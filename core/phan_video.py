"""Dựng theo PHẦN — nghỉ 3 giây, chuyển cảnh, SRT sạch, mục lục đồng bộ.

═══ VIỆC 2 CỦA `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`, duyệt 28/09/2026 ═══

Chủ kênh đang phải sửa TAY mọi video bằng CapCut: mỗi phần (chương) một
khoảng nghỉ ~3 giây có hiệu ứng tối dần/sáng dần, mỗi phần một nhạc nền cố
định −18 dB dưới giọng, sang phần mới thì đổi nhạc và im ~2 giây. Tệp này là
phần THUẦN (tính toán, không Qt, không mạng) của việc đó; `core/auto_khau.py`
(`_khau_dung`, `_ghep_video`) gọi vào đây, `core/kho_nhac.py` lo phần nhạc.

═══ MỐC THỜI GIAN — HAI TRỤC ═══

* Trục GIỌNG GỐC: `2-giong-doc.mp3` đúng như khâu giọng đã ghép. Ranh giới
  phần k có `a_k` (hết lời phần trước) và `b_k` (giọng vào lại), đo bằng
  `silencedetect` chứ không tin mốc SRT (bộ ép phụ đề hay đặt câu đầu phần
  ngay ĐẦU khoảng lặng — lỗi thật TL3/0004: 93,76 thay vì 95,12).
* Trục VIDEO: lượt cũ nghỉ 1,2 giây, muốn 3 giây thì CHÈN THÊM lặng
  `e_k = max(0, P − (b_k − a_k))` vào ĐÚNG GIỮA khoảng nghỉ `m_k`. Mọi mốc
  giọng gốc đổi sang mốc video bằng `f(t) = t + Σ_{m_k ≤ t} e_k`.

Lượt mới (giọng đã nghỉ 3 giây sẵn) thì mọi `e_k = 0`, `f` là hàm đồng nhất
— cùng một đường code cho cả lượt cũ lẫn lượt mới.

═══ KHÔNG BAO GIỜ LÀM HỎNG KHÂU DỰNG ═══

Mọi hàm ở đây hoặc thuần, hoặc chỉ đọc; nơi gọi (`auto_khau._khau_dung`)
bọc toàn bộ trong try/except và lùi về dựng như cũ khi có bất cứ lỗi gì
(thiết kế mục (i)).
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "RanhGioi", "KeHoach", "doc_lang", "do_lang", "bam_lang", "tim_phan",
    "bang_bu", "lap_ke_hoach", "ke_hoach_tu_json", "loc_giong_bu_nghi",
    "bo_tien_to_ngat", "sach_srt", "ghi_srt_sach", "ghep_nhan", "muc_luc",
    "dat_muc_luc_seo", "xep_canh", "khung_nhac", "cam_xuc_phan",
    "do_lufs_giong", "ghi_phan_giong",
]

TEN_PHAN_GIONG = "2-phan.json"
TEN_PHAN_DUNG = "8-phan.json"
TEN_SRT_SACH = "8-phu-de.srt"
TEN_NHAC_NEN = "8-nhac-nen.m4a"
TEN_NHAC_JSON = "8-nhac.json"

#: Ngưỡng lặng của thiết kế: `silencedetect=n=-40dB:d=0.8`.
NGUONG_LANG_DB = -40
GIAY_LANG_TOI_THIEU = 0.8
#: Ứng viên ranh giới (mốc SRT/cộng dồn đoạn) chỉ được bám về một khoảng lặng
#: cách nó không quá bấy nhiêu giây.
CUA_BAM = 2.5
#: Giọng nghỉ ≥ ngần này giây (lượt mới, `giay_nghi_phan: 3.0`) thì MỌI khoảng
#: lặng ≥ 0,8 × nghỉ đều là ranh giới — nhịp nghỉ tự nhiên giữa câu của giọng
#: giọng đọc đo trên TL3/0004 chỉ 0,8–1,9 giây, không lẫn được với 2,4.
GIAY_NGHI_TU_NHAN = 2.5

#: Tiền tố dấu ngắt phần còn dính trong SRT: "--- ユングは、" (lỗi thật (a)).
_RE_TIEN_TO_NGAT = re.compile(r"^\s*[-—–_*]{3,}\s*")


# ── Dữ liệu ─────────────────────────────────────────────────────────────────


@dataclass
class RanhGioi:
    """Ranh giới giữa phần k và phần k+1, trên trục GIỌNG GỐC."""

    a: float            # hết lời phần trước
    b: float            # giọng vào lại
    nguon: str = ""

    @property
    def m(self) -> float:
        return (self.a + self.b) / 2.0


@dataclass
class KeHoach:
    """Mọi mốc của một video dựng theo phần.

    `ranh[k]`/`bu[k]` đi cặp; `nhan[k]` là nhãn phần k (k = 0…len(ranh)).
    """

    tong_giong: float
    ranh: List[RanhGioi] = field(default_factory=list)
    bu: List[float] = field(default_factory=list)
    giay_nghi: float = 3.0
    nguon: str = ""
    nhan: List[str] = field(default_factory=list)

    # f(t) = t + Σ_{m_k ≤ t} e_k
    def f(self, t: float) -> float:
        them = 0.0
        for r, e in zip(self.ranh, self.bu):
            if r.m <= t:
                them += e
        return float(t) + them

    def a2(self, k: int) -> float:
        return self.f(self.ranh[k].a)

    def b2(self, k: int) -> float:
        return self.f(self.ranh[k].b)

    def m2(self, k: int) -> float:
        """Giữa khoảng nghỉ trên trục VIDEO — điểm tối nhất của chuyển cảnh,
        và là mốc mục lục của chương k+1."""
        return (self.a2(k) + self.b2(k)) / 2.0

    @property
    def tong_bu(self) -> float:
        return float(sum(self.bu))

    @property
    def tong_moi(self) -> float:
        return self.tong_giong + self.tong_bu

    @property
    def so_phan(self) -> int:
        return len(self.ranh) + 1

    def phan_moi(self) -> List[Dict[str, float]]:
        """Từng phần trên trục video: `bat_dau` = giọng vào, `het_loi` = hết lời."""
        ra = []
        for k in range(self.so_phan):
            bd = 0.0 if k == 0 else self.b2(k - 1)
            hl = self.tong_moi if k == len(self.ranh) else self.a2(k)
            ra.append({"so": k + 1, "bat_dau": round(bd, 3), "het_loi": round(hl, 3)})
        return ra

    def khong_bu(self) -> "KeHoach":
        """Bản sao y hệt nhưng không chèn lặng — dùng khi lùi về dựng như cũ."""
        return KeHoach(tong_giong=self.tong_giong, ranh=list(self.ranh),
                       bu=[0.0] * len(self.ranh), giay_nghi=self.giay_nghi,
                       nguon=self.nguon, nhan=list(self.nhan))

    def to_dict(self) -> Dict[str, Any]:
        ranh = []
        for k, r in enumerate(self.ranh):
            ranh.append({"a": round(r.a, 3), "b": round(r.b, 3), "m": round(r.m, 3),
                         "bu": round(self.bu[k], 3), "a_moi": round(self.a2(k), 3),
                         "b_moi": round(self.b2(k), 3), "m_moi": round(self.m2(k), 3),
                         "nguon": r.nguon})
        phan = self.phan_moi()
        for k, p in enumerate(phan):
            p["nhan"] = self.nhan[k] if k < len(self.nhan) else ""
        return {"giay_nghi": self.giay_nghi, "nguon": self.nguon,
                "tong_giong": round(self.tong_giong, 3),
                "tong_bu": round(self.tong_bu, 3),
                "tong_video": round(self.tong_moi, 3),
                "ranh": ranh, "phan": phan}


# ── Đo lặng thật (silencedetect) ────────────────────────────────────────────


def _co_tao() -> int:
    """Ưu tiên THẤP + không cửa sổ đen — máy đang sản xuất thật."""
    return (getattr(subprocess, "IDLE_PRIORITY_CLASS", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _chay(cmd: Sequence[str], timeout: float = 600.0) -> str:
    try:
        ra = subprocess.run(list(cmd), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout,
                            creationflags=_co_tao())
    except (OSError, subprocess.SubprocessError):
        return ""
    return ra.stderr or ""


_RE_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_RE_LANG_BD = re.compile(r"silence_start:\s*(-?[0-9.]+)")
_RE_LANG_KT = re.compile(r"silence_end:\s*(-?[0-9.]+)")


def _do_dai(stderr: str) -> float:
    m = _RE_DURATION.search(stderr or "")
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def doc_lang(stderr: str, tong: float = 0.0) -> List[Tuple[float, float]]:
    """Các khoảng lặng `(bắt đầu, kết thúc)` từ stderr của `silencedetect` (THUẦN).

    Lặng kéo tới hết tệp thì `silencedetect` chỉ in `silence_start` — lấy
    `tong` làm mép cuối (không có `tong` thì bỏ khoảng đó).
    """
    ra: List[Tuple[float, float]] = []
    dang: Optional[float] = None
    for dong in (stderr or "").splitlines():
        m = _RE_LANG_BD.search(dong)
        if m:
            dang = max(0.0, float(m.group(1)))
            continue
        m = _RE_LANG_KT.search(dong)
        if m and dang is not None:
            ra.append((dang, float(m.group(1))))
            dang = None
    if dang is not None and tong > dang:
        ra.append((dang, tong))
    return ra


def do_lang(ffmpeg: str, tep: str, nguong_db: float = NGUONG_LANG_DB,
            toi_thieu: float = GIAY_LANG_TOI_THIEU) -> Tuple[List[Tuple[float, float]], float]:
    """Chạy `silencedetect` thật trên một tệp tiếng. Trả `(các lặng, độ dài)`."""
    text = _chay([ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-i", tep,
                  "-af", "silencedetect=n={0}dB:d={1}".format(nguong_db, toi_thieu),
                  "-threads", "1", "-f", "null", "-"])
    tong = _do_dai(text)
    return doc_lang(text, tong), tong


def bam_lang(ung_vien: float, cac_lang: Sequence[Tuple[float, float]],
             cua: float = CUA_BAM) -> Optional[Tuple[float, float]]:
    """Khoảng lặng thật gần `ung_vien` nhất (THUẦN), trong cửa `±cua` giây.

    "Gần" = khoảng cách từ mốc tới MÉP khoảng lặng (nằm trong thì bằng 0),
    hoà thì lấy khoảng dài hơn. KHÔNG lấy "dài nhất trong cửa": đo TL3/0004,
    nhịp nghỉ tự nhiên giữa câu (0,8–1,9 giây) còn DÀI HƠN nhịp nghỉ phần cũ
    (1,2 giây) — chọn dài nhất là bám nhầm sang câu bên cạnh.
    """
    tot = None
    for bd, kt in cac_lang:
        if kt < ung_vien - cua or bd > ung_vien + cua:
            continue
        xa = 0.0 if bd <= ung_vien <= kt else min(abs(ung_vien - bd), abs(ung_vien - kt))
        khoa = (xa, -(kt - bd))
        if tot is None or khoa < tot[0]:
            tot = (khoa, (bd, kt))
    return tot[1] if tot else None


def _ranh_tu_ung_vien(ung_vien: Sequence[float], cac_lang: Sequence[Tuple[float, float]],
                      tong: float, giay_nghi: float, nguon: str,
                      ghi: Callable[[str], None]) -> List[RanhGioi]:
    """Bám từng ứng viên về lặng thật, bỏ trùng, cộng lặng dài (giọng nghỉ ≥2,5s)."""
    da: Dict[Tuple[float, float], RanhGioi] = {}
    for c in ung_vien:
        lang = bam_lang(c, cac_lang)
        if lang is None:
            ghi("    (ranh giới ~{0:.1f}s: không thấy khoảng lặng thật trong ±{1}s — "
                "bỏ ranh giới này)".format(c, CUA_BAM))
            continue
        da.setdefault(lang, RanhGioi(lang[0], lang[1], nguon))
    if giay_nghi >= GIAY_NGHI_TU_NHAN:
        for bd, kt in cac_lang:
            if kt - bd >= 0.8 * giay_nghi and (bd, kt) not in da:
                da[(bd, kt)] = RanhGioi(bd, kt, "lang-dai")
    ra = []
    for r in sorted(da.values(), key=lambda x: x.a):
        # Lặng dính đầu/cuối tệp không phải ranh giới giữa hai phần.
        if r.a < 0.5 or (tong > 0 and r.b > tong - 0.5):
            continue
        ra.append(r)
    return ra


# ── Ứng viên ranh giới: 2-phan.json → SRT `---` → cộng dồn 2-doan ──────────


def ung_vien_tu_srt(srt: str) -> List[float]:
    """Mốc bắt đầu các câu SRT còn tiền tố `---` (THUẦN)."""
    from .phu_de import doc_srt  # noqa: PLC0415

    return [c.bat_dau for c in doc_srt(srt) if _RE_TIEN_TO_NGAT.match(c.chu)]


def _dai_tep(ffmpeg: str, tep: str) -> float:
    return _do_dai(_chay([ffmpeg, "-hide_banner", "-nostdin", "-i", tep], timeout=60))


def ung_vien_tu_doan(thu_muc: str, ffmpeg: str) -> List[float]:
    """Mốc hết từng PHẦN theo cộng dồn `2-doan/NNN.mp3` + lặng đã chèn.

    Cấu trúc (đoạn nào là cuối phần) tính lại từ chính bản đã đem đọc
    (`1-kich-ban-the.txt` nếu có, không thì `1-kich-ban.txt`) bằng
    `auto_khau.chia_doan_va_nghi`; số đoạn phải khớp số tệp mp3, lệch thì
    không đoán (trả rỗng). Độ dài lặng lấy từ chính tệp `_im-lang-*ms.mp3`
    trong `2-doan/` (mp3 đệm khung nên 1200ms thực là ~1,23s).
    """
    from .auto_khau import chia_doan_va_nghi, GIAY_NGHI_GIUA_KHUC  # noqa: PLC0415

    thu_doan = os.path.join(thu_muc, "2-doan")
    try:
        ten = sorted(t for t in os.listdir(thu_doan)
                     if re.fullmatch(r"\d{3}\.mp3", t))
    except OSError:
        return []
    if not ten:
        return []
    cau_truc = None
    for kb in ("1-kich-ban-the.txt", "1-kich-ban.txt"):
        try:
            with open(os.path.join(thu_muc, kb), "r", encoding="utf-8") as tep:
                chu = tep.read().strip()
        except OSError:
            continue
        if not chu:
            continue
        doan, nghi = chia_doan_va_nghi(chu, giay_nghi=1.0)
        if len(doan) == len(ten):
            cau_truc = nghi
            break
    if cau_truc is None:
        return []
    lang: Dict[int, float] = {}
    for t in os.listdir(thu_doan):
        m = re.fullmatch(r"_im-lang-(\d+)ms\.mp3", t)
        if m:
            d = _dai_tep(ffmpeg, os.path.join(thu_doan, t))
            lang[int(m.group(1))] = d if d > 0 else int(m.group(1)) / 1000.0
    lang_phan = max((v for k, v in lang.items() if k > 500), default=0.0)
    lang_khuc = lang.get(int(round(GIAY_NGHI_GIUA_KHUC * 1000)), 0.0)
    ra: List[float] = []
    t = 0.0
    for i, tn in enumerate(ten):
        d = _dai_tep(ffmpeg, os.path.join(thu_doan, tn))
        if d <= 0:
            return []
        t += d
        if i == len(ten) - 1:
            break
        if cau_truc[i] >= 1.0:          # hết một PHẦN
            ra.append(t)
            t += lang_phan
        elif cau_truc[i] > 0:           # cắt vì quá trần — nhịp ngắn
            t += lang_khuc
    return ra


def _doc_json(duong: str) -> Optional[Dict[str, Any]]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else None
    except (OSError, ValueError):
        return None


def _doc_chu(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8-sig", errors="replace") as tep:
            return tep.read()
    except OSError:
        return ""


def tim_phan(thu_muc: str, ffmpeg: str, giay_nghi: float,
             ghi: Optional[Callable[[str], None]] = None,
             mp3: str = "") -> Tuple[List[RanhGioi], float, str]:
    """Tìm ranh giới các phần trên giọng GỐC. Trả `(ranh, độ dài giọng, nguồn)`.

    Nguồn theo thứ tự thiết kế: `2-phan.json` (khâu giọng ghi, lượt mới) →
    câu SRT có `---` → cộng dồn `2-doan/*.mp3` + nghỉ → cả video một phần.

    LỆCH THIẾT KẾ CÓ CHỦ Ý: nguồn 2 và 3 GỘP lại chứ không chọn một. SRT làm
    rơi dấu (lỗi thật (c): TL3/0004 kịch bản 7 dấu, SRT còn 6), còn cộng dồn
    đoạn thì đủ dấu nhưng cần cấu trúc đoạn khớp — gộp rồi bám lặng thật và
    bỏ trùng thì lấy được đủ ranh giới mà không ranh giới nào bị đếm hai lần.
    """
    ghi = ghi or (lambda s: None)
    mp3 = mp3 or os.path.join(thu_muc, "2-giong-doc.mp3")
    cac_lang, tong = do_lang(ffmpeg, mp3)
    if tong <= 0:
        raise RuntimeError("không đo được độ dài giọng đọc")

    du = _doc_json(os.path.join(thu_muc, TEN_PHAN_GIONG))
    if du and isinstance(du.get("phan"), list) and len(du["phan"]) >= 1:
        ranh = []
        phan = du["phan"]
        for k in range(len(phan) - 1):
            try:
                a = float(phan[k]["het_loi"])
                b = float(phan[k + 1]["bat_dau"])
            except (KeyError, TypeError, ValueError):
                ranh = None
                break
            if b > a:
                ranh.append(RanhGioi(a, b, "2-phan.json"))
        if ranh is not None:
            return ranh, tong, "2-phan.json"

    ung: List[float] = []
    nguon = []
    srt = _doc_chu(os.path.join(thu_muc, "3-phu-de.srt"))
    if srt:
        u = ung_vien_tu_srt(srt)
        if u:
            ung += u
            nguon.append("srt")
    try:
        u = ung_vien_tu_doan(thu_muc, ffmpeg)
    except Exception:  # noqa: BLE001 — nguồn phụ, hỏng thì thôi
        u = []
    if u:
        ung += u
        nguon.append("2-doan")
    ranh = _ranh_tu_ung_vien(ung, cac_lang, tong, giay_nghi, "+".join(nguon), ghi)
    if ranh:
        return ranh, tong, "+".join(nguon) or "lang-dai"
    return [], tong, "mot-phan"


def ghi_phan_giong(thu_muc: str, ffmpeg: str, nghi: Sequence[float],
                   giay_nghi: float, manh: Sequence[str]) -> Optional[Dict[str, Any]]:
    """Khâu giọng (thiết kế (b)): ghi `2-phan.json` ngay sau khi ghép giọng.

    `nghi[i]` là lặng chèn sau đoạn `manh[i]` (đúng danh sách `_noi_mp3` vừa
    dùng). Mốc hết phần = cộng dồn độ dài đoạn + lặng, rồi bám về khoảng
    lặng thật của tệp ghép (`silencedetect`). Trả nội dung đã ghi (hoặc `None`
    khi không có gì để ghi — kịch bản một phần vẫn ghi một phần).
    """
    mp3 = os.path.join(thu_muc, "2-giong-doc.mp3")
    cac_lang, tong = do_lang(ffmpeg, mp3)
    if tong <= 0:
        return None
    dai = [_dai_tep(ffmpeg, m) for m in manh]
    if any(d <= 0 for d in dai):
        return None
    cong = sum(dai) + sum(float(x) for x in list(nghi)[:len(manh) - 1])
    ti_le = tong / cong if cong > 0 else 1.0      # đệm khung mp3, lệch rất nhỏ
    phan: List[Dict[str, Any]] = []
    dang = {"so": 1, "bat_dau": 0.0, "doan": []}
    t = 0.0
    for i, d in enumerate(dai):
        t += d
        dang["doan"].append(i + 1)
        n = float(nghi[i]) if i < len(nghi) else 0.0
        het_phan = i < len(dai) - 1 and n >= max(0.5, 0.99 * float(giay_nghi))
        if het_phan:
            lang = bam_lang(t * ti_le, cac_lang)
            a, b = lang if lang else (t * ti_le, (t + n) * ti_le)
            dang["het_loi"] = round(a, 3)
            phan.append(dang)
            dang = {"so": len(phan) + 1, "bat_dau": round(b, 3), "doan": []}
        t += n
    dang["het_loi"] = round(tong, 3)
    phan.append(dang)
    du = {"giay_nghi": float(giay_nghi), "tong": round(tong, 3), "phan": phan}
    tam = os.path.join(thu_muc, TEN_PHAN_GIONG + ".tmp")
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=2)
    os.replace(tam, os.path.join(thu_muc, TEN_PHAN_GIONG))
    return du


# ── Bảng bù và lập kế hoạch ────────────────────────────────────────────────


def bang_bu(ranh: Sequence[RanhGioi], giay_nghi: float) -> List[float]:
    """`e_k = max(0, P − (b_k − a_k))` — thiếu bao nhiêu giây thì chèn bấy nhiêu."""
    return [max(0.0, float(giay_nghi) - (r.b - r.a)) for r in ranh]


def lap_ke_hoach(thu_muc: str, ffmpeg: str, giay_nghi: float, *,
                 giay_nghi_giong: float = 0.0, mp3: str = "",
                 ghi: Optional[Callable[[str], None]] = None) -> KeHoach:
    """Tìm phần + tính bù + nhãn phần từ SRT. Ném lỗi khi không đo được giọng.

    `giay_nghi` = P, khoảng nghỉ muốn có trong VIDEO (`giay_nghi_chuyen_phan`).
    `giay_nghi_giong` = nghỉ khâu giọng ĐÃ chèn (`giay_nghi_phan`), chỉ để
    biết có được coi mọi lặng dài là ranh giới không.
    """
    ranh, tong, nguon = tim_phan(thu_muc, ffmpeg, max(giay_nghi_giong, 0.0),
                                 ghi=ghi, mp3=mp3)
    kh = KeHoach(tong_giong=tong, ranh=ranh, bu=bang_bu(ranh, giay_nghi),
                 giay_nghi=float(giay_nghi), nguon=nguon)
    kh.nhan = _nhan_cac_phan(kh, _doc_chu(os.path.join(thu_muc, "3-phu-de.srt")))
    return kh


def ke_hoach_tu_json(du: Dict[str, Any], tong: float, giay_nghi: float) -> KeHoach:
    """KeHoach từ nội dung `2-phan.json` (khâu phụ đề dùng — không chạy FFmpeg)."""
    ranh = []
    phan = du.get("phan") or []
    for k in range(len(phan) - 1):
        a, b = float(phan[k]["het_loi"]), float(phan[k + 1]["bat_dau"])
        if b > a:
            ranh.append(RanhGioi(a, b, "2-phan.json"))
    return KeHoach(tong_giong=float(tong or du.get("tong") or 0.0), ranh=ranh,
                   bu=bang_bu(ranh, giay_nghi), giay_nghi=float(giay_nghi),
                   nguon="2-phan.json")


# ── Lọc giọng: chèn lặng bù ngay trong lượt mã cuối ─────────────────────────


def loc_giong_bu_nghi(ranh: Sequence[RanhGioi], bu: Sequence[float],
                      vao: str = "1:a", ra: str = "g") -> str:
    """Chuỗi `filter_complex` chèn `e_k` giây lặng vào giọng tại `m_k`.

    `aformat=48000:stereo, asplit, atrim từng đoạn, aevalsrc=0:d=e_k,
    concat=v=0:a=1` — không tệp tạm, không thêm lượt mã nào.
    """
    dau = ("[{0}]aformat=sample_rates=48000:channel_layouts=stereo,"
           "asetpts=PTS-STARTPTS".format(vao))
    cac = [(r.m, float(e)) for r, e in zip(ranh, bu) if float(e) > 0.005]
    if not cac:
        return dau + "[{0}]".format(ra)
    n = len(cac) + 1
    phan = [dau + ",asplit={0}{1}".format(
        n, "".join("[gb{0}]".format(i) for i in range(n)))]
    noi = []
    moc = [0.0] + [m for m, _e in cac]
    for i in range(n):
        cat = "atrim=start={0:.4f}".format(moc[i])
        if i + 1 < n:
            cat += ":end={0:.4f}".format(moc[i + 1])
        phan.append("[gb{0}]{1},asetpts=PTS-STARTPTS[gp{0}]".format(i, cat))
        noi.append("[gp{0}]".format(i))
        if i + 1 < n:
            phan.append("aevalsrc=0|0:c=stereo:s=48000:d={0:.4f}[gz{1}]".format(
                cac[i][1], i))
            noi.append("[gz{0}]".format(i))
    phan.append("{0}concat=n={1}:v=0:a=1[{2}]".format("".join(noi), len(noi), ra))
    return ";".join(phan)


# ── SRT sạch (8-phu-de.srt) ─────────────────────────────────────────────────


def bo_tien_to_ngat(chu: str) -> str:
    """Bỏ tiền tố `--- ` (và biến thể —, –, _, *) khỏi một câu phụ đề."""
    return _RE_TIEN_TO_NGAT.sub("", chu or "").strip()


def sach_srt(cau: Sequence[Any], kh: KeHoach) -> List[Any]:
    """Dời phụ đề sang trục video + dọn dấu ngắt + đẩy câu ra khỏi khoảng nghỉ.

    Luật (thiết kế (a)4, cộng một luật bổ sung cho lỗi thật (b)):
    * dời mọi mốc bằng `f`;
    * bỏ tiền tố `^\\s*[-—–_*]{3,}\\s*`, câu rỗng sau khi bỏ thì bỏ hẳn;
    * câu chạy qua `a'_k` (bắt đầu trước, kết thúc trong nghỉ) → kết thúc
      tại `a'_k`; câu bắt đầu trong `[a'_k, b'_k)` → dời về `b'_k`;
    * BỔ SUNG: câu mở phần (có dấu `---`) hoặc câu phủ cả khoảng nghỉ mà phần
      nằm SAU nghỉ dài hơn phần trước → cũng dời về `b'_k`. Đúng ca TL3/0004:
      "--- ユングは、" 93,76→95,62 trong khi lặng 93,79→95,12 — theo luật trơn
      nó thành câu 0,03 giây trước nghỉ, còn chữ thật thì nói SAU nghỉ.
    """
    from .phu_de import Cau  # noqa: PLC0415

    ra: List[Any] = []
    for c in cau:
        mo_phan = bool(_RE_TIEN_TO_NGAT.match(c.chu or ""))
        chu = bo_tien_to_ngat(c.chu)
        if not chu:
            continue
        s, e = float(c.bat_dau), float(max(c.ket_thuc, c.bat_dau))
        for r in kh.ranh:
            if e <= r.a or s >= r.b:
                continue            # không chạm khoảng nghỉ này
            if s >= r.a:            # bắt đầu TRONG nghỉ
                dai = max(0.5, e - s)
                s = r.b
                e = max(e, r.b + dai)
            elif e <= r.b:          # bắt đầu trước, kết thúc trong nghỉ
                if mo_phan:
                    dai = max(0.5, e - s)
                    s, e = r.b, r.b + dai
                else:
                    e = r.a
            else:                   # phủ cả khoảng nghỉ
                if mo_phan or (e - r.b) > (r.a - s):
                    s = r.b
                else:
                    e = r.a
        ra.append(Cau(so=0, bat_dau=kh.f(s), ket_thuc=kh.f(e), chu=chu))
    ra.sort(key=lambda x: x.bat_dau)
    # Câu bị DỒN về mốc `b'_k` trùng (gần) mốc câu ngay sau nó thì bị kẹp còn
    # ~0 giây — GỘP chữ nó vào câu sau, không vứt chữ. Chỉ áp cho câu nằm ở
    # `b'_k`; câu ngắn bình thường giữa phần không bị đụng.
    moc_b = [kh.b2(k) for k in range(len(kh.ranh))]
    gon: List[Any] = []
    i = 0
    while i < len(ra):
        c = ra[i]
        o_b = any(abs(c.bat_dau - b) < 0.01 for b in moc_b)
        if o_b and i + 1 < len(ra) and ra[i + 1].bat_dau - c.bat_dau < 0.3:
            ke = ra[i + 1]
            # Chữ Nhật/Trung/Hàn không cách từ; chữ Latinh (kể cả tiếng Việt) có.
            cjk = any(ord(x) >= 0x2E80 for x in (c.chu[-1:] + ke.chu[:1]))
            ke.chu = c.chu + ("" if cjk else " ") + ke.chu
            ke.bat_dau = c.bat_dau
            ke.ket_thuc = max(ke.ket_thuc, c.ket_thuc)
            i += 1
            continue
        gon.append(c)
        i += 1
    for i, c in enumerate(gon):
        c.so = i + 1
        if i + 1 < len(gon) and c.ket_thuc > gon[i + 1].bat_dau:
            c.ket_thuc = gon[i + 1].bat_dau
        if c.ket_thuc <= c.bat_dau:
            c.ket_thuc = c.bat_dau + 0.05
    return gon


def ghi_srt_sach(srt_vao: str, dich: str, kh: KeHoach) -> List[Any]:
    """Đọc `3-phu-de.srt`, làm sạch theo `kh`, ghi nguyên tử ra `dich`."""
    from .phu_de import doc_srt, viet_srt  # noqa: PLC0415

    cau = sach_srt(doc_srt(_doc_chu(srt_vao)), kh)
    if not cau:
        raise RuntimeError("phụ đề rỗng sau khi làm sạch")
    viet_srt(dich, cau)
    return cau


# ── Nhãn chương (dùng CHUNG với `auto_khau._muc_luc_tu_srt`) ────────────────


def _nhan_chu(chu: str) -> str:
    chu = chu.lstrip("-—– ").strip().rstrip("。.、,").strip()
    if len(chu) > 60:
        # Dài quá thì cắt ở dấu ngắt gần nhất, không cắt ngang chữ.
        cat = max(chu.rfind(d, 20, 60) for d in ("、", "──", "—", "。"))
        chu = chu[:cat] if cat > 0 else chu[:60]
    return chu.rstrip("。.、,").strip()


def _het_cau(chu: str) -> bool:
    return chu.rstrip().endswith(("。", "！", "？", "!", "?", ".", "」"))


def ghep_nhan(cau: Sequence[Tuple[float, str]], i: int,
              la_dau_phan: Optional[Callable[[int], bool]] = None) -> str:
    """Nhãn chương = cả CÂU mở chương, ghép dòng phụ đề từ `i` tới dấu hết câu
    (tối đa 4 dòng / 60 ký tự), không ghép lấn sang phần sau.

    Tách từ `auto_khau._muc_luc_tu_srt.ghep` (thiết kế (a)5) — hai nơi dùng
    chung một luật. `la_dau_phan(j)` mặc định = dòng `j` còn tiền tố `---`.
    """
    if la_dau_phan is None:
        def la_dau_phan(j: int) -> bool:
            return cau[j][1].startswith("---")
    chu = cau[i][1].lstrip("-—– ").strip()
    j = i + 1
    while (not _het_cau(chu) and j < len(cau) and j - i < 4
           and len(chu) < 60 and not la_dau_phan(j)):
        chu += cau[j][1].strip()
        j += 1
    return _nhan_chu(chu)


def _moc_chu(giay: float) -> str:
    phut, s = divmod(int(giay), 60)
    gio, phut = divmod(phut, 60)
    return ("{0}:{1:02d}:{2:02d}".format(gio, phut, s) if gio
            else "{0:02d}:{1:02d}".format(phut, s))


def _chi_so_dau_phan(cau: Sequence[Tuple[float, str]], kh: KeHoach,
                     truc_video: bool) -> List[int]:
    """Chỉ số câu đầu tiên của mỗi phần (phần 1 = câu 0)."""
    ra = [0] if cau else []
    for k in range(len(kh.ranh)):
        moc = kh.b2(k) if truc_video else kh.ranh[k].b
        # Câu mở phần có khi bị bộ ép đặt ở ĐẦU khoảng lặng (lỗi (b)) — nhận
        # cả câu bắt đầu từ `a` trở đi.
        moc_a = kh.a2(k) if truc_video else kh.ranh[k].a
        idx = next((i for i, (t, _c) in enumerate(cau) if t >= moc - 0.05), None)
        idx2 = next((i for i, (t, _c) in enumerate(cau) if t >= moc_a - 0.05), None)
        if idx2 is not None and idx is not None and idx2 < idx and \
                cau[idx2][1].startswith("---"):
            idx = idx2
        ra.append(idx if idx is not None else -1)
    return ra


def _nhan_cac_phan(kh: KeHoach, srt: str, truc_video: bool = False) -> List[str]:
    from .phu_de import doc_srt  # noqa: PLC0415

    cau = [(c.bat_dau, c.chu) for c in doc_srt(srt)]
    if not cau:
        return [""] * kh.so_phan
    dau = _chi_so_dau_phan(cau, kh, truc_video)
    tap = {i for i in dau if i >= 0}
    ra = []
    for i in dau:
        ra.append(ghep_nhan(cau, i, lambda j: j in tap or cau[j][1].startswith("---"))
                  if i >= 0 else "")
    return ra


def muc_luc(kh: KeHoach, srt_sach: str, lam_sach: bool = False) -> List[str]:
    """Các dòng `MM:SS nhãn` cho mục lục YouTube (thiết kế (a)5).

    Chương k+1 bắt đầu `floor(m'_k)` — giữa khoảng nghỉ, chỗ tối nhất. Luật
    YouTube: ≥3 chương, chương đầu 00:00, mỗi chương ≥10 giây (chương quá
    ngắn thì GỘP vào chương trước, không bịa mốc). Không đủ 3 → `[]`.

    `lam_sach=True`: `srt_sach` thật ra là `3-phu-de.srt` THÔ (trục giọng) —
    làm sạch trong bộ nhớ trước (`sach_srt`), để câu mở phần bị đặt ở đầu
    khoảng lặng vẫn được nhận đúng phần của nó.
    """
    from .phu_de import doc_srt  # noqa: PLC0415

    cac = doc_srt(srt_sach)
    if lam_sach:
        cac = sach_srt(cac, kh)
    cau = [(c.bat_dau, bo_tien_to_ngat(c.chu)) for c in cac]
    cau = [x for x in cau if x[1]]
    if not cau:
        return []
    moc = [0.0] + [float(math.floor(kh.m2(k))) for k in range(len(kh.ranh))]
    dau = [0]
    for k in range(len(kh.ranh)):
        b2 = kh.b2(k)
        idx = next((i for i, (t, _c) in enumerate(cau) if t >= b2 - 0.05), None)
        dau.append(idx if idx is not None else -1)
    tap = {i for i in dau if i >= 0}
    muc: List[Tuple[float, str]] = []
    for k, (t, i) in enumerate(zip(moc, dau)):
        if i < 0:
            continue
        nhan = ghep_nhan(cau, i, lambda j: j in tap)
        if len(nhan) < 6 and i + 1 < len(cau) and (i + 1) not in tap:
            nhan = (nhan + "、" + _nhan_chu(cau[i + 1][1])).lstrip("、")
        if muc and t - muc[-1][0] < 10:
            continue            # chương < 10 giây: gộp vào chương trước
        if muc and nhan == muc[-1][1] and i + 1 < len(cau):
            nhan = _nhan_chu(nhan + "、" + ghep_nhan(cau, i + 1, lambda j: j in tap))
        muc.append((t, nhan))
    tong = kh.tong_moi
    while len(muc) > 1 and tong > 0 and tong - muc[-1][0] < 10:
        muc.pop()
    if len(muc) < 3 or muc[0][0] != 0.0:
        return []
    return ["{0} {1}".format(_moc_chu(t), n) for t, n in muc]


_GACH = "━━━━━━━━━━━━━━"

#: Nhãn khối mục lục theo tiếng kênh (06/10/2026 — ngách/máy khác tiếng). Tiếng không có trong bảng → "Chapters".
NHAN_MUC_LUC = {"ja": "目次", "ko": "목차", "vi": "Mục lục", "zh": "目录"}


def dau_muc_luc(ngon_ngu: str) -> str:
    """Dòng đầu khối mục lục: `📌 目次` (ja, như cũ), `📌 목차` (ko)…, mặc định `📌 Chapters`."""
    ma = str(ngon_ngu or "").strip().lower().split("-")[0].split("_")[0]
    return "📌 " + NHAN_MUC_LUC.get(ma, "Chapters")


def co_muc_luc(seo: str) -> bool:
    """Mô tả đã có một khối mục lục (của tool hay người/AI viết) — để không chèn đúp."""
    seo = str(seo or "")
    # "目次" khớp ở bất cứ đâu như luật cũ; nhãn khác chỉ khớp khi đứng cuối dòng (tránh khớp nhầm câu thường).
    return "目次" in seo or any((n + "\n") in seo for n in ("Chapters",) + tuple(NHAN_MUC_LUC.values()))


def dat_muc_luc_seo(duong_seo: str, dong: Sequence[str], ngon_ngu: str) -> str:
    """ĐẶT khối mục lục trong `1-seo.txt`: thay khối cũ (giữa hai dòng `━…`
    có `📌`) nếu có, không có thì chèn như `_chen_muc_luc_seo`. Idempotent.

    `dong` rỗng (không đủ 3 chương) → GỠ khối cũ nếu có: mốc cũ sai trục.
    Trả `"thay"`, `"chen"`, `"go"`, `"giu"` (không đổi gì) hoặc `""`.
    """
    seo = _doc_chu(duong_seo)
    if not seo:
        return ""
    dau = dau_muc_luc(ngon_ngu)
    khoi = [_GACH, dau] + list(dong) + [_GACH] if dong else []
    cac = seo.replace("\r\n", "\n").split("\n")
    # Tìm khối của tool: dòng ━…, rồi dòng 📌, …, dòng ━… đóng.
    i_mo = i_dong = None
    for i, x in enumerate(cac):
        if x.strip().startswith("━") and i + 1 < len(cac) and "📌" in cac[i + 1]:
            for j in range(i + 2, len(cac)):
                if cac[j].strip().startswith("━"):
                    i_mo, i_dong = i, j
                    break
            if i_mo is not None:
                break
    if i_mo is not None:
        if cac[i_mo:i_dong + 1] == khoi:
            return "giu"
        cac[i_mo:i_dong + 1] = khoi
        ket = "thay" if khoi else "go"
    else:
        if not khoi:
            return "giu"
        if co_muc_luc(seo):
            return "giu"        # khối lạ do người/AI viết — không chèn đúp
        vi_tri = None
        for i, x in enumerate(cac):
            if x.strip().upper().startswith("HASHTAGS:"):
                vi_tri = i
                break
        if vi_tri is None:
            while cac and not cac[-1].strip():
                cac.pop()
            cac += [""] + khoi
        else:
            j = vi_tri - 1
            while j >= 0 and not cac[j].strip():
                j -= 1
            if j >= 0 and cac[j].lstrip().startswith("#"):
                vi_tri = j
            cac[vi_tri:vi_tri] = khoi + [""]
        ket = "chen"
    tam = duong_seo + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        tep.write("\n".join(cac))
    os.replace(tam, duong_seo)
    return ket


# ── Cảnh: dời theo `f`, cảnh đầu phần bắt đầu tại m'_k ──────────────────────


def xep_canh(moc: Sequence[float], het: Sequence[float], kh: KeHoach,
             ghi: Optional[Callable[[str], None]] = None
             ) -> Tuple[List[float], List[float], List[bool], set, set, List[int]]:
    """Thiết kế (e). Trả `(mốc mới, hết mới, giữ?, vào, ra, ranh không có cảnh)`.

    * mọi mốc dời bằng `f`; cảnh đầu video bắt đầu tại 0;
    * ranh giới k: cảnh có mốc gần `b_k` nhất trong `[a_k − 1, b_k + 4]` bắt
      đầu tại `m'_k` (mờ VÀO), cảnh còn giữ liền trước nó mờ RA;
    * cảnh bị kẹp về độ dài ~0 (nằm lọt giữa hai mốc) thì BỎ — cảnh trước
      giữ hình bù, y như cách khâu dựng vẫn xử cảnh thiếu clip;
    * không có cảnh nào trong cửa → bỏ chuyển ở ranh giới đó + ghi nhật ký.
    """
    ghi = ghi or (lambda s: None)
    n = len(moc)
    moi = [kh.f(float(t)) for t in moc]
    het_moi = [kh.f(float(t)) for t in het]
    if n:
        moi[0] = 0.0
    giu = [True] * n
    vao: set = set()
    ra: set = set()
    bo: List[int] = []
    for k, r in enumerate(kh.ranh):
        m2 = kh.m2(k)
        ung = [i for i in range(n) if giu[i] and r.a - 1.0 <= moc[i] <= r.b + 4.0]
        if not ung:
            bo.append(k)
            ghi("    (ranh giới phần {0}→{1} ~{2:.1f}s: không có cảnh nào bắt đầu "
                "gần đó — bỏ hiệu ứng chuyển ở chỗ này, vẫn nghỉ + đổi nhạc)".format(
                    k + 1, k + 2, r.b))
            continue
        c = min(ung, key=lambda i: (abs(moc[i] - r.b), i))
        truoc = [i for i in range(c) if giu[i]]
        if not truoc:
            bo.append(k)
            continue
        bi_bo = [i for i in truoc if moi[i] >= m2 - 0.1 and i not in vao] + \
                [i for i in range(c + 1, n) if giu[i] and moi[i] <= m2 + 0.1
                 and i not in vao]
        con_truoc = [i for i in truoc if i not in bi_bo]
        if not con_truoc:
            bo.append(k)
            continue
        for i in bi_bo:
            giu[i] = False
        moi[c] = m2
        vao.add(c)
        ra.add(con_truoc[-1])
    return moi, het_moi, giu, vao, ra, bo


# ── Khung nhạc từng phần (thiết kế (g)) ─────────────────────────────────────


def khung_nhac(kh: KeHoach, gap: float = 2.0) -> List[Dict[str, float]]:
    """Khung nhạc phần k trên trục VIDEO.

    Từ `b'_{k−1} − (P−gap)/2` tới `a'_k + (P−gap)/2`; mờ vào 1,5s (phần 1 từ
    giây 0, mờ vào 2s); mờ ra 2s đúng mép khung; phần cuối mờ ra 3s cuối
    video. Giữa hai khung im ≥ `gap` giây.
    """
    le = max(0.0, (float(kh.giay_nghi) - float(gap)) / 2.0)
    T = kh.tong_moi
    ra = []
    for k in range(kh.so_phan):
        if k == 0:
            s, mv = 0.0, 2.0
        else:
            s, mv = max(0.0, kh.b2(k - 1) - le), 1.5
        if k == kh.so_phan - 1:
            e, mr = T, 3.0
        else:
            e, mr = min(T, kh.a2(k) + le), 2.0
        L = max(0.0, e - s)
        mv = min(mv, L / 3.0)
        mr = min(mr, L / 3.0)
        ra.append({"so": k + 1, "bat_dau": round(s, 3), "ket_thuc": round(e, 3),
                   "mo_vao": round(mv, 3), "mo_ra": round(mr, 3)})
    return ra


#: Cảm xúc `4-ke-hoach.json[].emotion` (tiếng Anh, vế sau "→") → nhãn kho nhạc.
TU_CAM_XUC_KE_HOACH: Dict[str, Tuple[str, ...]] = {
    "căng": ("shock", "fear", "anxious", "anxiety", "panic", "dread", "tense",
             "alarm", "urgent", "threat", "angry", "anger", "restrained"),
    "buồn": ("weary", "hollow", "sad", "lonely", "isolat", "grief", "melanchol",
             "sorrow", "regret", "loss", "hurt"),
    "ấm": ("warm", "tender", "comfort", "gentle", "connected", "accepted",
           "loved", "hopeful", "relief"),
    "tĩnh lặng": ("serene", "calm", "center", "peace", "quiet", "grounded",
                  "still", "content", "settled"),
    "hùng tráng": ("liberat", "triumph", "empower", "resolute", "determin",
                   "awaken", "confident", "strong", "free"),
    "bí ẩn": ("question", "curious", "myster", "uncertain", "doubt", "seeking",
              "intrigu", "wonder"),
    "vui": ("joy", "playful", "bright", "delight", "happy", "amus"),
}


def _doi_cam_xuc(emotion: str) -> List[str]:
    ve_sau = str(emotion or "").split("→")[-1].lower()
    return [nhan for nhan, tu in TU_CAM_XUC_KE_HOACH.items()
            if any(t in ve_sau for t in tu)]


def cam_xuc_phan(thu_muc: str, kh: KeHoach) -> List[List[str]]:
    """Nhãn cảm xúc gợi ý cho từng phần, từ `4-ke-hoach.json` (theo số dòng SRT)."""
    try:
        with open(os.path.join(thu_muc, "4-ke-hoach.json"), "r", encoding="utf-8") as tep:
            kehoach = json.load(tep)
    except (OSError, ValueError):
        return [[] for _ in range(kh.so_phan)]
    from .phu_de import doc_srt  # noqa: PLC0415

    cau = doc_srt(_doc_chu(os.path.join(thu_muc, "3-phu-de.srt")))
    ra: List[List[str]] = []
    for k in range(kh.so_phan):
        moc = 0.0 if k == 0 else kh.ranh[k - 1].b
        so_dong = next((i + 1 for i, c in enumerate(cau) if c.bat_dau >= moc - 0.05), 0)
        nhan: List[str] = []
        for muc in (kehoach if isinstance(kehoach, list) else []):
            try:
                if int(muc.get("srt_from", 0)) <= so_dong <= int(muc.get("srt_to", 0)):
                    nhan = _doi_cam_xuc(muc.get("emotion", ""))
                    break
            except (TypeError, ValueError, AttributeError):
                continue
        ra.append(nhan)
    return ra


_RE_EBUR_I = re.compile(r"I:\s*(-?[0-9.]+)\s*LUFS")


def do_lufs_giong(ffmpeg: str, tep: str) -> Optional[float]:
    """LUFS tích hợp (ebur128) của giọng đọc — gốc tính độ to nhạc nền."""
    text = _chay([ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-i", tep,
                  "-af", "ebur128=framelog=quiet", "-threads", "1", "-f", "null", "-"])
    tim = _RE_EBUR_I.findall(text)
    if not tim:
        return None
    try:
        v = float(tim[-1])
    except ValueError:
        return None
    return v if -70.0 < v < 0.0 else None
