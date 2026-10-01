# Nhật ký phát hành

Rút gọn từ `NHAT-KY-PHAT-TRIEN.md` (nhật ký chi tiết máy — mỗi mục có ngày,
lý do sửa, tệp đụng tới, kết quả test). Tệp này chỉ ghi TÍNH NĂNG CHÍNH, cho
người cần biết "bản mới có gì" mà không cần đọc hết nhật ký chi tiết.

## Các bản đẩy lên kho chung (tự ghi bởi `dong_bo_git day`, mới nhất ở trên)

- **2.141.4** — 2026-10-01 — `vps-jp1` — Dọn: video đã lên YouTube là xoá ngay file nặng + ảnh; gói Bỏ xoá ngay
- **2.141.3** — 2026-10-01 — `vps-jp1` — Gọn luật dọn DONE (một luật 3 ngày) + van ổ 10 GB
- **2.141.2** — 2026-10-01 — `vps-jp1` — Dọn DONE sau khi đăng + chặn ổ đầy + trần theo ổ
- **2.141.1** — 2026-10-01 — `vps-jp1` — Giãn lịch đăng theo nhịp ngày + dời lịch video đã hẹn + sản xuất theo nhịp
- **2.141.0** — 2026-10-01 — `vps-jp1` — Cứu video CTR thấp (đổi tiêu đề/bìa, duyệt 3 lần đầu) + vá lỗ bản chụp + giờ online + bìa
- **2.140.2** — 2026-10-01 — `vps-jp1` — Trang chủ: lưu CSV thử lại khi tệp đích đang bị mở (WinError 5 làm hỏng lượt nghiên cứu TL2)
- **2.140.1** — 2026-10-01 — `vps-jp1` — Phòng điều hành: ẩn việc ghim khi kênh tắt ghim; nút Sai loại bài học mọi nguồn khỏi lời nhắc; số 1709.0 → 1709
- **2.140.0** — 2026-10-01 — `vps-jp1` — Bảng điều khiển: phòng điều hành công ty
- **2.139.0** — 2026-10-01 — `vps-jp1` — Đội chuyên gia + hội đồng quyết định + sổ độ chính xác; sửa đo công suất cửa sổ gần
- **2.138.0** — 2026-10-01 — `vps-jp1` — Công ty YouTube (gọn): khám nghiệm video + bài học + tổng giám đốc gợi ý
- **2.137.2** — 2026-10-01 — `vps-jp1` — Ví: chi ngày theo số thật (độ tụt ví/chi phí lượt), cảnh báo đúng số ngày còn
- **2.137.1** — 2026-10-01 — `vps-jp1` — Gác tổng: cảnh báo 'hẹn lịch chưa tải' chỉ KHẨN khi còn ≤3 giờ (bớt báo động nhiễu)
- **2.137.0** — 2026-10-01 — `vps-jp1` — Giám đốc kênh: nối vào gác tổng/biên tập/hồ sơ; sửa ngưỡng thắng kênh ít video; TL3 chế độ gợi ý
- **2.136.1** — 2026-10-01 — `vps-jp1` — Golden giữ LF trên clone Windows (.gitattributes)
- **2.136.0** — 2026-10-01 — `vps-jp1` — VPS mới: khởi tạo ngách bằng AI + bỏ chỗ cứng Nhật
- **2.135.0** — 2026-10-01 — `vps-jp1` — Giám đốc kênh: gói lõi + 5 plugin đợt 1 (chưa nối)
- **2.134.1** — 2026-10-01 — `vps-jp1` — Máy đăng: bù MHKT video cũ giờ vắng
- **2.134.0** — 2026-10-01 — `vps-jp1` — Gọn kho: một README, một bộ luật, 3 tài liệu; bỏ luồng cài ZIP cũ
- **2.133.3** — 2026-10-01 — `vps-jp1` — Gọn kho: bỏ mã chết, công cụ cũ, bản trùng; README mới
- **2.133.2** — 2026-09-30 — `vps-jp1` — Máy đăng: quét ngày độc lập, MHKT dựng từ mẫu, chờ tải xong 100% + hậu kiểm
- **2.133.1** — 2026-09-30 — `vps-jp1` — docs(nhieu-vps): thêm dòng xem nhanh phiên bản (bản vá thử đường tự cập nhật)
- **2.133.0** — 2026-09-30 — `vps-jp1` — feat(cap-nhat): một hệ cập nhật git duy nhất — day tự nâng phiên bản + CHANGELOG + tag; máy tự kiểm ~30' và tự nhận bản mới lúc rảnh (mặc định bật, tắt trong Cài đặt); khung Cập nhật trên giao diện; bỏ lịch 03:40; A17 kho đọc cap-nhat.json

## [3.0.0-dev] — 22/09/2026 – 29/09/2026

Chuẩn bị phát hành v3.0 (sản phẩm nhiều VPS, nhiều ngách) — xem
`workspace/LO-TRINH-PHAT-HANH-V3.md` cho lộ trình đầy đủ.

### Giao diện & vận hành VPS

- Thiết kế lại giao diện VPS: gộp 6 tab rời thành trang **Trung tâm**, sau
  đó thành **Bảng điều khiển** — mở tool trả lời ngay ba câu "kênh có ổn
  không / tôi cần làm gì / kết quả ra sao" (khối Việc của bạn, Dòng máy,
  Thẻ kênh lớn theo từng kênh, xem `README-VPS.md`).
