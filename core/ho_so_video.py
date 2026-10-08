"""Hồ sơ video + nối số liệu Studio — Việc 3 của
`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

═══ VÌ SAO CÓ TỆP NÀY ═══

Mọi thứ tool quyết định cho một video (bản kịch bản nào thắng, ảnh bìa concept
gì, nghỉ mấy giây giữa các phần…) đến giờ chỉ sống trong thư mục lượt sản xuất
`PROJECTS/AUTO/<kênh>/<lượt>/` — và thư mục đó bị `core/don_dep.py` xoá sau khi
đăng. Khi số liệu Studio (CTR/AVD) về sau đó vài ngày, không còn gì để nối "video
này CTR bao nhiêu" với "ảnh bìa/tiêu đề nào tool đã chọn cho nó" — vòng học
(`core/bai_hoc_san_xuat.py`, `core/khuon_bia.py`) phải mò lại đúng lúc bằng
chứng đã mất.

`tao_ho_so()` chụp một BẢN SAO nhẹ, bền, KHÔNG phụ thuộc `PROJECTS/AUTO` còn
sống hay không — ghi ngay khi bàn giao (`ban_giao_dang.ban_giao`, còn đầy đủ
mọi tệp) vào `CHANNEL/<kênh>/ho-so-video/<mã gói>.json`, một thư mục
`core/don_dep*.py` KHÔNG BAO GIỜ đụng vào (không nằm trong danh sách được dọn —
xem `core/don_dep.py`, `core/don_dep_mo_rong.py`).

`cap_nhat_chi_so()` sau đó nối từng hồ sơ với `video_id` thật (qua tiêu đề,
`chi_so_ytb.doc_kenh`) và điền số liệu tại 4 mốc chuẩn 24h/48h/72h/7 ngày —
gọi lại nhiều lần vẫn an toàn (idempotent), số liệu chỉ TĂNG DẦN như chính
Studio.

`bu_ho_so()` bù hồ sơ cho các gói đã đăng TRƯỚC KHI tệp này tồn tại — đọc lại
`PROJECTS/AUTO/<kênh>/<lượt>/` nếu còn, lùi về bản tối giản (DONE + kế hoạch)
nếu thư mục lượt đã bị dọn.

Không gọi mạng, không phụ thuộc Qt — thuần đọc/ghi đĩa (trừ một lượt `ffmpeg -i`
rất rẻ để đo thời lượng/độ phân giải, không giải mã hình). Mọi hàm ở đây được
gọi từ `core/vong_hoc.py` (Việc 3) — không bước nào được phép ném lỗi ra ngoài
làm chặn sản xuất, nhưng CHÍNH module này vẫn để lỗi cục bộ nổi lên (try/except
ở nơi gọi, không phải ở đây) — mỗi hàm là MỘT việc rõ ràng, dễ kiểm độc lập.
"""

from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import ban_giao_dang
from . import chi_so_ytb as _chi_so
from . import ke_hoach_dang
from . import kenh as _kenh_mod
from . import qa_truoc_dang
from .auto_khau import KIEU_THUMB

__all__ = [
    "duong_thu_muc_ho_so", "duong_tep_ho_so", "duong_anh_ho_so", "doc_ho_so",
    "tao_ho_so", "ghi_video_id", "cap_nhat_chi_so", "bu_ho_so",
    "doc_bang_hieu_suat_tieu_de", "nguon_cua_goi",
    "ghi_sua", "do_truoc_sau", "duong_bia_2_ho_so",
]

#: Khung mốc giờ chuẩn dùng để gộp số liệu Studio (mục 2.2, Việc 3 bản thiết
#: kế): `(tên mốc, giờ thấp nhất bao gồm, giờ cao nhất KHÔNG bao gồm)`. Một
#: video có thể có nhiều lần chụp rơi vào cùng một khung — bản chụp MUỘN NHẤT
#: (Studio chỉ tăng dần) thắng, xem `cap_nhat_chi_so`.
_KHUNG_MOC: Tuple[Tuple[str, float, float], ...] = (
    ("24h", 18.0, 36.0), ("48h", 36.0, 60.0), ("72h", 60.0, 96.0), ("7d", 144.0, 240.0),
)

#: Trần "gần đây" mà vòng học/`doc_bang_hieu_suat_tieu_de` còn quan tâm — 30
#: ngày. Quá mốc này thì KHÔNG bucket nữa (không phải vì mất, mà vì không ai
#: còn đọc số liệu video 31 ngày tuổi qua đường này).
_GIO_TRAN_NGAY_GAN_DAY = 720.0

#: Bản chụp gần nhất của một hồ sơ CŨ hơn ngần này GIỜ thì vẫn dùng được (số
#: liệu Studio chỉ tăng dần, không sai) — chỉ ghi log để chủ dự án biết đang
#: nhìn số của ngày nào, không phải lỗi.
NGUONG_GIO_SO_LIEU_CU = 36.0

_RE_THUMB_SO = re.compile(r"thumb_(\d+)\.", re.IGNORECASE)


# ── Tiện ích đọc/ghi đĩa dùng chung ─────────────────────────────────────────


