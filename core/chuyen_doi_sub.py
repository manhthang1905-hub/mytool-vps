"""CHUYỂN ĐỔI SUB: đo đăng ký / 1.000 view và các đòn bẩy kéo đăng ký (12/10/2026).

═══ VÌ SAO ═══

Hai kênh gần YPP nhất đều đang thiếu SUB, không thiếu giờ xem. Phép đo cũ báo một kênh
"sub/1k view ≈ 0,0". Đó là lỗi đo, không phải số thật:
- Sau khoảng 24 giờ, Studio chỉ trả gói tab Reach (`yta_web/join`). Gói này KHÔNG có
  `SUBSCRIBERS_NET_CHANGE`.
- Nên ô "Đăng ký" ở bản chụp mới nhất bỏ trống.
- Bộ đọc cũ (`ket_qua._sub_theo_video`) đọc ô trống thành 0 rồi chia cho lượt xem MỚI NHẤT.

Từ nay số sub của video lấy CẶP (đăng ký, lượt xem) của CÙNG một bản chụp có số đăng ký,
tức bản có nhiều lượt xem nhất. Hai cột `COT_SUB`/`COT_XEM` của `bang-tom-tat.csv` do
`chi_so_ytb.xuat_tom_tat` ghi.

═══ ĐÒN BẨY (mỗi kênh tự bật/tắt trong `kenh.yaml: chuyen_doi_sub`) ═══

    chuyen_doi_sub:
      bat: auto          # auto = bật khi kênh trong tầm YPP (xem `trong_tam_ypp`); true / false
      cta_giua: ab       # câu mời đăng ký giữa bài + câu hứa video tiếp (A/B) — ab | true | false
      binh_luan: ab      # bình luận mồi: câu hỏi dễ trả lời + lời mời đăng ký nhẹ (A/B)
      ti_le_bat: 0.7     # phần lượt được BẬT khi `ab`; phần còn lại là nhóm đối chứng
      mo_ta_lien_ket: true   # mô tả có link một video liên quan của kênh (AI chọn theo nghĩa)

Lượt nào bật hay tắt thì ghi ở `<lượt>/1-don-bay-sub.json` (`TEP_LUOT`). Hồ sơ video chép
tệp này thành khoá `don_bay_sub`. `danh_gia_ab` so sub/1k của hai nhóm, dùng chính số đo
mới ở trên. Vòng học (`ti_le_thich_ung`): A/B phân được thắng thua (khoảng tin ~90%, mỗi nhóm
≥ `N_AB_TOI_THIEU` video) thì lượt mới dồn 90% về nhánh thắng, vẫn giữ 10% để đo tiếp.
Kết quả hiện ở mục DANH MỤC của chương trình não (`dong_nao`).

Không đụng luật mở đầu:
- Câu mời giữa bài nằm ở 25–40% bài và không bao giờ rơi vào `giay_mo_dau_toi_da` giây đầu.
- `kiem_chat_luong` vẫn cảnh báo câu rào trong ~60 giây đầu như cũ.

    python -m core.chuyen_doi_sub [--kenh K] [--chi-tiet]   # bảng chuyển đổi + tương quan + A/B (chỉ đọc)
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import os
import re
import statistics
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

#: Hai cột mới của `bang-tom-tat.csv`: số đăng ký và lượt xem của CÙNG bản chụp có số đăng ký.
COT_SUB = "ĐK đo được"
COT_XEM = "Xem cùng lúc ĐK"
COT_MOC = "Mốc ĐK"
TEP_LUOT = "1-don-bay-sub.json"
KHOA_HO_SO = "don_bay_sub"
DON_BAY = ("cta_giua", "binh_luan")
TEN_DON_BAY = {"cta_giua": "CTA giữa bài + hứa video tiếp", "binh_luan": "bình luận mời trả lời + đăng ký"}
MAC_DINH: Dict[str, Any] = {"bat": "auto", "cta_giua": "ab", "binh_luan": "ab", "ti_le_bat": 0.7,
                            "mo_ta_lien_ket": True}
#: "Trong tầm YPP": còn ≤ `TAM_NGAY` ngày tới mốc ở tốc độ hiện tại, hoặc đã ≥ một nửa đường (sub/giờ).
TAM_NGAY = 90.0
TAM_SUB = 500
TAM_GIO = 3000.0
#: Video phải có ít nhất chừng này lượt xem (ở bản chụp có số đăng ký) mới vào phép tính sub/1k.
XEM_TOI_THIEU = 300
#: Mỗi nhóm A/B cần chừng này video đo được mới được nói "thắng/thua".
N_AB_TOI_THIEU = 6
#: Cửa sổ câu mời giữa bài (phần trăm độ dài bài).
CTA_TU, CTA_DEN = 25, 40


# ── tiện ích ─────────────────────────────────────────────────────────────────

def _so(x: Any) -> Optional[float]:
    if x is None or isinstance(x, bool):
        return None
    s = str(x).strip().replace(",", "").rstrip("%")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _doc_json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(p: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    tam = p + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def _doc_csv(p: str) -> List[Dict[str, str]]:
    try:
        with io.open(p, encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep))
    except (OSError, ValueError, csv.Error):
        return []


def _f(x: Any, so_le: int = 1) -> str:
    if x is None:
        return "?"
    try:
        return ("{0:,.%df}" % so_le).format(float(x)).replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "?"


def _thu_muc_kenh(goc: str, kenh: str) -> str:
    return os.path.join(goc, "CHANNEL", kenh)


# ── 1. ĐO: sub / 1.000 view ──────────────────────────────────────────────────

def cap_sub_xem(dong: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """(đăng ký, lượt xem) của CÙNG một bản chụp, từ một dòng `bang-tom-tat.csv`, hoặc None khi chưa đo được sub.

    Ưu tiên hai cột mới. Bảng cũ chưa có hai cột đó thì dùng "Đăng ký"/"Lượt xem", nhưng chỉ khi ô
    "Đăng ký" CÓ số: ô trống nghĩa là "Studio không trả" (gói join), không phải 0."""
    su, xem = _so(dong.get(COT_SUB)), _so(dong.get(COT_XEM))
    if su is not None and xem:
        return su, xem
    if COT_SUB in dong and str(dong.get(COT_SUB) or "").strip():
        return None
    su, xem = _so(dong.get("Đăng ký")), _so(dong.get("Lượt xem"))
    if su is None or not xem:
        return None
    return su, xem


def sub_theo_video(goc: str, kenh: str) -> Dict[str, Tuple[float, float]]:
    """`{video_id: (đăng ký, lượt xem cùng bản chụp)}`. Chỉ video ĐO ĐƯỢC sub; video chưa đo được thì vắng mặt."""
    ra: Dict[str, Tuple[float, float]] = {}
    for d in _doc_csv(os.path.join(_thu_muc_kenh(goc, kenh), "chi-so", "bang-tom-tat.csv")):
        vid = str(d.get("Mã video") or "").strip()
        cap = cap_sub_xem(d) if vid else None
        if cap:
            ra[vid] = cap
    return ra


def chon_ban_do_sub(ban_ghi: Sequence[Any]) -> Optional[Any]:
    """Trong các bản chụp của MỘT video, chọn bản CÓ số đăng ký và nhiều lượt xem nhất.

    Lượt xem cộng dồn, nên bản nhiều lượt xem nhất là bản muộn nhất. Cách so này đúng cả với bản
    chụp tay không có mốc giờ. Dùng ở `chi_so_ytb.xuat_tom_tat`."""
    co = [b for b in ban_ghi if getattr(b, "subs", None) is not None and (getattr(b, "views", None) or 0) > 0]
    if not co:
        return None
    return max(co, key=lambda b: (float(b.views or 0), getattr(b, "moc_gio", None) or -1))


def sub_1k_kenh(goc: str, kenh: str) -> Dict[str, Any]:
    """Sub/1k CẤP KÊNH từ chuỗi ngày Studio (`SUBSCRIBERS_NET_CHANGE` ÷ `EXTERNAL_VIEWS`):
    `{tb7, tb7_truoc, tb28, sub7, xem7, ngay_cuoi}`. Thiếu chuỗi thì các số là None."""
    ra: Dict[str, Any] = {"tb7": None, "tb7_truoc": None, "tb28": None, "sub7": None, "xem7": None, "ngay_cuoi": ""}
    try:
        from . import chi_so_kenh  # noqa: PLC0415

        s = chi_so_kenh.chuoi_ngay(goc, kenh, "SUBSCRIBERS_NET_CHANGE")
        v = chi_so_kenh.chuoi_ngay(goc, kenh, "EXTERNAL_VIEWS")
    except Exception:  # noqa: BLE001 — số cấp kênh là phụ
        return ra
    ngay = sorted(set(s) & set(v))
    if not ngay:
        return ra

    def ti_le(ds: Sequence[str]) -> Tuple[Optional[float], float, float]:
        xem, sub = sum(v[n] for n in ds), sum(s[n] for n in ds)
        return (round(1000.0 * sub / xem, 2) if xem > 0 else None), sub, xem

    ra["ngay_cuoi"] = ngay[-1]
    if len(ngay) >= 3:
        ra["tb7"], ra["sub7"], ra["xem7"] = ti_le(ngay[-7:])
    if len(ngay) >= 10:
        ra["tb7_truoc"] = ti_le(ngay[-14:-7])[0]
    ra["tb28"] = ti_le(ngay[-28:])[0]
    return ra


# ── 2. CÀI ĐẶT + CHIA NHÁNH A/B ─────────────────────────────────────────────

def cai_dat(k: Any) -> Dict[str, Any]:
    """`MAC_DINH` đè bằng khối `chuyen_doi_sub` của kenh.yaml (bỏ khoá lạ)."""
    ra = dict(MAC_DINH)
    tho = getattr(k, "chuyen_doi_sub", None)
    if isinstance(tho, dict):
        for kh, gt in tho.items():
            if kh in MAC_DINH and gt is not None:
                ra[kh] = gt
    try:
        ra["ti_le_bat"] = max(0.0, min(1.0, float(ra["ti_le_bat"])))
    except (TypeError, ValueError):
        ra["ti_le_bat"] = MAC_DINH["ti_le_bat"]
    return ra


def _che_do(gt: Any) -> str:
    """true/false/ab/auto (chữ hay bool) → "bat" | "tat" | "ab" | "auto"."""
    if gt is True:
        return "bat"
    if gt is False or gt is None:
        return "tat"
    s = str(gt).strip().lower()
    if s in ("ab", "a/b", "thu"):
        return "ab"
    if s in ("auto", "tu_dong", "tự động"):
        return "auto"
    if s in ("true", "yes", "1", "bat", "bật", "on"):
        return "bat"
    return "tat"


def trong_tam_ypp(goc: str, kenh: str, bay_gio: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """(có trong tầm YPP không, lý do). Luật chung cho mọi kênh, mọi ngách: chưa đạt YPP, và còn
    ≤ `TAM_NGAY` ngày tới mốc HOẶC đã có ≥ `TAM_SUB` sub hay ≥ `TAM_GIO` giờ xem. Đọc số hỏng → (False, lý do)."""
    try:
        from . import ypp  # noqa: PLC0415

        y = ypp.du_bao(goc, kenh, bay_gio)
    except Exception as loi:  # noqa: BLE001
        return False, "không đọc được YPP ({0})".format(str(loi)[:60])
    if y.get("trang_thai") == "dat":
        return False, "đã đủ YPP"
    toi, dk, gio = _so(y.get("ngay_toi")), _so(y.get("dang_ky")) or 0.0, _so(y.get("gio")) or 0.0
    if toi is not None and toi <= TAM_NGAY:
        return True, "còn ~{0:.0f} ngày tới YPP".format(toi)
    if dk >= TAM_SUB or gio >= TAM_GIO:
        return True, "{0:.0f} sub · {1:.0f} giờ xem".format(dk, gio)
    return False, "chưa trong tầm YPP ({0:.0f} sub, {1:.0f} giờ, ETA {2})".format(
        dk, gio, "?" if toi is None else "{0:.0f} ngày".format(toi))


def kenh_bat(goc: str, k: Any, bay_gio: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    cd = _che_do(cai_dat(k).get("bat"))
    if cd == "bat":
        return True, "kenh.yaml bật"
    if cd in ("tat", "ab"):
        return False, "kenh.yaml tắt"
    return trong_tam_ypp(goc, str(getattr(k, "ma", "") or ""), bay_gio)


def chia_nhanh(kenh: str, ma_luot: str, don_bay: str, ti_le: float) -> bool:
    """Nhánh BẬT/TẮT cố định theo (kênh, lượt, đòn bẩy): chạy lại lượt thì ra đúng nhánh cũ.

    Lượt đánh số thì dùng dãy Weyl (số lượt × tỉ lệ vàng): các nhánh xen đều nhau, tránh chuỗi dài
    toàn bật hoặc toàn tắt như khi bốc thăm. Lượt không đánh số thì băm."""
    muoi = int(hashlib.sha1("{0}|{1}".format(don_bay, kenh).encode("utf-8")).hexdigest()[:8], 16) / float(1 << 32)
    try:
        u = (int(str(ma_luot).strip()) * 0.6180339887498949 + muoi) % 1.0
    except ValueError:
        u = int(hashlib.sha1("{0}|{1}|{2}".format(don_bay, kenh, ma_luot).encode("utf-8")).hexdigest()[:8],
                16) / float(1 << 32)
    return u < ti_le


#: Vòng học của đòn bẩy: A/B đã phân thắng thua thì dồn lượt về nhánh thắng, nhưng vẫn giữ một phần nhỏ nhánh kia
#: để còn đo tiếp (kênh đổi ngách, khán giả đổi thì kết luận cũ có thể sai).
TI_LE_THANG, TI_LE_THUA = 0.9, 0.1


def ti_le_thich_ung(ti_le_khai: float, ket_ab: Dict[str, Any]) -> Tuple[float, str]:
    """(tỉ lệ bật dùng cho lượt mới, lý do). Theo `danh_gia_ab`: "BẬT thắng" → `TI_LE_THANG`, "BẬT thua" →
    `TI_LE_THUA`, chưa phân thắng thua → tỉ lệ khai trong kenh.yaml."""
    ket = str((ket_ab or {}).get("ket") or "")
    if ket == "BẬT thắng":
        return max(ti_le_khai, TI_LE_THANG), "A/B: nhánh bật thắng ×{0}".format(_f(ket_ab.get("ti_so"), 2))
    if ket == "BẬT thua":
        return min(ti_le_khai, TI_LE_THUA), "A/B: nhánh bật thua ×{0}".format(_f(ket_ab.get("ti_so"), 2))
    return ti_le_khai, "tỉ lệ khai ({0})".format(ket or "chưa đo")


def doc_quyet_dinh(thu_muc_luot: str) -> Dict[str, Any]:
    d = _doc_json(os.path.join(thu_muc_luot, TEP_LUOT))
    return d if isinstance(d, dict) else {}


def nhanh_bat(qd: Dict[str, Any], don_bay: str) -> bool:
    return bool(((qd or {}).get(don_bay) or {}).get("bat"))


def quyet_dinh_luot(goc: str, k: Any, thu_muc_luot: str, ma_kenh: str, ma_luot: str, *,
                    bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Chốt nhánh của lượt, MỘT LẦN rồi ghi ra `TEP_LUOT`. Chạy lại lượt thì đọc lại đúng quyết định cũ,
    kể cả khi trạng thái YPP đã đổi. Hỏng ghi đĩa thì vẫn trả quyết định, không làm vỡ lượt."""
    cu = doc_quyet_dinh(thu_muc_luot)
    if cu.get("phien") and all(db in cu for db in DON_BAY):
        return cu
    bg = bay_gio or _dt.datetime.now()
    cd = cai_dat(k)
    bat, ly_do = kenh_bat(goc, k, bg)
    qd: Dict[str, Any] = {"phien": 1, "kenh": ma_kenh, "luot": str(ma_luot), "luc": bg.isoformat(timespec="seconds"),
                          "kenh_bat": bat, "ly_do": ly_do, "ti_le": cd["ti_le_bat"]}
    ab: Optional[Dict[str, Dict[str, Any]]] = None
    for db in DON_BAY:
        che = _che_do(cd.get(db))
        if not bat:
            qd[db] = {"bat": False, "che_do": "kenh_tat"}
        elif che == "ab":
            if ab is None:
                try:
                    ab = danh_gia_ab(goc, ma_kenh)
                except Exception:  # noqa: BLE001 — đo hỏng thì chia theo tỉ lệ khai
                    ab = {}
            ti_le, vi_sao = ti_le_thich_ung(cd["ti_le_bat"], (ab or {}).get(db) or {})
            qd[db] = {"bat": chia_nhanh(ma_kenh, ma_luot, db, ti_le), "che_do": "ab", "ti_le": ti_le,
                      "vi_sao": vi_sao}
        else:
            qd[db] = {"bat": che == "bat", "che_do": che}
    if nhanh_bat(qd, "cta_giua"):
        # Video đã có của kênh, cho câu hứa "video tiếp" ở đoạn kết. Chốt cùng lúc để chạy lại thì lời nhắc giữ y nguyên.
        try:
            qd["lien_quan"] = [v["tieu_de"] for v in video_lien_quan(goc, ma_kenh, toi_da=6)]
        except Exception:  # noqa: BLE001
            qd["lien_quan"] = []
    try:
        _ghi_json(os.path.join(thu_muc_luot, TEP_LUOT), qd)
    except OSError:
        pass
    return qd


