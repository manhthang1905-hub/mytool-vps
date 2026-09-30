# Thiết kế bộ máy chiến lược chọn content

Bộ máy này là **vòng học của từng kênh**, bọc quanh các công thức chọn nguồn. Mỗi công thức là một tệp nhỏ có 2 hàm; ngữ cảnh kênh là một dataclass; bộ điều phối chỉ vài chục dòng. Hướng dẫn vận hành (không cần đọc mã) nằm ở `chien-luoc.md`.

Mục tiêu thiết kế: **đơn giản, hiệu quả, dễ thêm công thức**, không cứng ngách / quốc gia / ngôn ngữ.

## 1. Bài học rút ra khi dựng (áp cho mọi lần sửa lớn)

- **Công thức dính cứng trong một hàm với nhiều nhánh `if`** sẽ có cách lùi khác nhau cho từng nhánh (có nhánh lùi sang công thức khác, có nhánh trả rỗng). Khi đóng gói thành plugin phải giữ đúng hành vi và **đúng thứ tự** các bước (ví dụ: cộng điểm anh em chạy SAU lọc loại trừ và lọc trùng tiêu đề, vì trần điểm tính trên bảng đã lọc).
- **Mọi nơi gọi cùng một bảng xếp hạng phải ra cùng kết quả** (vòng chọn nguồn và trạm lấy lời thoại). Vì vậy quyết định "thăm dò" phải **tất định**, không dùng số ngẫu nhiên.
- **Nháp cũ không được chép đè lên bản sống.** Bản sống thường đã thêm hàng trăm dòng sau khi viết nháp. Áp theo từng đoạn, đoạn nào không áp được thì chép tay theo nghĩa.
- **Bật đọc cấu hình mới (YAML ngách) chỉ sau khi đồng bộ nó với hằng số đang chạy**, kèm một test "YAML khớp hằng số" để việc bật không đổi một điểm số nào.
- **Rà hằng số cứng theo thị trường** (tên ngôn ngữ, tuổi khán giả, ví dụ bằng tiếng bản địa, ngưỡng view cố định) và chuyển chúng vào hồ sơ ngách.
- **Dữ liệu cho vòng học thường đã có sẵn nhưng nằm rải rác** (đường giữ chân từng video, bài học sản xuất, đánh giá dự đoán vs thật, insight nhóm, nhãn công thức ghi trong sổ lượt). Gom lại, đừng dựng thêm nguồn.

## 2. Giao diện công thức (plugin)

Gói `core/chien_luoc/`. Mỗi tệp không bắt đầu bằng `_` là một công thức, tự phát hiện bằng `pkgutil.iter_modules`. Tệp nhập hỏng thì ghi log rồi bỏ qua.

```python
# core/chien_luoc/<ten>.py — toàn bộ hợp đồng
TEN = "vph"; MO_TA = "…"; LUI_KHI_RONG = "mot_nut"   # "" = không lùi
def ap_dung(nc) -> float: ...     # 0..1 độ hợp với kênh/giai đoạn; 0 = không dùng được
def cham(nc) -> list[dict]: ...   # bảng ĐÃ XẾP, mạnh nhất trước, dòng chuẩn
```

**Dòng chuẩn** giữ nguyên tên khoá đang dùng: `nguon`, `ma`, `link`, `tieu_de`, `kenh` (kênh nguồn), `diem`, `loai`, `view`, `vph`, `dot_bien`, `tuoi_gio`, `cum`, `tuyen`, `ly_do[]`; thêm `cong_thuc`, `tham_do`, `tin_hieu{}`.

Công thức có sẵn:

| tệp | ý chính | hợp với |
|---|---|---|
| `vph.py` | trend / đột biến view-mỗi-giờ của đối thủ; rỗng thì lùi về Một nút | kênh mới |
| `v7.py` | remake theo cụm đã thắng của kênh (pool + bảng nhóm) | kênh đang lên / kiếm tiền; = 0 khi chưa có video thắng |
| `mot_nut.py` | gộp bảng mới / vượt / bứt + điểm anh em | đường lùi |
| `_mau.py` | khuôn chép cho công thức mới | |

Ý tưởng công thức sau (khung, `ap_dung` = 0 khi thiếu dữ liệu): xu hướng tìm kiếm, phần tiếp của video đã thắng, bám đối thủ lớn vừa vượt mức thường, mùa vụ theo quốc gia (`ngach.yaml: thi_truong.mua_vu`), video khán giả mình đang xem.

## 3. Ngữ cảnh kênh (`NguCanh`)

