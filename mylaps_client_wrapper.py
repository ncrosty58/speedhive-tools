from typing import Optional

from event_results_client import Client
from event_results_client.api.system_time_controller import get_time as time_api


def make_client(base_url: str = "https://api2.mylaps.com/v3", **kwargs) -> Client:
    """Create and return an `event_results_client.Client` instance.

    Any extra keyword args are forwarded to the generated `Client` constructor.
    """
    return Client(base_url=base_url, **kwargs)


def get_server_time(client: Optional[Client] = None):
    """Return the server time by calling the generated `system_time_controller`.

    If no `client` is provided, one is created with the default base_url.
    """
    client = client or make_client()
    return time_api.sync(client=client)


if __name__ == "__main__":
    c = make_client()
    t = get_server_time(c)
    print("Server time:", t)
