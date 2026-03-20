"""
vision.py — Red Carpet Detection Pipeline
==========================================
Runs on Raspberry Pi Zero 2W using the nose-mounted
Camera Module 3 Wide (CSI-2).

The camera IS the nose of the pod — it faces in the
direction of travel (forward/down during descent).
As the pod dives toward the target, the red carpet
appears increasingly centred in frame.

Detection method: dual-range HSV masking (red wraps
around 0°/180° in HSV colour space) + morphological
filtering + contour centroid extraction.
"""

import cv2
import numpy as np
import threading
import logging
import time
from dataclasses import dataclass
from typing import Optional

import config

log = logging.getLogger("VISION")


# ──────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────

@dataclass
class DetectionResult:
    """Result from a single camera frame."""
    cx: float            # Centroid X (pixels, 0 = left)
    cy: float            # Centroid Y (pixels, 0 = top)
    area_px: float       # Blob area in pixels²
    confidence: float    # 0.0–1.0 — how solid the detection is
    bbox: tuple          # (x, y, w, h) bounding box
    frame_w: int         # Frame width for normalisation
    frame_h: int         # Frame height for normalisation
    timestamp: float     # Unix timestamp of frame capture


# ──────────────────────────────────────────────────────────────────
# RED CARPET TRACKER
# ──────────────────────────────────────────────────────────────────

