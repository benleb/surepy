class SurePetcareError(Exception):
    """General Sure Petcare Error exception occurred."""


class SurePetcareConnectionError(SurePetcareError):
    """When a connection error is encountered."""


class SurePetcareAuthenticationError(SurePetcareError):
    """When a authentication error is encountered."""
