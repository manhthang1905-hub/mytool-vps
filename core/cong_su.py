"""**Cộng sự** (Collaborators / «Cộng tác» trong Studio) — video của ta đang lên thì mời các kênh ta khác làm cộng sự.

═══ VÌ SAO (21/10/2026, chủ duyệt chạy tự động hoàn toàn) ═══

YouTube Studio cho một video nhiều kênh CỘNG SỰ: kênh được mời bấm nhận thì video hiện cả trên kênh đó (khán giả của
kênh cộng sự thấy nó trên trang chủ/đăng ký). Video của ta đang cất cánh là lúc rẻ nhất để đổ khán giả sang các kênh
em: kênh em được ghi công trên một video đang chạy, người xem bấm đăng ký kênh em ngay trên trang xem.

Luật của chủ (mặc định `CAI_DAT_MAC_DINH`, đè bằng `workspace/cai-dat.json` khoá `cong_su: {...}`):
* Kích hoạt: video của ta > `nguong_view` (20.000) lượt xem trong `gio_cua_so` (48) giờ đầu. Số lượt xem đọc từ TRANG
  XEM CÔNG KHAI (`"viewCount"` của videoDetails — rẻ, mỗi giờ, không Chrome), chỉ cho video ≤ 48 giờ tuổi; lùi về
  `bang-tom-tat.csv` khi mạng hỏng. Giờ đăng: sổ máy đăng (`vm/logs/so-video-id.json` `lich`) → `publishDate` của
  trang xem → ngày của bảng tóm tắt (coi 00:00 — phía SỚM, để không lỡ cửa sổ).
* Mời: MỌI kênh ta đang chạy (`core.kenh.liet_ke_kenh` — bỏ kênh trả kho, kênh mẫu, kênh không có UC ghim hay không có
  Chrome trên máy này), trừ kênh nguồn, tới trần `toi_da_moi_video` của YouTube.
* Thứ tự trong trần và trong đợt (chủ 21/10): kênh CÙNG VÙNG đề tài với video (`workspace/chien-truong/chu-quyen-vung.json`
  chủ/chia sẻ vùng → có video thắng trong vùng) trước; rồi kênh MỚI (≤ `ngay_kenh_moi` = 14 ngày tuổi — khởi động lạnh) và
  kênh XA mốc 1.000 đăng ký YPP nhất (đăng ký là nút thắt YPP); rồi phần còn lại.
* HAI ĐỢT để đo nhân quả mà không bỏ ai: chia ngẫu nhiên có định (băm video+kênh, phân tầng theo cặp thứ tự ưu tiên) —
  đợt A mời ngay, đợt B mời sau `gio_dot_b` (24) giờ. Cửa sổ 24 giờ ấy, kênh đợt B là ĐỐI CHỨNG của đợt A.
* An toàn: tối đa `toi_da_moi_ngay` (30) lời mời mới mỗi ngày toàn máy; tối đa MỘT lô mỗi kênh nguồn mỗi ngày; nghỉ
  `nghi_giay` giữa hai thao tác như người; hộp cảnh báo/hạn chế của YouTube về cộng tác → DỪNG cả tính năng
  (`dung.json`) + Việc của bạn, tới khi người gỡ. Không đụng tiêu đề/bìa (khiên video thắng giữ nguyên), không xoá gì.

═══ HÀNG (`workspace/cong-su/hang.json`, khoá `hang.json.khoa`) ═══

Mỗi lô là MỘT mục `loai: moi_cong_su` = {id, kenh_nguon, video_id, view_luc_kich, luc_kich, dang_luc, vung, nguoi_moi:
[{kenh, uc, dot, han_moi, trang_thai, ...}], moc, do_sau}. Trạng thái từng kênh được mời:
`cho` (chờ tới hạn mời) → `da_moi` (đã gửi, `link` mời nếu Studio đưa) → `da_nhan` (kênh kia đã nhận) → `xac_minh`
(trang xem công khai ghi công kênh đó) · `loi` (lan_loi, ly_do — thử lại có hạn) · `bo_qua` (ly_do: vượt trần, kênh
không có tính năng…). Mục chạy lại được, không trùng: một video chỉ một lô; một kênh chỉ mời một lần.
Máy DOM thực thi: `vm/cong_su_dom.py` (skill D26). Quét + lập lô + đo: `python -m core.cong_su quet` (skill D25).

═══ ĐO ═══ (`do_hieu_qua`, sau `ngay_do` + `ngay_tre_studio` ngày)
Mỗi kênh cộng sự và kênh nguồn: view/ngày, đăng ký mới/ngày, hiển thị/ngày (chuỗi ngày Studio `core.chi_so_kenh`) trong
7 ngày sau lúc nhận ÷ trung bình 7 ngày trước (tỉ lệ của CHÍNH kênh); % traffic trang chủ trước/sau. So A–B: ngày đầu
sau khi đợt A nhận (đợt B chưa được mời) — trung vị tỉ lệ A trừ trung vị tỉ lệ B = độ nâng ước của việc làm cộng sự.
Kết quả vào `do_sau` của mục + sổ `so.jsonl` + sự kiện não bộ phận `tang-truong` — chỉ ĐỀ XUẤT chỉnh ngưỡng/đợt, không tự
đổi luật của chủ.
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
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

THU_MUC = os.path.join("workspace", "cong-su")
TEP_HANG = "hang.json"
TEP_SO = "so.jsonl"
TEP_DUNG = "dung.json"
TEP_QUET = "quet-cuoi.json"
KHOA_CAI = "cong_su"
BO_PHAN_NAO = "tang-truong"
LOAI = "moi_cong_su"

CAI_DAT_MAC_DINH: Dict[str, Any] = {
    "bat": True,
    "nguong_view": 20000,
    "gio_cua_so": 48,
    #: Trần kênh cộng sự mỗi video — số thật của YouTube đo ở lượt thăm dò (vm/cong_su_dom.py --tham-do); máy DOM đọc
    #: lại trần trong hộp mỗi lượt và không bao giờ vượt.
    "toi_da_moi_video": 5,
    "toi_da_moi_ngay": 30,
    "lo_moi_kenh_nguon_ngay": 1,
    "gio_dot_b": 24,
    "gio_cho_nhan": 48,
    "so_thu_lai": 1,
    "toi_da_loi": 3,
    "phut_thu_lai": 90,
    "ngay_do": 7,
    "ngay_tre_studio": 2,
    "ngay_kenh_moi": 14,
    "nghi_giay": [20, 60],
    #: Khung giờ không chạy DOM (giờ máy): quét ngày 02:10–06:00, 60 phút trước khe đăng 05:00 / 20:00.
    "gio_cam": [["02:10", "06:00"], ["04:00", "05:00"], ["19:00", "20:00"]],
}

TT_CHO, TT_DA_MOI, TT_DA_NHAN, TT_XAC_MINH, TT_LOI, TT_BO_QUA = "cho", "da_moi", "da_nhan", "xac_minh", "loi", "bo_qua"
TT_DANG_DO = (TT_DA_NHAN, TT_XAC_MINH)
_RE_VID = re.compile(r"^[A-Za-z0-9_-]{11}$")

Tai = Callable[[str], Tuple[int, bytes]]


# ── tiện ích ────────────────────────────────────────────────────────────────

def thu_muc(goc: str) -> str:
    return os.path.join(goc, THU_MUC)


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=1, default=str)
    os.replace(tam, duong)


def _luc(t: _dt.datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def _doc_luc(s: Any) -> Optional[_dt.datetime]:
    s = str(s or "").strip()
    for dang, n in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16),
                    ("%d/%m/%Y %H:%M", 16), ("%Y-%m-%d", 10), ("%d/%m/%Y", 10)):
        try:
            return _dt.datetime.strptime(s[:n], dang)
        except ValueError:
            continue
    return None


def _so(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def doc_cai(goc: str, de: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mặc định ← `workspace/cai-dat.json: cong_su` ← `de`."""
    cai = dict(CAI_DAT_MAC_DINH)
    tep = _doc_json(os.path.join(goc, "workspace", "cai-dat.json"))
    if isinstance(tep, dict) and isinstance(tep.get(KHOA_CAI), dict):
        cai.update({k: v for k, v in tep[KHOA_CAI].items() if not str(k).startswith("_")})
    if de:
        cai.update(de)
    return cai


