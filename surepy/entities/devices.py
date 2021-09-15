"""
surepy.devices
====================================
ABC representing a Sure Petcare Device.

|license-info|
"""

from __future__ import annotations

import logging

from abc import ABC
from typing import Any
from urllib.parse import urlparse

from surepy.const import SURE_BATT_VOLTAGE_FULL, SURE_BATT_VOLTAGE_LOW
from surepy.entities import SurepyEntity
from surepy.enums import BowlPosition, FoodType, LockState


# get a logger
logger: logging.Logger = logging.getLogger(__name__)


class Hub(SurepyEntity):
    """Sure Petcare Hub."""

    @property
    def online(self) -> bool:
        return bool(self._data.get("status", {}).get("online"))

    @property
    def parent_id(self) -> int | None:
        return self._data.get("parent_device_id", None)

    @property
    def serial(self) -> str | None:
        """ID of the household the pet belongs to."""
        return str(serial) if (serial := self._data.get("serial_number")) else None

    @property
    def icon(self) -> str | None:
        """Picture of the Pet."""
        return urlparse("https://surehub.io/assets/images/hub-icon.svg").geturl()


class SurepyDevice(SurepyEntity, ABC):
    """Abstract Surepy base device"""

    @property
    def parent_id(self) -> int | None:
        return self._data.get("parent_device_id", None)

    @property
    def serial(self) -> str | None:
        """ID of the household the pet belongs to."""
        return str(serial) if (serial := self._data.get("serial_number")) else None

    @property
    def battery_level(self) -> int | None:
        """Return battery level in percent."""
        return self.calculate_battery_level()

    def calculate_battery_level(
        self,
        voltage_full: float = SURE_BATT_VOLTAGE_FULL,
        voltage_low: float = SURE_BATT_VOLTAGE_LOW,
        num_batteries: int = 4,
    ) -> int | None:
        """Return battery voltage."""

        try:
            voltage_diff = voltage_full - voltage_low
            battery_voltage = float(self._data["status"]["battery"])
            voltage_per_battery = battery_voltage / num_batteries
            voltage_per_battery_diff = voltage_per_battery - voltage_low

            # return batterie level between 0 and 100
            return max(min(int(voltage_per_battery_diff / voltage_diff * 100), 100), 0)

        except (KeyError, TypeError, ValueError) as error:
            logger.debug("error while calculating battery level: %s", error)
            return None


class FeederBowl:
    """Sure Petcare Felaqua."""

    def __init__(self, data: dict[str, int | float | str], feeder: Feeder):
        """Initialize a Sure Petcare sensor."""

        self._data: dict[str, int | float | str] = data
        self._name = f"{feeder.name} Bowl {self._data['index']}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def weight(self) -> float:
        return float(self._data["weight"])

    @property
    def change(self) -> float:
        return float(self._data["change"])

    @property
    def target(self) -> int | None:
        return int(self._data["target"]) if "target" in self._data else None

    @property
    def index(self) -> int | None:
        return int(self._data["index"]) if "index" in self._data else None

    @property
    def food_type_id(self) -> int | None:
        return int(self._data["food_type_id"]) if "food_type_id" in self._data else None

    @property
    def food_type(self) -> str | None:
        return FoodType(self.food_type_id).name.capitalize() if self.food_type_id else None

    @property
    def position(self) -> str | None:
        return BowlPosition(self.index).name.capitalize() if self.index else None

    def raw_data(self) -> dict[str, int | float | str]:
        return self._data


class Feeder(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""

    def __init__(self, data: dict[str, Any]):
        """Initialize a Sure Petcare sensor."""
        super().__init__(data)

        self.bowls: dict[int, FeederBowl] = {}

        self.add_bowls()

    @property
    def bowl_count(self) -> int:
        return len(self.bowls)

    @property
    def total_weight(self) -> float:
        return sum([bowl.weight or 0.0 for bowl in self.bowls.values() if bowl.weight > 0.0])

    def add_bowls(self) -> None:
        if lunch := self._data.get("lunch"):
            for bowl in lunch.get("weights", []):
                self.bowls[bowl["index"]] = FeederBowl(data=bowl, feeder=self)

    @property
    def icon(self) -> str | None:
        """Icon of the Felaqua."""
        return urlparse("https://surehub.io/assets/images/feeder-left-menu.png").geturl()


class Felaqua(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""

    @property
    def water_remaining(self) -> float | None:
        remaining = None

        try:
            remaining = float(self._data["latest_drink"]["remaining"])
        except (KeyError, TypeError):
            pass

        return remaining

    @property
    def water_change(self) -> float | None:
        change = None

        try:
            change = float(self._data["latest_drink"]["change"])
        except (KeyError, TypeError):
            pass

        return change

    @property
    def icon(self) -> str | None:
        """Icon of the Felaqua."""
        return urlparse("https://surehub.io/assets/images/poseidon-left-menu.png").geturl()


class Flap(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""

    @property
    def state(self) -> LockState:
        return LockState(self._data["status"]["locking"]["mode"])

    @property
    def unlocked(self) -> bool:
        return self.state in [LockState.UNLOCKED, LockState.CURFEW_UNLOCKED]

    @property
    def icon(self) -> str | None:
        """Icon of the Pet/Cap Flap."""

        icon_url = "https://surehub.io/assets/images/petdoor-left-menu.png"

        if self.state == LockState.LOCKED_ALL:
            icon_url = "https://surehub.io/assets/images/both-ways-icon.svg"
        elif self.state == LockState.LOCKED_IN:
            icon_url = "https://surehub.io/assets/images/inside-icon.svg"
        elif self.state == LockState.LOCKED_OUT:
            icon_url = "https://surehub.io/assets/images/outside-icon.svg"

        return urlparse(icon_url).geturl()
