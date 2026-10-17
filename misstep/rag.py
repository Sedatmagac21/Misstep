"""Local retrieval-augmented explanations.

Knowledge lives in ``knowledge/*.md`` (one section per misconception). Retrieval
is hybrid: BM25 always, plus EmbeddingGemma vectors when Ollama has the model,
merged with reciprocal-rank fusion. Gemma 4 then explains the mistake using
the student's own line, and may only use the retrieved notes, which it cites.
If no model is running, the matching note itself is shown.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .vision import MODEL, VisionError, _post

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge"
EMBED_MODEL = "embeddinggemma"


@dataclass(frozen=True)
class Chunk:
    id: str
    title: str
    text: str
    source: str = "note"        # "note" (Misstep's own), "mine" (my upload) or "shared" (my teacher's upload)
    doc_id: int | None = None


def _tokens(text: str) -> list[str]:
    # F5 stemming: the first five letters of a Turkish word are a strong, cheap stem
    # (kesirleri / kesirlerle / kesir -> kesir), see Can et al. 2008.
    words = re.findall(r"[a-zçğıöşü0-9]+", text.replace("İ", "i").replace("I", "ı").lower())
    return [w[:5] for w in words]


@lru_cache(maxsize=1)
def load_chunks() -> tuple[Chunk, ...]:
    chunks = []
    for path in sorted(KB_DIR.glob("*.md")):
        for block in path.read_text(encoding="utf-8").split("\n## ")[1:]:
            header, _, body = block.partition("\n")
            cid, _, title = header.partition("|")
            chunks.append(Chunk(cid.strip(), title.strip(), body.strip()))
    return tuple(chunks)


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.avg = sum(map(len, docs)) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for d in self.docs:
            tf, s = Counter(d), 0.0
            for t in query:
                if t in tf:
                    s += self.idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out.append(s)
        return out


def _embed(texts: list[str]) -> list[list[float]] | None:
    try:
        return _post("/api/embed", {"model": EMBED_MODEL, "input": texts}, timeout=30)["embeddings"]
    except (VisionError, KeyError):
        return None


_VECTORS: list | None = None


def _chunk_vectors() -> list | None:
    global _VECTORS
    if _VECTORS is None:  # retried until the embedding model is available
        _VECTORS = _embed([f"{c.title}\n{c.text}" for c in load_chunks()])
    return _VECTORS


def _cos(a, b) -> float:
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1)


def embed_passages(texts: list[str]) -> list[list[float]] | None:
    """Vectors for uploaded passages, computed once at upload time (None when the model is off)."""
    return _embed(texts) if texts else None


def retrieve(query: str, rule_id: str | None = None, k: int = 2, use_embeddings: bool = True,
             extra: list[tuple[Chunk, list[float] | None]] = (), notes: bool = True) -> list[Chunk]:
    """Hybrid search over Misstep's notes plus `extra` uploaded passages (each with its stored vector)."""
    chunks = (list(load_chunks()) if notes else []) + [c for c, _ in extra]
    if not chunks:
        return []
    rankings = []
    bm = BM25([_tokens(c.title + " " + c.text) for c in chunks]).scores(_tokens(query))
    rankings.append(sorted(range(len(chunks)), key=lambda i: -bm[i]))
    note_vecs = _chunk_vectors() if use_embeddings and notes else []
    if use_embeddings and (note_vecs is not None) and (q := _embed([query])):
        vecs = list(note_vecs or []) + [v for _, v in extra]
        sims = [_cos(q[0], v) if v else -1.0 for v in vecs]
        rankings.append(sorted(range(len(chunks)), key=lambda i: -sims[i]))
    fused: Counter = Counter()
    for ranking in rankings:  # reciprocal-rank fusion
        for rank, i in enumerate(ranking):
            fused[i] += 1 / (60 + rank)
    order = [i for i, _ in fused.most_common()]
    if rule_id:  # a verified diagnosis pins its own note to the top
        order = [i for i in order if chunks[i].id == rule_id] + [i for i in order if chunks[i].id != rule_id]
    return [chunks[i] for i in order[:k]]


