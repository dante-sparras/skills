from .prompts import PROTOCOL, TASK_SYSTEM, arm_prompt, nonempty, parse_checks, task_judge_prompt
from .scoring import judged
from .textutil import digest, read_json

DEFAULT_TASKS = (".skills", "evals")


def task_dir(args, root):
    return args.tasks or root.joinpath(*DEFAULT_TASKS)


def load_tasks(directory, skill):
    path = directory / f"{skill}.json"
    if not path.is_file():
        return None, f"no task file at {path}"
    tasks = read_json(path)
    valid = isinstance(tasks, list) and tasks and all(
        isinstance(task, dict) and str(task.get("id") or "").strip() and str(task.get("prompt") or "").strip()
        and isinstance(task.get("checks"), list) and task["checks"] for task in tasks)
    if not valid:
        raise ValueError(f"{path} must be a list of objects with id, prompt, and a nonempty checks list")
    return tasks, None


def run_task(context, skill, task, seat, bundle, base=""):
    caller, cache, identities = context.caller, context.cache, context.identities
    prompt = arm_prompt(task["prompt"], bundle, base)
    key = digest("task", PROTOCOL, identities.of(seat), TASK_SYSTEM, task, bundle, *([prompt] if base else []))
    answer, _ = cache.get("tasks", key, lambda: caller.call(seat, TASK_SYSTEM, prompt, nonempty, "task", skill))
    checks, _ = judged(context, seat, "checks", task_judge_prompt(task, answer), parse_checks(len(task["checks"])),
                       "task-judge", skill)
    return checks


def compare(context, skill, tasks, versions, base=""):
    answerers = context.panel.answerers
    jobs = [(task, seat, version) for task in tasks for seat in answerers for version in versions]
    results = dict(zip(
        [(task["id"], seat.key, version) for task, seat, version in jobs],
        context.claims.map(lambda job: run_task(context, skill, job[0], job[1], versions[job[2]], base), jobs),
    ))
    regressions = [
        {"task": task["id"], "seat": seat.key, "check": index, "reason": new["reason"]}
        for task in tasks for seat in answerers
        for index, (old, new) in enumerate(zip(results[(task["id"], seat.key, "original")],
                                               results[(task["id"], seat.key, "candidate")]), start=1)
        if old["result"] == "pass" and new["result"] == "fail"
    ]
    return {"status": "regressed" if regressions else "passed", "tasks": len(tasks), "regressions": regressions}
