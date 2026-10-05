"""KỸ NĂNG "MỞ KÊNH" tự động (04/10/2026) — số do MÃ tính, LLM chỉ chọn góc + đặt tên, người chỉ đăng nhập Chrome.

    python -m core.mo_kenh de-xuat                    # có nên mở kênh nào không? In + ghi workspace/mo-kenh/de-xuat.json
    python -m core.mo_kenh chuan-bi <TÊN>             # tự dựng mọi thứ (góc, hồ sơ, ảnh, giọng, kenh.yaml, thư mục Chrome)
    python -m core.mo_kenh kich-hoat <TÊN>            # Chrome đã đăng nhập → ghép máy đăng → thiết lập kênh → tu_chay
    python -m core.mo_kenh tiep-tuc                   # móc hằng ngày của gác tổng: làm tiếp mọi bước tới hạn
    python -m core.mo_kenh xem                        # trạng thái các kênh đang mở

Luồng: `de-xuat` (luật số kênh của tổng giám đốc, KHÔNG tạo gì) → đăng ký 1 đề xuất → `chuan-bi` (tu_chay: false,
nuoi_trang_chu/thiet_lap_kenh tắt) → "Việc của bạn": MỘT việc duy nhất "Mở kênh <TÊN>" → người tạo kênh YouTube + đăng
nhập Chrome → `kich-hoat` (tự chạy khi thấy phiên đăng nhập) → thiết lập kênh `xong` → `tu_chay: true`.

TỔNG QUÁT: không cứng tên TL*, không cứng tiếng Nhật — ngôn ngữ, quốc gia, ngách đọc từ `CHANNEL/_NHOM/<nhóm>/ngach.yaml`;
mã kênh đặt theo mẫu mã đang có (`<tiền tố><số>-<hậu tố>`, bản nhân `-K2`, `-K3`). Nhóm/chủ đề MỚI hoàn toàn thì chạy
`core.khoi_tao_ngach` trước (nó dựng ngách + kênh đầu), `mo_kenh` lo các kênh THÊM của ngách đã có.

Luật (chủ dự án 01/10/2026, cài ở `core/giam_doc/tong.py`): số kênh tối đa của một tệp = số nguồn nổ ĐANG LÊN mỗi tháng
÷ 15, chỉ khi trang chủ của tệp lên/ổn định; kênh nhân bản chỉ mở khi kênh đầu của tệp đã thắng ≥ 2 video; tệp mới
đánh số tiếp; mỗi kênh một góc, hai kênh không remake cùng nguồn (cùng `nhom` → giữ nguồn chung).
Công tắc `workspace/cai-dat.json: mo_kenh` = tat | goi_y | tu_chuan_bi (mặc định tu_chuan_bi: máy tự chuẩn bị, người
quyết định bằng việc đăng nhập Chrome).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

THU_MUC = os.path.join("workspace", "mo-kenh")
TEP_DE_XUAT = "de-xuat.json"
TEP_TRANG_THAI = "trang-thai.json"
TEP_NHAT_KY = "nhat-ky.log"
TEP_KHOA = ".khoa"
CHE_DO = ("tat", "goi_y", "tu_chuan_bi")

#: Số liệu thị trường (`thi-truong.json`) cũ hơn ngần này ngày → KHÔNG đề xuất (chỉ cảnh báo).
TUOI_SO_LIEU_TOI_DA_NGAY = 30
TUOI_SO_LIEU_CANH_BAO_NGAY = 14
#: Đề xuất lại tối đa 1 lần / ngần này ngày (bảng thị trường đổi chậm; một lượt `bang_cong_ty` nặng ~1 phút CPU).
NGAY_DE_XUAT_LAI = 7
#: Hai góc giống nhau quá ngưỡng này (Jaccard trên từ) → LLM phải viết lại.
NGUONG_TRUNG_GOC = 0.5
#: Kiểm đăng nhập Chrome tối đa 1 lần / ngần này phút cho mỗi kênh đang chờ.
PHUT_KIEM_LAI = 60
#: Chrome mẫu phải còn trống ngần này GB sau khi chép.
GB_TRONG_TOI_THIEU = 6.0
NHIP_MAC_DINH = "05:00"
GIO_DANG_MAC_DINH = "05:00"

#: Trạng thái kênh đang mở. `de_xuat` → `chuan_bi_xong` → `cho_chrome` → `dang_thiet_lap` → `xong` | `huy`.
TT_DANG_MO = ("de_xuat", "chuan_bi_xong", "cho_chrome", "dang_thiet_lap")

#: Giọng đã duyệt khởi đầu (đang dùng tốt trên VPS đầu tiên) — `ky_tu_moi_phut` ĐÃ ĐO.
GIONG_KHOI_DAU = (
    {"voice_id": "b34JylakFZPlGS0BnwyY", "ky_tu_moi_phut": 270, "ghi_chu": "giọng đã duyệt (TL1-TL3)"},
    {"voice_id": "GxxMAMfQkDlnqjpzjLHH", "ky_tu_moi_phut": 273, "ghi_chu": "giọng đã duyệt (TL4-T7-K2)"},
    {"voice_id": "T7yYq3WpB94yAuOXraRi", "ky_tu_moi_phut": 268, "ghi_chu": "giọng đã duyệt (TL6-T7)"},
)

#: Khoá style.yaml gắn với NHÂN VẬT/khán giả của góc — viết lại cho kênh mới; các khoá hình còn lại (kiểu hình của kênh
#: thắng trong tuyến) giữ nguyên.
KHOA_STYLE_NHAN_VAT = ("default_character_prompt", "default_character_lock", "reference_lock", "engagement_rules")

_QUOC_GIA_THEO_NGON_NGU = {"ja": "JP", "vi": "VN", "ko": "KR", "th": "TH", "id": "ID", "pt": "BR", "es": "ES",
                           "de": "DE", "fr": "FR", "en": "US", "zh": "TW"}


# ═══════════════════════════ tiện ích ═══════════════════════════════════════
def _doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def _tm(goc: str, *phan: str) -> str:
    return os.path.join(goc, THU_MUC, *phan)


def _doc(duong: str) -> str:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""


def _ghi(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)
    os.replace(tam, duong)


def _bay_gio(bay_gio: Optional[_dt.datetime] = None) -> _dt.datetime:
    return bay_gio or _dt.datetime.now()


def _f(x: Any, le: int = 1) -> str:
    """Số kiểu Việt: 47,0."""
    try:
        return "{0:.{1}f}".format(float(x), le).replace(".", ",")
    except (TypeError, ValueError):
        return "?"


def _ngay(chu: Any) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(chu or "")[:10])
    except ValueError:
        return None


def che_do(goc: str) -> str:
    cd = str((_doc_json(os.path.join(goc, "workspace", "cai-dat.json"), {}) or {}).get("mo_kenh") or "tu_chuan_bi")
    cd = cd.strip().lower()
    return cd if cd in CHE_DO else "tu_chuan_bi"


def _nhat_ky(goc: str, dong: str) -> None:
    try:
        os.makedirs(_tm(goc), exist_ok=True)
        with io.open(_tm(goc, TEP_NHAT_KY), "a", encoding="utf-8") as tep:
            tep.write("{0} {1}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong))
    except OSError:
        pass


def _kenh_yaml(goc: str, ma: str) -> Dict[str, Any]:
    from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    return dict(doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {})


def _cac_kenh(goc: str) -> List[str]:
    """Mọi mã kênh trong CHANNEL/ (bỏ thư mục `_...`)."""
    d = os.path.join(goc, "CHANNEL")
    try:
        return sorted(k for k in os.listdir(d) if not k.startswith(("_", ".")) and os.path.isfile(os.path.join(d, k, "kenh.yaml")))
    except OSError:
        return []


# ═══════════════════════════ đặt mã kênh ════════════════════════════════════
_RE_V = re.compile(r"[-_]v\d+$", re.IGNORECASE)
_RE_K = re.compile(r"-K(\d+)$", re.IGNORECASE)
_RE_MA = re.compile(r"^([A-Za-z]+)(\d+)(?:-(.+))?$")


def phan_ma(ma: str) -> Dict[str, Any]:
    """`TL4-T7-K2` → {goc: TL4-T7, k: 2, tien: TL, so: 4, hau: T7}. Cặp `-v2` (cùng kênh YouTube) tính là kênh gốc."""
    s = _RE_V.sub("", str(ma or "").strip())
    m = _RE_K.search(s)
    k = int(m.group(1)) if m else 1
    goc = _RE_K.sub("", s) if m else s
    mm = _RE_MA.match(goc)
    return {"goc": goc, "k": k, "tien": mm.group(1) if mm else "", "so": int(mm.group(2)) if mm else 0,
            "hau": (mm.group(3) or "") if mm else ""}


def ma_nhan_ban(cac_ma: Sequence[str], ma_goc: str, ton_tai: Callable[[str], bool] = lambda m: False) -> str:
    """Kênh nhân bản của `ma_goc`: `<gốc>-K<n>`, n = số K lớn nhất đang có của gốc đó + 1 (≥ 2)."""
    goc = phan_ma(ma_goc)["goc"]
    k = max([phan_ma(m)["k"] for m in cac_ma if phan_ma(m)["goc"] == goc] + [1])
    while True:
        k += 1
        ma = "{0}-K{1}".format(goc, k)
        if ma not in cac_ma and not ton_tai(ma):
            return ma


def ma_tep_moi(cac_ma: Sequence[str], ton_tai: Callable[[str], bool] = lambda m: False) -> str:
    """Mã cho TỆP MỚI: đánh số tiếp theo mẫu đang có (TL1-T7…TL6-T7 → TL7-T7). Không có mẫu → K<n>."""
    ds = [phan_ma(m) for m in cac_ma]
    ds = [d for d in ds if d["tien"]]
    if not ds:
        n = 1
        while "K{0}".format(n) in cac_ma or ton_tai("K{0}".format(n)):
            n += 1
        return "K{0}".format(n)
    dem_tien: Dict[str, int] = {}
    dem_hau: Dict[str, int] = {}
    for d in ds:
        dem_tien[d["tien"]] = dem_tien.get(d["tien"], 0) + 1
        dem_hau[d["hau"]] = dem_hau.get(d["hau"], 0) + 1
    tien = max(dem_tien, key=lambda t: (dem_tien[t], t))
    hau = max(dem_hau, key=lambda h: (dem_hau[h], h))
    so = max(d["so"] for d in ds if d["tien"] == tien) + 1
    while True:
        ma = "{0}{1}{2}".format(tien, so, ("-" + hau) if hau else "")
        if ma not in cac_ma and not ton_tai(ma):
            return ma
        so += 1


# ═══════════════════════════ 1) ĐỀ XUẤT ═════════════════════════════════════
def _thang_theo_kenh(bang: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    return {str(d.get("ma")): int(d.get("thang_tong") or 0) for d in bang or []}


def de_xuat(goc: str, *, bang: Optional[List[Dict[str, Any]]] = None,
            bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Quyết định CÓ NÊN MỞ KÊNH KHÔNG — thuần số, không LLM, không tạo gì.

    `bang` = `tong.bang_cong_ty(goc)` (nặng ~1 phút; để None thì tính). Số kênh tối đa, điều kiện nhân bản (kênh đầu
    thắng ≥ 2) lấy ĐÚNG từ `tong.bang_so_kenh` — một luật, một chỗ. Ở đây thêm: tuổi số liệu thị trường, loại đề xuất
    (nhân bản / tệp mới), mã đề xuất, kênh gốc để lấy khuôn, giải thích bằng số."""
    from .giam_doc import tong  # noqa: PLC0415

    bay_gio = _bay_gio(bay_gio)
    tt = _doc_json(os.path.join(goc, tong.TEP_THI_TRUONG), {}) or {}
    tt_tep = tt.get("tep") if isinstance(tt.get("tep"), dict) else {}
    ngay_tt = _ngay(tt.get("ngay"))
    tuoi = (bay_gio.date() - ngay_tt).days if ngay_tt else None
    canh_bao: List[str] = []
    if not tt_tep:
        canh_bao.append("chưa có {0} — không đủ số liệu thị trường, KHÔNG đề xuất".format(tong.TEP_THI_TRUONG.replace(os.sep, "/")))
    elif tuoi is None or tuoi > TUOI_SO_LIEU_TOI_DA_NGAY:
        canh_bao.append("số liệu thị trường {0} cũ quá {1} ngày — KHÔNG đề xuất cho tới khi cập nhật".format(
            "không rõ ngày" if tuoi is None else "({0} ngày)".format(tuoi), TUOI_SO_LIEU_TOI_DA_NGAY))
    elif tuoi > TUOI_SO_LIEU_CANH_BAO_NGAY:
        canh_bao.append("số liệu thị trường đã {0} ngày (> {1}) — nên cập nhật".format(tuoi, TUOI_SO_LIEU_CANH_BAO_NGAY))
    du_so_lieu = bool(tt_tep) and tuoi is not None and tuoi <= TUOI_SO_LIEU_TOI_DA_NGAY

    if bang is None and tt_tep:
        bang = tong.bang_cong_ty(goc, bay_gio)
    bang = list(bang or [])
    thang = _thang_theo_kenh(bang)
    hang = tong.bang_so_kenh(goc, bang) if tt_tep else []
    cac_ma = _cac_kenh(goc)
    nhom_chung = _nhom_pho_bien(goc, cac_ma)

    ra: List[Dict[str, Any]] = []
    for r in hang:
        s = {}
        for k_, v_ in tt_tep.items():                       # số gốc theo khoá tệp của thi-truong.json
            if str(r.get("ten")) == str(v_.get("ten")):
                s = v_
                break
        kenh = list(r.get("kenh") or [])
        dau = max([thang.get(m, 0) for m in kenh] + [int(s.get("thang_kenh_dau") or 0)] if kenh else [0])
        mo = bool(r.get("de_xuat_mo")) and du_so_lieu
        d = {"tep": r["tep"], "ten": r["ten"], "nguon_no_thang": r.get("nguon_no_thang"), "trang_chu": r.get("trang_chu"),
             "he_so_trang_chu": s.get("he_so_trang_chu"), "toi_da": r.get("toi_da"), "dang_co": r.get("dang_co"), "kenh": kenh,
             "thang_kenh_dau": dau, "mo": mo, "loai": "", "ma_de_xuat": "", "nhom": "", "kenh_goc": "",
             "ghi_chu_luat": r.get("ghi_chu")}
        d["ly_do"] = _ly_do_so(d, du_so_lieu, tuoi)
        if mo:
            nhom = _nhom_cua(goc, kenh) or nhom_chung
            d["nhom"] = nhom
            if kenh:
                d["loai"] = "nhan_ban"
                d["kenh_goc"] = _kenh_thang_nhat(kenh, thang)
                d["ma_de_xuat"] = ma_nhan_ban(cac_ma, d["kenh_goc"], lambda m: os.path.exists(os.path.join(goc, "CHANNEL", m)))
            else:
                d["loai"] = "tep_moi"
                d["kenh_goc"] = _kenh_thang_nhat([m for m in cac_ma if _kenh_yaml(goc, m).get("nhom") == nhom], thang)
                d["ma_de_xuat"] = ma_tep_moi(cac_ma, lambda m: os.path.exists(os.path.join(goc, "CHANNEL", m)))
            d["goc_da_co"] = [{"ma": m, "luat_chon": str(_kenh_yaml(goc, m).get("luat_chon") or "")[:200]} for m in kenh]
        ra.append(d)
    ra.sort(key=lambda d: (-int(bool(d["mo"])), -(float(d.get("nguon_no_thang") or 0)), d["tep"]))
    cac_de_xuat = [d for d in ra if d["mo"]]
    # mỗi lần MỘT kênh (luật 4: không dồn): chỉ tệp đứng đầu là "nên mở ngay", các tệp sau xếp hàng
    for i, d in enumerate(cac_de_xuat):
        d["thu_tu"] = i + 1
    kq = {"ngay": bay_gio.strftime("%Y-%m-%d %H:%M"),
          "so_lieu": {"tep": tong.TEP_THI_TRUONG.replace(os.sep, "/"), "ngay": tt.get("ngay"), "tuoi_ngay": tuoi,
                      "nguon": str(tt.get("nguon") or "")[:300]},
          "luat": "tối đa = nguồn nổ/tháng ÷ {0} (chỉ khi trang chủ lên/ổn định); nhân bản cần kênh đầu thắng ≥ {1} video; "
                  "mỗi lần mở MỘT kênh".format(tong.NHIP_THANG, tong.THANG_MO_THEM),
          "tep": ra, "de_xuat": cac_de_xuat, "canh_bao": canh_bao}
    kq["tom_tat"] = tom_tat(kq)
    return kq


