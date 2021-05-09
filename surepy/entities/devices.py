"""
surepy.devices
====================================
ABC representing a Sure Petcare Device.

|license-info|
"""

from __future__ import annotations

from abc import ABC

from surepy.const import PET_FLAP_VOLTAGE_DIFF, PET_FLAP_VOLTAGE_LOW
from surepy.entities import SurepyEntity
from surepy.enums import LockState


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


class SurepyDevice(SurepyEntity, ABC):
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

        battery_percent: int | None
        try:
            per_battery_voltage = self._data["status"]["battery"] / 4
            voltage_diff = per_battery_voltage - PET_FLAP_VOLTAGE_LOW
            battery_percent = min(int(voltage_diff / PET_FLAP_VOLTAGE_DIFF * 100), 100)
            battery_percent = max(battery_percent, 0)
        except (KeyError, TypeError):
            battery_percent = None

        return battery_percent


class Feeder(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""


class Felaqua(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""

    @property
    def water_remaining(self) -> float | None:
        if "drink" in self._data and (weights := self._data["drink"]["weights"].pop()):
            return float(weights["weight"])
        else:
            return None

    @property
    def water_change(self) -> float | None:
        if "drink" in self._data and (weights := self._data["drink"]["weights"].pop()):
            return float(weights["change"])
        else:
            return None


class Flap(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""

    @property
    def state(self) -> LockState:
        return LockState(self._data["status"]["locking"]["mode"])

    @property
    def unlocked(self) -> bool:
        return self.state in [LockState.UNLOCKED, LockState.CURFEW_UNLOCKED]
