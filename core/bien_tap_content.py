"""**Biên tập viên AI** — một lượt gọi mô hình MẠNH NHẤT đọc ĐỦ BỐI CẢNH rồi xếp hạng
nguồn remake theo Ý NGHĨA, không theo từ khoá.

═══ VÌ SAO CÓ MODULE NÀY (29/09/2026) ═══

Chủ dự án: *"Với remake, cái quyết định video nổ view + kênh bật kiếm tiền là CHỌN CONTENT
ĐÚNG."* … *"Đừng tiếc token ShopAPI. Lọc theo từ khoá là SAI — phải theo Ý NGHĨA, suy nghĩ."*

Ba công thức chọn nguồn (`cong_thuc_v7`, `cong_thuc_vph`, bảng "Một nút") chấm bằng SỐ và TỪ
KHOÁ: đột biến, VPH, cụm từ khoá, tỉ số vượt kênh. Chúng trả lời tốt câu *"video nguồn nào
đang nổ"*, nhưng không trả lời được câu *"nó nổ VÌ SAO, và cái 'vì sao' ấy có chuyển được sang
khán giả Nhật 55+ của kênh MÌNH không, có trùng ý thứ cả nhóm đã làm không"*. Câu đó cần ĐỌC
HIỂU: lời hứa của tiêu đề, cảm xúc nó chạm, tệp nó kéo — và đọc cả lời thoại.

Module này là lớp đọc hiểu ấy, đứng SAU công thức: nhận top ứng viên công thức đã xếp, đưa
cho mô hình mạnh nhất ĐỦ bối cảnh một lần (định vị kênh, khán giả thật, video đã thắng/trượt
kèm số, bài học, xu hướng, cái cả nhóm đã làm, lời thoại từng nguồn) rồi nhận về thứ tự + lý
do + dự đoán CTR/giữ chân.

═══ HỢP ĐỒNG VỚI ĐIỂM MÓC (`core/tu_chay.py`, agent khác viết) ═══

    chon(goc, ma_kenh, ung_vien_top, goi_chat, *, so_chon=3)
      -> {"thu_tu": [link…], "ly_do": {link: "…"}, "du_doan": {link: {"ctr", "vi_sao_no",
          "rui_ro", …}}, "loai": {link: "…"}, "nhan_dinh": "…", "tep": "<đường tệp quyết định>"}
      -> None khi không có gì để nói (goi_chat None, ứng viên rỗng, mọi lượt gọi hỏng, JSON
         không đọc được, AI loại hết). `None` = điểm móc GIỮ NGUYÊN thứ tự công thức.

KHÔNG BAO GIỜ ném lỗi ra ngoài: lớp này là một cải thiện xác suất, không phải điều kiện để
sản xuất (cùng nết `core.kiem_trung_y`). Không import Qt.

`goi_chat` là hàm chữ của `tu_chay._dung_goi_chat_mac_dinh`:
`goi(loi_nhac, mo_hinh=…, khoa=…, toi_da_token=…) -> str` — bài kiểm truyền hàm giả.

═══ MÔ HÌNH ═══

`GET /v1/models` của ShopAPI (đo 29/09/2026) liệt kê `claude-sonnet-5`, `claude-opus-5`,
`claude-fable-5` — CÙNG GIÁ (3.500 µVND/token vào, 17.500 µVND/token ra). Fable là bậc mạnh
nhất (`core/viet_max.THANG_MO_HINH`), nên bước này mặc định Fable, lùi Opus rồi Sonnet khi
lượt gọi hỏng. `kenh.yaml: mo_hinh_bien_tap` đặt được mô hình khác (đứng đầu thang).

Một lượt ~20–30k token vào + ~1–2k token ra ≈ 100–150 đồng. Cái đắt là THỜI GIAN: nguồn LLM
chạy 2–8 token/giây ban ngày (`goi_van_ban.han_cho_theo_token`), nên đầu ra được giữ GỌN
(số thứ tự ứng viên thay cho link, chi tiết chỉ cho nhóm được chọn).

═══ HỌC TỪ CHÍNH MÌNH ═══

Mỗi quyết định ghi `CHANNEL/<k>/nghien-cuu/bien-tap/<ngày>-<giờphút>.json`. `danh_gia_lai`
nối nguồn đã sản xuất → gói → số Studio 48–72h (hồ sơ video), so với dự đoán, ghi
`bien-tap/danh-gia.json` + `bien-tap/BAI-HOC-BIEN-TAP.md`; lần chọn sau đọc lại mấy dòng đó
("các lần tao dự đoán sai vì…"). `chon` tự gọi `danh_gia_lai` trước mỗi lượt (không mạng —
chỉ gọi AI để rút "vì sao sai" khi có ca MỚI chấm được).
"""

from __future__ import annotations

import csv
import datetime as _dt
import glob
import hashlib
import io
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "THANG_MO_HINH", "SO_UNG_VIEN_TOI_DA", "THU_MUC", "TEP_DANH_GIA", "TEP_BAI_HOC",
    "dang_bat", "thang_mo_hinh", "chon", "dung_boi_canh", "dung_loi_nhac", "doc_ket_qua",
    "danh_gia_lai", "doc_bai_hoc_bien_tap",
]

#: Thang mô hình — mạnh nhất trước (xem docstring đầu tệp, mục MÔ HÌNH).
THANG_MO_HINH: Tuple[str, ...] = ("claude-fable-5", "claude-opus-5", "claude-sonnet-5")
#: Số lượt gọi tối đa cho MỘT lần chọn (mỗi lượt một bậc thang). Hai là đủ: bậc ba chỉ kéo
#: dài lượt chọn nguồn thêm vài phút mà xác suất cứu được đã rất thấp.
SO_LUOT_GOI_TOI_DA = 3  # 30/09/2026: 2 → 3 — cổng chất lượng cần phán quyết, thà chậm vài phút.
#: Đưa tối đa ngần này ứng viên cho biên tập viên đọc MỘT lượt (một "cửa sổ"). 30/09/2026: 12 → 20
#: — kiểm toán TL2 thấy 12 dòng đầu bảng VPH có 5 dòng sức khoẻ/ăn uống シニア (lệch ngách), biên
#: tập viên chỉ còn 7 dòng để chọn 3. Không đủ nguồn TỐT thì `chon_cua_so` mở cửa sổ kế.
SO_UNG_VIEN_TOI_DA = 20
#: Trần token đầu ra — nhận định + 3 ca chi tiết + chấm TỪNG ứng viên + thứ tự còn lại + loại.
TOI_DA_TOKEN = 7000
#: Hạng chất lượng biên tập viên chấm cho TỪNG ứng viên (30/09/2026, cổng chất lượng nguồn).
TOT, TAM, TE = "TOT", "TAM", "TE"
#: Không có nguồn TỐT nào sau mọi cửa sổ thì chỉ nhận nguồn TẠM có điểm biên tập từ đây trở lên.
NGUONG_TAM_DUNG = 65
#: Số cửa sổ tối đa một lần chọn (mỗi cửa sổ một lượt gọi mô hình mạnh).
SO_CUA_SO_TOI_DA = 3
#: Phán quyết từng ứng viên được nhớ ngần này giờ (`bien-tap/nho-cham.json`) — vòng giữ nguồn gọi
#: `_chon_nguon` tới 3 lần, và mỗi lượt sản xuất chỉ lấy một nguồn: không chấm lại cùng ứng viên.
NHO_CHAM_GIO = 18
TEP_NHO_CHAM = "nho-cham.json"
#: Tệp INSIGHT sống của nhóm (`CHANNEL/_NHOM/<nhóm>/…`) — bài học chọn content có số, người/agent sửa.
TEP_INSIGHT = "INSIGHT-CHON-CONTENT.md"

THU_MUC = "bien-tap"
TEP_DANH_GIA = "danh-gia.json"
TEP_BAI_HOC = "BAI-HOC-BIEN-TAP.md"

#: Ngưỡng kết cục @48h (hiển thị) — chép từ `CHANNEL/TL4-T7/CONG-THUC-V7.md` mục 5.
NGUONG_THANG_48H = 20000
NGUONG_TRUOT_48H = 6000

#: Điểm giống CHỮ (`trung_tieu_de.diem_giong_tieu_de`) từ đây trở lên thì cắm cờ "gần giống
#: thứ nhóm đã làm" lên ứng viên — KHÔNG loại (0,80 mới là ngưỡng loại của `trung_tieu_de`); cờ
#: chỉ để mô hình tự đọc nghĩa mà phán, vì ca "cùng ý khác chữ" nằm ngay dưới 0,80.
NGUONG_GAN_GIONG = 0.45

#: Lời thoại trích cho MỖI ứng viên: đầu + giữa + cuối (ký tự). Mô hình mạnh đọc trích đoạn
#: dài tốt hơn một bản tóm tắt do mô hình yếu viết hộ; đầu vào rẻ, đầu ra mới chậm.
_TRICH_DAU, _TRICH_GIUA, _TRICH_CUOI = 1300, 700, 450


# ── tiện ích đọc đĩa — mọi hàm ở đây nuốt lỗi, trả rỗng ──────────────────────────


def _ghi_log(ghi: Optional[Callable[[str], None]], dong: str) -> None:
    if ghi is not None:
        try:
            ghi(dong)
        except Exception:  # noqa: BLE001
            pass


def _doc_chu(duong: str, toi_da: int = 0) -> str:
    try:
        with io.open(duong, encoding="utf-8-sig") as tep:
            chu = tep.read()
    except (OSError, UnicodeDecodeError):
        return ""
    return chu[:toi_da] if toi_da else chu


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError, UnicodeDecodeError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = "{0}.{1}.tmp".format(duong, os.getpid())
    with io.open(tam, "w", encoding="utf-8") as tep:
        tep.write(json.dumps(du, ensure_ascii=False, indent=1))
    os.replace(tam, duong)


def _ghi_chu_tep(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = "{0}.{1}.tmp".format(duong, os.getpid())
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)
    os.replace(tam, duong)