def _ly_do_so(d: Dict[str, Any], du_so_lieu: bool, tuoi: Optional[int]) -> str:
    """Một câu CÓ SỐ: vì sao tệp này mở / không mở."""
    nguon = d.get("nguon_no_thang")
    he = d.get("he_so_trang_chu")
    from .giam_doc.tong import TEN_XU_HUONG  # noqa: PLC0415

    tc = "{0}{1}".format(TEN_XU_HUONG.get(str(d.get("trang_chu") or ""), str(d.get("trang_chu") or "?")),
                         " ×" + _f(he, 2) if he is not None else "")
    co = "đang có {0}{1}".format(d.get("dang_co"), " (" + ", ".join(d["kenh"]) + ")" if d.get("kenh") else "")
    dau = "kênh đầu thắng {0}/2".format(d.get("thang_kenh_dau")) if d.get("kenh") else "chưa có kênh nào"
    cs = "nguồn nổ {0}/tháng ÷ 15 = tối đa {1} (trang chủ {2}); {3}; {4}".format(_f(nguon), d.get("toi_da"), tc, co, dau)
    if not du_so_lieu:
        return cs + " → không đề xuất (số liệu thị trường {0})".format("thiếu" if tuoi is None else "cũ {0} ngày".format(tuoi))
    if d.get("mo"):
        return cs + " → ĐỀ XUẤT MỞ"
    return cs + " → không mở: " + str(d.get("ghi_chu_luat") or "")


def tom_tat(kq: Dict[str, Any]) -> str:
    d: List[str] = ["ĐỀ XUẤT MỞ KÊNH — {0} (số liệu thị trường ngày {1}, {2} ngày tuổi)".format(
        kq.get("ngay"), (kq.get("so_lieu") or {}).get("ngay") or "?", (kq.get("so_lieu") or {}).get("tuoi_ngay"))]
    d.append("Luật: " + str(kq.get("luat")))
    for c in kq.get("canh_bao") or []:
        d.append("  ! " + c)
    for t in kq.get("tep") or []:
        d.append("  - [{0}] {1}: {2}".format("MỞ" if t["mo"] else "—", t["ten"], t["ly_do"]))
    if kq.get("de_xuat"):
        d.append("=> NÊN MỞ:")
        for t in kq["de_xuat"]:
            d.append("   {0}. {1}  (loại: {2}; tệp: {3}; lấy khuôn từ {4})".format(
                t.get("thu_tu"), t["ma_de_xuat"], "nhân bản" if t["loai"] == "nhan_ban" else "tệp mới", t["tep"],
                t.get("kenh_goc") or "—"))
    else:
        d.append("=> KHÔNG có đề xuất mở kênh lúc này.")
    return "\n".join(d)


def _nhom_cua(goc: str, kenh: Sequence[str]) -> str:
    for m in kenh:
        n = str(_kenh_yaml(goc, m).get("nhom") or "")
        if n:
            return n
    return ""


