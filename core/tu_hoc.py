"""Vòng tự học kiểu cờ vua — Đợt 1 của `workspace/THIET-KE-TU-HOC.md` (03/10/2026).

Mỗi video = một VÁN. `CHANNEL/<k>/tu-hoc/van.json` = `{mã gói: {nuoc, du_doan, ket, ket_pv, …, ket7, lech, dung}}`:

  * nước đi (`nuoc`) theo NHÃN CHUẨN của `TRUC` — ghi lúc bàn giao (`ghi_van`);
  * KẾT QUẢ CHÍNH (`cham_van`, 12/10/2026): `ket` = thang | trung_binh | truot theo THƯỚC CHUNG `core.thuoc_thang`
    (phân vị hiển thị so video của chính kênh CÙNG tuổi, phán ở ≥ 96h, đông cứng từ 168h — cùng nhãn V7, giám đốc,
    bộ não đọc), kèm `ket_pv` (phân vị), `ket_tuoi`, `ket_gia_tri`, `ket_tin` (độ tin), `ket_lui` (phán bằng bản
    72–96h), `ket_som` (phân vị tín hiệu sớm 24–72h), `thuoc` (phiên bản thước). Chấm lại MỖI lượt — nhãn cũ (kể cả
    `ket48` ngưỡng 48h đời trước) được thay; `ket48` chỉ còn là bí danh HAI MỨC của `ket` cho bộ đọc cũ. Bỏ
    `ket_tv`/`ket_muon` (cùng đại lượng, đo quá sớm / so trung vị trôi). `ket7` (giờ xem 7d) giữ để đọc, không
    còn vào bảng điểm — một thước cho mọi bộ phận;
  * bảng điểm (`bang_diem`): Beta(1+thắng, 1+trượt) mỗi (trục, giá trị CHUẨN `chuan_gia_tri`): `ket` thắng = 1,
    trung bình = ½ thắng ½ trượt, trượt = 1 (phán bằng bản 72–96h nặng `TRONG_SO_KET_LUI`), cộng số các kênh cùng
    nhóm × 0,3 làm tiên nghiệm; trục bao bì thêm `ket_ctr` (CTR so trung vị kênh, nặng 0,5); đường học hỏng →
    `canh_bao` (báo cáo ngày đọc);
  * chọn lần sau (`rut`): Thompson sampling. Sơ đồ cả vòng: `docs/VONG-HOC.md`.

Không Qt, không mạng. Thiếu số thì để trống — không bịa. Thêm trục (đợt 2): thêm tên vào `TRUC`
và đưa nhãn vào `nuoc`; mọi thứ còn lại tự chạy theo `TRUC`.
"""

from __future__ import annotations

import glob
import io
import json
import logging
import os
import random
import re
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

#: Trục nhãn. Đợt 2 (03/10/2026) thêm "kieu_tieu_de", "hook". 07/10/2026 (`workspace/chan-doan/2026-10-07.md`)
#: thêm hai trục ĐO (chưa trục nào bẻ lựa chọn — chỉ bảng điểm/bộ não đọc): "chu_bia_dai" (số ký tự chữ bìa:
#: 15–20 ký tự CTR trung vị 4,84% n=12, ≤14 ký tự 1,9–2,8% n=10) và "mo_dau" (giây của phần mở đầu trước ý 1:
#: TL4 trung vị ~59s, kênh mình có bài 110–265s).
#: 09/10/2026 (`core/do_bia.py`): trục ĐO "bia_doc_duoc" (cao|vua|thap — độ đọc được của bìa, tương phản WCAG +
#: cỡ chữ ở khung điện thoại) để học xem độ đọc được đi với CTR thế nào (40 bìa 09/10: bìa ĐẠT CTR trung vị 4,8%
#: n=11 vs TRƯỢT 3,1% n=23 — mẫu nhỏ, cần học tiếp).
#: 09/10/2026 thêm trục ĐO "chat_luong" — điểm cổng chất lượng thành phẩm (`core/kiem_chat_luong`, hồ sơ `cl_diem`):
#: để bảng điểm/bộ não thấy video điểm thấp có giữ chân/CTR kém hơn không (chưa bẻ lựa chọn).
TRUC = ("cum", "cong_thuc", "kieu_bia", "do_dai", "kieu_tieu_de", "hook", "chu_bia_dai", "mo_dau", "bia_doc_duoc",
        "chat_luong")
#: Trục "bao bì" (06/10/2026): ngoài kết quả chung (hiển thị 48h / giờ xem 7d) còn được chấm thêm bằng CTR 48h
#: so trung vị CTR của chính kênh (`ket_ctr`) — bìa và tiêu đề tác động thẳng vào CTR, hiển thị chỉ gián tiếp.
TRUC_BAO_BI = ("kieu_bia", "kieu_tieu_de", "chu_bia_dai", "bia_doc_duoc")
#: Kết quả CHÍNH theo thước chung (`core.thuoc_thang`, 12/10/2026) — thay `ket48` (ngưỡng 48h: kênh nhỏ ~9/10 ván
#: "trượt", video nổ ngày 3–5 bị chốt trượt), `ket_tv` (48h so trung vị trôi) và `ket_muon` (cửa sổ 96–240h bỏ sót
#: số 94h của chính video lớn nhất TL1). Phán bằng bản 72–96h (`ket_lui`) nặng ít hơn.
TRONG_SO_KET = 1.0
TRONG_SO_KET_LUI = 0.75
#: Các khoá kết quả `cham_van` ghi lại mỗi lượt theo thước chung.
KHOA_KET = ("ket", "ket_pv", "ket_tuoi", "ket_gia_tri", "ket_tin", "ket_lui", "ket_som", "ket48", "thuoc")
#: Khoá kết quả ĐỜI TRƯỚC (thước 48h / trung vị trôi) — xoá khỏi ván khi chấm lại.
KHOA_CU = ("ket_tv", "ket_muon")
#: Số MUỘN của hồ sơ để HIỂN THỊ (`moc_muon`, biên tập viên đọc): bản muộn nhất có số từ tuổi PHÁN được của thước
#: chung (72h — bản 94h của vidGia685d6 từng bị bỏ vì cửa sổ cũ bắt đầu 96h) tới 240h.
GIO_MUON_TU, GIO_MUON_DEN = 72.0, 240.0
TRONG_SO_CTR = 0.5
HIEN_THI_TOI_THIEU_CTR = 100   # mốc 48h ít hơn ngần này lượt hiển thị thì CTR còn nhiễu — không chấm `ket_ctr`
N_TOI_THIEU_CTR = 4            # kênh cần ngần này video đủ hiển thị mới có trung vị CTR để so
#: Tệp cảnh báo của các đường học (`canh_bao`) — mục "Tín hiệu học" của báo cáo ngày đọc lại.
TEP_CANH_BAO = os.path.join("workspace", "tu-hoc", "canh-bao.jsonl")
CANH_BAO_TOI_DA_DONG = 1000
#: Tập nhãn cố định của 2 trục đợt 2 (LLM trả kèm lúc chấm; thiếu thì lùi về regex).
KIEU_TIEU_DE = ("so_dem", "cau_hoi", "canh_bao", "bi_mat", "doi_lap", "dac_diem_nguoi", "khac")
KIEU_HOOK = ("cau_hoi", "canh_tinh_huong", "so_lieu_su_that", "canh_bao", "ke_chuyen", "khac")
_TAP_NHAN = {"kieu_tieu_de": KIEU_TIEU_DE, "hook": KIEU_HOOK}
HE_SO_CHON_NEN, HE_SO_CHON_BIEN = 0.9, 0.2   # hệ số = 0,9 + 0,2 × điểm rút ∈ [0,9; 1,1]
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


