"""Bảng Một nút — MỚI / VƯỢT / BỨT, xếp theo SỨC NỔ của video nguồn.

Thân nhánh Một nút cũ của `tu_chay.ung_vien_xep_hang`, dời nguyên văn:

1. gộp `moi` ∪ `vuot` ∪ `but` của `danh-sach-chon.json` (khử trùng theo link, bảng trước thắng);
2. lọc chung (`nc.loc`) THEO THỨ TỰ QUÉT — trước khi xếp, như bản cũ;
3. xếp: bậc view (≥ `bac_view_manh`) → vượt (trần `tran_vuot`) → tăng/ngày → view;
4. cộng 1 bit anh em trong CÙNG bậc view (`tu_chay._cong_diem_anh_em_an_toan`).

Hai ngưỡng theo cỡ THỊ TRƯỜNG (30/09/2026): đọc `nc.thi_truong` (kenh.yaml > ngach.yaml `thi_truong:`),
mặc định = hằng cũ của thị trường Nhật (`tu_chay.NGUONG_BAC_VIEW` 100.000 view, `TRAN_VUOT` ×25). Ngách
nhỏ hơn (vd tiếng Việt) khai `bac_view_manh: 30000` để "nguồn đang nổ thật" không bị đo bằng cỡ Nhật.
"""

from __future__ import annotations

from typing import Any, Dict, List

TEN = "mot_nut"
MO_TA = "Bảng Một nút — MỚI/VƯỢT/BỨT, xếp theo sức nổ nguồn"
LUI_KHI_RONG = ""
#: Trần "vượt × mức thường của kênh nguồn" — quá trần không còn đáng tin (một kênh cá biệt ăn bảng).
TRAN_VUOT = 25.0


def ap_dung(nc: Any) -> float:
    return 0.1


def cham(nc: Any) -> List[Dict[str, Any]]:
    from .. import doi_thu_kenh as so  # noqa: PLC0415
    from .. import mot_nut  # noqa: PLC0415
    from .. import tu_chay  # noqa: PLC0415 — nhập muộn: tu_chay nhập gói này lúc nạp

    du_lieu = (nc.doc_danh_sach or mot_nut.doc_danh_sach)(nc.goc, nc.ma_kenh) or {}
    theo_link: Dict[str, Dict[str, Any]] = {}
    for nhom in ("moi", "vuot", "but"):
        for d in du_lieu.get(nhom) or []:
            link = str(d.get("link") or "").strip()
            if not link or link in theo_link:
                continue  # đã gặp ở bảng trước (moi ưu tiên hơn vuot, vuot hơn but) — không đè
            theo_link[link] = d

    ung_vien: List[Dict[str, Any]] = []
    for link, d in theo_link.items():
        view, vuot, tang = (float(d.get("view") or 0), float(d.get("vuot") or 0),
                            float(d.get("tang") or 0))
        ly_do = []
        if view:
            ly_do.append("{0:,.0f} view".format(view).replace(",", "."))
        if vuot:
            ly_do.append("vượt ×{0:.1f} mức thường của kênh nguồn".format(vuot))
        if tang:
            ly_do.append("đang lên +{0:,.0f} view/ngày".format(tang).replace(",", "."))
        ung_vien.append({"nguon": "mot_nut", "ma": so.ma_video(link) or "", "link": link,
                         "tieu_de": str(d.get("tieu_de") or ""), "kenh": str(d.get("kenh") or ""),
                         "diem": d.get("diem", 0), "loai": "",
                         # `view` mang theo để `cong_diem_anh_em` xếp lại TRONG TỪNG BẬC view.
                         "view": view, "ly_do": ly_do, "_khoa": (view, vuot, tang)})
    ung_vien = nc.loc(ung_vien)
    if not ung_vien:
        return []
    bac = _so(nc.thi_truong.get("bac_view_manh"), tu_chay.NGUONG_BAC_VIEW)
    tran_vuot = _so(nc.thi_truong.get("tran_vuot"), TRAN_VUOT)

    def _khoa_uu_tien(d: Dict[str, Any]) -> tuple:
        view, vuot, tang = d["_khoa"]
        return (0 if view >= bac else 1, -min(vuot, tran_vuot), -tang, -view)

    ung_vien.sort(key=_khoa_uu_tien)
    for d in ung_vien:
        d.pop("_khoa", None)
    return tu_chay._cong_diem_anh_em_an_toan(nc.goc, nc.ma_kenh, ung_vien, False, nc.ghi,
                                             nguong_bac_view=bac)


def _so(gt: Any, mac_dinh: float) -> float:
    try:
        return float(gt) if gt not in (None, "") and float(gt) > 0 else float(mac_dinh)
    except (TypeError, ValueError):
        return float(mac_dinh)
