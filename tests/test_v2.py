from misstep.counterexample import counterexample
from misstep.parsing import parse_line as p
from misstep.pdf_report import build_pdf
from misstep.pipeline import analyze
from misstep.rag import load_chunks, retrieve
from misstep.bugs import RULES


def test_every_rule_has_a_knowledge_note():
    ids = {c.id for c in load_chunks()}
    assert {r.id for r in RULES} <= ids


def test_retrieval_finds_the_right_note_from_plain_turkish():
    queries = {
        "eksi parantez işaret": "SIGN_DISTRIBUTION",
        "kesirleri toplarken payda": "ADD_FRACTIONS",
        "karekök iki çözüm negatif": "LOSE_NEGATIVE_ROOT",
        "her terimi bölmeyi unuttu": "PARTIAL_BOTH_SIDES",
    }
    for q, rid in queries.items():
        assert retrieve(q, use_embeddings=False)[0].id == rid


def test_verified_diagnosis_pins_its_note():
    assert retrieve("alakasız bir soru", rule_id="SQUARE_OF_SUM", use_embeddings=False)[0].id == "SQUARE_OF_SUM"


def test_counterexamples():
    assert "sol taraf 1, sağ taraf 7" in counterexample(p("3x-(x+3)=7"), p("3x-x+3=7"))
    assert "x = -3" in counterexample(p("x^2=9"), p("x=3"))
    assert "25" in counterexample(p("(x+3)^2"), p("x^2+9"))


def test_pipeline_and_pdf(tmp_path):
    a = analyze(["2x+4=10", "x+4=5", "x=1"], explain_with_model=False)
    assert a.report.diagnosis.rule.id == "PARTIAL_BOTH_SIDES" and len(a.questions) == 3
    out = build_pdf(a, tmp_path / "r.pdf", student="Ayşe")
    assert out.stat().st_size > 5000
