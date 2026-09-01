# Crow Translate — Tổng quan cơ chế dịch (Translation Mechanism)

> Ghi chú: repo checkout tại đây **không phải là git repo** (không có `.git`) và các
> git submodule đang **rỗng** (chưa clone): `src/qonlinetranslator`, `src/qgittag`,
> `src/third-party/qhotkey`, `src/third-party/qtaskbarcontrol`, `src/third-party/singleapplication`.
> Quan trọng nhất: **`src/qonlinetranslator` — nơi thực sự chứa code gọi API dịch
> (Google/Yandex/Bing/LibreTranslate/Lingva) — hiện KHÔNG có mặt trong checkout này.**
> Muốn xem/sửa logic gọi API thật sự, cần clone riêng:
> https://github.com/crow-translate/QOnlineTranslator

## 1. Bức tranh tổng thể

Crow Translate là app desktop C++/Qt5. Toàn bộ phần "dịch" của app (UI này) **không tự
implement** việc gọi Google/Yandex/Bing/LibreTranslate/Lingva — nó **ủy quyền hết** cho
một thư viện ngoài, `QOnlineTranslator`, được nhúng như git submodule tại
`src/qonlinetranslator`. App chỉ đóng vai trò:

- Chọn engine nào sẽ dùng (qua enum `QOnlineTranslator::Engine`).
- Gom text nguồn (gõ tay / selection toàn cục / OCR) rồi gọi `translate(...)`.
- Hiển thị / đọc (TTS) kết quả trả về.

→ Nếu mục tiêu là **customize cơ chế dịch** (đổi engine, thêm engine mới, đổi cách
build request, đổi parser response, thêm proxy/API-key logic riêng cho engine), phần
việc thật sự nằm trong repo `QOnlineTranslator`, không nằm trong repo `crow-tool` này.
Nếu mục tiêu là **customize cách app này sử dụng thư viện đó** (thêm lựa chọn engine
trên UI, đổi flow gọi dịch, đổi settings lưu trữ...), thì đúng chỗ.

## 2. Build wiring

- Không có `src/CMakeLists.txt` riêng — toàn bộ build nằm ở `CMakeLists.txt` gốc.
- Submodule được add vô điều kiện: `add_subdirectory(src/qonlinetranslator)` (`CMakeLists.txt:72`),
  cạnh các submodule khác (`singleapplication:69`, `qhotkey:70`, `qtaskbarcontrol:71`;
  riêng `qgittag` chỉ add `if(WIN32)` — dòng 73-75).
- Target được link vào executable chính dưới tên `QOnlineTranslator::QOnlineTranslator`
  (`CMakeLists.txt:238`).
- **Không có CMake option nào để bật/tắt từng engine** — cả 5 engine được compile cứng
  vào 1 thư viện; việc chọn engine hoàn toàn ở runtime qua enum `QOnlineTranslator::Engine`.
- `vcpkg.json` gốc chỉ khai báo `tesseract`, `qt5-winextras`/`qt5-x11extras`, `ecm`,
  `qt5-multimedia`, `qt5-svg`, `qt5-tools`, `qt5-translations` — không có dependency nào
  liên quan tới dịch (QOnlineTranslator không qua vcpkg, chỉ qua submodule).

## 3. Luồng dịch phía GUI (`src/mainwindow.cpp` / `.h`)

- `MainWindow` giữ **một** instance `QOnlineTranslator *m_translator` (khởi tạo tại
  `mainwindow.cpp:75`), dùng chung cho mọi tác vụ dịch trong cửa sổ chính.
- **Chọn engine:** lấy trực tiếp từ index của `QComboBox`:
  ```cpp
  // mainwindow.cpp:1118-1121
  QOnlineTranslator::Engine MainWindow::currentEngine() const
  {
      return static_cast<QOnlineTranslator::Engine>(ui->engineComboBox->currentIndex());
  }
  ```
  Thứ tự item trong combo box (`mainwindow.ui:189-241`) — Google(0), Yandex(1), Bing(2),
  LibreTranslate(3), Lingva(4) — **phải khớp** thứ tự giá trị enum `QOnlineTranslator::Engine`.
  Đây là điểm dễ vỡ nhất nếu muốn thêm/xoá engine: phải sửa đồng bộ cả `.ui` lẫn enum
  bên thư viện.
