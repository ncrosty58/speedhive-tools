from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    count: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    sport: str | Unset = UNSET,
    sport_category: str | Unset = UNSET,
    country: str | Unset = UNSET,
    start_date: str | Unset = UNSET,
    end_date: str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["count"] = count

    params["offset"] = offset

    params["sport"] = sport

    params["sportCategory"] = sport_category

    params["country"] = country

    params["startDate"] = start_date

    params["endDate"] = end_date

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v2/events",
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
    *,
    client: AuthenticatedClient | Client,
    count: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    sport: str | Unset = UNSET,
    sport_category: str | Unset = UNSET,
    country: str | Unset = UNSET,
    start_date: str | Unset = UNSET,
    end_date: str | Unset = UNSET,
) -> Response[Any]:
    """
    Args:
        count (int | Unset):
        offset (int | Unset):
        sport (str | Unset):
        sport_category (str | Unset):
        country (str | Unset):
        start_date (str | Unset):
        end_date (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        count=count,
        offset=offset,
        sport=sport,
        sport_category=sport_category,
        country=country,
        start_date=start_date,
        end_date=end_date,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    count: int | Unset = UNSET,
    offset: int | Unset = UNSET,
    sport: str | Unset = UNSET,
    sport_category: str | Unset = UNSET,
    country: str | Unset = UNSET,
    start_date: str | Unset = UNSET,
    end_date: str | Unset = UNSET,
) -> Response[Any]:
    """
    Args:
        count (int | Unset):
        offset (int | Unset):
        sport (str | Unset):
        sport_category (str | Unset):
        country (str | Unset):
        start_date (str | Unset):
        end_date (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        count=count,
        offset=offset,
        sport=sport,
        sport_category=sport_category,
        country=country,
        start_date=start_date,
        end_date=end_date,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
