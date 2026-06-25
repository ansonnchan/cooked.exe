from __future__ import annotations

import threading
from platform import system
from time import perf_counter, sleep, strftime, time
from typing import Any, Generator

from .attention_engine import AttentionEngine
from .config import settings
from .feature_extractor import FeatureExtractor
from .intervention import InterventionEngine
from .mediapipe_tracker import MediaPipeTracker
from .state_machine import AttentionStateMachine, StateSnapshot

try:
    import cv2
    import numpy as np
except ImportError as import_error:
    cv2 = None
    np = None
    CAMERA_IMPORT_ERROR = str(import_error)
else:
    CAMERA_IMPORT_ERROR = ""


class CameraService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_frame = None
        self._latest_payload = self._default_payload("starting")
        self._last_log_at = 0.0
        self._last_logged_state = ""
        self._tracker = MediaPipeTracker()
        self._extractor = FeatureExtractor()
        self._attention_engine = AttentionEngine()
        self._state_machine = AttentionStateMachine()
        self._intervention_engine = InterventionEngine()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="camera-service", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._tracker.close()

    def telemetry(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._latest_payload)

    def current_frame(self):
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def current_jpeg(self) -> bytes | None:
        frame = self.current_frame()
        if frame is None or cv2 is None:
            return None

        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), settings.jpeg_quality],
        )
        if not ok:
            return None
        return encoded.tobytes()

    def dismiss_intervention(self) -> dict[str, Any]:
        self._intervention_engine.clear()
        snapshot = self._state_machine.dismiss()
        with self._lock:
            self._latest_payload = {
                **self._latest_payload,
                "state": snapshot.state.value,
                "distraction_seconds": snapshot.distraction_seconds,
                "intervention_active": False,
                "intervention": None,
            }
            return dict(self._latest_payload)

    def frame_stream(self) -> Generator[bytes, None, None]:
        boundary = settings.frame_boundary.encode()
        while not self._stop_event.is_set():
            frame = self._current_frame()
            if frame is None:
                sleep(0.1)
                continue

            yield (
                b"--"
                + boundary
                + b"\r\nContent-Type: image/jpeg\r\nContent-Length: "
                + str(len(frame)).encode()
                + b"\r\n\r\n"
                + frame
                + b"\r\n"
            )
            sleep(1.0 / max(1, settings.fps))

    def _run(self) -> None:
        if cv2 is None or np is None:
            self._set_unavailable(f"OpenCV unavailable: {CAMERA_IMPORT_ERROR}")
            while not self._stop_event.is_set():
                sleep(0.5)
            return

        while not self._stop_event.is_set():
            backend = cv2.CAP_AVFOUNDATION if system() == "Darwin" else cv2.CAP_ANY
            camera = cv2.VideoCapture(settings.camera_index, backend)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, settings.camera_width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.camera_height)
            camera.set(cv2.CAP_PROP_FPS, settings.fps)
            camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not camera.isOpened():
                self._set_unavailable("Unable to open webcam")
                sleep(1.0)
                continue

            try:
                self._capture_loop(camera)
            finally:
                camera.release()

    def _capture_loop(self, camera) -> None:
        while not self._stop_event.is_set():
            started_at = perf_counter()
            ok, frame = camera.read()
            if not ok:
                self._set_unavailable("Webcam frame unavailable")
                sleep(0.2)
                continue

            self._process_frame(frame)
            elapsed = perf_counter() - started_at
            sleep(max(0.0, (1.0 / max(1, settings.fps)) - elapsed))

    def _process_frame(self, frame) -> None:
        tracking = self._tracker.detect(frame)
        features = self._extractor.extract(tracking)
        attention = self._attention_engine.evaluate(features)
        state = self._state_machine.update(
            attention_score=attention.smoothed_score,
            face_detected=features.face_detected,
        )

        if state.intervention_requested:
            self._intervention_engine.start()
            state = self._state_machine.mark_intervening()
        elif state.intervention_cleared:
            self._intervention_engine.clear()

        intervention = self._intervention_engine.active()
        display_frame = cv2.flip(frame, 1) if settings.mirror_preview else frame
        payload = self._build_payload(
            attention=attention,
            state=state,
            features=features,
            intervention=intervention,
            camera_error=tracking.error,
        )

        with self._lock:
            self._latest_frame = display_frame.copy()
            self._latest_payload = payload

        self._log_payload(payload)

    def _build_payload(
        self,
        attention,
        state: StateSnapshot,
        features,
        intervention: dict[str, Any] | None,
        camera_error: str | None,
    ) -> dict[str, Any]:
        return {
            "timestamp": time(),
            "attention_score": round(attention.smoothed_score),
            "raw_attention_score": round(attention.raw_score),
            "state": state.state.value,
            "head_yaw": round(features.head_yaw, 2),
            "head_pitch": round(features.head_pitch, 2),
            "mouth_ratio": round(features.mouth_ratio, 3),
            "mouth_open": features.mouth_open,
            "face_detected": features.face_detected,
            "distraction_seconds": round(state.distraction_seconds, 2),
            "intervention_active": intervention is not None,
            "intervention": intervention,
            "penalties": attention.penalties,
            "reasons": attention.reasons,
            "camera_error": camera_error,
        }

    def _set_unavailable(self, message: str) -> None:
        placeholder = self._placeholder_frame(message)
        payload = self._default_payload("camera_unavailable")
        payload["camera_error"] = message

        with self._lock:
            self._latest_frame = placeholder
            self._latest_payload = payload

        self._log_payload(payload)

    def _placeholder_frame(self, message: str):
        if cv2 is None or np is None:
            return None

        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        image[:] = (26, 26, 28)
        cv2.putText(
            image,
            "cooked.exe",
            (72, 320),
            cv2.FONT_HERSHEY_SIMPLEX,
            2.2,
            (245, 245, 245),
            4,
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            message,
            (76, 390),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (120, 190, 255),
            2,
            cv2.LINE_AA,
        )
        return image

    def _current_frame(self) -> bytes | None:
        return self.current_jpeg()

    def _log_payload(self, payload: dict[str, Any]) -> None:
        now = perf_counter()
        state = (
            "DISTRACTED"
            if payload["intervention_active"] or payload["state"] in {"distracted", "intervening"}
            else "FOCUSED"
        )
        should_log = state != self._last_logged_state or (now - self._last_log_at) >= 0.75
        if not should_log:
            return

        self._last_log_at = now
        self._last_logged_state = state
        face_detected = "TRUE" if payload["face_detected"] else "FALSE"
        print(
            f"[{strftime('%H:%M:%S')}] "
            f"STATUS={state} | "
            f"SCORE={payload['attention_score']} | "
            f"YAW={payload['head_yaw']:.1f} | "
            f"PITCH={payload['head_pitch']:.1f} | "
            f"FACE={face_detected}",
            flush=True,
        )

    def _default_payload(self, state: str) -> dict[str, Any]:
        return {
            "timestamp": time(),
            "attention_score": 100,
            "raw_attention_score": 100,
            "state": state,
            "head_yaw": 0.0,
            "head_pitch": 0.0,
            "mouth_ratio": 0.0,
            "mouth_open": False,
            "face_detected": False,
            "distraction_seconds": 0.0,
            "intervention_active": False,
            "intervention": None,
            "penalties": {},
            "reasons": [],
            "camera_error": None,
        }
