# MyTool VPS

Tool tự vận hành kênh YouTube trên một VPS Windows: nghiên cứu đối thủ → chọn
content → sản xuất video (ShopAPI) → tự đăng → trả lời bình luận → học lại từ
số liệu Studio. Một VPS chạy tối đa 10 kênh cùng ngách. Kho này là nguồn mã
chung của mọi VPS; mỗi máy giữ cấu hình, khoá và dữ liệu kênh riêng (không lên kho).

## Cần gì
- Windows Server/10+, 8 GB RAM trở lên, Google Chrome.
- Tài khoản ShopAPI (khoá API) và các kênh YouTube đã đăng nhập trên Chrome.
- Git và một deploy key riêng cho máy (để nhận bản mới từ kho chung).

## Cài VPS mới
1. Tạo deploy key, mở đường SSH (máy chỉ có IPv6 đi qua NAT64), rồi clone:
   `git clone git@github-mytool:manhthang1905-hub/mytool-vps.git MyTool`
   — chi tiết từng bước ở `docs/PHAT-TRIEN-NHIEU-VPS.md` mục 1.
2. Chạy `CAI-DAT-VPS.bat`: gọi `SETUP.bat` (Python, venv, `requirements.txt`, lối tắt),
   cài thư viện cho `vm/`, ghi `vps.json`, `vm/config.json` và đăng ký lịch Task Scheduler.
3. Mở tool (`CHAY-GON.vbs`; cần console để gỡ lỗi thì `CHAY-QT.bat`), nhập khoá
   ShopAPI, thêm kênh theo `docs/THEM-KENH.md` (đổi ngách: `docs/DOI-CHU-DE.md`).
4. Kiểm máy: `python -m core.kiem_may --day-du`; kiểm đường kho: `python -m core.dong_bo_git ket_noi`.

## Thư mục
| Thư mục / tệp | Dùng làm gì |
|---|---|
| `shopapi_studio_qt.py` | Giao diện (7 trang VPS) |
| `tu_chay.py` | Sản xuất tự động theo lịch |
| `tram_nen.py` | Trạm số liệu Studio (cổng 8765) |
| `core/` | Toàn bộ logic, chạy được không cần giao diện; `chien_luoc/` công thức chọn nguồn, `chi_so_ytb/` trạm + giải mã số liệu, `ytb_extension/` nguồn extension cào Studio |
| `ui_qt/` | Giao diện PyQt5 |
| `vm/` | Máy đăng, bình luận, quét Studio (`vm/agent.py`) |
| `_sdk/shopapi/` | SDK ShopAPI đi kèm |
| `tool-catalog/` | `prompt.workbook` (bảng prompt cảnh), `transcribe.local` |
| `mau-capcut/` | Khuôn CapCut |
| `CHANNEL/` | Khuôn ngách (`_KHUON`, `_NHOM`); thư mục kênh thật nằm ở đây nhưng không vào kho |
| `chia-se/bai-hoc/` | Bài học ngách dùng chung giữa các VPS |
| `docs/` | Hướng dẫn vận hành, bản đồ module, kiến thức dùng chung (`docs/kien-thuc/`) |
| `tests/` | Kiểm thử pytest |

## Chạy tự động (Task Scheduler)
`ShopAPI-TuChay` (hằng ngày), `ShopAPI-DieuPhoi` (10 phút), `ShopAPI-CanhTram`,
`ShopAPI-TramLucDangNhap`, `ShopAPI-GacTong` (15 phút, trong đó có kiểm cập nhật).
Chi tiết vận hành: `README-VPS.md`.

## Phát triển và cập nhật
- Sửa mã sống chỉ trong khung phút :15–:45; chỉ chạy test lẻ liên quan,
  **không** `pytest tests/` toàn kho trên máy đang sản xuất.
- Sửa xong: `python -m core.dong_bo_git day "<thông điệp>"` (thêm `--chi <tệp…>`
  khi máy còn tệp dở của người khác). Lệnh tự kiểm, quét bí mật, commit, rebase,
  nâng phiên bản (`VERSION`, `CHANGELOG.md`, tag) rồi đẩy.
- Các VPS khác tự nhận bản mới lúc rảnh (gác tổng 15', tự lùi nếu hỏng); xem
  bản đang chạy và bản trên kho: `python -m core.dong_bo_git kiem`.
- Quy trình đầy đủ: `docs/PHAT-TRIEN-NHIEU-VPS.md`. Luật cho trợ lý lập trình: `CLAUDE.md`.
