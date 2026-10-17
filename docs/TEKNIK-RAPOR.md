# Misstep Teknik Rapor

**Proje:** Misstep, 7–10. sınıf cebir için yerel çalışan bir çalışma arkadaşı. Öğrencinin hatasının nerede ve neden yapıldığını bulur.
**Etkinlik:** MLH Hacktoberfest Hack Day Elazığ (17–18 Ekim 2026), tema *Side Hustle*.
**Repo:** https://github.com/Sedatmagac21/Misstep
**Durum:**
- 108 otomatik test geçiyor.
- Değerlendirme setinde 43 vaka var.
- Kod yaklaşık 4.200 satır Python, buna vanilla JS arayüz ekleniyor.

---

## 1. Özet
Misstep öğrencinin el yazısı çözümünü üç katmanda işler:
1. **Okuma: Gemma 4 E4B** (Ollama ile yerel). Fotoğraftaki satırları öğrencinin yazdığı gibi, düzeltmeden metne çevirir.
2. **Doğrulama: SymPy.** Her satırın bir öncekiyle matematiksel olarak denk olup olmadığını kanıtlar. Denkliği bozan ilk satır ilk hatalı adımdır.
3. **Teşhis: 13 yanılgı kuralı.** Her kural, gerçek öğrencilerin yaptığı yanlış bir dönüşümü uygular. Önceki satırdan öğrencinin yazdığı satırı **birebir üreten** kural, hatanın arkasındaki yanılgıdır.

Bu çekirdeğin etrafında şunlar var:
- Kaynaklı açıklama yapan bir **hibrit RAG** (BM25 + EmbeddingGemma).
- SymPy ile doğrulanmış **soru üretimi**.
- Yanılgı başına ustalığı izleyen **Bayesian Knowledge Tracing**.
- Öğretmen ve veli panelleri.

Temel tasarım ilkesi: **model okur ve anlatır, asla not vermez.** Doğruluk kararını her zaman sembolik matematik verir.

## 2. Problem
Fotoğraftan çözüm veren uygulamalar doğru cevabı gösterir, ama öğrencinin *kendi* çözümündeki hatayı ve o hatanın nedenini söylemez. Örnek: öğrenci `3x − (x + 3) = 7` sorusunda ikinci satıra `3x − x + 3 = 7` yazıyor. Buradaki sorun bir işlem hatası değil, bir **yanılgı**: "Eksi işareti sadece parantezin ilk terimini etkiler." Bu yanılgı düzeltilmezse öğrenci aynı hatayı başka sorularda da tekrarlar. Misstep bu yanılgıyı adıyla bulmayı, açıklamayı ve hedefli pratikle kapatmayı amaçlar.

## 3. Kullanılan modeller ve araçlar

| Bileşen | Ne iş yapar | Neden seçildi |
|---|---|---|
| **Gemma 4 E4B** (`gemma4:e4b`, Ollama) | El yazısı okuma (görüntü → satırlar), açıklama yazma, çalışma sohbeti, derin araştırma planı ve özeti, serbest metin soru isteğini ayara çevirme, soruya hikaye ekleme | Açık ağırlıklı ve görüntü girdisi alıyor. Dizüstü bilgisayarda (Mac M4) yerel çalışacak kadar küçük. Hackathonun "açık model merkezde olsun" şartını karşılıyor. Öğrencinin verisi bilgisayardan çıkmıyor. |
| **EmbeddingGemma** (`embeddinggemma`, Ollama) | Notların ve yüklenen dosyaların vektörleri, anlamsal arama | Aynı aileden, yerel ve hafif. Kurulu değilse sistem yalnızca BM25 ile çalışmaya devam ediyor. |
| **SymPy** | Ayrıştırma, denklik kanıtı, çözüm kümeleri, karşı örnek, soru doğrulama | Deterministik. Modelin "halüsinasyon" riski not verme kararına hiç girmiyor. |
| **FastAPI + Uvicorn** | 48 uç noktalı JSON API ve statik site | Hafif, hızlı geliştirme, otomatik doğrulama (pydantic). |
| **SQLite** | Hesaplar, denemeler, sınıflar, dosyalar | Kurulum gerektirmiyor, tek dosya, yerel. |
| **reportlab + DejaVu fontları** | PDF raporlar (haftalık sınıf, çalışma kâğıdı, araştırma, konu raporu) | Türkçe karakterleri doğru basıyor. |
| **pypdf** | Yüklenen PDF'lerden metin çıkarma | Saf Python. Word (.docx) dosyaları ek kütüphane olmadan zip ve XML olarak okunuyor. |

