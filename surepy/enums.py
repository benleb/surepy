from enum import IntEnum


class SureEnum(IntEnum):
    """Sure base enum."""

    def __str__(self) -> str:
        return self.name.title()


class EntityType(SureEnum):
    """Sure Entity Types."""

    PET = 0  # artificial ID, not used by the Sure Petcare API
    HUB = 1  # Hub
    REPEATER = 2  # Repeater
    PET_FLAP = 3  # Pet Door Connect
    FEEDER = 4  # Microchip Pet Feeder Connect
    PROGRAMMER = 5  # Programmer
    CAT_FLAP = 6  # Cat Flap Connect


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
