# chia-se/bai-hoc/: bài học ngách dùng chung giữa các VPS

Trong thư mục này, mỗi máy có một tệp riêng cho mỗi ngách, đặt tên
`<ma-may>-<ngach>.json`. Không máy nào ghi vào tệp của máy khác, nên các lần
push không xung đột nhau.

- Tệp được **ghi** bởi `python -m core.dong_bo_git bai_hoc`. Lệnh này cũng tự
  chạy trong mỗi lần `day`. Nó gom các bài học phạm vi kênh có n ≥ 3 từ
  `core.chien_luoc.bai_hoc` của mọi kênh cùng ngách trên máy. Câu nào có tên
  kênh thật, video id, URL hoặc email thì bị bỏ.
- Tệp được **đọc** khi `python -m core.dong_bo_git keo` nhận bản mới. Lúc đó
  tệp của máy khác cùng ngách được chép vào `CHANNEL/_NHOM/<ngach>/bai-hoc-ngoai/`.
  `bai_hoc._tu_ngoai` đọc chúng làm tiên nghiệm "ngoài", loại yếu nhất: chỉ
  dùng khi kênh chưa có số riêng trên trục đó.

Định dạng: `{"ma_may", "ngach", "xuat_luc", "bai_hoc": [{"truc", "cum", "cau", "n", "dung_cho"}]}`.