def _doc(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            return tep.read()
    except OSError:
        return ""


def _doc_json(duong: str) -> Optional[Any]:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, obj: Dict[str, Any]) -> None:
    """Ghi nguyên tử `.tmp` + `os.replace` — cùng khuôn `core/chon_content.py._luu`."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)


def duong_thu_muc_ho_so(goc: str, kenh: str) -> str:
    return os.path.join(_kenh_mod.duong_kenh(goc, kenh), "ho-so-video")


def duong_tep_ho_so(goc: str, kenh: str, ma_goi: str) -> str:
    return os.path.join(duong_thu_muc_ho_so(goc, kenh), "{0}.json".format(ma_goi))


def duong_anh_ho_so(goc: str, kenh: str, ma_goi: str) -> str:
    """Bản sao ảnh bìa LÂU DÀI — luôn `.jpg` (dữ liệu thumbnail của tool vốn
    là JPEG dù tên nguồn mang đuôi `.png`, xem "Hiện trạng" mục 0 bản thiết kế)."""
    return os.path.join(duong_thu_muc_ho_so(goc, kenh), "anh", "{0}.jpg".format(ma_goi))


def doc_ho_so(goc: str, kenh: str, ma_goi: str) -> Optional[Dict[str, Any]]:
    return _doc_json(duong_tep_ho_so(goc, kenh, ma_goi))


def _luu_ho_so(goc: str, kenh: str, ma_goi: str, ho_so: Dict[str, Any]) -> str:
    duong = duong_tep_ho_so(goc, kenh, ma_goi)
    _ghi_json(duong, ho_so)
    return duong


def _sao_luu_anh_bia(goc: str, kenh: str, ma_goi: str, duong_anh: str) -> None:
    """Chép ảnh bìa đang dùng sang `ho-so-video/anh/` — sống lâu hơn lượt sản
    xuất. Lỗi đọc/ghi ảnh (đĩa đầy, tệp khoá…) không được làm hỏng cả hồ sơ."""
    if not duong_anh or not os.path.isfile(duong_anh):
        return
    dich = duong_anh_ho_so(goc, kenh, ma_goi)
    try:
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        tam = dich + ".tmp"
        shutil.copy2(duong_anh, tam)
        os.replace(tam, dich)
    except OSError:
        pass


def duong_bia_2_ho_so(goc: str, kenh: str, ma_goi: str) -> str:
    """Bản sao bìa HẠNG NHÌ của giám khảo — `ho-so-video/anh/<mã gói>-bia-2.jpg`."""
    return os.path.join(duong_thu_muc_ho_so(goc, kenh), "anh", "{0}-bia-2.jpg".format(ma_goi))


def _sao_luu_bia_2(goc: str, kenh: str, ma_goi: str, duong_anh: str) -> Optional[Dict[str, Any]]:
    """Chép bìa hạng nhì (theo `chon-bia.json`: điểm cao nhất sau tấm được chọn, không bị loại) sang
    `anh/<mã gói>-bia-2.jpg` — giám đốc kênh đổi bìa video trượt mà không tốn tiền sinh lại.
    Không có bản chấm / không có tấm nhì / lỗi đĩa → None (metadata phụ, không chặn hồ sơ)."""
    try:
        from . import chon_bia  # noqa: PLC0415

        thu_muc = os.path.dirname(duong_anh)
        du = chon_bia.doc_chon_bia(thu_muc) or {}
        so_chon = (du.get("chon") or {}).get("so")
        ds = [u for u in du.get("ung_vien") or [] if isinstance(u, dict) and not u.get("loai")
              and u.get("so") is not None and u.get("so") != so_chon and u.get("tong_diem") is not None]
        if not ds:
            return None
        nhi = max(ds, key=lambda u: float(u["tong_diem"]))
        nguon = next((os.path.join(thu_muc, t) for t in sorted(os.listdir(thu_muc))
                      if not t.upper().startswith("CHON-") and _RE_THUMB_SO.match(t)
                      and int(_RE_THUMB_SO.match(t).group(1)) == int(nhi["so"])
                      and os.path.splitext(t)[1].lower() in (".png", ".jpg", ".jpeg", ".webp")), "")
        if not nguon:
            return None
        dich = duong_bia_2_ho_so(goc, kenh, ma_goi)
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        shutil.copy2(nguon, dich + ".tmp")
        os.replace(dich + ".tmp", dich)
        return {"tep": os.path.basename(nguon), "so": nhi["so"], "kieu": str(nhi.get("kieu") or ""),
                "nhom": str(nhi.get("nhom") or ""), "tong_diem": nhi.get("tong_diem"),
                "anh": os.path.join("anh", os.path.basename(dich)).replace("\\", "/")}
    except Exception:  # noqa: BLE001 — bìa nhì là phụ
        return None


# ── Đọc dữ liệu từ thư mục lượt sản xuất ────────────────────────────────────


def _doc_tieu_de_va_bia(thu_muc_luot: str) -> Tuple[str, str]:
    """`(tiêu đề, chữ bìa)` từ `1-tieu-de.txt` — dòng `TITLE:`/`THUMB:`."""
    tieu_de, chu_bia = "", ""
    for dong in _doc(os.path.join(thu_muc_luot, "1-tieu-de.txt")).splitlines():
        d = dong.strip()
        if d.startswith("TITLE:"):
            tieu_de = d[len("TITLE:"):].strip()
        elif d.startswith("THUMB:"):
            chu_bia = d[len("THUMB:"):].strip()
    return tieu_de, chu_bia


_RE_KY_TU = re.compile(r"Bản\s+([A-Za-z]):\s*(\d+)\s*ký tự")
_RE_CHON = re.compile(r"Chọn:\s*bản\s+([A-Za-z])")
_RE_CHON_HOOK = re.compile(r"Chọn hook:\s*bản\s+([A-Za-z])")
_RE_DIEM = re.compile(r"Điểm:\s*(\{[^\n]*\})")


def _doc_cham_diem(duong: str) -> Dict[str, Any]:
    """Rút từ `1-cham-diem.txt` (văn bản tự do, không phải JSON): số ký tự mỗi
    bản kịch bản, bản được chọn + điểm giám khảo, và cùng bộ cho hook — tách
    hai phần bằng dòng chia `── HOOK ──` mà lời nhắc chấm luôn in ra.

    Tệp hỏng/thiếu/đổi khuôn chữ: trả khung rỗng, không ném lỗi — đây là
    METADATA phụ, thiếu nó không được chặn cả hồ sơ.
    """
    ra: Dict[str, Any] = {"so_ky_tu": {}, "ban_chon": "", "diem": {},
                          "ky_tu_ban_chon": None, "hook_chon": "", "hook_diem": {}}
    chu = _doc(duong)
    if not chu:
        return ra
    phan_kb, co_hook, phan_hook = chu.partition("── HOOK ──")
    for m in _RE_KY_TU.finditer(phan_kb):
        ra["so_ky_tu"][m.group(1).upper()] = int(m.group(2))
    m = _RE_CHON.search(phan_kb)
    if m:
        ra["ban_chon"] = m.group(1).upper()
        ra["ky_tu_ban_chon"] = ra["so_ky_tu"].get(ra["ban_chon"])
    m = _RE_DIEM.search(phan_kb)
    if m:
        try:
            ra["diem"] = json.loads(m.group(1))
        except (ValueError, TypeError):
            pass
    if co_hook:
        m = _RE_CHON_HOOK.search(phan_hook)
        if m:
            ra["hook_chon"] = m.group(1).upper()
        m = _RE_DIEM.search(phan_hook)
        if m:
            try:
                ra["hook_diem"] = json.loads(m.group(1))
            except (ValueError, TypeError):
                pass
    return ra


def _doc_phan(thu_muc_luot: str) -> Optional[Dict[str, Any]]:
    """Mốc từng PHẦN của video, từ `8-phan.json` (khâu dựng đã ghi) — không có
    thì lùi về `2-phan.json` (khâu giọng, chưa qua khâu dựng). Cả hai đều là
    sản phẩm của Việc 2 (`core/phan_video.py`) — kênh/lượt chưa dựng theo phần
    thì trả `None`, không suy diễn."""
    for ten in ("8-phan.json", "2-phan.json"):
        du = _doc_json(os.path.join(thu_muc_luot, ten))
        if not isinstance(du, dict):
            continue
        phan = du.get("phan")
        if not isinstance(phan, list):
            continue
        danh_sach = []
        for p in phan:
            if not isinstance(p, dict):
                continue
            bd, hl = p.get("bat_dau"), p.get("het_loi")
            giay = (round(hl - bd, 3)
                    if isinstance(bd, (int, float)) and isinstance(hl, (int, float)) else None)
            danh_sach.append({"so": p.get("so"), "nhan": p.get("nhan") or "",
                              "bat_dau": bd, "het_loi": hl, "giay": giay})
        return {"nguon": ten, "giay_nghi": du.get("giay_nghi"), "danh_sach": danh_sach}
    return None


def _version_desc_tu_ten_anh(ten_tep: str) -> str:
    """`CHON-thumb_002.png` → `dramatic_scene` — cùng cách suy diễn với
    `core/bai_hoc_san_xuat._version_desc_tu_ten_anh` (nhân đôi có chủ ý: hai
    module không nên nhập hàm riêng của nhau, xem docstring đầu tệp đó)."""
    ten = ten_tep[5:] if ten_tep.upper().startswith("CHON-") else ten_tep
    m = _RE_THUMB_SO.match(ten)
    if not m:
        return ""
    idx = int(m.group(1)) - 1
    if 0 <= idx < len(KIEU_THUMB):
        return KIEU_THUMB[idx][0]
    return ""


def _thong_tin_chon_bia(duong_anh: str) -> Dict[str, Any]:
    """Điểm/lý do/người chọn của ảnh bìa ĐANG DÙNG — đọc `chon-bia.json`
    (Việc 4, `core.chon_bia.chon`) nếu có, nằm CẠNH chính ảnh đó.

    Thêm 29/09/2026 (Việc 4) — hàm MỚI, không đổi chữ ký hàm nào có sẵn.
    Không có tệp/không khớp đúng ảnh đang dùng thì trả khung rỗng như cũ,
    không suy diễn.
    """
    rong = {"chon_boi": "", "diem_giam_khao": None, "ly_do": "", "khuon_thang_dung": False,
            "kieu": "", "nhom": "", "theo_khuon": None, "tham_do": None}
    try:
        from . import chon_bia  # noqa: PLC0415 — tránh vòng nhập lúc nạp module
        du = chon_bia.doc_chon_bia(os.path.dirname(duong_anh))
    except Exception:  # noqa: BLE001 — Việc 4 chưa chạy/hỏng thì coi như không có
        return rong
    if not isinstance(du, dict):
        return rong
    chon = du.get("chon") or {}
    if not isinstance(chon, dict) or chon.get("tep") != os.path.basename(duong_anh):
        return rong
    # "kham_pha" vẫn là AI chọn (chỉ khác lý do) — gộp về đúng ba giá trị
    # hồ sơ video dùng: "ai" | "nguoi" | "luat".
    chon_boi = str(chon.get("chon_boi") or "")
    chon_boi = "ai" if chon_boi in ("ai", "kham_pha") else chon_boi
    return {
        "chon_boi": chon_boi, "diem_giam_khao": chon.get("tong_diem"),
        "ly_do": str(chon.get("ly_do") or ""),
        "khuon_thang_dung": bool(chon.get("theo_khuon")) or chon.get("kieu") == "khuon_thang",
        # 30/09/2026 (`core/bia_theo_khuon.py`): tấm theo khuôn/chuẩn ngách đánh số 7..18
        # (ngoài mối nối vị trí KIEU_THUMB) — kiểu/nhóm lấy thẳng từ bản ghi chọn.
        "kieu": str(chon.get("kieu") or ""), "nhom": str(chon.get("nhom") or ""),
        "theo_khuon": chon.get("theo_khuon"), "tham_do": chon.get("tham_do"),
    }


def _doc_duoc_bia(duong_anh: str, bc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """09/10/2026 (`core/do_bia.py`): độ ĐỌC ĐƯỢC của bìa đang dùng — `bia_diem` (0–100),
    `bia_tuong_phan_min` (WCAG, dòng tệ nhất), `bia_doc_duoc` (cao|vua|thap — trục học `tu_hoc`),
    `bia_do` (chinh_xac | mu). Đo hỏng / không dò ra chữ → khung rỗng (không bịa)."""
    try:
        from . import do_bia  # noqa: PLC0415

        bc = bc if bc is not None else do_bia.cham_tep(duong_anh)
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(bc, dict) or bc.get("dat") is None:
        return {}
    return {"bia_diem": bc.get("diem"), "bia_tuong_phan_min": bc.get("tuong_phan_min"),
            "bia_doc_duoc": bc.get("doc_duoc") or "", "bia_do": bc.get("cach") or ""}


def cap_nhat_bia_doc_duoc(goc: str, kenh: str, ma_goi: str, bc: Dict[str, Any]) -> bool:
    """Ghi lại độ đọc được của bìa (vd sau khi đổi sang bìa vẽ lại `do_bia --lam-lai`). False nếu chưa có hồ sơ."""
    ho_so = doc_ho_so(goc, kenh, ma_goi)
    if not ho_so:
        return False
    th = ho_so.get("thumbnail") if isinstance(ho_so.get("thumbnail"), dict) else {}
    th.update(_doc_duoc_bia("", bc))
    ho_so["thumbnail"] = th
    _luu_ho_so(goc, kenh, ma_goi, ho_so)
    return True


def _thong_tin_video(goc: str, duong_video: str) -> Dict[str, Any]:
    """`{thoi_luong_giay, rong, cao}` đọc bằng `ffmpeg -i` (không ffprobe, xem
    "Hiện trạng" mục 0 bản thiết kế) — tái dùng đúng bộ đọc của cổng QA
    (`core.qa_truoc_dang.doc_thong_tin_media`) thay vì viết lại lần hai."""
    try:
        from .dung_video import tim_ffmpeg  # noqa: PLC0415 — tránh nạp khi không cần
        ffmpeg = tim_ffmpeg(goc)
        if not ffmpeg:
            return {}
        tt = qa_truoc_dang.doc_thong_tin_media(ffmpeg, duong_video)
        if tt.mo_duoc:
            return {"thoi_luong_giay": round(tt.giay, 1), "rong": tt.rong, "cao": tt.cao}
    except Exception:  # noqa: BLE001 — metadata phụ, không được chặn hồ sơ
        pass
    return {}


def _khung_ho_so(kenh: str, ma_goi: str, *, luc: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Bộ khung ĐẦY ĐỦ trường — mọi hồ sơ (dù xây từ lượt còn sống hay bù tối
    giản) đều có cùng lược đồ, để nơi đọc (`bai_hoc_san_xuat`, `khuon_bia`)
    không phải `dict.get` phòng thủ nhiều tầng."""
    return {
        "ma_goi": ma_goi, "kenh": kenh, "luot": "",
        "tao_luc": (luc or _dt.datetime.now()).replace(microsecond=0).isoformat(),
        "tieu_de": "", "chu_bia": "", "tieu_de_cham": None,
        "kich_ban": {"so_ky_tu": {}, "ban_chon": "", "diem": {},
                    "ky_tu_ban_chon": None, "hook_chon": "", "hook_diem": {}},
        "phan": None, "nhac": None,
        "giay_nghi_phan": None, "chuyen_phan": "",
        "thumbnail": {"tep": "", "kieu": "", "chon_boi": "", "diem_giam_khao": None,
                     "ly_do": "", "khuon_thang_dung": False},
        "thoi_luong_giay": None, "rong": None, "cao": None,
        "video_id": None, "chi_so": {}, "so_lieu_moi_nhat": None,
        # 30/09/2026 (B4 bộ máy chiến lược): công thức đã chọn nguồn của video + lượt đó có phải
        # lượt THĂM DÒ không — tra qua sổ lượt (`nguon_cua_goi`). Hồ sơ cũ thiếu hai khoá này vẫn
        # đúng: `core.chien_luoc.ket_qua` nối lại qua sổ lượt, không đọc hai khoá này.
        "cong_thuc": "", "tham_do": False,
        # 01/10/2026 (giám đốc kênh): mọi lần sửa tiêu đề/bìa trên Studio (`ghi_sua`, đo trước/sau ở
        # `cap_nhat_chi_so`) + id thí nghiệm đang mở lúc video ra đời (cách nhau dấu phẩy; rỗng = không).
        "lich_su_sua": [], "thi_nghiem": "",
        # bìa hạng nhì của giám khảo (`anh/<mã gói>-bia-2.jpg`) — đổi bìa không tốn tiền sinh lại.
        "bia_2": None,
        # 06/10/2026: "<n>/<tổng cảnh>" cảnh dựng TỪ ẢNH (engine clip hết hạn mức tới hạn
        # chót, `core/clip_tu_anh.py`); None = mọi cảnh là clip engine thật.
        "clip_tu_anh": None,
    }


