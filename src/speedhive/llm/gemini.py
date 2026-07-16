"""LLM client (currently Google Gemini) used by the track-record parsers in
speedhive.llm.track_records.

Config is env-var only -- GEMINI_API_KEY / GEMINI_MODEL -- matching every
other credential this library's caller (speedhive-tools-ui) uses (e.g.
RESEND_API_KEY, GOTIFY_APP_TOKEN): no file-based config, no UI-editable
secret storage.
"""
import json
import os
from typing import Any, List, Optional

from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash"


def get_gemini_api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY")


def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL


def call_gemini_json(
    prompt: str,
    response_schema: Optional[dict] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.0,
    max_output_tokens: Optional[int] = None,
    timeout_ms: Optional[int] = None,
) -> Any:
    """Call Gemini and return the parsed JSON response.

    Raises RuntimeError if no API key is configured, or the underlying
    google-genai exception if the call itself fails.
    """
    key = api_key or get_gemini_api_key()
    if not key:
        raise RuntimeError(
            "No Gemini API key configured. Set the GEMINI_API_KEY environment variable."
        )

    http_options = types.HttpOptions(timeout=timeout_ms) if timeout_ms else None
    client = genai.Client(api_key=key, http_options=http_options)
    config_kwargs = {
        "temperature": temperature,
        "response_mime_type": "application/json",
    }
    if response_schema is not None:
        config_kwargs["response_schema"] = response_schema
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens

    response = client.models.generate_content(
        model=model or get_gemini_model(),
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    return json.loads(response.text)


def parse_track_record_text_with_gemini(text: str) -> Optional[dict]:
    """Drop-in replacement for speedhive.utils.lap_analysis.parse_track_record_text,
    backed by the configured Gemini model instead of a regex."""
    from speedhive.llm.track_records import parse_track_record_text_llm

    def _call(prompt: str, schema: dict) -> Any:
        return call_gemini_json(prompt, response_schema=schema)

    return parse_track_record_text_llm(text, _call)


def parse_track_records_bulk_with_gemini(texts: List[str]) -> List[Optional[dict]]:
    """Drop-in bulk replacement: parses an entire list of announcement texts
    in a single Gemini call instead of one call per announcement. Returns a
    list aligned with `texts` (record dict or None per position)."""
    from speedhive.llm.track_records import parse_track_record_texts_llm_bulk

    def _call(prompt: str, schema: dict) -> Any:
        # A single call covering hundreds/thousands of announcements needs
        # more room (both to generate and to respond) than the per-item path.
        return call_gemini_json(
            prompt,
            response_schema=schema,
            max_output_tokens=65536,
            timeout_ms=600_000,
        )

    return parse_track_record_texts_llm_bulk(texts, _call)
