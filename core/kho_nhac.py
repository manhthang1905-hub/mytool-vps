"""Kho nhạc nền chuẩn hoá — đọc `PROJECTS/music`, ghi `workspace/kho-nhac/`.

═══ VIỆC 1 CỦA `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`, duyệt 28/09/2026 ═══

`PROJECTS/music` là 107 bài Suno (~3,8 giờ) chủ dự án đã tải sẵn — KHÔNG BAO
GIỜ được ghi/xoá/đổi tên gì trong đó (luật 1 của CLAUDE.md, "PROJECTS/ là sản
phẩm khách đã trả tiền"). Máy này còn không có `ffprobe` — chỉ có một bản
FFmpeg gói sẵn (`core.dung_video.tim_ffmpeg`).

Việc 1 chỉ làm MỘT thứ: đọc kho thô đó, cắt lặng đầu/cuối, đưa mọi bài về
CÙNG MỘT MỨC TO (−32 LUFS, để cộng với "nhạc dưới giọng 18 dB" ở Việc 2 ra
đúng −18 dB dưới giọng đọc thật −14,5 LUFS), rồi ghi bản `.m4a` đã chuẩn hoá
+ một chỉ mục (JSON máy đọc, CSV người sửa tay) vào `workspace/kho-nhac/`.

═══ TĂNG DẦN — KHÔNG LÀM LẠI VIỆC ĐÃ LÀM ═══

Kho 107 bài chuẩn hoá lần đầu tốn vài phút (mỗi bài qua FFmpeg ba lượt: đo,
ghi, đo lại). `cap_nhat()` vì vậy nhớ **vân tay nhanh** của từng tệp nguồn
(đường tương đối + cỡ tệp + mtime_ns) — khớp thì bỏ qua ngay, không mở lại
tệp. Vân tay lệch mới tính sha1 để biết THẬT SỰ có đổi nội dung hay chỉ đổi
mốc giờ (chép đè cùng nội dung). Nhờ vậy các bước gọi `cap_nhat` lặp lại từ
`vong_hoc.truoc_luot` (Việc 3, 300 giây/lượt) hay khâu dựng (Việc 2, 60
giây/lượt) hầu như không tốn gì sau lần nạp đầu.

Chống trùng theo `id=<uuid>` trong metadata `comment` (Suno gắn cho mọi bài
nó sinh) — không có thì theo sha1 nội dung. Kho thô có ít nhất 3 cặp trùng
tên khác nhau ("Felt Gravity"/"(1)", "Ivory Panic"×2, "Basalt Piano"×2); gộp
theo khoá này thay vì theo tên file tránh chuẩn hoá hai lần cùng một bài.

═══ CSV: CHỦ KÊNH SỬA, TOOL KHÔNG ĐÈ ═══

`chi-muc.csv` là thứ duy nhất người không biết lập trình đụng tới: sửa cột
`cam_xuc` (bỏ hậu tố "(đoán từ tên)" đi coi như đã xác nhận/sửa tay) hoặc
`loai`. Lượt `cap_nhat` sau đọc CSV TRƯỚC khi ghi lại — ô nào không còn hậu
tố đoán, hoặc khác giá trị mặc định tool tự đặt lần trước, coi là chủ kênh
đã sửa và GIỮ NGUYÊN, không tính lại. Các cột còn lại (giây, lufs, tp,
co_giong, mat_goc) luôn là số đo thật, tool luôn ghi đè.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import dung_video, ffmpeg_goi_san, so_csv, tieng_canh

__all__ = [
    "duong_kho", "cap_nhat", "doc_chi_muc", "do_lufs_that",
    "doan_cam_xuc_tu_ten", "chon_nhac", "lenh_lop_nhac", "lich_su_dung",
    "main",
]

TEN_THU_MUC_BAI = "bai"
TEN_CHI_MUC_JSON = "chi-muc.json"
TEN_CHI_MUC_CSV = "chi-muc.csv"
TEN_TEP_KHOA = ".khoa"

#: Ngân sách mặc định khi gọi `python -m core.kho_nhac` không kèm `--het` —
#: khớp "bước 0 tu_chay" trong thiết kế (300 giây/lượt).
NGAN_SACH_MAC_DINH_GIAY = 300.0

#: Khoá coi là "cũ, tiến trình sinh ra nó đã chết" sau ngần này — tránh kho
#: nhạc bị khoá vĩnh viễn nếu tiến trình trước bị giết giữa chừng.
KHOA_CU_QUA_GIAY = 3600.0

#: Bài ngắn hơn ngần này chỉ dùng để LẤP (không đủ trải một phần video).
GIAY_TOI_THIEU_DU_DUNG = 45.0

NGUON_DOAN = "đoán từ tên"
NGUON_KENH = "kênh"
HAU_TO_DOAN = " (đoán từ tên)"

CHUAN_COT_CSV = ("id", "ten", "nhom", "giay", "lufs", "tp", "co_giong",
                  "cam_xuc", "loai", "mat_goc")


# ── FFmpeg: chuỗi lọc (THUẦN — không đụng tệp, không gọi tiến trình) ─────────


def chuoi_cat_lang() -> str:
    """Cắt lặng đầu và cuối — không đổi tốc độ, không đổi cao độ.

    Đảo ngược (`areverse`) rồi cắt lặng đầu lần hai là cách chuẩn để cắt lặng
    CUỐI bằng đúng bộ lọc chỉ biết cắt đầu (`silenceremove` không có chế độ
    "cắt đuôi" trực tiếp).
    """
    return ("silenceremove=start_periods=1:start_threshold=-50dB:"
             "start_silence=0.1:detection=peak,"
             "areverse,"
             "silenceremove=start_periods=1:start_threshold=-50dB:"
             "start_silence=0.4:detection=peak,"
             "areverse")


#: Thiết kế duyệt 28/09 ghi `TP=-12`, nhưng bộ lọc `loudnorm` của FFmpeg CHỈ
#: nhận `TP` trong khoảng [-9, 0] (đo bằng `ffmpeg -h filter=loudnorm` trên
#: chính bản FFmpeg của tool, 28/09/2026) — `-12` bị FFmpeg từ chối thẳng
#: ("Value -12.000000 for parameter 'TP' out of range"), mọi bài đều lỗi.
#: Lấy `-9` (mép an toàn nhất còn hợp lệ, gần `-12` nhất) — `I=-32` mới là số
#: quyết định độ to cuối, `TP` chỉ chặn đỉnh không cho vỡ tiếng, nên đổi số
#: này không ảnh hưởng ý đồ "-32 LUFS" của thiết kế.
TP_MUC_TIEU = -9


def chuoi_loc_do() -> str:
    """Lượt 1 (chỉ ĐO, không ghi tệp): cắt lặng rồi đo loudnorm hai lượt."""
    return (chuoi_cat_lang() +
            ",loudnorm=I=-32:TP={0}:LRA=20:print_format=json".format(TP_MUC_TIEU))


def chuoi_loc_ghi(do1: Dict[str, Any]) -> str:
    """Lượt 2 (GHI tệp): cùng chuỗi cắt, áp số đo lượt 1 để chỉnh TUYẾN TÍNH.

    `do1` là JSON `loudnorm` lượt 1 (`input_i`, `input_tp`, `input_lra`,
    `input_thresh`, `target_offset`). Thiếu khoá nào ném `KeyError` — người
    gọi tự quyết định lùi về đâu (`_chuan_hoa_mot_bai` lùi về lượt khuếch đại
    đơn khi lượt này không ra JSON hợp lệ).
    """
    return (chuoi_cat_lang() +
            ",loudnorm=I=-32:TP={0}:LRA=20:"
            "measured_I={1}:measured_TP={2}:measured_LRA={3}:"
            "measured_thresh={4}:offset={5}:linear=true:print_format=json"
            ",aresample=48000,aformat=channel_layouts=stereo,"
            "afade=t=in:d=0.3").format(
        TP_MUC_TIEU, do1["input_i"], do1["input_tp"], do1["input_lra"],
        do1["input_thresh"], do1["target_offset"])


def chuoi_loc_khuech_dai_don(gain_db: float) -> str:
    """Đường lùi khi `loudnorm` hai lượt không ra `normalization_type=linear`.

    Thiết kế: "JSON trả `normalization_type` ≠ linear → làm lại bằng
    `volume=(-32 - input_i)dB`" — một phép khuếch đại tuyến tính đơn giản,
    không dựa vào `loudnorm` nữa.
    """
    return (chuoi_cat_lang() +
            ",volume={0:.3f}dB,aresample=48000,aformat=channel_layouts=stereo,"
            "afade=t=in:d=0.3").format(gain_db)


# ── FFmpeg: chạy tiến trình + đọc JSON `loudnorm` từ stderr ──────────────────


def _co_tao_tien_trinh() -> int:
    return (getattr(subprocess, "IDLE_PRIORITY_CLASS", 0) |
            getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _chay_ffmpeg(cmd: Sequence[str], timeout: float = 600.0) -> Optional[str]:
    """Chạy FFmpeg ưu tiên thấp, không cửa sổ đen. Trả `stderr`, `None` khi lỗi.

    ƯU TIÊN THẤP + `-threads 1` (đặt sẵn trong từng lệnh gọi) vì máy này còn
    đang sản xuất thật — chuẩn hoá kho nhạc không được giành CPU của các khâu
    khác.
    """
    try:
        ra = subprocess.run(  # noqa: S603
            list(cmd), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=_co_tao_tien_trinh())
    except (OSError, subprocess.SubprocessError):
        return None
    return ra.stderr or ""


_RE_JSON_LOUDNORM = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.S)


def parse_json_loudnorm(stderr_text: str) -> Optional[Dict[str, Any]]:
    """Khối JSON cuối `loudnorm` in ra `stderr` (THUẦN — nhận sẵn chuỗi).

    `loudnorm print_format=json` in một khối `{...}` phẳng (không JSON lồng)
    kèm dòng chữ khác quanh nó. Tìm khối CUỐI CÙNG có khoá `input_i` — lượt
    ghi (lượt 2) có thể có nhiều bộ lọc khác cũng in JSON, khối của
    `loudnorm` luôn nhận ra được nhờ khoá riêng này.
    """
    if not stderr_text:
        return None
    ung_vien = _RE_JSON_LOUDNORM.findall(stderr_text)
    if not ung_vien:
        return None
    try:
        return json.loads(ung_vien[-1])
    except (ValueError, TypeError):
        return None


_RE_DURATION = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def _doc_do_dai_giay(stderr_text: str) -> float:
    m = _RE_DURATION.search(stderr_text or "")
    if not m:
        return 0.0
    gio, phut, giay = m.groups()
    return int(gio) * 3600 + int(phut) * 60 + float(giay)


_RE_META_HEADER = re.compile(r"^ {2}Metadata:\s*$")
_RE_META_LINE = re.compile(r"^ {4}(\S.*?)\s*:\s?(.*)$")


def phan_tich_metadata(stderr_text: str) -> Dict[str, str]:
    """`ffmpeg -i <tệp>` in `title/artist/comment` — chỉ lấy khối ĐẦU TIÊN.

    MP3 Suno có ảnh bìa đính kèm như một luồng video "attached pic" riêng,
    và luồng đó CŨNG có `Metadata:` của chính nó (`title: Cover`,
    `comment: Cover (front)`) — thụt sâu hơn (6 dấu cách thay vì 2). Đọc
    nhầm khối đó thì `id=` của Suno biến mất, chống trùng vỡ. Khối đầu tiên
    (2 dấu cách, ngay dưới `Input #0`) luôn là của TỆP, không phải của ảnh.
    """
    ra: Dict[str, str] = {}
    trong_khoi = False
    for dong in (stderr_text or "").splitlines():
        if _RE_META_HEADER.match(dong):
            if ra:
                break  # đã đọc xong khối đầu tiên, đừng đọc khối thứ hai
            trong_khoi = True
            continue
        if trong_khoi:
            m = _RE_META_LINE.match(dong)
            if m:
                ra[m.group(1).strip().lower()] = m.group(2).strip()
                continue
            if ra:
                break
            trong_khoi = False
    return ra


def do_lufs_that(ffmpeg: str, duong_tep: str) -> Optional[Dict[str, float]]:
    """Đo LUFS/TP/độ dài THẬT của một tệp âm thanh sẵn có — không sửa gì.

    Dùng hai chỗ: (1) `_chuan_hoa_mot_bai` gọi ngay sau khi ghi xong, để chỉ
    mục ghi đúng số đo lại chứ không ghi số MỤC TIÊU (-32/-12); (2) kiểm tra
    tay sau `--het` — đo vài bài ngẫu nhiên trong `bai/` xem có đúng khoảng
    −32 LUFS không.
    """
    if not ffmpeg or not os.path.isfile(duong_tep):
        return None
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-i", duong_tep,
           "-map", "0:a:0",
           "-af", "loudnorm=I=-32:TP={0}:LRA=20:print_format=json".format(
               TP_MUC_TIEU),
           "-threads", "1", "-f", "null", "-"]
    text = _chay_ffmpeg(cmd)
    if text is None:
        return None
    js = parse_json_loudnorm(text)
    if js is None:
        return None
    try:
        return {"lufs": float(js["input_i"]), "tp": float(js["input_tp"]),
                "giay": _doc_do_dai_giay(text)}
    except (KeyError, TypeError, ValueError):
        return None


def _chuan_hoa_mot_bai(ffmpeg: str, duong_vao: str,
                        duong_ra: str) -> Tuple[float, float, float]:
    """Cắt lặng + đưa một tệp về −32 LUFS. Trả `(giây, lufs, tp)` ĐO LẠI.

    Ba lượt FFmpeg: (1) đo, (2) ghi bằng số đo lượt 1, (3) đo lại bản vừa ghi
    — lượt 3 vừa để KIỂM (không tin mù `loudnorm` luôn đúng mục tiêu), vừa để
    lấy độ dài SAU KHI đã cắt lặng (không phải độ dài tệp gốc).
    """
    text1 = _chay_ffmpeg(
        [ffmpeg, "-hide_banner", "-nostdin", "-i", duong_vao,
         "-map", "0:a:0", "-af", chuoi_loc_do(), "-threads", "1",
         "-f", "null", "-"])
    do1 = parse_json_loudnorm(text1 or "")
    if do1 is None:
        raise RuntimeError("không đo được loudnorm lượt 1 (FFmpeg không trả JSON)")

    tam = duong_ra + ".dang-ghi.m4a"
    da_ghi = False
    try:
        loc = chuoi_loc_ghi(do1)
    except (KeyError, TypeError, ValueError):
        loc = None
    if loc is not None:
        text2 = _chay_ffmpeg(
            [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", duong_vao,
             "-map", "0:a:0", "-af", loc, "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", "-threads", "1", tam])
        do2 = parse_json_loudnorm(text2 or "") if text2 is not None else None
        da_ghi = os.path.isfile(tam) and do2 is not None
        neu_tuyen_tinh = da_ghi and str(
            do2.get("normalization_type", "")).lower() == "linear"
    else:
        neu_tuyen_tinh = False

    if not neu_tuyen_tinh:
        # Đường lùi: loudnorm 2 lượt không ra kiểu tuyến tính (hoặc lượt ghi
        # hỏng) — khuếch đại đơn giản theo số đo lượt 1.
        try:
            input_i = float(do1.get("input_i", -32.0))
        except (TypeError, ValueError):
            input_i = -32.0
        gain_db = -32.0 - input_i
        text2b = _chay_ffmpeg(
            [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", duong_vao,
             "-map", "0:a:0", "-af", chuoi_loc_khuech_dai_don(gain_db),
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
             "-threads", "1", tam])
        da_ghi = os.path.isfile(tam) and text2b is not None

    if not da_ghi:
        _xoa_neu_co(tam)
        raise RuntimeError("FFmpeg không ghi được tệp chuẩn hoá")

    do3 = do_lufs_that(ffmpeg, tam)
    if do3 is None:
        _xoa_neu_co(tam)
        raise RuntimeError("ghi xong nhưng không đo lại được")

    os.makedirs(os.path.dirname(duong_ra), exist_ok=True)
    os.replace(tam, duong_ra)
    return do3["giay"], do3["lufs"], do3["tp"]


def _xoa_neu_co(duong: str) -> None:
    try:
        os.remove(duong)
    except OSError:
        pass


# ── Nhận diện có giọng (dùng lại core.tieng_canh, không cần mạng) ────────────


def _do_co_giong(ffmpeg: str,
                  duong_tep: str) -> Tuple[Optional[bool], str]:
    """`True/False` nghe ra tiếng người hay không; `None` = không đo được.

    Dùng đúng phép đo của `tieng_canh` (dải tần + nhịp âm tiết 3–6 Hz) — cùng
    một tiêu chí tắt tiếng clip lúc dựng video. Không có numpy (SETUP.bat
    chưa chạy, hoặc máy tối giản) thì trả `None` kèm ghi chú, KHÔNG đoán liều
    thành `False`.
    """
    try:
        import numpy  # noqa: F401,PLC0415
    except ImportError:
        return None, "không đo được (thiếu numpy)"
    x = tieng_canh.doc_pcm(ffmpeg, duong_tep)
    if x is None:
        return None, "không đo được (FFmpeg không đọc được tiếng)"
    diem = tieng_canh.diem_tieng_noi(x)
    return (diem >= tieng_canh.NGUONG_TIENG_NGUOI), ""


# ── Đoán nhóm / cảm xúc từ tên (THUẦN) ────────────────────────────────────────


_RE_NHOM = (
    re.compile(r"^(TL\d+-\d{4})_"),
    re.compile(r"^([A-Z]\d+)\."),
)

#: Tiền tố rác lặp trước tên bài thật, kiểu `"4113974 Apr 22 20:10 4 Marble
#: Applause.mp3"` (đo được trong `PROJECTS/music` 28/09/2026): số, tháng viết
#: tắt, giờ:phút — dọn từng lớp một cho tới khi không còn khớp.
_RE_TIEN_TO_RAC = re.compile(
    r"^(?:\d+|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}:\d{2})"
    r"[\s.:_-]+", re.IGNORECASE)


def don_ten(ten: str) -> str:
    """Bỏ tiền tố rác (số/ngày/giờ dính trước tên bài thật) khỏi một cái tên.

    >>> don_ten("4113974 Apr 22 20:10 4 Marble Applause")
    'Marble Applause'
    >>> don_ten("Ivory Panic")
    'Ivory Panic'
    """
    ten = (ten or "").strip()
    truoc = None
    while truoc != ten:
        truoc = ten
        ten = _RE_TIEN_TO_RAC.sub("", ten).strip()
    return ten or truoc or ""


def doan_nhom(ten_tep: str, ten_sach: str) -> str:
    """Nhóm bài theo quy ước đặt tên đã thấy trong kho: `TL1-00xx_`, `B1.`…

    Không khớp quy ước nào thì bài đứng riêng — nhóm của nó là chính tên nó
    (thiết kế: "nhom (...), hoặc tên").
    """
    for rx in _RE_NHOM:
        m = rx.match(ten_tep)
        if m:
            return m.group(1)
    return ten_sach


#: Từ khoá tiếng Anh (tên Suno hầu hết đặt tiếng Anh) → nhãn cảm xúc tiếng
#: Việt. Chỉ là ĐOÁN SƠ theo thiết kế mục (e) Việc 1 — CSV chủ kênh luôn
#: thắng con đoán này.
TU_KHOA_CAM_XUC: Dict[str, Tuple[str, ...]] = {
    "căng": ("panic", "storm", "frozen", "tension", "dread", "alarm",
             "chaos", "crisis", "urgent", "frantic", "fear", "danger"),
    "ấm": ("hearth", "candle", "apricot", "warm", "cozy", "gentle",
           "tender", "lullaby", "home", "embrace"),
    "buồn": ("grief", "sorrow", "tears", "lonely", "melancholy", "elegy",
             "loss", "mourning", "sad"),
    "vui": ("joy", "bright", "sunny", "cheer", "dance", "playful",
            "bounce", "festive", "delight", "spark"),
    "bí ẩn": ("mystery", "shadow", "whisper", "secret", "enigma", "veil",
              "fog", "riddle"),
    "hùng tráng": ("epic", "triumph", "anthem", "victory", "march",
                   "heroic", "rise", "glory"),
    "tĩnh lặng": ("silence", "still", "calm", "quiet", "drift", "float",
                  "hush", "ambient", "resolve", "static"),
}


def doan_cam_xuc_tu_ten(ten: str) -> List[str]:
    """Đoán sơ nhãn cảm xúc từ tên bài (THUẦN). Không khớp gì → `[]`.

    >>> doan_cam_xuc_tu_ten("Salt-Paper Storm")
    ['căng']
    """
    thap = (ten or "").lower()
    ra: List[str] = []
    for nhan, tu_khoa in TU_KHOA_CAM_XUC.items():
        if any(t in thap for t in tu_khoa):
            ra.append(nhan)
    return ra


def _loai_mac_dinh(co_giong: Optional[bool], giay: float) -> str:
    """`loai` mặc định tool tự đặt — chủ kênh sửa tay đè lên trong CSV.

    Thiết kế: "có giọng → loại mặc định" (đánh dấu để Việc 2 loại khỏi vòng
    xoay nhạc nền) và "bài <45s chỉ để lấp".
    """
    if co_giong:
        return "co_giong"
    if giay < GIAY_TOI_THIEU_DU_DUNG:
        return "lap"
    return ""


# ── Khoá chống trùng + vân tay tăng dần ───────────────────────────────────────


_RE_SUNO_ID = re.compile(r"id=([0-9a-fA-F-]{8,})")


def _khoa_bai(metadata: Dict[str, str], sha1: str) -> str:
    """`id=` của Suno trong `comment` nếu có, không thì sha1 nội dung."""
    m = _RE_SUNO_ID.search(metadata.get("comment", "") or "")
    if m:
        return "suno:" + m.group(1).lower()
    return "sha1:" + sha1


def _sha1_tep(duong: str, buf: int = 1 << 20) -> str:
    bam = hashlib.sha1()
    with open(duong, "rb") as tep:
        while True:
            khoi = tep.read(buf)
            if not khoi:
                break
            bam.update(khoi)
    return bam.hexdigest()


def _van_tay_nhanh(duong_tuyet_doi: str, thu_muc_nguon: str) -> Dict[str, Any]:
    st = os.stat(duong_tuyet_doi)
    rel = os.path.relpath(duong_tuyet_doi, thu_muc_nguon).replace(os.sep, "/")
    return {"duong_tuong_doi": rel, "co_bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns}


def _van_tay_khop(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (a.get("duong_tuong_doi") == b.get("duong_tuong_doi") and
            a.get("co_bytes") == b.get("co_bytes") and
            a.get("mtime_ns") == b.get("mtime_ns"))


def _sinh_id8(khoa: str, da_dung: Dict[str, Any]) -> str:
    goc_bam = hashlib.sha1(khoa.encode("utf-8")).hexdigest()
    do_dai = 8
    while do_dai <= len(goc_bam):
        ung_vien = goc_bam[:do_dai]
        if ung_vien not in da_dung:
            return ung_vien
        do_dai += 2
    # Cực hiếm (đụng hàng ở cả 40 hex sha1) — thêm hậu tố đếm cho chắc duy nhất.
    i = 0
    while "{0}-{1}".format(goc_bam[:8], i) in da_dung:
        i += 1
    return "{0}-{1}".format(goc_bam[:8], i)


def _liet_ke_mp3(thu_muc: str) -> List[str]:
    """Mọi `.mp3` dưới `thu_muc`, sắp theo đường dẫn — thứ tự ổn định giữa
    các lượt (dễ so sánh nhật ký, dễ viết bài kiểm)."""
    ra: List[str] = []
    if not os.path.isdir(thu_muc):
        return ra
    for goc, _thu, teps in os.walk(thu_muc):
        for ten in teps:
            if ten.lower().endswith(".mp3"):
                ra.append(os.path.join(goc, ten))
    ra.sort()
    return ra


# ── Đường dẫn, khoá độc quyền ─────────────────────────────────────────────────


def duong_kho(goc: str) -> str:
    """`workspace/kho-nhac/` — nằm trong `safe_update.PRESERVE`, sống qua mọi
    lượt cập nhật tool."""
    return os.path.join(goc, "workspace", "kho-nhac")


def _pid_con_song(pid: int) -> bool:
    """Tiến trình mang PID này còn sống không — bản RÚT GỌN của
    `core.tu_chay._pid_con_song` (không `import core.tu_chay`: tệp đó đang
    được sửa song song bởi phiên khác, và VPS lỡ chập cũng không nên kéo
    `.khoa` của kho nhạc theo). Hỏi hỏng → coi là CÒN SỐNG, an toàn hơn giành
    khoá bừa."""
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    try:
        import ctypes  # noqa: PLC0415

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel.OpenProcess(0x1000, False, int(pid))
        if handle:
            kernel.CloseHandle(handle)
            return True
        return False
    except Exception:  # noqa: BLE001 — hỏi hỏng thì coi là còn sống
        return True


def _tao_khoa(duong: str) -> bool:
    """Khoá độc quyền `O_CREAT|O_EXCL` — giành lại khi PID cũ đã CHẾT (không
    chỉ khi khoá đã CŨ): tiến trình bị kill giữa chừng (hết giờ, mất điện)
    không được để `workspace/kho-nhac/.khoa` chặn kho nhạc cả `KHOA_CU_QUA_GIAY`
    giây sau đó."""
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    try:
        fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        pid_cu = 0
        try:
            with open(duong, "r", encoding="utf-8") as tep:
                pid_cu = int(json.load(tep).get("pid") or 0)
        except (OSError, ValueError, TypeError):
            pid_cu = 0
        try:
            tuoi = time.time() - os.path.getmtime(duong)
        except OSError:
            tuoi = KHOA_CU_QUA_GIAY + 1
        pid_song = pid_cu and pid_cu != os.getpid() and _pid_con_song(pid_cu)
        if pid_song and tuoi < KHOA_CU_QUA_GIAY:
            return False
        try:
            os.remove(duong)
        except OSError:
            return False
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tep:
            tep.write(json.dumps({"pid": os.getpid(), "luc": time.time()}))
    except OSError:
        pass
    return True


def _nha_khoa(duong: str) -> None:
    try:
        os.remove(duong)
    except OSError:
        pass


# ── Chỉ mục: đọc/ghi JSON + CSV ───────────────────────────────────────────────


def _duong_json(thu_muc: str) -> str:
    return os.path.join(thu_muc, TEN_CHI_MUC_JSON)


def _duong_csv(thu_muc: str) -> str:
    return os.path.join(thu_muc, TEN_CHI_MUC_CSV)


def _doc_chi_muc_tu_thu_muc(thu_muc: str) -> Dict[str, Any]:
    duong = _duong_json(thu_muc)
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        du = {}
    if not isinstance(du, dict) or not isinstance(du.get("bai"), dict):
        du = {"bai": {}}
    return du


def doc_chi_muc(goc: str) -> Dict[str, Any]:
    """Đọc `chi-muc.json` hiện có — rỗng (`{"bai": {}}`) nếu chưa từng chạy."""
    return _doc_chi_muc_tu_thu_muc(duong_kho(goc))


def _ghi_json_nguyen_tu(duong: str, obj: Any) -> None:
    thu_muc = os.path.dirname(duong)
    if thu_muc:
        os.makedirs(thu_muc, exist_ok=True)
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(obj, tep, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tam, duong)


def _tach_cam_xuc_hien(cell: str) -> Tuple[List[str], bool]:
    """Ô CSV `cam_xuc` → `(danh sách, còn hậu tố "đoán từ tên" hay không)`."""
    cell = (cell or "").strip()
    doan = False
    if cell.endswith(HAU_TO_DOAN):
        doan = True
        cell = cell[: -len(HAU_TO_DOAN)].strip()
    ds = [x.strip() for x in cell.split(";") if x.strip()]
    return ds, doan


def _ap_dung_ghi_de_tu_csv(chi_muc: Dict[str, Any], thu_muc: str) -> None:
    """Đọc `chi-muc.csv` TRƯỚC khi xử lý — cột chủ kênh đã sửa thì giữ.

    `cam_xuc`: còn hậu tố "(đoán từ tên)" thì vẫn coi là máy đoán (có thể
    đoán lại/ghi đè ở lượt sau); mất hậu tố (chủ kênh đã gõ tay, kể cả xoá
    hết) thì khoá lại thành nguồn `"kênh"`, không đụng nữa.

    `loai`: khác với `loai_mac_dinh_ap_dung` (giá trị tool tự đặt LẦN TRƯỚC)
    thì coi là chủ kênh đã sửa, giữ nguyên.
    """
    cot, hang = so_csv.doc_csv(_duong_csv(thu_muc), CHUAN_COT_CSV)
    idx = so_csv.chi_so_cot(cot)
    if "id" not in idx:
        return
    for dong in hang:
        id8 = dong[idx["id"]].strip()
        b = chi_muc["bai"].get(id8)
        if not b:
            continue
        if "cam_xuc" in idx:
            ds, doan = _tach_cam_xuc_hien(dong[idx["cam_xuc"]])
            if not doan:
                b["cam_xuc"] = ds
                b["cam_xuc_nguon"] = NGUON_KENH
        if "loai" in idx:
            hien = dong[idx["loai"]].strip()
            if hien != b.get("loai_mac_dinh_ap_dung", ""):
                b["loai"] = hien
                b["loai_tu_kenh"] = True


def _chu_bool(v: Optional[bool]) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    return ""


def _ghi_chi_muc_csv(thu_muc: str, chi_muc: Dict[str, Any]) -> None:
    hang: List[List[str]] = []
    for id8 in sorted(chi_muc["bai"]):
        b = chi_muc["bai"][id8]
        cam_xuc_cell = "; ".join(b.get("cam_xuc") or [])
        if cam_xuc_cell and b.get("cam_xuc_nguon") == NGUON_DOAN:
            cam_xuc_cell += HAU_TO_DOAN
        hang.append([
            id8,
            b.get("ten", ""),
            b.get("nhom", ""),
            "{0:.2f}".format(b.get("giay", 0.0)),
            "{0:.1f}".format(b.get("lufs", 0.0)),
            "{0:.1f}".format(b.get("tp", 0.0)),
            _chu_bool(b.get("co_giong")),
            cam_xuc_cell,
            b.get("loai", ""),
            "true" if b.get("mat_goc") else "false",
        ])
    so_csv.luu_csv(_duong_csv(thu_muc), CHUAN_COT_CSV, hang, sao_luu=True)


def _luu_chi_muc(thu_muc: str, chi_muc: Dict[str, Any]) -> None:
    """Ghi JSON + CSV NGAY — gọi sau MỖI bài xử lý xong, không đợi hết vòng.

    28/09/2026: lượt nạp `--het` đầu tiên bị dừng giữa chừng (nền chạy quá
    lâu) — 22 bài đã chuẩn hoá xong nằm trong `bai/` nhưng KHÔNG một dòng nào
    vào `chi-muc.json` (khi đó chỉ ghi Ở CUỐI vòng), vô hiệu hoá đúng thứ
    "TĂNG DẦN" mà thiết kế đòi: chạy lại từ đầu vẫn coi 22 bài đó là MỚI.
    Ghi sau từng bài thì bị dừng bất cứ lúc nào (hết ngân sách giây, tiến
    trình bị kill, mất điện) cũng chỉ mất đúng bài đang xử lý dở, không mất
    những bài đã xong trước đó.
    """
    _ghi_json_nguyen_tu(_duong_json(thu_muc), chi_muc)
    _ghi_chi_muc_csv(thu_muc, chi_muc)


# ── Vòng chính: cập nhật tăng dần ─────────────────────────────────────────────


def _ket_qua_rong() -> Dict[str, Any]:
    return {
        "moi": 0, "bo_qua_khong_doi": 0, "trung_gop": 0,
        "mat_goc": 0, "co_giong": 0, "qua_ngan": 0,
        "loi": [], "het_ngan_sach": False, "con_lai": 0,
        "giay_da_dung": 0.0, "tong_bai_trong_kho": 0, "loi_chung": "",
    }


def cap_nhat(goc: str = "", ngan_sach_giay: Optional[float] = None, *,
             thu_muc_nguon: str = "", thu_muc_dich: str = "",
             ffmpeg: str = "",
             ghi: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Nạp/chuẩn hoá TĂNG DẦN toàn bộ kho nhạc. Không bao giờ ghi vào nguồn.

    `ngan_sach_giay=None` = không giới hạn, xử lý hết (dùng cho `--het`).
    Có số thì dừng nhận bài MỚI khi đã tốn quá ngần ấy giây xử lý thật (đếm
    riêng, không tính thời gian quét/so vân tay) — bài đang dở vẫn ghi xong,
    không cắt nửa chừng.

    `thu_muc_nguon`/`thu_muc_dich`/`ffmpeg` để trống thì tự suy từ `goc`
    (mặc định sản xuất thật); bài kiểm tự truyền thư mục tạm để không đụng
    `PROJECTS/music` thật và không cần dựng cả 107 bài.
    """
    goc = goc or dung_video.thu_muc_tool()
    thu_muc_nguon = thu_muc_nguon or os.path.join(goc, "PROJECTS", "music")
    thu_muc_dich = thu_muc_dich or duong_kho(goc)
    ffmpeg = ffmpeg or dung_video.tim_ffmpeg(goc)
    ghi = ghi or (lambda s: None)

    kq = _ket_qua_rong()
    if not ffmpeg or not ffmpeg_goi_san.du_dung(ffmpeg):
        kq["loi_chung"] = ("không có FFmpeg đủ dùng (thiếu libx264/bộ lọc) — "
                            "bỏ qua lượt cập nhật kho nhạc, không phải lỗi "
                            "chặn sản xuất.")
        ghi("  kho nhạc: " + kq["loi_chung"])
        return kq

    thu_muc_bai = os.path.join(thu_muc_dich, TEN_THU_MUC_BAI)
    os.makedirs(thu_muc_bai, exist_ok=True)

    duong_khoa = os.path.join(thu_muc_dich, TEN_TEP_KHOA)
    if not _tao_khoa(duong_khoa):
        kq["loi_chung"] = "đang có tiến trình khác cập nhật kho nhạc — bỏ qua lượt này."
        ghi("  kho nhạc: " + kq["loi_chung"])
        return kq

    try:
        chi_muc = _doc_chi_muc_tu_thu_muc(thu_muc_dich)
        _ap_dung_ghi_de_tu_csv(chi_muc, thu_muc_dich)

        theo_khoa: Dict[str, str] = {
            b["khoa"]: id8 for id8, b in chi_muc["bai"].items() if b.get("khoa")
        }

        tim_thay: set = set()
        bat_dau = time.monotonic()
        het_ngan_sach = False

        for duong_tep in _liet_ke_mp3(thu_muc_nguon):
            vt = _van_tay_nhanh(duong_tep, thu_muc_nguon)
            rel = vt["duong_tuong_doi"]
            tim_thay.add(rel)

            id8_hien_co, nguon_hien_co = _tim_theo_duong_nguon(chi_muc, rel)
            if nguon_hien_co and _van_tay_khop(nguon_hien_co, vt):
                kq["bo_qua_khong_doi"] += 1
                continue

            sha1 = _sha1_tep(duong_tep)
            if nguon_hien_co and nguon_hien_co.get("sha1") == sha1:
                # Nội dung y hệt, chỉ mốc giờ/đường dẫn đổi — cập nhật vân tay,
                # không mở FFmpeg.
                nguon_hien_co.update(vt)
                kq["bo_qua_khong_doi"] += 1
                continue

            if het_ngan_sach:
                kq["con_lai"] += 1
                continue
            if (ngan_sach_giay is not None and
                    (time.monotonic() - bat_dau) >= ngan_sach_giay):
                het_ngan_sach = True
                kq["con_lai"] += 1
                continue

            text_meta = _chay_ffmpeg(
                [ffmpeg, "-hide_banner", "-nostdin", "-i", duong_tep]) or ""
            metadata = phan_tich_metadata(text_meta)
            khoa = _khoa_bai(metadata, sha1)

            id8_trung = theo_khoa.get(khoa)
            if id8_trung and id8_trung != id8_hien_co:
                _them_nguon_vao_bai(chi_muc["bai"][id8_trung], vt, sha1)
                if id8_hien_co and id8_hien_co in chi_muc["bai"]:
                    _bo_nguon_khoi_bai(chi_muc["bai"][id8_hien_co], rel)
                kq["trung_gop"] += 1
                ghi("  kho nhạc: {0} trùng bài đã có ({1}) — gộp, không ghi "
                    "lại.".format(rel, id8_trung))
                _luu_chi_muc(thu_muc_dich, chi_muc)
                continue

            id8 = id8_hien_co or _sinh_id8(khoa, chi_muc["bai"])
            duong_ra = os.path.join(thu_muc_bai, id8 + ".m4a")
            luc_bat_dau_bai = time.monotonic()
            try:
                giay, lufs, tp = _chuan_hoa_mot_bai(ffmpeg, duong_tep, duong_ra)
            except Exception as loi:  # noqa: BLE001 — một bài hỏng không được
                                        # chặn cả kho, ghi lại rồi đi tiếp
                kq["loi"].append((rel, str(loi)[:200]))
                ghi("  kho nhạc: LỖI {0}: {1}".format(rel, str(loi)[:200]))
                continue
            finally:
                kq["giay_da_dung"] += time.monotonic() - luc_bat_dau_bai

            co_giong, ghi_chu_giong = _do_co_giong(ffmpeg, duong_ra)

            entry_cu = chi_muc["bai"].get(id8, {})
            ten_sach = don_ten(metadata.get("title") or
                                os.path.splitext(os.path.basename(duong_tep))[0])
            loai_moi = _loai_mac_dinh(co_giong, giay)
            # Chủ kênh đã gõ tay (nguồn "kênh", kể cả xoá hết thành rỗng) thì
            # giữ nguyên — CHỈ đoán lại khi entry mới toanh hoặc còn là con
            # đoán của máy (nguồn "đoán từ tên").
            if entry_cu and entry_cu.get("cam_xuc_nguon") == NGUON_KENH:
                cam_xuc_moi = entry_cu.get("cam_xuc") or []
                cam_xuc_nguon_moi = NGUON_KENH
            else:
                cam_xuc_moi = doan_cam_xuc_tu_ten(ten_sach)
                cam_xuc_nguon_moi = NGUON_DOAN
            entry = {
                "id": id8,
                "khoa": khoa,
                "ten": ten_sach,
                "nhom": doan_nhom(os.path.basename(duong_tep), ten_sach),
                "giay": giay,
                "lufs": lufs,
                "tp": tp,
                "co_giong": co_giong,
                "co_giong_ghi_chu": ghi_chu_giong,
                "cam_xuc": cam_xuc_moi,
                "cam_xuc_nguon": cam_xuc_nguon_moi,
                "loai": entry_cu.get("loai", loai_moi) if entry_cu.get("loai_tu_kenh")
                        else loai_moi,
                "loai_mac_dinh_ap_dung": loai_moi,
                "loai_tu_kenh": entry_cu.get("loai_tu_kenh", False),
                "mat_goc": False,
                "nguon": (entry_cu.get("nguon") or []),
                "cap_nhat_luc": _now_iso(),
            }
            _them_nguon_vao_bai(entry, vt, sha1)
            chi_muc["bai"][id8] = entry
            theo_khoa[khoa] = id8

            kq["moi"] += 1
            if co_giong:
                kq["co_giong"] += 1
            if giay < GIAY_TOI_THIEU_DU_DUNG:
                kq["qua_ngan"] += 1
            _luu_chi_muc(thu_muc_dich, chi_muc)

        kq["het_ngan_sach"] = het_ngan_sach

        for b in chi_muc["bai"].values():
            con_ton = any(n.get("duong_tuong_doi") in tim_thay
                          for n in (b.get("nguon") or []))
            b["mat_goc"] = not con_ton
            if not con_ton:
                kq["mat_goc"] += 1

        _luu_chi_muc(thu_muc_dich, chi_muc)
        kq["tong_bai_trong_kho"] = len(chi_muc["bai"])
    finally:
        _nha_khoa(duong_khoa)
    return kq


