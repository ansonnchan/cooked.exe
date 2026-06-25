from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic

from .config import settings


class AttentionState(str, Enum):
    FOCUSED = "focused"
    FACE_MISSING = "face_missing"
    POSSIBLY_DISTRACTED = "possibly_distracted"
    DISTRACTED = "distracted"
    INTERVENING = "intervening"


@dataclass(frozen=True)
class StateSnapshot:
    state: AttentionState
    distraction_seconds: float
    intervention_requested: bool = False
    intervention_cleared: bool = False


class AttentionStateMachine:
    def __init__(self) -> None:
        self._state = AttentionState.FOCUSED
        self._distraction_started_at: float | None = None

    def update(
        self,
        attention_score: float,
        face_detected: bool,
        now: float | None = None,
    ) -> StateSnapshot:
        current_time = monotonic() if now is None else now
        threshold = settings.attention_threshold
        recovery_threshold = max(settings.recovery_threshold, threshold)

        if self._state == AttentionState.INTERVENING:
            elapsed = self._elapsed(current_time)
            if face_detected and attention_score >= recovery_threshold:
                self._reset()
                return StateSnapshot(
                    state=self._state,
                    distraction_seconds=0.0,
                    intervention_cleared=True,
                )
            return StateSnapshot(
                state=self._state,
                distraction_seconds=elapsed,
            )

        if attention_score >= threshold:
            self._distraction_started_at = None
            self._state = (
                AttentionState.FACE_MISSING
                if not face_detected
                else AttentionState.FOCUSED
            )
            return StateSnapshot(state=self._state, distraction_seconds=0.0)

        if self._distraction_started_at is None:
            self._distraction_started_at = current_time

        elapsed = self._elapsed(current_time)
        if elapsed >= settings.intervention_delay_seconds:
            self._state = AttentionState.DISTRACTED
            return StateSnapshot(
                state=self._state,
                distraction_seconds=elapsed,
                intervention_requested=True,
            )

        self._state = (
            AttentionState.FACE_MISSING
            if not face_detected
            else AttentionState.POSSIBLY_DISTRACTED
        )
        return StateSnapshot(state=self._state, distraction_seconds=elapsed)

    def mark_intervening(self) -> StateSnapshot:
        self._state = AttentionState.INTERVENING
        return self.snapshot()

    def dismiss(self) -> StateSnapshot:
        self._reset()
        return self.snapshot()

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            state=self._state,
            distraction_seconds=self._elapsed(monotonic()),
        )

    def _elapsed(self, current_time: float) -> float:
        if self._distraction_started_at is None:
            return 0.0
        return max(0.0, current_time - self._distraction_started_at)

    def _reset(self) -> None:
        self._state = AttentionState.FOCUSED
        self._distraction_started_at = None
