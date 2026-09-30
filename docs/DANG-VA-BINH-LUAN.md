# Đăng video và bình luận

Mọi việc ở đây do phiên kênh `vm/agent.py` làm. Giao diện (`core/giam_sat_vm.py`) trông agent này và tự mở lại khi nó chết. Không có lối tắt hay lịch Windows riêng cho `vm/`.

## 1. Phiên kênh
- Khoảng `phien_truoc_phut` (mặc định 60) phút trước giờ đăng, agent mở trình duyệt của kênh. Mỗi lúc chỉ một trình duyệt.
- Trong phiên, agent làm lần lượt: quét Studio và trang chủ → lấy lời thoại đối thủ → đăng → bình luận → đóng trình duyệt.
- Hôm nào kênh không có gì để đăng thì phiên chạy lúc `gio_phien` (mặc định 07:30).
- Video chờ đăng nằm ở `DONE/<mã gói>/`. `core/ban_giao_dang.py` xuất gói vào đó. Kế hoạch đăng nằm ở `CHANNEL/<k>/ke-hoach-dang/ke-hoach.csv`.
- Luật an toàn:
  - không bao giờ bật IPv4 khi trình duyệt đang mở;
  - không taskkill;
  - chỉ đóng tab của mình;
  - nháp thừa trên Studio thì chỉ báo, không xoá.

## 2. Thiết lập của từng kênh
Thiết lập nằm ở `CHANNEL/<k>/may-ao.json`. Trạm đẩy xuống agent mỗi nhịp, nên sửa xong agent nhận ngay. Mặc định và giải thích từng khoá ở `core/vm_cai_dat.py` (`MAC_DINH`). Các khoá chính:

| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `tu_dang` | `false` | Máy đăng có đăng kênh này không |
| `cach_dang` | `"anh"` | `anh`: dò ảnh (`vm/may_dang.py`). `dom`: DevTools (`vm/may_dang_dom.py`), hỏng thì dừng. `tu_dong`: thử DOM trước, DOM báo mã 3 thì lùi sang đường ảnh |
| `binh_luan_dom` | `true` | Bình luận mồi và trả lời bình luận qua DOM (`vm/may_cmt_dom.py`) |
| `cmt_toi_da_phien` | `10` | Số bình luận mới tối đa được trả lời trong mỗi phiên |
| `ghim_dom` | `false` | Tự ghim bình luận mồi. Tắt vì YouTube đòi xác minh số điện thoại |
| `tu_tra_loi_cmt`, `lay_loi_thoai` | `true` | Trả lời bình luận; lấy lời thoại đối thủ bằng trình duyệt kênh |

`cach_dang` là quyết định của chủ dự án. Chỉ đổi sau khi đã đăng thử đạt.

## 3. Máy đăng
- **DOM** (`vm/may_dang_dom.py`): điền form Studio qua DevTools (`vm/cdp.py`, `vm/cdp_studio.py`). Bộ chọn phần tử nằm ở `vm/studio-selectors.json`.
  - Mã thoát: 0 xong · 1 hỏng sau khi đã chạm kênh (không lùi, lượt sau tiếp tục nháp) · 3 DOM không dùng được trước khi chạm kênh · 4 bị chặn an toàn.
  - Sổ chống trùng: `vm/logs/so-video-id.json`.
  - Kiểm mà không đăng: `python vm/may_dang_dom.py --kiem-dom --kenh <k>`.
- **Ảnh** (`vm/may_dang.py`): dò nút trên màn hình bằng PyAutoGUI và ảnh mẫu `vm/icon/*.PNG`. Đây là đường lùi. Nó cần phiên RDP có màn hình.
- Nhật ký: `vm/logs/dang-dom.log`, `vm/logs/dang.log`, `vm/agent.log`.
- Tải hỏng để lại nháp thì lượt sau tải bản mới. Không sửa, không xoá nháp cũ.

## 4. Bình luận
- **DOM** (`vm/may_cmt_dom.py`) là đường chính. Nó dùng Chrome kênh đã đăng nhập, không cần OAuth. Việc gồm: đăng bình luận mồi (`1-binh-luan.txt` trong gói), ghim (khi `ghim_dom`), và trả lời bình luận mới.
  - Chỉ chạy cho kênh đang `tu_dang`.
  - Spam, link, xúc phạm: để nguyên, không xoá, không trả lời.
  - Sổ: `vm/logs/cmt-dom.json`. Id đã trả lời lưu ở `vm/replied/<k>.txt`, dùng chung với đường API nên không bao giờ trả lời trùng.
  - Kiểm mà không gửi: `python vm/may_cmt_dom.py --kenh <k> --kiem-dom`.
- Không ghim được thì việc ghim được ghi vào `CHANNEL/<k>/can-ghim.md`, kèm link video. Ghim tay xong thì bấm "Đã ghim" ở Bảng điều khiển.

## 5. OAuth: đường dự phòng qua YouTube Data API
Agent chọn `vm/may_cmt.py` (API) thay cho DOM khi kênh đã có token `vm/tokens/<k>.json`, hoặc khi `binh_luan_dom=false`. Hai đường không bao giờ chạy cùng lúc. API không ghim được bình luận. Chỉ làm phần này khi thật sự cần API.

**A. Chìa khoá phần mềm** (làm một lần, dùng chung cho mọi kênh):
1. Vào https://console.cloud.google.com/, đăng nhập tài khoản Google bất kỳ, tạo project mới.
2. Tìm "YouTube Data API v3" và bấm **Enable**.
3. Vào **OAuth consent screen**:
   - chọn **External**;
   - điền tên ứng dụng và email;
   - ở màn **Test users**, thêm email của **từng kênh**. Thiếu bước này thì Google chặn đăng nhập.
4. Vào **Credentials → Create credentials → OAuth client ID**, chọn loại **Desktop app** (không phải Web application), rồi bấm **Download JSON**.
5. Đặt tệp vừa tải vào `vm\clients\`:
   - chỉ một tệp thì dùng chung cho mọi kênh;
   - muốn mỗi kênh một chìa khoá thì đặt tên tệp là `<mã kênh>.json`.

**B. Đăng nhập từng kênh:**
1. Mở cmd ở thư mục `MyTool` và chạy `python vm\setup_oauth.py --kenh <mã kênh>`.
2. Tool tự mở Chrome của kênh và bấm qua các bước. Nếu dừng ở màn chọn tài khoản thì chọn đúng tài khoản kênh.
3. Gặp cảnh báo "Google hasn't verified this app" thì bấm **Advanced → Go to … (unsafe)**. Đây là bình thường.
4. Không tìm thấy Chrome của kênh thì tool in ra một link. Dán link đó vào trình duyệt đã đăng nhập kênh.
5. Thấy dòng `XONG. Kenh <k> da san sang…` là xong.

Làm lại cho một kênh: xoá `vm\tokens\<mã kênh>.json` rồi chạy lại lệnh ở B.

Lỗi hay gặp:
- `redirect_uri_mismatch`: đã chọn nhầm loại "Web application" ở bước A4.
- "Access blocked": chưa thêm email kênh vào Test users.
