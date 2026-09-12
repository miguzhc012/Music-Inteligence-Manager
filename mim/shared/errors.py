class MIMError(Exception):
    """Base exception for all MIM errors."""

class ConfigurationError(MIMError):
    """Raised when configuration is invalid."""