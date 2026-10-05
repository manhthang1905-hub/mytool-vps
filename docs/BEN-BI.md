# Bền bỉ 365 ngày — cái gì chạy khi nào, báo gì, người phải làm gì

Mục tiêu: VPS chạy một năm không người ngồi canh. Hỏng thì tự thử lại; kẹt thì có chỗ phát hiện; việc chỉ người
làm được thì hiện ra rõ. Không bao giờ chết im lặng. Cập nhật 06/10/2026 (v2.157 → v2.165).

## 1. Cái gì chạy khi nào

| Nhịp | Việc | Module |
|---|---|---|
| 15 phút (lịch `ShopAPI-GacTong`) | Gác tổng: chụp trạng thái, tìm sự cố, tự sửa, báo động | `core/gac_tong.py`, `core/ben_bi.py` |
| 10 phút (lịch `ShopAPI-DieuPhoi`) | Bộ điều phối sản xuất; canh nhịp tim của gác tổng | `tu_chay.py --dieu-phoi`, `ben_bi.canh_gac_tong` |
| Vài phút (lịch `ShopAPI-CanhTram`) | Giữ trạm 8765 sống | `core/canh_tram.py` |
| 04:10 (lịch `ShopAPI-Nao`) | Bộ não đọc số, chấm dự đoán, ra quyết định | `nao/CLAUDE.md` |
| Sau 06:30, một lần/ngày | Báo cáo sức khoẻ hằng ngày | `core/bao_cao_ngay.py` |
| 3 giờ một lần (trong gác tổng) | Dọn đĩa: file nặng của video đã lên + xoay `*.log` | `core/don_dia.py` |
| ~30 phút (trong gác tổng) | Kiểm bản mới trên kho, áp lúc máy rảnh | `core/cap_nhat_git.py` |
| Liên tục | Agent đăng/chăm kênh, tự chạy lại khi vòng chính sập | `vm/agent.py` (`chay_ben`) |

## 2. Lưới tự phục hồi (thêm 06/10/2026)

- **Gác tổng bọc lỗi từng bước.** Mỗi bước (chốt an toàn, giám đốc kênh, mở kênh, tự sửa, dọn đĩa, báo cáo
  ngày, cập nhật) có `try` riêng. Một bước hỏng không làm cả lượt chết.
- **Nhịp tim + hạn giờ cứng.** Gác tổng ghi `workspace/gac-tong/nhip.json` mỗi lượt. Một lượt treo quá 40 phút
  tự thoát, để lượt 15 phút sau chạy được. Trước đây một lượt treo làm lịch Windows bỏ qua mọi lượt sau tới 72 giờ.
- **Ai gác người gác.** Bộ điều phối thấy nhịp gác tổng cũ hơn 60 phút thì đăng ký lại lịch gác tổng nếu mất,
  rồi báo động. Gác tổng sập liền thì báo khẩn từ lần thứ hai.
- **Khoá của tiến trình đã chết** được dọn chỉ khi: nội dung tệp lúc xoá vẫn đúng PID đã thấy, PID vẫn chết,
  khoá đủ tuổi. Xoá bằng đổi tên nguyên tử rồi đọc lại; lỡ lấy khoá của tiến trình đang sống thì trả lại.
- **Hồi sinh agent.** Agent chỉ được giao diện nuôi. Giao diện chết thì gác tổng mở lại giao diện; vẫn không lên
  thì mở thẳng agent. Agent im quá 20 phút (60 phút nếu đang tải lên) thì bị dừng để giao diện bật lại.
- **Agent `chay_ben`.** Vòng chính của agent sập thì ghi `vm/logs/agent-sap.json`, chờ lùi dần rồi chạy lại.
  Gác tổng đọc sổ đó và báo nếu sập lặp.
- **Kiểm khói khi cập nhật** giờ import cả các module `vm/` (agent, máy đăng, máy bình luận, tự chữa DOM, thiết
  lập kênh). Không qua thì không áp bản mới. Gác tổng cũng xoá tệp `.py` rỗng ở gốc che mất module `vm/`.
- **Telegram thử lại.** Gửi lỗi (mạng chập) thì thử lại sau 15 phút, nhân đôi mỗi lần lỗi, không quá khoảng lặng
  của loại tin đó. Trước đây tin "kênh 2 ngày không đăng" có thể im 24 giờ dù mạng có lại sau 5 phút.
- **Máy đăng tự chữa DOM** khi Studio đổi giao diện: xem `docs/DANG-VA-BINH-LUAN.md` và `vm/tu_chua_dom.py`
  (tắt bằng `TL_TU_CHUA_DOM=0`).

## 3. Báo động: hai điều kiện thật sự mất tiền

Tin mức khẩn luôn có ba dòng: chuyện gì, bạn cần làm gì, nếu không làm thì sao. Mỗi loại tin báo một lần rồi
nhắc tối đa một lần/ngày khi sự cố còn đó, không dội mỗi 15 phút.

