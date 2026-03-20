"""
comms.py — Flight Controller MAVLink Interface
===============================================
Handles all bidirectional communication between the
Raspberry Pi mission manager and the F405 flight controller.

Protocol: MAVLink v2 over hardware UART (RPi GPIO14/15)
Library: pymavlink
"""

import asyncio
import logging
import time
from typing import Optional, Any

log = logging.getLogger("COMMS")

try:
    from pymavlink import mavutil
    from pymavlink.dialects.v20 import ardupilotmega as mavlink2
    MAVLINK_AVAILABLE = True
except ImportError:
    log.warning("pymavlink not installed — comms module in SIMULATION mode")
    MAVLINK_AVAILABLE = False

import config


# ──────────────────────────────────────────────────────────────────
# FC LINK
# ──────────────────────────────────────────────────────────────────

class FC_Link:
    """
    Async wrapper around pymavlink for FC communication.
    All methods are coroutines — await them from the mission FSM.
    """

    def __init__(self, port: str, baud: int):
        self.port = port
        self.baud = baud
        self._conn: Optional[Any] = None
        self._connected = False
        self._message_queue: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._recv_task: Optional[asyncio.Task] = None

    # ────────────────────────────────────────────────────────────
    # CONNECTION
    # ────────────────────────────────────────────────────────────

    async def connect(self):
        """Open MAVLink connection to FC."""
        if not MAVLINK_AVAILABLE:
            log.warning("pymavlink not available — using simulation stub")
            self._connected = True
            return

        loop = asyncio.get_event_loop()
        try:
            # Open in executor so it doesn't block the event loop
            self._conn = await loop.run_in_executor(
                None,
                lambda: mavutil.mavlink_connection(
                    self.port,
                    baud=self.baud,
                    dialect="ardupilotmega",
                    source_system=config.MAVLINK_SYSID_PI,
                    source_component=config.MAVLINK_COMPID_PI,
                )
            )
            # Wait for heartbeat
            log.info("Waiting for FC heartbeat on %s @ %d baud...", self.port, self.baud)
            await loop.run_in_executor(None, self._conn.wait_heartbeat)
            self._connected = True
            log.info("FC heartbeat received. Target sysid=%d compid=%d",
                     self._conn.target_system, self._conn.target_component)

            # Request data streams
            self._request_data_streams()

            # Start background receive task
            self._recv_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            log.error("FC connection failed: %s", e)
            raise

    async def disconnect(self):
        """Close FC connection."""
        if self._recv_task:
            self._recv_task.cancel()
        if self._conn:
            self._conn.close()
        self._connected = False
        log.info("FC disconnected")

    # ────────────────────────────────────────────────────────────
    # DATA STREAM REQUEST
    # ────────────────────────────────────────────────────────────

    def _request_data_streams(self):
        """Ask FC to stream position, attitude, battery, and RC at useful rates."""
        if not self._conn:
            return
        streams = [
            (mavutil.mavlink.MAV_DATA_STREAM_POSITION,  10),  # 10 Hz GPS
            (mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,    50),  # 50 Hz attitude
            (mavutil.mavlink.MAV_DATA_STREAM_EXTRA2,    10),  # 10 Hz batt
            (mavutil.mavlink.MAV_DATA_STREAM_RC_CHANNELS, 20),# 20 Hz RC
            (mavutil.mavlink.MAV_DATA_STREAM_RAW_SENSORS, 50),# 50 Hz IMU
        ]
        for stream_id, rate_hz in streams:
            self._conn.mav.request_data_stream_send(
                self._conn.target_system,
                self._conn.target_component,
                stream_id,
                rate_hz,
                1  # Start streaming
            )
        log.debug("Data stream requests sent")

    # ────────────────────────────────────────────────────────────
    # RECEIVE LOOP
    # ────────────────────────────────────────────────────────────

    async def _receive_loop(self):
        """Read MAVLink messages from FC and push to queue."""
        loop = asyncio.get_event_loop()
        while self._connected:
            try:
                msg = await loop.run_in_executor(
                    None,
                    lambda: self._conn.recv_match(blocking=True, timeout=0.1)
                )
                if msg is not None:
                    if self._message_queue.full():
                        try:
                            self._message_queue.get_nowait()  # Drop oldest
                        except asyncio.QueueEmpty:
                            pass
                    await self._message_queue.put(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.debug("Receive error: %s", e)
                await asyncio.sleep(0.01)

    async def read_message(self):
        """Get next message from receive queue (non-blocking)."""
        if not MAVLINK_AVAILABLE:
            await asyncio.sleep(0.1)
            return None
        try:
            return self._message_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    # ────────────────────────────────────────────────────────────
    # COMMANDS
    # ────────────────────────────────────────────────────────────

    async def send_heartbeat(self):
        """Send MAVLink heartbeat from Pi companion computer."""
        if not self._conn or not MAVLINK_AVAILABLE:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._conn.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, 0
        ))

    async def fire_latch(self):
        """
        Command the release servo (CH5 relay) to fire.
        This drops the pod from the carrier aircraft wing.
        Maps to RELAY_SET command — must configure FC relay output to CH5.
        """
        if not self._conn or not MAVLINK_AVAILABLE:
            log.info("[SIM] LATCH FIRED")
            return

        log.info("Sending LATCH FIRE command to FC (DO_SET_RELAY relay_num=0 state=1)")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._conn.mav.command_long_send(
            self._conn.target_system,
            self._conn.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
            0,      # Confirmation
            0,      # Relay number 0 (mapped to CH5 in FC params)
            1,      # State: 1 = HIGH (releases latch)
            0, 0, 0, 0, 0
        ))

        # Hold HIGH for 500ms then return to LOW
        await asyncio.sleep(0.5)
        await loop.run_in_executor(None, lambda: self._conn.mav.command_long_send(
            self._conn.target_system,
            self._conn.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_RELAY,
            0, 0, 0, 0, 0, 0, 0, 0
        ))
        log.info("Latch servo returned to LOW")

    async def set_guided_target(self, lat: float, lon: float, alt: float):
        """
        Set the GPS waypoint target for FC to navigate toward.
        Sends SET_POSITION_TARGET_GLOBAL_INT to FC in GUIDED mode.
        """
        if not self._conn or not MAVLINK_AVAILABLE:
            log.info("[SIM] GPS target set: %.6f, %.6f, %.1fm", lat, lon, alt)
            return

        log.info("Setting guided target: lat=%.6f lon=%.6f alt=%.1f", lat, lon, alt)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._conn.mav.set_position_target_global_int_send(
            0,          # time_boot_ms (ignored)
            self._conn.target_system,
            self._conn.target_component,
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            0b0000111111111000,  # Type mask: position only (ignore velocity/accel)
            int(lat * 1e7),      # lat_int
            int(lon * 1e7),      # lon_int
            alt,                 # alt (relative to home)
            0, 0, 0,             # vx, vy, vz (ignored)
            0, 0, 0,             # afx, afy, afz (ignored)
            0, 0                 # yaw, yaw_rate (ignored)
        ))

    async def inject_visual_correction(self, roll_correction: float,
                                        pitch_correction: float):
        """
        Inject optical guidance corrections as attitude setpoint offsets.
        Sent as ATTITUDE_TARGET with the correction applied to the FC's
        current attitude setpoint.

        This is handled in FC by the vision_inject.lua script which
        receives a custom MAVLink message and adds the correction to
        the attitude controller setpoint.
        """
        if not self._conn or not MAVLINK_AVAILABLE:
            log.debug("[SIM] Visual correction: roll=%+.1f° pitch=%+.1f°",
                      roll_correction, pitch_correction)
            return

        import math
        loop = asyncio.get_event_loop()

        # Encode as quaternion — apply roll and pitch corrections
        # This is a small-angle correction quaternion
        half_r = math.radians(roll_correction  / 2.0)
        half_p = math.radians(pitch_correction / 2.0)

        qw = math.cos(half_r) * math.cos(half_p)
        qx = math.sin(half_r) * math.cos(half_p)
        qy = math.cos(half_r) * math.sin(half_p)
        qz = 0.0

        # Mask: use quaternion, ignore body rates and thrust
        type_mask = 0b11000111  # Use Q, ignore rates, ignore thrust

        await loop.run_in_executor(None, lambda: self._conn.mav.set_attitude_target_send(
            0,          # time_boot_ms
            self._conn.target_system,
            self._conn.target_component,
            type_mask,
            [qw, qx, qy, qz],
            0, 0, 0,   # roll/pitch/yaw rates (ignored)
            0.5        # thrust (ignored by mask)
        ))

    async def send_status_text(self, text: str):
        """Send a status text message visible on GCS."""
        if not self._conn or not MAVLINK_AVAILABLE:
            log.info("[STATUS] %s", text)
            return

        # Truncate to 50 chars (MAVLink STATUSTEXT limit)
        text = text[:50]
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._conn.mav.statustext_send(
            mavutil.mavlink.MAV_SEVERITY_INFO,
            text.encode("utf-8")
        ))
        log.info("GCS status: %s", text)
