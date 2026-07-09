class STTProjectError(Exception):
    """Base exception for STT AI project errors."""


class ProjectAlreadyExistsError(STTProjectError):
    """Raised when trying to create a project that already exists."""


class InvalidProjectError(STTProjectError):
    """Raised when a folder is not a valid STT AI project."""


class ProjectConfigError(STTProjectError):
    """Raised when project config cannot be read or written."""
