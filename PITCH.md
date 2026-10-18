# Misstep: sunum ve pazarlama planı

## Tek cümle
"Fotoğraftan çözüm veren uygulamalar doğru cevabı söyler; Misstep öğrencinin kendi çözümünde **nerede ve neden** yanıldığını bulur, hem de bilgisayarın içinde, Gemma 4 ile."

## Kime satıyoruz
| Kim | Acısı | Misstep ne verir | Kim öder |
|---|---|---|---|
| 7–10. sınıf öğrenci (LGS / lise) | Cevabı görüyor ama neden yanlış yaptığını bilmiyor | İlk hatalı adım + yanılgının adı + doğrulanmış teşhis soruları | 99 ₺/ay (veli dahil) |
| **Özel ders öğretmeni** (Side Hustle) | Her hafta kâğıt okumak saatler alıyor, veliye rapor vermek zor | Sınıf tablosu, haftalık PDF, veli raporu | 499 ₺/ay |
| Okul / dershane | Sınıfta hangi yanılgı yaygın bilinmiyor, veri gizliliği | Okul sunucusunda kurulum, yanılgı haritası | 39 ₺/öğrenci/ay |
| Veli | Çocuğun neyde zorlandığını göremiyor | Çocuk başına ilerleme ve zayıf konu | Öğrenci ve öğretmen paketine dahil |

**Side Hustle hikayesi:** 30 öğrencili bir özel ders öğretmeni öğrenci başı 300 ₺ "haftalık hata takibi" alırsa ayda 9.000 ₺ gelir, 499 ₺ gider (sitedeki hesaplayıcı bunu canlı gösterir). Kod açık kaynak kalır; ücretli paketler hazır kurulum, güncelleme ve destek içerir.

## Jüriye 3 dakikalık demo
1. **0:00 Sorun (20 sn).** "Öğrenci 3x − (x + 3) = 7 yazıyor, 2. satırda −3 yerine +3 yazıyor. Cevap uygulaması x = 5 der, geçer. Öğrenci aynı hatayı sınavda tekrar yapar."
2. **0:20 Fotoğraf (60 sn).** Öğrenci demosu, Analiz et, el yazısı fotoğraf. Gemma 4 satırları okur, SymPy her adımı kontrol eder, 2. adım kırmızı, "eksi parantezin yalnızca ilk terimine dağıtılmış". Ardından doğrulanmış 3 teşhis sorusu.
3. **1:20 Ders çalış (30 sn).** Asistana sor (kaynaklı cevap, K1 K2) ve Derin araştırma, PDF rapor.
4. **1:50 Öğretmen (30 sn).** Hesap değiştir, Öğretmen, sınıf tablosu (yanlış sayısına göre sırala), haftalık PDF.
5. **2:20 İş modeli (30 sn).** Ana sayfa, Fiyatlar, hesaplayıcıyı kaydır. "Öğrenciye uygun fiyat, öğretmene yan gelir."
6. **2:50 Kapanış (10 sn).** "43 vakalık değerlendirme setimiz var, sonuçlar Hakkında sayfasında. Hepsi açık kaynak ve internetsiz çalışıyor."

## Jürinin puanladığı yerler
- **Açık model merkezde:** Gemma 4 fotoğrafı okur ve anlatır; EmbeddingGemma kaynak arar. Hepsi Ollama ile yerel.
- **Ölçülmüş doğruluk:** `python -m misstep.evaluate` ile canlı çalışan 43 vakalık set. Uydurma sayı yok, başarısız vakalar da listeleniyor.
- **Güven:** Matematiği model değil SymPy doğrular; Gemma yanlış okursa satır düzeltilebilir.
- **Gizlilik:** Çocuk verisi bilgisayardan çıkmaz (KVKK açısından güçlü argüman).

## Sık gelecek sorular
- *"Photomath'tan farkı?"* O cevap verir, biz öğrencinin kendi hatasını ve yanılgısını buluruz.
- *"Gemma yanlış okursa?"* Satırlar ekranda düzenlenebilir; teşhisi SymPy yapar.
- *"Neden sadece cebir?"* Bilerek dar tuttuk: 13 yanılgıyı derinlemesine doğruluyoruz. Sonraki adım kesirler ve geometri.
