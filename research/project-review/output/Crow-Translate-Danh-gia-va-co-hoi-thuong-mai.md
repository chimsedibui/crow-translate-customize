# Crow Translate — Đánh giá dự án và cơ hội thương mại

**Ngày đánh giá:** 16/09/2026  
**Phạm vi:** bản viết lại bằng Python tại commit `f85adfbf7327`  
**Dành cho:** chủ dự án và nhóm kỹ thuật, sản phẩm.

> Giá, mục tiêu và kế hoạch trong tài liệu là đề xuất để kiểm chứng. Các thử nghiệm thương mại chưa được thực hiện.

## Thông tin tài liệu

| Trường | Nội dung |
| --- | --- |
| Phiên bản | 1.0 |
| Biên soạn | Codex dựa trên mã nguồn không gian làm việc |
| Người sử dụng | Chủ dự án và nhóm kỹ thuật sản phẩm |
| Ngày đánh giá | 16 tháng 09 năm 2026 |
| Phạm vi | Bản viết lại bằng Python tại commit f85adfbf7327 |
| Trạng thái | Đề xuất để quyết định đầu tư và thử nghiệm |

## Kết luận và mục tiêu

Crow Translate có nền tảng tốt cho một công cụ dịch máy tính chạy trong luồng công việc. Chưa đủ bằng chứng để kết luận dự án sẵn sàng bán rộng rãi hoặc đã có nhu cầu trả phí. Khuyến nghị ưu tiên sửa độ tin cậy và quản lý dữ liệu, sau đó thử một MVP cho nhóm CSKH và vận hành dùng Windows, với bảng thuật ngữ chung và bộ nhớ bản dịch.

Tài liệu giúp chủ dự án chọn việc cần làm trước, xác định tính năng có khả năng tạo doanh thu và thiết kế phép thử trước khi đầu tư lớn. Các phát hiện code, kết quả kiểm tra, nhận định sản phẩm và giả thuyết thương mại được ghi riêng. Giá, mục tiêu và thời lượng triển khai là đề xuất, không phải kết quả kinh doanh hay cam kết giao hàng.

## Sản phẩm và cơ hội thị trường

Bản Python dùng PySide6 và QML, có dịch Google Đám mây Basic v2, chọn và phát hiện ngôn ngữ, GUI và CLI, tray, chỉ chạy một phiên ứng dụng, phím tắt dịch clipboard và vùng chọn, cửa sổ dịch nhanh có ghim, OCR từ ảnh clipboard hoặc vùng màn hình, TTS và lịch sử tìm kiếm. Tesseract xử lý OCR cục bộ; OpenAI Vision là lựa chọn OCR đám mây. OCR cục bộ không đồng nghĩa bản dịch chạy ngoại tuyến vì bộ cung cấp dịch vụ dịch tích hợp sẵn vẫn là Google Đám mây.

Lợi ích có thể bán là giảm thời gian chuyển ứng dụng và giữ thuật ngữ nhất quán trong công việc lặp lại. DeepL máy tính đã có phím tắt, chụp màn hình, bảng thuật ngữ và dịch tệp [S1], nên OCR ảnh chụp màn hình đơn lẻ chưa tạo lợi thế đủ mạnh. Đề xuất tập trung một nhóm khách hàng có quy trình cụ thể, đo thời gian hoàn thành công việc và lỗi thuật ngữ, rồi mới mở rộng. Chưa có dữ liệu quy mô thị trường hoặc mức sẵn sàng trả phí của dự án.

## Hiện trạng theo thành phần

| Thành phần | Quan sát và mức hoàn thiện |
| --- | --- |
| Kiến trúc | Core model có kiểu dữ liệu; bộ cung cấp dịch vụ và dịch vụ tách khỏi QML. Có thể mở rộng nhưng viewmodels.py gộp nhiều trách nhiệm. |
| Dịch văn bản | Google v2 gọi API có giới hạn thời gian, thử lại và phân loại lỗi; chưa thấy bộ nhớ bản dịch hoặc sổ theo dõi chi phí. |
| Plugin cung cấp dịch vụ | Entry point và allowlist đã có. Lưu tùy chọn thay bộ quản lý bằng Google duy nhất; cấu hình plugin chưa truyền từ bootstrap. |
| GUI | Chọn ngôn ngữ, swap, dịch tự động và lịch sử đã có; UI hiện dùng tiếng Anh. |
| Phím tắt Windows | Code hiện dùng RegisterHotKey native; README vẫn nhấn mạnh keyboard hook. Cần cập nhật tài liệu. |
| Quick translate | Chụp văn bản selection qua copy và trả lại clipboard; cần kiểm tra rich clipboard và ứng dụng đặc biệt. |
| Capture screenshot | Có overlay theo màn hình và vùng ảnh cắt bộ nhớ; chưa thấy chuyển tọa độ logic sang pixel theo từng màn hình. |
| OCR cục bộ | Tesseract chạy qua asyncio.to_thread; chỉ map vi và en sang tên gói ngôn ngữ. |
| OCR đám mây | Có đổi kích thước ảnh và siêu dữ liệu về mức sử dụng ở bộ cung cấp dịch vụ; dịch vụ chỉ phát văn bản nên UI không nhận chi phí hoặc cảnh báo. |
| Điều phối OCR | Có tracker riêng cho clipboard và region để bỏ kết quả cũ; chưa tự hủy các request bị thay thế. |
| TTS | Dựa trên giọng hệ điều hành, chọn locale nếu có; im lặng khi thiếu engine. |
| Lịch sử | JSON trong user data, mặc định 100 mục; có clear nhưng chưa có TTL, phiên riêng tư hoặc ghi dữ liệu tuần tự. |
| Cấu hình | TOML thay file qua temporary; Khóa API lưu dạng văn bản thuần. Chưa xử lý TOML hỏng hoặc field lạ khi khởi động. |
| Đóng gói | Có PyInstaller và Inno Setup per user; build script cài dependency rồi build, chưa dùng lockfile để cố định môi trường. |
| Kiểm thử | 61 test được thu thập trong lần chạy toàn bộ; có test QML, bộ cung cấp dịch vụ HTTP, bất đồng bộ và máy tính. |
| Quan sát vận hành | Chưa thấy telemetry sản phẩm, crash reporter, hạn mức gateway, subscription hay dashboard đội nhóm. |
| Nền tảng | Windows có đường tích hợp cụ thể; startup ở platform khác trả về. Chưa kiểm chứng Linux và macOS. |
| Giấy phép | README và pyproject khai báo GPL 3.0 or later; không thấy Giấy phép trong danh sách tệp repo đã kiểm tra. |