- **Gọi dịch** — toàn app được điều phối bởi một `QStateMachine` (`buildStateMachine()`,
  `mainwindow.cpp:609-666`). Điểm gọi API thật sự:
  ```cpp
  // mainwindow.cpp:354-363
  void MainWindow::requestTranslation()
  {
      ...
      m_translator->translate(ui->sourceEdit->toSourceText(), currentEngine(),
                               translationLang, ui->sourceLanguagesWidget->checkedLanguage());
  }
  ```
  Kết quả được lấy ra khi signal `finished` của `m_translator` bắn, xử lý ở
  `MainWindow::displayTranslation()` (`mainwindow.cpp:373-393`), gọi
  `ui->translationEdit->parseTranslationData(m_translator)`.
- **Auto-detect ngôn ngữ nguồn:**
  `requestSourceLanguage()` → `m_translator->detectLanguage(text, currentEngine())`
  (`mainwindow.cpp:401-404`), kết quả đọc ở `parseSourceLanguage()` (406-414).
- **Lọc engine theo ngôn ngữ hỗ trợ:**
  ```cpp
  // mainwindow.cpp:1092-1100
  if (!QOnlineTranslator::isSupportTranslation(currentEngine(), checkedLang)) {
      for (int i = 0; i < ui->engineComboBox->count(); ++i) {
          if (QOnlineTranslator::isSupportTranslation(static_cast<QOnlineTranslator::Engine>(i), checkedLang)) {
              ui->engineComboBox->setCurrentIndex(i);
              break;
          }
      }
      return;
  }
  ```
- **Cấu hình engine tự host (LibreTranslate/Lingva)** — URL + API key nạp từ settings:
  ```cpp
  // mainwindow.cpp:987-989
  m_translator->setEngineUrl(QOnlineTranslator::LibreTranslate, settings.engineUrl(QOnlineTranslator::LibreTranslate));
  m_translator->setEngineApiKey(QOnlineTranslator::LibreTranslate, settings.engineApiKey(QOnlineTranslator::LibreTranslate));
  m_translator->setEngineUrl(QOnlineTranslator::Lingva, settings.engineUrl(QOnlineTranslator::Lingva));
  ```
- **TTS (đọc to)** cấu hình riêng cho Yandex (voice/emotion) và Google (regions),
  `mainwindow.cpp:1010-1015`; việc đọc thực hiện qua `SpeakButtons::speak(text, lang, currentEngine())`
  (dùng `QOnlineTts` nội bộ).
- **Các flow khác đều tái sử dụng cùng state `buildTranslationState`:**
  - `buildTranslateSelectionState` — dịch text đang bôi đen (global hotkey), dựa vào
    `src/selection.cpp/h` (singleton `Selection::instance()` bắt selection của OS).
  - `buildRecognizeScreenAreaState` + `buildTranslateScreenAreaState` — chụp vùng màn
    hình → OCR (`src/ocr/ocr.cpp`, dùng Tesseract) → text đó chạy tiếp qua
    `buildTranslationState` y hệt text gõ tay.
  - `buildSpeakSourceState` / `buildSpeakTranslationState` / các biến thể "Selection" —
    TTS variants.

## 4. Luồng dịch phía CLI (`src/cli.cpp` / `.h`)

- `Cli` có `QOnlineTranslator *m_translator` riêng (khởi tạo `cli.cpp:38`) — **hoàn toàn
  tách biệt** với instance của `MainWindow`, không share.
- Option `-e/--engine` map string → enum bằng chuỗi if/else (`cli.cpp:129-144`):
  ```cpp
  if (parser.value(engine) == QLatin1String("google")) {
      m_engine = QOnlineTranslator::Google;
  } else if (... == "yandex") { m_engine = QOnlineTranslator::Yandex;
  } else if (... == "bing") { m_engine = QOnlineTranslator::Bing;
  } else if (... == "libretranslate") {
      m_engine = QOnlineTranslator::LibreTranslate;
      m_translator->setEngineUrl(QOnlineTranslator::Engine::LibreTranslate, AppSettings().engineUrl(...));
  } else if (... == "lingva") {
      m_engine = QOnlineTranslator::Lingva;
      m_translator->setEngineUrl(QOnlineTranslator::Engine::Lingva, AppSettings().engineUrl(...));
  } else {
      qCritical() << tr("Error: Unknown engine") << '\n';
      parser.showHelp();
  }
  ```
  → Đây là điểm **dễ nhất để thêm 1 engine mới ở phía app** (thêm 1 nhánh `else if`),
  với điều kiện engine đó đã tồn tại trong enum `QOnlineTranslator::Engine` (tức đã được
  implement bên thư viện `QOnlineTranslator`).
