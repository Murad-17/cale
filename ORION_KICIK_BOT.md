# ORION 0.5.8 — Kiçik bot mərkəzi

Coucou-nun kiçik köməkçi iş axını ORION-un mövcud Python/HTML tətbiqinə uyğunlaşdırılıb. Görünüş, şəffaf robot, beş ORION personajı, rəng mövzuları və mövcud əsas panel qorunur. Göndərilən Coucou arxivindəki hazır macOS tətbiqi Windows proqramına çevrilməyib; bu funksiyalar ORION daxilində həyata keçirilib.

## Başlamaq

1. ORION fayllarını mövcud ORION qovluğuna köçür və `START.bat` ilə aç.
2. Kiçik botda **Mərkəz** düyməsini və ya yuxarıdakı orbit işarəsini seç.
3. **Bağlantılar** bölməsində Claude və ya OpenAI açarını daxil et, **Yoxla və saxla** seç.
4. Xidmətdən alınan siyahıdan AI modelini seç və **Modeli seç** düyməsinə bas.

Əvvəldən qoşulmuş açarlar da işləyir. İşləyən bağlantı yeni açarın yoxlanması uğursuz olduqda əvəz edilmir. Siyahının alınması modelin gələcək sorğularının balans və istifadə limitlərindən asılılığını aradan qaldırmır.

Claude açarın müəyyən workspace-ə bağlanmayıbsa, **Workspace ID** sahəsinə hesabındakı `wrkspc_…` identifikatorunu daxil et. Uyğun workspace başlığı həm söhbətə, həm model siyahısına, həm də Blender/Roblox Claude sorğularına əlavə olunur. Tək workspace-ə bağlanmış açarda bu sahə boş qala bilər.

## Kiçik botun bölmələri

| Bölmə | İşləyən funksiyalar |
| --- | --- |
| Söhbətlər | Yeni söhbət, ayrıca tarixçə, ad dəyişmə, davam etmə və arxivləmə |
| Yaddaş | Qeyd əlavə etmə, redaktə, silmə, sabitləmə və axtarış |
| Tapşırıqlar | Sadə tapşırıq, tarixli xatırlatma, 10 dəqiqə təxirə salma, tamamlama və silmə |
| Canlı işlər | Həqiqi alət addımları, nəticələr, təsdiq/imtina və qoşulmuş agentin vəziyyəti |
| Bağlantılar | API açarı, workspace, model seçimi, ünsiyyət və cavab uzunluğu |

Yeni bot söhbətləri bir-birinin model kontekstinə qarışmır. Əvvəlki ortaq dashboard mesajları silinmir və əsas paneldə qalır. Arxivləmə də mesajları silmir. Mesaj və fayl qaralaması yenidən açılış üçün saxlanılır; göndəriş qəbul edilmədikdə təmizlənmir.

## Davranış və yaddaş

Orbit, Vector, Nova, Muse və Atlas mövcud seçilmiş AI modeli üzərində işləyən ORION davranışlarıdır. Bunlar beş ayrı provayder deyil. Hər rejimin robot rəngi və mimikası qorunur.

**Bağlantılar → Xasiyyət və yaddaş** bölməsində mehriban, peşəkar və dəqiq üslub; qısa, normal və ətraflı cavab seçmək, xüsusi təlimat yazmaq mümkündür. Bu seçimlər həqiqi model təlimatına əlavə olunur.

Yaddaş qeydləri avtomatik uydurulmur. Söhbətdə “Bunu yadda saxla” istəyəndə bot qeyd təklif edə bilər; **Canlı işlər → İcazə ver** seçildikdən sonra yaddaşa yazılır. Cavabın altındakı **Yadda saxla** düyməsi isə redaktə edilən qeyd formasını açır. Yaddaşdan istifadəni söndürmək qeydləri silmir.

Sabit və sorğuya uyğun qeydlər ölçü limiti daxilində model kontekstinə əlavə edilir. Dashboard xülasəsi ayrıca paylaşma seçimi açılmadan bota ötürülmür. Fayl və şəkilləri söhbətə əlavə etməklə paylaşa bilərsən. Başqa tətbiqlərin ekranı avtomatik tutulmur və oxunmur.

## Əməliyyatlar və təsdiq

Bot fayl axtara/oxuya, məzənnə yoxlaya, araşdırma apara, icazəli proqramı aça, qoşulmuş Blender/Roblox alətindən və mövcud şəkil/video xidmətindən istifadə edə bilər. Hər imkan öz proqramının və ya API bağlantısının mövcudluğundan asılıdır.

