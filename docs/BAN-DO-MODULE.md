# Bản đồ module chính — theo khâu

Dành cho người sửa mã (phiên Claude Code) cần biết ĐỌC FILE NÀO trước khi
viết. Xếp theo đúng dòng chảy một video: nghiên cứu → chọn nguồn → 8 khâu
sản xuất → bàn giao → đăng → dọn dẹp → báo cáo, rồi tới hạ tầng VPS (chạy
24/7 không cần người). Đây là bản đồ, KHÔNG phải tài liệu API — đọc code
thật của module trước khi sửa, docstring đầu mỗi tệp luôn có bối cảnh "vì
sao" đầy đủ hơn bảng này nhiều.

> Cột "được sửa" chỉ tình trạng lúc viết tài liệu này (29/09/2026, phiên
> đóng băng tới sáng 30/09) — không phải luật vĩnh viễn. `core/che_do_vps.py`
> nói riêng vẫn đang bị đóng băng vì một agent khác đang sửa các module cập
> nhật (`core/safe_update.py`, `core/cap_nhat_github.py`,
> `core/nguon_cap_nhat.py`, `ui_qt/cap_nhat.py`, `vm/giao_dien.py`) cùng lúc.

## 1. Nghiên cứu → chọn nguồn

| Module | Việc |
|---|---|
| `core/danh_ba_doi_thu.py` | Danh sách kênh đối thủ theo dõi cho từng kênh/nhóm. |
| `core/doi_thu_kenh.py` | Cào số liệu kênh đối thủ (view, sub, ngày đăng). |
| `core/mot_nut.py` | "Một nút" — chuỗi nghiên cứu tự động: cào đối thủ → chấm điểm → đề xuất nguồn, chạy từ `tu_chay.py`. |
| `core/cong_thuc_v7.py`, `core/cong_thuc_v7_ai.py` | Công thức chấm điểm nội dung — **A1**: hiện cứng khuôn "tâm lý × Nhật", xem `docs/DOI-CHU-DE.md` mục 0. |
| `core/phan_tuyen.py`, `core/tuyen_con.py`, `core/tuyen_noi_dung.py` | Phân tuyến nội dung (chủ đề con trong ngách) — cùng nhóm A1-A5. |
| `core/chot_doi_thu.py` | Chốt danh sách đối thủ gốc dùng để so sánh/chấm điểm. |
| `core/trung_tieu_de.py` | Chặn trùng tiêu đề giữa các video cùng kênh. |
| `core/kiem_trung_y.py` | Kiểm trùng Ý TƯỞNG (không chỉ trùng chữ) trước khi vào sản xuất. |

## 2. Tám khâu sản xuất (mỗi kênh, mỗi lượt)

Định nghĩa TÁM khâu nằm ở `core/auto.py:KHAU` — đây là danh sách CHUẨN, đổi
tên khâu ở đây thì mọi nơi khác (bàn giao, dọn dẹp, báo cáo) phải đổi theo:

