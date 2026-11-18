#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

from land_lib import leases
from land_lib.contract import change_cap, init, no_checks_note
from land_lib.core import MODES, LandError
from land_lib.drain import holder_status, land, status
from land_lib.governor import run_slot
from land_lib.queue import submit
from land_lib.store import Store


def parser():
    top = argparse.ArgumentParser(prog="land.py", description="Land many agents' work on one repository through one queue.")
    top.add_argument("--repo", default=".", help="any checkout of the repository (default: the current directory)")
    commands = top.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("init", help="write or update the repository's landing contract")
    setup.add_argument("--trunk", help="the one branch every change lands on (needed the first time)")
    setup.add_argument("--mode", choices=MODES, help="human (default): open a PR the user merges. push: push trunk. "
                                                     "local: move refs/landing/<trunk>")
    setup.add_argument("--remote", help="the remote holding trunk (default: origin)")
    setup.add_argument("--base", help="local mode: the commit refs/landing/<trunk> starts at (default: trunk)")
    setup.add_argument("--check", action="append", help="a check command the candidate must pass. Repeat for more")
    setup.add_argument("--setup", help="a command that installs dependencies before the checks")
    setup.add_argument("--batch", type=int, help="push and local mode: entries tried together (default: 1)")
    setup.add_argument("--timeout", type=int, help="seconds each check may run (default: 1800)")
    setup.add_argument("--cap", type=int, help="most changes in flight at once; 0 means no cap")

    cap = commands.add_parser("cap", help="set the most changes in flight at once; 0 clears it")
    cap.add_argument("count", type=int)

    lease = commands.add_parser("lease", help="claim, check, renew, widen, release, or list path leases")
    actions = lease.add_subparsers(dest="action", required=True)
    for name, text in (("claim", "claim paths for a holder; prints L<n> or why not"),
                       ("check", "say whether a claim would succeed now, claiming nothing")):
        sub = actions.add_parser(name, help=text)
        sub.add_argument("--holder", required=True, help="<run>/<task>")
        sub.add_argument("--paths", required=True, help="comma-separated files and directories; . is the whole repo")
        if name == "claim":
            sub.add_argument("--ttl-hours", type=float, default=6)
    renew = actions.add_parser("renew", help="extend a lease; an expired one is admitted again")
    renew.add_argument("id")
    renew.add_argument("--ttl-hours", type=float, default=6)
    renew.add_argument("--if-live", action="store_true", help="refuse an expired lease instead of admitting it again")
    widen = actions.add_parser("widen", help="add paths to an active lease")
    widen.add_argument("id")
    widen.add_argument("--paths", required=True)
    widen.add_argument("--ttl-hours", type=float, default=6)
    release = actions.add_parser("release", help="release an active lease")
    release.add_argument("id")
    actions.add_parser("list", help="list leases in flight")

    send = commands.add_parser("submit", help="queue a reviewed commit; prints E<n>")
    send.add_argument("--holder", required=True)
    send.add_argument("--branch", required=True)
    send.add_argument("--sha", required=True, help="the exact commit the reviewer passed")
    send.add_argument("--lease", required=True, help="L<n>")
    send.add_argument("--reviewer", required=True, help="<provider>/<model> of the reviewer")
    send.add_argument("--title", default="", help="human mode: the PR title (default: the commit subject)")
    send.add_argument("--body-file", help="human mode: a file holding the PR body (default: the commit body)")

    commands.add_parser("land", help="drain the queue; prints what landed, bounced, opened, or is still queued")
    look = commands.add_parser("status", help="the queue, one entry, or one holder's entries")
    look.add_argument("id", nargs="?", help="E<n>")
    look.add_argument("--holder", help="a holder, or a prefix ending in / for every holder under it")
    look.add_argument("--sha", help="with --holder: only entries at this commit")
    look.add_argument("--json", action="store_true", help="with --holder: JSON, one object per entry")
    commands.add_parser("resume", help="clear a pause after the user confirmed trunk is right")

    run = commands.add_parser("slot", help="run a heavy command under a governor slot")
    run.add_argument("--slots", type=int, default=1, help="worker slots to take at once (default: 1)")
    run.add_argument("--exclusive", action="store_true", help="hold every slot so nothing heavy runs beside a measurement")
    run.add_argument("--for", dest="seconds", type=int, help="exclusive: seconds before the command is stopped (default: 600)")
    run.add_argument("--reason", help="exclusive: why, needed for --for over 600")
    run.add_argument("cmd", nargs=argparse.REMAINDER)
    return top


def run(argv):
    args = parser().parse_args(argv)
    if args.command == "slot":
        command = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
        if not command:
            raise LandError("slot needs a command after --")
        if args.exclusive and args.slots != 1:
            raise LandError("--slots cannot be combined with --exclusive")
        return None, run_slot(command, args.slots, args.exclusive, args.seconds, args.reason)
    if args.command == "init":
        text = init(args.repo, args.trunk, args.mode, args.remote, args.base, args.check, args.setup,
                    args.batch, args.timeout, args.cap)
        with Store.for_repo(args.repo) as store:
            warning = no_checks_note(store.contract)
        if warning:
            print(warning, file=sys.stderr)
        return text, 0
    with Store.for_repo(args.repo) as store:
        if args.command == "cap":
            return change_cap(store, args.count), 0
        if args.command == "lease":
            if args.action == "claim":
                return leases.claim(store, args.holder, args.paths, args.ttl_hours), 0
            if args.action == "check":
                return leases.check(store, args.holder, args.paths)
            if args.action == "list":
                return leases.listing(store), 0
            number = leases.lease_id(args.id)
            if args.action == "renew":
                return leases.renew(store, number, args.ttl_hours, args.if_live), 0
            if args.action == "widen":
                return leases.widen(store, number, args.paths, args.ttl_hours), 0
            return leases.release(store, number), 0
        if args.command == "submit":
            body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
            return submit(store, args.holder, args.branch, args.sha, args.lease, args.reviewer, args.title, body), 0
        if args.command == "land":
            return land(store), 0
        if args.command == "resume":
            with store.tx() as db:
                db.execute("DELETE FROM contract WHERE key IN ('paused', 'tip')")
                store.log(db, "queue", 0, "resumed")
            return "queue resumed", 0
        if args.holder:
            if args.id:
                raise LandError("status takes an entry id or --holder, not both")
            return holder_status(store, args.holder, args.sha, args.json), 0
        if args.sha or args.json:
            raise LandError("status --sha and --json need --holder")
        text = status(store, args.id)
        warning = "" if args.id else no_checks_note(store.contract)
        if warning:
            print(warning, file=sys.stderr)
        return text, 0


def main(argv=None):
    try:
        output, code = run(sys.argv[1:] if argv is None else argv)
    except LandError as error:
        print(f"land: {error}", file=sys.stderr)
        return 1
    if output is not None:
        print(output)
    return code


if __name__ == "__main__":
    sys.exit(main())
