"""NUÔI TRANG CHỦ cho kênh (03/10/2026) — CÔNG TẮC: chạy tới khi ĐẠT rồi tự TẮT.

Vì sao: trang chủ YouTube của tài khoản kênh mới đề xuất lung tung, mà tool lấy trang
chủ để tìm đối thủ + xu hướng. Tệp này cho Chrome ĐÃ ĐĂNG NHẬP của kênh xem video đối
thủ cùng ngách như người thật (tắt tiếng, xem 35–85% thời lượng, thỉnh thoảng tua), bấm
"Không quan tâm" vài video lạc đề, rồi ĐO trang chủ (~30 ô) bằng LLM theo NGHĨA.

ĐẠT (nuôi lần đầu) = % chủ đề (dung_ngach + dung_chu_de) > 90%, CHỈ CẦN 1 lần đo.

DUY TRÌ (19/10/2026, chủ: "quét trang chủ các kênh hiện tại không đạt 90% đúng chủ đề — cần 1 tuần 1 lần hoặc kênh
nào <90 thì cần logic để nó đúng chủ đề"). Trạng thái MÁY ở `<kênh>.duy-tri.json` (KHÔNG ghi kenh.yaml nữa):
  duy_tri   đo-không-xem mỗi 7 ngày (`--do`, skill D18, khe máy + khoá Chrome kênh); lần đo cuối dưới mục tiêu → 3 ngày.
  nuoi_lai  lần đo có % chủ đề < 90% HOẶC % ngách tụt (< 0,6 × tốt nhất 90 ngày của CHÍNH kênh, < 30%, hụt ≥ 10 điểm)
            → phiên nuôi thường (agent, cùng giới hạn) nghiêng về NGÁCH HẸP (bài biên tập viên chọn, nguồn video thắng
            của kênh, nguồn anh em cùng tệp), đo sau mỗi phiên. 2 lần đạt liền (cách ≥ 3 giờ) + % ngách khoẻ → về duy_tri.
            7 ngày + ≥ 8 phiên vẫn dưới → báo động MỘT lần kèm ô lạc đề, nuôi CHẬM (nghỉ 60–120', ≤ 20 video/ngày), không dừng.
Công tắc chủ `nuoi_trang_chu` (kenh.yaml): true = bật; false do CHÍNH máy ghi khi đạt (bản trước 19/10, sổ có
`da_tat_yaml`) = máy được duy trì + nuôi lại; false chủ tự đặt = CHỈ ĐO, dưới mục tiêu thì hỏi chủ ("Việc của bạn");
`duy_tri_trang_chu: false` = tắt hẳn (không đo).
Đo: ô có `&list=` (Mix/danh sách) và ô quảng cáo bị loại; Shorts (`/shorts/`) không bao giờ vào thước. Lần đo duy trì
đọc trang chủ 2 lần (nạp lại) rồi gộp ô khác nhau — ghi % từng lần + độ chênh để biết thước có ổn định không.

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
      `python vm/nuoi_trang_chu.py --kenh TL5-T7 --do [--on-dinh]`  CHỈ ĐO (không xem, không bấm gì); `--on-dinh` phân
      loại lại ô lần 1 không cache để đo độ ổn định của thước LLM.
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
#: Thư mục khoá Chrome theo kênh + cờ `.dung` (None = cùng thư mục sổ). Tách được để chạy thử sổ ở chỗ khác mà khoá vẫn
#: nằm đúng chỗ agent nhìn.
THU_MUC_KHOA = None

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

# ── DUY TRÌ (19/10/2026) ────────────────────────────────────────────────────
DUY_TRI_PCT_CHU_DE = 90.0                # đo duy trì: % chủ đề DƯỚI ngần này → tự nuôi lại
NGAY_DO_DUY_TRI = 7                      # đo lại mỗi tuần
NGAY_DO_DUOI_MUC = 3                     # lần đo cuối dưới mục tiêu / đang nuôi lại → đo lại sau 3 ngày
NGAY_NGACH_TOT = 90                      # "tốt nhất gần đây" của % ngách = max các lần đo trong 90 ngày
HE_SO_NGACH_TUT, NGACH_SAN_PCT, NGACH_HUT_TOI_THIEU = 0.6, 30.0, 10.0   # tụt: < 0,6×tốt nhất VÀ < 30% VÀ hụt ≥ 10 điểm
HE_SO_NGACH_KHOE = 0.75                  # khoẻ lại: ≥ 30% hoặc ≥ 0,75×tốt nhất (trễ so với ngưỡng tụt)
SO_DAT_LIEN_VE_DUY_TRI = 2
GIO_GIUA_HAI_LAN_DAT = 3                 # hai lần đạt tính "liền" phải cách nhau ≥ 3 giờ (khác phiên)
NGAY_BAO_DONG, PHIEN_BAO_DONG = 7, 8     # nuôi lại ≥ 7 ngày + ≥ 8 phiên vẫn dưới → báo động một lần, nuôi chậm
NGAY_BAO_IT_PHIEN = 10                   # nuôi lại ≥ 10 ngày mà chưa đủ 8 phiên (bị nhường mãi) → báo một lần
NGHI_CHAM_PHUT = (60, 120)
TOI_DA_VIDEO_NGAY_CHAM = 20
TI_LE_NGACH_NUOI_LAI = 0.85
DU_KIEN_DO_PHUT = 8
NHAN_CHE_DO = {"duy_tri": "duy trì (đo hằng tuần)", "nuoi_lai": "đang tự nuôi lại", "nuoi_dau": "đang nuôi lần đầu"}

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
        # 19/10: `uu_tien` (nguồn ngách hẹp khi nuôi lại — `nguon_ngach_hep`) nhân điểm; mặc định 1 = như cũ
        nguoi.append((view / max(1, tuoi) * max(1.0, float(v.get("uu_tien") or 1)), v))
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


def ghi_lan_do(so: dict, ket: dict, luc: str, nguon: str = "phien") -> dict:
    """Thêm một lần đo vào sổ; đạt (1 lần) thì `trang_thai = "dat"`. `nguon`: phien | duy_tri (đo-không-xem)."""
    muc = {"luc": luc, "n": ket["n"], "pct_chu_de": ket["pct_chu_de"], "pct_ngach": ket["pct_ngach"],
           "dem": ket["dem"], "dat": dat_tieu_chi(ket["pct_chu_de"], ket["pct_ngach"], ket["n"]),
           "vi_du_lac_de": list(ket.get("vi_du_lac_de") or [])[:6], "nguon": nguon}
    for k in ("doc", "chenh_chu_de", "trung_o", "bo_qua", "hl", "on_dinh"):
        if ket.get(k) not in (None, "", [], {}):
            muc[k] = ket[k]
    so.setdefault("lan_do", []).append(muc)
    so["lan_do"] = so["lan_do"][-200:]
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


def quyet_dinh(so: dict, luc: float, du_kien_phut: float = 0.0, bo_qua_khung: bool = False, dt: dict = None) -> tuple:
    """(số video được xem phiên này, lý do bỏ qua). 0 + lý do = không chạy lúc này. Thuần.
    `dt` = sổ duy trì: `che_do == "nuoi_lai"` thì kênh đã đạt vẫn được nuôi; `cham` = nhịp chậm (≤ 20 video/ngày)."""
    tt = so.get("trang_thai", "dang_nuoi")
    dt = dt or {}
    if tt == "can_nguoi":
        return 0, "đang chờ người xử lý ({0})".format(so.get("ly_do", ""))
    if tt == "dat" and dt.get("che_do") != "nuoi_lai":
        return 0, "đã đạt — không nuôi nữa (duy trì: đo lại định kỳ)"
    if not bo_qua_khung:
        k = khung_cam(luc, du_kien_phut)
        if k:
            return 0, k
    tran = TOI_DA_VIDEO_NGAY_CHAM if dt.get("cham") else TOI_DA_VIDEO_NGAY
    con = tran - video_hom_nay(so, datetime.fromtimestamp(luc).date().isoformat())
    if con <= 0:
        return 0, "đã đủ {0} video hôm nay".format(tran)
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


def nghi_giua_phien(rng: random.Random, bi_ngat: bool = False, cham: bool = False) -> float:
    """Số giây nghỉ tới phiên kế: 20–40 phút (bị ngắt giữa chừng thì chỉ vài phút; nhịp chậm sau báo động 60–120')."""
    if bi_ngat:
        return NGHI_NGAT_PHUT * 60.0
    return rng.uniform(*(NGHI_CHAM_PHUT if cham else NGHI_PHIEN_PHUT)) * 60.0


# ═══════════════════════════ DUY TRÌ (thuần, có test) ═══════════════════════
def _luc_so(chu) -> float:
    """"YYYY-MM-DD HH:MM" (giờ máy) → timestamp; hỏng → 0."""
    try:
        return time.mktime(time.strptime(str(chu or "")[:16], "%Y-%m-%d %H:%M"))
    except (ValueError, OverflowError):
        return 0.0


def lan_do_hop_le(lan_do) -> list:
    return [x for x in (lan_do or []) if isinstance(x, dict) and int(x.get("n") or 0) >= TOI_THIEU_O_DO]


def ngach_tot(lan_do, luc: float, ngay: int = NGAY_NGACH_TOT) -> float:
    """% ngách tốt nhất của CHÍNH kênh trong `ngay` ngày trước `luc` (0 nếu chưa có)."""
    moc = luc - ngay * 86400
    return max([float(x.get("pct_ngach") or 0) for x in lan_do_hop_le(lan_do) if _luc_so(x.get("luc")) >= moc] or [0.0])


def danh_gia_do(muc: dict, lan_do_truoc, luc: float) -> dict:
    """Một lần đo so với thước duy trì: {dat, chu_de_ok, ngach_tut, ngach_khoe, ngach_tot, ly_do}.
    Đạt = đủ ô, % chủ đề ≥ 90 và % ngách KHÔNG tụt so với mức tốt nhất gần đây của chính kênh."""
    tot = ngach_tot(lan_do_truoc, luc)
    cd, ng, n = float(muc.get("pct_chu_de") or 0), float(muc.get("pct_ngach") or 0), int(muc.get("n") or 0)
    chu_de_ok = n >= TOI_THIEU_O_DO and cd >= DUY_TRI_PCT_CHU_DE
    tut = tot > 0 and ng < HE_SO_NGACH_TUT * tot and ng < NGACH_SAN_PCT and tot - ng >= NGACH_HUT_TOI_THIEU
    khoe = tot <= 0 or ng >= NGACH_SAN_PCT or ng >= HE_SO_NGACH_KHOE * tot
    ly = []
    if n < TOI_THIEU_O_DO:
        ly.append("chỉ {0} ô (cần ≥ {1})".format(n, TOI_THIEU_O_DO))
    elif not chu_de_ok:
        ly.append("chủ đề {0:.0f}% < {1:.0f}%".format(cd, DUY_TRI_PCT_CHU_DE))
    if tut:
        ly.append("ngách tụt {0:.0f}% (tốt nhất {1:.0f}%)".format(ng, tot))
    return {"dat": chu_de_ok and not tut, "chu_de_ok": chu_de_ok, "ngach_tut": tut, "ngach_khoe": khoe,
            "ngach_tot": round(tot, 1), "ly_do": "; ".join(ly) or "chủ đề {0:.0f}% · ngách {1:.0f}%".format(cd, ng)}


def duy_tri_moi(kenh: str) -> dict:
    return {"kenh": kenh, "che_do": "", "tu_luc": 0.0, "dat_lien": 0, "dat_cuoi_luc": 0.0, "phien_nuoi_lai": 0,
            "cham": False, "bao_dong": "", "ly_do": "", "do_cuoi": {}, "lich_su": []}


def che_do_hien(so: dict, dt: dict, ct: str) -> str:
    """duy_tri | nuoi_lai | nuoi_dau. Sổ duy trì thắng; chưa có thì suy từ sổ nuôi + công tắc."""
    c = (dt or {}).get("che_do")
    if c in ("duy_tri", "nuoi_lai"):
        return c
    if (so or {}).get("trang_thai") == "dat":
        return "duy_tri"
    if ct == "bat" and (so or {}).get("trang_thai") != "can_nguoi":
        return "nuoi_dau"
    return "duy_tri"


def duoc_nuoi_lai(ct: str) -> bool:
    """Công tắc cho máy TỰ nuôi lại: chủ bật, hoặc false do chính máy ghi lúc đạt (trước 19/10)."""
    return ct in ("bat", "may_tat")


def cap_nhat_duy_tri(dt: dict, muc: dict, lan_do_truoc, luc: float) -> tuple:
    """(sổ duy trì mới, sự kiện "" | "duoi_muc" | "ve_duy_tri") sau MỘT lần đo hợp lệ. Thuần."""
    dg = danh_gia_do(muc, lan_do_truoc, luc)
    dt = dict(duy_tri_moi(str((dt or {}).get("kenh") or "")), **(dt or {}))
    dt["do_cuoi"] = {"luc": muc.get("luc"), "pct_chu_de": muc.get("pct_chu_de"), "pct_ngach": muc.get("pct_ngach"),
                     "n": muc.get("n"), "nguon": muc.get("nguon") or "", "dat": dg["dat"], "ngach_tot": dg["ngach_tot"],
                     "ly_do": dg["ly_do"]}
    sk = ""
    if dt.get("che_do") != "nuoi_lai":
        if not dg["dat"]:
            dt.update(che_do="nuoi_lai", tu_luc=luc, dat_lien=0, dat_cuoi_luc=0.0, phien_nuoi_lai=0, cham=False,
                      bao_dong="", ly_do=dg["ly_do"])
            sk = "duoi_muc"
        else:
            dt.update(che_do="duy_tri", ly_do=dg["ly_do"])
            dt["tu_luc"] = dt.get("tu_luc") or luc
    elif dg["dat"] and dg["ngach_khoe"]:
        if not dt.get("dat_lien") or luc - float(dt.get("dat_cuoi_luc") or 0) >= GIO_GIUA_HAI_LAN_DAT * 3600:
            dt["dat_lien"], dt["dat_cuoi_luc"] = int(dt.get("dat_lien") or 0) + 1, luc
        if dt["dat_lien"] >= SO_DAT_LIEN_VE_DUY_TRI:
            dt.update(che_do="duy_tri", tu_luc=luc, dat_lien=0, dat_cuoi_luc=0.0, cham=False, bao_dong="",
                      ly_do="về duy trì: {0} lần đạt liền ({1})".format(SO_DAT_LIEN_VE_DUY_TRI, dg["ly_do"]))
            sk = "ve_duy_tri"
    else:
        dt.update(dat_lien=0, dat_cuoi_luc=0.0, ly_do=dg["ly_do"] if not dg["dat"] else
                  "chủ đề đạt nhưng ngách chưa khoẻ ({0})".format(dg["ly_do"]))
    dt["lich_su"] = (list(dt.get("lich_su") or []) + [{"luc": muc.get("luc"), "pct_chu_de": muc.get("pct_chu_de"),
                                                       "pct_ngach": muc.get("pct_ngach"), "dat": dg["dat"],
                                                       "che_do": dt["che_do"], "su_kien": sk}])[-60:]
    return dt, sk


def can_bao_dong(dt: dict, luc: float, ct: str = "bat") -> str:
    """"" | "khong_hieu_qua" (≥ 7 ngày + ≥ 8 phiên vẫn dưới) | "it_phien" (≥ 10 ngày mà < 8 phiên). Một lần mỗi đợt;
    chủ đang tắt nuôi thì không báo động (đã hỏi chủ ở Việc của bạn)."""
    dt = dt or {}
    if dt.get("che_do") != "nuoi_lai" or dt.get("bao_dong") or not duoc_nuoi_lai(ct) or not dt.get("tu_luc"):
        return ""
    ngay, phien = (luc - float(dt["tu_luc"])) / 86400.0, int(dt.get("phien_nuoi_lai") or 0)
    if ngay >= NGAY_BAO_DONG and phien >= PHIEN_BAO_DONG:
        return "khong_hieu_qua"
    if ngay >= NGAY_BAO_IT_PHIEN and phien < PHIEN_BAO_DONG:
        return "it_phien"
    return ""


def den_han_do(so: dict, dt: dict, luc: float, ct: str, kiem_dom_luc: float = 0.0) -> tuple:
    """(cần đo-không-xem bây giờ?, lý do) — lịch tuần, 3 ngày khi lần trước dưới mục tiêu / đang nuôi lại. Thuần."""
    if ct == "khong_co":
        return False, "không có kenh.yaml"
    if ct == "tat_han":
        return False, "chủ tắt hẳn (duy_tri_trang_chu: false)"
    so, dt = so or {}, dt or {}
    if so.get("trang_thai") == "can_nguoi":
        moc = float(so.get("can_nguoi_luc") or 0)
        if kiem_dom_luc and kiem_dom_luc > moc:
            return True, "Chrome kênh đã kiểm lại đạt sau lần cần người — đo lại"
        return False, "chờ người: " + str(so.get("ly_do") or "")[:100]
    che = che_do_hien(so, dt, ct)
    if che == "nuoi_dau":
        return False, "đang nuôi lần đầu (phiên nuôi tự đo)"
    hl = lan_do_hop_le(so.get("lan_do"))
    if not hl:
        return True, "chưa đo trang chủ lần nào"
    cuoi = hl[-1]
    duoi = che == "nuoi_lai" or not danh_gia_do(cuoi, hl[:-1], _luc_so(cuoi.get("luc")) or luc)["dat"]
    han = NGAY_DO_DUOI_MUC if duoi else NGAY_DO_DUY_TRI
    tuoi = luc - _luc_so(cuoi.get("luc"))
    if tuoi >= han * 86400:
        return True, "lần đo cuối {0:.0f} ngày trước (nhịp {1} ngày{2})".format(tuoi / 86400, han,
                                                                             ", lần trước dưới mục tiêu" if duoi else "")
    return False, "đo lại sau {0} (nhịp {1} ngày)".format(
        time.strftime("%d/%m %H:%M", time.localtime(_luc_so(cuoi.get("luc")) + han * 86400)), han)


def gop_hai_lan(o1: list, nl1: dict, o2: list, nl2: dict) -> dict:
    """Gộp 2 lần đọc trang chủ (nạp lại giữa hai lần): % gộp trên các ô KHÁC NHAU + % từng lần, độ chênh, tỉ lệ ô trùng."""
    def mot(o, nl):
        k = phan_tram([nl[x["id"]] for x in o if x["id"] in nl])
        return {"n": k["n"], "pct_chu_de": k["pct_chu_de"], "pct_ngach": k["pct_ngach"]}
    gop, vi_du = {}, []
    for o, nl in ((o1, nl1), (o2, nl2)):
        for x in o:
            if x["id"] in nl and x["id"] not in gop:
                gop[x["id"]] = nl[x["id"]]
                if nl[x["id"]] == "lac_de":
                    vi_du.append("{0} — {1}".format(str(x.get("kenh") or "")[:25], str(x.get("tieu_de") or "")[:60]))
    ket = phan_tram(list(gop.values()))
    d1, d2 = mot(o1, nl1), mot(o2, nl2)
    a, b = {x["id"] for x in o1}, {x["id"] for x in o2}
    ket.update(doc=[d1, d2], vi_du_lac_de=vi_du, trung_o=round(len(a & b) / float(max(1, len(a | b))), 2),
               chenh_chu_de=round(abs(d1["pct_chu_de"] - d2["pct_chu_de"]), 1) if d1["n"] and d2["n"] else None)
    return ket


def do_khop_nhan(nl_a: dict, nl_b: dict) -> dict:
    """Độ ổn định của THƯỚC LLM: hai lần phân loại cùng các ô → {n, khop (0..1), lech: [(id, a, b)]}."""
    chung = [k for k in nl_a if k in nl_b]
    lech = [(k, nl_a[k], nl_b[k]) for k in chung if nl_a[k] != nl_b[k]]
    return {"n": len(chung), "khop": round(1 - len(lech) / float(max(1, len(chung))), 3) if chung else None,
            "lech": lech[:10]}


_LOAI_BO = {"quang_cao": "quảng cáo", "mix": "Mix/danh sách phát", "khong_ten": "chưa nạp tiêu đề"}


def loc_o_do(o: list) -> tuple:
    """(ô video thường, {loại bị bỏ: số}). Ô quảng cáo và ô Mix/danh sách (`&list=`) không phải video của một kênh
    — không vào thước, không bấm "Không quan tâm". Shorts (`/shorts/`) vốn không được đọc."""
    ra, bo = [], {}
    for x in o or []:
        l = x.get("loai") or "video"
        if l == "video" and x.get("id") and not str(x.get("tieu_de") or "").strip():
            l = "khong_ten"             # ô chưa nạp tiêu đề: không phân loại được theo nghĩa
        if l in _LOAI_BO:
            bo[l] = bo.get(l, 0) + 1
        elif x.get("id"):
            ra.append(x)
    return ra, bo


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
            "ngon_ngu": _yaml_chu(nd, "ngon_ngu").split("#")[0].strip().strip('"').strip("'"),
            "nuoi_tho": _yaml_chu(nd, "nuoi_trang_chu").split("#")[0].strip().lower(),
            "duy_tri": _yaml_chu(nd, "duy_tri_trang_chu").split("#")[0].strip().lower(),
            "bat": _yaml_chu(nd, "nuoi_trang_chu").lower() == "true"}