class RedCarpetTracker:
    """
    Thread-safe red carpet detection.
    Runs in a background daemon thread.
    Call get_latest() from main FSM loop.
    """

    def __init__(self):
        self._latest: Optional[DetectionResult] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._cap: Optional[cv2.VideoCapture] = None

        # Pre-build morphological kernels (constant, no need to rebuild each frame)
        self._kernel_open  = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (config.MORPH_OPEN_KERNEL_SIZE, config.MORPH_OPEN_KERNEL_SIZE)
        )
        self._kernel_close = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (config.MORPH_CLOSE_KERNEL_SIZE, config.MORPH_CLOSE_KERNEL_SIZE)
        )

        # Statistics
        self.frames_processed = 0
        self.frames_detected  = 0

        log.info("RedCarpetTracker initialised")

    def start(self):
        """Open camera and start detection thread."""
        if self._thread and self._thread.is_alive():
            log.warning("Tracker already running")
            return

        self._stop_event.clear()
        self._cap = self._open_camera()
        if self._cap is None:
            log.error("Failed to open camera — optical guidance unavailable")
            return

        self._thread = threading.Thread(
            target=self._detection_loop,
            name="vision-tracker",
            daemon=True
        )
        self._thread.start()
        log.info("Vision tracker started (%.0fx%.0f @ %dfps)",
                 *config.CAM_RESOLUTION, config.CAM_FPS)

    def stop(self):
        """Stop detection thread and release camera."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._cap:
            self._cap.release()
        log.info("Vision tracker stopped. Processed: %d frames, Detections: %d (%.1f%%)",
                 self.frames_processed, self.frames_detected,
                 100 * self.frames_detected / max(1, self.frames_processed))

    def get_latest(self) -> Optional[DetectionResult]:
        """Thread-safe access to latest detection result."""
        with self._lock:
            return self._latest

    # ────────────────────────────────────────────────────────────
    # CAMERA INIT
    # ────────────────────────────────────────────────────────────

    def _open_camera(self) -> Optional[cv2.VideoCapture]:
        """Open the RPi CSI camera via libcamera/V4L2."""
        w, h = config.CAM_RESOLUTION
        fps   = config.CAM_FPS

        # Try libcamera pipeline first (RPi Camera Module 3)
        gst_pipeline = (
            f"libcamerasrc ! "
            f"video/x-raw,width={w},height={h},framerate={fps}/1,format=BGR ! "
            f"appsink drop=true max-buffers=1"
        )
        cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            log.info("Camera opened via libcamera GStreamer pipeline")
            return cap

        # Fallback: V4L2 /dev/video0
        log.warning("libcamera pipeline failed, trying V4L2 /dev/video0")
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            cap.set(cv2.CAP_PROP_FPS,          fps)
            log.info("Camera opened via V4L2")
            return cap

        log.error("No camera available on this system")
        return None

    # ────────────────────────────────────────────────────────────
    # DETECTION LOOP
    # ────────────────────────────────────────────────────────────

    def _detection_loop(self):
        """Main detection loop — runs in daemon thread."""
        log.info("Detection loop running")

        while not self._stop_event.is_set():
            ret, frame = self._cap.read()
            if not ret or frame is None:
                log.debug("Frame grab failed — skipping")
                time.sleep(0.01)
                continue

            t0 = time.perf_counter()
            result = self._detect(frame)
            dt = time.perf_counter() - t0

            self.frames_processed += 1
            if result is not None:
                self.frames_detected += 1

            with self._lock:
                self._latest = result

            # Log processing time occasionally
            if self.frames_processed % 100 == 0:
                log.debug("Vision: %d frames, %.1fms/frame, %.1f%% detection rate",
                          self.frames_processed, dt*1000,
                          100 * self.frames_detected / self.frames_processed)

    # ────────────────────────────────────────────────────────────
    # CORE DETECTION ALGORITHM
    # ────────────────────────────────────────────────────────────

    def _detect(self, frame: np.ndarray) -> Optional[DetectionResult]:
        """
        Detect red carpet in a BGR frame.

        Pipeline:
        1. Downscale to processing resolution if needed
        2. Convert BGR → HSV
        3. Dual-range red mask (hue wraps at 0/180)
        4. Morphological open (noise removal) + close (fill gaps)
        5. Find largest contour
        6. Compute centroid, area, confidence
        7. Return DetectionResult or None
        """
        h, w = frame.shape[:2]

        # ── Step 1: Resize for faster processing (optional) ───
        proc_w, proc_h = 640, 360  # Process at half resolution
        if w != proc_w or h != proc_h:
            small = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_LINEAR)
        else:
            small = frame
        sh, sw = small.shape[:2]

        # ── Step 2: BGR → HSV ─────────────────────────────────
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        # ── Step 3: Dual-range red mask ───────────────────────
        mask1 = cv2.inRange(hsv,
                            np.array(config.HSV_RED_LOW_1),
                            np.array(config.HSV_RED_HIGH_1))
        mask2 = cv2.inRange(hsv,
                            np.array(config.HSV_RED_LOW_2),
                            np.array(config.HSV_RED_HIGH_2))
        mask = cv2.bitwise_or(mask1, mask2)

        # ── Step 4: Morphological filtering ──────────────────
        # Open: removes small isolated noise specks
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  self._kernel_open)
        # Close: fills internal holes in carpet blob
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel_close)

        # ── Step 5: Find contours ─────────────────────────────
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Keep only the largest contour
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        # Scale area threshold to processing resolution
        scale = (proc_w / w) * (proc_h / h)
        min_area_scaled = config.MIN_CARPET_AREA_PX * scale

        if area < min_area_scaled:
            return None

        # ── Step 6: Centroid + bounding box ──────────────────
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None

        cx_proc = M["m10"] / M["m00"]
        cy_proc = M["m01"] / M["m00"]

        # Scale centroid back to original resolution
        cx = cx_proc * (w / proc_w)
        cy = cy_proc * (h / proc_h)

        bx, by, bw, bh = cv2.boundingRect(largest)
        bbox = (int(bx * w / proc_w), int(by * h / proc_h),
                int(bw * w / proc_w), int(bh * h / proc_h))

        # ── Step 7: Confidence score ──────────────────────────
        # Based on: blob area relative to expected carpet size,
        # aspect ratio (carpet is approximately square), and
        # blob solidity (convex hull fill ratio)
        hull      = cv2.convexHull(largest)
        hull_area = cv2.contourArea(hull)
        solidity  = area / hull_area if hull_area > 0 else 0

        # Aspect ratio score — carpet should be roughly square
        aspect    = min(bw, bh) / max(bw, bh, 1)
        aspect_score = aspect  # 1.0 = perfect square, 0 = line

        # Normalised area score (saturates at 10% of frame = 1.0)
        area_score = min(1.0, area / (sw * sh * 0.10))

        confidence = (0.4 * solidity + 0.3 * aspect_score + 0.3 * area_score)

        return DetectionResult(
            cx=cx,
            cy=cy,
            area_px=area / scale,  # Back to original-res equivalent
            confidence=confidence,
            bbox=bbox,
            frame_w=w,
            frame_h=h,
            timestamp=time.time(),
        )


# ──────────────────────────────────────────────────────────────────
# TESTING UTILITY
# ──────────────────────────────────────────────────────────────────

def run_visual_test():
    """
    Standalone test: open camera, display detection overlay.
    Run on Pi with display: python3 vision.py
    Useful for HSV threshold tuning.
    """
    import config as cfg

    tracker = RedCarpetTracker()
    cap = tracker._open_camera()

    if cap is None:
        print("No camera available")
        return

    print("Visual test running. Press Q to quit.")
    print("Adjust HSV thresholds in config.py for your carpet colour.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        result = tracker._detect(frame)
        display = frame.copy()

        if result is not None:
            # Draw centroid
            cx, cy = int(result.cx), int(result.cy)
            cv2.circle(display, (cx, cy), 10, (0, 255, 255), 2)
            cv2.line(display, (cx - 15, cy), (cx + 15, cy), (0, 255, 255), 1)
            cv2.line(display, (cx, cy - 15), (cx, cy + 15), (0, 255, 255), 1)

            # Draw bounding box
            bx, by, bw, bh = result.bbox
            cv2.rectangle(display, (bx, by), (bx+bw, by+bh), (0, 0, 255), 2)

            # Frame center crosshair
            fw, fh = result.frame_w, result.frame_h
            cv2.line(display, (fw//2 - 20, fh//2), (fw//2 + 20, fh//2), (255, 0, 0), 1)
            cv2.line(display, (fw//2, fh//2 - 20), (fw//2, fh//2 + 20), (255, 0, 0), 1)

            # Error vector
            cv2.arrowedLine(display, (fw//2, fh//2), (cx, cy), (0, 255, 0), 2, tipLength=0.2)

            # Info overlay
            cv2.putText(display, f"LOCKED conf={result.confidence:.2f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(display, f"err_x={cx - fw//2:+.0f}px  err_y={cy - fh//2:+.0f}px",
                        (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(display, "NO LOCK",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow("Drop Pod — Vision Test", display)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_visual_test()
