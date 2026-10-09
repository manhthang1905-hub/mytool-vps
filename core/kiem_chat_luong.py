"""core/kiem_chat_luong.py — CỔNG CHẤT LƯỢNG THÀNH PHẨM (trừ ảnh bìa), chạy lúc bàn giao.

═══ VÌ SAO (chủ dự án 09/10/2026) ═══

"Mọi thứ phải có logic và tự phát triển" + luật 07/10 "thà không đăng còn hơn sản phẩm kém". Cổng cũ
(`core/qa_truoc_dang.py`) chỉ kiểm "có đủ tệp, mở được, có tiếng, đúng khổ, phụ đề không quá đuôi" — KHÔNG đo
được video nghe/xem có ổn không, và không để lại số nào cho vòng học đối chiếu với giữ chân/CTR. Gói đã đăng thì
mp4/clip/giọng bị dọn (`don_dep`), nên lúc BÀN GIAO là lần cuối còn đo được — module này đo đúng lúc đó, tự sửa
thứ sửa được rẻ, chặn thứ không sửa được, và ghi số vào `9-chat-luong.json` → hồ sơ video (`cl_*`).

Kiểm toán 09/10/2026: `workspace/chan-doan/chat-luong-2026-10-09.md` (ngưỡng dưới đây lấy từ đó).

═══ ĐO GÌ (mọi phép đo cục bộ, FFmpeg, 0 đồng; nơi gọi GIỮ KHE "nang") ═══

* Tiếng (`8-video.mp4`): độ to tích hợp (LUFS, ebur128), đỉnh thật (dBTP), LRA, khoảng lặng (silencedetect)
  — tách khoảng lặng NẰM TRONG chỗ nghỉ giữa phần (`8-phan.json: ranh`, chủ ý) với khoảng lặng ngoài đó (lỗi).
* Phụ đề: lệch mốc so tiếng nói (khởi âm đo trên `2-giong-doc.mp3` ↔ mốc bắt đầu `3-phu-de.srt`), CPS, dòng
  dài, chồng mốc, khối rỗng, mốc vượt đuôi video, đoạn nói dài không có phụ đề.
* Hình: khung ĐỨNG (gói tin hình gần rỗng liên tiếp — đọc gói, không giải mã: < 1 giây cho cả video), khung ĐEN
  ngoài chỗ chuyển phần (chỉ giải mã khung khoá), clip TRÙNG HỆT (md5), clip TĨNH (đứng liền ≥ 4/8 giây —
  freezedetect trên khung 64×36, 6 FFmpeg song song), bitrate.
* Kịch bản: lời rào/tự giới thiệu trong ~60 giây đầu, lặp 12-gram, độ dài mở đầu (trục `mo_dau` có sẵn).
* Siêu dữ liệu: tiêu đề, mô tả (rỗng = chặn), chương (hợp lệ theo luật YouTube: đầu 00:00, ≥3, tăng dần, cách
  ≥10 giây, không vượt đuôi video), thẻ (tổng ≤ 500 ký tự — YouTube từ chối hơn).

═══ SỬA TỰ ĐỘNG (rẻ, không gọi mạng) RỒI ĐO LẠI ═══

* Độ to ngoài khoảng / đỉnh thật quá trần → chuẩn hoá loudnorm 2 lượt về −14 LUFS, đỉnh −1,5 dBTP; hình chép
  nguyên (`-c:v copy`), ~10–20 giây.
* Phụ đề lệch đều (cả bài sớm/muộn) → dời mốc; mốc vượt đuôi → kẹp/bỏ; chồng mốc → cắt đuôi; khối rỗng → bỏ.
* Mô tả: chương sai luật → bỏ dòng chương hỏng; thẻ > 500 ký tự → cắt bớt thẻ cuối.
* Clip trùng hệt / đen / tĩnh quá ngưỡng → xoá đúng clip đó + video dựng, mở lại khâu clip + dựng
  (`lam_lai_clip_that.dat_lai_khau_clip`) — `tu_chay` làm lại ĐÚNG những cảnh ấy (tốn tiền clip, có trần
  `toi_da_lam_lai_canh`, mỗi cảnh tối đa một lần) rồi bàn giao lại, cổng đo lại từ đầu.

Không sửa được (khoảng lặng chết, đoạn nói không phụ đề, khung đứng dài, mô tả rỗng, phụ đề lệch không đều, hết
lượt làm lại cảnh) → CHẶN bàn giao với lý do rõ + báo động. Phép đo hỏng (không có FFmpeg, tệp không mở được) →
không chặn ở đây: `qa_truoc_dang` đã chặn "không mở được"; thiếu số đo được ghi rõ là thiếu, không bịa.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["NGUONG", "TEP_KET_QUA", "KetQuaChatLuong", "do_luot", "danh_gia", "kiem_va_sua",
           "sua_mo_ta", "chi_so_ho_so", "doc_ket_qua", "doc_nhat_ky", "duong_nhat_ky",
           "do_am", "do_goi_hinh", "doan_dong_bang", "do_phu_de", "lech_phu_de", "do_kich_ban", "do_meta"]

TEP_KET_QUA = "9-chat-luong.json"
PHIEN_BAN = 1

#: Ngưỡng — nguồn số ở `workspace/chan-doan/chat-luong-2026-10-09.md`.
NGUONG: Dict[str, float] = {
    # Tiếng. YouTube hạ video to hơn −14 LUFS, KHÔNG nâng video nhỏ hơn → nhỏ là mất thật. Đo thật: giọng mọi gói
    # −14,4 (`8-nhac.json`, 79/79), video thành phẩm −14,5 LUFS / −3,6 dBTP.
    "lufs_muc_tieu": -14.0, "lufs_duoi": -16.5, "lufs_tren": -11.5, "tp_tran": -1.0, "tp_muc_tieu": -1.5,
    # Lặng: chỗ nghỉ giữa phần 3,0–4,8 giây là CHỦ Ý (`giay_nghi_phan` 3 s, đo giọng TL2-0015 4,8 s ở ranh phần).
    "im_ngoai_ranh_chan": 3.5, "im_trong_ranh_chan": 8.0, "im_dau_chan": 2.0,
    # Phụ đề (không đốt vào hình: `dot_phu_de` false — là phụ đề CC tải lên). Đo: CPS p95 7,4–9,2; dòng ≤ 53.
    # Khớp mốc (`khop05`, xem `lech_phu_de`): đúng 0,55–0,64, lệch 1 s 0,17–0,29, ngẫu nhiên ~0,3.
    "khop05_dat": 0.42, "lech_pd_sua": 0.35,
    "pd_tre_cuoi": 1.0, "cps95_canh_bao": 14.0, "dong_canh_bao": 42,
    "pd_thieu_chan_giay": 8.0,
    # Hình: cảnh dài nhất đo được 14 s (giữ khung 6 s), giữ khung trung vị 1,2–1,6%. Clip Veo TĨNH (đứng ≥ 4/8 s
    # — nhìn như ảnh tĩnh, đúng thứ luật 07/10 cấm): đo 4 lượt còn clip 3%, 5%, 10%, 17%. Làm lại một clip 500₫.
    # Đọc gói tin hụt ~1–2 s đầu mỗi đoạn đứng → chặn ở 7 s đo được (≈ 8–9 s thật).
    "dong_bang_chan_giay": 7.0, "dong_bang_chan_pct": 8.0, "clip_giay_tinh": 4.0, "clip_tinh_pct_sua": 10.0,
    "toi_da_lam_lai_canh": 30, "bitrate_canh_bao_mbps": 2.0,
    # Siêu dữ liệu: video thắng TL4 20–52 ký tự tiêu đề, 6–11 chương.
    "tieu_de_canh_bao": 60, "chuong_toi_da": 15, "the_toi_da_ky_tu": 500,
    # Kịch bản.
    "lap_canh_bao_pct": 3.0, "mo_dau_canh_bao_giay": 120.0,
}

#: Câu rào / tự giới thiệu / xin đăng ký trong ~60 giây đầu (≈ 330 ký tự tiếng Nhật): chẩn đoán 07/10 mục D
#: (「人生の羅針盤へようこそ」 68s, 「本題に入る前に」…). CHỈ cảnh báo + ghi số: chưa đủ bằng chứng nhân quả để chặn.
CAU_RAO = ("ようこそ", "チャンネル登録", "高評価", "最後までご覧", "本題に入る前に", "こんにちは", "それでは早速",
           "先にルールを決め", "ここから本題", "この動画の立場")
KY_TU_MO_DAU = 330

_CO_TAO = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
_DAU = re.compile(r"[\s、。，,．.！!？?「」『』（）()【】・…ー―〜~\"'：:；;｜|]")
_MOC = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")
_CHUONG = re.compile(r"^\s*((?:\d{1,2}:)?\d{1,2}:\d{2})\s+(\S.*)$")


# ── tiện ích ─────────────────────────────────────────────────────────────────

def _chay(ffmpeg: str, ts: Sequence[str], timeout: float = 300.0) -> Tuple[str, str, int]:
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", *ts], capture_output=True, text=True,  # noqa: S603
                           encoding="utf-8", errors="replace", timeout=timeout, creationflags=_CO_TAO)
        return r.stdout or "", r.stderr or "", r.returncode
    except (OSError, subprocess.SubprocessError) as loi:
        return "", str(loi), -1


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def _giay(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000.0


def _giay_chuong(chu: str) -> int:
    p = [int(x) for x in chu.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def _dai_media(tho: str) -> float:
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", tho)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def _p(xs: Sequence[float], q: float) -> float:
    s = sorted(xs)
    return s[int(round(q * (len(s) - 1)))] if s else 0.0


# ── TIẾNG ────────────────────────────────────────────────────────────────────

def do_am(ffmpeg: str, duong: str, *, nguong_lang: str = "-50dB", lang_toi_thieu: float = 2.0) -> Dict[str, Any]:
    """Một lượt giải mã CHỈ tiếng: ebur128 (I, LRA, đỉnh thật) + silencedetect. Trả {} nếu không đọc được."""
    _o, tho, ma = _chay(ffmpeg, ["-i", duong, "-vn", "-af",
                                 "ebur128=peak=true:framelog=quiet,silencedetect=n={0}:d={1}".format(
                                     nguong_lang, lang_toi_thieu), "-f", "null", "-"], timeout=600)
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", tho)
    if ma != 0 or not i:
        return {}
    tp = re.findall(r"Peak:\s*(-?[\d.]+|-inf) dBFS", tho)
    lra = re.findall(r"LRA:\s*(-?[\d.]+) LU", tho)
    im: List[List[float]] = []
    bd: Optional[float] = None
    for d in tho.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", d)
        if m:
            bd = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", d)
        if m:
            im.append([round(float(m.group(1)) - float(m.group(2)), 2), round(float(m.group(2)), 2)])
            bd = None
    dai = _dai_media(tho)
    if bd is not None and dai > bd:      # lặng tới hết tệp: silencedetect không in silence_end
        im.append([round(bd, 2), round(dai - bd, 2)])
    tp_so = float(tp[-1]) if tp and tp[-1] != "-inf" else -99.0
    return {"lufs": float(i[-1]), "tp": tp_so, "lra": float(lra[-1]) if lra else None, "im": im,
            "giay": round(dai, 2)}


def _trong_ranh(t0: float, dai: float, ranh: Sequence[Tuple[float, float]], du: float = 1.0) -> bool:
    return any(t0 >= a - du and t0 + dai <= b + du for a, b in ranh)


def ranh_phan(thu_muc_luot: str) -> List[Tuple[float, float]]:
    """Chỗ nghỉ giữa phần (trục video) — `8-phan.json: ranh[a_moi, b_moi]`. Không có tệp → []."""
    du = _doc_json(os.path.join(thu_muc_luot, "8-phan.json")) or {}
    ra = []
    for r in du.get("ranh") or []:
        try:
            ra.append((float(r.get("a_moi", r.get("a"))), float(r.get("b_moi", r.get("b")))))
        except (TypeError, ValueError):
            continue
    return ra


# ── HÌNH ─────────────────────────────────────────────────────────────────────

def do_goi_hinh(ffmpeg: str, duong: str) -> List[Tuple[float, int, bool]]:
    """(mốc giây, cỡ byte, là khung khoá) từng gói tin hình — `-c copy -f framecrc`: chỉ tách luồng, KHÔNG giải
    mã. framecrc in `F=0x..` cho gói KHÔNG phải khung khoá."""
    out, _e, ma = _chay(ffmpeg, ["-i", duong, "-map", "0:v:0", "-c", "copy", "-f", "framecrc", "-"], timeout=300)
    if ma != 0:
        return []
    tb, ra = None, []
    for d in out.splitlines():
        if d.startswith("#tb"):
            m = re.search(r"(\d+)/(\d+)", d)
            tb = int(m.group(1)) / int(m.group(2)) if m else None
        elif d and not d.startswith("#") and tb:
            p = [x.strip() for x in d.split(",")]
            try:
                ra.append((int(p[2]) * tb, int(p[4]), "F=" not in d))
            except (IndexError, ValueError):
                continue
    ra.sort()
    return ra


def doan_dong_bang(goi: Sequence[Tuple[Any, ...]], *, ti_le: float = 0.02,
                   toi_thieu: float = 2.0) -> List[Tuple[float, float]]:
    """Đoạn khung ĐỨNG: gói tin KHÔNG-khoá liên tiếp < `ti_le` × trung vị cỡ gói (khung lặp lại y hệt nén về gần
    0 byte — đúng thứ `tpad=clone` / clip đứng tạo ra); khung khoá (luôn to) không cắt đoạn. Đối chiếu
    freezedetect giải mã đủ trên video thật: cùng kết quả (0 đoạn), nhanh hơn ~100 lần (0,7 s so 70 s)."""
    goi = [(g[0], g[1]) for g in goi if not (len(g) > 2 and g[2])]
    if not goi:
        return []
    moc = _p([s for _t, s in goi], 0.9) or 1        # mốc = gói CÓ chuyển động (p90), không bị đoạn đứng kéo xuống
    ra, bd, truoc = [], None, None
    for t, s in goi:
        if s < moc * ti_le:
            if bd is None:
                bd = truoc if truoc is not None else t
        elif bd is not None:
            if t - bd >= toi_thieu:
                ra.append((round(bd, 2), round(t - bd, 2)))
            bd = None
        truoc = t
    if bd is not None and goi[-1][0] - bd >= toi_thieu:
        ra.append((round(bd, 2), round(goi[-1][0] - bd, 2)))
    return ra


def do_khung_den(ffmpeg: str, duong: str) -> List[float]:
    """Mốc các khung KHOÁ đen (chỉ giải mã khung khoá, ~4 s / 17 phút 1080p)."""
    _o, tho, _m = _chay(ffmpeg, ["-skip_frame", "nokey", "-i", duong, "-an", "-vf",
                                 "scale=64:36,blackframe=amount=98:threshold=24", "-f", "null", "-"], timeout=300)
    return [round(float(t), 2) for t in re.findall(r"blackframe.*?\bt:([\d.]+)", tho)]


def giay_dung_clip(ffmpeg: str, tep: str) -> Optional[float]:
    """Tổng giây ĐỨNG HÌNH LIỀN của một clip (freezedetect −50 dB trên khung 64×36, chỉ đoạn liền ≥ 4 s — đoạn
    đứng ngắn xen chuyển động là nhịp tự nhiên của nét vẽ phẳng: đo d=1 thì 32–53% clip "dính", vô nghĩa).
    Đo 09/10: gói tin KHÔNG phân biệt được clip tĩnh của Veo (nén nhiễu) — phải giải mã; clip 8 s ~0,2 s."""
    # `-skip_frame noref`: bỏ giải mã khung không làm tham chiếu — nhanh ~40% (đo 105 clip: 12,0 s so 20,3 s),
    # khớp 17/18 clip tĩnh với giải mã đủ.
    _o, tho, ma = _chay(ffmpeg, ["-threads", "1", "-skip_frame", "noref", "-i", tep, "-an", "-vf",
                                 "scale=64:36,freezedetect=n=-50dB:d=4",
                                 "-f", "null", "-"], timeout=120)
    if ma != 0:
        return None
    dai = _dai_media(tho)
    tong, bd = 0.0, None
    for d in tho.splitlines():
        m = re.search(r"freeze_start: ([\d.]+)", d)
        if m:
            bd = float(m.group(1))
        m = re.search(r"freeze_duration: ([\d.]+)", d)
        if m:
            tong += float(m.group(1))
            bd = None
    if bd is not None and dai > bd:      # đứng tới hết clip: không có freeze_end
        tong += dai - bd
    return round(tong, 2)


def _md5(tep: str) -> str:
    h = hashlib.md5()  # noqa: S324 — so trùng nội dung, không phải bảo mật
    with open(tep, "rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def do_clip(ffmpeg: str, thu_muc_luot: str, giay_tinh: float = 4.0, luong: int = 0) -> Dict[str, Any]:
    """Clip từng cảnh `6-clip/<id>.mp4`: md5 trùng hệt + TĨNH (đứng ≥ `giay_tinh` giây — nửa clip Veo 8 s).
    `luong` FFmpeg một luồng chạy song song (khe "nang" độc quyền máy nên dùng được CPU)."""
    from concurrent.futures import ThreadPoolExecutor  # noqa: PLC0415

    canh = _doc_json(os.path.join(thu_muc_luot, "4-canh.json")) or []
    ds: List[Tuple[int, str]] = []
    for c in canh if isinstance(canh, list) else []:
        try:
            so = int(c["scene_id"])
        except (KeyError, TypeError, ValueError):
            continue
        tep = os.path.join(thu_muc_luot, "6-clip", "{0}.mp4".format(so))
        if os.path.isfile(tep):
            ds.append((so, tep))
    luong = luong or max(2, min(6, (os.cpu_count() or 4) - 2))
    with ThreadPoolExecutor(max_workers=luong) as ex:
        dung = list(ex.map(lambda x: giay_dung_clip(ffmpeg, x[1]), ds))
    theo_md5: Dict[str, List[int]] = {}
    for (so, tep), g in zip(ds, dung):
        if g is not None:       # chỉ clip GIẢI MÃ ĐƯỢC (clip hỏng là việc của `_loai_clip_hong` khâu dựng)
            theo_md5.setdefault(_md5(tep), []).append(so)
    return {"tong": len(ds), "trung": [sorted(v) for v in theo_md5.values() if len(v) > 1],
            "tinh": [so for (so, _t), g in zip(ds, dung) if g is not None and g >= giay_tinh]}


# ── PHỤ ĐỀ ───────────────────────────────────────────────────────────────────

def doc_srt(duong: str) -> List[Tuple[float, float, str]]:
    try:
        with open(duong, "r", encoding="utf-8-sig", errors="replace") as tep:
            noi = tep.read()
    except OSError:
        return []
    ra = []
    for k in re.split(r"\r?\n\s*\r?\n", noi.strip()):
        dong = [d for d in k.splitlines() if d.strip()]
        for i, d in enumerate(dong):
            m = _MOC.search(d)
            if m:
                ra.append((_giay(*m.group(1, 2, 3, 4)), _giay(*m.group(5, 6, 7, 8)), "\n".join(dong[i + 1:])))
                break
    return ra


def _dong_ho(g: float) -> str:
    ms = max(0, int(round(g * 1000)))
    h, du = divmod(ms, 3600000)
    m, du = divmod(du, 60000)
    s, ms = divmod(du, 1000)
    return "{0:02d}:{1:02d}:{2:02d},{3:03d}".format(h, m, s, ms)


def ghi_srt(duong: str, cues: Sequence[Tuple[float, float, str]]) -> None:
    khoi = ["{0}\n{1} --> {2}\n{3}\n".format(i + 1, _dong_ho(a), _dong_ho(max(b, a + 0.05)), chu)
            for i, (a, b, chu) in enumerate(cues)]
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        tep.write("\n".join(khoi))
    os.replace(tam, duong)


def do_phu_de(cues: Sequence[Tuple[float, float, str]], dai_video: float) -> Dict[str, Any]:
    """Cấu trúc phụ đề giao đi: CPS (ký tự đọc được/giây), dòng dài nhất, chồng mốc, rỗng, vượt đuôi."""
    if not cues:
        return {"so": 0}
    cps, dong = [], []
    chong = rong = 0
    for i, (a, b, chu) in enumerate(cues):
        n = len(_DAU.sub("", chu))
        if not n:
            rong += 1
        cps.append(n / max(0.05, b - a))
        dong.extend(len(x.strip()) for x in chu.splitlines())
        if i and a < cues[i - 1][1] - 0.05:
            chong += 1
    cuoi = max(b for _a, b, _c in cues)
    return {"so": len(cues), "cps50": round(statistics.median(cps), 2), "cps95": round(_p(cps, 0.95), 2),
            "dong_max": max(dong or [0]), "chong": chong, "rong": rong, "cuoi": round(cuoi, 2),
            "vuot_duoi": round(cuoi - dai_video, 2) if dai_video else None}


def khoi_am(ffmpeg: str, mp3: str) -> Tuple[List[float], List[Tuple[float, float]], float]:
    """Khởi âm (hết lặng ≥ 0,25 s) + các đoạn NÓI trên giọng đọc trần — để so mốc phụ đề."""
    _o, tho, ma = _chay(ffmpeg, ["-i", mp3, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-"], timeout=300)
    if ma != 0:
        return [], [], 0.0
    dai = _dai_media(tho)
    bd = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", tho)]
    kt = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", tho)]
    bat_dau_noi = not bd or bd[0] > 0.05          # tệp mở đầu bằng tiếng nói
    on = sorted(set([0.0] + kt)) if bat_dau_noi else sorted(kt)
    noi: List[Tuple[float, float]] = []
    # đoạn nói = khoảng giữa silence_end(i) và silence_start(i+1)
    moc = sorted([(t, "s") for t in bd] + [(t, "e") for t in kt])
    dang = 0.0 if bat_dau_noi else None
    for t, loai in moc:
        if loai == "s" and dang is not None:
            if t - dang > 0.05:
                noi.append((dang, t))
            dang = None
        elif loai == "e":
            dang = t
    if dang is not None and dai > dang:
        noi.append((dang, dai))
    return on, noi, dai


def lech_phu_de(cues: Sequence[Tuple[float, float, str]], khoi: Sequence[float],
                noi: Sequence[Tuple[float, float]]) -> Dict[str, Any]:
    """Lệch mốc phụ đề ↔ tiếng. `khop05` = tỉ lệ câu có khởi âm trong ±0,5 s quanh mốc bắt đầu. Đo 09/10 trên
    giọng thật: phụ đề đúng 0,55–0,64; dời ±1 s còn 0,17–0,29 (trung vị lệch có dấu thì KHÔNG dùng được: khởi âm
    cách nhau ~3 s nên dời 2 s lại "khớp" câu bên cạnh). Nên quét độ dời −3…+3 s tìm `doi_tot` làm `khop05` cao
    nhất: thấp ở 0 mà cao ở `doi_tot` = lệch ĐỀU (dời là sửa); thấp ở mọi độ dời = lệch không đều. Thêm: đoạn nói
    dài nhất không có câu nào phủ."""
    if not cues or not khoi:
        return {}
    import bisect  # noqa: PLC0415

    def khop(doi: float) -> Tuple[float, float]:
        """(tỉ lệ câu khớp ±0,5 s, khoảng cách trung bình tới khởi âm gần nhất)."""
        n, tong = 0, 0.0
        for a, _b, _c in cues:
            t = a + doi
            i = bisect.bisect_left(khoi, t)
            gan = min(abs(khoi[j] - t) for j in (i - 1, i) if 0 <= j < len(khoi))
            n += gan <= 0.5
            tong += min(gan, 2.0)
        return n / float(len(cues)), tong / len(cues)

    k0 = khop(0.0)[0]
    bang = [(b * 0.05,) + khop(b * 0.05) for b in range(-60, 61)]
    k_max = max(k for _d, k, _r in bang)
    # Trong các độ dời gần cao nhất (bình nguyên — khởi âm đều nhau thì nhiều độ dời cùng khớp), lấy độ dời làm
    # khoảng cách trung bình nhỏ nhất, hoà thì độ dời nhỏ nhất.
    doi_tot, k_tot, _r = min((x for x in bang if x[1] >= k_max - 0.02), key=lambda x: (round(x[2], 3), abs(x[0])))
    # đoạn nói không phủ
    phu = sorted((a, b) for a, b, _c in cues)
    thieu_max, thieu_luc = 0.0, None
    for a, b in noi:
        con = [(a, b)]
        for x, y in phu:
            if y <= a or x >= b:
                continue
            moi = []
            for p, q in con:
                if y <= p or x >= q:
                    moi.append((p, q))
                    continue
                if x > p:
                    moi.append((p, x))
                if y < q:
                    moi.append((y, q))
            con = moi
        for p, q in con:
            if q - p > thieu_max:
                thieu_max, thieu_luc = q - p, p
    return {"khop05": round(k0, 3), "doi_tot": round(doi_tot, 2), "khop05_tot": round(k_tot, 3),
            "thieu_max": round(thieu_max, 2), "thieu_luc": round(thieu_luc, 2) if thieu_luc is not None else None}


# ── KỊCH BẢN / SIÊU DỮ LIỆU ──────────────────────────────────────────────────

def do_kich_ban(chu: str) -> Dict[str, Any]:
    sach = _DAU.sub("", chu or "")
    if not sach:
        return {}
    n = 12
    lap = 0.0
    if len(sach) > 200:
        from collections import Counter  # noqa: PLC0415
        dem = Counter(sach[i:i + n] for i in range(len(sach) - n))
        lap = 100.0 * sum(v - 1 for v in dem.values() if v > 1) / max(1, len(sach) - n)
    dau = (chu or "").replace("\n", "")[:KY_TU_MO_DAU]
    return {"ky_tu": len(sach), "lap_pct": round(lap, 2), "rao": [c for c in CAU_RAO if c in dau]}


def _dong_chuong(mo_ta: str) -> List[Tuple[int, int, str]]:
    """[(chỉ số dòng, giây, tên)] các dòng mốc chương trong mô tả."""
    ra = []
    for i, d in enumerate((mo_ta or "").splitlines()):
        m = _CHUONG.match(d)
        if m:
            ra.append((i, _giay_chuong(m.group(1)), m.group(2).strip()))
    return ra


def do_meta(tieu_de: str, mo_ta: str, the: str, dai_video: float) -> Dict[str, Any]:
    ch = _dong_chuong(mo_ta)
    hop_le = bool(ch) and ch[0][1] == 0 and len(ch) >= 3 and all(
        ch[i][1] - ch[i - 1][1] >= 10 for i in range(1, len(ch))) and (
        not dai_video or ch[-1][1] < dai_video - 10)
    the_ds = [x.strip() for x in re.split(r"[,、]", the or "") if x.strip()]
    return {"tieu_de_ky_tu": len(tieu_de or ""), "mo_ta_ky_tu": len((mo_ta or "").strip()),
            "chuong": len(ch), "chuong_hop_le": hop_le, "the": len(the_ds),
            "the_ky_tu": len(",".join(the_ds))}


def sua_mo_ta(mo_ta: str, the: str, dai_video: float, the_toi_da: int = 500) -> Tuple[str, str, List[str]]:
    """Sửa rẻ phần chương + thẻ: bỏ chương vượt đuôi video / không tăng / cách < 10 s, ép chương đầu 00:00; còn
    < 3 chương thì bỏ hẳn dòng chương (YouTube không hiện ít hơn 3). Thẻ cắt đuôi cho tổng ≤ `the_toi_da`."""
    da: List[str] = []
    dong = (mo_ta or "").splitlines()
    ch = _dong_chuong(mo_ta)
    if ch:
        giu: List[Tuple[int, int, str]] = []
        for i, g, ten in ch:
            if dai_video and g >= dai_video - 10:
                continue
            if giu and g - giu[-1][1] < 10:
                continue
            giu.append((i, g, ten))
        if giu and giu[0][1] != 0:
            i0 = giu[0][0]
            dong[i0] = re.sub(r"^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}", "00:00", dong[i0])
            giu[0] = (i0, 0, giu[0][2])
            da.append("chương đầu ép về 00:00")
        bo = {i for i, _g, _t in ch} - {i for i, _g, _t in giu}
        if len(giu) < 3:
            bo = {i for i, _g, _t in ch}
        if bo:
            dong = [d for j, d in enumerate(dong) if j not in bo]
            da.append("bỏ {0} dòng chương sai luật YouTube".format(len(bo)))
    the_ds = [x.strip() for x in re.split(r"[,、]", the or "") if x.strip()]
    the_moi = the
    if len(",".join(the_ds)) > the_toi_da:
        while the_ds and len(",".join(the_ds)) > the_toi_da:
            the_ds.pop()
        the_moi = ", ".join(the_ds)
        da.append("cắt thẻ còn {0} ký tự".format(len(",".join(the_ds))))
    return "\n".join(dong), the_moi, da


# ── ĐO CẢ LƯỢT ───────────────────────────────────────────────────────────────

def _srt_giao(thu_muc_luot: str) -> str:
    """Phụ đề ĐI THEO GÓI — cùng luật `ban_giao_dang.xuat_goi` (8-phu-de.srt nếu có)."""
    p = os.path.join(thu_muc_luot, "8-phu-de.srt")
    return p if os.path.isfile(p) else os.path.join(thu_muc_luot, "3-phu-de.srt")


def do_luot(thu_muc_luot: str, ffmpeg: str, *, gt: Optional[Dict[str, str]] = None,
            nguong: Optional[Dict[str, float]] = None, clip_cu: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Đo mọi trục của một lượt (chỉ đọc). Trục nào không đo được thì vắng mặt, kèm `thieu` liệt kê lý do.
    `clip_cu` (kết quả `do["clip"]` lần đo trước, `{}` = không có clip) → dùng lại, không đo clip lần nữa."""
    ng = dict(NGUONG, **(nguong or {}))
    t0 = time.time()
    do: Dict[str, Any] = {"phien_ban": PHIEN_BAN, "thieu": [], "giay_do": {}}
    video = os.path.join(thu_muc_luot, "8-video.mp4")
    co_ff = bool(ffmpeg) and os.path.isfile(ffmpeg)
    dai = 0.0
    if not co_ff:
        do["thieu"].append("không có FFmpeg")
    elif not os.path.isfile(video):
        do["thieu"].append("không có 8-video.mp4")
    else:
        t = time.time()
        am = do_am(ffmpeg, video)
        do["giay_do"]["am"] = round(time.time() - t, 1)
        if am:
            dai = am.get("giay") or 0.0
            ranh = ranh_phan(thu_muc_luot)
            ngoai = [x for x in am["im"] if not _trong_ranh(x[0], x[1], ranh)]
            trong = [x for x in am["im"] if _trong_ranh(x[0], x[1], ranh)]
            am["im_ngoai_max"] = max([d for _a, d in ngoai] or [0.0])
            am["im_trong_max"] = max([d for _a, d in trong] or [0.0])
            am["im_dau"] = next((d for a, d in am["im"] if a <= 0.05), 0.0)
            am["im_ngoai"] = ngoai[:10]
            do["am"] = am
        else:
            do["thieu"].append("không đo được tiếng của video")
        t = time.time()
        goi = do_goi_hinh(ffmpeg, video)
        if goi:
            db = doan_dong_bang(goi)
            dai_h = goi[-1][0] - goi[0][0] or dai or 1.0
            dai = dai or dai_h
            ranh = ranh_phan(thu_muc_luot)
            den = [x for x in do_khung_den(ffmpeg, video) if not _trong_ranh(x, 0.0, ranh, du=3.5)]
            do["hinh"] = {"dong_bang": db[:20], "dong_bang_max": max([d for _a, d in db] or [0.0]),
                          "dong_bang_pct": round(100.0 * sum(d for _a, d in db) / dai_h, 2),
                          "den_ngoai_ranh": den[:20],
                          "bitrate_mbps": round(os.path.getsize(video) * 8 / dai_h / 1e6, 2)}
        else:
            do["thieu"].append("không đọc được luồng hình")
        do["giay_do"]["hinh"] = round(time.time() - t, 1)
    if clip_cu is not None:            # đo lại sau khi sửa tiếng/phụ đề/mô tả: clip không đổi, khỏi giải mã lại
        if clip_cu:
            do["clip"] = clip_cu
    elif co_ff:
        t = time.time()
        if os.path.isdir(os.path.join(thu_muc_luot, "6-clip")):
            cl = do_clip(ffmpeg, thu_muc_luot, ng["clip_giay_tinh"])
            if cl["tong"]:
                cl["tinh_pct"] = round(100.0 * len(cl["tinh"]) / cl["tong"], 1)
                do["clip"] = cl
        do["giay_do"]["clip"] = round(time.time() - t, 1)
    # phụ đề
    cues = doc_srt(_srt_giao(thu_muc_luot))
    if cues:
        do["phu_de"] = do_phu_de(cues, dai)
        mp3 = os.path.join(thu_muc_luot, "2-giong-doc.mp3")
        srt_goc = os.path.join(thu_muc_luot, "3-phu-de.srt")
        if co_ff and os.path.isfile(mp3) and os.path.isfile(srt_goc):
            t = time.time()
            on, noi, _d = khoi_am(ffmpeg, mp3)
            do["phu_de"].update(lech_phu_de(doc_srt(srt_goc), on, noi))
            do["giay_do"]["phu_de"] = round(time.time() - t, 1)
    else:
        do["thieu"].append("không đọc được phụ đề")
    # kịch bản + mở đầu
    try:
        with open(os.path.join(thu_muc_luot, "1-kich-ban.txt"), "r", encoding="utf-8") as tep:
            do["kich_ban"] = do_kich_ban(tep.read())
    except OSError:
        pass
    p8 = _doc_json(os.path.join(thu_muc_luot, "8-phan.json")) or {}
    r0 = (p8.get("ranh") or [{}])[0] if isinstance(p8, dict) else {}
    if isinstance(r0, dict) and r0.get("a_moi", r0.get("a")) is not None:
        do.setdefault("kich_ban", {})["mo_dau_giay"] = round(float(r0.get("a_moi", r0.get("a"))), 1)
    if gt is not None:
        do["meta"] = do_meta(gt.get("tieu_de", ""), gt.get("mo_ta", ""), gt.get("the", ""), dai)
    do["dai_video"] = round(dai, 2)
    do["giay_do"]["tong"] = round(time.time() - t0, 1)
    return do


