# Trung tâm chỉ huy (cổng 8770)

Trang web **chỉ đọc** cho chủ dự án thấy cả VPS trong một chỗ: chiếm được bao nhiêu thị phần ngách, dây
chuyền hôm nay tới đâu, bộ não đang nghĩ gì. Trang không bấm, không sửa, không gọi AI, không tiêu tiền.
Cập nhật 06/10/2026.

## Mở trang

- Bấm đúp `MO-TRUNG-TAM.bat` ở gốc MyTool. Tệp bật máy chủ nhỏ nếu chưa chạy rồi mở `http://127.0.0.1:8770/`.
- Hoặc dòng lệnh: `python -X utf8 -m core.truc_quan` (`--cong 8771` đổi cổng, `--json` chỉ in dữ liệu để kiểm).
- Máy chủ chỉ nghe `127.0.0.1` và tách hẳn khỏi trạm 8765 của MyTool. Tắt nó không ảnh hưởng sản xuất hay đăng.

| Đường dẫn | Tab | Dữ liệu (JSON) | Module |
|---|---|---|---|
| `/` | Chiến trường | `/chien-truong.json`, `/chien-truong-lich-su.json` | `core/chien_truong.py`, `core/chien_truong_ai.py`, `core/chien_truong_lich_su.py` |
| `/hau-can` | Hậu cần | `/du-lieu.json` | `core/truc_quan.py` |
| `/nao` | Não | `/nao.json` (nhớ đệm 5 phút) | `core/nao_truc_quan.py` |

Trang HTML nằm ở `ui_web/` (`chien-truong.html`, `truc-quan.html`, `nao.html`).

## Tab 1 — Chiến trường: chiếm ngách như chiếm đất

YouTube trong một ngách là một trận chiếm thị phần: khán giả có hạn, ai có video đúng đề trước thì được xem.
Tab này cho biết đất nào lớn, ai đang giữ, ta giữ bao nhiêu và nên đánh vào đâu tiếp.

```
 NGÁCH (vd "tâm lý Nhật")  = nhiều VÙNG (cụm đề tài)
 ┌────────────┬────────────┬────────────┬────────────┐
 │ Vùng 1     │ Vùng 2     │ Vùng 3     │ Vùng AI mới│   đất mỗi vùng = lượt xem video ĐỐI THỦ 28 ngày
 │ địch 70%   │ địch 95%   │ trống      │ địch 60%   │   phần ta      = lượt xem video của TA trong vùng
 │ ta   30%   │ ta    5%   │            │ ta   40%   │   thị phần     = ta / (ta + địch)
 └────────────┴────────────┴────────────┴────────────┘
 Lệnh tác chiến: kênh A → vùng 2 · kênh B → vùng 3 · kênh C → vùng 1   (toả ra, không dồn một vùng)
```

| Khối trên trang | Nghĩa |
|---|---|
| Bản đồ thị phần | Mỗi vùng: quy mô (lượt xem đối thủ 28 ngày), thị phần ta, kênh địch dẫn đầu |
| Thị phần ta theo ngày · Quy mô ngách theo ngày | Ảnh chụp mỗi ngày một lần (tắt bằng `MYTOOL_CHIEN_TRUONG_GHI=0`) |
| Điểm nóng (14 ngày) | Video đối thủ mới đang tăng nhanh nhất (lượt xem/ngày) |
| Bảng xếp hạng | Đối thủ và kênh ta xếp theo thị phần |
| Lệnh tác chiến | Mỗi kênh ta 2 vùng nên đánh, kèm lý do |
| Quân ta (28 ngày) | Sức từng kênh: giờ xem, người đăng ký, mặt trận đang đánh |

Cách tính, đọc từ docstring:

- **Vùng** là bộ cụm đề tài của vòng tự học (`cong_thuc_v7.cum_cua_tieu_de`). Khoảng 55% lượt xem ngách rơi
  vào "Đề tài khác" vì từ khoá không nhận ra. `core/chien_truong_ai.py` cho AI xếp các video đó vào vùng theo
  nghĩa, hoặc đặt **vùng mới**. Mỗi video chỉ hỏi AI một lần (`workspace/chien-truong/vung-ai.json`).
- **Điểm cơ hội** 0–100 mỗi vùng = 100 × (0,35·cầu + 0,25·đà + 0,20·địch yếu + 0,20·thế chân của ta).
- **Lệnh chia đất**: cấp lệnh theo cặp (kênh, vùng) điểm cao nhất trước. Vùng đã cấp cho kênh khác bị trừ điểm,
  nên các kênh phủ cả ngách thay vì đánh nhau trong một vùng.
- Lệnh ghi vào `workspace/chien-truong/tan-cong.json` và **đi vào chọn nội dung** (`core/chien_luoc/tan_cong.py`):
  ứng viên thuộc vùng được lệnh nhân điểm tối đa ×1,3. Đây là trọng số mềm, không loại ứng viên nào. Tệp
  lệnh cũ quá hạn thì không áp gì.
- Tên ngách và đề bài AI lấy từ `ngach.yaml`, nên máy chủ đề khác tự đúng, không có mã kênh viết cứng.

## Tab 2 — Hậu cần: dây chuyền và máy

- **Dây chuyền hôm nay**: mỗi khối là video **ngày mai** của một kênh, đứng ở một trạm: chờ mở cửa sản xuất →
  nghiên cứu → sản xuất (8 khâu, ô xanh/vàng/đỏ = xong/đang/lỗi) → bàn giao → chờ tải lên → đã hẹn 05:00.
  Kênh sản xuất ở máy khác hiện riêng.
- **Chi tiết kênh**: bấm một kênh để xem lượt sản xuất và trạng thái của nó.
- **Lỗi cần chú ý (24 giờ)** và **Sự kiện agent** (nhật ký của agent đăng/chăm kênh).
- Nguồn: kế hoạch đăng, lượt sản xuất, điều phối, quét ngày, danh mục skill, nhật ký. Chỉ đọc.

## Tab 3 — Não: thấy bộ não nghĩ, đoán, bị chấm và học

| Khối | Đọc từ |
|---|---|
| Bảng điểm, tỉ lệ đúng theo ngày chấm (cộng dồn) | `nao/hanh-dong.json` |
| Dòng suy nghĩ của phiên gần nhất | `nao/nhat-ky/phien-*.log` |
| Hành động: dự đoán, ngày kiểm, kết quả chấm đúng/sai | `nao/hanh-dong.json` |
| Trí nhớ | `nao/tri-nho/`, `nao/ky-nang/` |
| Bài học đang áp | `CHANNEL/<kênh>/giam-doc/bai-hoc.jsonl` |

Trang Não không ghi tệp nào. Mỗi khối có `try` riêng: một khối hỏng chỉ hiện `loi`, các khối khác vẫn hiện.
Chuỗi đưa ra ngoài đều qua bộ che khoá.

## Khi trang trống hoặc báo lỗi

- `thiếu ui_web/<tên>.html`: bản cài thiếu thư mục `ui_web/`. Cập nhật tool.
- JSON trả `{"loi": ...}`: một nguồn hỏng, thường là sổ dữ liệu chưa có (kênh mới, máy mới). Sản xuất không bị ảnh hưởng.
- Chiến trường trống: chưa có `nghien-cuu/content.csv` hoặc `chi-so/bang-tom-tat.csv`. Đợi một lượt nghiên cứu và một lần quét ngày.
