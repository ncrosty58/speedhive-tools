from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Callable, Optional, Tuple


def ndjson_writer(path: Path, compress: bool = True) -> Tuple[Any, Callable[[Any], None]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compress:
        fh = gzip.open(path.with_suffix(path.suffix + ".gz"), "wt", encoding="utf8")
    else:
        fh = open(path, "w", encoding="utf8")

    def write(obj: Any) -> None:
        fh.write(json.dumps(obj, ensure_ascii=False))
        fh.write("\n")

    return fh, write


def safe_load_json(raw: Optional[bytes]) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None
