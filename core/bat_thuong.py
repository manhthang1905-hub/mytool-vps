"""PHÁT HIỆN TỤT + TỰ CHẨN ĐOÁN theo kênh (17/10/2026) — thay việc người giám sát kéo `bang-tom-tat.csv` rồi soi bìa.

═══ VÌ SAO ═══ TL1-T7 sụp từ 07/10 (hiển thị/video 5k–35k → < 2k, CTR 5–7% → 1–3%) suốt một tuần không ai biết; người
tìm ra gốc (bìa sai kanji / lặp chữ do máy vẽ ảnh tự viết chữ) bằng tay. Tệp này làm đúng hai việc ấy mỗi ngày.

═══ PHÁT HIỆN (`tin_hieu_kenh` → `phat_hien`) ═══ Mỗi video của kênh (chuỗi chụp đã làm sạch của thước chung
`core.thuoc_thang.chuoi_kenh`): hiển thị ước ở tuổi 72 giờ (nội suy `thuoc_thang.khoang_tai`, bản chụp trong
[43; 115] giờ), và ở bản chụp gần 72 giờ nhất trong [48; 96] giờ: CTR, AVD %, tỉ phần trang chủ (browse), đăng ký /
1.000 lượt xem. KHÔNG phán ở 48 giờ: chỉ video đã qua 96 giờ mới vào cửa sổ phán. Nền = trung vị `SO_NEN` video ĐÃ
PHÁN ngay trước cửa sổ (của chính kênh); cửa sổ = `CUA_SO` video đã phán mới nhất. Tụt khi trung vị cửa sổ < nền ×
ngưỡng (`NGUONG`), và (với hiển thị) ít nhất 2/3 video cửa sổ mang nhãn `truot` / `trung_binh` của thước chung.
`lich_su`: phán lại ở từng video → ngày đầu tiên tụt (TL1: 07/10).

═══ CHẨN ĐOÁN khi tụt (`chan_doan`) ═══
  (1) chữ bìa ĐANG CHẠY (`soat_bia_song`): bìa i.ytimg.com của video cửa sổ + video gần nhất → trùng vân tay một tệp có
      dấu cổng chữ hợp lệ thì đạt (không gọi AI); không thì `cong_chu.kiem_anh` hai lượt đọc mù so chữ bìa mong đợi
      (chữ đã vẽ / THUMB / `chu_bia` hồ sơ);
  (2) lệch kiểu bìa: khoảng cách vân tay bìa gần đây → bìa thắng THẬT của kênh, so với khoảng cách giữa các bìa thắng;
  (3) lệch đề tài / tiêu đề: LLM (đi ví) xét tiêu đề gần đây so với tiêu đề thắng — có / không + lý do;
  (4) lỗi sản xuất: AVD % tụt + `9-chat-luong.json` của lượt (điểm, số lỗi).
TỰ LÀM: bìa sai chữ → hàng `workspace/tu-kiem/viec-sua-bia.json` (skill S06: bìa lô → đóng dấu cổng chữ → xếp đổi bìa
qua `do_bia.xep_doi_bia`); video trượt chưa có A/B → việc máy `studio_test_compare` (D13); mọi bước → sự kiện não. Chỉ
việc người mới lên "Việc của bạn".

    python -X utf8 -m core.bat_thuong kenh --kenh TL1-T7 [--thu] [--goc G]   phát hiện + chẩn đoán + tự làm (--thu: chỉ đọc)
    python -X utf8 -m core.bat_thuong xem [--goc G]                          bảng phát hiện mọi kênh (chỉ đọc, không AI)
    python -X utf8 -m core.bat_thuong sua-bia --kenh K [--thu]               MỘT việc sửa bìa sai chữ (skill S06)
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import statistics
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

TUOI_DO, TUOI_PHAN = 72.0, 96.0
CUA_SO_DO = (48.0, 96.0)
SO_NEN, CUA_SO, NEN_TOI_THIEU = 6, 3, 4
#: Nền hiển thị dưới ngần này = kênh chưa được YouTube phát (việc của `core.kenh_khong_phat`), không phán tụt.
NEN_DUOC_PHAT = 300.0
NGUONG = {"hien_thi": 0.5, "ctr": 0.7, "avd": 0.75, "sub_1k": 0.5}
TUT_BROWSE_DIEM = 15.0
LECH_KIEU = 1.35
SO_BIA_SOAT = 8
THU_MUC = ("workspace", "tu-kiem")
TEN_TIN_HIEU = {"hien_thi": "hiển thị @72h", "ctr": "CTR", "avd": "AVD %", "browse": "tỉ phần trang chủ",
                "sub_1k": "đăng ký / 1k xem"}


def _json(p: str) -> Any:
    try:
        with io.open(p, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(p: str, du: Any) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(p + ".tam", p)


def _so(x: Any) -> Optional[float]:
    try:
        v = float(str(x).replace("%", "").replace(",", ""))
        return v
    except (TypeError, ValueError):
        return None


# ── tín hiệu ───────────────────────────────────────────────────────────────────

def tin_hieu_video(c: Any, thu_muc_video: str) -> Dict[str, Any]:
    """Một `thuoc_thang.Chuoi` → {ma, dang, tuoi_max, hien_thi, ctr, avd, browse, sub_1k}."""
    from . import thuoc_thang as tt  # noqa: PLC0415
    k = tt.khoang_tai(c.diem, TUOI_DO)
    gan = [d for d in c.diem if CUA_SO_DO[0] <= d.tuoi <= CUA_SO_DO[1]]
    d = min(gan, key=lambda x: abs(x.tuoi - TUOI_DO)) if gan else None
    ra: Dict[str, Any] = {"ma": c.ma, "dang": c.dang, "tuoi_max": max((x.tuoi for x in c.diem), default=0.0),
                          "hien_thi": round(k[1], 1) if k else None, "ctr": None, "avd": None, "browse": None,
                          "sub_1k": None, "tuoi_do": d.tuoi if d else None}
    if d is not None:
        tq = _json(os.path.join(thu_muc_video, d.thu_muc, "tong-quan.json")) or {}
        ra["ctr"] = _so(tq.get("ctr")) if tq.get("ctr") is not None else d.ctr
        ra["avd"] = _so(tq.get("avd_pct"))
        ra["browse"] = _so((tq.get("traffic") or {}).get("browse"))
        xem, sub = _so(tq.get("views")), _so(tq.get("subs"))
        ra["sub_1k"] = round(sub * 1000.0 / xem, 2) if xem and xem >= 50 and sub is not None else None
    return ra


def tin_hieu_kenh(goc: str, kenh: str) -> List[Dict[str, Any]]:
    """Mọi video của kênh (thước chung) có giờ đăng, cũ → mới, kèm nhãn thước chung."""
    from . import thuoc_thang as tt  # noqa: PLC0415
    from .kenh import duong_kenh  # noqa: PLC0415
    chuoi = tt.chuoi_kenh(goc, kenh)
    nhan = tt.danh_gia(chuoi)
    thu_muc = os.path.join(duong_kenh(goc, kenh), "chi-so")
    ra = []
    for ma, c in chuoi.items():
        if c.dang is None or not c.diem:
            continue
        x = tin_hieu_video(c, os.path.join(thu_muc, ma))
        x["nhan"] = nhan[ma].nhan if ma in nhan else ""
        x["ngay"] = _dt.datetime.utcfromtimestamp(c.dang).date().isoformat()   # = "Ngày đăng" của Studio
        ra.append(x)
    return sorted(ra, key=lambda x: x["dang"])


def _tv(ds: Sequence[Optional[float]]) -> Optional[float]:
    v = [x for x in ds if x is not None]
    return statistics.median(v) if v else None


def phat_hien(ds: Sequence[Dict[str, Any]], *, bay: Optional[float] = None) -> Dict[str, Any]:
    """THUẦN. → {tut: [tín hiệu] (rỗng nếu không tụt CHÍNH), canh_bao: [tín hiệu phụ tụt một mình], chi_tiet,
    cua_so: [mã], ngay, du, ly_do}. Tụt CHÍNH = hiển thị @72h (≥ 2/3 video cửa sổ trượt/trung bình theo thước chung) hoặc
    CTR + tỉ phần trang chủ cùng tụt. Tín hiệu phụ (AVD, đăng ký/1k) tụt một mình chỉ là cảnh báo."""
    import time as _t  # noqa: PLC0415
    bay = _t.time() if bay is None else bay
    phan = [x for x in ds if x.get("dang") and (bay - x["dang"]) / 3600.0 >= TUOI_PHAN]
    gan, nen = phan[-CUA_SO:], phan[-CUA_SO - SO_NEN:-CUA_SO]
    ra: Dict[str, Any] = {"tut": [], "canh_bao": [], "chi_tiet": {}, "cua_so": [x["ma"] for x in gan],
                          "ngay": gan[-1]["ngay"] if gan else "", "tu_ngay": gan[0]["ngay"] if gan else "",
                          "du": False, "ly_do": ""}
    if len(gan) < CUA_SO or len([x for x in nen if x.get("hien_thi") is not None]) < NEN_TOI_THIEU:
        ra["ly_do"] = "chưa đủ video đã phán ({0} gần + {1} nền)".format(len(gan), len(nen))
        return ra
    nen_ht = _tv([x.get("hien_thi") for x in nen])
    if nen_ht is None or nen_ht < NEN_DUOC_PHAT:
        ra["ly_do"] = "kênh chưa được phát (nền {0:.0f} hiển thị/video) — kenh_khong_phat lo".format(nen_ht or 0)
        return ra
    ra["du"] = True
    co = []
    for k in ("hien_thi", "ctr", "avd", "sub_1k", "browse"):
        a, b = _tv([x.get(k) for x in nen]), _tv([x.get(k) for x in gan])
        if a is None or b is None:
            continue
        ti = b / a if a else None
        ra["chi_tiet"][k] = {"nen": round(a, 2), "gan": round(b, 2), "ti_le": round(ti, 2) if ti is not None else None}
        if k == "browse":
            if a - b >= TUT_BROWSE_DIEM:
                co.append(k)
        elif k == "sub_1k":
            if a >= 1.0 and ti is not None and ti < NGUONG[k]:
                co.append(k)
        elif ti is not None and ti < NGUONG[k]:
            if k == "hien_thi" and sum(1 for x in gan if x.get("nhan") in ("truot", "trung_binh")) < 2:
                continue
            co.append(k)
    chinh = "hien_thi" in co or ("ctr" in co and "browse" in co)
    ra["tut" if chinh else "canh_bao"] = co
    return ra


def lich_su(ds: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Phán lại tại từng video (như thể hôm ấy video đó vừa qua 96 giờ) → [{ngay, tu_ngay, ma, tut}] (dòng tụt CHÍNH)."""
    ra = []
    for i in range(len(ds)):
        con = list(ds[:i + 1])
        if not con[-1].get("dang"):
            continue
        p = phat_hien(con, bay=con[-1]["dang"] + TUOI_PHAN * 3600 + 1)
        if p["tut"]:
            ra.append({"ngay": con[-1]["ngay"], "tu_ngay": p["tu_ngay"], "ma": con[-1]["ma"], "tut": p["tut"]})
    return ra


