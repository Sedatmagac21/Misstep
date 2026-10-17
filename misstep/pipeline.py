"""One call from lines of student work to everything the teacher sees."""

from __future__ import annotations

from dataclasses import dataclass, field

from .counterexample import counterexample
from .diagnose import Report, check_solution
from .practice import Question, make_questions
from .rag import Chunk, explain


@dataclass
class Analysis:
    report: Report
    counterexample: str | None = None
    explanation: str = ""
    sources: list[Chunk] = field(default_factory=list)
    explained_by_model: bool = False
    questions: list[Question] = field(default_factory=list)


def analyze(lines: list[str], explain_with_model: bool = True, seed: int = 0, lang: str = "tr") -> Analysis:
    report = check_solution(lines)
    result = Analysis(report)
    i = report.first_error
    if i is None:
        return result
    step = report.steps[i]
    prev = next(s for s in reversed(report.steps[:i]) if s.line is not None)
    result.counterexample = counterexample(prev.line, step.line, lang=lang)
    diag = report.diagnosis
    diagnosis_text = f"{diag.rule.name}. {diag.rule.misconception}" if diag else "Bilinen bir kalıba uymayan işlem hatası"
    if explain_with_model:
        result.explanation, result.sources, result.explained_by_model = explain(
            prev.raw, step.raw, diagnosis_text, result.counterexample, diag.rule.id if diag else None, lang=lang
        )
    if diag:
        result.questions = make_questions(diag.rule.id, n=3, seed=seed)
    return result
