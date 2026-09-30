"""core/chot_an_toan.py — bốn chốt an toàn để máy tự chạy 1 năm không người trông.

Chủ dự án KHÔNG dùng bot Telegram, tự nạp tiền và tự gia hạn — nên mọi cảnh báo
ở đây trả về dạng "sự cố" (cùng khuôn `core.gac_tong._su_co`), để gác tổng hiện
ở CẢ BA nơi: giao diện (`workspace/tinh-trang.json` → `canh_bao_may`),
`workspace/loi-chay-max.md`, và bản tin gác tổng. Câu viết cho người thường
hiểu, luôn kèm "việc cần làm".

Bốn chốt:

1. VÍ ShopAPI (`core.van_vi` giữ van + số liệu; đây chỉ dựng câu cảnh báo).
2. LICENSE Windows (V5, `core.ban_quyen_windows`): kiểm 1 lần/ngày. Còn ≤10 ngày
   và còn lượt rearm → TỰ `slmgr /rearm`, rồi lên lịch khởi động lại lúc máy rảnh
   (`core.an_toan_khoi_dong.kiem_tra`, và Windows đã bật tự đăng nhập). Hết lượt
   rearm → cảnh báo sớm 30/14/7 ngày.
3. HẠN THUÊ VPS: khoá `ngay_het_han_vps` trong `workspace/cai-dat.json`
   (`"2027-03-15"` hoặc `"15/03/2027"`; để trống thì bỏ qua). Nhắc trước 14/7/3/1 ngày.
4. GIỌNG ĐỌC TRÙNG (4.6): 2 kênh `tu_chay` dùng chung `voice_id` → chỉ CẢNH BÁO.

Hàm nào chạm hệ thống (`slmgr`, `shutdown`, registry, mạng) đều nhận seam để test
không đụng máy thật. KHÔNG hàm nào tự đổi giọng hay tự đổi cấu hình kênh.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import ban_quyen_windows as bq
from . import van_vi

__all__ = ["kiem_tat_ca", "kiem_vi", "kiem_license", "kiem_han_vps", "kiem_giong_trung",
           "doc_trang_thai"]

ChayLenh = Callable[[List[str]], Tuple[int, str]]

#: Sau khi rearm, chưa thấy khởi động lại trong ngần này ngày thì KHÔNG rearm lại
#: (mỗi lượt rearm chỉ có vài lần — tuyệt đối không đốt lượt thứ hai oan).
NGAY_KHOA_REARM = 5
#: Khởi động lại bằng `shutdown /r /t <giây>` — cho người đang xem 2 phút để lưu việc.
GIAY_DEM_KHOI_DONG_LAI = 120

#: Câu lặp báo (giờ) cho từng loại — ví lặp 4 giờ; hạn ngày (license/VPS/giọng) 24 giờ.
LAP_VI_GIO = 4.0
LAP_NGAY_GIO = 24.0


def _duong_trang_thai(goc: str) -> str:
    return os.path.join(goc, "workspace", "chot-an-toan.json")


def doc_trang_thai(goc: str) -> Dict[str, Any]:
    try:
        with open(_duong_trang_thai(goc), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_trang_thai(goc: str, du: Dict[str, Any]) -> None:
    try:
        duong = _duong_trang_thai(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def _su_co(loai: str, muc: str, chuyen_gi: str, can_lam_gi: str, neu_khong_lam: str, *,
           khoa: str, lap_gio: float) -> Dict[str, Any]:
    """Cùng khuôn `core.gac_tong._su_co` (+ `lap_gio` để lọc lặp theo loại)."""
    return {"loai": loai, "kenh": "", "muc": muc, "chuyen_gi": chuyen_gi,
            "can_lam_gi": can_lam_gi, "neu_khong_lam": neu_khong_lam,
            "dedupe_khoa": khoa, "lap_gio": lap_gio}


def _muc(ten: str) -> str:
    from . import bao_dong  # noqa: PLC0415

    return {"khan": bao_dong.MUC_KHAN, "nhac": bao_dong.MUC_NHAC}[ten]


# ═══ 1) VÍ ═══════════════════════════════════════════════════════════════════


def kiem_vi(goc: str, *, client: Any = None, bay_gio: Optional[float] = None,
            lay: Optional[Callable[[Any], Any]] = None) -> Tuple[List[Dict[str, Any]], Optional[float]]:
    """`(sự cố, số dư VND | None)`. Cập nhật `workspace/vi/trang-thai.json` (giao diện đọc)."""
    _duoc, _ly, dg = van_vi.cho_phep_mo_luot(goc, client, bay_gio=bay_gio, lay=lay)
    tt = van_vi.doc_trang_thai(goc)
    ra: List[Dict[str, Any]] = []
    het = tt.get("het_tien") if isinstance(tt.get("het_tien"), dict) else None
    if het:
        ra.append(_su_co(
            "vi_het_tien", _muc("khan"),
            "Ví ShopAPI HẾT TIỀN giữa lúc đang làm video. Máy đã dừng êm, phần đã làm "
            "được giữ nguyên.",
            "Nạp tiền vào ví ShopAPI. Không cần bấm gì thêm: máy tự chạy tiếp khi thấy ví "
            "có tiền.",
            "Kênh ngừng ra video mới cho tới khi có tiền.",
            khoa="vi:het_tien", lap_gio=LAP_VI_GIO))
    elif dg["muc"] in ("het", "som"):
        ra.append(_su_co(
            "vi_sap_can", _muc("khan"), dg["cau"], dg["viec_can_lam"],
            "Hết tiền giữa lượt sản xuất, kênh dừng ra video mới.",
            khoa="vi:" + dg["muc"], lap_gio=LAP_VI_GIO))
    return ra, dg.get("so_du_vnd")


# ═══ 2) LICENSE WINDOWS ═════════════════════════════════════════════════════


def _tu_dang_nhap_bat_that() -> bool:
    try:
        import winreg  # noqa: PLC0415

        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon") as khoa:
            gia_tri, _ = winreg.QueryValueEx(khoa, "AutoAdminLogon")
        return str(gia_tri).strip() == "1"
    except Exception:  # noqa: BLE001
        return False


def _chay_lenh_that(lenh: List[str]) -> Tuple[int, str]:
    return bq._chay_lenh_mac_dinh(lenh)  # noqa: SLF001


def _khoi_dong_lai_khi_ranh(goc: str, tt_lic: Dict[str, Any], bay_gio: _dt.datetime, *,
                            chay_lenh: ChayLenh, tu_dang_nhap_bat: Callable[[], bool],
                            an_toan_fn: Optional[Callable[..., Dict[str, Any]]] = None
                            ) -> Optional[str]:
    """Đang chờ khởi động lại sau rearm → làm khi máy rảnh. Trả câu mô tả nếu vừa ra lệnh."""
    if not tt_lic.get("cho_khoi_dong_lai"):
        return None
    if not tu_dang_nhap_bat():
        return None  # khởi động lại mà không tự đăng nhập là máy mù — để người làm (có cảnh báo)
    from . import an_toan_khoi_dong  # noqa: PLC0415

    kiem = (an_toan_fn or an_toan_khoi_dong.kiem_tra)(goc, bay_gio)
    if not kiem.get("duoc"):
        tt_lic["ly_do_cho_ranh"] = "; ".join(kiem.get("ly_do") or [])[:300]
        return None
    ma, ra = chay_lenh(["shutdown", "/r", "/t", str(GIAY_DEM_KHOI_DONG_LAI), "/c",
                        "ShopAPI Studio: khởi động lại để áp dụng gia hạn Windows (rearm)."])
    if ma != 0:
        tt_lic["loi_khoi_dong_lai"] = (ra or "")[:200]
        return None
    tt_lic["cho_khoi_dong_lai"] = False
    tt_lic["khoi_dong_lai_luc"] = bay_gio.isoformat(timespec="seconds")
    tt_lic.pop("ly_do_cho_ranh", None)
    return "Đã ra lệnh khởi động lại máy sau {0} giây (máy rảnh).".format(GIAY_DEM_KHOI_DONG_LAI)


def kiem_license(goc: str, bay_gio: Optional[_dt.datetime] = None, *,
                 chay_lenh: Optional[ChayLenh] = None,
                 tu_dang_nhap_bat: Optional[Callable[[], bool]] = None,
                 an_toan_fn: Optional[Callable[..., Dict[str, Any]]] = None,
                 doc_giay_phep: Optional[Callable[..., Dict[str, Any]]] = None,
                 cho_phep_rearm: bool = True
                 ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """`(sự cố, số ngày còn lại | None)`. Đọc `slmgr` tối đa 1 lần/ngày (ngoài ra
    dùng số đã nhớ); việc khởi động lại chờ được xét MỖI lần gọi."""
    bay_gio = bay_gio or _dt.datetime.now()
    chay_lenh = chay_lenh or _chay_lenh_that
    tu_dang_nhap_bat = tu_dang_nhap_bat or _tu_dang_nhap_bat_that
    doc_gp = doc_giay_phep or (lambda: bq.doc_giay_phep(chay_lenh=chay_lenh))

    st = doc_trang_thai(goc)
    lic = st.get("license") if isinstance(st.get("license"), dict) else {}
    hom_nay = bay_gio.strftime("%Y-%m-%d")

    if lic.get("ngay_kiem") != hom_nay:
        try:
            tin = doc_gp()
        except Exception:  # noqa: BLE001
            tin = None
        lic["ngay_kiem"] = hom_nay
        if tin is not None:
            lic["vinh_vien"] = bool(tin.get("vinh_vien"))
            lic["so_ngay_con_lai"] = tin.get("so_ngay_con_lai")
            lic["rearm_con_lai"] = tin.get("rearm_con_lai")
            het_han = tin.get("het_han")
            lic["het_han"] = het_han.isoformat() if het_han else None

            goi_y = bq.nen_rearm(tin, goc, bay_gio=bay_gio)
            # KHÔNG dựa vào khung an toàn để rearm (rearm không làm gián đoạn gì, chỉ
            # khởi động lại mới cần rảnh) — chỉ cần trong hạn + còn lượt.
            if (cho_phep_rearm and goi_y["trong_han"] and goi_y["con_rearm"]
                    and not lic.get("cho_khoi_dong_lai")
                    and not _moi_rearm(lic, bay_gio)):
                ok, ra = bq.thuc_hien_rearm(chay_lenh=chay_lenh)
                lic["rearm_luc"] = bay_gio.isoformat(timespec="seconds")
                if ok:
                    lic["cho_khoi_dong_lai"] = True
                    lic.pop("loi_rearm", None)
                    lic["so_lan_rearm_tu_dong"] = int(lic.get("so_lan_rearm_tu_dong") or 0) + 1
                else:
                    lic["loi_rearm"] = (ra or "")[:300]
                    lic.pop("rearm_luc", None)  # lần sau (mai) thử lại
        else:
            lic["khong_doc_duoc"] = hom_nay

    vua_ra_lenh = _khoi_dong_lai_khi_ranh(
        goc, lic, bay_gio, chay_lenh=chay_lenh, tu_dang_nhap_bat=tu_dang_nhap_bat,
        an_toan_fn=an_toan_fn)
    st["license"] = lic
    _ghi_trang_thai(goc, st)

    ra: List[Dict[str, Any]] = []
    so_ngay = lic.get("so_ngay_con_lai")
    rearm = lic.get("rearm_con_lai")
    if lic.get("vinh_vien"):
        return [], None
    if lic.get("loi_rearm"):
        ra.append(_su_co(
            "license_rearm_loi", _muc("khan"),
            "Windows sắp hết hạn dùng thử (còn {0} ngày) và máy tự gia hạn (rearm) KHÔNG "
            "được: {1}".format(so_ngay, lic["loi_rearm"][:120]),
            "Mở máy (RDP), chạy tay PowerShell quản trị: cscript //nologo "
            "%windir%\\system32\\slmgr.vbs /rearm rồi khởi động lại máy.",
            "Windows hết hạn thì máy tắt định kỳ, kênh ngừng đăng.",
            khoa="license:rearm_loi", lap_gio=LAP_NGAY_GIO))
    if lic.get("cho_khoi_dong_lai"):
        ly_do = lic.get("ly_do_cho_ranh") or ""
        if not tu_dang_nhap_bat():
            ra.append(_su_co(
                "license_cho_khoi_dong_lai", _muc("khan"),
                "Windows đã được gia hạn (rearm) nhưng CẦN KHỞI ĐỘNG LẠI máy, và máy chưa bật "
                "tự đăng nhập nên tool KHÔNG tự khởi động lại.",
                "Mở máy (RDP) và khởi động lại Windows (Start > Restart), rồi đăng nhập lại.",
                "Gia hạn không có tác dụng và Windows vẫn hết hạn đúng hạn cũ.",
                khoa="license:cho_khoi_dong_lai", lap_gio=LAP_NGAY_GIO))
        else:
            ra.append(_su_co(
                "license_cho_khoi_dong_lai", _muc("nhac"),
                "Windows đã tự gia hạn (rearm), đang chờ lúc máy rảnh để khởi động lại"
                + (" ({0}).".format(ly_do) if ly_do else "."),
                "Không cần làm gì — máy tự khởi động lại khi không có lượt dựng/đăng nào.",
                "Nếu máy không rảnh quá lâu, mở máy và tự khởi động lại.",
                khoa="license:cho_khoi_dong_lai", lap_gio=LAP_NGAY_GIO))
    if vua_ra_lenh:
        ra.append(_su_co(
            "license_khoi_dong_lai", _muc("nhac"),
            "Windows vừa được gia hạn (rearm). " + vua_ra_lenh,
            "Không cần làm gì; máy tự đăng nhập lại và tool tự chạy tiếp.",
            "", khoa="license:khoi_dong_lai:" + str(lic.get("khoi_dong_lai_luc")),
            lap_gio=LAP_NGAY_GIO))
    if isinstance(so_ngay, int) and rearm is not None and rearm <= 0 and so_ngay <= 30:
        muc = "khan" if so_ngay <= 14 else "nhac"
        moc = 7 if so_ngay <= 7 else 14 if so_ngay <= 14 else 30
        ra.append(_su_co(
            "license_het_rearm", _muc(muc),
            "Windows hết hạn dùng thử sau {0} ngày{1} và ĐÃ HẾT lượt gia hạn tự động (rearm)."
            .format(so_ngay, " (ngày {0})".format(lic["het_han"]) if lic.get("het_han") else ""),
            "Mua/nhập khoá bản quyền Windows hợp lệ (Settings > Activation), hoặc dựng lại VPS.",
            "Tới hạn Windows tự tắt máy theo giờ, kênh ngừng đăng.",
            khoa="license:het_rearm:{0}".format(moc), lap_gio=LAP_NGAY_GIO))
    return ra, (so_ngay if isinstance(so_ngay, int) else None)


def _moi_rearm(lic: Dict[str, Any], bay_gio: _dt.datetime) -> bool:
    luc = lic.get("rearm_luc")
    if not luc:
        return False
    try:
        return (bay_gio - _dt.datetime.fromisoformat(luc)).days < NGAY_KHOA_REARM
    except ValueError:
        return False


# ═══ 3) HẠN THUÊ VPS ════════════════════════════════════════════════════════


def _doc_ngay(chu: Any) -> Optional[_dt.date]:
    chu = str(chu or "").strip()
    if not chu:
        return None
    for dang in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return _dt.datetime.strptime(chu, dang).date()
        except ValueError:
            continue
    return None


def kiem_han_vps(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        with open(os.path.join(goc, "workspace", "cai-dat.json"), "r", encoding="utf-8") as tep:
            cai = json.load(tep)
    except (OSError, ValueError):
        return []
    tho = cai.get("ngay_het_han_vps") if isinstance(cai, dict) else None
    if not str(tho or "").strip():
        return []
    han = _doc_ngay(tho)
    if han is None:
        return [_su_co(
            "han_vps_sai_dinh_dang", _muc("nhac"),
            "Ô \"ngay_het_han_vps\" trong workspace/cai-dat.json ghi \"{0}\" — máy không đọc "
            "được thành ngày.".format(str(tho)[:40]),
            "Sửa lại thành dạng 2027-03-15 (năm-tháng-ngày) hoặc 15/03/2027.",
            "Không có nhắc hạn thuê VPS.",
            khoa="vps:sai_dinh_dang", lap_gio=LAP_NGAY_GIO)]
    con = (han - bay_gio.date()).days
    if con > 14:
        return []
    ngay_chu = han.strftime("%d/%m/%Y")
    moc = 0 if con <= 0 else 1 if con <= 1 else 3 if con <= 3 else 7 if con <= 7 else 14
    if con <= 0:
        cau = "Hạn thuê VPS ĐÃ QUA ({0}).".format(ngay_chu)
    else:
        cau = "Hạn thuê VPS còn {0} ngày (hết {1}).".format(con, ngay_chu)
    return [_su_co(
        "han_vps", _muc("khan" if con <= 3 else "nhac"), cau,
        "Gia hạn thuê VPS ở nhà cung cấp; xong sửa \"ngay_het_han_vps\" trong "
        "workspace/cai-dat.json sang ngày hết hạn mới.",
        "VPS bị tắt/xoá thì mọi kênh ngừng đăng.",
        khoa="vps:{0}".format(moc), lap_gio=LAP_NGAY_GIO)]


# ═══ 4) GIỌNG ĐỌC TRÙNG ═════════════════════════════════════════════════════


def kiem_giong_trung(goc: str) -> List[Dict[str, Any]]:
    """Cảnh báo (KHÔNG tự đổi) khi ≥2 kênh `tu_chay` cùng `voice_id`."""
    try:
        from . import tu_chay  # noqa: PLC0415
        from .kenh import doc_kenh  # noqa: PLC0415

        nhom: Dict[str, List[str]] = {}
        for ma in tu_chay.kenh_tu_chay(goc):
            try:
                vid = str(getattr(doc_kenh(goc, ma), "voice_id", "") or "").strip()
            except Exception:  # noqa: BLE001
                continue
            if vid:
                nhom.setdefault(vid, []).append(ma)
    except Exception:  # noqa: BLE001
        return []
    ra: List[Dict[str, Any]] = []
    for vid, cac in sorted(nhom.items()):
        if len(cac) < 2:
            continue
        ra.append(_su_co(
            "giong_doc_trung", _muc("nhac"),
            "{0} kênh ({1}) đang dùng CHUNG một giọng đọc (voice_id {2}…) — video nghe giống "
            "hệt nhau, dễ bị coi là nội dung lặp hoặc các kênh bị liên kết với nhau."
            .format(len(cac), ", ".join(cac), vid[:6]),
            "Chọn giọng tiếng Nhật KHÁC nhau cho từng kênh (gợi ý: workspace/giong-doc-goi-y.md) "
            "rồi sửa \"voice_id\" trong CHANNEL/<kênh>/kenh.yaml. Máy KHÔNG tự đổi giọng.",
            "Rủi ro nội dung lặp / kênh bị YouTube coi là cùng một chủ.",
            khoa="giong:" + vid, lap_gio=LAP_NGAY_GIO * 7))
    return ra


# ═══ GỘP ═════════════════════════════════════════════════════════════════════


def kiem_tat_ca(goc: str, bay_gio: Optional[_dt.datetime] = None, *, client: Any = None,
                chay_lenh: Optional[ChayLenh] = None, **seam: Any) -> Dict[str, Any]:
    """`{"su_co": [...], "so_du_vnd": float|None, "license_ngay": int|None}`. Mỗi chốt tự
    bọc lỗi — một chốt hỏng không làm mất các chốt khác (nhưng KHÔNG im lặng: ghi sự cố)."""
    bay_gio = bay_gio or _dt.datetime.now()
    su_co: List[Dict[str, Any]] = []
    so_du: Optional[float] = None
    ngay_lic: Optional[int] = None

    def _hong(ten: str, loi: Exception) -> Dict[str, Any]:
        return _su_co("chot_an_toan_hong", _muc("nhac"),
                      "Chốt an toàn \"{0}\" không kiểm được: {1}".format(ten, str(loi)[:150]),
                      "Báo người quản trị tool xem nhật ký.", "", khoa="chot:" + ten,
                      lap_gio=LAP_NGAY_GIO)
    try:
        r, so_du = kiem_vi(goc, client=client, bay_gio=bay_gio.timestamp(),
                           lay=seam.get("lay_so_du"))
        su_co += r
    except Exception as loi:  # noqa: BLE001
        su_co.append(_hong("vi", loi))
    try:
        r, ngay_lic = kiem_license(
            goc, bay_gio, chay_lenh=chay_lenh,
            tu_dang_nhap_bat=seam.get("tu_dang_nhap_bat"), an_toan_fn=seam.get("an_toan_fn"),
            doc_giay_phep=seam.get("doc_giay_phep"),
            cho_phep_rearm=seam.get("cho_phep_rearm", True))
        su_co += r
    except Exception as loi:  # noqa: BLE001
        su_co.append(_hong("license", loi))
    try:
        su_co += kiem_han_vps(goc, bay_gio)
    except Exception as loi:  # noqa: BLE001
        su_co.append(_hong("han_vps", loi))
    try:
        su_co += kiem_giong_trung(goc)
    except Exception as loi:  # noqa: BLE001
        su_co.append(_hong("giong", loi))
    return {"su_co": su_co, "so_du_vnd": so_du, "license_ngay": ngay_lic}
