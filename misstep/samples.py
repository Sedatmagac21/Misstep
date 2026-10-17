"""Sample study PDFs for the Resources page (the demo teacher shares them with the class).

python -m misstep.samples      # writes the PDFs to samples/ so they can also be uploaded by hand
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .pdf_report import ASSETS, GREY, NAVY, _fonts, _md

OUT = Path(__file__).resolve().parent.parent / "samples"

# (title, file name, [(heading, [paragraph or ("table", rows)])])
SAMPLES = [
    ("Cebir formül kartı", "cebir-formul-karti.pdf", [
        ("Parantez açma ve dağılma", [
            "a(b + c) = ab + ac. Parantezin önündeki sayı içerideki HER terimle çarpılır: 3(x + 4) = 3x + 12, 3x + 4 değil.",
            "-(a + b) = -a - b ve -(a - b) = -a + b. Eksi işareti parantezin içindeki bütün terimlerin işaretini değiştirir.",
            ("table", [["İfade", "Doğru açılım", "Sık yapılan hata"],
                       ["2(x + 5)", "2x + 10", "2x + 5"], ["-(x + 3)", "-x - 3", "-x + 3"], ["4 - (x - 2)", "6 - x", "2 - x"]]),
        ]),
        ("Özdeşlikler", [
            "(a + b)² = a² + 2ab + b². (a - b)² = a² - 2ab + b². (a + b)(a - b) = a² - b².",
            "Toplamın karesi, kareler toplamı değildir: (x + 3)² = x² + 6x + 9, x² + 9 değil. Kontrol için x = 1 koyun: 16 ≠ 10.",
        ]),
        ("Üslü ifadeler", [
            "aᵐ · aⁿ = aᵐ⁺ⁿ (üsler toplanır, çarpılmaz). (aᵐ)ⁿ = aᵐⁿ (üsler çarpılır). a⁰ = 1, a⁻ⁿ = 1/aⁿ.",
            "Benzer terimler toplanırken üs değişmez: 3x + 5x = 8x, 8x² değil. Üs yalnızca çarpmada değişir: 3x · 5x = 15x².",
        ]),
        ("Köklü ifadeler", [
            "√(a · b) = √a · √b, ama √(a + b) ≠ √a + √b. Örnek: √(9 + 16) = √25 = 5, 3 + 4 = 7 değil.",
            "x² = 25 denkleminin İKİ kökü vardır: x = 5 veya x = -5.",
        ]),
        ("Kesirler", [
            "a/b + c/d = (ad + bc)/(bd). Paylar ve paydalar ayrı ayrı toplanmaz: 1/2 + 1/3 = 5/6, 2/5 değil.",
            "(a + b)/a ifadesinde a sadeleşmez, çünkü a paydaki bir TERİMDİR, çarpan değildir: (x + 6)/6 = x/6 + 1.",
        ]),
    ]),
    ("Denklem çözme rehberi", "denklem-cozme-rehberi.pdf", [
        ("Altın kural: iki tarafa da aynısını yap", [
            "Bir denklem terazi gibidir. Bir tarafa yaptığınız işlemi (ekleme, çıkarma, çarpma, bölme) diğer tarafa da yapmalısınız.",
            "Karşıya geçen terim işaret değiştirir: x + 7 = 15 ise x = 15 - 7 = 8. Aslında iki taraftan da 7 çıkarıyoruz.",
        ]),
        ("Adım adım birinci dereceden denklem", [
            "1) Parantezleri dikkatle açın. 2) Benzer terimleri birleştirin. 3) x'li terimleri bir tarafa, sayıları diğer tarafa toplayın. "
            "4) x'in katsayısına iki tarafı da bölün. 5) Bulduğunuz değeri ilk denklemde yerine koyup kontrol edin.",
            ("table", [["Adım", "Satır", "Ne yaptık?"],
                       ["0", "5x - (x + 3) = 13", "Soru"], ["1", "5x - x - 3 = 13", "Eksi parantezin içindeki her terimi değiştirdi"],
                       ["2", "4x - 3 = 13", "Benzer terimler"], ["3", "4x = 16", "İki tarafa 3 ekledik"], ["4", "x = 4", "İki tarafı 4'e böldük"]]),
            "Kontrol: 5·4 - (4 + 3) = 20 - 7 = 13. Sonuç doğru.",
        ]),
        ("Çarpanı karşıya atmak", [
            "3x = 12 ise iki taraf 3'e bölünür: x = 4. Sık yapılan hata 3'ü çıkarmaktır (x = 12 - 3 = 9). Çarpma işleminin tersi bölmedir.",
            "4x + 8 = 20 denkleminde 4'e bölerken HER terim bölünür: x + 2 = 5. Sadece 4x'i bölüp 8'i unutmak (x + 8 = 5) yanlış sonuç verir.",
        ]),
        ("İkinci dereceden basit denklemler", [
            "x² = 49 ise x = 7 veya x = -7, çünkü (-7)² = 49. Negatif kökü unutmak en sık kayıp puan nedenidir.",
            "2x² = 50 ise önce x² = 25, sonra x = ±5.",
        ]),
        ("Sınav öncesi kontrol listesi", [
            "Her parantezi açtıktan sonra x = 1 koyup iki satırın aynı değeri verdiğine bakın. Cevabı ilk denklemde deneyin. "
            "x² gördüğünüzde iki kök arayın. Kesirli denklemde önce paydaları eşitleyin.",
        ]),
    ]),
    ("Kesirler çalışma föyü", "kesirler-calisma-foyu.pdf", [
        ("Kesirleri toplama", [
            "Paydalar eşitse paylar toplanır, payda aynı kalır: 2/7 + 3/7 = 5/7. Paydalar farklıysa önce ortak payda bulunur.",
            "x/2 + x/3 = 3x/6 + 2x/6 = 5x/6. Sık hata: (x + x)/(2 + 3) = 2x/5. Kontrol: x = 6 için 3 + 2 = 5, ama 12/5 = 2,4.",
        ]),
        ("Sadeleştirme: sadece çarpanlar sadeleşir", [
            "6x/6 = x doğrudur, çünkü 6 bir çarpandır. (x + 6)/6 = x yanlıştır, çünkü 6 paydaki bir terimdir.",
            "Doğrusu (x + 6)/6 = x/6 + 6/6 = x/6 + 1. Önce payı çarpanlarına ayırın: (2x + 6)/2 = 2(x + 3)/2 = x + 3.",
        ]),
        ("Kesirli denklemler", [
            "x/4 + x/6 = 10 denkleminde ortak payda 12'dir. İki tarafı 12 ile çarparız: 3x + 2x = 120, 5x = 120, x = 24.",
            "Kontrol: 24/4 + 24/6 = 6 + 4 = 10.",
        ]),
        ("Alıştırmalar", [
            ("table", [["Soru", "Cevap"],
                       ["1) x/3 + x/6 = 4", "x = 8"], ["2) (x + 4)/4 = 3", "x = 8"], ["3) x/2 + x/5 = 14", "x = 20"],
                       ["4) (3x + 9)/3 sadeleştir", "x + 3"], ["5) 2/3 + 1/4", "11/12"]]),
            "Her cevabı yerine koyarak kontrol edin. Misstep'te Kesirli ifadeler konusunda soru üreterek bu hataları test edebilirsiniz.",
        ]),
    ]),
]


def build_sample(title: str, sections: list, path: Path) -> Path:
    _fonts()
    body = ParagraphStyle("b", fontName="Sans", fontSize=10.5, leading=15, spaceAfter=5)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, textColor=GREY, leading=11)
    h1 = ParagraphStyle("h1", parent=body, fontName="Sans-Bold", fontSize=18, leading=22, textColor=NAVY, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=13, textColor=NAVY, spaceBefore=10, spaceAfter=4)
    cell = ParagraphStyle("c", parent=body, fontSize=9.5, leading=12, spaceAfter=0)
    story = [Image(str(ASSETS / "wordmark.png"), width=56 * mm, height=14 * mm, hAlign="LEFT"), Spacer(1, 4),
             Paragraph(_md(title), h1), Paragraph("Misstep örnek kaynak · 7–10. sınıf cebir", small), Spacer(1, 6)]
    for heading, parts in sections:
        story.append(Paragraph(_md(heading), h2))
        for part in parts:
            if isinstance(part, tuple):
                rows = [[Paragraph(_md(c), cell) for c in row] for row in part[1]]
                t = Table(rows, colWidths=[174 * mm / len(rows[0])] * len(rows[0]))
                t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1F6")),
                                       ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E1E5EE")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                story += [t, Spacer(1, 6)]
            else:
                story.append(Paragraph(_md(part), body))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                      title=title, author="Misstep").build(story)
    return path


def build_samples(out: Path = OUT) -> list[tuple[str, Path]]:
    out.mkdir(parents=True, exist_ok=True)
    return [(title, build_sample(title, sections, out / name)) for title, name, sections in SAMPLES]


if __name__ == "__main__":
    for title, path in build_samples():
        print(f"{title}: {path}")
