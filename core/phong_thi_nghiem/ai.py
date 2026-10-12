"""H-AI — xác suất THẮNG do AI đọc (chỉ chạy bóng, hằng ngày, khi có ví).

Một lượt gọi mỗi kênh mỗi ngày (`toi_da_goi_ngay`), tối đa `so_dong` ứng viên: hợp top-`tu_top` của các giả thuyết
khác (đúng thứ tự xuất hiện) rồi bù theo "gấp". AI đọc: mô tả ngách + tuyến kênh đang đánh, video của kênh kèm nhãn
thước chung (thắng / trung bình / trượt — để tự hiệu chỉnh), và từng ứng viên (tiêu đề, mô tả ngắn, kênh nguồn, view,
gấp trung vị, tuổi, độ dài, cụm, pool, trang chủ). Trả `{số thứ tự: 0–100}`. Kết quả nhớ ở
`CHANNEL/<k>/phong-thi-nghiem/ai-<ngày>.json` — cùng ngày không gọi lại.

Ví chặn / gốc không có `config.json` (bài kiểm) → không gọi, không ghi gì. Lỗi → {} (H-AI vắng mặt hôm ấy).
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import _chung as c


def duong(goc: str, kenh: str, ngay: str) -> str:
    return os.path.join(c.thu_muc_kenh(goc, kenh), "ai-{0}.json".format(ngay))


def chon_dong(kho: Sequence[Dict[str, Any]], top_khac: Dict[str, List[str]], so_dong: int,
              tu_top: int) -> List[Dict[str, Any]]:
    theo_ma = {str(d.get("ma")): d for d in kho}
    ra: List[Dict[str, Any]] = []
    thay = set()
    for _gt, ds in sorted(top_khac.items()):
        for ma in ds[:tu_top]:
            if ma in theo_ma and ma not in thay and len(ra) < so_dong:
                thay.add(ma)
                ra.append(theo_ma[ma])
    for d in sorted(kho, key=lambda x: (-(x.get("vuot") or 0), str(x.get("ma")))):
        if len(ra) >= so_dong:
            break
        if str(d.get("ma")) not in thay and d.get("vuot"):
            thay.add(str(d.get("ma")))
            ra.append(d)
    return ra


def _ngu_canh_kenh(goc: str, kenh: str) -> str:
    phan = []
    try:
        from ..ho_so_ngach import doc_ngach  # noqa: PLC0415

        n = doc_ngach(goc, kenh)
        if getattr(n, "mo_ta_ngach", ""):
            phan.append("Ngách: " + str(n.mo_ta_ngach)[:600])
    except Exception:  # noqa: BLE001
        pass
    try:
        rows = c.doc_csv(os.path.join(c.thu_muc_nghien_cuu(goc, kenh), "tuyen.csv"))
        for r in rows:
            if str(r.get("Trạng thái") or "").strip() == "đang đánh":
                phan.append("Tệp khán giả: {0} — insight: {1}; họ cần: {2}".format(
                    str(r.get("Tên tuyến") or "")[:80], str(r.get("Insight") or "")[:200],
                    str(r.get("Họ cần") or "")[:160]))
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(phan)


def de_bai(goc: str, kenh: str, dong: Sequence[Dict[str, Any]], video_minh: Sequence[Dict[str, Any]]) -> str:
    from .. import thuoc_thang as tt  # noqa: PLC0415

    ten_nhan = {"thang": "THẮNG", "trung_binh": "trung bình", "truot": "trượt"}
    vm = [v for v in video_minh if v.get("nhan") in ten_nhan][-20:]
    ds_vm = "\n".join("- [{0}] {1}".format(ten_nhan[v["nhan"]], str(v.get("tieu_de") or v.get("nguon_td") or "")[:90])
                      for v in vm) or "(kênh chưa có video đã phán)"
    ds = []
    for i, d in enumerate(dong, 1):
        ds.append("{0}. {1}{2} | kênh nguồn: {3} | {4:,.0f} view, gấp {5} trung vị kênh | {6} ngày tuổi | {7} phút | "
                  "cụm: {8} | pool: {9} | trang chủ: {10} ngày{11}".format(
                      i, str(d.get("tieu_de") or "")[:120],
                      " ({0})".format(str(d.get("tieu_de_viet"))[:120]) if d.get("tieu_de_viet") else "",
                      str(d.get("kenh_nguon") or "?")[:40], float(d.get("view") or 0),
                      "{0:.1f}×".format(d["vuot"]) if d.get("vuot") else "?",
                      "{0:.0f}".format(d["tuoi_ngay"]) if d.get("tuoi_ngay") is not None else "?",
                      "{0:.0f}".format(d["dai_phut"]) if d.get("dai_phut") is not None else "?",
                      d.get("cum") or d.get("nhan_y") or "—", "có" if d.get("trong_pool") else "không",
                      int(d.get("tc_ngay") or 0),
                      " | mô tả: " + str(d.get("mo_ta"))[:160].replace("\n", " ") if d.get("mo_ta") else ""))
    return (
        "Bạn là biên tập viên chọn nguồn cho một kênh YouTube làm lại (remake) video đối thủ. Với MỖI ứng viên dưới "
        "đây, ước XÁC SUẤT (0–100) để video kênh này làm lại từ nguồn đó THẮNG theo thước chung của kênh: {mo_ta}.\n\n"
        "BỐI CẢNH KÊNH\n{ngu_canh}\n\nVIDEO CỦA KÊNH (kết quả thật, mới nhất cuối — dùng để hiệu chỉnh):\n{vm}\n\n"
        "ỨNG VIÊN:\n{ds}\n\n"
        "Chấm theo NGHĨA: tệp khán giả của kênh có bấm vì đề tài này không, nguồn có đang được YouTube đẩy không, "
        "giống cái đã thắng của kênh hay cái đã trượt. Phần lớn video không thắng — dùng cả thang, đừng dồn quanh 50.\n"
        "Trả về DUY NHẤT một object JSON đủ mọi số thứ tự: {{\"1\": 35, \"2\": 8, ...}}"
    ).format(mo_ta=tt.MO_TA, ngu_canh=_ngu_canh_kenh(goc, kenh) or "(không có mô tả)", vm=ds_vm, ds="\n".join(ds))


def chay(goc: str, kenh: str, ngay: str, kho: Sequence[Dict[str, Any]], gt: Dict[str, Any],
         top_khac: Dict[str, List[str]], video_minh: Sequence[Dict[str, Any]], *,
         goi: Optional[Callable[..., str]] = None, log: Optional[Callable[[str], None]] = None) -> Dict[str, float]:
    """`{mã: xác suất}` của H-AI cho (kênh, ngày) — xem đầu tệp."""
    p = duong(goc, kenh, ngay)
    cu = c.doc_json(p, None)
    if isinstance(cu, dict) and isinstance(cu.get("ket"), dict):
        return {str(m): float(x) for m, x in cu["ket"].items() if c.so(x) is not None}
    ts = gt.get("tham_so") or {}
    tran = int(ts.get("toi_da_goi_ngay", 1) or 0)
    lan = int((cu or {}).get("lan_thu") or 0) if isinstance(cu, dict) else 0
    if tran <= 0 or lan >= tran + 1:  # trần lượt gọi/ngày (+1 lần thử lại khi lượt trước hỏng)
        return {}
    dong = chon_dong(kho, top_khac, int(ts.get("so_dong", 40) or 40), int(ts.get("tu_top", 15) or 15))
    if not dong:
        return {}
    if goi is None:
        try:
            from .. import cum_y_nghia  # noqa: PLC0415

            goi = cum_y_nghia.goi_vi(goc, log)
        except Exception:  # noqa: BLE001
            goi = None
    if goi is None:
        return {}
    mo_hinh = str(ts.get("mo_hinh") or "claude-fable-5")
    db = de_bai(goc, kenh, dong, video_minh)
    khoa = "phong-thi-nghiem-ai-{0}-{1}-{2}".format(kenh, ngay, hashlib.sha1(db.encode("utf-8")).hexdigest()[:10])
    try:
        from ..goi_van_ban import loc_json  # noqa: PLC0415

        tho = goi(db, mo_hinh=mo_hinh, khoa=khoa, toi_da_token=max(2048, 12 * len(dong) + 600))
        du = loc_json(tho)
        if isinstance(du, list):
            du = {str(i + 1): x for i, x in enumerate(du)}
        if not isinstance(du, dict):
            raise ValueError("AI không trả JSON object")
    except Exception as loi:  # noqa: BLE001
        if log:
            log("  phòng thí nghiệm H-AI hỏng, bỏ qua hôm nay: {0}".format(str(loi)[:120]))
        try:
            c.ghi_json(p, {"ngay": ngay, "luc": c.luc_iso(), "lan_thu": lan + 1, "loi": str(loi)[:200]})
        except OSError:
            pass
        return {}
    ket: Dict[str, float] = {}
    for i, d in enumerate(dong, 1):
        x = c.so(du.get(str(i)))
        if x is not None:
            ket[str(d.get("ma"))] = max(0.0, min(100.0, x))
    if ket:
        try:
            c.ghi_json(p, {"ngay": ngay, "luc": c.luc_iso(), "mo_hinh": mo_hinh, "so_dong": len(dong), "ket": ket})
        except OSError:
            pass
    return ket
