# 0.5.8 əlavəsi

Üst robotun ana görünüşündə və çat başlığında **Köməkçin** rejim seçimi var.
Orbit / Vector / Nova / Muse / Atlas seçimi əsas proqramın Köməkçilər səhifəsi
ilə sinxronlaşır. Ayrıca maliyyə və notepad tabları, video studiyası və yeni
mobil/giriş görünüşü üçün **BIG_UPDATE_058_AZ.md** təlimatına bax.

# ORION 0.5.7 — sağda açılan çat və canlı salamlaşma

## Bu buraxılışda

Ana görünüş **680 × 212** ölçülüdür və robot əvvəlkindən böyükdür. Ev, çat,
fayl, yeniləmə və ayar düymələri başlığın sağındadır. Robotun PNG gövdəsi,
üz animasiyası və panel rəngləri seçilmiş tema ilə birlikdə dəyişir.

**Çat aç** sağ kənarda **560 × 920** ölçülü pəncərə açır; ekran kiçikdirsə ölçülər
ekrana uyğun azalır. Profilindəki ad və günün saatına uyğun qarşılama, altı təklif
kartı, imkan düymələri və işıqlı yumru yazı sahəsi görünür. Çatın **×** düyməsi
kiçik paneli əvvəlki yerinə qaytarır. Yuxarı kənara sürükləyərək tab şəklində
yığmaq da mümkündür.

**Tarixçə** əvvəlki mesajları göstərir və gizlədir; söhbət məlumatları silinmir.
Təklif kartları mesajı yazı sahəsinə gətirir, özbaşına göndərmir. “Ətraflı araşdır”,
“Şəkil yarat” və “Video yarat” təsvir üçün başlanğıc mətn əlavə edir. Göndərmə
seçilmiş ORION modeli və mövcud alətləri ilə işləyir. “AI imkanları” hazırda qoşulu
imkanları göstərir. Şəkil, video və səs müvafiq açar/asılılıqlar olmadan aktiv
göstərilmir. “Səs” yalnız üzərinə basanda mövcud səsli komanda xidmətini işə salır.

## Əl işarəli salamlaşma

Robot salam verəndə göz və ağız yerinə visorun içində hərəkətli **əl işarəsi**
görünür. Baş yüngül salam hərəkəti edir. Bir neçə saniyədən sonra normal üz
ifadəsi qayıdır; yazmağa başlayanda robot dərhal mətn kursorunu izləməyə keçir.
Azaldılmış hərəkət seçimi olan sistemlərdə əl statik göstərilir.

Panel boş olanda və əvvəlki salamlaşmadan ən azı **90 dəqiqə** keçəndə kiçik
salamlama görünə bilər. Bu fasilə proqram yenidən açılanda da yadda qalır.
Qaralama, fayl, aktiv tapşırıq, səsli komanda və ya yeniləmə varsa avtomatik
salamlaşma göstərilmir. Bağladığın üst chatbot özü yenidən açılmır.

Üst paneldə **Ayarlar → Arada salamlaşma göstər** seçimi bunu açıb-söndürür.
**Salam ver** düyməsi nümunəni dərhal göstərir. Salamlaşmanı × və ya Escape ilə
bağlamaq olar; təxminən 7 saniyədən sonra özü əvvəlki görünüşə qayıdır. “Çata keç”
seçsən, söhbət açıq qalır.

Bu versiyada robotun gövdəsi həqiqi şəffaf PNG-dir. Gözlər, qaşlar və ağız canlı
animasiya olunur; baxış mətn kursorunu və gələn cavabı izləyir. Əsas interfeys və
üst chatbot kompüterdə quraşdırılmış Euclid Circular şriftini prioritet götürür.
Euclid Circular A/B adları və PostScript adları dəstəklənir. Şrift quraşdırılmayıbsa
Azərbaycan hərflərini dəstəkləyən, paketdəki Poppins ehtiyat olaraq işləyir.
Euclid-in öz şrift faylı bu paketə daxil deyil. Yeni xərc və silmə qaydaları
ROBOT_ANIMASIYA_AZ.md-dədir.

Bu versiyada chatbot artıq ayrıca masaüstü pəncərəsidir. Ekranın yuxarısında
ortalanır, digər adi proqram pəncərələrinin üzərində qalır və əsas ORION pəncərəsi
gizlədiləndə işləməyə davam edir. Tam ekranı özünə ayıran bəzi oyunlar sistemin
pəncərə üstünlüyünü məhdudlaşdıra bilər.

