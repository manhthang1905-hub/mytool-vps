# Vòng tự học — tín hiệu nào lái quyết định nào

Tài liệu cho người mới: tool **tự học** như thế nào, từ số liệu YouTube Studio tới video kế tiếp, và chỗ nào vòng
còn hở. Cập nhật 12/10/2026 — **thước thắng chung** `core/thuoc_thang.py` (mục 0).

## 0. Thước thắng chung (12/10/2026) — MỘT định nghĩa cho V7, tự học, giám đốc kênh, bộ não

* Chuỗi số mỗi video: mọi bản chụp có số, **tuổi thật** = `captured_at` − giờ đăng (không tin nhãn thư mục), bỏ
  bản chép trùng và bản hỏng (số cộng dồn giảm).
* **Phân vị cùng tuổi**: hiển thị của video ở tuổi t so với ≤ 20 video gần nhất (theo giờ đăng) của CHÍNH kênh ở
  cùng tuổi t — chỉ dùng số chụp tới lúc **chốt** của video (đăng + 168h) → nhãn không trôi theo ngày.
* **Phán** từ bản muộn nhất trong 96–168h (không có: sớm nhất sau 168h; không có nữa mà video đã qua 96h: bản
  72–96h). 24–72h chỉ là **tín hiệu sớm**; **không bao giờ phán ở 48h**.
* Nhãn: `thang` = phân vị ≥ 75 và ≥ 2.000 hiển thị (hoặc ≥ 20.000 bất kể) · `truot` = phân vị < 40 hoặc < 300
  hiển thị · còn lại `trung_binh` · `chua_du`. Kênh < 4 tham chiếu: sàn tuyệt đối (≥ 5.000 thắng).
* "Đang nóng" (V7/bộ não nhân bản khi còn nóng, KHÔNG phải kết luận): chưa phán, tín hiệu sớm top 10% và ≥ 2.500.
* Giám đốc chỉ tạm bỏ cụm khi ≥ 6 video đã phán và P(cụm kém hơn nền) > 0,9.
* Chấm lại lịch sử ngay: `python -m core.thuoc_thang --ghi` (cùng đường mã vòng học / giám đốc dùng).

## 1. Sơ đồ vòng kín

```
                ┌──────────────────────────── ĐO ─────────────────────────────┐
  Studio (trình duyệt, 1 lần/ngày)                                             │
    → CHANNEL/<k>/chi-so/<video_id>/<mốc>/tong-quan.json                       │
    → ho_so_video.cap_nhat_chi_so  (vong_hoc bước 2)                           │
    → CHANNEL/<k>/ho-so-video/<mã gói>.json  chi_so{24h,48h,72h,7d}            │
                                                                               │
                ┌──────────────────────────── CHẤM ───────────────────────────┐│
  tu_hoc.cham_van  (vong_hoc bước 6, MỖI lượt, trước khi chọn video mới)      ││
    ván = một video, nhãn = `nuoc` {cum, cong_thuc, kieu_bia, do_dai,          ││
                                   kieu_tieu_de, hook, chu_bia_dai, mo_dau}    ││
                                   (nhãn CHUẨN; 2 trục cuối chỉ ĐO, 07/10)    ││
    ket     THƯỚC CHUNG (mục 0): thang 1 · trung_binh ½–½ · truot 1 (bản 72–96h ×0,75)││
            + ket_pv/ket_tuoi/ket_tin/ket_som; ket48 = bí danh hai mức của ket  ││
    ket7    giờ xem 7d ≥ trung vị kênh — chỉ để đọc, không vào bảng điểm        ││
    ket_ctr CTR 48h ≥ trung vị kênh — bìa, tiêu đề, chu_bia_dai nặng 0,5        ││
    → tu_hoc.bang_diem: Beta(a, b) mỗi (trục, giá trị) + tiên nghiệm nhóm ×0,3 ││
    → CHANNEL/<k>/tu-hoc/{van.json, bang-diem.md}                              ││
                                                                               ││
                ┌──────────────────────────── QUYẾT ──────────────────────────┐││
  tu_hoc.rut (Thompson) ← nao.ap_hieu_luc_rut (thu = 1,0 / tranh = 0,0)        │││
    cụm content   chien_luoc._ap_he_so_cum   điểm × (0,8 + 0,4·rút)  thu: ×1,5 │││
    vùng tấn công chien_luoc.tan_cong        điểm × (1 + 0,3·cơ hội/100) ≤+30% │││
    kiểu tiêu đề  auto_khau (chấm N bản)     điểm LLM × (0,9 + 0,2·rút)        │││
    hook          viet_nhieu_ban.thay_hook   điểm LLM × (0,9 + 0,2·rút)        │││
    kiểu bìa      chon_bia.chon              điểm giám khảo × (0,9 + 0,2·rút)  │││
                                                                               │││
                ┌──────────────────────────── SẢN XUẤT ───────────────────────┐│││
  bàn giao (tu_chay) → tu_hoc.ghi_van_tu_luot: ghi `nuoc` của video MỚI        ││││
    cụm = `cum_tu_hoc` (nhãn đã nhận hệ số lúc chọn) → ván tính đúng cánh tay ││││
    → nao.tru_luot: `thu` khớp nhãn trừ 1 lượt, ghi mã gói vào `tham_so.goi`   ││││
    → video đăng → Studio đo → quay lại ĐO ───────────────────────────────────┘│││
                                                                                └┘┘
```

