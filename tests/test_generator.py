import pytest
import sympy as sp

from misstep.generator import LEVELS, TEMPLATES, generate, interpret_keywords, tidy
from misstep.equivalence import solutions
from misstep.parsing import parse_line
from misstep.progress import TOPICS


@pytest.mark.parametrize("rule_id", sorted(TEMPLATES))
@pytest.mark.parametrize("level", LEVELS)
def test_every_rule_and_level_makes_verified_diagnostic_questions(rule_id, level):
    items = generate([rule_id], level, 3, seed=11)
    assert len(items) == 3
    for item in items:
        q = item.question
        assert len(q.choices) == 4 and q.answer in q.choices
        assert q.misconception_answers and q.answer not in q.misconception_answers
        line = parse_line(q.problem)
        if line.is_equation:
            sols = solutions(line, sp.Symbol("x"))
            for part in q.answer.split(" veya "):
                assert sp.Rational(part.split("=")[1]) in sols


def test_count_and_spread_over_topics():
    rules = TOPICS["Kesirli ifadeler"] + TOPICS["Parantez ve dağılma"]
    items = generate(rules, "medium", 8, seed=3)
    assert len(items) == 8 and len({i.question.problem for i in items}) == 8
    assert {i.question.rule_id for i in items} == set(rules)


def test_tidy_writes_problems_like_a_teacher():
    assert tidy("8x + 15 = 1x + 8") == "8x + 15 = x + 8"
    assert tidy("12x + 4 = 4x + -28") == "12x + 4 = 4x - 28"
    assert tidy("10x + 1 = 21") == "10x + 1 = 21"


def test_free_text_request_without_model():
    s = interpret_keywords("zor seviye 8 kesirli denklem, pazar alışverişi temalı")
    assert s.level == "hard" and s.count == 8 and s.theme == "pazar alışverişi"
    assert set(TOPICS["Kesirli ifadeler"]) <= set(s.rule_ids)
    assert interpret_keywords("kolay 3 soru").count == 3