### 3.1 Gemma 4 çağrılarının ayarları
Tüm çağrılar `misstep/vision.py` içindeki tek `_post` fonksiyonundan geçer. Bu fonksiyon dört şey yapar:
- **Proxy'yi devre dışı bırakır:** Ollama yerel çalıştığı için sistem proxy'si atlanır.
- **Düşünme modunu kapatır:** Sohbet çağrılarına `think: false` ekler. Gemma 4 düşünme moduna girip token bütçesini orada bitirirse cevap boş dönebiliyordu. Bu seçeneği tanımayan eski bir Ollama sürümü isteği reddederse aynı istek seçeneksiz tekrar gönderilir.
- **Son hatayı kaydeder:** Her hatanın nedeni `LAST_ERROR` içinde tutulur.
- **Sorunu teşhis eder:** `diagnose()` Ollama'nın açık olup olmadığını ve modelin indirilip indirilmediğini kontrol eder. Arayüz kullanıcıya nedeni ve çalıştırılacak komutu gösterir (`ollama serve` veya `ollama pull gemma4:e4b`).

| Görev | Dosya | Sıcaklık | Çıktı sınırı | Biçim | Zaman aşımı |
|---|---|---|---|---|---|
| Fotoğraf okuma | vision.py | 0 | – | JSON şeması (`lines[{text, confidence}]`) | 180 sn |
| Hata açıklaması | rag.py `explain` | 0.2 | 320 token | serbest metin, [K1] atıflı | 120 sn |
| Çalışma sohbeti | rag.py `chat` | 0.3 | 450 token | serbest metin, [K1] atıflı | 240 sn |
| Serbest metin soru isteği | generator.py `interpret` | 0 | – | JSON şeması | – |
| Soru hikayesi | generator.py `add_story` | 0.7 | – | serbest metin | – |
| Araştırma planı / adım / özet | research.py | 0.2 | 200 / 220 / 300 | JSON / metin / metin | 150 sn |

**Okuma promptunun kritik kuralı:** "Yalnızca öğrencinin yazdığını aktar, hiçbir şeyi düzeltme, sadeleştirme ya da tamamlama; hatalar yazıldığı gibi kalmalı." Model hatayı düzeltirse teşhis imkânsız hale gelir. Okunan satırlar kullanıcıya düzenlenebilir bir kutuda gösterilir, böylece okuma hatası teşhisten önce elle düzeltilebilir.

## 4. Mimari

```
┌────────────────────────── Tarayıcı (web/, vanilla JS, TR/EN) ──────────────────────────┐
│ Ana sayfa · Giriş/Üye ol · Öğrenci · Öğretmen · Veli · Ders çalış · Hata Avı · Kaynaklar  │
└───────────────────────────────────────┬────────────────────────────────────────────────┘
                                        │ JSON (oturum çerezi)
┌───────────────────────────────────────▼────────────────────────────────────────────────┐
│ misstep/server.py  FastAPI, 48 uç nokta                                                 │
├──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬─────────────┤
│ vision.py    │ diagnose.py  │ rag.py       │ generator.py │ progress.py  │ accounts.py │
│ Gemma okuma  │ parsing.py   │ documents.py │ practice.py  │ BKT, takvim  │ roller,     │
│ teşhis       │ equivalence  │ research.py  │ hunt.py      │              │ sınıf, ödev │
│              │ bugs.py (13) │              │              │              │             │
│              │ counterex.   │              │              │              │             │
├──────────────┴──────┬───────┴──────┬───────┴──────────────┴──────┬───────┴─────────────┤
│ Ollama (yerel)      │ SymPy        │ SQLite (~/.misstep/misstep.db)│ reportlab (PDF)    │
│ gemma4:e4b          │              │ tek, kilitli bağlantı (db.py) │                    │
│ embeddinggemma      │              │                               │                    │
└─────────────────────┴──────────────┴───────────────────────────────┴────────────────────┘
```