def bat_dau_tut(ls: Sequence[Dict[str, Any]], ds: Sequence[Dict[str, Any]]) -> str:
    """Ngày bắt đầu đợt tụt ĐANG diễn ra: lần phán tụt đầu tiên của chuỗi tụt liền (≥ 2 lần phán) kéo tới cuối lịch sử
    → ngày đăng video đầu cửa sổ ấy. "" nếu không có."""
    ma = [x["ma"] for x in ds]
    if not ls:
        return ""
    chuoi = [ls[-1]]
    for x in reversed(ls[:-1]):
        if ma.index(chuoi[0]["ma"]) - ma.index(x["ma"]) <= 2:
            chuoi.insert(0, x)
        else:
            break
    if len(chuoi) < 2:
        return ""
    co_ht = [x for x in chuoi if "hien_thi" in x["tut"]]          # mốc là lần phán đầu tiên HIỂN THỊ đã tụt
    return (co_ht or chuoi)[0]["tu_ngay"]


# ── chẩn đoán ──────────────────────────────────────────────────────────────────

def _thu_muc(goc: str) -> str:
    return os.path.join(goc, *THU_MUC)


def _thu_muc_bia(goc: str, kenh: str, luu: str = "") -> str:
    return os.path.join(luu, kenh) if luu else os.path.join(_thu_muc(goc), "bia-song", kenh)


