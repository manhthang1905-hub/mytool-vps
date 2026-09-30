# Phát triển trên nhiều VPS: một kho chung

Kho `github.com/manhthang1905-hub/mytool-vps` là **nguồn gốc duy nhất** của mã
tool. Mỗi VPS chạy một ngách hoặc một quốc gia riêng. Sửa ở máy nào thì máy đó
đẩy lên kho, các máy khác tự kéo về. Càng nhiều VPS thì tool càng được sửa
nhiều.

Công cụ dùng cho việc này: `python -m core.dong_bo_git <lệnh>` (chạy tại thư mục
gốc MyTool).

| lệnh | làm gì |
|---|---|
| `ket_noi` | Kiểm đường tới GitHub. Máy có IPv4 thì đi thẳng; máy chỉ có IPv6 thì dò NAT64 qua DNS64 và sửa `HostName` của `Host github-mytool` trong `~/.ssh/config`. Cuối cùng thử xác thực bằng deploy key. |
| `trang_thai` | Cho biết nhánh, số commit máy này đi trước hay sau origin, và các tệp đã đổi. |
| `day "thông điệp"` | Kiểm rồi commit, rebase lên origin, push (chi tiết ở mục 2). |
| `keo [--ep]` | Tự cập nhật an toàn trên máy sản xuất (chi tiết ở mục 3). |
| `quet` | Chỉ quét bí mật và dữ liệu kênh trên toàn bộ tệp sẽ lên kho. |
| `bai_hoc` | Xuất bài học ngách của máy này ra `chia-se/bai-hoc/`. |
| `lich bat` / `lich tat` | Bật hoặc tắt lịch Windows `ShopAPI-DongBoGit`, chạy `keo` mỗi ngày. |

## 1. Cài một VPS mới từ kho

1. **Tạo deploy key riêng cho máy.** Mỗi máy một khoá, không chép khoá từ máy khác:
   `ssh-keygen -t ed25519 -f %USERPROFILE%\.ssh\mytool_vps_deploy -N "" -C mytool-<ma-may>`.
   Chủ dự án thêm tệp `.pub` vào GitHub tại Settings > Deploy keys, **bật Allow write access**.
2. **Mở đường SSH.** Máy có IPv4 thì bỏ qua bước này. Máy chỉ có IPv6 thì hỏi AAAA
   tổng hợp qua DNS64 (`2a00:1098:2b::1`, `2a00:1098:2c::1`, `2a01:4f8:c2c:123f::1`):
   `Resolve-DnsName github.com -Type AAAA -Server 2a00:1098:2b::1`.
   Sau đó ghi vào `%USERPROFILE%\.ssh\config`:

   ```
   Host github-mytool
       HostName <địa chỉ AAAA vừa dò>
       HostKeyAlias github.com
       User git
       IdentityFile ~/.ssh/mytool_vps_deploy
       IdentitiesOnly yes
   ```

   Lần đầu phải kiểm vân tay khoá ED25519 của GitHub (so với trang
   docs.github.com "GitHub's SSH key fingerprints"), rồi mới thêm vào `known_hosts`.
3. **Clone:** `git clone git@github-mytool:manhthang1905-hub/mytool-vps.git MyTool`.
   Muốn clone qua HTTPS trên máy chỉ có IPv6 thì dùng
   `git -c http.curloptResolve=github.com:443:[<AAAA>] clone https://github.com/manhthang1905-hub/mytool-vps.git MyTool`.
4. **Cài:** chạy `MyTool\CAI-DAT-VPS.bat`. Bước này chạy SETUP.bat, cài thư viện
   cho vm/, ghi vps.json, tạo vm/config.json, sinh CLAUDE.local.md và đăng ký các lịch.
5. **Tạo cấu hình riêng của máy** từ các tệp mẫu (xem mục 4), rồi thêm kênh
   (theo `docs/THEM-KENH.md`).
