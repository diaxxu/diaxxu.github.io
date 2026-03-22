# 3D Printed Parts — Print Settings & Assembly Guide
## Drop Pod Hardware Revision A

---

## Printer Requirements

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Build volume | 100×100×100mm | 200×200×200mm |
| Layer resolution | 0.2mm | 0.15mm |
| Extruder temp | 230°C (PETG) | 240°C |
| Bed temp | - | 80°C |
| Bed surface | PEI/glass | PEI textured |

---

## Material

**Use PETG for ALL structural parts.** Do NOT use PLA.

| Property | PLA | PETG |
|----------|-----|------|
| Impact resistance | Low | High |
| Heat deflection | ~60°C (warps in sun) | ~80°C |
| Layer adhesion | Medium | High |
| Price | Cheaper | Slightly more |

Impact resistance is critical — the pod noses into a cushion at speed. PETG absorbs impact energy significantly better than PLA.

---

## Parts List

### Part 01: `nose_camera_mount.stl`
**The nose of the pod — this IS the camera housing.**

```
Description : Cylindrical nose section, ø80mm OD, 85mm long.
              Camera Module 3 Wide seats in a recessed pocket at
              the very tip. CSI ribbon exits through a slot in
              the side wall toward the avionics bay.
              
Function    : Camera housing + aerodynamic nose fairing.
              The camera lens is flush with the front face.
              
Print settings:
  - Layer height : 0.15mm (critical for lens pocket accuracy)
  - Infill       : 40% gyroid
  - Walls        : 4 perimeters
  - Top/bottom   : 5 layers
  - Supports     : YES — needed for camera pocket recess
  - Orientation  : Print nose-tip UP for best surface quality on lens face
  
Post-processing:
  - Sand camera pocket with 400-grit until Camera Module 3
    sits flush with no wobble
  - Apply thin bead of hot glue around camera module edges
    to lock in place (do not glue over lens)
  - Thread CSI ribbon through side slot before gluing camera
  - Bond to CF tube with 30-min epoxy. Align with fin mount slots.
```

### Part 02: `fin_mount_forward.stl`
**Servo bay ring — slides into CF tube, holds 4 servos.**

```
Description : Ring-shaped collar, ø80mm OD to match CF tube ID.
              Four servo pockets, cruciform pattern at 90° spacing.
              Servo horns face inward.
              
Print settings:
  - Layer height : 0.2mm
  - Infill       : 60% gyroid (strength critical)
  - Walls        : 5 perimeters
  - Top/bottom   : 5 layers
  - Supports     : Minimal — servo pockets may need tree supports
  - Orientation  : Print in the mounting orientation (ring flat on bed)

Post-processing:
  - Test-fit all 4 servos before final assembly
  - Drill out M3 screw holes with 3.2mm drill bit if tight
  - Apply Loctite 243 to all servo mount screws
```

### Part 03: `fin_blade.stl`
**Canard fin — print 4 identical copies.**

```
Description : Trapezoidal fin blade, 55mm span × 40mm chord.
              NACA 0009 profile (symmetrical, zero camber).
              Servo horn attachment slot at root.
              Pushrod clevis attachment hole at trailing edge root.
              
Print settings:
  - Layer height : 0.15mm (profile accuracy)
  - Infill       : 30% triangles (strong in bending)
  - Walls        : 4 perimeters
  - Top/bottom   : 4 layers
  - Supports     : None needed
  - Orientation  : Print FLAT on bed (fin in horizontal plane)
  - Note         : Print ALL FOUR in same batch for matching mass

Post-processing:
  - Sand trailing edge to sharp edge with 400-grit
  - Check all 4 fins have same mass (±0.5g). Add tiny epoxy
    drops to lighter fins to balance.
  - Attach servo horn to root slot. Use M2 screw + Loctite.
```

### Part 04: `servo_bay_cover.stl`
**Aesthetic/protective cover over the servo bay area.**

```
Description : Thin cylindrical skin section, 80mm OD × 50mm long.
              Four slots cut for fin root protrusion.
              Snaps over fin_mount_forward.
              
Print settings:
  - Layer height : 0.2mm
  - Infill       : 20%
  - Walls        : 3 perimeters
  - Supports     : None
  - Orientation  : Vertical (cylinder axis vertical on bed)
```

### Part 05: `avionics_tray.stl`
**Internal mounting tray for FC, Pi, GPS.**

