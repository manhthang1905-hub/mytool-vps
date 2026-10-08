"""Chốt MỤC LỤC (chương YouTube) từ các PHẦN kịch bản — một hàm chung cho mọi đường.

═══ VÌ SAO (kiểm toán chất lượng 09/10/2026, `workspace/chan-doan/chat-luong-2026-10-09.md`) ═══

Trước đây mỗi dấu `---` của kịch bản là một chương, nhãn = câu thoại mở phần nguyên văn. Đo thật: có lượt
35 chương, có lượt 21 chương kèm chương tự giới thiệu 「…へようこそ」 và chương quảng bá kênh; video thắng
TL4 có 6–11 chương (trung vị 7), tên chương là Ý NỘI DUNG ngắn.

Luật ở đây:
* tối đa `toi_da` chương (mặc định 10, `kenh.yaml: chuong_toi_da`); nhiều phần hơn thì GỘP phần kề nhau
  (AI chọn theo nghĩa; đường lui gộp theo độ dài, ưu tiên phần mở bằng từ nối) — không cắt cụt;
* luật YouTube: ≥ 3 chương, chương đầu 00:00, mỗi chương ≥ 10 giây, chương cuối cách đuôi ≥ 10 giây;
* nhãn ngắn (CJK ~8–22 ký tự), nói ý của chương, không chào/tự giới thiệu/quảng bá kênh/xin đăng ký,
  không trùng nhau;
* AI (một lượt gọi nhỏ) đặt nhãn + chọn chỗ gộp; kết quả CẤT ở `3-muc-luc.json` trong thư mục lượt,
  khoá theo "chữ ký" các phần — đường SRT, đường `2-phan.json` và lượt đặt lại sau khi dựng video cùng ra
  ĐÚNG một bộ chương (chỉ mốc giây theo trục của từng đường), và không trả tiền hai lần;
* AI hỏng (mạng, JSON sai…) → nhãn dự phòng TẤT ĐỊNH: rút gọn câu mở phần, bỏ mệnh đề chào/quảng bá,
  vẫn đúng độ dài và không trùng.

Thuần: không Qt, không mạng — lời gọi AI do nơi gọi truyền vào (`goi_ai(loi_nhac, khoa_phu) -> str`).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["TEP_CACHE", "TOI_DA_CHUONG", "MO_HINH_NHAN", "chot_chuong", "nhan_hop_le", "nhan_du_phong",
           "gop_theo_do_dai", "gioi_han_nhan", "de_bai_nhan"]

#: Tệp cất kết quả trong thư mục lượt.
TEP_CACHE = "3-muc-luc.json"
#: Trần số chương (kênh đổi được bằng `chuong_toi_da`). Video thắng TL4: 6–11, trung vị 7.
TOI_DA_CHUONG = 10
#: Sàn số chương khi PHẢI gộp (nhiều phần hơn trần).
SAN_CHUONG_GOP = 6
#: Mô hình cho việc chữ ngắn này — bậc giữa, như các việc nhỏ khác (`ban_giao_dang` chọn danh sách phát).
MO_HINH_NHAN = "claude-sonnet-5"
#: Khi phải gộp: nhắm ~2,5 phút/chương (video 16 phút → 6, 20 phút → 8; TL4 thắng trung vị 7).
GIAY_MOI_CHUONG = 150.0
#: Mỗi chương ít nhất ngần này giây (luật YouTube).
GIAY_TOI_THIEU = 10.0

#: Mảnh không được có trong tên chương (so chữ thường). Chung mọi tiếng — tool phát hành cho ngách khác.
CAM_NHAN = (
    # ja
    "ようこそ", "こんにちは", "こんばんは", "おはよう", "はじめまして", "チャンネル", "登録", "高評価", "グッドボタン",
    "ご視聴", "ご覧いただ", "最後までご覧", "最後まで見", "本題に入る前に", "それでは早速", "この動画では", "この動画の",
    "今回の動画", "コメント", "これからも", "お届けしま", "通知",
    # en
    "welcome", "subscribe", "hello", "hi everyone", "this channel", "this video", "comment", "like and", "smash",
    # vi
    "chào mừng", "xin chào", "đăng ký", "kênh", "bình luận", "video này",
    # ko / zh
    "안녕하세요", "구독", "좋아요", "채널", "댓글", "欢迎", "订阅", "点赞", "频道",
)
#: Từ nối/đệm ở ĐẦU nhãn dự phòng — bỏ đi cho nhãn vào thẳng ý.
_DEM_DAU = ("それでは", "では", "さて", "まず", "次に", "そして", "ここで", "ところで", "実は", "でも", "しかし",
            "つまり", "ただ", "また", "so ", "now ", "well ", "okay ", "và ", "vậy ", "giờ ")
#: Phần mở bằng các từ này thường là "nối tiếp ý trước" → đường lui gộp ưu tiên dán nó vào phần trước.
_TU_NOI = ("つまり", "しかし", "でも", "実は", "実際", "ここで", "さて", "特に", "そして", "また", "ただ", "例えば",
           "なぜ", "今日の実践", "では", "それでは", "because", "but ", "so ", "for example", "nhưng", "vì vậy",
           "ví dụ")
#: Chỉ bỏ đuôi HỆ TỪ (không đổi nghĩa); không đụng ます/ません — bỏ đi là ra chữ cụt hoặc đảo nghĩa.
_DUOI_CAU = ("なのです", "のです", "です")
_RE_CAU = re.compile(r"[^。！？!?\n]+[。！？!?]?")
_RE_DAU_CUOI = re.compile(r"[\s。．.、,，！!？?…・\-—–「」『』\"']+$")
_RE_DAU_DAU = re.compile(r"^[\s。．.、,，！!？?…・\-—–_*」』\"']+")


def _cjk(ngon_ngu: str) -> bool:
    ma = str(ngon_ngu or "ja").strip().lower()[:2]
    return ma in ("ja", "zh", "ko", "")


def gioi_han_nhan(ngon_ngu: str) -> Tuple[int, int, str]:
    """`(sàn, trần, câu cho lời nhắc)` độ dài nhãn theo tiếng."""
    if _cjk(ngon_ngu):
        return 3, 22, "8–22 ký tự"
    return 8, 50, "15–45 ký tự"


def _chuan(chu: str) -> str:
    return re.sub(r"[\s、。，,．.！!？?…・「」『』\"'()（）【】\-—–]+", "", str(chu or "")).lower()


def _co_cam(chu: str, cam_them: Sequence[str] = ()) -> bool:
    thap = str(chu or "").lower()
    return any(x and x.lower() in thap for x in tuple(CAM_NHAN) + tuple(cam_them))


def nhan_hop_le(chu: str, ngon_ngu: str, da_dung: Sequence[str] = (), cam_them: Sequence[str] = ()) -> bool:
    """Nhãn dùng được: đủ độ dài, không chào/quảng bá, không có mốc giờ, không trùng nhãn đã dùng."""
    chu = str(chu or "").strip()
    san, tran, _c = gioi_han_nhan(ngon_ngu)
    if not (san <= len(chu) <= tran) or "\n" in chu or "---" in chu:
        return False
    if re.match(r"^\d{1,2}:\d{2}", chu) or _co_cam(chu, cam_them):
        return False
    k = _chuan(chu)
    return bool(k) and all(k != _chuan(x) for x in da_dung)


def _bo_dem(chu: str) -> str:
    chu = _RE_DAU_DAU.sub("", chu)
    doi = True
    while doi:
        doi = False
        for w in _DEM_DAU:
            if chu.lower().startswith(w) and len(chu) > len(w) + 2:
                chu = _RE_DAU_DAU.sub("", chu[len(w):])
                doi = True
    return chu


def _rut_gon(chu: str, ngon_ngu: str, cam_them: Sequence[str]) -> Tuple[str, bool]:
    """Một câu → `(nhãn ngắn, có phải cắt ngang chữ không)`: bỏ mệnh đề chào/quảng bá, bỏ từ đệm đầu, bỏ
    đuôi hệ từ です, cắt ở dấu phẩy; chỉ cắt ngang chữ khi không còn cách nào."""
    san, tran, _c = gioi_han_nhan(ngon_ngu)
    chu = re.sub(r"\s+", " " if not _cjk(ngon_ngu) else "", str(chu or "")).strip()
    menh = [m for m in re.split(r"(?<=[、,，])", chu) if m.strip()]
    menh = [m for m in menh if not _co_cam(m, cam_them)]
    chu = _bo_dem("".join(menh).strip())
    chu = _RE_DAU_CUOI.sub("", chu)
    if len(chu) > tran:
        for duoi in _DUOI_CAU:
            if chu.endswith(duoi) and len(chu) - len(duoi) >= san:
                chu = chu[:-len(duoi)]
                break
    cat_ngang = False
    if len(chu) > tran:
        cat = max(chu.rfind(d, 0, tran + 1) for d in ("、", ",", "，", "—", "：", ":"))
        if cat >= max(san, 8):
            chu = chu[:cat]
        elif not _cjk(ngon_ngu) and chu.rfind(" ", 0, tran + 1) >= san:
            chu = chu[:chu.rfind(" ", 0, tran + 1)]
        else:
            chu, cat_ngang = chu[:tran], True
    return _RE_DAU_CUOI.sub("", chu).strip(), cat_ngang


def nhan_du_phong(nhan_tho: str, chu_nhom: str, ngon_ngu: str, da_dung: Sequence[str], so: int,
                  cam_them: Sequence[str] = ()) -> str:
    """Nhãn TẤT ĐỊNH khi không có AI: câu mở phần, rồi lần lượt các câu trong chương — câu đầu tiên rút gọn
    được mà KHÔNG phải cắt ngang chữ thắng; không có thì câu đầu hợp lệ (cắt ngang); hết cách thì nhãn chung
    "第N章"/"Part N" (vẫn hợp lệ, không trùng)."""
    ung = [nhan_tho] + [m.group(0) for m in _RE_CAU.finditer(str(chu_nhom or ""))][:12]
    du_phong = ""
    for c in ung:
        n, cat_ngang = _rut_gon(c, ngon_ngu, cam_them)
        if nhan_hop_le(n, ngon_ngu, da_dung, cam_them):
            if not cat_ngang:
                return n
            du_phong = du_phong or n
    if du_phong:
        return du_phong
    mau = "第{0}章" if str(ngon_ngu or "ja").lower().startswith("ja") else "Part {0}"
    goc = mau.format(so)
    n, i = goc, 2
    while any(_chuan(n) == _chuan(x) for x in da_dung):
        n, i = "{0} ({1})".format(goc, i), i + 1
    return n


# ── Gộp phần ────────────────────────────────────────────────────────────────


def _toan_rac(chu: str, cam_them: Sequence[str] = ()) -> bool:
    """Phần chỉ toàn câu chào / quảng bá kênh / xin đăng ký (không có câu nội dung nào)."""
    cau = [m.group(0) for m in _RE_CAU.finditer(str(chu or "")) if m.group(0).strip()]
    return bool(cau) and all(_co_cam(c, cam_them) for c in cau)


def _dai(t: Sequence[float], tong: float, i: int, j: int) -> float:
    """Độ dài khối phần [i, j)."""
    het = t[j] if j < len(t) else max(tong, t[-1])
    return max(0.0, het - t[i])


def gop_theo_do_dai(t: Sequence[float], tong: float, mo_dau: Sequence[str] = (),
                    toi_da: int = TOI_DA_CHUONG, rac: Sequence[bool] = ()) -> List[int]:
    """Đường lui (không AI): chỉ số phần MỞ mỗi chương. Phần < 10 s dán vào phần trước; phần cuối cách đuôi
    < 10 s dán vào phần trước; còn quá `toi_da` thì gộp dần CẶP KỀ ngắn nhất (phần mở bằng từ nối được tính
    "ngắn" hơn — nó vốn nối tiếp ý trước) tới số chương mục tiêu ~2,5 phút/chương, kẹp [6, toi_da].
    `rac[i]` = phần i CHỈ có chào/quảng bá/xin đăng ký → không mở chương riêng, dán vào phần trước."""
    n = len(t)
    if n == 0:
        return []
    dau = [0]
    for i in range(1, n):
        if i < len(rac) and rac[i]:
            continue
        if t[i] - t[dau[-1]] >= GIAY_TOI_THIEU:
            dau.append(i)
    while len(dau) > 1 and tong > 0 and tong - t[dau[-1]] < GIAY_TOI_THIEU:
        dau.pop()
    if len(dau) <= toi_da:
        return dau
    muc_tieu = int(round(tong / GIAY_MOI_CHUONG)) if tong > 0 else 8
    muc_tieu = max(min(SAN_CHUONG_GOP, toi_da), min(toi_da, muc_tieu))
    while len(dau) > muc_tieu:
        tot, chon = None, 1
        for k in range(1, len(dau)):
            het = dau[k + 1] if k + 1 < len(dau) else n
            gia = _dai(t, tong, dau[k - 1], het)
            mo = str(mo_dau[dau[k]] if dau[k] < len(mo_dau) else "").lstrip("-—– ").lower()
            if any(mo.startswith(w) for w in _TU_NOI):
                gia *= 0.6
            if tot is None or gia < tot:
                tot, chon = gia, k
        del dau[chon]
    return dau


# ── AI ──────────────────────────────────────────────────────────────────────


def _ten_tieng(ngon_ngu: str) -> str:
    try:
        from .kenh import ten_tieng  # noqa: PLC0415

        return ten_tieng(ngon_ngu) or ngon_ngu or "tiếng của kênh"
    except Exception:  # noqa: BLE001
        return ngon_ngu or "tiếng của kênh"


def _moc(giay: float) -> str:
    phut, s = divmod(int(giay), 60)
    gio, phut = divmod(phut, 60)
    return "{0}:{1:02d}:{2:02d}".format(gio, phut, s) if gio else "{0:02d}:{1:02d}".format(phut, s)


def de_bai_nhan(phan: Sequence[Tuple[float, str, str]], tong: float, ngon_ngu: str, toi_da: int,
                cam_them: Sequence[str] = ()) -> str:
    """Lời nhắc: đặt tên chương (và chọn chỗ gộp khi nhiều phần hơn `toi_da`). Trả JSON."""
    n = len(phan)
    t = [p[0] for p in phan]
    _s, _t, cau_dai = gioi_han_nhan(ngon_ngu)
    gop = n > toi_da
    dong = []
    for i, (giay, _nh, chu) in enumerate(phan):
        doan = re.sub(r"\s+", " ", str(chu or "")).strip()[:170]
        dong.append("P{0} [{1}, dài {2:.0f}s] {3}".format(i + 1, _moc(giay), _dai(t, tong, i, i + 1), doan))
    viec = ("Video có {0} PHẦN — quá nhiều cho mục lục. GỘP các phần KỀ NHAU cùng một ý thành {1}–{2} chương "
            "(gộp theo nghĩa: một luận điểm/một bước là một chương; phần mở đầu thường gộp với phần ngay sau nếu "
            "nó ngắn), rồi đặt tên từng chương.".format(n, min(SAN_CHUONG_GOP, toi_da), toi_da)
            if gop else
            "Video có {0} PHẦN, mỗi phần là MỘT chương (giữ nguyên, không gộp). Đặt tên từng chương.".format(n))
    cam = ""
    if cam_them:
        cam = " Không nhắc tên kênh ({0}).".format(", ".join(str(x) for x in cam_them if x))
    return (
        "Bạn đặt MỤC LỤC (chương YouTube) cho một video nói {tieng}.\n{viec}\n\n"
        "LUẬT TÊN CHƯƠNG:\n"
        "1. Viết bằng {tieng}, {dai}, là Ý NỘI DUNG của chương — người lướt mục lục đọc là biết chương nói gì "
        "(một danh từ/cụm ý, không chép nguyên câu thoại, không dấu chấm cuối).\n"
        "2. KHÔNG chào hỏi, KHÔNG tự giới thiệu, KHÔNG quảng bá kênh, KHÔNG xin đăng ký/like/bình luận, KHÔNG "
        "câu dẫn kiểu 'trước khi vào chủ đề'.{cam} Chương 1 đặt theo vấn đề/câu hỏi video mở ra; chương cuối "
        "theo ý kết.\n"
        "3. Không hai tên trùng nhau; không mốc giờ trong tên; không đánh số máy móc kiểu '第1章'.\n\n"
        "Trả về DUY NHẤT một JSON, không giải thích:\n"
        "{{\"chuong\": [{{\"phan\": 1, \"nhan\": \"...\"}}, {{\"phan\": 4, \"nhan\": \"...\"}}]}}\n"
        "`phan` = số phần MỞ chương đó (P1 luôn là chương đầu; tăng dần{gop}).\n\n"
        "CÁC PHẦN (mốc, độ dài, đoạn đầu lời đọc):\n{dong}"
    ).format(tieng=_ten_tieng(ngon_ngu), viec=viec, dai=cau_dai, cam=cam,
             gop="" if gop else "; liệt kê ĐỦ mọi phần P1…P{0}".format(n), dong="\n".join(dong))


def _doc_json(chu: str) -> Any:
    chu = str(chu or "")
    m = re.search(r"\{.*\}", chu, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def _doc_tra_loi(tra: str, n: int, toi_da: int) -> Optional[List[Tuple[int, str]]]:
    """`[(chỉ số phần 0-based, nhãn)]` hoặc None nếu cấu trúc sai."""
    du = _doc_json(tra)
    ds = du.get("chuong") if isinstance(du, dict) else None
    if not isinstance(ds, list) or not ds:
        return None
    ra: List[Tuple[int, str]] = []
    for x in ds:
        if not isinstance(x, dict):
            return None
        try:
            i = int(x.get("phan")) - 1
        except (TypeError, ValueError):
            return None
        if not (0 <= i < n) or (ra and i <= ra[-1][0]):
            return None
        ra.append((i, str(x.get("nhan") or "").strip()))
    if ra[0][0] != 0:
        ra[0] = (0, ra[0][1])
    if len(ra) > toi_da or len(ra) < min(3, n):
        return None
    if n <= toi_da and len(ra) != n:
        return None
    return ra


# ── Cất ─────────────────────────────────────────────────────────────────────


def _chu_ky(phan: Sequence[Tuple[float, str, str]], ngon_ngu: str, toi_da: int) -> str:
    """Chữ ký bộ phần — KHÔNG gồm mốc giây (trục giọng/trục video lệch nhau vài giây nhưng là cùng bộ)."""
    tho = "|".join(_chuan(p[2])[:30] for p in phan)
    return hashlib.sha1("{0}|{1}|{2}".format(ngon_ngu, toi_da, tho).encode("utf-8")).hexdigest()[:16]


def _doc_cache(thu_muc: str) -> Dict[str, Any]:
    if not thu_muc:
        return {}
    try:
        with open(os.path.join(thu_muc, TEP_CACHE), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_cache(thu_muc: str, khoa: str, ban: Dict[str, Any]) -> None:
    if not thu_muc or not os.path.isdir(thu_muc):
        return
    du = _doc_cache(thu_muc)
    du[khoa] = ban
    if len(du) > 8:  # chỉ giữ vài bản gần nhất
        for k in list(du)[:-8]:
            du.pop(k, None)
    tam = os.path.join(thu_muc, TEP_CACHE + ".tmp")
    try:
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(tam, os.path.join(thu_muc, TEP_CACHE))
    except OSError:
        pass


# ── Hàm chung ───────────────────────────────────────────────────────────────


def chot_chuong(phan: Sequence[Tuple[float, str, str]], tong: float, *,
                goi_ai: Optional[Callable[[str, str], str]] = None, thu_muc: str = "", ngon_ngu: str = "ja",
                cam_them: Sequence[str] = (), toi_da: int = TOI_DA_CHUONG,
                ghi: Optional[Callable[[str], None]] = None) -> List[str]:
    """Các PHẦN `(giây mở, nhãn thô, lời của phần)` → dòng mục lục `MM:SS tên`. `[]` khi không đủ 3 chương.

    `goi_ai(lời nhắc, khoá phụ) -> chữ` (nơi gọi lo thử lại/khoá idempotency); None/hỏng → nhãn dự phòng.
    `thu_muc` (thư mục lượt) → cất/đọc `3-muc-luc.json`.
    """
    ghi = ghi or (lambda _s: None)
    toi_da = max(3, int(toi_da or TOI_DA_CHUONG))
    phan = sorted([(float(a), str(b or ""), str(c or "")) for a, b, c in phan], key=lambda x: x[0])
    if len(phan) < 3 or phan[0][0] != 0.0:
        return []
    n = len(phan)
    t = [p[0] for p in phan]
    tong = float(tong or 0.0) or t[-1] + GIAY_TOI_THIEU
    khoa = _chu_ky(phan, ngon_ngu, toi_da)
    cu = _doc_cache(thu_muc).get(khoa)
    chon: Optional[List[Tuple[int, str]]] = None
    nguon = ""
    if isinstance(cu, dict) and (cu.get("nguon") == "ai" or goi_ai is None):
        try:
            chon = [(int(i), str(nh)) for i, nh in zip(cu["dau"], cu["nhan"])]
            nguon = str(cu.get("nguon") or "")
        except (KeyError, TypeError, ValueError):
            chon = None
    if chon is None and goi_ai is not None:
        loi_nhac = de_bai_nhan(phan, tong, ngon_ngu, toi_da, cam_them)
        for lan in range(2):
            try:
                tra = goi_ai(loi_nhac + ("" if lan == 0 else "\n\n(Lần trước JSON sai luật — làm lại đúng luật.)"),
                             hashlib.sha1(loi_nhac.encode("utf-8")).hexdigest()[:12] + ("" if lan == 0 else "r1"))
            except Exception as loi:  # noqa: BLE001 — API hỏng (đã thử lại ở nơi gọi) → dự phòng
                ghi("  (đặt tên chương bằng AI không xong: {0} — dùng nhãn dự phòng)".format(str(loi)[:80]))
                break
            chon = _doc_tra_loi(tra, n, toi_da)
            if chon is not None:
                nguon = "ai"
                break
        if chon is None and nguon != "ai":
            ghi("  (AI không trả mục lục dùng được — dùng nhãn dự phòng)")
    if chon is None:
        rac = [_toan_rac(p[2], cam_them) for p in phan]
        if len(phan) - sum(rac[1:]) < 3:
            rac = []
        chon = [(i, "") for i in gop_theo_do_dai(t, tong, [p[1] for p in phan], toi_da, rac)]
        nguon = "du_phong"

    # Nhãn: AI hợp lệ thì giữ, hỏng từng cái thì dự phòng; luôn không trùng.
    dau = [i for i, _nh in chon]
    nhan: List[str] = []
    for k, (i, nh) in enumerate(chon):
        het = dau[k + 1] if k + 1 < len(dau) else n
        if not nhan_hop_le(nh, ngon_ngu, nhan, cam_them):
            nh = nhan_du_phong(phan[i][1], " ".join(p[2] for p in phan[i:het]), ngon_ngu, nhan, k + 1, cam_them)
        nhan.append(nh)
    if not isinstance(cu, dict) or cu.get("dau") != dau or cu.get("nhan") != nhan:
        _ghi_cache(thu_muc, khoa, {"dau": dau, "nhan": nhan, "nguon": nguon, "so_phan": n})

    # Luật YouTube trên mốc CỦA ĐƯỜNG NÀY (trục giọng / trục video).
    muc: List[Tuple[float, str]] = []
    for i, nh in zip(dau, nhan):
        if muc and t[i] - muc[-1][0] < GIAY_TOI_THIEU:
            continue
        muc.append((t[i], nh))
    while len(muc) > 1 and tong - muc[-1][0] < GIAY_TOI_THIEU:
        muc.pop()
    if len(muc) < 3 or muc[0][0] != 0.0:
        return []
    return ["{0} {1}".format(_moc(g), nh) for g, nh in muc]
