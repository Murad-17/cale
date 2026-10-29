ORION — İnternet və ətraflı araşdırma yeniləməsi
================================================
Bu, əvvəl göndərilmiş ORION_Desktop_AI paketinə tətbiq edilən yeniləmədir.
Ayrıca proqram deyil. Mövcud quraşdırmanın fayllarını yeniləyir.

ADDIMLAR
1. ORION-da açıq işlərini saxla. Saatın yanındakı ORION ikonuna sağ kliklə
   “Tam çıxış” seç. Terminaldan işlədirsənsə Ctrl+C bas.
   Təkcə pəncərəni bağlamaq kifayət etmir: arxa planda işləyə bilər.
2. İşləyən ORION qovluğunun ehtiyat nüsxəsini saxla.
3. Bu ZIP-i ayrıca müvəqqəti qovluğa çıxart.
4. Çıxarılan faylların hamısını mövcud ORION qovluğuna kopyala:
   main.py, .env və .venv qovluğunun olduğu yerə.
   Windows soruşanda eyni adlı faylları əvəz etməyi seç.
   tests qovluğunu da birləşdirə bilərsən; proqramın işləməsi üçün şərt deyil.
5. Həmin mövcud ORION qovluğunda START.bat aç.
   Yenidən INSTALL.bat işlətmək və ya API açarlarını dəyişmək lazım deyil.
6. Ayarlar → AI imkanları → İnternet və ətraflı araşdırma bölməsinə bax:
   İnternet axtarışı aktiv, rejim Avtomatik, araşdırma limiti 10 000 token.

Yeniləmə .env, .venv və şəxsi məlumat fayllarını ehtiva etmir və onların
üstünə yazmır. SQLite yaddaşının yeri dəyişməyib. Eyni Windows istifadəçisi
və eyni ORION_DATA_DIR ilə əvvəlki yaddaş saxlanır. İnterfeys məlumatlarını
qorumaq üçün əvvəlki tətbiq rejimini, portu və profilini istifadə et.

YOXLAMA SUALLARI
• Bu gün 100 USD neçə AZN edir? Rəsmi mənbəni və tarixi göstər.
• 100 AZN neçə TRY edir? Rəsmi kursla hesabla.
• Ətraflı araşdır: Blender-də məhsul animasiyası üçün iş axını.
  Müxtəlif mənbələri müqayisə et, nümunələr və mənbə linkləri ver.

NƏ DƏYİŞDİ
• OpenAI üçün hosted web_search; Claude üçün hosted web_search və web_fetch.
  Ayrı axtarış açarı lazım deyil; mövcud seçilmiş provayderin API açarı
  istifadə olunur. Model və hesab həmin alətləri dəstəkləməlidir.
• “Araşdır / research” sözləri avtomatik geniş araşdırma rejimini açır.
  Çatda yeni “Ətraflı araşdır” qısa yolu var. Rejimi hər sorğu üçün də
  aktivləşdirmək və ya normal rejimə keçmək mümkündür.
• Araşdırma: müxtəlif sorğular və əsas səhifələrin oxunması üçün təlimat,
  mənbələrin müqayisəsi, geniş hesabat, 6 000 / 10 000 / 16 000 token limiti.
  Bu, sərhədsiz Deep Research xidməti deyil: bir sorğunun alət və vaxt
  büdcəsi var. Mənbə sayı və nəticənin uzunluğu mövzu/modeldən asılıdır.
• Kliklənən mənbə linkləri DOM ilə təhlükəsiz göstərilir; modelin HTML
  məzmunu icra olunmur. Axtarış/fetch xətaları gizlədilmir.
• Mərkəzi Bankın rəsmi XML bülleteni ilə məzənnə və çevirmə:
  nominal nəzərə alınır, bülletenin faktiki tarixi göstərilir, qeyri-iş
  günlərində əvvəlki 14 günədək bülleten yoxlanır. 10 dəqiqəlik keş var.
  Bu, bankların alış/satış qiyməti deyil. Rəsmi mənbə işləməyəndə xəta verilir.
• Köhnə UI, hero, səs, yaddaş, modellər, Blender/Roblox saxlanıldı.
• INSTALL/START faylları Windows üçün ASCII + CRLF ilə yenidən yazıldı;
  quraşdırma və başlatma xətalarında pəncərə açıq qalır.

İSTİFADƏ VƏ MƏHDUDİYYƏTLƏR
Araşdırma bir neçə dəqiqə çəkə bilər. Pəncərəni bağlamağa ehtiyac yoxdur.
Veb alətləri və əlavə tokenlər provayderin API balansından istifadə edir.
Sırf söhbət üçün internet açarını söndürmək mümkündür. Rəsmi valyuta aləti
internet axtarışı söndürülsə də ayrıca işləyir.

Model/alət uyğunluğu və ya icazə xətası çıxarsa ekran görüntüsünü göndər;
.env məzmununu və açarları paylaşma. Sistem provayderi səssiz dəyişmir,
ödənişli sorğunu başqa modeldə avtomatik təkrarlamır.

Yoxlama: 19 offline backend testi, desktop/mobil/reduced-motion DOM
sınaqları. Real ödənişli OpenAI/Claude sorğuları bu mühitdə yoxlanılmayıb.
Mərkəzi Banka buradan canlı sorğu HTTP 503 qaytardı; kurs və bank bağlantısı
istifadəçinin şəbəkəsində ayrıca yoxlanmalıdır. Kurs rəqəmi kodda sabit deyil.

RƏSMİ SƏNƏDLƏR
https://developers.openai.com/api/docs/guides/tools-web-search
https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
https://www.cbar.az/currency/rates
