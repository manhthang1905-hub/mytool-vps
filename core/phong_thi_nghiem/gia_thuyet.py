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
    # 12/10/2026 — hạt giống THÊM SAU (sổ đã có 7 mục: mã chỉ nối mục còn thiếu, không đổi thứ tự mục cũ).
    {"id": "H-RADAR", "phien_ban": 1, "loai": LOAI_TRONG_SO, "trang_thai": BONG,
     "mo_ta": "Radar thị trường (12/10): video đối thủ đang NỔ ở tuổi thật (≥ 3× kỳ vọng theo đường cong của chính "
              "kênh nguồn, ≤ 7 ngày) mà radar GÁN cho chính kênh này (chủ vùng / AI hợp tệp / nhãn tuyến); ưu tiên "
              "≤ 72h, dài 12–21 phút. Ca cực mạnh được máy ép chọn (ghi công chính xác)",
     "tham_so": {"cong": [{"f": "radar_muc", "op": ">=", "v": 1}, {"f": "radar_cua_minh", "op": "co"}],
                 "trong_so": {"log_radar_boi": 1.0, "radar_tre": 0.5, "dai_tot": 0.5, "log_view": 0.2,
                              "co_trang_chu": 0.2, "co_pool": 0.2},
                 "tran": {"log_radar_boi": 5.3}}},
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


def doi_trang_thai(goc: str, doi: Dict[str, Tuple[str, str]]) -> int:
    """Sửa `trang_thai` của các mục trong sổ (luật quyết: loại chung / tốt nghiệp) — chỉ trường trạng thái + dấu vết
    (`doi_luc`, `ly_do_doi`), giữ nguyên mọi thứ khác. Trả số mục đã đổi."""
    p = duong(goc)
    du = c.doc_json(p, None)
    if not isinstance(du, dict) or not isinstance(du.get("gia_thuyet"), list):
        return 0
    so = 0
    for g in du["gia_thuyet"]:
        if not isinstance(g, dict) or g.get("id") not in doi:
            continue
        tt, ly = doi[g["id"]]
        if tt not in (BONG, SONG, LOAI) or g.get("trang_thai") == tt:
            continue
        g["trang_thai"], g["doi_luc"], g["ly_do_doi"] = tt, c.luc_iso(), str(ly or "")[:300]
        so += 1
    if so:
        du["luc"] = c.luc_iso()
        c.ghi_json(p, du)
    return so


# ── giả thuyết MỚI dạng dữ liệu (bộ não đề xuất — `python -m core.nao gia-thuyet-moi`) ──────────────────────────

#: Đặc trưng DẪN XUẤT (`dac_trung.mo_rong`) — cùng các cột số của ảnh chụp kho là những gì một giả thuyết mới được dùng.
DAN_XUAT = ("log_vuot", "log_view", "dai_tot", "dai_tam", "tang_duong", "log_pool_xem", "log_pool_cum_xem",
            "log_pool_thang_xem", "log_pool_kenh_xem", "log_thi_truong", "log_tc", "vung_chua_chu", "co_doi_thu",
            "co_pool", "co_trang_chu", "tre_3n", "tre_7n", "tre_30n", "log_radar_boi", "radar_tre")
OP_HOP_LE = (">=", ">", "<=", "<", "==", "!=", "co", "khong", "trong", "ngoai", "hoac")
TOI_DA_DE_XUAT_TUAN = 2
TOI_DA_BONG_CUA_NAO = 6
TOI_DA_TRONG_SO = 12
TRAN_HE_SO = 10.0


def dac_trung_hop_le() -> Tuple[List[str], List[str]]:
    """`(đặc trưng SỐ dùng được làm trọng số/cổng, đặc trưng CHỮ chỉ dùng làm cổng)`."""
    from .dac_trung import COT_CHU, COT_KHO  # noqa: PLC0415

    so_ = [x for x in COT_KHO if x not in COT_CHU and x != "luc"] + list(DAN_XUAT)
    chu = [x for x in COT_KHO if x in COT_CHU and x not in ("ma", "tieu_de")]
    return so_, chu


def phan_tich_cap(chuoi: str) -> Dict[str, float]:
    ra: Dict[str, float] = {}
    for manh in str(chuoi or "").replace(";", ",").split(","):
        manh = manh.strip()
        if not manh:
            continue
        ten, _, w = manh.partition(":")
        try:
            ra[ten.strip()] = float(w)
        except ValueError:
            raise ValueError("“{0}” phải dạng đặc_trưng:hệ_số".format(manh)) from None
    return ra


