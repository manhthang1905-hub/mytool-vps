"""Một chỗ đọc bài học — mục 3a + 3b `workspace/THIET-KE-CHIEN-LUOC.md` (B4, 30/09/2026).

    doc(goc, ma_kenh, dung_cho, toi_da=8)      -> list[BaiHoc]
    khoi_chu(goc, ma_kenh, dung_cho, toi_da=8) -> str   (khối chữ gọn cho lời nhắc)
    diem_thoat(goc, ma_kenh)                   -> list[dict]  (giữ chân từng video, nối về nguồn)
    khoi_nguon_giu_roi(goc, ma_kenh)           -> str   (nguồn của video giữ tốt / rơi sớm)

    BaiHoc = {pham_vi: "kenh"|"nhom"|"ngoai", truc, cum, cau (≤ 2 câu, có số), n, tin_cay,
              dung_cho: [...], bom (n ≥ 3), muc_tieu? (trục ctr_trang_chu)}

KHÔNG dời tệp nào — chỉ gộp các nguồn có sẵn thành một danh sách chuẩn:

  kênh  · `bai-hoc-san-xuat.json` (tiêu đề/cụm, CTR trang chủ, sub/1k, độ dài/AVD, bìa)
        · `bien-tap/danh-gia.json:bai_hoc` (biên tập viên tự sửa mình, n = số lần đã chấm)
        · `ket_qua.thong_ke` (kết quả theo công thức)
        · điểm thoát (`diem_thoat`: `retention.xlsx` — đúng đường `BanGhi.retention` — nối về nguồn
          qua `ho_so_video.nguon_cua_goi`)
        · bảng thắng/trượt theo cụm của chính kênh (`cong_thuc_v7.video_cua_kenh`, ngưỡng kênh)
        · khám nghiệm video (`giam-doc/bai-hoc.jsonl` qua `giam_doc.kham_nghiem.doc_bai_hoc`: gộp theo khoá,
          n = video ủng hộ − video phản; mâu thuẫn hoặc bóng → không bơm)
        · mục tiêu CTR trang chủ (trung vị video thắng, lùi về trung vị kênh)
  nhóm  · `_NHOM/<nhóm>/INSIGHT-CHON-CONTENT.md` (từng mục) và bảng thắng/trượt theo cụm của các
          kênh anh em (`bang-nhom.csv`, so với trung vị của CHÍNH kênh anh em đó)
  ngoài · `_NHOM/<nhóm>/bai-hoc-ngoai/*.json` (bài VPS khác xuất ra — tiên nghiệm yếu nhất)

Luật phạm vi (theo từng TRỤC = (truc, cum)):
  * bài KÊNH luôn đứng trước;
  * bài NHÓM chỉ vào khi kênh có n < 3 trên đúng trục đó — kèm nhãn "(tiên nghiệm nhóm — kênh chưa
    có số riêng)";
  * bài NGOÀI chỉ vào khi kênh có n = 0 trên trục đó;
  * n < 3 → chỉ ghi cho người đọc (`bom=False`), `khoi_chu` không bơm (đúng `NGUONG_VUA`).

Chỉ đọc đĩa, 0 đồng, không gọi mạng; mỗi nguồn tự `try`, hỏng nguồn nào thì thiếu nguồn đó.
Chưa khâu sống nào gọi module này (B5 nối vào biên tập viên); `NguCanh.bai_hoc` đọc lười qua `doc`.
"""

from __future__ import annotations

import csv
import datetime as _dt
import glob
import io
import json
import os
import re
import statistics
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PHAM_VI = ("kenh", "nhom", "ngoai")
DUNG_CHO = ("chon", "bien_tap", "kich_ban", "tieu_de", "bia")
NGUONG_VUA = 3          # = bai_hoc_san_xuat.NGUONG_VUA — dưới ngưỡng này không bơm vào lời nhắc
NGUONG_CAO = 6
LECH_GIU_CHAN = 8.0     # điểm % — "rơi sớm"/"giữ tốt" so với trung vị kênh ở 2:00
NHAN_NHOM = " (tiên nghiệm nhóm — kênh chưa có số riêng)"
NHAN_NGOAI = " (bài học ngoài — tiên nghiệm yếu nhất, kênh chưa có số)"
#: Trục đứng đầu trong cùng phạm vi — mục tiêu CTR trang chủ là dòng 3 của `NguCanh.muc_tieu()`,
#: phải lọt vào `doc(..., toi_da=8)` dù n nhỏ hơn các trục khác.
_UU_TIEN = {"ctr_trang_chu": 0}

