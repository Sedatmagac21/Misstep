# Misstep Teknik Rapor

> **Misstep** 7–10. sınıf cebir için bir çalışma platformudur.
> - **Öğrenci:** çözümünü kontrol ettirir, kaynaklarından ders çalışır, kendine özel test üretir ve ilerlemesini takip eder.
> - **Öğretmen:** sınıflarını yönetir, ödev verir ve sınıfın durumunu tek tabloda görür.
> - **Veli:** çocuklarının gelişimini ve ödevlerini izler.
>
> Sistemin kalbinde açık kaynak **Gemma 4** modeli var ve her şey internete veri göndermeden, kullanıcının kendi bilgisayarında çalışır.

**Repo:** https://github.com/Sedatmagac21/Misstep
**Etkinlik:** MLH Hacktoberfest Hack Day Elazığ (17–18 Ekim 2026), tema *Side Hustle*.

İçindekiler:
1. Kim ne yapabiliyor?
2. Tek cümleyle nasıl çalışıyor?
3. Kullanılan modeller ve neden
4. Mimari
5. Çözüm kontrolü adım adım
6. 13 yanılgı
7. Ders çalışma asistanı ve kaynaklar (RAG)
8. Soru üretimi, Hata Avı, derin araştırma
9. İlerleme takibi
10. Güvenlik ve veri
11. Testler ve değerlendirme
12. Sınırlamalar
13. Sık sorulan sorular

---

## 1. Kim ne yapabiliyor?

### Öğrenci
| Özellik | Ne yapar |
|---|---|
| **Panelim** | GitHub tarzı çalışma takvimi, günlük grafik, konu bazında ustalık, odak konuları, son testler |
| **Soru üret** | Konu ve zorluk (kolay / orta / zor / **uyarlanabilir**) seçilir, 1–20 soru. "Kesirlerden 5 zor soru, market temalı" gibi serbest yazıyla da istenebilir. |
| **Test değerlendirmesi** | Doğru / yanlış / boş grafiği, net, süre, güçlü yönler, ortaya çıkan yanılgılar ve her soru için "Neden?" açıklaması |
| **Çözüm kontrolü** | El yazısı çözümün fotoğrafı ya da yazılı hali. İlk hatalı adım, yanılgının adı, sayısal bir karşı örnek ve kaynaklı açıklama. |
| **Ders çalış** | Konu anlatımı, kaynaklardan cevap veren **asistan** ve **derin araştırma** (çok adımlı, kaynaklı, PDF rapor) |
| **Kaynaklar** | Öğretmenin paylaştığı ve öğrencinin yüklediği PDF, Word ve metin dosyaları. Asistan bunlardan cevap verir. |
| **Hata Avı** | Bir sınıf arkadaşının çözümündeki hatayı bulma oyunu, puan ve seriyle |
| **Hata defterim** | Geçmiş hatalar ve onlardan otomatik test |

### Öğretmen
- **Sınıflar:** Her sınıfın bir katılım kodu vardır. Sınıfa tıklayınca öğrenci tablosu açılır. Tablo her sütuna göre sıralanabilir: soru, doğru, yanlış, başarı yüzdesi, bu hafta, seri, ödev, son giriş, en zayıf yanılgı.
- **Sınıf genel görünümü:** Öğrenci × konu ustalık haritası ve sınıfta en yaygın yanılgılar.
- **Ödev:** Konu, seviye ve soru sayısı seçilerek ödev atanır. Her öğrencinin ödevdeki ilerlemesi görülür.
- **Raporlar:** Haftalık sınıf raporu PDF'i ve cevap anahtarlı çalışma kâğıdı PDF'i.
- **Kaynak paylaşma:** Ders dosyaları sınıfla paylaşılır ve öğrencilerin asistanı bunları kullanır.

### Veli
- Birden fazla çocuk yan yana izlenebilir. Bağlantı, öğrencinin aile koduyla kurulur.
- Her çocuk için haftalık özet, öğretmenin verdiği ödevler ve **yapılıp yapılmadığı**, bitirilen testler, çalışma takvimi ve zayıf konular görülür.

