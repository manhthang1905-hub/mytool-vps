# MyTool trên VPS — đọc trước khi cài

Tài liệu này dành cho người VẬN HÀNH máy (không cần biết lập trình). Máy VPS
chạy 24/7, tự nghiên cứu — tự làm video — tự đăng — tự trả lời bình luận cho
nhiều kênh YouTube, không cần ai ngồi trước màn hình. Bốn việc dưới đây là
mọi thứ bạn cần biết để bắt đầu:

1. [Cài VPS mới](#1-cài-vps-mới)
2. [Bật tự động cho một kênh](#2-bật-tự-động-cho-một-kênh)
3. [Xem Bảng điều khiển](#3-xem-bảng-điều-khiển)
4. [Việc tay định kỳ](#4-việc-tay-định-kỳ)

Muốn thêm kênh mới → đọc `docs/THEM-KENH.md`. Muốn đổi chủ đề/ngách → đọc
`docs/DOI-CHU-DE.md`. Sửa mã (dành cho phiên Claude Code mở ngay trên VPS) →
đọc `CLAUDE.local.md` ở gốc thư mục này.

## 1. Cài VPS mới

Máy Windows Server sạch, có thể **chỉ có mạng IPv6** (nhiều VPS thuê ngoài là
vậy — xem `CLAUDE.local.md` luật riêng VPS số 5 sau khi cài xong).

1. Đăng nhập máy bằng Remote Desktop, mở PowerShell hoặc File Explorer.
2. Chép (hoặc `git clone`) toàn bộ kho MyTool vào một thư mục, ví dụ
   `C:\MyTool`. Xong bước này, `vm\` phải nằm NGAY BÊN TRONG thư mục đó
   (cùng cấp với `core\`, `ui_qt\`, `tu_chay.py`).
3. Đặt trình duyệt Chrome portable của TỪNG kênh cạnh `C:\MyTool` (không
   nằm trong), mỗi kênh một thư mục tên đúng MÃ KÊNH, ví dụ
   `C:\TL1-T7\TL1-T7.exe` — chi tiết ở `docs/THEM-KENH.md` bước 2. Có thể
   làm bước này SAU, lúc thêm từng kênh.
4. Mở thư mục `C:\MyTool`, nhấp đúp **`CAI-DAT-VPS.bat`**. Cửa sổ đen hiện
   ra và tự làm hết: cài thư viện (kể cả bản cho máy chỉ IPv6), đánh dấu máy
   đang chạy chế độ VPS, tạo `vm\config.json`, tạo thư mục `DONE\`, sinh
   `CLAUDE.local.md`, và đăng ký BA lịch Windows (Task Scheduler) để máy tự
   chạy kể cả khi khởi động lại. Có thể mất vài phút, đừng tắt cửa sổ.
   - Muốn xem TRƯỚC các bước sẽ làm mà chưa làm gì thật: mở PowerShell trong
     thư mục đó, gõ `CAI-DAT-VPS.bat --thu`.
5. Cài xong, kiểm lại bằng lệnh (mở PowerShell trong `C:\MyTool`):

   ```
   python -m core.kiem_may --day-du
   ```

   Bảng OK/THIẾU hiện ra — mọi dòng phải **OK** trước khi giao máy cho chạy
   thật. Dòng nào THIẾU thì đọc gợi ý ngay bên cạnh nó:
   - **Thiếu mô hình Whisper** (máy chỉ IPv6 không tự tải được từ
     HuggingFace): mở Remote Desktop từ MÁY NHÀ, chép nguyên thư mục
     `models\faster-whisper-small\` từ máy nhà (đã tải sẵn) sang đúng vị trí
     đó trên VPS qua ổ đĩa chia sẻ của RDP.
   - **Thiếu thư viện**: chạy lại `CAI-DAT-VPS.bat` một lần nữa khi mạng ổn.
   - **Trạm/Phiên kênh chưa chạy**: bình thường nếu MyTool CHƯA được mở lần
     nào — mở MyTool lên rồi kiểm lại.
6. Mở MyTool (biểu tượng "MyTool VPS" trên Desktop). Vào **Tài khoản &
   Cài đặt** đăng nhập bằng tài khoản shopapi.vn, dán khoá API/nạp ví.

Từ đây máy đã sẵn sàng — việc còn lại là thêm kênh (`docs/THEM-KENH.md`) và
bật công tắc tự chạy cho từng kênh (mục 2 dưới).

## 2. Bật tự động cho một kênh

Mỗi kênh có MỘT công tắc chính: `tu_chay` (trong `kenh.yaml` của kênh đó,
hoặc tick "Cho kênh tự làm video mỗi ngày" ở bước 3 của thuật sĩ **Thêm
kênh** — xem `docs/THEM-KENH.md`). Bật công tắc này thì:

- Lịch Windows **ShopAPI-TuChay** (đăng ký sẵn lúc cài, chạy `tu_chay.py
  --tat-ca` mỗi ngày lúc 02:00, tự thử lại trong ngày nếu lượt trước chưa
  xong) sẽ nghiên cứu → chọn nguồn → qua van ngân sách → chạy 8 khâu sản
  xuất → bàn giao → xếp lịch đăng cho kênh này.
- Phiên kênh (`vm/agent.py`, khoảng 60 phút trước giờ đăng đã đặt) mở trình
  duyệt của kênh, đăng video theo lịch, trả lời bình luận, rồi tự đóng.
- Lịch **ShopAPI-CanhTram** (mỗi 5 phút) canh trạm nội bộ (cổng 8765) —
  trạm chết thì tự khởi động lại, không cần ai can thiệp.

Ba lịch này CAI-DAT-VPS.bat đã đăng ký sẵn — không cần bật tay. Việc BẬN
TAY thật sự chỉ có: bật `tu_chay` cho từng kênh, đặt **trần tiền mỗi ngày**
(kênh không bao giờ tiêu quá số đó, để 0 thì kênh không tự sản xuất), và
chọn **tự đăng hay chờ duyệt** (`tu_duyet`):

- **Chờ duyệt** (mặc định, an toàn cho kênh mới): video làm xong nằm chờ ở
  Bảng điều khiển, bạn bấm "Duyệt đăng" thì mới lên lịch thật.
- **Tự đăng**: video làm xong tới giờ tự lên sóng, không ai xem lại — chỉ
  bật khi đã tin kênh (khuyến nghị: chờ ít nhất 7 ngày đầu, xem quyết định
  #7 trong `workspace/LO-TRINH-PHAT-HANH-V3.md`).

Tắt tự chạy tạm thời cho một kênh: bỏ tick `tu_chay` — mọi thứ khác (trình
duyệt, dữ liệu) giữ nguyên, bật lại là chạy tiếp.

## 3. Xem Bảng điều khiển

Mở MyTool trên VPS, màn hình đầu tiên LUÔN là **Bảng điều khiển** (không
phải màn nào khác) — trả lời ba câu trong vài giây:

| Khối | Trả lời câu | Nội dung |
|---|---|---|
| **Việc của bạn** | Tôi cần làm gì? | Danh sách việc TAY, xếp theo mức nặng: ✕ hỏng (cần xử lý ngay) → ⚠ cần xem (chờ duyệt, quá giờ đăng…) → • thông tin (ghim bình luận, dọn nháp thừa). Mỗi dòng có nút bấm thẳng, không cần đi tìm ở tab khác. |
| **Dòng máy** | Máy có ổn không? | Một dòng: ví còn bao nhiêu (chạy được bao lâu nữa), ổ đĩa còn trống, máy bật từ bao giờ, máy có đang chạy nền không, lần quét Studio gần nhất, lịch hằng ngày có đăng ký chưa. |
| **Thẻ kênh** | Kết quả ra sao? | Mỗi kênh một thẻ lớn: câu tình trạng hiện tại, video kế tiếp lên sóng lúc nào, ba video gần nhất kèm mũi tên so cùng mốc tuổi (tăng/giảm so với video trước). Kênh không tự chạy dồn vào dòng "Kênh khác đang tắt ▸" phía dưới. |

Màu viền mỗi thẻ kênh nói ngay tình trạng: xanh = tốt, vàng = cần xem, đỏ =
hỏng, xám = đang tắt. Bấm vào một việc trong khối "Việc của bạn" là xử lý
được luôn (duyệt đăng, chạy lại khâu hỏng, đánh dấu đã ghim…) — không phải
mở thêm tab nào khác cho việc thường ngày.

Muốn xem số liệu Studio thật của một kênh (view/giờ xem/sub theo TUỔI THẬT
của video, không lẫn video già/mới) → mở thẻ kênh đó, hoặc đọc thẳng
`CHANNEL/<kênh>/CLAUDE.md` + `NHAT-KY-KENH.md` (hai tệp này thắng mọi phân
tích chung, xem `CLAUDE.local.md`).

## 4. Việc tay định kỳ

Máy tự chạy hầu hết mọi thứ, nhưng vài việc CỐ Ý để người quyết (tiền thật,
uy tín kênh):

- **Duyệt video chờ duyệt** — kênh nào chưa bật "tự đăng" thì video nằm chờ
  ở Bảng điều khiển, khối "Việc của bạn". Không duyệt trong `bien_xu_ly_gio`
  (mặc định 12 giờ trước giờ công khai) thì lịch bị lùi, không mất video.
- **Ghim bình luận mở đầu** — YouTube API không cho tool tự ghim; tool chỉ
  soạn sẵn bình luận và nhắc ở khối "Việc của bạn". Ghim bằng điện thoại
  hoặc máy nhà, bấm "Đã ghim" là xong.
- **Kiểm ví đủ tiền** — dòng "Dòng máy" báo ví còn chạy được bao lâu; hết ví
  giữa lượt sản xuất, tool tự dừng an toàn (không mất tiền oan) nhưng kênh
  ngừng ra video tới khi nạp lại.
- **Kiểm ổ đĩa còn trống** — video/ảnh/clip chiếm nhiều dung lượng; ổ gần
  đầy thì dọn `PROJECTS/AUTO/<kênh>/<lượt cũ>` đã bàn giao xong (tool tự dọn
  phần lớn, nhưng đáng kiểm định kỳ, đặc biệt sau vài tuần chạy nhiều kênh).
- **Windows sắp hết hạn** — bản dùng thử/OEM có hạn; Bảng điều khiển cảnh
  báo trước khi hết hạn (khối "Việc của bạn"), gia hạn hoặc kích hoạt lại
  TRƯỚC khi máy khoá, không để lỡ giữa lúc đang đăng video.
- **Khởi động lại máy (bảo trì Windows, mất điện...)** — sau khi máy lên
  lại, đợi khoảng 10 phút rồi kiểm bằng `python -m core.kiem_may --day-du`:
  trạm + phiên kênh phải tự sống lại không cần ai mở tay (lịch
  `ShopAPI-TramLucDangNhap` lo việc này). Vẫn không sống lại thì mở MyTool
  bằng tay một lần.
- **Chép/gộp bản vá mới** — chủ dự án gửi thư mục
  `workspace/ban-va/<ngày>-<việc>/` từ máy nhà (qua cách cập nhật của
  `cap-nhat.json`, hoặc chép tay qua RDP với máy chỉ IPv6) — không tự ý sửa
  thẳng mã trên VPS nếu không phải phiên Claude Code đang làm việc đó (xem
  `CLAUDE.local.md`).

### Cảnh báo tự động — máy tự nhắc, bạn chỉ làm theo "Việc cần làm"

Không có bot Telegram: mọi cảnh báo hiện ở (1) khối "Việc của bạn" trên Bảng điều khiển,
(2) `workspace/loi-chay-max.md`, (3) bản tin gác tổng. Bốn thứ được canh (`core/chot_an_toan.py`):

- **Ví ShopAPI** — ví < 1,5 lần chi phí một video thì máy KHÔNG mở video mới (video đang làm dở vẫn
  được làm nốt nếu đủ tiền); nhắc mỗi 4 giờ "Ví sắp hết: còn X₫, đủ khoảng N video — cần nạp", và nhắc
  sớm khi còn dưới 2 ngày sản xuất. Bạn chỉ cần NẠP TIỀN; máy tự chạy lại khi thấy ví đủ.
- **Windows dùng thử** — mỗi ngày máy tự kiểm; còn ≤10 ngày và còn lượt gia hạn (rearm) thì tự gia hạn rồi
  tự khởi động lại lúc máy rảnh (cần Windows đang bật tự đăng nhập). Hết lượt gia hạn thì nhắc trước
  30/14/7 ngày: phải nhập khoá bản quyền Windows.
- **Hạn thuê VPS** — ĐIỀN ngày hết hạn vào `workspace/cai-dat.json`, khoá `"ngay_het_han_vps"`, ví dụ
  `"ngay_het_han_vps": "2027-03-15"` (hoặc `"15/03/2027"`; để trống thì bỏ qua). Máy nhắc trước 14/7/3/1
  ngày. Gia hạn xong nhớ sửa sang ngày mới. (Chưa có ô sửa trong giao diện.)
- **Giọng đọc trùng** — hai kênh tự chạy dùng chung `voice_id` thì báo; máy KHÔNG tự đổi giọng. Gợi ý ở
  `workspace/giong-doc-goi-y.md`.

Không việc nào ở trên cần làm NGAY LẬP TỨC trong vài phút — Bảng điều khiển
luôn hiện sẵn, cứ mở lên mỗi ngày một lần là đủ theo kịp.
