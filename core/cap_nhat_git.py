# -*- coding: utf-8 -*-
"""core/cap_nhat_git.py — HỆ CẬP NHẬT DUY NHẤT của ShopAPI Studio (30/09/2026).

Chủ dự án, 30/09/2026: *"khi có update mới tool tự nâng version, trên giao diện
tool cũng nhìn được ở setting; mặc định là bật update, còn VPS nào ổn định tao
sẽ tự tắt — tức là có logic cập nhật, có nút ấn cập nhật…"*

═══ MỘT HỆ, DỰA TRÊN GIT + KHO CHUNG ═══

Kho chung `cap-nhat.json: kho` (mặc định `manhthang1905-hub/mytool-vps`), nhánh
`main`. Mọi máy cài bằng `git clone` (CAI-DAT-VPS.bat). Đường ZIP
(`core/cap_nhat_github.py` + `cap-nhat.py`) và manifest (`core/nguon_cap_nhat.py`)
KHÔNG còn nơi nào gọi để áp mã — chỉ còn là thư viện cũ/so số hiệu.

    ĐẨY   (máy phát triển)  python -m core.dong_bo_git day "<msg>" [--minor|--major] [--chi tệp…]
          → commit → rebase lên origin → TỰ NÂNG VERSION (+patch mặc định) → 1 dòng
            CHANGELOG.md → tag v<version> → push. Hai máy cùng đẩy: bị từ chối thì
            bỏ commit phiên bản, rebase lại, tăng lại số — không bao giờ trùng.
    KIỂM  (mọi máy)        `nhip()` mỗi ~30 phút (gác tổng 15' + giao diện) và khi mở
            giao diện: `git fetch` rồi đọc `origin/main:VERSION` + CHANGELOG. Ghi
            `workspace/cap-nhat/trang-thai.json`.
    ÁP    (mặc định BẬT)   có bản mới + `tu_dong_cap_nhat` (hoặc người bấm "Cập nhật
            ngay") + máy rảnh → sinh tiến trình tách rời `python -m core.dong_bo_git
            keo` (worktree tạm, py_compile, kiểm khói, khung :15–:45, khe nặng, tag
            `truoc-cap-nhat-<ts>`, `merge --ff-only`, khởi động lại giao diện + vm,
            theo dõi; chết lặp thì tự lùi và BỎ QUA bản đó).

═══ BẬT/TẮT: `cap-nhat.json` (riêng máy, không lên kho) ═══

    {"kho": "manhthang1905-hub/mytool-vps", "nhanh": "main",
     "tu_dong_cap_nhat": true, "kiem_moi_phut": 30,
     "dong_bo_git": {"ma_may": "vps-jp1"}}

`tu_dong_cap_nhat` chỉ TẮT khi ghi đúng `false` — thiếu tệp/thiếu khoá/giá trị lạ
đều là BẬT (VPS mới cũng bật). Tắt thì vẫn kiểm và báo "có bản mới", chỉ không
tự áp; nút "Cập nhật ngay" vẫn dùng được.

Mọi lệnh git đi qua `core.dong_bo_git.git` (seam `_chay`), nên test thay được.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import dong_bo_git as dbg

__all__ = [
    "KHO_MAC_DINH", "NHANH_MAC_DINH", "doc_cau_hinh", "dat_tu_dong",
    "phan_tich", "tang", "moi_hon", "doc_phien_ban",
    "them_dong_changelog", "doc_changelog",
    "doc_trang_thai", "ghi_trang_thai", "kiem", "quyet_dinh", "nhip",
    "yeu_cau_cap_nhat_ngay", "yeu_cau_quay_lai", "tag_lui", "day_sua_cuc_bo",
    "bo_sua_cuc_bo", "giu_khoa", "nha_khoa", "dang_cap_nhat",
]

KHO_MAC_DINH = "manhthang1905-hub/mytool-vps"
NHANH_MAC_DINH = "main"
KIEM_MOI_PHUT = 30

#: Tiêu đề mục tự ghi trong CHANGELOG.md — dòng mới chèn NGAY DƯỚI (mới nhất ở trên).
DAU_MUC_CHANGELOG = "## Các bản đẩy lên kho chung (tự ghi bởi `dong_bo_git day`, mới nhất ở trên)"
_DONG_CHANGELOG = re.compile(
    r"^- \*\*(\d+\.\d+\.\d+)\*\* — (\d{4}-\d{2}-\d{2}) — `([^`]*)` — (.*)$")
_SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

#: Khoá tiến trình cập nhật đang chạy — quá hạn này coi như chết (theo dõi 20' + dựng kiểm).
KHOA_QUA_HAN_GIAY = 3 * 3600


# ═══ cấu hình ═══════════════════════════════════════════════════════════════


def _duong_cap_nhat_json(goc: str) -> str:
    return os.path.join(goc, "cap-nhat.json")


def _doc_json_goc(goc: str) -> Dict[str, Any]:
    try:
        with io.open(_duong_cap_nhat_json(goc), encoding="utf-8-sig") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def doc_cau_hinh(goc: str) -> Dict[str, Any]:
    """Không bao giờ ném lỗi. `tu_dong_cap_nhat` mặc định True (chỉ `false` mới tắt)."""
    du = _doc_json_goc(goc)
    kho = str(du.get("kho") or "").strip().strip("/") or KHO_MAC_DINH
    if kho.lower().startswith("https://github.com/"):
        kho = kho[len("https://github.com/"):]
    if kho.endswith(".git"):
        kho = kho[:-4]
    nhanh = str(du.get("nhanh") or "").strip() or NHANH_MAC_DINH
    try:
        phut = max(5, min(1440, int(du.get("kiem_moi_phut") or KIEM_MOI_PHUT)))
    except (TypeError, ValueError):
        phut = KIEM_MOI_PHUT
    return {"kho": kho, "nhanh": nhanh, "tu_dong_cap_nhat": du.get("tu_dong_cap_nhat") is not False,
            "kiem_moi_phut": phut}


def dat_tu_dong(goc: str, bat: bool) -> bool:
    """Ghi `tu_dong_cap_nhat` vào `cap-nhat.json`, GIỮ mọi khoá khác. Ghi qua tệp tạm."""
    du = _doc_json_goc(goc)
    du["tu_dong_cap_nhat"] = bool(bat)
    if not str(du.get("kho") or "").strip():
        du["kho"] = KHO_MAC_DINH
    du.setdefault("nhanh", NHANH_MAC_DINH)
    duong = _duong_cap_nhat_json(goc)
    try:
        tam = duong + ".tam"
        with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=2)
            tep.write("\n")
        os.replace(tam, duong)
    except OSError:
        return False
    ghi_trang_thai(goc, tu_dong=bool(bat))
    return True


# ═══ phiên bản (semver) ═════════════════════════════════════════════════════


def phan_tich(v: str) -> Optional[Tuple[int, int, int]]:
    """`"2.132.0"` → (2, 132, 0). BOM/khoảng trắng bỏ; sai dạng → None."""
    m = _SEMVER.match((v or "").lstrip("﻿").strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def tang(v: str, muc: str = "patch") -> str:
    so = phan_tich(v) or (0, 0, 0)
    if muc == "major":
        return "{0}.0.0".format(so[0] + 1)
    if muc == "minor":
        return "{0}.{1}.0".format(so[0], so[1] + 1)
    return "{0}.{1}.{2}".format(so[0], so[1], so[2] + 1)


def moi_hon(a: str, b: str) -> bool:
    pa, pb = phan_tich(a), phan_tich(b)
    return bool(pa and pb and pa > pb)


def doc_phien_ban(goc: str) -> str:
    try:
        with io.open(os.path.join(goc, "VERSION"), encoding="utf-8-sig") as tep:
            return tep.read().strip()
    except OSError:
        return ""


# ═══ CHANGELOG.md ═══════════════════════════════════════════════════════════


def _mot_dong(chu: str, toi_da: int = 240) -> str:
    chu = " ".join((chu or "").split())
    return chu if len(chu) <= toi_da else chu[:toi_da - 1] + "…"


def them_dong_changelog(chu: str, phien_ban: str, ngay: str, ma_may: str, thong_diep: str) -> str:
    """Chèn `- **x.y.z** — ngày — `máy` — thông điệp` ngay dưới `DAU_MUC_CHANGELOG`.
    Chưa có mục thì dựng mục trước tiêu đề `## ` đầu tiên (sau phần giới thiệu)."""
    dong = "- **{0}** — {1} — `{2}` — {3}".format(phien_ban, ngay, _mot_dong(ma_may, 40).replace("`", "'"),
                                                _mot_dong(thong_diep))
    cac = chu.splitlines()
    if DAU_MUC_CHANGELOG not in cac:
        vi_tri = next((i for i, d in enumerate(cac) if d.startswith("## ")), len(cac))
        chen = [DAU_MUC_CHANGELOG, "", dong, ""]
        if vi_tri > 0 and cac[vi_tri - 1].strip():
            chen.insert(0, "")
        cac[vi_tri:vi_tri] = chen
    else:
        dau = cac.index(DAU_MUC_CHANGELOG)
        i = dau + 1
        while i < len(cac) and not cac[i].strip():
            i += 1
        if i < len(cac) and cac[i].startswith("- **"):
            cac.insert(i, dong)          # mới nhất ở trên
        else:
            cac[dau + 1:i] = ["", dong, ""]
    return "\n".join(cac).rstrip("\n") + "\n"


def doc_changelog(chu: str) -> List[Dict[str, str]]:
    ra: List[Dict[str, str]] = []
    for d in (chu or "").splitlines():
        m = _DONG_CHANGELOG.match(d.strip())
        if m:
            ra.append({"phien_ban": m.group(1), "ngay": m.group(2), "may": m.group(3),
                       "noi_dung": m.group(4).strip()})
    return ra


def _show(goc: str, ref: str, tep: str) -> str:
    ma, ra, _ = dbg.git(goc, "show", "{0}:{1}".format(ref, tep), timeout=60)
    return ra if ma == 0 else ""


# ═══ trạng thái (workspace/cap-nhat/trang-thai.json) ════════════════════════


def _thu_muc(goc: str) -> str:
    return os.path.join(goc, "workspace", "cap-nhat")


def duong_trang_thai(goc: str) -> str:
    return os.path.join(_thu_muc(goc), "trang-thai.json")


def doc_trang_thai(goc: str) -> Dict[str, Any]:
    try:
        with io.open(duong_trang_thai(goc), encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_trang_thai(goc: str, **muc: Any) -> Dict[str, Any]:
    du = doc_trang_thai(goc)
    du.update(muc)
    try:
        os.makedirs(_thu_muc(goc), exist_ok=True)
        tam = duong_trang_thai(goc) + ".{0}.tam".format(os.getpid())
        with io.open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong_trang_thai(goc))
    except OSError:
        pass
    return du


def _bay_gio_chu(bay_gio: Optional[_dt.datetime] = None) -> str:
    return (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d %H:%M")


def ghi_ket_qua(goc: str, ket_qua: str, chi_tiet: str = "", **them: Any) -> None:
    """Kết quả lượt cập nhật / quay lại gần nhất (cho dòng trạng thái giao diện)."""
    muc = {"luc": _bay_gio_chu(), "ket_qua": ket_qua, "chi_tiet": _mot_dong(chi_tiet, 400)}
    muc.update(them)
    ghi_trang_thai(goc, cap_nhat_cuoi=muc)
    try:
        os.makedirs(_thu_muc(goc), exist_ok=True)
        with io.open(os.path.join(_thu_muc(goc), "nhat-ky.txt"), "a", encoding="utf-8") as tep:
            tep.write("{0} {1}: {2}\n".format(muc["luc"], ket_qua, muc["chi_tiet"]))
    except OSError:
        pass


# ═══ khoá "đang cập nhật" (một tiến trình keo/lui mỗi lúc) ══════════════════


def _duong_khoa(goc: str) -> str:
    return os.path.join(_thu_muc(goc), "dang-cap-nhat.json")


def _pid_song(pid: int) -> bool:
    try:
        from .tien_trinh_con import con_song  # noqa: PLC0415
        return bool(con_song(int(pid)))
    except Exception:  # noqa: BLE001
        return False


def dang_cap_nhat(goc: str) -> Dict[str, Any]:
    """{} nếu không có lượt nào đang chạy; khoá của tiến trình chết/quá hạn bị bỏ qua."""
    try:
        with io.open(_duong_khoa(goc), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {}
    if not isinstance(du, dict):
        return {}
    if time.time() - float(du.get("tu_luc") or 0) > KHOA_QUA_HAN_GIAY:
        return {}
    if du.get("pid") != os.getpid() and not _pid_song(int(du.get("pid") or 0)):
        return {}
    return du


def giu_khoa(goc: str, viec: str) -> bool:
    cu = dang_cap_nhat(goc)
    if cu and cu.get("pid") != os.getpid():
        return False
    try:
        os.makedirs(_thu_muc(goc), exist_ok=True)
        with io.open(_duong_khoa(goc), "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "viec": viec, "tu_luc": time.time(),
                       "luc": _bay_gio_chu()}, tep, ensure_ascii=False)
        return True
    except OSError:
        return False


def nha_khoa(goc: str) -> None:
    du = dang_cap_nhat(goc)
    if du and du.get("pid") != os.getpid():
        return
    try:
        os.remove(_duong_khoa(goc))
    except OSError:
        pass


# ═══ KIỂM ═══════════════════════════════════════════════════════════════════


def _dich() -> str:
    return "{0}/{1}".format(dbg.REMOTE, dbg.NHANH)


def kiem(goc: str, *, co_fetch: bool = True, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Một lượt kiểm NHẸ: `git fetch` → `origin/main:VERSION` + CHANGELOG. Ghi và trả trạng thái."""
    cfg = doc_cau_hinh(goc)
    hien_tai = doc_phien_ban(goc)
    chung = {"hien_tai": hien_tai, "kho": cfg["kho"], "nhanh": cfg["nhanh"],
             "tu_dong": cfg["tu_dong_cap_nhat"], "kiem_luc": _bay_gio_chu(bay_gio),
             "kiem_epoch": time.time()}
    if not dbg.la_kho_git(goc):
        return ghi_trang_thai(goc, kiem_ok=False, ban_moi="", thay_doi=[], co_sua_chua_day=[],
                              loi="Bản cài này không có Git nên không tự cập nhật được — "
                                  "cài lại bằng CAI-DAT-VPS.bat (git clone kho chung).", **chung)
    loi = ""
    if co_fetch:
        ok, chu = dbg.fetch(goc)
        if not ok:
            loi = "Chưa nối được GitHub: " + _mot_dong(chu, 200)
    if not dbg._co_ref(goc, _dich()):  # noqa: SLF001
        return ghi_trang_thai(goc, kiem_ok=False, ban_moi="", thay_doi=[],
                              loi=loi or "Kho chung chưa có nhánh main.", **chung)
    xa = _show(goc, _dich(), "VERSION").strip()
    sha_xa = dbg.git(goc, "rev-parse", _dich())[1].strip()
    truoc, sau = dbg.truoc_sau(goc)
    doi = dbg.tep_doi_cuc_bo(goc)
    thay_doi = [d for d in doc_changelog(_show(goc, _dich(), "CHANGELOG.md"))
                if moi_hon(d["phien_ban"], hien_tai)] if sau else []
    return ghi_trang_thai(
        goc, kiem_ok=not loi, loi=loi, ban_xa=xa, sha_xa=sha_xa,
        ban_moi=(xa or "?") if sau else "", so_commit_moi=sau or 0, so_commit_chua_day=truoc or 0,
        thay_doi=thay_doi[:40], co_sua_chua_day=doi[:60], **chung)