## Phương pháp và độ chắc chắn

Đánh giá dựa trên README, cấu hình build, các module core bộ cung cấp dịch vụ dịch vụ, QML, test và tài liệu nghiên cứu OCR có sẵn. Đã chạy pytest bằng virtual environment của dự án trên Windows. Không gửi dữ liệu lên API thật, không chạy benchmark có tính phí và không thay đổi code sản phẩm. Các vị trí nguồn được ghi ở phụ lục để kiểm tra lại.

Mức chắc chắn cao áp dụng cho hành vi đọc được trực tiếp từ code và lỗi test lặp lại. Rủi ro DPI và ghi lịch sử đồng thời cần phép thử tái hiện riêng. Tài liệu OCR ngày 06/09/2026 mô tả trạng thái cũ: screenshot picker, gợi ý ngôn ngữ và cơ chế theo dõi kết quả cũ đã xuất hiện trong code hiện tại. Không dùng tài liệu cũ để kết luận các tính năng này còn thiếu.

## Giả thuyết thương mại ưu tiên

Nếu nhóm CSKH và vận hành thường dịch câu trả lời, email và ảnh chụp với cùng thuật ngữ, bảng thuật ngữ được quản lý theo nhóm và bộ nhớ bản dịch có thể giảm thời gian sửa, tạo lý do trả phí hàng tháng. Đây là giả thuyết ưu tiên vì tận dụng cửa sổ dịch nhanh, phím tắt và lịch sử hiện có. Nhánh người học ngôn ngữ và dịch tài liệu hàng loạt là cơ hội phụ, chỉ phát triển sau khi thử nghiệm xác nhận nhu cầu.

## Tiêu chí cho bản thử nghiệm thực tế

Các ngưỡng dưới đây là mục tiêu thử nghiệm ban đầu, chưa được đo. Trước thử nghiệm thực tế phải chốt cách đo và mốc đối chiếu ban đầu. Không công bố SLA cho đến khi đã có kết quả trên bộ cài sạch và thiết bị khách hàng.

| Chỉ số | Mục tiêu và quy tắc đề xuất |
| --- | --- |
| Độ tin cậy | Toàn bộ test bắt buộc đạt; test bất đồng bộ không phụ thuộc tốc độ hoàn tất tức thời. Phím tắt, startup và cửa sổ dịch nhanh đạt smoke test Windows. |
| Kích hoạt | Ít nhất 80% người tham gia hoàn tất bản dịch đầu tiên trong 5 phút, từ lúc mở bộ cài. |
| Chất lượng | Bản có bảng thuật ngữ giảm lỗi thuật ngữ ít nhất 30% trên tập công việc so với mốc đối chiếu ban đầu, không tăng lỗi số và tên riêng. |
| Giá trị sử dụng | Trung vị thời gian hoàn tất tác vụ giảm ít nhất 20%, đo bằng tác vụ ghép cặp; tỷ lệ duy trì sử dụng tuần 4 ít nhất 50% nhóm người dùng cùng đợt đã kích hoạt. |
| Quyết định | Tiếp tục khi có ít nhất 3 tổ chức trả phí thử trong 5 tổ chức thử nghiệm thực tế, điều kiện bảo vệ dữ liệu đạt và hiệu quả kinh tế trên mỗi đơn vị sử dụng đáp ứng ngưỡng. Đây là tín hiệu định hướng, không chứng minh thị trường rộng. |

## Kiểm tra trước khi phát hành thử nghiệm thực tế

- Thiết lập CI Windows và chạy test cả tuần tự lẫn lặp lại phần bất đồng bộ. Xác nhận test phím tắt kiểm tra hành vi conflict, rồi thống nhất yêu cầu về thông báo cụ thể.

- Kiểm tra lưu cấu hình khi plugin đang bật, khi Google khóa API đổi và khi một yêu cầu dịch đang chạy. Đảm bảo ghi settings hoàn tất trước khi báo thành công, bộ quản lý giữ plugin và lỗi factory không làm app sập.

