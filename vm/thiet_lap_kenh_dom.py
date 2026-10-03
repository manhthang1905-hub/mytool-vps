"""TỰ THIẾT LẬP KÊNH YouTube trên Studio (03/10/2026) — phần 2: ĐIỀN HỒ SƠ VÀO STUDIO.

Chạy MỘT LẦN cho mỗi kênh, lặp lại an toàn: ĐỌC hiện trạng Studio trước, chỉ SỬA mục khác hồ sơ
(`CHANNEL/<K>/thiet-lap/ho-so.json`, dựng bởi `python -m core.thiet_lap_kenh tao <K>`), sửa xong
ĐỌC LẠI để xác nhận. Máy mới chỉ cần Chrome đã đăng nhập.

Mục (sổ `vm/logs/thiet-lap-kenh/<K>.json`, mỗi mục `dat` / `hong` / `can_nguoi` / `cho`):
  tên · handle · mô tả · logo · banner · hình mờ   (Tuỳ chỉnh kênh → Hồ sơ → Xuất bản)
  quốc gia · từ khoá                               (Cài đặt → Kênh → Thông tin cơ bản)
  mặc định tải lên: ngôn ngữ, danh mục, thẻ        (Cài đặt → Chế độ mặc định cho video tải lên;
                                                    KHÔNG đụng chế độ hiển thị mặc định)
  danh sách phát còn thiếu (so tên), công khai     (Nội dung → Danh sách phát)
Đủ mục `dat` → kênh `xong`; agent tự ghi `thiet_lap_kenh: false` vào kenh.yaml.

Luật đổi tên / handle: YouTube cho 2 lần / 14 ngày → CHỈ đổi khi KHÁC hồ sơ, ghi ngày đổi vào sổ;
Studio từ chối thì ghi lý do + `can_nguoi`, KHÔNG thử lại cùng giá trị. Handle trùng → thử tối đa 3
biến thể nhẹ (thêm -<ngôn ngữ>, số), ghi handle THẬT.

An toàn: gặp xác minh danh tính / đăng nhập lại / CAPTCHA / hộp yêu cầu điện thoại → DỪNG, `can_nguoi`,
không thử lại. Khoá RIÊNG THEO KÊNH dùng chung cơ chế `.khoa`/`.dung` của `vm/nuoi_trang_chu.py`
(CÙNG tệp `logs/nuoi-trang-chu/<K>.khoa` → không bao giờ 2 tiến trình cùng mở Chrome một kênh; agent
đòi Chrome để đăng thì ghi `<K>.dung`, phiên này đóng Chrome ngay, hôm sau/nhịp sau làm tiếp).
Không chạy 02:00–07:00; van IPv4 mở thì hoãn; một lúc chỉ MỘT phiên thiết lập trên máy.

Chạy:  python vm/thiet_lap_kenh_dom.py --kenh TL5-T7 [--thu]
       (`--thu` = chỉ ĐỌC Studio, in khác biệt so với hồ sơ, không sửa, không ghi sổ)
       --mo-lai   xoá `can_nguoi`/từ chối cũ (khi người đã xử lý) rồi chạy tiếp
Mã thoát: 0 xong/đã đủ · 10 hoãn · 20 cần người · 30 không cần chạy · 1 lỗi.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.abspath(__file__))                 # vm/
GOC_TOOL = os.path.dirname(GOC)                                  # MyTool/
for _d in (GOC, GOC_TOOL):          # chỉ NỐI ĐUÔI (agent nạp module này: không đổi thứ tự sys.path của nó)
    if _d not in sys.path:
        sys.path.append(_d)
import nuoi_trang_chu as nuoi  # noqa: E402  — khoá/cờ dừng/khung cấm/khe nang dùng CHUNG, không viết cơ chế thứ hai

THU_MUC_SO = os.path.join(GOC, "logs", "thiet-lap-kenh")
THU_MUC_KHOA_RIENG = THU_MUC_SO                                  # khoá "một phiên thiết lập một lúc"
MA_HOAN, MA_CAN_NGUOI, MA_KHONG_CAN = nuoi.MA_HOAN, nuoi.MA_CAN_NGUOI, nuoi.MA_KHONG_CAN

# ── Hằng số luật (đổi ở đây, test canh) ─────────────────────────────────────
MUC = ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo", "quoc_gia", "tu_khoa", "mac_dinh", "danh_sach_phat")
TEN_MUC = {"ten": "tên kênh", "handle": "handle", "mo_ta": "mô tả", "logo": "logo", "banner": "banner",
           "hinh_mo": "hình mờ", "quoc_gia": "quốc gia", "tu_khoa": "từ khoá kênh",
           "mac_dinh": "mặc định tải lên", "danh_sach_phat": "danh sách phát"}
TOI_DA_LAN_NGAY = 2                       # mỗi kênh tối đa 2 phiên thiết lập / ngày
NGHI_SAU_HONG_PHUT = 45                   # phiên hỏng → nghỉ ngần này rồi mới thử lại
CUA_SO_DOI_TEN_NGAY = 14                  # YouTube: 2 lần đổi tên / handle trong 14 ngày
TOI_DA_DOI_TRONG_CUA_SO = 2
TOI_DA_BIEN_THE_HANDLE = 3
NGAN_SACH_PHIEN_PHUT = 25
KHUNG_CAM = nuoi.KHUNG_CAM
CHU_KY_LICH_AGENT_GIAY = 10 * 60

#: Trang / hộp đòi người: URL hoặc chữ trong HỘP THOẠI (đa ngôn ngữ).
URL_CHAN = (("accounts.google.com", "dang_xuat"), ("/signin", "dang_xuat"), ("servicelogin", "dang_xuat"),
            ("/challenge", "xac_minh"), ("recaptcha", "captcha"), ("/speedbump", "xac_minh"),
            ("consent.youtube.com", "dong_y"), ("consent.google.com", "dong_y"))
RE_CHU_CHAN = re.compile(
    r"(xác minh (danh tính|bạn là ai|tài khoản|số điện thoại|qua điện thoại|bằng số điện thoại)|xác nhận (đó là bạn|danh tính)|"
    r"verify (it'?s you|your identity|your phone|phone number)|confirm (it'?s you|your identity)|phone verification|"
    r"本人確認|電話番号(を|の)?(確認|認証|入力)|アカウントの確認|ロボットではありません|captcha|not a robot|"
    r"đăng nhập lại|sign in again|please sign in|再度ログイン|2-step|xác minh 2 bước|2 段階認証|2段階認証)", re.I)
CHU_NUT_XONG = ("Xong", "Done", "完了", "Áp dụng", "Apply", "適用", "Lưu", "Save", "保存")
CHU_NUT_XAC_NHAN = ("Xác nhận", "Tiếp tục", "Có", "Confirm", "Continue", "OK", "Yes", "確認", "続行", "はい", "Đồng ý")
CHU_CONG_KHAI = ("Công khai", "Public", "公開")
CHU_TAO = ("Tạo", "Create", "作成")
CHU_DS_MOI = ("Danh sách phát mới", "New playlist", "新しい再生リスト", "新規再生リスト")
CHU_TAB_DS_PHAT = ("Danh sách phát", "Playlists", "再生リスト")


class CanNguoi(Exception):
    """Cần người xử lý (xác minh danh tính, đăng nhập, CAPTCHA, điện thoại...) — dừng, không thử lại."""


class Hoan(Exception):
    """Chưa chạy được lúc này (không phải lỗi)."""


class LoiMuc(Exception):
    """Một mục hỏng (không đọc/sửa được) — ghi `hong`, đi tiếp mục khác."""


# ═══════════════════════════ HÀM THUẦN (có test) ═════════════════════════════
def chuan(s: Any) -> str:
    """Chuẩn hoá để so: NFKC, gộp khoảng trắng, hạ chữ."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip().casefold()


def chuan_dong(s: Any) -> List[str]:
    """Chữ nhiều dòng → danh sách dòng KHÔNG rỗng đã chuẩn hoá (so mô tả: lệch dòng trống không tính)."""
    s = unicodedata.normalize("NFKC", str(s or "")).replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    return [" ".join(d.split()) for d in s.split("\n") if d.strip()]


def mo_ta_giong(a: Any, b: Any) -> bool:
    return chuan_dong(a) == chuan_dong(b)


def bo_chu(ds: Any) -> set:
    if isinstance(ds, str):
        ds = re.split(r"[,、，\n]+", ds)
    return {chuan(x) for x in (ds or []) if chuan(x)}


def khop_ten(ten: Any, aliases) -> bool:
    return chuan(ten) in {chuan(a) for a in (aliases or ())}


def sha_tep(duong: str) -> str:
    try:
        with open(duong, "rb") as tep:
            return hashlib.sha1(tep.read()).hexdigest()
    except OSError:
        return ""


def so_moi(kenh: str) -> dict:
    return {"kenh": kenh, "trang_thai": "chua_chay", "ly_do": "", "uc": "", "handle_that": "",
            "muc": {m: {"tt": "chua"} for m in MUC}, "ngay_doi": {"ten": [], "handle": []},
            "tu_choi": {}, "hash_anh": {}, "truoc": {}, "phien": [], "nghi_den_luc": 0.0}


def chuan_so(so: dict, kenh: str) -> dict:
    """Điền khoá thiếu (sổ cũ/hỏng) — không bao giờ ném."""
    moi = so_moi(kenh)
    for k, v in moi.items():
        if k not in so or not isinstance(so[k], type(v)):
            so[k] = v
    for m in MUC:
        so["muc"].setdefault(m, {"tt": "chua"})
    for k in ("ten", "handle"):
        so["ngay_doi"].setdefault(k, [])
    return so


def tinh_trang(so: dict) -> Tuple[str, str]:
    """(trạng thái, lý do) của kênh từ các mục: xong | can_nguoi | hong | dang_lam."""
    muc = so.get("muc") or {}
    tt = {m: (muc.get(m) or {}).get("tt", "chua") for m in MUC}
    if all(v == "dat" for v in tt.values()):
        return "xong", "đủ {0} mục".format(len(MUC))
    cn = [m for m, v in tt.items() if v == "can_nguoi"]
    if cn:
        return "can_nguoi", "; ".join("{0}: {1}".format(TEN_MUC[m], (muc[m].get("ly_do") or "")[:100]) for m in cn)
    hong = [m for m, v in tt.items() if v == "hong"]
    if hong:
        return "hong", "; ".join("{0}: {1}".format(TEN_MUC[m], (muc[m].get("ly_do") or "")[:100]) for m in hong)
    cho = [m for m, v in tt.items() if v == "cho"]
    if cho:
        return "dang_lam", "chờ: " + "; ".join("{0}: {1}".format(TEN_MUC[m], (muc[m].get("ly_do") or "")[:80]) for m in cho)
    return "dang_lam", "còn {0} mục chưa đạt".format(sum(1 for v in tt.values() if v != "dat"))


def dat_muc(so: dict, muc: str, gia_tri: Any, luc: float, ghi_chu: str = "") -> None:
    so["muc"][muc] = {"tt": "dat", "luc": time.strftime("%Y-%m-%d %H:%M", time.localtime(luc)),
                      "gia_tri": gia_tri, "ghi_chu": ghi_chu, "lan": int((so["muc"].get(muc) or {}).get("lan", 0)) + 1}


