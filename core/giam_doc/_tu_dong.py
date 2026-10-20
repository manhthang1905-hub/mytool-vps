"""Tự động hoá phần "Việc của bạn" của giám đốc kênh (04/10/2026 — chủ dự án: "mọi thứ auto 100%").

Người CHỈ làm việc máy không làm được (đăng nhập Chrome/Google, 2FA, nạp ShopAPI, bản quyền Windows, thuê VPS).

    phan_loai_viec(chu)                        "nguoi" | "cho_so" | "may"
    ghi_viec_may(goc, ma, viec, loai)          "may" → hàng đợi `nao/viec-tu-giam-doc.json` cho bộ não (việc nhận ra
                                               kiểu → việc máy CÓ KIỂU, bên dưới); "cho_so" → nhật ký giám đốc 1 lần.
                                               Trả True nếu là việc MỚI
    doc_viec_cho_nao(goc, bay_gio)             mục còn hạn của hàng đợi (`core.nao xem` in) — không gồm việc có kiểu
    quyen_kenh(goc, ma)                        kênh nên ở `goi_y` hay `tu_ap` theo `do-chinh-xac.json`
    tu_nang_ha_quyen(goc, …)                   hằng ngày: đủ ngưỡng → `tu_ap`; tụt → lùi `goi_y` (ghi kenh.yaml)

═══ VIỆC MÁY CÓ KIỂU (16/10/2026 — chủ: "mục đích cuối VPS này auto 100%") ═══

Việc Studio mà bộ chạy DOM làm được (bộ chạy viết ở đợt sau) nằm ở khoá `viec_may` của cùng tệp
`nao/viec-tu-giam-doc.json` — KHÔNG hết hạn 9 ngày như hàng chữ cho bộ não. Một mục:

    {"id": "m-<12 hex>", "loai": "studio_test_compare" | "studio_kiem_suc_khoe", "kenh": "<mã kênh>",
     "video_ids": [...],            # test_compare: ≥ 1 video CỦA kênh này; kiem_suc_khoe: []
     "trang_thai": "cho" | "dang" | "xong" | "loi" | "can_nguoi" | "bo",
     "nguon": "nao:n038" | "giam-doc:suc_khoe", "chu": "<câu gốc>", "tao_luc": iso, "cap_nhat": iso,
     "lan_thu": 0, "ket": {}}        # kiem_suc_khoe xong: ket = {"canh_bao": bool, "chi_tiet": "…"}

    kieu_viec_may(chu, kenh, ban_do)           câu việc → [{loai, kenh, video_ids}] (rỗng = không nhận ra kiểu)
    ghi_viec_may_kieu(goc, loai, kenh, …)      thêm (một mục mở cho mỗi loai+kênh+bộ video), trả True nếu mới/mở lại
    doc_viec_may_kieu(goc, loai, trang_thai)   bộ chạy đọc việc của mình (mặc định: còn mở)
    cap_nhat_viec_may_kieu(goc, id, **truong)  bộ chạy ghi kết quả; "can_nguoi" (đọc Studio THẤY cảnh báo/gậy) → bảng
                                               điều khiển hiện cho người
    dinh_tuyen_de_xuat_nao(goc)                gác tổng: đề xuất của bộ não mà máy làm được → việc máy có kiểu
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

TEP_HANG_DOI = os.path.join("nao", "viec-tu-giam-doc.json")
HAN_MUC_NGAY = 9              # > VIEC_CUA_BAN_CON_NGAY (8): hết hạn rồi báo cáo cũ cũng đã bỏ → không lặp lại
HAN_NHO_NGAY = 10
TOI_DA_MUC = 60

#: Câu CODE tự viết (không phải lời LLM) — chỉ người làm được: quyết định chiến lược lớn chờ chủ.
#: 16/10/2026: bỏ "Đổi tiêu đề video " (chủ duyệt máy tự đổi tiêu đề có rào — `cuu_ctr`) và câu cò sức khoẻ (máy đọc
#: Studio — việc `studio_kiem_suc_khoe`; chỉ báo người khi bộ đọc THẤY cảnh báo/gậy).
_NGUOI_TIEN_TO = ("Quyết định lớn chờ bạn duyệt:",)
#: Việc chỉ người làm được dù LLM viết tự do: đăng nhập, 2FA/xác minh điện thoại, tiền, bản quyền Windows, VPS.
_RE_NGUOI = re.compile(r"đăng nhập|nạp tiền|nạp thêm|xác minh|2fa|điện thoại|bản quyền windows|thuê vps|gia hạn vps|captcha",
                       re.IGNORECASE)
#: Nhắc "chờ N video qua 48h…", "Đợi…" — máy tự đợi.
_RE_CHO_SO = re.compile(r"^\s*(?:đang\s+)?(?:chờ|đợi)\b", re.IGNORECASE)


def phan_loai_viec(chu: Any) -> str:
    """"nguoi" (chỉ người làm được) | "cho_so" (máy tự đợi số) | "may" (máy/bộ não tự xem)."""
    s = " ".join(str(chu or "").split())
    if s.startswith(_NGUOI_TIEN_TO):
        return "nguoi"
    if _RE_CHO_SO.match(s):
        return "cho_so"
    if _RE_NGUOI.search(s):
        return "nguoi"
    return "may"


def phan_loai_de_xuat_nao(chu: Any, ban_do: Optional[Dict[str, str]] = None, kenh: str = "") -> str:
    """Đề xuất của bộ não (`nao de-xuat` = "việc chỉ người làm được" theo não): "may" khi máy nhận ra kiểu việc Studio
    làm được (bật Thử nghiệm và so sánh bìa, đọc sức khoẻ kênh…) và câu không đòi việc chỉ người làm (đăng nhập, xác
    minh, tiền…); còn lại "nguoi" (quyết định chiến lược của chủ). `ban_do` (sổ videoId) + `kenh` = ĐÚNG tham số mà
    `dinh_tuyen_de_xuat_nao` dùng → "ẩn khỏi người" và "vào hàng máy" luôn khớp nhau."""
    if _RE_NGUOI.search(" ".join(str(chu or "").split())):
        return "nguoi"
    return "may" if kieu_viec_may(chu, kenh, ban_do or None) else "nguoi"


def la_viec_suc_khoe(chu: Any) -> bool:
    """Câu cò sức khoẻ (`suc_khoe.VIEC_CUA_BAN`) — 16/10/2026: thành việc máy `studio_kiem_suc_khoe`."""
    from .suc_khoe import VIEC_CUA_BAN  # noqa: PLC0415

    return " ".join(str(chu or "").split()) == " ".join(VIEC_CUA_BAN.split())


# ── việc máy có kiểu (16/10/2026) ───────────────────────────────────────────

LOAI_TEST_COMPARE = "studio_test_compare"      # bật "Thử nghiệm và so sánh" (bìa) cho `video_ids` trong Studio
LOAI_KIEM_SUC_KHOE = "studio_kiem_suc_khoe"    # đọc Studio: cảnh báo chính sách, gậy, "nội dung dùng lại", kiếm tiền
#: 16/10/2026: A/B «Tiêu đề và hình thu nhỏ» (tiêu đề thêm do giám đốc viết — sổ `giam-doc/ab-tieu-de.json`,
#: `core/ab_tieu_de.py`); bộ chạy D13 làm chung với `studio_test_compare`.
LOAI_AB_TIEU_DE = "studio_ab_tieu_de"
LOAI_VIEC_MAY = (LOAI_TEST_COMPARE, LOAI_KIEM_SUC_KHOE, LOAI_AB_TIEU_DE)
TT_CHO, TT_DANG, TT_XONG, TT_LOI, TT_CAN_NGUOI, TT_BO = "cho", "dang", "xong", "loi", "can_nguoi", "bo"
#: Còn việc cho bộ chạy (loi: bộ chạy tự thử lại tới `LAN_THU_TOI_DA`).
TT_MO = (TT_CHO, TT_DANG, TT_LOI)
LAN_THU_TOI_DA = 5
#: Cò sức khoẻ còn báo động thì đọc lại Studio sau ngần này ngày (mục cũ đã xong được mở lại).
NGAY_KIEM_LAI_SUC_KHOE = 3
#: Mục đã kết thúc (xong / bo / can_nguoi đã quá hạn) giữ ngần này ngày rồi bỏ khỏi tệp.
NGAY_GIU_VIEC_KET_THUC = 30
_RE_TEST_COMPARE = re.compile(r"thử nghiệm và so sánh|test\s*(?:&|and|và)\s*compare", re.IGNORECASE)
_RE_SUC_KHOE = re.compile(r"cảnh báo chính sách|\bgậy\b|nội dung dùng lại|reused content|community guidelines strike",
                          re.IGNORECASE)
_RE_VID = re.compile(r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")


def _la_ma_video(x: str) -> bool:
    """Mã video YouTube (11 ký tự) — chữ thường + gạch ("ho-so-video") không phải."""
    return bool(re.search(r"[A-Z0-9]", x))


def ban_do_video_kenh(goc: str) -> Dict[str, str]:
    """`{video_id: mã kênh}` từ sổ videoId của máy đăng (`vm/logs/so-video-id.json`). Hỏng → {}."""
    try:
        from ..trung_tam import thu_muc_vm  # noqa: PLC0415

        tm = thu_muc_vm(goc)
    except Exception:  # noqa: BLE001
        tm = os.path.join(goc, "vm")
    try:
        with io.open(os.path.join(tm, "logs", "so-video-id.json"), encoding="utf-8") as tep:
            so = json.load(tep)
    except (OSError, ValueError):
        return {}
    ra: Dict[str, str] = {}
    for k, v in (so.items() if isinstance(so, dict) else []):
        if isinstance(v, dict) and v.get("video_id") and "/" in str(k):
            ra[str(v["video_id"])] = str(k).split("/", 1)[0]
    return ra


def kieu_viec_may(chu: Any, kenh: str = "", ban_do: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Câu việc → việc máy có kiểu `[{loai, kenh, video_ids}]`; [] = không nhận ra / không biết kênh (máy không làm
    được — để người xem). Mọi mục trả ra đều có `kenh`.

    * câu cò sức khoẻ / câu nhờ xem cảnh báo chính sách, gậy, nội dung dùng lại → `studio_kiem_suc_khoe` của `kenh`;
    * "Thử nghiệm và so sánh" / "Test & compare" + mã video → `studio_test_compare`, tách MỘT mục cho mỗi kênh (kênh của
      video tra `ban_do` = sổ videoId; không tra được thì `kenh`)."""
    s = " ".join(str(chu or "").split())
    if not s:
        return []
    if _RE_TEST_COMPARE.search(s):
        ids = []
        for x in _RE_VID.findall(s):
            if x not in ids and (x in ban_do if ban_do else _la_ma_video(x)):
                ids.append(x)
        nhom: Dict[str, List[str]] = {}
        for x in ids:
            nhom.setdefault((ban_do or {}).get(x) or kenh, []).append(x)
        return [{"loai": LOAI_TEST_COMPARE, "kenh": k, "video_ids": v} for k, v in nhom.items() if k]
    if kenh and (la_viec_suc_khoe(s) or _RE_SUC_KHOE.search(s)):
        return [{"loai": LOAI_KIEM_SUC_KHOE, "kenh": kenh, "video_ids": []}]
    return []