def _nhom_pho_bien(goc: str, cac_ma: Sequence[str]) -> str:
    dem: Dict[str, int] = {}
    for m in cac_ma:
        n = str(_kenh_yaml(goc, m).get("nhom") or "")
        if n:
            dem[n] = dem.get(n, 0) + 1
    return max(dem, key=lambda n: (dem[n], n)) if dem else ""


def _kenh_thang_nhat(kenh: Sequence[str], thang: Dict[str, int]) -> str:
    """Kênh thắng nhiều video nhất (hoà → kênh đầu theo tên): lấy khuôn kiểu hình đã chứng minh."""
    ds = sorted(kenh, key=lambda m: (-thang.get(m, 0), m))
    return ds[0] if ds else ""


def ghi_de_xuat(goc: str, kq: Dict[str, Any]) -> str:
    duong = _tm(goc, TEP_DE_XUAT)
    _ghi_json(duong, kq)
    return duong


# ═══════════════════════════ trạng thái ════════════════════════════════════
def doc_trang_thai(goc: str) -> Dict[str, Any]:
    st = _doc_json(_tm(goc, TEP_TRANG_THAI), {})
    st = st if isinstance(st, dict) else {}
    if not isinstance(st.get("kenh"), dict):
        st["kenh"] = {}
    st.setdefault("ngay_de_xuat_cuoi", "")
    return st


def luu_trang_thai(goc: str, st: Dict[str, Any]) -> None:
    _ghi_json(_tm(goc, TEP_TRANG_THAI), st)


def dang_mo(goc: str) -> List[str]:
    """Các kênh đang trong luồng mở (chưa xong/huỷ), theo thứ tự đăng ký."""
    st = doc_trang_thai(goc)
    return [m for m, d in st["kenh"].items() if d.get("trang_thai") in TT_DANG_MO]


def dang_ky(goc: str, kq: Dict[str, Any], bay_gio: Optional[_dt.datetime] = None) -> str:
    """Nhận ĐỀ XUẤT ĐỨNG ĐẦU vào luồng, chỉ khi chưa có kênh nào đang mở (mỗi lần MỘT kênh). Trả mã hoặc ''."""
    if che_do(goc) == "tat" or not kq.get("de_xuat") or dang_mo(goc):
        return ""
    d = kq["de_xuat"][0]
    ma = d["ma_de_xuat"]
    if not ma or os.path.exists(os.path.join(goc, "CHANNEL", ma)):
        return ""
    st = doc_trang_thai(goc)
    st["kenh"][ma] = {"trang_thai": "de_xuat", "tep": d["tep"], "ten_tep": d["ten"], "loai": d["loai"], "nhom": d["nhom"],
                      "kenh_goc": d.get("kenh_goc") or "", "ly_do": d["ly_do"], "ngay_de_xuat": _bay_gio(bay_gio).strftime("%Y-%m-%d"),
                      "kiem_cuoi": 0, "loi": ""}
    st["ngay_de_xuat_cuoi"] = _bay_gio(bay_gio).strftime("%Y-%m-%d")
    luu_trang_thai(goc, st)
    _nhat_ky(goc, "đăng ký đề xuất {0} ({1}, tệp {2}): {3}".format(ma, d["loai"], d["tep"], d["ly_do"]))
    return ma


# ═══════════════════════════ 2) CHUẨN BỊ ════════════════════════════════════
def _tu(chu: Any) -> set:
    """Tập từ để so góc: từ chữ-số ≥ 2 ký tự + cặp ký tự chữ Hán/kana liền nhau."""
    s = str(chu or "").casefold()
    ra = set(re.findall(r"[^\W\d_]{2,}|\d{2,}", s))
    for run in re.findall(r"[぀-ヿ㐀-鿿]+", s):
        ra.update(run[i:i + 2] for i in range(len(run) - 1))
    return ra


def do_giong_goc(a: Any, b: Any) -> float:
    """Jaccard trên từ của hai mô tả góc (0 = khác hẳn, 1 = y hệt)."""
    ta, tb = _tu(a), _tu(b)
    return (len(ta & tb) / float(len(ta | tb))) if (ta and tb) else 0.0


def _sach(chu: Any, toi_da: int = 2000) -> str:
    """Một dòng, bỏ ký tự làm hỏng YAML (`"`, `\\`, tab, xuống dòng)."""
    return re.sub(r'["\\\t]', "", " ".join(str(chu or "").replace("\r", " ").replace("\n", " ").split()))[:toi_da]


def kiem_goc(du: Dict[str, Any], anh_em: Sequence[Dict[str, Any]]) -> List[str]:
    """Mã kiểm trả lời LLM chọn góc. Rỗng = đạt. Các số (độ giống) do MÃ tính, không tin LLM."""
    loi: List[str] = []
    luat = _sach(du.get("luat_chon"), 3000)
    if len(luat) < 120:
        loi.append("luat_chon quá ngắn (< 120 ký tự)")
    if not _sach(du.get("giong_van")):
        loi.append("thiếu giong_van")
    if not _sach(du.get("ten_goi_y"), 80):
        loi.append("thiếu ten_goi_y")
    ds = [_sach(x, 60) for x in (du.get("danh_sach_phat_kenh") or []) if _sach(x, 60)]
    if len(ds) < 3:
        loi.append("danh_sach_phat_kenh cần ≥ 3 tên")
    co = {_sach(x, 60).casefold() for a in anh_em for x in str(a.get("danh_sach_phat_kenh") or "").split("|")}
    trung = [x for x in ds if x.casefold() in co]
    if trung:
        loi.append("trùng tên danh sách phát với kênh anh em: " + ", ".join(trung[:3]))
    for a in anh_em:
        ng = max(do_giong_goc(luat, a.get("luat_chon")), do_giong_goc(du.get("goc"), a.get("luat_chon")))
        if ng >= NGUONG_TRUNG_GOC:
            loi.append("góc giống kênh {0} tới {1} (ngưỡng {2}) — chọn góc KHÁC hẳn".format(a.get("ma"), _f(ng, 2), _f(NGUONG_TRUNG_GOC, 2)))
    nv = du.get("nhan_vat") if isinstance(du.get("nhan_vat"), dict) else {}
    if len(_sach(nv.get("default_character_prompt"))) < 40:
        loi.append("thiếu nhan_vat.default_character_prompt")
    return loi


def _ngu_canh(goc: str, nhom: str) -> Dict[str, Any]:
    from .ho_so_ngach import doc_ngach_tho  # noqa: PLC0415

    ng = doc_ngach_tho(goc, nhom) or {}
    tt = ng.get("thi_truong") if isinstance(ng.get("thi_truong"), dict) else {}
    cum = ng.get("cum")
    ten_cum = [str((v or {}).get("ten") or k) for k, v in cum.items()] if isinstance(cum, dict) else []
    ngon_ngu = str(tt.get("ngon_ngu") or ng.get("ngon_ngu_nguon") or "").lower()
    return {"mo_ta_ngach": str(ng.get("mo_ta_ngach") or ""), "ngon_ngu": ngon_ngu,
            "quoc_gia": str(tt.get("quoc_gia") or "").upper() or _QUOC_GIA_THEO_NGON_NGU.get(ngon_ngu, ""),
            "cum": ten_cum[:40]}


def _anh_em(goc: str, tep: str, nhom: str, tru: str = "") -> List[Dict[str, Any]]:
    """Kênh anh em (cùng nhóm + cùng tệp), KHÔNG tính chính kênh đang chuẩn bị (chạy lại không tự so với mình)."""
    ra = []
    for m in _cac_kenh(goc):
        if m == tru:
            continue
        y = _kenh_yaml(goc, m)
        if str(y.get("nhom") or "") == nhom and (str(y.get("tep") or "") == tep or not tep):
            ra.append({"ma": m, "ten": str(y.get("ten") or ""), "luat_chon": str(y.get("luat_chon") or ""),
                       "danh_sach_phat_kenh": str(y.get("danh_sach_phat_kenh") or ""), "voice_id": str(y.get("voice_id") or "")})
    return ra


def loi_nhac_goc(hang: Dict[str, Any], ctx: Dict[str, Any], anh_em: Sequence[Dict[str, Any]], ma: str) -> str:
    """Lời nhắc chọn góc. Các SỐ/sự kiện thị trường do mã điền sẵn; LLM chỉ viết góc, tên, danh sách phát, nhân vật."""
    vd = "\n".join("- {0} ({1}): {2}".format(a["ma"], a["ten"][:60], a["luat_chon"][:450]) for a in anh_em) or "(none)"
    lg = ctx.get("ngon_ngu") or "en"
    dau = (
        "You plan the ANGLE of a NEW YouTube channel that remakes proven content for a market. Reply with ONE JSON object only.\n"
        "MARKET FACTS (computed by code, do not change)\n"
        "- new channel code: {ma}\n- audience segment (tep): {tep}\n- niche: {nganh}\n"
        "- language of channel text: {lg}; country: {qg}\n- segment market size: {ly}\n- clusters known in this niche: {cum}\n"
        "SIBLING CHANNELS ALREADY IN THIS SEGMENT/GROUP (your angle must be CLEARLY DIFFERENT from each; two sibling channels "
        "never remake the same source):\n{vd}\n\n"
    ).format(ma=ma, tep=hang.get("ten_tep") or hang.get("tep"), nganh=str(ctx.get("mo_ta_ngach", ""))[:300], lg=lg,
             qg=ctx.get("quoc_gia") or "?", ly=str(hang.get("ly_do"))[:300], cum=", ".join(ctx.get("cum") or [])[:600] or "(none)", vd=vd)
    viet = (
        "WRITE these keys:\n"
        '"goc": 1-2 sentences, the angle of this channel (what the viewer feels / which sub-topic), different from every sibling,\n'
        '"luat_chon": the source-selection rule of this channel, 4-6 parts separated by " | ", written in Vietnamese like the siblings: '
        "part 1 = the channel angle and which clusters to prefer; part 2 = platform-policy safety (never teach manipulation or revenge, "
        "no medical diagnosis); part 3 = what is OFF-angle and belongs to sibling channels; part 4 = preferred source length and trend. "
        "At least 400 characters. No double quotes, no backslashes,\n"
        '"giong_van": narrator voice and tone direction in English (1-3 sentences), different in feel from the siblings,\n'
        '"ten_goi_y": a working channel name in language ' + lg + ', at most 40 characters,\n'
        '"danh_sach_phat_kenh": array of exactly 5 playlist names in language ' + lg + ' (at most 40 characters each), none equal to a sibling playlist,\n'
        '"nhan_vat": object with "default_character_prompt" (detailed English description of ONE recurring illustrated character that fits '
        "the angle, same visual style as the winning sibling channel but a different character), \"default_character_lock\" (short English "
        "lock phrase of the character's fixed visual traits), \"reference_lock\" (one English sentence: the attached reference image IS the "
        "character), \"engagement_rules\" (2-3 English sentences about this channel's viewer and how to treat them).\n"
    )
    return dau + viet


