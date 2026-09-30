# Máy này là VPS tự chạy kênh — đọc trước khi sửa gì

Tệp này được bộ cài VPS chép thành `CLAUDE.local.md` ở gốc MyTool. Nó bổ sung
cho `CLAUDE.md` (luật chung của tool) bằng những gì CHỈ đúng trên VPS.

Chủ dự án mở phiên ở đây để tối ưu và phát triển tiếp tool, ngay trên máy
đang chạy thật. Máy này đang tiêu tiền thật và đăng video thật lên kênh thật.
Mọi thay đổi đều phải tính đến điều đó.

## Máy này đang làm gì

```
MyTool\                       thư mục duy nhất của máy
  <MÃ KÊNH>\<MÃ KÊNH>.exe   trình duyệt của từng kênh (GPM/Chrome portable), tối đa 10
  vm\                       động cơ: agent.py, may_dang.py, may_cmt.py
  DONE\                     các gói video đang chờ đăng
  PROJECTS\                 kết quả sản xuất
  vps.json                  dấu CHẾ ĐỘ VPS; `vm_dir` dùng đường tương đối `vm`
```

- **MyTool** là thứ duy nhất hiện trên màn hình. Mở lên là trang **Trung tâm**.
  Nó bật trạm (cổng 8765, chỉ 127.0.0.1) và trông ba động cơ của vm\ qua
  `core/giam_sat_vm.py`. Tắt cửa sổ MyTool thì động cơ **vẫn chạy**, vì chúng
  được tách khỏi tiến trình MyTool.
- **Sản xuất:** lịch Windows `ShopAPI-TuChay` (`core/lich_tu_chay.py`) mỗi
  ngày chạy `tu_chay.py --tat-ca`. Các kênh chạy lần lượt: nghiên cứu → chọn
  nguồn → van ngân sách → 8 khâu → bàn giao → dọn đồ đã đăng → báo cáo.
- **Phiên kênh** (`vm/agent.py`, chế độ phiên): khoảng 60 phút trước giờ đăng
  của từng kênh thì mở trình duyệt kênh đó (mỗi lúc chỉ MỘT trình duyệt), cào
  Studio và trang chủ, đăng (hẹn giờ bằng lịch của YouTube), trả lời bình
  luận, rồi đóng.

## Xem máy đang ra sao (miễn phí, không gọi mạng)

| câu hỏi | chỗ xem |
|---|---|
| hôm nay mỗi kênh làm gì | `workspace/tu-chay/<ngày>.md`, và `CHANNEL/<k>/tu-chay/<ngày>.json` (có `nhat_ky`) |
| nhật ký lịch chạy ngầm | `workspace/tu-chay/tu-chay.log` |
| một video đang ở khâu nào | `PROJECTS/AUTO/<k>/<lượt>/trang-thai.json` |
| phiên kênh, đăng, bình luận | `vm/agent.log`, nhật ký của may_dang/may_cmt trong `vm/`, `vm/trang-thai.json` |
| kế hoạch đăng | `CHANNEL/<k>/ke-hoach-dang/ke-hoach.csv` |
| số liệu Studio | `CHANNEL/<k>/chi-so/` (mốc chọn theo TUỔI THẬT, xem `gom.tuoi_that_gio`) |
| đã dọn gì | `CHANNEL/<k>/tu-chay/don-dep.log`, `da-don.json` trong thư mục lượt |
| trạm | `GET http://127.0.0.1:8765/trang-thai`, `/may-noi`, `/tu-chay` |

Luật lịch sử và số liệu của từng kênh nằm ở `CHANNEL/<k>/CLAUDE.md` và
`NHAT-KY-KENH.md`. Hai tệp này thắng mọi phân tích chung.

## Luật riêng của VPS (thêm vào 5 luật của CLAUDE.md)

1. **Trình duyệt mở thì IPv4 phải TẮT.** Danh tính của kênh là IPv6. Chỉ bật
   IPv4 khi đã đóng hết trình duyệt kênh và đã cắm cờ `vm/van-ipv4.json`, rồi
   tắt IPv4 ngay khi xong (xem `vm/KE-HOACH.md`, "IPV4 VALVE"). Không có ngoại
   lệ, kể cả để tải thư viện.