- Kiểm tra vùng ảnh cắt trên scale 100%, 125%, 150% và 200%, hai màn hình scale khác nhau, màn hình trái có tọa độ âm và màn hình dọc. Đối chiếu ảnh vùng ảnh cắt với vùng đã chọn, không chỉ nhìn OCR văn bản.

- Kiểm tra hủy yêu cầu OCR, đóng app giữa request và chụp mới khi request cũ chưa xong. Theo dõi số request thực gửi, thời hạn xử lý và bộ nhớ; bỏ kết quả cũ trên UI chưa đủ để kiểm soát chi phí.

- Chạy bộ cài trên Windows sạch không có Python hoặc Tesseract trong PATH. Kiểm tra OCR eng và vie, ký số, upgrade, uninstall, tray và startup. Chưa coi sự tồn tại của file dist là bằng chứng bản phát hành đã đạt.

## Kết quả kiểm thử trong đánh giá

Lần chạy toàn bộ đạt 58 test, lỗi 2 test và bỏ qua 1 test trong 1,70 giây. Chạy lại cặp lỗi riêng đạt test translation state và vẫn lỗi phím tắt message. Test translation state tiếp tục đạt ở hai lần chạy riêng bổ sung. Không sửa test trong phạm vi đánh giá. Các lần chạy có tập test khác nhau nên không diễn giải như kết quả A/B hoặc độ tin cậy thực tế.

| Hạng mục | Chạy toàn bộ | Xác minh sau đó |
| --- | --- | --- |
| Số test | 61 test | 2 test mục tiêu, thêm 2 lần test bất đồng bộ riêng |
| Đạt | 58 | Test trạng thái dịch đạt trong cặp và hai lần riêng |
| Lỗi | 2 | Phím tắt message vẫn lỗi |
| Bỏ qua | 1 | Không nằm trong tập chạy mục tiêu |
| Diễn giải | Suite hiện chưa xanh | 1 mismatch lặp lại và 1 dấu hiệu phụ thuộc thời điểm |

## Danh sách công việc cải tiến kỹ thuật

| Mã và ưu tiên | Thay đổi | Công sức | Tác động | Tiêu chí hoàn tất |
| --- | --- | --- | --- | --- |
| T1 P0 | Chuẩn hóa test phím tắt và bất đồng bộ | 1 đến 2 ngày | Chặn release lỗi | Suite đạt và test bất đồng bộ lặp lại ổn định |
| T2 P0 | Lưu secret qua Credential Bộ quản lý và tách chính sách dữ liệu | 3 đến 5 ngày | Tin cậy khách hàng | TOML không còn khóa API mới, migration có kiểm tra |
| T3 P0 | Đổi HistoryStore sang ghi file nguyên tử và một writer | 2 đến 4 ngày | Tránh mất dữ liệu | Stress add flush clear không tạo file hỏng hoặc phục hồi nội dung đã xóa |
| T4 P0 | Giữ plugin cung cấp dịch vụ sau save và truyền cấu hình plugin | 2 đến 4 ngày | Mở rộng được | Plugin hoạt động trước sau save, factory lỗi có thông báo |
| T5 P1 | Hàng đợi OCR có giới hạn, hủy yêu cầu và giới hạn thời gian | 4 đến 7 ngày | Độ trễ và chi phí | Một active và một pending mới nhất; hủy yêu cầu vô hiệu hóa kết quả ngay |
| T6 P1 | Sửa hoặc chứng minh vùng ảnh cắt đúng theo DPI | 2 đến 5 ngày | Chính xác screenshot | Ma trận multi monitor và scale đạt |
| T7 P1 | Xem sửa OCR trước dịch và giữ siêu dữ liệu | 4 đến 7 ngày | Giảm lỗi số và gửi nhầm | Ảnh vùng ảnh cắt văn bản sửa được, cảnh báo và mức sử dụng tới UI |
| T8 P1 | Validate config, khôi phục TOML hỏng và khóa API lạ | 2 đến 3 ngày | Khởi động bền | App mở với cảnh báo recovery, settings hợp lệ không mất |
| T9 P1 | Build từ lockfile, ký số và quy trình update | 4 đến 7 ngày | Phân phối thương mại | Installer sạch đạt, artifact hash và upgrade rollback được kiểm tra |
| T10 P2 | Tách viewmodels theo chức năng và chuẩn hóa lỗi | 3 đến 5 ngày | Bảo trì dễ hơn | Translation settings và OCR có owner rõ, hành vi giữ nguyên |

P0 cần xong trước thử nghiệm thực tế có thu phí. Công sức là ước tính kỹ sư ngày cho một người quen code, chưa gồm mua chứng thư ký số, kiểm thử khách hàng hoặc review. Các hạng mục có thể chồng phần việc nên không cộng thành lịch chắc chắn. Ưu tiên dựa trên mức ảnh hưởng đến người dùng và điều kiện của MVP, không dùng điểm ROI giả định.

## Rủi ro dữ liệu và độ tin cậy

