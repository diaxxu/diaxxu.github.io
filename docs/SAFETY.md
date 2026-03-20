# Safety Guide & Pre-Flight Checklist
## Drop Pod — Mandatory Reading Before Any Field Operation

---

> **This document must be read by every person involved in a drop pod operation.**
> The pod is a guided projectile. Treat it with the same respect as any object launched from height.

---

## Risk Assessment

| Hazard | Severity | Probability | Mitigation |
|--------|----------|------------|------------|
| Pod impacts person | Critical | Low (with protocols) | Ground exclusion zone, ARM verification |
| Pod drifts off-target | Moderate | Medium | Reachability check, wind limit |
| Battery fire (LiPo) | High | Low (with handling protocols) | Safe LiPo procedures, check voltage before flight |
| GPS signal loss | Moderate | Low | Watchdog: degrades gracefully, no abrupt changes |
| Accidental release on ground | Critical | Low | Two-stage ARM→DROP, arming check |
| Camera miss / wrong target | Moderate | Medium | Bench-test HSV thresholds before each field op |

---

## Exclusion Zone

**Before any drop:**

```
                    ┌─────────────┐
                    │  TARGET     │ ← Red carpet + cushion
                    │  ZONE       │
                    └─────────────┘
    ←──────── MINIMUM 30m RADIUS ────────►
    
    NO PERSONNEL inside this radius
    during any DROP operation.
    
    Exception: the person who placed the cushion.
    They must exit the zone before ARM command is issued.
```

Establish the exclusion zone with:
- Physical barrier (cones, tape)
- Radio communication with all team members
- Visual confirmation before ARM

---

## Two-Stage Safety Gates

The system has two mandatory gates before the pod can be released:

```
GATE 1 — ARM
  Required: Explicit ARM command (TX CH7 HIGH or GCS button)
  System checks: GPS fix valid, HDOP < 3.0
  On pass: system enters ARMED state, monitors reachability
  
  ↓ (only after GATE 1 passes)
  
GATE 2 — REACHABILITY CHECK (automatic, runs on DROP command)
  Checks: horizontal distance ≤ (alt_agl × glide_ratio × 0.85)
  Checks: altitude ≥ MIN_RELEASE_AGL (40m default)
  On fail: DROP is silently rejected, GCS notified
  On pass: latch fires, mission begins
```

**Never modify the reachability check logic to force it to pass.** It exists to prevent the pod from landing outside the target area.

---

## Pre-Flight Checklist

Run this checklist in order before every flight. No shortcuts.

### A — Site Preparation
```
□ Landing zone surveyed, obstruction-free (30m radius)
□ Red carpet placed flat, no wrinkles or folds
□ Impact cushion centred on red carpet
□ Target GPS coordinates measured and loaded into config.py
□ Ground personnel briefed on exclusion zone
□ Communication established with all team members
□ First aid kit on site
□ Emergency abort procedure agreed upon
```

### B — Weather Check
```
□ Wind speed: measured at site (anemometer or phone app)
  - Green: < 4 m/s
  - Yellow: 4–6 m/s (reduced accuracy expected)
  - Red/No-fly: > 8 m/s  ← ABORT
□ No rain forecast during operation window
□ Visibility > 500m (can see pod throughout flight)
□ Sun angle not directly into pilot's/camera's field of view
```

### C — Electrical Check (Before Mounting on Aircraft)
```
□ LiPo voltage ≥ 12.3V (3S — do not fly below 12.0V)
□ LiPo shows no swelling, no damage to leads
□ All servo connectors seated and secure
□ GPS antenna seated and not cracked
□ Camera lens clean and clear
□ ELRS receiver LED indicating bound status
□ SiK radio LED indicating link to GCS
```

