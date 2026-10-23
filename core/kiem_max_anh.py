"""Claude Max KIỂM CUỐI ảnh cảnh theo lô — bù trần của giám khảo đi ví (17/10/2026).

═══ VÌ SAO ═══

Hiệu chỉnh 17/10 trên 50 cảnh thật (`workspace/chan-doan/anh-canh-17-10.md`, mục 8): giám khảo đi ví (Fable 5 — bậc
mạnh nhất của ví) chỉ tương quan 0,40 với thước mù (Claude Max Opus 5.5, tự chấm lại tương quan 0,80). Chọn tấm cao
nhất trong 3–9 tấm bằng một giám khảo nhiễu như thế thì nhiễu được phóng lên: tấm thắng ví chấm 8, thước mù 5–6,5.
Chủ dự án: chất lượng trước, không trần tiền — ràng buộc duy nhất là hạn mức Claude Max (để dành cho viết chữ).

═══ CÁCH LÀM ═══

* Ví chọn xong một cảnh (tấm thắng + 2 tấm á) → cảnh ấy XẾP vào lô. Đủ `LO` cảnh (hoặc chờ quá `CHO_GOM` giây) thì
  MỘT lượt Claude Max chấm cả lô theo thước mù, chỉ nhìn câu đọc + "khoảnh khắc" (không xem lời nhắc cảnh — xem hiệu
  chỉnh) và được quyền đổi sang tấm á. ~150 cảnh / 6 = 25 lượt, cộng lượt kiểm lại cảnh phải viết lại → 25–40 lượt
  một video.
* Điểm Max của tấm tốt nhất < `NGUONG_MAX` (thang mù) → cảnh vào vòng viết lại (vẫn trần 2 vòng tổng) rồi Max kiểm lại
  ĐÚNG cảnh ấy.
* Max không dùng được (máy không có thuê bao, `MaxKhongDung`, hết hạn mức tuần, lỗi, hoặc chạm trần lượt/ngày
  `cai-dat.json: anh_kiem_max_ngay`) → im lặng giữ lựa chọn của ví, ghi lý do vào sổ cảnh + não. KHÔNG chặn dựng.

Sổ đếm lượt/ngày: `workspace/viet-max/kiem-anh-ngay.json` = {ngày: số lượt}.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

__all__ = ["LO", "CHO_GOM", "NGUONG_MAX", "TRAN_NGAY_MAC_DINH", "KHOA_CAI_DAT", "LOI_NHAC_LO", "doc_lo",
           "KiemMax", "tran_ngay", "da_dung_hom_nay", "cua_luot"]

LO = 6
#: Giây chờ gom đủ lô; quá thì cảnh nào chờ lâu nhất tự chấm phần lô đang có.
CHO_GOM = 90.0
#: Thang MÙ (mục thấp nhất của nội dung / giọng / lỗi / phong cách) — 7 là "đạt" của thước mù.
NGUONG_MAX = 7.0
#: Trần lượt Claude Max / ngày cho việc kiểm ảnh. Đo sổ `viet-max/so-dung.jsonl` 12–16/10/2026: viết chữ dùng
#: 1.300–1.700 lượt/ngày (13/10 chạm hạn mức tuần, 162 lượt hỏng). 8 video × ~35 lượt ≈ 280 → trần 300 (≈ +20% tải).
TRAN_NGAY_MAC_DINH = 300
KHOA_CAI_DAT = "anh_kiem_max_ngay"
TEP_DEM = os.path.join("workspace", "viet-max", "kiem-anh-ngay.json")
#: Lượt Max cùng lúc của việc kiểm ảnh (mỗi tiến trình Claude vài trăm MB RAM, chung suất với viết chữ).
SONG_SONG = 2
_VAN = threading.BoundedSemaphore(SONG_SONG)
_KHOA_DEM = threading.Lock()
_NHAN = "ABC"

LOI_NHAC_LO = """You are a strict art director reviewing scene illustrations for a Japanese YouTube channel of WARM,
CALM self-understanding psychology for adults (the viewer comes to feel understood and at ease; never scared).
{ta_ref}Each other image carries its label in a red box at its top-left corner: "S<scene>-<candidate>", e.g. S2-B.
For each scene below there are up to 3 candidates (A, B, C); pick the one to publish.
Channel style note: {phong}

