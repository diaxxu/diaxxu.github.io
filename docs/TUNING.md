# PID Tuning Guide
## Drop Pod — Control System Calibration

---

## Philosophy

**Never tune on a real drop from altitude before completing all lower-risk steps.**

Follow this progression:

```
Level 0: Bench test (no flight, no movement)
Level 1: Hand-drop from 1–2m
Level 2: Drop from pole/crane at 10–20m
Level 3: Full aircraft drop at 60–100m
```

Only move to the next level when the current level is fully verified.

---

## Level 0 — Bench Tests

### 0.1 Servo Zero Calibration

Before ANY tuning, all fins must be perfectly zeroed:

```bash
# In Mission Planner:
# Config → Servo Output → Test
# Set each servo (S1–S4) to 1500μs
# Each fin should be FLUSH with the tube body
# If not flush: adjust servo arm position on spline
```

Acceptable tolerance: ±0.5° from flush. Any more and you'll have a persistent roll/pitch offset.

### 0.2 Fin Deflection Direction

Run this test and compare to expected:

| Servo command | Expected fin deflection | Expected pod response |
|--------------|----------------------|----------------------|
| S3 = 1700μs (FIN TOP up) | Top fin deflects left (into airstream) | Pitch nose up |
| S3 = 1300μs (FIN TOP down) | Top fin deflects right | Pitch nose down |
| S4 = 1700μs (FIN BOTTOM) | Bottom fin deflects opposite to top | Pitch nose up (same as top) |
| S1 = 1700μs (FIN LEFT up) | Left fin deflects | Roll right |
| S2 = 1700μs (FIN RIGHT) | Right fin deflects opposite to left | Roll right (same) |

If any fin moves the wrong way: set `SERVOx_REVERSED = 1` for that servo in ArduPlane params.

### 0.3 Control Mixing Verification

In ArduPlane, roll pilot input should move S1+S2 differentially.
Pitch pilot input should move S3+S4 symmetrically.

Test with TX in MANUAL mode:
- Pitch stick forward: both FIN TOP and FIN BOTTOM deflect to pitch nose down
- Roll stick right: FIN LEFT and FIN RIGHT deflect differentially to roll right

### 0.4 IMU Axis Verification

Mount pod on flat surface. Check GCS:
- Roll = 0°, Pitch = 0°, Yaw = any value ✓
- Tilt nose up 30°: Pitch shows +30° ✓
- Roll right 30°: Roll shows +30° ✓

If any axis is inverted or swapped: check AHRS_ORIENTATION param in ArduPlane.

---

## Level 1 — Hand Drop Tests (1–2m height)

### 1.1 Attitude Stabilisation Test

Hold pod horizontally, tip nose down 20°, then release:
- Pod should correct back toward level attitude within 1–2 seconds
- If it oscillates wildly: reduce `RLL_RATE_P` and `PTCH_RATE_P` by 20%
- If it barely corrects: increase P gains by 20%

### 1.2 Step Response Tuning

With pod in hand (simulate holding it during descent), command roll input:
- Response should be: fast initial movement, no overshoot, settles quickly
- Oscillation = too much P or too little D
- Sluggish = not enough P
- Steady-state error = not enough I

### 1.3 Starting PID Values

Use these as the initial starting point:

```
# Pitch Rate Loop
PTCH_RATE_P = 0.08
PTCH_RATE_I = 0.020  
PTCH_RATE_D = 0.004
PTCH_RATE_FF = 0.0

# Pitch Angle Loop  
PTCH2SRV_P = 1.5
PTCH2SRV_I = 0.2
PTCH2SRV_D = 0.04

# Roll Rate Loop
RLL_RATE_P = 0.10
RLL_RATE_I = 0.020
RLL_RATE_D = 0.004

# Roll Angle Loop
RLL2SRV_P = 1.8
RLL2SRV_I = 0.2
RLL2SRV_D = 0.04
```

---

## Level 2 — Low-Altitude Drops (10–20m)

Use a tall ladder, crane, or first-floor window ledge. Drop pod by hand.

### 2.1 What to Observe

1. **Separation stability**: does pod immediately stabilise? Should be level within 0.5s
2. **Directional bias**: does pod consistently drift left/right or nose up/down?
3. **Oscillation**: does pod "wag" or "hunt" during descent?
4. **GPS tracking**: does pod turn toward the target waypoint?

