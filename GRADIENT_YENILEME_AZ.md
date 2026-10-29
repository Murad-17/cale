# ORION — Gradient və Ayarlar yeniləməsi

## Nə dəyişdi?

- Ayarlar üçün yenilənmiş, səliqəli masaüstü və mobil düzülüş.
- “İşıq kolleksiyası” bölməsində beş yeni rəng mövzusu: İnci işığı,
  Kobalt işığı, Mərcan alovu, Mavi laqun və Qütb parıltısı.
- Yumşaq alt işıq, parlaq incə kənarlar və mirvari gradient düymə.
- Seçilən rəngləri göstərən canlı önizləmə.
- Əvvəlki 12 palitra, axtarış, bütün ayar bölmələri və yadda saxlama saxlanılıb.
- Kiçik ekranlarda üfüqi sürüşən bölmə menyusu; klaviatura fokus göstəriciləri
  və azaldılmış hərəkət seçiminə uyğun davranış.

## Mövcud ORION-a tətbiq etmək

1. ORION-u sistem panelindən tam bağla.
2. Əvvəlki proqram qovluğunun ehtiyat nüsxəsini götür.
3. Yeni arxivdəki proqram fayllarını mövcud ORION qovluğuna köçür və eyni
   adlı proqram fayllarının əvəzlənməsinə icazə ver. `panel_assets` qovluğunu da
   daxil et — şriftlər oradadır.
4. Öz `.env`, `.venv` və şəxsi məlumatlarını saxla; onları silmə.
5. `START.bat` və ya `START_BROWSER.bat` ilə aç. Brauzer köhnə görünüşü
   göstərərsə `Ctrl + F5` bas.
6. **Ayarlar → Mövzular / Rənglər → İşıq kolleksiyası** bölməsindən mövzu seç.
   Seçim dərhal tətbiq olunur və bu cihazda yadda qalır.

Bu paket 0.6.0 tam mənbə arxividir. İnterfeys yeniləməsi ilə yanaşı, yerli
şriftlərin servis edilməsi, paketə daxil edilməsi və buraxılış adının göstərilməsi
düzəldilib. Yeni API açarı və ya Python paketi tələb olunmur. Əsas dəyişikliklər:
`orion_dashboard.html`, `orion_panel.html`, `orion_premium.css`,
`orion_premium.js`, `dashboard_bridge.py`, `updater.py`, `update_installer.py`
və `release_tools.py`. Buraxılış qeydləri `RELEASE_NOTES_AZ.md` faylındadır.

## Yoxlama

Playwright ilə mövzu seçimi və yenidən yükləmədən sonra saxlanması,
hover/klaviatura önizləməsi, axtarış, mövcud ayar bölmələri, yadda saxlama,
Escape ilə bağlama və 1440/1024/768/390/360 piksel enlərində düzülüş yoxlanıb.
Açıq palitra və 844 × 390 üfüqi ekran da ayrıca yoxlanıb.

Yeni brauzer yoxlaması: `node tests/ui_gradients.cjs`.
Sistem Chromium-u üçün `ORION_UI_CHROMIUM` yolunu göstərmək olar.

Mövcud Python testləri və buraxılış metadatası 0.6.0 ilə uyğunlaşdırılıb.
Windows masaüstü pəncərəsi bu Linux mühitində işə salınmayıb; interfeys yerli
backend və Chromium ilə yoxlanıb. Real AI, Blender, Roblox və mikrofon xidmətləri
istifadəçinin cihazında və uyğun xidmət bağlantıları ilə ayrıca yoxlanmalıdır.
