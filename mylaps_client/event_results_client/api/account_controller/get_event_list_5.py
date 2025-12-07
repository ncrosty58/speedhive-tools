from http import HTTPStatus
from typing import Any
from urllib.parse import quote

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import UNSET, Response, Unset


def _get_kwargs(
    global_account_id: str,
    *,
    count: int | Unset = 100,
    offset: int | Unset = 0,
    sport: str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["count"] = count

    params["offset"] = offset

    params["sport"] = sport

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/accounts/{global_account_id}/events".format(
            global_account_id=quote(str(global_account_id), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | None:
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    global_account_id: str,
    *,
    client: AuthenticatedClient | Client,
    count: int | Unset = 100,
    offset: int | Unset = 0,
    sport: str | Unset = UNSET,
) -> Response[Any]:
    """
    Args:
        global_account_id (str):
        count (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        sport (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        global_account_id=global_account_id,
        count=count,
        offset=offset,
        sport=sport,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    global_account_id: str,
    *,
    client: AuthenticatedClient | Client,
    count: int | Unset = 100,
    offset: int | Unset = 0,
    sport: str | Unset = UNSET,
) -> Response[Any]:
    """
    Args:
        global_account_id (str):
        count (int | Unset):  Default: 100.
        offset (int | Unset):  Default: 0.
        sport (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        global_account_id=global_account_id,
        count=count,
        offset=offset,
        sport=sport,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