def hong_muc(so: dict, muc: str, ly_do: str, tt: str = "hong") -> None:
    cu = so["muc"].get(muc) or {}
    so["muc"][muc] = {"tt": tt, "ly_do": str(ly_do)[:300], "lan": int(cu.get("lan", 0)) + 1,
                      "luc": time.strftime("%Y-%m-%d %H:%M"), "mo_lai_luc": cu.get("mo_lai_luc", 0)}


def doi_gan_day(so: dict, muc: str, luc: float) -> List[float]:
    return [t for t in so["ngay_doi"].get(muc, []) if 0 <= luc - t < CUA_SO_DOI_TEN_NGAY * 86400]


def quyet_doi(so: dict, muc: str, hien: Any, mong: Any, luc: float) -> Tuple[str, str]:
    """Luật đổi TÊN / HANDLE. ("giong"|"doi"|"cho"|"tu_choi", lý do).
    giong = đã đúng, KHÔNG đổi (không tốn lượt) · cho = hết 2 lượt/14 ngày · tu_choi = Studio từng từ chối đúng giá trị này."""
    if chuan(hien).lstrip("@") == chuan(mong).lstrip("@") and chuan(hien):
        return "giong", ""
    tc = (so.get("tu_choi") or {}).get(muc) or {}
    if tc and chuan(tc.get("gia_tri")).lstrip("@") == chuan(mong).lstrip("@"):
        return "tu_choi", "Studio đã từ chối («{0}», {1}) — không thử lại; người xử lý rồi chạy với --mo-lai".format(
            str(tc.get("ly_do"))[:100], tc.get("luc"))
    gan = doi_gan_day(so, muc, luc)
    if len(gan) >= TOI_DA_DOI_TRONG_CUA_SO:
        mo = min(gan) + CUA_SO_DOI_TEN_NGAY * 86400
        return "cho", "đã đổi {0} lần trong {1} ngày — mở lại {2}".format(
            len(gan), CUA_SO_DOI_TEN_NGAY, time.strftime("%Y-%m-%d %H:%M", time.localtime(mo)))
    return "doi", ""


def ghi_doi(so: dict, muc: str, luc: float) -> None:
    so["ngay_doi"].setdefault(muc, []).append(luc)
    so["ngay_doi"][muc] = doi_gan_day(so, muc, luc + 1)[-6:]


def ghi_tu_choi(so: dict, muc: str, gia_tri: Any, ly_do: str, luc: float) -> None:
    so["tu_choi"][muc] = {"gia_tri": gia_tri, "ly_do": str(ly_do)[:200], "luc": time.strftime("%Y-%m-%d %H:%M", time.localtime(luc))}


def bien_the_handle(handle: str, ma_ngon_ngu: str = "jp") -> List[str]:
    """Handle gốc rồi tối đa 3 biến thể nhẹ (thêm -<ngôn ngữ>, số). Mỗi cái ≤ 30 ký tự, không trùng nhau."""
    h = str(handle or "").lstrip("@")
    ng = {"ja": "jp"}.get(str(ma_ngon_ngu or "").lower(), str(ma_ngon_ngu or "").lower()) or "jp"
    ra: List[str] = []
    for c in (h, "{0}-{1}".format(h, ng), "{0}2".format(h), "{0}-{1}2".format(h, ng)):
        c = c[:30].rstrip("-.")
        if c and c.lower() not in [x.lower() for x in ra]:
            ra.append(c)
    return ra[:1 + TOI_DA_BIEN_THE_HANDLE]


def phat_hien_chan(url: str, chu_hop_thoai: str = "", chu_trang: str = "") -> str:
    """"" nếu ổn; không thì mã: dang_xuat | xac_minh | captcha | dong_y | dien_thoai (xem `URL_CHAN`/`RE_CHU_CHAN`).
    Chữ trong HỘP THOẠI luôn xét; chữ cả trang chỉ xét khi KHÔNG ở Studio (Studio có sẵn chữ "số điện thoại" ở trang tính năng)."""
    u = str(url or "").lower()
    for mau, ma in URL_CHAN:
        if mau in u:
            return ma
    for chu in (chu_hop_thoai, chu_trang if "studio.youtube.com" not in u else ""):
        m = RE_CHU_CHAN.search(str(chu or ""))
        if m:
            t = m.group(0).lower()
            return "captcha" if ("captcha" in t or "robot" in t or "ロボット" in t) else (
                "dien_thoai" if ("điện thoại" in t or "phone" in t or "電話" in t) else "xac_minh")
    return ""


def khung_cam(luc: float, du_kien_phut: float = 0.0) -> str:
    return nuoi.khung_cam(luc, du_kien_phut)


def lan_hom_nay(so: dict, ngay: str) -> int:
    return sum(1 for p in so.get("phien", []) if p.get("ngay") == ngay and not str(p.get("ket_qua", "")).startswith("hoãn"))


def quyet_dinh(so: dict, luc: float, du_kien_phut: float = 0.0, bo_qua_khung: bool = False) -> Tuple[bool, str]:
    """(được chạy phiên mới không, lý do). Thuần: nhận sổ + giờ."""
    tt = so.get("trang_thai")
    if tt == "xong":
        return False, "đã xong"
    if tt == "can_nguoi":
        return False, "đang chờ người xử lý: " + str(so.get("ly_do", ""))[:120]
    if not bo_qua_khung:
        k = khung_cam(luc, du_kien_phut)
        if k:
            return False, k
    if lan_hom_nay(so, time.strftime("%Y-%m-%d", time.localtime(luc))) >= TOI_DA_LAN_NGAY:
        return False, "đã chạy {0} phiên hôm nay".format(TOI_DA_LAN_NGAY)
    if float(so.get("nghi_den_luc") or 0) > luc:
        return False, "nghỉ tới {0}".format(time.strftime("%H:%M", time.localtime(so["nghi_den_luc"])))
    return True, ""


def khac_biet(hs: dict, ht: dict, so: dict, hash_anh: Optional[Dict[str, str]] = None) -> Dict[str, dict]:
    """So hồ sơ `hs` với hiện trạng Studio `ht`. {mục: {"khac": True/False/None, "hien", "mong", "ghi"}}.
    `khac=None` = chưa đọc được. Chỉ mục KHÁC mới bị sửa. Ảnh: Studio không cho so điểm ảnh → coi là ĐÚNG khi sổ ghi
    đã đặt đúng tệp này (hash) VÀ Studio đang có ảnh."""
    tl = _tl()
    ra: Dict[str, dict] = {}
    muc_so = so.get("muc") or {}

    def mot(m, khac, hien, mong, ghi=""):
        ra[m] = {"khac": khac, "hien": hien, "mong": mong, "ghi": ghi}

    if "ten" in ht:
        mot("ten", chuan(ht["ten"]) != chuan(hs.get("ten")), ht["ten"], hs.get("ten"))
    else:
        mot("ten", None, None, hs.get("ten"))
    handle_mong = so.get("handle_that") or hs.get("handle") or ""
    if "handle" in ht:
        mot("handle", chuan(ht["handle"]).lstrip("@") != chuan(handle_mong).lstrip("@"), ht["handle"], handle_mong)
    else:
        mot("handle", None, None, handle_mong)
    if "mo_ta" in ht:
        mot("mo_ta", not mo_ta_giong(ht["mo_ta"], hs.get("mo_ta")), (ht["mo_ta"] or "")[:60], (hs.get("mo_ta") or "")[:60])
    else:
        mot("mo_ta", None, None, (hs.get("mo_ta") or "")[:60])
    for m in ("logo", "banner", "hinh_mo"):
        co = (ht.get("anh") or {}).get(m)
        if co is None:
            mot(m, None, None, hs.get(m))
            continue
        khop_so = (muc_so.get(m) or {}).get("tt") == "dat" and bool(hash_anh) and \
            (so.get("hash_anh") or {}).get(m) == (hash_anh or {}).get(m)
        mot(m, not (co and khop_so), "có ảnh" if co else "chưa có ảnh", hs.get(m),
            "" if khop_so else "chưa có sổ đặt đúng tệp này")
    if "quoc_gia" in ht:
        mot("quoc_gia", not khop_ten(ht["quoc_gia"], tl.ten_quoc_gia(hs.get("quoc_gia")) + (str(hs.get("quoc_gia") or ""),)),
            ht["quoc_gia"], hs.get("quoc_gia"))
    else:
        mot("quoc_gia", None, None, hs.get("quoc_gia"))
    if "tu_khoa" in ht:
        a, b = bo_chu(ht["tu_khoa"]), bo_chu(hs.get("tu_khoa"))
        mot("tu_khoa", a != b, "{0} từ khoá".format(len(a)), "{0} từ khoá".format(len(b)),
            "thiếu {0}, thừa {1}".format(len(b - a), len(a - b)))
    else:
        mot("tu_khoa", None, None, "{0} từ khoá".format(len(bo_chu(hs.get("tu_khoa")))))
    md = hs.get("mac_dinh_tai_len") or {}
    hm = ht.get("mac_dinh")
    if hm is None:
        mot("mac_dinh", None, None, md)
    else:
        sai = []
        if not khop_ten(hm.get("ngon_ngu_video"), tl.ten_ngon_ngu(md.get("ngon_ngu"))):
            sai.append("ngôn ngữ video")
        if not khop_ten(hm.get("ngon_ngu_mo_ta"), tl.ten_ngon_ngu(md.get("ngon_ngu"))):
            sai.append("ngôn ngữ mô tả")
        if not khop_ten(hm.get("danh_muc"), tl.ten_danh_muc(md.get("danh_muc"))):
            sai.append("danh mục")
        if bo_chu(hm.get("the")) != bo_chu(md.get("the")):
            sai.append("thẻ")
        mot("mac_dinh", bool(sai), hm, md, ("khác: " + ", ".join(sai)) if sai else "")
    if "danh_sach_phat" in ht:
        co = [chuan(x) for x in ht["danh_sach_phat"]]
        thieu = [d["ten"] for d in (hs.get("danh_sach_phat") or []) if chuan(d.get("ten")) not in co]
        mot("danh_sach_phat", bool(thieu), "{0} danh sách".format(len(co)), "{0} danh sách".format(len(hs.get("danh_sach_phat") or [])),
            "thiếu: " + " | ".join(thieu) if thieu else "")
    else:
        mot("danh_sach_phat", None, None, "{0} danh sách".format(len(hs.get("danh_sach_phat") or [])))
    return ra


def _tl():
    from core import thiet_lap_kenh as tl  # noqa: PLC0415
    return tl


# ═══════════════════════════ SỔ ═════════════════════════════════════════════
def duong_so(kenh: str) -> str:
    return os.path.join(THU_MUC_SO, kenh + ".json")


def doc_so(kenh: str) -> dict:
    try:
        with open(duong_so(kenh), "r", encoding="utf-8") as tep:
            so = json.load(tep)
        return chuan_so(so if isinstance(so, dict) else {}, kenh)
    except (OSError, ValueError):
        return so_moi(kenh)


#: 04/10: thiết lập kênh chỉ dùng Chrome, gần như không tốn CPU — KHÔNG chờ khe nang (7 kênh sản xuất thì
#: khe nang bận gần cả ngày, thiết lập sẽ không bao giờ tới lượt). Giữ khung cấm, khoá kênh, nhường việc đăng.
CHO_KHE_NANG = False
_BO_QUA_KHE = False          # (dev) `--bo-qua-khung`: bỏ kiểm khe nang — CHỈ dùng khi thử tay
_NHOM_CHON: Optional[set] = None   # (dev) `--nhom ho_so,mac_dinh`: chỉ chạy các nhóm này
_KHONG_GHI_SO = False        # `--thu` / `--khong-luu`: không ghi sổ (không làm bẩn sổ thật)