## 2. Các vòng song song (học khác, cùng số đo)

| Tín hiệu đo | Bộ học | Quyết định nó lái |
|---|---|---|
| nhãn thước chung theo công thức (`chien_luoc.ket_qua.thong_ke`) | `chien_luoc.ke_hoach` khi `chien_luoc_tu_hoc: true` | tỉ trọng V7 / VPH / Một nút |
| CTR video thắng của chính kênh (`khuon_bia.tim_video_thang`) | AI tả ảnh bìa thật → `khuon-bia-thang.json` | kiểu bìa `khuon_thang` + khối `<<BAI_HOC_ANH_BIA>>` |
| khám nghiệm video 96h/7d (`giam_doc.kham_nghiem`, LLM; bài học chỉ khi video đã phán) | sổ `bai-hoc.jsonl`, bài "thật" khi ≥3 video ủng hộ | lời nhắc **kịch bản**, **tiêu đề** (viết + chấm), **bìa** |
| giờ xem / 1.000 hiển thị @52h (`giam_doc.do_dai`) | thí nghiệm của giám đốc kênh | `phut_muc_tieu` (độ dài) |
| bảng điểm + video 14 ngày + hành động tới hạn (`nao.bao_cao`) | bộ não hằng ngày (`nao/CLAUDE.md`) | `thu` / `tranh` (đè Thompson), `bai-hoc`, `de-xuat` |
| lệnh tấn công (`chien_truong.de_xuat_tan_cong`) | ghi `workspace/chien-truong/tan-cong.json` mỗi lần `tinh()` | trọng số mềm khi chọn content |

Bộ não chấm chính mình: lúc `kiem_ngay` tới, `xem` in **TỚI HẠN KIỂM** kèm số đo của đúng các video lần `thu` đã
sinh ra (`nao.ket_qua_goi`) → não `cham <id> dung|sai` → tỉ lệ đúng < 50% (≥10 lần chấm) thì quyền co còn 1 hành
động/ngày.

## 3. Luật nhãn (để điểm không bị chẻ)

* `tu_hoc.chuan_gia_tri` là MỘT luật cho mọi nơi đếm / rút / khớp `thu`: chữ thường; `kieu_bia` bỏ hậu tố số biến
  thể (`khuon_thang_2` = `khuon_thang`). Ván ghi nhãn chuẩn, bản thô để ở `kieu_bia_tho`.
* Cụm của một video là nhãn **lúc chọn** (`cum_tu_hoc`), không phân loại lại lúc bàn giao.
* Bộ cụm V7 trả `[]` → nhãn **theo nghĩa** (`core/cum_y_nghia`, 07/10/2026): một lượt LLM xếp tiêu đề vào MỘT cụm
  có sẵn hoặc `khac` (cũng là một cánh tay). Nhớ `CHANNEL/<k>/tu-hoc/cum-y-nghia.json`, mỗi tiêu đề hỏi một lần,
  ≤ 60 tiêu đề/lượt, qua van ví. Chạy ở `phan_cum_ai.lam_nong` (ứng viên lúc chọn) và `cham_van(dung_ai=True)`
  (bù hồi tố ván cũ). Ván ghi `nuoc.cum_nguon`: `nguon` | `tu_khoa` | `y_nghia`.
* Ván chỉ nhận `ket` khi thước chung đã PHÁN — cờ "đang nóng" / "thắng sớm" mốc 13h của V7 không vào ván.

## 4. Khi vòng hở — xem ở đâu

* Đường học hỏng không còn im lặng: `tu_hoc.canh_bao` → log + `workspace/tu-hoc/canh-bao.jsonl`.
* Báo cáo ngày (`core/bao_cao_ngay.py`, mục **Tín hiệu học thiếu/cũ**): video đăng ≥5 ngày chưa được thước chung phán,
  kênh có ≥ nửa số ván không nhãn cụm, vòng học không chấm lại > 48h, tệp lệnh chiến trường cũ, số cảnh báo học 24h.

## 5. Còn hở (chưa làm)

* Giờ đăng: cố định theo `kenh.yaml` (`gio_dang` / `nhip_dang`) — chưa có trục học.
* Độ dài: trục `do_dai` được chấm nhưng `rut` không lái; độ dài do thí nghiệm của giám đốc kênh quyết.
* Kênh không khai `chien_luoc` (đường "luật cũ", golden test canh từng byte) không nhận hệ số cụm lẫn lệnh tấn công.
* Ứng viên không có nhãn cụm (bộ cụm AI chưa phân, từ khoá trượt) → trục cụm không học được từ video ấy.
* Số Studio thiếu (bản chụp `impressions: null`) → ván chờ mãi; chỉ báo, chưa tự chụp lại.
