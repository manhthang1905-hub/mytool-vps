# Luật vận hành VPS (máy vừa chạy kênh thật vừa là chỗ phát triển)

Áp cho mọi VPS cài ShopAPI Studio, bất kể ngách hay quốc gia. Máy đang tiêu tiền thật và đăng video thật lên kênh thật; dev không được làm chết máy kiếm tiền. Luật riêng từng máy (mạng, số kênh) nằm ở `CLAUDE.local.md` của máy đó; luật chung của tool ở `CLAUDE.md`.

## 1. Không đụng tài sản của chủ

- **`PROJECTS/`**: kết quả sản xuất đã trả tiền — không xoá, không dọn, không đổi tên. (Dọn đồ đã đăng công khai là việc của `core/don_dep.py` khi kênh bật `tu_don`, không tự viết cơ chế khác.)
- **`config.json`, `secrets.json`, `.claude/`**: chứa khoá API và đăng nhập — không đụng.
- **Không tự bật tiền / tự động:** `tu_chay`, `tu_dang`, `tu_duyet`, `tu_don`, `ngan_sach_ngay` trong `kenh.yaml` là quyết định của chủ dự án. Thử thì dùng `python tu_chay.py --kenh <k> --thu` (chỉ nghiên cứu + chọn nguồn, không tốn ví).
- **Kênh đối chứng:** kênh nào có bản `-v2` cạnh nó là một cặp A/B có chủ đích — không đổi cách bản gốc *làm video* khi chưa được bảo. Trước khi đổi, tìm test tham chiếu cả hai.
- **Không in, không lưu mật khẩu/khoá** vào log, tài liệu, output. Không đưa IP, email, tên người dùng, tên kênh thật, số tiền cụ thể vào tài liệu lên repo.

## 2. Thay tệp mã đang sống

- Chỉ **thay tệp mã sống trong khung phút :15–:45** của mỗi giờ (tránh các lượt lịch chạy quanh giờ tròn).
- Viết trên **bản nháp** → `python -m py_compile` → thay **một lần trọn vẹn**. Không sửa dở trực tiếp các tệp mà lịch tự chạy đang gọi (`core/tu_chay.py` và các tệp nó nạp) — từng có lượt chết "lỗi ngoài dự kiến" vì lịch chạy trúng tệp đang sửa dở.
- **Sao lưu trước khi thay:** chép bản gốc (giữ đường dẫn tương đối) vào `workspace/ban-va/<ngày>-<việc>/`, kèm `GHI-CHU.md`: vì sao sửa, tệp nào, đã chạy test nào, cách hoàn tác.
- Ghi một mục vào `NHAT-KY-PHAT-TRIEN.md`. Không sửa thẳng `vm/` mà không chép bản vá (bản cập nhật sau sẽ ghi đè).
- **Không tự cập nhật tool từ kho từ xa trên máy đang chạy** nếu bản chạy có vá tại chỗ chưa về kho — kéo về sẽ ghi đè ngược. Bản vá đi về kho gốc bằng tay, rồi phát hành lại.
- Nháp cũ không bao giờ chép đè nguyên tệp lên bản sống; áp từng đoạn, không áp được thì chép tay theo nghĩa.

## 3. Một khe nặng — không chạy nặng song song

- Máy vừa sản xuất vừa dev. Đã có lần nhiều agent chạy song song, mỗi agent tự chạy test toàn kho cùng lúc với sản xuất → cạn RAM, VM treo cứng, mất khoảng 1,5 ngày sản xuất.
- **Tối đa 1 agent viết mã tại một thời điểm** trên máy sản xuất. Kiểm RAM trống trước khi giao việc nặng.
- **Không chạy `pytest tests/` toàn kho trên máy sản xuất.** Chỉ chạy tệp test liên quan phần vừa sửa (`python -m pytest tests/test_<phan>.py -q`). Bộ toàn kho chạy trên máy dev hoặc bản clone sạch.
- Điều phối tài nguyên của tool:
  - khâu gọi API (LLM, giọng, ảnh, video) chạy **song song** nhiều kênh;
  - việc nặng trên máy (dựng FFmpeg, Whisper, xoá dấu, chuẩn nhạc) đi **1 khe** xếp hàng;
  - việc mở trình duyệt kênh (đăng, quét Studio, lấy lời thoại, bình luận) đi **1 khe** — mỗi lúc chỉ MỘT trình duyệt;
  - hai khe nặng loại trừ nhau;
  - ưu tiên: **đăng đúng giờ > quét Studio > dựng > việc nền**.
- Agent chạy song song (khi được phép) phải có phạm vi tệp không giẫm nhau; tệp dùng chung làm tuần tự.

## 4. Không phá việc đang chạy thật

