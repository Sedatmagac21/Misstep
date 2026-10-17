"""Misstep web server: the JSON API behind the site in ``web/``.

python app.py   ->   http://localhost:7860
"""

from __future__ import annotations

import json
import random
import tempfile
from urllib.parse import quote
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response as RawResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import documents, generator, hunt as hunts, research, vision
from .accounts import AccountError, Accounts, User
from .bugs import RULES, RULES_BY_ID
from .counterexample import counterexample
from .diagnose import Report, check_solution
from .i18n import rule_text, topic_name
from .parsing import ParseError, parse_line
from .pdf_report import build_class_report, build_pdf, build_research_pdf, build_topic_report, build_worksheet
from .pipeline import analyze
from .practice import display
from .progress import DB_PATH, TOPIC_OF, TOPICS, Store, record_solution, summarize
from .rag import Chunk, chat, embed_passages, explain, load_chunks, retrieve

ROOT = Path(__file__).resolve().parent.parent
WEB, ASSETS = ROOT / "web", ROOT / "assets"
COOKIE = "ms_session"


# ---- request bodies ----
class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    role: str
    grade: int | None = None
    code: str = ""          # class code (student) or family code (parent)


class LoginIn(BaseModel):
    email: str
    password: str


class LinesIn(BaseModel):
    lines: list[str]
    explain: bool = True


class GenerateIn(BaseModel):
    topics: list[str] = []
    level: str = "medium"
    count: int = Field(5, ge=1, le=20)
    prompt: str = ""
    story: bool = False
    rules: list[str] = []      # exact misconceptions, e.g. a test built from the mistake notebook
    assignment_id: int | None = None


class AnswerIn(BaseModel):
    question_id: str
    choice: int
    explain: bool = False      # tests answer instantly; the explanation is asked for separately


class ExplainIn(BaseModel):
    question_id: str
    choice: int


class StepsIn(BaseModel):
    question_id: str
    lines: list[str]
    explain: bool = False


class ChatMsg(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    message: str
    history: list[ChatMsg] = []
    topic: str = ""


class TestIn(BaseModel):
    data: dict


class CodeIn(BaseModel):
    code: str


class NameIn(BaseModel):
    name: str


class ProfileIn(BaseModel):
    name: str | None = None
    grade: int | None = None


class AssignmentIn(BaseModel):
    class_id: int
    title: str = ""
    topics: list[str] = []
    level: str = "medium"
    count: int = Field(10, ge=1, le=20)
    due: str | None = None


class WorksheetIn(BaseModel):
    question_ids: list[str]
    title: str = "Çalışma kâğıdı"


class ContactIn(BaseModel):
    name: str
    email: str
    message: str


class ResearchIn(BaseModel):
    question: str
    topic: str = ""
    sub: str = ""
    steps: list[dict] = []


class ResearchReportIn(BaseModel):
    question: str
    summary: str = ""
    steps: list[dict] = []
    rules: list[dict] = []
    questions: list[dict] = []


class HuntIn(BaseModel):
    topics: list[str] = []
    level: str = "medium"
    weak: bool = False


class HuntAnswerIn(BaseModel):
    hunt_id: str
    line: int
    rule: str


class DemoIn(BaseModel):
    role: str = "student"


# ---- serialisation helpers ----
def lang_of(request: Request) -> str:
    return "en" if request.headers.get("x-lang", "tr").lower().startswith("en") else "tr"


def report_json(report: Report, lang: str) -> dict:
    steps = []
    for s in report.steps:
        steps.append({"index": s.index, "raw": s.raw, "status": s.status.value,
                      "pretty": display(s.raw), "note": s.note,
                      "diagnoses": [{"rule": rule_text(d.rule.id, lang), "confidence": d.confidence} for d in s.diagnoses]})
    diag = report.diagnosis
    return {"steps": steps, "first_error": report.first_error, "final_correct": report.final_correct,
            "diagnosis": {"rule": rule_text(diag.rule.id, lang), "confidence": diag.confidence} if diag else None}


def chunk_json(chunk, lang: str) -> dict:
    topic = TOPIC_OF.get(chunk.id)
    return {"id": chunk.id, "title": chunk.title, "text": chunk.text, "source": chunk.source, "doc_id": chunk.doc_id,
            "topic": topic_name(topic, lang) if topic else None, "rule": rule_text(chunk.id, lang) if chunk.id in RULES_BY_ID else None}


def pdf_response(path: Path, name: str) -> RawResponse:
    return RawResponse(path.read_bytes(), media_type="application/pdf",
                       headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})


def doc_passages(accounts: Accounts, user: User) -> list[tuple[Chunk, list | None]]:
    return [(Chunk(f"doc:{d}:{i}", title, text, "mine" if mine else "shared", d), vec)
            for d, i, title, text, vec, mine in accounts.document_chunks(user)]


def topic_rules(names: list[str]) -> list[str]:
    ids = [r for t in names if t in TOPICS for r in TOPICS[t]]
    return ids or [r.id for r in RULES]


