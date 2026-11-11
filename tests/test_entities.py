"""Offline tests for device properties, using payloads shaped like /api/me/start."""

from datetime import datetime, timezone

from surepy.entities.devices import Curfew, Feeder, Felaqua, Flap, Hub
from surepy.entities.pet import Pet

STATUS = {
    "battery": 5.49,
    "learn_mode": False,
    "online": True,
    "signal": {"device_rssi": -81},
}

HUB = {
    "id": 1,
    "household_id": 100,
    "name": "Hub",
    "product_id": 1,
    "control": {"led_mode": 4, "pairing_mode": 0},
    "status": {"led_mode": 4, "pairing_mode": 0, "online": True},
}

FEEDER = {
    "id": 2,
    "household_id": 100,
    "name": "Feeder",
    "product_id": 4,
    "parent_device_id": 1,
    "control": {
        "bowls": {"settings": [{"food_type": 2, "target": 0}, {"food_type": 1, "target": 0}]},
        "lid": {"close_delay": 4},
        "training_mode": 2,
        "fast_polling": False,
    },
    "status": STATUS,
    "tags": [{"id": 501, "device_id": 2, "index": 1, "profile": 2}],
}

FLAP = {
    "id": 3,
    "household_id": 100,
    "name": "Flap",
    "product_id": 6,
    "parent_device_id": 1,
    "control": {
        "curfew": [{"enabled": True, "lock_time": "19:00", "unlock_time": "07:00"}],
        "locking": 0,
        "fail_safe": 0,
        "non_selective_exit": True,
        "non_selective_entry": False,
    },
    "status": {**STATUS, "learn_mode": True, "locking": {"mode": 0}},
    "tags": [
        {"id": 501, "device_id": 3, "index": 1, "profile": 2},
        {"id": 502, "device_id": 3, "index": 2, "profile": 3},
    ],
}

FELAQUA = {
    "id": 4,
    "household_id": 100,
    "name": "Water",
    "product_id": 8,
    "parent_device_id": 1,
    "control": {"learn_mode": False, "fast_polling": False},
    "status": STATUS,
    "tags": [{"id": 502, "device_id": 4, "index": 1, "profile": 2}],
}


def test_hub_led_and_pairing_mode():
    hub = Hub(HUB)

    assert hub.led_mode == 4
    assert hub.pairing_mode is False


def test_hub_without_status():
    hub = Hub({**HUB, "status": None})

    assert hub.led_mode is None
    assert hub.pairing_mode is False


def test_feeder_training_mode_and_lid():
    feeder = Feeder(FEEDER)

    assert feeder.training_mode == 2
    assert feeder.lid_close_delay == 4
    assert feeder.learn_mode is False
    assert [tag.id for tag in feeder.tags.values()] == [501]


def test_feeder_without_control_block():
    feeder = Feeder({**FEEDER, "control": None})

    assert feeder.training_mode is None
    assert feeder.lid_close_delay is None


def test_flap_settings_and_tags():
    flap = Flap(FLAP)

    assert flap.curfew == [Curfew(enabled=True, lock_time="19:00", unlock_time="07:00")]
    assert flap.fail_safe == 0
    assert flap.non_selective_entry is False
    assert flap.non_selective_exit is True
    assert flap.learn_mode is True
    assert {tag.id: tag.profile() for tag in flap.tags.values()} == {501: 2, 502: 3}


def test_flap_curfew_as_single_dict():
    flap = Flap(
        {
            **FLAP,
            "control": {"curfew": {"enabled": False, "lock_time": "22:00", "unlock_time": "06:30"}},
        }
    )

    assert flap.curfew == [Curfew(enabled=False, lock_time="22:00", unlock_time="06:30")]


def test_flap_curfew_without_times():
    flap = Flap({**FLAP, "control": {"curfew": [{"enabled": False}]}})

    assert flap.curfew == [Curfew(enabled=False, lock_time=None, unlock_time=None)]


def test_flap_without_curfew():
    assert not Flap({**FLAP, "control": {"curfew": []}}).curfew


def test_felaqua_tags_and_learn_mode():
    felaqua = Felaqua(FELAQUA)

    assert [tag.id for tag in felaqua.tags.values()] == [502]
    assert felaqua.learn_mode is False


def test_learn_mode_unknown_without_status():
    assert Felaqua({**FELAQUA, "status": {}}).learn_mode is None


PET = {
    "id": 10,
    "household_id": 100,
    "name": "Rex",
    "tag_id": 503,
    "status": {
        "feeding": {
            "id": 1,
            "tag_id": 503,
            "device_id": 2,
            "change": [-11.15, 0.06],
            "at": "2026-11-03T08:07:32+00:00",
        },
        "drinking": {
            "id": 2,
            "tag_id": 503,
            "device_id": 4,
            "change": [-12.7],
            "at": "2026-10-27T00:14:48+00:00",
        },
    },
}


def test_pet_feeding_and_drinking_include_device():
    pet = Pet(PET)

    assert pet.feeding is not None
    assert pet.feeding.device_id == 2
    assert pet.feeding.change == [-11.15, 0.06]
    assert pet.feeding.at == datetime(2026, 11, 3, 8, 7, 32, tzinfo=timezone.utc)
    assert pet.drinking is not None
    assert pet.drinking.device_id == 4


def test_pet_without_feeding():
    assert Pet({**PET, "status": {}}).feeding is None
