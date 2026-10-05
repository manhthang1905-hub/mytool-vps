"""Bìa BÁM KHUÔN THẮNG — khai thác / thăm dò / tự học (30/09/2026).

═══ VÌ SAO CÓ TỆP NÀY ═══

`core/khuon_bia.py` BIẾT ảnh bìa nào đang thắng, nhưng khâu bìa chỉ dành cho
khuôn đó MỘT trong bảy tấm (`khuon_thang`), và giám khảo `chon_bia` hầu như
không bao giờ chọn nó (sổ TL3-T7: 0003→0008 chỉ một lần). Tệ hơn, khuôn chữ
được tả từ tấm TOOL TẠO lúc sản xuất, không phải tấm chủ kênh ĐĂNG THẬT:
vea03c3caae (CTR 9,73% / 19.618 hiển thị) trên YouTube là nền TÍM, nhân vật ở
GIỮA ngồi xổm, chữ TRẦN 2 tầng (trắng trên, ĐỎ+VÀNG cực lớn dưới, viền đậm,
KHÔNG khối nền) — còn tấm tool tạo là nền cam/xám, chữ trắng trong khối đen.
Tức là tool đã học… đúng kiểu THUA (v452ac76644, 14 view/48h).

Tệp này gom mọi luật MỚI để các tệp sống chỉ cần nối dây:

    trang_thai_khai_thac()   — kênh đã có khuôn ĐỦ BẰNG CHỨNG chưa → "khai_thac"
                               hay "tham_do" + số tấm theo khuôn + lượt thăm dò.
    la_luot_tham_do()        — lượt THĂM DÒ tất định theo hash mã gói (1/N video).
    LOI_NHAC_DOC_BIA_CAU_TRUC / chuan_hoa_khuon_chu()
                             — mô tả khuôn CÓ CẤU TRÚC (cùng tên trường với nghiên
                               cứu `workspace/nghien-cuu-bia/`), rút từ ẢNH THẬT.
    khoi_khuon_tieng_anh()   — khuôn cấu trúc → khối lời nhắc tiếng Anh.
    loi_nhac_theo_khuon()    — lời nhắc ảnh bìa theo khuôn (chỉ đổi chữ + đạo cụ).
    ve_chu_len_anh()         — bộ vẽ chữ TRẦN nhiều màu, viền đậm, 2 tầng (hoặc có
                               khối nền nếu khuôn có) — dùng khi chữ do mô hình
                               ảnh vẽ hay sai chính tả tiếng Nhật.
    hoc_sau_video()          — vòng học: so CTR theo khuôn vs thăm dò, hạ/nâng độ
                               tin của khuôn, bỏ qua video chủ kênh ĐỔI BÌA TAY.

Mọi ngưỡng đặt trong mã và ghi đè được bằng khoá `kenh.yaml` (đọc THÔ bằng
`core.kenh.doc_yaml`, không cần thêm trường vào lớp `Kenh`):

    bia_khai_thac: true              # tắt = luôn thăm dò như cũ
    bia_khai_thac_ctr_min: 7.0       # CTR tối thiểu tuyệt đối (%)
    bia_khai_thac_he_so_trung_vi: 1.5
    bia_khai_thac_imp_min: 10000
    bia_so_tam_theo_khuon: 3         # trong so_thumbnail tấm (điều phối 30/09: 3/7)
    bia_chu_ky_tham_do: 5            # 1/5 video được CHỌN tấm thăm dò
    bia_ve_chu: "tron"               # "tron" (xen kẽ) | "ma" = code vẽ chữ | "mo_hinh" = mô hình ảnh vẽ

Mỗi kênh học từ dữ liệu CỦA RIÊNG KÊNH ĐÓ (không mượn khuôn nhóm).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import io
import json
import os
import re
import statistics
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "NGUONG_MAC_DINH", "cau_hinh_kenh", "trang_thai_khai_thac", "la_luot_tham_do",
    "LOI_NHAC_DOC_BIA_CAU_TRUC", "chuan_hoa_khuon_chu", "khoi_khuon_tieng_anh",
    "loi_nhac_theo_khuon", "ve_chu_len_anh", "hoc_sau_video", "kieu_theo_khuon",
    "khac_bia_tool", "tong_ky_tu_khuon",
]

#: Ngưỡng "khuôn ĐỦ BẰNG CHỨNG để khai thác" — chủ dự án 30/09/2026.
NGUONG_MAC_DINH: Dict[str, Any] = {
    "bia_khai_thac": True,
    "bia_khai_thac_ctr_min": 7.0,
    "bia_khai_thac_he_so_trung_vi": 1.5,
    "bia_khai_thac_imp_min": 10000,
    "bia_so_tam_theo_khuon": 3,
    "bia_chu_ky_tham_do": 5,
    "bia_ve_chu": "tron",
}

#: Tiền tố tên kiểu của mọi tấm theo khuôn: `khuon_thang`, `khuon_thang_2`…
TIEN_TO_KHUON = "khuon_thang"

#: Vòng học: video theo khuôn có CTR < hệ số × CTR khuôn thì tính là "tụt".
HE_SO_TUT = 0.6
#: Bao nhiêu lần tụt LIÊN TIẾP thì hạ độ tin một nấc.
SO_LAN_TUT_HA_TIN = 2
BUOC_HA_TIN = 0.25
DO_TIN_SAN = 0.25  # xuống tới đây thì thôi khai thác (về thăm dò)
IMP_TOI_THIEU_DANH_GIA = 1000
#: Chênh ảnh (0-255, trung bình tuyệt đối trên lưới xám 32×18) quá ngưỡng này
#: thì coi bìa trên YouTube KHÁC bìa tool chọn (chủ kênh đổi bìa tay). Đo
#: 30/09/2026: TL3-0001 tool↔thật = khác hẳn; cùng ảnh qua nén lại YouTube < 8.
NGUONG_KHAC_BIA = 22.0


def kieu_theo_khuon(kieu: str) -> bool:
    return str(kieu or "").startswith(TIEN_TO_KHUON)


# ── Cấu hình kênh (đọc thô kenh.yaml) ──────────────────────────────────────


def cau_hinh_kenh(goc: str, kenh: str) -> Dict[str, Any]:
    ra = dict(NGUONG_MAC_DINH)
    try:
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415
        tho = doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}
    except Exception:  # noqa: BLE001 — cấu hình hỏng thì giữ mặc định
        tho = {}
    for k, mac_dinh in NGUONG_MAC_DINH.items():
        if k not in tho or tho[k] is None or tho[k] == "":
            continue
        v = tho[k]
        try:
            if isinstance(mac_dinh, bool):
                ra[k] = v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "on")
            elif isinstance(mac_dinh, int):
                ra[k] = int(float(v))
            elif isinstance(mac_dinh, float):
                ra[k] = float(v)
            else:
                ra[k] = str(v).strip()
        except (TypeError, ValueError):
            pass
    ra["bia_so_tam_theo_khuon"] = max(1, ra["bia_so_tam_theo_khuon"])
    ra["bia_chu_ky_tham_do"] = max(2, ra["bia_chu_ky_tham_do"])
    if ra["bia_ve_chu"] not in ("ma", "mo_hinh", "tron"):
        ra["bia_ve_chu"] = "tron"
    return ra


# ── Bằng chứng khai thác ─────────────────────────────────────────────────────


def _ctr_cac_video_khac(goc: str, kenh: str, bo_video_id: str) -> List[float]:
    """CTR mốc MUỘN NHẤT của mọi video khác của kênh (≥100 hiển thị) — mẫu để
    tính trung vị kênh. Không lọc khung 36-96h như `khuon_bia` vì kênh mới có
    rất ít video chín đủ mốc; ngưỡng tuyệt đối `ctr_min` đã chặn ca mẫu non."""
    from . import ho_so_video  # noqa: PLC0415
    ra: List[float] = []
    thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
    try:
        ten_tep = sorted(t for t in os.listdir(thu_muc) if t.endswith(".json"))
    except OSError:
        return ra
    for ten in ten_tep:
        hs = ho_so_video.doc_ho_so(goc, kenh, ten[:-5])
        if not isinstance(hs, dict) or not hs.get("video_id") or hs.get("video_id") == bo_video_id:
            continue
        tot = None
        for m in (hs.get("chi_so") or {}).values():
            if not isinstance(m, dict) or m.get("ctr") is None or (m.get("impressions") or 0) < 100:
                continue
            gio = m.get("moc_gio_that") or 0
            if tot is None or gio > tot[0]:
                tot = (gio, float(m["ctr"]))
        if tot is not None:
            ra.append(tot[1])
    return ra


def trang_thai_khai_thac(goc: str, kenh: str, khuon: Optional[Dict[str, Any]] = None
                         ) -> Dict[str, Any]:
    """`{che_do, khuon, ly_do, nguong_ctr, trung_vi, do_tin, so_tam_theo_khuon,
    chu_ky_tham_do, ve_chu}` — KHÔNG ném lỗi (hỏng thì "tham_do")."""
    ch = cau_hinh_kenh(goc, kenh)
    ra: Dict[str, Any] = {"che_do": "tham_do", "khuon": None, "ly_do": "", "nguong_ctr": None,
                          "trung_vi": None, "do_tin": 1.0,
                          "so_tam_theo_khuon": ch["bia_so_tam_theo_khuon"],
                          "chu_ky_tham_do": ch["bia_chu_ky_tham_do"], "ve_chu": ch["bia_ve_chu"]}
    try:
        if khuon is None:
            from . import khuon_bia  # noqa: PLC0415
            khuon = khuon_bia.doc_khuon(goc, kenh)
        if not ch["bia_khai_thac"]:
            ra["ly_do"] = "kênh tắt bia_khai_thac"
            return ra
        if not khuon or khuon.get("het_hieu_luc") or not khuon.get("khuon_chu"):
            ra["ly_do"] = "chưa có khuôn thắng hợp lệ"
            return ra
        if khuon.get("nguon") not in (None, "", "kenh"):
            ra["ly_do"] = "khuôn không phải của chính kênh"
            return ra
        if not khuon.get("anh_that"):
            ra["ly_do"] = "khuôn chưa rút từ bìa THẬT trên YouTube"
            return ra
        ctr = float(khuon.get("ctr") or 0.0)
        imp = float(khuon.get("imp") or 0.0)
        khac = _ctr_cac_video_khac(goc, kenh, str(khuon.get("video_id") or ""))
        tv = statistics.median(khac) if khac else None
        nguong = max(ch["bia_khai_thac_ctr_min"],
                     (ch["bia_khai_thac_he_so_trung_vi"] * tv) if tv is not None else 0.0)
        ra.update(nguong_ctr=round(nguong, 3), trung_vi=tv)
        if ctr < nguong or imp < ch["bia_khai_thac_imp_min"]:
            ra["ly_do"] = ("khuôn chưa đủ bằng chứng: CTR {0:.2f}% (cần ≥{1:.2f}%), hiển thị "
                           "{2:.0f} (cần ≥{3})").format(ctr, nguong, imp, ch["bia_khai_thac_imp_min"])
            return ra
        do_tin = float((khuon.get("hoc") or {}).get("do_tin", 1.0))
        ra["do_tin"] = do_tin
        if do_tin <= DO_TIN_SAN:
            ra["ly_do"] = "khuôn mất tin (CTR theo khuôn tụt nhiều lần) — quay về thăm dò"
            return ra
        # Độ tin thấp → ít tấm theo khuôn hơn, lượt thăm dò DÀY hơn.
        ra["so_tam_theo_khuon"] = max(2, int(round(ch["bia_so_tam_theo_khuon"] * min(1.0, do_tin))))
        ra["chu_ky_tham_do"] = max(2, int(round(ch["bia_chu_ky_tham_do"] * min(1.0, do_tin))))
        ra.update(che_do="khai_thac", khuon=khuon,
                  ly_do="khuôn {0} đủ bằng chứng: CTR {1:.2f}% ≥ {2:.2f}%, {3:.0f} hiển thị".format(
                      khuon.get("video_id"), ctr, nguong, imp))
    except Exception as loi:  # noqa: BLE001
        ra.update(che_do="tham_do", khuon=None, ly_do="lỗi đọc khuôn: {0}".format(str(loi)[:120]))
    return ra


def la_luot_tham_do(ma_goi: str, chu_ky: int) -> bool:
    """Lượt THĂM DÒ tất định: sha1(mã gói) mod chu_ky == 0 — cùng gói luôn cùng
    kết quả (chạy lại khâu không đổi quyết định), trung bình 1/chu_ky video."""
    if not ma_goi or chu_ky <= 1:
        return False
    h = int(hashlib.sha1(ma_goi.encode("utf-8")).hexdigest()[:8], 16)  # noqa: S324
    return h % int(chu_ky) == 0


# ── Mô tả khuôn CÓ CẤU TRÚC (rút từ ẢNH THẬT) ────────────────────────────────


LOI_NHAC_DOC_BIA_CAU_TRUC = """This is the thumbnail CURRENTLY LIVE on YouTube for a channel's \
best-performing video (real CTR {ctr:.2f}%, {impressions:.0f} impressions at ~{moc_gio:.0f}h). \
Measure it so another artist can rebuild the SAME winning design for a different story. Be \
precise and literal about what you SEE — especially the TEXT: colour of each line, outline, \
whether there is ANY background box/plate behind the text (true/false), and which words are \
coloured differently.