# ── ĐÁNH GIÁ ─────────────────────────────────────────────────────────────────

def _loi(ma: str, muc: str, chi_tiet: str, sua: str = "") -> Dict[str, str]:
    return {"ma": ma, "muc": muc, "chi_tiet": chi_tiet, "sua": sua}


def danh_gia(do: Dict[str, Any], nguong: Optional[Dict[str, float]] = None) -> List[Dict[str, str]]:
    """Số đo → danh sách lỗi. `muc`: "chan" (không cho bàn giao) | "canh_bao". `sua`: mã cách sửa tự động
    ("" = không sửa tự động được)."""
    ng = dict(NGUONG, **(nguong or {}))
    ra: List[Dict[str, str]] = []
    am = do.get("am") or {}
    if am:
        if not (ng["lufs_duoi"] <= am["lufs"] <= ng["lufs_tren"]):
            ra.append(_loi("am_do_to", "chan", "độ to {0:.1f} LUFS ngoài khoảng {1:.1f}…{2:.1f}".format(
                am["lufs"], ng["lufs_duoi"], ng["lufs_tren"]), "chuan_hoa_am"))
        if am["tp"] > ng["tp_tran"]:
            ra.append(_loi("am_dinh", "chan", "đỉnh thật {0:.1f} dBTP > {1:.1f} (vỡ tiếng sau nén YouTube)".format(
                am["tp"], ng["tp_tran"]), "chuan_hoa_am"))
        if am.get("im_ngoai_max", 0) > ng["im_ngoai_ranh_chan"]:
            a, d = max(am.get("im_ngoai") or [[0, 0]], key=lambda x: x[1])
            ra.append(_loi("am_lang", "chan", "lặng {0:.1f} giây ở {1:.0f}s (ngoài chỗ nghỉ giữa phần)".format(d, a)))
        if am.get("im_trong_max", 0) > ng["im_trong_ranh_chan"]:
            ra.append(_loi("am_lang_ranh", "chan", "chỗ nghỉ giữa phần lặng {0:.1f} giây".format(am["im_trong_max"])))
        if am.get("im_dau", 0) > ng["im_dau_chan"]:
            ra.append(_loi("am_lang_dau", "chan", "video mở đầu bằng {0:.1f} giây im lặng".format(am["im_dau"])))
    h = do.get("hinh") or {}
    if h:
        if h["dong_bang_max"] > ng["dong_bang_chan_giay"] or h["dong_bang_pct"] > ng["dong_bang_chan_pct"]:
            ra.append(_loi("hinh_dong_bang", "chan", "khung đứng dài nhất {0:.1f}s, tổng {1:.1f}% thời lượng".format(
                h["dong_bang_max"], h["dong_bang_pct"])))
        if h.get("den_ngoai_ranh"):
            ra.append(_loi("hinh_den", "chan", "{0} khung khoá ĐEN ngoài chỗ chuyển phần (vd {1:.0f}s)".format(
                len(h["den_ngoai_ranh"]), h["den_ngoai_ranh"][0]), "lam_lai_canh"))
        if h.get("bitrate_mbps") and h["bitrate_mbps"] < ng["bitrate_canh_bao_mbps"]:
            ra.append(_loi("hinh_bitrate", "canh_bao", "bitrate {0:.1f} Mb/s thấp".format(h["bitrate_mbps"])))
    cl = do.get("clip") or {}
    if cl.get("trung"):
        ra.append(_loi("clip_trung", "chan", "clip trùng hệt nhau ở cảnh {0}".format(
            "; ".join(",".join(map(str, g)) for g in cl["trung"][:5])), "lam_lai_canh"))
    if cl.get("tinh_pct", 0) > ng["clip_tinh_pct_sua"]:
        ra.append(_loi("clip_tinh", "chan", "{0}/{1} clip ĐỨNG HÌNH liền ≥ 4 giây ({2:.1f}% > {3:.0f}%)".format(
            len(cl["tinh"]), cl["tong"], cl["tinh_pct"], ng["clip_tinh_pct_sua"]), "lam_lai_canh"))
    pd = do.get("phu_de") or {}
    if pd.get("so"):
        if pd.get("vuot_duoi") is not None and pd["vuot_duoi"] > ng["pd_tre_cuoi"]:
            ra.append(_loi("pd_vuot_duoi", "chan", "phụ đề vượt đuôi video {0:.1f}s".format(pd["vuot_duoi"]),
                           "sua_phu_de"))
        if pd.get("chong") or pd.get("rong"):
            ra.append(_loi("pd_cau_truc", "chan", "{0} câu chồng mốc, {1} câu rỗng".format(
                pd.get("chong", 0), pd.get("rong", 0)), "sua_phu_de"))
        if pd.get("khop05") is not None:
            if pd["khop05"] < ng["khop05_dat"]:
                if pd.get("khop05_tot", 0) >= ng["khop05_dat"] and abs(pd.get("doi_tot", 0)) > ng["lech_pd_sua"]:
                    ra.append(_loi("pd_lech", "chan", "phụ đề lệch đều cả bài {0:+.2f}s (khớp {1:.0%} → {2:.0%} nếu "
                                   "dời)".format(-pd["doi_tot"], pd["khop05"], pd["khop05_tot"]), "sua_phu_de"))
                else:
                    ra.append(_loi("pd_lech_khong_deu", "chan", "phụ đề không theo tiếng: chỉ {0:.0%} câu khớp khởi "
                                   "âm ±0,5s (đúng: 55–64%)".format(pd["khop05_tot"])))
            if pd.get("thieu_max", 0) > ng["pd_thieu_chan_giay"]:
                ra.append(_loi("pd_thieu", "chan", "đoạn nói {0:.1f}s ở {1:.0f}s không có phụ đề".format(
                    pd["thieu_max"], pd.get("thieu_luc") or 0)))
        if pd.get("cps95", 0) > ng["cps95_canh_bao"]:
            ra.append(_loi("pd_nhanh", "canh_bao", "phụ đề nhanh: CPS p95 {0:.1f}".format(pd["cps95"])))
        if pd.get("dong_max", 0) > ng["dong_canh_bao"]:
            ra.append(_loi("pd_dong_dai", "canh_bao", "dòng phụ đề dài {0} ký tự".format(pd["dong_max"])))
    kb = do.get("kich_ban") or {}
    if kb.get("rao"):
        ra.append(_loi("kb_rao", "canh_bao", "mở đầu có câu rào/tự giới thiệu: " + "、".join(kb["rao"])))
    if kb.get("lap_pct", 0) > ng["lap_canh_bao_pct"]:
        ra.append(_loi("kb_lap", "canh_bao", "kịch bản lặp {0:.1f}% (12-gram)".format(kb["lap_pct"])))
    if kb.get("mo_dau_giay", 0) > ng["mo_dau_canh_bao_giay"]:
        ra.append(_loi("kb_mo_dau", "canh_bao", "phần mở đầu {0:.0f}s trước chỗ nghỉ đầu tiên".format(
            kb["mo_dau_giay"])))
    mt = do.get("meta") or {}
    if mt:
        if not mt["mo_ta_ky_tu"]:
            ra.append(_loi("meta_mo_ta_rong", "chan", "mô tả RỖNG (không chương, không hashtag, mất SEO)"))
        elif mt["chuong"] and not mt["chuong_hop_le"]:
            ra.append(_loi("meta_chuong", "chan", "chương sai luật YouTube (đầu 00:00, ≥3, cách ≥10s, trong video)",
                           "sua_mo_ta"))
        elif not mt["chuong"]:
            ra.append(_loi("meta_khong_chuong", "canh_bao", "mô tả không có chương"))
        if mt["chuong"] > ng["chuong_toi_da"]:
            ra.append(_loi("meta_chuong_nhieu", "canh_bao", "{0} chương (video thắng TL4: 6–11)".format(mt["chuong"])))
        if mt["the_ky_tu"] > ng["the_toi_da_ky_tu"]:
            ra.append(_loi("meta_the", "chan", "thẻ {0} ký tự > {1}".format(mt["the_ky_tu"], ng["the_toi_da_ky_tu"]),
                           "sua_mo_ta"))
        if mt["tieu_de_ky_tu"] > ng["tieu_de_canh_bao"]:
            ra.append(_loi("meta_tieu_de_dai", "canh_bao", "tiêu đề {0} ký tự (video thắng TL4 20–52)".format(
                mt["tieu_de_ky_tu"])))
    return ra


