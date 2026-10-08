"""Cổng KIỂM CHẤT LƯỢNG đứng TRƯỚC lúc đăng — chạy sau khi bàn giao, trước khi
đánh "Sẵn sàng" vào `ke-hoach-dang/ke-hoach.csv`.

═══ VÌ SAO CÓ MODULE NÀY ═══

`tu_duyet: false` (mặc định) nghĩa là mọi gói bàn giao xong đều để TRỐNG ngày
giờ đăng — chủ dự án tự mở bảng kế hoạch, tự nhìn qua rồi mới gõ giờ vào. Đó
chính là cổng kiểm chất lượng DUY NHẤT đang có: con mắt người.

Muốn bật `tu_duyet: true` (tool tự điền giờ, không ai duyệt lại) thì phải có
một cổng khác đứng thay con mắt ấy — không thì một video lỗi (thiếu tiếng,
ngắn cụt, phụ đề trôi, ảnh bìa méo…) đi thẳng lên kênh thật mà không ai biết
cho tới khi khán giả báo.

Module này LÀ cổng đó: kiểm một gói đã xuất trong `DONE/<kênh>/<mã gói>` bằng
các phép đo rẻ, chạy trên máy, KHÔNG gọi mạng, KHÔNG tốn tiền — dùng chính
FFmpeg mà khâu dựng (`core/auto_khau.py`, khâu 8) đã dùng để ra được video đó.

═══ HAI QUYẾT ĐỊNH LỆCH VỚI YÊU CẦU BAN ĐẦU, VÀ VÌ SAO ═══

1. **Không đòi `1-seo.txt`/`1-tieu-de.txt` nằm TRONG gói.** Soi tám gói thật
   đang chờ trong `DONE/TL1-T7`, `DONE/TL2-T7`, `DONE/TL3-T7` (22–24/09/2026)
   thì thấy: `core/ban_giao_dang.xuat_goi` chỉ chép đúng ba thứ bắt buộc (mp4,
   srt, ảnh bìa) cộng `1-binh-luan.txt` tuỳ chọn — tiêu đề/mô tả/thẻ SEO đã
   được `doc_gioi_thieu()` đọc và GHI THẲNG vào cột "Tiêu đề"/"Mô tả"/"Thẻ SEO"
   của `ke-hoach.csv`, không copy tệp `.txt` riêng nữa (hai gói cũ nhất,
   `TL1-T7-0001`/`0002`, còn tệp ấy vì bàn giao thủ công kiểu cũ, sáu gói còn
   lại thì không). Đòi tệp `.txt` sẽ chặn 6/8 gói THẬT đang chạy tốt chỉ vì một
   quy ước file đã đổi — sai đúng thứ QA cần tránh: chặn nhầm cái ĐANG chạy
   đúng. Nên tiêu đề/mô tả được kiểm từ chính cột kế hoạch (nguồn thật), tệp gì
   nằm trong `DONE/` không quan trọng.

2. **Độ phân giải THẤP hơn cấu hình mới là LỖI; CAO hơn chỉ là CẢNH BÁO.**
   Đo cùng ngày: 7/8 video thật đang là 3840×2160 dù `kenh.yaml` cả ba kênh đều
   khai `do_phan_giai: 1080p` — nhiều khả năng gói dựng TRƯỚC khi khoá này
   được thêm vào, và khâu dựng vốn bỏ qua nếu `8-video.mp4` đã có (xem
   `_khau_dung.soi_lai` trong `auto_khau.py`) nên không tự dựng lại theo cấu
   hình mới. Cao hơn cấu hình không hại người xem (xem lý do trong
   `core/nang_anh.py`: nét thêm ra là máy đoán, cái được nằm ở bộ mã hoá của
   YouTube) — chặn đăng vì lý do này là bắt sản xuất lại một video vốn xem tốt.
   Thấp hơn cấu hình (vd 720p khi kênh xin 1080p) mới thật sự là hình mờ hơn
   người xem sẽ thấy, nên mới chặn.

Chạy thử trên tám gói thật xác nhận đúng phỏng đoán: xem báo cáo trong
`NHAT-KY-PHAT-TRIEN.md` và `workspace/ban-va/2026-09-26-qa-truoc-dang/`.

═══ CHỦ ĐÍCH KHÔNG GIẢI MÃ TOÀN BỘ VIDEO ═══

`core/auto_khau._loi_giai_ma` giải mã CẢ CLIP trước khi ghép (khâu 8) vì đó là
clip THÔ tải thẳng từ nhà cung cấp — chỗ đã từng cụt giữa chừng dù khai đủ
byte (xem docstring `_kiem_media`). `8-video.mp4` ở đây thì khác: nó vừa được
chính FFmpeg trên máy này MÃ HOÁ LẠI (ghép + đốt phụ đề + `lam_sach_video`),
nên rủi ro "cụt giữa chừng" thấp hơn hẳn — cái cần bắt ở đây là "mở được đầu
tệp", không phải "đọc được từng khung hình". Giải mã hết một video 15 phút
4K từng đo mất **1 phút 46 giây** trên máy này; nhân với vài kênh mỗi ngày là
phí CPU thật trên VPS đang chạy sản xuất/đăng cùng lúc. Nên mặc định chỉ đọc
tiêu đề tệp (`ffmpeg -i`, dưới một giây) — `giai_ma_day_du=True` vẫn có, để
dùng khi nghi ngờ cụ thể (không mở được ở nơi khác chẳng hạn), không phải hàng
ngày.

═══ ĐEN / ĐỨNG HÌNH: DỪNG Ở CẢNH BÁO ═══

`blackdetect`/`freezedetect` của FFmpeg là phép đo tốt nhưng có thể bắt oan một
cảnh tối/tĩnh mà kịch bản CHỦ Ý làm vậy (video những kênh này toàn cảnh AI vẽ
tĩnh, giữ khung lâu là chuyện thường). Bắt oan mà chặn đăng thì mỗi video lại
phải có người ngồi bấm qua tay — đúng thứ `tu_duyet` sinh ra để tránh. Nên
xếp vào CẢNH BÁO: người xem báo cáo vẫn thấy, nhưng không chặn.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

__all__ = [
    "TEN_TEP_KET_QUA",
    "TEP_VIDEO_CHUAN", "TEP_SRT_CHUAN", "TEP_BINH_LUAN",
    "KetQuaQA", "ThongTinMedia",
    "kiem_thu_muc_goi", "kiem_goi",
    "do_phan_giai_mong_muon",
    "ghi_ket_qua", "bao_qa_hong",
]

#: Tên tệp kết quả QA, đặt cạnh gói trong `DONE/<kênh>/<mã gói>/`.
TEN_TEP_KET_QUA = "qa-loi.txt"

#: CÙNG GIÁ TRỊ với `core.ban_giao_dang.TEP_VIDEO`/`TEP_SRT`/`TEP_BINH_LUAN`.
#: Không `import` thẳng từ đó được: `ban_giao_dang` phải `import` module NÀY để
#: chạy QA sau khi xuất gói — nhập ngược lại là vòng nhập. Sửa tên tệp chuẩn ở
#: một bên thì phải sửa cả bên kia.
TEP_VIDEO_CHUAN = "8-video.mp4"
TEP_SRT_CHUAN = "3-phu-de.srt"
TEP_BINH_LUAN = "1-binh-luan.txt"

#: Tối thiểu YouTube còn coi là HD — mốc sàn cho mọi video, bất kể kênh khai gì.
_RONG_TOI_THIEU, _CAO_TOI_THIEU = 1280, 720
#: YouTube cho tối đa 100 ký tự tiêu đề.
_TIEU_DE_TOI_DA = 100
#: Ảnh bìa: YouTube khuyên dưới 2 MB.
_ANH_BIA_TOI_DA_BYTE = 2 * 1024 * 1024
#: Dung sai tỉ lệ khung hình ảnh bìa quanh 16:9 (ảnh nhà cung cấp trả 1376×768,
#: lệch 16:9 một chút do làm tròn — 2% đủ rộng để không bắt oan số đó).
_DUNG_SAI_TI_LE = 0.02
#: Số giây lấy mẫu ở đầu/cuối video để soi đen/đứng hình — đủ để bắt một đoạn
#: intro/outro hỏng, không đủ dài để soi cả video (đó là việc của khâu dựng).
_GIAY_SOI_DAU_CUOI = 6.0
#: Windows: đừng bật cửa sổ đen mỗi lần gọi FFmpeg — cùng nếp với
#: `core/ffmpeg_goi_san.py`.
_CO_TAO = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class KetQuaQA:
    """Kết quả kiểm một gói. `loi` chặn đăng; `canh_bao` chỉ để đọc."""

    loi: List[str] = field(default_factory=list)
    canh_bao: List[str] = field(default_factory=list)

    @property
    def dat(self) -> bool:
        """Đạt — cho phép đánh "Sẵn sàng". Có cảnh báo vẫn ĐẠT, chỉ lỗi mới chặn."""
        return not self.loi

    def van_ban(self) -> str:
        """Nội dung ghi vào `qa-loi.txt` — tiếng Việt, đọc được ngay không cần tra mã."""
        moc = _dt.datetime.now().strftime("%d/%m/%Y %H:%M")
        dong = ["KIỂM CHẤT LƯỢNG TRƯỚC KHI ĐĂNG — {0}".format(moc),
                "Kết quả: {0}".format(
                    "ĐẠT — cho phép đăng" if self.dat
                    else "CHƯA ĐẠT — chưa đánh Sẵn sàng, chưa cho phép đăng")]
        if self.loi:
            dong.append("")
            dong.append("LỖI (chặn đăng):")
            dong.extend("  - " + m for m in self.loi)
        if self.canh_bao:
            dong.append("")
            dong.append("CẢNH BÁO (không chặn đăng, nên xem lại):")
            dong.extend("  - " + m for m in self.canh_bao)
        return "\n".join(dong) + "\n"


@dataclass
class ThongTinMedia:
    """Những gì đọc được từ đầu tệp video bằng `ffmpeg -i` (không giải mã)."""

    mo_duoc: bool = False
    giay: float = 0.0
    rong: int = 0
    cao: int = 0
    co_tieng: bool = False


# ── Tìm tệp trong gói ─────────────────────────────────────────────────────────


def _liet_ke(thu_muc: str) -> List[str]:
    try:
        return os.listdir(thu_muc)
    except OSError:
        return []


def _tim_mot_tep(thu_muc: str, ten_chuan: str, duoi: Sequence[str],
                 loai_tru: Sequence[str] = ()) -> Tuple[str, Optional[str]]:
    """Trả `(đường dẫn, cảnh báo hoặc None)`. Ưu tiên tên chuẩn của bàn giao
    hiện tại; gói dựng theo quy ước cũ (tên tệp = tiêu đề video) thì nhận đại
    tệp duy nhất cùng đuôi. Nhiều hơn một ứng viên thì chọn tệp NẶNG nhất
    (nhiều khả năng là bản chính, không phải bản nháp/cũ) và cảnh báo mơ hồ."""
    chuan = os.path.join(thu_muc, ten_chuan)
    if os.path.isfile(chuan):
        return chuan, None
    ten_loai_tru = {t.lower() for t in loai_tru}
    ung_vien = [t for t in _liet_ke(thu_muc)
                if os.path.splitext(t)[1].lower() in duoi
                and t.lower() not in ten_loai_tru]
    if not ung_vien:
        return "", None
    if len(ung_vien) == 1:
        return os.path.join(thu_muc, ung_vien[0]), None
    ung_vien.sort(key=lambda t: os.path.getsize(os.path.join(thu_muc, t)), reverse=True)
    canh_bao = ("có {0} tệp {1} trong gói, không rõ tệp nào là chính — đang dùng "
               "“{2}” (nặng nhất)").format(len(ung_vien), "/".join(duoi), ung_vien[0])
    return os.path.join(thu_muc, ung_vien[0]), canh_bao


def _tim_video(thu_muc: str) -> Tuple[str, Optional[str]]:
    return _tim_mot_tep(thu_muc, TEP_VIDEO_CHUAN, (".mp4", ".mov", ".mkv"),
                        loai_tru=("8-video.cu.mp4", "9-video-capcut.mp4"))


def _tim_srt(thu_muc: str) -> Tuple[str, Optional[str]]:
    return _tim_mot_tep(thu_muc, TEP_SRT_CHUAN, (".srt",))


def _tim_thumbnail(thu_muc: str) -> Tuple[str, Optional[str]]:
    return _tim_mot_tep(thu_muc, "", (".png", ".jpg", ".jpeg", ".webp"))


# ── Đọc video bằng FFmpeg (không giải mã, chỉ đọc đầu tệp) ───────────────────


def _chay_ffmpeg(ffmpeg: str, tham_so: Sequence[str], *, timeout: float = 60.0) -> str:
    """Chạy FFmpeg, trả `stdout+stderr`. Lỗi/timeout thì trả chuỗi rỗng — nơi
    gọi coi rỗng là "không đọc được", không phân biệt lý do."""
    try:
        ket = subprocess.run(  # noqa: S603
            [ffmpeg, "-hide_banner", *tham_so], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, creationflags=_CO_TAO)
        return (ket.stdout or "") + (ket.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


_MOC_THOI_LUONG = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")
_MOC_KHUNG_HINH = re.compile(r"Video:.*?(\d{2,5})x(\d{2,5})")


def doc_thong_tin_media(ffmpeg: str, duong: str) -> ThongTinMedia:
    """Đọc thời lượng/độ phân giải/có-tiếng-không từ đầu tệp — dưới một giây,
    cùng kỹ thuật `core.auto_khau._dai_clip`/`_clip_co_tieng` (đọc banner
    `ffmpeg -i`, không cần `ffprobe` — máy này không mang theo `ffprobe`, chỉ
    có `ffmpeg`, xem `core/ffmpeg_goi_san.py`)."""
    if not ffmpeg or not os.path.isfile(ffmpeg) or not os.path.isfile(duong):
        return ThongTinMedia()
    tho = _chay_ffmpeg(ffmpeg, ["-i", duong])
    if not tho or "No such file" in tho:
        return ThongTinMedia()
    m_dai = _MOC_THOI_LUONG.search(tho)
    if not m_dai or "Invalid data found" in tho:
        return ThongTinMedia()
    gio, phut, giay_le = m_dai.groups()
    giay = int(gio) * 3600 + int(phut) * 60 + float(giay_le)
    m_khung = _MOC_KHUNG_HINH.search(tho)
    rong, cao = (int(m_khung.group(1)), int(m_khung.group(2))) if m_khung else (0, 0)
    return ThongTinMedia(mo_duoc=True, giay=giay, rong=rong, cao=cao,
                         co_tieng="Audio:" in tho)


def _giai_ma_day_du(ffmpeg: str, duong: str) -> str:
    """Giải mã CẢ tệp (`-xerror`: dừng ở lỗi đầu tiên). Rỗng = lành.

    Cùng kỹ thuật `core.auto_khau._loi_giai_ma` — chỉ dùng khi gọi tường minh
    `giai_ma_day_du=True`, xem lý do "không giải mã toàn bộ mặc định" ở đầu tệp.
    """
    try:
        ket = subprocess.run(  # noqa: S603
            [ffmpeg, "-v", "error", "-xerror", "-i", duong, "-f", "null", "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=1800, creationflags=_CO_TAO)
    except (OSError, subprocess.SubprocessError) as loi:
        return str(loi)
    if ket.returncode == 0:
        return ""
    return (ket.stderr or "").strip()[-300:] or "FFmpeg trả mã {0}".format(ket.returncode)


def _soi_den_dung_hinh(ffmpeg: str, duong: str,
                       giay_mau: float = _GIAY_SOI_DAU_CUOI) -> List[str]:
    """Soi `giay_mau` giây đầu và `giay_mau` giây cuối tìm đoạn ĐEN/ĐỨNG HÌNH.
    Luôn trả CẢNH BÁO, không bao giờ LỖI — xem lý do ở đầu tệp."""
    canh_bao: List[str] = []
    loc = "blackdetect=d=1.0:pic_th=0.98,freezedetect=n=-60dB:d=1.5"
    for nhan, tham_so_dau in (("đầu", ["-t", str(giay_mau)]),
                              ("cuối", ["-sseof", "-{0}".format(giay_mau)])):
        tho = _chay_ffmpeg(
            ffmpeg, [*tham_so_dau, "-i", duong, "-vf", loc, "-an", "-f", "null", "-"],
            timeout=60.0)
        if "black_start" in tho:
            canh_bao.append("có đoạn ĐEN ở {0} video (soi {1:.0f} giây {0})"
                            .format(nhan, giay_mau))
        if "freeze_start" in tho:
            canh_bao.append("có đoạn ĐỨNG HÌNH ở {0} video (soi {1:.0f} giây {0})"
                            .format(nhan, giay_mau))
    return canh_bao


# ── Các phép kiểm riêng lẻ ────────────────────────────────────────────────────


def _kiem_tieu_de(tieu_de: str) -> List[str]:
    tieu_de = str(tieu_de or "")
    if not tieu_de.strip():
        loi = ["chưa có tiêu đề (cột “Tiêu đề” trong kế hoạch đăng đang rỗng)"]
        return loi
    if len(tieu_de) > _TIEU_DE_TOI_DA:
        return ["tiêu đề dài {0} ký tự, vượt {1} ký tự YouTube cho phép"
               .format(len(tieu_de), _TIEU_DE_TOI_DA)]
    return []


def _kiem_do_dai(giay_video: float, phut_muc_tieu: float, chenh_cho_phep: float,
                 do_dai_tu_do: bool, do_dai_theo_goc: bool) -> List[str]:
    if giay_video <= 0:
        return []  # đã báo ở "video không mở được"
    if do_dai_tu_do or do_dai_theo_goc:
        return []  # kênh chủ ý KHÔNG nhắm theo phút cố định — xem core.kenh.Kenh
    if phut_muc_tieu <= 0:
        return []  # kênh chưa khai mục tiêu — không có gì để so
    tol = chenh_cho_phep if chenh_cho_phep > 0 else 0.15  # core.auto_khau.CHENH_CHO_PHEP
    muc_tieu_giay = phut_muc_tieu * 60.0
    duoi, tren = muc_tieu_giay * (1 - tol), muc_tieu_giay * (1 + tol)
    if duoi <= giay_video <= tren:
        return []
    return ["video dài {0:.1f} phút, ngoài khoảng cho phép {1:.1f}–{2:.1f} phút "
           "(mục tiêu {3:.0f} phút ± {4:.0f}%)".format(
               giay_video / 60.0, duoi / 60.0, tren / 60.0, phut_muc_tieu, tol * 100)]


def _kiem_do_phan_giai(rong: int, cao: int, mong_muon: str) -> Tuple[List[str], List[str]]:
    if rong <= 0 or cao <= 0:
        return [], []  # đã báo ở "video không mở được"
    if rong < _RONG_TOI_THIEU or cao < _CAO_TOI_THIEU:
        return (["video {0}x{1} thấp hơn sàn tối thiểu {2}x{3}"
                .format(rong, cao, _RONG_TOI_THIEU, _CAO_TOI_THIEU)], [])
    from .nang_anh import KHUNG  # noqa: PLC0415 — tránh nạp khi không cần

    if not mong_muon or mong_muon == "Giữ nguyên":
        return [], []
    w2, h2 = KHUNG.get(mong_muon, (0, 0))
    if not w2 or not h2 or (rong, cao) == (w2, h2):
        return [], []
    if rong < w2 or cao < h2:
        return (["video {0}x{1} thấp hơn cấu hình kênh yêu cầu ({2}, {3}x{4})"
                .format(rong, cao, mong_muon, w2, h2)], [])
    return ([], ["video {0}x{1} CAO hơn cấu hình kênh yêu cầu ({2}, {3}x{4}) — có thể "
                "gói này dựng trước khi đổi cấu hình; không hại người xem, chỉ nặng "
                "đĩa/băng thông hơn cần".format(rong, cao, mong_muon, w2, h2)])


_MOC_SRT = re.compile(
    r"(\d{1,3}):(\d{1,2}):(\d{1,2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,3}):(\d{1,2}):(\d{1,2})[,.](\d{1,3})")


def _giay_srt(gio: str, phut: str, giay: str, mili: str) -> float:
    return int(gio) * 3600 + int(phut) * 60 + int(giay) + int(mili.ljust(3, "0")[:3]) / 1000.0


def _kiem_srt(duong_srt: str, giay_video: float) -> Tuple[List[str], List[str]]:
    """Parse SRT dễ tính hơn `core.phu_de.doc_srt` một bậc: ở ĐÂY cố tình
    KHÔNG bỏ qua khối rỗng chữ, vì mục đích là BẮT ra đúng khối ấy để báo,
    không phải chữa nó."""
    try:
        with open(duong_srt, "r", encoding="utf-8-sig", errors="replace") as tep:
            noi_dung = tep.read()
    except OSError as loi:
        return (["không đọc được phụ đề: {0}".format(loi)], [])

    khoi_tho = [k for k in re.split(r"\r?\n\s*\r?\n", noi_dung.strip()) if k.strip()]
    if not khoi_tho:
        return (["phụ đề rỗng hoặc không tách được khối nào"], [])

    moc_cuoi = 0.0
    so_khoi_hop_le = 0
    so_dong_trong = 0
    for khoi in khoi_tho:
        dong = [d for d in khoi.splitlines() if d.strip() != ""]
        vi_tri, m = -1, None
        for i, d in enumerate(dong):
            m = _MOC_SRT.search(d)
            if m:
                vi_tri = i
                break
        if not m:
            continue  # dòng số thứ tự lạc/khối hỏng nhẹ — bỏ qua như doc_srt
        so_khoi_hop_le += 1
        moc_cuoi = max(moc_cuoi, _giay_srt(*m.group(5, 6, 7, 8)))
        if not " ".join(dong[vi_tri + 1:]).strip():
            so_dong_trong += 1

    if so_khoi_hop_le == 0:
        return (["phụ đề không có khối nào đọc được mốc thời gian hợp lệ"], [])

    loi: List[str] = []
    canh_bao: List[str] = []
    if so_dong_trong:
        canh_bao.append("phụ đề có {0} khối có mốc thời gian nhưng không có chữ"
                        .format(so_dong_trong))
    # Du di 2 giây cho sai số làm tròn giữa mốc phụ đề và mốc FFmpeg đo được.
    if giay_video > 0 and moc_cuoi > giay_video + 2.0:
        loi.append("mốc phụ đề cuối ({0:.1f} phút) vượt quá độ dài video ({1:.1f} phút)"
                  .format(moc_cuoi / 60.0, giay_video / 60.0))
    return loi, canh_bao


def _kiem_thumbnail(duong_anh: str) -> Tuple[List[str], List[str]]:
    try:
        dung_luong = os.path.getsize(duong_anh)
    except OSError as loi:
        return (["không đọc được ảnh bìa: {0}".format(loi)], [])
    try:
        from PIL import Image  # noqa: PLC0415 — cùng nếp core/nang_anh.py

        with Image.open(duong_anh) as anh:
            anh.load()  # ép giải mã hết — bắt tệp cụt/hỏng, không chỉ đọc header
            rong, cao = anh.size
    except Exception as loi:  # noqa: BLE001 — mọi kiểu lỗi Pillow đều là "ảnh hỏng"
        return (["ảnh bìa mở không được: {0}".format(str(loi)[:150])], [])

    loi_ra: List[str] = []
    if rong < _RONG_TOI_THIEU or cao < _CAO_TOI_THIEU:
        loi_ra.append("ảnh bìa {0}x{1} nhỏ hơn mức tối thiểu {2}x{3}"
                      .format(rong, cao, _RONG_TOI_THIEU, _CAO_TOI_THIEU))
    if cao and abs((rong / cao) - (16 / 9)) / (16 / 9) > _DUNG_SAI_TI_LE:
        loi_ra.append("ảnh bìa {0}x{1} lệch tỉ lệ 16:9".format(rong, cao))
    if dung_luong > _ANH_BIA_TOI_DA_BYTE:
        loi_ra.append("ảnh bìa nặng {0:.2f}MB, vượt mức khuyên dùng {1:.0f}MB"
                      .format(dung_luong / 1024 / 1024, _ANH_BIA_TOI_DA_BYTE / 1024 / 1024))
    # 09/10/2026 — ĐỘ ĐỌC ĐƯỢC (`core/do_bia.py`): chữ chìm vào nền / chữ nhỏ thì KHÔNG giao (luật chủ dự
    # án 07/10: thà không đăng còn hơn sản phẩm kém). Không đo được (không dò ra chữ) → chỉ cảnh báo.
    canh_bao: List[str] = []
    try:
        from . import do_bia  # noqa: PLC0415

        bc = do_bia.cham_tep(duong_anh)
        if bc.get("dat") is False:
            loi_ra.append("ảnh bìa khó đọc — " + do_bia.tom_tat(bc)[:400])
        elif bc.get("dat") is None:
            canh_bao.append("không đo được độ đọc được của ảnh bìa — " + do_bia.tom_tat(bc)[:200])
    except Exception as loi:  # noqa: BLE001 — bộ đo hỏng không được giết QA
        canh_bao.append("đo độ đọc được ảnh bìa hỏng: {0}".format(str(loi)[:150]))
    return loi_ra, canh_bao


# ── Hàm chính: kiểm một gói ───────────────────────────────────────────────────


def kiem_thu_muc_goi(
    thu_muc_goi: str,
    *,
    tieu_de: str = "",
    mo_ta: str = "",
    phut_muc_tieu: float = 0.0,
    chenh_cho_phep: float = 0.0,
    do_dai_tu_do: bool = False,
    do_dai_theo_goc: bool = False,
    do_phan_giai_mong_muon: str = "",
    ffmpeg: str = "",
    giai_ma_day_du: bool = False,
) -> KetQuaQA:
    """Kiểm MỘT gói đã nằm trong `DONE/<kênh>/<mã gói>`. Thuần tuý phần đọc
    file/gọi FFmpeg cục bộ — không gọi mạng, không ghi gì (xem :func:`ghi_ket_qua`
    và :func:`bao_qa_hong` cho phần có tác dụng phụ).

    Tham số ứng với `core.kenh.Kenh` cùng tên; để trống/0/False thì bỏ qua đúng
    phép kiểm cần tới nó (kèm cảnh báo nói rõ vì sao) thay vì đoán liều.
    """
    kq = KetQuaQA()
    if not os.path.isdir(thu_muc_goi):
        kq.loi.append("không thấy thư mục gói: {0}".format(thu_muc_goi))
        return kq

    duong_video, canh_bao_video = _tim_video(thu_muc_goi)
    duong_srt, canh_bao_srt = _tim_srt(thu_muc_goi)
    duong_anh, canh_bao_anh = _tim_thumbnail(thu_muc_goi)
    for c in (canh_bao_video, canh_bao_srt, canh_bao_anh):
        if c:
            kq.canh_bao.append(c)

    if not duong_video:
        kq.loi.append("thiếu video (không thấy tệp .mp4 nào trong gói)")
    if not duong_srt:
        kq.loi.append("thiếu phụ đề (không thấy tệp .srt nào trong gói)")
    if not duong_anh:
        kq.loi.append("thiếu ảnh bìa (không thấy .png/.jpg/.jpeg/.webp nào trong gói)")
    if not os.path.isfile(os.path.join(thu_muc_goi, TEP_BINH_LUAN)):
        # KHÔNG chặn — đúng nếp `core.ban_giao_dang.TEP_BINH_LUAN`: thiếu vẫn
        # đăng được, chỉ là không có sẵn câu để ghim.
        kq.canh_bao.append(
            "thiếu {0} — video vẫn đăng được, chỉ là không có sẵn câu để ghim"
            .format(TEP_BINH_LUAN))

    kq.loi.extend(_kiem_tieu_de(tieu_de))
    if not str(mo_ta or "").strip():
        kq.canh_bao.append(
            "chưa có mô tả (cột “Mô tả” trong kế hoạch đăng đang rỗng) — video "
            "vẫn đăng được nhưng mất phần SEO")

    giay_video = 0.0
    if duong_video:
        if not ffmpeg or not os.path.isfile(ffmpeg):
            kq.canh_bao.append(
                "không tìm được FFmpeg trên máy này — bỏ qua kiểm video (mở "
                "được, có tiếng, độ dài, độ phân giải, đen/đứng hình)")
        else:
            tt = doc_thong_tin_media(ffmpeg, duong_video)
            if not tt.mo_duoc:
                kq.loi.append("video không mở được bằng FFmpeg (tệp hỏng hoặc cụt)")
            else:
                giay_video = tt.giay
                if not tt.co_tieng:
                    kq.loi.append("video không có tiếng (không thấy luồng Audio)")
                # Lệch độ dài KHÔNG BAO GIỜ chặn đăng (chủ kênh chốt 30/09): độ dài
                # đi theo nguồn, khâu sản xuất đã nắn độ dài; video cụt/hỏng đã bị
                # bắt ở "không mở được"/phụ đề. Chặn chỉ làm gói xong nằm kẹt DONE.
                kq.canh_bao.extend(_kiem_do_dai(
                    tt.giay, phut_muc_tieu, chenh_cho_phep, do_dai_tu_do, do_dai_theo_goc))
                loi_dpg, canh_bao_dpg = _kiem_do_phan_giai(
                    tt.rong, tt.cao, do_phan_giai_mong_muon)
                kq.loi.extend(loi_dpg)
                kq.canh_bao.extend(canh_bao_dpg)
                if giai_ma_day_du:
                    loi_gm = _giai_ma_day_du(ffmpeg, duong_video)
                    if loi_gm:
                        kq.loi.append(
                            "video giải mã lỗi giữa chừng — tệp có thể cụt/hỏng: {0}"
                            .format(loi_gm))
                kq.canh_bao.extend(_soi_den_dung_hinh(ffmpeg, duong_video))

    if duong_srt:
        loi_srt, canh_bao_srt2 = _kiem_srt(duong_srt, giay_video)
        kq.loi.extend(loi_srt)
        kq.canh_bao.extend(canh_bao_srt2)

    if duong_anh:
        loi_anh, canh_bao_anh2 = _kiem_thumbnail(duong_anh)
        kq.loi.extend(loi_anh)
        kq.canh_bao.extend(canh_bao_anh2)

    return kq


def do_phan_giai_mong_muon(goc: str, kenh) -> str:
    """Bản sao RÚT GỌN của `core.auto_khau.chon_do_phan_giai` — CÙNG LOGIC hệt
    (kênh khai gì thì theo kênh, không khai thì theo cài đặt chung, hỏng cả
    hai thì `"1080p"`), viết lại ở đây để module QA không phải kéo theo toàn bộ
    `core/auto_khau.py` (~8000 dòng, nhiều phụ thuộc mạng/GUI) chỉ để dùng một
    hàm thuần. **Hai bên phải luôn khớp nhau** — sửa quy tắc ở một nơi thì sửa
    cả nơi kia.
    """
    from . import cai_dat  # noqa: PLC0415
    from .kenh import ten_khung  # noqa: PLC0415

    rieng = ten_khung(getattr(kenh, "do_phan_giai", ""))
    if rieng:
        return rieng
    return ten_khung(cai_dat.doc(goc).get("do_phan_giai")) or "1080p"


def kiem_goi(goc: str, ma_kenh: str, ma: str, thu_muc_goi: str = "") -> KetQuaQA:
    """Tiện ích: tự đọc `kenh.yaml`, `ke-hoach.csv` và tìm FFmpeg rồi gọi
    :func:`kiem_thu_muc_goi`. Dùng khi kiểm một gói ĐÃ nằm sẵn trong `DONE/`
    (vd chạy tay, chạy lại QA cho gói cũ) — lúc BÀN GIAO thì
    `core.ban_giao_dang.ban_giao` gọi thẳng `kiem_thu_muc_goi` vì nó đã có sẵn
    tiêu đề/mô tả trong tay (`doc_gioi_thieu`), khỏi đọc lại kế hoạch.
    """
    from . import ke_hoach_dang  # noqa: PLC0415
    from .dung_video import tim_ffmpeg  # noqa: PLC0415
    from .kenh import doc_kenh  # noqa: PLC0415

    k = doc_kenh(goc, ma_kenh)
    if not thu_muc_goi:
        if not k.thu_muc_done:
            kq = KetQuaQA()
            kq.loi.append("kênh “{0}” chưa khai `thu_muc_done` trong kenh.yaml — "
                          "không biết gói nằm ở đâu".format(ma_kenh))
            return kq
        thu_muc_goi = os.path.join(k.thu_muc_done, ma)

    tieu_de, mo_ta = "", ""
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    if "Mã gói" in cot:
        o_ma = cot.index("Mã gói")
        o_td = cot.index("Tiêu đề") if "Tiêu đề" in cot else -1
        o_mt = cot.index("Mô tả") if "Mô tả" in cot else -1
        for dong in hang:
            if dong[o_ma].strip() != str(ma).strip():
                continue
            tieu_de = dong[o_td] if o_td >= 0 else ""
            mo_ta = dong[o_mt] if o_mt >= 0 else ""
            break

    return kiem_thu_muc_goi(
        thu_muc_goi, tieu_de=tieu_de, mo_ta=mo_ta,
        phut_muc_tieu=k.phut_muc_tieu, chenh_cho_phep=k.chenh_cho_phep,
        do_dai_tu_do=k.do_dai_tu_do, do_dai_theo_goc=k.do_dai_theo_goc,
        do_phan_giai_mong_muon=do_phan_giai_mong_muon(goc, k),
        ffmpeg=tim_ffmpeg(goc))


# ── Tác dụng phụ: ghi tệp kết quả, báo ra ngoài ───────────────────────────────


def ghi_ket_qua(thu_muc_goi: str, ket_qua: KetQuaQA) -> str:
    """Ghi/lau tệp `qa-loi.txt` cạnh gói. Trả đường dẫn đã ghi, hoặc `""` khi
    xoá/không có gì để ghi.

    Chỉ ghi tệp khi QA **CHƯA ĐẠT** (`ket_qua.dat` là `False`) — đúng tên tệp
    "qa-loi.txt": có cảnh báo nhưng vẫn ĐẠT thì không viết gì, kẻo một gói lành
    (chỉ thiếu bình luận ghim, hay hiện đang cao hơn cấu hình một chút) lại
    nằm cạnh một tệp trông như báo hỏng — người mở `DONE/` ra sẽ đọc nhầm.
    Cảnh báo dù không ghi ra đĩa vẫn còn nguyên trong `KetQuaQA` trả về, ai gọi
    trực tiếp vẫn thấy đủ.

    QA đạt thì XOÁ tệp cũ nếu có — đừng để lại dấu vết của một lần chạy trước
    đã hỏng nhưng nay đã lành, kẻo người đọc tưởng gói vẫn còn vấn đề.
    """
    duong = os.path.join(thu_muc_goi, TEN_TEP_KET_QUA)
    if ket_qua.dat:
        try:
            os.remove(duong)
        except OSError:
            pass
        return ""
    try:
        os.makedirs(thu_muc_goi, exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            tep.write(ket_qua.van_ban())
        os.replace(tam, duong)
    except OSError:
        return ""
    return duong


def bao_qa_hong(goc: str, ma: str, ket_qua: KetQuaQA) -> None:
    """Báo ra ngoài khi một gói KHÔNG qua QA. KHÔNG BAO GIỜ ném lỗi — một hàm
    báo sự cố mà làm sập luồng bàn giao đang chạy thì còn tệ hơn im lặng.

    Thử `core.bao_dong` (Telegram/webhook) trước — im lặng nếu chưa cấu hình,
    đúng hợp đồng của module đó. LUÔN ghi thêm một dòng vào
    `workspace/tu-chay/tu-chay.log` bất kể Telegram có cấu hình hay không, vì
    đó là chỗ chủ dự án đã quen đọc mỗi khi `--tat-ca` chạy đêm — không phụ
    thuộc một kênh báo duy nhất cho một việc quan trọng thế này.
    """
    tieu_de = "QA gói {0} CHƯA ĐẠT — chưa đánh Sẵn sàng".format(ma)
    chi_tiet = "; ".join(ket_qua.loi)[:500]
    try:
        from . import bao_dong  # noqa: PLC0415

        bao_dong.bao_dong("qa_truoc_dang", tieu_de, chi_tiet, goc=goc)
    except Exception:  # noqa: BLE001
        pass
    try:
        duong_log = os.path.join(goc, "workspace", "tu-chay", "tu-chay.log")
        os.makedirs(os.path.dirname(duong_log), exist_ok=True)
        moc = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(duong_log, "a", encoding="utf-8") as tep:
            tep.write("[{0}] {1}: {2}\n".format(moc, tieu_de, chi_tiet))
    except OSError:
        pass
