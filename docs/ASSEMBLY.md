# Assembly Guide
## Drop Pod — Step-by-Step Build

---

## Before You Start

- Read the **entire guide** before starting. Understand each step fully.
- Lay out all components and verify against [BOM.csv](../../BOM.csv).
- Print all 3D parts before starting (see [hardware/stl/README.md](../stl/README.md)).
- Have these tools ready:
  - Soldering iron + 63/37 solder
  - 30-minute epoxy
  - Loctite 243 (threadlocker)
  - M2, M3 hex key set
  - Digital multimeter
  - Servo tester
  - Pliers (for Z-bending pushrods)
  - 3.2mm drill bit (for screw hole cleanup)
  - 400-grit sandpaper

---

## Phase 1 — Camera Nose Assembly

The camera IS the nose of the pod. This is the first and most critical assembly step.

```
STEP 1.1 — Camera Module Preparation
  - Unbox RPi Camera Module 3 Wide
  - Handle by edges only — do not touch sensor or lens
  - Attach 200mm CSI-2 ribbon cable to camera (locking tab faces lens side)
  - Test camera on RPi before installing: rpicam-still -o test.jpg

STEP 1.2 — Nose Section Print Inspection
  - Inspect nose_camera_mount.stl for print defects
  - Camera pocket must be free of support material — clean with tweezers
  - Test-fit camera module in pocket. Should seat flush with lens at nose tip
  - If too tight: sand pocket with 400-grit, test-fit again
  - If too loose: add thin strip of foam tape around camera edges

STEP 1.3 — Camera Installation
  - Thread CSI ribbon through side slot in nose section FIRST
  - Lower camera module into pocket (lens facing nose tip)
  - Verify lens is flush or 0.5mm recessed from nose face
  - Apply thin bead of hot glue around 4 camera module edges
  - DO NOT get glue on lens or ribbon connector
  - Let cure 5 minutes before handling

STEP 1.4 — Nose-to-Tube Bond
  - Sand the front 20mm of CF tube OD with 120-grit for epoxy adhesion
  - Mix 30-minute epoxy, apply thin layer inside nose section socket
  - Press nose section onto CF tube front
  - Rotate nose section to align fin slots with subsequent fin mount slots
  - Hold or tape in position for 30 minutes minimum
  - Allow full cure: 24 hours before loads
```

---

## Phase 2 — Fin & Servo Assembly

```
STEP 2.1 — Servo Preparation
  - Test all 4 servos with servo tester BEFORE installing
  - Command each servo to 1500μs (neutral). Verify servo arm is at 90° to body
  - If arm is not at 90°, remove arm, reposition on spline, reinstall
  - Apply Loctite 243 to servo arm M2 screw

STEP 2.2 — Servo Installation in Fin Mount Ring
  - Press each servo into pocket in fin_mount_forward ring
  - Servo label should face inward (toward tube centre)
  - Secure each servo with M2×8 screws + Loctite 243
  - Servo orientation: arm swings toward tube centre when deflecting fin

STEP 2.3 — Pushrod Fabrication
  - Cut 4× 80mm lengths of 1.5mm music wire
  - Z-bend one end of each pushrod (90° bend, 5mm long leg)
  - Hook Z-bend into servo arm outermost hole
  - Other end: attach Du-Bro EZ connector

STEP 2.4 — Fin Installation
  - Slide fin_mount_forward assembly into CF tube from front
  - Position so fin slots align with the 4 pre-cut slots in tube
  - Secure with M3×12 screw through tube wall into ring (×2 per ring)
  - Slide fin blade root into slot, attach clevis to EZ connector
  - With servo at neutral (1500μs), fin should be perfectly flush with tube
  - If not: adjust EZ connector position on pushrod

STEP 2.5 — Full Deflection Test
  - Command each servo to 1200μs (full one way): verify fin deflects 20°
  - Command each servo to 1800μs (full other way): verify fin deflects 20°
  - Check for binding throughout travel
  - Verify fin snaps back to neutral when servo returns to 1500μs
```

---

## Phase 3 — Avionics Installation

