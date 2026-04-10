import cv2
import threading
import time


class CameraStream:
    def __init__(
        self,
        camera_index=0,
        width=1280,
        height=720,
        fps=30,
        jpeg_quality=80,
    ):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.jpeg_quality = jpeg_quality

        self.camera = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.thread = None
        self.running = False

    def start(self):
        if self.running:
            return

        self.camera = cv2.VideoCapture(self.camera_index, cv2.CAP_V4L2)

        if not self.camera.isOpened():
            raise RuntimeError(f"Could not open camera index {self.camera_index}")

        self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.camera.set(cv2.CAP_PROP_FPS, self.fps)

        self.running = True
        self.thread = threading.Thread(target=self._update_frames, daemon=True)
        self.thread.start()

    def _update_frames(self):
        while self.running:
            ret, frame = self.camera.read()

            if not ret:
                time.sleep(0.05)
                continue

            with self.frame_lock:
                self.latest_frame = frame.copy()

    def generate_frames(self):
        while True:
            with self.frame_lock:
                frame = None if self.latest_frame is None else self.latest_frame.copy()

            if frame is None:
                time.sleep(0.01)
                continue

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

    def stop(self):
        self.running = False

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        if self.camera is not None:
            self.camera.release()
            self.camera = None