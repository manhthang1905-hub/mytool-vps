"""Đội chuyên gia + hội đồng quyết định (Đợt F, `workspace/VIEC-CON-LAI-30-09.md`, chủ dự án 01/10/2026).

Quyết định đi như viết content: nhiều góc nhìn → phản biện → chấm → chọn; mã kiểm số ở giữa.

    hop(loai, loi_nhac, so_lieu, goi_chat, *, doc, …)   thân `quan_ly.goi_quyet` khi hội đồng bật
        1. 3 CHUYÊN GIA (Nền tảng · Khán giả · Chủ đề), mỗi người: lời nhắc ngắn theo mục tiêu + lát dữ
           liệu + sổ kinh nghiệm riêng + bài toán → MỘT phương án đúng dạng trả lời của bài toán.
        2. MÃ KIỂM SỐ: số trong `so_dan` phải khớp `so_lieu[khoá]` — luận điểm có số bịa bị loại, phương
           án có số bịa bị loại; số trong chữ không có trong dữ liệu → trừ độ tin.
        3. PHẢN BIỆN: một lượt độc lập (ngữ cảnh mới, mô hình khác) tìm bằng chứng ngược + giải thích khác.
        4. QUYẾT ĐỊNH: `viet_nhieu_ban.cham_va_chon` chấm các phương án còn lại → chọn + độ tin 0–1;
           trái TRI THỨC ĐÃ CHỨNG MINH (`docs/kien-thuc/`) cần độ tin cao hơn.
        5. CỔNG: tin thấp / n ít → chỉ quan sát, hoặc một thay đổi nhỏ quay lui được.
    y_kien_ung_vien(goc, ma, uv, goi_chat, boi_canh)      3 dòng ý kiến cho biên tập viên ("" khi tắt)
    do_chinh_xac(goc, ma) · quyen(goc, ma, loai)          sổ độ chính xác + quyền tự áp theo thành tích
    so_lieu_kenh(bs)                                      {khoá nguồn: số} cho giám đốc kênh

Sổ kinh nghiệm: Nền tảng TOÀN CỤC `workspace/giam-doc/so-nen-tang.jsonl` (+ đọc `chia-se/bai-hoc/` máy
khác) · Khán giả KÊNH `CHANNEL/<k>/giam-doc/so-khan-gia.jsonl` · Chủ đề NGÁCH
`CHANNEL/_NHOM/<ngách>/so-chu-de.jsonl`. Bảng điều khiển đọc `giam-doc/hoi-dong-cuoi.json`.
Cờ: env `SHOPAPI_HOI_DONG=0|1` thắng `workspace/cai-dat.json: hoi_dong` (mặc định bật). Test tắt sẵn.
"""

from __future__ import annotations

import bisect
import datetime as _dt
import glob
import hashlib
import io
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

CHUYEN_GIA: Tuple[Dict[str, Any], ...] = (
    {"ma": "nen_tang", "ten": "NỀN TẢNG", "pham_vi": "toan_cuc",
     "muc_tieu": "hiểu THUẬT TOÁN YouTube: video có được hiển thị không, trang chủ / đề xuất có đẩy không, pool "
                 "đề xuất (video nằm cạnh) có đúng ngách không, giờ đăng, CTR trang chủ. Hỏi: YouTube đang hiểu kênh "
                 "là ai và đang thử video tới đâu?",
     "khoa_so": ("hien_thi", "ctr", "browse", "de_xuat", "pool", "tuoi", "nguong", "/da", "khe", "tran", "may/")},
    {"ma": "khan_gia", "ten": "KHÁN GIẢ", "pham_vi": "kenh",
     "muc_tieu": "hiểu TỆP NGƯỜI XEM của CHÍNH kênh này: họ ở lại bao lâu (giữ chân, AVD), thoát ở đâu và câu kịch "
                 "bản nào ở đó, họ bình luận gì, tuổi, sub/1.000 view. Hỏi: người xem của kênh muốn gì và mất hứng ở đâu?",
     "khoa_so": ("giu", "avd", "gx_1k", "sub", "xem", "gio_xem", "ypp")},
    {"ma": "chu_de", "ten": "CHỦ ĐỀ", "pham_vi": "ngach",
     "muc_tieu": "hiểu THỊ TRƯỜNG NGÁCH: cụm chủ đề nào đang thắng / đang lên / đã nguội, nguồn nào đã chứng minh nổ, "
                 "ĐÀ TĂNG view/ngày hơn tổng view. Hỏi: đề tài nào ngách đang muốn, đề tài nào đã hết thời?",
     "khoa_so": ("cum", "thang", "truot", "ti_le", "cong_thuc", "nguon", "hien_thi_48h", "kl_28")},
)
TEN = {c["ma"]: c["ten"].capitalize() for c in CHUYEN_GIA}
TOI_DA_TOKEN_PHAN_BIEN = 1500
TOI_DA_TOKEN_CHAM = 1500
TOI_DA_TOKEN_Y_KIEN = 500
NGUONG_TIN = 0.6           # độ tin tối thiểu để áp đủ
NGUONG_TIN_TRAI = 0.8      # … khi trái tri thức đã chứng minh
NGUONG_THU_NHO = 0.4       # dưới đây: chỉ quan sát
N_IT = 3                   # cỡ mẫu dưới đây: tối đa thay đổi nhỏ
TU_AP_TI_LE, TU_AP_N, LUI_TI_LE = 0.70, 10, 0.55
TEP_CUOI = "hoi-dong-cuoi.json"
TEP_NHAT_KY = "hoi-dong.jsonl"
TEP_DO_CHINH_XAC = "do-chinh-xac.json"
TEP_TRI_THUC = ("con-duong-kenh-thang.md", "nghien-cuu-bia.md")
LOAI_DO = {"chan_doan_cong": "chẩn đoán cổng", "du_doan": "dự đoán thắng/trượt", "bai_hoc": "bài học",
           "doi_chuan": "đổi chuẩn", "chia_khe": "chia khe",
           "du_doan_bien_tap": "dự đoán của biên tập (tự học)"}
#: Khoá thực đơn = quyết định LỚN (đổi chiến lược) — không bao giờ tự áp, vào "Việc của bạn".
KHOA_LON = ("chien_luoc", "chien_luoc_tu_hoc", "cong_thuc_chon")


# ── tiện ích ───────────────────────────────────────────────────────────────

