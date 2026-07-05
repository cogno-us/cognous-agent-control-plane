"""Custom exceptions for Agent Control Plane."""


class AgentControlPlaneError(Exception):
    """Base exception for Agent Control Plane."""


class PolicyViolationError(AgentControlPlaneError):
    """Raised when a policy violation occurs that prevents execution."""


class FrameConfigurationError(AgentControlPlaneError):
    """Raised when a Frame is improperly configured."""


class ReplayError(AgentControlPlaneError):
    """Raised when a replay bundle cannot be constructed or loaded."""