def summary_json(store: Store, student_key: str, lang: str, today: date | None = None) -> dict:
    today = today or date.today()
    attempts = store.attempts(student_key)
    s = summarize(attempts, today)
    days = []
    for back in range(181, -1, -1):
        d = today - timedelta(days=back)
        c, w = s.by_day.get(d, (0, 0))
        days.append({"date": d.isoformat(), "correct": c, "wrong": w})
    topics = []
    for t, ids in TOPICS.items():
        rules = [{**rule_text(r, lang), "mastery": round(s.mastery[r], 3), "seen": s.seen.get(r, 0),
                  "trend": round(s.trend[r], 3)} for r in ids]
        seen = [r["mastery"] for r in rules if r["seen"]]
        topics.append({"key": t, "name": topic_name(t, lang), "mastery": round(sum(seen) / len(seen), 3) if seen else None,
                       "rules": rules})
    week = sum(c + w for d, (c, w) in s.by_day.items() if d > today - timedelta(days=7))
    prev_week = sum(c + w for d, (c, w) in s.by_day.items() if today - timedelta(days=14) < d <= today - timedelta(days=7))
    rec = s.recommendation()
    last = max((a.ts for a in attempts), default=None)
    return {"total": s.total, "correct": s.correct, "accuracy": round(s.correct / s.total, 3) if s.total else None,
            "streak": s.streak, "today": dict(zip(("correct", "wrong"), s.by_day.get(today, (0, 0)))),
            "week": week, "prev_week": prev_week, "days": days, "topics": topics,
            "weakest": [{**rule_text(r, lang), "mastery": round(s.mastery[r], 3), "topic": topic_name(TOPIC_OF[r], lang)}
                        for r in s.weakest(3)],
            "recommendation": {**rule_text(rec, lang), "topic_key": TOPIC_OF[rec], "topic": topic_name(TOPIC_OF[rec], lang)} if rec else None,
            "last_active": last.isoformat() if last else None}


def public_question(qid: str, data: dict, with_key: bool, lang: str = "tr") -> dict:
    out = {"id": qid, "instruction": data["instruction"], "problem": data["problem"], "problem_display": data["problem_display"],
           "choices": data["choices_display"], "level": data["level"], "story": data.get("story", ""),
           "topic": topic_name(data["topic"], lang), "topic_key": TOPIC_OF.get(data["rule_id"]), "rule_id": data["rule_id"],
           "is_equation": "=" in data["problem"]}
    if with_key:
        out["answer_index"] = data["choices"].index(data["answer"])
        out["traps"] = {str(data["choices"].index(c)): r for c, r in data["distractor_rules"].items() if c in data["choices"]}
    return out


