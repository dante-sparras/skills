import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .clis import ADAPTERS, CallError, connect
from .seats import CLIS, PROJECT_PANEL, USER_PANEL, Panel
from .textutil import save_json

SKILL_DIRS = (".claude/skills", ".agents/skills", ".grok/skills", ".config/opencode/skills", ".codex/skills")
SKILLS_QUESTION = "List the name of every skill available to you, one per line. If there are none, reply NONE."


def installed_skills(root):
    folders = [Path.home() / folder for folder in SKILL_DIRS] + [root / "skills"]
    return sorted({path.parent.name for folder in folders if folder.is_dir() for path in folder.glob("*/SKILL.md")})


def reported_skills(text, names):
    return [name for name in names if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text, re.I)]


def probe(adapter, seat, names):
    started = time.monotonic()
    try:
        reply = adapter.ask(seat, "Answer in one word.", "Reply with the word OK.", threading.Event())
        if "ok" not in reply.text.lower():
            raise CallError(f"unexpected reply {reply.text[:80]!r}")
        listing = adapter.ask(seat, "Answer plainly.", SKILLS_QUESTION, threading.Event()).text
        seen = reported_skills(listing, names)
        if seen:
            raise CallError(f"the seat can see installed skills: {', '.join(seen)}")
        return seat.key, True, round(time.monotonic() - started, 1), ", ".join(reply.models) + ", sees no skills"
    except CallError as error:
        return seat.key, False, round(time.monotonic() - started, 1), str(error)[:300]


def check(panel, timeout):
    adapters, notes = connect(panel, timeout)
    names = installed_skills(panel.root)
    seats = list(dict.fromkeys(panel.seats()))
    with ThreadPoolExecutor(max_workers=len(seats)) as pool:
        results = list(pool.map(lambda seat: probe(adapters[seat.cli], seat, names), seats))
    return notes, results


def list_models(timeout):
    lines = []
    for cli in CLIS:
        try:
            note, models = ADAPTERS[cli](timeout).catalog()
        except (OSError, SystemExit) as error:
            lines.append(f"{cli}: unavailable ({error})")
            continue
        lines.append(f"{cli}: {note}")
        lines += [f"  {cli}:{model}" + (f"  efforts: {', '.join(efforts)}" if efforts else "") for model, efforts in models]
    return lines


def panel_command(args):
    panel = Panel.resolve(args)
    if args.list:
        print("\n".join(list_models(args.timeout)) + "\n")
    print("Resolved panel (role, seat, source):")
    for role, seat, source in panel.table():
        print(f"  {role}: {seat}  [{source}]")
    if panel.note:
        print(panel.note)
    failed = False
    if args.check:
        notes, results = check(panel, args.timeout)
        print("\nCheck:")
        for note in notes:
            print(f"  {note}")
        for seat, ok, seconds, detail in results:
            failed = failed or not ok
            print(f"  {'ok  ' if ok else 'FAIL'} {seat} in {seconds}s: {detail}")
    if args.save and not failed:
        target = panel.root / PROJECT_PANEL if args.project else USER_PANEL
        save_json(target, panel.as_file())
        print(f"\nSaved to {target}")
    return 1 if failed else 0
