# Phát triển trên nhiều VPS

Kho `github.com/manhthang1905-hub/mytool-vps` là nguồn mã duy nhất. Mỗi VPS chạy một ngách hoặc một quốc gia. Máy nào sửa thì máy đó đẩy lên kho, và các máy khác tự nhận. Luật khi sửa trên máy đang chạy thật nằm ở `CLAUDE.md`. Cách cài VPS mới nằm ở `README.md`.

## 1. Lệnh `python -m core.dong_bo_git <lệnh>` (chạy ở gốc MyTool)
| Lệnh | Làm gì |
|---|---|
| `ket_noi` | Kiểm đường tới GitHub. Máy chỉ có IPv6 thì lệnh tự dò NAT64 và sửa `HostName` của `github-mytool` trong `~/.ssh/config`. Sau đó thử deploy key |
| `trang_thai` | Nhánh hiện tại, số commit đi trước hoặc sau origin, các tệp đã đổi |
| `day "thông điệp" [--minor\|--major] [--chi tệp…]` | Kiểm, commit, rebase, nâng phiên bản, push (mục 2) |
| `kiem` | Kiểm có bản mới trên kho không |
| `keo [--ep]` | Áp bản mới an toàn (mục 3). `--ep` giống nút "Cập nhật ngay" |
| `lui [--tag T]` | Quay lại tag `truoc-cap-nhat-*` gần nhất |
| `quet` | Chỉ quét bí mật và dữ liệu kênh trên các tệp sẽ lên kho |
| `bai_hoc` | Xuất bài học ngách ra `chia-se/bai-hoc/` (xem `docs/KENH-VA-NGACH.md`) |
| `lich bat\|tat` | Bảo đảm có lịch `ShopAPI-GacTong`, và gỡ lịch cũ `ShopAPI-DongBoGit` |

## 2. Đẩy một bản sửa: `day`
1. `git add -A`. `.gitignore` là **danh sách trắng**, nên chỉ những gì được khai rõ mới lên kho. Thêm tệp hoặc thư mục mới ở gốc thì phải mở lối cho nó trong `.gitignore`.
2. Kiểm:
   - `py_compile` các tệp đã đổi;
   - kiểm khói: import các module chính;
   - chạy nhóm `TEST_NHANH`, chỉ khi khe "nang" đang trống.
3. Quét bí mật: `core/kiem_phat_hanh.py` quét khoá, email, đường dẫn có tên người dùng, tên kênh thật, video id và tiêu đề của máy.
   Chuỗi mẫu trong test cố tình giống khoá thì viết tách ra (`"sk_live_" "abc…"`), hoặc thêm `# dong-bo-git: mau` ở cuối dòng.
4. Commit, `fetch`, rồi rebase lên `origin/main` (dùng `--autostash`). Gặp xung đột thì huỷ rebase và báo tên tệp. Người sửa tự giải rồi chạy lại.
5. Nâng phiên bản trong commit riêng `v<x.y.z>: <thông điệp>`:
   - số mới = max(bản của máy, bản của origin) cộng patch, hoặc `--minor`, `--major`;
   - thêm một dòng vào `CHANGELOG.md`;
   - gắn tag `v<x.y.z>`.
6. Push nguyên tử (nhánh và tag cùng lúc). Nếu máy khác vừa đẩy trước, lệnh kéo lại, rebase rồi tăng lại số, nên hai máy không bao giờ trùng phiên bản.

Dùng `--chi <tệp…>` khi máy còn tệp dở của người khác: chỉ những tệp đó được commit.

