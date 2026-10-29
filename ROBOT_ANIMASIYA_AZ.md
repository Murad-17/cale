# ORION 0.5.6

## Canlı robot

Robotun ətrafındakı qara düzbucaqlı fon çıxarılıb. Gövdə həqiqi alfa kanallı
PNG-dir; gözlər, qaşlar və ağız onun üstündə ayrıca çəkilir və animasiya olunur.
Baş sadəcə yerində titrəmir: baxdığı istiqamətə dönür, gözünü qırpır, göz vurur,
sualda maraqlı, sevincli mətndə gülərüz, tapşırıq zamanı diqqətli ifadə alır.
Xəta olduqda narahat ifadə göstərir.

Yazarkən gözlər yazı sahəsindəki kursorun yerinə baxır. Kursoru mətnin başqa
yerinə qoyanda baxış da dəyişir. Yeni cavab görünəndə, yazmağa davam etmirsənsə,
robot görünən cavaba baxır. Çat tarixçəsi dolu olanda da başlıqda robot qalır.
Başın, gövdənin və üz işıqlarının çaları seçdiyin tema ilə birlikdə dəyişir.

Sistemdə azaldılmış hərəkət aktivdirsə, keçidlər və başın fırlanması dayandırılır;
baxış və vəziyyət dəyişiklikləri dərhal tətbiq olunur. Şrift Poppins-dir,
400/500/600/700 çəkiləri paketdədir; internet və ayrıca şrift quraşdırması lazım deyil.
Ə, ə, ğ, ı, İ, ş, ç, ö və ü hərfləri daxildir.

## Xərc üçün mənfi işarə

- “Xərclədim” və ana səhifədəki xərc kartını redaktə edəndə **-100** yaz: 100 AZN xərc göstərilir.
- Xərc yerinə **100** yazsan, qəbul edilmir və xərc cəmi dəyişmir.
- Məxaric əməliyyatında da **-100** yaz. Müsbət məbləğ mədaxil üçündür.
- Hesab/kredit bölməsinin **cari balansına -100** yazanda bu məbləğ xərc əməliyyatı kimi tarixçəyə düşür. Məsələn, “iPhone krediti” bölməsində aylıq ödənişi mənfi yazmaq olar.
- Həmin mənfi məbləği dəyişmək əlaqəli əməliyyatı yeniləyir; eyni rəqəmi təkrar saxlamaq yeni xərc yaratmır.
- Bölmənin müsbət cari məbləği qənaət/balans kimi qalır, xərcə daxil olmur.
- Əvvəlki versiyalarda qəbul edilmiş xərclər məlumat itirmədən mənfi yazılışa köçürülür.
- Başlanğıc balans, keçmiş əməliyyatlar və cari məbləğ fərqli sahələrdir. Cari məbləğdən sonra əlavə etdiyin əməliyyatlar hesabı yeniləməyə davam edir.

Ay, valyuta və gözlənilən/tamamlanmış statusu əvvəlki qaydada ayrıca hesablanır.
Mənfi məbləğin xərcə daxil olması üçün əməliyyat tamamlanmış olmalıdır.

## Bitmiş kredit bölməsini silmək

Hesab/kredit kartında qələmin yanında zibil qabı işarəsi var. Ona basıb
“Bölməni sil” seç. Kart seçilmiş aydan etibarən kartlardan və balans cəmindən
çıxarılır; onun keçmiş əməliyyatları və xərcləri tarixçədə qalır.

Səhvən silmisənsə Maliyyə səhifəsində **Silinmiş bölmələr** → bölməni seç →
**Geri qaytar** istifadə et. Yenidən açanda məlumatlar yerindədir.

## Quraşdırma

ORION-u sistem panelində “Tam çıxış” ilə bağla. Yeni proqram fayllarını və
panel_assets qovluğunu mövcud ORION qovluğuna köçür. Öz .env, .venv və məlumat
qovluğunu saxla. START.bat və ya START_TOP_PANEL.bat ilə aç.

Windows-un real masaüstü pəncərəsi bu Linux iş mühitində canlı yoxlanılmayıb.
Brauzer mühərrikində üz animasiyası, kursor izlənməsi, fayllar, çat, temalar və
dar ekranlar yerli sınaq serveri ilə yoxlanılıb. Ödənişli AI çağırışı edilməyib.

## Aktivlərin mənbəyi

- Şəffaf gövdə: panel_assets/orion-shell.png. Göndərilən robot əsasında built-in image_gen vasitəsi ilə hazırlanıb; orijinal dizayn istinad kimi saxlanılıb. Üz ifadələri robot_animator.js tərəfindən yaradılır.
- Poppins: Google Fonts / Indian Type Foundry. Şrift faylları panel_assets/fonts daxilindədir; OFL.txt lisenziyası eyni qovluğa daxildir. Mənbə: https://github.com/google/fonts/tree/main/ofl/poppins

Şəffaf gövdə üçün istifadə edilmiş prompt:

> Preserve the supplied ORION robot's rounded dark metallic headset, green rim lighting, earpieces, and tilted orbital ring. Remove the entire exterior black rectangle, green fog, floor and background shadow; use true transparent alpha. Remove only the eyebrows, eyes and mouth inside the visor, leaving clean blank glossy black glass for real-time facial animation. Keep the head front facing, centered, symmetrical, with the orbital ring fully in frame, no body, no text, no checkerboard and no new features.