def luu_so(so: dict) -> None:
    if _KHONG_GHI_SO:
        return
    os.makedirs(THU_MUC_SO, exist_ok=True)
    d = duong_so(so["kenh"])
    with open(d + ".tam", "w", encoding="utf-8") as tep:
        json.dump(so, tep, ensure_ascii=False, indent=1)
    os.replace(d + ".tam", d)
    ghi_bao_cao(so)


def ghi_bao_cao(so: dict) -> None:
    d = ["# Thiết lập kênh — {0}".format(so["kenh"]), "",
         "- Trạng thái: **{0}** {1}".format(so.get("trang_thai"), so.get("ly_do") or ""),
         "- Kênh Studio: {0} · handle thật: {1}".format(so.get("uc") or "?", so.get("handle_that") or "(theo hồ sơ)"), "",
         "| Mục | Trạng thái | Lần | Ghi chú |", "|---|---|---|---|"]
    for m in MUC:
        x = so["muc"].get(m) or {}
        d.append("| {0} | {1} | {2} | {3} |".format(TEN_MUC[m], x.get("tt"), x.get("lan", ""),
                                                    str(x.get("ly_do") or x.get("ghi_chu") or "").replace("|", "/")[:120]))
    try:
        with open(os.path.join(THU_MUC_SO, so["kenh"] + ".md"), "w", encoding="utf-8") as tep:
            tep.write("\n".join(d) + "\n")
    except OSError:
        pass


def _nhat_ky(kenh: str):
    os.makedirs(THU_MUC_SO, exist_ok=True)
    duong = os.path.join(THU_MUC_SO, kenh + ".log")

    def ghi(dong):
        chu = "{0} {1}".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong)
        try:
            print(chu, flush=True)
        except (OSError, UnicodeEncodeError):
            pass
        try:
            with open(duong, "a", encoding="utf-8") as tep:
                tep.write(chu + "\n")
        except OSError:
            pass
    return ghi