2. **Đang đăng thì không giết.** Trước khi khởi động lại động cơ hay MyTool,
   xem `vm/trang-thai.json` và nhật ký may_dang: có phiên đang chạy thì chờ.
   Giết giữa lúc tải lên có thể để lại video dở trên kênh.
3. **Không tự bật tiền.** `tu_chay`, `ngan_sach_ngay`, `tu_duyet`, `tu_don`
   trong `kenh.yaml` là quyết định của chủ dự án. Muốn thử thì dùng
   `python tu_chay.py --kenh <k> --thu`: nó chỉ nghiên cứu và chọn nguồn,
   không tốn ví.
4. **Không chạy vòng hỏi job.** Luật 4 của CLAUDE.md vẫn nguyên: chờ job thì
   dùng đường có sẵn, không viết vòng hỏi dày.
5. **Mạng chỉ có IPv6.** Dùng được: api.shopapi.vn, pypi/python.org,
   api.anthropic.com, npm/nodejs.org, YouTube, raw.githubusercontent.com.
   KHÔNG dùng được trực tiếp (đo 18/09/2026): github.com, codeload,
   objects.githubusercontent, tải tệp HuggingFace, downloads.claude.ai. Đừng
   viết mã phụ thuộc chúng. Riêng kho chung GitHub thì đi qua NAT64 công cộng
   (`python -m core.dong_bo_git ket_noi` tự dò và sửa `~/.ssh/config`).
6. **Kiểm thử trên máy sản xuất: KHÔNG pytest toàn kho.** Chỉ chạy test lẻ có
   liên quan (`python -m pytest tests/test_<việc>.py -q`), khi khe "nang" trống.
   `dong_bo_git day` tự chạy nhóm test nhanh trước khi đẩy. Tự chạy thật thì
   bắt đầu bằng `--thu`.

## Sửa xong thì đưa về kho gốc thế nào

Kho chung `github.com/manhthang1905-hub/mytool-vps` là nguồn gốc mã của MỌI
VPS (xem `docs/PHAT-TRIEN-NHIEU-VPS.md`). Nên:

1. Sửa trong khung :15–:45, sao lưu bản cũ vào `workspace/ban-va/<ngày>-<việc>/`
   (kèm GHI-CHU.md), ghi một mục vào `NHAT-KY-PHAT-TRIEN.md` (nhật ký riêng
   máy, không lên kho).
2. **Mọi sửa xong phải `python -m core.dong_bo_git day "<thông điệp>"`**
   (`--minor`/`--major` khi cần, `--chi <tệp…>` nếu máy còn tệp dở của người
   khác) — kiểm + quét bí mật + commit + rebase + TỰ NÂNG PHIÊN BẢN (VERSION,
   1 dòng CHANGELOG.md, tag v<x.y.z>) + push. Xung đột thì nó dừng và báo,
   đừng tự giải bừa.
3. Các VPS khác TỰ NHẬN bản mới (`core/cap_nhat_git.py`: kiểm ~30 phút trong
   gác tổng + giao diện, áp lúc máy rảnh trong khung :15–:45, tự lùi nếu
   hỏng). Mặc định bật; tắt ở Cài đặt → Cập nhật tool. Máy có sửa chưa đẩy
   thì KHÔNG bị kéo đè — nên đừng để sửa nằm lại.

## Kế hoạch và lịch sử

Hai tệp dưới chỉ còn trên máy gốc (đã gỡ khỏi kho chung 30/09/2026); nội dung
còn đúng đã nằm trong `README-VPS.md`, `docs/` và tệp này.

- `vm/KE-HOACH-5-KENH.md`: kế hoạch tổng 5 kênh / 1 VPS, bảng việc đã xong,
  câu hỏi còn chờ chủ dự án.
- `vm/KE-HOACH.md`: nhật ký đường dây trạm ↔ VM và các bẫy đã dính (IPv6,
  khoá một-mình, extension không tự nạp lại, van IPv4…).