## 3. Máy tự nhận bản mới: `core/cap_nhat_git.py`
- **Kiểm:** hàm `nhip` chạy khoảng 30 phút một lần, trong gác tổng và giao diện, và mỗi lần mở giao diện. Nó chạy `git fetch`, đọc `origin/main:VERSION` và CHANGELOG, rồi ghi `workspace/cap-nhat/trang-thai.json`.
- **Khi nào áp:** có bản mới, tự động đang bật (hoặc người bấm "Cập nhật ngay"), và máy rảnh. Khi đó `nhip` sinh tiến trình tách rời `dong_bo_git keo`.
- **`keo` làm các bước:**
  1. Thoát ngay nếu `tu_dong_cap_nhat` đang tắt (trừ khi chạy `--ep`). Chỉ một lượt mỗi lúc, giữ bằng khoá `workspace/cap-nhat/dang-cap-nhat.json`.
  2. Máy có sửa chưa commit hoặc commit chưa đẩy thì không kéo đè. Máy báo "có sửa chưa đẩy".
  3. Dựng bản mới trong một git worktree tạm, py_compile toàn bộ rồi kiểm khói. Không đạt thì không áp.
  4. Chờ máy rảnh, tối đa `cho_toi_da_phut`. Rảnh nghĩa là đủ cả 4 điều kiện:
     - đang trong khung phút :15–:45;
     - `core.an_toan_khoi_dong` đồng ý;
     - khe "nang" trống;
     - không lượt nào đang dựng hoặc làm phụ đề.
  5. Gắn tag `truoc-cap-nhat-<ts>`, `merge --ff-only`, rồi kiểm khói lại. Hỏng thì `reset --hard` về tag.
  6. Khởi động lại giao diện. Giao diện tự mở lại các tiến trình con của `vm/`. Lịch `tu_chay` tự nhận mã mới ở lượt sau.
  7. Theo dõi trong `theo_doi_phut`. Giao diện hoặc agent (cổng 8767) chết 3 lần kiểm liên tiếp thì máy tự lùi về tag, ghi lý do, và bỏ qua bản hỏng cho tới khi kho có bản mới hơn.
- **Nhật ký:** `workspace/cap-nhat/nhat-ky.txt`, `workspace/dong-bo-git/nhat-ky.txt`.
- **Chỉ có một hệ cập nhật.** Các đường cũ (`core/cap_nhat_github.py`, `core/safe_update.py`, `core/nguon_cap_nhat.py`) luôn nhường khi máy có `.git`.

## 4. Cấu hình riêng mỗi máy (không lên kho)
| Tệp | Nội dung | Mẫu hoặc nơi tạo |
|---|---|---|
| `config.json` | địa chỉ máy chủ, số job | `config.example.json` |
| `secrets.json` | khoá API, mã hoá DPAPI | tool tự tạo khi đăng nhập |
| `cap-nhat.json` | `kho`, `nhanh`, `tu_dong_cap_nhat`, `dong_bo_git.ma_may`… | `cap-nhat.example.json` |
| `vps.json`, `vm/config.json`, `CLAUDE.local.md` | dấu chế độ VPS, cấu hình agent, luật riêng máy | `CAI-DAT-VPS.bat` (`vm/cai_dat_tu_kho.py`) |
| `workspace/cai-dat.json` | cài đặt vận hành (`dieu_phoi`, `ngay_het_han_vps`…) | giao diện |
| `CHANNEL/<kênh>/` | kênh thật | `docs/KENH-VA-NGACH.md` |
| `PROJECTS/`, `DONE/`, `workspace/`, `vm/logs/`, `NHAT-KY-PHAT-TRIEN.md` | dữ liệu chạy và nhật ký | |

## 5. Bản đồ module (theo dòng chảy một video)
Đọc hết docstring đầu tệp trước khi sửa. Lý do của các quyết định nằm ở đó.

**Điểm vào:**
- `shopapi_studio_qt.py`: giao diện;
- `tu_chay.py`: sản xuất;
- `tram_nen.py`: trạm;
- `-m core.gac_tong`: gác tổng;
- `vm/agent.py`: phiên kênh, do giao diện mở.

