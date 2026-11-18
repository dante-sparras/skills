import json
from datetime import timedelta

from .core import Infrastructure, LandError, changed_paths, covered, fingerprint, gh, git, git_push, git_reason, now, stamp, tail
from .governor import run_build, slot
from .leases import lease_id, release_lease
from .store import pin_ref, trunk_ref

ALREADY_IN_TRUNK = "already-in-trunk"
PR_STATES = ("OPEN", "CLOSED", "MERGED")


def fetch_trunk(store):
    contract = store.contract
    if contract["mode"] != "local":
        git("fetch", contract["remote"], contract["trunk"], cwd=store.repo)
    return git("rev-parse", trunk_ref(contract), cwd=store.repo).stdout.strip()


def submit(store, holder, branch, sha, lease, reviewer, title, body):
    repo, number = store.repo, lease_id(lease)
    sha = git("rev-parse", "--verify", f"{sha}^{{commit}}", cwd=repo).stdout.strip()
    trunk = fetch_trunk(store)
    base = git("merge-base", trunk, sha, cwd=repo).stdout.strip()
    if git("rev-list", "--merges", f"{base}..{sha}", "--", cwd=repo).stdout.strip():
        raise LandError(f"{branch} has merge commits; make its history linear on {store.contract['trunk']} first")
    files = changed_paths(repo, base, sha)
    if not files:
        raise LandError(f"{sha[:12]} changes nothing relative to {store.contract['trunk']}")
    print_ = fingerprint(repo, base, sha)
    git("update-ref", pin_ref(sha), sha, cwd=repo)
    with store.tx() as db:
        existing = db.execute("SELECT id, state FROM entry WHERE sha = ? AND holder = ?", (sha, holder)).fetchone()
        if existing and existing["state"] != "bounced":
            return f"E{existing['id']} already {existing['state']}"
        row = db.execute("SELECT * FROM lease WHERE id = ?", (number,)).fetchone()
        if not row or row["holder"] != holder or row["state"] != "active" or row["expires"] <= stamp():
            raise LandError(f"L{number} is not an active lease held by {holder}; claim one before submitting")
        outside = [f for f in files if not covered(f, row["paths"].split("\n"))]
        if outside:
            raise LandError(f"changes paths outside L{number}: {', '.join(outside)}; widen the lease or split the change")
        if existing:
            db.execute("DELETE FROM entry WHERE id = ?", (existing["id"],))
        cursor = db.execute("INSERT INTO entry (at, holder, branch, sha, base, fingerprint, lease, reviewer, state, title, body) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)",
                            (stamp(), holder, branch, sha, base, print_, number, reviewer, title, body))
        db.execute("UPDATE lease SET state = 'submitted' WHERE id = ?", (number,))
        store.log(db, "entry", cursor.lastrowid, "queued", f"{holder}: {branch}")
    return f"E{cursor.lastrowid}"


def committer(repo):
    if git("config", "user.email", cwd=repo, check=False).stdout.strip():
        return []
    return ["-c", "user.name=land queue", "-c", "user.email=land@localhost"]


def stopped_for_conflict(result):
    detail = result.stderr + result.stdout
    return "CONFLICT" in detail or "could not apply" in detail