| Rủi ro | Hiện trạng | Biện pháp | Ưu tiên | Xác minh |
| --- | --- | --- | --- | --- |
| Secret | Khóa API trong TOML | OS secret store và redaction log URL | P0 | Kiểm tra file và log không lộ khóa API |
| Lịch sử | Ghi JSON trực tiếp; hai VM dùng chung store | Snapshot bất biến, writer tuần tự, thay file nguyên tử, TTL | P0 | Flush clear đồng thời và crash giữa ghi |
| Đám mây | Settings đã báo OpenAI nhận ảnh; screenshot flow dịch ngay | Review draft, chính sách cục bộ only và chỉ báo destination | P0 | Cục bộ only không phát network dịch hoặc OCR đám mây |
| Plugin | Python plugin có quyền như app; factory lỗi lan ra | Allowlist, validate schema và cô lập lỗi load | P0 | Plugin lỗi không chặn app còn bộ cung cấp dịch vụ hợp lệ |

Quyền file hạn chế và ô nhập mật khẩu không thay thế kho lưu thông tin bí mật. Credential Bộ quản lý không bảo vệ khỏi mọi mã chạy dưới cùng tài khoản, nhưng giảm việc khóa API nằm rõ trong file cấu hình và bản sao lưu. Chính sách cục bộ only phải chặn cả OCR đám mây lẫn dịch đám mây, kể cả dịch tự động và CLI. Chỉ lưu ảnh hoặc văn bản nhạy cảm khi người dùng hoặc tổ chức đã chọn chế độ lưu.

## Tính năng mới có tiềm năng thương mại

Các đề xuất sau chưa có trong sản phẩm ở mức hoàn chỉnh. Khách hàng, giá trị và khả năng trả phí đều cần xác minh. F1 và F2 tạo MVP đầu tiên, F3 là điều kiện để phục vụ đội nhóm; những nhánh còn lại không nên làm cùng lúc.

| Tính năng | Khách hàng | Giá trị trả phí | MVP | Ưu tiên |
| --- | --- | --- | --- | --- |
| F1 Bảng thuật ngữ nhóm | CSKH và vận hành | Tên sản phẩm thuật ngữ nhất quán | CSV nhập dữ liệu, version, quy tắc và cảnh báo | Ưu tiên đầu |
| F2 Bộ nhớ bản dịch | Nhóm có câu lặp | Tái dùng bản đã duyệt và giảm API | Khớp chính xác có nguồn duyệt, sửa và lưu | Ưu tiên đầu |
| F3 Không gian làm việc quản trị | Trưởng nhóm IT | Chính sách đám mây, ngân sách và hướng dẫn sử dụng ban đầu | Vai trò admin member, hạn mức, chính sách sync | Sau tín hiệu thử nghiệm thực tế |
| F4 OCR kiểm chứng | Logistics thương mại điện tử | Giảm sai SKU số lượng giá trong ảnh | Review vùng ảnh cắt và cảnh báo số trước dịch | Nâng chất lượng |
| F5 Ngoại tuyến hoặc triển khai tại hạ tầng khách hàng | Tổ chức có yêu cầu dữ liệu | Xử lý tại chỗ và triển khai kiểm soát | Một bộ cung cấp dịch vụ dịch cục bộ, model giấy phép rõ | Theo hợp đồng |
| F6 Dịch tệp theo lô | Nhóm localization | Rút ngắn xử lý TXT CSV subtitle | Xem trước, job hàng đợi, giữ ID và xuất dữ liệu | Thử sau |
| F7 Sổ từ và ôn tập | Người học ngôn ngữ | Chuyển lịch sử thành học tập | Save word, câu ví dụ và xuất dữ liệu Anki | Nhánh phụ |

F1 cần tránh thay chuỗi sau dịch một cách mù quáng vì có thể sai ngữ pháp hoặc phá tên riêng. Bộ cung cấp dịch vụ cần capability bảng thuật ngữ; bộ cung cấp dịch vụ không hỗ trợ thì ưu tiên cảnh báo và gợi ý kiểm tra. F2 bắt đầu bằng khớp chính xác theo ngôn ngữ nguồn, ngôn ngữ đích bộ cung cấp dịch vụ phiên bản bảng thuật ngữ và chính sách. Bản máy dịch chưa duyệt không được coi là bộ nhớ bản dịch chuẩn; nội dung giữa tổ chức phải tách biệt.

## Giới hạn và điều kiện thương mại

- Chưa có số người dùng, tỷ lệ duy trì của từng nhóm người dùng, lượt dịch, phân phối lượng văn bản, doanh thu, CAC hoặc phỏng vấn khách hàng. Vì vậy chưa tính TAM, không dự báo doanh thu và không khẳng định mức phù hợp giữa sản phẩm và thị trường.

- Chưa benchmark OCR hiện tại trên bộ dữ liệu đa dạng. Script bench_ocr_openai.py có CER, percentile độ trễ và mức sử dụng, nhưng không thấy output benchmark đã lưu trong tập tệp đọc; comment trong mã nguồn không đủ làm kết quả đo chính thức.

- Các test phần lớn dùng bộ cung cấp dịch vụ giả lập, không xác minh API thật, tính khả dụng của giọng đọc hoặc hoạt động của installer trên máy sạch. Rủi ro DPI và writer race dựa trên đường code cần tái hiện trước khi gọi là lỗi sản phẩm đã xác nhận.