Return JSON only (no markdown), exactly these keys:
{{
  "bo_cuc": "framing — subject size/position, where the text sits",
  "mau_sac": "dominant palette, which colour dominates",
  "anh_sang": "light source(s), brightest vs darkest area",
  "vi_tri_chu": "text tiers and where each sits, reading order",
  "kieu_chu": "font weight, fill colours, outline/stroke, shadow, background box or bare text",
  "diem_hut_mat": "the element the eye lands on first and why",
  "nen_mau_chu_dao": "dominant background colour as a name + hex, e.g. 'deep purple #2B0B4F'",
  "nen_do_sang": "toi | vua | sang",
  "nen_hieu_ung": ["short phrases: glow/halo, particles, cracks, digital lines, vignette..."],
  "tuong_phan": "rat_cao | cao | vua | thap",
  "bao_hoa": "cao | vua | thap",
  "sac_thai": "the emotional tone in 2-5 words",
  "nhan_vat": {{"vi_tri": "trai | giua | phai", "co_pct": 0, "tu_the": "pose", "net_mat": "expression"}},
  "chu": {{
    "so_tang": 0,
    "tang": [
      {{"vi_tri": "tren | giua | duoi | trai | phai", "noi_dung": "the exact text you read",
        "so_ky_tu": 0, "co_pct": 0,
        "mau": ["#hex fill colours in reading order"],
        "phan_mau": [{{"chu": "part of the text", "mau": "#hex"}}],
        "vien": "outline description, e.g. 'thick black outline ~8% of letter height' or 'none'",
        "khoi_nen": false, "trich_dan": false}}
    ],
    "tu_to_mau": "which words are coloured differently and why (e.g. subject red, key idea yellow)"
  }}
}}
`co_pct` = share of frame HEIGHT (0-100). `trich_dan` = the line is wrapped in 「」 quotes.
Write every value in ENGLISH (only `noi_dung`/`phan_mau.chu` keep the original script). For \
`phan_mau`, check the colour of EVERY character one by one and cut the text exactly where the \
colour changes — the split must reproduce `noi_dung` when concatenated."""


def _chuoi(v: Any, toi_da: int = 300) -> str:
    return str(v if v is not None else "").strip()[:toi_da]


def _so(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _co(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v or "").strip().lower() in ("true", "1", "yes", "co", "có")


_RE_HEX = re.compile(r"#[0-9a-fA-F]{6}")


def chuan_hoa_khuon_chu(du: Any) -> Dict[str, Any]:
    """JSON AI trả → khuôn cấu trúc sạch. Giữ 6 trường văn xuôi cũ (tương thích
    `doc_bai_hoc_anh_bia`/`chon_bia`) + các trường cấu trúc mới."""
    if not isinstance(du, dict):
        return {}
    ra: Dict[str, Any] = {}
    for t in ("bo_cuc", "mau_sac", "anh_sang", "vi_tri_chu", "kieu_chu", "diem_hut_mat",
              "nen_mau_chu_dao", "nen_do_sang", "tuong_phan", "bao_hoa", "sac_thai"):
        if du.get(t):
            ra[t] = _chuoi(du.get(t), 400)
    hu = du.get("nen_hieu_ung")
    if isinstance(hu, (list, tuple)):
        ra["nen_hieu_ung"] = [_chuoi(x, 80) for x in hu if x][:8]
    elif hu:
        ra["nen_hieu_ung"] = [_chuoi(hu, 160)]
    nv = du.get("nhan_vat")
    if isinstance(nv, dict):
        ra["nhan_vat"] = {"vi_tri": _chuoi(nv.get("vi_tri"), 20), "co_pct": _so(nv.get("co_pct")),
                          "tu_the": _chuoi(nv.get("tu_the"), 160), "net_mat": _chuoi(nv.get("net_mat"), 160)}
    chu = du.get("chu")
    if isinstance(chu, dict):
        tang_ra = []
        for t in (chu.get("tang") or [])[:4]:
            if not isinstance(t, dict):
                continue
            mau = t.get("mau")
            mau = [m for m in (mau if isinstance(mau, list) else [mau]) if m]
            mau = [(_RE_HEX.search(str(m)).group(0).upper() if _RE_HEX.search(str(m)) else _chuoi(m, 30))
                   for m in mau][:4]
            phan = []
            for p in (t.get("phan_mau") or [])[:6]:
                if isinstance(p, dict) and p.get("chu"):
                    hm = _RE_HEX.search(str(p.get("mau") or ""))
                    phan.append({"chu": _chuoi(p["chu"], 40), "mau": hm.group(0).upper() if hm else ""})
            noi_dung = _chuoi(t.get("noi_dung"), 60)
            tang_ra.append({
                "vi_tri": _chuoi(t.get("vi_tri"), 20), "noi_dung": noi_dung,
                "so_ky_tu": int(_so(t.get("so_ky_tu")) or len(re.sub(r"[\s\W_]+", "", noi_dung))),
                "co_pct": _so(t.get("co_pct")), "mau": mau, "phan_mau": phan,
                "vien": _chuoi(t.get("vien"), 120), "khoi_nen": _co(t.get("khoi_nen")),
                "trich_dan": _co(t.get("trich_dan")),
            })
        ra["chu"] = {"so_tang": int(_so(chu.get("so_tang")) or len(tang_ra)), "tang": tang_ra,
                     "tu_to_mau": _chuoi(chu.get("tu_to_mau"), 200)}
    return ra


LOI_NHAC_SOI_MAU_TANG = """The image is a CROP of one text line from a YouTube thumbnail. The line \
reads: {noi_dung}
List EVERY character of that line in order with its FILL colour (ignore the outline), as JSON only:
{{"ky_tu": [["低", "#hex"], ["I", "#hex"], ...]}}"""


def _cat_dai_chu(duong_anh: str, vi_tri: str, dich: str) -> bool:
    try:
        from PIL import Image  # noqa: PLC0415
        im = Image.open(duong_anh).convert("RGB")
    except (OSError, ValueError):
        return False
    W, H = im.size
    hop = {"tren": (0, 0, W, int(H * 0.36)), "duoi": (0, int(H * 0.64), W, H),
           "trai": (0, 0, W // 2, H), "phai": (W // 2, 0, W, H)}.get(vi_tri)
    if not hop:
        return False
    im.crop(hop).save(dich, format="PNG")
    return True


def soi_mau_tang(goi_chat: Callable[..., str], duong_anh: str, khuon_chu: Dict[str, Any],
                 thu_muc_tam: str) -> Dict[str, Any]:
    """Lượt SOI KỸ màu từng ký tự của mỗi tầng chữ (cắt riêng dải chữ, nhìn gần)
    — lượt tả tổng thể hay chia sai chỗ đổi màu. Gộp ký tự liền nhau cùng màu
    thành `phan_mau`. Hỏng thì giữ nguyên bản cũ."""
    from .goi_van_ban import loc_json  # noqa: PLC0415
    chu = (khuon_chu or {}).get("chu") or {}
    for i, t in enumerate(chu.get("tang") or []):
        if not t.get("noi_dung"):
            continue
        cat = os.path.join(thu_muc_tam, "_soi_tang_{0}.png".format(i))
        try:
            if not _cat_dai_chu(duong_anh, t.get("vi_tri", ""), cat):
                continue
            from .cham_anh import data_url  # noqa: PLC0415
            du = loc_json(str(goi_chat(LOI_NHAC_SOI_MAU_TANG.format(noi_dung=t["noi_dung"]),
                                       toi_da_token=900, anh=data_url(cat)) or ""))
            ds = du.get("ky_tu") if isinstance(du, dict) else None
            phan: List[Dict[str, str]] = []
            for cap in ds or []:
                if not isinstance(cap, (list, tuple)) or len(cap) < 2:
                    continue
                hm = _RE_HEX.search(str(cap[1]))
                mau = _nhom_mau(hm.group(0).upper()) if hm else ""
                if phan and phan[-1]["mau_nhom"] == mau:
                    phan[-1]["chu"] += str(cap[0])
                else:
                    phan.append({"chu": str(cap[0]), "mau": hm.group(0).upper() if hm else "",
                                 "mau_nhom": mau})
            if phan and "".join(p["chu"] for p in phan).replace(" ", "") == t["noi_dung"].replace(" ", ""):
                t["phan_mau"] = [{"chu": p["chu"], "mau": p["mau"]} for p in phan]
                t["mau"] = list(dict.fromkeys(p["mau"] for p in phan))
        except Exception:  # noqa: BLE001
            continue
        finally:
            try:
                os.remove(cat)
            except OSError:
                pass
    return khuon_chu


def _nhom_mau(hexm: str) -> str:
    return _ten_mau(hexm).split(" ")[0] if hexm else ""


def tong_ky_tu_khuon(khuon_chu: Dict[str, Any]) -> int:
    chu = (khuon_chu or {}).get("chu") or {}
    return int(sum(int(t.get("so_ky_tu") or 0) for t in (chu.get("tang") or [])))


def _ten_mau(hexm: str) -> str:
    """#hex → tên màu tiếng Anh thô (mô hình ảnh hiểu tên màu tốt hơn hex)."""
    m = _RE_HEX.search(hexm or "")
    if not m:
        return hexm or ""
    h = m.group(0)
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    if r > 220 and g > 220 and b > 220:
        ten = "white"
    elif r < 40 and g < 40 and b < 40:
        ten = "black"
    elif r > 180 and g > 170 and b < 90:
        ten = "bright yellow"
    elif r > 180 and g < 80 and b < 80:
        ten = "pure red"
    elif r > 200 and 90 <= g <= 170 and b < 80:
        ten = "orange"
    elif b > r and b > g:
        ten = "blue" if g > r else "purple"
    else:
        ten = "coloured"
    return "{0} {1}".format(ten, h)