- **Arayüz:** Derleme adımı yok. ES modülleri, hash tabanlı yönlendirme ve iki dil (TR/EN) var.
- **Sunucu:** Tek süreç, `python app.py` ile `localhost:7860` adresinde açılır.
- **Veritabanı:** Tek dosya. `db.py` tüm iş parçacıkları için kilitli tek bir bağlantı tutar.

## 5. Ana veri akışı: çözüm kontrolü

```
fotoğraf ─► Gemma 4 ─► satırlar (öğrenci düzeltebilir)
                          │
                          ▼
            parsing.py: her satır → değerlendirilmemiş SymPy ağacı
                          │
                          ▼
            equivalence.py: satır k, satır k−1 ile denk mi?
              ├─ denk ve henüz hata yok ─► OK
              ├─ denk ama önceki bir hataya dayanıyor ─► CONSISTENT
              └─ denk değil ─► ERROR (ilk ERROR = ilk hatalı adım)
                                   │
                                   ▼
            diagnose.py: 13 kuralı satır k−1'e uygula; hangisi satır k'yi üretiyor?
                                   │
                ┌──────────────────┼────────────────────┐
                ▼                  ▼                    ▼
       counterexample.py     rag.py explain       progress.py
       sayısal karşı örnek   kaynaklı açıklama    BKT güncelle, kaydet
                                   │
                                   ▼
            practice.py: bu yanılgıya özel, doğrulanmış teşhis soruları
```

### 5.1 Ayrıştırma (parsing.py)
SymPy normalde ayrıştırırken sadeleştirir: `3x-(x+3)` doğrudan `2x-3` olur. Bu, öğrencinin hatasının içinde yaşadığı yapıyı siler. Bu yüzden ağaç Python'un AST'sinden **`evaluate=False` ile** elle kurulur. Örtük çarpma (`3x`, `2(x+1)`) belirteç aşamasında eklenir. Sayılar `Rational` olarak tutulur, böylece kayan nokta hatası olmaz.

### 5.2 Denklik (equivalence.py)
İki satır dört seviyede karşılaştırılır:

| Seviye | Anlamı | Örnek |
|---|---|---|
| EXACT | İki taraf ayrı ayrı eşit (ya da yer değiştirmiş) | `2x+4=10` ve `4+2x=10` |
| PROPORTIONAL | Denklemler sıfır olmayan bir sabitle orantılı | `2x+4=10` ve `x+2=5` |
| SAME_SOLUTIONS | Yalnızca çözüm kümeleri aynı (reel sayılarda `solveset`) | `(x−3)² = 0` ve `x = 3` |
| NONE | Denk değil | `3x−(x+3)=7` ve `3x−x+3=7` |

Değerlendirme sonuçları `lru_cache` ile önbelleğe alınır (4.096 girdi).

### 5.3 Yanılgı kuralları (bugs.py)
Kurallar Brown & Burton'ın BUGGY (1978) fikrine dayanır. Her kural, önceki satıra uygulanınca "yanılgılı" aday satırlar üreten bir fonksiyondur. Kurallar alt ağaçların her birinde denenir. Eşleşme gücü şöyle sıralanır: EXACT = 3, PROPORTIONAL = 2, SAME_SOLUTIONS = 1. En güçlü eşleşme "kesin", daha zayıfı "olası" olarak raporlanır. Önceki satırı değiştirmeyen adaylar elenir, yani kural gerçekten bir şey yapmamışsa yanılgı sayılmaz. Hiçbir kural eşleşmezse sistem yanılgı uydurmaz ve "muhtemelen işlem hatası" der.

| # | Kural | Yanılgı |
|---|---|---|
| 1 | SIGN_DISTRIBUTION | Eksiyi parantezin sadece ilk terimine dağıtma |
| 2 | PARTIAL_DISTRIBUTION | Çarpanı parantezin sadece ilk terimine dağıtma |
| 3 | SQUARE_OF_SUM | (a+b)² = a² + b² sanma |
| 4 | POWER_RULES | Üslü sayılarda çarpma ve kuvvet kurallarını karıştırma |
| 5 | LIKE_TERMS_POWER | Benzer terimleri toplarken üssü artırma |
| 6 | COMBINE_UNLIKE | Benzer olmayan terimleri birleştirme |
| 7 | ILLEGAL_CANCELLATION | Kesirde çarpan yerine terim sadeleştirme |
| 8 | ADD_FRACTIONS | Kesirleri pay paya, payda paydaya toplama |
| 9 | SQRT_OF_SUM | √(a+b) = √a + √b sanma |
| 10 | MOVE_WITHOUT_SIGN_CHANGE | Terimi karşıya işaret değiştirmeden geçirme |
| 11 | WRONG_INVERSE_OPERATION | Katsayıyı yanlış ters işlemle geçirme (bölmek yerine çıkarmak) |
| 12 | PARTIAL_BOTH_SIDES | Bölme veya çarpmayı tüm terimlere uygulamama |
| 13 | LOSE_NEGATIVE_ROOT | x² = a çözümünde negatif kökü unutma |

