from pathlib import Path

from .core import REMOTE_MODES, LandError, common_dir, git
from .store import Store, store_dir, trunk_ref

IN_FLIGHT = ("queued", "landing", "awaiting-merge")


def init(path, trunk, mode, remote, base, checks, setup, batch, timeout, cap):
    common = common_dir(path)
    repo = common.parent if common.name == ".git" else Path(git("rev-parse", "--show-toplevel", cwd=path).stdout.strip())
    with Store(store_dir(common)) as store:
        stored = store.contract

        def pick(key, passed, default):
            if passed is not None:
                return passed
            return stored.get(key, default)

        fixed = {"trunk": pick("trunk", trunk, None), "mode": pick("mode", mode, "human"),
                 "remote": pick("remote", remote, "origin")}
        if not fixed["trunk"]:
            raise LandError("the first init needs --trunk")
        moved = [key for key, value in fixed.items() if stored and stored.get(key) != value]
        busy = store.entries(*IN_FLIGHT)
        if moved and busy:
            raise LandError(f"{len(busy)} entries are queued, landing, or awaiting merge; "
                            f"change {', '.join(moved)} when the queue is empty")
        contract = {**fixed, "commonDir": str(common), "repo": str(repo)}
        if fixed["mode"] in REMOTE_MODES:
            git("remote", "get-url", fixed["remote"], cwd=repo)
            git("fetch", fixed["remote"], fixed["trunk"], cwd=repo)
        else:
            ref = trunk_ref(contract)
            if git("rev-parse", "--verify", "--quiet", ref, cwd=repo, check=False).returncode != 0:
                start = git("rev-parse", "--verify", f"{base or fixed['trunk']}^{{commit}}", cwd=repo).stdout.strip()
                git("update-ref", ref, start, cwd=repo)
        contract.update({
            "checks": pick("checks", checks or None, []),
            "setup": pick("setup", setup, ""),
            "batch": pick("batch", batch, 1),
            "timeout": pick("timeout", timeout, 1800),
            "cap": pick("cap", cap, 0),
        })
        if contract["batch"] < 1 or contract["timeout"] < 1 or contract["cap"] < 0:
            raise LandError("--batch and --timeout must be positive and --cap must not be negative")
        with store.tx() as db:
            for key, value in contract.items():
                store.put(db, key, value)
            if moved:
                db.execute("DELETE FROM contract WHERE key = 'tip'")
            store.log(db, "contract", 0, "init", fixed["mode"])
        return summary(store.contract)


def summary(contract):
    checks = "; ".join(contract.get("checks") or []) or "none"
    cap = f", cap {contract['cap']}" if contract.get("cap") else ""
    return f"{contract['mode']} mode onto {trunk_ref(contract)}, checks: {checks}{cap}"


def no_checks_note(contract):
    if contract.get("mode") not in ("push", "local") or contract.get("checks"):
        return ""
    return (f"warning: {contract['mode']} mode has no checks, so nothing gates a landing. "
            "Add one with land.py init --check <command>.")


def change_cap(store, count):
    if count < 0:
        raise LandError(f"cap {count} is negative")
    with store.tx() as db:
        store.put(db, "cap", count)
        store.log(db, "contract", count, "cap")
    return f"cap {count}" if count else "cap cleared"
