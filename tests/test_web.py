import pytest
from fastapi.testclient import TestClient

from misstep.server import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app(tmp_path / "db.sqlite")


def client(app):
    return TestClient(app)


def register(c, role, email, **extra):
    r = c.post("/api/register", json={"name": f"{role} kişi", "email": email, "password": "secret1", "role": role, **extra})
    assert r.status_code == 200, r.text
    return r.json()["user"]


def test_pages_and_public_api(app):
    c = client(app)
    assert "app.js" in c.get("/").text
    assert c.get("/js/app.js").status_code == 200
    s = c.get("/api/stats").json()
    assert s["rules"] == 13 and s["users"] == 0
    assert c.post("/api/contact", json={"name": "A", "email": "a@b.co", "message": "Merhaba Misstep"}).json()["ok"]
    assert c.get("/api/progress").status_code == 401


def test_accounts_and_errors(app):
    c = client(app)
    register(c, "student", "s@x.com")
    r = c.post("/api/register", json={"name": "Again", "email": "s@x.com", "password": "secret1", "role": "student"})
    assert r.status_code == 400 and r.json()["detail"] == "err_email_taken"
    assert c.post("/api/login", json={"email": "s@x.com", "password": "nope"}).json()["detail"] == "err_login"
    assert c.post("/api/login", json={"email": "S@X.com", "password": "secret1"}).status_code == 200
    assert c.get("/api/me").json()["user"]["role"] == "student"


def test_student_flow_check_generate_answer_progress(app):
    c = client(app)
    register(c, "student", "s@x.com", grade=8)
    r = c.post("/api/check", json={"lines": ["3x - (x + 3) = 7", "3x - x + 3 = 7", "2x = 4", "x = 2"], "explain": False}).json()
    assert r["first_error"] == 1 and r["diagnosis"]["rule"]["id"] == "SIGN_DISTRIBUTION"
    assert r["practice_topic"] == "Parantez ve dağılma"

    g = c.post("/api/generate", json={"topics": ["Kesirli ifadeler"], "level": "hard", "count": 3}).json()
    assert g["made"] == 3 and all("answer_index" not in q for q in g["questions"])  # the key stays on the server
    q = g["questions"][0]
    first = c.post("/api/answer", json={"question_id": q["id"], "choice": 0, "explain": False}).json()
    right = first["answer_index"]
    wrong = next(k for k in range(4) if k != right)
    w = c.post("/api/answer", json={"question_id": q["id"], "choice": wrong, "explain": False}).json()
    assert w["correct"] is False and w["answer_index"] == right

    steps = c.post("/api/solve-steps", json={"question_id": g["questions"][1]["id"], "lines": ["x = 0"]}).json()
    assert "steps" in steps and steps["solved"] in (True, False)

    p = c.get("/api/progress").json()
    assert p["total"] == 4 and len(p["days"]) == 182
    assert c.get("/api/mistakes").json()
    assert c.post("/api/report.pdf", json={"lines": ["2(x + 3) = 10", "2x + 3 = 10"], "explain": False}).content[:4] == b"%PDF"


def test_teacher_parent_permissions_and_homework(app):
    teacher, student, parent, other = (TestClient(app) for _ in range(4))
    register(teacher, "teacher", "t@x.com")
    s = register(student, "student", "s@x.com")
    register(parent, "parent", "p@x.com")
    register(other, "parent", "o@x.com")

    klass = teacher.post("/api/classes", json={"name": "8-A"}).json()
    assert student.post("/api/join-class", json={"code": klass["code"].lower()}).json()["name"] == "8-A"
    assert student.post("/api/classes", json={"name": "hack"}).status_code == 403

    a = teacher.post("/api/assignments", json={"class_id": klass["id"], "title": "Kesir", "topics": ["Kesirli ifadeler"], "level": "easy", "count": 2}).json()
    g = student.post("/api/generate", json={"assignment_id": a["id"]}).json()
    assert g["made"] == 2
    student.post("/api/answer", json={"question_id": g["questions"][0]["id"], "choice": 0, "explain": False})
    mine = student.get("/api/assignments").json()
    assert mine[0]["done"] == 1
    assert teacher.get("/api/assignments").json()[0]["progress"][0]["done"] == 1
    assert other.post("/api/generate", json={"assignment_id": a["id"]}).status_code == 403

    cls = teacher.get("/api/classes").json()
    assert cls[0]["students"][0]["name"] == "student kişi"
    assert teacher.get(f"/api/progress?student_id={s['id']}").status_code == 200
    assert other.get(f"/api/progress?student_id={s['id']}").status_code == 403

    fam = student.get("/api/me").json()["user"]["family_code"]
    assert parent.post("/api/link-child", json={"code": fam}).json()["id"] == s["id"]
    assert parent.get(f"/api/progress?student_id={s['id']}").json()["total"] == 1

    tg = teacher.post("/api/generate", json={"topics": [], "level": "medium", "count": 2}).json()
    assert "answer_index" in tg["questions"][0]
    pdf = teacher.post("/api/worksheet.pdf", json={"question_ids": [q["id"] for q in tg["questions"]]})
    assert pdf.content[:4] == b"%PDF"
    assert student.post("/api/worksheet.pdf", json={"question_ids": []}).status_code == 403


