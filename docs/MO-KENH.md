# Mở kênh mới tự động (`core/mo_kenh.py`)

Máy tự quyết có nên mở kênh không (bằng số), tự dựng mọi thứ, người chỉ **tạo kênh YouTube và đăng nhập Chrome**.
Tổng quát cho VPS/ngách/quốc gia khác: ngôn ngữ, quốc gia, ngách đọc từ `CHANNEL/_NHOM/<nhóm>/ngach.yaml`; mã kênh
đặt theo mẫu mã đang có (`TL6-T7` → bản nhân `TL6-T7-K2`; tệp mới `TL7-T7`; chưa có mẫu → `K1`, `K2`).
Chủ đề/nhóm HOÀN TOÀN mới: chạy `python -m core.khoi_tao_ngach` trước (dựng ngách + kênh đầu); `mo_kenh` lo kênh THÊM.

## Luồng

1. **`de-xuat`** (không tạo gì, không LLM): luật số kênh của tổng giám đốc, số do mã tính từ
   `workspace/chuan-bi-kenh-moi/thi-truong.json` + số video thắng của kênh.
   - tối đa của tệp = nguồn nổ đang lên mỗi tháng ÷ 15, chỉ khi trang chủ của tệp lên/ổn định;
   - kênh nhân bản (`-K2`, `-K3`) chỉ khi kênh đầu của tệp đã thắng ≥ 2 video; tệp mới đánh số tiếp;
   - số liệu thị trường cũ > 30 ngày hoặc thiếu → không đề xuất; mỗi lần mở MỘT kênh.
   Ghi `workspace/mo-kenh/de-xuat.json` (mỗi tệp một câu lý do có số).
2. **`chuan-bi <TÊN>`** (tự làm hết, `tu_chay: false`): LLM chọn góc khác kênh anh em + tên + 5 danh sách phát + nhân vật
   (mã kiểm độ giống góc, trùng tên danh sách phát) · kiểu hình/prompt chép từ kênh thắng của tuyến · giọng từ
   `CHANNEL/_NHOM/<nhóm>/kho-giong.json` (không trùng kênh cùng tệp) · `kenh.yaml` (05:00, `san_xuat_truoc_gio 24`,
   `tu_duyet true`, `chien_luoc tu_dong`) · ảnh nhân vật, hồ sơ, logo/banner/hình mờ (`core.thiet_lap_kenh`, ShopAPI) ·
   handle chưa ai dùng (kiểm YouTube) · sổ tuyến + V7 · **chép sẵn Chrome Portable** `..\<TÊN>\<TÊN>.exe` từ bản có sẵn
   (App + launcher, `Data` để trống, không chép phiên đăng nhập kênh khác).
   `nuoi_trang_chu` và `thiet_lap_kenh` để `false` cho tới bước 3 (Chrome chưa đăng nhập thì agent chỉ báo `can_nguoi` oan).
3. **Việc duy nhất của người** (bảng điều khiển → "Việc của bạn"):
   `Mở kênh <TÊN>: tạo kênh YouTube và đăng nhập Chrome Portable tại Documents\TL\<TÊN>\<TÊN>.exe`.
4. **`kich-hoat <TÊN>`** (tự chạy mỗi nhịp khi tới hạn): thấy cookie `LOGIN_INFO` trong Chrome → ghép máy đăng
   (`trung_tam.them_kenh_vao_vm`, tự bật `tu_dang`) → bật `thiet_lap_kenh` + `nuoi_trang_chu` (ngôn ngữ tài khoản theo quốc gia
   nếu đã chứng minh, xem dưới) → đợi sổ thiết lập kênh `xong` → bật `tu_chay: true`.

## Lệnh

```
python -m core.mo_kenh de-xuat                 # in đề xuất + ghi de-xuat.json (KHÔNG tạo kênh)
python -m core.mo_kenh chuan-bi <TÊN> [--thu]  # (thêm --tep T --nhom N --goc-tu K khi đăng ký tay)
python -m core.mo_kenh kich-hoat <TÊN> [--ep]
python -m core.mo_kenh tiep-tuc                # móc của gác tổng: kích hoạt / chuẩn bị / đề xuất định kỳ 7 ngày
python -m core.mo_kenh xem
```