Chỉ đọc đĩa; hỏng chỗ nào thì trường đó để rỗng.

- **Định danh:** gốc, mã kênh, nhóm, tệp khán giả, thời điểm.
- **Ngách và thị trường:** hồ sơ ngách + `thi_truong` (quốc gia, ngôn ngữ, múi giờ, khung giờ đăng, phút mục tiêu, số ký tự bìa tối đa, bậc làm tròn view, CTR trang chủ mục tiêu, mùa vụ). **Thứ tự ưu tiên: kenh.yaml > ngach.yaml > mặc định trong mã** — cá nhân hoá theo kênh đứng trên hết.
- **Giai đoạn:** `moi` (chưa có video thắng) / `dang_len` / `kiem_tien` (đã khai hoặc đạt ngưỡng YPP). Chỉ 3 giai đoạn, vì chưa có luật nào cần giai đoạn thứ tư.
- **YPP:** sub, giờ xem, đang thiếu gì. Lưu ý số đọc từ Studio thường là 28 ngày, còn YPP tính 12 tháng → cho kenh.yaml ghi đè số trọn đời.
- **Bộ lọc:** loại trừ, tiêu đề đã làm, ngưỡng giống, `loc(ds)` (chạy lại vẫn cùng kết quả).
- **Mục tiêu:** `muc_tieu()` trả 3 dòng dùng cho mọi lời nhắc. *Ví dụ: "Kênh mới, thiếu N sub để bật kiếm tiền (giờ xem đã đủ). Tệp: … Video phải đạt CTR trang chủ ≥ X% @48h (bài học kênh, n=5)."*

## 4. Vòng học — trung tâm của bộ máy

Chọn → làm → đăng → Studio → **bài học ngắn có số** → tiêu chí chấm của công thức, bối cảnh biên tập viên, chấm kịch bản/hook.

**(a) Một chỗ đọc bài học** (`bai_hoc.py`): gộp mọi nguồn thành danh sách chuẩn `{pham_vi, truc, cau (≤2 câu, có số), n, tin_cay, dung_cho}`.

**Luật phạm vi (kênh > nhóm > ngoài):**
- bài học **kênh** luôn đứng trước;
- bài học **nhóm** chỉ vào khi kênh có n < 3 trên đúng trục đó, kèm nhãn "tiên nghiệm nhóm";
- bài học **ngoài** (từ VPS khác) chỉ vào khi kênh có n = 0;
- n < 3 thì chỉ ghi cho người đọc, không bơm vào lời nhắc.

**(b) Điểm thoát quay về khâu CHỌN.** Với mỗi video của mình: tính % còn lại ở 30s / 2 phút và "vách" (đoạn rơi dốc nhất), nối ngược tới nguồn, xếp "rơi sớm" / "giữ tốt" so với trung vị kênh. Sinh ra:
1. bài học có số theo cụm (*"cụm X: còn 41% ở 2:00, kênh trung vị 52%, n=3"*), công thức đọc để cộng/trừ nhẹ;
2. khối "nguồn của video giữ tốt / rơi sớm" cho biên tập viên AI so **theo nghĩa**. Không dựng máy so khớp riêng.

**(c) Kết quả theo công thức:** nối sổ lượt (nhãn công thức) với hồ sơ video (mốc 48h/72h). **"Thắng" đo theo chính kênh** (ngưỡng tương đối theo trung vị kênh), không dùng một con số cứng chung. Sổ cũ cũng thống kê ngược được nhờ nhãn đã ghi sẵn.

## 5. Bộ điều phối

Cấu hình phẳng trong kenh.yaml:

```yaml
chien_luoc: "vph:0.7, v7:0.3"   # hoặc "tu_dong"; không khai → luật cũ 1 công thức
chien_luoc_tham_do: 20          # % lượt thăm dò
chien_luoc_tu_hoc: false        # true → tự dồn tỉ trọng; false → chỉ ghi gợi ý
```

