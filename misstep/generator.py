"""Question generator with difficulty levels, topic choice and free-text requests.

Every question is built backwards from an integer answer, then checked by
SymPy: the answer key must really solve it and at least one known
misconception must lead to a *different* answer (that wrong answer becomes a
choice, so a wrong pick tells us which misconception is still there).

A free-text request ("zor kesirli 5 soru, pazar alışverişi temalı") is turned
into settings by Gemma 4 when it is running, with a keyword fallback that
works offline. Gemma may also wrap an equation in a short story; the
equation itself always comes from the verified template.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field

from .practice import Question, build_question, display
from .progress import TOPICS, TOPIC_OF

LEVELS = ("easy", "medium", "hard")
LEVEL_TR = {"easy": "Kolay", "medium": "Orta", "hard": "Zor"}

SOLVE, SIMPLIFY, EXPAND, EVAL = "Denklemi çözünüz.", "İfadeyi sadeleştiriniz.", "İfadeyi açınız.", "İşlemin sonucunu bulunuz."


# ---- templates: rule -> level -> list of (instruction, builder(r) -> problem text) ----

def _sign_easy(r):
    a, b, x = r(3, 9), r(2, 9), r(2, 12)
    return f"{a}x - (x + {b}) = {a * x - (x + b)}"


def _sign_med(r):
    a, b, c, x = r(3, 7), r(1, 6), r(2, 9), r(-6, 12)
    if r(0, 1):
        return f"{a}x - (2x - {b}) = {a * x - (2 * x - b)}"
    return f"{a}(x + {c}) - (x + {b}) = {a * (x + c) - (x + b)}"


def _sign_hard(r):
    a, b, c, d, x = r(4, 9), r(2, 7), r(2, 3), r(2, 9), r(-8, 10)
    return f"{a}(x - {b}) - ({c}x - {d}) = {a * (x - b) - (c * x - d)}"


def _dist_easy(r):
    a, b, x = r(2, 6), r(2, 9), r(2, 12)
    return f"{a}(x + {b}) = {a * (x + b)}"


def _dist_med(r):
    a, b, c, x = r(2, 6), r(2, 9), r(1, 9), r(-5, 12)
    return f"{a}(x + {b}) + {c} = {a * (x + b) + c}"


def _dist_hard(r):
    a, b, c, d, x = r(3, 7), r(2, 9), r(2, 5), r(1, 6), r(-6, 10)
    if a == c:
        a += 1
    return f"{a}(x + {b}) = {c}(x + {d}) + {a * (x + b) - c * (x + d)}"


def _cancel_easy(r):
    a, x = r(2, 9), r(1, 6)
    return f"(x + {a})/{a} = {x + 1}"


def _cancel_med(r):
    a, k = r(2, 6), r(1, 8)
    x = a * k
    if r(0, 1):
        return f"(x + {a})/{a} = {x // a + 1}"
    return f"(x + {2 * a})/{a} = {k + 2}"


def _cancel_hard(r):
    a, b, k = r(2, 5), r(2, 9), r(1, 6)
    return f"(x + {a * b})/{a} - {b} = {k}"


def _frac_easy(r):
    a, b = r(2, 4), r(5, 7)
    x = a * b * r(1, 3)
    return f"x/{a} + x/{b} = {x // a + x // b}"


def _frac_med(r):
    a, b = r(2, 3), r(4, 5)
    x = a * b * r(1, 4)
    c = r(1, 9)
    return f"x/{a} + x/{b} + {c} = {x // a + x // b + c}"


def _frac_hard(r):
    a, b = r(2, 4), r(5, 6)
    y = a * b * r(1, 3)  # y = x + 1
    return f"(x + 1)/{a} + (x + 1)/{b} = {y // a + y // b}"


def _sides_easy(r):
    a, b, x = r(2, 5), r(1, 5), r(2, 9)
    return f"{a}x + {a * b} = {a * x + a * b}"


def _sides_med(r):
    a, b, x = r(2, 5), r(1, 6), r(-4, 9)
    return f"{a}x - {a * b} = {a * x - a * b}"


def _sides_hard(r):
    a, b, c, x = r(2, 4), r(1, 5), r(2, 3), r(-5, 8)
    return f"{a * c}x + {a * b} = {a}x + {a * c * x + a * b - a * x}"


def _move_easy(r):
    return f"x + {r(3, 15)} = {r(16, 40)}"


def _move_med(r):
    a, b, x = r(2, 6), r(3, 15), r(2, 9)
    return f"{a}x + {b} = {a * x + b}"


def _move_hard(r):
    a, b, c, x = r(4, 9), r(3, 15), r(1, 3), r(-5, 9)
    return f"{a}x + {b} = {c}x + {(a - c) * x + b}"


def _inv_easy(r):
    a = r(2, 9)
    return f"{a}x = {a * r(2, 9)}"


def _inv_med(r):
    a, b, x = r(2, 9), r(1, 12), r(2, 9)
    return f"{a}x + {b} = {a * x + b}"


def _inv_hard(r):
    a, b, c, x = r(5, 9), r(2, 9), r(1, 3), r(2, 8)
    return f"{a}x - {b} = {c}x + {(a - c) * x - b}"


def _root_easy(r):
    return f"x^2 = {r(2, 12) ** 2}"


def _root_med(r):
    a, b = r(2, 10), r(1, 20)
    return f"x^2 - {b} = {a * a - b}"


def _root_hard(r):
    a, b = r(2, 4), r(2, 6)
    return f"{a}x^2 = {a * b * b}"


TEMPLATES: dict[str, dict[str, list[tuple[str, callable]]]] = {
    "SIGN_DISTRIBUTION": {"easy": [(SOLVE, _sign_easy)], "medium": [(SOLVE, _sign_med)], "hard": [(SOLVE, _sign_hard)]},
    "PARTIAL_DISTRIBUTION": {"easy": [(SOLVE, _dist_easy)], "medium": [(SOLVE, _dist_med)], "hard": [(SOLVE, _dist_hard)]},
    "SQUARE_OF_SUM": {
        "easy": [(EXPAND, lambda r: f"(x + {r(2, 9)})^2")],
        "medium": [(EXPAND, lambda r: f"({r(2, 4)}x + {r(1, 7)})^2")],
        "hard": [(EXPAND, lambda r: f"(x + {r(2, 6)})^2 + (x + {r(1, 5)})^2")],
    },
    "POWER_RULES": {
        "easy": [(SIMPLIFY, lambda r: f"x^{r(2, 5)} * x^{r(2, 5)}")],
        "medium": [(SIMPLIFY, lambda r: f"(x^{r(2, 4)})^{r(2, 4)}")],
        "hard": [(SIMPLIFY, lambda r: f"(x^{r(2, 3)})^{r(2, 3)} * x^{r(2, 5)}")],
    },
    "LIKE_TERMS_POWER": {
        "easy": [(SIMPLIFY, lambda r: f"{r(2, 9)}x + {r(2, 9)}x")],
        "medium": [(SIMPLIFY, lambda r: f"{r(5, 12)}x + {r(2, 9)}x - {r(1, 4)}x")],
        "hard": [(SIMPLIFY, lambda r: f"{r(2, 6)}x + {r(2, 9)}y + {r(2, 9)}x - {r(1, 4)}y")],
    },
    "COMBINE_UNLIKE": {
        "easy": [(SIMPLIFY, lambda r: f"{r(2, 9)}x + {r(2, 9)} + {r(2, 9)}x")],
        "medium": [(SIMPLIFY, lambda r: f"{r(2, 9)}x + {r(2, 9)} + {r(2, 9)}x - {r(1, 9)}")],
        "hard": [(SIMPLIFY, lambda r: f"{r(2, 5)}x^2 + {r(2, 9)}x + {r(2, 9)} + {r(2, 9)}x")],
    },
    "ILLEGAL_CANCELLATION": {"easy": [(SOLVE, _cancel_easy)], "medium": [(SOLVE, _cancel_med)], "hard": [(SOLVE, _cancel_hard)]},
    "ADD_FRACTIONS": {"easy": [(SOLVE, _frac_easy)], "medium": [(SOLVE, _frac_med)], "hard": [(SOLVE, _frac_hard)]},
    "SQRT_OF_SUM": {
        "easy": [(EVAL, lambda r: ["sqrt(9 + 16)", "sqrt(36 + 64)", "sqrt(16 + 9)", "sqrt(64 + 36)"][r(0, 3)])],
        "medium": [(EVAL, lambda r: ["sqrt(25 + 144)", "sqrt(64 + 225)", "sqrt(81 + 144)", "sqrt(144 + 256)"][r(0, 3)])],
        "hard": [(EVAL, lambda r: ["sqrt(9 + 16) + sqrt(36 + 64)", "2*sqrt(25 + 144)", "sqrt(64 + 36) - sqrt(9 + 16)",
                                    "sqrt(81 + 144) - sqrt(16 + 9)", "3*sqrt(36 + 64)", "sqrt(25 + 144) + sqrt(64 + 225)"][r(0, 5)])],
    },
    "MOVE_WITHOUT_SIGN_CHANGE": {"easy": [(SOLVE, _move_easy)], "medium": [(SOLVE, _move_med)], "hard": [(SOLVE, _move_hard)]},
    "WRONG_INVERSE_OPERATION": {"easy": [(SOLVE, _inv_easy)], "medium": [(SOLVE, _inv_med)], "hard": [(SOLVE, _inv_hard)]},
    "PARTIAL_BOTH_SIDES": {"easy": [(SOLVE, _sides_easy)], "medium": [(SOLVE, _sides_med)], "hard": [(SOLVE, _sides_hard)]},
    "LOSE_NEGATIVE_ROOT": {"easy": [(SOLVE, _root_easy)], "medium": [(SOLVE, _root_med)], "hard": [(SOLVE, _root_hard)]},
}


def tidy(text: str) -> str:
    """Write generated problems the way a teacher would: 1x -> x, + -3 -> - 3, - -3 -> + 3."""
    text = re.sub(r"(?<![\d.])1(?=[a-z(])", "", text)
    text = re.sub(r"\+ -(\d)", r"- \1", text)
    return re.sub(r"- -(\d)", r"+ \1", text)


@dataclass
class Settings:
    rule_ids: list[str]
    level: str = "medium"
    count: int = 5
    theme: str = ""          # optional story theme, e.g. "pazar alışverişi"
    understood: str = ""     # human-readable summary of what the request was taken to mean
    by_model: bool = False


@dataclass
class Generated:
    question: Question
    level: str
    story: str = ""
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        q = asdict(self.question)
        q.update(level=self.level, story=self.story, topic=TOPIC_OF[self.question.rule_id],
                 problem_display=display(self.question.problem),
                 choices_display=[display(c) for c in self.question.choices])
        return q


def generate(rule_ids: list[str], level: str = "medium", count: int = 5, seed: int = 0) -> list[Generated]:
    """``count`` distinct verified questions spread evenly over ``rule_ids``."""
    level = level if level in LEVELS else "medium"
    count = max(1, min(int(count), 20))
    rng = random.Random(seed)
    out: list[Generated] = []
    seen: set[str] = set()
    rules = list(rule_ids) or list(TEMPLATES)
    attempts = 0
    i = 0
    while len(out) < count and attempts < count * 80:
        rid = rules[i % len(rules)]
        attempts += 1
        instruction, build = rng.choice(TEMPLATES[rid][level])
        text = tidy(build(lambda a, b: rng.randint(a, b)))
        if text in seen:
            continue
        try:
            q = build_question(rid, text, instruction, rng)
        except Exception:  # noqa: BLE001 - a malformed candidate is skipped
            q = None
        if q is None:
            continue
        seen.add(text)
        out.append(Generated(q, level))
        i += 1
    return out


# ---- free-text requests ----

_KEYWORDS = {
    "Parantez ve dağılma": ["parantez", "dağılma", "dagilma", "bracket", "distribut"],
    "Denklem çözme": ["denklem", "eşitlik", "esitlik", "equation", "karşıya", "linear"],
    "Terimler ve sadeleştirme": ["terim", "sadeleş", "sadeles", "benzer", "like term", "simplif"],
    "Kesirli ifadeler": ["kesir", "payda", "fraction", "rasyonel"],
    "Özdeşlikler": ["özdeşlik", "ozdeslik", "kare açılım", "toplamın karesi", "identit", "square of"],
    "Üslü ve köklü ifadeler": ["üs", "üslü", "kuvvet", "kök", "karekök", "power", "exponent", "root", "sqrt"],
    "İkinci dereceden denklemler": ["ikinci derece", "x^2", "x²", "quadratic"],
}
_LEVEL_WORDS = {"easy": ["kolay", "basit", "easy", "simple"], "hard": ["zor", "ileri", "hard", "difficult", "challenging", "lgs", "yks"],
                "medium": ["orta", "medium", "normal"]}
_THEME = re.compile(r"(\w[\w\s]{2,30}?)\s*(?:temalı|temali|konulu|hikayeli|hikâyeli|themed)", re.I)


def interpret_keywords(text: str, default_level: str = "medium", default_count: int = 5) -> Settings:
    low = text.lower()
    topics = [t for t, words in _KEYWORDS.items() if any(w in low for w in words)]
    if "Üslü ve köklü ifadeler" in topics and not any(w in low for w in ["üslü", "kuvvet", "kök", "power", "exponent", "root", "sqrt", " üs "]):
        topics.remove("Üslü ve köklü ifadeler")  # "üs" also appears inside other words
    level = next((lv for lv, words in _LEVEL_WORDS.items() if any(w in low for w in words)), default_level)
    num = re.search(r"\b(\d{1,2})\b", low)
    count = max(1, min(int(num.group(1)), 20)) if num else default_count
    theme = (m.group(1).strip() if (m := _THEME.search(text)) else "")
    rule_ids = [r for t in topics for r in TOPICS[t]] or [r for ids in TOPICS.values() for r in ids]
    understood = f"{', '.join(topics) or 'Tüm konular'} · {LEVEL_TR[level]} · {count} soru" + (f" · Tema: {theme}" if theme else "")
    return Settings(rule_ids, level, count, theme, understood, False)


REQUEST_PROMPT = """A student or teacher typed a request for algebra practice questions:
"{text}"
Choose settings. Topics must be chosen only from this list: {topics}.
Return JSON with: topics (list of topic names from the list, empty = all), level ("easy", "medium" or "hard"),
count (1-20), theme (a short story theme if they asked for one, otherwise "")."""

REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {"type": "array", "items": {"type": "string"}},
        "level": {"type": "string", "enum": list(LEVELS)},
        "count": {"type": "integer"},
        "theme": {"type": "string"},
    },
    "required": ["topics", "level", "count", "theme"],
}


def interpret(text: str, default_level: str = "medium", default_count: int = 5, use_model: bool = True) -> Settings:
    """Settings from a free-text request: Gemma 4 when available, keywords otherwise."""
    fallback = interpret_keywords(text, default_level, default_count)
    if not use_model or not text.strip():
        return fallback
    from .vision import MODEL, VisionError, _post
    try:
        reply = _post("/api/chat", {"model": MODEL, "stream": False, "format": REQUEST_SCHEMA, "options": {"temperature": 0},
                                    "messages": [{"role": "user", "content": REQUEST_PROMPT.format(text=text, topics=list(TOPICS))}]},
                      timeout=60)
        data = json.loads(reply["message"]["content"])
    except (VisionError, KeyError, ValueError, TypeError):
        return fallback
    topics = [t for t in data.get("topics", []) if t in TOPICS]
    level = data.get("level") if data.get("level") in LEVELS else fallback.level
    count = max(1, min(int(data.get("count") or fallback.count), 20))
    theme = str(data.get("theme") or "").strip()[:60]
    rule_ids = [r for t in topics for r in TOPICS[t]] or fallback.rule_ids
    understood = f"{', '.join(topics) or 'Tüm konular'} · {LEVEL_TR[level]} · {count} soru" + (f" · Tema: {theme}" if theme else "")
    return Settings(rule_ids, level, count, theme, understood, True)


STORY_PROMPT = """Write a very short real-life word problem in {lang} (at most 2 sentences) for grade 7-10 students,
themed "{theme}", whose unknown quantity x satisfies exactly this equation: {equation}
Do not give the answer and do not write the equation. Only the story."""


def add_story(item: Generated, theme: str, lang: str = "Turkish") -> None:
    """Wrap an equation in a short story written by Gemma 4. The equation itself stays visible and verified."""
    if not theme or "=" not in item.question.problem:
        return
    from .vision import MODEL, VisionError, _post
    try:
        reply = _post("/api/chat", {"model": MODEL, "stream": False, "options": {"temperature": 0.7},
                                    "messages": [{"role": "user", "content": STORY_PROMPT.format(
                                        theme=theme, equation=item.question.problem, lang=lang)}]}, timeout=60)
        item.story = reply["message"]["content"].strip()[:400]
    except (VisionError, KeyError):
        pass