def quyet_dinh(goc: str, tt: Dict[str, Any], cfg: Dict[str, Any],
               bay_gio: Optional[_dt.datetime] = None) -> Tuple[str, str]:
    """("ap" | "cho" | "khong", lý do). "cho" = có bản mới, được phép, chỉ chờ máy rảnh."""
    if tt.get("hen_quay_lai"):
        if tt.get("co_sua_chua_day"):
            return "khong", "máy có sửa chưa đẩy — không quay lại được"
        ly = dbg.ly_do_chua_ranh(goc, bay_gio)
        return ("cho", "; ".join(ly)) if ly else ("lui", "quay lại " + str(tt["hen_quay_lai"]))
    if not tt.get("ban_moi"):
        return "khong", "đang dùng bản mới nhất"
    if tt.get("bo_qua_sha") and tt.get("bo_qua_sha") == tt.get("sha_xa") and not tt.get("hen_cap_nhat"):
        return "khong", "bỏ qua bản {0} (đã lùi/hỏng kiểm) — chờ bản mới hơn".format(tt.get("ban_xa") or "?")
    if not (cfg.get("tu_dong_cap_nhat") or tt.get("hen_cap_nhat")):
        return "khong", "tự động cập nhật đang tắt"
    if dang_cap_nhat(goc):
        return "khong", "đang có một lượt cập nhật chạy"
    if tt.get("co_sua_chua_day"):
        return "khong", "máy này có sửa chưa đẩy lên kho"
    if tt.get("so_commit_chua_day"):
        return "khong", "máy này có commit chưa đẩy lên kho"
    ly = dbg.ly_do_chua_ranh(goc, bay_gio)
    if ly:
        return "cho", "; ".join(ly)
    return "ap", ""


