# ReplayCore - Tek EXE olusturma (Windows)

Bu paket ReplayCore v0.1 uygulamasini **tek bir `ReplayCore.exe`** dosyasi olarak paketlemek icin guncellenmistir. Uygulamanin oyun yakalama ozellikleri v0.1 ile aynidir. `ffmpeg.exe` PyInstaller icine dahil edilir; hedef bilgisayarda Python veya FFmpeg kurulumu gerekmez.

## Yontem A - Kendi bilgisayarinda (derleme icin Python gerekir)

1. Windows 10/11 64-bit uzerinde Python 3.10+ ve pip kur.
2. `EXE_OLUSTUR.bat` dosyasina cift tikla. Gerekirse `KUR_FFMPEG.bat` otomatik calistirilir.
3. Islem basarili ise `dist/ReplayCore.exe` dosyasini ac.
4. Diger Windows bilgisayarlara bu tek EXE dosyasini kopyalayabilirsin.

## Yontem B - Bilgisayarina Python kurmadan (GitHub Actions)

1. https://github.com/new adresinden bir depo olustur. Kolaylik icin varsayilan `main` dalini kullan.
2. Bu paket icindeki dosyalari, klasor yapisini koruyarak deponun **kokune** yukle (`replaycore.py`, `recorder.py`, `hotkeys.py`, `test_core.py`, ve `.github/workflows/build-windows.yml` dahil). ZIP dosyasini tek dosya olarak yuklemek yerine **ZIP'i acip icindekileri yukle**. `.github` klasoru gorunmuyor ya da yuklenmiyorsa depoda "Add file > Create new file" ile `.github/workflows/build-windows.yml` yolunu olustur ve paketteki workflow dosyasinin icerigini yapistir.
3. Depoda **Actions** sekmesine gir. **ReplayCore Windows EXE** is akisini sec ve **Run workflow** (ya da kod yuklenince otomatik baslamis olan is akisi) ile derlemeyi baslat.
4. Is akisi basarili bitince ilgili calistirma kaydinin **Artifacts** alanindan **ReplayCore-Windows-EXE** dosyasini indir. ZIP'i acip `ReplayCore.exe`'ye cift tikla.
5. GitHub derlemeyi kendi Windows makinesinde yapar. Kendi PC'ne Python kurman gerekmez.

GitHub Actions'da ozel depolar/hesaplar icin kullanim kotasi bulunabilir. Indirilen EXE, mevcut Windows oyun ekran yakalama yetenekleri uzerinde **otomatik olarak test edilmis sayilmaz**.

## Klip ve kisayollar

- Windows 10/11, 64-bit hedeflenir.
- `Ctrl+Shift+F9`: Kaydi baslat/durdur.
- `Ctrl+Shift+F10`: Son klibi kaydet.
- Klipler: kullanicinin `Videolar/ReplayCore` klasorune kaydedilir.

## Neden EXE buyuk olabilir?

Tek dosyada Python runtime, Tkinter ve FFmpeg bir aradadir; ilk acilista gecici klasore acilabilir. Bu nedenle hem dosya boyutu hem de baslangic suresi artabilir. Bazı antivirus programlari yeni/imzasiz EXE'leri ek tarayabilir.

## Notlar ve lisans

ReplayCore arayuzu kaynak kodu MIT lisanslidir (LICENSE). FFmpeg ayridir ve gyan.dev Essentials derlemesi GPLv3 lisanslidir. FFmpeg ile uygulamayi **baskalarina dagitmadan once** ilgili lisans, kaynak kodu saglama ve atif gereklerini incele. FFmpeg'in resmi sitesi: https://ffmpeg.org/legal.html

Bu bir prototiptir. DXGI ekran yakalama, tum oyunlarda ses kaydi ve eski ekran kartlarinda sorunsuz calisma garantisi **yoktur**. EXE sadece Windows 64-bit icin olusturulur.
