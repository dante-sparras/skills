from .prompts import JUDGE_SYSTEM, PROTOCOL, TASK_SYSTEM, arm_prompt, nonempty, parse_checks, task_judge_prompt
from .textutil import digest, read_json


def load_tasks(directory, skill):
    path = directory / f"{skill}.json" if directory else None
    if not path or not path.is_file():
        return None, f"no task file at {path}" if path else "no --tasks directory"
    return read_json(path), None


def run_task(caller, cache, panel, skill, task, seat, bundle):
    key = digest("task", PROTOCOL, seat.key, TASK_SYSTEM, task, bundle)
    answer, _ = cache.get("tasks", key, lambda: caller.call(
        seat, TASK_SYSTEM, arm_prompt(task["prompt"], bundle), nonempty, "task", skill))
    judge = panel.judges_for(seat)[0]
    prompt = task_judge_prompt(task, answer)
    checks, _ = cache.get("grades", digest("checks", PROTOCOL, judge.key, JUDGE_SYSTEM, prompt), lambda: caller.call(
        judge, JUDGE_SYSTEM, prompt, parse_checks(len(task["checks"])), "task-judge", skill))
    return checks


def compare(caller, cache, panel, skill, tasks, versions, pool):
    jobs = [(task, seat, version) for task in tasks for seat in panel.answerers for version in versions]
    results = dict(zip(
        [(task["id"], seat.key, version) for task, seat, version in jobs],
        pool.map(lambda job: run_task(caller, cache, panel, skill, job[0], job[1], versions[job[2]]), jobs),
    ))
    regressions = [
        {"task": task["id"], "seat": seat.key, "check": index, "reason": new["reason"]}
        for task in tasks for seat in panel.answerers
        for index, (old, new) in enumerate(zip(results[(task["id"], seat.key, "original")],
                                               results[(task["id"], seat.key, "candidate")]), start=1)
        if old["result"] == "pass" and new["result"] == "fail"
    ]
    return {"status": "regressed" if regressions else "passed", "tasks": len(tasks), "regressions": regressions}
