"""Other skills a skill builds on. Both arms get them, so the score is what the skill adds on top of them."""
import re
from dataclasses import dataclass
from pathlib import Path

from . import skillfiles

LINK = re.compile(r"\]\((\.\./[^)#\s]+)(?:#[^)]*)?\)")
NAMED = re.compile(r"[\"`]([a-z0-9]+(?:-[a-z0-9]+)*)[\"`]")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n")


@dataclass(frozen=True)
class Dependencies:
    text: str
    sources: list


def skill_tool_names(text, skills_root, own):
    """Skills a sentence tells the agent to load, as in: call the Skill tool with "grilling"."""
    names = []
    for sentence in SENTENCE.split(text):
        if "Skill tool" in sentence:
            names += [name for name in NAMED.findall(sentence)
                      if name != own and (skills_root / name / "SKILL.md").is_file()]
    return names


def linked_files(path, text, skills_root, own):
    """Files in other skills that a relative link points at."""
    found = []
    for target in LINK.findall(text):
        resolved = (path.parent / target).resolve()
        try:
            relative = resolved.relative_to(skills_root)
        except ValueError:
            continue
        if relative.parts[0] != own and resolved.is_file():
            found.append(resolved)
    return found


def dependencies(skills_root, name):
    """Skills the tested skill loads, and the files any loaded text links to. Skills a dependency loads in turn
    are left out, since the agent loads those only when it gets that far."""
    skills_root = Path(skills_root).resolve()
    own = [(part.path.resolve(), part.full) for part in skillfiles.parts(skills_root / name)]
    whole = list(dict.fromkeys(other for _, text in own for other in skill_tool_names(text, skills_root, name)))
    queue = own + [(part.path.resolve(), part.full) for other in whole for part in skillfiles.parts(skills_root / other)]
    seen = {path for path, _ in queue}
    files = []
    while queue:
        path, text = queue.pop(0)
        for linked in linked_files(path, text, skills_root, name):
            if linked not in seen:
                seen.add(linked)
                files.append(linked)
                queue.append((linked, skillfiles.read_text(linked)[0]))
    files = [path for path in files if path.relative_to(skills_root).parts[0] not in whole]
    blocks = [f'<skill name="{other}">\n{skillfiles.bundle(skills_root / other)}</skill>' for other in sorted(whole)]
    for path in sorted(files):
        source = path.relative_to(skills_root.parent).as_posix()
        blocks.append(f'<file path="{source}">\n{skillfiles.read_text(path)[0].strip()}\n</file>')
    sources = [f"skills/{other}" for other in sorted(whole)]
    sources += [path.relative_to(skills_root.parent).as_posix() for path in sorted(files)]
    return Dependencies("\n\n".join(blocks), sources)
