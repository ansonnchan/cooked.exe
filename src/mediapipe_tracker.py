from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"),
)
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

try:
    import cv2
    import mediapipe as mp
except ImportError as import_error:
    cv2 = None
    mp = None
    MEDIAPIPE_IMPORT_ERROR = str(import_error)
else:
    MEDIAPIPE_IMPORT_ERROR = ""


@dataclass(frozen=True)
class NormalizedLandmark:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class TrackingResult:
    face_detected: bool
    frame_width: int
    frame_height: int
    landmarks: list[NormalizedLandmark] = field(default_factory=list)
    error: str | None = None


class MediaPipeTracker:
    def __init__(self) -> None:
        self._face_mesh = None
        self._face_detector = None

        if cv2 is None:
            return

        if mp is not None and hasattr(mp, "solutions"):
            self._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=settings.max_faces,
                refine_landmarks=True,
                min_detection_confidence=settings.min_detection_confidence,
                min_tracking_confidence=settings.min_tracking_confidence,
            )
            return

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if cascade_path.exists():
            self._face_detector = cv2.CascadeClassifier(str(cascade_path))

    def detect(self, frame) -> TrackingResult:
        frame_height, frame_width = frame.shape[:2]

        if cv2 is None:
            return TrackingResult(
                face_detected=False,
                frame_width=frame_width,
                frame_height=frame_height,
                error=f"OpenCV unavailable: {MEDIAPIPE_IMPORT_ERROR}",
            )

        if self._face_mesh is None:
            return self._detect_with_opencv(frame, frame_width, frame_height)

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self._face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return TrackingResult(
                face_detected=False,
                frame_width=frame_width,
                frame_height=frame_height,
            )

        face_landmarks = results.multi_face_landmarks[0]
        landmarks = [
            NormalizedLandmark(
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
            )
            for landmark in face_landmarks.landmark
        ]

        return TrackingResult(
            face_detected=True,
            frame_width=frame_width,
            frame_height=frame_height,
            landmarks=landmarks,
        )

    def _detect_with_opencv(
        self,
        frame,
        frame_width: int,
        frame_height: int,
    ) -> TrackingResult:
        if self._face_detector is None or self._face_detector.empty():
            return TrackingResult(
                face_detected=False,
                frame_width=frame_width,
                frame_height=frame_height,
                error="MediaPipe Face Mesh unavailable; OpenCV face fallback unavailable",
            )

        grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_detector.detectMultiScale(
            grayscale,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )

        return TrackingResult(
            face_detected=len(faces) > 0,
            frame_width=frame_width,
            frame_height=frame_height,
            error="Using OpenCV face detection fallback; head pose metrics unavailable",
        )

    def close(self) -> None:
        if self._face_mesh is not None:
            self._face_mesh.close()