# ── 3. LUẬT LỜI NHẮC ─────────────────────────────────────────────────────────

LUAT_DANG_KY = (
    "═══ LUẬT MỜI ĐĂNG KÝ (áp cho mọi bản viết) ═══\n"
    "1. Đúng MỘT câu mời đăng ký GIỮA BÀI, đặt ngay sau ý giá trị lớn đầu tiên, khoảng {tu}–{den}% bài "
    "(~ký tự thứ {kt_tu}–{kt_den} tính từ đầu). KHÔNG BAO GIỜ đặt trong {giay} giây đầu (~{kt_dau} ký tự). "
    "Câu ấy nói GIÁ TRỊ trước: người xem vừa nhận được gì, và kênh sẽ còn cho họ gì nữa (cùng chủ đề, lời hứa "
    "cụ thể). Sau đó mới mời đăng ký. Dài 1–2 câu, đúng giọng kênh, tự nhiên như đang trò chuyện. Không van nài, "
    "không gộp like/chia sẻ/bật chuông. Nói xong thì vào lại mạch bài ngay.\n"
    "2. Đoạn KẾT có một câu hứa video TIẾP THEO liên quan, theo khung 'chuỗi': nói rõ khía cạnh kế tiếp nối từ chính "
    "bài này mà người xem sẽ muốn biết{lien_quan}. Không hứa ngày, không bịa tên video. Kèm một lời mời đăng ký ngắn "
    "để không lỡ phần ấy.\n"
    "3. Ngoài hai chỗ trên không có lời mời đăng ký nào khác. Viết bằng đúng ngôn ngữ và giọng của bài.\n")