### 2.2 Common Issues and Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Rolls immediately on release | Servo zero offset | Re-zero all servos |
| Pitches nose-up consistently | CG too far back | Move battery forward |
| High-frequency oscillation | Too much D or P | Reduce D first, then P by 10% |
| Slow response to roll commands | Too little P | Increase RLL_RATE_P by 15% |
| Oscillates and diverges | Unstable (too much P) | Reduce P gains 30%, restart |
| No GPS correction | Wrong mode or WP not set | Check GUIDED mode, verify WP set |

### 2.3 Tuning Procedure (Ziegler-Nichols Simplified)

For each axis independently:
1. Set I and D to zero
2. Increase P until steady oscillation appears (critical gain Kc)
3. Record oscillation period Tc
4. Set: P = 0.6×Kc, I = 1.2×Kc/Tc, D = 0.075×Kc×Tc
5. Reduce all by 20% for safety margin

---

## Level 3 — Full Altitude Drops (60m+)

Only proceed here when Level 2 shows stable, well-damped attitude control.

### 3.1 First Full Drop Protocol

- Start at 60m AGL (minimum)
- Target offset: 50m horizontal (conservative)
- Camera threshold: 40m AGL
- Observe via GCS: track pod state transitions

### 3.2 Vision System Tuning

If camera locks poorly:

```python
# In config.py — adjust HSV thresholds:
# Make red detection more permissive if missing carpet:
HSV_RED_LOW_1  = (0,  100, 60)   # Lower S and V thresholds
HSV_RED_HIGH_1 = (15, 255, 255)  # Wider hue range

# Make more restrictive if getting false positives (other red objects):
HSV_RED_LOW_1  = (0,  150, 100)  # Higher saturation required
HSV_RED_HIGH_1 = (10, 255, 255)  # Narrower hue range
```

Run `python3 software/vision.py` on ground with the carpet lit by the same lighting conditions expected in field to tune thresholds before flight.

### 3.3 Optical Gain Tuning

```python
# In config.py:
# If pod overshoots target during optical phase (oscillates around target):
KV_LATERAL = 0.25  # Reduce from 0.4

# If pod doesn't track fast enough:
KV_LATERAL = 0.5   # Increase from 0.4

# Pitch correction should almost always be smaller than lateral:
KV_PITCH = 0.10    # Further reduce if any instability appears
```

### 3.4 Accuracy Evaluation

After each drop:
1. Measure distance from pod nose-impact to carpet centre
2. Log: drop altitude, wind speed, measured landing error, direction of error
3. Build a correction table across altitudes

| Drop Altitude | Wind | Expected CEP | Notes |
|-------------|------|-------------|-------|
| 60m | <2 m/s | ≤ 2m | Optical phase dominant |
| 100m | <2 m/s | ≤ 3m | GPS phase longer |
| 60m | 5 m/s | ≤ 5m | Wind compensation |

---

## L1 Navigation Tuning

The L1 controller governs how aggressively the pod turns toward the target during GPS phase.

```
NAVL1_PERIOD (default: 18)
  - Lower = more aggressive tracking, tighter turns
  - Higher = smoother, more gentle arcs
  - For pod descent (fast, no loitering): 12–16 is appropriate
  
NAVL1_DAMPING (default: 0.75)
  - Lower = more oscillation around track
  - Higher = overdamped, sluggish
  - Typically leave at 0.75
```

---

## Log Analysis

Every flight generates ArduPlane logs (.bin) on the FC SD card.

Download and analyse with Mission Planner → DataFlash Log → Review:
- **ATT**: Actual vs desired attitude (RollIn vs Roll, PitchIn vs Pitch)
- **GPS**: Position accuracy, HDOP
- **RCIN**: RC channel inputs (verify ARM/DROP on correct channels)
- **MODE**: Flight mode changes (should see AUTO or GUIDED during descent)

Key signature of well-tuned system:
```
ATT.RollIn ≈ ATT.Roll  (small error, no oscillation)
ATT.PitchIn ≈ ATT.Pitch (small error, no oscillation)
GPS tracking: smooth approach to WP, not hunting
```
