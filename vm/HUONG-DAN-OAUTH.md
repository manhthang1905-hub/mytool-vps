# Đăng nhập YouTube cho từng kênh (OAuth) — làm 1 lần cho mỗi kênh

Không cần biết lập trình. Làm đúng theo thứ tự, không bỏ bước.

**Vì sao phải làm việc này:** tool cần "quyền" của chính kênh YouTube để tự
trả lời bình luận và tự đăng bình luận mở đầu dưới video. Quyền này KHÔNG
phải mật khẩu Gmail — nó là một "tấm vé" (token) mà chỉ đúng phần mềm của
kênh đó dùng được, và kênh nào cũng cần một tấm vé riêng.

Làm cho **mỗi kênh mất khoảng 10–15 phút** (lần đầu có project Google Cloud
thì cộng thêm 5 phút). 4 kênh làm hết khoảng **45–70 phút**, nhưng từ kênh
thứ hai trở đi nhanh hơn (đã quen tay, và nếu dùng chung 1 "OAuth client" cho
mọi kênh thì bỏ qua được Phần A).

---

## Việc cần làm, tóm tắt 1 câu

1. (Chỉ làm 1 lần cho cả 4 kênh) Tạo một "chìa khoá phần mềm" trên trang của
   Google, tải một tệp `.json` về, đặt vào thư mục `vm\clients\`.
2. (Làm cho TỪNG kênh) Chạy một lệnh, làm theo màn hình hiện ra, xong.

---

## PHẦN A — Tạo "chìa khoá phần mềm" (làm 1 LẦN, dùng chung cho mọi kênh)

Đây là phần có vẻ "kỹ thuật" nhất nhưng chỉ cần bấm theo đúng thứ tự, không
cần hiểu các từ tiếng Anh trên màn hình.

### A1. Mở trang Google Cloud và tạo một "Project"

1. Mở trình duyệt **bất kỳ** (không cần đúng trình duyệt của kênh cho bước
   này), vào địa chỉ: `https://console.cloud.google.com/`
2. Đăng nhập bằng **một tài khoản Google bất kỳ** của bạn (tài khoản cá nhân
   cũng được — cái này chỉ để quản lý "chìa khoá phần mềm", không phải tài
   khoản kênh).
3. Trên thanh trên cùng, cạnh chữ "Google Cloud", có một ô tên dự án (chỗ
   thường ghi "My Project" hoặc tên project cũ). Bấm vào đó.
   - *Hình dung:* một hộp thoại nhỏ xổ xuống, có nút **"NEW PROJECT"** (Dự án
     mới) ở góc trên bên phải hộp thoại.
4. Bấm **"NEW PROJECT"**. Đặt tên bất kỳ, ví dụ `shopapi-cmt`. Bấm **CREATE**
   (Tạo). Đợi vài giây tới khi có thông báo tạo xong (một chuông nhỏ góc
   trên bên phải sẽ báo).
5. Sau khi tạo xong, bấm lại vào ô tên dự án ở bước 3, chọn ĐÚNG project vừa
   tạo (`shopapi-cmt`) để "đứng" trong project đó.

### A2. Bật "YouTube Data API v3"

1. Vào ô tìm kiếm trên cùng của trang (biểu tượng kính lúp), gõ:
   `YouTube Data API v3`
2. Bấm vào kết quả đúng tên đó.
   - *Hình dung:* một trang giới thiệu API hiện ra, có nút xanh **ENABLE**
     (Bật) ở giữa hoặc góc trên.
3. Bấm **ENABLE**. Đợi vài giây.

### A3. Tạo màn hình xin quyền (OAuth consent screen)

