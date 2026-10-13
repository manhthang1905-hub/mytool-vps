"""**Sổ đối thủ CHUNG của nhóm** — mỗi kênh đối thủ MỘT dòng cho cả nhóm, sổ riêng từng kênh là bản chiếu.

Chủ dự án, 12/10/2026: *"dữ liệu đối thủ khi gộp all các kênh vào sẽ có 1 danh sách toàn diện — việc theo dõi
đối thủ sẽ ok — để phát hiện ra content đột biến … giúp tao đạt mục tiêu để các kênh nổ view, kiếm tiền".*

═══ VÌ SAO ═══

Đo 12/10/2026 (8 kênh nhóm tâm lý): 14.389 dòng sổ đối thủ (`CHANNEL/<k>/nghien-cuu/doi-thu.csv`) nhưng chỉ
1.843 khoá link khác nhau (1.813 kênh thật sau khi gộp `@handle` ↔ `/channel/UC…`) — mỗi kênh đối thủ được
ghi ~8 lần. Tệ hơn: `nhom_kenh.dong_bo_doi_thu` gộp HỘP THƯ của cả nhóm vào hộp thư từng kênh, nên kênh nào có sổ
cũ (TL4-T7, sổ đứng từ 21/09) thì lượt đầu tiên chấm lại TOÀN BỘ hộp thư: 1.542 kênh, mỗi kênh một lượt yt-dlp +
một lần ghi lại `kenh-do.json` 27 MB + một phán quyết ngách — 1,5 giờ để ra đúng những phán quyết anh em đã có.

═══ SỔ CHUNG ═══ `CHANNEL/_NHOM/<nhóm>/doi-thu-chung.json` (+ bản đọc `doi-thu-chung.csv`)

    {"phien_ban": 1, "nhom", "luc", "thanh_vien": [...], "thong_ke": {...},
     "bi_danh": {khoá link: "UC…"},                      # @handle/c/user → mã kênh (nhớ mãi)
     "gieo": {kênh ta: {khoá chuẩn: {"tu", "luc", "trang_thai"}}},   # dòng sổ chung đã gieo vào sổ riêng
     "kenh": {khoá chuẩn: {
        "khoa", "uc", "link", "lien_ket": [mọi dạng link], "ten",
        "so": {Subs, Số video, Dài TV, View TV, Vượt quy mô, AI, …},  "so_luc": lần quét của bộ số,
        "quet_luc", "lan_dau",
        "ngach": {"ket": giu|bo|nghi, "ngay", "ly_do", "nguon"},   # phán quyết NGÁCH (một lần cho cả nhóm)
        "song": {"ket": het|chet|lech_tieng, "ngay", "ly_do"},     # sức sống / kênh chết / sai tiếng
        "ban_dua": bool,                                           # chủ dự án tự tay đưa — luôn quét
        "trang_thai": theo dõi|hết|bỏ (đồng thuận), "gieo": {"trang_thai", "ghi_chu", "tu"} | None,
        "theo_kenh": {kênh ta: {tt, tuyen, ghi, cua, diem, ly, quet, lan_dau, link}},   # phán quyết RIÊNG
        "lien_quan": {kênh ta: {tc, pool, khop_tep, n_content}}}}}                   # khán giả / tệp

Khoá chuẩn = mã kênh `UC…` khi biết (ảnh chụp `kenh-do.json`, `quet-kenh/`, bí danh đã nhớ), không thì
`danh_ba_doi_thu.khoa(link)`.

═══ LUẬT ═══

1. **Sổ riêng là sự thật của phần RIÊNG** (tuyến, trạng thái khách đặt tay, ghi chú, cửa/điểm/lý do): mỗi lần gộp
   (`gop`) dựng lại sổ chung TỪ ĐẦU bằng mọi sổ riêng + kho phán quyết nhóm (`kenh-ai.json`) — không ghi chú nào bị
   mất vì nó nằm nguyên ở sổ riêng, và `theo_kenh` chép đủ từng ô.
2. **Phần CHUNG chỉ là sự thật về kênh đối thủ**: số đo (lần quét mới nhất thắng), phán quyết ngách theo NGHĨA của
   nhóm (đúng vai `kenh-ai.json` — `nghien_cuu_chung`), sức sống, cờ "bạn đưa — luôn quét".
3. **Gieo, không đè** (`ap_vao_so`): link nằm trong HỘP THƯ của một kênh mà sổ riêng của nó chưa có, nếu sổ chung
   đã có phán quyết đủ chắc → thêm thẳng vào sổ riêng (trạng thái + Ghi chú NGUYÊN VĂN của dòng anh em đã chấm,
   tuyến để trống cho kênh tự gán) — KHÔNG đo lại, KHÔNG hỏi AI lại. Dòng đã có thì chỉ làm mới số đo chung
   (`COT_SO_CHUNG`) khi sổ chung quét mới hơn; cột của khách (`danh_ba_doi_thu.COT_CUA_KHACH`) không bao giờ bị đè.
   Kênh vừa bật / sổ cũ / kênh mới tạo trong nhóm vì thế không phải chấm lại cả nghìn kênh.
4. Chỉ gieo phán quyết ĐỦ CHẮC: AI ngách (giữ/bỏ), hết (sức sống), kênh chết, sai tiếng, bạn đưa. KHÔNG gieo: "bỏ"
   chỉ vì từ khoá (cổng thể loại khác nhau theo tệp — `bo_qua_zatsugaku`), máy chấm cũ trước 30/09, ghi chú tay/trống,
   ⚠ NGHI. Kênh bật `cho_phep_tep_gia` (kho phán quyết ngách RIÊNG, `nghien_cuu_chung.duong_kenh_ai`) chỉ nhận gieo
   phần không phụ thuộc tệp (chết, sai tiếng, hết, bạn đưa); phán quyết ngách của nó cũng không vào phần chung.
5. Xoá hẳn một đối thủ ở một kênh (`danh_ba_doi_thu.xoa`, gỡ cả hộp thư) → không gieo lại cho kênh ấy trừ khi link
   quay về hộp thư (y luật cũ của `nhom_kenh.dong_bo_doi_thu`).

Nơi gọi: `chot_doi_thu.chot` (đầu lượt chấm hộp thư: gộp + gieo; cuối lượt: gộp lại), `mot_nut.chay` (gộp sau
bước quét), `radar_dot_bien` (đọc + cập nhật `lien_quan`). Kênh không khai `nhom` → không có sổ chung (sổ riêng của
nó vẫn là danh bạ duy nhất), mọi hàm ở đây là không-làm-gì.

    python -m core.so_doi_thu_chung --nhom <nhóm> [--goc <cây>] [--ghi] [--gieo] [--lien-quan]   # mặc định chạy thử

Không mạng, không AI, không Qt. Ghi nguyên tử dưới khoá ngắn (`nghien_cuu_chung._KhoaNgan`).
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import re
import sys
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import danh_ba_doi_thu as db

__all__ = ["TEP", "TEP_CSV", "COT_SO_CHUNG", "COT_SO_RIENG", "duong", "doc", "gop", "ap_vao_so",
           "dong_bo_truoc_chot", "gop_sau", "phan_loai_ghi_chu", "tra", "thanh_vien_nhom", "nhom_cua",
           "thong_ke_so"]

TEP = "doi-thu-chung.json"
TEP_CSV = "doi-thu-chung.csv"
PHIEN_BAN = 1

#: Số đo về CHÍNH kênh đối thủ — như nhau với mọi kênh ta: lần quét mới nhất thắng, được làm mới vào sổ riêng.
COT_SO_CHUNG = ("Subs", "Số video", "Dài TV", "View TV", "Vượt quy mô", "AI")
#: Cột tính từ bảng content CỦA TỪNG kênh (`danh_ba_doi_thu.cap_nhat_tu_bang`) — chỉ để xem trong sổ chung, không
#: chép vào sổ riêng (sổ riêng tự tính lại từ bảng của nó, "luôn khớp với thứ khách đang nhìn").
COT_SO_RIENG = ("Tuổi (tháng)", "View/tháng", "Im lặng", "Mới 7 ngày", "Đăng gần nhất")

GHI_CHU_BAN_DUA = "bạn đưa — luôn quét"
LOP_GIEO = ("ban_dua", "giu", "bo", "het", "chet", "lech_tieng")
#: Lớp gieo được cho kênh có kho ngách RIÊNG (`cho_phep_tep_gia`): không phụ thuộc tệp khán giả.
LOP_GIEO_RIENG = ("ban_dua", "het", "chet", "lech_tieng")
#: Thứ tự ưu tiên khi hai sự kiện cùng ngày.
_UU_TIEN = {"chet": 6, "lech_tieng": 5, "het": 4, "bo": 3, "giu": 2, "nghi": 1}
_RE_NGAY = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{4}))?")
_RE_UC = re.compile(r"^(UC[\w-]{20,24})$")


# ── đường / nhóm ─────────────────────────────────────────────────────────────

def nhom_cua(goc: str, kenh: str) -> str:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        return nhom_kenh.nhom_cua_kenh(goc, kenh)
    except Exception:  # noqa: BLE001
        return ""


def thanh_vien_nhom(goc: str, nhom: str) -> List[str]:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        return list(nhom_kenh._thanh_vien_cua_nhom(goc, nhom))  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return []


def thu_muc(goc: str, nhom: str) -> str:
    from . import nhom_kenh  # noqa: PLC0415

    return nhom_kenh.duong_thu_muc_nhom(goc, nhom)


def duong(goc: str, nhom: str) -> str:
    return os.path.join(thu_muc(goc, nhom), TEP)


def _doc_json(p: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def doc(goc: str, nhom: str) -> Dict[str, Any]:
    """Sổ chung đang có (`{}` khi chưa có / hỏng)."""
    du = _doc_json(duong(goc, nhom), {})
    return du if isinstance(du, dict) and isinstance(du.get("kenh"), dict) else {}


def ghi_json_gon(p: str, du: Any) -> None:
    """Ghi JSON GỌN (không thụt lề) nguyên tử — sổ chung ~1.800 kênh × 8 kênh ta, ghi vài lần mỗi lượt nghiên cứu."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = "{0}.{1}.tmp".format(p, os.getpid())
    with io.open(tam, "w", encoding="utf-8") as tep:
        tep.write(json.dumps(du, ensure_ascii=False, separators=(",", ":")))
    for lan in range(5):
        try:
            os.replace(tam, p)
            return
        except PermissionError:   # Windows: tệp đang bị mở đọc
            if lan == 4:
                raise
            time.sleep(0.2 * (lan + 1))


