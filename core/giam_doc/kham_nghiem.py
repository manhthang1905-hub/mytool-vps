"""Khám nghiệm video — mốc 48h và 7 ngày (`workspace/THIET-KE-CONG-TY.md`, BẢN GỌN mục 1–2).

KHÔNG phải plugin (nằm trong `_KHONG_PHAI_VIEC`). Mã chỉ gom số, đặt giới hạn và ghi sổ; phần suy luận
(cổng nào hỏng, vì sao, nhãn theo NGHĨA, bài học) là của MỘT lượt LLM qua `quan_ly.goi_quyet`.

    can_kham(bs)                         [(video, moc)] chưa khám — ≤ 4/vòng, ≤ 2/video, video cũ trước
    ho_so_kham(goc, ma, bs, v, moc)      hồ sơ 0 đồng (chỉ đọc đĩa) + `so_lieu` {khoá nguồn: số}
    loi_nhac(hs, muc_tieu)               lời nhắc ngắn
    doc_ket_qua(tho, so_lieu)            JSON đã soát | None
    chay(goc, ma, bs, goi_chat)          khám + ghi `giam-doc/kham-nghiem/<vid>-<moc>.json`, `giam-doc/bai-hoc.jsonl`
    doc_bai_hoc(goc, ma)                 bài học gộp theo khoá (n = video ủng hộ − video phản; mâu thuẫn → không bơm)
    khoi_gan_day(goc, ma)                khối "KHÁM NGHIỆM GẦN ĐÂY" cho giám đốc kênh ("" nếu chưa có)

Mỗi số LLM trích phải kèm khoá nguồn (`so_dan: [{"so", "nguon"}]`, khoá lấy từ `so_lieu`) để hội đồng quyết
định sau này kiểm lại được; hôm nay chỉ gắn cờ `khop`.
"""

from __future__ import annotations

import datetime as _dt
import glob
import io
import json
import os
import re
import statistics
from typing import Any, Callable, Dict, List, Optional, Tuple

from .du_lieu import BangSo, ban_chup_gan, chu_so, ctr_trang_chu, moi_nhat, so, thu_muc_giam_doc, thu_muc_kenh

THU_MUC = "kham-nghiem"
TEP_BAI_HOC = "bai-hoc.jsonl"
TOI_DA_MOI_VONG = 4
TOI_DA_MOI_VIDEO = 2
TOI_DA_TOKEN = 2500
NGAY_BAI_HOC = 90
N_BOM = 3
#: mốc → (giờ chuẩn, khung tuổi bản chụp). Studio không chụp đúng giờ nên khung rộng hơn 44–85 / 144–240.
MOC = {"48h": (52.0, 40.0, 100.0), "7d": (168.0, 120.0, 260.0)}
CONG = ("hien_thi", "ctr", "giu_chan", "khong")
KIEU_TIEU_DE = ("so_dem", "hai_ve", "to_mo", "chan_dung", "cau_hoi", "khang_dinh", "khac")
KIEU_HOOK = ("nghich_ly", "cau_hoi", "so_lieu", "chan_dung", "ke_chuyen", "khac")
TRUC = ("tieu_de", "hook", "bia", "do_dai", "cum", "loi_moi_dk", "nguon", "giu_chan")
#: trục → khâu dùng bài (`dung_cho` của `chien_luoc.bai_hoc`): chọn content · tiêu đề/bìa · kịch bản.
DUNG_CHO = {"tieu_de": ["chon", "tieu_de"], "hook": ["kich_ban"], "bia": ["bia"], "do_dai": ["kich_ban", "chon"],
            "cum": ["chon", "bien_tap"], "loi_moi_dk": ["kich_ban"], "nguon": ["chon", "bien_tap"],
            "giu_chan": ["kich_ban"]}


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)