- **Không dừng/giết tiến trình đang chạy thật** (lượt sản xuất, động cơ `vm/`, trình duyệt kênh). Trước khi khởi động lại động cơ hay MyTool, xem `vm/trang-thai.json` và nhật ký máy đăng: có phiên đang chạy thì chờ. Giết giữa lúc tải lên có thể để lại video dở trên kênh.
- **Tránh khung giờ đăng / quét:** phiên kênh mở trình duyệt khoảng 60 phút trước giờ đăng của từng kênh (xem `nhip_dang` trong `kenh.yaml`, `ke-hoach-dang/ke-hoach.csv`). Không thay mã liên quan đăng/quét, không khởi động lại, không chạy việc nặng trong khung đó.
- Test và công cụ dev không được gọi hàm dọn tiến trình của máy thật (từng có test dựng cửa sổ chính làm giết tiến trình của lượt sản xuất). Dọn tệp tạm chỉ dọn rác của chính mình, không xoá sạch `%TEMP%`.
- **Không hỏi job dày.** Dùng `app.start_batch`, webhook/SSE, hoặc `poll_delays(...)` của SDK; không bao giờ `while True: sleep(2); jobs.list()`. Hỏi dày làm nghẽn CPU và đường truyền của chính máy chủ và máy mình.
- Nếu danh tính kênh gắn với một đường mạng (ví dụ chỉ IPv6), đường mạng khác phải tắt khi trình duyệt kênh đang mở; chỉ mở van khi đã đóng hết trình duyệt, rồi đóng ngay khi xong. Không viết mã phụ thuộc dịch vụ mà máy không tới được (ghi rõ trong `CLAUDE.local.md`).

## 5. Phân loại content theo NGHĨA bằng LLM

- Chọn content quyết định ~80% thành công của kênh remake → đầu tư mạnh nhất ở đây: LLM mạnh, đủ bối cảnh, biên tập viên AI chốt nguồn có lý do, đo lại dự đoán vs thật.
- **Mọi quyết định nội dung** (cụm chủ đề, lọc ngách/đối thủ, tệp khán giả, xu hướng, chống trùng ý) dùng LLM đọc hiểu nghĩa, có cache. **Không lọc bằng từ khoá**; từ khoá/regex chỉ là đường lùi khi LLM lỗi. *Ví dụ lỗi: một từ khoá "không sở hữu" gán nhầm video "không quan tâm người khác" vào cụm tiền bạc.*
- Cửa vào danh sách đối thủ "theo dõi" phải có phán quyết LLM đúng ngách, dùng chung cả nhóm; tỉ lệ khớp bằng máy không đủ.
- Không cắt lượt gọi AI chỉ để tiết kiệm nếu nó giúp chọn/làm tốt hơn; chỉ bỏ lượt gọi THỪA (lặp y hệt, kết quả bị vứt).
- **Cá nhân hoá theo tệp:** mỗi kênh tự học từ số của chính nó; dữ liệu nhóm chỉ là tiên nghiệm yếu khi kênh chưa có số; cold start = thăm dò có chủ đích trên chính kênh.
- **Lọc video rác cũ:** kênh tái sử dụng còn video cũ không liên quan — mọi số liệu/vòng học chỉ tính video do tool làm hoặc đăng sau mốc bắt đầu ngách mới.
- **Mục đích sống của tool:** kênh có view và bật kiếm tiền (YPP). Chọn content theo ràng buộc YPP kênh đang thiếu (thiếu sub → cụm kéo sub; thiếu giờ xem → nguồn đột biến ăn trang chủ, video dài giữ chân).

## 6. Tự vận hành một năm — không chết im lặng

Chuẩn: *cài xong, một năm sau quay lại máy vẫn đang đăng video hằng ngày.* Mọi tính năng mới phải trả lời 3 câu:
1. Lỗi thì **tự thử lại / tự phục hồi** thế nào?
2. Kẹt vĩnh viễn thì có **bị phát hiện và bỏ qua / làm lượt mới** không? (Lượt dở bị bỏ kẹt là bug.)
3. Việc máy không tự làm được (nạp tiền, đăng nhập lại cookie/OAuth, license Windows) thì **báo Telegram** bằng câu người thường hiểu, kèm việc cần làm, và **nhắc lại** — không bao giờ đứng im vô hạn không cảnh báo.

Thêm:
- **Không có cải tiến "làm một lần".** Mọi thứ (bìa, tiêu đề, hook, độ dài, nhạc) là vòng lặp mỗi lượt: đọc Studio → cập nhật bài học → áp vào video đang làm → lưu hồ sơ → đo 24/48/72h/7 ngày → học tiếp.
- **Lời nhắc SINH đơn giản; sức mạnh ở sinh NHIỀU BẢN + TIÊU CHÍ CHẤM** nuôi bằng số Studio. Lời nhắc ngắn nhưng MỤC TIÊU cụ thể, không nhồi luật chi tiết.
- **Tiêu chí mềm chỉ cảnh báo, không chặn đăng** (ví dụ độ dài lệch mục tiêu). Chỉ chặn lỗi thật: video hỏng/không tiếng, thiếu phụ đề, tiêu đề/bìa không hợp lệ.
- Lượt tải hỏng để lại nháp trên Studio → lượt sau **tải mới**, không sửa/xoá nháp; chỉ chống trùng video đã xác nhận lên lịch/công khai.
- Mọi lời nhắc/khuôn mới (bìa, v.v.) phải qua: tạo thử thật → chấm theo trường cấu trúc → xem bằng mắt → mới áp vào sản xuất.
- Khi tài nguyên (đĩa, RAM) cản đường: nói ra con số và đề nghị nâng phần cứng, không tự hạ quy mô kế hoạch hay dùng mẹo rủi ro.

## 7. Nói thật, báo ngắn

- Không báo "đã xong" cho việc chưa xong. Báo cáo ngắn: kết quả chính + việc chủ phải làm (nếu có).
- Tự suy luận và quyết khi đủ dữ liệu; chỉ hỏi chủ khi là việc chỉ người làm được (đăng nhập, xác minh, tiền, license) hoặc hành động không đảo ngược nguy hiểm.
- Mọi thứ chỉnh được nên có chỗ chỉnh trên giao diện; sửa tay YAML/JSON chỉ là đường dự phòng.
