# MyTool VPS

Tool tự vận hành kênh YouTube trên một VPS Windows: nghiên cứu đối thủ → chọn
content → sản xuất video (ShopAPI) → tự đăng → trả lời bình luận → học lại từ
số liệu Studio. Một VPS chạy tối đa 10 kênh cùng ngách. Kho này là nguồn mã
chung của mọi VPS. Cấu hình, khoá và dữ liệu kênh của từng máy không lên kho.

Tệp này là cửa vào duy nhất. Phiên Claude trên máy đọc thêm `CLAUDE.md`.

## Cần gì
- Windows Server 2019+ hoặc Windows 10+, RAM từ 8 GB, Git for Windows.
- Tài khoản shopapi.vn (khoá API, ví có tiền).
- Mỗi kênh một Chrome portable (GPM…) đã đăng nhập YouTube.
- Một deploy key riêng cho máy. Chủ dự án thêm key vào GitHub.

## Cài VPS mới (6 bước)
1. **Deploy key.** Mỗi máy một key, không chép key của máy khác:
   `ssh-keygen -t ed25519 -f %USERPROFILE%\.ssh\mytool_vps_deploy -N "" -C mytool-<ma-may>`.
   Gửi tệp `.pub` cho chủ dự án. Chủ dự án thêm nó vào GitHub, mục Settings > Deploy keys, và bật **Allow write access**.
2. **Đường SSH.** Máy có IPv4 thì bỏ qua bước này. Máy chỉ có IPv6 thì đi qua NAT64: dò địa chỉ AAAA tổng hợp
   `Resolve-DnsName github.com -Type AAAA -Server 2a00:1098:2b::1`
   (DNS64 dự phòng: `2a00:1098:2c::1`, `2a01:4f8:c2c:123f::1`), rồi ghi vào `%USERPROFILE%\.ssh\config`:
   ```
   Host github-mytool
       HostName <địa chỉ AAAA vừa dò>
       HostKeyAlias github.com
       User git
       IdentityFile ~/.ssh/mytool_vps_deploy
       IdentitiesOnly yes
   ```
   Lần đầu kết nối, so vân tay ED25519 với trang "GitHub's SSH key fingerprints" trên docs.github.com.
   Máy có IPv4 thì dùng cùng khối này, nhưng `HostName github.com`.
