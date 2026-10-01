# Kênh và ngách

Tài liệu này nói về 5 việc: ngách mới bằng AI, thêm kênh, hồ sơ ngách (đổi chủ đề/quốc gia bằng tay), và chia sẻ bài học giữa các VPS.
Bộ máy chọn nguồn (công thức, thăm dò, tự học) có tài liệu riêng: `docs/kien-thuc/chien-luoc.md`.

## 1. Một kênh gồm gì
```
CHANNEL/<MÃ>/            thư mục kênh thật: ở lại máy, không lên kho
  kenh.yaml              tiếng, giọng (voice_id), độ dài, nhóm, công tắc tự chạy, ngân sách
  style.yaml             nét vẽ, màu, bối cảnh
  nv/nv1.png             nhân vật tham chiếu cho mọi cảnh
  prompt/                lời nhắc từng bước: 1-tieu-de, 2-viet, 2b-cham… 3-sua, 6-seo, 7-ke-hoach, 7-canh, 8-thumbnail, 9-nhac
  may-ao.json            thiết lập máy đăng/bình luận của kênh (xem docs/DANG-VA-BINH-LUAN.md)
  CLAUDE.md, NHAT-KY-KENH.md   luật và lịch sử riêng kênh (thắng mọi phân tích chung)
```
Thiếu tệp lời nhắc nào thì bước đó tự bỏ qua. Muốn đổi lời nhắc thì sửa thẳng các tệp trong `prompt/`.

Hai con số hay sai:
- `ky_tu_moi_phut` là số ký tự giọng đọc đọc được mỗi phút. Nó quyết định độ dài kịch bản. Tham khảo: tiếng Nhật 341, tiếng Việt 832, tiếng Anh 920. Đổi giọng thì phải đo lại: lấy số ký tự kịch bản chia cho số phút của `2-giong-doc.mp3`.
- `chu_bia_hoa` phải để `false` với tiếng Nhật và tiếng Hàn.

Không bao giờ đặt khoá API vào thư mục kênh. Tool thấy chuỗi giống khoá trong đó sẽ báo đỏ và không chạy.

## 2. Ngách mới bằng AI — VPS mới, chủ đề mới, quốc gia mới
Chỉ cần chủ đề + quốc gia + ngôn ngữ (thêm 1–3 kênh mẫu hoặc từ khoá nếu có):
```
python -m core.khoi_tao_ngach --chu-de "nấu ăn tại gia" --quoc-gia VN --ngon-ngu vi --thu
python -m core.khoi_tao_ngach --chu-de "nấu ăn tại gia" --quoc-gia VN --ngon-ngu vi --kenh-mau <link> --tu-khoa "<cụm>"
```
Giao diện: **Số liệu kênh → Thêm kênh → "Ngách mới bằng AI"** (chọn kênh có sẵn trong ô "Cho kênh" = đổi chủ đề kênh đó).
`--thu` không gọi AI, không gọi mạng, không ghi gì: chỉ in kế hoạch.

Lệnh làm bốn việc, chạy lại an toàn (đã có thì dùng lại, câu trả lời AI có nhớ đệm ở `_NHOM/<nhóm>/khoi-tao/`):
1. **Hồ sơ ngách** `CHANNEL/_NHOM/<chủ-đề>-<qg>/ngach.yaml`: AI đọc khung `_KHUON/ngach-mau.yaml` và ví dụ tâm lý Nhật rồi viết
   mô tả ngách theo nghĩa, tệp khán giả, cụm, luật chọn, tiêu chí đối thủ, thị trường (múi giờ, giờ đăng gợi ý, bậc làm tròn view),
   chuẩn bìa ước lượng, cụm tìm kiếm. Viết lại: thêm `--lam-lai-ngach`.
2. **Kênh** `CHANNEL/<MÃ>/` từ khuôn `_KHUON/kenh-mau/` (cấu hình sản xuất đã chứng minh). Mã kênh: `--ma-kenh`, không thì theo
   thư mục trình duyệt `<MÃ>\<MÃ>.exe` cạnh MyTool, không nữa thì `K1`. AI viết lại theo mục tiêu (không dịch máy) các lời
   nhắc còn mang ngách cũ — `2d-hook`, `2e-cham-hook`, `6-seo`, `8-thumbnail`, `9-nhac` — và 8 khoá văn hoá/bìa của `style.yaml`;
   lời nhắc chung giữ nguyên. Bản viết lại mất chỗ điền `<<…>>` hay định dạng trả về thì giữ bản khuôn. Tạo ảnh nhân vật
   (1 ảnh), gieo sổ tuyến + Công thức V7, đưa kênh vào máy đăng nếu đã thấy trình duyệt.
