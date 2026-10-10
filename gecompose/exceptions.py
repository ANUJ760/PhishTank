"""Exceptions for the GeCompose scheduling engine."""


class GeComposeError(Exception):
    """Base exception for all GeCompose errors."""
    pass


class ValidationError(GeComposeError):
    """Raised when problem input data or schedule validation fails."""
    pass


class SolverError(GeComposeError):
    """Raised when an internal solver error occurs."""
    pass
