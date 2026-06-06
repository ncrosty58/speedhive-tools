"""NDJSON file helpers."""

import gzip
import json
from pathlib import Path
from typing import Iterator, Dict, Any

def open_ndjson(path: Path) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    opener = gzip.open if (path.suffix == ".gz" or path.name.endswith(".gz")) else open
    with opener(path, "rt", encoding="utf8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
