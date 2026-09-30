# Nghiên cứu bìa (thumbnail): bìa là vé vào cửa, không phải đòn bẩy

Nghiên cứu đo trên ngách tâm lý / não khoa học tiếng Nhật (30/09/2026). Kết luận và phương pháp dùng lại được cho ngách khác; số cụ thể chỉ là minh hoạ.

## Phương pháp (chép lại được cho ngách khác)

- **Chỉ học từ ảnh bìa THẬT trên YouTube** (`https://i.ytimg.com/vi/<id>/maxresdefault.jpg`, lùi về `hqdefault`), không học từ tệp tool tự làm — chủ kênh có thể đăng tay hoặc đổi bìa trên Studio, nên CTR thuộc về ảnh đang hiển thị. So sha1 với bản tool làm để biết.
- **Mẫu đối thủ:** gộp sổ content đối thủ, bỏ trùng; chỉ lấy kênh "theo dõi" đã qua kiểm ngách bằng LLM; video 14–365 ngày tuổi, dài > 8 phút; kênh có ≥ 5 video.
- **Nhãn nổ/thường tính trong từng kênh:** r = view ÷ trung vị view của chính kênh đó. Nổ: r ≥ 5; thường: 0,5 ≤ r ≤ 1,5. Lấy mẫu phân tầng, mỗi kênh tối đa 8 video mỗi nhóm (mẫu đã chạy: ~250 nổ và ~250 thường từ ~100 kênh).
- **Gắn nhãn thị giác bằng LLM nhìn ảnh** (qua ShopAPI, cùng đường với bộ chấm bìa), mỗi lần 6 ảnh, cache theo sha1 ảnh, mô hình không biết ảnh thuộc nhóm nào. Tệp người xem gán theo nghĩa từ tiêu đề.
- **Kiểm độ ổn định nhãn:** gắn lại một lô ở lần khác rồi so. Kết quả: cấu trúc chữ (số tầng, chữ trần, cặp màu) khớp ~98%; độ sáng nền, vị trí nhân vật ~92%; quầng sáng ~85%; **màu nền ~73% và sắc thái ~62% → đọc thận trọng**.
- **Kiểm nhiễu bằng hoán vị:** thử mọi tổ hợp 2–3 đặc trưng, rồi hoán vị nhãn nổ/thường trong từng kênh vài lần. Chỉ tin tổ hợp vượt hẳn nền nhiễu.

## 1. Phát hiện chính: đặc trưng bìa KHÔNG tách được video nổ khỏi video thường

- Trên ~80 đặc trưng, lift đều nằm trong khoảng 0,70–1,27; chỉ 2 đặc trưng đạt p < 0,05, trong khi riêng may rủi đã cho ~4.
- ~15.000 tổ hợp 2–3 đặc trưng: số tổ hợp "có ý nghĩa" trên dữ liệu thật **không vượt** số trên dữ liệu hoán vị → không có "tổ hợp thắng" đáng tin.
- Chữ trên bìa (*実は, 正体/理由, dấu ？, con số, câu bỏ lửng*) cũng không phân biệt được hai nhóm.
- **Vì sao:** mỗi kênh mang một "bộ áo" cố định (trong cùng kênh, 64% bìa cùng màu nền, so với 29% trên cả mẫu). Nổ hay không do **đề tài và tiêu đề**, không do bộ áo.

Tín hiệu yếu (nghiêng, chỉ để tham khảo, đo trong kênh bằng Mantel–Haenszel):

| hướng | đặc trưng |
|---|---|
| hơi tốt | sắc thái nhẹ nhàng; nhân vật cười; chữ có màu xanh; chữ đỏ; tầng chữ dưới cùng lớn nhất |
| hơi xấu | nhân vật mặt buồn (lift 0,70); quầng sáng; sắc thái bí ẩn; tô màu khác cho từ khoá |
| rõ nhất | **nền tối + nhân vật mặt buồn**: tỉ lệ nổ chỉ ~0,38× nền (p ≈ 0,003) → tránh |

## 2. Bằng chứng trên chính kênh mình: cùng tiêu đề, khác bìa, CTR như nhau

- Cùng một đề tài/tiêu đề làm trên hai kênh với hai khuôn bìa khác hẳn (một tím đen quầng sáng chữ trần; một nền cam chữ trắng trong khối đỏ 3 tầng) → CTR gần bằng nhau (~8,9% và ~8,7%).
- Khuôn "thắng" của kênh này đặt lên đề tài khác → CTR rơi còn ~4%.
- → **CTR đi theo đề tài + câu chữ, không đi theo khuôn.**

## 3. Tách theo tệp người xem (n nhỏ, chỉ là gợi ý)

Mỗi tệp khán giả có thể có sở thích bìa riêng, ví dụ trong ngách tâm lý Nhật:
- tệp "lệch nhịp" (TL4): mặt cười, chữ lớn nhất 22–29% chiều cao nổi lên; nền tối chìm;
- tệp "IQ" (TL3): nền sáng, người que nổi lên; **quầng sáng chìm**;
- tệp "tò mò" (TL1): nhân vật bên trái, ≥ 3 màu chữ nổi lên; **2 tầng chữ chìm**;
- tệp "trung niên" (TL2): ≥ 3 màu chữ, đỏ+vàng nổi lên; **chữ dồn một bên chìm**.

## 4. Chuẩn ngách vs bìa kênh mình

Đo tỉ lệ phổ biến của từng đặc trưng trong ngách (trung bình hai nhóm, vì hai nhóm gần như bằng nhau), rồi so với bìa từng kênh. Ngách tâm lý Nhật: chữ trần không khối ~80%, có chữ vàng ~78%, tô màu từ khoá ~78%, nhân vật minh hoạ ~80%, chữ đen chỉ ~16%.

Các kênh mình lệch chuẩn ngách rõ (chữ trong khối, nền trơn trắng, chữ đen, mặt bình thản). Kênh lệch nhiều nhất cũng có CTR thấp nhất. Kênh đã thắng dùng một khuôn cố định, và khuôn không khác nhau giữa video rất lớn và video yếu — lại một bằng chứng bìa không phải đòn bẩy.

## 5. Kết luận thực hành

1. **Chuẩn ngách là lớp nền bắt buộc** (vé vào cửa): chữ lớn 22–29% chiều cao, 2–3 tầng, tầng dưới lớn nhất, đọc được ở 120 px; với ngách tâm lý Nhật thêm: chữ trần viền dày, vàng/trắng, từ khoá tô màu, cảnh minh hoạ cụ thể, nhân vật có biểu cảm; chữ bìa ngắn (tệp lớn tuổi, xem trên TV).
2. **Mỗi kênh giữ bộ áo riêng**, học từ số của chính nó; không chép khuôn kênh này sang kênh khác.
3. **Đòn bẩy CTR nằm ở đề tài và câu chữ trên bìa.**
4. Khuôn thắng của kênh: khai thác vừa phải (đa số video theo khuôn, ~1/5 thử kiểu khác).
5. Muốn biết khuôn nào thắng cho một kênh, chỉ có một cách: **A/B bằng Test & Compare của YouTube trên chính kênh đó.**
6. Mọi khuôn/lời nhắc bìa mới phải qua vòng: khuôn → tạo thử ảnh thật → chấm theo các trường cấu trúc → xem contact sheet bằng mắt → mới áp vào sản xuất.
