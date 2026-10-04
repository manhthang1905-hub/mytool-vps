"""NUÔI TRANG CHỦ cho kênh (03/10/2026) — CÔNG TẮC: chạy tới khi ĐẠT rồi tự TẮT.

Vì sao: trang chủ YouTube của tài khoản kênh mới đề xuất lung tung, mà tool lấy trang
chủ để tìm đối thủ + xu hướng. Tệp này cho Chrome ĐÃ ĐĂNG NHẬP của kênh xem video đối
thủ cùng ngách như người thật (tắt tiếng, xem 35–85% thời lượng, thỉnh thoảng tua), bấm
"Không quan tâm" vài video lạc đề, rồi ĐO trang chủ (~30 ô) bằng LLM theo NGHĨA.

ĐẠT = % chủ đề (dung_ngach + dung_chu_de) > 90%, CHỈ CẦN 1 lần đo. % ngách vẫn đo và
ghi để xem, không là điều kiện. Đạt thì tự ghi `nuoi_trang_chu: false` vào kenh.yaml
của kênh (chủ muốn nuôi lại thì tự bật `true`) và ghi sổ/báo cáo. Không có chế độ duy trì.

Song song: mỗi kênh `nuoi_trang_chu: true` chạy các phiên liên tiếp (<= 15 video/phiên,
nghỉ 20–40 phút giữa các phiên, <= 40 video/ngày/kênh); tối đa 4 Chrome nuôi cùng lúc,
chỉ mở thêm khi RAM trống >= 4 GB. Phiên nuôi KHÔNG giữ khe máy chung; dùng khoá RIÊNG
THEO KÊNH (`<kênh>.khoa`) để không bao giờ có 2 tiến trình cùng mở Chrome của một kênh.

NHƯỜNG VIỆC ĐĂNG (cách (a), chọn vì mọi việc của agent đều đi qua `giu_khoa_may_chung(
kenh=...)`): agent thấy khoá nuôi của kênh X thì ghi cờ `<X>.dung`; phiên nuôi thấy cờ là
đóng Chrome ngay (<= 2 phút) rồi agent mới làm việc (tải lên, ghim, dời lịch, sửa tiêu
đề, MHKT, quét). Phiên nuôi còn tự không mở khi kênh có việc đăng chờ.

Khung cấm 02:00–07:00 (quét Studio, sản xuất, tải lên). Khe "nang" của máy (dựng/phụ
đề...) bận thì không mở phiên mới và phiên đang chạy dừng ở video kế. Van IPv4 mở thì hoãn.
CAPTCHA/đăng xuất thì DỪNG, ghi `can_nguoi`, không thử lại. KHÔNG thích/đăng ký/bình
luận/chia sẻ.

Chạy: `python vm/nuoi_trang_chu.py --kenh TL5-T7 [--so-video 15] [--thu]`
(`--thu` = không mở Chrome, chỉ chọn video + kiểm giới hạn + in kế hoạch).
Agent gọi mỗi ~10 phút (`agent.chay_nuoi_trang_chu`), mỗi kênh một tiến trình con.

Ghi sổ: `vm/logs/nuoi-trang-chu/<kênh>.json` + `.md` + `.log`.
Mã thoát: 0 xong · 10 hoãn · 20 cần người · 30 không cần chạy (đạt/tắt) · 1 lỗi.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta

try:
    from vm import canh_tien_trien
except ImportError:  # chạy trực tiếp `python vm/nuoi_trang_chu.py` (vm/ nằm trong sys.path)
    import canh_tien_trien

GOC = os.path.dirname(os.path.abspath(__file__))            # vm/
GOC_TOOL = os.path.dirname(GOC)                             # MyTool/
THU_MUC_SO = os.path.join(GOC, "logs", "nuoi-trang-chu")

# ── Hằng số luật (đổi ở đây, test canh) ─────────────────────────────────────
TOI_DA_VIDEO_PHIEN = 15
TOI_DA_VIDEO_NGAY = 40
NGHI_PHIEN_PHUT = (20, 40)
NGHI_NGAT_PHUT = 5                       # phiên bị ngắt (nhường đăng/khe nang) thì nghỉ ngắn hơn
TOI_DA_CHROME_NUOI = 4
TOI_DA_CHROME_KHI_DUNG = 2               # đang có việc dựng/sản xuất giữ khe nang thì chỉ ≤ 2 Chrome nuôi
CPU_TOI_DA_PCT = 75.0                    # CPU tổng ≥ ngần này thì nhường
#: Việc của agent ĐĂNG (khe nang) — nuôi trang chủ nhường tuyệt đối khi những việc này đang giữ.
VIEC_DANG = ("tai_len", "phien", "viec", "binh_luan", "bu_mhkt", "sua_video")
RAM_TOI_THIEU_GB = 4.0
CHU_KY_LICH_AGENT_GIAY = 10 * 60
NGAN_SACH_PHIEN_PHUT = 90                # quá ngần này thì thôi không mở video mới
NHIN_TRUOC_PHIEN_PHUT = 25               # phiên kênh đăng sắp tới trong ngần này => nhường
CHO_NHUONG_GIAY = 120
TOI_DA_KHONG_QUAN_TAM = 30          # 04/10: dọn mạnh — tối đa mỗi phiên (trước 5)
KHONG_QUAN_TAM_MOI_LAN = 4          # tối đa mỗi lần về trang chủ (đầu phiên gấp đôi)
TUOI_VIDEO_TOI_DA_NGAY = 60
#: CHỈ xem video THẮNG (03/10): view tối thiểu + phải ≥ HE_SO_NO × trung vị view của chính kênh đó.
VIEW_THANG_TOI_THIEU = 30000
HE_SO_NO = 2.0
TI_LE_NGACH = 0.7
DAT_PCT_CHU_DE = 90.0                    # đạt khi % chủ đề > ngưỡng này, 1 lần đo
TOI_THIEU_O_DO = 18                      # ít hơn ngần này ô video thì phép đo không tính
SO_O_DO = 30
XEM_TU, XEM_DEN = 0.35, 0.85
XEM_SAN_GIAY, XEM_TRAN_GIAY = 2 * 60, 12 * 60
XAC_SUAT_TUA = 0.30
#: Khung cấm (phút trong ngày): quét Studio 02:00, sản xuất 05:00, tải lên → cấm 02:00–07:00.
KHUNG_CAM = ((2 * 60, 7 * 60),)
MA_HOAN, MA_CAN_NGUOI, MA_KHONG_CAN = 10, 20, 30

NHAN_HOP_LE = ("dung_ngach", "dung_chu_de", "lac_de")
CHU_KHONG_QUAN_TAM = ("^(興味なし|興味がない|Not interested|No me interesa|Không quan tâm|"
                      "Pas intéressé|Kein Interesse|Não tenho interesse|관심 없음|不感兴趣|对此不感兴趣)$")
KENH_MOI_THU_TU = ("TL4-T7-K2", "TL5-T7", "TL6-T7", "TL6-T7-K2")   # để cấp cổng DevTools riêng


class CanNguoi(Exception):
    """Gặp CAPTCHA / đăng xuất / trang đồng ý — dừng ngay, không thử lại."""


class Hoan(Exception):
    """Chưa chạy được lúc này (không phải lỗi)."""


# ═══════════════════════════ HÀM THUẦN (có test) ═════════════════════════════
def _phut(luc: float) -> int:
    t = time.localtime(luc)
    return t.tm_hour * 60 + t.tm_min


def khung_cam(luc: float, du_kien_phut: float = 0.0) -> str:
    """Lý do bị cấm (chuỗi), hoặc "" nếu được chạy. Cấm cả khi phiên DỰ KIẾN kéo
    dài `du_kien_phut` sẽ chạm khung cấm."""
    bd = _phut(luc)
    kt = bd + max(0.0, du_kien_phut)
    for ngay in (0, 1440):
        for a, b in KHUNG_CAM:
            a, b = a + ngay, b + ngay
            if (a <= bd < b) or (bd < a <= kt):
                return "khung cấm {0:02d}:{1:02d}–{2:02d}:{3:02d} ({4})".format(
                    (a % 1440) // 60, a % 60, (b % 1440) // 60 or 24, b % 60,
                    "QUÉT NGÀY" if (a % 1440) < 240 else "giờ đăng/sản xuất")
    return ""


def thoi_luong_xem(dai_giay: float, rng: random.Random) -> int:
    """Số giây xem: 35–85% thời lượng, kẹp 2–12 phút (video ngắn hơn 2 phút thì xem ~90%)."""
    dai = max(1.0, float(dai_giay))
    x = dai * rng.uniform(XEM_TU, XEM_DEN)
    x = max(XEM_SAN_GIAY, min(XEM_TRAN_GIAY, x))
    return int(max(1.0, min(x, dai * 0.9 if dai <= XEM_SAN_GIAY else dai - 5)))


def ke_hoach_xem(dai_giay: float, rng: random.Random) -> dict:
    """{xem_giay, tua}: tua = None hoặc {sau_giay, nhay_giay} (một lần, ~30%)."""
    xem = thoi_luong_xem(dai_giay, rng)
    tua = None
    if xem >= 90 and rng.random() < XAC_SUAT_TUA:
        tua = {"sau_giay": int(rng.uniform(0.2, 0.6) * xem), "nhay_giay": int(rng.uniform(20, 90))}
    return {"xem_giay": xem, "tua": tua}


def chuan_ten(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s or ""))).lower()


def ma_video(link: str) -> str:
    m = re.search(r"(?:[?&]v=|youtu\.be/|/shorts/)([\w-]{11})", str(link or ""))
    return m.group(1) if m else ""


def _giay(chu: str) -> int:
    try:
        p = [int(x) for x in str(chu).strip().split(":")]
    except ValueError:
        return 0
    return sum(v * 60 ** i for i, v in enumerate(reversed(p))) if 1 <= len(p) <= 3 else 0


def chon_video(ung_vien: list, da_xem, cam_id, cam_ten, so_video: int, bay_gio: date,
               rng: random.Random, ti_le_ngach: float = TI_LE_NGACH) -> list:
    """Chọn `so_video` video: ~70% `ngach=True`, ~30% còn lại (chủ đề rộng).

    Loại: đã xem, video/kênh của MÌNH, quá `TUOI_VIDEO_TOI_DA_NGAY`, view 0, dài < 2 phút.
    Ưu tiên mới + nhiều view (lấy mẫu có trọng số, không lặp). Thiếu nhóm này thì bù
    nhóm kia. Mỗi ứng viên: {id, tieu_de, kenh, view, ngay(date), dai(giây), ngach(bool)}."""
    # 03/10/2026 (chủ dự án): "cho xem video yếu thì YouTube lại học đề xuất video yếu". CHỈ xem VIDEO
    # THẮNG: view ≥ VIEW_THANG_TOI_THIEU VÀ ≥ HE_SO_NO × trung vị view của chính kênh đó (video nổ của
    # kênh, không phải video thường); xếp theo view/ngày, lấy mẫu trong nhóm mạnh nhất. Thiếu thì xem ÍT
    # hơn — KHÔNG bù bằng video yếu.
    da_xem, cam_id = set(da_xem or ()), set(cam_id or ())
    cam_ten = {chuan_ten(x) for x in (cam_ten or ()) if x}
    theo_kenh: dict = {}
    for v in ung_vien:
        theo_kenh.setdefault(chuan_ten(v.get("kenh")), []).append(int(v.get("view") or 0))
    # trung vị chỉ có nghĩa khi kênh có ≥ 5 video trong kho ứng viên; ít hơn thì chỉ xét ngưỡng view
    tv_kenh = {k: sorted(x)[len(x) // 2] for k, x in theo_kenh.items() if len(x) >= 5}
    nguoi, da_lay = [], set()
    for v in ung_vien:
        vid = v.get("id")
        if not vid or vid in da_xem or vid in cam_id or vid in da_lay:
            continue
        ten = chuan_ten(v.get("kenh"))
        if ten in cam_ten:
            continue
        tuoi = (bay_gio - v["ngay"]).days if v.get("ngay") else 9999
        view = int(v.get("view") or 0)
        if tuoi > TUOI_VIDEO_TOI_DA_NGAY or view < VIEW_THANG_TOI_THIEU:
            continue
        if view < HE_SO_NO * tv_kenh.get(ten, 0):
            continue
        if v.get("dai") and v["dai"] < 120:
            continue
        da_lay.add(vid)
        nguoi.append((view / max(1, tuoi), v))
    nguoi.sort(key=lambda x: -x[0])
    def _manh(ds: list) -> list:   # xáo trong top 2×so_video mạnh nhất cho đa dạng, bỏ phần đuôi yếu
        top = ds[:so_video * 2]
        rng.shuffle(top)
        return top
    ngach = _manh([v for _, v in nguoi if v.get("ngach")])
    rong = _manh([v for _, v in nguoi if not v.get("ngach")])
    can_ngach = min(len(ngach), int(round(so_video * ti_le_ngach)))
    can_rong = min(len(rong), so_video - can_ngach)
    can_ngach = min(len(ngach), so_video - can_rong)      # bù nếu nhóm rộng thiếu
    ra = ngach[:can_ngach] + rong[:can_rong]
    rng.shuffle(ra)
    return ra


def phan_tram(nhan: list) -> dict:
    """{n, pct_chu_de, pct_ngach, dem}: chủ đề = dung_ngach + dung_chu_de."""
    dem = {k: 0 for k in NHAN_HOP_LE}
    for x in nhan:
        if x in dem:
            dem[x] += 1
    n = sum(dem.values())
    if not n:
        return {"n": 0, "pct_chu_de": 0.0, "pct_ngach": 0.0, "dem": dem}
    return {"n": n, "pct_chu_de": round(100.0 * (dem["dung_ngach"] + dem["dung_chu_de"]) / n, 1),
            "pct_ngach": round(100.0 * dem["dung_ngach"] / n, 1), "dem": dem}


def dat_tieu_chi(pct_chu_de: float, pct_ngach: float, n: int) -> bool:
    """Đạt: đủ ô đo và % chủ đề > 90%. % ngách chỉ để xem (không là điều kiện)."""
    return n >= TOI_THIEU_O_DO and pct_chu_de > DAT_PCT_CHU_DE


def ghi_lan_do(so: dict, ket: dict, luc: str) -> dict:
    """Thêm một lần đo vào sổ; đạt (1 lần) thì `trang_thai = "dat"`."""
    muc = {"luc": luc, "n": ket["n"], "pct_chu_de": ket["pct_chu_de"], "pct_ngach": ket["pct_ngach"],
           "dem": ket["dem"], "dat": dat_tieu_chi(ket["pct_chu_de"], ket["pct_ngach"], ket["n"]),
           "vi_du_lac_de": list(ket.get("vi_du_lac_de") or [])[:6]}
    so.setdefault("lan_do", []).append(muc)
    if muc["dat"] and so.get("trang_thai", "dang_nuoi") == "dang_nuoi":
        so["trang_thai"], so["dat_luc"] = "dat", luc
        so["ly_do"] = "đạt: chủ đề {0}% > {1:.0f}% ({2}) — đã tắt nuoi_trang_chu".format(
            muc["pct_chu_de"], DAT_PCT_CHU_DE, luc)
    return so


def so_moi(kenh: str) -> dict:
    return {"kenh": kenh, "trang_thai": "dang_nuoi", "ly_do": "", "bat_dau": "", "phien": [],
            "lan_do": [], "da_xem": {}, "cache": {}}


def video_hom_nay(so: dict, ngay: str) -> int:
    return sum(int(p.get("so_video") or 0) for p in so.get("phien", []) if p.get("ngay") == ngay)


def quyet_dinh(so: dict, luc: float, du_kien_phut: float = 0.0, bo_qua_khung: bool = False) -> tuple:
    """(số video được xem phiên này, lý do bỏ qua). 0 + lý do = không chạy lúc này. Thuần."""
    tt = so.get("trang_thai", "dang_nuoi")
    if tt == "can_nguoi":
        return 0, "đang chờ người xử lý ({0})".format(so.get("ly_do", ""))
    if tt == "dat":
        return 0, "đã đạt — không nuôi nữa"
    if not bo_qua_khung:
        k = khung_cam(luc, du_kien_phut)
        if k:
            return 0, k
    con = TOI_DA_VIDEO_NGAY - video_hom_nay(so, datetime.fromtimestamp(luc).date().isoformat())
    if con <= 0:
        return 0, "đã đủ {0} video hôm nay".format(TOI_DA_VIDEO_NGAY)
    nghi = float(so.get("nghi_den_luc") or 0)
    if luc < nghi:
        return 0, "nghỉ giữa phiên, còn {0} phút".format(int((nghi - luc) // 60) + 1)
    return min(TOI_DA_VIDEO_PHIEN, con), ""


def kiem_gioi_han(so: dict, luc: float, du_kien_phut: float = 0.0, bo_qua_khung: bool = False) -> str:
    """Lý do KHÔNG được chạy, hoặc "" nếu được (bọc `quyet_dinh`)."""
    so_v, ly = quyet_dinh(so, luc, du_kien_phut, bo_qua_khung)
    return "" if so_v else ly


def duoc_mo_them(so_chrome_dang_nuoi: int, ram_trong_gb, dang_dung: bool = False) -> str:
    """Lý do KHÔNG được mở thêm Chrome nuôi, hoặc "": tối đa 4 Chrome (2 khi máy đang dựng) và RAM trống >= 4 GB."""
    tran = TOI_DA_CHROME_KHI_DUNG if dang_dung else TOI_DA_CHROME_NUOI
    if so_chrome_dang_nuoi >= tran:
        return "đã có {0} Chrome nuôi (tối đa {1}{2})".format(
            so_chrome_dang_nuoi, tran, " khi máy đang dựng" if dang_dung else "")
    if ram_trong_gb is None or ram_trong_gb < RAM_TOI_THIEU_GB:
        return "RAM trống {0} GB < {1:.0f} GB".format(
            "?" if ram_trong_gb is None else "{0:.1f}".format(ram_trong_gb), RAM_TOI_THIEU_GB)
    return ""


def nghi_giua_phien(rng: random.Random, bi_ngat: bool = False) -> float:
    """Số giây nghỉ tới phiên kế: 20–40 phút (bị ngắt giữa chừng thì chỉ vài phút)."""
    return NGHI_NGAT_PHUT * 60.0 if bi_ngat else rng.uniform(*NGHI_PHIEN_PHUT) * 60.0


# ═══════════════════════════ DỮ LIỆU KÊNH / ĐỐI THỦ ══════════════════════════
def _doc_csv(duong: str) -> list:
    try:
        with open(duong, "r", encoding="utf-8-sig", newline="") as tep:
            return list(csv.DictReader(tep))
    except (OSError, csv.Error):
        return []


def _yaml_chu(noi_dung: str, khoa: str) -> str:
    m = re.search(r"(?m)^{0}:\s*(.*?)\s*$".format(re.escape(khoa)), noi_dung)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def duong_kenh_yaml(kenh: str, goc: str = GOC_TOOL) -> str:
    """`CHANNEL/<K>/kenh.yaml` nếu đã có, không thì bản nháp `workspace/chuan-bi-<K>/...`."""
    for d in (os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"),
              os.path.join(goc, "workspace", "chuan-bi-" + kenh, "CHANNEL", kenh, "kenh.yaml")):
        if os.path.isfile(d):
            return d
    return ""


def doc_kenh_yaml(kenh: str, goc: str = GOC_TOOL) -> dict:
    d = duong_kenh_yaml(kenh, goc)
    if not d:
        return {}
    with open(d, "r", encoding="utf-8") as tep:
        nd = tep.read()
    return {"duong": d, "ten": _yaml_chu(nd, "ten"), "tep": _yaml_chu(nd, "tep"),
            "nhom": _yaml_chu(nd, "nhom"), "luat_chon": _yaml_chu(nd, "luat_chon"),
            "bat": _yaml_chu(nd, "nuoi_trang_chu").lower() == "true"}


def cac_kenh_bat(goc: str = GOC_TOOL) -> list:
    """Mọi kênh có `nuoi_trang_chu: true` (CHANNEL/<K> thắng bản nháp)."""
    ra = []
    for mau in (os.path.join(goc, "CHANNEL", "*", "kenh.yaml"),
                os.path.join(goc, "workspace", "chuan-bi-*", "CHANNEL", "*", "kenh.yaml")):
        import glob
        for d in sorted(glob.glob(mau)):
            k = os.path.basename(os.path.dirname(d))
            if k.startswith("_") or k in ra:
                continue
            try:
                if doc_kenh_yaml(k, goc).get("bat"):
                    ra.append(k)
            except OSError:
                pass
    return ra


def ten_kenh_cua_minh(goc: str = GOC_TOOL) -> set:
    """Tên kênh của MÌNH: phần trước ' — ' của `ten:` trong mọi kenh.yaml (bỏ tên tạm)."""
    import glob
    ra = set()
    for mau in (os.path.join(goc, "CHANNEL", "*", "kenh.yaml"),
                os.path.join(goc, "workspace", "chuan-bi-*", "CHANNEL", "*", "kenh.yaml")):
        for d in glob.glob(mau):
            try:
                with open(d, "r", encoding="utf-8") as tep:
                    ten = _yaml_chu(tep.read(), "ten")
            except OSError:
                continue
            ten = ten.split(" — ")[0].strip()
            if ten and not ten.startswith("("):
                ra.add(ten)
    return ra


def id_video_cua_minh(goc: str = GOC_TOOL) -> set:
    """Mọi videoId đã đăng của các kênh mình (sổ videoId + bảng nhóm)."""
    ra = set()
    try:
        with open(os.path.join(GOC, "logs", "so-video-id.json"), "r", encoding="utf-8") as tep:
            for v in (json.load(tep) or {}).values():
                if isinstance(v, dict):
                    ra.add(str(v.get("video_id") or ""))
                    ra.update(str(x) for x in (v.get("id_cu") or []))
    except (OSError, ValueError):
        pass
    import glob
    for d in glob.glob(os.path.join(goc, "CHANNEL", "_NHOM", "*", "bang-nhom.csv")):
        ra.update(r.get("Mã video", "") for r in _doc_csv(d))
    ra.discard("")
    return ra


def _thu_muc_nc(kenh: str, goc: str = GOC_TOOL) -> str:
    for d in (os.path.join(goc, "CHANNEL", kenh, "nghien-cuu"),
              os.path.join(goc, "workspace", "chuan-bi-" + kenh, "CHANNEL", kenh, "nghien-cuu")):
        if os.path.isdir(d):
            return d
    return ""


def doi_thu_hop_le(kenh: str, goc: str = GOC_TOOL) -> set:
    """Tên đối thủ HỢP LỆ (đang theo dõi). Sổ của kênh thắng; kênh chưa có trong sổ
    của nó thì nhận nếu sổ kênh khác đang `theo dõi`."""
    import glob
    ok_k, xau_k = set(), set()
    for r in _doc_csv(os.path.join(_thu_muc_nc(kenh, goc) or "-", "doi-thu.csv")):
        (ok_k if (r.get("Trạng thái") or "").strip() in ("", "theo dõi") else xau_k).add(chuan_ten(r.get("Kênh")))
    ok_all = set()
    for mau in (os.path.join(goc, "CHANNEL", "*", "nghien-cuu", "doi-thu.csv"),
                os.path.join(goc, "workspace", "chuan-bi-*", "CHANNEL", "*", "nghien-cuu", "doi-thu.csv")):
        for d in glob.glob(mau):
            for r in _doc_csv(d):
                if (r.get("Trạng thái") or "").strip() in ("", "theo dõi"):
                    ok_all.add(chuan_ten(r.get("Kênh")))
    ok_k.discard("")
    return ok_k | (ok_all - xau_k - {""})


def doc_ung_vien(kenh: str, hom_nay: date, goc: str = GOC_TOOL) -> list:
    """Ứng viên từ kho đối thủ: kho khởi động + content của kênh (= NGÁCH) và content
    của các kênh khác trong nhóm (NGÁCH nếu cùng tuyến `tep`, còn lại = chủ đề rộng,
    bỏ tuyến 'khac'). Chỉ video của đối thủ hợp lệ, <= 60 ngày."""
    import glob
    cfg = doc_kenh_yaml(kenh, goc)
    tep = cfg.get("tep", "")
    hop_le = doi_thu_hop_le(kenh, goc)
    ra = {}

    def them(r, ngach):
        vid = ma_video(r.get("Link video"))
        try:
            ngay = date.fromisoformat((r.get("Ngày đăng") or "")[:10])
        except ValueError:
            return
        if not vid or (hom_nay - ngay).days > TUOI_VIDEO_TOI_DA_NGAY or chuan_ten(r.get("Kênh")) not in hop_le:
            return
        try:
            view = int(float(r.get("View") or 0))
        except ValueError:
            view = 0
        cu = ra.get(vid)
        if cu and cu["ngach"]:
            return
        ra[vid] = {"id": vid, "tieu_de": r.get("Tiêu đề video") or "", "kenh": r.get("Kênh") or "",
                   "view": view, "ngay": ngay, "dai": _giay(r.get("Thời lượng")), "ngach": bool(ngach)}

    nc = _thu_muc_nc(kenh, goc)
    for ten in ("kho-khoi-dong.csv", "content.csv"):
        for r in _doc_csv(os.path.join(nc or "-", ten)):
            them(r, True)
    for mau in (os.path.join(goc, "CHANNEL", "*", "nghien-cuu", "content.csv"),
                os.path.join(goc, "workspace", "chuan-bi-*", "CHANNEL", "*", "nghien-cuu", "content.csv")):
        for d in glob.glob(mau):
            if os.path.basename(os.path.dirname(os.path.dirname(d))) == kenh:
                continue
            for r in _doc_csv(d):
                tuyen = (r.get("Tuyến / Kênh") or "").strip()
                if tuyen == "khac":
                    continue
                them(r, bool(tep) and tuyen == tep)
    return list(ra.values())


def mo_ta_ngach(kenh: str, goc: str = GOC_TOOL) -> str:
    cfg = doc_kenh_yaml(kenh, goc)
    ten = cfg.get("ten", "")
    mo = ten.split(" — ", 1)[1] if " — " in ten else ten
    for r in _doc_csv(os.path.join(_thu_muc_nc(kenh, goc) or "-", "tuyen.csv")):
        if (r.get("Mã") or "").strip() == cfg.get("tep"):
            mo += " | tuyến: {0}. {1}. Từ khoá: {2}".format(r.get("Tên tuyến", ""), (r.get("Mô tả") or "")[:300],
                                                            (r.get("Từ khoá nhận biết") or "")[:200])
            break
    return mo or cfg.get("luat_chon", "")[:400]


# ═══════════════════════════ SỔ ═════════════════════════════════════════════
def duong_so(kenh: str) -> str:
    return os.path.join(THU_MUC_SO, kenh + ".json")


def doc_so(kenh: str) -> dict:
    try:
        with open(duong_so(kenh), "r", encoding="utf-8") as tep:
            so = json.load(tep)
        base = so_moi(kenh)
        base.update(so)
        return base
    except (OSError, ValueError):
        return so_moi(kenh)


def luu_so(so: dict) -> None:
    os.makedirs(THU_MUC_SO, exist_ok=True)
    cache = so.get("cache") or {}
    if len(cache) > 1500:
        so["cache"] = dict(list(cache.items())[-1000:])
    so["phien"] = so.get("phien", [])[-60:]
    duong = duong_so(so["kenh"])
    with open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(so, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)
    ghi_bao_cao(so)


def ghi_bao_cao(so: dict) -> None:
    """`<kênh>.md` cho người đọc."""
    d = [["# Nuôi trang chủ — {0}".format(so["kenh"]), "",
          "- Trạng thái: **{0}** {1}".format(so.get("trang_thai"), ("— " + so["ly_do"]) if so.get("ly_do") else ""),
          "- Bắt đầu: {0} · số phiên: {1} · video đã xem: {2}".format(
              so.get("bat_dau") or "-", len(so.get("phien", [])), len(so.get("da_xem", {}))),
          "- Tiêu chí đạt: % chủ đề > {0:.0f}% (1 lần đo); % ngách chỉ để xem".format(DAT_PCT_CHU_DE), "", "## Các lần đo", "",
          "| Lúc | Số ô | % chủ đề | % ngách | Đạt |", "|---|---|---|---|---|"]]
    for x in so.get("lan_do", []):
        d[0].append("| {0} | {1} | {2} | {3} | {4} |".format(
            x["luc"], x["n"], x["pct_chu_de"], x["pct_ngach"], "có" if x["dat"] else "chưa"))
    if so.get("lan_do") and so["lan_do"][-1].get("vi_du_lac_de"):
        d[0] += ["", "Ví dụ ô lạc đề ở lần đo cuối:"] + ["- " + t for t in so["lan_do"][-1]["vi_du_lac_de"]]
    d[0] += ["", "## Các phiên", ""]
    for p in so.get("phien", [])[-15:]:
        d[0].append("- {0} {1}: {2} video, {3} phút xem, không quan tâm {4}, kết quả: {5}".format(
            p.get("ngay"), p.get("bat_dau", ""), p.get("so_video", 0), int(p.get("giay_xem", 0)) // 60,
            p.get("khong_quan_tam", 0), p.get("ket_qua", "")))
    try:
        os.makedirs(THU_MUC_SO, exist_ok=True)
        with open(os.path.join(THU_MUC_SO, so["kenh"] + ".md"), "w", encoding="utf-8") as tep:
            tep.write("\n".join(d[0]) + "\n")
    except OSError:
        pass


# ═══════════════════════════ LỊCH CHO AGENT ═════════════════════════════════
# ═══════════════════════════ KHOÁ THEO KÊNH, RAM, KHE NANG, CÔNG TẮC ═════════
def pid_con_song(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        ra = subprocess.run(["tasklist", "/FI", "PID eq {0}".format(pid), "/NH"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=8,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return ra.returncode != 0 or str(pid) in (ra.stdout or "")
    except Exception:  # noqa: BLE001 — không chắc thì coi như còn sống (không giẫm lên)
        return True


def duong_khoa(ten: str, thu_muc: str = None) -> str:
    return os.path.join(thu_muc or THU_MUC_SO, ten + ".khoa")


def chu_khoa(ten: str, thu_muc: str = None) -> int:
    """PID đang giữ khoá `ten` (0 = không ai; khoá của tiến trình chết bị dọn)."""
    d = duong_khoa(ten, thu_muc)
    try:
        with open(d, "r", encoding="utf-8") as tep:
            pid = int((json.load(tep) or {}).get("pid") or 0)
    except (OSError, ValueError, TypeError):
        return 0
    if pid and pid_con_song(pid):
        return pid
    try:
        os.remove(d)
    except OSError:
        pass
    return 0


def giu_khoa(ten: str, thu_muc: str = None) -> bool:
    """Giành khoá `ten` (O_EXCL). Khoá RIÊNG THEO KÊNH: không bao giờ 2 tiến trình cùng mở Chrome một kênh."""
    d = duong_khoa(ten, thu_muc)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(d, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if chu_khoa(ten, thu_muc):
                return False
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "luc": time.time()}, tep)
        return True
    return False


def nha_khoa(ten: str, thu_muc: str = None) -> None:
    if chu_khoa(ten, thu_muc) == os.getpid():
        try:
            os.remove(duong_khoa(ten, thu_muc))
        except OSError:
            pass


def cac_kenh_dang_nuoi(thu_muc: str = None) -> list:
    """Kênh có khoá nuôi còn sống (đếm Chrome nuôi)."""
    try:
        ten = [f[:-5] for f in os.listdir(thu_muc or THU_MUC_SO) if f.endswith(".khoa") and not f.startswith("_")]
    except OSError:
        return []
    return [k for k in ten if chu_khoa(k, thu_muc)]


def co_dung(kenh: str, thu_muc: str = None) -> bool:
    """Agent đã ghi cờ `<kênh>.dung` (có việc đăng cần Chrome kênh) — phải đóng Chrome ngay."""
    return os.path.isfile(os.path.join(thu_muc or THU_MUC_SO, kenh + ".dung"))


def xoa_co_dung(kenh: str, thu_muc: str = None) -> None:
    try:
        os.remove(os.path.join(thu_muc or THU_MUC_SO, kenh + ".dung"))
    except OSError:
        pass


def ram_trong_gb():
    """RAM trống (GB) qua GlobalMemoryStatusEx; None nếu không đọc được."""
    try:
        import ctypes

        class _M(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = _M()
        m.dwLength = ctypes.sizeof(_M)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / float(1 << 30)
    except Exception:  # noqa: BLE001
        return None


def cpu_tong_pct(giay: float = 3.0):
    """CPU tổng (%) trung bình `giay` giây qua psutil; không có thì GetSystemTimes (ctypes). None nếu không đo được."""
    try:
        import psutil                                          # noqa: PLC0415
        return float(psutil.cpu_percent(interval=giay))
    except Exception:  # noqa: BLE001
        pass
    try:
        import ctypes                                          # noqa: PLC0415
        from ctypes import wintypes                            # noqa: PLC0415

        def _lay():
            r = [wintypes.FILETIME() for _ in range(3)]
            ctypes.windll.kernel32.GetSystemTimes(*[ctypes.byref(x) for x in r])
            return [(x.dwHighDateTime << 32) | x.dwLowDateTime for x in r]   # rảnh, nhân, người dùng
        d1 = _lay()
        time.sleep(giay)
        d2 = _lay()
        d = [b - a for a, b in zip(d1, d2)]
        tong = d[1] + d[2]                                     # thời gian nhân đã gồm cả rảnh
        return 100.0 * (tong - d[0]) / tong if tong > 0 else None
    except Exception:  # noqa: BLE001
        return None


def khe_nang_viec(goc_tool: str = GOC_TOOL) -> str:
    """Tên việc đang giữ khe "nang" của máy ("" nếu rảnh; "?" nếu giữ mà không rõ việc)."""
    try:
        if goc_tool not in sys.path:
            sys.path.insert(0, goc_tool)
        from core import khe                                  # noqa: PLC0415
        du = khe.trang_thai(goc_tool).get("nang")
        return "" if du is None else str(du.get("viec") or "?")
    except Exception:  # noqa: BLE001
        return ""


def khe_nang_ban(goc_tool: str = GOC_TOOL) -> bool:
    """Máy quá bận để nuôi: việc ĐĂNG đang giữ khe nang (nhường tuyệt đối) hoặc CPU tổng >= 75%.
    Khe nang bận vì dựng/sản xuất mà CPU còn dư thì vẫn nuôi (tối đa 2 Chrome — xem `duoc_mo_them`)."""
    if khe_nang_viec(goc_tool) in VIEC_DANG:
        return True
    cpu = cpu_tong_pct()
    return cpu is not None and cpu >= CPU_TOI_DA_PCT


def tat_nuoi(kenh: str, goc: str = GOC_TOOL) -> str:
    """Ghi `nuoi_trang_chu: false` vào kenh.yaml (CHANNEL/<K>, chưa có thì bản nháp). Trả đường tệp, "" nếu không ghi được."""
    d = duong_kenh_yaml(kenh, goc)
    if not d:
        return ""
    with open(d, "rb") as tep:
        b = tep.read()
    moi = re.sub(rb"(?m)^nuoi_trang_chu:[ \t]*true[ \t]*(?=\r?$)", b"nuoi_trang_chu: false", b)
    if moi == b:
        return d if b"nuoi_trang_chu: false" in b else ""
    with open(d + ".tam", "wb") as tep:
        tep.write(moi)
    os.replace(d + ".tam", d)
    return d


# ═══════════════════════════ LỊCH CHO AGENT ═════════════════════════════════
def kenh_den_luot(luc: float, dang_chay=(), goc: str = GOC_TOOL, ram=None, nang_ban=None) -> tuple:
    """(danh sách kênh nên mở tiến trình con, {kênh: lý do bỏ qua}). Agent gọi mỗi ~10 phút.
    `dang_chay`: kênh agent đã mở con mà chưa chắc đã giữ khoá. Cắt ở 4 Chrome + RAM >= 4 GB."""
    ly, ung = {}, []
    dang = set(dang_chay) | set(cac_kenh_dang_nuoi())
    for k in cac_kenh_bat(goc):
        if k in dang:
            ly[k] = "đang nuôi"
            continue
        so_v, r = quyet_dinh(doc_so(k), luc, NGAN_SACH_PHIEN_PHUT)
        if so_v and not (os.path.isfile(os.path.join(goc, "..", k, k + ".exe"))
                         or os.path.isfile(os.path.join(goc, "..", k, k, k + ".exe"))):
            so_v, r = 0, "chưa có Chrome Portable {0}/{0}.exe".format(k)
        if not so_v:
            ly[k] = r
        else:
            ung.append(k)
    if not ung:
        return [], ly
    if nang_ban if nang_ban is not None else khe_nang_ban(goc):
        return [], dict(ly, **{k: "máy đang bận (việc đăng giữ khe hoặc CPU ≥ 75%) — nhường" for k in ung})
    ra, ram = [], (ram_trong_gb() if ram is None else ram)
    dung = bool(khe_nang_viec(goc)) if nang_ban is None else False      # máy đang dựng → trần 2 Chrome
    for k in ung:
        r = duoc_mo_them(len(dang) + len(ra), ram, dung)
        if r:
            ly[k] = r
        else:
            ra.append(k)
            ram = None if ram is None else ram - 1.0       # mỗi Chrome nuôi ước ~1 GB
    return ra, ly


# ═══════════════════════════ LLM ════════════════════════════════════════════
def tao_llm():
    """Trả `goi(prompt) -> str` qua ShopAPI của tool (cùng cách mọi khâu LLM khác)."""
    if GOC_TOOL not in sys.path:
        sys.path.insert(0, GOC_TOOL)
    from core.api import build_client                       # noqa: PLC0415
    from core.config import CONFIG_FILENAME, load_config    # noqa: PLC0415
    from core.goi_van_ban import goi_van_ban                # noqa: PLC0415
    cfg = load_config(os.path.join(GOC_TOOL, CONFIG_FILENAME))
    if cfg.problem:
        raise RuntimeError("không đọc được cấu hình ShopAPI: " + str(cfg.problem)[:100])
    client = build_client(cfg)
    return lambda prompt: goi_van_ban(client, [{"role": "user", "content": prompt}],
                                      mo_hinh="claude-sonnet-5", toi_da_token=4096)


#: Ngôn ngữ của kênh đang nuôi (đặt ở đầu `chay_phien` từ kenh.yaml `ngon_ngu`).
NGON_NGU_KENH = "ja"
_RE_KANA = re.compile(r"[぀-ヿ]")


def sai_ngon_ngu(tieu_de: str, ngon_ngu: str = None) -> bool:
    """04/10/2026 (chủ dự án): nội dung KHÁC QUỐC GIA/ngôn ngữ (vd tâm lý tiếng Việt trên trang chủ kênh Nhật) là
    LẠC ĐỀ dù cùng chủ đề — chặn bằng MÃ, không trông LLM. Hiện chỉ chắc cho tiếng Nhật: không có kana = không phải
    tiếng Nhật (chữ Hán trơn có thể là tiếng Trung). Ngôn ngữ khác: không chặn (để LLM)."""
    ng = str(ngon_ngu or NGON_NGU_KENH or "").lower()
    if ng == "ja":
        return not _RE_KANA.search(str(tieu_de or ""))
    return False


def phan_loai(goi, mo_ta: str, cac_o: list, cache: dict) -> dict:
    """{video_id: nhan}. Phân loại theo NGHĨA bằng LLM, cache theo video_id (trong `cache`).
    Mỗi ô: {id, tieu_de, kenh}. LLM lỗi/thiếu thì ô đó KHÔNG có trong kết quả.
    Ô sai ngôn ngữ của kênh → `lac_de` ngay bằng mã (không gọi LLM)."""
    ra = {o["id"]: "lac_de" for o in cac_o if o.get("id") and sai_ngon_ngu(o.get("tieu_de"))}
    ra.update({o["id"]: cache[o["id"]] for o in cac_o if o["id"] not in ra and cache.get(o["id"]) in NHAN_HOP_LE})
    chua = [o for o in cac_o if o["id"] not in ra]
    for i in range(0, len(chua), 30):
        lo = chua[i:i + 30]
        ds = "\n".join("{0}|{1}|{2}".format(j + 1, o["tieu_de"][:150], o["kenh"][:50]) for j, o in enumerate(lo))
        prompt = (
            "Bạn phân loại video YouTube THEO Ý NGHĨA (không theo từ khoá) cho một kênh tâm lý học tiếng Nhật.\n"
            "NGÁCH của kênh: {0}\n"
            "CHỦ ĐỀ RỘNG của kênh: tâm lý học / khoa học não bộ / hiểu người, tiếng Nhật (tâm lý hành vi, tính cách, "
            "quan hệ, tuổi tác, não khoa học).\n"
            "Nhãn:\n- dung_ngach: đúng ngách cụ thể của kênh nói trên.\n"
            "- dung_chu_de: là tâm lý học/não khoa học tiếng Nhật nhưng KHÔNG đúng ngách cụ thể.\n"
            "- lac_de: mọi thứ khác (nấu ăn, game, tin tức, nhạc, giải trí, y tế/sức khoẻ thuần, tiền hưu/tài chính, "
            "Phật pháp/tâm linh, truyện đọc, học ngoại ngữ, video không phải tiếng Nhật, ...).\n"
            "QUAN TRỌNG: video của QUỐC GIA/NGÔN NGỮ KHÁC (tiếng Việt, Anh, Hàn, Trung…) luôn là lac_de, kể cả khi "
            "cũng nói về tâm lý.\n"
            "Danh sách (số|tiêu đề|kênh):\n{1}\n"
            "Chỉ trả JSON thuần: [{{\"i\":1,\"nhan\":\"dung_ngach\"}}, ...] đủ {2} phần tử.").format(mo_ta, ds, len(lo))
        try:
            if GOC_TOOL not in sys.path:
                sys.path.insert(0, GOC_TOOL)
            from core.goi_van_ban import loc_json               # noqa: PLC0415
            kq = loc_json(goi(prompt))
        except Exception as loi:                                # noqa: BLE001 — ô nào chưa phân loại thì bỏ
            print("phân loại LLM lỗi: {0}".format(str(loi)[:120]), flush=True)
            continue
        for x in kq if isinstance(kq, list) else []:
            try:
                o = lo[int(x["i"]) - 1]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            if x.get("nhan") in NHAN_HOP_LE:
                ra[o["id"]] = cache[o["id"]] = x["nhan"]
    return ra


# ═══════════════════════════ TRÌNH DUYỆT (CDP) ══════════════════════════════
_JS_O = r"""(() => {
  const bd = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const ra = [], thay = new Set();
  for (const a of document.querySelectorAll('a[href*="/watch?v="]')) {
    const m = /[?&]v=([\w-]{11})/.exec(a.getAttribute('href') || '');
    if (!m || thay.has(m[1])) continue;
    const o = a.closest('ytd-rich-item-renderer') || a.closest('yt-lockup-view-model') || a.closest('ytd-video-renderer');
    if (!o || o.closest('ytd-ad-slot-renderer, ytd-in-feed-ad-layout-renderer, ytd-display-ad-renderer')) continue;
    let ti = '';
    const h = o.querySelector('#video-title, h3 a, h3');
    if (h) ti = bd(h.getAttribute('title') || h.innerText || h.textContent);
    if (!ti) ti = bd(a.getAttribute('title') || a.getAttribute('aria-label') || a.innerText);
    const c = o.querySelector('ytd-channel-name a, #channel-name a, a[href^="/@"], a[href*="/channel/"], .yt-content-metadata-view-model__metadata-text');
    thay.add(m[1]);
    ra.push({id: m[1], tieu_de: ti, kenh: bd(c ? c.innerText : ''), meta: bd(o.innerText).slice(0, 160)});
  }
  return ra;
})()"""

_JS_KIEM_TRANG = r"""(() => {
  const t = ((document.body && document.body.innerText) || '').toLowerCase();
  const u = location.href;
  if (/consent\.youtube|consent\.google/.test(u)) return 'dong_y';
  if (/google\.com\/sorry|recaptcha/.test(u) || /unusual traffic|not a robot|not a bot|ロボットではありません|ボットでない|自動(送信|化)されたトラフィック/.test(t)) return 'captcha';
  if (/accounts\.google\.com/.test(u)) return 'dang_xuat';
  if (document.querySelector('ytd-masthead a[href*="ServiceLogin"], ytd-masthead a[href*="accounts.google.com"]') && !document.querySelector('#avatar-btn')) return 'dang_xuat';
  if (document.querySelector('ytd-masthead') && !document.querySelector('#avatar-btn')) return 'chua_ro';
  return 'ok';
})()"""

_JS_VIDEO = r"""(() => {
  const v = document.querySelector('video');
  if (!v) return null;
  const q = (s) => document.querySelector(s);
  const qc = document.querySelector('.ytp-skip-ad-button, .ytp-ad-skip-button, .ytp-ad-skip-button-modern, .ytp-skip-ad-button__text');
  let nut = null;
  if (qc) { const b = (qc.closest('button') || qc).getBoundingClientRect(); if (b.width > 0) nut = {x: b.x + b.width / 2, y: b.y + b.height / 2}; }
  return {dai: v.duration, t: v.currentTime, dung: v.paused, het: v.ended, tat_tieng: v.muted,
          qc: !!q('.ad-showing'), nut_qc: nut, live: !isFinite(v.duration)};
})()"""


class Tab:
    """Một tab Chrome kênh, điều khiển qua `vm/cdp.py` (JS trong thế giới riêng, chuột/cuộn thật)."""

    def __init__(self, cdp, tid, sid, rng, ngu=time.sleep):
        self.cdp, self.tid, self.sid, self.rng, self.ngu = cdp, tid, sid, rng, ngu
        self.ctx = None
        self.chuot = (rng.uniform(300, 700), rng.uniform(200, 400))

    @classmethod
    def gan(cls, cdp, rng):
        ds = cdp.goi("Target.getTargets", han=10).get("targetInfos") or []
        trang = [t for t in ds if t.get("type") == "page"]
        tid = trang[0]["targetId"] if trang else cdp.goi("Target.createTarget", {"url": "about:blank"})["targetId"]
        sid = cdp.goi("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        cdp.goi("Page.enable", sid=sid)
        try:
            cdp.goi("Emulation.setFocusEmulationEnabled", {"enabled": True}, sid=sid)
        except Exception:  # noqa: BLE001
            pass
        return cls(cdp, tid, sid, rng)

    def _the_gioi(self):
        fid = self.cdp.goi("Page.getFrameTree", sid=self.sid, han=15)["frameTree"]["frame"]["id"]
        self.ctx = self.cdp.goi("Page.createIsolatedWorld", {"frameId": fid, "worldName": "nt"},
                                sid=self.sid, han=15)["executionContextId"]

    def js(self, bt: str, han: float = 30.0):
        for lan in range(2):
            try:
                if self.ctx is None:
                    self._the_gioi()
                r = self.cdp.goi("Runtime.evaluate", {"expression": bt, "contextId": self.ctx, "returnByValue": True,
                                                      "awaitPromise": False}, sid=self.sid, han=han)
                if r.get("exceptionDetails"):
                    raise RuntimeError("JS lỗi: " + str((r["exceptionDetails"].get("exception") or {}).get("description") or "")[:150])
                canh_tien_trien.danh_dau()
                return (r.get("result") or {}).get("value")
            except RuntimeError:
                raise
            except Exception:  # noqa: BLE001 — mất ngữ cảnh sau điều hướng: dựng lại 1 lần
                self.ctx = None
                if lan:
                    raise
        return None

    def mo(self, url: str, han: float = 60.0):
        self.cdp.xoa_su_kien("Page.loadEventFired", self.sid)
        self.ctx = None
        r = self.cdp.goi("Page.navigate", {"url": url}, sid=self.sid, han=60)
        if r.get("errorText"):
            raise RuntimeError("điều hướng hỏng: " + r["errorText"])
        try:
            self.cdp.cho_su_kien("Page.loadEventFired", han=han, sid=self.sid)
        except Exception:  # noqa: BLE001 — trang nặng chưa báo xong thì dò tiếp
            pass
        self.ctx = None
        self.ngu(self.rng.uniform(1.5, 3.0))

    def kiem_trang(self) -> str:
        try:
            return str(self.js(_JS_KIEM_TRANG) or "ok")
        except Exception:  # noqa: BLE001
            return "ok"

    def chuot_toi(self, x, y):
        x0, y0 = self.chuot
        b = self.rng.randint(3, 6)
        for i in range(1, b + 1):
            t = i / float(b)
            self.cdp.goi("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": round(x0 + (x - x0) * t, 1),
                                                      "y": round(y0 + (y - y0) * t, 1), "button": "none"},
                         sid=self.sid, han=10)
            self.ngu(self.rng.uniform(0.01, 0.04))
        self.chuot = (x, y)

    def bam(self, x, y):
        self.chuot_toi(x, y)
        for loai, nut in (("mousePressed", 1), ("mouseReleased", 0)):
            self.cdp.goi("Input.dispatchMouseEvent", {"type": loai, "x": x, "y": y, "button": "left",
                                                      "buttons": nut, "clickCount": 1}, sid=self.sid, han=10)
            self.ngu(self.rng.uniform(0.04, 0.12))

    def cuon(self, dy):
        x, y = self.chuot
        self.cdp.goi("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": x, "y": y, "deltaX": 0, "deltaY": dy},
                     sid=self.sid, han=10)
        canh_tien_trien.danh_dau()

    def cuon_trang_chu(self, giay: float):
        """Cuộn như người thật `giay` giây: cuộn xuống từng đoạn, thỉnh thoảng lên một chút."""
        het = time.monotonic() + giay
        while time.monotonic() < het:
            self.cuon(self.rng.choice((-200, 300, 400, 500, 600)))
            self.ngu(self.rng.uniform(0.8, 2.2))


def doc_o_trang_chu(tab: Tab, toi_thieu: int = 8, cho_giay: float = 40.0, can: int = SO_O_DO) -> list:
    """Nạp trang chủ, cuộn cho tới khi có >= `can` ô (hoặc hết giờ), trả các ô theo thứ tự DOM."""
    tab.mo("https://www.youtube.com/")
    kt = tab.kiem_trang()
    if kt in ("captcha", "dang_xuat", "dong_y"):
        raise CanNguoi(kt)
    het, o = time.monotonic() + cho_giay, []
    while time.monotonic() < het:
        o = tab.js(_JS_O) or []
        if len(o) >= can:
            break
        if len(o) >= toi_thieu:
            tab.cuon(700)
        tab.ngu(1.5)
    kt = tab.kiem_trang()
    if kt in ("captcha", "dang_xuat", "dong_y"):
        raise CanNguoi(kt)
    if kt == "chua_ro" and not o:
        raise CanNguoi("không thấy ảnh đại diện — có thể chưa đăng nhập YouTube")
    return o


def xem_mot_video(tab: Tab, v: dict, ghi, kh: dict = None, ngu=time.sleep, dung=None) -> int:
    """Mở video, tắt tiếng, xem theo kế hoạch. Trả số giây đã xem (0 = bỏ qua)."""
    tab.mo("https://www.youtube.com/watch?v=" + v["id"])
    kt = tab.kiem_trang()
    if kt in ("captcha", "dang_xuat", "dong_y"):
        raise CanNguoi(kt)
    info, het = None, time.monotonic() + 100
    while time.monotonic() < het:            # chờ hết quảng cáo đầu (thời lượng của QC không phải của video)
        info = tab.js(_JS_VIDEO)
        if info and info.get("dai") and not info.get("live") and not info.get("qc"):
            break
        if info and info.get("nut_qc"):
            tab.bam(info["nut_qc"]["x"], info["nut_qc"]["y"])
        ngu(2)
    if info and info.get("qc"):
        info = None
    if not info or not info.get("dai") or info.get("live"):
        ghi("   bỏ qua {0}: không có trình phát/đang phát trực tiếp".format(v["id"]))
        return 0
    tab.js("(()=>{const v=document.querySelector('video'); if(v){v.muted=true; v.play&&v.play().catch(()=>{});} return 1;})()")
    ngu(1.5)
    if not (tab.js(_JS_VIDEO) or {}).get("tat_tieng"):
        ghi("   CẢNH BÁO: chưa tắt được tiếng {0}".format(v["id"]))
    kh = kh or ke_hoach_xem(info["dai"], tab.rng)
    ghi("   xem {0} ({1}) {2}: {3} phút trên {4:.1f} phút{5}".format(
        v["id"], v["kenh"][:20], v["tieu_de"][:30], kh["xem_giay"] // 60, info["dai"] / 60.0,
        ", sẽ tua" if kh["tua"] else ""))
    bd, da_tua, lan_kt = time.monotonic(), False, 0
    tran = kh["xem_giay"] * 1.7 + 180
    while True:
        gio = time.monotonic() - bd
        if gio >= kh["xem_giay"] or gio >= tran or (dung is not None and dung()):
            break
        ngu(tab.rng.uniform(5, 9))
        info = tab.js(_JS_VIDEO)
        if not info:
            break
        if info.get("t") is None or not info.get("dai"):    # trình phát chưa nạp / đang quảng cáo: chờ nhịp sau
            continue
        if info.get("het") or info["t"] >= info["dai"] - 3:
            break
        if info.get("nut_qc"):                       # quảng cáo cho bỏ qua
            tab.bam(info["nut_qc"]["x"], info["nut_qc"]["y"])
        elif info.get("dung") and not info.get("qc"):
            tab.js("(()=>{const v=document.querySelector('video'); if(v){v.muted=true; v.play().catch(()=>{});}})()")
        if kh["tua"] and not da_tua and gio >= kh["tua"]["sau_giay"] and not info.get("qc"):
            den = min(info["dai"] - 10, info["t"] + kh["tua"]["nhay_giay"])
            tab.js("(()=>{const v=document.querySelector('video'); if(v) v.currentTime=%d;})()" % int(den))
            da_tua = True
        lan_kt += 1
        if lan_kt % 6 == 0 and tab.kiem_trang() in ("captcha", "dang_xuat", "dong_y"):
            raise CanNguoi(tab.kiem_trang())
    return int(time.monotonic() - bd)


def khong_quan_tam(tab: Tab, vid: str, ghi) -> bool:
    """Bấm ⋮ → "Không quan tâm" ở ô `vid` trên trang chủ. Tìm nút theo chữ đa ngôn ngữ."""
    js = ("((vid)=>{const a=document.querySelector('a[href*=\"v='+vid+'\"]'); if(!a) return null;"
          "const o=a.closest('ytd-rich-item-renderer')||a.closest('yt-lockup-view-model'); if(!o) return null;"
          "o.scrollIntoView({block:'center'}); const r=o.getBoundingClientRect();"
          "const b=o.querySelector('yt-lockup-metadata-view-model button, ytd-menu-renderer button, "
          ".yt-lockup-metadata-view-model__menu-button button');"
          "const q=b?b.getBoundingClientRect():null;"
          "return {tx:r.x+r.width/2, ty:r.y+r.height/3, b:q&&q.width>0?{x:q.x+q.width/2,y:q.y+q.height/2}:null};})(%s)"
          % json.dumps(vid))
    tab.ngu(0.6)
    p = tab.js(js)
    if not p or not p.get("b"):
        ghi("   không thấy nút ⋮ của {0}".format(vid))
        return False
    tab.chuot_toi(p["tx"], p["ty"])                 # rê chuột vào ô cho nút ⋮ hiện
    tab.ngu(tab.rng.uniform(0.4, 0.9))
    p = tab.js(js) or p
    tab.bam(p["b"]["x"], p["b"]["y"])
    tab.ngu(tab.rng.uniform(0.7, 1.4))
    m = tab.js("((re)=>{const R=new RegExp(re,'i'); for(const x of document.querySelectorAll("
               "'ytd-popup-container *, tp-yt-iron-dropdown *, yt-sheet-view-model *, [role=\"menu\"] *, [role=\"listbox\"] *')){"
               "if(x.children.length) continue; const t=(x.innerText||'').replace(/ +/g,' ').trim(); const r=x.getBoundingClientRect();"
               "if(r.width>0&&r.height>0&&R.test(t)) return {x:r.x+r.width/2,y:r.y+r.height/2,t:t};} return null;})(%s)"
               % json.dumps(CHU_KHONG_QUAN_TAM))
    if not m:
        ghi("   menu ⋮ của {0} không có mục 'Không quan tâm'".format(vid))
        tab.cdp.goi("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape",
                                               "windowsVirtualKeyCode": 27}, sid=tab.sid, han=10)
        return False
    tab.bam(m["x"], m["y"])
    tab.ngu(tab.rng.uniform(1.0, 2.0))
    return True


# ═══════════════════════════ PHIÊN ══════════════════════════════════════════
def _nhat_ky(kenh: str):
    os.makedirs(THU_MUC_SO, exist_ok=True)
    duong = os.path.join(THU_MUC_SO, kenh + ".log")

    def ghi(dong):
        canh_tien_trien.danh_dau()
        chu = "{0} {1}".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong)
        try:
            print(chu, flush=True)
        except (OSError, UnicodeEncodeError):
            pass
        try:
            with open(duong, "a", encoding="utf-8") as tep:
                tep.write(chu + "\n")
        except OSError:
            pass
    return ghi


def _nap_agent(ghi):
    if GOC not in sys.path:
        sys.path.insert(0, GOC)
    import agent                                            # noqa: PLC0415 — nạp không chạy gì
    agent.ghi = ghi                                         # mọi dòng log của agent.* vào sổ của phiên này
    return agent


def cau_hinh_kenh_moi(agent, kenh: str) -> dict:
    """Cấu hình agent cho kênh mới: thêm các kênh mới vào CUỐI `cac_kenh` để có CỔNG DevTools
    RIÊNG (9304+), không đụng cổng 9300–9303 của TL4/1/2/3 đang đăng."""
    cfg = agent.doc_cau_hinh()
    cac = list(agent.danh_sach_kenh(cfg))
    for k in KENH_MOI_THU_TU + (kenh,):
        if k not in cac:
            cac.append(k)
    cfg = dict(cfg, cac_kenh=cac)
    return agent.cau_hinh_kenh(cfg, kenh)


def kiem_truoc_khi_chay(agent, kenh: str) -> None:
    if agent.van_ipv4_mo():
        raise Hoan("van IPv4 đang mở")
    if os.path.exists(os.path.join(GOC_TOOL, "logs", "dang-dodang.json")):
        raise Hoan("đang có máy đăng dở (logs/dang-dodang.json)")


def co_nguoi_xep_hang(goc_tool: str = GOC_TOOL) -> bool:
    """Có việc khác đang xếp hàng xin khe "nang" (tải lên/quét/sản xuất) — nhường họ."""
    try:
        sys.path.insert(0, GOC_TOOL) if GOC_TOOL not in sys.path else None
        from core import khe                                  # noqa: PLC0415
        return any(v.get("loai") == "nang" for v in khe.trang_thai(goc_tool).get("cho", []))
    except Exception:  # noqa: BLE001
        return False


def viec_dang_cho(agent, luc: float, kenh: str) -> str:
    """Lý do phải NHƯỜNG riêng KÊNH này (có việc đăng chờ), hoặc "". Cùng nguồn với agent:
    phiên kênh sắp tới giờ, gói chờ tải lên, bình luận chờ ghim, máy đăng dở."""
    if os.path.exists(os.path.join(GOC_TOOL, "logs", "dang-dodang.json")):
        return "đang có máy đăng dở"
    try:
        if GOC not in sys.path:
            sys.path.insert(0, GOC)
        import nguon_tool                                                               # noqa: PLC0415
        cfg = agent.doc_cau_hinh()
        tt, hom = agent._doc_trang_thai(cfg), time.strftime("%Y-%m-%d", time.localtime(luc))   # noqa: SLF001
        so_id = agent._doc_so_video_id()                                                # noqa: SLF001
        if kenh not in agent.danh_sach_kenh(cfg):
            return ""                                   # kênh mới chưa đăng qua agent: không có việc đăng
        ch = agent.cau_hinh_kenh(cfg, kenh)
        mt = tt.get("phien_muc_tieu@{0}@{1}".format(kenh, hom))
        if isinstance(mt, str) and mt and tt.get("phien_cuoi@" + kenh) != hom:
            tm = agent._phan_tich_gio(mt)                                               # noqa: SLF001
            if tm and tm.tm_hour * 60 + tm.tm_min <= _phut(luc) + NHIN_TRUOC_PHIEN_PHUT:
                return "phiên kênh {0} (mục tiêu {1}) sắp/đã tới giờ".format(kenh, mt)
        try:
            if agent.ma_can_tai_bo_sung(nguon_tool._tai_csv(ch, kenh), kenh, so_id, luc):   # noqa: SLF001
                return "kênh {0} có gói chờ tải lên".format(kenh)
        except Exception:  # noqa: BLE001 — không đọc được kế hoạch: không chặn
            pass
        lan_ghim = int(tt.get("ghim_som@{0}@{1}".format(kenh, hom)) or 0)
        if lan_ghim < agent.GHIM_SOM_TOI_DA_LUOT_NGAY and agent.video_can_ghim_som(
                so_id, agent._doc_so_cmt_dom(), kenh, luc, ghim_bat=bool(ch.get("ghim_dom", False))):   # noqa: SLF001
            return "kênh {0} có bình luận chờ ghim".format(kenh)
    except Exception:  # noqa: BLE001 — đọc nguồn hỏng thì không tự chặn (còn cờ .dung của agent canh)
        pass
    return ""


def ly_do_dung(agent, kenh: str, luc: float) -> str:
    """Lý do phải DỪNG phiên đang chạy ở video kế: cờ của agent, khe nang bận, khung cấm, việc đăng chờ."""
    if co_dung(kenh):
        return "agent báo có việc đăng cần Chrome kênh (cờ .dung)"
    if khung_cam(luc, 0):
        return khung_cam(luc, 0)
    if khe_nang_ban():
        return "máy đang bận (việc đăng giữ khe hoặc CPU ≥ 75%) — nhường"
    return viec_dang_cho(agent, luc, kenh)


def chay_phien(kenh: str, so_video: int, ghi, rng=None, bo_qua_khung: bool = False) -> int:
    rng = rng or random.Random()
    luc0 = time.time()
    so = doc_so(kenh)
    toi_da, ly = quyet_dinh(so, luc0, NGAN_SACH_PHIEN_PHUT, bo_qua_khung)
    if not toi_da:
        ghi("bỏ qua: " + ly)
        return MA_KHONG_CAN if so.get("trang_thai") in ("can_nguoi", "dat") else MA_HOAN
    so_video = max(1, min(int(so_video), toi_da))
    agent = _nap_agent(ghi)
    try:
        kiem_truoc_khi_chay(agent, kenh)
        for r in (viec_dang_cho(agent, luc0, kenh), "máy đang bận (việc đăng/CPU ≥ 75%)" if khe_nang_ban() else ""):
            if r:
                raise Hoan("nhường: " + r)
    except Hoan as h:
        ghi("hoãn: {0}".format(h))
        return MA_HOAN
    ch = cau_hinh_kenh_moi(agent, kenh)
    chrome = agent.tim_chrome(ch)
    if not chrome:
        ghi("hoãn: không thấy Chrome Portable của kênh {0}".format(kenh))
        return MA_HOAN
    # Khoá RIÊNG THEO KÊNH: không bao giờ 2 tiến trình cùng mở Chrome/profile của kênh này.
    if not giu_khoa(kenh):
        ghi("hoãn: kênh {0} đang có tiến trình nuôi khác (khoá {0}.khoa)".format(kenh))
        return MA_HOAN
    xoa_co_dung(kenh)
    khoa_mo, cdp, tab, tu_mo, ch_da_mo = False, None, None, False, False
    phien = {"ngay": datetime.fromtimestamp(luc0).date().isoformat(), "bat_dau": time.strftime("%H:%M", time.localtime(luc0)),
             "bat_dau_luc": luc0, "so_video": 0, "giay_xem": 0, "khong_quan_tam": 0, "ket_qua": "đang chạy"}
    ma_thoat, bi_ngat = 0, False
    try:
        if agent._chrome_dang_chay(chrome):                 # noqa: SLF001 — Chrome kênh đang mở bởi người/agent: KHÔNG đụng
            ghi("hoãn: Chrome kênh {0} đang chạy (không phải phiên của tôi)".format(kenh))
            phien["ket_qua"] = "hoãn: Chrome đang chạy"
            return MA_HOAN
        # Mở Chrome lần lượt (khoá `_mo`): kiểm 4 Chrome + RAM >= 4 GB ngay trước mỗi lần mở.
        han = time.monotonic() + 180
        while not giu_khoa("_mo"):
            if time.monotonic() > han:
                ghi("hoãn: chờ lượt mở Chrome quá 3 phút")
                phien["ket_qua"] = "hoãn: chờ lượt mở"
                return MA_HOAN
            time.sleep(3)
        khoa_mo = True
        r = duoc_mo_them(len(cac_kenh_dang_nuoi()) - 1, ram_trong_gb(),
                        bool(khe_nang_viec()))      # trừ chính mình
        if r:
            ghi("hoãn: {0}".format(r))
            phien["ket_qua"] = "hoãn: " + r
            return MA_HOAN
        if not so.get("bat_dau"):
            so["bat_dau"] = phien["ngay"]
        so["phien"].append(phien)
        luu_so(so)                                          # ghi TRƯỚC khi chạy: tắt giữa chừng vẫn tính lượt
        ghi("── NUÔI TRANG CHỦ {0}: phiên {1} (tối đa {2} video) ──".format(kenh, len(so["phien"]), so_video))
        if GOC not in sys.path:
            sys.path.insert(0, GOC)
        import cdp as cdp_mod                               # noqa: PLC0415
        agent.ghi_che_do_mat_cao(ch, False)
        cong = agent._cong_devtools(ch)                     # noqa: SLF001
        tu_mo = True
        canh_tien_trien.bat_canh(lambda: (agent.dong_chrome_kenh(ch), nha_khoa(kenh)), ghi=ghi)
        agent.mo_chrome_kenh(ch, "https://www.youtube.com/", chrome, da_chay=False, quet=False)
        ws = agent._cho_devtools(cong, agent.CHO_DEVTOOLS_GIAY)  # noqa: SLF001
        nha_khoa("_mo")
        khoa_mo = False
        if not ws:
            raise RuntimeError("Chrome mở nhưng cổng DevTools {0} không đáp".format(cong))
        cdp = cdp_mod.Cdp.mo(ws)
        tab = Tab.gan(cdp, rng)
        tab.ngu(3)
        mo_ta, goi = mo_ta_ngach(kenh), tao_llm()

        def dung():
            return ly_do_dung(agent, kenh, time.time())

        def do_va_ghi(o: list, nl: dict, nhan: str) -> None:
            """04/10/2026: ĐO mỗi lần đã đọc + phân loại trang chủ (đầu phiên, giữa phiên, cuối phiên) — trước đây
            chỉ đo cuối phiên, mà phiên hay bị ngắt để nhường việc đăng → nhiều kênh không có lần đo nào."""
            o = o[:SO_O_DO]
            ket = phan_tram([nl[x["id"]] for x in o if x["id"] in nl])
            ket["vi_du_lac_de"] = ["{0} — {1}".format(x["kenh"][:25], x["tieu_de"][:60]) for x in o if nl.get(x["id"]) == "lac_de"]
            if ket["n"] >= TOI_THIEU_O_DO:
                ghi_lan_do(so, ket, time.strftime("%Y-%m-%d %H:%M"))
                luu_so(so)
                ghi("ĐO ({0}): {1} ô · chủ đề {2}% · ngách {3}% · {4}".format(
                    nhan, ket["n"], ket["pct_chu_de"], ket["pct_ngach"], "ĐẠT" if so["lan_do"][-1]["dat"] else "chưa đạt"))
                for t in ket["vi_du_lac_de"][:5]:
                    ghi("   lạc đề: " + t)
            else:
                ghi("ĐO KHÔNG TÍNH ({0}): chỉ phân loại được {1} ô (cần >= {2}) — {3} ô đọc được".format(
                    nhan, ket["n"], TOI_THIEU_O_DO, len(o)))

        def day_lac_de(o: list, nl: dict, toi_da: int) -> None:
            """04/10/2026 (chủ dự án): VỪA bấm "Không quan tâm" mọi ô lạc đề (kể cả khác quốc gia) VỪA xem tích cực
            đúng chủ đề → trang chủ sạch nhanh. Mỗi lần về trang chủ đều dọn, không đợi 3–5 video."""
            n = 0
            for x in o:
                if n >= toi_da or phien["khong_quan_tam"] >= TOI_DA_KHONG_QUAN_TAM:
                    break
                if nl.get(x["id"]) == "lac_de" and khong_quan_tam(tab, x["id"], ghi):
                    n += 1
                    phien["khong_quan_tam"] += 1
                    ghi("   Không quan tâm: {0} — {1}".format(x["kenh"][:20], x["tieu_de"][:40]))

        global NGON_NGU_KENH
        NGON_NGU_KENH = str(doc_kenh_yaml(kenh).get("ngon_ngu") or "ja").strip().lower()
        # Kiểm trang chủ trước: chưa đăng nhập / CAPTCHA thì dừng ngay. Đọc đủ ô để ĐO luôn đầu phiên.
        o0 = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=30)
        ghi("trang chủ đã đăng nhập, thấy {0} ô video".format(len(o0)))
        nl0 = phan_loai(goi, mo_ta, o0[:SO_O_DO], so["cache"])
        do_va_ghi(o0, nl0, "đầu phiên")
        if so.get("trang_thai") == "dat":
            chon_truoc = True
        else:
            chon_truoc = False
            day_lac_de(o0, nl0, KHONG_QUAN_TAM_MOI_LAN * 2)
            luu_so(so)
        hom = datetime.fromtimestamp(luc0).date()
        ung = doc_ung_vien(kenh, hom)
        cam_id, cam_ten = id_video_cua_minh(), ten_kenh_cua_minh()
        chon = chon_video(ung, so["da_xem"], cam_id, cam_ten, so_video * 2, hom, rng)
        nh = phan_loai(goi, mo_ta, chon, so["cache"])                # LLM loại ô lạc đề theo nghĩa
        chon = [v for v in chon if nh.get(v["id"]) in ("dung_ngach", "dung_chu_de")]
        chon = chon_video([dict(v, ngach=(nh[v["id"]] == "dung_ngach")) for v in chon], (), (), (), so_video, hom, rng)
        ghi("đã chọn {0} video ({1} đúng ngách) từ {2} ứng viên".format(
            len(chon), sum(1 for v in chon if v["ngach"]), len(ung)))
        moc_day, so_gan = rng.randint(3, 5), 0
        if chon_truoc:
            chon = []                                       # đạt ngay đầu phiên → không cần xem thêm
        for v in chon:
            r = dung()
            if not r and time.time() - luc0 > NGAN_SACH_PHIEN_PHUT * 60:
                r = "hết ngân sách {0} phút của phiên".format(NGAN_SACH_PHIEN_PHUT)
            if r:
                ghi("dừng sớm: {0}".format(r))
                bi_ngat = not r.startswith("hết ngân sách")
                break
            so["da_xem"][v["id"]] = {"luc": time.strftime("%Y-%m-%d %H:%M"), "tieu_de": v["tieu_de"][:80], "kenh": v["kenh"]}
            giay = xem_mot_video(tab, v, ghi, dung=dung)
            phien["so_video"] += 1 if giay else 0
            phien["giay_xem"] += giay
            luu_so(so)
            so_gan += 1
            if dung():
                continue                                    # vòng sau sẽ ghi lý do và dừng
            tab.mo("https://www.youtube.com/")
            if tab.kiem_trang() in ("captcha", "dang_xuat", "dong_y"):
                raise CanNguoi(tab.kiem_trang())
            tab.cuon_trang_chu(rng.uniform(5, 20))
            # Mỗi lần về trang chủ: đọc + dọn ô lạc đề; ĐO (ghi sổ) mỗi 3–5 video.
            o = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=25)
            nl = phan_loai(goi, mo_ta, o, so["cache"])
            if so_gan >= moc_day:
                so_gan, moc_day = 0, rng.randint(3, 5)
                do_va_ghi(o, nl, "giữa phiên")
                if so.get("trang_thai") == "dat":
                    break
            day_lac_de(o, nl, KHONG_QUAN_TAM_MOI_LAN)
            luu_so(so)
            tab.ngu(rng.uniform(10, 60))
        if not bi_ngat and so.get("trang_thai") != "dat":
            # Đo cuối phiên: nạp lại trang chủ, ~30 ô đầu, LLM phân loại.
            o = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=40)[:SO_O_DO]
            do_va_ghi(o, phan_loai(goi, mo_ta, o, so["cache"]), "cuối phiên")
        phien["ket_qua"] = "bị ngắt (nhường việc đăng/khe nang)" if bi_ngat else "xong"
        if so.get("trang_thai") == "dat":
            d = tat_nuoi(kenh)
            ghi("*** ĐẠT: {0} — {1} ***".format(so["ly_do"], ("đã ghi nuoi_trang_chu: false vào " + d) if d
                                                 else "KHÔNG ghi được false vào kenh.yaml, chủ tự tắt"))
            so["da_tat_yaml"] = d
    except CanNguoi as c:
        so["trang_thai"], so["ly_do"] = "can_nguoi", "cần người xử lý: {0} (không thử lại)".format(c)
        phien["ket_qua"] = "can_nguoi: {0}".format(c)
        ghi("DỪNG — {0}".format(so["ly_do"]))
        ma_thoat = MA_CAN_NGUOI
    except Exception as loi:  # noqa: BLE001 — phiên hỏng: ghi rõ, phiên sau thử lại
        phien["ket_qua"] = "lỗi: {0}".format(str(loi)[:150])
        ghi("PHIÊN LỖI: {0}".format(str(loi)[:200]))
        ma_thoat = 1
    finally:
        phien["ket_thuc_luc"] = time.time()
        if phien in so["phien"]:
            so["nghi_den_luc"] = phien["ket_thuc_luc"] + nghi_giua_phien(rng, bi_ngat or phien["ket_qua"].startswith("hoãn"))
            try:
                luu_so(so)
            except OSError:
                pass
        try:
            if cdp:
                cdp.dong()
            if tu_mo:
                agent.dong_chrome_kenh(ch)
        finally:
            if khoa_mo:
                nha_khoa("_mo")
            xoa_co_dung(kenh)
            nha_khoa(kenh)
    return ma_thoat


def che_thu(kenh: str, so_video: int, ghi) -> int:
    """`--thu`: không mở Chrome, không ghi sổ — chỉ kiểm giới hạn + in kế hoạch chọn video."""
    rng, hom_nay, luc = random.Random(), date.today(), time.time()
    so = doc_so(kenh)
    toi_da, ly = quyet_dinh(so, luc, NGAN_SACH_PHIEN_PHUT)
    ghi("[thử] phiên này tối đa {0} video {1}".format(toi_da, ly))
    ung = doc_ung_vien(kenh, hom_nay)
    chon = chon_video(ung, so["da_xem"], id_video_cua_minh(), ten_kenh_cua_minh(), min(so_video, TOI_DA_VIDEO_PHIEN),
                      hom_nay, rng)
    ghi("[thử] {0} ứng viên hợp lệ ({1} đúng ngách) → chọn {2}:".format(
        len(ung), sum(1 for v in ung if v["ngach"]), len(chon)))
    for v in chon:
        kh = ke_hoach_xem(v["dai"] or 600, rng)
        ghi("   {0} {1} | {2} | {3} view | xem {4}s{5}".format(
            "NGÁCH" if v["ngach"] else "rộng ", v["id"], v["kenh"][:18], v["view"], kh["xem_giay"],
            " + tua" if kh["tua"] else ""))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Nuôi trang chủ YouTube cho kênh mới.")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--so-video", type=int, default=TOI_DA_VIDEO_PHIEN)
    ap.add_argument("--thu", action="store_true", help="không mở Chrome, chỉ in kế hoạch")
    a = ap.parse_args(argv)
    ghi = _nhat_ky(a.kenh)
    cfg = doc_kenh_yaml(a.kenh)
    if not cfg:
        ghi("không thấy kenh.yaml của {0}".format(a.kenh))
        return 1
    if not cfg.get("bat"):
        ghi("kênh {0} không bật nuoi_trang_chu: true — không chạy".format(a.kenh))
        return MA_KHONG_CAN
    if a.thu:
        return che_thu(a.kenh, a.so_video, ghi)
    return chay_phien(a.kenh, a.so_video, ghi)


if __name__ == "__main__":
    sys.exit(main())