def cong_tac(kenh: str, goc: str = GOC_TOOL, so: dict = None) -> str:
    """Công tắc CHỦ (kenh.yaml) cho trang chủ: bat | may_tat | chu_tat | tat_han | khong_co.
    false mà sổ có `da_tat_yaml` = CHÍNH máy ghi lúc đạt (bản trước 19/10) → máy vẫn được duy trì + tự nuôi lại."""
    cfg = doc_kenh_yaml(kenh, goc)
    if not cfg:
        return "khong_co"
    if cfg.get("duy_tri") == "false":
        return "tat_han"
    if cfg.get("bat"):
        return "bat"
    if cfg.get("nuoi_tho") == "false" and (so or {}).get("da_tat_yaml"):
        return "may_tat"
    return "chu_tat"


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


def _doc_json(duong: str):
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _goi_thang(kenh: str, goc: str = GOC_TOOL) -> set:
    """Mã lượt (`0031`) của các video THẮNG của kênh: lượt xem ≥ trung vị kênh (bảng nhóm), cần ≥ 3 video có số."""
    import glob
    xem = {}
    for d in glob.glob(os.path.join(goc, "CHANNEL", "_NHOM", "*", "bang-nhom.csv")):
        for r in _doc_csv(d):
            if (r.get("Kênh") or "") == kenh:
                try:
                    xem[r.get("Mã video") or ""] = float(str(r.get("Lượt xem") or "0").replace(",", ""))
                except ValueError:
                    pass
    so = sorted(v for v in xem.values() if v > 0)
    if len(so) < 3:
        return set()
    tv = so[len(so) // 2]
    ra = set()
    for r in _doc_csv(os.path.join(goc, "CHANNEL", kenh, "ke-hoach-dang", "ke-hoach.csv")):
        vid, ma = (r.get("Video ID") or "").strip(), (r.get("Mã gói") or "").strip()
        if vid and xem.get(vid, 0) >= tv and ma.startswith(kenh + "-"):
            ra.add(ma[len(kenh) + 1:])
    return ra


def nguon_ngach_hep(kenh: str, goc: str = GOC_TOOL) -> dict:
    """{video_id: trọng số} — nguồn NGÁCH HẸP cho phiên nuôi lại (19/10): bài biên tập viên đã chọn theo NGHĨA trong
    tuyến của kênh (`danh-sach-chon.json`, ×3), nguồn kênh đã làm (`giu-nguon/`, ×3; nguồn của video THẮNG ×4), nguồn
    kênh anh em CÙNG TỆP đã giữ (kho loại trừ của nhóm, ×2). Đọc hỏng phần nào thì bỏ phần đó."""
    ra = {}
    cfg = doc_kenh_yaml(kenh, goc)

    def them(vid, w):
        if vid:
            ra[vid] = max(ra.get(vid, 1), w)
    d = _doc_json(os.path.join(_thu_muc_nc(kenh, goc) or "-", "danh-sach-chon.json")) or {}
    for khoa in ("moi", "but", "vuot"):
        for x in d.get(khoa) or [] if isinstance(d, dict) else []:
            if isinstance(x, dict):
                them(ma_video(x.get("link")), 3)
    nhom, tep = cfg.get("nhom"), cfg.get("tep")
    thu = os.path.join(goc, "CHANNEL", "_NHOM", nhom or "-", "nghien-cuu", "giu-nguon")
    try:
        tep_ds = sorted(os.listdir(thu)) if nhom else []
    except OSError:
        tep_ds = []
    thang, tep_k = _goi_thang(kenh, goc) if tep_ds else set(), {}
    for t in tep_ds:
        x = _doc_json(os.path.join(thu, t)) or {}
        k, vid = str(x.get("kenh") or ""), str(x.get("ma") or "")
        if k == kenh:
            them(vid, 4 if str(x.get("ma_luot") or "") in thang else 3)
        elif k and tep:
            if k not in tep_k:
                tep_k[k] = doc_kenh_yaml(k, goc).get("tep", "")
            if tep_k[k] == tep:
                them(vid, 2)
    return ra


def doc_ung_vien(kenh: str, hom_nay: date, goc: str = GOC_TOOL, hep: dict = None) -> list:
    """Ứng viên từ kho đối thủ: kho khởi động + content của kênh (= NGÁCH) và content
    của các kênh khác trong nhóm (NGÁCH nếu cùng tuyến `tep`, còn lại = chủ đề rộng,
    bỏ tuyến 'khac'). Chỉ video của đối thủ hợp lệ, <= 60 ngày.
    `hep` ({id: trọng số}, `nguon_ngach_hep`): ứng viên trong đó = NGÁCH + `uu_tien` (nuôi lại nghiêng ngách hẹp)."""
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
    for vid, w in (hep or {}).items():
        if vid in ra:
            ra[vid].update(ngach=True, uu_tien=w)
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


def doc_so(kenh: str, thu_muc: str = None) -> dict:
    try:
        with open(os.path.join(thu_muc, kenh + ".json") if thu_muc else duong_so(kenh), "r", encoding="utf-8") as tep:
            so = json.load(tep)
        base = so_moi(kenh)
        base.update(so)
        return base
    except (OSError, ValueError):
        return so_moi(kenh)


def duong_duy_tri(kenh: str, thu_muc: str = None) -> str:
    return os.path.join(thu_muc or THU_MUC_SO, kenh + ".duy-tri.json")


def doc_duy_tri(kenh: str, thu_muc: str = None) -> dict:
    d = _doc_json(duong_duy_tri(kenh, thu_muc))
    return dict(duy_tri_moi(kenh), **d) if isinstance(d, dict) else duy_tri_moi(kenh)


def luu_duy_tri(dt: dict) -> None:
    os.makedirs(THU_MUC_SO, exist_ok=True)
    d = duong_duy_tri(dt["kenh"])
    with open(d + ".tam", "w", encoding="utf-8") as tep:
        json.dump(dt, tep, ensure_ascii=False, indent=1)
    os.replace(d + ".tam", d)


def cac_kenh_nuoi_lai() -> list:
    """Kênh có sổ duy trì `che_do: nuoi_lai` (máy tự nuôi lại; công tắc kiểm ở `kenh_den_luot`)."""
    try:
        ten = sorted(f[:-len(".duy-tri.json")] for f in os.listdir(THU_MUC_SO) if f.endswith(".duy-tri.json"))
    except OSError:
        return []
    return [k for k in ten if doc_duy_tri(k).get("che_do") == "nuoi_lai"]


def tom_tat_duy_tri(kenh: str, goc: str = GOC_TOOL, luc: float = None, thu_muc: str = None) -> dict:
    """Một kênh cho bảng 8790 / Tự kiểm / skill: {che_do, nhan, cong_tac, pct_chu_de, pct_ngach, ngach_tot, luc_do,
    den_han, ly_do_han, dat, bao_dong, phien_nuoi_lai, ngay_nuoi_lai, can_nguoi, tt, cau}. Chỉ đọc đĩa.
    tt: dat | thu_lai (máy đang nuôi lại) | cho (chờ đo / chưa đo) | nguoi (cần chủ: đăng nhập, hoặc chủ đang tắt nuôi)."""
    luc = time.time() if luc is None else luc
    thu_muc = thu_muc or os.path.join(goc, "vm", "logs", "nuoi-trang-chu")
    so, dt = doc_so(kenh, thu_muc), doc_duy_tri(kenh, thu_muc)
    ct = cong_tac(kenh, goc, so)
    che = che_do_hien(so, dt, ct)
    hl = lan_do_hop_le(so.get("lan_do"))
    cuoi = hl[-1] if hl else {}
    dg = danh_gia_do(cuoi, hl[:-1], _luc_so(cuoi.get("luc")) or luc) if cuoi else {}
    han, ly_han = den_han_do(so, dt, luc, ct)
    ngay_nl = (luc - float(dt.get("tu_luc") or luc)) / 86400.0 if che == "nuoi_lai" else 0.0
    ra = {"kenh": kenh, "che_do": che, "nhan": NHAN_CHE_DO.get(che, che), "cong_tac": ct,
          "pct_chu_de": cuoi.get("pct_chu_de"), "pct_ngach": cuoi.get("pct_ngach"), "ngach_tot": dg.get("ngach_tot"),
          "luc_do": cuoi.get("luc") or "", "den_han": han, "ly_do_han": ly_han, "dat": dg.get("dat"),
          "ly_do": dg.get("ly_do") or "", "bao_dong": dt.get("bao_dong") or "", "phien_nuoi_lai": int(dt.get("phien_nuoi_lai") or 0),
          "ngay_nuoi_lai": round(ngay_nl, 1), "can_nguoi": so.get("trang_thai") == "can_nguoi",
          "vi_du_lac_de": list(cuoi.get("vi_du_lac_de") or [])[:3], "cham": bool(dt.get("cham"))}
    if ct in ("khong_co", "tat_han"):
        ra.update(tt="", cau="chủ tắt hẳn duy trì trang chủ" if ct == "tat_han" else "")
    elif ra["can_nguoi"]:
        ra.update(tt="nguoi", cau="cần người: " + str(so.get("ly_do") or "")[:120])
    elif not cuoi:
        ra.update(tt="cho", cau="chưa đo trang chủ lần nào — " + ly_han)
    elif che == "nuoi_lai" and not duoc_nuoi_lai(ct):
        ra.update(tt="nguoi", cau="trang chủ {0:.0f}% chủ đề · {1:.0f}% ngách ({2}) — chủ đang tắt nuôi_trang_chu, máy chỉ đo".format(
            float(cuoi.get("pct_chu_de") or 0), float(cuoi.get("pct_ngach") or 0), dg.get("ly_do")))
    elif che == "nuoi_lai":
        ra.update(tt="thu_lai", cau="trang chủ {0:.0f}% chủ đề · {1:.0f}% ngách — máy tự nuôi lại {2:.0f} ngày, {3} phiên{4}".format(
            float(cuoi.get("pct_chu_de") or 0), float(cuoi.get("pct_ngach") or 0), ngay_nl, ra["phien_nuoi_lai"],
            " · đã báo động, nuôi chậm" if dt.get("bao_dong") else ""))
    elif che == "nuoi_dau":
        ra.update(tt="thu_lai", cau="đang nuôi lần đầu: {0:.0f}% chủ đề".format(float(cuoi.get("pct_chu_de") or 0)))
    else:
        cu = luc - _luc_so(cuoi.get("luc")) > (NGAY_DO_DUY_TRI + 3) * 86400
        ra.update(tt="cho" if cu else ("dat" if dg.get("dat") else "cho"),
                  cau="trang chủ {0:.0f}% chủ đề · {1:.0f}% ngách lúc {2} — {3}".format(
                      float(cuoi.get("pct_chu_de") or 0), float(cuoi.get("pct_ngach") or 0), cuoi.get("luc"),
                      "quá hạn đo lại" if cu else ly_han))
    return ra


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
          "- Tiêu chí đạt: % chủ đề > {0:.0f}% (1 lần đo); % ngách chỉ để xem".format(DAT_PCT_CHU_DE)]]
    dt = doc_duy_tri(so["kenh"])
    if dt.get("che_do"):
        dc = dt.get("do_cuoi") or {}
        d[0] += ["- Duy trì: **{0}**{1} · lần đo duy trì cuối {2}: {3}{4}".format(
            NHAN_CHE_DO.get(dt["che_do"], dt["che_do"]), " (nhịp chậm, đã báo động)" if dt.get("cham") else "",
            dc.get("luc") or "-", dc.get("ly_do") or "-",
            " · nuôi lại {0} phiên".format(dt.get("phien_nuoi_lai") or 0) if dt["che_do"] == "nuoi_lai" else "")]
    d[0] += ["- Thước duy trì: % chủ đề ≥ {0:.0f}% và % ngách không tụt (< {1}×tốt nhất {2} ngày, < {3:.0f}%); đo lại {4} ngày "
             "(dưới mục tiêu: {5} ngày); 2 lần đạt liền mới về duy trì".format(
                 DUY_TRI_PCT_CHU_DE, HE_SO_NGACH_TUT, NGAY_NGACH_TOT, NGACH_SAN_PCT, NGAY_DO_DUY_TRI, NGAY_DO_DUOI_MUC),
             "", "## Các lần đo", "", "| Lúc | Nguồn | Số ô | % chủ đề | % ngách | Chênh 2 lần đọc | Đạt |",
             "|---|---|---|---|---|---|---|"]
    for x in so.get("lan_do", [])[-40:]:
        d[0].append("| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            x["luc"], "đo" if x.get("nguon") == "duy_tri" else "phiên", x["n"], x["pct_chu_de"], x["pct_ngach"],
            "-" if x.get("chenh_chu_de") is None else x["chenh_chu_de"], "có" if x["dat"] else "chưa"))
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
    return os.path.join(thu_muc or THU_MUC_KHOA or THU_MUC_SO, ten + ".khoa")


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
        ten = [f[:-5] for f in os.listdir(thu_muc or THU_MUC_KHOA or THU_MUC_SO) if f.endswith(".khoa") and not f.startswith("_")]
    except OSError:
        return []
    return [k for k in ten if chu_khoa(k, thu_muc)]