# ── cảnh báo của đường học (06/10/2026) ─────────────────────────────────────
#
# Trước đây mọi đường học bọc `except Exception: pass` — học hỏng thì im lặng, vòng học "chạy" mà không học
# gì và không ai biết. Giờ mỗi chỗ hỏng gọi `canh_bao`: vẫn KHÔNG ném lỗi (học không được chặn sản xuất),
# nhưng ghi `logging.warning` + một dòng JSONL mà báo cáo ngày (`core/bao_cao_ngay._muc_hoc`) gom lại.

def duong_canh_bao(goc: str) -> str:
    return os.path.join(goc, TEP_CANH_BAO)


def canh_bao(goc: str, nguon: str, loi: Any, ma_kenh: str = "") -> None:
    """Ghi một cảnh báo học (không bao giờ ném). `nguon` = tên ngắn của đường học hỏng."""
    chu = "{0}: {1}".format(type(loi).__name__, str(loi)[:160]) if isinstance(loi, BaseException) else str(loi)[:200]
    try:
        _log.warning("tu_hoc[%s]%s %s", nguon, " " + ma_kenh if ma_kenh else "", chu)
    except Exception:  # noqa: BLE001
        pass
    if not goc:
        return
    try:
        duong = duong_canh_bao(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with io.open(duong, "a", encoding="utf-8", newline="\n") as tep:
            tep.write(json.dumps({"luc": time.strftime("%Y-%m-%dT%H:%M:%S"), "nguon": nguon, "kenh": ma_kenh,
                                  "loi": chu}, ensure_ascii=False) + "\n")
        if os.path.getsize(duong) > CANH_BAO_TOI_DA_DONG * 400:  # cắt đuôi, giữ nửa mới nhất
            with io.open(duong, encoding="utf-8") as tep:
                dong = tep.read().splitlines()
            _ghi_nguyen_tu(duong, "\n".join(dong[-CANH_BAO_TOI_DA_DONG // 2:]) + "\n")
    except Exception:  # noqa: BLE001 — đĩa hỏng: còn log, không làm gì hơn được
        pass


def doc_canh_bao(goc: str, gio: float = 24.0, bay_gio: Optional[float] = None) -> List[Dict[str, Any]]:
    """Cảnh báo học trong `gio` giờ gần nhất (cũ → mới)."""
    moc = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime((bay_gio or time.time()) - gio * 3600.0))
    ra: List[Dict[str, Any]] = []
    try:
        with io.open(duong_canh_bao(goc), encoding="utf-8") as tep:
            for dong in tep:
                try:
                    d = json.loads(dong)
                except ValueError:
                    continue
                if isinstance(d, dict) and str(d.get("luc") or "") >= moc:
                    ra.append(d)
    except OSError:
        pass
    return ra


def ghi_van(goc: str, ma_kenh: str, ma_goi: str, nuoc: Dict[str, Any], du_doan: Optional[Dict[str, Any]] = None) -> None:
    """Ghi/cập nhật một ván. Giữ nguyên kết quả đã chấm nếu ván đã có."""
    van = doc_van(goc, ma_kenh)
    cu = van.get(ma_goi) or {}
    van[ma_goi] = dict(cu, ma_goi=ma_goi, nuoc={k: v for k, v in (nuoc or {}).items() if v not in (None, "", [])},
                       du_doan=dict(du_doan or {}))
    van[ma_goi].setdefault("ngay", time.strftime("%Y-%m-%d"))
    _luu_van(goc, ma_kenh, van)
    if not cu:  # ván MỚI: bộ não (`core/nao`) trừ 1 lượt mỗi lần `thu` khớp (ghi kèm mã gói để lúc chấm não
        #         thấy đúng video nào chịu ảnh hưởng). Lỗi = như không có bộ não, nhưng có cảnh báo.
        try:
            from . import nao  # noqa: PLC0415

            nao.tru_luot(goc, ma_kenh, van[ma_goi].get("nuoc") or {}, ma_goi=ma_goi)
        except Exception as loi:  # noqa: BLE001
            canh_bao(goc, "nao.tru_luot", loi, ma_kenh)


# ── nhãn chuẩn ──────────────────────────────────────────────────────────────

def nhom_do_dai(giay: Any) -> str:
    try:
        phut = float(giay) / 60.0
    except (TypeError, ValueError):
        return ""
    if phut <= 0:
        return ""
    return "<10" if phut < 10 else "10-15" if phut < 15 else "15-20" if phut < 20 else ">20"


def so_ky_tu_bia(chu: Any) -> int:
    """Số ký tự ĐỌC ĐƯỢC của chữ bìa — cùng cách đếm `chon_bia._chuan_hoa_chu` (bỏ khoảng trắng, dấu câu)."""
    return len(re.sub(r"[\s\W_]+", "", str(chu or "")))


def nhom_chu_bia(chu: Any) -> str:
    n = so_ky_tu_bia(chu)
    if n <= 0:
        return ""
    return "<10" if n < 10 else "10-14" if n <= 14 else "15-20" if n <= 20 else ">20"


def nhom_chat_luong(hs: Dict[str, Any]) -> str:
    """Nhóm điểm cổng chất lượng (`cl_diem`, 0–100): "<80" (≥ 1 lỗi đã tự sửa + vài cảnh báo, hoặc tệ hơn),
    "80-94", "95+" (sạch). Hồ sơ trước 09/10 không có → ""."""
    d = _so(hs.get("cl_diem"))
    if d is None:
        return ""
    return "<80" if d < 80 else "80-94" if d < 95 else "95+"


def nhom_mo_dau(hs: Dict[str, Any]) -> str:
    """Nhóm độ dài phần MỞ ĐẦU (phần 1 của `8-phan.json` trong hồ sơ) — trước ý chính đầu tiên."""
    ds = ((hs.get("phan") or {}).get("danh_sach") or []) if isinstance(hs.get("phan"), dict) else []
    giay = _so((ds[0] or {}).get("giay")) if ds and isinstance(ds[0], dict) else None
    if giay is None or giay <= 0:
        return ""
    return "<60" if giay < 60 else "60-90" if giay < 90 else ">90"


def nhan_cum(d: Dict[str, Any], cum_cua: Any = None) -> str:
    """Nhãn cụm của một nguồn. Thứ tự: nhãn ĐÃ DÙNG lúc chọn (`cum_tu_hoc`, do `chien_luoc._ap_he_so_cum` ghi —
    ván được tính cho đúng cánh tay đã nhận hệ số), cụm đã gắn trong dòng, không có thì phân theo tiêu đề
    (cùng bộ cụm V7)."""
    return nhan_cum_nguon(d, cum_cua)[0]


def nhan_cum_nguon(d: Dict[str, Any], cum_cua: Any = None) -> Tuple[str, str]:
    """`(nhãn, nguồn nhãn)` — như `nhan_cum`, kèm nguồn (`cum_y_nghia.NGUON_*`): "nguon" (nhãn sẵn trong dòng;
    `cum_tu_hoc` giữ `cum_nguon` đã ghi lúc chọn), "tu_khoa" (bộ nhận cụm V7 trên tiêu đề). Không có → ("", "")."""
    if str(d.get("cum_tu_hoc") or "").strip():
        return str(d["cum_tu_hoc"]).strip(), str(d.get("cum_nguon") or "nguon")
    cum = [str(c) for c in (d.get("cum") or []) if c]
    if cum:
        return cum[0], "nguon"
    if cum_cua is not None and d.get("tieu_de"):
        try:
            cum = [str(c) for c in (cum_cua(str(d["tieu_de"])) or []) if c]
        except Exception as loi:  # noqa: BLE001
            canh_bao("", "nhan_cum", loi)
            cum = []
    return (cum[0], "tu_khoa") if cum else ("", "")


def _mo_ta_van(nguon: Dict[str, Any], hs: Dict[str, Any]) -> str:
    """Ngữ cảnh cho LLM nhãn cụm: tiêu đề video CỦA KÊNH (nếu khác tiêu đề nguồn) + chữ bìa."""
    td_ng, td_hs = str((nguon or {}).get("tieu_de") or "").strip(), str((hs or {}).get("tieu_de") or "").strip()
    phan = []
    if td_hs and td_ng and td_hs != td_ng:
        phan.append("video của kênh: " + td_hs)
    if str((hs or {}).get("chu_bia") or "").strip():
        phan.append("chữ bìa: " + " ".join(str(hs["chu_bia"]).split()))
    return "; ".join(phan)


def _nhan_cum_van(nguon: Dict[str, Any], hs: Dict[str, Any], cum_cua: Any, bo: Any = None) -> Tuple[str, str]:
    """Nhãn cụm của một VÁN, không gọi AI: nhãn của nguồn (`nhan_cum_nguon`) → bộ nhận cụm V7 trên tiêu đề video
    của kênh (hồ sơ) → bộ nhớ nhãn theo nghĩa (`cum_y_nghia`) của tiêu đề nguồn / tiêu đề kênh."""
    nhan, tu = nhan_cum_nguon(nguon or {}, cum_cua)
    if nhan:
        return nhan, tu
    td_hs = str((hs or {}).get("tieu_de") or "").strip()
    if td_hs and cum_cua is not None:
        nhan, tu = nhan_cum_nguon({"tieu_de": td_hs}, cum_cua)
        if nhan:
            return nhan, tu
    if bo is not None:
        for td in (str((nguon or {}).get("tieu_de") or "").strip(), td_hs):
            c = bo.tra(td) if td else ""
            if c:
                return c, "y_nghia"
    return "", ""


def _bo_nho_cum(goc: str, ma_kenh: str) -> Any:
    try:
        from . import cum_y_nghia  # noqa: PLC0415

        return cum_y_nghia.BoNho(goc, ma_kenh)
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "cum_y_nghia", loi, ma_kenh)
        return None


_RE_HAU_TO_SO = re.compile(r"_\d+$")


def chuan_gia_tri(truc: str, gia_tri: Any) -> str:
    """Nhãn CHUẨN của một giá trị trục — dùng ở MỌI nơi đếm/rút/so khớp để cùng một cánh tay không bị chẻ.
    `kieu_bia`: bỏ hậu tố số biến thể (`khuon_thang_2`, `chuan_ngach_3` = cùng kiểu `khuon_thang`/`chuan_ngach`
    — `bia_theo_khuon` đánh số các tấm cùng khuôn). Mọi trục: bỏ khoảng trắng, chữ thường."""
    v = str(gia_tri or "").strip().lower()
    if truc == "kieu_bia":
        v = _RE_HAU_TO_SO.sub("", v)
    return v


def _ham_cum(goc: str, ma_kenh: str) -> Any:
    try:
        from .chien_luoc import ngu_canh  # noqa: PLC0415

        return ngu_canh.dung(goc, ma_kenh, co_v7=False).cum_cua
    except Exception as loi:  # noqa: BLE001 — không có bộ cụm: ván mới sẽ THIẾU nhãn cụm
        canh_bao(goc, "bo_cum", loi, ma_kenh)
        return None


def _doc_ho_so(goc: str, ma_kenh: str, ma_goi: str) -> Dict[str, Any]:
    try:
        from . import ho_so_video  # noqa: PLC0415

        return ho_so_video.doc_ho_so(goc, ma_kenh, ma_goi) or {}
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "doc_ho_so", loi, ma_kenh)
        return {}


def _nuoc_tu(nguon: Dict[str, Any], hs: Dict[str, Any], cum_cua: Any, bo: Any = None) -> Dict[str, Any]:
    th = hs.get("thumbnail") or {}
    kieu_tho = str(th.get("kieu") or "")
    cum, cum_nguon = _nhan_cum_van(nguon or {}, hs, cum_cua, bo)
    ra = {"cum": cum,
          "cong_thuc": str((nguon or {}).get("cong_thuc") or hs.get("cong_thuc") or (nguon or {}).get("nguon") or ""),
          "kieu_bia": chuan_gia_tri("kieu_bia", kieu_tho), "do_dai": nhom_do_dai(hs.get("thoi_luong_giay"))}
    if cum:
        ra["cum_nguon"] = cum_nguon   # tu_khoa | y_nghia | nguon — để đọc, không phải trục
    if kieu_tho and kieu_tho != ra["kieu_bia"]:
        ra["kieu_bia_tho"] = kieu_tho   # biến thể thật (`khuon_thang_2`) — để đọc, không phải trục
    ra.update(_nhan_dot2(hs))
    ra.update(_nhan_do(hs))
    return ra


def _nhan_do(hs: Dict[str, Any]) -> Dict[str, str]:
    """Các trục ĐO (`chu_bia_dai`, `mo_dau` 07/10; `bia_doc_duoc`, `chat_luong` 09/10) — tính thẳng từ hồ sơ,
    thiếu số thì không ghi."""
    th = hs.get("thumbnail") if isinstance(hs.get("thumbnail"), dict) else {}
    ra = {"chu_bia_dai": nhom_chu_bia(hs.get("chu_bia")), "mo_dau": nhom_mo_dau(hs),
          "bia_doc_duoc": str(th.get("bia_doc_duoc") or "") if th.get("bia_doc_duoc") in ("cao", "vua", "thap") else "",
          "chat_luong": nhom_chat_luong(hs)}
    return {k: v for k, v in ra.items() if v}


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
    if not bang_diem(goc, ma_kenh).get(truc) and not _nao_hieu_luc(goc, ma_kenh, truc):
        return {}
    tho = sorted({str(n) for n in nhan if n})
    rd = rut(goc, ma_kenh, truc, sorted({chuan_gia_tri(truc, n) for n in tho}), random.Random(hat))
    # Khoá trả về là NHÃN THÔ nơi gọi đưa vào (vd. `khuon_thang_2`), hệ số theo nhãn CHUẨN của nó.
    return {n: round(HE_SO_CHON_NEN + HE_SO_CHON_BIEN * rd[chuan_gia_tri(truc, n)], 3) for n in tho}


def bo_chon(goc: str, ma_kenh: str, truc: str, ban: Any, hat: str,
            trong_so_giam_khao: float = 1.0) -> Tuple[Any, Dict[str, Any]]:
    """`(sau_cham, ghi)` cho `viet_nhieu_ban.cham_va_chon(sau_cham=…)`: gắn nhãn, nhân hệ số vào điểm LLM,
    chọn lại phương án điểm cao nhất. Mọi thứ giải thích được nằm trong `ghi` (cập nhật khi callback chạy).

    20/10/2026 — `trong_so_giam_khao` (w, `core/hieu_chuan`): giám khảo không dự báo kết quả thật → điểm LLM được
    lấy MŨ w trước khi nhân hệ số Thompson (log điểm = w·log LLM + log hệ số — tổng có trọng số), để kết quả thật
    của trục nói nhiều hơn. w = 1: y như cũ."""
    ghi: Dict[str, Any] = {}
    mu = max(0.05, min(1.0, float(trong_so_giam_khao if trong_so_giam_khao is not None else 1.0)))

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
        d1 = {i: round((max(v, 0.0) ** mu if mu < 1.0 else v) * he.get(nhan[i], 1.0), 3) for i, v in d0.items()}
        moi = max(d1, key=lambda i: (d1[i], i == chon))
        ghi["he_so"] = {"truc": truc, "he_so": he, "diem_goc": {chr(65 + i): v for i, v in d0.items()},
                        "diem_sau": {chr(65 + i): v for i, v in d1.items()}, "chon_truoc": chon, "chon_sau": moi}
        if mu < 1.0:
            ghi["he_so"]["trong_so_giam_khao"] = round(mu, 3)
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
    ghi_van(goc, ma_kenh, ma_goi, _nuoc_tu(nguon or {}, _doc_ho_so(goc, ma_kenh, ma_goi), _ham_cum(goc, ma_kenh),
                                           _bo_nho_cum(goc, ma_kenh)),
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
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "so_luot", loi, ma_kenh)
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
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "trung_vi_7d_nhom", loi, ma_kenh)
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


