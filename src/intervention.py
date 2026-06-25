from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from time import time
from typing import Any

from .config import settings


@dataclass(frozen=True)
class InterventionTemplate:
    kind: str
    title: str
    body: str
    action_label: str


class InterventionEngine:
    def __init__(self) -> None:
        self._lock = RLock()
        self._active: dict[str, Any] | None = None
        self._templates = [
            InterventionTemplate(
                kind="employment_interest_form",
                title="Performance Warning",
                body="We noticed signs of decreased productivity. Please complete this Employment Interest Form.",
                action_label="Apply Now",
            ),
            InterventionTemplate(
                kind="hr_warning",
                title="HR Notice",
                body="Your attention metrics have entered a deeply unserious zone. This will be added to your imaginary file.",
                action_label="Acknowledge",
            ),
            InterventionTemplate(
                kind="performance_review",
                title="Performance Review Starting...",
                body="Please remain seated while your local webcam invents a management meeting.",
                action_label="Return To Work",
            ),
            InterventionTemplate(
                kind="termination_notice",
                title="Termination Notice Draft",
                body="Reason: suspiciously powerful commitment to anything except the task at hand.",
                action_label="Appeal Decision",
            ),
        ]

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._active is not None:
                return deepcopy(self._active)

            template = random.choice(self._templates)
            self._active = {
                "id": f"{template.kind}-{int(time() * 1000)}",
                "kind": template.kind,
                "title": template.title,
                "body": template.body,
                "action_label": template.action_label,
                "started_at": time(),
                "sound_enabled": settings.sound_enabled,
            }
            return deepcopy(self._active)

    def clear(self) -> None:
        with self._lock:
            self._active = None

    def active(self) -> dict[str, Any] | None:
        with self._lock:
            return deepcopy(self._active)
