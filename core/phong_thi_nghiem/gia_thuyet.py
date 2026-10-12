"""SỔ GIẢ THUYẾT (dữ liệu, không phải mã) + bộ chấm của từng LOẠI giả thuyết.

Sổ: `workspace/phong-thi-nghiem/gia-thuyet.json`

    {"phien_ban": 1, "k": 10, "gia_thuyet": [
      {"id": "H-DOT-BIEN", "mo_ta": "...", "phien_ban": 1,
       "loai": "trong_so" | "dung_san" | "llm",          # kind: trọng số trên đặc trưng | bộ chấm có sẵn | AI đọc
       "tham_so": {...},                                   # params
       "trang_thai": "bong" | "song" | "loai",             # status: chạy bóng | đang sản xuất | đã loại
       "tao_luc": "2026-10-12", "tao_boi": "hat-giong" | "nao" | "chu-du-an"}]}

* `trong_so` — `tham_so = {"cong": [điều kiện…], "trong_so": {đặc trưng: hệ số}, "tran": {đặc trưng: trần}}`.
  Điểm = Σ hệ số × min(giá trị, trần) (thiếu → 0). Điều kiện: `{"f": đặc trưng, "op": ">=", "v": 8}` với op
  `>= > <= < == != co khong trong ngoai`; `{"op": "hoac", "v": [điều kiện…]}` = một trong các điều kiện.
  So sánh với đặc trưng thiếu (None) = trượt (trừ `khong`).
* `dung_san` — `{"cot": "v7_diem", "phu": "-v7_hang"}`: xếp theo một cột điểm mà kho đã tính sẵn từ bộ chấm thật
  (V7, VPH). Dòng không có điểm = bộ chấm ấy đã loại (cổng của nó là một phần giả thuyết).
* `llm` — xác suất thắng do AI đọc (`core/phong_thi_nghiem/ai.py`), chỉ chạy hằng ngày khi có ví, trần lượt gọi/ngày.

Thêm giả thuyết mới = thêm một mục vào sổ (bộ não / chủ dự án), KHÔNG sửa mã. Sửa tham số một giả thuyết đang chạy
thì TĂNG `phien_ban` — nhật ký bóng và bảng xếp hạng tách theo (id, phiên bản). Hạt giống trong mã chỉ được THÊM vào sổ
khi id chưa có; mục đã có trong sổ không bao giờ bị mã ghi đè.
"""

from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import _chung as c

K_MAC_DINH = 10
LOAI_TRONG_SO, LOAI_DUNG_SAN, LOAI_LLM = "trong_so", "dung_san", "llm"
BONG, SONG, LOAI = "bong", "song", "loai"
_TRAN_LOG_VUOT = 3.912  # ln 50 — "gấp" trên 50 lần không thêm điểm (kênh nguồn bé thổi phồng tỉ số)

