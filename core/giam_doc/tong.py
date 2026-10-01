"""Tổng giám đốc — cấp VPS, bản gọn (`workspace/THIET-KE-CONG-TY.md`, BẢN GỌN mục 3).

Mỗi thứ Hai, sau lượt tuần của mọi giám đốc kênh: bảng công ty (một dòng mỗi KÊNH YOUTUBE — cặp `-v2` gộp
làm một) → xếp loại lên / chững / tụt → luật ±1 khe/kênh/tuần trong trần máy → MỘT lượt LLM chọn trong thực
đơn → (tu_ap) đổi khe qua `trung_tam.ghi_cai_kenh` → báo cáo `workspace/tong-giam-doc/BAO-CAO-CONG-TY.md`.

    bang_cong_ty(goc) · xep_loai(dong) · chia_khe(bang, tran) · hop_tuan(goc, goi_chat) · bao_cao(goc, kq)
    den_han(goc) · cau_the(goc) · de_xuat_kenh_moi(goc, cs)

Khoá `workspace/cai-dat.json: tong_giam_doc: tat | goi_y | tu_ap` (mặc định `tat`). Gợi ý = chỉ ghi báo cáo.
Chỉ đổi `nhip_dang`, `video_toi_da_ngay`, `ngan_sach_ngay` (chỉ nâng) của kênh nhiều khe; nghỉ 14 ngày sau mỗi
lần đổi; chủ sửa tay thì không đè; quay lui khi hiển thị 48h trung vị tụt ≥ 30% hoặc máy quá tải.
"""

from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import math
import os
import re
import statistics
from typing import Any, Callable, Dict, List, Optional, Sequence

THU_MUC = os.path.join("workspace", "tong-giam-doc")
TEP_SO = "so.json"
TEP_MD = "BAO-CAO-CONG-TY.md"
TEP_JSON = "bao-cao.json"
CHE_DO = ("tat", "goi_y", "tu_ap")
KHE_MIN, KHE_MAX = 1, 6
HE_SO_TRAN = 0.85
NGHI_NGAY = 14
CHU_GIU_NGAY = 30
QUAY_LUI_SAU_NGAY = 7
TUT_QUAY_LUI = 0.30
KHE_NANG_QUA_TAI = 90.0
#: Cửa sổ đo công suất: 48 giờ gần, không lùi qua mốc thay đổi lớn (`cong_suat.MOC_DOI_LON`). 01/10/2026:
#: đo 168 giờ (phần lớn trước khi khâu ảnh nhanh gấp 4) + 3 lượt giữ làn API "ma" → trần 17,9 → đề xuất
#: cắt TL1–3 6→5 khe sai.
GIO_CONG_SUAT = 48
TEN_LOAI = {"len": "lên", "chung": "chững", "tut": "tụt"}


def _doc_json(duong: str, mac_dinh: Any = None) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return mac_dinh


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)


def _tm(goc: str, ten: str = "") -> str:
    return os.path.join(goc, THU_MUC, ten) if ten else os.path.join(goc, THU_MUC)


def che_do(goc: str) -> str:
    cd = str((_doc_json(os.path.join(goc, "workspace", "cai-dat.json"), {}) or {}).get("tong_giam_doc") or "tat")
    cd = cd.strip().lower()
    return cd if cd in CHE_DO else "tat"


def doc_so(goc: str) -> Dict[str, Any]:
    du = _doc_json(_tm(goc, TEP_SO), {})
    du = du if isinstance(du, dict) else {}
    du.setdefault("hop", [])
    du.setdefault("thay_doi", [])
    return du


# ── bảng công ty ───────────────────────────────────────────────────────────

def _cac_kenh(goc: str) -> Dict[str, List[str]]:
    """{mã kênh YouTube (gốc): [mã kênh tool…]} — `X-v2` đăng cùng kênh YouTube với `X`."""
    from ..kenh import TEP_KENH, duong_kenh  # noqa: PLC0415

    ra: Dict[str, List[str]] = {}
    for p in sorted(glob.glob(os.path.join(duong_kenh(goc), "*", TEP_KENH))):
        ma = os.path.basename(os.path.dirname(p))
        if not ma.startswith("_"):
            ra.setdefault(re.sub(r"[-_]v\d+$", "", ma, flags=re.IGNORECASE), []).append(ma)
    return ra


def _nhip(cai: Dict[str, Any]) -> List[str]:
    from ..xep_lich import chuan_hoa_nhip  # noqa: PLC0415

    return chuan_hoa_nhip(cai.get("nhip_dang"))