- README tuyên bố nhiều nền tảng nhưng startup code chỉ có Windows và phím tắt Windows đã chuyển native. Nên chọn Windows cho thử nghiệm thực tế và công bố ma trận tính năng theo OS thay vì hứa parity chưa kiểm tra.

- GPL cho phép bán phần mềm nhưng phân phối bản sửa vẫn phải tuân thủ GPL, gồm cung cấp mã nguồn theo điều kiện áp dụng và quyền sửa phân phối của người nhận [S3]. Không coi dịch vụ phía máy chủ riêng hoặc mua giấy phép Qt là cách tự động xóa nghĩa vụ GPL của code ứng dụng. Cần kiểm tra provenance quyền tác giả, dependency giấy phép và cách đóng gói Qt trước phát hành [S4].

Khuyến nghị duy trì máy tính theo GPL và bán dịch vụ không gian làm việc, vận hành hoặc hỗ trợ, sau khi kiểm tra ranh giới giấy phép cụ thể. Không giả định có quyền relicensing toàn bộ dự án. Nếu muốn máy tính độc quyền, cần xác minh quyền của từng contributor và mã kế thừa. Đây là điều kiện mô hình kinh doanh cần chủ dự án chốt, không phải chứng nhận tuân thủ pháp lý.

## MVP và hướng kinh doanh

MVP đề xuất gồm bản Windows ổn định, hướng dẫn sử dụng ban đầu khóa API và OCR, bảng thuật ngữ cá nhân hoặc nhóm nhỏ, bộ nhớ bản dịch khớp chính xác, phiên riêng tư, hạn mức và hiển thị nơi xử lý dữ liệu. Bắt đầu cùng 5 tổ chức CSKH hoặc vận hành có 5 đến 20 người cần dịch Việt Anh. Nhóm này là đối tượng tuyển thử đề xuất, chưa phải khách hàng hiện hữu. Cách tiếp cận đầu là demo một quy trình thật, nhập bảng thuật ngữ của họ và so thời gian xử lý trước sau.

Giai đoạn đầu có thể dùng BYOK, tức khách hàng tự cung cấp khóa API, để tách nhu cầu trả tiền cho quy trình làm việc khỏi chi phí suy luận. Gói do nhà cung cấp quản lý chỉ làm khi đã có sổ theo dõi chi phí, hạn mức và cơ chế ngăn lạm dụng. Không dùng gói unlimited khi chưa biết lượng sử dụng. Dịch PDF giữ layout, hội thoại real time và GPU OCR chưa thuộc MVP 90 ngày.

## Các quyết định cần chủ dự án chốt

| Nội dung | Khuyến nghị để xem xét |
| --- | --- |
| Khách hàng đầu | CSKH và vận hành Windows, Việt Anh, có bảng thuật ngữ và công việc lặp |
| Phạm vi đầu tư | Hoàn tất P0 và thử F1 và F2 trước không gian làm việc đầy đủ |
| Mô hình giấy phép | Giữ máy tính GPL; rà soát giấy phép và quyền mã nguồn trước đóng gói |
| Kênh thử | 5 tổ chức được tuyển trực tiếp, thử nghiệm thực tế có hỗ trợ và giá thử rõ |
| Điều kiện dừng | Sự cố lộ dữ liệu, chi phí vượt hạn mức hoặc không đạt giá trị công việc |
| Bước tiếp theo | Đo mốc đối chiếu ban đầu, sửa P0, tuyển thử nghiệm thực tế; chưa có quyết định triển khai được phê duyệt |

## Kế hoạch 90 ngày đề xuất

- Ngày 1 đến 15: kỹ thuật xử lý T1 đến T4 và khôi phục cấu hình; sản phẩm phỏng vấn 10 người thuộc nhóm khách hàng đích để chọn một tác vụ lặp. Đầu ra là mốc đối chiếu ban đầu, issue có tiêu chí nghiệm thu và bản chạy ổn định. Nếu không tìm thấy công việc đủ lặp, điều chỉnh phân khúc trước xây dịch vụ phía máy chủ cho đội nhóm.

- Ngày 16 đến 35: hoàn thiện DPI, Xem và sửa kết quả OCR và hủy yêu cầu; phát triển bảng thuật ngữ và bộ nhớ bản dịch khớp chính xác. Chuẩn hóa chính sách gửi yêu cầu và test build sạch. Dùng một kỹ sư ứng dụng máy tính, một kỹ sư phía máy chủ bán thời gian và một người sản phẩm QA là giả định nguồn lực cần xác minh, chưa phải nhân sự đã có.

- Ngày 36 đến 60: tuyển 5 tổ chức thử nghiệm thực tế, đo tác vụ trước sau và giá thử, hỗ trợ cài đặt trực tiếp. BYOK là đường mặc định. Nếu khách hàng cần quản trị chung, làm không gian làm việc tối thiểu, cách ly dữ liệu giữa các tổ chức và hạn mức; không mở SSO hoặc marketplace ngay.

- Ngày 61 đến 90: triển khai thử nghiệm thực tế trả phí, ghi nhận siêu dữ liệu về mức sử dụng có sự đồng ý và không thu nội dung dịch. Báo cáo tỷ lệ kích hoạt, tỷ lệ duy trì sử dụng tuần 4, lỗi thuật ngữ, thời gian tác vụ và chi phí. Đo riêng CSKH và vận hành, không gộp một nhóm người dùng cùng đợt nhỏ thành kết luận về toàn thị trường.

