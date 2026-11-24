"""Check the wiring between skills: layout, names, shape, invocation flags, the manifest, links, and skill calls.

Every skill lives at skills/<name>/, the same layout it installs to, so a link between two
skills is written as ../<name>/... The plugin that .claude-plugin/marketplace.json declares
lists every skill.

Each problem prints as path:line: what is wrong, then how to fix it.
"""
import json
import posixpath
import re
import sys
from pathlib import Path

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"(?<!\!)\[[^\]\n]*\]\(([^)\s]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
SKILL_CALL = re.compile(r"Skill tool(?: twice,)? (?:with|for) ((?:[`\"][a-z][a-z0-9-]*[`\"](?:,? (?:and |or )?)?)+)")
SKILL_TOKEN = re.compile(r"[`\"]([a-z][a-z0-9-]*)[`\"]")
EXTERNAL = ("http://", "https://", "mailto:")
MANIFEST = ".claude-plugin/marketplace.json"
DISPLAY_NAME = re.compile(r"^\s*display_name:\s*[\"']?(.*?)[\"']?\s*$", re.M)
REFERENCE_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")
REPORT_HEADING = re.compile(r"^#{1,6}\s+(?:\d+\.\s+)?(?:Reply|Report|Reporting|Output)\s*$", re.I)

# The skills an agent may load on its own, each with why. Every other skill is user-invoked.
# A skill belongs here when a person asks for it in plain words outside the factory, and it
# does no harm when it loads unasked: it files nothing, labels nothing, and starts no long job.
MODEL_INVOKED = {
    "debug": "A crash or a slowdown comes up in any session, and the skill is what stops an agent from guessing.",
    "pr": "Opening a PR comes up in any session, and the skill only shapes the PR's title and body.",
    "research": "A person asks for research in plain words, and its only output is a notes file.",
    "writing-for-agents": "It is reference, wanted whenever a skill or an AGENTS.md is edited.",
}


def find_skill_dirs(skills_root):
    """Every skill folder: skills/<name>/."""
    return sorted(p.parent for p in skills_root.glob("*/SKILL.md"))


def frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, colon, value = line.partition(":")
        if colon and key and key[0] not in " \t":
            fields[key.strip()] = value.strip().strip("\"'")
    return {}


def prose_lines(text):
    """Yield (number, line) for lines outside code fences."""
    fence = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE.match(line)
        if fence is None and match:
            fence = match.group(1)
            continue
        if fence is not None:
            closes = match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence)
            if closes and not line[match.end():].strip():
                fence = None
            continue
        yield number, line


def slug(heading):
    text = re.sub(r"[`*_]", "", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path):
    found = set()
    for _, line in prose_lines(path.read_text(encoding="utf-8")):
        match = HEADING.match(line)
        if match:
            found.add(slug(match.group(1)))
    return found


def owning_skill(path, skills):
    for name, skill_dir in skills.items():
        if skill_dir in path.parents:
            return name, skill_dir
    return None


def resolve_link(path, file_part, skills):
    """Resolve a link the way it resolves once skills are installed side by side."""
    owner = owning_skill(path, skills) if skills else None
    if owner is None:
        return (path.parent / file_part).resolve()
    name, skill_dir = owner
    here = posixpath.join(name, path.parent.relative_to(skill_dir).as_posix())
    virtual = posixpath.normpath(posixpath.join(here, file_part))
    target_skill, _, rest = virtual.partition("/")
    if target_skill not in skills:
        return None
    return (skills[target_skill] / rest).resolve() if rest else skills[target_skill]


def link_problems(path, skills=None):
    for number, line in prose_lines(path.read_text(encoding="utf-8")):
        for match in LINK.finditer(INLINE_CODE.sub(lambda m: " " * len(m.group()), line)):
            target = match.group(1)
            if target.startswith(EXTERNAL) or "<" in target or "{" in target:
                continue
            file_part, _, anchor = target.partition("#")
            dest = resolve_link(path, file_part, skills) if file_part else path
            if dest is None or not dest.exists():
                yield number, (
                    f"link target {target} does not exist. Fix the path. A link to another skill "
                    "is written ../<skill name>/<file>, as it resolves once skills are installed side by side."
                )
                continue
            if anchor and dest.is_file() and dest.suffix == ".md" and anchor not in anchors(dest):
                yield number, (
                    f"link target {target} names a heading that is not in {dest.name}. "
                    "Use the heading's text in lower case with spaces as hyphens."
                )


