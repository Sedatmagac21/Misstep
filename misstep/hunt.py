"""Hata Avı (mistake hunt): find the wrong step in a made-up classmate's solution.

Research on *erroneous examples* (Adams, McLaren et al., 2014; Große & Renkl,
2007) shows that spotting and explaining someone else's mistake helps
students avoid it later. Misstep can build such examples honestly because the
same bug rules that diagnose real work can also *inject* one mistake into a
correct solution. Every hunt is then re-checked by the diagnosis engine: the
puzzle is only used when ``check_solution`` finds exactly the injected step
as the first error and names the injected misconception.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

import sympy as sp

from .bugs import RULES, RULES_BY_ID
from .diagnose import check_solution
from .equivalence import equivalent
from .generator import LEVELS, TEMPLATES, tidy
from .parsing import Line, parse_line
from .practice import X, _answer, _stages, display
from .progress import TOPIC_OF

NAMES = ["Deniz", "Ece", "Mert", "Zeynep", "Can", "Elif", "Kaan", "Defne"]


@dataclass
class Hunt:
    rule_id: str
    level: str
    instruction: str
    lines: list[str]        # SymPy-readable lines, the first is the problem
    wrong_index: int        # the line where the injected mistake is
    options: list[str]      # rule ids: the injected one plus two others, shuffled
    student: str

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "level": self.level, "instruction": self.instruction, "lines": self.lines,
                "lines_display": [display(l) for l in self.lines], "wrong_index": self.wrong_index,
                "options": self.options, "student": self.student, "topic": TOPIC_OF[self.rule_id]}


def _expr(e: sp.Expr) -> str:
    """Write a sum the way a student would: variable terms first, positives before negatives, constants last."""
    if not isinstance(e, sp.Add):
        return re.sub(r"(?<![\d.])1\*", "", sp.sstr(e))
    flat: list[sp.Expr] = []
    for a in sp.Add.make_args(e):  # a nested positive sum needs no brackets
        flat += list(sp.Add.make_args(a)) if isinstance(a, sp.Add) and len(sp.Add.make_args(a)) > 1 else [a]
    terms = sorted(flat, key=lambda a: (a.is_number, a.could_extract_minus_sign()))
    out = ""
    for k, a in enumerate(terms):
        neg = a.could_extract_minus_sign()
        body = _expr(-a if neg else a)
        if isinstance(-a if neg else a, sp.Add):
            body = f"({body})"
        out += (("-" if neg else "") if k == 0 else (" - " if neg else " + ")) + body
    return out


def _text(line: Line) -> str:
    return f"{_expr(line.lhs)} = {_expr(line.rhs)}" if line.is_equation else _expr(line.lhs)


def _finish(line: Line) -> list[str]:
    """The rest of a (consistent) solution from ``line``: its stages and the final answer."""
    out = [_text(s) for s in _stages(line)]
    ans = _answer(line)
    if ans and " veya " not in ans:
        out.append(ans)
    return out


def _correct_path(problem: Line) -> list[str]:
    path = [_text(s) for s in _stages(problem)]
    ans = _answer(problem)
    if ans and " veya " not in ans:
        path.append(ans)
    return path


def _dedupe(lines: list[str]) -> list[str]:
    out: list[str] = []
    for l in lines:
        if not out or _same(l, out[-1]) is False:
            out.append(l)
    return out


def _same(a: str, b: str) -> bool:
    norm = lambda t: display(t).replace(" ", "").replace("(", "").replace(")", "")  # noqa: E731
    return norm(a) == norm(b) or _text(parse_line(a)) == _text(parse_line(b))


def build(rule_id: str, text: str, instruction: str, rng: random.Random) -> Hunt | None:
    rule = RULES_BY_ID[rule_id]
    problem = parse_line(text)
    sites = [problem]
    if problem.is_equation:  # the tidy "ax + b = c" line gives later misconceptions (moving, dividing) a place to strike
        flat = Line("", sp.expand(problem.lhs), sp.expand(problem.rhs))
        if _text(flat) != _text(problem) and len(sp.Add.make_args(flat.lhs)) > 1:
            sites.append(flat)
    sites += _stages(problem)
    order = list(range(len(sites)))
    rng.shuffle(order)
    for k in order:
        site = sites[k]
        for wrong in rule.apply(site):
            try:
                if equivalent(site, wrong):
                    continue
                rest = _finish(wrong)
            except Exception:  # noqa: BLE001 - a malformed rewrite is skipped
                continue
            before = [text] + [_text(s) for s in sites[1:k + 1]]
            lines = _dedupe(before + [_text(wrong)] + rest)
            if len(lines) < 3 or any(_same(a, b) for i, a in enumerate(lines) for b in lines[i + 1:]):
                continue
            idx = len(before)
            try:
                report = check_solution(lines)
            except Exception:  # noqa: BLE001
                continue
            top = [d.rule.id for d in report.steps[idx].diagnoses] if report.first_error == idx else []
            if rule_id not in top or any(s.status.value == "unreadable" for s in report.steps):
                continue
            others = [r.id for r in RULES if r.id not in top]
            same = [r for r in others if TOPIC_OF[r] == TOPIC_OF[rule_id]]
            pool = same + rng.sample([r for r in others if r not in same], len(others) - len(same))
            options = [rule_id, *pool[:2]]
            rng.shuffle(options)
            return Hunt(rule_id, "", instruction, lines, idx, options, rng.choice(NAMES))
    return None


def make_hunt(rule_ids: list[str] | None = None, level: str = "medium", seed: int | None = None, tries: int = 80) -> Hunt | None:
    rng = random.Random(seed)
    level = level if level in LEVELS else "medium"
    rules = [r for r in (rule_ids or []) if r in TEMPLATES] or list(TEMPLATES)
    for k in range(tries):
        rid = rng.choice(rules if k < tries // 2 else list(TEMPLATES))  # some rule/level pairs rarely yield a hunt
        instruction, make = rng.choice(TEMPLATES[rid][level])
        try:
            h = build(rid, tidy(make(lambda a, b: rng.randint(a, b))), instruction, rng)
        except Exception:  # noqa: BLE001
            h = None
        if h:
            h.level = level
            return h
    return None


def score(hunt: dict, line: int, rule_id: str) -> dict:
    """Points: 10 for the wrong line, 5 more for naming the misconception."""
    line_ok = line == hunt["wrong_index"]
    rule_ok = rule_id == hunt["rule_id"]
    return {"line_ok": line_ok, "rule_ok": rule_ok, "points": 10 * line_ok + 5 * (line_ok and rule_ok)}


__all__ = ["Hunt", "build", "make_hunt", "score", "X"]
