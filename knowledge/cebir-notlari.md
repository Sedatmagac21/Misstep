# Misstep cebir konu notları
Her bölüm bir kavram yanılgısını anlatır. Başlıktaki kimlik, bugs.py içindeki kural kimliğiyle aynıdır.

## SIGN_DISTRIBUTION | Parantez önündeki eksi işareti
Parantezin önündeki eksi, parantezi −1 ile çarpmak demektir. Bu yüzden parantezin içindeki **her** terimin işareti değişir: −(a + b) = −a − b ve −(a − b) = −a + b.
Neden yanlış: −(x + 3) yazıp sadece x'in işaretini değiştirmek, −1'i yalnızca ilk terimle çarpmak anlamına gelir. Dağılma özelliği her terime uygulanmalıdır.
Sayıyla kontrol: x = 2 için −(2 + 3) = −5, ama −2 + 3 = 1. İki sonuç farklı olduğu için −(x + 3) ≠ −x + 3.
İpucu: Parantezi açmadan önce eksiyi "−1·" olarak yaz, sonra −1'i her terimle tek tek çarp.

## PARTIAL_DISTRIBUTION | Dağılma özelliği
k(a + b) = ka + kb. Parantezin önündeki çarpan, parantezin içindeki **bütün** terimlerle çarpılır.
Neden yanlış: 2(x + 3) = 2x + 3 yazmak, 3'ün 2 ile çarpılmasını unutmaktır. Alan modeliyle düşün: eni 2, boyu x + 3 olan dikdörtgenin alanı 2x + 6'dır.
Sayıyla kontrol: x = 1 için 2(1 + 3) = 8, ama 2·1 + 3 = 5.
İpucu: Çarpanından her terime bir ok çiz ve her oku bir çarpma işlemi olarak yaz.

## SQUARE_OF_SUM | İki terim toplamının karesi
(a + b)² = (a + b)(a + b) = a² + 2ab + b². Ortadaki 2ab terimi, iki çarpanın "çapraz" çarpımlarından gelir.
Neden yanlış: Üs, toplama üzerine dağılmaz. (a + b)² ≠ a² + b².
Sayıyla kontrol: (2 + 3)² = 25, ama 2² + 3² = 13. Aradaki 12, 2·2·3 = 2ab'dir.
İpucu: Kareyi (a + b)(a + b) şeklinde iki çarpan olarak yaz ve dört çarpımı tek tek yap.

## POWER_RULES | Üslü ifadelerde çarpma ve kuvvetin kuvveti
Aynı tabanlı üslü ifadeler çarpılırken üsler **toplanır**: xᵃ · xᵇ = xᵃ⁺ᵇ. Bir kuvvetin kuvveti alınırken üsler **çarpılır**: (xᵃ)ᵇ = xᵃᵇ.
Neden yanlış: x² · x³ = (x·x)·(x·x·x) = x⁵. Beş tane x çarpılıyor, altı değil.
Sayıyla kontrol: 2² · 2³ = 4 · 8 = 32 = 2⁵, ama 2⁶ = 64.
İpucu: Emin değilsen üsleri açıp x'leri say.

## LIKE_TERMS_POWER | Benzer terimleri toplama
Benzer terimler toplanırken katsayılar toplanır, değişken ve üssü aynen kalır: ax + bx = (a + b)x.
Neden yanlış: 2x + 3x, "2 tane x ile 3 tane x" demektir, yani 5 tane x: 5x. x², x'in kendisiyle çarpımıdır ve toplama ile oluşmaz.
Sayıyla kontrol: x = 2 için 2·2 + 3·2 = 10 = 5·2, ama 5·2² = 20.
İpucu: Değişkeni bir nesne gibi düşün: 2 elma + 3 elma = 5 elma, "5 elma kare" değil.

## COMBINE_UNLIKE | Benzer olmayan terimler
Sadece aynı değişkeni ve aynı üssü taşıyan terimler toplanabilir. 2x + 3 ifadesi daha fazla sadeleşmez.
Neden yanlış: 2x + 3 = 5x yazmak, sabit sayıyı x'li terim gibi saymaktır.
Sayıyla kontrol: x = 2 için 2·2 + 3 = 7, ama 5·2 = 10.
İpucu: Terimleri türlerine göre renklendir: x'liler bir renk, sabitler başka bir renk. Sadece aynı renkler toplanır.

