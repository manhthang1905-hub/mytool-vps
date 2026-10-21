"""Hằng số + tiện ích chung của não bộ phận — xem `core/nao_bo_phan/__init__.py`."""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: 16 bộ phận: mã → tên đọc. Mọi sự kiện / nơ-ron thuộc đúng MỘT bộ phận.
BO_PHAN: Dict[str, str] = {
    "chon-content": "Chọn content", "kich-ban": "Kịch bản", "tieu-de": "Tiêu đề / SEO", "bia": "Bìa",
    "giong-doc": "Giọng đọc", "anh-clip": "Ảnh / clip", "dung-video": "Dựng video",
    "kiem-chat-luong": "Kiểm chất lượng", "ban-giao": "Bàn giao / lịch", "dang-video": "Đăng video (máy ảo)",
    "binh-luan": "Bình luận / ghim", "chi-so-studio": "Chỉ số Studio", "doi-thu": "Đối thủ",
    "dieu-phoi": "Điều phối / phục hồi", "suc-khoe-may": "Sức khoẻ máy",
    "tang-truong": "Tăng trưởng (cộng sự / kéo chéo)",
}
LOAI = ("chon", "loi", "sua", "ket_qua", "do")

#: Lần gom ĐẦU của một tệp chỉ nhìn lùi ngần này ngày (sự kiện cũ hơn không bao giờ vào sổ).
NGAY_GOM_DAU = 14
#: Nơ-ron lỗi: gặp trong 48h → đang xảy ra; im ≥ 7 ngày → đã hết; quay lại sau quãng im ≥ 7 ngày → tái phát.
GIO_DANG_XAY_RA = 48
NGAY_DA_HET = 7
#: Sổ tay: mục "đã hết gần đây" giữ lỗi hết trong ngần này ngày; bài học cần n ≥ ngần này; trần số dòng.
NGAY_HET_GAN_DAY = 14
N_BAI_HOC_SO_TAY = 3
SO_TAY_TOI_DA_DONG = 40
#: Truy xuất: tỉ lệ quyết định đối chứng, nửa đời độ tươi, sàn của nơ-ron không khớp chữ, thưởng lan 1 bước.
TI_LE_DOI_CHUNG = 0.15
NUA_DOI_NGAY = 14.0
SAN_KHOP = 0.1
LAN_TRUYEN = 0.2

DANG, TAI_PHAT, TAM_LANG, DA_HET = "dang-xay-ra", "tai-phat", "tam-lang", "da-het"
UNG_VIEN, DANG_DUNG, THU_THACH, NGHI = "ung-vien", "dang-dung", "thu-thach", "nghi"
TEN_TRANG_THAI = {DANG: "đang xảy ra", TAI_PHAT: "tái phát", TAM_LANG: "tạm lặng", DA_HET: "đã hết",
                  UNG_VIEN: "ứng viên", DANG_DUNG: "đang dùng", THU_THACH: "thử thách", NGHI: "nghỉ"}

#: Mức nơ-ron lỗi: `canh-bao` khi MỌI sự kiện của nó là cảnh báo (dòng DU PHONG — bộ chọn dự phòng đã cứu; mục kiểm
#: chất lượng mức `canh_bao` — không chặn video); trọng số truy xuất nhân `TRONG_CANH_BAO`, không vào "lỗi đang tăng".
LOI, CANH_BAO = "loi", "canh-bao"
TRONG_CANH_BAO = 0.3
#: Phiên luật ký: đổi luật chữ ký (chuẩn hoá, tách DU PHONG…) thì tăng số này — lượt gom sau tự `ky_lai` một lần.
PHIEN_KY = 2

#: ═══ GIẤC NGỦ (đợt 2) ═══ bộ phận có ≥ ngần này sự kiện mới mới được ngủ; mỗi đêm tối đa ngần này bộ phận (bận
#: nhất trước = cũng là trần số lượt gọi LLM); mỗi bộ phận giữ tối đa ngần này bài học tự rút còn sống.
SU_KIEN_MOI_TOI_THIEU = 20
BO_PHAN_TOI_DA_DEM = 6
BAI_HOC_TOI_DA = 60
LENH_TOI_DA = 5
TRAN_TO_SO = 15000
NGAY_TO_SO = 30
NGAY_CAP = 3
NGAY_CU = 30
GIONG_TRUNG = 0.6
NGUON_NGU = "ngu"