def skill_problems(skill_dir, user_invoked):
    skill_md = skill_dir / "SKILL.md"
    fields = frontmatter(skill_md.read_text(encoding="utf-8").splitlines())
    name = fields.get("name")
    if name != skill_dir.name:
        yield skill_md, 2, (
            f"frontmatter name is {name!r} but the folder is {skill_dir.name!r}. "
            "Make the name match the folder."
        )
    yaml_path = skill_dir / "agents" / "openai.yaml"
    if not yaml_path.is_file():
        yield skill_md, 1, (
            "has no agents/openai.yaml. Add one with interface.display_name and "
            "interface.short_description, as the other skills have."
        )
        return
    implicit_off = re.search(r"allow_implicit_invocation:\s*false", yaml_path.read_text(encoding="utf-8"))
    if (skill_dir.name in user_invoked) != bool(implicit_off):
        yield yaml_path, 1, (
            "disagrees with SKILL.md on invocation. A skill with disable-model-invocation: true "
            "needs policy.allow_implicit_invocation: false here, and a skill without it must "
            "not set that policy."
        )


def invocation_problems(skill_dir, user_invoked, model_invoked=MODEL_INVOKED):
    """Yield (path, line, problem) where a skill's invocation and MODEL_INVOKED disagree."""
    name = skill_dir.name
    if name not in user_invoked and name not in model_invoked:
        yield skill_dir / "SKILL.md", 2, (
            "can be triggered by an agent on its own, at the wrong moment. Add "
            "disable-model-invocation: true to its frontmatter: the flow sends agents to each "
            "skill's file, and a person can still type its name. If an agent must reach it "
            "unasked, list it in MODEL_INVOKED in scripts/check-skills.py with the reason."
        )
    if name in user_invoked and name in model_invoked:
        yield skill_dir / "SKILL.md", 2, (
            "sets disable-model-invocation: true, but MODEL_INVOKED in scripts/check-skills.py "
            "lists it. Remove the line from its frontmatter, or remove the skill from MODEL_INVOKED."
        )


def stale_model_invoked(skills, model_invoked=MODEL_INVOKED):
    """Yield each name in MODEL_INVOKED that no skill folder has."""
    return sorted(name for name in model_invoked if name not in skills)


def shape_problems(skill_dir):
    """Yield (path, line, problem) where a skill departs from the shape every skill shares."""
    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    lines = text.splitlines()
    yaml_path = skill_dir / "agents" / "openai.yaml"
    display = DISPLAY_NAME.search(yaml_path.read_text(encoding="utf-8")) if yaml_path.is_file() else None
    if display:
        title = f"# {display.group(1)}"
        body = lines.index("---", 1) + 1 if lines[:1] == ["---"] and "---" in lines[1:] else 0
        first = next((n for n in range(body, len(lines)) if lines[n].strip()), None)
        if first is None or lines[first].strip() != title:
            yield skill_md, (body if first is None else first) + 1, (
                f"body must open with the heading {title!r}. "
                "Every skill is titled with the display_name in its agents/openai.yaml."
            )
    for number, line in prose_lines(text):
        if REPORT_HEADING.match(line) and line.strip() != "## Report":
            yield skill_md, number, (
                f"names its closing section {line.strip()!r}. Name it '## Report', unnumbered, "
                "as every skill that hands back a result does."
            )
    for path in sorted(skill_dir.iterdir()):
        if path.is_dir() and path.name == "references":
            yield path, 1, "is a references folder. Put reference files beside SKILL.md, where the other skills keep them."
        elif path.suffix == ".md" and path.name != "SKILL.md" and not REFERENCE_NAME.match(path.name):
            yield path, 1, (
                "is not named in lower-case kebab-case. Rename it, such as model-roles.md, "
                "so only SKILL.md stands out in a skill's folder."
            )


