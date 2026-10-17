"""Local learning record and student model.

Every checked solution and every practice answer is stored in a SQLite file on
this computer. Mastery of each misconception is tracked with Bayesian
Knowledge Tracing (Corbett & Anderson, 1994): each observation updates the
probability that the student has overcome that misconception.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .bugs import RULES, RULES_BY_ID
from .db import connect

DB_PATH = Path(os.environ.get("MISSTEP_DB", Path.home() / ".misstep" / "misstep.db"))

TOPICS: dict[str, list[str]] = {
    "Parantez ve dağılma": ["SIGN_DISTRIBUTION", "PARTIAL_DISTRIBUTION"],
    "Denklem çözme": ["MOVE_WITHOUT_SIGN_CHANGE", "WRONG_INVERSE_OPERATION", "PARTIAL_BOTH_SIDES"],
    "Terimler ve sadeleştirme": ["LIKE_TERMS_POWER", "COMBINE_UNLIKE"],
    "Kesirli ifadeler": ["ILLEGAL_CANCELLATION", "ADD_FRACTIONS"],
    "Özdeşlikler": ["SQUARE_OF_SUM"],
    "Üslü ve köklü ifadeler": ["POWER_RULES", "SQRT_OF_SUM"],
    "İkinci dereceden denklemler": ["LOSE_NEGATIVE_ROOT"],
}
TOPIC_OF = {rid: t for t, ids in TOPICS.items() for rid in ids}
assert set(TOPIC_OF) == {r.id for r in RULES}

# BKT parameters: prior, learn (transit), slip, guess (4-choice questions)
P_INIT, P_LEARN, P_SLIP, P_GUESS = 0.3, 0.15, 0.1, 0.25


def bkt_update(p: float, correct: bool) -> float:
    if correct:
        post = p * (1 - P_SLIP) / (p * (1 - P_SLIP) + (1 - p) * P_GUESS)
    else:
        post = p * P_SLIP / (p * P_SLIP + (1 - p) * (1 - P_GUESS))
    return post + (1 - post) * P_LEARN


@dataclass
class Attempt:
    ts: datetime
    student: str
    kind: str          # "solution" | "practice"
    rule_id: str       # misconception this observation is about
    correct: bool
    detail: dict


class Store:
    def __init__(self, path: Path | str = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = connect(self.path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY, ts TEXT, student TEXT, kind TEXT,
            rule_id TEXT, correct INTEGER, detail TEXT)""")
        self.db.commit()

    def add(self, student: str, kind: str, rule_id: str, correct: bool, detail: dict | None = None,
            ts: datetime | None = None) -> None:
        self.db.execute("INSERT INTO attempts (ts, student, kind, rule_id, correct, detail) VALUES (?,?,?,?,?,?)",
                        ((ts or datetime.now()).isoformat(timespec="seconds"), student.strip() or "Öğrenci",
                         kind, rule_id, int(correct), json.dumps(detail or {}, ensure_ascii=False)))
        self.db.commit()

    def attempts(self, student: str) -> list[Attempt]:
        rows = self.db.execute("SELECT ts, student, kind, rule_id, correct, detail FROM attempts WHERE student=? ORDER BY ts",
                               (student.strip() or "Öğrenci",)).fetchall()
        return [Attempt(datetime.fromisoformat(r[0]), r[1], r[2], r[3], bool(r[4]), json.loads(r[5])) for r in rows]

    def students(self) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT DISTINCT student FROM attempts ORDER BY student")]

    def clear(self, student: str) -> None:
        self.db.execute("DELETE FROM attempts WHERE student=?", (student,))
        self.db.commit()


@dataclass
class Summary:
    total: int
    correct: int
    by_day: dict[date, tuple[int, int]]          # day -> (correct, wrong)
    mastery: dict[str, float]                    # rule_id -> P(known)
    seen: dict[str, int]                         # rule_id -> observations
    trend: dict[str, float]                      # rule_id -> mastery change over last 7 days
    streak: int

    def topic_mastery(self) -> dict[str, float]:
        out = {}
        for topic, ids in TOPICS.items():
            seen = [self.mastery[r] for r in ids if self.seen.get(r)]
            if seen:
                out[topic] = sum(seen) / len(seen)
        return out

    def weakest(self, n: int = 3) -> list[str]:
        ids = [r for r in self.mastery if self.seen.get(r)]
        return sorted(ids, key=lambda r: self.mastery[r])[:n]

    def recommendation(self) -> str | None:
        weak = [r for r in self.weakest(len(RULES)) if self.mastery[r] < 0.95]
        return weak[0] if weak else None


PRIMARY = ("solution", "practice", "hunt")  # kinds that count as a question; traps and analyses only inform mastery


def summarize(attempts: list[Attempt], today: date | None = None) -> Summary:
    today = today or date.today()
    by_day: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    mastery = {r.id: P_INIT for r in RULES}
    seen: dict[str, int] = defaultdict(int)
    week_ago = {r.id: P_INIT for r in RULES}
    cutoff = datetime.combine(today - timedelta(days=7), datetime.min.time())
    primary = [a for a in attempts if a.kind in PRIMARY]
    for a in attempts:
        if a.kind in PRIMARY:  # trap observations update mastery only
            by_day[a.ts.date()][0 if a.correct else 1] += 1
        if a.rule_id in mastery:
            mastery[a.rule_id] = bkt_update(mastery[a.rule_id], a.correct)
            seen[a.rule_id] += 1
            if a.ts < cutoff:
                week_ago[a.rule_id] = mastery[a.rule_id]
    streak, d = 0, today
    if d not in by_day:
        d -= timedelta(days=1)  # today not studied yet: the streak is still alive
    while d in by_day:
        streak, d = streak + 1, d - timedelta(days=1)
    return Summary(
        total=len(primary), correct=sum(a.correct for a in primary),
        by_day={k: tuple(v) for k, v in by_day.items()}, mastery=mastery, seen=dict(seen),
        trend={r: mastery[r] - week_ago[r] for r in mastery}, streak=streak,
    )


def rule_name(rule_id: str) -> str:
    return RULES_BY_ID[rule_id].name


def record_solution(store: Store, student: str, report, lines: list[str]) -> None:
    """Log a checked solution and what it says about each misconception."""
    from .diagnose import Status  # local import: progress must not depend on diagnosis at import time
    from .equivalence import equivalent

    detail = {"lines": lines, "first_error": report.first_error}
    diag = report.diagnosis
    if report.first_error is not None:
        store.add(student, "solution", diag.rule.id if diag else "UNKNOWN", False, detail)
        return
    if report.final_correct is False:
        store.add(student, "solution", "UNKNOWN", False, detail)
        return
    store.add(student, "solution", "SOLVED", True, detail)
    given = next((s.line for s in report.steps if s.status is Status.GIVEN), None)
    if given is None:
        return
    for rule in RULES:  # a correct solution is evidence against every trap the problem contained
        try:
            if any(not equivalent(given, c) for c in rule.apply(given)):
                store.add(student, "solution_trap", rule.id, True, {})
        except Exception:  # noqa: BLE001
            continue
