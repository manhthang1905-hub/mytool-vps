"""Vòng tự học kiểu cờ vua — Đợt 1 của `workspace/THIET-KE-TU-HOC.md` (03/10/2026).

Mỗi video = một VÁN. `CHANNEL/<k>/tu-hoc/van.json` = `{mã gói: {nuoc, du_doan, ket48, ket7, lech, dung}}`:

  * nước đi (`nuoc`) theo NHÃN CHUẨN của `TRUC` — ghi lúc bàn giao (`ghi_van`);
  * kết quả chấm dần (`cham_van`): 48h = hiển thị ≥ ngưỡng thắng của kênh (dùng lại `chien_luoc.ket_qua`),
    7 ngày = GIỜ XEM ≥ trung vị kênh (kênh < 5 video có số 7d thì so trung vị NHÓM);
  * bảng điểm (`bang_diem`): Beta(1+thắng, 1+trượt) mỗi (trục, giá trị), ván 7d nặng 1, chỉ 48h nặng 0,5,
    cộng số các kênh cùng nhóm × 0,3 làm tiên nghiệm;
  * chọn lần sau (`rut`): Thompson sampling.

Không Qt, không mạng. Thiếu số thì để trống — không bịa. Thêm trục (đợt 2): thêm tên vào `TRUC`
và đưa nhãn vào `nuoc`; mọi thứ còn lại tự chạy theo `TRUC`.
"""

from __future__ import annotations

import glob
import io
import json
import os
import random
import re
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple

#: Trục nhãn. Đợt 2 (03/10/2026) thêm "kieu_tieu_de", "hook".
TRUC = ("cum", "cong_thuc", "kieu_bia", "do_dai", "kieu_tieu_de", "hook")
#: Tập nhãn cố định của 2 trục đợt 2 (LLM trả kèm lúc chấm; thiếu thì lùi về regex).
KIEU_TIEU_DE = ("so_dem", "cau_hoi", "canh_bao", "bi_mat", "doi_lap", "dac_diem_nguoi", "khac")
KIEU_HOOK = ("cau_hoi", "canh_tinh_huong", "so_lieu_su_that", "canh_bao", "ke_chuyen", "khac")
_TAP_NHAN = {"kieu_tieu_de": KIEU_TIEU_DE, "hook": KIEU_HOOK}
HE_SO_CHON_NEN, HE_SO_CHON_BIEN = 0.9, 0.2   # hệ số = 0,9 + 0,2 × điểm rút ∈ [0,9; 1,1]
TRONG_SO_7D = 1.0
TRONG_SO_48H = 0.5
HE_SO_NHOM = 0.3
N_TOI_THIEU_7D = 5      # kênh có ít hơn ngần này video có số 7d → so trung vị nhóm
N_TOI_THIEU_NHOM = 3
_CHIEU = {"thắng": "thang", "trượt": "truot", "thang": "thang", "truot": "truot"}


# ── đĩa ─────────────────────────────────────────────────────────────────────

def _thu_muc(goc: str, ma_kenh: str) -> str:
    from .kenh import duong_kenh  # noqa: PLC0415

    return os.path.join(duong_kenh(goc, ma_kenh), "tu-hoc")


def duong_van(goc: str, ma_kenh: str) -> str:
    return os.path.join(_thu_muc(goc, ma_kenh), "van.json")