Proqram açma, generasiya və layihəyə dəyişiklik standart olaraq təsdiq gözləyir. Sorğunun məzmununa baxıb **İcazə ver** və ya **İmtina et** seç. Eyni təsdiq iki dəfə icra edilmir. Cavabsız sorğunun vaxtı 24 saatdan sonra bitir. Yaddaşa yeni AI qeydi həmişə təsdiq tələb edir.

Şəkil və hazır video söhbətdə açılır. Video xidmətdən faktiki tamamlanma siqnalı gələndən sonra hazır sayılır. İşləmə vaxtı vəziyyət göstərilir; faiz yalnız xidmət həqiqi gedişat göndərəndə görünür. Uğursuz ödənişli əməliyyat avtomatik təkrarlanmır.

## Xatırlatmalar

Xatırlatma yerli tarix/saatla yaradılır və UTC vaxtı ilə saxlanılır. ORION prosesi açıq olanda vaxtı çatmış tapşırıq paneldə göstərilir; bot kiçilmişdirsə işarə görünür. **Gördüm**, **10 dəq sonra**, **Tamamladım** seçimləri yadda saxlanılır.

Tətbiq tam bağlanıbsa, əməliyyat sistemi səviyyəsində ayrıca zəng qurulmur. Vaxtı keçmiş xatırlatma ORION yenidən açılanda görünür. Xatırlatma özbaşına API sorğusu, ödəniş və ya proqram əmri başlatmır.

Səsli komanda üçün kiçik çatın **Səs** düyməsi mövcud səs xidmətindən istifadə edir; transkripsiya və cavab seçilmiş söhbətdə qalır. Mikrofon və səs xidmətinin uyğun bağlantısı tələb olunur.

## Kod agentini qoşmaq — istəyə bağlı

**Mərkəz → Canlı işlər → Agent izləməsini aç** seç. Sonra ORION qovluğunda bu əmri işlət:

```bat
python orion_agent_hook.py --agent Codex --session orion --state working --label "Faylları oxuyur"
```

Tamamlandıqda eyni sessiya ilə yeni vəziyyət göndər:

```bat
python orion_agent_hook.py --agent Codex --session orion --state completed --label "İş tamamlandı"
```

Vəziyyətlər: `working`, `waiting`, `completed`, `error`. Bu əmri istifadə etdiyin agentin öz hook mexanizmindən də çağıra bilərsən. Agent adı sərbəstdir; vəziyyət yalnız həqiqi hook hadisəsi gələndə göstərilir. Heç bir agentin quruluşu və ayar faylı avtomatik dəyişdirilmir.

Bağlantı yalnız `127.0.0.1` üzərindən və gizli yerli tokenlə işləyir. Token söhbətə və interfeysə verilmir; helper onu ORION istifadəçi qovluğundan oxuyur. İzləməni söndürəndə token ləğv olunur. Açıq saxlanmış seçim növbəti başlanğıcda yeni tokenlə bərpa edilir. Bu hook xarici terminalda əmri təsdiqləmir; təsdiq düymələri ORION-un öz əməliyyatları üçündür.

## Saxlanma və uyğunluq

Mövcud məlumat bazasına yalnız əlavə cədvəllər və söhbət sütunu əlavə olunur. Maliyyə, layihə, parametrlər, əvvəlki mesajlar və fayllar sıfırlanmır. API açarları mesaj və ümumi parametrlər bazasına yazılmır. Windows-da yeni açarlar istifadəçinin DPAPI qoruması ilə saxlanılır; digər sistemlərdə yalnız istifadəçiyə açıq ayrıca yerli fayl istifadə olunur.

Bu paketdə Coucou-nun Mochi şəkilləri, ikonları, səsləri və macOS binarisi yoxdur. iCloud/telefon sinxronlaşdırması, macOS ekran tutma, görüş yazıcısı və Coucou-nun bütün servis inteqrasiyaları bu yeniləməyə daxil deyil.

Funksional sınaqlar xarici AI sorğuları əvəz edilərək aparılıb. Real API istifadəsi üçün etibarlı açar, şəbəkə və xidmətə giriş lazımdır. Windows-da yerli pəncərə və mikrofon fiziki cihazda ayrıca yoxlanmalıdır.

İş axını üçün istinad: https://github.com/Louis-CFM/coucou