def _ghi(goc: str, nhom: str, du: Dict[str, Any]) -> str:
    p = duong(goc, nhom)
    ghi_json_gon(p, du)
    try:
        _ghi_csv(os.path.join(os.path.dirname(p), TEP_CSV), du)
    except OSError:
        pass  # bản đọc hỏng không làm hỏng sổ
    return p


def _khoa_ghi(goc: str, nhom: str):
    from .nghien_cuu_chung import _KhoaNgan  # noqa: PLC0415

    return _KhoaNgan(duong(goc, nhom), cho=20.0, cu=120.0)


# ── ngày / ghi chú ───────────────────────────────────────────────────────────

def _ngay_tu_dd_mm(chu: str, moc: _dt.date) -> str:
    """"30/09" → "2026-09-30" (năm suy theo `moc`: ngày sau mốc > 2 ngày → năm trước)."""
    m = _RE_NGAY.search(chu or "")
    if not m:
        return ""
    try:
        d, th = int(m.group(1)), int(m.group(2))
        nam = int(m.group(3)) if m.group(3) else moc.year
        ngay = _dt.date(nam, th, d)
    except ValueError:
        return ""
    if not m.group(3) and ngay > moc + _dt.timedelta(days=2):
        try:
            ngay = _dt.date(nam - 1, th, d)
        except ValueError:
            return ""
    return ngay.isoformat()


