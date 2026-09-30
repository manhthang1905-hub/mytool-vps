# Đổi chủ đề / ngách (niche)

Dành cho người vận hành muốn một kênh MỚI đi chủ đề khác hẳn "tâm lý" (ví dụ
tài chính, sức khoẻ, lịch sử...). Đọc kỹ mục 0 trước khi bắt đầu — hiện tại
việc đổi ngách đòi sửa TAY nhiều tệp, chưa có một công tắc duy nhất.

## 0. Hiện trạng: chưa có "hồ sơ ngách" — phải sửa tay

Tool hôm nay có SẴN một số hằng số gắn cứng với công thức "tâm lý × khán giả
Nhật Bản" (điểm chấm nội dung, câu hỏi nghiên cứu, mẫu tiêu đề...) rải rác ở
vài tệp lõi (`core/cong_thuc_v7.py`, `core/cong_thuc_v7_ai.py`,
`core/phan_tuyen.py`, `core/trang_chu.py`, `core/chot_doi_thu.py`,
`core/tram.py`, `core/trung_tam.py`, `core/tuyen_con.py`,
`core/tuyen_noi_dung.py` — xem mục "Chặn phát hành A1-A5" trong
`workspace/LO-TRINH-PHAT-HANH-V3.md`).

**Một "hồ sơ ngách" gom hết các hằng số này vào một tệp cấu hình dễ đổi
(`core/ho_so_ngach.py` + `CHANNEL/_NHOM/<nhóm>/ngach.yaml`) SẼ CÓ Ở v3.0 Đợt
4 — chưa có ở bản này.** Tới lúc đó, đổi ngách nghĩa là đổi PROMPT + hồ sơ
ngách bên dưới, còn công thức chấm điểm/chọn nguồn vẫn nghiêng về khuôn tâm
lý hiện tại — kênh ngách khác vẫn CHẠY được, nhưng câu hỏi nghiên cứu và
tiêu chí chấm điểm sẽ cần bạn tự đọc và sửa cho khớp chủ đề mới (không tự
động 100% như đổi trong cùng ngách tâm lý).

## 1. Prompt kênh — nơi thật sự quyết định nội dung

Mỗi kênh có một cây prompt riêng ở `CHANNEL/<mã kênh>/prompt/` (chép từ kênh
mẫu lúc "Thêm kênh", xem `docs/THEM-KENH.md`). Đây là chỗ SỬA THẬT khi đổi
chủ đề — không cần đụng tới `core/`:

- `1-tieu-de.md` — cách đặt tiêu đề, từ khoá SEO của ngách mới.
- `2-viet.md` / `2b-cham.md` / `2c-hoan-thien.md` / `2d-hook.md` /
  `2e-cham-hook.md` — khung viết kịch bản, tiêu chí chấm điểm nội dung, cách
  mở bài (hook). Đây là phần TỐN CÔNG SỬA NHẤT khi đổi ngách — công thức
  chấm điểm hiện nghiêng theo nội dung tâm lý (mục 0), đổi sang tài
  chính/sức khoẻ... cần viết lại tiêu chí "bài hay là bài thế nào" cho đúng
  ngách mới.
- `3-sua.md` — vòng tự sửa sau khi có bản nháp.
- Thư mục `chien-luoc/` (`cover/`, `sang-tao/`) — chiến lược chọn ảnh
  bìa/tiêu đề theo A/B, giữ nguyên khung, chỉ đổi TỪ KHOÁ cho khớp ngách.

Cách làm AN TOÀN nhất: "Thêm kênh" chép nguyên một kênh mẫu, rồi sửa TỪNG
tệp prompt ở trên theo ngách mới — đọc `DOC-TRUOC.md`/`nganh.yaml` (nếu còn
trong kênh mẫu bạn chép) để hiểu khung trước khi sửa lời.

## 2. Hồ sơ ngách — kế hoạch, chưa dùng được ở bản này

Xem mục 0. Khi Đợt 4 hoàn tất, cách đổi ngách sẽ là: tạo
`CHANNEL/_NHOM/<nhóm mới>/ngach.yaml` khai câu hỏi nghiên cứu + tiêu chí
chấm điểm của ngách đó, gán kênh vào nhóm này — không cần sửa `core/` nữa.
Tài liệu này sẽ cập nhật lại đúng bước khi việc đó xong.

## 3. Kho nhạc

`PROJECTS/music` (kho nhạc nền Suno gốc, KHÔNG được sửa/xoá — luật 1 của
`CLAUDE.md`) và bản đã chuẩn hoá `workspace/kho-nhac/` (`core/kho_nhac.py`)
hiện DÙNG CHUNG cho mọi kênh, không lọc theo ngách/tâm trạng — phù hợp với
các ngách hiện có (đều thiên về nội dung trầm, suy ngẫm). Đổi sang một ngách
khác hẳn không khí (ví dụ hài hước, năng lượng cao) thì kho nhạc hiện tại có
thể không hợp — cân nhắc thêm nhạc mới vào `PROJECTS/music` và chạy lại
`python -m core.kho_nhac` để chuẩn hoá, hoặc tắt nhạc nền cho kênh đó trong
lúc chờ kho nhạc lọc theo ngách (chưa xây).

## Tóm tắt: đổi ngách hôm nay làm được tới đâu

| Việc | Làm được ngay | Cần Đợt 4 |
|---|---|---|
| Nội dung/tiêu đề/hook theo ngách mới | Có (sửa `prompt/`) | — |
| Câu hỏi nghiên cứu, tiêu chí chấm điểm đúng ngách | Một phần (nghiêng khuôn tâm lý) | Có |
| Chọn nguồn/đối thủ không dùng hằng số tâm lý/Nhật | Không | Có (`ho_so_ngach.py`) |
| Giọng đọc/ngôn ngữ khác | Có (`voice_id`, `ngon_ngu` trong `kenh.yaml`) | — |
| Nhạc nền hợp không khí ngách mới | Một phần (kho chung) | Có thể cần thêm nhạc tay |
