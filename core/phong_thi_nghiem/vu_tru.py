"""Vũ trụ ứng viên của một kênh một ngày — 3 nguồn, chỉ ĐỐI THỦ THẬT (`workspace/chan-doan/ke-hoach-phong-thi-nghiem-content.md` mục 1).

Nguồn (mỗi ứng viên mang nhãn nguồn, có thể nhiều):
  * `doi_thu`   — video trong sổ content của kênh đối thủ THẬT (video mới / còn tăng; cũ mà đứng im thì bỏ);
  * `pool`      — video trong bảng "video đề xuất" Studio của video mình (khán giả CỦA MÌNH bấm sang/từ đó);
  * `trang_chu` — video trang chủ máy ảo của kênh đẩy trong `NGAY_TRANG_CHU` ngày.

ĐỐI THỦ THẬT (`phan_kenh`, theo thứ tự — lý do đầu tiên trượt được ghi):
  1. sổ đối thủ không để "bỏ"/"hết";
  2. cùng ngách theo AI (Ghi chú "✓ AI kiểm ngách" / kho chung `kenh-ai.json` / bộ nhớ AI của V7) — AI phán lạc → bỏ;
     chưa ai phán thì giữ, ghi `ngach = "?"`;
  3. còn hoạt động: video dài (≥ 4 phút) mới nhất trong sổ ≤ `NGAY_HOAT_DONG` ngày;
  4. đủ lớn: trung vị view/kênh ("View TV") ≥ max(`SAN_KENH_TUYET_DOI`, phân vị `SAN_KENH_PHAN_VI` của các kênh đối
     thủ đạt 1–3) — sàn TƯƠNG ĐỐI theo ngách (chẩn đoán 12/10: kênh nguồn "yếu" < 1.500 vẫn cho 4/8 hit, nên sàn thấp);
  5. có bằng chứng YouTube nối khán giả: kênh hiện trên trang chủ máy ảo của kênh mình trong `NGAY_BANG_CHUNG` ngày,
     hoặc có video trong pool đề xuất của mình.
Kênh trượt → mọi video của nó ra khỏi vũ trụ (vẫn lưu tên + lý do trong `kenh` để tra).

Video bị bỏ dù kênh đạt: video của ta (mọi kênh trong nhóm), nguồn nhóm đã làm TRƯỚC mốc, video ngắn < 4 phút, video
cũ hơn `NGAY_MOI` ngày mà không đột biến (gấp < `VUOT_DOT_BIEN` × trung vị kênh và không còn tăng). Ứng viên chỉ có trong pool (kênh ngoài sổ) được GIỮ với `kenh_ro = 0`
(pool đã là bằng chứng khán giả); ứng viên chỉ có trên trang chủ mà kênh ngoài sổ → bỏ.

Hàm thuần trên `TheGioi` (bài kiểm dựng số giả). Không mạng, không AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from . import _chung as c
from .nguon import TheGioi, luc_quet_kenh

SAN_KENH_PHAN_VI = 0.10
SAN_KENH_TUYET_DOI = 50.0
NGAY_HOAT_DONG = 30
NGAY_BANG_CHUNG = 28
NGAY_TRANG_CHU = 14
GIAY_VIDEO_DAI = 240
#: Sổ đối thủ chỉ góp video MỚI (≤ `NGAY_MOI` ngày) hoặc ĐỘT BIẾN (gấp ≥ `VUOT_DOT_BIEN` × trung vị kênh, hoặc còn
#: tăng giữa hai lượt quét). Video cũ, thường, đứng im không là ứng viên của giả thuyết nào (V7 bản 5 cũng chỉ sản
#: xuất nguồn gấp ≥ 3×).
NGAY_MOI = 30
VUOT_DOT_BIEN = 2.0

THEO_DOI, BO, HET = "theo dõi", "bỏ", "hết"
DAU_GIU, DAU_NGHI, DAU_BO = "✓ AI kiểm ngách", "⚠ NGHI", "AI kiểm ngách"

NGUON_DOI_THU, NGUON_POOL, NGUON_TRANG_CHU = "doi_thu", "pool", "trang_chu"


@dataclass
class VuTru:
    ung_vien: List[Dict[str, Any]] = field(default_factory=list)
    kenh: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    bo: Dict[str, int] = field(default_factory=dict)
    thong_ke: Dict[str, Any] = field(default_factory=dict)


def _ma(link: str) -> str:
    try:
        from ..doi_thu_kenh import ma_video  # noqa: PLC0415

        return ma_video(link)
    except Exception:  # noqa: BLE001
        return ""


def _ngach(r: Dict[str, str], kenh_ai: Dict[str, str], ai_nho: Dict[str, Dict[str, Any]]) -> str:
    ghi = str(r.get("Ghi chú") or "").strip()
    if ghi.startswith(DAU_GIU):
        return "giu"
    if ghi.startswith(DAU_NGHI):
        return "nghi"
    v = kenh_ai.get(str(r.get("Link kênh") or "").strip().lower())
    if v:
        return v
    if ghi.startswith(DAU_BO):
        return "bo"
    k = ai_nho.get("kenh:" + str(r.get("Kênh") or "").strip())
    if isinstance(k, dict) and k.get("ngach") in ("dung", "gan", "lac"):
        return "bo" if k["ngach"] == "lac" else "giu"
    return "?"


def da_lam_truoc(da_lam: Dict[str, str], ma: str, ngay: str) -> bool:
    """Nguồn đã được nhóm làm TỚI hết ngày `ngay` ("" = không rõ ngày → coi như làm từ lâu)."""
    if ma not in da_lam:
        return False
    d = da_lam[ma]
    return (not d) or d <= ngay


def phan_kenh(tg: TheGioi, tc_kenh: Set[str], pool_kenh: Set[str]) -> Dict[str, Dict[str, Any]]:
    """`{tên kênh: {ok, ly_do, ngach, trang_thai, view_tv, cach_dang, ai, subs, bang_chung}}` — xem đầu tệp."""
    theo_kenh: Dict[str, List[Dict[str, str]]] = {}
    for r in tg.sach:
        ten = str(r.get("Kênh") or "").strip()
        if ten:
            theo_kenh.setdefault(ten, []).append(r)
    ra: Dict[str, Dict[str, Any]] = {}
    for r in tg.danh_ba:
        ten = str(r.get("Kênh") or "").strip()
        if not ten or ten in ra:
            continue
        tt = str(r.get("Trạng thái") or "").strip() or THEO_DOI
        ngach = _ngach(r, tg.kenh_ai, tg.ai_nho)
        ds = theo_kenh.get(ten, [])
        tv = c.so(r.get("View TV"))
        if not tv:
            views = [c.so(x.get("View")) for x in ds]
            views = [v for v in views if v]
            tv = c.trung_vi(views) if len(views) >= 5 else None
        dang_cuoi = None
        for x in ds:
            g = c.phut(x.get("Thời lượng"))
            if g is not None and g * 60 < GIAY_VIDEO_DAI:
                continue
            t = c.epoch_ngay_dang(x.get("Ngày đăng"))
            if t is not None and (dang_cuoi is None or t > dang_cuoi):
                dang_cuoi = t
        cach = (tg.moc - dang_cuoi) / c.NGAY_GIAY if dang_cuoi is not None else None
        bang = [x for x, co in (("trang_chu", ten in tc_kenh), ("pool", ten in pool_kenh)) if co]
        o = {"ok": False, "ly_do": "", "ngach": ngach, "trang_thai": tt, "view_tv": tv,
             "cach_dang": None if cach is None else round(cach, 1), "ai": str(r.get("AI") or "").strip(),
             "subs": c.so(r.get("Subs")), "bang_chung": bang, "link": str(r.get("Link kênh") or "")}
        if tt == BO:
            o["ly_do"] = "sổ: kênh bỏ"
        elif tt == HET:
            o["ly_do"] = "sổ: kênh hết (không còn làm / không phát triển)"
        elif ngach == "bo":
            o["ly_do"] = "AI: lạc ngách"
        elif cach is not None and cach > NGAY_HOAT_DONG:
            o["ly_do"] = "không đăng video dài > {0} ngày".format(NGAY_HOAT_DONG)
        ra[ten] = o
    # Sàn cỡ kênh: phân vị của các kênh đã qua cửa 1–3.
    tv_dat = [o["view_tv"] for o in ra.values() if not o["ly_do"] and o["view_tv"]]
    san = max(SAN_KENH_TUYET_DOI, c.phan_vi(tv_dat, SAN_KENH_PHAN_VI) or 0.0)
    for o in ra.values():
        if o["ly_do"]:
            continue
        if o["view_tv"] is not None and o["view_tv"] < san:
            o["ly_do"] = "kênh quá nhỏ (trung vị {0:.0f} < sàn {1:.0f} view)".format(o["view_tv"], san)
        elif not o["bang_chung"]:
            o["ly_do"] = "chưa có bằng chứng khán giả (không ở pool/trang chủ)"
        else:
            o["ok"] = True
        o["san"] = round(san, 1)
    return ra


def dung(tg: TheGioi) -> VuTru:
    """Vũ trụ ứng viên của `tg` (xem đầu tệp)."""
    vt = VuTru()
    bo = vt.bo

    def bo_(ly: str) -> None:
        bo[ly] = bo.get(ly, 0) + 1

    het = tg.ngay + " 99"
    tu_bc = c.cong_ngay(tg.ngay, -(NGAY_BANG_CHUNG - 1))
    tu_tc = c.cong_ngay(tg.ngay, -(NGAY_TRANG_CHU - 1))
    tc_kenh: Set[str] = set()
    tc_video: Dict[str, Dict[str, str]] = {}
    for r in tg.trang_chu:
        lq = str(r.get("Lúc quét") or "")[:16]
        if not lq or lq > het or lq[:10] < tu_bc:
            continue
        if str(r.get("Short") or "").strip():
            continue
        ten = str(r.get("Kênh") or "").strip()
        if ten:
            tc_kenh.add(ten)
        if lq[:10] >= tu_tc:
            ma = str(r.get("Mã video") or "")
            cu = tc_video.get(ma)
            if ma and (cu is None or lq > str(cu.get("Lúc quét") or "")):
                tc_video[ma] = r
    sach_theo_ma: Dict[str, Dict[str, str]] = {}
    for r in tg.sach:
        ma = _ma(str(r.get("Link video") or ""))
        if ma and ma not in sach_theo_ma:
            sach_theo_ma[ma] = r
    pool_ma = {p["ma"] for p in tg.pool}
    pool_kenh = {str(sach_theo_ma[m].get("Kênh") or "").strip() for m in pool_ma if m in sach_theo_ma}
    vt.kenh = phan_kenh(tg, tc_kenh, pool_kenh)
    luc_k = luc_quet_kenh(tg.danh_ba)

    def ung_vien_tu_sach(ma: str, r: Dict[str, str]) -> Dict[str, Any]:
        ten = str(r.get("Kênh") or "").strip()
        return {"ma": ma, "tieu_de": str(r.get("Tiêu đề video") or ""), "tieu_de_viet": str(r.get("Tiêu đề (Việt)") or ""),
                "kenh_nguon": ten, "nguon": {NGUON_DOI_THU}, "view": c.so(r.get("View")),
                "luc": luc_k.get(ten) or tg.luc_quet_sach or tg.moc, "ngay_dang": str(r.get("Ngày đăng") or "")[:10],
                "dai_phut": c.phut(r.get("Thời lượng")), "tang_ngay": c.so(r.get("Tăng/ngày")),
                "view_truoc": c.so(r.get("View lần trước")), "tuyen_nhan": str(r.get("Tuyến / Kênh") or "").strip(),
                "mo_ta": str(r.get("Mô tả") or "")[:300], "kenh_ro": 1,
                "da_lam_cot": str(r.get("Đã làm") or "").strip()}

    da: Dict[str, Dict[str, Any]] = {}
    n_sach = 0
    for ma, r in sach_theo_ma.items():
        n_sach += 1
        if not str(r.get("Tiêu đề video") or "").strip():
            bo_("thiếu tiêu đề")
            continue
        if ma in tg.ma_cua_nhom:
            bo_("video của ta")
            continue
        if da_lam_truoc(tg.da_lam, ma, tg.ngay) or (tg.che_do == "that" and str(r.get("Đã làm") or "").strip()):
            bo_("nhóm đã làm")
            continue
        ten = str(r.get("Kênh") or "").strip()
        o = vt.kenh.get(ten)
        if o is None:
            bo_("kênh ngoài sổ đối thủ")
            continue
        if not o["ok"]:
            bo_(o["ly_do"].split(" (")[0])
            continue
        g = c.phut(r.get("Thời lượng"))
        if g is not None and g * 60 < GIAY_VIDEO_DAI:
            bo_("video ngắn < 4 phút")
            continue
        t = c.epoch_ngay_dang(r.get("Ngày đăng"))
        tang = c.so(r.get("Tăng/ngày")) or 0.0
        view, tv = c.so(r.get("View")), o.get("view_tv")
        vuot = (view / tv) if (view and tv) else None
        if (t is not None and (tg.moc - t) / c.NGAY_GIAY > NGAY_MOI and tang <= 0
                and (vuot is None or vuot < VUOT_DOT_BIEN)):
            bo_("cũ > {0} ngày, không đột biến".format(NGAY_MOI))
            continue
        da[ma] = ung_vien_tu_sach(ma, r)
    # Pool: video khán giả mình bấm — kênh trong sổ thì theo luật kênh; ngoài sổ thì giữ (kenh_ro = 0).
    n_pool = 0
    for p in tg.pool:
        ma = p["ma"]
        if ma in da:
            da[ma]["nguon"].add(NGUON_POOL)
            continue
        if ma in tg.ma_cua_nhom or da_lam_truoc(tg.da_lam, ma, tg.ngay):
            continue
        if ma in sach_theo_ma:
            continue  # kênh/ video đã bị luật trên loại (lý do đã đếm)
        n_pool += 1
        da[ma] = {"ma": ma, "tieu_de": p.get("tieu_de", ""), "tieu_de_viet": "", "kenh_nguon": "", "nguon": {NGUON_POOL},
                  "view": None, "luc": tg.moc, "ngay_dang": "", "dai_phut": None, "tang_ngay": None,
                  "view_truoc": None, "tuyen_nhan": "", "mo_ta": "", "kenh_ro": 0, "da_lam_cot": ""}
    # Trang chủ máy ảo.
    for ma, r in tc_video.items():
        if ma in da:
            da[ma]["nguon"].add(NGUON_TRANG_CHU)
            continue
        if ma in tg.ma_cua_nhom or da_lam_truoc(tg.da_lam, ma, tg.ngay) or ma in sach_theo_ma:
            continue
        if str(r.get("Bị loại") or "").strip():
            bo_("trang chủ: bị loại khi lọc")
            continue
        ten = str(r.get("Kênh") or "").strip()
        o = vt.kenh.get(ten)
        if o is None:
            bo_("trang chủ: kênh ngoài sổ đối thủ")
            continue
        if not o["ok"]:
            bo_(o["ly_do"].split(" (")[0])
            continue
        g = c.phut(r.get("Dài"))
        if g is not None and g * 60 < GIAY_VIDEO_DAI:
            bo_("video ngắn < 4 phút")
            continue
        da[ma] = {"ma": ma, "tieu_de": str(r.get("Tiêu đề") or ""), "tieu_de_viet": "", "kenh_nguon": ten,
                  "nguon": {NGUON_TRANG_CHU}, "view": c.so(r.get("Lượt xem")),
                  "luc": c.epoch_luc(r.get("Lúc quét")) or tg.moc, "ngay_dang": str(r.get("Đăng") or "")[:10],
                  "dai_phut": g, "tang_ngay": None, "view_truoc": None, "tuyen_nhan": "", "mo_ta": "", "kenh_ro": 1,
                  "da_lam_cot": ""}
    vt.ung_vien = sorted(da.values(), key=lambda x: x["ma"])
    so_kenh = len(vt.kenh)
    so_kenh_dat = sum(1 for o in vt.kenh.values() if o["ok"])
    ly_kenh: Dict[str, int] = {}
    for o in vt.kenh.values():
        if not o["ok"]:
            k = o["ly_do"].split(" (")[0]
            ly_kenh[k] = ly_kenh.get(k, 0) + 1
    theo_nguon: Dict[str, int] = {}
    for u in vt.ung_vien:
        for n in u["nguon"]:
            theo_nguon[n] = theo_nguon.get(n, 0) + 1
    vt.thong_ke = {"n_sach": n_sach, "n_pool_ngoai_so": n_pool, "n_trang_chu_14n": len(tc_video),
                   "n_vu_tru": len(vt.ung_vien), "theo_nguon": theo_nguon, "kenh_so": so_kenh,
                   "kenh_theo_doi": sum(1 for o in vt.kenh.values() if o.get("trang_thai") == THEO_DOI),
                   "kenh_dat": so_kenh_dat, "kenh_bo": ly_kenh, "video_bo": dict(bo),
                   "san_kenh": next((o.get("san") for o in vt.kenh.values() if o.get("san") is not None), None)}
    return vt