- Cuối ngày 90: tiếp tục đầu tư khi đạt mục tiêu giá trị, có ít nhất 3 tổ chức trả phí thử và điều kiện bảo vệ dữ liệu đạt. Nếu nhu cầu có nhưng hiệu quả kinh tế yếu, điều chỉnh hạn mức hoặc BYOK; nếu không giảm công sức tác vụ, thu hẹp hoặc đổi hướng. Người phụ trách và ngày bắt đầu sẽ do chủ dự án xác nhận sau đánh giá.

## Phụ lục A — Định nghĩa chỉ số

- **Tỷ lệ kích hoạt 5 phút:** số người có bản dịch thành công trong 5 phút từ mở bộ cài chia số người tham gia được quan sát. Báo riêng lỗi cài đặt, khóa API và thao tác UI.

- **Tỷ lệ duy trì sử dụng tuần 4:** người đã kích hoạt và có ít nhất một tác vụ dịch chủ động ở tuần 4 chia nhóm người dùng cùng đợt đã kích hoạt. Không tính background heartbeat hoặc mở app tự động.

- **Lỗi thuật ngữ:** số lần xuất hiện dịch sai theo bảng thuật ngữ đã chốt chia tổng lần xuất hiện đủ điều kiện, được người đánh giá ẩn biến thể kiểm tra. Báo riêng tên riêng, mã và số.

- **CER:** số phép sửa ký tự Levenshtein chia số ký tự dữ liệu chuẩn đã đối chiếu; giữ dấu và số, chỉ áp dụng chuẩn hóa dữ liệu đã công bố. p95 độ trễ đo từ thao tác người dùng đến kết quả sẵn sàng, báo cold warm riêng.

- **Biên đóng góp:** doanh thu trừ API, OCR đám mây, hạ tầng biến đổi, thanh toán và hỗ trợ trực tiếp, chia doanh thu. Không gọi chỉ số này là lợi nhuận ròng vì chưa trừ phát triển, bán hàng và chi phí cố định.

## Phụ lục B — Kế hoạch thử nghiệm

- Tất cả thử nghiệm dưới đây đang ở trạng thái đề xuất, chưa tuyển mẫu hoặc chạy. Không có mức độ tác động quan sát, khoảng tin cậy hoặc giá trị p để báo cáo. Trước thử cần chốt đơn vị đo, phân nhóm, thời lượng và quy tắc dừng, tránh chọn metric sau khi xem kết quả.

### E1 Hướng dẫn sử dụng ban đầu

Giả thuyết: hướng dẫn khóa API OCR và test connection trong app tăng tỷ lệ kích hoạt so với Settings hiện tại. Thử 20 người mới, phân ngẫu nhiên 10 người mỗi luồng; cùng tác vụ và máy đã kiểm tra. Đo tỷ lệ kích hoạt 5 phút, thời gian hoàn tất tác vụ đầu tiên, lỗi cấu hình và số lần cần hỗ trợ. Mẫu nhỏ chỉ phục vụ usability. Mục tiêu là ít nhất 8 trong 10 người hoàn tất luồng mới, không tăng sự cố dữ liệu. Sau đó tính cỡ mẫu thử xác nhận bằng mốc đối chiếu ban đầu thực.

### E2 Bảng thuật ngữ và bộ nhớ bản dịch

Giả thuyết: F1 và F2 giảm trung vị thời gian hoàn tất ít nhất 20% và lỗi thuật ngữ ít nhất 30%. Mời 15 người, mỗi người xử lý 20 tác vụ đã khử dữ liệu nhạy cảm, chia hai nhóm tác vụ tương đương và đảo thứ tự A B. A là cửa sổ dịch nhanh hiện tại, B có bảng thuật ngữ bộ nhớ bản dịch; dùng cùng bộ cung cấp dịch vụ. Đánh giá theo người, bootstrap chênh lệch theo người và báo CI 95%, không coi 300 tác vụ độc lập. Điều kiện bảo vệ lỗi số không tăng và tỷ lệ sửa kết quả không xấu hơn. Nếu CI còn rộng, không tuyên bố chiến thắng.

### E3 OCR

Giả thuyết: review ảnh vùng ảnh cắt và giữ chất lượng ảnh giảm lỗi số mà không làm thời gian tác vụ vượt ngưỡng chấp nhận. Tạo 200 ảnh dữ liệu chuẩn đã đối chiếu do hai người đối chiếu, 4 nhóm Việt Anh trộn, chữ nhỏ, mã số và giao diện tối. So cùng ảnh qua engine và đổi kích thước ảnh đã chốt, lặp warm 3 lần, báo cold riêng. Chia development và tập kiểm tra độc lập trước tune. Đo CER, khớp chính xác số, end to end p95 và chi phí request. Mục tiêu tham khảo: không mất số đúng so mốc đối chiếu ban đầu và p95 OCR cục bộ dưới 3 giây trên cấu hình thử nghiệm thực tế đã công bố. Đám mây chỉ chạy với bộ dữ liệu được phép gửi và ngân sách được chốt.

