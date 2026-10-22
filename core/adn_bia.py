"""ADN PHONG CÁCH BÌA (22/10/2026) — học bảng màu / ánh sáng / độ nghiêng chữ của bìa THẮNG thật từng kênh, ép vào lời
nhắc ảnh, bộ vẽ chữ và cổng chọn bìa.

═══ VÌ SAO ═══

Chủ 22/10: *"bìa thắng rõ ràng có hình thức / tông màu / phong cách, nhưng video mới không học được."* Soi bìa thật:
TL3 — MỌI bìa thắng nền TÍM sẫm phát sáng + nhân vật cam; bìa 14/10 và 21/10 nền nâu hổ phách → mất tông tím. Sàn màu
cũ (`bia_lo.san_mau`: bão hoà / tương phản / dải sáng) KHÔNG đo SẮC nên hổ phách vẫn qua. TL2 — bìa thắng có dải màu
NGHIÊNG, cảnh tối đèn rọi; bìa máy chữ thẳng trên nền be sáng. Hệ dữ liệu (`core/bia_du_lieu` họ kiểu chữ, `core/bia_ab`,
`core/hieu_chuan`) chỉ học HỌ kiểu chữ, không học ADN phong cách.

═══ LÀM GÌ ═══

1. ĐO ADN MỖI BÌA (máy, numpy/PIL, cache theo sha1 — `workspace/bia-kieu/adn.json`):
   · `hue`: phân bố SẮC 12 ô (30°/ô, chia mềm hai ô kề), trọng số bão hoà × √độ sáng, bỏ vùng chữ (chữ màu ngách sát
     viền tối — `mat_na_chu`) và điểm xám/đen;
   · `sang_nen` (trung vị độ sáng nền ngoài chữ), `ti_toi` (phần nền gần đen), `ti_sang`;
   · `goc_chu`: độ nghiêng dòng chữ (độ, + = lên về bên phải) — chiếu hình mặt nạ chữ theo từng góc, góc cho biểu đồ
     hàng SẮC nhất (cách chỉnh nghiêng văn bản cổ điển), rồi từng dòng riêng; `goc_dai`: độ nghiêng DẢI màu sau dòng
     chữ — màu trội quanh dòng, mép trên/dưới của dải (chỗ không bị chữ che) → độ dốc Theil–Sen; `chu_mau`: phần
     trắng / vàng / đỏ của chữ. Đo 22/10: bìa thắng #1 TL2 chữ 8,25° + dải 9,5° (đo cột tay: ~8°), #2 chữ 5,25°.
   · NHÌN (một lượt AI theo nhóm 6 ảnh qua ví ShopAPI — `goi_van_ban.qua_vi`, cache theo sha1 —
     `workspace/bia-kieu/adn-nhin.json`): ánh sáng (tối / sáng / đèn rọi / phát sáng), từ màu, bố cục chữ (thẳng /
     nghiêng / dải chéo), nhân vật (cỡ, vị trí, tư thế), một câu tả.
2. ADN KÊNH = tổng hợp có trọng số LƯỢT BẤM (hiển thị × CTR) trên bộ bìa thắng D21 (`thang.json`) — cả kênh và theo
   HỌ kiểu chữ. Ngưỡng tự hiệu chỉnh trên chính bìa thắng: `nguong_hue` = khoảng cách sắc (Hellinger) của bìa thắng
   XA nhất tới ADN của các bìa thắng còn lại (bỏ-một-ra), không dưới `HUE_NGUONG_SAN`; kênh "tối" (≥ `TI_TOI_KENH`
   trọng số bìa thắng có nền tối) → `nguong_sang` = max(nền sáng nhất của bìa thắng + `LE_SANG`, `NEN_TOI`).
3. ÉP VÀO SẢN XUẤT (`core/bia_lo`): câu ADN (`cau_lenh`) vào lời nhắc ảnh nền + đạo diễn + giám khảo; bộ vẽ nghiêng
   dòng chữ / dải theo góc đo của họ (`goc_ve`); cổng `kiem`: sắc lệch > `nguong_hue` hoặc kênh tối mà cảnh sáng hơn
   `nguong_sang` → dưới sàn (không vào top; ô C khám phá A/B được miễn sàn sáng).
4. VÒNG HỌC: ADN mỗi bìa máy vào `bia-ket-qua.jsonl` và sổ A/B; `nghien-cuu/bia-adn.json` (D21) giữ ADN + CTR mọi
   video đủ chín → `core/hieu_chuan.them_adn` đo đặc trưng ADN nào đi cùng CTR / thắng A/B. Đích ADN dịch theo bộ bìa
   thắng mới mỗi lần D21 dựng lại (dữ liệu, không mã cứng).

Dùng:  python -X utf8 -m core.adn_bia thu --kenh K [--so 6] [--khong-ai] [--tam DIR] [--goc G]   (CHỈ ĐỌC)
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

PHIEN_BAN = 1
PHIEN_BAN_NHIN = 1
SO_O = 12
#: Lưới đo màu và lưới đo chữ/góc.
LUOI_MAU, LUOI_CHU = (320, 180), (640, 360)
#: Góc nghiêng lớn nhất được tin (độ).
GOC_TOI_DA = 12.0
#: Ngưỡng khoảng cách sắc tối thiểu — bìa thắng gần như một màu vẫn chừa chỗ cho khác biệt nhỏ (đo 22/10: TL6 3 bìa
#: thắng bỏ-một-ra ≤ 0,09 → sàn 0,12 loại 4/6 bìa máy cùng tông cam; TL3 hổ phách lệch 0,72–0,77 so ngưỡng 0,34).
HUE_NGUONG_SAN = 0.25
#: Kênh "tối": ≥ ngần này trọng số bìa thắng có `sang_nen` < `NEN_TOI`.
TI_TOI_KENH, NEN_TOI = 0.75, 0.30
LE_SANG = 0.05
#: Cổng chỉ bật khi đủ bằng chứng: ≥ `SO_THANG_CONG` bìa thắng đo được, tổng ≥ `BAM_CONG` lượt bấm.
SO_THANG_CONG, BAM_CONG = 3, 1500.0
#: Dòng chữ nghiêng ít hơn ngần này độ coi là thẳng (không vẽ nghiêng).
GOC_THANG = 1.5
#: Góc vẽ tối đa (bộ vẽ kẹp thêm cho chữ không tràn khung).
GOC_VE_TOI_DA = 8.0
#: Bộ vẽ nghiêng chữ / dải khi ≥ ngần này trọng số lượt bấm bìa thắng của họ nghiêng / có dải.
TI_VE = 0.4
#: Bìa "nghiêng" khi ≥ ngần này trọng số dòng (số điểm chữ) nghiêng ≥ `GOC_THANG` CÙNG chiều.
TI_DONG_NGHIENG = 0.6
TEP_CACHE = os.path.join("workspace", "bia-kieu", "adn.json")
TEP_NHIN = os.path.join("workspace", "bia-kieu", "adn-nhin.json")
TEP_THANG = "adn-thang.json"
TEP_KENH = "bia-adn.json"
NHOM_NHIN = 6
MO_HINH_NHIN = "claude-sonnet-5"
_DUOI_ANH = (".jpg", ".jpeg", ".png", ".webp")

#: Tên màu tiếng Anh của 12 ô sắc (tâm ô 0°, 30°, …).
TEN_O = ("red", "orange", "amber yellow", "yellow-green", "green", "teal", "cyan", "sky blue", "blue", "violet purple",
         "magenta", "pink red")

LOI_NHAC_NHIN = """These {n} images are YouTube thumbnails, numbered 1 to {n} in the order shown. For EACH one describe \
its STYLE (not its text content):
"anh_sang": the scene lighting: "dark" | "medium" | "bright";
"kieu_sang": "spotlight" (a cone or pool of light in a dark scene) | "glow" (a glowing aura / neon light around the \
character or objects) | "even" (flat even light) | "backlit" | "none";
"mau": up to 4 colour words of the BACKGROUND, most dominant first (e.g. "deep purple", "violet", "beige");
"bo_cuc_chu": how the big text lines are laid out: "straight" (horizontal lines) | "tilted" (lines rotated a few \
degrees) | "diagonal_bands" (lines on slanted colour bands) | "stacked_bands" (lines on horizontal colour bands) | \
"mixed";
"nhan_vat": the main character: "co": "small" | "medium" | "large" (share of frame height), "vi_tri": "left" | \
"center" | "right", "tu_the": its pose in at most 8 words;
"ta": ONE English sentence (at most 30 words) describing the visual style DNA (palette, light, mood, character look) as \
an instruction for an image model — no text, no layout.
Return JSON only: {{"bia": [{{"so": 1, "anh_sang": "dark", "kieu_sang": "glow", "mau": ["deep purple"], \
"bo_cuc_chu": "straight", "nhan_vat": {{"co": "large", "vi_tri": "center", "tu_the": "..."}}, "ta": "..."}}]}} — one \
item per image."""


# ── tiện ích ────────────────────────────────────────────────────────────────


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with io.open(duong + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tmp", duong)


def sha1_tep(duong: str) -> str:
    h = hashlib.sha1()  # noqa: S324 — nhận diện tệp, không mật mã
    try:
        with open(duong, "rb") as tep:
            for khoi in iter(lambda: tep.read(1 << 16), b""):
                h.update(khoi)
    except OSError:
        return ""
    return h.hexdigest()


def _np():
    import numpy as np  # noqa: PLC0415
    return np


def _anh(nguon: Any):
    from PIL import Image  # noqa: PLC0415
    if hasattr(nguon, "size"):
        return nguon.convert("RGB")
    with Image.open(nguon) as im:  # đóng tệp ngay (Windows khoá tệp đang mở)
        return im.convert("RGB")


def _gian(m, r: int):
    """Giãn mặt nạ bool `m` bán kính `r` (ô vuông) — numpy thuần."""
    np = _np()
    if r <= 0:
        return m
    h, w = m.shape
    p = np.pad(m, r)
    ra = np.zeros_like(m)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ra |= p[r + dy:r + dy + h, r + dx:r + dx + w]
    return ra


def mat_na_chu(a) -> Tuple[Any, Any]:
    """(mặt nạ NÉT chữ, mặt nạ VÙNG chữ đã giãn gồm viền) trên mảng rgb int16 — chữ trần của ngách: điểm trắng tinh / đỏ
    tươi / vàng tươi nằm sát nét viền TỐI (như `bia_lo.tinh_hop_dong`; đỏ ≥ 200 — dải cọ đỏ SẪM ~#B3191E không phải
    chữ)."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mau = (a.min(axis=2) >= 225) | ((r >= 200) & (g <= 80) & (b <= 80)) | ((r >= 200) & (g >= 170) & (b <= 100))
    vien = _gian(a.max(axis=2) <= 80, 3)
    net = mau & vien
    return net, _gian(net, 4)