```
Description : Rectangular tray, 70mm × 150mm × 10mm.
              Slots for M3 nylon standoffs at FC and Pi footprints.
              Slides into CF tube and is retained by M3 screws
              through the CF tube wall.
              
Print settings:
  - Layer height : 0.2mm
  - Infill       : 40% gyroid
  - Walls        : 4 perimeters
  - Supports     : None
  - Orientation  : Flat on bed

Component placement on tray (front to back):
  [0mm]   GPS module (UART3, antenna pointing up through hole in tray)
  [30mm]  F405 FC (SPI/I2C sensors connect here)
  [80mm]  RPi Zero 2W (UART0 → FC UART1)
  [130mm] SiK radio module
```

### Part 06: `power_bay.stl`
**Battery bay and BEC holder — rear section of pod.**

```
Description : Cylindrical section, 80mm OD × 90mm long.
              Battery cradle sized for 3S 1000mAh (18×35×72mm approx).
              Two BEC holders on sides.
              XT30 port slot at rear.
              
Print settings:
  - Layer height : 0.2mm
  - Infill       : 35%
  - Walls        : 4 perimeters
  - Supports     : YES for battery cradle lip
  - Orientation  : Print with XT30 port face UP

Battery retention:
  - Two Velcro straps through slots in cradle
  - Do NOT rely on friction alone — battery must not shift under impact
```

### Part 07: `tail_ballast_cap.stl`
**Rear end cap with ballast weight pocket.**

```
Description : Domed end cap, 80mm OD.
              Central ballast pocket for tungsten or steel slug.
              Plug-in fit with rubber O-ring for retention.
              
Print settings:
  - Layer height : 0.2mm
  - Infill       : 50% (structural for ballast retention)
  - Walls        : 5 perimeters
  - Supports     : None
  - Orientation  : Dome up on bed

CG Note:
  Target CG location: 30% of total body length from nose.
  Add/remove ballast weight in this cap to tune CG.
  A nose-heavy pod is more stable; tail-heavy causes tumbling.
  Test CG on assembled pod: balance on a round rod at 30% point.
```

### Part 08: `wing_saddle_mount.stl`
**Mounting saddle that attaches to carrier aircraft wing.**

```
Description : Wing saddle, curved to fit wing profile of carrier.
              Two M4 bolt through-holes for wing attachment.
              Pod-rail slot (20mm wide) for pod to slide in.
              Latch retention pin hole (M3 diameter).
              
Print settings:
  - Layer height : 0.15mm (mounting accuracy)
  - Infill       : 80% (maximum strength — structural)
  - Walls        : 6 perimeters
  - Top/bottom   : 6 layers
  - Supports     : YES — curved base needs support
  - Material     : PETG (or Carbon-fibre PETG for extra strength)

IMPORTANT: This part takes the full impact load of separation.
Print with maximum infill and wall count. Inspect after every flight.
Replace if any cracking appears.
```

---

## Assembly Order

```
1. Print all parts (2–3 hour total print time)
2. Test-fit nose_camera_mount to CF tube — should be snug, not loose
3. Install servos into fin_mount_forward ring
4. Thread pushrods through fin slots, attach to servo horns (Z-bend)
5. Attach fin blades to pushrod clevis ends
6. Slide fin_mount_forward + fins assembly into CF tube front
7. Install avionics_tray with FC, Pi, GPS into CF tube mid-section
8. Install power_bay with battery and BECs at rear
9. Install tail_ballast_cap — add initial ballast (50g)
10. Attach nose_camera_mount (with camera already installed)
11. Route all cables: UART (FC→Pi), servo wires, GPS, power
12. BEFORE sealing: CG check. Balance point must be at 28-32% from nose
13. Adjust ballast until CG is correct
14. Final assembly: epoxy all section joints
15. Install on wing_saddle_mount on carrier aircraft
```

---

## CG Check Procedure

```
1. Assemble pod completely with battery at its planned position
2. Balance pod on a 5mm round rod at 95mm from nose (30% of 320mm)
3. Pod should balance level or very slightly nose-heavy
4. If tail-heavy: move battery forward, or add ballast to nose_camera_mount
5. If very nose-heavy: move battery rearward, or reduce ballast weight
6. Never fly tail-heavy — this causes tumbling and loss of control
```

Target CG: **95–105mm from nose tip**

---

## Post-Print Finishing

1. **Deburr** all holes with a 3mm drill bit by hand
2. **Sand** any rough layer lines on aerodynamic surfaces with 400-grit
3. **Test-fit** every servo before final assembly
4. **Hot-glue** all cable routing to prevent vibration chafing
5. **Mark** each fin with a number (1-4) and corresponding servo number
6. **Photograph** internal wiring before closing pod — invaluable for troubleshooting
