"""
surepy.devices
====================================
ABC representing a Sure Petcare Device.

|license-info|
"""

import logging

from abc import ABC
from typing import Any, Dict, Optional

from surepy.const import BASE_RESOURCE, CONTROL_RESOURCE
from surepy.entities import SurepyEntity
from surepy.enums import LockState
from surepy.exceptions import SurePetcareError


class SurepyDevice(SurepyEntity, ABC):
    @property
    def serial(self) -> Optional[str]:
        """ID of the household the pet belongs to."""
        return str(serial) if (serial := self._data.get("serial_number")) else None


class Hub(SurepyDevice):
    """Sure Petcare Hub."""


class Flap(SurepyDevice):
    """Sure Petcare Cat- or Pet-Flap."""

    async def lock(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, LockState.LOCKED_ALL)

    async def lock_in(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, LockState.LOCKED_IN)

    async def lock_out(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, LockState.LOCKED_OUT)

    async def unlock(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        return await self._locking(device_id, LockState.UNLOCKED)

    async def _locking(self, device_id: int, mode: LockState) -> Optional[Dict[str, Any]]:
        """Retrieve the flap data/state."""
        resource = CONTROL_RESOURCE.format(BASE_RESOURCE=BASE_RESOURCE, device_id=device_id)
        data = {"locking": int(mode.value)}

        if (
            response := await self._sac.call(
                method="PUT", resource=resource, device_id=device_id, data=data
            )
        ) and (response_data := response.get("data")):

            desired_state = data.get("locking")
            state = response_data.get("locking")

            logging.debug(f"bool({state} == {desired_state}) = {bool(state == desired_state)}")

            # check if the state is correctly updated
            if state == desired_state:
                return response

        # return None
        raise SurePetcareError("ERROR (UN)LOCKING DEVICE - PLEASE CHECK IMMEDIATELY!")