def _gon(x: Any, n: int) -> str:
    s = " ".join(str(x or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1, default=str)
    os.replace(duong + ".tam", duong)


def _doc_dong(duong: str) -> List[Dict[str, Any]]:
    ra = []
    try:
        with io.open(duong, encoding="utf-8") as tep:
            for dong in tep:
                try:
                    d = json.loads(dong)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    ra.append(d)
    except OSError:
        pass
    return ra


def _luc() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def bat(goc: str) -> bool:
    """Hội đồng bật? env `SHOPAPI_HOI_DONG` thắng `workspace/cai-dat.json: hoi_dong` (mặc định True)."""
    env = os.environ.get("SHOPAPI_HOI_DONG", "").strip()
    if env:
        return env not in ("0", "false", "tat")
    cai = _doc_json(os.path.join(goc, "workspace", "cai-dat.json"), {}) if goc else {}
    v = (cai or {}).get("hoi_dong", True) if isinstance(cai, dict) else True
    return str(v).strip().lower() not in ("false", "0", "tat")


def _cai_kenh(goc: str, ma: str) -> Dict[str, Any]:
    if not (goc and ma):
        return {}
    try:
        from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        return dict(doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {})
    except Exception:  # noqa: BLE001
        return {}


def _ngach(goc: str, ma: str) -> str:
    return str(_cai_kenh(goc, ma).get("nhom") or "").strip()


# ── số: đọc, khớp, quét chữ ────────────────────────────────────────────────

_SO = re.compile(r"\d+(?:[.,]\d+)*")


def _ung_vien_so(t: str) -> List[float]:
    """"1.200" → [1200, 1.2]; "9,7" → [9.7]; "1,200" → [1200, 1.2]; "47121" → [47121]."""
    ra: List[float] = []
    for chu in {t.replace(".", "").replace(",", "") if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", t) else "",
                t.replace(",", "."), t.replace(",", "") if t.count(",") and t.count(".") else "",
                t.replace(".", "").replace(",", ".") if t.count(",") and t.count(".") else ""}:
        try:
            if chu and chu.count(".") <= 1:
                ra.append(float(chu))
        except ValueError:
            continue
    return ra


def _so_cua(x: Any) -> List[float]:
    if isinstance(x, bool):
        return []
    if isinstance(x, (int, float)):
        return [float(x)]
    return [v for t in _SO.findall(str(x or "")) for v in _ung_vien_so(t)][:4]


def _gan(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.05, abs(b) * 0.01)


def khop(so: Any, gia_tri: Any) -> bool:
    """Số LLM trích có khớp giá trị nguồn không (cùng sai số `kham_nghiem.doc_ket_qua`)."""
    g = _so_cua(gia_tri)
    return bool(g) and any(_gan(s, g[0]) for s in _so_cua(so))


def kiem_so_dan(ds: Any, so_lieu: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """[{so, nguon}] → (khớp, bịa). Khoá không có trong `so_lieu` = bịa."""
    dung, bia = [], []
    for x in ds if isinstance(ds, list) else []:
        if not isinstance(x, dict) or not str(x.get("nguon") or "").strip():
            continue
        k = str(x["nguon"]).strip()
        (dung if k in so_lieu and khop(x.get("so"), so_lieu[k]) else bia).append(
            {"so": x.get("so"), "nguon": k, "that": so_lieu.get(k)})
    return dung, bia


def tap_so(*chu: str, so_lieu: Optional[Dict[str, Any]] = None) -> List[float]:
    """Mọi số có trong dữ liệu đưa cho LLM (chữ lời nhắc + giá trị `so_lieu`), đã sắp."""
    ra = set()
    for c in chu:
        for t in _SO.findall(c or ""):
            ra.update(_ung_vien_so(t))
    for v in (so_lieu or {}).values():
        ra.update(_so_cua(v))
    return sorted(ra)


def so_khong_nguon(chu: str, tap: Sequence[float]) -> List[str]:
    """Số trong `chu` không thấy trong dữ liệu (bỏ số đếm nhỏ ≤ 12). Số tự tính (tỉ lệ, hiệu) cũng rơi vào
    đây — nên chỉ TRỪ độ tin, không loại."""
    ra = []
    for t in _SO.findall(chu or ""):
        vs = _ung_vien_so(t)
        if not vs or all(v <= 12 and float(v).is_integer() for v in vs):
            continue
        thay = False
        for v in vs:
            i = bisect.bisect_left(tap, v - max(0.05, abs(v) * 0.011))
            if i < len(tap) and tap[i] <= v + max(0.05, abs(v) * 0.011):
                thay = True
                break
        if not thay and t not in ra:
            ra.append(t)
    return ra[:12]


# ── tri thức đã chứng minh ─────────────────────────────────────────────────

def tri_thuc(goc: str, toi_da: int = 14) -> List[str]:
    """Các câu IN ĐẬM (đã chứng minh) trong `docs/kien-thuc/{con-duong-kenh-thang,nghien-cuu-bia}.md`."""
    ra: List[str] = []
    for ten in TEP_TRI_THUC:
        try:
            with io.open(os.path.join(goc, "docs", "kien-thuc", ten), encoding="utf-8") as tep:
                dong = tep.read().splitlines()
        except OSError:
            continue
        for d in dong:
            if "**" not in d or d.lstrip().startswith("#") or "|" in d:
                continue
            s = re.sub(r"\*\*|\*|`", "", d).strip(" -0123456789.")
            if len(s) >= 25:
                ra.append(_gon(s, 230))
    return ra[:toi_da]


# ── sổ kinh nghiệm ─────────────────────────────────────────────────────────

def duong_so(goc: str, ma: str, cg: str) -> str:
    if cg == "nen_tang":
        return os.path.join(goc, "workspace", "giam-doc", "so-nen-tang.jsonl")
    if cg == "chu_de":
        ng = _ngach(goc, ma)
        if ng and os.path.isdir(os.path.join(goc, "CHANNEL", "_NHOM", ng)):
            return os.path.join(goc, "CHANNEL", "_NHOM", ng, "so-chu-de.jsonl")
    return os.path.join(goc, "CHANNEL", ma or "_", "giam-doc", "so-{0}.jsonl".format(cg.replace("_", "-")))


def doc_so(goc: str, ma: str, cg: str, toi_da: int = 6) -> List[str]:
    """Bài trong sổ của chuyên gia, gộp theo khoá (n = số video ủng hộ), n lớn + mới trước."""
    if not goc or (cg != "nen_tang" and not ma):
        return []
    nhom: Dict[str, List[Dict[str, Any]]] = {}
    for d in _doc_dong(duong_so(goc, ma, cg)):
        if d.get("cau"):
            nhom.setdefault(str(d.get("khoa") or d["cau"])[:80], []).append(d)
    ds = sorted(nhom.values(), key=lambda xs: str(xs[-1].get("luc")), reverse=True)        # mới trước …
    ds.sort(key=lambda xs: -len({x.get("video_id") for x in xs}))                          # … rồi n lớn trước
    ra = ["- {0} (n={1}{2})".format(_gon(xs[-1]["cau"], 220), len({x.get("video_id") for x in xs}),
                                    ", bóng" if all(x.get("bong") for x in xs) else "") for xs in ds[:toi_da]]
    if cg == "nen_tang":  # máy khác (chia-se/bai-hoc): bài phạm vi kênh n ≥ 3 làm tiên nghiệm ngoài
        try:
            from ..dong_bo_git import doc_cau_hinh  # noqa: PLC0415

            ma_may = doc_cau_hinh(goc).get("ma_may")
        except Exception:  # noqa: BLE001
            ma_may = None
        for p in sorted(glob.glob(os.path.join(goc, "chia-se", "bai-hoc", "*.json"))):
            du = _doc_json(p, {}) or {}
            if not isinstance(du, dict) or (ma_may and du.get("ma_may") == ma_may):
                continue
            for b in (du.get("bai_hoc") or [])[:3]:
                if isinstance(b, dict) and b.get("cau"):
                    ra.append("- (máy {0}) {1} (n={2})".format(du.get("ma_may"), _gon(b["cau"], 180), b.get("n")))
    return ra[: toi_da + 3]


def ghi_bai(goc: str, ma: str, cg: str, bai: Dict[str, Any]) -> None:
    """Thêm/thay một bài vào sổ của chuyên gia `cg` — cùng (video, mốc, chuyên gia) thì thay."""
    duong = duong_so(goc, ma, cg)
    ds = [d for d in _doc_dong(duong) if not (d.get("video_id") and d.get("video_id") == bai.get("video_id")
                                             and d.get("moc") == bai.get("moc") and d.get("kenh") == bai.get("kenh"))]
    ds.append(bai)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8", newline="\n") as tep:
        tep.write("".join(json.dumps(d, ensure_ascii=False, default=str) + "\n" for d in ds[-400:]))
    os.replace(duong + ".tam", duong)


# ── lát dữ liệu ────────────────────────────────────────────────────────────

def _an_toan(f: Callable[[], str], n: int = 1500) -> str:
    try:
        return _gon_dong(f() or "", n)
    except Exception:  # noqa: BLE001
        return ""


def _gon_dong(chu: str, n: int) -> str:
    return chu if len(chu) <= n else chu[: n - 1] + "…"


def lat_du_lieu(goc: str, ma: str, cg: str, so_lieu: Optional[Dict[str, Any]] = None,
                boi_canh: Optional[Dict[str, str]] = None) -> str:
    """Lát riêng của chuyên gia: khoá SỐ LIỆU thuộc góc mình + vài khối chữ đọc đĩa (0 đồng)."""
    c = next(x for x in CHUYEN_GIA if x["ma"] == cg)
    khoa = [k for k in (so_lieu or {}) if any(t in k for t in c["khoa_so"])]
    ra = ["Số thuộc góc bạn (đọc kỹ nhất): " + ", ".join(khoa[:40])] if khoa else []
    bc = boi_canh or {}
    if not ma:
        return "\n".join(ra)
    from datetime import datetime  # noqa: PLC0415

    from .. import bien_tap_content as btc  # noqa: PLC0415

    if cg == "nen_tang":
        x = bc.get("xu_huong") or _an_toan(lambda: btc._xu_huong(goc, ma, datetime.now()))  # noqa: SLF001
        if x:
            ra.append("TRANG CHỦ ĐANG PHÁT (máy ảo, theo cụm):\n" + _gon_dong(x, 1500))
    elif cg == "khan_gia":
        x = bc.get("khan_gia") or _an_toan(lambda: btc._khan_gia(goc, ma))  # noqa: SLF001
        if x:
            ra.append("TỆP KHÁN GIẢ:\n" + _gon_dong(x, 1200))
    else:
        x = _an_toan(lambda: btc._thang_truot_theo_cum(goc, ma, datetime.now()), 1800)  # noqa: SLF001
        if x:
            ra.append("CỤM THẮNG / TRƯỢT (cả nhóm):\n" + x)
    return "\n".join(ra)


# ── lời nhắc ───────────────────────────────────────────────────────────────

def _khoi_so_lieu(so_lieu: Dict[str, Any]) -> str:
    return "SỐ LIỆU (khoá = giá trị)\n" + "\n".join("{0} = {1}".format(k, v) for k, v in so_lieu.items())


def loi_nhac_chuyen_gia(cg: Dict[str, Any], loai: str, ma: str, loi_nhac: str, so_lieu: Dict[str, Any],
                        so_kn: List[str], lat: str, tt: List[str]) -> str:
    them_bai = loai == "kham_nghiem"
    dong = [
        "Bạn là CHUYÊN GIA {0} trong đội cố vấn của kênh YouTube {1}. MỤC TIÊU CỦA BẠN: {2}\n"
        "Đọc bài toán dưới đây từ GÓC CỦA BẠN và đưa ra MỘT phương án hoàn chỉnh theo đúng dạng trả lời của bài "
        "toán. Hai chuyên gia khác (góc khác) cũng làm; một người phản biện sẽ soi số của bạn.".format(
            cg["ten"], ma or "(công ty)", cg["muc_tieu"]),
        "SỔ KINH NGHIỆM CỦA BẠN ({0}):\n{1}".format(
            {"toan_cuc": "toàn cục", "kenh": "kênh", "ngach": "ngách"}[cg["pham_vi"]], "\n".join(so_kn) or "(chưa có)"),
    ]
    if lat:
        dong.append("LÁT DỮ LIỆU CỦA BẠN\n" + lat)
    if tt:
        dong.append("TRI THỨC ĐÃ CHỨNG MINH (đi ngược phải có số của chính kênh mạnh hơn):\n" + "\n".join("- " + x for x in tt))
    dong.append("═══ BÀI TOÁN ═══\n" + loi_nhac)
    if so_lieu and "SỐ LIỆU" not in loi_nhac:
        dong.append(_khoi_so_lieu(so_lieu))
    dong.append(
        "═══ THÊM vào khối JSON trả lời ═══\n"
        "\"luan_diem\": [{{\"cau\": \"1 câu có số, từ góc {0}\", \"so_dan\": [{{\"so\": 1.2, \"nguon\": \"<khoá SỐ LIỆU>\"}}]}}]"
        " (2–4 luận điểm),\n\"so_dan\": [mọi số bạn dùng: giá trị NGUYÊN VĂN trong SỐ LIỆU kèm đúng khoá; số tự tính "
        "(tỉ lệ, hiệu) không ghi vào so_dan]{1}\nSố bịa / khoá sai → phương án của bạn bị loại.".format(
            cg["ten"].lower(), ",\n\"bai_hoc_cua_toi\": {\"khoa\": \"ngắn, vd ctr_browse|thap\", \"cau\": \"1 câu có số "
            "cho sổ kinh nghiệm của bạn — không nêu mã video / tên kênh\", \"so_dan\": [...]}" if them_bai else ""))
    return "\n\n".join(dong)


def _tom(du: Dict[str, Any], n: int = 2400) -> str:
    """Phương án gọn cho phản biện / chấm: bỏ so_dan; mục `chon` chỉ giữ trường mô tả."""
    x = {k: v for k, v in du.items() if k not in ("so_dan", "bai_hoc_cua_toi")}
    if isinstance(x.get("chon"), list):
        x["chon"] = [{k: v for k, v in m.items() if k in ("id", "loai", "khoa", "gia_tri_cu", "gia_tri", "noi_dung",
                                                          "ly_do", "ly_do_llm", "ma", "khe_cu", "khe_moi", "video_id")}
                     if isinstance(m, dict) else m for m in x["chon"]]
    return _gon_dong(json.dumps(x, ensure_ascii=False, default=str), n)


def loi_nhac_phan_bien(loai: str, ma: str, so_lieu: Dict[str, Any], pa: List[Tuple[str, str, str]],
                       tt: List[str]) -> str:
    return "\n\n".join([
        "Bạn là NGƯỜI PHẢN BIỆN ĐỘC LẬP cho quyết định \"{0}\" của kênh YouTube {1}. View = Hiển thị × CTR × Giữ "
        "chân. Với TỪNG phương án: tìm BẰNG CHỨNG NGƯỢC trong SỐ LIỆU (số nào bác nó) và MỘT GIẢI THÍCH KHÁC cho "
        "cùng các số. Không đề xuất phương án mới; không khen.".format(loai, ma or "(công ty)"),
        _khoi_so_lieu(so_lieu) if so_lieu else "SỐ LIỆU: (không có bảng khoá — chỉ soi lập luận)",
        "TRI THỨC ĐÃ CHỨNG MINH:\n" + ("\n".join("- " + x for x in tt) or "(không có)"),
        "\n\n".join("PHƯƠNG ÁN {0} (chuyên gia {1}):\n{2}".format(nh, ten, chu) for nh, ten, chu in pa),
        "Chỉ trả MỘT khối JSON: {" + ", ".join(
            "\"{0}\": {{\"nguoc\": \"1–2 câu có số\", \"giai_thich_khac\": \"1 câu\", \"muc\": \"manh|vua|yeu\", "
            "\"so_dan\": [{{\"so\": 1, \"nguon\": \"<khoá>\"}}]}}".format(nh) for nh, _t, _c in pa) + "}",
    ])


KHUON_CHAM = (
    "Bạn là HỘI ĐỒNG QUYẾT ĐỊNH của <<KENH>> (việc: <<LOAI>>). Dưới đây là <<SO_BAN>> phương án của đội chuyên "
    "gia, mỗi phương án kèm ý kiến PHẢN BIỆN độc lập và kết quả MÃ KIỂM SỐ. Chấm từng phương án 0–10 rồi CHỌN MỘT:\n"
    "<<TIEU_CHI>>\n\nTRI THỨC ĐÃ CHỨNG MINH:\n<<TRI_THUC>>\n\n"
    "trả về DUY NHẤT một JSON:\n{\"chon\": \"A\", \"diem\": {\"A\": 7, \"B\": 5}, \"do_tin\": 0.7, "
    "\"trai_tri_thuc\": false, \"ly_do\": \"2–3 câu có số: vì sao phương án này hơn\", \"diem_manh\": \"…\", "
    "\"diem_yeu\": \"…\", \"cho_de_rot\": \"điều gì có thể làm quyết định này SAI\"}\n"
    "(do_tin 0–1 = xác suất phương án đúng; trai_tri_thuc = true nếu phương án đi ngược tri thức ở trên)\n\n<<CAC_BAN>>")
TIEU_CHI_CHAM = (
    "1. Đúng cổng hỏng / đúng mục tiêu kênh, có số của CHÍNH kênh chống lưng (không phải cảm giác)\n"
    "2. Chịu được phản biện: bằng chứng ngược yếu, giải thích khác kém thuyết phục hơn\n"
    "3. Không trái tri thức đã chứng minh — trái thì chỉ chọn khi số của kênh mạnh hơn, và ghi trai_tri_thuc\n"
    "4. Ít thay đổi, quay lui được, đo được; n nhỏ thì phương án thận trọng hơn được điểm cao hơn")


# ── gọi LLM theo thang ─────────────────────────────────────────────────────

def _thang(goc: str, ma: str) -> List[str]:
    from ..bien_tap_content import thang_mo_hinh  # noqa: PLC0415

    return list(thang_mo_hinh(goc, ma))[:3]


def _goi(goi_chat: Callable[..., str], ln: str, thang: List[str], khoa: str, toi_da_token: int,
         doc: Callable[[str], Any], ghi: Optional[Callable[[str], None]] = None,
         nhan: str = "") -> Tuple[Any, str, str, str]:
    """(kết quả doc, thô, mô hình, lỗi) — thử từng bậc thang."""
    loi = ""
    for lan, mh in enumerate(thang, 1):
        try:
            tho = goi_chat(ln, mo_hinh=mh, khoa="{0}-{1}".format(khoa, lan), toi_da_token=toi_da_token)
        except Exception as e:  # noqa: BLE001
            loi = "{0}: {1}".format(mh, str(e)[:120])
            if ghi:
                ghi("  [hội đồng] {0} {1} hỏng — thử bậc dưới.".format(nhan, loi))
            continue
        try:
            kq = doc(tho)
        except Exception:  # noqa: BLE001
            kq = None
        if kq is not None:
            return kq, tho, mh, ""
        loi = "{0}: trả lời không đọc được — {1}".format(mh, _gon(tho, 100))
    return None, "", "", loi or "không mô hình nào trả lời"


def _json(tho: str) -> Optional[Dict[str, Any]]:
    from ..goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return None
    return du if isinstance(du, dict) else None


def _chu_cua(du: Dict[str, Any]) -> str:
    """Chữ lập luận của phương án (để quét số không nguồn)."""
    ph = [str(du.get(k) or "") for k in ("chan_doan", "vi_sao", "tuan_toi", "du_doan_lech")]
    ph += [str(m.get("ly_do") or "") for m in du.get("chon") or [] if isinstance(m, dict)]
    return " ".join(ph)


def _chu_ky(ket: Dict[str, Any]) -> Any:
    if isinstance(ket.get("chon"), list):
        return tuple(sorted(str(m.get("id")) for m in ket["chon"] if isinstance(m, dict)))
    return ket.get("cong_hong")


def _ap_cong(ket: Dict[str, Any], cong: str) -> Dict[str, Any]:
    """Cổng: quan_sat → bỏ mọi thay đổi (và bài học); thu_nho → ≤ 1 thay đổi quay lui được."""
    ket = dict(ket)
    if isinstance(ket.get("chon"), list):
        if cong == "quan_sat":
            ket["chon"] = []
        elif cong == "thu_nho":
            nho = [m for m in ket["chon"] if isinstance(m, dict) and m.get("loai") != "viec_studio"
                   and str(m.get("khoa") or "") not in KHOA_LON]
            ket["chon"] = nho[:1]
    if cong == "quan_sat" and "bai_hoc" in ket:
        ket["bai_hoc"] = None
    return ket


# ── HỘI ĐỒNG ───────────────────────────────────────────────────────────────

def hop(loai: str, loi_nhac: str, so_lieu: Optional[Dict[str, Any]], goi_chat: Callable[..., str], *,
        doc: Callable[[str], Optional[Dict[str, Any]]], goc: str = "", ma: str = "", khoa: str = "",
        toi_da_token: int = 3000, ghi: Optional[Callable[[str], None]] = None, n: Optional[int] = None,
        luu: bool = True, nhan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Một phiên hội đồng. Trả {ket, mo_hinh, tho, loi, hoi_dong} như `goi_quyet` (+ biên bản)."""
    so_lieu = dict(so_lieu or {})
    thang = _thang(goc, ma)
    tt = tri_thuc(goc) if goc else []
    hd: Dict[str, Any] = {"loai": loai, "ma": ma, "luc": _luc(), "n": n, "chuyen_gia": [], "phan_bien": {},
                          "quyet": {}, "cong": "", "loi": ""}
    pa: List[Dict[str, Any]] = []
    for cg in CHUYEN_GIA:
        ln = loi_nhac_chuyen_gia(cg, loai, ma, loi_nhac, so_lieu, doc_so(goc, ma, cg["ma"]),
                                 lat_du_lieu(goc, ma, cg["ma"], so_lieu) if goc else "", tt)
        ket, tho, mh, loi = _goi(goi_chat, ln, thang, "{0}-{1}".format(khoa, cg["ma"]), toi_da_token, doc, ghi,
                                 cg["ten"])
        du = _json(tho) if ket is not None else None
        x = {"ma": cg["ma"], "ten": TEN[cg["ma"]], "mo_hinh": mh, "loi": loi}
        if ket is None or du is None:
            hd["chuyen_gia"].append(dict(x, loai_bo=True, ly_do_loai=loi or "không đọc được"))
            continue
        dung, bia = kiem_so_dan(du.get("so_dan"), so_lieu)
        ld = []
        for d in du.get("luan_diem") or []:
            if isinstance(d, dict) and d.get("cau"):
                d_ok, d_bia = kiem_so_dan(d.get("so_dan"), so_lieu)
                ld.append({"cau": _gon(d["cau"], 260), "so_khop": len(d_ok), "so_bia": d_bia, "giu": not d_bia})
        tap = tap_so(ln, so_lieu=so_lieu)
        knv = so_khong_nguon(_chu_cua(du) + " " + " ".join(d["cau"] for d in ld if d["giu"]), tap)
        bh = du.get("bai_hoc_cua_toi") if isinstance(du.get("bai_hoc_cua_toi"), dict) else None
        if bh:
            b_ok, b_bia = kiem_so_dan(bh.get("so_dan"), so_lieu)
            bh = {"khoa": _gon(bh.get("khoa"), 60), "cau": _gon(bh.get("cau"), 260), "so_dan": b_ok, "so_bia": b_bia,
                  "giu": bool(re.search(r"\d", str(bh.get("cau") or ""))) and not b_bia}
        x.update(phuong_an=_tom(du), luan_diem=ld, so_khop=len(dung), so_bia=bia, so_khong_nguon=knv,
                 bai_hoc_cua_toi=bh, loai_bo=bool(bia), ly_do_loai="số bịa: " + ", ".join(
                     "{0}={1} (thật {2})".format(b["nguon"], b["so"], b["that"]) for b in bia[:4]) if bia else "")
        hd["chuyen_gia"].append(x)
        pa.append({"x": x, "ket": ket, "tho": tho, "du": du, "mo_hinh": mh})
    if not pa:
        hd["loi"] = "không chuyên gia nào trả lời được"
        _luu(goc, ma, hd, luu)
        return {"ket": None, "mo_hinh": "", "tho": "", "loi": hd["loi"], "hoi_dong": hd}
    con = [p for p in pa if not p["x"]["loai_bo"]]
    ep_quan_sat = not con
    if not con:  # mọi phương án có số bịa: giữ phương án ít bịa nhất, chỉ quan sát
        con = [min(pa, key=lambda p: (len(p["x"]["so_bia"]), -p["x"]["so_khop"]))]
    # thứ tự đưa vào chấm: số khớp nhiều, số không nguồn ít trước (chấm hỏng → chọn bản đầu)
    con.sort(key=lambda p: (len(p["x"]["so_khong_nguon"]) - p["x"]["so_khop"]))
    nh = [chr(65 + i) for i in range(len(con))]
    # PHẢN BIỆN — ngữ cảnh mới, mô hình khác (bậc 2 của thang trước)
    pb: Dict[str, Any] = {}
    thang_pb = thang[1:] + thang[:1] if len(thang) > 1 else thang
    ln_pb = loi_nhac_phan_bien(loai, ma, so_lieu, [(nh[i], p["x"]["ten"], p["x"]["phuong_an"]) for i, p in enumerate(con)], tt)
    du_pb, _t, mh_pb, loi_pb = _goi(goi_chat, ln_pb, thang_pb, "{0}-phan-bien".format(khoa), TOI_DA_TOKEN_PHAN_BIEN,
                                    _json, ghi, "phản biện")
    for i, p in enumerate(con):
        y = (du_pb or {}).get(nh[i]) if isinstance((du_pb or {}).get(nh[i]), dict) else {}
        ok, bia = kiem_so_dan(y.get("so_dan"), so_lieu)
        muc = str(y.get("muc") or "").strip().lower()
        pb[p["x"]["ma"]] = {"nguoc": _gon(y.get("nguoc"), 300), "giai_thich_khac": _gon(y.get("giai_thich_khac"), 240),
                            "muc": muc if muc in ("manh", "vua", "yeu") and not bia else ("yeu" if bia else ""),
                            "so_khop": len(ok), "so_bia": bia}
    hd["phan_bien"] = {"mo_hinh": mh_pb, "loi": loi_pb, "y_kien": pb}
    # QUYẾT ĐỊNH — cham_va_chon (viết N phương án → chấm → chọn)
    from ..viet_nhieu_ban import cham_va_chon  # noqa: PLC0415

    ban = []
    for i, p in enumerate(con):
        y = pb.get(p["x"]["ma"]) or {}
        ban.append("Chuyên gia {0}:\n{1}\nPHẢN BIỆN ({2}): {3} — giải thích khác: {4}\nMÃ KIỂM SỐ: {5} số khớp nguồn, "
                   "{6} số bịa, số không thấy trong dữ liệu: {7}".format(
                       p["x"]["ten"], p["x"]["phuong_an"], y.get("muc") or "?", y.get("nguoc") or "—",
                       y.get("giai_thich_khac") or "—", p["x"]["so_khop"], len(p["x"]["so_bia"]),
                       ", ".join(p["x"]["so_khong_nguon"]) or "không"))
    hop_tho: Dict[str, str] = {}

    def goi_cham(de_bai: str) -> str:
        loi_c = ""
        for lan, mh in enumerate(thang, 1):
            try:
                t = goi_chat(de_bai, mo_hinh=mh, khoa="{0}-cham-{1}".format(khoa, lan), toi_da_token=TOI_DA_TOKEN_CHAM)
            except Exception as e:  # noqa: BLE001
                loi_c = str(e)[:120]
                continue
            if _json(t) and str((_json(t) or {}).get("chon") or "").strip():
                hop_tho.update(tho=t, mo_hinh=mh)
                return t
        raise RuntimeError(loi_c or "chấm không đọc được")

    i_chon, ly_do, diem, _bang = cham_va_chon(
        goi_cham if len(con) > 1 else None, ban, "", khuon_cham=KHUON_CHAM, tieu_chi=TIEU_CHI_CHAM,
        chung={"KENH": "kênh " + ma if ma else "công ty", "LOAI": loai,
               "TRI_THUC": "\n".join("- " + x for x in tt) or "(không có)"},
        ten_ban=[p["x"]["ten"] for p in con])
    chon = con[i_chon]
    dc = _json(hop_tho.get("tho", "")) or {}
    try:
        tin_llm = float(dc.get("do_tin"))
    except (TypeError, ValueError):
        d_ = diem.get(nh[i_chon]) if isinstance(diem, dict) else None
        tin_llm = float(d_) / 10.0 if isinstance(d_, (int, float)) else 0.5
    tin_llm = max(0.0, min(1.0, tin_llm if tin_llm <= 1.0 else tin_llm / 10.0))
    trai = str(dc.get("trai_tri_thuc")).strip().lower() == "true"
    dong_thuan = sum(1 for p in con if p is not chon and _chu_ky(p["ket"]) == _chu_ky(chon["ket"]))
    muc_pb = (pb.get(chon["x"]["ma"]) or {}).get("muc")
    tin = tin_llm - {"manh": 0.15, "vua": 0.05}.get(muc_pb or "", 0.0) + 0.05 * dong_thuan \
        - min(0.15, 0.03 * len(chon["x"]["so_khong_nguon"]))
    tin = round(max(0.0, min(1.0, tin)), 2)
    nguong = NGUONG_TIN_TRAI if trai else NGUONG_TIN
    cong = "ap" if tin >= nguong else ("thu_nho" if tin >= NGUONG_THU_NHO else "quan_sat")
    if n is not None and n < N_IT and cong == "ap":
        cong = "thu_nho"
    if ep_quan_sat:
        cong = "quan_sat"
    ket = _ap_cong(chon["ket"], cong)
    hd["quyet"] = {"chon": chon["x"]["ma"], "ten": chon["x"]["ten"], "nhan": nh[i_chon], "diem": diem,
                   "do_tin_llm": round(tin_llm, 2), "do_tin": tin, "trai_tri_thuc": trai, "dong_thuan": dong_thuan,
                   "phan_bien": muc_pb or "", "ly_do": _gon(ly_do, 700), "mo_hinh": hop_tho.get("mo_hinh", "")}
    hd["cong"], hd["nguong"] = cong, nguong
    hd["cat_boi_cong"] = len((chon["ket"] or {}).get("chon") or []) - len(ket.get("chon") or []) \
        if isinstance(ket.get("chon"), list) else 0
    if ghi:
        ghi("  [hội đồng] {0}: chọn {1} · tin {2} ({3}) · {4} phương án, loại {5} vì số bịa".format(
            loai, chon["x"]["ten"], tin, cong, len(pa), sum(1 for p in pa if p["x"]["loai_bo"])))
    if luu and goc and loai == "kham_nghiem":
        _ghi_bai_chuyen_gia(goc, ma, pa, nhan or {})
    _luu(goc, ma, hd, luu)
    return {"ket": ket, "mo_hinh": chon["mo_hinh"], "tho": chon["tho"], "loi": "", "hoi_dong": hd}


def _ghi_bai_chuyen_gia(goc: str, ma: str, pa: List[Dict[str, Any]], nhan: Dict[str, Any]) -> None:
    """Khám nghiệm: mỗi chuyên gia ghi bài học từ góc mình vào SỔ CỦA MÌNH (số khớp mới ghi)."""
    bong = str(_cai_kenh(goc, ma).get("giam_doc") or "tat").strip().lower() != "tu_ap"
    for p in pa:
        bh = p["x"].get("bai_hoc_cua_toi")
        if p["x"]["loai_bo"] or not bh or not bh.get("giu"):
            continue
        cg = next(c for c in CHUYEN_GIA if c["ma"] == p["x"]["ma"])
        try:
            ghi_bai(goc, ma, cg["ma"], {
                "luc": _luc(), "chuyen_gia": cg["ma"], "pham_vi": cg["pham_vi"], "kenh": ma, "ngach": _ngach(goc, ma),
                "video_id": nhan.get("video_id"), "moc": nhan.get("moc"), "khoa": bh["khoa"] or bh["cau"][:60],
                "cau": bh["cau"], "so_dan": bh["so_dan"], "bong": bong})
        except OSError:
            continue


def _luu(goc: str, ma: str, hd: Dict[str, Any], luu: bool) -> None:
    """`hoi-dong-cuoi.json` ({loai: phiên cuối}) cho bảng điều khiển + một dòng `hoi-dong.jsonl`."""
    if not (luu and goc):
        return
    tm = os.path.join(goc, "CHANNEL", ma, "giam-doc") if ma else os.path.join(goc, "workspace", "tong-giam-doc")
    try:
        cuoi = _doc_json(os.path.join(tm, TEP_CUOI), {}) or {}
        cuoi = cuoi if isinstance(cuoi, dict) else {}
        cuoi[hd["loai"]] = hd
        _ghi_json(os.path.join(tm, TEP_CUOI), cuoi)
        q = hd.get("quyet") or {}
        with io.open(os.path.join(tm, TEP_NHAT_KY), "a", encoding="utf-8", newline="\n") as tep:
            tep.write(json.dumps({"luc": hd["luc"], "loai": hd["loai"], "chon": q.get("chon"), "do_tin": q.get("do_tin"),
                                  "cong": hd.get("cong"), "n": hd.get("n"), "loi": hd.get("loi"),
                                  "loai_bo": [x["ma"] for x in hd["chuyen_gia"] if x.get("loai_bo")]},
                                 ensure_ascii=False) + "\n")
    except OSError:
        pass


# ── số liệu giám đốc kênh ──────────────────────────────────────────────────

def so_lieu_kenh(bs: Any, toi_da_video: int = 12) -> Dict[str, Any]:
    """{khoá nguồn: số} từ bảng số của kênh — khoá cùng kiểu khám nghiệm (`v:<id>/<mốc>/<trường>`)."""
    from .du_lieu import ctr_trang_chu, moi_nhat, trong_khoang  # noqa: PLC0415

    ra: Dict[str, Any] = {}

    def dat(k: str, x: Any) -> None:
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            ra[k] = round(float(x), 2) if isinstance(x, float) else x

    dat("kenh/nguong_thang_48h", bs.nguong_thang_48h)
    dat("kenh/ctr_trang_chu_muc_tieu", bs.ctr_muc_tieu)
    dat("kenh/phut_muc_tieu", getattr(bs, "phut_muc_tieu", None))
    for k in ("sub", "gio_xem"):
        dat("ypp/" + k, (bs.ypp or {}).get(k))
    mot = _dt.timedelta(days=7)
    for ten, tu, den in (("7d", bs.bay_gio - mot, bs.bay_gio), ("7d_truoc", bs.bay_gio - 2 * mot, bs.bay_gio - mot)):
        for k in ("hien_thi", "gio_xem", "sub", "xem"):
            try:
                dat("kenh/{0}/{1}".format(ten, k), trong_khoang(bs, k, tu, den))
            except Exception:  # noqa: BLE001
                pass
    for v in list(bs.video)[:toi_da_video]:
        b = moi_nhat(v) or {}
        nhan = "v:{0}/{1}".format(v["id"], b.get("moc", "?"))
        for k in ("hien_thi", "ctr", "avd_pct", "gx_1k", "pct_browse", "pct_de_xuat", "tuoi"):
            dat("{0}/{1}".format(nhan, k), b.get(k))
        tc = ctr_trang_chu(v) or {}
        dat("v:{0}/{1}/ctr_browse".format(v["id"], tc.get("moc", "?")), tc.get("ctr_browse"))
        dat("v:{0}/hien_thi_48h".format(v["id"]), v.get("hien_thi_48h"))
        dat("v:{0}/sub_1k_view".format(v["id"]), v.get("sub_1k"))
    return ra


# ── chọn content: 3 dòng ý kiến cho biên tập viên ─────────────────────────

def _dong_uv(i: int, d: Dict[str, Any]) -> str:
    so = ["{0} view".format(int(float(d.get("view") or 0)))]
    if d.get("tuoi_ngay") is not None:
        so.append("tuổi {0:.1f} ngày".format(float(d["tuoi_ngay"])))
    if d.get("da"):
        so.append("đà " + str(d["da"]) + (" +{0}/ngày".format(int(float(d.get("tang_ngay") or 0)))
                                          if d.get("da") == "dang_len" else ""))
    if d.get("dot_bien"):
        so.append("đột biến ×{0:.1f}".format(float(d["dot_bien"])))
    if d.get("ty_so_vuot"):
        so.append("×{0:.1f} trung vị kênh nguồn".format(float(d["ty_so_vuot"])))
    if d.get("cum"):
        so.append("cụm " + "/".join(d["cum"]))
    if d.get("khan_gia_cung_xem"):
        so.append("khán giả kênh mình đang xem")
    return "[U{0}] {1} — {2}".format(i, _gon(d.get("tieu_de"), 90), " · ".join(so))


def y_kien_ung_vien(goc: str, ma: str, uv: Sequence[Dict[str, Any]], goi_chat: Optional[Callable[..., str]], *,
                    boi_canh: Optional[Dict[str, str]] = None, ghi: Optional[Callable[[str], None]] = None,
                    toi_da: int = 8) -> str:
    """Mỗi chuyên gia MỘT dòng về các ứng viên top → khối cho biên tập viên. "" khi hội đồng tắt, kênh
    không bật giám đốc, không có AI, hoặc không ai trả lời (lời nhắc biên tập y hệt từng byte)."""
    if goi_chat is None or not uv or not bat(goc):
        return ""
    if str(_cai_kenh(goc, ma).get("giam_doc") or "tat").strip().lower() not in ("goi_y", "tu_ap"):
        return ""
    top = list(uv)[:toi_da]
    bang = "\n".join(_dong_uv(i, d) for i, d in enumerate(top, 1))
    h = hashlib.sha1(bang.encode("utf-8")).hexdigest()[:10]
    thang = _thang(goc, ma)
    dong, bien_ban = [], {}
    for cg in CHUYEN_GIA:
        ln = "\n\n".join([
            "Bạn là CHUYÊN GIA {0} của kênh YouTube {1}. MỤC TIÊU CỦA BẠN: {2}".format(cg["ten"], ma, cg["muc_tieu"]),
            "SỔ KINH NGHIỆM CỦA BẠN:\n" + ("\n".join(doc_so(goc, ma, cg["ma"])) or "(chưa có)"),
            "LÁT DỮ LIỆU CỦA BẠN\n" + (lat_du_lieu(goc, ma, cg["ma"], None, boi_canh) or "(không có)"),
            "ỨNG VIÊN TOP (biên tập viên sẽ tự chấm; bạn chỉ góp MỘT ý từ góc của bạn):\n" + bang,
            "Chỉ trả JSON: {\"y_kien\": \"1–2 câu có số: nên ưu tiên U?, nên tránh U? vì sao (từ góc của bạn)\"}",
        ])
        du, _t, mh, _l = _goi(goi_chat, ln, thang, "{0}:y-kien:{1}:{2}".format(ma, cg["ma"], h), TOI_DA_TOKEN_Y_KIEN,
                              lambda t: (_json(t) or {}).get("y_kien") or None, ghi, cg["ten"])
        if du:
            dong.append("- {0}: {1}".format(TEN[cg["ma"]], _gon(du, 320)))
            bien_ban[cg["ma"]] = {"y_kien": _gon(du, 320), "mo_hinh": mh}
    if not dong:
        return ""
    _luu(goc, ma, {"loai": "bien_tap", "luc": _luc(), "n": len(top), "chuyen_gia": [
        dict(v, ma=k, ten=TEN[k]) for k, v in bien_ban.items()], "quyet": {}, "cong": "", "ung_vien": bang}, True)
    if ghi:
        ghi("  [hội đồng] {0} ý kiến chuyên gia cho biên tập viên.".format(len(dong)))
    return ("Đội chuyên gia mỗi người góp MỘT ý về các ứng viên top (tham khảo — bạn vẫn tự chấm theo số và luật "
            "ở trên):\n" + "\n".join(dong))


# ── sổ độ chính xác + quyền tự áp ──────────────────────────────────────────

def _cong_ma(so_lieu: Dict[str, Any], moc: str, vid: str) -> Optional[str]:
    """Cổng hỏng theo SỐ (mã, không LLM): tỉ số với trung vị kênh cùng tuổi thấp nhất < 0,8 → cổng đó;
    mọi tỉ số ≥ 0,9 → "khong"; còn lại → None (không chấm)."""
    def ti(truong: str, ten_tv: str) -> Optional[float]:
        v = next((x for k, x in so_lieu.items() if k.startswith("v:{0}/".format(vid)) and k.endswith("/" + truong)
                  and isinstance(x, (int, float))), None)
        tv = so_lieu.get("kenh/tv@{0}/{1}".format(moc, ten_tv))
        return float(v) / float(tv) if isinstance(v, (int, float)) and isinstance(tv, (int, float)) and tv else None

    t = {"hien_thi": ti("hien_thi", "hien_thi"), "ctr": ti("ctr_browse", "ctr_browse") or ti("ctr", "ctr"),
         "giu_chan": ti("avd_pct", "avd_pct")}
    t = {k: x for k, x in t.items() if x is not None}
    if not t:
        return None
    thap = min(t, key=t.get)
    if t[thap] < 0.8:
        return thap
    return "khong" if all(x >= 0.9 for x in t.values()) else None


def do_chinh_xac(goc: str, ma: str, *, ghi: bool = True) -> Dict[str, Any]:
    """Tỉ lệ đúng theo loại quyết định, đọc từ sổ có sẵn → `giam-doc/do-chinh-xac.json` (kèm `quyen`)."""
    from .du_lieu import thu_muc_giam_doc  # noqa: PLC0415

    tm = thu_muc_giam_doc(goc, ma)
    mau: Dict[str, List[Tuple[bool, str]]] = {k: [] for k in LOAI_DO}
    for p in glob.glob(os.path.join(tm, "kham-nghiem", "*.json")):
        du = _doc_json(p, {}) or {}
        k = du.get("ket") or {}
        if k.get("cong_hong"):
            c = _cong_ma(((du.get("ho_so") or {}).get("so_lieu") or {}), str(du.get("moc")), str(du.get("video_id")))
            if c:
                mau["chan_doan_cong"].append((k["cong_hong"] == c, "{0}@{1}".format(du.get("video_id"), du.get("moc"))))
    for d in (_doc_json(os.path.join(tm, "du-doan.json"), {}) or {}).get("du_doan") or []:
        if isinstance(d, dict) and "dung" in d:
            mau["du_doan"].append((bool(d["dung"]), str(d.get("video_id"))))
    nhom: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for d in _doc_dong(os.path.join(tm, "bai-hoc.jsonl")):
        if d.get("truc") and d.get("video_id"):
            nhom.setdefault((str(d["truc"]), str(d.get("gia_tri") or ""), str(d.get("cum") or "")), []).append(d)
    for ds in nhom.values():
        ds.sort(key=lambda x: str(x.get("luc")))
        for d in ds[1:]:  # bài đầu là giả thuyết; video sau cùng hướng = bài đúng
            mau["bai_hoc"].append((d.get("huong") == ds[0].get("huong"), str(d.get("video_id"))))
    for t in (_doc_json(os.path.join(tm, "thi-nghiem.json"), {}) or {}).get("thi_nghiem") or []:
        if isinstance(t, dict) and t.get("trang_thai") in ("giu", "mo_rong", "bo", "quay_lui"):
            mau["doi_chuan"].append((t["trang_thai"] in ("giu", "mo_rong"), str(t.get("id"))))
    goc_ma = re.sub(r"[-_]v\d+$", "", ma, flags=re.IGNORECASE)
    for t in (_doc_json(os.path.join(goc, "workspace", "tong-giam-doc", "so.json"), {}) or {}).get("thay_doi") or []:
        if isinstance(t, dict) and t.get("ma") in (ma, goc_ma) and t.get("trang_thai") in ("giu", "quay_lui"):
            mau["chia_khe"].append((t["trang_thai"] == "giu", str(t.get("id"))))
    try:  # đợt 3 tự học: biên tập đoán thắng/trượt đúng không (ván `tu-hoc/van.json`) — để đo "trình độ" theo thời gian
        from .. import tu_hoc  # noqa: PLC0415

        for mg, v in tu_hoc.doc_van(goc, ma).items():
            if isinstance(v, dict) and "dung" in v:
                mau["du_doan_bien_tap"].append((bool(v["dung"]), str(mg)))
    except Exception:  # noqa: BLE001
        pass
    cu = (_doc_json(os.path.join(tm, TEP_DO_CHINH_XAC), {}) or {}).get("loai") or {}
    loai = {}
    for k, xs in mau.items():
        n, dung = len(xs), sum(1 for x in xs if x[0])
        tl = round(dung / n, 2) if n else None
        q_cu = (cu.get(k) or {}).get("quyen") if isinstance(cu.get(k), dict) else None
        if n >= TU_AP_N and tl is not None and tl >= TU_AP_TI_LE:
            q = "tu_ap"
        elif q_cu == "tu_ap" and tl is not None and tl >= LUI_TI_LE:
            q = "tu_ap"  # đã có quyền: chỉ lùi khi tụt dưới 55%
        else:
            q = "goi_y"
        loai[k] = {"ten": LOAI_DO[k], "n": n, "dung": dung, "ti_le": tl, "quyen": q,
                   "sai_gan_day": [x[1] for x in xs if not x[0]][-5:]}
    ra = {"kenh": ma, "luc": _luc(), "luat": "tu_ap khi ≥ {0:.0%} đúng trên n ≥ {1}; tụt < {2:.0%} → goi_y".format(
        TU_AP_TI_LE, TU_AP_N, LUI_TI_LE), "loai": loai}
    if ghi:
        try:
            _ghi_json(os.path.join(tm, TEP_DO_CHINH_XAC), ra)
        except OSError:
            pass
    return ra


def quyen(goc: str, ma: str, loai: str) -> str:
    """"tu_ap" | "goi_y" cho một loại quyết định của kênh (`ma` rỗng = công ty: chia khe gộp mọi kênh)."""
    if not ma:
        xs = [t for t in (_doc_json(os.path.join(goc, "workspace", "tong-giam-doc", "so.json"), {}) or {}).get(
            "thay_doi") or [] if isinstance(t, dict) and t.get("trang_thai") in ("giu", "quay_lui")]
        n = len(xs)
        return "tu_ap" if n >= TU_AP_N and sum(1 for t in xs if t["trang_thai"] == "giu") / n >= TU_AP_TI_LE else "goi_y"
    return str(((do_chinh_xac(goc, ma, ghi=False).get("loai") or {}).get(loai) or {}).get("quyen") or "goi_y")


def la_quyet_lon(d: Dict[str, Any]) -> bool:
    """Đổi chiến lược lớn (khoá chien_luoc / tự học / công thức chọn) — chỉ chủ duyệt."""
    return d.get("loai") == "tham_so" and str(d.get("khoa") or "") in KHOA_LON


def in_bien_ban(h: Dict[str, Any]) -> str:
    """Biên bản một phiên hội đồng cho người đọc (CLI / tệp mẫu)."""
    if not h:
        return "(không có phiên hội đồng — hội đồng tắt hoặc không gọi AI)"
    ra = ["=== HỘI ĐỒNG: {0} · kênh {1} · {2} · n={3} ===".format(h.get("loai"), h.get("ma") or "(công ty)",
                                                               h.get("luc"), h.get("n"))]
    for x in h.get("chuyen_gia") or []:
        ra.append("\n--- Chuyên gia {0} ({1}){2}".format(x.get("ten"), x.get("mo_hinh") or "—",
                                                       " — LOẠI: " + str(x.get("ly_do_loai")) if x.get("loai_bo") else ""))
        if x.get("phuong_an"):
            ra.append("phương án: " + str(x["phuong_an"]))
        for d in x.get("luan_diem") or []:
            ra.append("  • {0}{1}".format(d["cau"], "" if d.get("giu") else "  [LOẠI — số bịa: {0}]".format(
                ", ".join("{0}={1} (thật {2})".format(b["nguon"], b["so"], b["that"]) for b in d.get("so_bia") or []))))
        if "so_khop" in x:
            ra.append("  kiểm số: {0} số khớp nguồn · {1} số bịa · số không thấy trong dữ liệu: {2}".format(
                x["so_khop"], len(x.get("so_bia") or []), ", ".join(x.get("so_khong_nguon") or []) or "không"))
        if x.get("bai_hoc_cua_toi"):
            b = x["bai_hoc_cua_toi"]
            ra.append("  bài học cho sổ mình: {0}{1}".format(b.get("cau"), "" if b.get("giu") else " [không ghi]"))
        if x.get("y_kien"):
            ra.append("  ý kiến: " + str(x["y_kien"]))
    pb = h.get("phan_bien") or {}
    if pb:
        ra.append("\n--- PHẢN BIỆN ({0}){1}".format(pb.get("mo_hinh") or "—", " — " + pb["loi"] if pb.get("loi") else ""))
        for k, y in (pb.get("y_kien") or {}).items():
            ra.append("  {0} [{1}]: ngược: {2} · giải thích khác: {3}{4}".format(
                TEN.get(k, k), y.get("muc") or "?", y.get("nguoc") or "—", y.get("giai_thich_khac") or "—",
                " · số bịa {0}".format(len(y["so_bia"])) if y.get("so_bia") else ""))
    q = h.get("quyet") or {}
    if q:
        ra.append("\n--- QUYẾT ĐỊNH ({0}): chọn {1} · điểm {2} · độ tin LLM {3} → độ tin {4} (phản biện {5}, đồng thuận "
                  "+{6}{7})".format(q.get("mo_hinh") or "—", q.get("ten"), json.dumps(q.get("diem"), ensure_ascii=False),
                                    q.get("do_tin_llm"), q.get("do_tin"), q.get("phan_bien") or "?", q.get("dong_thuan"),
                                    ", TRÁI TRI THỨC" if q.get("trai_tri_thuc") else ""))
        ra.append("lý do: " + str(q.get("ly_do") or ""))
        ra.append("CỔNG: {0} (ngưỡng {1}{2})".format(h.get("cong"), h.get("nguong"), "; cắt {0} thay đổi".format(
            h["cat_boi_cong"]) if h.get("cat_boi_cong") else ""))
    if h.get("loi"):
        ra.append("lỗi: " + str(h["loi"]))
    return "\n".join(ra)
