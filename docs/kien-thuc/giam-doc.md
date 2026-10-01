# Giám đốc kênh

Tầng tự quyết SAU KHI ĐĂNG: đọc số → quyết → áp có giới hạn → đo → giữ / bỏ / mở rộng. Lấp chỗ trống "tool học nhiều nhưng không ai đổi tham số". Gói `core/giam_doc/`, nối vào lịch từ v2.137 (mục 8).

## 1. Dùng thử (0 đồng, không ghi gì)

```
python -m core.giam_doc --kenh <mã> --thu            # bảng số + quan sát + thực đơn (✔ qua giới hạn / ✘ lý do)
python -m core.giam_doc --kenh <mã> --llm [--tuan]   # + MỘT lượt LLM thật qua ví — vẫn không ghi
python -m core.giam_doc --nhip                       # kênh nào đến hạn
```

## 2. Khoá kenh.yaml

| khoá | mặc định | nghĩa |
|---|---|---|
| `giam_doc` | `tat` | `goi_y` = chế độ bóng (ghi sổ + báo cáo, không đổi kenh.yaml) · `tu_ap` = tự áp qua giới hạn |
| `giam_doc_studio` | `false` | đợt 1 việc Studio (đổi tiêu đề) CHỈ là gợi ý trong "Việc của bạn" |
| `giam_doc_khong_dung` | — | `"phut_muc_tieu, chien_luoc"` — khoá chủ cấm chạm |
| `giam_doc_cho_phep_ab` | `false` | kênh có cặp `-v2` tối đa `goi_y` trừ khi bật |

## 3. Ai quyết gì

- **Việc (plugin)** đưa ra SỐ và THỰC ĐƠN — thuần, 0 đồng.
- **LLM** (`quan_ly.nghi`, thang Fable → Opus → Sonnet, ~1 lượt/ngày/kênh, hỏi van ví trước) CHỈ chọn id trong thực đơn và viết chữ (chỉ đạo, tiêu đề mới). LLM hỏng thì hôm đó không áp gì.
- **Giới hạn** (`gioi_han.kiem`) là luật cứng, soát cả trước lời nhắc lẫn trước khi áp.

Ba tay: tham số kenh.yaml (danh sách trắng) · chỉ đạo chữ ≤ 5 dòng có hạn (`giam-doc/chi-dao.json`, biên tập viên đọc như tiêu chí tuần) · việc Studio (đợt 1b).

## 4. Giới hạn an toàn

| khoá | biên | bước |
|---|---|---|
| `chien_luoc` | mỗi công thức 0,1–0,9, giữ đúng tập công thức | ±0,2 |
| `chien_luoc_tham_do` | 10–35 | ±10 |
| `chien_luoc_tu_hoc` | chỉ false → true (đủ 3 điều kiện `chien-luoc.md` mục 5) | — |
| `phut_muc_tieu` | 10–25 (số nguyên) | ±3 |
| `luat_chon_tuan` | ≤ 3 câu | thay cả khối |

- Ngoài tầm (chỉ gợi ý): `tu_*`, `ngan_sach_ngay`, `video_toi_da_ngay`, `nhip_dang`, `so_ban_nhap`, `voice_id`, `cach_dang`.
- Ngân sách: ≤ 2 tham số/kênh/tuần; 1 thí nghiệm mở / chỉ số chính; khoá vừa đổi (hoặc vừa quay lui) nghỉ 14 ngày.
- Studio: ≤ 2 video/tuần, mỗi video sửa 1 lần trong đời, chỉ video đã TRƯỢT có hồ sơ của tool, không bao giờ video thắng, không trong 60 phút trước giờ đăng.
- Quay lui tự động: hiển thị 7 ngày tụt ≥ 35% so với nền 14 ngày trước khi áp (mà vẫn đăng đều) · chỉ số chính tệ hơn nền quá `tut_pct` khi n ≥ 3 · sức khoẻ báo động.
- Chủ sửa tay khoá giám đốc đã ghi → giữ (`chu_giu`) 30 ngày.