#: Khâu viết (ô `dung_cho` của `core.chien_luoc.bai_hoc`) → bộ phận có não bơm vào lời nhắc.
DUNG_CHO_BO_PHAN = {"chon": "chon-content", "bien_tap": "chon-content", "kich_ban": "kich-ban",
                    "tieu_de": "tieu-de", "bia": "bia"}
#: Mã kiểm chất lượng (tiền tố) → bộ phận làm ra thứ bị kiểm — nơ-ron kiểm chất lượng "liên quan" bộ phận ấy.
MA_KIEM_BO_PHAN = (("kb_", "kich-ban"), ("meta_", "tieu-de"), ("pd_", "giong-doc"), ("clip_", "anh-clip"),
                   ("hinh_", "dung-video"), ("am_", "dung-video"))

#: Nốt thực thể: loại → tên đọc. Nơ-ron nối vào nốt thực thể để "sáng cùng" (lan 1 bước) và để Obsidian vẽ đồ thị.
THUC_THE = {"kenh": "kênh", "khau": "khâu", "engine": "engine", "bo-chon": "bộ chọn", "ma-kiem": "mã kiểm"}
ENGINE = (("veo3", re.compile(r"\bveo ?3?\b", re.I)), ("seedance", re.compile(r"seedance", re.I)),
          ("elevenlabs", re.compile(r"elevenlabs", re.I)), ("tts", re.compile(r"\btts\b", re.I)),
          ("shopapi", re.compile(r"shopapi", re.I)), ("claude-max", re.compile(r"claude (?:max|code)", re.I)))

#: Khâu sản xuất (`core.auto.KHAU`) → bộ phận; nhãn khâu in trong nhật ký → mã khâu.
KHAU_BO_PHAN = {"kich-ban": "kich-ban", "hook": "kich-ban", "tieu-de": "tieu-de", "seo": "tieu-de",
                "giong-doc": "giong-doc", "phu-de": "giong-doc", "bang-canh": "anh-clip", "anh": "anh-clip",
                "anh-noi-canh": "anh-clip", "clip": "anh-clip", "thumbnail": "bia", "dung": "dung-video"}
NHAN_KHAU = {"Viết kịch bản": "kich-ban", "Đọc thành giọng": "giong-doc", "Tách phụ đề": "phu-de",
             "Cắt cảnh và viết lời nhắc": "bang-canh", "Tạo ảnh từng cảnh": "anh", "Tạo clip từng cảnh": "clip",
             "Tạo ảnh bìa": "thumbnail", "Dựng video hoàn thiện": "dung"}
#: Trục bài học (sổ giám đốc `giam-doc/bai-hoc.jsonl` + sổ sản xuất `nghien-cuu/bai-hoc-san-xuat.json`) → bộ phận;
#: trục lạ → chọn content.
TRUC_BO_PHAN = {"tieu_de": "tieu-de", "tieu_de_cum": "tieu-de", "bia": "bia", "thumbnail_ctr": "bia",
                "hook": "kich-ban", "kich_ban": "kich-ban", "mo_dau": "kich-ban", "do_dai": "kich-ban",
                "do_dai_avd": "kich-ban", "giu_chan": "kich-ban", "loi_moi_dk": "kich-ban",
                "cum": "chon-content", "nguon": "chon-content", "tu_do": "chon-content",
                "ctr_browse_48h": "chon-content", "sub_1k_view": "chon-content"}


def duong_db(goc: str) -> str:
    return os.path.join(goc, "nao", "bo-phan.db")


def duong_vault(goc: str) -> str:
    return os.path.join(goc, "nao", "bo-phan")


# ── thời gian ────────────────────────────────────────────────────────────────