def phan_tich_cong(chuoi: str) -> List[Dict[str, Any]]:
    """`"vuot>=3; dai_phut<=21; trong_pool co; vung_cua_anh_em khong"` → danh sách điều kiện (xem đầu tệp)."""
    import re  # noqa: PLC0415

    ra: List[Dict[str, Any]] = []
    for manh in str(chuoi or "").split(";"):
        manh = manh.strip()
        if not manh:
            continue
        m = re.fullmatch(r"([a-z0-9_]+)\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?)", manh)
        if m:
            ra.append({"f": m.group(1), "op": m.group(2), "v": float(m.group(3))})
            continue
        m = re.fullmatch(r"([a-z0-9_]+)\s+(co|khong)", manh)
        if m:
            ra.append({"f": m.group(1), "op": m.group(2)})
            continue
        raise ValueError("điều kiện “{0}” không hiểu (dạng: f>=số | f<=số | f co | f khong; cách nhau bằng ;)".format(
            manh))
    return ra


def kiem_tham_so(ts: Dict[str, Any]) -> List[str]:
    """Lỗi của bộ tham số `trong_so` (rỗng = hợp lệ): chỉ đặc trưng có trong kho, op trong danh sách trắng, hệ số
    hữu hạn ≤ `TRAN_HE_SO`, ≤ `TOI_DA_TRONG_SO` trọng số, có ít nhất một trọng số."""
    import math  # noqa: PLC0415

    so_, chu = dac_trung_hop_le()
    loi: List[str] = []
    w = ts.get("trong_so")
    if not isinstance(w, dict) or not w:
        loi.append("cần ít nhất một trọng số (--trong-so f:hệ_số)")
        w = {}
    if len(w) > TOI_DA_TRONG_SO:
        loi.append("tối đa {0} trọng số".format(TOI_DA_TRONG_SO))
    for f, x in w.items():
        if f not in so_:
            loi.append("đặc trưng “{0}” không có trong kho (dùng được: {1})".format(f, ", ".join(so_)))
        try:
            xf = float(x)
            if not math.isfinite(xf) or abs(xf) > TRAN_HE_SO:
                loi.append("hệ số {0}={1} ngoài [−{2:g}, {2:g}]".format(f, x, TRAN_HE_SO))
        except (TypeError, ValueError):
            loi.append("hệ số {0} không phải số".format(f))

    def kiem_dk(dk: Any) -> None:
        if not isinstance(dk, dict) or dk.get("op") not in OP_HOP_LE:
            loi.append("điều kiện hỏng: {0}".format(dk))
            return
        if dk["op"] == "hoac":
            for x in dk.get("v") or []:
                kiem_dk(x)
            return
        if dk.get("f") not in so_ + chu:
            loi.append("cổng dùng đặc trưng lạ “{0}”".format(dk.get("f")))
    for dk in ts.get("cong") or []:
        kiem_dk(dk)
    for f, t in (ts.get("tran") or {}).items():
        if f not in w:
            loi.append("trần cho “{0}” nhưng không có trọng số ấy".format(f))
        if _so(t) is None:
            loi.append("trần {0} không phải số".format(f))
    return loi