## Açmaq

1. Köhnə ORION-u saatın yanındakı ikonundan “Tam çıxış” ilə bağla.
2. Yeni ZIP-dəki proqram fayllarını mövcud ORION qovluğuna köçür.
   Öz .env faylını, .venv qovluğunu və məlumat qovluğunu saxla.
3. Yalnız üst chatbot üçün **START_TOP_PANEL.bat** aç.
   Əsas pəncərə və üst paneli birlikdə açmaq üçün əvvəlki **START.bat** da işləyir.
4. Yeni Python paketi tələb olunmur. Mövcud masaüstü asılılıqları qurulmayıbsa,
   həmin ORION qovluğunda INSTALL.bat işlət.

İşləyən ORION-un ikinci nüsxəsini açma. Paneli “×” ilə bağlamısansa:

- Əsas ORION-un yuxarı alət zolağında çat ikonuna bas.
- Yaxud Parametrlər → Ümumi və görünüş → “Chatbotu aktivləşdir” seç.
- Saatın yanındakı ORION ikonuna sağ klik → “Üst chatbot panelini göstər” də işləyir.

Panel artıq açıq, amma kiçildilmişdirsə, həmin düymələr onu böyüdür. Qaralaman və
seçdiyin fayllar saxlanır. Panelin fonu, mətnləri, vurğu işıqları və robotun rəng
çaları əsas ORION-da seçdiyin temaya avtomatik uyğunlaşır. Temanın üstünə sadəcə
siçan aparmaq əsas seçimi dəyişmir; seçmək üçün kliklə.

## Aylıq gəlir və hesablar

Ana səhifədə “Aylıq gəlir” və “Bu ay xərc” kartlarının qələm düyməsi var.
Məbləği yaz, Enter və ya ✓ ilə saxla. Maliyyə səhifəsində hesabları da eyni
qaydada redaktə et. Vergüllə və nöqtə ilə qəpik yazmaq olar.

Məbləği əl ilə yazmaq artıq gələcək əməliyyatları dondurmur. Məsələn, aylıq gəliri
1 000 AZN yazıb sonra 100 AZN tamamlanmış mədaxil əlavə etsən, 1 100 AZN görünür.
Hesabın cari balansını 500 AZN yazıb ona 100 AZN mədaxil etsən, balans 600 AZN olur.
Məxaric həmin hesabın balansını azaldır. Əməliyyatın redaktəsi və silinməsi də
cəmlərə təsir edir. Gözlənilən mədaxil tamamlanana qədər real gəlirə daxil olmur.

Əvvəlki əl ilə yazılmış məbləğlər saxlanır; sonrakı əməliyyatlar onların üzərindən
hesablanır. Mövcud əməliyyatlar ikinci dəfə əlavə olunmur. Boş məbləğ tam avtomatik
hesablama rejiminə qaytarır. Hesabların ümumi cəmi hesab kartlarından hesablanır.
Hər ay və valyuta ayrıca saxlanır; ana səhifənin xülasəsi həmişə cari ayı göstərir.

## İdarəetmə

- Robot göndərdiyin baş dizaynı əsasında hazırlanmış şəffaf gövdə və canlı üz ifadələrindən istifadə edir.
- Çat ikonuna basaraq əsas ORION ilə eyni AI modelinə və söhbət xidmətinə yaz.
- “+” və ya fayl düyməsi ilə şəkil, PDF, DOCX, mətn və kod faylı seç. Faylı panelə sürükləyib buraxmaq da mümkündür.
- Enter mesajı göndərir, Shift+Enter yeni sətir yaradır.
- Başlıqdan tutub ekranın yuxarı kənarına sürüklə: panel 252 × 44 ölçülü kiçik taba yığılır. Başlıqdakı yuxarı ox da bunu edir. Tab üst kənara birləşir; konturu və ikon düymələri seçilmiş temaya uyğunlaşır.
- Kiçik tabdakı aşağı ox əvvəlki görünüşü böyüdür. Çat və qaralama qaldığı yerdən davam edir. Tabı aşağı çəkmək də açır.
- Başlığın orta hissəsindən tutub paneli sürüklə. Ayarlar → “Yuxarıda ortala” başlanğıc mövqeyinə qaytarır. Kiçik tab vəziyyəti növbəti açılış üçün yadda saxlanır.
- Ana görünüşün başlığındakı “×” üst paneli gizlədir. Çatın “×” düyməsi kiçik panelə qaytarır; salamlaşmanın “×” düyməsi əvvəlki görünüşə qaytarır. ORION serveri işləməyə davam edir.
- “Əsas panel” tam ORION pəncərəsini açır. Tam çıxış sistem panelindəki ORION menyusundadır.
- Qaralama və seçilmiş fayllar cihazda saxlanır. Göndərmə rədd ediləndə silinmir.