def luc_tu(x: Any) -> Optional[float]:
    """Epoch (giây, giờ máy) từ epoch số / chuỗi ISO / "dd/mm/YYYY HH:MM"; không đọc được → None."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x) if x > 1e9 else None
    s = str(x or "").strip()
    if not s:
        return None
    try:
        return _dt.datetime.fromisoformat(s[:19].replace(" ", "T")).timestamp()
    except ValueError:
        pass
    for mau in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(s[:16], mau).timestamp()
        except ValueError:
            continue
    return None


def ngay_gio(luc: Optional[float]) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(luc)) if luc else ""


# ── kênh ────────────────────────────────────────────────────────────────────

_KENH: Dict[str, List[str]] = {}


def cac_kenh(goc: str) -> List[str]:
    """Kênh = thư mục `CHANNEL/<k>` có `kenh.yaml`, không bắt đầu bằng `_`/`.` (bỏ `_NHOM`, `_KHUON`, vỏ rỗng)."""
    if goc not in _KENH:
        thu_muc = os.path.join(goc, "CHANNEL")
        try:
            ten = os.listdir(thu_muc)
        except OSError:
            ten = []
        _KENH[goc] = sorted(t for t in ten if not t.startswith(("_", "."))
                            and os.path.isfile(os.path.join(thu_muc, t, "kenh.yaml")))
    from ..kenh import bo_kenh_tra_kho  # noqa: PLC0415 — 20/10: kênh trả kho không vào não

    return bo_kenh_tra_kho(goc, _KENH[goc])


def tim_kenh(van: str, kenh_ds: Sequence[str]) -> str:
    """Tên kênh DÀI nhất xuất hiện nguyên chữ trong câu ("" nếu không có)."""
    for k in sorted(kenh_ds, key=len, reverse=True):
        if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(k) + r"(?![A-Za-z0-9_])", van):
            return k
    return ""


# ── chữ ký lỗi ───────────────────────────────────────────────────────────────

_A = r"[A-Za-z0-9_-]"
_THAY: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"https?://\S+"), "<duong>"),
    (re.compile(r"(?:[A-Za-z]:[\\/]|\\\\)[^\s'\"<>|]*"), "<duong>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<ma>"),
    (re.compile(r"(?<!" + _A + r")UC" + _A + r"{22}(?!" + _A + r")"), "<uc>"),
)
_RE_MA_DAI = re.compile(r"(?<!" + _A + r")(?=" + _A + r"*\d)(?=" + _A + r"*[A-Za-z])" + _A + r"{16,}(?!" + _A + r")")
_RE_ID = re.compile(r"(?<!" + _A + r")" + _A + r"{11}(?!" + _A + r")")
_RE_HEX = re.compile(r"(?<![A-Za-z0-9])(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{8,}(?![A-Za-z0-9])")
_RE_TRICH = re.compile(r"「.*」|『.*』")           # tham lam: tiêu đề video lồng 「」 bên trong
_RE_CHUOI_SO = re.compile(r"#(?:[\s,.:/×x~–-]*#)+")
_RE_LAP_MA = re.compile(r"(<\w+>)(?:[\s,;]+\1)+")      # "<id>, <id>, <id>" → "<id>" (số mã liệt kê đổi từng lần)


def _la_id(m: re.Match) -> str:
    t = m.group(0)
    return "<id>" if re.search(r"[a-z]", t) and re.search(r"[A-Z0-9]", t) else t


def chuan_hoa(van: Any, kenh_ds: Sequence[str] = ()) -> str:
    """Câu lỗi → mẫu: bỏ đường dẫn/URL, mã (uuid, hex, `UC…`, id video 11 ký tự, mã dài), mã gói → `<goi>`, tên
    kênh → `<kenh>`, chữ trong 「」, số → `#` (dãy số liền nhau gộp một), gộp khoảng trắng, cắt 160 ký tự."""
    s = " ".join(str(van or "").split())
    for re_, thay in _THAY:
        s = re_.sub(thay, s)
    for k in sorted(kenh_ds, key=len, reverse=True):
        s = re.sub(r"(?<!" + _A + r")" + re.escape(k) + r"-\d{3,}(?!" + _A + r")", "<goi>", s)
        s = re.sub(r"(?<!" + _A + r")" + re.escape(k) + r"(?![A-Za-z0-9_])", "<kenh>", s)
    s = _RE_MA_DAI.sub("<ma>", s)
    s = _RE_ID.sub(_la_id, s)
    s = _RE_HEX.sub("<ma>", s)
    s = _RE_TRICH.sub("「…」", s)
    s = _RE_CHUOI_SO.sub("#", re.sub(r"\d+", "#", s))
    s = _RE_LAP_MA.sub(r"\1", s)
    return " ".join(s.split())[:160]


def bam(chu: str, n: int = 10) -> str:
    return hashlib.sha1(chu.encode("utf-8")).hexdigest()[:n]


def chu_ky(van: Any, kenh_ds: Sequence[str] = ()) -> str:
    """Chữ ký = băm ngắn của câu đã chuẩn hoá."""
    return bam(chuan_hoa(van, kenh_ds))


def chu_ky_su_kien(nguon: str, loai: str, noi_dung: Any, so: Dict[str, Any], kenh_ds: Sequence[str],
                   cu: str = "") -> str:
    """Luật ký MỘT chỗ (bộ gom + `ky_lai`): khoá bộ chọn → `dom:` (DU PHONG riêng `dom-du-phong:`), mã kiểm chất
    lượng → `qa:`, lỗi còn lại → câu đã chuẩn hoá; sự kiện khác giữ chữ ký cũ."""
    if so.get("khoa_dom"):
        return bam(("dom-du-phong:" if so.get("kieu") == "DU PHONG" else "dom:") + str(so["khoa_dom"]))
    if nguon == "chat-luong" and so.get("ma") and loai == "loi":
        return bam("qa:" + str(so["ma"]))
    return chu_ky(noi_dung, kenh_ds) if loai == "loi" and noi_dung else cu


def la_canh_bao(nguon: str, so: Dict[str, Any]) -> bool:
    """Sự kiện cảnh báo: dòng DU PHONG (bộ chọn dự phòng đã cứu) hoặc mục kiểm chất lượng mức `canh_bao`."""
    return so.get("kieu") == "DU PHONG" or (nguon == "chat-luong" and so.get("muc") == "canh_bao")


def thuc_the(nguon: str, noi_dung: Any, so: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Thực thể (ngoài kênh) của một sự kiện: khâu, bộ chọn, mã kiểm, engine (nhắc tên trong câu; viết Max = claude-max)."""
    ra = [("khau", str(so["khau"]))] if so.get("khau") else []
    if so.get("khoa_dom"):
        ra.append(("bo-chon", str(so["khoa_dom"])))
    if nguon == "chat-luong" and so.get("ma"):
        ra.append(("ma-kiem", str(so["ma"])))
    van = str(noi_dung or "")
    ra += [("engine", ten) for ten, re_ in ENGINE if re_.search(van) or (ten == "claude-max" and nguon == "viet-max")]
    return ra