def _gon(x: Any, n: int) -> str:
    s = " ".join(str(x or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _tv(xs: List[Optional[float]]) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def _mmss(g: Optional[float]) -> str:
    if g is None:
        return "?"
    g = int(round(g))
    return "{0}:{1:02d}".format(g // 60, g % 60)


def thu_muc(goc: str, ma: str) -> str:
    return os.path.join(thu_muc_giam_doc(goc, ma), THU_MUC)


def do_dai_nhom(giay: Optional[float]) -> str:
    """Nhóm độ dài (phút) — mã gắn, không phải LLM."""
    if not giay:
        return "?"
    p = giay / 60.0
    for tran, ten in ((12, "<12"), (15, "12-15"), (18, "15-18"), (21, "18-21")):
        if p < tran:
            return ten
    return ">=21"


# ── chọn video cần khám ────────────────────────────────────────────────────

def da_kham(goc: str, ma: str) -> Dict[str, List[str]]:
    """{video_id: [moc…]} đã có tệp khám."""
    ra: Dict[str, List[str]] = {}
    for p in glob.glob(os.path.join(thu_muc(goc, ma), "*.json")):
        vid, _, moc = os.path.basename(p)[:-5].rpartition("-")
        if vid and moc in MOC:
            ra.setdefault(vid, []).append(moc)
    return ra


def moc_cua(v: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Mốc MUỘN nhất mà video có bản chụp hợp lệ: ("7d"|"48h", bản chụp) | None."""
    for moc in ("7d", "48h"):
        gio, lo, hi = MOC[moc]
        b = ban_chup_gan(v, gio, lo, hi)
        if b is not None:
            return moc, b
    return None


def can_kham(bs: BangSo, da: Optional[Dict[str, List[str]]] = None,
             toi_da: int = TOI_DA_MOI_VONG) -> List[Tuple[Dict[str, Any], str]]:
    """Video có bản chụp ở mốc muộn nhất chưa khám (mỗi video ≤ 2 lần đời), video cũ trước."""
    da = da_kham(bs.goc, bs.ma_kenh) if da is None else da
    ra = []
    for v in sorted(bs.video, key=lambda x: x.get("dang_luc") or _dt.datetime.min):
        m = moc_cua(v)
        cu = da.get(v["id"]) or []
        if m and m[0] not in cu and len(cu) < TOI_DA_MOI_VIDEO:
            ra.append((v, m[0]))
    return ra[:toi_da]


# ── hồ sơ (0 đồng) ─────────────────────────────────────────────────────────

_TRUONG = ("hien_thi", "ctr", "ctr_browse", "xem", "avd_pct", "avd_giay", "gx_1k", "pct_browse", "pct_de_xuat", "sub")


def _luot_cua(goc: str, ma: str, v: Dict[str, Any], hs_video: Dict[str, Any]) -> str:
    luot = str(hs_video.get("luot") or "")
    d = os.path.join(goc, "PROJECTS", "AUTO", ma, luot) if luot else ""
    if d and os.path.isdir(d):
        return d
    try:
        from ..chi_so_ytb import tim_luot_theo_tieu_de  # noqa: PLC0415

        return tim_luot_theo_tieu_de(v.get("tieu_de") or "", os.path.join(goc, "PROJECTS", "AUTO"))
    except Exception:  # noqa: BLE001
        return ""


def _giu_chan(thu_muc_video: str, moc_dir: str) -> Dict[str, Any]:
    """Đường giữ chân ở bản chụp của mốc (lùi về bản muộn nhất có retention) → giu_30s, giu_2p, vách."""
    from ..chi_so_ytb import gom  # noqa: PLC0415
    from ..chien_luoc import bai_hoc  # noqa: PLC0415

    r: List[float] = []
    dai = None
    p = os.path.join(thu_muc_video, moc_dir, "retention.xlsx")
    if moc_dir and os.path.isfile(p):
        r = [float(x) for x in gom.doc_retention(p) or []]
        dai = so((_doc_json(os.path.join(thu_muc_video, moc_dir, "tong-quan.json")) or {}).get("thoi_luong_giay"))
    if len(r) < 20:
        r, dai = bai_hoc._duong_giu_chan(thu_muc_video)  # noqa: SLF001 — bộ đọc sẵn có
    return dict(bai_hoc.do_duong_giu_chan(r, dai), _r=r)


def _pool(thu_muc_moc: str, n: int = 5) -> List[str]:
    from ..chi_so_ytb.gom import doc_csv  # noqa: PLC0415

    hang = [r for r in doc_csv(os.path.join(thu_muc_moc, "traffic-related.csv"))[2:] if len(r) > 5 and r[2]]
    hang.sort(key=lambda r: -(so(r[5]) or 0))
    return ["{0} ({1} view)".format(_gon(r[2], 60), chu_so(so(r[5]))) for r in hang[:n]]


def _bien_tap(goc: str, ma: str, ma_goi: str) -> Dict[str, Any]:
    """Nguồn + dự đoán của biên tập viên lúc chọn (sổ `tu-chay/<ngày>.json`, mới trước)."""
    if not ma_goi:
        return {}
    for p in sorted(glob.glob(os.path.join(thu_muc_kenh(goc, ma), "tu-chay", "*.json")), reverse=True):
        du = _doc_json(p)
        for run in (du.get("runs") or []) if isinstance(du, dict) else []:
            if isinstance(run, dict) and str((run.get("ban_giao") or {}).get("ma_goi") or "") == ma_goi:
                ng = run.get("nguon") or {}
                bt = ng.get("bien_tap") or {}
                return {"nguon_tieu_de": ng.get("tieu_de"), "nguon_view": ng.get("view"), "cong_thuc": ng.get("cong_thuc"),
                        "tham_do": ng.get("tham_do"), "hang": bt.get("hang"), "ly_do": _gon(bt.get("ly_do"), 300),
                        "du_doan": bt.get("du_doan") or {}}
    return {}


def _cau_quanh(srt: List[Tuple[float, float, str]], giay: Optional[float]) -> str:
    if giay is None or not srt:
        return ""
    i = next((k for k, (a, b, _t) in enumerate(srt) if a <= giay <= b or a > giay), len(srt) - 1)
    return " / ".join("[{0}] {1}".format(_mmss(a), _gon(t, 90)) for a, _b, t in srt[max(0, i - 1): i + 2])


def doc_binh_luan(goc: str, ma: str, vid: str) -> List[Dict[str, Any]]:
    du = _doc_json(os.path.join(thu_muc_kenh(goc, ma), "chi-so", vid, "binh-luan.json"))
    return [x for x in ((du.get("binh_luan") if isinstance(du, dict) else None) or []) if isinstance(x, dict)]


def binh_luan_that(goc: str, ma: str, vid: str, lang: str = "") -> int:
    """yt-dlp (mạng, 0 đồng) → `chi-so/<vid>/binh-luan.json`. Đã có thì thôi. Trả số bình luận."""
    cu = doc_binh_luan(goc, ma, vid)
    if cu:
        return len(cu)
    from ..trang_chu import binh_luan_video  # noqa: PLC0415

    ds = [{"like": int(lk or 0), "chu": _gon(c, 300)} for lk, c in binh_luan_video(vid, so=20, lang=lang)]
    _ghi_json(os.path.join(thu_muc_kenh(goc, ma), "chi-so", vid, "binh-luan.json"),
              {"video_id": vid, "luc": _dt.datetime.now().replace(microsecond=0).isoformat(), "binh_luan": ds})
    return len(ds)


def ho_so_kham(goc: str, ma: str, bs: BangSo, v: Dict[str, Any], moc: str,
               ban_chup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mọi thứ LLM cần về MỘT video ở `moc` — chỉ đọc đĩa. `so_lieu` = {khoá nguồn: số} (bảng LLM được trích)."""
    from .. import ho_so_video  # noqa: PLC0415
    from ..chi_so_ytb import _doc_srt, su_that_tu_luot  # noqa: PLC0415
    from . import so_thi_nghiem as stn  # noqa: PLC0415

    vid = v["id"]
    gio, lo, hi = MOC[moc]
    b = ban_chup or ban_chup_gan(v, gio, lo, hi) or moi_nhat(v) or {}
    nhan = "v:{0}/{1}".format(vid, b.get("moc", "?"))
    so_lieu: Dict[str, Any] = {"{0}/{1}".format(nhan, k): b[k] for k in _TRUONG if b.get(k) is not None}
    so_lieu[nhan + "/tuoi_gio"] = b.get("tuoi")
    tc = ctr_trang_chu(v, 36.0, max(hi, float(b.get("tuoi") or 0)))  # không phải bản chụp nào cũng có dòng Browse
    if tc and tc.get("moc") != b.get("moc"):
        so_lieu["v:{0}/{1}/ctr_browse".format(vid, tc["moc"])] = tc["ctr_browse"]
    khac = [x for x in (ban_chup_gan(o, gio, lo, hi) for o in bs.video if o["id"] != vid) if x]
    for k in _TRUONG:
        tv = _tv([x.get(k) for x in khac])
        if tv is not None:
            so_lieu["kenh/tv@{0}/{1}".format(moc, k)] = round(tv, 2)
    so_lieu["kenh/tv@{0}/n".format(moc)] = len(khac)
    for k, x in (("kenh/nguong_thang_48h", bs.nguong_thang_48h), ("kenh/ctr_trang_chu_muc_tieu", bs.ctr_muc_tieu),
                 ("v:{0}/hien_thi_48h".format(vid), v.get("hien_thi_48h")), ("v:{0}/sub_1k_view".format(vid), v.get("sub_1k"))):
        if x is not None:
            so_lieu[k] = round(x, 2)
    tmv = os.path.join(thu_muc_kenh(goc, ma), "chi-so", vid)
    try:
        gc = _giu_chan(tmv, str(b.get("moc") or ""))
    except Exception:  # noqa: BLE001
        gc = {}
    for k in ("giu_30s", "giu_2p", "vach_giay", "vach_rot"):
        if gc.get(k) is not None:
            so_lieu["v:{0}/giu/{1}".format(vid, k)] = gc[k]
    try:
        from ..chien_luoc import bai_hoc  # noqa: PLC0415

        dt = [d for d in bai_hoc.diem_thoat(goc, ma) if d["video_id"] != vid]
        for k in ("giu_30s", "giu_2p"):
            tv = _tv([d.get(k) for d in dt])
            if tv is not None:
                so_lieu["kenh/tv/giu/{0}".format(k)] = round(tv, 1)
    except Exception:  # noqa: BLE001
        pass
    hs_v = (ho_so_video.doc_ho_so(goc, ma, v["ma_goi"]) if v.get("ma_goi") else None) or {}
    luot = _luot_cua(goc, ma, v, hs_v)
    srt = _doc_srt(os.path.join(luot, "3-phu-de.srt")) if luot else []
    td, th, kb = hs_v.get("tieu_de_cham") or {}, hs_v.get("thumbnail") or {}, hs_v.get("kich_ban") or {}
    dd = next((d for d in stn.doc_du_doan(goc, ma) if d.get("video_id") == vid), {})
    chu = {
        "tieu_de": v.get("tieu_de"), "ngay_dang": v.get("ngay_dang"),
        "phut": round((v.get("dai_giay") or 0) / 60.0, 1) if v.get("dai_giay") else None,
        "cum": [bs.cum(c) for c in v.get("cum") or []], "cong_thuc": v.get("cong_thuc"),
        "ket_luan": v.get("ket_luan") or "chờ", "chu_bia": hs_v.get("chu_bia"),
        "bia": {"nhom": th.get("nhom"), "kieu": th.get("kieu"), "ly_do": _gon(th.get("ly_do"), 200)} if th else {},
        "kich_ban": {"ban_chon": kb.get("ban_chon"), "hook_chon": kb.get("hook_chon"), "ky_tu": kb.get("ky_tu_ban_chon")}
        if kb else {},
        "tieu_de_ung_vien": [_gon(u.get("tieu_de"), 80) for u in td.get("ung_vien") or [] if isinstance(u, dict)][:5],
        "tieu_de_ly_do": _gon(td.get("ly_do"), 240),
        "hook_30s": _gon(" ".join(t for a, _b, t in srt if a < 30), 320),
        "cau_tai_vach": _cau_quanh(srt, gc.get("vach_giay")), "vach": gc.get("vach") or "",
        "su_that_luot": su_that_tu_luot(luot, gc.get("_r") or None) if luot else [],
        "pool": _pool(os.path.join(tmv, str(b.get("moc")))) if b.get("moc") else [],
        "binh_luan": ["({0}) {1}".format(c.get("like"), _gon(c.get("chu"), 120)) for c in doc_binh_luan(goc, ma, vid)[:8]]
        if moc == "7d" else [],
        "du_doan_giam_doc": {k: dd.get(k) for k in ("ket", "ly_do", "ket_that") if dd.get(k)},
        "bien_tap": _bien_tap(goc, ma, v.get("ma_goi") or ""),
    }
    return {"video_id": vid, "moc": moc, "ban_chup": b.get("moc"), "so_lieu": so_lieu, "chu": chu,
            "nhan_ma": {"do_dai_nhom": do_dai_nhom(v.get("dai_giay")), "kieu_bia": str(th.get("nhom") or "khac")},
            "luot": os.path.basename(luot) if luot else ""}


# ── lời nhắc + đọc kết quả ─────────────────────────────────────────────────

DANG_TRA_LOI = """\
Chỉ trả MỘT khối JSON:
{"chan_doan": "≤ 3 câu, có số: cổng nào mạnh, cổng nào hỏng so với trung vị kênh cùng tuổi",
 "cong_hong": "hien_thi|ctr|giu_chan|khong",
 "vi_sao": "1–2 câu: vì sao (tiêu đề / bìa / hook / chỗ thoát / nguồn / cụm) — dựa trên chữ ở trên",
 "du_doan_lech": "1 câu: dự đoán lúc chọn (biên tập viên / giám đốc) lệch thật ở đâu; không có thì \\"\\"",
 "nhan": {"kieu_tieu_de": "so_dem|hai_ve|to_mo|chan_dung|cau_hoi|khang_dinh|khac",
          "kieu_hook": "nghich_ly|cau_hoi|so_lieu|chan_dung|ke_chuyen|khac"},
 "bai_hoc": {"truc": "tieu_de|hook|bia|do_dai|cum|loi_moi_dk|nguon|giu_chan",
             "gia_tri": "giá trị ngắn trên trục (vd so_dem, 15-18, mã cụm)",
             "huong": "+ (nên làm thêm) | - (nên tránh)", "cum": "mã cụm nếu bài chỉ đúng cho cụm đó, không thì \\"\\"",
             "cau": "1 câu có số, người làm video hiểu được"},
 "so_dan": [{"so": 7.37, "nguon": "<khoá trong SỐ LIỆU>"}]}"""


def loi_nhac(hs: Dict[str, Any], muc_tieu: str = "", ma: str = "") -> str:
    """Lời nhắc ngắn (~2–3k token): mục tiêu + số + chữ + dạng trả lời."""
    c = hs["chu"]
    dong = [
        "Bạn khám nghiệm MỘT video YouTube của kênh {0} ở mốc {1} (bản chụp {2}). View = Hiển thị × CTR × Giữ chân: "
        "so với trung vị kênh CÙNG TUỔI, tìm cổng hỏng và vì sao, rồi rút ĐÚNG MỘT bài học có số cho video sau "
        "(chọn content · tiêu đề/bìa · kịch bản giữ chân).".format(ma, hs["moc"], hs.get("ban_chup")),
        "MỤC TIÊU KÊNH\n" + (muc_tieu or "(không khai)"),
        "SỐ LIỆU (khoá = giá trị; mỗi số bạn dùng phải ghi lại kèm khoá trong so_dan; tv@ = trung vị kênh cùng tuổi; "
        "ctr = CTR mọi nguồn, ctr_browse = CTR trang chủ, gx_1k = giờ xem/1.000 hiển thị, giu_30s/giu_2p = % người "
        "còn lại)\n" + "\n".join("{0} = {1}".format(k, x) for k, x in hs["so_lieu"].items()),
        "VIDEO\n" + json.dumps({k: c[k] for k in ("tieu_de", "ngay_dang", "phut", "cum", "cong_thuc", "ket_luan",
                                                    "chu_bia", "bia", "kich_ban")}, ensure_ascii=False),
        "TIÊU ĐỀ ĐÃ CHẤM (ứng viên lúc làm): " + (" / ".join(c["tieu_de_ung_vien"]) or "—")
        + ("\nLý do chọn: " + c["tieu_de_ly_do"] if c["tieu_de_ly_do"] else ""),
        "30 GIÂY ĐẦU (hook): " + (c["hook_30s"] or "—"),
        "CÂU KỊCH BẢN Ở CHỖ NGƯỜI XEM THOÁT NHIỀU NHẤT ({0}): {1}".format(c["vach"] or "?", c["cau_tai_vach"] or "—"),
        "SỰ THẬT TỪ LƯỢT: " + ("; ".join(c["su_that_luot"]) or "—"),
        "POOL ĐỀ XUẤT (video kéo view sang): " + (" | ".join(c["pool"]) or "—"),
        "NGUỒN + DỰ ĐOÁN LÚC CHỌN: " + (json.dumps(c["bien_tap"], ensure_ascii=False) if c["bien_tap"] else "—")
        + ("\nGiám đốc kênh đã đoán: " + json.dumps(c["du_doan_giam_doc"], ensure_ascii=False)
           if c["du_doan_giam_doc"] else ""),
    ]
    if c["binh_luan"]:
        dong.append("BÌNH LUẬN (like):\n" + "\n".join(c["binh_luan"]))
    dong.append("LUẬT: chỉ dùng số trong SỐ LIỆU; mẫu là MỘT video nên câu bài học nói rõ đó là quan sát một video; "
                "nhãn theo NGHĨA của tiêu đề / 30 giây đầu, không theo từ khoá.")
    dong.append(DANG_TRA_LOI)
    return "\n\n".join(dong)


def _co_so(s: Any) -> bool:
    return bool(re.search(r"\d", str(s or "")))


def _chon(x: Any, ds: Tuple[str, ...]) -> str:
    x = str(x or "").strip().lower()
    return x if x in ds else "khac"


def doc_ket_qua(tho: str, so_lieu: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Câu trả lời thô → kết quả đã soát | None (chẩn đoán không có số / sai dạng). Bài học thiếu số, trục lạ
    hoặc hướng lạ → `bai_hoc = None` (vẫn giữ chẩn đoán)."""
    from ..goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return None
    if not isinstance(du, dict) or not _co_so(du.get("chan_doan")):
        return None
    so_lieu = so_lieu or {}
    dan = []
    for x in du.get("so_dan") or []:
        if isinstance(x, dict) and str(x.get("nguon") or "").strip():
            k, s = str(x["nguon"]).strip(), so(x.get("so"))
            g = so(so_lieu.get(k))
            dan.append({"so": s, "nguon": k,
                        "khop": bool(g is not None and s is not None and abs(g - s) <= max(0.05, abs(g) * 0.01))})
    nh = du.get("nhan") if isinstance(du.get("nhan"), dict) else {}
    bh = du.get("bai_hoc") if isinstance(du.get("bai_hoc"), dict) else {}
    huong = str(bh.get("huong") or "").strip()[:1]
    bai = None
    if str(bh.get("truc") or "") in TRUC and _co_so(bh.get("cau")) and huong in ("+", "-") and str(bh.get("gia_tri") or "").strip():
        bai = {"truc": str(bh["truc"]), "gia_tri": _gon(bh["gia_tri"], 40).lower(), "huong": huong,
               "cum": _gon(bh.get("cum"), 40), "cau": _gon(bh["cau"], 260)}
    cong = str(du.get("cong_hong") or "").strip().lower()
    return {"chan_doan": _gon(du.get("chan_doan"), 600), "cong_hong": cong if cong in CONG else "khong",
            "vi_sao": _gon(du.get("vi_sao"), 400), "du_doan_lech": _gon(du.get("du_doan_lech"), 300),
            "nhan": {"kieu_tieu_de": _chon(nh.get("kieu_tieu_de"), KIEU_TIEU_DE),
                     "kieu_hook": _chon(nh.get("kieu_hook"), KIEU_HOOK)},
            "bai_hoc": bai, "so_dan": dan[:16]}


# ── chạy + ghi ─────────────────────────────────────────────────────────────

def _doc_dong(duong: str) -> List[Dict[str, Any]]:
    ra = []
    try:
        with io.open(duong, encoding="utf-8") as tep:
            for dong in tep:
                try:
                    d = json.loads(dong)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    ra.append(d)
    except OSError:
        pass
    return ra


def _ghi_bai_hoc(goc: str, ma: str, dong_moi: Optional[Dict[str, Any]], vid: str, moc: str) -> None:
    """Viết lại sổ: bỏ dòng cũ cùng (video, mốc), thêm dòng mới — khám lại không nhân đôi phiếu."""
    duong = os.path.join(thu_muc_giam_doc(goc, ma), TEP_BAI_HOC)
    ds = [d for d in _doc_dong(duong) if not (d.get("video_id") == vid and d.get("moc") == moc)]
    if dong_moi:
        ds.append(dong_moi)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8", newline="\n") as tep:
        tep.write("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in ds))
    os.replace(duong + ".tam", duong)


def kham_mot(goc: str, ma: str, bs: BangSo, v: Dict[str, Any], moc: str, goi_chat: Optional[Callable[..., str]], *,
             ghi_tep: bool = True, ban_chup: Optional[Dict[str, Any]] = None,
             ghi: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Khám một video: hồ sơ → 1 lượt LLM (`quan_ly.goi_quyet`) → ghi. Trả bản khám (`ket` None + `loi` nếu hỏng)."""
    from . import gioi_han, quan_ly  # noqa: PLC0415

    hs = ho_so_kham(goc, ma, bs, v, moc, ban_chup=ban_chup)
    ln = loi_nhac(hs, bs.muc_tieu, ma)
    luc = bs.bay_gio.replace(microsecond=0).isoformat()
    q = quan_ly.goi_quyet("kham_nghiem", ln, hs["so_lieu"], goi_chat, doc=lambda t: doc_ket_qua(t, hs["so_lieu"]),
                          goc=goc, ma=ma, khoa="kham-{0}-{1}-{2}".format(ma, v["id"], moc), toi_da_token=TOI_DA_TOKEN,
                          ghi=ghi)
    ket = q["ket"]
    ban = {"video_id": v["id"], "moc": moc, "luc": luc, "mo_hinh": q["mo_hinh"], "loi": q["loi"],
           "bong": gioi_han.che_do(bs) != "tu_ap", "ket_luan": v.get("ket_luan") or "",
           "hien_thi_48h": v.get("hien_thi_48h"), "ket": ket,
           "nhan": dict(ket["nhan"], **hs["nhan_ma"]) if ket else {}, "ho_so": hs, "loi_nhac": ln}
    if ghi_tep and ket is not None:
        _ghi_json(os.path.join(thu_muc(goc, ma), "{0}-{1}.json".format(v["id"], moc)),
                  {k: x for k, x in ban.items() if k != "loi_nhac"})
        bh = ket.get("bai_hoc")
        _ghi_bai_hoc(goc, ma, dict(bh, khoa="{0}|{1}|{2}|{3}".format(bh["truc"], bh["gia_tri"], bh["huong"], bh["cum"]),
                                   video_id=v["id"], moc=moc, so_dan=ket.get("so_dan") or [], bong=ban["bong"], luc=luc)
                     if bh else None, v["id"], moc)
    return ban


def chay(goc: str, ma: str, bs: BangSo, goi_chat: Optional[Callable[..., str]], *,
         lay_binh_luan: Optional[Callable[..., int]] = None, ghi: Optional[Callable[[str], None]] = None,
         toi_da: int = TOI_DA_MOI_VONG) -> List[Dict[str, Any]]:
    """Một vòng khám (≤ 4 video). `lay_binh_luan` (mạng, 0 đồng) chỉ truyền khi gọi AI thật."""
    if goi_chat is None:
        return []
    ra = []
    for v, moc in can_kham(bs, toi_da=toi_da):
        if moc == "7d" and lay_binh_luan is not None:
            try:
                lay_binh_luan(goc, ma, v["id"], str(bs.cai.get("ngon_ngu") or ""))
            except Exception as loi:  # noqa: BLE001 — không có bình luận vẫn khám được
                if ghi:
                    ghi("  [khám nghiệm] không lấy được bình luận {0}: {1}".format(v["id"], str(loi)[:80]))
        try:
            ra.append(kham_mot(goc, ma, bs, v, moc, goi_chat, ghi=ghi))
        except Exception as loi:  # noqa: BLE001 — một video hỏng không chặn video khác
            ra.append({"video_id": v["id"], "moc": moc, "ket": None,
                       "loi": "{0}: {1}".format(type(loi).__name__, str(loi)[:160])})
    return ra


# ── đọc lại: bài học, khối cho giám đốc kênh ──────────────────────────────

def doc_bai_hoc(goc: str, ma: str, *, ngay: int = NGAY_BAI_HOC, bay_gio: Optional[_dt.datetime] = None,
                bo_bong: bool = False) -> List[Dict[str, Any]]:
    """Gộp `bai-hoc.jsonl` theo (trục, giá trị, cụm): n = số video ủng hộ hướng đa số − số video phản.
    `bom` = n ≥ 3, không mâu thuẫn, không bóng (`bo_bong=True`: coi bài bóng như thật — giám đốc `tu_ap`)."""
    tu = ((bay_gio or _dt.datetime.now()) - _dt.timedelta(days=ngay)).isoformat()
    nhom: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for d in _doc_dong(os.path.join(thu_muc_giam_doc(goc, ma), TEP_BAI_HOC)):
        if str(d.get("luc") or "") >= tu and d.get("truc") in TRUC and d.get("video_id") and _co_so(d.get("cau")):
            nhom.setdefault((d["truc"], str(d.get("gia_tri") or ""), str(d.get("cum") or "")), []).append(d)
    ra = []
    for (truc, gt, cum), ds in nhom.items():
        theo = {h: {x["video_id"] for x in ds if x.get("huong") == h} for h in ("+", "-")}
        huong = "+" if len(theo["+"]) >= len(theo["-"]) else "-"
        ung, phan = theo[huong], theo["-" if huong == "+" else "+"]
        cung = sorted((x for x in ds if x.get("huong") == huong), key=lambda x: str(x.get("luc")))
        bong = all(x.get("bong") for x in cung) and not bo_bong
        n = len(ung) - len(phan)
        ra.append({"truc": truc, "gia_tri": gt, "cum": cum, "huong": huong, "n": n, "ung": len(ung), "phan": len(phan),
                   "mau_thuan": bool(phan), "bong": bong, "video": sorted(ung), "cau": cung[-1]["cau"],
                   "khoa": "{0}|{1}|{2}|{3}".format(truc, gt, huong, cum), "dung_cho": DUNG_CHO.get(truc, ["bien_tap"]),
                   "bom": n >= N_BOM and not phan and not bong})
    ra.sort(key=lambda b: (-b["n"], b["truc"]))
    return ra


def doc_kham(goc: str, ma: str) -> List[Dict[str, Any]]:
    """Bản khám MỚI NHẤT của mỗi video (mốc 7d thắng 48h), mới → cũ."""
    theo: Dict[str, Dict[str, Any]] = {}
    for p in glob.glob(os.path.join(thu_muc(goc, ma), "*.json")):
        du = _doc_json(p)
        if not isinstance(du, dict) or not du.get("ket"):
            continue
        cu = theo.get(du.get("video_id"))
        if cu is None or (du.get("moc") == "7d", str(du.get("luc"))) > (cu.get("moc") == "7d", str(cu.get("luc"))):
            theo[du["video_id"]] = du
    return sorted(theo.values(), key=lambda d: str(d.get("luc")), reverse=True)


def bang_nhan(ds: List[Dict[str, Any]], ket_luan_cua: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Dict[str, int]]]:
    """{nhãn: {giá trị: {n, thang, truot}}} — kết luận HIỆN TẠI (`ket_luan_cua`) thắng kết luận lúc khám."""
    ra: Dict[str, Dict[str, Dict[str, int]]] = {}
    for d in ds:
        kl = (ket_luan_cua or {}).get(d["video_id"]) or d.get("ket_luan") or ""
        for nhan, gt in (d.get("nhan") or {}).items():
            o = ra.setdefault(nhan, {}).setdefault(str(gt), {"n": 0, "thang": 0, "truot": 0})
            o["n"] += 1
            o["thang"] += kl == "thang"
            o["truot"] += kl == "truot"
    return ra


def khoi_gan_day(goc: str, ma: str, *, ket_luan_cua: Optional[Dict[str, str]] = None, toi_da: int = 5) -> str:
    """Khối "KHÁM NGHIỆM GẦN ĐÂY" cho lời nhắc giám đốc kênh — "" khi chưa có bản khám nào."""
    ds = doc_kham(goc, ma)
    if not ds:
        return ""
    kl = ket_luan_cua or {}
    dong = ["- {0} @{1} [{2}, cổng hỏng: {3}]: {4}".format(
        d["video_id"], d["moc"], kl.get(d["video_id"]) or d.get("ket_luan") or "chờ", d["ket"].get("cong_hong"),
        _gon(d["ket"].get("chan_doan"), 260)) for d in ds[:toi_da]]
    bang = bang_nhan(ds, kl)
    for nhan in ("kieu_tieu_de", "kieu_hook", "kieu_bia", "do_dai_nhom"):
        if bang.get(nhan):
            dong.append("  {0}: ".format(nhan) + " · ".join("{0} {1} video (thắng {2}, trượt {3})".format(
                gt, x["n"], x["thang"], x["truot"]) for gt, x in sorted(bang[nhan].items(), key=lambda kv: -kv[1]["n"])))
    for b in [b for b in doc_bai_hoc(goc, ma) if b["n"] >= 1][:4]:
        dong.append("  bài học {0} (n={1}{2}{3}): {4}".format(b["khoa"], b["n"], ", mâu thuẫn" if b["mau_thuan"] else "",
                                                          ", bóng" if b["bong"] else "", _gon(b["cau"], 200)))
    return ("KHÁM NGHIỆM GẦN ĐÂY ({0} video — nhóm nhãn nào thắng/thua trong kênh; muốn đổi \"chuẩn\" thì chọn trong "
            "THỰC ĐƠN: luat_chon_tuan, phut_muc_tieu, chien_luoc, chỉ đạo — sửa câu được; n < 3 là tín hiệu yếu)\n"
            .format(len(ds)) + "\n".join(dong))
