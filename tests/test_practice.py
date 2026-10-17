import pytest

from misstep.bugs import RULES
from misstep.equivalence import solutions
from misstep.parsing import parse_line
from misstep.practice import TEMPLATES, make_questions
import sympy as sp


def test_every_rule_has_a_template():
    assert {r.id for r in RULES} == set(TEMPLATES)


@pytest.mark.parametrize("rule_id", sorted(TEMPLATES))
def test_questions_are_verified_and_diagnostic(rule_id):
    qs = make_questions(rule_id, n=2)
    assert len(qs) == 2
    for q in qs:
        assert q.answer in q.choices
        assert q.misconception_answers and q.answer not in q.misconception_answers
        line = parse_line(q.problem)
        if line.is_equation:  # the answer key really solves the equation
            sols = solutions(line, sp.Symbol("x"))
            for part in q.answer.split(" veya "):
                assert sp.Rational(part.split("=")[1]) in sols


def test_partial_division_gets_the_classic_distractor():
    q = make_questions("PARTIAL_BOTH_SIDES", n=1)[0]
    a, b, c = (int(t) for t in q.problem.replace("x", " ").replace("+", " ").replace("=", " ").split())
    assert f"x = {c // a - b}" in q.misconception_answers  # ax + b = c  ->  x + b = c/a