def bia_song(goc: str, kenh: str, vid: str, tai: Optional[Callable[[str], Tuple[int, bytes]]] = None,
             luu: str = "") -> str:
    """Tải bìa đang chạy (maxres → hq) vào `workspace/tu-kiem/bia-song/<kênh>/<vid>.jpg` (`luu`: thư mục khác — chạy
    thử không ghi vào gốc); "" nếu không tải được."""
    from . import tu_kiem  # noqa: PLC0415
    tai = tai or tu_kiem.tai_that
    for ten in ("maxresdefault", "hqdefault"):
        ma, du = tai("https://i.ytimg.com/vi/{0}/{1}.jpg".format(vid, ten))
        if ma == 200 and du:
            p = os.path.join(_thu_muc_bia(goc, kenh, luu), vid + ".jpg")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as tep:
                tep.write(du)
            return p
    return ""


def _tep_co_dau(goc: str, kenh: str, vid: str, ma: str) -> List[str]:
    """Tệp bìa CÓ DẤU cổng chữ có thể là bìa đang chạy: tệp hàng sửa của video, bìa CHON-* của lượt."""
    from . import cong_chu  # noqa: PLC0415
    ds = []
    for v in (_json(os.path.join(goc, "vm", "logs", "hang-sua.json")) or {}).get("viec") or []:
        if isinstance(v, dict) and v.get("video_id") == vid and v.get("anh"):
            ds.append(str(v["anh"]))
    luot = ma[len(kenh) + 1:] if ma.startswith(kenh + "-") else ""
    if luot:
        tm = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "7-thumbnail")
        try:
            ds += [os.path.join(tm, t) for t in os.listdir(tm) if t.upper().startswith("CHON-")]
        except OSError:
            pass
    return [p for p in dict.fromkeys(ds) if os.path.isfile(p) and not cong_chu.kiem_dau(p)]


def soat_bia_song(goc: str, kenh: str, vids: Sequence[str], goi: Optional[Callable[..., str]], *,
                  tai: Optional[Callable[[str], Tuple[int, bytes]]] = None, luu: str = "") -> List[Dict[str, Any]]:
    """Chữ trên bìa ĐANG CHẠY: {vid, ma, ok (True/False/None), cach, ly_do, chu}."""
    from . import cong_chu, studio_may, tu_kiem  # noqa: PLC0415
    ra = []
    for vid in vids:
        ma = studio_may.ma_goi_cua_video(goc, kenh, vid)
        tep = bia_song(goc, kenh, vid, tai, luu)
        x: Dict[str, Any] = {"vid": vid, "ma": ma, "ok": None, "cach": "", "ly_do": "", "chu": ""}
        if not tep:
            ra.append(dict(x, ly_do="không tải được bìa đang chạy"))
            continue
        vt = tu_kiem.van_tay(tep)
        khop = [p for p in _tep_co_dau(goc, kenh, vid, ma)
                if (lambda d: d is not None and d <= tu_kiem.LECH_DAT)(tu_kiem.lech(vt, tu_kiem.van_tay(p)))]
        if khop:
            ra.append(dict(x, ok=True, cach="dau", ly_do="trùng tệp có dấu cổng chữ " + os.path.basename(khop[0])))
            continue
        try:
            chu = cong_chu._chu_mong_goi(goc, kenh, ma).get("chu", "") if ma else ""  # noqa: SLF001
        except Exception:  # noqa: BLE001
            chu = ""
        if not chu:
            ra.append(dict(x, cach="khong_chu", ly_do="không biết chữ bìa mong đợi (gói ngoài tool?)"))
            continue
        if goi is None:
            ra.append(dict(x, chu=chu, cach="chua_doc", ly_do="chạy thử: chưa đọc chữ (cần AI)"))
            continue
        kq = cong_chu.kiem_anh(goi, tep, chu, khoa="tu-kiem-bia-song:" + vid)
        ra.append(dict(x, ok=kq.get("ok"), cach="doc2", chu=chu, ly_do="; ".join(kq.get("ly_do") or [])[:300]))
    return ra