class Integration:
    def __init__(self, store):
        self.store = store
        self.path = store.dir / "integration"
        if not (self.path / ".git").exists():
            git("worktree", "prune", cwd=store.repo, check=False)
            git("worktree", "add", "--detach", str(self.path), trunk_ref(store.contract), cwd=store.repo)

    def git(self, *args, check=True):
        return git(*args, cwd=self.path, check=check)

    def reset(self, commit):
        for operation in ("cherry-pick", "rebase", "merge"):
            self.git(operation, "--abort", check=False)
        self.git("checkout", "--force", "--detach", commit)
        self.git("reset", "--hard", commit)
        self.git("clean", "-ffdx")

    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()

    def give_up(self, before, reason):
        self.git("reset", "--hard", before, check=False)
        return reason

    def picked_empty(self):
        picked = self.git("rev-parse", "-q", "--verify", "CHERRY_PICK_HEAD", check=False)
        if picked.returncode != 0:
            return None
        sha = picked.stdout.strip()
        parent_tree = self.git("rev-parse", "-q", "--verify", f"{sha}^^{{tree}}", check=False).stdout.strip()
        own_tree = self.git("rev-parse", "-q", "--verify", f"{sha}^{{tree}}", check=False).stdout.strip()
        return sha, parent_tree == own_tree

    def skip_emptied(self, result, spec, identity):
        counted = self.git("rev-list", "--count", spec, "--", check=False)
        remaining = int(counted.stdout.strip() or "0") if counted.returncode == 0 else 0
        while result.returncode != 0 and remaining > 0 and not stopped_for_conflict(result):
            picked = self.picked_empty()
            dirty = (self.git("diff", "--quiet", check=False).returncode != 0
                     or self.git("diff", "--cached", "--quiet", check=False).returncode != 0)
            if picked is None or picked[1] or dirty:
                break
            result = self.git(*identity, "-c", "rerere.enabled=false", "cherry-pick", "--skip", check=False)
            remaining -= 1
        return result

    def apply(self, entry):
        before = self.head()
        spec = f"{entry['base']}..{pin_ref(entry['sha'])}"
        identity = committer(self.path)
        result = self.git(*identity, "-c", "rerere.enabled=false", "cherry-pick", spec, check=False)
        if result.returncode != 0:
            result = self.skip_emptied(result, spec, identity)
        if result.returncode != 0:
            picked = self.picked_empty()
            self.git("cherry-pick", "--abort", check=False)
            if stopped_for_conflict(result):
                return self.give_up(before, "conflict with trunk")
            if picked and picked[1]:
                return self.give_up(before, f"commit {picked[0][:12]} is empty; drop it from the branch, then review and submit again")
            self.give_up(before, "")
            raise Infrastructure("cherry-pick failed: " + tail(result.stderr + result.stdout))
        if not changed_paths(self.path, before, self.head()):
            self.git("reset", "--hard", before)
            return ALREADY_IN_TRUNK
        if fingerprint(self.path, before, self.head()) != entry["fingerprint"]:
            return self.give_up(before, "the rebased change differs from the reviewed one; review it again")
        return None

    def check(self):
        contract = self.store.contract
        expected = self.head()
        commands = ([contract["setup"]] if contract.get("setup") else []) + list(contract.get("checks") or [])
        with slot("landing", command=" && ".join(commands)):
            for command in commands:
                code, output = run_build(command, self.path, contract.get("timeout") or 1800)
                if code != 0:
                    reason = "timed out" if code is None else f"exited {code}"
                    return f"`{command}` {reason}: {tail(output)}"
        if self.head() != expected or self.git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            raise LandError("a check changed tracked files in the integration worktree; fix the check, then run land again")
        return None


def settle_landed(store, db, ident, landed, note=""):
    lease = store.entry(ident)["lease"]
    store.set_entry(db, ident, "landed", landed=landed, note=note)
    release_lease(store, db, lease, f"E{ident} landed")


def settle_bounced(store, db, ident, reason):
    lease = store.entry(ident)["lease"]
    store.set_entry(db, ident, "bounced", note=reason, candidate="")
    db.execute("UPDATE lease SET state = 'active', expires = ? WHERE id = ?", (stamp(now() + timedelta(hours=6)), lease))
    store.log(db, "lease", lease, "active", f"E{ident} bounced; the lease is back for the fix")


def pause(store, reason):
    with store.tx() as db:
        store.put(db, "paused", reason)
        store.log(db, "queue", 0, "paused", reason)


def rewound(store, base):
    tip = store.contract.get("tip") or ""
    if not tip:
        return False
    code = git("merge-base", "--is-ancestor", tip, base, cwd=store.repo, check=False).returncode
    if code == 0:
        return False
    if code == 1:
        pause(store, f"trunk no longer contains the last landed commit {tip[:12]} (now {base[:12]}); "
                     "check what happened to trunk, then run land.py resume")
    else:
        pause(store, f"could not check that trunk contains the last landed commit {tip[:12]} "
                     f"(git merge-base --is-ancestor exited {code}); check that git can read it here, then run land.py resume")
    return True