LUAT_GIU_DANG_KY = (
    "═══ GIỮ ĐÒN BẨY ĐĂNG KÝ ═══\n"
    "Bài có MỘT câu mời đăng ký giữa bài (ngay sau ý giá trị đầu tiên) và một câu hứa video tiếp theo ở đoạn kết. "
    "GIỮ cả hai (được sửa chữ cho mượt). Không xoá, không dời vào {giay} giây đầu, không thêm lời mời nào khác.\n")

LUAT_BINH_LUAN = (
    "═══ SUBSCRIBER LEVER (applies on top of the rules above) ═══\n"
    "- The question must be answerable in ONE short line (pick A or B, or one personal moment), so a viewer can "
    "reply right away.\n"
    "- LAST line: one soft, value-first subscribe line tied to what comes next on the channel (e.g. follow the "
    "channel so you don't miss the next part about <the related next angle>). No begging, no links.\n"
    "- Keep the whole comment under 400 characters, same language as the rest.\n")

#: Ô DỮ LIỆU dài: luật phải nằm TRƯỚC khối dữ liệu đầu tiên (cùng luật với `auto_khau._O_DU_LIEU`).
_O_DU_LIEU = ("<<COMPETITOR_TRANSCRIPT>>", "<<DRAFT>>", "<<THAN_BAI>>", "<<TRANSCRIPT_SAMPLE>>")


