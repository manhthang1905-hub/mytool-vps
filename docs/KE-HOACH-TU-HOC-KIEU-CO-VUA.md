# Kế hoạch: tool tự học kiểu cờ vua (AlphaZero cho YouTube)

Bản 20/10/2026. Mục tiêu sống còn do chủ đặt: **mọi kênh của nhóm vào top 10 ngách và chiếm thị phần**. Có 10 kênh thì 10 kênh nằm trong top 10.

## 1. Điều kiện thắng phải đo được

- **Ngách và thước đo** lấy theo trang Chiến trường của bảng 8790 (`/chien-truong.json`, mã `core/truc_quan`):
  - 468 kênh đối thủ trực tiếp, 7.560 video, chia thành 32 vùng đề tài.
  - View/tháng của đối thủ ước tối thiểu theo tốc độ tăng. View của phe ta là số 28 ngày thật lấy từ Studio.
- **Thước đo chính:** hạng của từng kênh theo view/tháng trong ngách, và thị phần của cả nhóm.
- **Mốc 20/10:**
  - Ngách khoảng 139 triệu view/tháng và đang lớn: 95 triệu ngày 06/10, 139 triệu ngày 20/10.
  - Kênh số 1 có 20 triệu view/tháng (14,1%). **Ngưỡng top 10 khoảng 3,2 triệu view/tháng.**
  - Phe ta có 317.000 view/tháng, tức **0,23% thị phần**, gần như đứng yên trong 2 tuần (0,22–0,31%).
  - Theo view 28 ngày: TL2 142.000, TL4 101.000, TL3 60.000, TL1 25.000, TL6 3.000.
  - **Kênh tốt nhất phải tăng khoảng 22 lần mới chạm top 10.**
- **Đây là thị trường ăn theo video nổ.** Ví dụ một video đối thủ đạt 610.000 view sau 5 ngày; video tốt nhất của ta khoảng 47.000 view. Muốn vào top phải tăng xác suất ra video nổ trên mỗi video, rồi nhân với số video:
  - **đề tài:** radar của phòng thí nghiệm cho 44% video nổ, so với 6% khi chọn ngẫu nhiên;
  - **đóng gói:** tiêu đề và bìa, để tăng CTR;
  - **giữ chân:** để được đề xuất ở trang chủ và cột đề xuất.
- **Vùng cơ hội lớn nhất:**
  - "tuổi tác là nhân vật chính": 37 triệu view/tháng, ta chỉ có 0,09%;
  - "Trí tuệ/IQ": 17 triệu, ta 0,23%;
  - "Người độc hại": 10 triệu, ta khoảng 0%;
  - "Nhân cách và tính cách": 11 triệu, ta chưa có kênh nào.
- **Đường tới YPP** (1.000 đăng ký + 4.000 giờ xem):
  - TL4 có 8.009 giờ và 758 đăng ký;
  - TL2 có 5.000 giờ và 377 đăng ký.
  - Nút thắt là **đăng ký**, không phải giờ xem.
- **Ví:** khoảng 200.000đ/video, chi 1,1–1,4 triệu đồng/ngày, đủ khoảng 33 ngày ở mức hiện tại. Tăng số video thì chi tăng theo.

## 2. Bài học AlphaZero và chỗ khác của YouTube

AlphaZero có 4 phần:
1. **Chính sách:** đề xuất nước đi.
2. **Hàm giá trị:** đoán thắng hay thua.
3. **Tìm kiếm:** thử nhiều nước, chọn nước theo hàm giá trị.
4. **Tự chơi:** chơi hàng triệu ván để có dữ liệu, rồi học lại từ đó.

Áp vào tool:

| Phần | Bên cờ vua | Bên tool YouTube |
|---|---|---|
| Chính sách | mạng chính sách | LLM sinh ứng viên: đề tài, tiêu đề, kịch bản, bìa |
| Hàm giá trị | mạng giá trị | **ĐANG THIẾU.** Hiện là LLM chấm theo ý kiến, đo 20/10 thấy gần như không dự báo được: bìa −0,39, hook 0,12, kịch bản 0,15 |
| Tìm kiếm | MCTS | best-of-N, nhưng đang chọn bằng LLM chấm |
| Tự chơi | hàng triệu ván/ngày | khoảng 10 ván/ngày, kết quả trễ 2–7 ngày và nhiễu |

Cách vượt chỗ khác biệt:
- **Học từ ván của người khác.** Mỗi kênh đã có khoảng 26.000 video đối thủ kèm view, tốc độ tăng, ngày đăng, thời lượng và ảnh bìa (`nghien-cuu/content.csv`, `kenh-do.json`). Tức là hàng trăm nghìn ván đã có kết quả.
- **Mỗi video thành 3 ván sạch:** dùng A/B của YouTube (Thử nghiệm và so sánh: 3 bìa hoặc 3 tiêu đề trên cùng một video, cùng thời điểm).
- **Tín hiệu sớm:** dùng số ở mốc 2 giờ và 24 giờ để đoán kết quả 7 ngày, học nhanh hơn 3–5 lần.

