# Chiến lược chọn nguồn: hướng dẫn người vận hành

Tài liệu này dành cho người dựng VPS mới hoặc mở thêm ngách, không cần đọc mã. Mọi thay đổi ở đây chỉ là sửa tệp YAML. Chưa khai khoá mới nào thì tool vẫn chạy y như trước.

## 1. Vòng học trong 5 dòng

1. Mỗi lượt, **công thức** (VPH / V7 / Một nút / công thức bạn tự thêm) xếp hạng các video nguồn chưa làm.
2. **Biên tập viên AI** đọc bảng đó theo nghĩa, chấm TỐT / TẠM / TỆ, rồi chốt 1 nguồn.
3. Tool làm video, đăng, rồi đọc số Studio ở mốc 48h / 72h.
4. Mỗi video được ghi lại công thức đã chọn nó (`run.nguon.cong_thuc`). **Vòng học** đếm thắng / trượt theo từng công thức vào `nghien-cuu/chien-luoc.json`, và rút bài học vào `nghien-cuu/bai-hoc-*.json`.
5. Bài học quay lại bước 1–2: tiêu chí chấm của công thức, lời nhắc biên tập, và (nếu bạn bật) tỉ trọng giữa các công thức.

"Thắng" luôn đo theo **chính kênh**: hiển thị @48h ≥ max(ngưỡng tối thiểu, bội số × trung vị 48h của kênh). Không có con số cứng chung cho mọi kênh.

## 2. VPS mới / ngách mới / quốc gia mới

Làm theo thứ tự. Mỗi bước đều có thể hoàn tác bằng cách xoá dòng vừa thêm.

1. **Tạo nhóm ngách.** Chép một mẫu trong `CHANNEL/_KHUON/` thành `CHANNEL/_NHOM/<tên-nhóm>/ngach.yaml`:

   | mẫu | dùng khi |
   |---|---|
   | `ngach-mau.yaml` | ngách bất kỳ (ví dụ "nấu ăn tiếng Việt"); có chú thích từng khoá |
   | `ngach-mau-vi.yaml` / `ngach-mau-en-us.yaml` | khung theo thị trường Việt Nam / Mỹ |
   | `ngach-mau-ja-tam-ly.yaml` | bản đầy đủ của nhóm `tam-ly-nhat` đang chạy, tra cứu mọi khoá |

2. **Viết 3 khoá "theo nghĩa" trước tiên.** AI đọc 3 khoá này để chọn và lọc nguồn. Từ khoá trong tệp chỉ là đường lùi khi AI lỗi.
   - `mo_ta_ngach`: một câu nói ngách là gì.
   - `mo_ta_cho_loc_ai`: cái gì đúng ngách, cái gì lệch ngách.
   - `luat_chon`: danh sách câu ngắn, là luật chọn nguồn. Biên tập viên (đề bài gọn) và mọi lời nhắc chọn nguồn đọc qua `nc.luat_chon`.

   **Đừng thêm danh sách từ khoá để lọc nội dung.** Việc phân loại đã giao cho AI theo nghĩa.
3. **Thị trường** (khối `thi_truong:` trong ngach.yaml):
   - `quoc_gia`, `ngon_ngu`, `mui_gio`;
   - `bac_lam_tron_view`: bậc làm tròn lượt xem mà YouTube hiển thị ở thị trường đó;
   - `ctr_trang_chu_muc_tieu`, nếu muốn khác 5%.

   Thị trường nhỏ hơn Nhật thì khai thêm `bac_view_manh` (mặc định 100000) và `tran_vuot` (mặc định 25) cho bảng Một nút. Hai khoá này quyết định thế nào là một nguồn "đang nổ thật".
4. **Gắn kênh vào nhóm.** Trong `CHANNEL/<kênh>/kenh.yaml`, thêm `nhom: "<tên-nhóm>"` và `tep: "<mã tệp khán giả>"`. Cách tạo kênh, trình duyệt và giọng đọc xem `docs/THEM-KENH.md`.
5. **Chạy thử miễn phí.** Chạy một lượt ở chế độ "thu" (không tốn ví), rồi đọc log chọn nguồn:
   - dòng `đang dùng công thức …` cho biết công thức nào đang chạy;
   - phải có ứng viên, và tiêu đề phải đúng ngách.

Thứ tự ưu tiên khi cùng một khoá được khai ở nhiều nơi: **kenh.yaml > ngach.yaml > mặc định trong mã**. Nhờ vậy mỗi kênh vẫn tự cá nhân hoá được trong nhóm.

## 3. Các khoá kenh.yaml của bộ máy chọn nguồn

