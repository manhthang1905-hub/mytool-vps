# Thêm kênh mới

Dành cho người vận hành (không cần biết code). Một VPS chạy được tối đa
**10 kênh cùng ngách** (ví dụ cùng chủ đề "tâm lý"), mỗi kênh một trình
duyệt Chrome portable riêng, một giọng đọc riêng, một danh sách đối thủ
riêng. Làm đủ SÁU bước dưới đây — thiếu bước nào cũng khiến kênh mới đè lên
dữ liệu của kênh cũ hoặc bị YouTube coi là nội dung trùng lặp.

## 1. Tạo kênh (thuật sĩ "Thêm kênh")

1. Mở MyTool → trang **Trung tâm** hoặc **Kênh** → bấm nút **"Thêm kênh"**
   (góc trên bên phải).
2. Bước 1 của hộp thoại: chọn **"Tạo kênh mới từ một kênh mẫu"**.
   - **Chép từ kênh**: chọn một kênh mẫu có sẵn (ví dụ `TL4-T7`) — kênh mới
     nhận đủ prompt/style/nhạc/ảnh nhân vật của kênh mẫu, KHÔNG đụng gì tới
     kênh gốc.
   - **Mã kênh mới**: tên thư mục, viết liền không dấu, ví dụ `TL5-T7`. Đây
     cũng là tên thư mục trình duyệt sẽ dùng ở bước 2 — đặt cho đúng ngay từ
     đầu, đổi sau phải sửa nhiều chỗ.
   - **Tên kênh**, **Nhóm kênh**, **Tệp khán giả** — điền theo kế hoạch nội
     dung của bạn (không bắt buộc để chạy được, chỉ phục vụ báo cáo/so
     sánh).
   - Bấm **Tiếp** — tool tự tạo `CHANNEL/<mã mới>/` với cờ `kenh_rieng: true`
     (từ giờ cập nhật tool KHÔNG đụng vào kênh này nữa).

## 2. Gắn trình duyệt Chrome portable + đăng nhập YouTube

Mỗi kênh PHẢI có một trình duyệt riêng — dùng chung trình duyệt là dùng
chung danh tính, YouTube phát hiện và có thể khoá cả hai kênh.

1. Chuẩn bị một bản Chrome portable (GPM hoặc tương đương) cho kênh mới,
   đặt vào thư mục `<MÃ KÊNH>\<MÃ KÊNH>.exe` — CẠNH thư mục MyTool (không
   nằm trong CHANNEL/), ví dụ `C:\TL5-T7\TL5-T7.exe`.
2. Mở trình duyệt đó MỘT LẦN BẰNG TAY, đăng nhập tài khoản Google/YouTube
   của kênh (danh tính riêng — IPv6 riêng theo luật VPS, xem
   `CLAUDE.local.md` luật 1: đóng hết trình duyệt kênh khác trước khi làm
   việc này). Đăng nhập xong, vào YouTube Studio một lần cho chắc phiên
   đăng nhập đã lưu, rồi ĐÓNG trình duyệt lại — máy đăng sẽ tự mở nó khi cần.
3. Quay lại thuật sĩ "Thêm kênh" (hoặc mở lại nếu đã đóng), bước 2:
   - Tool tự dò trình duyệt theo đúng mã kênh; thấy dòng "✓ Đã thấy trình
     duyệt của kênh" là xong. Không thấy thì bấm "Thư mục trình duyệt" trỏ
     tay tới thư mục chứa `<MÃ>.exe`.
   - Tick **"Cho máy đăng lo kênh này (đăng + trả lời bình luận)"** — thiếu
     bước này thì video làm xong không bao giờ tự đăng.

## 3. Giọng đọc — PHẢI khác các kênh khác trên cùng máy

Mở `CHANNEL/<mã kênh>/kenh.yaml`, sửa khoá `voice_id` sang một giọng KHÁC
mọi kênh khác đang chạy trên máy này (xem danh sách trong từng
`kenh.yaml` của các kênh còn lại, hoặc hỏi chủ dự án nếu không chắc).