def _bu_nhan_cum(goc: str, ma_kenh: str, van: Dict[str, Dict[str, Any]], ho_so: Dict[str, Dict[str, Any]],
                 nguon_so: Dict[str, Dict[str, Any]], cum_cua: Any, dung_ai: bool = False, bo: Any = None,
                 goi: Any = None) -> int:
    """Bù nhãn cụm cho ván THIẾU `nuoc.cum` (07/10/2026 — ván cũ được nhãn hồi tố): `_nhan_cum_van` (không AI),
    còn thiếu mà `dung_ai` thì MỘT lượt LLM theo lô (`cum_y_nghia.phan_loai`, tối đa `TOI_DA_MOT_LUOT` tiêu đề,
    qua van ví; `goi` thay được — chạy thử). Ghi `nuoc.cum` + `nuoc.cum_nguon`. Trả số ván được gắn nhãn."""
    thieu = [ma for ma, v in van.items() if not (v.get("nuoc") or {}).get("cum")
             and ((ho_so.get(ma) or {}).get("tieu_de") or (nguon_so.get(ma) or {}).get("tieu_de")
                  or (nguon_so.get(ma) or {}).get("cum_tu_hoc") or (nguon_so.get(ma) or {}).get("cum"))]
    if not thieu:
        return 0
    bo = bo if bo is not None else _bo_nho_cum(goc, ma_kenh)

    def gan(ma: str, nhan: str, tu: str) -> None:
        van[ma]["nuoc"] = dict(van[ma].get("nuoc") or {}, cum=nhan, cum_nguon=tu)

    doi = 0
    cho: List[Tuple[str, str, str]] = []
    for ma in thieu:
        ng, hs = nguon_so.get(ma) or {}, ho_so.get(ma) or {}
        nhan, tu = _nhan_cum_van(ng, hs, cum_cua, bo)
        if nhan:
            gan(ma, nhan, tu)
            doi += 1
            continue
        td = str(ng.get("tieu_de") or "").strip() or str(hs.get("tieu_de") or "").strip()
        if td:
            cho.append((ma, td, _mo_ta_van(ng, hs)))
    if cho and dung_ai and bo is not None:
        try:
            from . import cum_y_nghia  # noqa: PLC0415

            goi = goi if goi is not None else cum_y_nghia.goi_vi(goc)
            if goi is not None:  # None = ví đang chặn: lượt sau thử lại
                cum_y_nghia.phan_loai(goc, ma_kenh, [(td, mt) for _ma, td, mt in cho], goi, bo=bo)
                for ma, td, _mt in cho:
                    c = bo.tra(td)
                    if c:
                        gan(ma, c, "y_nghia")
                        doi += 1
        except Exception as loi:  # noqa: BLE001
            canh_bao(goc, "cum_y_nghia", loi, ma_kenh)
    return doi