# ═══════════════════════════ kenh.yaml ══════════════════════════════════════
def _yaml_gia_tri(duong: str, khoa: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return nuoi._yaml_chu(tep.read(), khoa)
    except OSError:
        return ""


def thiet_lap_bat(kenh: str, goc: str = GOC_TOOL) -> bool:
    d = nuoi.duong_kenh_yaml(kenh, goc)
    return bool(d) and _yaml_gia_tri(d, "thiet_lap_kenh").lower() == "true"


def cac_kenh_bat(goc: str = GOC_TOOL) -> List[str]:
    """Mọi kênh có `thiet_lap_kenh: true` (CHANNEL/<K> thắng bản nháp chuan-bi-<K>)."""
    import glob
    ra: List[str] = []
    for mau in (os.path.join(goc, "CHANNEL", "*", "kenh.yaml"),
                os.path.join(goc, "workspace", "chuan-bi-*", "CHANNEL", "*", "kenh.yaml")):
        for d in sorted(glob.glob(mau)):
            k = os.path.basename(os.path.dirname(d))
            if k.startswith("_") or k in ra:
                continue
            try:
                if thiet_lap_bat(k, goc):
                    ra.append(k)
            except OSError:
                pass
    return ra


def _sua_yaml(kenh: str, ham, goc: str = GOC_TOOL) -> str:
    d = nuoi.duong_kenh_yaml(kenh, goc)
    if not d:
        return ""
    with open(d, "rb") as tep:
        b = tep.read()
    moi = ham(b)
    if moi == b:
        return d
    with open(d + ".tam", "wb") as tep:
        tep.write(moi)
    os.replace(d + ".tam", d)
    return d


def tat_thiet_lap(kenh: str, goc: str = GOC_TOOL) -> str:
    """Ghi `thiet_lap_kenh: false` vào kenh.yaml. Trả đường tệp, "" nếu không ghi được."""
    d = _sua_yaml(kenh, lambda b: re.sub(rb"(?m)^thiet_lap_kenh:[ \t]*true[ \t]*(?=\r?$)", b"thiet_lap_kenh: false", b), goc)
    return d if d and _yaml_gia_tri(d, "thiet_lap_kenh").lower() == "false" else ""


def ghi_ten_yaml(kenh: str, ten: str, goc: str = GOC_TOOL) -> bool:
    """`ten:` còn là tên tạm "(…) — mô tả" thì thay phần tên thật vào, giữ phần sau " — " (nuôi trang chủ dùng phần trước)."""
    d = nuoi.duong_kenh_yaml(kenh, goc)
    cu = _yaml_gia_tri(d, "ten") if d else ""
    if not d or not (cu.startswith("(") or not cu) or '"' in ten or "\n" in ten:
        return False
    sau = cu.split(" — ", 1)[1] if " — " in cu else ""
    moi = ('ten: "{0} — {1}"'.format(ten, sau) if sau else 'ten: "{0}"'.format(ten)).encode("utf-8")
    _sua_yaml(kenh, lambda b: re.sub(rb"(?m)^ten:[^\r\n]*", lambda _m: moi, b, count=1), goc)
    return True


# ═══════════════════════════ LỊCH CHO AGENT ═════════════════════════════════
def _co_chrome_portable(k: str, goc: str = GOC_TOOL) -> bool:
    return os.path.isfile(os.path.join(goc, "..", k, k + ".exe")) or os.path.isfile(os.path.join(goc, "..", k, k, k + ".exe"))


def kenh_den_luot(luc: float, dang_chay=(), goc: str = GOC_TOOL, ram=None, nang_ban=None) -> Tuple[List[str], Dict[str, str]]:
    """(kênh nên mở tiến trình con, {kênh: lý do bỏ qua}). Agent gọi mỗi ~10 phút.
    Một lúc chỉ MỘT phiên thiết lập trên máy (tuần tự); kênh đang được nuôi trang chủ thì đợi lượt nuôi nghỉ."""
    ly: Dict[str, str] = {}
    ung: List[str] = []
    dang = set(dang_chay) | {k for k in cac_kenh_bat(goc) if nuoi.chu_khoa(k, THU_MUC_KHOA_RIENG)}
    for k in cac_kenh_bat(goc):
        if k in dang:
            ly[k] = "đang thiết lập"
            continue
        so = doc_so(k)
        ok, r = quyet_dinh(so, luc, NGAN_SACH_PHIEN_PHUT)
        if ok and not _co_chrome_portable(k, goc):
            ok, r = False, "chưa có Chrome Portable {0}/{0}.exe".format(k)
        if ok and nuoi.chu_khoa(k):
            ok, r = False, "kênh đang có tiến trình khác giữ Chrome (nuôi trang chủ) — đợi lượt nghỉ"
        if ok:
            ung.append(k)
        else:
            ly[k] = r
    if not ung:
        return [], ly
    if dang:
        return [], dict(ly, **{k: "đang có phiên thiết lập kênh khác — tuần tự từng kênh" for k in ung})
    if CHO_KHE_NANG and (nang_ban if nang_ban is not None else nuoi.khe_nang_ban(goc)):
        return [], dict(ly, **{k: "khe nang của máy đang bận — nhường CPU" for k in ung})
    r = nuoi.duoc_mo_them(len(nuoi.cac_kenh_dang_nuoi()), ram_gb(ram))
    if r:
        return [], dict(ly, **{k: r for k in ung})
    return ung[:1], dict(ly, **{k: "xếp hàng sau {0}".format(ung[0]) for k in ung[1:]})


def ram_gb(ram):
    return nuoi.ram_trong_gb() if ram is None else ram


# ═══════════════════════════ JS ĐỌC TRẠNG THÁI ══════════════════════════════
_JS_CHUNG = r"""
const q = (s, r) => (r || document).querySelector(s);
const qa = (s, r) => [...(r || document).querySelectorAll(s)];
const hien = e => { if (!e || !e.isConnected) return false; const b = e.getBoundingClientRect(); if (b.width < 1 || b.height < 1) return false;
  const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && cs.display !== 'none'; };
const giaTri = e => !e ? null : ((e.tagName === 'INPUT' || e.tagName === 'TEXTAREA') ? e.value : (e.innerText || ''));
const dongCuoi = e => { if (!e) return null; const t = (e.innerText || '').split('\n').map(x => x.trim()).filter(x => x); return t.length ? t[t.length - 1] : ''; };
const anh = (host, theoNut) => { const h = q(host); if (!h) return null;
  const rm = qa('#remove-button', h).some(hien), src = [];
  qa('img', h).forEach(i => { if (i.src && hien(i)) src.push(i.src); });
  qa('image', h).forEach(i => { const u = i.getAttribute('href') || ''; if (u) src.push(u.length + ':' + u.slice(-30)); });
  return {co: theoNut ? rm : src.length > 0, src: src}; };
const chips = host => qa('ytcp-chip', q(host) || document.createElement('i')).map(c => (c.innerText || '').trim()).filter(x => x);
"""

_JS_HO_SO = "(() => {" + _JS_CHUNG + r"""
  const ten = q('ytcp-channel-editing-channel-name input'), handle = q('ytcp-channel-editing-channel-handle input');
  const mt = q('#description-textbox [role=textbox]') || q('ytcp-social-suggestions-textbox [role=textbox]');
  if (!ten || !handle || !mt) return null;
  const pub = q('ytcp-button#publish-button button') || q('ytcp-button#publish-button');
  const tat = e => !!e && (e.hasAttribute('disabled') || e.getAttribute('aria-disabled') === 'true' || (e.closest('ytcp-button') || e).hasAttribute('disabled') || (e.closest('ytcp-button') || e).getAttribute('aria-disabled') === 'true');
  return {ten: giaTri(ten), handle: giaTri(handle), mo_ta: giaTri(mt), banner: anh('ytcp-banner-upload', true), logo: anh('ytcp-profile-image-upload', false),
          hinh_mo: anh('ytcp-video-watermark-upload', true), url_kenh: giaTri(q('input.ytcpChannelUrlReadonlyInput') || q('ytcp-channel-url input')),
          xuat_ban_tat: tat(pub)};
})()"""

_JS_LOI_O = "((host) => {" + _JS_CHUNG + r"""
  const h = q(host); if (!h) return null;
  const box = q('ytcp-form-input-container', h) || h;
  const loi = [];
  qa('#error-message, .error-message, [id*=error], [class*=error], [role=alert], ytcp-form-error', h).forEach(e => { const t = (e.innerText || '').trim(); if (t && hien(e)) loi.push(t); });
  const inp = q('input', h);
  const dong = (h.innerText || '').split('\n').map(x => x.trim()).filter(x => x);
  return {invalid: box.hasAttribute('invalid') || (inp && inp.getAttribute('aria-invalid') === 'true') || !!q('[invalid]', h),
          loi: [...new Set(loi)].join(' | '), thong_bao: dong.length ? dong[dong.length - 1] : '', chu: (h.innerText || '').trim().slice(0, 400)};
})"""

_JS_HOP_THOAI = "(() => {" + _JS_CHUNG + r"""
  const ds = qa('tp-yt-paper-dialog, ytcp-dialog, ytcp-confirmation-dialog, [role=dialog], [role=alertdialog]').filter(hien);
  return ds.map(d => (d.innerText || '').trim().slice(0, 600)).join('\n----\n');
})()"""

_JS_CAI_DAT_KENH = "(() => {" + _JS_CHUNG + r"""
  const qg = q('#country-of-residence-select');
  const vb = qa('#keywords-container ytcp-free-text-chip-bar ytcp-chip, ytcp-free-text-chip-bar ytcp-chip').map(c => (c.innerText || '').trim()).filter(x => x);
  if (!qg) return null;
  return {quoc_gia: dongCuoi(qg), tu_khoa: vb, dem: (q('#keywords-container') ? ((q('#keywords-container').innerText.match(/\d+\s*\/\s*\d+/) || [''])[0]) : '')};
})()"""

_JS_MAC_DINH_CO_BAN = "(() => {" + _JS_CHUNG + r"""
  const tc = q('#tags-container'); if (!tc) return null;
  return {the: qa('ytcp-chip', tc).map(c => (c.innerText || '').trim()).filter(x => x),
          che_do: dongCuoi(q('#privacy-select'))};
})()"""

_JS_MAC_DINH_NANG_CAO = "(() => {" + _JS_CHUNG + r"""
  const dm = q('#category-select'), nv = q('#audio-language'), md = q('#metadata-language');
  if (!dm || !nv || !md) return null;
  return {danh_muc: dongCuoi(dm), ngon_ngu_video: dongCuoi(nv), ngon_ngu_mo_ta: dongCuoi(md)};
})()"""

_JS_DS_PHAT = "(() => {" + _JS_CHUNG + r"""
  const s = q('ytcp-playlist-section-content') || q('ytcp-playlist-section'); if (!s) return null;
  const ten = qa('ytcp-playlist-row a.playlist-title-link, ytcp-playlist-row #video-title', s).map(a => (a.innerText || '').trim()).filter(x => x);
  const dem = (((s.innerText || '').match(/\d+\s*[–-]\s*\d+\s*\/\s*\d+/) || [''])[0]) || '';
  return {ten: [...new Set(ten)], chu: (s.innerText || '').slice(0, 3000), phan_trang: dem};
})()"""


# ═══════════════════════════ ĐIỀU KHIỂN STUDIO ══════════════════════════════
class Studio:
    """Bọc `TrangStudio` (vm/cdp_studio.py) cho việc thiết lập kênh: tìm theo CSS (cấu trúc phần tử ổn định của
    Studio) rồi dự phòng theo CHỮ đa ngôn ngữ; bấm/gõ có xác minh như máy đăng."""

    def __init__(self, st, ghi, thu_muc_anh: str, ngu=time.sleep):
        self.st, self.ghi, self.thu_muc_anh, self.ngu = st, ghi, thu_muc_anh, ngu
        self.uc = ""
        self.debug = False                      # `--khong-luu`: chụp thêm ảnh giữa các bước để soi hộp cắt ảnh/hình mờ
        self.st.thu_muc_dom = thu_muc_anh

    # ── tìm / bấm / đọc ──
    def tim(self, css, chu=(), han: float = 6.0, cho_tat: bool = False, thu: int = 0):
        css = [css] if isinstance(css, str) else list(css)
        return self.st._tim_spec("tl:" + (css[0] if css else "|".join(chu)), {"chon": css, "chu": list(chu)},  # noqa: SLF001
                                 han, True, cho_tat, None, thu, ghi_du_phong=False)

    def bam(self, css, chu=(), han: float = 8.0, cho_tat: bool = False, hau_dieu_kien=None):
        pt = self.tim(css, chu, han, cho_tat)
        if not pt:
            raise LoiMuc("không thấy {0}".format(css if isinstance(css, str) else (list(css) or list(chu))[0]))
        return self.st.bam(pt, hau_dieu_kien=hau_dieu_kien, cho_tat=cho_tat)

    def co(self, css, chu=(), han: float = 0.0, cho_tat: bool = False) -> bool:
        return self.tim(css, chu, han, cho_tat) is not None

    def js(self, bt: str):
        return self.st.js_tho(bt)

    def url(self) -> str:
        return self.st.url()

    def nhap(self, css, chu: str, nhieu_dong: bool = False, han: float = 8.0) -> str:
        """Bấm ô, Ctrl+A, gõ, ĐỌC LẠI so; lệch → thử 1 lần nữa → LoiMuc. Trả chữ đọc lại."""
        doc = ""
        for lan in range(2):
            pt = self.bam(css, han=han)
            if lan == 0:
                self.st._ctrl_a()                                   # noqa: SLF001
            else:
                self.st._js("chonHet", pt["id"])                    # noqa: SLF001
            if chu:
                self.st._chen(chu)                                  # noqa: SLF001
            else:
                self.st.phim("Delete")
            self.ngu(0.6)
            doc = self.st.doc_chu(self.tim(css, han=2, cho_tat=True)) or ""
            ok = mo_ta_giong(chu, doc) if nhieu_dong else chuan(chu) == chuan(doc)
            if ok:
                return doc
        raise LoiMuc("gõ vào {0} nhưng đọc lại lệch: {1!r}".format(css if isinstance(css, str) else css[0], str(doc)[:60]))

    def doi_hien(self, css, han: float = 10.0) -> bool:
        return self.tim(css, han=han, cho_tat=True) is not None

    # ── trang ──
    def hop_thoai(self) -> str:
        try:
            return str(self.js(_JS_HOP_THOAI) or "")
        except Exception:  # noqa: BLE001
            return ""

    def kiem_chan(self) -> None:
        try:
            chu_trang = str(self.js("document.body ? document.body.innerText.slice(0, 1500) : ''") or "")
        except Exception:  # noqa: BLE001
            chu_trang = ""
        ma = phat_hien_chan(self.url(), self.hop_thoai(), chu_trang)
        if ma:
            raise CanNguoi({"dang_xuat": "Chrome chưa đăng nhập / bị đăng xuất YouTube", "xac_minh": "YouTube đòi xác minh danh tính",
                            "captcha": "YouTube hiện CAPTCHA", "dong_y": "YouTube hiện trang đồng ý điều khoản",
                            "dien_thoai": "YouTube đòi xác minh số điện thoại"}.get(ma, ma))

    def mo(self, url: str, cho_css: str, han: float = 45.0) -> None:
        self.st.mo(url, han=60)
        self.kiem_chan()
        het = time.monotonic() + han
        while time.monotonic() < het:
            if self.co(cho_css):
                return
            self.kiem_chan()
            self.ngu(1.0)
        raise LoiMuc("trang {0} không dựng xong ({1})".format(url[-40:], cho_css))

    def chup(self, nhan: str) -> None:
        try:
            self.st.ghi_bang_chung(nhan)
        except Exception:  # noqa: BLE001
            pass

    def url_hoso(self) -> str:
        return "https://studio.youtube.com/channel/{0}/editing/profile".format(self.uc)

    def vao_studio(self) -> str:
        self.st.mo("https://studio.youtube.com/", han=60)
        self.ngu(3)
        self.kiem_chan()
        het = time.monotonic() + 40
        while time.monotonic() < het:
            m = re.search(r"/channel/(UC[\w-]{20,})", self.url())
            if m:
                self.uc = m.group(1)
                return self.uc
            self.kiem_chan()
            self.ngu(1.5)
        raise CanNguoi("không vào được Studio của kênh (URL {0}) — chưa đăng nhập hoặc tài khoản có nhiều kênh".format(self.url()[:80]))

    # ── đọc ──
    def doc_ho_so(self) -> dict:
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self.doi_hien("#description-textbox [role=textbox]", 15)
        self.ngu(1.5)
        du = self.js(_JS_HO_SO)
        if not du:
            raise LoiMuc("không đọc được trang Hồ sơ")
        return du

    def mo_cai_dat(self) -> None:
        self.bam(["tp-yt-paper-icon-item#settings-item", "#settings-item"], ("Cài đặt", "Settings", "設定"))
        if not self.doi_hien("ytcp-navigation li#channel", 12):
            raise LoiMuc("hộp Cài đặt không mở")
        self.ngu(1.0)

    def vao_muc_cai_dat(self, id_muc: str, cho_css: str) -> None:
        self.bam(["ytcp-navigation li#{0}".format(id_muc), "li#{0}".format(id_muc)])
        if not self.doi_hien(cho_css, 12):
            raise LoiMuc("mục cài đặt {0} không dựng xong".format(id_muc))
        self.ngu(1.0)

    def dong_cai_dat(self) -> None:
        try:
            self.bam(["ytcp-settings-dialog ytcp-button#cancel-button", "ytcp-button#cancel-button"], CHU_NUT_XONG[:0] + ("Đóng", "Close", "閉じる"), han=4)
        except LoiMuc:
            pass
        self.ngu(0.8)

    def doc_cai_dat(self, ht: dict, loi: dict) -> None:
        try:
            self.mo_cai_dat()
            self.vao_muc_cai_dat("channel", "#country-of-residence-select")
            kc = self.js(_JS_CAI_DAT_KENH)
            if kc:
                ht["quoc_gia"], ht["tu_khoa"] = kc["quoc_gia"], kc["tu_khoa"]
            self.vao_muc_cai_dat("uploads", "#tags-container")
            md = {}
            cb = self.js(_JS_MAC_DINH_CO_BAN)
            if cb:
                md["the"], md["che_do"] = cb["the"], cb["che_do"]
            self.bam(["tp-yt-paper-tab#advancedSettings"], ("Cài đặt nâng cao", "Advanced settings", "詳細設定"))
            self.doi_hien("#category-select", 10)
            na = self.js(_JS_MAC_DINH_NANG_CAO)
            if na:
                md.update(na)
            if "danh_muc" in md and "the" in md:
                ht["mac_dinh"] = md
        except (LoiMuc, Exception) as e:  # noqa: BLE001
            if isinstance(e, CanNguoi):
                raise
            loi["cai_dat"] = str(e)[:150]
            self.chup("doc-cai-dat-hong")
        finally:
            self.dong_cai_dat()

    def doc_ds_phat(self, ht: dict, loi: dict) -> None:
        try:
            self.mo("https://studio.youtube.com/channel/{0}/content/playlists".format(self.uc), "ytcp-playlist-section")
            self.ngu(2.5)
            du = self.js(_JS_DS_PHAT)
            if du is None:
                raise LoiMuc("không đọc được danh sách phát")
            ht["danh_sach_phat"] = du["ten"]
            ht["_ds_phat_chu"] = du["chu"]
        except (LoiMuc, Exception) as e:  # noqa: BLE001
            if isinstance(e, CanNguoi):
                raise
            loi["danh_sach_phat"] = str(e)[:150]
            self.chup("doc-ds-phat-hong")

    def doc_hien_trang(self) -> Tuple[dict, dict]:
        """Đọc TOÀN BỘ hiện trạng (không sửa gì). Trả (hiện trạng, {nhóm: lỗi đọc})."""
        ht: dict = {}
        loi: dict = {}
        try:
            hs = self.doc_ho_so()
            ht.update(ten=hs["ten"], handle=hs["handle"], mo_ta=hs["mo_ta"],
                      anh={m: bool((hs[m] or {}).get("co")) for m in ("logo", "banner", "hinh_mo")},
                      _src={m: (hs[m] or {}).get("src") for m in ("logo", "banner", "hinh_mo")})
        except LoiMuc as e:
            loi["ho_so"] = str(e)[:150]
            self.chup("doc-ho-so-hong")
        self.doc_cai_dat(ht, loi)
        self.doc_ds_phat(ht, loi)
        return ht, loi

    # ── sửa: Hồ sơ ──
    def dat_tep(self, css_nut, duong: str, han: float = 10.0) -> None:
        """Bấm nút → Chrome mở hộp chọn tệp (đã bị chặn) → DOM.setFileInputFiles."""
        duong = os.path.abspath(duong)
        if not os.path.isfile(duong):
            raise LoiMuc("không có tệp ảnh {0}".format(duong))
        cdp, sid = self.st.cdp, self.st.sid
        cdp.tep_cho.pop(sid, None)
        self.bam(css_nut)
        het = time.monotonic() + han
        while time.monotonic() < het:
            p = cdp.tep_cho.pop(sid, None)
            if p and p.get("backendNodeId"):
                cdp.goi("DOM.setFileInputFiles", {"files": [duong], "backendNodeId": p["backendNodeId"]}, sid=sid, han=30)
                self.ngu(2.0)
                if self.debug:
                    self.chup("sau-chon-tep")
                return
            cdp.bom(0.3)
        raise LoiMuc("bấm xong nhưng không mở hộp chọn tệp")

    def xong_hop_cat(self, han: float = 12.0) -> None:
        """Sau khi chọn ảnh có hộp cắt/xem trước: bấm nút Xong/Áp dụng của HỘP đó (nếu có hộp)."""
        het = time.monotonic() + han
        while time.monotonic() < het:
            if self.hop_thoai():
                if self.debug:
                    self.ghi("   hộp cắt/xem trước: " + re.sub(r"\s+", " ", self.hop_thoai())[:160])
                try:
                    self.bam(["tp-yt-paper-dialog ytcp-button#done-button", "ytcp-dialog ytcp-button#done-button",
                              "tp-yt-paper-dialog ytcp-button.done-button", "ytcp-banner-editor ytcp-button#done-button"],
                             CHU_NUT_XONG, han=3)
                    self.ngu(1.5)
                    return
                except LoiMuc:
                    pass
            self.ngu(0.8)

    def doi_o_hop_le(self, host: str, han: float = 4.5) -> dict:
        """Chờ Studio kiểm ô xong (handle: trùng/ngắn…). Báo `invalid` ngay khi thấy; không thấy sau `han` giây = hợp lệ."""
        het = time.monotonic() + han
        e: dict = {}
        while True:
            self.ngu(1.2)
            e = self.js("(" + _JS_LOI_O + ")('{0}')".format(host)) or {}
            if e.get("invalid") or time.monotonic() >= het:
                return e

    def huy_thay_doi(self, ghi=None) -> None:
        """Bấm Hủy ở trang Hồ sơ (bỏ thay đổi chưa Xuất bản) để rời trang không kẹt hộp 'rời trang?'."""
        try:
            if self.co(["ytcp-button#discard-changes-button button"]):
                self.bam(["ytcp-button#discard-changes-button button"], ("Hủy", "Huỷ", "Cancel", "キャンセル"), han=3)
                self.ngu(1.2)
                if self.hop_thoai().strip():
                    self.bam(["tp-yt-paper-dialog ytcp-button#confirm-button", "ytcp-confirmation-dialog ytcp-button#confirm-button"],
                             CHU_NUT_XAC_NHAN, han=3)
        except LoiMuc:
            pass

    def sua_ho_so(self, hs: dict, kh: Dict[str, dict], so: dict, ht: dict, luc: float, ghi, khong_luu: bool = False) -> dict:
        """Điền các mục KHÁC ở trang Hồ sơ rồi Xuất bản. Trả {mục: ("dat"|"hong"|"can_nguoi"|"cho", lý do)}."""
        kq: dict = {}
        thu_muc = _tl().thu_muc_thiet_lap(so["kenh"], GOC_TOOL)
        can = [m for m in ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo") if kh[m]["khac"] in (True, None)]
        if not can:
            return kq
        self.mo(self.url_hoso(), "ytcp-channel-editing-channel-name input")
        self.doi_hien("#description-textbox [role=textbox]", 15)
        da_xuat_ban = False
        try:
            sua_gi = False
            # tên
            if "ten" in can:
                v, ly = quyet_doi(so, "ten", ht.get("ten"), hs["ten"], luc)
                if v == "doi":
                    try:
                        self.nhap("ytcp-channel-editing-channel-name input", hs["ten"])
                        self.ngu(1.5)
                        e = self.js("(" + _JS_LOI_O + ")('ytcp-channel-editing-channel-name')")
                        if e and e.get("invalid"):
                            raise LoiMuc("Studio báo tên không hợp lệ: " + str(e.get("loi") or e.get("chu"))[:100])
                        sua_gi = True
                    except LoiMuc as e:
                        kq["ten"] = ("hong", str(e))
                elif v == "giong":
                    kq["ten"] = ("giong", "")
                else:
                    kq["ten"] = ("cho" if v == "cho" else "can_nguoi", ly)
            # handle: thử gốc rồi tối đa 3 biến thể (CHỈ gõ + xem Studio báo, chưa tốn lượt; lượt chỉ tính khi Xuất bản)
            handle_dung = None
            if "handle" in can:
                goc_h = so.get("handle_that") or hs["handle"]
                v, ly = quyet_doi(so, "handle", ht.get("handle"), goc_h, luc)
                if v == "doi":
                    for cand in bien_the_handle(goc_h, (hs.get("mac_dinh_tai_len") or {}).get("ngon_ngu", "jp")):
                        try:
                            self.nhap("ytcp-channel-editing-channel-handle input", cand)
                        except LoiMuc as e:
                            kq["handle"] = ("hong", str(e))
                            break
                        e = self.doi_o_hop_le("ytcp-channel-editing-channel-handle")
                        if not e.get("invalid"):
                            handle_dung = cand
                            sua_gi = True
                            ghi("   handle «{0}»: Studio nhận".format(cand))
                            break
                        ghi("   handle «{0}» Studio không nhận: {1}".format(cand, str(e.get("loi") or e.get("thong_bao") or e.get("chu"))[:100]))
                    else:
                        kq["handle"] = ("hong", "mọi biến thể handle đều bị Studio từ chối/trùng")
                        # trả ô về giá trị cũ để Xuất bản không mang handle lỗi
                        try:
                            self.nhap("ytcp-channel-editing-channel-handle input", str(ht.get("handle") or "").lstrip("@"))
                        except LoiMuc:
                            pass
                elif v == "giong":
                    kq["handle"] = ("giong", "")
                else:
                    kq["handle"] = ("cho" if v == "cho" else "can_nguoi", ly)
            if "mo_ta" in can:
                try:
                    self.nhap("#description-textbox [role=textbox]", hs["mo_ta"], nhieu_dong=True)
                    sua_gi = True
                except LoiMuc as e:
                    kq["mo_ta"] = ("hong", str(e))
            anh_moi = {}
            for muc, host in (("logo", "ytcp-profile-image-upload"), ("banner", "ytcp-banner-upload"), ("hinh_mo", "ytcp-video-watermark-upload")):
                if muc not in can:
                    continue
                try:
                    d = _tl().duong_anh(hs, muc, thu_muc)
                    nut = ["{0} ytcp-button#replace-button".format(host), "{0} ytcp-button#upload-button".format(host)]
                    self.dat_tep(nut, d)
                    self.xong_hop_cat()
                    if muc == "hinh_mo":
                        self.chon_thoi_gian_hinh_mo()
                    anh_moi[muc] = sha_tep(d)
                    sua_gi = True
                except LoiMuc as e:
                    kq[muc] = ("hong", str(e))
                    self.chup("anh-{0}-hong".format(muc))

            if not sua_gi:
                return kq
            if khong_luu:
                ghi("   [--khong-luu] đã điền xong, KHÔNG bấm Xuất bản (bỏ thay đổi)")
                self.chup("khong-luu")
                du = self.js(_JS_HO_SO) or {}
                ghi("   [--khong-luu] đọc lại trang: tên={0!r} handle={1!r} mô tả={2} ký tự, ảnh có: logo={3} banner={4} hình mờ={5}, nút Xuất bản {6}".format(
                    du.get("ten"), du.get("handle"), len(du.get("mo_ta") or ""), (du.get("logo") or {}).get("co"),
                    (du.get("banner") or {}).get("co"), (du.get("hinh_mo") or {}).get("co"), "mờ" if du.get("xuat_ban_tat") else "SÁNG"))
                for m in can:
                    kq.setdefault(m, ("khong_luu", ""))
                return kq
            # Xuất bản
            self.chup("truoc-xuat-ban")
            self.bam(["ytcp-button#publish-button button", "ytcp-button#publish-button"], ("Xuất bản", "Publish", "公開"), han=6)
            da_xuat_ban = True
            self.xu_ly_sau_xuat_ban(ghi)
            # ghi lượt đổi tên/handle NGAY sau Xuất bản (đã tốn lượt dù đọc lại có lệch)
            if "ten" in can and "ten" not in kq:
                ghi_doi(so, "ten", luc)
            if handle_dung:
                ghi_doi(so, "handle", luc)
                so["handle_that"] = "@" + handle_dung
            luu_so(so)
            for muc, h in anh_moi.items():
                so["hash_anh"][muc] = h
            self.ngu(2.0)
            return kq
        finally:
            if not da_xuat_ban:
                self.huy_thay_doi(ghi)

    def chon_thoi_gian_hinh_mo(self) -> None:
        """Hình mờ: đặt hiển thị TOÀN BỘ video (mặc định của Studio có thể là 'Toàn bộ video' — chỉ bấm nếu thấy lựa chọn)."""
        try:
            self.bam(["ytcp-video-watermark-upload tp-yt-paper-radio-button[name=ENTIRE_VIDEO]",
                      "ytcp-video-watermark-upload tp-yt-paper-radio-button[name=FULL_VIDEO]"],
                     ("Toàn bộ video", "Entire video", "動画全体"), han=3)
        except LoiMuc:
            pass

    def xu_ly_sau_xuat_ban(self, ghi, han: float = 40.0) -> None:
        """Chờ Xuất bản xong: gặp hộp xác nhận thì bấm Xác nhận (nếu hộp ĐÒI xác minh thì dừng người); xong khi nút Xuất bản mờ lại."""
        het = time.monotonic() + han
        while time.monotonic() < het:
            self.ngu(1.5)
            self.kiem_chan()
            ht = self.hop_thoai()
            if ht.strip():
                ghi("   hộp sau Xuất bản: {0}".format(re.sub(r"\s+", " ", ht)[:140]))
                try:
                    self.bam(["tp-yt-paper-dialog ytcp-button.action-button", "tp-yt-paper-dialog ytcp-button#confirm-button",
                              "ytcp-confirmation-dialog ytcp-button#confirm-button"], CHU_NUT_XAC_NHAN, han=3)
                    continue
                except LoiMuc:
                    self.chup("hop-sau-xuat-ban")
                    raise LoiMuc("hộp lạ sau Xuất bản, không có nút xác nhận: " + re.sub(r"\s+", " ", ht)[:120])
            du = self.js(_JS_HO_SO)
            if du is not None and du.get("xuat_ban_tat"):
                return
        raise LoiMuc("Xuất bản xong nhưng nút vẫn sáng sau {0:.0f}s (Studio chưa xác nhận lưu)".format(han))

    # ── sửa: Cài đặt kênh / mặc định tải lên ──
    def chon_dropdown(self, css_trigger: str, aliases) -> None:
        if not aliases:
            raise LoiMuc("không biết tên «{0}» bằng tiếng Studio".format(css_trigger))
        self.bam(css_trigger)
        self.ngu(0.8)
        if not self.doi_hien("tp-yt-paper-listbox", 6):
            raise LoiMuc("danh sách chọn của {0} không mở".format(css_trigger))
        # tìm theo chữ trong CÁC mục của danh sách (khớp chính xác tên)
        pt = self.st._tim_spec("chon:" + aliases[0], {"chon": [], "chu": list(aliases)}, 4, True, False, None, 0, ghi_du_phong=False)  # noqa: SLF001
        if not pt:
            self.chup("dropdown-khong-thay")
            raise LoiMuc("không thấy mục «{0}» trong danh sách {1}".format(aliases[0], css_trigger))
        self.st.bam(pt)
        self.ngu(1.0)

    def dat_chip(self, host: str, ds: List[str]) -> None:
        """Xoá hết chip trong `host` rồi gõ lại từng từ khoá + Enter."""
        for _ in range(60):
            pt = self.tim(["{0} ytcp-chip ytcp-icon-button.delete-icon".format(host), "{0} ytcp-chip #delete-icon".format(host)], han=0.5)
            if not pt:
                break
            self.st.bam(pt)
            self.ngu(0.3)
        inp = ["{0} input.text-input".format(host), "{0} input".format(host)]
        for kw in ds:
            self.bam(inp)
            self.st._chen(kw)                                       # noqa: SLF001
            self.st.phim("Enter")
            self.ngu(0.35)

    def luu_cai_dat(self) -> None:
        self.bam(["ytcp-settings-dialog ytcp-button#submit-button button", "ytcp-button#submit-button button", "ytcp-button#submit-button"],
                 ("Lưu", "Save", "保存"), han=6)
        self.ngu(2.5)
        self.kiem_chan()

    def sua_cai_dat_kenh(self, hs: dict, kh: Dict[str, dict], khong_luu: bool = False) -> dict:
        kq: dict = {}
        if not (kh["quoc_gia"]["khac"] in (True, None) or kh["tu_khoa"]["khac"] in (True, None)):
            return kq
        tl = _tl()
        self.mo_cai_dat()
        try:
            self.vao_muc_cai_dat("channel", "#country-of-residence-select")
            if kh["quoc_gia"]["khac"] in (True, None):
                try:
                    self.chon_dropdown("#country-of-residence-select ytcp-dropdown-trigger", tl.ten_quoc_gia(hs.get("quoc_gia")))
                except LoiMuc as e:
                    kq["quoc_gia"] = ("hong", str(e))
            if kh["tu_khoa"]["khac"] in (True, None):
                try:
                    self.dat_chip("#keywords-container", [t for t in hs.get("tu_khoa") or []])
                except LoiMuc as e:
                    kq["tu_khoa"] = ("hong", str(e))
            if khong_luu:
                self.chup("khong-luu-cai-dat")
                self.ghi("   [--khong-luu] đọc lại hộp: {0}".format(json.dumps(self.js(_JS_CAI_DAT_KENH), ensure_ascii=False)[:300]))
                return kq
            self.luu_cai_dat()
        finally:
            self.dong_cai_dat()
        return kq

    def sua_mac_dinh(self, hs: dict, kh: Dict[str, dict], khong_luu: bool = False) -> dict:
        kq: dict = {}
        if kh["mac_dinh"]["khac"] not in (True, None):
            return kq
        tl = _tl()
        md = hs.get("mac_dinh_tai_len") or {}
        self.mo_cai_dat()
        try:
            self.vao_muc_cai_dat("uploads", "#tags-container")
            ghi_chu = kh["mac_dinh"]["ghi"]
            if "thẻ" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.dat_chip("#tags-container", [t for t in md.get("the") or []])
            self.bam(["tp-yt-paper-tab#advancedSettings"], ("Cài đặt nâng cao", "Advanced settings", "詳細設定"))
            self.doi_hien("#category-select", 10)
            if "danh mục" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.chon_dropdown("#category-select ytcp-dropdown-trigger", tl.ten_danh_muc(md.get("danh_muc")))
            if "ngôn ngữ video" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.chon_dropdown("#audio-language ytcp-dropdown-trigger", tl.ten_ngon_ngu(md.get("ngon_ngu")))
            if "ngôn ngữ mô tả" in ghi_chu or kh["mac_dinh"]["khac"] is None:
                self.chon_dropdown("#metadata-language ytcp-dropdown-trigger", tl.ten_ngon_ngu(md.get("ngon_ngu")))
            if khong_luu:
                self.chup("khong-luu-mac-dinh")
                self.ghi("   [--khong-luu] đọc lại hộp (nâng cao): {0}".format(json.dumps(self.js(_JS_MAC_DINH_NANG_CAO), ensure_ascii=False)[:300]))
                self.bam(["tp-yt-paper-tab#basicInfo"], ("Thông tin cơ bản", "Basic info", "基本情報"), han=4)
                self.ngu(1.0)
                self.ghi("   [--khong-luu] đọc lại hộp (cơ bản): {0}".format(json.dumps(self.js(_JS_MAC_DINH_CO_BAN), ensure_ascii=False)[:300]))
                return kq
            self.luu_cai_dat()
        except LoiMuc as e:
            kq["mac_dinh"] = ("hong", str(e))
            self.chup("mac-dinh-hong")
        finally:
            self.dong_cai_dat()
        return kq

    # ── danh sách phát ──
    def tao_ds_phat(self, ten: str, mo_ta: str) -> None:
        try:                                                       # danh sách còn TRỐNG: nút ngay giữa trang
            self.bam(["ytcp-playlist-section ytcp-button.content-button", "ytcp-playlist-section-content ytcp-button.content-button"],
                     CHU_DS_MOI, han=2.5)
        except LoiMuc:                                             # đã có danh sách: nút Tạo trên đầu trang → mục "Danh sách phát mới"
            self.bam(["ytcp-button#create-icon button", "ytcp-button#create-icon"], CHU_TAO, han=6)
            self.ngu(1.0)
            self.bam([], CHU_DS_MOI, han=6)
        if not self.doi_hien("ytcp-playlist-metadata-editor", 6):          # có thể hiện menu con "Danh sách phát mới"
            self.bam([], CHU_DS_MOI, han=4)
            if not self.doi_hien("ytcp-playlist-metadata-editor", 8):
                raise LoiMuc("hộp tạo danh sách phát không mở")
        self.ngu(1.0)
        self.nhap("ytcp-playlist-metadata-editor #title-textarea [role=textbox]", ten)
        if mo_ta:
            self.nhap("ytcp-playlist-metadata-editor #description-textarea [role=textbox]", mo_ta, nhieu_dong=True)
        che_do = self.js("(() => {" + _JS_CHUNG + "return dongCuoi(q('ytcp-playlist-metadata-visibility'));})()") or ""
        if not khop_ten(che_do, CHU_CONG_KHAI):
            self.chon_dropdown("ytcp-playlist-metadata-visibility ytcp-dropdown-trigger", CHU_CONG_KHAI)
        self.bam(["ytcp-playlist-metadata-editor ~ * ytcp-button#create-button button", "ytcp-button#create-button button",
                  "ytcp-button#create-button"], CHU_TAO, han=6)
        het = time.monotonic() + 20
        while time.monotonic() < het:
            self.ngu(1.0)
            self.kiem_chan()
            if not self.co("ytcp-playlist-metadata-editor"):
                return
        raise LoiMuc("bấm Tạo nhưng hộp danh sách phát không đóng")

    def sua_ds_phat(self, hs: dict, ht: dict, ghi) -> dict:
        thieu = [d for d in hs.get("danh_sach_phat") or []
                 if chuan(d.get("ten")) not in [chuan(x) for x in ht.get("danh_sach_phat") or []]]
        kq: dict = {}
        if not thieu:
            return kq
        self.mo("https://studio.youtube.com/channel/{0}/content/playlists".format(self.uc), "ytcp-playlist-section")
        self.ngu(2.0)
        for d in thieu:
            try:
                self.tao_ds_phat(d["ten"], d.get("mo_ta") or "")
                ghi("   đã tạo danh sách phát «{0}»".format(d["ten"]))
                self.ngu(2.0)
            except LoiMuc as e:
                kq["danh_sach_phat"] = ("hong", "«{0}»: {1}".format(d["ten"], e))
                self.chup("ds-phat-hong")
                break
        return kq


# ═══════════════════════════ PHIÊN ══════════════════════════════════════════
def _nap_cdp():
    """Nạp `vm/cdp.py` + `vm/cdp_studio.py` ĐÚNG tệp (thư mục gốc cũng có một `cdp_studio.py` cũ — agent chèn gốc lên đầu sys.path)."""
    import importlib.util  # noqa: PLC0415
    if GOC in sys.path:
        sys.path.remove(GOC)
    sys.path.insert(0, GOC)
    mods = []
    for ten in ("cdp", "cdp_studio"):
        cu = sys.modules.get(ten)
        if cu is not None and os.path.dirname(os.path.abspath(getattr(cu, "__file__", "") or "")) != GOC:
            del sys.modules[ten]
        if ten not in sys.modules:
            spec = importlib.util.spec_from_file_location(ten, os.path.join(GOC, ten + ".py"))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[ten] = mod
            spec.loader.exec_module(mod)
        mods.append(sys.modules[ten])
    return mods[0], mods[1]


def don_launcher_mo_coi(kenh: str, ghi, cho_giay: float = 15.0) -> int:
    """Sau khi đóng Chrome: launcher Portable `<K>.exe` đôi khi KẸT lại không còn cây Chrome (chặn lần mở kế vì
    `_chrome_dang_chay` hỏi theo tên launcher). Đợi nó tự thoát; vẫn kẹt VÀ không còn tiến trình chrome.exe nào của
    hồ sơ kênh này thì tắt ĐÚNG launcher đó (theo PID, không /T, không đụng kênh khác). Trả số launcher đã tắt."""
    import subprocess  # noqa: PLC0415

    def liet_ke():
        lenh = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*\\" + kenh + "\\*' } | "
                "Select-Object ProcessId,Name | ConvertTo-Json -Compress")
        try:
            ra = subprocess.run(["powershell", "-NoProfile", "-Command", lenh], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=40,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            du = json.loads(ra.stdout.strip() or "[]")
        except Exception:  # noqa: BLE001
            return None
        return du if isinstance(du, list) else [du]
    het = time.monotonic() + cho_giay
    ds = liet_ke()
    while ds and time.monotonic() < het and any(str(x.get("Name", "")).lower() == kenh.lower() + ".exe" for x in ds):
        time.sleep(2)
        ds = liet_ke()
    if not ds:
        return 0
    chrome_con = [x for x in ds if str(x.get("Name", "")).lower() == "chrome.exe"]
    launcher = [x for x in ds if str(x.get("Name", "")).lower() == kenh.lower() + ".exe"]
    if chrome_con or not launcher:
        return 0
    n = 0
    for x in launcher:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(x["ProcessId"])], capture_output=True, timeout=15)
            n += 1
        except Exception:  # noqa: BLE001
            pass
    if n:
        ghi("đã tắt {0} launcher {1}.exe kẹt (không còn Chrome con)".format(n, kenh))
    return n


