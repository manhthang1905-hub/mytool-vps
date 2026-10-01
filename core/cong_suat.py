"""Đo CÔNG SUẤT THẬT của máy — thuần đọc đĩa, không mạng, không sửa gì.

═══ VÌ SAO CÓ MODULE NÀY ═══

`workspace/LO-TRINH-PHAT-HANH-V3.md` (Đợt 0 mục 0.1) cần một con số NỀN đo
TRƯỚC khi sửa `core/che_do_vps.py` (Đợt 1 mục 1.1) — nếu không có số trước, sau
này không ai chứng minh được việc sửa có thật sự nhanh hơn hay không, chỉ có
cảm giác "hình như nhanh hơn".

Ba nguồn số liệu, đều đã nằm sẵn trên đĩa từ trước:

* `PROJECTS/AUTO/<kênh>/<lượt>/trang-thai.json` — mốc `bắt_đầu`/`kết_thúc`
  (epoch giây) của từng khâu trong một lượt sản xuất video.
* `vm/trang-thai.json`, khoá `phien_ket_qua@<kênh>` — mốc bắt đầu/kết thúc một
  PHIÊN KÊNH (mở trình duyệt, cào Studio, đăng, trả lời bình luận).
* `vm/logs/dang-dom.log` — nhật ký máy đăng; đo được thời lượng TẢI LÊN từ lúc
  bấm chọn tệp tới lúc xác nhận xong.
* `workspace/tu-chay/*.json` — mỗi ngày một tệp, biết được bao nhiêu kênh chạy
  thật và bao nhiêu video đã xong trong ngày (đối chiếu ước tính với thực tế).

═══ BA LỚP (chốt ở LO-TRINH-PHAT-HANH-V3.md, "Luật điều phối") ═══

* Lớp A — API: máy chỉ CHỜ máy chủ ShopAPI, không ăn CPU/RAM cục bộ trong lúc
  chờ. Chạy song song nhiều làn không tốn thêm tài nguyên MÁY NÀY.
* Lớp B — máy nặng: FFmpeg (dựng, giọng đọc đoạn cuối), Whisper (phụ đề) — ăn
  CPU/RAM thật của máy, không nên chạy nhiều việc cùng lúc trên VPS nhỏ.
* Lớp C — trình duyệt: quét Studio, tải lên — mỗi lúc chỉ MỘT trình duyệt
  (luật riêng của VPS, xem `CLAUDE.local.md`).

Lớp B và C dùng CHUNG một khe loại trừ (không thể chạy FFmpeg nặng cùng lúc
trình duyệt đang tải lên mà máy không ì) — nên công thức công suất gộp
chung "khe B∪C" cho cả hai.

CLI: ``python -m core.cong_suat --bao-cao [--tu YYYY-MM-DD]``
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "LOP_KHAU", "KHE_NGAY_PHUT", "MOC_MAC_DINH",
    "doc_khau", "doc_phien_quet", "doc_tai_len", "doc_hoat_dong_kenh",
    "phan_tich", "ghi_bao_cao", "do_chu_ky_that",
    "doc_nhat_ky_khe", "cong_suat_hien_tai", "ghi_hien_tai", "doc_hien_tai", "cau_mot_dong",
]

#: Khâu nào thuộc lớp nào — bảng "Luật điều phối" trong lộ trình v3.
#:
#: `giong-doc` (giọng đọc) đa số thời gian là CHỜ máy chủ TTS (lớp A), chỉ có
#: một "đuôi" cục bộ dưới một phút (`_noi_mp3`/`silencedetect`, lớp B) — quá
#: nhỏ để tách riêng từ một mốc bắt_đầu/kết_thúc duy nhất trong
#: `trang-thai.json`, nên xếp cả khâu vào lớp A (thành phần chiếm đa số).
LOP_KHAU: Dict[str, str] = {
    "kich-ban": "A",
    "bang-canh": "A",
    "anh": "A",
    "clip": "A",
    "thumbnail": "A",
    "giong-doc": "A",
    "phu-de": "B",
    "dung": "B",
}

#: Khe "sản xuất được" mỗi ngày, theo C.2: 24 giờ nhưng chỉ tính 80% (chừa chỗ
#: cho khởi động lại, cập nhật, máy đứng không giữa hai việc).
KHE_NGAY_PHUT = 24 * 60 * 0.8  # = 1152.0

#: Mốc ngày mặc định để so "trước/sau" — ngày `core/che_do_vps.py` ra đời và
#: ép mọi việc song song về 1 trên VPS (`git log --follow core/che_do_vps.py`
#: chỉ có một commit, 2026-09-24). Đúng khớp quan sát trong lộ trình: khâu ảnh
#: 45–150' trước mốc này, 383–482' sau đó (27–28/09).
MOC_MAC_DINH = "2026-09-24"

_RE_EPOCH_NGAY = None  # (giữ chỗ — không cần biên dịch regex cho ngày epoch)

#: Khớp một dòng nhật ký `dang-dom.log`: "<ngày giờ>,<mili> <mức>: <nội dung>".
_RE_DONG_LOG = re.compile(
    r"^(?P<luc>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+\s+\w+:\s*(?P<noi_dung>.*)$")
#: "<mã>: đã chọn tệp (hop_chon_tep) — YouTube bắt đầu tải" — mốc BẮT ĐẦU tải.
_RE_BAT_DAU_TAI = re.compile(
    r"^(?P<ma>\S+): đã chọn tệp \(hop_chon_tep\) — YouTube bắt đầu tải$")
#: "<mã>: KẾT QUẢ xong" — mốc KẾT THÚC tải (chỉ tính lượt THÀNH CÔNG).
_RE_KET_QUA_XONG = re.compile(r"^(?P<ma>\S+): KẾT QUẢ xong$")
#: Trần một lượt tải hợp lý — mốc bắt đầu/kết thúc cách nhau quá xa (nhiều giờ)
#: là ghép nhầm hai lượt tải khác nhau của cùng một mã (thử lại), không phải
#: một lượt tải thật.
_TRAN_TAI_LEN_PHUT = 6 * 60.0


def _doc_json(duong: str) -> Optional[Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ngay_tu_epoch(epoch: float) -> str:
    return datetime.fromtimestamp(float(epoch)).strftime("%Y-%m-%d")


def _qua_moc(ngay: str, tu: Optional[str]) -> bool:
    return bool(tu) and ngay < str(tu)


# ═══ NGUỒN 1 — trang-thai.json của từng lượt sản xuất ═════════════════════


def doc_khau(goc: str, tu: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mỗi bản ghi là MỘT khâu của MỘT lượt: kênh, lượt, khâu, lớp, phút, ngày.

    Bỏ qua khâu chưa có cả `bat_dau` lẫn `ket_thuc` (đang chạy dở, hoặc lượt
    cũ chưa có khâu đó) và khâu có `ket_thuc < bat_dau` (đồng hồ máy nhảy lùi,
    hoặc tệp bị sửa tay — số âm chỉ làm nhiễu trung vị, thà thiếu còn hơn sai).
    """
    ra: List[Dict[str, Any]] = []
    mau = os.path.join(goc, "PROJECTS", "AUTO", "*", "*", "trang-thai.json")
    for duong in sorted(glob.glob(mau)):
        du = _doc_json(duong)
        if not isinstance(du, dict):
            continue
        kenh = str(du.get("ma_kenh") or "")
        luot = str(du.get("ma_luot") or "")
        khau = du.get("khau")
        if not isinstance(khau, dict):
            continue
        for ma_khau, muc in khau.items():
            if not isinstance(muc, dict):
                continue
            bd, kt = muc.get("bat_dau"), muc.get("ket_thuc")
            if not isinstance(bd, (int, float)) or not isinstance(kt, (int, float)):
                continue
            if kt < bd:
                continue
            ngay = _ngay_tu_epoch(bd)
            if tu and ngay < tu:
                continue
            ra.append({
                "kenh": kenh, "luot": luot, "khau": ma_khau,
                "lop": LOP_KHAU.get(ma_khau, "khac"),
                "phut": (kt - bd) / 60.0, "ngay": ngay,
                "trang_thai": muc.get("trang_thai") or "",
            })
    return ra


