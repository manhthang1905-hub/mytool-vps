# Chiến lược chọn nguồn — hướng dẫn người vận hành

Dành cho người dựng VPS mới hoặc mở ngách/quốc gia mới, không cần đọc mã. Mọi thay đổi chỉ là sửa YAML. Chưa khai khoá mới nào thì tool chạy y như trước. Thiết kế bên trong (plugin công thức, `NguCanh`, dòng chuẩn): `thiet-ke-chien-luoc.md`.

## 1. Vòng học trong 5 dòng

1. Mỗi lượt, **công thức** (VPH / V7 / Một nút / công thức tự thêm) xếp hạng video nguồn chưa làm.
2. **Biên tập viên AI** đọc bảng theo nghĩa, chấm TỐT / TẠM / TỆ, chốt 1 nguồn.
3. Tool làm video, đăng, đọc số Studio ở mốc 48h / 72h.
4. Mỗi video ghi lại công thức đã chọn nó; vòng học đếm thắng/trượt theo công thức (`nghien-cuu/chien-luoc.json`) và rút bài học (`nghien-cuu/bai-hoc-*.json`).
5. Bài học quay lại bước 1–2: tiêu chí chấm, lời nhắc biên tập, và (nếu bật) tỉ trọng công thức.

**"Thắng" luôn đo theo chính kênh:** hiển thị @48h ≥ max(ngưỡng tối thiểu, bội số × trung vị 48h của kênh). Không có con số cứng chung.

## 2. VPS mới / ngách mới / quốc gia mới

1. **Tạo nhóm ngách:** chép một mẫu trong `CHANNEL/_KHUON/` thành `CHANNEL/_NHOM/<tên-nhóm>/ngach.yaml`.

   | mẫu | dùng khi |
   |---|---|
   | `ngach-mau.yaml` | ngách bất kỳ; có chú thích từng khoá |
   | `ngach-mau-vi.yaml` / `ngach-mau-en-us.yaml` | khung thị trường Việt Nam / Mỹ |
   | `ngach-mau-ja-tam-ly.yaml` | bản đầy đủ của nhóm tâm lý Nhật đang chạy — tra cứu mọi khoá |

2. **Viết 3 khoá "theo nghĩa" trước tiên** (AI đọc để chọn và lọc nguồn):
   - `mo_ta_ngach`: một câu nói ngách là gì;
   - `mo_ta_cho_loc_ai`: cái gì đúng ngách, cái gì lệch;
   - `luat_chon`: danh sách câu ngắn — luật chọn nguồn.

   **Đừng thêm danh sách từ khoá để lọc nội dung.** Phân loại do AI làm theo nghĩa; từ khoá chỉ là đường lùi khi AI lỗi.
3. **Thị trường** (`thi_truong:`): `quoc_gia`, `ngon_ngu`, `mui_gio`, `bac_lam_tron_view` (bậc làm tròn view YouTube hiển thị ở thị trường đó), `ctr_trang_chu_muc_tieu` (nếu khác 5%). Thị trường nhỏ hơn thì khai thêm `bac_view_manh` (mặc định 100000) và `tran_vuot` (mặc định 25) — hai khoá quyết định thế nào là nguồn "đang nổ thật".
4. **Gắn kênh vào nhóm:** trong `CHANNEL/<kênh>/kenh.yaml` thêm `nhom: "<tên-nhóm>"` và `tep: "<mã tệp khán giả>"`. Tạo kênh, trình duyệt, giọng đọc: `docs/THEM-KENH.md`.
5. **Chạy thử miễn phí** ở chế độ `--thu` (không tốn ví), đọc log chọn nguồn: dòng `đang dùng công thức …`, phải có ứng viên và tiêu đề đúng ngách.

Ưu tiên khi một khoá khai nhiều nơi: **kenh.yaml > ngach.yaml > mặc định trong mã** — mỗi kênh vẫn tự cá nhân hoá được trong nhóm.

## 3. Khoá kenh.yaml của bộ máy chọn nguồn

| khoá | mặc định | tác dụng |
|---|---|---|
| `cong_thuc_chon` | `tu_dong` | 1 công thức: `v7` / `vph` / `mot_nut` / tên mới. `tu_dong` = V7 khi kênh đã có video thắng, còn lại VPH |
| `chien_luoc` | *(không khai)* | trộn nhiều công thức, ví dụ `"vph:0.8, v7:0.2"`, hoặc `"tu_dong"` |
| `chien_luoc_tham_do` | `20` | % lượt thăm dò khi có ≥ 2 công thức |
| `chien_luoc_tu_hoc` | `false` | `true` = tự dồn tỉ trọng theo thắng/trượt thật |
| `de_bai_bien_tap` | *(không khai)* | `"gon"` = đề bài gọn: MỤC TIÊU 3 dòng + `luat_chon` + bài học kênh |
| `luat_chon` | từ ngach.yaml | luật riêng của kênh, đè luật nhóm |
| `bac_view_manh`, `tran_vuot` | 100000, 25 | ngưỡng bảng Một nút theo cỡ thị trường |
| `ypp_sub`, `ypp_gio`, `da_kiem_tien` | *(không khai)* | số trọn đời cho dòng mục tiêu YPP (số tự đọc từ Studio chỉ là 28 ngày) |
| `bien_tap_ai`, `phan_cum_ai` | `true` | tắt biên tập / phân cụm AI (chỉ khi gỡ lỗi) |
| `cho_phep_tep_gia` | `false` | `true` = kênh nhắm tệp người già: tắt cổng tuổi cho riêng kênh đó |

