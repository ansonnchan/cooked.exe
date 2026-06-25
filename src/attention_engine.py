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
        self._yaw_evidence = 0.0
        self._pitch_evidence = 0.0
        self._face_missing_evidence = 0.0
        self._mouth_evidence = 0.0

    def reset(self) -> None:
        self._smoothed_score = 100.0
        self._yaw_evidence = 0.0
        self._pitch_evidence = 0.0
        self._face_missing_evidence = 0.0
        self._mouth_evidence = 0.0

    def evaluate(self, features: FaceFeatures) -> AttentionResult:
        penalties: dict[str, int] = {}
        reasons: list[str] = []

        if not features.face_detected:
            self._face_missing_evidence = self._update_evidence(
                self._face_missing_evidence,
                1.0,
            )
            self._yaw_evidence = self._update_evidence(self._yaw_evidence, 0.0)
            self._pitch_evidence = self._update_evidence(self._pitch_evidence, 0.0)
            self._mouth_evidence = self._update_evidence(self._mouth_evidence, 0.0)
        else:
            self._face_missing_evidence = self._update_evidence(
                self._face_missing_evidence,
                0.0,
            )
            self._yaw_evidence = self._update_evidence(
                self._yaw_evidence,
                self._band_score(
                    abs(features.head_yaw),
                    settings.head_yaw_threshold,
                    settings.head_yaw_severe_threshold,
                ),
            )
            self._pitch_evidence = self._update_evidence(
                self._pitch_evidence,
                self._band_score(
                    features.head_pitch,
                    settings.head_pitch_threshold,
                    settings.head_pitch_severe_threshold,
                ),
            )
            self._mouth_evidence = self._update_evidence(
                self._mouth_evidence,
                1.0 if features.mouth_open else 0.0,
            )

        self._add_penalty(
            penalties,
            reasons,
            key="face_missing",
            reason="Face missing",
            max_penalty=settings.face_missing_penalty,
            evidence=self._face_missing_evidence,
        )
        self._add_penalty(
            penalties,
            reasons,
            key="looking_away",
            reason="Looking away",
            max_penalty=settings.yaw_penalty,
            evidence=self._yaw_evidence,
        )
        self._add_penalty(
            penalties,
            reasons,
            key="looking_down",
            reason="Head tilted downward",
            max_penalty=settings.pitch_penalty,
            evidence=self._pitch_evidence,
        )
        self._add_penalty(
            penalties,
            reasons,
            key="mouth_open",
            reason="Possible yawn",
            max_penalty=settings.mouth_open_penalty,
            evidence=self._mouth_evidence,
        )
        self._rebalance_signal_confidence(penalties, reasons)

        raw_score = max(0.0, 100.0 - float(sum(penalties.values())))
        alpha = min(1.0, max(0.0, settings.ema_alpha))
        self._smoothed_score = alpha * raw_score + (1.0 - alpha) * self._smoothed_score

        return AttentionResult(
            raw_score=raw_score,
            smoothed_score=self._smoothed_score,
            penalties=penalties,
            reasons=reasons,
        )

    def _update_evidence(self, current: float, target: float) -> float:
        alpha = (
            settings.evidence_rise_alpha
            if target > current
            else settings.evidence_fall_alpha
        )
        alpha = min(1.0, max(0.0, alpha))
        return alpha * target + (1.0 - alpha) * current

    def _band_score(self, value: float, moderate: float, severe: float) -> float:
        if value <= moderate:
            return 0.0
        if severe <= moderate:
            return 1.0
        return min(1.0, max(0.0, (value - moderate) / (severe - moderate)))

    def _add_penalty(
        self,
        penalties: dict[str, int],
        reasons: list[str],
        key: str,
        reason: str,
        max_penalty: int,
        evidence: float,
    ) -> None:
        penalty = round(max_penalty * evidence)
        if penalty <= 0:
            return

        penalties[key] = penalty
        if evidence >= 0.35:
            reasons.append(reason)

    def _rebalance_signal_confidence(
        self,
        penalties: dict[str, int],
        reasons: list[str],
    ) -> None:
        if "face_missing" in penalties:
            return

        active_pose_signals = [
            evidence
            for evidence in (self._yaw_evidence, self._pitch_evidence)
            if evidence >= 0.25
        ]
        weak_incidental_signals = [
            evidence
            for evidence in (self._mouth_evidence,)
            if evidence >= 0.5
        ]
        active_signals = active_pose_signals + weak_incidental_signals

        if len(active_pose_signals) >= 2:
            combined = min(self._yaw_evidence, self._pitch_evidence)
            penalty = round(settings.combined_distraction_penalty * combined)
            if penalty > 0:
                penalties["combined_pose"] = penalty
                if "Combined posture shift" not in reasons:
                    reasons.append("Combined posture shift")
            return

        if len(active_signals) != 1:
            return

        key = ""
        if self._yaw_evidence >= 0.25:
            key = "looking_away"
        elif self._pitch_evidence >= 0.25:
            key = "looking_down"
        elif self._mouth_evidence >= 0.5:
            key = "mouth_open"

        if key not in {"looking_away", "looking_down", "mouth_open"}:
            return

        evidence = {
            "looking_away": self._yaw_evidence,
            "looking_down": self._pitch_evidence,
            "mouth_open": self._mouth_evidence,
        }[key]

        penalties[key] = min(penalties[key], settings.single_signal_penalty_cap)
        if evidence >= settings.high_confidence_single_signal_evidence and key != "mouth_open":
            penalties[f"{key}_sustained"] = settings.high_confidence_single_signal_bonus
            if "Sustained high-confidence cue" not in reasons:
                reasons.append("Sustained high-confidence cue")