Gác tổng (`core/gac_tong.py`, 15 phút) gọi `mo_kenh.nhip`: chỉ quyết có bước tới hạn không, có thì sinh `tiep-tuc` tách
rời. Bộ não (`core/nao.py xem`) hiện mục "MỞ KÊNH MỚI". Trạng thái: `workspace/mo-kenh/trang-thai.json`
(`de_xuat → chuan_bi_xong → cho_chrome → dang_thiet_lap → xong`).

Công tắc `workspace/cai-dat.json: "mo_kenh": "tat" | "goi_y" | "tu_chuan_bi"` (mặc định `tu_chuan_bi`; `goi_y` = máy chỉ đề xuất,
người chạy `chuan-bi`).

## Ngôn ngữ tài khoản theo quốc gia (Studio)

`kenh.yaml: ngon_ngu_tai_khoan_dich: "ja"` → `vm/thiet_lap_kenh_dom.py` đổi ngôn ngữ Google của tài khoản kênh sang đó
(bảng `NGON_NGU_DICH`: vi, ja, en, ko). Không khai = giữ `vi`; khai lệch quốc gia hồ sơ = giữ `vi`. Triển khai dần: kênh
mới chỉ được khai khoá này khi `workspace/cai-dat.json: "ngon_ngu_tai_khoan_chung_minh": ["ja"]` (ghi sau khi kênh thử
đăng thật qua Studio ngôn ngữ đó ĐẠT).

## Kho Chrome + thay kênh không được phát (20/10/2026, `core/thay_kenh.py`, skill D20)

- **Kho Chrome** = `<cha của MyTool>\kho\` (tính từ GOC). Trả kho (`python -m core.tra_kho tra <MÃ>`) dời Chrome kênh vào
  `kho\<MÃ>\` khi Chrome không chạy / khoá máy không giữ cho kênh (bận thì `nhip` sau); `lay-lai` dời về. Không xoá, không đè.
  Mọi chỗ tìm Chrome kênh lùi về `kho\<MÃ>\<MÃ>.exe`. Chủ thả Chrome Portable MỚI (tên tuỳ ý, có `<tên>.exe`) đã đăng
  nhập Gmail tay vào kho; `python -m core.kho_chrome quet` liệt kê (chỉ đọc). Sổ đã giao: `kho\_da-dung.json`.
- **Kênh trả kho không tính ở đâu cả**: `core.kenh.liet_ke_kenh` mặc định bỏ (chỗ quản lý truyền `ca_tra_kho=True`),
  `core.kenh.bo_kenh_tra_kho` cho danh sách đọc từ `vm/cai-dat-tool.json` / `vm/config.json`; agent bỏ mọi việc Chrome
  (kể cả việc từ trạm) của kênh trả kho; nguồn kênh trả kho đang giữ được nhả.
- **Luật hỏng** (mỗi ngày): ≥ 10 video đăng ≥ 72 giờ, trung vị hiển thị < 100, không video nào > 500 (bảng
  `CHANNEL/<k>/chi-so/bang-tom-tat.csv`; cũ > 3 ngày / thiếu = không kết luận). `python -m core.thay_kenh xet` (chỉ đọc).
- **Thay** (mỗi ngày tối đa một lượt mới, sổ `workspace/mo-kenh/thay-kenh.json`, chạy lại an toàn): trả kho → Chrome mới đã
  đăng nhập trong kho → mã kế cùng dòng (`TL5-T7-K2` → `TL5-T7-K3`) → giọng chưa kênh đang chạy nào dùng → đăng ký mở kênh
  (`loai: thay_kenh_tu_dong`, khuôn kênh cũ) → `vm/tao_kenh_thuong_hieu.py` (không tạo trùng, chọn kênh + ghim UC) → kích
  hoạt (nối đuôi `cac_kenh`, agent nạp nóng) → thiết lập 11/11 + UC ghim → bật `tu_chay`/`tu_duyet`/`tu_dang` → một tin báo.
  Kho hết Chrome / hết giọng / tạo kênh cần người → "Việc của bạn". Tắt: `workspace/cai-dat.json: thay_kenh_tu_dong: false`.