Kurallar yedi konuya ayrılır: Parantez ve dağılma, Denklem çözme, Terimler ve sadeleştirme, Kesirli ifadeler, Özdeşlikler, Üslü ve köklü ifadeler, İkinci dereceden denklemler.

### 5.4 Karşı örnek (counterexample.py)
Öğrenciye "yanlış" demek yerine somut bir sayı gösterilir:
- **Denklemlerde:** Öğrencinin satırının bir çözümü bulunur ve önceki satırda yerine konur. Sol ve sağ tarafların eşit çıkmadığı gösterilir. Bir çözüm kaybolduysa bu belirtilir.
- **İfadelerde:** x = 2, 1, 3, −1, 4, 5 değerleri sırayla denenir ve iki ifadenin farklı sonuç verdiği ilk değer gösterilir.

## 6. Hibrit RAG (rag.py, documents.py)
- **Kaynaklar:**
  - `knowledge/cebir-notlari.md`: her yanılgı için bir bölüm ve bir genel bölüm.
  - Öğretmenin ve öğrencinin yüklediği PDF, Word, TXT ve Markdown dosyaları (en fazla 15 MB).
- **Parçalama:** Paragraf sınırlarından bölünür, parçalar yaklaşık 900 karakterdir. Çok uzun bir paragraf cümle sonundan kesilir.
- **Arama:**
  1. **BM25** (k1 = 1.5, b = 0.75) her zaman çalışır.
  2. EmbeddingGemma varsa kosinüs benzerliğiyle ikinci bir sıralama yapılır.
  3. İki sıralama **Reciprocal Rank Fusion** ile birleştirilir: skor = Σ 1/(60 + sıra).
  4. Teşhis edilen yanılgının kendi notu öne alınır.
- **Üretim:** Gemma'ya yalnızca bulunan kaynaklar verilir ve her bilginin sonuna [K1], [K2] gibi atıf koyması istenir. Kaynakta cevap yoksa bunu açıkça söylemesi istenir. Sohbet, son 6 mesajı ve öğrencinin zayıf olduğu yanılgıları bağlam olarak alır.
- **Model çalışmazsa:** Sohbet bir "çıkarımsal" cevap verir. Sorudaki nadir kelimelere göre (IDF ağırlıklı) en uygun kaynak cümleleri seçilir, atıflarıyla gösterilir ve ekrana Gemma'nın neden cevap veremediği yazılır. Hiçbir bilgi uydurulmaz.

## 7. Soru üretimi ve çeldiriciler (generator.py, practice.py)
- Her soru, tam sayı bir cevaptan **geriye doğru** kurulur. 13 kural × 3 seviye (kolay, orta, zor) için şablon vardır. Adaptif modda doğru cevaptan sonra zorluk artar, yanlıştan sonra azalır.
- **Kabul şartları:**
  - SymPy cevap anahtarının soruyu gerçekten çözdüğünü doğrulamalı.
  - En az bir yanılgı *farklı* bir cevaba götürmeli.
- **Çeldiriciler:** Yanlış seçenekler, yanılgıların ürettiği cevaplardır. Öğrenci bir çeldirici seçerse hangi yanılgının hâlâ sürdüğü bilinir. Saçma seçenekler (ör. x = 319) elenir. Yeterli seçenek çıkmazsa ±1, ±2 gibi işlem hatası seçenekleri eklenir.
- **Serbest metin istek:** "zor kesirli 5 soru, pazar alışverişi temalı" gibi bir istek, Gemma ile JSON ayarlarına çevrilir (konu, seviye, adet, tema). Model yoksa anahtar kelimeyle çalışan bir yedek devreye girer. Hikaye yalnızca soruyu sarar; denklemin kendisi her zaman doğrulanmış şablondan gelir.