def lech_kieu(goc: str, kenh: str, vids_gan: Sequence[str], vids_thang: Sequence[str], *,
              tai: Optional[Callable[[str], Tuple[int, bytes]]] = None, luu: str = "") -> Dict[str, Any]:
    """Khoảng cách vân tay (dHash) bìa gần đây → bìa thắng gần nhất, so với giữa các bìa thắng (bỏ-một-ra)."""
    from . import tu_kiem  # noqa: PLC0415

    def vt(vid):
        p = os.path.join(_thu_muc_bia(goc, kenh, luu), vid + ".jpg")
        return tu_kiem.van_tay(p if os.path.isfile(p) else bia_song(goc, kenh, vid, tai, luu) or "")
    thang = [v for v in (vt(x) for x in vids_thang) if v]
    gan = [v for v in (vt(x) for x in vids_gan) if v]
    if len(thang) < 2 or not gan:
        return {"du": False, "ly_do": "thiếu bìa thắng thật ({0}) / bìa gần ({1})".format(len(thang), len(gan))}
    noi = statistics.mean(min(tu_kiem.lech(a, b) for j, b in enumerate(thang) if j != i) for i, a in enumerate(thang))
    ngoai = statistics.mean(min(tu_kiem.lech(a, b) for b in thang) for a in gan)
    ti = ngoai / noi if noi else None
    return {"du": True, "noi": round(noi, 1), "gan": round(ngoai, 1), "ti_le": round(ti, 2) if ti else None,
            "lech": bool(ti and ti >= LECH_KIEU)}


LOI_NHAC_DE_TAI = """You audit a Japanese psychology YouTube channel. WINNING titles (the channel's best videos):
{thang}
RECENT titles (the videos whose reach just dropped):
{gan}
Did the recent videos drift away from the topic family / promise / title style that wins on this channel? Judge by
MEANING, not by shared words. Return JSON only: {{"lech": true|false, "ly_do": "<one short sentence in Vietnamese>"}}"""


def lech_de_tai(goi: Optional[Callable[..., str]], tieu_de_thang: Sequence[str], tieu_de_gan: Sequence[str]
                ) -> Dict[str, Any]:
    if goi is None or not tieu_de_thang or not tieu_de_gan:
        return {"du": False, "ly_do": "không có AI / thiếu tiêu đề"}
    from .goi_van_ban import loc_json  # noqa: PLC0415
    try:
        du = loc_json(goi(LOI_NHAC_DE_TAI.format(thang="\n".join("- " + t for t in tieu_de_thang[:8]),
                                                   gan="\n".join("- " + t for t in tieu_de_gan[:6])),
                          mo_hinh="claude-opus-5", khoa="tu-kiem-de-tai:" + str(abs(hash(tuple(tieu_de_gan))))[:10],
                          toi_da_token=400))
    except Exception as loi:  # noqa: BLE001
        return {"du": False, "ly_do": "AI lỗi: {0}".format(str(loi)[:100])}
    if not isinstance(du, dict) or "lech" not in du:
        return {"du": False, "ly_do": "AI trả rác"}
    return {"du": True, "lech": bool(du.get("lech")), "ly_do": str(du.get("ly_do") or "")[:240]}


def loi_san_xuat(goc: str, kenh: str, mas: Sequence[str], p: Dict[str, Any]) -> Dict[str, Any]:
    qc = []
    for ma in mas:
        luot = ma[len(kenh) + 1:] if ma.startswith(kenh + "-") else ""
        d = _json(os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "9-chat-luong.json")) if luot else None
        if isinstance(d, dict):
            qc.append({"ma": ma, "diem": d.get("diem"), "loi": d.get("loi"), "dat": d.get("dat")})
    kem = [x for x in qc if x.get("dat") is False or (x.get("diem") is not None and float(x["diem"]) < 80)]
    return {"avd_tut": "avd" in p.get("tut", []), "qc": qc, "qc_kem": kem,
            "co_loi": "avd" in p.get("tut", []) or bool(kem)}


def _tieu_de(goc: str, kenh: str, vid: str) -> str:
    for tq in sorted((os.path.join(goc, "CHANNEL", kenh, "chi-so", vid, d, "tong-quan.json")
                      for d in (os.listdir(os.path.join(goc, "CHANNEL", kenh, "chi-so", vid))
                                if os.path.isdir(os.path.join(goc, "CHANNEL", kenh, "chi-so", vid)) else [])), reverse=True):
        t = (_json(tq) or {}).get("tieu_de")
        if t:
            return str(t)
    return ""


