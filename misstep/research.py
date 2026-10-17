"""Derin araştırma: a multi-step, cited study report built only from the student's sources.

1. plan     Gemma splits the question into 3-4 sub-questions (a fixed plan when no model runs)
2. step     each sub-question gets its own retrieval over notes + uploaded files and a short cited answer
3. summary  the answers are merged into a summary, linked to Misstep's misconceptions, and closed with
            practice questions that SymPy has verified

Without a model every step still works: answers are the best-matching sentences of the sources (extractive),
so nothing is invented.
"""

from __future__ import annotations

import json
import re

from .bugs import RULES
from .rag import Chunk, _tokens
from .vision import MODEL, VisionError, _post

PLAN_PROMPT = """Bir öğrenci cebirle ilgili şu araştırma sorusunu sordu: "{q}"{topic}
Bu soruyu adım adım araştırmak için 3 veya 4 kısa alt soru yaz. Alt sorular birbirini tekrar etmesin; kural, sık yapılan hata,
çözülmüş örnek ve kontrol yöntemi gibi farklı yönlere baksın. Sadece JSON döndür: {{"steps": ["...", "..."]}}{lang}"""

STEP_PROMPT = """Sen bir matematik öğretmenisin. Aşağıdaki alt soruyu SADECE verilen kaynaklara dayanarak 2-4 cümleyle cevapla.
Kullandığın her bilginin sonuna [K1], [K2] gibi kaynağını yaz. Kaynaklarda cevap yoksa "Kaynaklarda bu bilgi yok." yaz.{lang}

Ana soru: {q}
Alt soru: {sub}

Kaynaklar:
{context}"""

SUMMARY_PROMPT = """Bir öğrencinin araştırma sorusu: "{q}"
Aşağıda bu soru için adım adım bulunan cevaplar var. Bunları öğrencinin anlayacağı dilde 4-6 cümlelik bir özete dönüştür.
Yeni bilgi ekleme, sadece bu cevaplardaki bilgileri kullan. En sonda öğrenciye tek cümlelik bir çalışma önerisi ver.{lang}

{answers}"""

FALLBACK_PLAN = {
    "tr": ["{q}: temel kural nedir?", "Bu konuda en sık yapılan hata nedir ve neden yanlıştır?",
           "Adım adım çözülmüş bir örnek nasıl olur?", "Kendi çözümümü nasıl kontrol edebilirim?"],
    "en": ["{q}: what is the basic rule?", "What is the most common mistake here and why is it wrong?",
           "What does a worked example look like step by step?", "How can I check my own solution?"],
}
EN = "\nWrite in English (the sources are in Turkish; translate what you use)."


def _ask(prompt: str, tokens: int, fmt: str | None = None) -> str:
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False,
               "options": {"temperature": 0.2, "num_predict": tokens}}
    if fmt:
        payload["format"] = fmt
    try:
        return _post("/api/chat", payload, timeout=150).get("message", {}).get("content", "").strip()
    except VisionError:
        return ""


def plan(question: str, topic: str = "", lang: str = "tr", use_model: bool = True) -> tuple[list[str], bool]:
    question = question.strip()[:300]
    if use_model:
        text = _ask(PLAN_PROMPT.format(q=question, topic=f"\nÇalıştığı konu: {topic}." if topic else "", lang=EN if lang == "en" else ""), 200, "json")
        try:
            steps = [s.strip() for s in json.loads(text).get("steps", []) if isinstance(s, str) and s.strip()]
        except (json.JSONDecodeError, AttributeError):
            steps = []
        if 2 <= len(steps):
            return steps[:4], True
    return [s.format(q=topic or question.rstrip("?")) for s in FALLBACK_PLAN.get(lang, FALLBACK_PLAN["tr"])], False


# question words that say nothing about the topic ("en sık yapılan hata nedir?"), as 5-letter stems
_STOP = set(_tokens("en sık yapılan yapılır hata hatalar hatası nedir neden nasıl bir bu şu ve veya ile için konu konusunda "
                    "olur olurum adım adımda kendi kendimi çözüm çözümümü kontrol edebilirim temel kural örnek "
                    "what is the how why most common mistake step check my own rule example"))


