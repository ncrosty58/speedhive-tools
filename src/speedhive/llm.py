"""LLM client (currently Google Gemini) used by the track-record parsers in
speedhive.utils.llm_track_records.

Config is env-var based -- GEMINI_API_KEY / GEMINI_MODEL, or their per-org
variants GEMINI_API_KEY_<org_id> / GEMINI_MODEL_<org_id> when an org_id is
given, falling back to the bare name as a shared default. Resolution goes
through speedhive.settings, which any process (a CLI invocation or a host
application) resolves the same way.
"""
import os
from typing import Any, List, Optional

from google import genai
from google.genai import types

from speedhive.settings import get_org_env_var


def get_gemini_api_key(org_id: Optional[int] = None) -> Optional[str]:
    if org_id is not None:
        return get_org_env_var("GEMINI_API_KEY", org_id)
    return os.environ.get("GEMINI_API_KEY")


def get_gemini_model(org_id: Optional[int] = None) -> Optional[str]:
    if org_id is not None:
        return get_org_env_var("GEMINI_MODEL", org_id)
    return os.environ.get("GEMINI_MODEL")


def call_gemini_json(
    prompt: str,
    response_schema: Optional[dict] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.0,
    max_output_tokens: Optional[int] = None,
    timeout_ms: Optional[int] = None,
    org_id: Optional[int] = None,
) -> Any:
    """Call Gemini and return the parsed JSON response.

    Raises RuntimeError if no API key or model is configured, or the underlying
    google-genai exception if the call itself fails.
    """
    key = api_key or get_gemini_api_key(org_id)
    if not key:
        suffix = f" (or GEMINI_API_KEY_{org_id})" if org_id is not None else ""
        raise RuntimeError(
            f"No Gemini API key configured. Set the GEMINI_API_KEY{suffix} environment variable."
        )

    model_name = model or get_gemini_model(org_id)
    if not model_name:
        suffix = f" (or GEMINI_MODEL_{org_id})" if org_id is not None else ""
        raise RuntimeError(
            f"No Gemini model configured. Set the GEMINI_MODEL{suffix} environment variable."
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
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    return json.loads(response.text)


def parse_track_record_text_with_gemini(text: str, org_id: Optional[int] = None) -> Optional[dict]:
    """Drop-in replacement for speedhive.utils.lap_analysis.parse_track_record_text,
    backed by the configured Gemini model instead of a regex."""
    from speedhive.utils.llm_track_records import parse_track_record_text_llm

    def _call(prompt: str, schema: dict) -> Any:
        return call_gemini_json(prompt, response_schema=schema, org_id=org_id)

    return parse_track_record_text_llm(text, _call)


def parse_track_records_bulk_with_gemini(texts: List[str], org_id: Optional[int] = None) -> List[Optional[dict]]:
    """Drop-in bulk replacement: parses an entire list of announcement texts
    in a single Gemini call instead of one call per announcement. Returns a
    list aligned with `texts` (record dict or None per position)."""
    from speedhive.utils.llm_track_records import parse_track_record_texts_llm_bulk

    def _call(prompt: str, schema: dict) -> Any:
        # A single call covering hundreds/thousands of announcements needs
        # more room (both to generate and to respond) than the per-item path.
        return call_gemini_json(
            prompt,
            response_schema=schema,
            max_output_tokens=65536,
            timeout_ms=600_000,
            org_id=org_id,
        )

    return parse_track_record_texts_llm_bulk(texts, _call)
