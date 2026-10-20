"""TRẢ KÊNH VỀ KHO (19/10/2026) — dừng một kênh kém mà KHÔNG xoá gì, lấy lại được.

Chủ: "kênh view ít thì để lại, coi như trả về kho — tao cấp mail mới làm kênh thay".

Trả kho = tắt mọi công tắc chạy của kênh:
- kenh.yaml: `tu_chay`, `thiet_lap_kenh`, `nuoi_trang_chu` → false; ghi `tra_kho: <ngày>`, `thay_boi: <mã mới>`;
- may-ao.json: `tu_dang`, `tu_tra_loi_cmt`, `binh_luan_dom`, `ghim_dom`, `quet_trang_chu_hang_ngay` → false.
Giá trị cũ cất ở `CHANNEL/<k>/tra-kho.json` để `lay_lai` trả đúng như trước.

KHÔNG gỡ kênh khỏi `vm/config.json` `cac_kenh`: cổng DevTools = 9300 + vị trí trong danh sách, gỡ là lệch cổng mọi
kênh sau. Hồ sơ, tài khoản, dữ liệu, video đã đăng giữ nguyên.

KHO CHROME (20/10/2026, chủ): `<cha của MyTool>\\kho\\` (tính từ GOC, không cứng đường). Trả kho thì thư mục Chrome
Portable của kênh (`<cha>\\<MÃ>\\`) được DỜI sang `kho\\<MÃ>\\` — chỉ khi Chrome kênh không chạy, khoá máy không giữ
cho kênh đó, agent không làm dở việc của kênh đó; bận thì để nhịp sau (`nhip_chrome`). `lay_lai` dời về. KHÔNG BAO GIỜ
xoá thư mục Chrome; đích đã có thì không đè. Chủ cũng thả Chrome Portable MỚI (đã đăng nhập Gmail tay) vào kho — xem
`core/kho_chrome.py`. Mọi chỗ tìm Chrome kênh (`tim_chrome`) lùi về `kho\\<MÃ>\\<MÃ>.exe` khi đường thường không có.

    python -m core.tra_kho tra <MÃ> [--thay <MÃ MỚI>]
    python -m core.tra_kho lay-lai <MÃ>
    python -m core.tra_kho nhip            # dời Chrome các kênh trả kho còn nằm đường thường (khi rảnh)
    python -m core.tra_kho ds
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_LUU = "tra-kho.json"
THU_MUC_KHO = "kho"
KHOA_KENH = ("tu_chay", "thiet_lap_kenh", "nuoi_trang_chu")
KHOA_MAY_AO = ("tu_dang", "tu_tra_loi_cmt", "binh_luan_dom", "ghim_dom", "quet_trang_chu_hang_ngay")
#: Dấu "agent đang làm dở việc" cũ hơn ngần này thì coi như không còn (như `vm/agent.viec_dang_lam`).
HAN_DANG_LAM_GIAY = 15 * 60


def _kenh_yaml(goc: str, ma: str) -> Dict[str, Any]:
    from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    return doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}


def da_tra_kho(goc: str, ma: str) -> bool:
    """Kênh đã trả kho chưa — mọi bộ máy (kỹ năng tự kích hoạt, mở kênh, anh em cùng tệp, số liệu, não…) bỏ qua."""
    from .kenh import da_tra_kho as _da  # noqa: PLC0415

    return _da(goc, ma)


def kenh_dang_chay(goc: str) -> List[str]:
    """Mọi kênh CHƯA trả kho (thư mục CHANNEL có kenh.yaml, bỏ `_…`)."""
    from .kenh import liet_ke_kenh  # noqa: PLC0415

    return liet_ke_kenh(goc)


# ── đường Chrome ────────────────────────────────────────────────────────────
def thu_muc_kho(goc: str) -> str:
    """`<cha của MyTool>\\kho`."""
    return os.path.join(os.path.dirname(os.path.abspath(goc)), THU_MUC_KHO)


def thu_muc_chrome_thuong(goc: str, ma: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(goc)), ma)


def tim_chrome(goc: str, ma: str) -> str:
    """Launcher Chrome Portable của kênh: `<cha>\\<MÃ>\\<MÃ>.exe` (hoặc lồng `<MÃ>\\<MÃ>\\<MÃ>.exe`), không có thì
    `kho\\<MÃ>\\<MÃ>.exe`; '' nếu không thấy ở đâu."""
    ma = str(ma or "").strip()
    if not ma:
        return ""
    cha = os.path.dirname(os.path.abspath(goc))
    for p in (os.path.join(cha, ma, ma + ".exe"), os.path.join(cha, ma, ma, ma + ".exe"),
              os.path.join(thu_muc_kho(goc), ma, ma + ".exe")):
        if os.path.isfile(p):
            return p
    return ""


def _json(duong: str) -> Dict[str, Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def chrome_ban(goc: str, ma: str, thu_muc: str) -> str:
    """'' nếu dời được thư mục Chrome `thu_muc` của kênh `ma`; câu lý do nếu đang bận: Chrome chạy từ thư mục đó,
    khoá máy (`workspace/tu-chay/.khoa-may`) đang giữ cho kênh, agent đang làm dở việc của kênh (`vm/dang-lam.json`)."""
    try:
        from .dang_nhap_gmail import chrome_dang_chay  # noqa: PLC0415

        if chrome_dang_chay(os.path.join(thu_muc, ma + ".exe")):
            return "Chrome kênh đang chạy"
    except Exception:  # noqa: BLE001 — không kiểm được thì coi như bận (an toàn)
        return "không kiểm được Chrome kênh có đang chạy"
    try:
        from .khe import duong_khoa_nang, pid_con_song  # noqa: PLC0415

        k = _json(duong_khoa_nang(goc))
        if k and str(k.get("kenh") or "") == ma and pid_con_song(int(k.get("pid") or 0)):
            return "khoá máy đang giữ cho kênh ({0})".format(k.get("viec") or "?")
    except Exception:  # noqa: BLE001
        pass
    d = _json(os.path.join(goc, "vm", "dang-lam.json"))
    try:
        tuoi = time.time() - float(d.get("tu") or 0)
    except (TypeError, ValueError):
        tuoi = HAN_DANG_LAM_GIAY + 1
    if d and str(d.get("kenh") or "") == ma and tuoi <= HAN_DANG_LAM_GIAY:
        return "agent đang làm việc #{0} của kênh".format(d.get("id"))
    return ""


def _doi(nguon: str, dich: str) -> Tuple[str, str]:
    """Dời nguyên thư mục (đổi tên — cùng ổ đĩa thì tức thì). Không đè; hỏng (tệp đang khoá) → 'hoan'."""
    if os.path.exists(dich):
        return "da_co", "đích {0} đã có — không đè, người kiểm tra".format(dich)
    try:
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        os.rename(nguon, dich)
    except OSError as e:
        return "hoan", "chưa dời được ({0}) — nhịp sau thử lại".format(str(e)[:120])
    return "da_doi", "{0} → {1}".format(nguon, dich)


def cat_chrome(goc: str, ma: str, ban: Optional[Callable[[str, str, str], str]] = None) -> Tuple[str, str]:
    """Dời Chrome kênh `ma` vào kho. (trạng thái, ghi chú): da_doi | o_kho (đã ở kho) | khong_co | hoan (bận) | da_co."""
    nguon = thu_muc_chrome_thuong(goc, ma)
    dich = os.path.join(thu_muc_kho(goc), ma)
    if not os.path.isdir(nguon):
        if os.path.isdir(dich):
            return "o_kho", "Chrome đã ở " + dich
        return "khong_co", "không thấy thư mục Chrome {0}".format(nguon)
    ly = (ban or chrome_ban)(goc, ma, nguon)
    if ly:
        return "hoan", ly + " — chưa dời Chrome vào kho, nhịp sau thử lại"
    return _doi(nguon, dich)


def dua_chrome_ve(goc: str, ma: str, ban: Optional[Callable[[str, str, str], str]] = None) -> Tuple[str, str]:
    """Lấy lại kênh: dời `kho\\<MÃ>` về `<cha>\\<MÃ>` (da_doi | o_thuong | khong_co | hoan | da_co)."""
    nguon = os.path.join(thu_muc_kho(goc), ma)
    dich = thu_muc_chrome_thuong(goc, ma)
    if not os.path.isdir(nguon):
        return ("o_thuong", "Chrome đã ở " + dich) if os.path.isdir(dich) else ("khong_co", "không thấy Chrome trong kho")
    ly = (ban or chrome_ban)(goc, ma, nguon)
    if ly:
        return "hoan", ly + " — chưa dời Chrome về, chạy lại `lay-lai` sau"
    return _doi(nguon, dich)


def chrome_cho_cat(goc: str) -> List[str]:
    """Kênh đã trả kho mà Chrome còn nằm đường thường (chưa dời được vào kho)."""
    return [d["ma"] for d in danh_sach(goc)
            if os.path.isdir(thu_muc_chrome_thuong(goc, d["ma"])) and not os.path.exists(os.path.join(thu_muc_kho(goc), d["ma"]))]


def nhip_chrome(goc: str, ban: Optional[Callable[[str, str, str], str]] = None) -> Dict[str, Tuple[str, str]]:
    """Mỗi nhịp: dời Chrome của kênh trả kho còn ở đường thường (bận thì để nhịp sau). {mã: (trạng thái, ghi chú)}."""
    return {ma: cat_chrome(goc, ma, ban) for ma in chrome_cho_cat(goc)}


# ── trả / lấy lại ───────────────────────────────────────────────────────────
def tra(goc: str, ma: str, thay: str = "", bay_gio: _dt.datetime = None,
        ban: Optional[Callable[[str, str, str], str]] = None) -> Dict[str, Any]:
    from . import vm_cai_dat  # noqa: PLC0415
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415

    y = _kenh_yaml(goc, ma)
    if not y:
        raise RuntimeError("không thấy CHANNEL/{0}/kenh.yaml".format(ma))
    duong_luu = os.path.join(goc, "CHANNEL", ma, TEP_LUU)
    if not os.path.isfile(duong_luu):     # chỉ cất lần ĐẦU — trả kho lần 2 không đè giá trị gốc bằng false
        may = vm_cai_dat.doc(goc, ma)
        luu = {"kenh": {k: y.get(k) for k in KHOA_KENH}, "may_ao": {k: may.get(k) for k in KHOA_MAY_AO}}
        with open(duong_luu, "w", encoding="utf-8") as f:
            json.dump(luu, f, ensure_ascii=False, indent=1)
    ngay = str(y.get("tra_kho") or "").strip() or (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d")
    ghi_cai_kenh(goc, ma, tu_chay=False, thiet_lap_kenh=False, nuoi_trang_chu=False, tra_kho=ngay,
                 thay_boi=thay or str(y.get("thay_boi") or ""))
    vm_cai_dat.luu(goc, ma, **{k: False for k in KHOA_MAY_AO})
    tt, gc = cat_chrome(goc, ma, ban)
    return {"ma": ma, "tra_kho": ngay, "thay_boi": thay, "chrome": tt, "chrome_ghi_chu": gc}


def lay_lai(goc: str, ma: str, ban: Optional[Callable[[str, str, str], str]] = None) -> Dict[str, Any]:
    from . import vm_cai_dat  # noqa: PLC0415
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415

    duong_luu = os.path.join(goc, "CHANNEL", ma, TEP_LUU)
    with open(duong_luu, "r", encoding="utf-8") as f:
        luu = json.load(f)
    tt, gc = dua_chrome_ve(goc, ma, ban)
    ghi_cai_kenh(goc, ma, tra_kho="", thay_boi="",
                 **{k: bool(v) for k, v in (luu.get("kenh") or {}).items() if v is not None})
    vm_cai_dat.luu(goc, ma, **{k: v for k, v in (luu.get("may_ao") or {}).items() if v is not None})
    os.replace(duong_luu, duong_luu + ".da-lay-lai")
    return {"ma": ma, "lay_lai": True, "chrome": tt, "chrome_ghi_chu": gc}


def danh_sach(goc: str) -> List[Dict[str, str]]:
    d = os.path.join(goc, "CHANNEL")
    ra = []
    for m in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if m.startswith(("_", ".")) or not os.path.isfile(os.path.join(d, m, "kenh.yaml")):
            continue
        y = _kenh_yaml(goc, m)
        if str(y.get("tra_kho") or "").strip():
            ra.append({"ma": m, "tra_kho": str(y.get("tra_kho")), "thay_boi": str(y.get("thay_boi") or ""),
                       "chrome": tim_chrome(goc, m)})
    return ra


def main(argv: List[str] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m core.tra_kho")
    sp = p.add_subparsers(dest="lenh", required=True)
    a = sp.add_parser("tra")
    a.add_argument("ma")
    a.add_argument("--thay", default="")
    b = sp.add_parser("lay-lai")
    b.add_argument("ma")
    sp.add_parser("ds")
    sp.add_parser("nhip")
    ns = p.parse_args(argv)
    if ns.lenh == "tra":
        print(json.dumps(tra(GOC, ns.ma, ns.thay), ensure_ascii=False))
    elif ns.lenh == "lay-lai":
        print(json.dumps(lay_lai(GOC, ns.ma), ensure_ascii=False))
    elif ns.lenh == "nhip":
        print(json.dumps(nhip_chrome(GOC), ensure_ascii=False))
    else:
        print(json.dumps(danh_sach(GOC), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