def test_demo_login_creates_a_full_class_once(app):
    c = TestClient(app)
    me = c.post("/api/demo-login", json={"role": "teacher"}).json()["user"]
    assert me["role"] == "teacher"
    cls = c.get("/api/classes").json()
    assert len(cls) == 1 and len(cls[0]["students"]) == 5 and cls[0]["total"] > 100
    assert TestClient(app).post("/api/demo-login", json={"role": "parent"}).status_code == 200
    assert c.get("/api/stats").json()["users"] == 10
    parent = TestClient(app)
    parent.post("/api/demo-login", json={"role": "parent"})
    kids = parent.get("/api/me").json()["children"]
    assert len(kids) == 4  # a parent follows more than one child
    homework = parent.get(f"/api/assignments?student_id={kids[0]['id']}").json()
    assert homework and homework[0]["title"]
    assert parent.get(f"/api/tests?student_id={kids[0]['id']}").json()
    assert parent.get("/api/documents").status_code == 403


def test_resources_search_finds_the_right_note(app):
    c = TestClient(app)
    hits = c.get("/api/resources?q=kesirleri toplarken payda").json()
    assert hits[0]["id"] == "ADD_FRACTIONS"
    assert len(c.get("/api/resources").json()) >= 13


def test_uploads_feed_search_and_reach_the_class(app, tmp_path):
    import io
    import zipfile
    teacher, student, outsider = (TestClient(app) for _ in range(3))
    register(teacher, "teacher", "t@x.com")
    register(student, "student", "s@x.com")
    register(outsider, "student", "o@x.com")
    klass = teacher.post("/api/classes", json={"name": "8-A"}).json()
    student.post("/api/join-class", json={"code": klass["code"]})

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                   '<w:p><w:r><w:t>Zürafa yöntemi: denklemin iki tarafına aynı sayıyı ekleriz.</w:t></w:r></w:p>'
                   '<w:p><w:r><w:t>Bu nota zürafa diyoruz çünkü uzun boyunlu bir kuraldır.</w:t></w:r></w:p></w:body></w:document>')
    r = teacher.post("/api/documents", files={"file": ("ders.docx", buf.getvalue())}, data={"title": "Zürafa notu"})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["kind"] == "docx" and doc["passages"] >= 1

    mine = student.post("/api/documents", files={"file": ("notlarim.md", "# Benim notum\nKesirleri toplarken paydaları eşitle, sonra payları topla.".encode())}).json()
    assert [d["title"] for d in student.get("/api/documents").json()] == ["notlarim", "Zürafa notu"]
    assert outsider.get("/api/documents").json() == []
    assert outsider.get(f"/api/documents/{doc['id']}").status_code == 404

    hits = student.get("/api/resources?q=zürafa yöntemi").json()
    assert hits[0]["source"] == "shared" and hits[0]["doc_id"] == doc["id"]
    assert student.get(f"/api/documents/{mine['id']}/file").content.startswith(b"# Benim")
    assert student.delete(f"/api/documents/{doc['id']}").status_code == 400  # only the owner deletes
    assert student.post("/api/documents", files={"file": ("virus.exe", b"MZ....")}).json()["detail"] == "err_doc_type"

    chat = student.post("/api/chat", json={"message": "zürafa yöntemi nedir?", "topic": "Denklem çözme"}).json()
    assert any(s["doc_id"] == doc["id"] for s in chat["sources"])  # retrieval works even with the model off


def test_fast_answers_explanations_and_saved_tests(app):
    c = TestClient(app)
    register(c, "student", "s@x.com")
    g = c.post("/api/generate", json={"rules": ["ADD_FRACTIONS"], "level": "easy", "count": 2}).json()
    assert {q["rule_id"] for q in g["questions"]} == {"ADD_FRACTIONS"}
    q = g["questions"][0]
    right = c.post("/api/answer", json={"question_id": q["id"], "choice": 0}).json()["answer_index"]
    wrong = next(k for k in range(4) if k != right)
    e = c.post("/api/explain-answer", json={"question_id": q["id"], "choice": wrong}).json()
    assert e["rule"]["id"] and e["explanation"]
    assert c.post("/api/tests", json={"data": {"total": 2, "correct": 1, "wrong": 1, "blank": 0, "seconds": 40}}).json()["id"]
    assert c.get("/api/tests").json()[0]["correct"] == 1

    c.post("/api/check", json={"lines": ["2(x + 4) = 18", "2x + 4 = 18"], "explain": False})
    h = c.get("/api/analyses").json()
    assert h[0]["first_error"] == 1 and h[0]["rule"]["id"] == "PARTIAL_DISTRIBUTION"
    assert c.post("/api/check-explain", json={"lines": ["2(x + 4) = 18", "2x + 4 = 18"]}).json()["explanation"]
    assert c.get("/api/progress").json()["total"] == 2  # history rows do not count twice