def reconcile(store):
    trunk = fetch_trunk(store)
    for row in store.db.execute("SELECT * FROM attempt WHERE state = 'publishing'").fetchall():
        published = git("merge-base", "--is-ancestor", row["candidate"], trunk, cwd=store.repo, check=False).returncode == 0
        with store.tx() as db:
            for ident in json.loads(row["entries"]):
                if published:
                    settle_landed(store, db, ident, row["candidate"], "recovered after an interrupted run")
                else:
                    store.set_entry(db, ident, "queued", candidate="", note="requeued after an interrupted run")
            db.execute("UPDATE attempt SET state = ? WHERE id = ?", ("published" if published else "abandoned", row["id"]))
    with store.tx() as db:
        for entry in db.execute("SELECT id FROM entry WHERE state = 'landing'").fetchall():
            store.set_entry(db, entry["id"], "queued", candidate="", note="requeued after an interrupted run")


def remote_trunk(store):
    contract = store.contract
    line = git("ls-remote", contract["remote"], f"refs/heads/{contract['trunk']}", cwd=store.repo).stdout.split()
    return line[0] if line else ""


def publish(store, base, candidate):
    contract, repo = store.contract, store.repo
    if contract["mode"] == "local":
        result = git("update-ref", trunk_ref(contract), candidate, base, cwd=repo, check=False)
        return None if result.returncode == 0 else "trunk moved during landing"
    result = git_push(f"--force-with-lease=refs/heads/{contract['trunk']}:{base}", contract["remote"],
                      f"{candidate}:refs/heads/{contract['trunk']}", cwd=repo)
    if result.returncode != 0:
        if remote_trunk(store) != base:
            return "trunk moved during landing"
        raise Infrastructure(f"push rejected: {git_reason(result.stderr)}. Let the remote accept this push, "
                             "or switch to human mode with land.py init --mode human once the queue is empty")
    fetch_trunk(store)
    return None


def attempt(store, integration, entries):
    base = fetch_trunk(store)
    if rewound(store, base):
        return [], [], []
    integration.reset(base)
    applied, bounced, landed, deferred = [], [], [], []
    for entry in entries:
        reason = integration.apply(entry)
        with store.tx() as db:
            if reason == ALREADY_IN_TRUNK and applied:
                store.set_entry(db, entry["id"], "queued", candidate="", note="its change is in the batch ahead of it")
                deferred.append(entry["id"])
            elif reason == ALREADY_IN_TRUNK:
                settle_landed(store, db, entry["id"], base, "already in trunk")
                landed.append(entry["id"])
            elif reason:
                settle_bounced(store, db, entry["id"], reason)
                bounced.append(entry["id"])
            else:
                store.set_entry(db, entry["id"], "landing", candidate=integration.head())
                applied.append(entry)
    if not applied:
        return landed, bounced, deferred
    failure = integration.check()
    if failure:
        with store.tx() as db:
            if len(applied) > 1:
                for entry in applied:
                    store.set_entry(db, entry["id"], "queued", candidate="", note="batch failed checks; landing one at a time")
                return landed, bounced, [entry["id"] for entry in applied] + deferred
            settle_bounced(store, db, applied[0]["id"], f"checks failed: {failure}")
            return landed, bounced + [applied[0]["id"]], deferred
    candidate = integration.head()
    with store.tx() as db:
        cursor = db.execute("INSERT INTO attempt (at, base, candidate, entries, state) VALUES (?, ?, ?, ?, 'publishing')",
                            (stamp(), base, candidate, json.dumps([entry["id"] for entry in applied])))
    problem = publish(store, base, candidate)
    with store.tx() as db:
        db.execute("UPDATE attempt SET state = ? WHERE id = ?", ("abandoned" if problem else "published", cursor.lastrowid))
        for entry in applied:
            if problem:
                store.set_entry(db, entry["id"], "queued", candidate="", note=problem)
            else:
                settle_landed(store, db, entry["id"], candidate)
        if not problem:
            store.put(db, "tip", candidate)
    if problem:
        return landed, bounced, [entry["id"] for entry in applied] + deferred
    return landed + [entry["id"] for entry in applied], bounced, deferred


def queue_branch(entry):
    return f"landing/e{entry['id']}"


def warn(text):
    print(f"warning: {text}")


def delete_queue_branch(store, entry):
    pushed = git_push(store.contract["remote"], "--delete", queue_branch(entry), cwd=store.repo)
    if pushed.returncode != 0 and "remote ref does not exist" not in pushed.stderr:
        warn(f"could not delete {queue_branch(entry)}: {git_reason(pushed.stderr)}")