def in_khac_biet(kh: Dict[str, dict], ghi) -> None:
    for m in MUC:
        x = kh.get(m) or {}
        if x.get("khac") is None:
            dau = "?  KHÔNG ĐỌC ĐƯỢC"
        else:
            dau = "KHÁC" if x["khac"] else "đúng"
        ghi("   {0:<16} {1:<18} hiện: {2!s:<40} mong: {3!s:<40} {4}".format(
            TEN_MUC[m], dau, " ".join(str(x.get("hien")).split())[:40], " ".join(str(x.get("mong")).split())[:40], x.get("ghi") or ""))


def _hash_anh(hs: dict, thu_muc: str) -> Dict[str, str]:
    tl = _tl()
    return {m: sha_tep(tl.duong_anh(hs, m, thu_muc)) for m in ("logo", "banner", "hinh_mo")}


def chuan_bi_ho_so(kenh: str, ghi) -> dict:
    """Hồ sơ đủ + đúng luật; chưa có thì gọi phần 1 (`core.thiet_lap_kenh.tao`)."""
    tl = _tl()
    hs = tl.doc_ho_so(kenh)
    if not hs or tl.kiem_ho_so(hs, tl.thu_muc_thiet_lap(kenh)):
        ghi("chưa có hồ sơ đủ — dựng bằng core.thiet_lap_kenh.tao")
        hs = tl.tao(kenh, log=ghi)
    loi = tl.kiem_ho_so(hs, tl.thu_muc_thiet_lap(kenh))
    if loi:
        raise LoiMuc("hồ sơ chưa đạt luật: " + "; ".join(loi)[:200])
    return hs