def _goi_that(goc: str) -> Optional[Callable[..., str]]:
    """Hàm chữ + ảnh qua phễu `goi_van_ban` (ví ShopAPI khi Cài đặt chọn ví) — không có đường riêng Claude Max."""
    try:
        from .bia_lo import _goi_that as g  # noqa: PLC0415
        return g(goc, lambda s: None)
    except Exception:  # noqa: BLE001
        return None


def chan_doan(goc: str, kenh: str, ds: Sequence[Dict[str, Any]], p: Dict[str, Any], *,
              goi: Optional[Callable[..., str]] = None, tai: Optional[Callable[[str], Tuple[int, bytes]]] = None,
              luu: str = "") -> Dict[str, Any]:
    gan = [x["ma"] for x in ds][-SO_BIA_SOAT:]
    thang = [x["ma"] for x in sorted((x for x in ds if x.get("nhan") == "thang"), key=lambda x: -(x.get("hien_thi") or 0))][:6]
    bia = soat_bia_song(goc, kenh, gan, goi, tai=tai, luu=luu)
    from . import studio_may  # noqa: PLC0415
    mas = [studio_may.ma_goi_cua_video(goc, kenh, v) for v in p.get("cua_so") or []]
    return {"bia_sai_chu": [b for b in bia if b["ok"] is False], "bia": bia,
            "kieu": lech_kieu(goc, kenh, gan[-CUA_SO:], thang, tai=tai, luu=luu),
            "de_tai": lech_de_tai(goi, [_tieu_de(goc, kenh, v) for v in thang], [_tieu_de(goc, kenh, v) for v in gan[-CUA_SO:]]),
            "san_xuat": loi_san_xuat(goc, kenh, [m for m in mas if m], p)}


# ── tự làm ─────────────────────────────────────────────────────────────────────

def duong_hang_sua_bia(goc: str) -> str:
    return os.path.join(_thu_muc(goc), "viec-sua-bia.json")


def xep_sua_bia(goc: str, kenh: str, bia_sai: Sequence[Dict[str, Any]], *, thu: bool = False) -> List[Dict[str, Any]]:
    du = _json(duong_hang_sua_bia(goc)) or {"viec": []}
    co = {(v.get("kenh"), v.get("vid")) for v in du["viec"] if v.get("trang_thai") in ("cho", "dang", "xong")}
    moi = [{"kenh": kenh, "vid": b["vid"], "ma": b["ma"], "chu": b.get("chu", ""), "ly_do": b.get("ly_do", ""),
            "trang_thai": "cho", "them_luc": _dt.datetime.now().isoformat(timespec="seconds"), "lan": 0}
           for b in bia_sai if b.get("ma") and (kenh, b["vid"]) not in co]
    if moi and not thu:
        du["viec"] = du["viec"][-200:] + moi
        _ghi_json(duong_hang_sua_bia(goc), du)
    return moi


def xep_ab(goc: str, kenh: str, ds: Sequence[Dict[str, Any]], p: Dict[str, Any], *, thu: bool = False) -> List[str]:
    """Video trượt trong cửa sổ chưa có A/B → việc máy `studio_test_compare` (D13 làm, chỉ bìa có dấu cổng chữ)."""
    from . import ab_tieu_de as ab  # noqa: PLC0415
    yeu = [x["ma"] for x in ds if x["ma"] in (p.get("cua_so") or []) and x.get("nhan") in ("truot", "trung_binh")]
    yeu = [v for v in yeu if not ab.chan_doi_truc_tiep(goc, kenh, v)]
    if yeu and not thu:
        from .giam_doc import _tu_dong as td  # noqa: PLC0415
        td.ghi_viec_may_kieu(goc, td.LOAI_TEST_COMPARE, kenh, video_ids=yeu, nguon="tu_kiem:bat_thuong",
                             chu="tụt {0} — thử bìa cho video yếu".format(", ".join(p.get("tut") or [])))
    return yeu


def _nao(goc: str, kenh: str, bp: str, loai: str, noi_dung: str, khoa: str, so: Optional[Dict[str, Any]] = None) -> None:
    try:
        from . import nao_bo_phan  # noqa: PLC0415
        nao_bo_phan.ghi(goc, bp, loai, kenh=kenh, noi_dung=noi_dung, so=so or {}, nguon="tu_kiem", khoa=khoa)
    except Exception:  # noqa: BLE001
        pass