HAT_GIONG: List[Dict[str, Any]] = [
    {"id": "H-V7", "phien_ban": 1, "loai": LOAI_DUNG_SAN, "trang_thai": SONG,
     "mo_ta": "V7 bản 5: bảng V7 của ngày (Nổ 30 · Khuôn 15 · Cụm 30 · Bảng đề xuất 25 · Đang lên 0, cổng V7), "
              "xếp theo điểm — chọn theo hạng top-10",
     "tham_so": {"cot": "v7_diem", "phu": "-v7_hang"}},
    {"id": "H-VPH", "phien_ban": 1, "loai": LOAI_DUNG_SAN, "trang_thai": SONG,
     "mo_ta": "VPH: đột biến view/giờ so video cùng tuổi của kênh và của ngách (đang dùng ~80% lượt)",
     "tham_so": {"cot": "vph_diem", "phu": "-vph_hang"}},
    {"id": "H-POOL", "phien_ban": 1, "loai": LOAI_TRONG_SO, "trang_thai": BONG,
     "mo_ta": "Công thức TL4: đề tài lấy từ POOL (cụm khán giả của mình đang bấm), nguồn từ sổ đối thủ gấp ≥ 3× "
              "trung vị kênh nguồn, còn đà tăng; ưu tiên dài 12–21 phút",
     "tham_so": {"cong": [{"f": "co_doi_thu", "op": "co"}, {"f": "vuot", "op": ">=", "v": 3},
                          {"f": "tang_duong", "op": "co"},
                          {"op": "hoac", "v": [{"f": "pool_cum_xem", "op": ">", "v": 0},
                                               {"f": "trong_pool", "op": "co"}]}],
                 "trong_so": {"log_pool_cum_xem": 1.0, "trong_pool": 1.5, "log_pool_xem": 0.5,
                              "log_pool_kenh_xem": 0.3, "log_vuot": 1.0, "dai_tot": 0.8},
                 "tran": {"log_vuot": _TRAN_LOG_VUOT}}},
    {"id": "H-DOT-BIEN", "phien_ban": 1, "loai": LOAI_TRONG_SO, "trang_thai": BONG,
     "mo_ta": "Nguồn nổ thật: gấp ≥ 8× trung vị kênh nguồn + dài 12–21 phút (chẩn đoán 12/10: 44% hit vs 14%)",
     "tham_so": {"cong": [{"f": "vuot", "op": ">=", "v": 8}, {"f": "dai_phut", "op": ">=", "v": 12},
                          {"f": "dai_phut", "op": "<=", "v": 21}],
                 "trong_so": {"log_vuot": 1.0, "tang_duong": 0.2}}},
    {"id": "H-NHAN-BAN", "phien_ban": 1, "loai": LOAI_TRONG_SO, "trang_thai": BONG,
     "mo_ta": "Nhân bản cái THẮNG: cùng chủ ngữ hẹp với video thắng của chính kênh (cùng cụm / AI thấy gần / "
              "tiêu đề gần), góc mới (không gần y hệt video đã làm), nguồn gấp ≥ 2×",
     "tham_so": {"cong": [{"f": "co_thang", "op": "co"},
                          {"op": "hoac", "v": [{"f": "thang_cum", "op": "co"},
                                               {"f": "giong_thang_ai", "op": ">=", "v": 60},
                                               {"f": "giong_thang_chu", "op": ">=", "v": 0.2}]},
                          {"f": "giong_minh_chu", "op": "<", "v": 0.6}, {"f": "vuot", "op": ">=", "v": 2}],
                 "trong_so": {"thang_cum": 2.0, "giong_thang_ai": 0.02, "giong_thang_chu": 4.0, "log_vuot": 0.5,
                              "dai_tot": 0.5},
                 "tran": {"log_vuot": _TRAN_LOG_VUOT}}},
    {"id": "H-KHOANG-TRONG", "phien_ban": 1, "loai": LOAI_TRONG_SO, "trang_thai": BONG,
     "mo_ta": "Khoảng trống: vùng đề tài có thị trường lớn (≥ 1 triệu view đối thủ/28 ngày) mà danh mục ta gần như "
              "chưa chiếm (< 0,5%), không thuộc kênh anh em; nguồn gấp ≥ 3×",
     "tham_so": {"cong": [{"f": "vung", "op": "co"}, {"f": "vung_cua_anh_em", "op": "khong"},
                          {"f": "vung_thi_truong", "op": ">=", "v": 1000000},
                          {"op": "hoac", "v": [{"f": "vung_thi_phan", "op": "<", "v": 0.5},
                                               {"f": "vung_thi_phan", "op": "khong"}]},
                          {"f": "vuot", "op": ">=", "v": 3}],
                 "trong_so": {"log_thi_truong": 1.0, "vung_tang": 1.0, "log_vuot": 0.7, "dai_tot": 0.5,
                              "vung_chua_chu": 1.0, "vung_cua_minh": 0.5},
                 "tran": {"log_vuot": _TRAN_LOG_VUOT}}},
    {"id": "H-AI", "phien_ban": 1, "loai": LOAI_LLM, "trang_thai": BONG,
     "mo_ta": "AI đọc: xác suất một bản làm lại trên kênh này THẮNG (thước chung), đọc tiêu đề + mô tả nguồn, số "
              "nguồn, tệp khán giả và video thắng/trượt của kênh. Chỉ chấm nhóm đầu bảng của các giả thuyết khác",
     "tham_so": {"so_dong": 40, "tu_top": 15, "toi_da_goi_ngay": 1, "mo_hinh": "claude-fable-5"}},
]


def duong(goc: str) -> str:
    return os.path.join(c.thu_muc_chung(goc), c.TEP_GIA_THUYET)


def _hop_le(g: Any) -> bool:
    return (isinstance(g, dict) and str(g.get("id") or "").strip()
            and g.get("loai") in (LOAI_TRONG_SO, LOAI_DUNG_SAN, LOAI_LLM)
            and isinstance(g.get("tham_so"), dict))