def chen_luat(khuon: str, luat: str, o_giu: str) -> str:
    """Đưa `luat` vào lời nhắc. Có ô `o_giu` thì thay vào đó. Không có thì chèn ngay trước khối dữ liệu đầu tiên,
    kể cả dòng nhãn "…:" đứng trên nó. Không có khối dữ liệu thì nối cuối. Lời nhắc rỗng thì giữ rỗng."""
    if not (khuon or "").strip():
        return khuon
    if o_giu in khuon:
        return khuon.replace(o_giu, luat)
    if not luat:
        return khuon
    vt = [khuon.find(o) for o in _O_DU_LIEU if o in khuon]
    if not vt:
        return khuon.rstrip() + "\n\n" + luat
    p = khuon.rfind("\n", 0, min(vt)) + 1
    if khuon[p:min(vt)].strip():
        return khuon[:min(vt)] + "\n" + luat + "\n" + khuon[min(vt):]
    dong = khuon[:p].split("\n")[:-1]
    j = len(dong)
    while j > 0 and not dong[j - 1].strip():
        j -= 1
    if j > 0 and (dong[j - 1].rstrip().endswith((":", "：")) or dong[j - 1].lstrip().startswith("#")):
        # Dòng nhãn "…:" hay tiêu đề markdown "## Script" đứng trên khối dữ liệu → luật nằm TRÊN nhãn ấy, không chen
        # giữa nhãn và bài (AI dễ đọc luật thành một phần của bài).
        p = len("\n".join(dong[:j - 1])) + (1 if j > 1 else 0)
    return khuon[:p] + luat + "\n" + khuon[p:]


def _nhip(k: Any) -> float:
    try:
        return float(getattr(k, "ky_tu_moi_phut", 0) or 0) or 300.0
    except (TypeError, ValueError):
        return 300.0


def _giay_dau(k: Any) -> int:
    try:
        return max(20, min(180, int(getattr(k, "giay_mo_dau_toi_da", 60) or 60)))
    except (TypeError, ValueError):
        return 60


def video_lien_quan(goc: str, kenh: str, *, toi_da: int = 6, bo_tieu_de: str = "") -> List[Dict[str, Any]]:
    """Video ĐÃ ĐĂNG của kênh, xếp theo lượt xem: `[{id, tieu_de, xem}]`. Bỏ video trùng `bo_tieu_de`.
    Dùng làm ngữ cảnh cho câu hứa video tiếp và cho link ở mô tả."""
    ds = []
    for d in _doc_csv(os.path.join(_thu_muc_kenh(goc, kenh), "chi-so", "bang-tom-tat.csv")):
        vid, td, xem = str(d.get("Mã video") or "").strip(), str(d.get("Tiêu đề") or "").strip(), _so(d.get("Lượt xem"))
        if not vid or not td or td == vid or not xem or (bo_tieu_de and td.strip() == bo_tieu_de.strip()):
            continue
        ds.append({"id": vid, "tieu_de": td, "xem": xem})
    ds.sort(key=lambda x: -x["xem"])
    return ds[:max(0, toi_da)]


def luat_dang_ky(k: Any, muc_tieu_kt: int = 0, lien_quan: Sequence[str] = ()) -> str:
    giay = _giay_dau(k)
    nhip = _nhip(k)
    kt_dau = int(round(nhip * giay / 60.0 / 10.0)) * 10
    dai = int(muc_tieu_kt or 0) or int(nhip * 12)
    kt_tu = max(int(dai * CTA_TU / 100.0), kt_dau + 50)
    kt_den = max(int(dai * CTA_DEN / 100.0), kt_tu + 100)
    lq = ""
    if lien_quan:
        lq = ("; nếu một video ĐÃ CÓ của kênh dưới đây nối tiếp tự nhiên thì nhắc tới nó theo CHỦ ĐỀ (không đọc "
              "nguyên tiêu đề, không đọc link): " + " / ".join("「{0}」".format(str(t)[:60]) for t in lien_quan[:6]))
    return LUAT_DANG_KY.format(tu=CTA_TU, den=CTA_DEN, kt_tu=kt_tu, kt_den=kt_den, giay=giay, kt_dau=kt_dau,
                               lien_quan=lq)


def them_luat_dang_ky(khuon: str, k: Any, qd: Dict[str, Any], *, muc_tieu_kt: int = 0,
                      lien_quan: Optional[Sequence[str]] = None, giu: bool = False) -> str:
    """Nhánh `cta_giua` BẬT thì thêm luật vào lời nhắc viết. `giu=True` chỉ thêm câu GIỮ, dùng cho các bước viết lại
    phía sau như nắn độ dài và rà soát. Nhánh TẮT thì lời nhắc giữ y nguyên: đó là nhóm đối chứng. `lien_quan` để
    None thì lấy danh sách đã chốt trong quyết định của lượt."""
    if not nhanh_bat(qd, "cta_giua"):
        return khuon.replace("<<LUAT_DANG_KY>>", "") if khuon else khuon
    if lien_quan is None:
        lien_quan = [str(x) for x in (qd.get("lien_quan") or []) if x]
    luat = LUAT_GIU_DANG_KY.format(giay=_giay_dau(k)) if giu else luat_dang_ky(k, muc_tieu_kt, lien_quan)
    return chen_luat(khuon, luat, "<<LUAT_DANG_KY>>")


