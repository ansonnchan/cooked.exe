from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[1] / ".cache" / "matplotlib"),
)

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

        if mp is None:
            return

        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=settings.max_faces,
            refine_landmarks=True,
            min_detection_confidence=settings.min_detection_confidence,
            min_tracking_confidence=settings.min_tracking_confidence,
        )

    def detect(self, frame) -> TrackingResult:
        frame_height, frame_width = frame.shape[:2]

        if self._face_mesh is None or cv2 is None:
            return TrackingResult(
                face_detected=False,
                frame_width=frame_width,
                frame_height=frame_height,
                error=f"MediaPipe unavailable: {MEDIAPIPE_IMPORT_ERROR}",
            )

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

    def close(self) -> None:
        if self._face_mesh is not None:
            self._face_mesh.close()
