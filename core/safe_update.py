"""Cap nhat Studio: staging, atomic swap va rollback.

Module khong tu goi mang. Ben goi tai ZIP ve roi truyen bytes vao day. Viec
apply nen do launcher rieng goi sau khi GUI thoat.

═══ PHẦN CHỮ KÝ ED25519 ĐÃ ĐƯỢC GỠ ═══

`verify_manifest`/`canonical_manifest`/`_ed25519_verify` từng kiểm chữ ký của
manifest do máy chủ ShopAPI ký. Chúng chết cùng `GET /v1/tools/studio-update/*`:
tool nay đối chiếu phiên bản thẳng với kho GitHub (`core/cap_nhat_github.py`).

Điều còn lại và **không được bỏ**: `stage_update` vẫn đối chiếu SHA-256 cùng
kích thước ZIP, vẫn chặn path traversal, symbolic link và bom giải nén. Đó là
lớp phòng thủ duy nhất còn đứng giữa một ZIP tải từ Internet và thư mục cài đặt
của khách.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import time
from typing import Any, Callable, List, Mapping, Optional, Tuple, Union
import zipfile


#: Những thứ THUỘC VỀ KHÁCH — cập nhật là thay mã, không được đụng tới chúng.
#:
#: Danh sách này **không còn là tấm chắn duy nhất** kể từ 15/08/2026, nhưng vẫn
#: là tấm chắn đáng tin nhất — hãy đọc kỹ trước khi bỏ tên nào ra.
#:
#: Trước đó cập nhật tráo cả thư mục cài, nên thứ gì không có tên ở đây là mất
#: vĩnh viễn sau một lần bấm Cập nhật: không thùng rác, không hỏi lại. Danh
#: sách đã quên bốn lần và cả bốn đều là đồ khách (xem đoạn dưới, và `CHANNEL`
#: trong `HOA_NHAP`).
#:
#: `apply_tai_cho` giờ có thêm một luật **không cần ai nhớ**: thứ gì bản mới
#: không mang theo thì không đụng vào. Nhờ vậy thư mục lạ do khách tạo tự động
#: an toàn. Nhưng danh sách này vẫn cần, vì nó che những cái tên **có** trong
#: bản mới mà bản của khách phải thắng — `config.json`, `.claude`, `workspace`.
#:
#: `ket-qua`, `phien-viet`, `mau-kich-ban` thêm ngày 12/08/2026: ba thư mục này
#: sinh ra sau khi danh sách được viết, và tới lúc thêm thì chúng đang nằm ngoài
#: — tức là bản cập nhật đầu tiên sẽ xoá sạch file khách đã tạo, toàn bộ phiên
#: chat viết kịch bản, và mọi template họ tự dựng. Thêm thư mục dữ liệu mới mà
#: quên dòng này là lặp lại đúng cái bẫy đó.
PRESERVE = (
    "config.json", "secrets.json",
    "workspace", "models", "user-tools",
    "ket-qua",        # sản phẩm khách đã tạo (mặc định lưu ngay trong thư mục cài)
    "phien-viet",     # phiên chat của tab Viết kịch bản
    "mau-kich-ban",   # template prompt khách tự lưu
    "skill-cua-toi",  # Skill Agent đẻ ra riêng cho khách (`core.skill_rieng`)
    "PROJECTS",     # MỌI sản phẩm của khách, xếp theo dự án (core.du_an).
                     # Mất thư mục này là mất cả kịch bản, giọng, ảnh, bản dựng.
    "runtime",       # Mọi bản gói sẵn tool tự tải: Node (`core.node_goi_san`,
                     # 35 MB) và FFmpeg (`core.ffmpeg_goi_san`, 40 MB). Tải lại
                     # mỗi lần cập nhật là phí băng thông khách — mà nhiều
                     # người ở đây trả tiền theo dung lượng.
    ".claude",        # cấu hình Claude Code của riêng thư mục này, có KHOÁ của
                      # khách trong đó (`core.claude_code`). Mất là mỗi lần cập
                      # nhật khách lại phải vào tab Agent bấm lại từ đầu — mà họ
                      # sẽ không đoán được vì sao Claude Code đòi đăng nhập lại.
    ".venv",          # môi trường Python RIÊNG của thư mục tool (SETUP.bat
                      # dựng, 01/09/2026 — "những gì tool cần thì nằm trong thư
                      # mục tool"). Cả trăm MB thư viện; xoá là tool KHÔNG MỞ
                      # LÊN ĐƯỢC ngay sau cập nhật vì lối tắt trỏ thẳng vào
                      # .venv\Scripts\pythonw.exe.
    "venv",           # tên cũ cùng vai — hai launcher đều nhận cả hai tên.

    # ── Thêm 29/09/2026 (Đợt 5.2), sau khi phát hiện `vm` đè trắng ────────
    # (xem `HOA_GIU_TRANG_THAI` ngay dưới) — bốn tên này SINH RA TRÊN VPS,
    # không phải trên máy dựng bản cập nhật, nên rất dễ quên y hệt `CHANNEL`
    # đã từng bị quên.
    "vps.json",       # dấu CHẾ ĐỘ VPS (`core.che_do_vps.la_vps`) — mất là máy
                      # tưởng mình là máy nhà: đổi cả trang mở đầu lẫn trần
                      # song song Chrome/FFmpeg (VPS lại tranh RAM như cũ).
    "DONE",           # gói video đang chờ đăng, `vm/may_dang.py` đọc thẳng từ
                      # đây. Mất là video đã sản xuất xong biến mất trước khi
                      # kịp đăng lên kênh thật.
    "bao-dong.json",  # nhật ký báo động ĐÃ gửi. Mất là báo động cũ gửi lại
                      # từ đầu — dội tin nhắn cho đúng chuyện đã báo rồi.
    "CLAUDE.local.md", # tự sinh riêng cho VPS từ `vm/VPS-CLAUDE.md` lúc cài
                      # (`vm/cai_dat_vps.py`), không phải mã dùng chung — đè
                      # mất là mất luôn luật riêng của máy này.
    "mang-youtube.json", # bản đồ mạng/kênh đối thủ, tích luỹ theo thời gian.
                      # Mất là phải quét nghiên cứu đối thủ lại từ đầu.
)
#: Thư mục **hoà vào nhau**: giữ nguyên thứ khách đang có, chỉ thêm thứ còn thiếu.
#:
#: `PRESERVE` không dùng được cho `CHANNEL`, và để nguyên như cũ cũng không
#: được — hai đằng đều sai một nửa:
#:
#: * Bỏ ngoài `PRESERVE` (như trước 15/08/2026): mỗi lần cập nhật là **xoá sạch
#:   lời nhắc khách đã sửa và mọi kênh họ tự tạo**. Mà cả hộp "Quản lý kênh"
#:   sinh ra để mời khách sửa đúng những tệp ấy — tool vừa bảo họ sửa, vừa xoá
#:   công của họ ở lần cập nhật kế tiếp. Không thùng rác, không hỏi lại.
#: * Cho vào `PRESERVE`: khách giữ được đồ, nhưng **không bao giờ** nhận được
#:   kênh mẫu mới hay lời nhắc được cải tiến ở các bản sau.
#:
#: Nên hoà: tệp nào khách đã có thì để nguyên, tệp nào bản mới có mà máy khách
#: chưa có thì thêm vào. Kênh mẫu mới xuất hiện, kênh cũ của khách không suy
#: suyển.
#:
#: ═══ 26/08/2026: KÊNH MẪU THÌ ĐÈ, KÊNH RIÊNG THÌ GIỮ ═══
#:
#: Luật "không đè thứ khách đã có" có mặt trái: kênh mẫu (`TL4-T7`…) cũng
#: không bao giờ nhận được bản cải tiến của tool. Chủ dự án: *"các template đó
#: tao có cập nhật nên nếu khách dùng và tùy chỉnh thì khi update sẽ bị đè,
#: nên tao muốn những template khách tạo sẽ không bị đè"*. Nên trong `CHANNEL`:
#:
#: * thư mục kênh mà `kenh.yaml` của KHÁCH có `kenh_rieng: true` (tạo mới hay
#:   nhân bản từ mẫu — `core/kenh.nhan_ban_kenh`): chỉ thêm tệp còn thiếu;
#: * thư mục khác mà bản mới mang theo (kênh mẫu, `_KHUON`, `_MAU-GON`): tệp
#:   của bản mới **thắng**, tệp khách thêm vào (bộ vẽ riêng…) vẫn để nguyên;
#: * thứ bản mới không mang theo: không đụng (luật chung ở `apply_tai_cho`).
#:
#: Giao diện nói rõ điều này: kênh mẫu có nhãn "mẫu" và nút Nhân bản; Quản lý
#: kênh hỏi lại trước khi lưu vào mẫu.
HOA_NHAP = ("CHANNEL", "agent-skills")

#: Thư mục hoà kiểu THỨ BA — khác cả `PRESERVE` (giữ nguyên, không nhận mã
#: mới) lẫn `HOA_NHAP` (chỉ thêm-thiếu, không đè mã cũ). `vm/` cần NGƯỢC LẠI:
#: mã (`agent.py`, `may_dang.py`, `tien-ich/*/manifest.json`…) phải nhận bản
#: mới THẮNG như mọi thư mục mã khác, nhưng TRẠNG THÁI MÁY THẬT nằm lẫn bên
#: trong (`config.json`, `tokens/`, `replied/`, `logs/so-video-id.json`…)
#: tuyệt đối không được đụng.
#:
#: ═══ 29/09/2026: `vm` KHÔNG Ở `PRESERVE` CŨNG KHÔNG Ở `HOA_NHAP` ═══
#:
#: Trước Đợt 5.2, `vm` rơi thẳng vào nhánh "bản mới đè hoàn toàn" — đúng lỗi
#: `CHANNEL` từng mắc trước 15/08/2026, chỉ nặng hơn: một lần cập nhật là mất
#: `vm/config.json`, `vm/cai-dat-tool.json`, `vm/trang-thai.json`, toàn bộ
#: token OAuth (`tokens/`), client bí mật (`clients/`), đã trả lời cmt nào
#: (`replied/`), và `vm/logs/so-video-id.json` — mất cái cuối là ĐĂNG TRÙNG
#: một video thật lên kênh thật. Và lần cập nhật SAU thì `.rollback` cũ bị
#: xoá luôn — mất vĩnh viễn, không hỏi lại.
HOA_GIU_TRANG_THAI = ("vm",)

#: Tên tệp TRẠNG THÁI MÁY THẬT trong `vm/`, khớp CHÍNH XÁC — không phân biệt
#: nằm ở độ sâu nào (`cau-hinh.json` chỉ xuất hiện trong `tien-ich/<kênh>/`,
#: tên khác không đụng hàng nên soi phẳng vẫn an toàn). Gom lại từ ba chỗ
#: từng liệt kê ĐỘC LẬP — `.gitignore` (khối "vm/"), `core/goi_vps.py`
#: (`_TEN_VM_CAM`), `core/chi_so_ytb/tram.py` (`_GOI_VM_BO_TEP`) — cộng thêm
#: vài tên soi được bằng cách đọc chính `vm/agent.py`, `vm/may_dang.py`,
#: `vm/may_cmt.py`, `vm/cdp.py` (`van-ipv4.json`, `dang-lam.json`,
#: `client_secret.json`) mà ba chỗ trên chưa liệt kê.
_VM_TEN_TRANG_THAI = frozenset({
    "config.json", "cai-dat-tool.json", "trang-thai.json", "_sheet_cache.json",
    "phien-ban.txt", "agent.pid", "agent.log", "van-ipv4.json", "dang-lam.json",
    "may-ao.json", "cau-hinh.json", "client_secret.json",
})
#: Thư mục CON mà TOÀN BỘ bên trong là trạng thái/bí mật máy thật — quyết một
#: lần ở tên thư mục, không cần soi tiếp bên trong.
_VM_THU_MUC_TRANG_THAI = frozenset({
    "tokens", "clients", "replied", "transcripts", "da-dang-cmt-moi",
    "logs", "goi-vps", "__pycache__", ".claude", ".vscode",
})
#: Khuôn tên (glob) cho nhật ký/kế hoạch/tệp tạm đặt tên theo kênh hoặc theo
#: lượt chạy — không liệt kê hết bằng tên chính xác được. Lấy nguyên từ
#: `.gitignore` (`vm/ke-hoach-*.csv`, `vm/*.truoc-*`, `vm/*.pid.*`) cộng mẫu
#: `core/goi_vps.py::_tep_goi_vm` đã dùng (`ke-hoach-`, `cho-bao-`, `.log`,
#: `.pid`).
_VM_KHUON_TRANG_THAI = (
    "ke-hoach-*.csv", "thu-muc-dang-*.json", "cho-bao-*", "*.truoc-*",
    "*.pid.*", "*.pid", "*.log", "*.tmp",
)
#: Khuôn tên trông giống bí mật — lớp chặn thứ hai, cùng nết với
#: `core/goi_vps.py::_MAU_BI_MAT`. Tên lạ chưa kịp liệt kê ở trên mà khớp mẫu
#: này (thêm một `*-rieng.json`, một `*.key` mới…) vẫn được coi là trạng thái.
_VM_MAU_BI_MAT = re.compile(
    r"secret|cookie|credential|(?:^|[-_.])token(?:[-_.]|$)|api[-_]?key|"
    r"-rieng\.json$|\.key$|\.pem$", re.IGNORECASE)


def _la_trang_thai_may(ten: str) -> bool:
    """`ten` (tên tệp/thư mục trần, không kèm đường dẫn) có phải trạng thái
    hay bí mật của MÁY ĐANG CHẠY trong `vm/` không.

    Ưu tiên AN TOÀN HƠN LÀ ĐỦ MÃ MỚI (chủ trương của `apply_tai_cho` từ
    15/08/2026): tên không chắc là mã hay trạng thái thì xử lý như trạng
    thái — thà chậm nhận một bản mã mới còn hơn đè mất đồ không lấy lại được.
    """
    if ten in _VM_TEN_TRANG_THAI or ten in _VM_THU_MUC_TRANG_THAI:
        return True
    if any(fnmatch.fnmatch(ten, khuon) for khuon in _VM_KHUON_TRANG_THAI):
        return True
    return bool(_VM_MAU_BI_MAT.search(ten))


def _hoa_vm(nguon: Path, dich: Path) -> None:
    """Hoà `vm/`: mã của bản mới thắng, trạng thái máy thật của khách giữ
    nguyên — kể cả trạng thái nằm SÂU trong thư mục con
    (`tien-ich/<kênh>/cau-hinh.json`), không chỉ ở cấp gốc `vm/`.

    `apply_tai_cho` gọi hàm này TRÊN BẢN GỐC `dich` (chưa có bản sao lưu nào
    — xem `da_hoa_vm` ở `apply_tai_cho`, nơi tự chụp một bản `vm/` cũ TRƯỚC
    khi gọi hàm này, để còn có gì mà lùi nếu healthcheck hỏng ngay sau đó).
    """
    dich.mkdir(parents=True, exist_ok=True)
    for muc in nguon.iterdir():
        ra = dich / muc.name
        if muc.name == "tien-ich" and muc.is_dir():
            _hoa_vm_tien_ich(muc, ra)
            continue
        if _la_trang_thai_may(muc.name):
            # `dich` chưa có mục này thì chép từ `nguon` vẫn an toàn — không
            # có gì để mất, và máy mới cần khung tối thiểu để chạy được.
            if not ra.exists():
                if muc.is_dir():
                    shutil.copytree(muc, ra)
                else:
                    shutil.copy2(muc, ra)
            continue
        if muc.is_dir():
            _chep_de(muc, ra)
        else:
            shutil.copy2(muc, ra)


def _hoa_vm_tien_ich(nguon: Path, dich: Path) -> None:
    """`vm/tien-ich/<mã-kênh>/`: mã dùng chung (`manifest.json`, `*.js`,
    `*.html`) của bản mới thắng, `cau-hinh.json` riêng từng kênh giữ nguyên.

    Tái dùng thẳng `_la_trang_thai_may` — không có luật riêng nào cho
    `tien-ich` ngoài "biết dừng lại đúng một cấp trước khi hoà từng tệp".
    """
    dich.mkdir(parents=True, exist_ok=True)
    for kenh in nguon.iterdir():
        ra_kenh = dich / kenh.name
        if not kenh.is_dir():
            # Phòng thủ: tệp lạ nằm thẳng trong tien-ich/ (không phải thư
            # mục của một kênh) — coi như mã dùng chung, bản mới thắng.
            shutil.copy2(kenh, ra_kenh)
            continue
        ra_kenh.mkdir(parents=True, exist_ok=True)
        for muc in kenh.iterdir():
            dich_muc = ra_kenh / muc.name
            if _la_trang_thai_may(muc.name):
                if not dich_muc.exists():
                    shutil.copy2(muc, dich_muc)
                continue
            shutil.copy2(muc, dich_muc)


def _kenh_rieng(thu_muc: Path) -> bool:
    """`kenh.yaml` trong `thu_muc` có `kenh_rieng: true` không (đọc thô, không
    cần PyYAML — chạy trong launcher cập nhật, càng ít phụ thuộc càng tốt)."""
    tep = thu_muc / "kenh.yaml"
    try:
        chu = tep.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    for dong in chu.splitlines():
        d = dong.strip()
        if d.startswith("kenh_rieng:"):
            return d.split(":", 1)[1].strip().strip("\"'").lower() in ("true", "yes", "1")
    return False


def _chep_de(nguon: Path, dich: Path) -> None:
    """Chép `nguon` lên `dich`: tệp của bản mới thắng, tệp thừa ở `dich` giữ nguyên."""
    dich.mkdir(parents=True, exist_ok=True)
    for muc in nguon.iterdir():
        ra = dich / muc.name
        if muc.is_dir():
            _chep_de(muc, ra)
        else:
            shutil.copy2(muc, ra)


def _hoa_channel(nguon: Path, dich: Path) -> None:
    """Hoà thư mục `CHANNEL`: kênh riêng của khách giữ, kênh mẫu của tool đè."""
    dich.mkdir(parents=True, exist_ok=True)
    for muc in nguon.iterdir():
        ra = dich / muc.name
        if muc.is_dir() and ra.is_dir() and _kenh_rieng(ra):
            _chep_thieu(muc, ra)
        elif muc.is_dir():
            _chep_de(muc, ra)
        else:
            shutil.copy2(muc, ra)

MAX_FILES = 5000
MAX_UNCOMPRESSED = 2 * 1024 * 1024 * 1024


class UpdateError(RuntimeError):
    pass


def stage_update(archive: bytes, manifest: Mapping[str, Any], staging_root: Union[str, Path]) -> Path:
    if len(archive) != manifest["size"]:
        raise UpdateError("Kích thước ZIP không khớp manifest")
    if hashlib.sha256(archive).hexdigest() != manifest["sha256"]:
        raise UpdateError("SHA-256 của ZIP không khớp manifest")
    root = Path(staging_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / _safe_version(str(manifest["version"]))
    temp = Path(tempfile.mkdtemp(prefix="update-", dir=str(root)))
    try:
        archive_path = temp / "release.zip"
        archive_path.write_bytes(archive)
        payload = temp / "payload"
        payload.mkdir()
        _safe_extract(archive_path, payload)
        app_root = _single_root(payload)
        _healthcheck_tree(app_root)
        (app_root / "update-manifest.json").write_text(
            json.dumps(dict(manifest), ensure_ascii=False, indent=2) + "\n", "utf-8")
        if target.exists():
            shutil.rmtree(target)
        os.replace(str(app_root), str(target))
        return target
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _chep_thieu(nguon: Path, dich: Path) -> None:
    """Chép từ `nguon` sang `dich` những gì `dich` **chưa có**. Không đè gì cả.

    Đi vào tận từng tệp chứ không dừng ở cấp thư mục: khách có thư mục
    `CHANNEL/TL1-T1` rồi, nhưng bản mới có thêm `prompt/9-nhac.md` trong đó —
    dừng ở cấp thư mục là tệp mới ấy không bao giờ tới được máy khách.

    Không đè: một tệp khách đã sửa thì bản mới không có quyền ghi lên. Kể cả
    khi bản mới viết hay hơn — đó là lựa chọn của khách, không phải của tool.
    """
    dich.mkdir(parents=True, exist_ok=True)
    for muc in nguon.iterdir():
        ra = dich / muc.name
        if muc.is_dir():
            _chep_thieu(muc, ra)
        elif not ra.exists():
            shutil.copy2(muc, ra)


def _doi_ten_kien_tri(nguon: Path, dich: Path, so_lan: int = 12) -> None:
    """Đổi tên thư mục, thử lại vài lần khi Windows đang khoá.

    Trên Windows, đổi tên một thư mục thất bại (`WinError 32`) khi có bất cứ
    thứ gì đang giữ nó: phần mềm diệt virus vừa quét xong nhưng chưa nhả, một
    cửa sổ Explorer đang mở đúng thư mục ấy, hoặc dịch vụ đánh chỉ mục của
    Windows. Phần lớn những cái đó nhả ra sau một hai giây.

    Đây **không** phải chỗ chữa cho lỗi thư mục làm việc — cái đó không bao giờ
    tự nhả, và đã được chặn ở `cap-nhat.py` bằng `os.chdir` ra ngoài. Chỗ này
    chỉ lo mấy khoá tạm thời.
    """
    for lan in range(so_lan):
        try:
            os.replace(str(nguon), str(dich))
            return
        except OSError:
            if lan == so_lan - 1:
                raise
            time.sleep(0.5)


def apply_tai_cho(staged: Union[str, Path], current: Union[str, Path], *,
                  healthcheck: Optional[Callable[[Path], None]] = None) -> Path:
    """Thay **ruột** thư mục cài, giữ nguyên chính thư mục ấy.

    ═══ VÌ SAO KHÔNG ĐỔI TÊN THƯ MỤC NỮA ═══

    Bản trước tráo bằng cách đổi tên: `cài` → `cài.rollback`, rồi `bản mới` →
    `cài`. Nghe gọn, nhưng trên Windows nó hỏng vì một luật rất cứng: **không
    đổi tên được thư mục nào có tiến trình đang đứng bên trong**. Mà tiến trình
    đi tráo lại được tool khởi chạy, nên nó thừa hưởng đúng thư mục cài làm thư
    mục làm việc — tự chặn mình ngay bước đầu, lần nào cũng vậy.

    Chữa bằng `os.chdir` ra ngoài thì được, nhưng đó là bịt một lỗ trên một
    thiết kế còn nhiều lỗ khác cùng loại: một cửa sổ Explorer đang mở thư mục
    ấy, phần mềm diệt virus vừa quét, dịch vụ đánh chỉ mục của Windows — mỗi
    thứ đều đủ để chặn một lần đổi tên, và khách thì không hiểu vì sao "cập
    nhật lúc được lúc không".

    Chủ dự án, 15/08/2026: *"giải quyết từ gốc rễ… thư mục gốc đúng tên luôn vì
    tao làm việc thì thường cập nhật vào luôn thư mục gốc"*.

    Nên: **không đụng vào thư mục cài**. Chỉ dọn ruột nó ra chỗ lùi rồi chép
    ruột mới vào. Thư mục giữ nguyên đường dẫn, nên lối tắt ngoài màn hình,
    `.claude/` và mọi thứ trỏ tới nó đều còn nguyên.

    Đổi lại: không còn "tráo một nhát" nữa, giữa chừng hỏng là thư mục ở trạng
    thái nửa vời. Nên có chỗ lùi: mọi thứ dọn ra đều nằm ở `<tên>.rollback`, và
    hỏng thì chép ngược lại trước khi ném lỗi.
    """
    staged_path, current_path = Path(staged).resolve(), Path(current).resolve()
    if not staged_path.is_dir() or not current_path.is_dir():
        raise UpdateError("Thiếu thư mục bản mới hoặc bản hiện tại")
    if current_path in staged_path.parents or staged_path == current_path:
        raise UpdateError("Bản mới không được nằm bên trong thư mục đang cập nhật")
    # Soi bản mới TRƯỚC khi động vào bản đang chạy. Dọn ruột ra rồi mới phát
    # hiện bản mới thiếu tệp là lúc đã không còn gì để chạy.
    (healthcheck or _healthcheck_tree)(staged_path)

    lui = current_path.with_name(current_path.name + ".rollback")
    if lui.exists():
        shutil.rmtree(lui, ignore_errors=True)
    lui.mkdir(parents=True, exist_ok=True)

    da_don: List[str] = []
    #: `vm/` (và mọi thứ khác trong `HOA_GIU_TRANG_THAI`) không đi qua vòng
    #: "dời-sang-rollback" bên dưới — nó hoà TẠI CHỖ. Nên tự chụp một bản sao
    #: riêng NGAY TRƯỚC khi hoà (xem vòng 2), để nhánh lỗi còn có gì mà trả
    #: lại nếu healthcheck hỏng ngay sau bước hoà đó.
    da_hoa_vm: List[Tuple[str, Path]] = []
    try:
        # ═══ CHỈ ĐỘNG VÀO THỨ BẢN MỚI CÓ MANG THEO ═══
        #
        # `PRESERVE` là một danh sách **phải nhớ**, và người ta thì quên. Nó đã
        # quên `CHANNEL` một lần, và cái giá là lời nhắc khách sửa cùng mọi kênh
        # họ tự tạo bị xoá sạch ở mỗi lần cập nhật — im lặng, không thùng rác.
        # Ghi chú ở đầu `PRESERVE` cũng kể đúng chuyện ấy đã xảy ra ba lần với
        # ba thư mục khác nhau.
        #
        # Chủ dự án, 15/08/2026: *"channel và các prompt… về sau khách sẽ có
        # nhiều, không nên làm mất của họ"*.
        #
        # Nên thêm một luật **không cần ai nhớ**: thứ gì bản mới không mang
        # theo thì tool không có quyền đụng vào. Thư mục lạ trong chỗ cài chỉ
        # có thể do khách tạo ra, và tool không biết nó là gì thì càng không
        # nên xoá nó.
        #
        # Đổi lại: tệp bị **bỏ đi** giữa hai bản sẽ nằm lại. Chấp nhận được —
        # một tệp thừa không hại ai, còn xoá nhầm đồ khách thì không lấy lại
        # được.
        ten_ban_moi = {m.name for m in staged_path.iterdir()}
        for muc in list(current_path.iterdir()):
            if muc.name in PRESERVE or muc.name in HOA_NHAP or muc.name in HOA_GIU_TRANG_THAI:
                continue
            if muc.name == lui.name or muc.name not in ten_ban_moi:
                continue
            _doi_ten_kien_tri(muc, lui / muc.name)
            da_don.append(muc.name)

        # 2. Chép ruột mới vào.
        for muc in list(staged_path.iterdir()):
            dich = current_path / muc.name
            if muc.name in PRESERVE and dich.exists():
                continue
            if muc.name == "CHANNEL" and dich.exists():
                # Kênh riêng của khách giữ nguyên; kênh mẫu của tool cập nhật.
                _hoa_channel(muc, dich)
                continue
            if muc.name in HOA_NHAP and dich.exists():
                # Hoà: chỉ thêm thứ còn thiếu, không đụng thứ khách đã có.
                _chep_thieu(muc, dich)
                continue
            if muc.name in HOA_GIU_TRANG_THAI and dich.exists():
                # Mã vm/ thắng, trạng thái máy thật giữ nguyên (xem
                # `HOA_GIU_TRANG_THAI`, `_hoa_vm`). Chụp một bản sao lưu
                # TRƯỚC khi hoà — merge tại chỗ ghi đè thẳng mã cũ
                # (agent.py, may_dang.py…), nên vẫn cần một chỗ lùi riêng
                # phòng healthcheck hỏng ngay sau bước này.
                luu_vm = lui / (muc.name + ".sao-luu")
                shutil.copytree(dich, luu_vm)
                da_hoa_vm.append((muc.name, luu_vm))
                _hoa_vm(muc, dich)
                continue
            if muc.is_dir():
                shutil.copytree(muc, dich, dirs_exist_ok=True)
            else:
                shutil.copy2(muc, dich)

        (healthcheck or _healthcheck_tree)(current_path)
    except Exception as loi:
        # 3. Hỏng thì trả lại nguyên trạng: bỏ thứ vừa chép, chép ngược đồ cũ.
        for ten in da_don:
            dich = current_path / ten
            if dich.exists():
                if dich.is_dir():
                    shutil.rmtree(dich, ignore_errors=True)
                else:
                    dich.unlink(missing_ok=True)
            nguon = lui / ten
            if nguon.exists():
                _doi_ten_kien_tri(nguon, dich)
        for ten, luu_vm in da_hoa_vm:
            dich = current_path / ten
            if dich.exists():
                shutil.rmtree(dich, ignore_errors=True)
            _doi_ten_kien_tri(luu_vm, dich)
        raise UpdateError("Cập nhật lỗi; đã trả lại bản cũ") from loi
    return lui


def apply_staged(staged: Union[str, Path], current: Union[str, Path], *,
                 healthcheck: Optional[Callable[[Path], None]] = None) -> Path:
    """Atomic swap. Chi goi tu launcher sau khi Studio da thoat."""
    staged_path, current_path = Path(staged).resolve(), Path(current).resolve()
    if not staged_path.is_dir() or not current_path.is_dir():
        raise UpdateError("Thiếu thư mục staged hoặc bản hiện tại")
    if staged_path.parent == current_path or current_path in staged_path.parents:
        raise UpdateError("Staging không được nằm bên trong thư mục đang cập nhật")
    backup = current_path.with_name(current_path.name + ".rollback")
    if backup.exists():
        shutil.rmtree(backup)
    for name in PRESERVE:
        source = current_path / name
        destination = staged_path / name
        if not source.exists():
            continue
        if destination.exists():
            if destination.is_dir(): shutil.rmtree(destination)
            else: destination.unlink()
        if source.is_dir(): shutil.copytree(source, destination)
        else: shutil.copy2(source, destination)
    _doi_ten_kien_tri(current_path, backup)
    try:
        _doi_ten_kien_tri(staged_path, current_path)
        (healthcheck or _healthcheck_tree)(current_path)
    except Exception as exc:
        if current_path.exists():
            failed = current_path.with_name(current_path.name + ".failed-update")
            if failed.exists(): shutil.rmtree(failed)
            os.replace(str(current_path), str(failed))
        os.replace(str(backup), str(current_path))
        raise UpdateError("Cập nhật lỗi; đã khôi phục bản cũ") from exc
    return backup


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        infos = handle.infolist()
        if not infos or len(infos) > MAX_FILES:
            raise UpdateError("ZIP cập nhật rỗng hoặc có quá nhiều file")
        total = 0
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise UpdateError("ZIP chứa đường dẫn không an toàn")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UpdateError("ZIP không được chứa symbolic link")
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise UpdateError("ZIP giải nén vượt giới hạn")
        handle.extractall(destination)


def _single_root(payload: Path) -> Path:
    roots = [item for item in payload.iterdir() if item.name != "__MACOSX"]
    if len(roots) != 1 or not roots[0].is_dir():
        raise UpdateError("ZIP phải chứa đúng một thư mục gốc")
    return roots[0]


def _healthcheck_tree(root: Path) -> None:
    required = ("shopapi_studio_qt.py", "core", "ui_qt", "tool-catalog")
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise UpdateError("Bản staged thiếu: " + ", ".join(missing))
    manifests = list((root / "tool-catalog").glob("*/tool.json"))
    if not manifests:
        raise UpdateError("Bản staged không có tool manifest")


def _safe_version(value: str) -> str:
    clean = "".join(char for char in value if char.isalnum() or char in ".-_").strip(".-")
    if not clean or len(clean) > 80:
        raise UpdateError("Version không hợp lệ")
    return clean
