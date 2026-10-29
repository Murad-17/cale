# ORION 0.6.0 — Premium UI

## Yeni görünüş

Ayarlar bölməsi yumşaq işıq və ardıcıl boşluqlarla yenilənib. Rəng seçimləri
oxunaqlı kartlara çevrilib; şaquli mətnli kapsulların əvəzinə iki kolleksiya var.

**İşıq kolleksiyası**
- **İnci işığı** — mint, inci ağ və yasəmən keçidləri.
- **Kobalt işığı** — dərin mavi, elektrik mavisi və buz ağ parıltı.
- **Mərcan alovu** — kəhrəba, mərcan və çəhrayı alt işıq.
- **Mavi laqun** — firuzə, su mavisi və sakit buz işığı.
- **Qütb parıltısı** — firuzə, bənövşəyi və çəhrayı aurora.

**Klassik palitralar** bölməsində əvvəlki 12 mövzu qalır.

Canlı önizləmə rəngləri nümunə kartda göstərir. “Yadda saxla” düyməsi seçilən
palitraya uyğun gradient kapsuldur. Tema seçimi dərhal yadda qalır; siçanla və
klaviatura ilə baxış zamanı yalnız müvəqqəti önizləmə göstərilir.

## Mobil və əlçatanlıq

Mobil ekranda axtarış ayrıca sətirdə, bölmələr üfüqi menyudadır. Kartlar iki
sütunda düzülür; yadda saxlama zolağı aşağıda əlçatan qalır. Klaviatura fokusları
aydındır, azaldılmış hərəkət seçimi yeni animasiyaları dayandırır.

## Yoxlama

Mövzu seçimi, yadda saxlama, yenidən yükləmə, chatbot panelinə ötürmə,
önizləmə, axtarış, bölmələr və Escape ilə bağlama ayrıca brauzer testindədir:
`node tests/ui_gradients.cjs`.

1440, 1024, 768, 390 və 360 piksel enləri, açıq mövzu və qısa üfüqi ekran
Chromium ilə yoxlanıb. Windows native pəncərəsinin davranışı və real API
əməliyyatları həmin cihazda ayrıca yoxlanmalıdır.

Quraşdırma addımları: **GRADIENT_YENILEME_AZ.md**.