---

## 2. Tek cümleyle nasıl çalışıyor?
**Gemma 4 okur ve anlatır, SymPy hesaplar ve karar verir.**

Bir yapay zekâ modeli bazen emin bir dille yanlış şey söyleyebilir ("halüsinasyon"). Bu yüzden Misstep'te bir cevabın doğru mu yanlış mı olduğuna **asla model karar vermez**. O kararı, sonucu matematiksel olarak kanıtlayan **SymPy** (sembolik matematik kütüphanesi) verir. Model okuma, açıklama, soru isteğini anlama ve kaynaklardan özet çıkarma gibi dil işlerini yapar.

---

## 3. Kullanılan modeller ve neden

| Bileşen | Ne işe yarar | Neden bu? |
|---|---|---|
| **Gemma 4 E4B** (Google'ın açık modeli, Ollama ile yerel) | El yazısını okur, açıklama yazar, sohbet eder, serbest metin soru isteğini anlar, araştırma planı ve özeti çıkarır | Açık ağırlıklı ve görüntü okuyabiliyor. Bir dizüstü bilgisayarda (MacBook Air M4) çalışacak kadar küçük. İnternet ve API ücreti gerektirmiyor. |
| **EmbeddingGemma** (Ollama) | Metinlerin anlamını sayılara çevirir, anlamsal arama yapar | Aynı aileden, küçük ve yerel. Kurulu değilse sistem kelime aramasıyla çalışmaya devam eder. |
| **SymPy** | Matematiği kontrol eder: iki satır denk mi, çözüm nedir, üretilen soru doğru mu? | Kesin sonuç verir ve uydurmaz. |
| **FastAPI** | Sunucu (48 uç nokta) | Hafif ve hızlı geliştiriliyor |
| **SQLite** | Hesaplar, sınıflar, denemeler, dosyalar | Kurulumsuz, tek dosya, yerel |
| **reportlab** | PDF raporlar | Türkçe karakterleri doğru basıyor (DejaVu fontu) |

**E4B ne demek?** Gemma 4 ailesinin cihaz üstünde çalışmak için tasarlanmış küçük, görüntü ve metin anlayan sürümü. Ollama'daki adı `gemma4:e4b`.

**Neden bulut API'si (ör. ChatGPT, Gemini API) değil de açık model?**
- **Gizlilik:** Çocuğun el yazısı ve notları bilgisayardan çıkmıyor. Bu, KVKK ve MEB'in yapay zekâ etik kılavuzu açısından önemli.
- **Maliyet:** Soru başına API ücreti yok. Öğrenci sayısı arttıkça maliyet artmıyor, bu da düşük fiyatı mümkün kılıyor.
- **İnternetsiz çalışma:** Bağlantı zayıf bir okulda da çalışıyor.
- **Kontrol:** Model sürümü bizim elimizde. Bir API sağlayıcısı modeli değiştirince ya da fiyatı artırınca ürün bozulmuyor.
- **Uyarlanabilirlik:** Açık model ileride kendi verimizle ince ayar yapılabilir.

### Gemma'yı nasıl kullanıyoruz?
| Görev | "Yaratıcılık" (sıcaklık) | Çıktı |
|---|---|---|
| Fotoğraf okuma | 0 (hiç yaratıcı değil) | Sabit bir JSON şablonu: satırlar ve güven |
| Hata açıklaması | 0.2 | En fazla 320 token, kaynak etiketli ([K1]) |
| Ders asistanı | 0.3 | En fazla 450 token, kaynak etiketli |
| Soru isteğini anlama | 0 | JSON: konu, seviye, adet, tema |
| Soruya hikaye ekleme | 0.7 | 1–2 cümle |
| Derin araştırma | 0.2 | Plan (JSON), adım cevapları, özet |

**Okuma talimatının en önemli kuralı:** "Öğrencinin yazdığını aynen aktar, **hiçbir hatayı düzeltme**." Model hatayı düzeltirse hata bulunamaz. Okunan satırlar ekranda düzenlenebilir, böylece öğrenci bir okuma hatasını kontrol etmeden önce düzeltebilir.

**Gemma çalışmazsa ne olur?** Teşhis, soru üretimi, takip ve raporlar modelsiz de çalışır. Asistan Gemma'nın neden cevap veremediğini (Ollama kapalı, model indirilmemiş, zaman aşımı) ve düzeltme komutunu gösterir. Cevabı da kaynaklardan seçtiği cümlelerle verir.

---

## 4. Mimari

```
┌────────────── Tarayıcı (HTML + JavaScript, Türkçe/İngilizce) ──────────────┐
│ Ana sayfa · Giriş · Öğrenci · Öğretmen · Veli · Ders çalış · Hata Avı       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│ Sunucu (FastAPI, Python)                                                     │
│  okuma (vision) · kontrol ve teşhis (diagnose, bugs) · asistan (rag)         │
│  soru üretimi (generator, practice) · Hata Avı (hunt) · araştırma (research) │
│  takip (progress) · hesaplar, sınıflar, ödevler (accounts) · PDF (pdf_report)│
└───────┬─────────────────────┬──────────────────────┬────────────────────────┘
        │                     │                      │
   Ollama (yerel)          SymPy             SQLite dosyası
   gemma4:e4b                                (bilgisayarda)
   embeddinggemma
```
Her şey tek bir programla, `python app.py` komutuyla `localhost:7860` adresinde açılır.

---

## 5. Çözüm kontrolü adım adım
Örnek: öğrenci `3x − (x + 3) = 7` sorusunu çözüyor.

| Satır | Öğrencinin yazdığı | Misstep'in kararı |
|---|---|---|
| 0 | 3x − (x + 3) = 7 | Soru |
| 1 | 3x − x + 3 = 7 | **Hata:** önceki satırla denk değil |
| 2 | 2x + 3 = 7 | Tutarlı (hatalı satıra göre doğru işlem) |
| 3 | x = 2 | Tutarlı |

1. **Okuma:** Gemma fotoğraftaki dört satırı metne çevirir.
2. **Yapıyı koruma:** SymPy normalde ifadeyi okurken sadeleştirir (`3x − (x+3)` doğrudan `2x − 3` olur), bu da hatanın izini siler. Bu yüzden her satır **sadeleştirilmeden** bir ağaç olarak okunur.
3. **Denklik kontrolü:** Her satır bir öncekiyle karşılaştırılır. 4 seviye vardır:
   - aynı (taraflar eşit);
   - orantılı (`2x+4=10` ile `x+2=5`);
   - sadece çözümleri aynı;
   - denk değil.

   Denkliği bozan ilk satır **ilk hatalı adımdır**.
4. **Teşhis:** 13 yanılgı kuralının her biri satır 0'a uygulanır. "Eksiyi sadece ilk terime dağıt" kuralı tam olarak `3x − x + 3 = 7` satırını üretir, yani yanılgı budur. Bu bir tahmin değil, **yeniden üretimdir**.
5. **Karşı örnek:** "Senin satırına göre x = 2. Bunu ilk satıra koyalım: sol taraf 1, sağ taraf 7. Eşit değil."
6. **Açıklama:** Asistan konu notlarından bu yanılgının notunu bulur ve Gemma kaynak göstererek anlatır.
7. **Pratik:** Bu yanılgıyı yakalayan, SymPy ile doğrulanmış sorular üretilir.
8. **Kayıt:** Sonuç öğrencinin ilerlemesine işlenir.

Hiçbir kural satırı üretemezse sistem **yanılgı uydurmaz** ve "muhtemelen işlem hatası" der.

---

## 6. 13 yanılgı
Fikir, Brown & Burton'ın 1978'deki BUGGY çalışmasından gelir: öğrenciler rastgele hata yapmaz, **yanlış öğrenilmiş bir kuralı** tutarlı biçimde uygular.

| Konu | Yanılgılar |
|---|---|
| Parantez ve dağılma | Eksiyi sadece ilk terime dağıtma · Çarpanı sadece ilk terime dağıtma |
| Denklem çözme | Terimi işaret değiştirmeden karşıya atma · Katsayıyı yanlış ters işlemle atma (3x = 12 → x = 9) · Bölmeyi tüm terimlere uygulamama |
| Terimler | Benzer terimleri toplarken üssü artırma (3x + 5x = 8x²) · Benzer olmayanları birleştirme |
| Kesirler | Terim sadeleştirme ((x+6)/6 = x) · Pay paya, payda paydaya toplama |
| Özdeşlikler | (a+b)² = a² + b² sanma |
| Üslü ve köklü | Üs kurallarını karıştırma · √(a+b) = √a + √b sanma |
| İkinci derece | x² = 25 için −5 kökünü unutma |

---

## 7. Ders çalışma asistanı ve kaynaklar (RAG)
**RAG**, yani "bul, sonra anlat": model kafasından cevap vermez. Önce kaynaklardan ilgili parçalar bulunur, model **sadece bunları kullanarak** cevap yazar ve her bilginin yanına kaynağını ([K1], [K2]) koyar. Öğrenci kaynağa tıklayıp orijinal metni görebilir.

- **Kaynaklar:** Konu notları ve yüklenen PDF, Word, TXT ve Markdown dosyaları (en fazla 15 MB). Dosyalar yaklaşık 900 karakterlik parçalara bölünür.
- **İki tür arama:**
  - **BM25:** Kelime eşleşmesine bakar ve nadir kelimeye daha çok puan verir. Örneğin "parantez" kelimesi "hata" kelimesinden daha değerlidir.
  - **EmbeddingGemma:** Anlam benzerliğine bakar. "Eksi işareti" ile "negatif çarpan" yakın bulunur.
- **Birleştirme (RRF):** İki aramanın sıralamaları birleştirilir. Her iki listede de üst sıralarda olan parça kazanır.
- **Gemma yoksa:** En uygun kaynak cümleleri, kaynaklarıyla birlikte gösterilir.

---

## 8. Soru üretimi, Hata Avı, derin araştırma
- **Soru üretimi:**
  - Soru **cevaptan geriye doğru** kurulur. Örneğin cevap x = 4 seçilir ve ona uyan bir denklem yazılır.
  - SymPy cevap anahtarının gerçekten doğru olduğunu kontrol eder.
  - **Yanlış seçenekler rastgele değildir:** her biri bir yanılgının üreteceği cevaptır. Öğrenci yanlış şıkkı seçince hangi yanılgıya sahip olduğu anlaşılır.
- **Uyarlanabilir test:** Doğru cevaptan sonra zorluk artar, yanlıştan sonra azalır.
- **Hata Avı:** Aynı kurallar ters çalıştırılır. Doğru bir çözüme bir yanılgı bilerek eklenir, öğrenci hatalı satırı bulur ve yanılgıyı seçer. Bulmaca öğrenciye gösterilmeden önce teşhis motoru tarafından tekrar kontrol edilir. Puanlama: satırı bulmak 10, yanılgıyı da bilmek +5 puan. "Hatalı örneklerden öğrenme" araştırmalarına dayanır.
- **Derin araştırma:** Gemma soruyu 3–4 alt soruya böler, her biri için ayrı arama yapılır ve kaynaklı cevap yazılır. Sonra hepsi özetlenir ve doğrulanmış alıştırmalarla birlikte PDF olarak indirilir.

---

## 9. İlerleme takibi
Her yanılgı için "öğrenci bunu artık aştı mı?" olasılığı tutulur. Bu, eğitim teknolojisinde yaygın olan **Bayesian Knowledge Tracing (BKT)** yöntemidir.
- **Doğru cevap:** olasılık artar.
- **Yanlış cevap:** olasılık düşer.
- **Dikkatsizlik ve şans payı:** Model iki olasılığı hesaba katar:
  - %10 bilip yanlış yapma (dikkatsizlik);
  - %25 bilmeden doğru tutturma (4 şıkta şans).

Konu ustalığı, o konudaki yanılgıların ortalamasıdır. Paneldeki yüzdeler, odak konuları ve öneriler buradan gelir.

---

## 10. Güvenlik ve veri
- **Veri yeri:** Tüm veriler kullanıcının bilgisayarındaki tek bir SQLite dosyasında tutulur. Hiçbir veri dış bir servise gönderilmez.
- **Şifreler:** PBKDF2-SHA256 ile 200.000 kez özetlenir ve her şifre için rastgele bir tuz kullanılır. Şifrenin kendisi hiçbir yerde saklanmaz.
- **Oturum:** Rastgele, tahmin edilemez bir anahtar çerezde tutulur.
- **Kodlar:** Sınıf ve aile kodları karıştırılabilecek harfler (0/O, 1/I) olmadan üretilir.

---

## 11. Testler ve değerlendirme

### Otomatik testler (108 test)
| Grup | Neyi kontrol ediyor |
|---|---|
| Matematik motoru | Ayrıştırma, denklik, her yanılgı kuralının doğru satırı üretmesi, karşı örnek |
| Soru üretimi | Her kural ve seviye için soruların gerçekten çözülebilmesi, cevap anahtarının ve yanlış seçeneklerin doğruluğu |
| Takip | BKT güncellemeleri, takvim ve seri hesapları |
| Dosyalar | PDF, Word ve metin okuma, parçalama, boş dosya ve boyut sınırı |
| Web | Kayıt, giriş, üç rol, sınıf tablosu ve sıralama, ödev, veli bağlantısı, PDF'ler, araştırma, Hata Avı |
| Model bağlantısı | Sahte bir Ollama sunucusuyla dört senaryo: başarılı cevap, eksik model, düşünme modunu desteklemeyen eski Ollama, kapalı servis |

### Değerlendirme seti (43 çözüm)
Elle yazılmış 43 öğrenci çözümünden oluşur: 10 tamamen doğru, 30 bilinen bir yanılgı içeren ve 3 basit işlem hatası içeren çözüm. Vakalar sistem üzerinde denenmeden önce yazıldı ve sonuçlar güzel görünsün diye değiştirilmedi.

| Ölçüt | Sonuç | Anlamı |
|---|---|---|
| İlk hatalı adımı bulma | **%100** (43/43) | Hatanın hangi satırda başladığını her vakada doğru buldu |
| Yanılgıyı doğru adlandırma | **%97** (29/30) | 30 yanılgılı çözümün 29'unda doğru yanılgıyı söyledi |
| Doğru çözümde yanlış alarm | **%0** (0/10) | Doğru çözüme hiç "hata var" demedi |
| Ortalama süre | 0,8 sn | Bir çözümün kontrolü (model okuması hariç) |

İki zayıf nokta açıkça listelenir:
1. **Bir kesir sadeleştirme vakasında** satır doğru bulundu ama kural o yazım biçimini üretemedi.
2. **İşlem hatası vakaları:** 3 vakadan birinde, sıradan bir işlem hatası tesadüfen bir yanılgının ürettiği satırla aynı çıktığı için yanılgı olarak etiketlendi.

**Fotoğraf okuma doğruluğu** henüz ölçülmedi. Bunun için gerçek el yazısı fotoğrafları gerekiyor; araç hazır (`--photos`).

---

## 12. Sınırlamalar
- **Kapsam:** Şimdilik yalnızca 7–10. sınıf cebir ve tek değişkenli denklemler. Eşitsizlik, denklem sistemi ve geometri yok.
- **Kural listesi:** 13 yanılgıyla sınırlı. Bunların dışındaki bir hata "işlem hatası" olarak görülür.
- **El yazısı okuma:** Kalitesi Gemma'ya ve fotoğrafa bağlıdır; öğrenci satırları düzelterek telafi eder.
- **Hız:** Zayıf bir bilgisayarda Gemma'nın ilk açılışı yavaş olabilir.
- **Değerlendirme seti:** Küçük ve ekip tarafından hazırlandı. Gerçek öğrencilerle pilot çalışma henüz yapılmadı.

---

## 13. Sık sorulan sorular

**Misstep sadece hata bulan bir uygulama mı?**
Hayır. Öğrenci için çözüm kontrolünün yanında soru üretimi, uyarlanabilir test ve değerlendirme, kaynaklardan ders çalışma asistanı, derin araştırma, Hata Avı ve ilerleme takvimi var. Öğretmen sınıf yönetimi, ödev, sınıf tablosu ve haftalık rapor alır; veli çocuklarını ve ödevlerini izler. Hata teşhisi bu platformu diğerlerinden ayıran çekirdektir.

**"13" ne?**
Ortaokul ve lise cebirinde en sık görülen 13 yanılgı, yani yanlış öğrenilmiş kural. Her biri, öğrencinin yanlış satırını birebir yeniden üretebilen bir program parçası olarak yazıldı.

**"%100" neyin yüzdesi?**
43 çözümlük test setinde hatanın **hangi satırda başladığını** bulma oranı. Bu kısmı model değil SymPy yapıyor, yani matematiksel bir kontrol olduğu için hata payı çok düşük. Yanılgıyı adlandırma oranı ise %97.

**%97 neden %100 değil?**
Bir vakada öğrencinin kesri sadeleştirme biçimini kuralımız üretemedi. Sistem satırı doğru buldu ama yanılgıya isim veremedi. Bu durumda uydurmak yerine "işlem hatası olabilir" dedi.

**Test setini siz yazdınız, sonuçlar taraflı olabilir mi?**
Olabilir, bu yüzden bunu açıkça söylüyoruz. Vakalar sistem denenmeden önce yazıldı, sonradan değiştirilmedi ve başarısız vakalar da yayınlandı. Bir sonraki adım, gerçek öğrenci kâğıtlarıyla pilot çalışma.

**Neden ChatGPT veya Gemini API değil de Gemma?**
Çocuk verisi buluta gitmiyor (KVKK), soru başına API ücreti yok (öğrenci arttıkça maliyet artmıyor), internetsiz çalışıyor ve model değişikliği bizim kontrolümüzde. Ayrıca matematik kararını zaten SymPy verdiği için en büyük modele ihtiyacımız yok: okuma ve anlatma için yerel bir model yetiyor.

**Gemma yanlış okursa ne olur?**
Okunan satırlar ekranda düzenlenebilir bir kutuda gösterilir, öğrenci kontrol etmeden önce düzeltebilir. Teşhis, okunan metne göre SymPy ile yapılır.

**Model halüsinasyon görürse ne olur?**
Not verme ve doğru/yanlış kararı modele hiç bırakılmadı. Açıklamalarda model yalnızca bulunan kaynakları kullanıyor ve her bilginin kaynağını gösteriyor; öğrenci tıklayıp kontrol edebiliyor.

**SymPy nedir?**
Python'un açık kaynak sembolik matematik kütüphanesi. Bir hesap makinesinin aksine sayılarla değil ifadelerle çalışır: "x + x" ile "2x"in aynı olduğunu kanıtlayabilir.

**RAG nedir?**
"Önce bul, sonra anlat" yaklaşımı. Model kendi hafızasından değil, bulduğumuz kaynak parçalarından cevap verir ve kaynağını gösterir.

**BM25 ve RRF nedir?**
BM25 kelime eşleşmesine dayalı klasik bir arama puanıdır. RRF, iki farklı aramanın sıralamasını birleştirme yöntemidir: iki listede de üst sıradaki sonuç öne çıkar.

**BKT nedir?**
Bayesian Knowledge Tracing: öğrencinin bir konuyu öğrenmiş olma olasılığını her cevaptan sonra güncelleyen bir yöntem. Dikkatsizliği (bilip yanlış yapma) ve şansı (bilmeden doğru tutturma) hesaba katar.

**Photomath gibi uygulamalardan farkı ne?**
Onlar soruyu kendileri çözer ve doğru cevabı gösterir. Misstep öğrencinin **kendi** çözümünü okur, nerede ve **neden** yanıldığını söyler, o yanılgıya özel soru üretir ve bunu zamanla takip eder. Öğretmen ve veli panelleri de vardır.

**İnternet gerekiyor mu? Hangi bilgisayarda çalışır?**
Kurulumdan sonra internet gerekmez. MacBook Air M4 üzerinde geliştirildi. Gemma olmadan da teşhis, soru üretimi ve takip çalışır.

**Modeli eğittiniz mi (fine-tune)?**
Hayır. Okuma ve anlatma için doğru talimat ve sabit JSON çıktı şablonu yetti; asıl zekâ kural kütüphanesinde ve SymPy'de. Açık model olduğu için ileride gerçek öğrenci verisiyle ince ayar yapılabilir; bu bir API ile mümkün değildir.

**Neden sadece cebir?**
Bilerek dar tuttuk: her yanılgıyı derinlemesine doğrulamak istedik. Mimari genişlemeye hazır; yeni bir konu, yeni kurallar ve notlar eklemek demek.

**TAM, SAM, SOM nedir?**
Pazar büyüklüğünü üç katmanda gösterir:
- **TAM:** Toplam pazar. Türkiye'deki tüm ortaokul ve lise öğrencileri, yaklaşık 10,56 milyon (MEB 2025–2026).
- **SAM:** Ulaşılabilir pazar. Ürünün hitap ettiği 7–10. sınıf öğrencileri, yaklaşık 5,3 milyon.
- **SOM:** Gerçekçi hedef. 3. yılda yaklaşık 50 bin öğrenci, yani SAM'in yaklaşık %1'i.

TL değerleri öğrenci × 39 ₺ × 12 ay ile hesaplanır. SAM ve SOM tahmindir.

**Para nereden geliyor?**
Paketlerden: Öğrenci 99 ₺/ay (veli paneli dahil), Özel öğretmen 499 ₺/ay, Okul ve kurs öğrenci başı 39 ₺/ay. Yerel çalıştığı için sunucu ve API maliyeti çok düşük, bu da fiyatı uygun tutmayı sağlıyor.

**Veriler nerede, KVKK'ya uygun mu?**
Tüm veriler kullanıcının bilgisayarında. Şifreler geri çevrilemeyecek şekilde saklanıyor. Hiçbir veri üçüncü bir tarafa gitmiyor. Bu, MEB'in Eğitimde Yapay Zekâ Etik Kılavuzu'nun önem verdiği veri gizliliği konusunda güçlü bir yaklaşım.

**Ne kadar sürede yaptınız?**
11 saatlik hackathon süresi içinde (17 Ekim 19:00 – 18 Ekim 06:00). Kod açık kaynak ve GitHub'da.

---

## Kaynaklar
- Brown, J. S., & Burton, R. R. (1978). Diagnostic models for procedural bugs in basic mathematical skills. *Cognitive Science*, 2(2), 155–192.
- Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4, 253–278.
- Adams, D. M., McLaren, B. M., et al. (2014). Using erroneous examples to improve mathematics learning with a web-based tutoring system. *Computers in Human Behavior*, 36, 401–411.
- Große, C. S., & Renkl, A. (2007). Finding and fixing errors in worked examples. *Learning and Instruction*, 17(6), 612–634.
- Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.
- Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. *SIGIR*.
- MEB, 2025–2026 Örgün Eğitim İstatistikleri.
- MEB, Eğitimde Yapay Zekâ Uygulamaları Etik Kılavuzu (2026).
