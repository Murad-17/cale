# ORION 0.5.8 — Big Update

## Quraşdırma

1. Saatın yanındakı ORION ikonundan **Tam çıxış** seç.
2. Arxivdəki proqram fayllarını və `panel_assets` qovluğunu mövcud ORION qovluğuna köçür.
3. Öz `.env`, `.venv` və istifadəçi məlumat qovluğunu saxla.
4. **START.bat** ilə aç. Yalnız üst robot üçün **START_TOP_PANEL.bat** də işləyir.

Əvvəlki maliyyə məlumatları, mənfi xərc qaydası, hesab/kredit bölmələri, qeydlər,
şəxsi mövzular və AI parametrləri saxlanır. Yeni Python asılılığı əlavə edilməyib;
şəkil hazırlığı mövcud masaüstü paketindəki Pillow-dan istifadə edir.

## Daha yığcam ana səhifə

Ana səhifədə əsas rəqəmlər, balans qrafiki, son əməliyyatlar, gələcək ayın planı
və qənaətin dəyişimi görünür. Aşağıdakı **Yaradıcı axınını kəşf et** sətri əlavə
detalları açır. Naviqasiyada Maliyyə, İş sahəsi, Studiya və Köməkçilər ayrıdır.
**Daha çox** menyusunda Tablarım, Sual dəftəri, Mülklər, Statistika, Profil və
Ayarlar var. İkonlar şüşə görünüşü və seçilmiş temanın rəngindən istifadə edir.

## Şəkil + prompt → video

**Studiya** bölməsində:

1. PNG, JPEG və ya WebP şəkli seç; sürükləyib buraxmaq da olar. Limit 20 MB və 25 meqapikseldir.
2. Hərəkəti təsvir et. Şəkilsiz də yalnız təsvirlə başlamaq olar.
3. 5 və ya 10 saniyə, üfüqi 16:9 və ya şaquli 9:16 formatını seç.
4. **Videonu yarat** düyməsinə bas.

Video **Runway Gen-4.5** ilə hazırlanır. Studiyanın altındakı **Video xidmətini
qoş** sətrini açıb Runway API açarını daxil et. Açar yalnız istifadəçi məlumat
qovluğundakı yerli yaddaşda saxlanır və brauzerə geri göndərilmir. İstəsən mövcud
`.env` daxilində `RUNWAYML_API_SECRET` istifadə edə bilərsən; mühitdəki açar üstünlük təşkil edir.

**Generasiya xarici xidmətdə ödənişlidir.** Yalnız “Videonu yarat” düyməsinə basmaq
sorğu göndərir. Fayl seçmək, prompt yazmaq və açarı saxlamaq generasiya başlatmır.
Açarı saxlamaq hesabın balansını və modelə çıxışını təsdiqləmir; bunlar faktiki
sorğu zamanı xidmət tərəfindən yoxlanılır.

Eyni anda bir video sorğusu qəbul olunur. Xidmət faiz bildirirsə həmin rəqəm
göstərilir; bildirmirsə status və faizsiz hərəkətli göstərici görünür. Proqram
arxa planda işlədikcə nəticə yoxlanılır. Bağlantı kəsiləndə sorğunun identifikatoru
saxlanır, ikinci ödənişli sorğu avtomatik yaradılmır. ORION-u yenidən açmaq və
ya səhifəni yeniləmək davam edən videonu təkrar göndərmir.

Hazır MP4 cihazda saxlanır, studiyada açılır və endirilir. Son təsvir və seçilmiş
şəkil də qalır. Əvvəlki Sora tapşırıqları yeni tamamlanmış video kimi göstərilmir:
Sora API-si 24 sentyabr 2026-da bağlandığı üçün onlar aydın xəta vəziyyəti alır.

Texniki mənbələr:
- https://docs.dev.runwayml.com/guides/using-the-api/
- https://docs.dev.runwayml.com/assets/inputs/
- https://developers.openai.com/api/reference/resources/videos/methods/create

## Maliyyə: üç daxili səhifə

### Xülasə

Əvvəlki hesablar, mədaxil və məxaric, tarixçə və aylıq redaktə bu səhifədədir.
Tamamlanmış yeni əməliyyatlar əl ilə yazılmış məbləğləri yeniləməyə davam edir.
Xərc üçün **−100** kimi mənfi məbləğ istifadə et. Silinmiş hesabların əvvəlki
əməliyyatları tarixçədə qalır.