- `tu_dong`: công thức `ap_dung` cao nhất 0,8, thứ hai 0,2. Bỏ tên lạ và công thức `ap_dung == 0`.
- Tự học: `w ← w × (thắng+1)/(n+2)`, kẹp [0,1; 0,9], chuẩn hoá; chỉ áp khi tổng n ≥ 6.
- **Thăm dò tất định:** `hash(kênh|ngày|số lượt hôm nay) % 100 < tham_do`; công thức được thăm dò là cái ít n nhất trong 14 ngày. Kênh mới: thăm dò ưu tiên **cụm kênh chưa thử lần nào** — kênh non tự thăm dò trên chính mình thay vì mượn nhóm.
- **Trộn theo THỨ HẠNG** (vòng xoay có trọng số), không so điểm giữa các công thức vì thang điểm khác nhau. Khử trùng theo mã; video trùng ghi "được 2 công thức cùng chọn".
- Chỉ 1 công thức thì kết quả trùng hệt bảng cũ (kiểm bằng golden test).
- Sau đó vẫn qua đường cũ: phân cụm AI, biên tập viên AI (TỐT/TẠM/TỆ), cổng chất lượng, kiểm trùng ý. **Biên tập viên AI chốt cuối.** Nhãn `cong_thuc`/`tham_do` đi theo vào hồ sơ video và thống kê.

## 6. Lời nhắc ngắn, nêu mục tiêu

Mẫu chung: **MỤC TIÊU** (3 dòng) + **TIÊU CHÍ** (bài học, tối đa 8) + **DỮ LIỆU** + **DẠNG TRẢ LỜI**.
- Xoá mọi chữ cứng theo thị trường khỏi đề bài (ngôn ngữ, tuổi, quốc gia, ví dụ bản địa); thay bằng ô đọc từ hồ sơ ngách: `mo_ta_ngach`, `luat_chon`, `vi_du_phan_cum`, `thi_truong.quoc_gia`.
- Khối dữ liệu nhóm chỉ đưa vào khi kênh còn ít video riêng.

## 7. Thừa hưởng nhóm phải giảm dần

Nguyên tắc: **mỗi kênh tự tối ưu; dữ liệu nhóm chỉ là tiên nghiệm yếu khi kênh chưa có số.**

Hàm chung `he_so_tien_nghiem(n48, he_so, k=2, tat_khi=6) = he_so × k/(k+n48)`, về 0 khi n48 ≥ 6 (n48 = số video riêng đã đủ 48h).

| tham số | trước | sau |
|---|---|---|
| hệ số mượn | 0,5 (tối đa 15/100 điểm) | 0,35 (không tự đẩy một dòng lên "Làm ngay") |
| cách giảm | theo cụm | nhân thêm hệ số giảm toàn kênh |
| tắt khi thắng riêng | ≥ 3 | ≥ 2 |
| video riêng trượt trong cụm | vẫn giữ điểm mượn | 1 video riêng trượt đủ 48h → bỏ phần mượn của cụm |
| hệ số ngoài tệp | 0,8 | 0,5 |

Lưu ý: giá trị lưu sẵn trong tệp cấu hình từng kênh (`cong-thuc-v7.json`) **đè lên mặc định trong mã** — đổi mặc định không đủ, phải sửa (có sao lưu) các tệp đó.

## 8. Nhiều VPS, nhiều ngách, nhiều quốc gia

- Hồ sơ ngách có thêm `thi_truong`, `luat_chon`, `vi_du_phan_cum` — đều tuỳ chọn, rỗng thì dùng mặc định.
- Mẫu ở `CHANNEL/_KHUON/`: `ngach-mau.yaml` (chung, có chú thích), `ngach-mau-ja-tam-ly.yaml` (bản đầy đủ đang chạy), `ngach-mau-vi.yaml`, `ngach-mau-en-us.yaml` (khung).
- **Chia sẻ bài học giữa VPS**, không cần mạng: `python -m core.chien_luoc --xuat-bai-hoc <nhom> <tep.json>` (không kèm mã kênh hay đường dẫn) và `--nhap-bai-hoc <tep.json>` → `_NHOM/<nhom>/bai-hoc-ngoai/`. Bài nhập là tiên nghiệm yếu nhất (chỉ dùng khi n = 0).
- Tiêu chí sẵn sàng: một kênh giả ngách khác (*ví dụ "nấu ăn tiếng Việt"*) chạy khô chọn được nguồn.

## 9. Cách chuyển đổi trên máy đang chạy thật

- Viết nháp → `py_compile` → thay tệp một lần trọn vẹn trong khung phút **:15–:45** (xem `luat-van-hanh-vps.md`).
- **Golden test trước khi sửa:** chụp đầu ra hàm xếp hạng hiện tại trên vài fixture kênh giả; mọi bước sau phải khớp từng byte khi chưa khai khoá mới.
- Chỉ chạy test liên quan, không chạy toàn kho. Mỗi bước ghi nhật ký. Bật thử chiến lược mới trên **1 kênh** trước.
- Chia việc cho nhiều agent theo **tệp độc quyền, không giẫm nhau**; tệp dùng chung thì làm tuần tự.
