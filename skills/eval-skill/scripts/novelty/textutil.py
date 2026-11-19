import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def digest(*values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as output:
        output.write(json.dumps(value, ensure_ascii=False, indent=1).encode("utf-8"))
    temporary = Path(output.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def tokens(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def normalize_ws(text):
    return re.sub(r"\s+", " ", text or "").strip()


def strip_fence(text):
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    return re.sub(r"\s*```$", "", raw)


def json_between(text, opener, closer, what):
    raw = strip_fence(text)
    start, end = raw.find(opener), raw.rfind(closer)
    if start < 0 or end < start:
        raise ValueError(f"{what} returned no JSON")
    return json.loads(raw[start:end + 1])


def forbidden_punctuation(text):
    if "—" in text:
        return True
    fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            fence = not fence
            continue
        if not fence and ";" in re.sub(r"`[^`]*`", "", line):
            return True
    return False