- Gộp toàn bộ thư mục VPS về một `MyTool\` duy nhất (bỏ cấu trúc nhiều thư
  mục rời rạc của bản trước).
- Bảng điều khiển: cảnh báo Windows sắp hết hạn, sửa 5 lỗi phát hiện trên
  dữ liệu thật sau khi khởi động lại máy.
- Cài VPS từ bản clone git thẳng (`CAI-DAT-VPS.bat` + `vm/cai_dat_tu_kho.py`,
  MỚI) — thay thế cho phải đóng gói `vm/goi-vps/` trên máy nhà rồi chép
  sang; thêm `websocket-client` (từng thiếu, làm máy đăng DOM hỏng trên máy
  sạch), lùi nguồn tải cho máy chỉ IPv6. Đi kèm `core/kiem_may.py` — bảng
  OK/THIẾU kiểm máy đã sẵn sàng tự chạy chưa.
- `.gitignore` vá lỗ lọt dữ liệu riêng máy/kênh (nhật ký kênh thật, hồ sơ
  video, trạng thái `vm/`); đổi chặn hồ sơ trình duyệt kênh sang chặn THEO
  CẤU TRÚC (`Data/profile`, `App/Chrome-bin`) thay vì theo tên `TL*`.
- Tài liệu vận hành mới: `README-VPS.md`, `docs/THEM-KENH.md`,
  `docs/DOI-CHU-DE.md`, `docs/BAN-DO-MODULE.md`.

### Điều phối tài nguyên (nền tảng cho nhiều kênh/nhiều VPS)

- Đo công suất thật của máy (`core/cong_suat.py`) trước khi sửa điều phối —
  số nền để so sánh trước/sau.
- Tách lớp song song **API** (gọi máy chủ, chạy song song nhiều làn) và
  **nặng** (Chrome/FFmpeg/Whisper, độc quyền một lượt) — sửa nút thắt từng
  ép mọi việc VPS về song song = 1, kéo dài khâu ảnh gấp nhiều lần.
- Khe tài nguyên liên tiến trình + hàng đợi ưu tiên P0–P4 + đệm sổ job dùng
  chung toàn máy (`core/khe.py`, `core/uu_tien.py`, `core/so_job_chung.py`,
  `core/bang_thong.py`) — module mới, thuần, sẵn sàng để nối vào bộ điều
  phối chính ở đợt kế tiếp.

### Sản xuất & chất lượng nội dung

- Sản xuất theo đúng nhịp đăng, tự ghi nhận khi có người đăng tay, tự phục
  hồi khi lượt trước dở dang.
- Một hàng đợi tuần tự cho toàn VPS — chặn hai lượt việc NẶNG chạy chồng
  nhau (Chrome + FFmpeg cùng lúc từng làm máy đơ).
- `core/bai_hoc_san_xuat.py` (MỚI) — vòng phản hồi: kênh tự học từ video đã
  đăng để cải thiện lượt sau.
- `core/qa_truoc_dang.py` (MỚI) — cổng kiểm chất lượng trước khi bàn giao
  cho máy đăng, chặn video lỗi lọt lên kênh thật.
- Hồ sơ video + vòng học chạy trước MỖI lượt sản xuất (không chỉ sau).
- Khuôn ảnh bìa "thắng" + giám khảo AI tự chọn ảnh bìa tốt nhất trong nhiều
  bản.
- N bản tiêu đề mỗi video + chấm điểm CTR dự đoán; kiểm trùng Ý TƯỞNG bằng
  LLM (không chỉ trùng chữ).
- Kho nhạc nền chuẩn hoá tăng dần (`core/kho_nhac.py`), dựng video theo
  PHẦN (nghỉ giữa phần, chuyển cảnh, nhạc đổi theo phần, phụ đề/mục lục
  đồng bộ).
- Chặn vượt cửa nhịp đăng + chống làm trùng nội dung theo TIÊU ĐỀ.

### Đăng video & bình luận

- **Máy đăng DOM/CDP** (MỚI) — đăng video qua Chrome DevTools Protocol thay
  vì chỉ giả lập chuột/phím; nối vào phiên kênh (`vm/agent.py`), trạm nội
  bộ, và kế hoạch đăng (`core/ke_hoach_dang.py`); đã thử đăng thật liên
  tiếp trên kênh thật.
- Máy đăng: dò ảnh đa tỉ lệ (sửa lỗi 0/1 mã im lặng), dẹp vật cản (hộp xin
  quyền, lỗi End Screen), bỏ lệnh xoá đệ quy `%TEMP%` nguy hiểm.
- Nhường phiên kênh cho `vm/agent.py` đúng trước giờ đăng — không để lượt
  sản xuất nặng giữ máy tới lỡ giờ.
- Tự nhận diện video đã đăng (không đứng im chờ mãi vì "quên" một gói).
- Báo động Telegram bền vững khi có sự cố cần người can thiệp.
- Bật tự động hoàn toàn cho các kênh đã qua thử nghiệm DOM đạt yêu cầu; hỗ
  trợ tải lên bổ sung trong ngày (không chỉ một lượt cố định).

### Dọn dẹp & xử lý sự cố

- Dọn hậu quả sau khi bỏ thư mục khuôn `_KHUON`/`_MAU-GON`; mở rộng cơ chế
  dọn đĩa (không chờ "đã đăng" mới dọn, có luật dọn sớm hơn).
- Lượt sản xuất "kẹt" tự phát hiện và tự xử lý (bốn mức xử lý khác nhau
  theo mức độ kẹt); sửa hai lỗi thật phát hiện sau khi triển khai.

---

Bản trước (2.x) — xem lịch sử `NHAT-KY-PHAT-TRIEN.md` trước ngày 22/09/2026.
