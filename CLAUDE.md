# Luật cho mọi phiên Claude trên mọi VPS

Máy này vừa chạy kênh thật vừa là chỗ phát triển tool. Nó tiêu tiền thật và đăng video thật. Không được làm chết máy đang kiếm tiền.

- Luật riêng của từng máy (mạng, số kênh) nằm ở `CLAUDE.local.md`. Tệp này do bộ cài sinh ra.
- Luật và số liệu của từng kênh nằm ở `CHANNEL/<k>/CLAUDE.md` và `NHAT-KY-KENH.md`. Hai tệp này thắng mọi phân tích chung.
- Cài đặt và vận hành: `README.md`. Sửa mã và bản đồ module: `docs/PHAT-TRIEN.md`.

## 1. Tài sản của chủ: không đụng
- `PROJECTS/` là kết quả đã trả tiền: không xoá, không dọn, không đổi tên. Dọn video đã đăng là việc của `core/don_dep.py` khi kênh bật `tu_don`.
- `config.json`, `secrets.json`, `.claude/` chứa khoá API: không đụng.
- Không tự bật tiền hay tự động. `tu_chay`, `tu_dang`, `tu_duyet`, `tu_don`, `ngan_sach_ngay` (trong `kenh.yaml`) và `cach_dang` (trong `may-ao.json`) do chủ dự án quyết. Muốn thử thì chạy `python tu_chay.py --kenh <k> --thu`: lệnh này chỉ nghiên cứu và chọn nguồn, không tốn ví.
- Kênh có bản `-v2` là cặp A/B có chủ đích. Không đổi cách bản gốc làm video khi chưa được bảo.
- Không in hay lưu mật khẩu, khoá vào log hoặc tài liệu. Tài liệu lên kho không được có IP, email, tên người dùng, tên kênh thật, số tiền.

## 2. Sửa mã đang sống
- Chỉ thay tệp mã sống trong khung phút :15–:45 của mỗi giờ.
- Viết trên bản nháp, chạy `python -m py_compile`, rồi thay một lần trọn vẹn. Không sửa dở các tệp mà lịch đang gọi (`tu_chay.py`, `core/tu_chay.py` và các tệp chúng nạp).
- Trước khi thay, sao lưu bản gốc vào `workspace/ban-va/<ngày>-<việc>/`, kèm `GHI-CHU.md` ghi vì sao sửa, đã chạy test nào, cách hoàn tác. Sau đó ghi một mục vào `NHAT-KY-PHAT-TRIEN.md`. Nhật ký này nằm trên máy, không lên kho.
- Nháp cũ không bao giờ chép đè nguyên tệp lên bản sống. Áp từng đoạn. Đoạn nào không áp được thì chép tay theo nghĩa.
- Không dời hay đổi tên các điểm vào mà tác vụ Windows trỏ tới: `tu_chay.py`, `tram_nen.py`, `shopapi_studio_qt.py`, `CHAY-GON.vbs`, `-m core.gac_tong`.
- Sửa xong **phải** chạy `python -m core.dong_bo_git day "<thông điệp>"`:
  - thêm `--minor` hoặc `--major` khi cần;
  - thêm `--chi <tệp…>` khi máy còn tệp dở của người khác;
  - lệnh này tự kiểm, quét bí mật, commit, rebase, nâng `VERSION`, ghi CHANGELOG, gắn tag rồi push;
  - không sửa `VERSION` bằng tay;
  - gặp xung đột thì lệnh dừng và báo. Không tự giải bừa.
- Sửa mà không đẩy thì máy này không tự cập nhật được nữa.

## 3. Một khe nặng: không chạy nặng song song
- Tối đa **1 agent viết mã** trên máy sản xuất tại một thời điểm. Từng có lúc nhiều agent cùng chạy test toàn kho làm VM cạn RAM và treo.
- **Không `pytest tests/` toàn kho** trên máy sản xuất. Chỉ chạy test lẻ liên quan: `python -m pytest tests/test_<việc>.py -q`. `dong_bo_git day` tự chạy nhóm test nhanh.
- Tool điều phối tài nguyên như sau:
  - khâu gọi API (LLM, giọng, ảnh, video) chạy song song nhiều kênh;
  - việc nặng trên máy (FFmpeg, Whisper, xoá dấu, chuẩn nhạc) đi 1 khe;
  - việc mở trình duyệt kênh đi 1 khe (mỗi lúc một trình duyệt);
  - hai khe này loại trừ nhau;
  - thứ tự ưu tiên: đăng đúng giờ > quét Studio > dựng > việc nền.
- Agent chạy song song (khi được phép) phải có phạm vi tệp riêng. Tệp dùng chung thì làm tuần tự.

