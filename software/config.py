"""
config.py — Drop Pod Central Configuration
===========================================
All tunable mission, vision, guidance, and communication parameters
live here. Edit this file before each mission.

DO NOT modify values mid-flight. Restart mission_manager.py
to apply changes.
"""

# ──────────────────────────────────────────────────────────────────────────────
# MISSION TARGET
# ──────────────────────────────────────────────────────────────────────────────

# GPS coordinates of the red carpet landing target
TARGET_LAT: float = 33.5731       # Decimal degrees — replace with your target
TARGET_LON: float = -7.5898       # Decimal degrees — replace with your target
TARGET_ALT_MSL: float = 0.0       # Ground elevation above mean sea level (metres)
                                   # Use GPS waypoint tool or topo map to get this

# ──────────────────────────────────────────────────────────────────────────────
# REACHABILITY CHECK
# ──────────────────────────────────────────────────────────────────────────────

# Conservative glide ratio for reachability calculation
# Real glide may be higher — use conservative value for safety
GLIDE_RATIO: float = 4.0          # horizontal distance / altitude lost

# Fraction of theoretical max range to use (safety buffer)
# 0.85 = use only 85% of maximum glide range
SAFETY_MARGIN: float = 0.85

# Wind speed above which DROP command is automatically rejected
MAX_WIND_SPEED_MS: float = 8.0    # m/s — measured from FC EKF or baro

# Minimum release altitude for any drop to be accepted
MIN_RELEASE_AGL_M: float = 40.0   # metres AGL

# ──────────────────────────────────────────────────────────────────────────────
# PHASE TRANSITION THRESHOLDS
# ──────────────────────────────────────────────────────────────────────────────

# Altitude AGL at which camera activates and optical tracking begins
CAMERA_ACTIVATE_AGL_M: float = 40.0   # metres

# Minimum lock confidence (0.0–1.0) to transition GPS→OPTICAL phase
MIN_LOCK_CONFIDENCE: float = 0.80

# Impact detection: accelerometer spike above this triggers LANDED state
IMPACT_ACCEL_G: float = 4.0            # multiples of g

# Minimum consecutive frames target must be detected before lock confirmed
MIN_LOCK_FRAMES: int = 5

# ──────────────────────────────────────────────────────────────────────────────
# VISION PARAMETERS
# ──────────────────────────────────────────────────────────────────────────────

# Camera resolution for OpenCV processing
# Lower resolution = faster processing. 1280×720 recommended.
CAM_RESOLUTION: tuple = (1280, 720)
CAM_FPS: int = 30

# Camera FOV (degrees) — RPi Camera Module 3 Wide
CAM_FOV_H_DEG: float = 102.0     # Horizontal field of view
CAM_FOV_V_DEG: float = 67.0      # Vertical field of view

# HSV colour ranges for red carpet detection
# Red hue wraps in HSV (near 0° AND near 180°) — two ranges needed
# Adjust S and V thresholds for your lighting conditions
HSV_RED_LOW_1:  tuple = (0,   120, 80)    # Lower bound — range 1 (hue 0–12)
HSV_RED_HIGH_1: tuple = (12,  255, 255)   # Upper bound — range 1
HSV_RED_LOW_2:  tuple = (165, 120, 80)    # Lower bound — range 2 (hue 165–180)
HSV_RED_HIGH_2: tuple = (180, 255, 255)   # Upper bound — range 2

# Morphological kernel sizes for noise filtering
MORPH_OPEN_KERNEL_SIZE:  int = 5   # Removes small noise blobs
MORPH_CLOSE_KERNEL_SIZE: int = 11  # Fills gaps in carpet blob

# Minimum red carpet blob area (pixels²) to register as valid detection
# Increase if getting false positives; decrease if carpet not detected at height
MIN_CARPET_AREA_PX: int = 800

# ──────────────────────────────────────────────────────────────────────────────
# OPTICAL GUIDANCE GAINS
# ──────────────────────────────────────────────────────────────────────────────

# Lateral correction gain: pixel offset → roll correction (degrees)
KV_LATERAL: float = 0.4

# Pitch correction gain: pixel offset → pitch correction (degrees)
# Smaller than lateral — pitch is less sensitive in nose-dive
KV_PITCH: float = 0.15

# Maximum optical correction magnitude (degrees) — safety clamp
MAX_OPTICAL_CORRECTION_DEG: float = 15.0

# ──────────────────────────────────────────────────────────────────────────────
# COMMUNICATION
# ──────────────────────────────────────────────────────────────────────────────

# Serial port for FC MAVLink connection on RPi
FC_UART_PORT: str = "/dev/serial0"   # RPi hardware UART (GPIO14/15)
FC_UART_BAUD: int = 115200

# Heartbeat interval (seconds) — Pi → FC
HEARTBEAT_INTERVAL_S: float = 0.5

# Telemetry broadcast rate (Hz) for position + state to GCS
TELEM_RATE_HZ: float = 5.0

# MAVLink system IDs
MAVLINK_SYSID_FC:  int = 1    # Flight controller system ID
MAVLINK_SYSID_PI:  int = 2    # Companion computer system ID
MAVLINK_COMPID_PI: int = 191  # Companion computer component ID

# ──────────────────────────────────────────────────────────────────────────────
# RC CHANNEL ASSIGNMENTS
# ──────────────────────────────────────────────────────────────────────────────

# RC channel numbers (1-indexed) for ARM and DROP commands
RC_CHANNEL_ARM:   int = 7   # Aux 1 on most TX (CH7)
RC_CHANNEL_DROP:  int = 8   # Aux 2 on most TX (CH8)
RC_CHANNEL_ABORT: int = 9   # Aux 3 on most TX (CH9)

# PWM threshold above which channel is considered HIGH
RC_HIGH_THRESHOLD_US: int = 1700   # microseconds

# ──────────────────────────────────────────────────────────────────────────────
# SAFETY & WATCHDOG
# ──────────────────────────────────────────────────────────────────────────────

# GPS lock timeout — if no GPS for this long, degrade to attitude hold
GPS_TIMEOUT_S: float = 3.0

# Heartbeat watchdog — if FC doesn't hear Pi for this long, disable corrections
FC_WATCHDOG_TIMEOUT_S: float = 1.5

# Maximum mission duration from drop to landed before timeout fault
MISSION_TIMEOUT_S: float = 120.0

# Minimum battery voltage (per cell) before low-voltage telemetry alert
LOW_BATT_CELL_V: float = 3.4   # volts per cell (3S × 3.4 = 10.2V total)

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────────

LOG_DIR: str = "/home/pi/drop-pod-logs"
LOG_LEVEL: str = "DEBUG"       # DEBUG / INFO / WARNING / ERROR
LOG_VIDEO: bool = True         # Save annotated video of each mission
LOG_VIDEO_FILENAME: str = "mission_video.mp4"