def cham_van(goc: str, ma_kenh: str, dung_ai: bool = False) -> Dict[str, int]:
    """Bù ván từ hồ sơ video + sổ lượt cho gói chưa có ván, rồi chấm ván chưa kết luận. Không ném lỗi số liệu.
    `dung_ai=True` (vòng học thật): ván thiếu nhãn cụm được nhãn THEO NGHĨA bằng một lượt LLM (`_bu_nhan_cum`)."""
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
        if hs:  # bù hai trục đo 07/10/2026 cho ván cũ — chỉ thêm khoá còn thiếu, không đè nhãn đã ghi
            them = {k: x for k, x in _nhan_do(hs).items() if k not in (v.get("nuoc") or {})}
            if them:
                v["nuoc"] = dict(v.get("nuoc") or {}, **them)
                bu += 1
    cum_bu = 0
    if any(not (v.get("nuoc") or {}).get("cum") for v in van.values()):
        try:
            if nguon_so is None:
                nguon_so, cum_cua = _nguon_theo_goi(goc, ma_kenh), _ham_cum(goc, ma_kenh)
            cum_bu = _bu_nhan_cum(goc, ma_kenh, van, ho_so, nguon_so, cum_cua, dung_ai)
        except Exception as loi:  # noqa: BLE001 — nhãn cụm hỏng không được chặn chấm ván
            canh_bao(goc, "bu_nhan_cum", loi, ma_kenh)
    moi += bu + cum_bu
    tv7: Optional[Tuple[Optional[float], str]] = None
    so_ket = so7 = so_kd = so_dung = 0
    ket_cua = _ket_theo_van(goc, ma_kenh, van, ho_so) if van else {}
    for ma, v in van.items():
        hs = ho_so.get(ma) or {}
        if not hs:
            continue
        if ket_cua is not None:   # None = thước hỏng lượt này (đã cảnh báo): giữ nguyên nhãn, không xoá
            so_ket += 1 if _ghi_ket(v, ket_cua.get(ma)) else 0
        if v.get("ket"):
            if v.pop("khong_do", None) is not None:
                so_ket += 1
        elif "khong_do" not in v and _du_ngay(hs, v, NGAY_KHONG_DO):
            # ≥ 7 ngày mà thước chung vẫn chưa phán được (không bản chụp hợp lệ ≥ 72h): chốt "không đo được" —
            # thôi nằm trong danh sách "thiếu kết quả"; có số về sau thì nhánh trên tự gỡ cờ.
            v["khong_do"] = time.strftime("%Y-%m-%d")
            so_kd += 1
        if _moc(hs) and "lech" not in v:
            lech = _lech(v.get("du_doan") or {}, hs)
            if lech:
                v["lech"] = lech
        # Dự đoán thắng/trượt của biên tập chấm theo THƯỚC CHUNG, hai mức (thắng / không thắng) — chấm lại mỗi lượt.
        dd = _CHIEU.get(str((v.get("du_doan") or {}).get("ket_cuc") or "").strip().lower())
        dung = ((dd == "thang") == (v["ket"] == "thang")) if (dd and v.get("ket")) else None
        if dung is None and "dung" in v:
            v.pop("dung")
            so_dung += 1
        elif dung is not None and v.get("dung") is not dung:
            v["dung"] = dung
            so_dung += 1
        if not v.get("ket7") and _gio_7d(hs) is not None:
            if tv7 is None:
                tv7 = _trung_vi_7d(goc, ma_kenh, ho_so)
            if tv7[0] is not None:
                v["ket7"] = "thang" if _gio_7d(hs) >= tv7[0] else "truot"
                v["so_voi_7d"] = tv7[1]
                so7 += 1
    # Khoá đời trước (thước 48h / trung vị trôi) — xoá, không để bộ đọc nào đọc nhầm.
    so_cu = 0
    for v in van.values():
        for k in KHOA_CU:
            if k in v:
                v.pop(k)
                so_cu += 1
    soctr = _cham_tuong_doi(van, {ma: _ctr_48h(ho_so.get(ma) or {}) for ma in van}, "ket_ctr", N_TOI_THIEU_CTR)
    if moi or so_ket or so7 or soctr or so_kd or so_dung or so_cu:
        _luu_van(goc, ma_kenh, van)
    return {"van": len(van), "moi": moi, "ket": so_ket, "ket7": so7, "ket_ctr": soctr, "khong_do": so_kd,
            "dung": so_dung, "xoa_cu": so_cu, "cum_bu": cum_bu,
            "thang": sum(1 for v in van.values() if v.get("ket") == "thang"),
            "da_phan": sum(1 for v in van.values() if v.get("ket"))}