def diem(loi: Sequence[Dict[str, str]], da_sua: Sequence[str] = ()) -> int:
    """Điểm chất lượng 0–100 (đọc nhanh, cho vòng học): chặn −30, cảnh báo −5, mỗi lần đã tự sửa −2."""
    tru = sum(30 if x["muc"] == "chan" else 5 for x in loi) + 2 * len(da_sua)
    return max(0, 100 - tru)


# ── SỬA ──────────────────────────────────────────────────────────────────────

def sua_am(ffmpeg: str, video: str, am: Dict[str, Any], ng: Dict[str, float]) -> bool:
    """Loudnorm hai lượt (số đo lượt 1 lấy từ chính lượt loudnorm print_format=json), hình chép nguyên."""
    _o, tho, ma = _chay(ffmpeg, ["-i", video, "-vn", "-af", "loudnorm=I={0}:TP={1}:LRA=11:print_format=json".format(
        ng["lufs_muc_tieu"], ng["tp_muc_tieu"]), "-f", "null", "-"], timeout=600)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", tho, re.S)
    if ma != 0 or not m:
        return False
    try:
        s = json.loads(m.group(0))
    except ValueError:
        return False
    loc = ("loudnorm=I={0}:TP={1}:LRA=11:measured_I={2}:measured_TP={3}:measured_LRA={4}:measured_thresh={5}:"
           "offset={6}:linear=true").format(ng["lufs_muc_tieu"], ng["tp_muc_tieu"], s["input_i"], s["input_tp"],
                                             s["input_lra"], s["input_thresh"], s["target_offset"])
    goc, duoi = os.path.splitext(video)
    tam = goc + ".cl" + duoi
    _o, _e, ma = _chay(ffmpeg, ["-y", "-i", video, "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", loc,
                                "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-map_metadata", "-1",
                                "-movflags", "+faststart", tam], timeout=900)
    if ma != 0 or not os.path.isfile(tam) or os.path.getsize(tam) <= 0:
        try:
            os.remove(tam)
        except OSError:
            pass
        return False
    os.replace(tam, video)
    return True


