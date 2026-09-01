# Hướng dẫn build & deploy Crow Translate

Tài liệu này hướng dẫn build, đóng gói và cài đặt bản Crow Translate trong repo này
(đã có thêm cơ chế dịch qua Google Cloud Translation API, xem
[TRANSLATION_MECHANISM.md](TRANSLATION_MECHANISM.md)). Áp dụng cho Linux (chính) và
ghi chú riêng cho Windows.

## 1. Lấy đủ source (submodules)

Đây **không phải git repo** trong môi trường hiện tại (`.git` không tồn tại), nên các
git submodule khai báo trong [.gitmodules](.gitmodules) đang là **thư mục rỗng**, trừ
`src/qonlinetranslator` (đã được clone thủ công trong phiên làm việc trước để lấy header
thật phục vụ việc code).

Kiểm tra nhanh trước khi build:
```bash
for d in src/third-party/singleapplication src/third-party/qhotkey \
         src/third-party/qtaskbarcontrol src/qonlinetranslator src/qgittag \
         data/icons/third-party/circle-flags data/icons/third-party/fluent-icon-theme; do
    echo "$d: $(ls "$d" 2>/dev/null | wc -l) file(s)"
done
```

**Nếu bạn clone lại từ đầu (khuyến nghị cho việc build/deploy thật sự):**
```bash
git clone --recurse-submodules https://github.com/crow-translate/crow-translate.git
```
(Repo gốc đã chuyển về KDE: https://invent.kde.org/office/crow-translate — dùng URL đó
nếu muốn bản mới nhất, nhưng lưu ý code trong thư mục hiện tại đã được sửa để thêm cơ
chế Google Cloud, cái đó **không có** trên upstream).

**Nếu tiếp tục làm việc trên thư mục hiện tại** (đã có sẵn thay đổi Google Cloud), cần
tự clone từng submodule còn thiếu theo URL trong `.gitmodules`:
```bash
git clone https://github.com/itay-grudev/SingleApplication.git src/third-party/singleapplication
git clone https://github.com/Skycoder42/QHotkey.git src/third-party/qhotkey
git clone https://github.com/crow-translate/QTaskbarControl.git src/third-party/qtaskbarcontrol
git clone https://github.com/crow-translate/QGitTag.git src/qgittag                # chỉ cần trên Windows
git clone https://github.com/HatScripts/circle-flags.git data/icons/third-party/circle-flags
git clone https://github.com/vinceliuice/Fluent-icon-theme.git data/icons/third-party/fluent-icon-theme
```
`src/qonlinetranslator` đã có sẵn, không cần clone lại.

## 2. Cài dependency hệ thống (Linux)

Cần Qt5 (>=5.9, khuyến nghị 5.15) với các module: Widgets, **Network** (mới thêm do
GoogleCloudTranslator dùng `QNetworkAccessManager`), Multimedia, Concurrent, X11Extras,
DBus, LinguistTools; Tesseract >=4.0; Extra CMake Modules (ECM); CMake >=3.16.

Ví dụ trên Ubuntu/Debian:
```bash
sudo apt install cmake extra-cmake-modules \
    qtbase5-dev qttools5-dev qttools5-dev-tools qtmultimedia5-dev \
    libqt5x11extras5-dev libqt5svg5-dev \
    libtesseract-dev libleptonica-dev \
    libxcb1-dev libdbus-1-dev
```
Nếu build với `WITH_KWAYLAND` (tích hợp Wayland/KDE tốt hơn), cần thêm
`libkf5wayland-dev` (hoặc gói KWayland tương ứng distro).

## 3. Configure & build

```bash
mkdir build && cd build
cmake .. -D CMAKE_BUILD_TYPE=Release
cmake --build . -j"$(nproc)"
```

Các option đáng chú ý (truyền qua `-D`):
- `WITH_PORTABLE_MODE` — cho phép chạy portable (đọc `settings.ini` cạnh binary thay vì
  `~/.config`).
- `WITH_KWAYLAND` — tích hợp Wayland/KDE tốt hơn (cần KWayland dev package).

Binary tạo ra tên là `crow` (biến `EXECUTABLE_NAME` trong `CMakeLists.txt`).

**Kiểm tra build có nhận đúng Qt5::Network:** nếu CMake báo lỗi
`Could NOT find Qt5Network`, cài thêm gói Qt5 Network dev (thường đã kèm theo
`qtbase5-dev`, nhưng một số distro tách riêng `libqt5network5-dev`).

## 4. Chạy thử / smoke test trước khi đóng gói

```bash
./build/crow                       # GUI
./build/crow -e google -t vi "hello"   # CLI, dùng engine Google
```

