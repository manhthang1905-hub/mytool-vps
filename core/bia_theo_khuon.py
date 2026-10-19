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

    du_bang_chung()          — LUẬT BẰNG CHỨNG một câu (13/10/2026), dùng chung với `khuon_bia`.
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
    bia_khai_thac_imp_min: 10000
    bia_khai_thac_imp_lon: 50000     # sàn "hiển thị lớn" của luật bằng chứng (xem `du_bang_chung`)
    bia_so_tam_theo_khuon: 3         # trong so_thumbnail tấm (điều phối 30/09: 3/7)
    bia_chu_ky_tham_do: 5            # 1/5 video được CHỌN tấm thăm dò
    bia_ve_chu: "tron"               # "tron" (xen kẽ) | "ma" = code vẽ chữ | "mo_hinh" = mô hình ảnh vẽ
    bia_hop_nen: ""                  # nền ảnh bìa kiểu HỘP (tiếng Anh); rỗng = phẳng, sáng, ấm, sạch

Mỗi kênh học từ dữ liệu CỦA RIÊNG KÊNH ĐÓ (không mượn khuôn nhóm).

13/10/2026 tối — khuôn kiểu HỘP chữ (`kieu_hop`, TL4-T7) có đường riêng đạt chuẩn bìa thắng (xem khối `HOP_*`):
`tach_chu_mac_dinh`/`viet_bien_the` chia 2–4 dòng có đúng MỘT dòng cực to (+ cảnh ẩn dụ do LLM viết),
`loi_nhac_hop_chu` (nền phẳng sáng, mẫu phong cách = bìa thắng thật), `ve_chu_len_anh` → `_ve_bia_hop` (phông
`fonts/MPLUSRounded1c-Black.ttf`, hộp đỏ sẫm so le) + báo cáo `hop_chu` cho cổng `do_bia.cham_hop`.
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
    "khac_bia_tool", "tong_ky_tu_khuon", "du_bang_chung", "gan_kieu_khuon",
    "kieu_hop", "loi_nhac_hop_chu", "xep_hop_chu", "chon_anh_mau_phong_cach", "chuan_thu_bac",
]