def trong_gio_cam(bay: _dt.datetime, cai: Dict[str, Any]) -> str:
    """'' khi được chạy DOM; câu lý do khi trong khung cấm."""
    p = bay.hour * 60 + bay.minute
    for tu, den in cai.get("gio_cam") or []:
        try:
            a = int(tu[:2]) * 60 + int(tu[3:5])
            b = int(den[:2]) * 60 + int(den[3:5])
        except (TypeError, ValueError):
            continue
        if a <= p < b:
            return "khung cấm {0}–{1}".format(tu, den)
    return ""


# ── dừng khẩn (YouTube cảnh báo/hạn chế) ────────────────────────────────────

def dang_dung(goc: str) -> Dict[str, Any]:
    d = _doc_json(os.path.join(thu_muc(goc), TEP_DUNG))
    return d if isinstance(d, dict) and d.get("dung") else {}


def dat_dung(goc: str, ly_do: str, kenh: str = "", bang_chung: str = "") -> None:
    """YouTube hiện hộp cảnh báo/hạn chế về cộng tác → DỪNG mọi lời mời/nhận tới khi người gỡ (xoá tệp hoặc
    `dung: false`)."""
    _ghi_json(os.path.join(thu_muc(goc), TEP_DUNG), {"dung": True, "luc": _luc(_dt.datetime.now()), "kenh": kenh,
                                                       "ly_do": str(ly_do)[:400], "bang_chung": bang_chung})
    ghi_su_kien(goc, "dung", kenh=kenh, ly_do=ly_do, bang_chung=bang_chung, nao_loai="loi")


# ── sổ + não ────────────────────────────────────────────────────────────────