### E4 Thử nghiệm thực tế trả phí

Giả thuyết: các tổ chức cần tính nhất quán sẵn sàng trả tiền cho quy trình làm việc ngay cả khi tự trả API. Tuyển 5 tổ chức đích, thử nghiệm thực tế 4 tuần, báo giá trước khi bắt đầu và quan sát sử dụng thực. Mục tiêu là ít nhất 3 tổ chức thanh toán thử nghiệm thực tế và ít nhất 50% người đã kích hoạt còn dùng ở tuần 4. Thu lý do từ chối và mẫu hỗ trợ. Không dùng lời hứa mua hay feedback tích cực thay giao dịch. Các tổ chức không được phân ngẫu nhiên nên kết quả không chứng minh quan hệ nhân quả hoặc nhu cầu thị trường rộng.

## Phụ lục C — Giá thử và chi phí

Giá để kiểm chứng, chưa phải bảng giá phát hành: gói cá nhân BYOK thử 5 USD mỗi tháng; gói nhóm thử 12 USD mỗi người dùng được cấp quyền mỗi tháng, tối thiểu 5 người dùng được cấp quyền, API tách riêng. Gói do nhà cung cấp quản lý tham khảo 12 USD mỗi người dùng được cấp quyền mỗi tháng kèm 100.000 ký tự tới một ngôn ngữ đích, phần vượt hạn mức tính theo chi phí và mức biên đóng góp chốt sau thử nghiệm thực tế. OCR đám mây tính hạn mức riêng. Không mặc định entitlement này đã bền vững hoặc khách hàng chấp nhận mức giá.

Google Đám mây Basic niêm yết khoảng 20 USD cho một triệu ký tự đầu vào sau credit và trong bậc tiêu chuẩn; credit tối đa 10 USD tháng được áp dụng chung Basic và Advanced [S2]. Mức sử dụng tính theo code point, không phải số từ. Công thức dưới đây bỏ qua credit để đánh giá đơn vị sử dụng khi mở rộng, không cộng credit cho từng người dùng được cấp quyền. Giá nguồn kiểm tra ngày 16/09/2026, có thể thay đổi.

| Kịch bản giả định | Ký tự mỗi người dùng được cấp quyền tháng | Chi phí dịch USD |
| --- | --- | --- |
| Nhẹ | 100.000 | 2,00 |
| Vừa | 300.000 | 6,00 |
| Nặng | 1.000.000 | 20,00 |

Ví dụ do nhà cung cấp quản lý giá 12 USD: nếu một người dùng được cấp quyền gửi 100.000 ký tự, chi phí dịch 2 USD, cộng giả định hạ tầng thanh toán hỗ trợ 2 USD thì đóng góp còn 8 USD, tương đương 66,7%. Nếu gửi 300.000 ký tự, còn 4 USD, tương đương 33,3%. Nếu gửi một triệu ký tự, âm 10 USD. Cả ba chưa gồm OCR đám mây. Đây là mô phỏng giả định, không phải chi phí đo hoặc lợi nhuận dự án. Với mục tiêu biên đóng góp 65%, tổng chi phí biến đổi tối đa là 4,20 USD trên người dùng được cấp quyền giá 12 USD, nên hạn mức và BYOK là điều kiện quan trọng.

Cần sổ theo dõi chi phí theo tenant request bộ cung cấp dịch vụ, ký tự và token thực dùng, cache hit, thử lại và status. Không lưu văn bản hay Khóa API trong ledger. Hạn mức phải thực thi phía dịch vụ khi công ty trả API, không chỉ trong app máy tính. Theo dõi người dùng được cấp quyền dùng nặng và chính sách giới hạn rõ để tránh hỗ trợ trực tiếp hoặc OCR phá hiệu quả kinh tế.

## Phụ lục D — Phạm vi kỹ thuật tính năng

### F1 bảng thuật ngữ

thuật ngữ có ngôn ngữ nguồn và ngôn ngữ đích, domain, owner và version; CSV nhập dữ liệu có validation; rule scoped tenant. Khi đổi version phải invalidate bộ nhớ bản dịch. Tiêu chí nghiệm thu: cùng bộ câu chuẩn không sai tên sản phẩm, tránh replacement trong URL mã và substrings. Cần một bộ cung cấp dịch vụ có khả năng bảng thuật ngữ hoặc UI cảnh báo giới hạn, không hứa Google Basic v2 đã hỗ trợ yêu cầu này.

### F2 bộ nhớ bản dịch

SQLite cục bộ cho khớp chính xác và bản người dùng duyệt, index theo cặp ngôn ngữ và phiên bản bảng thuật ngữ, hỗ trợ edit delete xuất dữ liệu. Thử nghiệm thực tế nhóm cần dịch vụ phía máy chủ chia tenant với một cơ chế sync đơn giản và conflict version. Tiêu chí nghiệm thu: không đọc được bộ nhớ bản dịch tenant khác, delete không tái xuất hiện qua sync và cache không vượt chính sách tỷ lệ duy trì sử dụng.

### F3 Không gian làm việc