def co_dung(kenh: str, thu_muc: str = None) -> bool:
    """Agent đã ghi cờ `<kênh>.dung` (có việc đăng cần Chrome kênh) — phải đóng Chrome ngay."""
    return os.path.isfile(os.path.join(thu_muc or THU_MUC_KHOA or THU_MUC_SO, kenh + ".dung"))


def xoa_co_dung(kenh: str, thu_muc: str = None) -> None:
    try:
        os.remove(os.path.join(thu_muc or THU_MUC_KHOA or THU_MUC_SO, kenh + ".dung"))
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
    bat = cac_kenh_bat(goc)
    for k in list(dict.fromkeys(bat + cac_kenh_nuoi_lai())):
        if k in dang:
            ly[k] = "đang nuôi"
            continue
        so, dt = doc_so(k), doc_duy_tri(k)
        if k not in bat and not duoc_nuoi_lai(cong_tac(k, goc, so)):
            ly[k] = "trang chủ dưới mục tiêu nhưng chủ đang tắt nuoi_trang_chu — chỉ đo"
            continue
        so_v, r = quyet_dinh(so, luc, NGAN_SACH_PHIEN_PHUT, dt=dt)
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
    if not str(tieu_de or "").strip():
        return False                    # 19/10: ô chưa nạp tiêu đề KHÔNG phải "khác ngôn ngữ" (từng bị bấm Không quan tâm mù)
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
            "Thêm trường \"tam_ly\": true nếu video NÓI VỀ tâm lý học / hiểu người / não bộ (bất kể ngách hay ngôn ngữ), "
            "false nếu hoàn toàn không phải (nấu ăn, game, tin tức, nhạc…).\n"
            "Danh sách (số|tiêu đề|kênh):\n{1}\n"
            "Chỉ trả JSON thuần: [{{\"i\":1,\"nhan\":\"dung_ngach\",\"tam_ly\":true}}, ...] đủ {2} phần tử.").format(mo_ta, ds, len(lo))
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
                if isinstance(x.get("tam_ly"), bool):
                    cache["tl:" + o["id"]] = x["tam_ly"]
    return ra


