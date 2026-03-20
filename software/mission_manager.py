"""
mission_manager.py — Drop Pod Mission State Machine
=====================================================
Main entry point. Runs on Raspberry Pi Zero 2W.
Manages high-level mission phases, communicates with
the F405 flight controller via MAVLink, and triggers
the vision pipeline at the correct altitude.

Run: python3 mission_manager.py
"""

import asyncio
import logging
import time
import signal
import sys
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional

import config
from comms import FC_Link
from vision import RedCarpetTracker
from guidance import ReachabilityChecker, compute_optical_correction

# ──────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"{config.LOG_DIR}/mission_{int(time.time())}.log"),
    ]
)
log = logging.getLogger("MISSION")


# ──────────────────────────────────────────────────────────────────
# MISSION STATES
# ──────────────────────────────────────────────────────────────────

class MissionState(Enum):
    IDLE         = auto()   # Pre-arm, passive on carrier wing
    ARMED        = auto()   # ARM received, monitoring, latch ready
    RELEASED     = auto()   # Latch fired, pod in free flight
    GLIDE_GPS    = auto()   # GPS-guided approach toward target
    GLIDE_OPTICAL= auto()   # Camera locked, optical terminal guidance
    LANDED       = auto()   # Impact detected, mission complete
    ABORT        = auto()   # Operator abort or safety fault


# ──────────────────────────────────────────────────────────────────
# TELEMETRY SNAPSHOT (thread-safe shared state)
# ──────────────────────────────────────────────────────────────────

@dataclass
class PodTelemetry:
    """Current pod state, updated by FC MAVLink messages."""
    lat: float          = 0.0
    lon: float          = 0.0
    alt_msl: float      = 0.0
    alt_agl: float      = 0.0
    roll_deg: float     = 0.0
    pitch_deg: float    = 0.0
    yaw_deg: float      = 0.0
    vx: float           = 0.0   # velocity m/s
    vy: float           = 0.0
    vz: float           = 0.0
    gps_fix: bool       = False
    gps_hdop: float     = 99.0
    battery_v: float    = 0.0
    battery_pct: float  = 0.0
    accel_g: float      = 0.0
    rc_arm_high: bool   = False
    rc_drop_high: bool  = False
    rc_abort_high: bool = False
    timestamp: float    = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────────────
# MISSION MANAGER
# ──────────────────────────────────────────────────────────────────

