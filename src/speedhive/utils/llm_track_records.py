"""LLM-based alternative to parse_track_record_text (see lap_analysis.py).

The regex parser only catches announcements matching one exact phrasing
("New Track/Class Record (TIME) for CLASS by DRIVER in MARQUE."). This module
extracts the same information from free-text announcements using an LLM,
tolerating phrasing the regex misses. It has no dependency on a specific LLM
provider -- the caller injects call_llm_fn, which must accept
(prompt: str, response_schema: dict) and return the parsed JSON response.
"""
from typing import Any, Callable, Dict, List, Optional

from speedhive.utils.lap_analysis import parse_time_value

TRACK_RECORD_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_record": {
            "type": "boolean",
            "description": "True only if this announcement reports a new track or class record being set.",
        },
        "low_confidence": {
            "type": "boolean",
            "description": (
                "True if is_record is true but you are NOT confident about the extraction -- "
                "e.g. the class, lap time, or driver name is ambiguous, garbled, or could "
                "reasonably be read more than one way. False if the extraction is clear-cut."
            ),
        },
        "classification": {
            "type": "string",
            "description": "The class/category abbreviation the record was set in, e.g. 'FA', 'GT3'.",
        },
        "lap_time": {
            "type": "string",
            "description": "The record lap time exactly as written, e.g. '1:01.861' or '58.204'.",
        },
        "driver": {
            "type": "string",
            "description": "The driver's name, with any leading car-number/position marker like '[12]' removed.",
        },
        "marque": {
            "type": "string",
            "description": "The car make/model if mentioned (e.g. 'Swift 01 4A'), otherwise omit.",
        },
    },
    "required": ["is_record"],
}

_PROMPT_TEMPLATE = """You are parsing a single motorsport session announcement to detect whether it reports a new track or class lap record.

Announcement text:
\"\"\"{text}\"\"\"

If the text announces a new track record or class record being set (including phrasings other than the standard template), extract the record's classification, lap time, driver, and marque/car if mentioned.

If the text is not about a track/class record, or explicitly says the record is unconfirmed/not official/rejected (e.g. contains "to be confirmed", "not a track record", "not a class record"), set is_record to false and omit the other fields.

If it IS a record but you're not fully confident in the extraction (ambiguous class abbreviation, garbled/unclear driver name, uncertain lap time), set low_confidence to true -- still fill in your best-effort values for the other fields.

Respond with JSON matching the schema."""


def build_track_record_prompt(text: str) -> str:
    return _PROMPT_TEMPLATE.format(text=text)


def parse_track_record_text_llm(
    text: str,
    call_llm_fn: Callable[[str, dict], Any],
) -> Optional[Dict[str, Any]]:
    """Parse announcement text for a track record using an injected LLM call.

    Returns dict with keys 'lap_time', 'lap_time_seconds', 'classification',
    'driver', 'marque', 'llm_uncertain' or None if not a track record at all --
    same shape as parse_track_record_text plus 'llm_uncertain', so it's a
    drop-in replacement (callers that don't know about 'llm_uncertain' can
    just ignore it).

    A record with 'llm_uncertain': True is still returned (not dropped) so
    that low-confidence extractions stay visible and reviewable downstream
    (run_sync_and_diff routes these straight to rejected) rather than
    silently vanishing.
    """
    if not text or not text.strip():
        return None

    prompt = build_track_record_prompt(text)
    result = call_llm_fn(prompt, TRACK_RECORD_RESPONSE_SCHEMA)

    if not isinstance(result, dict) or not result.get("is_record"):
        return None

    classification = (result.get("classification") or "").strip()
    lap_time_str = (result.get("lap_time") or "").strip()
    driver = (result.get("driver") or "").strip()
    marque = (result.get("marque") or "").strip() or None

    # A missing required field is itself a sign the extraction is unreliable,
    # even if the model didn't flag low_confidence itself.
    uncertain = bool(result.get("low_confidence")) or not classification or not lap_time_str

    return {
        "lap_time": lap_time_str or None,
        "lap_time_seconds": parse_time_value(lap_time_str) if lap_time_str else None,
        "classification": classification or None,
        "driver": driver,
        "marque": marque,
        "llm_uncertain": uncertain,
    }


