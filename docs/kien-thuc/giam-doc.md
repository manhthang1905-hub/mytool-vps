# Giám đốc kênh

Tầng tự quyết SAU KHI ĐĂNG: đọc số → quyết → áp có giới hạn → đo → giữ / bỏ / mở rộng. Lấp chỗ trống "tool học nhiều nhưng không ai đổi tham số". Gói `core/giam_doc/` (chưa nối vào lịch — việc nối là bước sau).

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
