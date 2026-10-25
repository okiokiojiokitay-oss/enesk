# ReplayCore v0.1 — AMD ve NVIDIA anında yeniden oynatma (Windows)

**Durum:** Çalıştırılabilir ilk prototip / kaynak kod. Windows bilgisayarda uçtan uca test edilmedi. Henüz son kullanıcı için doğrulanmış bir `.exe` değil. Tek dosyalı EXE oluşturma: `NASIL_EXE_OLUSTURULUR.md`.

## Özellikler

- Masaüstü görüntüsünü, kayıt başlatıldığı andan itibaren kesintisiz arka planda yakalar.
- Son yaklaşık **15 / 30 / 60 / 120 saniyeyi** MP4'e kaydeder. Tam süre birkaç saniye değişebilir.
- Otomatik **NVIDIA NVENC → AMD AMF → CPU x264** denemesi. Donanımsal kodlama bulunmuyorsa CPU ile devam eder.
- 480p/720p/1080p/orijinal çözünürlük; 15/30/60 FPS.
- Global kısayollar: **Ctrl+Shift+F9** başlat/durdur; **Ctrl+Shift+F10** tekrar kaydet.
- İsteğe bağlı DirectShow ses kaynağı (örneğin Stereo Mix); başlangıçta sessiz kayıt.
- Kayıtlar `C:\Users\<kullanici>\Videos\ReplayCore` klasörüne kaydedilir.

## Nasıl başlatılır?

1. **Windows 10 veya 11 (64-bit)** ve **Python 3.10+** kurulu olmalı (Tkinter ile gelen standart Python paketi). Python: https://www.python.org/downloads/windows/
2. `KUR_FFMPEG.bat` dosyasını çalıştır. Bu dosya FFmpeg Windows Essentials ZIP dosyasını *gyan.dev* üzerinden indirir, içerisindeki `ffmpeg.exe`yi proje dizinine çıkarır. Alternatif olarak `https://www.gyan.dev/ffmpeg/builds/` sayfasından indirip `bin/ffmpeg.exe` dosyasını proje klasörüne elle kopyalayabilirsin.
3. `BASLAT.bat` dosyasını aç.
4. Replay süresini ve ayarları seç; **KAYDI BAŞLAT** düğmesine bas.
5. Yaklaşık 5 saniye sonra **Ctrl+Shift+F10** tuşlarına basarak son anları MP4 kaydet.

**İsteğe bağlı tek .exe oluşturma:** `EXE_OLUSTUR.bat`, `ffmpeg.exe` dahil tek `dist/ReplayCore.exe` üretir. Yerel derleme Python gerektirir. Python kurmadan derlemek için `.github/workflows/build-windows.yml` ile GitHub Actions kullan; ayrıntılar `NASIL_EXE_OLUSTURULUR.md` dosyasında. Son kullanıcıya dağıtılan EXE için Python veya ayrı FFmpeg gerekmez.

## Eski kartlarda ne olur?

FFmpeg'in `gdigrab` Windows GDI yöntemi, ekranı belirli GPU modeline bağlı olmadan yakalamak için seçildi. NVENC/AMF donanım hızlandırması yalnızca GPU, sürücü ve FFmpeg birlikte destekliyorsa çalışır; aksi halde `libx264` denenir. Çok eski ekran kartları ve CPU'larda **480p + 15 FPS + CPU x264** ile başla. Tam ekran ayrıcalıklı oyunlarda GDI siyah ekran gösterebilir; bunun için sonraki sürümde DXGI/Windows Graphics Capture yakalama seçeneği gerekir.

## Ses hakkında

Windows'ta FFmpeg'in `dshow` girişi, varsayılan olarak hoparlörden oynatılan sesi doğrudan yakalamaz. 'Stereo Mix' kayıt aygıtı varsa Windows ses ayarlarından açıp uygulamadaki **Aygıtları tara** ile seçebilirsin. Mikrofon seçersen yalnızca mikrofon kaydedilir. Bazı bilgisayarlarda hiçbir Stereo Mix bulunmaz: bu durumda sistem sesi için sanal audio loopback gerekir. Sonraki sürümde üçüncü taraf sanal aygıt gerektirmeyen WASAPI loopback eklenebilir.

