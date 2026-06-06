"""Shared errors for the Speedhive API."""

class SpeedhiveError(Exception):
    """Base exception for all Speedhive errors."""

class UnexpectedStatus(SpeedhiveError):
    """Raised when an undocumented HTTP status is returned."""

    def __init__(self, status_code: int, content: bytes):
        self.status_code = status_code
        self.content = content
        super().__init__(
            f"Unexpected status code: {status_code}\n\n"
            f"Response content:\n{content.decode(errors='ignore')}"
        )