def nguon_cua_goi(goc: str, kenh: str) -> Dict[str, Dict[str, Any]]:
    """`{mã gói "<kênh>-<lượt>": {link, ma, tieu_de, cong_thuc, tham_do, nguon, ngay, bo}}` — nối từ sổ
    tự chạy (`CHANNEL/<k>/tu-chay/<ngày>.json`) và `PROJECTS/AUTO/<kênh>/<lượt>/trang-thai.json`.

    Chép logic `bien_tap_content._nguon_cua_goi` (30/09/2026 — tệp ấy đang có agent khác sửa; bước
    B5 cho nó gọi hàm này thay bản riêng), thêm:
      * `cong_thuc` = `run.nguon.cong_thuc`, lùi về `run.nguon.nguon` (sổ cũ trước bộ máy chiến
        lược chỉ có nhãn này — nhờ vậy thống kê theo công thức áp NGƯỢC được cho video cũ);
        dòng lùi từ `trang-thai.json` không biết công thức → `""`;
      * `tham_do` (bool), `nguon` (nhãn gốc), `ngay` (tên tệp sổ, `YYYY-MM-DD`; `""` nếu lùi),
        `bo` (lượt đã bị đánh dấu bỏ — không ra video);
      * lượt có `ban_giao.ma_goi` thật THẮNG lượt chỉ suy mã gói từ `ma_luot` (lượt phục hồi / lượt
        bỏ dở cùng mã lượt không đè được lượt đã bàn giao).
    Chỉ đọc đĩa; tệp hỏng thì bỏ qua tệp đó."""
    ra: Dict[str, Dict[str, Any]] = {}
    that: set = set()
    try:
        from .doi_thu_kenh import ma_video as _ma  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        _ma = None  # type: ignore[assignment]

    def ma_cua(link: str) -> str:
        try:
            return str((_ma(link) if _ma else "") or "")
        except Exception:  # noqa: BLE001
            return ""

    for duong in sorted(glob.glob(os.path.join(_kenh_mod.duong_kenh(goc, kenh), "tu-chay", "*.json"))):
        du = _doc_json(duong)
        cac_luot = (du.get("runs") or []) if isinstance(du, dict) else []
        ngay = os.path.splitext(os.path.basename(duong))[0]
        for run in cac_luot:
            if not isinstance(run, dict):
                continue
            ng = run.get("nguon") or {}
            bg = run.get("ban_giao") or {}
            if not isinstance(ng, dict) or not isinstance(bg, dict):
                continue
            ma_goi = str(bg.get("ma_goi") or "").strip()
            co_that = bool(ma_goi)
            if not ma_goi and run.get("ma_luot"):
                ma_goi = "{0}-{1}".format(kenh, run.get("ma_luot"))
            link = str(ng.get("link") or "").strip()
            if not (ma_goi and link) or (not co_that and ma_goi in that):
                continue
            if co_that:
                that.add(ma_goi)
            ra[ma_goi] = {"link": link, "ma": str(ng.get("ma") or ma_cua(link)),
                          "tieu_de": str(ng.get("tieu_de") or ""),
                          "cong_thuc": str(ng.get("cong_thuc") or ng.get("nguon") or ""),
                          "tham_do": bool(ng.get("tham_do")), "nguon": str(ng.get("nguon") or ""),
                          "ngay": ngay, "bo": bool(run.get("bo"))}
    for duong in glob.glob(os.path.join(goc, "PROJECTS", "AUTO", kenh, "*", "trang-thai.json")):
        du = _doc_json(duong)
        if not isinstance(du, dict):
            continue
        ma_goi = "{0}-{1}".format(kenh, os.path.basename(os.path.dirname(duong)))
        link = str((du.get("dau_vao") or {}).get("link") or "").strip()
        if link and ma_goi not in ra:
            ra[ma_goi] = {"link": link, "ma": ma_cua(link), "tieu_de": "", "cong_thuc": "",
                          "tham_do": False, "nguon": "", "ngay": "", "bo": False}
    return ra