def bo_ba(van: Any) -> set:
    """Tập cụm 3 ký tự của câu đã hạ chữ thường, số → `#`, gộp trắng — đo câu na ná (Jaccard)."""
    s = " ".join(re.sub(r"\d+", "#", str(van or "").lower()).split())
    return {s[i:i + 3] for i in range(max(0, len(s) - 2))}


def giong(a: Any, b: Any) -> float:
    x, y = bo_ba(a), bo_ba(b)
    return len(x & y) / len(x | y) if x and y else 0.0


# ── tệp ──────────────────────────────────────────────────────────────────────

def doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def jdong(dong: str) -> Dict[str, Any]:
    """Một dòng JSONL → dict ({} nếu hỏng / không phải dict)."""
    try:
        d = json.loads(dong)
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def doc_chu(duong: str) -> Optional[str]:
    try:
        with io.open(duong, encoding="utf-8", newline="") as tep:
            return tep.read()
    except (OSError, UnicodeDecodeError):
        return None


def ghi_neu_khac(duong: str, noi_dung: str) -> bool:
    """Ghi nguyên tử CHỈ khi nội dung khác bản trên đĩa. Trả True nếu đã ghi."""
    if doc_chu(duong) == noi_dung:
        return False
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8", newline="\n") as tep:
        tep.write(noi_dung)
    os.replace(duong + ".tam", duong)
    return True