def sua_phu_de(thu_muc_luot: str, do: Dict[str, Any], ng: Dict[str, float]) -> List[str]:
    """Dời đều (nếu lệch đều), kẹp đuôi, bỏ câu rỗng, cắt chồng — trên cả `3-phu-de.srt` và `8-phu-de.srt`."""
    pd = do.get("phu_de") or {}
    dai = float(do.get("dai_video") or 0.0)
    doi = 0.0
    if pd.get("khop05") is not None and pd["khop05"] < ng["khop05_dat"] \
            and pd.get("khop05_tot", 0) >= ng["khop05_dat"] and abs(pd.get("doi_tot", 0)) > ng["lech_pd_sua"]:
        doi = float(pd["doi_tot"])
    da: List[str] = []
    for ten in ("3-phu-de.srt", "8-phu-de.srt"):
        p = os.path.join(thu_muc_luot, ten)
        cues = doc_srt(p)
        if not cues:
            continue
        moi: List[Tuple[float, float, str]] = []
        for a, b, chu in sorted(cues):
            if not _DAU.sub("", chu):
                continue
            a, b = max(0.0, a + doi), max(0.0, b + doi)
            if dai and ten == os.path.basename(_srt_giao(thu_muc_luot)):
                if a >= dai:
                    continue
                b = min(b, dai)
            if moi and a < moi[-1][1]:
                moi[-1] = (moi[-1][0], max(moi[-1][0] + 0.05, a), moi[-1][2])
            moi.append((a, max(b, a + 0.05), chu))
        if moi != list(cues):
            ghi_srt(p, moi)
            da.append(ten)
    if da:
        return ["phụ đề: {0}{1}".format(", ".join(da), " dời {0:+.2f}s".format(doi) if doi else "")]
    return []


