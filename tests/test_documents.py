import io

import pytest

from misstep.documents import DocumentError, chunk_text, extract_text


def test_pdf_text_is_extracted():
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    pdf.drawString(72, 720, "Paydalar esitlenmeden kesirler toplanmaz.")
    pdf.save()
    assert "Paydalar" in extract_text("not.pdf", buf.getvalue())


def test_bad_files_are_refused():
    with pytest.raises(DocumentError):
        extract_text("resim.png", b"\x89PNG")
    with pytest.raises(DocumentError):
        extract_text("bos.txt", b"  ")
    with pytest.raises(DocumentError):
        extract_text("bozuk.docx", b"not a zip")


def test_chunks_keep_paragraphs_and_stay_short():
    text = "\n\n".join(f"Paragraf {i}. " + "kelime " * 60 for i in range(10))
    chunks = chunk_text(text, size=500)
    assert len(chunks) > 3 and all(len(c) <= 500 for c in chunks)
    assert chunks[0].startswith("Paragraf 0")
