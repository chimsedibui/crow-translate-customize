# PyCrow — quy tắc làm việc cho Claude

File này chứa các rule Claude phải theo khi làm việc trong repo. Thêm rule mới vào mục
**Rule bổ sung** ở cuối file.

## Tổng quan

- App Python/PySide6/QML nằm ở `src/py_crow_tool`. Branch chính: `dev/python`.
- Test tự động: `.venv\Scripts\python.exe -m pytest -q tests`.
  Khi chạy từ một worktree, đặt `PYTHONPATH=<worktree>\src`. Nếu không, `.venv` sẽ import
  code ở checkout chính chứ không phải code trong worktree.
- Vai trò provider: Google lo dịch, Azure OpenAI lo OCR. Lựa chọn dịch bằng Azure luôn là
  opt-in, không bật mặc định.

## Quy trình test một thay đổi (bắt buộc)

Không cài đặt và không release bất cứ thứ gì trước khi người dùng test xong và xác nhận OK.

### 1. Build bản test tạm vào `dist/`

Bản test là file `dist\PyCrowTool.exe` của checkout chính (`crow\dist\`). Mỗi lần build
ghi đè bản test cũ. **Không chạy installer** ở bước này.

```powershell
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-windows.ps1
```

- Luôn xoá `build/` trước khi build. OneDrive giữ file trong đó và PyInstaller `--clean`
  sẽ fail với lỗi `Access is denied`.
- Không thêm `2>&1` vào lệnh build. PyInstaller ghi log ra stderr, và PowerShell 5.1 biến
  mỗi dòng log thành lỗi, nên báo "PyInstaller build failed." dù build thật ra vẫn ổn.
- Nếu code nằm trong worktree, đưa thay đổi vào checkout chính trước khi build, rồi để
  output vào `crow\dist\`. Không tạo `dist/` hay `.venv` riêng trong worktree.

### 2. Chạy bản test

1. Tắt bản đang cài (`%LOCALAPPDATA%\Programs\PyCrow Tool\PyCrowTool.exe`). App chỉ cho
   chạy một instance và hai bản sẽ tranh hotkey. Bản cài và bản test cùng tên tiến trình,
   nên phải dừng theo **đường dẫn file**, không dừng theo tên.
2. Chạy `dist\PyCrowTool.exe`. Settings và API key dùng chung với bản cài, không cần
   cấu hình lại.
3. Bản build local luôn báo version 1.0.0, nên app sẽ mời cập nhật. **Không bấm
   "Update now" trên bản test**: làm vậy sẽ cài đè bản release lên.
4. Báo người dùng cần test những gì, rồi chờ họ phản hồi.

### 3. Khi người dùng xác nhận OK, mới được cập nhật

Hỏi người dùng muốn cập nhật theo cách nào:

- **Installer local:** chạy `scripts/build-installer.ps1` (vẫn xoá `build/` trước, không
  dùng `2>&1`), sau đó chạy `installer\Output\PyCrowTool-Setup.exe`.
- **Release:** merge vào `dev/python`, push tag `vX.Y.Z`. CI sẽ build và publish GitHub
  Release, sau đó dùng nút **Update** trong app. Mỗi lần push tag cần người dùng duyệt.

Nếu bản test không ổn, hoặc người dùng chưa muốn cập nhật: tắt bản test và mở lại bản cài.

## Rule bổ sung

<!-- Thêm rule mới bên dưới. -->