gateway giữ khóa API công ty, tenant RBAC, chính sách đám mây, ngân sách yêu cầu và sổ theo dõi mức sử dụng. Máy tính gửi request bằng token scoped ngắn hạn, không nhúng master khóa API. Nếu dịch vụ phía máy chủ mất kết nối, báo trạng thái và chỉ dùng cục bộ path đã cho phép; không chuyển dữ liệu sang đám mây khác tự động. Billing và quyền không gian làm việc là phần dịch vụ thương mại, cần kiểm tra giấy phép toàn kiến trúc trước đóng gói.

### F4 review

một draft OCR riêng không kích hoạt dịch tự động, có vùng ảnh cắt thumbnail văn bản sửa được và nút dịch chủ động. Giữ cảnh báo độ tin cậy khi bộ cung cấp dịch vụ thật có cung cấp, không biến output LLM thành độ tin cậy đã hiệu chỉnh. Khi phát hiện mã hoặc số, highlight để người dùng đối chiếu ảnh thay vì âm thầm sửa bằng model.

### F5 ngoại tuyến

một bộ cung cấp dịch vụ dịch cục bộ phía sau TranslationProvider, self test capability ngôn ngữ và giới hạn tài nguyên; model và dictionary phải có giấy phép phù hợp thương mại. Cần đo chất lượng Việt Anh và cài đặt trên máy khách trước bán gói riêng. Triển khai tại hạ tầng khách hàng phát sinh deployment security update và hỗ trợ, nên chỉ mở theo hợp đồng có ngân sách.

## Phụ lục E — Nguồn và bằng chứng

Mã nguồn đánh giá tại C:/Users/NTQ/OneDrive/Desktop/crow, commit f85adfbf73270e82f243deb356cdb1b17185152a. Working tree sạch ở thời điểm bắt đầu. Tài liệu này thêm artifact trong research/project-review, không sửa code runtime.

R1 README.md và pyproject.toml: định vị, version, giấy phép và dependency. docs/WINDOWS_PACKAGING.md, scripts/build-windows.ps1 và installer/PyCrowTool.iss: quy trình release, ký số và bộ cài.

R2 src/py_crow_tool/config.py, SettingsStore.load save _decode: khóa API dạng văn bản thuần, write temporary và kiểm tra tính hợp lệ của cấu hình. src/py_crow_tool/services/history.py, HistoryStore.flush clear: write JSON và race risk.

R3 src/py_crow_tool/viewmodels.py, TranslationViewModel.savePreferences tại dòng 256: replace Google only. src/py_crow_tool/bootstrap.py, build_services: cấu hình plugin chưa truyền. plugins.py: entry point factory và allowlist.

R4 src/py_crow_tool/services/ocr.py, _submit recognizeImageBytes cancel_current: cơ chế theo dõi kết quả cũ, drop siêu dữ liệu và hủy yêu cầu riêng. providers/tesseract_ocr.py: language mapping, to_thread và thiếu giới hạn thời gian subprocess. providers/openai_ocr.py: đổi kích thước ảnh và mức sử dụng.

R5 services/capture.py, CaptureController.confirmRegion và qml/CaptureOverlayWindow.qml: vùng ảnh cắt QRect từ tọa độ overlay. app.py dòng 99 đến 104: nhận OCR region rồi gọi dịch ngay. qml/Main.qml dòng 295: có thông báo OCR đám mây, không phải hoàn toàn thiếu disclosure.

R6 tests/test_qml.py dòng 116: kỳ vọng chữ clipboard nhưng thông báo hiện là This shortcut is already in use. Choose another. tests/test_viewmodels.py dòng 80: assert busy ngay sau translate với fake bộ cung cấp dịch vụ hoàn tất tức thời. Lệnh kiểm tra python -m pytest trong .venv trên Windows.

R7 research/Nghien-cuu-phat-trien-OCR-screenshot.docx: tài liệu định hướng ngày 06/09/2026, chỉ dùng làm bối cảnh. scripts/bench_ocr_openai.py và bench_ocr_tesseract.py: công cụ thử, không phải output kết quả.

[S1] DeepL Help Center About DeepL máy tính apps. [Tính năng ứng dụng DeepL trên máy tính](https://support.deepl.com/hc/en-us/articles/18609624054300-About-DeepL-desktop-apps) . Kiểm tra 16/09/2026. Cơ sở so feature phím tắt chụp màn hình bảng thuật ngữ file translation.

[S2] Google Đám mây Đám mây Translation pricing. [Bảng giá Google Cloud Translation](https://cloud.google.com/products/translate/pricing) . Kiểm tra 16/09/2026. Cơ sở giá Basic v2, cách đếm ký tự và credit chung.

[S3] GNU Frequently Asked Questions about the GNU Licenses. [GNU — Thương mại hóa phần mềm GPL](https://www.gnu.org/licenses/gpl-faq.en.html#GPLCommercially) . Kiểm tra 16/09/2026. Cơ sở GPL cho phép thương mại và nghĩa vụ khi phân phối.

[S4] Qt Licensing và Obligations of the GPL and LGPL. [Giấy phép Qt](https://doc.qt.io/qt-6/licensing.html) và [Nghĩa vụ khi sử dụng Qt theo LGPL](https://www.qt.io/development/open-source-lgpl-obligations) . Kiểm tra 16/09/2026. Cơ sở cần rà soát module giấy phép và packaging, không kết luận máy tính bắt buộc mua Qt commercial.
