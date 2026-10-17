"""Değerlendirme seti: how often does Misstep find the right step and the right misconception?

python -m misstep.evaluate            # runs eval/cases.jsonl, prints a table, writes eval/results.json
python -m misstep.evaluate --photos   # also reads eval/photos/*.jpg with Gemma and compares to the .txt next to each

Each case is a hand-written student solution with the expected first wrong line (null when the solution is
correct) and the expected misconception (null for a plain arithmetic slip). The cases were written before
running the engine on them and are not adjusted to make the numbers look better; failures are listed.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .diagnose import check_solution

ROOT = Path(__file__).resolve().parent.parent / "eval"
CASES = ROOT / "cases.jsonl"
RESULTS = ROOT / "results.json"


def load_cases(path: Path = CASES) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def run(cases: list[dict]) -> dict:
    rows = []
    started = time.perf_counter()
    for c in cases:
        t0 = time.perf_counter()
        report = check_solution(c["lines"])
        got_rules = [d.rule.id for d in report.steps[report.first_error].diagnoses] if report.first_error is not None else []
        rows.append({"id": c["id"], "expected_step": c["first_error"], "got_step": report.first_error,
                     "expected_rule": c["rule"], "got_rule": got_rules[0] if got_rules else None, "candidates": got_rules,
                     "step_ok": report.first_error == c["first_error"],
                     "rule_ok": (got_rules[:1] == [c["rule"]]) if c["rule"] else not got_rules,
                     "ms": round((time.perf_counter() - t0) * 1000)})
    correct = [r for r in rows if r["expected_step"] is None]
    wrong = [r for r in rows if r["expected_step"] is not None]
    named = [r for r in wrong if r["expected_rule"]]
    slips = [r for r in wrong if not r["expected_rule"]]
    pct = lambda xs, f: round(sum(map(f, xs)) / len(xs), 3) if xs else None  # noqa: E731
    return {
        "cases": len(rows), "correct_solutions": len(correct), "with_mistake": len(wrong), "rules_covered": len({r["expected_rule"] for r in named}),
        "step_accuracy": pct(rows, lambda r: r["step_ok"]),
        "rule_top1": pct(named, lambda r: r["step_ok"] and r["got_rule"] == r["expected_rule"]),
        "rule_in_candidates": pct(named, lambda r: r["step_ok"] and r["expected_rule"] in r["candidates"]),
        "false_alarm_rate": pct(correct, lambda r: r["got_step"] is not None),
        "slip_honesty": pct(slips, lambda r: r["step_ok"] and not r["candidates"]),
        "avg_ms": round(sum(r["ms"] for r in rows) / len(rows)) if rows else 0,
        "seconds": round(time.perf_counter() - started, 1),
        "failures": [r for r in rows if not (r["step_ok"] and r["rule_ok"])],
        "rows": rows,
    }


def run_photos(folder: Path = ROOT / "photos") -> dict | None:
    """Optional: Gemma's reading of real photos against a hand-typed transcript (same name, .txt)."""
    from .equivalence import equivalent
    from .parsing import parse_line
    from .vision import VisionError, read_image

    pairs = [(p, p.with_suffix(".txt")) for p in sorted(folder.glob("*.jp*g")) + sorted(folder.glob("*.png")) if p.with_suffix(".txt").exists()]
    if not pairs:
        return None
    lines_ok = lines_n = 0
    for img, txt in pairs:
        truth = [l.strip() for l in txt.read_text(encoding="utf-8").splitlines() if l.strip()]
        try:
            read = [l.text for l in read_image(img.read_bytes())]
        except VisionError:
            return {"error": "model_offline", "photos": len(pairs)}
        for k, t in enumerate(truth):
            lines_n += 1
            try:
                lines_ok += k < len(read) and (read[k].replace(" ", "") == t.replace(" ", "") or equivalent(parse_line(read[k]), parse_line(t)))
            except Exception:  # noqa: BLE001
                pass
    return {"photos": len(pairs), "lines": lines_n, "line_accuracy": round(lines_ok / lines_n, 3) if lines_n else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--photos", action="store_true", help="also evaluate Gemma's photo reading on eval/photos")
    args = ap.parse_args()
    res = run(load_cases())
    if args.photos:
        res["vision"] = run_photos()
    RESULTS.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    show = lambda x: "–" if x is None else f"%{round(x * 100)}"  # noqa: E731
    print(f"Misstep değerlendirme seti: {res['cases']} vaka ({res['correct_solutions']} doğru çözüm, {res['with_mistake']} hatalı, "
          f"{res['rules_covered']}/13 yanılgı)")
    print(f"  İlk hatalı adımı bulma ........ {show(res['step_accuracy'])}")
    print(f"  Yanılgıyı doğru adlandırma .... {show(res['rule_top1'])} (adaylar arasında {show(res['rule_in_candidates'])})")
    print(f"  Doğru çözüme yanlış alarm ..... {show(res['false_alarm_rate'])}")
    print(f"  İşlem hatasında uydurmama ..... {show(res['slip_honesty'])}")
    print(f"  Ortalama süre ................. {res['avg_ms']} ms / çözüm")
    for f in res["failures"]:
        print(f"  ✗ {f['id']}: beklenen adım {f['expected_step']} / {f['expected_rule']}, bulunan {f['got_step']} / {f['got_rule']}")
    if res.get("vision"):
        print(f"  Fotoğraf okuma: {res['vision']}")
    print(f"Sonuçlar: {RESULTS}")


if __name__ == "__main__":
    main()
