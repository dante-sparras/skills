import re
from dataclasses import dataclass
from pathlib import Path

from .textutil import digest, normalize_ws


@dataclass(frozen=True)
class Part:
    path: Path
    source: str
    body: str
    full: str

    @property
    def front(self):
        return self.full[:-len(self.body)] if self.body and self.body != self.full else ""


def read_text(path):
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"), newline


def write_text(path, text, newline):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    path.write_bytes(text.encode("utf-8"))


def split_frontmatter(text):
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", text
    line_end = text.find("\n", end + 1)
    if line_end < 0:
        return text, ""
    return text[:line_end + 1], text[line_end + 1:]


def parts(skill_dir):
    files = [path for path in skill_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".sh"}]
    files.sort(key=lambda path: (path.name != "SKILL.md", path.relative_to(skill_dir).as_posix()))
    result = []
    for path in files:
        text, _ = read_text(path)
        source = path.relative_to(skill_dir.parent.parent).as_posix()
        body = split_frontmatter(text)[1] if path == skill_dir / "SKILL.md" else text
        result.append(Part(path, source, body, text))
    return result


def bundle(skill_dir):
    return "\n".join(f"<!-- {part.source} -->\n{part.body.strip()}\n" for part in parts(skill_dir)).strip() + "\n"


def size(skill_dir):
    return sum(len(part.full) for part in parts(skill_dir))


def paragraph_blocks(text):
    pieces = re.split(r"(\n[ \t]*\n)", text)
    return [(pieces[index], pieces[index + 1] if index + 1 < len(pieces) else "") for index in range(0, len(pieces), 2)]


def paragraph_key(source, paragraph):
    return digest(source, paragraph)


def paragraphs(skill_dir):
    return {
        paragraph_key(part.source, paragraph): (part.source, paragraph)
        for part in parts(skill_dir)
        for paragraph, _ in paragraph_blocks(part.body)
        if paragraph.strip()
    }


def span_paragraphs(span, source, paragraphs_by_key):
    wanted = normalize_ws(span)
    by_path = {}
    for key, (path, paragraph) in paragraphs_by_key.items():
        by_path.setdefault(path, []).append((key, normalize_ws(paragraph)))
    matches = {}
    for path, pieces in by_path.items():
        body = " ".join(text for _, text in pieces)
        ranges = [(match.start(), match.end()) for match in re.finditer(re.escape(wanted), body)]
        start = 0
        for key, text in pieces:
            end = start + len(text)
            if any(left < end and start < right for left, right in ranges):
                matches.setdefault(path, []).append(key)
            start = end + 1
    if not matches:
        raise ValueError("span matches no paragraph")
    return sorted(matches.get(source) or [key for group in matches.values() for key in group])


def apply_paragraph_edits(skill_dir, edits):
    for part in parts(skill_dir):
        pieces = []
        for paragraph, separator in paragraph_blocks(part.body):
            replacement = paragraph
            if paragraph.strip() and paragraph_key(part.source, paragraph) in edits:
                replacement = edits[paragraph_key(part.source, paragraph)]
                if replacement:
                    replacement = replacement.strip() + paragraph[len(paragraph.rstrip()):]
            pieces.append(replacement + separator if replacement or not paragraph else "")
        text = part.front + "".join(pieces)
        if text.strip() and text != part.full:
            write_text(part.path, text, read_text(part.path)[1])
