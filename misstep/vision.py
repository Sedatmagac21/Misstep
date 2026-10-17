"""Read a photo of handwritten work into lines with Gemma 4, running locally in Ollama.

The model only *transcribes*. It is told never to fix the student's mistakes,
because correctness is decided by SymPy afterwards, not by the model.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("MISSTEP_MODEL", "gemma4:e4b")

PROMPT = """You are transcribing a student's handwritten algebra solution.
Write down EXACTLY what the student wrote, one line of work per entry, top to bottom.
Never correct, simplify or complete anything, even if it is mathematically wrong:
mistakes must stay exactly as written.
Use plain ASCII math: ^ for powers, * only where written, / for fractions,
parentheses as written, sqrt(...) for roots. Keep '=' signs.
Skip words and crossed-out work. For each line give your confidence from 0 to 1
that you read every symbol correctly."""

SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "confidence": {"type": "number"}},
                "required": ["text", "confidence"],
            },
        }
    },
    "required": ["lines"],
}


@dataclass
class ReadLine:
    text: str
    confidence: float


class VisionError(RuntimeError):
    pass


# Ollama runs on this computer: never send its requests through a system or environment proxy.
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LAST_ERROR = ""  # the most recent reason a model call failed, shown to the user by /api/health


def _post(path: str, payload: dict, timeout: float) -> dict:
    """POST to Ollama. Chat calls ask for no 'thinking' (Gemma 4 can think first and spend the whole token
    budget there, leaving an empty answer); if this Ollama version rejects that, the call is retried without it."""
    global LAST_ERROR
    if path == "/api/chat":
        payload = {"think": False, **payload}
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with _LOCAL.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        if "think" in detail and "think" in payload:
            return _retry(path, payload, timeout)
        LAST_ERROR = f"Ollama hata verdi ({exc.code}): {detail}"
        raise VisionError(LAST_ERROR) from exc
    except TimeoutError as exc:
        LAST_ERROR = f"Gemma {int(timeout)} saniyede cevap vermedi (model ilk kez yükleniyor olabilir, tekrar dene)."
        raise VisionError(LAST_ERROR) from exc
    except OSError as exc:
        LAST_ERROR = f"Ollama'ya ulaşılamadı ({OLLAMA_URL}). Ollama açık mı ve '{MODEL}' indirildi mi?"
        raise VisionError(LAST_ERROR) from exc
    msg = data.get("message") or {}
    if path == "/api/chat" and not str(msg.get("content", "")).strip():
        LAST_ERROR = "Gemma boş cevap döndürdü" + (" (cevabı düşünme kısmında bitirdi)." if msg.get("thinking") else ".")
    else:
        LAST_ERROR = ""
    return data


def _retry(path: str, payload: dict, timeout: float) -> dict:
    """Older Ollama without the 'think' option: send the same request without it."""
    global LAST_ERROR
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", data=json.dumps({k: v for k, v in payload.items() if k != "think"}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with _LOCAL.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except OSError as exc:
        LAST_ERROR = f"Ollama hata verdi: {exc}"
        raise VisionError(LAST_ERROR) from exc
    LAST_ERROR = ""
    return data


def parse_response(content: str) -> list[ReadLine]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VisionError("Model geçerli JSON döndürmedi.") from exc
    lines = []
    for item in data.get("lines", []):
        text = str(item.get("text", "")).strip()
        if text:
            conf = float(item.get("confidence", 0.0))
            lines.append(ReadLine(text, max(0.0, min(1.0, conf))))
    return lines


def read_image(image_bytes: bytes, timeout: float = 180) -> list[ReadLine]:
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT, "images": [base64.b64encode(image_bytes).decode()]}],
        "format": SCHEMA,
        "stream": False,
        "options": {"temperature": 0},
    }
    reply = _post("/api/chat", payload, timeout)
    return parse_response(reply.get("message", {}).get("content", ""))


def health(timeout: float = 2) -> tuple[bool, list[str]]:
    """Is Ollama running, and which models are installed?"""
    try:
        with _LOCAL.open(f"{OLLAMA_URL}/api/tags", timeout=timeout) as resp:
            return True, [m["name"] for m in json.loads(resp.read()).get("models", [])]
    except (OSError, ValueError, KeyError):
        return False, []


def diagnose() -> dict:
    """Why model features would not work right now, with the command that fixes it."""
    ok, models = health()
    base = MODEL.split(":")[0]
    if not ok:
        return {"state": "offline", "model": MODEL, "fix": "ollama serve", "installed": [], "detail": LAST_ERROR}
    if not any(m == MODEL or m.startswith(MODEL + "-") or (":" not in MODEL and m.startswith(base)) for m in models):
        return {"state": "no_model", "model": MODEL, "fix": f"ollama pull {MODEL}", "installed": models, "detail": LAST_ERROR}
    return {"state": "error" if LAST_ERROR else "ok", "model": MODEL, "fix": "", "installed": models, "detail": LAST_ERROR}