def _canh_theo_moc(thu_muc_luot: str, moc: Sequence[float]) -> List[int]:
    """Cảnh đang chiếu ở các mốc (trục video ≈ trục phụ đề `srt_start`)."""
    canh = _doc_json(os.path.join(thu_muc_luot, "4-canh.json")) or []
    bd = []
    for c in canh if isinstance(canh, list) else []:
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", str(c.get("srt_start") or ""))
        if m:
            bd.append((_giay(*m.groups()), int(c["scene_id"])))
    bd.sort()
    ra = []
    for t in moc:
        truoc = [s for g, s in bd if g <= t + 0.05]
        if truoc and truoc[-1] not in ra:
            ra.append(truoc[-1])
    return ra


def canh_can_lam_lai(thu_muc_luot: str, do: Dict[str, Any], ng: Optional[Dict[str, float]] = None) -> List[int]:
    ng = dict(NGUONG, **(ng or {}))
    cl = do.get("clip") or {}
    ra: List[int] = []
    for g in cl.get("trung") or []:
        ra.extend(g[1:])        # giữ cảnh đầu nhóm, làm lại các bản sao
    if cl.get("tinh_pct", 0) > ng["clip_tinh_pct_sua"]:
        ra.extend(cl.get("tinh") or [])
    ra.extend(_canh_theo_moc(thu_muc_luot, (do.get("hinh") or {}).get("den_ngoai_ranh") or []))
    return sorted(set(ra))


