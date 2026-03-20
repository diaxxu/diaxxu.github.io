# Wiring Diagram & Pinout Reference
## Drop Pod — Hardware Revision A

---

## Overview

The pod uses two power rails and three main communication buses:

| Bus | Protocol | Parties |
|-----|----------|---------|
| UART1 | MAVLink v2 @ 115200 | F405 FC ↔ RPi Zero 2W |
| UART2 | SBUS @ 100000 inv | ELRS Receiver → F405 FC |
| UART3 | MAVLink NMEA @ 38400 | u-blox GPS → F405 FC |
| SPI1 | SPI @ 8MHz | F405 FC → ICM-42688 IMU |
| I2C1 | I2C @ 400kHz | F405 FC → BMP388 Baro |
| CSI-2 | MIPI 2-lane | RPi Camera Module 3 → RPi Zero 2W |

---

## Power Architecture

```
3S LiPo (11.1V) ────────────── XT30 ─────────────────────────────
         │                                                        │
         ├── Pololu BEC #1 (5V / 2.2A) ──────────────────────────┤
         │   (Logic Rail)                                         │
         │   ├── F405 FC 5V input                                 │
         │   ├── RPi Zero 2W 5V (via GPIO pin 2 or USB-C)        │
         │   ├── u-blox GPS 5V                                    │
         │   └── SiK Radio 5V                                     │
         │                                                        │
         └── Pololu BEC #2 (5V / 2.2A) ──────────────────────────┤
             (Servo Rail)                                         │
             ├── Servo 1 (FIN TOP)    5V signal common           │
             ├── Servo 2 (FIN BOTTOM) 5V signal common           │
             ├── Servo 3 (FIN LEFT)   5V signal common           │
             ├── Servo 4 (FIN RIGHT)  5V signal common           │
             └── Servo 5 (LATCH)      5V signal common           │
                                                                  │
All GND ──────────────────────────────────────────────── GND ────┘
```

> ⚠️ **Critical**: The two BECs must share a common GND. Connect both BEC GND wires and the LiPo GND together. Never power servos from the same BEC as the FC/Pi — servo transients will reset/damage logic.

---

## Matek F405-WING Pinout

```
Matek F405-WING
┌─────────────────────────────────────┐
│ S1  ─────── FIN LEFT servo signal   │
│ S2  ─────── FIN RIGHT servo signal  │
│ S3  ─────── FIN TOP servo signal    │
│ S4  ─────── FIN BOTTOM servo signal │
│ S5  ─────── LATCH servo signal      │
│                                     │
│ UART1 TX ── RPi GPIO15 (RX)         │  MAVLink to companion
│ UART1 RX ── RPi GPIO14 (TX)         │
│ UART1 GND ─ RPi GND                 │
│                                     │
│ UART2 RX ── ELRS SBUS OUT           │  RC receiver (inverted SBUS)
│                                     │
│ UART3 TX ── GPS RX                  │  u-blox GPS
│ UART3 RX ── GPS TX                  │
│                                     │
│ SPI SCK  ── ICM-42688 SCK           │  External IMU (if not using onboard)
│ SPI MOSI ── ICM-42688 SDI           │
│ SPI MISO ── ICM-42688 SDO           │
│ CS1      ── ICM-42688 CS            │
│                                     │
│ I2C SCL  ── BMP388 SCL              │  Barometer
│ I2C SDA  ── BMP388 SDA              │
│                                     │
│ UART4 TX ── SiK Radio RX            │  Telemetry to GCS
│ UART4 RX ── SiK Radio TX            │
│                                     │
│ BAT+     ── LiPo V+ (voltage sense) │
│ GND      ── Common GND              │
│ 5V in    ── BEC #1 5V output        │
│ VCC servo── BEC #2 5V output        │
└─────────────────────────────────────┘
```

---

## Raspberry Pi Zero 2W Pinout

```
RPi Zero 2W — 40-Pin Header
┌───────────┬─────┬─────┬──────────────┐
│ Function  │ Pin │ Pin │ Function     │
├───────────┼─────┼─────┼──────────────┤
│ 3.3V      │  1  │  2  │ 5V           │ ← 5V from BEC #1
│ GPIO2 SDA │  3  │  4  │ 5V           │
│ GPIO3 SCL │  5  │  6  │ GND          │ ← Common GND
│ GPIO4     │  7  │  8  │ GPIO14 (TX)  │ ← UART0 TX → FC UART1 RX
│ GND       │  9  │ 10  │ GPIO15 (RX)  │ ← UART0 RX ← FC UART1 TX
│ ...       │ ... │ ... │ ...          │
└───────────┴─────┴─────┴──────────────┘

CSI Camera Port (bottom of board):
  ← RPi Camera Module 3 Wide (15-pin FFC ribbon cable)
  Ensure camera orientation: lens faces NOSE DIRECTION
  (forward/downward during pod descent)
```