### Plan və qəbzlər

Kredit, abunəlik, alış və digər gələcək ödəniş üçün plan əlavə et. Tarix, məbləğ,
valyuta, kateqoriya və təkrarı seç. Plan birdəfəlik və ya aylıq ola bilər; son ay
boşdursa aylıq plan davam edir. Ayın 29–31-i qısa aya düşəndə həmin ayın son günü
istifadə olunur.

Ayları oxlarla dəyişərək nə qədər ödəniş planlaşdırdığını gör. Sağdakı şəxsi qəbzdə
sətirlər, planın cəmi, qeyd edilmiş ödənişlər və qalan plan görünür. **Qəbzi endir**
mətn faylı saxlayır. Bu şəxsi plan qeydi bank və ya vergi qəbzi deyil.

Plan əlavə etmək faktiki xərc yaratmır. **Ödənişi qeyd et** seçib mənfi məbləği,
faktiki tarixi və hesabı təsdiqləyəndə bir tamamlanmış məxaric əlavə olunur. Eyni
planın eyni ay ödənişi təkrarlanmır. Faktiki tarix fərqli aydadırsa xərc həmin
faktiki ayda hesablanır; planın öz ayındakı qəbzdə ödənildiyi görünür. Planı silmək
keçmiş ödənişi silmir. Əməliyyatı tarixçədən silsən, həmin plan ödənişi yenidən
qeyd edilə bilən vəziyyətə qayıdır.

### Müqayisə və proqnoz

Saxlanılan məbləğ və xərc əvvəlki ayla müqayisə olunur. Məsələn, əvvəl 100 AZN,
indi 200 AZN saxlanılıbsa dəyişmə **+100%** olur. Əvvəlki məbləğ 0-dırsa faiz
uydurulmur; baza olmadığı göstərilir. Aylar və valyutalar qarışdırılmır.

Cari ayın xərc məbləği keçən günlərə bölünərək ay sonuna təxmini uzadılır. Bu,
daxil etdiyin məbləğin ay ərzində bərabər tempdə yığılması fərziyyəsinə əsaslanır;
yeni əməliyyat və ya əl ilə redaktə proqnozu dəyişir. Keçmiş ay üçün faktiki yekun,
gələcək ay üçün isə yalnız planlaşdırılmış ödənişlər göstərilir.

## Ayrıca tablar və notepad

Kartın küncündəki **⋯ → Tab kimi saxla** menyusunu seç. Hesablar, statistika,
qeydlər və qəbzlər ayrıca açıla bilər. Studiya kartlarından birini seçmək tam,
işlək studiyanı ayrıca açır. **Daha çox → Tablarım** saxlanılan tabları göstərir.
**Boş notepad** ilə ayrıca mətn qeydi yaratmaq olar.

START.bat ilə masaüstü rejimdə bu pəncərələr digər adi pəncərələrin üstündə qalır,
yerini və ölçüsünü sistem pəncərəsinin kənarlarından dəyişmək olur. Əsas ORION-u
gizlətsən tablar işləməyə davam edir. Brauzer rejimində ayrıca brauzer pəncərəsi
açılır; brauzer onu başqa proqramların üzərində məcburi saxlaya bilmir.

Kart eyni iş sahəsinin canlı məlumatından göstərilir. Ayrıca hesab kartındakı
redaktə əsas maliyyəyə də tətbiq olunur. Müasir brauzer/WebView-də paralel yazılar
Web Locks ilə növbələnir, fərqli qeyd və əməliyyatların dəyişiklikləri birləşdirilir.
Notepad yazarkən saxlanır və saxlanma vəziyyəti görünür. Tab siyahısından çıxarmaq
əsas hesabı, qeydi və ya əməliyyatı silmir. Yeniləmənin təhlükəsiz yenidən başlatma
yoxlaması açıq tabdakı redaktələri də nəzərə alır.

## Beş köməkçi rejimi