def _gan_cong_thuc(ho_so: Dict[str, Any], nguon: Optional[Dict[str, Any]]) -> None:
    """Chép `cong_thuc`/`tham_do` của lượt vào hồ sơ — metadata phụ, thiếu thì để mặc định."""
    if isinstance(nguon, dict):
        ho_so["cong_thuc"] = str(nguon.get("cong_thuc") or "")
        ho_so["tham_do"] = bool(nguon.get("tham_do"))


def _xay_ho_so(goc: str, kenh: str, thu_muc_luot: str, ma_goi: str) -> Dict[str, Any]:
    """Xây hồ sơ ĐẦY ĐỦ từ một thư mục lượt AUTO còn sống trên đĩa — dùng
    chung cho `tao_ho_so` (lượt vừa bàn giao) và `bu_ho_so` (lượt cũ, thư mục
    còn nguyên vì chưa tới lượt `don_dep` xoá)."""
    ho_so = _khung_ho_so(kenh, ma_goi)
    ho_so["luot"] = os.path.basename(thu_muc_luot.rstrip("/\\"))

    tieu_de, chu_bia = _doc_tieu_de_va_bia(thu_muc_luot)
    ho_so["tieu_de"] = tieu_de
    ho_so["chu_bia"] = chu_bia
    ho_so["tieu_de_cham"] = _doc_json(os.path.join(thu_muc_luot, "1-tieu-de-cham.json"))
    ho_so["kich_ban"] = _doc_cham_diem(os.path.join(thu_muc_luot, "1-cham-diem.txt"))
    hook_nhan = _doc_json(os.path.join(thu_muc_luot, "1-tu-hoc-hook.json"))  # tự học đợt 2
    if isinstance(hook_nhan, dict):
        ho_so["kich_ban"]["hook_nhan"] = hook_nhan
    ho_so["phan"] = _doc_phan(thu_muc_luot)
    ho_so["nhac"] = _doc_json(os.path.join(thu_muc_luot, "8-nhac.json"))
    tu_anh = _doc_json(os.path.join(thu_muc_luot, "6-clip", "tu-anh.json"))
    if isinstance(tu_anh, dict) and tu_anh.get("canh"):
        ho_so["clip_tu_anh"] = "{0}/{1}".format(len(tu_anh["canh"]), tu_anh.get("tong") or "?")

    try:
        k = _kenh_mod.doc_kenh(goc, kenh)
        ho_so["giay_nghi_phan"] = k.giay_nghi_phan
        ho_so["chuyen_phan"] = k.chuyen_phan
    except Exception:  # noqa: BLE001 — kênh đọc hỏng thì bỏ trống, không chặn hồ sơ
        pass

    # Ảnh bìa ĐANG DÙNG — đúng luật `ban_giao_dang._tim_thumb` (CHON- nếu có,
    # không thì tấm đầu): đây là ảnh THẬT SẼ lên video, không phải suy đoán.
    duong_anh = ban_giao_dang._tim_thumb(thu_muc_luot)  # noqa: SLF001
    if duong_anh:
        ten_anh = os.path.basename(duong_anh)
        # Việc 4: `chon-bia.json` (giám khảo AI) biết CHÍNH XÁC ai chọn —
        # thiếu tệp đó (kênh tắt `chon_bia_ai`, hoặc CHON- do người tự bấm)
        # thì lùi về đoán thô cũ theo tiền tố tên tệp.
        tt_chon = _thong_tin_chon_bia(duong_anh)
        ho_so["thumbnail"] = {
            "tep": ten_anh, "kieu": tt_chon.get("kieu") or _version_desc_tu_ten_anh(ten_anh),
            "chon_boi": tt_chon["chon_boi"] or (
                "nguoi" if ten_anh.upper().startswith("CHON-") else "luat"),
            "diem_giam_khao": tt_chon["diem_giam_khao"], "ly_do": tt_chon["ly_do"],
            "khuon_thang_dung": tt_chon["khuon_thang_dung"],
        }
        if tt_chon.get("theo_khuon") is not None:
            ho_so["thumbnail"].update(nhom=tt_chon.get("nhom", ""), theo_khuon=bool(tt_chon["theo_khuon"]),
                                      tham_do=bool(tt_chon.get("tham_do")))
        ho_so["thumbnail"].update(_doc_duoc_bia(duong_anh))
        _sao_luu_anh_bia(goc, kenh, ma_goi, duong_anh)
        ho_so["bia_2"] = _sao_luu_bia_2(goc, kenh, ma_goi, duong_anh)

    duong_video = os.path.join(thu_muc_luot, ban_giao_dang.TEP_VIDEO)
    if os.path.isfile(duong_video):
        ho_so.update(_thong_tin_video(goc, duong_video))

    return ho_so


