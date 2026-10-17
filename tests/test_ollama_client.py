"""vision._post against a fake local Ollama: success, missing model, an Ollama that rejects 'think', offline."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from misstep import vision


class Fake(BaseHTTPRequestHandler):
    mode = "ok"
    seen: list = []

    def log_message(self, *a):
        pass

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self._send(200, {"models": [{"name": "gemma4:e4b"}] if Fake.mode != "no_model" else [{"name": "llama3:8b"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Fake.seen.append(body)
        if Fake.mode == "no_model":
            return self._send(404, {"error": "model 'gemma4:e4b' not found"})
        if Fake.mode == "old" and "think" in body:
            return self._send(400, {"error": "invalid option provided: think"})
        self._send(200, {"message": {"role": "assistant", "content": "Merhaba"}})


@pytest.fixture
def fake(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(vision, "OLLAMA_URL", f"http://127.0.0.1:{srv.server_port}")
    Fake.seen = []
    yield Fake
    srv.shutdown()


CHAT = {"model": "gemma4:e4b", "messages": [{"role": "user", "content": "selam"}], "stream": False}


def test_chat_ok_sends_think_false(fake):
    fake.mode = "ok"
    assert vision._post("/api/chat", CHAT, 5)["message"]["content"] == "Merhaba"
    assert fake.seen[0]["think"] is False and vision.LAST_ERROR == ""
    assert vision.diagnose()["state"] == "ok"


def test_old_ollama_retried_without_think(fake):
    fake.mode = "old"
    assert vision._post("/api/chat", CHAT, 5)["message"]["content"] == "Merhaba"
    assert "think" not in fake.seen[-1] and vision.LAST_ERROR == ""


def test_missing_model_is_explained(fake):
    fake.mode = "no_model"
    with pytest.raises(vision.VisionError):
        vision._post("/api/chat", CHAT, 5)
    assert "404" in vision.LAST_ERROR
    d = vision.diagnose()
    assert d["state"] == "no_model" and d["fix"] == "ollama pull gemma4:e4b"


def test_offline(monkeypatch):
    monkeypatch.setattr(vision, "OLLAMA_URL", "http://127.0.0.1:9")
    with pytest.raises(vision.VisionError):
        vision._post("/api/chat", CHAT, 2)
    assert vision.diagnose()["state"] == "offline"