def phan_loai_bau(goi, mo_ta: str, cac_o: list, cache: dict, bo_cache: bool = False) -> tuple:
    """Phân loại cho ĐO DUY TRÌ — thước LLM ổn định hơn (19/10: hai lượt phân loại cùng 28 ô chỉ khớp 82%, % chủ đề lệch
    7 điểm): ô chưa có trong cache được phân loại HAI lượt độc lập; lệch nhau thì lượt BA phân xử (đa số; ba nhãn khác
    nhau → `dung_chu_de`, nhãn giữa). Ghi cache. Trả ({id: nhãn}, {n, khop, lech} của hai lượt đầu).
    `bo_cache`: phân loại lại MỌI ô (kiểm độ ổn định của thước)."""
    ra = {} if bo_cache else {o["id"]: cache[o["id"]] for o in cac_o if cache.get(o["id"]) in NHAN_HOP_LE}
    chua = [o for o in cac_o if o["id"] not in ra]
    if not chua:
        return ra, {"n": 0, "khop": None, "lech": []}
    c1, c2, c3 = {}, {}, {}
    a, b = phan_loai(goi, mo_ta, chua, c1), phan_loai(goi, mo_ta, chua, c2)
    lech = [o for o in chua if o["id"] in a and o["id"] in b and a[o["id"]] != b[o["id"]]]
    d = phan_loai(goi, mo_ta, lech, c3) if lech else {}
    for o in chua:
        i = o["id"]
        v = [x for x in (a.get(i), b.get(i)) if x]
        if not v:
            continue
        if len(v) == 1 or v[0] == v[1]:
            nhan = v[0]
        elif d.get(i) in v:
            nhan = d[i]
        else:
            nhan = "dung_chu_de" if d.get(i) else v[0]
        ra[i] = cache[i] = nhan
        tl = [x for x in (c1.get("tl:" + i), c2.get("tl:" + i), c3.get("tl:" + i)) if isinstance(x, bool)]
        if tl:
            cache["tl:" + i] = max(set(tl), key=tl.count)
    return ra, do_khop_nhan(a, b)


