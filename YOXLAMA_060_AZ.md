# ORION 0.6.0 — yoxlama hesabatı

Bu paket istifadəçinin təqdim etdiyi mənbə arxivi üzərində hazırlanıb.
Yoxlamalar Linux mühitində, müvəqqəti profil və yerli test serveri ilə aparılıb;
şəxsi istifadəçi məlumatları və ödənişli AI əməliyyatları istifadə olunmayıb.

## Keçən yoxlamalar

- **Python: 112 test** — yaddaş, HTTP, xidmətlər, media növbəsi, masaüstü
  interfeys müqavilələri, yeniləmə paketləri, yol məhdudiyyətləri və bərpa.
- **Yeni Ayarlar testi: 8 yoxlama qrupu** — 5 yeni + 12 mövcud palitra;
  seçim, yenidən yükləmədən sonra saxlanma, ayrıca chatbot panelinə rəng ötürmə;
  müvəqqəti siçan/klaviatura önizləməsi; axtarış; mövcud ayar bölmələri;
  0.6.0 adı və real buraxılış qeydləri; beş ekran eni; yadda saxlama və Escape.
- **Mövcud iş axınları: 6 yoxlama qrupu** — node statusları, sabit qeyd faizi,
  maliyyə axtarışı/filtrləri, balans düzəlişi və yeni mədaxil, qeydlərin və
  maliyyənin yenidən yükləmədən sonra saxlanması, üç birbaşa keçid,
  10 bölmə × 5 ekran eni, chatbotun menyusu və qaralamasının qorunması.
- **Ayrıca görünüş yoxlamaları** — açıq palitra, 844 × 390 üfüqi ekran,
  masaüstü/mobil ekran görüntüləri, HTML daxilindəki bütün skriptlərin sintaksisi.
- **Arxiv** — fayl siyahısı, ZIP bütövlüyü, 0.6.0 versiyası və mənbə fayllarına
  uyğunluq yoxlanıb. `.env`, `.venv`, `.git` və keşlər arxivə daxil edilməyib.

## Köhnə testlərlə bağlı aşkar edilmiş uyğunsuzluqlar

- `tests/ui_smoke.cjs` faylının yeni node və qeyd-faiz yoxlamaları keçir;
  daha sonrakı addım bu mənbədə olmayan `#osTransactionAccount` nəzarətini
  gözləyir. Bu və onun ardınca həmin ssenaridəki addımlar uğurlu sayılmır.
- `tests/ui_mini_update.cjs` mənbədə inteqrasiya edilməmiş
  `#bigEntryPasswordMeter` komponentini gözləyir və vaxt limitinə çatır.
  Ondan sonrakı addımlar icra olunmayıb. Şifrə göstəricisinin mövcud CSS/JS
  fayllarının servis və paket dəstəyi düzəldilib; giriş formasına yeni şifrə
  komponenti bu dizayn işində əlavə edilməyib.
- `tests/ui_practical.cjs` şriftlər, beş ölçüdə qrafik/rəqəm düzülüşü, studiya,
  0.6.0 məlumatları, chatbot konturu və qaralamanın qorunmasını yoxlayıb.
  Sonrakı köhnə yoxlama robotun cari API-sində olmayan `state().activity`
  sahəsini gözlədiyi üçün uğursuzdur; ondan sonrakı azaldılmış hərəkət
  yoxlaması həmin ssenaridə icra olunmayıb.
- Brauzerin avtomatik istədiyi `/favicon.ico` ilkin paketdə də yoxdur (404).
  Bu xəbərdarlıq yeni testdə ayrıca qeydə alınır; başqa uğursuz tətbiq HTTP
  sorğuları və JavaScript xətaları qəbul edilmir.

## Bu mühitdə yoxlanmayanlar

Windows-un həqiqi native pəncərəsi, sistem paneli, cihazın mikrofonu/oyatma
sözü, Blender/Roblox daxilində real əmrlər və real AI/media provayderləri həmin
cihazda, uyğun tətbiq və hesablarla ayrıca yoxlanmalıdır. Python testlərində
bu sistemlərin bir hissəsi saxta cavablar və interfeys müqavilələri ilə sınaqdan
keçirilib; bu, həqiqi cihaz testini əvəz etmir.

Yeni dizayn yoxlaması: `node tests/ui_gradients.cjs`.
Mövcud iş axınlarının yoxlaması: `node tests/ui_release_060.cjs`.
Python: `python -m unittest discover -s tests -p "test_*.py"`.
Brauzer ssenariləri ayrıca Playwright tələb edir; proqramın normal işi üçün
Playwright quraşdırmaq lazım deyil.
