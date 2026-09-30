# Phát triển trên nhiều VPS: một kho chung

Kho `github.com/manhthang1905-hub/mytool-vps` là **nguồn gốc duy nhất** của mã
tool. Mỗi VPS chạy một ngách hoặc một quốc gia riêng. Sửa ở máy nào thì máy đó
đẩy lên kho (`day` **tự nâng phiên bản**), các máy khác **tự nhận bản mới** lúc
rảnh — mặc định bật, tắt được trong Cài đặt. Càng nhiều VPS thì tool càng được
sửa nhiều.

Tóm tắt một vòng:

1. Máy A sửa xong: `python -m core.dong_bo_git day "fix(...): ..."` → kiểm, commit,
   rebase, `VERSION` +patch (hoặc `--minor`/`--major`), một dòng `CHANGELOG.md`,
   tag `v<x.y.z>`, push.
2. Máy B (mỗi ~30 phút, trong gác tổng 15' và giao diện; và mỗi lần mở giao
   diện): `git fetch`, đọc `origin/main:VERSION` → ghi
   `workspace/cap-nhat/trang-thai.json`.
3. Có bản mới + `tu_dong_cap_nhat` bật + máy rảnh → máy B tự áp (mục 3) rồi tự mở
   lại giao diện. Tắt tự động thì chỉ báo "Có bản mới x.y.z" (Bảng điều khiển +
   Cài đặt) và chờ người bấm **Cập nhật ngay**.

Xem nhanh bản đang chạy và bản trên kho: `python -m core.dong_bo_git kiem`.

Công cụ dùng cho việc này: `python -m core.dong_bo_git <lệnh>` (chạy tại thư mục
gốc MyTool).

| lệnh | làm gì |
|---|---|
| `ket_noi` | Kiểm đường tới GitHub. Máy có IPv4 thì đi thẳng; máy chỉ có IPv6 thì dò NAT64 qua DNS64 và sửa `HostName` của `Host github-mytool` trong `~/.ssh/config`. Cuối cùng thử xác thực bằng deploy key. |
| `trang_thai` | Cho biết nhánh, số commit máy này đi trước hay sau origin, và các tệp đã đổi. |
| `day "thông điệp" [--minor\|--major] [--chi tệp…]` | Kiểm, commit, rebase lên origin, **tự nâng phiên bản** + CHANGELOG + tag, push (mục 2). `--chi`: chỉ commit các tệp đó, tệp dở của người khác để nguyên. |
| `kiem` | Kiểm có bản mới không (fetch, đọc `origin/main:VERSION`, in các thay đổi). |
| `keo [--ep]` | Áp bản mới an toàn (mục 3). Thường do `core.cap_nhat_git.nhip` tự sinh ra; `--ep` = như nút "Cập nhật ngay". |
| `lui [--tag T]` | Quay lại bản trước (tag `truoc-cap-nhat-*`), như nút "Quay lại bản trước". |
| `quet` | Chỉ quét bí mật và dữ liệu kênh trên toàn bộ tệp sẽ lên kho. |
| `bai_hoc` | Xuất bài học ngách của máy này ra `chia-se/bai-hoc/`. |
| `lich bat` | Bảo đảm lịch `ShopAPI-GacTong` (15', trong đó có kiểm cập nhật) và gỡ lịch `ShopAPI-DongBoGit` 03:40 cũ. |

Tắt/bật tự cập nhật: công tắc **Tự động cập nhật** (Cài đặt → Cập nhật tool), hoặc
`python -m core.cap_nhat_git tu_dong tat|bat` — ghi `tu_dong_cap_nhat` trong `cap-nhat.json`.

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
7. **Tự cập nhật: đã BẬT sẵn** (kể cả khi chưa có `cap-nhat.json`). Chỉ cần đặt mã máy
   trong `cap-nhat.json`: `{"dong_bo_git": {"ma_may": "<ma-may>"}}` (mẫu:
   `cap-nhat.example.json`), rồi `python -m core.dong_bo_git lich bat` để có gác tổng
   15' (giao diện đang mở cũng tự kiểm mỗi 30'). VPS nào đã ổn định muốn giữ nguyên:
   tắt công tắc **Tự động cập nhật** trong Cài đặt.

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
   - commit, `fetch`, rebase lên `origin/main` (có tệp dở thì `--autostash`);
   - **nâng phiên bản** trong một commit riêng `v<x.y.z>: <thông điệp>`: số mới =
     max(VERSION của máy, của origin) +patch (`--minor`, `--major`), thêm một dòng
     `- **x.y.z** — ngày — `mã máy` — thông điệp` vào mục tự ghi của `CHANGELOG.md`,
     tag `v<x.y.z>`;
   - push nguyên tử (`--atomic`: nhánh + tag). Máy khác vừa đẩy (bị từ chối) thì
     bỏ commit phiên bản, kéo lại, rebase, **tăng lại số** — hai máy không bao giờ
     cùng một phiên bản.

   Còn tệp dở của người/agent khác trên máy? Dùng `--chi <tệp của mình…>`: chỉ
   những tệp đó được commit, phần còn lại để nguyên.

   Nếu rebase gặp **xung đột**, lệnh huỷ rebase và báo tên các tệp bị xung đột.
   Commit trên máy vẫn còn nguyên. Người sửa tự giải xung đột rồi chạy lại
   `day`, không để máy tự giải.