def clean_bounced(store, entry, reason):
    if entry["pr"]:
        closed = gh("pr", "close", entry["pr"], "--comment", " ".join(reason.split()), cwd=store.repo)
        if closed.returncode != 0 and "already closed" not in closed.stderr and "merged" not in closed.stderr.lower():
            warn(f"could not close {entry['pr']}: {closed.stderr.strip() or 'gh pr close failed'}")
    if store.contract["mode"] == "human":
        delete_queue_branch(store, entry)


def pr_body(store, entry):
    return entry["body"] or git("log", "-1", "--format=%b", entry["sha"], "--", cwd=store.repo).stdout.rstrip()


def ensure_pr(store, entry):
    branch = queue_branch(entry)
    found = gh("pr", "view", branch, "--json", "url,state,headRefOid",
               "-q", f'select(.state == "OPEN" or .headRefOid == "{entry["candidate"]}") | .url', cwd=store.repo)
    url = found.stdout.strip() if found.returncode == 0 else ""
    outcome = "adopted" if url else "opened"
    if not url:
        title = entry["title"] or git("log", "-1", "--format=%s", entry["sha"], "--", cwd=store.repo).stdout.strip()
        created = gh("pr", "create", "--base", store.contract["trunk"], "--head", branch, "--title", title,
                     "--body", pr_body(store, entry), cwd=store.repo)
        if created.returncode != 0:
            raise Infrastructure("gh pr create failed: " + created.stderr.strip())
        url = created.stdout.strip().splitlines()[-1]
    with store.tx() as db:
        store.set_entry(db, entry["id"], "awaiting-merge", pr=url, note="")
    return outcome


def build(store, integration, entry, out):
    trunk = fetch_trunk(store)
    integration.reset(trunk)
    reason = integration.apply(entry)
    if not reason:
        failure = integration.check()
        reason = f"checks failed: {failure}" if failure else None
    if reason:
        with store.tx() as db:
            if reason == ALREADY_IN_TRUNK:
                settle_landed(store, db, entry["id"], trunk, "already in trunk")
            else:
                settle_bounced(store, db, entry["id"], reason)
        (out["landed"] if reason == ALREADY_IN_TRUNK else out["bounced"]).append(entry["id"])
        return
    head = integration.head()
    pushed = git_push("--force", store.contract["remote"], f"{head}:refs/heads/{queue_branch(entry)}", cwd=store.repo)
    if pushed.returncode != 0:
        raise Infrastructure("push failed: " + git_reason(pushed.stderr))
    with store.tx() as db:
        store.set_entry(db, entry["id"], "awaiting-merge", candidate=head, pr="", note="")
    out[ensure_pr(store, store.entry(entry["id"]))].append(entry["id"])


def read_pr_state(store, url):
    view = gh("pr", "view", url, "--json", "state,headRefOid,mergeCommit",
              "-q", '.state + " " + .headRefOid + " " + (.mergeCommit.oid // "")', cwd=store.repo)
    fields = (view.stdout.strip().split(" ") + ["", "", ""])[:3]
    if view.returncode != 0 or fields[0] not in PR_STATES:
        raise Infrastructure(f"could not read the state of {url}. gh said {view.stderr.strip() or 'nothing'}")
    return fields


def poll(store, entry, out):
    if not entry["pr"]:
        out[ensure_pr(store, entry)].append(entry["id"])
        entry = store.entry(entry["id"])
    try:
        state, head, merged = read_pr_state(store, entry["pr"])
    except Infrastructure as problem:
        warn(str(problem))
        return
    if state == "MERGED":
        delete_queue_branch(store, entry)
        with store.tx() as db:
            if head == entry["candidate"]:
                settle_landed(store, db, entry["id"], merged)
                out["landed"].append(entry["id"])
            else:
                settle_bounced(store, db, entry["id"], f"merged at {merged[:12]} with head {head[:12]}, not the checked "
                                                       f"{entry['candidate'][:12]}; review what reached trunk")
                out["bounced"].append(entry["id"])
            if merged:
                store.put(db, "tip", merged)
    elif state == "CLOSED":
        reason = "PR closed without merging"
        clean_bounced(store, entry, reason)
        with store.tx() as db:
            settle_bounced(store, db, entry["id"], reason)
        out["bounced"].append(entry["id"])
    elif head and head != entry["candidate"]:
        with store.tx() as db:
            store.set_entry(db, entry["id"], "awaiting-merge", note=f"PR head changed to {head[:12]} outside the queue")