def them_luat_binh_luan(khuon: str, qd: Dict[str, Any]) -> str:
    """Nhánh `binh_luan` BẬT thì nối luật vào lời nhắc bình luận (`6b-binh-luan.md`). Lời nhắc ấy không có khối dữ
    liệu dài, nên luật nằm cuối. Có ô `<<LUAT_BINH_LUAN>>` thì luật vào đúng ô ấy."""
    if not nhanh_bat(qd, "binh_luan"):
        return khuon.replace("<<LUAT_BINH_LUAN>>", "") if khuon else khuon
    if not (khuon or "").strip():
        return khuon
    if "<<LUAT_BINH_LUAN>>" in khuon:
        return khuon.replace("<<LUAT_BINH_LUAN>>", LUAT_BINH_LUAN)
    return khuon.rstrip() + "\n\n" + LUAT_BINH_LUAN


# ── 4. ĐO KỊCH BẢN: có câu mời không, nằm đâu ───────────────────────────────

#: Cụm "mời đăng ký" theo tiếng. Chỉ dùng để ĐO vị trí câu mời trong bài đã viết, không dùng để chọn content.
_RE_DANG_KY = re.compile(
    r"チャンネル登録|ご登録|登録ボタン|登録して|登録を|登録しておいて|登録いただ|"
    r"đăng ký kênh|đăng kí kênh|bấm đăng ký|nhấn đăng ký|đăng ký để|theo dõi kênh|"
    r"subscrib|suscr[ií]b|inscreva|inscrever|abonne|abonnier|구독|订阅|訂閱|กดติดตาม|ติดตามช่อง", re.I)
#: Cụm "hứa video tiếp" (khung chuỗi) — đo ở 20% cuối bài.
_RE_HUA_TIEP = re.compile(
    r"次回|次の動画|次は|別の動画|こちらの動画|続きは|また次|"
    r"video tiếp theo|video sau|lần sau|kỳ sau|phần tiếp|"
    r"next video|next time|next part|próximo vídeo|próximo video|prochaine vidéo|nächsten video|다음 영상|下期|下一期",
    re.I)
_KHOANG = re.compile(r"\s+")


def do_kich_ban(chu: str, k: Any = None) -> Dict[str, Any]:
    """`{ky_tu, vi_tri_pct: [..], giay: [..], giua: bool, som: bool, ket: bool, hua_tiep: bool}`: các câu mời đăng
    ký nằm ở đâu, tính trên chữ ĐỌC LÊN (bỏ khoảng trắng). `som` = có câu rơi vào `giay_mo_dau_toi_da` giây đầu (phạm
    luật mở đầu), `giua` = có câu sau giây ấy và trước 80% bài, `ket` = có câu ở 20% cuối."""
    sach = _KHOANG.sub("", chu or "")
    n = len(sach)
    ra: Dict[str, Any] = {"ky_tu": n, "vi_tri_pct": [], "giay": [], "giua": False, "som": False, "ket": False,
                          "hua_tiep": False}
    if not n:
        return ra
    nhip = _nhip(k) if k is not None else 300.0
    giay_dau = _giay_dau(k) if k is not None else 60
    for m in _RE_DANG_KY.finditer(sach):
        pct = 100.0 * m.start() / n
        giay = m.start() * 60.0 / nhip
        ra["vi_tri_pct"].append(round(pct, 1))
        ra["giay"].append(int(giay))
        if giay < giay_dau:
            ra["som"] = True
        elif pct < 80:
            ra["giua"] = True
        else:
            ra["ket"] = True
    duoi = sach[int(n * 0.8):]
    ra["hua_tiep"] = bool(_RE_HUA_TIEP.search(duoi))
    return ra


def ghi_do_kich_ban(thu_muc_luot: str, chu: str, k: Any = None) -> Dict[str, Any]:
    """Đo kịch bản CUỐI rồi ghi vào `TEP_LUOT` (khoá `do`). Lượt cũ chưa có quyết định thì ghi khung "chưa áp"."""
    qd = doc_quyet_dinh(thu_muc_luot) or {"phien": 0, "kenh_bat": False, "ly_do": "lượt trước khi có đòn bẩy"}
    qd["do"] = do_kich_ban(chu, k)
    try:
        _ghi_json(os.path.join(thu_muc_luot, TEP_LUOT), qd)
    except OSError:
        pass
    return qd


# ── 5. MÔ TẢ: link một video liên quan ─────────────────────────────────────

NHAN_LIEN_KET = {"ja": "▼ あわせて観たい動画", "vi": "▼ Xem tiếp", "en": "▼ Watch next", "ko": "▼ 함께 보면 좋은 영상",
                 "zh": "▼ 推荐观看", "es": "▼ Mira también", "pt": "▼ Assista também", "de": "▼ Als Nächstes ansehen",
                 "fr": "▼ À voir ensuite", "id": "▼ Tonton juga", "th": "▼ ดูต่อ"}
_RE_CO_LINK = re.compile(r"youtu\.be/|youtube\.com/(watch|playlist)", re.I)


def chon_video_lien_quan(tieu_de: str, mo_ta: str, ung_vien: Sequence[Dict[str, Any]],
                         goi_ai: Optional[Callable[[str], str]], han_giay: float = 120.0) -> Optional[Dict[str, Any]]:
    """AI chọn THEO NGHĨA một video người xem video mới sẽ muốn xem tiếp. AI hỏng hoặc không gọi được thì lấy video
    nhiều lượt xem nhất. Đường lùi này không lọc từ khoá."""
    if not ung_vien:
        return None
    if goi_ai is not None and len(ung_vien) > 1:
        de = ("A viewer just finished this video. Pick the ONE existing video of the same channel they would most want "
              "to watch next (same audience, closest promise/topic by MEANING).\n\nNew video title: {0}\n"
              "New video description: {1}\n\nCandidates:\n{2}\n\nReply with ONLY the candidate number.").format(
                  str(tieu_de)[:300], str(mo_ta)[:800],
                  "\n".join("{0}. {1}".format(i + 1, u["tieu_de"][:120]) for i, u in enumerate(ung_vien)))
        try:
            from .ban_giao_dang import _goi_co_han  # noqa: PLC0415

            tra = str(_goi_co_han(goi_ai, de, han_giay) or "")
            m = re.search(r"\d+", tra)
            if m and 1 <= int(m.group(0)) <= len(ung_vien):
                return ung_vien[int(m.group(0)) - 1]
        except Exception:  # noqa: BLE001 — AI hỏng: lùi về video nhiều lượt xem nhất
            pass
    return max(ung_vien, key=lambda u: u.get("xem") or 0)