def _ket_theo_van(goc: str, ma_kenh: str, van: Dict[str, Dict[str, Any]],
                  ho_so: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """`{mã gói: thuoc_thang.KetQua}` — nhãn thước chung của video mỗi ván: lấy NGUYÊN nhãn V7 đã tính
    (`cong_thuc_v7.video_cua_kenh` → `VideoMinh.ket`, cùng nhãn mọi bộ phận đọc); video không có trong `chi-so/` (vd.
    mã có dấu "-" bị cắt tên thư mục) thì chấm chuỗi dựng từ mốc của HỒ SƠ (`moc_gio_that`) so với cùng tập video
    kênh, không làm đổi nhãn video khác. Hỏng → None + cảnh báo (ván giữ nguyên nhãn — không đọc qua
    `ket_qua.video_kenh` vì hàm ấy nuốt lỗi thành danh sách rỗng, sẽ chấm nhầm mọi ván bằng sàn tuyệt đối)."""
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415
        from .chien_luoc import ket_qua  # noqa: PLC0415

        ch, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
        vm_theo_id = {v.ma: v for v in v7.video_cua_kenh(goc, ma_kenh, ch)}
        ra: Dict[str, Any] = {}
        for ma in van:
            hs = ho_so.get(ma) or {}
            vid = str(hs.get("video_id") or "")
            k = ket_qua.ket_thuoc(vm_theo_id.get(vid) if vid else None, hs, vm_theo_id,
                                  ngay_du_phong=str((van.get(ma) or {}).get("ngay") or ""))
            if k is not None:
                ra[ma] = k
        return ra
    except Exception as loi:  # noqa: BLE001 — thước hỏng: không chấm lượt này, nhưng phải biết
        canh_bao(goc, "thuoc_thang", loi, ma_kenh)
        return None


def _ghi_ket(v: Dict[str, Any], k: Any) -> bool:
    """Ghi kết quả thước chung `k` (`thuoc_thang.KetQua` | None) vào ván `v` (khoá `KHOA_KET`). Trả True nếu đổi.
    Chưa phán → bỏ `ket`/`ket48` (nhãn 48h đời trước KHÔNG được giữ), vẫn ghi `ket_som` nếu có tín hiệu sớm."""
    from . import thuoc_thang as tt  # noqa: PLC0415

    if k is None and v.get("thuoc") == tt.PHIEN_BAN:
        return False   # đã chấm bằng thước hiện hành mà lượt này không đọc được số: GIỮ nhãn, không xoá vì lỗi tạm
    moi: Dict[str, Any] = {}
    if k is not None and getattr(k, "da_phan", False):
        moi = {"ket": k.nhan, "ket_pv": round(k.phan_vi, 1) if k.phan_vi is not None else None,
               "ket_tuoi": round(k.tuoi, 1) if k.tuoi is not None else None,
               "ket_gia_tri": round(k.gia_tri) if k.gia_tri is not None else None,
               "ket_tin": k.do_tin, "ket_lui": k.giai_doan == "phan_quyet_lui",
               "ket48": "thang" if k.nhan == tt.THANG else "truot"}
    if k is not None and getattr(k, "som_phan_vi", None) is not None:
        moi["ket_som"] = round(k.som_phan_vi, 1)
    if k is not None:
        moi["thuoc"] = tt.PHIEN_BAN
    doi = False
    for khoa in KHOA_KET:
        gt = moi.get(khoa)
        if gt is None:
            if khoa in v and khoa != "thuoc":
                v.pop(khoa)
                doi = True
        elif v.get(khoa) != gt:
            v[khoa] = gt
            doi = True
    return doi


NGAY_KHONG_DO = 7             # đăng ≥ ngần này ngày mà thước chung vẫn chưa phán được → chốt "không đo được"


GIO_XAP_XI_TOI_THIEU = 22.0   # mốc muộn nhất có số mà ≥ ngần này giờ thì dùng XẤP XỈ khi 48h/72h trống


def _moc_do_duoc(hs: Dict[str, Any]) -> Dict[str, Any]:
    """Mốc 48h (lùi 72h) CÓ số hiển thị — bản chụp mà Studio trả trống (`impressions: null`) không phải số đo.
    CHỈ để đọc CTR/hiển thị sớm (`ket_ctr`, dòng của bộ não) — KHÔNG phán thắng/trượt (đó là `core.thuoc_thang`).

    06/10/2026: 48h và 72h đều trống (Studio chỉ trả số các mốc sớm — 8 video đo được) thì lùi tới mốc MUỘN NHẤT
    ≥ `GIO_XAP_XI_TOI_THIEU` giờ có hiển thị, trả bản sao gắn `xap_xi=True` + `moc_dung` (tên khung) — số ấy
    không cùng tuổi 48h nên người gọi phải đọc cờ."""
    cs = hs.get("chi_so") or {}
    for m in ("48h", "72h"):
        if isinstance(cs.get(m), dict) and _so(cs[m].get("impressions")) is not None:
            return cs[m]
    ung = []
    for ten, gt in cs.items():
        if not isinstance(gt, dict) or _so(gt.get("impressions")) is None:
            continue
        g = _so(gt.get("moc_gio_that"))
        if g is not None and g >= GIO_XAP_XI_TOI_THIEU:
            ung.append((g, ten, gt))
    if ung:
        g, ten, gt = max(ung, key=lambda x: x[0])
        return dict(gt, xap_xi=True, moc_dung=ten)
    return {}


def moc_muon(hs: Dict[str, Any]) -> Dict[str, Any]:
    """Bản số MUỘN NHẤT của hồ sơ có hiển thị, tuổi thật (`moc_gio_that`) trong [`GIO_MUON_TU`, `GIO_MUON_DEN`] —
    bản sao kèm `moc` (tên khung: `ngay4`, `7d`, …). Không có thì `{}`. Chỉ đọc, không đoán tuổi."""
    tot: Optional[Tuple[float, str, Dict[str, Any]]] = None
    for ten, gt in (hs.get("chi_so") or {}).items():
        if not isinstance(gt, dict) or _so(gt.get("impressions")) is None:
            continue
        g = _so(gt.get("moc_gio_that"))
        if g is None or not GIO_MUON_TU <= g <= GIO_MUON_DEN:
            continue
        if tot is None or g > tot[0]:
            tot = (g, str(ten), gt)
    return dict(tot[2], moc=tot[1]) if tot else {}


def _ctr_48h(hs: Dict[str, Any]) -> Optional[float]:
    m = _moc_do_duoc(hs)
    if not m or (_so(m.get("impressions")) or 0) < HIEN_THI_TOI_THIEU_CTR:
        return None
    return _so(m.get("ctr"))


def _cham_tuong_doi(van: Dict[str, Dict[str, Any]], gia_tri: Dict[str, Optional[float]], khoa: str,
                    n_toi_thieu: int) -> int:
    """`van[ma][khoa]` = "thang" nếu số ≥ trung vị của CHÍNH kênh (cần ≥ `n_toi_thieu` ván có số), "truot" nếu
    dưới; ván không có số → bỏ khoá. Chỉ còn dùng cho `ket_ctr` (CTR 48h, trục bao bì — tín hiệu bao bì, không
    phải nhãn thắng). Trả số ván đổi nhãn."""
    so = {ma: x for ma, x in gia_tri.items() if x is not None and ma in van}
    tv = statistics.median(so.values()) if len(so) >= n_toi_thieu else None
    doi = 0
    for ma, v in van.items():
        moi = ("thang" if so[ma] >= tv else "truot") if (tv is not None and ma in so) else ""
        if moi != str(v.get(khoa) or ""):
            if moi:
                v[khoa] = moi
            else:
                v.pop(khoa, None)
            doi += 1
    return doi


# ── bảng điểm, Thompson ─────────────────────────────────────────────────────

def _o_moi() -> Dict[str, float]:
    return {"a": 0.0, "b": 0.0, "n": 0, "thang": 0, "n_ctr": 0, "thang_ctr": 0}


#: Điểm "thắng" của một nhãn thước chung khi đếm Beta (trung bình = nửa thắng nửa trượt).
_DIEM_KET = {"thang": 1.0, "trung_binh": 0.5, "truot": 0.0}


def _dem(van: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, float]]]:
    """`{trục: {giá trị CHUẨN: {a, b (thắng/trượt có trọng số), n, thang (kết quả chính), n_ctr, thang_ctr}}}`.
    Mỗi ván góp:

    * kết quả CHÍNH = `ket` của thước chung (`core.thuoc_thang`): thắng → a += w; trượt → b += w; trung bình → a, b
      mỗi bên += w/2; w = `TRONG_SO_KET` (phán bằng bản 72–96h: `TRONG_SO_KET_LUI`). Ván chưa phán: không góp;
    * trục bao bì (`TRUC_BAO_BI`): thêm `ket_ctr` (CTR 48h so trung vị kênh, nặng `TRONG_SO_CTR`)."""
    ra: Dict[str, Dict[str, Dict[str, float]]] = {}
    for v in van.values():
        kl = v.get("ket") if v.get("ket") in _DIEM_KET else None
        w = TRONG_SO_KET_LUI if v.get("ket_lui") else TRONG_SO_KET
        kc = v.get("ket_ctr") if v.get("ket_ctr") in ("thang", "truot") else None
        for truc in TRUC:
            gt = chuan_gia_tri(truc, (v.get("nuoc") or {}).get(truc))
            if not gt:
                continue
            if kl:
                o = ra.setdefault(truc, {}).setdefault(gt, _o_moi())
                o["a"] += w * _DIEM_KET[kl]
                o["b"] += w * (1.0 - _DIEM_KET[kl])
                o["n"] += 1
                o["thang"] += 1 if kl == "thang" else 0
            if kc and truc in TRUC_BAO_BI:
                o = ra.setdefault(truc, {}).setdefault(gt, _o_moi())
                o["a" if kc == "thang" else "b"] += TRONG_SO_CTR
                o["n_ctr"] += 1
                o["thang_ctr"] += 1 if kc == "thang" else 0
    return ra