def chac_lac_de(o: dict, cache: dict) -> bool:
    """Được bấm "Không quan tâm" KHÔNG — chặt hơn nhãn `lac_de` (04/10/2026: máy từng bấm cả video tâm lý tiếng
    Nhật bị LLM xếp lệch ngách). CHỈ khi: khác ngôn ngữ/quốc gia (mã), HOẶC LLM khẳng định KHÔNG phải tâm lý
    (`tam_ly` False). Chưa biết `tam_ly` → không bấm (an toàn: bỏ sót hơn bấm nhầm)."""
    vid = o.get("id")
    if not vid:
        return False
    if sai_ngon_ngu(o.get("tieu_de")):
        return True
    return cache.get(vid) == "lac_de" and cache.get("tl:" + vid) is False


# ═══════════════════════════ TRÌNH DUYỆT (CDP) ══════════════════════════════
_JS_O = r"""(() => {
  const bd = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const ra = [], thay = new Set();
  const QC = 'ytd-ad-slot-renderer, ytd-in-feed-ad-layout-renderer, ytd-display-ad-renderer, ytd-promoted-video-renderer, ' +
             'ytd-promoted-sparkles-web-renderer, ad-badge-view-model, feed-ad-metadata-view-model';
  for (const a of document.querySelectorAll('a[href*="/watch?v="]')) {
    const href = a.getAttribute('href') || '';
    const m = /[?&]v=([\w-]{11})/.exec(href);
    if (!m || thay.has(m[1])) continue;
    const o = a.closest('ytd-rich-item-renderer') || a.closest('yt-lockup-view-model') || a.closest('ytd-video-renderer');
    if (!o) continue;
    // 19/10: ô quảng cáo (khung QC nằm TRONG ô, không phải tổ tiên) và ô Mix/danh sách (&list=) đánh dấu để bỏ khỏi thước
    const loai = (a.closest(QC) || o.closest(QC) || o.querySelector(QC)) ? 'quang_cao' : (/[?&](list|start_radio)=/.test(href) ? 'mix' : 'video');
    if (loai !== 'video') { if (!thay.has(loai + m[1])) { thay.add(loai + m[1]); ra.push({id: m[1], loai: loai, tieu_de: '', kenh: '', meta: ''}); } continue; }
    let ti = '';
    const h = o.querySelector('#video-title, h3 a, h3');
    if (h) ti = bd(h.getAttribute('title') || h.innerText || h.textContent);
    if (!ti) ti = bd(a.getAttribute('title') || a.getAttribute('aria-label') || a.innerText);
    const c = o.querySelector('ytd-channel-name a, #channel-name a, a[href^="/@"], a[href*="/channel/"], .yt-content-metadata-view-model__metadata-text');
    thay.add(m[1]);
    ra.push({id: m[1], loai: 'video', tieu_de: ti, kenh: bd(c ? c.innerText : ''), meta: bd(o.innerText).slice(0, 160)});
  }
  return ra;
})()"""