# --- Bulk variant: parse an entire list of announcements in one LLM call ---
#
# The per-text version above makes one round trip per announcement, which is
# fine for an incremental scan (a handful of new announcements) but far too
# slow/expensive for a one-off pass over a whole org's history (hundreds to
# thousands of announcements, almost all of which aren't records at all).
# This variant embeds every text in a single prompt and asks for one sparse
# array back (only entries that ARE records), cutting the whole job to one
# API call instead of one per announcement.

BULK_TRACK_RECORD_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "description": (
                "One entry per announcement that reports a new track/class record. "
                "Do NOT include an entry for announcements that aren't about a record -- "
                "skip those entirely rather than listing them with is_record=false."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The announcement's index number from the input list.",
                    },
                    "low_confidence": {
                        "type": "boolean",
                        "description": (
                            "True if you are NOT confident about this extraction -- e.g. the "
                            "class, lap time, or driver name is ambiguous, garbled, or could "
                            "reasonably be read more than one way."
                        ),
                    },
                    "classification": {
                        "type": "string",
                        "description": "The class/category abbreviation the record was set in, e.g. 'FA', 'GT3'.",
                    },
                    "lap_time": {
                        "type": "string",
                        "description": "The record lap time exactly as written, e.g. '1:01.861' or '58.204'.",
                    },
                    "driver": {
                        "type": "string",
                        "description": "The driver's name, with any leading car-number/position marker like '[12]' removed.",
                    },
                    "marque": {
                        "type": "string",
                        "description": "The car make/model if mentioned (e.g. 'Swift 01 4A'), otherwise omit.",
                    },
                },
                "required": ["index", "classification", "lap_time"],
            },
        },
    },
    "required": ["results"],
}

_BULK_PROMPT_TEMPLATE = """You are parsing a list of {count} motorsport session announcements, each labeled with an index number, to find which ones report a NEW track record or class record being set (including phrasings other than a single standard template).

Ignore announcements that are not about a record, or that explicitly say the record is unconfirmed/not official/rejected (e.g. contains "to be confirmed", "not a track record", "not a class record").

Only include an entry in your "results" array for announcements that ARE reporting a new record -- skip every other announcement entirely, do not list it at all.

Announcements:
{items}

Respond with JSON matching the schema -- a "results" array with one entry per record found."""


def build_bulk_track_record_prompt(texts: List[str]) -> str:
    items = "\n".join(f"[{i}] {text}" for i, text in enumerate(texts))
    return _BULK_PROMPT_TEMPLATE.format(count=len(texts), items=items)


def parse_track_record_texts_llm_bulk(
    texts: List[str],
    call_llm_fn: Callable[[str, dict], Any],
) -> List[Optional[Dict[str, Any]]]:
    """Parse an entire list of announcement texts in a single LLM call.

    Returns a list the same length as `texts`, aligned by position: each
    entry is either a record dict (same shape as parse_track_record_text_llm's
    return value) or None (not a record). Makes exactly one call for the
    whole list rather than one per announcement.
    """
    results: List[Optional[Dict[str, Any]]] = [None] * len(texts)
    if not texts:
        return results

    prompt = build_bulk_track_record_prompt(texts)
    response = call_llm_fn(prompt, BULK_TRACK_RECORD_RESPONSE_SCHEMA)

    items = response.get("results") if isinstance(response, dict) else None
    if not isinstance(items, list):
        return results

    for item in items:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        if not isinstance(idx, int) or not (0 <= idx < len(texts)):
            continue

        classification = (item.get("classification") or "").strip()
        lap_time_str = (item.get("lap_time") or "").strip()
        driver = (item.get("driver") or "").strip()
        marque = (item.get("marque") or "").strip() or None
        uncertain = bool(item.get("low_confidence")) or not classification or not lap_time_str

        results[idx] = {
            "lap_time": lap_time_str or None,
            "lap_time_seconds": parse_time_value(lap_time_str) if lap_time_str else None,
            "classification": classification or None,
            "driver": driver,
            "marque": marque,
            "llm_uncertain": uncertain,
        }

    return results
