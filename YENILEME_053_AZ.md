# ORION 0.5.3 — quraşdırma və yeniləmə mənbəyi

## Bu paketi necə istifadə etməli

1. Açıq işlərini saxla. Saatın yanındakı ORION ikonundan “Tam çıxış” seç.
2. Mövcud ORION qovluğunun ehtiyat nüsxəsini çıxart.
3. Bu ZIP-dəki ORION qovluğunun proqram fayllarını əvvəlki ORION qovluğuna köçür.
   Öz .env faylını, .venv qovluğunu və şəxsi məlumatlarını saxla; onları sıfırlama.
4. Həmin qovluqdakı START.bat faylını aç. Mövcud Python mühiti kifayətdir;
   bu yeniləmə üçün yeni asılılıq tələb olunmur.
5. Maliyyə → Hesablarım bölməsində məbləğləri dəyiş. Aşağıdakı ümumi məbləğ
   və yuxarıdakı ümumi balans eyni hesabların cəmindən avtomatik yenilənir.
6. Ayarlar → ORION haqqında → Proqram yeniləmələri bölməsini aç.
   “Bildirişə bax” ilə panelin dizaynını görə bilərsən.

Cari versiya 0.5.3-dür. Əvvəlki paketdə versiya metadatası olmadığı üçün bu
buraxılış üçün version.json əlavə olunub. Gələcək versiyalar onunla müqayisə edilir.

## Həqiqi avtomatik yeniləməni aktivləşdirmək

Paketdə rəsmi release hesabı, domeni və yeniləmə ünvanı yoxdur.
UI və Python yeniləmə mexanizmi hazırdır, amma yeni buraxılışların gəlməsi üçün
layihə sahibi aşağıdakı iki üsuldan biri ilə öz HTTPS mənbəyini qoşmalıdır:

- Mövcud .env faylına ORION_UPDATE_MANIFEST_URL=https://SENIN-DOMENIN/latest.json əlavə et; və ya
- update_source.json faylında manifest_url sahəsinə həmin HTTPS ünvanını yaz.

Yuxarıdakı ünvan nümunədir, işləyən rəsmi ORION serveri deyil.
Mənbə qoşulandan sonra ORION-u yenidən aç. Avtomatik yoxlamaya icazə ver və ya
“Yeniləmələri yoxla” düyməsindən istifadə et. Birinci icazə seçimi yadda saxlanır.

İstəyə görə eyni mənşəli özəl HTTPS mənbəyi üçün .env-də ORION_UPDATE_TOKEN
təyin edilə bilər. Token yalnız həmin hosta göndərilir, paneldə göstərilmir.

## Gələcək buraxılışı hazırlamaq

Tətbiq fayllarının yeni versiyasını hazırladıqdan sonra, məsələn:

```bash
python release_tools.py --version 0.5.4 --url https://SENIN-DOMENIN/ORION-0.5.4.zip --output release
```

Bu əmr təmiz yeniləmə ZIP-i və latest.json yaradır. Hər ikisini öz etibarlı
HTTPS mənbəyinə yerləşdir. Əvvəlcə ZIP-i, sonra latest.json-u yayımla.
release_tools.py şəxsi .env, .venv, məlumat bazası, qaralama və ehtiyat nüsxələri
buraxılışa daxil etmir. İstifadəçinin tam arxivini update paketi kimi yayımlama.

latest.json formatı:

```json
{
  "version": "0.5.4",
  "url": "https://SENIN-DOMENIN/ORION-0.5.4.zip",
  "sha256": "release_tools.py tərəfindən hesablanan 64 simvolluq SHA-256",
  "size": 123456,
  "notes": "Bu buraxılışda nələr dəyişib"
}
```

Nümunədəki size və sha256 real məlumat deyil; həqiqi rəqəmləri alət avtomatik yazır.
HTTPS server etibarlı TLS sertifikatına malik olmalıdır. HTTP-yə yönləndirmə,
ölçü uyğunsuzluğu, səhv SHA-256, zərərli ZIP yolları və şəxsi faylların
üstünə yazılması qəbul edilmir. Manifest ünvanı etibarlı layihə sahibinə məxsus olmalıdır.
Bu variant TLS + SHA-256 yoxlaması istifadə edir; ayrıca kod imzası infrastrukturu yoxdur.

## Quraşdırma davranışı

- “İndi yenilə” yalnız endirir və yoxlayır. Faiz faktiki endirilən baytlardan hesablanır.
- Sonra “Quraşdır və yenidən başlat” düyməsi görünür. Bu seçim yenidən başlatmanın təsdiqidir.
- Açıq redaktə, göndərilməmiş mesaj, kiçik çat qaralaması və aktiv AI işi quraşdırmanı saxlayır.
- Köməkçi proses ORION-un tam çıxmasını gözləyir, yalnız proqram fayllarını əvəz edir,
  fayl əvəzlənməsi alınmasa əvvəlki faylları bərpa edir və eyni rejimlə ORION-u açır.
- .env, .venv, update_source.json, istifadəçi məlumatları və WebView profili dəyişdirilmir.
- Yerli verilənlər bazasının surəti məlumat qovluğunda updates/pre-update.sqlite3-də,
  proqram fayllarının surəti isə updates/backup-.../original içində saxlanır.
- Brauzer rejimində eyni yerli ünvan, port və profil saxlanır. Köhnə açıq səhifə
  serverə yenidən qoşulur; yeni faylları göstərmək üçün lazım gələrsə səhifəni yenilə.
- Yeni Python asılılığı və ya tam Python/runtime dəyişməsi bu source updater ilə
  avtomatik quraşdırılmır. Belə buraxılış ayrıca quraşdırıcı tələb edir.
- Birbaşa HTML açılışı yalnız interfeys önbaxışıdır. Həqiqi yeniləmə üçün START.bat istifadə et.

## Yoxlama

```bash
python -m unittest discover -s tests -v
```

Avtomatlaşdırılmış sınaqlar yerli/müvəqqəti paketlərlə aparılır; real API ödənişi
və şəxsi layihələr tələb etmir. Windows masaüstü yenidən başlatması bu Linux
mühitində canlı yoxlanılmayıb. Rəsmi HTTPS mənbəyi qoşulmadığı üçün canlı rəsmi
buraxılış endirməsi də burada həyata keçirilməyib.
