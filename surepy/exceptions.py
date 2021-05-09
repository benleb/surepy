from typing import Any


class SurePetcareError(Exception):
    """General Sure Petcare Error exception occurred."""


class SurePetcareConnectionError(SurePetcareError):
    """When a connection error is encountered."""


class SurePetcareAuthenticationError(SurePetcareError):
    """When a authentication error is encountered."""


class SurePetcareAPIError(SurePetcareError):
    """When a connection error is encountered."""

    def __init__(self, resource: str, response: Any, message: str) -> None:
        self.resource = resource
        self.response = response
        self.message = message