def ghi_su_kien(goc: str, viec: str, *, kenh: str = "", video_id: str = "", nao_loai: str = "", **them: Any) -> None:
    """Một dòng `so.jsonl` (+ một sự kiện não bộ phận `tang-truong` nếu `nao_loai`). Không bao giờ ném lỗi."""
    d = {"luc": _luc(_dt.datetime.now()), "viec": viec, "kenh": kenh, "video_id": video_id}
    d.update(them)
    try:
        os.makedirs(thu_muc(goc), exist_ok=True)
        with io.open(os.path.join(thu_muc(goc), TEP_SO), "a", encoding="utf-8") as tep:
            tep.write(json.dumps(d, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass
    if nao_loai:
        try:
            from core import nao_bo_phan  # noqa: PLC0415
            nd = them.get("noi_dung") or "{0}: {1}".format(viec, ", ".join(
                "{0}={1}".format(k, v) for k, v in them.items() if k not in ("noi_dung", "so") and v not in ("", None))[:300])
            nao_bo_phan.ghi(goc, BO_PHAN_NAO, nao_loai, kenh=kenh, noi_dung=str(nd)[:600],
                            so=them.get("so") if isinstance(them.get("so"), dict) else None, nguon="cong_su",
                            khoa="cong-su|{0}|{1}|{2}|{3}".format(viec, kenh, video_id, d["luc"]))
        except Exception:  # noqa: BLE001
            pass


#: Điều đo được bằng thăm dò chỉ đọc 21/10/2026 (chi tiết: docs/kien-thuc/cong-su.md) — vào não MỘT lần.
KIEN_THUC = (
    "Cộng sự YouTube (đo 21/10/2026): (1) view, giờ xem, doanh thu của video cộng tác tính HẾT cho kênh nguồn (hộp mời "
    "ghi «Quyền sở hữu toàn bộ»); kênh cộng sự chỉ được thêm hiển thị, người đăng ký qua nút đăng ký riêng trên trang "
    "xem (hộp «コラボレーター» liệt kê từng kênh) và view lan sang video của chính nó. (2) Video cộng tác hiện ở kệ "
    "«コラボレーション» trang chủ kênh cộng sự, không có trong tab Video. (3) Ô mời chỉ tìm theo tên/@handle, không "
    "nhận link kênh hay UC. Có dòng «đã đạt giới hạn tạo lời mời»; chủ đã thử tay 4 cộng sự trên một video TL4. "
    "(4) Kênh được mời xem ở tab «Video cộng tác» (/videos/collaboration). Đo hiệu quả: so đăng ký và view video "
    "riêng của kênh cộng sự, đợt A với đợt B.")


def ghi_kien_thuc(goc: str) -> None:
    try:
        from core import nao_bo_phan  # noqa: PLC0415
        nao_bo_phan.ghi(goc, BO_PHAN_NAO, "ket_qua", noi_dung=KIEN_THUC, nguon="cong_su", khoa="cong-su|kien-thuc|v1")
    except Exception:  # noqa: BLE001
        pass


# ── hàng (khoá chung với máy DOM) ───────────────────────────────────────────

def _duong_hang(goc: str) -> str:
    return os.path.join(thu_muc(goc), TEP_HANG)


def giu_khoa(goc: str, han: float = 20.0, qua_han: float = 15 * 60) -> Optional[str]:
    """Khoá `hang.json.khoa` (O_EXCL; khoá cũ quá 15 phút bị dọn). None = không giữ được trong `han` giây."""
    duong = _duong_hang(goc) + ".khoa"
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    het = time.monotonic() + han
    while True:
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return duong
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(duong) > qua_han:
                    os.remove(duong)
                    continue
            except OSError:
                pass
        if time.monotonic() >= het:
            return None
        time.sleep(0.3)


def nha_khoa(duong: Optional[str]) -> None:
    if duong:
        try:
            os.remove(duong)
        except OSError:
            pass


def doc_hang(goc: str) -> List[Dict[str, Any]]:
    d = _doc_json(_duong_hang(goc))
    return [x for x in ((d or {}).get("viec") or []) if isinstance(x, dict)] if isinstance(d, dict) else []


def ghi_hang(goc: str, ds: List[Dict[str, Any]]) -> None:
    _ghi_json(_duong_hang(goc), {"phien_ban": 1, "viec": ds})


def sua_hang(goc: str, ham: Callable[[List[Dict[str, Any]]], Any]) -> Any:
    """Đọc → `ham(ds)` (sửa tại chỗ) → ghi, dưới khoá. Không giữ được khoá → RuntimeError."""
    k = giu_khoa(goc)
    if k is None:
        raise RuntimeError("hàng cộng sự đang bị khoá")
    try:
        ds = doc_hang(goc)
        kq = ham(ds)
        ghi_hang(goc, ds)
        return kq
    finally:
        nha_khoa(k)


def cap_nhat_nguoi(goc: str, id_muc: str, kenh: str, **truong: Any) -> bool:
    """Cập nhật trạng thái MỘT kênh được mời của MỘT mục (máy DOM gọi sau từng thao tác)."""
    def ham(ds):
        for m in ds:
            if m.get("id") != id_muc:
                continue
            for n in m.get("nguoi_moi") or []:
                if n.get("kenh") == kenh:
                    n.update(truong)
                    n["cap_nhat"] = _luc(_dt.datetime.now())
                    return True
        return False
    return bool(sua_hang(goc, ham))


def cap_nhat_muc(goc: str, id_muc: str, **truong: Any) -> bool:
    def ham(ds):
        for m in ds:
            if m.get("id") == id_muc:
                m.update(truong)
                return True
        return False
    return bool(sua_hang(goc, ham))


# ── kênh ────────────────────────────────────────────────────────────────────

def uc_ghim(goc: str) -> Dict[str, str]:
    d = _doc_json(os.path.join(goc, "vm", "logs", "kenh-uc.json"))
    return {str(k): str(v) for k, v in d.items() if str(v).startswith("UC")} if isinstance(d, dict) else {}


def _kenh_mau(goc: str, kenh: str) -> bool:
    try:
        with io.open(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8-sig") as tep:
            return bool(re.search(r"(?m)^mau_cua_tool:\s*true", tep.read()))
    except OSError:
        return False


def _kenh_co_chrome(goc: str) -> Optional[set]:
    """Kênh khai trong `vm/config.json: cac_kenh` (có Chrome trên máy này). None = không đọc được (không lọc)."""
    d = _doc_json(os.path.join(goc, "vm", "config.json"))
    if not isinstance(d, dict) or not isinstance(d.get("cac_kenh"), list):
        return None
    ra = set()
    for x in d["cac_kenh"]:
        if isinstance(x, dict):
            ra.add(str(x.get("ma") or x.get("kenh") or x.get("ten") or ""))
        else:
            ra.add(str(x))
    return ra


def kenh_hoat_dong(goc: str) -> Dict[str, Dict[str, Any]]:
    """`{kenh: {uc, ly_do_bo}}` — mọi kênh đang chạy; `ly_do_bo` khác "" = không mời/nhận được ở máy này."""
    from .kenh import liet_ke_kenh  # noqa: PLC0415
    ghim = uc_ghim(goc)
    chrome = _kenh_co_chrome(goc)
    ra: Dict[str, Dict[str, Any]] = {}
    for k in liet_ke_kenh(goc):
        if _kenh_mau(goc, k):
            continue
        ly = ""
        if not ghim.get(k):
            ly = "chưa có UC ghim (vm/logs/kenh-uc.json)"
        elif chrome is not None and k not in chrome:
            ly = "không có Chrome kênh trên máy này"
        ra[k] = {"uc": ghim.get(k, ""), "ly_do_bo": ly}
    return ra


def link_kenh(uc: str) -> str:
    return "https://www.youtube.com/channel/{0}".format(uc)


TEP_HANDLE = "handle.json"
_RE_HANDLE = re.compile(r'"vanityChannelUrl"\s*:\s*"https?://(?:www\.)?youtube\.com/(@[^"?/]+)"')


def doc_handle(html: str) -> str:
    """@handle của CHÍNH kênh từ HTML trang kênh công khai (`channelMetadataRenderer.vanityChannelUrl`) — thuần."""
    from urllib.parse import unquote  # noqa: PLC0415
    m = _RE_HANDLE.search(html)
    return unicodedata_nfkc(unquote(m.group(1))) if m else ""


def unicodedata_nfkc(s: str) -> str:
    import unicodedata  # noqa: PLC0415
    return unicodedata.normalize("NFKC", str(s or "")).strip()


_RE_TEN_KENH = re.compile(r'"channelMetadataRenderer"\s*:\s*\{\s*"title"\s*:\s*"((?:[^"\\]|\\.)*)"')


def doc_ten_kenh(html: str) -> str:
    """Tên hiển thị của CHÍNH kênh (`channelMetadataRenderer.title`) — thuần."""
    m = _RE_TEN_KENH.search(html)
    if not m:
        return ""
    try:
        return unicodedata_nfkc(json.loads('"' + m.group(1) + '"'))
    except ValueError:
        return unicodedata_nfkc(m.group(1))


def ho_so_cong_khai(goc: str, uc: str, tai: Optional[Tai] = None, tuoi_gio: float = 72.0) -> Dict[str, str]:
    """`{handle, ten}` của kênh `uc` từ trang kênh công khai. Ô tìm «Mời cộng sự» chỉ tìm theo TÊN/@handle (đo
    21/10/2026: dán link kênh hay UC → «Không tìm thấy người dùng phù hợp»; gõ @handle → đúng một kênh); hàng cộng sự
    trong hộp chỉ mang TÊN kênh + nhãn trạng thái. Nhớ `handle.json` ≤ `tuoi_gio` giờ."""
    duong = os.path.join(thu_muc(goc), TEP_HANDLE)
    nho = _doc_json(duong)
    nho = nho if isinstance(nho, dict) else {}
    x = nho.get(uc) or {}
    t = _doc_luc(x.get("luc"))
    if x.get("handle") and t and (_dt.datetime.now() - t).total_seconds() < tuoi_gio * 3600:
        return {"handle": str(x["handle"]), "ten": str(x.get("ten") or "")}
    ma, du = (tai or tai_that)("https://www.youtube.com/channel/{0}?hl=en".format(uc))
    html = du.decode("utf-8", "replace") if ma == 200 and du else ""
    h, ten = doc_handle(html), doc_ten_kenh(html)
    if h:
        nho[uc] = {"handle": h, "ten": ten, "luc": _luc(_dt.datetime.now())}
        try:
            _ghi_json(duong, nho)
        except OSError:
            pass
        return {"handle": h, "ten": ten}
    return {"handle": str(x.get("handle") or ""), "ten": str(x.get("ten") or "")}


def handle_cua_uc(goc: str, uc: str, tai: Optional[Tai] = None) -> str:
    return ho_so_cong_khai(goc, uc, tai)["handle"]


# ── video mới + lượt xem ────────────────────────────────────────────────────

def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with io.open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return [d for d in csv.DictReader(tep) if isinstance(d, dict)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def bang_tom_tat(goc: str, kenh: str) -> Dict[str, Dict[str, str]]:
    return {str(d.get("Mã video") or "").strip(): d
            for d in _doc_csv(os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv"))
            if str(d.get("Mã video") or "").strip()}


def video_gan_day(goc: str, bay: _dt.datetime, gio: float, kenh_ds: Sequence[str]) -> List[Dict[str, Any]]:
    """Video của ta công khai trong `gio` giờ qua (hoặc sắp tới 1 giờ nữa — để lượt quét kế bắt kịp):
    `[{kenh, video_id, dang_luc, nguon, tieu_de, view_bang}]`. Chỉ đọc đĩa."""
    ra: Dict[str, Dict[str, Any]] = {}
    so = _doc_json(os.path.join(goc, "vm", "logs", "so-video-id.json"))
    co_so = set()                     # video máy đăng biết giờ hẹn: tin sổ (kể cả video CHƯA tới giờ công khai)
    for khoa, m in (so.items() if isinstance(so, dict) else []):
        if not isinstance(m, dict) or "/" not in str(khoa):
            continue
        kenh = str(khoa).split("/", 1)[0]
        vid = str(m.get("video_id") or "")
        if _doc_luc(m.get("lich_dat") or m.get("lich")) is not None:
            co_so.add(vid)
        if kenh not in kenh_ds or not _RE_VID.match(vid):
            continue
        luc = _doc_luc(m.get("lich_dat") or m.get("lich"))
        if luc is None:
            continue
        tuoi = (bay - luc).total_seconds() / 3600.0
        if -1.0 <= tuoi <= gio:
            ra[vid] = {"kenh": kenh, "video_id": vid, "dang_luc": _luc(luc), "nguon": "so_may_dang"}
    for kenh in kenh_ds:
        for vid, d in bang_tom_tat(goc, kenh).items():
            if not _RE_VID.match(vid):
                continue
            if vid in ra:
                ra[vid].update(tieu_de=str(d.get("Tiêu đề") or ""), view_bang=_so(d.get("Lượt xem")))
                continue
            if vid in co_so:
                continue
            ngay = _doc_luc(str(d.get("Ngày đăng") or "")[:10])
            if ngay is None:
                continue
            tuoi = (bay - ngay).total_seconds() / 3600.0      # 00:00 của ngày đăng: phía sớm, không lỡ cửa sổ
            if 0 <= tuoi <= gio + 24:
                ra[vid] = {"kenh": kenh, "video_id": vid, "dang_luc": _luc(ngay), "nguon": "bang_tom_tat_ngay",
                           "tieu_de": str(d.get("Tiêu đề") or ""), "view_bang": _so(d.get("Lượt xem"))}
    return sorted(ra.values(), key=lambda x: x["dang_luc"], reverse=True)


def tai_that(url: str) -> Tuple[int, bytes]:
    import urllib.error  # noqa: PLC0415
    try:
        from .mang_an_toan import mo_url  # noqa: PLC0415
        with mo_url(url, cho=20, headers={"Accept-Language": "ja,en;q=0.8"}) as ph:
            return int(getattr(ph, "status", 200) or 200), ph.read()
    except urllib.error.HTTPError as loi:
        return int(loi.code or 0), b""
    except Exception:  # noqa: BLE001
        return 0, b""


_RE_VIEW = re.compile(r'"videoDetails":\{.{0,6000}?"viewCount":"(\d+)"', re.S)
_RE_VIEW_LUI = re.compile(r'"viewCount":"(\d+)"')
_RE_PUBLISH = re.compile(r'"(?:publishDate|uploadDate)":"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})([+-]\d{2}:\d{2})"')


def doc_trang_xem(html: str) -> Dict[str, Any]:
    """`{view, dang_luc_utc}` từ HTML trang xem công khai (thuần). Không thấy → None."""
    m = _RE_VIEW.search(html) or _RE_VIEW_LUI.search(html)
    view = int(m.group(1)) if m else None
    dang = None
    p = _RE_PUBLISH.search(html)
    if p:
        try:
            t = _dt.datetime.strptime(p.group(1), "%Y-%m-%dT%H:%M:%S")
            dau = 1 if p.group(2)[0] == "+" else -1
            lech = _dt.timedelta(hours=int(p.group(2)[1:3]), minutes=int(p.group(2)[4:6]))
            dang = t - dau * lech            # → UTC
        except ValueError:
            dang = None
    return {"view": view, "dang_luc_utc": dang}


def _gio_dia_phuong(utc: _dt.datetime) -> _dt.datetime:
    lech = _dt.datetime.now() - _dt.datetime.utcnow()
    return utc + _dt.timedelta(seconds=round(lech.total_seconds() / 60.0) * 60)


def view_cong_khai(vid: str, tai: Optional[Tai] = None) -> Dict[str, Any]:
    ma, du = (tai or tai_that)("https://www.youtube.com/watch?v={0}&hl=en".format(vid))
    if ma != 200 or not du:
        return {"view": None, "dang_luc": None, "ma": ma}
    d = doc_trang_xem(du.decode("utf-8", "replace"))
    return {"view": d["view"], "dang_luc": _gio_dia_phuong(d["dang_luc_utc"]) if d["dang_luc_utc"] else None, "ma": ma}


# ── ưu tiên + chia đợt ──────────────────────────────────────────────────────

def vung_video(goc: str, vid: str, tieu_de: str, kenh_ds: Sequence[str]) -> str:
    """Vùng đề tài của video: vùng AI theo mã video (chiến trường) → nhãn cụm của tiêu đề (bộ cụm gộp mọi kênh)."""
    try:
        from . import chu_quyen_vung as cq  # noqa: PLC0415
        v = cq._vung_ai(goc).get(vid)  # noqa: SLF001
        if v and v not in ("ngoai-ngach", "khac"):
            return str(v)
    except Exception:  # noqa: BLE001
        pass
    if not tieu_de:
        return ""
    try:
        from . import cong_thuc_v7 as v7  # noqa: PLC0415
        import copy  # noqa: PLC0415
        gop: Dict[str, Dict[str, Any]] = {}
        for k in kenh_ds:
            try:
                ch, _ = v7.nap_cau_hinh(goc, k, ghi_neu_thieu=False)
            except Exception:  # noqa: BLE001
                continue
            for ma, c in (ch.get("cum") or {}).items():
                gop.setdefault(ma, copy.deepcopy(c))
        ch = copy.deepcopy(v7.CAU_HINH_MAC_DINH)
        ch["cum"] = gop
        ds = v7.cum_cua_tieu_de(tieu_de, ch)
        return str(ds[0]) if ds and ds[0] != "khac" else ""
    except Exception:  # noqa: BLE001
        return ""


def diem_vung(goc: str, vung: str) -> Dict[str, int]:
    """`{kenh: 2 chủ/chia sẻ vùng · 1 có video thắng trong vùng}`."""
    if not vung:
        return {}
    d = _doc_json(os.path.join(goc, "workspace", "chien-truong", "chu-quyen-vung.json")) or {}
    z = ((d.get("vung") or {}).get(vung)) if isinstance(d, dict) else None
    if not isinstance(z, dict):
        return {}
    ra = {str(k): 1 for k in (z.get("thang") or {})}
    for k in [z.get("chu")] + list(z.get("chia_se") or []):
        if k:
            ra[str(k)] = 2
    return ra


def diem_nghia(goc: str, tieu_de: str, ung: Sequence[str], nguong: float = 0.3) -> Dict[str, int]:
    """Lùi khi video chưa có vùng (vùng AI chỉ phủ video đối thủ, bộ cụm từ khoá hụt tiêu đề mới): so THEO NGHĨA bằng
    nhãn D24 (`core.nhan_nghia`, không gọi thêm LLM) — kênh có ≥ `nguong` tiêu đề cùng `linhvuc` với video = 1 điểm."""
    try:
        from . import nhan_nghia  # noqa: PLC0415
        nho = nhan_nghia.doc_nho(goc)
        goc_n = (nhan_nghia.tra(goc, tieu_de, nho) or {}).get("n") or {}
        lv = goc_n.get("linhvuc")
        if not lv or lv == "none":
            return {}
        ra = {}
        for k in ung:
            ds = [(nhan_nghia.tra(goc, str(d.get("Tiêu đề") or ""), nho) or {}).get("n") or {}
                  for d in bang_tom_tat(goc, k).values()]
            ds = [x for x in ds if x]
            if ds and sum(1 for x in ds if x.get("linhvuc") == lv) / len(ds) >= nguong:
                ra[k] = 1
        return ra
    except Exception:  # noqa: BLE001
        return {}


def ho_so_kenh(goc: str, kenh: str, bay: _dt.datetime) -> Dict[str, Any]:
    """`{sub, tuoi_ngay}` — sub trọn đời (core.ypp), tuổi kênh = ngày video đầu tiên trong bảng tóm tắt."""
    sub = None
    try:
        from . import ypp  # noqa: PLC0415
        sub = ypp.du_bao(goc, kenh, bay).get("dang_ky")
    except Exception:  # noqa: BLE001
        sub = None
    ngay = [_doc_luc(str(d.get("Ngày đăng") or "")[:10]) for d in bang_tom_tat(goc, kenh).values()]
    # bảng tóm tắt chỉ giữ video gần đây → thêm lần chụp cấp kênh ĐẦU TIÊN (kenh-theo-ngay.csv) cho tuổi kênh thật
    dau = _doc_csv(os.path.join(goc, "CHANNEL", kenh, "chi-so", "kenh-theo-ngay.csv"))[:1]
    ngay += [_doc_luc(str(d.get("Lúc chụp") or "")[:16]) for d in dau]
    ngay = [n for n in ngay if n]
    tuoi = (bay - min(ngay)).days if ngay else 0
    return {"sub": sub, "tuoi_ngay": tuoi}


def ti_le_trang_chu(goc: str, kenh: str) -> Optional[float]:
    """% traffic TRANG CHỦ (browse) cấp kênh, trung vị ≤ 7 bản chụp gần nhất (`core.chi_so_kenh`)."""
    try:
        from . import chi_so_kenh  # noqa: PLC0415
        return chi_so_kenh.ti_le_traffic(goc, kenh).get("trang_chu")
    except Exception:  # noqa: BLE001
        return None


def xep_uu_tien(ung: Sequence[str], diem: Dict[str, int], ho_so: Dict[str, Dict[str, Any]],
                ngay_kenh_moi: int = 14) -> List[Dict[str, Any]]:
    """Thứ tự mời (thuần): cùng vùng → kênh mới / xa 1.000 đăng ký → còn lại. Trả [{kenh, ly_do, khoa}]."""
    ra = []
    for k in ung:
        hs = ho_so.get(k) or {}
        sub = hs.get("sub")
        thieu = max(0.0, 1000.0 - float(sub)) if sub is not None else 1000.0
        moi = int(hs.get("tuoi_ngay") or 0) <= int(ngay_kenh_moi)
        dv = int(diem.get(k) or 0)
        ly = []
        if dv:
            ly.append("cùng vùng" + (" (chủ)" if dv >= 2 else ""))
        if moi:
            ly.append("kênh mới {0} ngày".format(hs.get("tuoi_ngay") or 0))
        ly.append("còn thiếu {0:.0f} đăng ký tới 1.000".format(thieu))
        ra.append({"kenh": k, "ly_do": "; ".join(ly), "khoa": (-dv, 0 if moi else 1, -thieu, k)})
    ra.sort(key=lambda x: x["khoa"])
    return ra


def _bam(s: str) -> int:
    return int(hashlib.sha1(s.encode("utf-8")).hexdigest()[:8], 16)


def chia_dot(xep: Sequence[str], vid: str) -> Dict[str, str]:
    """Ngẫu nhiên CÓ ĐỊNH, phân tầng theo cặp: mỗi cặp liền nhau theo thứ tự ưu tiên → một kênh A, một kênh B (băm
    video+kênh quyết ai). Lẻ một kênh cuối → băm quyết. Trả `{kenh: "A"|"B"}`."""
    ra: Dict[str, str] = {}
    ds = list(xep)
    for i in range(0, len(ds), 2):
        cap = ds[i:i + 2]
        if len(cap) == 2:
            a, b = sorted(cap, key=lambda k: _bam(vid + "|" + k))
            ra[a], ra[b] = "A", "B"
        else:
            ra[cap[0]] = "A" if _bam(vid + "|" + cap[0]) % 2 == 0 else "B"
    if ds and "A" not in ra.values():
        ra[ds[0]] = "A"
    return ra


# ── lập lô ──────────────────────────────────────────────────────────────────

def da_moi_hom_nay(ds: Sequence[Dict[str, Any]], ngay: str) -> int:
    return sum(1 for m in ds for n in m.get("nguoi_moi") or []
               if str(n.get("luc_moi") or "").startswith(ngay))


def tao_lo(goc: str, v: Dict[str, Any], view: int, bay: _dt.datetime, cai: Dict[str, Any],
           kenh: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """MỘT mục `moi_cong_su` cho video `v` (chưa ghi). Kênh không mời được → `bo_qua` kèm lý do (vẫn ghi để đọc)."""
    kenh = kenh if kenh is not None else kenh_hoat_dong(goc)
    nguon = v["kenh"]
    vung = vung_video(goc, v["video_id"], v.get("tieu_de") or "", list(kenh))
    diem = diem_vung(goc, vung)
    ung = [k for k, x in kenh.items() if k != nguon and not x["ly_do_bo"]]
    nguon_vung = "chien_truong" if diem else ""
    if not diem:
        diem = diem_nghia(goc, v.get("tieu_de") or "", ung)
        nguon_vung = "nhan_nghia" if diem else ""
    ho_so = {k: ho_so_kenh(goc, k, bay) for k in ung}
    xep = xep_uu_tien(ung, diem, ho_so, int(cai.get("ngay_kenh_moi") or 14))
    tran = int(cai.get("toi_da_moi_video") or 5)
    trong = [x["kenh"] for x in xep[:tran]]
    dot = chia_dot(trong, v["video_id"])
    han_b = bay + _dt.timedelta(hours=float(cai.get("gio_dot_b") or 24))
    nguoi = []
    for i, x in enumerate(xep):
        k = x["kenh"]
        n = {"kenh": k, "uc": kenh[k]["uc"], "link_kenh": link_kenh(kenh[k]["uc"]), "thu_tu": i + 1,
             "ly_do_chon": x["ly_do"], "sub_luc_kich": (ho_so.get(k) or {}).get("sub"), "lan_loi": 0,
             "trang_chu_truoc": ti_le_trang_chu(goc, k)}
        if k in dot:
            n.update(dot=dot[k], trang_thai=TT_CHO, han_moi=_luc(bay if dot[k] == "A" else han_b))
        else:
            n.update(dot="", trang_thai=TT_BO_QUA, ly_do="vượt trần {0} cộng sự/video".format(tran))
        nguoi.append(n)
    for k, x in kenh.items():
        if k != nguon and x["ly_do_bo"]:
            nguoi.append({"kenh": k, "uc": x["uc"], "trang_thai": TT_BO_QUA, "ly_do": x["ly_do_bo"], "dot": ""})
    return {"id": "{0}:{1}".format(LOAI, v["video_id"]), "loai": LOAI, "kenh_nguon": nguon, "video_id": v["video_id"],
            "tieu_de": (v.get("tieu_de") or "")[:200], "dang_luc": v.get("dang_luc"), "nguon_gio": v.get("nguon"),
            "view_luc_kich": view, "luc_kich": _luc(bay), "ngay": bay.date().isoformat(), "vung": vung,
            "nguon_vung": nguon_vung,
            "trang_thai": "mo", "tran_youtube": tran, "nguoi_moi": nguoi,
            "moc": {"sub_nguon": ho_so_kenh(goc, nguon, bay).get("sub")}}


def quet(goc: str, bay: Optional[_dt.datetime] = None, tai: Optional[Tai] = None, thu: bool = False,
         cai_de: Optional[Dict[str, Any]] = None, nk: Callable[[str], None] = lambda s: None) -> Dict[str, Any]:
    """MỘT lượt (skill D25, mỗi giờ): đọc lượt xem công khai video ≤ 48 giờ → lập lô cho video đạt ngưỡng → đo các lô
    đã đủ ngày. `thu`: không ghi gì (trả các lô SẼ lập)."""
    bay = bay or _dt.datetime.now()
    cai = doc_cai(goc, cai_de)
    kq: Dict[str, Any] = {"luc": _luc(bay), "thu": thu, "video": [], "lo_moi": [], "bo": [], "do": []}
    if not cai.get("bat", True):
        kq["ly_do"] = "cài đặt cong_su.bat = false"
        return kq
    kenh = kenh_hoat_dong(goc)
    ds_cu = doc_hang(goc)
    co_lo = {m.get("video_id") for m in ds_cu}
    nguong, cua_so = float(cai["nguong_view"]), float(cai["gio_cua_so"])
    for v in video_gan_day(goc, bay, cua_so, list(kenh)):
        r = view_cong_khai(v["video_id"], tai)
        view, nguon_view = r["view"], "trang_xem"
        if view is None and not r.get("ma") and v.get("view_bang") is not None:     # chỉ khi MẠNG hỏng
            view, nguon_view = int(v["view_bang"]), "bang_tom_tat"
        dang = r.get("dang_luc") or _doc_luc(v.get("dang_luc"))
        if r.get("dang_luc") and v.get("nguon") != "so_may_dang":
            v["dang_luc"], v["nguon"] = _luc(r["dang_luc"]), "trang_xem"
        tuoi = (bay - dang).total_seconds() / 3600.0 if dang else None
        dong = {"kenh": v["kenh"], "video_id": v["video_id"], "view": view, "nguon_view": nguon_view,
                "tuoi_gio": None if tuoi is None else round(tuoi, 1), "ma_http": r.get("ma")}
        kq["video"].append(dong)
        if view is None or tuoi is None or tuoi > cua_so or tuoi < 0 or view <= nguong:
            continue
        if v["video_id"] in co_lo:
            continue
        ngay = bay.date().isoformat()
        if sum(1 for m in ds_cu + kq["lo_moi"] if m.get("kenh_nguon") == v["kenh"] and m.get("ngay") == ngay) \
                >= int(cai.get("lo_moi_kenh_nguon_ngay") or 1):
            kq["bo"].append(dict(dong, ly_do="kênh nguồn đã có một lô cộng sự hôm nay"))
            continue
        lo = tao_lo(goc, v, int(view), bay, cai, kenh)
        kq["lo_moi"].append(lo)
        nk("video {0}/{1}: {2:,} lượt xem ở {3:.0f} giờ > {4:,.0f} → lô cộng sự {5} kênh (A {6}, B {7})".format(
            v["kenh"], v["video_id"], view, tuoi, nguong, sum(1 for n in lo["nguoi_moi"] if n.get("dot")),
            sum(1 for n in lo["nguoi_moi"] if n.get("dot") == "A"), sum(1 for n in lo["nguoi_moi"] if n.get("dot") == "B")))
    if not thu:
        ghi_kien_thuc(goc)
        if kq["lo_moi"]:
            def them(ds):
                co = {m.get("video_id") for m in ds}
                ds.extend(m for m in kq["lo_moi"] if m["video_id"] not in co)
            sua_hang(goc, them)
            for lo in kq["lo_moi"]:
                ghi_su_kien(goc, "lap_lo", kenh=lo["kenh_nguon"], video_id=lo["video_id"], nao_loai="chon",
                            noi_dung="video {0} đạt {1:,} lượt xem trong {2} giờ đầu → mời {3} kênh cộng sự (đợt A: {4}; "
                                     "đợt B sau {5} giờ: {6}); vùng «{7}»".format(
                                         lo["video_id"], lo["view_luc_kich"], int(cua_so),
                                         sum(1 for n in lo["nguoi_moi"] if n.get("dot")),
                                         ", ".join(n["kenh"] for n in lo["nguoi_moi"] if n.get("dot") == "A"),
                                         int(cai.get("gio_dot_b") or 24),
                                         ", ".join(n["kenh"] for n in lo["nguoi_moi"] if n.get("dot") == "B"),
                                         lo["vung"] or "?"),
                            so={"view": lo["view_luc_kich"], "nguong": nguong})
        try:
            kq["do"] = do_hieu_qua(goc, bay)
        except Exception as loi:  # noqa: BLE001
            kq["loi_do"] = str(loi)[:200]
        _ghi_json(os.path.join(thu_muc(goc), TEP_QUET), dict({k: v for k, v in kq.items() if k != "lo_moi"},
                                                                  lo_moi=[m["id"] for m in kq["lo_moi"]]))
    return kq


# ── việc cho máy DOM ────────────────────────────────────────────────────────

def _han_qua(n: Dict[str, Any], khoa: str, bay: _dt.datetime) -> bool:
    t = _doc_luc(n.get(khoa))
    return t is None or t <= bay


def viec_dom(goc: str, bay: Optional[_dt.datetime] = None, cai: Optional[Dict[str, Any]] = None,
             ds: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Việc tới hạn (thuần trên `ds`): `{"viec": "moi", "kenh": nguồn, id, video_id, nguoi: [...]}` — mời các kênh
    tới hạn (trong ngân sách ngày còn lại); `{"viec": "nhan", "kenh": kênh được mời, id, video_id, link, kenh_nguon}`."""
    bay = bay or _dt.datetime.now()
    cai = cai or doc_cai(goc)
    ds = doc_hang(goc) if ds is None else ds
    con = max(0, int(cai.get("toi_da_moi_ngay") or 30) - da_moi_hom_nay(ds, bay.date().isoformat()))
    toi_da_loi = int(cai.get("toi_da_loi") or 3)
    ra: List[Dict[str, Any]] = []
    for m in ds:
        if m.get("loai") != LOAI or m.get("trang_thai") != "mo":
            continue
        moi = []
        for n in m.get("nguoi_moi") or []:
            tt = n.get("trang_thai")
            if tt == TT_CHO and _han_qua(n, "han_moi", bay) and _han_qua(n, "thu_lai_luc", bay):
                moi.append(n)
            elif tt == TT_LOI and n.get("buoc_loi") == "moi" and int(n.get("lan_loi") or 0) < toi_da_loi \
                    and _han_qua(n, "thu_lai_luc", bay):
                moi.append(n)
        moi = moi[:con]
        con -= len(moi)
        if moi:
            ra.append({"viec": "moi", "kenh": m["kenh_nguon"], "id": m["id"], "video_id": m["video_id"],
                       "nguoi": [{"kenh": n["kenh"], "uc": n.get("uc"), "link_kenh": n.get("link_kenh") or
                                  link_kenh(n.get("uc") or "")} for n in moi]})
        for n in m.get("nguoi_moi") or []:
            tt = n.get("trang_thai")
            if (tt == TT_DA_MOI and _han_qua(n, "thu_lai_luc", bay)) or (
                    tt == TT_LOI and n.get("buoc_loi") == "nhan" and int(n.get("lan_loi") or 0) < toi_da_loi
                    and _han_qua(n, "thu_lai_luc", bay)):
                ra.append({"viec": "nhan", "kenh": n["kenh"], "id": m["id"], "video_id": m["video_id"],
                           "link": n.get("link") or "", "kenh_nguon": m["kenh_nguon"],
                           "uc_nguon": (uc_ghim(goc).get(m["kenh_nguon"]) or "")})
    return ra


def ghi_loi(goc: str, id_muc: str, kenh: str, buoc: str, ly_do: str, cai: Optional[Dict[str, Any]] = None) -> None:
    """Một thao tác hỏng: `loi` + hẹn thử lại sau `phut_thu_lai` × số lần (lùi dần)."""
    cai = cai or doc_cai(goc)
    lan = 0
    for m in doc_hang(goc):
        if m.get("id") == id_muc:
            lan = next((int(n.get("lan_loi") or 0) for n in m.get("nguoi_moi") or [] if n.get("kenh") == kenh), 0)
    bay = _dt.datetime.now()
    cap_nhat_nguoi(goc, id_muc, kenh, trang_thai=TT_LOI, buoc_loi=buoc, ly_do=str(ly_do)[:300], lan_loi=lan + 1,
                   thu_lai_luc=_luc(bay + _dt.timedelta(minutes=float(cai.get("phut_thu_lai") or 90) * (lan + 1))))


# ── đo hiệu quả ─────────────────────────────────────────────────────────────

def _chuoi(goc: str, kenh: str, metric: str) -> Dict[str, float]:
    try:
        from . import chi_so_kenh  # noqa: PLC0415
        return chi_so_kenh.chuoi_dai(goc, kenh, metric)
    except Exception:  # noqa: BLE001
        return {}


def _tb(c: Dict[str, float], tu: _dt.date, den: _dt.date) -> Optional[float]:
    x = [v for n, v in c.items() if tu <= _dt.date.fromisoformat(n) <= den]
    return sum(x) / len(x) if len(x) >= 3 or (x and (den - tu).days < 3) else None


def do_kenh(goc: str, kenh: str, moc: _dt.date, so_ngay: int = 7) -> Dict[str, Any]:
    """Tỉ lệ (sau ÷ 7 ngày trước) của view, đăng ký mới, hiển thị; ngày đầu riêng (`ngay1`) cho so A–B."""
    ra: Dict[str, Any] = {"moc": moc.isoformat()}
    for ten, metric in (("view", "EXTERNAL_VIEWS"), ("dang_ky", "SUBSCRIBERS_NET_CHANGE"),
                        ("hien_thi", "VIDEO_THUMBNAIL_IMPRESSIONS")):
        c = _chuoi(goc, kenh, metric)
        truoc = _tb(c, moc - _dt.timedelta(days=7), moc - _dt.timedelta(days=1))
        sau = _tb(c, moc, moc + _dt.timedelta(days=so_ngay - 1))
        n1 = c.get(moc.isoformat())
        ra[ten] = {"truoc_tb": None if truoc is None else round(truoc, 2),
                   "sau_tb": None if sau is None else round(sau, 2),
                   "ti_le": round(sau / truoc, 3) if truoc and sau is not None else None,
                   "ngay1": n1, "ti_le_ngay1": round(n1 / truoc, 3) if truoc and n1 is not None else None}
    return ra


def _ngay_studio(luc: Any) -> Optional[_dt.date]:
    """Ngày Studio (giờ Thái Bình Dương ≈ giờ máy − 14 giờ) của một mốc giờ máy."""
    t = _doc_luc(luc)
    return (t - _dt.timedelta(hours=14)).date() if t else None


def do_hieu_qua(goc: str, bay: Optional[_dt.datetime] = None, cai: Optional[Dict[str, Any]] = None
                ) -> List[Dict[str, Any]]:
    """Đo các lô đã đủ `ngay_do` + `ngay_tre_studio` ngày kể từ lúc đợt B được mời (hoặc lúc lập lô) mà chưa đo."""
    bay = bay or _dt.datetime.now()
    cai = cai or doc_cai(goc)
    can = int(cai.get("ngay_do") or 7) + int(cai.get("ngay_tre_studio") or 2) + int(round(float(cai.get("gio_dot_b") or 24) / 24))
    ds = doc_hang(goc)
    vua = []
    for m in ds:
        if m.get("loai") != LOAI or m.get("do_sau"):
            continue
        kich = _doc_luc(m.get("luc_kich"))
        if not kich or (bay - kich).days < can:
            continue
        nguoi = [n for n in m.get("nguoi_moi") or [] if n.get("dot")]
        dot_a = [n for n in nguoi if n.get("dot") == "A" and n.get("trang_thai") in TT_DANG_DO]
        dot_b = [n for n in nguoi if n.get("dot") == "B"]
        moc_a = min((d for d in (_ngay_studio(n.get("luc_nhan")) for n in dot_a) if d), default=None)
        kq_kenh = {}
        for n in nguoi:
            d0 = _ngay_studio(n.get("luc_nhan")) if n.get("trang_thai") in TT_DANG_DO else None
            if d0 is None:
                continue
            x = do_kenh(goc, n["kenh"], d0, int(cai.get("ngay_do") or 7))
            x.update(dot=n["dot"], trang_thai=n.get("trang_thai"), trang_chu_truoc=n.get("trang_chu_truoc"),
                     trang_chu_sau=ti_le_trang_chu(goc, n["kenh"]))
            try:
                x["gom_video_cong_tac"] = m["video_id"] in bang_tom_tat(goc, n["kenh"])
            except Exception:  # noqa: BLE001
                x["gom_video_cong_tac"] = None
            kq_kenh[n["kenh"]] = x
        ab: Dict[str, Any] = {"ngay": moc_a.isoformat() if moc_a else ""}
        if moc_a:
            for ten in ("view", "dang_ky"):
                a = [do_kenh(goc, n["kenh"], moc_a, 1)[ten]["ti_le_ngay1"] for n in dot_a]
                b = [do_kenh(goc, n["kenh"], moc_a, 1)[ten]["ti_le_ngay1"] for n in dot_b]
                a, b = [x for x in a if x is not None], [x for x in b if x is not None]
                ab[ten] = {"a_tv": statistics.median(a) if a else None, "b_tv": statistics.median(b) if b else None,
                           "n_a": len(a), "n_b": len(b),
                           "nang": round(statistics.median(a) - statistics.median(b), 3) if a and b else None}
        kn = _doc_luc(m.get("luc_kich")) or bay
        nguon = do_kenh(goc, m["kenh_nguon"], _ngay_studio(_luc(kn)) or kn.date(), int(cai.get("ngay_do") or 7))
        view_sau = _so((bang_tom_tat(goc, m["kenh_nguon"]).get(m["video_id"]) or {}).get("Lượt xem"))
        nang_v = (ab.get("view") or {}).get("nang")
        if nang_v is None:
            ket = "khong_du_so"
        elif nang_v >= 0.2:
            ket = "nang_ro"
        elif nang_v > 0:
            ket = "nang_nhe"
        else:
            ket = "chua_thay"
        goi_y = {"nang_ro": "cộng sự nâng rõ kênh đợt A so đợt B — có thể thử hạ ngưỡng (vd 15.000) hoặc mời hết một đợt",
                 "nang_nhe": "nâng nhẹ — giữ ngưỡng 20.000, đo thêm lô",
                 "chua_thay": "chưa thấy nâng — giữ ngưỡng, xem lại sau 3 lô",
                 "khong_du_so": "chưa đủ số Studio (kênh chưa nhận / thiếu chuỗi ngày)"}[ket]
        do = {"luc": _luc(bay), "ket": ket, "goi_y": goi_y, "a_b": ab, "kenh": kq_kenh, "nguon": nguon,
              "view_video_sau": view_sau, "view_video_luc_kich": m.get("view_luc_kich")}
        m["do_sau"] = do
        vua.append(m)
        ghi_su_kien(goc, "do", kenh=m["kenh_nguon"], video_id=m["video_id"], nao_loai="do",
                    noi_dung="cộng sự video {0}: {1} — A–B view ngày 1 nâng {2}, đăng ký nâng {3}; {4}".format(
                        m["video_id"], ket, nang_v, (ab.get("dang_ky") or {}).get("nang"), goi_y),
                    so={"nang_view": nang_v, "nang_dk": (ab.get("dang_ky") or {}).get("nang")})
    if vua:
        def ghi(ds2):
            moi = {m["id"]: m.get("do_sau") for m in vua}
            for m in ds2:
                if m.get("id") in moi:
                    m["do_sau"] = moi[m["id"]]
        sua_hang(goc, ghi)
    return vua


# ── tự kiểm (core/tu_kiem.py gọi) ───────────────────────────────────────────

_RE_UC = re.compile(r"UC[A-Za-z0-9_-]{22}")


def _doi_tuong_json(html: str, dau: int) -> str:
    """Chuỗi một đối tượng JSON bắt đầu ở `{` thứ nhất từ `dau` (đếm ngoặc, bỏ qua chuỗi) — "" nếu hỏng."""
    i = html.find("{", dau)
    if i < 0:
        return ""
    sau, trong_chuoi, thoat = 0, False, False
    for j in range(i, min(len(html), i + 400000)):
        c = html[j]
        if trong_chuoi:
            if thoat:
                thoat = False
            elif c == "\\":
                thoat = True
            elif c == '"':
                trong_chuoi = False
        elif c == '"':
            trong_chuoi = True
        elif c == "{":
            sau += 1
        elif c == "}":
            sau -= 1
            if sau == 0:
                return html[i:j + 1]
    return ""


def uc_ghi_cong(html: str) -> List[str]:
    """UC các kênh được GHI CÔNG trên trang xem công khai (thuần). Đo 21/10/2026: video có cộng sự thì
    `videoOwnerRenderer.navigationEndpoint.showDialogCommand` mở hộp «コラボレーター/Collaborators» liệt kê chủ +
    từng cộng sự (`listItemViewModel` có nút đăng ký riêng, `browseEndpoint.browseId`). CHỈ đọc khối chủ video —
    video đề xuất cũng có hộp cộng tác của kênh khác (`avatarStackViewModel`)."""
    m = re.search(r'"videoOwnerRenderer"\s*:', html)
    if not m:
        return []
    khoi = _doi_tuong_json(html, m.end())
    ra: List[str] = []
    for uc in re.findall(r'"browseId"\s*:\s*"(UC[A-Za-z0-9_-]{22})"', khoi):
        if uc not in ra:
            ra.append(uc)
    return ra


def xac_minh_cong_khai(vid: str, ucs: Sequence[str], tai: Optional[Tai] = None) -> Dict[str, Any]:
    """`{ma, thay: [uc…], thieu: [uc…]}` — kênh cộng sự có được ghi công trên trang xem công khai không."""
    ma, du = (tai or tai_that)("https://www.youtube.com/watch?v={0}&hl=en".format(vid))
    if ma != 200 or not du:
        return {"ma": ma, "thay": [], "thieu": list(ucs)}
    co = set(uc_ghi_cong(du.decode("utf-8", "replace")))
    return {"ma": ma, "thay": [u for u in ucs if u in co], "thieu": [u for u in ucs if u not in co]}


def muc_tu_kiem(goc: str, bay: _dt.datetime, tai: Optional[Tai] = None, ghi: bool = True) -> List[Dict[str, Any]]:
    """Kỳ vọng cho `core.tu_kiem` (dict thô — tu_kiem bọc lại): lời mời chờ nhận > `gio_cho_nhan` giờ; kênh đã nhận
    mà trang xem công khai chưa ghi công (kiểm lại một lần mỗi lượt, đạt thì ghi `xac_minh`); dừng khẩn."""
    cai = doc_cai(goc)
    ra: List[Dict[str, Any]] = []
    d = dang_dung(goc)
    if d:
        ra.append({"khoa": "cong_su:dung", "kenh": d.get("kenh") or "", "tt": "hong", "nguoi": True,
                   "viec": "cộng sự (Collaborators) đang DỪNG", "bang_chung": d.get("ly_do") or "",
                   "can_lam": "xem hộp YouTube báo ({0}); ổn thì xoá workspace/cong-su/dung.json".format(
                       d.get("bang_chung") or "vm/logs/dom")})
    gio_cho = float(cai.get("gio_cho_nhan") or 48)
    for m in doc_hang(goc):
        if m.get("loai") != LOAI:
            continue
        cho_xm = []
        for n in m.get("nguoi_moi") or []:
            khoa = "cong_su:{0}:{1}".format(m["video_id"], n["kenh"])
            viec = "cộng sự {0} trên video {1} của {2}".format(n["kenh"], m["video_id"], m["kenh_nguon"])
            tt = n.get("trang_thai")
            if tt == TT_DA_MOI:
                luc = _doc_luc(n.get("luc_moi"))
                if luc and (bay - luc).total_seconds() / 3600.0 > gio_cho:
                    ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "hong", "viec": viec, "thu_lai": "cong_su",
                               "id_muc": m["id"], "kenh_moi": n["kenh"],
                               "bang_chung": "lời mời gửi {0} chưa được nhận sau {1:.0f} giờ".format(n.get("luc_moi"), gio_cho)})
                else:
                    ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "cho", "viec": viec,
                               "bang_chung": "đã mời {0}, chờ nhận".format(n.get("luc_moi") or "")})
            elif tt == TT_DA_NHAN:
                cho_xm.append(n)
            elif tt == TT_XAC_MINH:
                ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "dat", "viec": viec,
                           "bang_chung": "trang xem ghi công từ {0}".format(n.get("luc_xac_minh") or "")})
            elif tt == TT_LOI and int(n.get("lan_loi") or 0) >= int(cai.get("toi_da_loi") or 3):
                ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "hong", "viec": viec,
                           "bang_chung": "hỏng {0} lần ở bước {1}: {2}".format(n.get("lan_loi"), n.get("buoc_loi"),
                                                                            n.get("ly_do") or ""),
                           "nguoi": bool(n.get("can_nguoi")), "can_lam": n.get("can_lam") or ""})
            elif tt == TT_BO_QUA and n.get("can_nguoi"):
                ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "cho", "viec": viec, "nguoi": True,
                           "bang_chung": n.get("ly_do") or "", "can_lam": n.get("can_lam") or ""})
        if cho_xm:
            xm = xac_minh_cong_khai(m["video_id"], [n.get("uc") or "" for n in cho_xm], tai)
            for n in cho_xm:
                khoa = "cong_su:{0}:{1}".format(m["video_id"], n["kenh"])
                viec = "cộng sự {0} trên video {1} của {2}".format(n["kenh"], m["video_id"], m["kenh_nguon"])
                if n.get("uc") in xm["thay"] and ghi:
                    try:
                        cap_nhat_nguoi(goc, m["id"], n["kenh"], trang_thai=TT_XAC_MINH, luc_xac_minh=_luc(bay))
                    except RuntimeError:
                        pass
                    ghi_su_kien(goc, "xac_minh", kenh=n["kenh"], video_id=m["video_id"], nao_loai="ket_qua",
                                noi_dung="trang xem công khai của {0} ghi công kênh cộng sự {1}".format(
                                    m["video_id"], n["kenh"]))
                if n.get("uc") in xm["thay"]:
                    ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "dat", "viec": viec,
                               "bang_chung": "trang xem công khai ghi công kênh"})
                else:
                    luc = _doc_luc(n.get("luc_nhan"))
                    qua = luc is not None and (bay - luc).total_seconds() > 6 * 3600
                    ra.append({"khoa": khoa, "kenh": n["kenh"], "tt": "hong" if qua else "cho", "viec": viec,
                               "bang_chung": "đã nhận {0} mà trang xem (HTTP {1}) chưa ghi công".format(
                                   n.get("luc_nhan") or "", xm["ma"])})
    return ra


def thu_lai_nhan(goc: str, id_muc: str, kenh: str, cai: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """Tự kiểm: lời mời quá hạn chưa nhận → hẹn lượt nhận lại NGAY (một lần, `so_thu_lai`); hết lượt → False."""
    cai = cai or doc_cai(goc)
    for m in doc_hang(goc):
        if m.get("id") != id_muc:
            continue
        n = next((x for x in m.get("nguoi_moi") or [] if x.get("kenh") == kenh), None)
        if n is None:
            return False, "không còn kênh này trong lô"
        if int(n.get("lan_thu_lai") or 0) >= int(cai.get("so_thu_lai") or 1):
            return False, "đã thử nhận lại {0} lần — báo người".format(n.get("lan_thu_lai"))
        cap_nhat_nguoi(goc, id_muc, kenh, lan_thu_lai=int(n.get("lan_thu_lai") or 0) + 1,
                       thu_lai_luc=_luc(_dt.datetime.now()), luc_moi=_luc(_dt.datetime.now()))
        return True, "hẹn máy DOM mở lại lời mời trên Chrome kênh {0}".format(kenh)
    return False, "không còn mục"


# ── điều kiện skill (chỉ đọc đĩa) ───────────────────────────────────────────

def can_quet(goc: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """D25: có video ≤ 48 giờ tuổi (sổ máy đăng) hoặc lô chờ đo — và lượt quét cuối đã cũ ≥ 50 phút."""
    bay = bay or _dt.datetime.now()
    cai = doc_cai(goc)
    if not cai.get("bat", True):
        return False, "cài đặt cong_su.bat = false"
    q = _doc_json(os.path.join(thu_muc(goc), TEP_QUET)) or {}
    cuoi = _doc_luc(q.get("luc")) if isinstance(q, dict) else None
    if cuoi and (bay - cuoi).total_seconds() < 50 * 60:
        return False, "vừa quét {0}".format(q.get("luc"))
    kenh = list(kenh_hoat_dong(goc))
    moi = [v for v in video_gan_day(goc, bay, float(cai["gio_cua_so"]), kenh) if v.get("nguon") == "so_may_dang"]
    cho_do = [m for m in doc_hang(goc) if m.get("loai") == LOAI and not m.get("do_sau")]
    if not moi and not cho_do:
        return False, "không có video ≤ {0} giờ tuổi, không lô chờ đo".format(cai["gio_cua_so"])
    return True, "{0} video ≤ {1} giờ tuổi · {2} lô chờ đo".format(len(moi), cai["gio_cua_so"], len(cho_do))


def can_dom(goc: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str]:
    """D26: có việc mời/nhận tới hạn, không dừng khẩn, ngoài khung giờ cấm."""
    bay = bay or _dt.datetime.now()
    cai = doc_cai(goc)
    if not cai.get("bat", True):
        return False, "cài đặt cong_su.bat = false"
    d = dang_dung(goc)
    if d:
        return False, "DỪNG: " + str(d.get("ly_do") or "")[:100]
    cam = trong_gio_cam(bay, cai)
    if cam:
        return False, cam
    v = viec_dom(goc, bay, cai)
    if not v:
        return False, "không có lời mời/nhận tới hạn"
    return True, "{0} việc mời · {1} việc nhận".format(sum(1 for x in v if x["viec"] == "moi"),
                                                       sum(1 for x in v if x["viec"] == "nhan"))


# ── CLI ─────────────────────────────────────────────────────────────────────

def _in_quet(kq: Dict[str, Any]) -> None:
    print("lượt quét {0}{1}".format(kq["luc"], " (THỬ — không ghi)" if kq.get("thu") else ""))
    for v in kq["video"]:
        print("  {0:<10} {1} · {2} lượt xem ({3}) · {4} giờ tuổi".format(v["kenh"], v["video_id"], v["view"],
                                                                          v["nguon_view"], v["tuoi_gio"]))
    for b in kq["bo"]:
        print("  BỎ {0}/{1}: {2}".format(b["kenh"], b["video_id"], b["ly_do"]))
    for lo in kq["lo_moi"]:
        print("  LÔ MỚI {0} ({1}, {2:,} lượt xem, vùng «{3}»):".format(lo["video_id"], lo["kenh_nguon"],
                                                                       lo["view_luc_kich"], lo["vung"]))
        for n in lo["nguoi_moi"]:
            print("    {0:<10} {1:<2} {2:<7} {3}".format(n["kenh"], n.get("dot") or "-", n["trang_thai"],
                                                       n.get("ly_do_chon") or n.get("ly_do") or ""))
    if not kq["video"]:
        print("  (không có video ≤ cửa sổ)")


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(prog="python -m core.cong_su")
    ap.add_argument("lenh", choices=("quet", "xem", "viec", "do"))
    ap.add_argument("--thu", action="store_true", help="quet: chỉ đọc + in lô SẼ lập, không ghi")
    ap.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    if a.lenh == "quet":
        kq = quet(a.goc, thu=a.thu, nk=print)
        _in_quet(kq)
        return 0
    if a.lenh == "viec":
        for v in viec_dom(a.goc):
            print(json.dumps(v, ensure_ascii=False))
        return 0
    if a.lenh == "do":
        for m in do_hieu_qua(a.goc):
            print(m["id"], (m.get("do_sau") or {}).get("ket"))
        return 0
    for m in doc_hang(a.goc):
        print("{0} {1} {2} view {3} · {4}".format(m["id"], m["kenh_nguon"], m.get("trang_thai"), m.get("view_luc_kich"),
                                                 ", ".join("{0}:{1}{2}".format(n["kenh"], n.get("dot") or "-", "/" + n["trang_thai"])
                                                           for n in m.get("nguoi_moi") or [])))
    d = dang_dung(goc=a.goc)
    if d:
        print("DỪNG:", d.get("ly_do"))
    return 0


if __name__ == "__main__":
    if os.path.dirname(os.path.dirname(os.path.abspath(__file__))) not in sys.path:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    raise SystemExit(main())
