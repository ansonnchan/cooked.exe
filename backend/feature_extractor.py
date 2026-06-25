from __future__ import annotations

from dataclasses import dataclass
from math import dist

from .config import settings
from .mediapipe_tracker import NormalizedLandmark, TrackingResult

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


@dataclass(frozen=True)
class FaceFeatures:
    face_detected: bool
    head_yaw: float = 0.0
    head_pitch: float = 0.0
    mouth_ratio: float = 0.0
    mouth_open: bool = False


class FeatureExtractor:
    _HEAD_POSE_INDICES = (1, 152, 33, 263, 61, 291)
    _MOUTH_INDICES = (13, 14, 78, 308)

    def extract(self, tracking: TrackingResult) -> FaceFeatures:
        if not tracking.face_detected:
            return FaceFeatures(face_detected=False)

        if not self._has_required_landmarks(tracking.landmarks):
            return FaceFeatures(face_detected=False)

        head_pitch, head_yaw = self._estimate_head_pose(
            tracking.landmarks,
            tracking.frame_width,
            tracking.frame_height,
        )
        mouth_ratio = self._mouth_openness_ratio(tracking.landmarks)

        return FaceFeatures(
            face_detected=True,
            head_yaw=head_yaw,
            head_pitch=head_pitch,
            mouth_ratio=mouth_ratio,
            mouth_open=mouth_ratio >= settings.mouth_open_threshold,
        )

    def _has_required_landmarks(self, landmarks: list[NormalizedLandmark]) -> bool:
        required = (*self._HEAD_POSE_INDICES, *self._MOUTH_INDICES)
        return len(landmarks) > max(required)

    def _estimate_head_pose(
        self,
        landmarks: list[NormalizedLandmark],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float]:
        if cv2 is None or np is None:
            return 0.0, 0.0

        image_points = np.array(
            [
                self._pixel_point(landmarks[1], frame_width, frame_height),
                self._pixel_point(landmarks[152], frame_width, frame_height),
                self._pixel_point(landmarks[33], frame_width, frame_height),
                self._pixel_point(landmarks[263], frame_width, frame_height),
                self._pixel_point(landmarks[61], frame_width, frame_height),
                self._pixel_point(landmarks[291], frame_width, frame_height),
            ],
            dtype="double",
        )

        model_points = np.array(
            [
                (0.0, 0.0, 0.0),
                (0.0, -63.6, -12.5),
                (-43.3, 32.7, -26.0),
                (43.3, 32.7, -26.0),
                (-28.9, -28.9, -24.1),
                (28.9, -28.9, -24.1),
            ],
            dtype="double",
        )

        focal_length = float(frame_width)
        center = (frame_width / 2.0, frame_height / 2.0)
        camera_matrix = np.array(
            [
                (focal_length, 0.0, center[0]),
                (0.0, focal_length, center[1]),
                (0.0, 0.0, 1.0),
            ],
            dtype="double",
        )
        distortion_coefficients = np.zeros((4, 1))

        success, rotation_vector, _translation_vector = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            distortion_coefficients,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return 0.0, 0.0

        rotation_matrix, _jacobian = cv2.Rodrigues(rotation_vector)
        angles = cv2.RQDecomp3x3(rotation_matrix)[0]
        pitch = float(angles[0])
        yaw = float(angles[1])
        return pitch, yaw

    def _mouth_openness_ratio(self, landmarks: list[NormalizedLandmark]) -> float:
        upper_lip = self._normalized_point(landmarks[13])
        lower_lip = self._normalized_point(landmarks[14])
        left_mouth = self._normalized_point(landmarks[78])
        right_mouth = self._normalized_point(landmarks[308])

        mouth_width = dist(left_mouth, right_mouth)
        if mouth_width == 0:
            return 0.0

        return dist(upper_lip, lower_lip) / mouth_width

    def _pixel_point(
        self,
        landmark: NormalizedLandmark,
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float]:
        return landmark.x * frame_width, landmark.y * frame_height

    def _normalized_point(self, landmark: NormalizedLandmark) -> tuple[float, float]:
        return landmark.x, landmark.y