| # | Mã khâu | Làm gì | Bắt buộc? |
|---|---|---|---|
| 1 | `kich-ban` | Viết kịch bản (`1-kich-ban.txt`) | Có |
| 2 | `giong-doc` | Đọc thành giọng nói (`2-giong-doc.mp3`) | Có |
| 3 | `phu-de` | Tách phụ đề bằng Whisper (`3-phu-de.srt`) | Không (lớp B, máy nặng) |
| 4 | `bang-canh` | Cắt cảnh + viết lời nhắc ảnh (`4-canh.xlsx`) | Có |
| 5 | `anh` | Tạo ảnh từng cảnh (`5-anh/`) | Có — chậm nhất (45-150'), lớp A song song |
| 6 | `clip` | Tạo clip từng cảnh (`6-clip/`) | Có |
| 7 | `thumbnail` | Tạo ảnh bìa (`7-thumbnail/`) | Có — nhưng KHÔNG chặn khâu 8 (`KHAU_KHONG_CHAN`) |
| 8 | `dung` | Dựng video hoàn thiện bằng FFmpeg (`8-video.mp4`) | Không (lớp B, máy nặng, chạy trên máy) |

Động cơ chạy các khâu này: `core/auto_khau.py` (hàng đợi job gọi máy chủ
ShopAPI, `SoTheoDoi` theo dõi job — **đây là chỗ trừ tiền thật**, xem luật 3
của `CLAUDE.md`), điều phối bởi `core/tu_chay.py` (một lượt/kênh/ngày) và
`core/che_do_vps.py` (giới hạn song song theo lớp `"api"`/`"nang"` trên VPS
nhiều kênh).

Việc RIÊNG máy chạy trên đĩa/CPU (không gọi máy chủ, không tốn tiền):
`core/ffmpeg_goi_san.py` (bảo đảm có FFmpeg đủ dùng, ưu tiên bản đi kèm
`imageio-ffmpeg` trước khi tải mạng ngoài), `core/dung_video.py` (dựng
thật), `core/kho_nhac.py` (chuẩn hoá nhạc nền từ `PROJECTS/music`).

## 3. Bàn giao → xếp lịch → đăng

| Module | Việc |
|---|---|
| `core/ban_giao_dang.py` | Xuất gói (`8-video.mp4` + phụ đề + thumbnail + tiêu đề/mô tả) từ `PROJECTS/AUTO/<kênh>/<lượt>/` sang `DONE/<mã gói>/`. |
| `core/ke_hoach_dang.py` | Kế hoạch đăng của một kênh — `CHANNEL/<kênh>/ke-hoach-dang/ke-hoach.csv`, nguồn THẬT thay cho trang tính cũ. |
| `vm/may_dang.py`, `vm/may_dang_dom.py` | Máy đăng — đọc `DONE/`, điền form YouTube Studio (DOM, qua `vm/cdp.py` — Chrome DevTools Protocol) hoặc giả lập chuột/phím, đăng theo lịch. |
| `vm/cdp.py`, `vm/cdp_studio.py` | Nói chuyện với Chrome qua DevTools Protocol (cần `websocket-client`, xem vá 29/09/2026 — `vm/requirements-vm.txt`). |
| `vm/agent.py` | Vòng lặp phiên kênh: mở trình duyệt kênh (chỉ MỘT lúc), cào Studio + trang chủ, gọi máy đăng, trả lời bình luận, đóng. |
| `vm/may_cmt.py` | Trả lời bình luận tự động. |

## 4. Dọn dẹp, giám sát, báo cáo

| Module | Việc |
|---|---|
| `core/don_dep.py`, `core/don_dep_mo_rong.py` | Dọn `PROJECTS/AUTO/<kênh>/<lượt>` đã bàn giao/đã công khai. |
| `core/nhuong_phien_kenh.py` | Nhường khoá giữa lượt sản xuất và phiên kênh (không đè lên nhau). |
| `core/vong_hoc.py` | Vòng học — kênh tự điều chỉnh theo phản hồi số liệu thật. |
| `core/bao_dong.py`, `core/su_co.py` | Báo động/sự cố — phát hiện bất thường (ví cạn, job kẹt, kênh lỗi liên tục). |
| `core/da_lam.py`, `core/tu_nhan_da_dang.py` | Sổ đã làm — chặn làm lại/đăng lại việc đã xong. |
| `core/bang_dieu_khien.py` | Lõi dữ liệu THUẦN cho trang Bảng điều khiển (`ui_qt/trang_bang_dieu_khien.py`) — xem `README-VPS.md` mục 3. |
| `core/tong_quan_vps.py` | Cảnh báo Windows sắp hết hạn + số liệu tổng quan máy. |
| `core/chi_so_ytb/` | Đọc số liệu YouTube Studio thật (mốc theo TUỔI THẬT video). |

## 5. Hạ tầng VPS — chạy 24/7 không cần người

| Module | Việc |
|---|---|
| `core/tram.py` | Trạm nội bộ, cổng 8765, chỉ `127.0.0.1` — cầu nối MyTool ↔ `vm/agent.py`. |
| `core/giam_sat_vm.py` | Trông ba động cơ của `vm/` (agent/may_dang/may_cmt) từ MyTool. |
| `core/che_do_vps.py` | Đánh dấu + giới hạn song song khi chạy chế độ VPS (đọc `vps.json`). **Đóng băng — xem cảnh báo đầu trang.** |
| `core/lich_tu_chay.py` | Bọc `schtasks.exe` — 3 việc: `ShopAPI-TuChay` (sản xuất hằng ngày), `ShopAPI-CanhTram` (canh trạm mỗi 5'), `ShopAPI-TramLucDangNhap` (một lượt kiểm lúc đăng nhập). |
| `core/khe.py`, `core/uu_tien.py`, `core/so_job_chung.py`, `core/bang_thong.py` | Đợt 1 (29/09/2026) — khe tài nguyên liên tiến trình + ưu tiên P0-P4 + đệm sổ job dùng chung. **MỚI, THUẦN, CHƯA NỐI vào `tu_chay.py`/`auto_khau.py`/`agent.py`** — xem `workspace/ban-va/2026-09-29-dot1-khe-uu-tien/GHI-CHU.md`. |
| `vm/cai_dat_vps.py` + `CAI-DAT-VM.bat` | Cài VPS từ GÓI đóng sẵn trên máy nhà (`vm/goi-vps/tool.zip`) — luồng CŨ. |
| `vm/cai_dat_tu_kho.py` + `CAI-DAT-VPS.bat` | Cài VPS từ BẢN CLONE git thẳng — luồng MỚI (Việc 5.1, 29/09/2026), xem `README-VPS.md` mục 1. |
| `core/kiem_may.py` | `python -m core.kiem_may --day-du` — bảng OK/THIẾU kiểm máy đã sẵn sàng tự chạy chưa (Việc 5.1). |
| `core/goi_vps.py` | Đóng gói `vm/goi-vps/` trên máy nhà (nút "Tạo bộ cài VPS", tab VM). |
| `core/safe_update.py`, `core/cap_nhat_github.py`, `core/nguon_cap_nhat.py` | Cập nhật tool từ kho GitHub. **Đang được một agent khác sửa (Đợt 5.2/5.3) — không đụng.** |
| `core/kenh.py` | Đọc/ghi `kenh.yaml`, nhân bản kênh (`nhan_ban_kenh`). **Đóng băng.** |
| `core/nhom_kenh.py` | Tạo kênh trong một nhóm (`tao_kenh_trong_nhom`) — lõi của thuật sĩ "Thêm kênh". |

## 6. Giao diện (PyQt5)

| Module | Việc |
|---|---|
| `ui_qt/app.py` | Cửa sổ chính, danh sách tab (`TRANG`), xưởng dựng trang (`_dung_cac_trang`). Trên VPS, trang mở đầu là `tong-quan` (khoá `core.che_do_vps.KHOA_TRANG_TRUNG_TAM`) = Bảng điều khiển. |
| `ui_qt/trang_bang_dieu_khien.py` | Trang **Bảng điều khiển** — vẽ dữ liệu từ `core.bang_dieu_khien`. |
| `ui_qt/trang_trung_tam.py` | Trang **Trung tâm** / **Kênh** + hộp thoại 3 bước **"Thêm kênh"** (`HopThemKenh`). |
| `ui_qt/trang_quan_ly_kenh.py` | Quản lý kênh — sửa `kenh.yaml`, nút "Nhân bản". |
| `ui_qt/huong_dan.py` | Nội dung nút "? Hướng dẫn" của từng tab — cập nhật khi thêm/đổi tab. |

## Cách dùng bản đồ này

1. Biết đang sửa việc thuộc KHÂU nào (nghiên cứu? sản xuất? đăng? hạ tầng?).
2. Tra bảng tương ứng, mở đúng module, ĐỌC HẾT docstring đầu tệp trước khi
   sửa — phần lớn quyết định khó hiểu ở đây đều có lý do lịch sử ghi ngay
   trong code (ngày, người, số đo thật), không phải chỉ đọc tên hàm là đủ.
3. Kiểm danh sách "TUYỆT ĐỐI KHÔNG SỬA" của phiên hiện tại (nếu có) trước
   khi động vào bất cứ tệp nào trong `core/`/`vm/` — xem đầu
   `CLAUDE.local.md` hoặc chỉ dẫn giao việc của phiên đó.
