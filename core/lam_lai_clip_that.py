"""Làm lại bằng CLIP THẬT những gói có cảnh dựng từ ảnh — luật 07/10/2026.

═══ VÌ SAO ═══

Đêm 06/10/2026 kho clip của cổng hết hạn mức; đường lùi v2.170.0 dựng 22–129
cảnh/gói bằng ảnh tĩnh (Ken Burns, `6-clip/tu-anh.json`) cho cả bảy gói đăng
05:00 ngày 07/10, rồi dựng, QA, BÀN GIAO lúc 01:00 — một gói đã kịp lên YouTube
(bản nháp, máy đăng gãy ngay sau khi tải). Chủ dự án: *"Chỗ ShopAPI lỗi thì
retry thôi — không nên dùng các phương án mà sản phẩm cuối kém — thà không đăng
còn hơn là sản phẩm cuối không ổn."*

═══ LỆNH ═══

    python -m core.lam_lai_clip_that --tat-ca --thu          # chỉ IN kế hoạch
    python -m core.lam_lai_clip_that --kenh K --ma 0021      # làm thật một gói
    python -m core.lam_lai_clip_that --tat-ca                # làm thật mọi gói

Mỗi gói có `6-clip/tu-anh.json` (cảnh dựng từ ảnh):

1. GỠ BÀN GIAO cho sạch — xoá dòng kế hoạch (`ke-hoach.csv`, khe giờ được trả
   lại; giữ dòng thì bàn giao lại sẽ giữ NGUYÊN giờ cũ), xoá dòng ấy ở bản đệm
   kế hoạch của máy đăng (`vm/ke-hoach-<kênh>.csv`), xoá thư mục gói trong DONE
   (máy đăng không còn gì để tải), sổ ngày tu_chay của lượt: `da_ban_giao` →
   false, `xong_het` → false, bộ đếm phục hồi về 0.
2. Gói ĐÃ LÊN YOUTUBE (sổ máy đăng `vm/logs/so-video-id.json` có videoId): KHÔNG
   đụng gì trên YouTube (xoá nháp là việc của chủ). Mục sổ được cất: videoId cũ
   chuyển vào `id_cu`, `video_id` để trống, đếm lượt tải hôm nay về 0 — lần tải
   lại sau không bị bỏ qua là "đã tải" và không vướng trần tải/ngày. Báo chủ
   (`workspace/loi-chay-max.md` + báo khẩn) để xoá bản nháp, tránh hai video
   cùng tiêu đề trên Studio.
3. Xoá ĐÚNG các clip dựng từ ảnh liệt kê trong `tu-anh.json` + chính tệp ấy +
   video đã dựng và tệp suy ra từ nó (`8-video*.mp4`, `9-video-capcut.mp4`,
   `8-phu-de.srt`, `8-phan.json`, `8-nhac*`, `_cat/`, `_dung-do/`). Kịch bản,
   giọng đọc, phụ đề gốc, ảnh, clip thật, ảnh bìa: GIỮ NGUYÊN.
4. `trang-thai.json`: khâu clip + khâu dựng về CHỜ — `core.tu_chay` nhặt lại
   lượt (`_tim_run_chua_xong`) và chạy tiếp ĐÚNG từ khâu clip (khâu đã xong bỏ
   qua, không trả tiền lại); kho clip còn hết hạn mức thì khâu clip CHỜ engine.

Mọi tệp nhỏ bị sửa được sao lưu trước vào `workspace/sao-luu/lam-lai-clip-that/
<giờ>/`. Kênh đang có tiến trình tu_chay sống (khoá `.khoa`) hoặc máy đăng đang
dở (`vm/logs/dang-dodang.json`) → không làm thật (in lý do), chạy lại sau.

`mo_lai_khau_clip` (dùng ở `core.tu_chay`): lượt "đã xong" mà còn cảnh không
phải clip thật → mở lại khâu clip + dựng, để lượt dở bàn giao bị từ chối không
kẹt mãi ở bước bàn giao.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["tim_goi", "lap_ke_hoach", "thuc_hien", "mo_lai_khau_clip", "dat_lai_khau_clip",
           "TEP_DAU_LAM_LAI", "TRANG_THAI_SO_LAM_LAI", "main"]

#: Tệp ghi chú để lại trong thư mục lượt (chủ mở thư mục là thấy vì sao).
TEP_DAU_LAM_LAI = "LAM-LAI-CLIP-THAT.txt"
#: Trạng thái mục sổ máy đăng sau khi cất videoId nháp cũ.
TRANG_THAI_SO_LAM_LAI = "lam-lai-clip-that"
#: Video + tệp suy ra từ clip (khâu dựng làm lại hết).
_TEP_SUY_RA = ("8-video.mp4", "8-video.cu.mp4", "9-video-capcut.mp4", "8-phu-de.srt",
               "8-phan.json", "8-nhac.json", "8-nhac-nen.m4a")
_THU_MUC_SUY_RA = ("_cat", "_dung-do")


def _goc_mac_dinh() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    from .ghi_dia import ghi_json  # noqa: PLC0415

    ghi_json(duong, du)


# ── Mở lại khâu clip (dùng chung CLI + tu_chay) ─────────────────────────────


def dat_lai_khau_clip(luot) -> None:
    """Khâu clip + dựng về CHỜ (xoá lỗi, ghi chú, mốc giờ) rồi ghi `trang-thai.json`."""
    from . import auto  # noqa: PLC0415

    for ma in ("clip", "dung"):
        tt = luot.tt(ma)
        tt.trang_thai = auto.CHO
        tt.loi = ""
        tt.ghi_chu = {}
        tt.bat_dau = 0.0
        tt.ket_thuc = 0.0
    auto.ghi_luot(luot)


def mo_lai_khau_clip(luot, kenh: Any = None, log: Optional[Callable[[str], None]] = None) -> bool:
    """Lượt coi như đã xong (dựng XONG) mà còn cảnh KHÔNG phải clip thật (clip từ
    ảnh ở kênh không bật `clip_tu_anh`, hoặc thiếu clip) → mở lại khâu clip +
    dựng. Trả True nếu đã mở lại. Không ném lỗi."""
    from . import auto  # noqa: PLC0415
    from .ban_giao_dang import kiem_clip_that  # noqa: PLC0415

    try:
        if luot.tt("dung").trang_thai != auto.XONG and not luot.xong_het:
            return False
        try:
            from .timelapse import la_timelapse  # noqa: PLC0415

            tl = bool(la_timelapse(kenh)) if kenh is not None else False
        except Exception:  # noqa: BLE001
            tl = False
        kq = kiem_clip_that(luot.thu_muc, kiem_thieu=not tl)
        cho_phep = bool(getattr(kenh, "clip_tu_anh", False))
        loi = [x for x in kq["loi"] if not (cho_phep and "DỰNG TỪ ẢNH" in x)]
        if not loi:
            return False
        dat_lai_khau_clip(luot)
        if log is not None:
            log("  [LÀM LẠI CLIP THẬT] lượt {0}: {1} — mở lại khâu clip + dựng (luật 07/10/2026: "
                "thà không đăng còn hơn sản phẩm kém).".format(luot.ma_luot, "; ".join(loi)))
        return True
    except Exception as loi_mo:  # noqa: BLE001
        if log is not None:
            log("  (không kiểm được clip thật của lượt: {0})".format(str(loi_mo)[:120]))
        return False


# ── Tìm gói + lập kế hoạch (CHỈ ĐỌC) ────────────────────────────────────────


def tim_goi(goc: str, kenh: str = "", ma_luot: str = "") -> List[Tuple[str, str]]:
    """`[(kênh, mã lượt)]` có `6-clip/tu-anh.json` liệt kê ít nhất một cảnh."""
    goc_auto = os.path.join(goc, "PROJECTS", "AUTO")
    try:
        cac_kenh = [kenh] if kenh else sorted(os.listdir(goc_auto))
    except OSError:
        return []
    ra = []
    for k in cac_kenh:
        try:
            cac_luot = [ma_luot] if ma_luot else sorted(os.listdir(os.path.join(goc_auto, k)))
        except OSError:
            continue
        for m in cac_luot:
            du = _doc_json(os.path.join(goc_auto, k, m, "6-clip", "tu-anh.json"))
            if isinstance(du, dict) and du.get("canh"):
                ra.append((k, m))
    return ra


def _tim_so_ngay(goc: str, kenh: str, ma_luot: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """(đường sổ ngày, mục run chính) của lượt — sổ mới nhất có `ma_luot` này."""
    from .kenh import duong_kenh  # noqa: PLC0415

    thu_muc = os.path.join(duong_kenh(goc, kenh), "tu-chay")
    try:
        ten = sorted((t for t in os.listdir(thu_muc) if t.endswith(".json")
                      and len(t) == len("2026-10-06.json") and t[:4].isdigit()), reverse=True)
    except OSError:
        return "", None
    for t in ten:
        du = _doc_json(os.path.join(thu_muc, t))
        if not isinstance(du, dict):
            continue
        for r in du.get("runs") or []:
            if isinstance(r, dict) and str(r.get("ma_luot") or "") == ma_luot \
                    and not r.get("tham_chieu_ma_luot"):
                return os.path.join(thu_muc, t), r
    return "", None


def _khoa_kenh_song(goc: str, kenh: str) -> int:
    """PID tu_chay đang giữ khoá kênh (sống), 0 nếu không."""
    from .kenh import duong_kenh  # noqa: PLC0415

    du = _doc_json(os.path.join(duong_kenh(goc, kenh), "tu-chay", ".khoa"))
    try:
        pid = int((du or {}).get("pid") or 0)
    except (TypeError, ValueError, AttributeError):
        return 0
    if pid <= 0:
        return 0
    try:
        from .khe import pid_con_song  # noqa: PLC0415

        return pid if pid_con_song(pid) else 0
    except Exception:  # noqa: BLE001
        return pid


def _dong_csv(duong: str, ma_goi: str) -> bool:
    """Bản đệm CSV có dòng `ma_goi` không."""
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            dong = list(csv.reader(io.StringIO(tep.read())))
    except OSError:
        return False
    if not dong or "Mã gói" not in dong[0]:
        return False
    i = dong[0].index("Mã gói")
    return any(len(d) > i and d[i].strip() == ma_goi for d in dong[1:])


def lap_ke_hoach(goc: str, kenh: str, ma_luot: str) -> Dict[str, Any]:
    """Kế hoạch làm lại MỘT gói — chỉ đọc đĩa, không đổi gì."""
    from . import ke_hoach_dang  # noqa: PLC0415
    from .auto import doc_luot, duong_luot  # noqa: PLC0415
    from .ban_giao_dang import ma_goi as _ma_goi  # noqa: PLC0415
    from .ho_so_video import duong_tep_ho_so  # noqa: PLC0415
    from .kenh import doc_kenh  # noqa: PLC0415

    thu_muc_luot = duong_luot(goc, kenh, ma_luot)
    ma_goi = _ma_goi(kenh, ma_luot)
    kh: Dict[str, Any] = {"kenh": kenh, "ma_luot": ma_luot, "ma_goi": ma_goi,
                          "thu_muc_luot": thu_muc_luot, "canh_bao": [], "chan": ""}
    du = _doc_json(os.path.join(thu_muc_luot, "6-clip", "tu-anh.json")) or {}
    tu_anh = sorted({int(x) for x in (du.get("canh") or [])}) if isinstance(du, dict) else []
    kh["tu_anh"] = tu_anh
    kh["tong"] = int(du.get("tong") or 0) if isinstance(du, dict) else 0
    kh["xoa_clip"] = [p for p in (os.path.join(thu_muc_luot, "6-clip", "{0}.mp4".format(n))
                                  for n in tu_anh) if os.path.isfile(p)]
    kh["xoa_khac"] = ([p for p in (os.path.join(thu_muc_luot, t) for t in _TEP_SUY_RA)
                       if os.path.isfile(p)]
                      + [p for p in (os.path.join(thu_muc_luot, t) for t in _THU_MUC_SUY_RA)
                         if os.path.isdir(p)])
    # Kế hoạch đăng.
    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    kh["dong_ke_hoach"] = None
    if "Mã gói" in cot:
        o = cot.index("Mã gói")
        for d in hang:
            if d[o].strip() == ma_goi:
                kh["dong_ke_hoach"] = {t: (d[cot.index(t)] if t in cot else "")
                                       for t in ("Ngày đăng", "Giờ đăng", "Sẵn sàng",
                                                 "Trạng thái đăng", "Video ID")}
                break
    kh["ke_hoach_csv"] = ke_hoach_dang.duong_ke_hoach(goc, kenh)
    cache = os.path.join(goc, "vm", "ke-hoach-{0}.csv".format(kenh))
    kh["cache_csv"] = [cache] if _dong_csv(cache, ma_goi) else []
    # Gói DONE.
    try:
        k = doc_kenh(goc, kenh)
        done = str(k.thu_muc_done or "")
    except Exception:  # noqa: BLE001
        done = ""
    goi = os.path.join(done, ma_goi) if done else ""
    kh["goi_done"] = goi if goi and os.path.isdir(goi) else ""
    # Sổ máy đăng.
    so = _doc_json(os.path.join(goc, "vm", "logs", "so-video-id.json"))
    khoa_so = "{0}/{1}".format(kenh, ma_goi)
    muc = so.get(khoa_so) if isinstance(so, dict) else None
    kh["so_video_id"] = None
    if isinstance(muc, dict) and muc.get("video_id"):
        kh["so_video_id"] = {"khoa": khoa_so, "video_id": str(muc.get("video_id")),
                             "trang_thai": str(muc.get("trang_thai") or ""),
                             "tai_luc": str(muc.get("tai_xong_luc") or muc.get("cap_nhat") or "")}
        kh["canh_bao"].append(
            "ĐÃ LÊN YOUTUBE: video {0} ({1}, tải {2}) — KHÔNG xoá tự động; chủ kênh xoá tay bản "
            "này trên Studio trước khi bật lại tu_dang (không thì Studio có hai video cùng "
            "tiêu đề).".format(kh["so_video_id"]["video_id"], kh["so_video_id"]["trang_thai"] or "?",
                               kh["so_video_id"]["tai_luc"] or "?"))
    # Sổ ngày tu_chay.
    duong_so_ngay, run = _tim_so_ngay(goc, kenh, ma_luot)
    kh["so_ngay"] = duong_so_ngay
    kh["run_ban_giao"] = dict((run or {}).get("ban_giao") or {}) if run else None
    if run is None:
        kh["canh_bao"].append("không thấy lượt trong sổ tu-chay 7 ngày — tu_chay sẽ nhận nuôi "
                              "lượt mồ côi (L1) thay vì chạy tiếp theo sổ")
    elif run.get("bo"):
        kh["canh_bao"].append("lượt đang bị đánh dấu BỎ trong sổ — sẽ gỡ dấu bỏ")
    # Hồ sơ video.
    duong_hs = duong_tep_ho_so(goc, kenh, ma_goi)
    hs = _doc_json(duong_hs)
    kh["ho_so"] = duong_hs if isinstance(hs, dict) and hs.get("video_id") else ""
    # Trạng thái lượt.
    luot = doc_luot(thu_muc_luot)
    kh["trang_thai"] = ({m: luot.tt(m).trang_thai for m in ("anh", "clip", "thumbnail", "dung")}
                        if luot is not None else None)
    if luot is None:
        kh["chan"] = "không đọc được trang-thai.json của lượt"
    # Chặn làm thật.
    pid = _khoa_kenh_song(goc, kenh)
    if pid:
        kh["chan"] = kh["chan"] or "kênh đang có tiến trình tu_chay sống (PID {0}) — chạy lại sau".format(pid)
    if os.path.exists(os.path.join(goc, "vm", "logs", "dang-dodang.json")):
        kh["chan"] = kh["chan"] or "máy đăng đang dở một gói (vm/logs/dang-dodang.json) — chạy lại sau"
    return kh


def in_ke_hoach(kh: Dict[str, Any], goc: str, ghi: Callable[[str], None] = print) -> None:
    def rel(p: str) -> str:
        try:
            return os.path.relpath(p, goc)
        except ValueError:
            return p
    ghi("● {0} (lượt {1}/{2}) — {3}/{4} cảnh là clip dựng từ ảnh".format(
        kh["ma_goi"], kh["kenh"], kh["ma_luot"], len(kh["tu_anh"]), kh["tong"] or "?"))
    dk = kh.get("dong_ke_hoach")
    ghi("   - kế hoạch: {0}".format(
        "XOÁ dòng {0} {1} (Sẵn sàng={2!r}, Trạng thái={3!r}, Video ID={4!r}) → trả khe".format(
            dk["Ngày đăng"], dk["Giờ đăng"], dk["Sẵn sàng"], dk["Trạng thái đăng"], dk["Video ID"])
        if dk else "không có dòng"))
    for c in kh["cache_csv"]:
        ghi("   - bản đệm máy đăng: XOÁ dòng ở {0}".format(rel(c)))
    ghi("   - gói DONE: {0}".format("XOÁ thư mục {0}".format(kh["goi_done"]) if kh["goi_done"]
                                     else "không có"))
    sv = kh.get("so_video_id")
    ghi("   - sổ máy đăng: {0}".format(
        "CẤT videoId {0} vào id_cu, video_id='', lan_tai_moi=0 (KHÔNG đụng YouTube)".format(
            sv["video_id"]) if sv else "không có videoId"))
    bg = kh.get("run_ban_giao")
    ghi("   - sổ ngày: {0}".format(
        "{0}: da_ban_giao {1} → false, xong_het → false, phục hồi → 0".format(
            rel(kh["so_ngay"]), bool((bg or {}).get("da_ban_giao"))) if kh["so_ngay"] else "không thấy"))
    ghi("   - trang-thai.json: {0} → clip=cho, dung=cho".format(kh.get("trang_thai")))
    ghi("   - xoá {0} clip từ ảnh + tu-anh.json; xoá {1}".format(
        len(kh["xoa_clip"]), ", ".join(os.path.basename(p) for p in kh["xoa_khac"]) or "(không có video)"))
    if kh.get("ho_so"):
        ghi("   - hồ sơ video: video_id → video_id_nhap_cu ({0})".format(rel(kh["ho_so"])))
    for cb in kh["canh_bao"]:
        ghi("   ⚠ " + cb)
    if kh.get("chan"):
        ghi("   ✖ KHÔNG làm thật: " + kh["chan"])


# ── Làm thật ────────────────────────────────────────────────────────────────


def _sao_luu(goc: str, thu_muc_sl: str, cac_tep: Sequence[str]) -> None:
    for p in cac_tep:
        if not p or not os.path.isfile(p):
            continue
        try:
            rel = os.path.relpath(p, goc)
        except ValueError:
            rel = ""
        if not rel or rel.startswith(".."):
            rel = os.path.join("_ngoai", os.path.basename(p))
        dich = os.path.join(thu_muc_sl, rel)
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        shutil.copy2(p, dich)


def _xoa_dong_csv(duong: str, ma_goi: str) -> bool:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            dong = list(csv.reader(io.StringIO(tep.read())))
    except OSError:
        return False
    if not dong or "Mã gói" not in dong[0]:
        return False
    i = dong[0].index("Mã gói")
    con = [dong[0]] + [d for d in dong[1:] if not (len(d) > i and d[i].strip() == ma_goi)]
    if len(con) == len(dong):
        return False
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8-sig", newline="") as tep:
        csv.writer(tep).writerows(con)
    os.replace(tam, duong)
    return True


def _bao_nhap(goc: str, kh: Dict[str, Any]) -> None:
    """Báo chủ: gói đã có bản trên YouTube cần xoá tay — loi-chay-max.md + báo khẩn."""
    sv = kh.get("so_video_id") or {}
    chuyen = ("Gói {0} (kênh {1}) đã lên YouTube thành video {2} ({3}) với cảnh dựng từ ảnh — "
              "tool đã gỡ bàn giao để làm lại bằng clip thật.".format(
                  kh["ma_goi"], kh["kenh"], sv.get("video_id"), sv.get("trang_thai") or "nháp"))
    can = ("Vào Studio kênh {0}, xoá video {1} (bản nháp/riêng tư), rồi mới bật lại tu_dang "
           "trong CHANNEL/{0}/may-ao.json.".format(kh["kenh"], sv.get("video_id")))
    try:
        duong = os.path.join(goc, "workspace", "loi-chay-max.md")
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write("- [{0}] **khan** · kênh {1} — {2} Bạn cần làm gì: {3}\n".format(
                time.strftime("%Y-%m-%d %H:%M"), kh["kenh"], chuyen, can))
    except OSError:
        pass
    try:
        from . import bao_dong  # noqa: PLC0415

        bao_dong.bao_dong_khan("nhap_clip_tu_anh", chuyen, can,
                               "Video làm lại sẽ tải lên cùng tiêu đề — Studio có hai bản, dễ đăng "
                               "nhầm bản dựng từ ảnh.", goc=goc, kenh=kh["kenh"])
    except Exception:  # noqa: BLE001
        pass


def thuc_hien(goc: str, kh: Dict[str, Any], thu_muc_sl: str,
              ghi: Callable[[str], None] = print) -> bool:
    """Làm thật kế hoạch `kh` (đã lập bằng `lap_ke_hoach`). Trả True nếu xong."""
    from . import ke_hoach_dang  # noqa: PLC0415
    from .auto import doc_luot  # noqa: PLC0415

    if kh.get("chan"):
        ghi("  ✖ {0}: bỏ qua — {1}".format(kh["ma_goi"], kh["chan"]))
        return False
    ma_goi, kenh, d = kh["ma_goi"], kh["kenh"], kh["thu_muc_luot"]
    duong_so = os.path.join(goc, "vm", "logs", "so-video-id.json")
    _sao_luu(goc, thu_muc_sl, [kh["ke_hoach_csv"], *kh["cache_csv"], duong_so, kh["so_ngay"],
                               os.path.join(d, "trang-thai.json"),
                               os.path.join(d, "6-clip", "tu-anh.json"), kh.get("ho_so") or ""])
    # 1) Máy đăng không còn gì để tải: dòng kế hoạch, bản đệm, gói DONE.
    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    if "Mã gói" in cot:
        o = cot.index("Mã gói")
        con = [h for h in hang if h[o].strip() != ma_goi]
        if len(con) != len(hang):
            ke_hoach_dang.luu_bang(goc, kenh, con, cot)
    for c in kh["cache_csv"]:
        _xoa_dong_csv(c, ma_goi)
    if kh["goi_done"] and os.path.isdir(kh["goi_done"]):
        shutil.rmtree(kh["goi_done"])
    # 2) Sổ máy đăng: cất videoId nháp (không đụng YouTube).
    sv = kh.get("so_video_id")
    if sv:
        so = _doc_json(duong_so)
        if isinstance(so, dict) and isinstance(so.get(sv["khoa"]), dict):
            muc = dict(so[sv["khoa"]])
            vid = str(muc.get("video_id") or "")
            id_cu = [x for x in (muc.get("id_cu") or []) if x]
            if vid and vid not in id_cu:
                id_cu.append(vid)
            muc.update(video_id="", trang_thai=TRANG_THAI_SO_LAM_LAI, id_cu=id_cu,
                       lan_tai_moi=0, ngay_tai="",
                       lam_lai_clip_that={"luc": time.strftime("%Y-%m-%d %H:%M:%S"),
                                          "video_id_nhap": vid,
                                          "ghi_chu": "bản trên YouTube dựng từ ảnh — chủ kênh "
                                                     "xoá tay; gói làm lại bằng clip thật"})
            so[sv["khoa"]] = muc
            _ghi_json(duong_so, so)
    # 3) Thư mục lượt: chỉ clip từ ảnh + video/tệp suy ra.
    for p in kh["xoa_clip"]:
        try:
            os.remove(p)
        except OSError:
            pass
    try:
        os.remove(os.path.join(d, "6-clip", "tu-anh.json"))
    except OSError:
        pass
    for p in kh["xoa_khac"]:
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except OSError:
                pass
    # 4) Trạng thái lượt: clip + dựng về CHỜ.
    luot = doc_luot(d)
    if luot is not None:
        dat_lai_khau_clip(luot)
    # 5) Sổ ngày tu_chay: chưa bàn giao, chưa xong, phục hồi về 0.
    if kh["so_ngay"]:
        du = _doc_json(kh["so_ngay"])
        if isinstance(du, dict):
            for r in du.get("runs") or []:
                if not isinstance(r, dict) or str(r.get("ma_luot") or "") != kh["ma_luot"] \
                        or r.get("tham_chieu_ma_luot"):
                    continue
                bg_cu = dict(r.get("ban_giao") or {})
                r["ban_giao"] = dict(bg_cu, da_ban_giao=False, ngay_dang="", gio_dang="",
                                     ly_do_trong="", loi="")
                sx = dict(r.get("san_xuat") or {})
                sx.update(xong_het=False, khau_hong=[], loi="")
                r["san_xuat"] = sx
                r.pop("phuc_hoi", None)
                r.pop("bo", None)
                r.pop("ly_do_bo", None)
                r.setdefault("lam_lai_clip_that", []).append({
                    "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "so_canh_tu_anh": len(kh["tu_anh"]),
                    "tong": kh["tong"], "ban_giao_cu": bg_cu,
                    "video_id_nhap": (sv or {}).get("video_id", "")})
            _ghi_json(kh["so_ngay"], du)
    # 6) Hồ sơ video: bỏ videoId nháp (bàn giao lại ghi đè hồ sơ).
    if kh.get("ho_so"):
        hs = _doc_json(kh["ho_so"])
        if isinstance(hs, dict) and hs.get("video_id"):
            hs["video_id_nhap_cu"] = hs.pop("video_id")
            _ghi_json(kh["ho_so"], hs)
    # 7) Ghi chú trong thư mục lượt + báo chủ nếu đã lên YouTube.
    try:
        with open(os.path.join(d, TEP_DAU_LAM_LAI), "a", encoding="utf-8") as tep:
            tep.write("{0}: gỡ bàn giao {1}, xoá {2} clip dựng từ ảnh + video đã dựng — làm lại "
                      "bằng clip thật (luật 07/10/2026).{3} Sao lưu: {4}\n".format(
                          time.strftime("%Y-%m-%d %H:%M"), ma_goi, len(kh["xoa_clip"]),
                          " Bản trên YouTube: {0} — chủ kênh xoá tay.".format(sv["video_id"])
                          if sv else "", thu_muc_sl))
    except OSError:
        pass
    if sv:
        _bao_nhap(goc, kh)
    ghi("  ✔ {0}: đã gỡ bàn giao, xoá {1} clip từ ảnh — tu_chay sẽ làm lại từ khâu clip.".format(
        ma_goi, len(kh["xoa_clip"])))
    return True


# ── Dòng lệnh ───────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m core.lam_lai_clip_that",
                                description="Làm lại bằng clip thật các gói có cảnh dựng từ ảnh.")
    p.add_argument("--kenh", default="")
    p.add_argument("--ma", default="", help="mã lượt (vd 0021)")
    p.add_argument("--tat-ca", action="store_true", help="mọi gói có 6-clip/tu-anh.json")
    p.add_argument("--thu", action="store_true", help="chỉ in kế hoạch, không đổi gì")
    p.add_argument("--goc", default="", help="gốc MyTool (mặc định: thư mục chứa core/)")
    a = p.parse_args(list(argv) if argv is not None else None)
    if not a.tat_ca and not (a.kenh and a.ma):
        p.error("cần --kenh K --ma M, hoặc --tat-ca")
    goc = os.path.abspath(a.goc or _goc_mac_dinh())
    goi = tim_goi(goc, "" if a.tat_ca and not a.kenh else a.kenh, "" if a.tat_ca else a.ma)
    if not goi:
        print("Không có gói nào có cảnh dựng từ ảnh (6-clip/tu-anh.json).")
        return 0
    print("{0} gói có cảnh dựng từ ảnh{1}:".format(len(goi), " — CHẠY THỬ, không đổi gì" if a.thu else ""))
    cac_kh = [lap_ke_hoach(goc, k, m) for k, m in goi]
    for kh in cac_kh:
        in_ke_hoach(kh, goc)
    nhap = [kh for kh in cac_kh if kh.get("so_video_id")]
    if nhap:
        print("\nVIỆC CỦA CHỦ: xoá tay trên Studio " + "; ".join(
            "{0}: video {1}".format(kh["kenh"], kh["so_video_id"]["video_id"]) for kh in nhap)
              + " — rồi mới bật lại tu_dang.")
    if a.thu:
        return 0
    thu_muc_sl = os.path.join(goc, "workspace", "sao-luu", "lam-lai-clip-that",
                              time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(thu_muc_sl, exist_ok=True)
    xong = sum(1 for kh in cac_kh if thuc_hien(goc, kh, thu_muc_sl))
    print("\nXong {0}/{1} gói. Sao lưu: {2}".format(xong, len(cac_kh), thu_muc_sl))
    return 0 if xong == len(cac_kh) else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    sys.exit(main())
