"""Check a student's solution step by step and diagnose the first mistake."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .bugs import RULES, BugRule
from .equivalence import Match, compare, equivalent, solutions, unknown
from .parsing import Line, ParseError, parse_line

_STRENGTH = {Match.EXACT: 3, Match.PROPORTIONAL: 2, Match.SAME_SOLUTIONS: 1}


class Status(str, Enum):
    GIVEN = "given"            # the problem statement
    OK = "ok"                  # equivalent to the previous line
    ERROR = "error"            # first line that breaks equivalence
    CONSISTENT = "consistent"  # correct move, but built on an earlier error
    UNREADABLE = "unreadable"  # could not be parsed


@dataclass
class Diagnosis:
    rule: BugRule
    confidence: str  # "kesin" (exact reconstruction) or "olası"


@dataclass
class StepResult:
    index: int
    raw: str
    status: Status
    line: Line | None = None
    note: str = ""
    diagnoses: list[Diagnosis] = field(default_factory=list)


@dataclass
class Report:
    steps: list[StepResult]
    first_error: int | None
    final_correct: bool | None

    @property
    def diagnosis(self) -> Diagnosis | None:
        if self.first_error is None:
            return None
        d = self.steps[self.first_error].diagnoses
        return d[0] if d else None


def diagnose_step(prev: Line, cur: Line) -> list[Diagnosis]:
    """Find bug rules that turn ``prev`` into what the student wrote in ``cur``."""
    best: dict[str, tuple[int, BugRule]] = {}
    seen: set[str] = set()
    for rule in RULES:
        for candidate in rule.apply(prev):
            key = candidate.pretty()
            if (rule.id, key) in seen:
                continue
            seen.add((rule.id, key))
            try:
                if equivalent(prev, candidate):
                    continue  # the "bug" did not actually change anything here
                strength = _STRENGTH.get(compare(candidate, cur), 0)
            except Exception:  # noqa: BLE001 - a malformed candidate is just skipped
                continue
            if strength and strength > best.get(rule.id, (0, rule))[0]:
                best[rule.id] = (strength, rule)
    ranked = sorted(best.values(), key=lambda t: -t[0])
    if not ranked:
        return []
    top = ranked[0][0]
    return [Diagnosis(rule, "kesin" if s == 3 else "olası") for s, rule in ranked if s == top]


def check_solution(lines: list[str]) -> Report:
    steps: list[StepResult] = []
    prev: Line | None = None
    first_error: int | None = None
    given: Line | None = None

    for i, raw in enumerate(lines):
        try:
            line = parse_line(raw)
        except ParseError as exc:
            steps.append(StepResult(i, raw, Status.UNREADABLE, note=str(exc)))
            continue
        if prev is None:
            steps.append(StepResult(i, raw, Status.GIVEN, line))
            prev = given = line
            continue
        if equivalent(prev, line):
            status = Status.OK if first_error is None else Status.CONSISTENT
            steps.append(StepResult(i, raw, status, line))
        else:
            result = StepResult(i, raw, Status.ERROR, line, diagnoses=diagnose_step(prev, line))
            if not result.diagnoses:
                result.note = "Bilinen bir hata kalıbıyla eşleşmedi (muhtemelen işlem hatası)."
            if first_error is None:
                first_error = i
            steps.append(result)
        prev = line

    final_correct = None
    if given is not None and prev is not None and given is not prev and given.is_equation and prev.is_equation:
        var = unknown(given, prev)
        if var is not None:
            final_correct = solutions(given, var) == solutions(prev, var)
    elif given is not None and prev is not None and given is not prev:
        final_correct = equivalent(given, prev)
    return Report(steps, first_error, final_correct)