def _tim_theo_duong_nguon(chi_muc: Dict[str, Any],
                           rel: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    for id8, b in chi_muc["bai"].items():
        for n in (b.get("nguon") or []):
            if n.get("duong_tuong_doi") == rel:
                return id8, n
    return None, None


def _them_nguon_vao_bai(entry: Dict[str, Any], vt: Dict[str, Any],
                         sha1: str) -> None:
    entry.setdefault("nguon", [])
    for n in entry["nguon"]:
        if n.get("duong_tuong_doi") == vt["duong_tuong_doi"]:
            n.update(vt)
            n["sha1"] = sha1
            return
    moi = dict(vt)
    moi["sha1"] = sha1
    entry["nguon"].append(moi)


def _bo_nguon_khoi_bai(entry: Dict[str, Any], rel: str) -> None:
    entry["nguon"] = [n for n in (entry.get("nguon") or [])
                       if n.get("duong_tuong_doi") != rel]


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


# ── Việc 2 — chọn nhạc theo phần + dựng lớp nhạc nền ─────────────────────────


#: Độ dài tối thiểu một bài để được NỐI (acrossfade cần cả hai bài dài hơn
#: đoạn hoà). Bài ngắn hơn thế không dùng được kể cả để lấp.
GIAY_TOI_THIEU_NOI = 12.0
#: Một phần nối tối đa bấy nhiêu bài — chặn vòng lặp khi kho toàn bài ngắn.
TOI_DA_BAI_MOI_PHAN = 6
#: Loại bài dùng trong bấy nhiêu video gần nhất (thiếu ứng viên thì nới dần).
SO_VIDEO_TRANH_LAP = 10
#: Nhãn cảm xúc chỉ được dùng để lọc khi ≥ ngần này phần kho có nhãn do CHỦ
#: KÊNH gắn (không tính nhãn "đoán từ tên") — quyết định 5 của thiết kế.
TI_LE_CO_NHAN_DE_LOC = 0.6


def _bai_dung_duoc(b: Dict[str, Any]) -> bool:
    """Bài có giọng hát/nói → loại (thiết kế (g)); còn lại dùng được."""
    if b.get("co_giong") is True or str(b.get("loai", "")).strip() == "co_giong":
        return False
    return float(b.get("giay") or 0.0) >= GIAY_TOI_THIEU_NOI


def _bam(hat_giong: str, id8: str) -> str:
    return hashlib.sha1("{0}:{1}".format(hat_giong, id8).encode("utf-8")).hexdigest()


def lich_su_dung(goc: str, ma_kenh: str, bo_qua: str = ""
                 ) -> Tuple[List[List[str]], Dict[str, float]]:
    """Nhạc đã dùng ở các video trước của kênh — MỚI NHẤT trước.

    Nguồn: `PROJECTS/AUTO/<kênh>/*/8-nhac.json` (khâu dựng ghi cạnh video, tệp
    nhỏ nên bộ dọn đĩa giữ lại) và `CHANNEL/<kênh>/ho-so-video/*.json` khóa
    `nhac.da_dung` (hồ sơ video, Việc 3 — chưa có thì thôi). `bo_qua` = thư
    mục lượt đang dựng (không tính chính nó). Trả `(danh sách id theo video,
    {id: lần dùng gần nhất (epoch)})`.
    """
    muc: List[Tuple[float, List[str]]] = []
    goc_kenh = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    bo_qua = os.path.normcase(os.path.abspath(bo_qua)) if bo_qua else ""
    try:
        cac_luot = os.listdir(goc_kenh)
    except OSError:
        cac_luot = []
    for luot in cac_luot:
        d = os.path.join(goc_kenh, luot)
        if bo_qua and os.path.normcase(os.path.abspath(d)) == bo_qua:
            continue
        duong = os.path.join(d, "8-nhac.json")
        try:
            with open(duong, "r", encoding="utf-8") as tep:
                du = json.load(tep)
            luc = float(du.get("tao_luc") or os.path.getmtime(duong))
            ids = [str(x) for x in (du.get("da_dung") or [])]
        except (OSError, ValueError, TypeError, AttributeError):
            continue
        if ids:
            muc.append((luc, ids))
    thu_hs = os.path.join(goc, "CHANNEL", ma_kenh, "ho-so-video")
    try:
        cac_hs = [t for t in os.listdir(thu_hs) if t.endswith(".json")]
    except OSError:
        cac_hs = []
    for t in cac_hs:
        try:
            with open(os.path.join(thu_hs, t), "r", encoding="utf-8") as tep:
                du = json.load(tep)
            nhac = du.get("nhac") or {}
            ids = [str(x) for x in (nhac.get("da_dung") or [])]
            luc = float(nhac.get("tao_luc") or os.path.getmtime(os.path.join(thu_hs, t)))
        except (OSError, ValueError, TypeError, AttributeError):
            continue
        if ids and not any(set(ids) == set(m[1]) for m in muc):
            muc.append((luc, ids))
    muc.sort(key=lambda x: -x[0])
    lan: Dict[str, float] = {}
    for luc, ids in muc:
        for i in ids:
            lan[i] = max(lan.get(i, 0.0), luc)
    return [ids for _l, ids in muc], lan


def chon_nhac(cac_phan: Sequence[Any], chi_muc: Dict[str, Any],
              da_dung: Sequence[str], *, hat_giong: str,
              video_gan_day: Optional[Sequence[Sequence[str]]] = None,
              lan_dung_cuoi: Optional[Dict[str, float]] = None,
              cam_xuc_phan: Optional[Sequence[Sequence[str]]] = None,
              noi_bai_giay: float = 4.0,
              thu_muc_bai: str = "") -> List[List[str]]:
    """Chọn nhạc cho TỪNG phần — thiết kế mục 2g. THUẦN (trừ kiểm tệp có thật
    khi truyền `thu_muc_bai`).

    `cac_phan[k]` là khung nhạc phần k (`{"bat_dau", "ket_thuc"}` — xem
    `phan_video.khung_nhac`). Trả về danh sách CÙNG độ dài, mỗi phần tử là
    danh sách id8 (bài đầu + các bài nối thêm khi bài đầu không đủ dài).

    LỆCH KHUNG VIỆC 1: khung cũ trả `List[str]` (một bài/phần); thiết kế lại
    đòi "phần dài thì ghép 2–3 bài", nên mỗi phần phải là một DANH SÁCH.

    * Loại: bài có giọng; bài đã dùng TRONG video này (`da_dung` + các phần
      trước); bài dùng trong 10 video gần nhất — không đủ ứng viên thì nới
      dần (9, 8, … 0 video).
    * Phần có nhãn cảm xúc (`cam_xuc_phan[k]`) VÀ ≥60% kho có nhãn chủ kênh
      gắn → lọc theo nhãn (lọc ra rỗng thì bỏ lọc, không bỏ nhạc).
    * Xếp: lần dùng gần nhất TĂNG DẦN (chưa dùng bao giờ lên đầu), rồi
      `sha1(hat_giong:id)` — cùng mã gói luôn ra cùng lựa chọn.
    * Bài đầu không đủ khung → nối thêm, ưu tiên CÙNG NHÓM với bài liền trước.
    """
    bai = (chi_muc or {}).get("bai") or {}
    lan = dict(lan_dung_cuoi or {})

    def co_tep(i: str) -> bool:
        return not thu_muc_bai or os.path.isfile(os.path.join(thu_muc_bai, i + ".m4a"))

    dung = {i: b for i, b in bai.items() if _bai_dung_duoc(b) and co_tep(i)}
    if not dung:
        return []

    def giay(i: str) -> float:
        return float(dung[i].get("giay") or 0.0)

    def khoa(i: str) -> Tuple[float, str]:
        return (float(lan.get(i, 0.0)), _bam(hat_giong, i))

    chinh = sorted((i for i, b in dung.items()
                    if str(b.get("loai", "")).strip() != "lap"
                    and giay(i) >= GIAY_TOI_THIEU_DU_DUNG), key=khoa)
    lap = sorted((i for i in dung if i not in chinh), key=khoa)
    if not chinh:
        chinh, lap = lap, []

    # Ước số bài cần cho cả video, để biết phải nới "10 video gần nhất" tới đâu.
    tb = sum(giay(i) for i in chinh) / max(1, len(chinh))
    can = 0
    for p in cac_phan:
        L = float(p["ket_thuc"]) - float(p["bat_dau"])
        can += max(1, int(math.ceil(max(0.0, L - noi_bai_giay) /
                                    max(1.0, tb - noi_bai_giay))))
    gan = [list(v) for v in (video_gan_day or [])][:SO_VIDEO_TRANH_LAP]
    cam_ngoai: set = set()
    for n in range(len(gan), -1, -1):
        cam_ngoai = set().union(*gan[:n]) if n else set()
        if sum(1 for i in chinh if i not in cam_ngoai and i not in da_dung) >= can:
            break

    co_nhan = sum(1 for b in dung.values()
                  if b.get("cam_xuc") and b.get("cam_xuc_nguon") == NGUON_KENH)
    loc_cam_xuc = co_nhan >= TI_LE_CO_NHAN_DE_LOC * len(dung)

    trong_video: set = set(da_dung)
    ket: List[List[str]] = []
    for k, p in enumerate(cac_phan):
        L = float(p["ket_thuc"]) - float(p["bat_dau"])
        ung = [i for i in chinh if i not in trong_video and i not in cam_ngoai]
        if not ung:
            ung = [i for i in chinh if i not in trong_video]
        if not ung:          # kho quá nhỏ cho video này — cho lặp lại bài
            truoc = ket[-1][-1] if ket and ket[-1] else ""
            ung = [i for i in chinh if i != truoc] or list(chinh)
        if loc_cam_xuc and cam_xuc_phan and k < len(cam_xuc_phan) and cam_xuc_phan[k]:
            muon = set(cam_xuc_phan[k])
            hop = [i for i in ung if muon & set(dung[i].get("cam_xuc") or [])]
            if hop:
                ung = hop
        chon = [ung[0]]
        trong_video.add(ung[0])
        du = giay(ung[0])
        while du < L and len(chon) < TOI_DA_BAI_MOI_PHAN:
            nhom = dung[chon[-1]].get("nhom", "")
            con = [i for i in chinh + lap
                   if i not in trong_video and i not in cam_ngoai and giay(i) > 2 * noi_bai_giay]
            if not con:
                con = [i for i in chinh + lap
                       if i not in trong_video and giay(i) > 2 * noi_bai_giay]
            if not con:
                con = [i for i in chinh if i != chon[-1] and giay(i) > 2 * noi_bai_giay]
            if not con:
                break
            cung_nhom = [i for i in con if nhom and dung[i].get("nhom") == nhom]
            ke = sorted(cung_nhom or con, key=khoa)[0]
            chon.append(ke)
            trong_video.add(ke)
            du += giay(ke) - noi_bai_giay
        ket.append(chon)
    return ket


def lenh_lop_nhac(goc: str, chi_muc: Dict[str, Any], lua_chon: Sequence[Sequence[str]],
                  cac_phan: Sequence[Any], ffmpeg: str, duong_ra: str, *,
                  nhac_duoi_giong_db: float = 18.0,
                  nhac_nghi_giua_phan: float = 2.0,
                  nhac_noi_bai_giay: float = 4.0,
                  lufs_giong_do: float = -14.5,
                  tong_giay: float = 0.0,
                  thu_muc_bai: str = "") -> Dict[str, Any]:
    """Dựng lớp nhạc nền CẢ VIDEO → `duong_ra` (`8-nhac-nen.m4a`) + `8-nhac.json`.

    `cac_phan[k]` = khung nhạc phần k (`phan_video.khung_nhac`: bat_dau,
    ket_thuc, mo_vao, mo_ra — đã tính sẵn khoảng im `nhac_nghi_giua_phan`
    giữa hai phần, nên tham số đó ở đây chỉ để ghi vào JSON). Chuỗi mỗi phần:

        volume={g}dB (từng bài) → acrossfade=d=4:c1=qsin:c2=qsin → atrim=0:L
        → afade in/out → adelay={S_ms}:all=1 → apad=whole_dur=T

    gộp bằng `amix=normalize=0` (BẪY TRỘN TIẾNG: `normalize` mặc định hạ mỗi
    đầu vào). `g = (LUFS giọng − nhac_duoi_giong_db) − LUFS bài đo thật` —
    kho đã chuẩn −32 nên g ≈ −0,5 dB; dùng số đo từng bài cho chính xác.
    Không `-stream_loop`, không sidechain. Ném lỗi khi FFmpeg hỏng hoặc độ
    dài ra lệch — nơi gọi lùi về dựng không nhạc.
    """
    bai = (chi_muc or {}).get("bai") or {}
    thu_muc_bai = thu_muc_bai or os.path.join(duong_kho(goc), TEN_THU_MUC_BAI)
    T = float(tong_giay)
    if T <= 0:
        raise ValueError("thiếu độ dài video")
    if len(lua_chon) != len(cac_phan):
        raise ValueError("số phần nhạc không khớp số khung")
    muc_tieu = float(lufs_giong_do) - float(nhac_duoi_giong_db)
    d = float(nhac_noi_bai_giay)

    vao: List[str] = []
    loc: List[str] = []
    nhan_phan: List[str] = []
    mo_ta: List[Dict[str, Any]] = []
    da_dung: List[str] = []
    for k, (ids, p) in enumerate(zip(lua_chon, cac_phan)):
        S, E = float(p["bat_dau"]), float(p["ket_thuc"])
        L = E - S
        if L <= 0.3 or not ids:
            continue
        mv, mr = float(p.get("mo_vao", 1.5)), float(p.get("mo_ra", 2.0))
        cac_bai = []
        for j, i in enumerate(ids):
            tep = os.path.join(thu_muc_bai, i + ".m4a")
            if not os.path.isfile(tep):
                raise RuntimeError("kho nhạc thiếu tệp {0}.m4a".format(i))
            b = bai.get(i, {})
            lufs = float(b.get("lufs") or -32.0)
            g = max(-30.0, min(12.0, muc_tieu - lufs))
            so = len(vao) // 2      # mỗi đầu vào là một cặp ("-i", tệp)
            vao += ["-i", tep]
            loc.append("[{0}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                       "volume={1:.2f}dB[n{2}b{3}]".format(so, g, k, j))
            cac_bai.append({"id": i, "ten": b.get("ten", ""), "nhom": b.get("nhom", ""),
                            "giay": round(float(b.get("giay") or 0.0), 2),
                            "lufs": round(lufs, 2), "gain_db": round(g, 2)})
            da_dung.append(i)
        dang = "n{0}b0".format(k)
        for j in range(1, len(ids)):
            moi = "n{0}x{1}".format(k, j)
            loc.append("[{0}][n{1}b{2}]acrossfade=d={3:.2f}:c1=qsin:c2=qsin[{4}]".format(
                dang, k, j, d, moi))
            dang = moi
        loc.append(
            "[{0}]atrim=0:{1:.3f},asetpts=PTS-STARTPTS,"
            "afade=t=in:st=0:d={2:.3f},afade=t=out:st={3:.3f}:d={4:.3f},"
            "adelay={5}:all=1,apad=whole_dur={6:.3f}[p{7}]".format(
                dang, L, mv, max(0.0, L - mr), mr, int(round(S * 1000)), T, k))
        nhan_phan.append("[p{0}]".format(k))
        mo_ta.append({"so": p.get("so", k + 1), "bat_dau": round(S, 3),
                      "ket_thuc": round(E, 3), "mo_vao": round(mv, 3),
                      "mo_ra": round(mr, 3), "bai": cac_bai})
    if not nhan_phan:
        raise RuntimeError("không có phần nào để đặt nhạc")
    if len(nhan_phan) == 1:
        loc.append("{0}atrim=0:{1:.3f}[ra]".format(nhan_phan[0], T))
    else:
        loc.append("{0}amix=inputs={1}:duration=longest:dropout_transition=0:"
                   "normalize=0,atrim=0:{2:.3f}[ra]".format(
                       "".join(nhan_phan), len(nhan_phan), T))
    tam = duong_ra + ".dang-ghi.m4a"
    cmd = ([ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-y"] + vao +
           ["-filter_complex", ";".join(loc), "-map", "[ra]",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", "-threads", "2", tam])
    text = _chay_ffmpeg(cmd, timeout=1800.0)
    if text is None or not os.path.isfile(tam):
        _xoa_neu_co(tam)
        raise RuntimeError("FFmpeg không dựng được lớp nhạc nền: " +
                           " | ".join((text or "").strip().splitlines()[-3:])[:300])
    dai = _doc_do_dai_giay(_chay_ffmpeg([ffmpeg, "-hide_banner", "-nostdin", "-i", tam]) or "")
    if dai <= 0 or abs(dai - T) > 1.0:
        _xoa_neu_co(tam)
        raise RuntimeError("lớp nhạc nền dài {0:.1f}s, video {1:.1f}s — lệch".format(dai, T))
    os.replace(tam, duong_ra)
    do = do_lufs_that(ffmpeg, duong_ra)
    ket = {
        "tao_luc": time.time(),
        "tong_giay": round(T, 3),
        "lufs_giong": round(float(lufs_giong_do), 2),
        "nhac_duoi_giong_db": float(nhac_duoi_giong_db),
        "nhac_nghi_giua_phan": float(nhac_nghi_giua_phan),
        "nhac_noi_bai_giay": d,
        "lufs_nhac_do": round(do["lufs"], 2) if do else None,
        "phan": mo_ta,
        "da_dung": list(dict.fromkeys(da_dung)),
        "tep": os.path.basename(duong_ra),
    }
    _ghi_json_nguyen_tu(os.path.join(os.path.dirname(duong_ra) or ".", "8-nhac.json"), ket)
    return ket


# ── `python -m core.kho_nhac [--het]` ────────────────────────────────────────


def _chuoi_bao_cao(kq: Dict[str, Any]) -> str:
    dong = [
        "Kho nhạc: {0} bài mới, {1} bỏ qua (không đổi), {2} trùng đã "
        "gộp.".format(kq.get("moi", 0), kq.get("bo_qua_khong_doi", 0),
                       kq.get("trung_gop", 0)),
        "  có giọng: {0} · quá ngắn (<{1:.0f}s): {2} · mất gốc: "
        "{3}.".format(kq.get("co_giong", 0), GIAY_TOI_THIEU_DU_DUNG,
                       kq.get("qua_ngan", 0), kq.get("mat_goc", 0)),
        "  tổng trong kho: {0}. tốn {1:.0f} giây xử lý FFmpeg.".format(
            kq.get("tong_bai_trong_kho", 0), kq.get("giay_da_dung", 0.0)),
    ]
    if kq.get("loi"):
        dong.append("  lỗi {0} tệp: {1}".format(
            len(kq["loi"]),
            "; ".join("{0}: {1}".format(t, e) for t, e in kq["loi"][:5])))
    if kq.get("het_ngan_sach"):
        dong.append("  HẾT NGÂN SÁCH GIÂY — còn {0} bài chưa xử lý, chạy lại "
                     "(hoặc thêm --het) để tiếp tục.".format(kq.get("con_lai", 0)))
    if kq.get("loi_chung"):
        dong.append("  " + kq["loi_chung"])
    return "\n".join(dong)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m core.kho_nhac",
        description="Nạp/chuẩn hoá kho nhạc nền (PROJECTS/music, chỉ đọc) "
                     "vào workspace/kho-nhac/ — tăng dần, không mạng.")
    ap.add_argument("--het", action="store_true",
                     help="bỏ ngân sách giây, xử lý hết trong một lượt "
                          "(dùng khi chạy tay lần đầu)")
    ap.add_argument("--ngan-sach", type=float, default=NGAN_SACH_MAC_DINH_GIAY,
                     help="ngân sách giây xử lý FFmpeg cho lượt này (mặc định "
                          "{0:.0f}s; bỏ qua nếu có --het)".format(
                              NGAN_SACH_MAC_DINH_GIAY))
    ap.add_argument("--goc", default="",
                     help="thư mục cài tool (mặc định tự dò theo vị trí tệp này)")
    ns = ap.parse_args(argv)

    ngan_sach = None if ns.het else ns.ngan_sach
    kq = cap_nhat(ns.goc, ngan_sach, ghi=print)
    print(_chuoi_bao_cao(kq))
    return 1 if kq.get("loi_chung") else 0


if __name__ == "__main__":
    raise SystemExit(main())
