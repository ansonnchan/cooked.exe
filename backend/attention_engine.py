from __future__ import annotations

from dataclasses import dataclass, field

from .config import settings
from .feature_extractor import FaceFeatures


@dataclass(frozen=True)
class AttentionResult:
    raw_score: float
    smoothed_score: float
    penalties: dict[str, int] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


class AttentionEngine:
    def __init__(self) -> None:
        self._smoothed_score = 100.0

    def reset(self) -> None:
        self._smoothed_score = 100.0

    def evaluate(self, features: FaceFeatures) -> AttentionResult:
        penalties: dict[str, int] = {}
        reasons: list[str] = []

        if not features.face_detected:
            penalties["face_missing"] = settings.face_missing_penalty
            reasons.append("Face missing")
        else:
            if abs(features.head_yaw) >= settings.head_yaw_threshold:
                penalties["looking_away"] = settings.yaw_penalty
                reasons.append("Looking away")

            if features.head_pitch >= settings.head_pitch_threshold:
                penalties["looking_down"] = settings.pitch_penalty
                reasons.append("Head tilted downward")

            if features.mouth_open:
                penalties["mouth_open"] = settings.mouth_open_penalty
                reasons.append("Possible yawn")

        raw_score = max(0.0, 100.0 - float(sum(penalties.values())))
        alpha = min(1.0, max(0.0, settings.ema_alpha))
        self._smoothed_score = alpha * raw_score + (1.0 - alpha) * self._smoothed_score

        return AttentionResult(
            raw_score=raw_score,
            smoothed_score=self._smoothed_score,
            penalties=penalties,
            reasons=reasons,
        )