## ILLEGAL_CANCELLATION | Kesirlerde sadeleştirme
Sadeleştirme yalnızca pay ve paydanın **ortak çarpanları** arasında yapılır. Paydaki bir **terim** paydayla sadeleşmez: (x + 3)/3 = x/3 + 3/3 = x/3 + 1.
Neden yanlış: (x + 3)/3 = x yazmak, bölmeyi yalnızca 3'e uygulamaktır. Payda, payın tamamını böler.
Sayıyla kontrol: x = 6 için (6 + 3)/3 = 3, ama sonuç x = 6 olurdu.
İpucu: Önce payı çarpanlarına ayır. Ortak çarpan yoksa sadeleştirme de yoktur.

## ADD_FRACTIONS | Kesirlerle toplama
Kesirler toplanırken önce paydalar eşitlenir: a/b + c/d = (ad + bc)/(bd). Paylar ve paydalar ayrı ayrı toplanmaz.
Neden yanlış: x/2 + x/3 = 2x/5 yazmak, payları ve paydaları ayrı ayrı toplamaktır.
Sayıyla kontrol: 1/2 + 1/3 = 5/6, ama (1 + 1)/(2 + 3) = 2/5. Yarım ile üçte birin toplamı yarımdan küçük olamaz.
İpucu: Denklemde kesir varsa, her terimi paydaların EKOK'u ile çarpıp kesirlerden kurtul.

## SQRT_OF_SUM | Toplamın karekökü
Karekök çarpma üzerine dağılır (√(ab) = √a·√b), ama toplama üzerine dağılmaz: √(a + b) ≠ √a + √b.
Neden yanlış: √(9 + 16) = √25 = 5, ama √9 + √16 = 7.
İpucu: Önce kökün içini hesapla, sonra kökü al.

## MOVE_WITHOUT_SIGN_CHANGE | Terimi eşitliğin diğer tarafına geçirme
"Karşıya geçirme" aslında eşitliğin iki tarafına aynı işlemi yapmaktır. x + 3 = 7 denkleminde iki taraftan 3 çıkarılır: x = 7 − 3.
Neden yanlış: Terimi işaretini değiştirmeden geçirmek, bir tarafa 3 ekleyip diğer taraftan 3 çıkarmak gibidir. Terazinin dengesi bozulur.
Sayıyla kontrol: x + 3 = 7 için x = 10 bulunursa 10 + 3 = 13 ≠ 7.
İpucu: "Geçirmek" yerine "iki tarafa da aynı işlemi yapmak" diye düşün ve işlemi iki tarafa da yaz.

## WRONG_INVERSE_OPERATION | Katsayıyı karşıya geçirme
3x = 12, "3 çarpı x" demektir. Çarpmanın tersi bölmedir: iki taraf 3'e bölünür ve x = 12/3 = 4 olur.
Neden yanlış: x = 12 − 3 yazmak, çarpma ile toplamayı karıştırmaktır. x = 12·3 yazmak ise ters işlem yerine aynı işlemi yapmaktır.
Sayıyla kontrol: x = 9 bulunursa 3·9 = 27 ≠ 12.
İpucu: Kendine sor: "x'e ne yapılmış?" Çarpılmışsa böl, eklenmişse çıkar.

## PARTIAL_BOTH_SIDES | Eşitliği bir sayıyla bölme veya çarpma
Eşitliği bir sayıyla bölerken iki taraftaki **her terim** bölünür: 2x + 4 = 10 ⇒ x + 2 = 5.
Neden yanlış: 2x + 4 = 10 ⇒ x + 4 = 5 yazmak, sol taraftaki 4'ü bölmeyi unutmaktır.
Sayıyla kontrol: x = 1 bulunursa 2·1 + 4 = 6 ≠ 10.
İpucu: Önce sabit terimi karşıya at (2x = 6), sonra böl (x = 3). Böylece bölmen gereken tek bir terim kalır.

## LOSE_NEGATIVE_ROOT | Kare alan denklemlerde iki kök
x² = 9 denkleminin iki çözümü vardır: x = 3 ve x = −3, çünkü (−3)² = 9.
Neden yanlış: Karekök almak yalnızca pozitif kökü verir. Denklemi çözerken x = ±√9 yazılmalıdır.
Sayıyla kontrol: (−3)² = 9, yani −3 de denklemi sağlıyor.
İpucu: x² = a (a > 0) gördüğünde iki cevap ara. İstersen x² − 9 = 0 yazıp (x − 3)(x + 3) = 0 şeklinde çarpanlarına ayır.

## GENEL | Denklem çözmenin altın kuralı
Denklem bir terazidir. Bir tarafa ne yapıyorsan diğer tarafa da aynısını yapmalısın: aynı sayıyı ekle, çıkar, sıfır olmayan aynı sayıyla çarp veya böl. Her adımda yeni denklem öncekiyle aynı çözüme sahip olmalıdır.
Kontrol yöntemi: Bulduğun cevabı ilk denklemde yerine koy. İki taraf eşit çıkmıyorsa bir adımda hata vardır.
