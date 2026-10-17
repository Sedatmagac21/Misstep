import pytest

from misstep.diagnose import Status, check_solution
from misstep.parsing import parse_line

BUGGY = [
    (["3x-(x+3)=7", "3x-x+3=7", "2x+3=7", "2x=4", "x=2"], "SIGN_DISTRIBUTION"),
    (["2(x+3)=10", "2x+3=10", "2x=7", "x=7/2"], "PARTIAL_DISTRIBUTION"),
    (["x+3=7", "x=7+3", "x=10"], "MOVE_WITHOUT_SIGN_CHANGE"),
    (["3x=12", "x=12-3", "x=9"], "WRONG_INVERSE_OPERATION"),
    (["2x+4=10", "x+4=5", "x=1"], "PARTIAL_BOTH_SIDES"),
    (["(x+3)^2", "x^2+9"], "SQUARE_OF_SUM"),
    (["x^2=9", "x=3"], "LOSE_NEGATIVE_ROOT"),
    (["(x+3)/3 = 2", "x=2"], "ILLEGAL_CANCELLATION"),
    (["x/2+x/3=5", "2x/5=5"], "ADD_FRACTIONS"),
    (["x^2 * x^3", "x^6"], "POWER_RULES"),
    (["2x+3x", "5x^2"], "LIKE_TERMS_POWER"),
    (["2x+3", "5x"], "COMBINE_UNLIKE"),
]


@pytest.mark.parametrize("lines, rule_id", BUGGY)
def test_first_error_is_found_and_named(lines, rule_id):
    report = check_solution(lines)
    assert report.first_error == 1
    assert report.final_correct is False
    ids = [d.rule.id for d in report.steps[1].diagnoses]
    assert rule_id in ids
    assert report.diagnosis.confidence == "kesin"


def test_steps_after_error_are_marked_consistent():
    report = check_solution(["3x-(x+3)=7", "3x-x+3=7", "2x+3=7", "2x=4", "x=2"])
    assert [s.status for s in report.steps[2:]] == [Status.CONSISTENT] * 3


@pytest.mark.parametrize("lines", [
    ["5-2(x+1)=1", "5-2x-2=1", "3-2x=1", "-2x=-2", "x=1"],
    ["x/2 + 3 = 5", "x/2 = 2", "x = 4"],
    ["(x+1)^2", "x^2+2x+1"],
    ["x^2=9", "x^2-9=0"],
])
def test_correct_solutions_have_no_error(lines):
    report = check_solution(lines)
    assert report.first_error is None


def test_unknown_arithmetic_slip_is_flagged_without_a_rule():
    report = check_solution(["2x+5=11", "2x=7", "x=3.5"])
    assert report.first_error == 1
    assert report.steps[1].note


def test_turkish_notation_is_parsed():
    line = parse_line("x:2 + 3 = 5")
    assert line.is_equation
    report = check_solution(["x:2 + 3 = 5", "x:2 = 2", "x = 4"])
    assert report.first_error is None and report.final_correct


def test_unreadable_line_is_reported_not_crashed():
    report = check_solution(["x+3=7", "x = 7 $ 3", "x=4"])
    assert report.steps[1].status is Status.UNREADABLE
    assert report.final_correct is True
