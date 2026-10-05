# Danh mục skill

Sinh tự động từ `core/ky_nang.py` (`python -m core.ky_nang md`) — sửa ở mã, không sửa tay.

Xem theo kênh: `python -m core.ky_nang xem` · skill khởi tạo còn thiếu: `python -m core.ky_nang thieu <kênh>`.

## KHỞI TẠO — một lần mỗi kênh (chạy theo thứ tự)

| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước |
|---|---|---|---|---|
| K01 | Chrome kênh đã đăng nhập | Chrome Portable riêng của kênh đã đăng nhập Google/YouTube; đọc lại bằng kiểm DOM (UC kênh). | `nguoi: đăng nhập Chrome · rồi python vm/may_dang_dom.py --kenh K --kiem-dom` | nguoi:dang_nhap_chrome |
| K02 | Tài khoản kênh (kho bí mật) | Email/mật khẩu/2FA cất mã hoá DPAPI ở bi-mat/ (không lên git). | `nguoi: điền dữ liệu ban đầu` | nguoi:du_lieu_ban_dau |
| K03 | Ngách + tuyến + tệp khán giả | ngach.yaml, nhóm/tệp trong kenh.yaml, tuyến nội dung. | `python -m core.khoi_tao_ngach --chu-de "…" --quoc-gia QG --ngon-ngu NN --ma-kenh K` | K01 |
| K04 | Giọng đọc | voice_id của nhà cung cấp giọng, lấy từ kho giọng (kho-giong.json). | `nguoi: điền voice_id trong kenh.yaml (nhóm có kho-giong.json thì mo_kenh chuan-bi tự gán)` | — |
| K05 | Nhân vật tham chiếu | Ảnh nv/ — mọi ảnh cảnh và bìa vẽ đúng nhân vật này. | `core.thiet_lap_kenh (ảnh ShopAPI)` | — |
| K06 | Ngôn ngữ hiển thị + địa điểm | youtube.com → menu avatar → Ngôn ngữ/Địa điểm = nước kênh; đọc lại menu. | `python vm/thiet_lap_kenh_dom.py --kenh K --ngon-ngu` | K01 |
| K07 | Tên kênh | Studio → Tuỳ chỉnh → tên; đọc lại trang công khai. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K01, K06 |
| K08 | Handle | @handle theo tên kênh; YouTube giới hạn đổi 14 ngày. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K07 |
| K09 | Mô tả + từ khoá + quốc gia | SEO kênh, quốc gia cư trú = nước kênh. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K06 |
| K10 | Logo | Ảnh ShopAPI theo hồ sơ; đọc lại trang công khai. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K05 |
| K11 | Banner | Ảnh ShopAPI theo hồ sơ. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K05 |
| K12 | Hình mờ | Watermark kênh. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K10 |
| K13 | Mặc định tải lên (Giáo dục) | Danh mục Giáo dục + ngôn ngữ video/mô tả mặc định. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K06 |
| K14 | Danh sách phát | Tạo các danh sách phát theo cụm nội dung (danh_sach_phat_kenh). | `python vm/thiet_lap_kenh_dom.py --kenh K` | K03 |
| K15 | Bật tự đăng trên máy | may-ao.json: tu_dang=true, cach_dang=tu_dong. | `core.trung_tam.them_kenh_vao_vm` | K01 |
| K16 | Danh bạ đối thủ | Nghiên cứu nhóm: chấm hộp thư → doi-thu.csv. | `python tu_chay.py --kenh K (bước 1)` | K03 |
| K17 | Nuôi trang chủ | Xem video thắng của đối thủ + Không quan tâm lạc đề tới khi trang chủ >90% chủ đề. | `kenh.yaml nuoi_trang_chu: true (agent tự chạy)` | K06 |
| K18 | OAuth client (dùng chung) | Tệp client Google Cloud (đã xuất bản) ở vm/clients/ — mở đường API bình luận. | `nguoi: tạo OAuth client một lần` | nguoi:google_cloud |
| K19 | Token bình luận (API) | Đồng ý một lần trong Chrome kênh → vm/tokens/<K>.json. Không có thì bình luận chạy DOM. | `python vm/setup_oauth.py --kenh K` | K18, K01 |

## ĐỊNH KỲ — mỗi ngày

| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước |
|---|---|---|---|---|
| D01 | Quét ngày | Studio + trang chủ + lời thoại → số liệu học (agent, sau 05:00). | `agent (tự)` | K01 |
| D02 | Sản xuất + bàn giao video ngày mai | Nghiên cứu → chọn nguồn → 8 khâu → QA → bàn giao lịch 05:00. | `tu_chay.py (điều phối)` | K03, K04, K05 |
| D03 | Bình luận (mồi + trả lời) | Phiên kênh, DOM: đăng mồi + trả lời bình luận mới — đúng NỘI DUNG video (lời thoại từ phụ đề gói), giọng kênh, đúng ngôn ngữ kênh, gõ như người (không emoji/kaomoji). | `agent phiên kênh · thử không đăng: workspace/cong-cu-dieu-phoi/thu_tra_loi.py` | K01 |
| D04 | Vòng tự học | Bảng điểm cụm/công thức/bìa/tiêu đề/hook theo số Studio. | `tu_chay.py (bước 0)` | D01 |
| D05 | Bộ não | Phiên 04:10: chấm dự đoán, quyết định ≤3 hành động, ghi nhớ. | `ShopAPI-Nao` | — |
| D06 | Bù màn hình kết thúc | Video thiếu MHKT → bù giờ vắng 02:00–05:00. | `agent --bu-mhkt` | K01 |
| D07 | Đường tới YPP | Dự báo ngày đủ 4000 giờ + 1000 đăng ký từ chỉ số Studio hằng ngày (cận dưới theo cửa sổ 28 ngày); cảnh báo khi gần/đạt. | `python -m core.ypp · --canh-bao` | D01 |

## SỬA CHỮA — khi hỏng

| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước |
|---|---|---|---|---|
| S01 | Trả ngôn ngữ giao diện | Máy DOM tạm vi chưa trả (chết giữa chừng) → lần chạy sau tự trả. | `tự (ngon_ngu_tam.tra)` | — |