def them_lien_ket_mo_ta(goc: str, k: Any, tieu_de: str, mo_ta: str,
                        goi_ai: Optional[Callable[[str], str]] = None, *,
                        bay_gio: Optional[_dt.datetime] = None) -> Tuple[str, str]:
    """(mô tả mới, ghi chú). Nối link MỘT video liên quan của kênh vào cuối mô tả khi kênh bật đòn bẩy và
    `mo_ta_lien_ket`. Mô tả đã có link YouTube thì giữ nguyên (chạy lại không nối hai lần). Hỏng thì trả mô tả cũ."""
    try:
        cd = cai_dat(k)
        if not bool(cd.get("mo_ta_lien_ket")) or _RE_CO_LINK.search(mo_ta or ""):
            return mo_ta, ""
        bat, ly_do = kenh_bat(goc, k, bay_gio)
        if not bat:
            return mo_ta, ""
        uv = video_lien_quan(goc, str(getattr(k, "ma", "") or ""), toi_da=12, bo_tieu_de=tieu_de)
        chon = chon_video_lien_quan(tieu_de, mo_ta, uv, goi_ai)
        if not chon:
            return mo_ta, "chưa có video đã đăng để link"
        nhan = NHAN_LIEN_KET.get(str(getattr(k, "ngon_ngu", "") or "")[:2].lower(), NHAN_LIEN_KET["en"])
        khoi = "{0}\n{1}\nhttps://youtu.be/{2}".format(nhan, chon["tieu_de"][:100], chon["id"])
        moi = (mo_ta or "").rstrip() + ("\n\n" if (mo_ta or "").strip() else "") + khoi
        if len(moi) > 4900:
            return mo_ta, "mô tả quá dài, bỏ link"
        return moi, "link video liên quan {0}".format(chon["id"])
    except Exception as loi:  # noqa: BLE001 — mô tả là phụ: hỏng thì giữ nguyên
        return mo_ta, "lỗi link liên quan: {0}".format(str(loi)[:80])


# ── 6. ĐÁNH GIÁ A/B + BẢNG CHO NÃO ───────────────────────────────────────────

def _ho_so_kenh(goc: str, kenh: str) -> List[Dict[str, Any]]:
    import glob  # noqa: PLC0415

    ra = []
    for p in sorted(glob.glob(os.path.join(_thu_muc_kenh(goc, kenh), "ho-so-video", "*.json"))):
        d = _doc_json(p)
        if isinstance(d, dict):
            ra.append(d)
    return ra


def _qd_cua_ho_so(goc: str, kenh: str, hs: Dict[str, Any]) -> Dict[str, Any]:
    qd = hs.get(KHOA_HO_SO)
    if isinstance(qd, dict):
        return qd
    luot = str(hs.get("luot") or "")
    return doc_quyet_dinh(os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)) if luot else {}