### D — Software Check
```
□ Pi mission manager started: python3 software/mission_manager.py
□ GCS Mission Planner connected, telemetry streaming
□ GPS 3D fix acquired: HDOP < 2.0, sats ≥ 8
□ Target coordinates verified on GCS map (marker at correct location)
□ Reachability check tested from ground (should say OUT OF RANGE from ground)
□ Vision test: camera feed active, red carpet detected in bench test
□ RC bind confirmed: all channels responding on GCS RC screen
□ ARM channel (CH7) verified: stick/switch moves correct channel
□ DROP channel (CH8) verified: stick/switch moves correct channel
□ ABORT channel (CH9) verified: accessible, tested
```

### E — Carrier Aircraft Check
```
□ Carrier aircraft pre-flight complete per its own checklist
□ Latch servo tested with pod: PIN ENGAGED, pod does not slide out
□ Latch servo tested: PIN RETRACTED at DROP command (test WITHOUT pod first)
□ Pod re-installed, pin engaged, pull-test: pod does not release under 5N pull
□ Servo extension cable has adequate slack, secured at regular intervals
□ Pod CG re-verified after installation on carrier
□ Combined carrier + pod CG acceptable for carrier aircraft flight envelope
```

---

## In-Flight Abort Procedure

If at any point during the flight the operator decides to abort:

1. **ABORT command**: TX CH9 HIGH or GCS Abort button
2. This transitions the pod to ABORT state: all optical corrections disabled, pod holds last attitude
3. **If pod has already been released**: it will continue to descend with no guidance correction (flat attitude hold)
4. **If release has NOT happened**: do not issue DROP — fly carrier back and land with pod attached

If carrier aircraft loses control with pod attached:
- The pod will remain attached until latch is actively commanded
- Only command DROP if carrier is already in a safe recovery trajectory
- Otherwise land carrier with pod attached

---

## LiPo Safety Protocol

```
CHARGING
  - Never charge unattended
  - Use balance charger (all cells must balance to ±0.05V)
  - Max charge rate: 1C (1.0A for 1000mAh)
  - Never charge below 3.0V/cell (cell may be permanently damaged)
  
STORAGE
  - Store at 3.8V/cell (storage charge)
  - Store in LiPo-safe bag or metal ammo box
  - Never in hot vehicle (> 40°C)
  - Inspect before each use for swelling

DISPOSAL
  - Discharge completely to 3.0V/cell using a discharge resistor
  - Submerge in salt water for 2 weeks (renders cell inert)
  - Then dispose as electronic waste
  
IN-FLIGHT LOW BATTERY
  - GCS will alert at 3.4V/cell
  - Abort mission, fly carrier back immediately
  - Never fully deplete mid-flight — over-discharge destroys cells permanently
```

---

## Regulatory Notes

> **This section does not constitute legal advice. Consult your national aviation authority.**

| Country | Authority | Key Requirement |
|---------|-----------|----------------|
| Morocco | ANAC | UAS ops require authorisation; dropping objects may need specific waiver |
| EU | EASA | Specific category UAS ops; dropping objects requires PDRA or STS |
| USA | FAA | Part 107 rule 107.23 prohibits dropping objects that create hazard — waiver needed |
| UK | CAA | OSC required for dropping objects from UAS |

**General principles (apply everywhere):**
- Always operate in unpopulated areas
- Never drop over or near roads, buildings, or crowds
- Maintain Visual Line of Sight (VLOS) with both carrier and pod
- Log all flights (date, location, altitude, operator)
- Carry third-party liability insurance

---

## Emergency Contacts

Fill in before field operations:

```
Local ATC / NOTAM office: _______________________
Team lead phone:          _______________________
Nearest hospital:         _______________________
Emergency services:       _______________________
```

---

## Incident Reporting

If the pod impacts outside the target zone, impacts infrastructure, or causes any injury:

1. Ensure all personnel are safe
2. Do not move any wreckage
3. Photograph the scene
4. Record: time, weather conditions, telemetry log, last known GPS position
5. Report to national aviation authority per their incident reporting procedure
6. Open a GitHub issue in this repository with logs (anonymised if needed)
