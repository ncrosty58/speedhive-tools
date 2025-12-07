
from typing import Any
from .config import Settings

class MissingGeneratedClient(RuntimeError):
    pass

def get_api_client(settings: Settings) -> Any:
    try:
        from event_results_client import Client, AuthenticatedClient  # generated package
    except Exception as e:
        raise MissingGeneratedClient(
            "Generated client not found. Run: pip install -e clients/python-speedhive"
        ) from e

    if settings.token:
        return AuthenticatedClient(
            base_url=settings.base_url, token=settings.token, timeout=settings.timeout
        )
    return Client(base_url=settings.base_url, timeout=settings.timeout)