| Sự cố | Ngưỡng | Nơi kiểm |
|---|---|---|
| Một kênh không có video mới | 48 giờ | `gac_tong._kiem_khong_video_moi` |
| Cả máy không làm ra gói video mới | 36 giờ | `ben_bi.kiem_khong_san_xuat` |
| Ổ đĩa sắp đầy | dưới 10 GB: không dựng video mới, báo 24 giờ/lần | `don_dep_mo_rong.van_o`, `gac_tong` |
| Ví AI, license Windows, hạn thuê VPS, giọng đọc trùng | theo `core/chot_an_toan.py` | gác tổng |
| Kênh có dấu hiệu bị phạt (hiển thị sụp, CTR cùng tụt) | 3 cò của `core/giam_doc/suc_khoe.py` | giám đốc kênh, nhắc 1 lần/ngày |
| Kênh gần hoặc đạt YPP (tin tốt, mức nhắc) | 4.000 giờ / 1.000 đăng ký | `core/ypp.py --canh-bao` |

**Quan trọng: báo ra điện thoại cần `bao-dong.json`.** Thiếu tệp này thì `core/bao_dong.py` tắt hẳn, không lỗi.
Khi đó mọi sự cố chỉ được ghi vào `workspace/loi-chay-max.md` và báo cáo ngày `workspace/bao-cao-ngay/<ngày>.md`.
Không ai đọc hai tệp đó thì coi như không có báo động.

## 4. Báo cáo sức khoẻ hằng ngày

`core/bao_cao_ngay.py` viết một bản tin ngắn (≤ ~40 dòng) đọc trên điện thoại. Mục nào hỏng chỉ in một dòng
"không đọc được", không làm vỡ bản tin.

1. Video ngày mai: kênh nào đã có.
2. Skill hỏng hoặc thiếu (`core/ky_nang.py`).
3. Đường tới YPP: dự báo ngày đủ 4.000 giờ / 1.000 đăng ký (`core/ypp.py`, cận dưới vì chỉ thấy cửa sổ 28 ngày).
4. Chiến trường: thị phần, quy mô ngách, đối thủ số 1, lệnh tác chiến. Kèm **tín hiệu học thiếu/cũ** (`docs/VONG-HOC.md` mục 4).
5. Lỗi 24 giờ (từ `workspace/loi-chay-max.md`).
6. Máy: RAM, đĩa, nhịp tim agent.

Lệnh: `python -m core.bao_cao_ngay` (in) · `--ghi` · `--gui`.

## 5. Ổ đĩa đủ cho cả năm

Luật hai câu (`core/don_dia.py`): video đã lên YouTube (sổ `vm/logs/so-video-id.json` xác nhận) thì xoá file nặng
của nó, giữ srt/json/bìa đã chọn; ổ trống dưới 10 GB thì không dựng video mới và báo động. Thêm: `*.log` quá
10 MB được xoay, giữ 3 bản nén. Không đụng `*.jsonl` (sổ dữ liệu tự học đọc).

Gói raw chỉ số Studio cũ hơn 7 ngày được nén gzip (`core/chi_so_ytb/kho_raw.py`, nhỏ ~5 lần, đọc lại y hệt;
ghi ở CHANGELOG 2.164.0, mã còn chờ gộp vào nhánh chính lúc viết tài liệu này). Raw
không được xoá vì công thức chọn nguồn và giải mã còn đọc lại. Đo 06/10: raw ~90 MB/ngày ≈ 33 GB/năm nếu không nén.

Lệnh: `python -m core.don_dia --thu` (chỉ tính) · `--that` (dọn thật). Xoá thật vẫn sau cờ `tu_don` của từng kênh.

## 6. Việc người phải làm

- [ ] **Tạo `bao-dong.json`** ở gốc MyTool (cạnh `config.json`) với `telegram.bot_token` + `telegram.chat_id`,
      hoặc `webhook.url`. Mẫu trong docstring `core/bao_dong.py`. Tệp này không lên kho.
      Kiểm máy chỉ có IPv6 có tới được Telegram không: `python -m core.bao_dong --kiem`.
- [ ] **Đọc báo cáo ngày** mỗi sáng (Telegram, hoặc `workspace/bao-cao-ngay/<ngày>.md`).
- [ ] **Xem cảnh báo chính sách trên Studio** khi được nhắc: gậy, "nội dung dùng lại". Giám đốc kênh đã đóng
      băng thay đổi tự động của kênh đó cho tới khi số hồi lại. Máy không tự xử lý việc này.
- [ ] **Giọng đọc (`voice_id`)**: hai kênh dùng chung một giọng thì chọn giọng khác và sửa `kenh.yaml`. Máy chỉ
      cảnh báo, không tự đổi.
- [ ] **Ví AI, license Windows, hạn thuê VPS**: nạp tiền, nhập khoá, điền `ngay_het_han_vps` vào `workspace/cai-dat.json`.
- [ ] **Xác minh tài khoản Google** (điện thoại, CAPTCHA, đăng nhập lại) khi máy dừng ở `can_nguoi`.