- Gọi dịch: `m_translator->translate(m_sourceText, m_engine, translationLang, m_sourceLang, m_uiLang)`
  (`cli.cpp:166-172`) — có thêm tham số thứ 5 `m_uiLang` (ngôn ngữ hiển thị translation
  options/examples) so với GUI chỉ truyền 4 tham số.
- In kết quả: `Cli::printTranslation()` (`cli.cpp:186-256`) đọc `toJson()`, `translation()`,
  `translationOptions()`, `examples()`... từ cùng `QOnlineTranslator` object.
- TTS trong CLI **không đi qua `QOnlineTranslator`** mà build `QOnlineTts` trực tiếp:
  ```cpp
  // cli.cpp:350-363
  QOnlineTts tts;
  tts.generateUrls(text, m_engine, lang);
  ...
  m_player->playlist()->addMedia(tts.media());
  m_player->play();
  ```
- `--codes`: `Cli::printLangCodes()` (`cli.cpp:274-280`) lặp `QOnlineTranslator::Auto` →
  `QOnlineTranslator::Zulu`, gọi `languageName`/`languageCode` tĩnh của thư viện.

## 5. `src/main.cpp` — điểm rẽ nhánh GUI/CLI

```cpp
int main(int argc, char *argv[])
{
    ...
    if (argc == 1)
        return launchGui(argc, argv);
    return launchCli(argc, argv);
}
```
- Không có argument → GUI (`SingleApplication` + `MainWindow`, đăng ký D-Bus object cho
  `translateSelection()`, `translateScreenArea()`... để desktop environment / `qdbus`
  gọi từ ngoài).
- Có argument → CLI (`QCoreApplication` + `Cli::process`).
- Hai path **share `AppSettings`** (nên `engineUrl`/`engineApiKey` của LibreTranslate/Lingva
  dùng chung giữa GUI và CLI) nhưng **không share `QOnlineTranslator` instance**.

## 6. Settings liên quan tới dịch (`src/settings/appsettings.h` / `.cpp`)

Class `AppSettings` (persist qua `QSettings`) là nơi lưu mọi config runtime. Các phần
liên quan trực tiếp tới cơ chế dịch:

| Nhóm | Getter/Setter | Vị trí |
|---|---|---|
| Engine hiện tại | `currentEngine()` / `setCurrentEngine(QOnlineTranslator::Engine)` | `appsettings.h:382-383` |
| Auto-translate | `isAutoTranslateEnabled()` / `setAutoTranslateEnabled(bool)` | `appsettings.h:379-380` |
| Ngôn ngữ đích chính/phụ | `primaryLanguage()`/`secondaryLanguage()` + setters | `appsettings.h:192-198` |
| Ép auto-detect | `isForceSourceAutodetect()`, `isForceTranslationAutodetect()` | `appsettings.h:200-206` |
| URL/API key engine tự host | `engineUrl(Engine)`, `engineApiKey(Engine)` + setters (LibreTranslate, Lingva) | `appsettings.h:208-214` |
| Hiển thị chi tiết bản dịch | `isSourceTranslitEnabled`, `isTranslationOptionsEnabled`, `isExamplesEnabled`, `isSimplifySource`,... | `appsettings.h:168-190` |
| Danh sách/nút ngôn ngữ đã lưu | `languages(LanguageButtonsType)`, `checkedButton(...)` | `appsettings.h:369-373` |
| TTS engine config | `voice(Engine)`, `emotion(Engine)`, `regions(Engine)` | `appsettings.h:216-227` |
| Proxy (ảnh hưởng mọi engine HTTP) | `proxyType/Host/Port`, `isProxyAuthEnabled`, `proxyUsername/Password` | `appsettings.h:230-252` |
| Global shortcuts liên quan dịch | `translateSelectionShortcut`, `translateScreenAreaShortcut`,... | `appsettings.h:259-326` |
| OCR (nguồn text đầu vào) | `ocrLanguagesPath`, `tesseractParameters`, `cropRegion`,... | `appsettings.h:329-366` |