- **Orbit:** gündəlik suallar və rahat söhbət.
- **Vector:** kod, texniki izah və yoxlama.
- **Nova:** dərin araşdırma və mənbələrin müqayisəsi.
- **Muse:** qrafik, motion və 3D yaradıcılığı.
- **Atlas:** prioritet, vaxt və şəxsi büdcə planı.

Bunlar seçilmiş AI modelinin davranış rejimləridir; ayrı model abonentliyi və ya
beş fərqli provayder deyil. **Rahat / Diqqətli / Enerjili** ünsiyyət tempi də seçilir.
Nova araşdırma üçün mövcud internet alətini istifadə edir; internet seçimi sönübsə
özbaşına aktivləşdirmir. Seçim və temp yadda qalır, əsas və üst chatbot arasında
sinxronlaşır. Şəxsi sistem təlimatı, yaddaş və dil seçimi qorunur.

Köməkçilərin fərqli cizgiləri, göz qırpması və yüngül hərəkətləri var. Üst robotun
kursoru izləməsi, üz ifadələri və əl işarəli salamlaşması da qalır. Sistem
azaldılmış hərəkət istəyirsə yeni animasiyalar dayandırılır.

## Şəxsi aktivlik

Statistika bölməsində son 12 həftənin günlər üzrə fəaliyyət xəritəsi var. Bu,
şəxsi qeydlərindən hesablanır. Nümunədəki müştəri qruplarının geri qayıtma
statistikası ORION-un şəxsi iş sahəsinə uyğun olmadığı üçün istifadəçi və ya
müştəri rəqəmləri uydurulmur.

## Mobil görünüş və giriş

Ana səhifə, studiya, maliyyə səhifələri, köməkçilər və Tablarım dar ekranlarda
uyğunlaşır. Mobil menyu altdadır, saxlanılan tablar yumru şüşə üslublu kartlar
kimi sıralanır. Bu buraxılış ayrıca APK/IPA yaratmır.

Yaşıl işıq və hərəkətli orbitləri olan giriş ekranı kompüterdə və mobil ölçüdə
mövcuddur. **Profil yarat / Daxil ol** bu cihazdakı bir şəxsi iş sahəsi üçündür.
İlk dəfə profil yaratmadan davam etmək mümkündür. Mövcud məlumatlar sıfırlanmır.
Profil şifrəsi ayrıca təsadüfi duz ilə PBKDF2-SHA256 həşi kimi saxlanır; şifrə
mətninin özü saxlanmır. Giriş sessiyası HTTP-only cookie ilə 8 saat işləyir və
server yenidən başladıqda təkrar giriş tələb olunur.

Bu giriş bulud hesabı, e-poçt təsdiqi, diskin şifrlənməsi və ya localhost API-si
üçün ayrıca icazə sərhədi deyil. Mövcud ORION kimi bu server yalnız yerli cihazda
və əməliyyat sistemi istifadəçisi daxilində işləmək üçündür. Şəxsi profil şifrəsi
qoymaq məlumat qovluğunu və disk fayllarını şifrləmir.

## Yoxlama

ORION qovluğunda:

```bash
python -m unittest discover -s tests -v
```

60 Python testi, yerli serverlə brauzer sınaqları və 360/390/768 piksel səhifələr
əhatə olunub. Maliyyə, planın təkrarsız ödənilməsi, qəbz, giriş, rejimlər, paralel
tab redaktəsi, notepad, şəkil yüklənməsi, video vəziyyətləri və əvvəlki robot
funksiyaları yoxlanıb. Video xidmətinin cavabları sınaqda əvəz edilib; canlı
ödənişli Runway generasiyası edilməyib. Real Windows pəncərələri və ekran DPI-si
bu Linux mühitində canlı yoxlanmayıb; native pəncərə müqavilələri mock ilə yoxlanıb.
# Görünüş düzəlişi