def _moc(quet: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(str(quet or "")[:10])
    except ValueError:
        return _dt.date.today()


def phan_loai_ghi_chu(ghi: str, quet: str = "") -> Tuple[str, str]:
    """Ghi chú một dòng sổ riêng → `(lớp, ngày ISO)`.

    Lớp: `ban_dua` · `giu` (AI: đúng ngách) · `bo` (AI: lạc ngách) · `nghi` · `het` (sức sống) · `chet` (kênh không
    còn) · `lech_tieng` · `tu_khoa` (bỏ chỉ vì từ khoá) · `may` (máy chấm cũ) · `tay` (trống / khách viết tay).
    Ngày: dd/mm trong ghi chú (dấu kiểm ngách), không có thì ngày của `quet` (Quét lúc của dòng).

    >>> phan_loai_ghi_chu("✓ AI kiểm ngách 12/10: chân dung tâm lý", "2026-10-12 05:00")
    ('giu', '2026-10-12')
    >>> phan_loai_ghi_chu("không phải kênh tâm lý — AI: toàn nhạc", "2026-10-01 10:00")[0]
    'bo'
    >>> phan_loai_ghi_chu("")[0]
    'tay'
    """
    g = str(ghi or "").strip()
    moc = _moc(quet)
    ngay_quet = moc.isoformat() if quet else ""
    if not g:
        return "tay", ""
    if g.startswith(GHI_CHU_BAN_DUA):
        return "ban_dua", ngay_quet
    if g.startswith("✓ AI kiểm ngách"):
        return "giu", _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("⚠ NGHI"):
        return "nghi", _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("Hết"):
        return "het", _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("AI kiểm ngách"):
        try:
            from .kiem_ngach_doi_thu import la_bo_suc_song  # noqa: PLC0415

            suc_song = la_bo_suc_song(g)
        except Exception:  # noqa: BLE001
            suc_song = False
        return ("het" if suc_song else "bo"), _ngay_tu_dd_mm(g.split(":", 1)[0], moc) or ngay_quet
    if g.startswith("không phải kênh tâm lý — "):
        return "bo", ngay_quet
    if g.startswith("AI: đối thủ") or g.startswith("AI ("):
        return "giu", ngay_quet
    if g.startswith("kênh không còn hoặc không xem được"):
        return "chet", ngay_quet
    if g.startswith("không phải tiếng của kênh"):
        return "lech_tieng", ngay_quet
    if g.startswith("không phải kênh tâm lý:"):
        return "tu_khoa", ngay_quet
    if g.startswith(("thị trường (", "máy chấm:")):
        return "may", ngay_quet
    return "tay", ngay_quet


# ── bí danh (mã kênh UC…) ────────────────────────────────────────────────────

_NHO_BI_DANH: Dict[str, Tuple[Tuple[float, ...], Dict[str, str]]] = {}


def _them_bi_danh(ra: Dict[str, str], ch: Dict[str, Any]) -> None:
    cid = str((ch or {}).get("channel_id") or "").strip()
    if not _RE_UC.match(cid):
        return
    for l in ((ch or {}).get("input_url"), (ch or {}).get("channel_url"),
              "https://www.youtube.com/channel/" + cid,
              ("https://www.youtube.com/" + str(ch.get("handle"))) if str((ch or {}).get("handle") or "").startswith("@")
              else ""):
        k = db.khoa(str(l or ""))
        if k:
            ra.setdefault(k, cid)


def bang_bi_danh(goc: str, nhom: str, cu: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """`{khoá link: "UC…"}` từ ảnh chụp kênh của kho nhóm (`kenh-do.json`, `quet-kenh/*.json`) + bí danh đã nhớ.
    `kenh-do.json` ~27 MB → nhớ trong tiến trình theo giờ sửa tệp."""
    ra: Dict[str, str] = dict(cu or {})
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        kho = os.path.join(thu_muc(goc, nhom), ncc.THU_MUC)
    except Exception:  # noqa: BLE001
        return ra
    p_do = os.path.join(kho, ncc.TEP_KENH_DO)
    d_q = os.path.join(kho, ncc.THU_MUC_QUET)
    try:
        dau = (os.path.getmtime(p_do), float(os.path.getsize(p_do)))
    except OSError:
        dau = (0.0, 0.0)
    try:
        dau = dau + (os.path.getmtime(d_q),)
    except OSError:
        pass
    nho = _NHO_BI_DANH.get(kho)
    if nho is None or nho[0] != dau:
        moi: Dict[str, str] = {}
        du = _doc_json(p_do, {}) or {}
        if isinstance(du, dict):
            for m in du.values():
                if isinstance(m, dict):
                    _them_bi_danh(moi, m.get("ch") or {})
        try:
            ten = os.listdir(d_q)
        except OSError:
            ten = []
        for t in ten:
            if t.endswith(".json"):
                m = _doc_json(os.path.join(d_q, t), {}) or {}
                if isinstance(m, dict):
                    _them_bi_danh(moi, m.get("ch") or {})
        _NHO_BI_DANH[kho] = (dau, moi)
        nho = _NHO_BI_DANH[kho]
    for k, v in nho[1].items():
        ra.setdefault(k, v)
    return ra


def khoa_chuan(link: str, bi_danh: Dict[str, str]) -> str:
    """Khoá chuẩn của một link kênh: mã `UC…` khi biết, không thì `danh_ba_doi_thu.khoa`."""
    k = db.khoa(link)
    if not k:
        return ""
    if k in bi_danh:
        return bi_danh[k]
    if k.lower().startswith("channel/"):
        uc = k.split("/", 1)[1]
        if _RE_UC.match(uc):
            return uc
    return k


# ── đọc sổ riêng + kho phán quyết ────────────────────────────────────────────

def _rieng(goc: str, kenh: str) -> bool:
    """Kênh dùng kho phán quyết ngách RIÊNG (`cho_phep_tep_gia`) — xem luật 4."""
    try:
        from .phan_tuyen import cho_phep_tep_gia  # noqa: PLC0415

        return bool(cho_phep_tep_gia(goc, kenh))
    except Exception:  # noqa: BLE001
        return False


def _ban_dua(goc: str, kenh: str) -> Set[str]:
    try:
        from .doi_thu_kenh import doc_ban_dua  # noqa: PLC0415

        return {k for k in (db.khoa(l) for l in doc_ban_dua(goc, kenh)) if k}
    except Exception:  # noqa: BLE001
        return set()


def _kenh_ai_nhom(goc: str, nhom: str) -> Dict[str, Dict[str, Any]]:
    """Kho phán quyết ngách CHUNG của nhóm (`CHANNEL/_NHOM/<nhóm>/nghien-cuu/kenh-ai.json`)."""
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        p = os.path.join(thu_muc(goc, nhom), ncc.THU_MUC, ncc.TEP_KENH_AI)
    except Exception:  # noqa: BLE001
        return {}
    du = _doc_json(p, {}) or {}
    return du if isinstance(du, dict) else {}


def _lop_kenh_ai(m: Dict[str, Any]) -> str:
    kn = str(m.get("kiem_ngach") or "").strip().lower()
    if kn in ("giu", "bo", "nghi"):
        return kn
    return {"doi_thu": "giu", "khong": "bo", "gan": "bo"}.get(str(m.get("ket") or "").strip().lower(), "")


def _o(dong: Sequence[str], o: Dict[str, int], ten: str) -> str:
    i = o.get(ten)
    return str(dong[i]).strip() if i is not None and i < len(dong) else ""


# ── gộp ──────────────────────────────────────────────────────────────────────

def _dung_lai(goc: str, nhom: str, thanh_vien: Sequence[str], cu: Dict[str, Any]) -> Dict[str, Any]:
    """Dựng sổ chung TỪ ĐẦU (luật 1). `cu` = sổ cũ — chỉ mang sang bí danh, mốc gieo, lần đầu thấy, liên quan."""
    bi = bang_bi_danh(goc, nhom, cu.get("bi_danh") or {})
    kenh_cu = cu.get("kenh") or {}
    for e in kenh_cu.values():   # bí danh suy từ sổ cũ: mọi link của một dòng UC… là bí danh của mã ấy
        if isinstance(e, dict) and _RE_UC.match(str(e.get("khoa") or "")):
            for l in e.get("lien_ket") or []:
                k = db.khoa(l)
                if k:
                    bi.setdefault(k, e["khoa"])
    kenh: Dict[str, Dict[str, Any]] = {}
    rieng = {m: _rieng(goc, m) for m in thanh_vien}
    n_dong = 0
    for m in thanh_vien:
        cot, hang = db.doc(goc, m)
        o = db.chi_so_cot(list(cot))
        if o.get("Link kênh") is None:
            continue
        bd = _ban_dua(goc, m)
        for d in hang:
            link = _o(d, o, "Link kênh")
            k = khoa_chuan(link, bi)
            if not k:
                continue
            n_dong += 1
            e = kenh.get(k)
            if e is None:
                e = kenh[k] = {"khoa": k, "uc": k if _RE_UC.match(k) else "", "link": link, "lien_ket": [],
                               "ten": "", "so": {}, "so_luc": "", "quet_luc": "", "lan_dau": "",
                               "ban_dua": False, "theo_kenh": {}, "_su_kien": []}
            if link not in e["lien_ket"]:
                e["lien_ket"].append(link)
            quet = _o(d, o, "Quét lúc")
            ten = _o(d, o, "Kênh")
            moi_hon = quet >= e["so_luc"]
            if ten and (moi_hon or not e["ten"]):
                e["ten"] = ten
            if ten and ten not in e.setdefault("ten_khac", []):
                e["ten_khac"].append(ten)   # sổ content nối với danh bạ bằng TÊN — radar tra mọi tên từng thấy
            for c in COT_SO_CHUNG + COT_SO_RIENG:
                v = _o(d, o, c)
                if v and (moi_hon or not e["so"].get(c)):
                    e["so"][c] = v
            if moi_hon and quet:
                e["so_luc"] = quet
                e["link"] = link
            e["quet_luc"] = max(e["quet_luc"], quet)
            ld = _o(d, o, "Lần đầu thấy")
            if ld and (not e["lan_dau"] or ld < e["lan_dau"]):
                e["lan_dau"] = ld
            ghi = _o(d, o, "Ghi chú")
            tt = _o(d, o, "Trạng thái")
            ban = {"tt": tt, "tuyen": _o(d, o, "Tuyến"), "ghi": ghi, "cua": _o(d, o, "Cửa"),
                   "diem": _o(d, o, "Điểm"), "ly": _o(d, o, "Lý do"), "quet": quet, "lan_dau": ld, "link": link}
            ban = {a: b for a, b in ban.items() if b or a == "tt"}   # ô trống không ghi (sổ gọn); đọc bằng .get
            if m in e["theo_kenh"]:
                # Cùng một kênh hai dòng trong MỘT sổ (`@handle` + `/channel/UC…` — quét ghi link yt-dlp trả về):
                # dòng đầu là dòng chính, dòng sau giữ nguyên văn ở `trung` (không mất ghi chú nào).
                e["theo_kenh"][m].setdefault("trung", []).append(ban)
            else:
                e["theo_kenh"][m] = ban
            lop, ngay = phan_loai_ghi_chu(ghi, quet)
            if lop == "ban_dua" or db.khoa(link) in bd:
                e["ban_dua"] = True
            if lop in ("giu", "bo", "nghi") and rieng.get(m):
                continue   # phán quyết ngách theo TỆP của kênh có kho riêng — không phải sự thật chung
            if lop in ("giu", "bo", "nghi", "het", "chet", "lech_tieng"):
                e["_su_kien"].append((ngay, _UU_TIEN[lop], lop, m, ghi))
    # Kho phán quyết ngách của nhóm (nguồn sự thật về ngách — `kiem_ngach_doi_thu`).
    kai = _kenh_ai_nhom(goc, nhom)
    tra_ai: Dict[str, Dict[str, Any]] = {}
    for l, m in kai.items():
        if isinstance(m, dict):
            k = khoa_chuan(str(l), bi)
            if k and (k not in tra_ai or str(m.get("ngay") or "") > str(tra_ai[k].get("ngay") or "")):
                tra_ai[k] = m
    for k, e in kenh.items():
        ev = sorted(e.pop("_su_kien"), key=lambda x: (x[0], x[1]))
        m = tra_ai.get(k)
        lop_ai = _lop_kenh_ai(m) if m else ""
        ngach = None
        dong_ngach = [x for x in ev if x[2] in ("giu", "bo", "nghi")]
        if dong_ngach:
            x = dong_ngach[-1]
            ngach = {"ket": x[2], "ngay": x[0], "ly_do": x[4][:200], "nguon": "so:" + x[3]}
        if lop_ai and (ngach is None or str(m.get("ngay") or "") >= ngach["ngay"]):
            ngach = {"ket": lop_ai, "ngay": str(m.get("ngay") or ""), "ly_do": str(m.get("ly_do") or "")[:200],
                     "nguon": "kenh-ai"}
        e["ngach"] = ngach
        song = None
        for x in ev:
            if x[2] in ("chet", "lech_tieng"):
                song = {"ket": x[2], "ngay": x[0], "ly_do": x[4][:200], "nguon": "so:" + x[3]}
        if song is None:
            het = [x for x in ev if x[2] == "het"]
            giu = [x for x in ev if x[2] == "giu"]
            if het and (not giu or het[-1][0] >= giu[-1][0]):
                x = het[-1]
                song = {"ket": "het", "ngay": x[0], "ly_do": x[4][:200], "nguon": "so:" + x[3]}
        e["song"] = song
        e["gieo"] = _phan_quyet_gieo(e, ev)
        e["trang_thai"] = (e["gieo"] or {}).get("trang_thai") or _da_so(e)
        e["lien_quan"] = dict((kenh_cu.get(k) or {}).get("lien_quan") or {})
        if (kenh_cu.get(k) or {}).get("lan_dau") and (not e["lan_dau"] or kenh_cu[k]["lan_dau"] < e["lan_dau"]):
            e["lan_dau"] = kenh_cu[k]["lan_dau"]
    for k, e in kenh.items():
        for l in e["lien_ket"]:
            kk = db.khoa(l)
            if kk and _RE_UC.match(k):
                bi[kk] = k
    du = {"phien_ban": PHIEN_BAN, "nhom": nhom, "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
          "thanh_vien": list(thanh_vien), "bi_danh": bi, "gieo": dict(cu.get("gieo") or {}), "kenh": kenh}
    du["thong_ke"] = thong_ke_so(du, n_dong=n_dong)
    return du


def _da_so(e: Dict[str, Any]) -> str:
    dem: Dict[str, int] = {}
    for x in (e.get("theo_kenh") or {}).values():
        t = x.get("tt") or db.THEO_DOI
        dem[t] = dem.get(t, 0) + 1
    return max(dem.items(), key=lambda kv: (kv[1], kv[0] == db.THEO_DOI))[0] if dem else ""


def _phan_quyet_gieo(e: Dict[str, Any], ev: Sequence[Tuple[str, int, str, str, str]]) -> Optional[Dict[str, Any]]:
    """Trạng thái + Ghi chú NGUYÊN VĂN để gieo dòng này vào sổ riêng còn thiếu (luật 3–4), hoặc None."""
    def ghi_cua(lop: str) -> Tuple[str, str]:
        ds = [x for x in ev if x[2] == lop]
        return (ds[-1][4], ds[-1][3]) if ds else ("", "")
    song, ngach = e.get("song") or {}, e.get("ngach") or {}
    # Thứ tự = thứ tự của cửa duyệt `chot_doi_thu._chot`: kênh chết / sai tiếng → sức sống (cả kênh bạn đưa) →
    # bạn đưa (luôn quét, không hỏi AI) → phán quyết ngách.
    if song.get("ket") in ("chet", "lech_tieng"):
        g, tu = ghi_cua(song["ket"])
        return {"trang_thai": db.BO, "ghi_chu": g, "tu": tu, "lop": song["ket"]}
    if song.get("ket") == "het":
        g, tu = ghi_cua("het")
        return {"trang_thai": db.HET, "ghi_chu": g, "tu": tu, "lop": "het"}
    if e.get("ban_dua"):
        g, tu = "", ""
        for m, x in (e.get("theo_kenh") or {}).items():
            if str(x.get("ghi") or "").startswith(GHI_CHU_BAN_DUA):
                g, tu = x["ghi"], m
                break
        return {"trang_thai": db.THEO_DOI, "ghi_chu": g or GHI_CHU_BAN_DUA, "tu": tu, "lop": "ban_dua"}
    if ngach.get("ket") == "bo":
        g, tu = ghi_cua("bo")
        if not g:
            g = "không phải kênh tâm lý — AI (sổ chung {0}): {1}".format(_dd_mm(ngach.get("ngay")),
                                                                        str(ngach.get("ly_do") or "")[:150])
            tu = "kenh-ai"
        return {"trang_thai": db.BO, "ghi_chu": g, "tu": tu, "lop": "bo"}
    if ngach.get("ket") == "giu":
        g, tu = ghi_cua("giu")
        if not g:
            g = "AI (sổ chung {0}): đối thủ — {1}".format(_dd_mm(ngach.get("ngay")), str(ngach.get("ly_do") or "")[:150])
            tu = "kenh-ai"
        return {"trang_thai": db.THEO_DOI, "ghi_chu": g, "tu": tu, "lop": "giu"}
    return None


def _dd_mm(ngay: Any) -> str:
    s = str(ngay or "")
    return "{0}/{1}".format(s[8:10], s[5:7]) if len(s) >= 10 else "?"


def thong_ke_so(du: Dict[str, Any], *, n_dong: Optional[int] = None) -> Dict[str, Any]:
    kenh = du.get("kenh") or {}
    tt: Dict[str, int] = {}
    gieo: Dict[str, int] = {}
    for e in kenh.values():
        tt[e.get("trang_thai") or "?"] = tt.get(e.get("trang_thai") or "?", 0) + 1
        g = (e.get("gieo") or {}).get("lop") or "khong"
        gieo[g] = gieo.get(g, 0) + 1
    ra = {"kenh": len(kenh), "trang_thai": tt, "gieo_duoc": gieo,
          "uc": sum(1 for e in kenh.values() if e.get("uc")),
          "ban_dua": sum(1 for e in kenh.values() if e.get("ban_dua")),
          "ghi_chu_rieng": sum(1 for e in kenh.values() for x in (e.get("theo_kenh") or {}).values() if x.get("ghi"))}
    if n_dong is not None:
        ra["dong_so_rieng"] = n_dong
    return ra


def gop(goc: str, nhom: str, *, thanh_vien: Optional[Sequence[str]] = None, ghi: bool = True,
        lien_quan: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None) -> Dict[str, Any]:
    """Dựng lại sổ chung của `nhom` từ mọi sổ riêng + kho phán quyết (luật 1–2) và ghi (`ghi=True`). Trả sổ.
    `lien_quan` (`{khoá: {kênh: {...}}}`, `radar_dot_bien` tính) → ghi đè phần liên quan của các dòng ấy."""
    tv = list(thanh_vien) if thanh_vien is not None else thanh_vien_nhom(goc, nhom)
    if not nhom or not tv:
        return {}
    if not ghi:
        du = _dung_lai(goc, nhom, tv, doc(goc, nhom))
        _ap_lien_quan(du, lien_quan)
        return du
    with _khoa_ghi(goc, nhom):
        du = _dung_lai(goc, nhom, tv, doc(goc, nhom))
        _ap_lien_quan(du, lien_quan)
        _ghi(goc, nhom, du)
    return du


def _ap_lien_quan(du: Dict[str, Any], lien_quan: Optional[Dict[str, Dict[str, Dict[str, Any]]]]) -> None:
    for k, x in (lien_quan or {}).items():
        e = (du.get("kenh") or {}).get(k)
        if e is not None and isinstance(x, dict):
            e["lien_quan"] = x


# ── gieo vào sổ riêng ────────────────────────────────────────────────────────

def ap_vao_so(goc: str, kenh: str, *, du: Optional[Dict[str, Any]] = None, ghi: bool = True,
              ban_dua: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Gieo phán quyết sổ chung vào sổ riêng của `kenh` (luật 3–5). Trả `{"gieo", "lam_moi", "bo_qua",
    "theo_lop": {...}, "links": [...]}`. `ghi=False` → chỉ đếm (chạy thử)."""
    dem: Dict[str, Any] = {"gieo": 0, "lam_moi": 0, "bo_qua": 0, "theo_lop": {}, "links": []}
    nhom = nhom_cua(goc, kenh)
    if not nhom:
        return dem
    du = du if du is not None else doc(goc, nhom)
    if not du.get("kenh"):
        return dem
    bi = du.get("bi_danh") or {}
    rieng = _rieng(goc, kenh)
    lop_duoc = LOP_GIEO_RIENG if rieng else LOP_GIEO
    cot, hang = db.doc(goc, kenh)
    cot = list(cot)
    o = db.chi_so_cot(cot)
    if o.get("Link kênh") is None:
        return dem
    hang = [list(d) + [""] * (len(cot) - len(d)) for d in hang]
    co: Dict[str, int] = {}
    for i, d in enumerate(hang):
        k = khoa_chuan(_o(d, o, "Link kênh"), bi)
        if k and k not in co:
            co[k] = i
    doi = False
    # (a) làm mới số đo chung của dòng đã có: ô TRỐNG thì điền; dòng "theo dõi" mà sổ chung quét mới hơn
    #     ≥ `NGAY_LAM_MOI` ngày thì đè (dòng bỏ/hết không ai dùng số của nó — không xáo sổ vô ích).
    for k, i in co.items():
        e = du["kenh"].get(k)
        if not e:
            continue
        d = hang[i]
        q = _o(d, o, "Quét lúc")
        de = (_o(d, o, "Trạng thái") or db.THEO_DOI) == db.THEO_DOI and bool(e.get("so_luc")) \
            and _cach_ngay(q, e["so_luc"]) >= NGAY_LAM_MOI
        sua = False
        for c in COT_SO_CHUNG:
            j = o.get(c)
            v = str((e.get("so") or {}).get(c) or "")
            if j is not None and v and d[j] != v and (de or not str(d[j]).strip()):
                d[j] = v
                sua = True
        if sua:
            dem["lam_moi"] += 1
            doi = True
    # (b) gieo link hộp thư chưa có trong sổ riêng
    them: List[Tuple[str, Dict[str, Any], str]] = []
    thay: Set[str] = set(co)
    for link in db.hop_thu(goc, kenh):
        k = khoa_chuan(link, bi)
        if not k or k in thay:
            continue
        e = du["kenh"].get(k)
        g = (e or {}).get("gieo")
        if not e or not g or g.get("lop") not in lop_duoc:
            dem["bo_qua"] += 1
            continue
        thay.add(k)
        them.append((link, e, k))
    luc = time.strftime("%Y-%m-%dT%H:%M:%S")
    so_gieo = du.setdefault("gieo", {}).setdefault(kenh, {}) if ghi else {}
    for link, e, k in them:
        g = e["gieo"]
        d = [""] * len(cot)
        d[o["Link kênh"]] = link
        if "Kênh" in o:
            d[o["Kênh"]] = e.get("ten") or db._ten_tu_link(link)  # noqa: SLF001
        if "Trạng thái" in o:
            d[o["Trạng thái"]] = g["trang_thai"]
        if "Ghi chú" in o:
            d[o["Ghi chú"]] = g.get("ghi_chu") or ""
        if "Lần đầu thấy" in o:
            d[o["Lần đầu thấy"]] = e.get("lan_dau") or luc[:10]
        for c in COT_SO_CHUNG:
            if c in o and (e.get("so") or {}).get(c):
                d[o[c]] = str(e["so"][c])
        hang.append(d)
        dem["gieo"] += 1
        dem["theo_lop"][g["lop"]] = dem["theo_lop"].get(g["lop"], 0) + 1
        dem["links"].append(link)
        so_gieo[k] = {"tu": g.get("tu") or "", "luc": luc, "trang_thai": g["trang_thai"]}
        doi = True
    if doi and ghi:
        db.luu(goc, kenh, cot, hang)
    return dem


#: Dòng "theo dõi" của sổ riêng được đè số đo chung khi sổ chung quét mới hơn ngần này ngày.
NGAY_LAM_MOI = 3.0


def _cach_ngay(cu: str, moi: str) -> float:
    """Số ngày `moi` sau `cu` ("YYYY-MM-DD HH:MM"); `cu` trống → vô cực."""
    def ep(s: str) -> Optional[float]:
        for dang, dai in (("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
            try:
                return time.mktime(_dt.datetime.strptime(str(s or "")[:dai], dang).timetuple())
            except ValueError:
                continue
        return None
    a, b = ep(cu), ep(moi)
    if b is None:
        return 0.0
    if a is None:
        return float("inf")
    return (b - a) / 86400.0


def dong_bo_truoc_chot(goc: str, kenh: str, *, on_log: Optional[Callable[[str], None]] = None,
                       ghi: bool = True) -> Dict[str, Any]:
    """Đầu lượt chấm hộp thư của `kenh`: gộp sổ chung (mọi sổ riêng mới nhất) rồi gieo vào sổ của `kenh`.
    Không nhóm / lỗi → `{}` (lượt chấm đi như cũ). Không bao giờ ném."""
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return {}
        t0 = time.time()
        if not ghi:
            du = gop(goc, nhom, ghi=False)
            return ap_vao_so(goc, kenh, du=du, ghi=False) if du else {}
        with _khoa_ghi(goc, nhom):
            tv = thanh_vien_nhom(goc, nhom)
            du = _dung_lai(goc, nhom, tv, doc(goc, nhom))
            dem = ap_vao_so(goc, kenh, du=du, ghi=True)
            if dem.get("gieo") or dem.get("lam_moi"):
                # sổ riêng vừa đổi → dựng lại để sổ chung ghi ra khớp mọi sổ riêng (`gop_sau` bỏ qua theo giờ sửa)
                du = _dung_lai(goc, nhom, tv, du)
            _ghi(goc, nhom, du)
        if on_log is not None and (dem.get("gieo") or dem.get("lam_moi")):
            on_log("  sổ đối thủ chung ({0} kênh): gieo {1} kênh anh em đã chấm vào sổ {2} ({3}) — không đo lại, "
                   "không hỏi AI lại · làm mới số đo {4} dòng · {5:.1f}s".format(
                       len(du.get("kenh") or {}), dem["gieo"], kenh,
                       ", ".join("{0} {1}".format(a, b) for a, b in sorted(dem["theo_lop"].items())) or "—",
                       dem["lam_moi"], time.time() - t0))
        return dem
    except Exception as loi:  # noqa: BLE001 — sổ chung hỏng không được chặn lượt chấm
        if on_log is not None:
            on_log("  sổ đối thủ chung hỏng, chấm như cũ: {0}: {1}".format(type(loi).__name__, str(loi)[:160]))
        return {}


def gop_sau(goc: str, kenh: str, *, on_log: Optional[Callable[[str], None]] = None) -> None:
    """Sau một bước ghi sổ riêng của `kenh` (chấm hộp thư, quét): gộp lại sổ chung để kênh anh em kế tiếp thấy ngay —
    bỏ qua khi sổ riêng không đổi từ lần gộp trước (giờ sửa tệp). Không bao giờ ném."""
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom:
            return
        try:
            if os.path.getmtime(db.duong_so(goc, kenh)) < os.path.getmtime(duong(goc, nhom)):
                return
        except OSError:
            pass
        gop(goc, nhom)
    except Exception as loi:  # noqa: BLE001
        if on_log is not None:
            on_log("  gộp sổ đối thủ chung hỏng (lượt sau gộp lại): {0}".format(str(loi)[:120]))


def bo_bi_danh_da_co(goc: str, kenh: str, links: Sequence[str]) -> Tuple[List[str], int]:
    """Link hộp thư mà sổ riêng của `kenh` ĐÃ CÓ dưới dạng link khác (`@handle` ↔ `/channel/UC…`, theo bí danh của sổ
    chung) → bỏ khỏi lượt chấm (không đo lại cùng một kênh). Trả `(còn lại, số bỏ)`. Không nhóm / lỗi → nguyên."""
    try:
        nhom = nhom_cua(goc, kenh)
        if not nhom or not links:
            return list(links), 0
        bi = (doc(goc, nhom).get("bi_danh") or {})
        if not bi:
            return list(links), 0
        cot, hang = db.doc(goc, kenh)
        o = db.chi_so_cot(list(cot))
        co = {khoa_chuan(_o(d, o, "Link kênh"), bi) for d in hang}
        con = [l for l in links if khoa_chuan(l, bi) not in co]
        return con, len(links) - len(con)
    except Exception:  # noqa: BLE001
        return list(links), 0


def tra(goc: str, nhom: str, link: str, *, du: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Dòng sổ chung của một link kênh (mọi dạng link), hoặc None."""
    du = du if du is not None else doc(goc, nhom)
    k = khoa_chuan(link, du.get("bi_danh") or {})
    return (du.get("kenh") or {}).get(k) if k else None


# ── bản đọc CSV ──────────────────────────────────────────────────────────────

COT_CSV = ("Kênh", "Trạng thái chung", "Ngách (AI)", "Ngày phán", "Sức sống", "Bạn đưa", "AI", "Subs", "View TV",
           "Dài TV", "Số video", "View/tháng", "Im lặng", "Đăng gần nhất", "Quét lúc", "Lần đầu thấy",
           "Kênh ta theo dõi", "Kênh ta bỏ/hết", "Tuyến (theo kênh ta)", "Trang chủ/pool kênh ta", "Lý do ngách",
           "Mã kênh", "Link kênh")


def _ghi_csv(p: str, du: Dict[str, Any]) -> None:
    rows = []
    for k, e in sorted((du.get("kenh") or {}).items(), key=lambda kv: (kv[1].get("trang_thai") != db.THEO_DOI,
                                                                         str(kv[1].get("ten") or ""))):
        tk = e.get("theo_kenh") or {}
        so = e.get("so") or {}
        lq = e.get("lien_quan") or {}
        rows.append({
            "Kênh": e.get("ten", ""), "Trạng thái chung": e.get("trang_thai", ""),
            "Ngách (AI)": (e.get("ngach") or {}).get("ket", ""), "Ngày phán": (e.get("ngach") or {}).get("ngay", ""),
            "Sức sống": (e.get("song") or {}).get("ket", ""), "Bạn đưa": "x" if e.get("ban_dua") else "",
            "AI": so.get("AI", ""), "Subs": so.get("Subs", ""), "View TV": so.get("View TV", ""),
            "Dài TV": so.get("Dài TV", ""), "Số video": so.get("Số video", ""), "View/tháng": so.get("View/tháng", ""),
            "Im lặng": so.get("Im lặng", ""), "Đăng gần nhất": so.get("Đăng gần nhất", ""),
            "Quét lúc": e.get("quet_luc", ""), "Lần đầu thấy": e.get("lan_dau", ""),
            "Kênh ta theo dõi": " ".join(sorted(m for m, x in tk.items() if (x.get("tt") or db.THEO_DOI) == db.THEO_DOI)),
            "Kênh ta bỏ/hết": " ".join(sorted(m for m, x in tk.items() if x.get("tt") in (db.BO, db.HET))),
            "Tuyến (theo kênh ta)": " · ".join("{0}:{1}".format(m, x["tuyen"]) for m, x in sorted(tk.items())
                                              if x.get("tuyen"))[:200],
            "Trang chủ/pool kênh ta": " · ".join("{0}:{1}/{2}".format(m, int(x.get("tc") or 0), int(x.get("pool") or 0))
                                                for m, x in sorted(lq.items()) if x.get("tc") or x.get("pool"))[:200],
            "Lý do ngách": str((e.get("ngach") or {}).get("ly_do") or "")[:160], "Mã kênh": e.get("uc", ""),
            "Link kênh": e.get("link", "")})
    tam = p + ".{0}.tmp".format(os.getpid())
    with io.open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(COT_CSV))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    os.replace(tam, p)


# ── dòng lệnh ────────────────────────────────────────────────────────────────

def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.so_doi_thu_chung")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p.add_argument("--nhom", default="")
    p.add_argument("--ghi", action="store_true", help="ghi sổ chung (mặc định chỉ in thống kê)")
    p.add_argument("--gieo", action="store_true", help="gieo vào sổ riêng mọi kênh (cần --ghi)")
    a = p.parse_args(list(argv) if argv is not None else None)
    nhom = a.nhom
    if not nhom:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        nhom = next((nhom_cua(a.goc, k) for k in liet_ke_kenh(a.goc) if nhom_cua(a.goc, k)), "")
    if not nhom:
        print("không có nhóm kênh nào")
        return 1
    tv = thanh_vien_nhom(a.goc, nhom)
    du = gop(a.goc, nhom, thanh_vien=tv, ghi=bool(a.ghi))
    print(json.dumps({"nhom": nhom, "thanh_vien": tv, "thong_ke": du.get("thong_ke")}, ensure_ascii=False, indent=1))
    for k in tv:
        dem = ap_vao_so(a.goc, k, du=du, ghi=bool(a.ghi and a.gieo))
        print("{0}: gieo {1} {2} · làm mới số {3} · hộp thư chưa gieo được {4}".format(
            k, dem.get("gieo"), dem.get("theo_lop"), dem.get("lam_moi"), dem.get("bo_qua")))
    if a.ghi and a.gieo:
        _ghi(a.goc, nhom, du)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