Scenes:
{ds}

For EACH candidate judge, on 0-10:
- fit: does the picture show the narration line's concrete moment (the given "moment": who, doing what, where, with
  which key object)? 10 = obvious and literal; 5 = loosely related / generic; 0 = unrelated or contradicts it.
- tone: 10 = warm, calm, safe; lower for anything horror-like, creepy, sinister, gloomy, faceless or masked figures,
  distorted faces, looming shadows, staring eyes, doubles of the character.
- defects: 10 = clean; lower for extra/missing/merged limbs, melted faces, broken anatomy, furniture stacked or merged.
- style: 10 = same character design and drawing style as the reference.
Hard failures (flag true): "chu" any letters/numbers/words; "danh_dau" arrows or marks drawn over the picture;
"luoi" panels / grid / collage. Set "horror" true for any creepy element.
Keep text short. Return JSON only:
{{"canh": [{{"canh": 1, "ung_vien": [{{"nhan": "A", "fit": 0, "tone": 0, "defects": 0, "style": 0, "horror": false,
"chu": false, "danh_dau": false, "luoi": false, "ly_do": "<short>"}}], "sua": "<if no candidate reaches 7: what the
image prompt must change, one short sentence; else empty>"}}]}}"""


def _so(v: Any) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    try:
        return max(0.0, min(10.0, float(v)))
    except (TypeError, ValueError):
        return None


def _co(v: Any) -> bool:
    return v is True or str(v).strip().lower() in ("true", "yes", "1")


def doc_lo(du: Any, so_ung_vien: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """JSON lô → {số cảnh trong lô (1..): {"ung_vien": {chỉ số 0..: mục}, "tot": chỉ số, "tong": điểm, "sua"}}.

    Điểm một tấm = mục thấp nhất của 4 mục; cờ cứng → 0; tấm rợn xếp sau mọi tấm sạch. Cảnh thiếu điểm → bỏ."""
    ra: Dict[int, Dict[str, Any]] = {}
    ds = du.get("canh") if isinstance(du, dict) else None
    for c in ds if isinstance(ds, list) else []:
        if not isinstance(c, dict):
            continue
        try:
            so = int(c.get("canh"))
        except (TypeError, ValueError):
            continue
        if not 1 <= so <= len(so_ung_vien):
            continue
        uv: Dict[int, Dict[str, Any]] = {}
        for x in c.get("ung_vien") or []:
            if not isinstance(x, dict):
                continue
            nhan = str(x.get("nhan") or "").strip().upper()[-1:]
            if nhan not in _NHAN or _NHAN.index(nhan) >= int(so_ung_vien[so - 1]):
                continue
            d = {k: _so(x.get(k)) for k in ("fit", "tone", "defects", "style")}
            if any(v is None for v in d.values()):
                continue
            co = [k for k in ("chu", "danh_dau", "luoi") if _co(x.get(k))]
            uv[_NHAN.index(nhan)] = {"diem": d, "co": co, "horror": _co(x.get("horror")),
                                     "tong": 0.0 if co else round(min(d.values()), 1),
                                     "ly_do": " ".join(str(x.get("ly_do") or "").split())[:200]}
        if not uv:
            continue
        tot = sorted(uv, key=lambda i: (uv[i]["horror"], -uv[i]["tong"], i))[0]
        ra[so] = {"ung_vien": uv, "tot": tot, "tong": uv[tot]["tong"], "horror": uv[tot]["horror"],
                  "sua": " ".join(str(c.get("sua") or "").split())[:240]}
    return ra


def tran_ngay(goc: str) -> int:
    try:
        from .cai_dat import doc  # noqa: PLC0415
        return max(0, int(doc(goc).get(KHOA_CAI_DAT, TRAN_NGAY_MAC_DINH)))
    except Exception:  # noqa: BLE001
        return TRAN_NGAY_MAC_DINH


def _hom_nay() -> str:
    return _dt.date.today().isoformat()


def da_dung_hom_nay(goc: str) -> int:
    try:
        with open(os.path.join(goc, TEP_DEM), "r", encoding="utf-8") as f:
            return int((json.load(f) or {}).get(_hom_nay()) or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def _xin_luot(goc: str, tran: int) -> bool:
    """Giữ một lượt của trần ngày (đếm TRƯỚC khi gọi — lượt hỏng vẫn tính, thà dè xẻn hạn mức của viết chữ)."""
    duong = os.path.join(goc, TEP_DEM)
    with _KHOA_DEM:
        try:
            with open(duong, "r", encoding="utf-8") as f:
                du = json.load(f)
            du = du if isinstance(du, dict) else {}
        except (OSError, ValueError):
            du = {}
        ngay = _hom_nay()
        if int(du.get(ngay) or 0) >= tran:
            return False
        du = {k: v for k, v in du.items() if k >= (_dt.date.today() - _dt.timedelta(days=14)).isoformat()}
        du[ngay] = int(du.get(ngay) or 0) + 1
        try:
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            with open(duong + ".tmp", "w", encoding="utf-8") as f:
                json.dump(du, f)
            os.replace(duong + ".tmp", duong)
        except OSError:
            pass
        return True


class _Cho:
    def __init__(self, muc: Dict[str, Any]) -> None:
        self.muc = muc
        self.kq: Optional[Dict[str, Any]] = None
        self.xong = threading.Event()
        self.luc = time.time()


class KiemMax:
    """Một lô kiểm cho MỘT lượt (cùng kênh, cùng ảnh tham chiếu). An toàn đa luồng.

    `goi(tin_nhan, khoa) -> str` là lời gọi Claude Max (ném lỗi = không dùng được). `kiem(muc)` chặn tới khi lô của
    nó được chấm, trả {"ok": True, "tot", "tong", "ung_vien", "sua"} hoặc {"ok": False, "ly_do"}.
    `muc` = {"ma", "loi_doc", "khoanh_khac", "tep": [≤3 ảnh], "ref": ảnh tham chiếu hay ""}."""

    def __init__(self, goi: Optional[Callable[[List[Dict[str, Any]], str], str]], *, goc: str = "",
                 phong: str = "", tran: Optional[int] = None, lo: int = LO, cho_gom: float = CHO_GOM,
                 ghi: Callable[[str], None] = lambda _d: None, anh_url: Optional[Callable[..., str]] = None,
                 tieng_en: str = "", kenh_en: str = "") -> None:
        self._goi, self.goc, self.phong = goi, goc, phong
        #: 22/10/2026 — ngách khác ngách mặc định: tiếng lời đọc (tiếng Anh, vd "English") + một câu tả kênh bằng tiếng Anh
        #: thay câu "Japanese … psychology" của lời nhắc. Rỗng → lời nhắc cũ nguyên văn.
        self.tieng_en, self.kenh_en = str(tieng_en or "").strip(), str(kenh_en or "").strip()
        self.tran = tran_ngay(goc) if tran is None else int(tran)
        self.lo, self.cho_gom, self.ghi = max(1, int(lo)), float(cho_gom), ghi
        self._khoa = threading.Lock()
        self._hang: List[_Cho] = []
        self._tat = ""          # lý do Max không dùng được (đã gặp một lần thì cả lượt khỏi thử lại)
        self.so_luot = 0
        if anh_url is None:
            from .chon_anh_canh import anh_data_url as anh_url  # noqa: PLC0415
        self._anh = anh_url

    def kiem(self, muc: Dict[str, Any]) -> Dict[str, Any]:
        if self._goi is None:
            return {"ok": False, "ly_do": "máy không có Claude Max"}
        if self._tat:
            return {"ok": False, "ly_do": self._tat}
        cho = _Cho(muc)
        lo = None
        with self._khoa:
            self._hang.append(cho)
            if len(self._hang) >= self.lo:
                lo, self._hang = self._hang, []
        if lo:
            self._chay(lo)
        while not cho.xong.wait(min(5.0, self.cho_gom)):
            with self._khoa:
                if cho in self._hang and time.time() - self._hang[0].luc >= self.cho_gom:
                    lo, self._hang = self._hang, []
                else:
                    lo = None
            if lo:
                self._chay(lo)
        return cho.kq or {"ok": False, "ly_do": "không có kết quả"}

    def _chay(self, lo: List[_Cho]) -> None:
        try:
            kq = self._cham_lo([c.muc for c in lo])
        except Exception as loi:  # noqa: BLE001 — Max không dùng được: mọi cảnh trong lô giữ lựa chọn của ví
            ly = "Claude Max không dùng được ({0})".format(str(loi)[:120])
            if type(loi).__name__ in ("MaxKhongDung", "HetTranNgay"):
                self._tat = ly
            kq = {i: {"ok": False, "ly_do": ly} for i in range(1, len(lo) + 1)}
        for i, c in enumerate(lo, 1):
            c.kq = kq.get(i) or {"ok": False, "ly_do": "Claude Max không chấm cảnh này"}
            c.xong.set()

    def _cham_lo(self, ds: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        if not _xin_luot(self.goc, self.tran):
            raise HetTranNgay("đã dùng hết {0} lượt/ngày dành cho kiểm ảnh (cai-dat: {1})".format(
                self.tran, KHOA_CAI_DAT))
        ref = next((m.get("ref") for m in ds if m.get("ref") and os.path.isfile(m.get("ref"))), "")
        dong, anh = [], []
        if ref:
            anh.append(self._anh(ref, 448, nhan="REF"))
        for so, m in enumerate(ds, 1):
            dong.append(('Scene {0}: narration (' + (self.tieng_en or 'Japanese') + ') 「{1}」 | moment: {2} | candidates: {3}').format(
                so, " ".join(str(m.get("loi_doc") or "").split())[:240],
                " ".join(str(m.get("khoanh_khac") or "").split())[:200] or "(not given)",
                ", ".join("S{0}-{1}".format(so, _NHAN[i]) for i in range(len(m["tep"])))))
            anh += [self._anh(t, 640, nhan="S{0}-{1}".format(so, _NHAN[i])) for i, t in enumerate(m["tep"])]
        ln = LOI_NHAC_LO.format(ta_ref='The first image (label "REF") is the channel\'s reference character and the '
                                'ONLY truth for how the main character looks - if the style note describes it '
                                'differently, follow the REF; a candidate whose main character is clearly a different '
                                'KIND of figure from the REF (mascot vs person, other gender, very different age) gets '
                                'style 5 at most; small shade/pose/outfit differences are not a different figure. '
                                if ref else "", phong=" ".join(str(self.phong or "").split())[:500] or "(none)",
                                ds="\n".join(dong))
        if self.kenh_en:
            ln = ln.replace(LOI_NHAC_LO.split("\n{ta_ref}")[0], "You are a strict art director reviewing scene illustrations for "
                            + " ".join(self.kenh_en.split()).replace("{", "(").replace("}", ")") + ".")
        tin = [{"role": "user", "content": [{"type": "text", "text": ln}]
                + [{"type": "image_url", "image_url": {"url": a}} for a in anh]}]
        with _VAN:
            self.so_luot += 1
            tho = self._goi(tin, "kiem-anh-max:" + "|".join(str(m.get("ma")) for m in ds))
        from .goi_van_ban import loc_json  # noqa: PLC0415
        du = doc_lo(loc_json(str(tho or "")), [len(m["tep"]) for m in ds])
        if not du:
            raise RuntimeError("Claude Max trả rác")
        return {so: dict(v, ok=True) for so, v in du.items()}


class HetTranNgay(RuntimeError):
    """Chạm trần lượt Claude Max/ngày của việc kiểm ảnh."""


_LUOT: Dict[str, KiemMax] = {}
_KHOA_LUOT = threading.Lock()


def cua_luot(thu_muc_luot: str, tao: Callable[[], Optional[KiemMax]]) -> Optional[KiemMax]:
    """Một `KiemMax` cho mỗi thư mục lượt (mọi luồng ảnh của lượt dùng chung để gom lô)."""
    with _KHOA_LUOT:
        if thu_muc_luot not in _LUOT:
            _LUOT[thu_muc_luot] = tao()
        return _LUOT[thu_muc_luot]