| khoá | mặc định | tác dụng |
|---|---|---|
| `cong_thuc_chon` | `tu_dong` | luật cũ, 1 công thức: `v7` / `vph` / `mot_nut` / `<tên công thức mới>`. `tu_dong` = V7 khi kênh đã có video thắng thật, còn lại VPH |
| `chien_luoc` | *(không khai)* | trộn nhiều công thức, ví dụ `"vph:0.8, v7:0.2"`, hoặc `"tu_dong"` (tự chia theo giai đoạn kênh). Không khai = dùng `cong_thuc_chon` |
| `chien_luoc_tham_do` | `20` | % lượt thăm dò khi có ≥ 2 công thức |
| `chien_luoc_tu_hoc` | `false` | `true` = tự dồn tỉ trọng theo thắng / trượt thật (xem mục 5) |
| `de_bai_bien_tap` | *(không khai)* | `"gon"` = đề bài biên tập gọn: MỤC TIÊU 3 dòng, luật ngách từ `luat_chon`, bài học của kênh. Không khai = đề bài cũ |
| `luat_chon` | lấy từ ngach.yaml | luật chọn riêng của kênh, đè lên luật nhóm |
| `bac_view_manh`, `tran_vuot` | 100000, 25 | ngưỡng của bảng Một nút theo cỡ thị trường |
| `ypp_sub`, `ypp_gio`, `da_kiem_tien` | *(không khai)* | số sub và giờ xem trọn đời để viết dòng mục tiêu YPP. Số tự đọc được từ Studio chỉ là số 28 ngày |
| `bien_tap_ai`, `phan_cum_ai` | `true` | tắt biên tập viên AI / phân cụm AI (chỉ dùng khi gỡ lỗi) |
| `cho_phep_tep_gia` | `false` | `true` = kênh nhắm tệp **người già** (65+): tắt cổng tuổi, xem mục dưới |

### Kênh nhắm người già: `cho_phep_tep_gia: true`

Mặc định, mọi công thức loại nguồn có mốc tuổi (60代 / 老後 / シニア…), vì 4 kênh đầu nhắm người 25–62. Kênh nhắm chính người già thì khai `cho_phep_tep_gia: true` trong kenh.yaml. Khi bật, **chỉ riêng kênh đó**:
- VPH, V7 (cả nhãn AI "nhắm người lớn tuổi"), Một nút và luật cứng gán tuyến không loại nguồn chỉ vì mốc tuổi.
- Lời nhắc lọc ngách (trang chủ, kiểm ngách đối thủ, chốt danh bạ) được báo rằng nhắm người già là đúng tệp, kèm `luat_chon` của kênh.
- Phán quyết ngách của kênh đối thủ dùng kho **riêng** `CHANNEL/<kênh>/nghien-cuu/kenh-ai.json`, không dùng kho chung của nhóm. Kho nhóm phán theo tệp của các kênh kia.

Khoá này không tắt từ loại trừ thể loại (漫画, 雑学…). Muốn loại sức khoẻ, tiền hưu hay truyện đọc thì viết vào `luat_chon` của kênh; AI đọc theo nghĩa. Đừng thêm danh sách từ khoá.

Tệp mới của nhóm thì thêm một dòng vào `tep_khan_gia` trong ngach.yaml, có `ma_tuyen` là mã tuyến (vd. `ma: '7'`, `ma_tuyen: nguoi-cao-tuoi-dang-song-tuoi-gia`). `ma_tep('7')` tự nhận mã mới, không phải sửa mã.

### Bật `chien_luoc` cho một kênh

1. Mỗi lần chỉ thử **1 kênh**, ví dụ thêm `chien_luoc: "vph:0.8, v7:0.2"` vào kenh.yaml của TL2.
2. Log lượt sau phải có dòng:

   ```
   đang dùng chiến lược VPH 80% + V7 20% (kenh.yaml chien_luoc: …)
   ```

   Lượt thăm dò thì dòng này ghi thêm `— lượt THĂM DÒ: bảng … đứng trước`.
3. Công thức nào kênh chưa dùng được sẽ tự bị bỏ và có log ghi rõ. Ví dụ: V7 khi kênh chưa có video thắng thật.
4. Tắt bằng cách xoá dòng vừa thêm. Lượt sau chạy lại luật cũ y hệt trước.

Cách trộn:
- Xếp theo **thứ hạng**, không so điểm giữa các công thức, vì mỗi công thức có thang điểm riêng.
- Video được nhiều công thức cùng chọn chỉ xuất hiện một lần, mang nhãn "cũng được X chọn" (`tin_hieu.cong_thuc_khac`).

Cách thăm dò:
- Tất định: cùng kênh, cùng ngày, cùng số lượt thì ra cùng bảng. Trạm lấy lời thoại và vòng chọn nguồn nhờ vậy luôn thấy cùng một bảng.
- Lượt thăm dò đưa bảng của công thức **ra ít video nhất trong 14 ngày** lên trước.
- Kênh mới (chưa qua ngưỡng V7): trong bảng thăm dò, video thuộc **cụm chủ đề kênh chưa làm lần nào** được đưa lên trước (`tin_hieu.cum_chua_thu`).
- Lượt thăm dò không có nguồn nào qua cổng chất lượng thì lùi ngay về bảng khai thác, không mất ngày.

## 4. Đọc `CHANNEL/<kênh>/nghien-cuu/chien-luoc.json`

Vòng học ghi tệp này mỗi lượt, không tốn tiền, dùng cửa sổ 28 ngày:

| trường | nghĩa |
|---|---|
| `thong_ke.<công thức>.lam` | số video công thức này đã ra |
| `.n` / `.thang` / `.truot` / `.cho` | số video đã có kết luận / thắng / trượt / chưa đủ 48h |
| `.ctr_trang_chu_tv`, `.avd_giay_tv`, `.sub_1k` | trung vị CTR trang chủ @48h, trung vị thời lượng xem (giây), sub trên 1.000 view |
| `nguong_thang_48h` | ngưỡng thắng của chính kênh lúc ghi |
| `ti_trong_hien_tai` → `ti_trong_goi_y`, `ly_do_goi_y` | tỉ trọng đang dùng, và tỉ trọng vòng học **gợi ý** (chưa áp, `da_ap: false`) |
| `thong_ke_toan_bo` | như `thong_ke` nhưng tính trên toàn bộ sổ |

Sổ cũ trước bộ máy chiến lược cũng được thống kê ngược, qua nhãn `run.nguon.nguon`.

## 5. Khi nào bật `chien_luoc_tu_hoc: true`

Chỉ bật khi đủ **cả ba** điều kiện:
- kênh đã khai `chien_luoc` với ≥ 2 công thức;
- `chien-luoc.json` có **tổng `n` ≥ 6**, và nên có mỗi công thức ≥ 3 kết luận (dưới 6 thì mã tự bỏ qua, chỉ ghi gợi ý);
- `ti_trong_goi_y` đã **ổn định qua ≥ 2 lần ghi** (không đảo chiều mỗi ngày).

Khi bật, tỉ trọng được nhân với (thắng + 1) / (n + 2), kẹp trong khoảng 10–90%, nên không công thức nào bị tắt hẳn. Phần thăm dò (`chien_luoc_tham_do`) vẫn giữ để công thức yếu còn cơ hội chứng minh lại. Muốn quay về tỉ trọng tay thì đặt lại `false`.

## 6. Bài học và tiên nghiệm nhóm

- **Phạm vi bài học:** kênh > nhóm > ngoài.
  - Bài học nhóm chỉ vào lời nhắc khi kênh có < 3 video trên đúng trục đó.
  - Bài học từ VPS khác ("ngoài") chỉ vào khi kênh chưa có số nào.
  - Bài học có n < 3 chỉ ghi cho người đọc, không vào lời nhắc.
- **Tiên nghiệm nhóm giảm dần** (`cong_thuc_v7.he_so_tien_nghiem`, tham số `thua_huong_nhom` trong `cong-thuc-v7.json`):
  - Điểm cụm V7 mượn của kênh anh em và điểm anh em của bảng Một nút dùng **cùng một hàm**: 0,35 × 2/(2 + n48), với n48 là số video riêng của kênh đã đủ 48h.
  - Kênh có ≥ 6 video riêng đủ 48h thì tắt hẳn phần mượn nhóm. Từ đó kênh tự tối ưu bằng số của chính mình.

## 7. (Cho người viết mã) Thêm một công thức

1. Chép `core/chien_luoc/_mau.py` thành `core/chien_luoc/<ten>.py`. Tên tệp không bắt đầu bằng `_`, và tool tự phát hiện tệp mới.
2. Điền `TEN`, `MO_TA`, và `LUI_KHI_RONG` (tên công thức lùi về khi bảng rỗng; `""` là không lùi).
3. Viết hai hàm:
   - `ap_dung(nc) -> 0..1`: trả 0 khi thiếu dữ liệu.
   - `cham(nc) -> list[dòng chuẩn]`: mạnh nhất đứng trước, kết thúc bằng `return nc.loc(ds)`.
4. Viết 1 test fixture: tệp `tests/du-lieu/chien-luoc/<ten>.json`, hoặc một bài trong `tests/test_chien_luoc.py`.

Luật:
- Không `import core.tu_chay` ở đầu tệp.
- `cham` không gọi mạng, không tốn ví.
- Phân loại nội dung theo nghĩa, dùng `nc.cum_cua(tieu_de)` (nhãn AI trước) và `nc.luat_chon`. **Không** thêm bộ lọc từ khoá.

Dòng chuẩn gồm:
- `nguon` (= TEN), `ma`, `link`, `tieu_de`, `kenh` (kênh nguồn), `diem` (thang điểm riêng của công thức);
- tuỳ công thức: `loai`, `view`, `vph`, `dot_bien`, `tuoi_gio`, `cum`, `tuyen`, `ly_do[]`;
- khi trộn, bộ điều phối gắn thêm `cong_thuc`, `tham_do`, `tin_hieu{cong_thuc_khac, cum_chua_thu}`.

Hợp đồng đầy đủ của `NguCanh` nằm trong docstring `core/chien_luoc/ngu_canh.py`.

**Kiểm:**
- `tests/test_chien_luoc_golden.py` so đầu ra khi **không** khai `chien_luoc` với bản chụp, khớp từng byte. Muốn chụp lại có chủ ý: xoá `.golden.json` rồi ghi lý do vào nhật ký.
- `tests/test_chien_luoc.py` kiểm phần trộn và thăm dò.
- Trên VPS, **không** chạy `pytest tests/` toàn kho.
