"""Lỗi CỨNG trên ảnh cảnh, kiểm bằng máy (không gọi mạng) — 17/10/2026.

═══ VÌ SAO ═══

Tờ liên thử thật TL6 17/10: giám khảo AI chấm 10 điểm lỗi cho một tấm LƯỚI 12 ô, và để lọt mũi tên đỏ vẽ chồng lên
tranh. Hai lỗi này nhìn bằng mắt là thấy ngay, nên có một tầng kiểm tất định đứng trước giám khảo:

* `mui_ten_do`: mảng đỏ thuần (đỏ "ký hiệu", không phải đỏ gạch / hồng / cam của tranh) đủ lớn — dấu mũi tên, dấu X,
  vòng khoanh đỏ vẽ chồng lên tranh.
* `luoi`: tranh bị chia ô — đường kẻ thẳng chạy SUỐT chiều cao VÀ suốt chiều ngang, gần các vạch chia đều.

Mỗi phép đo có hai ngưỡng: lỗi CHẮC (điểm tấm = 0, không cần hỏi ai) và NGHI (báo cho giám khảo nhìn kỹ tấm ấy). Hai phép đo chỉ cần numpy + PIL —
đã có sẵn trong bộ cài. Lỗi đọc ảnh → coi như sạch (không chặn ảnh vì một phép đo hỏng).

Chữ trong ảnh và dấu sao góc không đo được tử tế bằng máy ở đây (không có OCR trong bộ cài; dấu sao do nhà cung cấp
dán sau và `core/xoa_dau_anh` gỡ) — giám khảo AI trả hai cờ `chu` / `dau` cho chúng.
"""

from __future__ import annotations

from typing import Any, Dict

__all__ = ["kiem", "do_do", "do_luoi", "DO_CUNG", "DO_NGHI", "LUOI_CUNG", "LUOI_NGHI"]

#: Mảng đỏ-ký-hiệu lớn nhất (phần khung, ảnh thu về 344×192). Đo 17/10 trên 296 ảnh thật: mũi tên đỏ vẽ chồng
#: 0,004–0,025; đồ vật đỏ thật của tranh (gáy sách, quả hồng) ≤ 0,0032. Từ `DO_CUNG` là lỗi chắc; từ `DO_NGHI` thì
#: báo giám khảo nhìn kỹ (nó quyết).
DO_CUNG, DO_NGHI = 0.006, 0.001
#: Độ phủ của đường kẻ suốt (nhỏ hơn trong hai trục), gần vạch chia đều. Đo: lưới 4 ô thật 0,97; lưới 12 ô viền mờ 0,71;
#: tranh thường (khung cửa shoji, phòng kẻ ô) tới 0,77. Từ `LUOI_CUNG` là lỗi chắc; từ `LUOI_NGHI` báo giám khảo.
LUOI_CUNG, LUOI_NGHI = 0.90, 0.65
NGUONG_DO, NGUONG_LUOI = DO_CUNG, LUOI_CUNG
_CO = (344, 192)
_VACH = (1 / 2, 1 / 3, 2 / 3, 1 / 4, 3 / 4)


def _nap(duong: str):
    from PIL import Image  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    im = Image.open(duong).convert("RGB").resize(_CO)
    return np, np.asarray(im, dtype=np.int32)


def _mang_lon_nhat(mat) -> int:
    """Diện tích mảng liền (4 hướng) lớn nhất trong mặt nạ bool — ảnh nhỏ, BFS thường là đủ."""
    co = set(zip(*mat.nonzero()))
    da = set()
    tot = 0
    for p in list(co):
        if p in da:
            continue
        hang, n = [p], 0
        da.add(p)
        while hang:
            y, x = hang.pop()
            n += 1
            for q in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if q in co and q not in da:
                    da.add(q)
                    hang.append(q)
        tot = max(tot, n)
    return tot


def do_do(duong: str) -> float:
    """Phần khung của mảng đỏ-ký-hiệu lớn nhất (0 = không có)."""
    np, a = _nap(duong)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mat = (r > 185) & (g < 75) & (b < 85) & (r - g > 130) & (r - b > 120)
    if int(mat.sum()) == 0:
        return 0.0
    return _mang_lon_nhat(mat) / float(_CO[0] * _CO[1])


def do_luoi(duong: str) -> float:
    """Độ phủ (0..1) của đường kẻ thẳng suốt khung gần vạch chia đều — lấy trục KÉM hơn (lưới cần cả dọc lẫn ngang)."""
    np, a = _nap(duong)
    xam = a.mean(axis=2)
    ra = []
    for truc in (1, 0):
        d = np.abs(np.diff(xam, axis=truc))
        phu = (d > 28).mean(axis=1 - truc)
        n = len(phu)
        ra.append(max([float(phu[i]) for i in range(n) if any(abs((i + 1) / n - v) < 0.025 for v in _VACH)] or [0.0]))
    return min(ra)


def kiem(duong: str, *, cho_do: bool = False) -> Dict[str, Any]:
    """{"loi": [lỗi chắc], "nghi": [cần giám khảo nhìn kỹ], "do": phần đỏ, "luoi": độ phủ}. `cho_do`: kênh cho dấu đỏ."""
    ra: Dict[str, Any] = {"loi": [], "nghi": [], "do": 0.0, "luoi": 0.0}
    try:
        ra["do"] = round(do_do(duong), 5)
        ra["luoi"] = round(do_luoi(duong), 3)
    except Exception:  # noqa: BLE001 — phép đo hỏng: coi như sạch, để giám khảo lo
        return ra
    if not cho_do:
        if ra["do"] >= DO_CUNG:
            ra["loi"].append("mui_ten_do")
        elif ra["do"] >= DO_NGHI:
            ra["nghi"].append("mui_ten_do")
    if ra["luoi"] >= LUOI_CUNG:
        ra["loi"].append("luoi")
    elif ra["luoi"] >= LUOI_NGHI:
        ra["nghi"].append("luoi")
    return ra