def chay_kenh(goc: str, kenh: str, *, thu: bool = False, goi: Optional[Callable[..., str]] = None,
              tai: Optional[Callable[[str], Tuple[int, bytes]]] = None) -> Dict[str, Any]:
    """Phát hiện → (tụt) chẩn đoán → tự làm → báo cáo `workspace/tu-kiem/bat-thuong/<kênh>.json`."""
    ds = tin_hieu_kenh(goc, kenh)
    p = phat_hien(ds)
    ls = lich_su(ds)
    ra: Dict[str, Any] = {"kenh": kenh, "luc": _dt.datetime.now().isoformat(timespec="seconds"), "phat_hien": p,
                          "lich_su": ls, "tut_tu": bat_dau_tut(ls, ds), "chan_doan": {}, "lam": {}}
    if p["tut"]:
        if goi is None and not thu:
            goi = _goi_that(goc)
        import tempfile  # noqa: PLC0415
        cd = chan_doan(goc, kenh, ds, p, goi=goi, tai=tai, luu=tempfile.mkdtemp(prefix="tu-kiem-thu-") if thu else "")
        ra["chan_doan"] = cd
        ra["lam"]["sua_bia"] = xep_sua_bia(goc, kenh, cd["bia_sai_chu"], thu=thu)
        ra["lam"]["ab"] = xep_ab(goc, kenh, ds, p, thu=thu)
        gay = (["bìa sai chữ: " + ", ".join(b["ma"] or b["vid"] for b in cd["bia_sai_chu"])] if cd["bia_sai_chu"] else []) + \
              (["kiểu bìa lệch khỏi bìa thắng (×{0})".format(cd["kieu"].get("ti_le"))] if cd["kieu"].get("lech") else []) + \
              (["lệch đề tài: " + cd["de_tai"].get("ly_do", "")] if cd["de_tai"].get("lech") else []) + \
              (["lỗi sản xuất (AVD / QC)"] if cd["san_xuat"].get("co_loi") else [])
        ra["gay"] = gay or ["chưa thấy gốc trong 4 phép chẩn đoán"]
        if not thu:
            _nao(goc, kenh, "chi-so-studio", "do", "tụt {0} so với nền của kênh (cửa sổ {1}); chẩn đoán: {2}".format(
                ", ".join(TEN_TIN_HIEU[k] for k in p["tut"]), ", ".join(p["cua_so"]), "; ".join(ra["gay"])),
                "tu-kiem:tut:{0}:{1}".format(kenh, p["ngay"]), {"chi_tiet": p["chi_tiet"]})
            for b in cd["bia_sai_chu"]:
                _nao(goc, kenh, "bia", "loi", "bìa ĐANG CHẠY sai chữ {0}: {1}".format(b["ma"] or b["vid"], b["ly_do"]),
                     "tu-kiem:bia-sai:{0}".format(b["vid"]))
    if not thu:
        _ghi_json(os.path.join(_thu_muc(goc), "bat-thuong", kenh + ".json"), ra)
    return ra


# ── S06: sửa MỘT bìa sai chữ đang chạy ─────────────────────────────────────────

def viec_sua_bia(goc: str, kenh: str) -> List[Dict[str, Any]]:
    return [v for v in (_json(duong_hang_sua_bia(goc)) or {}).get("viec") or []
            if v.get("kenh") == kenh and v.get("trang_thai") == "cho" and int(v.get("lan") or 0) < 3]


def _cap_nhat_viec(goc: str, v: Dict[str, Any], **truong: Any) -> None:
    du = _json(duong_hang_sua_bia(goc)) or {"viec": []}
    for x in du["viec"]:
        if x.get("kenh") == v["kenh"] and x.get("vid") == v["vid"] and x.get("them_luc") == v.get("them_luc"):
            x.update(truong)
    _ghi_json(duong_hang_sua_bia(goc), du)


def sua_bia(goc: str, kenh: str, *, vid: str = "", goi: Optional[Callable[..., str]] = None, chay_lo: Optional[Callable[..., Dict[str, Any]]] = None,
            xep: Optional[Callable[..., Any]] = None, log: Callable[[str], None] = print) -> Dict[str, Any]:
    """Chữ bìa soát lại (`cong_chu.chot_chu`) → bìa lô (`core.bia_lo`, chữ vẽ bằng mã) → đọc lại hai lượt + dấu
    (`cong_chu.xac_minh`) → `do_bia.xep_doi_bia` (máy DOM đổi bìa; tự kiểm đọc lại i.ytimg.com). AI / vẽ hỏng → giữ việc,
    lần sau thử lại (tối đa 3 lần)."""
    from . import cong_chu  # noqa: PLC0415
    ds = [v for v in viec_sua_bia(goc, kenh) if not vid or v.get("vid") == vid]
    if not ds:
        return {"ket": "khong_co"}
    v = ds[0]
    _cap_nhat_viec(goc, v, trang_thai="dang", lan=int(v.get("lan") or 0) + 1)
    goi = goi or _goi_that(goc)
    try:
        nc = cong_chu._ngu_canh(goc, kenh, v["ma"])  # noqa: SLF001
        s = cong_chu.chot_chu(goi, v.get("chu") or "", tieu_de=nc["tieu_de"], ngu_canh=nc["ngu_canh"],
                              khoa="tu-kiem-sua-bia:{0}:soat".format(v["ma"]))
        if s.get("ok") is not True:
            raise RuntimeError("chữ bìa chưa qua soát: " + str(s.get("ly_do") or ""))
        chu = str(s["chu"])
        luot = os.path.join(goc, "PROJECTS", "AUTO", kenh, v["ma"][len(kenh) + 1:])
        ra_tm = os.path.join(goc, "workspace", "bia-sua-chu", v["ma"])
        if chay_lo is None:
            from . import bia_lo  # noqa: PLC0415

            def chay_lo(**kw):
                mau = bia_lo.mau_cua_kenh(goc, kenh, (), ho_so=bia_lo.ho_so_kieu(goc, kenh, goi=goi))
                nv = os.path.join(goc, "CHANNEL", kenh, "nv", "nv1.png")
                return bia_lo.chay(goc, kenh, thu_muc_luot=luot, ra=ra_tm, chu=chu, goi=goi, mau=mau,
                                   ve=bia_lo._ve_that(goc, mau + ([nv] if os.path.isfile(nv) else [])), log=log)  # noqa: SLF001
        kq = chay_lo(chu=chu)
        for t in kq.get("top") or []:
            x = cong_chu.xac_minh(goi, t["tep"], chu, goc=goc, kenh=kenh, ma_goi=v["ma"], khoa="tu-kiem-sua-bia:" + v["ma"])
            if x.get("ok") is True:
                if xep is None:
                    from . import do_bia  # noqa: PLC0415
                    xep = do_bia.xep_doi_bia
                xep(goc, kenh, v["ma"], t["tep"], ly_do="tự kiểm: bìa đang chạy sai chữ ({0}) → bìa lô chữ vẽ bằng mã".format(
                    v.get("ly_do", "")[:120]))
                _cap_nhat_viec(goc, v, trang_thai="xong", anh=t["tep"])
                _nao(goc, kenh, "bia", "sua", "tự kiểm xếp đổi bìa sai chữ {0} → {1}".format(v["ma"], os.path.basename(t["tep"])),
                     "tu-kiem:sua-bia:{0}:{1}".format(v["vid"], os.path.basename(t["tep"])))
                return {"ket": "xong", "ma": v["ma"], "anh": t["tep"]}
        raise RuntimeError("không tấm nào của bìa lô qua đọc lại hai lượt")
    except Exception as loi:  # noqa: BLE001
        _cap_nhat_viec(goc, v, trang_thai="cho", ly_do_cuoi=str(loi)[:300])
        return {"ket": "hong", "ma": v["ma"], "ly_do": str(loi)[:300]}