## Yeniləmələr

İlk icazə, yeni versiya, həqiqi endirmə faizi, təkrar sınama, buraxılış qeydləri
və quraşdırma təsdiqi üst panelin daxilində göstərilir. Üst panel işləyəndə eyni
avtomatik bildiriş əsas pəncərədə təkrarlanmır. Üst panel bağlı olsa, əsas
pəncərə bildirişləri üzərinə götürür.

Endirmə zamanı çata keçmək olar: gedişat paneldə ayrıca kiçik zolaqda qalır.
Yeni versiyanın hazır olması yazılan mesajı bağlamır. Göndərilməmiş mətn,
seçilmiş fayl və ya işləyən tapşırıq varsa, yenidən başlatma dayandırılır.

**Rəsmi buraxılış ünvanı təqdim edilməyib.** Həqiqi gələcək yeniləmələrin
gəlməsi üçün YENILEME_053_AZ.md-dəki qayda ilə öz etibarlı HTTPS mənbəyini qoş.
Mənbə qoşulmayıbsa tətbiq bunu açıq göstərir. Yeni versiya və endirmə faizi uydurulmur.

## Texniki qeyd və yoxlamalar

Üst panel ayrıca pywebview prosesidir; əsas HTML səhifəsinin içində yerləşən
maket deyil. /panel ünvanı tək brauzerdə açılanda yalnız görünüş önbaxışıdır:
adi brauzer özünü digər proqramların üzərində saxlaya bilməz. Bunun üçün
START_TOP_PANEL.bat / START.bat ilə masaüstü rejimi istifadə et.

Windows-da real pəncərə frameless + always-on-top kimi yaradılır. Künclər
Həqiqi pəncərə koordinatları və DPI miqyası ilə 26 piksel radiusda
yuvarlaqlaşdırılır. Əlavə Windows kölgə çərçivəsi söndürülüb; tabın üstü düzdür.
Windows-da dəstəklənməyən
WebView şəffaflığına güvənilmir. Yerləşmə və ölçülər ekran sərhədlərinə uyğunlaşdırılır.

Python yoxlamaları:

```bash
python -m unittest discover -s tests -v
```

Avtomatlaşdırılmış yoxlamalar qaralama və faylların saxlanmasını, pəncərə
yaradılması parametrlərini, ekran sərhədlərini, bildiriş sahibliyini, yeniləməni
və məlumatların qorunmasını əhatə edir. Panel brauzer mühərrikində real yerli
serverlə masaüstü və dar ölçülərdə də yoxlanılıb. Ödənişli AI çağırışı edilməyib;
söhbət və buraxılışlar yerli sınaq nümunələri ilə yoxlanılıb.

Bu iş mühiti Linux-dur. Windows-un real pəncərəsi, ekran miqyası və Win32
yuvarlaqlaşdırması burada canlı yoxlanılmayıb. Windows-da nəticə ilə bağlı
problem olsa, companion.log və orion.log faylları diaqnostika üçün istifadə oluna bilər.


## Künc düzəlişini yükləyərkən

Əvvəlki ORION-u sistem panelindəki (tray) menyudan **Tam çıxış** ilə bağla. Pəncərənin X düyməsi əsas proqramı arxa planda saxlaya bilər. Yenilənmiş faylları köçürdükdən sonra **START.bat** aç. Beləliklə pəncərəni yaradan yeni kod da yüklənəcək.

## Açıq panelin küncləri və axıcılıq

