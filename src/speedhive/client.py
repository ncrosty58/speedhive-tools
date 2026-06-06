"""Low‑level HTTP clients for the Speedhive API (no duplication)."""

import ssl
from typing import Any, Optional

import httpx
from attrs import define, field, evolve


@define
class BaseClient:
    base_url: str
    headers: dict[str, str] = field(factory=dict)
    cookies: dict[str, str] = field(factory=dict)
    timeout: Optional[httpx.Timeout] = None
    verify_ssl: bool | str | ssl.SSLContext = True
    follow_redirects: bool = False
    _client: Optional[httpx.Client] = field(default=None, init=False, repr=False)
    _async_client: Optional[httpx.AsyncClient] = field(default=None, init=False, repr=False)

    def _build_client(self, async_mode: bool = False):
        cls_ = httpx.AsyncClient if async_mode else httpx.Client
        return cls_(
            base_url=self.base_url,
            cookies=self.cookies,
            headers={**self.headers},
            timeout=self.timeout,
            verify=self.verify_ssl,
            follow_redirects=self.follow_redirects,
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


@define
class AuthenticatedClient(BaseClient):
    token: str = field(kw_only=True)
    prefix: str = "Bearer"
    auth_header_name: str = "Authorization"

    def _build_client(self, async_mode: bool = False):
        self.headers[self.auth_header_name] = f"{self.prefix} {self.token}" if self.prefix else self.token
        return super()._build_client(async_mode)

