# Danh mục skill

Sinh tự động từ `core/ky_nang.py` (`python -m core.ky_nang md`) — sửa ở mã, không sửa tay.

Xem theo kênh: `python -m core.ky_nang xem` · skill khởi tạo còn thiếu: `python -m core.ky_nang thieu <kênh>`.

## Tự kích hoạt

Bộ chạy `python -X utf8 -m core.ky_nang tu-kich-hoat [--thu]` (`core/ky_nang_tu.py`), tác vụ Windows `ShopAPI-KyNang` mỗi giờ phút :35 — chủ tự đăng ký (`python -m core.ky_nang lich` in đúng đường của máy):

```
schtasks /Create /TN ShopAPI-KyNang /SC HOURLY /MO 1 /ST 00:35 /F /TR "cmd /c cd /d \"<MyTool>\" && \"<pythonw.exe>\" -X utf8 -m core.ky_nang tu-kich-hoat"
```

Luật (mỗi luật một câu):

1. Mỗi lượt quét kênh máy này quản lý × skill có `dieu_kien`; skill `toan_may` quét một lần.
2. Chạy khi điều kiện đúng, `tu_ap`, công tắc chung bật (`workspace/cai-dat.json: ky_nang_tu_kich_hoat`), kênh không tắt skill (`kenh.yaml: ky_nang_tat: [mã, …]`), đã qua `nhip_gio` kể từ lần chạy cuối và không đang tạm dừng.
3. Việc nhẹ chạy hết; việc NẶNG (DOM / sản xuất) tối đa MỘT mỗi lượt và chỉ khi khoá máy `.khoa-may` rảnh, không ai xếp hàng — bận thì để lượt sau, không bao giờ ép.
4. Không chạy trong phút :55–:05.
5. Mã thoát 0/30 = xong, 10/4 = hoãn (không tính), còn lại hay quá giờ = hỏng; xong mà điều kiện vẫn đúng với CÙNG lệnh = chưa đạt (tính hỏng).
6. Hỏng 3 lần liền → tạm dừng skill đó ở kênh đó 24 giờ, báo Việc của bạn + báo động.
7. `tu_ap=False` chỉ báo «nên chạy» (bảng 8790 + báo cáo ngày), không bao giờ tự chạy.
8. Mọi kết quả, và mọi quyết định khác lần ghi trước, vào `workspace/ky-nang/so-chay.jsonl` + một sự kiện não bộ phận.

## KHỞI TẠO — một lần mỗi kênh (chạy theo thứ tự)

| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước | Tự kích hoạt |
|---|---|---|---|---|---|
| K01 | Chrome kênh đã đăng nhập | Chrome Portable riêng của kênh đã đăng nhập Google/YouTube; đọc lại bằng kiểm DOM (UC kênh). | `nguoi: đăng nhập Chrome · rồi python vm/may_dang_dom.py --kenh K --kiem-dom` | nguoi:dang_nhap_chrome | — |
| K02 | Tài khoản kênh (kho bí mật) | Email/mật khẩu/2FA cất mã hoá DPAPI ở bi-mat/ (không lên git). | `nguoi: điền dữ liệu ban đầu` | nguoi:du_lieu_ban_dau | — |
| K03 | Ngách + tuyến + tệp khán giả | ngach.yaml, nhóm/tệp trong kenh.yaml, tuyến nội dung. | `python -m core.khoi_tao_ngach --chu-de "…" --quoc-gia QG --ngon-ngu NN --ma-kenh K` | K01 | — |
| K04 | Giọng đọc | voice_id của nhà cung cấp giọng, lấy từ kho giọng (kho-giong.json). | `nguoi: điền voice_id trong kenh.yaml (nhóm có kho-giong.json thì mo_kenh chuan-bi tự gán)` | — | — |
| K05 | Nhân vật tham chiếu | Ảnh nv/ — mọi ảnh cảnh và bìa vẽ đúng nhân vật này. | `core.thiet_lap_kenh (ảnh ShopAPI)` | — | — |
| K06 | Ngôn ngữ hiển thị + địa điểm | youtube.com → menu avatar → Ngôn ngữ/Địa điểm = nước kênh; đọc lại menu. | `python vm/thiet_lap_kenh_dom.py --kenh K --ngon-ngu` | K01 | — |
| K07 | Tên kênh | Studio → Tuỳ chỉnh → tên; đọc lại trang công khai. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K01, K06 | — |
| K08 | Handle | @handle theo tên kênh; YouTube giới hạn đổi 14 ngày. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K07 | — |
| K09 | Mô tả + từ khoá + quốc gia | SEO kênh, quốc gia cư trú = nước kênh. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K06 | — |
| K10 | Logo | Ảnh ShopAPI theo hồ sơ; đọc lại trang công khai. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K05 | — |
| K11 | Banner | Ảnh ShopAPI theo hồ sơ. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K05 | — |
| K12 | Hình mờ | Watermark kênh. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K10 | — |
| K13 | Mặc định tải lên (Giáo dục) | Danh mục Giáo dục + ngôn ngữ video/mô tả mặc định. | `python vm/thiet_lap_kenh_dom.py --kenh K` | K06 | — |
| K14 | Danh sách phát | Tạo các danh sách phát theo cụm nội dung (danh_sach_phat_kenh). | `python vm/thiet_lap_kenh_dom.py --kenh K` | K03 | — |
| K15 | Bật tự đăng trên máy | may-ao.json: tu_dang=true, cach_dang=tu_dong. | `core.trung_tam.them_kenh_vao_vm` | K01 | — |
| K16 | Danh bạ đối thủ | Nghiên cứu nhóm: chấm hộp thư → doi-thu.csv. | `python tu_chay.py --kenh K (bước 1)` | K03 | — |
| K17 | Nuôi trang chủ | Xem video thắng của đối thủ + Không quan tâm lạc đề tới khi trang chủ >90% chủ đề. | `kenh.yaml nuoi_trang_chu: true (agent tự chạy)` | K06 | — |
| K18 | OAuth client (dùng chung) | Tệp client Google Cloud (đã xuất bản) ở vm/clients/ — mở đường API bình luận. | `nguoi: tạo OAuth client một lần` | nguoi:google_cloud | — |
| K19 | Token bình luận (API) | Đồng ý một lần trong Chrome kênh → vm/tokens/<K>.json. Không có thì bình luận chạy DOM. | `python vm/setup_oauth.py --kenh K` | K18, K01 | — |
| K20 | Trang chủ + video giới thiệu | Kích hoạt: kết quả kiểm thương hiệu thấy thẻ Trang chủ tắt / chưa có video giới thiệu; hằng tháng video thắng nhất (luật của chế độ: dài, ≥ 7 ngày, hiển thị × tỷ lệ bấm, công khai) đổi → đặt lại. Đọc lại sau Xuất bản (chủ duyệt 14/10). | `python vm/thiet_lap_kenh_dom.py --kenh K --dat-trang-chu` | D09 | tự chạy · nhịp 24 giờ · nặng (khoá máy) |

## ĐỊNH KỲ — mỗi ngày

| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước | Tự kích hoạt |
|---|---|---|---|---|---|
| D01 | Quét ngày | Studio + trang chủ + lời thoại → số liệu học (agent, sau 05:00). | `agent (tự)` | K01 | — |
| D02 | Sản xuất + bàn giao video ngày mai | Nghiên cứu → chọn nguồn → 8 khâu → QA → bàn giao lịch 05:00. | `tu_chay.py (điều phối)` | K03, K04, K05 | — |
| D03 | Bình luận (mồi + trả lời) | Phiên kênh, DOM: đăng mồi + trả lời bình luận mới — đúng NỘI DUNG video (lời thoại từ phụ đề gói), giọng kênh, đúng ngôn ngữ kênh, gõ như người (không emoji/kaomoji). | `agent phiên kênh · thử không đăng: workspace/cong-cu-dieu-phoi/thu_tra_loi.py` | K01 | — |
| D04 | Vòng tự học | Bảng điểm cụm/công thức/bìa/tiêu đề/hook theo số Studio. | `tu_chay.py (bước 0)` | D01 | — |
| D05 | Bộ não | Phiên sáng (06:45, đợi quét Studio xong): chấm dự đoán, chương trình 6 việc, ghi nhớ. | `ShopAPI-Nao` | — | — |
| D06 | Bù màn hình kết thúc | Video thiếu MHKT → bù giờ vắng 02:00–05:00. | `agent --bu-mhkt` | K01 | — |
| D07 | Đường tới YPP | Dự báo ngày đủ 4000 giờ + 1000 đăng ký từ chỉ số Studio hằng ngày (cận dưới theo cửa sổ 28 ngày); cảnh báo khi gần/đạt. | `python -m core.ypp · --canh-bao` | D01 | — |
| D08 | Kéo view chéo | Kênh lớn thêm video kênh em vào danh sách phát (playlist tự học từ hộp Lưu, AI chọn theo nghĩa); mỗi lần thêm có dự đoán, đo sau 7 ngày. | `python vm/keo_cheo_dom.py --ke-hoach (agent tự chạy 1 lần/ngày)` | D01 | — |
| D09 | Thương hiệu kênh (hình mờ) | Kích hoạt: chưa có kết quả kiểm thương hiệu hoặc cũ > 30 ngày → kiểm (CHỈ ĐỌC hình mờ, trailer, video nổi bật); kiểm thấy THIẾU hình mờ → gắn (toàn bộ video), đọc lại. | `python vm/thiet_lap_kenh_dom.py --kenh K --kiem-thuong-hieu [--dat-hinh-mo]` | K01 | tự chạy · nhịp 24 giờ · nặng (khoá máy) |
| D10 | Đòn bẩy đăng ký | Kích hoạt: kênh có phân phối (không bị cờ «không phát») mà `chuyen_doi_sub` đang tắt → CHỈ BÁO nên bật. | `kenh.yaml: chuyen_doi_sub: {bat: true} (chủ duyệt)` | D01 | chỉ báo |
| D11 | Lô bìa | Kích hoạt: kênh có khuôn bìa thắng THẬT (đủ bằng chứng, đang khai thác) mà chưa bật `bia_lo` → CHỈ BÁO nên bật. | `kenh.yaml: bia_lo: true (chủ duyệt)` | D01 | chỉ báo |
| D12 | Não bộ phận khỏe | Kích hoạt (toàn máy): lần gom nao/bo-phan.db cũ > 2 giờ → gom lại; giấc ngủ cuối cũ > 30 giờ → báo Việc của bạn. | `python -m core.nao_bo_phan gom` | — | tự chạy · nhịp 1 giờ · toàn máy |
| D13 | Thử nghiệm A/B tiêu đề + bìa | Kích hoạt: hàng việc máy có `studio_test_compare` (đề xuất bộ não) hoặc `studio_ab_tieu_de` (giám đốc kênh: video mới / video trượt, kenh.yaml `ab_tieu_de`) → Studio, trang sửa video, «Thử nghiệm A/B»: «Tiêu đề và hình thu nhỏ» (tiêu đề A + 1–2 tiêu đề đã soát, bìa A + 1–2 bìa có dấu cổng chữ) | «Chỉ tiêu đề» | «Chỉ hình thu nhỏ» → Lưu → đọc lại thử nghiệm STARTED + tiêu đề. Video đã có thử nghiệm → không đụng. Kênh thiếu tính năng nâng cao / không còn ứng viên → bỏ việc. | `python vm/studio_may_dom.py --kenh K --test-compare` | K01 | tự chạy · nhịp 3 giờ · nặng (khoá máy) |
| D14 | Đọc sức khoẻ Studio | Kích hoạt: hàng việc máy có `studio_kiem_suc_khoe` của kênh (cò sức khoẻ giám đốc) → CHỈ ĐỌC Studio: gậy / cảnh cáo, kiếm tiền, «nội dung dùng lại»; thấy thật mới báo chủ. Mỗi kênh mở Chrome tối đa 1 lần / 3 ngày. | `python vm/studio_may_dom.py --kenh K --suc-khoe` | K01 | tự chạy · nhịp 6 giờ · nặng (khoá máy) |
| D15 | Danh sách phát chủ đề | Kích hoạt: kênh ĐƯỢC PHÁT, kenh.yaml không khai danh_sach_phat_kenh, và chưa có danh sách phát chủ đề / còn danh sách chưa tạo / video chờ thêm / ≥ 8 video mới chưa vào danh sách nào → LLM gom video đã đăng thành 3–5 danh sách theo nghĩa (tên + mô tả tiếng kênh, video tốt trước) → nghien-cuu/danh-sach-phat.json → Studio tạo (Công khai, tên đã có thì dùng lại, không tạo trùng / xoá / đổi tên) → thêm video qua trang sửa Studio (không mở trang xem) → đọc lại. Chỉ video của chính kênh. Video mới lúc bàn giao: LLM chọn danh sách hợp nhất, hỏng thì danh sách đầu. | `python vm/danh_sach_phat_dom.py --kenh K` | K01, D01 | tự chạy · nhịp 3 giờ · nặng (khoá máy) |
| D18 | Duy trì trang chủ đúng chủ đề | Mỗi lần quét trang chủ CỦA KÊNH (lịch quét ngày của máy ảo → nghien-cuu/trang-chu.csv; bỏ dòng gộp từ kênh anh em) mới hơn lần đo trước: lấy ~30 ô đầu (bỏ Shorts / kệ / quảng cáo / Mix; ô mắt cào đánh 'Bị loại' vẫn tính), phân loại theo NGHĨA (đúng ngách / đúng chủ đề / lạc đề; cache theo mã video). KHÔNG mở Chrome. Chủ đề < 90% hoặc % ngách tụt (< 0,6 × tốt nhất 90 ngày, < 30%) → máy tự nuôi lại (sổ máy duy-tri.json, không đụng kenh.yaml) với nguồn ngách hẹp; 2 lần đạt liền → về duy trì; 7 ngày + 8 phiên vẫn dưới → báo động một lần, nuôi chậm. Quá 3 ngày không có lần quét mới → Tự kiểm báo một lần (lịch quét hỏng). Kênh trả kho / tu_chay: false → bỏ. kenh.yaml nuoi_trang_chu: false do chủ đặt → chỉ đo, hỏi chủ; duy_tri_trang_chu: false → tắt hẳn. | `python vm/nuoi_trang_chu.py --kenh K --tu-quet` | K17 | tự chạy · nhịp 1 giờ |
| D16 | Phát hiện tụt + tự chẩn đoán | Mỗi ngày: hiển thị @72h / CTR / AVD / trang chủ / đăng ký mỗi 1k của video đã qua 96 giờ so nền của CHÍNH kênh (thước chung). Tụt → soát chữ bìa đang chạy, lệch kiểu bìa, lệch đề tài, lỗi sản xuất → tự xếp sửa bìa sai chữ (S06), A/B cho video yếu, ghi não. | `python -X utf8 -m core.bat_thuong kenh --kenh K` | D01 | tự chạy · nhịp 20 giờ |
| D17 | Soát sản phẩm tuần | Mỗi tuần: chữ bìa đang chạy, 20 ảnh cảnh qua giám khảo, độ độc đáo kịch bản (kể cả xuyên ngôn ngữ); tỉ lệ ảnh xấu đi → vòng cải tiến lời nhắc đo trước/sau, chỉ áp vào prompt/7-canh.md khi qua thanh (có sao lưu). | `python -X utf8 -m core.soat_san_pham tuan --kenh K` | D02 | tự chạy · nhịp 144 giờ |
| D19 | Kiểm vàng bìa | Kích hoạt: vân tay mã bìa (bia_lo/cong_chu/do_bia/chon_bia/bia_theo_khuon + phần ảnh bìa của auto_khau), style.yaml, prompt/8-thumbnail.md, khoá bia_* của kenh.yaml hoặc thư mục bìa thắng ĐỔI (hay lần trước trượt > 24 giờ) → vẽ MỘT lô thật bằng mã hiện tại cho lượt mới nhất → tờ so bìa thắng | 3 bìa đang chạy | top-3 mới → cùng giám khảo chấm (kèm một bìa thắng giấu để hiệu chỉnh sàn) + sàn màu/bố cục/nhân vật. Trượt → bìa mới của kênh bị GIỮ + báo. | `python -X utf8 -m core.bia_lo --kiem-vang --kenh K` | D02 | tự chạy · nhịp 1 giờ |