**RPi UART Setup:**
```bash
# In /boot/config.txt:
enable_uart=1
dtoverlay=disable-bt   # Free up UART0 (disable Bluetooth)

# In /boot/cmdline.txt — remove:
# console=serial0,115200
```

---

## u-blox M10 GPS

```
u-blox M10 Breakout
┌─────────────────┐
│ VCC ─── 5V      │ ← BEC #1 5V
│ GND ─── GND     │
│ TX  ─── FC UART3 RX  │
│ RX  ─── FC UART3 TX  │
│ PPS ─── FC GPIO (optional, for time sync) │
│ Antenna: patch antenna facing UP in nose section │
└─────────────────┘
```

GPS Antenna Placement:
- Mount patch antenna flat, facing skyward (top of pod)
- 15mm aluminium ground plane behind antenna improves gain
- Keep at least 30mm away from any servos or high-current wires

---

## ELRS Receiver (e.g. BetaFPV ELRS Lite)

```
ELRS Receiver
┌──────────────┐
│ 5V  ── 5V    │ ← BEC #1
│ GND ── GND   │
│ SBUS─── FC UART2 RX (set SERIAL2_PROTOCOL = 23 for SBUS) │
└──────────────┘
```

> **Note**: SBUS is an inverted serial signal. Most ArduPlane FC boards auto-detect this. If not, use a hardware inverter (single NPN transistor circuit).

---

## SiK 915MHz Telemetry Radio

```
SiK Radio (Pod unit)
┌──────────────┐
│ 5V  ── 5V    │ ← BEC #1
│ GND ── GND   │
│ TX  ── FC UART4 RX  │
│ RX  ── FC UART4 TX  │
└──────────────┘

SiK Radio (GCS unit) → USB to laptop
Configure both radios with SiK firmware at same baud (57600)
Net ID must match between pair.
```

---

## Latch Servo (on Carrier Aircraft Wing)

```
CARRIER AIRCRAFT WING
┌─────────────────────────────────────┐
│ Release servo (9g)                  │
│   Signal ── FC S5 output            │ ← Long servo extension cable runs
│   5V     ── BEC #2 5V               │   from pod to wing mount point
│   GND    ── GND                     │
│                                     │
│ Retention pin: M3 × 20mm steel bolt │
│ Servo pulls: 8mm stroke to clear pin│
└─────────────────────────────────────┘

At PWM 1500μs (TRIM) → pin engaged, pod locked
At PWM 2000μs (MAX)  → pin retracted, pod released
```

---

## ICM-42688-P IMU (External, if FC onboard IMU is insufficient)

```
ICM-42688-P Breakout
┌──────────────┐
│ VCC ── 3.3V  │ ← FC 3.3V out
│ GND ── GND   │
│ SCK ── SPI SCK  │
│ SDI ── SPI MOSI │
│ SDO ── SPI MISO │
│ CS  ── SPI CS1  │
│ INT ── FC GPIO (optional interrupt) │
└──────────────┘

Mount on 3mm vibration dampening foam under FC.
Align axes: X = forward (toward nose), Y = right, Z = down.
```

---

## BMP388 Barometer

```
BMP388 Breakout
┌──────────────┐
│ VCC ── 3.3V  │
│ GND ── GND   │
│ SCL ── I2C SCL  │
│ SDA ── I2C SDA  │
└──────────────┘

Important: Place in a vented enclosure or expose to ambient air.
If sealed in fuselage, drill 1mm vent holes near sensor.
Cover vent holes with foam to block wind.
```

---

## Wire Gauge Recommendations

| Connection | Wire Gauge | Reason |
|-----------|-----------|--------|
| LiPo to BEC inputs | 22 AWG | Up to 3A continuous |
| BEC outputs to FC/Pi | 26 AWG | Low current logic |
| BEC #2 to servo common rail | 22 AWG | Peak servo current |
| Servo signal wires | 26 AWG | Signal only |
| GPS / Baro / IMU | 26 AWG silicone | Flexible signal |

Use **silicone-insulated** wire throughout — it remains flexible at low temperatures and resists vibration cracking.

---

## Wiring Checklist Before First Power-On

```
□ Both BEC input voltages correct (11.1V from LiPo)
□ Both BEC output voltages measured: 5.0V ± 0.1V
□ FC 5V rail measured: 5.0V ± 0.1V  
□ RPi 5V measured at GPIO pin 2: 5.0V ± 0.1V
□ All GND connections are continuous (test with multimeter)
□ No shorts between 5V rails and GND
□ No shorts between BEC #1 and BEC #2 output rails
□ Servo signal wires connected to correct FC output pins
□ UART wires: TX→RX and RX→TX (crossed correctly)
□ Camera ribbon cable seated fully in both connectors
□ GPS antenna facing upward, away from metal
□ All connectors hot-glued or zip-tied for vibration security
```