## 4. Không phá việc đang chạy
- Không giết lượt sản xuất, động cơ `vm/`, hay trình duyệt kênh. Trước khi khởi động lại, xem `vm/trang-thai.json` và `vm/agent.log`. Giết giữa lúc tải lên có thể để lại video dở trên kênh.
- Tránh khung giờ phiên kênh, khoảng 60 phút trước giờ đăng (`CHANNEL/<k>/ke-hoach-dang/ke-hoach.csv`). Trong khung đó không thay mã đăng hay quét, không khởi động lại, không chạy việc nặng.
- Test và công cụ dev không được gọi hàm dọn tiến trình thật, không xoá sạch `%TEMP%`, không đăng ký tác vụ Windows thật.
- **Không hỏi job dày.** Không job nào xong dưới 30 giây. Hỏi dày làm nghẽn CPU máy chủ và đường truyền của chính máy.
  - Dùng `app.start_batch`, webhook hoặc SSE (`client.jobs.stream`).
  - Buộc phải tự hỏi thì dùng `poll_delays(estimated_seconds=...)` của SDK, và không kẹp nhỏ nhịp nó tính ra.
  - Không bao giờ viết `while True: sleep(2); jobs.list()`. Chờ một job thì hỏi `jobs.get(id)` của đúng job đó.
  - Muốn nút Dừng nhạy thì dùng `Event.wait(giây)`.
- Ảnh tải lên được giữ một bản trên đĩa (`core/auto_khau._luu_ban_cuc_bo`), và phía nhận tra bản đó trước. Sửa đầu này thì phải sửa cả đầu kia cho khớp.
- **Mạng.** Danh tính kênh gắn với IPv6. Khi trình duyệt kênh đang mở thì IPv4 phải tắt. Chỉ mở van IPv4 (`vm/van-ipv4.json`) khi đã đóng hết trình duyệt, và đóng lại ngay khi xong.
- Máy chỉ có IPv6 không tới được github.com (trừ qua NAT64), HuggingFace, downloads.claude.ai. Đừng viết mã phụ thuộc các nơi này.

## 5. Chọn content theo NGHĨA bằng LLM
- Chọn content quyết định khoảng 80% thành công. Đầu tư mạnh nhất ở khâu này: LLM mạnh, đủ bối cảnh, biên tập viên AI chốt nguồn có lý do, và đo lại dự đoán so với kết quả thật.
- Mọi quyết định nội dung đều do LLM đọc nghĩa, có cache: cụm chủ đề, lọc ngách hoặc đối thủ, tệp khán giả, chống trùng ý. **Không lọc bằng từ khoá.** Regex chỉ là đường lùi khi LLM lỗi.
- Không cắt lượt gọi AI chỉ để tiết kiệm. Chỉ bỏ lượt gọi thừa: lặp y hệt, hoặc kết quả bị bỏ đi.
- Mỗi kênh tự học từ số của chính nó. Dữ liệu nhóm chỉ là tiên nghiệm yếu. Chỉ tính video do tool làm, hoặc đăng sau mốc bắt đầu ngách.
- Mục đích: kênh có view và bật kiếm tiền (YPP). Chọn content theo thứ kênh đang thiếu: thiếu sub, hoặc thiếu giờ xem.

## 6. Tự vận hành một năm: không chết im lặng
Mọi tính năng mới phải trả lời được 3 câu:
1. Lỗi thì tự thử lại hay tự phục hồi thế nào?
2. Kẹt vĩnh viễn thì có bị phát hiện, bỏ qua hoặc làm lượt mới không? Lượt dở bị bỏ kẹt là bug.
3. Việc máy không tự làm được (nạp tiền, đăng nhập lại, license) có hiện ở "Việc của bạn" và `workspace/loi-chay-max.md` bằng câu người thường hiểu, và có nhắc lại không?

Thêm:
- Mọi cải tiến (bìa, tiêu đề, hook, độ dài) là vòng lặp: đọc Studio → bài học → áp vào → đo 48h/72h/7 ngày → học tiếp.
- Lời nhắc sinh nội dung giữ ngắn nhưng nêu mục tiêu cụ thể. Sức mạnh nằm ở sinh nhiều bản và có tiêu chí chấm tốt.
- Tiêu chí mềm chỉ cảnh báo. Chỉ chặn lỗi thật: video hỏng, không tiếng, thiếu phụ đề, tiêu đề hoặc bìa không hợp lệ.
- Lượt tải hỏng để lại nháp trên Studio thì lượt sau tải mới. Không sửa, không xoá nháp cũ.
- Lời nhắc hay khuôn mới phải qua các bước: tạo thử thật → chấm → xem bằng mắt → mới áp vào sản xuất.
- Khi tài nguyên (đĩa, RAM) cản đường, nói rõ con số và đề nghị nâng phần cứng. Không tự hạ quy mô.

## 7. Nói thật, báo ngắn
- Không báo "đã xong" cho việc chưa xong. Báo cáo gồm kết quả chính và việc chủ phải làm, nếu có.
- Tự quyết khi đủ dữ liệu. Chỉ hỏi chủ về việc chỉ người làm được (đăng nhập, tiền, license) hoặc về hành động không đảo ngược được.
- Giao diện viết tiếng Việt, nhãn ngắn, không dùng từ kỹ thuật. Thứ gì chỉnh được thì nên có chỗ chỉnh trên giao diện.