def chon_goc(goc: str, ma: str, hang: Dict[str, Any], ctx: Dict[str, Any], anh_em: Sequence[Dict[str, Any]],
             goi: Callable[..., str], log: Callable[[str], None] = print) -> Dict[str, Any]:
    """LLM chọn góc + tên + 5 danh sách phát + nhân vật; MÃ kiểm (độ giống góc anh em, tên trùng...). Tối đa 2 lượt."""
    from .thiet_lap_kenh import _bat_json  # noqa: PLC0415

    ask = loi_nhac_goc(hang, ctx, anh_em, ma)
    loi: List[str] = []
    for lan in range(2):
        tra = goi(ask + (("\nPREVIOUS ANSWER WAS REJECTED BY CODE CHECKS: " + "; ".join(loi)) if loi else ""))
        try:
            du = _bat_json(tra)
        except (ValueError, TypeError) as e:
            loi = [str(e)]
            log("  góc: lượt {0} không đọc được JSON ({1})".format(lan + 1, loi[0][:80]))
            continue
        loi = kiem_goc(du, anh_em)
        if not loi:
            return du
        log("  góc: lượt {0} bị mã loại: {1}".format(lan + 1, "; ".join(loi)[:200]))
    raise RuntimeError("chưa chọn được góc đạt luật: " + "; ".join(loi)[:300])


# ── giọng ─────────────────────────────────────────────────────────────────────
def duong_kho_giong(goc: str, nhom: str) -> str:
    return os.path.join(goc, "CHANNEL", "_NHOM", nhom, "kho-giong.json")


def _tieng_nhom(goc: str, nhom: str) -> str:
    """Mã tiếng của nhóm theo `ngach.yaml` (`thi_truong.ngon_ngu` > `ngon_ngu_nguon`); "" nếu nhóm chưa có hồ sơ."""
    try:
        from .ho_so_ngach import doc_ngach_tho  # noqa: PLC0415

        tho = doc_ngach_tho(goc, nhom) or {}
    except Exception:  # noqa: BLE001 — hồ sơ hỏng: coi như chưa khai
        return ""
    tt = tho.get("thi_truong") if isinstance(tho.get("thi_truong"), dict) else {}
    return str(tt.get("ngon_ngu") or tho.get("ngon_ngu_nguon") or "").strip().lower().split("-")[0]


def doc_kho_giong(goc: str, nhom: str, ghi: bool = True) -> List[Dict[str, Any]]:
    """Kho giọng ĐÃ DUYỆT của nhóm; chưa có thì tạo từ giọng khởi đầu + giọng các kênh đang chạy (đã đo ký tự/phút)."""
    duong = duong_kho_giong(goc, nhom)
    du = _doc_json(duong)
    ds = [dict(x) for x in (du or {}).get("giong", []) if isinstance(x, dict) and x.get("voice_id")] if isinstance(du, dict) else []
    if ds:
        return ds
    # GIONG_KHOI_DAU là giọng TIẾNG NHẬT (ký tự/phút đo cho tiếng Nhật) — chỉ gieo cho nhóm tiếng Nhật / nhóm chưa khai
    # tiếng. Nhóm tiếng khác (06/10/2026 — chạy thử ngách Hàn) chỉ nhận giọng của chính các kênh trong nhóm; rỗng thì
    # `chuan_bi` báo rõ "kho giọng hết giọng" thay vì gán nhầm giọng Nhật cho kênh Hàn.
    ds = [dict(x) for x in GIONG_KHOI_DAU] if _tieng_nhom(goc, nhom) in ("", "ja") else []
    co = {x["voice_id"] for x in ds}
    for m in _cac_kenh(goc):
        y = _kenh_yaml(goc, m)
        v = str(y.get("voice_id") or "").strip()
        if str(y.get("nhom") or "") == nhom and v and v not in co:
            try:
                kt = int(float(y.get("ky_tu_moi_phut") or 0))
            except (TypeError, ValueError):
                kt = 0
            if kt > 0:
                ds.append({"voice_id": v, "ky_tu_moi_phut": kt, "ghi_chu": "đang dùng ở " + m})
                co.add(v)
    if ghi and os.path.isdir(os.path.dirname(duong)):
        _ghi_json(duong, {"nhom": nhom, "cap_nhat": time.strftime("%Y-%m-%d"),
                          "ghi_chu": "Kho giọng ĐÃ DUYỆT. Thêm giọng mới: thêm {voice_id, ky_tu_moi_phut (đã đo)} vào đây.", "giong": ds})
    return ds


def chon_giong(kho: Sequence[Dict[str, Any]], giong_cung_tep: Sequence[str], dem_trong_nhom: Optional[Dict[str, int]] = None) -> Optional[Dict[str, Any]]:
    """Giọng từ kho KHÔNG trùng với kênh CÙNG TỆP; ưu tiên giọng ít dùng nhất trong nhóm (hoà → theo thứ tự kho).
    Hết giọng khác tệp → None (cần người thêm giọng vào kho)."""
    cam = {str(v).strip() for v in giong_cung_tep if str(v).strip()}
    dem = dem_trong_nhom or {}
    ung = [(dem.get(x["voice_id"], 0), i, x) for i, x in enumerate(kho) if x.get("voice_id") and x["voice_id"] not in cam]
    ung.sort(key=lambda t: (t[0], t[1]))
    return ung[0][2] if ung else None


def _dem_giong_nhom(goc: str, nhom: str, tru: str = "") -> Dict[str, int]:
    dem: Dict[str, int] = {}
    for m in _cac_kenh(goc):
        if m == tru:
            continue
        y = _kenh_yaml(goc, m)
        if str(y.get("nhom") or "") == nhom and y.get("voice_id"):
            dem[str(y["voice_id"]).strip()] = dem.get(str(y["voice_id"]).strip(), 0) + 1
    return dem


# ── dựng CHANNEL/<TÊN> ────────────────────────────────────────────────────────
def dung_kenh(goc: str, ma: str, kenh_goc: str, hang: Dict[str, Any], du: Dict[str, Any], giong: Dict[str, Any],
              ctx: Dict[str, Any], bay_gio: Optional[_dt.datetime] = None) -> str:
    """Chép KHUÔN từ kênh gốc (kenh.yaml, style.yaml, prompt/*.md — KHÔNG chép số liệu/lượt chạy của kênh gốc), đặt góc +
    giọng + nhịp mới, `tu_chay: false`. Ghi nguyên tử qua thư mục tạm. Trả đường kênh mới."""
    from .dong_bo_kenh import dat_khoa_yaml  # noqa: PLC0415
    from .khoi_tao_ngach import _dat_khoa  # noqa: PLC0415,SLF001
    from .kenh import TEP_KENH, TEP_STYLE, THU_MUC_PROMPT, duong_kenh, kiem_ma_kenh_moi  # noqa: PLC0415

    loi = kiem_ma_kenh_moi(goc, ma)
    if loi:
        raise RuntimeError(loi)
    nguon = duong_kenh(goc, kenh_goc)
    if not os.path.isfile(os.path.join(nguon, TEP_KENH)):
        raise RuntimeError("không thấy kênh gốc {0} để lấy khuôn".format(kenh_goc))
    dich = duong_kenh(goc, ma)
    tam = duong_kenh(goc, "_tao-" + ma)
    shutil.rmtree(tam, ignore_errors=True)
    os.makedirs(os.path.join(tam, THU_MUC_PROMPT))
    try:
        # kenh.yaml: bỏ dòng ghi chú của kênh gốc (nói về góc cũ), đặt khoá mới
        chu = "\n".join(d for d in _doc(os.path.join(nguon, TEP_KENH)).split("\n")
                        if not d.lstrip().startswith("#") and not d.strip().startswith("mau_cua_tool:"))
        chu = re.sub(r"\n{3,}", "\n\n", chu).strip("\n") + "\n"
        today = _bay_gio(bay_gio).strftime("%Y-%m-%d")
        khoa: Dict[str, Any] = {
            "kenh_rieng": True, "ma": ma, "ten": _sach(du.get("ten_goi_y"), 80), "nhom": hang.get("nhom") or "",
            "tep": hang.get("tep") or "", "giong_van": _sach(du.get("giong_van"), 600),
            "voice_id": giong["voice_id"], "ky_tu_moi_phut": int(giong["ky_tu_moi_phut"]),
            "luat_chon": _sach(du.get("luat_chon"), 3000),
            "danh_sach_phat_kenh": " | ".join(_sach(x, 60) for x in du.get("danh_sach_phat_kenh")[:5] if _sach(x, 60)),
            "ngay_bat_dau": today, "thu_muc_done": "DONE/" + ma,
            "gio_dang": GIO_DANG_MAC_DINH, "nhip_dang": NHIP_MAC_DINH, "chu_ky_dang_ngay": 1, "san_xuat_truoc_gio": 24,
            "tu_duyet": True, "giam_doc": "goi_y", "chien_luoc": "tu_dong", "chien_luoc_tu_hoc": True,
            "tu_chay": False,                                   # CHỈ bật ở `kich_hoat`, sau khi thiết lập kênh `xong`
            "nuoi_trang_chu": False, "thiet_lap_kenh": False,   # bật ở `kich_hoat` (Chrome chưa đăng nhập thì agent chỉ báo `can_nguoi` oan)
            "ngon_ngu_tai_khoan_dich": "",                      # xem `ngon_ngu_dich_bat_cho`: chỉ khai khi ngôn ngữ đã chứng minh
        }
        if ctx.get("ngon_ngu"):
            khoa["ngon_ngu"] = ctx["ngon_ngu"]
        for k, v in khoa.items():
            chu = _dat_khoa(chu, k, v)
        _ghi(os.path.join(tam, TEP_KENH), (
            "# KÊNH {0} — dựng bởi `python -m core.mo_kenh chuan-bi` ngày {1}. Tệp {2}; lấy khuôn kiểu hình + prompt từ {3}.\n"
            "# tu_chay: false cho tới khi Chrome đăng nhập + thiết lập kênh xong (`kich-hoat`). Xem docs/MO-KENH.md.\n").format(
                ma, today, hang.get("tep"), kenh_goc) + chu)
        # style.yaml: kiểu hình của kênh thắng GIỮ NGUYÊN; chỉ viết lại các khoá nhân vật/khán giả
        cs = _doc(os.path.join(nguon, TEP_STYLE))
        nv = du.get("nhan_vat") if isinstance(du.get("nhan_vat"), dict) else {}
        for k in KHOA_STYLE_NHAN_VAT:
            if _sach(nv.get(k)):
                cs = _dat_khoa(cs, k, _sach(nv.get(k), 1500))
        _ghi(os.path.join(tam, TEP_STYLE), cs)
        tp = os.path.join(nguon, THU_MUC_PROMPT)
        for ten in sorted(os.listdir(tp)) if os.path.isdir(tp) else []:
            if ten.endswith(".md"):
                shutil.copyfile(os.path.join(tp, ten), os.path.join(tam, THU_MUC_PROMPT, ten))
        os.rename(tam, dich)
    except Exception:
        shutil.rmtree(tam, ignore_errors=True)
        raise
    return dich


