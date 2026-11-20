import json
import re
from dataclasses import dataclass
from pathlib import Path

CLIS = ("claude", "codex", "grok", "opencode")
FIXED_FAMILIES = {"claude": "claude", "codex": "gpt", "grok": "grok"}
FAMILY_HINTS = (
    ("claude", ("anthropic/", "claude", "opus", "sonnet", "haiku")),
    ("gpt", ("openai/", "gpt", "codex")),
    ("grok", ("xai/", "grok")),
    ("gemini", ("google/", "gemini")),
)
USER_PANEL = Path.home() / ".config" / "skills" / "eval-skill.json"
PROJECT_PANEL = Path(".skills") / "eval-skill.json"
PANEL_KEYS = {"answerers", "judges", "drafter", "implementer", "limits"}
DEFAULT_PARALLEL = 8
DEFAULT_PANEL = {
    "answerers": ["claude:sonnet:low", "codex:gpt-6.2-sol:low", "grok:grok-4.7-build-fast:low"],
    "judges": {
        "claude": "codex:gpt-6.2-sol:low",
        "gpt": "claude:sonnet:low",
        "grok": "codex:gpt-6.2-sol:low",
    },
    "drafter": "claude:sonnet:low",
    "implementer": "claude:sonnet:low",
}
ROLES = ("drafter", "implementer")
FAMILY_NAME = re.compile(r"[a-z0-9]+")


def model_family(cli, model):
    if cli in FIXED_FAMILIES:
        return FIXED_FAMILIES[cli]
    text = model.lower()
    for family, hints in FAMILY_HINTS:
        if any(hint in text for hint in hints):
            return family
    name = text.rpartition("/")[2]
    return re.split(r"[^a-z]", name)[0] or name


@dataclass(frozen=True)
class Seat:
    cli: str
    model: str
    effort: str

    @classmethod
    def parse(cls, text):
        pieces = str(text).split(":")
        if len(pieces) != 3 or pieces[0] not in CLIS or not pieces[1] or not pieces[2]:
            raise SystemExit(f"Seat {text!r} must look like claude:sonnet:low, with cli one of {', '.join(CLIS)}")
        return cls(*pieces)

    @property
    def key(self):
        return f"{self.cli}:{self.model}:{self.effort}"

    @property
    def family(self):
        return model_family(self.cli, self.model)

    def __str__(self):
        return self.key


def load_panel_file(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}")
    if not isinstance(data, dict) or set(data) - PANEL_KEYS:
        raise SystemExit(f"{path} may only hold {', '.join(sorted(PANEL_KEYS))}")
    for text in seat_texts(data):
        Seat.parse(text)
    if set(data.get("limits", {})) - set(CLIS):
        raise SystemExit(f"{path}: limits are keyed by {', '.join(CLIS)}")
    if not all(FAMILY_NAME.fullmatch(family) for family in data.get("judges", {})):
        raise SystemExit(f"{path}: judges are keyed by model family, such as claude, gpt, or grok")
    return data


def seat_texts(layer):
    return [text for text in [*layer.get("answerers", []), *layer.get("judges", {}).values(),
                              *(layer.get(role) for role in ROLES)] if text]


def flag_layer(args):
    layer = {}
    if args.answerer:
        layer["answerers"] = list(args.answerer)
    if args.judge:
        layer["judges"] = {}
        for text in args.judge:
            family, _, seat = text.partition("=")
            if not FAMILY_NAME.fullmatch(family) or not seat:
                raise SystemExit(f"--judge {text!r} must look like claude=codex:gpt-6.2-sol:low")
            layer["judges"][family] = seat
    for role in ROLES:
        if getattr(args, role):
            layer[role] = getattr(args, role)
    if args.model:
        family = Seat.parse(args.model).family
        layer.update(answerers=[args.model], judges={family: args.model},
                     **{role: args.model for role in ROLES})
    if args.parallel:
        layer["limits"] = {cli: {"parallel": args.parallel} for cli in CLIS}
    for text in seat_texts(layer):
        Seat.parse(text)
    return layer


