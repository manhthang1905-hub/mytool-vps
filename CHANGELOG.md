# Nhật ký phát hành

Rút gọn từ `NHAT-KY-PHAT-TRIEN.md` (nhật ký chi tiết máy — mỗi mục có ngày,
lý do sửa, tệp đụng tới, kết quả test). Tệp này chỉ ghi TÍNH NĂNG CHÍNH, cho
người cần biết "bản mới có gì" mà không cần đọc hết nhật ký chi tiết.

## Các bản đẩy lên kho chung (tự ghi bởi `dong_bo_git day`, mới nhất ở trên)

- **2.149.4** — 2026-10-04 — `vps-jp1` — Quet ngay: chi cao trang chu kenh tin cay (kenh.yaml trang_chu_tin_cay: true, hoac lan do nuoi trang chu gan nhat > 90% chu de) - trang chu kenh moi linh tinh la du lieu rac
- **2.149.3** — 2026-10-04 — `vps-jp1` — Kiem DOM: kenh moi chua co video thi danh sach trong khong bi bao HONG hang_video/hang_tieu_de
- **2.149.2** — 2026-10-04 — `vps-jp1` — Quet ngay: kenh moi chua co video nao thi khong coi la CHUA DU (tranh quet lai 3 lan/ngay giu Chrome + khe nang vo ich)
- **2.149.1** — 2026-10-04 — `vps-jp1` — Ghep kenh vao may dang: kenh chua co may-ao.json tu bat tu_dang + cach_dang tu_dong (4 kenh moi lam xong video ma may dang bo qua)
- **2.149.0** — 2026-10-04 — `vps-jp1` — Tu dong hoa dot 1: loc Viec cua ban (cho so -> nhat ky, xem Studio -> bo nao), giam doc tu nang/ha quyen theo thanh tich, cuu_ctr tu ap kenh <1000 sub, de-xuat nao het han 7 ngay, lich tat tu dang ky lai
- **2.148.4** — 2026-10-04 — `vps-jp1` — Bo nao: de cu uu-tien-nguon chi tinh da dung khi link that su co trong danh sach ung vien; vang 3 luot thi dong khong tinh diem
- **2.148.3** — 2026-10-04 — `vps-jp1` — xep_lich: goi 'Bo' khong giu khe va khong tinh vao kho dem (TL6-T7-K2 bo vi trung nguon van chan san xuat)
- **2.148.2** — 2026-10-04 — `vps-jp1` — fix: chong trung nguon khi nhan nuoi luot mo coi + luot thu khong thanh mo coi
- **2.148.1** — 2026-10-04 — `vps-jp1` — thiet_lap_kenh: doc lai handle theo trang cong khai, doi o anh dung cham, sua bo chon danh sach phat
- **2.148.0** — 2026-10-04 — `vps-jp1` — Thiet lap kenh tu dong (core/thiet_lap_kenh ho so: ten/handle/mo ta SEO/tu khoa/danh sach phat/mac dinh tai len + logo/banner/hinh mo; vm/thiet_lap_kenh_dom dien Studio, doc lai xac nhan, chi doi muc khac, luat doi ten/handle; agent tu cha…
- **2.147.1** — 2026-10-03 — `vps-jp1` — Nuoi trang chu: chong loi NoneType khi trinh phat chua nap/dang quang cao
- **2.147.0** — 2026-10-03 — `vps-jp1` — Nuoi trang chu (cong tac nuoi_trang_chu): Chrome kenh xem video doi thu THANG (view>=30k va >=2x trung vi kenh do, <=60 ngay), 70% ngach/30% chu de, tat tieng, thoi luong ngau nhien, Khong quan tam muc lac de; dat >90% chu de thi tu tat; s…
- **2.146.0** — 2026-10-03 — `vps-jp1` — Bo nao (kieu Hermes/Claude Code): core/nao.py CLI an toan (thu/tranh/bai-hoc/uu-tien-nguon/de-xuat, gioi han + quyen theo ti le dung, ngay kiem >= luc co so 48h), phien Claude Code headless 04:10 hang ngay (ShopAPI-Nao), nao/CLAUDE.md 6 bu…
- **2.145.0** — 2026-10-03 — `vps-jp1` — Vong tu hoc dot 3: so bai hoc co bo dem cong/tru (kieu ExpeL/ACE, delta <=3 thao tac/video, that khi >=3 video xac nhan, chu gach = bo); hieu chinh du doan bien tap (lech CTR/AVD, ti le dung) dua vao loi nhac + so do chinh xac
- **2.144.0** — 2026-10-03 — `vps-jp1` — Vong tu hoc dot 2: truc kieu_tieu_de + hook (nhan theo nghia do LLM tra kem luc cham, regex chi la duong lui), Thompson he so 0.9-1.1 khi chon tieu de/hook/kieu bia, ghi nhan vao ho so + van
- **2.143.0** — 2026-10-03 — `vps-jp1` — Vong tu hoc dot 1 (kieu AI co vua): core/tu_hoc ghi van (nuoc di + du doan) luc ban giao, cham ket qua 48h/7 ngay (gio xem), bang diem Beta + tien nghiem nhom, Thompson sampling he so cum 0.8-1.2 trong xep hang nguon
- **2.142.0** — 2026-10-03 — `vps-jp1` — Giao dien VPS moi (cot icon, danh sach kenh, tab, cot phai Viec cua ban/Canh bao/Sap dang, dai trang thai); san xuat dung han (M1 chon content cho khe M2, san_xuat_truoc_gio); tai bo sung ghi ly do khi het luot; bang dieu hanh: lich tiep t…
- **2.141.8** — 2026-10-01 — `vps-jp1` — feat: tu chon danh sach phat theo de tai (kenh.yaml danh_sach_phat_kenh -> cot Danh sach phat -> may dang)
- **2.141.7** — 2026-10-01 — `vps-jp1` — doi thu: ba duong vao mot cua duyet, 4 dieu kien, trang thai het tu hoi sinh, co AI (thi giac)
- **2.141.6** — 2026-10-01 — `vps-jp1` — feat(tong giam doc): LUAT SO KENH theo do lon thi truong + kenh -K2 la kenh YouTube rieng - tong.py: so_kenh_toi_da (nguon no/thang / 15, chi khi trang chu len/on dinh), bang_so_kenh (tep -> toi da / dang co / de xuat mo, kenh thu 2+ cho k…
- **2.141.5** — 2026-10-01 — `vps-jp1` — Máy đăng: video làm xong tải + hẹn lịch luôn (cửa sổ 7 → 30 ngày)
- **2.141.4** — 2026-10-01 — `vps-jp1` — Dọn: video đã lên YouTube là xoá ngay file nặng + ảnh; gói Bỏ xoá ngay
- **2.141.3** — 2026-10-01 — `vps-jp1` — Gọn luật dọn DONE (một luật 3 ngày) + van ổ 10 GB
- **2.141.2** — 2026-10-01 — `vps-jp1` — Dọn DONE sau khi đăng + chặn ổ đầy + trần theo ổ
- **2.141.1** — 2026-10-01 — `vps-jp1` — Giãn lịch đăng theo nhịp ngày + dời lịch video đã hẹn + sản xuất theo nhịp
- **2.141.0** — 2026-10-01 — `vps-jp1` — Cứu video CTR thấp (đổi tiêu đề/bìa, duyệt 3 lần đầu) + vá lỗ bản chụp + giờ online + bìa
- **2.140.2** — 2026-10-01 — `vps-jp1` — Trang chủ: lưu CSV thử lại khi tệp đích đang bị mở (WinError 5 làm hỏng lượt nghiên cứu TL2)
- **2.140.1** — 2026-10-01 — `vps-jp1` — Phòng điều hành: ẩn việc ghim khi kênh tắt ghim; nút Sai loại bài học mọi nguồn khỏi lời nhắc; số 1709.0 → 1709
- **2.140.0** — 2026-10-01 — `vps-jp1` — Bảng điều khiển: phòng điều hành công ty
- **2.139.0** — 2026-10-01 — `vps-jp1` — Đội chuyên gia + hội đồng quyết định + sổ độ chính xác; sửa đo công suất cửa sổ gần
- **2.138.0** — 2026-10-01 — `vps-jp1` — Công ty YouTube (gọn): khám nghiệm video + bài học + tổng giám đốc gợi ý
- **2.137.2** — 2026-10-01 — `vps-jp1` — Ví: chi ngày theo số thật (độ tụt ví/chi phí lượt), cảnh báo đúng số ngày còn
- **2.137.1** — 2026-10-01 — `vps-jp1` — Gác tổng: cảnh báo 'hẹn lịch chưa tải' chỉ KHẨN khi còn ≤3 giờ (bớt báo động nhiễu)
- **2.137.0** — 2026-10-01 — `vps-jp1` — Giám đốc kênh: nối vào gác tổng/biên tập/hồ sơ; sửa ngưỡng thắng kênh ít video; TL3 chế độ gợi ý
- **2.136.1** — 2026-10-01 — `vps-jp1` — Golden giữ LF trên clone Windows (.gitattributes)
- **2.136.0** — 2026-10-01 — `vps-jp1` — VPS mới: khởi tạo ngách bằng AI + bỏ chỗ cứng Nhật
- **2.135.0** — 2026-10-01 — `vps-jp1` — Giám đốc kênh: gói lõi + 5 plugin đợt 1 (chưa nối)
- **2.134.1** — 2026-10-01 — `vps-jp1` — Máy đăng: bù MHKT video cũ giờ vắng
- **2.134.0** — 2026-10-01 — `vps-jp1` — Gọn kho: một README, một bộ luật, 3 tài liệu; bỏ luồng cài ZIP cũ
- **2.133.3** — 2026-10-01 — `vps-jp1` — Gọn kho: bỏ mã chết, công cụ cũ, bản trùng; README mới
- **2.133.2** — 2026-09-30 — `vps-jp1` — Máy đăng: quét ngày độc lập, MHKT dựng từ mẫu, chờ tải xong 100% + hậu kiểm
- **2.133.1** — 2026-09-30 — `vps-jp1` — docs(nhieu-vps): thêm dòng xem nhanh phiên bản (bản vá thử đường tự cập nhật)
- **2.133.0** — 2026-09-30 — `vps-jp1` — feat(cap-nhat): một hệ cập nhật git duy nhất — day tự nâng phiên bản + CHANGELOG + tag; máy tự kiểm ~30' và tự nhận bản mới lúc rảnh (mặc định bật, tắt trong Cài đặt); khung Cập nhật trên giao diện; bỏ lịch 03:40; A17 kho đọc cap-nhat.json

## [3.0.0-dev] — 22/09/2026 – 29/09/2026

Chuẩn bị phát hành v3.0 (sản phẩm nhiều VPS, nhiều ngách) — xem
`workspace/LO-TRINH-PHAT-HANH-V3.md` cho lộ trình đầy đủ.

### Giao diện & vận hành VPS

- Thiết kế lại giao diện VPS: gộp 6 tab rời thành trang **Trung tâm**, sau
  đó thành **Bảng điều khiển** — mở tool trả lời ngay ba câu "kênh có ổn
  không / tôi cần làm gì / kết quả ra sao" (khối Việc của bạn, Dòng máy,
  Thẻ kênh lớn theo từng kênh, xem `README-VPS.md`).
- Gộp toàn bộ thư mục VPS về một `MyTool\` duy nhất (bỏ cấu trúc nhiều thư
  mục rời rạc của bản trước).
- Bảng điều khiển: cảnh báo Windows sắp hết hạn, sửa 5 lỗi phát hiện trên
  dữ liệu thật sau khi khởi động lại máy.
- Cài VPS từ bản clone git thẳng (`CAI-DAT-VPS.bat` + `vm/cai_dat_tu_kho.py`,
  MỚI) — thay thế cho phải đóng gói `vm/goi-vps/` trên máy nhà rồi chép
  sang; thêm `websocket-client` (từng thiếu, làm máy đăng DOM hỏng trên máy
  sạch), lùi nguồn tải cho máy chỉ IPv6. Đi kèm `core/kiem_may.py` — bảng
  OK/THIẾU kiểm máy đã sẵn sàng tự chạy chưa.
- `.gitignore` vá lỗ lọt dữ liệu riêng máy/kênh (nhật ký kênh thật, hồ sơ
  video, trạng thái `vm/`); đổi chặn hồ sơ trình duyệt kênh sang chặn THEO
  CẤU TRÚC (`Data/profile`, `App/Chrome-bin`) thay vì theo tên `TL*`.
- Tài liệu vận hành mới: `README-VPS.md`, `docs/THEM-KENH.md`,
  `docs/DOI-CHU-DE.md`, `docs/BAN-DO-MODULE.md`.

### Điều phối tài nguyên (nền tảng cho nhiều kênh/nhiều VPS)

- Đo công suất thật của máy (`core/cong_suat.py`) trước khi sửa điều phối —
  số nền để so sánh trước/sau.
- Tách lớp song song **API** (gọi máy chủ, chạy song song nhiều làn) và
  **nặng** (Chrome/FFmpeg/Whisper, độc quyền một lượt) — sửa nút thắt từng
  ép mọi việc VPS về song song = 1, kéo dài khâu ảnh gấp nhiều lần.
- Khe tài nguyên liên tiến trình + hàng đợi ưu tiên P0–P4 + đệm sổ job dùng
  chung toàn máy (`core/khe.py`, `core/uu_tien.py`, `core/so_job_chung.py`,
  `core/bang_thong.py`) — module mới, thuần, sẵn sàng để nối vào bộ điều
  phối chính ở đợt kế tiếp.

### Sản xuất & chất lượng nội dung

- Sản xuất theo đúng nhịp đăng, tự ghi nhận khi có người đăng tay, tự phục
  hồi khi lượt trước dở dang.
- Một hàng đợi tuần tự cho toàn VPS — chặn hai lượt việc NẶNG chạy chồng
  nhau (Chrome + FFmpeg cùng lúc từng làm máy đơ).
- `core/bai_hoc_san_xuat.py` (MỚI) — vòng phản hồi: kênh tự học từ video đã
  đăng để cải thiện lượt sau.
- `core/qa_truoc_dang.py` (MỚI) — cổng kiểm chất lượng trước khi bàn giao
  cho máy đăng, chặn video lỗi lọt lên kênh thật.
- Hồ sơ video + vòng học chạy trước MỖI lượt sản xuất (không chỉ sau).
- Khuôn ảnh bìa "thắng" + giám khảo AI tự chọn ảnh bìa tốt nhất trong nhiều
  bản.
- N bản tiêu đề mỗi video + chấm điểm CTR dự đoán; kiểm trùng Ý TƯỞNG bằng
  LLM (không chỉ trùng chữ).
- Kho nhạc nền chuẩn hoá tăng dần (`core/kho_nhac.py`), dựng video theo
  PHẦN (nghỉ giữa phần, chuyển cảnh, nhạc đổi theo phần, phụ đề/mục lục
  đồng bộ).
- Chặn vượt cửa nhịp đăng + chống làm trùng nội dung theo TIÊU ĐỀ.

### Đăng video & bình luận

- **Máy đăng DOM/CDP** (MỚI) — đăng video qua Chrome DevTools Protocol thay
  vì chỉ giả lập chuột/phím; nối vào phiên kênh (`vm/agent.py`), trạm nội
  bộ, và kế hoạch đăng (`core/ke_hoach_dang.py`); đã thử đăng thật liên
  tiếp trên kênh thật.
- Máy đăng: dò ảnh đa tỉ lệ (sửa lỗi 0/1 mã im lặng), dẹp vật cản (hộp xin
  quyền, lỗi End Screen), bỏ lệnh xoá đệ quy `%TEMP%` nguy hiểm.
- Nhường phiên kênh cho `vm/agent.py` đúng trước giờ đăng — không để lượt
  sản xuất nặng giữ máy tới lỡ giờ.
- Tự nhận diện video đã đăng (không đứng im chờ mãi vì "quên" một gói).
- Báo động Telegram bền vững khi có sự cố cần người can thiệp.
- Bật tự động hoàn toàn cho các kênh đã qua thử nghiệm DOM đạt yêu cầu; hỗ
  trợ tải lên bổ sung trong ngày (không chỉ một lượt cố định).

### Dọn dẹp & xử lý sự cố

- Dọn hậu quả sau khi bỏ thư mục khuôn `_KHUON`/`_MAU-GON`; mở rộng cơ chế
  dọn đĩa (không chờ "đã đăng" mới dọn, có luật dọn sớm hơn).
- Lượt sản xuất "kẹt" tự phát hiện và tự xử lý (bốn mức xử lý khác nhau
  theo mức độ kẹt); sửa hai lỗi thật phát hiện sau khi triển khai.

---

Bản trước (2.x) — xem lịch sử `NHAT-KY-PHAT-TRIEN.md` trước ngày 22/09/2026.
