# ORION 0.6.0 — Premium UI

Beş yeni işıqlı gradient mövzusu, canlı rəng önizləməsi və yenilənmiş Ayarlar
bölməsi. Masaüstü və mobil ekranlar üçün oxunaqlı kartlar, incə parıltı və
temaya uyğun gradient düymələr.

Nələr yenidir: **RELEASE_NOTES_AZ.md**. Quraşdırma və dəyişən fayllar:
**GRADIENT_YENILEME_AZ.md**. Dizaynın təfərrüatları: **PREMIUM_UI_AZ.md**.

## ORION 0.5.8 — əvvəlki Big Update

Yeni görünüş, şəkil + prompt video studiyası, beş köməkçi rejimi, canlı ayrıca
tablar/notepad, maliyyə planı və şəxsi qəbzlər, aylıq faiz müqayisəsi, ay sonu
proqnozu, mobil səhifələr və animasiyalı cihaz profili girişi əlavə edilib.

İstifadə və qoşulma: **BIG_UPDATE_058_AZ.md**.
Video üçün Studiyada **Runway API açarı** qoş; OpenAI/Claude çat ayarların qalır.
Köhnə ORION-u tam bağlayıb proqram fayllarını köçür. Öz .env, .venv və istifadəçi
məlumatlarını saxla, START.bat ilə aç.

ORION 0.5.7 — daha böyük robot, sağda açılan çat və əl işarəli salamlaşma.
Ana panelin idarəetməsi sağdadır. “Çat aç” şəxsi qarşılama və təklif kartları olan
hündür pəncərəni açır. Çatdakı × kiçik panelə qaytarır. Salamlaşma ayarlarını
üst panelin dişli ikonundan dəyişmək olar. İstifadə: YUXARI_PANEL_AZ.md.

ORION 0.5.6 — canlı robot mimikası, şəffaf PNG və Poppins.
Robot gözünü qırpır, qaşını və ağzını dəyişir, yazı kursoruna və gələn cavaba
baxır. Şriftlər internet olmadan işləyir. Xərc üçün mənfi məbləğ yaz: -100.
Hesab/kredit kartlarının yanında silmə düyməsi var; tarixçə saxlanır və bölməni
“Silinmiş bölmələr” ilə geri qaytarmaq olur. Təfərrüat: ROBOT_ANIMASIYA_AZ.md.

ORION 0.5.5 — aylıq gəlir düzəlişi və tema ilə uyğunlaşan chatbot tabı.
Ana səhifədə aylıq gəliri qələmlə dəyiş; yeni tamamlanmış mədaxil onun üstünə gəlir.
Chatbotu bağlasan üst alət zolağındakı çat ikonu və ya Ümumi parametrlərdəki
“Chatbotu aktivləşdir” düyməsi ilə yenidən aç. Yuxarı sürükləyəndə kiçilir,
tabdakı oxla böyüyür. Quraşdırma və istifadə: YUXARI_PANEL_AZ.md.

ORION 0.5.4 — ayrıca üst chatbot paneli.
Yalnız panel üçün START_TOP_PANEL.bat, tam tətbiq üçün START.bat aç.
Yeni panelin təlimatı: YUXARI_PANEL_AZ.md

ORION 0.5.3 yeniləməsi: avtomatik hesab cəmi və proqram yeniləmələri.
Quraşdırma və yeniləmə mənbəyinin qoşulması: YENILEME_053_AZ.md
Buraxılış qeydləri: RELEASE_NOTES_AZ.md

# ORION — vahid AI və masaüstü paketi

## İlk dəfə açmaq

1. ZIP-i ayrıca qovluğa çıxart. Köhnə ORION serverini və terminalını bağla.
2. Mövcud **`.env`** faylını bu qovluğa köçür. Faylın adı `.env(3)` və ya `.env.txt` deyil, **`.env`** olmalıdır. Yoxdursa, `.env.example` faylının surətini `.env` adı ilə saxla.
3. **`INSTALL.bat`** faylını aç. Python 3.11+ və internet lazımdır. Bu addım yalnız ilk qurulum və yeniləmələr üçündür.
4. **`START.bat`** faylını aç. Tətbiq pəncərəsi açılacaq. Masaüstü modul açıla bilməzsə, `START_BROWSER.bat` istifadə et.
5. **Ayarlar → AI imkanları** bölməsində modeli, Azərbaycan/ingilis dilini və səsi seç. **AI ayarlarını saxla** düyməsini bas.