def nap(goc: str, *, ghi: bool = True) -> Tuple[List[Dict[str, Any]], int]:
    """`(giả thuyết hợp lệ, K)` từ sổ; thiếu sổ / thiếu hạt giống → thêm vào (giữ nguyên mục đã có). Mục hỏng bị bỏ
    qua (không xoá khỏi sổ). `ghi=False`: không đụng đĩa."""
    p = duong(goc)
    du = c.doc_json(p, None)
    doi = False
    if not isinstance(du, dict) or not isinstance(du.get("gia_thuyet"), list):
        du = {"phien_ban": 1, "k": K_MAC_DINH, "gia_thuyet": []}
        doi = True
    co = {str(g.get("id")) for g in du["gia_thuyet"] if isinstance(g, dict)}
    for h in HAT_GIONG:
        if h["id"] not in co:
            m = copy.deepcopy(h)
            m.setdefault("tao_luc", c.hom_nay())
            m.setdefault("tao_boi", "hat-giong")
            du["gia_thuyet"].append(m)
            doi = True
    if doi and ghi:
        try:
            du["luc"] = c.luc_iso()
            c.ghi_json(p, du)
        except OSError:
            pass
    try:
        k = max(1, int(du.get("k") or K_MAC_DINH))
    except (TypeError, ValueError):
        k = K_MAC_DINH
    ra = []
    for g in du["gia_thuyet"]:
        if not _hop_le(g):
            continue
        g = dict(g)
        try:
            g["phien_ban"] = int(g.get("phien_ban") or 1)
        except (TypeError, ValueError):
            g["phien_ban"] = 1
        g["trang_thai"] = g.get("trang_thai") if g.get("trang_thai") in (BONG, SONG, LOAI) else BONG
        ra.append(g)
    return ra, k


# ── chấm ────────────────────────────────────────────────────────────────────

def _so(x: Any) -> Optional[float]:
    if x is None or isinstance(x, bool):
        return None if x is None else float(x)
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def dat(d: Dict[str, Any], dk: Dict[str, Any]) -> bool:
    """Dòng `d` có qua điều kiện `dk` không (xem đầu tệp)."""
    op = str(dk.get("op") or "").strip()
    if op == "hoac":
        return any(dat(d, x) for x in (dk.get("v") or []) if isinstance(x, dict))
    gt = d.get(dk.get("f"))
    if op == "co":
        return bool(gt) and gt != 0
    if op == "khong":
        return (not gt) or gt == 0
    if op in ("trong", "ngoai"):
        ds = dk.get("v") or []
        return (gt in ds) if op == "trong" else (gt not in ds)
    if op in ("==", "!="):
        return (gt == dk.get("v")) if op == "==" else (gt != dk.get("v"))
    x, v = _so(gt), _so(dk.get("v"))
    if x is None or v is None:
        return False
    return {">=": x >= v, ">": x > v, "<=": x <= v, "<": x < v}.get(op, False)


def diem_trong_so(d: Dict[str, Any], ts: Dict[str, Any]) -> Optional[float]:
    """Điểm của một dòng theo giả thuyết `trong_so`; không qua cổng → None."""
    for dk in ts.get("cong") or []:
        if isinstance(dk, dict) and not dat(d, dk):
            return None
    tran = ts.get("tran") or {}
    tong = 0.0
    for f, w in (ts.get("trong_so") or {}).items():
        x = _so(d.get(f))
        if x is None:
            continue
        t = _so(tran.get(f))
        if t is not None:
            x = min(x, t)
        tong += float(w) * x
    return round(tong, 4)


def _khoa_hoa(d: Dict[str, Any], diem: float, phu: float = 0.0) -> Tuple:
    return (-diem, -phu, -(_so(d.get("vuot")) or 0.0), -(_so(d.get("view")) or 0.0), str(d.get("ma") or ""))


def xep_hang(gt: Dict[str, Any], kho: Sequence[Dict[str, Any]], k: int = K_MAC_DINH, *,
             ket_ai: Optional[Dict[str, float]] = None) -> Tuple[List[Tuple[Dict[str, Any], float]], int]:
    """`([(dòng, điểm)] top-k, số dòng đủ điều kiện)` của giả thuyết `gt` trên kho. Tất định (hoà → gấp, view, mã)."""
    ts = gt.get("tham_so") or {}
    ds: List[Tuple[Tuple, Dict[str, Any], float]] = []
    if gt["loai"] == LOAI_TRONG_SO:
        for d in kho:
            x = diem_trong_so(d, ts)
            if x is not None:
                ds.append((_khoa_hoa(d, x), d, x))
    elif gt["loai"] == LOAI_DUNG_SAN:
        cot = str(ts.get("cot") or "")
        phu = str(ts.get("phu") or "")
        dau = -1.0 if phu.startswith("-") else 1.0
        phu = phu.lstrip("-+")
        for d in kho:
            x = _so(d.get(cot))
            if x is None:
                continue
            p = _so(d.get(phu)) if phu else None
            ds.append((_khoa_hoa(d, x, dau * p if p is not None else -1e18), d, x))
    elif gt["loai"] == LOAI_LLM:
        for d in kho:
            x = (ket_ai or {}).get(str(d.get("ma") or ""))
            if x is not None:
                ds.append((_khoa_hoa(d, float(x)), d, float(x)))
    ds.sort(key=lambda t: t[0])
    return [(d, x) for _k, d, x in ds[:max(1, int(k))]], len(ds)