def _sentences(text: str) -> list[str]:
    """Sentences of a note or an extracted PDF: wrapped lines are joined, headings stay on their own."""
    out = []
    for block in re.split(r"\n\s*\n|\n(?=#)", text):
        block = re.sub(r"\s*\n\s*(?=[a-zçğıöşü0-9(−\-=])", " ", block.strip())  # a line that continues the sentence
        out += [x.strip(" #*-") for x in _SENT.split(block) if x.strip(" #*-")]
    return out


_CITE = re.compile(r"\s*\[K\d+\]")
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def extractive(sub: str, question: str, chunks: list[Chunk], n: int = 3, avoid: str = "") -> str:
    """The source sentences that best match the (sub-)question, each cited.

    Words are weighted by rarity across the candidate sentences (so "hata" or "sık" count less than
    "parantez"), sentences from higher-ranked sources count more, and sentences an earlier step
    already used are skipped.
    """
    import math
    want = (set(_tokens(sub)) | set(_tokens(question))) - _STOP
    used = {_CITE.sub("", x).strip(" .") for x in _SENT.split(avoid) if x.strip()}
    cands = []
    for k, c in enumerate(chunks, 1):
        for s in _sentences(c.text):
            if len(s) >= 30 and len(s.split()) >= 6 and s.rstrip(".") not in used:
                cands.append((k, s, set(_tokens(s))))
    if not cands:
        return ""
    df: dict[str, int] = {}
    for _, _, words in cands:
        for w in words:
            df[w] = df.get(w, 0) + 1
    scored = []
    for k, s, words in cands:
        weight = sum(math.log(1 + len(cands) / df[w]) for w in words & want)
        scored.append((weight / (1 + 0.15 * len(words)) / (1 + 0.35 * (k - 1)), k, s))
    best = [b for b in sorted(scored, key=lambda x: -x[0])[:n] if b[0] > 0] or sorted(scored, key=lambda x: x[1])[:1]
    best.sort(key=lambda b: (b[1], chunks[b[1] - 1].text.find(b[2])))  # keep the sources' own order: it reads better
    return " ".join(f"{s.rstrip('.')}. [K{k}]" for _, k, s in best)


def answer_step(sub: str, question: str, chunks: list[Chunk], lang: str = "tr", use_model: bool = True,
                avoid: str = "") -> tuple[str, bool]:
    if use_model and chunks:
        context = "\n\n".join(f"[K{i}] {c.title}\n{c.text[:1400]}" for i, c in enumerate(chunks, 1))
        text = _ask(STEP_PROMPT.format(q=question, sub=sub, context=context, lang=EN if lang == "en" else ""), 220)
        if text:
            return text, True
    return extractive(sub, question, chunks, avoid=avoid) if chunks else "", False


def related_rules(text: str, n: int = 2) -> list[str]:
    """Misconceptions whose description shares the most words with the research text."""
    words = set(_tokens(text))
    scored = sorted(((len(words & set(_tokens(f"{r.name} {r.misconception} {r.correct_rule}"))), r.id) for r in RULES), reverse=True)
    return [rid for s, rid in scored[:n] if s > 1]


def summarize(question: str, steps: list[dict], lang: str = "tr", use_model: bool = True) -> tuple[str, bool]:
    clean = [_CITE.sub("", s["answer"]).strip() for s in steps]
    answers = "\n\n".join(f"{i}. {s['q']}\n{a}" for i, (s, a) in enumerate(zip(steps, clean), 1))
    if use_model:
        text = _ask(SUMMARY_PROMPT.format(q=question, answers=answers, lang=EN if lang == "en" else ""), 300)
        if text:
            return text, True
    seen, out = set(), []
    for a in clean:
        for f in _SENT.split(a)[:2]:
            if f and f not in seen and len(out) < 4:
                seen.add(f)
                out.append(f.rstrip(".") + ".")
    return " ".join(out), False