class MissionManager:
    def __init__(self):
        self.state = MissionState.IDLE
        self.telemetry = PodTelemetry()
        self.mission_start_time: Optional[float] = None
        self.drop_time: Optional[float] = None
        self._running = True

        # Sub-systems (initialised in run())
        self.fc: Optional[FC_Link] = None
        self.tracker: Optional[RedCarpetTracker] = None
        self.reachability: Optional[ReachabilityChecker] = None

        # Tracking state
        self.lock_frame_count = 0
        self.camera_active = False

        log.info("MissionManager initialised. State: IDLE")

    # ────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ────────────────────────────────────────────────────────────

    async def run(self):
        """Main async mission loop. Entry point."""
        log.info("Starting Drop Pod Mission Manager")
        log.info(f"Target: {config.TARGET_LAT:.6f}, {config.TARGET_LON:.6f}")

        # Initialise sub-systems
        self.fc = FC_Link(config.FC_UART_PORT, config.FC_UART_BAUD)
        self.tracker = RedCarpetTracker()
        self.reachability = ReachabilityChecker()

        await self.fc.connect()

        # Spawn tasks
        tasks = [
            asyncio.create_task(self._telemetry_loop()),
            asyncio.create_task(self._state_machine_loop()),
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._watchdog_loop()),
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            log.info("Mission tasks cancelled — shutting down")
        finally:
            await self._shutdown()

    # ────────────────────────────────────────────────────────────
    # TELEMETRY LOOP
    # ────────────────────────────────────────────────────────────

    async def _telemetry_loop(self):
        """Continuously read MAVLink messages from FC and update telemetry."""
        log.info("Telemetry loop started")
        while self._running:
            msg = await self.fc.read_message()
            if msg is None:
                await asyncio.sleep(0.001)
                continue

            t = self.telemetry

            if msg.get_type() == "GLOBAL_POSITION_INT":
                t.lat     = msg.lat / 1e7
                t.lon     = msg.lon / 1e7
                t.alt_msl = msg.alt / 1000.0
                t.alt_agl = msg.relative_alt / 1000.0
                t.vx      = msg.vx / 100.0
                t.vy      = msg.vy / 100.0
                t.vz      = msg.vz / 100.0
                t.gps_fix = True

            elif msg.get_type() == "ATTITUDE":
                import math
                t.roll_deg  = math.degrees(msg.roll)
                t.pitch_deg = math.degrees(msg.pitch)
                t.yaw_deg   = math.degrees(msg.yaw)

            elif msg.get_type() == "GPS_RAW_INT":
                t.gps_fix  = msg.fix_type >= 3
                t.gps_hdop = msg.eph / 100.0

            elif msg.get_type() == "SYS_STATUS":
                t.battery_v   = msg.voltage_battery / 1000.0
                t.battery_pct = msg.battery_remaining

            elif msg.get_type() == "SCALED_IMU":
                import math
                accel_mag = math.sqrt(msg.xacc**2 + msg.yacc**2 + msg.zacc**2) / 1000.0
                t.accel_g = accel_mag / 9.81

            elif msg.get_type() == "RC_CHANNELS":
                t.rc_arm_high   = msg.chan7_raw  > config.RC_HIGH_THRESHOLD_US
                t.rc_drop_high  = msg.chan8_raw  > config.RC_HIGH_THRESHOLD_US
                t.rc_abort_high = msg.chan9_raw  > config.RC_HIGH_THRESHOLD_US

            t.timestamp = time.time()

    # ────────────────────────────────────────────────────────────
    # STATE MACHINE LOOP
    # ────────────────────────────────────────────────────────────

    async def _state_machine_loop(self):
        """Core mission FSM — transitions based on telemetry and commands."""
        log.info("State machine loop started")

        while self._running:
            await asyncio.sleep(0.05)  # 20 Hz FSM tick
            t = self.telemetry

            # ── ABORT override — highest priority ────────────────
            if t.rc_abort_high and self.state not in (MissionState.IDLE, MissionState.LANDED, MissionState.ABORT):
                await self._transition(MissionState.ABORT, "Operator ABORT command")
                continue

            # ── Per-state logic ──────────────────────────────────
            if self.state == MissionState.IDLE:
                await self._state_idle(t)

            elif self.state == MissionState.ARMED:
                await self._state_armed(t)

            elif self.state == MissionState.RELEASED:
                await self._state_released(t)

            elif self.state == MissionState.GLIDE_GPS:
                await self._state_glide_gps(t)

            elif self.state == MissionState.GLIDE_OPTICAL:
                await self._state_glide_optical(t)

            elif self.state == MissionState.LANDED:
                pass  # Terminal state — wait for shutdown

            elif self.state == MissionState.ABORT:
                await self._state_abort(t)

    # ────────────────────────────────────────────────────────────
    # STATE HANDLERS
    # ────────────────────────────────────────────────────────────

    async def _state_idle(self, t: PodTelemetry):
        """IDLE: Wait for ARM command."""
        if t.rc_arm_high:
            if not t.gps_fix or t.gps_hdop > 3.0:
                log.warning("ARM received but GPS fix not valid (HDOP %.1f) — holding IDLE", t.gps_hdop)
                await self.fc.send_status_text("ARM REJECTED: GPS NOT READY")
                return
            await self._transition(MissionState.ARMED, "ARM command received")

    async def _state_armed(self, t: PodTelemetry):
        """ARMED: Monitor, check reachability, wait for DROP command."""
        # Continuous reachability update
        reachable, dist, max_range = self.reachability.check(
            pod_lat=t.lat, pod_lon=t.lon,
            pod_alt_agl=t.alt_agl,
            target_lat=config.TARGET_LAT,
            target_lon=config.TARGET_LON,
        )

        # Log reachability status at 1 Hz
        if int(time.time() * 10) % 10 == 0:
            status = "IN RANGE" if reachable else "OUT OF RANGE"
            log.debug("Reachability: %s | dist=%.0fm | max=%.0fm", status, dist, max_range)

        # Check DROP command
        if t.rc_drop_high:
            if not reachable:
                log.warning("DROP rejected — target OUT OF RANGE (dist=%.0fm, max=%.0fm)", dist, max_range)
                await self.fc.send_status_text(f"DROP REJECTED: OUT OF RANGE ({dist:.0f}m > {max_range:.0f}m)")
                return

            if t.alt_agl < config.MIN_RELEASE_AGL_M:
                log.warning("DROP rejected — altitude too low (%.0fm AGL < %.0fm)", t.alt_agl, config.MIN_RELEASE_AGL_M)
                await self.fc.send_status_text(f"DROP REJECTED: TOO LOW ({t.alt_agl:.0f}m AGL)")
                return

            # All checks passed — fire latch
            log.info("DROP accepted. Firing latch. dist=%.0fm, max=%.0fm, alt=%.0fm AGL", dist, max_range, t.alt_agl)
            await self.fc.fire_latch()
            await self._transition(MissionState.RELEASED, "Latch fired")

    async def _state_released(self, t: PodTelemetry):
        """RELEASED: Stabilise after separation, transition to GPS glide."""
        # Small delay for separation dynamics to settle
        await asyncio.sleep(0.3)

        # Send target waypoint to FC
        await self.fc.set_guided_target(
            lat=config.TARGET_LAT,
            lon=config.TARGET_LON,
            alt=config.TARGET_ALT_MSL,
        )
        self.drop_time = time.time()
        await self._transition(MissionState.GLIDE_GPS, "Separation confirmed, GPS approach active")

    async def _state_glide_gps(self, t: PodTelemetry):
        """GLIDE_GPS: GPS-guided approach toward target. Camera not yet active."""
        # Check mission timeout
        if self.drop_time and (time.time() - self.drop_time) > config.MISSION_TIMEOUT_S:
            await self._transition(MissionState.ABORT, "Mission timeout exceeded")
            return

        # Check GPS loss
        if not t.gps_fix:
            log.warning("GPS fix lost during GPS glide phase")
            await self.fc.send_status_text("WARNING: GPS FIX LOST")
            # Continue — FC will hold last heading

        # Activate camera when below threshold altitude
        if t.alt_agl <= config.CAMERA_ACTIVATE_AGL_M and not self.camera_active:
            log.info("AGL %.1fm — activating camera", t.alt_agl)
            self.tracker.start()
            self.camera_active = True
            await self.fc.send_status_text("CAMERA ACTIVE — searching for target")
            await self._transition(MissionState.GLIDE_OPTICAL, "Altitude threshold reached")

    async def _state_glide_optical(self, t: PodTelemetry):
        """GLIDE_OPTICAL: Camera active, optical corrections injected to FC."""
        # Get latest vision result
        result = self.tracker.get_latest()

        if result is not None and result.confidence >= config.MIN_LOCK_CONFIDENCE:
            self.lock_frame_count += 1

            if self.lock_frame_count >= config.MIN_LOCK_FRAMES:
                # Compute angular correction from centroid error
                correction = compute_optical_correction(
                    cx=result.cx,
                    cy=result.cy,
                    frame_w=config.CAM_RESOLUTION[0],
                    frame_h=config.CAM_RESOLUTION[1],
                )
                # Send correction to FC
                await self.fc.inject_visual_correction(
                    roll_correction=correction.roll_deg,
                    pitch_correction=correction.pitch_deg,
                )
                log.debug("Optical lock: conf=%.2f cx=%.1f cy=%.1f | ΔR=%.1f° ΔP=%.1f°",
                          result.confidence, result.cx, result.cy,
                          correction.roll_deg, correction.pitch_deg)
        else:
            self.lock_frame_count = max(0, self.lock_frame_count - 1)
            log.debug("Target not locked (conf=%.2f)", result.confidence if result else 0.0)

        # Check for impact (landing detection)
        if t.accel_g > config.IMPACT_ACCEL_G:
            await self._transition(MissionState.LANDED, f"Impact detected ({t.accel_g:.1f}g)")

    async def _state_abort(self, t: PodTelemetry):
        """ABORT: Disable optical corrections, hold last attitude."""
        if self.camera_active:
            self.tracker.stop()
            self.camera_active = False
        await self.fc.send_status_text("MISSION ABORTED")
        log.warning("MISSION ABORTED — holding attitude, no corrections")
        self._running = False

    # ────────────────────────────────────────────────────────────
    # HEARTBEAT LOOP
    # ────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self):
        """Send periodic heartbeat to FC so watchdog knows Pi is alive."""
        while self._running:
            await self.fc.send_heartbeat()
            await asyncio.sleep(config.HEARTBEAT_INTERVAL_S)

    # ────────────────────────────────────────────────────────────
    # WATCHDOG LOOP
    # ────────────────────────────────────────────────────────────

    async def _watchdog_loop(self):
        """Monitor telemetry freshness and battery voltage."""
        while self._running:
            await asyncio.sleep(1.0)
            t = self.telemetry
            age = time.time() - t.timestamp

            if age > 5.0 and self.state not in (MissionState.IDLE, MissionState.LANDED, MissionState.ABORT):
                log.error("FC telemetry stale (%.1fs old) — possible FC comms failure", age)
                await self.fc.send_status_text("WARNING: TELEMETRY STALE")

            per_cell_v = t.battery_v / 3.0 if t.battery_v > 0 else 0
            if 0 < per_cell_v < config.LOW_BATT_CELL_V:
                log.warning("Low battery: %.2fV/cell (%.1fV total)", per_cell_v, t.battery_v)
                await self.fc.send_status_text(f"LOW BATTERY: {t.battery_v:.1f}V")

    # ────────────────────────────────────────────────────────────
    # HELPERS
    # ────────────────────────────────────────────────────────────

    async def _transition(self, new_state: MissionState, reason: str):
        old = self.state.name
        self.state = new_state
        log.info("STATE: %s → %s | %s", old, new_state.name, reason)
        await self.fc.send_status_text(f"STATE:{new_state.name}")

        if new_state == MissionState.LANDED:
            elapsed = time.time() - self.drop_time if self.drop_time else 0
            log.info("MISSION COMPLETE. Flight time: %.1fs", elapsed)
            if self.camera_active:
                self.tracker.stop()
            self._running = False

    async def _shutdown(self):
        log.info("Shutting down mission manager")
        if self.tracker:
            self.tracker.stop()
        if self.fc:
            await self.fc.disconnect()


# ──────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def main():
    import os
    os.makedirs(config.LOG_DIR, exist_ok=True)

    manager = MissionManager()

    # Graceful shutdown on Ctrl+C / SIGTERM
    loop = asyncio.get_event_loop()

    def handle_signal(sig, frame):
        log.info("Received signal %s — initiating shutdown", sig)
        loop.stop()

    signal.signal(signal.SIGINT,  handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        loop.run_until_complete(manager.run())
    finally:
        loop.close()
        log.info("Mission manager stopped")


if __name__ == "__main__":
    main()
