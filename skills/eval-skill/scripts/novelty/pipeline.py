import secrets
import shutil
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from . import skillfiles
from .cache import Cache
from .calls import Caller
from .claims import ClaimBook, draft, manifest_path
from .clis import connect
from .isolation import Markers, canary, verdict
from .prompts import PROTOCOL
from .report import call_stats, render_report
from .rewrite import needs_rewrite, repo_checks, rewrite_paragraph, write_patch
from .scoring import bucket_counts, by_answerer, taught_scales, Scorer
from .seats import Panel
from .tasks import compare, load_tasks
from .textutil import digest, save_json, write_jsonl

SUMMARY_ROW = ("id", "kind", "source", "span", "answerer", "judges", "bucket_lenient", "bucket_strict", "decision",
               "without_cached", "with_cached")


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


class Steps:
    def __init__(self, origin):
        self.origin = origin
        self.data = {}
        self.lock = threading.Lock()

    def now(self):
        return round(time.monotonic() - self.origin, 2)

    def start(self, name):
        with self.lock:
            self.data.setdefault(name, {"start": self.now()})

    def end(self, name):
        with self.lock:
            entry = self.data.setdefault(name, {"start": self.now()})
            entry["end"] = self.now()
            entry["seconds"] = round(entry["end"] - entry["start"], 2)

    def timed(self, name, function):
        def wrapper(*args):
            self.start(name)
            try:
                return function(*args)
            finally:
                self.end(name)
        return wrapper


class RunContext:
    def __init__(self, args, adapters=None):
        self.args = args
        self.origin = time.monotonic()
        self.root = args.root.resolve()
        self.panel = Panel.resolve(args)
        self.adapters, self.notes = connect(self.panel, args.timeout, adapters)
        self.caller = Caller(self.adapters, self.panel, args.hedge)
        self.state = args.state.expanduser().resolve() / f"v{PROTOCOL}"
        self.cache = Cache(self.state / "cache")
        self.run_dir = self.state / "runs" / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2)}"
        self.run_dir.mkdir(parents=True)
        width = sum(self.panel.parallel(cli) for cli in self.adapters)
        self.arms = ThreadPoolExecutor(max_workers=max(64, width * 8), thread_name_prefix="arm")
        self.claims = ThreadPoolExecutor(max_workers=max(32, width * 4), thread_name_prefix="claim")

    def close(self):
        self.arms.shutdown(wait=True)
        self.claims.shutdown(wait=True)


