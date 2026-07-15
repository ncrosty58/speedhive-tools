"""Shared NDJSON conventions for row-shaped data.

One convention, used by the CLI exporters and by consumers of this library
(e.g. the speedhive-tools-ui curation storage): an optional first line
``{"_meta": {...}}`` carrying document-level fields, then one JSON object per
line. Loaders return plain dicts shaped ``{**meta, records_key: [rows]}``.
"""
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

META_KEY = "_meta"


def iter_ndjson_lines(doc: Dict[str, Any], records_key: str) -> Iterator[str]:
    """Yield NDJSON lines (without trailing newlines) for a document."""
    meta = {k: v for k, v in doc.items() if k != records_key}
    if meta:
        yield json.dumps({META_KEY: meta}, ensure_ascii=False)
    for row in doc.get(records_key) or []:
        yield json.dumps(row, ensure_ascii=False)


def dumps_ndjson(doc: Dict[str, Any], records_key: str) -> str:
    """Serialize a document to an NDJSON string (with trailing newline)."""
    return "\n".join(iter_ndjson_lines(doc, records_key)) + "\n"


def save_ndjson(path, doc: Dict[str, Any], records_key: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for line in iter_ndjson_lines(doc, records_key):
            f.write(line + "\n")


def parse_ndjson_lines(lines, records_key: str) -> Dict[str, Any]:
    """Parse an iterable of NDJSON lines into ``{**meta, records_key: [rows]}``."""
    meta: Dict[str, Any] = {}
    rows: List[Any] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict) and set(obj.keys()) == {META_KEY}:
            meta = obj[META_KEY] or {}
        else:
            rows.append(obj)
    doc = dict(meta)
    doc[records_key] = rows
    return doc


def load_ndjson(path, default: Dict[str, Any], records_key: str) -> Dict[str, Any]:
    """Load an NDJSON document, transparently migrating a legacy ``.json``
    document with the same stem the first time it's read (the old file is
    kept as ``*.json.migrated``). Returns a fresh copy of ``default`` when
    neither file exists."""
    path = Path(path)
    if not path.exists():
        migrated = migrate_legacy_json(path, records_key)
        if migrated is not None:
            return migrated
        doc = dict(default)
        doc[records_key] = list(default.get(records_key) or [])
        return doc
    with open(path) as f:
        parsed = parse_ndjson_lines(f, records_key)
    doc = dict(default)
    doc.update(parsed)
    return doc


def migrate_legacy_json(ndjson_path, records_key: str) -> Optional[Dict[str, Any]]:
    """One-time migration from an old pretty-printed .json document."""
    ndjson_path = Path(ndjson_path)
    legacy = ndjson_path.with_suffix(".json")
    if not legacy.exists():
        return None
    with open(legacy) as f:
        doc = json.load(f)
    save_ndjson(ndjson_path, doc, records_key)
    try:
        legacy.rename(legacy.with_suffix(".json.migrated"))
    except OSError:
        pass  # a concurrent worker won the rename race; content is identical
    return doc