class Panel:
    def __init__(self, layers, root):
        self.root = root
        merged, self.sources = {}, {}
        for label, layer in layers:
            for key in ("answerers", *ROLES):
                if key in layer:
                    merged[key] = layer[key]
                    self.sources[key] = label
            for family, seat in layer.get("judges", {}).items():
                merged.setdefault("judges", {})[family] = seat
                self.sources[f"judges.{family}"] = label
            for cli, limit in layer.get("limits", {}).items():
                merged.setdefault("limits", {}).setdefault(cli, {}).update(limit)
                self.sources[f"limits.{cli}"] = label
        self.answerers = [Seat.parse(text) for text in merged.get("answerers", [])]
        if not self.answerers or len(set(self.answerers)) != len(self.answerers):
            raise SystemExit("Give one or more answerers, each seat once")
        self.drafter = Seat.parse(merged.get("drafter") or merged["answerers"][0])
        self.implementer = Seat.parse(merged.get("implementer") or self.drafter.key)
        families = list(dict.fromkeys([*(seat.family for seat in self.answerers), self.drafter.family]))
        judges = merged.get("judges", {})
        missing = [family for family in families if family not in judges]
        if missing:
            raise SystemExit(f"Give a judge for {', '.join(missing)} with --judge <family>=<seat>. "
                             "The judge for the drafter's family also reviews its claims.")
        self.judges = {family: Seat.parse(judges[family]) for family in families}
        self.limits = {cli: {"parallel": DEFAULT_PARALLEL, **merged.get("limits", {}).get(cli, {})} for cli in CLIS}
        for cli, limit in self.limits.items():
            if set(limit) != {"parallel"} or not isinstance(limit["parallel"], int) or limit["parallel"] < 1:
                raise SystemExit(f"limits.{cli} takes only parallel, a positive integer")
        self.single = len(set(self.seats())) == 1
        for family, judge in self.judges.items():
            if judge.family == family and not self.single:
                raise SystemExit(
                    f"The judge for {family} answers is also {family}. Pick another family, "
                    "or pick one model for every role with --model"
                )

    @classmethod
    def resolve(cls, args):
        root = args.root.resolve()
        layers = [("built-in default", DEFAULT_PANEL)]
        for path in (USER_PANEL, root / PROJECT_PANEL):
            if path.is_file():
                layers.append((str(path), load_panel_file(path)))
        if args.panel:
            if not args.panel.is_file():
                raise SystemExit(f"Panel file {args.panel} does not exist")
            layers.append((str(args.panel), load_panel_file(args.panel)))
        flags = flag_layer(args)
        if flags:
            layers.append(("command line", flags))
        return cls(layers, root)

    def seats(self):
        return [*self.answerers, *self.judges.values(), self.drafter, self.implementer]

    @property
    def clis(self):
        return sorted({seat.cli for seat in self.seats()})

    @property
    def note(self):
        if not self.single:
            return None
        return (f"Single-model panel: every role used {self.drafter} because one model was picked for every role. "
                "Each answer was judged by the model that gave it.")

    def parallel(self, cli):
        return self.limits[cli]["parallel"]

    def judges_for(self, answerer):
        if self.single:
            return [answerer]
        ordered = [self.judges[answerer.family]]
        for seat in [*self.judges.values(), *self.answerers, self.drafter, self.implementer]:
            if seat.family != answerer.family and seat not in ordered:
                ordered.append(seat)
        return ordered

    def as_file(self):
        return {
            "answerers": [seat.key for seat in self.answerers],
            "judges": {family: seat.key for family, seat in self.judges.items()},
            "drafter": self.drafter.key,
            "implementer": self.implementer.key,
            "limits": {cli: dict(limit) for cli, limit in self.limits.items()},
        }

    def describe(self):
        return {**self.as_file(), "limits": {cli: self.parallel(cli) for cli in self.clis},
                "sources": self.sources, "single_model_panel": self.single}

    def table(self):
        rows = [("answerer", seat.key, self.sources.get("answerers")) for seat in self.answerers]
        rows += [(f"judge of {family} answers", seat.key, self.sources.get(f"judges.{family}"))
                 for family, seat in self.judges.items()]
        rows += [(role, getattr(self, role).key, self.sources.get(role, "first answerer")) for role in ROLES]
        rows += [(f"{cli} parallel calls", str(self.parallel(cli)), self.sources.get(f"limits.{cli}", "built-in default"))
                 for cli in self.clis]
        return rows
