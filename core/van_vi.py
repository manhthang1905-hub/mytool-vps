"""core/van_vi.py — Van VÍ ShopAPI: đừng mở lượt sản xuất mới khi ví sắp cạn.

Việc V8 (`workspace/KE-HOACH-GIA-CO-1-NAM.md`, mục 3.3 lộ trình V3). Chủ dự án
KHÔNG dùng bot Telegram, tự nạp tiền — nên tool phải TỰ DỪNG ÊM khi ví cạn, nói
rõ bằng câu người thường, rồi TỰ CHẠY LẠI khi thấy ví đã có tiền (không ai bấm).

═══ LUẬT ═══

* Chi phí một video = ước tính lớn nhất trong các kênh `tu_chay: true`
  (`core.tu_chay._uoc_chi_phi_micro`, chính là số tiền ShopAPI "giữ" trước khi
  làm — thiếu số này là gặp 402).
* Lượt MỚI chỉ được mở khi `số dư >= ước 1 video x HE_SO_AN_TOAN (1,5)`.
* Lượt ĐANG DỞ vẫn được làm nốt khi `số dư >= ước 1 video` (không biết chính
  xác các khâu còn lại tốn bao nhiêu, lấy trần là cả video — thà dè dặt).
* Số dư đọc bằng `GET /v1/balance` (`core.api.fetch_balance`), MIỄN PHÍ, có nhớ
  đệm `workspace/vi/so-du.json` (TTL ngắn) để nhịp điều phối 10 phút và gác
  tổng 15 phút không gọi dồn. Không đọc được số dư (mất mạng, khoá lỗi) thì
  KHÔNG chặn (đừng dừng cả máy vì một lỗi đọc) — chỉ ghi lại là "không rõ".
* Hết tiền giữa chừng (402 / thiếu tiền): :func:`ghi_het_tien` nhớ số dư lúc
  đó; van CHẶN cho tới khi số dư thấy tăng lên (đã nạp) — rồi tự mở lại.
* Cảnh báo sớm: còn đủ dưới `NGUONG_SOM_NGAY` (2) ngày sản xuất theo nhịp chi
  tiêu 7 ngày gần nhất (`workspace/chi-phi/<ngày>.json`).

Trạng thái ghi ra `workspace/vi/trang-thai.json` (giao diện + gác tổng đọc).
Module KHÔNG gửi tin nào — việc báo (giao diện / loi-chay-max.md / bản tin gác
tổng, lặp mỗi 4 giờ) do `core.chot_an_toan` + `core.gac_tong` lo.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

__all__ = [
    "HE_SO_AN_TOAN", "NGUONG_SOM_NGAY", "TTL_SO_DU_GIAY",
    "doc_so_du", "uoc_mot_video_vnd", "nhip_chi_vnd_ngay", "danh_gia",
    "cho_phep_mo_luot", "ghi_het_tien", "doc_trang_thai", "duong_trang_thai",
]

HE_SO_AN_TOAN = 1.5
NGUONG_SOM_NGAY = 2.0
#: Số dư nhớ đệm bao lâu thì hỏi lại (giây). Khi đang bị chặn hỏi thường hơn để
#: TỰ CHẠY LẠI nhanh sau khi nạp tiền.
TTL_SO_DU_GIAY = 600.0
TTL_KHI_CHAN_GIAY = 240.0
#: Chưa thấy số dư nhích lên thêm ngần này (đồng) thì chưa coi là "đã nạp".
BIEN_DA_NAP_VND = 1000.0
SO_NGAY_NHIP = 7


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def _thu_muc(goc: str) -> str:
    return os.path.join(goc, "workspace", "vi")


def duong_trang_thai(goc: str) -> str:
    return os.path.join(_thu_muc(goc), "trang-thai.json")


def _duong_so_du(goc: str) -> str:
    return os.path.join(_thu_muc(goc), "so-du.json")


def doc_trang_thai(goc: str) -> Dict[str, Any]:
    du = _doc_json(duong_trang_thai(goc))
    return du if isinstance(du, dict) else {}


def _vnd_chu(n: float) -> str:
    return "{0:,.0f}₫".format(n).replace(",", ".")


# ── số dư ───────────────────────────────────────────────────────────────────


def _micro_tu_phan_hoi(phan_hoi: Any) -> Optional[int]:
    """`{"wallet": "<µVND>"}` → µVND; KHÔNG đoán khi phản hồi lạ (trả None)."""
    if not isinstance(phan_hoi, Mapping) or "wallet" not in phan_hoi:
        return None
    try:
        return int(str(phan_hoi.get("wallet")))
    except (TypeError, ValueError):
        return None


def _tao_client(goc: str) -> Any:
    from .api import build_client  # noqa: PLC0415
    from .config import CONFIG_FILENAME, load_config  # noqa: PLC0415

    cau_hinh = load_config(os.path.join(goc, CONFIG_FILENAME))
    if cau_hinh.problem:
        return None
    return build_client(cau_hinh)


def doc_so_du(goc: str, client: Any = None, *, ttl: float = TTL_SO_DU_GIAY,
              bay_gio: Optional[float] = None,
              lay: Optional[Callable[[Any], Any]] = None) -> Optional[float]:
    """Số dư ví (VND) hoặc None nếu không đọc được. Dùng đệm còn tươi; hết hạn
    thì gọi `GET /v1/balance` (miễn phí). `lay(client)` là seam cho test."""
    bay_gio = bay_gio if bay_gio is not None else time.time()
    dem = _doc_json(_duong_so_du(goc))
    if isinstance(dem, dict):
        try:
            if 0 <= bay_gio - float(dem.get("luc")) < ttl and dem.get("vnd") is not None:
                return float(dem["vnd"])
        except (TypeError, ValueError):
            pass
    try:
        if client is None and lay is None:
            client = _tao_client(goc)
        if client is None and lay is None:
            return None
        if lay is not None:
            phan_hoi = lay(client)
        else:
            from .api import fetch_balance  # noqa: PLC0415

            phan_hoi = fetch_balance(client)
    except Exception:  # noqa: BLE001 — mất mạng/khoá lỗi: không chặn máy vì lỗi đọc
        return None
    micro = _micro_tu_phan_hoi(phan_hoi)
    if micro is None:
        return None
    vnd = micro / 1_000_000.0
    _ghi_json(_duong_so_du(goc), {"luc": bay_gio, "vnd": vnd})
    return vnd


# ── ước tính ────────────────────────────────────────────────────────────────


def uoc_mot_video_vnd(goc: str) -> Optional[float]:
    """Ước 1 video (VND) = lớn nhất trong các kênh tự chạy; None nếu không tính được."""
    try:
        from . import tu_chay  # noqa: PLC0415
        from .kenh import doc_kenh  # noqa: PLC0415
        from .money import micro_to_vnd  # noqa: PLC0415
        from .pricing import DEFAULT_PRICES  # noqa: PLC0415

        cao = 0.0
        for ma in tu_chay.kenh_tu_chay(goc):
            try:
                micro = tu_chay._uoc_chi_phi_micro(doc_kenh(goc, ma), DEFAULT_PRICES)  # noqa: SLF001
                cao = max(cao, float(micro_to_vnd(micro)))
            except Exception:  # noqa: BLE001
                continue
        return cao or None
    except Exception:  # noqa: BLE001
        return None


def nhip_chi_vnd_ngay(goc: str, bay_gio: Optional[_dt.datetime] = None) -> Optional[float]:
    """Chi tiêu TB/ngày (VND) trong 7 ngày gần nhất có sổ `workspace/chi-phi/`."""
    bay_gio = bay_gio or _dt.datetime.now()
    tong, so = 0.0, 0
    for i in range(1, SO_NGAY_NHIP + 1):
        ngay = (bay_gio - _dt.timedelta(days=i)).strftime("%Y-%m-%d")
        du = _doc_json(os.path.join(goc, "workspace", "chi-phi", ngay + ".json"))
        if isinstance(du, dict):
            try:
                v = float(du.get("tong_micro") or 0) / 1_000_000.0
            except (TypeError, ValueError):
                continue
            if v > 0:
                tong += v
                so += 1
    return (tong / so) if so else None


def danh_gia(so_du_vnd: Optional[float], uoc_video_vnd: Optional[float],
             chi_ngay_vnd: Optional[float]) -> Dict[str, Any]:
    """Hàm THUẦN. `muc`: "khong_ro" | "ok" | "som" (còn <2 ngày) | "het" (không
    đủ mở lượt mới). Kèm câu người thường."""
    ra: Dict[str, Any] = {"so_du_vnd": so_du_vnd, "uoc_video_vnd": uoc_video_vnd,
                          "chi_ngay_vnd": chi_ngay_vnd, "du_video": None,
                          "ngay_con": None, "muc": "khong_ro", "cau": "", "viec_can_lam": ""}
    if so_du_vnd is None or not uoc_video_vnd:
        return ra
    du_video = int(so_du_vnd // uoc_video_vnd)
    ngay_con = (so_du_vnd / chi_ngay_vnd) if chi_ngay_vnd else None
    ra["du_video"] = du_video
    ra["ngay_con"] = ngay_con
    ra["can_toi_thieu_vnd"] = uoc_video_vnd * HE_SO_AN_TOAN
    goi_y = ("Nạp thêm tiền vào ví ShopAPI. Máy sẽ TỰ chạy lại khi thấy ví đủ "
             "tiền, bạn không cần bấm gì thêm.")
    if so_du_vnd < uoc_video_vnd * HE_SO_AN_TOAN:
        ra["muc"] = "het"
        ra["cau"] = ("Ví sắp hết: còn {0}, đủ khoảng {1} video — cần nạp. Máy đã "
                     "ngừng mở video mới (video đang làm dở vẫn được làm nốt nếu đủ "
                     "tiền).").format(_vnd_chu(so_du_vnd), du_video)
        ra["viec_can_lam"] = goi_y
    elif ngay_con is not None and ngay_con < NGUONG_SOM_NGAY:
        ra["muc"] = "som"
        ra["cau"] = ("Ví sắp hết: còn {0}, đủ khoảng {1} video (chừng {2:.1f} ngày sản "
                     "xuất theo nhịp hiện tại) — cần nạp sớm.").format(
                         _vnd_chu(so_du_vnd), du_video, ngay_con)
        ra["viec_can_lam"] = goi_y
    else:
        ra["muc"] = "ok"
        ra["cau"] = "Ví còn {0}, đủ khoảng {1} video.".format(_vnd_chu(so_du_vnd), du_video)
    return ra


# ── 402 giữa chừng ──────────────────────────────────────────────────────────


def ghi_het_tien(goc: str, chi_tiet: str = "", *, so_du_vnd: Optional[float] = None,
                 bay_gio: Optional[float] = None) -> None:
    """Gọi khi một lượt gặp 402/thiếu tiền. Nhớ số dư lúc đó; van sẽ chặn tới khi
    thấy số dư TĂNG (đã nạp) rồi tự mở lại."""
    bay_gio = bay_gio if bay_gio is not None else time.time()
    if so_du_vnd is None:
        so_du_vnd = doc_so_du(goc, ttl=0.0, bay_gio=bay_gio)
    tt = doc_trang_thai(goc)
    tt["het_tien"] = {"luc": bay_gio, "so_du_vnd": so_du_vnd,
                      "chi_tiet": str(chi_tiet)[:300]}
    _ghi_json(duong_trang_thai(goc), tt)


def _da_nap_lai(tt: Dict[str, Any], so_du_vnd: float) -> bool:
    ht = tt.get("het_tien")
    if not isinstance(ht, dict):
        return True
    truoc = ht.get("so_du_vnd")
    if truoc is None:
        return True  # không biết số dư lúc lỗi: dựa vào ngưỡng chung
    try:
        return so_du_vnd > float(truoc) + BIEN_DA_NAP_VND
    except (TypeError, ValueError):
        return True


# ── CỬA CHÍNH ───────────────────────────────────────────────────────────────


def cho_phep_mo_luot(goc: str, client: Any = None, *, dang_do: bool = False,
                     uoc_video_vnd: Optional[float] = None,
                     bay_gio: Optional[float] = None,
                     lay: Optional[Callable[[Any], Any]] = None
                     ) -> Tuple[bool, str, Dict[str, Any]]:
    """`(được, lý_do, đánh_giá)`. `dang_do=True`: lượt đã chạy dở, chỉ cần đủ 1 video.
    Không đọc được số dư → (True, "", ...) (không chặn). Ghi `trang-thai.json`."""
    bay_gio = bay_gio if bay_gio is not None else time.time()
    tt = doc_trang_thai(goc)
    dang_chan = bool((tt.get("chan") or False))
    so_du = doc_so_du(goc, client, bay_gio=bay_gio, lay=lay,
                      ttl=TTL_KHI_CHAN_GIAY if dang_chan else TTL_SO_DU_GIAY)
    uoc = uoc_video_vnd if uoc_video_vnd is not None else uoc_mot_video_vnd(goc)
    dg = danh_gia(so_du, uoc, nhip_chi_vnd_ngay(goc, _dt.datetime.fromtimestamp(bay_gio)))

    def _xet(he_so: float, viec: str) -> Tuple[bool, str]:
        if dg["muc"] == "khong_ro":
            return True, ""
        can = uoc * he_so
        if so_du < can:
            return False, ("ví còn {0}, chưa đủ {1} để {2} — cần nạp tiền; máy tự chạy lại "
                           "khi ví đủ.").format(_vnd_chu(so_du), _vnd_chu(can), viec)
        if not _da_nap_lai(tt, so_du):
            return False, ("lần trước hết tiền giữa chừng (ví còn {0} lúc đó), chưa thấy ví "
                           "tăng — chờ nạp tiền.").format(
                               _vnd_chu(float(tt["het_tien"].get("so_du_vnd") or 0)))
        return True, ""

    duoc_moi, ly_do_moi = _xet(HE_SO_AN_TOAN, "mở video mới")
    duoc_do, ly_do_do = _xet(1.0, "làm nốt video đang dở")
    moi: Dict[str, Any] = {k: v for k, v in tt.items() if k != "het_tien"}
    if "het_tien" in tt and (so_du is None or not _da_nap_lai(tt, so_du)):
        moi["het_tien"] = tt["het_tien"]  # chưa thấy nạp: giữ dấu
    moi.update({"luc": bay_gio, "chan": not duoc_moi, "ly_do_chan": ly_do_moi,
                "chan_luot_do": not duoc_do, "danh_gia": dg})
    if duoc_moi and dang_chan:
        moi["mo_lai_luc"] = bay_gio
    _ghi_json(duong_trang_thai(goc), moi)
    return (duoc_do, ly_do_do, dg) if dang_do else (duoc_moi, ly_do_moi, dg)