## 8. Hata Avı (hunt.py)
Yanılgı kuralları **ters yönde** çalıştırılır. Doğru bir çözüm yolunun rastgele bir adımına bir yanılgı enjekte edilir ve çözümün geri kalanı o hatalı satırdan tutarlı biçimde devam ettirilir. Bulmaca öğrenciye gösterilmeden önce teşhis motoru tarafından yeniden kontrol edilir. Bulmaca yalnızca şu iki koşul sağlanırsa kullanılır:
- `check_solution`, enjekte edilen adımı tam olarak ilk hata olarak buluyor.
- Enjekte edilen yanılgıyı adlandırıyor.

Öğrenci yanlış satırı bulursa 10 puan alır, yanılgıyı da doğru seçerse 5 puan daha. Yöntem "hatalı örneklerden öğrenme" araştırmasına dayanır (Adams vd. 2014; Große & Renkl 2007).

## 9. Derin araştırma (research.py)
1. **Plan:** Gemma soruyu 3–4 alt soruya böler (JSON). Model yoksa sabit 4 adımlık bir plan kullanılır: kural, sık hata, çözülmüş örnek, kontrol yöntemi.
2. **Adım:** Her alt soru için ayrı bir arama yapılır ve kaynaklı kısa bir cevap yazılır. Önceki adımlarda kullanılan cümleler tekrar edilmez.
3. **Özet:** Cevaplar 4–6 cümlede birleştirilir. İlgili yanılgılar bulunur ve sonuç, SymPy ile doğrulanmış alıştırma sorularıyla birlikte PDF'e aktarılır.

## 10. Öğrenci modeli (progress.py)
- Her kontrol edilen çözüm ve her cevaplanan soru, yanılgı bazında bir gözlem olarak kaydedilir.
- **Bayesian Knowledge Tracing** (Corbett & Anderson 1994) kullanılır. Parametreler: başlangıç olasılığı P(L₀) = 0.3, öğrenme P(T) = 0.15, kayma P(S) = 0.1, tahmin P(G) = 0.25 (4 seçenekli sorular).
  - Doğru cevapta: P(L|doğru) = P(L)(1−S) / [P(L)(1−S) + (1−P(L))G]
  - Yanlış cevapta: P(L|yanlış) = P(L)S / [P(L)S + (1−P(L))(1−G)]
  - Ardından öğrenme adımı uygulanır: P(L) ← P(L|gözlem) + (1 − P(L|gözlem)) · T
- **Panellerde kullanımı:**
  - Konu ustalığı, ilgili yanılgıların ortalamasıdır.
  - En zayıf yanılgılar odak alanlarını ve önerileri belirler.
  - Günlük etkinlik GitHub tarzı takvimi ve seri (streak) bilgisini oluşturur.

## 11. Roller, veri ve güvenlik (accounts.py, db.py)
- **Roller:**
  - Öğrenci, öğretmenin verdiği sınıf koduyla sınıfa katılır.
  - Veli, öğrencinin aile koduyla çocuğuna bağlanır. Bir veli birden fazla çocuk izleyebilir.
- **Şifreler:** PBKDF2-HMAC-SHA256 ile 200.000 iterasyon ve 16 baytlık rastgele tuz kullanılır.
- **Oturumlar:** 32 baytlık rastgele bir anahtar oluşturulur ve çerezde saklanır.
- **Kodlar:** Karışmasın diye 0/O ve 1/I harfleri hariç tutulan 6 karakterli bir alfabeyle üretilir.
- **Veri:** Tüm veriler tek bir yerel SQLite dosyasında tutulur (`MISSTEP_DB` ile değiştirilebilir). Hiçbir veri dış bir servise gönderilmez. Bu, çocuk verisi ve KVKK açısından ürünün temel argümanıdır.

## 12. Değerlendirme
Değerlendirme seti `eval/cases.jsonl` dosyasında, `python -m misstep.evaluate` ile çalışır. Elle yazılmış **43 çözümden** oluşur:
- 10 doğru çözüm.
- 33 hatalı çözüm. Bunların 30'u adlandırılmış bir yanılgı içerir ve 13 yanılgının hepsini kapsar. Kalan 3'ü sıradan işlem hatasıdır.