_JS_KIEM_TRANG = r"""(() => {
  const t = ((document.body && document.body.innerText) || '').toLowerCase();
  const u = location.href;
  if (/consent\.youtube|consent\.google/.test(u)) return 'dong_y';
  if (/google\.com\/sorry|recaptcha/.test(u) || /unusual traffic|not a robot|not a bot|ロボットではありません|ボットでない|自動(送信|化)されたトラフィック|로봇이 아닙니다|비정상적인 트래픽|người máy|rô-bốt|lưu lượng truy cập bất thường/.test(t)) return 'captcha';
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
        self.bo_qua = {}

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
    het, o, bo = time.monotonic() + cho_giay, [], {}
    while time.monotonic() < het:
        o, bo = loc_o_do(tab.js(_JS_O) or [])
        if len(o) >= can:
            break
        if len(o) >= toi_thieu:
            tab.cuon(700)
        tab.ngu(1.5)
    tab.bo_qua = bo                                         # ô quảng cáo / Mix đã bỏ khỏi thước (ghi vào lần đo)
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


def goi_giu_vi_bia(kenh: str, goc_tool: str = "") -> set:
    """Mã gói chờ đăng mà máy đăng SẼ GIỮ (bìa chưa có dấu cổng chữ — `may_dang_dom` không tải). 18/10/2026: TL4-T7-K2
    giữ gói vì bìa thiếu dấu → thiết lập kênh "nhường gói chờ tải lên" mỗi 10 phút suốt ngày (64 lần) mà gói ấy không
    bao giờ tải được tới khi S05 đóng dấu. Gói bị giữ không phải việc đăng đang chờ — không nhường nó."""
    try:
        goc_tool = goc_tool or GOC_TOOL
        if goc_tool not in sys.path:
            sys.path.insert(0, goc_tool)
        from core import cong_chu  # noqa: PLC0415
        return {g["ma"] for g in cong_chu.goi_cho_dang(goc_tool, kenh) if not g.get("anh") or cong_chu.kiem_dau(g["anh"])}
    except Exception:  # noqa: BLE001 — đọc hỏng: không lọc gì (giữ hành vi cũ)
        return set()


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
            ma_cho = agent.ma_can_tai_bo_sung(nguon_tool._tai_csv(ch, kenh), kenh, so_id, luc)   # noqa: SLF001
            ma_cho = [m for m in ma_cho or [] if m not in goi_giu_vi_bia(kenh)]
            if ma_cho:
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


def tra_ngon_ngu(cdp, kenh: str, ghi, ngon_ngu: str = "") -> str:
    """Giao diện YouTube đúng ngôn ngữ kênh trước khi đọc trang chủ: TRẢ hl tạm của máy DOM chết giữa chừng
    (`ngon_ngu_tam.tra`), rồi cookie PREF còn `hl` khác ngôn ngữ kênh (vd `vi`) thì đặt lại `hl=<kênh>` + đọc lại.
    Trả hl sau cùng ("" = không có hl, theo ngôn ngữ tài khoản). Lỗi → ghi log, không chặn phiên."""
    ng = str(ngon_ngu or NGON_NGU_KENH or "").strip().lower().split("-")[0]
    try:
        if GOC not in sys.path:
            sys.path.insert(0, GOC)
        import ngon_ngu_tam as nnt                          # noqa: PLC0415
        nnt.tra(cdp, kenh, ghi)
        goc = nnt._pref_cookie(cdp)                         # noqa: SLF001
        hl = nnt.hl_cua(goc.get("value", ""))
        if hl and ng and hl.lower().split("-")[0] != ng:
            nnt._dat_pref(cdp, goc, nnt.pref_voi_hl(goc.get("value", ""), ng))   # noqa: SLF001
            sau = nnt.hl_cua(nnt._pref_cookie(cdp).get("value", ""))             # noqa: SLF001
            ghi("ngôn ngữ giao diện {0}: hl={1} → hl={2} (đọc lại {3})".format(kenh, hl, ng, sau or "-"))
            return sau
        return hl
    except Exception as loi:  # noqa: BLE001
        ghi("ngôn ngữ giao diện {0}: không kiểm/trả được ({1})".format(kenh, str(loi)[:120]))
        return "?"


def ghi_nao(kenh: str, loai: str, noi_dung: str, so_lieu: dict = None, khoa: str = "") -> None:
    """Sự kiện não bộ phận `doi-thu` (trang chủ là nguồn đối thủ/xu hướng). Hỏng không bao giờ làm vỡ phiên."""
    try:
        if GOC_TOOL not in sys.path:
            sys.path.insert(0, GOC_TOOL)
        from core import nao_bo_phan                        # noqa: PLC0415
        nao_bo_phan.ghi(GOC_TOOL, "doi-thu", loai, kenh=kenh, noi_dung=noi_dung, so=so_lieu or {}, nguon="nuoi_trang_chu",
                        khoa=khoa or "trang-chu|{0}|{1}|{2}".format(kenh, loai, time.strftime("%Y-%m-%d %H:%M")))
    except Exception:  # noqa: BLE001
        pass


def bao_dong_duy_tri(kenh: str, so: dict, dt: dict, loai: str, ghi) -> None:
    """MỘT báo động mỗi đợt nuôi lại (kèm ô lạc đề làm bằng chứng); `khong_hieu_qua` → chuyển nhịp chậm, KHÔNG dừng."""
    hl = lan_do_hop_le(so.get("lan_do"))
    cuoi = hl[-1] if hl else {}
    ngay = (time.time() - float(dt.get("tu_luc") or time.time())) / 86400.0
    tieu = ("Trang chủ kênh {0}: tự nuôi lại {1:.0f} ngày, {2} phiên mà vẫn {3}% đúng chủ đề · {4}% ngách".format(
        kenh, ngay, dt.get("phien_nuoi_lai") or 0, cuoi.get("pct_chu_de"), cuoi.get("pct_ngach"))
        if loai == "khong_hieu_qua" else
        "Trang chủ kênh {0}: dưới mục tiêu {1:.0f} ngày mà máy chỉ chạy được {2} phiên nuôi (bị nhường việc đăng / khe máy)".format(
            kenh, ngay, dt.get("phien_nuoi_lai") or 0))
    chi = ["Lần đo cuối {0}: {1}".format(cuoi.get("luc"), (dt.get("do_cuoi") or {}).get("ly_do") or ""),
           "Các lần đo gần nhất: " + ", ".join("{0}%/{1}%".format(x.get("pct_chu_de"), x.get("pct_ngach")) for x in hl[-6:]),
           "Ví dụ ô lạc đề:"] + ["- " + t for t in (cuoi.get("vi_du_lac_de") or [])[:6]] + [
           "Máy {0} — không dừng. Sổ: vm/logs/nuoi-trang-chu/{1}.md".format(
               "chuyển nuôi CHẬM (nghỉ 60–120', ≤ 20 video/ngày)" if loai == "khong_hieu_qua" else "vẫn thử mỗi khi khe rảnh", kenh)]
    dt["bao_dong"] = "{0}@{1}".format(loai, time.strftime("%Y-%m-%d %H:%M"))
    if loai == "khong_hieu_qua":
        dt["cham"] = True
    luu_duy_tri(dt)
    ghi("BÁO ĐỘNG: " + tieu)
    try:
        if GOC_TOOL not in sys.path:
            sys.path.insert(0, GOC_TOOL)
        from core import bao_dong                           # noqa: PLC0415
        bao_dong.bao_dong("nuoi_trang_chu_" + kenh, tieu, "\n".join(chi)[:3000], kenh=kenh)
    except Exception as loi:  # noqa: BLE001
        ghi("không gửi được báo động: {0}".format(str(loi)[:120]))
    ghi_nao(kenh, "loi", tieu, {"loai": loai, "pct_chu_de": cuoi.get("pct_chu_de"), "pct_ngach": cuoi.get("pct_ngach"),
                                "phien": dt.get("phien_nuoi_lai")}, khoa="trang-chu|{0}|bao|{1}".format(kenh, dt["bao_dong"]))


def sau_lan_do(kenh: str, so: dict, dt: dict, ct: str, ghi, che: str = "") -> tuple:
    """Sau MỖI lần đo hợp lệ (đã `ghi_lan_do`): cập nhật sổ duy trì (trừ khi đang nuôi lần đầu), ghi não, kiểm báo động.
    `che`: chế độ lúc BẮT ĐẦU phiên (phiên nuôi lần đầu vừa đạt → duy trì). Trả (dt mới, sự kiện)."""
    muc = so["lan_do"][-1]
    che = che or che_do_hien(so, dt, ct)
    if che == "nuoi_dau":
        if so.get("trang_thai") != "dat":
            return dt, ""
        dt = dict(dt, che_do="duy_tri", tu_luc=time.time(), ly_do="đạt lần đầu: " + str(so.get("ly_do") or ""))
        sk = "dat_lan_dau"
    else:
        dt = dict(dt, che_do=che)
        dt, sk = cap_nhat_duy_tri(dt, muc, so["lan_do"][:-1], _luc_so(muc.get("luc")) or time.time())
    luu_duy_tri(dt)
    cau = {"duoi_muc": "DƯỚI MỤC TIÊU → {0}".format("máy tự nuôi lại" if duoc_nuoi_lai(ct) else
                                                    "chủ đang tắt nuôi_trang_chu: chỉ đo, hỏi chủ"),
           "ve_duy_tri": "ĐẠT 2 lần liền → về duy trì (đo hằng tuần)", "dat_lan_dau": "đạt lần đầu → duy trì"}.get(sk, "")
    ghi("duy trì {0}: {1} · {2}{3}".format(kenh, NHAN_CHE_DO.get(dt["che_do"], dt["che_do"]),
                                          (dt.get("do_cuoi") or {}).get("ly_do") or muc.get("pct_chu_de"),
                                          (" — " + cau) if cau else ""))
    ghi_nao(kenh, "chon" if sk else "do", "trang chủ {0}% chủ đề · {1}% ngách ({2}){3}".format(
        muc.get("pct_chu_de"), muc.get("pct_ngach"), "đo duy trì" if muc.get("nguon") == "duy_tri" else "trong phiên nuôi",
        (" → " + cau) if cau else ""), {"pct_chu_de": muc.get("pct_chu_de"), "pct_ngach": muc.get("pct_ngach"), "n": muc.get("n"),
                                         "che_do": dt["che_do"], "chenh": muc.get("chenh_chu_de")},
        khoa="trang-chu|{0}|do|{1}|{2}".format(kenh, muc.get("luc"), muc.get("nguon")))
    loai = can_bao_dong(dt, time.time(), ct)
    if loai:
        bao_dong_duy_tri(kenh, so, dt, loai, ghi)
    return dt, sk


def chay_phien(kenh: str, so_video: int, ghi, rng=None, bo_qua_khung: bool = False) -> int:
    rng = rng or random.Random()
    luc0 = time.time()
    so, dt = doc_so(kenh), doc_duy_tri(kenh)
    ct = cong_tac(kenh, GOC_TOOL, so)
    che = che_do_hien(so, dt, ct)
    nuoi_lai = che == "nuoi_lai"
    if nuoi_lai and not duoc_nuoi_lai(ct):
        ghi("bỏ qua: trang chủ dưới mục tiêu nhưng chủ đang tắt nuoi_trang_chu — máy chỉ đo (--do)")
        return MA_KHONG_CAN
    toi_da, ly = quyet_dinh(so, luc0, NGAN_SACH_PHIEN_PHUT, bo_qua_khung, dt=dt)
    if not toi_da:
        ghi("bỏ qua: " + ly)
        return MA_KHONG_CAN if so.get("trang_thai") in ("can_nguoi", "dat") and not nuoi_lai else MA_HOAN
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
    st = {"dt": dt}                                         # sổ duy trì (đổi sau mỗi lần đo)
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
        if nuoi_lai:
            phien["nuoi_lai"] = True
            st["dt"]["phien_nuoi_lai"] = int(st["dt"].get("phien_nuoi_lai") or 0) + 1
            luu_duy_tri(st["dt"])
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
        global NGON_NGU_KENH
        NGON_NGU_KENH = str(doc_kenh_yaml(kenh).get("ngon_ngu") or "ja").strip().lower()
        tra_ngon_ngu(cdp, kenh, ghi)                        # 19/10: giao diện đúng ngôn ngữ kênh trước khi đọc trang chủ
        mo_ta, goi = mo_ta_ngach(kenh), tao_llm()

        def xong() -> bool:
            """Đủ rồi, thôi xem: nuôi lại → đã về duy trì; nuôi lần đầu → đạt 1 lần."""
            return st["dt"].get("che_do") == "duy_tri" if nuoi_lai else so.get("trang_thai") == "dat"

        def dung():
            return ly_do_dung(agent, kenh, time.time())

        def do_va_ghi(o: list, nl: dict, nhan: str) -> None:
            """04/10/2026: ĐO mỗi lần đã đọc + phân loại trang chủ (đầu phiên, giữa phiên, cuối phiên) — trước đây
            chỉ đo cuối phiên, mà phiên hay bị ngắt để nhường việc đăng → nhiều kênh không có lần đo nào."""
            o = o[:SO_O_DO]
            ket = phan_tram([nl[x["id"]] for x in o if x["id"] in nl])
            ket["vi_du_lac_de"] = ["{0} — {1}".format(x["kenh"][:25], x["tieu_de"][:60]) for x in o if nl.get(x["id"]) == "lac_de"]
            if ket["n"] >= TOI_THIEU_O_DO:
                ket["bo_qua"] = dict(getattr(tab, "bo_qua", {}) or {})
                ghi_lan_do(so, ket, time.strftime("%Y-%m-%d %H:%M"), nguon="phien")
                luu_so(so)
                ghi("ĐO ({0}): {1} ô · chủ đề {2}% · ngách {3}% · {4}".format(
                    nhan, ket["n"], ket["pct_chu_de"], ket["pct_ngach"], "ĐẠT" if so["lan_do"][-1]["dat"] else "chưa đạt"))
                for t in ket["vi_du_lac_de"][:5]:
                    ghi("   lạc đề: " + t)
                st["dt"], _sk = sau_lan_do(kenh, so, st["dt"], ct, ghi, che if che == "nuoi_dau" else "")
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
                if nl.get(x["id"]) == "lac_de" and chac_lac_de(x, so["cache"]) and khong_quan_tam(tab, x["id"], ghi):
                    n += 1
                    phien["khong_quan_tam"] += 1
                    ghi("   Không quan tâm: {0} — {1}".format(x["kenh"][:20], x["tieu_de"][:40]))

        # Kiểm trang chủ trước: chưa đăng nhập / CAPTCHA thì dừng ngay. Đọc đủ ô để ĐO luôn đầu phiên.
        o0 = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=30)
        ghi("trang chủ đã đăng nhập, thấy {0} ô video".format(len(o0)))
        nl0 = phan_loai_bau(goi, mo_ta, o0[:SO_O_DO], so["cache"])[0]      # 19/10: ô trang chủ phân loại 2 lượt + phân xử
        do_va_ghi(o0, nl0, "đầu phiên")
        if xong():
            chon_truoc = True
        else:
            chon_truoc = False
            day_lac_de(o0, nl0, KHONG_QUAN_TAM_MOI_LAN * 2)
            luu_so(so)
        hom = datetime.fromtimestamp(luc0).date()
        hep = nguon_ngach_hep(kenh) if nuoi_lai else None    # 19/10: nuôi lại nghiêng NGÁCH HẸP của chính kênh
        ung = doc_ung_vien(kenh, hom, hep=hep)
        tl_ngach = TI_LE_NGACH_NUOI_LAI if nuoi_lai else TI_LE_NGACH
        cam_id, cam_ten = id_video_cua_minh(), ten_kenh_cua_minh()
        chon = chon_video(ung, so["da_xem"], cam_id, cam_ten, so_video * 2, hom, rng, tl_ngach)
        nh = phan_loai(goi, mo_ta, chon, so["cache"])                # LLM loại ô lạc đề theo nghĩa
        chon = [v for v in chon if nh.get(v["id"]) in ("dung_ngach", "dung_chu_de")]
        chon = chon_video([dict(v, ngach=(nh[v["id"]] == "dung_ngach")) for v in chon], (), (), (), so_video, hom, rng,
                          tl_ngach)
        ghi("đã chọn {0} video ({1} đúng ngách{2}) từ {3} ứng viên".format(
            len(chon), sum(1 for v in chon if v["ngach"]),
            ", {0} nguồn ngách hẹp".format(sum(1 for v in chon if v.get("uu_tien"))) if nuoi_lai else "", len(ung)))
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
            nl = phan_loai_bau(goi, mo_ta, o, so["cache"])[0]
            if so_gan >= moc_day:
                so_gan, moc_day = 0, rng.randint(3, 5)
                do_va_ghi(o, nl, "giữa phiên")
                if xong():
                    break
            day_lac_de(o, nl, KHONG_QUAN_TAM_MOI_LAN)
            luu_so(so)
            tab.ngu(rng.uniform(10, 60))
        if not bi_ngat and not xong():
            # Đo cuối phiên: nạp lại trang chủ, ~30 ô đầu, LLM phân loại.
            o = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=40)[:SO_O_DO]
            do_va_ghi(o, phan_loai_bau(goi, mo_ta, o, so["cache"])[0], "cuối phiên")
        phien["ket_qua"] = "bị ngắt (nhường việc đăng/khe nang)" if bi_ngat else "xong"
        if xong():
            # 19/10: KHÔNG ghi kenh.yaml nữa (công tắc của chủ) — máy chuyển sang DUY TRÌ ở `<kênh>.duy-tri.json`
            ghi("*** ĐẠT: {0} — chuyển DUY TRÌ (đo lại mỗi {1} ngày, dưới {2:.0f}% thì tự nuôi lại) ***".format(
                st["dt"].get("ly_do") or so.get("ly_do"), NGAY_DO_DUY_TRI, DUY_TRI_PCT_CHU_DE))
    except CanNguoi as c:
        if so.get("trang_thai") != "can_nguoi":
            so["trang_thai_truoc"] = so.get("trang_thai") or "dang_nuoi"
        so["trang_thai"], so["ly_do"] = "can_nguoi", "cần người xử lý: {0} (không thử lại)".format(c)
        so["can_nguoi_luc"] = time.time()
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
            so["nghi_den_luc"] = phien["ket_thuc_luc"] + nghi_giua_phien(
                rng, bi_ngat or phien["ket_qua"].startswith("hoãn"), cham=bool(st["dt"].get("cham")))
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


def chay_do(kenh: str, ghi, bo_qua_khung: bool = False, on_dinh: bool = False, rng=None) -> int:
    """ĐO-KHÔNG-XEM (duy trì, skill D18): bảo vệ như máy DOM (khung cấm 02–07 + :55–:05, van IPv4, máy đăng dở, việc
    đăng chờ / phiên sắp tới, Chrome kênh đang mở → hoãn) → khoá máy `.khoa-may` (khe nặng, nhường) + khoá Chrome kênh →
    mở Chrome kênh (máy này mở, cuối phiên đóng) → trả giao diện `hl` đúng ngôn ngữ kênh → đọc trang chủ 2 lần (nạp lại)
    → phân loại theo NGHĨA (thước cũ) → ghi lần đo + sổ duy trì. KHÔNG xem video, KHÔNG bấm gì (kể cả Không quan tâm),
    không thích/đăng ký/bình luận/chia sẻ. CAPTCHA / đăng xuất → dừng, `can_nguoi`.
    Mã: 0 đã đo · 10 hoãn · 20 cần người · 30 không cần · 1 lỗi / không đọc đủ ô."""
    rng = rng or random.Random()
    luc0 = time.time()
    so, dt = doc_so(kenh), doc_duy_tri(kenh)
    ct = cong_tac(kenh, GOC_TOOL, so)
    if ct in ("khong_co", "tat_han"):
        ghi("bỏ qua đo: {0}".format("không có kenh.yaml" if ct == "khong_co" else "chủ tắt hẳn (duy_tri_trang_chu: false)"))
        return MA_KHONG_CAN
    if kenh in cac_kenh_dang_nuoi():
        ghi("hoãn đo: kênh {0} đang có phiên nuôi (phiên tự đo)".format(kenh))
        return MA_HOAN
    agent = _nap_agent(ghi)
    try:
        import studio_may_dom as smd                        # noqa: PLC0415 — bảo vệ CHUNG của các máy DOM
        tl = smd.tl
        cfg = tl._cfg_kenh(agent, kenh)                     # noqa: SLF001
        cdp_mod, _cs = tl._nap_cdp()                        # noqa: SLF001
    except Exception as loi:  # noqa: BLE001
        ghi("hoãn đo: không nạp được bảo vệ máy DOM / cấu hình agent: {0}".format(str(loi)[:160]))
        return MA_HOAN
    r = smd.ly_do_hoan(agent, cfg, kenh, luc0, DU_KIEN_DO_PHUT, bo_qua_khung, cdp_mod) or (
        "máy đang bận (việc đăng giữ khe hoặc CPU ≥ 75%)" if khe_nang_ban() else "")
    if r:
        ghi("hoãn đo: " + r)
        return MA_HOAN
    khoa_may = khoa_kenh = False
    cdp = tab = None
    ma = 0
    try:
        if not agent.giu_khoa_may_chung(viec="trang_chu_do", kenh=kenh, uu_tien=smd.UU_TIEN_KHOA):
            raise Hoan("khoá máy (.khoa-may) đang bận — không ép")
        khoa_may = True
        if not giu_khoa(kenh):
            raise Hoan("kênh {0} đang có tiến trình khác giữ khoá Chrome".format(kenh))
        khoa_kenh = True
        xoa_co_dung(kenh)
        r = smd.chrome_dang_mo(agent, cfg, kenh, cdp_mod) or duoc_mo_them(len(cac_kenh_dang_nuoi()) - 1, ram_trong_gb())
        if r:
            raise Hoan(r)
        ch = agent.cau_hinh_kenh(cfg, kenh)
        try:
            agent.ghi_che_do_mat_cao(ch, False)
        except Exception:  # noqa: BLE001
            pass
        try:
            cdp = cdp_mod.ket_noi_kenh(cfg, kenh, nhat_ky=ghi, url_mo="https://www.youtube.com/")   # kiểm van IPv4 sát lúc mở
        except cdp_mod.CdpKhongDung as e:
            raise Hoan("không nối được Chrome kênh: {0} (mã {1})".format(e.ly_do, e.ma))
        ghi("── ĐO TRANG CHỦ (duy trì) {0} — Chrome cổng {1}{2} ──".format(
            kenh, cdp.cong, " (máy này tự mở)" if cdp.tu_mo else " (có sẵn — chỉ tab của mình)"))
        canh_tien_trien.bat_canh(lambda: (cdp_mod.dong_trinh_duyet(cdp) if cdp.tu_mo else cdp.dong()), ghi=ghi)
        tid, sid = cdp.tao_tab("about:blank")
        tab = Tab(cdp, tid, sid, rng)
        global NGON_NGU_KENH
        NGON_NGU_KENH = str(doc_kenh_yaml(kenh).get("ngon_ngu") or "ja").strip().lower()
        hl = tra_ngon_ngu(cdp, kenh, ghi)
        mo_ta, goi = mo_ta_ngach(kenh), tao_llm()

        def kiem_dung():
            if co_dung(kenh):
                raise Hoan("agent cần Chrome kênh (cờ .dung) — dừng đo")
        o1 = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=40)[:SO_O_DO]
        bo = dict(tab.bo_qua)
        kiem_dung()
        nl1, od1 = phan_loai_bau(goi, mo_ta, o1, so["cache"], bo_cache=on_dinh)
        kiem_dung()
        tab.ngu(rng.uniform(4, 9))
        o2 = doc_o_trang_chu(tab, can=SO_O_DO, cho_giay=40)[:SO_O_DO]      # nạp lại: đo độ ổn định của trang
        for k, v in tab.bo_qua.items():
            bo[k] = bo.get(k, 0) + v
        nl2, od2 = phan_loai_bau(goi, mo_ta, o2, so["cache"])
        ket = gop_hai_lan(o1, nl1, o2, nl2)
        ket.update(bo_qua=bo, hl=hl or "-")
        n_od = od1["n"] + od2["n"]
        if n_od:         # độ khớp hai lượt phân loại độc lập (ô mới / --on-dinh: mọi ô) — thước LLM ổn định tới đâu
            khop = ((od1["khop"] or 0) * od1["n"] + (od2["khop"] or 0) * od2["n"]) / float(n_od)
            ket["on_dinh"] = {"n": n_od, "khop": round(khop, 3), "lech": (od1["lech"] + od2["lech"])[:10]}
            ghi("ổn định thước LLM: {0} ô phân loại 2 lượt, khớp {1:.0%} — lệch: {2}".format(
                n_od, khop, ket["on_dinh"]["lech"][:5]))
        if ket["n"] < TOI_THIEU_O_DO:
            ghi("ĐO KHÔNG TÍNH: chỉ phân loại được {0} ô (cần ≥ {1}) — đọc {2}+{3} ô".format(
                ket["n"], TOI_THIEU_O_DO, len(o1), len(o2)))
            ma = 1
        else:
            if so.get("trang_thai") == "can_nguoi":             # trang chủ đọc được = người đã xử lý xong
                so["trang_thai"] = so.pop("trang_thai_truoc", "") or ("dat" if so.get("dat_luc") else "dang_nuoi")
                so["ly_do"] = "hết cần người ({0}): đo lại được trang chủ".format(time.strftime("%Y-%m-%d %H:%M"))
            ghi_lan_do(so, ket, time.strftime("%Y-%m-%d %H:%M"), nguon="duy_tri")
            luu_so(so)
            ghi("ĐO (duy trì): {0} ô khác nhau · chủ đề {1}% · ngách {2}% · lần 1 {3}% / lần 2 {4}% (chênh {5}, trùng ô {6}) · "
                "bỏ {7}".format(ket["n"], ket["pct_chu_de"], ket["pct_ngach"], ket["doc"][0]["pct_chu_de"],
                                ket["doc"][1]["pct_chu_de"], ket["chenh_chu_de"], ket["trung_o"], bo or "0"))
            for t in ket["vi_du_lac_de"][:5]:
                ghi("   lạc đề: " + t)
            sau_lan_do(kenh, so, dt, ct, ghi)
    except CanNguoi as c:
        if so.get("trang_thai") != "can_nguoi":
            so["trang_thai_truoc"] = so.get("trang_thai") or "dang_nuoi"
        so["trang_thai"], so["ly_do"] = "can_nguoi", "cần người xử lý: {0} (đo duy trì)".format(c)
        so["can_nguoi_luc"] = time.time()
        luu_so(so)
        ghi("DỪNG — {0} (đăng nhập / CAPTCHA là việc của người, máy không gõ mật khẩu)".format(so["ly_do"]))
        ma = MA_CAN_NGUOI
    except Hoan as h:
        ghi("hoãn đo: {0}".format(h))
        ma = MA_HOAN
    except Exception as loi:  # noqa: BLE001
        ghi("ĐO LỖI: {0}".format(str(loi)[:300]))
        ma = 1
    finally:
        try:
            if tab is not None:
                cdp.dong_tab(tab.tid)
            if cdp is not None:
                if cdp.tu_mo:
                    ghi("đóng Chrome kênh {0} (máy này đã mở): {1}".format(
                        kenh, "đã đóng" if cdp_mod.dong_trinh_duyet(cdp) else "CỔNG CHƯA ĐÓNG"))
                    try:
                        smd.tl.don_launcher_mo_coi(kenh, ghi)
                    except Exception:  # noqa: BLE001
                        pass
                else:
                    cdp.dong()
        finally:
            if khoa_kenh:
                xoa_co_dung(kenh)
                nha_khoa(kenh)
            if khoa_may:
                agent.nha_khoa_may_chung()
    return ma


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
    ap.add_argument("--do", action="store_true", help="CHỈ ĐO trang chủ (duy trì): không xem, không bấm gì")
    ap.add_argument("--on-dinh", action="store_true", help="(--do) phân loại lại không cache để đo độ ổn định thước LLM")
    ap.add_argument("--bo-qua-khung", action="store_true", help="(dev, --do) bỏ khung cấm 02–07 + phút :55–:05")
    a = ap.parse_args(argv)
    ghi = _nhat_ky(a.kenh)
    cfg = doc_kenh_yaml(a.kenh)
    if not cfg:
        ghi("không thấy kenh.yaml của {0}".format(a.kenh))
        return 1
    if a.do:
        return chay_do(a.kenh, ghi, bo_qua_khung=a.bo_qua_khung, on_dinh=a.on_dinh)
    so = doc_so(a.kenh)
    ct = cong_tac(a.kenh, GOC_TOOL, so)
    if not (ct == "bat" or (che_do_hien(so, doc_duy_tri(a.kenh), ct) == "nuoi_lai" and duoc_nuoi_lai(ct))):
        ghi("kênh {0}: không bật nuoi_trang_chu và không ở chế độ máy tự nuôi lại ({1}) — không chạy".format(a.kenh, ct))
        return MA_KHONG_CAN
    if a.thu:
        return che_thu(a.kenh, a.so_video, ghi)
    return chay_phien(a.kenh, a.so_video, ghi)


if __name__ == "__main__":
    sys.exit(main())