def create_app(db_path: Path | str = DB_PATH) -> FastAPI:
    app = FastAPI(title="Misstep", docs_url="/api/docs", openapi_url="/api/openapi.json")
    accounts, store = Accounts(db_path), Store(db_path)

    def current(request: Request) -> User | None:
        return accounts.by_token(request.cookies.get(COOKIE))

    def need_user(request: Request) -> User:
        user = current(request)
        if user is None:
            raise HTTPException(401, "err_auth")
        return user

    def need_role(*roles: str):
        def dep(user: User = Depends(need_user)) -> User:
            if user.role not in roles:
                raise HTTPException(403, "err_forbidden")
            return user
        return dep

    def student_for(viewer: User, student_id: int | None) -> User:
        if student_id is None or student_id == viewer.id:
            if viewer.role != "student":
                raise HTTPException(400, "err_no_student")
            return viewer
        if not accounts.can_view(viewer, student_id):
            raise HTTPException(403, "err_forbidden")
        return accounts.user(student_id)

    @app.exception_handler(AccountError)
    async def _account_error(_, exc: AccountError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    def _login_response(user: User, token: str) -> Response:
        resp = JSONResponse({"user": user.public()})
        resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
        return resp

    # ---- public ----
    @app.get("/api/stats")
    def stats():
        kinds = Counter(k for (k,) in store.db.execute("SELECT kind FROM attempts"))
        users = accounts.counts()
        return {"users": sum(users.values()), "by_role": users, "solutions": kinds["solution"], "answers": kinds["practice"],
                "rules": len(RULES), "topics": len(TOPICS)}

    @app.get("/api/health")
    def health():
        d = vision.diagnose()
        return {"model_ok": d["state"] in ("ok", "error"), "model": vision.MODEL, "diagnosis": d,
                "embeddings": any(m.startswith("embeddinggemma") for m in d["installed"])}

    @app.post("/api/contact")
    def contact(body: ContactIn):
        accounts.contact(body.name, body.email, body.message)
        return {"ok": True}

    # ---- accounts ----
    @app.post("/api/register")
    def register(body: RegisterIn):
        user = accounts.register(body.name, body.email, body.password, body.role, body.grade)
        if body.code.strip():
            try:
                if user.role == "student":
                    accounts.join_class(user, body.code)
                elif user.role == "parent":
                    accounts.link_child(user, body.code)
            except AccountError:
                pass  # the account is created; the code can be entered again later
        user, token = accounts.login(body.email, body.password)
        return _login_response(user, token)

    @app.post("/api/login")
    def login(body: LoginIn):
        user, token = accounts.login(body.email, body.password)
        return _login_response(user, token)

    @app.post("/api/demo-login")
    def demo_login(body: DemoIn):
        from .demo_data import DEMO_PASSWORD, ensure_demo
        emails = ensure_demo(accounts, store)
        user, token = accounts.login(emails.get(body.role, emails["student"]), DEMO_PASSWORD)
        return _login_response(user, token)

    @app.get("/api/eval")
    def eval_results():
        """The evaluation set's numbers (eval/results.json, refreshed with python -m misstep.evaluate)."""
        from . import evaluate
        if not evaluate.RESULTS.exists():
            evaluate.RESULTS.write_text(json.dumps(evaluate.run(evaluate.load_cases()), ensure_ascii=False, indent=1), encoding="utf-8")
        data = json.loads(evaluate.RESULTS.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if k != "rows"}

    @app.post("/api/logout")
    def logout(request: Request):
        accounts.logout(request.cookies.get(COOKIE, ""))
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(COOKIE)
        return resp

    @app.get("/api/me")
    def me(request: Request):
        user = current(request)
        if user is None:
            return {"user": None}
        out = {"user": user.public()}
        if user.role == "student":
            out["classes"] = accounts.classes_of_student(user)
        elif user.role == "parent":
            out["children"] = [c.public() for c in accounts.children(user)]
        elif user.role == "teacher":
            out["classes"] = [{"id": c["id"], "name": c["name"], "code": c["code"], "size": len(c["students"])}
                              for c in accounts.classes_of_teacher(user)]
        return out

    @app.post("/api/profile")
    def profile(body: ProfileIn, user: User = Depends(need_user)):
        return {"user": accounts.update_profile(user, body.name, body.grade).public()}

    @app.post("/api/join-class")
    def join_class(body: CodeIn, user: User = Depends(need_role("student"))):
        return accounts.join_class(user, body.code)

    @app.post("/api/link-child")
    def link_child(body: CodeIn, user: User = Depends(need_role("parent"))):
        return accounts.link_child(user, body.code).public()

    # ---- checking a solution ----
    @app.post("/api/read-image")
    async def read_image(file: UploadFile = File(...), user: User = Depends(need_user)):
        try:
            lines = vision.read_image(await file.read())
        except vision.VisionError as exc:
            raise HTTPException(503, f"err_model:{exc}") from exc
        return {"lines": [{"text": line.text, "confidence": line.confidence} for line in lines]}

    @app.post("/api/check")
    def check(body: LinesIn, request: Request, user: User = Depends(need_user)):
        lang = lang_of(request)
        lines = [l.strip() for l in body.lines if l.strip()]
        if len(lines) < 2:
            raise HTTPException(400, "err_lines")
        analysis = analyze(lines, explain_with_model=body.explain, seed=random.randrange(10**6), lang=lang)
        if user.role == "student":
            record_solution(store, user.key, analysis.report, lines)
            rep = analysis.report  # history row for the analysis page; its rule id is kept out of the mastery model
            store.add(user.key, "analysis", "ANALYSIS", rep.first_error is None and rep.final_correct is not False,
                      {"lines": lines, "first_error": rep.first_error, "rule": rep.diagnosis.rule.id if rep.diagnosis else None})
        out = report_json(analysis.report, lang)
        out.update(counterexample=analysis.counterexample, explanation=analysis.explanation,
                   explained_by_model=analysis.explained_by_model, sources=[chunk_json(c, lang) for c in analysis.sources])
        diag = analysis.report.diagnosis
        if diag:
            out["practice_topic"] = TOPIC_OF[diag.rule.id]
        return out

    @app.post("/api/check-explain")
    def check_explain(body: LinesIn, request: Request, user: User = Depends(need_user)):
        """The slow part of a check (Gemma's explanation), asked for after the verdict is already on screen."""
        lang = lang_of(request)
        lines = [l.strip() for l in body.lines if l.strip()]
        if len(lines) < 2:
            raise HTTPException(400, "err_lines")
        analysis = analyze(lines, explain_with_model=True, lang=lang)
        return {"explanation": analysis.explanation, "explained_by_model": analysis.explained_by_model,
                "sources": [chunk_json(c, lang) for c in analysis.sources]}

    @app.get("/api/analyses")
    def analyses(request: Request, user: User = Depends(need_role("student"))):
        lang = lang_of(request)
        out = []
        for a in reversed(store.attempts(user.key)):
            if a.kind != "analysis":
                continue
            out.append({"ts": a.ts.isoformat(), "lines": a.detail.get("lines", []), "correct": a.correct,
                        "first_error": a.detail.get("first_error"), "problem": display((a.detail.get("lines") or [""])[0]),
                        "rule": rule_text(a.detail["rule"], lang) if a.detail.get("rule") in RULES_BY_ID else None})
            if len(out) >= 12:
                break
        return out

    @app.post("/api/report.pdf")
    def report_pdf(body: LinesIn, user: User = Depends(need_user)):
        lines = [l.strip() for l in body.lines if l.strip()]
        if len(lines) < 2:
            raise HTTPException(400, "err_lines")
        analysis = analyze(lines, explain_with_model=body.explain)
        path = Path(tempfile.mkdtemp()) / "misstep-rapor.pdf"
        build_pdf(analysis, path, student=user.name)
        return FileResponse(path, media_type="application/pdf", filename="misstep-rapor.pdf")

    # ---- practice ----
    @app.get("/api/topics")
    def topics(request: Request):
        lang = lang_of(request)
        return [{"key": t, "name": topic_name(t, lang), "rules": [rule_text(r, lang) for r in ids]} for t, ids in TOPICS.items()]

    @app.post("/api/generate")
    def generate(body: GenerateIn, request: Request, user: User = Depends(need_user)):
        lang = lang_of(request)
        seed, understood, by_model, theme = random.randrange(10**9), "", False, ""
        rule_ids, level, count = topic_rules(body.topics), body.level, body.count
        if body.rules:
            rule_ids = [r for r in body.rules if r in RULES_BY_ID] or rule_ids
        if body.assignment_id is not None:
            a = accounts.assignment(body.assignment_id)
            if a is None or not (user.role == "student" and accounts.can_do_assignment(user, a["id"])):
                raise HTTPException(403, "err_forbidden")
            rule_ids, level, count, seed = a["rule_ids"], a["level"], a["count"], a["seed"]
        elif body.prompt.strip():
            settings = generator.interpret(body.prompt, body.level, body.count)
            rule_ids, level, count = settings.rule_ids, settings.level, settings.count
            understood, by_model, theme = settings.understood, settings.by_model, settings.theme
        items = generator.generate(rule_ids, level, count, seed=seed)
        if body.story or theme:
            for item in items:
                generator.add_story(item, theme or ("günlük hayat" if lang == "tr" else "everyday life"),
                                    "English" if lang == "en" else "Turkish")
        out = []
        for item in items:
            data = item.to_dict()
            data["assignment_id"] = body.assignment_id
            qid = accounts.save_question(user, data)
            out.append(public_question(qid, data, with_key=user.role == "teacher", lang=lang))
        return {"questions": out, "understood": understood, "by_model": by_model, "level": level,
                "requested": count, "made": len(out), "rules": rule_ids}

    def _record_practice(user: User, rule_id: str, correct: bool, detail: dict) -> None:
        if user.role == "student":
            store.add(user.key, "practice", rule_id, correct, detail)

    @app.post("/api/answer")
    def answer(body: AnswerIn, request: Request, user: User = Depends(need_user)):
        lang = lang_of(request)
        q = accounts.question(user, body.question_id)
        if q is None or not 0 <= body.choice < len(q["choices"]):
            raise HTTPException(404, "err_question")
        chosen = q["choices"][body.choice]
        detail = {"problem": q["problem"], "picked": chosen, "answer": q["answer"], "assignment": q.get("assignment_id"),
                  "question_id": body.question_id, "level": q["level"]}
        right = q["choices"].index(q["answer"])
        if chosen == q["answer"]:
            _record_practice(user, q["rule_id"], True, detail)
            return {"correct": True, "answer_index": right, "answer": display(q["answer"])}
        revealed = q["distractor_rules"].get(chosen)
        _record_practice(user, revealed or "SLIP", False, detail)
        try:
            counter = counterexample(parse_line(q["problem"]), parse_line(chosen), practice=True, lang=lang)
        except (ParseError, Exception):  # noqa: BLE001 - "x = 3 veya x = -3" and friends have no single line
            counter = None
        out = {"correct": False, "answer_index": right, "answer": display(q["answer"]), "counterexample": counter,
               "rule": rule_text(revealed, lang) if revealed else None}
        if revealed and body.explain:
            rule = RULES_BY_ID[revealed]
            text, sources, by_model = explain(q["problem"], chosen, f"{rule.name}. {rule.misconception}", counter, revealed, lang=lang)
            out.update(explanation=text, explained_by_model=by_model, sources=[chunk_json(c, lang) for c in sources])
        return out

    @app.post("/api/explain-answer")
    def explain_answer(body: ExplainIn, request: Request, user: User = Depends(need_user)):
        """Gemma's explanation of one wrong pick, asked for from the test evaluation."""
        lang = lang_of(request)
        q = accounts.question(user, body.question_id)
        if q is None or not 0 <= body.choice < len(q["choices"]):
            raise HTTPException(404, "err_question")
        chosen = q["choices"][body.choice]
        revealed = q["distractor_rules"].get(chosen) or q["rule_id"]
        try:
            counter = counterexample(parse_line(q["problem"]), parse_line(chosen), practice=True, lang=lang)
        except Exception:  # noqa: BLE001
            counter = None
        rule = RULES_BY_ID[revealed]
        text, sources, by_model = explain(q["problem"], chosen, f"{rule.name}. {rule.misconception}", counter, revealed, lang=lang)
        return {"explanation": text, "explained_by_model": by_model, "counterexample": counter,
                "rule": rule_text(revealed, lang), "sources": [chunk_json(c, lang) for c in sources]}

    @app.post("/api/solve-steps")
    def solve_steps(body: StepsIn, request: Request, user: User = Depends(need_user)):
        lang = lang_of(request)
        q = accounts.question(user, body.question_id)
        if q is None:
            raise HTTPException(404, "err_question")
        lines = [q["problem"]] + [l.strip() for l in body.lines if l.strip()]
        if len(lines) < 2:
            raise HTTPException(400, "err_lines")
        analysis = analyze(lines, explain_with_model=body.explain, lang=lang)
        r = analysis.report
        ok = r.first_error is None and r.final_correct is True
        diag = r.diagnosis
        _record_practice(user, q["rule_id"] if ok else (diag.rule.id if diag else "SLIP"), ok,
                         {"problem": q["problem"], "lines": lines, "assignment": q.get("assignment_id"),
                          "question_id": body.question_id, "level": q["level"], "mode": "steps"})
        out = report_json(r, lang)
        out.update(solved=ok, answer=display(q["answer"]), answer_index=q["choices"].index(q["answer"]),
                   rule=rule_text(diag.rule.id, lang) if diag and not ok else None, counterexample=analysis.counterexample,
                   explanation=analysis.explanation, explained_by_model=analysis.explained_by_model,
                   sources=[chunk_json(c, lang) for c in analysis.sources])
        return out

    # ---- progress ----
    @app.get("/api/progress")
    def progress(request: Request, student_id: int | None = None, user: User = Depends(need_user)):
        student = student_for(user, student_id)
        return {"student": student.public(), **summary_json(store, student.key, lang_of(request))}

    @app.get("/api/mistakes")
    def mistakes(request: Request, student_id: int | None = None, user: User = Depends(need_user)):
        lang = lang_of(request)
        student = student_for(user, student_id)
        out = []
        for a in reversed(store.attempts(student.key)):
            if a.correct or a.kind not in ("solution", "practice") or a.detail.get("demo"):
                continue
            out.append({"ts": a.ts.isoformat(), "kind": a.kind, "rule": rule_text(a.rule_id, lang) if a.rule_id in RULES_BY_ID else None,
                        "topic_key": TOPIC_OF.get(a.rule_id), "problem": display(a.detail.get("problem") or (a.detail.get("lines") or [""])[0]),
                        "picked": display(a.detail["picked"]) if a.detail.get("picked") else None,
                        "answer": display(a.detail["answer"]) if a.detail.get("answer") else None,
                        "lines": a.detail.get("lines")})
            if len(out) >= 60:
                break
        return out

    # ---- learning material ----
    @app.get("/api/resources")
    def resources(request: Request, q: str = ""):
        lang = lang_of(request)
        user = current(request)
        extra = doc_passages(accounts, user) if user and user.role != "parent" else []
        chunks = retrieve(q, k=8, extra=extra) if q.strip() else list(load_chunks())
        return [chunk_json(c, lang) for c in chunks]

    @app.get("/api/documents")
    def list_documents(user: User = Depends(need_role("student", "teacher"))):
        return accounts.documents(user)

    @app.post("/api/documents")
    async def upload_document(file: UploadFile = File(...), title: str = Form(""), user: User = Depends(need_role("student", "teacher"))):
        data = await file.read()
        try:
            kind = documents.kind_of(file.filename or "")
            text = documents.extract_text(file.filename or "", data)
        except documents.DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        passages = documents.chunk_text(text)
        title = title or (file.filename or "").rsplit(".", 1)[0]
        doc = accounts.add_document(user, title, file.filename or "dosya", kind, data, text, passages,
                                    embed_passages([f"{title}\n{p}" for p in passages]))
        doc.pop("text", None)
        return doc

    @app.get("/api/documents/{doc_id}")
    def get_document(doc_id: int, user: User = Depends(need_role("student", "teacher"))):
        doc = accounts.document(user, doc_id)
        if doc is None:
            raise HTTPException(404, "err_doc")
        return doc

    @app.get("/api/documents/{doc_id}/file")
    def document_file(doc_id: int, user: User = Depends(need_role("student", "teacher"))):
        doc = accounts.document(user, doc_id, with_data=True)
        if doc is None:
            raise HTTPException(404, "err_doc")
        types = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                 "md": "text/markdown; charset=utf-8", "txt": "text/plain; charset=utf-8"}
        return RawResponse(doc["data"], media_type=types.get(doc["kind"], "application/octet-stream"),
                           headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc['filename'])}"})

    @app.delete("/api/documents/{doc_id}")
    def delete_document(doc_id: int, user: User = Depends(need_role("student", "teacher"))):
        accounts.delete_document(user, doc_id)
        return {"ok": True}

    # ---- study chat ----
    @app.post("/api/chat")
    def study_chat(body: ChatIn, request: Request, user: User = Depends(need_role("student", "teacher"))):
        lang = lang_of(request)
        if not body.message.strip():
            raise HTTPException(400, "err_empty")
        topic = topic_name(body.topic, lang) if body.topic in TOPICS else ""
        rule_hint = " ".join(RULES_BY_ID[r].name for r in TOPICS.get(body.topic, []))
        chunks = retrieve(f"{body.message} {topic} {rule_hint}", k=4, extra=doc_passages(accounts, user))
        weak = []
        if user.role == "student":
            weak = [RULES_BY_ID[r].name for r in summarize(store.attempts(user.key)).weakest(3)]
        answer, by_model = chat(body.message, [m.model_dump() for m in body.history], chunks, lang=lang, topic=topic, weak=weak)
        out = {"answer": answer, "by_model": by_model, "sources": [chunk_json(c, lang) for c in chunks]}
        if not by_model:
            out["model_issue"] = vision.diagnose()
            out["fallback"] = research.extractive(body.message, topic, chunks, n=3)  # still answer from the sources
        return out

    # ---- derin araştırma: plan -> one call per step -> summary, so the page shows real progress ----
    def _research_q(body: ResearchIn) -> str:
        q = body.question.strip()[:300]
        if not q:
            raise HTTPException(400, "err_empty")
        return q

    @app.post("/api/research/plan")
    def research_plan(body: ResearchIn, request: Request, user: User = Depends(need_role("student", "teacher"))):
        lang = lang_of(request)
        steps, by_model = research.plan(_research_q(body), topic_name(body.topic, lang) if body.topic in TOPICS else "", lang)
        return {"steps": steps, "by_model": by_model}

    @app.post("/api/research/step")
    def research_step(body: ResearchIn, request: Request, user: User = Depends(need_role("student", "teacher"))):
        lang = lang_of(request)
        q = _research_q(body)
        hint = " ".join(RULES_BY_ID[r].name for r in TOPICS.get(body.topic, []))
        chunks = retrieve(f"{body.sub} {q} {hint}", k=3, extra=doc_passages(accounts, user))
        earlier = " ".join(str(x.get("answer", "")) for x in body.steps[:4])
        answer, by_model = research.answer_step(body.sub or q, q, chunks, lang, avoid=earlier)
        return {"q": body.sub, "answer": answer, "by_model": by_model, "sources": [chunk_json(c, lang) for c in chunks]}

    @app.post("/api/research/summary")
    def research_summary(body: ResearchIn, request: Request, user: User = Depends(need_role("student", "teacher"))):
        lang = lang_of(request)
        q = _research_q(body)
        steps = [{"q": str(x.get("q", ""))[:300], "answer": str(x.get("answer", ""))[:3000]} for x in body.steps[:4]]
        summary, by_model = research.summarize(q, steps, lang)
        rules = research.related_rules(q + " " + " ".join(x["answer"] for x in steps)) or list(TOPICS.get(body.topic, []))[:2]
        items = generator.generate(rules[:2], "medium", 3, seed=random.randrange(10**9)) if rules else []
        questions = []
        for item in items:
            data = item.to_dict()
            qid = accounts.save_question(user, data)
            questions.append({**public_question(qid, data, with_key=True, lang=lang)})
        return {"summary": summary, "by_model": by_model, "rules": [rule_text(r, lang) for r in rules[:2]], "questions": questions}

    @app.post("/api/research/report.pdf")
    def research_pdf(body: ResearchReportIn, request: Request, user: User = Depends(need_role("student", "teacher"))):
        lang = lang_of(request)
        path = Path(tempfile.mkdtemp()) / "research.pdf"
        build_research_pdf(body.model_dump(), path, student=user.name, lang=lang)
        name = "misstep-arastirma-raporu.pdf" if lang == "tr" else "misstep-research-report.pdf"
        return pdf_response(path, name)

    @app.get("/api/study/{topic}/report.pdf")
    def topic_report(topic: str, request: Request, user: User = Depends(need_role("student"))):
        lang = lang_of(request)
        if topic not in TOPICS:
            raise HTTPException(404, "err_topic")
        summ = summary_json(store, user.key, lang)
        t = next(x for x in summ["topics"] if x["key"] == topic)
        mistakes = []
        for a in reversed(store.attempts(user.key)):
            if not a.correct and a.rule_id in TOPICS[topic] and not a.detail.get("demo") and (a.detail.get("problem") or a.detail.get("lines")):
                mistakes.append({"problem": display(a.detail.get("problem") or a.detail["lines"][0]), "picked": display(a.detail.get("picked") or ""),
                                 "rule": rule_text(a.rule_id, lang)["name"], "ts": a.ts.strftime("%d.%m.%Y")})
            if len(mistakes) >= 6:
                break
        notes = {c.id: c for c in load_chunks()}
        weak_first = sorted(TOPICS[topic], key=lambda r: next(x["mastery"] for x in t["rules"] if x["id"] == r))
        items = generator.generate(weak_first[:3], "medium", 6, seed=random.randrange(10**9))
        data = {"topic": t, "mistakes": mistakes, "notes": [{"title": notes[r].title, "text": notes[r].text} for r in TOPICS[topic] if r in notes],
                "questions": [i.to_dict() for i in items], "total": summ["total"], "accuracy": summ["accuracy"], "streak": summ["streak"]}
        path = Path(tempfile.mkdtemp()) / "topic.pdf"
        build_topic_report(data, path, student=user.name, lang=lang)
        return pdf_response(path, f"misstep-{topic}-{'rapor' if lang == 'tr' else 'report'}.pdf".replace(" ", "-").lower())

    @app.get("/api/study/{topic}")
    def study(topic: str, request: Request, user: User = Depends(need_user)):
        lang = lang_of(request)
        if topic not in TOPICS:
            raise HTTPException(404, "err_topic")
        notes = {c.id: c for c in load_chunks()}
        mastery = {}
        if user.role == "student":
            s = summarize(store.attempts(user.key))
            mastery = {r: (round(s.mastery[r], 3), s.seen.get(r, 0)) for r in TOPICS[topic]}
        return {"key": topic, "name": topic_name(topic, lang),
                "rules": [{**rule_text(r, lang), "note": chunk_json(notes[r], lang) if r in notes else None,
                           "mastery": mastery.get(r, (None, 0))[0], "seen": mastery.get(r, (None, 0))[1]} for r in TOPICS[topic]]}

    # ---- assignments ----
    @app.get("/api/assignments")
    def assignments(request: Request, student_id: int | None = None, user: User = Depends(need_user)):
        lang = lang_of(request)
        if user.role in ("student", "parent"):
            student = student_for(user, student_id)
            done = Counter()
            right = Counter()
            for a in store.attempts(student.key):
                if a.detail.get("assignment"):
                    done[a.detail["assignment"]] += 1
                    right[a.detail["assignment"]] += a.correct
            return [{**a, "topics": sorted({topic_name(TOPIC_OF[r], lang) for r in a["rule_ids"]}),
                     "done": min(done[a["id"]], a["count"]), "right": right[a["id"]]} for a in accounts.assignments_for_student(student)]
        out = []
        for c in accounts.classes_of_teacher(user):
            for a in accounts.assignments_for_class(c["id"]):
                progress = []
                for s in c["students"]:
                    att = [x for x in store.attempts(s.key) if x.detail.get("assignment") == a["id"]]
                    progress.append({"student": s.name, "done": min(len(att), a["count"]), "right": sum(x.correct for x in att)})
                out.append({**a, "topics": sorted({topic_name(TOPIC_OF[r], lang) for r in a["rule_ids"]}), "progress": progress})
        return out

    @app.post("/api/assignments")
    def create_assignment(body: AssignmentIn, user: User = Depends(need_role("teacher"))):
        return accounts.create_assignment(user, body.class_id, body.title, topic_rules(body.topics), body.level, body.count, body.due)

    # ---- finished tests ----
    @app.post("/api/tests")
    def save_test(body: TestIn, user: User = Depends(need_role("student"))):
        keep = {k: body.data.get(k) for k in ("total", "correct", "wrong", "blank", "seconds", "level", "topics", "adaptive", "weak")}
        return {"id": accounts.save_test(user, keep)}

    @app.get("/api/tests")
    def list_tests(student_id: int | None = None, user: User = Depends(need_user)):
        return accounts.tests(student_for(user, student_id).id)

    # ---- Hata Avı: find the injected mistake in a classmate's solution ----
    @app.post("/api/hunt/new")
    def hunt_new(body: HuntIn, request: Request, user: User = Depends(need_role("student"))):
        lang = lang_of(request)
        rule_ids = topic_rules(body.topics) if body.topics else []
        if body.weak:
            summ = summarize(store.attempts(user.key))
            rule_ids = sorted(summ.mastery, key=summ.mastery.get)[:3]
        h = hunts.make_hunt(rule_ids, body.level, seed=random.randrange(10**9))
        if h is None:
            raise HTTPException(503, "err_hunt")
        data = {"type": "hunt", **h.to_dict()}
        qid = accounts.save_question(user, data)
        return {"id": qid, "student": h.student, "level": h.level, "instruction": data["instruction"],
                "lines": data["lines_display"], "topic": topic_name(h.to_dict()["topic"], lang),
                "options": [{"id": r, **rule_text(r, lang)} for r in h.options]}

    @app.post("/api/hunt/answer")
    def hunt_answer(body: HuntAnswerIn, request: Request, user: User = Depends(need_role("student"))):
        lang = lang_of(request)
        h = accounts.question(user, body.hunt_id)
        if h is None or h.get("type") != "hunt":
            raise HTTPException(404, "err_question")
        if h.get("answered"):
            raise HTTPException(409, "err_hunt_done")
        result = hunts.score(h, body.line, body.rule)
        accounts.update_question(user, body.hunt_id, {**h, "answered": True})
        store.add(user.key, "hunt", h["rule_id"], result["line_ok"] and result["rule_ok"],
                  {"problem": h["lines"][0], "lines": h["lines"], "picked_line": body.line, "picked_rule": body.rule, "points": result["points"]})
        wrong, prev = h["lines"][h["wrong_index"]], h["lines"][h["wrong_index"] - 1]
        try:
            counter = counterexample(parse_line(prev), parse_line(wrong), lang=lang)
        except Exception:  # noqa: BLE001
            counter = None
        return {**result, "wrong_index": h["wrong_index"], "rule": rule_text(h["rule_id"], lang), "counterexample": counter}

    @app.get("/api/hunt/stats")
    def hunt_stats(user: User = Depends(need_role("student"))):
        rows = [a for a in store.attempts(user.key) if a.kind == "hunt"]
        best = run = 0
        for a in rows:
            run = run + 1 if a.correct else 0
            best = max(best, run)
        return {"played": len(rows), "solved": sum(a.correct for a in rows), "points": sum(a.detail.get("points", 0) for a in rows),
                "streak": run, "best": best}

    # ---- teacher ----
    @app.post("/api/classes")
    def create_class(body: NameIn, user: User = Depends(need_role("teacher"))):
        return accounts.create_class(user, body.name)

    def class_data(c: dict, lang: str) -> dict:
        """One class with a row per student: the teacher's sortable table and the weekly PDF both use it."""
        students, totals = [], Counter()
        mastery_sum, mastery_n = Counter(), Counter()
        homework = accounts.assignments_for_class(c["id"])
        for s in c["students"]:
            summ = summary_json(store, s.key, lang)
            attempts = store.attempts(s.key)
            topic_m = {t["key"]: t["mastery"] for t in summ["topics"]}
            for t in summ["topics"]:
                for r in t["rules"]:
                    if r["seen"]:
                        mastery_sum[r["id"]] += r["mastery"]
                        mastery_n[r["id"]] += 1
            last7 = summ["days"][-7:]
            week_c, week_n = sum(d["correct"] for d in last7), sum(d["correct"] + d["wrong"] for d in last7)
            hw_done = sum(min(sum(1 for a in attempts if a.detail.get("assignment") == h["id"]), h["count"]) for h in homework)
            weakest = summ["weakest"][0] if summ["weakest"] else None
            students.append({"id": s.id, "name": s.name, "grade": s.grade, "total": summ["total"], "correct": summ["correct"],
                             "wrong": summ["total"] - summ["correct"], "accuracy": summ["accuracy"], "streak": summ["streak"],
                             "week": summ["week"], "week_accuracy": round(week_c / week_n, 3) if week_n else None,
                             "hunts": sum(1 for a in attempts if a.kind == "hunt"),
                             "homework": round(hw_done / sum(h["count"] for h in homework), 3) if homework else None,
                             "last_active": summ["last_active"], "weakest": weakest, "topics": topic_m})
            totals["total"] += summ["total"]
            totals["correct"] += summ["correct"]
            totals["week"] += week_n
            totals["week_correct"] += week_c
        class_weak = sorted(((mastery_sum[r] / mastery_n[r], r) for r in mastery_n))[:3]
        topic_avg = []
        for t in TOPICS:
            vals = [st["topics"][t] for st in students if st["topics"].get(t) is not None]
            topic_avg.append({"key": t, "name": topic_name(t, lang), "mastery": round(sum(vals) / len(vals), 3) if vals else None})
        return {"id": c["id"], "name": c["name"], "code": c["code"], "students": students,
                "topics": [{"key": t, "name": topic_name(t, lang)} for t in TOPICS], "topic_mastery": topic_avg,
                "total": totals["total"], "accuracy": round(totals["correct"] / totals["total"], 3) if totals["total"] else None,
                "week": totals["week"], "week_accuracy": round(totals["week_correct"] / totals["week"], 3) if totals["week"] else None,
                "assignments": [{"title": h["title"], "count": h["count"], "due": h["due"],
                                 "done": sum(1 for st in c["students"] if sum(1 for a in store.attempts(st.key) if a.detail.get("assignment") == h["id"]) >= h["count"])}
                                for h in homework],
                "weak": [{**rule_text(r, lang), "mastery": round(m, 3), "students": sum(1 for st in students if st["weakest"] and st["weakest"]["id"] == r)}
                         for m, r in class_weak]}

    @app.get("/api/classes")
    def classes(request: Request, user: User = Depends(need_role("teacher"))):
        lang = lang_of(request)
        return [class_data(c, lang) for c in accounts.classes_of_teacher(user)]

    @app.get("/api/classes/{class_id}/report.pdf")
    def class_report(class_id: int, request: Request, user: User = Depends(need_role("teacher"))):
        lang = lang_of(request)
        c = next((c for c in accounts.classes_of_teacher(user) if c["id"] == class_id), None)
        if c is None:
            raise HTTPException(404, "err_forbidden")
        name = f"misstep-{c['name']}-haftalik-rapor.pdf" if lang == "tr" else f"misstep-{c['name']}-weekly-report.pdf"
        path = Path(tempfile.mkdtemp()) / "report.pdf"
        build_class_report(class_data(c, lang), path, teacher=user.name, lang=lang)
        return pdf_response(path, name)

    @app.post("/api/worksheet.pdf")
    def worksheet(body: WorksheetIn, user: User = Depends(need_role("teacher"))):
        qs = [q for qid in body.question_ids if (q := accounts.question(user, qid))]
        if not qs:
            raise HTTPException(400, "err_question")
        path = Path(tempfile.mkdtemp()) / "misstep-calisma-kagidi.pdf"
        build_worksheet(qs, path, title=body.title, subtitle=f"{user.name} · {datetime.now():%d.%m.%Y}")
        return FileResponse(path, media_type="application/pdf", filename="misstep-calisma-kagidi.pdf")

    # ---- site ----
    app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app
