import httpx
import pytest
from unittest.mock import patch

from speedhive.client import BaseClient, Client, AuthenticatedClient


def test_base_client_construction():
    c = BaseClient(base_url="https://example.com")
    assert c.base_url == "https://example.com"
    assert c.headers == {}
    assert c._client is None

def test_base_client_get_httpx_client():
    c = BaseClient(base_url="https://example.com", headers={"Accept": "application/json"})
    client = c.get_httpx_client()
    assert isinstance(client, httpx.Client)
    assert client.base_url == "https://example.com"
    assert client.headers["Accept"] == "application/json"

def test_base_client_context_manager():
    c = BaseClient(base_url="https://example.com")
    with c:
        assert c._client is not None
    assert c._client.is_closed

def test_authenticated_client_sets_auth_header():
    c = AuthenticatedClient(base_url="https://example.com", token="secret")
    client = c.get_httpx_client()
    assert client.headers["Authorization"] == "Bearer secret"

def test_authenticated_client_custom_header():
    c = AuthenticatedClient(
        base_url="https://example.com",
        token="mykey",
        prefix="Token",
        auth_header_name="X-Auth",
    )
    client = c.get_httpx_client()
    assert client.headers["X-Auth"] == "Token mykey"

def test_with_headers_returns_new_instance():
    c = Client(base_url="https://example.com")
    c2 = c.with_headers({"X-Custom": "value"})
    assert c2 is not c
    assert "X-Custom" not in c.headers
    assert c2.headers["X-Custom"] == "value"

def test_cookies():
    c = Client(base_url="https://example.com", cookies={"session": "abc"})
    client = c.get_httpx_client()
    assert client.cookies["session"] == "abc"
