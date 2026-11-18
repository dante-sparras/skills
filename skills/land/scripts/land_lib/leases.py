import re
from datetime import timedelta

from .core import LandError, canonical, now, overlaps, stamp


def in_flight(db):
    return db.execute("SELECT * FROM lease WHERE state = 'submitted' OR (state = 'active' AND expires > ?) ORDER BY id",
                      (stamp(),)).fetchall()


def paths_of(row):
    return row["paths"].split("\n")


def shown(row):
    return row["paths"].replace("\n", ", ") or "(whole repo)"


def held_on(row):
    return f"L{row['id']} held by {row['holder']} on {shown(row)}"


def wanted_paths(paths):
    items = [p for p in paths.split(",") if p.strip()]
    if not items:
        raise LandError("--paths names no path; pass . for the whole repository")
    return sorted({canonical(p) for p in items})


def refusal(store, db, holder, wanted, excluding=()):
    leases = [row for row in in_flight(db) if row["id"] not in excluding]
    clash = [row for row in leases if row["holder"] != holder and overlaps(wanted, paths_of(row))]
    if clash:
        return "paths overlap " + "; ".join(held_on(row) for row in clash)
    cap = store.contract.get("cap")
    if cap and len(leases) >= cap:
        holders = ", ".join(sorted({row["holder"] for row in leases}))
        return f"repository at its cap: {len(leases)} of {cap} changes in flight ({holders})"
    return ""


def until(ttl_hours):
    return stamp(now() + timedelta(hours=ttl_hours))


def claim(store, holder, paths, ttl_hours):
    wanted = wanted_paths(paths)
    with store.tx() as db:
        reason = refusal(store, db, holder, wanted)
        if reason:
            raise LandError(reason)
        cursor = db.execute("INSERT INTO lease (at, holder, paths, state, expires) VALUES (?, ?, ?, 'active', ?)",
                            (stamp(), holder, "\n".join(wanted), until(ttl_hours)))
        store.log(db, "lease", cursor.lastrowid, "active", holder)
    return f"L{cursor.lastrowid}"


def check(store, holder, paths):
    reason = refusal(store, store.db, holder, wanted_paths(paths))
    return (reason, 1) if reason else ("free", 0)


def active_row(db, number):
    row = db.execute("SELECT * FROM lease WHERE id = ?", (number,)).fetchone()
    if not row:
        raise LandError(f"no L{number}")
    if row["state"] == "submitted":
        raise LandError(f"L{number} is submitted; the queue holds it until its entry lands or bounces")
    if row["state"] == "released":
        raise LandError(f"L{number} is released")
    return row


def renew(store, number, ttl_hours, if_live):
    with store.tx() as db:
        row = active_row(db, number)
        expired = row["expires"] <= stamp()
        if expired and if_live:
            raise LandError(f"L{number} expired at {row['expires'][:16]}")
        if expired:
            reason = refusal(store, db, row["holder"], paths_of(row), excluding={number})
            if reason:
                raise LandError(f"L{number} expired and {reason}; claim again once that clears")
        db.execute("UPDATE lease SET expires = ? WHERE id = ?", (until(ttl_hours), number))
        store.log(db, "lease", number, "renewed", "after it expired" if expired else "")
    return f"L{number} renewed"


def widen(store, number, paths, ttl_hours):
    with store.tx() as db:
        row = active_row(db, number)
        merged = sorted({*paths_of(row), *wanted_paths(paths)})
        reason = refusal(store, db, row["holder"], merged, excluding={number})
        if reason:
            raise LandError(reason)
        expires = until(ttl_hours) if row["expires"] <= stamp() else row["expires"]
        db.execute("UPDATE lease SET paths = ?, expires = ? WHERE id = ?", ("\n".join(merged), expires, number))
        store.log(db, "lease", number, "widened", ", ".join(merged))
    return f"L{number} widened"


def release(store, number):
    with store.tx() as db:
        row = db.execute("SELECT * FROM lease WHERE id = ?", (number,)).fetchone()
        if not row or row["state"] != "active":
            raise LandError(f"L{number} is not active; a submitted lease is released when its entry lands or bounces")
        release_lease(store, db, number)
    return f"L{number} released"


def release_lease(store, db, number, note=""):
    db.execute("UPDATE lease SET state = 'released' WHERE id = ?", (number,))
    store.log(db, "lease", number, "released", note)


def listing(store):
    rows = in_flight(store.db)
    return "\n".join(f"L{r['id']} {r['state']} {r['holder']} until {r['expires'][:16]}: {shown(r)}" for r in rows) \
        or "no leases held"


def lease_id(text):
    if not re.fullmatch(r"L?\d+", text or ""):
        raise LandError(f"{text!r} is not a lease id such as L3")
    return int(text.lstrip("L"))


def entry_id(text):
    if not re.fullmatch(r"E?\d+", text or ""):
        raise LandError(f"{text!r} is not an entry id such as E3")
    return int(text.lstrip("E"))