1. Ô tìm kiếm trên cùng, gõ: `OAuth consent screen`, bấm vào kết quả đó.
2. Chọn loại **External** (Bên ngoài), bấm **CREATE**.
3. Điền:
   - **App name** (Tên ứng dụng): gõ gì cũng được, ví dụ `Kenh cua toi`.
   - **User support email**: chọn email của bạn trong danh sách xổ xuống.
   - **Developer contact information**: gõ lại email của bạn.
   - Các ô khác để trống, cứ bấm **SAVE AND CONTINUE** (Lưu và tiếp tục) ở
     những màn tiếp theo (Scopes, Test users) cho tới khi thấy trang tóm tắt.
4. Ở màn **Test users** (Người dùng thử), bấm **+ ADD USERS**, gõ đúng email
   Gmail của TỪNG kênh YouTube bạn định gắn tool (ví dụ email quản lý kênh
   TL1-T7, TL2-T7...). Đây là bước QUAN TRỌNG — thiếu bước này, lúc đăng nhập
   ở Phần B, Google sẽ báo "ứng dụng chưa được xác minh, không cho vào".
5. Bấm **SAVE AND CONTINUE** tới khi xong.

### A4. Tạo "OAuth client" kiểu Desktop và tải tệp về

1. Ô tìm kiếm trên cùng, gõ: `Credentials` (Thông tin xác thực), bấm vào.
2. Bấm **+ CREATE CREDENTIALS** (Tạo thông tin xác thực) → chọn
   **OAuth client ID**.
3. Ở ô **Application type** (Loại ứng dụng), chọn **Desktop app** (Ứng dụng
   máy tính để bàn). Đây là chỗ hay chọn nhầm nhất — PHẢI là "Desktop app",
   không phải "Web application".
4. Đặt tên bất kỳ, ví dụ `may-tinh-dang-nhap`. Bấm **CREATE**.
5. Một hộp thoại hiện ra báo đã tạo xong, có nút **DOWNLOAD JSON**
   (Tải xuống JSON). Bấm nút đó — một tệp `.json` sẽ tải về máy (thường vào
   thư mục Downloads).

### A5. Đặt tệp vừa tải vào đúng chỗ

1. Tìm tệp vừa tải (tên dạng `client_secret_xxxxx.json`) trong thư mục
   Downloads.