def _canh_phai_lam_lai(thu_muc_luot: str, do: Dict[str, Any]) -> List[int]:
    """Cảnh hỏng nặng (clip trùng hệt, khung đen) — ưu tiên dùng suất làm lại trước clip tĩnh."""
    ra: List[int] = []
    for g in (do.get("clip") or {}).get("trung") or []:
        ra.extend(g[1:])
    ra.extend(_canh_theo_moc(thu_muc_luot, (do.get("hinh") or {}).get("den_ngoai_ranh") or []))
    return ra


def lam_lai_canh(thu_muc_luot: str, canh: Sequence[int]) -> None:
    """Xoá clip của đúng các cảnh + video và tệp suy ra từ nó, mở lại khâu clip + dựng."""
    from . import auto, lam_lai_clip_that  # noqa: PLC0415

    for so in canh:
        try:
            os.remove(os.path.join(thu_muc_luot, "6-clip", "{0}.mp4".format(int(so))))
        except OSError:
            pass
    for ten in lam_lai_clip_that._TEP_SUY_RA:  # noqa: SLF001 — cùng danh sách tệp suy ra từ clip
        try:
            os.remove(os.path.join(thu_muc_luot, ten))
        except OSError:
            pass
    luot = auto.doc_luot(thu_muc_luot)
    if luot is not None:
        lam_lai_clip_that.dat_lai_khau_clip(luot)


