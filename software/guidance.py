"""
guidance.py — Reachability Check & Optical Correction
======================================================
Computes whether the target is reachable from the current
pod position and altitude, and converts camera centroid
error into roll/pitch correction angles for the FC.
"""

import math
import logging
from dataclasses import dataclass

import config

log = logging.getLogger("GUIDANCE")


# ──────────────────────────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────────────────────────

EARTH_RADIUS_M = 6_371_000.0  # Earth mean radius in metres


# ──────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────

@dataclass
class OpticalCorrection:
    """Angular corrections derived from camera centroid error."""
    roll_deg:  float   # Positive = roll right
    pitch_deg: float   # Positive = pitch up (nose up)
    err_x_norm: float  # Normalised lateral error (-1.0 to +1.0)
    err_y_norm: float  # Normalised longitudinal error (-1.0 to +1.0)


# ──────────────────────────────────────────────────────────────────
# GREAT-CIRCLE DISTANCE
# ──────────────────────────────────────────────────────────────────

def haversine_distance(lat1: float, lon1: float,
                        lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two GPS points.

    Args:
        lat1, lon1: Source point (decimal degrees)
        lat2, lon2: Destination point (decimal degrees)

    Returns:
        Distance in metres.
    """
    phi1   = math.radians(lat1)
    phi2   = math.radians(lat2)
    dphi   = math.radians(lat2 - lat1)
    dlambda= math.radians(lon2 - lon1)

    a = (math.sin(dphi   / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(dlambda / 2) ** 2)

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def bearing_to(lat1: float, lon1: float,
               lat2: float, lon2: float) -> float:
    """
    Initial bearing from point 1 to point 2.

    Returns:
        Bearing in degrees (0 = North, 90 = East).
    """
    phi1    = math.radians(lat1)
    phi2    = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    x = math.sin(dlambda) * math.cos(phi2)
    y = (math.cos(phi1) * math.sin(phi2) -
         math.sin(phi1) * math.cos(phi2) * math.cos(dlambda))

    brng = math.degrees(math.atan2(x, y))
    return (brng + 360) % 360


# ──────────────────────────────────────────────────────────────────
# REACHABILITY CHECKER
# ──────────────────────────────────────────────────────────────────

class ReachabilityChecker:
    """
    Determines whether the target is within glide range of the pod.

    The check is:
        reachable if: distance_to_target ≤ (alt_agl × glide_ratio × safety_margin)

    A safety margin is applied to the theoretical max range so we
    never arrive at the target with exactly zero altitude margin.
    """

    def __init__(self,
                 glide_ratio: float   = config.GLIDE_RATIO,
                 safety_margin: float = config.SAFETY_MARGIN):
        self.glide_ratio    = glide_ratio
        self.safety_margin  = safety_margin

    def check(self,
              pod_lat: float,  pod_lon: float,
              pod_alt_agl: float,
              target_lat: float, target_lon: float,
              ) -> tuple[bool, float, float]:
        """
        Perform the reachability check.

        Args:
            pod_lat, pod_lon:       Pod GPS coordinates (decimal degrees)
            pod_alt_agl:            Pod altitude above ground level (metres)
            target_lat, target_lon: Target GPS coordinates (decimal degrees)

        Returns:
            Tuple of:
                reachable (bool):       True if target is within glide range
                distance_m (float):     Horizontal distance to target (metres)
                max_range_m (float):    Maximum reachable range from this altitude
        """
        distance_m  = haversine_distance(pod_lat, pod_lon, target_lat, target_lon)
        max_range_m = pod_alt_agl * self.glide_ratio * self.safety_margin

        reachable = distance_m <= max_range_m

        log.debug(
            "Reachability: dist=%.1fm  max=%.1fm  ratio=%.2f  → %s",
            distance_m, max_range_m,
            distance_m / max_range_m if max_range_m > 0 else float('inf'),
            "IN RANGE" if reachable else "OUT OF RANGE"
        )

        return reachable, distance_m, max_range_m

    def utilisation(self, pod_lat, pod_lon, pod_alt_agl,
                    target_lat, target_lon) -> float:
        """
        Returns the fraction of maximum range currently used.
        0.0 = at target, 1.0 = exactly at edge of range,
        > 1.0 = out of range.
        """
        _, dist, max_r = self.check(pod_lat, pod_lon, pod_alt_agl,
                                    target_lat, target_lon)
        return dist / max_r if max_r > 0 else float('inf')


# ──────────────────────────────────────────────────────────────────
# OPTICAL GUIDANCE CORRECTION
# ──────────────────────────────────────────────────────────────────

def compute_optical_correction(cx: float, cy: float,
                                frame_w: int, frame_h: int,
                                ) -> OpticalCorrection:
    """
    Convert camera centroid pixel error to roll/pitch correction angles.

    The camera is nose-mounted and faces the direction of travel.
    As the pod descends toward the target:
    - Lateral error (cx != frame centre) → roll correction
    - Longitudinal error (cy != frame centre) → pitch correction

    The corrections are ADDITIVE biases injected into the FC
    attitude setpoints, not absolute commands.

    Args:
        cx, cy:         Detected centroid position (pixels)
        frame_w, frame_h: Frame dimensions (pixels)

    Returns:
        OpticalCorrection with roll_deg and pitch_deg correction
    """
    # Normalise error to [-1.0, +1.0]
    # Positive err_x = target is to the RIGHT of frame centre
    # Positive err_y = target is BELOW frame centre (closer in dive)
    err_x = (cx - frame_w / 2.0) / (frame_w / 2.0)
    err_y = (cy - frame_h / 2.0) / (frame_h / 2.0)

    # Convert to angular corrections using FOV scaling
    # Half-FOV gives the maximum angular span at the frame edge
    half_fov_h = config.CAM_FOV_H_DEG / 2.0
    half_fov_v = config.CAM_FOV_V_DEG / 2.0

    ang_x = err_x * half_fov_h  # degrees
    ang_y = err_y * half_fov_v  # degrees

    # Apply guidance gains
    roll_cmd  = ang_x * config.KV_LATERAL
    pitch_cmd = ang_y * config.KV_PITCH

    # Safety clamp — never command more than max correction
    max_c = config.MAX_OPTICAL_CORRECTION_DEG
    roll_cmd  = max(-max_c, min(max_c, roll_cmd))
    pitch_cmd = max(-max_c, min(max_c, pitch_cmd))

    return OpticalCorrection(
        roll_deg=roll_cmd,
        pitch_deg=pitch_cmd,
        err_x_norm=err_x,
        err_y_norm=err_y,
    )


# ──────────────────────────────────────────────────────────────────
# FLIGHT PATH ANGLE
# ──────────────────────────────────────────────────────────────────

def required_flight_path_angle(distance_m: float, alt_agl_m: float) -> float:
    """
    Compute the required Flight Path Angle (FPA) to reach a target
    at a given horizontal distance and current altitude.

    Args:
        distance_m: Horizontal distance to target (metres)
        alt_agl_m:  Current altitude above ground (metres)

    Returns:
        FPA in degrees. Negative = nose down (descending toward target).
    """
    if distance_m <= 0:
        return -90.0  # Directly overhead — dive straight down
    return -math.degrees(math.atan2(alt_agl_m, distance_m))


# ──────────────────────────────────────────────────────────────────
# SELF-TEST
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    checker = ReachabilityChecker()

    print("=== REACHABILITY CHECK TESTS ===")

    # Test 1: Should be reachable (100m alt → ~340m max range at 4:1 ratio × 0.85)
    r, d, m = checker.check(33.5731, -7.5898, 100.0, 33.5750, -7.5898)
    print(f"Test 1 (nearby, 100m): reachable={r}, dist={d:.0f}m, max={m:.0f}m")
    assert r is True, "Should be reachable"

    # Test 2: Should NOT be reachable (10m alt → ~34m max range)
    r, d, m = checker.check(33.5731, -7.5898, 10.0, 33.5750, -7.5898)
    print(f"Test 2 (far, low alt): reachable={r}, dist={d:.0f}m, max={m:.0f}m")
    assert r is False, "Should NOT be reachable"

    print("\n=== OPTICAL CORRECTION TESTS ===")

    # Target perfectly centred
    c = compute_optical_correction(640, 360, 1280, 720)
    print(f"Centred: roll={c.roll_deg:.2f}° pitch={c.pitch_deg:.2f}°")
    assert abs(c.roll_deg) < 0.01 and abs(c.pitch_deg) < 0.01

    # Target top-right of frame
    c = compute_optical_correction(960, 180, 1280, 720)
    print(f"Top-right: roll={c.roll_deg:+.2f}° pitch={c.pitch_deg:+.2f}°")
    assert c.roll_deg > 0   # Roll right
    assert c.pitch_deg < 0  # Pitch down (target above centre)

    print("\nAll tests passed ✓")
