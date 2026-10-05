"""core/bao_cao_ngay.py — "Báo cáo sức khoẻ hằng ngày": MỘT bản tin tiếng Việt ngắn (≤ ~40 dòng) chủ đọc trên điện thoại buổi sáng.

Sáu mục, mục nào hỏng cũng chỉ in một dòng "không đọc được" — không mục nào làm vỡ cả bản tin:
  1 Video mai (kênh nào đã có video ngày mai)      4 Chiến trường (thị phần, quy mô ngách, đối thủ số 1, lệnh tác chiến)
  2 Skill hỏng/thiếu (core.ky_nang)                5 Lỗi 24 giờ (workspace/loi-chay-max.md, bỏ mức nhắc)
  3 Đường tới YPP (core.ypp.du_bao)                6 Máy (RAM, đĩa, nhịp tim agent)

Dùng:  python -m core.bao_cao_ngay            in ra
       python -m core.bao_cao_ngay --ghi      ghi workspace/bao-cao-ngay/<ngày>.md
       python -m core.bao_cao_ngay --gui      gửi qua core.bao_dong (Telegram/webhook nếu đã cấu hình; không thì bỏ qua)
`chay_hang_ngay(goc)` là chỗ gác tổng gọi: sau 06:30 mỗi ngày ghi + gửi ĐÚNG MỘT lần (trạng thái `workspace/bao-cao-ngay/.trang-thai.json`).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import sys
import time
from typing import Any, Callable, Dict, List, Optional

GIO_GUI = (6, 30)
TOI_DA_GUI_MOI_NGAY = 3          # gửi lỗi mạng thì thử lại ở nhịp sau, tối đa ngần này lần/ngày
GIOI_HAN_TIN = 3900              # Telegram cắt ở 4096 ký tự
_LOAI_BAO_DONG = "bao_cao_ngay"


def _goc_mac_dinh() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _muc(tieu_de: str, ham: Callable[[], List[str]]) -> List[str]:
    """Chạy một mục; hỏng → một dòng thông báo, KHÔNG ném lỗi."""
    try:
        dong = [d for d in ham() if d is not None]
    except Exception as loi:  # noqa: BLE001 — một mục hỏng không làm vỡ bản tin
        dong = ["(không đọc được: {0})".format(str(loi)[:80])]
    return ["**{0}**".format(tieu_de)] + dong


def _cac_kenh(goc: str) -> List[str]:
    from core import ypp  # noqa: PLC0415
    return ypp.cac_kenh(goc)


# ── 1. Video mai ──────────────────────────────────────────────────────────────

def _muc_video(goc: str, bay_gio: _dt.datetime) -> List[str]:
    from core import truc_quan  # noqa: PLC0415
    mai = bay_gio.date() + _dt.timedelta(days=1)
    ra = []
    for k in _cac_kenh(goc):
        v = truc_quan._video_mai(k, tu_ngay=mai) or {}  # noqa: SLF001
        if not v:
            ra.append("- {0}: ? không đọc được kế hoạch đăng".format(k))
        elif v.get("co") and v.get("ngay") == mai.strftime("%d/%m"):
            ra.append("- {0}: có video mai {1} {2}{3}".format(
                k, v.get("ngay"), v.get("gio") or "", " (đã hẹn lịch)" if v.get("da_hen") else " (chưa hẹn)"))
        elif v.get("co"):
            ra.append("- {0}: MAI TRỐNG — video gần nhất {1}".format(k, v.get("ngay")))
        else:
            ra.append("- {0}: MAI TRỐNG — chưa có video nào xếp lịch".format(k))
    return ra or ["(chưa có kênh)"]


# ── 2. Skill ──────────────────────────────────────────────────────────────────

def _muc_skill(goc: str) -> List[str]:
    from core import ky_nang  # noqa: PLC0415
    loi: Dict[str, List[str]] = {}
    thieu: Dict[str, List[str]] = {}
    for k in _cac_kenh(goc):
        for sk, tt, _gc in ky_nang.kiem_kenh(goc, k):
            nhan = "{0} {1}".format(sk.ma, sk.ten)
            if tt == ky_nang.LOI:
                loi.setdefault(nhan, []).append(k)
            elif tt == ky_nang.THIEU and sk.loai == "khoi_tao":
                thieu.setdefault(nhan, []).append(k)
    ra = ["- HỎNG {0}: {1}".format(n, ", ".join(ks)) for n, ks in sorted(loi.items())]
    ra += ["- THIẾU {0}: {1}".format(n, ", ".join(ks)) for n, ks in sorted(thieu.items())]
    return ra or ["- không skill nào hỏng/thiếu"]


# ── 3. YPP ────────────────────────────────────────────────────────────────────

def _muc_ypp(goc: str, bay_gio: _dt.datetime) -> List[str]:
    from core import ypp  # noqa: PLC0415
    ra = []
    for k in _cac_kenh(goc):
        r = ypp.du_bao(goc, k, bay_gio)
        if r.get("gio") is None:
            continue
        eta = {"dat": "ĐÃ ĐỦ", "cham": "chậm/không tăng", "chua_du_so": "chưa đủ số liệu"}.get(
            r.get("trang_thai"), r.get("ngay_du_kien") or "?")
        if r.get("trang_thai") in ("gan", "dang_len") and r.get("ngay_toi") is not None:
            eta = "dự kiến {0} (~{1:.0f} ngày)".format(r.get("ngay_du_kien"), r["ngay_toi"])
        ra.append("- {0}: {1:.0f}/4000h · {2}/1000 đk · {3}".format(k, float(r["gio"]), r.get("dang_ky"), eta))
    return ra or ["(chưa kênh nào có số liệu)"]


# ── 4. Chiến trường ───────────────────────────────────────────────────────────

def _gon(n: Any) -> str:
    n = float(n or 0)
    return "{0:.1f}tr".format(n / 1e6) if n >= 1e6 else ("{0:.0f}k".format(n / 1e3) if n >= 1e3 else "{0:.0f}".format(n))


def _muc_chien_truong() -> List[str]:
    from core import chien_truong  # noqa: PLC0415
    d = chien_truong.tinh()
    t = d.get("tong") or {}
    ra = ["- Thị phần ta {0}% · ngách ~{1} lượt/tháng (địch {2}, ta {3})".format(
        t.get("thi_phan", 0), _gon((t.get("dich") or 0) + (t.get("ta") or 0)), _gon(t.get("dich")), _gon(t.get("ta")))]
    top = (d.get("dich_top") or [None])[0]
    if top:
        ra.append("- Đối thủ số 1: {0} ({1}/tháng, {2}%)".format(top.get("kenh"), _gon(top.get("view")), top.get("thi_phan")))
    for x in (d.get("de_xuat_tan_cong") or [])[:3]:
        vs = " | ".join("{0} ({1})".format(v.get("ten"), v.get("co_hoi")) for v in (x.get("vung") or [])[:2])
        ra.append("- Lệnh {0} → {1}".format(x.get("kenh"), vs or "-"))
    return ra


# ── 5. Lỗi 24h ────────────────────────────────────────────────────────────────

_RE_LOI = re.compile(r"^- \[(\d{4}-\d\d-\d\d \d\d:\d\d)\] \*\*(\w+)\*\*\s*(.*)$")


def _muc_loi(goc: str, bay_gio: _dt.datetime, toi_da: int = 6) -> List[str]:
    duong = os.path.join(goc, "workspace", "loi-chay-max.md")
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            dong = tep.read().splitlines()
    except OSError:
        return ["- (chưa có nhật ký lỗi)"]
    moc = bay_gio - _dt.timedelta(hours=24)
    dem: Dict[str, int] = {}
    for d in dong:
        m = _RE_LOI.match(d.strip())
        if not m or m.group(2).lower() == "nhac":
            continue
        try:
            luc = _dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if luc >= moc:
            noi = m.group(3).lstrip("—- ").strip()[:110]
            dem[noi] = dem.get(noi, 0) + 1
    if not dem:
        return ["- không có lỗi nào trong 24 giờ"]
    ra = ["- {0}{1}".format(n, " (x{0})".format(c) if c > 1 else "") for n, c in list(dem.items())[-toi_da:]]
    if len(dem) > toi_da:
        ra.append("- … và {0} lỗi khác".format(len(dem) - toi_da))
    return ra


# ── 6. Máy ────────────────────────────────────────────────────────────────────

def _muc_may(goc: str) -> List[str]:
    from core import truc_quan  # noqa: PLC0415
    ram = truc_quan._ram_gb()  # noqa: SLF001
    dia = shutil.disk_usage(goc)
    ra = ["- RAM trống {0}/{1} GB · đĩa trống {2:.0f} GB".format(ram.get("trong"), ram.get("tong"), dia.free / 2 ** 30)]
    try:
        tuoi = (time.time() - os.path.getmtime(os.path.join(goc, "vm", "logs", "nhip-tim.json"))) / 60.0
        ra.append("- Agent: nhịp tim cách đây {0:.0f} phút{1}".format(tuoi, " — CŨ, kiểm agent" if tuoi > 20 else ""))
    except OSError:
        ra.append("- Agent: không thấy nhịp tim")
    return ra


# ── bản tin ───────────────────────────────────────────────────────────────────

def tao(goc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None) -> str:
    goc = goc or _goc_mac_dinh()
    bay_gio = bay_gio or _dt.datetime.now()
    kh: List[str] = ["# Báo cáo sức khoẻ — {0}".format(bay_gio.strftime("%d/%m/%Y %H:%M")), ""]
    cac = [
        ("Video ngày mai", lambda: _muc_video(goc, bay_gio)),
        ("Skill hỏng/thiếu", lambda: _muc_skill(goc)),
        ("Đường tới YPP", lambda: _muc_ypp(goc, bay_gio)),
        ("Chiến trường", _muc_chien_truong),
        ("Lỗi 24 giờ", lambda: _muc_loi(goc, bay_gio)),
        ("Máy", lambda: _muc_may(goc)),
    ]
    for ten, ham in cac:
        kh += _muc(ten, ham) + [""]
    return "\n".join(kh).rstrip() + "\n"


def _thu_muc(goc: str, thu_muc: Optional[str]) -> str:
    return thu_muc or os.path.join(goc, "workspace", "bao-cao-ngay")


def ghi(goc: Optional[str] = None, thu_muc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None,
        van_ban: Optional[str] = None) -> str:
    goc = goc or _goc_mac_dinh()
    bay_gio = bay_gio or _dt.datetime.now()
    nd = van_ban if van_ban is not None else tao(goc, bay_gio)
    tm = _thu_muc(goc, thu_muc)
    os.makedirs(tm, exist_ok=True)
    duong = os.path.join(tm, bay_gio.strftime("%Y-%m-%d") + ".md")
    with open(duong, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(nd)
    return duong


# ── trạng thái "một lần/ngày" ─────────────────────────────────────────────────

def _doc_tt(tm: str) -> Dict[str, Any]:
    try:
        with open(os.path.join(tm, ".trang-thai.json"), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_tt(tm: str, d: Dict[str, Any]) -> None:
    os.makedirs(tm, exist_ok=True)
    with open(os.path.join(tm, ".trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump(d, tep, ensure_ascii=False)


def _gui_mac_dinh(goc: str, van_ban: str) -> bool:
    from core import bao_dong  # noqa: PLC0415
    return bool(bao_dong.bao_dong(_LOAI_BAO_DONG, van_ban[:GIOI_HAN_TIN], "", goc=goc))


def gui(goc: Optional[str] = None, thu_muc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None,
        van_ban: Optional[str] = None, ham_gui: Optional[Callable[[str, str], bool]] = None) -> str:
    """Gửi tối đa MỘT lần/ngày. Trả: 'da_gui' | 'da_gui_truoc_do' | 'chua_cau_hinh' | 'that_bai'.
    `ham_gui(goc, van_ban) -> bool` là seam cho test (mặc định core.bao_dong.bao_dong — tự nuốt lỗi mạng)."""
    goc = goc or _goc_mac_dinh()
    bay_gio = bay_gio or _dt.datetime.now()
    hom = bay_gio.strftime("%Y-%m-%d")
    tm = _thu_muc(goc, thu_muc)
    tt = _doc_tt(tm)
    if tt.get("ngay_gui") == hom:
        return "da_gui_truoc_do"
    if ham_gui is None:
        from core import bao_dong  # noqa: PLC0415
        if not bao_dong.doc_cau_hinh_bao_dong(goc):
            tt["ngay_gui"], tt["ket_qua_gui"] = hom, "chua_cau_hinh"
            _ghi_tt(tm, tt)
            return "chua_cau_hinh"
        ham_gui = _gui_mac_dinh
    nd = van_ban if van_ban is not None else tao(goc, bay_gio)
    thu = int(tt.get("thu") or 0) if tt.get("ngay_thu") == hom else 0
    ok = False
    try:
        ok = bool(ham_gui(goc, nd))
    except Exception:  # noqa: BLE001
        ok = False
    thu += 1
    tt["ngay_thu"], tt["thu"] = hom, thu
    if ok or thu >= TOI_DA_GUI_MOI_NGAY:
        tt["ngay_gui"], tt["ket_qua_gui"] = hom, ("da_gui" if ok else "that_bai")
    _ghi_tt(tm, tt)
    return "da_gui" if ok else "that_bai"


def chay_hang_ngay(goc: Optional[str] = None, thu_muc: Optional[str] = None, bay_gio: Optional[_dt.datetime] = None,
                   ham_gui: Optional[Callable[[str, str], bool]] = None) -> str:
    """Gác tổng gọi mỗi nhịp: sau 06:30, mỗi ngày dựng + ghi + gửi MỘT lần. Trả chuỗi tóm tắt 1 dòng ('' nếu chưa tới giờ/đã xong)."""
    goc = goc or _goc_mac_dinh()
    bay_gio = bay_gio or _dt.datetime.now()
    if (bay_gio.hour, bay_gio.minute) < GIO_GUI:
        return ""
    hom = bay_gio.strftime("%Y-%m-%d")
    tm = _thu_muc(goc, thu_muc)
    tt = _doc_tt(tm)
    if tt.get("ngay_ghi") == hom and tt.get("ngay_gui") == hom:
        return ""
    nd = tao(goc, bay_gio)
    duong = ""
    if tt.get("ngay_ghi") != hom:
        duong = ghi(goc, tm, bay_gio, nd)
        tt = _doc_tt(tm)
        tt["ngay_ghi"] = hom
        _ghi_tt(tm, tt)
    kq = gui(goc, tm, bay_gio, nd, ham_gui)
    return "báo cáo ngày {0}: ghi {1}, gửi {2}".format(hom, os.path.basename(duong) or "(đã ghi trước)", kq)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    a = sys.argv[1:] if argv is None else argv
    goc = _goc_mac_dinh()
    nd = tao(goc)
    print(nd)
    if "--ghi" in a:
        print("đã ghi:", ghi(goc, van_ban=nd))
    if "--gui" in a:
        print("gửi:", gui(goc, van_ban=nd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