2. Đặt nó vào thư mục: `vm\clients\`
   - **Nếu dùng CHUNG 1 chìa khoá cho mọi kênh** (cách đơn giản nhất — đủ
     dùng cho 4 kênh cùng một VPS): chỉ cần đặt ĐÚNG MỘT tệp `.json` vào
     thư mục `vm\clients\`, đặt tên gì cũng được. Tool tự nhận ra "chỉ có 1
     tệp thì dùng chung cho mọi kênh" — không cần làm lại Phần A cho kênh
     sau.
   - **Nếu muốn mỗi kênh một chìa khoá riêng** (an toàn hơn nhưng phải lặp
     lại Phần A cho từng kênh): đổi tên tệp thành ĐÚNG mã kênh, ví dụ
     `TL1-T7.json`, rồi đặt vào `vm\clients\`.

Xong Phần A. Phần này **không phải làm lại** cho các kênh sau nếu bạn chọn
cách "dùng chung 1 chìa khoá".

---

## PHẦN B — Đăng nhập cho TỪNG kênh (lặp lại cho mỗi kênh)

Làm lần lượt cho từng kênh: `TL1-T7`, `TL2-T7`, `TL3-T7`, `TL4-T7`, ...

### B1. Mở cửa sổ dòng lệnh đúng thư mục tool

1. Mở thư mục `MyTool` (thư mục chứa tool này).
2. Bấm vào thanh địa chỉ của cửa sổ thư mục (phía trên), gõ `cmd`, bấm Enter
   — một cửa sổ đen (dòng lệnh) sẽ mở ra, đã đứng sẵn ở đúng thư mục.

### B2. Chạy lệnh cho kênh muốn đăng nhập

Gõ đúng dòng sau (đổi `TL1-T7` thành mã kênh bạn đang làm), rồi Enter:

```
python vm\setup_oauth.py --kenh TL1-T7
```

### B3. Làm theo màn hình hiện ra

Cửa sổ dòng lệnh sẽ tự nói cho bạn biết đang thiếu gì (nếu thiếu Phần A thì
nó sẽ nhắc quay lại đọc hướng dẫn này, không làm hỏng gì cả — cứ đọc và làm
theo).

Nếu mọi thứ đã sẵn sàng, sẽ xảy ra MỘT trong hai trường hợp:

**Trường hợp 1 — tool tự mở trình duyệt của kênh (thường gặp nhất):**

- Một cửa sổ Chrome của ĐÚNG kênh đó tự bật lên.
- Tool tự bấm qua hầu hết các bước. Nếu màn hình dừng lại ở chỗ **chọn tài
  khoản** (Choose an account), bạn tự bấm chọn ĐÚNG tài khoản của kênh này
  (đừng chọn tài khoản cá nhân khác nếu có nhiều tài khoản hiện ra).
- Nếu Google cảnh báo "Google hasn't verified this app" (Google chưa xác
  minh ứng dụng này) — đây là chuyện BÌNH THƯỜNG vì bạn tự tạo chìa khoá ở
  Phần A, không phải lỗi. Bấm chữ nhỏ **Advanced** (Nâng cao) rồi bấm
  **Go to (tên ứng dụng) (unsafe)** — tool cũng tự làm được bước này, nhưng
  nếu nó dừng lại thì bạn bấm hộ.
- Cuối cùng có dòng "Xác thực thành công!" — thế là xong, cửa sổ dòng lệnh
  báo **XONG**.

**Trường hợp 2 — không tìm thấy trình duyệt riêng của kênh, tool in ra một
đường dẫn (link):**

- Bạn tự chép nguyên đường dẫn đó, dán vào **đúng trình duyệt bạn đã đăng
  nhập sẵn tài khoản của kênh này**, Enter.
- Đăng nhập / bấm Cho phép tới cùng như trường hợp 1.
- Xong, quay lại cửa sổ dòng lệnh sẽ tự báo **XONG** — không cần dán gì
  ngược lại vào cửa sổ dòng lệnh.

### B4. Kiểm tra đã xong chưa

Cửa sổ dòng lệnh in dòng:

```
XONG. Kenh TL1-T7 da san sang: tu tra loi binh luan VA tu dang binh luan mo dau cho video moi.
```

Vậy là kênh đó xong. Lặp lại B2–B3 cho kênh tiếp theo.

---

## Lỡ đăng nhập nhầm tài khoản / muốn làm lại một kênh

Xoá đúng một tệp: `vm\tokens\<mã kênh>.json` (ví dụ `vm\tokens\TL1-T7.json`),
rồi chạy lại đúng lệnh ở B2 cho kênh đó.

## Vài câu hay gặp

- **"Error 400: redirect_uri_mismatch"** — bạn chọn nhầm loại ứng dụng ở A4
  (chọn "Web application" thay vì "Desktop app"). Xoá OAuth client đó, làm
  lại đúng A4 với "Desktop app".
- **"Access blocked: this app's request is invalid"** hoặc báo không cho
  đăng nhập — kiểm lại bước A3.4 (đã thêm đúng email của kênh vào Test
  users chưa).
- **Không có việc "ghim" bình luận nào chạy tự động** — đúng vậy, đây không
  phải lỗi. YouTube không cho phần mềm nào ghim bình luận thay người dùng
  (không có "nút API" nào làm việc đó). Sau khi kênh đăng nhập xong, tool tự
  ĐĂNG bình luận mở đầu; việc GHIM nó lên đầu vẫn cần bạn tự bấm 1 cái — mở
  tệp `CHANNEL\<mã kênh>\can-ghim.md` mỗi ngày, trong đó có sẵn link thẳng
  tới từng video cần ghim.