#: Giá trị bậc (lược đồ nghiên cứu dùng cả chữ Việt lẫn số 1-5) → tiếng Anh cho lời nhắc ảnh.
_MUC_EN = {"rat_cao": "very high", "cao": "high", "vua": "medium", "trung": "medium", "thap": "low",
           "5": "very high", "4": "high", "3": "medium", "2": "low", "1": "very low"}


#: 01/10/2026 (bìa nhỏ ngày 01/10) — hai luật thêm vào MỌI lời nhắc bìa:
#: (1) TL3-0015 có người chụp kiểu ẢNH THẬT ở nền, lạc nét so với phong cách vẽ của kênh → cấm người thật /
#:     ảnh chụp; (2) nhân vật TL1 chỉ ~15% chiều cao khung → chuẩn ngách: biểu cảm rõ, ≥ 30% chiều cao khung
#:     (giám khảo `chon_bia` chấm theo cùng luật).
NHAN_VAT_TOI_THIEU_PCT = 30
CAM_ANH_THAT = ("NO real people and NO photographs anywhere — not even in the background: every figure is DRAWN in "
                "the same illustration style as the reference character (no photo-realistic faces, crowds, stock "
                "photos or camera-shot scenery)")
NHAN_VAT_LON = ("the character is BIG: at least {0}% of the frame height (head and upper body at least), face large "
                "enough that the expression reads at phone size — never a tiny figure lost in the scene").format(
                    NHAN_VAT_TOI_THIEU_PCT)


def khoi_khuon_tieng_anh(khuon_chu: Dict[str, Any], *, co_chu: bool = True) -> str:
    """Khuôn cấu trúc → các dòng tiếng Anh cho lời nhắc sinh ảnh / giám khảo."""
    kc = khuon_chu or {}
    dong: List[str] = []
    if kc.get("nen_mau_chu_dao"):
        dong.append("background: {0}, {1} overall brightness, saturation {2}, contrast {3}".format(
            kc["nen_mau_chu_dao"], {"toi": "dark", "vua": "medium", "sang": "bright"}.get(
                kc.get("nen_do_sang", ""), kc.get("nen_do_sang", "dark")),
            _MUC_EN.get(str(kc.get("bao_hoa", "cao")), str(kc.get("bao_hoa", "high"))),
            _MUC_EN.get(str(kc.get("tuong_phan", "cao")), str(kc.get("tuong_phan", "high")))))
    if kc.get("nen_hieu_ung"):
        dong.append("background effects: " + ", ".join(kc["nen_hieu_ung"]))
    if kc.get("anh_sang"):
        dong.append("lighting: " + kc["anh_sang"])
    nv = kc.get("nhan_vat") or {}
    if nv:
        vt = {"trai": "left third", "giua": "CENTRE of the frame", "phai": "right third"}.get(
            nv.get("vi_tri", ""), nv.get("vi_tri", ""))
        # 01/10/2026: chuẩn ngách — nhân vật biểu cảm rõ, ≥ 30% chiều cao khung (TL1 từng ~15%: lọt thỏm)
        co = "about {0:.0f}% of frame height".format(max(float(nv["co_pct"]), float(NHAN_VAT_TOI_THIEU_PCT))) \
            if nv.get("co_pct") else ""
        dong.append("the reference character placed in the {0}{1}".format(vt, (", " + co) if co else ""))
    if kc.get("sac_thai"):
        dong.append("mood: " + kc["sac_thai"])
    chu = kc.get("chu") or {}
    if co_chu and chu.get("tang"):
        mo_ta = []
        for t in chu["tang"]:
            mau = " + ".join(_ten_mau(m) for m in (t.get("mau") or [])) or "white"
            mo_ta.append("{vt} tier: {mau} bare lettering{vien}{khoi}, about {co}% of frame height{td}".format(
                vt=t.get("vi_tri") or "?", mau=mau,
                vien=(", " + t["vien"]) if t.get("vien") and t["vien"].lower() != "none" else "",
                khoi=" on a solid background box" if t.get("khoi_nen") else " with NO background box",
                co=int(t.get("co_pct") or 20), td=", wrapped in 「」 quotes" if t.get("trich_dan") else ""))
        dong.append("TEXT LAYOUT: " + "; ".join(mo_ta))
        if chu.get("tu_to_mau"):
            dong.append("text colouring rule: " + chu["tu_to_mau"])
    return "\n".join(dong)


# ── Lời nhắc sinh ảnh theo khuôn ─────────────────────────────────────────────


def _vung_trong_chu(khuon_chu: Dict[str, Any]) -> str:
    vt = [str(t.get("vi_tri") or "") for t in (((khuon_chu or {}).get("chu") or {}).get("tang") or [])]
    phan = []
    if any(v in ("tren",) for v in vt):
        phan.append("the TOP 30% of the frame")
    if any(v in ("duoi",) for v in vt):
        phan.append("the BOTTOM 32% of the frame")
    if any(v in ("trai",) for v in vt):
        phan.append("the LEFT half")
    if any(v in ("phai",) for v in vt):
        phan.append("the RIGHT half")
    return " and ".join(phan) or "the top and bottom bands"


def loi_nhac_theo_khuon(khuon_chu: Dict[str, Any], *, phong_cach: str, bien_the: Dict[str, str],
                        chu_tang: Optional[Sequence[Dict[str, Any]]] = None,
                        chu_do_ma_ve: bool = True, cam: str = "") -> str:
    """Lời nhắc ẢNH cho một tấm theo khuôn thắng. Chỉ đổi: đạo cụ/biểu tượng,
    tư thế, nét mặt (theo nội dung video) và CHỮ. Bố cục/màu/sáng giữ nguyên.

    `chu_do_ma_ve=True` → ảnh nền KHÔNG CHỮ, chừa trống vùng chữ để
    `ve_chu_len_anh` vẽ đúng chính tả; `False` → mô hình ảnh tự vẽ chữ.
    """
    kc = khuon_chu or {}
    nv = kc.get("nhan_vat") or {}
    tu_the = bien_the.get("tu_the") or nv.get("tu_the") or "dynamic pose"
    net_mat = bien_the.get("net_mat") or nv.get("net_mat") or "strong clear emotion"
    dao_cu = bien_the.get("dao_cu") or ""
    dong = [
        "psychology YouTube thumbnail, rebuild EXACTLY the attached winning thumbnail's design "
        "(second reference image) for a new story — keep its composition, palette, background "
        "lighting and text layout identical; change only the prop/symbol and the pose/expression",
        "use the attached character reference image (first reference image) for the character — "
        "same drawing style, do not redesign it",
        "",
        khoi_khuon_tieng_anh(kc, co_chu=not chu_do_ma_ve),
        "character: {0}, expression: {1} — a strong, readable emotion on the face".format(tu_the, net_mat),
        NHAN_VAT_LON,
        CAM_ANH_THAT,
    ]
    if dao_cu:
        dong.append("one symbolic prop tied to this story, drawn in the same style, behind or beside "
                    "the character, never covering the face, a plain object with no writing on it: "
                    + dao_cu)
    if chu_do_ma_ve:
        dong += [
            "",
            "ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS-AS-WORDS anywhere in the image — the title "
            "text is added later. Keep {0} free of any important detail (only background "
            "texture/glow there), so large lettering can be laid over it.".format(_vung_trong_chu(kc)),
        ]
    elif chu_tang:
        dong += ["", _dong_chu_tang(chu_tang)]
    dong += [
        "",
        "drawing style: " + (phong_cach or "flat bold brush illustration"),
        "high contrast, saturated, reads instantly when shrunk to 120 pixels wide",
        "aspect ratio 16:9, ultra sharp, no watermark, no logo",
    ]
    if cam:
        dong.append("Avoid: " + cam)
    return "\n".join(d for d in dong if d is not None)


# ── CHUẨN NGÁCH (lớp nền bắt buộc) + BỘ ÁO kênh ──────────────────────────────
#
# Nghiên cứu 493 bìa đối thủ (workspace/nghien-cuu-bia/BAO-CAO-BIA.md, 30/09/2026):
# KHÔNG đặc trưng bìa nào tách được video nổ khỏi video thường (CTR do đề tài và
# câu chữ), nhưng có một CHUẨN mà cả hai nhóm cùng theo — "vé vào cửa": chữ TRẦN
# viền dày (80%), chữ vàng/trắng cực lớn, từ khoá tô màu khác (78%), nền là CẢNH
# minh hoạ ấm (không nền trơn), nhân vật biểu cảm rõ. Bốn kênh mình đang lệch
# (TL1 chữ đen trong khối cam, nền trắng, mặt bình thản: CTR 1,7–2,9%).
#
# Luật đọc từ `ngach.yaml` khoá `bia_chuan_ngach` (ngách khác tự khai); thiếu
# khoá thì KHÔNG chèn lớp này (ngách chưa nghiên cứu thì không đoán).