Açıq panelin arxasında görünən boz düzbucaqlı qat brauzerin real ekran
koordinatlarına uyğun kəsilir. Windows-da host və WebView adi, qeyri-şəffaf
pəncərə kimi işləyir; yalnız künclər native pəncərə sərhədindən çıxarılır.
Əvvəlki rəng açarı və layered şəffaflıq klikləri arxadakı proqrama ötürə
bildiyi üçün çıxarılıb. Düymələr, mətn sahəsi və sürükləmə bölgəsi normal
siçan və klaviatura girişi qəbul edir. Yığılmış tabın üstü düz qalır.

Native ölçü və DPI dəyişən kimi sərhəd yenidən hesablanır. Windows-un əlavə
boz çərçivəsi söndürülüb. İstifadə məlumatlarına toxunulmur. Diaqnostika üçün
panelin vəziyyət faylının yanında **panel-window-status.json** yaranır; yalnız
pəncərə sərhədi, kəsim və giriş yoxlamasını saxlayır, söhbət mətnini saxlamır.

### Boz düzbucaqlı sistem fonu

Göndərilən diaqnostikada `clip: true` və `interactive: true` olduğu halda boz
künclər görünürdü. Paketdəki pywebview, Windows tünd temada olduqda,
`BrowserForm.update_title_bar_theme` daxilində ayrıca Mica sistem fonu
(`DWMWA_SYSTEMBACKDROP_TYPE = 38`, `DWMSBT_MAINWINDOW = 2`) aktivləşdirir.
Bu fon HWND-in öz məzmun kəsimindən ayrıca çəkilir; yalnız `shadow=False`
və künc regionunu dəyişmək həmin fonu söndürmür.

Üst panel indi ilk görünən kadrdan əvvəl `DWMSBT_NONE = 1` tətbiq edir və
Windows-un cavabını geri oxuyur. Pəncərə kitabxanasının tema yeniləməsindən
sonra da bu seçim saxlanır; əsas ORION pəncərəsinin temasına toxunulmur.
Çərçivənin müştəri sahəsinə uzanması sıfırlanır. Rəng açarı və klikləri
arxaya ötürən şəffaflıq tətbiq edilmir.

Diaqnostikada `revision: no-system-backdrop-20261023`, `dwm.backdrop_initial`,
`dwm.backdrop_current`, `dwm.backdrop_disabled` və `system_theme_guard` var.
Windows 11-də dəstəklənən sistem fonu üçün cari dəyər 1, söndürülmə yoxlaması
isə `true` olmalıdır. API-ni dəstəkləməyən Windows 10-da bu yoxlama `null`
göstərə bilər; adi künc kəsimi və kliklər işləməyə davam edir.

Bu düzəliş paketdəki həqiqi Windows backend koduna və göndərilən diaqnostikaya
əsaslanır. Avtomatik sınaqlar həmin fonun açılma/tema dəyişmə halını təkrar
yaradır; bu iş mühitində fiziki Windows ekranı mövcud deyil.

Söhbət açılarkən başqa bölməyə keçsən, gec gələn tarixçə cavabı artıq səni
məcburi çata qaytarmır. Yeni söhbət və bölmə keçidləri son seçiminə uyğun qalır.

Keçidlər 240 ms müddət və 60 FPS hədəfi ilə işləyir. Eyni kadrda ölçü və mövqe
birlikdə dəyişir, təkrarlanan ağır kəsim və brauzer sorğuları azaldılıb. Robotun
üzü hər kadrda lazımsız yenidən çəkilmir, baxış və mimikalar vaxt əsasında axıcı
dəyişir. Azaldılmış hərəkət seçimi qorunur. Faktiki FPS cihazdan və WebView-dən
asılıdır; bu paket Windows cihazında canlı ölçülməyib.

## Mərkəz → Statistika

Sol menyudakı **Statistika** bölməsi göndərilən sözləri, mesaj sayını, orta API
cavab müddətini və token sürətini göstərir. **Həftə**, **Ay** və **Hamısı**
düymələri işləyir. Qrafik saxlanmış mesajları günlər üzrə göstərir; uzun
tarixçədə həftə, ay və ya il üzrə qruplaşdırır. Kiçik bot, əsas ORION və səsli
komandaların payı ayrıca görünür. Statistika bütün yerli ORION istifadəsinə
aiddir; başqa proqramlarda yazdıqlarını izləmir. Məlumat yoxdursa sıfır və ya
“—” göstərilir. Nümunə rəqəm və hesablanmamış “qazanılan vaxt” göstərilmir.
