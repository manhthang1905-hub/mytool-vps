"""ĐO độ ĐỌC ĐƯỢC của ảnh bìa — số đo khách quan, không đoán (09/10/2026).

═══ VÌ SAO CÓ TỆP NÀY ═══

Chủ dự án, 09/10/2026: *"thumb rất kém — kiểu nền và text không tương phản … mọi thứ phải có
logic và tự phát triển chứ sao lại tệ vậy"*. Soi 7 bìa lên lịch 09/10: chữ ĐỎ/VÀNG đặt thẳng lên
nền cam/nâu/kem — viền đen có, nhưng KHỐI chữ hoà vào nền cùng tông ấm; có tấm chữ nhỏ vàng/đỏ trên
nền kem, thu nhỏ cỡ điện thoại là không đọc nổi. Trước tệp này không có chỗ nào ĐO điều đó: màu chữ
do lời nhắc mô hình ảnh (tấm `ve_chu: mo_hinh`) hoặc do khuôn (`bia_theo_khuon.tach_chu_mac_dinh`:
trắng trên, ĐỎ+VÀNG dưới) quyết, bộ vẽ (`bia_theo_khuon._ve_mot_dong`) luôn tô đúng màu đó + viền
đen, không nhìn nền bên dưới.

═══ SỐ ĐO (mỗi DÒNG chữ) ═══

    tuong_phan_nen   WCAG giữa MÀU CHỮ và nền quanh/dưới dòng (bách phân vị 25/75 độ sáng nền,
                     lấy phía XẤU — nền loang thì phần gần màu chữ quyết). Đây là thứ mắt thấy
                     "khối chữ có nổi khỏi nền không" — viền mảnh không cứu được khối chữ chìm.
    tuong_phan       hiệu dụng = max(tuong_phan_nen, WCAG(chữ, viền)) khi viền đủ dày ở cỡ điện thoại
                     (≥ `VIEN_DT_TOI_THIEU` px trên khung 320×180), không thì = tuong_phan_nen.
    cao_pct          chiều cao nét chữ của dòng / chiều cao ảnh (%); `cao_dt_px` = cùng số ở 320×180.
    ban_ron          mật độ cạnh của NỀN dưới dòng (0..1) — nền rối thì chữ cần khung/dải nền.

ĐẠT một dòng khi: tuong_phan ≥ 4,5 (≥ 3,0 nếu dòng rất lớn ≥ `CAO_LON_PCT`), tuong_phan_nen ≥
`NGUONG_NEN` và cao_pct ≥ `CAO_TOI_THIEU_PCT`. Bìa ĐẠT khi mọi dòng đạt. Ngưỡng hiệu chỉnh trên
bìa thật của các kênh (xem `hieu_chinh` / `python -m core.do_bia --hieu-chinh`).

Hai cách đo:
  * CHÍNH XÁC — bộ vẽ chữ của tool (`bia_theo_khuon.ve_chu_len_anh`) biết hộp từng dòng, màu chữ,
    màu/độ dày viền, và có ẢNH NỀN TRƯỚC KHI VẼ CHỮ → `cham_dong` đo trên nền thật. Kết quả ghi
    cạnh ảnh (`<tên>.do-bia.json`).
  * MÙ — ảnh đã ghép (chữ do mô hình ảnh vẽ, hoặc bìa cũ): `tim_dong_chu` dò dòng chữ theo vành
    viền (chữ bìa kiểu này luôn có viền tối/sáng bao quanh), ước màu chữ/viền/nền rồi đo y như trên.
    Không dò ra chữ → `tin_cay=False` (không kết luận).

Ngoài đo còn: `chon_kieu_dong` (chọn màu chữ/viền/khung theo nền ĐO được — bộ vẽ dùng),
`ve_lai_tu_anh_ghep` (xoá chữ cũ bằng nội suy nền + vẽ lại chữ theo kiểu thích nghi, KHÔNG gọi AI),
và CLI:

    python -m core.do_bia --kiem <kênh> <mã gói>
    python -m core.do_bia --lam-lai <kênh> <mã gói> [--thu [--ra <thư mục>]]
    python -m core.do_bia --hieu-chinh [--n 40]
    python -m core.do_bia --xep-doi-bia <kênh> <mã gói> --anh <tệp>   # xếp việc đổi bìa cho máy DOM
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "NGUONG_TUONG_PHAN", "NGUONG_TUONG_PHAN_LON", "NGUONG_NEN", "CAO_TOI_THIEU_PCT", "CAO_LON_PCT",
    "do_sang", "ti_le_tuong_phan", "cham_dong", "tong_hop", "cham_anh", "cham_tep", "tim_dong_chu",
    "chon_kieu_dong", "ve_lai_tu_anh_ghep", "nhom_doc_duoc", "duong_bao_cao", "ghi_bao_cao",
    "doc_bao_cao",
]

#: WCAG: chữ thường ≥ 4,5:1; chữ RẤT LỚN ≥ 3:1.
NGUONG_TUONG_PHAN = 4.5
NGUONG_TUONG_PHAN_LON = 3.0
#: Màu chữ (không kể viền) ↔ nền dưới ngần này thì ghi CẢNH BÁO (không tự nó làm trượt: chữ trắng viền
#: đen dày trên nền kem vẫn đọc tốt — viền↔nền gánh). Bộ chọn kiểu ưu tiên kiểu vượt cả ngưỡng này.
NGUONG_NEN = 2.0
#: Dòng LỚN NHẤT của bìa phải cao ít nhất ngần này % khung — bìa không có "dòng chính" đủ lớn (chữ dồn
#: một góc, hai dòng nhỏ đều nhau) thu về điện thoại là mất. Bộ vẽ đặt tầng chính ≥ 25% (khối 1–2 dòng).
CAO_CHINH_TOI_THIEU_PCT = 14.0
#: Dòng cao ≥ ngần này % khung là "chữ rất lớn" (ngưỡng 3:1).
CAO_LON_PCT = 18.0
#: Dòng thấp hơn ngần này % khung thì thu về cỡ điện thoại (320×180) chỉ còn < ~13 px — không đọc nổi.
CAO_TOI_THIEU_PCT = 7.0
#: Viền mỏng hơn ngần này px ở khung 320×180 thì coi như không có viền (bị nhoè lẫn vào nền khi thu nhỏ).
VIEN_DT_TOI_THIEU = 1.2
#: Nền rối: mật độ cạnh vượt ngưỡng này mà dòng không có khung/dải nền → ghi lý do (trừ điểm).
NGUONG_BAN_RON = 0.22
KHUNG_DT = (320, 180)
#: Khung làm việc của bộ dò mù (đủ nét cho chữ bìa, nhanh trên VPS).
_KHUNG_DO = (640, 360)

#: Màu thay thế khi màu gốc không đạt (đã đo: trắng/vàng trên nền tối, xanh đen/đỏ đậm trên nền sáng).
TRANG = (255, 255, 255)
VANG = (255, 214, 0)
XANH_DEN = (12, 20, 48)
DO_DAM = (176, 0, 24)
DEN = (10, 8, 14)


# ── Màu & độ sáng ─────────────────────────────────────────────────────────────


def _tuyen_tinh(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def do_sang(rgb: Sequence[float]) -> float:
    """Độ sáng tương đối WCAG (0 = đen, 1 = trắng) của màu sRGB 0..255."""
    r, g, b = (float(x) for x in rgb[:3])
    return 0.2126 * _tuyen_tinh(r) + 0.7152 * _tuyen_tinh(g) + 0.0722 * _tuyen_tinh(b)


def ti_le_tuong_phan(l1: float, l2: float) -> float:
    """Tỉ lệ tương phản WCAG giữa hai độ sáng tương đối (1..21)."""
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def _np():
    import numpy as np  # noqa: PLC0415
    return np


_BANG_TT = None


def _mang_do_sang(arr):
    """Ảnh uint8 HxWx3 → mảng độ sáng tương đối float32 HxW."""
    global _BANG_TT
    np = _np()
    if _BANG_TT is None:
        _BANG_TT = np.array([_tuyen_tinh(i) for i in range(256)], dtype=np.float32)
    a = arr.astype(np.intp)
    return (0.2126 * _BANG_TT[a[..., 0]] + 0.7152 * _BANG_TT[a[..., 1]] + 0.0722 * _BANG_TT[a[..., 2]]).astype(
        np.float32)


def _mat_do_canh(xam):
    """Độ lớn gradient (0..~1) của ảnh xám float 0..1 — sai phân trung tâm, không cần scipy."""
    np = _np()
    gx = np.zeros_like(xam)
    gy = np.zeros_like(xam)
    gx[:, 1:-1] = xam[:, 2:] - xam[:, :-2]
    gy[1:-1, :] = xam[2:, :] - xam[:-2, :]
    return np.sqrt(gx * gx + gy * gy)


def _gian(mask, r: int):
    """Giãn mặt nạ bool theo ô vuông bán kính r (cộng dồn 2 chiều, O(HW))."""
    np = _np()
    if r <= 0:
        return mask.copy()
    m = mask.astype(np.int32)
    H, W = m.shape
    c = np.zeros((H + 1, W + 1), dtype=np.int32)
    c[1:, 1:] = m.cumsum(0).cumsum(1)
    y0 = np.clip(np.arange(H) - r, 0, H)
    y1 = np.clip(np.arange(H) + r + 1, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W)
    x1 = np.clip(np.arange(W) + r + 1, 0, W)
    s = c[y1][:, x1] - c[y0][:, x1] - c[y1][:, x0] + c[y0][:, x0]
    return s > 0


def _phan_vi(v, q: float, mac_dinh: float = 0.0) -> float:
    np = _np()
    return float(np.percentile(v, q)) if getattr(v, "size", 0) else mac_dinh


# ── Đo một dòng ───────────────────────────────────────────────────────────────


def cham_dong(*, l_chu: Sequence[float], l_vien: Optional[float], vien_px: float, cao_px: float,
              H: int, l_nen, ban_ron: float = 0.0, co_khung: bool = False,
              hop: Optional[Sequence[float]] = None, ten: str = "") -> Dict[str, Any]:
    """Chấm MỘT dòng từ các số đã đo.

    `l_chu`: độ sáng của (các) màu chữ trong dòng — dòng nhiều màu thì chấm màu XẤU nhất; `l_vien`:
    độ sáng màu viền (None = không viền); `vien_px`/`cao_px`: độ dày viền / chiều cao nét chữ (px ở
    ảnh cao `H`); `l_nen`: mảng độ sáng các điểm NỀN dưới/quanh dòng (đã gồm khung nền nếu có)."""
    np = _np()
    l_nen = np.asarray(l_nen, dtype=np.float32).ravel()
    if l_nen.size == 0:
        l_nen = np.array([0.5], dtype=np.float32)
    p25, p50, p75 = (_phan_vi(l_nen, q) for q in (25, 50, 75))
    he = KHUNG_DT[1] / float(max(1, H))
    vien_dt = vien_px * he
    cao_pct = 100.0 * cao_px / float(max(1, H))
    lon = cao_pct >= CAO_LON_PCT
    nguong = NGUONG_TUONG_PHAN_LON if lon else NGUONG_TUONG_PHAN
    tp_nen_ds, tp_ds = [], []
    co_vien = l_vien is not None and vien_dt >= VIEN_DT_TOI_THIEU
    # Viền tách khỏi nền ở phía XẤU của nền (viền tối ↔ phần nền tối nhất p25, và ngược lại).
    tp_vien_nen = 0.0
    if co_vien:
        tp_vien_nen = ti_le_tuong_phan(l_vien, p25 if l_vien < p50 else p75)
    for lc in (l_chu or [1.0]):
        # Phía XẤU của nền: chữ sáng → phần nền SÁNG nhất (p75) quyết; chữ tối → phần nền TỐI nhất (p25).
        lb = p75 if lc >= p50 else p25
        tn = ti_le_tuong_phan(lc, lb)
        # Đường viền chỉ cứu được khi CẢ HAI phía tách: chữ↔viền (nét chữ) VÀ viền↔nền (khối chữ nổi
        # khỏi nền). Đỏ viền đen trên gỗ nâu: chữ↔viền 4,7 nhưng viền↔nền ~2 → khối chữ chìm.
        tv = min(ti_le_tuong_phan(lc, l_vien), tp_vien_nen) if co_vien else 0.0
        tp_nen_ds.append(tn)
        tp_ds.append(max(tn, tv))
    tp_nen, tp = min(tp_nen_ds), min(tp_ds)
    ly_do: List[str] = []
    if tp < nguong:
        ly_do.append("tương phản {0:.1f}:1 < {1:.1f}:1 (màu chữ↔nền {2:.1f}{3})".format(
            tp, nguong, tp_nen, ", viền↔nền {0:.1f}".format(tp_vien_nen) if co_vien else ", viền mỏng/không có"))
    if cao_pct < CAO_TOI_THIEU_PCT:
        ly_do.append("chữ nhỏ {0:.1f}% khung (~{1:.0f}px trên điện thoại) < {2:.0f}%".format(
            cao_pct, cao_px * he, CAO_TOI_THIEU_PCT))
    canh_bao = []
    if tp_nen < NGUONG_NEN:
        canh_bao.append("màu chữ gần độ sáng nền ({0:.1f}:1) — chỉ viền gánh".format(tp_nen))
    if ban_ron > NGUONG_BAN_RON and not co_khung:
        canh_bao.append("nền rối {0:.2f} dưới chữ, không có khung/dải nền".format(ban_ron))
    return {
        "ten": ten, "hop": [int(round(x)) for x in hop] if hop else None,
        "tuong_phan": round(tp, 2), "tuong_phan_nen": round(tp_nen, 2), "nguong": nguong,
        "cao_pct": round(cao_pct, 1), "cao_dt_px": round(cao_px * he, 1), "vien_dt_px": round(vien_dt, 2),
        "ban_ron": round(float(ban_ron), 3), "nen_p50": round(p50, 3), "co_khung": bool(co_khung),
        "dat": not ly_do, "ly_do": ly_do, "canh_bao": canh_bao,
    }


def _diem_dong(d: Dict[str, Any]) -> float:
    """0..100: tương phản (60%) + tách nền (15%) + cỡ chữ (20%) + nền gọn (5%)."""
    import math  # noqa: PLC0415

    def ty(x, a, b):
        return max(0.0, min(1.0, (x - a) / (b - a)))
    f_tp = ty(math.log(max(1.0, d["tuong_phan"])), math.log(1.5), math.log(7.0))
    f_nen = ty(math.log(max(1.0, d["tuong_phan_nen"])), math.log(1.2), math.log(4.5))
    f_cao = ty(d["cao_pct"], 4.0, 20.0)
    f_br = 1.0 if d.get("co_khung") else 1.0 - ty(d["ban_ron"], 0.08, 0.40)
    return 100.0 * (0.60 * f_tp + 0.15 * f_nen + 0.20 * f_cao + 0.05 * f_br)


def nhom_doc_duoc(diem: Optional[float], dat: Optional[bool]) -> str:
    """Nhãn trục học `bia_doc_duoc`: cao | vua | thap ("" = chưa đo)."""
    if diem is None or dat is None:
        return ""
    if not dat:
        return "thap"
    return "cao" if diem >= 75 else "vua"


def tong_hop(cac_dong: Sequence[Dict[str, Any]], *, cach: str = "", tin_cay: bool = True) -> Dict[str, Any]:
    """Gộp các dòng → `{dat, diem, tuong_phan_min, tuong_phan_nen_min, cao_min_pct, ban_ron_max,
    doc_duoc, ly_do, dong}`. Không có dòng nào → `tin_cay=False`, `dat=None` (không kết luận)."""
    ds = list(cac_dong or [])
    if not ds:
        return {"dat": None, "diem": None, "tin_cay": False, "cach": cach, "dong": [], "tuong_phan_min": None,
                "tuong_phan_nen_min": None, "cao_min_pct": None, "ban_ron_max": None, "doc_duoc": "",
                "ly_do": ["không dò ra dòng chữ nào — không kết luận"]}
    diem = min(_diem_dong(d) for d in ds) * 0.7 + sum(_diem_dong(d) for d in ds) / len(ds) * 0.3
    dat = all(d["dat"] for d in ds)
    ly_do = ["dòng {0}: {1}".format(i + 1, "; ".join(d["ly_do"])) for i, d in enumerate(ds) if d["ly_do"]]
    cao_max = max(d["cao_pct"] for d in ds)
    if cao_max < CAO_CHINH_TOI_THIEU_PCT:
        dat = False
        diem *= 0.8
        ly_do.insert(0, "không có dòng chính đủ lớn (dòng lớn nhất {0:.1f}% khung < {1:.0f}%)".format(
            cao_max, CAO_CHINH_TOI_THIEU_PCT))
    ly_do += ["dòng {0}: {1}".format(i + 1, "; ".join(d["canh_bao"])) for i, d in enumerate(ds) if d.get("canh_bao")]
    return {
        "dat": dat if tin_cay else None, "diem": round(diem, 1), "tin_cay": bool(tin_cay), "cach": cach,
        "tuong_phan_min": min(d["tuong_phan"] for d in ds),
        "tuong_phan_nen_min": min(d["tuong_phan_nen"] for d in ds),
        "cao_min_pct": min(d["cao_pct"] for d in ds), "ban_ron_max": max(d["ban_ron"] for d in ds),
        "doc_duoc": nhom_doc_duoc(diem, dat) if tin_cay else "", "ly_do": ly_do, "dong": ds,
    }


# ── Dò MÙ dòng chữ trên ảnh đã ghép ───────────────────────────────────────────


def _khoang_trong_giua(mask_bien, truc: int):
    """Với mỗi điểm KHÔNG thuộc `mask_bien`: độ dài đoạn không-biên chứa nó theo trục (1 = ngang),
    và cờ "hai đầu đều chạm biên". Trả (dai, kin)."""
    np = _np()
    m = mask_bien if truc == 1 else mask_bien.T
    H, W = m.shape
    x = np.broadcast_to(np.arange(W), (H, W))
    trai = np.maximum.accumulate(np.where(m, x, -1), axis=1)
    phai = np.minimum.accumulate(np.where(m, x, W)[:, ::-1], axis=1)[:, ::-1]
    dai = phai - trai - 1
    kin = (trai >= 0) & (phai < W)
    if truc == 0:
        return dai.T, kin.T
    return dai, kin


def _thanh_phan(o, noi: int = 1) -> List[List[Tuple[int, int]]]:
    """Thành phần liên thông (8 hướng, nối qua khe ≤ `noi` ô ngang) của lưới bool nhỏ."""
    H, W = o.shape
    da = [[False] * W for _ in range(H)]
    ra = []
    for y in range(H):
        for x in range(W):
            if not o[y, x] or da[y][x]:
                continue
            ngan = [(y, x)]
            da[y][x] = True
            tp = []
            while ngan:
                cy, cx = ngan.pop()
                tp.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in range(-1 - noi, 2 + noi):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and o[ny, nx] and not da[ny][nx]:
                            da[ny][nx] = True
                            ngan.append((ny, nx))
            ra.append(tp)
    return ra


def _mau_troi(px, toi_da: int = 2) -> List[Tuple[Tuple[int, int, int], float]]:
    """Các màu trội (lượng tử 32 mức/kênh) của tập điểm Nx3 → [(màu trung bình, tỉ phần)]."""
    np = _np()
    n = len(px)
    if n == 0:
        return []
    con = px.astype(np.int32)
    ra = []
    for _ in range(toi_da):
        if len(con) == 0:
            break
        q = con // 32
        ma = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
        k = int(np.argmax(np.bincount(ma, minlength=512)))
        tam = con[ma == k].mean(axis=0)
        # Cụm = mọi điểm cách tâm ≤ 110 (L1) — một màu tô bị nén/đổ bóng trải qua nhiều ô lượng tử.
        gan = np.abs(con - tam).sum(axis=1) <= 110
        phan = gan.sum() / float(n)
        if ra and phan < 0.15:
            break
        ra.append((tuple(int(v) for v in con[gan].mean(axis=0)), float(phan)))
        con = con[~gan]
    return ra


def tim_dong_chu(anh) -> Dict[str, Any]:
    """Dò MÙ các dòng chữ có VIỀN (tối hoặc sáng) trên ảnh đã ghép (PIL.Image).

    Trả `{cuc: "toi"|"sang"|"", dong: [{hop (toạ độ ảnh gốc), mau_chu:[rgb], l_chu:[...], l_vien, vien_px,
    cao_px, l_nen (mảng), ban_ron, mat_na_hop}], mat_na (bool HxW ở khung dò — vùng chữ + viền),
    he (tỉ lệ ảnh gốc / khung dò)}`."""
    np = _np()
    from PIL import Image  # noqa: PLC0415
    W0, H0 = anh.size
    im = anh.convert("RGB").resize(_KHUNG_DO, Image.BOX)
    arr = np.asarray(im)
    L = _mang_do_sang(arr)
    xam = arr.astype(np.float32).mean(axis=2) / 255.0
    canh = _mat_do_canh(xam)
    H, W = L.shape
    he = W0 / float(W)
    tot: Optional[Dict[str, Any]] = None
    mx = arr.max(axis=2).astype(np.int32)
    mn = arr.min(axis=2).astype(np.int32)
    # Màu chữ bìa luôn "THUẦN": trắng, hoặc màu rực (vàng/đỏ/cam/xanh) — khác da/áo/gỗ của tranh.
    ruc = ((mx - mn) >= 0.55 * np.maximum(mx, 1)) & (mx >= 170)
    trang = mn >= 215
    for cuc in ("toi", "sang"):
        bien = L < 0.035 if cuc == "toi" else L > 0.80
        G = 30  # nét chữ dày nhất (px ở khung dò) — chữ bìa cỡ 1/3 khung nét ~20px
        dh, kh = _khoang_trong_giua(bien, 1)
        dv, kv = _khoang_trong_giua(bien, 0)
        trong = (~bien) & ((kh & (dh >= 2) & (dh <= G)) | (kv & (dv >= 2) & (dv <= G)))
        thuan = (ruc | trang) if cuc == "toi" else (ruc | (L < 0.05))
        trong &= thuan
        # Bằng chứng chữ: điểm nét THUẦN sát vành viền, và điểm viền sát nét thuần.
        sat = (trong & _gian(bien, 2)) | (bien & _gian(trong, 2))
        o = 8
        Hc, Wc = H // o, W // o
        sc = sat[:Hc * o, :Wc * o].reshape(Hc, o, Wc, o).mean(axis=(1, 3))
        o_chu = sc >= 0.18
        # Đóng lỗ: giãn 1 ô rồi nối (khe ≤ 2 ô ngang) — nét to bên trong chữ không có viền vẫn là chữ.
        o_chu = _gian(o_chu, 1) & _gian(sc >= 0.06, 0)
        ds = []
        mat_na = np.zeros((H, W), dtype=bool)
        for tp in _thanh_phan(o_chu, noi=2):
            if len(tp) < 10:
                continue
            ys = [p[0] for p in tp]
            xs = [p[1] for p in tp]
            y0, y1, x0, x1 = min(ys) * o, (max(ys) + 1) * o, min(xs) * o, (max(xs) + 1) * o
            if (x1 - x0) < 0.07 * W or (y1 - y0) < 0.04 * H:
                continue
            # Khối chữ thật: phần lớn điểm "trong nét" của khối là MỘT-HAI màu thuần.
            if trong[y0:y1, x0:x1].mean() < 0.06:
                continue
            # Tách KHỐI thành DÒNG theo hồ sơ hàng của điểm trong-nét.
            vung_tr = trong[y0:y1, x0:x1]
            hang = vung_tr.mean(axis=1)
            co = hang > max(0.04, 0.25 * float(hang.max()))
            doan, bat = [], None
            for i, c in enumerate(list(co) + [False]):
                if c and bat is None:
                    bat = i
                elif not c and bat is not None:
                    if i - bat >= 0.012 * H:
                        doan.append((bat, i))
                    bat = None
            # Gộp mảnh thấp sát nhau (bộ 宀 của 守 tách khỏi phần dưới qua một khe vài hàng).
            gop: List[Tuple[int, int]] = []
            for a, b in doan:
                if gop:
                    pa, pb = gop[-1]
                    thap, cao_ = sorted((pb - pa, b - a))
                    if a - pb <= 0.2 * cao_ and thap < 0.45 * cao_ and (b - pa) <= 1.4 * cao_:
                        gop[-1] = (pa, b)
                        continue
                gop.append((a, b))
            for a, b in gop:
                ya, yb = y0 + a, y0 + b
                h = yb - ya
                if h < 0.045 * H:
                    continue
                cot = list(trong[ya:yb, x0:x1].mean(axis=0) > 0.02) + [False]
                # Cắt dòng theo KHE NGANG lớn (≥ 0,8 × cao dòng): chữ và nét tranh cạnh nhau không gộp.
                manh, bat, trong_khe = [], None, 0
                for i, c in enumerate(cot):
                    if c:
                        if bat is None:
                            bat = i
                        trong_khe = 0
                        cuoi = i
                    elif bat is not None:
                        trong_khe += 1
                        if trong_khe >= 0.8 * h or i == len(cot) - 1:
                            manh.append((bat, cuoi + 1))
                            bat, trong_khe = None, 0
                for ma_, mb_ in manh:
                    xa, xb = x0 + ma_, x0 + mb_
                    if xb - xa < max(0.06 * W, 0.6 * h):
                        continue
                    mat_do = float(sat[ya:yb, xa:xb].mean())
                    if mat_do < 0.10:
                        continue
                    d = _do_dong_mu(arr, L, canh, bien, trong, (xa, ya, xb, yb), he, H0)
                    if d is None:
                        continue
                    d["mat_do"] = round(mat_do, 3)
                    bb = bien[ya:yb, xa:xb]
                    d["doi_em"] = round(float((bb[:, 1:] != bb[:, :-1]).sum(axis=1).mean())
                                        / max(1.0, (xb - xa) / float(h)), 2)
                    # Lọc nét TRANH (mặt nạ, mũi tên, mặt nhân vật): chữ bìa có viền đo được, dày đặc
                    # nét (≥ 2,5 lần đổi viền↔nét mỗi "ô chữ" theo hàng) — đo trên 7 bìa 09/10.
                    if (d["vien_px"] * KHUNG_DT[1] / float(H0) < VIEN_DT_TOI_THIEU or d["doi_em"] < 2.5
                            or mat_do < 0.15):
                        continue
                    ds.append(d)
                    # Mặt nạ chữ (để xoá chữ cũ): nét chữ + vành viền (giãn theo độ dày viền đo được) trong
                    # hộp nới rộng — KHÔNG lấy mọi điểm tối (nền tối không phải chữ).
                    r = int(round(d["vien_px"] / he)) + 2
                    mm = max(4, int(0.25 * h)) + r
                    sy0, sy1, sx0, sx1 = max(0, ya - mm), min(H, yb + mm), max(0, xa - mm), min(W, xb + mm)
                    mat_na[sy0:sy1, sx0:sx1] |= _gian(trong[sy0:sy1, sx0:sx1], r)
        ds = [d for d in ds if d is not None]
        diem_cuc = sum((d["hop"][2] - d["hop"][0]) * (d["hop"][3] - d["hop"][1]) for d in ds)
        if ds and (tot is None or diem_cuc > tot["_dien"]):
            tot = {"cuc": cuc, "dong": ds, "mat_na": mat_na, "_dien": diem_cuc}
    if tot is None:
        return {"cuc": "", "dong": [], "mat_na": np.zeros(L.shape, dtype=bool), "he": he}
    tot.pop("_dien", None)
    tot["dong"].sort(key=lambda d: (d["hop"][1], d["hop"][0]))
    tot["he"] = he
    return tot


def _do_dong_mu(arr, L, canh, bien, trong, hop, he: float, H0: int) -> Optional[Dict[str, Any]]:
    np = _np()
    xa, ya, xb, yb = hop
    H, W = L.shape
    tr = trong[ya:yb, xa:xb]
    if tr.sum() < 30:
        return None
    px = arr[ya:yb, xa:xb][tr]
    mau = _mau_troi(px, 2)
    if not mau:
        return None
    # Viền: các đoạn BIÊN chạm điểm trong-nét theo hàng → độ dày trung vị.
    bn = bien[ya:yb, xa:xb]
    dai = []
    for hang_b, hang_t in zip(bn[::2], tr[::2]):
        i, n = 0, len(hang_b)
        while i < n:
            if hang_b[i]:
                j = i
                while j < n and hang_b[j]:
                    j += 1
                cham = (i > 0 and hang_t[i - 1]) or (j < n and hang_t[j])
                if cham and j - i <= 30:
                    dai.append(j - i)
                i = j
            else:
                i += 1
    vien = float(np.median(dai)) if dai else 0.0
    l_vien = float(np.median(L[ya:yb, xa:xb][bn])) if bn.any() else None
    # Nền: hộp nới 35% chiều cao, trừ vùng chữ+viền giãn 3px.
    h = yb - ya
    m = int(0.35 * h) + 3
    y0, y1, x0, x1 = max(0, ya - m), min(H, yb + m), max(0, xa - m), min(W, xb + m)
    chu = _gian((trong | bien)[y0:y1, x0:x1] & _gian(trong[y0:y1, x0:x1], 8), 3)
    nen = ~chu
    l_nen = L[y0:y1, x0:x1][nen]
    ban_ron = float((canh[y0:y1, x0:x1][nen] > 0.12).mean()) if nen.any() else 0.0
    # Chiều cao nét = khoảng hàng có điểm trong-nét (bỏ 3% đuôi hai đầu).
    hang = np.where(tr.any(axis=1))[0]
    cao = float(hang[-1] - hang[0] + 1) if len(hang) else float(h)
    return {"hop": [xa * he, ya * he, xb * he, yb * he], "mau_chu": [m_ for m_, _p in mau],
            "ti_phan_mau": [round(p, 2) for _m, p in mau], "l_chu": [do_sang(m_) for m_, _p in mau],
            "l_vien": l_vien, "vien_px": vien * he, "cao_px": cao * he, "l_nen": l_nen, "ban_ron": ban_ron}


def cham_anh(anh_hoac_duong) -> Dict[str, Any]:
    """Chấm MÙ một ảnh bìa đã ghép (đường dẫn hoặc PIL.Image)."""
    from PIL import Image  # noqa: PLC0415
    anh = Image.open(anh_hoac_duong).convert("RGB") if isinstance(anh_hoac_duong, str) else anh_hoac_duong
    W, H = anh.size
    tim = tim_dong_chu(anh)
    ds = []
    for i, d in enumerate(tim["dong"]):
        ds.append(cham_dong(l_chu=d["l_chu"], l_vien=d["l_vien"], vien_px=d["vien_px"], cao_px=d["cao_px"],
                            H=H, l_nen=d["l_nen"], ban_ron=d["ban_ron"], hop=d["hop"],
                            ten="dòng {0}".format(i + 1)))
        ds[-1]["mau_chu"] = ["#{0:02X}{1:02X}{2:02X}".format(*m) for m in d["mau_chu"]]
        ds[-1]["mat_do"] = d.get("mat_do")
        ds[-1]["doi_em"] = d.get("doi_em")
    return tong_hop(ds, cach="mu", tin_cay=bool(ds))


# ── Báo cáo cạnh ảnh (đo CHÍNH XÁC lúc vẽ) ────────────────────────────────────

_RE_CHON = re.compile(r"^CHON-", re.I)
#: Vân tay ảnh (lưới xám 32×18) — báo cáo chỉ dùng cho ĐÚNG ảnh nó đo: `CHON-*.jpg` xuất lại / chép sang gói
#: vẫn cùng vân tay (lệch < `_LECH_VAN_TAY`), ảnh vẽ lại thì khác → chấm mù lại.
_LECH_VAN_TAY = 6.0


def van_tay(anh_hoac_duong) -> List[int]:
    from PIL import Image, ImageOps  # noqa: PLC0415
    anh = Image.open(anh_hoac_duong) if isinstance(anh_hoac_duong, str) else anh_hoac_duong
    nho = ImageOps.fit(anh.convert("L"), (32, 18), method=Image.BOX)
    return [int(v) for v in _np().asarray(nho).ravel()]


def _lech_van_tay(a: Sequence[int], b: Sequence[int]) -> float:
    if not a or not b or len(a) != len(b):
        return 255.0
    return sum(abs(int(x) - int(y)) for x, y in zip(a, b)) / float(len(a))


def duong_bao_cao(duong_anh: str) -> str:
    """`thumb_002.png` → `thumb_002.do-bia.json`; `CHON-thumb_002.jpg` dùng chung báo cáo của
    `thumb_002` (chọn bìa chỉ xuất lại jpg cùng hình)."""
    thu_muc, ten = os.path.split(duong_anh)
    goc_ten = _RE_CHON.sub("", os.path.splitext(ten)[0])
    return os.path.join(thu_muc, goc_ten + ".do-bia.json")


def ghi_bao_cao(duong_anh: str, bc: Dict[str, Any], anh=None) -> str:
    """Ghi báo cáo đo cạnh ảnh (kèm vân tay của `anh`/tệp `duong_anh`). Trả đường đã ghi ('' nếu hỏng)."""
    duong = duong_bao_cao(duong_anh)
    try:
        vt = van_tay(anh if anh is not None else duong_anh)
        os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(dict(bc, tep=os.path.basename(duong_anh), van_tay=vt,
                           luc=_dt.datetime.now().isoformat(timespec="seconds")), tep, ensure_ascii=False)
        os.replace(tam, duong)
        return duong
    except (OSError, ValueError):
        return ""


def doc_bao_cao(duong_anh: str) -> Optional[Dict[str, Any]]:
    try:
        with open(duong_bao_cao(duong_anh), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return None
    return du if isinstance(du, dict) and du.get("dong") is not None else None


def cham_tep(duong_anh: str) -> Dict[str, Any]:
    """Điểm đọc được của MỘT tệp bìa: báo cáo CHÍNH XÁC lúc vẽ nếu có và đúng ảnh này (vân tay),
    không thì chấm mù."""
    bc = doc_bao_cao(duong_anh)
    if bc is not None:
        try:
            if _lech_van_tay(bc.get("van_tay") or [], van_tay(duong_anh)) < _LECH_VAN_TAY:
                bc = dict(bc)
                bc.pop("van_tay", None)
                return bc
        except (OSError, ValueError):
            pass
    try:
        return cham_anh(duong_anh)
    except Exception as loi:  # noqa: BLE001 — ảnh hỏng: không kết luận
        return tong_hop([], cach="loi:" + str(loi)[:80], tin_cay=False)


def tom_tat(bc: Dict[str, Any]) -> str:
    """Một dòng cho log/hồ sơ: `ĐẠT 82/100 (…)` / `TRƯỢT …: lý do`."""
    if not bc or bc.get("dat") is None:
        return "không đo được ({0})".format("; ".join((bc or {}).get("ly_do") or [])[:120])
    s = "{0} {1:.0f}/100 (tương phản min {2:.1f}:1, chữ min {3:.1f}% khung, đo {4})".format(
        "ĐẠT" if bc["dat"] else "TRƯỢT", bc.get("diem") or 0, bc.get("tuong_phan_min") or 0,
        bc.get("cao_min_pct") or 0, bc.get("cach") or "?")
    if not bc["dat"]:
        s += " — " + "; ".join(bc.get("ly_do") or [])[:300]
    return s


# ── Chọn kiểu chữ theo NỀN đo được (bộ vẽ dùng) ───────────────────────────────


def _la_mau_an_toan(rgb: Sequence[int]) -> bool:
    """Trắng / vàng / xanh đen / đen — các màu chính được phép tô cả dòng."""
    r, g, b = (int(v) for v in rgb[:3])
    if min(r, g, b) >= 225 or max(r, g, b) <= 60:
        return True
    return r >= 220 and g >= 170 and b <= 90  # vàng


_KHUNG_TOI = (16, 12, 24)
_KHUNG_SANG = (250, 247, 240)


def _kieu_theo_nen(p50: float) -> List[Dict[str, Any]]:
    """Thứ tự kiểu thử cho một dòng theo độ sáng nền (trung vị) dưới dòng — luật chủ dự án 09/10:
    nền sáng → chữ TỐI (xanh đen) viền trắng; nền tối → chữ trắng/vàng viền đen; nền vừa/ấm/rối → viền
    đen dày rồi dải/khung nền mờ phía sau, bóng đổ mạnh hơn."""
    toi = {"vien": DEN, "chinh": TRANG, "nhan": (VANG, TRANG)}
    sang = {"vien": TRANG, "chinh": XANH_DEN, "nhan": (DO_DAM, XANH_DEN)}

    def k(ten, nen, he=1.0, bong=200, khung=None):
        return dict(nen, ten=ten, vien_he=he, bong=bong, khung=khung)

    def kh(mau, a, dang="hop"):
        return {"mau": mau, "alpha": a, "dang": dang}
    if p50 >= 0.45:
        return [k("toi_tren_sang", sang, 1.0, 150), k("trang_vien_den", toi, 1.0, 200),
                k("trang_vien_den_day", toi, 1.35, 230),
                k("toi_tren_sang+khung", sang, 1.0, 120, kh(_KHUNG_SANG, 0.72)),
                k("trang+khung_toi", toi, 1.15, 220, kh(_KHUNG_TOI, 0.72)),
                k("trang+khung_toi_dam", toi, 1.15, 220, kh(_KHUNG_TOI, 0.88))]
    if p50 <= 0.12:
        return [k("trang_vien_den", toi, 1.0, 200), k("trang_vien_den_day", toi, 1.35, 230),
                k("trang+khung_toi_nhat", toi, 1.15, 220, kh(_KHUNG_TOI, 0.6)),
                k("trang+khung_toi_dam", toi, 1.15, 220, kh(_KHUNG_TOI, 0.85))]
    return [k("trang_vien_den", toi, 1.0, 200), k("trang_vien_den_day", toi, 1.35, 235),
            k("trang+khung_toi_nhat", toi, 1.15, 225, kh(_KHUNG_TOI, 0.6)),
            k("trang+khung_toi", toi, 1.15, 225, kh(_KHUNG_TOI, 0.72)),
            k("trang+khung_toi_dam", toi, 1.15, 225, kh(_KHUNG_TOI, 0.88)),
            k("toi_tren_sang+khung", sang, 1.0, 120, kh(_KHUNG_SANG, 0.85))]


def _vung(hop, H: int, W: int, nong: float = 0.0):
    x0, y0, x1, y1 = hop
    m = nong * (y1 - y0)
    return (max(0, int(y0 - m)), min(H, int(y1 + m)), max(0, int(x0 - m)), min(W, int(x1 + m)))


def _nen_sau_khung(arr, canh, hop, khung: Optional[Dict[str, Any]]):
    """(độ sáng nền, mật độ cạnh nền) dưới `hop` SAU khi phủ khung/dải nền (nếu có)."""
    np = _np()
    H, W = arr.shape[:2]
    y0, y1, x0, x1 = _vung(hop, H, W, 0.0 if khung else 0.12)
    vung = arr[y0:y1, x0:x1].astype(np.float32)
    c = canh[y0:y1, x0:x1]
    if khung:
        a = float(khung["alpha"])
        vung = vung * (1.0 - a) + np.array(khung["mau"], dtype=np.float32) * a
        c = c * (1.0 - a)
    L = _mang_do_sang(np.clip(vung, 0, 255).astype(np.uint8))
    return L, (float((c > 0.12).mean()) if c.size else 0.0)


def mang_nen(anh):
    """PIL.Image nền → (mảng RGB uint8, mật độ cạnh) — đầu vào của `chon_kieu_dong` / `cham_dong_ve`."""
    np = _np()
    arr = np.asarray(anh.convert("RGB"))
    return arr, _mat_do_canh(arr.astype(np.float32).mean(axis=2) / 255.0)


def cham_dong_ve(arr, canh, hop, mau: Sequence[Sequence[int]], *, vien_mau, vien_px: float, cao_px: float,
                 H: int, khung: Optional[Dict[str, Any]] = None, ten: str = "") -> Dict[str, Any]:
    """Chấm một dòng do TOOL vẽ — đo trên ảnh NỀN trước khi vẽ chữ (`arr`, `canh` = mật độ cạnh)."""
    L, br = _nen_sau_khung(arr, canh, hop, khung)
    d = cham_dong(l_chu=[do_sang(m) for m in mau], l_vien=do_sang(vien_mau) if vien_mau else None,
                  vien_px=vien_px, cao_px=cao_px, H=H, l_nen=L, ban_ron=br,
                  co_khung=bool(khung and khung.get("alpha", 0) >= 0.5), hop=hop, ten=ten)
    d["mau_chu"] = ["#{0:02X}{1:02X}{2:02X}".format(*[int(v) for v in m[:3]]) for m in mau]
    d["vien_mau"] = "#{0:02X}{1:02X}{2:02X}".format(*[int(v) for v in vien_mau[:3]]) if vien_mau else ""
    d["khung"] = dict(khung, mau=list(khung["mau"])) if khung else None
    return d


_KHOI_NEN = {"ten": "khoi_nen", "vien": DEN, "chinh": TRANG, "nhan": (VANG, TRANG), "vien_he": 1.0,
             "bong": 200, "khung": {"mau": (20, 20, 20), "alpha": 0.92, "dang": "hop"}}


def _ap_kieu(arr, canh, hop, mau_doan, kieu: Dict[str, Any], *, vien_px: float, cao_px: float, H: int,
             vong: int, nhan_toi_da: int = 1) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
    """Áp MỘT kiểu cho một dòng: giữ / đổi màu từng đoạn (xem `chon_kieu_dong`) rồi chấm. → (kieu, cham, đạt)."""
    vp = vien_px * kieu["vien_he"]

    def qua(d):
        return d["tuong_phan"] >= d["nguong"] and (vong == 2 or d["tuong_phan_nen"] >= NGUONG_NEN)

    def dat(m):
        return qua(cham_dong_ve(arr, canh, hop, [m], vien_mau=kieu["vien"], vien_px=vp, cao_px=cao_px, H=H,
                                khung=kieu["khung"]))
    mau: List[Tuple[int, int, int]] = []
    nhan = 0
    for m in mau_doan:
        m = tuple(int(v) for v in m[:3])
        an_toan = _la_mau_an_toan(m)
        if (an_toan or nhan < nhan_toi_da) and dat(m):
            nhan += 0 if an_toan else 1
            mau.append(m)
            continue
        if min(m) >= 225:
            mau.append(kieu["chinh"])
        else:
            mau.append(next((c for c in kieu["nhan"] if dat(c)), kieu["chinh"]))
    d = cham_dong_ve(arr, canh, hop, mau, vien_mau=kieu["vien"], vien_px=vp, cao_px=cao_px, H=H,
                     khung=kieu["khung"])
    return dict(kieu, mau=mau), d, qua(d)


def chon_kieu_dong(arr, canh, hop, mau_doan: Sequence[Sequence[int]], *, vien_px: float, cao_px: float,
                   H: int, khoi_nen: bool = False, nhan_toi_da: int = 1) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Chọn kiểu (màu từng đoạn, viền, bóng, khung) cho MỘT dòng theo nền ĐO được dưới dòng.

    Thử lần lượt `_kieu_theo_nen(trung vị độ sáng nền)`. Mỗi kiểu: màu GỐC của một đoạn được giữ nếu
    tự nó đạt VÀ là màu chính an toàn (trắng/vàng/xanh đen) — màu nhấn khác (đỏ của kênh…) chỉ giữ cho
    tối đa `nhan_toi_da` đoạn; đoạn trượt đổi sang màu nhấn ĐẠT của kiểu (vàng/trắng trên nền tối, đỏ
    đậm/xanh đen trên nền sáng); chữ trắng gốc trượt → màu chính của kiểu. Vòng 1 đòi cả tách nền
    `NGUONG_NEN`; không kiểu nào qua thì vòng 2 chỉ đòi tương phản hiệu dụng. Không kiểu nào đạt →
    kiểu tương phản tốt nhất (báo cáo sẽ TRƯỢT). Trả `(kieu, cham)`."""
    ra = chon_kieu_khoi(arr, canh, [{"hop": hop, "mau_doan": mau_doan, "vien_px": vien_px, "cao_px": cao_px,
                                     "khoi_nen": khoi_nen}], H=H, nhan_toi_da=nhan_toi_da)
    return ra[0]


