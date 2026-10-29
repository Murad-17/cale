# ORION — ekran fiquru və əlaqəli toplamlar

## Yeniləmə

1. Açıq ORION-un sistem panelindəki işarəsinə sağ klik et və **Tam çıxış** seç.
2. Yeniləmə ZIP-indəki `orion_dashboard.html`, `main.py`, `dashboard_bridge.py` və `orion_companion.py` fayllarını mövcud ORION qovluğuna köçür. Eyni adlı faylları əvəz et.
3. ORION-u `START.bat` ilə aç. API açarları və əvvəlki ayların məlumatları öz yerində qalır.
4. Masaüstü modulları əvvəldən qurulmayıbsa, əvvəl `INSTALL.bat`, sonra `START.bat` aç. Python-un Tcl/Tk komponenti qurulu olmalıdır; standart Windows Python quraşdırıcısında bu komponent var.

## Ekran fiquru

- Narıncı ORION fiquru ekranın kənarında görünür. Alt-Tab edəndə və əsas ORION pəncərəsini X ilə bağlayanda fiqur işləməyə davam edir.
- Fiqura bas: kiçik komanda çatı açılır. Komandanı yaz və Enter və ya Göndər seç. Çat mövcud ORION modeli və komanda sistemi ilə işləyir.
- Fiquru sürüşdürərək yerini dəyiş. Yeri növbəti açılış üçün saxlanır.
- Kiçik çatın X düyməsi yalnız çatı gizlədir; fiqur qalır. ↗ əsas paneli açır.
- Fiqura sağ kliklə çatı açmaq, əsas panelə keçmək və fiquru gizlətmək olar.
- Gizlədilmiş fiquru sistem panelində ORION menyusundan **Ekran fiqurunu göstər** seçərək geri gətir.
- Bütün ORION-dan çıxmaq üçün sistem panelində **Tam çıxış** seç. Bu, fiquru da dayandırır.
- Fiqursuz işə salmaq üçün `python main.py --desktop --no-companion` istifadə edilə bilər.

## Maliyyə

Manual hesab balansı həmin ayın əməliyyatlar üzrə balansına düzəliş sayılır: müsbət fərq gəlirə, mənfi fərq xərcə əlavə edilir. Başlanğıc balans gəlir sayılmır. Qənaət, ümumi balans, ana səhifə göstəriciləri və qrafiklər buna uyğun yenilənir.

Hesab balansını dəyişəndə həmin ay və valyuta üçün gəlir, xərc, qənaət, ümumi balans və bölgü faizinin köhnə manual üst yazmaları sıfırlanır ki, yeni toplamı gizlətməsin. Gəlir və ya xərci ayrıca dəyişəndə qənaət və bölgü yenidən hesablanır. Başqa ay və valyutalar ayrıca saxlanır.

## Narıncı timeline

Xətlər və parıltılar tam narıncıdır. Yeni görünüş ilk açılışda yüksək detallı keyfiyyətlə tətbiq olunur. Zəif cihazlarda axıcılığı qorumaq üçün təsvir ölçüsü yükə uyğun azalır. Keyfiyyəti Görünüş ayarlarından dəyişmək olar.

## Yoxlama

Maliyyə əlaqələri brauzerdə yoxlanılıb. Server və fiqurun komanda göndərməsi, cavab alması, uğursuz sorğuda mətnin qorunması, pəncərəni bağlama və tam çıxış davranışı üçün 18 avtomatlaşdırılmış yoxlama keçib. Real Windows pəncərəsinin ekranüstü görünüşü bu mühitdə yoxlanılmayıb.