3. **Nghiên cứu khởi động:** tìm YouTube theo `tu_khoa_tim` + kênh mẫu → hộp thư đối thủ → chuỗi Một nút có ví (chốt đối thủ,
   kiểm ngách theo nghĩa bằng LLM, quét content = kho nguồn). Từ hôm sau, phiên quét ngày tự tìm thêm bằng chính Chrome kênh
   (trạm giao 3 cụm/ngày qua `/tim-kiem/can-tim`).
4. **Giai đoạn:** `chien_luoc: "tu_dong"` — kênh mới chọn nguồn bằng VPH + lượt thăm dò; có video thắng thật thì tự sang V7.

Công tắc tiền và tự động để TẮT. Việc của người (giọng đọc, đăng nhập Chrome kênh, bật `ngan_sach_ngay`/`tu_chay`) ghi ở
`CHANNEL/<MÃ>/KHOI-TAO.md`. Trước khi cho tiêu tiền: `python tu_chay.py --kenh <mã> --thu`.

## 3. Thêm kênh bằng tay (6 bước)
1. **Tạo:** vào trang **Số liệu kênh**, bấm **Thêm kênh**, chọn "Tạo kênh mới từ một kênh mẫu".
   - Chọn kênh mẫu để chép prompt, style và nhân vật. Kênh gốc không bị đổi.
   - Đặt **mã kênh**: viết liền, không dấu, ví dụ `TL5-T7`. Mã này cũng là tên thư mục trình duyệt.

   Kênh mới được tạo ở `CHANNEL/<mã>/` với `kenh_rieng: true`, nên cập nhật tool không bao giờ ghi đè nó.