def _id_viec_may(loai: str, kenh: str, video_ids: Any) -> str:
    return "m-" + hashlib.sha1("{0}|{1}|{2}".format(loai, kenh, ",".join(sorted(video_ids or []))).encode("utf-8")) \
        .hexdigest()[:12]


def _don_viec_may(ds: List[Dict[str, Any]], bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Bỏ mục đã kết thúc quá `NGAY_GIU_VIEC_KET_THUC` ngày (mục còn mở không bao giờ tự mất)."""
    return [m for m in ds if m.get("trang_thai") in TT_MO
            or (_tuoi_ngay(m.get("cap_nhat") or m.get("tao_luc"), bay_gio) or 0) <= NGAY_GIU_VIEC_KET_THUC]


def ghi_viec_may_kieu(goc: str, loai: str, kenh: str, *, video_ids: Any = (), nguon: str = "", chu: str = "",
                      bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Thêm MỘT việc máy có kiểu. Cùng (loai, kenh, bộ video) đang mở → không thêm. Đã kết thúc: `kiem_suc_khoe`
    "xong" quá `NGAY_KIEM_LAI_SUC_KHOE` ngày → mở lại (cò vẫn báo động thì đọc Studio lại); còn lại không mở lại.
    Trả True nếu vừa thêm/mở lại."""
    if loai not in LOAI_VIEC_MAY or not kenh or (loai in (LOAI_TEST_COMPARE, LOAI_AB_TIEU_DE) and not video_ids):
        return False
    bay_gio = bay_gio or _dt.datetime.now()
    luc = bay_gio.isoformat(timespec="seconds")
    du = _doc(goc)
    ds = _don_viec_may([m for m in du.get("viec_may") or [] if isinstance(m, dict)], bay_gio)
    vid = list(dict.fromkeys(str(x) for x in video_ids or []))
    ma_id = _id_viec_may(loai, kenh, vid)
    cu = next((m for m in ds if m.get("id") == ma_id), None)
    moi = False
    if cu is None:
        ds.append({"id": ma_id, "loai": loai, "kenh": kenh, "video_ids": vid, "trang_thai": TT_CHO, "nguon": nguon,
                   "chu": str(chu)[:400], "tao_luc": luc, "cap_nhat": luc, "lan_thu": 0, "ket": {}})
        moi = True
    elif (loai == LOAI_KIEM_SUC_KHOE and cu.get("trang_thai") == TT_XONG
          and (_tuoi_ngay(cu.get("cap_nhat"), bay_gio) or 0) >= NGAY_KIEM_LAI_SUC_KHOE):
        cu.update(trang_thai=TT_CHO, cap_nhat=luc, lan_thu=0, nguon=nguon or cu.get("nguon", ""), ket_truoc=cu.get("ket"),
                  ket={})
        moi = True
    if moi or len(ds) != len(du.get("viec_may") or []):
        du["viec_may"] = ds
        _ghi(goc, du)
    return moi


def doc_viec_may_kieu(goc: str, loai: Optional[str] = None,
                      trang_thai: Optional[Any] = TT_MO) -> List[Dict[str, Any]]:
    """Việc máy có kiểu (cũ → mới). `trang_thai=None` = mọi trạng thái. Hỏng → []."""
    try:
        ds = [m for m in _doc(goc).get("viec_may") or [] if isinstance(m, dict)]
    except Exception:  # noqa: BLE001
        return []
    return [m for m in ds if (loai is None or m.get("loai") == loai)
            and (trang_thai is None or m.get("trang_thai") in ((trang_thai,) if isinstance(trang_thai, str)
                                                              else tuple(trang_thai)))]


def cap_nhat_viec_may_kieu(goc: str, id_viec: str, *, bay_gio: Optional[_dt.datetime] = None, **truong: Any) -> bool:
    """Bộ chạy ghi kết quả: `trang_thai` ("dang" | "xong" | "loi" | "can_nguoi" | "bo"), `ket`, `lan_thu`, … "loi" lần
    thứ `LAN_THU_TOI_DA` tự thành "bo". Trả False nếu không có mục."""
    bay_gio = bay_gio or _dt.datetime.now()
    du = _doc(goc)
    ds = [m for m in du.get("viec_may") or [] if isinstance(m, dict)]
    m = next((x for x in ds if x.get("id") == id_viec), None)
    if m is None:
        return False
    m.update(truong)
    m["cap_nhat"] = bay_gio.isoformat(timespec="seconds")
    if m.get("trang_thai") == TT_LOI:
        m["lan_thu"] = int(m.get("lan_thu") or 0) + (0 if "lan_thu" in truong else 1)
        if m["lan_thu"] >= LAN_THU_TOI_DA:
            m["trang_thai"] = TT_BO
    du["viec_may"] = ds
    _ghi(goc, du)
    return True


def dinh_tuyen_de_xuat_nao(goc: str, *, bay_gio: Optional[_dt.datetime] = None) -> int:
    """Gác tổng (mỗi nhịp): đề xuất CÒN MỞ của bộ não mà máy làm được (`phan_loai_de_xuat_nao` = "may") → việc máy có
    kiểu; bảng điều khiển không hiện các đề xuất ấy cho người. Không đổi `nao/hanh-dong.json` (não vẫn tự chấm đề xuất
    của mình). Trả số việc máy mới."""
    try:
        from .. import nao  # noqa: PLC0415

        ds = nao.viec_de_xuat(goc, bay_gio)
    except Exception:  # noqa: BLE001 — não hỏng = như không có não
        return 0
    ban_do = None
    n = 0
    for d in ds:
        if not _RE_TEST_COMPARE.search(d.get("chu") or "") and not _RE_SUC_KHOE.search(d.get("chu") or ""):
            continue
        if ban_do is None:
            ban_do = ban_do_video_kenh(goc)
        if phan_loai_de_xuat_nao(d.get("chu"), ban_do, d.get("kenh") or "") != "may":
            continue
        for v in kieu_viec_may(d.get("chu"), d.get("kenh") or "", ban_do or None):
            n += int(ghi_viec_may_kieu(goc, v["loai"], v["kenh"], video_ids=v["video_ids"], nguon=d.get("khoa") or "",
                                       chu=d.get("chu") or "", bay_gio=bay_gio))
    return n


# ── hàng đợi cho bộ não ─────────────────────────────────────────────────────

def _duong(goc: str) -> str:
    return os.path.join(goc, TEP_HANG_DOI)


def _doc(goc: str) -> Dict[str, Any]:
    try:
        with io.open(_duong(goc), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return {"muc": [], "da_thay": {}}
    if not isinstance(du, dict):
        return {"muc": [], "da_thay": {}}
    du["muc"] = [m for m in du.get("muc") or [] if isinstance(m, dict)]
    du["da_thay"] = du.get("da_thay") if isinstance(du.get("da_thay"), dict) else {}
    return du


def _ghi(goc: str, du: Dict[str, Any]) -> None:
    duong = _duong(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8", newline="\n") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
        tep.write("\n")
    os.replace(tam, duong)


def _tuoi_ngay(luc: Any, bay_gio: _dt.datetime) -> Optional[float]:
    try:
        return (bay_gio - _dt.datetime.fromisoformat(str(luc)[:19])).total_seconds() / 86400.0
    except ValueError:
        return None


def ghi_viec_may(goc: str, ma: str, viec: str, loai: str, *, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Một dòng "Việc của bạn" mà máy lo được. Cùng nội dung chỉ tính MỘT lần (nhớ `HAN_NHO_NGAY` ngày).
    "may" → hàng đợi bộ não; "cho_so" → nhật ký giám đốc kênh (1 lần). Trả True nếu việc MỚI."""
    bay_gio = bay_gio or _dt.datetime.now()
    if loai == "may":
        kieu = kieu_viec_may(viec, ma, ban_do_video_kenh(goc) if _RE_TEST_COMPARE.search(str(viec or "")) else None)
        if kieu:   # 16/10/2026: việc Studio có bộ chạy máy → hàng việc máy có kiểu (không hết hạn 9 ngày)
            return any([ghi_viec_may_kieu(goc, v["loai"], v["kenh"] or ma, video_ids=v["video_ids"],
                                          nguon="giam-doc:" + ma, chu=viec, bay_gio=bay_gio) for v in kieu])
    khoa = hashlib.sha1("{0}|{1}".format(ma, viec).encode("utf-8")).hexdigest()[:12]
    du = _doc(goc)
    du["da_thay"] = {k: v for k, v in du["da_thay"].items()
                     if (_tuoi_ngay(v, bay_gio) if _tuoi_ngay(v, bay_gio) is not None else 99) <= HAN_NHO_NGAY}
    moi = khoa not in du["da_thay"]
    if moi:
        du["da_thay"][khoa] = bay_gio.isoformat(timespec="seconds")
        if loai == "may":
            du["muc"].append({"id": khoa, "kenh": ma, "viec": str(viec)[:400], "luc": du["da_thay"][khoa]})
        else:
            try:
                from . import so_thi_nghiem as stn  # noqa: PLC0415

                stn.ghi_nhat_ky(goc, ma, viec="cho_so", ly_do_llm=str(viec)[:300], bay_gio=bay_gio)
            except Exception:  # noqa: BLE001 — không ghi được nhật ký thì thôi, không báo người
                pass
    truoc = len(du["muc"])
    du["muc"] = [m for m in du["muc"] if (_tuoi_ngay(m.get("luc"), bay_gio) or 0) <= HAN_MUC_NGAY][-TOI_DA_MUC:]
    if moi or len(du["muc"]) != truoc:
        _ghi(goc, du)
    return moi


def doc_viec_cho_nao(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Mục giám đốc nhờ bộ não xem (còn hạn, mới → cũ). Hỏng → []."""
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        ds = [m for m in _doc(goc)["muc"] if (_tuoi_ngay(m.get("luc"), bay_gio) or 0) <= HAN_MUC_NGAY]
    except Exception:  # noqa: BLE001
        return []
    return list(reversed(ds))


# ── quyền tự nâng / hạ theo thành tích ──────────────────────────────────────

def quyen_kenh(goc: str, ma: str, hien_tai: str) -> Dict[str, Any]:
    """Quyền kênh theo `do-chinh-xac.json`, loại "dự đoán thắng/trượt" (thước đo chung của giám đốc).
    `hien_tai` = "goi_y" | "tu_ap". Có hysteresis: đang `tu_ap` chỉ lùi khi n ≥ ngưỡng mà tụt < 55%.
    Trả `{"quyen", "n", "ti_le", "dung", "doi": bool}`."""
    from . import hoi_dong  # noqa: PLC0415

    o = (hoi_dong.do_chinh_xac(goc, ma, ghi=False).get("loai") or {}).get("du_doan") or {}
    n, tl = int(o.get("n") or 0), o.get("ti_le")
    ky_nang = True
    if "ti_le_nen" in o:        # 12/10/2026: đúng nhiều nhờ tỉ lệ nền ≠ kỹ năng (xem hoi_dong.KY_NANG_*)
        bien = hoi_dong.KY_NANG_GIU_HON_NEN if hien_tai == "tu_ap" else hoi_dong.KY_NANG_HON_NEN
        nen = o.get("ti_le_nen")
        ky_nang = bool(nen is not None and tl is not None and tl >= nen + bien
                       and int(o.get("dung_thang") or 0) >= hoi_dong.KY_NANG_DUNG_THANG)
    if not ky_nang:
        moi = "goi_y"
    elif tl is None or n < hoi_dong.TU_AP_N:
        moi = hien_tai
    elif hien_tai == "tu_ap":
        moi = "goi_y" if tl < hoi_dong.LUI_TI_LE else "tu_ap"
    else:
        moi = "tu_ap" if tl >= hoi_dong.TU_AP_TI_LE else "goi_y"
    return {"quyen": moi, "n": n, "ti_le": tl, "dung": o.get("dung"), "doi": moi != hien_tai}


def tu_nang_ha_quyen(goc: str, *, bay_gio: Optional[_dt.datetime] = None,
                     ghi_cai: Optional[Callable[..., None]] = None,
                     ghi: bool = True) -> List[Dict[str, Any]]:
    """Mỗi ngày: kênh `goi_y` đủ thành tích (≥ 70% đúng, n ≥ 10) → `tu_ap`; kênh `tu_ap` tụt (< 55%) → `goi_y`.
    Không đụng kênh `tat`, kênh có cặp `-v2` (A/B giữ `goi_y`), kênh chủ đặt `giam_doc_cho_phep_ab`.
    Ghi `kenh.yaml` qua `trung_tam.ghi_cai_kenh` + nhật ký giám đốc kèm số. Trả danh sách kênh đã đổi."""
    from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
    from . import so_thi_nghiem as stn  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    if ghi_cai is None:
        def ghi_cai(g: str, m: str, **kv: Any) -> None:
            from ..trung_tam import ghi_cai_kenh  # noqa: PLC0415

            ghi_cai_kenh(g, m, **kv)
    ra: List[Dict[str, Any]] = []
    try:
        ten_kenh = sorted(os.listdir(duong_kenh(goc)))
    except OSError:
        return ra
    for ma in ten_kenh:
        if ma.startswith("_") or ma.lower().endswith(("-v2", "_v2")):
            continue
        cai = doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {}
        if str(cai.get("tra_kho") or "").strip():  # 20/10: kênh trả kho không tính
            continue
        cd = str(cai.get("giam_doc") or "tat").strip().lower()
        if cd not in ("goi_y", "tu_ap"):
            continue
        if os.path.isdir(duong_kenh(goc, ma + "-v2")):
            if str(cai.get("giam_doc_cho_phep_ab", "")).lower() != "true":
                continue  # cặp A/B: giữ `goi_y`, không tự nâng
        try:
            q = quyen_kenh(goc, ma, cd)
        except Exception:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
            continue
        if not q["doi"]:
            continue
        ly = "{0}: dự đoán thắng/trượt đúng {1}/{2} = {3:.0%} ({4})".format(
            "nâng giam_doc goi_y → tu_ap" if q["quyen"] == "tu_ap" else "lùi giam_doc tu_ap → goi_y",
            q["dung"], q["n"], q["ti_le"] or 0.0,
            "≥ 70% trên n ≥ 10" if q["quyen"] == "tu_ap" else "tụt dưới 55%")
        if ghi:
            ghi_cai(goc, ma, giam_doc=q["quyen"])
            try:
                stn.ghi_nhat_ky(goc, ma, viec="doi_quyen", truoc=cd, sau=q["quyen"], ly_do_llm=ly, bay_gio=bay_gio)
            except Exception:  # noqa: BLE001
                pass
        ra.append({"ma": ma, "truoc": cd, "sau": q["quyen"], "ly_do": ly})
    return ra