| Khâu | Module |
|---|---|
| Khởi tạo ngách (VPS/chủ đề/quốc gia mới) | `core/khoi_tao_ngach.py` (một lệnh: hồ sơ ngách → kênh từ `CHANNEL/_KHUON/kenh-mau/` → nghiên cứu khởi động), `core/ho_so_ngach.py` (`la_ngach_mac_dinh`: ngách tâm lý Nhật giữ nguyên văn lời nhắc cũ) |
| Nghiên cứu đối thủ | `core/danh_ba_doi_thu.py`, `core/doi_thu_kenh.py`, `core/chot_doi_thu.py`, `core/loi_thoai.py` |
| Chọn nguồn | `core/chien_luoc/` (công thức `v7`, `vph`, `mot_nut`; `bai_hoc`, `ngu_canh`; xem `docs/kien-thuc/chien-luoc.md`), `core/cong_thuc_v7*.py`, `core/mot_nut.py`, `core/bien_tap_content.py`, `core/chon_content.py`, `core/kiem_trung_y.py`, `core/trung_tieu_de.py`, `core/ho_so_ngach.py` |
| Điều phối lượt | `core/tu_chay.py` (một lượt mỗi kênh), `core/dieu_phoi.py` (song song), `core/khe.py`, `core/uu_tien.py` (khe "api"/"nang" liên tiến trình), `core/che_do_vps.py` |
| 8 khâu sản xuất | Danh sách chuẩn ở `core/auto.py:KHAU`: kich-ban → giong-doc → phu-de → bang-canh → anh → clip → thumbnail → dung. Động cơ: `core/auto_khau.py` (**chỗ trừ tiền**). Dựng trên máy: `core/dung_video.py`, `core/ffmpeg_goi_san.py`, `core/kho_nhac.py` |
| Bàn giao → đăng | `core/ban_giao_dang.py` (→ `DONE/`), `core/ke_hoach_dang.py`, `vm/agent.py`, `vm/may_dang_dom.py`, `vm/may_dang.py`, `vm/may_cmt_dom.py`, `vm/may_cmt.py`; thiết lập kênh ở `core/vm_cai_dat.py` (xem `docs/DANG-VA-BINH-LUAN.md`) |
| Số liệu và học | `core/chi_so_ytb/` (trạm 8765, giải mã Studio, mốc theo tuổi thật), `core/ytb_extension/` (extension cào Studio), `core/vong_hoc.py`, `core/tu_hoc.py` (ván, bảng điểm, Thompson; sơ đồ `docs/VONG-HOC.md`), `core/da_lam.py`, `core/ypp.py` (dự báo ngày đạt YPP) |
| Chiến trường | `core/chien_truong.py` (vùng, thị phần, điểm cơ hội, lệnh chia đất), `core/chien_truong_ai.py` (AI xếp vùng theo nghĩa), `core/chien_truong_lich_su.py`, `core/chien_luoc/tan_cong.py` (lệnh → trọng số mềm ≤ +30% khi chọn nguồn) |
| Kéo view chéo | `core/keo_cheo.py` (kế hoạch, giới hạn, đo), `vm/keo_cheo_dom.py` (thêm vào danh sách phát trên Chrome kênh lớn) |
| Đăng: bền với Studio | `vm/tu_chua_dom.py` (AI đề xuất bộ chọn, kiểm trên trang, `TL_TU_CHUA_DOM=0` tắt), `vm/ngon_ngu_tam.py` (tạm `hl=vi` rồi trả), `vm/thiet_lap_kenh_dom.py` (thiết lập kênh một lần) |
| Dọn và canh | `core/don_dep.py`, `core/don_dia.py` (nhịp dọn từ gác tổng + xoay log), `core/gac_tong.py`, `core/ben_bi.py` (khoá chết, nhịp tim, hồi sinh agent, 36h không sản xuất), `core/chot_an_toan.py` (ví, Windows, hạn VPS, giọng trùng), `core/bao_dong.py`, `core/bao_cao_ngay.py` (06:30), `core/su_co.py`, `core/kiem_may.py`. Xem `docs/BEN-BI.md` |
| Trung tâm chỉ huy (chỉ đọc, cổng 8770) | `core/truc_quan.py`, `core/nao_truc_quan.py`, `ui_web/*.html`, `MO-TRUNG-TAM.bat`. Xem `docs/TRUNG-TAM-CHI-HUY.md` |
| Danh mục skill | `core/ky_nang.py` → `docs/KY-NANG.md` (`python -m core.ky_nang md`) |
| Hạ tầng VPS | `core/giam_sat_vm.py` (trông tiến trình con `vm/`), `core/lich_tu_chay.py` (5 lịch Windows), `core/nhuong_phien_kenh.py`, `core/an_toan_khoi_dong.py`, `vm/cai_dat_tu_kho.py` (bộ cài) |
| Đồng bộ kho | `core/dong_bo_git.py`, `core/cap_nhat_git.py`, `core/kiem_phat_hanh.py` |
| Giao diện | `ui_qt/app.py` (danh sách trang `TRANG`, xưởng `_dung_cac_trang`). Ở chế độ VPS, `core/che_do_vps.TRANG_VPS` thay thanh bên bằng 7 trang: Bảng điều khiển (`trang_bang_dieu_khien`), Số liệu kênh (`trang_trung_tam`, có hộp **Thêm kênh**), Nghiên cứu, Chọn nội dung, Sản xuất, Lịch đăng, Cài đặt (`trang_may_vi`) |

**Thêm một trang giao diện:**
1. Viết `ui_qt/trang_<tên>.py`: một `QWidget` nhận `app`.
2. Thêm khoá của trang vào `TRANG` và vào xưởng trong `ui_qt/app.py`. Trang dành cho VPS thì thêm cả vào `core/che_do_vps.TRANG_VPS`.
3. Viết bài hướng dẫn trong `ui_qt/huong_dan.py`.
4. Chạy `tests/test_bo_cuc.py`, bài này kiểm trang không tràn mép.