def test_parallel_requests_share_the_database_safely(app):
    from concurrent.futures import ThreadPoolExecutor
    c = TestClient(app)
    c.post("/api/demo-login", json={"role": "parent"})
    kids = c.get("/api/me").json()["children"]
    urls = [f"/api/{p}?student_id={k['id']}" for k in kids for p in ("progress", "assignments", "tests")] * 4
    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(lambda u: c.get(u).status_code, urls))
    assert set(codes) == {200}


def test_class_table_and_weekly_report(app):
    c = TestClient(app)
    c.post("/api/demo-login", json={"role": "teacher"})
    cls = c.get("/api/classes").json()[0]
    row = cls["students"][0]
    assert row["wrong"] == row["total"] - row["correct"] and "week_accuracy" in row and "homework" in row
    assert cls["topic_mastery"] and cls["assignments"]
    pdf = c.get(f"/api/classes/{cls['id']}/report.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    student = TestClient(app)
    student.post("/api/demo-login", json={"role": "student"})
    assert student.get(f"/api/classes/{cls['id']}/report.pdf").status_code == 403
    docs = student.get("/api/documents").json()
    assert sum(d["kind"] == "pdf" for d in docs) >= 3  # the sample PDFs the demo teacher shares


def test_mistake_hunt_is_verified_and_scored(app):
    from misstep.diagnose import check_solution
    from misstep.hunt import make_hunt

    for seed in range(3):
        h = make_hunt(["SIGN_DISTRIBUTION", "MOVE_WITHOUT_SIGN_CHANGE"], "medium", seed=seed)
        report = check_solution(h.lines)
        assert report.first_error == h.wrong_index and report.diagnosis.rule.id == h.rule_id
        assert h.rule_id in h.options and len(set(h.options)) == 3
    c = TestClient(app)
    register(c, "student", "s@x.com")
    p = c.post("/api/hunt/new", json={"level": "easy"}).json()
    assert len(p["lines"]) >= 3 and len(p["options"]) == 3
    r = c.post("/api/hunt/answer", json={"hunt_id": p["id"], "line": 0, "rule": p["options"][0]["id"]}).json()
    assert r["line_ok"] is False and r["points"] == 0 and r["wrong_index"] >= 1
    assert c.post("/api/hunt/answer", json={"hunt_id": p["id"], "line": 1, "rule": "X"}).status_code == 409
    stats = c.get("/api/hunt/stats").json()
    assert stats["played"] == 1 and stats["points"] == 0
    assert c.get("/api/progress").json()["total"] == 1  # a hunt counts as a question


def test_research_steps_and_reports_work_offline(app):
    c = TestClient(app)
    register(c, "student", "s@x.com")
    q = "Parantezin önündeki eksi işaret neden hepsini değiştirir?"
    plan = c.post("/api/research/plan", json={"question": q, "topic": "Parantez ve dağılma"}).json()
    assert 3 <= len(plan["steps"]) <= 4
    steps = [c.post("/api/research/step", json={"question": q, "topic": "Parantez ve dağılma", "sub": s}).json() for s in plan["steps"][:2]]
    assert all(s["answer"] and s["sources"] and "[K" in s["answer"] for s in steps)
    summ = c.post("/api/research/summary", json={"question": q, "topic": "Parantez ve dağılma",
                                                 "steps": [{"q": s["q"], "answer": s["answer"]} for s in steps]}).json()
    assert summ["summary"] and summ["questions"]
    pdf = c.post("/api/research/report.pdf", json={"question": q, **summ, "steps": steps})
    assert pdf.content.startswith(b"%PDF")
    topic = c.get("/api/study/Kesirli ifadeler/report.pdf")
    assert topic.status_code == 200 and topic.content.startswith(b"%PDF")
    assert c.post("/api/research/plan", json={"question": " "}).status_code == 400


def test_evaluation_set_runs_and_is_honest():
    from misstep.evaluate import load_cases, run

    cases = load_cases()
    assert len(cases) >= 40 and len({c["rule"] for c in cases if c["rule"]}) == 13
    res = run([c for c in cases if c["id"].startswith(("ok-", "sign-", "slip-"))])
    assert res["false_alarm_rate"] == 0 and res["step_accuracy"] == 1