def _nhom(rs: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
    rs = [(s, v) for s, v in rs if v >= XEM_TOI_THIEU]
    xem, sub = sum(v for _s, v in rs), sum(s for s, _v in rs)
    return {"n": len(rs), "xem": xem, "sub": sub, "sub_1k": round(1000.0 * sub / xem, 2) if xem else None,
            "trung_vi": round(statistics.median(1000.0 * s / v for s, v in rs), 2) if rs else None}


def danh_gia_ab(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{đòn bẩy: {bat: nhóm, tat: nhóm, ket: chu, ti_so, khoang}}` — sub/1k gộp (tổng sub ÷ tổng view) của video
    nhánh BẬT so với nhánh TẮT (chỉ lượt có quyết định A/B, video ≥ `XEM_TOI_THIEU` view). `khoang` = khoảng tin ~90%
    của tỉ số hai tỉ lệ Poisson (log-ratio). Chưa đủ `N_AB_TOI_THIEU` video mỗi nhóm → "chưa đủ mẫu"."""
    import math  # noqa: PLC0415

    sub = sub_theo_video(goc, kenh)
    gom: Dict[str, Dict[str, List[Tuple[float, float]]]] = {db: {"bat": [], "tat": []} for db in DON_BAY}
    for hs in _ho_so_kenh(goc, kenh):
        vid = str(hs.get("video_id") or "")
        if vid not in sub:
            continue
        qd = _qd_cua_ho_so(goc, kenh, hs)
        for db in DON_BAY:
            o = qd.get(db) or {}
            if o.get("che_do") != "ab":
                continue
            gom[db]["bat" if o.get("bat") else "tat"].append(sub[vid])
    ra: Dict[str, Dict[str, Any]] = {}
    for db, g in gom.items():
        b, t = _nhom(g["bat"]), _nhom(g["tat"])
        o: Dict[str, Any] = {"bat": b, "tat": t, "ket": "chưa đủ mẫu", "ti_so": None, "khoang": None}
        if b["sub_1k"] is not None and t["sub_1k"]:
            o["ti_so"] = round(b["sub_1k"] / t["sub_1k"], 2)
        if b["n"] >= N_AB_TOI_THIEU and t["n"] >= N_AB_TOI_THIEU and b["sub"] > 0 and t["sub"] > 0 and b["xem"] and t["xem"]:
            lr = math.log((b["sub"] / b["xem"]) / (t["sub"] / t["xem"]))
            se = math.sqrt(1.0 / b["sub"] + 1.0 / t["sub"])
            o["khoang"] = (round(math.exp(lr - 1.645 * se), 2), round(math.exp(lr + 1.645 * se), 2))
            o["ket"] = ("BẬT thắng" if o["khoang"][0] > 1 else "BẬT thua" if o["khoang"][1] < 1 else "chưa phân thắng")
        ra[db] = o
    return ra


def _so_dang(goc: str) -> Dict[str, Any]:
    d = _doc_json(os.path.join(goc, "vm", "logs", "so-video-id.json"))
    return d if isinstance(d, dict) else {}


def _bl_dom(goc: str) -> Dict[str, Any]:
    d = _doc_json(os.path.join(goc, "vm", "logs", "cmt-dom.json"))
    return d if isinstance(d, dict) else {}


#: Nhãn hàng thành phần MHKT mà trình soạn Studio in ra (đọc lại, vd "Đăng ký: <tên kênh>", "Video: Phù hợp nhất
#: với người xem", "Danh sách phát: …") — theo ngôn ngữ giao diện Studio.
_NHAN_DANG_KY = re.compile(r"^(đăng ký|đăng kí|subscribe|チャンネル登録|登録|구독|订阅|訂閱|suscripci|inscri|abonn)", re.I)
_NHAN_VIDEO = re.compile(r"^(video|動画|视频|視頻|동영상|vídeo|vidéo)\b", re.I)
_NHAN_DSP = re.compile(r"^(danh sách phát|playlist|再生リスト|播放列表|재생목록|lista)", re.I)
_PHU_HOP = re.compile(r"phù hợp nhất với người xem|best for viewer|視聴者に最適|最適な動画|为观看者|시청자에게 맞춤", re.I)


def phan_loai_mhkt(hang: Sequence[Any]) -> Dict[str, Optional[bool]]:
    """Chữ các hàng thành phần MHKT → `{doc_duoc, dang_ky, video, phu_hop}`.

    `doc_duoc=False` nghĩa là không hàng nào mang nhãn nhận ra được, kể cả chỗ giữ "(có thành phần)" mà bộ đọc DOM
    trả khi không đọc được chữ. Khi ấy ba khoá kia là None ("chưa rõ"), để không kết luận "thiếu nút Đăng ký" oan."""
    ds = [str(x or "").strip() for x in hang or [] if str(x or "").strip() and str(x).strip() != "(có thành phần)"]
    nhan = [re.split(r"[:：]", x, 1)[0].strip() for x in ds]
    nhan_ra = [n for n in nhan if _NHAN_DANG_KY.match(n) or _NHAN_VIDEO.match(n) or _NHAN_DSP.match(n)]
    if not nhan_ra:
        return {"doc_duoc": False, "dang_ky": None, "video": None, "phu_hop": None}
    co_video = any(_NHAN_VIDEO.match(n) for n in nhan)
    return {"doc_duoc": True, "dang_ky": any(_NHAN_DANG_KY.match(n) for n in nhan), "video": co_video,
            "phu_hop": any(_PHU_HOP.search(x) for x in ds) if co_video else None}


def mhkt_kenh(goc: str, kenh: str, so: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """`{tong, co_dk, thieu_dk, chua_ro, khong_co}` MÀN HÌNH KẾT THÚC của video kênh đã lên (sổ máy đăng). `co_dk`/
    `thieu_dk` chỉ tính được ở video có chữ đọc lại (đăng từ 12/10/2026, hoặc đã bù đêm)."""
    ra = {"tong": 0, "co_dk": 0, "thieu_dk": 0, "chua_ro": 0, "khong_co": 0}
    for kh, m in (so if so is not None else _so_dang(goc)).items():
        if not isinstance(m, dict) or not str(kh).startswith(kenh + "/") or not m.get("video_id"):
            continue
        ra["tong"] += 1
        if not str(m.get("mhkt") or "").startswith("ok"):
            ra["khong_co"] += 1
            continue
        ra["co_dk" if _mhkt_dk(m) is True else "thieu_dk" if _mhkt_dk(m) is False else "chua_ro"] += 1
    return ra


def _mhkt_dk(m: Dict[str, Any]) -> Optional[bool]:
    """Mục sổ máy đăng → MHKT có nút Đăng ký không (None = chưa có chữ đọc lại)."""
    dk = m.get("mhkt_dang_ky")
    if dk is None:
        chu = str(m.get("mhkt_doc_lai") or m.get("mhkt_bu_doc_lai") or "")
        if chu:
            dk = phan_loai_mhkt(chu.split(" | ")).get("dang_ky")
    return dk


def dong_nao(goc: str, kenh: str, k: Any = None, *, bay_gio: Optional[_dt.datetime] = None) -> List[str]:
    """Dòng cho mục DANH MỤC của chương trình não: sub/1k (kênh 7 ngày + xu hướng, video đo được) và trạng thái A/B
    của các đòn bẩy, kèm MHKT/danh sách phát. Hỏng phần nào thì phần ấy ghi "?"."""
    if k is None:
        try:
            from .kenh import doc_kenh  # noqa: PLC0415

            k = doc_kenh(goc, kenh)
        except Exception:  # noqa: BLE001
            k = None
    s = sub_1k_kenh(goc, kenh)
    vd = _nhom(list(sub_theo_video(goc, kenh).values()))
    xu = ""
    if s.get("tb7") is not None and s.get("tb7_truoc"):
        xu = " (7 ngày trước {0}, ×{1})".format(_f(s["tb7_truoc"], 2), _f(s["tb7"] / s["tb7_truoc"], 2))
    d1 = "    Sub/1k view: kênh 7 ngày {0}{1} · 28 ngày {2} · video đo được {3} (n {4}, ≥{5} view)".format(
        _f(s.get("tb7"), 2), xu, _f(s.get("tb28"), 2), _f(vd["sub_1k"], 2), vd["n"], XEM_TOI_THIEU)
    if k is None:
        return [d1]
    bat, ly_do = kenh_bat(goc, k, bay_gio)
    cd = cai_dat(k)
    ab = danh_gia_ab(goc, kenh) if bat else {}
    phan = []
    for db in DON_BAY:
        che = _che_do(cd.get(db))
        if not bat:
            continue
        o = ab.get(db) or {}
        b, t = o.get("bat") or {}, o.get("tat") or {}
        phan.append("{0} [{1}]: bật n {2} ({3}/1k) · tắt n {4} ({5}/1k) — {6}{7}".format(
            TEN_DON_BAY[db], "A/B {0:.0%} bật".format(ti_le_thich_ung(cd["ti_le_bat"], o)[0]) if che == "ab" else che,
            b.get("n", 0), _f(b.get("sub_1k"), 2), t.get("n", 0), _f(t.get("sub_1k"), 2), o.get("ket", "?"),
            " ×{0} [{1}–{2}]".format(_f(o["ti_so"], 2), _f(o["khoang"][0], 2), _f(o["khoang"][1], 2))
            if o.get("khoang") else ""))
    mh = mhkt_kenh(goc, kenh)
    dsp = "có" if str(getattr(k, "danh_sach_phat_kenh", "") or "").strip() else "CHƯA khai (video vào danh sách đầu tiên)"
    d2 = "    Đòn bẩy sub: {0}{1} · MHKT có nút Đăng ký {2}/{3} (thiếu {4}, chưa đọc {5}, không có {6}) · danh sách " \
         "phát chủ đề: {7}".format("BẬT" if bat else "tắt", " ({0})".format(ly_do) if ly_do else "",
                                   mh["co_dk"], mh["tong"], mh["thieu_dk"], mh["chua_ro"], mh["khong_co"], dsp)
    ra = [d1, d2]
    ra.extend("      · " + p for p in phan)
    return ra


# ── 7. BẢNG TƯƠNG QUAN (chỉ đọc, cho người) ─────────────────────────────────

def bang_video(goc: str, kenh: str) -> List[Dict[str, Any]]:
    """Mỗi video ĐO ĐƯỢC sub một dòng: sub, view, sub/1k, dài, CTA trong kịch bản (nếu còn thư mục lượt/hồ sơ),
    MHKT, bình luận, nhánh A/B."""
    sub = sub_theo_video(goc, kenh)
    dai = {}
    for d in _doc_csv(os.path.join(_thu_muc_kenh(goc, kenh), "chi-so", "bang-tom-tat.csv")):
        m = re.fullmatch(r"(\d+):(\d{2})", str(d.get("Dài") or "").strip())
        if m:
            dai[str(d.get("Mã video") or "")] = int(m.group(1)) * 60 + int(m.group(2))
    hs_theo_id = {str(h.get("video_id")): h for h in _ho_so_kenh(goc, kenh) if h.get("video_id")}
    so = _so_dang(goc)
    bl = _bl_dom(goc)
    mh_id = {str(m.get("video_id")): m for kh, m in so.items() if isinstance(m, dict) and str(kh).startswith(kenh + "/")}
    ra = []
    for vid, (s, v) in sub.items():
        hs = hs_theo_id.get(vid) or {}
        qd = _qd_cua_ho_so(goc, kenh, hs) if hs else {}
        do = qd.get("do") or {}
        if not do and hs.get("luot"):
            kb = os.path.join(goc, "PROJECTS", "AUTO", kenh, str(hs["luot"]), "1-kich-ban.txt")
            try:
                with io.open(kb, encoding="utf-8", errors="ignore") as tep:
                    do = do_kich_ban(tep.read())
            except OSError:
                do = {}
        m = mh_id.get(vid) or {}
        dk = _mhkt_dk(m) if m else None
        b = bl.get(vid) or {}
        ra.append({"id": vid, "sub": s, "xem": v, "sub_1k": round(1000.0 * s / v, 2) if v else None,
                   "dai": dai.get(vid) or hs.get("thoi_luong_giay"),
                   "cta": ("giua" if do.get("giua") else "ket" if do.get("ket") else "som" if do.get("som")
                           else "khong") if do else None,
                   "mhkt": (str(m.get("mhkt") or "")[:2] == "ok") if m else None, "mhkt_dk": dk,
                   "binh_luan": (b.get("trang_thai") in ("da-dang", "da-ghim", "ghim-khac")) if b else None,
                   "ghim": bool(b.get("da_ghim")) if b else None,
                   "nhanh": {db: (qd.get(db) or {}).get("bat") for db in DON_BAY} if qd.get("phien") else {}})
    return ra


def _in_nhom(nhan: str, rs: Sequence[Dict[str, Any]]) -> str:
    g = _nhom([(r["sub"], r["xem"]) for r in rs])
    return "  {0:<34} n {1:>2} · {2:>9} view · {3:>5} sub · gộp {4:>5}/1k · trung vị {5:>5}".format(
        nhan, g["n"], _f(g["xem"], 0), _f(g["sub"], 0), _f(g["sub_1k"], 2), _f(g["trung_vi"], 2))


def bao_cao(goc: str, kenh_ds: Sequence[str]) -> str:
    dong = ["CHUYỂN ĐỔI SUB (video ≥ {0} view ở bản chụp có số đăng ký; gộp = tổng sub ÷ tổng view)".format(
        XEM_TOI_THIEU)]
    tat_ca: List[Dict[str, Any]] = []
    for k in kenh_ds:
        rs = bang_video(goc, k)
        tat_ca.extend(rs)
        s = sub_1k_kenh(goc, k)
        dong.append(_in_nhom(k, rs) + " · kênh 7 ngày {0} · 28 ngày {1}".format(_f(s.get("tb7"), 2),
                                                                             _f(s.get("tb28"), 2)))
    dong.append("TƯƠNG QUAN (mọi kênh gộp)")
    for nhan, loc in (("dài < 15 phút", lambda r: (r["dai"] or 0) and r["dai"] < 900),
                      ("dài 15–20 phút", lambda r: (r["dai"] or 0) and 900 <= r["dai"] < 1200),
                      ("dài ≥ 20 phút", lambda r: (r["dai"] or 0) >= 1200),
                      ("kịch bản: mời giữa bài", lambda r: r["cta"] == "giua"),
                      ("kịch bản: mời chỉ ở cuối", lambda r: r["cta"] == "ket"),
                      ("kịch bản: không mời", lambda r: r["cta"] == "khong"),
                      ("MHKT có nút Đăng ký", lambda r: r["mhkt_dk"] is True),
                      ("MHKT thiếu nút Đăng ký", lambda r: r["mhkt_dk"] is False),
                      ("bình luận mồi đã đăng", lambda r: r["binh_luan"] is True),
                      ("bình luận đã ghim", lambda r: r["ghim"] is True)):
        dong.append(_in_nhom(nhan, [r for r in tat_ca if loc(r)]))
    return "\n".join(dong)


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(prog="core.chuyen_doi_sub", description="Chuyển đổi sub / 1.000 view")
    ap.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--kenh", action="append")
    ap.add_argument("--chi-tiet", action="store_true")
    a = ap.parse_args(argv)
    if a.goc not in sys.path:
        sys.path.insert(0, a.goc)
    from . import ypp  # noqa: PLC0415

    ds = a.kenh or ypp.cac_kenh(a.goc)
    print(bao_cao(a.goc, ds))
    for k in ds:
        print("\n" + k)
        for d in dong_nao(a.goc, k):
            print(d)
        if a.chi_tiet:
            for r in sorted(bang_video(a.goc, k), key=lambda r: -(r["xem"] or 0)):
                print("   {0} {1:>7} view {2:>4} sub {3:>6}/1k dài {4} cta {5} mhkt_dk {6} nhánh {7}".format(
                    r["id"], _f(r["xem"], 0), _f(r["sub"], 0), _f(r["sub_1k"], 2), r["dai"], r["cta"],
                    r["mhkt_dk"], r["nhanh"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