2. **Trình duyệt:** mỗi kênh có một Chrome portable riêng, đặt ở `<MÃ>\<MÃ>.exe`, cùng cấp với thư mục `MyTool\`.
   - Đóng hết trình duyệt kênh khác (luật IPv4/IPv6 trong `CLAUDE.md`).
   - Mở trình duyệt này bằng tay, đăng nhập YouTube, vào Studio một lần, rồi đóng lại.
   - Ở bước 2 của hộp thoại, chờ dòng "✓ Đã thấy trình duyệt của kênh". Không thấy thì bấm "Thư mục trình duyệt" để chỉ tay.
   - Tick **"Cho máy đăng lo kênh này"**. Không tick thì video làm xong sẽ không được đăng.
3. **Giọng đọc:** `voice_id` trong `kenh.yaml` phải khác mọi kênh khác trên máy. Nhiều kênh cùng giọng, cùng máy trông như "kênh trại" và hại khả năng bật YPP. Gác tổng sẽ báo khi hai kênh tự chạy dùng chung giọng.
4. **Đối thủ:** mỗi kênh một danh sách đối thủ riêng, lệch nhau trong cùng ngách. Thêm ở trang **Nghiên cứu**. Bản đồ tuyến nằm ở `CHANNEL/<k>/nghien-cuu/tuyen.csv`.
5. **Ngân sách:** đặt `ngan_sach_ngay` ít nhất bằng chi phí một video. Để `0` thì kênh không tự sản xuất. Giờ đăng tính theo giờ của VPS.
6. **Công tắc:**
   - "Cho kênh tự làm video mỗi ngày" (`tu_chay`).
   - "Tự đăng, không chờ duyệt" (`tu_duyet`). Nên để tắt ít nhất 7 ngày đầu và duyệt tay ở Bảng điều khiển.

   Trước khi cho tiêu tiền, chạy thử miễn phí: `python tu_chay.py --kenh <mã> --thu`.

Tắt tạm một kênh: bỏ `tu_chay`. Dữ liệu và trình duyệt vẫn giữ nguyên.

## 4. Hồ sơ ngách bằng tay: đổi chủ đề hoặc quốc gia
Ngách thuộc về **nhóm kênh**, không thuộc từng kênh. Kênh khai `nhom: "<tên-nhóm>"` và `tep: "<mã tệp khán giả>"` trong `kenh.yaml`. Hồ sơ của nhóm nằm ở `CHANNEL/_NHOM/<tên-nhóm>/ngach.yaml`, đọc qua `core/ho_so_ngach.py`. Kênh không có nhóm thì dùng mặc định trong mã (tâm lý × Nhật). Cách nhanh nhất: mục 2 (AI viết hồ sơ).

1. Chép một khuôn trong `CHANNEL/_KHUON/` thành `CHANNEL/_NHOM/<tên-nhóm>/ngach.yaml`:
   - `ngach-mau.yaml`: khuôn chung, có chú thích từng khoá;
   - `ngach-mau-vi.yaml`, `ngach-mau-en-us.yaml`: khung cho thị trường Việt Nam và Mỹ;
   - `ngach-mau-ja-tam-ly.yaml`: bản đầy đủ của nhóm tâm lý Nhật đang chạy. Tra khoá ở đây.
2. Viết trước 3 khoá "theo nghĩa" để AI đọc:
   - `mo_ta_ngach`: ngách là gì;
   - `mo_ta_cho_loc_ai`: cái gì đúng ngách, cái gì lệch;
   - `luat_chon`: các câu luật ngắn để chọn nguồn;
   - ngách không phải tâm lý Nhật: thêm `mau_tieu_de` riêng, `tieu_chi_doi_thu`, `luat_nan_khuon`, `tu_khoa_tim`,
     `the_loai_en` (xem `ngach-mau.yaml`) — mọi lời nhắc lọc/kiểm/gán/nắn tiêu đề/bìa dựng theo chúng.

   Không thêm danh sách từ khoá để lọc.
3. Điền `thi_truong`:
   - bắt buộc: `quoc_gia`, `ngon_ngu`, `mui_gio`, `bac_lam_tron_view`;
   - khi cần: `ctr_trang_chu_muc_tieu`;
   - thị trường nhỏ: `bac_view_manh`, `tran_vuot`.

   Tệp khán giả mới thì thêm một dòng vào `tep_khan_gia`.
4. Ghi tri thức chọn content của ngách vào `CHANNEL/_NHOM/<tên-nhóm>/INSIGHT-CHON-CONTENT.md`.
5. Sửa `prompt/` của từng kênh cho ngách mới. Đây là phần tốn công nhất: tiêu đề, khung viết, tiêu chí chấm, hook.
6. Kho nhạc (`PROJECTS/music`, chuẩn hoá bằng `python -m core.kho_nhac`) dùng chung cho mọi kênh. Ngách có không khí khác hẳn thì thêm nhạc vào kho.
7. Chạy thử `--thu`. Log phải có ứng viên, và tiêu đề đúng ngách.

Thứ tự ưu tiên khi một khoá được khai ở nhiều nơi: **kenh.yaml > ngach.yaml > mặc định trong mã**.
Chỉ `ngach.yaml` và `INSIGHT-CHON-CONTENT.md` được lên kho. Máy khác cùng ngách dùng chung hai tệp này. Các tệp khác trong `_NHOM/<nhóm>/` ở lại máy.
Phải sửa mã cho ngách mới thì sửa tổng quát: đọc giá trị từ `ngach.yaml`, không viết cứng tên ngách.

## 5. Chia sẻ bài học giữa các VPS
- **Xuất:** lệnh `python -m core.dong_bo_git bai_hoc` gom bài học phạm vi kênh có n ≥ 3 (`core.chien_luoc.bai_hoc`) vào `chia-se/bai-hoc/<ma_may>-<ngach>.json`. Lệnh này cũng tự chạy trong mỗi lần `day`.
  - Mỗi máy ghi tệp riêng của mình, nên push không xung đột.
  - Câu nào có tên kênh thật, video id, URL hoặc email thì bị bỏ.
- **Nhập:** khi máy tự cập nhật (`keo`), tệp của máy khác cùng ngách được chép vào `CHANNEL/_NHOM/<ngach>/bai-hoc-ngoai/`.
  - Đây là tiên nghiệm yếu nhất, chỉ dùng khi kênh chưa có số riêng trên trục đó.
  - Thứ tự tin: kênh > nhóm > ngoài.
- **Định dạng:** `{"ma_may", "ngach", "xuat_luc", "bai_hoc": [{"truc", "cum", "cau", "n", "dung_cho"}]}`.
