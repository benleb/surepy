"""
surepy.entities.states
====================================
Classes representing pet states.

|license-info|
"""

from abc import ABC
from typing import Any

from surepy.enums import Location
from datetime import datetime


class PetState(ABC):
    """abstract surepy state."""

    def __init__(self, state: dict[str, dict[str, Any]]):
        self.activity: ActivityState | None = (
            ActivityState(state=state["activity"]) if "activity" in state else None
        )
        self.drinking: DrinkingState | None = (
            DrinkingState(state=state["drinking"]) if "drinking" in state else None
        )
        self.feeding: FeedingState | None = (
            FeedingState(state=state["feeding"]) if "feeding" in state else None
        )


class ActivityState:
    """surepy activity state."""

    def __init__(self, state: dict[str, Any]):
        self.device_id = state.get("device_id")
        self.tag_id = state.get("tag_id")
        self.since: datetime = (
            datetime.fromisoformat(state["at"]) if isinstance(state.get("at", None), str) else None
        )
        self.where: Location = Location(state["where"])


class DrinkingState:
    """surepy drinking state."""

    def __init__(self, state: dict[str, Any]):
        self.device_id = state.get("device_id")
        self.tag_id = state.get("tag_id")
        self.at: datetime = datetime.fromisoformat(state.get("at"))
        self.change: float = state["change"] if "change" in state else None


class FeedingState:
    """surepy feeding state."""

    def __init__(self, state: dict[str, Any]):
        self.device_id = state.get("device_id")
        self.tag_id = state.get("tag_id")
        self.at: datetime = datetime.fromisoformat(state.get("at"))
        self.changes: list[float] = state["change"] if "change" in state else None
        self.change_bowl_one = self.changes[0] if self.changes else None
        self.change_bowl_two = self.changes[1] if self.changes else None