6. **Kiểm:** chạy `python -m core.dong_bo_git ket_noi`, sau đó `trang_thai`.
7. **Bật tự kéo:** trong `cap-nhat.json`, đặt `"dong_bo_git": {"tu_keo": true, "ma_may": "<ma-may>"}`,
   rồi chạy `python -m core.dong_bo_git lich bat`.

## 2. Quy trình phát triển (cho người và cho phiên Claude)

1. Sửa mã theo đúng luật vận hành (`docs/kien-thuc/luat-van-hanh-vps.md`):
   - chỉ thay tệp mã sống trong khung phút :15–:45;
   - sao lưu vào `workspace/ban-va/<ngày>-<việc>/`;
   - chỉ chạy test lẻ có liên quan, **không** pytest toàn kho trên máy sản xuất.
2. **Sửa xong thì chạy** `python -m core.dong_bo_git day "feat(...): mô tả ngắn"`. Lệnh này:
   - `git add -A` (chỉ những tệp `.gitignore` danh sách trắng cho phép);
   - py_compile các tệp .py đã đổi;
   - kiểm khói: import các module chính, rồi chạy nhóm test nhanh `TEST_NHANH`
     ở ưu tiên thấp, chỉ khi khe "nang" đang trống;
   - quét bí mật: `core/kiem_phat_hanh.py` cộng thêm lớp quét khoá, email,
     đường có tên người dùng, tên kênh thật, video id và tiêu đề video của máy này;
   - commit, `fetch`, rebase lên `origin/main`, rồi push.

   Nếu rebase gặp **xung đột**, lệnh huỷ rebase và báo tên các tệp bị xung đột.
   Commit trên máy vẫn còn nguyên. Người sửa tự giải xung đột rồi chạy lại
   `day`, không để máy tự giải.
3. Các máy khác tự nhận bản mới qua `keo`. Lịch chạy mỗi ngày lúc 03:40, hoặc
   gọi tay bằng `keo --ep`.

Chuỗi mẫu trong test cố tình trông giống khoá (để kiểm bộ lọc) phải được viết
tách, ví dụ `"sk_live_" "abc…"`, hoặc cuối dòng có đánh dấu `# dong-bo-git: mau`.

## 3. `keo` trên máy sản xuất làm gì

1. Thoát ngay nếu `tu_keo` đang tắt (gọi `--ep` thì bỏ qua khoá này).
2. Nếu máy **có sửa cục bộ chưa commit, hoặc có commit chưa đẩy**, lệnh KHÔNG
   kéo đè mà báo "máy này có sửa chưa đẩy".
3. `fetch`. Nếu có commit mới thì dựng bản đó trong một **git worktree tạm**
   (nằm ngoài MyTool), rồi chạy py_compile toàn bộ và kiểm khói trên bản tạm đó.
   Không đạt thì không áp.
4. Chờ máy rảnh, tối đa `cho_toi_da_phut` phút. Máy được coi là rảnh khi đủ cả:
   - đang trong khung phút :15–:45;
   - `core.an_toan_khoi_dong` đồng ý;
   - khe "nang" trống;
   - không có lượt AUTO nào đang ở khâu dựng hoặc phụ đề.

   Trong lúc áp, tool giữ khe "nang".
5. Gắn tag `truoc-cap-nhat-<ts>` để lùi được, rồi `git merge --ff-only`, rồi
   kiểm khói lại. Hỏng thì `reset --hard` về tag.
6. Khởi động lại giao diện. Giao diện mới tự mở lại ba tiến trình con của vm/.
   Lịch `tu_chay` mở tiến trình mới cho mỗi lượt nên tự nhận mã mới.
7. Theo dõi `theo_doi_phut` phút. Nếu giao diện hoặc agent vm/ (cổng 8767)
   chết 3 lần kiểm liền, tool **tự lùi về tag** rồi khởi động lại.