def doc_van(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Any]]:
    try:
        with io.open(duong_van(goc, ma_kenh), encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_nguyen_tu(duong: str, noi_dung: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(noi_dung)
    for lan in range(5):
        try:
            os.replace(tam, duong)
            return
        except PermissionError:  # Windows: tệp đang bị chương trình khác mở
            if lan == 4:
                raise
            time.sleep(0.2)


def _luu_van(goc: str, ma_kenh: str, van: Dict[str, Any]) -> None:
    _ghi_nguyen_tu(duong_van(goc, ma_kenh), json.dumps(van, ensure_ascii=False, indent=1) + "\n")


def ghi_van(goc: str, ma_kenh: str, ma_goi: str, nuoc: Dict[str, Any], du_doan: Optional[Dict[str, Any]] = None) -> None:
    """Ghi/cập nhật một ván. Giữ nguyên kết quả đã chấm nếu ván đã có."""
    van = doc_van(goc, ma_kenh)
    cu = van.get(ma_goi) or {}
    van[ma_goi] = dict(cu, ma_goi=ma_goi, nuoc={k: v for k, v in (nuoc or {}).items() if v not in (None, "", [])},
                       du_doan=dict(du_doan or {}))
    van[ma_goi].setdefault("ngay", time.strftime("%Y-%m-%d"))
    _luu_van(goc, ma_kenh, van)


# ── nhãn chuẩn ──────────────────────────────────────────────────────────────

def nhom_do_dai(giay: Any) -> str:
    try:
        phut = float(giay) / 60.0
    except (TypeError, ValueError):
        return ""
    if phut <= 0:
        return ""
    return "<10" if phut < 10 else "10-15" if phut < 15 else "15-20" if phut < 20 else ">20"


def nhan_cum(d: Dict[str, Any], cum_cua: Any = None) -> str:
    """Nhãn cụm của một nguồn: cụm đã gắn trong dòng, không có thì phân theo tiêu đề (cùng bộ cụm V7)."""
    cum = [str(c) for c in (d.get("cum") or []) if c]
    if not cum and cum_cua is not None and d.get("tieu_de"):
        try:
            cum = [str(c) for c in (cum_cua(str(d["tieu_de"])) or []) if c]
        except Exception:  # noqa: BLE001
            cum = []
    return cum[0] if cum else ""


def _ham_cum(goc: str, ma_kenh: str) -> Any:
    try:
        from .chien_luoc import ngu_canh  # noqa: PLC0415

        return ngu_canh.dung(goc, ma_kenh, co_v7=False).cum_cua
    except Exception:  # noqa: BLE001
        return None


def _doc_ho_so(goc: str, ma_kenh: str, ma_goi: str) -> Dict[str, Any]:
    try:
        from . import ho_so_video  # noqa: PLC0415

        return ho_so_video.doc_ho_so(goc, ma_kenh, ma_goi) or {}
    except Exception:  # noqa: BLE001
        return {}


def _nuoc_tu(nguon: Dict[str, Any], hs: Dict[str, Any], cum_cua: Any) -> Dict[str, Any]:
    th = hs.get("thumbnail") or {}
    ra = {"cum": nhan_cum(nguon or {}, cum_cua),
          "cong_thuc": str((nguon or {}).get("cong_thuc") or hs.get("cong_thuc") or (nguon or {}).get("nguon") or ""),
          "kieu_bia": str(th.get("kieu") or ""), "do_dai": nhom_do_dai(hs.get("thoi_luong_giay"))}
    ra.update(_nhan_dot2(hs))
    return ra


def _nhan_dot2(hs: Dict[str, Any]) -> Dict[str, Any]:
    """`kieu_tieu_de`/`hook` của ván: nhãn LLM đã ghi lúc làm video (`tieu_de_cham.tu_hoc`,
    `kich_ban.hook_nhan`) nếu có; không có thì đoán bằng regex từ tiêu đề thật và đánh dấu `nhan_doan`.
    Hook không có chữ trong hồ sơ cũ nên không đoán được — để trống, không bịa."""
    ra: Dict[str, Any] = {}
    doan: List[str] = []
    td = ((hs.get("tieu_de_cham") or {}).get("tu_hoc") or {}) if isinstance(hs.get("tieu_de_cham"), dict) else {}
    hk = ((hs.get("kich_ban") or {}).get("hook_nhan") or {}) if isinstance(hs.get("kich_ban"), dict) else {}
    for truc, nguon in (("kieu_tieu_de", td), ("hook", hk)):
        v = chuan_nhan(truc, nguon.get(truc)) if isinstance(nguon, dict) else ""
        if v:
            ra[truc] = v
            if nguon.get("nhan_doan"):
                doan.append(truc)
    if "kieu_tieu_de" not in ra and str(hs.get("tieu_de") or "").strip():
        ra["kieu_tieu_de"] = nhan_tieu_de_regex(str(hs["tieu_de"]))
        doan.append("kieu_tieu_de")
    if doan:
        ra["nhan_doan"] = True
        ra["nhan_doan_truc"] = doan
    return ra


# ── nhãn kiểu tiêu đề / hook: LLM trả kèm lúc chấm, regex chỉ là đường lùi ──

_RE_HOI = re.compile(r"[?？]|\bbạn có (?:biết|bao giờ)\b|\bwhy\b|\bhow\b|\bwhat\b|(?:ですか|でしょうか|のか)[。！!]?$", re.I)
_RE_CANH_BAO = re.compile(r"sai lầm|đừng|không bao giờ|cảnh báo|nguy hiểm|tránh|thảm họa|mistake|never|stop |don'?t|warning|"
                          r"avoid|danger|危険|やめ|注意|失敗|絶対|してはいけ|ダメ", re.I)
_RE_BI_MAT = re.compile(r"bí mật|sự thật|ít ai|không ai nói|giấu|che giấu|bị che|secret|truth|hidden|nobody tells|"
                        r"秘密|真実|知らない|誰も|隠", re.I)
_RE_DOI_LAP = re.compile(r"ngược lại|trái ngược|thực ra|hóa ra|thật ra|không phải|nhưng thực|opposite|actually|"
                         r"contrary|myth|逆|実は|ではなく|じゃない|真逆", re.I)
_RE_NGUOI = re.compile(r"kiểu người|người (?:\w+ ){0,3}(?:thường|hay|có)|những người|people who|type of (?:person|people)|"
                       r"タイプ|人は|人の特徴|な人|する人", re.I)
_RE_SO = re.compile(r"\d|[０-９]|[一二三四五六七八九十百千]+(?:つ|個|選|大|の|%)|top\s*\d", re.I)
_RE_TINH_HUONG = re.compile(r"tưởng tượng|giả sử|hãy nghĩ|bạn đang|bạn có từng|imagine|suppose|picture this|"
                            r"想像|もし|あなたが|ある日|いつも", re.I)
_RE_KE = re.compile(r"ngày xưa|hồi đó|một hôm|có một|câu chuyện|năm \d{4}|story|once|years ago|back in|"
                    r"昔|ある男|ある女|物語|あれは", re.I)


def nhan_tieu_de_regex(chu: str) -> str:
    """Đường lùi RẺ khi LLM không trả nhãn. Thứ tự: hỏi > cảnh báo > bí mật > đối lập > kiểu người > số đếm."""
    c = str(chu or "")
    for ten, re_ in (("cau_hoi", _RE_HOI), ("canh_bao", _RE_CANH_BAO), ("bi_mat", _RE_BI_MAT),
                     ("doi_lap", _RE_DOI_LAP), ("dac_diem_nguoi", _RE_NGUOI), ("so_dem", _RE_SO)):
        if re_.search(c):
            return ten
    return "khac"


def nhan_hook_regex(chu: str) -> str:
    """Đường lùi cho hook — chỉ nhìn ~220 ký tự đầu."""
    c = str(chu or "").strip()[:220]
    for ten, re_ in (("cau_hoi", _RE_HOI), ("canh_bao", _RE_CANH_BAO), ("so_lieu_su_that", _RE_SO),
                     ("canh_tinh_huong", _RE_TINH_HUONG), ("ke_chuyen", _RE_KE)):
        if re_.search(c):
            return ten
    return "khac"


_REGEX_NHAN = {"kieu_tieu_de": nhan_tieu_de_regex, "hook": nhan_hook_regex}


def chuan_nhan(truc: str, gia_tri: Any) -> str:
    """Nhãn hợp lệ của trục (chữ thường, thuộc tập cố định) hoặc "" nếu lạ."""
    v = str(gia_tri or "").strip().lower()
    return v if v in _TAP_NHAN.get(truc, ()) else ""


def yeu_cau_nhan(truc: str) -> str:
    """Đoạn THÊM vào cuối lời nhắc chấm đang có: xin LLM ghi nhãn từng phương án, khỏi tốn thêm lượt gọi."""
    return ("\n\nNgoài ra, trong JSON trả về, thêm khoá \"kieu\": nhãn của TỪNG ứng viên theo Ý NGHĨA, dạng "
            "{\"A\": \"<nhãn>\", \"B\": \"<nhãn>\"}. Mỗi nhãn CHỈ là một trong: " + ", ".join(_TAP_NHAN[truc])
            + " (không chắc thì \"khac\"). Giữ nguyên mọi khoá khác như yêu cầu ở trên.")


def gan_nhan(truc: str, ban: Any, kieu_llm: Any = None) -> Tuple[List[str], List[bool]]:
    """Nhãn mỗi phương án: của LLM nếu hợp lệ, không thì regex (`doan`=True)."""
    kl = kieu_llm if isinstance(kieu_llm, dict) else {}
    nhan, doan = [], []
    for i, b in enumerate(ban):
        v = chuan_nhan(truc, kl.get(chr(65 + i)) or kl.get(chr(97 + i)))
        nhan.append(v or _REGEX_NHAN[truc](b))
        doan.append(not v)
    return nhan, doan


def he_so_chon(goc: str, ma_kenh: str, truc: str, nhan: Any, hat: str) -> Dict[str, float]:
    """`{nhãn: hệ số}` = 0,9 + 0,2 × điểm rút Thompson. Trục chưa có ván kết luận → {} (không làm gì).
    Hạt giống tất định theo `hat` (kênh + mã gói)."""
    if not bang_diem(goc, ma_kenh).get(truc):
        return {}
    rd = rut(goc, ma_kenh, truc, sorted({n for n in nhan if n}), random.Random(hat))
    return {n: round(HE_SO_CHON_NEN + HE_SO_CHON_BIEN * r, 3) for n, r in rd.items()}


def bo_chon(goc: str, ma_kenh: str, truc: str, ban: Any, hat: str) -> Tuple[Any, Dict[str, Any]]:
    """`(sau_cham, ghi)` cho `viet_nhieu_ban.cham_va_chon(sau_cham=…)`: gắn nhãn, nhân hệ số vào điểm LLM,
    chọn lại phương án điểm cao nhất. Mọi thứ giải thích được nằm trong `ghi` (cập nhật khi callback chạy)."""
    ghi: Dict[str, Any] = {}

    def sau_cham(chon: int, diem: Dict[str, Any], kieu_llm: Any) -> int:
        nhan, doan = gan_nhan(truc, ban, kieu_llm)
        ghi.update(nhan=nhan, doan=doan)
        he = he_so_chon(goc, ma_kenh, truc, nhan, hat)
        if not he:
            return chon
        d0 = {i: _so(diem.get(chr(65 + i))) for i in range(len(ban)) if isinstance(diem, dict)}
        d0 = {i: v for i, v in d0.items() if v is not None}
        if len(d0) < 2:
            return chon
        d1 = {i: round(v * he.get(nhan[i], 1.0), 3) for i, v in d0.items()}
        moi = max(d1, key=lambda i: (d1[i], i == chon))
        ghi["he_so"] = {"truc": truc, "he_so": he, "diem_goc": {chr(65 + i): v for i, v in d0.items()},
                        "diem_sau": {chr(65 + i): v for i, v in d1.items()}, "chon_truoc": chon, "chon_sau": moi}
        return moi

    return sau_cham, ghi


def ket_nhan(truc: str, ban: Any, chon: int, ghi: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Nhãn của phương án ĐÃ CHỌN để ghi vào hồ sơ/ván. Callback chưa chạy (chấm hỏng) thì dùng regex."""
    ghi = ghi or {}
    if ghi.get("nhan") and 0 <= chon < len(ghi["nhan"]):
        nhan, doan = ghi["nhan"][chon], bool(ghi["doan"][chon])
    elif 0 <= chon < len(ban):
        nhan, doan = _REGEX_NHAN[truc](ban[chon]), True
    else:
        return {}
    ra: Dict[str, Any] = {truc: nhan, "nhan_doan": doan}
    if ghi.get("he_so"):
        ra["he_so_tu_hoc"] = ghi["he_so"]
    return ra


def _du_doan_tu(nguon: Dict[str, Any]) -> Dict[str, Any]:
    dd = ((nguon or {}).get("bien_tap") or {}).get("du_doan") or {}
    return {k: dd[k] for k in ("ctr_so", "avd_giay", "ket_cuc") if dd.get(k) is not None}


def ghi_van_tu_luot(goc: str, ma_kenh: str, ma_goi: str, nguon: Dict[str, Any]) -> None:
    """Nơi gọi lúc bàn giao: `nguon` = `run["nguon"]`. Hồ sơ video đã được `ban_giao` ghi trước đó."""
    ghi_van(goc, ma_kenh, ma_goi, _nuoc_tu(nguon or {}, _doc_ho_so(goc, ma_kenh, ma_goi), _ham_cum(goc, ma_kenh)),
            _du_doan_tu(nguon or {}))


# ── chấm ván ────────────────────────────────────────────────────────────────

def _so(x: Any) -> Optional[float]:
    try:
        return None if x is None or x == "" else float(x)
    except (TypeError, ValueError):
        return None


def _nguon_theo_goi(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{mã gói: run.nguon}` đọc thẳng sổ lượt (cần cả `cum`, `bien_tap.du_doan`)."""
    ra: Dict[str, Dict[str, Any]] = {}
    try:
        from .kenh import duong_kenh  # noqa: PLC0415

        tep = sorted(glob.glob(os.path.join(duong_kenh(goc, ma_kenh), "tu-chay", "*.json")))
    except Exception:  # noqa: BLE001
        return ra
    for duong in tep:
        try:
            with io.open(duong, encoding="utf-8") as f:
                runs = (json.load(f) or {}).get("runs") or []
        except (OSError, ValueError, AttributeError):
            continue
        for run in runs:
            if not isinstance(run, dict):
                continue
            ma = str(((run.get("ban_giao") or {}).get("ma_goi")) or "").strip()
            if ma and isinstance(run.get("nguon"), dict):
                ra[ma] = run["nguon"]
    return ra


def _gio_7d(hs: Dict[str, Any]) -> Optional[float]:
    return _so(((hs.get("chi_so") or {}).get("7d") or {}).get("gio_xem"))


def _trung_vi_7d(goc: str, ma_kenh: str, ho_so: Dict[str, Dict[str, Any]]) -> Tuple[Optional[float], str]:
    """`(trung vị giờ xem 7d, "kenh"|"nhom"|"")`: kênh đủ `N_TOI_THIEU_7D` video có số 7d thì của kênh,
    không thì của cả nhóm (nếu đủ `N_TOI_THIEU_NHOM`), không thì None."""
    own = [g for g in (_gio_7d(h) for h in ho_so.values()) if g is not None]
    if len(own) >= N_TOI_THIEU_7D:
        return statistics.median(own), "kenh"
    try:
        from .nhom_kenh import thanh_vien  # noqa: PLC0415
        from .chien_luoc.ket_qua import ho_so_theo_goi  # noqa: PLC0415

        nhom = [g for k in thanh_vien(goc, ma_kenh) for g in (_gio_7d(h) for h in ho_so_theo_goi(goc, k).values())
                if g is not None]
    except Exception:  # noqa: BLE001
        nhom = own
    return (statistics.median(nhom), "nhom") if len(nhom) >= N_TOI_THIEU_NHOM else (None, "")


def _moc(hs: Dict[str, Any]) -> Dict[str, Any]:
    cs = hs.get("chi_so") or {}
    for m in ("48h", "72h"):
        if isinstance(cs.get(m), dict) and cs[m]:
            return cs[m]
    return {}


def _lech(du_doan: Dict[str, Any], hs: Dict[str, Any]) -> Dict[str, float]:
    """Dự đoán − thật. CTR so với CTR trang chủ 48h (lùi CTR chung), AVD so với AVD giây."""
    m, ra = _moc(hs), {}
    thatctr = _so(m.get("ctr_trang_chu"))
    thatctr = _so(m.get("ctr")) if thatctr is None else thatctr
    if _so(du_doan.get("ctr_so")) is not None and thatctr is not None:
        ra["ctr"] = round(_so(du_doan["ctr_so"]) - thatctr, 2)
    if _so(du_doan.get("avd_giay")) is not None and _so(m.get("avd_giay")) is not None:
        ra["avd"] = round(_so(du_doan["avd_giay"]) - _so(m["avd_giay"]), 1)
    return ra


def cham_van(goc: str, ma_kenh: str) -> Dict[str, int]:
    """Bù ván từ hồ sơ video + sổ lượt cho gói chưa có ván, rồi chấm ván chưa kết luận. Không ném lỗi số liệu."""
    from .chien_luoc import ket_qua  # noqa: PLC0415

    van = doc_van(goc, ma_kenh)
    ho_so = ket_qua.ho_so_theo_goi(goc, ma_kenh)
    nguon_so = None
    cum_cua = None
    moi = 0
    for ma, hs in ho_so.items():
        if ma in van:
            continue
        if nguon_so is None:
            nguon_so, cum_cua = _nguon_theo_goi(goc, ma_kenh), _ham_cum(goc, ma_kenh)
        ng = nguon_so.get(ma) or {}
        nuoc = {k: v for k, v in _nuoc_tu(ng, hs, cum_cua).items() if v}
        van[ma] = {"ma_goi": ma, "nuoc": nuoc, "du_doan": _du_doan_tu(ng), "ngay": str(hs.get("ngay_dang") or ""),
                   "tu_cu": True}
        moi += 1
    bu = 0
    for ma, v in van.items():  # bù nhãn đợt 2 cho ván cũ (regex, không gọi LLM)
        hs = ho_so.get(ma) or {}
        if hs and "kieu_tieu_de" not in (v.get("nuoc") or {}):
            them = _nhan_dot2(hs)
            if them:
                v["nuoc"] = dict(v.get("nuoc") or {}, **them)
                bu += 1
    moi += bu
    vm_theo_id: Optional[Dict[str, Any]] = None
    nguong: Optional[float] = None
    tv7: Optional[Tuple[Optional[float], str]] = None
    so48 = so7 = 0
    for ma, v in van.items():
        hs = ho_so.get(ma) or {}
        if not hs:
            continue
        if not v.get("ket48"):
            if vm_theo_id is None:
                vm_theo_id, nguong = ket_qua.video_kenh(goc, ma_kenh)
            vid = str(hs.get("video_id") or "")
            kl = ket_qua.ket_luan(vm_theo_id.get(vid) if vid else None, hs, nguong) if (vid or hs.get("chi_so")) else ""
            if kl:
                v["ket48"] = kl
                so48 += 1
        if _moc(hs) and "lech" not in v:
            lech = _lech(v.get("du_doan") or {}, hs)
            if lech:
                v["lech"] = lech
            dd = _CHIEU.get(str((v.get("du_doan") or {}).get("ket_cuc") or "").strip().lower())
            if dd and v.get("ket48"):
                v["dung"] = dd == v["ket48"]
        if not v.get("ket7") and _gio_7d(hs) is not None:
            if tv7 is None:
                tv7 = _trung_vi_7d(goc, ma_kenh, ho_so)
            if tv7[0] is not None:
                v["ket7"] = "thang" if _gio_7d(hs) >= tv7[0] else "truot"
                v["so_voi_7d"] = tv7[1]
                so7 += 1
    if moi or so48 or so7:
        _luu_van(goc, ma_kenh, van)
    return {"van": len(van), "moi": moi, "ket48": so48, "ket7": so7}


# ── bảng điểm, Thompson ─────────────────────────────────────────────────────

def _dem(van: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, List[float]]]:
    """`{trục: {giá trị: [thắng có trọng số, trượt có trọng số, n ván có kết luận, n thắng]}}`."""
    ra: Dict[str, Dict[str, List[float]]] = {}
    for v in van.values():
        kl, w = (v.get("ket7"), TRONG_SO_7D) if v.get("ket7") else (v.get("ket48"), TRONG_SO_48H)
        if kl not in ("thang", "truot"):
            continue
        for truc in TRUC:
            gt = str((v.get("nuoc") or {}).get(truc) or "")
            if not gt:
                continue
            o = ra.setdefault(truc, {}).setdefault(gt, [0.0, 0.0, 0, 0])
            o[0 if kl == "thang" else 1] += w
            o[2] += 1
            o[3] += 1 if kl == "thang" else 0
    return ra


def bang_diem(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """`{trục: {giá trị: {"a", "b", "n", "thang"}}}` — a/b là tham số Beta (đã cộng tiên nghiệm nhóm × 0,3)."""
    own = _dem(doc_van(goc, ma_kenh))
    nhom: Dict[str, Dict[str, List[float]]] = {}
    try:
        from .nhom_kenh import thanh_vien  # noqa: PLC0415

        for k in thanh_vien(goc, ma_kenh):
            if k == ma_kenh:
                continue
            for truc, gts in _dem(doc_van(goc, k)).items():
                for gt, o in gts.items():
                    t = nhom.setdefault(truc, {}).setdefault(gt, [0.0, 0.0, 0, 0])
                    t[0] += o[0]
                    t[1] += o[1]
    except Exception:  # noqa: BLE001
        pass
    ra: Dict[str, Dict[str, Dict[str, float]]] = {}
    for truc in set(own) | set(nhom):
        for gt in set(own.get(truc, {})) | set(nhom.get(truc, {})):
            o = own.get(truc, {}).get(gt, [0.0, 0.0, 0, 0])
            p = nhom.get(truc, {}).get(gt, [0.0, 0.0, 0, 0])
            ra.setdefault(truc, {})[gt] = {"a": 1 + o[0] + HE_SO_NHOM * p[0], "b": 1 + o[1] + HE_SO_NHOM * p[1],
                                           "n": int(o[2]), "thang": int(o[3])}
    return ra


def rut(goc: str, ma_kenh: str, truc: str, cac_gia_tri: Any, rng: Optional[random.Random] = None) -> Dict[str, float]:
    """Thompson sampling: `{giá trị: điểm rút 0..1}`. Giá trị chưa từng có dùng Beta(1,1)."""
    rng = rng or random.Random()
    bd = bang_diem(goc, ma_kenh).get(truc, {})
    return {str(g): rng.betavariate((bd.get(str(g)) or {}).get("a", 1.0), (bd.get(str(g)) or {}).get("b", 1.0))
            for g in cac_gia_tri}


# ── hiệu chỉnh dự đoán (đợt 3, 03/10/2026) ───────────────────────────────────

def hieu_chinh(goc: str, ma_kenh: str) -> Dict[str, Any]:
    """Biên tập đoán lệch bao nhiêu — từ các ván có CẢ dự đoán lẫn số thật (`lech`/`dung` do `cham_van` ghi).
    `{n, lech_ctr_pct (tương đối %, + = đoán cao hơn thật), n_ctr, lech_avd_giay, n_avd, dung, tong_dung,
    ti_le_dung}`; n < 2 thì `{}`. Chỉ tính bằng mã, không LLM."""
    ctr, avd, dung, n = [], [], [], 0
    for v in doc_van(goc, ma_kenh).values():
        lech = v.get("lech") if isinstance(v.get("lech"), dict) else {}
        co = False
        dd = _so((v.get("du_doan") or {}).get("ctr_so"))
        if _so(lech.get("ctr")) is not None and dd is not None:
            that = dd - _so(lech["ctr"])
            if that > 0:
                ctr.append(_so(lech["ctr"]) / that * 100.0)
                co = True
        if _so(lech.get("avd")) is not None:
            avd.append(_so(lech["avd"]))
            co = True
        if "dung" in v:
            dung.append(bool(v["dung"]))
            co = True
        n += 1 if co else 0
    if n < 2:
        return {}
    return {"n": n, "lech_ctr_pct": round(sum(ctr) / len(ctr), 1) if ctr else None, "n_ctr": len(ctr),
            "lech_avd_giay": round(sum(avd) / len(avd), 1) if avd else None, "n_avd": len(avd),
            "dung": sum(dung), "tong_dung": len(dung), "ti_le_dung": round(sum(dung) / len(dung), 2) if dung else None}


def cau_hieu_chinh(goc: str, ma_kenh: str) -> str:
    """1–2 câu cho lời nhắc biên tập ("" khi n < 2). Chỉ nói phần có số."""
    h = hieu_chinh(goc, ma_kenh)
    if not h:
        return ""
    mau = []
    if h["lech_ctr_pct"] is not None:
        mau.append("bạn đoán CTR {0} thật trung bình {1:g}%".format(
            "cao hơn" if h["lech_ctr_pct"] > 0 else "thấp hơn", abs(h["lech_ctr_pct"])))
    if h["lech_avd_giay"] is not None:
        mau.append("đoán AVD {0} thật trung bình {1:g} giây".format(
            "cao hơn" if h["lech_avd_giay"] > 0 else "thấp hơn", abs(h["lech_avd_giay"])))
    if h["tong_dung"]:
        mau.append("đoán thắng/trượt đúng {0}/{1}".format(h["dung"], h["tong_dung"]))
    return "Hiệu chỉnh từ {0} video: {1}.".format(h["n"], "; ".join(mau)) if mau else ""


# ── bảng điểm cho người đọc ─────────────────────────────────────────────────

def ghi_bang_diem_md(goc: str, ma_kenh: str) -> str:
    van = doc_van(goc, ma_kenh)
    bd = bang_diem(goc, ma_kenh)
    d = ["# Bảng điểm tự học — {0}".format(ma_kenh), "",
         "{0} ván; {1} có kết quả 48h, {2} có kết quả 7 ngày. Thắng/n = số ván thắng / số ván đã có kết luận "
         "(ván 7d nặng 1, chỉ 48h nặng 0,5; số kênh cùng nhóm chỉ làm tiên nghiệm × {3}).".format(
             len(van), sum(1 for v in van.values() if v.get("ket48")), sum(1 for v in van.values() if v.get("ket7")),
             HE_SO_NHOM), ""]
    for truc in TRUC:
        if truc not in bd:
            continue
        d += ["## {0}".format(truc), "", "| giá trị | thắng/n | trung bình Beta |", "|---|---|---|"]
        for gt, o in sorted(bd[truc].items(), key=lambda x: -x[1]["a"] / (x[1]["a"] + x[1]["b"])):
            d.append("| {0} | {1}/{2} | {3:.2f} |".format(gt, o["thang"], o["n"], o["a"] / (o["a"] + o["b"])))
        d.append("")
    lech = [v["lech"] for v in van.values() if v.get("lech")]
    d += ["## Lệch dự đoán (dự đoán − thật)", ""]
    for khoa, ten, don_vi in (("ctr", "CTR", " điểm %"), ("avd", "AVD", " giây")):
        xs = [l[khoa] for l in lech if khoa in l]
        if xs:
            tb = sum(xs) / len(xs)
            d.append("- Biên tập đoán {0} {1} thật trung bình {2:.1f}{3} (n={4}).".format(
                ten, "CAO hơn" if tb > 0 else "THẤP hơn", abs(tb), don_vi, len(xs)))
    dung = [v["dung"] for v in van.values() if "dung" in v]
    if dung:
        d.append("- Đoán đúng thắng/trượt: {0}/{1}.".format(sum(dung), len(dung)))
    if not lech and not dung:
        d.append("- Chưa có ván nào vừa có dự đoán vừa có số thật.")
    try:  # đợt 3: trình độ dự đoán — theo dõi theo thời gian
        h = hieu_chinh(goc, ma_kenh)
        if h:
            d.append("- Trình độ dự đoán: {0}; lệch CTR {1}.".format(
                "đúng {0}/{1} ({2:.0f}%)".format(h["dung"], h["tong_dung"], 100 * h["ti_le_dung"])
                if h["tong_dung"] else "chưa có ván chấm thắng/trượt",
                "{0:+g}% (tương đối, n={1})".format(h["lech_ctr_pct"], h["n_ctr"]) if h["lech_ctr_pct"] is not None
                else "chưa có"))
    except Exception:  # noqa: BLE001
        pass
    duong = os.path.join(_thu_muc(goc, ma_kenh), "bang-diem.md")
    _ghi_nguyen_tu(duong, "\n".join(d) + "\n")
    return duong