#: 20/10/2026 — kết quả A/B tiêu đề YouTube (`core.ab_tieu_de.ket_qua_xong`): một cặp thắng/thua TRÊN CÙNG video là
#: bằng chứng sạch (cùng nội dung, cùng bìa, cùng giờ) → nhãn thắng a += trọng số, mỗi nhãn thua (khác nhãn) b += trọng
#: số. Thắng suy từ số / từ tiêu đề hiện tại (không có cờ của YouTube) nặng một nửa.
TRONG_SO_AB = 1.0


def _dem_ab(goc: str, ma_kenh: str) -> Dict[str, Dict[str, float]]:
    """`{nhãn kieu_tieu_de: {a, b, n_ab, thang_ab}}` từ các thử nghiệm A/B đã có bản thắng. Hỏng → {} (có cảnh báo)."""
    ra: Dict[str, Dict[str, float]] = {}
    try:
        from .ab_tieu_de import ket_qua_xong  # noqa: PLC0415
        ds = ket_qua_xong(goc, ma_kenh)
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "ab_tieu_de", loi, ma_kenh)
        return {}
    for k in ds:
        thang = chuan_nhan("kieu_tieu_de", k.get("nhan_thang"))
        if not thang:
            continue
        w = TRONG_SO_AB * (0.5 if k.get("suy_ra") else 1.0)
        thua = [t for t in (chuan_nhan("kieu_tieu_de", x) for x in k.get("nhan_thua") or []) if t and t != thang]
        if not thua:
            continue
        o = ra.setdefault(thang, {"a": 0.0, "b": 0.0, "n_ab": 0, "thang_ab": 0})
        o["a"] += w
        o["n_ab"] += 1
        o["thang_ab"] += 1
        for t in thua:
            p = ra.setdefault(t, {"a": 0.0, "b": 0.0, "n_ab": 0, "thang_ab": 0})
            p["b"] += w
            p["n_ab"] += 1
    return ra