Việc gọi API đi qua `JobSpec` và `app.start_batch(...)`. Không bao giờ gọi mạng trên luồng giao diện.

**Thêm một công thức chọn nguồn:** xem `docs/kien-thuc/chien-luoc.md` mục 7.

## 6. Kiểm thử
- Trên máy sản xuất chỉ chạy test lẻ: `python -m pytest tests/test_<việc>.py -q`.
- Bộ đầy đủ: chạy THEO LÔ (~20 tệp một lượt, tuần tự, ưu tiên thấp), không bao giờ `pytest tests/` một phát trên máy đang chạy thật (từng làm VM treo).
- Bản clone sạch (không `CHANNEL/<kênh>/`, `DONE/`, `workspace/`) phải xanh: bài nào cần kênh thật thì lùi về khuôn `CHANNEL/_KHUON/kenh-mau/` hoặc `skip` có lý do — không đỏ vì thiếu dữ liệu máy.
- Test không gọi mạng, không đăng ký tác vụ Windows, không giết tiến trình thật.

## 7. Máy mới + chủ đề mới — danh sách đã chạy thử
Chạy khô ngày 06/10/2026 trên bản `git archive` sạch: ngách "nấu ăn gia đình Hàn · KR · ko", 2 kênh giả `KR1`, `KR2`, AI/YouTube/ảnh là đồ giả (không Chrome, không ví). Bài kiểm giữ đúng luồng này: `tests/test_ngach_khac_tieng.py`, `tests/test_khoi_tao_ngach.py`.

**A. Máy (một lần)**
1. Cài theo `README.md`: clone kho → `CAI-DAT-VPS.bat` (ghi `vps.json`, `vm/config.json`, lịch Windows).
2. `python -m core.kiem_may` → mọi dòng OK. Hay thiếu trên máy mới: mô hình Whisper `models/faster-whisper-small/` (máy chỉ IPv6: chép tay qua RDP).
3. Đăng nhập ShopAPI trong giao diện (tạo `secrets.json`).
4. Font chữ bìa/banner theo tiếng: tool tự chọn theo CHỮ sẽ vẽ (`core/bia_theo_khuon.bo_font_cho`) — Hangul → Malgun Gothic/Noto Sans KR, La-tinh có dấu → Arial/Segoe UI, chữ Nhật → Yu Gothic như cũ. Windows thiếu font đó thì bỏ tệp `.ttf/.otf` vào `MyTool/assets/fonts/` (thư mục này thắng font hệ thống; không lên kho).
5. Mỗi kênh một Chrome Portable đã đăng nhập YouTube: `<thư mục chứa MyTool>\<MÃ>\<MÃ>.exe`.

**B. Ngách + kênh (mỗi kênh một lệnh, cùng `--nhom`)**
1. Xem trước, không tốn gì: `python -m core.khoi_tao_ngach --chu-de "nấu ăn gia đình" --quoc-gia KR --ngon-ngu ko --nhom bep-han --ma-kenh KR1 --thu`.
2. Chạy thật (bỏ `--thu`). Kênh đầu: AI viết `CHANNEL/_NHOM/bep-han/ngach.yaml` (có cả `giong_van`, `ten_kenh_goi_y`), dựng `CHANNEL/KR1/` từ khuôn, viết lại 5 lời nhắc + 8 khoá style, ảnh nhân vật, sổ tuyến + V7, đưa kênh vào `vm/config.json` nếu thấy Chrome.
3. Kênh thứ hai: cùng lệnh, `--ma-kenh KR2`. Hồ sơ ngách và lời nhắc dùng lại (0 lượt AI mới); kênh nhận **tệp khán giả còn trống** kế tiếp (`chon_tep`), tên làm việc `<tên gợi ý> · <tệp>`.
4. `kenh.yaml` mới có sẵn: `ngon_ngu`, `quoc_gia`, `dia_diem_xem` (= nước kênh — skill K06 và hồ sơ Studio đọc, không suy từ tiếng), `ky_tu_moi_phut` tham khảo theo tiếng, `chu_bia_hoa: false` cho ja/ko/zh, `gio_dang` đã đổi sang giờ VPS. Công tắc tiền/tự chạy TẮT.
5. Kiểm bằng mã: `python -m core.ky_nang thieu KR1` — sau bước B còn: K01 (Chrome), K02 (tài khoản), K04 (giọng), K06–K14 (thiết lập Studio, agent tự làm khi Chrome đã đăng nhập), K16 (danh bạ đối thủ, lượt tự chạy đầu).