def _xay_ho_so_toi_gian(goc: str, kenh: str, ma_goi: str, hang: Dict[str, str]) -> Dict[str, Any]:
    """Bù hồ sơ khi thư mục lượt AUTO đã bị `don_dep` xoá — chỉ còn `DONE/` và
    dòng kế hoạch. Không có kịch bản/phần/nhạc để đọc (đã mất thật), chỉ còn
    tiêu đề + ảnh bìa đã đăng — ghi rõ nguồn để người đọc biết đây là bản THIẾU."""
    ho_so = _khung_ho_so(kenh, ma_goi)
    ho_so["tieu_de"] = hang.get("Tiêu đề", "")

    thu_muc_goi = os.path.join(goc, "DONE", kenh, ma_goi)
    duong_anh = ""
    if os.path.isdir(thu_muc_goi):
        try:
            for ten in sorted(os.listdir(thu_muc_goi)):
                if os.path.splitext(ten)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"):
                    duong_anh = os.path.join(thu_muc_goi, ten)
                    break
        except OSError:
            pass
    if duong_anh:
        ten_anh = os.path.basename(duong_anh)
        ho_so["thumbnail"] = {
            # 01/10/2026: bỏ `tt_chon.get("kieu")` — biến không tồn tại ở nhánh tối giản (NameError
            # làm `bu_ho_so` im lặng bỏ mọi gói đã dọn).
            "tep": ten_anh, "kieu": _version_desc_tu_ten_anh(ten_anh),
            "chon_boi": "nguoi" if ten_anh.upper().startswith("CHON-") else "khong_ro",
            "diem_giam_khao": None, "ly_do": "", "khuon_thang_dung": False,
        }
        _sao_luu_anh_bia(goc, kenh, ma_goi, duong_anh)
        duong_video = os.path.join(thu_muc_goi, ban_giao_dang.TEP_VIDEO)
        if os.path.isfile(duong_video):
            ho_so.update(_thong_tin_video(goc, duong_video))
    return ho_so


# ── API chính ────────────────────────────────────────────────────────────────


def tao_ho_so(goc: str, kenh: str, luot: str, ma_goi: str) -> str:
    """Tạo/ghi đè hồ sơ của một lượt — gọi CUỐI `ban_giao_dang.ban_giao`, khi
    thư mục lượt còn ĐẦY ĐỦ mọi tệp. Trả đường dẫn tệp hồ sơ vừa ghi.

    Nơi gọi (`ban_giao_dang.ban_giao`) tự bọc `try/except` riêng — hàm này cứ
    để lỗi nổi lên nếu có, để test/gọi tay khác thấy ngay sự cố thật.
    """
    from .auto import duong_luot  # noqa: PLC0415 — tránh vòng nhập với core.auto

    thu_muc_luot = duong_luot(goc, kenh, luot)
    ho_so = _xay_ho_so(goc, kenh, thu_muc_luot, ma_goi)
    try:  # công thức/thăm dò — metadata phụ, sổ lượt hỏng không được chặn hồ sơ
        _gan_cong_thuc(ho_so, nguon_cua_goi(goc, kenh).get(ma_goi))
    except Exception:  # noqa: BLE001
        pass
    ho_so["thi_nghiem"] = _thi_nghiem_dang_mo(goc, kenh)
    return _luu_ho_so(goc, kenh, ma_goi, ho_so)


def _thi_nghiem_dang_mo(goc: str, kenh: str) -> str:
    """Id các thí nghiệm giám đốc kênh đang mở (`giam-doc/thi-nghiem.json`), cách nhau dấu phẩy —
    video ra đời lúc này thuộc mẫu đo của chúng. Không có sổ / hỏng → ""."""
    try:
        from .giam_doc import so_thi_nghiem as _stn  # noqa: PLC0415

        return ",".join(str(t.get("id")) for t in _stn.dang_mo(_stn.doc(goc, kenh)) if t.get("id"))
    except Exception:  # noqa: BLE001
        return ""


#: Mỗi phía của phép đo trước/sau một lần sửa cần ít nhất ngần này hiển thị.
HIEN_THI_TOI_THIEU_DO_SUA = 500
_KHOA_MOC_SUA = ("impressions", "ctr", "views", "ctr_trang_chu", "hien_thi_trang_chu", "luc_chup", "moc_gio_that")


def ghi_sua(goc: str, kenh: str, ma_goi: str, *, loai: str, cu: Any, moi: Any, doi_boi: str = "giam_doc",
            thi_nghiem: str = "", ly_do: str = "", bay_gio: Optional[_dt.datetime] = None) -> Optional[Dict[str, Any]]:
    """Ghi MỘT lần sửa trên Studio (`loai`: "tieu_de" | "bia") vào `lich_su_sua[]` của hồ sơ.

    Chỉ hồ sơ ĐÃ có `video_id` (sửa video nào phải biết video nào). `moc_truoc` = bản chụp mới nhất lúc
    sửa (số CỘNG DỒN); `cap_nhat_chi_so` điền `do` (hiệu hai bản chụp, mỗi phía ≥ 500 hiển thị).
    `doi_boi="giam_doc"` để `bia_theo_khuon` không coi bìa giám đốc đổi là bìa tay. Trả mục vừa ghi
    hoặc None."""
    ho_so = doc_ho_so(goc, kenh, ma_goi)
    if not isinstance(ho_so, dict) or not ho_so.get("video_id"):
        return None
    sm = ho_so.get("so_lieu_moi_nhat") or {}
    muc = {"luc": (bay_gio or _dt.datetime.now()).replace(microsecond=0).isoformat(), "loai": str(loai),
           "cu": cu, "moi": moi, "doi_boi": str(doi_boi or ""), "thi_nghiem": str(thi_nghiem or ""),
           "ly_do": str(ly_do or ""), "moc_truoc": {k: sm.get(k) for k in _KHOA_MOC_SUA} if sm else None,
           "do": None}
    ho_so["lich_su_sua"] = list(ho_so.get("lich_su_sua") or []) + [muc]
    _luu_ho_so(goc, kenh, ma_goi, ho_so)
    return muc