def bang_diem(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Dict[str, float]]]:
    """`{trục: {giá trị: {"a", "b", "n", "thang", [n_tv, thang_tv, n_ctr, thang_ctr, n_ab, thang_ab]}}}` — a/b là tham
    số Beta (1 + số có trọng số của kênh + cặp thắng/thua A/B tiêu đề của kênh + tiên nghiệm nhóm × 0,3)."""
    own = _dem(doc_van(goc, ma_kenh))
    for gt, o_ab in _dem_ab(goc, ma_kenh).items():
        o = own.setdefault("kieu_tieu_de", {}).setdefault(gt, _o_moi())
        o["a"] += o_ab["a"]
        o["b"] += o_ab["b"]
        o["n_ab"] = int(o.get("n_ab") or 0) + int(o_ab["n_ab"])
        o["thang_ab"] = int(o.get("thang_ab") or 0) + int(o_ab["thang_ab"])
    nhom: Dict[str, Dict[str, Dict[str, float]]] = {}
    try:
        from .nhom_kenh import thanh_vien  # noqa: PLC0415

        for k in thanh_vien(goc, ma_kenh):
            if k == ma_kenh:
                continue
            for truc, gts in _dem(doc_van(goc, k)).items():
                for gt, o in gts.items():
                    t = nhom.setdefault(truc, {}).setdefault(gt, _o_moi())
                    t["a"] += o["a"]
                    t["b"] += o["b"]
    except Exception as loi:  # noqa: BLE001 — mất tiên nghiệm nhóm: vẫn học từ kênh mình, nhưng phải biết
        canh_bao(goc, "tien_nghiem_nhom", loi, ma_kenh)
    ra: Dict[str, Dict[str, Dict[str, float]]] = {}
    for truc in set(own) | set(nhom):
        for gt in set(own.get(truc, {})) | set(nhom.get(truc, {})):
            o = own.get(truc, {}).get(gt) or _o_moi()
            p = nhom.get(truc, {}).get(gt) or _o_moi()
            ra.setdefault(truc, {})[gt] = {"a": 1 + o["a"] + HE_SO_NHOM * p["a"], "b": 1 + o["b"] + HE_SO_NHOM * p["b"],
                                           "n": int(o["n"]), "thang": int(o["thang"])}
            if o.get("n_ctr"):
                ra[truc][gt].update({"n_ctr": int(o["n_ctr"]), "thang_ctr": int(o["thang_ctr"])})
            if o.get("n_ab"):
                ra[truc][gt].update({"n_ab": int(o["n_ab"]), "thang_ab": int(o.get("thang_ab") or 0)})
    return ra


def rut(goc: str, ma_kenh: str, truc: str, cac_gia_tri: Any, rng: Optional[random.Random] = None) -> Dict[str, float]:
    """Thompson sampling: `{giá trị: điểm rút 0..1}` (khoá = giá trị nơi gọi đưa vào, tra bảng điểm theo nhãn
    CHUẨN `chuan_gia_tri`). Giá trị chưa từng có dùng Beta(1,1)."""
    rng = rng or random.Random()
    bd = bang_diem(goc, ma_kenh).get(truc, {})
    ra = {}
    for g in cac_gia_tri:
        o = bd.get(chuan_gia_tri(truc, g)) or {}
        ra[str(g)] = rng.betavariate(o.get("a", 1.0), o.get("b", 1.0))
    try:  # bộ não (`core/nao`): `thu` còn lượt → 1,0 (trần); `tranh` còn hạn → 0,0 (sàn). Lỗi = như không có não.
        from . import nao  # noqa: PLC0415

        nao.ap_hieu_luc_rut(goc, ma_kenh, truc, ra)
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "nao.ap_hieu_luc_rut", loi, ma_kenh)
    return ra


