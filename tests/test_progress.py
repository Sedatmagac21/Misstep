from datetime import date, datetime, timedelta

from misstep.demo_data import DEMO, seed
from misstep.diagnose import check_solution
from misstep.practice import make_question
from misstep.progress import Store, bkt_update, record_solution, summarize


def test_bkt_moves_in_the_right_direction():
    assert bkt_update(0.5, True) > 0.5 > bkt_update(0.5, False)


def test_streak_and_daily_counts(tmp_path):
    st = Store(tmp_path / "db.sqlite")
    today = date(2026, 10, 17)
    for back in (0, 1, 2, 5):
        st.add("A", "practice", "SIGN_DISTRIBUTION", back != 1, ts=datetime(2026, 10, 17, 12) - timedelta(days=back))
    s = summarize(st.attempts("A"), today)
    assert s.streak == 3 and s.total == 4 and s.correct == 3
    assert s.by_day[date(2026, 10, 16)] == (0, 1)


def test_solutions_are_recorded_as_evidence(tmp_path):
    st = Store(tmp_path / "db.sqlite")
    record_solution(st, "B", check_solution(["3x-(x+3)=7", "3x-x+3=7", "x=2"]), [])
    failed = summarize(st.attempts("B")).mastery["SIGN_DISTRIBUTION"]
    assert failed < 0.3
    # a correct solution of a problem with the same trap is evidence of progress
    record_solution(st, "B", check_solution(["5-2(x+1)=1", "5-2x-2=1", "x=1"]), [])
    s = summarize(st.attempts("B"))
    assert s.total == 2 and s.correct == 1
    assert s.mastery["SIGN_DISTRIBUTION"] > failed
    assert s.seen["PARTIAL_DISTRIBUTION"] >= 1


def test_distractors_know_their_misconception():
    q = make_question("SIGN_DISTRIBUTION", seed=3)
    for wrong in q.misconception_answers:
        assert q.distractor_rules[wrong] == "SIGN_DISTRIBUTION"


def test_demo_summary_has_history_and_weak_spots(tmp_path):
    from misstep.server import summary_json

    st = Store(tmp_path / "db.sqlite")
    seed(st)
    s = summary_json(st, DEMO, "tr")
    assert len(s["days"]) == 182 and s["total"] > 50 and s["streak"] >= 0
    m = [w["mastery"] for w in s["weakest"]]
    assert len(m) == 3 and m == sorted(m) and s["recommendation"]["topic_key"]