#: Ngưỡng "khuôn ĐỦ BẰNG CHỨNG để khai thác" — chủ dự án 30/09/2026.
NGUONG_MAC_DINH: Dict[str, Any] = {
    "bia_khai_thac": True,
    "bia_khai_thac_ctr_min": 7.0,
    "bia_khai_thac_imp_min": 10000,
    "bia_khai_thac_imp_lon": 50000,
    # 16/10/2026: vế NỚI của luật bằng chứng (chỉ khi KHÔNG video nào đạt luật chặt) — CTR ≥ hệ số × trung vị kênh.
    "bia_khai_thac_he_so_tv": 1.2,
    "bia_so_tam_theo_khuon": 3,
    "bia_chu_ky_tham_do": 5,
    "bia_ve_chu": "tron",
    # 13/10/2026: nền ảnh bìa KIỂU HỘP (tiếng Anh) — rỗng = `NEN_HOP_MAC_DINH` (phẳng, sáng, ấm, sạch).
    "bia_hop_nen": "",
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


def du_bang_chung(ctr: float, imp: float, *, ctr_min: float, imp_min: float, imp_lon: float,
                  trung_vi: Optional[float], noi: bool = False, he_so_tv: float = 1.2) -> bool:
    """LUẬT BẰNG CHỨNG (13/10/2026, một câu): bìa đủ làm khuôn của kênh khi (CTR ≥ `ctr_min` VÀ hiển thị ≥
    `imp_min`) HOẶC (hiển thị ≥ `imp_lon` VÀ CTR ≥ trung vị CTR các video thật ≥1.000 hiển thị của kênh).

    Vế sau vì bìa thắng hiển thị LỚN có CTR tự nhiên thấp hơn: TL4-T7 (khuôn hộp chữ đỏ) 5,2–5,9% trên
    100k–300k hiển thị bị ngưỡng 7% loại hết. Dùng CHUNG cho `khuon_bia.tim_video_thang` (chọn khuôn) và
    `trang_thai_khai_thac` (khai thác) — hai nơi không được lệch luật.

    16/10/2026 — vế NỚI (`noi=True`, chỉ dùng khi KHÔNG video nào của kênh đạt luật chặt): hiển thị ≥ `imp_min` VÀ CTR ≥
    `he_so_tv` × trung vị kênh. TL1-T7: bìa thắng thật 5,3–6,8% trên 14k–35k hiển thị (trung vị 3,9%) bị luật chặt loại
    hết → kênh không bao giờ có khuôn để khai thác, trong khi kênh đang tụt."""
    if ctr >= ctr_min and imp >= imp_min:
        return True
    if trung_vi is not None and imp >= imp_lon and ctr >= trung_vi:
        return True
    return bool(noi) and trung_vi is not None and imp >= imp_min and ctr >= float(he_so_tv) * trung_vi


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
        # 13/10/2026: CÙNG luật với `khuon_bia.tim_video_thang` (`du_bang_chung`); trung vị CTR các video
        # thật của kênh do `khuon_bia.cap_nhat` đo lúc chọn khuôn (`trung_vi_ctr_that`).
        tv = _so(khuon.get("trung_vi_ctr_that"))
        nguong = float(ch["bia_khai_thac_ctr_min"])
        ra.update(nguong_ctr=round(nguong, 3), trung_vi=tv)
        # 16/10/2026: khuôn chọn bằng vế NỚI (`khuon_bia`, không video nào đạt luật chặt) xét đúng vế ấy.
        if not du_bang_chung(ctr, imp, ctr_min=nguong, imp_min=ch["bia_khai_thac_imp_min"],
                             imp_lon=ch["bia_khai_thac_imp_lon"], trung_vi=tv,
                             noi=khuon.get("luat_bang_chung") == "noi", he_so_tv=ch["bia_khai_thac_he_so_tv"]):
            ra["ly_do"] = ("khuôn chưa đủ bằng chứng: CTR {0:.2f}% / {1:.0f} hiển thị (cần ≥{2:.2f}% và ≥{3}, "
                           "hoặc ≥{4} hiển thị và CTR ≥ trung vị kênh {5})").format(
                ctr, imp, nguong, ch["bia_khai_thac_imp_min"], ch["bia_khai_thac_imp_lon"],
                "{0:.2f}%".format(tv) if tv is not None else "?")
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
                  ly_do="khuôn {0} đủ bằng chứng: CTR {1:.2f}%, {2:.0f} hiển thị{3}".format(
                      khuon.get("video_id"), ctr, imp, "" if ctr >= nguong else
                      " (hiển thị lớn, CTR ≥ trung vị kênh {0:.2f}%)".format(tv)))
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
  "nen_kieu": "flat | painted | near_photo  (near_photo = a softly lit illustrated scene that looks close to a real photo: cinematic light, depth, bokeh)",
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
        "khoi_nen": false, "mau_khoi": "#hex of the box/plate behind this line, empty if none",
        "canh": "trai | giua | phai (the side the line is aligned to)", "trich_dan": false}}
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
    nk = _chuoi(du.get("nen_kieu"), 40).lower()
    nk = "near_photo" if ("near" in nk or "photo" in nk) else "painted" if "paint" in nk else \
        "flat" if "flat" in nk else ""
    if nk:
        ra["nen_kieu"] = nk
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
            hk = _RE_HEX.search(str(t.get("mau_khoi") or ""))
            canh = _chuoi(t.get("canh"), 20).lower()
            tang_ra.append({
                "vi_tri": _chuoi(t.get("vi_tri"), 20), "noi_dung": noi_dung,
                "so_ky_tu": int(_so(t.get("so_ky_tu")) or len(re.sub(r"[\s\W_]+", "", noi_dung))),
                "co_pct": _so(t.get("co_pct")), "mau": mau, "phan_mau": phan,
                "vien": _chuoi(t.get("vien"), 120), "khoi_nen": _co(t.get("khoi_nen")),
                "mau_khoi": hk.group(0).upper() if hk else "",
                "canh": canh if canh in ("trai", "giua", "phai") else "",
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
#: 13/10/2026 — khuôn CỦA CHÍNH KÊNH đo từ bìa THẬT có nền "near_photo" (TL4-T7: cảnh minh hoạ ánh sáng mềm gần như
#: ảnh chụp) → vẫn cấm NGƯỜI thật, nhưng cảnh được giữ đúng vẻ gần-ảnh-chụp của bìa thắng.
CAM_NGUOI_THAT = ("NO real people and NO photographs of people anywhere: every person or figure is DRAWN in the same "
                  "illustration style as the reference character (no photo-realistic faces, crowds or stock photos); "
                  "the SCENE itself keeps the winning thumbnail's softly lit, near-photographic illustrated look "
                  "(warm cinematic light, depth, gentle bokeh)")
#: Bề ngang cột chữ (tỉ lệ khung) của tầng có HỘP chữ canh một bên — bìa thắng TL4-T7: hộp đỏ xếp ở ~60% bên trái.
COT_CHU_KHOI = 0.62
#: Lề trong của hộp chữ khuôn (tỉ lệ cỡ chữ) — thay cho viền, dòng có hộp không có viền.
HOP_LE_PCT = 0.12
#: Tầng có hộp chỉ xuống 2 dòng khi một dòng (cả hộp) thấp hơn ngần này % khung (~10% nét chữ).
HOP_XUONG_DONG_PCT = 14.0

# ── BÌA KIỂU HỘP CHỮ (13/10/2026 tối) ─────────────────────────────────────────────────────────────────────────
# Chủ dự án soi bìa TL4-T7 tool làm: "ảnh thumb xấu, không thu hút như các thumb đã win của kênh". Soi các bìa thắng
# thật (100k–300k hiển thị) + công cụ tay chủ đã duyệt (`workspace/cong-cu/bia_tl4.py`, bìa đang sống) — 5 điều:
#  1. chữ là nhân vật chính, có THỨ BẬC: 2–4 dòng, đúng MỘT dòng CỰC TO (~28% khung), các dòng kia vừa (~13%);
#  2. phông RẤT ĐẬM bo tròn (M PLUS Rounded 1c Black — `fonts/`, SIL OFL 1.1);
#  3. hộp ĐỎ SẪM ôm sát chữ, bo góc, so le nhẹ, đè nhẹ lên nhau, bóng mềm, viền nâu sẫm mảnh tách hộp khỏi nền;
#  4. nền minh hoạ PHẲNG, SÁNG, ẤM, sạch — mẫu phong cách là chính các bìa thắng thật của kênh;
#  5. MỘT ẩn dụ / tương phản gây tò mò rút từ tiêu đề (LLM viết cảnh + nét mặt, `viet_bien_the`).
# Chỉ khuôn có HỘP chữ (`kieu_hop`) đi đường này; chữ trần / chuẩn ngách / kênh khác giữ nguyên.
HOP_DO_SAU = (190, 57, 43)          # #BE392B — đỏ sẫm của bìa thắng
HOP_VIEN_MAU = (70, 22, 15)         # #46160F — viền mảnh tách hộp đỏ khỏi nền cùng độ sáng
HOP_CO_TO = 0.285                   # cỡ phông dòng CỰC TO / chiều cao khung (205/720)
HOP_CO_VUA = 0.128                  # cỡ phông dòng vừa (92/720)
HOP_CO_NHO = 0.42                   # đuôi chữ nhỏ (「天才」+「かも」) / cỡ dòng
HOP_RONG_CHU = 0.60                 # bề ngang chữ tối đa / bề ngang khung
HOP_LE_NGANG = 0.17                 # lề trong ngang của hộp / cỡ phông
HOP_BO_GOC = 0.18                   # bán kính bo góc / cỡ phông
HOP_CAO = 1.12                      # chiều cao hộp / cỡ phông
HOP_DE = 0.06                       # hộp sau đè lên đáy hộp trước (× cỡ phông dòng trước)
HOP_SO_LE = 14.0 / 1280             # mỗi dòng lùi vào thêm (× bề ngang)
HOP_MEP = 34.0 / 1280               # mép cột hộp (× bề ngang)
#: Dòng cực to: tối đa ngần này ký tự (không kể đuôi nhỏ) — "cụm mạnh NGẮN nhất".
HOP_TO_TOI_DA = 5
#: Đuôi mềm của dòng cực to được vẽ NHỎ (bìa thắng 「非常に高い」+「かも」).
_DUOI_NHO = ("かもしれない", "かもね", "かも", "なのか", "だった", "でした", "らしい")
#: Phông vẽ chữ bìa kiểu hộp (vendor trong kho, `fonts/OFL.txt`).
FONT_HOP = "MPLUSRounded1c-Black.ttf"
_THU_MUC_FONT_KHO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")


def kieu_hop(khuon_chu: Optional[Dict[str, Any]]) -> bool:
    """Khuôn bìa thắng dạng HỘP chữ (TL4-T7: hộp đỏ xếp chồng nửa trái): ít nhất nửa số tầng (≥1) có hộp đo được màu
    → bìa theo khuôn đi đường kiểu hộp (thứ bậc, phông bo tròn, nền phẳng sáng, mẫu phong cách là bìa thắng thật)."""
    tang = [t for t in (((khuon_chu or {}).get("chu") or {}).get("tang") or []) if isinstance(t, dict)]
    co = sum(1 for t in tang if _hop_ro(t) is not None)
    return bool(tang) and co >= max(1, (len(tang) + 1) // 2)


def _gan_anh_that(kc: Dict[str, Any]) -> bool:
    return str((kc or {}).get("nen_kieu") or "") == "near_photo"


def _canh_hop(t: Dict[str, Any]) -> str:
    """Bên ("trai"/"phai") mà tầng CÓ HỘP chữ canh vào — "" với tầng chữ trần hoặc hộp căn giữa."""
    if not (t or {}).get("khoi_nen"):
        return ""
    for v in (t.get("canh"), t.get("vi_tri")):
        if v in ("trai", "phai"):
            return str(v)
    return ""


def _hop_ro(t: Dict[str, Any]) -> Optional[Tuple[int, int, int]]:
    """Màu hộp (rgb) của tầng có hộp chữ ĐO được màu — None: tầng trần, hoặc hộp không rõ màu (bộ vẽ dùng
    kiểu khối nền tối cũ của `do_bia`)."""
    if not (t or {}).get("khoi_nen") or not _RE_HEX.search(str(t.get("mau_khoi") or "")):
        return None
    return _mau_rgb(str(t["mau_khoi"]))


def gan_kieu_khuon(chu_tang: Sequence[Dict[str, Any]], khuon_chu: Dict[str, Any]) -> List[Dict[str, Any]]:
    """13/10/2026 — tầng chữ MỚI nhận HỘP chữ (có hộp, màu hộp, bên canh) của tầng khuôn tương ứng: tầng đầu ↔
    tầng đầu, tầng cuối ↔ tầng cuối, tầng giữa rải đều. Tầng khuôn chữ TRẦN không gán gì (bìa trần như cũ)."""
    tang_k = [t for t in (((khuon_chu or {}).get("chu") or {}).get("tang") or []) if isinstance(t, dict)]
    ra = [dict(t) for t in chu_tang if isinstance(t, dict)]
    if not tang_k:
        return ra
    if kieu_hop(khuon_chu):
        return _gan_kieu_hop(ra, khuon_chu)
    n, m = len(ra), len(tang_k)
    for i, t in enumerate(ra):
        k = tang_k[0 if n == 1 else int(round(i * (m - 1) / float(n - 1)))]
        if k.get("khoi_nen"):
            t.update(khoi_nen=True, mau_khoi=str(k.get("mau_khoi") or ""), canh=_canh_hop(k))
    return ra


def _la_do(rgb: Tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return r >= 150 and g <= 110 and b <= 100 and r - g >= 80


def _hex(rgb: Sequence[int]) -> str:
    return "#{0:02X}{1:02X}{2:02X}".format(*[int(v) for v in rgb[:3]])


def _ben_chu_hop(khuon_chu: Optional[Dict[str, Any]]) -> str:
    """Bên ("trai"/"phai") của cột hộp chữ: theo tầng hộp của khuôn canh một bên; khuôn không đo thì phía ngược
    nhân vật (mặc định trái — nhân vật bên phải như bìa thắng TL4)."""
    for k in (((khuon_chu or {}).get("chu") or {}).get("tang") or []):
        if isinstance(k, dict) and _canh_hop(k):
            return _canh_hop(k)
    return "phai" if str(((khuon_chu or {}).get("nhan_vat") or {}).get("vi_tri") or "") == "trai" else "trai"


def _gan_kieu_hop(ra: List[Dict[str, Any]], khuon_chu: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Khuôn HỘP: dòng CỰC TO (`to`) nhận kiểu tầng "đinh" của khuôn (tầng cỡ lớn hẳn, hoặc tầng duy nhất khác màu hộp
    — vd. hộp TRẮNG chữ ĐỎ giữa các hộp đỏ), mọi dòng khác nhận kiểu chung (màu hộp nhiều nhất). Màu chữ theo tầng
    khuôn (chữ trắng trên hộp đỏ); màu đỏ của khuôn (AI đọc ảnh lệch vài độ) chuẩn về đỏ sẫm bìa thắng `HOP_DO_SAU`.
    Chưa dòng nào `to` thì chọn bằng `_chon_dong_to`."""
    tang_k = [t for t in (((khuon_chu or {}).get("chu") or {}).get("tang") or [])
              if isinstance(t, dict) and _hop_ro(t) is not None]
    if not ra or not tang_k:
        return ra
    dem: Dict[str, int] = {}
    for k in tang_k:
        dem[_hex(_hop_ro(k))] = dem.get(_hex(_hop_ro(k)), 0) + 1
    chung_hex = max(dem, key=lambda h: dem[h])
    thuong = next(k for k in tang_k if _hex(_hop_ro(k)) == chung_hex)
    co = [float(_so(k.get("co_pct")) or 0) for k in tang_k]
    dinh = None
    if co and max(co) >= 1.25 * (statistics.median(co) or 1e-9) and max(co) > 0:
        dinh = tang_k[co.index(max(co))]
    elif len(dem) > 1 and min(dem.values()) == 1 and len(tang_k) >= 3:
        dinh = next(k for k in tang_k if dem[_hex(_hop_ro(k))] == 1)
    canh = _ben_chu_hop(khuon_chu)
    if not any(t.get("to") for t in ra):
        i_to = _chon_dong_to([chu_cua_tang(t) for t in ra])
        ra[i_to]["to"] = True
    for t in ra:
        k = dinh if (t.get("to") and dinh is not None) else thuong
        hop = _hop_ro(k)
        mau_chu = _mau_rgb(str((k.get("mau") or ["#FFFFFF"])[0]), (255, 255, 255))
        hop = HOP_DO_SAU if _la_do(hop) else hop
        mau_chu = HOP_DO_SAU if _la_do(mau_chu) else mau_chu
        t.update(khoi_nen=True, mau_khoi=_hex(hop), canh=canh)
        doan = [dict(p) for p in (t.get("phan_mau") or []) if p.get("chu")]
        if not doan and t.get("chu"):
            doan = [{"chu": str(t["chu"])}]
        t["phan_mau"] = [dict(p, mau=_hex(mau_chu)) for p in doan]
    return ra


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
    if _gan_anh_that(kc):
        dong.append("scene rendering: a softly lit, near-photographic illustrated scene (cinematic warm light, "
                    "depth, gentle bokeh) like the winning thumbnail")
    if kc.get("nen_hieu_ung"):
        dong.append("background effects: " + ", ".join(kc["nen_hieu_ung"]))
    if kc.get("anh_sang"):
        dong.append("lighting: " + kc["anh_sang"])
    nv = kc.get("nhan_vat") or {}
    if nv:
        vt = {"trai": "left third", "giua": "CENTRE of the frame", "phai": "right third"}.get(
            nv.get("vi_tri", ""), nv.get("vi_tri", ""))
        # 13/10/2026: cỡ nhân vật ĐO trên bìa thắng thật của kênh thắng luật ngách ≥30% (luật ấy chỉ còn ở
        # `loi_nhac_theo_khuon` khi khuôn không đo được cỡ).
        co = "about {0:.0f}% of frame height".format(float(nv["co_pct"])) if _so(nv.get("co_pct")) else ""
        dong.append("the reference character placed in the {0}{1}".format(vt, (", " + co) if co else ""))
    if kc.get("sac_thai"):
        dong.append("mood: " + kc["sac_thai"])
    chu = kc.get("chu") or {}
    if co_chu and chu.get("tang"):
        mo_ta = []
        for t in chu["tang"]:
            mau = " + ".join(_ten_mau(m) for m in (t.get("mau") or [])) or "white"
            if t.get("khoi_nen"):
                mo_ta.append("{vt} tier: {mau} lettering on a solid {hop} rounded box{canh}, about {co}% of frame "
                             "height{td}".format(
                                 vt=t.get("vi_tri") or "?", mau=mau, hop=_ten_mau(t.get("mau_khoi") or "") or "dark",
                                 canh={"trai": ", boxes left-aligned on the left side",
                                       "phai": ", boxes right-aligned on the right side"}.get(t.get("canh") or "", ""),
                                 co=int(t.get("co_pct") or 20),
                                 td=", wrapped in 「」 quotes" if t.get("trich_dan") else ""))
                continue
            mo_ta.append("{vt} tier: {mau} bare lettering{vien}{khoi}, about {co}% of frame height{td}".format(
                vt=t.get("vi_tri") or "?", mau=mau,
                vien=(", " + t["vien"]) if t.get("vien") and t["vien"].lower() != "none" else "",
                khoi=" with NO background box",
                co=int(t.get("co_pct") or 20), td=", wrapped in 「」 quotes" if t.get("trich_dan") else ""))
        dong.append("TEXT LAYOUT: " + "; ".join(mo_ta))
        if chu.get("tu_to_mau"):
            dong.append("text colouring rule: " + chu["tu_to_mau"])
    return "\n".join(dong)


# ── Lời nhắc sinh ảnh theo khuôn ─────────────────────────────────────────────


def _vung_trong_chu(khuon_chu: Dict[str, Any]) -> str:
    """Vùng phải chừa trống cho chữ code vẽ. Tầng có hộp chữ canh một bên → cột `COT_CHU_KHOI` bên đó."""
    phan: List[str] = []
    for t in (((khuon_chu or {}).get("chu") or {}).get("tang") or []):
        canh = _canh_hop(t)
        if canh:
            v = "the {0} {1:.0f}% of the frame".format("LEFT" if canh == "trai" else "RIGHT", COT_CHU_KHOI * 100)
        else:
            v = {"tren": "the TOP 30% of the frame", "duoi": "the BOTTOM 32% of the frame",
                 "trai": "the LEFT half", "phai": "the RIGHT half"}.get(str(t.get("vi_tri") or ""), "")
        if v and v not in phan:
            phan.append(v)
    return " and ".join(phan) or "the top and bottom bands"


def loi_nhac_theo_khuon(khuon_chu: Dict[str, Any], *, phong_cach: str, bien_the: Dict[str, str],
                        chu_tang: Optional[Sequence[Dict[str, Any]]] = None,
                        chu_do_ma_ve: bool = True, cam: str = "") -> str:
    """Lời nhắc ẢNH cho một tấm theo khuôn thắng. Chỉ đổi: đạo cụ/biểu tượng,
    tư thế, nét mặt (theo nội dung video) và CHỮ. Bố cục/màu/sáng giữ nguyên.

    `chu_do_ma_ve=True` → ảnh nền KHÔNG CHỮ, chừa trống vùng chữ để
    `ve_chu_len_anh` vẽ đúng chính tả; `False` → mô hình ảnh tự vẽ chữ.

    13/10/2026 — khuôn là bìa THẬT của chính kênh nên số ĐO của nó thắng luật ngách chung: cỡ nhân vật đo được
    thay luật ≥30% (`NHAN_VAT_LON` chỉ còn khi khuôn không đo cỡ); nền "near_photo" → `CAM_NGUOI_THAT` (cấm
    người thật, giữ cảnh gần-ảnh-chụp) thay `CAM_ANH_THAT`, và bỏ "no photorealism" khỏi `cam`.
    """
    kc = khuon_chu or {}
    nv = kc.get("nhan_vat") or {}
    tu_the = bien_the.get("tu_the") or nv.get("tu_the") or "dynamic pose"
    net_mat = bien_the.get("net_mat") or nv.get("net_mat") or "strong clear emotion"
    dao_cu = bien_the.get("dao_cu") or ""
    gan_anh = _gan_anh_that(kc)
    dong = [
        "psychology YouTube thumbnail, rebuild EXACTLY the attached winning thumbnail's design "
        "(second reference image) for a new story — keep its composition, palette, background "
        "lighting and text layout identical; change only the prop/symbol and the pose/expression",
        "use the attached character reference image (first reference image) for the character — "
        "same drawing style, do not redesign it",
        "",
        khoi_khuon_tieng_anh(kc, co_chu=not chu_do_ma_ve),
        "character: {0}, expression: {1} — a strong, readable emotion on the face".format(tu_the, net_mat),
        None if _so(nv.get("co_pct")) else NHAN_VAT_LON,
        CAM_NGUOI_THAT if gan_anh else CAM_ANH_THAT,
    ]
    if gan_anh and cam:
        cam = ", ".join(x.strip() for x in cam.split(",") if x.strip() and "photoreal" not in x.lower())
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
        ("character and props drawing style (the scene keeps the winner's near-photographic light): "
         if gan_anh else "drawing style: ") + (phong_cach or "flat bold brush illustration"),
        "high contrast, saturated, reads instantly when shrunk to 120 pixels wide",
        "aspect ratio 16:9, ultra sharp, no watermark, no logo",
    ]
    if cam:
        dong.append("Avoid: " + cam)
    return "\n".join(d for d in dong if d is not None)


#: Nền mặc định của bìa kiểu hộp — đúng nền các bìa thắng sáng nhất + bìa chủ duyệt 13/10 (đè bằng `kenh.yaml:
#: bia_hop_nen`). Bìa tool làm trước đó (gara tối, ảnh gần-chụp) bị chủ chê "xấu, không thu hút".
NEN_HOP_MAC_DINH = ("clean FLAT VECTOR cartoon, soft warm beige / peach / terracotta palette, gentle soft light, simple "
                    "uncluttered background, smooth clean shapes — bright and inviting, NOT dark, NOT gritty, NOT "
                    "photographic")
#: Câu nhân vật mặc định của lời nhắc nền kiểu hộp (nhân vật TL4) — `loi_nhac_hop_chu(nhan_vat=...)` thay câu này.
NV_HOP_MAC_DINH = ("The main character is the plain white round-headed figure from the character reference image (the "
                   "image that shows only that figure): thick black outline, no clothes, no hair, no nose")
LOI_NHAC_NEN_HOP = (
    "YouTube thumbnail illustration for a Japanese psychology channel, drawn in EXACTLY the same art style as this "
    "channel's real winning thumbnails (the attached reference images that show red text boxes — copy ONLY their art "
    "style, palette and light, never their text or boxes): {nen}. "
    "The main character is the plain white round-headed figure from the character reference image (the image that "
    "shows only that figure): thick black outline, no clothes, no hair, no nose, a BIG clear expressive face ({mat})"
    "{tu_the}. Any other people are flat, faded, featureless silhouettes in the background. "
    "Scene — one visual metaphor that makes people curious: {canh}. "
    # 13/10/2026 (thử thật): "the RIGHT 45% / LEFT 55%" bị mô hình VẼ THÀNH CHỮ lên ảnh + chia hai khung có vạch.
    "Composition: the character and the scene sit on the {ben_tranh} side of the picture; the {ben_chu} half is an "
    "empty, plain soft background with no objects that blends smoothly into the scene — no panels, no dividing line, "
    "no frame (large text boxes are added there later). The character's face stays fully on the {ben_tranh} side. "
    "The picture contains NO writing of any kind: no letters, words, numbers, percentages, labels, price tags, signs, "
    "logos or watermark, and none of these instructions written into the image — any tag, sign or screen is blank. "
    "Aspect ratio 16:9.")


def loi_nhac_hop_chu(khuon_chu: Dict[str, Any], *, bien_the: Dict[str, str], nen: str = "",
                     nhan_vat: str = "") -> str:
    """Lời nhắc ẢNH NỀN (không chữ) cho tấm bìa kiểu HỘP: nét vẽ/bảng màu lấy theo các bìa thắng thật gửi kèm làm
    ảnh tham chiếu, nhân vật của kênh, MỘT cảnh ẩn dụ/tương phản (`bien_the.canh`, LLM viết theo tiêu đề) + nét mặt;
    chừa trống phía cột chữ. Chữ do `ve_chu_len_anh` vẽ (thứ bậc, phông bo tròn, hộp đỏ sẫm)."""
    trai = _ben_chu_hop(khuon_chu) != "phai"
    nv = (khuon_chu or {}).get("nhan_vat") or {}
    canh = str(bien_the.get("canh") or bien_the.get("dao_cu") or "").strip() or (
        "the figure reacting to the video's idea with one simple symbolic prop beside it")
    mat = str(bien_the.get("net_mat") or nv.get("net_mat") or "a strong, clear emotion").strip()
    tu_the = str(bien_the.get("tu_the") or "").strip()
    ra = LOI_NHAC_NEN_HOP.format(nen=(nen or NEN_HOP_MAC_DINH).strip(), mat=mat,
                                 tu_the=(", " + tu_the) if tu_the else "", canh=canh.rstrip("."),
                                 ben_tranh="right" if trai else "left", ben_chu="left" if trai else "right")
    if nhan_vat.strip():
        # 19/10/2026 (`bia_lo`): nhân vật CỦA kênh theo style.yaml — kênh mượn khuôn hộp (TL4-K2) có nhân vật riêng
        ra = ra.replace(NV_HOP_MAC_DINH, "The main character is EXACTLY the figure from the character reference image "
                        "(the image that shows only that figure): {0}".format(nhan_vat.strip().rstrip(".")))
    return ra


def chon_anh_mau_phong_cach(cac_duong: Sequence[str], toi_da: int = 3, toi_thieu: int = 2) -> List[str]:
    """2–3 bìa thắng THẬT làm mẫu phong cách cho ảnh nền bìa kiểu hộp: ưu tiên bìa SÁNG + SẠCH (độ sáng trung bình +
    nửa bách phân vị 10 − mật độ cạnh, lưới 128×72) — đúng gu chủ duyệt 13/10 (nền phẳng sáng, không tối/rối). Giữ
    bìa ≥ 70% điểm bìa tốt nhất, ít nhất `toi_thieu`, nhiều nhất `toi_da`. Ảnh hỏng thì bỏ qua."""
    from PIL import Image, ImageOps  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    diem: List[Tuple[float, str]] = []
    for d in dict.fromkeys(x for x in cac_duong if x):
        try:
            a = np.asarray(ImageOps.fit(Image.open(d).convert("L"), (128, 72)), dtype=np.float32) / 255.0
        except Exception:  # noqa: BLE001 — ảnh hỏng/không phải ảnh
            continue
        canh = float(np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean())
        diem.append((float(a.mean()) + 0.5 * float(np.percentile(a, 10)) - canh, d))
    diem.sort(key=lambda x: -x[0])
    if not diem:
        return []
    ra = [d for s, d in diem if s >= 0.7 * diem[0][0]][:max(1, toi_da)]
    return ra if len(ra) >= toi_thieu else [d for _s, d in diem[:toi_thieu]]


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
        kieu = ("huge bare lettering, thick black outline, no background box" if not t.get("khoi_nen") else
                "big lettering on its own solid {0} rounded box, no outline{1}".format(
                    _ten_mau(str(t.get("mau_khoi") or "")) or "dark",
                    {"trai": ", box left-aligned", "phai": ", box right-aligned"}.get(_canh_hop(t), "")))
        dong.append("{0} text line (one single line, {1}): 「{2}」{3}".format(
                        ten_vt.get(t.get("vi_tri", ""), "TOP"), kieu, ca_dong,
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

#: 13/10/2026 tối — biến thể cho khuôn HỘP chữ (TL4-T7): chữ là nhân vật chính có thứ bậc + một ẩn dụ/tương phản.
LOI_NHAC_BIEN_THE_HOP = """You prepare thumbnail VARIANTS for a YouTube channel that rebuilds its WINNING \
thumbnail design for a new video. The winning design (this channel's real top thumbnails, 100k-300k impressions): \
2-4 short lines of the hook text, each in its own tight deep-red rounded box, stacked on the {ben_chu} side; exactly \
ONE line is HUGE (about a third of the frame height — the keyword or payoff that makes people click), the other lines \
are medium; a bright, clean flat-vector illustration on the {ben_tranh} side where the channel's plain white \
round-headed character acts out ONE visual metaphor or contrast from the story that makes viewers curious.

New video title: {tieu_de}
Hook text (Japanese): {chu_bia}
{luat_chu}

Return JSON only:
{{"chu": ["best marking of the hook", "second marking", "third marking"], "bien_the": [{{"canh": "...", \
"net_mat": "...", "tu_the": "..."}}, ... exactly {n} items]}}

chu: 2-3 alternative markings, best first. Each one copies the hook text EXACTLY and only INSERTS marks into it — \
"|" between lines (2-4 lines at natural phrase breaks, never starting a line with a particle), "[ ]" around the ONE \
huge line, and optionally "( )" around a soft ending of the huge line such as かも / なのか / だった (drawn small). \
Do not change, drop, add or reorder any character of the hook. The huge line is the PAYOFF — the short, \
emotionally strong keyword that makes people curious (the surprising result, judgement or hidden thing the video \
reveals), at most {to_toi_da} characters; never the opening context words (like 一人で / 実は / お金持ちほど). Examples from the channel's winners: \
「お金持ちほど|[買わない物]|ほとんどが」, 「富裕層が|[掃除に]|執着する本当の理由」, \
「『これ』を一人でしているなら|あなたのIQは|[非常に高い(かも)]」, 「低IQの人の|[思考の癖]」.
bien_the: {n} DIFFERENT scenes. "canh" (English, one sentence): ONE concrete visual metaphor or contrast drawn \
from the title/hook — the white figure in the foreground doing the telling thing, and behind it the contrast \
(best pattern of the winners: flat faded silhouettes of OTHER people doing the common/opposite thing), in a bright, \
warm, everyday place (never dark, night or gloomy). Examples of the level of idea wanted: "the figure lovingly \
polishing an old small car while a crowd gathers around a shiny new car on a showroom stand behind it"; "the figure \
reading alone with a cup of tea on a cushion while a noisy party is visible through a doorway behind it"; "a big \
pile of luxury bags, watches and phones, and the figure calmly walking away from it". Simple, readable at phone \
size; nothing that carries writing — no billboards, posters, signs, screens, labels, price tags, numbers or medals. \
"net_mat": the figure's big, clear facial expression that fits the story. "tu_the": its pose."""

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
    if kieu_hop(khuon_chu):  # 13/10/2026: bìa kiểu hộp — 2–4 dòng, đúng một dòng cực to
        return gan_kieu_khuon(_tach_tang_hop(s), khuon_chu)
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
    return gan_kieu_khuon(ra, khuon_chu)


# ── Chia chữ bìa kiểu HỘP: 2–4 dòng, đúng MỘT dòng cực to (đường lùi không AI) ─────────────────────────────────

_TRO_TU = "はがをにでとのもへや"
_RE_TRO_TU_GHEP = re.compile(r"ほど|なら|から|まで|より|だけ")
_RE_HAN_KATA = re.compile(r"[\u30a0-\u30ff\u3400-\u9fff\uf900-\ufaff\u3005A-Za-z0-9\uff10-\uff19]")


def _la_hira(c: str) -> bool:
    return "\u3040" <= c <= "\u309f"


def _cum_chu(s: str) -> List[str]:
    """Chữ bìa → CỤM (chỗ xuống dòng tự nhiên): sau trợ từ đứng sau chữ Hán/Katakana/số/ngoặc đóng (車に・人の・
    『コレ』を), sau trợ từ ghép (ほど・なら・から…) khi chữ sau không phải đuôi chia (ならない), sau dấu câu/khoảng
    trắng. Không bao giờ cắt trong 『』「」."""
    ra: List[str] = []
    cur = ""
    sau = 0
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " 　、。！？!?":
            cur += c if c not in " 　" else ""
            if cur.strip():
                ra.append(cur.strip())
            cur = ""
            i += 1
            continue
        if c in "『「":
            sau += 1
        elif c in "』」":
            sau = max(0, sau - 1)
        m = _RE_TRO_TU_GHEP.match(s, i) if sau == 0 else None
        if m and cur:
            ke = s[m.end():m.end() + 1]
            if not ke or ke not in "ないずばれせく":
                cur += m.group(0)
                ra.append(cur)
                cur = ""
                i = m.end()
                continue
        cur += c
        ke = s[i + 1:i + 2]
        if sau == 0 and len(cur) >= 2 and not _la_hira(cur[-2]) and ke and (
                (c in _TRO_TU and ke not in _TRO_TU + "っ")
                # trạng từ/đuôi -く trước chữ Hán (長く|乗る — bìa chủ duyệt 「同じ車に長く / 乗る人の」)
                or (c == "く" and bool(_RE_HAN_KATA.search(ke)) and not _la_hira(ke))):
            ra.append(cur)
            cur = ""
        i += 1
    if cur.strip():
        ra.append(cur.strip())
    return [x for x in ra if x]


def _tach_duoi(s: str) -> Tuple[str, str]:
    """(phần chính, đuôi nhỏ) — đuôi mềm `_DUOI_NHO` cuối dòng, phần chính còn ≥ 2 ký tự."""
    for d in _DUOI_NHO:
        if s.endswith(d) and len(_chuan(s[:-len(d)])) >= 2:
            return s[:-len(d)], d
    return s, ""


def _diem_dong_to(chu: str, cuoi: bool) -> Optional[float]:
    """Điểm (thấp = tốt) của MỘT dòng làm dòng CỰC TO — None: không hợp (dài quá `HOP_TO_TOI_DA`). Luật: cụm mạnh
    NGẮN nhất (có chữ Hán/Katakana — 「ほとんどが」 toàn hiragana không phải từ khoá)."""
    chinh = _tach_duoi(chu)[0] if cuoi else chu
    L = len(_chuan(chinh))
    if L < 1 or L > HOP_TO_TOI_DA:
        return None
    return 0.3 * L + (0.0 if _RE_HAN_KATA.search(chinh) else 3.0)


def _chon_dong_to(cac_chu: Sequence[str]) -> int:
    """Chỉ số dòng làm dòng cực to: dòng hợp có điểm `_diem_dong_to` tốt nhất (hoà → dòng sau); không dòng nào hợp
    → dòng NGẮN nhất."""
    ds = list(cac_chu)
    if not ds:
        return 0
    diem = [(_diem_dong_to(c, i == len(ds) - 1), i) for i, c in enumerate(ds)]
    hop = [(d, -i) for d, i in diem if d is not None]
    if hop:
        return -min(hop)[1]
    return min(range(len(ds)), key=lambda i: (len(_chuan(ds[i])), -i))


def _diem_tang(tang: Sequence[Dict[str, Any]]) -> Optional[float]:
    """Điểm MỘT cách chia bìa kiểu hộp (thấp = tốt) — None khi không có đúng MỘT dòng `to` hợp lệ (phần chính ≤
    `HOP_TO_TOI_DA` ký tự) hoặc dòng nào dài quá `TRAN_KY_TU_TANG`. Luật rút từ bìa thắng: dòng cực to là cụm mạnh
    NGẮN (có chữ Hán/Katakana — 「ほとんどが」 toàn hiragana không phải từ khoá), không phải dòng đầu (bối cảnh); dòng
    vừa 3–10 ký tự, cân nhau; ưu tiên 3 dòng."""
    if not 1 <= len(tang) <= 4:
        return None
    chu = [chu_cua_tang(t) for t in tang]
    dai = [len(_chuan(c)) for c in chu]
    hs = [i for i, t in enumerate(tang) if t.get("to")]
    if len(hs) != 1 or any(x > TRAN_KY_TU_TANG or x < 1 for x in dai):
        return None
    h = hs[0]
    chinh = "".join(p["chu"] for p in (tang[h].get("phan_mau") or []) if p.get("chu") and not p.get("nho")) or chu[h]
    L = len(_chuan(chinh))
    if L < 2 or L > HOP_TO_TOI_DA:
        return None
    p = {1: 1.5, 2: 0.8, 3: 0.0, 4: 1.2}[len(tang)] + 0.3 * L + (0.0 if _RE_HAN_KATA.search(chinh) else 3.0)
    p += 1.5 if (h == 0 and len(tang) > 1) else 0.0
    p += 1.0 if chinh.endswith("く") else 0.0  # trạng từ trơ (「長く」) không phải từ khoá
    vua = [x for i, x in enumerate(dai) if i != h]
    # dòng vừa > 8 ký tự co nhỏ dưới ~9% khung (thử 13/10: 「一人で『コレ』をする人は」 11 ký tự còn 7,6%)
    p += sum(0.5 * (x - 8) for x in vua if x > 8) + sum(1.5 * (x - 10) for x in vua if x > 10)
    p += sum(1.5 for x in vua if x < 3)
    return p + (0.2 * (max(vua) - min(vua)) if len(vua) >= 2 else 0.0)


def _la_duoi_mem(s: str) -> bool:
    return s in _DUOI_NHO or (1 <= len(s) <= 3 and all(_la_hira(c) for c in s))


def _dat_to(tang: Sequence[Dict[str, Any]], i_to: int) -> List[Dict[str, Any]]:
    """Bản sao `tang` với ĐÚNG dòng `i_to` là dòng cực to. Đuôi nhỏ (`nho`) chỉ giữ khi là các đoạn LIỀN cuối dòng
    cực to và là ĐUÔI MỀM (かも…; thử 13/10: AI đánh dấu 「乗る」 là đuôi nhỏ); dòng cực to là dòng cuối mà chưa tách
    đuôi thì tự tách (「天才かも」 → 天才 + かも)."""
    ra: List[Dict[str, Any]] = []
    for j, t in enumerate(tang):
        doan = [dict(p) for p in (t.get("phan_mau") or []) if p.get("chu")] or [{"chu": str(t.get("chu") or "")}]
        t2 = {k: v for k, v in t.items() if k not in ("to", "phan_mau")}
        sach = [{k: v for k, v in p.items() if k != "nho"} for p in doan]
        if j != i_to:
            t2["phan_mau"] = sach
            ra.append(t2)
            continue
        t2["to"] = True
        k = len(doan)
        while k > 0 and doan[k - 1].get("nho"):
            k -= 1
        duoi = "".join(p["chu"] for p in doan[k:])
        if k < len(doan) and k > 0 and _la_duoi_mem(duoi):
            t2["phan_mau"] = sach[:k] + [dict(sach[k], chu=duoi, nho=True)]
        elif j == len(tang) - 1 and len(sach) == 1:
            a, d = _tach_duoi(sach[0]["chu"])
            t2["phan_mau"] = [dict(sach[0], chu=a)] + ([dict(sach[0], chu=d, nho=True)] if d else [])
        else:
            t2["phan_mau"] = sach
        ra.append(t2)
    return ra


def _tang_hop(cac_chu: Sequence[str], i_to: int) -> List[Dict[str, Any]]:
    tang = [{"vi_tri": "tren" if i == 0 else ("duoi" if i == len(cac_chu) - 1 else "giua"), "phan_mau": [{"chu": c}]}
            for i, c in enumerate(cac_chu)]
    return _dat_to(tang, i_to)


def _tach_tang_hop(s: str, toi_da: int = 4) -> List[Dict[str, Any]]:
    """Đường lùi KHÔNG AI cho bìa kiểu hộp: mọi cách gộp cụm (`_cum_chu`) thành 1–`toi_da` dòng × mọi dòng làm dòng
    cực to, chọn điểm `_diem_tang` thấp nhất. Ví dụ 「一人で『コレ』をする人は上位1%の天才かも」 → 一人で『コレ』を /
    する人は上位1%の / 天才(かも) — đúng cách chia bìa chủ duyệt 13/10."""
    import itertools  # noqa: PLC0415

    cum = _cum_chu(s)
    if len(cum) < 2 and len(_chuan(s)) > HOP_TO_TOI_DA:
        k = _cho_xuong_dong(s)
        cum = [x for x in (s[:k].strip(), s[k:].strip()) if x]
    if not cum:
        return []
    tot: Optional[Tuple[float, List[Dict[str, Any]]]] = None
    for so in range(1, min(max(1, toi_da), len(cum)) + 1):
        for cat in itertools.combinations(range(1, len(cum)), so - 1):
            moc = (0,) + cat + (len(cum),)
            dong = ["".join(cum[a:b]) for a, b in zip(moc, moc[1:])]
            for h in range(len(dong)):
                v = _tang_hop(dong, h)
                d = _diem_tang(v)
                if d is not None and (tot is None or d < tot[0]):
                    tot = (d, v)
    if tot is not None:
        return tot[1]
    # Không cách nào có dòng cực to ≤ HOP_TO_TOI_DA ký tự: ≤ 3 dòng cân nhau, dòng ngắn nhất (sau dòng đầu) to.
    so = min(3, len(cum), max(1, toi_da))
    moc = [round(i * len(cum) / float(so)) for i in range(so + 1)]
    dong = ["".join(cum[a:b]) for a, b in zip(moc, moc[1:]) if b > a]
    sau = list(range(1, len(dong))) or [0]
    return _tang_hop(dong, min(sau, key=lambda i: (len(_chuan(dong[i])), -i)))


def _gop_dong_nho(tang: Sequence[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Các biến thể gộp một dòng VỪA quá ngắn (< 3 ký tự, 「人の」 mồ côi) vào dòng vừa kề sau/trước."""
    ra: List[List[Dict[str, Any]]] = []
    for i, t in enumerate(tang):
        if t.get("to") or len(_chuan(chu_cua_tang(t))) >= 3:
            continue
        for j in (i + 1, i - 1):
            if 0 <= j < len(tang) and not tang[j].get("to"):
                a, b = sorted((i, j))
                gop = dict(tang[a], phan_mau=[{"chu": chu_cua_tang(tang[a]) + chu_cua_tang(tang[b])}])
                ra.append(list(tang[:a]) + [gop] + list(tang[b + 1:]))
    return ra


def _doc_chu_danh_dau(s: str, chu_bia: str = "") -> List[Dict[str, Any]]:
    """Chữ bìa AI chỉ CHÈN dấu (13/10/2026 — chép lại cả câu thì AI hay bịa/bỏ chữ): 「同じ車に長く|[乗る人の]|ほとんどが」,
    「…|[天才(かも)]」 → tầng chữ: "|" tách dòng, "[ ]" = dòng cực to (`to`), "( )" cuối dòng cực to = đuôi nhỏ
    (`nho`). Nơi gọi so lại với chữ bìa gốc (bỏ dấu) — lệch thì chia máy."""
    s = str(s or "").strip().translate(str.maketrans("［］（）｜", "[]()|")).replace("\r", "").replace("\n", "|")
    if s.startswith("「") and s.endswith("」") and not str(chu_bia or "").strip().startswith("「"):
        s = s[1:-1]
    ra: List[Dict[str, Any]] = []
    for dong in s.split("|"):
        dong = dong.strip()
        if not dong:
            continue
        to = "[" in dong and "]" in dong
        loi = dong.replace("[", "").replace("]", "")
        m = re.match(r"^(.+?)\(([^()]+)\)$", loi) if to else None
        if m:
            phan = [{"chu": m.group(1)}, {"chu": m.group(2), "nho": True}]
        else:
            phan = [{"chu": loi.replace("(", "").replace(")", "")}]
        ra.append(dict({"phan_mau": phan}, **({"to": True} if to else {})))
    return ra


_SUA_CHU_HOP = ("\n\nYour previous \"chu\" was 「{cu}」 — it does NOT contain the hook exactly. The hook is 「{chu}」. "
                "Copy every character of it in the same order and only insert | [ ] ( ). Return the same JSON.")


def _cac_tang_ai(du: Dict[str, Any], chu_bia: str, co_dinh_chu: bool) -> List[List[Dict[str, Any]]]:
    """Các cách chia AI đề xuất cho bìa kiểu hộp (`chu`: một hay nhiều chuỗi có dấu, hoặc `chu_tang`) — chỉ giữ cách
    1–4 dòng và (kênh cố định chữ) nối lại ĐÚNG TRỌN chữ bìa: luật "các đoạn theo thứ tự" cũ cho AI bỏ mất cả mệnh đề
    (thử 13/10: 「同じ車に|長く乗る」, 「一人で|コレ|天才かも」)."""
    tho = du.get("chu")
    cac = [_doc_chu_danh_dau(x, chu_bia) for x in ([tho] if isinstance(tho, str) else tho if isinstance(tho, list)
                                                    else []) if isinstance(x, str)][:4]
    if isinstance(du.get("chu_tang"), list):
        cac.append([t for t in du["chu_tang"] if isinstance(t, dict)])
    # So CHẶT (chỉ bỏ khoảng trắng): `_chuan` bỏ cả dấu câu nên 「同じ車に{長く」 (AI tự chế dấu `{ }`) lọt — 13/10.
    goc = re.sub(r"\s+", "", _cat_theo_tran(str(chu_bia or "").strip()))
    return [t for t in cac if t and 1 <= len(t) <= 4
            and (not co_dinh_chu or re.sub(r"\s+", "", "".join(chu_cua_tang(x) for x in t)) == goc)]


def chon_tang_hop(cac_tang: Sequence[Sequence[Dict[str, Any]]], chu_bia: str = "") -> List[Dict[str, Any]]:
    """Chọn cách chia bìa kiểu hộp từ các đề xuất của AI (mỗi đề xuất đã đúng TRỌN chữ bìa) + đường lùi máy: với mỗi
    đề xuất thử mọi dòng làm dòng cực to, chia nhỏ dòng quá dài (「上位1%の天才かも」 → 上位1%の / 天才(かも)), gộp
    dòng mồ côi; chấm cùng `_diem_tang`. Dòng cực to do AI chọn được ưu tiên (−0,6 điểm) — AI đọc nghĩa, máy giữ
    luật hình (≤ 5 ký tự, không dòng đầu, 2–4 dòng)."""
    ung: List[Tuple[float, List[Dict[str, Any]]]] = []
    for tang in cac_tang:
        tang = [t for t in tang if isinstance(t, dict) and chu_cua_tang(t).strip()]
        if not tang:
            continue
        ai_to = [i for i, t in enumerate(tang) if t.get("to")]
        thu: List[Tuple[List[Dict[str, Any]], bool]] = [(_dat_to(tang, i), ai_to == [i]) for i in range(len(tang))]
        for i, t in enumerate(tang):
            if len(_chuan(chu_cua_tang(t))) <= HOP_TO_TOI_DA:
                continue
            for so in range(2, 4 - len(tang) + 2):  # chia dòng i thành `so` dòng (điểm chung quyết số dòng)
                con = _tach_tang_hop(chu_cua_tang(t), toi_da=so)
                if len(con) > 1:
                    khac = [dict({k: v for k, v in x.items() if k != "to"},
                                 phan_mau=[{kk: vv for kk, vv in p.items() if kk != "nho"}
                                           for p in (x.get("phan_mau") or [{"chu": chu_cua_tang(x)}])])
                            for x in tang]
                    thu.append((khac[:i] + con + khac[i + 1:], i in ai_to))
        thu += [(g, uu) for v, uu in list(thu) for g in _gop_dong_nho(v)]
        for v, uu in thu:
            d = _diem_tang(v)
            if d is not None:
                ung.append((d - (0.6 if uu else 0.0), v))
    may = _tach_tang_hop(_cat_theo_tran(str(chu_bia or "").strip())) if chu_bia else []
    d = _diem_tang(may) if may else None
    if d is not None:
        ung.append((d, may))
    if not ung:
        return may or [dict(t) for t in (cac_tang[0] if cac_tang else [])]
    return [dict(t) for t in min(ung, key=lambda x: x[0])[1]]


def chuan_thu_bac(chu_tang: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tầng chữ (một cách chia) cho bìa kiểu hộp → đúng MỘT dòng `to` theo luật `chon_tang_hop` (chữ giữ nguyên)."""
    ds = [t for t in chu_tang if isinstance(t, dict)]
    return chon_tang_hop([ds], "".join(chu_cua_tang(t) for t in ds))


#: 01/10/2026 — các cụm viết cứng cho kênh tâm lý Nhật trong lời nhắc ảnh bìa. Ngách KHÁC ngách mặc
#: định (`ho_so_ngach.la_ngach_mac_dinh`) được thay bằng thể loại/tiếng của chính nó (`ban_dia_hoa`);
#: ngách mặc định giữ nguyên từng ký tự.
_CUM_CUNG = (
    ("psychology YouTube thumbnail", "{the_loai} YouTube thumbnail"),
    ("for a Japanese psychology channel", "for a {tieng} {the_loai} channel"),
    ("Hook text (Japanese)", "Hook text ({tieng})"),
    ("Spell every Japanese character EXACTLY", "Spell every character EXACTLY"),
    ("the Japanese text is spelled exactly", "the {tieng} text is spelled exactly"),
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
    hop = kieu_hop(kc)
    ra: Dict[str, Any] = {}
    tang_hop: Optional[List[Dict[str, Any]]] = None
    if goi_chat is not None:
        try:
            kw: Dict[str, Any] = {"toi_da_token": 1500}
            if mo_hinh:
                kw["mo_hinh"] = mo_hinh
            if khoa:
                kw["khoa"] = khoa
            if hop:  # 13/10/2026: bìa kiểu hộp — LLM chọn dòng cực to + viết cảnh ẩn dụ/tương phản + nét mặt
                trai = _ben_chu_hop(kc) != "phai"
                loi_nhac = LOI_NHAC_BIEN_THE_HOP.format(
                    tieu_de=tieu_de, chu_bia=chu_bia, luat_chu=luat, n=n, to_toi_da=HOP_TO_TOI_DA,
                    ben_chu="LEFT" if trai else "RIGHT", ben_tranh="RIGHT" if trai else "LEFT")
            else:
                loi_nhac = LOI_NHAC_BIEN_THE.format(
                    khuon=khoi_khuon_tieng_anh(kc), mau_chu=mau_chu, tieu_de=tieu_de, chu_bia=chu_bia,
                    luat_chu=luat, n=n)
            if ban_dia is not None:
                loi_nhac = ban_dia(loi_nhac)
            du = loc_json(str(goi_chat(loi_nhac, **kw) or ""))
            if isinstance(du, dict):
                ra = du
            if hop:
                cac = _cac_tang_ai(ra, chu_bia, co_dinh_chu)
                if not cac and ra.get("chu"):
                    # Một lượt SỬA (thử 13/10: AI bỏ mất 「人のほとんどが」/「の」 dù được dặn chép nguyên): chỉ ra chỗ
                    # lệch, xin lại đúng câu — cảnh của lượt đầu giữ nếu lượt sửa không có.
                    kw2 = dict(kw, khoa=kw["khoa"] + ":sua-chu") if kw.get("khoa") else dict(kw)
                    du2 = loc_json(str(goi_chat(loi_nhac + _SUA_CHU_HOP.format(
                        cu=json.dumps(ra["chu"], ensure_ascii=False), chu=_cat_theo_tran(chu_bia.strip())),
                        **kw2) or ""))
                    if isinstance(du2, dict):
                        cac = _cac_tang_ai(du2, chu_bia, co_dinh_chu)
                        if not [b for b in (ra.get("bien_the") or []) if isinstance(b, dict)]:
                            ra["bien_the"] = du2.get("bien_the")
                tang_hop = chon_tang_hop(cac, chu_bia) if cac else None
        except Exception:  # noqa: BLE001
            ra = ra if isinstance(ra, dict) else {}
    if hop:
        ra["chu_tang"] = tang_hop  # bìa kiểu hộp: chỉ nhận tầng đã qua `chon_tang_hop`, không thì chia máy
    if not kiem_chu_tang(ra.get("chu_tang"), chu_bia, co_dinh=co_dinh_chu):
        ra["chu_tang"] = tach_chu_mac_dinh(chu_bia, kc)
        ra["chu_tang_lui"] = True
    else:
        ra["chu_tang"] = gan_kieu_khuon(ra["chu_tang"], kc)
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


def bo_font_cho(chu: str = "", ngon_ngu: str = "", kieu: str = "") -> Tuple[str, ...]:
    """Thứ tự tên tệp font nên thử cho chữ `chu` (kênh tiếng `ngon_ngu`, có thể rỗng).

    - có Hangul, hoặc kênh `ko` mà chữ không có kana/kanji → font Hàn trước;
    - không kana/kanji/Hangul, và (kênh khai tiếng khác ja/zh, hoặc chữ có ký tự ngoài ASCII như chữ Việt có dấu)
      → font La-tinh trước;
    - còn lại (chữ Nhật, hoặc chữ ASCII trơn mà không biết tiếng kênh) → thứ tự cũ (font Nhật); `kieu="hop"` (bìa
      kiểu hộp, 13/10/2026) → phông bo tròn rất đậm `FONT_HOP` trước."""
    chu = str(chu or "")
    nn = str(ngon_ngu or "").strip().lower().split("-")[0].split("_")[0]
    co_cjk = bool(_RE_CJK_NHAT_TRUNG.search(chu))
    if _RE_HANGUL.search(chu) or (nn == "ko" and not co_cjk):
        return _FONT_HAN + _FONT_UU_TIEN
    if not co_cjk and ((nn and nn not in ("ja", "zh")) or (not nn and re.search(r"[^\x00-\x7f]", chu))):
        return _FONT_LA_TINH + _FONT_UU_TIEN
    return ((FONT_HOP,) if kieu == "hop" else ()) + ("NotoSansJP-Black.otf",) + _FONT_UU_TIEN


_DU_CHU: Dict[Tuple[str, str], bool] = {}


def _font_du_chu(duong: str, chu: str) -> bool:
    """Phông có ĐỦ nét cho mọi ký tự của `chu` không (ký tự thiếu thì FreeType vẽ ô .notdef — so mặt nạ với một mã
    chắc chắn thiếu). Đo hỏng → coi như đủ (giữ hành vi chọn phông cũ)."""
    khoa = (duong, chu)
    if khoa not in _DU_CHU:
        try:
            from PIL import ImageFont  # noqa: PLC0415
            f = ImageFont.truetype(duong, 48)

            def mat_na(c: str):
                m = f.getmask(c)
                return m.size, bytes(m)
            thieu = mat_na("\U0010FFFD")
            _DU_CHU[khoa] = all(mat_na(c) != thieu for c in set(chu) if not c.isspace())
        except Exception:  # noqa: BLE001
            _DU_CHU[khoa] = True
    return _DU_CHU[khoa]


def _tim_font(goc: str = "", chu: str = "", ngon_ngu: str = "", kieu: str = "") -> str:
    cho = []
    if kieu == "hop":  # phông vendor trong kho (`fonts/`) — chỉ bìa kiểu hộp
        cho.append(_THU_MUC_FONT_KHO)
    if goc:
        cho.append(os.path.join(goc, "assets", "fonts"))
    cho.append(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    cho.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts"))
    for thu_muc in cho:
        for ten in bo_font_cho(chu, ngon_ngu, kieu):
            d = os.path.join(thu_muc, ten)
            if os.path.isfile(d) and (ten != FONT_HOP or _font_du_chu(d, chu)):
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


def _thay_tep(tam: str, dich: str, lan: int = 8) -> None:
    """`os.replace` có thử lại: Windows khoá tệp ảnh vừa ghi vài trăm ms (trình quét virus / trình xem) — kiểm vàng
    19/10/2026: "[WinError 5] Access is denied" giết cả lô TL3/TL5 ở lượt vẽ chữ lần hai lên cùng tệp."""
    import time as _t  # noqa: PLC0415
    for k in range(lan):
        try:
            os.replace(tam, dich)
            return
        except PermissionError:
            if k == lan - 1:
                raise
            _t.sleep(0.15 * (k + 1))


def ve_chu_len_anh(nen: str, dich: str, chu_tang: Sequence[Dict[str, Any]], *,
                   goc: str = "", kich_thuoc: Tuple[int, int] = (1280, 720), ngon_ngu: str = "",
                   khung_chu: Optional[Sequence[float]] = None, anh_nen: Any = None,
                   bao_cao: Optional[Dict[str, Any]] = None, cho_khung: bool = True,
                   tranh_them: Sequence[Sequence[float]] = (), ep_co: float = 1.0, doc: float = 0.5,
                   kieu_phong: str = "", uu_tien_kieu: Sequence[str] = (), nhan_toi_da: int = 1,
                   dien_tich_muc: Optional[Sequence[float]] = None, doc_khoi: Optional[float] = None) -> bool:
    """Vẽ các tầng chữ lên ảnh nền `nen` → `dich` (PNG). Mỗi tầng:
    `{vi_tri: tren|duoi, phan_mau:[{chu, mau}], co_pct, chinh, vung, can, khoi_nen}`.

    Bố cục theo luật điều phối (xem hằng trên): tầng thiếu chiều cao thì XUỐNG 2 DÒNG, tổng diện tích
    chữ < 40% thì phóng to dần, > 55% thì thu lại; tầng trên và dưới không được đè nhau.

    09/10/2026 — KIỂU CHỮ THEO NỀN ĐO ĐƯỢC (`core/do_bia.py`): trước đây mọi đoạn tô đúng màu khuôn
    (trắng / ĐỎ+VÀNG) + viền đen bất kể nền → chữ đỏ chìm trên nền gỗ nâu, chữ vàng trên nền kem. Giờ
    MỖI DÒNG đo nền ngay dưới nó (`do_bia.chon_kieu_dong`): nền sáng → chữ xanh đen viền trắng; nền tối →
    trắng/vàng viền đen; nền vừa/ấm/rối → viền dày, dải/khung nền mờ, bóng mạnh. Màu nhấn của kênh giữ
    cho MỘT đoạn nếu nó đạt tương phản, không thì đổi màu nhấn đạt. Sau khi vẽ, ĐO lại cả bìa trên nền
    thật (+ khung) → `bao_cao` (dict truyền vào được điền) và `<dich không đuôi>.do-bia.json`.

    `khung_chu` (x0, y0, x1, y1 — tỉ lệ 0..1): dồn chữ vào vùng này (vẽ lại bìa cũ đúng chỗ chữ cũ);
    `anh_nen`: PIL.Image dùng thay `nen` (đã mở sẵn). Trả False nếu không có font/không mở được ảnh.

    09/10/2026 (v2, sau khi chủ dự án soi bìa vẽ lại): mọi kiểu KHÔNG khung (đổi màu/viền dày) được thử
    trước; khung/dải nền chỉ khi không kiểu nào đạt, và không bao giờ đặt khung lên CHỦ THỂ (nhân vật/mặt/
    vật chính — `do_bia.ban_do_chu_the` đo trên nền sạch này). `cho_khung=False`: tuyệt đối không khung.
    Báo cáo có `bo_cuc` = {so_khung, chong_khung, che_chu_the} để cổng kiểm bố cục (`do_bia.bo_cuc_dat`).

    13/10/2026 — HỘP CHỮ CỦA KHUÔN (`khoi_nen` + `mau_khoi`, gán bởi `gan_kieu_khuon`): dòng đó KHÔNG đi đường
    thích nghi (trần trước, khung sau) mà vẽ ĐÚNG KIỂU khuôn — mỗi dòng một hộp bo góc đặc màu khuôn (bóng mềm
    dưới hộp), chữ màu khuôn không viền; chữ không đủ tương phản với hộp ở cỡ của dòng thì màu TỐI hơn trong cặp
    chữ/hộp được tối dần tới khi đạt (`_kieu_hop_khuon`). Vẫn đo + báo cáo như mọi dòng (cổng `do_bia` giữ nguyên).
    Đường cũ (tầng không có hộp, hoặc hộp không rõ màu) không đổi.

    13/10/2026 tối — MỌI tầng có hộp (khuôn kiểu hộp, `gan_kieu_khuon`) và không dồn vào `khung_chu` → `_ve_bia_hop`:
    thứ bậc (một dòng cực to), phông bo tròn rất đậm, hộp đỏ sẫm so le/đè nhẹ/bóng/viền mảnh; báo cáo mang bố cục hộp
    (`hop_chu`) để cổng `do_bia` đo chữ↔hộp và hộp↔nền trên chính tệp giao.

    14/10/2026 (`core/bia_lo.py`, bìa lô theo khuôn chữ TRẦN của kênh): tầng có `co_toi_da_pct` không cao quá ngần
    ấy % khung (thứ bậc: một dòng cực to, các dòng khác vừa), tầng `mot_dong` không tự xuống dòng (cách chia đã
    quyết); `ep_co` thu mọi dòng sau khi cân diện tích (né đầu nhân vật); `kieu_phong="hop"` dùng phông rất đậm
    `FONT_HOP`; `uu_tien_kieu`/`nhan_toi_da` chuyển cho `do_bia.chon_kieu_khoi` (giữ đúng kiểu chữ khuôn — trắng viền
    đen, đỏ/vàng từ khoá). Mặc định: y như cũ.

    18/10/2026 (`bia_lo` — bố cục chữ của bìa THẮNG): `dien_tich_muc` (% khung, (thấp, cao)) thay mục tiêu diện tích chữ
    mặc định — số đo bìa thắng của kênh; `doc_khoi` (0..1): các dòng xếp từ trên thành MỘT khối, khối đặt ở vị trí dọc
    này trong vùng chữ (0,5 = giữa) — cột chữ của bìa thắng là một khối liền, không hở giữa."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps  # noqa: PLC0415

    ds_tang = [t for t in chu_tang if isinstance(t, dict)]
    if ds_tang and not khung_chu and all(_hop_ro(t) is not None for t in ds_tang):
        return _ve_bia_hop(nen, dich, ds_tang, goc=goc, kich_thuoc=kich_thuoc, ngon_ngu=ngon_ngu, anh_nen=anh_nen,
                           bao_cao=bao_cao, tranh_them=tranh_them, ep_co=ep_co, doc=doc)
    font_duong = _tim_font(goc, "".join(chu_cua_tang(t) for t in chu_tang if isinstance(t, dict)), ngon_ngu,
                           kieu=kieu_phong)
    if not font_duong:
        return False
    try:
        goc_anh = anh_nen if anh_nen is not None else Image.open(nen)
        anh = ImageOps.fit(goc_anh.convert("RGB"), kich_thuoc, method=Image.LANCZOS)
    except (OSError, ValueError):
        return False
    W, H = anh.size
    le = int(W * 0.018)
    kx0, ky0, kx1, ky1 = (0.0, 0.0, 1.0, 1.0) if not khung_chu else [float(v) for v in khung_chu]
    zy0, zy1 = int(H * ky0), int(H * ky1)
    zH = max(1, zy1 - zy0)
    do = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    _cache: Dict[int, Any] = {}

    def font(c: int):
        c = max(12, int(c))
        if c not in _cache:
            _cache[c] = ImageFont.truetype(font_duong, c)
        return _cache[c]

    def vien_cua(c: int, t: Dict[str, Any]) -> int:
        # dòng có HỘP khuôn không có viền — phần này thành lề trong của hộp
        return max(3, int(c * float(t.get("vien_px_pct") or (HOP_LE_PCT if _hop_ro(t) else 0.075))))

    def rong_dong(doan, c, t) -> float:
        return sum(do.textlength(p["chu"], font=font(c)) for p in doan) + 2 * vien_cua(c, t) + c * 0.07

    def hop_dong(c: int, t) -> float:  # chiều cao hộp một dòng (có viền)
        return c * 1.12 + 2 * vien_cua(c, t)

    def tran_dong(t) -> float:  # chiều cao hộp dòng tối đa (% khung) của tầng
        return min(DONG_TOI_DA_PCT, float(t.get("co_toi_da_pct") or DONG_TOI_DA_PCT))

    def co_vua(doan, t, rong_vung) -> int:
        c = int(H * tran_dong(t) / 100.0 / 1.25)
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
        if khung_chu:
            vung = (kx0 + (kx1 - kx0) * float(vung[0]), kx0 + (kx1 - kx0) * float(vung[1]))
        vx0, vx1 = int(W * float(vung[0])) + le, int(W * float(vung[1])) - le
        rv = vx1 - vx0
        # Tầng có HỘP khuôn: mỗi dòng bìa thắng là một tầng/một hộp → chỉ xuống dòng khi một dòng quá thấp
        # (< HOP_XUONG_DONG_PCT khung, chữ nhỏ trên điện thoại), không theo luật khối 18/25% của chữ trần.
        toi_thieu = (HOP_XUONG_DONG_PCT if _hop_ro(t) is not None else TANG_CHINH_TOI_THIEU_PCT if t.get("chinh")
                     else TANG_TOI_THIEU_PCT) / 100.0 * H
        c1 = co_vua(doan, t, rv)
        cach = {"dong": [doan], "co": c1}
        s = "".join(p["chu"] for p in doan)
        if hop_dong(c1, t) < toi_thieu and len(_chuan(s)) >= 4 and not t.get("mot_dong"):
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
        tren = sum(cao_khoi(b) for b in bo if _xep_tu_tren(b["t"]))
        duoi = sum(cao_khoi(b) for b in bo if not _xep_tu_tren(b["t"]))
        return tren + duoi > zH * 0.93

    # Vùng chữ riêng (vẽ lại đúng chỗ chữ cũ): mục tiêu diện tích theo VÙNG, chữ phủ kín vùng hơn.
    dt_muc = DIEN_TICH_CHU_PCT if not khung_chu else tuple(
        x * (kx1 - kx0) * (ky1 - ky0) for x in (60.0, 85.0))
    if dien_tich_muc:
        dt_muc = (float(dien_tich_muc[0]), float(dien_tich_muc[1]))

    # 2) Cân diện tích chữ về 40–55% mà không đè nhau / không tràn bề ngang.
    for _ in range(30):
        dt = dien_tich()
        if dt > dt_muc[1] or chong_nhau():
            for b in bo:
                b["co"] = max(14, int(b["co"] * 0.95))
            continue
        if dt >= dt_muc[0]:
            break
        lon_duoc = False
        for b in bo:
            c_moi = int(b["co"] * 1.05) + 1
            if (all(rong_dong(d, c_moi, b["t"]) <= b["vx1"] - b["vx0"] for d in b["dong"])
                    and hop_dong(c_moi, b["t"]) <= H * tran_dong(b["t"]) / 100.0):
                b["co"] = c_moi
                lon_duoc = True
        if not lon_duoc or chong_nhau():
            if chong_nhau():
                for b in bo:
                    b["co"] = max(14, int(b["co"] * 0.97))
            break
    if ep_co != 1.0:
        for b in bo:
            b["co"] = max(14, int(b["co"] * float(ep_co)))

    # 3) Hình học từng dòng: tầng "tren" (và tầng có hộp canh một bên) xếp từ mép trên xuống, tầng khác từ
    #    mép dưới lên.
    hinh: List[Dict[str, Any]] = []
    y_tren = zy0 + int(H * 0.03)
    y_duoi = zy1 - int(H * 0.045)
    ds_duoi = [b for b in bo if not _xep_tu_tren(b["t"])]
    for b in bo:
        if b in ds_duoi:
            continue
        for d in b["dong"]:
            g = _hinh_dong(d, b, font, vien_cua, rong_dong, hop_dong, y_tren, True)
            y_tren = g["day"]
            hinh.append(g)
    for b in reversed(ds_duoi):
        for d in reversed(b["dong"]):
            g = _hinh_dong(d, b, font, vien_cua, rong_dong, hop_dong, y_duoi, False)
            y_duoi = g["day"]
            hinh.append(g)
    hinh.sort(key=lambda g: g["top"])
    if doc_khoi is not None and hinh and not ds_duoi:
        # MỘT khối dòng xếp từ trên: dời cả khối tới vị trí dọc `doc_khoi` của phần trống trong vùng chữ.
        dau, cuoi = min(g["top"] for g in hinh), max(g["top"] + g["h"] for g in hinh)
        tu, toi = zy0 + int(H * 0.03), zy1 - int(H * 0.045)
        lech = tu + max(0.0, (toi - tu) - (cuoi - dau)) * max(0.0, min(1.0, float(doc_khoi))) - dau
        for g in hinh:
            g["y"] += lech
            g["top"] += lech
            g["day"] += lech
            g["hop"] = (g["hop"][0], g["hop"][1] + lech, g["hop"][2], g["hop"][3] + lech)
            g["hop_khung"] = (g["hop_khung"][0], g["hop_khung"][1] + lech, g["hop_khung"][2], g["hop_khung"][3] + lech)

    # 4) Kiểu chữ THEO NỀN đo được (do_bia), rồi vẽ: khung/dải nền → bóng → viền → chữ.
    from . import do_bia  # noqa: PLC0415
    arr, canh = do_bia.mang_nen(anh)
    try:
        chu_the = do_bia.ban_do_chu_the(arr)
    except Exception:  # noqa: BLE001 — không đo được chủ thể: vẫn vẽ, chỉ không tránh được
        chu_the = None
    thuong = [g for g in hinh if _hop_ro(g["t"]) is None]
    chon = do_bia.chon_kieu_khoi(arr, canh, [
        {"hop": g["hop"], "mau_doan": [_mau_rgb(p.get("mau", ""), (255, 255, 255)) for p in g["doan"]],
         "vien_px": g["vien"] + g["dam"], "cao_px": g["cao_px"], "khoi_nen": bool(g["t"].get("khoi_nen"))}
        for g in thuong], H=H, cho_khung=cho_khung, chu_the=chu_the, uu_tien=uu_tien_kieu,
        nhan_toi_da=max(1, int(nhan_toi_da))) if thuong else []
    for g, (kieu, _cham) in zip(thuong, chon):
        g["kieu"] = kieu
    for g in hinh:
        if "kieu" not in g:  # dòng có HỘP của khuôn: đúng kiểu khuôn, không thích nghi
            g["kieu"] = _kieu_hop_khuon(g, H)
    from PIL import ImageChops  # noqa: PLC0415
    mat_khung: Dict[Tuple[int, ...], Any] = {}
    # Khung: các dòng LIỀN NHAU cùng kiểu khung gộp thành MỘT khung bo góc (khối chú thích liền mạch) — trừ hộp
    # của khuôn: mỗi dòng một hộp riêng như bìa thắng.
    nhom: List[List[Dict[str, Any]]] = []
    bong_hop: List[Tuple[Tuple[float, float, float, float], int]] = []
    for g in hinh:
        kh = g["kieu"].get("khung")
        if not kh:
            continue
        if (nhom and not kh.get("rieng") and nhom[-1][-1]["kieu"].get("khung") == kh
                and g["top"] - (nhom[-1][-1]["top"] + nhom[-1][-1]["h"]) < 0.35 * g["h"]):
            nhom[-1].append(g)
        else:
            nhom.append([g])
    hop_cac_khung: List[Tuple[float, float, float, float]] = []
    hop_khung_them: List[Tuple[float, float, float, float]] = []  # khung bộ vẽ THÊM (không phải khối nền khuôn)
    che_max = 0.0
    for ds_g in nhom:
        kh = ds_g[0]["kieu"]["khung"]
        mn = Image.new("L", anh.size, 0)
        x0 = min(g["hop_khung"][0] for g in ds_g)
        y0 = min(g["hop_khung"][1] for g in ds_g)
        x1 = max(g["hop_khung"][2] for g in ds_g)
        y1 = max(g["hop_khung"][3] for g in ds_g)
        hop_cac_khung.append((x0, y0, x1, y1))
        if not any(g["t"].get("khoi_nen") for g in ds_g):  # khối nền của KHUÔN là thiết kế, không tính che
            che_max = max(che_max, do_bia.che_chu_the(chu_the, (x0, y0, x1, y1), W, H))
            hop_khung_them.append((x0, y0, x1, y1))
        ban_kinh = int(min(g["c"] for g in ds_g) * (0.12 if kh.get("rieng") else 0.22))
        ImageDraw.Draw(mn).rounded_rectangle([x0, y0, x1, y1], radius=ban_kinh, fill=int(255 * float(kh["alpha"])))
        if kh.get("rieng"):
            bong_hop.append(((x0, y0, x1, y1), ban_kinh))
        # Mặt nạ theo MÀU, ghép MAX alpha — hai khung chạm nhau không chồng tối gấp đôi.
        khoa = tuple(int(v) for v in kh["mau"][:3])
        mat_khung[khoa] = ImageChops.lighter(mat_khung[khoa], mn) if khoa in mat_khung else mn
    nen_co_khung = anh.convert("RGBA")
    if bong_hop:  # bóng mềm DƯỚI hộp chữ của khuôn (bìa thắng có), vẽ trước hộp
        lop_b = Image.new("RGBA", anh.size, (0, 0, 0, 0))
        for (x0, y0, x1, y1), r in bong_hop:
            ImageDraw.Draw(lop_b).rounded_rectangle([x0 + W * 0.005, y0 + H * 0.011, x1 + W * 0.005, y1 + H * 0.011],
                                                    radius=r, fill=(0, 0, 0, 110))
        nen_co_khung = Image.alpha_composite(nen_co_khung, lop_b.filter(ImageFilter.GaussianBlur(max(2, W // 160))))
    for mau_k, mn in mat_khung.items():
        lop_k = Image.new("RGBA", anh.size, mau_k + (255,))
        lop_k.putalpha(mn)
        nen_co_khung = Image.alpha_composite(nen_co_khung, lop_k)
    lop = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    bong = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    ve = ImageDraw.Draw(lop)
    ve_bong = ImageDraw.Draw(bong)
    for g in hinh:
        _ve_dong_kieu(ve, ve_bong, g)
    bong = bong.filter(ImageFilter.GaussianBlur(max(2, W // 320)))
    ket = Image.alpha_composite(Image.alpha_composite(nen_co_khung, bong), lop).convert("RGB")
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    tam = dich + ".tmp.png"
    ket.save(tam, format="PNG")
    _thay_tep(tam, dich)

    # 5) ĐO lại cả bìa trên nền thật (kèm khung) — báo cáo cạnh ảnh + trả cho người gọi.
    try:
        ds = [do_bia.cham_dong_ve(arr, canh, g["hop"], g["kieu"]["mau"], vien_mau=g["kieu"]["vien"],
                                  vien_px=(g["vien"] + g["dam"]) * g["kieu"]["vien_he"], cao_px=g["cao_px"], H=H,
                                  khung=g["kieu"].get("khung"),
                                  ten="".join(p["chu"] for p in g["doan"])[:24]) for g in hinh]
        for d, g in zip(ds, hinh):
            d["kieu"] = g["kieu"]["ten"]
        bc = do_bia.tong_hop(ds, cach="chinh_xac")
        # 12/10/2026 (TL2-0021: khung tối to đè ngang ảnh): thêm diện tích khung bộ vẽ thêm + phần CHỦ THỂ bị che
        # (đo theo chủ thể, không theo hộp) — `do_bia.bo_cuc_dat` chặn khi quá `KHUNG_DT_TOI_DA` /
        # `CHE_CHU_THE_PHAN_TOI_DA`.
        bc["bo_cuc"] = {"so_khung": len(hop_cac_khung), "chong_khung": do_bia.khung_chong_nhau(hop_cac_khung),
                        "che_chu_the": round(che_max, 3),
                        "dt_khung": round(do_bia.dien_tich_hop(hop_khung_them, W, H), 3),
                        "che_chu_the_phan": round(do_bia.phan_chu_the_bi_che(chu_the, hop_khung_them, W, H), 3)}
        do_bia.ghi_bao_cao(dich, bc, anh=ket)
        if bao_cao is not None:
            bao_cao.clear()
            bao_cao.update(bc)
    except Exception as loi:  # noqa: BLE001 — đo hỏng không được làm mất bìa đã vẽ
        if bao_cao is not None:
            bao_cao.clear()
            bao_cao.update({"dat": None, "loi": str(loi)[:200]})
    return True


# ── Bộ vẽ bìa kiểu HỘP CHỮ (13/10/2026 tối — số đo bìa thắng thật + công cụ tay chủ duyệt) ───────────────────────


def xep_hop_chu(dong: Sequence[Dict[str, Any]], W: int, H: int, do_rong: Callable[[str, float], float], *,
                canh: str = "trai", tranh: Sequence[Sequence[float]] = (), ep_co: float = 1.0,
                doc: float = 0.5) -> List[Dict[str, Any]]:
    """BỐ CỤC cột hộp chữ (không vẽ). `dong` = [{"chu", "duoi", "to"}] theo thứ tự đọc; `do_rong(chu, co)` = bề
    ngang px của chuỗi ở cỡ phông `co`; `tranh` = hộp (x0, y0, x1, y1) px của nhân vật/chủ thể mà hộp chữ CÙNG DẢI
    DỌC không được lấn qua (cột trái: mép trái của chúng; cột phải: mép phải).

    Dòng `to`: cỡ `HOP_CO_TO`×H, dòng khác `HOP_CO_VUA`×H (không to quá 62% dòng cực to); co dần tới khi chữ ≤
    `HOP_RONG_CHU`×W. Hộp ôm sát (lề `HOP_LE_NGANG`×cỡ), cao `HOP_CAO`×cỡ, dòng sau đè `HOP_DE`×cỡ lên đáy dòng trước,
    lùi vào `HOP_SO_LE`×W mỗi dòng; cả cột căn giữa theo chiều dọc, quá cao thì thu đều. Hộp chạm chủ thể → thu cỡ
    dòng đó (không dưới 75% cỡ gốc — chữ vẫn là nhân vật chính) rồi xếp lại.
    14/10/2026 (`core/bia_lo.py`): `ep_co` thu cả cột (×cỡ gốc), `doc` dời cột theo chiều dọc (0 = sát trên, 0,5 = giữa
    như cũ, 1 = sát dưới) — để né đầu nhân vật / manh mối khi co từng dòng chưa đủ.
    Trả [{"co", "co_duoi", "le", "hop": (x0, y0, x1, y1)}] cùng thứ tự `dong`."""
    phai = canh == "phai"
    tr = [(W - float(b[2]), float(b[1]), W - float(b[0]), float(b[3])) if phai else tuple(float(v) for v in b[:4])
          for b in tranh]
    le, so_le, khe = W * HOP_MEP, W * HOP_SO_LE, 0.012 * W
    co_min = 0.045 * H

    def rong(d: Dict[str, Any], c: float) -> float:
        r = do_rong(str(d.get("chu") or ""), c)
        if d.get("duoi"):
            r += do_rong(str(d["duoi"]), c * HOP_CO_NHO) + c * 0.06
        return r

    co: List[float] = []
    for d in dong:
        c = (HOP_CO_TO if d.get("to") else HOP_CO_VUA) * H * ep_co
        while c > co_min and rong(d, c) > HOP_RONG_CHU * W:
            c *= 0.98
        co.append(c)
    c_to = max([c for c, d in zip(co, dong) if d.get("to")] or [0.0])
    if c_to:
        co = [c if d.get("to") else min(c, max(0.62 * c_to, 0.10 * H)) for c, d in zip(co, dong)]
    goc_co = list(co)
    ra: List[Dict[str, Any]] = []
    for _vong in range(5):
        tong = sum(HOP_CAO * c for c in co) - HOP_DE * sum(co[:-1])
        tran = H * (1.0 - 2 * 0.042)
        if tong > tran:
            co = [c * tran / tong for c in co]
            tong = tran
        y = max(0.039 * H, min((H - tong) * doc - 0.014 * H, H * (1 - 0.039) - tong))
        ra, doi = [], False
        for i, (d, c) in enumerate(zip(dong, co)):
            x0 = le + i * so_le
            hop = (x0, y, x0 + rong(d, c) + 2 * HOP_LE_NGANG * c, y + HOP_CAO * c)
            gioi = min([b[0] for b in tr if b[1] < hop[3] and b[3] > hop[1] and b[0] > x0 + 0.30 * W] or [W * 2.0])
            if hop[2] > gioi - khe:
                c_moi = c
                while (c_moi > max(co_min, 0.75 * goc_co[i])
                       and x0 + rong(d, c_moi) + 2 * HOP_LE_NGANG * c_moi > gioi - khe):
                    c_moi *= 0.97
                if c_moi < c - 0.5:
                    co[i], doi = c_moi, True
                    hop = (x0, y, x0 + rong(d, c_moi) + 2 * HOP_LE_NGANG * c_moi, y + HOP_CAO * c_moi)
                    c = c_moi
            ra.append({"co": c, "co_duoi": c * HOP_CO_NHO, "le": HOP_LE_NGANG * c, "hop": hop})
            y = hop[3] - HOP_DE * c
        if not doi:
            break
    if phai:
        for g in ra:
            x0, y0, x1, y1 = g["hop"]
            g["hop"] = (W - x1, y0, W - x0, y1)
    return ra


def vung_tranh_tu_chu_the(chu_the: Any, W: int, H: int, canh: str = "trai", tu: float = 0.50
                          ) -> List[Tuple[float, float, float, float]]:
    """Mặt nạ CHỦ THỂ (`do_bia.ban_do_chu_the`, nền sạch) → dải hộp px để `xep_hop_chu` né: mỗi hàng mặt nạ, đoạn chủ
    thể liền ≥ 3 ô đầu tiên tính từ phía cột chữ, chỉ xét phần sau `tu` bề ngang (lời nhắc đặt nhân vật ở 45% phía
    kia — chủ thể lấn sâu hơn thì chữ vẫn là nhân vật chính, không co theo)."""
    if chu_the is None:
        return []
    h, w = chu_the.shape
    ra: List[Tuple[float, float, float, float]] = []
    for r in range(h):
        hang = list(chu_the[r][::-1]) if canh == "phai" else list(chu_the[r])
        x = next((c for c in range(int(tu * w), w - 2) if hang[c] and hang[c + 1] and hang[c + 2]), None)
        if x is None:
            continue
        y0, y1 = r * H / float(h), (r + 1) * H / float(h)
        ra.append((0.0, y0, W - x * W / float(w), y1) if canh == "phai" else (x * W / float(w), y0, float(W), y1))
    return ra


def _mau_chu_tren_hop(chu: Tuple[int, int, int], hop: Tuple[int, int, int], cao_pct: float
                      ) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """(màu chữ, màu hộp) đọc được: chữ gần màu hộp → trắng/nâu sẫm (cái tương phản hơn); vẫn dưới ngưỡng theo cỡ
    (`do_bia.nguong_theo_co`) → màu TỐI hơn trong cặp tối dần 8%/bước (≤ 12 bước)."""
    from . import do_bia  # noqa: PLC0415

    def tp(a, b) -> float:
        return do_bia.ti_le_tuong_phan(do_bia.do_sang(a), do_bia.do_sang(b))
    nguong = do_bia.nguong_theo_co(cao_pct)
    if tp(chu, hop) < 2.0:
        chu = max(((255, 255, 255), HOP_VIEN_MAU), key=lambda m: tp(m, hop))
    for _ in range(12):
        if tp(chu, hop) >= nguong:
            break
        if do_bia.do_sang(hop) <= do_bia.do_sang(chu):
            hop = tuple(int(v * 0.92) for v in hop)
        else:
            chu = tuple(int(v * 0.92) for v in chu)
    return chu, hop


def _ve_bia_hop(nen: str, dich: str, chu_tang: Sequence[Dict[str, Any]], *, goc: str = "",
                kich_thuoc: Tuple[int, int] = (1280, 720), ngon_ngu: str = "", anh_nen: Any = None,
                bao_cao: Optional[Dict[str, Any]] = None, tranh_them: Sequence[Sequence[float]] = (),
                ep_co: float = 1.0, doc: float = 0.5) -> bool:
    """Vẽ bìa KIỂU HỘP (xem khối `HOP_*`): một dòng cực to, phông `FONT_HOP`, hộp màu khuôn (đỏ sẫm) ôm sát chữ, so
    le, đè nhẹ, bóng mềm, viền nâu sẫm mảnh; chữ trắng (hoặc màu chữ khuôn, đuôi nhỏ cùng màu). Né nhân vật đo trên
    nền sạch (`do_bia.ban_do_chu_the`) + các hộp px `tranh_them` (đầu nhân vật, `core/bia_lo.py`). Sau khi vẽ: ĐO trên
    ảnh thật bằng `do_bia.cham_hop` (chữ↔hộp, hộp↔nền) → `bao_cao` + `<dich không đuôi>.do-bia.json` kèm `hop_chu`
    (cổng `do_bia.cham_tep` đo lại trên tệp giao). `ep_co`/`doc`: xem `xep_hop_chu`."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps  # noqa: PLC0415

    font_duong = _tim_font(goc, "".join(chu_cua_tang(t) for t in chu_tang), ngon_ngu, kieu="hop")
    if not font_duong:
        return False
    try:
        goc_anh = anh_nen if anh_nen is not None else Image.open(nen)
        anh = ImageOps.fit(goc_anh.convert("RGB"), kich_thuoc, method=Image.LANCZOS)
    except (OSError, ValueError):
        return False
    W, H = anh.size
    s = H / 720.0
    _cache: Dict[int, Any] = {}

    def font(c: float):
        k = max(10, int(round(c)))
        if k not in _cache:
            _cache[k] = ImageFont.truetype(font_duong, k)
        return _cache[k]
    do = ImageDraw.Draw(Image.new("RGB", (8, 8)))

    def do_rong(chu: str, c: float) -> float:
        return float(do.textlength(chu, font=font(c))) if chu else 0.0

    dong: List[Dict[str, Any]] = []
    for t in chu_tang:
        doan = [p for p in (t.get("phan_mau") or []) if p.get("chu")] or [{"chu": str(t.get("chu") or "")}]
        chinh = "".join(p["chu"] for p in doan if not p.get("nho")).strip()
        duoi = "".join(p["chu"] for p in doan if p.get("nho")).strip()
        if not chinh:
            chinh, duoi = duoi, ""
        if chinh:
            dong.append({"chu": chinh, "duoi": duoi, "to": bool(t.get("to")), "t": t,
                         "mau": _mau_rgb(str(doan[0].get("mau") or ""), (255, 255, 255))})
    if not dong:
        return False
    if not any(d["to"] for d in dong):
        dong[_chon_dong_to([d["chu"] + d["duoi"] for d in dong])]["to"] = True
    canh = next((_canh_hop(d["t"]) for d in dong if _canh_hop(d["t"])), "trai")
    from . import do_bia  # noqa: PLC0415
    arr, _canh_nen = do_bia.mang_nen(anh)
    try:
        chu_the = do_bia.ban_do_chu_the(arr)
    except Exception:  # noqa: BLE001 — không đo được chủ thể: vẫn vẽ, chỉ không né được
        chu_the = None
    hinh = xep_hop_chu(dong, W, H, do_rong, canh=canh, ep_co=ep_co, doc=doc,
                       tranh=vung_tranh_tu_chu_the(chu_the, W, H, canh) + [tuple(b) for b in tranh_them])

    lop = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    bong = Image.new("RGBA", anh.size, (0, 0, 0, 0))
    ve, ve_bong = ImageDraw.Draw(lop), ImageDraw.Draw(bong)
    hop_chu: List[Dict[str, Any]] = []
    for d, g in zip(dong, hinh):
        f = font(g["co"])
        x0, y0, x1, y1 = g["hop"]
        b = f.getbbox(d["chu"])
        cao_px = float(max(1, b[3] - b[1]))
        mau_chu, mau_hop = _mau_chu_tren_hop(d["mau"], _hop_ro(d["t"]) or HOP_DO_SAU, 100.0 * cao_px / H)
        r = HOP_BO_GOC * g["co"]
        vien = max(2, int(round(3 * s)), int(g["co"] * 0.03))
        ve_bong.rounded_rectangle((x0 + 7 * s, y0 + 9 * s, x1 + 7 * s, y1 + 9 * s), radius=r, fill=(40, 10, 5, 120))
        ve.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=mau_hop + (255,), outline=HOP_VIEN_MAU + (255,),
                             width=vien)
        ty = y0 + ((y1 - y0) - cao_px) / 2.0 - b[1]
        ve.text((x0 + g["le"], ty), d["chu"], font=f, fill=mau_chu + (255,))
        if d["duoi"]:
            fd = font(g["co_duoi"])
            bd = fd.getbbox(d["duoi"])
            ve.text((x0 + g["le"] + do_rong(d["chu"], g["co"]) + g["co"] * 0.06, ty + b[3] - bd[3]), d["duoi"],
                    font=fd, fill=mau_chu + (255,))
        hop_chu.append({"hop": [round(v, 1) for v in (x0, y0, x1, y1)], "chu": d["chu"] + d["duoi"],
                        "cao_px": cao_px, "co": round(g["co"], 1), "to": d["to"], "mau_chu": _hex(mau_chu),
                        "mau_hop": _hex(mau_hop), "vien_px": vien, "vien_mau": _hex(HOP_VIEN_MAU), "bong": True,
                        "kieu": "hop_khuon"})
    ket = anh.convert("RGBA")
    ket.alpha_composite(bong.filter(ImageFilter.GaussianBlur(max(2, 9 * s))))
    ket.alpha_composite(lop)
    ket = ket.convert("RGB")
    os.makedirs(os.path.dirname(dich) or ".", exist_ok=True)
    tam = dich + ".tmp.png"
    ket.save(tam, format="PNG")
    _thay_tep(tam, dich)
    try:
        bc = do_bia.cham_hop(ket, hop_chu)
        cac_hop = [h["hop"] for h in hop_chu]
        # Hộp chữ là THIẾT KẾ của khuôn (đè nhẹ có chủ đích) — không phải khung bộ vẽ thêm: không tính chồng/che.
        bc["bo_cuc"] = {"so_khung": len(hop_chu), "chong_khung": False, "che_chu_the": 0.0, "dt_khung": 0.0,
                        "che_chu_the_phan": 0.0,
                        "hop_che_chu_the": round(do_bia.phan_chu_the_bi_che(chu_the, cac_hop, W, H), 3)}
        bc.update(hop_chu=hop_chu, kich_thuoc=[W, H], kieu_bia="hop", font=os.path.basename(font_duong))
        do_bia.ghi_bao_cao(dich, bc, anh=ket)
        if bao_cao is not None:
            bao_cao.clear()
            bao_cao.update(bc)
    except Exception as loi:  # noqa: BLE001 — đo hỏng không được làm mất bìa đã vẽ
        if bao_cao is not None:
            bao_cao.clear()
            bao_cao.update({"dat": None, "loi": str(loi)[:200]})
    return True


def _hinh_dong(doan, b, font, vien_cua, rong_dong, hop_dong, y_moc: float, tu_tren: bool) -> Dict[str, Any]:
    """Hình học MỘT dòng (chưa vẽ): vị trí chữ, hộp dòng, hộp khung, chiều cao nét chữ."""
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
    s = "".join(p["chu"] for p in doan)
    _l, bt, _r2, bd = f.getbbox(s)
    # 19/10/2026 (`bia_lo`): độ "đậm giả" theo nét bìa thắng đo được (`dam_pct` của tầng), mặc định như cũ
    dam = max(1, int(c * float(t.get("dam_pct") or 0.022)))
    hop = (x - vien, top, x + rong - vien, top + h)
    hop_khung = (x - vien - c * 0.12, top, x + rong - vien - c * 0.07 + c * 0.12, top + h)
    if _hop_ro(t) is not None:
        # Hộp của khuôn: ôm sát chữ (lề trong = `vien`), lùi 6% chiều cao dòng trên/dưới để các hộp xếp chồng
        # có khe; chữ căn giữa hộp theo đúng nét của chuỗi. Đo độ đọc được trên chính hộp này.
        dai_chu = rong - 2 * vien - c * 0.07
        le_doc = h * 0.06
        hop = hop_khung = (x - vien - c * 0.035, top + le_doc, x + dai_chu + vien + c * 0.035, top + h - le_doc)
        y = top + h / 2.0 - (bt + bd) / 2.0
    return {"t": t, "doan": doan, "c": c, "f": f, "vien": vien, "dam": dam, "x": x, "y": y, "top": top,
            "h": h, "rong": rong, "vx0": vx0, "vx1": vx1, "cao_px": float(max(1, bd - bt)),
            "hop": hop, "hop_khung": hop_khung, "day": top + h if tu_tren else top}


def _xep_tu_tren(t: Dict[str, Any]) -> bool:
    """Tầng xếp từ mép TRÊN xuống: tầng "tren", và MỌI tầng có hộp canh một bên — một cột hộp chữ liền từ góc
    trên như bìa TL4-T7 (bìa chủ duyệt 13/10 `workspace/cong-cu/bia_tl4.py`), không chia hai đầu để hở giữa."""
    return str(t.get("vi_tri") or "tren") == "tren" or bool(_canh_hop(t))


def _kieu_hop_khuon(g: Dict[str, Any], H: int) -> Dict[str, Any]:
    """Kiểu của dòng có HỘP khuôn: hộp đặc màu khuôn, chữ màu khuôn (không viền, không bóng chữ).

    Đọc được: đoạn chữ gần trùng màu hộp (AI tô nhầm) đổi sang trắng/đen — màu nào tương phản hơn; rồi màu TỐI
    hơn trong cặp chữ/hộp tối dần 8%/bước (≤12 bước) tới khi đạt ngưỡng tương phản theo cỡ dòng của `do_bia`."""
    from . import do_bia  # noqa: PLC0415
    hop = _hop_ro(g["t"]) or (20, 20, 20)
    nguong = do_bia.nguong_theo_co(100.0 * g["cao_px"] / float(max(1, H)))

    def tp(a, b) -> float:
        return do_bia.ti_le_tuong_phan(do_bia.do_sang(a), do_bia.do_sang(b))

    mau = []
    for p in g["doan"]:
        m = _mau_rgb(p.get("mau", ""), do_bia.TRANG)
        if tp(m, hop) < 2.0:
            m = max((do_bia.TRANG, do_bia.DEN), key=lambda x: tp(x, hop))
        mau.append(m)

    def toi(rgb, he=0.92):
        return tuple(int(v * he) for v in rgb)
    for _ in range(12):
        xau = min(mau, key=lambda m: tp(m, hop))
        if tp(xau, hop) >= nguong:
            break
        if do_bia.do_sang(hop) <= do_bia.do_sang(xau):
            hop = toi(hop)
        else:
            mau = [toi(m) if do_bia.do_sang(m) <= do_bia.do_sang(hop) else m for m in mau]
    return {"ten": "hop_khuon", "vien": hop, "chinh": mau[0] if mau else do_bia.TRANG, "nhan": tuple(mau),
            "mau": mau, "vien_he": 0.0, "bong": 0,
            "khung": {"mau": hop, "alpha": 1.0, "dang": "hop", "rieng": True}}


def _ve_dong_kieu(ve, ve_bong, g: Dict[str, Any]) -> None:
    """Vẽ MỘT dòng theo kiểu đã chọn: bóng đổ, viền (màu viền của kiểu) rồi chữ từng đoạn.
    "Đậm giả": Yu Gothic Bold mảnh hơn nét Black của bìa thật — viền rộng (dam + vien) trước, rồi chữ
    kèm viền CÙNG MÀU (dam) đè lên."""
    k = g["kieu"]
    f, x, y = g["f"], g["x"], g["y"]
    # 13/10/2026: 0 là giá trị THẬT (hộp khuôn: không viền, không bóng chữ) — chỉ thiếu khoá mới dùng mặc định
    vien = max(1, int(round(g["vien"] * float(1.0 if k.get("vien_he") is None else k["vien_he"]))))
    dam = g["dam"]
    vm = tuple(int(v) for v in k["vien"][:3])
    a_bong = int(200 if k.get("bong") is None else k["bong"])
    x0 = x
    for p in g["doan"]:
        ve_bong.text((x + vien * 0.6, y + vien * 0.9), p["chu"], font=f, fill=(0, 0, 0, a_bong),
                     stroke_width=vien + dam, stroke_fill=(0, 0, 0, a_bong))
        ve.text((x, y), p["chu"], font=f, fill=vm + (255,), stroke_width=vien + dam, stroke_fill=vm + (255,))
        x += ve.textlength(p["chu"], font=f)
    x = x0
    for p, mau in zip(g["doan"], k["mau"]):
        mau = tuple(int(v) for v in mau[:3])
        ve.text((x, y), p["chu"], font=f, fill=mau + (255,), stroke_width=dam, stroke_fill=mau + (255,))
        x += ve.textlength(p["chu"], font=f)


def bo_tri_chu(loai: str, chu_tang: Sequence[Dict[str, Any]],
               khuon_chu: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Gán vùng/canh/vai "tầng chính" cho từng tầng trước `ve_chu_len_anh`.

    - "khuon": theo bìa thắng — mọi tầng căn giữa, trải cả bề ngang; tầng dưới là
      tầng chính.
    - "chuan_ngach": nhân vật bên TRÁI, tầng trên ở 64% bên PHẢI (tự xuống 2 dòng
      nếu dài), tầng dưới trải cả bề ngang và là tầng chính.
    - 13/10/2026: tầng có HỘP khuôn canh một bên (`gan_kieu_khuon`) → cột `COT_CHU_KHOI` bên đó, canh mép.
    Cỡ chữ do `ve_chu_len_anh` tự cân theo luật diện tích/chiều cao."""
    ra = []
    for t in chu_tang:
        t2 = dict(t)
        vt = str(t.get("vi_tri") or "tren")
        chinh = vt != "tren"
        canh = _canh_hop(t)
        if loai == "chuan_ngach" and vt == "tren":
            t2.update(vung=(0.36, 1.0), can="phai", chinh=False)
        elif canh:
            t2.update(vung=(0.0, COT_CHU_KHOI) if canh == "trai" else (1.0 - COT_CHU_KHOI, 1.0), can=canh,
                      chinh=chinh)
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
            # 13/10/2026: khuôn kiểu HỘP — chữ luôn do code vẽ (thứ bậc + phông bo tròn mô hình ảnh không vẽ được).
            hop = kieu_hop(khuon.get("khuon_chu"))
            muc = [{"so": SO_KHUON_DAU + i, "kieu": TIEN_TO_KHUON if i == 0 else "{0}_{1}".format(TIEN_TO_KHUON, i + 1),
                    "mo_ta": "rebuild the channel's measured winning thumbnail", "nhom": "khuon",
                    "ve_chu": "ma" if hop else cach_ve(i)} for i in range(n_khuon)]
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
- nen: background matches (dominant colour, darkness, glow/halo behind character, effects, rendering style)
- nhan_vat: the same character as in IMAGE 1, placed and sized like the winner, clear pose and expression
- chu_bo_cuc: text tiers in the same places, same colours per tier, same text treatment as IMAGE 1 (bare \
outlined lettering, or solid boxes behind the lines when IMAGE 1 has them)
- chinh_ta: the Japanese text is spelled exactly as expected, no garbled/extra glyphs
- doc_120px: text still readable in IMAGE 3
- dung_nhan_vat: character is recognisably the SAME character as in IMAGE 1, not deformed
Also "suc_bam": 0-10, how close its click-pull on a phone/TV home feed is to IMAGE 1 (10 = as \
strong as the winner), "chu_doc_ra": every text line you can read on the candidate, exactly, in \
reading order (include any stray text on props), and "khac_biet": the 1-4 biggest visible \
differences from IMAGE 1.
Be a STRICT art director: pass=true only when that item would clearly read as the same series as \
IMAGE 1. Do not be polite; most rebuilds miss something.
Return JSON only: {{"nen": {{"pass": true, "ly_do": ""}}, "nhan_vat": {{...}}, "chu_bo_cuc": {{...}}, \
"chinh_ta": {{...}}, "doc_120px": {{...}}, "dung_nhan_vat": {{...}}, "suc_bam": 0, \
"chu_doc_ra": ["..."], "khac_biet": ["..."], "tom_tat": "one sentence in English"}}"""
