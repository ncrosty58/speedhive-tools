"""LLM-based track-record parsing.

- `speedhive.llm.gemini` -- the actual Gemini client (env-var config, the
  network-calling code).
- `speedhive.llm.track_records` -- provider-agnostic prompt/schema/parsing
  logic; takes an injected call_llm_fn so it has no dependency on Gemini
  specifically.

The common entry points are re-exported here for convenience:

    from speedhive.llm import parse_track_records_bulk_with_gemini
"""
from speedhive.llm.gemini import (
    DEFAULT_MODEL,
    call_gemini_json,
    get_gemini_api_key,
    get_gemini_model,
    parse_track_record_text_with_gemini,
    parse_track_records_bulk_with_gemini,
)

__all__ = [
    "DEFAULT_MODEL",
    "call_gemini_json",
    "get_gemini_api_key",
    "get_gemini_model",
    "parse_track_record_text_with_gemini",
    "parse_track_records_bulk_with_gemini",
]
