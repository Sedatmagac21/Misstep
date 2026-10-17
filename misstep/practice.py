"""Diagnostic practice questions for a misconception.

A question is only accepted when SymPy shows that the correct answer and the
answer the misconception produces are *different*. The wrong answers become
the multiple-choice distractors, so if the student picks one, the teacher
knows exactly which misconception is still there.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

import sympy as sp

from .bugs import RULES, RULES_BY_ID, BugRule
from .equivalence import equivalent, solutions, value
from .parsing import Line, parse_line

X = sp.Symbol("x")

# Each template: (instruction, problem text built from random integers)
def _sign(r):
    a, b, x = r(3, 9), r(2, 9), r(2, 12)
    return f"{a}x - (x + {b}) = {a * x - (x + b)}"


def _partial_dist(r):
    a, b, x = r(2, 6), r(2, 9), r(2, 12)
    return f"{a}(x + {b}) = {a * (x + b)}"


def _cancel(r):
    a, x = r(2, 9), r(1, 6)
    return f"(x + {a})/{a} = {x + 1}"


def _add_frac(r):
    a, b = r(2, 4), r(5, 7)
    x = a * b * r(1, 3)
    return f"x/{a} + x/{b} = {sp.Rational(x, a) + sp.Rational(x, b)}"


def _partial_sides(r):
    a, b, x = r(2, 5), r(1, 5), r(2, 9)
    return f"{a}x + {a * b} = {a * x + a * b}"


# Each template: (instruction, problem builder). Equations are built backwards
# from a chosen integer answer, so every coefficient range is used evenly.
TEMPLATES: dict[str, tuple[str, callable]] = {
    "SIGN_DISTRIBUTION": ("Denklemi çözünüz.", _sign),
    "PARTIAL_DISTRIBUTION": ("Denklemi çözünüz.", _partial_dist),
    "SQUARE_OF_SUM": ("İfadeyi açınız.", lambda r: f"(x + {r(2, 9)})^2"),
    "POWER_RULES": ("İfadeyi sadeleştiriniz.", lambda r: f"x^{r(2, 5)} * x^{r(2, 5)}"),
    "LIKE_TERMS_POWER": ("İfadeyi sadeleştiriniz.", lambda r: f"{r(2, 9)}x + {r(2, 9)}x"),
    "COMBINE_UNLIKE": ("İfadeyi sadeleştiriniz.", lambda r: f"{r(2, 9)}x + {r(2, 9)} + {r(2, 9)}x"),
    "ILLEGAL_CANCELLATION": ("Denklemi çözünüz.", _cancel),
    "ADD_FRACTIONS": ("Denklemi çözünüz.", _add_frac),
    "SQRT_OF_SUM": ("İşlemin sonucunu bulunuz.", lambda r: ["sqrt(9 + 16)", "sqrt(36 + 64)", "sqrt(25 + 144)", "sqrt(64 + 225)"][r(0, 3)]),
    "MOVE_WITHOUT_SIGN_CHANGE": ("Denklemi çözünüz.", lambda r: f"x + {r(3, 15)} = {r(16, 40)}"),
    "WRONG_INVERSE_OPERATION": ("Denklemi çözünüz.", lambda r: (lambda a: f"{a}x = {a * r(2, 9)}")(r(2, 9))),
    "PARTIAL_BOTH_SIDES": ("Denklemi çözünüz.", _partial_sides),
    "LOSE_NEGATIVE_ROOT": ("Denklemi çözünüz.", lambda r: f"x^2 = {r(2, 12) ** 2}"),
}


@dataclass
class Question:
    rule_id: str
    instruction: str
    problem: str
    answer: str
    choices: list[str]
    misconception_answers: list[str]  # what a student with this misconception writes
    distractor_rules: dict[str, str] = field(default_factory=dict)  # wrong choice -> misconception it reveals


def _answer(line: Line) -> str | None:
    if line.is_equation:
        sols = solutions(line, X)
        if not isinstance(sols, sp.FiniteSet) or len(sols) == 0:
            return None
        return " veya ".join(f"x = {sp.sstr(s)}" for s in sorted(sols, key=lambda s: float(s)))
    return sp.sstr(sp.expand(value(line.lhs)))


def _stages(problem: Line) -> list[Line]:
    """Lines a correct solution passes through (ax = b, x² = c), so a misconception can strike later in a longer problem."""
    if not problem.is_equation:
        return []
    expr = sp.expand(value(problem.lhs) - value(problem.rhs))
    if expr.free_symbols != {X} or not expr.is_polynomial(X):
        return []
    poly = sp.Poly(expr, X)
    if poly.degree() == 1:
        a, b = poly.all_coeffs()
        if a not in (1, -1) and (a * X).is_Mul:
            return [Line("", sp.Mul(a, X, evaluate=False), -b)]
    if poly.degree() == 2 and poly.coeff_monomial(X) == 0:
        a, c = poly.coeff_monomial(X**2), poly.coeff_monomial(1)
        return [Line("", sp.Pow(X, 2, evaluate=False), -c / a)]
    return []


def _wrong_answers(rule: BugRule, problem: Line, correct: str) -> list[str]:
    wrong: list[str] = []
    candidates = [c for line in (problem, *_stages(problem)) for c in rule.apply(line)]
    for candidate in candidates:
        try:  # an unchanged answer is skipped below, so no separate equivalence check is needed
            ans = _answer(candidate)
        except Exception:  # noqa: BLE001
            continue
        if ans and ans != correct and ans not in wrong:
            wrong.append(ans)
    return wrong


def _is_nice(answer: str) -> bool:
    return "/" not in answer and "sqrt" not in answer and len(answer) < 40


def _plausible(answer: str) -> bool:
    """Drop absurd distractors (e.g. x = 319 or x = 11*sqrt(2)) that no student would believe."""
    if "sqrt" in answer or "I" in answer:
        return False
    for part in answer.split(" veya "):
        try:
            if abs(sp.Rational(part.split("=")[-1].strip())) > 100:
                return False
        except (TypeError, ValueError, SyntaxError):
            pass
    return len(answer) < 40


def display(answer: str) -> str:
    """Write SymPy output the way it is written in class: 10*x**2 -> 10x²."""
    sup = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
    answer = re.sub(r"(?:\*\*|\^)(\d+)", lambda m: m.group(1).translate(sup), answer)
    answer = re.sub(r"(\d)\*(?=[a-z(])", r"\1", answer)
    return answer.replace("*", "·").replace("sqrt", "√")


def _near_misses(correct: str, taken: list[str], rng: random.Random) -> list[str]:
    """Arithmetic-slip options (a number off by 1, 2, ...) when misconceptions give too few choices."""
    out = []
    numbers = list(re.finditer(r"(?<![\w.])\d+", correct))
    for d in rng.sample([1, -1, 2, -2, 3, 10], 6):
        for m in rng.sample(numbers, len(numbers)):
            n = int(m.group()) + d
            if n < 0:
                continue
            cand = correct[: m.start()] + str(n) + correct[m.end():]
            if cand not in taken and cand not in out and cand != correct:
                out.append(cand)
                break
    return out


def build_question(rule_id: str, text: str, instruction: str, rng: random.Random) -> Question | None:
    """Turn one problem into a verified diagnostic question, or None if it is not diagnostic."""
    rule = RULES_BY_ID[rule_id]
    problem = parse_line(text)
    correct = _answer(problem)
    if not correct or not _is_nice(correct):
        return None
    wrong = sorted((w for w in _wrong_answers(rule, problem, correct) if _plausible(w)),
                   key=lambda w: not _is_nice(w))[:3]  # stable: direct misconceptions before later-stage ones
    if not wrong:
        return None
    source = {w: rule_id for w in wrong}
    for other in RULES:
        if other.id != rule_id:
            for w in _wrong_answers(other, problem, correct):
                if _plausible(w):
                    source.setdefault(w, other.id)
    others = sorted((w for w in source if w not in wrong), key=lambda w: (not _is_nice(w), len(w)))
    choices = [correct, *wrong, *others][:4]
    choices += _near_misses(correct, choices, rng)[: 4 - len(choices)]
    rng.shuffle(choices)
    return Question(rule_id, instruction, text, correct, choices, wrong,
                    {c: source[c] for c in choices if c in source})


def make_question(rule_id: str, seed: int | None = None, tries: int = 60) -> Question | None:
    rng = random.Random(seed)
    instruction, build = TEMPLATES[rule_id]
    for _ in range(tries):
        q = build_question(rule_id, build(lambda a, b: rng.randint(a, b)), instruction, rng)
        if q:
            return q
    return None


def make_questions(rule_id: str, n: int = 3, seed: int = 0) -> list[Question]:
    out, seen, s = [], set(), seed
    while len(out) < n and s < seed + 50:
        q = make_question(rule_id, seed=s)
        s += 1
        if q and q.problem not in seen:
            seen.add(q.problem)
            out.append(q)
    return out