def _nao_hieu_luc(goc: str, ma_kenh: str, truc: str) -> Dict[str, float]:
    try:
        from . import nao  # noqa: PLC0415

        return nao.hieu_luc(goc, ma_kenh, truc)
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "nao.hieu_luc", loi, ma_kenh)
        return {}


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
    from . import thuoc_thang as tt  # noqa: PLC0415

    dem = {k: sum(1 for v in van.values() if v.get("ket") == k) for k in ("thang", "trung_binh", "truot")}
    d = ["# Bảng điểm tự học — {0}".format(ma_kenh), "",
         "{0} ván; {1} đã phán theo thước chung (thắng {2}, trung bình {3}, trượt {4}), {5} có giờ xem 7 ngày "
         "(chỉ để đọc). Thước chung `core.thuoc_thang` v{6}: {7}. Thắng/n = số ván thắng / số ván đã phán; Beta: "
         "thắng 1, trung bình ½–½, trượt 1 (phán bằng bản 72–96h nặng {8:g}); bìa/tiêu đề thêm CTR 48h so trung vị "
         "kênh nặng {9:g}; số kênh cùng nhóm chỉ làm tiên nghiệm × {10}.".format(
             len(van), sum(dem.values()), dem["thang"], dem["trung_binh"], dem["truot"],
             sum(1 for v in van.values() if v.get("ket7")), tt.PHIEN_BAN, tt.MO_TA, TRONG_SO_KET_LUI, TRONG_SO_CTR,
             HE_SO_NHOM), ""]
    for truc in TRUC:
        if truc not in bd:
            continue
        d += ["## {0}".format(truc), "", "| giá trị | thắng/n | trung bình Beta |", "|---|---|---|"]
        for gt, o in sorted(bd[truc].items(), key=lambda x: -x[1]["a"] / (x[1]["a"] + x[1]["b"])):
            d.append("| {0} | {1}/{2}{4} | {3:.2f} |".format(
                gt, o["thang"], o["n"], o["a"] / (o["a"] + o["b"]),
                " (CTR ≥ trung vị {0}/{1})".format(o["thang_ctr"], o["n_ctr"]) if o.get("n_ctr") else ""))
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
    except Exception as loi:  # noqa: BLE001
        canh_bao(goc, "hieu_chinh", loi, ma_kenh)
    duong = os.path.join(_thu_muc(goc, ma_kenh), "bang-diem.md")
    _ghi_nguyen_tu(duong, "\n".join(d) + "\n")
    return duong


# ── tín hiệu học thiếu / cũ (06/10/2026) — cho mục "Tín hiệu học" của báo cáo ngày ─────────

#: Video đăng quá ngần này ngày mà ván vẫn chưa được thước chung phán (cần bản ≥ 96h, lùi 72h) → THIẾU SỐ.
#: Tên giữ cho bộ đọc cũ (báo cáo ngày) — nghĩa nay là "thiếu kết quả", không còn là mốc 48h.
NGAY_CHO_48H = 5
GIO_VAN_CU = 48.0     # `van.json` không được chấm lại quá ngần này giờ → vòng học không chạy cho kênh này


def _ngay_dang(hs: Dict[str, Any], v: Dict[str, Any]) -> Optional[str]:
    """Ngày đăng `YYYY-MM-DD` của một ván: lịch đăng của hồ sơ (dd/mm/yyyy), ngày đăng ISO, không thì ngày ghi ván."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(hs.get("lich_dang") or ""))
    if m:
        return "{0}-{1:02d}-{2:02d}".format(m.group(3), int(m.group(2)), int(m.group(1)))
    for x in (hs.get("ngay_dang"), v.get("ngay")):
        if re.match(r"\d{4}-\d\d-\d\d", str(x or "")):
            return str(x)[:10]
    return None


def _du_ngay(hs: Dict[str, Any], v: Dict[str, Any], so_ngay: int, bay_gio: Optional[float] = None) -> bool:
    """Video đăng đã ≥ `so_ngay` ngày (theo `_ngay_dang`); không biết ngày đăng → False."""
    nd = _ngay_dang(hs, v)
    if not nd:
        return False
    han = time.strftime("%Y-%m-%d", time.localtime((bay_gio or time.time()) - so_ngay * 86400))
    return nd <= han


def tin_hieu_thieu(goc: str, ma_kenh: str, bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Đo độ "kín" của vòng học một kênh, chỉ đọc đĩa: `{van, co_ket, thieu_48h: [mã gói], khong_cum, van_cu_gio}`.

    * `thieu_48h` (tên cũ, nghĩa: THIẾU KẾT QUẢ) — video đăng ≥ `NGAY_CHO_48H` ngày mà thước chung chưa phán được:
      số Studio muộn (≥ 72–96h) không về / không nối được; vòng học đang mù với video đó. `studio_rong` = không mốc
      ≥ 22h nào có số; `cho_moc` = có số sớm mà thiếu bản muộn;
    * `khong_cum`  — ván không có nhãn cụm: trục cụm không học được gì từ video này;
    * `van_cu_gio` — giờ kể từ lần chấm ván cuối (vòng học ghi `bang-diem.md` MỖI lượt, kể cả khi không có số
      mới; None = kênh chưa từng chấm)."""
    from .chien_luoc import ket_qua  # noqa: PLC0415

    bay_gio = bay_gio or time.time()
    van = doc_van(goc, ma_kenh)
    ho_so = ket_qua.ho_so_theo_goi(goc, ma_kenh) if van else {}
    han = time.strftime("%Y-%m-%d", time.localtime(bay_gio - NGAY_CHO_48H * 86400))
    thieu = sorted(ma for ma, v in van.items() if not v.get("ket") and not v.get("khong_do")
                   and (_ngay_dang(ho_so.get(ma) or {}, v) or "9") <= han)
    # Tách hai nguyên nhân (06/10/2026): Studio RỖNG (không mốc ≥ 22h nào có hiển thị) khác CHƯA TỚI MỐC (có số
    # sớm nhưng thiếu bản muộn để phán) — cách xử lý khác nhau nên báo cáo không gộp.
    studio_rong = [ma for ma in thieu if not _moc_do_duoc(ho_so.get(ma) or {})]
    cho_moc = [ma for ma in thieu if ma not in set(studio_rong)]
    khong_do = sorted(ma for ma, v in van.items() if v.get("khong_do") and not v.get("ket"))
    try:
        cu: Optional[float] = round((bay_gio - os.path.getmtime(
            os.path.join(_thu_muc(goc, ma_kenh), "bang-diem.md"))) / 3600.0, 1)
    except OSError:
        cu = None
    return {"van": len(van), "co_ket": sum(1 for v in van.values() if v.get("ket")),
            "thieu_48h": thieu, "studio_rong": studio_rong, "cho_moc": cho_moc, "khong_do": khong_do,
            "khong_cum": sum(1 for v in van.values() if not (v.get("nuoc") or {}).get("cum")),
            "van_cu_gio": cu}
