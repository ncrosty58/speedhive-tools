from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    vendor_id: str | Unset = UNSET,
    package_id: str | Unset = UNSET,
    login_name: str | Unset = UNSET,
    login_pass: str | Unset = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["VendorID"] = vendor_id

    params["PackageID"] = package_id

    params["loginName"] = login_name

    params["loginPass"] = login_pass

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "head",
        "url": "/upload/thirdparty/signin",
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
    vendor_id: str | Unset = UNSET,
    package_id: str | Unset = UNSET,
    login_name: str | Unset = UNSET,
    login_pass: str | Unset = UNSET,
) -> Response[Any]:
    """
    Args:
        vendor_id (str | Unset):
        package_id (str | Unset):
        login_name (str | Unset):
        login_pass (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        vendor_id=vendor_id,
        package_id=package_id,
        login_name=login_name,
        login_pass=login_pass,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    vendor_id: str | Unset = UNSET,
    package_id: str | Unset = UNSET,
    login_name: str | Unset = UNSET,
    login_pass: str | Unset = UNSET,
) -> Response[Any]:
    """
    Args:
        vendor_id (str | Unset):
        package_id (str | Unset):
        login_name (str | Unset):
        login_pass (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any]
    """

    kwargs = _get_kwargs(
        vendor_id=vendor_id,
        package_id=package_id,
        login_name=login_name,
        login_pass=login_pass,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)