**Kênh nhắm người già:** mặc định mọi công thức loại nguồn có mốc tuổi già (*ví dụ Nhật: 60代 / 老後 / シニア*). Bật `cho_phep_tep_gia` thì riêng kênh đó không loại theo tuổi, lời nhắc lọc ngách được báo đây là đúng tệp, và phán quyết ngách đối thủ dùng kho riêng của kênh. Muốn loại chủ đề khác (sức khoẻ, tiền hưu…) thì viết vào `luat_chon`, không thêm từ khoá. Tệp khán giả mới: thêm một dòng vào `tep_khan_gia` trong ngach.yaml (có `ma` và `ma_tuyen`), không phải sửa mã.

**Bật `chien_luoc` cho một kênh:** mỗi lần thử **1 kênh**; log lượt sau phải có `đang dùng chiến lược VPH 80% + V7 20% …` (lượt thăm dò ghi thêm `lượt THĂM DÒ`). Công thức kênh chưa dùng được tự bị bỏ, có log. Tắt bằng cách xoá dòng.

- Trộn theo **thứ hạng**, không so điểm giữa công thức. Video nhiều công thức cùng chọn chỉ xuất hiện một lần, mang nhãn "cũng được X chọn".
- Thăm dò **tất định** (cùng kênh/ngày/số lượt → cùng bảng); đưa công thức ít video nhất trong 14 ngày lên trước; kênh mới ưu tiên **cụm chưa làm lần nào**; không có nguồn qua cổng chất lượng thì lùi ngay về bảng khai thác.

## 4. Đọc `nghien-cuu/chien-luoc.json`

Ghi mỗi lượt, không tốn tiền, cửa sổ 28 ngày:

| trường | nghĩa |
|---|---|
| `thong_ke.<ct>.lam` | số video công thức này đã ra |
| `.n` / `.thang` / `.truot` / `.cho` | đã có kết luận / thắng / trượt / chưa đủ 48h |
| `.ctr_trang_chu_tv`, `.avd_giay_tv`, `.sub_1k` | trung vị CTR trang chủ @48h, thời lượng xem (giây), sub trên 1.000 view |
| `nguong_thang_48h` | ngưỡng thắng của chính kênh lúc ghi |
| `ti_trong_hien_tai` → `ti_trong_goi_y`, `ly_do_goi_y` | tỉ trọng đang dùng và tỉ trọng vòng học **gợi ý** (chưa áp, `da_ap: false`) |
| `thong_ke_toan_bo` | như `thong_ke` nhưng tính trên toàn bộ sổ |

Sổ cũ trước bộ máy chiến lược cũng được thống kê ngược qua nhãn `run.nguon.nguon`.

## 5. Khi nào bật tự học

Chỉ khi đủ **cả ba**: đã khai ≥ 2 công thức; tổng n ≥ 6 (nên mỗi công thức ≥ 3 kết luận); `ti_trong_goi_y` ổn định qua ≥ 2 lần ghi. Tỉ trọng nhân (thắng+1)/(n+2), kẹp 10–90%, nên không công thức nào tắt hẳn; thăm dò vẫn giữ.

## 6. Bài học và tiên nghiệm nhóm

- **Phạm vi:** kênh > nhóm > ngoài. Bài nhóm chỉ vào lời nhắc khi kênh có < 3 video trên trục đó; bài từ VPS khác chỉ khi kênh chưa có số; bài n < 3 chỉ để người đọc.
- **Tiên nghiệm nhóm giảm dần:** điểm mượn của kênh anh em = 0,35 × 2/(2 + n48); kênh có ≥ 6 video riêng đủ 48h thì tắt hẳn phần mượn — từ đó kênh tự tối ưu bằng số của chính mình.

## 7. (Người viết mã) Thêm một công thức

1. Chép `core/chien_luoc/_mau.py` thành `core/chien_luoc/<ten>.py` (không bắt đầu bằng `_`; tự được phát hiện).
2. Điền `TEN`, `MO_TA`, `LUI_KHI_RONG`.
3. Viết `ap_dung(nc) -> 0..1` (0 khi thiếu dữ liệu) và `cham(nc) -> list[dòng chuẩn]` (mạnh nhất trước, kết bằng `return nc.loc(ds)`).
4. Viết 1 test fixture: `tests/du-lieu/chien-luoc/<ten>.json`, hoặc một bài trong `tests/test_chien_luoc.py`.

Luật: không `import core.tu_chay` ở đầu tệp; `cham` không gọi mạng, không tốn ví; phân loại theo nghĩa (`nc.cum_cua`, `nc.luat_chon`), **không** thêm bộ lọc từ khoá. Hợp đồng đầy đủ của `NguCanh`: docstring `core/chien_luoc/ngu_canh.py`.

Kiểm: `tests/test_chien_luoc_golden.py` so đầu ra khi **không** khai `chien_luoc` với bản chụp, khớp từng byte (muốn chụp lại có chủ ý: xoá `.golden.json` rồi ghi lý do vào nhật ký); `tests/test_chien_luoc.py` kiểm phần trộn và thăm dò. Trên VPS **không** chạy test toàn kho.
