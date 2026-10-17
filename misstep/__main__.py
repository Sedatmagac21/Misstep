"""Command line demo:  python -m misstep "3x-(x+3)=7" "3x-x+3=7" "2x=4" "x=2" """

import sys

from .diagnose import Status, check_solution

ICONS = {Status.GIVEN: "📝", Status.OK: "✅", Status.ERROR: "❌", Status.CONSISTENT: "➡️", Status.UNREADABLE: "❓"}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    report = check_solution(argv)
    for step in report.steps:
        print(f"{ICONS[step.status]} {step.index}. {step.raw}")
        for d in step.diagnoses:
            r = d.rule
            print(f"    Hata ({d.confidence}): {r.name}\n    Yanılgı: {r.misconception}\n    Doğrusu: {r.correct_rule}")
        if step.note:
            print(f"    Not: {step.note}")
    if report.final_correct is not None:
        print("\nSonuç:", "doğru ✅" if report.final_correct else "yanlış ❌")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