Python yoxdursa, python.org-dan Python 3.11+ quraşdır. Masaüstü pəncərəsi Windows Edge WebView2 runtime-dan istifadə edə bilər; runtime xətası olarsa brauzer rejimi işlək alternativdir.

## Hansı açar nə üçündür?

| Dəyişən | İmkan |
|---|---|
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Claude söhbəti və mövcud Blender/Roblox kod generatorları |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | OpenAI söhbəti; FORGE əvəzinə model menyusundan seçilir |
| `OPENAI_IMAGE_MODEL` | Şəkil modeli; standart `gpt-image-2.5-sunburst` |
| `OPENAI_VIDEO_MODEL` | Video modeli; standart `sora-2` |
| `OPENAI_TRANSCRIBE_MODEL` | Səsi mətnə çevirmə; standart `gpt-transcribe` |
| `OPENAI_TTS_MODEL`, `OPENAI_VOICE` | Cavabın səsləndirilməsi |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | Alternativ ElevenLabs səsi |
| `BLENDER_PATH` və ya köhnə `BLENDER_EXE` | Kompüterdə `blender.exe` yolu |

Model adlarını hesabında çıxışın olan modellərlə dəyişə bilərsən. API açarı təyin edilməsi modelə giriş, işlək balans və ya bütün dillərdə eyni keyfiyyət demək deyil. Xəta olanda real status göstərilir. Açarlar HTML-ə yerləşdirilmir və backend ayar API-si ilə geri qaytarılmır. `.env` dəyişəndən sonra tətbiqi tam bağlayıb yenidən aç.

Yalnız Claude açarın varsa mətn söhbəti və Blender/Roblox alətləri işləyə bilər. Şəkil/video və bulud səs tanıması üçün ayrıca `OPENAI_API_KEY` lazımdır. Brauzerin öz səs tanımasını alternativ kimi seçə bilərsən; dəstək brauzerə və dilə görə dəyişir.

## Səsli söhbət

- Çatdakı mikrofonu bas, danış, bitirəndə yenidən bas. Sükut da yazını dayandıra bilər.
- **AI imkanları → Səsli söhbətə başla** açıq olduqda danışıq göndərilir, cavab səsləndirilir və növbəti dinləmə başlayır.
- **Cavab və danışıq dili**: Azərbaycan dili və English. Bu seçim cavabın dilinə və transkripsiya dilinə ötürülür.
- **Kompüterdən səsli komanda ver**: Windows/Python mikrofonunu istifadə edir; brauzer mikrofonu tələb olunmur.
- Səslər süni intellektlə yaradılır. Azərbaycan tələffüzünün və səs tanımasının keyfiyyəti seçilən provayderə, səsə və mikrofona görə dəyişir. Öz səsinlə sınaqdan keçir.

### Pəncərə bağlı olanda “Orion” ilə çağırmaq

1. Windows Settings → Time & Language bölməsində **English (United States) Speech** komponentinin mövcud olduğuna əmin ol.
2. Windows Privacy & Security → Microphone bölməsində desktop tətbiqlərinə mikrofon icazəsi ver.
3. AI imkanları bölməsində **Arxa planda “Orion” ilə oyat** seçimini aç.
4. “Orion” və ya “Hey Orion” de. Qısa səsdən sonra əmri Azərbaycan və ya ingilis dilində söylə.

Oyatma sözü Windows-da yerli tanınır; əmr yazısı oyandıqdan sonra bulud səs tanımasına göndərilir. Bu, tam dupleks Realtime səs deyil: danışıq → transkripsiya → AI/alət → cavab səsi ardıcıllığıdır.

**Pəncərənin × düyməsi** desktop rejimində onu gizlədir, proqram sistem panelində qalır. **Tray → Tam çıxış** prosesi dayandırır. Kompüter sönəndə və ya tətbiqdən tam çıxanda dinləmə işləmir. Brauzer rejimində server terminalı açıq qalmalıdır.

Windows-a daxil olanda ORION-un açılması üçün **`ENABLE_AUTOSTART.bat`** işlət. Ləğv etmək üçün `Win + R → shell:startup` qovluğundan ORION qısayolunu sil.

## Şəkil və video

- AI imkanları bölməsində təsviri yazıb növü seç və **Yarat** bas.
- Və ya çatda “... mövzusunda şəkil yarat” / “... haqqında video yarat” de.
- Şəkil üçün real generasiya çağırışı edilir. Video sorğusu asinxron yaradılır; tətbiq açıq olduqca server nəticəni yoxlayır.
- Nəticə aşağıdakı qalereyada açılır və yüklənir. Video növbəsinin remote ID-si diskdə saxlanır; server yenidən açılanda gözləyən videonun nəticəsi yoxlanır.
- Yarımçıq yerli sorğular avtomatik təkrar göndərilmir. Beləliklə restart eyni ödənişli işi iki dəfə başlatmır.