3. Các máy khác **tự nhận** bản mới (mục 3) — không còn lịch 03:40.

Chuỗi mẫu trong test cố tình trông giống khoá (để kiểm bộ lọc) phải được viết
tách, ví dụ `"sk_live_" "abc…"`, hoặc cuối dòng có đánh dấu `# dong-bo-git: mau`.

## 3. Máy sản xuất tự nhận bản mới thế nào

**Kiểm** (`core/cap_nhat_git.py: nhip`, mỗi ~30 phút qua gác tổng và giao diện, và
khi mở giao diện): `git fetch` → `origin/main:VERSION` + các dòng CHANGELOG mới
hơn bản đang chạy → `workspace/cap-nhat/trang-thai.json` (hiện tại, bản mới, thay
đổi, lần kiểm, kết quả lần cập nhật gần nhất, lỗi, sửa chưa đẩy). Có bản mới +
tự động bật (hoặc người đã bấm "Cập nhật ngay") + máy rảnh → sinh tiến trình tách
rời `dong_bo_git keo` (không là con cháu của giao diện, nên khởi động lại giao
diện không giết nó). Bận thì ghi "sẽ cập nhật khi máy rảnh" và thử lại nhịp sau.

**`keo`** làm:

1. Thoát ngay nếu `tu_dong_cap_nhat` đang tắt (gọi `--ep` thì bỏ qua khoá này).
   Chỉ một lượt cập nhật mỗi lúc (khoá `workspace/cap-nhat/dang-cap-nhat.json`).
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
   chết 3 lần kiểm liền, tool **tự lùi về tag** rồi khởi động lại, ghi lý do, và
   **bỏ qua** bản hỏng đó cho tới khi kho có bản mới hơn (bản không qua kiểm ở
   bước 3 cũng vậy).

Nút **Quay lại bản trước** (`lui`) về tag `truoc-cap-nhat-*` mới nhất theo cùng luật
máy rảnh, và cũng bỏ qua bản đang có trên kho cho tới khi có bản mới hơn.

Trạng thái: `workspace/cap-nhat/trang-thai.json`, nhật ký `workspace/cap-nhat/nhat-ky.txt`
và `workspace/dong-bo-git/nhat-ky.txt`. **Một hệ duy nhất**: đường ZIP
(`core/cap_nhat_github.py`, `cap-nhat.py`) và manifest (`core/nguon_cap_nhat.py`)
không còn áp mã lên máy nào; máy có `.git` thì chúng luôn nhường.

## 4. Cấu hình riêng của mỗi máy (KHÔNG lên kho)

| tệp | nội dung | mẫu |
|---|---|---|
| `config.json` | địa chỉ máy chủ, số job | `config.example.json` |
| `secrets.json` | khoá API, đã mã hoá DPAPI theo máy | tool tự tạo khi đăng nhập |
| `cap-nhat.json` | `kho`, `nhanh`, `tu_dong_cap_nhat` (mặc định true), `dong_bo_git.ma_may`… | `cap-nhat.example.json` |
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
- Khi máy tự nhận bản mới (`keo`), tệp của **máy khác** cùng ngách được chép vào
  `CHANNEL/_NHOM/<ngach>/bai-hoc-ngoai/`. `bai_hoc` đọc những tệp này làm tiên
  nghiệm "ngoài": yếu nhất, chỉ dùng khi kênh chưa có số riêng.
- Tri thức dạng văn bản (con đường kênh thắng, thiết kế chiến lược, nghiên cứu
  bìa, luật vận hành) nằm ở `docs/kien-thuc/`.