def _bat(x: Any) -> bool:
    return str(x).strip().lower() == "true" or x is True


def _uoc_vnd(goc: str, ma: str) -> int:
    """Ước chi 1 video (cùng cách `dieu_phoi.trang_thai_kenh`)."""
    try:
        from .. import tu_chay  # noqa: PLC0415
        from ..kenh import doc_kenh  # noqa: PLC0415
        from ..money import micro_to_vnd  # noqa: PLC0415
        from ..pricing import DEFAULT_PRICES  # noqa: PLC0415

        return int(micro_to_vnd(tu_chay._uoc_chi_phi_micro(doc_kenh(goc, ma), DEFAULT_PRICES)))  # noqa: SLF001
    except Exception:  # noqa: BLE001
        return 0


def xep_loai(d: Dict[str, Any]) -> str:
    """lên: đà hiển thị 7 ngày ≥ 1,2 và tỉ lệ thắng 28 ngày ≥ 25% · tụt: đà ≤ 0,8 · còn lại (cả thiếu số): chững."""
    da, th = d.get("da"), d.get("ti_le_thang")
    if da is not None and da >= 1.2 and (th or 0) >= 0.25:
        return "len"
    if da is not None and da <= 0.8:
        return "tut"
    return "chung"


def bang_cong_ty(goc: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Một dòng mỗi kênh YouTube: số 7 ngày / 7 ngày trước, thắng 28 ngày, YPP, khe, trần, ngân sách."""
    from . import bao_cao  # noqa: PLC0415
    from .du_lieu import tom_tat, trong_khoang  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    tuan = _dt.timedelta(days=7)
    ra = []
    for ma, cac in _cac_kenh(goc).items():
        bs = tom_tat(goc, ma, bay_gio=bay_gio)
        dau = next((x["luc"] for x in bs.kenh_ngay if x.get("hien_thi") is not None), None)
        tu7 = max(bay_gio - tuan, dau) if dau and dau < bay_gio - _dt.timedelta(days=2) else bay_gio - tuan
        so7 = {k: trong_khoang(bs, k, tu7, bay_gio) for k in ("hien_thi", "gio_xem", "sub", "xem")}  # kênh mới: từ dòng đầu
        truoc = trong_khoang(bs, "hien_thi", bay_gio - 2 * tuan, bay_gio - tuan)
        v28 = [v for v in bs.video if v.get("dang_luc") and v["dang_luc"] >= bay_gio - 4 * tuan]
        kl = [v for v in v28 if v.get("ket_luan") in ("thang", "truot")]
        v14 = [v.get("hien_thi_48h") for v in bs.video if v.get("dang_luc") and v["dang_luc"] >= bay_gio - 2 * tuan
               and v.get("hien_thi_48h") is not None]
        chay = []
        for m in cac:
            cai = bs.cai if m == ma else _cai(goc, m)
            if _bat(cai.get("tu_chay")) and _bat(cai.get("tu_duyet")) and _nhip(cai):
                chay.append({"ma": m, "nhip": _nhip(cai), "video_toi_da_ngay": int(cai.get("video_toi_da_ngay") or 0),
                             "ngan_sach_ngay": int(cai.get("ngan_sach_ngay") or 0)})
        d = {"ma": ma, "cac_ma": cac, "chay": chay, "khe": sum(len(c["nhip"]) for c in chay),
             "hien_thi_7": so7["hien_thi"], "hien_thi_7_truoc": truoc, "gio_xem_7": so7["gio_xem"], "sub_7": so7["sub"],
             "xem_7": so7["xem"], "da": round(so7["hien_thi"] / truoc, 2) if so7["hien_thi"] is not None and truoc else None,
             "thang_28": sum(1 for v in kl if v["ket_luan"] == "thang"), "kl_28": len(kl), "video_28": len(v28),
             "ti_le_thang": round(sum(1 for v in kl if v["ket_luan"] == "thang") / len(kl), 2) if kl else None,
             "tv_48h_14": statistics.median(v14) if v14 else None,
             "ypp_sub": (bs.ypp or {}).get("sub"), "ypp_gio": (bs.ypp or {}).get("gio_xem"),
             "giam_doc": str(bs.cai.get("giam_doc") or "tat"), "bao_cao_kenh": bao_cao.cau_the(goc, ma),
             "_video": [(v.get("dang_luc"), v.get("hien_thi_48h")) for v in bs.video]}
        d["loai"] = xep_loai(d)
        ra.append(d)
    return ra


def _cai(goc: str, ma: str) -> Dict[str, Any]:
    from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

    return dict(doc_yaml(os.path.join(duong_kenh(goc, ma), TEP_KENH)) or {})


def tran_may(cs: Dict[str, Any]) -> float:
    """Trần video/ngày của máy (`cong_suat`: min(khe nặng, làn API))."""
    xs = [cs.get("tran_video_ngay_khe_nang"), cs.get("tran_video_ngay_lan_api")]
    xs = [float(x) for x in xs if x is not None]
    return min(xs) if xs else 0.0


# ── luật khe ───────────────────────────────────────────────────────────────

def chia_khe(bang: List[Dict[str, Any]], tran: float) -> List[Dict[str, Any]]:
    """Lên +1, tụt −1, chững giữ; mỗi kênh 1..6; tổng ≤ 0,85 × trần máy (quá thì bỏ tăng, rồi bớt kênh nhiều khe)."""
    dong = [d for d in bang if d["chay"]]
    moi = {d["ma"]: max(KHE_MIN, min(KHE_MAX, d["khe"] + {"len": 1, "tut": -1}.get(d["loai"], 0))) for d in dong}
    tran_tong = math.floor(HE_SO_TRAN * tran) if tran else sum(d["khe"] for d in dong)
    for d in sorted((d for d in dong if moi[d["ma"]] > d["khe"]), key=lambda d: d.get("da") or 0):
        if sum(moi.values()) <= tran_tong:
            break
        moi[d["ma"]] = d["khe"]
    for d in sorted(dong, key=lambda d: (-d["khe"], d.get("da") or 0)):
        if sum(moi.values()) <= tran_tong:
            break
        if moi[d["ma"]] == d["khe"] and d["khe"] > KHE_MIN:
            moi[d["ma"]] = d["khe"] - 1
    ra = []
    for d in dong:
        if moi[d["ma"]] != d["khe"]:
            ly = ("kênh {0} (đà {1})".format(TEN_LOAI[d["loai"]], d.get("da")) if d["loai"] != "chung"
                  else "máy vượt trần {0}".format(tran_tong))
            ra.append({"ma": d["ma"], "khe_cu": d["khe"], "khe_moi": moi[d["ma"]], "ly_do": ly})
    return ra


def _phut(g: str) -> int:
    h, m = g.split(":")
    return int(h) * 60 + int(m)


def nhip_moi(nhip: List[str], so: int, video: Optional[List[Any]] = None) -> List[str]:
    """Thêm: giữa khoảng trống lớn nhất (giờ tròn). Bớt: khe có hiển thị 48h trung vị thấp nhất (thiếu số: khe cuối)."""
    ds = sorted(set(nhip))
    while len(ds) < so:
        ph = sorted(_phut(g) for g in ds) or [0]
        khoang = [((ph[(i + 1) % len(ph)] - p) % 1440 or 1440, p) for i, p in enumerate(ph)]
        dai, p = max(khoang)
        g = "{0:02d}:00".format(((p + dai // 2) // 60) % 24)
        if g in ds:
            break
        ds = sorted(ds + [g])
    while len(ds) > max(so, KHE_MIN):
        theo: Dict[str, List[float]] = {g: [] for g in ds}
        for luc, h48 in video or []:
            if luc is not None and h48 is not None:
                p = luc.hour * 60 + luc.minute
                g = min(ds, key=lambda x: min((p - _phut(x)) % 1440, (_phut(x) - p) % 1440))
                theo[g].append(h48)
        co = {g: statistics.median(x) for g, x in theo.items() if x}
        ds.remove(min(co, key=co.get) if len(co) >= 2 else ds[-1])
    return ds


def thuc_don(goc: str, bang: List[Dict[str, Any]], tran: float, so_: Dict[str, Any],
             bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Đề xuất đổi khe (id t1…) kèm kết quả soát: nghỉ 14 ngày, chủ sửa tay 30 ngày."""
    theo = {d["ma"]: d for d in bang}
    ra = []
    for c in chia_khe(bang, tran):
        d = theo[c["ma"]]
        k = d["chay"][0]
        moi_nhip = nhip_moi(k["nhip"], len(k["nhip"]) + (c["khe_moi"] - c["khe_cu"]), d.get("_video"))
        n = len(moi_nhip)
        ns = max(k["ngan_sach_ngay"], int(_uoc_vnd(goc, k["ma"]) * n * 1.3))
        cuoi = next((t for t in reversed(so_["thay_doi"]) if t.get("ma") == k["ma"]), None)
        duoc, ly = True, ""
        if cuoi:
            tuoi = (bay_gio - _dt.datetime.fromisoformat(str(cuoi["luc"])[:19])).days
            if tuoi < NGHI_NGAY:
                duoc, ly = False, "vừa đổi {0} ngày trước — nghỉ {1} ngày".format(tuoi, NGHI_NGAY)
            elif (tuoi < CHU_GIU_NGAY and cuoi.get("trang_thai") != "quay_lui"
                  and ", ".join(k["nhip"]) != (cuoi.get("moi") or {}).get("nhip_dang")):
                duoc, ly = False, "chủ đã sửa nhip_dang tay — giữ {0} ngày".format(CHU_GIU_NGAY)
        ra.append({"id": "t{0}".format(len(ra) + 1), "ma": k["ma"], "kenh_youtube": d["ma"], "loai": d["loai"],
                   "khe_cu": c["khe_cu"], "khe_moi": c["khe_moi"], "ly_do": c["ly_do"],
                   "cu": {"nhip_dang": ", ".join(k["nhip"]), "video_toi_da_ngay": k["video_toi_da_ngay"],
                          "ngan_sach_ngay": k["ngan_sach_ngay"]},
                   "moi": {"nhip_dang": ", ".join(moi_nhip), "video_toi_da_ngay": n, "ngan_sach_ngay": ns},
                   "duoc": duoc, "ly_do_kiem": ly})
    return ra


def de_xuat_kenh_moi(goc: str, cs: Dict[str, Any]) -> List[str]:
    """CHỈ gợi ý: ứng viên kênh mới từ bản đồ khoảng trống mới nhất, khi máy còn dư ≥ 2 video/ngày."""
    if float(cs.get("con_du_video_ngay") or 0) < 2:
        return []
    tep = sorted(glob.glob(os.path.join(goc, "workspace", "khoang-trong-kenh-*.md")))
    if not tep:
        return []
    try:
        with io.open(tep[-1], encoding="utf-8") as f:
            dong = [x.strip("# ").strip() for x in f if x.startswith("### ")]
    except OSError:
        return []
    chot = [x for x in dong if x.upper().startswith("CHỐT")]
    return (chot + [x for x in dong if x.startswith("Ứng viên")])[:4] + ["(nguồn: {0})".format(os.path.basename(tep[-1]))]


# ── quay lui (luật cứng) ───────────────────────────────────────────────────

def can_quay_lui(bang: List[Dict[str, Any]], cs: Dict[str, Any], so_: Dict[str, Any],
                 bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Thay đổi đang mở ≥ 7 ngày: hiển thị 48h trung vị (video đăng sau khi đổi) tụt ≥ 30% so với nền, hoặc
    máy quá tải (khe nặng ≥ 90%) với thay đổi TĂNG khe."""
    theo = {m: d for d in bang for m in d["cac_ma"]}
    qua_tai = float(cs.get("phan_tram_khe_nang") or 0) >= KHE_NANG_QUA_TAI
    ra = []
    for t in so_["thay_doi"]:
        if t.get("trang_thai") != "mo":
            continue
        luc = _dt.datetime.fromisoformat(str(t["luc"])[:19])
        if (bay_gio - luc).days < QUAY_LUI_SAU_NGAY:
            continue
        d = theo.get(t["ma"]) or {}
        sau = [h for l_, h in d.get("_video") or [] if l_ and l_ >= luc and h is not None]
        nen = (t.get("nen") or {}).get("tv_48h_14")
        ly = ""
        if len(sau) >= 2 and nen and statistics.median(sau) <= (1 - TUT_QUAY_LUI) * nen:
            ly = "hiển thị 48h trung vị {0:.0f} ≤ 70% nền {1:.0f}".format(statistics.median(sau), nen)
        elif qua_tai and t.get("khe_moi", 0) > t.get("khe_cu", 0):
            ly = "máy quá tải: khe nặng {0}%".format(cs.get("phan_tram_khe_nang"))
        if ly:
            ra.append(dict(t, ly_do_quay_lui=ly))
    return ra


def _ghi_kenh(goc: str, ma: str, gt: Dict[str, Any]) -> None:
    from ..trung_tam import ghi_cai_kenh  # noqa: PLC0415

    ghi_cai_kenh(goc, ma, nhip_dang=gt["nhip_dang"], video_toi_da_ngay=int(gt["video_toi_da_ngay"]),
                 ngan_sach_ngay=int(gt["ngan_sach_ngay"]))


# ── họp tuần ───────────────────────────────────────────────────────────────

DANG_TRA_LOI = """\
Chỉ trả MỘT khối JSON:
{"chan_doan": "≤ 3 câu có số: kênh nào kéo công ty, kênh nào tụt, máy còn dư bao nhiêu",
 "chon": [{"id": "t1", "ly_do": "1 câu có số"}],
 "viec_cua_ban": ["việc chỉ chủ làm được (mở kênh mới, đăng nhập…) — không có thì []"],
 "so_dan": [{"so": 1.25, "nguon": "<khoá trong BẢNG SỐ>"}]}"""


def _so_lieu(bang: List[Dict[str, Any]], cs: Dict[str, Any], tran: float) -> Dict[str, Any]:
    ra: Dict[str, Any] = {"may/tran_video_ngay": round(tran, 1), "may/con_du_video_ngay": cs.get("con_du_video_ngay"),
                          "may/khe_nang_pct": cs.get("phan_tram_khe_nang")}
    for d in bang:
        for k in ("khe", "hien_thi_7", "hien_thi_7_truoc", "da", "gio_xem_7", "sub_7", "ti_le_thang", "thang_28",
                  "kl_28", "tv_48h_14", "ypp_sub", "ypp_gio"):
            if d.get(k) is not None:
                ra["k:{0}/{1}".format(d["ma"], k)] = round(d[k], 2) if isinstance(d[k], float) else d[k]
    return ra


def loi_nhac(bang: List[Dict[str, Any]], cs: Dict[str, Any], tran: float, td: List[Dict[str, Any]],
             kenh_moi: List[str], so_lieu: Dict[str, Any], gio_online: Sequence[str] = ()) -> str:
    dong_td = ["{0} {1} [{2}]: khe {3} → {4} ({5}); nhip_dang “{6}” → “{7}”{8}".format(
        t["id"], t["ma"], TEN_LOAI[t["loai"]], t["khe_cu"], t["khe_moi"], t["ly_do"], t["cu"]["nhip_dang"],
        t["moi"]["nhip_dang"], "" if t["duoc"] else " — CHẶN: " + t["ly_do_kiem"]) for t in td]
    return "\n\n".join([
        "Bạn là TỔNG GIÁM ĐỐC một công ty làm YouTube (nhiều kênh trên một máy). View = Hiển thị × CTR × Giữ chân. "
        "Việc của bạn mỗi tuần: dồn khe đăng cho kênh đang lên, bớt cho kênh tụt, không vượt sức máy.",
        "BẢNG SỐ (khoá = giá trị; da = hiển thị 7 ngày ÷ 7 ngày trước; ti_le_thang = video thắng @48h / video đã có "
        "kết luận, 28 ngày; tv_48h_14 = trung vị hiển thị 48h video 14 ngày)\n"
        + "\n".join("{0} = {1}".format(k, v) for k, v in so_lieu.items()),
        "XẾP LOẠI (luật: lên = đà ≥ 1,2 và thắng ≥ 25%; tụt = đà ≤ 0,8)\n" + "\n".join(
            "- {0} ({1}): {2}, {3} khe — giám đốc kênh: {4}".format(d["ma"], "+".join(d["cac_ma"]), TEN_LOAI[d["loai"]],
                                                                    d["khe"], d["bao_cao_kenh"] or "—") for d in bang),
        "MÁY: " + str(cs.get("cau") or cs.get("de_xuat") or "") + " · trần ≈ {0:.1f} video/ngày, tổng khe ≤ 85% trần".format(tran),
        "THỰC ĐƠN (chỉ chọn id trong đây; không đáng đổi thì \"chon\": [])\n" + ("\n".join(dong_td) or "(trống)"),
        "KÊNH MỚI (chỉ gợi ý cho chủ): " + (" | ".join(kenh_moi) or "máy chưa dư ≥ 2 video/ngày — chưa nên mở"),
    ] + (["GIỜ KHÁN GIẢ ONLINE (đặt khe mới gần giờ đông; lệch nhiều thì ghi gợi ý vào viec_cua_ban)\n"
          + "\n".join("- " + x for x in gio_online)] if gio_online else []) + [
        DANG_TRA_LOI,
    ])


def doc_ket_qua(tho: str, td: List[Dict[str, Any]], so_lieu: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    from ..goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return None
    if not isinstance(du, dict) or "chon" not in du:
        return None
    theo = {t["id"]: t for t in td}
    chon = []
    for m in du.get("chon") or []:
        if isinstance(m, dict) and m.get("id") in theo and all(c["id"] != m["id"] for c in chon):
            chon.append(dict(theo[m["id"]], ly_do_llm=" ".join(str(m.get("ly_do") or "").split())[:300]))
    vcb = du.get("viec_cua_ban") or []
    return {"chan_doan": " ".join(str(du.get("chan_doan") or "").split())[:600], "chon": chon,
            "viec_cua_ban": [str(x)[:300] for x in (vcb if isinstance(vcb, list) else [vcb]) if str(x).strip()][:4],
            "so_dan": [x for x in du.get("so_dan") or [] if isinstance(x, dict) and x.get("nguon")][:12]}


def hop_tuan(goc: str, goi_chat: Optional[Callable[..., str]], *, ep_che_do: Optional[str] = None,
             thu: bool = False, bay_gio: Optional[_dt.datetime] = None,
             ghi: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Một lượt họp tuần. `thu=True`: tính + (nếu có `goi_chat`) hỏi LLM, KHÔNG ghi gì."""
    from .. import cong_suat  # noqa: PLC0415
    from . import quan_ly  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    cd = ep_che_do or che_do(goc)
    so_ = doc_so(goc)
    bang = bang_cong_ty(goc, bay_gio)
    try:
        cs = cong_suat.cong_suat_hien_tai(goc, gio=GIO_CONG_SUAT)
    except Exception:  # noqa: BLE001
        cs = {}
    tran = tran_may(cs)
    cs["cau"] = "{6} giờ gần{7}: {0} video ({1}/ngày) · khe nặng {2}% · làn API {3}/{4} · còn dư ≈ {5} video/ngày".format(
        cs.get("video_ban_giao", "?"), cs.get("video_ngay_do", "?"), cs.get("phan_tram_khe_nang", "?"),
        cs.get("lan_api_trung_binh_dang_dung", "?"), cs.get("lan_api", "?"), cs.get("con_du_video_ngay", "?"),
        cs.get("cua_so_gio", GIO_CONG_SUAT), " (từ mốc đổi {0})".format(cs["tu_moc_doi"]) if cs.get("tu_moc_doi") else "")
    td = thuc_don(goc, bang, tran, so_, bay_gio)
    kenh_moi = de_xuat_kenh_moi(goc, cs)
    sl = _so_lieu(bang, cs, tran)
    from . import goi_y_gio_dang  # noqa: PLC0415 — giờ khán giả online (chỉ khi kênh đã có gio-online.json)

    ln = loi_nhac(bang, cs, tran, td, kenh_moi, sl,
                  gio_online=[x for x in ("{0}: {1}".format(d["ma"], goi_y_gio_dang(goc, d["ma"])) for d in bang
                                          if goi_y_gio_dang(goc, d["ma"]))])
    kq: Dict[str, Any] = {"luc": bay_gio.replace(microsecond=0).isoformat(), "che_do": cd, "thu": thu,
                          "bang": [{k: v for k, v in d.items() if k != "_video"} for d in bang], "tran": round(tran, 1),
                          "may": {k: cs.get(k) for k in ("cau", "con_du_video_ngay", "phan_tram_khe_nang")},
                          "thuc_don": td, "kenh_moi": kenh_moi, "quyet": None, "da_lam": [], "se_lam": [],
                          "quay_lui": [], "loi": "", "loi_nhac": ln}
    if not thu:
        for t in can_quay_lui(bang, cs, so_, bay_gio):
            if cd == "tu_ap":
                _ghi_kenh(goc, t["ma"], t["cu"])
                next(x for x in so_["thay_doi"] if x["id"] == t["id"]).update(
                    trang_thai="quay_lui", ly_do_quay_lui=t["ly_do_quay_lui"], quay_lui_luc=kq["luc"])
            kq["quay_lui"].append({"ma": t["ma"], "ly_do": t["ly_do_quay_lui"], "ap": cd == "tu_ap"})
        for t in so_["thay_doi"]:
            if t.get("trang_thai") == "mo" and (bay_gio - _dt.datetime.fromisoformat(t["luc"][:19])).days >= NGHI_NGAY:
                t["trang_thai"] = "giu"
    if goi_chat is not None:
        q = quan_ly.goi_quyet("tong_giam_doc", ln, sl, goi_chat, doc=lambda tho: doc_ket_qua(tho, td, sl), goc=goc,
                              khoa="tong-{0:%Y%m%d}".format(bay_gio), ghi=ghi, luu=not thu,
                              n=sum(int(d.get("kl_28") or 0) for d in bang))
        kq["quyet"], kq["loi"], kq["mo_hinh"] = q["ket"], q["loi"], q["mo_hinh"]
        kq["hoi_dong"] = q.get("hoi_dong") or {}
    else:
        kq["loi"] = "không gọi AI (chế độ thử / van ví chặn)"
    if kq["quyet"] and kenh_moi and float(cs.get("con_du_video_ngay") or 0) >= 2:  # quyết định lớn: chủ duyệt
        vcb = kq["quyet"].setdefault("viec_cua_ban", [])
        vcb.append("Mở kênh mới (chỉ bạn quyết, máy còn dư ≈ {0} video/ngày): {1}".format(
            cs.get("con_du_video_ngay"), " | ".join(kenh_moi[:2])))
    from . import hoi_dong  # noqa: PLC0415

    quyen_khe = hoi_dong.quyen(goc, "", "chia_khe") if cd == "tu_ap" and not thu else "goi_y"
    kq["quyen_chia_khe"] = quyen_khe
    for t in (kq["quyet"] or {}).get("chon") or []:
        if not t["duoc"]:
            continue
        if cd == "tu_ap" and not thu and quyen_khe == "tu_ap":
            _ghi_kenh(goc, t["ma"], t["moi"])
            nen = {"tv_48h_14": next((d["tv_48h_14"] for d in bang if t["ma"] in d["cac_ma"]), None)}
            so_["thay_doi"].append({"id": "{0:%Y%m%d}-{1}".format(bay_gio, t["ma"]), "ma": t["ma"], "luc": kq["luc"],
                                    "khe_cu": t["khe_cu"], "khe_moi": t["khe_moi"], "cu": t["cu"], "moi": t["moi"],
                                    "nen": nen, "ly_do_llm": t.get("ly_do_llm"), "trang_thai": "mo"})
            kq["da_lam"].append(t)
        else:
            kq["se_lam"].append(t)
    if not thu:
        so_["hop"] = (so_["hop"] + [{"ngay": bay_gio.date().isoformat(), "che_do": cd, "chon": [t["id"] for t in (
            kq["quyet"] or {}).get("chon") or []], "loi": kq["loi"]}])[-60:]
        _ghi_json(_tm(goc, TEP_SO), so_)
        bao_cao(goc, kq)
    return kq


# ── báo cáo + nhịp ─────────────────────────────────────────────────────────

def _s(x: Any, le: int = 0) -> str:
    from .du_lieu import chu_so  # noqa: PLC0415

    return chu_so(x, le)


def chu_bao_cao(kq: Dict[str, Any]) -> str:
    q = kq.get("quyet") or {}
    ra = ["# Báo cáo công ty — {0} ({1}{2})".format(kq["luc"][:10], kq["che_do"], ", thử" if kq.get("thu") else ""), "",
          "| Kênh YouTube | Loại | Khe | Hiển thị 7 ngày | 7 ngày trước | Đà | Giờ xem 7 ngày | Sub 7 ngày | Thắng 28 ngày | YPP sub / giờ |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for d in kq["bang"]:
        ra.append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} / {10} |".format(
            "+".join(d["cac_ma"]), TEN_LOAI[d["loai"]], d["khe"], _s(d["hien_thi_7"]), _s(d["hien_thi_7_truoc"]),
            _s(d["da"], 2), _s(d["gio_xem_7"], 1), _s(d["sub_7"]),
            "{0}/{1}".format(d["thang_28"], d["kl_28"]) if d["kl_28"] else "—", _s(d["ypp_sub"]), _s(d["ypp_gio"])))
    ra += ["", "**Máy:** {0} — trần ≈ {1} video/ngày, tổng khe ≤ 85%.".format((kq.get("may") or {}).get("cau") or "?", kq["tran"])]
    if q.get("chan_doan"):
        ra += ["", "**Chẩn đoán:** " + q["chan_doan"]]
    hq = (kq.get("hoi_dong") or {}).get("quyet") or {}
    if hq:
        ra += ["", "**Hội đồng:** chọn phương án {0} · độ tin {1} · cổng {2}{3}".format(
            hq.get("ten"), hq.get("do_tin"), kq["hoi_dong"].get("cong"),
            " · chưa có quyền tự áp chia khe (cần ≥ 70% đúng trên ≥ 10 lần)"
            if kq.get("che_do") == "tu_ap" and kq.get("quyen_chia_khe") == "goi_y" else "")]
    ra += ["", "## Đổi khe"]
    chon = {t["id"]: t for t in (q.get("chon") or [])}
    da = {t["id"] for t in kq["da_lam"]}
    for t in kq["thuc_don"]:
        t = chon.get(t["id"], t)
        trang = ("ĐÃ ÁP" if t["id"] in da else "SẼ ĐỔI (gợi ý)" if t["id"] in chon and t["duoc"] else
                 "chặn: " + t["ly_do_kiem"] if not t["duoc"] else "không chọn")
        ra.append("- {0} {1}: khe {2} → {3} ({4}) — nhip “{5}” → “{6}” · {7}{8}".format(
            t["id"], t["ma"], t["khe_cu"], t["khe_moi"], t["ly_do"], t["cu"]["nhip_dang"], t["moi"]["nhip_dang"], trang,
            " — " + t["ly_do_llm"] if t.get("ly_do_llm") else ""))
    if not kq["thuc_don"]:
        ra.append("- Không kênh nào cần đổi khe tuần này.")
    for x in kq["quay_lui"]:
        ra.append("- QUAY LUI {0}: {1}{2}".format(x["ma"], x["ly_do"], "" if x["ap"] else " (gợi ý)"))
    ra += ["", "## Kênh mới (chỉ gợi ý)"] + ["- " + x for x in kq["kenh_moi"] or ["Máy chưa dư ≥ 2 video/ngày — chưa nên mở."]]
    vcb = q.get("viec_cua_ban") or []
    if vcb:
        ra += ["", "## Việc của bạn"] + ["- " + x for x in vcb]
    if kq.get("loi"):
        ra += ["", "_AI: {0}_".format(kq["loi"])]
    return "\n".join(ra) + "\n"


