"""Link every skill in this repo into an agent's skills folder, and drop the links that have gone stale.

    python scripts/link-skills.py [--skills <folder>] [--dry-run] [<agent skills folder> ...]

With no folder named, it syncs ~/.claude/skills and ~/.agents/skills, whichever exist. Run it again
after a pull that adds, renames, or removes a skill.

A link is a junction on Windows and a symlink elsewhere. Only links that point into this repo's
skills folder are ever removed: a real folder, or a link to somewhere else, is left alone and reported.
"""
import argparse
import os
import sys
from pathlib import Path

DEFAULT_TARGETS = ["~/.claude/skills", "~/.agents/skills"]


def link_target(path):
    """Where a symlink or junction points, or None when the path is neither."""
    try:
        target = os.readlink(path)
    except (OSError, ValueError):
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return Path(os.path.normpath(os.path.join(path.parent, target)))


def same(a, b):
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def inside(path, folder):
    path, folder = os.path.normcase(os.path.normpath(path)), os.path.normcase(os.path.normpath(folder))
    return path.startswith(folder + os.sep)


def make_link(link, target):
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


def remove_link(link):
    try:
        os.unlink(link)
    except OSError:
        os.rmdir(link)


def sync(skills, target, dry_run=False):
    """Make `target` hold one link per skill in `skills`. Returns (action, name) pairs."""
    wanted = {p.parent.name: p.parent for p in sorted(skills.glob("*/SKILL.md"))}
    done = []
    target.mkdir(parents=True, exist_ok=True)
    for entry in sorted(target.iterdir()):
        points_at = link_target(entry)
        if points_at is None or not inside(points_at, skills):
            continue
        if entry.name in wanted and same(points_at, wanted[entry.name]):
            continue
        done.append(("removed", entry.name))
        if not dry_run:
            remove_link(entry)
    for name, folder in wanted.items():
        link = target / name
        points_at = link_target(link)
        if points_at is not None and same(points_at, folder):
            continue
        if os.path.lexists(link) and not (dry_run and ("removed", name) in done):
            done.append(("skipped", name))
            continue
        done.append(("linked", name))
        if not dry_run:
            make_link(link, folder)
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("targets", nargs="*", help="agent skills folders to sync")
    parser.add_argument("--skills", default=str(Path(__file__).resolve().parent.parent / "skills"), help="the skills folder to link from")
    parser.add_argument("--dry-run", action="store_true", help="print what would change, and change nothing")
    args = parser.parse_args()

    skills = Path(args.skills).expanduser().resolve()
    if not any(skills.glob("*/SKILL.md")):
        print(f"{skills} holds no skills. Pass the folder that holds them with --skills.")
        return 1
    targets = [Path(t).expanduser() for t in args.targets] or [p for p in (Path(t).expanduser() for t in DEFAULT_TARGETS) if p.is_dir()]
    if not targets:
        print("No agent skills folder found. Name one, such as ~/.claude/skills.")
        return 1
    for target in targets:
        done = sync(skills, target, args.dry_run)
        print(f"{target}:")
        for action in ("linked", "removed", "skipped"):
            names = [name for did, name in done if did == action]
            if not names:
                continue
            note = " (something else has that name, so it was left alone)" if action == "skipped" else ""
            print(f"  {action}: {', '.join(names)}{note}")
        if not done:
            print("  already in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