# ── G1 (20/10/2026): THỊ PHẦN NGÁCH ĐỨNG YÊN ───────────────────────────────────────────────────────────────────
#: Thị phần cả nhóm (ảnh chụp chiến trường hằng ngày `workspace/chien-truong/lich-su.jsonl`) sau `NGAY_DUNG_YEN` ngày
#: mà tăng < `TANG_DUNG_YEN` (tương đối) — kể cả giảm — là «đứng yên»: một tín hiệu (bỏ trùng theo tuần ISO) vào bộ
#: não, bộ phận chọn content (chiến lược đề tài), và một dòng báo cáo ngày. Không báo động / Telegram (chủ đã từ chối).
NGAY_DUNG_YEN = 7
TANG_DUNG_YEN = 0.10


def thi_phan_dung_yen(lich_su: Sequence[Dict[str, Any]], so_ngay: int = NGAY_DUNG_YEN,
                      tang_min: float = TANG_DUNG_YEN) -> Optional[Dict[str, Any]]:
    """Hàm thuần trên ảnh chụp (cũ → mới). Cần ảnh mới nhất và ảnh cách ≥ `so_ngay` ngày; không đủ → None."""
    ds = [x for x in lich_su if isinstance(x, dict) and x.get("ngay")]
    if len(ds) < 2:
        return None
    moi = ds[-1]
    try:
        moc = (_dt.date.fromisoformat(str(moi["ngay"])[:10]) - _dt.timedelta(days=so_ngay)).isoformat()
    except ValueError:
        return None
    cu = [x for x in ds[:-1] if str(x["ngay"]) <= moc]
    if not cu:
        return None
    cu = cu[-1]
    tp = lambda x: float((x.get("tong") or {}).get("thi_phan") or 0)  # noqa: E731
    a, b = tp(cu), tp(moi)
    cua_so = [tp(x) for x in ds if str(x["ngay"]) >= str(cu["ngay"])]
    doi = (b - a) / a if a > 0 else (1.0 if b > 0 else 0.0)
    kenh = {}
    for m, q in (moi.get("quan") or {}).items():
        v0 = float(((cu.get("quan") or {}).get(m) or {}).get("view_28") or 0)
        kenh[m] = {"view_28": float((q or {}).get("view_28") or 0), "view_28_cu": v0}
    return {"dung_yen": doi < tang_min, "ngay_cu": cu["ngay"], "ngay_moi": moi["ngay"], "thi_phan_cu": a, "thi_phan_moi": b,
            "doi_pct": round(100.0 * doi, 1), "thap": min(cua_so), "cao": max(cua_so), "kenh": kenh,
            "nguong_top": (moi.get("bang_diem") or {}).get("nguong_top"), "hang": (moi.get("bang_diem") or {}).get("hang")}


def _tuan_iso(ngay: str) -> str:
    try:
        n, t, _ = _dt.date.fromisoformat(str(ngay)[:10]).isocalendar()
        return "{0}-W{1:02d}".format(n, t)
    except ValueError:
        return str(ngay)[:10]


