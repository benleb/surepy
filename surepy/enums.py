from enum import IntEnum


class SureEnum(IntEnum):
    """Sure base enum."""

    def __str__(self) -> str:
        return self.name.title()  # pylint: disable=no-member


class EntityType(SureEnum):
    """Sure Entity Types."""

    PET = 0  # artificial ID, not used by the Sure Petcare API
    HUB = 1  # Hub
    REPEATER = 2  # Repeater
    PET_FLAP = 3  # Pet Door Connect
    FEEDER = 4  # Microchip Pet Feeder Connect
    PROGRAMMER = 5  # Programmer
    CAT_FLAP = 6  # Cat Flap Connect
    FEEDER_LITE = 7  # Feeder Lite
    FELAQUA = 8  # Felaqua Connect


class LockState(SureEnum):
    """Sure Petcare API State IDs."""

    UNLOCKED = 0
    LOCKED_IN = 1
    LOCKED_OUT = 2
    LOCKED_ALL = 3
    CURFEW = 4
    CURFEW_LOCKED = -1
    CURFEW_UNLOCKED = -2
    CURFEW_UNKNOWN = -3


class Location(SureEnum):
    """Sure Locations."""

    INSIDE = 1
    OUTSIDE = 2
    UNKNOWN = -1


class FoodType(SureEnum):
    """Sure Food Types."""

    WET = 1
    DRY = 2
    BOTH = 3
    UNKNOWN = -1


class BowlPosition(SureEnum):
    """Sure Feeder Bowl side."""

    LEFT = 0
    RIGHT = 1


class Species(SureEnum):
    """Species of the pet."""

    CAT = 1
    DOG = 2


class TimelineEvent(SureEnum):
    """Sure timeline event types."""

    BATTERY_LOW = 1
    FOOD_FILLED = 21
    EAT = 22
    FEEDER_TARE = 24
    DRINK = 29
    REMINDER_FRESH_WATER = 32
    ANONYMOUS_DRINK = 34