## Bilinen sınırlamalar

- Bu ilk sürüm GDI ile **masaüstünü** kaydeder, özel oyun penceresi veya tam ekran exclusive capture modu yoktur.
- En güncel an birkaç saniyelik TS parçasında tutulur. Program, son parçayı da kopyalamayı dener; kilitli veya henüz eksikse tekrarın son 0–2 saniyesi eksik olabilir.
- Tam 30.000 saniye kesme garantisi yoktur; parça sınırlarına göre yaklaşık süre.
- Kayıt arka planda **diskte dönen kısa parçalar** tutar (RAM tamponu değil). Kısa klipler nedeniyle SSD'de yazma gerçekleşir.
- Windows dışı işletim sistemleri desteklenmez. Python kaynak dosyalarının Linux'ta derlenmesi/yayın testi Windows ekran kaydının çalıştığını doğrulamaz.
- Global kısayol farklı bir uygulamada kullanılıyorsa kayıt olmayabilir; arayüz düğmeleri çalışmaya devam eder.
- Kayıt esnasında `Ctrl+Shift+F10` tuşuna basarak yerel diske dosya kaydetme işlemini başlatırsın; videolar buluta aktarılmaz.

## Sorun giderme

- **FFmpeg bulunamadı:** `KUR_FFMPEG.bat` çalıştır ve `ffmpeg.exe` dosyasını ana klasörde kontrol et.
- **NVIDIA/AMD seçildi ancak CPU kullanıyor:** GPU sürücüsü veya kodlayıcı desteklemiyor olabilir. 'Otomatik' seç.
- **Kaydedilen klipte görüntü yok / siyah ekran:** Oyunu pencere modunda veya kenarlıksız tam ekranda dene.
- **Oyun kasıyor:** 480p, 15 FPS, CPU x264 dene. GPU encode varsa 'Otomatik' daha hızlı olabilir.
- **Ses yok:** Başlangıç varsayılanı sessiz kayıttır; Stereo Mix veya uygun kaydı etkinleştir, 'Aygıtları tara'ya basıp kaynağı seç.
- **Kayıt başlamıyor:** `%TEMP%\ReplayCore\session_*\*.log` dosyasında FFmpeg hatasını incele.

## Lisans ve bağımlılıklar

ReplayCore prototip kodu MIT lisansı ile sunulur. FFmpeg **ayrı projedir**; otomatik indirilen gyan.dev Essentials sürümünün lisansı GPLv3'tür. Uygulamayı FFmpeg ile dağıtmadan önce FFmpeg ve kodlayıcı lisans yükümlülüklerine uyulmalıdır. FFmpeg kaynak: https://ffmpeg.org/ ; Windows build: https://www.gyan.dev/ffmpeg/builds/.

## Sonraki geliştirmeler

1. WASAPI sistem sesi (sanal aygıtsız) ve mikrofon miksleme.
2. Daha iyi performans için DXGI/Windows Graphics Capture ekran yakalama; GDI'yi legacy fallback tutma.
3. RAM tabanlı replay halkası, çok monitör ve gerçek zamanlı ses/video senkronu.
4. Detaylı donanım algılama, otomatik FPS adaptasyonu, tray simgesi, güncelleme mekanizması.

## Test bilgisi

Linux ortamında Python sözdizimi ve FFmpeg ile MPEG-TS segment üretme → MP4 birleştirme otomatik testleri geçmiştir. Arayüz Linux sanal masaüstünde açılmıştır. Windows üzerinde `gdigrab`, NVENC/AMF, DirectShow ses ve global kısayollar gerçek cihazla henüz denenmemiştir.