Vakalar motor üzerinde çalıştırılmadan önce yazıldı ve sonuçları iyi göstermek için değiştirilmedi.

| Ölçüt | Sonuç |
|---|---|
| İlk hatalı adımı doğru bulma (43 vaka) | **%100** |
| Yanılgıyı doğru adlandırma, ilk tahmin (30 vaka) | **%97** (29/30) |
| Doğru çözümde yanlış alarm | **%0** |
| İşlem hatasında yanılgı uydurmama (3 vaka) | **%67** (2/3) |
| Ortalama süre | 774 ms / çözüm |

**Başarısız iki vaka** (her ikisi de raporda ve Hakkında sayfasında açıkça listelenir):
- `cancel-02`: Adım doğru bulundu, ancak ILLEGAL_CANCELLATION kuralı bu sadeleştirme biçimini üretemedi, bu yüzden yanılgı adlandırılmadı.
- `late-02`: Bir işlem hatası PARTIAL_BOTH_SIDES ile tesadüfen aynı satırı ürettiği için yanılgı olarak etiketlendi.

**Fotoğraf okuma:** `--photos` seçeneği, `eval/photos/` klasöründeki fotoğrafları Gemma ile okur ve elle yazılmış dökümle satır satır karşılaştırır. Bu set henüz oluşturulmadı, bu yüzden okuma doğruluğu için bir sayı verilmiyor.

## 13. Test
`pytest -q` ile 108 test yaklaşık 85 saniyede çalışır. Kapsadığı alanlar:
- Ayrıştırma, denklik ve her yanılgı kuralı.
- Karşı örnek, soru üretimi ve çeldiriciler.
- BKT, belge okuma ve parçalama.
- Web API: kayıt, giriş, roller, sınıf tablosu, PDF'ler, araştırma, Hata Avı.
- Sahte bir Ollama sunucusuyla model istemcisi senaryoları: başarı, eksik model, `think` seçeneğini reddeden eski sürüm ve kapalı servis.

## 14. Sınırlamalar
- **Kapsam:** Yalnızca 7–10. sınıf cebir ve tek değişkenli ifadeler ile denklemler. Eşitsizlikler, sistemler ve geometri yok.
- **Kural kütüphanesi kapalı bir küme:** 13 yanılgının dışındaki bir hata "işlem hatası" olarak görülür. Bu bilinçli bir tercih (uydurmamak), ama kapsamı sınırlar.
- **El yazısı okuma** Gemma'nın kalitesine bağlıdır. Okuma doğruluğu henüz ölçülmedi; öğrenci satırları düzenleyerek telafi eder.
- **İşlem hatası ve yanılgı ayrımı** %67'de kalıyor: bazı işlem hataları tesadüfen bir yanılgının ürettiği satırı veriyor.
- **Model gereksinimi:** Gemma'nın ilk yüklenmesi yavaş olabilir. Zayıf donanımda açıklama ve sohbet gecikir; teşhis ise modelden bağımsızdır.
- **Değerlendirme seti küçük (43 vaka)** ve yazarlar tarafından hazırlandı. Gerçek öğrenci verisiyle doğrulama henüz yapılmadı.

## 15. Sonraki adımlar
1. Gerçek el yazısı fotoğraflarıyla okuma doğruluğunu ölçmek (`--photos`).
2. Kural kütüphanesini kesirli denklemler, eşitsizlikler ve sistemlerle genişletmek.
3. Öğretmen paketi için okul sunucusuna kurulum ve çoklu sınıf desteği.
4. Pilot: bir özel ders öğretmeninin gerçek öğrencileriyle 2 haftalık kullanım.

## Kaynaklar
- Brown, J. S., & Burton, R. R. (1978). Diagnostic models for procedural bugs in basic mathematical skills. *Cognitive Science*, 2(2), 155–192.
- Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction*, 4, 253–278.
- Adams, D. M., McLaren, B. M., et al. (2014). Using erroneous examples to improve mathematics learning with a web-based tutoring system. *Computers in Human Behavior*, 36, 401–411.
- Große, C. S., & Renkl, A. (2007). Finding and fixing errors in worked examples: Can this foster learning outcomes? *Learning and Instruction*, 17(6), 612–634.
- Robertson, S., & Zaragoza, H. (2009). The probabilistic relevance framework: BM25 and beyond.
- Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. *SIGIR*.