def de_xuat(goc: str, ma: str, *, mo_ta: str, trong_so: Dict[str, float], cong: Optional[List[Dict[str, Any]]] = None,
            tran: Optional[Dict[str, float]] = None, ly_do: str = "", tac_gia: str = "nao",
            kenh_thu: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Thêm MỘT giả thuyết mới (loại `trong_so`, trạng thái `bong` — chỉ chạy bóng; khe sản xuất chỉ mở khi luật
    `luat.du_thu` cho: ≥ 7 ngày bóng + qua sàn tầng 1). Ném `ValueError` kèm lý do khi không hợp lệ / vượt hạn mức.
    Thử chấm trên ảnh chụp kho gần nhất của các kênh: 0 ứng viên qua cổng ở MỌI kênh → từ chối (cổng chết)."""
    import re  # noqa: PLC0415

    ma = str(ma or "").strip().upper()
    if not re.fullmatch(r"H-[A-Z0-9][A-Z0-9-]{1,23}", ma):
        raise ValueError("--id phải dạng H-TEN (chữ HOA/số/gạch, 3–26 ký tự), vd H-POOL-NGAN")
    if len(str(ly_do or "").strip()) < 20:
        raise ValueError("--ly-do phải có lý lẽ + số (≥ 20 ký tự): vì sao bộ chấm này nhặt đúng thứ sẽ thắng")
    if len(str(mo_ta or "").strip()) < 10:
        raise ValueError("--mo-ta quá ngắn (một câu nói giả thuyết là gì)")
    ts = {"cong": list(cong or []), "trong_so": dict(trong_so or {}), "tran": dict(tran or {})}
    loi = kiem_tham_so(ts)
    if loi:
        raise ValueError("; ".join(loi[:6]))
    reg, _k = nap(goc)
    du = c.doc_json(duong(goc), None)
    if not isinstance(du, dict) or not isinstance(du.get("gia_thuyet"), list):
        raise ValueError("không đọc được sổ giả thuyết")
    if any(str(g.get("id") or "").upper() == ma for g in du["gia_thuyet"] if isinstance(g, dict)):
        raise ValueError("id {0} đã có trong sổ (mỗi id một lần; sửa thì tăng phiên bản bằng tay)".format(ma))
    tuan = c.cong_ngay(c.hom_nay(), -6)
    cua = [g for g in du["gia_thuyet"] if isinstance(g, dict) and g.get("tao_boi") == tac_gia]
    if sum(1 for g in cua if str(g.get("tao_luc") or "") >= tuan) >= TOI_DA_DE_XUAT_TUAN:
        raise ValueError("đã đề xuất {0} giả thuyết trong 7 ngày (tối đa {0}) — chờ bảng có số".format(
            TOI_DA_DE_XUAT_TUAN))
    if sum(1 for g in cua if g.get("trang_thai") == BONG) >= TOI_DA_BONG_CUA_NAO:
        raise ValueError("đang có {0} giả thuyết của {1} chạy bóng (tối đa {0}) — đợi luật loại/tốt nghiệp".format(
            TOI_DA_BONG_CUA_NAO, tac_gia))
    moi = {"id": ma, "phien_ban": 1, "loai": LOAI_TRONG_SO, "trang_thai": BONG, "mo_ta": str(mo_ta).strip()[:300],
           "tham_so": ts, "tao_luc": c.hom_nay(), "tao_boi": tac_gia, "ly_do": str(ly_do).strip()[:600]}
    thu = _thu_tren_kho(goc, moi, kenh_thu)
    if thu and not any(x["n_du"] for x in thu):
        raise ValueError("cổng quá chặt: 0 ứng viên qua cổng trên ảnh chụp kho gần nhất của {0} kênh".format(len(thu)))
    du["gia_thuyet"].append(moi)
    du["luc"] = c.luc_iso()
    c.ghi_json(duong(goc), du)
    try:
        from . import luat  # noqa: PLC0415

        luat.ghi_quyet_dinh(goc, [{"luc": c.luc_iso(), "ngay": c.hom_nay(), "loai": "de_xuat_moi",
                                   "ten": luat.TEN_LOAI["de_xuat_moi"], "kenh": "", "gt": ma, "pb": 1,
                                   "tac_gia": tac_gia, "ly_do": moi["ly_do"], "tham_so": ts, "thu": thu}])
    except Exception:  # noqa: BLE001
        pass
    return {"gia_thuyet": moi, "thu": thu}


def _thu_tren_kho(goc: str, gt: Dict[str, Any], kenh_ds: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Chấm thử trên ảnh chụp kho GẦN NHẤT của từng kênh phòng thí nghiệm: `[{kenh, ngay, n_du, top: [mã…3]}]`."""
    from . import dac_trung  # noqa: PLC0415

    if kenh_ds is None:
        try:
            from .danh_gia import kenh_phong_thi_nghiem  # noqa: PLC0415

            kenh_ds = kenh_phong_thi_nghiem(goc)
        except Exception:  # noqa: BLE001
            kenh_ds = []
    ra = []
    for k in kenh_ds or []:
        ds = dac_trung.ngay_co_kho(goc, k)
        if not ds:
            continue
        kho = dac_trung.doc_kho(goc, k, ds[-1])
        top, n_du = xep_hang(gt, kho, 3)
        ra.append({"kenh": k, "ngay": ds[-1], "n_du": n_du, "top": [str(d.get("ma") or "") for d, _x in top]})
    return ra


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
