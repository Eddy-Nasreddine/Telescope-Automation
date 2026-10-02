import logging
import subprocess
import threading
import time

import cv2

import config

logger = logging.getLogger("CameraStream")


class CameraStream:
    def __init__(
        self,
        camera_index=config.CAMERA_INDEX,
        width=config.CAMERA_WIDTH,
        height=config.CAMERA_HEIGHT,
        fps=config.CAMERA_FPS,
        jpeg_quality=config.CAMERA_JPEG_QUALITY,
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.jpeg_quality = jpeg_quality

        self.camera = None
        self.latest_frame = None
        self.frame_id = 0               # increments on every new frame
        self.last_frame_time = 0.0
        self.frame_ready = threading.Condition()
        self.start_lock = threading.Lock()
        self.thread = None
        self.running = False

    def set_controls(self, exposure=None, gain=None, brightness=None):
        if not self.running:
            return      # no camera open; nothing to configure

        def set_ctrl(name, value):
            try:
                subprocess.run([
                    "v4l2-ctl",
                    f"--device=/dev/video{self.camera_index}",
                    f"--set-ctrl={name}={value}"
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                logger.warning("v4l2-ctl isn't installed; camera controls unavailable.")

        if exposure is None and gain is None and brightness is None:
            return

        if exposure is not None:
            exposure = max(12, min(int(exposure), 800))

            set_ctrl("auto_exposure", 1)
            set_ctrl("exposure_time_absolute", exposure)

        if gain is not None:
            set_ctrl("gain", max(0, min(int(gain), 100)))

        if brightness is not None:
            set_ctrl("brightness", max(-64, min(int(brightness), 64)))

    def start(self):
        # Several browser tabs can hit /video_feed at once; open the camera only once
        with self.start_lock:
            if self.running:
                return

            camera = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)
            if not camera.isOpened():
                camera.release()
                raise RuntimeError(f"Could not open camera index {self.camera_index}")

            camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            camera.set(cv2.CAP_PROP_FPS, self.fps)

            self.camera = camera
            self.last_frame_time = time.monotonic()
            self.running = True
            self.thread = threading.Thread(target=self._update_frames, daemon=True)
            self.thread.start()
            self.set_controls(
                exposure=200,
                gain=10,
                brightness=0
            )
            logger.info("Camera %d opened", self.camera_index)

    def is_streaming(self) -> bool:
        """True while frames are actually arriving (not just a stale last frame)."""
        return self.running and time.monotonic() - self.last_frame_time < config.CAMERA_LOST_TIMEOUT

    def _update_frames(self):
        while self.running:
            ret, frame = self.camera.read()

            if not ret:
                # No frames for a while = camera unplugged. Release it so the
                # stream ends and a later Retry reopens it.
                if time.monotonic() - self.last_frame_time > config.CAMERA_LOST_TIMEOUT:
                    logger.warning("Camera %d stopped sending frames", self.camera_index)
                    self._release()
                    return
                time.sleep(0.05)
                continue

            with self.frame_ready:
                self.latest_frame = frame
                self.frame_id += 1
                self.last_frame_time = time.monotonic()
                self.frame_ready.notify_all()

    def generate_frames(self):
        last_sent = -1
        while True:
            with self.frame_ready:
                # Wait for a frame we haven't sent yet (instead of re-encoding
                # the same one as fast as the CPU allows)
                self.frame_ready.wait_for(lambda: self.frame_id != last_sent or not self.running,
                                          timeout=config.CAMERA_LOST_TIMEOUT)
                if not self.running or self.frame_id == last_sent:
                    return      # camera gone: end the stream instead of freezing on the last frame
                frame = self.latest_frame
                last_sent = self.frame_id

            ok, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
            )

            if not ok:
                continue

            jpg = buffer.tobytes()

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            )

    def _release(self):
        with self.frame_ready:
            self.running = False
            self.latest_frame = None
            self.frame_ready.notify_all()
        if self.camera is not None:
            self.camera.release()
            self.camera = None

    def stop(self):
        self.running = False

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        self._release()