# ── CỔNG ─────────────────────────────────────────────────────────────────────

@dataclass
class KetQuaChatLuong:
    do: Dict[str, Any] = field(default_factory=dict)
    loi: List[Dict[str, str]] = field(default_factory=list)
    da_sua: List[str] = field(default_factory=list)
    lam_lai: List[int] = field(default_factory=list)
    gt: Optional[Dict[str, str]] = None
    diem: int = 100

    @property
    def chan(self) -> List[Dict[str, str]]:
        return [x for x in self.loi if x["muc"] == "chan"]

    @property
    def dat(self) -> bool:
        return not self.chan and not self.lam_lai

    def ly_do(self) -> str:
        cau = [x["chi_tiet"] for x in self.chan]
        if self.lam_lai:
            cau.append("đã mở lại khâu clip + dựng cho {0} cảnh ({1})".format(
                len(self.lam_lai), ", ".join(map(str, self.lam_lai[:12]))))
        return "; ".join(cau)


def duong_nhat_ky(goc: str) -> str:
    return os.path.join(goc, "workspace", "chat-luong", "nhat-ky.jsonl")


def doc_ket_qua(thu_muc_luot: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(thu_muc_luot, TEP_KET_QUA))
    return du if isinstance(du, dict) else {}


def doc_nhat_ky(goc: str, tu_luc: float = 0.0) -> List[Dict[str, Any]]:
    ra = []
    try:
        with open(duong_nhat_ky(goc), "r", encoding="utf-8") as tep:
            for d in tep:
                try:
                    x = json.loads(d)
                except ValueError:
                    continue
                if isinstance(x, dict) and float(x.get("ts") or 0) >= tu_luc:
                    ra.append(x)
    except OSError:
        pass
    return ra