def skill_call_problems(path, skills, user_invoked):
    for number, line in prose_lines(path.read_text(encoding="utf-8")):
        for call in SKILL_CALL.finditer(line):
            for token in SKILL_TOKEN.findall(call.group(1)):
                if token in user_invoked:
                    yield number, (
                        f"asks the Skill tool for {token}, which is user-invoked and will not load. "
                        f"Have the agent read ../{token}/SKILL.md and follow it instead."
                    )
                elif token not in skills:
                    yield number, (
                        f"asks the Skill tool for {token}, and no skill has that name. "
                        "Use an existing skill's folder name."
                    )


def layout_problems(skills_root):
    """Yield (path, problem) for skills that sit below skills/<name>/."""
    for nested in sorted(skills_root.glob("*/*/SKILL.md")):
        yield nested, (
            "sits in a subfolder. Move the skill to skills/<name>/SKILL.md: skills install side by side, "
            "and a link between two of them is written ../<name>/."
        )


def manifest_problems(repo, skill_dirs):
    """Yield problems where .claude-plugin/marketplace.json and the skill folders disagree."""
    manifest = repo / MANIFEST
    if not manifest.is_file():
        yield "is missing. Add it with one plugin that lists every skill."
        return
    try:
        plugins = json.loads(manifest.read_text(encoding="utf-8")).get("plugins", [])
    except json.JSONDecodeError as error:
        yield f"is not valid JSON ({error}). Fix the syntax."
        return
    listed = {}
    for plugin in plugins:
        group = plugin.get("name")
        for entry in plugin.get("skills", []):
            parts = entry.split("/")
            if len(parts) != 3 or parts[0] != "." or parts[1] != "skills":
                yield f"lists {entry!r} under {group!r}. Write each skill as ./skills/<name>."
                continue
            name = parts[2]
            if not (repo / "skills" / name / "SKILL.md").is_file():
                yield f"lists {entry!r}, which has no SKILL.md. Fix the path or remove the entry."
            if name in listed:
                yield f"lists the skill {name!r} under both {listed[name]!r} and {group!r}. Keep it in one plugin."
            listed[name] = group
    for skill_dir in skill_dirs:
        if skill_dir.name not in listed:
            yield (
                f"does not list ./skills/{skill_dir.name}. "
                "Add it to the plugin's skills, so a plugin install includes it."
            )


def main():
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    skills_root = repo / "skills"
    skill_dirs = find_skill_dirs(skills_root)
    skills = {p.name: p for p in skill_dirs}
    user_invoked = {
        p.name
        for p in skill_dirs
        if frontmatter((p / "SKILL.md").read_text(encoding="utf-8").splitlines()).get("disable-model-invocation") == "true"
    }
    found = 0

    def report(path, line, problem):
        nonlocal found
        found += 1
        print(f"{path.relative_to(repo).as_posix()}:{line}: {problem}")

    for path, problem in layout_problems(skills_root):
        report(path, 1, problem)

    for name in stale_model_invoked(skills):
        report(skills_root / name / "SKILL.md", 1, (
            "does not exist, but MODEL_INVOKED in scripts/check-skills.py lists the skill. "
            "Remove it there, or fix the name."
        ))

    for problem in manifest_problems(repo, skill_dirs):
        report(repo / MANIFEST, 1, problem)

    for skill_dir in skill_dirs:
        for path, line, problem in skill_problems(skill_dir, user_invoked):
            report(path, line, problem)
        for path, line, problem in invocation_problems(skill_dir, user_invoked):
            report(path, line, problem)
        for path, line, problem in shape_problems(skill_dir):
            report(path, line, problem)

    docs = sorted(skills_root.rglob("*.md")) + [p for p in (repo / "README.md", repo / "GLOSSARY.md") if p.is_file()]
    for path in docs:
        for line, problem in link_problems(path, skills):
            report(path, line, problem)
        for line, problem in skill_call_problems(path, skills, user_invoked):
            report(path, line, problem)

    readme = repo / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        for skill_dir in skill_dirs:
            link = f"{skill_dir.relative_to(repo).as_posix()}/SKILL.md"
            if link not in text:
                report(readme, 1, f"does not link {link}. Add the skill to a list in the README.")

    if found:
        print(f"\n{found} wiring problem(s) across {len(skill_dirs)} skills.")
        return 1
    print(f"Layout, names, shape, invocation flags, the manifest, links, and skill calls agree across {len(skill_dirs)} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
