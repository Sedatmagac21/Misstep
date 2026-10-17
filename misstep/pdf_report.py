"""Teacher report as a printable PDF (one page per analysed sheet)."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .bugs import RULES
from .diagnose import Status
from .pipeline import Analysis
from .practice import display

RULE_NAMES = {r.id: r.name for r in RULES}
ASSETS = Path(__file__).resolve().parent.parent / "assets"
_FONTS_READY = False


def _fonts() -> None:
    global _FONTS_READY
    if not _FONTS_READY:
        pdfmetrics.registerFont(TTFont("Sans", ASSETS / "fonts/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("Sans-Bold", ASSETS / "fonts/DejaVuSans-Bold.ttf"))
        pdfmetrics.registerFont(TTFont("Mono", ASSETS / "fonts/DejaVuSansMono.ttf"))
        registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")
        _FONTS_READY = True


NAVY, RED, AMBER, GREEN, GREY = (colors.HexColor(c) for c in ("#14213D", "#C62828", "#9A6700", "#1E7B3A", "#5C6B80"))
LABEL = {Status.GIVEN: ("Soru", NAVY), Status.OK: ("Doğru", GREEN), Status.ERROR: ("HATA", RED),
         Status.CONSISTENT: ("Hatanın üzerine kurulu", AMBER), Status.UNREADABLE: ("Okunamadı", GREY)}


def _md(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text).replace("\n", "<br/>")


def build_pdf(analysis: Analysis, path: str | Path, student: str = "") -> Path:
    _fonts()
    body = ParagraphStyle("b", fontName="Sans", fontSize=10, leading=14)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, textColor=GREY, leading=11)
    h2 = ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=13, textColor=NAVY, spaceBefore=8, spaceAfter=4)
    mono = ParagraphStyle("m", parent=body, fontName="Mono", fontSize=11)
    story = [Image(str(ASSETS / "wordmark.png"), width=90 * mm, height=22.5 * mm, hAlign="LEFT"), Spacer(1, 4)]
    r = analysis.report
    head = "Çözüm doğru." if r.first_error is None else f"İlk hata {r.first_error}. adımda."
    story.append(Paragraph(f"<b>Öğretmen raporu</b>{' · ' + _md(student) if student else ''} · {head}", body))

    story.append(Paragraph("Adım adım kontrol", h2))
    rows = [[Paragraph(f"<b>{s.index}</b>", body), Paragraph(_md(s.raw), mono),
             Paragraph(f'<font color="{LABEL[s.status][1].hexval()}"><b>{LABEL[s.status][0]}</b></font>', body)] for s in r.steps]
    table = Table(rows, colWidths=[10 * mm, 110 * mm, 50 * mm])
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E1E5EE")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if r.first_error is not None:
        style.append(("BACKGROUND", (0, r.first_error), (-1, r.first_error), colors.HexColor("#FDECEC")))
    table.setStyle(TableStyle(style))
    story.append(table)

    if r.diagnosis:
        rule = r.diagnosis.rule
        story += [Paragraph(f"Teşhis: {_md(rule.name)} ({r.diagnosis.confidence})", h2),
                  Paragraph(f"<b>Kavram yanılgısı:</b> {_md(rule.misconception)}", body),
                  Paragraph(f"<b>Doğru kural:</b> {_md(rule.correct_rule)}", body)]
    if analysis.counterexample:
        story.append(Paragraph(f"<b>Sayısal kontrol:</b> {_md(analysis.counterexample)}", body))
    if analysis.explanation:
        story += [Paragraph("Öğrenciye açıklama", h2), Paragraph(_md(analysis.explanation), body)]
        if analysis.sources:
            src = "; ".join(f"[K{i}] {c.title}" for i, c in enumerate(analysis.sources, 1))
            who = "Gemma 4 (local) tarafından konu notlarına dayanarak yazıldı" if analysis.explained_by_model else "Konu notu"
            story.append(Paragraph(f"{who}. Kaynaklar: {_md(src)}", small))
    if analysis.questions:
        story.append(Paragraph("Hedefli alıştırma", h2))
        for i, q in enumerate(analysis.questions, 1):
            opts = "   ".join(f"{'ABCD'[j]}) {_md(display(c))}" for j, c in enumerate(q.choices))
            story += [Paragraph(f"<b>{i}.</b> {_md(q.instruction)} <font name='Mono'>{_md(display(q.problem))}</font>", body),
                      Paragraph(opts, mono), Spacer(1, 4)]
        key = "  ·  ".join(
            f"{i}. {'ABCD'[q.choices.index(q.answer)]} (yanılgı: {', '.join('ABCD'[q.choices.index(w)] for w in q.misconception_answers if w in q.choices)})"
            for i, q in enumerate(analysis.questions, 1))
        story.append(Paragraph(f"<b>Cevap anahtarı:</b> {key}. Cevapların hepsi SymPy ile doğrulandı.", small))
    story += [Spacer(1, 10), Paragraph("Misstep · Tüm analiz bu bilgisayarda yapıldı, hiçbir veri dışarı gönderilmedi.", small)]
    path = Path(path)
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm).build(story)
    return path


def build_worksheet(questions: list[dict], path: str | Path, title: str = "Çalışma kâğıdı", subtitle: str = "") -> Path:
    """Printable worksheet of generated questions with an answer key that names the misconception behind each wrong choice."""
    _fonts()
    body = ParagraphStyle("b", fontName="Sans", fontSize=10.5, leading=15)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, textColor=GREY, leading=11)
    h2 = ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=13, textColor=NAVY, spaceBefore=8, spaceAfter=4)
    mono = ParagraphStyle("m", parent=body, fontName="Mono", fontSize=11)
    story = [Image(str(ASSETS / "wordmark.png"), width=70 * mm, height=17.5 * mm, hAlign="LEFT"), Spacer(1, 4),
             Paragraph(f"<b>{_md(title)}</b>" + (f" · {_md(subtitle)}" if subtitle else ""), body),
             Paragraph("Ad Soyad: ______________________   Tarih: ____________", body), Spacer(1, 6)]
    for i, q in enumerate(questions, 1):
        story.append(Paragraph(f"<b>{i}.</b> {_md(q['instruction'])}", body))
        if q.get("story"):
            story.append(Paragraph(_md(q["story"]), body))
        story.append(Paragraph(_md(display(q["problem"])), mono))
        story.append(Paragraph("   ".join(f"{'ABCD'[j]}) {_md(display(c))}" for j, c in enumerate(q["choices"])), mono))
        story.append(Spacer(1, 10))
    story.append(Paragraph("Cevap anahtarı (öğretmen için)", h2))
    for i, q in enumerate(questions, 1):
        right = "ABCD"[q["choices"].index(q["answer"])]
        traps = ", ".join(f"{'ABCD'[q['choices'].index(c)]} → {_md(RULE_NAMES.get(r, r))}"
                          for c, r in q.get("distractor_rules", {}).items() if c in q["choices"])
        story.append(Paragraph(f"<b>{i}. {right}</b>" + (f" · Yanlış şıklar: {traps}" if traps else ""), small))
    story += [Spacer(1, 8), Paragraph("Misstep · Her soru ve cevap SymPy ile doğrulandı.", small)]
    path = Path(path)
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm).build(story)
    return path


_CLASS_L = {
    "tr": {"title": "Haftalık sınıf raporu", "students": "Öğrenci", "week_q": "Bu hafta soru", "week_acc": "Bu hafta başarı",
           "total": "Toplam soru", "acc": "Genel başarı", "kpis": "Özet", "table": "Öğrenciler", "name": "Ad",
           "correct": "Doğru", "wrong": "Yanlış", "streak": "Seri", "hw": "Ödev", "weakest": "En zayıf yanılgı",
           "topics": "Konulara göre sınıf ustalığı", "common": "Sınıfta en sık görülen yanılgılar", "n_students": "{n} öğrencide en zayıf",
           "homework": "Ödevler", "cols": ["Ad", "Hafta", "Hafta %", "Toplam", "Doğru", "Yanlış", "Genel %", "Seri", "Ödev", "En zayıf yanılgı"], "hw_done": "{d}/{n} öğrenci bitirdi", "due": "son tarih", "attention": "Bu hafta ilgi bekleyenler",
           "inactive": "Bu hafta hiç çalışmadı", "low": "Başarısı %50'nin altında", "none": "Herkes yolunda görünüyor.",
           "foot": "Misstep · Ustalık değerleri Bayesçi bilgi izleme (BKT) ile hesaplanır; tüm veriler bu bilgisayarda kalır.", "no_data": "–"},
    "en": {"title": "Weekly class report", "students": "Students", "week_q": "Questions this week", "week_acc": "Accuracy this week",
           "total": "Total questions", "acc": "Overall accuracy", "kpis": "Summary", "table": "Students", "name": "Name",
           "correct": "Correct", "wrong": "Wrong", "streak": "Streak", "hw": "Homework", "weakest": "Weakest misconception",
           "topics": "Class mastery by topic", "common": "Most common misconceptions in the class", "n_students": "weakest for {n} students",
           "homework": "Homework", "cols": ["Name", "Week", "Week %", "Total", "Right", "Wrong", "Overall", "Streak", "Homework", "Weakest misconception"], "hw_done": "{d}/{n} students finished", "due": "due", "attention": "Needs attention this week",
           "inactive": "Did not study this week", "low": "Accuracy below 50%", "none": "Everyone looks on track.",
           "foot": "Misstep · Mastery is estimated with Bayesian Knowledge Tracing (BKT); all data stays on this computer.", "no_data": "–"},
}


def _pct(x) -> str:
    return "–" if x is None else f"%{round(x * 100)}"  # Turkish style; the English report reads it fine as a percentage


def _bar_chart(items: list[tuple[str, float | None]], width: float, label_w: float = 62 * mm):
    """Horizontal mastery bars drawn with reportlab graphics (no matplotlib needed)."""
    from reportlab.graphics.shapes import Drawing, Rect, String
    row = 7 * mm
    d = Drawing(width, row * len(items))
    track = width - label_w - 14 * mm
    for i, (name, m) in enumerate(items):
        y = (len(items) - 1 - i) * row + 1.5 * mm
        d.add(String(0, y + 1, name if len(name) <= 44 else name[:42] + "…", fontName="Sans", fontSize=8.5, fillColor=NAVY))
        d.add(Rect(label_w, y, track, 3.6 * mm, rx=4, ry=4, fillColor=colors.HexColor("#EEF1F6"), strokeColor=None))
        if m is not None:
            col = GREEN if m >= 0.8 else AMBER if m >= 0.5 else RED
            d.add(Rect(label_w, y, max(2, track * m), 3.6 * mm, rx=4, ry=4, fillColor=col, strokeColor=None))
        d.add(String(label_w + track + 2 * mm, y + 1, _pct(m), fontName="Sans-Bold", fontSize=8.5, fillColor=NAVY))
    return d


def build_class_report(cls: dict, path: str | Path, teacher: str = "", lang: str = "tr") -> Path:
    """One-page weekly class report: KPIs, a row per student, topic mastery, common misconceptions, homework."""
    from datetime import date, timedelta
    _fonts()
    L = _CLASS_L.get(lang, _CLASS_L["tr"])
    body = ParagraphStyle("b", fontName="Sans", fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=GREY, leading=10)
    cell = ParagraphStyle("c", parent=body, fontSize=8.5, leading=11)
    h2 = ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=12, textColor=NAVY, spaceBefore=10, spaceAfter=5)
    today = date.today()
    period = f"{today - timedelta(days=6):%d.%m.%Y} – {today:%d.%m.%Y}"
    story = [Image(str(ASSETS / "wordmark.png"), width=62 * mm, height=15.5 * mm, hAlign="LEFT"), Spacer(1, 2),
             Paragraph(f"<b>{L['title']} · {_md(cls['name'])}</b>", ParagraphStyle("t", parent=body, fontSize=14, leading=18, textColor=NAVY)),
             Paragraph(f"{period}" + (f" · {_md(teacher)}" if teacher else ""), small), Spacer(1, 6)]

    kpi = [(L["students"], str(len(cls["students"]))), (L["week_q"], str(cls["week"])), (L["week_acc"], _pct(cls["week_accuracy"])),
           (L["total"], str(cls["total"])), (L["acc"], _pct(cls["accuracy"]))]
    big = ParagraphStyle("k", parent=body, fontName="Sans-Bold", fontSize=15, leading=18, textColor=NAVY)
    kt = Table([[Paragraph(v, big) for _, v in kpi], [Paragraph(k, small) for k, _ in kpi]], colWidths=[34.8 * mm] * 5)
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FB")), ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#E1E5EE")),
                            ("LINEAFTER", (0, 0), (-2, -1), 0.4, colors.HexColor("#E1E5EE")), ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, 1), (-1, 1), 7)]))
    story.append(kt)

    story.append(Paragraph(L["table"], h2))
    head = L["cols"]
    hcell = ParagraphStyle("hc", parent=cell, fontSize=7.5, leading=9)
    rows = [[Paragraph(f"<b>{h}</b>", hcell) for h in head]]
    students = sorted(cls["students"], key=lambda s: (s["week_accuracy"] is None, s["week_accuracy"] or 0))
    for s in students:
        rows.append([Paragraph(f"<b>{_md(s['name'])}</b>", cell), str(s["week"]), _pct(s["week_accuracy"]), str(s["total"]), str(s["correct"]),
                     str(s["wrong"]), _pct(s["accuracy"]), str(s["streak"]), _pct(s["homework"]),
                     Paragraph(_md(s["weakest"]["name"]) if s["weakest"] else "–", cell)])
    t = Table(rows, colWidths=[28 * mm, 13 * mm, 15 * mm, 15 * mm, 14 * mm, 15 * mm, 15 * mm, 11 * mm, 13 * mm, 35 * mm], repeatRows=1)
    style = [("FONTNAME", (0, 0), (-1, -1), "Sans"), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1F6")), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E1E5EE")),
             ("ALIGN", (1, 1), (-2, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i, s in enumerate(students, 1):
        if s["week_accuracy"] is not None and s["week_accuracy"] < 0.5:
            style.append(("TEXTCOLOR", (2, i), (2, i), RED))
    t.setStyle(TableStyle(style))
    story.append(t)

    story.append(Paragraph(L["topics"], h2))
    story.append(_bar_chart([(x["name"], x["mastery"]) for x in cls["topic_mastery"]], 174 * mm))

    story.append(Paragraph(L["common"], h2))
    for w in cls["weak"]:
        story.append(Paragraph(f"<b>{_md(w['name'])}</b> · {_pct(w['mastery'])}" + (f" · {L['n_students'].format(n=w['students'])}" if w["students"] else "")
                               + f"<br/><font color='{GREY.hexval()}'>{_md(w['misconception'])}</font>", body))
        story.append(Spacer(1, 3))

    inactive = [s["name"] for s in cls["students"] if not s["week"]]
    low = [s["name"] for s in cls["students"] if s["week_accuracy"] is not None and s["week_accuracy"] < 0.5]
    story.append(Paragraph(L["attention"], h2))
    if inactive or low:
        if inactive:
            story.append(Paragraph(f"<b>{L['inactive']}:</b> {_md(', '.join(inactive))}", body))
        if low:
            story.append(Paragraph(f"<b>{L['low']}:</b> {_md(', '.join(low))}", body))
    else:
        story.append(Paragraph(L["none"], body))

    if cls["assignments"]:
        story.append(Paragraph(L["homework"], h2))
        for a in cls["assignments"]:
            story.append(Paragraph(f"<b>{_md(a['title'])}</b> · {L['hw_done'].format(d=a['done'], n=len(cls['students']))}"
                                   + (f" · {L['due']} {a['due']}" if a.get("due") else ""), body))
    story += [Spacer(1, 10), Paragraph(L["foot"], small)]
    path = Path(path)
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                      title=f"{L['title']} · {cls['name']}").build(story)
    return path


def _styles():
    _fonts()
    body = ParagraphStyle("b", fontName="Sans", fontSize=10, leading=14, spaceAfter=3)
    return {"body": body, "small": ParagraphStyle("s", parent=body, fontSize=8.5, textColor=GREY, leading=11),
            "h1": ParagraphStyle("h1", parent=body, fontName="Sans-Bold", fontSize=16, leading=20, textColor=NAVY),
            "h2": ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=12.5, textColor=NAVY, spaceBefore=10, spaceAfter=4),
            "mono": ParagraphStyle("m", parent=body, fontName="Mono", fontSize=10.5)}


def _cites(text: str) -> str:
    return re.sub(r"\[K(\d+)\]", r"<font color='#C62828'><b>[K\1]</b></font>", _md(text))


def _question_block(story, questions: list[dict], st: dict, key_title: str) -> None:
    for i, q in enumerate(questions, 1):
        choices = q.get("choices_display") or q.get("choices", [])
        story += [Paragraph(f"<b>{i}.</b> {_md(q['instruction'])} <font name='Mono'>{_md(q.get('problem_display') or display(q['problem']))}</font>", st["body"]),
                  Paragraph("   ".join(f"{'ABCD'[j]}) {_md(c)}" for j, c in enumerate(choices)), st["mono"]), Spacer(1, 4)]
    keys = []
    for i, q in enumerate(questions, 1):
        idx = q["answer_index"] if "answer_index" in q else q["choices"].index(q["answer"])
        keys.append(f"{i}. {'ABCD'[idx]}")
    story.append(Paragraph(f"<b>{key_title}:</b> " + "  ·  ".join(keys), st["small"]))


def build_research_pdf(data: dict, path: str | Path, student: str = "", lang: str = "tr") -> Path:
    """The derin araştırma result as a report: question, summary, each cited step, related misconceptions, practice."""
    from datetime import date
    en = lang == "en"
    st = _styles()
    story = [Image(str(ASSETS / "wordmark.png"), width=56 * mm, height=14 * mm, hAlign="LEFT"), Spacer(1, 4),
             Paragraph("Research report" if en else "Araştırma raporu", st["small"]), Paragraph(_md(data["question"]), st["h1"]),
             Paragraph(f"{_md(student)} · {date.today():%d.%m.%Y}", st["small"]), Spacer(1, 4)]
    if data.get("summary"):
        box = Table([[Paragraph(_cites(data["summary"]), st["body"])]], colWidths=[174 * mm])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FB")), ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#E1E5EE")),
                                 ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
        story += [Paragraph("Summary" if en else "Özet", st["h2"]), box]
    for i, s in enumerate(data.get("steps", []), 1):
        story += [Paragraph(f"{i}. {_md(s.get('q', ''))}", st["h2"]), Paragraph(_cites(s.get("answer", "")), st["body"])]
        src = s.get("sources") or []
        if src:
            story.append(Paragraph(("Sources" if en else "Kaynaklar") + ": " + "; ".join(f"[K{k}] {_md(c.get('title', ''))}" for k, c in enumerate(src, 1)), st["small"]))
    if data.get("rules"):
        story.append(Paragraph("Misconceptions to watch" if en else "Dikkat edilecek yanılgılar", st["h2"]))
        for r in data["rules"]:
            story.append(Paragraph(f"<b>{_md(r['name'])}:</b> {_md(r['misconception'])}<br/>✓ {_md(r['correct_rule'])}", st["body"]))
    if data.get("questions"):
        story.append(Paragraph("Try it yourself (verified with SymPy)" if en else "Kendini dene (SymPy ile doğrulandı)", st["h2"]))
        _question_block(story, data["questions"], st, "Answer key" if en else "Cevap anahtarı")
    story += [Spacer(1, 10), Paragraph("Misstep · " + ("Answers come only from your notes and files; the numbers in brackets point to the source."
                                                     if en else "Cevaplar yalnızca senin notlarından ve dosyalarından geldi; köşeli parantezler kaynağı gösterir."), st["small"])]
    path = Path(path)
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                      title=data["question"][:80]).build(story)
    return path


def build_topic_report(data: dict, path: str | Path, student: str = "", lang: str = "tr") -> Path:
    """A student's study report for one topic: mastery per misconception, recent mistakes, notes, practice with key."""
    from datetime import date
    en = lang == "en"
    st = _styles()
    t = data["topic"]
    story = [Image(str(ASSETS / "wordmark.png"), width=56 * mm, height=14 * mm, hAlign="LEFT"), Spacer(1, 4),
             Paragraph("Topic report" if en else "Konu raporu", st["small"]), Paragraph(_md(t["name"]), st["h1"]),
             Paragraph(f"{_md(student)} · {date.today():%d.%m.%Y} · " + (f"mastery {_pct(t['mastery'])}" if en else f"ustalık {_pct(t['mastery'])}"), st["small"])]
    story += [Paragraph("Where you stand" if en else "Neredesin?", st["h2"]),
              _bar_chart([(r["name"], r["mastery"] if r["seen"] else None) for r in t["rules"]], 174 * mm, label_w=70 * mm)]
    if data["mistakes"]:
        story.append(Paragraph("Your recent mistakes" if en else "Son hataların", st["h2"]))
        rows = [[Paragraph(f"<b>{h}</b>", st["body"]) for h in (("Date", "Question", "You wrote", "Misconception") if en else ("Tarih", "Soru", "Cevabın", "Yanılgı"))]]
        rows += [[m["ts"], Paragraph(_md(m["problem"]), st["mono"]), Paragraph(_md(m["picked"] or "–"), st["mono"]), Paragraph(_md(m["rule"]), st["body"])]
                 for m in data["mistakes"]]
        tb = Table(rows, colWidths=[22 * mm, 58 * mm, 40 * mm, 54 * mm])
        tb.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Sans"), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1F6")), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E1E5EE"))]))
        story.append(tb)
    story.append(Paragraph("Rules to remember" if en else "Akılda tutulacak kurallar", st["h2"]))
    for r in t["rules"]:
        story.append(Paragraph(f"<b>{_md(r['name'])}</b> · ✗ <font name='Mono'>{_md(r['example'])}</font><br/>✓ {_md(r['correct_rule'])}", st["body"]))
    if data["questions"]:
        story.append(Paragraph("Practice (weakest first, verified with SymPy)" if en else "Alıştırma (en zayıftan başlayarak, SymPy ile doğrulandı)", st["h2"]))
        _question_block(story, data["questions"], st, "Answer key" if en else "Cevap anahtarı")
    story += [Spacer(1, 10), Paragraph("Misstep · " + ("Mastery is estimated with Bayesian Knowledge Tracing." if en
                                                     else "Ustalık, Bayesçi bilgi izleme (BKT) ile tahmin edilir."), st["small"])]
    path = Path(path)
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                      title=t["name"]).build(story)
    return path