## 5. Sổ — `CHANNEL/<k>/giam-doc/`

`thi-nghiem.json` (id, giả thuyết, biến cũ/mới, chỉ số, nền, cỡ mẫu, hạn, trạng thái `mo|giu|bo|mo_rong|quay_lui|chua_du`) · `nhat-ky.jsonl` · `trang-thai.json` · `chi-dao.json` · `BAO-CAO-TUAN.md` + `bao-cao.json`. Tới hạn chưa đủ mẫu: gia hạn 1 lần, lần 2 trả giá trị cũ (`chua_du`). Kết luận theo trung vị: ≥ +30% mở rộng, ≥ +10% giữ, còn lại bỏ (tỉ lệ thắng: +25 / +10 điểm %).

## 6. Việc đợt 1

| việc | nhịp | đọc | đề xuất |
|---|---|---|---|
| `suc_khoe` | ngày | hiển thị 7 ngày / trung vị 14 ngày trước; 3 video mới nhất @48h; CTR cùng tụt | phanh: đóng băng + quay lui + báo chủ. Hiển thị nguội sau video nổ mà video mới vẫn khoẻ → chỉ cảnh báo |
| `cuu_ctr` | ngày | video 52–85h: CTR trang chủ vs 0,8 × mục tiêu | đổi tiêu đề (gợi ý); CTR ổn mà trượt = lỗi cổng hiển thị, không sửa |
| `dan_cum` | tuần | thắng/trượt theo cụm của chính kênh | ưu tiên / tạm bỏ 3 tuần, `luat_chon_tuan`, tỉ trọng, bật tự học |
| `muc_tieu_ypp` | tuần | sub/1k view, giờ xem/1k hiển thị theo cụm | xen cụm kéo thứ YPP đang thiếu; lời mời đăng ký trước vách rơi |
| `do_dai` | tuần | giờ xem / 1.000 hiển thị @52h theo nhóm độ dài (không theo AVD%) | thí nghiệm `phut_muc_tieu` ±2–3, cỡ mẫu 4 |

## 7. Thêm một việc

Chép `core/giam_doc/_mau.py` thành `core/giam_doc/<ten>.py` (tự được phát hiện): `TEN, MO_TA, NHIP, CHI_SO_CHINH`, `ap_dung(bs)` (0 = thiếu dữ liệu), `quan_sat(bs)` (câu có số + n + tin cậy), `de_xuat(bs, qs)` (thực đơn), `ket_luan(bs, tn)`. Chỉ đọc `BangSo` (`du_lieu.tom_tat`), không gọi mạng, chỉ số của chính kênh. Test: `tests/test_giam_doc_plugin.py` (kênh giả `tests/du-lieu/giam-doc/kenh-mau.json`).

## 8. Nối vào mã sống (01/10/2026)

