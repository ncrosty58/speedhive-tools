from __future__ import annotations

"""Low‑level HTTP clients for the Speedhive API with built-in retry transport."""

import ssl
import time
import asyncio
from typing import Any, Optional

import httpx
from attrs import define, field, evolve


class HTTPXRetryTransport(httpx.HTTPTransport):
    def __init__(self, max_retries=3, backoff_factor=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def handle_request(self, request, *args, **kwargs):
        retries = 0
        while True:
            try:
                response = super().handle_request(request, *args, **kwargs)
                if response.status_code in (429, 502, 503, 504) and retries < self.max_retries:
                    response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                retries += 1
                if retries > self.max_retries:
                    if isinstance(exc, httpx.HTTPStatusError):
                        return exc.response
                    raise
                sleep_time = self.backoff_factor * (2 ** (retries - 1))
                time.sleep(sleep_time)


class AsyncHTTPXRetryTransport(httpx.AsyncHTTPTransport):
    def __init__(self, max_retries=3, backoff_factor=1.0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    async def handle_async_request(self, request, *args, **kwargs):
        retries = 0
        while True:
            try:
                response = await super().handle_async_request(request, *args, **kwargs)
                if response.status_code in (429, 502, 503, 504) and retries < self.max_retries:
                    response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                retries += 1
                if retries > self.max_retries:
                    if isinstance(exc, httpx.HTTPStatusError):
                        return exc.response
                    raise
                sleep_time = self.backoff_factor * (2 ** (retries - 1))
                await asyncio.sleep(sleep_time)


@define
class BaseClient:
    base_url: str
    headers: dict[str, str] = field(factory=dict)
    cookies: dict[str, str] = field(factory=dict)
    timeout: Optional[httpx.Timeout] = None
    verify_ssl: bool | str | ssl.SSLContext = True
    follow_redirects: bool = False
    raise_on_unexpected_status: bool = False
    _client: Optional[httpx.Client] = field(default=None, init=False, repr=False)
    _async_client: Optional[httpx.AsyncClient] = field(default=None, init=False, repr=False)

    def _build_client(self, async_mode: bool = False):
        if async_mode:
            cls_ = httpx.AsyncClient
            transport = AsyncHTTPXRetryTransport(verify=self.verify_ssl)
        else:
            cls_ = httpx.Client
            transport = HTTPXRetryTransport(verify=self.verify_ssl)

        return cls_(
            base_url=self.base_url,
            cookies=self.cookies,
            headers={**self.headers},
            timeout=self.timeout,
            verify=self.verify_ssl,
            follow_redirects=self.follow_redirects,
            transport=transport,
        )

    def get_httpx_client(self) -> httpx.Client:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def get_async_httpx_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = self._build_client(async_mode=True)
        return self._async_client

    def __enter__(self):
        self.get_httpx_client().__enter__()
        return self

    def __exit__(self, *args):
        if self._client:
            self._client.__exit__(*args)

    async def __aenter__(self):
        await self.get_async_httpx_client().__aenter__()
        return self

    async def __aexit__(self, *args):
        if self._async_client:
            await self._async_client.__aexit__(*args)

    def with_headers(self, headers: dict[str, str]) -> "BaseClient":
        return evolve(self, headers={**self.headers, **headers})

    def with_cookies(self, cookies: dict[str, str]) -> "BaseClient":
        return evolve(self, cookies={**self.cookies, **cookies})

    def with_timeout(self, timeout: httpx.Timeout) -> "BaseClient":
        return evolve(self, timeout=timeout)


@define
class Client(BaseClient):
    """Unauthenticated Speedhive client."""


@define(kw_only=True)
class AuthenticatedClient(BaseClient):
    token: str = field(kw_only=True)
    prefix: str = "Bearer"
    auth_header_name: str = "Authorization"

    def _build_client(self, async_mode: bool = False):
        self.headers[self.auth_header_name] = f"{self.prefix} {self.token}" if self.prefix else self.token
        return super()._build_client(async_mode)