## 3. Việc cần xây (xếp theo ảnh hưởng)

| Mã | Việc | Vì sao | Cỡ |
|---|---|---|---|
| G1 | Bảng điểm thắng: trang Chiến trường đã có thị phần và vùng. Cần thêm hạng từng kênh, khoảng cách tới top 10, mục tiêu tuần, và báo khi thị phần đứng yên | Không đo được thì không tối ưu được. Thị phần đứng yên 2 tuần mà máy không phản ứng | S |
| G2 | **Hàm giá trị học máy:** đoán "độ nổ" (view so với trung vị của kênh, theo quy mô kênh) của đề tài + tiêu đề + bìa + thời lượng. Huấn luyện trên video đối thủ và Studio của mình, chạy cục bộ (onnxruntime + mô hình nhúng đa ngôn ngữ nhỏ), kiểm trên dữ liệu giữ lại, hiệu chuẩn hằng tuần bằng D22 | Đây là trái tim của AlphaZero. Thay "ý kiến LLM" bằng "dự đoán học từ kết quả thật" | M–L |
| G3 | Tìm kiếm bằng hàm giá trị: sinh 20–50 đề tài/tiêu đề và 30 bìa, chọn theo G2 kèm thăm dò (Thompson). LLM chỉ còn sinh ứng viên và gạt lỗi cứng | Chọn nước bằng hàm giá trị đã hiệu chuẩn | M |
| G4 | "Tự chơi": A/B 3 bìa (và tiêu đề) cho MỌI video, MỌI kênh; thu kết quả vào sổ học | Nhãn sạch nhất và nhiều nhất có thể có | M |
| G5 | Tín hiệu sớm: số 2h/24h → đoán kết quả 7 ngày. Video hỏng sớm thì đổi bìa/tiêu đề trong 24 giờ | Rút ngắn vòng học, cứu video sớm | M |
| G6 | Mô hình giữ chân: hook, nhịp, độ dài so với đường giữ chân (`retention.xlsx`). Hook kể chuyện đã thấy hơn kênh 6–8 điểm ở giây 30 | Giữ chân kéo đề xuất và thời gian xem | M |
| G7 | Chiến lược danh mục: mỗi kênh một vị trí riêng (tệp khán giả, ngách con), bản đồ đề tài cung–cầu (nhiều view, ít người làm), chia đề tài giữa các kênh, kéo chéo có đo | 10 kênh chiếm thị phần mà không ăn thịt nhau | M |
| G8 | Học chuyển giao: một mô hình chung cho nhóm, hiệu chỉnh theo từng kênh. Kênh mới khởi đầu bằng kinh nghiệm của kênh cũ, mở rộng được sang ngách khác | Mở rộng 10 kênh, nhiều VPS | M |
| G9 | Nhiều ván hơn: kênh có hàm giá trị tốt lên 2 video/ngày khi công suất cho phép (6 làn, đĩa đủ khoảng 31 video/ngày) | Nhiều ván thì học nhanh, có nhiều cửa trúng | S |
| G10 | An toàn sống còn: chính sách YouTube (nội dung dùng lại, AI), cổng độc đáo, theo dõi cảnh báo kênh, tự thay kênh hỏng (D20) | Không chết thì mới thắng | S |

## 4. Lộ trình

1. **Tuần 1:**
   - G1 bảng điểm thắng.
   - G2 bản 1 cho đề tài và tiêu đề, kiểm offline trên dữ liệu giữ lại.
   - Bắt đầu thu dữ liệu G5.
2. **Tuần 2–3:**
   - G3 tìm kiếm đề tài/tiêu đề bằng G2.
   - G4 A/B bìa cho mọi video.
   - G2 bản bìa.
3. **Tuần 3–5:** G6, G7, cứu video sớm (G5).
4. **Từ tuần 5:** G8, G9; tự hiệu chuẩn và tự tối ưu liên tục.

Thước đo nghiệm thu:
- G2 đạt Spearman ≥ 0,4 trên dữ liệu giữ lại, và hơn LLM chấm trên video thật của mình.
- CTR trung vị bìa mới ≥ trung vị bìa thắng.
- Hạng và thị phần ngách tăng mỗi tuần.

## 5. Giới hạn (nói thẳng)

- Kết quả YouTube nhiễu và trễ, và mình ít ván. Không thể học nhanh như cờ vua, nên phải dựa vào ván của đối thủ và A/B.
- Model chữ của ví ShopAPI là model rẻ (chủ chọn giữ, 20/10). Vì vậy hàm giá trị phải là mô hình học từ số liệu, không phải LLM.
- Thuật toán YouTube thay đổi, nên phải hiệu chuẩn lại hằng tuần.
- Không có gì bảo đảm 10/10 kênh vào top 10. Điều làm được là đo, tối ưu và tiến lên mỗi tuần.