- **Chạy:** gác tổng (`core/gac_tong._main`, mỗi 15') gọi `giam_doc.nhip(goc, thu=thu)` trong `try` riêng → kênh đến hạn (chưa chạy hôm nay; thứ Hai = lượt tuần; không trong 60' trước giờ đăng) thì sinh tiến trình tách rời `python -m core.giam_doc --chay` (khoá `workspace/giam-doc/.khoa`, giành lại sau 3 giờ, log `workspace/giam-doc/tien-trinh.log`). Không chạy trong `vong_hoc`/`tu_chay`.
- **Báo:** `giam_doc_ket` (mức thường) khi kênh đến hạn liền ≥ 6 giờ chưa chạy được (`kiem_ket`, mốc ở `workspace/giam-doc/den-han.json`); mỗi dòng "Việc của bạn" của báo cáo cuối → `giam_doc_viec` (mức nhắc, lọc lặp 4 giờ theo nội dung) + một dòng ở khối Việc của bạn (nút Báo cáo tuần / Đã xong).
- **Bảng điều khiển:** thẻ kênh có công tắc 3 nấc `giam_doc` (Tắt / Gợi ý / Tự áp — lên Tự áp phải xác nhận), một dòng `bao_cao.cau_the`, nút "Báo cáo tuần" (`BAO-CAO-TUAN.md`).
- **Chế độ gợi ý = bóng:** không đổi kenh.yaml, không ghi `chi-dao.json`, không mở thí nghiệm; ghi nhật ký `goi_y` + mục "Sẽ làm" của báo cáo. LLM đoán thắng/trượt cho mọi video đang chờ (`du_doan`), giữ lần đoán ĐẦU, máy tự chấm khi video có kết luận (`giam-doc/du-doan.json`; "đoán đúng x/y" trên thẻ).
- **Biên tập viên:** chỉ đạo còn hạn + `kenh.yaml: luat_chon_tuan` → khối "CHỈ ĐẠO TUẦN NÀY CỦA GIÁM ĐỐC KÊNH" ngay trước khối ỨNG VIÊN (cả đề bài cũ lẫn gọn). Không có gì → lời nhắc y hệt từng byte. `NguCanh.luat_chon` nối thêm `luat_chon_tuan`.
- **Hồ sơ video:** mỗi mốc thêm `ctr_trang_chu`, `hien_thi_trang_chu`, `pct_browse`, `pct_de_xuat`, `subs`, `gio_xem`; `thi_nghiem` (id thí nghiệm đang mở lúc bàn giao, cách nhau dấu phẩy); `lich_su_sua[]` (`ho_so_video.ghi_sua`, đo trước/sau bằng hiệu hai bản chụp, mỗi phía ≥ 500 hiển thị); `bia_2` + `anh/<mã gói>-bia-2.jpg` (bìa hạng nhì của giám khảo). `bia_theo_khuon` không coi bìa có `doi_boi: "giam_doc"` là bìa tay.
- **Ngưỡng thắng 48h** (`cong_thuc_v7.nguong_thang_48h`, dùng chung V7 / `chien_luoc.ket_qua` / biên tập viên / giám đốc): kênh ≥ 5 video có số 48h → max(`toi_thieu_48h`, 3 × trung vị kênh) như cũ; ít hơn → ngưỡng ngách (`ngach.yaml: nguong_thang_48h`, chưa khai = `toi_thieu_48h` 6.000) trộn sang ngưỡng kênh với trọng số ((n−1)/4)².

## 9. Công ty YouTube — bản gọn (01/10/2026)

Thiết kế: `workspace/THIET-KE-CONG-TY.md` (khung BẢN GỌN ở đầu tệp). Mọi lượt LLM ra quyết định / chẩn đoán đi qua MỘT cửa `quan_ly.goi_quyet(loai, loi_nhac, so_lieu, goi_chat, doc=…)` — hội đồng quyết định sau này chỉ thay thân hàm đó. Số LLM trích phải kèm khoá nguồn (`so_dan: [{"so", "nguon": "v:<vid>/<mốc>/<trường>"}]`).