3. **Clone** vào thư mục nằm cạnh các thư mục trình duyệt kênh:
   ```
   cd C:\TL
   git clone git@github-mytool:manhthang1905-hub/mytool-vps.git MyTool
   ```
   Trình duyệt của mỗi kênh nằm ở `C:\TL\<MÃ KÊNH>\<MÃ KÊNH>.exe`, cùng cấp với `MyTool\`, không nằm bên trong.
4. **Cài:** nhấp đúp `MyTool\CAI-DAT-VPS.bat`. Muốn xem trước các bước mà không làm gì thật thì chạy `CAI-DAT-VPS.bat --thu`. Bộ cài tự làm các việc sau:
   - Python, `.venv`, `requirements.txt`, lối tắt (qua `scripts\SETUP.bat`);
   - thư viện cho `vm\`;
   - `vps.json`, `vm\config.json`, thư mục `DONE\`, `CLAUDE.local.md`;
   - 5 lịch Windows (mục Vận hành).

   Sau đó tạo `cap-nhat.json` từ `cap-nhat.example.json` và điền `dong_bo_git.ma_may`, ví dụ `"vps-jp2"`.
5. **Kiểm và chạy:**
   ```
   python -m core.kiem_may --day-du      (mọi dòng phải OK)
   python -m core.dong_bo_git ket_noi    (đường tới kho + deploy key)
   ```
   Mở tool bằng biểu tượng **MyTool VPS** hoặc `CHAY-GON.vbs`. Vào **Tài khoản & Cài đặt** để đăng nhập shopapi.vn.
   - Thiếu mô hình Whisper (máy chỉ IPv6 không tải được từ HuggingFace): chép thư mục `models\faster-whisper-small\` từ một máy đã có, qua ổ chia sẻ RDP.
   - Thiếu thư viện: chạy lại `CAI-DAT-VPS.bat` khi mạng ổn. Chạy lại nhiều lần không hại gì.
   - Trạm hoặc phiên kênh chưa chạy: mở tool một lần rồi kiểm lại.
6. **Ngách + kênh đầu tiên (AI tự làm):** chủ đề, quốc gia, ngôn ngữ là đủ:
   ```
   python -m core.khoi_tao_ngach --chu-de "nấu ăn tại gia" --quoc-gia VN --ngon-ngu vi --thu   (xem trước, 0 đồng)
   python -m core.khoi_tao_ngach --chu-de "nấu ăn tại gia" --quoc-gia VN --ngon-ngu vi [--kenh-mau <link>]
   ```
   Hoặc trên giao diện: **Số liệu kênh → Thêm kênh → "Ngách mới bằng AI"**. Lệnh viết hồ sơ ngách, dựng kênh, viết lại lời nhắc theo ngách, tìm đối thủ rồi chạy nghiên cứu khởi động. Việc còn lại cho người (giọng đọc, Chrome kênh, bật tiền) nằm ở `CHANNEL/<mã>/KHOI-TAO.md`. Chi tiết: `docs/KENH-VA-NGACH.md`.

## Vận hành hằng ngày
Máy tự chạy qua 5 lịch Windows:

| Lịch | Nhịp | Việc |
|---|---|---|
| `ShopAPI-TuChay` | 02:00 hằng ngày | `tu_chay.py --tat-ca`: nghiên cứu → chọn nguồn → 8 khâu → bàn giao |
| `ShopAPI-DieuPhoi` | 10 phút | `tu_chay.py --dieu-phoi`: chạy song song các kênh (khi `workspace/cai-dat.json` có `"dieu_phoi": true`) |
| `ShopAPI-CanhTram` | 5 phút | `tram_nen.py --kiem`: trạm 127.0.0.1:8765 chết thì tự bật lại |
| `ShopAPI-TramLucDangNhap` | lúc đăng nhập | như trên, sau khi máy khởi động lại |
| `ShopAPI-GacTong` | 15 phút | `core.gac_tong`: canh lỗi, ví, Windows, và kiểm cập nhật |

Phiên kênh (`vm/agent.py`) mở trình duyệt khoảng 60 phút trước giờ đăng, mỗi lúc chỉ một trình duyệt. Nó quét Studio, đăng video, trả lời bình luận rồi đóng trình duyệt.

Mở tool mỗi ngày một lần. Trang **Bảng điều khiển** có ba phần:
- khối "Việc của bạn": việc cần làm tay, việc hỏng xếp trước, mỗi dòng có nút bấm;
- dòng máy: ví, ổ đĩa, lịch;
- mỗi kênh một thẻ.

Việc tay (tool chỉ nhắc, không tự làm):
- **Duyệt video** của kênh chưa bật `tu_duyet`.
- **Nạp ví.** Ví dưới 1,5 lần chi phí một video thì tool không mở video mới.
- **Ghim bình luận mở đầu** nếu kênh cần. Xem `docs/DANG-VA-BINH-LUAN.md`.
- **Windows hết hạn dùng thử.** Tool tự rearm khi còn lượt. Hết lượt thì phải nhập khoá.
- **Hạn thuê VPS.** Điền `"ngay_het_han_vps": "2027-03-15"` vào `workspace/cai-dat.json`.
- **Ổ đĩa đầy.** Dọn các lượt cũ đã đăng trong `PROJECTS/AUTO/<kênh>/`.

Nhật ký: `workspace/tu-chay/<ngày>.md`, `workspace/tu-chay/tu-chay.log`, `vm/agent.log`,
`PROJECTS/AUTO/<k>/<lượt>/trang-thai.json`, `workspace/loi-chay-max.md`.
Khi cần xem lỗi trên cửa sổ console, chạy `scripts\CHAY-QT.bat`.

## Cập nhật
- Tool tự cập nhật. Mặc định bật, kể cả trên VPS mới. Gác tổng kiểm kho khoảng 30 phút một lần.
- Khi có bản mới, máy chờ lúc rảnh trong khung phút :15–:45, áp bản mới, rồi tự mở lại giao diện. Bản mới hỏng thì máy tự lùi về bản cũ.
- Xem và bấm tay ở **Cài đặt → Cập nhật tool**. Ở đó có nút Kiểm tra, Cập nhật ngay, Quay lại bản trước, và công tắc Tự động.
- Dòng lệnh:
  - `python -m core.dong_bo_git kiem` xem bản đang chạy và bản trên kho;
  - `python -m core.dong_bo_git keo --ep` cập nhật ngay;
  - `python -m core.dong_bo_git lui` quay lại bản trước;
  - `python -m core.cap_nhat_git tu_dong tat|bat` tắt hoặc bật tự cập nhật.
- Máy có sửa chưa đẩy thì không bị kéo đè. Giao diện sẽ báo "có sửa chưa đẩy". Cách đẩy lên kho xem `docs/PHAT-TRIEN.md`.

## Tài liệu
| Tệp | Đọc khi |
|---|---|
| `CLAUDE.md` | Luật cho mọi phiên Claude trên mọi VPS |
| `docs/PHAT-TRIEN.md` | Sửa mã, đẩy lên kho, phiên bản, bản đồ module |
| `docs/KENH-VA-NGACH.md` | Ngách mới bằng AI, thêm kênh, đổi chủ đề/quốc gia, hồ sơ ngách, chia sẻ bài học |
| `docs/DANG-VA-BINH-LUAN.md` | Máy đăng (DOM/ảnh), bình luận, OAuth dự phòng |
| `docs/kien-thuc/` | `chien-luoc.md` (bộ máy chọn nguồn), `con-duong-kenh-thang.md`, `nghien-cuu-bia.md` |

`scripts/` chứa công cụ phụ ít dùng: `SETUP.bat` (do `CAI-DAT-VPS.bat` gọi), `CHAY-QT.bat` (mở tool kèm console), `KIEM-TRA.bat` (in chẩn đoán), `KIEM-TRA-PHAT-HANH.bat` (quét bí mật trước khi phát hành).