def kiem_truoc_khi_chay(agent, kenh: str) -> None:
    if agent.van_ipv4_mo():
        raise Hoan("van IPv4 đang mở")
    if os.path.exists(os.path.join(GOC_TOOL, "logs", "dang-dodang.json")):
        raise Hoan("đang có máy đăng dở (logs/dang-dodang.json)")


def nhuong_nuoi(kenh: str, ghi, cho_giay: float = 150.0) -> bool:
    """Kênh đang được nuôi trang chủ: ghi cờ `.dung`, đợi phiên nuôi đóng Chrome (<= cho_giay). True = đã trống."""
    pid = nuoi.chu_khoa(kenh)
    if not pid:
        return True
    try:
        with open(os.path.join(nuoi.THU_MUC_SO, kenh + ".dung"), "w", encoding="utf-8") as tep:
            tep.write(str(time.time()))
    except OSError:
        return False
    ghi("kênh {0} đang được nuôi trang chủ (pid {1}) — báo dừng sớm, đợi đóng Chrome".format(kenh, pid))
    han = time.monotonic() + cho_giay
    while nuoi.chu_khoa(kenh) and time.monotonic() < han:
        time.sleep(3)
    return not nuoi.chu_khoa(kenh)


def ly_do_dung(agent, kenh: str, luc: float) -> str:
    """Phải DỪNG ở bước kế? cờ `.dung` của agent, khung cấm, khe nang, việc đăng chờ — cùng luật với nuôi trang chủ."""
    if nuoi.co_dung(kenh):
        return "agent báo có việc đăng cần Chrome kênh (cờ .dung)"
    if khung_cam(luc, 0):
        return khung_cam(luc, 0)
    if CHO_KHE_NANG and nuoi.khe_nang_ban() and not _BO_QUA_KHE:
        return "khe nang của máy đang bận — nhường CPU"
    return nuoi.viec_dang_cho(agent, luc, kenh)


