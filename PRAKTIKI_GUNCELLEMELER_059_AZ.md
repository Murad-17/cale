# ORION 0.5.9 — Praktiki güncəlləmələr

## Quraşdırma

1. Saatın yanındakı ORION ikonundan **Tam çıxış** seç.
2. Arxivdəki `ORION` qovluğunun proqram fayllarını mövcud ORION qovluğuna köçür. Öz `.env`, `.venv` və `yenileme_ehtiyat` qovluğunu saxla.
3. `password_meter.css`, `password_meter.js`, `orion_fonts.css` fayllarını və `panel_assets/fonts` qovluğunu da köçür. `top_panel.py` və `panel_window.py` mütləq yenilənməlidir: kapsulun həqiqi ölçüsü və küncləri buradan idarə olunur.
4. **START.bat** ilə yenidən aç. Ayarlar → Proqram yeniləmələri bölməsində **0.5.9** və **Praktiki güncəlləmələr** görünəcək.

Proqram fayllarını birlikdə yenilə. Yeni Python asılılığı yoxdur. Bu paket 0.5.9 üçün mini düzəlişləri də əhatə edir; buraxılış adı dəyişmir.

## Görünüş

- Əsas interfeys və chatbot göndərilmiş **Euclid Circular A** şriftindən istifadə edir. Beş qalınlıq, italic variantları və Azərbaycan hərfləri proqramla birlikdə saxlanılıb.
- Statistika kartlarında başlıq, qrafik, rəqəm və izah ayrı sətirlərdədir. Qrafiklər rəqəmlərə daşmır; rəqəmlər eyni səviyyədədir.
- Studiyadakı **01 / 02 / 03** nişanlarının artıq boşluğu silinib. Rəqəmlər öz çərçivəsində mərkəzdədir.
- Açıq və yığcam chatbotun kənarında **2 piksel kontur** və yumşaq parıltı var. Hər ikisi seçilmiş tema rəngini izləyir.
- Çatın bağlama düyməsi onu **300 × 56** ölçülü, qara, **dörd küncü 28 piksel yumru** yığcam kapsula çevirir. 32 × 32 ölçülü çat və genişləndirmə düymələri açıq qalır. Genişləndirəndə qaralama və əvvəlki görünüş bərpa olunur.
- Ana ekranın ikinci sətrində **“Xoş gəldin.”** yazılır.

## Giriş ekranının mini yeniləməsi

- Göndərilmiş vividsites Password Meter komponenti yerli giriş formasına uyğunlaşdırılıb. Komponentin `vs-password-meter-` sinifləri, animasiyaları, həqiqi input, paste, seçim və klaviatura davranışı qorunur.
- Həm girişdə, həm qeydiyyatda şifrəni göstər/gizlət düyməsi və Caps Lock xəbərdarlığı var.
- Profil yaradanda dörd hissəli güc göstəricisi, qayda işarələri və **təxmini** oflayn qiymətləndirmə görünür. Bu qiymət zəmanət deyil; əlavə qaydalar məcburi deyil. Minimum uzunluq əvvəlki kimi 8 simvoldur.
- Azərbaycan hərfləri böyük/kiçik hərf kimi tanınır, xüsusi işarə sayılmır. Hesablamalar üçün şifrə xarici xidmətə göndərilmir.
- Uğurlu giriş, qonaq keçidi və giriş ekranının bağlanması şifrə sahəsini və animasiya simvollarını təmizləyir.
- İnterfeys Euclid Circular A, şifrə simvolları isə yerli JetBrains Mono ilə göstərilir. JetBrains Mono lisenziyası `panel_assets/fonts/JetBrainsMono-OFL.txt` faylındadır.

## Robot

- Yüngül nəfəs və baş hərəkəti, daha canlı baxışlar və təbii göz qırpması.
- Boşdaykən qısa təbəssüm, göz vurma və baş işarələri; robotun üstünə basanda salamlaşma.
- Düşünmə, dinləmə və danışma mimikaları faktiki iş və səs statusuna bağlanıb.
- Robot görünməyəndə davamlı rəsm dövrü dayanır. Sistemin azaldılmış hərəkət seçimi nəzərə alınır.

## Yoxlama

- **110 Python testi** uğurla keçib.
- Əvvəlki maliyyə, axtarış, qeyd, tab və yaddaş ssenariləri brauzerdə yenidən yoxlanılıb.
- Şriftin bütün 10 variantı, rəqəm və nişanların mövqeyi, Yeniləmələr bölməsi, kontur, yığcam görünüş, qaralama və animasiya vəziyyətləri brauzerdə yoxlanılıb.
- Mini düzəlişlər üçün real yerli qeydiyyat, səhv və düzgün şifrə ilə giriş, kursoru qoruyan göstər/gizlət, Caps Lock, simvolların təmizlənməsi, üç tema, toxunma və azaldılmış hərəkət ssenariləri yoxlanılıb.
- 360, 390, 768, 1024 və 1380 piksel enləri əhatə olunub.
- Səs vəziyyətləri sınaqda əvəzlənib; canlı AI/video/səs sorğusu göndərilməyib. Windows-un native pəncərəsi Linux mühitində canlı yoxlanılmayıb; ölçü və kəsim müqavilələri test edilib.

Bu arxivdə 0.5.9 versiyası və onun buraxılış qeydləri var. Avtomatik internet yayımı üçün ayrıca HTTPS yeniləmə mənbəsində paket və manifest yerləşdirilməlidir; bu işdə xarici yeniləmə serverinə nəşr edilməyib.