Vì cơ chế Google Cloud là **tuỳ chọn** (chỉ kích hoạt khi có API key trong settings),
build sẽ chạy được ngay cả khi chưa cấu hình key — engine "Google" sẽ tự rơi về
QOnlineTranslator (scrape) như cũ. Xem
[hướng dẫn nhập API key](#5-cấu-hình-google-cloud-api-key) bên dưới để test đường GCP.

Checklist smoke test tối thiểu trước khi phát hành:
- [ ] Dịch text bằng engine Google **không có** API key → vẫn ra kết quả (đường cũ).
- [ ] Nhập API key hợp lệ trong Settings → Google Cloud → dịch lại → kết quả đúng, không
      còn phần "translation options"/"examples" (đúng trade-off đã biết).
- [ ] Nhập API key sai/rỗng-nhưng-invalid → thấy thông báo lỗi rõ ràng, không crash.
- [ ] Dịch bằng Yandex/Bing/LibreTranslate/Lingva vẫn hoạt động bình thường (không bị
      ảnh hưởng bởi thay đổi).
- [ ] Global shortcut dịch từ selection, OCR-dịch vùng màn hình vẫn hoạt động.
- [ ] Auto-detect ngôn ngữ nguồn hoạt động cho cả 2 đường (GCP và QOnlineTranslator).

## 5. Cấu hình Google Cloud API key

Xem chi tiết đầy đủ trong lịch sử trao đổi trước, tóm tắt:
- **GUI:** Settings → group box "Google Cloud" → ô "API key".
- **File config trực tiếp** (hữu ích khi deploy hàng loạt / CLI-only): thêm vào file
  `.conf`/`.ini` của app (`~/.config/crow-translate/crow-translate.conf` trên Linux, hoặc
  `settings.ini` cạnh binary nếu build `WITH_PORTABLE_MODE`):
  ```ini
  [Translation]
  GoogleCloudApiKey=YOUR_API_KEY_HERE
  ```

**Lưu ý bảo mật khi deploy:** key được lưu dạng plaintext trong QSettings (giống hệt
cách LibreTranslate/Lingva API key đã được lưu từ trước — không phải thay đổi mới của
tôi, mà là convention sẵn có của app). Nếu deploy cho nhiều người dùng dùng chung 1 máy,
cân nhắc giới hạn quyền đọc file config, hoặc mỗi user tự nhập key riêng của họ. Không
nên embed key vào package cài đặt sẵn (không hardcode vào binary).

## 6. Đóng gói (CPack)

**Debian/Ubuntu (.deb):**
```bash
mkdir build && cd build
cmake .. -D CMAKE_BUILD_TYPE=Release -D CPACK_GENERATOR=DEB
cmake --build . --target package
```

**Nhiều loại gói cùng lúc:**
```bash
cmake .. -D CMAKE_BUILD_TYPE=Release -D CPACK_GENERATOR="DEB;RPM;ZIP"
cmake --build . --target package
```

**Hoặc dùng CPack trực tiếp sau khi build:**
```bash
cd build
cpack -G DEB
```

CMake tự động lo phần cài đặt file `.desktop`, icon, metainfo, bản dịch UI (`.qm`) — xem
mục `install(...)` cuối `CMakeLists.txt`. Không cần chỉnh gì thêm cho phần Google Cloud
(không có file/asset mới cần đóng gói, chỉ là code + 1 setting).

## 7. Cài đặt trực tiếp (không qua package manager)

```bash
cd build
sudo cmake --install .
```
(tương đương `make install`, dùng `CMAKE_INSTALL_PREFIX` để đổi nơi cài, mặc định
`/usr/local`).

## 8. Windows (tóm tắt, dùng vcpkg)

```powershell
git clone https://github.com/microsoft/vcpkg.git
.\vcpkg\bootstrap-vcpkg.bat
.\vcpkg\vcpkg install --triplet x64-windows

mkdir build
cd build
cmake .. -D CMAKE_TOOLCHAIN_FILE=<path-to-vcpkg>/scripts/buildsystems/vcpkg.cmake -D VCPKG_TARGET_TRIPLET=x64-windows
cmake --build . --config Release --target package
```
CMake tự động chạy `windeployqt` và copy OpenSSL DLL cần cho Qt Network (xem cuối
`CMakeLists.txt`) — bước này **quan trọng hơn trước** vì giờ toàn bộ nhánh Google Cloud
phụ thuộc `Qt5::Network`/HTTPS, đảm bảo `libssl`/`libcrypto` DLL được bundle đúng.

## 9. Rollback / tắt tính năng Google Cloud khi deploy

Nếu muốn deploy một bản **không** có tuỳ chọn Google Cloud (ví dụ do chính sách nội bộ),
cách đơn giản nhất không cần sửa code: đơn giản là **không cấp API key** cho người dùng —
tính năng tự động không kích hoạt (engine Google vẫn hoạt động qua đường cũ). Không cần
build flag riêng vì thay đổi này không có compile-time toggle (xem
[TRANSLATION_MECHANISM.md](TRANSLATION_MECHANISM.md) mục kiến trúc).