def chay_phien(kenh: str, ghi, thu: bool = False, mo_lai: bool = False, khong_luu: bool = False,
               bo_qua_khung: bool = False, rng=None) -> int:
    global _KHONG_GHI_SO, _BO_QUA_KHE
    _KHONG_GHI_SO = bool(thu or khong_luu)
    _BO_QUA_KHE = bool(bo_qua_khung)
    rng = rng or random.Random()
    luc0 = time.time()
    so = doc_so(kenh)
    if mo_lai:
        so["muc"] = {m: ({"tt": "chua"} if (v or {}).get("tt") in ("can_nguoi", "hong", "cho") else v) for m, v in so["muc"].items()}
        so["tu_choi"], so["trang_thai"], so["nghi_den_luc"] = {}, "dang_lam", 0.0
        ghi("--mo-lai: xoá trạng thái can_nguoi/hong/từ chối cũ")
    if not thu and not khong_luu:
        ok, ly = quyet_dinh(so, luc0, NGAN_SACH_PHIEN_PHUT, bo_qua_khung)
        if not ok:
            ghi("bỏ qua: " + ly)
            return MA_KHONG_CAN if so.get("trang_thai") in ("can_nguoi", "xong") else MA_HOAN
    elif khung_cam(luc0, 0) and not bo_qua_khung:
        ghi("hoãn: " + khung_cam(luc0, 0))
        return MA_HOAN
    try:
        hs = chuan_bi_ho_so(kenh, ghi)
    except Exception as e:  # noqa: BLE001
        ghi("hồ sơ lỗi: {0}".format(str(e)[:200]))
        return 1
    agent = nuoi._nap_agent(ghi)                                    # noqa: SLF001
    try:
        kiem_truoc_khi_chay(agent, kenh)
        for r in (nuoi.viec_dang_cho(agent, luc0, kenh), "khe nang của máy đang bận" if (CHO_KHE_NANG and nuoi.khe_nang_ban() and not bo_qua_khung) else ""):
            if r:
                raise Hoan("nhường: " + r)
    except Hoan as h:
        ghi("hoãn: {0}".format(h))
        return MA_HOAN
    ch = nuoi.cau_hinh_kenh_moi(agent, kenh)
    chrome = agent.tim_chrome(ch)
    if not chrome:
        ghi("hoãn: không thấy Chrome Portable của kênh {0}".format(kenh))
        return MA_HOAN
    # Một phiên thiết lập MỘT LÚC trên máy (tuần tự) + khoá Chrome RIÊNG THEO KÊNH dùng chung với nuôi trang chủ.
    if not nuoi.giu_khoa("_thiet-lap", THU_MUC_KHOA_RIENG):
        ghi("hoãn: đang có phiên thiết lập kênh khác (tuần tự từng kênh)")
        return MA_HOAN
    khoa_kenh = khoa_mo = False
    cdp = st = S = None
    tu_mo, ma_thoat = False, 0
    phien = {"ngay": time.strftime("%Y-%m-%d", time.localtime(luc0)), "bat_dau": time.strftime("%H:%M", time.localtime(luc0)),
             "bat_dau_luc": luc0, "ket_qua": "đang chạy", "che_do": "thu" if thu else ("khong-luu" if khong_luu else "that")}
    try:
        if not nhuong_nuoi(kenh, ghi):
            ghi("hoãn: kênh {0} vẫn bận (phiên nuôi chưa nhả Chrome)".format(kenh))
            phien["ket_qua"] = "hoãn: nuôi chưa nhả"
            return MA_HOAN
        if not nuoi.giu_khoa(kenh):
            ghi("hoãn: kênh {0} đang có tiến trình khác giữ khoá Chrome".format(kenh))
            phien["ket_qua"] = "hoãn: khoá kênh"
            return MA_HOAN
        khoa_kenh = True
        nuoi.xoa_co_dung(kenh)
        if agent._chrome_dang_chay(chrome):                         # noqa: SLF001
            ghi("hoãn: Chrome kênh {0} đang chạy (không phải phiên của tôi)".format(kenh))
            phien["ket_qua"] = "hoãn: Chrome đang chạy"
            return MA_HOAN
        han = time.monotonic() + 180
        while not nuoi.giu_khoa("_mo"):
            if time.monotonic() > han:
                ghi("hoãn: chờ lượt mở Chrome quá 3 phút")
                return MA_HOAN
            time.sleep(3)
        khoa_mo = True
        r = nuoi.duoc_mo_them(len(nuoi.cac_kenh_dang_nuoi()) - 1, nuoi.ram_trong_gb())
        if r:
            ghi("hoãn: {0}".format(r))
            phien["ket_qua"] = "hoãn: " + r
            return MA_HOAN
        if not (thu or khong_luu):
            so["phien"].append(phien)
            luu_so(so)
        ghi("── THIẾT LẬP KÊNH {0}{1} ──".format(kenh, " [CHỈ ĐỌC]" if thu else (" [không lưu]" if khong_luu else "")))
        cdp_mod, cdp_studio = _nap_cdp()
        agent.ghi_che_do_mat_cao(ch, False)
        cong = agent._cong_devtools(ch)                             # noqa: SLF001
        tu_mo = True
        agent.mo_chrome_kenh(ch, "https://studio.youtube.com/", chrome, da_chay=False, quet=False)
        ws = agent._cho_devtools(cong, agent.CHO_DEVTOOLS_GIAY)     # noqa: SLF001
        nuoi.nha_khoa("_mo")
        khoa_mo = False
        if not ws:
            raise RuntimeError("Chrome mở nhưng cổng DevTools {0} không đáp".format(cong))
        cdp = cdp_mod.Cdp.mo(ws, nhat_ky=ghi)
        try:
            cdp.goi("Browser.setPermission", {"permission": {"name": "display-capture"}, "setting": "denied",
                                              "origin": "https://studio.youtube.com"}, han=10)
        except Exception:  # noqa: BLE001
            pass
        thu_muc_anh = os.path.join(THU_MUC_SO, kenh)
        st = cdp_studio.TrangStudio.mo_tab_moi(cdp, nhat_ky=ghi, thu_muc_dom=thu_muc_anh, rng=rng)
        S = Studio(st, ghi, thu_muc_anh)
        S.debug = bool(khong_luu)
        uc = S.vao_studio()
        so["uc"] = uc
        ghi("kênh Studio {0}".format(uc))
        ht, loi_doc = S.doc_hien_trang()
        for k, v in loi_doc.items():
            ghi("   không đọc được nhóm {0}: {1}".format(k, v))
        thu_muc_hs = _tl().thu_muc_thiet_lap(kenh)
        hh = _hash_anh(hs, thu_muc_hs)
        kh = khac_biet(hs, ht, so, hh)
        ghi("so với hồ sơ:")
        in_khac_biet(kh, ghi)
        if thu:
            phien["ket_qua"] = "thử: chỉ đọc"
            _ghi_thu(kenh, hs, ht, kh, loi_doc)
            return 0
        for m in ("ten", "handle", "logo", "banner", "hinh_mo"):
            if kh[m]["hien"] is not None and m not in so["truoc"]:
                so["truoc"][m] = kh[m]["hien"] if m in ("ten", "handle") else None
        so["truoc"].setdefault("mo_ta", (ht.get("mo_ta") or "")[:300])
        luu_so(so)
        # đúng rồi thì ghi `dat` luôn (không động vào)
        for m in MUC:
            if kh[m]["khac"] is False and (so["muc"][m].get("tt") != "dat"):
                dat_muc(so, m, kh[m]["mong"], luc0, "đã đúng sẵn — không sửa")
        _chay_nhom(S, hs, kh, so, ht, luc0, ghi, agent, kenh, khong_luu)
        phien["ket_qua"] = "xong lượt"
    except CanNguoi as c:
        ma_thoat = MA_CAN_NGUOI
        phien["ket_qua"] = "can_nguoi: {0}".format(c)
        if not thu:
            so["trang_thai"], so["ly_do"] = "can_nguoi", "cần người xử lý: {0} (không thử lại)".format(c)
            for m in MUC:
                if so["muc"][m].get("tt") != "dat":
                    hong_muc(so, m, "cần người: {0}".format(c), tt="can_nguoi")
        if S:
            S.chup("can-nguoi")
        ghi("DỪNG — cần người xử lý: {0} (không thử lại)".format(c))
    except Hoan as h:
        phien["ket_qua"] = "hoãn: {0}".format(h)
        ghi("hoãn: {0}".format(h))
        ma_thoat = MA_HOAN
    except Exception as loi:  # noqa: BLE001
        phien["ket_qua"] = "lỗi: {0}".format(str(loi)[:150])
        ghi("PHIÊN LỖI: {0}".format(str(loi)[:200]))
        if S:
            S.chup("phien-loi")
        ma_thoat = 1
    finally:
        phien["ket_thuc_luc"] = time.time()
        if not thu and phien in so["phien"]:
            tt, ly = tinh_trang(so) if so.get("trang_thai") != "can_nguoi" else ("can_nguoi", so.get("ly_do", ""))
            so["trang_thai"], so["ly_do"] = tt, ly
            if tt in ("hong", "dang_lam") and ma_thoat in (0, 1):
                so["nghi_den_luc"] = phien["ket_thuc_luc"] + NGHI_SAU_HONG_PHUT * 60
            try:
                luu_so(so)
            except OSError:
                pass
        try:
            if cdp:
                cdp.dong()
            if tu_mo:
                agent.dong_chrome_kenh(ch)
                don_launcher_mo_coi(kenh, ghi)
        finally:
            if khoa_mo:
                nuoi.nha_khoa("_mo")
            if khoa_kenh:
                nuoi.xoa_co_dung(kenh)
                nuoi.nha_khoa(kenh)
            nuoi.nha_khoa("_thiet-lap", THU_MUC_KHOA_RIENG)
    if not thu and ma_thoat == 0:
        if so.get("trang_thai") == "xong":
            d = tat_thiet_lap(kenh)
            ghi("*** XONG: {0} — {1} ***".format(so["ly_do"], ("đã ghi thiet_lap_kenh: false vào " + d) if d
                                                 else "KHÔNG ghi được false vào kenh.yaml, chủ tự tắt"))
            if ghi_ten_yaml(kenh, hs["ten"]):
                ghi("đã cập nhật `ten:` trong kenh.yaml theo tên mới")
            return 0
        return MA_HOAN if so.get("trang_thai") in ("hong", "dang_lam") else 0
    return ma_thoat