def _python_nen() -> str:
    return dbg._python()  # noqa: SLF001 — python.exe (không pythonw) để log được


#: Tiến trình TRUNG GIAN: sinh tiến trình thật rồi thoát ngay. Nhờ vậy tiến trình
#: thật KHÔNG còn là con cháu của giao diện — `khoi_dong_lai` giết giao diện bằng
#: `taskkill /T` (cả cây) mà không giết luôn chính lượt cập nhật đang chạy.
_TRUNG_GIAN = (
    "import subprocess, sys, json\n"
    "a = json.loads(sys.argv[1])\n"
    "log = open(a['log'], 'a', encoding='utf-8')\n"
    "p = subprocess.Popen(a['lenh'], cwd=a['cwd'], creationflags=a['co'], close_fds=True,\n"
    "                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)\n"
    "log.write('pid %d\\n' % p.pid)\n"
)


def sinh_tien_trinh(goc: str, tham_so: Sequence[str]) -> int:
    """`python -m core.dong_bo_git <tham_so>` TÁCH RỜI: thoát khỏi job
    kill-on-close của giao diện (`CO_TACH_KHOI_JOB`) và khỏi cây tiến trình của
    nó (qua `_TRUNG_GIAN`). Trả PID tiến trình trung gian (0 = không sinh được)."""
    os.makedirs(_thu_muc(goc), exist_ok=True)
    duong_log = os.path.join(_thu_muc(goc), "tien-trinh.log")
    try:
        with io.open(duong_log, "a", encoding="utf-8") as log:
            log.write("\n{0} sinh: dong_bo_git {1}\n".format(_bay_gio_chu(), " ".join(tham_so)))
    except OSError:
        pass
    co = 0
    if os.name == "nt":
        for ten in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP"):
            co |= getattr(subprocess, ten, 0)
    try:
        from .tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        CO_TACH_KHOI_JOB = 0  # noqa: N806
    lenh = [_python_nen(), "-X", "utf8", "-m", "core.dong_bo_git", *tham_so]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for co_thu in ((co | CO_TACH_KHOI_JOB), co):
        doi_so = json.dumps({"lenh": lenh, "cwd": goc, "co": co_thu, "log": duong_log})
        try:
            p = subprocess.Popen([_python_nen(), "-c", _TRUNG_GIAN, doi_so], cwd=goc,  # noqa: S603
                                 creationflags=co_thu, close_fds=True, env=env,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            return p.pid
        except OSError:
            continue
    return 0


def nhip(goc: str, *, bat_buoc_kiem: bool = False, bay_gio: Optional[_dt.datetime] = None,
         sinh: Optional[Callable[[str, Sequence[str]], int]] = None) -> Dict[str, Any]:
    """Gọi định kỳ (gác tổng 15', giao diện 30') và khi mở giao diện. Kiểm nếu đã
    quá `kiem_moi_phut`, rồi quyết: áp (sinh `keo`), chờ máy rảnh, hay thôi."""
    cfg = doc_cau_hinh(goc)
    tt = doc_trang_thai(goc)
    tuoi = time.time() - float(tt.get("kiem_epoch") or 0)
    if bat_buoc_kiem or tuoi >= (cfg["kiem_moi_phut"] - 2) * 60:
        tt = kiem(goc, bay_gio=bay_gio)
    else:
        # không fetch, nhưng tình trạng cục bộ (sửa chưa đẩy, cờ tự động) phải mới
        tt = ghi_trang_thai(goc, tu_dong=cfg["tu_dong_cap_nhat"],
                            co_sua_chua_day=dbg.tep_doi_cuc_bo(goc)[:60] if dbg.la_kho_git(goc) else [])
    viec, ly_do = quyet_dinh(goc, tt, cfg, bay_gio)
    pid = 0
    if viec == "ap":
        tham = ["keo", "--cho-toi-da-phut", "0"] + (["--ep"] if tt.get("hen_cap_nhat") else [])
        pid = (sinh or sinh_tien_trinh)(goc, tham)
        ly_do = "đã bắt đầu cập nhật (tiến trình {0})".format(pid) if pid else "không sinh được tiến trình cập nhật"
    elif viec == "lui":
        pid = (sinh or sinh_tien_trinh)(goc, ["lui", "--tag", str(tt.get("hen_quay_lai"))])
        ly_do = "đã bắt đầu quay lại (tiến trình {0})".format(pid) if pid else "không sinh được tiến trình quay lại"
    tt = ghi_trang_thai(goc, quyet=viec, quyet_ly_do=ly_do, quyet_luc=_bay_gio_chu(bay_gio))
    tt["tom_tat"] = tom_tat(tt)
    return tt


def tom_tat(tt: Dict[str, Any]) -> str:
    """Một câu tiếng Việt cho người thường (dòng lệnh, gác tổng)."""
    if tt.get("loi") and not tt.get("ban_moi"):
        return "bản {0} — {1}".format(tt.get("hien_tai") or "?", tt["loi"])
    if tt.get("ban_moi"):
        return "bản {0} — có bản mới {1} — {2}".format(
            tt.get("hien_tai") or "?", tt["ban_moi"], tt.get("quyet_ly_do") or "")
    return "bản {0} — mới nhất".format(tt.get("hien_tai") or "?")


# ═══ hành động từ giao diện ═════════════════════════════════════════════════


def yeu_cau_cap_nhat_ngay(goc: str, *, sinh: Optional[Callable[[str, Sequence[str]], int]] = None) -> Dict[str, Any]:
    """Nút "Cập nhật ngay": kiểm lại, đặt hẹn, áp ngay nếu máy rảnh — không thì
    lượt nhịp kế tiếp tự áp khi rảnh. Vẫn đủ mọi luật an toàn của `keo`."""
    tt = kiem(goc)
    if not tt.get("ban_moi"):
        return dict(tt, cau="Máy đang ở bản mới nhất ({0}).".format(tt.get("hien_tai") or "?"))
    if tt.get("co_sua_chua_day") or tt.get("so_commit_chua_day"):
        return dict(tt, cau="Máy này có sửa chưa đẩy lên kho — đẩy trước hoặc bỏ các sửa đó, rồi bấm lại.")
    ghi_trang_thai(goc, hen_cap_nhat=True, hen_luc=_bay_gio_chu())
    tt = nhip(goc, sinh=sinh)
    if tt.get("quyet") == "ap":
        cau = "Đang cập nhật lên {0}. Giao diện sẽ tự đóng rồi mở lại trong vài phút.".format(tt["ban_moi"])
    elif tt.get("quyet") == "cho":
        cau = ("Máy đang bận ({0}). Tool sẽ tự cập nhật lên {1} khi máy rảnh — "
               "không cần bấm lại.").format(tt.get("quyet_ly_do") or "?", tt["ban_moi"])
    else:
        cau = "Chưa cập nhật được: {0}.".format(tt.get("quyet_ly_do") or "?")
    return dict(tt, cau=cau)


def tag_lui(goc: str) -> List[str]:
    """Các tag `truoc-cap-nhat-*` (mới nhất trước) — các bản có thể quay lại."""
    ma, ra, _ = dbg.git(goc, "tag", "--list", dbg.TIEN_TO_TAG + "*", "--sort=-creatordate")
    return [t for t in ra.split() if t] if ma == 0 else []


def yeu_cau_quay_lai(goc: str, *, sinh: Optional[Callable[[str, Sequence[str]], int]] = None) -> Dict[str, Any]:
    """Nút "Quay lại bản trước": về tag `truoc-cap-nhat-*` mới nhất, theo luật máy rảnh."""
    tags = tag_lui(goc) if dbg.la_kho_git(goc) else []
    if not tags:
        return {"cau": "Chưa có bản trước nào để quay lại (máy này chưa tự cập nhật lần nào)."}
    if dbg.tep_doi_cuc_bo(goc):
        return {"cau": "Máy này có sửa chưa đẩy lên kho — đẩy trước hoặc bỏ, rồi mới quay lại được."}
    ghi_trang_thai(goc, hen_quay_lai=tags[0], hen_cap_nhat=False)
    tt = nhip(goc, sinh=sinh)
    if tt.get("quyet") == "lui":
        cau = "Đang quay lại bản trước. Giao diện sẽ tự đóng rồi mở lại."
    elif tt.get("quyet") == "cho":
        cau = "Máy đang bận ({0}). Tool sẽ tự quay lại khi máy rảnh.".format(tt.get("quyet_ly_do") or "?")
    else:
        cau = "Chưa quay lại được: {0}.".format(tt.get("quyet_ly_do") or "?")
    return dict(tt, cau=cau)


def day_sua_cuc_bo(goc: str, thong_diep: str = "") -> Tuple[int, str]:
    """Nút "Đẩy lên kho": chạy `day` (kiểm + quét bí mật + tự nâng version)."""
    dong: List[str] = []
    ma_may = dbg.doc_cau_hinh(goc)["ma_may"]
    ma = dbg.day(goc, thong_diep or "sửa tại máy {0} (đẩy từ giao diện)".format(ma_may), in_ra=dong.append)
    kiem(goc, co_fetch=False)
    return ma, "\n".join(dong[-25:])


def bo_sua_cuc_bo(goc: str) -> Tuple[bool, str]:
    """Nút "Bỏ các sửa này": CẤT vào `git stash` (lấy lại được bằng `git stash pop`), không xoá."""
    ma, ra, loi = dbg.git(goc, "stash", "push", "-u", "-m",
                          "bo-sua-tu-giao-dien-" + time.strftime("%Y%m%d-%H%M%S"))
    kiem(goc, co_fetch=False)
    if ma != 0:
        return False, (loi or ra).strip()[:400]
    return True, "Đã cất các sửa vào git stash (lấy lại: git stash pop)."


# ═══ dòng lệnh: python -m core.cap_nhat_git [kiem|nhip|tu_dong bat|tat] ═════


def main(argv: Optional[Sequence[str]] = None) -> int:
    ds = list(sys.argv[1:] if argv is None else argv)
    goc = dbg.GOC
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError, OSError):
        pass
    lenh = ds[0] if ds else "kiem"
    if lenh == "kiem":
        tt = kiem(goc)
    elif lenh == "nhip":
        tt = nhip(goc)
    elif lenh == "tu_dong" and len(ds) > 1 and ds[1] in ("bat", "tat"):
        dat_tu_dong(goc, ds[1] == "bat")
        tt = doc_trang_thai(goc)
    else:
        print("Dùng: python -m core.cap_nhat_git [kiem | nhip | tu_dong bat|tat]")
        return 0
    print(tom_tat(tt))
    for d in tt.get("thay_doi") or []:
        print("  {phien_ban} ({ngay}, {may}): {noi_dung}".format(**d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