def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with io.open(duong, encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _duong_kenh(goc: str, ma_kenh: str = "") -> str:
    from .kenh import duong_kenh  # noqa: PLC0415

    return duong_kenh(goc, ma_kenh)


def _nghien_cuu(goc: str, ma_kenh: str) -> str:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    return thu_muc_nghien_cuu(goc, ma_kenh)


def _yaml_kenh(goc: str, ma_kenh: str) -> Dict[str, Any]:
    try:
        from .kenh import TEP_KENH, doc_yaml  # noqa: PLC0415

        return doc_yaml(os.path.join(_duong_kenh(goc, ma_kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        return {}


def _ma_video(link: str) -> str:
    try:
        from .doi_thu_kenh import ma_video  # noqa: PLC0415

        return ma_video(str(link or "")) or ""
    except Exception:  # noqa: BLE001
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", str(link or ""))
        return m.group(1) if m else ""


def _so(x: Any) -> float:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _gon(chu: Any, toi_da: int = 0) -> str:
    s = " ".join(str(chu or "").split())
    return s[:toi_da] if toi_da and len(s) > toi_da else s


def _ngan_so(n: float) -> str:
    return "{0:,.0f}".format(n).replace(",", ".") if n else "?"


# ── cấu hình ──────────────────────────────────────────────────────────────────


def dang_bat(goc: str, ma_kenh: str) -> bool:
    """`kenh.yaml: bien_tap_ai` (mặc định BẬT). Điểm móc hỏi hàm này trước khi gọi `chon`."""
    gt = _yaml_kenh(goc, ma_kenh).get("bien_tap_ai")
    if gt is None:
        return True
    return str(gt).strip().lower() not in ("false", "0", "no", "off", "tat", "tắt")


def thang_mo_hinh(goc: str, ma_kenh: str) -> List[str]:
    """Thang mô hình cho kênh: `mo_hinh_bien_tap` (nếu khai) đứng đầu, rồi `THANG_MO_HINH`."""
    rieng = str(_yaml_kenh(goc, ma_kenh).get("mo_hinh_bien_tap") or "").strip()
    ra = [rieng] if rieng else []
    ra += [m for m in THANG_MO_HINH if m not in ra]
    return ra


# ── ứng viên: chuẩn hoá + làm giàu từ sổ ──────────────────────────────────────


def _lay(o: Any, khoa: str, mac_dinh: Any = "") -> Any:
    if isinstance(o, dict):
        return o.get(khoa, mac_dinh)
    return getattr(o, khoa, mac_dinh)


def _chuan_hoa_ung_vien(ung_vien_top: Sequence[Any]) -> List[Dict[str, Any]]:
    """Mọi khuôn dòng của ba công thức (dict của `tu_chay.ung_vien_xep_hang`, hay đối tượng
    `UngVien` của V7) → dict chung. Bỏ dòng không có link/mã, khử trùng theo mã."""
    ra: List[Dict[str, Any]] = []
    thay = set()
    for i, d in enumerate(ung_vien_top or []):
        link = str(_lay(d, "link") or "").strip()
        ma = str(_lay(d, "ma") or "").strip() or _ma_video(link)
        if not link and ma:
            link = "https://www.youtube.com/watch?v=" + ma
        if not link or not ma or ma in thay:
            continue
        thay.add(ma)
        ly = _lay(d, "ly_do", []) or []
        ra.append({
            "hang_cong_thuc": i + 1, "link": link, "ma": ma,
            "tieu_de": str(_lay(d, "tieu_de") or ""), "kenh": str(_lay(d, "kenh") or ""),
            "nguon": str(_lay(d, "nguon") or ""), "diem": _lay(d, "diem", ""),
            "loai": str(_lay(d, "loai") or ""), "view": _so(_lay(d, "view", 0)),
            "vph": _so(_lay(d, "vph", 0)), "dot_bien": _so(_lay(d, "dot_bien", 0)),
            "tuoi_gio": _so(_lay(d, "tuoi_gio", 0)),
            "cum": [str(c) for c in (_lay(d, "cum", []) or [])],
            "ly_do_cong_thuc": [str(x) for x in ly] if isinstance(ly, (list, tuple)) else [str(ly)],
            "anh_em": _lay(d, "anh_em", None),
        })
    return ra


def _chi_muc_content(goc: str, ma_kenh: str) -> Dict[str, Dict[str, str]]:
    """`{mã video: dòng content.csv}` — sổ đối thủ của kênh (kênh nhóm vẫn giữ sổ riêng)."""
    ra: Dict[str, Dict[str, str]] = {}
    for d in _doc_csv(os.path.join(_nghien_cuu(goc, ma_kenh), "content.csv")):
        ma = _ma_video(d.get("Link video") or "")
        if ma:
            ra[ma] = d
    return ra


def _chi_muc_danh_ba(goc: str, ma_kenh: str) -> Dict[str, Dict[str, str]]:
    """`{tên kênh: dòng doi-thu.csv}` — cỡ kênh nguồn (subs, view trung vị, số video)."""
    return {str(d.get("Kênh") or "").strip(): d
            for d in _doc_csv(os.path.join(_nghien_cuu(goc, ma_kenh), "doi-thu.csv"))
            if str(d.get("Kênh") or "").strip()}


def _trich_loi_thoai(chu: str) -> str:
    chu = _gon(chu)
    n = len(chu)
    if n <= _TRICH_DAU + _TRICH_GIUA + _TRICH_CUOI + 200:
        return chu
    giua = int(n * 0.45)
    cuoi = int(n * 0.8)
    return (chu[:_TRICH_DAU] + " …(lược)… " + chu[giua:giua + _TRICH_GIUA]
            + " …(lược)… " + chu[cuoi:cuoi + _TRICH_CUOI])


def _noi_dung(goc: str, ma_kenh: str, ma: str, dong_content: Dict[str, str]) -> Tuple[str, str]:
    """(nhãn, nội dung): lời thoại trích từ kho nhóm nếu có, không thì mô tả video."""
    try:
        from . import loi_thoai  # noqa: PLC0415

        bg = loi_thoai.doc(goc, ma_kenh, ma) or {}
    except Exception:  # noqa: BLE001
        bg = {}
    chu = str(bg.get("text") or "") if not bg.get("khong_co") else ""
    if len(chu.strip()) >= 300:
        return "LỜI THOẠI (trích đầu–giữa–cuối, {0} ký tự gốc)".format(len(chu)), _trich_loi_thoai(chu)
    mo_ta = _gon(dong_content.get("Mô tả"), 900)
    tag = _gon(dong_content.get("Hashtag"), 200)
    if mo_ta or tag:
        return "MÔ TẢ VIDEO (chưa có lời thoại trong kho)", (mo_ta + (" · tag: " + tag if tag else ""))
    return "NỘI DUNG", "(chưa có lời thoại, chưa có mô tả — chỉ đọc được tiêu đề)"


def _tuoi_ngay(ngay: str, bay_gio: _dt.datetime) -> Optional[float]:
    try:
        d = _dt.datetime.strptime(str(ngay)[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return max(0.0, (bay_gio - d).total_seconds() / 86400.0)


def _tieu_de_nhom_da_co(goc: str, ma_kenh: str) -> List[Tuple[str, str]]:
    """`[(tiêu đề, nơi)]` mọi video cả nhóm ĐÃ LÀM/ĐÃ ĐĂNG — để cắm cờ "gần giống" cho ứng viên.

    Hai nguồn, vì mỗi nguồn sót một kiểu: `tieu_de_da_lam_ca_nhom` (lượt AUTO, kế hoạch) không
    thấy video làm TAY / ở dự án khác (V13 TL4 remake `GXNctv0oVSM` qua `TL4-T7-v2`), còn
    `bang-nhom.csv` (Studio) thấy mọi video đã đăng của nhóm."""
    ra: List[Tuple[str, str]] = []
    try:
        from . import nhom_kenh  # noqa: PLC0415

        ra += [(t, m) for t, m in nhom_kenh.tieu_de_da_lam_ca_nhom(goc, ma_kenh)]
        nhom = nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
        if nhom:
            for h in _doc_csv(os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), "bang-nhom.csv")):
                if h.get("Tiêu đề"):
                    ra.append((str(h["Tiêu đề"]), "{0} đã đăng · {1} hiển thị".format(
                        h.get("Kênh") or "?", _ngan_so(_so(h.get("Lượt hiển thị"))))))
    except Exception:  # noqa: BLE001
        pass
    return ra


def _gan_giong(tieu_de: str, da_co: Sequence[Tuple[str, str]]) -> Tuple[float, str, str]:
    try:
        from .trung_tieu_de import diem_giong_tieu_de  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return 0.0, "", ""
    tot = (0.0, "", "")
    for t, m in da_co:
        try:
            s = diem_giong_tieu_de(tieu_de, t)
        except Exception:  # noqa: BLE001
            continue
        if s > tot[0]:
            tot = (s, t, m)
    return tot


#: ĐÀ TĂNG lúc chọn là thước số 1 (`workspace/CON-DUONG-TL4.md` mục 2.4: V10 nguồn 32k nhưng +7.213/ngày → nổ;
#: nguồn 330k đà 0 → bỏ). Video quá ngần này ngày mà đà ≈ 0 qua hai lượt quét = NGUỘI (máy đã thôi phát).
NGAY_XET_NGUOI = 7
#: "Nguồn nổ thật" (CONG-THUC-V7 cửa 5, CON-DUONG-TL4 2.3): TỐT cần ≥ ×3 view trung vị kênh nguồn HOẶC đột biến
#: cùng tuổi ≥ ×3 — không thì máy hạ xuống TẠM dù AI chấm TỐT (chạy khô 30/09: AI chấm TỐT nguồn ×1,7 / ×2,4).
NGUONG_NO_THAT = 3.0
#: Nguồn ngắn hơn ngần này phút thì không TỐT (khuôn 12–21 phút; nguồn 9 phút phải khai triển gấp đôi).
PHUT_NGUON_TOI_THIEU = 11


def _phut_chu(t: str) -> Optional[float]:
    phan = str(t or "").strip().split(":")
    if not phan or not all(p.isdigit() for p in phan):
        return None
    giay = 0
    for p in phan:
        giay = giay * 60 + int(p)
    return giay / 60.0


def _phan_da(tang_ngay: float, view_truoc: float, tuoi_ngay: Optional[float]) -> str:
    """"dang_len" (Tăng/ngày > 0) · "nguoi" (đã có ≥ 2 lượt quét, Tăng/ngày ≈ 0, > `NGAY_XET_NGUOI` ngày
    tuổi) · "chua_do" (mới một lượt quét, hoặc video còn quá trẻ để gọi là nguội)."""
    if tang_ngay and tang_ngay > 0:
        return "dang_len"
    if view_truoc and view_truoc > 0 and (tuoi_ngay is None or tuoi_ngay > NGAY_XET_NGUOI):
        return "nguoi"
    return "chua_do"


def _lam_giau(goc: str, ma_kenh: str, uv: List[Dict[str, Any]], bay_gio: _dt.datetime,
              khan_gia_xem: set) -> None:
    """Đắp số từ sổ vào từng ứng viên (tại chỗ): ngày đăng, tuổi, dài, view, tăng/ngày, cỡ
    kênh nguồn, tỉ số đột biến so view trung vị kênh, tuyến/chủ đề, nội dung, cờ gần giống."""
    content = _chi_muc_content(goc, ma_kenh)
    danh_ba = _chi_muc_danh_ba(goc, ma_kenh)
    da_co = _tieu_de_nhom_da_co(goc, ma_kenh)
    for d in uv:
        c = content.get(d["ma"], {})
        d["tieu_de"] = d["tieu_de"] or str(c.get("Tiêu đề video") or "")
        d["kenh"] = d["kenh"] or str(c.get("Kênh") or "")
        d["ngay_dang"] = str(c.get("Ngày đăng") or "")[:10]
        tuoi = _tuoi_ngay(d["ngay_dang"], bay_gio) if d["ngay_dang"] else None
        if tuoi is None and d.get("tuoi_gio"):
            tuoi = d["tuoi_gio"] / 24.0
        d["tuoi_ngay"] = tuoi
        d["dai"] = str(c.get("Thời lượng") or "")
        d["view"] = d["view"] or _so(c.get("View"))
        d["tang_ngay"] = _so(c.get("Tăng/ngày"))
        d["view_truoc"] = _so(c.get("View lần trước"))
        d["da"] = _phan_da(d["tang_ngay"], d["view_truoc"], tuoi)
        d["tuyen"] = str(c.get("Tuyến / Kênh") or "")
        d["chu_de"] = str(c.get("Chủ đề") or "")
        d["tieu_de_viet"] = str(c.get("Tiêu đề (Việt)") or "")
        k = danh_ba.get(d["kenh"].strip(), {})
        d["subs_kenh"] = _so(k.get("Subs"))
        d["view_tv_kenh"] = _so(k.get("View TV"))
        d["so_video_kenh"] = str(k.get("Số video") or "")
        d["ghi_chu_kenh"] = _gon(k.get("Ghi chú"), 120)
        d["ty_so_vuot"] = (d["view"] / d["view_tv_kenh"]) if d["view"] and d["view_tv_kenh"] else 0.0
        d["khan_gia_cung_xem"] = d["ma"] in khan_gia_xem
        d["nhan_noi_dung"], d["noi_dung"] = _noi_dung(goc, ma_kenh, d["ma"], c)
        s, t, m = _gan_giong(d["tieu_de"], da_co) if d["tieu_de"] else (0.0, "", "")
        d["gan_giong"] = ({"diem": round(s, 2), "tieu_de": t, "noi": m} if s >= NGUONG_GAN_GIONG else None)


# ── bối cảnh kênh ─────────────────────────────────────────────────────────────


def _dinh_vi(goc: str, ma_kenh: str) -> str:
    y = _yaml_kenh(goc, ma_kenh)
    dong = ["Mã kênh: {0} · tên: {1}".format(ma_kenh, _gon(y.get("ten")) or "?"),
            "Tiếng: {0} · độ dài nhắm {1} phút · chế độ tiêu đề: {2} · nhãn tiêu đề: {3}".format(
                y.get("ngon_ngu") or "?", y.get("phut_muc_tieu") or "?",
                y.get("che_do_tieu_de") or "?", y.get("nhan_tieu_de") or "—")]
    if y.get("nhom"):
        dong.append("Thuộc nhóm “{0}” (mỗi kênh trong nhóm đánh MỘT tệp khán giả riêng).".format(y.get("nhom")))
    # Tệp khán giả đang đánh — dòng "đang đánh" của tuyen.csv.
    for d in _doc_csv(os.path.join(_nghien_cuu(goc, ma_kenh), "tuyen.csv")):
        if str(d.get("Trạng thái") or "").strip() != "đang đánh":
            continue
        dong.append("TỆP ĐANG ĐÁNH: {0} ({1})".format(d.get("Tên tuyến") or "?", d.get("Mã") or "?"))
        for nhan, cot, n in (("Insight (họ thầm nghĩ khi bấm)", "Insight", 300),
                             ("Lúc bấm họ đang", "Lúc bấm họ đang", 120), ("Họ cần", "Họ cần", 200),
                             ("Chân dung", "Mô tả", 700), ("Cửa vào + phân xử", "Từ khoá nhận biết", 1100)):
            if str(d.get(cot) or "").strip():
                dong.append("  {0}: {1}".format(nhan, _gon(d.get(cot), n)))
    # Hồ sơ ngách của nhóm (Đợt 4).
    try:
        from . import ho_so_ngach  # noqa: PLC0415

        hs = ho_so_ngach.doc_ngach(goc, ma_kenh)
        if hs.co():
            if hs.mo_ta_ngach:
                dong.append("Ngách của nhóm: " + hs.mo_ta_ngach)
            if hs.dang_thang:
                dong.append("Dạng đang thắng của ngách: " + hs.dang_thang)
            tho = ho_so_ngach.doc_ngach_tho(goc, hs.nhom) or {}
            if str(tho.get("mo_ta_cho_loc_ai") or "").strip():
                dong.append("Ngách theo nghĩa: " + _gon(tho.get("mo_ta_cho_loc_ai"), 900))
    except Exception:  # noqa: BLE001
        pass
    so_tay = _doc_chu(os.path.join(_duong_kenh(goc, ma_kenh), "CLAUDE.md"), 1800)
    if so_tay.strip():
        dong.append("Sổ tay kênh (đầu CLAUDE.md):\n" + so_tay.strip())
    return "\n".join(dong)


def _tong_quan_kenh_moi_nhat(goc: str, ma_kenh: str) -> Tuple[str, Dict[str, Any]]:
    """(ngày, tong-quan.json cấp kênh) bản mới nhất CÓ số tuổi — rỗng nếu chưa có."""
    thu_muc = os.path.join(_duong_kenh(goc, ma_kenh), "chi-so", "kenh")
    try:
        ten = sorted((t for t in os.listdir(thu_muc) if t.startswith("kenh-")), reverse=True)
    except OSError:
        return "", {}
    for t in ten:
        du = _doc_json(os.path.join(thu_muc, t, "tong-quan.json"))
        if isinstance(du, dict) and (du.get("tuoi") or du.get("thiet_bi")):
            return t[5:], du
    return "", {}


def _mo_ta_khan_gia(du: Dict[str, Any], quoc_gia: str = "JP") -> str:
    """`quoc_gia` (B5, 30/09/2026): tỉ lệ view của thị trường kênh nhắm — mặc định JP như trước."""
    quoc_gia = str(quoc_gia or "JP").strip().upper() or "JP"
    phan = []
    tuoi = du.get("tuoi") or {}
    if tuoi:
        def _nhan_tuoi(k: str) -> str:
            k2 = k.replace("AGE_", "")
            return k2.rstrip("_") + "+" if k2.endswith("_") else k2.replace("_", "–")
        phan.append("tuổi " + ", ".join("{0} {1:.0f}%".format(_nhan_tuoi(k), _so(v)) for k, v in tuoi.items()))
    tg = du.get("tuoi_gioi") or {}
    if tg:
        nu = sum(_so(v) for k, v in tg.items() if k.endswith("FEMALE"))
        phan.append("nữ {0:.0f}%".format(nu))
    tb = du.get("thiet_bi") or {}
    if tb:
        phan.append("thiết bị " + ", ".join("{0} {1:.0f}%".format(k, _so(v)) for k, v in tb.items()))
    vung = du.get("vung") or {}
    if vung:
        phan.append("{0} {1:.0f}%".format(quoc_gia, _so(vung.get(quoc_gia))))
    tr = du.get("traffic_chuan") or du.get("traffic") or {}
    if tr:
        phan.append("nguồn view: trang chủ {0:.0f}% · đề xuất {1:.0f}% · tìm kiếm {2:.1f}%".format(
            _so(tr.get("browse")), _so(tr.get("related")), _so(tr.get("search"))))
    if du.get("subs") or du.get("watch_hours"):
        phan.append("28 ngày: {0} sub · {1:.0f} giờ xem · CTR kênh {2}%".format(
            du.get("subs") or "?", _so(du.get("watch_hours")), du.get("ctr") or "?"))
    return " · ".join(phan)


def _quoc_gia(goc: str, ma_kenh: str) -> str:
    """Thị trường kênh nhắm: kenh.yaml > ngach.yaml `thi_truong` > "JP" (`NguCanh.thi_truong`)."""
    try:
        from .chien_luoc import ngu_canh  # noqa: PLC0415

        return str(ngu_canh.dung(goc, ma_kenh, co_v7=False).thi_truong.get("quoc_gia") or "JP")
    except Exception:  # noqa: BLE001
        return "JP"


def _khan_gia(goc: str, ma_kenh: str) -> str:
    dong = []
    ngay, du = _tong_quan_kenh_moi_nhat(goc, ma_kenh)
    qg = _quoc_gia(goc, ma_kenh)
    if du:
        dong.append("Kênh mình ({0}): {1}".format(ngay, _mo_ta_khan_gia(du, qg)))
    else:
        dong.append("Kênh mình: chưa có số khán giả Studio.")
    # Kênh non chưa đủ số → mượn khán giả của kênh anh em lớn nhất (cùng ngách, cùng máy phân phối).
    try:
        from . import nhom_kenh  # noqa: PLC0415

        tot = None
        for ma in nhom_kenh.thanh_vien(goc, ma_kenh):
            if ma == ma_kenh:
                continue
            n2, d2 = _tong_quan_kenh_moi_nhat(goc, ma)
            if d2 and (tot is None or _so(d2.get("views")) > _so(tot[2].get("views"))):
                tot = (ma, n2, d2)
        if tot is not None and (not du or _so(du.get("views")) < 20000):
            dong.append("Kênh anh em lớn nhất trong nhóm {0} ({1}) — đây là khán giả YouTube ĐANG phát "
                        "ngách này tới: {2}".format(tot[0], tot[1], _mo_ta_khan_gia(tot[2], qg)))
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(dong)


def _ctr_browse(goc: str, ma_kenh: str, video_id: str) -> Optional[float]:
    if not video_id:
        return None
    try:
        from .bai_hoc_san_xuat import _doc_ctr_browse_48h  # noqa: PLC0415

        return _doc_ctr_browse_48h(os.path.join(_duong_kenh(goc, ma_kenh), "chi-so"), video_id)
    except Exception:  # noqa: BLE001
        return None


def _so_moc(ho_so: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """(tên mốc, số) — ưu tiên 48h rồi 72h, rồi số mới nhất."""
    cs = ho_so.get("chi_so") or {}
    for moc in ("48h", "72h"):
        if isinstance(cs.get(moc), dict) and cs[moc]:
            return moc, cs[moc]
    moi = ho_so.get("so_lieu_moi_nhat") or {}
    return (str(moi.get("moc") or ""), moi) if moi else ("", {})


def _nguon_cua_goi(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{mã gói "<kênh>-<lượt>": {"link", "ma", "tieu_de", "cong_thuc", "tham_do", …}}` — bí danh của
    `ho_so_video.nguon_cua_goi` (B5, 30/09/2026: một bản logic duy nhất; bản đó thêm công thức/thăm dò,
    và lượt có `ma_goi` thật không bị lượt phục hồi cùng mã lượt đè)."""
    try:
        from . import ho_so_video  # noqa: PLC0415

        return ho_so_video.nguon_cua_goi(goc, ma_kenh)
    except Exception:  # noqa: BLE001 — bối cảnh phụ, hỏng thì rỗng
        return {}


def _ho_so_video(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    ra = []
    for duong in sorted(glob.glob(os.path.join(_duong_kenh(goc, ma_kenh), "ho-so-video", "*.json"))):
        du = _doc_json(duong)
        if isinstance(du, dict):
            ra.append(du)
    return ra


def _sub_theo_video(goc: str, ma_kenh: str) -> Dict[str, Tuple[float, float]]:
    """`{video_id: (đăng ký, lượt xem)}` từ `chi-so/bang-tom-tat.csv`."""
    ra = {}
    for d in _doc_csv(os.path.join(_duong_kenh(goc, ma_kenh), "chi-so", "bang-tom-tat.csv")):
        vid = str(d.get("Mã video") or "").strip()
        if vid:
            ra[vid] = (_so(d.get("Đăng ký")), _so(d.get("Lượt xem")))
    return ra


def _video_cua_minh(goc: str, ma_kenh: str) -> str:
    nguon = _nguon_cua_goi(goc, ma_kenh)
    sub = _sub_theo_video(goc, ma_kenh)
    dong = []
    for hs in _ho_so_video(goc, ma_kenh):
        moc, s = _so_moc(hs)
        vid = str(hs.get("video_id") or "")
        ng = nguon.get(str(hs.get("ma_goi") or ""), {})
        if not s:
            dong.append("- {0} · (chưa đăng hoặc chưa có số Studio){1}".format(
                _gon(hs.get("tieu_de"), 90) or "?",
                " · nguồn: " + (_gon(ng.get("tieu_de"), 60) or ng.get("ma", "")) if ng else ""))
            continue
        if moc not in ("48h", "72h") and s.get("moc_gio_that"):
            moc = "mới {0}h tuổi".format(s.get("moc_gio_that"))
        br = _ctr_browse(goc, ma_kenh, vid)
        su, vw = sub.get(vid, (0.0, 0.0))
        dong.append("- {0} · bìa “{1}” · {2}: {3} hiển thị · CTR {4}%{5} · {6} view · AVD {7}s ({8}%)"
                    " · sub/1k view {9}{10}".format(
                        _gon(hs.get("tieu_de"), 90) or "?", _gon(hs.get("chu_bia"), 30) or "—",
                        moc or "mốc ?", _ngan_so(_so(s.get("impressions"))), s.get("ctr", "?"),
                        " · CTR TRANG CHỦ {0:.2f}%".format(br) if br is not None else "",
                        _ngan_so(_so(s.get("views"))), s.get("avd_giay", "?"), s.get("avd_pct", "?"),
                        "{0:.1f}".format(1000.0 * su / vw) if vw else "?",
                        " · nguồn: " + (_gon(ng.get("tieu_de"), 60) or ng.get("ma", "")) if ng else ""))
    return "\n".join(dong) if dong else "(kênh chưa có video nào có số Studio)"


def _video_ca_nhom(goc: str, ma_kenh: str) -> str:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        nhom = nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
        if not nhom:
            return ""
        hang = _doc_csv(os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), "bang-nhom.csv"))
    except Exception:  # noqa: BLE001
        return ""
    hang = [h for h in hang if str(h.get("Kênh") or "") != ma_kenh]
    if not hang:
        return ""
    hang.sort(key=lambda h: -_so(h.get("Lượt hiển thị")))
    dong = []
    bay_gio = _dt.datetime.now()
    for h in hang[:30]:
        imp = _so(h.get("Lượt hiển thị"))
        tuoi = _tuoi_ngay(str(h.get("Ngày đăng") or ""), bay_gio)
        if tuoi is not None and tuoi < 3 and imp < NGUONG_THANG_48H:
            # 30/09/2026: video 2 ngày tuổi 116 hiển thị từng bị gắn "trượt" — chưa đủ mốc thì chưa kết.
            nhan = "MỚI {0:.0f} ngày — chưa kết luận".format(tuoi)
        else:
            nhan = "THẮNG" if imp >= NGUONG_THANG_48H else ("trượt" if imp < NGUONG_TRUOT_48H else "vừa")
        vw, su = _so(h.get("Lượt xem")), _so(h.get("Đăng ký"))
        dong.append("- [{0} · tệp {1}] {2} · {3} hiển thị (trọn đời) · CTR {4} · xem TB {5} · {6} view"
                    " · sub/1k {7} · đăng {8} → {9}".format(
                        h.get("Kênh"), h.get("Tệp") or "?", _gon(h.get("Tiêu đề"), 90), _ngan_so(imp),
                        h.get("Tỷ lệ bấm") or "?", h.get("Xem TB") or "?", _ngan_so(vw),
                        "{0:.1f}".format(1000.0 * su / vw) if vw else "?", h.get("Ngày đăng") or "?", nhan))
    return "\n".join(dong)


def _thang_truot_theo_cum(goc: str, ma_kenh: str, bay_gio: _dt.datetime) -> str:
    """Bảng SỐ THẬT của cả nhóm gom theo CỤM (nhận cụm theo nghĩa nếu AI đã phân, không thì từ
    khoá của kênh đang chọn): mỗi cụm bao nhiêu video, thắng/trượt, CTR TB — để biên tập viên
    thấy "cụm お金持ち thắng 4/4, 精神年齢 trượt 2/2" bằng số chứ không bằng lời kể."""
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415
        from . import nhom_kenh  # noqa: PLC0415

        nhom = nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
        if not nhom:
            return ""
        hang = _doc_csv(os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), "bang-nhom.csv"))
        ch, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
        v7.nap_phan_cum(goc, ma_kenh, ch)
    except Exception:  # noqa: BLE001
        return ""
    ten = {k: str((v or {}).get("ten") or k) for k, v in (ch.get("cum") or {}).items()}
    gom: Dict[str, List[Tuple[str, float, float, str]]] = {}
    for h in hang:
        td = str(h.get("Tiêu đề") or "").strip()
        tuoi = _tuoi_ngay(str(h.get("Ngày đăng") or ""), bay_gio)
        if not td or tuoi is None or tuoi < 3:
            continue
        imp = _so(h.get("Lượt hiển thị"))
        ctr = _so(h.get("Tỷ lệ bấm"))
        try:
            cum = v7.cum_cua_tieu_de(td, ch) or ["(không cụm)"]
        except Exception:  # noqa: BLE001
            cum = ["(không cụm)"]
        for c in cum[:2]:
            gom.setdefault(c, []).append((td, imp, ctr, str(h.get("Kênh") or ""),
                                          _so(h.get("Lượt xem")), _so(h.get("Đăng ký"))))
    if not gom:
        return ""
    dong = ["Mốc: THẮNG ≥ {0} hiển thị, trượt < {1} (số trọn đời, video ≥ 3 ngày tuổi).".format(
        _ngan_so(NGUONG_THANG_48H), _ngan_so(NGUONG_TRUOT_48H))]
    xep = sorted(gom.items(), key=lambda kv: -sum(1 for x in kv[1] if x[1] >= NGUONG_THANG_48H))
    for c, ds in xep:
        th = [x for x in ds if x[1] >= NGUONG_THANG_48H]
        tr = [x for x in ds if x[1] < NGUONG_TRUOT_48H]
        ctr = [x[2] for x in ds if x[2]]
        vd = "; ".join("{0}{1} {2}".format("✓" if x[1] >= NGUONG_THANG_48H else ("✗" if x[1] < NGUONG_TRUOT_48H else "~"),
                                            x[3], _gon(x[0], 34)) for x in sorted(ds, key=lambda x: -x[1])[:5])
        vw, su = sum(x[4] for x in ds), sum(x[5] for x in ds)
        dong.append("- cụm {0}: {1} video · thắng {2} · trượt {3} · CTR TB {4} · sub/1k view {5} — {6}".format(
            ten.get(c, c), len(ds), len(th), len(tr),
            "{0:.2f}%".format(sum(ctr) / len(ctr)) if ctr else "?",
            "{0:.1f}".format(1000.0 * su / vw) if vw else "?", vd))
    return "\n".join(dong)


#: Ngưỡng bật kiếm tiền YouTube (YPP).
YPP_SUB, YPP_GIO = 1000.0, 4000.0


def muc_tieu_ypp(goc: str, ma_kenh: str) -> Dict[str, Any]:
    """Tiến độ YPP của kênh từ `chi-so/kenh-theo-ngay.csv` (dòng mới nhất có số, qua
    `trung_tam.ypp`) + RÀNG BUỘC đang thiếu: "sub" | "gio_xem" | "chua_co_so" | "da_du".

    Luật chọn ràng buộc: tỉ lệ đạt (sub/1.000, giờ/4.000) thấp hơn là ràng buộc; kênh non cả hai
    đều < 25% thì "gio_xem" — ở giai đoạn này sub đến SAU view, việc số một là ăn được trang chủ."""
    try:
        from . import trung_tam  # noqa: PLC0415

        hang = _doc_csv(os.path.join(_duong_kenh(goc, ma_kenh), "chi-so", "kenh-theo-ngay.csv"))
        y = trung_tam.ypp(hang) if hang else {}
    except Exception:  # noqa: BLE001
        y = {}
    sub, gio = y.get("dang_ky"), y.get("gio_xem")
    if sub is None and gio is None:
        return {"rang_buoc": "chua_co_so", "sub": None, "gio_xem": None, "thieu_sub": None,
                "thieu_gio": None, "luc": ""}
    sub, gio = float(sub or 0), float(gio or 0)
    ts, tg = sub / YPP_SUB, gio / YPP_GIO
    if ts >= 1 and tg >= 1:
        rb = "da_du"
    elif ts < 0.25 and tg < 0.25:
        rb = "gio_xem"
    else:
        rb = "sub" if ts < tg else "gio_xem"
    return {"rang_buoc": rb, "sub": sub, "gio_xem": gio, "thieu_sub": max(0.0, YPP_SUB - sub),
            "thieu_gio": max(0.0, YPP_GIO - gio), "luc": str(y.get("luc") or "")}


def _khoi_muc_tieu(goc: str, ma_kenh: str) -> str:
    m = muc_tieu_ypp(goc, ma_kenh)
    if m["rang_buoc"] == "chua_co_so":
        return ("Kênh chưa có số Studio cấp kênh. Coi như kênh non: ràng buộc là VIEW/GIỜ XEM — chọn nguồn ăn được "
                "TRANG CHỦ (CTR browse) và giữ chân lâu (15–21 phút).")
    dong = ["Bật kiếm tiền (YPP) cần 1.000 sub + 4.000 giờ xem. Hiện: {0:,.0f} sub · {1:,.0f} giờ xem (Studio {2}). "
            "Còn thiếu: {3} · {4}.".format(
                m["sub"], m["gio_xem"], m["luc"] or "?",
                "{0:,.0f} sub".format(m["thieu_sub"]) if m["thieu_sub"] else "đủ sub",
                "{0:,.0f} giờ xem".format(m["thieu_gio"]) if m["thieu_gio"] else "đủ giờ xem").replace(",", ".")]
    if m["rang_buoc"] == "sub":
        dong.append("RÀNG BUỘC ĐANG THIẾU: SUB. Giờ xem đã gần/đủ — ưu tiên nguồn/cụm có SUB/1.000 VIEW cao (xem cột "
                    "sub/1k trong bảng thắng/trượt theo cụm và sub/1k từng video): nội dung khiến người xem muốn theo "
                    "dõi kênh (chuỗi, bản sắc, tệp trung thành), không chỉ view một lần.")
    elif m["rang_buoc"] == "gio_xem":
        dong.append("RÀNG BUỘC ĐANG THIẾU: VIEW/GIỜ XEM. Ưu tiên nguồn ĐỘT BIẾN có khả năng ăn TRANG CHỦ (CTR trang chủ "
                    "≥ 5,5%) và video dài giữ chân (15–21 phút, AVD giây cao) — giờ xem = view × thời lượng xem.")
    else:
        dong.append("Kênh đã đủ điều kiện YPP — tối ưu view/doanh thu: nguồn ăn trang chủ, giữ chân lâu.")
    dong.append("Với MỖI nguồn chọn, nói rõ nó giúp lấp chỗ thiếu này thế nào (trường \"giup_ypp\").")
    return "\n".join(dong)


def _insight_nhom(goc: str, ma_kenh: str, bay_gio: _dt.datetime) -> str:
    """INSIGHT có số của nhóm: tệp sống `CHANNEL/_NHOM/<nhóm>/INSIGHT-CHON-CONTENT.md` (người/agent
    viết từ phân tích dữ liệu) + bảng thắng/trượt theo cụm tính lại mỗi lượt từ `bang-nhom.csv`."""
    phan = []
    try:
        from . import nhom_kenh  # noqa: PLC0415

        nhom = nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
        if nhom:
            chu = _doc_chu(os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), TEP_INSIGHT), 6000).strip()
            if chu:
                phan.append(chu)
    except Exception:  # noqa: BLE001
        pass
    bang = _thang_truot_theo_cum(goc, ma_kenh, bay_gio)
    if bang:
        phan.append("THẮNG/TRƯỢT THEO CỤM — cả nhóm, số Studio thật:\n" + bang)
    return "\n\n".join(phan)


def _bai_hoc(goc: str, ma_kenh: str) -> str:
    phan = []
    rieng = _doc_chu(os.path.join(_nghien_cuu(goc, ma_kenh), "BAI-HOC-SAN-XUAT.md"), 3500).strip()
    if rieng:
        phan.append("Kênh mình:\n" + rieng)
    if len(rieng) < 1500:
        # Kênh non chưa có bài học — mượn bài học của kênh anh em nhiều bài học nhất.
        try:
            from . import nhom_kenh  # noqa: PLC0415

            tot = ("", "")
            for ma in nhom_kenh.thanh_vien(goc, ma_kenh):
                if ma == ma_kenh:
                    continue
                chu = _doc_chu(os.path.join(_nghien_cuu(goc, ma), "BAI-HOC-SAN-XUAT.md"), 5000).strip()
                if len(chu) > len(tot[1]):
                    tot = (ma, chu)
            if len(tot[1]) > 1500:
                phan.append("Kênh anh em {0} (đã có dữ liệu):\n{1}".format(tot[0], tot[1]))
        except Exception:  # noqa: BLE001
            pass
    return "\n\n".join(phan) or "(chưa có bài học sản xuất)"


def _xu_huong(goc: str, ma_kenh: str, bay_gio: _dt.datetime) -> str:
    """Tỉ lệ cụm chủ đề trên TRANG CHỦ máy ảo của kênh theo tuần (4 tuần) + tiêu đề đúng ngách
    xuất hiện nhiều nhất 7 ngày qua — để mô hình tự đọc cái gì đang lên/nguội."""
    hang = _doc_csv(os.path.join(_nghien_cuu(goc, ma_kenh), "trang-chu.csv"))
    if not hang:
        return "(chưa có dữ liệu trang chủ)"
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        cum_cua = v7.cum_cua_tieu_de
        ten_cum = {k: str(v.get("ten") or k) for k, v in (v7.CAU_HINH_MAC_DINH.get("cum") or {}).items()}
    except Exception:  # noqa: BLE001
        cum_cua, ten_cum = None, {}
    tuan: Dict[int, Dict[str, int]] = {}
    tong: Dict[int, int] = {}
    dem7: Dict[str, int] = {}
    for h in hang:
        td = str(h.get("Tiêu đề") or "").strip()
        try:
            luc = _dt.datetime.strptime(str(h.get("Lúc quét") or "")[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        cach = (bay_gio - luc).days
        if cach < 0 or cach >= 28 or not td:
            continue
        w = cach // 7
        tong[w] = tong.get(w, 0) + 1
        if cum_cua is not None:
            try:
                for c in cum_cua(td):
                    tuan.setdefault(w, {})[c] = tuan.setdefault(w, {}).get(c, 0) + 1
            except Exception:  # noqa: BLE001
                pass
        if cach < 7 and not str(h.get("Bị loại") or "").strip() and h.get("Short") != "x":
            dem7[td] = dem7.get(td, 0) + 1
    dong = []
    if tuan:
        cac_cum = sorted({c for v in tuan.values() for c in v})
        dong.append("Tỉ lệ tiêu đề trang chủ theo cụm (tuần cũ nhất → tuần này): ")
        for c in cac_cum:
            ty = ["{0:.1f}%".format(100.0 * tuan.get(w, {}).get(c, 0) / tong[w]) if tong.get(w) else "—"
                  for w in (3, 2, 1, 0)]
            dong.append("  {0}: {1}".format(ten_cum.get(c, c), " → ".join(ty)))
    if dem7:
        top = sorted(dem7.items(), key=lambda x: -x[1])[:20]
        dong.append("Tiêu đề (đã qua lọc ngách) trang chủ phát NHIỀU LẦN NHẤT 7 ngày qua:")
        dong += ["  ×{0} {1}".format(n, _gon(t, 90)) for t, n in top]
    return "\n".join(dong) or "(trang chủ 28 ngày qua trống)"


def _khan_gia_cung_xem(goc: str, ma_kenh: str) -> Tuple[set, str]:
    """(mã video khán giả mình vừa xem, chữ mô tả) — card AUDIENCE_INTERESTS của Studio."""
    try:
        from . import nghien_cuu_chung as ncc  # noqa: PLC0415

        kho = ncc.khan_gia_cung_xem_doc(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return set(), ""
    ban = (kho or {}).get(ma_kenh) or {}
    ma = {str(v.get("video_id") or "") for v in (ban.get("video_dang_xem") or []) if isinstance(v, dict)}
    ma.discard("")
    if not ma:
        return set(), ""
    content = _chi_muc_content(goc, ma_kenh)
    td = [_gon(content[m].get("Tiêu đề video"), 80) for m in ma if m in content]
    chu = "Studio (card “khán giả cũng xem”, {0}): {1} video; biết tiêu đề: {2}".format(
        ban.get("ngay") or "?", len(ma), " | ".join(td[:12]) or "(chưa tra được tiêu đề)")
    return ma, chu


def _da_lam_ca_nhom(goc: str, ma_kenh: str) -> str:
    try:
        from . import nhom_kenh  # noqa: PLC0415

        ds = nhom_kenh.tieu_de_da_lam_ca_nhom(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        ds = []
    if not ds:
        return "(chưa làm video nào)"
    # Một video hiện nhiều dòng (tiêu đề nguồn, tiêu đề đã đặt, kế hoạch, đã đăng) — khử trùng
    # theo tiêu đề đã bỏ nhãn 【…】 để còn chỗ cho nhiều ý hơn.
    thay, ra = set(), []
    for t, m in ds:
        khoa = re.sub(r"【[^】]*】", "", str(t or "")).strip()
        if not khoa or khoa in thay:
            continue
        thay.add(khoa)
        ra.append("- {0}  ({1})".format(_gon(t, 90), _gon(m, 50)))
    # 30/09/2026: `ra[-90:]` cắt mất ĐẦU danh sách — chính là video của kênh mình (thành viên xếp
    # theo tên, kênh đang chọn thường đứng đầu). Giữ tới 160 dòng, đủ cho cả nhóm hiện nay.
    return "\n".join(ra[:160])


def doc_bai_hoc_bien_tap(goc: str, ma_kenh: str, so_dong: int = 10) -> str:
    """Những lần biên tập viên đã dự đoán, kèm số thật — để lần chọn sau tự sửa mình."""
    du = _doc_json(os.path.join(_nghien_cuu(goc, ma_kenh), THU_MUC, TEP_DANH_GIA))
    ban = (du or {}).get("ban_ghi") if isinstance(du, dict) else None
    if not ban:
        return "(chưa có lần dự đoán nào đủ 48h để chấm)"
    dong = []
    for b in ban[-so_dong:]:
        dong.append("- {0}: dự đoán CTR {1} · {2} → thật: CTR {3}%{4} · {5} hiển thị @{6} · giờ xem {9} · "
                    "sub/1k {10} → {7}{8}".format(
            _gon(b.get("tieu_de_nguon"), 60) or b.get("ma_nguon"), b.get("du_doan_ctr") or "?",
            b.get("du_doan_ket_cuc") or "?", b.get("ctr_that") if b.get("ctr_that") is not None else "?",
            " (trang chủ {0}%)".format(b["ctr_browse"]) if b.get("ctr_browse") is not None else "",
            _ngan_so(_so(b.get("impressions"))), b.get("moc") or "?",
            "ĐÚNG" if b.get("dung") else "SAI",
            " — vì sao: " + _gon(b.get("vi_sao_sai"), 200) if b.get("vi_sao_sai") else "",
            b.get("gio_xem") if b.get("gio_xem") is not None else "?",
            b.get("sub_1k") if b.get("sub_1k") is not None else "?"))
    bai = (du or {}).get("bai_hoc") or []
    if bai:
        dong.append("Bài học rút ra từ các lần sai: " + " | ".join(_gon(x, 200) for x in bai[-5:]))
    return "\n".join(dong)


def dung_boi_canh(goc: str, ma_kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, str]:
    """Mọi khối bối cảnh KÊNH (không phụ thuộc ứng viên) — tách ra để test/đọc tay."""
    bay_gio = bay_gio or _dt.datetime.now()
    ma_xem, chu_xem = _khan_gia_cung_xem(goc, ma_kenh)

    def an_toan(f: Callable[[], str]) -> str:
        try:
            return f() or ""
        except Exception as loi:  # noqa: BLE001 — một khối hỏng không được giết cả lượt
            return "(không đọc được: {0})".format(str(loi)[:80])

    ra = {
        "muc_tieu": an_toan(lambda: _khoi_muc_tieu(goc, ma_kenh)),
        "dinh_vi": an_toan(lambda: _dinh_vi(goc, ma_kenh)),
        "khan_gia": an_toan(lambda: _khan_gia(goc, ma_kenh)) + ("\n" + chu_xem if chu_xem else ""),
        "video_minh": an_toan(lambda: _video_cua_minh(goc, ma_kenh)),
        "video_nhom": an_toan(lambda: _video_ca_nhom(goc, ma_kenh)),
        "insight_nhom": an_toan(lambda: _insight_nhom(goc, ma_kenh, bay_gio)),
        "bai_hoc": an_toan(lambda: _bai_hoc(goc, ma_kenh)),
        "xu_huong": an_toan(lambda: _xu_huong(goc, ma_kenh, bay_gio)),
        "da_lam": an_toan(lambda: _da_lam_ca_nhom(goc, ma_kenh)),
        "tu_sua": an_toan(lambda: doc_bai_hoc_bien_tap(goc, ma_kenh)),
        "_ma_khan_gia_xem": ",".join(sorted(ma_xem)),
    }
    if che_do_de_bai(goc, ma_kenh) == DE_BAI_GON:
        try:
            ra.update(_boi_canh_gon(goc, ma_kenh, bay_gio, ra, an_toan))
        except Exception:  # noqa: BLE001 — khối gọn hỏng thì lùi về đề bài cũ, không chặn lượt
            pass
    return ra


# ── lời nhắc ─────────────────────────────────────────────────────────────────

DE_BAI = """═══ MỤC TIÊU KÊNH — lý do tồn tại của kênh: có view và BẬT KIẾM TIỀN ═══
{muc_tieu}

Bạn là BIÊN TẬP VIÊN NỘI DUNG giỏi nhất của một kênh YouTube tiếng Nhật làm theo lối REMAKE:
chọn một video đối thủ đã nổ, viết lại kịch bản theo giọng kênh mình (tiêu đề giữ gần nguồn là CHỦ ĐÍCH,
không phải lỗi), dựng hình mới, đăng. Với remake, CHỌN ĐÚNG NGUỒN quyết định video có nổ không và kênh
có bật kiếm tiền (1.000 sub + 4.000 giờ) không. Bạn không lọc theo từ khoá — bạn ĐỌC NGHĨA và SUY LUẬN.

Máy đã xếp sẵn {so_uv} ứng viên theo công thức số (đột biến, VPH, cụm, điểm). Việc của bạn là thứ công
thức không làm được. Với TỪNG ứng viên, nghĩ kỹ:
 1. Video nguồn nổ VÌ SAO? — lời hứa của tiêu đề, cảm xúc nó chạm (tò mò / được gỡ tội / được khen /
    sợ / hả hê…), tệp người nó kéo, và phần nào của cái "vì sao" ấy nằm ở NỘI DUNG (chép được qua kịch
    bản) chứ không nằm ở danh tiếng/khuôn mặt/chuỗi series của kênh nguồn (không chép được).
 2. Cái "vì sao" ấy có CHUYỂN được sang kênh mình không — đúng tệp kênh đang đánh, và đúng KHÁN GIẢ
    THẬT YouTube đang phát ngách này tới (xem số tuổi/giới/thiết bị: phần lớn là người Nhật 55+, xem
    nhiều trên TV)? Một đề tài hay nhưng kéo tệp khác là kéo kênh lệch tệp.
 3. Có TRÙNG Ý thứ kênh mình hoặc cả nhóm đã làm/đã đăng không — cùng luận điểm, dù chữ khác? Trùng thì
    loại: hai kênh anh em không làm lại cùng một nội dung (dòng "⚠ GẦN GIỐNG" là máy nghi — bạn đọc nghĩa
    mà phán; một video anh em làm từ ĐÚNG nguồn này thì chắc chắn trùng).
 4. Dự đoán cổng quyết định: CTR TRANG CHỦ (Browse) @48h — video thắng của nhóm có CTR trang chủ
    ~5,5–6,2%, video trượt ~3–4,5% — và AVD (giây). Kết cục @48h theo lượt hiển thị: "thắng" ≥ {thang},
    "trượt" < {truot}, còn lại "vừa". Kênh non (ít sub) thì hiển thị thấp hơn kênh anh em lớn — dự đoán
    theo đúng cỡ kênh mình.
 5. Dùng SỐ THẬT bên dưới (video đã thắng/trượt, bài học, xu hướng) làm bằng chứng. Đọc phần "tự sửa":
    đó là những lần bạn đã dự đoán sai trước đây và vì sao — đừng lặp lại.

 6. Đọc "INSIGHT NHÓM" (cụm nào đã THẮNG/TRƯỢT bằng số thật). Cụm đã trượt ở kênh anh em (vd 精神年齢,
    物欲が減った) chỉ được chọn khi có lý do rất mạnh ghi rõ; cụm đang thắng (お金持ち…) ghép với tệp mình là
    hướng ưu tiên. Máy công thức KHÔNG biết điều này — bạn phải biết.
 7. Chỉ là TÂM LÝ / CHÂN DUNG CON NGƯỜI mới đúng ngách. Sức khoẻ, ăn uống, thuốc, mẹo vặt, tiền hưu/thuế
    thuần "cách làm", tin tức, người nổi tiếng, truyện đọc → lệch ngách dù cùng khán giả 55+.

Rồi CHẤM TỪNG ứng viên một hạng — đây là CỔNG CHẤT LƯỢNG, máy chỉ sản xuất nguồn TOT:
 - "TOT": đúng ngách tâm lý, hợp tệp kênh + khán giả thật, nổ thật vì NỘI DUNG (chép được), không trùng ý
   thứ nhóm đã làm, không thuộc cụm đã trượt, giúp lấp đúng chỗ thiếu ở MỤC TIÊU KÊNH; bạn tin CTR trang chủ
   ≥ 5%. Nguồn phải ĐÃ CHỨNG MINH nổ (≥ ×3 view trung vị kênh nguồn, hoặc đột biến cùng tuổi ≥ ×3): đề tài hay
   mà nguồn chưa nổ (vd 2 ngày tuổi, dưới mức thường của kênh) tối đa là TAM. ĐÀ TĂNG lúc chọn (view/ngày)
   là thước SỐ 1, không phải tổng view: nguồn "NGUỘI" (đà ≈ 0) nghĩa là máy đã thôi phát chủ đề đó → không
   được TOT (máy tự hạ). Đủ để bỏ tiền sản xuất hôm nay.
 - "TAM": dùng được nhưng có một điểm yếu rõ (tệp hơi lệch, nguồn nổ yếu/cũ, dạng "cách làm", thiếu lời thoại…).
 - "TE": lệch ngách, lệch tệp, trùng ý, cụm đã trượt, nổ nhờ thứ không chép được, kênh nguồn rác/không phải Nhật.
 kèm "điểm" 0–100 = xác suất bạn tin nó thắng × 100. Hãy khắt khe: thà ít TOT còn hơn TOT giả — không
 có TOT thì máy mở thêm ứng viên kế cho bạn đọc. Được đảo hoàn toàn thứ tự của máy.

═══ ĐỊNH VỊ KÊNH MÌNH ═══
{dinh_vi}

═══ INSIGHT NHÓM — bài học chọn content có số (ĐỌC KỸ) ═══
{insight_nhom}

═══ KHÁN GIẢ THẬT ═══
{khan_gia}

═══ VIDEO CỦA KÊNH MÌNH — số Studio ═══
{video_minh}

═══ VIDEO CỦA CÁC KÊNH ANH EM TRONG NHÓM — số Studio (cùng ngách, khác tệp) ═══
{video_nhom}

═══ BÀI HỌC SẢN XUẤT (quan sát có số) ═══
{bai_hoc}

═══ XU HƯỚNG (trang chủ máy ảo của kênh) ═══
{xu_huong}

═══ CẢ NHÓM ĐÃ LÀM (tránh trùng ý) ═══
{da_lam}

═══ TỰ SỬA — các lần biên tập viên đã dự đoán, và số thật ═══
{tu_sua}

═══ ỨNG VIÊN (thứ tự của công thức) ═══
{ung_vien}

═══ TRẢ LỜI ═══
DUY NHẤT một JSON (không rào ```, không chữ nào ngoài JSON), viết tiếng Việt, NGẮN — mỗi trường ≤ 35 chữ:
{{"nhan_dinh": "2-3 câu: tệp này đang cần gì, cái gì đang lên/nguội, bài học từ số",
  "chon": [{{"u": <số ứng viên>, "ly_do": "vì sao chọn", "vi_sao_no": "nguồn nổ vì lời hứa/cảm xúc/tệp nào",
            "chuyen_duoc": "vì sao hợp khán giả kênh mình", "ctr": <số, % CTR trang chủ dự đoán @48h, vd 5.2>,
            "avd_giay": <số giây AVD dự đoán>, "ket_cuc": "thắng|vừa|trượt", "rui_ro": "rủi ro chính",
            "giup_ypp": "nguồn này lấp chỗ thiếu ở MỤC TIÊU KÊNH (sub hay giờ xem) thế nào"}}],
  "con_lai": [<số ứng viên còn dùng được, theo thứ tự nên làm>],
  "loai": {{"<số>": "lý do loại"}},
  "cham": {{"<số>": ["TOT|TAM|TE", <điểm 0-100>]}}}}
"chon" có TỐI ĐA {so_chon} phần tử, CHỈ gồm ứng viên hạng TOT, tốt nhất trước (không có TOT thì "chon": []).
Mỗi ứng viên chỉ xuất hiện ở MỘT trong ba chỗ chon / con_lai / loai; ứng viên TE nằm ở "loai".
"cham" phải có ĐỦ mọi ứng viên U1…U{so_uv}."""


# ── đề bài GỌN (B5/B6 `workspace/THIET-KE-CHIEN-LUOC.md` mục 5/7, 30/09/2026) ─────
#
# MỤC TIÊU (3 dòng từ ngữ cảnh kênh) + TIÊU CHÍ (suy luận trung tính + luật ngách + bài học có số của
# CHÍNH kênh) + DỮ LIỆU + DẠNG TRẢ LỜI (y hệt khuôn cũ — `doc_ket_qua` không đổi). Không số cứng của một
# thị trường: khán giả, CTR, ngưỡng thắng, luật ngách đọc từ kênh/ngách, mặc định = hằng của DE_BAI cũ.
# CHỈ bật khi kenh.yaml khai `de_bai_bien_tap: "gon"` — kênh khác giữ nguyên DE_BAI từng byte.

KHOA_DE_BAI = "de_bai_bien_tap"
DE_BAI_GON = "gon"
#: Khối nhóm (video anh em, INSIGHT nhóm) chỉ vào khi kênh còn ít số riêng hơn ngần này video đủ 48h.
SO_VIDEO_48H_BO_NHOM = 6
#: Mặc định = hằng cũ của DE_BAI (nhóm tâm lý Nhật). kenh.yaml / ngach.yaml khai thì đè.
MAC_DINH_KHAN_GIA = "phần lớn là người Nhật 55+, xem nhiều trên TV"
MAC_DINH_CTR_THANG, MAC_DINH_CTR_TRUOT = "~5,5–6,2%", "~3–4,5%"
MAC_DINH_LUAT_NGACH = (
    "Chỉ là TÂM LÝ / CHÂN DUNG CON NGƯỜI mới đúng ngách.",
    "Sức khoẻ, ăn uống, thuốc, mẹo vặt, tiền hưu/thuế thuần \"cách làm\", tin tức, người nổi tiếng, truyện "
    "đọc → lệch ngách dù cùng khán giả.",
)
_TEN_TIENG = {"ja": "tiếng Nhật", "vi": "tiếng Việt", "en": "tiếng Anh", "ko": "tiếng Hàn", "zh": "tiếng Trung"}


def che_do_de_bai(goc: str, ma_kenh: str) -> str:
    """`"gon"` khi kenh.yaml khai `de_bai_bien_tap: "gon"`, ngược lại `""` (đề bài cũ)."""
    gt = str(_yaml_kenh(goc, ma_kenh).get(KHOA_DE_BAI) or "").strip().lower()
    return DE_BAI_GON if gt == DE_BAI_GON else ""


def _gia_tri(goc: str, ma_kenh: str, nc: Any, khoa: str, mac_dinh: Any) -> Any:
    """kenh.yaml > `NguCanh.thi_truong` > `HoSoNgach.<khoa>` > ngach.yaml thô (gốc / `thi_truong.<khoa>`) >
    mặc định."""
    gt = _yaml_kenh(goc, ma_kenh).get(khoa)
    if gt not in (None, "", []):
        return gt
    try:
        gt = nc.thi_truong.get(khoa)
        if gt not in (None, "", []):
            return gt
        gt = getattr(nc.ngach, khoa, None)
        if gt not in (None, "", []):
            return gt
        from . import ho_so_ngach  # noqa: PLC0415

        tho = ho_so_ngach.doc_ngach_tho(goc, nc.nhom) or {}
        gt = tho.get(khoa)
        if gt in (None, "", []) and isinstance(tho.get("thi_truong"), dict):
            gt = tho["thi_truong"].get(khoa)
        if gt not in (None, "", []):
            return gt
    except Exception:  # noqa: BLE001
        pass
    return mac_dinh


def _muc_tieu_gon(goc: str, ma_kenh: str, nc: Any) -> str:
    """3 dòng: YPP (số trọn đời `kenh-theo-ngay.csv` nếu có, không thì `NguCanh.ypp`) · tệp · CTR phải đạt."""
    dong = nc.muc_tieu().split("\n")
    m = muc_tieu_ypp(goc, ma_kenh)
    if m["rang_buoc"] != "chua_co_so":
        ten = {"moi": "Kênh mới", "dang_len": "Kênh đang lên", "kiem_tien": "Kênh đã kiếm tiền"}.get(
            nc.giai_doan, "Kênh")
        if m["rang_buoc"] == "da_du":
            d1 = "{0} — đã đủ YPP; tối đa view và giờ xem trên chính tệp của kênh.".format(ten)
        else:
            def so(x: float) -> str:
                return "{0:,.0f}".format(x).replace(",", ".")

            thieu = " · ".join(x for x in (
                so(m["thieu_sub"]) + " sub" if m["thieu_sub"] else "",
                so(m["thieu_gio"]) + " giờ xem" if m["thieu_gio"] else "") if x)
            d1 = "{0}: {1} sub · {2} giờ xem (Studio {3}); thiếu {4} — RÀNG BUỘC: {5}.".format(
                ten, so(m["sub"]), so(m["gio_xem"]), m["luc"] or "?", thieu,
                "SUB (ưu tiên nguồn/cụm có sub/1k view cao)" if m["rang_buoc"] == "sub"
                else "VIEW/GIỜ XEM (ưu tiên nguồn ăn trang chủ, giữ chân lâu)")
        dong[0] = d1
    return "\n".join(dong[:3])


def _boi_canh_gon(goc: str, ma_kenh: str, bay_gio: _dt.datetime, cu: Dict[str, str],
                  an_toan: Callable[[Callable[[], str]], str]) -> Dict[str, str]:
    """Khối thêm cho đề bài gọn. Không trùng khối cũ: bài học kênh bỏ trục `bien_tap` (đã ở TỰ SỬA) và
    `insight_nhom` (đã ở INSIGHT NHÓM), chỉ lấy phạm vi KÊNH. Khối nhóm tắt khi kênh đủ số riêng."""
    from .chien_luoc import bai_hoc, ket_qua, ngu_canh  # noqa: PLC0415

    co_v7 = False
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415

        co_v7 = os.path.isfile(os.path.join(_nghien_cuu(goc, ma_kenh), v7.TEP_CAU_HINH))
    except Exception:  # noqa: BLE001
        pass
    nc = ngu_canh.dung(goc, ma_kenh, co_v7=co_v7, bay_gio=bay_gio)
    try:
        _vm, nguong = ket_qua.video_kenh(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        nguong = None
    nguong = float(nguong or NGUONG_THANG_48H)
    try:
        so48 = int(nc.so_video_48h)
    except Exception:  # noqa: BLE001
        so48 = 0
    luat = _gia_tri(goc, ma_kenh, nc, "luat_chon", list(MAC_DINH_LUAT_NGACH))
    if isinstance(luat, str):
        luat = [x.strip() for x in luat.split("|") if x.strip()]
    ngon_ngu = str(nc.thi_truong.get("ngon_ngu") or "ja")
    ctr_muc_tieu = nc.thi_truong.get("ctr_trang_chu_muc_tieu")
    try:  # bài học CỦA KÊNH (n ≥ 3) đứng trên mặc định ngách — cùng luật dòng 3 của `NguCanh.muc_tieu()`
        for b in nc.bai_hoc:
            if "ctr" in str(b.get("truc") or "").lower() and int(b.get("n") or 0) >= 3 and b.get("muc_tieu"):
                ctr_muc_tieu = b.get("muc_tieu")
                break
    except Exception:  # noqa: BLE001
        pass
    try:
        ctr_tot = "{0:g}%".format(float(ctr_muc_tieu))
    except (TypeError, ValueError):
        ctr_tot = "5%"
    ra = {
        "_de_bai": DE_BAI_GON,
        "muc_tieu": an_toan(lambda: _muc_tieu_gon(goc, ma_kenh, nc)),
        "bai_hoc_kenh": an_toan(lambda: bai_hoc.khoi_chu(
            goc, ma_kenh, "bien_tap", pham_vi=("kenh",), bo_truc=("bien_tap", "insight_nhom"),
            bay_gio=bay_gio)) or "(kênh chưa có bài học đủ n ≥ 3)",
        "nguon_giu_roi": an_toan(lambda: bai_hoc.khoi_nguon_giu_roi(goc, ma_kenh)) or "(chưa nối được nguồn nào)",
        "ngon_ngu": _TEN_TIENG.get(ngon_ngu.lower(), ngon_ngu),
        "khan_gia_mo_ta": str(_gia_tri(goc, ma_kenh, nc, "khan_gia_mo_ta", MAC_DINH_KHAN_GIA)),
        "ctr_thang": str(_gia_tri(goc, ma_kenh, nc, "ctr_trang_chu_thang", MAC_DINH_CTR_THANG)),
        "ctr_truot": str(_gia_tri(goc, ma_kenh, nc, "ctr_trang_chu_truot", MAC_DINH_CTR_TRUOT)),
        "ctr_tot": ctr_tot,
        "luat_ngach": "\n".join("    - " + _gon(x, 300) for x in luat) or "    - (ngách chưa khai luat_chon)",
        # ngưỡng thắng của CHÍNH kênh (V7 `_danh_dau_thang`); trượt giữ đúng tỉ lệ cũ 6.000/20.000
        "thang": _ngan_so(nguong),
        "truot": _ngan_so(nguong * NGUONG_TRUOT_48H / NGUONG_THANG_48H),
    }
    if so48 >= SO_VIDEO_48H_BO_NHOM:
        ra["khoi_nhom"] = ""
    else:
        ra["khoi_nhom"] = ("\nNHÓM — tiên nghiệm (kênh mới có {0} video đủ 48h, dưới {1}; số của chính kênh luôn "
                           "đứng trên):\nINSIGHT NHÓM:\n{2}\n\nVIDEO CÁC KÊNH ANH EM (cùng ngách, khác tệp):\n{3}\n"
                           ).format(so48, SO_VIDEO_48H_BO_NHOM, cu.get("insight_nhom") or "(trống)",
                                    cu.get("video_nhom") or "(trống)")
    return ra


DE_BAI_GON_KHUON = """═══ MỤC TIÊU ═══
{muc_tieu}
Với MỖI nguồn chọn, nói rõ nó giúp lấp chỗ thiếu này thế nào (trường "giup_ypp").

Bạn là BIÊN TẬP VIÊN NỘI DUNG của một kênh YouTube {ngon_ngu} làm REMAKE (chọn video đối thủ đã nổ,
viết lại theo giọng kênh mình; tiêu đề gần nguồn là chủ đích). Chọn đúng nguồn quyết định video nổ và
kênh bật kiếm tiền. Không lọc theo từ khoá — ĐỌC NGHĨA và SUY LUẬN.

═══ TIÊU CHÍ ═══
Với TỪNG ứng viên (máy đã xếp {so_uv} dòng theo công thức số):
 1. Nguồn nổ VÌ SAO — lời hứa tiêu đề, cảm xúc, tệp người — và phần ấy nằm ở NỘI DUNG (chép được qua kịch
    bản) hay ở danh tiếng/khuôn mặt/series của kênh nguồn (không chép được)?
 2. Có CHUYỂN được sang kênh mình — đúng tệp kênh đang đánh và khán giả thật ({khan_gia_mo_ta})?
 3. TRÙNG Ý thứ kênh/nhóm đã làm (cùng luận điểm dù chữ khác; dòng "⚠ GẦN GIỐNG" là máy nghi) → loại.
 4. Dự đoán CTR TRANG CHỦ @48h (video thắng {ctr_thang}, trượt {ctr_truot}) và AVD (giây). Kết cục @48h theo
    hiển thị, ngưỡng của CHÍNH kênh: "thắng" ≥ {thang}, "trượt" < {truot}, còn lại "vừa".
 5. Dùng SỐ THẬT bên dưới làm bằng chứng; đọc TỰ SỬA — đừng lặp lại dự đoán sai cũ.
 6. Luật ngách:
{luat_ngach}
 7. Bài học có số của CHÍNH kênh (n ≥ 3) — đứng trên mọi tiên nghiệm nhóm:
{bai_hoc_kenh}

Chấm TỪNG ứng viên (cổng chất lượng, máy chỉ sản xuất TOT):
 - "TOT": đúng ngách, hợp tệp + khán giả thật, nổ thật vì NỘI DUNG, không trùng ý, không thuộc cụm đã trượt,
   lấp đúng chỗ thiếu ở MỤC TIÊU; bạn tin CTR trang chủ ≥ {ctr_tot}. Nguồn phải ĐÃ CHỨNG MINH nổ (≥ ×3 view
   trung vị kênh nguồn, hoặc đột biến cùng tuổi ≥ ×3); ĐÀ TĂNG lúc chọn là thước số 1 — nguồn NGUỘI không TOT.
 - "TAM": dùng được nhưng có một điểm yếu rõ. "TE": lệch ngách/tệp, trùng ý, cụm đã trượt, không chép được.
 kèm "điểm" 0–100 = xác suất thắng × 100. Khắt khe: thà ít TOT còn hơn TOT giả. Được đảo thứ tự của máy.

═══ DỮ LIỆU ═══
ĐỊNH VỊ KÊNH:
{dinh_vi}

KHÁN GIẢ THẬT:
{khan_gia}

VIDEO CỦA KÊNH MÌNH — số Studio:
{video_minh}

NGUỒN CỦA VIDEO GIỮ TỐT / RƠI SỚM (điểm thoát — so cấu trúc, mở đầu THEO NGHĨA với ứng viên):
{nguon_giu_roi}

BÀI HỌC SẢN XUẤT:
{bai_hoc}
{khoi_nhom}
XU HƯỚNG (trang chủ máy ảo):
{xu_huong}

CẢ NHÓM ĐÃ LÀM (tránh trùng ý):
{da_lam}

TỰ SỬA — các lần đã dự đoán, và số thật:
{tu_sua}

ỨNG VIÊN (thứ tự của công thức):
{ung_vien}

"""


def _dung_loi_nhac_gon(boi_canh: Dict[str, str], uv: Sequence[Dict[str, Any]], so_chon: int) -> str:
    """Đề bài gọn + ĐÚNG khối TRẢ LỜI của DE_BAI cũ (cắt từ chính DE_BAI — một nguồn, không lệch)."""
    tra_loi = DE_BAI[DE_BAI.index("═══ TRẢ LỜI ═══"):]
    gt = {k: v for k, v in boi_canh.items() if not k.startswith("_")}
    for k in ("muc_tieu", "dinh_vi", "khan_gia", "video_minh", "bai_hoc", "xu_huong", "da_lam", "tu_sua"):
        gt[k] = gt.get(k) or "(trống)"
    gt.setdefault("khoi_nhom", "")
    return (DE_BAI_GON_KHUON + tra_loi).format(so_uv=len(uv), so_chon=max(1, int(so_chon)),
                                               ung_vien=_khoi_ung_vien(uv), **gt)


def _khoi_ung_vien(uv: Sequence[Dict[str, Any]]) -> str:
    khoi = []
    for i, d in enumerate(uv, 1):
        so = ["{0} view".format(_ngan_so(d.get("view", 0)))]
        if d.get("tuoi_ngay") is not None:
            so.append("tuổi {0:.1f} ngày".format(d["tuoi_ngay"]))
        if d.get("vph"):
            so.append("VPH {0:.0f}".format(d["vph"]))
        if d.get("da") == "dang_len":
            so.append("ĐÀ +{0} view/ngày (đang lên)".format(_ngan_so(d["tang_ngay"])))
        elif d.get("da") == "nguoi":
            so.append("ĐÀ ≈ 0 — NGUỘI (hai lượt quét không tăng)")
        else:
            so.append("đà chưa đo (mới một lượt quét)")
        if d.get("dot_bien"):
            so.append("đột biến ×{0:.1f} (cùng tuổi)".format(d["dot_bien"]))
        if d.get("ty_so_vuot"):
            so.append("×{0:.1f} view trung vị kênh nguồn".format(d["ty_so_vuot"]))
        if d.get("dai"):
            so.append("dài {0}".format(d["dai"]))
        kenh = "{0} ({1} sub · view trung vị {2} · {3} video{4})".format(
            d.get("kenh") or "?", _ngan_so(d.get("subs_kenh", 0)), _ngan_so(d.get("view_tv_kenh", 0)),
            d.get("so_video_kenh") or "?", " · " + d["ghi_chu_kenh"] if d.get("ghi_chu_kenh") else "")
        dong = ["[U{0}] {1}".format(i, d.get("tieu_de") or "?")]
        if d.get("tieu_de_viet"):
            dong.append("  (Việt) " + _gon(d["tieu_de_viet"], 140))
        dong.append("  kênh nguồn: " + kenh)
        dong.append("  số: " + " · ".join(so) + ("  · đăng " + d["ngay_dang"] if d.get("ngay_dang") else ""))
        cong = ["hạng công thức {0}".format(d.get("hang_cong_thuc"))]
        if d.get("nguon"):
            cong.append("công thức {0}".format(d["nguon"]))
        if str(d.get("diem", "")) != "":
            cong.append("điểm {0}".format(d["diem"]))
        if d.get("loai"):
            cong.append(str(d["loai"]))
        if d.get("cum"):
            cong.append("cụm " + "/".join(d["cum"]))
        if d.get("tuyen"):
            cong.append("tệp gán: " + d["tuyen"] + ("/" + d["chu_de"] if d.get("chu_de") else ""))
        if d.get("khan_gia_cung_xem"):
            cong.append("KHÁN GIẢ KÊNH MÌNH ĐANG XEM VIDEO NÀY (Studio)")
        if isinstance(d.get("anh_em"), dict) and d["anh_em"]:
            cong.append("cụm đang thắng ở kênh anh em {0}".format(d["anh_em"].get("kenh", "")))
        dong.append("  công thức: " + " · ".join(cong))
        if d.get("ly_do_cong_thuc"):
            dong.append("  lý do công thức: " + _gon("; ".join(d["ly_do_cong_thuc"]), 260))
        if d.get("gan_giong"):
            g = d["gan_giong"]
            dong.append("  ⚠ {0}GẦN GIỐNG thứ nhóm đã làm/đăng ({1:.0%} theo chữ): “{2}” — {3}. Có thể là "
                        "CÙNG NGUỒN hoặc cùng luận điểm; nếu trùng ý thì loại.".format(
                            "RẤT " if g["diem"] >= 0.7 else "", g["diem"], _gon(g["tieu_de"], 80), _gon(g["noi"], 60)))
        dong.append("  {0}: {1}".format(d.get("nhan_noi_dung") or "NỘI DUNG", d.get("noi_dung") or ""))
        khoi.append("\n".join(dong))
    return "\n\n".join(khoi)


def dung_loi_nhac(boi_canh: Dict[str, str], uv: Sequence[Dict[str, Any]], so_chon: int) -> str:
    if boi_canh.get("_de_bai") == DE_BAI_GON:
        return _dung_loi_nhac_gon(boi_canh, uv, so_chon)
    return DE_BAI.format(so_uv=len(uv), so_chon=max(1, int(so_chon)), thang=_ngan_so(NGUONG_THANG_48H),
                         truot=_ngan_so(NGUONG_TRUOT_48H), ung_vien=_khoi_ung_vien(uv),
                         **{k: (v or "(trống)") for k, v in boi_canh.items() if not k.startswith("_")})


# ── đọc câu trả lời ───────────────────────────────────────────────────────────


def _so_u(x: Any, n: int) -> Optional[int]:
    """"U3" / 3 / "3" → chỉ số 0-based trong `range(n)`, không thì None."""
    m = re.search(r"\d+", str(x or ""))
    if not m:
        return None
    i = int(m.group(0)) - 1
    return i if 0 <= i < n else None


def _ctr_so(x: Any) -> Optional[float]:
    """"5.2" / "5,2%" / "4–5%" / 5.2 → số (trung điểm nếu là khoảng)."""
    so = [float(s.replace(",", ".")) for s in re.findall(r"\d+(?:[.,]\d+)?", str(x if x is not None else ""))]
    so = [s for s in so if 0 < s < 40]
    if not so:
        return None
    return round(sum(so[:2]) / len(so[:2]), 2)


def _chuan_hang(x: Any) -> str:
    """"TOT"/"Tốt"/"TỐT"/"tam"/"TỆ" → TOT|TAM|TE; lạ → ""."""
    import unicodedata  # noqa: PLC0415

    s = unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode("ascii")
    s = s.strip().upper()
    return {"TOT": TOT, "TAM": TAM, "TE": TE, "GOOD": TOT, "OK": TAM, "BAD": TE}.get(s, "")


def doc_ket_qua(tho: str, uv: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Câu trả lời thô → kết quả theo hợp đồng. Không đọc được → None. Đọc được mà AI LOẠI
    HẾT → kết quả có `thu_tu` rỗng (nơi gọi phân biệt: đó là ý kiến, không phải lỗi)."""
    from .goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return None
    if not isinstance(du, dict):
        return None
    n = len(uv)
    thu_tu: List[int] = []
    ly_do: Dict[str, str] = {}
    du_doan: Dict[str, Dict[str, Any]] = {}
    loai: Dict[str, str] = {}
    for m in du.get("chon") or []:
        if not isinstance(m, dict):
            continue
        i = _so_u(m.get("u"), n)
        if i is None or i in thu_tu:
            continue
        thu_tu.append(i)
        link = uv[i]["link"]
        ly_do[link] = _gon(m.get("ly_do"), 400)
        du_doan[link] = {
            "ctr": "" if m.get("ctr") is None else str(m.get("ctr")),
            "ctr_so": _ctr_so(m.get("ctr")),
            "avd_giay": _so(m.get("avd_giay")) or None,
            "ket_cuc": _gon(m.get("ket_cuc"), 20),
            "vi_sao_no": _gon(m.get("vi_sao_no"), 400),
            "chuyen_duoc": _gon(m.get("chuyen_duoc"), 400),
            "rui_ro": _gon(m.get("rui_ro"), 400),
            "giup_ypp": _gon(m.get("giup_ypp"), 400),
        }
    bo = set()
    loai_tho = du.get("loai") if isinstance(du.get("loai"), dict) else {}
    for k, v in loai_tho.items():
        i = _so_u(k, n)
        if i is None or i in thu_tu:
            continue
        bo.add(i)
        loai[uv[i]["link"]] = _gon(v, 300)
    # Hạng chất lượng (30/09/2026): mặc định theo chỗ AI đặt — chon → TOT, con_lai → TAM, loai → TE;
    # khối "cham" (nếu có) ghi đè. Ứng viên AI bỏ sót không có hạng = CHƯA CHẤM (không phải TẠM).
    hang_i: Dict[int, str] = {i: TOT for i in thu_tu}
    for i in bo:
        hang_i[i] = TE
    for x in du.get("con_lai") or []:
        i = _so_u(x, n)
        if i is None or i in thu_tu or i in bo:
            continue
        thu_tu.append(i)
        hang_i[i] = TAM
    diem_i: Dict[int, Optional[int]] = {}
    cham = du.get("cham") if isinstance(du.get("cham"), dict) else {}
    for k, v in cham.items():
        i = _so_u(k, n)
        if i is None:
            continue
        if isinstance(v, dict):
            h, d = v.get("hang"), v.get("diem")
        elif isinstance(v, (list, tuple)):
            h, d = (v[0] if v else ""), (v[1] if len(v) > 1 else None)
        else:
            h, d = v, None
        h = _chuan_hang(h)
        if h:
            hang_i[i] = h
        try:
            diem_i[i] = max(0, min(100, int(round(float(d))))) if d is not None and str(d) != "" else None
        except (TypeError, ValueError):
            diem_i[i] = None
    # Chấm TỆ mà lỡ nằm trong thứ tự → dời sang loại (cổng chất lượng thắng chỗ đặt).
    for i in [i for i in thu_tu if hang_i.get(i) == TE]:
        thu_tu.remove(i)
        bo.add(i)
        loai[uv[i]["link"]] = ly_do.pop(uv[i]["link"], "") or "biên tập chấm TỆ"
        du_doan.pop(uv[i]["link"], None)
    if not thu_tu and not loai:
        return None
    hang = {uv[i]["link"]: h for i, h in hang_i.items()}
    diem_bt = {uv[i]["link"]: d for i, d in diem_i.items()}
    if not thu_tu:
        return {"thu_tu": [], "ly_do": {}, "du_doan": {}, "loai": loai, "hang": hang, "diem_bt": diem_bt,
                "nhan_dinh": _gon(du.get("nhan_dinh"), 800)}
    # Ứng viên AI bỏ sót (không chọn, không xếp, không loại) → nối cuối theo thứ tự công thức.
    for i in range(n):
        if i not in thu_tu and i not in bo:
            thu_tu.append(i)
    return {"thu_tu": [uv[i]["link"] for i in thu_tu], "ly_do": ly_do, "du_doan": du_doan,
            "loai": loai, "hang": hang, "diem_bt": diem_bt, "nhan_dinh": _gon(du.get("nhan_dinh"), 800)}


# ── chọn ──────────────────────────────────────────────────────────────────────


def _khoa(ma_kenh: str, uv: Sequence[Dict[str, Any]], luc: _dt.datetime, lan: int) -> str:
    h = hashlib.sha1("|".join(d["ma"] for d in uv).encode("ascii", "replace")).hexdigest()[:10]
    return "{0}:bien-tap:{1}:{2}:k{3}".format(ma_kenh or "?", luc.strftime("%Y%m%d%H%M"), h, lan)


def _luu_quyet_dinh(goc: str, ma_kenh: str, luc: _dt.datetime, ban: Dict[str, Any]) -> str:
    thu_muc = os.path.join(_nghien_cuu(goc, ma_kenh), THU_MUC)
    duong = os.path.join(thu_muc, luc.strftime("%Y-%m-%d-%H%M") + ".json")
    if os.path.exists(duong):
        duong = os.path.join(thu_muc, luc.strftime("%Y-%m-%d-%H%M%S") + ".json")
    _ghi_json(duong, ban)
    return duong


def chon(goc: str, ma_kenh: str, ung_vien_top: Sequence[Any],
         goi_chat: Optional[Callable[..., str]], *, so_chon: int = 3,
         ghi: Optional[Callable[[str], None]] = None, luu: bool = True,
         bay_gio: Optional[_dt.datetime] = None,
         so_ung_vien_toi_da: int = SO_UNG_VIEN_TOI_DA,
         danh_gia_truoc: bool = True, tra_ca_khi_loai_het: bool = False) -> Optional[Dict[str, Any]]:
    """Biên tập viên AI xếp hạng `ung_vien_top` theo nghĩa. Xem hợp đồng ở docstring đầu tệp.

    KHÔNG ném lỗi. `None` = giữ thứ tự công thức (mỗi đường ra None đều có một dòng log nói
    vì sao — không chết im lặng).
    """
    try:
        return _chon(goc, ma_kenh, ung_vien_top, goi_chat, so_chon=so_chon, ghi=ghi, luu=luu,
                     bay_gio=bay_gio, so_ung_vien_toi_da=so_ung_vien_toi_da, danh_gia_truoc=danh_gia_truoc,
                     tra_ca_khi_loai_het=tra_ca_khi_loai_het)
    except Exception as loi:  # noqa: BLE001 — lớp tư vấn, không bao giờ chặn sản xuất
        _ghi_log(ghi, "  [biên tập AI] hỏng ngoài dự kiến ({0}) — giữ thứ tự công thức.".format(str(loi)[:160]))
        return None


# ── cổng chất lượng: nhiều cửa sổ + nhớ phán quyết (30/09/2026) ────────────────


def _duong_nho_cham(goc: str, ma_kenh: str) -> str:
    return os.path.join(_nghien_cuu(goc, ma_kenh), THU_MUC, TEP_NHO_CHAM)


def doc_nho_cham(goc: str, ma_kenh: str, bay_gio: Optional[_dt.datetime] = None,
                 nho_gio: float = NHO_CHAM_GIO) -> Dict[str, Dict[str, Any]]:
    """`{mã video: phán quyết}` còn hạn (`nho_gio` giờ) — rỗng nếu chưa có/hỏng."""
    bay_gio = bay_gio or _dt.datetime.now()
    du = _doc_json(_duong_nho_cham(goc, ma_kenh))
    ra: Dict[str, Dict[str, Any]] = {}
    for ma, v in (du or {}).items() if isinstance(du, dict) else []:
        try:
            luc = _dt.datetime.fromisoformat(str(v.get("luc")))
        except (TypeError, ValueError, AttributeError):
            continue
        if 0 <= (bay_gio - luc).total_seconds() <= nho_gio * 3600 and _chuan_hang(v.get("hang")):
            ra[ma] = v
    return ra


def _ghi_nho_cham(goc: str, ma_kenh: str, moi: Dict[str, Dict[str, Any]], bay_gio: _dt.datetime) -> None:
    duong = _duong_nho_cham(goc, ma_kenh)
    du = _doc_json(duong)
    du = du if isinstance(du, dict) else {}
    du.update(moi)
    # Bỏ phán quyết quá 7 ngày cho tệp khỏi phình.
    han = bay_gio - _dt.timedelta(days=7)
    giu = {}
    for ma, v in du.items():
        try:
            if _dt.datetime.fromisoformat(str(v.get("luc"))) >= han:
                giu[ma] = v
        except (TypeError, ValueError, AttributeError):
            continue
    _ghi_json(duong, giu)


def danh_dau_te(goc: str, ma_kenh: str, ma: str, *, link: str = "", tieu_de: str = "", ly_do: str = "",
                bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Ghi phán quyết TỆ cho một ứng viên vào bộ nhớ cổng chất lượng — dùng khi lớp kiểm trùng ý
    (`core.kiem_trung_y`) bắt được thứ biên tập viên bỏ sót (đo 30/09: biên tập chấm TỐT 85 cho
    「レジで『お願いします』と言う人」 trong khi TL1 đã làm 「お店の人にも『ありがとう』と言う人」). Không ghi thì
    mỗi lượt sau lại tốn một lượt kiểm để loại đúng nguồn ấy. Không ném lỗi; trả True nếu ghi được."""
    if not ma:
        return False
    luc = bay_gio or _dt.datetime.now()
    try:
        _ghi_nho_cham(goc, ma_kenh, {ma: {"hang": TE, "diem": 0, "link": link, "tieu_de": str(tieu_de)[:80],
                                          "ly_do": "kiểm trùng ý: " + str(ly_do or "")[:300], "du_doan": {},
                                          "luc": luc.isoformat(timespec="seconds"), "mo_hinh": "kiem_trung_y"}},
                      luc)
        return True
    except Exception:  # noqa: BLE001
        return False


def _da_lam_de_kiem(goc: str, ma_kenh: str) -> List[Tuple[str, str]]:
    """ĐÚNG danh sách mà lớp kiểm trùng ý cuối (`tu_chay._chon_khong_trung_y`) dùng: tiêu đề đã làm của
    kênh + của cả nhóm — hai lớp phải phán trên cùng một danh sách, không thì biên tập viên chấm TỐT
    đúng cái lớp cuối sẽ loại."""
    ra: List[Tuple[str, str]] = []
    try:
        from . import nhom_kenh, trung_tieu_de  # noqa: PLC0415

        ra += list(trung_tieu_de.doc_tieu_de_da_lam(goc, ma_kenh))
        ra += list(nhom_kenh.tieu_de_da_lam_ca_nhom(goc, ma_kenh) or ())
    except Exception:  # noqa: BLE001
        pass
    return ra


def _loc_trung_y(goc: str, ma_kenh: str, uv: Sequence[Dict[str, Any]], goi_chat: Callable[..., str],
                 ghi: Optional[Callable[[str], None]]) -> Dict[str, Tuple[str, str]]:
    """`{mã: (tiêu đề đã làm, lý do)}` — ứng viên TRÙNG Ý thứ kênh/nhóm đã làm, hỏi TRƯỚC khi biên tập
    viên đọc (30/09/2026: chạy khô, biên tập viên chấm TỐT 3/3 nguồn TL1 và 2/2 nguồn TL3 mà lớp kiểm
    trùng ý cuối loại cả — kênh ra 0 nguồn). Cùng hàm `kiem_trung_y.kiem_trung_y` với lớp cuối, 4 luồng
    song song. Lỗi từng lượt → coi như không trùng (lớp cuối vẫn còn)."""
    da_lam = _da_lam_de_kiem(goc, ma_kenh)
    if not da_lam or not uv:
        return {}
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    from . import kiem_trung_y  # noqa: PLC0415

    def mot(d: Dict[str, Any]) -> Tuple[str, bool, str, str]:
        try:
            trung, voi, ly = kiem_trung_y.kiem_trung_y(
                goi_chat, str(d.get("tieu_de") or ""), da_lam,
                khoa="{0}:bt-trung-y:{1}".format(ma_kenh or "?", d.get("ma") or "?"))
            return d["ma"], bool(trung), str(voi or ""), str(ly or "")
        except Exception:  # noqa: BLE001
            return d["ma"], False, "", ""

    with ThreadPoolExecutor(max_workers=4) as ex:
        kq = list(ex.map(mot, uv))
    ra = {ma: (voi, ly) for ma, trung, voi, ly in kq if trung}
    if ra:
        _ghi_log(ghi, "  [biên tập AI] kiểm trùng ý TRƯỚC khi chấm: loại {0}/{1} — {2}".format(
            len(ra), len(uv), " | ".join("“{0}” ≈ “{1}”".format(
                _gon(next((d.get("tieu_de") for d in uv if d["ma"] == ma), ""), 28), _gon(v[0], 28))
                for ma, v in list(ra.items())[:5])))
    return ra


def chon_cua_so(goc: str, ma_kenh: str, ung_vien: Sequence[Any],
                goi_chat: Optional[Callable[..., str]], *, can_tot: int = 3,
                moi_cua_so: int = SO_UNG_VIEN_TOI_DA, so_cua_so: int = SO_CUA_SO_TOI_DA,
                ghi: Optional[Callable[[str], None]] = None, bay_gio: Optional[_dt.datetime] = None,
                nho_gio: float = NHO_CHAM_GIO, kiem_trung: bool = True) -> Optional[Dict[str, Any]]:
    """CỔNG CHẤT LƯỢNG NGUỒN: biên tập viên chấm TỪNG ứng viên TOT/TAM/TE theo cửa sổ `moi_cua_so`
    dòng (thứ tự công thức), mở cửa sổ kế tới khi có ≥ `can_tot` nguồn TỐT hoặc hết `so_cua_so`.

    Phán quyết từng ứng viên được nhớ `nho_gio` giờ (`bien-tap/nho-cham.json`) — lượt sau / vòng giữ
    nguồn không chấm lại cùng ứng viên. Trả hợp đồng như `chon` + `hang` {link: TOT|TAM|TE}, `diem_bt`
    {link: 0–100}; `thu_tu` = TỐT (điểm cao trước) rồi TẠM; TỆ nằm ở `loai`. `None` = không có phán
    quyết nào (mọi lượt gọi hỏng / không có goi_chat) → nơi gọi tự quyết đường lùi. Không ném lỗi."""
    try:
        return _chon_cua_so(goc, ma_kenh, ung_vien, goi_chat, can_tot=can_tot, moi_cua_so=moi_cua_so,
                            so_cua_so=so_cua_so, ghi=ghi, bay_gio=bay_gio, nho_gio=nho_gio,
                            kiem_trung=kiem_trung)
    except Exception as loi:  # noqa: BLE001
        _ghi_log(ghi, "  [biên tập AI] cổng chất lượng hỏng ngoài dự kiến ({0}).".format(str(loi)[:160]))
        return None


def _chon_cua_so(goc, ma_kenh, ung_vien, goi_chat, *, can_tot, moi_cua_so, so_cua_so, ghi, bay_gio, nho_gio,
                 kiem_trung=True):
    if goi_chat is None:
        _ghi_log(ghi, "  [biên tập AI] bỏ qua: không có hàm gọi AI (chế độ thử) — giữ thứ tự công thức.")
        return None
    luc = bay_gio or _dt.datetime.now()
    uv = _chuan_hoa_ung_vien(ung_vien)
    if not uv:
        return None
    nho = doc_nho_cham(goc, ma_kenh, luc, nho_gio)
    tu_nho = sum(1 for d in uv if d["ma"] in nho)
    phan: Dict[str, Dict[str, Any]] = {d["ma"]: dict(nho[d["ma"]]) for d in uv if d["ma"] in nho}
    # Đà tăng lúc chọn (tính mỗi lượt, KHÔNG nhớ): phán quyết cũ 18 giờ vẫn bị hạ nếu nguồn vừa nguội.
    try:
        _lam_giau(goc, ma_kenh, uv, luc, set())
    except Exception:  # noqa: BLE001
        pass
    da_theo_ma = {d["ma"]: d.get("da") for d in uv}
    theo_ma_uv = {d["ma"]: d for d in uv}

    def _vi_sao_ha(ma: str) -> str:
        """Luật cứng của cổng (máy kiểm, không tin lời AI): nguồn NGUỘI · chưa chứng minh nổ (< ×3 view
        trung vị kênh nguồn VÀ đột biến cùng tuổi < ×3) · nguồn quá ngắn (< `PHUT_NGUON_TOI_THIEU`)."""
        d = theo_ma_uv.get(ma) or {}
        if da_theo_ma.get(ma) == "nguoi":
            return "nguồn NGUỘI (đà ≈ 0 qua hai lượt quét)"
        vuot, db = float(d.get("ty_so_vuot") or 0), float(d.get("dot_bien") or 0)
        if (vuot or db) and max(vuot, db) < NGUONG_NO_THAT:
            return "nguồn chưa chứng minh nổ (×{0:.1f} kênh nguồn, đột biến ×{1:.1f} < ×{2:g})".format(
                vuot, db, NGUONG_NO_THAT)
        phut = _phut_chu(str(d.get("dai") or ""))
        if phut is not None and phut < PHUT_NGUON_TOI_THIEU:
            return "nguồn quá ngắn ({0:.0f} phút < {1})".format(phut, PHUT_NGUON_TOI_THIEU)
        return ""

    def ha_nguoi(ma: str, v: Dict[str, Any]) -> Dict[str, Any]:
        vi_sao = _vi_sao_ha(ma) if v.get("hang") == TOT else ""
        if vi_sao:
            _ghi_log(ghi, "  [biên tập AI] hạ TỐT → TẠM “{0}”: {1}.".format(_gon(v.get("tieu_de"), 50), vi_sao))
            v = dict(v, hang=TAM, ly_do="(hạ: {0}) {1}".format(vi_sao, v.get("ly_do") or ""))
        return v

    phan = {ma: ha_nguoi(ma, v) for ma, v in phan.items()}
    nhan_dinh = ""
    tep: List[str] = []
    mo_hinh = ""
    so_goi = 0

    def dem_tot() -> int:
        return sum(1 for v in phan.values() if v.get("hang") == TOT)

    cho = [d for d in uv if d["ma"] not in phan]
    while dem_tot() < can_tot and cho and so_goi < so_cua_so:
        cua_so = cho[:moi_cua_so]
        if kiem_trung:
            trung = _loc_trung_y(goc, ma_kenh, cua_so, goi_chat, ghi)
            if trung:
                te = {ma: {"hang": TE, "diem": 0, "link": next(d["link"] for d in cua_so if d["ma"] == ma),
                           "tieu_de": next(d["tieu_de"] for d in cua_so if d["ma"] == ma)[:80],
                           "ly_do": "trùng ý “{0}”: {1}".format(_gon(v[0], 60), _gon(v[1], 200)), "du_doan": {},
                           "luc": luc.isoformat(timespec="seconds"), "mo_hinh": "kiem_trung_y"}
                      for ma, v in trung.items()}
                phan.update(te)
                try:
                    _ghi_nho_cham(goc, ma_kenh, te, luc)
                except OSError:
                    pass
                cho = [d for d in cho if d["ma"] not in trung]
                cua_so = [d for d in cua_so if d["ma"] not in trung]
            if not cua_so:
                continue
        so_goi += 1
        ket = _chon(goc, ma_kenh, cua_so, goi_chat, so_chon=can_tot, ghi=ghi, luu=True,
                    bay_gio=luc + _dt.timedelta(seconds=so_goi - 1),
                    so_ung_vien_toi_da=moi_cua_so, danh_gia_truoc=(so_goi == 1), tra_ca_khi_loai_het=True)
        if ket is None:
            break  # mọi bậc mô hình hỏng: đừng đốt thêm lượt cho cửa sổ sau
        nhan_dinh = nhan_dinh or str(ket.get("nhan_dinh") or "")
        mo_hinh = mo_hinh or str(ket.get("mo_hinh") or "")
        if ket.get("tep"):
            tep.append(str(ket["tep"]))
        hang = ket.get("hang") or {}
        diem = ket.get("diem_bt") or {}
        vi_tri = {l: i for i, l in enumerate(ket.get("thu_tu") or [])}
        moi: Dict[str, Dict[str, Any]] = {}
        for d in cua_so:
            link = d["link"]
            h = hang.get(link) or (TE if link in (ket.get("loai") or {}) else "")
            if not h:
                continue  # AI bỏ sót — chưa chấm, cửa sổ sau có thể đọc lại
            dd = (ket.get("du_doan") or {}).get(link) or {}
            d_bt = diem.get(link)
            if d_bt is None:
                # Không có điểm: suy từ chỗ đặt (đầu "chon" cao nhất) để còn xếp được giữa các cửa sổ.
                d_bt = {TOT: 75, TAM: 50, TE: 10}[h] - min(20, vi_tri.get(link, 20))
            moi[d["ma"]] = {"hang": h, "diem": int(d_bt), "link": link, "tieu_de": d.get("tieu_de", "")[:80],
                            "ly_do": (ket.get("ly_do") or {}).get(link) or (ket.get("loai") or {}).get(link) or "",
                            "du_doan": dd, "luc": luc.isoformat(timespec="seconds"),
                            "mo_hinh": ket.get("mo_hinh") or ""}
        phan.update({ma: ha_nguoi(ma, v) for ma, v in moi.items()})
        try:
            _ghi_nho_cham(goc, ma_kenh, moi, luc)
        except OSError as loi:
            _ghi_log(ghi, "  [biên tập AI] không ghi được bộ nhớ phán quyết: {0}".format(str(loi)[:100]))
        da_doc = set(ket.get("ung_vien_da_doc") or [d["link"] for d in cua_so])
        cho = [d for d in cho if d["link"] not in da_doc]
        if dem_tot() < can_tot and cho and so_goi < so_cua_so:
            _ghi_log(ghi, "  [biên tập AI] mới có {0}/{1} nguồn TỐT — mở cửa sổ kế ({2} ứng viên còn chờ).".format(
                dem_tot(), can_tot, len(cho)))
    if not phan:
        return None
    theo_ma = {d["ma"]: d for d in uv}
    xep = sorted(((ma, v) for ma, v in phan.items() if ma in theo_ma and v.get("hang") in (TOT, TAM)),
                 key=lambda kv: (0 if kv[1]["hang"] == TOT else 1, -int(kv[1].get("diem") or 0),
                                 theo_ma[kv[0]]["hang_cong_thuc"]))
    ra = {"thu_tu": [theo_ma[ma]["link"] for ma, _v in xep],
          "ly_do": {theo_ma[ma]["link"]: str(v.get("ly_do") or "") for ma, v in phan.items() if ma in theo_ma},
          "du_doan": {theo_ma[ma]["link"]: v.get("du_doan") or {} for ma, v in phan.items() if ma in theo_ma},
          "hang": {theo_ma[ma]["link"]: v["hang"] for ma, v in phan.items() if ma in theo_ma},
          "diem_bt": {theo_ma[ma]["link"]: v.get("diem") for ma, v in phan.items() if ma in theo_ma},
          "loai": {theo_ma[ma]["link"]: str(v.get("ly_do") or "TỆ") for ma, v in phan.items()
                   if ma in theo_ma and v.get("hang") == TE},
          "nhan_dinh": nhan_dinh, "tep": ";".join(tep), "mo_hinh": mo_hinh,
          "so_cua_so": so_goi, "tu_nho": tu_nho}
    _ghi_log(ghi, "  [biên tập AI] cổng chất lượng: {0} TỐT · {1} TẠM · {2} TỆ ({3} lượt gọi, {4} phán quyết từ bộ nhớ).".format(
        sum(1 for v in ra["hang"].values() if v == TOT), sum(1 for v in ra["hang"].values() if v == TAM),
        sum(1 for v in ra["hang"].values() if v == TE), so_goi, tu_nho))
    return ra


def _chon(goc, ma_kenh, ung_vien_top, goi_chat, *, so_chon, ghi, luu, bay_gio,
          so_ung_vien_toi_da, danh_gia_truoc, tra_ca_khi_loai_het=False):
    if goi_chat is None:
        _ghi_log(ghi, "  [biên tập AI] bỏ qua: không có hàm gọi AI (chế độ thử) — giữ thứ tự công thức.")
        return None
    uv = _chuan_hoa_ung_vien(ung_vien_top)[:max(1, int(so_ung_vien_toi_da))]
    if not uv:
        _ghi_log(ghi, "  [biên tập AI] bỏ qua: không có ứng viên nào có link.")
        return None
    luc = bay_gio or _dt.datetime.now()
    if danh_gia_truoc:
        try:
            danh_gia_lai(goc, ma_kenh, goi_chat=goi_chat, ghi=ghi, bay_gio=luc)
        except Exception as loi:  # noqa: BLE001
            _ghi_log(ghi, "  [biên tập AI] chấm lại dự đoán cũ hỏng ({0}) — đi tiếp.".format(str(loi)[:100]))
    boi_canh = dung_boi_canh(goc, ma_kenh, bay_gio=luc)
    ma_xem = set(filter(None, boi_canh.get("_ma_khan_gia_xem", "").split(",")))
    _lam_giau(goc, ma_kenh, uv, luc, ma_xem)
    loi_nhac = dung_loi_nhac(boi_canh, uv, so_chon)
    thang = thang_mo_hinh(goc, ma_kenh)
    _ghi_log(ghi, "  [biên tập AI] {0} ứng viên · lời nhắc {1:,} ký tự · mô hình {2}…".format(
        len(uv), len(loi_nhac), thang[0]).replace(",", "."))
    ket, tho, mo_hinh_dung, loi_cuoi = None, "", "", ""
    for lan, mo_hinh in enumerate(thang[:SO_LUOT_GOI_TOI_DA], 1):
        try:
            tho = goi_chat(loi_nhac, mo_hinh=mo_hinh, khoa=_khoa(ma_kenh, uv, luc, lan),
                           toi_da_token=TOI_DA_TOKEN)
        except Exception as loi:  # noqa: BLE001
            loi_cuoi = "{0}: {1}".format(mo_hinh, str(loi)[:160])
            _ghi_log(ghi, "  [biên tập AI] {0} hỏng ({1}) — thử bậc dưới.".format(mo_hinh, str(loi)[:120]))
            continue
        ket = doc_ket_qua(tho, uv)
        if ket is not None:
            mo_hinh_dung = mo_hinh
            break
        loi_cuoi = "{0}: câu trả lời không đọc được — {1}".format(mo_hinh, _gon(tho, 160))
        _ghi_log(ghi, "  [biên tập AI] {0} trả lời không đọc được (đầu: {1}) — thử bậc dưới.".format(
            mo_hinh, _gon(tho, 120)))
    ban = {"luc": luc.isoformat(timespec="seconds"), "kenh": ma_kenh, "mo_hinh": mo_hinh_dung or "",
           "so_chon": so_chon, "ung_vien": [{k: d.get(k) for k in (
               "hang_cong_thuc", "link", "ma", "tieu_de", "kenh", "nguon", "diem", "view", "tuoi_ngay",
               "ty_so_vuot", "dot_bien", "vph", "nhan_noi_dung")} for d in uv],
           "do_dai_loi_nhac": len(loi_nhac), "tra_loi_tho": (tho or "")[:20000]}
    if ket is None:
        ban["loi"] = loi_cuoi or "AI không chọn được ứng viên nào"
        if luu:
            try:
                _luu_quyet_dinh(goc, ma_kenh, luc, ban)
            except OSError:
                pass
        _ghi_log(ghi, "  [biên tập AI] không ra quyết định ({0}) — giữ thứ tự công thức.".format(ban["loi"][:160]))
        return None
    ban.update(ket)
    if luu:
        try:
            ket["tep"] = _luu_quyet_dinh(goc, ma_kenh, luc, ban)
        except OSError as loi:
            _ghi_log(ghi, "  [biên tập AI] không ghi được tệp quyết định: {0}".format(str(loi)[:100]))
    ket["mo_hinh"] = mo_hinh_dung
    theo_link = {d["link"]: d for d in uv}
    ket["ung_vien_da_doc"] = [d["link"] for d in uv]
    if not ket["thu_tu"] and tra_ca_khi_loai_het:
        _ghi_log(ghi, "  [biên tập AI] cửa sổ này không có ứng viên dùng được — loại {0}: {1}".format(
            len(ket["loai"]), " | ".join("“{0}”: {1}".format(_gon(theo_link[l].get("tieu_de"), 30), _gon(v, 60))
                                          for l, v in list(ket["loai"].items())[:6])))
        return ket
    if not ket["thu_tu"]:
        # AI LOẠI HẾT — đó là một ý kiến (ghi lại để người đọc), nhưng lớp này không được chặn
        # sản xuất: trả None để điểm móc giữ thứ tự công thức, và nói to trong nhật ký.
        _ghi_log(ghi, "  [biên tập AI] CẢNH BÁO: AI loại cả {0} ứng viên ({1}) — giữ thứ tự công thức; "
                 "xem {2}.".format(len(uv), " | ".join(_gon(v, 60) for v in list(ket["loai"].values())[:4]),
                                   ket.get("tep") or "tệp quyết định"))
        return None
    for i, link in enumerate(ket["thu_tu"][:max(1, so_chon)], 1):
        dd = ket["du_doan"].get(link, {})
        _ghi_log(ghi, "  [biên tập AI] #{0} [{6}{7}] “{1}” (hạng công thức {2}) — {3} · dự đoán CTR {4} · {5}".format(
            i, _gon(theo_link[link].get("tieu_de"), 60), theo_link[link].get("hang_cong_thuc"),
            _gon(ket["ly_do"].get(link) or "(xếp theo thứ tự còn lại)", 160), dd.get("ctr") or "?",
            dd.get("ket_cuc") or "?", (ket.get("hang") or {}).get(link) or "chưa chấm",
            " {0}".format((ket.get("diem_bt") or {}).get(link)) if (ket.get("diem_bt") or {}).get(link) is not None else ""))
    if ket["loai"]:
        _ghi_log(ghi, "  [biên tập AI] loại {0} ứng viên: {1}".format(len(ket["loai"]), " | ".join(
            "“{0}”: {1}".format(_gon(theo_link[l].get("tieu_de"), 40), _gon(v, 80)) for l, v in ket["loai"].items())))
    return ket


# ── chấm lại dự đoán ─────────────────────────────────────────────────────────


def _cac_quyet_dinh(goc: str, ma_kenh: str) -> List[Tuple[str, Dict[str, Any]]]:
    ra = []
    for duong in sorted(glob.glob(os.path.join(_nghien_cuu(goc, ma_kenh), THU_MUC, "20*.json"))):
        du = _doc_json(duong)
        if isinstance(du, dict) and du.get("du_doan"):
            ra.append((duong, du))
    return ra


def _ket_cuc_that(imp: float) -> str:
    if imp >= NGUONG_THANG_48H:
        return "thắng"
    if imp < NGUONG_TRUOT_48H:
        return "trượt"
    return "vừa"


def _chuan_ket_cuc(x: str) -> str:
    x = (x or "").strip().lower()
    if x.startswith("th"):
        return "thắng"
    if x.startswith("tr"):
        return "trượt"
    if x.startswith("v") or "trung" in x:
        return "vừa"
    return x


DE_BAI_VI_SAO_SAI = """Bạn là biên tập viên nội dung của kênh YouTube remake tiếng Nhật {kenh}. Trước đây bạn đã chọn các
nguồn dưới đây và DỰ ĐOÁN kết quả; giờ đã có số Studio thật @48–72h. Với MỖI ca, viết MỘT câu (≤ 35 chữ,
tiếng Việt) nói vì sao dự đoán lệch (hoặc vì sao đúng) — nghĩ về lời hứa tiêu đề, tệp khán giả, bìa, cỡ kênh.
Rồi rút 1–3 BÀI HỌC ngắn cho lần chọn sau — ưu tiên bài học "nguồn KIỂU GÌ đẩy YPP tốt" (sub/1k view cao,
giờ xem nhiều), vì mục tiêu của kênh là bật kiếm tiền (1.000 sub + 4.000 giờ), không chỉ hiển thị.

{ca}

Trả DUY NHẤT JSON: {{"ca": {{"<số>": "một câu"}}, "bai_hoc": ["...", "..."]}}"""


def danh_gia_lai(goc: str, ma_kenh: str, *, goi_chat: Optional[Callable[..., str]] = None,
                 ghi: Optional[Callable[[str], None]] = None,
                 bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """So `du_doan` của các quyết định cũ với số Studio 48–72h của video đã làm từ nguồn đó.

    Ghi `bien-tap/danh-gia.json` (`{"ban_ghi": [...], "bai_hoc": [...]}`) + `BAI-HOC-BIEN-TAP.md`.
    `goi_chat` có thì hỏi thêm AI "vì sao sai" cho ca MỚI chấm (một lượt ngắn). Không ném lỗi
    cho lỗi đọc đĩa; trả `{"moi": n, "tong": n, "tep": đường}`.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    thu_muc = os.path.join(_nghien_cuu(goc, ma_kenh), THU_MUC)
    duong_dg = os.path.join(thu_muc, TEP_DANH_GIA)
    cu = _doc_json(duong_dg)
    cu = cu if isinstance(cu, dict) else {}
    ban_ghi: List[Dict[str, Any]] = list(cu.get("ban_ghi") or [])
    da_cham = {(b.get("quyet_dinh"), b.get("ma_nguon")) for b in ban_ghi}
    quyet = _cac_quyet_dinh(goc, ma_kenh)
    if not quyet:
        return {"moi": 0, "tong": len(ban_ghi), "tep": ""}
    # nguồn → gói → hồ sơ video
    goi_theo_nguon: Dict[str, str] = {}
    for ma_goi, ng in _nguon_cua_goi(goc, ma_kenh).items():
        if ng.get("ma"):
            goi_theo_nguon.setdefault(ng["ma"], ma_goi)
    ho_so = {str(h.get("ma_goi") or ""): h for h in _ho_so_video(goc, ma_kenh)}
    sub_video = _sub_theo_video(goc, ma_kenh)
    moi: List[Dict[str, Any]] = []
    for duong, qd in quyet:
        ten_qd = os.path.basename(duong)
        tieu_de = {str(u.get("link")): str(u.get("tieu_de") or "") for u in qd.get("ung_vien") or []}
        for link, dd in (qd.get("du_doan") or {}).items():
            ma = _ma_video(link)
            if not ma or (ten_qd, ma) in da_cham:
                continue
            ma_goi = goi_theo_nguon.get(ma)
            hs = ho_so.get(ma_goi or "")
            if not hs:
                continue
            cs = hs.get("chi_so") or {}
            moc = next((m for m in ("48h", "72h") if isinstance(cs.get(m), dict) and cs[m]), "")
            if not moc:
                continue
            s = cs[moc]
            imp = _so(s.get("impressions"))
            ctr = _so(s.get("ctr")) if s.get("ctr") is not None else None
            br = _ctr_browse(goc, ma_kenh, str(hs.get("video_id") or ""))
            du_ctr = dd.get("ctr_so") if dd.get("ctr_so") is not None else _ctr_so(dd.get("ctr"))
            that_kc = _ket_cuc_that(imp)
            du_kc = _chuan_ket_cuc(str(dd.get("ket_cuc") or ""))
            ctr_so_sanh = br if br is not None else ctr
            lech = round(ctr_so_sanh - du_ctr, 2) if (ctr_so_sanh is not None and du_ctr is not None) else None
            dung = (du_kc == that_kc) if du_kc else (lech is not None and abs(lech) <= 1.0)
            # 30/09/2026 — đo theo MỤC TIÊU YPP: giờ xem ≈ view × AVD, sub của video (bang-tom-tat, số mới nhất).
            vw = _so(s.get("views"))
            avd = _so(s.get("avd_giay"))
            su_tong, vw_tong = sub_video.get(str(hs.get("video_id") or ""), (0.0, 0.0))
            moi.append({
                "gio_xem": round(vw * avd / 3600.0, 1) if vw and avd else None,
                "sub_video": su_tong or None,
                "sub_1k": round(1000.0 * su_tong / vw_tong, 1) if vw_tong else None,
                "quyet_dinh": ten_qd, "ma_nguon": ma, "link_nguon": link,
                "tieu_de_nguon": tieu_de.get(link, ""), "ma_goi": ma_goi, "video_id": hs.get("video_id"),
                "tieu_de_minh": hs.get("tieu_de"), "moc": moc, "impressions": imp, "ctr_that": ctr,
                "ctr_browse": br, "avd_giay": s.get("avd_giay"), "views": s.get("views"),
                "du_doan_ctr": dd.get("ctr"), "du_doan_ket_cuc": du_kc or dd.get("ket_cuc"),
                "du_doan_avd": dd.get("avd_giay"), "ket_cuc_that": that_kc, "lech_ctr": lech,
                "dung": bool(dung), "cham_luc": bay_gio.isoformat(timespec="seconds"),
            })
    bai_hoc = list(cu.get("bai_hoc") or [])
    if moi and goi_chat is not None:
        ca = "\n".join("{0}. nguồn “{1}” → video mình “{2}”: dự đoán CTR {3} · {4}; thật @{5}: CTR {6}%{7} · "
                       "{8} hiển thị ({9}) · AVD {10}s · {11} view · giờ xem {12} · sub/1k view {13}".format(
                           i, _gon(b["tieu_de_nguon"], 70), _gon(b["tieu_de_minh"], 70), b["du_doan_ctr"],
                           b["du_doan_ket_cuc"], b["moc"], b["ctr_that"],
                           " (trang chủ {0}%)".format(b["ctr_browse"]) if b["ctr_browse"] is not None else "",
                           _ngan_so(b["impressions"]), b["ket_cuc_that"], b["avd_giay"],
                           _ngan_so(_so(b.get("views"))), b.get("gio_xem") if b.get("gio_xem") is not None else "?",
                           b.get("sub_1k") if b.get("sub_1k") is not None else "?")
                       for i, b in enumerate(moi, 1))
        try:
            from .goi_van_ban import loc_json  # noqa: PLC0415

            tho = goi_chat(DE_BAI_VI_SAO_SAI.format(kenh=ma_kenh, ca=ca), mo_hinh=thang_mo_hinh(goc, ma_kenh)[0],
                           khoa="{0}:bien-tap-cham:{1}".format(ma_kenh, bay_gio.strftime("%Y%m%d%H%M")),
                           toi_da_token=4096)  # 1500 → 4096: trần thấp làm cổng trả rỗng (30/09)
            du = loc_json(tho)
            if isinstance(du, dict):
                for k, v in (du.get("ca") or {}).items():
                    i = _so_u(k, len(moi))
                    if i is not None:
                        moi[i]["vi_sao_sai"] = _gon(v, 300)
                bai_hoc += [_gon(x, 300) for x in (du.get("bai_hoc") or []) if str(x).strip()]
        except Exception as loi:  # noqa: BLE001 — thiếu câu "vì sao" vẫn giữ số đã chấm
            _ghi_log(ghi, "  [biên tập AI] hỏi 'vì sao sai' hỏng: {0}".format(str(loi)[:100]))
    if not moi:
        return {"moi": 0, "tong": len(ban_ghi), "tep": duong_dg if ban_ghi else ""}
    ban_ghi += moi
    _ghi_json(duong_dg, {"ban_ghi": ban_ghi, "bai_hoc": bai_hoc[-20:]})
    _ghi_md_bai_hoc(os.path.join(thu_muc, TEP_BAI_HOC), ma_kenh, ban_ghi, bai_hoc, bay_gio)
    so_dung = sum(1 for b in moi if b["dung"])
    _ghi_log(ghi, "  [biên tập AI] chấm lại {0} dự đoán cũ: đúng {1}, sai {2}.".format(
        len(moi), so_dung, len(moi) - so_dung))
    return {"moi": len(moi), "tong": len(ban_ghi), "tep": duong_dg}


def _ghi_md_bai_hoc(duong: str, ma_kenh: str, ban_ghi: Sequence[Dict[str, Any]],
                    bai_hoc: Sequence[str], luc: _dt.datetime) -> None:
    dong = ["# BÀI HỌC BIÊN TẬP — {0} (file sống, máy ghi)".format(ma_kenh), "",
            "Mỗi dòng: biên tập viên AI (`core/bien_tap_content.py`) đã DỰ ĐOÁN gì cho một nguồn, và số "
            "Studio thật @48–72h của video làm từ nguồn đó. Lần chọn sau đọc lại mục này.", "",
            "Cập nhật: {0} · {1} ca · đúng {2}.".format(luc.strftime("%Y-%m-%d %H:%M"), len(ban_ghi),
                                                        sum(1 for b in ban_ghi if b.get("dung"))), "",
            "| Nguồn | Dự đoán | Thật | YPP: giờ xem · sub/1k | Kết | Vì sao |", "|---|---|---|---|---|---|"]
    for b in ban_ghi:
        dong.append("| {0} | CTR {1} · {2} | CTR {3}%{4} · {5} hiển thị @{6} | {9} giờ · {10} | {7} | {8} |".format(
            _gon(b.get("tieu_de_nguon"), 50).replace("|", "/") or b.get("ma_nguon"), b.get("du_doan_ctr"),
            b.get("du_doan_ket_cuc"), b.get("ctr_that"),
            " (trang chủ {0}%)".format(b["ctr_browse"]) if b.get("ctr_browse") is not None else "",
            _ngan_so(_so(b.get("impressions"))), b.get("moc"), "ĐÚNG" if b.get("dung") else "SAI",
            _gon(b.get("vi_sao_sai"), 160).replace("|", "/"),
            b.get("gio_xem") if b.get("gio_xem") is not None else "?",
            b.get("sub_1k") if b.get("sub_1k") is not None else "?"))
    if bai_hoc:
        dong += ["", "## Bài học", ""] + ["- " + _gon(x, 300) for x in bai_hoc[-20:]]
    _ghi_chu_tep(duong, "\n".join(dong) + "\n")