#: trục của `bai-hoc-san-xuat.json` → khâu dùng được.
_DUNG_CHO_SAN_XUAT = {
    "tieu_de_cum": ["chon", "tieu_de"],
    "ctr_browse_48h": ["chon", "tieu_de", "bia"],
    "sub_1k_view": ["chon"],
    "do_dai_avd": ["kich_ban"],
    "thumbnail_ctr": ["bia"],
}


# ── tiện ích ────────────────────────────────────────────────────────────────

def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _so(x: Any) -> Optional[float]:
    try:
        return float(str(x).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _pct(x: Optional[float]) -> str:
    return "?" if x is None else "{0:.0f}%".format(x)


def _mmss(giay: Optional[float]) -> str:
    if giay is None:
        return "?"
    g = int(round(giay))
    return "{0}:{1:02d}".format(g // 60, g % 60)


def _hai_cau(chu: Any, toi_da: int = 240) -> str:
    """Tối đa 2 câu, tối đa `toi_da` ký tự."""
    s = " ".join(str(chu or "").split())
    cau = re.split(r"(?<=[.!?。！？])\s+", s)
    s = " ".join(cau[:2])
    return s if len(s) <= toi_da else s[:toi_da - 1].rstrip() + "…"


def _tin_cay(n: int) -> str:
    return "cao" if n >= NGUONG_CAO else "vua" if n >= NGUONG_VUA else "thap"


def _bh(pham_vi: str, truc: str, cau: str, n: int, dung_cho: Sequence[str], cum: str = "",
        **them: Any) -> Dict[str, Any]:
    n = int(n or 0)
    ra = {"pham_vi": pham_vi, "truc": truc, "cum": cum, "cau": _hai_cau(cau), "n": n,
          "tin_cay": _tin_cay(n), "dung_cho": list(dung_cho), "bom": n >= NGUONG_VUA}
    ra.update(them)
    return ra


def _duong_kenh(goc: str, ma_kenh: str = "") -> str:
    from ..kenh import duong_kenh  # noqa: PLC0415

    return duong_kenh(goc, ma_kenh)


def _nghien_cuu(goc: str, ma_kenh: str) -> str:
    from ..doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    return thu_muc_nghien_cuu(goc, ma_kenh)


def _nhom(goc: str, ma_kenh: str) -> str:
    try:
        from ..kenh import TEP_KENH, doc_yaml  # noqa: PLC0415

        return str((doc_yaml(os.path.join(_duong_kenh(goc, ma_kenh), TEP_KENH)) or {})
                   .get("nhom") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _thu_muc_nhom(goc: str, nhom: str) -> str:
    return os.path.join(_duong_kenh(goc), "_NHOM", nhom)


def _cau_hinh_v7(goc: str, ma_kenh: str) -> Dict[str, Any]:
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415

    ch, _ = v7.nap_cau_hinh(goc, ma_kenh, ghi_neu_thieu=False)
    v7.nap_phan_cum(goc, ma_kenh, ch)
    return ch


def _video_v7(goc: str, ma_kenh: str) -> Tuple[List[Any], Optional[float]]:
    from . import ket_qua  # noqa: PLC0415

    theo_id, nguong = ket_qua.video_kenh(goc, ma_kenh)
    return list(theo_id.values()), nguong


# ── 3b. điểm thoát ──────────────────────────────────────────────────────────

def _moc_gio(ten: str) -> Optional[int]:
    m = re.fullmatch(r"(\d+)h", ten)
    return int(m.group(1)) if m else None


def _duong_giu_chan(thu_muc_video: str) -> Tuple[List[float], Optional[float]]:
    """(`retention` 100 điểm %, thời lượng giây) của bản chụp MUỘN NHẤT có `retention.xlsx` —
    cùng bộ đọc `chi_so_ytb.gom.doc_retention` mà `BanGhi.retention` dùng, chỉ đọc."""
    try:
        con = sorted((c for c in os.listdir(thu_muc_video) if _moc_gio(c) is not None),
                     key=lambda c: -int(_moc_gio(c) or 0))
    except OSError:
        return [], None
    from ..chi_so_ytb import gom  # noqa: PLC0415

    for c in con:
        duong = os.path.join(thu_muc_video, c)
        if not os.path.isfile(os.path.join(duong, "retention.xlsx")):
            continue
        r = gom.doc_retention(os.path.join(duong, "retention.xlsx"))
        if len(r) < 20:
            continue
        tq = _doc_json(os.path.join(duong, "tong-quan.json")) or {}
        tt = _doc_json(os.path.join(duong, "_thong-tin.json")) or {}
        dai = _so(tq.get("thoi_luong_giay")) or _so(tt.get("thoi_luong"))
        return [float(x) for x in r], dai
    return [], None


def do_duong_giu_chan(r: Sequence[float], dai: Optional[float]) -> Dict[str, Any]:
    """`giu_30s`, `giu_2p` (% còn lại) và VÁCH — đoạn rơi dốc nhất (cửa sổ 3 điểm) sau 5% đầu,
    trước 10% cuối (màn kết)."""
    ra: Dict[str, Any] = {"giu_30s": None, "giu_2p": None, "vach_giay": None, "vach": "", "vach_rot": None}
    if not r or not dai or dai <= 0:
        return ra
    so = len(r)

    def tai(giay: float) -> Optional[float]:
        if giay >= dai:
            return None
        return round(float(r[min(so - 1, int(giay / dai * so))]), 1)

    ra["giu_30s"], ra["giu_2p"] = tai(30), tai(120)
    dau = max(1, int(round(so * 0.05)))
    cuoi = int(so * 0.9)  # 10% cuối là màn kết — ai cũng rơi ở đó, không phải "vách" của nội dung
    tot: Optional[Tuple[float, int]] = None
    for i in range(dau, max(dau, cuoi - 3)):
        rot = float(r[i]) - float(r[i + 3])
        if tot is None or rot > tot[0]:
            tot = (rot, i)
    if tot is not None and tot[0] > 0:
        giay = (tot[1] + 1.5) / so * dai
        ra.update(vach_giay=round(giay), vach=_mmss(giay), vach_rot=round(tot[0], 1))
    return ra


def diem_thoat(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    """Mỗi video của kênh có đường giữ chân: `{video_id, tieu_de, cum[], giu_30s, giu_2p, vach, vach_rot,
    ma_goi, nguon{link, ma, tieu_de}, nhom: "roi_som"|"giu_tot"|""}` — `nhom` so với TRUNG VỊ `giu_2p`
    của kênh ± `LECH_GIU_CHAN` điểm."""
    try:
        ds, _ng = _video_v7(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return []
    try:
        from . import ket_qua  # noqa: PLC0415
        from .. import ho_so_video  # noqa: PLC0415

        goi_theo_id = {str(h.get("video_id")): g for g, h in ket_qua.ho_so_theo_goi(goc, ma_kenh).items()
                       if h.get("video_id")}
        so_luot = ho_so_video.nguon_cua_goi(goc, ma_kenh) if goi_theo_id else {}
    except Exception:  # noqa: BLE001
        goi_theo_id, so_luot = {}, {}
    thu_muc = os.path.join(_duong_kenh(goc, ma_kenh), "chi-so")
    ra: List[Dict[str, Any]] = []
    for v in ds:
        r, dai = _duong_giu_chan(os.path.join(thu_muc, v.ma))
        do = do_duong_giu_chan(r, dai)
        if do["giu_30s"] is None and do["giu_2p"] is None:
            continue
        ma_goi = goi_theo_id.get(v.ma, "")
        ng = so_luot.get(ma_goi) or {}
        ra.append(dict(do, video_id=v.ma, tieu_de=v.tieu_de, cum=list(v.cum or []),
                       thoi_luong_giay=dai, ma_goi=ma_goi,
                       nguon={k: ng.get(k, "") for k in ("link", "ma", "tieu_de")} if ng else {},
                       nhom=""))
    hai = [d["giu_2p"] for d in ra if d["giu_2p"] is not None]
    if hai:
        tv = statistics.median(hai)
        for d in ra:
            if d["giu_2p"] is None:
                continue
            if d["giu_2p"] <= tv - LECH_GIU_CHAN:
                d["nhom"] = "roi_som"
            elif d["giu_2p"] >= tv + LECH_GIU_CHAN:
                d["nhom"] = "giu_tot"
    return ra


def _bai_giu_chan(dt: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    hai = [d["giu_2p"] for d in dt if d["giu_2p"] is not None]
    if not hai:
        return []
    tv2 = statistics.median(hai)
    ba = [d["giu_30s"] for d in dt if d["giu_30s"] is not None]
    vach = [d["vach_giay"] for d in dt if d.get("vach_giay") is not None]
    ra = [_bh("kenh", "giu_chan", "Kênh: trung vị còn {0} ở 0:30 và {1} ở 2:00; vách rơi dốc nhất thường "
              "quanh {2} (n={3}).".format(_pct(statistics.median(ba)) if ba else "?", _pct(tv2),
                                          _mmss(statistics.median(vach)) if vach else "?", len(hai)),
              len(hai), ["chon", "kich_ban", "bien_tap"])]
    theo_cum: Dict[str, List[float]] = {}
    for d in dt:
        if d["giu_2p"] is None:
            continue
        for c in d["cum"] or []:
            theo_cum.setdefault(c, []).append(d["giu_2p"])
    for c, xs in sorted(theo_cum.items()):
        ra.append(_bh("kenh", "giu_chan", "cụm {0}: còn {1} ở 2:00 (kênh trung vị {2}, n={3}).".format(
            c, _pct(statistics.median(xs)), _pct(tv2), len(xs)), len(xs), ["chon", "kich_ban", "bien_tap"],
            cum=c))
    return ra


def khoi_nguon_giu_roi(goc: str, ma_kenh: str, toi_da: int = 3, ky_tu_mo_dau: int = 300) -> str:
    """Khối cho biên tập viên: nguồn của video GIỮ TỐT / RƠI SỚM — tiêu đề nguồn, 300 ký tự mở đầu
    lời thoại nguồn (kho lời thoại), % còn lại ở 0:30/2:00 và vách. So cấu trúc/mở đầu THEO NGHĨA là
    việc của biên tập viên (LLM) — ở đây không so khớp gì. Chưa nối được nguồn nào → `""`."""
    try:
        dt = diem_thoat(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return ""
    try:
        from .. import loi_thoai  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        loi_thoai = None  # type: ignore[assignment]
    dong: List[str] = []
    for nhom, nhan in (("giu_tot", "GIỮ TỐT"), ("roi_som", "RƠI SỚM")):
        chon = sorted((d for d in dt if d["nhom"] == nhom and d.get("nguon")),
                      key=lambda d: d["giu_2p"], reverse=(nhom == "giu_tot"))[:toi_da]
        for d in chon:
            ng = d["nguon"]
            mo_dau = ""
            if loi_thoai is not None and ng.get("ma"):
                try:
                    ban = loi_thoai.doc(goc, ma_kenh, ng["ma"]) or {}
                    mo_dau = " ".join(str(ban.get("text") or "").split())[:ky_tu_mo_dau]
                except Exception:  # noqa: BLE001
                    mo_dau = ""
            dong.append("- [{0}] video “{1}” ← nguồn “{2}”: còn {3} @0:30 · {4} @2:00 · vách {5}{6}{7}".format(
                nhan, (d["tieu_de"] or d["video_id"])[:80], (ng.get("tieu_de") or ng.get("ma") or "?")[:80],
                _pct(d["giu_30s"]), _pct(d["giu_2p"]), d["vach"] or "?",
                " (−{0:g} điểm)".format(d["vach_rot"]) if d.get("vach_rot") else "",
                "\n  mở đầu lời thoại nguồn: “{0}”".format(mo_dau) if mo_dau else ""))
    return "\n".join(dong)


# ── nguồn KÊNH ───────────────────────────────────────────────────────────────

def _tu_san_xuat(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    from .. import bai_hoc_san_xuat as bhsx  # noqa: PLC0415

    ra = []
    for b in bhsx.doc_bai_hoc(goc, ma_kenh):
        if "mâu thuẫn với lần trước" in b.quan_sat:
            b_cau = b.quan_sat.split(" (mâu thuẫn")[0] + " (đang mâu thuẫn với số cũ)."
        else:
            b_cau = b.quan_sat
        ra.append(_bh("kenh", b.truc, b_cau, b.so_mau, _DUNG_CHO_SAN_XUAT.get(b.truc, ["bien_tap"]),
                      cum=b.cum))
    return ra


def _tu_danh_gia(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    du = _doc_json(os.path.join(_nghien_cuu(goc, ma_kenh), "bien-tap", "danh-gia.json"))
    if not isinstance(du, dict):
        return []
    n = len(du.get("ban_ghi") or [])
    return [_bh("kenh", "bien_tap", str(x), n, ["chon", "bien_tap"])
            for x in (du.get("bai_hoc") or [])[-5:] if str(x).strip()]


def _tu_kham_nghiem(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    """Bài học khám nghiệm video của kênh (`giam-doc/bai-hoc.jsonl`). Bài bóng (giám đốc chưa `tu_ap`) và bài
    mâu thuẫn chỉ cho người đọc (`bom=False`); giám đốc `tu_ap` thì bài bóng tính như thật."""
    from ..giam_doc import kham_nghiem as kn  # noqa: PLC0415
    from ..kenh import TEP_KENH, doc_yaml  # noqa: PLC0415

    cai = doc_yaml(os.path.join(_duong_kenh(goc, ma_kenh), TEP_KENH)) or {}
    tu_ap = str(cai.get("giam_doc") or "").strip().lower() == "tu_ap"
    ra = []
    for b in kn.doc_bai_hoc(goc, ma_kenh, bo_bong=tu_ap):
        if b["n"] <= 0:
            continue
        cau = "{0} (khám nghiệm {1} video{2})".format(b["cau"].rstrip(". "), b["ung"],
                                                    ", {0} video phản".format(b["phan"]) if b["phan"] else "")
        o = _bh("kenh", b["truc"], cau, b["n"], b["dung_cho"], cum=b["cum"], khoa=b["khoa"], bong=b["bong"],
                video=b["video"], nguon="kham_nghiem")
        o["bom"] = bool(b["bom"])
        o.update(cong=b["cong"], tru=b["tru"], trang_thai=b["trang_thai"], gia_thuyet=bool(b["gia_thuyet"]),
                 id_bai=b["id"])
        ra.append(o)
    return ra


NHAN_GIA_THUYET = "(đang kiểm, chưa chắc) "
TOI_DA_THAT = 5
TOI_DA_GIA_THUYET = 2


def _diem_bai(b: Dict[str, Any]) -> Tuple[int, int]:
    return (-(int(b.get("cong") or 0) - int(b.get("tru") or 0)), -int(b.get("cong") or 0))


def chon_bai_kham_nghiem(ds: Iterable[Dict[str, Any]], toi_da_that: int = TOI_DA_THAT,
                         toi_da_gia_thuyet: int = TOI_DA_GIA_THUYET) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Luật bơm sổ bài học có bộ đếm (đợt 3 tự học): `(that, gia_thuyet)` — CHỈ bài khám nghiệm trạng thái
    "that" (≤ 5, xếp cong − tru) và ≤ 2 "gia_thuyet" điểm cao nhất (ghi rõ "đang kiểm, chưa chắc"). "bo" không bơm."""
    kn = [b for b in ds if b.get("nguon") == "kham_nghiem"]
    that = sorted((b for b in kn if b.get("trang_thai") == "that"), key=_diem_bai)[:max(0, toi_da_that)]
    gt = sorted((b for b in kn if b.get("trang_thai") == "gia_thuyet"), key=_diem_bai)[:max(0, toi_da_gia_thuyet)]
    return that, gt


def khoi_kham_nghiem(goc: str, ma_kenh: str, dung_cho: Any = "", toi_da: int = 5) -> str:
    """Khối chữ CHỈ bài khám nghiệm bơm được (n ≥ 3, không mâu thuẫn, không bóng) cho khâu `dung_cho` —
    `""` khi chưa có (nơi gọi giữ lời nhắc y hệt từng byte). Đọc riêng nguồn này, không dựng cả `_tat_ca`."""
    try:
        ds = _loc_dung_cho(_tu_kham_nghiem(goc, ma_kenh), dung_cho)
    except Exception:  # noqa: BLE001
        return ""
    that, gt = chon_bai_kham_nghiem(ds, toi_da)
    return "\n".join(["- " + b["cau"] for b in that] + ["- " + NHAN_GIA_THUYET + b["cau"] for b in gt])


def _tu_ket_qua(goc: str, ma_kenh: str) -> List[Dict[str, Any]]:
    from . import ket_qua  # noqa: PLC0415

    ra = []
    for ct, o in sorted(ket_qua.thong_ke(goc, ma_kenh).items()):
        if not o.get("lam"):
            continue
        phu = []
        if o.get("ctr_trang_chu_tv") is not None:
            phu.append("CTR trang chủ tv {0:g}%".format(o["ctr_trang_chu_tv"]))
        if o.get("avd_giay_tv") is not None:
            phu.append("AVD tv {0}".format(_mmss(o["avd_giay_tv"])))
        if o.get("sub_1k") is not None:
            phu.append("{0:g} sub/1k view".format(o["sub_1k"]))
        cau = "Công thức {0} (28 ngày): {1}/{2} video đã có kết luận thắng @48h theo ngưỡng kênh{3}; " \
              "{4} video chưa đủ mốc (n={2}).".format(ct, o["thang"], o["n"],
                                                    " — " + ", ".join(phu) if phu else "", o["cho"])
        ra.append(_bh("kenh", "cong_thuc", cau, o["n"], ["chon"], cum=ct))
    return ra


def _cum_thang_truot_kenh(ds: List[Any], nguong: Optional[float]) -> List[Dict[str, Any]]:
    theo: Dict[str, List[bool]] = {}
    for v in ds:
        if v.hien_thi_48h is None and not v.thang:
            continue
        for c in v.cum or []:
            theo.setdefault(c, []).append(bool(v.thang))
    ra = []
    for c, xs in sorted(theo.items()):
        ra.append(_bh("kenh", "cum_thang_truot", "cụm {0}: {1}/{2} video thắng @48h (ngưỡng kênh {3} hiển "
                      "thị).".format(c, sum(xs), len(xs), "{0:,.0f}".format(nguong).replace(",", ".") if nguong else "?"),
                      len(xs), ["chon", "bien_tap"], cum=c))
    return ra


def _muc_tieu_ctr(goc: str, ma_kenh: str, ds: List[Any]) -> List[Dict[str, Any]]:
    from . import ket_qua  # noqa: PLC0415

    thang, tat_ca = [], []
    for v in ds:
        if v.hien_thi_48h is None:
            continue
        ctr = ket_qua._ctr_trang_chu(goc, ma_kenh, v.ma)  # noqa: SLF001
        if ctr is None:
            continue
        tat_ca.append(ctr)
        if v.thang:
            thang.append(ctr)
    if len(thang) >= NGUONG_VUA:
        mt, n, nhan = statistics.median(thang), len(thang), "trung vị video thắng"
    elif tat_ca:
        mt, n, nhan = statistics.median(tat_ca), len(tat_ca), "trung vị cả kênh"
    else:
        return []
    mt = round(mt, 1)
    return [_bh("kenh", "ctr_trang_chu", "CTR trang chủ @48h mục tiêu ≥ {0:g}% ({1}, n={2}).".format(mt, nhan, n),
                n, list(DUNG_CHO), muc_tieu=mt)]


# ── nguồn NHÓM, NGOÀI ───────────────────────────────────────────────────────

def _doc_csv(duong: str) -> List[Dict[str, str]]:
    try:
        with io.open(duong, encoding="utf-8-sig", newline="") as tep:
            return [dict(r) for r in csv.DictReader(tep)]
    except (OSError, csv.Error, UnicodeDecodeError):
        return []


def _tu_insight(goc: str, nhom: str, n_nhom: int) -> List[Dict[str, Any]]:
    try:
        with io.open(os.path.join(_thu_muc_nhom(goc, nhom), "INSIGHT-CHON-CONTENT.md"), encoding="utf-8") as tep:
            chu = tep.read()
    except OSError:
        return []
    ra = []
    for m in re.finditer(r"(?ms)^\s*(\d+)\.\s+(.+?)(?=^\s*\d+\.\s|\Z)", chu):
        ra.append(_bh("nhom", "insight_nhom", m.group(2), n_nhom, ["chon", "bien_tap"], muc=int(m.group(1))))
    return ra


def _cum_thang_truot_nhom(goc: str, ma_kenh: str, nhom: str, bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Cụm × kênh anh em: bao nhiêu video trên TRUNG VỊ hiển thị của chính kênh anh em đó (không dùng
    ngưỡng tuyệt đối — mỗi kênh một cỡ). Video < 3 ngày tuổi chưa kết luận, bỏ."""
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415

    hang = [h for h in _doc_csv(os.path.join(_thu_muc_nhom(goc, nhom), "bang-nhom.csv"))
            if str(h.get("Kênh") or "") != ma_kenh]
    if not hang:
        return []
    ch = _cau_hinh_v7(goc, ma_kenh)
    theo_kenh: Dict[str, List[Tuple[Dict[str, str], float]]] = {}
    for h in hang:
        try:
            tuoi = (bay_gio - _dt.datetime.strptime(str(h.get("Ngày đăng") or "")[:10], "%Y-%m-%d")).days
        except ValueError:
            tuoi = None
        imp = _so(h.get("Lượt hiển thị"))
        if imp is None or (tuoi is not None and tuoi < 3):
            continue
        theo_kenh.setdefault(str(h.get("Kênh") or ""), []).append((h, imp))
    theo_cum: Dict[str, List[bool]] = {}
    for _k, ds in theo_kenh.items():
        tv = statistics.median(x for _h, x in ds)
        for h, imp in ds:
            for c in v7.cum_cua_tieu_de(str(h.get("Tiêu đề") or ""), ch):
                theo_cum.setdefault(c, []).append(imp > tv)
    return [_bh("nhom", "cum_thang_truot", "cụm {0} ở kênh anh em: {1}/{2} video trên trung vị hiển thị của "
                "chính kênh đó.".format(c, sum(xs), len(xs)), len(xs), ["chon", "bien_tap"], cum=c)
            for c, xs in sorted(theo_cum.items())]


def _tu_ngoai(goc: str, nhom: str) -> List[Dict[str, Any]]:
    ra = []
    for duong in sorted(glob.glob(os.path.join(_thu_muc_nhom(goc, nhom), "bai-hoc-ngoai", "*.json"))):
        du = _doc_json(duong)
        ds = du.get("bai_hoc") if isinstance(du, dict) else du
        for b in ds if isinstance(ds, list) else []:
            if not isinstance(b, dict) or not str(b.get("cau") or "").strip():
                continue
            ra.append(_bh("ngoai", str(b.get("truc") or "ngoai"), str(b.get("cau")), int(_so(b.get("n")) or 0),
                          [x for x in (b.get("dung_cho") or ["chon"]) if x in DUNG_CHO] or ["chon"],
                          cum=str(b.get("cum") or ""), nguon_tep=os.path.basename(duong)))
    return ra


# ── gộp + luật phạm vi ──────────────────────────────────────────────────────

def _an_toan(f: Any, *a: Any) -> List[Dict[str, Any]]:
    try:
        return list(f(*a) or [])
    except Exception:  # noqa: BLE001 — một nguồn hỏng chỉ thiếu nguồn đó
        return []


def _tat_ca(goc: str, ma_kenh: str, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    bay_gio = bay_gio or _dt.datetime.now()
    try:
        ds, nguong = _video_v7(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        ds, nguong = [], None
    kenh = (_an_toan(_muc_tieu_ctr, goc, ma_kenh, ds) + _an_toan(_tu_san_xuat, goc, ma_kenh)
            + _an_toan(_tu_ket_qua, goc, ma_kenh) + _an_toan(_cum_thang_truot_kenh, ds, nguong)
            + _an_toan(lambda: _bai_giu_chan(diem_thoat(goc, ma_kenh)))
            + _an_toan(_tu_danh_gia, goc, ma_kenh) + _an_toan(_tu_kham_nghiem, goc, ma_kenh))
    # n của kênh trên từng trục; trục "insight_nhom" (cả kênh) = số video riêng đã đo 48h.
    n_kenh: Dict[Tuple[str, str], int] = {}
    for b in kenh:
        k = (b["truc"], b["cum"])
        n_kenh[k] = max(n_kenh.get(k, 0), b["n"])
    n_kenh[("insight_nhom", "")] = sum(1 for v in ds if v.hien_thi_48h is not None)
    nhom = _nhom(goc, ma_kenh)
    ngoai_vao: List[Dict[str, Any]] = []
    nhom_vao: List[Dict[str, Any]] = []
    if nhom:
        n_nhom = len(_doc_csv(os.path.join(_thu_muc_nhom(goc, nhom), "bang-nhom.csv")))
        for b in _an_toan(_tu_insight, goc, nhom, n_nhom) + _an_toan(_cum_thang_truot_nhom, goc, ma_kenh,
                                                                      nhom, bay_gio):
            if n_kenh.get((b["truc"], "" if b["truc"] == "insight_nhom" else b["cum"]), 0) < NGUONG_VUA:
                nhom_vao.append(b)
        for b in _an_toan(_tu_ngoai, goc, nhom):
            if n_kenh.get((b["truc"], b["cum"]), 0) == 0:
                ngoai_vao.append(b)
    ra = kenh + nhom_vao + ngoai_vao
    # Nút "Sai" trên Phòng điều hành: bài chủ kênh đã gạch thì không bao giờ vào lời nhắc.
    try:
        from ..bang_dieu_khien import khoa_bai_hoc_gach, ma_bai  # noqa: PLC0415
        gach = khoa_bai_hoc_gach(goc, ma_kenh)
        if gach:
            ra = [b for b in ra if str(b.get("ma_bai") or ma_bai(b)) not in gach]
    except Exception:  # noqa: BLE001
        pass
    return ra


def _loc_dung_cho(ds: List[Dict[str, Any]], dung_cho: Any) -> List[Dict[str, Any]]:
    if not dung_cho:
        return ds
    muon = {dung_cho} if isinstance(dung_cho, str) else set(dung_cho)
    return [b for b in ds if muon & set(b.get("dung_cho") or [])]


def doc(goc: str, ma_kenh: str, dung_cho: Any = "", toi_da: int = 8, *,
        tat_ca: bool = False, bay_gio: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Bài học cho khâu `dung_cho` ("chon", "bien_tap", …, hoặc list; rỗng = mọi khâu), đã áp luật
    phạm vi. Thứ tự: bài bơm được (n ≥ 3) trước; trong đó kênh → nhóm → ngoài, n lớn trước. `tat_ca`
    = không cắt `toi_da` (cho người đọc). Không ném lỗi."""
    try:
        ds = _loc_dung_cho(_tat_ca(goc, ma_kenh, bay_gio), dung_cho)
    except Exception:  # noqa: BLE001
        return []
    ds.sort(key=lambda b: (0 if b["bom"] else 1, PHAM_VI.index(b["pham_vi"]),
                           _UU_TIEN.get(b["truc"], 9), -b["n"]))
    return ds if tat_ca else ds[:max(0, int(toi_da))]


def khoi_chu(goc: str, ma_kenh: str, dung_cho: Any = "", toi_da: int = 8, *,
             bay_gio: Optional[_dt.datetime] = None, pham_vi: Sequence[str] = PHAM_VI,
             bo_truc: Sequence[str] = ()) -> str:
    """Khối chữ gọn (mỗi bài một dòng) — CHỈ bài n ≥ 3; bài nhóm/ngoài mang nhãn tiên nghiệm.

    `pham_vi` / `bo_truc` (B5): nơi gọi đã có khối riêng cho một nguồn (biên tập viên đã có INSIGHT
    nhóm và TỰ SỬA) thì lọc ra ở đây để lời nhắc không nhắc một bài hai lần."""
    dong = []
    ds = doc(goc, ma_kenh, dung_cho, tat_ca=True, bay_gio=bay_gio)
    # Bài khám nghiệm theo luật mới (that ≤ 5 + gia_thuyet ≤ 2); nguồn khác giữ luật cũ n ≥ 3.
    that, gia_thuyet = chon_bai_kham_nghiem(ds)
    cho_phep = {id(b) for b in that}
    for b in ds:
        if not b["bom"] or b["pham_vi"] not in pham_vi or b["truc"] in bo_truc:
            continue
        if b.get("nguon") == "kham_nghiem" and id(b) not in cho_phep:
            continue
        nhan = NHAN_NHOM if b["pham_vi"] == "nhom" else NHAN_NGOAI if b["pham_vi"] == "ngoai" else ""
        dong.append("- " + b["cau"] + nhan)
        if len(dong) >= toi_da:
            break
    if "kenh" in pham_vi:
        dong += ["- " + NHAN_GIA_THUYET + b["cau"] for b in gia_thuyet if b["truc"] not in bo_truc]
    return "\n".join(dong)


def pham_vi_cho(ds: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Đếm theo phạm vi — tiện cho log/người đọc."""
    ra = {p: 0 for p in PHAM_VI}
    for b in ds:
        ra[b["pham_vi"]] = ra.get(b["pham_vi"], 0) + 1
    return ra