def doc_chuan_ngach(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        from .ho_so_ngach import doc_ngach_tho, nhom_cua_kenh  # noqa: PLC0415
        nhom = nhom_cua_kenh(goc, kenh)
        tho = doc_ngach_tho(goc, nhom) if nhom else None
        cn = (tho or {}).get("bia_chuan_ngach")
        return dict(cn) if isinstance(cn, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


_TEN_MAU_VI = {"trang": "white #FFFFFF", "vang": "bright yellow #FFD400", "do": "pure red #E8202A",
               "den": "black #111111", "cam": "orange #FF8A00", "tim": "deep purple #2B0B4F",
               "xanh": "blue #1E6FE8", "xanh_dam": "dark navy #0E2A5A", "hong": "pink #FF4FA0"}


def _mau_vi_sang_hex(ten: str) -> str:
    return _TEN_MAU_VI.get(str(ten or "").strip().lower(), "").split(" ")[-1] if ten else ""


def khoi_chuan_ngach(cn: Dict[str, Any]) -> str:
    """`bia_chuan_ngach` → khối lời nhắc tiếng Anh (lớp bắt buộc cho mọi tấm)."""
    if not cn:
        return ""
    chu = cn.get("chu") or {}
    nen = cn.get("nen") or {}
    nv = cn.get("nhan_vat") or {}
    co = chu.get("co_lon_nhat_pct") or [22, 29]
    khung = chu.get("chiem_khung_pct") or [40, 55]
    mau = [_TEN_MAU_VI.get(m, m) for m in (chu.get("mau_chinh") or ["vang", "trang"])]
    dong = ["## NICHE STANDARD — MANDATORY FOR THIS THUMBNAIL (measured on {0} competitor thumbnails)".format(
        cn.get("so_bia_mau", "~500"))]
    dong.append("- text: BARE lettering, NO background boxes or plates, thick {0} outline on every "
                "line".format(_TEN_MAU_VI.get((chu.get("vien") or {}).get("mau", "den"), "black")))
    dong.append("- text colours: {0}; the key word of the hook in {1}".format(
        " or ".join(mau), _TEN_MAU_VI.get(chu.get("tu_khoa_mau_khac", "do"), "red")))
    dong.append("- {0} text lines, the BOTTOM line the biggest (about {1}-{2}% of frame height); all "
                "text together covers about {3}-{4}% of the frame".format(
                    "-".join(str(x) for x in (chu.get("so_tang") or [2, 3])), co[0], co[-1],
                    khung[0], khung[-1]))
    if nen.get("loai") == "canh_minh_hoa":
        dong.append("- background: a CONCRETE illustrated scene tied to the story (a room, a street, a desk…) "
                    "with {0} light — never a plain empty white, cream or black background".format(
                        {"am": "warm", "lanh": "cool"}.get(nen.get("anh_sang", "am"), "warm")))
    if nv.get("bieu_cam_ro"):
        tranh = ", ".join(nv.get("tranh_net_mat") or [])
        dong.append("- character: a CLEAR, strong facial expression readable at phone size, at least {0}% of the "
                    "frame height{1}".format(NHAN_VAT_TOI_THIEU_PCT,
                                             " (avoid: {0})".format({"buon": "a sad face"}.get(tranh, tranh)) if tranh else ""))
    dong.append("- illustration only: no real people, no photographs, no photo-realistic faces anywhere")
    dong.append("- must stay readable when shrunk to 120 px wide")
    return "\n".join(dong)


def khuon_tu_chuan_ngach(cn: Dict[str, Any]) -> Dict[str, Any]:
    """Khuôn cấu trúc GIẢ từ chuẩn ngách — để `viet_bien_the`/`ve_chu_len_anh`
    dùng chung một đường cho tấm "chuẩn ngách + bộ áo kênh"."""
    chu = (cn or {}).get("chu") or {}
    mau_chinh = [_mau_vi_sang_hex(m) or "#FFD400" for m in (chu.get("mau_chinh") or ["vang", "trang"])]
    tu_khoa = _mau_vi_sang_hex(chu.get("tu_khoa_mau_khac", "do")) or "#E8202A"
    co = chu.get("co_lon_nhat_pct") or [22, 29]
    trang = "#FFFFFF" if "#FFFFFF" in mau_chinh else mau_chinh[-1]
    vang = next((m for m in mau_chinh if m != "#FFFFFF"), "#FFD400")
    return {"chu": {"so_tang": 2, "tang": [
        {"vi_tri": "tren", "so_ky_tu": 8, "co_pct": float(co[0]) - 2, "mau": [trang],
         "vien": "thick black outline", "khoi_nen": False, "trich_dan": False},
        {"vi_tri": "duoi", "so_ky_tu": 10, "co_pct": float(co[-1]) - 2, "mau": [tu_khoa, vang],
         "vien": "thick black outline", "khoi_nen": False, "trich_dan": False}],
        "tu_to_mau": "the key word of the hook in red, the rest of the bottom line in yellow, top line white"},
        "nhan_vat": {"vi_tri": "phai", "tu_the": "expressive full-body pose",
                     "net_mat": "clear strong expression (surprised, knowing smile or indignant)"}}


def loi_nhac_chuan_ngach(cn: Dict[str, Any], *, bo_ao: Dict[str, str], bien_the: Dict[str, str],
                         chu_tang: Optional[Sequence[Dict[str, Any]]] = None,
                         chu_do_ma_ve: bool = True) -> str:
    """Tấm "CHUẨN NGÁCH + BỘ ÁO kênh": chuẩn ngách quyết chữ/nền/biểu cảm, bộ áo
    (style.yaml: nét vẽ, bảng màu, nhân vật tham chiếu) giữ nhận diện kênh."""
    kc = khuon_tu_chuan_ngach(cn)
    dong = [
        "psychology YouTube thumbnail designed for high click-through on a phone and a TV home feed",
        "use the attached character reference image for the character — same drawing style, do not redesign it",
        "",
        khoi_chuan_ngach(cn),
        "",
        "CHANNEL IDENTITY (keep it): drawing language — " + (bo_ao.get("phong_cach") or ""),
        "the scene's colours lean on the channel palette: {0} (its 'flat / no other colour / plain "
        "ground' limits do NOT apply to this thumbnail background — the niche standard above wins)".format(
            bo_ao.get("palette") or "channel colours"),
        "",
        "scene for this video: {0}; the character {1}, expression: {2}".format(
            bien_the.get("dao_cu") or "a place tied to the story",
            bien_the.get("tu_the") or "in an expressive full-body pose",
            bien_the.get("net_mat") or "clear strong emotion"),
        ("composition: the character on the LEFT third (about 50-60% of frame height), the key prop "
         "behind or beside the character" if chu_do_ma_ve else
         "composition: the character on one side (about 45-60% of frame height), text lines stacked on "
         "the other side and across the bottom, the key prop behind the character"),
        NHAN_VAT_LON,
        CAM_ANH_THAT,
    ]
    if chu_do_ma_ve:
        dong += ["", "ABSOLUTELY NO TEXT, NO LETTERS anywhere in the image — the title text is added later. "
                 "Keep the TOP-RIGHT area and the BOTTOM 30% of the frame free of important detail (only "
                 "the scene's walls/floor there) so large lettering can be laid over it."]
    elif chu_tang:
        dong += ["", _dong_chu_tang(chu_tang)]
    dong += ["", "rich WARM saturated light with strong contrast (deep shadows, bright warm highlights) — "
             "never a pale grey, washed-out or mostly empty background; the scene fills the frame",
             "high contrast, reads instantly at 120 pixels wide, aspect ratio 16:9, ultra sharp, "
             "no watermark, no logo"]
    if bo_ao.get("cam"):
        dong.append("Avoid: " + bo_ao["cam"])
    return "\n".join(dong)


def _dong_chu_tang(chu_tang: Sequence[Dict[str, Any]]) -> str:
    ten_vt = {"tren": "TOP", "giua": "MIDDLE", "duoi": "BOTTOM", "trai": "LEFT", "phai": "RIGHT"}
    dong = []
    for t in chu_tang:
        phan = [p for p in (t.get("phan_mau") or []) if p.get("chu")]
        ca_dong = "".join(p["chu"] for p in phan) or str(t.get("chu") or "")
        to_mau = ", ".join("「{0}」 {1}".format(p["chu"], _ten_mau(p.get("mau", "")).split(" #")[0])
                           for p in phan)
        dong.append("{0} text line (one single line, huge bare lettering, thick black outline, no "
                    "background box): 「{1}」{2}".format(
                        ten_vt.get(t.get("vi_tri", ""), "TOP"), ca_dong,
                        (" — colour the parts: " + to_mau) if len(phan) > 1 else
                        (" — " + to_mau if to_mau else "")))
    dong.append("the 「」 marks above only delimit the text — do not draw them. Spell every "
                "Japanese character EXACTLY as given, add no symbols between the coloured parts, "
                "and put NO other text anywhere (no labels, stamps, numbers or writing on props)")
    return "\n".join(dong)


# ── Biến thể theo video: chia chữ theo tầng + đạo cụ/tư thế/nét mặt ─────────


LOI_NHAC_BIEN_THE = """You prepare thumbnail VARIANTS for a YouTube channel that is REBUILDING its \
winning thumbnail design for a new video. The design is fixed; you decide only how the hook text \
is split into the design's text tiers and colours, and the per-video prop / pose / expression.

Winning design (measured from the real live thumbnail):
{khuon}
Winning thumbnail text tiers, for reference: {mau_chu}

New video title: {tieu_de}
Hook text (Japanese): {chu_bia}
{luat_chu}

Return JSON only:
{{"chu_tang": [
   {{"vi_tri": "tren", "phan_mau": [{{"chu": "...", "mau": "#FFFFFF"}}]}},
   {{"vi_tri": "duoi", "phan_mau": [{{"chu": "...", "mau": "#E8202A"}}, {{"chu": "...", "mau": "#FFD400"}}]}}
 ],
 "bien_the": [{{"dao_cu": "one symbolic prop (a plain object, no writing)", "tu_the": "dynamic full-body pose", \
"net_mat": "strong readable expression"}}, ... exactly {n} items]}}
Colour the tiers part-by-part exactly like the winner (same colour per role: e.g. subject red, key \
idea yellow, top line white). Each variant: a different prop and pose, all with a strong emotion \
that fits the story."""

_LUAT_CHU_CO_DINH = ("Use the hook text VERBATIM — split it into the tiers at a natural phrase break "
                     "and colour the parts, but do not change, add or reorder any character. HARD LIMITS: "
                     "each tier at most {0} characters, all tiers together at most {1} characters (shorter "
                     "is better) — if the hook is longer, DROP a leading or trailing clause, never rewrite.")
_LUAT_CHU_TU_DO = ("Keep the hook's meaning; you may shorten it. HARD LIMITS: each tier at most {0} "
                   "characters, all tiers together at most {1} characters — shorter is better.")

#: Trần ký tự chữ bìa — điều phối 30/09/2026: mỗi tầng ≤12, tổng ≤20 (bìa thắng
#: aV4: 8 + 10 = 18). Đếm bằng `_chuan` (bỏ dấu câu/khoảng trắng).
TRAN_KY_TU_TANG = 12
TRAN_KY_TU_TONG = 20
#: 06/10/2026 — trần trên đếm cho chữ Nhật/Hàn/Trung (một ký tự ≈ một âm tiết, ô vuông rộng). Chữ La-tinh
#: (en/vi/es…) cần ~gấp đôi ký tự cho cùng lượng ý và cùng bề ngang: 12/20 cắt cụt mọi bìa tiếng Anh.
HE_SO_TRAN_LA_TINH = 2


def tran_ky_tu(chu: str) -> Tuple[int, int]:
    """(trần mỗi tầng, trần tổng) cho chữ bìa `chu`: có kana/kanji/Hangul → (12, 20) như cũ; chỉ chữ
    La-tinh → nhân `HE_SO_TRAN_LA_TINH`."""
    if not chu or re.search(r"[\u1100-\u11ff\u3000-\u30ff\u3130-\u318f\u3400-\u9fff\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]", chu):
        return TRAN_KY_TU_TANG, TRAN_KY_TU_TONG
    return TRAN_KY_TU_TANG * HE_SO_TRAN_LA_TINH, TRAN_KY_TU_TONG * HE_SO_TRAN_LA_TINH


def _chuan(s: str) -> str:
    return re.sub(r"[\s\W_]+", "", s or "")


def chu_cua_tang(t: Dict[str, Any]) -> str:
    return "".join(p.get("chu", "") for p in (t.get("phan_mau") or [])) or str(t.get("chu") or "")


def kiem_chu_tang(chu_tang: Any, chu_bia: str, *, co_dinh: bool) -> bool:
    """Các tầng hợp lệ: có chữ, mỗi tầng ≤ TRAN_KY_TU_TANG, tổng ≤ TRAN_KY_TU_TONG;
    kênh cố định chữ thì mọi tầng nối lại phải là các đoạn (theo thứ tự) của
    chữ bìa gốc — cấm bịa câu mới."""
    if not isinstance(chu_tang, list) or not chu_tang:
        return False
    cac = [_chuan(chu_cua_tang(t)) for t in chu_tang if isinstance(t, dict)]
    tran_tang, tran_tong = tran_ky_tu(chu_bia or "".join(cac))
    if not all(cac) or any(len(c) > tran_tang for c in cac) or sum(map(len, cac)) > tran_tong:
        return False
    if co_dinh and chu_bia:
        goc = _chuan(chu_bia)
        vi_tri = 0
        for c in cac:
            k = goc.find(c, vi_tri)
            if k < 0:
                return False
            vi_tri = k + len(c)
    return True


def _cat_theo_tran(s: str) -> str:
    """Chữ bìa dài hơn TRAN_KY_TU_TONG → bỏ bớt mệnh đề ĐẦU (theo khoảng trắng/dấu
    câu) cho tới khi vừa; không có chỗ cắt thì giữ TRAN_KY_TU_TONG ký tự cuối."""
    tran = tran_ky_tu(s)[1]
    while len(_chuan(s)) > tran:
        m = re.search(r"[\s、。！？!?「」『』]+", s)
        if not m or m.end() >= len(s):
            s = s[-tran:]
            break
        s = s[m.end():].strip()
    return s


def tach_chu_mac_dinh(chu_bia: str, khuon_chu: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Đường lùi KHÔNG gọi AI: tách theo khoảng trắng/dấu câu (gần giữa nhất),
    tô màu theo vai trò của khuôn (tầng trên = màu tầng trên; tầng dưới chia
    đôi theo hai màu đầu của tầng dưới khuôn)."""
    tang_k = ((khuon_chu or {}).get("chu") or {}).get("tang") or []
    s = _cat_theo_tran((chu_bia or "").strip())
    cho = [m.end() for m in re.finditer(r"[\s、。！？!?]+", s)] or []
    giua = len(s) / 2.0
    cat = min(cho, key=lambda i: abs(i - giua)) if cho else int(round(giua))
    tren, duoi = s[:cat].strip(), s[cat:].strip()
    mau_tren = ((tang_k[0].get("mau") or ["#FFFFFF"])[0]) if tang_k else "#FFFFFF"
    mau_duoi = (tang_k[-1].get("mau") or ["#E8202A", "#FFD400"]) if len(tang_k) > 1 else ["#E8202A", "#FFD400"]
    ra = []
    if tren:
        ra.append({"vi_tri": "tren", "phan_mau": [{"chu": tren, "mau": mau_tren}]})
    if duoi:
        if len(mau_duoi) >= 2 and len(duoi) >= 4:
            k = len(duoi) // 2
            ra.append({"vi_tri": "duoi", "phan_mau": [{"chu": duoi[:k], "mau": mau_duoi[0]},
                                                      {"chu": duoi[k:], "mau": mau_duoi[-1]}]})
        else:
            ra.append({"vi_tri": "duoi", "phan_mau": [{"chu": duoi, "mau": mau_duoi[0]}]})
    return ra


#: 01/10/2026 — các cụm viết cứng cho kênh tâm lý Nhật trong lời nhắc ảnh bìa. Ngách KHÁC ngách mặc
#: định (`ho_so_ngach.la_ngach_mac_dinh`) được thay bằng thể loại/tiếng của chính nó (`ban_dia_hoa`);
#: ngách mặc định giữ nguyên từng ký tự.
_CUM_CUNG = (
    ("psychology YouTube thumbnail", "{the_loai} YouTube thumbnail"),
    ("for a Japanese psychology channel", "for a {tieng} {the_loai} channel"),
    ("Hook text (Japanese)", "Hook text ({tieng})"),
    ("Spell every Japanese character EXACTLY", "Spell every character EXACTLY"),
    ("the Japanese text is spelled exactly", "the {tieng} text is spelled exactly"),
    ("the orange-headed stick character, placed", "the channel's reference character, placed"),
    ("character is recognisably the SAME character (orange round head, black stick body)",
     "character is recognisably the SAME character as the channel's reference character"),
    ("(like Noto Sans JP Black)", "(heavy sans that supports {tieng} letters)"),
)


def ban_dia_hoa(chu: str, goc: str, kenh: str) -> str:
    """Thay các cụm "psychology / Japanese" viết cứng trong lời nhắc bìa bằng thể loại + tiếng của
    ngách kênh. Ngách mặc định (tâm lý Nhật) hoặc đọc hồ sơ hỏng → trả NGUYÊN `chu`."""
    if not chu or not goc or not kenh:
        return chu
    try:
        from . import ho_so_ngach  # noqa: PLC0415
        from .kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

        hs = ho_so_ngach.doc_ngach(goc, kenh)
        if ho_so_ngach.la_ngach_mac_dinh(hs):
            return chu
        ma_tieng = str((doc_yaml(os.path.join(duong_kenh(goc, kenh), TEP_KENH)) or {}).get("ngon_ngu")
                       or hs.ngon_ngu() or "")
        tieng = ho_so_ngach.ten_tieng(ma_tieng, anh=True) or "local-language"
        the_loai = (hs.the_loai_en or "").strip() or "niche"
    except Exception:  # noqa: BLE001
        return chu
    for cu, moi in _CUM_CUNG:
        if cu in chu:
            chu = chu.replace(cu, moi.replace("{the_loai}", the_loai).replace("{tieng}", tieng))
    return chu


def viet_bien_the(goi_chat: Optional[Callable[..., str]], khuon_chu: Dict[str, Any], *,
                  tieu_de: str, chu_bia: str, n: int, co_dinh_chu: bool,
                  mo_hinh: str = "", khoa: str = "",
                  ban_dia: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """`{chu_tang, bien_the[n]}` — AI hỏng/vi phạm luật chữ thì lùi `tach_chu_mac_dinh`.

    `ban_dia` (01/10/2026): hàm bản địa hoá lời nhắc theo ngách (`ban_dia_hoa`); `None` = nguyên văn."""
    from .goi_van_ban import loc_json  # noqa: PLC0415
    kc = khuon_chu or {}
    tang_k = (kc.get("chu") or {}).get("tang") or []
    tong = tong_ky_tu_khuon(kc) or 18
    mau_chu = json.dumps([{"vi_tri": t.get("vi_tri"), "noi_dung": t.get("noi_dung"),
                           "phan_mau": t.get("phan_mau")} for t in tang_k], ensure_ascii=False)
    _ = tong
    luat = (_LUAT_CHU_CO_DINH if co_dinh_chu else _LUAT_CHU_TU_DO).format(*tran_ky_tu(chu_bia))
    ra: Dict[str, Any] = {}
    if goi_chat is not None:
        try:
            kw: Dict[str, Any] = {"toi_da_token": 1500}
            if mo_hinh:
                kw["mo_hinh"] = mo_hinh
            if khoa:
                kw["khoa"] = khoa
            loi_nhac = LOI_NHAC_BIEN_THE.format(
                khuon=khoi_khuon_tieng_anh(kc), mau_chu=mau_chu, tieu_de=tieu_de, chu_bia=chu_bia,
                luat_chu=luat, n=n)
            if ban_dia is not None:
                loi_nhac = ban_dia(loi_nhac)
            du = loc_json(str(goi_chat(loi_nhac, **kw) or ""))
            if isinstance(du, dict):
                ra = du
        except Exception:  # noqa: BLE001
            ra = {}
    if not kiem_chu_tang(ra.get("chu_tang"), chu_bia, co_dinh=co_dinh_chu):
        ra["chu_tang"] = tach_chu_mac_dinh(chu_bia, kc)
        ra["chu_tang_lui"] = True
    bt = [b for b in (ra.get("bien_the") or []) if isinstance(b, dict)]
    nv = kc.get("nhan_vat") or {}
    while len(bt) < n:
        bt.append({"dao_cu": "", "tu_the": nv.get("tu_the", ""), "net_mat": nv.get("net_mat", "")})
    ra["bien_the"] = bt[:n]
    return ra


# ── Bộ vẽ chữ (chữ trần nhiều màu, viền đậm, 2 tầng) ─────────────────────────


_FONT_UU_TIEN = ("YuGothB.ttc", "meiryob.ttc", "msgothic.ttc", "YuGothM.ttc", "meiryo.ttc",
                 "NotoSansJP-Black.otf", "NotoSansCJK-Black.ttc")


#: 06/10/2026 — máy/ngách khác tiếng (thử dựng ngách nấu ăn Hàn): Yu Gothic/Meiryo KHÔNG có chữ Hangul (bìa ra ô
#: vuông) và thiếu nhiều chữ La-tinh có dấu (tiếng Việt). Chọn bộ font theo CHỮ sẽ vẽ (+ tiếng kênh nếu biết);
#: chữ Nhật (có kana/kanji) giữ nguyên thứ tự cũ.
_FONT_HAN = ("malgunbd.ttf", "NotoSansKR-Black.otf", "NotoSansCJKkr-Black.otf", "NotoSansCJK-Black.ttc",
             "malgun.ttf", "gulim.ttc")
_FONT_LA_TINH = ("arialbd.ttf", "segoeuib.ttf", "NotoSans-Black.ttf", "DejaVuSans-Bold.ttf", "arial.ttf",
                 "segoeui.ttf")
_RE_HANGUL = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7af]")
_RE_CJK_NHAT_TRUNG = re.compile(r"[\u3000-\u30ff\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]")


def bo_font_cho(chu: str = "", ngon_ngu: str = "") -> Tuple[str, ...]:
    """Thứ tự tên tệp font nên thử cho chữ `chu` (kênh tiếng `ngon_ngu`, có thể rỗng).

    - có Hangul, hoặc kênh `ko` mà chữ không có kana/kanji → font Hàn trước;
    - không kana/kanji/Hangul, và (kênh khai tiếng khác ja/zh, hoặc chữ có ký tự ngoài ASCII như chữ Việt có dấu)
      → font La-tinh trước;
    - còn lại (chữ Nhật, hoặc chữ ASCII trơn mà không biết tiếng kênh) → thứ tự cũ (font Nhật)."""
    chu = str(chu or "")
    nn = str(ngon_ngu or "").strip().lower().split("-")[0].split("_")[0]
    co_cjk = bool(_RE_CJK_NHAT_TRUNG.search(chu))
    if _RE_HANGUL.search(chu) or (nn == "ko" and not co_cjk):
        return _FONT_HAN + _FONT_UU_TIEN
    if not co_cjk and ((nn and nn not in ("ja", "zh")) or (not nn and re.search(r"[^\x00-\x7f]", chu))):
        return _FONT_LA_TINH + _FONT_UU_TIEN
    return ("NotoSansJP-Black.otf",) + _FONT_UU_TIEN


def _tim_font(goc: str = "", chu: str = "", ngon_ngu: str = "") -> str:
    cho = []
    if goc:
        cho.append(os.path.join(goc, "assets", "fonts"))
    cho.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    cho.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"))
    for thu_muc in cho:
        for ten in bo_font_cho(chu, ngon_ngu):
            d = os.path.join(thu_muc, ten)
            if os.path.isfile(d):
                return d
    return ""


def _mau_rgb(hexm: str, mac_dinh: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    m = _RE_HEX.search(hexm or "")
    if not m:
        return mac_dinh
    h = m.group(0)
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


#: Luật bố cục chữ do code vẽ — điều phối chốt 30/09/2026 sau khi xem bảng thử:
#: tổng chữ chiếm ~40–55% diện tích, mỗi tầng cao ≥18% khung, tầng CHÍNH ≥25%,
#: không để khoảng trống lớn. "Cao" = chiều cao KHỐI của tầng (1 hoặc 2 dòng).
TANG_TOI_THIEU_PCT = 18.0
TANG_CHINH_TOI_THIEU_PCT = 25.0
DIEN_TICH_CHU_PCT = (40.0, 55.0)
#: Một dòng chữ không cao quá ngần này % khung (chữ khổng lồ 3 ký tự nhìn như lỗi).
DONG_TOI_DA_PCT = 30.0


def _cat_doan(doan: List[Dict[str, str]], k: int) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Cắt danh sách đoạn màu tại ký tự thứ k (giữ màu từng đoạn)."""
    a: List[Dict[str, str]] = []
    b: List[Dict[str, str]] = []
    dem = 0
    for p in doan:
        s = p["chu"]
        if dem + len(s) <= k:
            a.append(dict(p))
        elif dem >= k:
            b.append(dict(p))
        else:
            cat = k - dem
            a.append(dict(p, chu=s[:cat]))
            b.append(dict(p, chu=s[cat:]))
        dem += len(s)
    return [p for p in a if p["chu"].strip()], [p for p in b if p["chu"].strip()]


def _cho_xuong_dong(s: str) -> int:
    """Chỗ xuống dòng tốt nhất gần giữa: sau khoảng trắng/dấu câu/trợ từ, không
    bao giờ để một trợ từ đứng đầu dòng sau."""
    giua = len(s) / 2.0
    tot: List[int] = [i + 1 for i, c in enumerate(s[:-1]) if c in " 　、。」』！？!?"]
    tot += [i + 1 for i, c in enumerate(s[:-1]) if c in "はがをにでともの" and 1 < i + 1 < len(s) - 1]
    if tot:
        return min(tot, key=lambda i: abs(i - giua))
    return max(1, int(round(giua)))


def ve_chu_len_anh(nen: str, dich: str, chu_tang: Sequence[Dict[str, Any]], *,
                   goc: str = "", kich_thuoc: Tuple[int, int] = (1280, 720), ngon_ngu: str = "") -> bool:
    """Vẽ các tầng chữ lên ảnh nền `nen` → `dich` (PNG). Mỗi tầng:
    `{vi_tri: tren|duoi, phan_mau:[{chu, mau}], co_pct, chinh, vung, can, khoi_nen}`.

    Chữ TRẦN, mỗi đoạn một màu, viền đen dày + bóng đổ; `khoi_nen` true thì vẽ
    khối đen bo góc phía sau. Bố cục theo luật điều phối (xem hằng trên): tầng
    thiếu chiều cao thì XUỐNG 2 DÒNG, tổng diện tích chữ < 40% thì phóng to dần,
    > 55% thì thu lại; tầng trên và dưới không được đè nhau. Trả False nếu không
    có font/không mở được ảnh."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps  # noqa: PLC0415

    font_duong = _tim_font(goc, "".join(chu_cua_tang(t) for t in chu_tang if isinstance(t, dict)), ngon_ngu)
    if not font_duong:
        return False
    try:
        anh = ImageOps.fit(Image.open(nen).convert("RGB"), kich_thuoc, method=Image.LANCZOS)
    except (OSError, ValueError):
        return False
    W, H = anh.size
    le = int(W * 0.018)
    do = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    _cache: Dict[int, Any] = {}

    def font(c: int):
        c = max(12, int(c))
        if c not in _cache:
            _cache[c] = ImageFont.truetype(font_duong, c)
        return _cache[c]

    def vien_cua(c: int, t: Dict[str, Any]) -> int:
        return max(3, int(c * float(t.get("vien_px_pct") or 0.075)))

    def rong_dong(doan, c, t) -> float:
        return sum(do.textlength(p["chu"], font=font(c)) for p in doan) + 2 * vien_cua(c, t) + c * 0.07

    def hop_dong(c: int, t) -> float:  # chiều cao hộp một dòng (có viền)
        return c * 1.12 + 2 * vien_cua(c, t)

    def co_vua(doan, t, rong_vung) -> int:
        c = int(H * DONG_TOI_DA_PCT / 100.0 / 1.25)
        while c > 14 and rong_dong(doan, c, t) > rong_vung:
            c -= 2
        return c

    # 1) Mỗi tầng: 1 dòng hay 2 dòng — chọn cách cho KHỐI cao hơn (đạt ngưỡng).
    bo: List[Dict[str, Any]] = []
    for t in chu_tang:
        doan = [dict(p) for p in (t.get("phan_mau") or []) if p.get("chu")]
        if not doan and t.get("chu"):
            doan = [{"chu": t["chu"], "mau": (t.get("mau") or ["#FFFFFF"])[0]}]
        if not doan:
            continue
        vung = t.get("vung") or (0.0, 1.0)
        vx0, vx1 = int(W * float(vung[0])) + le, int(W * float(vung[1])) - le
        rv = vx1 - vx0
        toi_thieu = (TANG_CHINH_TOI_THIEU_PCT if t.get("chinh") else TANG_TOI_THIEU_PCT) / 100.0 * H
        c1 = co_vua(doan, t, rv)
        cach = {"dong": [doan], "co": c1}
        s = "".join(p["chu"] for p in doan)
        if hop_dong(c1, t) < toi_thieu and len(_chuan(s)) >= 4:
            a, b = _cat_doan(doan, _cho_xuong_dong(s))
            if a and b:
                c2 = min(co_vua(a, t, rv), co_vua(b, t, rv))
                if 2 * hop_dong(c2, t) > hop_dong(c1, t) * 1.15:
                    cach = {"dong": [a, b], "co": c2}
        bo.append({"t": t, "vx0": vx0, "vx1": vx1, **cach})
    if not bo:
        return False

    def dien_tich() -> float:
        return sum(rong_dong(d, b["co"], b["t"]) * hop_dong(b["co"], b["t"])
                   for b in bo for d in b["dong"]) / float(W * H) * 100.0

    def cao_khoi(b) -> float:
        return len(b["dong"]) * hop_dong(b["co"], b["t"])

    def chong_nhau() -> bool:
        tren = sum(cao_khoi(b) for b in bo if str(b["t"].get("vi_tri") or "tren") == "tren")
        duoi = sum(cao_khoi(b) for b in bo if str(b["t"].get("vi_tri") or "tren") != "tren")
        return tren + duoi > H * 0.93

    # 2) Cân diện tích chữ về 40–55% mà không đè nhau / không tràn bề ngang.
    for _ in range(30):
        dt = dien_tich()
        if dt > DIEN_TICH_CHU_PCT[1] or chong_nhau():
            for b in bo:
                b["co"] = max(14, int(b["co"] * 0.95))
            continue
        if dt >= DIEN_TICH_CHU_PCT[0]:
            break
        lon_duoc = False
        for b in bo:
            c_moi = int(b["co"] * 1.05) + 1
            if (all(rong_dong(d, c_moi, b["t"]) <= b["vx1"] - b["vx0"] for d in b["dong"])
                    and hop_dong(c_moi, b["t"]) <= H * DONG_TOI_DA_PCT / 100.0):
                b["co"] = c_moi
                lon_duoc = True
        if not lon_duoc or chong_nhau():
            if chong_nhau():
                for b in bo:
                    b["co"] = max(14, int(b["co"] * 0.97))
            break

    # 3) Vẽ: tầng "tren" xếp từ mép trên xuống, tầng khác từ mép dưới lên.
    lop = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    bong = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    ve = ImageDraw.Draw(lop)
    ve_bong = ImageDraw.Draw(bong)
    y_tren = int(H * 0.03)
    y_duoi = H - int(H * 0.045)
    ds_duoi = [b for b in bo if str(b["t"].get("vi_tri") or "tren") != "tren"]
    for b in bo:
        if b in ds_duoi:
            continue
        for d in b["dong"]:
            y_tren = _ve_mot_dong(ve, ve_bong, d, b, font, vien_cua, rong_dong, hop_dong, y_tren, W, True)
    for b in reversed(ds_duoi):
        for d in reversed(b["dong"]):
            y_duoi = _ve_mot_dong(ve, ve_bong, d, b, font, vien_cua, rong_dong, hop_dong, y_duoi, W, False)
    bong = bong.filter(ImageFilter.GaussianBlur(max(2, W // 320)))
    ket = Image.alpha_composite(Image.alpha_composite(anh.convert("RGBA"), bong), lop).convert("RGB")
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    tam = dich + ".tmp.png"
    ket.save(tam, format="PNG")
    os.replace(tam, dich)
    return True


def _ve_mot_dong(ve, ve_bong, doan, b, font, vien_cua, rong_dong, hop_dong, y_moc: float, W: int,
                 tu_tren: bool) -> float:
    t, c = b["t"], b["co"]
    f = font(c)
    vien = vien_cua(c, t)
    rong = rong_dong(doan, c, t)
    can = str(t.get("can") or "giua")
    vx0, vx1 = b["vx0"], b["vx1"]
    x = (vx0 if can == "trai" else (vx1 - rong) if can == "phai" else vx0 + (vx1 - vx0 - rong) / 2) + vien
    tren, _t, _r, duoi = f.getbbox("低IQの人")
    h = hop_dong(c, t)
    top = y_moc if tu_tren else y_moc - h
    y = top + vien - tren + c * 0.04
    if t.get("khoi_nen"):
        ve.rounded_rectangle([x - vien * 2, top, x + rong - vien, top + h], radius=int(c * 0.2),
                             fill=(20, 20, 20, 235))
    # "Đậm giả": Yu Gothic Bold mảnh hơn nét Black của bìa thật — viền ĐEN rộng
    # (dam + vien) trước, rồi chữ kèm viền CÙNG MÀU (dam) đè lên.
    dam = max(1, int(c * 0.022))
    x0 = x
    for p in doan:
        ve_bong.text((x + vien * 0.6, y + vien * 0.9), p["chu"], font=f, fill=(0, 0, 0, 200),
                     stroke_width=vien + dam, stroke_fill=(0, 0, 0, 200))
        ve.text((x, y), p["chu"], font=f, fill=(12, 8, 18, 255),
                stroke_width=vien + dam, stroke_fill=(12, 8, 18, 255))
        x += ve.textlength(p["chu"], font=f)
    x = x0
    for p in doan:
        mau = _mau_rgb(p.get("mau", ""), (255, 255, 255))
        ve.text((x, y), p["chu"], font=f, fill=mau + (255,), stroke_width=dam, stroke_fill=mau + (255,))
        x += ve.textlength(p["chu"], font=f)
    return top + h if tu_tren else top


def bo_tri_chu(loai: str, chu_tang: Sequence[Dict[str, Any]],
               khuon_chu: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Gán vùng/canh/vai "tầng chính" cho từng tầng trước `ve_chu_len_anh`.

    - "khuon": theo bìa thắng — mọi tầng căn giữa, trải cả bề ngang; tầng dưới là
      tầng chính.
    - "chuan_ngach": nhân vật bên TRÁI, tầng trên ở 64% bên PHẢI (tự xuống 2 dòng
      nếu dài), tầng dưới trải cả bề ngang và là tầng chính.
    Cỡ chữ do `ve_chu_len_anh` tự cân theo luật diện tích/chiều cao."""
    ra = []
    for t in chu_tang:
        t2 = dict(t)
        vt = str(t.get("vi_tri") or "tren")
        chinh = vt != "tren"
        if loai == "chuan_ngach" and vt == "tren":
            t2.update(vung=(0.36, 1.0), can="phai", chinh=False)
        else:
            t2.update(vung=(0.0, 1.0), can="giua", chinh=chinh)
        ra.append(t2)
    return ra


def nen_nhat(duong: str) -> bool:
    """Ảnh nền "xám nhạt" (bão hoà thấp VÀ tương phản thấp) — luật điều phối:
    cảnh nền phải có ánh sáng ấm hoặc đủ tương phản."""
    try:
        from PIL import Image, ImageOps  # noqa: PLC0415
        im = ImageOps.fit(Image.open(duong).convert("HSV"), (64, 36))
    except (OSError, ValueError):
        return False
    _h, s, v = im.split()
    ds_s = list(s.getdata())
    ds_v = list(v.getdata())
    return (statistics.mean(ds_s) < 55 and statistics.pstdev(ds_v) < 48)


# ── So bìa thật ↔ bìa tool chọn ─────────────────────────────────────────────


def khac_bia_tool(anh_a: str, anh_b: str) -> Optional[float]:
    """Chênh trung bình tuyệt đối (0-255) trên lưới xám 32×18 — None nếu thiếu ảnh."""
    try:
        from PIL import Image, ImageOps  # noqa: PLC0415
        a = ImageOps.fit(Image.open(anh_a).convert("L"), (32, 18))
        b = ImageOps.fit(Image.open(anh_b).convert("L"), (32, 18))
    except (OSError, ValueError):
        return None
    pa, pb = list(a.getdata()), list(b.getdata())
    return sum(abs(x - y) for x, y in zip(pa, pb)) / float(len(pa))


# ── Vòng học sau mỗi video ──────────────────────────────────────────────────

#: Tỉ trọng A/B mặc định giữa các nhóm tấm KHI KHAI THÁC (lượt không phải lượt
#: thăm dò tất định). Điều phối 30/09: bằng chứng khuôn yếu (C432 cùng khuôn chỉ
#: 4,04%) — đo A/B thật theo CTR trang chủ @48h rồi tự dồn tỉ trọng.
TY_TRONG_MAC_DINH = {"khuon": 0.6, "chuan_ngach": 0.4}
TY_TRONG_SAN = 0.2


def _moc_danh_gia(hs: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
    """(ctr, imp, giờ) — mốc 48h trước, lùi 72h. CTR TỔNG (`ctr`), KHÔNG lấy `ctr_trang_chu`:
    `khuon["ctr"]` (mốc so "tụt") là CTR tổng của video khuôn — 01/10/2026 hồ sơ bắt đầu có
    `ctr_trang_chu` (giám đốc kênh), đổi thước giữa chừng sẽ làm "tụt" giả."""
    for ten in ("48h", "72h"):
        m = (hs.get("chi_so") or {}).get(ten)
        if not isinstance(m, dict) or m.get("ctr") is None:
            continue
        return float(m.get("ctr")), float(m.get("impressions") or 0), float(m.get("moc_gio_that") or 0)
    return None


def _sua_bia_giam_doc(hs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Lần đổi bìa CUỐI do giám đốc kênh làm (`lich_su_sua[]` có `doi_boi: "giam_doc"`), hoặc None."""
    for m in reversed(list(hs.get("lich_su_sua") or [])):
        if isinstance(m, dict) and m.get("loai") == "bia" and m.get("doi_boi") == "giam_doc":
            return m
    return None


def nhom_cua_thumbnail(th: Dict[str, Any]) -> str:
    nhom = str(th.get("nhom") or "")
    if nhom:
        return nhom
    if th.get("theo_khuon"):
        return "khuon"
    return "tham_do" if th.get("tham_do") else ""


def hoc_sau_video(goc: str, kenh: str, khuon: Dict[str, Any], *,
                  anh_that_cua: Optional[Callable[[str], str]] = None) -> Dict[str, Any]:
    """Cập nhật `khuon["hoc"]` từ hồ sơ video của CHÍNH kênh — trả khối `hoc` mới.

    - Tính video có video_id, đã tới mốc 48/72h, ≥ IMP_TOI_THIEU_DANH_GIA.
    - Bìa trên YouTube KHÁC bìa tool chọn (chủ kênh đổi bìa tay) → GHI LẠI (bìa
      thật khớp CTR thật — dữ liệu quý: aV4 là bìa tay, `khuon_bia` đã học từ ảnh
      thật) nhưng LOẠI khỏi thống kê "kiểu tool sinh" (khuon/chuan_ngach/tham_do).
    - Video theo khuôn: CTR < HE_SO_TUT × CTR khuôn = "tụt"; tụt liên tiếp
      SO_LAN_TUT_HA_TIN lần → hạ độ tin BUOC_HA_TIN (≥ DO_TIN_SAN); đạt ≥0,9× →
      hồi độ tin.
    - Tỉ trọng A/B khuon ↔ chuan_ngach dồn theo CTR trung bình của từng nhóm
      (mỗi nhóm ≥2 video), sàn TY_TRONG_SAN.
    - Video THĂM DÒ thắng rõ thì `khuon_bia.cap_nhat` tự đổi người thắng.
    """
    from . import ho_so_video  # noqa: PLC0415
    hoc = dict(khuon.get("hoc") or {})
    do_tin = float(hoc.get("do_tin", 1.0))
    ctr_khuon = float(khuon.get("ctr") or 0.0)
    da_tinh = set(hoc.get("da_tinh") or [])
    so_tut = int(hoc.get("so_tut_lien_tiep", 0))
    nhat_ky = list(hoc.get("nhat_ky") or [])[-60:]
    thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
    try:
        ten_tep = sorted(t for t in os.listdir(thu_muc) if t.endswith(".json"))
    except OSError:
        ten_tep = []
    for ten in ten_tep:
        ma_goi = ten[:-5]
        if ma_goi in da_tinh:
            continue
        hs = ho_so_video.doc_ho_so(goc, kenh, ma_goi)
        if not isinstance(hs, dict) or not hs.get("video_id"):
            continue
        if hs.get("video_id") == khuon.get("video_id"):
            continue
        th = hs.get("thumbnail") or {}
        moc = _moc_danh_gia(hs)
        if moc is None or moc[1] < IMP_TOI_THIEU_DANH_GIA:
            continue
        nhom = nhom_cua_thumbnail(th)
        dong = {"ma_goi": ma_goi, "video_id": hs["video_id"], "ctr": moc[0], "imp": moc[1],
                "nhom": nhom, "kieu": th.get("kieu", "")}
        sua_gd = _sua_bia_giam_doc(hs)
        if sua_gd is not None:
            # Bìa trên YouTube khác bìa tool chọn vì GIÁM ĐỐC KÊNH đổi (bìa hạng nhì) — không phải bìa
            # tay. Mốc đo trước lúc đổi vẫn là số của bìa tool chọn → tính như thường; đổi trước mốc
            # thì số trộn hai bìa → không tính.
            dong["doi_boi"] = "giam_doc"
            luc_moc = next((str(m.get("luc_chup") or "") for m in (hs.get("chi_so") or {}).values()
                            if isinstance(m, dict) and float(m.get("moc_gio_that") or -1) == moc[2]), "")
            if luc_moc and str(sua_gd.get("luc") or "").replace("T", " ")[:16] < luc_moc[:16]:
                da_tinh.add(ma_goi)
                dong["ket_qua"] = "giám đốc đổi bìa trước mốc đo — không tính"
                nhat_ky.append(dong)
                continue
        elif anh_that_cua is not None:
            duong_that = anh_that_cua(str(hs["video_id"]))
            duong_tool = ho_so_video.duong_anh_ho_so(goc, kenh, ma_goi)
            chenh = khac_bia_tool(duong_that, duong_tool) if duong_that else None
            if chenh is not None and chenh > NGUONG_KHAC_BIA:
                dong.update(bia_tay=True, chenh=round(chenh, 1))
        da_tinh.add(ma_goi)
        if dong.get("bia_tay") or not nhom:
            dong["ket_qua"] = "bia_tay — không tính vào thống kê kiểu tool" if dong.get("bia_tay") \
                else "trước cơ chế nhóm — không tính"
            nhat_ky.append(dong)
            continue
        if nhom == "khuon":
            if ctr_khuon and moc[0] < HE_SO_TUT * ctr_khuon:
                so_tut += 1
                dong["ket_qua"] = "tut"
                if so_tut >= SO_LAN_TUT_HA_TIN:
                    do_tin = max(DO_TIN_SAN, round(do_tin - BUOC_HA_TIN, 3))
                    so_tut = 0
                    dong["ket_qua"] = "tut — hạ độ tin còn {0}".format(do_tin)
            else:
                so_tut = 0
                if ctr_khuon and moc[0] >= 0.9 * ctr_khuon:
                    do_tin = min(1.0, round(do_tin + BUOC_HA_TIN, 3))
                dong["ket_qua"] = "giu"
        elif nhom == "tham_do" and ctr_khuon and moc[0] >= ctr_khuon:
            dong["ket_qua"] = "tham_do_thang"
        else:
            dong["ket_qua"] = "ghi_nhan"
        nhat_ky.append(dong)
    # Tỉ trọng A/B theo CTR trung bình nhóm (chỉ video tool sinh, không bìa tay).
    theo_nhom: Dict[str, List[float]] = {}
    for d in nhat_ky:
        if d.get("bia_tay") or d.get("nhom") not in TY_TRONG_MAC_DINH:
            continue
        theo_nhom.setdefault(d["nhom"], []).append(float(d.get("ctr") or 0))
    ty = dict(TY_TRONG_MAC_DINH)
    if all(len(theo_nhom.get(k, [])) >= 2 for k in ty):
        tb = {k: statistics.mean(v) for k, v in theo_nhom.items() if k in ty}
        tong = sum(tb.values()) or 1.0
        ty = {k: max(TY_TRONG_SAN, tb[k] / tong) for k in ty}
        s = sum(ty.values())
        ty = {k: round(v / s, 3) for k, v in ty.items()}
    hoc.update(do_tin=do_tin, so_tut_lien_tiep=so_tut, da_tinh=sorted(da_tinh), ty_trong=ty,
               nhat_ky=nhat_ky[-60:], cap_nhat=_dt.datetime.now().replace(microsecond=0).isoformat())
    return hoc


# ── Kế hoạch bộ bìa của MỘT video (khâu bìa `auto_khau` đọc) ────────────────

TEP_KE_HOACH = "ke-hoach-bia.json"
#: Số tệp cho tấm theo khuôn / chuẩn ngách — nằm NGOÀI 1..7 của `KIEU_THUMB`
#: (hồ sơ cũ nối tên tệp ↔ kiểu theo vị trí; không được đè mối nối đó).
SO_KHUON_DAU = 7
SO_CHUAN_NGACH_DAU = 13


def chon_nhom_ab(ma_goi: str, ty_trong: Dict[str, float]) -> str:
    """Nhóm được CHỌN cho video này (lượt không phải thăm dò) — tất định theo
    sha1(mã gói), trọng số `ty_trong`."""
    ds = [(k, float(v)) for k, v in sorted((ty_trong or TY_TRONG_MAC_DINH).items()) if float(v) > 0]
    if not ds:
        return "khuon"
    h = int(hashlib.sha1(("ab:" + (ma_goi or "")).encode("utf-8")).hexdigest()[:8], 16) / float(0xFFFFFFFF)  # noqa: S324
    tong = sum(v for _k, v in ds)
    tich = 0.0
    for k, v in ds:
        tich += v / tong
        if h <= tich:
            return k
    return ds[-1][0]


def _kieu_it_dung(goc: str, kenh: str, kieu_goc: Sequence[Tuple[str, str]], n: int) -> List[int]:
    """Chỉ số (0-based) của n kiểu LLM ít dùng nhất trong 12 hồ sơ gần nhất."""
    from . import ho_so_video  # noqa: PLC0415
    dem: Dict[str, int] = {t: 0 for t, _m in kieu_goc}
    try:
        thu_muc = ho_so_video.duong_thu_muc_ho_so(goc, kenh)
        ten_tep = sorted((t for t in os.listdir(thu_muc) if t.endswith(".json")), reverse=True)[:12]
        for ten in ten_tep:
            hs = ho_so_video.doc_ho_so(goc, kenh, ten[:-5]) or {}
            k = (hs.get("thumbnail") or {}).get("kieu") if isinstance(hs.get("thumbnail"), dict) else ""
            if k in dem:
                dem[k] += 1
    except Exception:  # noqa: BLE001
        pass
    thu_tu = sorted(range(len(kieu_goc)), key=lambda i: (dem.get(kieu_goc[i][0], 0), i))
    return sorted(thu_tu[:max(0, n)])


def ke_hoach_bia(goc: str, kenh: str, *, ma_goi: str, so_thumbnail: int,
                 kieu_goc: Sequence[Tuple[str, str]], cho_tam_khuon: bool = False) -> Dict[str, Any]:
    """Kế hoạch bộ bìa: `{che_do, ly_do, muc:[{so, kieu, mo_ta, nhom, ve_chu}],
    nhom_uu_tien, luot_tham_do, khuon, chuan_ngach, cau_hinh}`. KHÔNG ném lỗi.

    `kieu_goc` = danh sách (tên, mô tả) kiểu do AI viết lời nhắc (KIEU_THUMB sau
    các bộ lọc của `auto_khau`, KHÔNG gồm `khuon_thang`), đúng vị trí 1..n.

    - KHAI THÁC (khuôn đủ bằng chứng + đã qua vòng thử): 3 tấm theo khuôn, 2
      tấm chuẩn ngách + bộ áo, phần còn lại là THĂM DÒ (kiểu ít dùng nhất).
      Nhóm được chọn: lượt thăm dò tất định (1/N) → "tham_do"; còn lại A/B
      khuon ↔ chuan_ngach theo `hoc.ty_trong`.
    - THĂM DÒ (chưa có khuôn đủ bằng chứng): giữ các kiểu cũ; tấm `khuon_thang`
      vô nghĩa (không có khuôn) đổi thành 1 tấm chuẩn ngách nếu ngách có chuẩn.
    - "can_thu": khuôn đủ bằng chứng nhưng CHƯA qua vòng tạo thử — người gọi
      chạy vòng thử nhỏ (`auto_khau._thu_khuon_nho`) rồi gọi lại.
    """
    ch = cau_hinh_kenh(goc, kenh)
    cn = doc_chuan_ngach(goc, kenh)
    tt = trang_thai_khai_thac(goc, kenh)
    ve = ch.get("bia_ve_chu", "tron")

    def cach_ve(i: int) -> str:
        if ve in ("ma", "mo_hinh"):
            return ve
        return "mo_hinh" if i % 2 == 0 else "ma"

    ra: Dict[str, Any] = {"che_do": "tham_do", "ly_do": tt.get("ly_do", ""), "muc": [],
                          "nhom_uu_tien": None, "luot_tham_do": False, "khuon": None,
                          "chuan_ngach": cn, "cau_hinh": ch}
    khuon = tt.get("khuon")
    if tt.get("che_do") == "khai_thac" and khuon:
        thu = khuon.get("thu") or {}
        if thu.get("trang_thai") != "dat":
            if int(thu.get("so_lan") or 0) >= 2 and thu.get("trang_thai") == "khong_dat":
                ra["ly_do"] = "khuôn đủ bằng chứng nhưng vòng thử 2 lần không đạt — giữ thăm dò"
            else:
                ra.update(che_do="can_thu", khuon=khuon)
                return ra
        else:
            n = max(1, int(so_thumbnail))
            n_khuon = min(int(tt.get("so_tam_theo_khuon") or 3), max(1, n - 1))
            n_cn = min(2 if cn else 0, max(0, n - n_khuon - 1))
            n_td = max(0, n - n_khuon - n_cn)
            muc = [{"so": SO_KHUON_DAU + i, "kieu": TIEN_TO_KHUON if i == 0 else "{0}_{1}".format(TIEN_TO_KHUON, i + 1),
                    "mo_ta": "rebuild the channel's measured winning thumbnail", "nhom": "khuon",
                    "ve_chu": cach_ve(i)} for i in range(n_khuon)]
            muc += [{"so": SO_CHUAN_NGACH_DAU + i, "kieu": "chuan_ngach" if i == 0 else "chuan_ngach_{0}".format(i + 1),
                     "mo_ta": "niche standard + channel identity", "nhom": "chuan_ngach",
                     "ve_chu": cach_ve(i)} for i in range(n_cn)]
            for i in _kieu_it_dung(goc, kenh, kieu_goc, n_td):
                muc.append({"so": i + 1, "kieu": kieu_goc[i][0], "mo_ta": kieu_goc[i][1],
                            "nhom": "tham_do", "ve_chu": "mo_hinh"})
            luot_td = la_luot_tham_do(ma_goi, int(tt.get("chu_ky_tham_do") or 5)) and n_td > 0
            ty = ((khuon.get("hoc") or {}).get("ty_trong") or TY_TRONG_MAC_DINH)
            if not n_cn:
                ty = {"khuon": 1.0}
            ra.update(che_do="khai_thac", khuon=khuon, muc=sorted(muc, key=lambda m: m["so"]),
                      luot_tham_do=luot_td,
                      nhom_uu_tien="tham_do" if luot_td else chon_nhom_ab(ma_goi, ty))
            return ra
    # THĂM DÒ — giữ kiểu cũ; `khuon_thang` (không có khuôn hợp lệ) → chuẩn ngách.
    muc = []
    for i, (t, m) in enumerate(kieu_goc):
        muc.append({"so": i + 1, "kieu": t, "mo_ta": m, "nhom": "tham_do", "ve_chu": "mo_hinh"})
    if cho_tam_khuon:
        if cn:
            muc.append({"so": SO_CHUAN_NGACH_DAU, "kieu": "chuan_ngach", "mo_ta": "niche standard + channel identity",
                        "nhom": "chuan_ngach", "ve_chu": "mo_hinh"})
        else:
            muc.append({"so": SO_KHUON_DAU, "kieu": TIEN_TO_KHUON, "mo_ta": "", "nhom": "tham_do",
                        "ve_chu": "mo_hinh", "cu": True})
    ra["muc"] = muc
    return ra


def ghi_ke_hoach(thu_muc_thumb: str, kh: Dict[str, Any]) -> None:
    os.makedirs(thu_muc_thumb, exist_ok=True)
    duong = os.path.join(thu_muc_thumb, TEP_KE_HOACH)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(kh, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong)


def doc_ke_hoach(thu_muc_thumb: str) -> Optional[Dict[str, Any]]:
    try:
        with io.open(os.path.join(thu_muc_thumb, TEP_KE_HOACH), encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return None
    return du if isinstance(du, dict) else None


# ── Giám khảo thử (dùng cho vòng thử khuôn mới) ─────────────────────────────


LOI_NHAC_CHAM_CHUAN_NGACH = """IMAGE 1 is a YouTube thumbnail candidate for a Japanese psychology \
channel. IMAGE 2 is the same candidate shrunk to phone size. IMAGE 3 is the channel's character \
reference.

The niche standard every thumbnail must meet:
{chuan}

Expected text on the candidate (exact spelling): {chu}

Check item by item, pass=true/false, one short reason each:
- chu_tran: bare lettering with thick outline, NO background box/plate behind any text line
- mau_chu: yellow/white main text AND the key word in a different colour (red)
- nen_canh: a concrete illustrated scene with warm light (not a plain empty background)
- bieu_cam: the character's face shows a clear strong emotion (not blank/neutral, not sad)
- doc_120px: text readable in IMAGE 2
- dung_nhan_vat: recognisably the SAME character as IMAGE 3, not deformed
Also "suc_bam": 0-10 click-pull on a phone/TV home feed, "chu_doc_ra": every text line you can read, \
exactly, in reading order (include stray text on props), "khac_biet": 1-3 biggest problems.
Be a STRICT art director. Return JSON only: {{"chu_tran": {{"pass": true, "ly_do": ""}}, \
"mau_chu": {{...}}, "nen_canh": {{...}}, "bieu_cam": {{...}}, "doc_120px": {{...}}, \
"dung_nhan_vat": {{...}}, "suc_bam": 0, "chu_doc_ra": ["..."], "khac_biet": ["..."], "tom_tat": ""}}"""


LOI_NHAC_CHAM_THEO_KHUON ="""IMAGE 1 is a channel's REAL winning YouTube thumbnail (CTR {ctr:.2f}%). \
IMAGE 2 is a new candidate that should rebuild the same design for a different video. IMAGE 3 is \
the candidate shrunk to phone size.

The winning design, measured:
{khuon}

Expected text on the candidate (exact spelling): {chu}

Check the candidate item by item, pass=true/false, one short reason each:
- nen: background matches (dominant colour, darkness, glow/halo behind character, effects)
- nhan_vat: the orange-headed stick character, placed and sized like the winner, dynamic pose, strong expression
- chu_bo_cuc: text tiers in the same places, same colours per tier, bare lettering with outline, NO background box
- chinh_ta: the Japanese text is spelled exactly as expected, no garbled/extra glyphs
- doc_120px: text still readable in IMAGE 3
- dung_nhan_vat: character is recognisably the SAME character (orange round head, black stick body), not deformed
Also "suc_bam": 0-10, how close its click-pull on a phone/TV home feed is to IMAGE 1 (10 = as \
strong as the winner), "chu_doc_ra": every text line you can read on the candidate, exactly, in \
reading order (include any stray text on props), and "khac_biet": the 1-4 biggest visible \
differences from IMAGE 1.
Be a STRICT art director: pass=true only when that item would clearly read as the same series as \
IMAGE 1. Do not be polite; most rebuilds miss something.
Return JSON only: {{"nen": {{"pass": true, "ly_do": ""}}, "nhan_vat": {{...}}, "chu_bo_cuc": {{...}}, \
"chinh_ta": {{...}}, "doc_120px": {{...}}, "dung_nhan_vat": {{...}}, "suc_bam": 0, \
"chu_doc_ra": ["..."], "khac_biet": ["..."], "tom_tat": "one sentence in English"}}"""
