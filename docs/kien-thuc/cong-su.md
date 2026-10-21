# Cộng sự (Collaborators) — đo thật 21/10/2026

Tính năng «Cộng tác» của YouTube Studio, đo bằng thăm dò CHỈ ĐỌC trên Chrome kênh thật (không lưu, không mời).
Máy dùng: `core/cong_su.py` (quét, lập lô, đo — skill D25) + `vm/cong_su_dom.py` (mời/nhận — skill D26).

## Giao diện (Studio tiếng Việt)

- Trang sửa video → «Hiện thêm» → khối **Cộng tác** (`ytcp-video-metadata-editor-advanced div#collaboration-container`)
  → nút **Mời cộng sự** (`ytcp-button#collaboration-button`). Có ở mọi kênh đã thử, kể cả kênh chưa xác minh điện thoại.
- Hộp **Mời cộng sự** (`ytcp-video-collaborators-dialog`): ô **Tìm kênh** (`input#search-input`) → danh sách kết quả
  (`ytcp-channel-picker-list tp-yt-paper-item.channel`, mỗi hàng: tên + «@handle • N người đăng ký») → Hủy / Lưu.
  **Esc không đóng hộp** — phải bấm Hủy.
- Ô tìm chỉ nhận **tên hoặc @handle**. Dán link kênh hay mã UC → «Không tìm thấy người dùng phù hợp». Gõ @handle → đúng
  một kết quả. Trong DOM không có UC → máy lấy @handle từ trang kênh công khai (`vanityChannelUrl`), rồi so khớp nguyên văn.
- Video đã có cộng sự: nút đổi thành **Quản lý cộng tác viên**. Các hàng cộng sự chỉ nằm trong hộp
  (`div.collaborator`). Mỗi hàng chỉ có tên kênh (`[test-id=channel-name]`) và nhãn `ytcp-badge[test-id=collaborator-badge]`
  (state="complete", «Cộng sự đang hoạt động»), cộng nút ⋮ — máy không bao giờ bấm nút này. Máy đọc lại theo tên kênh.
- Giới hạn: hộp có sẵn dòng ẩn «**Bạn đã đạt đến giới hạn tạo lời mời**» (`#limit-reached-message`). Video của TL4 do chủ
  tự làm có 4 cộng sự + chủ, nên trần ≥ 4. Mặc định máy là 5 (`toi_da_moi_video`); máy dừng khi dòng giới hạn hiện ra.
- Kênh được mời: trang Nội dung có tab **Video cộng tác** = `studio.youtube.com/channel/<UC>/videos/collaboration`, mỗi
  video là một `ytcp-video-row` có chip kênh chủ. **Chưa đo được nút Chấp nhận** vì chưa có lời mời nào đang chờ. Máy chỉ
  bấm nút nằm trong hàng của đúng video và có chữ khớp nguyên văn (`cs_nut_nhan.chu`), sau đó đọc lại.

## Cộng tác làm gì (kiểm trên video TL4 mà chủ đã thêm TL1/TL2/TL3 làm cộng sự)

- **Trang xem công khai**: `videoOwnerRenderer` mở hộp «コラボレーター». Hộp liệt kê chủ và từng cộng sự (tên, @handle,
  số người đăng ký), **mỗi kênh có nút đăng ký riêng**. Tự kiểm xác minh ghi công bằng `browseId` trong khối này.
  Không đọc cả trang, vì video đề xuất cũng có hộp cộng tác của kênh khác.
- **Kênh cộng sự**: video hiện ở kệ «コラボレーション» trên trang chủ kênh, **không** hiện trong tab Video.
- **Số liệu**: hộp mời ghi «Quyền sở hữu toàn bộ — Bạn nắm giữ toàn bộ doanh thu, lượt xem và thời gian xem của video».
  Vậy view, giờ xem và doanh thu đều tính cho **kênh nguồn**. Kênh cộng sự chỉ có thể được thêm: hiển thị, người đăng ký
  qua nút riêng trên trang xem, và lượt xem lan sang video của chính nó. Phần đo của máy tính đúng các số đó.

## Luật chạy (chủ duyệt 21/10/2026)

Kích hoạt khi video > 20.000 lượt xem trong 48 giờ đầu → mời mọi kênh ta đang chạy, ưu tiên theo thứ tự: cùng vùng → kênh
mới / kênh xa mốc 1.000 đăng ký nhất → các kênh còn lại. Chia hai đợt A (mời ngay) và B (sau 24 giờ) để so nhân quả.
Mỗi ngày tối đa 30 lời mời, mỗi kênh nguồn tối đa 1 lô mỗi ngày. Nếu YouTube hiện hộp cảnh báo, máy dừng hẳn
(`workspace/cong-su/dung.json`) và báo vào Việc của bạn. Cài đặt nằm ở `workspace/cai-dat.json`, khoá `cong_su`.