def bao_thi_phan(goc: str, *, thu: bool = False, lich_su: Optional[Sequence[Dict[str, Any]]] = None) -> List[str]:
    """Dòng báo cáo ngày (bảng điểm thắng + thị phần đứng yên); đứng yên thì ghi MỘT sự kiện não/tuần (khoá
    `thi-phan-dung-yen:<tuần ISO>`). Không bao giờ ném lỗi."""
    try:
        if lich_su is None:
            from . import chien_truong_lich_su  # noqa: PLC0415
            lich_su = chien_truong_lich_su.doc_lich_su(goc, 30)
        r = thi_phan_dung_yen(lich_su or [])
    except Exception as loi:  # noqa: BLE001
        return ["- Bảng điểm thắng: lỗi đọc lịch sử chiến trường ({0})".format(str(loi)[:80])]
    if r is None:
        return ["- Bảng điểm thắng: chưa đủ {0} ngày ảnh chụp chiến trường".format(NGAY_DUNG_YEN)]
    hang = r.get("hang") or {}
    ra = []
    if hang:
        ra.append("- Hạng ngách (ngưỡng top 10 ≈ {0}/tháng): {1}".format(
            "{0:,.0f}".format(float(r["nguong_top"])) if r.get("nguong_top") else "?",
            ", ".join("{0} #{1}".format(m, h) for m, h in sorted(hang.items(), key=lambda x: (x[1] or 1e9)) if h)))
    ra.append("- Thị phần nhóm {0}% → {1}% ({2:+.1f}% sau {3}→{4}){5}".format(
        r["thi_phan_cu"], r["thi_phan_moi"], r["doi_pct"], r["ngay_cu"], r["ngay_moi"],
        " — ĐỨNG YÊN: đổi đề tài/đóng gói, không chờ thêm" if r["dung_yen"] else ""))
    if r["dung_yen"] and not thu:
        _nao(goc, "", "chon-content", "do",
             "thị phần ngách đứng yên {0} ngày: {1}% → {2}% ({3:+.1f}%, dao động {4}–{5}%); ngưỡng top 10 ≈ {6}/tháng — "
             "chiến lược đề tài/tiêu đề hiện tại không kéo được thị phần".format(
                 NGAY_DUNG_YEN, r["thi_phan_cu"], r["thi_phan_moi"], r["doi_pct"], r["thap"], r["cao"],
                 r.get("nguong_top")),
             "thi-phan-dung-yen:" + _tuan_iso(r["ngay_moi"]),
             so={k: r[k] for k in ("ngay_cu", "ngay_moi", "thi_phan_cu", "thi_phan_moi", "doi_pct", "nguong_top", "hang")})
    return ra


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.bat_thuong")
    p.add_argument("lenh", choices=("kenh", "xem", "sua-bia"))
    p.add_argument("--kenh", default="")
    p.add_argument("--vid", default="")
    p.add_argument("--thu", action="store_true")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args(argv)
    goc = os.path.abspath(a.goc)
    if a.lenh == "sua-bia":
        if a.thu:
            print(json.dumps(viec_sua_bia(goc, a.kenh), ensure_ascii=False, indent=1))
            return 0
        kq = sua_bia(goc, a.kenh, vid=a.vid)
        print(json.dumps(kq, ensure_ascii=False))
        return 0 if kq["ket"] in ("xong", "khong_co") else 2
    if a.lenh == "kenh":
        kq = chay_kenh(goc, a.kenh, thu=a.thu)
        print(json.dumps({k: kq[k] for k in ("kenh", "phat_hien", "tut_tu", "lam") if k in kq}, ensure_ascii=False, indent=1))
        if kq.get("chan_doan"):
            cd = kq["chan_doan"]
            print("chẩn đoán:", "; ".join(kq.get("gay") or []))
            for b in cd["bia"]:
                print("  bìa {0} {1}: {2} ({3}) {4}".format(b["vid"], b["ma"], b["ok"], b["cach"], b["ly_do"][:120]))
            print("  kiểu:", cd["kieu"], "\n  đề tài:", cd["de_tai"], "\n  sản xuất:", {k: cd["san_xuat"][k] for k in ("avd_tut", "qc_kem")})
        return 0
    try:
        from .ky_nang import _cac_kenh  # noqa: PLC0415
        cac = [a.kenh] if a.kenh else _cac_kenh(goc)
    except Exception:  # noqa: BLE001
        cac = [a.kenh]
    for k in cac:
        ds = tin_hieu_kenh(goc, k)
        ph = phat_hien(ds)
        ls = lich_su(ds)
        print("{0:<10} tụt: {1:<28} cửa sổ {2}→{3} · đợt tụt bắt đầu {4}{5}".format(
            k, ", ".join(ph["tut"]) or ("—" if ph["du"] else ph["ly_do"]), ph["tu_ngay"], ph["ngay"],
            bat_dau_tut(ls, ds) or "—", " · cảnh báo: " + ", ".join(ph["canh_bao"]) if ph["canh_bao"] else ""))
        for t, ct in ph["chi_tiet"].items():
            print("    {0:<18} nền {1:>9} → gần {2:>9}  (×{3})".format(TEN_TIN_HIEU[t], ct["nen"], ct["gan"], ct["ti_le"]))
        if ls:
            print("    lịch sử tụt: " + " · ".join("{0}→{1} {2}".format(x["tu_ngay"][5:], x["ngay"][5:], "/".join(x["tut"]))
                                              for x in ls[-8:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