def chon_kieu_khoi(arr, canh, cac_dong: Sequence[Dict[str, Any]], *, H: int,
                   nhan_toi_da: int = 1) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Chọn kiểu cho CẢ KHỐI chữ — ưu tiên MỘT kiểu chung cho mọi dòng (bìa nhìn liền một khối, không
    dòng tối dòng sáng). Thứ tự kiểu theo nền dưới cả khối; kiểu chung đầu tiên mà MỌI dòng đạt được chọn
    (vòng 1 đòi thêm tách nền, vòng 2 không). Không kiểu chung nào đạt → từng dòng tự chọn
    (`_kieu_theo_nen` của nền riêng dòng đó); dòng vẫn trượt giữ kiểu tương phản cao nhất.
    Dòng có `khoi_nen` (khuôn có khối nền) luôn giữ khối đậm. Trả [(kieu, cham)] theo thứ tự `cac_dong`."""
    ds = list(cac_dong)
    if not ds:
        return []
    # 1) Kiểu CHUNG cho cả khối (bỏ qua dòng khối nền — chúng luôn giữ khối đậm).
    thuong = [i for i, d in enumerate(ds) if not d.get("khoi_nen")]
    if thuong:
        x0 = min(ds[i]["hop"][0] for i in thuong)
        y0 = min(ds[i]["hop"][1] for i in thuong)
        x1 = max(ds[i]["hop"][2] for i in thuong)
        y1 = max(ds[i]["hop"][3] for i in thuong)
        L0, _ = _nen_sau_khung(arr, canh, (x0, y0, x1, y1), None)
        for vong in (1, 2):
            for kieu in _kieu_theo_nen(_phan_vi(L0, 50, 0.5)):
                kq = []
                for i in thuong:
                    dd = ds[i]
                    k, d, ok = _ap_kieu(arr, canh, dd["hop"], dd["mau_doan"], kieu, vien_px=dd["vien_px"],
                                        cao_px=dd["cao_px"], H=H, vong=vong, nhan_toi_da=nhan_toi_da)
                    if not ok:
                        break
                    kq.append((k, d))
                else:
                    ra: List[Any] = [None] * len(ds)
                    for i, x in zip(thuong, kq):
                        ra[i] = x
                    for i, dd in enumerate(ds):
                        if ra[i] is None:
                            ra[i] = _mot(arr, canh, dd, H, nhan_toi_da)
                    return ra
    # 2) Từng dòng tự chọn theo nền riêng.
    return [_mot(arr, canh, dd, H, nhan_toi_da) for dd in ds]


def _mot(arr, canh, dd: Dict[str, Any], H: int, nhan_toi_da: int):
    if dd.get("khoi_nen"):
        cac = [_KHOI_NEN]
    else:
        L0, _ = _nen_sau_khung(arr, canh, dd["hop"], None)
        cac = _kieu_theo_nen(_phan_vi(L0, 50, 0.5))
    tot = None
    for vong in (1, 2):
        for kieu in cac:
            k, d, ok = _ap_kieu(arr, canh, dd["hop"], dd["mau_doan"], kieu, vien_px=dd["vien_px"],
                                cao_px=dd["cao_px"], H=H, vong=vong, nhan_toi_da=nhan_toi_da)
            if ok:
                return k, d
            if tot is None or d["tuong_phan"] > tot[0]:
                tot = (d["tuong_phan"], k, d)
    return tot[1], tot[2]


# ── Vẽ lại bìa ĐÃ GHÉP (chữ do mô hình ảnh vẽ / nền gốc đã bị dọn) — không gọi AI ──


def _trung_binh_3(a):
    np = _np()
    p = np.pad(a, ((1, 1), (1, 1)) + ((0, 0),) * (a.ndim - 2), mode="edge")
    s = sum(p[dy:dy + a.shape[0], dx:dx + a.shape[1]] for dy in range(3) for dx in range(3))
    return s / 9.0


def va_nen(arr, hong):
    """Nội suy (kéo–đẩy theo tháp ảnh) màu nền vào các điểm `hong` (bool HxW) của ảnh float HxWx3 —
    xoá chữ cũ mà không cần mô hình: vùng xoá thành mảng màu loang mịn của nền xung quanh."""
    np = _np()
    ok = (~hong).astype(np.float32)
    tang = []
    a, w = arr.astype(np.float32) * ok[..., None], ok
    while True:
        tang.append((a, w))
        H, W = w.shape
        if min(H, W) <= 2:
            break
        H2, W2 = (H + 1) // 2, (W + 1) // 2
        ap = np.zeros((H2 * 2, W2 * 2, 3), np.float32)
        wp = np.zeros((H2 * 2, W2 * 2), np.float32)
        ap[:H, :W], wp[:H, :W] = a, w
        a = ap.reshape(H2, 2, W2, 2, 3).sum(axis=(1, 3))
        w = wp.reshape(H2, 2, W2, 2).sum(axis=(1, 3))
    a, w = tang[-1]
    c = a / np.maximum(w, 1e-6)[..., None]
    for a, w in reversed(tang[:-1]):
        H, W = w.shape
        len_ = _trung_binh_3(np.repeat(np.repeat(c, 2, axis=0), 2, axis=1)[:H, :W])
        wn = np.clip(w, 0.0, 1.0)[..., None]
        c = (a + len_ * (1.0 - wn)) / (w[..., None] + (1.0 - wn))
    return np.where(hong[..., None], c, arr).astype(np.float32)


def xoa_chu(anh, tim: Optional[Dict[str, Any]] = None):
    """Xoá các dòng chữ dò được khỏi ảnh đã ghép → (ảnh nền PIL, vùng chữ cũ (x0,y0,x1,y1) px, tim)."""
    np = _np()
    from PIL import Image, ImageFilter  # noqa: PLC0415
    anh = anh.convert("RGB")
    tim = tim if tim is not None else tim_dong_chu(anh)
    if not tim["dong"]:
        return anh, None, tim
    W, H = anh.size
    mn = Image.fromarray((tim["mat_na"] * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)
    hong = _gian(np.asarray(mn) > 127, max(4, int(W * 0.008)))
    # bóng đổ lệch xuống-phải của chữ mô hình vẽ
    lech = max(2, int(W * 0.006))
    hong[lech:, lech:] |= hong[:-lech, :-lech]
    arr = np.asarray(anh).astype(np.float32)
    va = va_nen(arr, hong)
    nen = Image.fromarray(np.clip(va, 0, 255).astype(np.uint8))
    mo = nen.filter(ImageFilter.GaussianBlur(max(3, W // 200)))
    mat = Image.fromarray((hong * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
    nen = Image.composite(mo, nen, mat)
    tim["hong"] = hong
    xs0 = min(d["hop"][0] for d in tim["dong"])
    ys0 = min(d["hop"][1] for d in tim["dong"])
    xs1 = max(d["hop"][2] for d in tim["dong"])
    ys1 = max(d["hop"][3] for d in tim["dong"])
    return nen, (xs0, ys0, xs1, ys1), tim


def _chia_tang(chu_bia: str) -> List[Dict[str, Any]]:
    """Chữ bìa → 2 tầng (trên/dưới) cho bộ vẽ: tách ở khoảng trắng/dấu câu gần giữa, không có thì ở sau
    trợ từ gần giữa (`bia_theo_khuon._cho_xuong_dong`) — không cắt giữa từ như 「70歳でこれ|が残って…」."""
    from . import bia_theo_khuon as btk  # noqa: PLC0415
    s = " ".join(str(chu_bia or "").split())
    if not s:
        return []
    if not re.search(r"[\s、。！？!?]", s) and len(btk._chuan(s)) >= 6:  # noqa: SLF001
        giua = len(s) / 2.0
        # sau trợ từ ghép (ほど/より/から…) hoặc trợ từ đơn, gần giữa nhất; trợ từ ghép thắng khi gần ngang
        cho = [(m.end(), 0.0) for m in re.finditer(_TRO_TU_GHEP, s) if 2 <= m.end() <= len(s) - 2]
        cho += [(i + 1, 1.0) for i, c in enumerate(s[:-1]) if c in "はがをにでともの" and 1 < i + 1 < len(s) - 1]
        k = min(cho, key=lambda x: abs(x[0] - giua) + x[1])[0] if cho else btk._cho_xuong_dong(s)  # noqa: SLF001
        s = s[:k] + " " + s[k:]
    return btk.tach_chu_mac_dinh(s, {})


_TRO_TU_GHEP = r"(?:ほど|より|から|まで|ても|ので|けど|なら|だけ|には|では|とは|って)"


def vet_xoa_lo(hong, bc: Dict[str, Any], phu_them: Sequence[Sequence[float]] = ()) -> float:
    """Tỉ lệ khung ảnh mà VẾT XOÁ chữ cũ (`hong`) lộ ra ngoài chữ/khung mới (theo hộp dòng trong `bc` và
    các hộp phủ thêm `phu_them` — khung nền khối đã phủ lên vùng chữ cũ)."""
    np = _np()
    if hong is None or not bc.get("dong"):
        return 0.0
    h = hong[::4, ::4]
    phu = np.zeros_like(h)
    for d in list(bc["dong"]) + [{"hop": r, "_m": 0} for r in phu_them]:
        x0, y0, x1, y1 = d.get("hop") or (0, 0, 0, 0)
        m = 0.0 if "_m" in d else 0.12 * (y1 - y0)
        phu[max(0, int((y0 - m) / 4)):int((y1 + m) / 4) + 1, max(0, int((x0 - m) / 4)):int((x1 + m) / 4) + 1] = True
    return float((h & ~phu).mean())


#: Vết xoá chữ cũ lộ quá ngần này phần khung thì lần vẽ lại đó TRƯỢT (mảng loang giữa bìa nhìn như lỗi).
VET_LO_TOI_DA = 0.035


#: Khung khối phủ vùng chữ cũ khi vẽ lại (che vết xoá): tối, mờ vừa — chữ trắng/vàng viền đen nổi trên nó.
_KHUNG_KHOI = ((14, 10, 22), 0.66)


def _phu_khoi(nen, vung, hong):
    """Phủ MỘT khung bo góc tối mờ lên vùng chữ cũ (bao cả vết xoá) → (ảnh nền mới, hộp khung px)."""
    np = _np()
    from PIL import Image, ImageDraw  # noqa: PLC0415
    W, H = nen.size
    x0, y0, x1, y1 = vung
    if hong is not None and hong.any():
        ys, xs = np.where(hong)
        x0, y0, x1, y1 = min(x0, xs.min()), min(y0, ys.min()), max(x1, xs.max()), max(y1, ys.max())
    p = 0.012 * W
    hop = (max(0, x0 - p), max(0, y0 - p), min(W, x1 + p), min(H, y1 + p))
    mn = Image.new("L", nen.size, 0)
    ImageDraw.Draw(mn).rounded_rectangle(hop, radius=int(0.03 * H), fill=int(255 * _KHUNG_KHOI[1]))
    lop = Image.new("RGBA", nen.size, _KHUNG_KHOI[0] + (255,))
    lop.putalpha(mn)
    return Image.alpha_composite(nen.convert("RGBA"), lop).convert("RGB"), hop


def ve_lai_tu_anh_ghep(anh, chu_tang: Sequence[Dict[str, Any]], dich: str, *, goc: str = "",
                       ngon_ngu: str = "", bao_cao: Optional[Dict[str, Any]] = None,
                       ghi: Optional[Any] = None) -> bool:
    """Vẽ lại bìa đã ghép `anh` (PIL.Image hoặc đường dẫn) với chữ `chu_tang` theo KIỂU THÍCH NGHI:
    xoá chữ cũ (`xoa_chu`), vẽ chữ vào đúng vùng chữ cũ; vùng chật không đạt cỡ chữ thì nới vùng rồi tới
    cả khung. Mỗi lần thử ĐO (`bia_theo_khuon.ve_chu_len_anh` → báo cáo chính xác); lấy lần ĐẠT đầu tiên,
    không lần nào đạt thì giữ lần điểm cao nhất (báo cáo TRƯỢT). Không gọi AI. Trả False khi không vẽ được."""
    from PIL import Image  # noqa: PLC0415
    from . import bia_theo_khuon as btk  # noqa: PLC0415
    if isinstance(anh, str):
        anh = Image.open(anh)
    anh = anh.convert("RGB")
    if anh.size != (1280, 720):
        from PIL import ImageOps  # noqa: PLC0415
        anh = ImageOps.fit(anh, (1280, 720), method=Image.LANCZOS)
    W, H = anh.size
    nen, vung, tim = xoa_chu(anh)
    # Các cách thử (vùng chữ, có phủ khung khối lên vùng chữ cũ không): gần chỗ chữ cũ trước.
    cach_thu: List[Tuple[Optional[Tuple[float, float, float, float]], bool]] = []
    if vung:
        x0, y0, x1, y1 = vung
        x0, x1 = max(0.0, x0 / W - 0.015), min(1.0, x1 / W + 0.015)
        y0, y1 = max(0.0, y0 / H - 0.02), min(1.0, y1 / H + 0.02)
        cach_thu += [((x0, y0, x1, y1), False), ((x0, y0, x1, y1), True)]
        if y1 - y0 < 0.6:  # nới dọc tới ≥ 60% khung quanh tâm vùng cũ
            tam = (y0 + y1) / 2
            n0 = max(0.0, min(tam - 0.3, 0.4))
            cach_thu += [((x0, n0, x1, min(1.0, n0 + 0.6)), True)]
    cach_thu += [(None, False), (None, True)]
    tot: Optional[Tuple[float, str, Dict[str, Any]]] = None
    tam_dir = os.path.dirname(os.path.abspath(dich)) or "."
    for i, (kc, phu) in enumerate(cach_thu):
        if phu and not vung:
            continue
        tep = dich if i == 0 else os.path.join(tam_dir, "_thu-{0}-{1}".format(i, os.path.basename(dich)))
        bc: Dict[str, Any] = {}
        tang = btk.bo_tri_chu("khuon", chu_tang)
        nen_thu, phu_them = nen, []
        if phu:
            nen_thu, hop_phu = _phu_khoi(nen, vung, tim.get("hong"))
            phu_them = [hop_phu]
        if not btk.ve_chu_len_anh("", tep, tang, goc=goc, ngon_ngu=ngon_ngu, khung_chu=kc, anh_nen=nen_thu,
                                  bao_cao=bc):
            continue
        lo = vet_xoa_lo(tim.get("hong"), bc, phu_them)
        if lo > VET_LO_TOI_DA and bc.get("dat"):
            bc["dat"] = False
            bc["doc_duoc"] = "thap"
            bc.setdefault("ly_do", []).insert(0, "vết xoá chữ cũ lộ {0:.0%} khung".format(lo))
        bc["vet_lo"] = round(lo, 3)
        diem = float(bc.get("diem") or 0) + (1000 if bc.get("dat") else 0)
        if ghi:
            ghi("    thử vùng {0}{1}: {2}".format(
                "cả khung" if kc is None else "({0:.2f},{1:.2f})–({2:.2f},{3:.2f})".format(*kc),
                " + khung khối" if phu else "", tom_tat(bc)))
        if tot is None or diem > tot[0]:
            tot = (diem, tep, bc)
        if bc.get("dat"):  # lần ĐẠT đầu tiên: gần chỗ chữ cũ nhất (che vết xoá, không đè nhân vật)
            break
    if tot is None:
        return False
    if tot[1] != dich:
        os.replace(tot[1], dich)
        ghi_bao_cao(dich, tot[2])
    for i in range(len(cach_thu)):
        t = os.path.join(tam_dir, "_thu-{0}-{1}".format(i, os.path.basename(dich)))
        for x in (t, duong_bao_cao(t)):
            try:
                os.remove(x)
            except OSError:
                pass
    if bao_cao is not None:
        bao_cao.clear()
        bao_cao.update(tot[2])
    return True


# ── Gói đã có (CLI) ───────────────────────────────────────────────────────────


def _goc_mac_dinh() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tim_bia_goi(goc: str, kenh: str, ma: str) -> Dict[str, Any]:
    """Tìm bìa ĐANG DÙNG của gói `ma` (vd TL4-T7-K2-0004): `{luot, thu_muc_luot, chon (CHON-*.jpg trong
    7-thumbnail, có thể ''), ho_so_anh, chu_bia, chu_tang (kế hoạch bìa nếu còn), nguon (ảnh để vẽ lại)}`."""
    from . import ho_so_video  # noqa: PLC0415
    luot = ma[len(kenh) + 1:] if ma.startswith(kenh + "-") else ma.rsplit("-", 1)[-1]
    thu_muc_luot = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)
    thu_muc_thumb = os.path.join(thu_muc_luot, "7-thumbnail")
    chon = ""
    try:
        for t in sorted(os.listdir(thu_muc_thumb)):
            if t.upper().startswith("CHON-") and os.path.splitext(t)[1].lower() in (".jpg", ".jpeg", ".png"):
                chon = os.path.join(thu_muc_thumb, t)
                break
    except OSError:
        pass
    hs = ho_so_video.doc_ho_so(goc, kenh, ma) or {}
    anh_hs = ho_so_video.duong_anh_ho_so(goc, kenh, ma)
    chu_bia = str(hs.get("chu_bia") or "")
    chu_tang: List[Dict[str, Any]] = []
    try:
        from . import bia_theo_khuon as btk  # noqa: PLC0415
        kh = btk.doc_ke_hoach(thu_muc_thumb) or {}
        so = int(re.search(r"(\d+)", os.path.basename(chon)).group(1)) if chon else -1
        for m in kh.get("muc") or []:
            if int(m.get("so") or 0) == so and m.get("chu_tang"):
                chu_tang = list(m["chu_tang"])
    except Exception:  # noqa: BLE001
        chu_tang = []
    nguon = chon if chon else (anh_hs if os.path.isfile(anh_hs) else "")
    return {"luot": luot, "thu_muc_luot": thu_muc_luot, "thu_muc_thumb": thu_muc_thumb, "chon": chon,
            "ho_so_anh": anh_hs, "chu_bia": chu_bia, "chu_tang": chu_tang, "nguon": nguon,
            "ngon_ngu": _ngon_ngu_kenh(goc, kenh)}


def _ngon_ngu_kenh(goc: str, kenh: str) -> str:
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        return str((doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}).get("ngon_ngu") or "")
    except Exception:  # noqa: BLE001
        return ""


def lam_lai_goi(goc: str, kenh: str, ma: str, *, thu: bool = False, ra: str = "", ep: bool = False,
                ghi: Any = print) -> Dict[str, Any]:
    """Vẽ lại bìa của gói đã có bằng kiểu thích nghi (không gọi AI). `thu=True`: chỉ ghi vào `ra` (thư mục
    tạm); không thì thay `CHON-*.jpg` trong `7-thumbnail` (bản cũ chép vào `7-thumbnail/_truoc-do-bia/`) và
    ghi bản chờ đổi `ho-so-video/anh/_doc-duoc/<mã>.jpg` cho `--xep-doi-bia`. Trả {truoc, sau, tep}."""
    from PIL import Image  # noqa: PLC0415
    tt = tim_bia_goi(goc, kenh, ma)
    if not tt["nguon"]:
        raise RuntimeError("không thấy bìa của {0} (7-thumbnail/CHON-* hay ho-so-video/anh)".format(ma))
    truoc = cham_tep(tt["nguon"])
    if truoc.get("dat") and not ep:
        # Bìa đang ĐẠT: không đụng (xoá chữ cũ có thể xoá luôn nhân vật nằm sau chữ — TL3 nền tím).
        ghi("  bìa đang dùng đã ĐẠT — giữ nguyên (thêm --ep để vẫn vẽ lại).")
        return {"ma": ma, "truoc": truoc, "sau": truoc, "tep": tt["nguon"], "nguon": tt["nguon"], "giu": True}
    chu_tang = tt["chu_tang"] or _chia_tang(tt["chu_bia"])
    if not chu_tang:
        raise RuntimeError("không có chữ bìa cho {0} (hồ sơ thiếu chu_bia)".format(ma))
    if thu:
        thu_muc = ra or os.path.join(os.environ.get("TEMP", "."), "do-bia-thu")
    else:
        thu_muc = os.path.join(tt["thu_muc_thumb"] if tt["chon"] else os.path.dirname(tt["ho_so_anh"]),
                               "_lam-lai")
    os.makedirs(thu_muc, exist_ok=True)
    png = os.path.join(thu_muc, "{0}.png".format(ma))
    bc: Dict[str, Any] = {}
    if not ve_lai_tu_anh_ghep(tt["nguon"], chu_tang, png, goc=goc, ngon_ngu=tt["ngon_ngu"], bao_cao=bc,
                              ghi=ghi):
        raise RuntimeError("không vẽ lại được (thiếu font?)")
    jpg = os.path.join(thu_muc, "{0}.jpg".format(ma))
    Image.open(png).convert("RGB").save(jpg, format="JPEG", quality=92)
    ghi_bao_cao(jpg, bc)
    ra_tt = {"ma": ma, "truoc": truoc, "sau": bc, "tep": jpg, "nguon": tt["nguon"], "chu_tang": chu_tang}
    if thu:
        return ra_tt
    if not bc.get("dat"):
        ghi("  (!) bản vẽ lại vẫn TRƯỢT — KHÔNG thay bìa gói: " + tom_tat(bc))
        return ra_tt
    if tt["chon"]:
        sao = os.path.join(tt["thu_muc_thumb"], "_truoc-do-bia")
        os.makedirs(sao, exist_ok=True)
        dich_sao = os.path.join(sao, os.path.basename(tt["chon"]))
        if not os.path.exists(dich_sao):
            shutil.copy2(tt["chon"], dich_sao)
        shutil.copy2(jpg, tt["chon"] + ".tam")
        os.replace(tt["chon"] + ".tam", tt["chon"])
        ghi_bao_cao(tt["chon"], bc)
    cho = os.path.join(os.path.dirname(tt["ho_so_anh"]), "_doc-duoc", "{0}.jpg".format(ma))
    os.makedirs(os.path.dirname(cho), exist_ok=True)
    shutil.copy2(jpg, cho)
    ghi_bao_cao(cho, bc)
    ra_tt["tep_doi"] = cho
    return ra_tt


def xep_doi_bia(goc: str, kenh: str, ma: str, anh: str, *, ly_do: str = "", ghi: Any = print) -> Dict[str, Any]:
    """Xếp MỘT việc đổi bìa cho máy DOM (`vm/logs/hang-sua.json`, cùng khoá với giám đốc kênh) — máy DOM
    làm ở lượt `python vm/may_dang_dom.py --kenh <kênh> --sua-video`. Chỉ nhận bìa ĐẠT `cham_tep`. Ghi
    `lich_su_sua` của hồ sơ (đo trước/sau CTR) và thay bản sao `ho-so-video/anh/<mã>.jpg` (bản cũ vào
    `anh/_truoc-do-bia/`) để vòng học so đúng bìa đang chạy."""
    from . import ho_so_video  # noqa: PLC0415
    from .giam_doc import cuu_ctr  # noqa: PLC0415
    anh = os.path.abspath(anh)
    if not os.path.isfile(anh):
        raise RuntimeError("không có tệp bìa " + anh)
    bc = cham_tep(anh)
    if not bc.get("dat"):
        raise RuntimeError("bìa mới chưa ĐẠT độ đọc được — không xếp: " + tom_tat(bc))
    hs = ho_so_video.doc_ho_so(goc, kenh, ma) or {}
    vid = str(hs.get("video_id") or "")
    if not vid:
        raise RuntimeError("hồ sơ {0} chưa có video_id (video chưa lên YouTube?)".format(ma))
    khoa = cuu_ctr.giu_khoa_hang(goc)
    if not khoa:
        raise RuntimeError("hàng sửa đang bị khoá (máy DOM/giám đốc đang ghi) — thử lại sau")
    try:
        hang = cuu_ctr.doc_hang(goc)
        muc = {"id": "do-bia-{0}-{1}".format(ma, _dt.datetime.now().strftime("%Y%m%d%H%M")), "video_id": vid,
               "ma_goi": ma}
        viec = cuu_ctr._viec_hang(muc, kenh, "bia", anh=anh)  # noqa: SLF001
        viec["ly_do"] = ly_do or "bìa đọc được (core/do_bia): " + tom_tat(bc)[:160]
        hang = [v for v in hang if not (v.get("ma_goi") == ma and v.get("buoc") == "bia"
                                        and v.get("trang_thai") in ("cho", "loi"))] + [viec]
        cuu_ctr._ghi_hang(goc, hang)  # noqa: SLF001
    finally:
        try:
            os.remove(khoa)
        except OSError:
            pass
    anh_hs = ho_so_video.duong_anh_ho_so(goc, kenh, ma)
    if os.path.isfile(anh_hs) and os.path.abspath(anh_hs) != anh:
        sao = os.path.join(os.path.dirname(anh_hs), "_truoc-do-bia")
        os.makedirs(sao, exist_ok=True)
        if not os.path.exists(os.path.join(sao, os.path.basename(anh_hs))):
            shutil.copy2(anh_hs, os.path.join(sao, os.path.basename(anh_hs)))
        shutil.copy2(anh, anh_hs)
    try:
        ho_so_video.ghi_sua(goc, kenh, ma, loai="bia", cu=os.path.basename(anh_hs), moi=os.path.basename(anh),
                            doi_boi="do_bia", ly_do=viec["ly_do"])
        ho_so_video.cap_nhat_bia_doc_duoc(goc, kenh, ma, bc)
    except Exception as loi:  # noqa: BLE001 — việc đã xếp; hồ sơ hỏng chỉ báo
        ghi("  (ghi hồ sơ hỏng: {0})".format(str(loi)[:120]))
    return {"viec": viec["id"], "video_id": "…" + vid[-3:], "anh": anh}


# ── Hiệu chỉnh trên bìa thật (chỉ đọc) ────────────────────────────────────────


def hieu_chinh(goc: str, n: int = 40) -> List[Dict[str, Any]]:
    """Chấm MÙ `n` bìa mới nhất (`CHANNEL/*/ho-so-video/anh/<mã gói>.jpg`) — bảng hiệu chỉnh ngưỡng."""
    import glob  # noqa: PLC0415
    ds = []
    for d in glob.glob(os.path.join(goc, "CHANNEL", "*", "ho-so-video", "anh", "*.jpg")):
        ten = os.path.splitext(os.path.basename(d))[0]
        if not re.match(r"^TL\d.*-\d{4}$", ten):
            continue
        ds.append((os.path.getmtime(d), ten, d))
    ra = []
    for _m, ten, d in sorted(ds, reverse=True)[:n]:
        bc = cham_tep(d)
        ra.append({"ma": ten, "dat": bc.get("dat"), "diem": bc.get("diem"), "tp_min": bc.get("tuong_phan_min"),
                   "nen_min": bc.get("tuong_phan_nen_min"), "cao_min": bc.get("cao_min_pct"),
                   "cao_max": max([x["cao_pct"] for x in bc.get("dong") or []] or [0]),
                   "so_dong": len(bc.get("dong") or []), "ly_do": (bc.get("ly_do") or [""])[0][:90]})
    return ra


def _in_bc(bc: Dict[str, Any], ghi=print) -> None:
    ghi("  " + tom_tat(bc))
    for d in bc.get("dong") or []:
        ghi("    - {0:<16} tương phản {1:>5.1f}:1 (chữ↔nền {2:.1f}, ngưỡng {3:.1f})  cao {4:>4.1f}%  "
            "nền rối {5:.2f}  màu {6}{7}".format(
                str(d.get("ten") or "")[:16], d["tuong_phan"], d["tuong_phan_nen"], d["nguong"], d["cao_pct"],
                d["ban_ron"], ",".join(d.get("mau_chu") or []),
                "  kiểu " + d["kieu"] if d.get("kieu") else ""))


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(prog="python -m core.do_bia", description=__doc__.split("\n")[0])
    ap.add_argument("--kiem", nargs=2, metavar=("KENH", "MA"), help="chấm bìa đang dùng của gói")
    ap.add_argument("--lam-lai", nargs=2, metavar=("KENH", "MA"), help="vẽ lại bìa gói với kiểu thích nghi")
    ap.add_argument("--thu", action="store_true", help="với --lam-lai: chỉ ghi vào thư mục tạm (--ra)")
    ap.add_argument("--ra", default="", help="thư mục ra cho --thu")
    ap.add_argument("--ep", action="store_true", help="với --lam-lai: vẽ lại cả khi bìa đang ĐẠT")
    ap.add_argument("--anh", default="", help="chấm một tệp ảnh bất kỳ / ảnh cho --xep-doi-bia")
    ap.add_argument("--xep-doi-bia", nargs=2, metavar=("KENH", "MA"), help="xếp việc đổi bìa cho máy DOM")
    ap.add_argument("--hieu-chinh", action="store_true", help="bảng điểm n bìa mới nhất (chỉ đọc)")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--goc", default=_goc_mac_dinh())
    a = ap.parse_args(argv)
    if a.kiem:
        tt = tim_bia_goi(a.goc, a.kiem[0], a.kiem[1])
        if not tt["nguon"]:
            print("không thấy bìa của", a.kiem[1])
            return 2
        print("{0}: {1}".format(a.kiem[1], os.path.relpath(tt["nguon"], a.goc)))
        bc = cham_tep(tt["nguon"])
        _in_bc(bc)
        return 0 if bc.get("dat") else 1
    if a.lam_lai:
        r = lam_lai_goi(a.goc, a.lam_lai[0], a.lam_lai[1], thu=a.thu, ra=a.ra, ep=a.ep)
        print("{0}: TRƯỚC".format(r["ma"]))
        _in_bc(r["truoc"])
        print("{0}: SAU → {1}".format(r["ma"], r["tep"]))
        _in_bc(r["sau"])
        if r.get("tep_doi"):
            print("  bản chờ đổi:", r["tep_doi"])
        return 0 if r["sau"].get("dat") else 1
    if a.xep_doi_bia:
        r = xep_doi_bia(a.goc, a.xep_doi_bia[0], a.xep_doi_bia[1], a.anh)
        print("đã xếp việc", r["viec"], "video", r["video_id"], "— máy DOM làm ở lượt --sua-video kế tiếp")
        return 0
    if a.hieu_chinh:
        for r in hieu_chinh(a.goc, a.n):
            print("{ma:<18} {d:<6} điểm {diem:>5}  tp_min {tp:>5}  chữ↔nền {nen:>5}  cao {cmin:>4}–{cmax:>4}%  "
                  "{n} dòng  {ly}".format(ma=r["ma"], d={True: "ĐẠT", False: "TRƯỢT", None: "?"}[r["dat"]],
                                          diem=r["diem"], tp=r["tp_min"], nen=r["nen_min"], cmin=r["cao_min"],
                                          cmax=round(r["cao_max"], 1), n=r["so_dong"], ly=r["ly_do"]))
        return 0
    if a.anh:
        _in_bc(cham_tep(a.anh))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
    sys.exit(main())


