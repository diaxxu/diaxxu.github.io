#  DROP POD — Precision Aerial Delivery System

<p align="center">
  
</p>
<img width="1255" height="507" alt="Capture d&#39;écran 2026-03-20 113256" src="https://github.com/user-attachments/assets/94ea00aa-1a5b-4375-b1bc-d8ddc1eb9a80" />

<p align="center">
  <img src="https://img.shields.io/badge/status-active--development-orange?style=flat-square"/>
  <img src="https://img.shields.io/badge/guidance-GPS%20%2B%20Optical-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/actuation-4×%20canard%20fins-red?style=flat-square"/>
  <img src="https://img.shields.io/badge/target-red%20carpet-crimson?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square"/>
</p>

---

> **A fully autonomous, GPS + vision-guided drop pod** carried under the wing of an RC aircraft. Released on operator command, it navigates to a red carpet landing zone using GPS macro-guidance and nose-mounted optical terminal tracking — nose-first impact, cushion-assisted landing. No propulsion. No parachute. Pure precision.

---

##  Table of Contents

1. [What This Is](#what-this-is)
2. [How It Works](#how-it-works)
3. [System Architecture](#system-architecture)
4. [Hardware Requirements](#hardware-requirements)
5. [Software Stack](#software-stack)
6. [Directory Structure](#directory-structure)
7. [Quick Start](#quick-start)
8. [Wiring Guide](#wiring-guide)
9. [Configuration](#configuration)
10. [Flight Operations](#flight-operations)
11. [Tuning Guide](#tuning-guide)
12. [Safety & Legal](#safety--legal)
13. [Contributing](#contributing)
14. [Roadmap](#roadmap)
15. [Team & Credits](#team--credits)

---

## What This Is

The **Drop Pod** is a passively propelled, actively guided aerial payload delivery system. It is:

- **Carried** under the wing of any medium RC aircraft (minimum 1.5 kg payload capacity)
- **Released** on operator command (RC transmitter aux channel or GCS MAVLink command)
- **Self-guided** using onboard GNSS to the target zone
- **Optically locked** onto a red carpet marker using a nose-mounted camera running real-time OpenCV detection
- **Nose-impact landed** — the pod dives nose-first onto the cushioned target

**Phase 1 scope (this repository):** GPS approach + optical lock + direct nose-impact. No flare. No glide slope. Ground team places a foam/air cushion on the red carpet. The pod hits it clean.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        MISSION TIMELINE                         │
└─────────────────────────────────────────────────────────────────┘

  [GROUND]                [IN-AIR]                    [TERMINAL]
  
  Load target GPS    →   Carrier delivers pod   →   Pod descends
  Arm system             over drop zone             GPS-guided
  Confirm carpet         ↓                          ↓
  is in range            Operator sends             At ~40m AGL:
  ↓                      ARM → DROP                 Camera activates
  Cushion placed         ↓                          Red carpet locked
  on carpet              Reachability check         Optical steering
                         passes                     ↓
                         ↓                          Nose-impact on
                         Latch fires                cushion ✓
                         Pod separates
```

### Phase Breakdown

| Phase | Mode | Altitude | Trigger |
|-------|------|----------|---------|
| **Idle** | Passive on wing | Any | — |
| **Armed** | Monitoring | Any | ARM command |
| **Released** | Stabilised descent | Drop alt | DROP command + reach check |
| **GPS Approach** | GNSS-guided | Drop → 40 m AGL | Automatic post-release |
| **Optical Lock** | Camera tracking | 40 m → impact | Barometer threshold |
| **Landed** | Inert | 0 | Impact detection (accel) |

---

## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    DROP POD INTERNALS                      │
│                                                            │
│  [NOSE — CAMERA]                                           │
│  ┌─────────────────────────────────────┐                   │
│  │  RPi Camera Module 3 (CSI-2)        │ ← Nose tip        │
│  │  IMX708 · 102° FOV · 30fps          │   looking forward │
│  └──────────────┬──────────────────────┘                   │
│                 │ CSI ribbon                               │
│  [FORWARD SECTION — COMPUTE + FINS]                        │
│  ┌──────────────▼──────────────────────┐                   │
│  │  Raspberry Pi Zero 2W               │ ← Vision + FSM    │
│  │  ├─ mission_manager.py              │                   │
│  │  ├─ vision.py (OpenCV)              │                   │
│  │  └─ UART → FC (MAVLink/MSP)         │                   │
│  │                                     │                   │
│  │  Matek F405-WING (ArduPlane)        │ ← PID + Servos    │
│  │  ├─ IMU ICM-42688 (SPI)             │                   │
│  │  ├─ GPS u-blox M10 (UART)          │                   │
│  │  ├─ Baro BMP388 (I2C)              │                   │
│  │  └─ 4× Servo PWM outputs           │                   │
│  │                                     │                   │
│  │  4× Canard Fins (cruciform)         │ ← Actuation       │
│  │  Emax ES9051 · 2.0 kg·cm           │                   │
│  └─────────────────────────────────────┘                   │
│                                                            │
│  [MID SECTION — POWER + COMMS]                             │
│  ┌─────────────────────────────────────┐                   │
│  │  3S 1000mAh LiPo (11.1V)           │ ← Main power       │
│  │  Pololu 5V BEC ×2                   │                   │
│  │  ELRS Receiver (2.4GHz SBUS)        │ ← RC commands      │
│  │  SiK 915MHz Telemetry               │ ← GCS MAVLink      │
│  └─────────────────────────────────────┘                   │
└────────────────────────────────────────────────────────────┘
```

### Inter-Processor Communication

```
RC TX (pilot)  ──SBUS──►  ELRS Receiver ──SBUS──► F405 FC
                                                      │
GCS (laptop)   ──MAVLink/915MHz──────────────────────►│
                                                      │
                                            F405 FC ◄─┤─► 4× Servo (PWM 400Hz)
                                               │      │
                                           UART/MSP   │
                                               │      │
                                        RPi Zero 2W   │
                                               │      │
                                         CSI-2 │      │
                                               │      │
                                        Camera Module  │
```

---

## Hardware Requirements

See [BOM.csv](BOM.csv) for complete sourcing list. Summary:

| # | Component | Purpose | Est. Cost |
|---|-----------|---------|-----------|
| 1 | **Matek F405-WING** | Flight controller, PID, servo output | $35 |
| 2 | **Raspberry Pi Zero 2W** | Vision compute, mission FSM | $15 |
| 3 | **RPi Camera Module 3 Wide** | Nose-mounted target tracking | $25 |
| 4 | **u-blox M10 GPS** | GNSS macro-approach guidance | $30 |
| 5 | **ICM-42688-P IMU** | Attitude estimation (may be on FC) | $8 |
| 6 | **BMP388 Barometer** | AGL altitude for camera activation | $5 |
| 7 | **SiK 915MHz Radio ×2** | GCS MAVLink telemetry + uplink | $30 |
| 8 | **ELRS Receiver** | RC TX commands (ARM/DROP) | $12 |
| 9 | **9g Digital Servo ×5** | 4× fin + 1× wing latch | $20 |
| 10 | **3S 1000mAh LiPo** | Main power | $18 |
| 11 | **Pololu 5V BEC ×2** | Regulated power rails | $10 |
| 12 | **CF Tube ø80×320mm** | Main fuselage | $15 |
| 13 | **PETG/PLA Filament** | Printed structure parts | $10 |
| **Total** | | | **~$233** |

### Carrier Aircraft Requirements

- Minimum payload capacity: **800g** (pod target mass ≤ 650g)
- Wing hardpoint or pod-rail mounting point
- Free aux channel on RC TX for release servo
- Stable flight at 12–22 m/s

---

## Software Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Flight controller | ArduPlane (STM32) | PID, servo mixing, GPS nav |
| Vision + FSM | Python 3.11 on RPi | OpenCV, mission state machine |
| Inter-proc comms | MAVLink over UART | Pi ↔ FC bidirectional |
| GCS | Mission Planner / MAVProxy | Ground control, telemetry display |
| Configuration | YAML + .param files | All tunable params in one place |

---

## Directory Structure

```
drop-pod/
│
├── README.md                    ← You are here
├── BOM.csv                      ← Full bill of materials with sourcing
├── LICENSE                      ← MIT License
│
├── software/                    ← All Python code for RPi
│   ├── requirements.txt         ← pip dependencies
│   ├── config.py                ← Central configuration (all tunable params)
│   ├── mission_manager.py       ← Main mission FSM — entry point
│   ├── vision.py                ← OpenCV red carpet detection pipeline
│   ├── guidance.py              ← Reachability check + GPS math
│   └── comms.py                 ← MAVLink interface (FC + GCS)
│
├── firmware/
│   ├── params/
│   │   └── drop_pod.param       ← ArduPlane parameter file (load via MP)
│   └── lua/
│       └── vision_inject.lua    ← ArduPlane Lua: ingest Pi corrections
│
├── hardware/
│   ├── stl/
│   │   ├── README.md            ← Print settings for every part
│   │   ├── nose_camera_mount.stl
│   │   ├── fin_mount_forward.stl
│   │   ├── fin_blade.stl
│   │   ├── servo_bay_cover.stl
│   │   ├── avionics_tray.stl
│   │   ├── power_bay.stl
│   │   └── tail_cap_camera_exit.stl   ← NOTE: camera is at nose, this is ballast
│   └── wiring/
│       └── wiring_diagram.md    ← Full pinout and wiring guide
│
├── docs/
│   ├── MECHANICAL.md            ← Dimensions, CG, fin geometry
│   ├── ASSEMBLY.md              ← Step-by-step build guide
│   ├── TUNING.md                ← PID tuning procedure
│   ├── SAFETY.md                ← Pre-flight checklist, regulations
│   └── FLIGHT_OPS.md            ← Field operations manual
│
└── .github/
    └── CONTRIBUTING.md          ← How to contribute
```

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/drop-pod.git
cd drop-pod
```

### 2. Set Up the Raspberry Pi Zero 2W

```bash
# Flash Raspberry Pi OS Lite (64-bit) onto SD card
# Enable SSH, I2C, SPI, Camera in raspi-config

# On the Pi:
sudo apt update && sudo apt install -y python3-pip python3-opencv libopencv-dev
cd /home/pi
git clone https://github.com/your-org/drop-pod.git
cd drop-pod/software
pip3 install -r requirements.txt

# Edit config before first run
nano config.py
```

### 3. Configure the Flight Controller

```
1. Flash ArduPlane latest stable to your F405
2. Open Mission Planner → Full Parameter List
3. Load firmware/params/drop_pod.param
4. Calibrate: accelerometer, compass, radio
5. Set SERVO1..4 outputs to match your fin wiring
```

### 4. Connect Telemetry

```bash
# On ground laptop:
mavproxy.py --master=/dev/ttyUSB0 --baudrate=57600 --out=udp:127.0.0.1:14550
# Open Mission Planner → connect UDP 14550
```

### 5. Set Target Coordinates

```python
# In software/config.py:
TARGET_LAT  = 33.5731  # Decimal degrees
TARGET_LON  = -7.5898
TARGET_ALT  = 0.0      # MSL in metres (ground elevation)
```

### 6. Pre-Flight Checklist

See [docs/SAFETY.md](docs/SAFETY.md) for complete pre-flight checklist.

---

## Wiring Guide

See [hardware/wiring/wiring_diagram.md](hardware/wiring/wiring_diagram.md) for complete pinout.

Quick reference:

```
F405 FC                     RPi Zero 2W
──────────                  ──────────
TX1 (UART1) ─────────────► RX (GPIO15 / UART0)
RX1 (UART1) ◄───────────── TX (GPIO14 / UART0)
GND ─────────────────────── GND

F405 FC                     ELRS Receiver
──────────                  ─────────────
RX2 (UART2) ◄───────────── SBUS OUT
5V BEC ─────────────────── 5V
GND ─────────────────────── GND

F405 FC                     u-blox M10 GPS
──────────                  ──────────────
TX3 (UART3) ─────────────► RX
RX3 (UART3) ◄───────────── TX
5V ─────────────────────── 5V
GND ─────────────────────── GND

F405 FC                     Servos (×4 fins + 1 latch)
──────────                  ──────────────────────────
S1 ────────────────────────► FIN TOP (signal)
S2 ────────────────────────► FIN BOTTOM (signal)
S3 ────────────────────────► FIN LEFT (signal)
S4 ────────────────────────► FIN RIGHT (signal)
S5 ────────────────────────► LATCH SERVO (on carrier aircraft)
Servo BEC 5V ──────────────► All servo 5V rails (common)
GND ───────────────────────► All servo GND (common)
```

---

## Configuration

All mission-tunable parameters live in `software/config.py`:

```python
# ── MISSION ──────────────────────────────────────────────
TARGET_LAT          = 33.5731       # Target latitude
TARGET_LON          = -7.5898       # Target longitude
TARGET_ALT_MSL      = 0.0           # Ground elevation MSL (m)

# ── REACHABILITY ─────────────────────────────────────────
GLIDE_RATIO         = 4.0           # Conservative glide ratio
SAFETY_MARGIN       = 0.85          # Use only 85% of max range
MAX_WIND_SPEED      = 8.0           # m/s — abort above this

# ── PHASE TRANSITIONS ────────────────────────────────────
CAMERA_ACTIVATE_AGL = 40.0          # metres — switch to optical
MIN_LOCK_CONFIDENCE = 0.80          # 0.0–1.0, red carpet lock threshold

# ── VISION ───────────────────────────────────────────────
CAM_FOV_H_DEG       = 102.0         # Camera horizontal FOV
CAM_FOV_V_DEG       = 67.0          # Camera vertical FOV
CAM_RESOLUTION      = (1280, 720)   # Capture resolution
CAM_FPS             = 30            # Target frame rate
HSV_RED_LOW_1       = (0,   120, 80)    # Red mask range 1 lower
HSV_RED_HIGH_1      = (12,  255, 255)   # Red mask range 1 upper
HSV_RED_LOW_2       = (165, 120, 80)    # Red mask range 2 lower
HSV_RED_HIGH_2      = (180, 255, 255)   # Red mask range 2 upper
MIN_CARPET_AREA_PX  = 800           # Min blob pixels to count as lock

# ── GUIDANCE GAINS ───────────────────────────────────────
KV_LATERAL          = 0.4           # Vision lateral correction gain
KV_PITCH            = 0.15          # Vision pitch correction gain

# ── COMMUNICATION ────────────────────────────────────────
FC_UART_PORT        = "/dev/serial0"
FC_UART_BAUD        = 115200
TELEM_BAUD          = 57600
HEARTBEAT_INTERVAL  = 0.5           # seconds
```

---

## Flight Operations

### Pre-Mission Checklist (Field)

```
□ Battery voltage > 12.0V (3S full = 12.6V)
□ GPS 3D fix acquired, HDOP < 2.0
□ All 4 fins deflect correctly (servo test)
□ Camera feed active, red carpet detected in bench test
□ Telemetry link established on GCS
□ Target coordinates loaded and verified
□ Red carpet placed at target, cushion on top
□ Drop zone clear of personnel (minimum 30m radius)
□ Weather: wind < 8 m/s, no rain
□ Carrier aircraft pre-flight complete
□ Carrier release servo tested (WITHOUT pod attached)
```

### Drop Sequence

```
1. Carrier aircraft takes off, climbs to mission altitude (min 60m AGL)
2. Pilot flies over or near drop zone
3. GCS operator confirms pod GPS position and range
4. Operator sends: ARM command (TX Ch7 HIGH or GCS button)
5. GCS shows: "POD ARMED — REACHABILITY CHECK ACTIVE"
6. If target in range: GCS shows "IN RANGE — SAFE TO DROP"
7. Operator sends: DROP command (TX Ch8 HIGH or GCS button)
8. Pod releases, begins GPS-guided descent
9. At 40m AGL: GCS shows "CAMERA ACTIVE"
10. At lock: GCS shows "TARGET LOCKED — [confidence]%"
11. Pod impacts cushion on red carpet
12. GCS shows "LANDED" (accel spike detected)
```

### GCS Commands (MAVLink)

| Action | Mission Planner | MAVProxy CLI |
|--------|----------------|-------------|
| ARM | Aux1 HIGH button | `param set RELAY_PIN1 1` |
| DROP | Aux2 HIGH button | `do_set_relay 1 1` |
| ABORT | Abort button | `mode GUIDED` |
| Update target | Right-click map → Set target | `guided LAT LON ALT` |

---

## Tuning Guide

See [docs/TUNING.md](docs/TUNING.md) for full procedure. Key steps:

1. **Bench test**: Verify all servos zero correctly with no power-on drift
2. **Hand-drop test**: Drop from 2m by hand. Verify fins stabilise attitude within 0.5s
3. **Low-altitude drop**: 15–20m from a tall pole or drone. Verify GPS tracks target
4. **Vision bench**: Move red carpet under camera. Verify centroid tracks correctly at 1m, 3m, 5m
5. **Full mission**: 60m+ drop with camera active at 40m. Evaluate impact accuracy

---

## Safety & Legal

 **Read [docs/SAFETY.md](docs/SAFETY.md) before any field test.**

- This system drops a ~650g object from altitude. Treat it as a **projectile**.
- Always operate in a **cleared, controlled area** with ground personnel outside the drop radius.
- **National regulations apply.** In EU: EASA UAS open/specific category rules. In the US: FAA Part 107 may require a waiver for dropping objects.
- Use the two-step ARM → DROP command sequence. Never skip ARM.
- The reachability check is a safety gate — **do not bypass it in code**.

---

## Roadmap

### Phase 1 — Current (This Repo)
- [x] GPS macro-approach guidance
- [x] Nose-camera optical red carpet lock
- [x] 4-fin canard attitude control
- [x] RC + GCS dual command interface
- [x] Reachability check with automatic abort
- [x] Nose-impact delivery (cushion-assisted)

### Phase 2 — Next
- [ ] RTK GPS for cm-level approach accuracy
- [ ] YOLOv8-nano detector replacing HSV (shadow-robust)
- [ ] LiDAR AGL sensor (TFMini) for precise altitude
- [ ] Controlled flare manoeuvre for softer landing

### Phase 3 — Future
- [ ] Two-way camera feed via 5.8GHz VTX
- [ ] Swappable payload bay
- [ ] Multiple concurrent pods on one carrier
- [ ] Sim-to-real training loop (Gazebo/AirSim)

---

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

PRs welcome in these areas:
- Better PID initial values (share your tuning data)
- Alternative vision algorithms
- 3D model improvements
- Documentation translations
- Simulation environments (Gazebo/AirSim configs)

---
## License

MIT License — see [LICENSE](LICENSE). Free to use, modify, and build. Please credit the project.

---

<p align="center">
  <strong>DROP POD — OPEN SOURCE PRECISION DELIVERY</strong><br/>
  <em>If it can be guided, it can be landed precisely.</em>
</p>