## Blender və Roblox

**Blender**: `BLENDER_PATH` təyin et. “Blender-də materialları ilə sadə masa modeli yarat” deyə sına. Mövcud modullar AI-dən `bpy` skripti alır, arxa planda Blender-də işlədir, `.blend` və mümkün olduqda `.fbx` saxlayır. Blender quraşdırılması və işlək Anthropic modeli lazımdır.

Yaradılmış bpy koduna statik import/sistem-əməliyyat yoxlaması əlavə edilib. Bu yoxlama tam əməliyyat sistemi sandbox-u deyil. Proqram mövcud istifadəçinin hüquqları ilə işləyir.

**Roblox**:

1. **`INSTALL_ROBLOX_PLUGIN.bat`** aç.
2. Studio-nu yenidən başlat, layihədə HTTP Requests icazəsini aç.
3. Plugins → ORION toolbar düyməsini aktiv et.
4. “Roblox-da mavi 4×4×4 kub yarat” kimi əmrlə sına.

Plugin hissə, skript, UI, weld və mesh yerləşdirmə əmrlərini qəbul edir. Standart port **8787**-dir. Portu dəyişsən `roblox_plugin/OrionBridge.lua` daxilindəki `BASE` ünvanını da dəyiş. Mesh yükləməsi Roblox hesab icazələrindən və asset emalından asılıdır.

## Məlumatlar və yaddaş

- AI mesajları, yaddaş ayarları, işlər və faktiki token statistikası SQLite-də qalır: Windows-da **`%LOCALAPPDATA%\ORION`**.
- Gələn fayllar `uploads`, media `media`, yaradılan Blender faylları `models` qovluğunda saxlanır. Mesajları/profili təmizləmədən əvvəl ehtiyat nüsxəsi götür.
- Maliyyə/mülklər/qeydlər/profil əvvəlki kimi frontend-in localStorage yaddaşında saxlanır. Brauzer və desktop WebView ayrı yaddaş istifadə edə bilər.
- Keçid üçün köhnə brauzerdə **Ayarlar → Sistem və diaqnostika → Məlumatları yüklə**, sonra yeni tətbiqdə **AI imkanları → İş sahəsini bərpa et** istifadə et.
- Dashboard-un yığcam statistika və qeyd xülasəsi AI üçün yerli serverə sinxronlaşdırılır; modelə alət vasitəsilə verilə bilər. API açarları bu kontekstə daxil edilmir.
- API statistikasında token və sorğu sayı faktiki cavablardan götürülür. Pul xərci uydurulmur; provayderin istifadə panelində yoxlanır.

## Fayllar

Şəkil (PNG/JPG/WebP/GIF), PDF, DOCX və mətn/kod sənədləri dəstəklənir. Hər fayl 20 MB, cəmi 25 MB, maksimum 5 fayl. Anthropic-in şəkil limiti tətbiq edildikdə daha kiçik fayl tələb oluna bilər. Sancaqdan seç, önbaxışı yoxla, göndər.

## Texniki yoxlama

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

Testlər saxta provayder cavabları ilə işləyir və API balansından istifadə etmir. Yaddaş, alət dövrü, HTTP əlaqəsi, fayl qəbulu, media növbəsi və səs sorğuları yoxlanır. Windows tray/mikrofon, real API çıxışı, Blender və Studio icrası həmin mühitdə ayrıca sınaq tələb edir.

Server yalnız `127.0.0.1` üzərində açılır. Başqa saytlardan idarəetmə sorğuları və `.env`/Python fayllarına HTTP çıxışı rədd edilir. Telefon/LAN istifadəsi bu desktop paketində aktiv deyil.

## İstifadə olunan rəsmi API sənədləri

- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/docs/guides/image-generation
- https://developers.openai.com/api/docs/guides/video-generation
- https://developers.openai.com/api/docs/guides/speech-to-text
- https://developers.openai.com/api/docs/guides/text-to-speech
- https://create.roblox.com/docs/reference/engine/classes/AssetService
- https://learn.microsoft.com/en-us/dotnet/api/system.speech.recognition.speechrecognitionengine
- https://pywebview.flowrl.com/api/
