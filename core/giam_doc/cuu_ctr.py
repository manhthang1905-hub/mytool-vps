"""Cứu video hỏng cổng CTR ở giờ 52–85 (View = Hiển thị × CTR × Giữ chân — sửa ĐÚNG cổng hỏng).

Điều kiện đề xuất đổi tiêu đề: video tuổi 52–85h, đã phán TRƯỢT, hiển thị ≥ 500, CTR trang chủ (Browse)
< 0,8 × mục tiêu CTR của kênh. Hiển thị thấp mà CTR ổn → lỗi ở cổng HIỂN THỊ (chủ đề / nguồn): không
sửa, chỉ ghi quan sát. Video thắng không bao giờ bị đụng.

Đợt 1: CHỈ GỢI Ý (vào "Việc của bạn"), LLM viết tiêu đề mới từ tiêu đề thắng của kênh, pool đề xuất,
cụm và các bản tiêu đề đã chấm của lượt đó. Đợt 1b: executor Studio tự áp (`vm/may_dang_dom.sua_video_mot`).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .du_lieu import chu_so, ctr_trang_chu, moi_nhat, thu_muc_kenh

TEN = "cuu_ctr"
MO_TA = "Cứu video trượt vì CTR trang chủ thấp ở giờ 52–85 (gợi ý đổi tiêu đề trước, bìa sau)"
NHIP = "ngay"
CHI_SO_CHINH = "ctr_browse_sau_sua"
TUOI = (52.0, 85.0)
HE_SO_CTR = 0.8
HIEN_THI_TOI_THIEU = 500


def _trong_khung(bs: Any) -> List[Dict[str, Any]]:
    return [v for v in bs.video if v.get("tuoi_gio") is not None and TUOI[0] <= v["tuoi_gio"] <= TUOI[1]
            and (moi_nhat(v) or {}).get("tuoi", 0) >= 36]


def ap_dung(bs: Any) -> float:
    """Chạy khi có video trong khung 52–85h đã có bản chụp ≥ 36h và kênh có mục tiêu CTR."""
    return 1.0 if bs.ctr_muc_tieu and _trong_khung(bs) else 0.0


def _chan_doan(bs: Any, v: Dict[str, Any]) -> Dict[str, Any]:
    b = moi_nhat(v) or {}
    tc = ctr_trang_chu(v, 36.0, TUOI[1] + 24)
    imp = b.get("hien_thi") or 0
    ctr = tc["ctr_browse"] if tc else b.get("ctr")
    nhan_ctr = "CTR trang chủ @{0:.0f}h".format(tc["tuoi"]) if tc else "CTR chung (thiếu bảng Browse)"
    muc = bs.ctr_muc_tieu
    dau = "“{0}” ({1}, {2:.0f}h): {3} hiển thị, {4} {5}".format(
        v["tieu_de"][:40], v["id"], b.get("tuoi", 0), chu_so(imp), nhan_ctr, chu_so(ctr, 1, "%"))
    q = {"video_id": v["id"], "n": 1, "tin_cay": "thap", "ctr": ctr, "hien_thi": imp}
    if v.get("thang"):
        return dict(q, cau=dau + " — đang THẮNG, không đụng.", cong="thang")
    if imp < HIEN_THI_TOI_THIEU or ctr is None:
        return dict(q, cau=dau + " — chưa đủ hiển thị để phán cổng CTR.", cong="chua_du")
    if ctr < HE_SO_CTR * muc:
        tr = " và đã phán TRƯỢT" if v.get("ket_luan") == "truot" else " (chưa phán trượt)"
        return dict(q, cau=dau + " < {0:.0%} mục tiêu {1} — HỎNG CỔNG CTR{2}.".format(HE_SO_CTR, chu_so(muc, 1, "%"), tr),
                    cong="ctr")
    if v.get("ket_luan") == "truot":
        vung = "" if bs.n_48h >= 5 else " (lưu ý: ngưỡng thắng {0} tính từ {1} video có số 48h — chưa vững)".format(
            chu_so(bs.nguong_thang_48h), bs.n_48h)
        return dict(q, cau=dau + " ≥ {0:.0%} mục tiêu {1} mà vẫn trượt — lỗi ở cổng HIỂN THỊ (chủ đề/nguồn), "
                    "đổi tiêu đề không cứu được{2}.".format(HE_SO_CTR, chu_so(muc, 1, "%"), vung), cong="hien_thi")
    return dict(q, cau=dau + " — CTR ổn, chưa có kết luận trượt.", cong="on")


def quan_sat(bs: Any) -> List[Dict[str, Any]]:
    """Chẩn đoán cổng của từng video trong khung 52–85h."""
    return [_chan_doan(bs, v) for v in _trong_khung(bs)]


def _pool(bs: Any, vid: str, toi_da: int = 5) -> List[str]:
    """Tiêu đề video mà YouTube đặt cạnh video này (bảng đề xuất), nhiều view nhất trước."""
    try:
        from .. import cong_thuc_v7 as v7  # noqa: PLC0415

        bang = v7.doc_bang_de_xuat(os.path.join(thu_muc_kenh(bs.goc, bs.ma_kenh), "chi-so"), vid) or {}
    except Exception:  # noqa: BLE001
        return []
    dong = sorted(bang.get("dong") or [], key=lambda d: -(d.get("xem") or 0))
    return [str(d.get("tieu_de"))[:60] for d in dong if d.get("tieu_de")][:toi_da]


def de_xuat(bs: Any, qs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mỗi video hỏng cổng CTR đã trượt → một việc Studio "đổi tiêu đề" (LLM viết `noi_dung`)."""
    thang = [v["tieu_de"] for v in bs.video if v.get("thang")][:3]
    ra = []
    for q in qs:
        v = bs.video_theo_id(q["video_id"])
        if q.get("cong") != "ctr" or not v or v.get("ket_luan") != "truot":
            continue
        da_cham = [u.get("tieu_de") for u in v.get("tieu_de_da_cham") or []
                   if u.get("tieu_de") and u.get("tieu_de") != v["tieu_de"]][:5]
        ra.append({"loai": "viec_studio", "viec": "doi_tieu_de", "video_id": v["id"], "tieu_de_cu": v["tieu_de"],
                   "can_noi_dung": True, "chi_goi_y": True,
                   "goi_y": {"tieu_de_da_cham": da_cham, "tieu_de_thang_kenh": thang, "cum": v.get("cum"),
                             "pool": _pool(bs, v["id"])},
                   "gia_thuyet": "Đổi tiêu đề nâng CTR trang chủ từ {0} lên ≥ {1}.".format(
                       chu_so(q["ctr"], 1, "%"), chu_so(HE_SO_CTR * bs.ctr_muc_tieu, 1, "%")),
                   "chi_so": CHI_SO_CHINH, "co_mau": 1, "han_ngay": 7,
                   "nen": {"gia_tri": q["ctr"], "n": 1, "tu_video": [v["id"]]}})
    return ra


def ket_luan(bs: Any, tn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Đo trước/sau cần `lich_su_sua` (đợt 1b) — đợt 1 chưa phán."""
    return None
