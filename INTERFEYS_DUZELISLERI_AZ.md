# ORION — interfeys və işləmə düzəlişləri

Mövcud ana ekran, temalar, yaşıl şüşə görünüşü, robot və proqramın bölmələri saxlanılıb.

## Nələr düzəldi?

- Kartların “⋯” menyusu redaktə, silmə və seçim düymələri ilə eyni yeri tutmur. Menyu kartın kənarında kəsilmir, ekranın daxilində açılır və Esc və ya kənara klik ilə bağlanır.
- 01 / 02 / 03 addım kartlarının menyuları kartın öz küncünə yerləşdirilib. Menyuya basmaq çata prompt əlavə etmir.
- Qeydin yoxlama siyahısına və menyusuna basmaq redaktə pəncərəsini açmır. Toxunma ilə idarə olunan düymələr sürüşdürmə əməliyyatını başlatmır.
- Qoşulmayan Blender, Roblox və Forge “Qoşuldu” kimi göstərilmir. Üst bağlantı sayı, kartlar və diaqnostika eyni statusdan istifadə edir.
- Tamamlanma faizi iş sahəsindəki qeydlərdən hesablanır. Serverin tapşırıq sorğuları bu faizi dəyişmir. Qrafik tamamlanma payını göstərir.
- Studiya, Köməkçilər və Tablarım birbaşa keçidlə və səhifəni yeniləyəndə düzgün açılır.
- Mülkü ayrıca tabda saxladıqdan sonra siyahını sıralamaq həmin tabı başqa mülklə əvəz etmir.
- Mövcud olmayan təqvim tarixləri qəbul edilmir.
- Dar ekranda maliyyə kartlarının redaktə düymələri mətnin üstünü tutmur. Üst robot panelinin dörd əsas əməli də dar görünüşdə əlçatandır.

## Yeni funksiyalar

- **İş sahəsində axtarış:** başlıqdakı böyüdücü ikon və ya **Ctrl / ⌘ + K**. Qeydlər, sual dəftəri, mülklər, əməliyyatlar, ödəniş planları və bölmələr axtarılır. Nəticə həmin qeydi açır. Axtarış bu cihazda aparılır.
- **Əməliyyatların hesab üzrə süzülməsi**, tamamlanmış/gözlənilən statusları və tarix və ya məbləğ üzrə sıralama.
- **Süzülmüş siyahının xülasəsi:** əməliyyat sayı, tamamlanmış mədaxil və məxaric, gözlənilən əməliyyat sayı.
- **CSV endir:** seçilmiş ay, valyuta və süzgəcdəki əməliyyatları UTF-8 faylına ixrac edir. Rəqəmlər və hesab adları daxil edilir.

## Quraşdırma

1. Saatın yanındakı ORION ikonundan **Tam çıxış** seç.
2. Arxivdəki bu dörd faylı mövcud ORION qovluğundakılarla əvəz et:
   `orion_dashboard.html`, `orion_big.js`, `orion_big.css`, `orion_panel.html`.
3. **START.bat** ilə yenidən aç.

Yeni Python asılılığı yoxdur. Şəxsi məlumat qovluğunu və öz `.env` faylını saxla.
Arxivdəki digər mövcud proqram faylları dəyişdirilməyib.

## Yoxlamalar

- 108 mövcud Python testi uğurla keçib: `python -m unittest discover -s tests -q`.
- Brauzerdə maliyyə cəmi, əməliyyat əlavə etmə, filtr, sıralama, CSV, axtarış, qeyd düymələri, saxlanmış mülk tabı və yaddaşın yenidən açılması yoxlanılıb.
- 1380, 1024, 768, 390 və 360 piksel enində 10 bölmə yoxlanılıb; səhifə səviyyəsində üfüqi daşma aşkarlanmayıb. Cədvəllər öz daxilində üfüqi sürüşür.
- Üst panel 740, 540, 390 və 360 piksel enində yoxlanılıb.
- Təkrar istifadə edilə bilən brauzer sınağı `tests/ui_smoke.cjs` faylındadır. Playwright və onun Chromium brauzeri quraşdırılmış mühitdə `node tests/ui_smoke.cjs` ilə işə salınır. Sınaq ayrıca müvəqqəti məlumat və brauzer yaddaşı istifadə edir.
- Canlı AI/video generasiyası və Windows-un native pəncərə görünüşü bu mühitdə yoxlanılmayıb.