```
STEP 3.1 — Avionics Tray Population
  - Solder nylon M3 standoffs to avionics_tray (4 per board)
  - Mount F405 FC at 30mm mark, using nylon standoffs
  - Mount vibration dampening foam pad between tray and FC
  - Mount RPi Zero 2W at 80mm mark, nylon standoffs

STEP 3.2 — GPS Installation
  - Mount u-blox M10 at 0mm mark (front of tray)
  - GPS patch antenna faces UP through hole in tray
  - Stick 15mm aluminium ground plane under antenna
  - Route UART cable to FC UART3

STEP 3.3 — Barometer
  - If using external BMP388: attach to I2C pads on FC or RPi
  - Drill 1mm vent hole in CF tube wall above sensor location
  - Cover vent hole with small foam square (static port foam)

STEP 3.4 — Tray Installation
  - Slide avionics tray into CF tube mid-section
  - Route CSI ribbon from nose section to RPi Camera connector
    CRITICAL: Connect CSI ribbon before closing tube. Cannot be done later.
  - Secure tray with M3×8 screws through tube wall

STEP 3.5 — ELRS Receiver
  - Mount ELRS receiver on tray with double-sided foam tape
  - Route antenna outside tube through small hole, tape along tube exterior
  - Connect SBUS wire to FC UART2 RX

STEP 3.6 — SiK Telemetry Radio
  - Mount SiK radio on tray rear section
  - Route antenna outside tube, position at 90° to ELRS antenna
  - Connect UART to FC UART4
```

---

## Phase 4 — Power Bay & Battery

```
STEP 4.1 — BEC Installation
  - Solder 22AWG leads from XT30 distribution board to both BEC inputs
  - BEC #1 output: 22AWG to FC 5V, RPi, GPS
  - BEC #2 output: 22AWG to servo power rail
  - Test each BEC output voltage before connecting any loads

STEP 4.2 — Battery Bay
  - Slide power_bay section onto CF tube rear
  - Route BEC input wires through power bay to battery cradle
  - Install XT30 female connector at rear of power bay
  - Secure power_bay with M3×8 screws

STEP 4.3 — Battery Test Install
  - Insert 3S LiPo — use Velcro straps to secure
  - Connect XT30 — verify system powers up
  - Check: FC boots (LED pattern), Pi boots (SSH in ~45s)

STEP 4.4 — Tail Cap
  - Install tail_ballast_cap with initial 50g steel weight
  - Secure with rubber O-ring or M3 screws
```

---

## Phase 5 — Carrier Aircraft Mount

```
STEP 5.1 — Saddle Mount Installation
  - Bolt wing_saddle_mount to carrier aircraft wing hardpoint
  - Use M4×20 bolts + nyloc nuts, torque to hand-tight + 1/4 turn
  - Verify mount is perpendicular to wing chord line (level check)

STEP 5.2 — Latch Servo
  - Mount release servo inside saddle mount housing
  - Fabricate retention pin from M3×25 steel bolt
  - Pin must pass through saddle mount wall and through pod saddle groove
  - Servo at 1500μs (neutral): pin is engaged (pod locked)
  - Servo at 2000μs (full): pin is retracted (pod free)

STEP 5.3 — Servo Extension Cable
  - Run servo extension from release servo to aircraft FC/receiver
  - Cable must have enough slack for wing flex without pulling servo
  - Secure cable with cable ties every 50mm along wing underside

STEP 5.4 — Pod Installation
  - Slide pod into saddle rail from rear
  - Push forward until pin engages in pod saddle groove (click)
  - Pull pod rearward lightly to confirm locked
  - Connect any inter-connection wires (power if pod battery on carrier)
```

---

## Phase 6 — Final Checks Before First Power-On

```
□ All M3 structural screws have Loctite 243
□ All soldered connections are visually inspected (no cold joints)
□ Multimeter continuity check: no shorts on 5V or servo rails
□ Battery XT30 polarity verified (XT30 is reverse-polarity-proof, but verify anyway)
□ CSI ribbon connector is fully seated at both ends (camera + Pi)
□ All servo signal connectors are correctly oriented (signal to correct pin)
□ GPS antenna not obstructed by metal parts
□ Pod CG is at 95–105mm from nose (see STL README for procedure)
□ All cable routing is secured and cannot contact servo linkages
□ Camera lens is clean and undamaged
```

---

## First Power-On Sequence

1. **Do not have pod mounted on aircraft for first power-on**
2. Connect battery XT30
3. Wait for FC to boot (ArduPlane splash screen on GCS)
4. Wait for RPi to boot (~45 seconds, SSH accessible)
5. Check GCS: all pre-arm checks green
6. Do **NOT** arm FC yet — just verify connectivity
7. Test all 4 servo outputs with servo test in Mission Planner
8. Verify fin deflection direction matches software mixer expectations
9. SSH into Pi, run: `python3 software/vision.py` — verify camera feed
10. Power down, correct any issues found
11. Ready for software configuration (see TUNING.md)