def ngon_ngu_dich_bat_cho(goc: str, ma_ngon_ngu: str) -> bool:
    """Ngôn ngữ tài khoản theo quốc gia (Phần A) chỉ BẬT cho kênh mới khi `workspace/cai-dat.json:
    ngon_ngu_tai_khoan_chung_minh` có ngôn ngữ đó (ghi sau khi kênh thử đăng thật qua Studio ngôn ngữ ấy ĐẠT)."""
    ds = (_doc_json(os.path.join(goc, "workspace", "cai-dat.json"), {}) or {}).get("ngon_ngu_tai_khoan_chung_minh") or []
    return str(ma_ngon_ngu or "").lower() in {str(x).lower() for x in ds}


# ── handle ────────────────────────────────────────────────────────────────────
def kiem_handle_trong(handle: str, mo_url: Optional[Callable[[str], Tuple[int, str]]] = None) -> Optional[bool]:
    """True = chưa ai dùng (YouTube trả 404), False = đã có kênh, None = không kiểm được (mạng/trang lạ)."""
    h = str(handle or "").lstrip("@")
    if not h:
        return None
    url = "https://www.youtube.com/@" + urllib.parse.quote(h)

    def mac_dinh(u: str) -> Tuple[int, str]:
        from .mang_an_toan import mo_url as _mo  # noqa: PLC0415 — cửa chung có chứng chỉ (certifi)

        dau = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36",
               "Accept-Language": "en"}
        try:
            with _mo(u, cho=20, headers=dau) as r:
                return r.status, r.read(300000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""

    try:
        ma, nd = (mo_url or mac_dinh)(url)
    except Exception:  # noqa: BLE001
        return None
    if ma == 404:
        return True
    if ma == 200 and ("channelId" in nd or "canonicalBaseUrl" in nd):
        return False
    return None


def handle_ranh(handle: str, ngon_ngu: str, kiem: Callable[[str], Optional[bool]]) -> Tuple[str, str]:
    """(handle dùng được, ghi chú). Thử handle gốc, rồi -<mã nước>, rồi -2, -3. Không kiểm được → giữ gốc (Studio sẽ báo)."""
    goc = str(handle or "").lstrip("@")
    hau = {"ja": "jp"}.get(str(ngon_ngu or "").lower(), str(ngon_ngu or "").lower() or "yt")
    ung = [goc, "{0}-{1}".format(goc, hau)] + ["{0}-{1}".format(goc, i) for i in (2, 3)]
    ket: List[Optional[bool]] = []
    for h in ung:
        h = h[:30]
        r = kiem(h)
        ket.append(r)
        if r is True:
            return "@" + h, "chưa ai dùng" if h == goc else "đổi từ @{0} vì đã có người dùng".format(goc)
        if r is None:
            return "@" + goc, "không kiểm được handle (Studio sẽ báo nếu trùng)"
    return "@" + goc, "4 biến thể đều đã có người dùng — thiet_lap_kenh_dom sẽ thử biến thể nhẹ lúc điền Studio"


# ── Chrome Portable ───────────────────────────────────────────────────────────
def thu_muc_chrome(goc: str, ma: str) -> str:
    """`<cha của MyTool>\\<MÃ>\\<MÃ>.exe` — nếp của cả tool (trung_tam.tim_trinh_duyet)."""
    return os.path.join(os.path.dirname(os.path.abspath(goc)), ma, ma + ".exe")


def _kich_thuoc(duong: str) -> int:
    tong = 0
    for g, _ds, tep in os.walk(duong):
        for t in tep:
            try:
                tong += os.path.getsize(os.path.join(g, t))
            except OSError:
                pass
    return tong


def tim_chrome_mau(goc: str, tru: str = "") -> str:
    """Thư mục Chrome Portable có sẵn (cạnh MyTool) để làm mẫu: có `<T>.exe` + `App\\Chrome-bin\\chrome.exe`, hồ sơ KHÔNG
    được chép nên chọn kênh nào cũng như nhau — ưu tiên theo thứ tự tên."""
    cha = os.path.dirname(os.path.abspath(goc))
    try:
        ten = sorted(os.listdir(cha))
    except OSError:
        return ""
    for t in ten:
        d = os.path.join(cha, t)
        if t == tru or t.startswith((".", "_")) or not os.path.isfile(os.path.join(d, t + ".exe")):
            continue
        if os.path.isfile(os.path.join(d, "App", "Chrome-bin", "chrome.exe")):
            return d
    return ""


def chep_chrome_portable(goc: str, ma: str, mau: str = "", log: Callable[[str], None] = print) -> Tuple[str, str]:
    """Chép Chrome Portable MỚI cho kênh `ma` từ một bản có sẵn: App\\ (Chrome), Other\\, help.html, launcher đổi tên
    `<MÃ>.exe`; Data\\ để TRỐNG (KHÔNG chép hồ sơ/phiên đăng nhập của kênh khác). Không đè thư mục đã có. Chép vào tên tạm
    rồi đổi tên (hỏng giữa chừng không để lại thư mục dở). Trả (trạng thái, ghi chú): co_san | da_chep | khong_chep."""
    dich = os.path.join(os.path.dirname(os.path.abspath(goc)), ma)
    if os.path.isfile(os.path.join(dich, ma + ".exe")):
        return "co_san", "đã có " + dich
    if os.path.exists(dich):
        return "khong_chep", "thư mục {0} đã tồn tại nhưng thiếu {1}.exe — không đè, người kiểm tra".format(dich, ma)
    nguon = mau or tim_chrome_mau(goc, tru=ma)
    if not nguon:
        return "khong_chep", "không thấy Chrome Portable mẫu cạnh MyTool"
    ten_nguon = os.path.basename(nguon.rstrip("\\/"))
    can = _kich_thuoc(os.path.join(nguon, "App")) + _kich_thuoc(os.path.join(nguon, "Other"))
    try:
        trong = shutil.disk_usage(os.path.dirname(dich)).free / 1073741824.0
    except OSError:
        trong = 0.0
    if trong - can / 1073741824.0 < GB_TRONG_TOI_THIEU:
        return "khong_chep", "ổ còn {0} GB, cần {1} GB + {2} GB dự phòng".format(_f(trong), _f(can / 1073741824.0), _f(GB_TRONG_TOI_THIEU))
    tam = dich + ".dang-chep"
    shutil.rmtree(tam, ignore_errors=True)
    try:
        log("  chép Chrome Portable từ {0} ({1} GB)…".format(ten_nguon, _f(can / 1073741824.0)))
        os.makedirs(tam)
        shutil.copytree(os.path.join(nguon, "App"), os.path.join(tam, "App"))
        if os.path.isdir(os.path.join(nguon, "Other")):
            shutil.copytree(os.path.join(nguon, "Other"), os.path.join(tam, "Other"))
        if os.path.isfile(os.path.join(nguon, "help.html")):
            shutil.copyfile(os.path.join(nguon, "help.html"), os.path.join(tam, "help.html"))
        shutil.copyfile(os.path.join(nguon, ten_nguon + ".exe"), os.path.join(tam, ma + ".exe"))
        os.makedirs(os.path.join(tam, "Data", "profile"))
        os.rename(tam, dich)
    except Exception as loi:  # noqa: BLE001
        shutil.rmtree(tam, ignore_errors=True)
        return "khong_chep", "chép hỏng: {0}".format(str(loi)[:150])
    return "da_chep", "đã chép từ {0} (Data trống — chỉ cần đăng nhập)".format(ten_nguon)


def chrome_da_dang_nhap(duong_exe: str) -> Tuple[Optional[bool], str]:
    """Hồ sơ Chrome Portable có phiên đăng nhập YouTube chưa — đọc TÊN cookie `LOGIN_INFO` (tên không mã hoá) trong bản
    sao của CSDL cookie; không mở Chrome. Chrome đang chạy có thể chưa ghi ra đĩa → (False, ...) và lần sau thử lại."""
    d = os.path.join(os.path.dirname(duong_exe), "Data", "profile", "Default")
    for p in (os.path.join(d, "Network", "Cookies"), os.path.join(d, "Cookies")):
        if not os.path.isfile(p):
            continue
        t = tempfile.mktemp(suffix=".sqlite")
        try:
            shutil.copyfile(p, t)
            con = sqlite3.connect(t)
            try:
                co = con.execute("select 1 from cookies where name='LOGIN_INFO' and host_key like '%youtube.com' limit 1").fetchone()
            finally:
                con.close()
            return (True, "") if co else (False, "chưa thấy phiên đăng nhập YouTube trong Chrome")
        except (OSError, sqlite3.Error) as e:
            return None, "không đọc được cookie: {0}".format(str(e)[:80])
        finally:
            try:
                os.remove(t)
            except OSError:
                pass
    return False, "Chrome chưa chạy lần nào (chưa có hồ sơ)"


# ── gieo sổ tuyến + V7 (như khoi_tao_ngach) ───────────────────────────────────
def _gieo_so_lieu(goc: str, ma: str, hang: Dict[str, Any]) -> None:
    from . import cong_thuc_v7 as v7  # noqa: PLC0415
    from . import tuyen_noi_dung as tn  # noqa: PLC0415
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    tep = hang.get("tep") or ""
    tn.gieo_cho_kenh(goc, hang.get("kenh_goc") or ma, ma, tep)
    ch = v7.cau_hinh_cho_tep(v7._cau_hinh_mac_dinh_cho_kenh(goc, ma), tep)  # noqa: SLF001
    _ghi(os.path.join(thu_muc_nghien_cuu(goc, ma), v7.TEP_CAU_HINH), json.dumps(ch, ensure_ascii=False, indent=2))


def _tao_goi_va_anh() -> Tuple[Callable[..., str], Callable[..., str]]:
    from . import thiet_lap_kenh as tl  # noqa: PLC0415

    goi = tl.tao_goi_llm()
    return goi, tl.tao_anh_that(goi.client)  # type: ignore[attr-defined]


def chuan_bi(goc: str, ma: str, *, hang: Optional[Dict[str, Any]] = None, goi: Optional[Callable[..., str]] = None,
             tao_anh: Optional[Callable[..., str]] = None, tao_ho_so: Optional[Callable[..., Dict[str, Any]]] = None,
             kiem_handle: Optional[Callable[[str], Optional[bool]]] = None, chep_chrome: Optional[Callable[..., Tuple[str, str]]] = None,
             gieo: Optional[Callable[..., None]] = None, log: Callable[[str], None] = print, thu: bool = False,
             bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """TỰ LÀM HẾT, KHÔNG CẦN NGƯỜI: góc khác kênh anh em · tên/handle/mô tả/từ khoá/5 danh sách phát · kiểu hình của kênh
    thắng · ảnh nhân vật/logo/banner/hình mờ (ShopAPI) · giọng từ kho · kenh.yaml · thư mục Chrome Portable. `tu_chay: false`.
    Chạy lại được (đã có thì dùng lại); `thu=True` chỉ in kế hoạch. Lỗi tạm (ví/mạng) → ném, lần `tiep-tuc` sau thử lại."""
    from . import thiet_lap_kenh as tl  # noqa: PLC0415
    from .kenh import TEP_KENH, TEP_STYLE, doc_yaml, duong_kenh  # noqa: PLC0415

    st = doc_trang_thai(goc)
    hang = dict(hang or st["kenh"].get(ma) or {})
    if not hang.get("tep") or not hang.get("nhom"):
        raise RuntimeError("{0}: thiếu tệp/nhóm — chạy `de-xuat` + `tiep-tuc` trước, hoặc đăng ký tay trong {1}".format(
            ma, TEP_TRANG_THAI))
    kenh_goc = hang.get("kenh_goc") or ""
    nhom, tep = hang["nhom"], hang["tep"]
    ctx = _ngu_canh(goc, nhom)
    anh_em = _anh_em(goc, tep, nhom, tru=ma)
    hang.setdefault("ten_tep", tep)
    log("── CHUẨN BỊ KÊNH {0} (tệp {1}, nhóm {2}, {3}/{4}; khuôn từ {5}) ──".format(
        ma, tep, nhom, ctx.get("ngon_ngu") or "?", ctx.get("quoc_gia") or "?", kenh_goc or "?"))
    if not kenh_goc or not os.path.isfile(os.path.join(duong_kenh(goc, kenh_goc), TEP_KENH)):
        raise RuntimeError("{0}: không có kênh gốc để lấy khuôn (kenh_goc={1!r})".format(ma, kenh_goc))
    if thu:
        kho = doc_kho_giong(goc, nhom, ghi=False)
        g = chon_giong(kho, [a["voice_id"] for a in anh_em], _dem_giong_nhom(goc, nhom, tru=ma))
        log("  [THỬ] anh em cùng tệp: {0}; giọng sẽ chọn: {1}".format(", ".join(a["ma"] for a in anh_em) or "—", (g or {}).get("voice_id", "HẾT GIỌNG")))
        log("  [THỬ] sẽ: LLM chọn góc → dựng CHANNEL/{0} từ {1} → ảnh nhân vật → hồ sơ + logo/banner/hình mờ → kiểm handle → "
            "gieo tuyến/V7 → chép Chrome Portable → trạng thái cho_chrome".format(ma, kenh_goc))
        return {"thu": True}
    if goi is None or tao_anh is None:
        goi_that, anh_that = _tao_goi_va_anh()
        goi, tao_anh = goi or goi_that, tao_anh or anh_that
    tien_trinh = _tm(goc, ma)
    os.makedirs(tien_trinh, exist_ok=True)

    # 1) góc (nhớ lại để lần chạy lại không hỏi LLM nữa)
    duong_goc = os.path.join(tien_trinh, "goc.json")
    du = _doc_json(duong_goc)
    if not isinstance(du, dict) or kiem_goc(du, anh_em):
        du = chon_goc(goc, ma, hang, ctx, anh_em, goi, log)
        _ghi_json(duong_goc, du)
    log("  góc: {0}".format(_sach(du.get("goc"), 160)))

    # 2) giọng từ kho — KHÔNG trùng kênh cùng tệp
    kho = doc_kho_giong(goc, nhom)
    giong = chon_giong(kho, [a["voice_id"] for a in anh_em], _dem_giong_nhom(goc, nhom, tru=ma))
    if giong is None:
        raise RuntimeError("kho giọng {0} hết giọng khác tệp — thêm voice_id đã duyệt (kèm ky_tu_moi_phut đã đo) vào {1}".format(
            nhom, duong_kho_giong(goc, nhom)))
    log("  giọng: {0} ({1} ký tự/phút)".format(giong["voice_id"], giong["ky_tu_moi_phut"]))

    # 3) CHANNEL/<TÊN>
    dich = duong_kenh(goc, ma)
    if not os.path.isfile(os.path.join(dich, TEP_KENH)):
        dung_kenh(goc, ma, kenh_goc, hang, du, giong, ctx, bay_gio)
        log("  đã dựng " + dich)
    else:
        log("  CHANNEL/{0} đã có — dùng lại".format(ma))
    from .trung_tam import ghi_cai_kenh  # noqa: PLC0415

    if ctx.get("ngon_ngu") and ngon_ngu_dich_bat_cho(goc, ctx["ngon_ngu"]):
        ghi_cai_kenh(goc, ma, ngon_ngu_tai_khoan_dich=ctx["ngon_ngu"])

    # 4) ảnh nhân vật tham chiếu
    nv = os.path.join(dich, "nv", "nv1.png")
    if not os.path.isfile(nv):
        sty = doc_yaml(os.path.join(dich, TEP_STYLE)) or {}
        p = "{0}. {1}. Plain light background, full body, centered, no text, no watermark.".format(
            sty.get("default_character_prompt") or "", sty.get("default_character_lock") or "")
        os.makedirs(os.path.dirname(nv), exist_ok=True)
        tao_anh(p, nv)
        log("  đã tạo nv/nv1.png")

    # 5) hồ sơ thiết lập + logo/banner/hình mờ (core.thiet_lap_kenh)
    hs = (tao_ho_so or tl.tao)(ma, goc, goi=goi, tao_anh=tao_anh, log=log)

    # 6) handle chưa ai dùng
    if hs.get("handle"):
        h, gc = handle_ranh(hs["handle"], ctx.get("ngon_ngu") or "", kiem_handle or kiem_handle_trong)
        if h != tl.chuan_handle(hs["handle"]):
            hs["handle"] = h
            tl.ghi_ho_so(ma, hs, goc)
        log("  handle {0}: {1}".format(hs.get("handle"), gc))

    # 7) sổ tuyến + V7, thư mục DONE
    try:
        (gieo or _gieo_so_lieu)(goc, ma, hang)
    except Exception as loi:  # noqa: BLE001
        log("  gieo sổ tuyến/V7 hỏng (không chặn): {0}".format(str(loi)[:120]))
    os.makedirs(os.path.join(goc, "DONE", ma), exist_ok=True)

    # 8) thư mục Chrome Portable
    tt_chrome, gc_chrome = (chep_chrome or chep_chrome_portable)(goc, ma, log=log)
    log("  Chrome Portable: {0} — {1}".format(tt_chrome, gc_chrome))

    st = doc_trang_thai(goc)
    d = st["kenh"].setdefault(ma, dict(hang))
    d.update(hang)
    d.update({"trang_thai": "cho_chrome" if tt_chrome in ("co_san", "da_chep") else "chuan_bi_xong", "chrome": tt_chrome,
              "chrome_ghi_chu": gc_chrome, "ngay_chuan_bi": _bay_gio(bay_gio).strftime("%Y-%m-%d"), "loi": "",
              "ten_goi_y": _sach(du.get("ten_goi_y"), 80), "handle": hs.get("handle") or "", "voice_id": giong["voice_id"]})
    luu_trang_thai(goc, st)
    _nhat_ky(goc, "chuẩn bị xong {0}: {1}".format(ma, d["trang_thai"]))
    log("── XONG chuẩn bị {0}: trạng thái {1}. Người chỉ cần tạo kênh YouTube + đăng nhập {2} ──".format(
        ma, d["trang_thai"], thu_muc_chrome(goc, ma)))
    return d


# ═══════════════════════════ 3) KÍCH HOẠT ═══════════════════════════════════
def doc_so_thiet_lap(ma: str, goc: str = GOC) -> Dict[str, Any]:
    """Sổ thiết lập kênh của agent (vm/logs/thiet-lap-kenh/<K>.json) — theo thư mục vm của máy này."""
    try:
        from .trung_tam import thu_muc_vm  # noqa: PLC0415

        vm = thu_muc_vm(goc)
    except Exception:  # noqa: BLE001
        vm = os.path.join(goc, "vm")
    du = _doc_json(os.path.join(vm, "logs", "thiet-lap-kenh", ma + ".json"), {})
    return du if isinstance(du, dict) else {}


def kich_hoat(goc: str, ma: str, *, kiem_dang_nhap: Optional[Callable[[str], Tuple[Optional[bool], str]]] = None,
              them_vao_vm: Optional[Callable[..., Any]] = None, doc_so: Optional[Callable[[str], Dict[str, Any]]] = None,
              ep: bool = False, log: Callable[[str], None] = print, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Đi tiếp MỘT bước (chạy lại an toàn, gọi mỗi nhịp):
    cho_chrome  → Chrome đã đăng nhập? có → ghép máy đăng (`tu_dang` tự bật) + bật `thiet_lap_kenh` + `nuoi_trang_chu`
                  (ngôn ngữ tài khoản theo quốc gia — Phần A — nếu đã chứng minh) → dang_thiet_lap
    dang_thiet_lap → sổ thiết lập `xong` → bật `tu_chay` → xong (`ep=True`: bật dù chưa xong). `can_nguoi` → ghi lý do, đợi."""
    from .trung_tam import ghi_cai_kenh, them_kenh_vao_vm, thu_muc_vm  # noqa: PLC0415

    st = doc_trang_thai(goc)
    d = st["kenh"].get(ma)
    if not d:
        return {"trang_thai": "", "ly_do": "{0} không nằm trong luồng mở kênh".format(ma)}
    d["kiem_cuoi"] = _bay_gio(bay_gio).timestamp()
    tt = d.get("trang_thai")
    if tt in ("chuan_bi_xong", "cho_chrome"):
        exe = thu_muc_chrome(goc, ma)
        if not os.path.isfile(exe):
            d["trang_thai"] = "chuan_bi_xong"
            d["loi"] = "chưa thấy Chrome Portable " + exe
            luu_trang_thai(goc, st)
            return {"trang_thai": d["trang_thai"], "ly_do": d["loi"]}
        d["trang_thai"] = "cho_chrome"
        ok, ly = (kiem_dang_nhap or chrome_da_dang_nhap)(exe)
        if not ok and not ep:
            d["loi"] = ly or "chưa đăng nhập"
            luu_trang_thai(goc, st)
            return {"trang_thai": "cho_chrome", "ly_do": d["loi"]}
        log("kích hoạt {0}: Chrome đã đăng nhập → ghép máy đăng + bật thiết lập kênh/nuôi trang chủ".format(ma))
        (them_vao_vm or them_kenh_vao_vm)(thu_muc_vm(goc), ma, chrome=exe)
        khoa: Dict[str, Any] = {"thiet_lap_kenh": True, "nuoi_trang_chu": True}
        ngon = str(_kenh_yaml(goc, ma).get("ngon_ngu") or "")
        if ngon and ngon_ngu_dich_bat_cho(goc, ngon):
            khoa["ngon_ngu_tai_khoan_dich"] = ngon
        ghi_cai_kenh(goc, ma, **khoa)
        d.update({"trang_thai": "dang_thiet_lap", "loi": "", "ngay_dang_nhap": _bay_gio(bay_gio).strftime("%Y-%m-%d")})
        luu_trang_thai(goc, st)
        _nhat_ky(goc, "kích hoạt {0}: đã đăng nhập → dang_thiet_lap".format(ma))
        return {"trang_thai": "dang_thiet_lap", "ly_do": ""}
    if tt == "dang_thiet_lap":
        so = (doc_so or (lambda m: doc_so_thiet_lap(m, goc)))(ma)
        tinh = str(so.get("trang_thai") or "")
        if tinh == "xong" or ep:
            ghi_cai_kenh(goc, ma, tu_chay=True)
            d.update({"trang_thai": "xong", "loi": "", "ngay_xong": _bay_gio(bay_gio).strftime("%Y-%m-%d")})
            luu_trang_thai(goc, st)
            _nhat_ky(goc, "kích hoạt {0}: thiết lập kênh xong → tu_chay: true".format(ma))
            log("kích hoạt {0}: thiết lập kênh xong → đã bật tu_chay".format(ma))
            return {"trang_thai": "xong", "ly_do": ""}
        ly = str(so.get("ly_do") or "") if tinh in ("can_nguoi", "hong") else "đang thiết lập ({0})".format(tinh or "chưa chạy")
        d["loi"] = ("thiết lập kênh cần người: " + ly) if tinh == "can_nguoi" else ly
        luu_trang_thai(goc, st)
        return {"trang_thai": "dang_thiet_lap", "ly_do": d["loi"]}
    luu_trang_thai(goc, st)
    return {"trang_thai": str(tt), "ly_do": "không có bước kế"}


# ═══════════════════════════ 4) MÓC HẰNG NGÀY + VIỆC CỦA BẠN ════════════════
def viec_cua_ban(goc: str) -> List[Dict[str, str]]:
    """ĐÚNG MỘT việc (kênh đang mở đầu tiên cần người): người tạo kênh YouTube + đăng nhập Chrome Portable.
    Chỉ hiện khi máy đã chuẩn bị xong (hoặc chế độ `goi_y`: máy không tự chuẩn bị)."""
    st = doc_trang_thai(goc)
    cd = che_do(goc)
    for ma in dang_mo(goc):
        d = st["kenh"][ma]
        tt = d.get("trang_thai")
        if tt in ("chuan_bi_xong", "cho_chrome") or (tt == "de_xuat" and cd == "goi_y"):
            exe = thu_muc_chrome(goc, ma)
            co_chrome = os.path.isfile(exe)
            chu = "Mở kênh {0}: tạo kênh YouTube và đăng nhập Chrome Portable tại {1}{2}".format(
                ma, exe, "" if co_chrome else " (chép từ một Chrome Portable có sẵn)")
            goi_y = "→ tool tự làm tiếp khi thấy Chrome đã đăng nhập" + (
                " (chạy `python -m core.mo_kenh chuan-bi {0}` trước)".format(ma) if tt == "de_xuat" else "")
            if d.get("loi") and tt == "cho_chrome" and "đăng nhập" not in str(d["loi"]):
                goi_y += " — " + str(d["loi"])[:100]
            return [{"khoa": "mo-kenh:" + ma, "kenh": ma, "chu": chu, "goi_y": goi_y}]
        if tt == "dang_thiet_lap" and str(d.get("loi") or "").startswith("thiết lập kênh cần người"):
            return [{"khoa": "mo-kenh:" + ma, "kenh": ma, "goi_y": "→ xem vm/logs/thiet-lap-kenh/{0}.md rồi chạy lại".format(ma),
                     "chu": "Mở kênh {0}: {1}".format(ma, d["loi"][:160])}]
    return []


def tom_tat_nao(goc: str) -> List[str]:
    """Cho `core.nao.bao_cao`: dòng tóm tắt đề xuất mở kênh gần nhất (đọc tệp, không tính lại)."""
    dx = _doc_json(_tm(goc, TEP_DE_XUAT), {}) or {}
    ra = ["  ({0}) {1}".format(dx.get("ngay") or "chưa chạy `python -m core.mo_kenh de-xuat`",
                               "; ".join(c for c in dx.get("canh_bao") or []) or "số liệu đủ")]
    for t in dx.get("de_xuat") or []:
        ra.append("  - NÊN MỞ {0} ({1}): {2}".format(t.get("ma_de_xuat"), t.get("loai"), str(t.get("ly_do"))[:200]))
    if not dx.get("de_xuat"):
        ra.append("  - không có đề xuất mở kênh")
    for ma in dang_mo(goc):
        ra.append("  - đang mở {0}: {1}".format(ma, doc_trang_thai(goc)["kenh"][ma].get("trang_thai")))
    return ra


def _khoa_dang_giu(goc: str) -> bool:
    d = _doc_json(_tm(goc, TEP_KHOA), {}) or {}
    pid = int(d.get("pid") or 0)
    if not pid:
        return False
    try:
        from .tien_trinh_con import con_song  # noqa: PLC0415

        return bool(con_song(pid)) and (time.time() - float(d.get("luc") or 0)) < 6 * 3600
    except Exception:  # noqa: BLE001
        return False


def _sinh(goc: str) -> int:
    """`python -m core.mo_kenh tiep-tuc` tách rời (cùng cách `core.giam_doc._sinh`)."""
    import subprocess  # noqa: PLC0415

    from .cap_nhat_git import _TRUNG_GIAN, _python_nen  # noqa: PLC0415

    co = 0
    for ten in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP"):
        co |= getattr(subprocess, ten, 0)
    try:
        from .tien_trinh_con import CO_TACH_KHOI_JOB  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        CO_TACH_KHOI_JOB = 0  # noqa: N806
    lenh = [_python_nen(), "-X", "utf8", "-m", "core.mo_kenh", "tiep-tuc"]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    os.makedirs(_tm(goc), exist_ok=True)
    for co_thu in (co | CO_TACH_KHOI_JOB, co):
        a = json.dumps({"lenh": lenh, "cwd": goc, "co": co_thu, "log": _tm(goc, "tien-trinh.log")})
        try:
            return subprocess.Popen([_python_nen(), "-c", _TRUNG_GIAN, a], cwd=goc, creationflags=co_thu,  # noqa: S603
                                    close_fds=True, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL).pid
        except OSError:
            continue
    return 0


def can_lam(goc: str, bay_gio: Optional[_dt.datetime] = None) -> str:
    """Nhịp này có việc đến hạn không? Rẻ (đọc trạng thái, không gọi mạng/Chrome). Trả lý do hoặc ''."""
    if che_do(goc) == "tat":
        return ""
    bay_gio = _bay_gio(bay_gio)
    st = doc_trang_thai(goc)
    for ma in dang_mo(goc):
        d = st["kenh"][ma]
        if d.get("trang_thai") == "de_xuat" and che_do(goc) == "tu_chuan_bi":
            return "chuẩn bị " + ma
        if d.get("trang_thai") in ("chuan_bi_xong", "cho_chrome", "dang_thiet_lap") and \
                bay_gio.timestamp() - float(d.get("kiem_cuoi") or 0) >= PHUT_KIEM_LAI * 60:
            return "kiểm " + ma
    if not dang_mo(goc):
        cuoi = _ngay(st.get("ngay_de_xuat_cuoi"))
        if cuoi is None or (bay_gio.date() - cuoi).days >= NGAY_DE_XUAT_LAI:
            return "đề xuất định kỳ"
    return ""


def nhip(goc: str, *, thu: bool = False, bay_gio: Optional[_dt.datetime] = None,
         sinh: Optional[Callable[[str], int]] = None) -> Dict[str, Any]:
    """Gác tổng gọi mỗi nhịp (15'): chỉ QUYẾT có việc không; có thì sinh `tiep-tuc` tách rời (không nặng trong gác tổng)."""
    ly = can_lam(goc, bay_gio)
    if not ly:
        return {"sinh": False, "ly_do": "không có việc mở kênh đến hạn"}
    if thu:
        return {"sinh": False, "ly_do": "(--thu) sẽ làm: " + ly}
    if _khoa_dang_giu(goc):
        return {"sinh": False, "ly_do": "đang có tiến trình mở kênh chạy"}
    pid = (sinh or _sinh)(goc)
    return {"sinh": bool(pid), "ly_do": ly, "pid": pid}


def tiep_tuc(goc: str, *, bay_gio: Optional[_dt.datetime] = None, log: Callable[[str], None] = print,
             de_xuat_ham: Optional[Callable[..., Dict[str, Any]]] = None, chuan_bi_ham: Optional[Callable[..., Any]] = None,
             kich_hoat_ham: Optional[Callable[..., Any]] = None) -> int:
    """Làm tiếp mọi bước tới hạn: kích hoạt kênh đã đăng nhập → chuẩn bị kênh đã đăng ký → đề xuất định kỳ."""
    cd = che_do(goc)
    if cd == "tat":
        log("mo_kenh: tắt")
        return 0
    bay_gio = _bay_gio(bay_gio)
    _ghi_json(_tm(goc, TEP_KHOA), {"pid": os.getpid(), "luc": time.time()})
    try:
        for ma in list(dang_mo(goc)):
            d = doc_trang_thai(goc)["kenh"][ma]
            if d.get("trang_thai") == "de_xuat" and cd == "tu_chuan_bi":
                st = doc_trang_thai(goc)
                st["kenh"][ma]["kiem_cuoi"] = bay_gio.timestamp()            # lùi nhịp nếu hỏng: không thử lại mỗi 15 phút
                luu_trang_thai(goc, st)
                try:
                    (chuan_bi_ham or chuan_bi)(goc, ma, log=log, bay_gio=bay_gio)
                except Exception as loi:  # noqa: BLE001 — lỗi tạm (ví/mạng): thử lại nhịp sau; chỉ ghi
                    st = doc_trang_thai(goc)
                    st["kenh"][ma]["loi"] = "chuẩn bị chưa xong: " + str(loi)[:200]
                    luu_trang_thai(goc, st)
                    _nhat_ky(goc, "chuẩn bị {0} lỗi: {1}".format(ma, str(loi)[:200]))
                    log("chuẩn bị {0} lỗi (sẽ thử lại): {1}".format(ma, str(loi)[:200]))
            d = doc_trang_thai(goc)["kenh"][ma]
            if d.get("trang_thai") in ("chuan_bi_xong", "cho_chrome", "dang_thiet_lap"):
                kq = (kich_hoat_ham or kich_hoat)(goc, ma, log=log, bay_gio=bay_gio)
                log("{0}: {1} {2}".format(ma, kq.get("trang_thai"), kq.get("ly_do") or ""))
        if not dang_mo(goc):
            st = doc_trang_thai(goc)
            cuoi = _ngay(st.get("ngay_de_xuat_cuoi"))
            if cuoi is None or (bay_gio.date() - cuoi).days >= NGAY_DE_XUAT_LAI:
                kq = (de_xuat_ham or de_xuat)(goc, bay_gio=bay_gio)
                ghi_de_xuat(goc, kq)
                st = doc_trang_thai(goc)
                st["ngay_de_xuat_cuoi"] = bay_gio.strftime("%Y-%m-%d")
                luu_trang_thai(goc, st)
                log(kq.get("tom_tat") or "")
                ma = dang_ky(goc, kq, bay_gio)
                if ma:
                    log("đăng ký đề xuất {0}".format(ma))
                    if cd == "tu_chuan_bi":
                        st = doc_trang_thai(goc)
                        st["kenh"][ma]["kiem_cuoi"] = bay_gio.timestamp()
                        luu_trang_thai(goc, st)
                        try:
                            (chuan_bi_ham or chuan_bi)(goc, ma, log=log, bay_gio=bay_gio)
                        except Exception as loi:  # noqa: BLE001
                            st = doc_trang_thai(goc)
                            st["kenh"][ma]["loi"] = "chuẩn bị chưa xong: " + str(loi)[:200]
                            luu_trang_thai(goc, st)
                            _nhat_ky(goc, "chuẩn bị {0} lỗi: {1}".format(ma, str(loi)[:200]))
                            log("chuẩn bị {0} lỗi (sẽ thử lại): {1}".format(ma, str(loi)[:200]))
    finally:
        try:
            os.remove(_tm(goc, TEP_KHOA))
        except OSError:
            pass
    return 0


# ═══════════════════════════ CLI ═════════════════════════════════════════════
def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m core.mo_kenh", description="Kỹ năng mở kênh tự động (xem docs/MO-KENH.md).")
    s = ap.add_subparsers(dest="lenh", required=True)
    s.add_parser("de-xuat", help="có nên mở kênh nào không (in + ghi workspace/mo-kenh/de-xuat.json; KHÔNG tạo kênh)")
    c = s.add_parser("chuan-bi", help="tự dựng mọi thứ cho kênh <TÊN> (tu_chay: false)")
    c.add_argument("ten")
    c.add_argument("--tep", default="")
    c.add_argument("--nhom", default="")
    c.add_argument("--goc-tu", default="", help="kênh lấy khuôn (kiểu hình, prompt)")
    c.add_argument("--thu", action="store_true", help="chỉ in kế hoạch")
    k = s.add_parser("kich-hoat", help="đi tiếp một bước khi Chrome đã đăng nhập")
    k.add_argument("ten")
    k.add_argument("--ep", action="store_true", help="bỏ qua kiểm đăng nhập / chờ thiết lập xong (người đã tự kiểm)")
    s.add_parser("tiep-tuc", help="móc hằng ngày: làm tiếp mọi bước tới hạn")
    s.add_parser("xem", help="trạng thái các kênh đang mở")
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    a = _parser().parse_args(argv)
    goc = GOC

    def log(dong: str) -> None:
        print(dong)
        _nhat_ky(goc, dong)

    if a.lenh == "de-xuat":
        kq = de_xuat(goc)
        duong = ghi_de_xuat(goc, kq)
        print(kq["tom_tat"])
        print("(đã ghi {0}; chưa tạo kênh nào — `tiep-tuc` mới đăng ký đề xuất)".format(duong))
        return 0
    if a.lenh == "chuan-bi":
        st = doc_trang_thai(goc)
        hang = dict(st["kenh"].get(a.ten) or {})
        for k_, v_ in (("tep", a.tep), ("nhom", a.nhom), ("kenh_goc", a.goc_tu)):
            if v_:
                hang[k_] = v_
        if not a.thu and a.ten not in st["kenh"]:
            st["kenh"][a.ten] = dict(hang, trang_thai="de_xuat", ngay_de_xuat=time.strftime("%Y-%m-%d"), kiem_cuoi=0, loi="", loai="tay")
            luu_trang_thai(goc, st)
        try:
            chuan_bi(goc, a.ten, hang=hang, log=log, thu=a.thu)
        except Exception as loi:  # noqa: BLE001
            print("LỖI: {0}".format(str(loi)[:400]))
            return 1
        return 0
    if a.lenh == "kich-hoat":
        kq = kich_hoat(goc, a.ten, ep=a.ep, log=log)
        print("{0}: {1} {2}".format(a.ten, kq.get("trang_thai"), kq.get("ly_do") or ""))
        return 0
    if a.lenh == "tiep-tuc":
        return tiep_tuc(goc, log=log)
    st = doc_trang_thai(goc)
    print("Chế độ: {0} · đề xuất gần nhất: {1}".format(che_do(goc), st.get("ngay_de_xuat_cuoi") or "chưa"))
    for ma, d in st["kenh"].items():
        print("  {0}: {1} (tệp {2}, {3}) {4}".format(ma, d.get("trang_thai"), d.get("tep"), d.get("loai"), d.get("loi") or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