# ── ghi chú markdown (frontmatter kiểu YAML, giá trị là vô hướng JSON → Obsidian đọc được) ─────────────────────

_RE_TRON = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")


def _yaml(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(round(v, 4) if isinstance(v, float) else v)
    if isinstance(v, (list, tuple)):
        return json.dumps(list(v), ensure_ascii=False)
    s = str(v if v is not None else "")
    return s if _RE_TRON.fullmatch(s) and s not in ("true", "false", "null") else json.dumps(s, ensure_ascii=False)


def ve_ghi_chu(dau: Dict[str, Any], than: str) -> str:
    return "---\n" + "".join("{0}: {1}\n".format(k, _yaml(v)) for k, v in dau.items()) + "---\n" + than.rstrip() + "\n"


def doc_ghi_chu(van: str) -> Tuple[Dict[str, Any], str]:
    """(frontmatter, thân). Không có frontmatter → ({}, cả bài)."""
    if not van.startswith("---\n"):
        return {}, van
    het = van.find("\n---\n", 3)
    if het < 0:
        return {}, van
    dau: Dict[str, Any] = {}
    for dong in van[4:het].splitlines():
        k, _, v = dong.partition(":")
        v = v.strip()
        try:
            dau[k.strip()] = json.loads(v)
        except ValueError:
            dau[k.strip()] = v
    return dau, van[het + 5:]


def ten_lien_ket(chu: Any, n: int = 100) -> str:
    """Chữ hiện của một [[liên kết|chữ]] — không được chứa `|`, `[`, `]`, xuống dòng."""
    s = " ".join(str(chu or "").split()).replace("|", "/").replace("[", "(").replace("]", ")")
    return s if len(s) <= n else s[: n - 1] + "…"


def lk(dich: str, chu: str = "") -> str:
    """Wikilink tuyệt đối trong vault `nao/` (Obsidian): `[[bo-phan/<dich>|chu]]`."""
    return "[[bo-phan/{0}{1}]]".format(dich, "|" + ten_lien_ket(chu) if chu else "")


def lk_kenh(kenh: str) -> str:
    return lk("thuc-the/kenh/" + ten_tep(kenh), kenh)


def lk_the(the: str) -> str:
    """`"khau/anh"` → `[[bo-phan/thuc-the/khau/anh|khâu anh]]`."""
    loai, _, ten = the.partition("/")
    return lk("thuc-the/{0}/{1}".format(loai, ten_tep(ten)), "{0} {1}".format(THUC_THE.get(loai, loai), ten))


def ghi_nhat_ky(vault: str, bp: str, tieu_de: str, dong: Sequence[str], tran: int = 25) -> bool:
    """Nối MỘT khối vào `<bộ phận>/nhat-ky.md` (append-only; tạo tệp khi chưa có). Không có dòng → không ghi."""
    if not dong:
        return False
    p = os.path.join(vault, bp, "nhat-ky.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    dau = "" if os.path.isfile(p) else ve_ghi_chu({"loai": "nhat-ky", "bo_phan": bp}, (
        "# Nhật ký não — {0}\n\nChỉ nối thêm: mỗi lượt gom / ngủ / soát ghi một khối khi não bộ phận này đổi "
        "(nơ-ron mới, đổi trạng thái, lệnh đã áp).").format(BO_PHAN.get(bp, bp)))
    dong = list(dong[:tran]) + (["- … còn {0} dòng".format(len(dong) - tran)] if len(dong) > tran else [])
    with io.open(p, "a", encoding="utf-8", newline="\n") as tep:
        tep.write(dau + "\n## {0}\n".format(tieu_de) + "\n".join(dong) + "\n")
    return True


def ten_tep(chu: str) -> str:
    return re.sub(r'[<>:"/\\|?*\s]+', "_", str(chu)).strip("._") or "_"