## SỬA CHỮA — khi hỏng

| Mã | Skill | Làm gì · đọc lại | Chạy | Cần trước | Tự kích hoạt |
|---|---|---|---|---|---|
| S01 | Trả ngôn ngữ giao diện | Máy DOM tạm vi chưa trả (chết giữa chừng) → lần chạy sau tự trả. | `tự (ngon_ngu_tam.tra)` | — | — |
| S02 | Khám cấu hình kênh | Kênh tự chạy: BOM (U+FEFF) kẹt giữa kenh.yaml → gỡ (chỉ khi YAML chuẩn và bộ đọc tối giản ra cùng giá trị, bản cũ cất sao-luu); thiếu khoá bắt buộc (thu_muc_done, giờ/nhịp đăng, ngan_sach_ngay > 0, voice_id) → báo Việc của bạn kèm khoá gợi ý. KHÔNG bao giờ tự bật tu_chay/tu_dang/tu_duyet/tu_don/ngan_sach_ngay. | `python -m core.ky_nang go-bom K` | — | tự chạy · nhịp 24 giờ |
| S03 | Đổi bìa gấp | Kích hoạt: hàng sửa có việc bìa đang chờ cho video lên sóng < 12 giờ hoặc đã lên sóng — hoặc việc sửa bất kỳ (bìa / tiêu đề) chờ khe đêm quá 36 giờ (đói khe) — mà khe đêm 02–05 còn > 2 giờ (nhường phiên đăng 60', không đụng máy đăng dở) → sửa video ngay khi khoá máy rảnh. | `python vm/may_dang_dom.py --kenh K --sua-video` | K01 | tự chạy · nhịp 1 giờ · nặng (khoá máy) |
| S04 | Bàn giao lượt kẹt | Kích hoạt: lượt có 8-video.mp4, da_ban_giao false, lý do dừng là lỗi CẤU HÌNH (khoá kenh.yaml — không phải lỗi máy chủ) và khoá đã sửa → bàn giao đúng luồng bước 5 (khe trống sớm nhất, cổng chất lượng). | `python -m core.ban_giao_dang ban-giao-tay K <lượt> <ngày sổ>` | D02 | tự chạy · nhịp 6 giờ · nặng (khoá máy) |
| S05 | Dấu cổng chữ bìa chờ đăng | Kích hoạt: gói chờ đăng có bìa CHƯA có dấu cổng chữ (bàn giao trước luật 16/10, hoặc bìa đổi tay) → soát chữ bìa, đọc chữ trên bìa hai lượt khớp tuyệt đối → đóng dấu; bìa sai chữ → bìa dự phòng chữ vẽ bằng mã; AI lỗi → giữ gói, giờ sau thử lại (máy đăng không bao giờ tải bìa không dấu). | `python -X utf8 -m core.cong_chu dau-goi --kenh K` | D02 | tự chạy · nhịp 1 giờ |
| S06 | Sửa bìa sai chữ đang chạy | Kích hoạt: hàng `workspace/tu-kiem/viec-sua-bia.json` (D16/D17 thấy bìa ĐANG CHẠY sai chữ) → soát chữ bìa → bìa lô chữ vẽ bằng mã → đọc lại hai lượt + dấu cổng chữ → xếp đổi bìa (máy DOM), tự kiểm đọc lại i.ytimg.com. | `python -X utf8 -m core.bat_thuong sua-bia --kenh K` | D16 | tự chạy · nhịp 1 giờ |
