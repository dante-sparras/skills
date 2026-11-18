import json

from .core import Infrastructure, LandError, git, open_lock
from .leases import entry_id, in_flight
from .queue import Integration, attempt, build, fetch_trunk, pause, poll, reconcile, rewound
from .store import trunk_ref

BUSY = "queue busy: another run is landing and will take queued entries. Run land again later if entries stay queued."


def land(store):
    handle = open_lock(store.dir / "queue.lock")
    if handle is None:
        return BUSY
    out = {"landed": [], "bounced": [], "opened": [], "adopted": []}
    try:
        if store.contract.get("paused"):
            return f"queue paused: {store.contract['paused']}"
        reconcile(store)
        integration = Integration(store)
        if store.contract["mode"] == "human":
            if not rewound(store, fetch_trunk(store)):
                for entry in store.entries("awaiting-merge"):
                    poll(store, entry, out)
                for entry in store.entries("queued"):
                    build(store, integration, entry, out)
            return report(store, out)
        single, rounds = False, 0
        while (queued := store.entries("queued")) and not store.contract.get("paused"):
            rounds += 1
            if rounds > 4 * len(queued) + 4:
                break
            size = 1 if single else max(1, int(store.contract.get("batch") or 1))
            landed, bounced, requeued = attempt(store, integration, queued[:size])
            out["landed"] += landed
            out["bounced"] += bounced
            single = bool(requeued)
        return report(store, out)
    except Infrastructure as problem:
        with store.tx() as db:
            for entry in db.execute("SELECT id FROM entry WHERE state = 'landing'").fetchall():
                store.set_entry(db, entry["id"], "queued", candidate="", note=str(problem))
        pause(store, f"{problem}. Fix it, then run land.py resume")
        return report(store, out)
    finally:
        handle.close()


def report(store, out):
    rows = {row["id"]: row for row in store.db.execute("SELECT * FROM entry")}

    def named(ident, extra=""):
        return f"E{ident} ({rows[ident]['holder']}){extra}"

    lines = []
    if out["landed"]:
        lines.append("landed " + ", ".join(named(i) for i in out["landed"]))
    if out["opened"]:
        lines.append("opened PRs for " + ", ".join(named(i, f" {rows[i]['pr']}") for i in out["opened"]))
    lines += [f"adopted {named(i, ' ' + rows[i]['pr'])}" for i in out["adopted"]]
    lines += [f"bounced {named(i, ': ' + rows[i]['note'])}" for i in out["bounced"]]
    waiting = [f"E{row['id']}" for row in rows.values() if row["state"] in ("queued", "landing")]
    if waiting:
        lines.append("still queued: " + ", ".join(waiting))
    awaiting = [named(row["id"], f" {row['pr']}") for row in rows.values() if row["state"] == "awaiting-merge"]
    if awaiting:
        lines.append("awaiting merge: " + ", ".join(awaiting))
    if store.contract.get("paused"):
        lines.append(f"queue paused: {store.contract['paused']}")
    return "\n".join(lines) or "nothing to land"


def holder_rows(store, holder, sha=None):
    if sha:
        resolved = git("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}", cwd=store.repo, check=False)
        sha = resolved.stdout.strip() if resolved.returncode == 0 else sha.lower()
    return [row for row in store.db.execute("SELECT * FROM entry ORDER BY id")
            if (row["holder"] == holder or (holder.endswith("/") and row["holder"].startswith(holder)))
            and (not sha or row["sha"] == sha)]


def holder_status(store, holder, sha=None, as_json=False):
    rows = holder_rows(store, holder, sha)
    if as_json:
        return json.dumps([{"id": f"E{row['id']}", "state": row["state"], "holder": row["holder"], "sha": row["sha"],
                            "pr": row["pr"], "note": row["note"]} for row in rows], indent=2)
    lines = []
    for row in rows:
        line = f"E{row['id']} {row['state']} ({row['holder']}, {row['sha'][:12]})"
        if row["state"] == "landed" and row["landed"]:
            line += f" as {row['landed'][:12]}"
        elif row["state"] == "awaiting-merge" and row["pr"]:
            line += f" awaiting merge {row['pr']}"
        elif row["state"] == "bounced":
            line += f": {row['note']}"
        lines.append(line)
    return "\n".join(lines) or f"no entries held by {holder}" + (f" at {sha}" if sha else "")


def status(store, ident=None):
    if ident:
        number = entry_id(ident)
        row = store.entry(number)
        if not row:
            raise LandError(f"no E{number}")
        detail = [f"reviewed by {row['reviewer']} at {row['sha'][:12]}",
                  f"landed as {row['landed'][:12]}" if row["landed"] else "", row["pr"], row["note"]]
        return f"E{row['id']} {row['state']} ({row['holder']}, {row['branch']})" + "".join(f". {p}" for p in detail if p)
    states = dict(store.db.execute("SELECT state, count(*) FROM entry GROUP BY state").fetchall())
    leases = len(in_flight(store.db))
    contract = store.contract
    parts = [f"{state}: {n}" for state, n in states.items()] + ([f"leases held: {leases}"] if leases else [])
    if contract.get("cap"):
        parts.append(f"changes in flight: {leases} of {contract['cap']}")
    paused = f" Paused: {contract['paused']}" if contract.get("paused") else ""
    return f"{contract['mode']} mode onto {trunk_ref(contract)}. " + (", ".join(parts) or "empty") + "." + paused