def hellinger(p: Sequence[float], q: Sequence[float]) -> float:
    """Khoảng cách Hellinger giữa hai phân bố (0 = trùng, 1 = rời hẳn)."""
    sp, sq = float(sum(p)) or 1.0, float(sum(q)) or 1.0
    bc = sum(math.sqrt(max(0.0, float(x) / sp) * max(0.0, float(y) / sq)) for x, y in zip(p, q))
    return round(math.sqrt(max(0.0, 1.0 - bc)), 4)


# ── 1) Góc nghiêng dòng chữ (chiếu hình) và dải màu (mép, Theil–Sen) ─────────


def _theil_sen(xc: Sequence[float], yc: Sequence[float], dx_toi_thieu: float) -> Optional[float]:
    """Độ dốc trung vị của mọi cặp điểm cách nhau ≥ `dx_toi_thieu` theo x (bền với điểm lạc). Ít cặp → None."""
    doc = [(yc[j] - yc[i]) / (xc[j] - xc[i]) for i in range(len(xc)) for j in range(i + 1, len(xc))
           if xc[j] - xc[i] >= dx_toi_thieu]
    if len(doc) < 6:
        return None
    doc.sort()
    return doc[len(doc) // 2]


def _do_sac(ys, xs, goc, o: float = 2.0):
    """Độ SẮC biểu đồ hàng khi chiếu điểm (y xuống, x phải) theo từng góc (+ = dòng lên về bên phải): Σ đếm² / N².
    Dòng chữ nghiêng α: mọi điểm của nó có y + x·tan α gần như không đổi → biểu đồ hàng sắc nhất ở đúng α."""
    np = _np()
    t = np.tan(np.radians(goc))
    ra = np.zeros(len(goc))
    n = float(len(ys)) or 1.0
    for i, ti in enumerate(t):
        yp = np.floor((ys + xs * ti) / o).astype(np.int64)
        dem = np.bincount(yp - yp.min())
        ra[i] = float((dem.astype(np.float64) ** 2).sum()) / (n * n)
    return ra


def goc_chieu(ys, xs, *, toi_da: float = GOC_TOI_DA, buoc: float = 0.5) -> Optional[float]:
    """Góc (độ, + = lên về bên phải) làm biểu đồ hàng của các điểm SẮC nhất (chỉnh nghiêng văn bản cổ điển). Đo
    22/10 trên bìa thắng thật: TL2 #1 chữ + dải nghiêng ~8° (đo cột: đáy dòng đỏ 339 → 245 px trên 660 px), TL3 ~0°.
    Ít điểm → None."""
    np = _np()
    if len(ys) < 80:
        return None
    goc = np.arange(-toi_da, toi_da + 1e-9, buoc)
    s = _do_sac(np.asarray(ys, dtype=np.float64), np.asarray(xs, dtype=np.float64), goc)
    return float(goc[int(np.argmax(s))])


def _doan(prof, nguong: float, gop: int = 2) -> List[Tuple[int, int]]:
    """Các đoạn liên tiếp `prof` > `nguong` (gộp khe ≤ `gop`)."""
    idx = [i for i, v in enumerate(prof) if v > nguong]
    if not idx:
        return []
    ra, a, b = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - b <= gop + 1:
            b = i
        else:
            ra.append((a, b + 1))
            a = b = i
    ra.append((a, b + 1))
    return ra


def _tach(prof, a: int, b: int, cao_toi_da: float) -> List[Tuple[int, int]]:
    """Đoạn [a, b) của biểu đồ hàng quá CAO (các dòng dính nhau — dải màu lấp khe) → tách đệ quy ở chỗ trũng sâu nhất
    (≤ 60% đỉnh thấp hơn của hai bên) trong 80% giữa đoạn."""
    if b - a <= cao_toi_da or b - a < 8:
        return [(a, b)]
    lo, hi = a + max(2, (b - a) // 10), b - max(2, (b - a) // 10)
    seg = prof[lo:hi]
    if len(seg) < 3:
        return [(a, b)]
    k = lo + int(seg.argmin())
    if float(prof[k]) > 0.6 * min(float(prof[a:k].max()), float(prof[k + 1:b].max())):
        return [(a, b)]
    return _tach(prof, a, k, cao_toi_da) + _tach(prof, k + 1, b, cao_toi_da)


def dong_chu(net, W: int) -> List[Dict[str, Any]]:
    """Các DÒNG chữ trên mặt nạ nét: góc chung (`goc_chieu`) → biểu đồ hàng đã chỉnh nghiêng → đoạn dòng (đoạn quá cao
    tách ở chỗ trũng); mỗi dòng (đủ dài, dẹt — đầu tròn trắng viền đen của nhân vật bị loại) đo góc riêng.
    [{goc, n, hop (hộp thẳng px bao dòng nghiêng), y0, y1 (trục chỉnh), x0, x1, goc_chung}]."""
    np = _np()
    H = net.shape[0]
    ys, xs = np.nonzero(net)
    if len(ys) < 200:
        return []
    ys, xs = ys.astype(np.float64), xs.astype(np.float64)
    g0 = goc_chieu(ys, xs) or 0.0
    t0 = math.tan(math.radians(g0))
    yp = ys + xs * t0
    dau = int(math.floor(yp.min()))
    prof = np.bincount(((np.floor(yp) - dau) // 2).astype(np.int64)).astype(np.float64)
    if len(prof) >= 5:
        prof = np.convolve(prof, np.ones(3) / 3.0, mode="same")
    doan: List[Tuple[int, int]] = []
    for a, b in _doan(prof, max(2.0, 0.12 * float(prof.max())), gop=2):
        doan += _tach(prof, a, b, 0.17 * H / 2.0)
    ra: List[Dict[str, Any]] = []
    for a, b in doan:
        y0, y1 = dau + 2.0 * a, dau + 2.0 * b
        chon = (yp >= y0) & (yp < y1)
        n = int(chon.sum())
        if n < 150:
            continue
        x0, x1 = float(np.percentile(xs[chon], 2)), float(np.percentile(xs[chon], 98))
        if x1 - x0 < 0.12 * W or (x1 - x0) < 2.2 * (y1 - y0):
            continue
        g = goc_chieu(ys[chon], xs[chon], buoc=0.25)
        # hộp thẳng (px) bao dòng nghiêng: y = yp − x·tan(g0)
        yy = [y0 - x0 * t0, y0 - x1 * t0, y1 - x0 * t0, y1 - x1 * t0]
        ra.append({"goc": round(float(g if g is not None else g0), 2), "n": n, "y0": y0, "y1": y1, "x0": x0,
                   "x1": x1, "goc_chung": round(g0, 2), "hop": [x0, max(0.0, min(yy)), x1, min(float(H), max(yy))]})
    return ra


def _mau_troi(px) -> Optional[Any]:
    """Màu trội rgb của các điểm `px` (N×3) — lượng tử 32 mức."""
    np = _np()
    if len(px) < 30:
        return None
    q = (px // 32).astype(np.int64)
    k = q[:, 0] * 64 + q[:, 1] * 8 + q[:, 2]
    return px[k == int(np.bincount(k).argmax())].mean(axis=0)


def dai_trong_hop(a, vung_chu, hop: Sequence[float], mau: Optional[Sequence[float]] = None,
                  cao: Optional[float] = None) -> Optional[float]:
    """Góc DẢI màu sau MỘT dòng chữ (hộp `hop`, px): màu dải (`mau` rgb đo sẵn, không có → màu trội quanh dòng ngoài
    chữ) → mặt nạ điểm gần màu ấy trong vùng quanh dòng (cao ± 0,45 dòng). Dải thật: phủ ≥ 60% bề dòng, đường bao
    TRÊN/DƯỚI nằm TRONG vùng (không phải nền một màu), cao 0,5–2 dòng → góc = trung bình hai đường bao. Không → None."""
    np = _np()
    H, W = vung_chu.shape
    x0, y0, x1, y1 = [float(v) for v in hop[:4]]
    h, w = max(4.0, float(cao) if cao else y1 - y0), max(4.0, x1 - x0)
    X0, X1 = int(max(0, x0 - 0.05 * w)), int(min(W, x1 + 0.05 * w))
    Y0, Y1 = int(max(0, y0 - 0.45 * h)), int(min(H, y1 + 0.45 * h))
    o = a[Y0:Y1, X0:X1].astype(np.float64)
    if o.size == 0:
        return None
    vc = vung_chu[Y0:Y1, X0:X1]
    tam = np.asarray(mau, dtype=np.float64) if mau is not None else _mau_troi(o[~vc])
    if tam is None:
        return None
    m = np.sqrt(((o - tam) ** 2).sum(axis=2)) < 55
    if mau is None and float(m[~vc].mean() if (~vc).any() else 0.0) < 0.3:
        return None
    ys, xs = np.nonzero(m)
    if len(ys) < 100:
        return None
    ox = (xs // 12).astype(np.int64)
    cot = [k for k in np.unique(ox) if int((ox == k).sum()) >= 0.2 * h]
    if len(cot) * 12 < 0.6 * w:
        return None
    tr = np.array([np.percentile(ys[ox == k], 3) for k in cot])
    du = np.array([np.percentile(ys[ox == k], 97) for k in cot])
    vh = Y1 - Y0
    if float(np.median(tr)) < 0.06 * h or float(np.median(du)) > vh - 0.06 * h:
        return None
    if not 0.5 * h <= float(np.median(du - tr)) <= 2.0 * h:
        return None
    # mép dải bị chữ CHE (dòng kề đè lên mép dải) không phải mép thật: chỉ lấy cột có mép giáp điểm KHÔNG phải chữ
    g = []
    for ds_y, huong in ((tr, -1), (du, 1)):
        xc, yv = [], []
        for k, yk in zip(cot, ds_y):
            c0, c1 = int(k * 12), int(min(vc.shape[1], k * 12 + 12))
            r0, r1 = (int(yk) - 5, int(yk) - 1) if huong < 0 else (int(yk) + 2, int(yk) + 6)
            r0, r1 = max(0, r0), min(vc.shape[0], r1)
            if r1 <= r0 or vc[r0:r1, c0:c1].any():
                continue
            xc.append(k * 12 + 6.0)
            yv.append(float(yk))
        if len(xc) >= 4 and xc[-1] - xc[0] >= 0.3 * w:
            d = _theil_sen(xc, yv, 36)
            if d is not None:
                g.append(-math.degrees(math.atan(d)))
    return float(sum(g) / len(g)) if g else None


# ── 2) ADN một bìa (máy) ────────────────────────────────────────────────────


def do_adn(nguon: Any) -> Dict[str, Any]:
    """ADN MÁY của một ảnh bìa (đường dẫn hoặc PIL). Xem docstring đầu tệp."""
    np = _np()
    from PIL import Image  # noqa: PLC0415
    im = _anh(nguon)
    a = np.asarray(im.resize(LUOI_CHU, Image.BOX)).astype(np.int16)
    net, vung = mat_na_chu(a)
    W, H = LUOI_CHU
    dong = dong_chu(net, W)
    goc_dai_ds: List[Tuple[float, float]] = []
    for d in dong:
        g = dai_trong_hop(a, vung, d["hop"], cao=d["y1"] - d["y0"])
        if g is not None and abs(g) <= GOC_TOI_DA:
            goc_dai_ds.append((g, float(d["n"])))
    gd = _trung_vi_ts(goc_dai_ds)
    n_dai = len(goc_dai_ds)
    # màu — lưới nhỏ, bỏ vùng chữ
    nho = im.resize(LUOI_MAU, Image.BOX)
    hsv = np.asarray(nho.convert("HSV")).astype(np.float64) / 255.0
    L = np.asarray(nho.convert("L")).astype(np.float64) / 255.0
    vung_nho = vung.reshape(LUOI_MAU[1], 2, LUOI_MAU[0], 2).any(axis=(1, 3))
    nen = ~vung_nho
    if nen.mean() < 0.2:  # gần như toàn chữ: đo cả ảnh
        nen = np.ones_like(nen)
    h, s, v = hsv[..., 0][nen], hsv[..., 1][nen], hsv[..., 2][nen]
    w = np.where((s >= 0.18) & (v >= 0.10), s * np.sqrt(v), 0.0)
    # chia mềm: tâm ô k ở sắc k × 30° (0° = đỏ) — điểm giữa hai tâm kề chia theo khoảng cách
    pos = (h * SO_O) % SO_O
    lo = np.floor(pos).astype(np.int64)
    f = pos - lo
    hist = np.zeros(SO_O)
    np.add.at(hist, lo % SO_O, w * (1.0 - f))
    np.add.at(hist, (lo + 1) % SO_O, w * f)
    sac = float(w.mean()) if w.size else 0.0
    hist = hist / hist.sum() if hist.sum() > 0 else np.full(SO_O, 1.0 / SO_O)
    Ln = L[nen]
    # chữ: phần trắng / vàng / đỏ trong nét
    o = a[net]
    if len(o):
        r, g, b = o[:, 0], o[:, 1], o[:, 2]
        trang = float(((o.min(axis=1)) >= 225).mean())
        do = float(((r >= 200) & (g <= 80) & (b <= 80)).mean())
        vang = float(((r >= 200) & (g >= 170) & (b <= 100) & (o.min(axis=1) < 225)).mean())
    else:
        trang = do = vang = 0.0
    goc_ds = [d["goc"] for d in dong]
    nn = [d["n"] for d in dong]
    gc = _trung_vi_ts(list(zip(goc_ds, nn))) if dong else None
    tn = float(sum(nn)) or 1.0
    duong = sum(n for g, n in zip(goc_ds, nn) if g >= GOC_THANG) / tn
    am = sum(n for g, n in zip(goc_ds, nn) if g <= -GOC_THANG) / tn
    nghieng = bool(dong) and max(duong, am) >= TI_DONG_NGHIENG
    if nghieng:  # góc của bìa = trung vị các dòng nghiêng cùng chiều
        gc = _trung_vi_ts([(g, n) for g, n in zip(goc_ds, nn) if (g >= GOC_THANG if duong >= am else g <= -GOC_THANG)])
    return {"nghieng": nghieng,"pb": PHIEN_BAN, "hue": [round(float(x), 4) for x in hist], "sac": round(sac, 4),
            "sang_nen": round(float(np.median(Ln)), 4) if Ln.size else None,
            "ti_toi": round(float((Ln < 0.25).mean()), 4) if Ln.size else None,
            "ti_sang": round(float((Ln > 0.75).mean()), 4) if Ln.size else None,
            "goc_chu": round(float(gc), 2) if gc is not None else None, "goc_dong": goc_ds, "so_dong": len(dong),
            "goc_dai": round(gd, 2) if gd is not None else None, "so_dai": n_dai,
            "ti_chu": round(float(vung.mean()), 4),
            "chu_mau": {"trang": round(trang, 3), "vang": round(vang, 3), "do": round(do, 3)}}


def _trung_vi_ts(cap: Sequence[Tuple[Any, float]]) -> Optional[float]:
    cap = sorted((float(v), max(0.0, float(w))) for v, w in cap if v is not None)
    tong = sum(w for _v, w in cap)
    if not cap or tong <= 0:
        return None
    dem = 0.0
    for v, w in cap:
        dem += w
        if dem >= tong / 2.0:
            return v
    return cap[-1][0]


def adn_tep(teps: Sequence[str], *, cache: str = "", cache_doc: Sequence[str] = (), ghi: bool = True
            ) -> Dict[str, Dict[str, Any]]:
    """ADN máy của các tệp `{tep: adn (+ sha1)}` — cache theo sha1 (`cache`; `cache_doc` chỉ đọc thêm). Tệp hỏng → bỏ."""
    kho = _doc_json(cache) if cache else None
    anh: Dict[str, Any] = dict((kho or {}).get("anh") or {}) if isinstance(kho, dict) else {}
    for c in cache_doc:
        du = _doc_json(c)
        for s, v in ((du or {}).get("anh") or {}).items() if isinstance(du, dict) else ():
            anh.setdefault(s, v)
    ra: Dict[str, Dict[str, Any]] = {}
    moi = 0
    for t in teps:
        if not t or not os.path.isfile(t):
            continue
        s = sha1_tep(t)
        x = anh.get(s)
        if not isinstance(x, dict) or x.get("pb") != PHIEN_BAN:
            try:
                x = do_adn(t)
            except Exception:  # noqa: BLE001 — ảnh hỏng: bỏ
                continue
            anh[s] = x
            moi += 1
        ra[t] = dict(x, sha1=s)
    if moi and cache and ghi:
        try:
            _ghi_json(cache, {"phien_ban": PHIEN_BAN, "anh": anh})
        except OSError:
            pass
    return ra


# ── 3) NHÌN (AI, một lượt / nhóm ảnh, ví ShopAPI) ───────────────────────────


def doc_nhin(du: Any, n: int) -> Dict[int, Dict[str, Any]]:
    ds = (du.get("bia") if isinstance(du, dict) else du) or []
    ra: Dict[int, Dict[str, Any]] = {}

    def chon(v: Any, cac: Sequence[str]) -> str:
        v = str(v or "").strip().lower()
        return v if v in cac else ""
    for x in ds if isinstance(ds, list) else []:
        try:
            so = int(x.get("so"))
        except (AttributeError, TypeError, ValueError):
            continue
        if not 1 <= so <= n or so in ra:
            continue
        nv = x.get("nhan_vat") if isinstance(x.get("nhan_vat"), dict) else {}
        mau = x.get("mau") if isinstance(x.get("mau"), list) else []
        ra[so] = {"anh_sang": chon(x.get("anh_sang"), ("dark", "medium", "bright")),
                  "kieu_sang": chon(x.get("kieu_sang"), ("spotlight", "glow", "even", "backlit", "none")),
                  "mau": [" ".join(str(m).split())[:24].lower() for m in mau if str(m).strip()][:4],
                  "bo_cuc_chu": chon(x.get("bo_cuc_chu"), ("straight", "tilted", "diagonal_bands", "stacked_bands",
                                                            "mixed")),
                  "nv_co": chon(nv.get("co"), ("small", "medium", "large")),
                  "nv_vi_tri": chon(nv.get("vi_tri"), ("left", "center", "right")),
                  "nv_tu_the": " ".join(str(nv.get("tu_the") or "").split())[:80],
                  "ta": " ".join(str(x.get("ta") or "").split())[:240]}
    return ra


def nhin(teps: Sequence[str], *, goi: Optional[Callable[..., str]], cache: str, cache_doc: Sequence[str] = (),
         log: Callable[[str], None] = print) -> Dict[str, Dict[str, Any]]:
    """Tả phong cách từng ảnh `{tep: {...}}` — cache theo sha1; ảnh chưa có + có `goi` → AI nhìn theo nhóm `NHOM_NHIN`
    ảnh / lượt, ép ví ShopAPI. Không `goi` / lượt hỏng → ảnh ấy không có tả (lần sau thử lại)."""
    kho = _doc_json(cache)
    anh: Dict[str, Any] = dict((kho or {}).get("anh") or {}) if isinstance(kho, dict) else {}
    for c in cache_doc:
        du = _doc_json(c)
        for s, v in ((du or {}).get("anh") or {}).items() if isinstance(du, dict) else ():
            anh.setdefault(s, v)
    sha = {t: sha1_tep(t) for t in teps if t and os.path.isfile(t)}
    thieu = list({s: t for t, s in sha.items() if s and s not in anh}.values())
    if goi is not None and thieu:
        from .bia_lo import _json, _url_anh  # noqa: PLC0415
        from .goi_van_ban import qua_vi  # noqa: PLC0415
        moi = 0
        for i in range(0, len(thieu), NHOM_NHIN):
            g = thieu[i:i + NHOM_NHIN]
            try:
                with qua_vi():
                    tho = goi(LOI_NHAC_NHIN.format(n=len(g)), khoa="bia-adn-v{0}:{1}".format(
                        PHIEN_BAN_NHIN, hashlib.sha1("|".join(sha[t] for t in g).encode()).hexdigest()[:16]),
                        toi_da_token=2400, mo_hinh=MO_HINH_NHIN, anh=[_url_anh(t, 512) for t in g])
                kq = doc_nhin(_json(tho), len(g))
            except Exception as loi:  # noqa: BLE001
                log("  (ADN bìa: AI nhìn phong cách hỏng: {0})".format(str(loi)[:160]))
                continue
            for j, t in enumerate(g, 1):
                if j in kq:
                    anh[sha[t]] = dict(kq[j], luc=time.strftime("%Y-%m-%d %H:%M:%S"), phien_ban=PHIEN_BAN_NHIN)
                    moi += 1
        if moi:
            _ghi_json(cache, {"phien_ban": PHIEN_BAN_NHIN, "anh": anh})
    return {t: dict(anh[s], sha1=s) for t, s in sha.items() if s in anh}


# ── 4) ADN kênh (tổng hợp bìa thắng) ────────────────────────────────────────


def _tb_hue(ds: Sequence[Tuple[Dict[str, Any], float]]) -> List[float]:
    tong = [0.0] * SO_O
    tw = sum(w for _d, w in ds) or 1.0
    for d, w in ds:
        for i, x in enumerate(d.get("hue") or [0.0] * SO_O):
            tong[i] += float(x) * w / tw
    s = sum(tong) or 1.0
    return [round(x / s, 4) for x in tong]


def ten_mau(hue: Sequence[float], toi: bool = False, n: int = 3) -> List[str]:
    """Tên các màu trội (ô ≥ 12% hoặc 2 ô đầu), ô kề gộp vào ô lớn hơn. `toi` → "deep …"."""
    xs = sorted(range(SO_O), key=lambda i: -float(hue[i]))
    chon: List[int] = []
    for i in xs:
        if len(chon) >= n or (float(hue[i]) < 0.12 and len(chon) >= 2):
            break
        if any(min(abs(i - j), SO_O - abs(i - j)) <= 1 for j in chon):
            continue
        chon.append(i)
    return [("deep " if toi and TEN_O[i] in ("violet purple", "blue", "magenta", "green", "teal", "red") else "")
            + TEN_O[i] for i in chon]


def tong_hop(ds: Sequence[Tuple[Dict[str, Any], float]], nhin_ds: Sequence[Tuple[Dict[str, Any], float]] = ()
             ) -> Dict[str, Any]:
    """ADN có trọng số (lượt bấm) của các bìa `[(adn, w)]` + ngưỡng tự hiệu chỉnh (xem docstring đầu tệp). Ít hơn 1
    bìa → {}."""
    ds = [(d, max(1.0, float(w or 1))) for d, w in ds if isinstance(d, dict) and d.get("hue")]
    if not ds:
        return {}
    hue = _tb_hue(ds)
    loo = []
    if len(ds) >= 2:
        for i, (d, _w) in enumerate(ds):
            con = [x for j, x in enumerate(ds) if j != i]
            loo.append(hellinger(d["hue"], _tb_hue(con)))
    tw = sum(w for _d, w in ds)
    du_cong = len(ds) >= SO_THANG_CONG and tw >= BAM_CONG
    sang = _trung_vi_ts([(d.get("sang_nen"), w) for d, w in ds])
    ti_toi_bia = sum(w for d, w in ds if d.get("sang_nen") is not None and float(d["sang_nen"]) < NEN_TOI) / tw
    toi = ti_toi_bia >= TI_TOI_KENH
    # nghiêng: bìa có các dòng nghiêng CÙNG chiều (`do_adn.nghieng`); góc = trung vị có trọng số của các bìa nghiêng
    # khi chúng đủ phần (`TI_VE`), không thì của mọi bìa
    nghieng = [(d.get("goc_chu"), w) for d, w in ds if d.get("nghieng") and d.get("goc_chu") is not None]
    ti_nghieng = sum(w for _g, w in nghieng) / tw
    goc_c = _trung_vi_ts(nghieng if ti_nghieng >= TI_VE else
                         [(d.get("goc_chu"), w) for d, w in ds if d.get("goc_chu") is not None])
    co_dai = [(d.get("goc_dai"), w) for d, w in ds if d.get("goc_dai") is not None]
    goc_d = _trung_vi_ts(co_dai)
    ra: Dict[str, Any] = {
        "n": len(ds), "hue": hue, "ten_mau": ten_mau(hue, toi=toi),
        "loo": [round(x, 3) for x in loo],
        "tong_bam": round(tw), "nguong_hue": round(max([HUE_NGUONG_SAN] + loo), 3) if du_cong else None,
        "sang_nen": round(sang, 3) if sang is not None else None,
        "ti_toi": round(sum(float(d.get("ti_toi") or 0) * w for d, w in ds) / tw, 3),
        "ti_bia_toi": round(ti_toi_bia, 3), "toi": toi,
        # kênh TỐI chặn cảnh KHÔNG tối: nền sáng hơn bìa thắng sáng nhất + `LE_SANG`, và không dưới ngưỡng "tối" `NEN_TOI`
        "nguong_sang": (round(max(NEN_TOI, max(float(d["sang_nen"]) for d, _w in ds if d.get("sang_nen") is not None)
                                  + LE_SANG), 3) if toi and du_cong else None),
        "goc_chu": round(goc_c, 2) if goc_c is not None else None, "ti_nghieng": round(ti_nghieng, 3),
        "goc_dai": round(goc_d, 2) if goc_d is not None else None,
        "ti_dai": round(sum(w for d, w in co_dai) / tw, 3),
        "chu_mau": {k: round(sum(float((d.get("chu_mau") or {}).get(k) or 0) * w for d, w in ds) / tw, 3)
                    for k in ("trang", "vang", "do")}}
    nh = [(x, max(1.0, float(w or 1))) for x, w in nhin_ds if isinstance(x, dict) and x]
    if nh:
        def phieu(k: str) -> str:
            dem: Dict[str, float] = {}
            for x, w in nh:
                if x.get(k):
                    dem[str(x[k])] = dem.get(str(x[k]), 0.0) + w
            return max(dem, key=lambda v: dem[v]) if dem else ""
        tu: Dict[str, float] = {}
        for x, w in nh:
            for i, m in enumerate(x.get("mau") or []):
                tu[m] = tu.get(m, 0.0) + w / (1.0 + i)
        ra["nhin"] = {"anh_sang": phieu("anh_sang"), "kieu_sang": phieu("kieu_sang"), "bo_cuc_chu": phieu("bo_cuc_chu"),
                      "nv_co": phieu("nv_co"), "nv_vi_tri": phieu("nv_vi_tri"),
                      "mau": [m for m, _v in sorted(tu.items(), key=lambda kv: -kv[1])][:4],
                      "ta": [x.get("ta") for x, _w in sorted(nh, key=lambda xw: -xw[1]) if x.get("ta")][:2]}
    return ra


def cau_lenh(adn: Optional[Dict[str, Any]]) -> str:
    """Câu ADN (tiếng Anh) cho lời nhắc ảnh nền / đạo diễn — '' khi chưa có ADN."""
    if not adn or not adn.get("hue"):
        return ""
    nh = adn.get("nhin") or {}
    toi = bool(adn.get("toi"))
    mau = list(dict.fromkeys((nh.get("mau") or [])[:3] + list(adn.get("ten_mau") or [])))[:4]
    sang = adn.get("sang_nen")
    if toi:
        nen = "a DARK scene (background brightness about {0:.0f}%, never a bright or warm daylight room)".format(
            100 * float(sang or 0.15))
    elif sang is not None and float(sang) > 0.6:
        nen = "a BRIGHT scene (background brightness about {0:.0f}%)".format(100 * float(sang))
    else:
        nen = "a medium-bright scene (background brightness about {0:.0f}%)".format(100 * float(sang or 0.45))
    sang_kieu = {"spotlight": "a spotlight / pool of light on the character" + (" in the dark" if toi else ""),
                 "glow": "a glowing aura and neon glow around the character",
                 "backlit": "strong backlight"}.get(str(nh.get("kieu_sang") or ""), "")
    cau = "STYLE DNA measured on this channel's real winning thumbnails — match it: palette dominated by {0}; {1}{2}.".format(
        ", ".join(mau) if mau else "the winners' colours", nen, ("; " + sang_kieu) if sang_kieu else "")
    if nh.get("ta"):
        cau += " Winner look: " + str(nh["ta"][0]).rstrip(".") + "."
    return cau


def ghi_chu_giam_khao(adn: Optional[Dict[str, Any]]) -> str:
    """Một mảnh cho mục `phong_cach` của giám khảo: ADN đo trên bìa thắng."""
    if not adn or not adn.get("hue"):
        return ""
    return "; the winners' measured style DNA: {0} palette, {1} scene{2}".format(
        " / ".join((adn.get("ten_mau") or [])[:3]) or "the same", "dark" if adn.get("toi") else (
            "bright" if float(adn.get("sang_nen") or 0.5) > 0.6 else "medium-bright"),
        ", tilted text/bands" if goc_ve(adn) else "")


def kiem(u_adn: Optional[Dict[str, Any]], adn: Optional[Dict[str, Any]], *, kham_pha: bool = False) -> List[str]:
    """CỔNG ADN: lý do tấm dưới sàn ADN ([] = đạt / chưa có cổng). Sắc lệch > `nguong_hue`; kênh TỐI mà nền tấm sáng
    hơn `nguong_sang` (ô khám phá A/B `kham_pha` được miễn sàn sáng)."""
    if not u_adn or not adn or not u_adn.get("hue"):
        return []
    ly: List[str] = []
    ng = adn.get("nguong_hue")
    if ng is not None:
        d = hellinger(u_adn["hue"], adn["hue"])
        if d > float(ng):
            ly.append("bảng màu lệch bìa thắng (khoảng cách sắc {0:.2f} > {1:.2f}; bìa thắng: {2}; tấm này: {3})".format(
                d, float(ng), ", ".join(adn.get("ten_mau") or []), ", ".join(ten_mau(u_adn["hue"], n=2))))
    ns = adn.get("nguong_sang")
    if ns is not None and not kham_pha and u_adn.get("sang_nen") is not None and float(u_adn["sang_nen"]) > float(ns):
        ly.append("cảnh sáng hơn bìa thắng (nền {0:.0%} > {1:.0%} — kênh thắng bằng nền tối)".format(
            float(u_adn["sang_nen"]), float(ns)))
    return ly


def tom_tat(u_adn: Optional[Dict[str, Any]], adn: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Bản gọn của ADN một tấm (sổ kết quả / A/B): khoảng cách sắc tới ADN kênh, độ sáng nền, phần tối, góc."""
    if not u_adn:
        return {}
    ra = {k: u_adn.get(k) for k in ("sang_nen", "ti_toi", "goc_chu", "goc_dai", "so_dong", "so_dai")}
    ra["mau"] = ten_mau(u_adn.get("hue") or [0.0] * SO_O, n=2)
    if adn and adn.get("hue") and u_adn.get("hue"):
        ra["kc_hue"] = hellinger(u_adn["hue"], adn["hue"])
    return ra


def goc_ve(adn_ho: Optional[Dict[str, Any]], adn_kenh: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """Góc VẼ cho bộ vẽ chữ theo ADN của HỌ (lùi ADN kênh): {nghieng (dòng chữ), nghieng_dai (dải)} — chỉ khi ≥ `TI_VE`
    trọng số bìa thắng nghiêng (≥ `GOC_THANG`) / có dải, kẹp ±`GOC_VE_TOI_DA`. {} = vẽ thẳng."""
    a = adn_ho if adn_ho and adn_ho.get("n") else (adn_kenh or {})
    ra: Dict[str, float] = {}
    gc = a.get("goc_chu")
    if gc is not None and abs(float(gc)) >= GOC_THANG and float(a.get("ti_nghieng") or 0) >= TI_VE:
        ra["nghieng"] = round(max(-GOC_VE_TOI_DA, min(GOC_VE_TOI_DA, float(gc))), 2)
    # dải đi CÙNG dòng chữ nó mang khi chữ nghiêng (bìa thắng TL2 #1: chữ 8,25°, dải 9,5°; TL4 #1 hộp nghiêng theo chữ —
    # dải cùng màu xếp chồng làm số đo mép dải lẫn); chữ thẳng mà dải nghiêng → góc dải đo được
    gd = ra.get("nghieng") if ra.get("nghieng") is not None else a.get("goc_dai")
    if gd is not None and abs(float(gd)) >= GOC_THANG and (ra.get("nghieng") is not None
                                                          or float(a.get("ti_dai") or 0) >= TI_VE):
        ra["nghieng_dai"] = round(max(-GOC_VE_TOI_DA, min(GOC_VE_TOI_DA, float(gd))), 2)
    return ra


# ── 5) ADN của thư mục bìa thắng ────────────────────────────────────────────


def _bia_thang(tm: str) -> List[Dict[str, Any]]:
    du = _doc_json(os.path.join(tm, "thang.json")) if tm else None
    ra = []
    for b in ((du or {}).get("bia") or []) if isinstance(du, dict) else []:
        if isinstance(b, dict) and b.get("tep") and os.path.isfile(os.path.join(tm, str(b["tep"]))):
            ra.append(dict(b, _duong=os.path.join(tm, str(b["tep"]))))
    if not ra and tm and os.path.isdir(tm):  # thư mục không có thang.json: mọi ảnh, trọng số đều
        ra = [{"tep": t, "_duong": os.path.join(tm, t)} for t in sorted(os.listdir(tm)) if t.lower().endswith(_DUOI_ANH)]
    return ra


def _trong_so(b: Dict[str, Any]) -> float:
    try:
        return max(1.0, float(b.get("imp") or 0) * float(b.get("ctr") or 0) / 100.0)
    except (TypeError, ValueError):
        return 1.0


def adn_thu_muc(tm: str, *, goc: str = "", ghi: bool = True, cache_doc: Sequence[str] = (),
                bo: Sequence[str] = ()) -> Dict[str, Any]:
    """ADN của thư mục bìa thắng `tm` → {kenh: ADN tổng hợp, ho: {họ: ADN}, bia: [{tep, video_id, w, kieu, adn}]}.
    Cache tổng hợp `<tm>/adn-thang.json` theo (sha1, trọng số, phiên bản) — bộ bìa thắng đổi (D21) thì tự đo lại; ADN
    từng ảnh cache chung `workspace/bia-kieu/adn.json`. `bo` = tệp loại khỏi tổng hợp (bìa thắng giấu / bỏ-một-ra).
    `ghi=False`: không ghi gì (chạy thử). Không có ảnh → {}."""
    bia = [b for b in _bia_thang(tm) if os.path.abspath(b["_duong"]) not in {os.path.abspath(x) for x in bo}]
    if not bia:
        return {}
    cache = os.path.join(goc, TEP_CACHE) if goc else ""
    do = adn_tep([b["_duong"] for b in bia], cache=cache if ghi else "", cache_doc=list(cache_doc) + (
        [cache] if cache and not ghi else []), ghi=ghi)
    khoa = hashlib.sha1(json.dumps([[(do.get(b["_duong"]) or {}).get("sha1"), round(_trong_so(b)), b.get("kieu")]
                                    for b in bia] + [PHIEN_BAN, PHIEN_BAN_NHIN], sort_keys=True).encode()).hexdigest()
    duong = os.path.join(tm, TEP_THANG)
    cu = _doc_json(duong)
    nh_cache = os.path.join(goc, TEP_NHIN) if goc else ""
    nh = nhin([b["_duong"] for b in bia], goi=None, cache=nh_cache, cache_doc=cache_doc) if nh_cache else {}
    khoa += ":" + str(len(nh))
    if not bo and isinstance(cu, dict) and cu.get("khoa") == khoa and cu.get("kenh"):
        return cu
    ds = [(b, do.get(b["_duong"])) for b in bia if do.get(b["_duong"])]
    ra: Dict[str, Any] = {"khoa": khoa, "phien_ban": PHIEN_BAN, "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "kenh": tong_hop([(d, _trong_so(b)) for b, d in ds],
                                           [(nh.get(b["_duong"]) or {}, _trong_so(b)) for b, _d in ds]),
                          "ho": {}, "bia": [{"tep": b["tep"], "video_id": b.get("video_id") or "", "w": round(
                              _trong_so(b)), "kieu": b.get("kieu") or "", "adn": tom_tat(d)} for b, d in ds]}
    for h in sorted({str(b.get("kieu") or "") for b, _d in ds} - {""}):
        cung = [(b, d) for b, d in ds if b.get("kieu") == h]
        ra["ho"][h] = tong_hop([(d, _trong_so(b)) for b, d in cung],
                               [(nh.get(b["_duong"]) or {}, _trong_so(b)) for b, _d in cung])
    if ghi and not bo:
        try:
            _ghi_json(duong, ra)
        except OSError:
            pass
    return ra


def adn_ho(adn_tm: Dict[str, Any], ho: str) -> Dict[str, Any]:
    """ADN của HỌ `ho` trong ADN thư mục (chưa có → {})."""
    return dict(((adn_tm or {}).get("ho") or {}).get(ho) or {})


# ── 6) Vòng học: ADN mọi video đủ chín của kênh (D21) ───────────────────────


def ghi_adn_kenh(goc: str, kenh: str, video: Dict[str, Dict[str, Any]], adn_kenh: Dict[str, Any], *,
                 ghi: bool = True) -> Dict[str, Any]:
    """`nghien-cuu/bia-adn.json`: ADN kênh (đích) + bản gọn ADN từng video đủ chín {imp, ctr, may, adn}. Trả nội dung."""
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415
    du = {"kenh": kenh, "phien_ban": PHIEN_BAN, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "dich": adn_kenh,
          "video": video}
    if ghi:
        _ghi_json(os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_KENH), du)
    return du


def doc_adn_kenh(goc: str, kenh: str) -> Dict[str, Any]:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415
    du = _doc_json(os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP_KENH))
    return du if isinstance(du, dict) else {}


DAC_TRUNG = ("kc_hue", "sang_nen", "ti_toi", "abs_goc_chu", "abs_goc_dai")


def _dac(x: Dict[str, Any], k: str) -> Optional[float]:
    if k.startswith("abs_"):
        v = x.get(k[4:])
        return abs(float(v)) if isinstance(v, (int, float)) else (0.0 if k == "abs_goc_dai" and "goc_dai" in x else None)
    v = x.get(k)
    return float(v) if isinstance(v, (int, float)) else None


def tuong_quan_ctr(du: Dict[str, Any], spearman: Callable[..., Optional[float]]) -> Dict[str, Any]:
    """Spearman (trọng số √hiển thị) giữa từng đặc trưng ADN và CTR trên video đủ chín của kênh (`bia-adn.json`)."""
    vs = [v for v in (du.get("video") or {}).values() if isinstance(v, dict) and isinstance(v.get("ctr"), (int, float))
          and float(v.get("imp") or 0) >= 1000 and isinstance(v.get("adn"), dict)]
    ra: Dict[str, Any] = {"n": len(vs)}
    for k in DAC_TRUNG:
        cap = [(_dac(v["adn"], k), float(v["ctr"]), math.sqrt(float(v["imp"]))) for v in vs]
        cap = [c for c in cap if c[0] is not None]
        ra[k] = {"n": len(cap), "rho": spearman([c[0] for c in cap], [c[1] for c in cap], [c[2] for c in cap])}
    return ra


def ab_gan_adn(goc: str, kenh: str, adn_kenh: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Thử nghiệm A/B đã xong của kênh: phần cặp (thắng, thua) mà nhánh thắng GẦN ADN kênh hơn (khoảng cách sắc) —
    > 0,5 = gần ADN thắng thật. ADN nhánh: bản ghi sổ (`adn`), không có thì đo tệp."""
    try:
        from . import bia_ab  # noqa: PLC0415
        ds = bia_ab.doc_so(goc, kenh)
    except Exception:  # noqa: BLE001
        return {"n": 0}
    dich = adn_kenh if adn_kenh is not None else (doc_adn_kenh(goc, kenh).get("dich") or {})
    if not dich.get("hue"):
        return {"n": 0}
    gan = tong = 0.0
    n = 0
    for m in ds:
        kc: Dict[str, float] = {}
        for b in m.get("bien_the") or []:
            x = b.get("adn") if isinstance(b.get("adn"), dict) else {}
            if x.get("kc_hue") is None and b.get("tep") and os.path.isfile(str(b["tep"])):
                try:
                    x = tom_tat(do_adn(str(b["tep"])), dich)
                except Exception:  # noqa: BLE001
                    x = {}
            if x.get("kc_hue") is not None:
                kc[str(b.get("nhan"))] = float(x["kc_hue"])
        for c in bia_ab.cap_ab(m):
            a, b = kc.get(c["thang"]), kc.get(c["thua"])
            if a is None or b is None or abs(a - b) < 1e-6:
                continue
            tong += c["w"]
            gan += c["w"] if a < b else 0.0
            n += 1
    return {"n": n, "ti_gan_thang": round(gan / tong, 3) if tong else None}


# ── 7) Chạy thử (CHỈ ĐỌC) ───────────────────────────────────────────────────


def _bia_may_gan(goc: str, kenh: str, so: int) -> List[Dict[str, Any]]:
    """`so` bìa máy mới nhất của kênh: ảnh THẬT đang chạy (`-that.jpg`), chưa có thì bìa của hồ sơ (`<mã>.jpg`)."""
    from . import bia_du_lieu, khuon_bia  # noqa: PLC0415
    from .ho_so_video import duong_thu_muc_ho_so  # noqa: PLC0415
    rows = bia_du_lieu.doc_bang(goc, kenh)
    may = bia_du_lieu.video_may(goc, kenh)
    ds = sorted((r for r in rows if r["video_id"] in may), key=lambda r: r["ngay"], reverse=True)[:so]
    ra = []
    for r in ds:
        p = khuon_bia.duong_anh_that(goc, kenh, r["video_id"])
        if not os.path.isfile(p):
            p = os.path.join(duong_thu_muc_ho_so(goc, kenh), "anh", may[r["video_id"]]["ma_goi"] + ".jpg")
        ra.append(dict(r, tep=p if os.path.isfile(p) else "", luot=may[r["video_id"]]["luot"]))
    return ra


def chay_thu(goc: str, kenh: str, *, so: int = 6, goi: Optional[Callable[..., str]] = None, tam: str = "",
             in_ra: Callable[[str], None] = print) -> Dict[str, Any]:
    """In ADN bìa thắng + chấm `so` bìa máy mới nhất theo cổng ADN. Bìa máy cũng là bìa thắng → so với ADN BỎ-MỘT-RA.
    Không ghi gì ngoài `tam` (cache)."""
    from . import bia_lo  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    tam = tam or tempfile.mkdtemp(prefix="adn-bia-")
    tm = bia_lo.thu_muc_mau(goc, kenh) or ""
    cache_doc = [os.path.join(goc, TEP_CACHE)]
    bia = _bia_thang(tm)
    teps = [b["_duong"] for b in bia]
    do = adn_tep(teps, cache=os.path.join(tam, "adn.json"), cache_doc=cache_doc)
    if goi is not None:
        nhin(teps, goi=goi, cache=os.path.join(tam, "adn-nhin.json"), cache_doc=[os.path.join(goc, TEP_NHIN)])
    nh = nhin(teps, goi=None, cache=os.path.join(tam, "adn-nhin.json"), cache_doc=[os.path.join(goc, TEP_NHIN)])
    ds = [(b, do[b["_duong"]]) for b in bia if b["_duong"] in do]
    dich = tong_hop([(d, _trong_so(b)) for b, d in ds], [(nh.get(b["_duong"]) or {}, _trong_so(b)) for b, _d in ds])
    bc: Dict[str, Any] = {"kenh": kenh, "thu_muc": tm, "dich": dich, "thang": [], "may": []}
    in_ra("== {0}: thư mục bìa thắng {1} ({2} bìa)".format(kenh, tm, len(ds)))
    for b, d in ds:
        nb = nh.get(b["_duong"]) or {}
        bc["thang"].append({"tep": b["tep"], "w": round(_trong_so(b)), "kieu": b.get("kieu"), "adn": tom_tat(d, dich)})
        in_ra("  thắng {0:<22} bấm {1:>6} họ {2:<4} màu {3:<28} nền {4:.2f} tối {5:.2f} góc chữ {6} (dòng {7}) dải {8}{9}"
              .format(b["tep"][:22], round(_trong_so(b)), b.get("kieu") or "-", "/".join(ten_mau(d["hue"], n=2)),
                      d["sang_nen"], d["ti_toi"], d["goc_chu"], d["goc_dong"], d["goc_dai"],
                      " | AI: {0} {1} {2}".format(nb.get("anh_sang"), nb.get("kieu_sang"), nb.get("bo_cuc_chu"))
                      if nb else ""))
    in_ra("  ADN kênh: màu {0} | nền trung vị {1} | kênh tối {2} (phần bìa tối {3}) | góc chữ {4} (phần nghiêng {5}) | "
          "góc dải {6} (phần có dải {7})".format(dich.get("ten_mau"), dich.get("sang_nen"), dich.get("toi"),
                                                dich.get("ti_bia_toi"), dich.get("goc_chu"), dich.get("ti_nghieng"),
                                                dich.get("goc_dai"), dich.get("ti_dai")))
    in_ra("  ngưỡng: sắc ≤ {0} (bỏ-một-ra {1}) | nền ≤ {2} | góc vẽ {3}".format(
        dich.get("nguong_hue"), dich.get("loo"), dich.get("nguong_sang"), goc_ve(None, dich)))
    for ho, x in sorted(adn_theo_ho(ds).items()):
        in_ra("  họ {0}: n={1} màu {2} góc chữ {3} góc dải {4} → vẽ {5}".format(
            ho, x.get("n"), x.get("ten_mau"), x.get("goc_chu"), x.get("goc_dai"), goc_ve(x, dich)))
    if nh:
        in_ra("  AI nhìn: {0}".format(json.dumps(dich.get("nhin") or {}, ensure_ascii=False)[:400]))
    in_ra("  câu ADN: " + cau_lenh(dich))
    sha_thang = {d.get("sha1"): b for b, d in ds}
    vid_thang = {str(b.get("video_id") or ""): b for b, _d in ds}
    for r in _bia_may_gan(goc, kenh, so):
        if not r["tep"]:
            in_ra("  máy {0} {1}: không có ảnh".format(r["ngay"], r["luot"]))
            continue
        d = adn_tep([r["tep"]], cache=os.path.join(tam, "adn.json"), cache_doc=cache_doc)[r["tep"]]
        la_thang = d.get("sha1") in sha_thang or r["video_id"] in vid_thang
        if la_thang:
            con = [(dd, _trong_so(b)) for b, dd in ds if dd.get("sha1") != d.get("sha1")
                   and str(b.get("video_id") or "") != r["video_id"]]
            so_voi = tong_hop(con)
        else:
            so_voi = dich
        so_voi = dict(so_voi, nguong_hue=dich.get("nguong_hue"), nguong_sang=dich.get("nguong_sang"))
        ly = kiem(d, so_voi)
        kc = hellinger(d["hue"], so_voi["hue"]) if so_voi.get("hue") else None
        bc["may"].append({"ngay": r["ngay"], "luot": r["luot"], "imp": r["imp"], "ctr": r["ctr"], "thang": la_thang,
                          "adn": tom_tat(d, so_voi), "ly": ly})
        in_ra("  máy {0} lượt {1} imp {2:>6} CTR {3:>5}%{4} màu {5:<26} kc sắc {6} nền {7:.2f} góc chữ {8} dải {9} → {10}"
              .format(r["ngay"], r["luot"], int(r["imp"]), r["ctr"], " (thắng, so bỏ-một-ra)" if la_thang else "",
                      "/".join(ten_mau(d["hue"], n=2)), kc, d["sang_nen"], d["goc_chu"], d["goc_dai"],
                      "TRƯỢT: " + "; ".join(ly) if ly else "ĐẠT"))
    return bc


def adn_theo_ho(ds: Sequence[Tuple[Dict[str, Any], Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    ra = {}
    for h in sorted({str(b.get("kieu") or "") for b, _d in ds} - {""}):
        ra[h] = tong_hop([(d, _trong_so(b)) for b, d in ds if b.get("kieu") == h])
    return ra


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(k, "1")
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.adn_bia", description="ADN phong cách bìa (chạy thử).")
    p.add_argument("lenh", choices=("thu",))
    p.add_argument("--kenh", action="append", required=True)
    p.add_argument("--so", type=int, default=6)
    p.add_argument("--khong-ai", action="store_true")
    p.add_argument("--tam", default="")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    goi = None
    if not a.khong_ai:
        from .bia_lo import _goi_that  # noqa: PLC0415
        goi = _goi_that(goc, print)
    loi = 0
    for k in a.kenh:
        try:
            chay_thu(goc, k, so=a.so, goi=goi, tam=os.path.abspath(a.tam) if a.tam else "")
        except Exception as e:  # noqa: BLE001
            loi += 1
            print("== {0}: HỎNG {1}".format(k, str(e)[:300]))
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(main())