Nhật ký nằm ở `workspace/dong-bo-git/nhat-ky.txt`, trạng thái ở `workspace/dong-bo-git/trang-thai.json`.
Đường cập nhật cũ qua manifest (`core/nguon_cap_nhat.py`) dành cho bản cài không có `.git`.
Máy đã bật `tu_keo` thì đường manifest tự nhường, nên không có hai hệ cùng thay tệp.

## 4. Cấu hình riêng của mỗi máy (KHÔNG lên kho)

| tệp | nội dung | mẫu |
|---|---|---|
| `config.json` | địa chỉ máy chủ, số job | `config.example.json` |
| `secrets.json` | khoá API, đã mã hoá DPAPI theo máy | tool tự tạo khi đăng nhập |
| `cap-nhat.json` | khoá `dong_bo_git` (tu_keo, gio, ma_may…) | `cap-nhat.example.json` |
| `vps.json`, `workspace/cai-dat.json` | dấu chế độ VPS, cài đặt vận hành | CAI-DAT-VPS.bat tạo |
| `vm/config.json`, `vm/cai-dat-tool.json` | máy đăng: kênh, trình duyệt | `vm/config.example.json` |
| `CHANNEL/<kênh>/` | kênh thật: kenh.yaml, chỉ số, nghiên cứu, hồ sơ video | `CHANNEL/_KHUON/` |
| `CLAUDE.local.md` | luật riêng của máy, sinh từ `vm/VPS-CLAUDE.md` | |
| `PROJECTS/`, `DONE/`, `workspace/`, `vm/logs/` | dữ liệu chạy | |

`.gitignore` là **danh sách trắng**: mọi thứ ở gốc đều bị chặn, trừ những gì
được khai rõ. Muốn thêm một tệp hay thư mục mới ở gốc lên kho thì phải mở lối
cho nó trong `.gitignore`.

## 5. Thêm ngách hoặc quốc gia mới

1. Chép một khuôn trong `CHANNEL/_KHUON/` (ví dụ `ngach-mau-en-us.yaml`,
   `ngach-mau-ja-tam-ly.yaml`) thành `CHANNEL/_NHOM/<ngach>/ngach.yaml`, rồi sửa
   ngôn ngữ, thị trường, mốc tuổi, từ loại trừ…
2. Ghi tri thức chọn content của ngách vào `CHANNEL/_NHOM/<ngach>/INSIGHT-CHON-CONTENT.md`.
3. Hai tệp trên **lên kho**: máy khác cùng ngách dùng chung được. Các tệp khác
   trong `_NHOM/<ngach>/` (bảng nhóm, nghiên cứu, lời thoại) ở lại trên máy.
4. Kênh mới trên máy thì theo `docs/THEM-KENH.md`, đặt `nhom: <ngach>` trong kenh.yaml.
5. Nếu phải sửa mã cho ngách mới (ngôn ngữ, định dạng ngày…), sửa theo cách
   **tổng quát**, đọc từ ngach.yaml, không viết cứng tên ngách. Rồi chạy `day`.

## 6. Chia sẻ bài học giữa các máy

- `python -m core.dong_bo_git bai_hoc` (cũng tự chạy trong `day`) gom các bài học
  phạm vi kênh có n ≥ 3 (`core.chien_luoc.bai_hoc`) vào
  `chia-se/bai-hoc/<ma-may>-<ngach>.json`. Mỗi máy một tệp cho mỗi ngách, nên
  push không xung đột. Câu nào có tên kênh thật, video id, URL hoặc email thì
  bị bỏ.
- Khi `keo` nhận bản mới, tệp của **máy khác** cùng ngách được chép vào
  `CHANNEL/_NHOM/<ngach>/bai-hoc-ngoai/`. `bai_hoc` đọc những tệp này làm tiên
  nghiệm "ngoài": yếu nhất, chỉ dùng khi kênh chưa có số riêng.
- Tri thức dạng văn bản (con đường kênh thắng, thiết kế chiến lược, nghiên cứu
  bìa, luật vận hành) nằm ở `docs/kien-thuc/`.