- Əvvəlki ana ekran ilk açılışda görünür: saatdan asılı çoxdilli salamlaşma, klaviatura yazı effekti, yazı sahəsi və üç yaradıcı kart saxlanılıb. Əlavə dashboard detalları aşağı sürüşdürəndə açılır.
- Kompüterdə əsas menyu yenidən soldadır. Telefonda mövcud yığcam alt menyu saxlanılıb.
- Kartlarda və çatda tema rənginə uyğun şəffaf şüşə səthi, incə neon kontur, yumşaq işıqlanma və yuvarlaq künclər var.
- Çat pəncərəsinin fonu və üst panelin səhifəsi də künclər üzrə kəsilir. Üst panelin Windows kəsimi səhifə yüklənəndən sonra yenidən tətbiq olunur.
- Orbit, Vector, Nova, Muse və Atlas ORION-un eyni şəffaf robot başlığından istifadə edir; rəngləri, LED mimikaları və baxış animasiyaları fərqlidir.
- Mövcud məlumatlar, maliyyə hesablamaları, ayrıca tablar və digər v0.5.8 funksiyaları qorunub.

# AI bağlantı xətalarının dəqiqləşdirilməsi

- HTTP 400 avtomatik olaraq internet alətinin problemi kimi təqdim edilmir. Xidmətin cavabı tanınan səbəb bildirirsə, API balansı, xərc limiti, model, açar, temperatur və digər uyğunluq xətaları ayrıca izah olunur.
- Xidmətin xam cavabı, API açarı, şəxsi mesajı və fayl mətni xəta bildirişinə çıxarılmır. Yalnız sabit izah, tanınan xəta kodu və yoxlanmış sorğu ID-si göstərilir. Səbəb tanınmırsa, proqram bunu özündən uydurmur.
- Müasir Claude modellərinə dəstəklənməyən temperatur parametri göndərilmir. Köhnə uyğun modellərdə ayrıca aktivləşdirilmiş ayar saxlanılır.
- Tək faylla göndərilən mesajlarda boş mətn bloku yaradılmır.
- Model yerinə API açarı daxil edilərsə, o, seçim siyahısında göstərilmir və API-yə model kimi göndərilmir. Əvvəldən səhv model sahəsində saxlanmış açar həmin sahədən çıxarılır.
- Öz kompüterində yeniləmək üçün `engine.py` və `orion_http.py` fayllarını dəyişmək kifayətdir. Şəxsi `.env` faylını saxla; ORION-u tam bağlayıb yenidən başlat. Yeni sorğunun xəta mətni göstəriləcək, əvvəlki tarixçə dəyişdirilmir.
- Həqiqi hesabın balansı və model icazələri burada canlı yoxlanılmayıb. Avtomatik ödəniş və ya əlavə ödənişli sınaq sorğusu göndərilmir.

# Seçilmiş köməkçinin panel ikonu və Windows küncləri

- Üst paneldə köməkçini seçəndə əsas robot, başlıqdakı kiçik ikon, çat robotu, kiçik tab, salamlaşma və yeniləmə görünüşləri həmin köməkçinin rəngini alır. Muse çəhrayı, Vector mavi, Nova bənövşəyi, Atlas sarı, Orbit mint rəngindədir.
- İkonun rəngi köməkçinin seçimindən gəlir; panelin fonu və düymələri seçilmiş tətbiq temasına uyğun qalır. Seçim yenidən açılışda da bərpa olunur.
- Kod köməkçisinin düz LED gözləri, yaradıcı köməkçinin göz vurması və araşdırma köməkçisinin maraqlı baxışı var. Kursoru izləmək, yazıya baxmaq və əl ilə salam vermək qorunur.
- Windows WinForms mühitində yalnız HTML yox, pəncərənin özü də GUI axınında saxlanılan `Control.Region` ilə yumrulaşdırılır. Bu, WebView-in arxasındakı səthi də kəsir. Digər Windows rendererləri üçün əvvəlki Win32 üsulu saxlanılıb.
- Kiçik tabın yuxarısı düz, aşağı küncləri yumrudur. DPI ölçüsü və görünüş dəyişmələri nəzərə alınır.
- 70 proqram testi və brauzerdə bütün köməkçilərin rəngi, saxlanılması, tema dəyişikliyi, yazı baxışı və kiçik tab yoxlanılıb. Həqiqi Windows masaüstü pəncərəsinin görünüşü bu mühitdə canlı yoxlanılmayıb.
- Bu düzəliş üçün ORION-u tam bağlayıb `top_panel.py`, `robot_animator.js`, `orion_modes.js` və `orion_big.css` fayllarını yenilə. Öz `.env` faylını və şəxsi məlumatlarını saxla, sonra `START.bat` ilə aç.

