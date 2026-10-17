"""Study files people upload (PDF, Word, text, Markdown) turned into searchable text.

The text is split into short passages so the RAG search and the study chat can
quote the exact part of a file that answers a question.
"""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

KINDS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt", ".md": "md"}
MAX_BYTES = 15 * 1024 * 1024


class DocumentError(ValueError):
    """A file that cannot be used, with a message key the interface translates."""


def kind_of(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in KINDS:
        raise DocumentError("err_doc_type")
    return KINDS[ext]


def _pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # listed in requirements.txt
        raise DocumentError("err_doc_pdf") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # noqa: BLE001 - broken or encrypted PDFs
        raise DocumentError("err_doc_read") from exc


def _docx_text(data: bytes) -> str:
    # a .docx is a zip; the body text lives in word/document.xml as <w:p> paragraphs of <w:t> runs
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
        raise DocumentError("err_doc_read") from exc
    paras = ["".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p")]
    return "\n".join(paras)


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise DocumentError("err_doc_size")
    kind = kind_of(filename)
    if kind == "pdf":
        text = _pdf_text(data)
    elif kind == "docx":
        text = _docx_text(data)
    else:
        text = data.decode("utf-8", errors="replace")
    text = re.sub(r"[ \t]+", " ", text).replace("\r", "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 20:
        raise DocumentError("err_doc_empty")  # e.g. a scanned PDF with no text layer
    return text


def chunk_text(text: str, size: int = 900) -> list[str]:
    """Split on paragraphs into passages of about `size` characters."""
    out, cur = [], ""
    for para in (p.strip() for p in re.split(r"\n\s*\n|\n(?=#)", text)):
        if not para:
            continue
        while len(para) > size:  # one huge paragraph: cut at a sentence end near the limit
            cut = max(para.rfind(". ", 0, size), para.rfind("\n", 0, size))
            cut = cut + 1 if cut > size // 3 else size
            if cur:
                out.append(cur)
                cur = ""
            out.append(para[:cut].strip())
            para = para[cut:].strip()
        if len(cur) + len(para) + 2 > size and cur:
            out.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        out.append(cur)
    return out