Các file khác trong `src/settings/` chỉ là hạ tầng UI/OS, không liên quan trực tiếp cơ
chế dịch: `settingsdialog.*` (dialog cài đặt, bind vào `AppSettings`),
`autostartmanager/` (chạy cùng OS), `shortcutsmodel/` (bảng shortcut editor),
`ocrlanguageslistwidget.*`, `tesseractparameterstablewidget.*`.

## 7. OCR → dịch (`src/ocr/`)

```
ocr.cpp / ocr.h                          — wrapper Tesseract OCR: recognize(QPixmap, dpi) → signal recognized(QString)
snippingarea.cpp / .h                    — overlay chọn vùng màn hình để chụp
screengrabbers/abstractscreengrabber.*   — interface chung cho các backend chụp màn hình
screengrabbers/genericscreengrabber.*    — chụp trên X11/Windows/macOS
screengrabbers/dbusscreengrabber.*       — chụp qua D-Bus portal
screengrabbers/waylandgnomescreengrabber.*    — Wayland/GNOME
screengrabbers/waylandplasmascreengrabber.*   — Wayland/KDE Plasma
screengrabbers/waylandportalscreengrabber.*   — Wayland/XDG desktop portal generic
```
OCR chỉ là **nguồn sinh text** — text nhận diện được feed thẳng vào cùng
`buildTranslationState`/`QOnlineTranslator::translate(...)` như text gõ tay, không có
logic dịch riêng ở đây.

## 8. Localization UI (khác với "cơ chế dịch")

Lưu ý phân biệt: `crowdin.yml` + `data/translations/*.ts` (Qt Linguist) chỉ là **dịch
chuỗi giao diện** (i18n UI — menu, tooltip, dialog...) sang các ngôn ngữ khác, **không
liên quan** tới engine dịch văn bản người dùng nhập. Nếu mục tiêu của bạn là "dịch app
sang tiếng Việt" thì đây mới là chỗ cần — thêm file
`data/translations/crow-translate_vi_VN.ts` và dịch qua Qt Linguist.

## 9. Kết luận — muốn customize thì sửa ở đâu?

| Muốn làm gì | Sửa ở đâu |
|---|---|
| Đổi cách gọi API của 1 engine có sẵn (Google/Yandex/Bing/LibreTranslate/Lingva), sửa parser response, thêm header/tham số request | Repo ngoài `QOnlineTranslator` (`src/qonlinetranslator` — cần `git clone https://github.com/crow-translate/QOnlineTranslator` vào đó) |
| Thêm 1 engine dịch hoàn toàn mới | Trước tiên implement trong `QOnlineTranslator` (thêm giá trị enum `Engine`, logic request/response), sau đó ở app này: thêm item vào `mainwindow.ui` combo box đúng thứ tự enum, thêm nhánh `else if` trong `cli.cpp:129-144`, thêm `engineUrl/engineApiKey` trong `AppSettings` nếu engine cần cấu hình endpoint/key |
| Đổi flow dịch (khi nào tự động dịch, dịch từ selection/OCR, delay,...) | `src/mainwindow.cpp` (các hàm `build*State`) |
| Đổi CLI options / cách chọn engine qua dòng lệnh | `src/cli.cpp` |
| Đổi nơi lưu / thêm setting mới cho engine | `src/settings/appsettings.h` + `.cpp` |
| Dịch giao diện app sang ngôn ngữ khác (không phải engine dịch) | `data/translations/*.ts` + `crowdin.yml` |

**Việc đầu tiên cần làm trước khi động vào "cơ chế dịch" thực sự:** clone submodule
`QOnlineTranslator` vào `src/qonlinetranslator` (hiện đang rỗng), vì toàn bộ logic gọi
API dịch (request building, parsing JSON response của Google/Yandex/Bing/LibreTranslate/Lingva)
nằm ở đó, không nằm trong repo `crow-tool`.