def chi_so_ho_so(kq: Dict[str, Any]) -> Dict[str, Any]:
    """Số phẳng `cl_*` cho hồ sơ video (vòng học/bộ não đọc thẳng, không lội cây)."""
    do = kq.get("do") or {}
    am, h, cl, pd = (do.get(k) or {} for k in ("am", "hinh", "clip", "phu_de"))
    kb, mt = do.get("kich_ban") or {}, do.get("meta") or {}
    ra = {"cl_diem": kq.get("diem"), "cl_dat": kq.get("dat"), "cl_lufs": am.get("lufs"), "cl_tp": am.get("tp"),
          "cl_lang_max": am.get("im_ngoai_max"), "cl_dong_bang_pct": h.get("dong_bang_pct"),
          "cl_den": len(h.get("den_ngoai_ranh") or []) if h else None, "cl_bitrate": h.get("bitrate_mbps"),
          "cl_clip_tinh_pct": cl.get("tinh_pct"), "cl_clip_trung": len(cl.get("trung") or []) if cl else None,
          "cl_cps": pd.get("cps95"), "cl_khop_phu_de": pd.get("khop05"), "cl_lech_phu_de": pd.get("doi_tot"),
          "cl_rao": len(kb.get("rao") or []) if kb else None, "cl_lap": kb.get("lap_pct"),
          "cl_chuong": mt.get("chuong"), "cl_loi": sorted({x["ma"] for x in kq.get("loi") or []}),
          "cl_da_sua": list(kq.get("da_sua") or [])}
    return ra


def kiem_va_sua(goc: str, thu_muc_luot: str, ffmpeg: str, *, gt: Optional[Dict[str, str]] = None,
                ma_goi: str = "", kenh: str = "", nguong: Optional[Dict[str, float]] = None,
                ghi: Optional[Callable[[str], None]] = None, toi_da_vong: int = 2) -> KetQuaChatLuong:
    """Đo → sửa thứ sửa rẻ được → đo lại (tối đa `toi_da_vong` lần). Ghi `9-chat-luong.json` + nhật ký.

    NƠI GỌI PHẢI GIỮ KHE "nang" (`core/khe.py`) — `ban_giao_dang.ban_giao` chạy trong `dieu_phoi.giu_nang
    ("qa_chep")` của `tu_chay`. Không bao giờ ném lỗi đo; chỉ trả kết quả (nơi gọi quyết chặn)."""
    ng = dict(NGUONG, **(nguong or {}))
    log = ghi or (lambda _s: None)
    kq = KetQuaChatLuong(gt=dict(gt) if gt is not None else None)
    cu = doc_ket_qua(thu_muc_luot)
    da_lam_lai: Dict[str, int] = {str(k): int(v) for k, v in (cu.get("da_lam_lai") or {}).items()}
    for vong in range(max(1, toi_da_vong)):
        try:
            kq.do = do_luot(thu_muc_luot, ffmpeg, gt=kq.gt, nguong=ng,
                            clip_cu=(kq.do.get("clip") or {}) if vong else None)
        except Exception as loi:  # noqa: BLE001 — đo hỏng không được làm sập bàn giao
            kq.do = {"thieu": ["đo hỏng: {0}".format(str(loi)[:200])]}
        kq.loi = danh_gia(kq.do, ng)
        sua = {x["sua"] for x in kq.loi if x["sua"] and x["muc"] == "chan"}
        if not sua:
            break
        # Làm lại cảnh TRƯỚC: video sẽ bị xoá để dựng lại, sửa tiếng/phụ đề lúc này là phí.
        if "lam_lai_canh" in sua:
            canh = [c for c in canh_can_lam_lai(thu_muc_luot, kq.do, ng)
                    if da_lam_lai.get(str(c), 0) < 1]                     # mỗi cảnh tối đa MỘT lần
            # 09/10/2026: vượt trần thì làm lại PHẦN còn suất (trùng/đen trước, rồi clip tĩnh) chứ không bỏ cả lượt
            # — TL2-T7-0022 có 31 clip tĩnh > trần 30 → không làm lại cảnh nào, chặn thẳng "cần người xem".
            con_suat = int(ng["toi_da_lam_lai_canh"]) - sum(da_lam_lai.values())
            if canh and con_suat > 0:
                phai = set(_canh_phai_lam_lai(thu_muc_luot, kq.do))
                canh = sorted(sorted(canh, key=lambda c: (c not in phai, c))[:con_suat])
                lam_lai_canh(thu_muc_luot, canh)
                for c in canh:
                    da_lam_lai[str(c)] = da_lam_lai.get(str(c), 0) + 1
                kq.lam_lai = canh
                kq.loi = [x for x in kq.loi if x["sua"] != "lam_lai_canh"]
                log("  [CHẤT LƯỢNG] mở lại khâu clip cho {0} cảnh: {1}".format(len(canh), canh))
                break           # video đã bị xoá — đo lại ở lượt bàn giao sau
            for x in kq.loi:
                if x["sua"] == "lam_lai_canh":
                    x["sua"] = ""
                    x["chi_tiet"] += (" — các cảnh này đã được làm lại một lần (hoặc hết trần {0} cảnh/lượt): "
                                      "cần người xem".format(int(ng["toi_da_lam_lai_canh"])))
        if vong == toi_da_vong - 1:
            break
        lam = False
        video = os.path.join(thu_muc_luot, "8-video.mp4")
        if "chuan_hoa_am" in sua and kq.do.get("am") and sua_am(ffmpeg, video, kq.do["am"], ng):
            kq.da_sua.append("chuẩn hoá tiếng {0:.1f} LUFS/{1:.1f} dBTP → {2:.0f} LUFS".format(
                kq.do["am"]["lufs"], kq.do["am"]["tp"], ng["lufs_muc_tieu"]))
            lam = True
        if "sua_phu_de" in sua:
            ds = sua_phu_de(thu_muc_luot, kq.do, ng)
            kq.da_sua.extend(ds)
            lam = lam or bool(ds)
        if "sua_mo_ta" in sua and kq.gt is not None:
            mt, the, ds = sua_mo_ta(kq.gt.get("mo_ta", ""), kq.gt.get("the", ""), float(kq.do.get("dai_video") or 0),
                                    int(ng["the_toi_da_ky_tu"]))
            if ds:
                kq.gt.update(mo_ta=mt, the=the)
                kq.da_sua.extend("mô tả: " + x for x in ds)
                lam = True
        if not lam:
            break
    kq.diem = diem(kq.loi, kq.da_sua)
    du = {"luc": _dt.datetime.now().replace(microsecond=0).isoformat(), "ma_goi": ma_goi, "kenh": kenh,
          "dat": kq.dat, "diem": kq.diem, "loi": kq.loi, "da_sua": kq.da_sua, "lam_lai": kq.lam_lai,
          "da_lam_lai": da_lam_lai, "so_lan_chan": int(cu.get("so_lan_chan") or 0) + (0 if kq.dat else 1),
          "do": kq.do}
    try:
        _ghi_json(os.path.join(thu_muc_luot, TEP_KET_QUA), du)
    except OSError:
        pass
    try:
        p = duong_nhat_ky(goc)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as tep:
            tep.write(json.dumps({"ts": time.time(), "kenh": kenh, "ma_goi": ma_goi, "dat": kq.dat,
                                  "diem": kq.diem, "loi": sorted({x["ma"] for x in kq.loi if x["muc"] == "chan"}),
                                  "canh_bao": sorted({x["ma"] for x in kq.loi if x["muc"] != "chan"}),
                                  "da_sua": len(kq.da_sua), "lam_lai": len(kq.lam_lai),
                                  "giay": (kq.do.get("giay_do") or {}).get("tong")}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    log("  [CHẤT LƯỢNG] {0}: điểm {1}{2}{3}".format(
        ma_goi or os.path.basename(thu_muc_luot), kq.diem, " — đã sửa: " + "; ".join(kq.da_sua) if kq.da_sua else "",
        "" if kq.dat else " — CHẶN: " + kq.ly_do()))
    return kq