- **Khám nghiệm video** (`core/giam_doc/kham_nghiem.py`, không phải plugin): trong `chay_kenh` sau bước tự chấm, mỗi lượt ≤ 4 video, mỗi video ≤ 2 lần (mốc `48h` = bản chụp 40–100h, `7d` = 120–260h, lấy mốc muộn nhất). Hồ sơ 0 đồng: 3 cổng so trung vị kênh cùng tuổi, CTR trang chủ, đường giữ chân + câu kịch bản ở vách (`3-phu-de.srt`), 30 giây đầu, `su_that_tu_luot`, pool, bình luận (mốc 7d, `chi-so/<vid>/binh-luan.json`, chỉ khi gọi AI thật), dự đoán lúc chọn. Một lượt LLM → `chan_doan` (có số), `cong_hong`, `vi_sao`, `du_doan_lech`, nhãn theo nghĩa (`kieu_tieu_de`, `kieu_hook`; mã gắn `kieu_bia`, `do_dai_nhom`), một `bai_hoc{truc, gia_tri, huong, cum, cau}`. Ghi `giam-doc/kham-nghiem/<vid>-<mốc>.json` + `giam-doc/bai-hoc.jsonl` (khám lại thay dòng cũ).
- **Bài học vào sổ chung**: `chien_luoc.bai_hoc._tu_kham_nghiem` (phạm vi kênh) gộp theo khoá `truc|gia_tri|huong|cum`, n = video ủng hộ − video phản, cần n ≥ 3, mâu thuẫn → không bơm; giám đốc chưa `tu_ap` → bài **bóng** (chỉ người đọc). Một móc: `auto_khau._khoi_khan_gia` nối khối "BÀI HỌC TỪ KHÁM NGHIỆM VIDEO CỦA KÊNH" vào cuối `SU_THAT_KENH` (bộ chấm 2b/2e/2g) — chưa có bài bơm được thì y hệt từng byte. Ngách/toàn cục: cơ chế sẵn có; `dong_bo_git bai_hoc` xuất thêm trường `khoa`.
- **Giám đốc kênh đọc khám nghiệm**: `quan_ly.loi_nhac` có khối "KHÁM NGHIỆM GẦN ĐÂY" (≤ 5 chẩn đoán + bảng đếm theo nhãn: thắng/trượt) sau QUAN SÁT; LLM đổi "chuẩn" bằng thực đơn sẵn có (`luat_chon_tuan`, `phut_muc_tieu`, `chien_luoc`, chỉ đạo sửa câu được). Chưa có bản khám → lời nhắc y hệt.
- **Tổng giám đốc** (`core/giam_doc/tong.py`, khoá `workspace/cai-dat.json: tong_giam_doc: tat|goi_y|tu_ap`): thứ Hai, sau lượt tuần của mọi giám đốc kênh (`den_han`, trong `chay_het`; `nhip` cũng sinh tiến trình khi chỉ tổng đến hạn). Bảng công ty (cặp `-v2` gộp một kênh YouTube): hiển thị/giờ xem/sub 7 ngày so 7 ngày trước, thắng 28 ngày, YPP, khe. Xếp loại lên (đà ≥ 1,2 và thắng ≥ 25%) / tụt (đà ≤ 0,8) / chững. Luật ±1 khe/kênh/tuần, mỗi kênh 1..6, tổng ≤ 0,85 × trần máy (`cong_suat.cong_suat_hien_tai(gio=168)`); khe mới ở giữa khoảng trống lớn nhất, bớt khe có hiển thị 48h trung vị thấp nhất; `video_toi_da_ngay` = số khe, `ngan_sach_ngay` chỉ nâng (ước/video × khe × 1,3). Một lượt LLM chọn id trong thực đơn. `tu_ap`: `trung_tam.ghi_cai_kenh`, sổ `workspace/tong-giam-doc/so.json`, nghỉ 14 ngày, chủ sửa tay giữ 30 ngày, quay lui sau ≥ 7 ngày khi hiển thị 48h trung vị tụt ≥ 30% hoặc khe nặng ≥ 90%. Báo cáo `workspace/tong-giam-doc/BAO-CAO-CONG-TY.md`; kênh mới chỉ gợi ý (từ `workspace/khoang-trong-kenh-*.md`, khi máy dư ≥ 2 video/ngày).
- **CLI**: `python -m core.giam_doc --kham <vid> [--llm]` (không `--llm`: in lời nhắc 0 đồng; có `--llm`: khám và GHI) · `--tong --thu|--llm` (không ghi). **Bảng điều khiển**: ô "Công ty" ở dòng MÁY (ẩn khi chưa họp), bấm = Báo cáo công ty.
