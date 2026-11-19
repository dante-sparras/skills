import argparse
import json
import re
import sys
from pathlib import Path

from novelty.panelcmd import panel_command
from novelty.pipeline import run_skills


def add_panel_options(parser):
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root that holds skills/.")
    parser.add_argument("--panel", type=Path, help="Panel file layered over the user and project files.")
    parser.add_argument("--model", help="One cli:model:effort seat for every role.")
    parser.add_argument("--answerer", action="append", default=[], help="Answerer seat. Repeat for more. Replaces the answerers.")
    parser.add_argument("--judge", action="append", default=[], help="FAMILY=SEAT, the judge for that model family's answers.")
    parser.add_argument("--drafter", help="Seat that splits skills into claims.")
    parser.add_argument("--implementer", help="Seat that rewrites paragraphs.")
    parser.add_argument("--parallel", type=int, help="Concurrent calls per CLI, overriding every limit.")
    parser.add_argument("--timeout", type=int, default=300, help="Seconds before a call is killed and retried.")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Run the novelty method on skills through subscription CLIs.")
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run", help="Evaluate skills.")
    add_panel_options(runner)
    runner.add_argument("--skill", action="append", default=[], help="Skill directory name. Repeat for more skills.")
    runner.add_argument("--all", action="store_true", help="Evaluate every skill under skills/.")
    runner.add_argument("--state", type=Path, default=Path.home() / ".cache" / "eval-skill")
    runner.add_argument("--hedge", type=float, default=45,
                        help="Seconds before a slow call gets a duplicate. Later calls use twice the median.")
    runner.add_argument("--max-claims", type=int, default=30)
    runner.add_argument("--samples", type=int, default=3,
                        help="Most samples per arm. The majority decides, and sampling stops once it is reached.")
    runner.add_argument("--score-only", action="store_true")
    runner.add_argument("--tasks", type=Path, help="Directory with <skill>.json task evals.")
    panel = commands.add_parser("panel", help="Show, list, check, or save the panel.")
    add_panel_options(panel)
    panel.add_argument("--list", action="store_true", help="List the models and efforts each CLI offers.")
    panel.add_argument("--check", action="store_true", help="Make one tiny call per seat and confirm it sees no skills.")
    panel.add_argument("--save", action="store_true", help="Save the resolved panel to the user file.")
    panel.add_argument("--project", action="store_true", help="With --save, write the project file instead.")
    args = parser.parse_args(argv)
    if (args.parallel is not None and args.parallel < 1) or args.timeout < 1:
        parser.error("--parallel and --timeout must be positive")
    if args.command == "run":
        if not args.all and not args.skill:
            parser.error("Pass --skill or --all")
        if args.max_claims < 1 or args.hedge <= 0 or args.samples < 1 or args.samples % 2 == 0:
            parser.error("--hedge and --max-claims must be positive, and --samples must be an odd positive number")
    return args


def resolve_skills(args):
    skills_dir = args.root.resolve() / "skills"
    if args.all:
        return sorted(path.parent.name for path in skills_dir.glob("*/SKILL.md"))
    for name in args.skill:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or not (skills_dir / name / "SKILL.md").is_file():
            raise SystemExit(f"No skill named {name!r} under {skills_dir}")
    return args.skill


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    if args.command == "panel":
        return panel_command(args)
    result, report, passed = run_skills(args, resolve_skills(args))
    print(json.dumps({
        "run": result["run"], "wall_seconds": result["wall_seconds"], "failures": result["failures"],
        "report": str(report),
        "skills": {summary["skill"]: {
            "buckets": summary["buckets"], "unscored": summary["unscored"],
            "isolation": summary["isolation"]["passed"], "proposal": summary.get("proposal", {}).get("status"),
        } for summary in result["skills"]},
    }, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