EXPLAIN_PROMPT = """Sen sabırlı bir matematik öğretmenisin. Bir öğrencinin cebir çözümündeki hatayı ona Türkçe olarak açıkla.

Önceki satır: {prev}
Öğrencinin yazdığı satır: {cur}
Doğrulanmış teşhis: {diagnosis}
Doğrulanmış sayısal kontrol: {counter}

Sadece aşağıdaki notları kullan. Bilgi kullandığın her cümlenin sonuna kaynağını [K1] veya [K2] şeklinde yaz.
{context}

Kurallar: En fazla 5 cümle yaz. Önce öğrencinin kendi satırında neyin değiştiğini göster, sonra doğru kuralı söyle, en son bu satırın doğru halini yaz.
Doğru hali yazarken sadece önceki satırdan tek bir doğru adım at. Notlarda olmayan bir bilgi ekleme."""


def explain(prev: str, cur: str, diagnosis: str, counter: str | None, rule_id: str | None,
            lang: str = "tr") -> tuple[str, list[Chunk], bool]:
    """Return (explanation, sources, generated_by_model)."""
    chunks = retrieve(f"{diagnosis} {prev} {cur}", rule_id=rule_id)
    context = "\n\n".join(f"[K{i}] {c.title}\n{c.text}" for i, c in enumerate(chunks, 1))
    prompt = EXPLAIN_PROMPT.format(prev=prev, cur=cur, diagnosis=diagnosis, counter=counter or "yok", context=context)
    if lang == "en":
        prompt += "\nWrite the whole explanation in English (the notes are in Turkish; translate what you use)."
    try:
        reply = _post("/api/chat", {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                                    "stream": False, "options": {"temperature": 0.2, "num_predict": 320}}, timeout=120)
        text = reply.get("message", {}).get("content", "").strip()
        if text:
            return text, chunks, True
    except VisionError:
        pass
    return chunks[0].text if chunks else "", chunks, False


CHAT_PROMPT = """Sen Misstep'in ders çalışma asistanısın: 7-10. sınıf öğrencilerine cebir anlatan sabırlı, sıcak bir öğretmen.
{topic}{weak}
Sadece aşağıdaki kaynaklara dayanarak cevap ver. Kaynaktan aldığın her bilginin sonuna [K1], [K2] gibi kaynağını yaz.
Kaynaklarda cevap yoksa bunu açıkça söyle ve öğrenciye öğretmenine sormasını ya da ilgili dosyayı Kaynaklar sayfasına yüklemesini öner.
Kısa paragraflar kullan, gerekirse küçük bir sayısal örnek ver, en fazla 8 cümle yaz. Sonunda öğrenciye kendini denemesi için tek bir kısa soru sor.

Kaynaklar:
{context}"""


def chat(message: str, history: list[dict], chunks: list[Chunk], lang: str = "tr", topic: str = "",
         weak: list[str] = ()) -> tuple[str, bool]:
    """Answer a student's question from the retrieved passages. Returns (answer, generated_by_model)."""
    context = "\n\n".join(f"[K{i}] {c.title}\n{c.text}" for i, c in enumerate(chunks, 1)) or "(kaynak bulunamadı)"
    system = CHAT_PROMPT.format(topic=f"Öğrencinin şu an çalıştığı konu: {topic}.\n" if topic else "",
                                weak=f"Öğrencinin zorlandığı yanılgılar: {', '.join(weak)}.\n" if weak else "", context=context)
    if lang == "en":
        system += "\nAnswer in English (translate what you use from the Turkish sources)."
    messages = [{"role": "system", "content": system}]
    messages += [{"role": m["role"], "content": m["content"][:2000]} for m in history[-6:] if m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": message[:2000]})
    try:
        reply = _post("/api/chat", {"model": MODEL, "messages": messages, "stream": False,
                                    "options": {"temperature": 0.3, "num_predict": 450}}, timeout=240)
        text = reply.get("message", {}).get("content", "").strip()
        if text:
            return text, True
    except VisionError:
        pass
    return "", False