def bao_cao(goc: str, kq: Dict[str, Any]) -> str:
    """Ghi `BAO-CAO-CONG-TY.md` + `bao-cao.json`. Trả đường md."""
    duong = _tm(goc, TEP_MD)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu_bao_cao(kq))
    _ghi_json(_tm(goc, TEP_JSON), {k: v for k, v in kq.items() if k != "loi_nhac"})
    return duong


def cau_the(goc: str) -> Dict[str, str]:
    """Một dòng "công ty" cho bảng điều khiển: {cau, bao_cao}. Chưa có báo cáo → cau rỗng."""
    bc = _doc_json(_tm(goc, TEP_JSON), {}) or {}
    if not bc.get("bang"):
        return {"cau": "", "bao_cao": ""}
    dem = {k: sum(1 for d in bc["bang"] if d.get("loai") == k) for k in TEN_LOAI}
    doi = [t for t in bc.get("da_lam") or bc.get("se_lam") or []]
    cau = "{0} {1}: {2} kênh · lên {3} · chững {4} · tụt {5} · {6} khe{7}".format(
        "Công ty" + (" (gợi ý)" if bc.get("che_do") != "tu_ap" else ""), str(bc.get("luc"))[5:10].replace("-", "/"),
        len(bc["bang"]), dem["len"], dem["chung"], dem["tut"], sum(d.get("khe") or 0 for d in bc["bang"]),
        " — " + ", ".join("{0} {1}→{2}".format(t["ma"], t["khe_cu"], t["khe_moi"]) for t in doi) if doi else "")
    return {"cau": cau, "bao_cao": _tm(goc, TEP_MD) if os.path.isfile(_tm(goc, TEP_MD)) else ""}


def den_han(goc: str, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Thứ Hai, tổng giám đốc bật, tuần này chưa họp, mọi giám đốc kênh đang bật đã chạy lượt tuần hôm nay."""
    from . import _kenh_bat, so_thi_nghiem as stn  # noqa: PLC0415

    bay_gio = bay_gio or _dt.datetime.now()
    if bay_gio.weekday() != 0 or che_do(goc) == "tat":
        return False
    hom_nay = bay_gio.date().isoformat()
    if any(h.get("ngay") == hom_nay for h in doc_so(goc)["hop"]):
        return False
    return all(stn.doc_trang_thai(goc, ma).get("ngay_tuan") == hom_nay for ma in _kenh_bat(goc))