def _chay_nhom(S: Studio, hs, kh, so, ht, luc0, ghi, agent, kenh, khong_luu) -> None:
    """Từng nhóm: sửa mục KHÁC → ĐỌC LẠI xác nhận → ghi `dat`/`hong`. Dừng sớm nếu agent đòi Chrome."""
    nhom = (("ho_so", ("ten", "handle", "mo_ta", "logo", "banner", "hinh_mo")),
            ("cai_dat_kenh", ("quoc_gia", "tu_khoa")), ("mac_dinh", ("mac_dinh",)), ("ds_phat", ("danh_sach_phat",)))
    for ten_nhom, muc_nhom in nhom:
        if all(kh[m]["khac"] is False for m in muc_nhom):
            continue
        if _NHOM_CHON and ten_nhom not in _NHOM_CHON:
            continue
        if khong_luu and ten_nhom == "ds_phat":
            ghi("── nhóm ds_phat: [--khong-luu] bỏ qua (tạo danh sách phát là ghi thật vào kênh)")
            continue
        r = ly_do_dung(agent, kenh, time.time())
        if r:
            raise Hoan("dừng sớm nhường việc đăng: " + r)
        ghi("── nhóm {0}: {1}".format(ten_nhom, ", ".join(TEN_MUC[m] for m in muc_nhom if kh[m]["khac"] is not False)))
        try:
            if ten_nhom == "ho_so":
                kq = S.sua_ho_so(hs, kh, so, ht, luc0, ghi, khong_luu)
            elif ten_nhom == "cai_dat_kenh":
                kq = S.sua_cai_dat_kenh(hs, kh, khong_luu)
            elif ten_nhom == "mac_dinh":
                kq = S.sua_mac_dinh(hs, kh, khong_luu)
            else:
                kq = S.sua_ds_phat(hs, ht, ghi)
        except CanNguoi:
            raise
        except (LoiMuc, Exception) as e:  # noqa: BLE001
            ghi("   nhóm {0} hỏng: {1}".format(ten_nhom, str(e)[:160]))
            S.chup("nhom-{0}-hong".format(ten_nhom))
            for m in muc_nhom:
                if kh[m]["khac"] is not False and so["muc"][m].get("tt") != "dat":
                    hong_muc(so, m, str(e))
            luu_so(so)
            continue
        if khong_luu:
            continue
        _doc_lai_va_ghi(S, ten_nhom, muc_nhom, hs, kh, kq, so, luc0, ghi)
        luu_so(so)


def _doc_lai_va_ghi(S: Studio, ten_nhom: str, muc_nhom, hs, kh, kq, so, luc0, ghi) -> None:
    """ĐỌC LẠI Studio sau khi sửa; mục nào khớp hồ sơ → `dat`, còn lại → hong/cho/can_nguoi kèm lý do."""
    ht2: dict = {}
    loi: dict = {}
    try:
        if ten_nhom == "ho_so":
            d = S.doc_ho_so()
            ht2.update(ten=d["ten"], handle=d["handle"], mo_ta=d["mo_ta"],
                       anh={m: bool((d[m] or {}).get("co")) for m in ("logo", "banner", "hinh_mo")},
                       _src={m: (d[m] or {}).get("src") for m in ("logo", "banner", "hinh_mo")})
        elif ten_nhom in ("cai_dat_kenh", "mac_dinh"):
            S.doc_cai_dat(ht2, loi)
        else:
            S.doc_ds_phat(ht2, loi)
    except LoiMuc as e:
        loi["doc_lai"] = str(e)
    so2 = json.loads(json.dumps(so))
    hh = _hash_anh(hs, _tl().thu_muc_thiet_lap(so["kenh"]))
    for m in ("logo", "banner", "hinh_mo"):
        if m in muc_nhom and kq.get(m) is None and kh[m]["khac"]:
            so2["muc"][m] = {"tt": "dat"}
            so2["hash_anh"][m] = hh[m]
    kh2 = khac_biet(hs, ht2, so2, hh)
    for m in muc_nhom:
        k = kq.get(m)
        if k and k[0] == "giong":
            if so["muc"][m].get("tt") != "dat":
                dat_muc(so, m, kh[m]["mong"], luc0, "đã đúng sẵn")
            continue
        if k and k[0] in ("cho", "can_nguoi", "hong"):
            if k[0] == "can_nguoi" and m in ("ten", "handle"):
                ghi_tu_choi(so, m, hs.get(m) if m == "ten" else (so.get("handle_that") or hs.get(m)), k[1], luc0)
            tt = {"cho": "cho", "can_nguoi": "can_nguoi", "hong": "hong"}[k[0]]
            hong_muc(so, m, k[1], tt=tt)
            if tt == "cho":
                so["muc"][m]["mo_lai_luc"] = time.time() + 6 * 3600
            ghi("   {0}: {1} — {2}".format(TEN_MUC[m], tt.upper(), k[1][:120]))
            continue
        if kh[m]["khac"] is False:
            continue
        x = kh2.get(m, {})
        if x.get("khac") is False:
            dat_muc(so, m, kh[m]["mong"], luc0, "đọc lại khớp")
            if m in ("logo", "banner", "hinh_mo"):
                so["hash_anh"][m] = hh[m]
            ghi("   {0}: ĐẠT (đọc lại khớp hồ sơ)".format(TEN_MUC[m]))
        else:
            ly = "đọc lại KHÔNG khớp hồ sơ ({0})".format(x.get("ghi") or loi or "?")
            if m in ("ten", "handle"):
                ly = "Studio không nhận giá trị mới (đọc lại: «{0}») — có thể đã hết lượt đổi".format(str(x.get("hien"))[:60])
                ghi_tu_choi(so, m, hs.get(m) if m == "ten" else (so.get("handle_that") or hs.get(m)), ly, luc0)
                hong_muc(so, m, ly, tt="can_nguoi")
            else:
                hong_muc(so, m, ly)
            ghi("   {0}: HỎNG — {1}".format(TEN_MUC[m], ly[:140]))
    # lượt đổi tên/handle ghi khi Xuất bản; ảnh ghi hash khi đạt


def _ghi_thu(kenh: str, hs: dict, ht: dict, kh: dict, loi: dict) -> None:
    os.makedirs(THU_MUC_SO, exist_ok=True)
    d = ["# Thử (chỉ đọc) — {0} — {1}".format(kenh, time.strftime("%Y-%m-%d %H:%M")), ""]
    for m in MUC:
        x = kh[m]
        d.append("- {0}: {1} · hiện «{2}» · mong «{3}» {4}".format(
            TEN_MUC[m], "?" if x["khac"] is None else ("KHÁC" if x["khac"] else "đúng"), str(x["hien"])[:60], str(x["mong"])[:60], x.get("ghi") or ""))
    if loi:
        d.append("\nLỗi đọc: " + json.dumps(loi, ensure_ascii=False))
    with open(os.path.join(THU_MUC_SO, kenh + ".thu.md"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(d) + "\n")


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="Tự thiết lập kênh YouTube trên Studio theo hồ sơ.")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--thu", action="store_true", help="chỉ ĐỌC Studio + in khác biệt, không sửa, không ghi sổ")
    ap.add_argument("--mo-lai", action="store_true", help="xoá can_nguoi/hong/từ chối cũ rồi chạy")
    ap.add_argument("--khong-luu", action="store_true", help="(dev) điền nhưng KHÔNG Xuất bản/Lưu")
    ap.add_argument("--bo-qua-khung", action="store_true", help="(dev) bỏ khung cấm 02–07h")
    ap.add_argument("--nhom", default="", help="(dev) chỉ chạy nhóm: ho_so,cai_dat_kenh,mac_dinh,ds_phat")
    a = ap.parse_args(argv)
    ghi = _nhat_ky(a.kenh)
    d = nuoi.duong_kenh_yaml(a.kenh)
    if not d:
        ghi("không thấy kenh.yaml của {0}".format(a.kenh))
        return 1
    if not a.thu and not a.khong_luu and not thiet_lap_bat(a.kenh) and not a.mo_lai:
        so = doc_so(a.kenh)
        ghi("kênh {0} không bật thiet_lap_kenh: true — không chạy{1}".format(a.kenh, " (đã xong)" if so.get("trang_thai") == "xong" else ""))
        return MA_KHONG_CAN
    global _NHOM_CHON
    _NHOM_CHON = {x.strip() for x in a.nhom.split(",") if x.strip()} or None
    return chay_phien(a.kenh, ghi, thu=a.thu, mo_lai=a.mo_lai, khong_luu=a.khong_luu, bo_qua_khung=a.bo_qua_khung)


if __name__ == "__main__":
    sys.exit(main())