def _so_hs(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def do_truoc_sau(muc: Dict[str, Any], sau: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Trước/sau một lần sửa từ HAI bản chụp cộng dồn: trước = số tới lúc sửa (`moc_truoc`), sau =
    hiệu (bản chụp mới nhất − `moc_truoc`). CTR sau = (bấm sau − bấm trước) / (hiển thị sau − trước).
    `du` = mỗi phía ≥ `HIEN_THI_TOI_THIEU_DO_SUA` hiển thị."""
    t = muc.get("moc_truoc") or {}
    ra: Dict[str, Any] = {"du": False, "truoc": None, "sau": None, "luc_chup_sau": (sau or {}).get("luc_chup")}
    it, ct = _so_hs(t.get("impressions")), _so_hs(t.get("ctr"))
    if it is None or ct is None:
        return ra
    ra["truoc"] = {"hien_thi": it, "ctr": round(ct, 2)}
    if not sau or str(sau.get("luc_chup") or "") <= str(t.get("luc_chup") or ""):
        return ra
    is_, cs = _so_hs(sau.get("impressions")), _so_hs(sau.get("ctr"))
    if is_ is None or cs is None or is_ <= it:
        return ra
    them = is_ - it
    ctr_sau = max(0.0, (is_ * cs - it * ct) / them)
    ra["sau"] = {"hien_thi": round(them), "ctr": round(ctr_sau, 2)}
    tb, cb = _so_hs(t.get("hien_thi_trang_chu")), _so_hs(t.get("ctr_trang_chu"))
    sb, csb = _so_hs(sau.get("hien_thi_trang_chu")), _so_hs(sau.get("ctr_trang_chu"))
    if None not in (tb, cb, sb, csb) and sb > tb:
        ra["truoc"]["ctr_trang_chu"] = round(cb, 2)
        ra["sau"]["ctr_trang_chu"] = round(max(0.0, (sb * csb - tb * cb) / (sb - tb)), 2)
    ra["du"] = it >= HIEN_THI_TOI_THIEU_DO_SUA and them >= HIEN_THI_TOI_THIEU_DO_SUA
    return ra


def _browse_cua_ban_chup(thu_muc: str) -> Tuple[Optional[float], Optional[float]]:
    """(hiển thị trang chủ, CTR trang chủ) — dòng "Browse features" của `traffic-type.csv` cạnh bản chụp
    (Studio xuất riêng, không bộ giải mã nào gộp vào `BanGhi`)."""
    if not thu_muc:
        return None, None
    try:
        from .chi_so_ytb.gom import doc_csv  # noqa: PLC0415

        for dong in doc_csv(os.path.join(thu_muc, "traffic-type.csv")):
            if dong and dong[0].strip() == "Browse features" and len(dong) > 2:
                return _so_hs(dong[1]), _so_hs(dong[2])
    except Exception:  # noqa: BLE001
        pass
    return None, None


def _pct_nguon(traffic: Any, khoa: str) -> Optional[float]:
    """% lượt xem từ nguồn `khoa` ("browse" | "related") — chuẩn hoá trên tổng các nguồn."""
    if not isinstance(traffic, dict):
        return None
    so_ = [float(v) for v in traffic.values() if isinstance(v, (int, float))]
    tong = sum(so_)
    if not tong:
        return None
    v = traffic.get(khoa)
    return round(100.0 * float(v) / tong, 1) if isinstance(v, (int, float)) else 0.0


def ghi_video_id(goc: str, kenh: str, ma_goi: str, video_id: str,
                 lich: str = "") -> bool:
    """Đặt `video_id` (và `lich`, nếu có) thẳng vào hồ sơ — gọi từ trạm
    (`core/chi_so_ytb/tram.py`, `/dang-xong`) ngay khi máy đăng DOM báo ĐÃ
    ĐĂNG kèm id (29/09/2026, mục 4.4 bản thiết kế). NỐI TRỰC TIẾP, không chờ
    `cap_nhat_chi_so` dò qua so khớp tiêu đề — so khớp có thể trật nếu chủ
    kênh sửa tiêu đề trên Studio, hoặc hai gói cùng tên.

    Hồ sơ chưa tồn tại (gói đăng trước khi tính năng hồ sơ hoá có, hoặc chưa
    kịp bù) thì tạo một khung tối giản rồi ghi — không được để mất video_id
    chỉ vì `tao_ho_so`/`bu_ho_so` chưa từng chạy qua gói này; lượt bù sau vẫn
    an toàn (không có `os.path.isfile` nào coi hồ sơ CHƯA CÓ trước khi ghi).
    Trả `True` nếu đã ghi được gì đó, `False` nếu `video_id` rỗng.
    """
    video_id = str(video_id or "").strip()
    if not video_id:
        return False
    ho_so = doc_ho_so(goc, kenh, ma_goi)
    if not isinstance(ho_so, dict):
        ho_so = _khung_ho_so(kenh, ma_goi)
    ho_so["video_id"] = video_id
    if lich:
        ho_so["lich_dang"] = str(lich)
    _luu_ho_so(goc, kenh, ma_goi, ho_so)
    return True


def _khung_co_so(gt: Any) -> bool:
    """Khung chỉ số có SỐ ĐO thật (hiển thị hoặc lượt xem) — không phải khung rỗng `can_chup_lai`."""
    return isinstance(gt, dict) and (gt.get("impressions") is not None or gt.get("views") is not None)


def moc_can_chup_lai(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None) -> List[Tuple[str, str]]:
    """`[(mã gói, khung)]` — khung đang đánh dấu `can_chup_lai` mà CỬA SỔ khung còn mở (tuổi video hôm nay chưa
    tới giờ cao của khung: 48h = tới 60h, 72h = tới 96h…). Tuổi hôm nay = `moc_gio_that` lúc chụp + thời gian
    đã trôi từ `luc_chup`. Cho bộ thu thập biết mốc nào còn kịp chụp lại; chỉ đọc đĩa."""
    bay_gio = bay_gio or _dt.datetime.now()
    cao = {ten: c for ten, _t, c in _KHUNG_MOC}
    thu_muc = duong_thu_muc_ho_so(goc, kenh)
    ra: List[Tuple[str, str]] = []
    try:
        ten_tep = sorted(t for t in os.listdir(thu_muc) if t.endswith(".json"))
    except OSError:
        return ra
    for ten in ten_tep:
        hs = _doc_json(os.path.join(thu_muc, ten))
        if not isinstance(hs, dict):
            continue
        for khung, gt in (hs.get("chi_so") or {}).items():
            if not (isinstance(gt, dict) and gt.get("can_chup_lai")) or khung not in cao:
                continue
            try:
                luc = _dt.datetime.strptime(str(gt.get("luc_chup")), "%Y-%m-%d %H:%M")
                gio_nay = float(gt.get("moc_gio_that")) + (bay_gio - luc).total_seconds() / 3600.0
            except (TypeError, ValueError):
                continue
            if gio_nay < cao[khung]:
                ra.append((ten[:-len(".json")], khung))
    return ra


def _chuan_hoa_tieu_de_noi(t: str) -> str:
    """Chuẩn hoá THÔ để nối tiêu đề hồ sơ (tool đặt) ↔ tiêu đề Studio thật —
    cùng phép chuẩn hoá (bỏ khoảng trắng/dấu câu, hạ thường) mà
    `chi_so_ytb.tim_luot_theo_tieu_de` đã dùng để nối lượt AUTO ↔ video đã
    đăng; kênh remake đăng ĐÚNG tiêu đề tool đặt nên so bằng nhau là đủ, không
    cần ngưỡng mờ (`difflib`) như `core.tu_nhan_da_dang` (nơi đó phải chịu
    chủ kênh SỬA tay tiêu đề lúc đăng — hồ sơ ở đây đăng qua máy, không sửa)."""
    return re.sub(r"[\s\W_]+", "", (t or "").lower())


def _ten_moc(moc_gio: Optional[float]) -> str:
    """Tên khung của một lần chụp, theo TUỔI THẬT tính bằng giờ.

    ═══ VÌ SAO CÓ NHÁNH RỚT (29/09/2026) ═══

    Bốn khung đặt tên tay ở trên (24h/48h/72h/7d) chỉ phủ 18–96h và 144–240h —
    NGOÀI bốn khung đó, kể cả khe hở 96–144h (ngày 4–6) và MỌI giờ sau 240h
    (10 ngày), bản cũ trả `""` và `cap_nhat_chi_so` BỎ LUÔN bản chụp
    (`if not ten_moc: continue`). Tiện ích vẫn chụp được — dữ liệu nằm nguyên
    trên đĩa ở `CHANNEL/<k>/chi-so/<id>/<moc>h/tong-quan.json` — chỉ là hồ sơ
    video (thứ vòng học/`doc_bang_hieu_suat_tieu_de` đọc) không bao giờ thấy
    nó. Case thật: `TL1-T7-0001` (`v425582e4bd`) kẹt ở khung "7d" từ 25/09 dù
    hôm sau tiện ích đã chụp thêm; tới 29/09 vẫn báo "số liệu cũ" — vì đâu có
    khung nào để ghi vào.

    Từ nay: giờ nào KHÔNG rơi vào bốn khung tay ở trên, nhưng còn trong 30
    ngày (`_GIO_TRAN_NGAY_GAN_DAY`), nhận một khung riêng theo NGÀY tuổi
    (`ngay0`…`ngay29`) — mỗi ngày một khoá, bản chụp muộn nhất trong ngày đó
    thắng (logic gộp ở `cap_nhat_chi_so` không đổi). `so_lieu_moi_nhat` tính
    bằng `max(..., key=moc_gio_that)` trên toàn bộ `chi_so`, nên tự nhặt khoá
    mới nhất — thêm tên khoá không quen không phá chỗ nào khác (không nơi nào
    trong kho đọc `chi_so["24h"]`/`["7d"]` theo TÊN CỐ ĐỊNH ngoài chính tệp
    này, đã rà `core/` trước khi đổi).
    """
    if moc_gio is None:
        return ""
    for ten, thap, cao in _KHUNG_MOC:
        if thap <= moc_gio < cao:
            return ten
    if 0.0 <= moc_gio < _GIO_TRAN_NGAY_GAN_DAY:
        return "ngay{0}".format(int(moc_gio // 24))
    return ""


def cap_nhat_chi_so(goc: str, kenh: str, *, bay_gio: Optional[_dt.datetime] = None,
                    on_log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Nối `video_id` (qua tiêu đề) và điền số liệu Studio (24h/48h/72h/7d, rồi
    theo NGÀY — `ngayN` — cho mọi giờ khác trong 30 ngày, xem `_ten_moc`) vào
    MỌI hồ sơ của `kenh`. Gọi lại nhiều lần AN TOÀN — chỉ ghi lại hồ sơ nào
    thật sự có gì mới (idempotent), số liệu chỉ tăng dần đúng như Studio.

    Trả `{"noi_video_id": n, "cap_nhat_moc": n, "so_lieu_cu": [mã gói…]}` —
    KHÔNG ném lỗi: đọc số liệu Studio hỏng (kênh mới, chưa quét lần nào) thì
    trả về số 0, không phải lỗi.
    """
    bay_gio = bay_gio or _dt.datetime.now()

    def log(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    rong = {"noi_video_id": 0, "cap_nhat_moc": 0, "so_lieu_cu": []}  # type: Dict[str, Any]

    thu_muc = duong_thu_muc_ho_so(goc, kenh)
    try:
        ten_tep = sorted(t for t in os.listdir(thu_muc) if t.endswith(".json"))
    except OSError:
        return rong

    try:
        ban_ghi = _chi_so.doc_kenh(kenh, goc=_kenh_mod.duong_kenh(goc))
    except Exception as loi:  # noqa: BLE001 — kênh chưa quét Studio lần nào là bình thường
        log("  0) [vòng học] chưa đọc được số liệu Studio của {0}: {1} — bỏ qua."
           .format(kenh, str(loi)[:200]))
        return rong

    theo_video: Dict[str, List[Any]] = {}
    ten_video: Dict[str, str] = {}
    for b in ban_ghi:
        if not b.video_id:
            continue
        theo_video.setdefault(b.video_id, []).append(b)
        if b.tieu_de:
            # `ban_ghi` đã sắp tăng dần theo (video_id, luc_chup) — bản CUỐI
            # (mới nhất) thắng, phòng khi chủ kênh sửa tiêu đề Studio sau đăng.
            ten_video[b.video_id] = b.tieu_de

    noi_video_id = 0
    cap_nhat_moc = 0
    so_lieu_cu: List[str] = []

    for ten in ten_tep:
        ma_goi = ten[:-len(".json")]
        duong = os.path.join(thu_muc, ten)
        ho_so = _doc_json(duong)
        if not isinstance(ho_so, dict):
            continue
        thay = False

        video_id = ho_so.get("video_id") or None
        if not video_id:
            muon = _chuan_hoa_tieu_de_noi(ho_so.get("tieu_de") or "")
            if muon:
                khop = [vid for vid, t in ten_video.items()
                       if _chuan_hoa_tieu_de_noi(t) == muon]
                if len(khop) == 1:
                    video_id = khop[0]
                    ho_so["video_id"] = video_id
                    thay = True
                    noi_video_id += 1
                    log("  0) [vòng học] {0}: nối được video_id {1} qua tiêu đề."
                       .format(ma_goi, video_id))

        if video_id and video_id in theo_video:
            chi_so = dict(ho_so.get("chi_so") or {})
            # 01/10/2026 — SỬA NHÃN MỐC SAI: mốc nay tính theo tuổi THẬT (`gom.dang_that_cua_video`);
            # khung cũ mang CÙNG lúc chụp mà nay thuộc khung khác (một video TL3: bản 38h từng nằm ở "24h")
            # thì bỏ — bản đó chỉ còn ở đúng khung.
            khung_dung = {b.luc_chup: _ten_moc(b.moc_gio) for b in theo_video[video_id] if b.luc_chup}
            for k in [k for k, gt in chi_so.items() if isinstance(gt, dict)
                      and khung_dung.get(gt.get("luc_chup")) not in (None, "", k)]:
                chi_so.pop(k, None)
                thay = True
            for k, gt in list(chi_so.items()):  # khung rỗng từ bản cũ (đã bị đè): đánh dấu để chụp lại
                if isinstance(gt, dict) and not _khung_co_so(gt) and not gt.get("can_chup_lai"):
                    chi_so[k] = dict(gt, can_chup_lai=True)
                    thay = True
            for b in theo_video[video_id]:
                ten_moc = _ten_moc(b.moc_gio)
                if not ten_moc:
                    continue
                cu = chi_so.get(ten_moc)
                if b.impressions is None and b.views is None:
                    # Bản chụp RỖNG (Studio chưa trả số / bộ giải mã chưa đọc được) KHÔNG được đè khung — bản cũ
                    # đè nên khung 48h thành toàn None, bộ thu thập tưởng mốc đã xong. Khung đã có số thì giữ;
                    # chưa có thì đánh dấu `can_chup_lai` để chụp lại khi cửa sổ khung còn mở.
                    if _khung_co_so(cu) or (isinstance(cu, dict) and cu.get("can_chup_lai")
                                            and cu.get("luc_chup") == b.luc_chup):
                        continue
                    chi_so[ten_moc] = {"impressions": None, "ctr": None, "views": None, "luc_chup": b.luc_chup,
                                       "moc_gio_that": b.moc_gio, "can_chup_lai": True}
                    thay = True
                    continue
                if isinstance(cu, dict) and cu.get("luc_chup") == b.luc_chup and "pct_browse" in cu:
                    continue  # số liệu y hệt lần trước — không phải "cập nhật mới"
                # 01/10/2026 (giám đốc kênh): thêm CTR trang chủ (dòng Browse của traffic-type.csv),
                # % view từ trang chủ / đề xuất, sub, giờ xem. Mốc cũ thiếu các khoá này được bù MỘT lần.
                hien_thi_tc, ctr_tc = _browse_cua_ban_chup(getattr(b, "thu_muc", "") or "")
                tr = getattr(b, "traffic", None) or {}
                chi_so[ten_moc] = {
                    "impressions": b.impressions, "ctr": b.ctr, "views": b.views,
                    "avd_pct": b.avd_pct, "avd_giay": b.avd_giay,
                    "luc_chup": b.luc_chup, "moc_gio_that": b.moc_gio,
                    "ctr_trang_chu": ctr_tc, "hien_thi_trang_chu": hien_thi_tc,
                    "pct_browse": _pct_nguon(tr, "browse"), "pct_de_xuat": _pct_nguon(tr, "related"),
                    "subs": getattr(b, "subs", None), "gio_xem": getattr(b, "watch_hours", None),
                }
                thay = True
                cap_nhat_moc += 1
            if chi_so:
                ho_so["chi_so"] = chi_so
                co_so = {k: gt for k, gt in chi_so.items() if _khung_co_so(gt)} or chi_so
                ten_moc_moi, gt_moi = max(
                    co_so.items(),
                    key=lambda kv: (kv[1].get("moc_gio_that")
                                   if isinstance(kv[1], dict) and kv[1].get("moc_gio_that") is not None
                                   else -1))
                ho_so["so_lieu_moi_nhat"] = dict(gt_moi, moc=ten_moc_moi)
                # đo trước/sau mọi lần sửa trên Studio (giám đốc kênh) bằng bản chụp mới nhất
                ls = [dict(m) for m in ho_so.get("lich_su_sua") or [] if isinstance(m, dict)]
                for m in ls:
                    do = do_truoc_sau(m, gt_moi)
                    if do != m.get("do"):
                        m["do"] = do
                        thay = True
                if ls:
                    ho_so["lich_su_sua"] = ls
                luc_chup = gt_moi.get("luc_chup")
                if luc_chup:
                    try:
                        luc = _dt.datetime.strptime(luc_chup, "%Y-%m-%d %H:%M")
                        gio_qua = (bay_gio - luc).total_seconds() / 3600.0
                    except ValueError:
                        gio_qua = 0.0
                    if gio_qua > NGUONG_GIO_SO_LIEU_CU:
                        so_lieu_cu.append(ma_goi)
                        # Log gọn (29/09/2026): chỉ in khi mốc cũ ĐỔI — trước đây
                        # mỗi giờ mỗi kênh in lại y một câu cho cùng một mốc.
                        if ho_so.get("_da_bao_so_lieu_cu") != luc_chup:
                            ho_so["_da_bao_so_lieu_cu"] = luc_chup
                            thay = True
                            log("  0) [vòng học] {0}: số liệu Studio cũ từ ngày {1} "
                               "({2:.0f} giờ trước) — vẫn dùng, không chặn."
                               .format(ma_goi, luc_chup[:10], gio_qua))

        if thay:
            _ghi_json(duong, ho_so)

    return {"noi_video_id": noi_video_id, "cap_nhat_moc": cap_nhat_moc, "so_lieu_cu": so_lieu_cu}


def doc_bang_hieu_suat_tieu_de(goc: str, kenh: str) -> List[Dict[str, Any]]:
    """Việc 5 (29/09/2026): MỌI hồ sơ video của `kenh` CÓ số liệu Studio, trả về
    `[{tieu_de, chu_bia, ctr, impressions, moc, ngay_so_lieu, tao_luc}]`, mới
    tạo TRƯỚC (sắp theo `tao_luc` GIẢM DẦN) — `core.auto_khau` (khuôn chấm N
    BẢN TIÊU ĐỀ) tự lọc 8 CTR cao/3 CTR thấp và tiêu đề 30 ngày gần đây từ danh
    sách thô này, không lọc sẵn ở đây để nơi gọi chủ động chọn ngưỡng của riêng
    mình (chấm tiêu đề, hay việc khác sau này).

    Chỉ lấy hồ sơ đã có `so_lieu_moi_nhat` (điền bởi `cap_nhat_chi_so`, ở trên)
    — hồ sơ chưa có số liệu (video quá mới, chưa quét Studio lần nào) bị bỏ
    qua, không có gì để so CTR. Không gọi mạng, không ném lỗi: thư mục hồ sơ
    thiếu/hỏng trả về `[]`.
    """
    thu_muc = duong_thu_muc_ho_so(goc, kenh)
    try:
        ten_tep = sorted(t for t in os.listdir(thu_muc) if t.endswith(".json"))
    except OSError:
        return []
    ra: List[Dict[str, Any]] = []
    for ten in ten_tep:
        ho_so = _doc_json(os.path.join(thu_muc, ten))
        if not isinstance(ho_so, dict):
            continue
        moi_nhat = ho_so.get("so_lieu_moi_nhat")
        tieu_de = str(ho_so.get("tieu_de") or "").strip()
        if not (isinstance(moi_nhat, dict) and tieu_de):
            continue
        ctr = moi_nhat.get("ctr")
        if ctr is None:
            continue
        ra.append({
            "tieu_de": tieu_de, "chu_bia": str(ho_so.get("chu_bia") or ""),
            "ctr": float(ctr), "impressions": moi_nhat.get("impressions"),
            "moc": str(moi_nhat.get("moc") or ""),
            "ngay_so_lieu": str(moi_nhat.get("luc_chup") or "")[:10],
            "tao_luc": str(ho_so.get("tao_luc") or ""),
        })
    ra.sort(key=lambda r: r["tao_luc"], reverse=True)
    return ra


def bu_ho_so(goc: str, kenh: str, *, on_log: Optional[Callable[[str], None]] = None) -> List[str]:
    """Bù hồ sơ cho các gói ĐÃ BÀN GIAO/ĐÃ ĐĂNG từ TRƯỚC khi tệp này tồn tại —
    idempotent (bỏ qua mã gói đã có hồ sơ). Trả danh sách mã gói VỪA được tạo.

    Chỉ bù gói có dấu vết đã bàn giao thật (cột "Sẵn sàng" hoặc "Trạng thái
    đăng" khác rỗng trong `ke-hoach.csv`) — dòng kế hoạch còn nháp/chưa qua QA
    thì chưa có gì để bù.
    """
    da_tao: List[str] = []

    def log(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    try:
        cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    except Exception as loi:  # noqa: BLE001 — kế hoạch hỏng/chưa có, không phải lỗi chặn
        log("  0) [vòng học] không đọc được kế hoạch của {0}: {1} — bỏ qua bù hồ sơ."
           .format(kenh, str(loi)[:200]))
        return da_tao
    if "Mã gói" not in cot:
        return da_tao
    o_ma = cot.index("Mã gói")
    o_san = cot.index("Sẵn sàng") if "Sẵn sàng" in cot else -1
    o_tt = cot.index("Trạng thái đăng") if "Trạng thái đăng" in cot else -1
    so_luot: Optional[Dict[str, Dict[str, Any]]] = None  # nguon_cua_goi — đọc lười, một lần

    for dong in hang:
        ma_goi = dong[o_ma].strip() if o_ma < len(dong) else ""
        if not ma_goi:
            continue
        san_sang = dong[o_san].strip() if 0 <= o_san < len(dong) else ""
        trang_thai = dong[o_tt].strip() if 0 <= o_tt < len(dong) else ""
        if not san_sang and not trang_thai:
            continue  # chưa từng bàn giao — chưa có gì để bù
        if os.path.isfile(duong_tep_ho_so(goc, kenh, ma_goi)):
            continue  # đã có hồ sơ rồi

        tien_to = kenh + "-"
        luot = ma_goi[len(tien_to):] if ma_goi.startswith(tien_to) else ""
        thu_muc_luot = ""
        if luot:
            try:
                from .auto import duong_luot  # noqa: PLC0415
                thu_muc_luot = duong_luot(goc, kenh, luot)
            except Exception:  # noqa: BLE001
                thu_muc_luot = ""

        try:
            if thu_muc_luot and os.path.isdir(thu_muc_luot):
                ho_so = _xay_ho_so(goc, kenh, thu_muc_luot, ma_goi)
                ho_so["nguon_bu"] = "PROJECTS/AUTO (lượt còn nguyên trên đĩa)"
            else:
                ho_so = _xay_ho_so_toi_gian(goc, kenh, ma_goi, dict(zip(cot, dong)))
                ho_so["nguon_bu"] = "DONE + ke-hoach.csv (lượt AUTO đã bị dọn dẹp)"
            try:
                if so_luot is None:
                    so_luot = nguon_cua_goi(goc, kenh)
                _gan_cong_thuc(ho_so, so_luot.get(ma_goi))
            except Exception:  # noqa: BLE001 — metadata phụ
                so_luot = {}
            _luu_ho_so(goc, kenh, ma_goi, ho_so)
            da_tao.append(ma_goi)
        except Exception as loi:  # noqa: BLE001 — một gói hỏng không được chặn cả lượt bù
            log("  0) [vòng học] bù hồ sơ {0} hỏng: {1} — bỏ qua, các gói khác vẫn chạy."
               .format(ma_goi, str(loi)[:200]))

    return da_tao