**Vì sao bắt buộc:** YouTube dùng giọng đọc (cùng nhiều tín hiệu khác) để
phát hiện nội dung nhân bản giữa các kênh — nhiều kênh cùng giọng, cùng máy,
cùng khung giờ đăng là dấu hiệu điển hình của "kênh trại" (content farm),
ảnh hưởng trực tiếp tới khả năng bật **YPP** (YouTube Partner Program —
1.000 subs + 4.000 giờ xem) của TẤT CẢ các kênh liên quan, không chỉ một.

> Tool **CHƯA tự chặn** trùng `voice_id` giữa các kênh (xem
> `workspace/LO-TRINH-PHAT-HANH-V3.md`, mục A16 — việc kiểm tự động còn
> đang chờ chủ dự án chốt). Tới lúc đó, đây là việc BẠN phải tự nhớ kiểm khi
> thêm kênh mới.

Đo lại `ky_tu_moi_phut` sau khi đổi giọng (xem chú thích ngay trong
`kenh.yaml`): lấy số ký tự kịch bản chia cho số phút của một file
`2-giong-doc.mp3` thật — giọng khác nhau đọc nhanh/chậm khác nhau, số cũ của
giọng trước không dùng lại được.

## 4. Đối thủ gốc — danh sách riêng, không trùng kênh khác

Kênh mới cần một danh sách kênh đối thủ RIÊNG để nghiên cứu chọn nguồn —
xem `CHANNEL/<mã kênh>/nghien-cuu/tuyen.csv` (bản đồ tuyến, đi kèm khuôn của
tool) và mở tab **Phân tích & Nghiên cứu** để thêm kênh đối thủ theo dõi.

Hai kênh của cùng bạn mà cùng "học" một nhóm đối thủ dễ ra kịch bản giống
nhau (cùng nguồn → cùng góc nhìn) — đúng vấn đề nội dung nhân bản ở mục 3.
Chọn đối thủ gốc lệch nhau (khác kênh nguồn, khác góc độ trong cùng ngách)
cho từng kênh mới thêm.

## 5. Ngân sách — trần tiền mỗi ngày

Bước 3 của thuật sĩ "Thêm kênh" (hoặc sau này ở `kenh.yaml`/Bảng điều
khiển):

- **Trần tiền mỗi ngày** (`ngan_sach_ngay`): kênh không bao giờ tiêu quá số
  này trong một ngày. Xem chi phí thật của một video trong báo cáo lượt chạy
  (Bảng điều khiển) rồi đặt trần ít nhất bằng chi phí một video — đặt
  trần thấp hơn thì kênh có ngày không ra video nào (không hỏng, chỉ chờ
  ngày mai). Để **0** thì kênh không tự sản xuất (dùng khi mới tạo, chưa
  muốn chạy thật).
- **Giờ đăng**: giờ video lên sóng mỗi ngày — máy VPS dùng giờ hệ thống của
  chính máy (`mui_gio_dang` mặc định = giờ VPS).
- Cân đối tổng ngân sách các kênh với ví ShopAPI: Bảng điều khiển (mục
  "Dòng máy") báo ví còn chạy được bao lâu theo tổng chi hiện tại.

## 6. Bật công tắc

- **"Cho kênh tự làm video mỗi ngày"** (`tu_chay: true`) — bật thì lịch
  `ShopAPI-TuChay` bắt đầu nghiên cứu/sản xuất cho kênh này từ lượt chạy kế
  tiếp (xem `README-VPS.md` mục 2).
- **"Tự đăng, không chờ duyệt"** (`tu_duyet`) — mặc định TẮT cho kênh mới
  (khuyến nghị giữ tắt ít nhất 7 ngày đầu, quyết định #7 trong lộ trình
  v3.0). Video làm xong nằm chờ ở Bảng điều khiển, bạn duyệt tay từng cái
  tới khi tin kênh chạy ổn rồi mới bật tự đăng.

Xong sáu bước, kênh mới sẽ xuất hiện thành một thẻ ở Bảng điều khiển
(`README-VPS.md` mục 3) từ lượt sản xuất kế tiếp.