**C. Việc của người (máy không tự làm được)**
1. Giọng đọc: điền `voice_id` một giọng ĐÚNG TIẾNG, riêng từng kênh. Nhóm tiếng khác tiếng Nhật KHÔNG được gieo giọng Nhật khởi đầu (`mo_kenh.doc_kho_giong`) — thêm giọng đã duyệt vào `CHANNEL/_NHOM/<nhóm>/kho-giong.json` thì `mo_kenh chuan-bi` tự gán cho kênh sau.
2. Đo lại `ky_tu_moi_phut` sau video đầu (ko: tham khảo 380).
3. Tài khoản kênh (email/2FA) vào kho bí mật — skill K02.
4. `python tu_chay.py --kenh KR1 --thu` → log có ứng viên đúng ngách → bật `ngan_sach_ngay`, `tu_chay`; duyệt tay ≥ 7 ngày (`tu_duyet` tắt).

**D. Chỉ kiểm được khi chạy thật (Chrome + tài khoản thật) — làm một lần cho mỗi tiếng/nước mới**
- Studio ép giao diện `vi` lúc đăng (`vm/may_dang_dom.NGON_NGU_GIAO_DIEN_DANG`, cookie `PREF hl=vi`) trên tài khoản nước khác — `python vm/may_dang_dom.py --kenh KR1 --kiem-dom`.
- Chọn ngôn ngữ phụ đề trong hộp phụ đề Studio: `vm/studio-selectors.json → ngon_ngu_video` (đã có ko/th/id/es/pt/fr/de, tên đọc từ bản dịch thường gặp, chưa đo).
- Menu youtube.com "Địa điểm": tên nước trong `vm/thiet_lap_kenh_dom.TEN_NUOC` (KR đã có; GB/CA/AU/IN/PH/SG/MY/DE/FR/ES/BR/MX mới thêm, chưa đo).
- Mặc định tải lên (ngôn ngữ video/mô tả) và danh mục: `core/thiet_lap_kenh.NGON_NGU`/`DANH_MUC`.
- Bình luận trả lời đúng tiếng kênh và giọng kênh (`vm/may_cmt_dom.py`); bộ lọc spam/xúc phạm mới có ít từ tiếng Hàn.
- Nuôi trang chủ: nút "Không quan tâm" tiếng Hàn và nhận captcha tiếng Hàn/Việt (`vm/nuoi_trang_chu.py`).
- Giọng ElevenLabs tiếng Hàn đọc đúng nhịp; chữ bìa AI viết bằng Hangul (lời nhắc bìa bản địa hoá qua `bia_theo_khuon.ban_dia_hoa`).
- Phụ đề đốt vào hình (`dot_phu_de: true`, mặc định tắt) dùng font `Arial` của libass (`core/dung_video.py`) — Hangul trông vào font dự phòng của máy.

**E. Còn viết cứng (đã biết, chưa sửa — thứ tự đáng sửa)**
- `core/chi_so_ytb/giai_ma.py` `LECH_JST_GIO = 9`: giờ khán giả quy về JST cố định (đúng cho JP/KR, lệch cho VN/US) — chỉ ảnh hưởng báo cáo/gợi ý khe đăng.
- `vm/nuoi_trang_chu.py` `KENH_MOI_THU_TU`: 4 mã kênh của máy đầu để xếp cổng DevTools; máy khác chỉ bị thêm tên ảo vào danh sách tạm.
- `core/kiem_ngach_doi_thu.py` `_tai_url`: `Accept-Language: ja,en`.
- Đường lùi tiếng Nhật khi ngách KHÔNG khai: `core/chien_luoc/ngu_canh.MAC_DINH_THI_TRUONG`, `core/bien_tap_content.MAC_DINH_KHAN_GIA` và `or "ja"`, `core/auto_khau.py` (`_NHAN_TUONG_DUONG` 心理学, `CHARS_HOOK … or 270`) — `khoi_tao_ngach` luôn khai đủ nên kênh dựng đúng luồng không rơi vào.
- `vm/may_cmt.py` `LANG_MAP` theo đuôi `-T<n>` (chỉ khi kênh không có `kenh.yaml`).
- Bộ ảnh mẫu phong cách `ui_qt/mau_phong_cach/` là media bị `.gitignore` chặn → máy clone từ GitHub thấy thẻ "Ảnh mẫu chưa tạo".
