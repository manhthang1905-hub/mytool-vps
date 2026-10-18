"""TRẢ KÊNH VỀ KHO (19/10/2026) — dừng một kênh kém mà KHÔNG xoá gì, lấy lại được.

Chủ: "kênh view ít thì để lại, coi như trả về kho — tao cấp mail mới làm kênh thay".

Trả kho = tắt mọi công tắc chạy của kênh:
- kenh.yaml: `tu_chay`, `thiet_lap_kenh`, `nuoi_trang_chu` → false; ghi `tra_kho: <ngày>`, `thay_boi: <mã mới>`;
- may-ao.json: `tu_dang`, `tu_tra_loi_cmt`, `binh_luan_dom`, `ghim_dom`, `quet_trang_chu_hang_ngay` → false.
Giá trị cũ cất ở `CHANNEL/<k>/tra-kho.json` để `lay_lai` trả đúng như trước.

KHÔNG gỡ kênh khỏi `vm/config.json` `cac_kenh`: cổng DevTools = 9300 + vị trí trong danh sách, gỡ là lệch cổng mọi
kênh sau. Chrome, hồ sơ, tài khoản, dữ liệu, video đã đăng giữ nguyên.

    python -m core.tra_kho tra <MÃ> [--thay <MÃ MỚI>]
    python -m core.tra_kho lay-lai <MÃ>
    python -m core.tra_kho ds
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from typing import Any, Dict, List

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEP_LUU = "tra-kho.json"
KHOA_KENH = ("tu_chay", "thiet_lap_kenh", "nuoi_trang_chu")
KHOA_MAY_AO = ("tu_dang", "tu_tra_loi_cmt", "binh_luan_dom", "ghim_dom", "quet_trang_chu_hang_ngay")


def _kenh_yaml(goc: str, ma: str) -> Dict[str, Any]:
    from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    return doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}


def da_tra_kho(goc: str, ma: str) -> bool:
    """Kênh đã trả kho chưa — mọi bộ máy (kỹ năng tự kích hoạt, mở kênh, anh em cùng tệp) bỏ qua kênh này."""
    try:
        return bool(str(_kenh_yaml(goc, ma).get("tra_kho") or "").strip())
    except Exception:  # noqa: BLE001
        return False


def tra(goc: str, ma: str, thay: str = "", bay_gio: _dt.datetime = None) -> Dict[str, Any]:
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
    ngay = (bay_gio or _dt.datetime.now()).strftime("%Y-%m-%d")
    ghi_cai_kenh(goc, ma, tu_chay=False, thiet_lap_kenh=False, nuoi_trang_chu=False, tra_kho=ngay, thay_boi=thay or "")
    vm_cai_dat.luu(goc, ma, **{k: False for k in KHOA_MAY_AO})
    return {"ma": ma, "tra_kho": ngay, "thay_boi": thay}


def lay_lai(goc: str, ma: str) -> Dict[str, Any]:
    from . import vm_cai_dat  # noqa: PLC0415
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415

    duong_luu = os.path.join(goc, "CHANNEL", ma, TEP_LUU)
    with open(duong_luu, "r", encoding="utf-8") as f:
        luu = json.load(f)
    ghi_cai_kenh(goc, ma, tra_kho="", thay_boi="",
                 **{k: bool(v) for k, v in (luu.get("kenh") or {}).items() if v is not None})
    vm_cai_dat.luu(goc, ma, **{k: v for k, v in (luu.get("may_ao") or {}).items() if v is not None})
    os.replace(duong_luu, duong_luu + ".da-lay-lai")
    return {"ma": ma, "lay_lai": True}


def danh_sach(goc: str) -> List[Dict[str, str]]:
    d = os.path.join(goc, "CHANNEL")
    ra = []
    for m in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if m.startswith(("_", ".")) or not os.path.isfile(os.path.join(d, m, "kenh.yaml")):
            continue
        y = _kenh_yaml(goc, m)
        if str(y.get("tra_kho") or "").strip():
            ra.append({"ma": m, "tra_kho": str(y.get("tra_kho")), "thay_boi": str(y.get("thay_boi") or "")})
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
    ns = p.parse_args(argv)
    if ns.lenh == "tra":
        print(json.dumps(tra(GOC, ns.ma, ns.thay), ensure_ascii=False))
    elif ns.lenh == "lay-lai":
        print(json.dumps(lay_lai(GOC, ns.ma), ensure_ascii=False))
    else:
        print(json.dumps(danh_sach(GOC), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