# ═══ NGUỒN 2 — phiên kênh (vm/trang-thai.json) ═════════════════════════════


def doc_phien_quet(goc: str, tu: Optional[str] = None) -> List[Dict[str, Any]]:
    """Thời lượng từng PHIÊN KÊNH (`phien_ket_qua@<kênh>`) — lớp C.

    Chỉ một khoá `phien_ket_qua@<kênh>` cho MỖI KÊNH (bị ghi đè ở phiên sau),
    nên đây là ảnh chụp phiên GẦN NHẤT của mỗi kênh, không phải toàn bộ lịch
    sử — đủ để ước lượng, không đủ để vẽ biểu đồ theo ngày.
    """
    du = _doc_json(os.path.join(goc, "vm", "trang-thai.json"))
    if not isinstance(du, dict):
        return []
    ra: List[Dict[str, Any]] = []
    for khoa, muc in du.items():
        if not khoa.startswith("phien_ket_qua@") or not isinstance(muc, dict):
            continue
        kenh = khoa.split("@", 1)[1]
        bd_s, kt_s = muc.get("bat_dau"), muc.get("ket_thuc")
        if not bd_s or not kt_s:
            continue
        try:
            bd = datetime.strptime(str(bd_s), "%Y-%m-%d %H:%M:%S")
            kt = datetime.strptime(str(kt_s), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if kt < bd:
            continue
        ngay = bd.strftime("%Y-%m-%d")
        if tu and ngay < tu:
            continue
        ra.append({
            "kenh": kenh, "loai": "phien_quet", "lop": "C",
            "phut": (kt - bd).total_seconds() / 60.0, "ngay": ngay,
        })
    return ra


# ═══ NGUỒN 3 — nhật ký máy đăng (vm/logs/dang-dom.log) ═════════════════════


def doc_tai_len(goc: str, tu: Optional[str] = None) -> List[Dict[str, Any]]:
    """Thời lượng TẢI LÊN từng video — lớp C. Khớp mốc bắt đầu/kết quả THEO MÃ.

    Nhật ký này chỉ giữ một cửa sổ gần đây (bị xoay vòng) — kết quả là mẫu
    NHỎ, không phải toàn bộ lịch sử tải lên. Ghép mốc gần nhất TRƯỚC mỗi dòng
    "KẾT QUẢ xong" cùng mã, để thử lại (mở Chrome lại, bấm lại) không lẫn vào
    lượt trước.
    """
    duong = os.path.join(goc, "vm", "logs", "dang-dom.log")
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            dong_list = tep.readlines()
    except OSError:
        return []
    bat_dau_gan_nhat: Dict[str, datetime] = {}
    ra: List[Dict[str, Any]] = []
    for dong in dong_list:
        khop = _RE_DONG_LOG.match(dong.rstrip("\n"))
        if not khop:
            continue
        try:
            luc = datetime.strptime(khop.group("luc"), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        noi_dung = khop.group("noi_dung")
        m_bd = _RE_BAT_DAU_TAI.match(noi_dung)
        if m_bd:
            bat_dau_gan_nhat[m_bd.group("ma")] = luc
            continue
        m_kt = _RE_KET_QUA_XONG.match(noi_dung)
        if not m_kt:
            continue
        ma = m_kt.group("ma")
        bd = bat_dau_gan_nhat.pop(ma, None)
        if bd is None or luc < bd:
            continue
        phut = (luc - bd).total_seconds() / 60.0
        if phut <= 0 or phut > _TRAN_TAI_LEN_PHUT:
            continue
        ngay = bd.strftime("%Y-%m-%d")
        if tu and ngay < tu:
            continue
        # Mã dạng "TL1-T7-0007" — cắt bỏ đuôi "-<lượt>" để ra mã kênh.
        kenh = ma.rsplit("-", 1)[0] if "-" in ma else ma
        ra.append({"kenh": kenh, "ma": ma, "loai": "tai_len", "lop": "C",
                   "phut": phut, "ngay": ngay})
    return ra


# ═══ NGUỒN 4 — workspace/tu-chay/*.json (thực tế mỗi ngày) ═════════════════


def doc_hoat_dong_kenh(goc: str, tu: Optional[str] = None) -> Dict[str, Any]:
    """Mỗi ngày: bao nhiêu kênh có chạy thật, bao nhiêu video đã xong.

    Đếm "xong video" bằng cách soát chữ trong `tom_tat` mỗi kết quả — tệp
    không có trường số đếm riêng, và đổi định dạng `tom_tat` là việc của một
    phiên khác nên soát chữ THÔ (chứa "xong video") an toàn hơn soát chuỗi dài.
    """
    theo_ngay: Dict[str, Dict[str, Any]] = {}
    mau = os.path.join(goc, "workspace", "tu-chay", "*.json")
    for duong in sorted(glob.glob(mau)):
        du = _doc_json(duong)
        if not isinstance(du, dict):
            continue
        ngay = str(du.get("ngay") or os.path.splitext(os.path.basename(duong))[0])
        if tu and ngay < tu:
            continue
        kenh_that: set = set()
        so_video = 0
        for run in du.get("runs") or []:
            if not isinstance(run, dict) or run.get("che_do") != "that":
                continue
            for kq in run.get("ket_qua") or []:
                if not isinstance(kq, dict):
                    continue
                kenh = str(kq.get("kenh") or "")
                if kenh:
                    kenh_that.add(kenh)
                if "xong video" in str(kq.get("tom_tat") or ""):
                    so_video += 1
        if kenh_that or so_video:
            theo_ngay[ngay] = {"so_kenh": len(kenh_that), "so_video": so_video,
                               "kenh": sorted(kenh_that)}
    return theo_ngay


# ═══ THỐNG KÊ ════════════════════════════════════════════════════════════


def _thong_ke(mau: Sequence[float]) -> Dict[str, Any]:
    if not mau:
        return {"so_mau": 0, "trung_vi": None, "min": None, "max": None}
    return {
        "so_mau": len(mau),
        "trung_vi": round(statistics.median(mau), 1),
        "min": round(min(mau), 1),
        "max": round(max(mau), 1),
    }


def _gom_theo(mau: Sequence[Dict[str, Any]], khoa: str) -> Dict[str, List[float]]:
    gom: Dict[str, List[float]] = {}
    for muc in mau:
        gom.setdefault(str(muc.get(khoa)), []).append(float(muc["phut"]))
    return gom


def _chia_giai_doan(mau: Sequence[Dict[str, Any]], moc: str) -> Dict[str, List[Dict[str, Any]]]:
    truoc = [m for m in mau if m["ngay"] < moc]
    sau = [m for m in mau if m["ngay"] >= moc]
    return {"truoc_moc": truoc, "tu_moc": sau, "tong": list(mau)}


# ═══ PHÂN TÍCH TỔNG ═════════════════════════════════════════════════════


# ═══ ĐO THẬT CHU KỲ MỖI VIDEO (30/09/2026) ═══════════════════════════════════
#
# Bản đầu ước "8 video/ngày mỗi làn × L" và L=1 mặc định — sai với máy thật:
# `cai-dat.json lan_api=4`, dựng một lần nén (~10-40', `dung_mot_lan`), và MỖI
# KÊNH chạy TUẦN TỰ (xong video này mới mở video kế) ~3-6 giờ/video. Trần thật
# = tổng các kênh (24h / chu kỳ một video), chu kỳ đo từ `trang-thai.json`.


def _so_lan_api_that(goc: str) -> Optional[int]:
    """`lan_api` khai trong `workspace/cai-dat.json` (1..4); không khai → None."""
    cai = _doc_json(os.path.join(goc, "workspace", "cai-dat.json"))
    try:
        v = int((cai or {}).get("lan_api"))
    except (TypeError, ValueError, AttributeError):
        return None
    return max(1, min(4, v)) if v >= 1 else None


def do_chu_ky_that(goc: str, so_ngay: float = 3.0,
                   bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Chu kỳ THẬT mỗi video từ `PROJECTS/AUTO/<kênh>/<lượt>/trang-thai.json`
    trong `so_ngay` ngày gần nhất (lượt có khâu `dung` xong; chu kỳ = từ bắt
    đầu khâu đầu tới hết khâu dựng, không tính thời gian nằm chờ giữa hai lượt).

    `video_ngay` mỗi kênh = 1440/chu kỳ trung vị (kênh chạy tuần tự);
    `tong_video_ngay` = tổng các kênh. `so_luot`=0 nếu chưa có mẫu.
    `khau_nghen` = khâu có trung vị phút lớn nhất."""
    den = bay_gio if bay_gio is not None else datetime.now().timestamp()
    tu = den - so_ngay * 86400.0
    chu_ky: Dict[str, List[float]] = {}
    theo_khau: Dict[str, List[float]] = {}
    so_luot = 0
    for duong in glob.glob(os.path.join(goc, "PROJECTS", "AUTO", "*", "*", "trang-thai.json")):
        du = _doc_json(duong)
        khau = du.get("khau") if isinstance(du, dict) else None
        if not isinstance(khau, dict):
            continue
        dung = khau.get("dung")
        if not isinstance(dung, dict) or dung.get("trang_thai") != "xong" \
                or not isinstance(dung.get("ket_thuc"), (int, float)) or dung["ket_thuc"] < tu:
            continue
        bd = [m["bat_dau"] for m in khau.values()
              if isinstance(m, dict) and isinstance(m.get("bat_dau"), (int, float))]
        if not bd or dung["ket_thuc"] < min(bd):
            continue
        so_luot += 1
        chu_ky.setdefault(str(du.get("ma_kenh") or ""), []).append((dung["ket_thuc"] - min(bd)) / 60.0)
        for ten, m in khau.items():
            if isinstance(m, dict) and isinstance(m.get("bat_dau"), (int, float)) \
                    and isinstance(m.get("ket_thuc"), (int, float)) and m["ket_thuc"] >= m["bat_dau"]:
                theo_khau.setdefault(ten, []).append((m["ket_thuc"] - m["bat_dau"]) / 60.0)
    theo_kenh: Dict[str, Any] = {}
    for kenh, ds in sorted(chu_ky.items()):
        vi = statistics.median(ds)
        theo_kenh[kenh] = {"so_video": len(ds), "chu_ky_trung_vi_phut": round(vi, 1),
                           "video_ngay": round(1440.0 / vi, 2) if vi > 0 else None}
    phut_khau = {k: round(statistics.median(v), 1) for k, v in sorted(theo_khau.items())}
    tong_khau = sum(phut_khau.values())
    nghen = max(phut_khau, key=lambda k: phut_khau[k]) if phut_khau else None
    return {"so_ngay": so_ngay, "so_luot": so_luot, "theo_kenh": theo_kenh,
            "tong_video_ngay": round(sum(k["video_ngay"] or 0 for k in theo_kenh.values()), 2),
            "phut_theo_khau": phut_khau, "khau_nghen": nghen,
            "khau_nghen_phut": phut_khau.get(nghen) if nghen else None,
            "ty_le_nghen": round(phut_khau[nghen] / tong_khau, 2) if nghen and tong_khau else None}


def phan_tich(goc: str, tu: Optional[str] = None, moc: str = MOC_MAC_DINH,
              so_kenh: Optional[int] = None, lan_song_song: Optional[int] = None) -> Dict[str, Any]:
    """Gộp bốn nguồn số liệu thành một báo cáo công suất.

    `so_kenh`: số kênh dùng để ước C.2 — để trống thì tự đếm số kênh có chạy
    thật (`che_do: "that"`) trong `workspace/tu-chay/*.json`, ngày gần nhất có
    dữ liệu. `lan_song_song` (L): số làn lớp A chạy song song hiện tại — mặc
    định 1 vì đó là hành vi CHƯA SỬA của `core/che_do_vps.py` (Đợt 1 mục 1.1
    ép mọi việc về 1 làn trên VPS, kể cả việc chỉ CHỜ máy chủ).
    """
    if lan_song_song is None:   # số làn THẬT trong cài đặt; chưa khai mới về 1
        lan_song_song = _so_lan_api_that(goc) or 1
    khau = doc_khau(goc, tu=tu)
    phien = doc_phien_quet(goc, tu=tu)
    tai_len = doc_tai_len(goc, tu=tu)
    hoat_dong = doc_hoat_dong_kenh(goc, tu=tu)

    theo_khau: Dict[str, Any] = {}
    giai_doan = _chia_giai_doan(khau, moc)
    for ten_gd, danh_sach in giai_doan.items():
        theo_khau[ten_gd] = {
            ma_khau: _thong_ke(mau)
            for ma_khau, mau in _gom_theo(danh_sach, "khau").items()
        }

    theo_lop: Dict[str, Any] = {}
    for ten_gd, danh_sach in giai_doan.items():
        theo_lop[ten_gd] = {
            lop: _thong_ke(mau) for lop, mau in _gom_theo(danh_sach, "lop").items()
        }

    thong_ke_phien = _thong_ke([m["phut"] for m in phien])
    thong_ke_tai_len = _thong_ke([m["phut"] for m in tai_len])

    # ── C.2: khe B∪C, ước video/ngày tối đa ─────────────────────────────────
    #
    # Q  = phút/kênh/ngày CỐ ĐỊNH của lớp C (phiên quét — chạy mỗi ngày dù có
    #      video mới hay không).
    # Bv = phút/VIDEO của lớp B (dựng + phụ đề).
    # Ct = phút/VIDEO của lớp C còn lại (tải lên).
    # N  = số kênh. r  = video/kênh/ngày (ẩn số cần tìm trần).
    #
    #   N·Q + N·r·(Bv+Ct) ≤ KHE_NGAY_PHUT
    #   => tổng video/ngày (N·r) ≤ (KHE_NGAY_PHUT − N·Q) / (Bv+Ct)
    #
    # Lớp A không tranh tài nguyên MÁY (chỉ chờ mạng), nên trần riêng của nó
    # là số làn song song × sức một làn (~8 video/ngày mỗi làn, đo được ở
    # `workspace/LO-TRINH-PHAT-HANH-V3.md`).
    q_phien = thong_ke_phien["trung_vi"] or 0.0
    dung_vi = (theo_khau["tong"].get("dung") or {}).get("trung_vi") or 0.0
    phude_vi = (theo_khau["tong"].get("phu-de") or {}).get("trung_vi") or 0.0
    bv = dung_vi + phude_vi
    ct = thong_ke_tai_len["trung_vi"] or 0.0

    n = so_kenh
    if n is None:
        ngay_gan_nhat = max(hoat_dong.keys(), default=None)
        n = hoat_dong.get(ngay_gan_nhat, {}).get("so_kenh") if ngay_gan_nhat else None
        n = n or 0

    video_ngay_bc = None
    if n and (bv + ct) > 0:
        video_ngay_bc = max(0.0, (KHE_NGAY_PHUT - n * q_phien) / (bv + ct))
    video_ngay_a = 8.0 * max(1, lan_song_song)
    do_thuc = do_chu_ky_that(goc)
    if do_thuc["so_luot"] >= 3:
        # Có số đo thật: kênh chạy tuần tự nên trần = tổng 1440/chu kỳ mỗi kênh.
        video_ngay_a = do_thuc["tong_video_ngay"]
    video_ngay_toi_da = (min(video_ngay_bc, video_ngay_a)
                         if video_ngay_bc is not None else video_ngay_a)

    # % khe B∪C dùng ước tính/ngày, theo mức sản xuất THỰC TẾ đo được gần nhất.
    video_thuc_te_ngay = None
    if hoat_dong:
        ngay_gan_nhat = max(hoat_dong.keys())
        video_thuc_te_ngay = hoat_dong[ngay_gan_nhat]["so_video"]
    phan_tram_khe = None
    if n and video_thuc_te_ngay is not None:
        tieu_thu = n * q_phien + video_thuc_te_ngay * (bv + ct)
        phan_tram_khe = round(100.0 * tieu_thu / KHE_NGAY_PHUT, 1)

    may_con_du = None
    if video_thuc_te_ngay is not None:
        may_con_du = round(video_ngay_toi_da - video_thuc_te_ngay, 1)

    return {
        "sinh_luc": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tu": tu,
        "moc_giai_doan": moc,
        "so_mau": {"khau": len(khau), "phien_quet": len(phien),
                   "tai_len": len(tai_len), "ngay_hoat_dong": len(hoat_dong)},
        "phut_theo_khau": theo_khau,
        "phut_theo_lop": theo_lop,
        "phien_quet_phut": thong_ke_phien,
        "tai_len_phut": thong_ke_tai_len,
        "hoat_dong_theo_ngay": hoat_dong,
        "do_thuc_3_ngay": do_thuc,
        "cong_thuc_c2": {
            "khe_ngay_phut": round(KHE_NGAY_PHUT, 1),
            "so_kenh_n": n,
            "lan_song_song_lop_a": lan_song_song,
            "q_phien_quet_phut": round(q_phien, 1),
            "bv_lop_b_phut_moi_video": round(bv, 1),
            "ct_lop_c_phut_moi_video": round(ct, 1),
            "video_ngay_toi_da_lop_bc": (round(video_ngay_bc, 2)
                                         if video_ngay_bc is not None else None),
            "video_ngay_toi_da_lop_a": video_ngay_a,
            "video_ngay_toi_da": round(video_ngay_toi_da, 2),
            "video_ngay_thuc_te_gan_nhat": video_thuc_te_ngay,
            "phan_tram_khe_bc_dung_uoc_tinh": phan_tram_khe,
            "may_con_du_video_ngay": may_con_du,
        },
    }


# ═══ BÁO CÁO ═════════════════════════════════════════════════════════════


def _dong_bang_khau(theo_khau_gd: Dict[str, Any]) -> List[str]:
    dong = ["| khâu | lớp | số mẫu | trung vị (phút) | min | max |",
           "|---|---|---:|---:|---:|---:|"]
    for ma_khau in sorted(theo_khau_gd.keys()):
        tk = theo_khau_gd[ma_khau]
        lop = LOP_KHAU.get(ma_khau, "khac")
        if tk["so_mau"] == 0:
            dong.append("| {0} | {1} | 0 | — | — | — |".format(ma_khau, lop))
        else:
            dong.append("| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                ma_khau, lop, tk["so_mau"], tk["trung_vi"], tk["min"], tk["max"]))
    return dong


def _dinh_dang_md(kq: Dict[str, Any]) -> str:
    c2 = kq["cong_thuc_c2"]
    dong = [
        "# Báo cáo công suất — {0}".format(kq["sinh_luc"]),
        "",
        "Đo THẬT trên đĩa máy này (không gọi mạng). Mốc so trước/sau: "
        "**{0}** (ngày `core/che_do_vps.py` ép song song về 1 trên VPS).".format(
            kq["moc_giai_doan"]),
        "",
        "Số mẫu: {0} khâu · {1} phiên quét · {2} lượt tải lên · {3} ngày có "
        "hoạt động thật.".format(
            kq["so_mau"]["khau"], kq["so_mau"]["phien_quet"],
            kq["so_mau"]["tai_len"], kq["so_mau"]["ngay_hoat_dong"]),
        "",
        "## Phút/khâu — TRƯỚC mốc {0}".format(kq["moc_giai_doan"]),
        "",
    ]
    dong += _dong_bang_khau(kq["phut_theo_khau"]["truoc_moc"])
    dong += ["", "## Phút/khâu — TỪ mốc {0}".format(kq["moc_giai_doan"]), ""]
    dong += _dong_bang_khau(kq["phut_theo_khau"]["tu_moc"])
    dong += ["", "## Phút/khâu — CẢ GIAI ĐOẠN", ""]
    dong += _dong_bang_khau(kq["phut_theo_khau"]["tong"])
    dong += [
        "",
        "## Lớp C (trình duyệt)",
        "",
        "- Phiên quét/kênh: trung vị {0} phút (min {1}, max {2}, {3} mẫu).".format(
            kq["phien_quet_phut"]["trung_vi"], kq["phien_quet_phut"]["min"],
            kq["phien_quet_phut"]["max"], kq["phien_quet_phut"]["so_mau"]),
        "- Tải lên/video: trung vị {0} phút (min {1}, max {2}, {3} mẫu).".format(
            kq["tai_len_phut"]["trung_vi"], kq["tai_len_phut"]["min"],
            kq["tai_len_phut"]["max"], kq["tai_len_phut"]["so_mau"]),
        "",
        "## Ước công suất (công thức C.2)",
        "",
        "- Khe B∪C: {0} phút/ngày (24h × 0,8).".format(c2["khe_ngay_phut"]),
        "- N = {0} kênh, L = {1} làn song song lớp A.".format(
            c2["so_kenh_n"], c2["lan_song_song_lop_a"]),
        "- Q (phiên quét, phút/kênh/ngày) = {0}.".format(c2["q_phien_quet_phut"]),
        "- Bv (lớp B, phút/video) = {0}.".format(c2["bv_lop_b_phut_moi_video"]),
        "- Ct (lớp C tải lên, phút/video) = {0}.".format(c2["ct_lop_c_phut_moi_video"]),
        "- Trần lớp B∪C: {0} video/ngày.".format(c2["video_ngay_toi_da_lop_bc"]),
        "- Trần lớp A ({1}): {0} video/ngày.".format(
            c2["video_ngay_toi_da_lop_a"],
            "đo thật 3 ngày: tổng 24h/chu kỳ mỗi kênh"
            if (kq.get("do_thuc_3_ngay") or {}).get("so_luot", 0) >= 3 else "ước 8×L"),
        "- **Ước tối đa: {0} video/ngày cho {1} kênh.**".format(
            c2["video_ngay_toi_da"], c2["so_kenh_n"]),
        "- Thực tế đo được gần nhất: {0} video/ngày.".format(
            c2["video_ngay_thuc_te_gan_nhat"]),
        "- % khe B∪C đang dùng ước tính: {0}%.".format(
            c2["phan_tram_khe_bc_dung_uoc_tinh"]),
        "",
        "**Máy còn dư {0} video/ngày** (so ước tối đa với thực tế đo gần "
        "nhất).".format(c2["may_con_du_video_ngay"]),
        "",
    ]
    dt = kq.get("do_thuc_3_ngay") or {}
    if dt.get("so_luot"):
        dong += ["## Đo thật — {0} ngày gần nhất ({1} video xong)".format(dt["so_ngay"], dt["so_luot"]), ""]
        for kenh, m in dt["theo_kenh"].items():
            dong.append("- {0}: {1} video, chu kỳ trung vị {2} phút (~{3} giờ) → {4} video/ngày.".format(
                kenh, m["so_video"], m["chu_ky_trung_vi_phut"],
                round(m["chu_ky_trung_vi_phut"] / 60.0, 1), m["video_ngay"]))
        dong.append("- **Tổng: {0} video/ngày.** Khâu nghẽn: {1} ({2} phút, {3}% cộng các khâu). "
                    "Phút/khâu: {4}".format(
                        dt["tong_video_ngay"], dt["khau_nghen"], dt["khau_nghen_phut"],
                        round(100 * (dt["ty_le_nghen"] or 0)), dt["phut_theo_khau"]))
        dong.append("")
    cs = kq.get("dieu_phoi_24h") or {}
    if cs:
        dong += ["## Điều phối — 24 giờ qua (nhật ký khe)", "",
                 "- " + (cs.get("cau") or cau_mot_dong(cs)),
                 "- Khe nặng theo việc (phút): {0}".format(cs.get("phut_khe_nang_theo_viec")),
                 "- Phút khe nặng / video: {0} · phút làn API / video: {1}".format(
                     cs.get("phut_nang_moi_video"), cs.get("phut_api_moi_video")),
                 "- Trần video/ngày: theo khe nặng {0} · theo làn API {1} (nút thắt: {2})".format(
                     cs.get("tran_video_ngay_khe_nang"), cs.get("tran_video_ngay_lan_api"),
                     cs.get("nut_that")),
                 "- Vượt trần giữ khe: {0} lần · chờ khe trung vị {1} phút".format(
                     cs.get("vuot_han_khe"), cs.get("cho_khe_trung_vi_phut")), ""]
    return "\n".join(dong)


def ghi_bao_cao(goc: str, kq: Dict[str, Any], ngay: Optional[str] = None) -> Dict[str, str]:
    """Ghi `workspace/cong-suat/<ngày>.{json,md}`. Trả về hai đường dẫn đã ghi."""
    ngay = ngay or date.today().strftime("%Y-%m-%d")
    thu_muc = os.path.join(goc, "workspace", "cong-suat")
    os.makedirs(thu_muc, exist_ok=True)
    duong_json = os.path.join(thu_muc, "{0}.json".format(ngay))
    duong_md = os.path.join(thu_muc, "{0}.md".format(ngay))
    with open(duong_json, "w", encoding="utf-8") as tep:
        json.dump(kq, tep, ensure_ascii=False, indent=2)
    with open(duong_md, "w", encoding="utf-8") as tep:
        tep.write(_dinh_dang_md(kq))
    return {"json": duong_json, "md": duong_md}


# ═══ CÔNG SUẤT HIỆN TẠI — từ nhật ký khe + trạng thái điều phối (29/09/2026) ═══
#
# Bước D bản vá full công suất: sau khi bật bộ điều phối (`core/dieu_phoi.py`),
# `workspace/khe/nhat-ky.jsonl` ghi MỌI lần xin/được/nhả khe "nang" và làn "api"
# (kể cả agent, qua `core.khe`). Từ đó đo được THẬT trong 24 giờ qua: khe nặng
# bận bao nhiêu phút, làn API giữ bao nhiêu giờ, mỗi video ăn bao nhiêu phút
# khe nặng — và còn dư bao nhiêu. Chỉ ĐỀ XUẤT (thêm kênh / nâng nhịp), không tự
# đổi gì (quyết định 8 của lộ trình).

#: Mỗi làn API ra được chừng này video/ngày khi chưa đủ mẫu đo (lộ trình v3).
VIDEO_MOI_LAN_NGAY_MAC_DINH = 8.0
#: Mỗi kênh mới cần chừng này video/ngày (2 khe đăng/ngày).
VIDEO_MOI_KENH_NGAY = 2.0
#: Chưa đủ mẫu điều phối (< 2 video trong cửa sổ): phút khe nặng / video theo mô
#: hình C.2 của lộ trình (dựng + phụ đề ~45' + tải lên ~20') và phút quét/kênh/ngày.
PHUT_NANG_MOI_VIDEO_MAC_DINH = 65.0
PHUT_QUET_MOI_KENH_NGAY = 15.0


#: Việc "giữ" mà không bao giờ có "nha" (tiến trình chết giữa chừng) — 01/10/2026 đo được 3 lượt
#: `san_xuat` mở từ 30/09 09:00–10:15 chưa đóng, cộng ~27 giờ/lượt vào làn API (lan TB 5,2 > 4 làn)
#: → trần làn API 17,9 thay vì ~33. Giữ còn mở bị cắt ở lần "duoc" kế của CÙNG kênh + lớp + việc
#: (tiến trình khác — kênh chạy tuần tự), không có thì tối đa ngần này phút.
TRAN_GIU_MO_PHUT = 8 * 60.0

#: Mốc thay đổi LỚN của dây chuyền (giờ máy, "YYYY-MM-DD HH:MM:SS") — lượt bắt đầu TRƯỚC mốc chạy mã
#: cũ, không được đo chung với lượt sau mốc. Thêm mốc riêng máy: `workspace/cai-dat.json:
#: cong_suat_moc_doi: ["…"]`. 30/09 19:15:20 = gỡ trần khâu ảnh (ảnh 143–210' → 48').
MOC_DOI_LON = ("2026-09-30 19:15:20",)


def moc_doi_gan_nhat(goc: str, den: float) -> Optional[float]:
    """Mốc thay đổi lớn gần nhất ≤ `den` (epoch) | None."""
    cai = _doc_json(os.path.join(goc, "workspace", "cai-dat.json")) or {}
    them = cai.get("cong_suat_moc_doi") if isinstance(cai, dict) else None
    ds = list(MOC_DOI_LON) + ([str(x) for x in them] if isinstance(them, list) else [])
    ra: List[float] = []
    for s in ds:
        try:
            ra.append(datetime.fromisoformat(str(s).strip().replace("T", " ")).timestamp())
        except ValueError:
            continue
    ra = [x for x in ra if x <= den]
    return max(ra) if ra else None


def doc_nhat_ky_khe(goc: str, tu_luc: float, den_luc: Optional[float] = None,
                    bo_truoc: Optional[float] = None) -> Dict[str, Any]:
    """Ghép cặp "duoc" → "nha" trong `workspace/khe/nhat-ky.jsonl` (và bản
    xoay vòng `.1`) theo (pid, lớp, việc) — trả phút giữ theo lớp/việc trong
    [tu_luc, den_luc], cắt phần nằm ngoài cửa sổ. Việc còn đang giữ (chưa có
    "nha") được tính tới `den_luc` — nhưng cắt ở lần "duoc" kế của cùng kênh/lớp/việc
    và tối đa `TRAN_GIU_MO_PHUT` (giữ "ma" của tiến trình chết). `bo_truoc`: bỏ hẳn
    việc bắt đầu trước mốc này (lượt chạy mã cũ)."""
    den = den_luc if den_luc is not None else datetime.now().timestamp()
    dong: List[Dict[str, Any]] = []
    thu_muc = os.path.join(goc, "workspace", "khe")
    for ten in ("nhat-ky.1.jsonl", "nhat-ky.jsonl"):
        try:
            with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
                for chu in tep:
                    try:
                        m = json.loads(chu)
                    except ValueError:
                        continue
                    if isinstance(m, dict):
                        dong.append(m)
        except OSError:
            continue
    dong.sort(key=lambda m: float(m.get("luc") or 0))
    mo: Dict[Any, float] = {}
    phut: Dict[str, Dict[str, float]] = {"nang": {}, "api": {}}
    so_lan: Dict[str, Dict[str, int]] = {"nang": {}, "api": {}}
    vuot_han = 0
    cho_phut: List[float] = []

    def cong(lop: str, viec: str, a: float, b: float) -> None:
        a, b = max(a, tu_luc), min(b, den)
        if b > a and lop in phut:
            phut[lop][viec] = phut[lop].get(viec, 0.0) + (b - a) / 60.0

    kenh_mo: Dict[Any, str] = {}
    cu_mo: Dict[Any, Any] = {}
    bo_khoang: List[Any] = []
    for m in dong:
        lop, viec, loai = str(m.get("lop") or ""), str(m.get("viec") or ""), m.get("viec_nk")
        khoa = (m.get("pid"), lop, viec)
        luc = float(m.get("luc") or 0)
        if loai == "duoc":
            kenh = str(m.get("kenh") or "")
            if kenh:  # giữ "ma" cùng kênh/lớp/việc của tiến trình khác → đóng ở đây
                for k_cu in [k for k in mo if k[1:] == (lop, viec) and k != khoa and kenh_mo.get(k) == kenh]:
                    bd = mo.pop(k_cu)
                    cong(lop, viec, bd, min(luc, bd + TRAN_GIU_MO_PHUT * 60.0))
                    kenh_mo.pop(k_cu, None)
                for k_cu in [k for k in cu_mo if k[1:] == (lop, viec) and k != khoa and cu_mo[k][0] == kenh]:
                    k_, a_ = cu_mo.pop(k_cu)
                    bo_khoang.append((k_, a_, min(luc, a_ + TRAN_GIU_MO_PHUT * 60.0)))
            if bo_truoc is not None and luc < bo_truoc:
                cu_mo[khoa] = (kenh, luc)  # lượt mã cũ: không tính, nhớ khoảng để bỏ video của nó
                continue
            mo[khoa] = luc
            kenh_mo[khoa] = kenh
            if luc >= tu_luc and lop in so_lan:
                so_lan[lop][viec] = so_lan[lop].get(viec, 0) + 1
                try:
                    cho_phut.append(float(m.get("phut_cho") or 0.0))
                except (TypeError, ValueError):
                    pass
        elif loai == "nha" and khoa in mo:
            cong(lop, viec, mo.pop(khoa), luc)
        elif loai == "nha" and khoa in cu_mo:
            k_, a_ = cu_mo.pop(khoa)
            bo_khoang.append((k_, a_, luc))
        elif loai == "vuot_han" and luc >= tu_luc:
            vuot_han += 1
    for (pid, lop, viec), bat_dau in mo.items():
        cong(lop, viec, bat_dau, min(den, bat_dau + TRAN_GIU_MO_PHUT * 60.0))
    return {"phut": {lop: {v: round(x, 1) for v, x in d.items()} for lop, d in phut.items()},
            "so_lan": so_lan, "vuot_han": vuot_han,
            "bo_khoang": bo_khoang + [(k_, a_, min(den, a_ + TRAN_GIU_MO_PHUT * 60.0)) for k_, a_ in cu_mo.values()],
            "cho_trung_vi_phut": round(statistics.median(cho_phut), 1) if cho_phut else None}


def _video_ban_giao(goc: str, tu_luc: float, bo_truoc: Optional[float] = None,
                    bo_khoang: Sequence[Any] = ()) -> int:
    """Số video DỰNG XONG trong cửa sổ — khâu `dung` có `ket_thuc` ≥ tu_luc
    (`PROJECTS/AUTO/*/*/trang-thai.json`, chỉ đọc). `bo_truoc`: bỏ lượt có khâu bắt đầu
    trước mốc hoặc nằm trong khoảng giữ làn API của một tiến trình sinh trước mốc
    (`bo_khoang` [(kênh, từ, tới)] — lượt sinh trước mốc có thể bắt đầu khâu đầu sau mốc)."""
    dem = 0
    for duong in glob.glob(os.path.join(goc, "PROJECTS", "AUTO", "*", "*", "trang-thai.json")):
        try:
            if os.path.getmtime(duong) < tu_luc:
                continue
        except OSError:
            continue
        du = _doc_json(duong)
        muc = ((du or {}).get("khau") or {}).get("dung") if isinstance(du, dict) else None
        if isinstance(muc, dict) and isinstance(muc.get("ket_thuc"), (int, float)) \
                and float(muc["ket_thuc"]) >= tu_luc and muc.get("trang_thai") == "xong":
            if bo_truoc is not None:
                bd = [float(m["bat_dau"]) for m in (du.get("khau") or {}).values()
                      if isinstance(m, dict) and isinstance(m.get("bat_dau"), (int, float))]
                kenh = str(du.get("ma_kenh") or "")
                if bd and (min(bd) < bo_truoc or any(k_ == kenh and a_ <= min(bd) <= b_ for k_, a_, b_ in bo_khoang)):
                    continue
            dem += 1
    return dem


# ═══ TRẦN THEO Ổ ĐĨA (01/10/2026) ═══════════════════════════════════════════
#
# Mô hình "đang dọn đều" (luật dọn `core/don_dep.py`):
#   * PROJECTS: mỗi kênh giữ `giu_toi_da_luot` lượt xong + 1 lượt đang dựng →
#     phần CỐ ĐỊNH = số kênh × (giữ + 1) × GB/lượt, KHÔNG tăng theo nhịp.
#   * DONE: mỗi video nằm đó từ lúc bàn giao tới giờ công khai + 3 ngày (luật
#     DONE) → phần TỈ LỆ = video/ngày × ngày nằm DONE × GB/video, trừ phần trùng
#     liên kết cứng với `giữ` lượt mới nhất trong PROJECTS.
#   * Sàn: luôn chừa `NGUONG_O_CHAN_GB` (dưới mức ấy van ổ chặn mở lượt mới).
# Mọi cỡ đo theo inode (hardlink PROJECTS↔DONE chỉ tính một lần).

NGUONG_O_CHAN_GB = 10.0  # = don_dep_mo_rong.NGUONG_O_GB
GIO_CHO_DONE_SAU_CONG_KHAI = 72.0  # = don_dep.NGAY_SAU_CONG_KHAI
_MB = 1024.0 ** 2
_GB = 1024.0 ** 3


def _tep_inode(thu_muc: str, da_thay: Optional[set] = None) -> int:
    """Byte của mọi tệp dưới `thu_muc`, mỗi inode tính một lần (cập nhật `da_thay`)."""
    da_thay = da_thay if da_thay is not None else set()
    tong = 0
    for cha, _thu, tep in os.walk(thu_muc):
        for t in tep:
            try:
                st = os.stat(os.path.join(cha, t))
            except OSError:
                continue
            khoa = (st.st_dev, st.st_ino) if st.st_ino else os.path.join(cha, t)
            if khoa in da_thay:
                continue
            da_thay.add(khoa)
            tong += st.st_size
    return tong


def tran_theo_o_dia(goc: str, *, con_trong_gb: Optional[float] = None,
                    so_kenh: Optional[int] = None) -> Dict[str, Any]:
    """Mỗi video cần bao nhiêu GB, ổ chịu được bao nhiêu video/ngày khi dọn đều.

    `tran_video_ngay` = None khi chưa đo được (chưa có lượt/gói thật trên đĩa)."""
    from .kenh import doc_kenh  # noqa: PLC0415

    ma_cac: List[str] = []
    for d in sorted(glob.glob(os.path.join(goc, "CHANNEL", "*", "kenh.yaml"))):
        try:
            if re.search(r"(?m)^tu_chay:\s*true", open(d, encoding="utf-8", errors="replace").read()):
                ma_cac.append(os.path.basename(os.path.dirname(d)))
        except OSError:
            continue
    n_kenh = int(so_kenh) if so_kenh is not None else len(ma_cac)
    giu_ds: List[int] = []
    done_ds: List[str] = []
    for ma in ma_cac:
        try:
            k = doc_kenh(goc, ma)
        except Exception:  # noqa: BLE001
            continue
        giu_ds.append(int(getattr(k, "giu_toi_da_luot", 0) or 0))
        if (k.thu_muc_done or "").strip() and os.path.isdir(k.thu_muc_done):
            done_ds.append(k.thu_muc_done)
    giu = max(giu_ds) if giu_ds else 3
    giu = giu if giu > 0 else 3

    # Đang dùng (PROJECTS + DONE, mỗi inode một lần)
    da_thay: set = set()
    dung = _tep_inode(os.path.join(goc, "PROJECTS", "AUTO"), da_thay)
    for d in done_ds:
        dung += _tep_inode(d, da_thay)

    # GB / lượt: lượt còn nguyên (có 8-video.mp4, chưa `da-don.json`)
    mau_luot: List[float] = []
    for v in glob.glob(os.path.join(goc, "PROJECTS", "AUTO", "*", "*", "8-video.mp4")):
        thu = os.path.dirname(v)
        if os.path.exists(os.path.join(thu, "da-don.json")):
            continue
        b = _tep_inode(thu)
        if b >= 50 * _MB:
            mau_luot.append(b / _GB)
    # GB / video DONE + số ngày nằm DONE (bàn giao → công khai + 3 ngày)
    so = _doc_json(os.path.join(goc, "vm", "logs", "so-video-id.json")) or {}
    mau_video: List[float] = []
    mau_tre: List[float] = []
    for d in done_ds:
        for v in glob.glob(os.path.join(d, "*", "*.mp4")):
            try:
                kt, mt = os.path.getsize(v), os.path.getmtime(v)
            except OSError:
                continue
            if kt < 10 * _MB:
                continue
            mau_video.append(kt / _GB)
            ma = os.path.basename(os.path.dirname(v))
            muc = so.get("{0}/{1}".format(ma.rsplit("-", 1)[0], ma)) if isinstance(so, dict) else None
            try:
                lich = datetime.strptime(str((muc or {}).get("lich") or ""), "%d/%m/%Y %H:%M")
                mau_tre.append(max(0.0, (lich.timestamp() - mt) / 86400.0))
            except ValueError:
                pass
    g_luot = statistics.median(mau_luot) if mau_luot else None
    g_video = statistics.median(mau_video) if mau_video else None
    tre = statistics.median(mau_tre) if mau_tre else 1.0
    ngay_done = tre + GIO_CHO_DONE_SAU_CONG_KHAI / 24.0 + 1.0 / 24.0
    if con_trong_gb is None:
        try:
            import shutil  # noqa: PLC0415

            con_trong_gb = shutil.disk_usage(goc)[2] / _GB
        except OSError:
            con_trong_gb = None
    ra: Dict[str, Any] = {"so_kenh": n_kenh, "giu_luot": giu, "con_trong_gb": _r(con_trong_gb),
                          "dang_dung_gb": round(dung / _GB, 2), "gb_moi_luot": _r(g_luot),
                          "gb_moi_video_done": _r(g_video), "ngay_nam_done": round(ngay_done, 2),
                          "nguong_chan_gb": NGUONG_O_CHAN_GB, "mau_luot": len(mau_luot),
                          "mau_video": len(mau_video), "tran_video_ngay": None}
    if g_luot is None and g_video is None or con_trong_gb is None or n_kenh <= 0:
        return ra
    g_video = g_video if g_video is not None else 0.4
    g_luot = g_luot if g_luot is not None else g_video * 2.5
    co_dinh = n_kenh * (giu + 1) * g_luot
    ngan_sach = con_trong_gb + dung / _GB - NGUONG_O_CHAN_GB
    gb_ngay = g_video * ngay_done  # GB·ngày mỗi video (phần tỉ lệ)
    trung = n_kenh * giu  # video nằm cả PROJECTS lẫn DONE (một inode)
    tran = max(0.0, (ngan_sach - co_dinh) / gb_ngay + trung / ngay_done) if ngan_sach > co_dinh \
        else 0.0
    ra.update({"co_dinh_projects_gb": round(co_dinh, 1), "ngan_sach_gb": round(ngan_sach, 1),
               "gb_ngay_moi_video": round(gb_ngay, 2),
               "gb_moi_video": round(g_luot + g_video, 2),
               "tran_video_ngay": round(tran, 1)})
    return ra


def _r(x: Optional[float]) -> Optional[float]:
    return round(float(x), 2) if x is not None else None


def cau_o_dia(o: Dict[str, Any]) -> str:
    if not o or o.get("tran_video_ngay") is None:
        return ""
    return ("Ổ đĩa: mỗi video ~{0} GB lúc dựng + {1} GB nằm DONE ~{2} ngày; cố định PROJECTS "
            "{3} GB ({4} kênh × {5}+1 lượt) → ổ chịu ≈ {6} video/ngày (chừa sàn {7:g} GB)").format(
                o.get("gb_moi_luot"), o.get("gb_moi_video_done"), o.get("ngay_nam_done"),
                o.get("co_dinh_projects_gb"), o.get("so_kenh"), o.get("giu_luot"),
                o.get("tran_video_ngay"), o.get("nguong_chan_gb"))


def cong_suat_hien_tai(goc: str, *, gio: float = 24.0,
                       bay_gio: Optional[float] = None) -> Dict[str, Any]:
    """Máy đang dùng X% khe nặng, Y làn API; còn dư ≈ Z video/ngày → đề xuất.

    Cửa sổ `gio` giờ gần nhất, nhưng KHÔNG lùi qua mốc thay đổi lớn (`moc_doi_gan_nhat`): có mốc
    trong cửa sổ thì cửa sổ bắt đầu từ mốc và bỏ lượt bắt đầu trước mốc (01/10/2026: đo 168 giờ
    gồm phần lớn thời gian trước khi khâu ảnh nhanh gấp 4 → trần 17,9 sai)."""
    den = bay_gio if bay_gio is not None else datetime.now().timestamp()
    tu = den - gio * 3600.0
    moc = moc_doi_gan_nhat(goc, den)
    moc = moc if moc is not None and moc > tu else None
    if moc is not None:
        tu = moc
        gio = max(0.25, (den - tu) / 3600.0)
    nk = doc_nhat_ky_khe(goc, tu, den, bo_truoc=moc)
    phut_nang = sum(nk["phut"]["nang"].values())
    phut_api = sum(nk["phut"]["api"].values())
    cai = _doc_json(os.path.join(goc, "workspace", "cai-dat.json")) or {}
    try:
        lan = max(1, min(4, int(cai.get("lan_api") or 2)))
    except (TypeError, ValueError):
        lan = 2
    dp = _doc_json(os.path.join(goc, "workspace", "khe", "dieu-phoi.json")) or {}
    video = _video_ban_giao(goc, tu, bo_truoc=moc, bo_khoang=nk["bo_khoang"])
    khe_cua_so = KHE_NGAY_PHUT * gio / 24.0
    pt_nang = round(100.0 * phut_nang / khe_cua_so, 1) if khe_cua_so else None
    lan_tb = round(phut_api / (gio * 60.0), 2)
    # phút khe nặng / video (đo) → trần video/ngày theo khe nặng
    du_mau = video >= 2
    so_kenh = len([d for d in glob.glob(os.path.join(goc, "CHANNEL", "*", "kenh.yaml"))
                   if re.search(r"(?m)^tu_chay:\s*true", open(d, encoding="utf-8", errors="replace").read())])
    nang_moi_video = (phut_nang / video) if du_mau and phut_nang > 0 else None
    nang_uoc = nang_moi_video or PHUT_NANG_MOI_VIDEO_MAC_DINH
    tran_nang = max(0.0, KHE_NGAY_PHUT - so_kenh * PHUT_QUET_MOI_KENH_NGAY) / nang_uoc
    # phút làn API / video (đo) → trần video/ngày theo làn
    api_moi_video = (phut_api / video) if du_mau and phut_api > 0 else None
    tran_api = ((lan * 24 * 60.0) / api_moi_video if api_moi_video
                else lan * VIDEO_MOI_LAN_NGAY_MAC_DINH)
    tran = min(tran_nang, tran_api)
    nut = "khe nặng" if tran_nang <= tran_api else "làn API"
    # 01/10/2026: trần theo Ổ ĐĨA (chỉ khi đo được lượt/gói thật) — tổng giám đốc
    # đọc `tran_video_ngay_o_dia` qua `giam_doc.tong.tran_may`.
    try:
        o_dia = tran_theo_o_dia(goc, so_kenh=so_kenh)
    except Exception:  # noqa: BLE001 — phần phụ
        o_dia = {}
    tran_o = o_dia.get("tran_video_ngay")
    if tran_o is not None and tran_o < tran:
        tran, nut = float(tran_o), "ổ đĩa"
    video_ngay = video * 24.0 / gio
    con_du = round(max(0.0, tran - video_ngay), 1)
    them_kenh = int(con_du // VIDEO_MOI_KENH_NGAY)
    if them_kenh >= 1:
        de_xuat = "có thể thêm {0} kênh (2 video/ngày) hoặc nâng nhịp kênh hiện có".format(them_kenh)
    elif con_du >= 1:
        de_xuat = "còn dư ~{0} video/ngày — có thể nâng nhịp một kênh".format(con_du)
    else:
        de_xuat = "đã gần hết công suất ({0} là nút thắt)".format(nut)
    if not du_mau:
        de_xuat += " (ƯỚC theo mô hình lộ trình — chưa đủ mẫu điều phối)"
    return {"luc": datetime.fromtimestamp(den).strftime("%Y-%m-%d %H:%M"), "cua_so_gio": round(gio, 1),
            "tu_moc_doi": datetime.fromtimestamp(moc).strftime("%Y-%m-%d %H:%M") if moc is not None else "",
            "du_mau": du_mau, "so_kenh_tu_chay": so_kenh,
            "phut_khe_nang": round(phut_nang, 1), "phan_tram_khe_nang": pt_nang,
            "phut_khe_nang_theo_viec": nk["phut"]["nang"], "gio_lan_api": round(phut_api / 60.0, 1),
            "lan_api": lan, "lan_api_trung_binh_dang_dung": lan_tb,
            "so_luot_dang_chay": dp.get("so_dang"), "video_ban_giao": video,
            "video_ngay_do": round(video_ngay, 1),
            "phut_nang_moi_video": round(nang_moi_video, 1) if nang_moi_video else None,
            "phut_api_moi_video": round(api_moi_video, 1) if api_moi_video else None,
            "tran_video_ngay_khe_nang": round(tran_nang, 1),
            "tran_video_ngay_lan_api": round(tran_api, 1), "nut_that": nut,
            "tran_video_ngay_o_dia": tran_o, "o_dia": o_dia,
            "con_du_video_ngay": con_du, "co_the_them_kenh": them_kenh, "de_xuat": de_xuat,
            "vuot_han_khe": nk["vuot_han"], "cho_khe_trung_vi_phut": nk["cho_trung_vi_phut"]}


def cau_mot_dong(cs: Dict[str, Any]) -> str:
    """Một dòng cho Bảng điều khiển (dòng Máy)."""
    if not cs:
        return ""
    cau = ("Công suất 24h: khe nặng {0}% · làn API TB {1}/{2} (đang chạy {6} lượt) · {3} video — "
           "còn dư ≈ {4} video/ngày → {5}").format(
               cs.get("phan_tram_khe_nang") if cs.get("phan_tram_khe_nang") is not None else "?",
               cs.get("lan_api_trung_binh_dang_dung"), cs.get("lan_api"),
               cs.get("video_ban_giao"), cs.get("con_du_video_ngay"), cs.get("de_xuat"),
               cs.get("so_luot_dang_chay") if cs.get("so_luot_dang_chay") is not None else "?")
    o = cs.get("o_dia") or {}
    if o.get("tran_video_ngay") is not None:
        cau += " · ổ: ~{0} GB/video, trần ≈ {1} video/ngày".format(
            o.get("gb_moi_video"), o.get("tran_video_ngay"))
    return cau


def ghi_hien_tai(goc: str, cs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Tính (nếu chưa có) + ghi `workspace/cong-suat/hien-tai.json` (nguyên tử)."""
    cs = cs if cs is not None else cong_suat_hien_tai(goc)
    cs = dict(cs, cau=cau_mot_dong(cs))
    thu_muc = os.path.join(goc, "workspace", "cong-suat")
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, "hien-tai.json")
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(cs, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)
    return cs


def doc_hien_tai(goc: str, tuoi_toi_da_giay: float = 3 * 3600.0) -> Dict[str, Any]:
    """Đọc bản đã ghi — cũ quá `tuoi_toi_da_giay` thì trả rỗng (không nói số cũ)."""
    duong = os.path.join(goc, "workspace", "cong-suat", "hien-tai.json")
    try:
        if datetime.now().timestamp() - os.path.getmtime(duong) > tuoi_toi_da_giay:
            return {}
    except OSError:
        return {}
    du = _doc_json(duong)
    return du if isinstance(du, dict) else {}


# ═══ CLI ═════════════════════════════════════════════════════════════════


def _main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    parser = argparse.ArgumentParser(
        prog="python -m core.cong_suat",
        description="Đo công suất thật của máy (phút/khâu, % khe, ước video/ngày). "
                    "Thuần đọc đĩa, không gọi mạng, không sửa gì.")
    parser.add_argument("--bao-cao", action="store_true",
                        help="Ghi workspace/cong-suat/<ngày>.{json,md} và in tóm tắt.")
    parser.add_argument("--tu", default=None, metavar="YYYY-MM-DD",
                        help="Chỉ tính dữ liệu từ ngày này trở đi.")
    parser.add_argument("--moc", default=MOC_MAC_DINH, metavar="YYYY-MM-DD",
                        help="Mốc ngày so sánh trước/sau (mặc định {0}).".format(
                            MOC_MAC_DINH))
    parser.add_argument("--kenh", type=int, default=None, metavar="N",
                        help="Số kênh dùng cho ước C.2 (mặc định tự đếm).")
    parser.add_argument("--lan", type=int, default=None, metavar="L",
                        help="Số làn song song lớp A (mặc định: lan_api trong cai-dat.json).")
    parser.add_argument("--hien-tai", action="store_true",
                        help="Công suất 24h qua từ nhật ký khe (điều phối) → "
                             "workspace/cong-suat/hien-tai.json + một dòng.")
    parser.add_argument("--o-dia", action="store_true",
                        help="In ước tính GB/video và trần video/ngày theo ổ đĩa (khi dọn đều).")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.o_dia:
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        o = tran_theo_o_dia(goc, so_kenh=args.kenh)
        print(json.dumps(o, ensure_ascii=False, indent=1))
        print(cau_o_dia(o) or "Chưa đo được (chưa có lượt/gói thật trên đĩa).")
        return 0

    if args.hien_tai:
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cs = ghi_hien_tai(goc)
        print(cs["cau"])
        return 0

    if not args.bao_cao:
        parser.print_help()
        return 0

    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kq = phan_tich(goc, tu=args.tu, moc=args.moc, so_kenh=args.kenh,
                   lan_song_song=args.lan)
    try:
        kq["dieu_phoi_24h"] = ghi_hien_tai(goc)
    except Exception:  # noqa: BLE001 — phần phụ, không chặn báo cáo chính
        kq["dieu_phoi_24h"] = {}
    duong = ghi_bao_cao(goc, kq)
    c2 = kq["cong_thuc_c2"]
    print("Đã ghi {0}".format(duong["json"]))
    print("Đã ghi {0}".format(duong["md"]))
    print("")
    print("Ước tối đa: {0} video/ngày cho {1} kênh (L={2} làn lớp A).".format(
        c2["video_ngay_toi_da"], c2["so_kenh_n"], c2["lan_song_song_lop_a"]))
    dt = kq.get("do_thuc_3_ngay") or {}
    if dt.get("so_luot"):
        print("Đo thật {0} ngày: {1} video → {2} video/ngày tổng; khâu nghẽn {3} ({4} phút).".format(
            dt["so_ngay"], dt["so_luot"], dt["tong_video_ngay"], dt["khau_nghen"], dt["khau_nghen_phut"]))
    print("Thực tế gần nhất: {0} video/ngày — máy còn dư {1} video/ngày.".format(
        c2["video_ngay_thuc_te_gan_nhat"], c2["may_con_du_video_ngay"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