class SkillRun:
    def __init__(self, context, name):
        self.context = context
        self.name = name
        self.args = context.args
        self.panel = context.panel
        self.steps = Steps(context.origin)
        self.state = context.state / "skills" / name
        self.output = context.run_dir / name
        self.before = self.output / "before" / "skills" / name
        self.candidate = self.output / "repo" / "skills" / name
        self.scorer = Scorer(context.caller, context.cache, context.panel, name, context.arms, self.state / "routes")

    def bundle(self, directory):
        return f"Isolation marker: {self.markers.current}\n\n{skillfiles.bundle(directory)}"

    def run(self):
        shutil.copytree(self.context.root / "skills" / self.name, self.candidate)
        shutil.copytree(self.candidate, self.before)
        self.markers = Markers(self.state / "markers.json")
        bundle = self.bundle(self.before)
        probe = self.steps.timed("isolation canary", canary)
        canaries = [self.context.arms.submit(probe, self.context.caller, seat, arm, bundle, self.markers.current, self.name)
                    for seat in self.panel.answerers for arm in ("without", "with")]
        book = ClaimBook(manifest_path(self.state, self.panel.drafter), skillfiles.paragraphs(self.before),
                         self.args.max_claims)
        futures = self.score_claims(book, bundle)
        rows, rewrites = self.collect(book, futures)
        isolation = verdict(self.name, self.markers, rows, [future.result() for future in canaries])
        summary = self.summarize(book, rows, isolation)
        if self.args.score_only:
            pass
        elif summary["unscored"] or not isolation["passed"]:
            summary["proposal"] = {"status": "none", "reason": "the run has unscored claims or failed isolation"}
        else:
            self.propose(rows, rewrites, summary)
        summary["steps"] = self.steps.data
        save_json(self.output / "summary.json", summary)
        return summary

    def score_claims(self, book, bundle):
        score = self.steps.timed("score", self.scorer.claim)
        futures = {claim["id"]: self.context.claims.submit(score, claim, bundle) for claim in book.claims}
        self.steps.start("draft")
        drafts = [self.context.arms.submit(draft, self.context.caller, self.panel.drafter, self.name, text,
                                           book.limit(source), book.paragraphs, bool(book.claims))
                  for source, text in book.changed.items()]
        for future in as_completed(drafts):
            claims, dropped = future.result()
            book.dropped += dropped
            for claim in book.admit(claims):
                futures[claim["id"]] = self.context.claims.submit(score, claim, bundle)
        self.steps.end("draft")
        if not book.claims:
            raise SystemExit(f"{self.name}: no claims were drafted")
        book.save()
        log(f"{self.name}: {len(book.claims)} claims, {book.reused} reused, {book.dropped} invalid drafts dropped")
        return futures

    def collect(self, book, futures):
        waiting = defaultdict(set)
        for claim in book.claims:
            for block in claim["_blocks"]:
                waiting[block].add(claim["id"])
        members = {block: sorted(ids, key=int) for block, ids in waiting.items()}
        rows, rewrites = {}, {}
        rewrite = self.steps.timed("rewrite", rewrite_paragraph)
        for future in as_completed(list(futures.values())):
            row = future.result()
            rows[row["id"]] = row
            if self.args.score_only:
                continue
            for block in [block for block, ids in waiting.items() if row["id"] in ids]:
                waiting[block].discard(row["id"])
                matched = [rows[identifier] for identifier in members[block]] if not waiting[block] else []
                if matched and needs_rewrite(matched):
                    rewrites[block] = self.context.arms.submit(
                        rewrite, self.context.caller, self.context.cache, self.panel.implementer, self.name,
                        book.paragraphs[block][1], matched)
        log(f"{self.name}: scored {len(rows)} claims")
        return [rows[claim["id"]] for claim in sorted(book.claims, key=lambda claim: int(claim["id"]))], rewrites

    def summarize(self, book, rows, isolation):
        scored = [row for row in rows if row["decision"] != "unscored"]
        write_jsonl(self.output / "claims.jsonl", rows)
        return {
            "skill": self.name,
            "claims": len(book.claims),
            "reused_claims": book.reused,
            "dropped_claims": book.dropped,
            "scored": len(scored),
            "unscored": [row["id"] for row in rows if row["decision"] == "unscored"],
            "moved_answerer": [row["id"] for row in scored if row["moved_answerer"]],
            "buckets": bucket_counts(scored),
            "buckets_by_answerer": by_answerer(scored),
            "decisions": dict(Counter(row["decision"] for row in rows)),
            "isolation": isolation,
            "rows": [{key: row.get(key) for key in SUMMARY_ROW} for row in rows],
        }

    def propose(self, rows, rewrites, summary):
        self.steps.start("rewrite")
        skillfiles.apply_paragraph_edits(self.candidate, {block: future.result() for block, future in rewrites.items()})
        self.steps.end("rewrite")
        before, after = skillfiles.size(self.before), skillfiles.size(self.candidate)
        summary.update(before_chars=before, proposed_chars=after)
        if after >= before:
            summary["proposal"] = {"status": "none", "reason": "the rewrite did not make the skill shorter"}
            return
        failures = self.steps.timed("checks", repo_checks)(self.context.root, self.candidate)
        if failures:
            summary["proposal"] = {"status": "rejected", "reason": "repo checks failed", "failures": failures}
            return
        bundle, version = self.bundle(self.candidate), digest(skillfiles.bundle(self.candidate))
        self.steps.start("validate")
        kept = list(self.context.claims.map(lambda row: self.scorer.recheck(row, bundle, version),
                                            [row for row in rows if taught_scales(row)]))
        self.steps.end("validate")
        write_jsonl(self.output / "kept.jsonl", kept)
        lost = [item["id"] for item in kept if item["status"] == "lost"]
        summary.update(checked_taught=len(kept), lost_taught=lost)
        if lost:
            summary["proposal"] = {"status": "rejected", "reason": "the shorter skill lost taught claims", "lost": lost}
            return
        tasks = self.task_evals()
        patch = write_patch(self.output, self.name)
        summary["proposal"] = {"status": "rejected" if tasks["status"] == "regressed" else "proposed",
                               "patch": str(patch), "task_evals": tasks}

    def task_evals(self):
        tasks, reason = load_tasks(self.args.tasks, self.name)
        if tasks is None:
            return {"status": "not run", "reason": reason}
        versions = {"original": skillfiles.bundle(self.before), "candidate": skillfiles.bundle(self.candidate)}
        self.steps.start("tasks")
        try:
            return compare(self.context.caller, self.context.cache, self.panel, self.name, tasks, versions,
                           self.context.claims)
        finally:
            self.steps.end("tasks")


def run_skills(args, skills, adapters=None):
    context = RunContext(args, adapters)
    log(f"Run directory: {context.run_dir}")
    results, failures = [], []
    try:
        with ThreadPoolExecutor(max_workers=len(skills)) as pool:
            futures = {pool.submit(SkillRun(context, name).run): name for name in skills}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as error:
                    failures.append(f"{futures[future]}: {error}")
                    log(f"{futures[future]} failed: {error}")
    finally:
        context.close()
    result = {
        "run": context.run_dir.name,
        "wall_seconds": round(time.monotonic() - context.origin, 1),
        "panel": context.panel.describe(),
        "panel_note": context.panel.note,
        "billing": context.notes + ["API key variables are removed from every child environment"],
        "skills": sorted(results, key=lambda summary: summary["skill"]),
        "failures": failures,
        "calls": call_stats(context.caller.records),
        "cache_hits": dict(context.cache.hits),
    }
    origin = context.origin
    write_jsonl(context.run_dir / "calls.jsonl", [
        dict(record, **{key: round(record[key] - origin, 2) for key in ("queued_at", "started_at", "ended_at")})
        for record in context.caller.records])
    save_json(context.run_dir / "summary.json", result)
    report = context.run_dir / "report.md"
    report.write_text(render_report(result), encoding="utf-8")
    log(f"Report: {report}")
    passed = not failures and all(not summary["unscored"] and summary["isolation"]["passed"] for summary in results)
    return result, report, passed
