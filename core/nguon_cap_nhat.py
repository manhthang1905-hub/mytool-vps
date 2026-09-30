"""Cập nhật qua MANIFEST + `raw.githubusercontent.com` — ĐÃ NGỪNG (30/09/2026).

Hệ cập nhật duy nhất giờ là `core/cap_nhat_git.py` (git + kho chung
`cap-nhat.json: kho`). Không giao diện/lịch nào gọi `ap_dung` nữa; máy có
`.git` thì `ap_dung` luôn nhường (`core.dong_bo_git.dang_quan_ly`). Giữ lại
module cho bản cài cũ không có Git và cho test — phần dưới là thiết kế cũ.

(Thiết kế cũ) dùng được trên máy
CHỈ CÓ IPv6 (VPS, `vm/VPS-CLAUDE.md` mục "Mạng chỉ có IPv6").

═══ VÌ SAO KHÔNG DÙNG ZIP NHƯ `core/cap_nhat_github.py` ═══

Đường cũ tải `github.com/<kho>/archive/refs/heads/<nhánh>.zip` — domain đó
(và `codeload.github.com`) đo được ngày 18/09/2026 là **IPv4-only**, không
với tới được từ một VPS chỉ có IPv6. `raw.githubusercontent.com` thì dùng
được (đã dùng để đọc `VERSION`). Nên đường ở đây đọc một **manifest** kê
từng tệp kèm SHA-256 qua `raw`, rồi tải TỪNG TỆP cũng qua `raw` — không một
request nào chạm `github.com`.

Đổi lại: không còn một cú tải ZIP một phát, mà là N lượt tải nhỏ. Với một bản
tool cỡ vài nghìn tệp, đây là đánh đổi hợp lý trên máy vốn chỉ có IPv6 hẹp.

═══ AI DÙNG MODULE NÀY ═══

`core/cap_nhat_github.py` (ZIP qua `github.com`) vẫn đứng nguyên, phục vụ nút
bấm tay trên máy NHÀ (có IPv4, một cú ZIP là xong, không cần đổi). Module này
phục vụ đường TỰ ĐỘNG trên VPS — nơi phải qua manifest.

═══ NGUỒN CẤU HÌNH: `cap-nhat.json`, KHÔNG PHẢI HẰNG SỐ TRONG MÃ ═══

Một kho GitHub gắn cứng trong mã (`core.cap_nhat_github.KHO`) có nghĩa là ĐỔI
KHO là phải phát hành một bản tool mới — con gà và quả trứng khi kho cũ
(`shopapivn/youtube`) không còn dùng nữa mà kho mới thì chưa có URL. Nên từ
Đợt 5.2 (29/09/2026), kho/nhánh/kênh phát hành/chính sách tự áp đều đọc từ
`cap-nhat.json` ở gốc tool — một tệp CẤU HÌNH RIÊNG MÁY, không lên kho
(`.gitignore`). Máy chưa có tệp này, hay `kho` để trống, coi như CHƯA CẤU
HÌNH — không cập nhật gì, không lỗi. Đây là mặc định AN TOÀN cố ý: một máy
không biết cập nhật từ đâu thì không được tự đoán.

Module này **không tự gọi mạng** — theo đúng khuôn `core/cap_nhat_github.py`:
mọi lối ra ngoài đi qua tham số `tai: Callable[[str], bytes]`, nên test chạy
được không cần mạng.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Union

from . import cap_nhat_github, che_do_vps
from .safe_update import UpdateError, _healthcheck_tree, apply_tai_cho

__all__ = [
    "doc_cau_hinh", "url_manifest", "url_tep", "kiem_ban_moi",
    "tai_va_dung_san", "giu_toi_da_2_ban_rollback", "ap_dung",
    "duoc_phep_hien_nut",
]

#: Mặc định khi `cap-nhat.json` không khai (nhánh chính, kênh ổn định).
_NHANH_MAC_DINH = "main"
_KENH_MAC_DINH = "on-dinh"
_CAC_KENH_HOP_LE = ("on-dinh", "thu")
_CAC_CHINH_SACH_HOP_LE = ("hoi", "khung_an_toan", "tat")


def doc_cau_hinh(goc: str) -> Dict[str, Any]:
    """Đọc `cap-nhat.json` ở gốc tool. Tệp thiếu, hỏng, hay không phải JSON
    object đều KHÔNG ném lỗi — trả về cấu hình mặc định AN TOÀN (`kho=""`,
    tức không cập nhật gì).

    `chinh_sach` thiếu khoá (nhưng CÓ `kho`) thì suy theo loại máy: VPS
    (`core.che_do_vps.la_vps`) mặc định `"khung_an_toan"` — được tự áp,
    nhưng luôn gác bằng `core.an_toan_khoi_dong` trước khi động tay; máy nhà
    mặc định `"hoi"` — chỉ báo có bản mới, khách tự bấm. Khoá ĐÃ có trong tệp
    thì tôn trọng nguyên văn, kể cả khi lạ (rơi về `"hoi"` — thà hỏi nhầm còn
    hơn tự áp nhầm).
    """
    duong = os.path.join(goc, "cap-nhat.json")
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        du = {}
    if not isinstance(du, dict):
        du = {}

    kho = str(du.get("kho") or "").strip()
    nhanh = str(du.get("nhanh") or "").strip() or _NHANH_MAC_DINH
    kenh = str(du.get("kenh") or "").strip() or _KENH_MAC_DINH
    if kenh not in _CAC_KENH_HOP_LE:
        kenh = _KENH_MAC_DINH

    chinh_sach = str(du.get("chinh_sach") or "").strip()
    if chinh_sach not in _CAC_CHINH_SACH_HOP_LE:
        if "chinh_sach" in du:
            # Khoá có mặt nhưng giá trị lạ — an toàn hơn là đoán quyền tự áp.
            chinh_sach = "hoi"
        else:
            try:
                la_vps = che_do_vps.la_vps(goc)
            except Exception:  # noqa: BLE001 — đọc hỏng thì lùi về mặc định máy nhà
                la_vps = False
            chinh_sach = "khung_an_toan" if la_vps else "hoi"

    return {"kho": kho, "nhanh": nhanh, "kenh": kenh, "chinh_sach": chinh_sach}


def duoc_phep_hien_nut(goc: str) -> bool:
    """Có nên cho khách THẤY nút cập nhật không — KHÔNG phải "có tự áp
    không" (quyết định đó ở `chinh_sach`, tại tầng `ap_dung`). Chưa cấu hình
    `kho`, hay `chinh_sach` là `"tat"`, đều trả `False` — đúng tinh thần an
    toàn ban đầu: máy chưa được chủ dự án cấu hình thì không tự bật gì cả.
    """
    try:
        cfg = doc_cau_hinh(goc)
    except Exception:  # noqa: BLE001 — đọc cấu hình hỏng thì coi như tắt
        return False
    return bool(cfg.get("kho")) and cfg.get("chinh_sach") != "tat"


def url_manifest(cfg: Dict[str, Any]) -> str:
    return "https://raw.githubusercontent.com/{0}/{1}/phat-hanh/{2}/manifest.json".format(
        cfg["kho"], cfg.get("nhanh") or _NHANH_MAC_DINH, cfg.get("kenh") or _KENH_MAC_DINH)


def url_tep(cfg: Dict[str, Any], duong_tuong_doi: str) -> str:
    return "https://raw.githubusercontent.com/{0}/{1}/{2}".format(
        cfg["kho"], cfg.get("nhanh") or _NHANH_MAC_DINH, duong_tuong_doi)


def _duong_an_toan(duong: str) -> bool:
    """`duong` (một `path` trong manifest) có an toàn để ghi ra đĩa không —
    cùng luật chặn path traversal với `safe_update._safe_extract` (không
    tuyệt đối, không `..`)."""
    if not duong or duong.startswith(("/", "\\")):
        return False
    phan = PurePosixPath(duong)
    return not (phan.is_absolute() or ".." in phan.parts or not phan.parts)


def kiem_ban_moi(cfg: Dict[str, Any], dang_dung: str,
                 tai: Callable[[str], bytes]) -> Optional[Dict[str, Any]]:
    """Đọc manifest qua `tai`, trả `None` nếu không có bản MỚI HƠN `dang_dung`.

    Chưa cấu hình `kho`, mất mạng, hay manifest sai định dạng/thiếu
    khoá/đường dẫn không an toàn đều lặng lẽ trả `None` — cùng triết lý với
    `cap_nhat_github.kiem_ban_moi`: đây là việc chạy ngầm, không được làm
    tool hỏng vì một manifest bẩn. **Không hạ bản**: manifest cũ hơn hay
    bằng `dang_dung` cũng trả `None` (`cap_nhat_github.moi_hon` so bằng số).
    """
    if not cfg.get("kho"):
        return None
    try:
        du = json.loads(tai(url_manifest(cfg)).decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — mất mạng/manifest hỏng là chuyện thường
        return None
    if not isinstance(du, dict):
        return None
    phien_ban = str(du.get("version") or "").strip()
    danh_sach = du.get("files")
    if not phien_ban or not isinstance(danh_sach, list) or not danh_sach:
        return None

    sach: List[Dict[str, Any]] = []
    for muc in danh_sach:
        if not isinstance(muc, dict):
            return None
        duong = str(muc.get("path") or "")
        sha = str(muc.get("sha256") or "")
        if not duong or not sha or not _duong_an_toan(duong):
            return None
        sach.append({"path": duong, "sha256": sha, "size": muc.get("size")})

    if not cap_nhat_github.moi_hon(phien_ban, dang_dung):
        return None
    return {"version": phien_ban, "files": sach}


def _ten_an_toan(chu: str) -> str:
    sach = "".join(c for c in chu if c.isalnum() or c in ".-_").strip(".-")
    if not sach or len(sach) > 80:
        raise UpdateError("Version trong manifest không hợp lệ: " + repr(chu))
    return sach


def tai_va_dung_san(cfg: Dict[str, Any], manifest: Dict[str, Any],
                    thu_muc_dung: Union[str, Path],
                    tai: Callable[[str], bytes]) -> Path:
    """Tải TỪNG tệp trong `manifest` qua `tai`, đối chiếu SHA-256 từng tệp,
    dựng thành một cây thư mục hoàn chỉnh dưới `thu_muc_dung/<version>/`.

    Một tệp sai SHA-256 (hay tải hỏng giữa chừng) là TỪ CHỐI TOÀN BỘ — không
    ghi một tệp nào vào `thu_muc_dung`, ném `UpdateError`. Chấp nhận một phần
    là để lại một bản cài dở dang không ai biết là dở dang.

    Soi `_healthcheck_tree` (tái dùng nguyên hàm của `safe_update`) TRƯỚC khi
    coi là dựng xong — một manifest thiếu tệp vẫn phải bị chặn ở đây, không
    để `apply_tai_cho` phát hiện muộn hơn.
    """
    danh_sach = manifest.get("files")
    if not isinstance(danh_sach, list) or not danh_sach:
        raise UpdateError("Manifest không có danh sách tệp hợp lệ")

    root = Path(thu_muc_dung).resolve()
    root.mkdir(parents=True, exist_ok=True)
    phien_ban = _ten_an_toan(str(manifest.get("version") or ""))
    target = root / phien_ban
    temp = Path(tempfile.mkdtemp(prefix="update-src-", dir=str(root)))
    try:
        payload = temp / "payload"
        payload.mkdir()
        for muc in danh_sach:
            duong = str(muc.get("path") or "")
            sha = str(muc.get("sha256") or "")
            if not duong or not sha or not _duong_an_toan(duong):
                raise UpdateError("Manifest chứa mục không an toàn: " + repr(muc))
            noi_dung = tai(url_tep(cfg, duong))
            if hashlib.sha256(noi_dung).hexdigest() != sha:
                raise UpdateError("SHA-256 không khớp cho tệp: " + duong)
            dich = payload.joinpath(*duong.split("/"))
            dich.parent.mkdir(parents=True, exist_ok=True)
            dich.write_bytes(noi_dung)

        _healthcheck_tree(payload)
        if target.exists():
            shutil.rmtree(target)
        os.replace(str(payload), str(target))
        return target
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def _duong_rollback_hien_tai(current: Path) -> Path:
    return current.with_name(current.name + ".rollback")


def giu_toi_da_2_ban_rollback(current: Union[str, Path], version_cu: str) -> None:
    """Gọi TRƯỚC `apply_tai_cho`: `apply_tai_cho` tự `rmtree` sạch
    `<current>.rollback` mỗi lần được gọi (chỗ lùi TỨC THỜI trong CHÍNH lượt
    cập nhật này) — nên nếu còn bản lùi từ LƯỢT TRƯỚC nằm đó, phải đặt tên nó
    theo phiên bản cũ rồi nhường chỗ, không thì mất luôn bản lùi duy nhất.

    Giữ tối đa 2 bản `<current>.rollback-<version>` gần nhất (theo thời gian
    sửa đổi); bản cũ hơn bị xoá. Không tệp/tên nào khác bị đụng vào.

    `version_cu` chỉ là DỰ PHÒNG: `<current>.rollback` đang có (nếu có) là
    thư mục `apply_tai_cho` của LƯỢT CẬP NHẬT TRƯỚC để lại, tự nó đã mang
    theo `VERSION` của phiên bản bị dời ra lúc đó — đúng version cần cho cái
    tên, và đáng tin hơn `version_cu` (đọc từ `VERSION` của `current` NGAY
    LÚC GỌI hàm này, tức là version ĐANG CHẠY — chênh một lượt cập nhật so
    với thứ nằm trong `.rollback`). Chỉ dùng `version_cu` khi không đọc được
    `VERSION` bên trong `.rollback` (tự dựng tay, hay bản rất cũ).
    """
    current = Path(current)
    lui = _duong_rollback_hien_tai(current)
    if lui.is_dir():
        ten_that = _doc_version(str(lui))
        nguon_ten = ten_that if ten_that and ten_that != "?" else version_cu
        ten_cu = _ten_an_toan(nguon_ten) if nguon_ten and nguon_ten != "?" \
            else time.strftime("%Y%m%d-%H%M%S")
        dich = current.with_name("{0}.rollback-{1}".format(current.name, ten_cu))
        if dich.exists():
            shutil.rmtree(dich, ignore_errors=True)
        shutil.move(str(lui), str(dich))

    cha = current.parent
    if not cha.is_dir():
        return
    tien_to = current.name + ".rollback-"
    ban_cu = sorted(
        (p for p in cha.iterdir() if p.is_dir() and p.name.startswith(tien_to)),
        key=lambda p: p.stat().st_mtime, reverse=True)
    for thua in ban_cu[2:]:
        shutil.rmtree(thua, ignore_errors=True)


def _doc_version(goc: str) -> str:
    try:
        with open(os.path.join(goc, "VERSION"), encoding="utf-8-sig") as tep:
            return tep.read().strip()
    except OSError:
        return "?"


#: Ba module chính soi được ngay là tool "còn sống" sau cập nhật: cửa sổ Qt
#: chính, bộ điều phối job, và trạm HTTP 8765 (`vm/VPS-CLAUDE.md`: "bật trạm
#: … qua core/giam_sat_vm.py", trạm thật nằm ở `core.chi_so_ytb.tram.Tram`).
_MODULE_HEALTHCHECK: tuple = ("shopapi_studio_qt", "core.jobs", "core.chi_so_ytb.tram")


def _healthcheck_module_that(goc: str, *, cho_giay: float = 30.0) -> None:
    """Nạp thử `_MODULE_HEALTHCHECK` trong một TIẾN TRÌNH CON riêng, đứng
    đúng tại `goc` — không nạp trong tiến trình đang chạy: nó đã có sẵn
    `sys.modules` từ trước lúc mở lên, một `import` lại không đọc file mới
    từ đĩa, nên không phát hiện được mã vừa cập nhật có nạp nổi hay không.

    Hỏng (import lỗi, hay tiến trình con thoát khác 0) ném `UpdateError` —
    `ap_dung` tự khôi phục bản cũ khi thấy lỗi này.
    """
    lenh = "; ".join("import " + m for m in _MODULE_HEALTHCHECK)
    moi_truong = dict(os.environ)
    moi_truong.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        ket = subprocess.run(
            [sys.executable, "-c", lenh], cwd=goc, env=moi_truong,
            capture_output=True, timeout=cho_giay,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as loi:
        raise UpdateError(
            "Không chạy được healthcheck sau cập nhật: {0}".format(loi)) from loi
    if ket.returncode != 0:
        raise UpdateError(
            "Nạp module chính sau cập nhật thất bại (mã {0}):\n{1}".format(
                ket.returncode, ket.stderr.decode("utf-8", "replace")[-2000:]))


def _khoi_phuc_tu_rollback(current: Path, lui: Path) -> None:
    """Chép ngược `<current>.rollback` (đúng thư mục `apply_tai_cho` vừa trả
    về) đè lại vào `current`. Dùng khi healthcheck SAU khi áp (import module
    thật, `_healthcheck_module_that`) phát hiện hỏng mà bản thân
    `apply_tai_cho` không tự biết — nó chỉ soi cây tệp (`_healthcheck_tree`),
    không import thật, nên "module có nạp được không" chỉ lộ ra ở đây.

    Chỉ khôi phục đúng những gì `lui` MANG THEO: tên thường (mã đã bị dời ra
    lúc cập nhật) chép thẳng đè lại; tên có hậu tố `.sao-luu` (snapshot
    `vm/` — xem `safe_update._hoa_vm`) chép đè lại đúng tên gốc, bỏ hậu tố.
    Không đụng gì khác — `PRESERVE`/`CHANNEL`/`HOA_NHAP` chưa từng bị
    `apply_tai_cho` dời ra nên không cần, và cũng không có gì để khôi phục.
    """
    if not lui.is_dir():
        raise UpdateError("Không tìm thấy .rollback để khôi phục: " + str(lui))
    HAU_TO = ".sao-luu"
    for muc in lui.iterdir():
        ten = muc.name[: -len(HAU_TO)] if muc.name.endswith(HAU_TO) else muc.name
        dich = current / ten
        if dich.exists():
            if dich.is_dir():
                shutil.rmtree(dich, ignore_errors=True)
            else:
                dich.unlink(missing_ok=True)
        if muc.is_dir():
            shutil.copytree(muc, dich)
        else:
            shutil.copy2(muc, dich)


def ap_dung(goc: str, cfg: Dict[str, Any], manifest: Dict[str, Any],
           thu_muc_staged: Union[str, Path], *,
           viec_chay_tay: bool = False,
           healthcheck: Optional[Callable[[Path], None]] = None,
           healthcheck_sau: Optional[Callable[[str], None]] = None,
           tai: Optional[Callable[[str], bytes]] = None) -> Dict[str, Any]:
    """Điều phối MỘT lượt cập nhật đã tải sẵn (`thu_muc_staged`, kết quả của
    `tai_va_dung_san`) vào `goc`. `tai` không được dùng ở đây (mọi việc tải
    xong ở `tai_va_dung_san`) — nhận cho khớp chữ ký, phòng khi cần tải thêm
    (vd log sự cố) ở bản sau; không truyền cũng chạy được.

    Trả `{"da_ap_dung": bool, "ly_do": str, ...}`. **Không ném lỗi** khi
    chính sách/an toàn từ chối áp — đó là đường đi bình thường, không phải sự
    cố. Chỉ ném `UpdateError` khi ĐÃ bắt đầu áp mà hỏng giữa chừng (và lúc đó
    đã tự khôi phục xong trước khi ném).
    """
    # Máy cài từ git clone: mã CHỈ cập nhật qua `core.cap_nhat_git` /
    # `core.dong_bo_git.keo` (ff-only + tag lùi). Hai hệ cùng tráo tệp là
    # cây git bẩn và `keo` sẽ từ chối mãi — đường manifest nhường (30/09/2026).
    try:
        from . import dong_bo_git  # noqa: PLC0415
        if dong_bo_git.dang_quan_ly(goc):
            return {"da_ap_dung": False, "ly_do": "may cap nhat qua git (core.dong_bo_git)"}
    except Exception:  # noqa: BLE001 — đọc hỏng thì giữ nguyên hành vi cũ
        pass
    chinh_sach = cfg.get("chinh_sach") or "hoi"
    if chinh_sach == "tat":
        return {"da_ap_dung": False, "ly_do": "chinh_sach=tat"}
    if chinh_sach == "hoi":
        return {"da_ap_dung": False, "ly_do": "chinh_sach=hoi (chi bao, khong tu ap)"}
    if chinh_sach != "khung_an_toan":
        return {"da_ap_dung": False, "ly_do": "chinh_sach khong hop le: " + str(chinh_sach)}

    from . import an_toan_khoi_dong  # noqa: PLC0415 — tránh vòng import lúc nạp module

    kt = an_toan_khoi_dong.kiem_tra(goc, viec_chay_tay=viec_chay_tay)
    if not kt.get("duoc"):
        return {"da_ap_dung": False, "ly_do": "chua_an_toan", "chi_tiet": kt.get("ly_do")}

    version_cu = _doc_version(goc)
    current = Path(goc).resolve()
    giu_toi_da_2_ban_rollback(current, version_cu)

    lui = apply_tai_cho(thu_muc_staged, current, healthcheck=healthcheck)
    try:
        (healthcheck_sau or _healthcheck_module_that)(str(current))
    except Exception as loi:
        _khoi_phuc_tu_rollback(current, lui)
        raise UpdateError(
            "Cập nhật lỗi ở bước healthcheck sau khi áp; đã khôi phục bản cũ") from loi

    return {"da_ap_dung": True, "phien_ban": manifest.get("version"),
            "phien_ban_cu": version_cu, "rollback": str(lui)}
