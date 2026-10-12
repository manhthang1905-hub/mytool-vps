"""Viết chữ bằng Claude Code trên **gói thuê bao của chính chủ máy** (Claude Max).

═══ VÌ SAO CÓ ĐƯỜNG NÀY ═══

Chủ dự án, 24/08/2026: *"với pc này của tao tao có claude max x20 và tao muốn
là khi viết content sẽ dùng nó… nhưng khi tạo các prompt ảnh video thì nó có
thể dùng key của shopapi"*.

Chủ dự án, 12/10/2026: *"phần viết đang dùng api của shopapi — tuy nhiên việc
content rất quan trọng nên sẽ dùng claude 20x trên máy này — dùng mode claude
opus 5.5 — và áp dụng cho các kênh khác — tức llm dùng claude 20x chính hãng"*.

Nên từ 12/10/2026 đường này không còn là "riêng khâu kịch bản": MỌI lượt viết
chữ của tool (`core.goi_van_ban.goi_van_ban` — chỗ duy nhất tool nhờ AI viết)
tự rẽ sang đây khi `duong_viet_chu` nói "max": kịch bản và mọi vòng của nó,
tiêu đề/SEO/mô tả/bình luận ghim, chữ bìa và đọc soát bìa (kèm ảnh), tên
chương, chọn/biên tập content, phòng thí nghiệm, giám đốc kênh. Riêng lời nhắc
ẢNH/CLIP (bảng cảnh, đạo diễn, viết lại lời nhắc bị từ chối) và cửa chấm ảnh
của nhà máy vẫn đi ví ShopAPI — nơi gọi bọc `goi_van_ban.qua_vi()` hoặc truyền
`qua_vi=True`. Ảnh, clip, giọng đọc thì vẫn là việc của nhà máy như cũ.

═══ MÁY NÀO ĐI ĐƯỜNG NÀY ═══

`workspace/cai-dat.json: viet_chu_bang` — mặc định `"tu_dong"`: máy có CLI
Claude Code (PATH hoặc extension VS Code, `claude_code.tim_claude`) VÀ có phiên
đăng nhập thuê bao (`claude_code.co_phien_dang_nhap`) thì viết bằng thuê bao;
máy khách chỉ có khoá ShopAPI thì vẫn đi ví như trước, không đổi gì.
`"claude_max"` ép đi thuê bao, `"vi"` ép đi ví. Khoá cũ
`kich_ban_bang_claude_code: true` vẫn được hiểu là `"claude_max"`.

═══ VÌ SAO KHOÁ SHOPAPI KHÔNG ĐƯỢC BÉN MẢNG VÀO ĐÂY ═══

Cùng ngày, cùng người: *"tao không muốn máy này claude code bị đi vào key đó"*.

Claude Code chỉ cần thấy `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` trong môi
trường là nó **dùng khoá thay vì phiên đăng nhập** — tiền lặng lẽ chạy sang ví
ShopAPI dù máy có gói Max. Nên tiến trình ở đây chạy bằng `moi_truong_max()`:
môi trường đã gỡ sạch mọi biến khoá mà Studio biết.

═══ VÌ SAO CHẠY TRONG MỘT THƯ MỤC RỖNG, VỚI LỜI NHẮC HỆ THỐNG RIÊNG ═══

Claude Code là agent: thả nó vào thư mục tool là nó ĐỌC được cả thư mục tool.
Việc ở đây chỉ là "viết một bài văn" — cho nó một thư mục rỗng
(`workspace/viet-max/<mã lượt>/`), không công cụ (trừ `Read` khi có ảnh), không
máy chủ MCP, không skill, không lưu phiên, và THAY hẳn lời nhắc hệ thống của
agent bằng `CHI_DAO_VIET`. Đo 12/10/2026 trên máy này: một lượt "OK" với lời
nhắc hệ thống mặc định của Claude Code tốn **37.104** token đầu vào; bản gọn
tốn **2.013**. Trên gói thuê bao, đó là hạn mức của cả máy — gấp 18 lần cho
không gì cả.

═══ HỎNG THÌ XỬ THẾ NÀO ═══

  hết hạn mức model     → tụt ngay xuống bậc model dưới, KHÔNG đợi
  model không dùng được → cũng tụt bậc, và khoá tên ấy một ngày
  nghẽn tạm / lỗi lẻ    → giữ nguyên model, đợi theo `NHIP_THU_LAI` rồi thử lại
  cạn CẢ thang          → đợi tới giờ mở lại gần nhất (tối đa
                          `GIAY_CHO_CAN_THANG_TOI_DA`), báo người qua gác tổng
                          ("Việc của bạn") + `core.bao_dong`, rồi TỰ chạy tiếp

Hết kiên nhẫn thì **ném lỗi nói rõ**, KHÔNG lặng lẽ rẽ sang ví ShopAPI — xem
`dung_goi_chat_max`: rẽ sang ví là trả tiền lần hai cho thứ đã trả tiền tháng.

═══ CÙNG LÚC BAO NHIÊU TIẾN TRÌNH ═══

Nhiều kênh, giám đốc, bộ não chạy song song, mỗi lượt viết là một tiến trình
`claude` (~vài trăm MB RAM, và cùng ăn một hạn mức thuê bao). `giu_suat` giữ
một trong `so_song_song(goc)` suất (mặc định 3, `cai-dat.json:
claude_max_song_song`) bằng tệp `O_EXCL` trong `workspace/viet-max/suat/` —
chung cho MỌI tiến trình Python trên máy; suất của tiến trình đã chết tự được
dọn. Mỗi lượt ghi một dòng vào `workspace/viet-max/so-dung.jsonl` (model, giây,
token) — `python -m core.viet_max --so-dung` để xem tải thuê bao.
"""

from __future__ import annotations

import base64
import contextlib
import datetime as _dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple, Union

__all__ = ["co_claude_code", "viet_bang_max", "dung_goi_chat_max",
           "THU_MUC_RONG", "THANG_MO_HINH", "la_het_han_muc",
           "mo_hinh_dang_dung", "doc_han_muc", "ghi_han_muc", "gio_mo_lai",
           "ly_do_tut_bac", "thang_mo_hinh", "duong_viet_chu", "xoa_nho_duong",
           "goi_tin_nhan_max", "phang_tin_nhan", "giu_suat", "HetGioChoSuat",
           "ghi_so_dung", "tom_tat_so_dung", "doc_trang_thai", "so_song_song",
           "muc_suy_nghi", "MO_HINH_DAU_CHON_DUOC", "MUC_SUY_NGHI"]

#: Gốc tool (thư mục chứa `core/`) — dùng khi nơi gọi không truyền `goc`.
GOC_TOOL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Thư mục làm việc RỖNG cho tiến trình Claude Code, tính từ gốc tool.
THU_MUC_RONG = os.path.join("workspace", "viet-max")

#: Viết một kịch bản dài mất vài phút; 900 giây là sàn. Lượt xin nhiều chữ hơn
#: được đợi lâu hơn — xem `gio_han_theo_token`.
GIAY_CHO_MAC_DINH = 900.0

#: Model đứng đầu thang — chủ dự án chọn, 12/10/2026: *"dùng mode claude opus
#: 5.5"*. Đổi được ở Cài đặt (`cai-dat.json: claude_max_mo_hinh`).
#:
#: Gói thuê bao tính tiền theo THÁNG, không theo token, nên `mo_hinh` mà nơi gọi
#: truyền vào (model của ĐƯỜNG VÍ, chọn rẻ cho việc vặt) không với tới đây.
MO_HINH_TOT_NHAT = "claude-opus-5-5"

#: ═══ BẬC THANG MODEL: HẾT HẠN MỨC THÌ TỤT XUỐNG, KHÔNG ĐỨNG ĐÓ ĐỢI ═══
#:
#: Chủ dự án, 26/08/2026: *"model fable đang hết token… muốn nó có logic tự
#: đổi model cao xuống thấp để không bị lỗi nữa"*.
#:
#: Hạn mức thuê bao Claude mở lại theo cửa sổ **hàng giờ**, nên thử lại trên
#: cùng model đã cạn là phí; model bên dưới đang rảnh. Đã thử từng tên bằng một
#: lượt 1 token qua CLI trên máy này 12/10/2026 (cả bốn đều chạy).
#:
#: Không có Haiku ở cuối thang nữa: chủ dự án *"khong dang san pham kem"* — cạn
#: cả bốn bậc thì đợi hạn mức mở lại (`GIAY_CHO_CAN_THANG_TOI_DA`) chứ không
#: viết content bằng model yếu.
THANG_MO_HINH = (MO_HINH_TOT_NHAT, "claude-opus-5", "claude-sonnet-5-5", "claude-sonnet-5")

#: Model đầu thang chọn được trên giao diện (đều đã thử 1 token qua CLI 12/10/2026).
MO_HINH_DAU_CHON_DUOC = (MO_HINH_TOT_NHAT, "claude-fable-5-1", "claude-fable-5",
                         "claude-opus-5", "claude-sonnet-5-5")

#: Mức suy nghĩ (`--effort` của CLI). Opus 5.5 mặc định `medium`; viết content
#: là việc chất lượng quyết định → mặc định `high` (chỉnh ở Cài đặt).
MUC_SUY_NGHI = ("low", "medium", "high", "xhigh", "max")
SUY_NGHI_MAC_DINH = "high"

#: Số tiến trình `claude` viết chữ cùng lúc trên cả máy (mọi tiến trình Python).
SONG_SONG_MAC_DINH = 3
SONG_SONG_TOI_DA = 8

#: Sổ khoá hạn mức, nằm cạnh sổ lỗi trong `workspace/viet-max/`.
TEP_HAN_MUC = "han-muc.json"

#: Khoá bao lâu khi Claude Code không nói giờ mở lại.
GIAY_KHOA_MAC_DINH = 3600.0


def co_claude_code() -> str:
    """Đường tới `claude` trên máy (PATH, chỗ cài quen, hoặc extension VS Code), hoặc rỗng."""
    from .claude_code import tim_claude  # noqa: PLC0415 — tránh vòng nhập

    return tim_claude()


# ── Cài đặt của đường thuê bao ──────────────────────────────────────────────


def _cai(goc: str) -> Dict[str, Any]:
    try:
        from . import cai_dat  # noqa: PLC0415

        return cai_dat.doc(goc or GOC_TOOL)
    except Exception:  # noqa: BLE001 — đọc cài đặt hỏng thì coi như mặc định
        return {}


_MAU_TEN_MODEL = re.compile(r"^claude-[a-z0-9][a-z0-9.\-]{1,60}$")


def thang_mo_hinh(goc: str = "") -> Tuple[str, ...]:
    """Thang model thật sự dùng: model đầu thang trong Cài đặt, rồi các bậc còn lại của `THANG_MO_HINH`."""
    dau = str(_cai(goc).get("claude_max_mo_hinh") or "").strip().lower()
    if not _MAU_TEN_MODEL.match(dau):
        dau = MO_HINH_TOT_NHAT
    return (dau,) + tuple(m for m in THANG_MO_HINH if m != dau)


def so_song_song(goc: str = "") -> int:
    try:
        n = int(_cai(goc).get("claude_max_song_song") or SONG_SONG_MAC_DINH)
    except (TypeError, ValueError):
        n = SONG_SONG_MAC_DINH
    return max(1, min(SONG_SONG_TOI_DA, n))


def muc_suy_nghi(goc: str = "") -> str:
    m = str(_cai(goc).get("claude_max_suy_nghi") or SUY_NGHI_MAC_DINH).strip().lower()
    return m if m in MUC_SUY_NGHI else SUY_NGHI_MAC_DINH


# ── Chọn đường viết chữ: thuê bao hay ví ────────────────────────────────────

CHON_TU_DONG, CHON_MAX, CHON_VI = "tu_dong", "claude_max", "vi"

#: Biến môi trường ép đường khi Cài đặt để "tu_dong": `vi` (bộ test đặt sẵn —
#: `tests/conftest.py`), `max`. Không đè lựa chọn TƯỜNG MINH trong Cài đặt.
BIEN_EP_DUONG = "MYTOOL_VIET_CHU"

#: Bộ test đặt `1`: `viet_bang_max` không bao giờ sinh tiến trình `claude` THẬT.
BIEN_CAM_CHAY_THAT = "MYTOOL_KHONG_CHAY_CLAUDE"

GIAY_NHO_DUONG = 30.0
_NHO_DUONG: Dict[Any, Tuple[float, Tuple[str, str]]] = {}
_KHOA_NHO = threading.Lock()


def xoa_nho_duong() -> None:
    with _KHOA_NHO:
        _NHO_DUONG.clear()


def _mtime(duong: str) -> float:
    try:
        return os.path.getmtime(duong)
    except OSError:
        return 0.0


def duong_viet_chu(goc: str = "") -> Tuple[str, str]:
    """`("max" | "vi" | "loi", câu giải thích)` — lượt viết chữ này đi đường nào.

    `"loi"`: Cài đặt ÉP thuê bao mà máy không có Claude Code — nơi gọi ném lỗi
    nói rõ chứ không lặng lẽ đi ví (chủ dự án 24/08/2026: *"đã nói máy này là
    claude max 20 thì cứ thế mà làm đừng cho nó đi nhầm"*).

    Nhớ `GIAY_NHO_DUONG` giây theo (gốc, biến ép, giờ sửa `cai-dat.json`): sửa
    Cài đặt là có hiệu lực ngay ở lượt sau.
    """
    goc = goc or GOC_TOOL
    ep = os.environ.get(BIEN_EP_DUONG, "").strip().lower()
    khoa = (os.path.abspath(goc), ep, _mtime(os.path.join(goc, "workspace", "cai-dat.json")))
    bay_gio = time.time()
    with _KHOA_NHO:
        san = _NHO_DUONG.get(khoa)
        if san is not None and bay_gio - san[0] < GIAY_NHO_DUONG:
            return san[1]
    ra = _tinh_duong(goc, ep)
    with _KHOA_NHO:
        _NHO_DUONG[khoa] = (bay_gio, ra)
    return ra


def _tinh_duong(goc: str, ep: str) -> Tuple[str, str]:
    cai = _cai(goc)
    chon = str(cai.get("viet_chu_bang") or CHON_TU_DONG).strip().lower()
    if chon == CHON_VI:
        return "vi", "Cài đặt chọn viết chữ bằng ví ShopAPI"
    if chon == CHON_MAX or cai.get("kich_ban_bang_claude_code") is True:
        if co_claude_code():
            return "max", "Cài đặt chọn viết chữ bằng thuê bao Claude Max"
        return "loi", ("Cài đặt chọn “Viết chữ bằng: Claude Max” nhưng máy này chưa có Claude Code. "
                       "Cài ở Cài đặt → Agent xây tool (rồi /login), hoặc chọn “Ví ShopAPI”.")
    if ep in ("vi", "shopapi", "tat", "0"):
        return "vi", "biến {0}={1}".format(BIEN_EP_DUONG, ep)
    if ep in ("max", "claude", "1"):
        return ("max", "biến {0}={1}".format(BIEN_EP_DUONG, ep)) if co_claude_code() else (
            "vi", "biến {0}={1} nhưng máy không có Claude Code".format(BIEN_EP_DUONG, ep))
    if not co_claude_code():
        return "vi", "máy chưa có Claude Code"
    from .claude_code import co_phien_dang_nhap  # noqa: PLC0415

    if not co_phien_dang_nhap():
        return "vi", "Claude Code chưa đăng nhập thuê bao Claude"
    return "max", "tự động: máy có Claude Code đã đăng nhập thuê bao Claude"


# ── Gói một hội thoại thành MỘT lời nhắc ────────────────────────────────────


def phang_tin_nhan(tin_nhan: Sequence[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """`messages` kiểu cổng chat → `(lời nhắc một khối, [ảnh data URL…])`.

    CLI `-p` nhận một lời nhắc qua stdin, không nhận mảng hội thoại. Nên:
    tin `system` (trừ câu `CHI_TRA_NOI_DUNG` chung — `CHI_DAO_VIET` đã nói đúng
    ý ấy) lên đầu; nhiều lượt thì chép lại thành "hội thoại trước đó" + "tin
    nhắn cần trả lời"; khối ảnh (Anthropic base64 hay `image_url` data URL) được
    tách ra theo thứ tự, chỗ của nó trong chữ đánh dấu `[ẢNH n]`.
    """
    try:
        from .goi_van_ban import CHI_TRA_NOI_DUNG  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        CHI_TRA_NOI_DUNG = ""
    anh: List[str] = []

    def _chu(nd: Any) -> str:
        if isinstance(nd, str):
            return nd
        if not isinstance(nd, list):
            return str(nd or "")
        phan: List[str] = []
        for k in nd:
            if isinstance(k, str):
                phan.append(k)
                continue
            if not isinstance(k, dict):
                continue
            loai = k.get("type")
            if loai == "text":
                phan.append(str(k.get("text") or ""))
            elif loai == "image":
                nguon = k.get("source") or {}
                if isinstance(nguon, dict) and nguon.get("type") == "base64" and nguon.get("data"):
                    anh.append("data:{0};base64,{1}".format(nguon.get("media_type") or "image/jpeg", nguon["data"]))
                    phan.append("[ẢNH {0}]".format(len(anh)))
            elif loai == "image_url":
                url = k.get("image_url")
                url = url.get("url") if isinstance(url, dict) else url
                if isinstance(url, str) and url.startswith("data:") and ";base64," in url:
                    anh.append(url)
                    phan.append("[ẢNH {0}]".format(len(anh)))
        return "\n".join(p for p in phan if p)

    he_thong: List[str] = []
    luot: List[Tuple[str, str]] = []
    for t in tin_nhan or []:
        if not isinstance(t, dict):
            continue
        vai = str(t.get("role") or "user")
        nd = _chu(t.get("content"))
        if vai == "system":
            if nd.strip() and nd.strip() != str(CHI_TRA_NOI_DUNG).strip():
                he_thong.append(nd.strip())
        else:
            luot.append((vai, nd))
    phan: List[str] = []
    if he_thong:
        phan.append("═══ CHỈ DẪN ═══\n" + "\n\n".join(he_thong))
    if len(luot) <= 1:
        if luot:
            phan.append(("═══ YÊU CẦU ═══\n" if he_thong else "") + luot[0][1])
    else:
        truoc, cuoi = luot[:-1], luot[-1]
        phan.append("═══ HỘI THOẠI TRƯỚC ĐÓ ═══\n" + "\n\n".join(
            "[{0}]\n{1}".format("Người dùng" if v == "user" else "Bạn (trợ lý)", c) for v, c in truoc))
        phan.append("═══ TIN NHẮN CẦN TRẢ LỜI NGAY BÂY GIỜ ═══\n" + cuoi[1])
    return "\n\n".join(p for p in phan if p), anh


def goi_tin_nhan_max(tin_nhan: Sequence[Dict[str, Any]], *, goc: str = "", toi_da_token: int = 0,
                     khoa: str = "", on_log: Optional[Callable[[str], None]] = None,
                     kiem_dung: Optional[Callable[[], None]] = None,
                     ngu: Callable[[float], None] = time.sleep,
                     viet: Optional[Callable[..., str]] = None) -> str:
    """Một lượt `goi_van_ban` đi đường thuê bao: gói hội thoại, đi thang model, trả chữ."""
    goc = goc or GOC_TOOL
    loi_nhac, anh = phang_tin_nhan(tin_nhan)
    goi = dung_goi_chat_max(goc, on_log=on_log, kiem_dung=kiem_dung, ngu=ngu, viet=viet)
    return goi(loi_nhac, khoa=khoa, toi_da_token=int(toi_da_token or 0), anh=anh)


#: Lời nhắc HỆ THỐNG của tiến trình viết (thay hẳn lời nhắc agent của Claude Code — xem đầu tệp).
#:
#: ═══ ĐO ĐƯỢC TRÊN LƯỢT CHẠY THẬT 24/08/2026, TL4-T7/0011 ═══
#:
#: Bước "đối chiếu và sửa" gửi qua Claude Code thì nó… làm đúng kiểu agent:
#: định GHI bản sửa ra một tệp rồi trả lời bằng **bản tóm tắt các chỗ đã sửa**
#: — 743 ký tự tiếng Việt thay vì 4.800 ký tự tiếng Nhật. Nguồn cơn: lời nhắc
#: `3-sua.md` của kênh có câu "đặt tên file kichban_…". Nên phải dặn ngay trong
#: system prompt, và rút luôn công cụ khỏi tay nó (`_CONG_CU_CAM`, `--tools`).
CHI_DAO_VIET = (
    "Bạn đang được gọi như một bộ máy sinh VĂN BẢN, không phải một agent. "
    "Câu trả lời của bạn phải là CHÍNH nội dung văn bản được yêu cầu, đầy đủ "
    "từ chữ đầu tới chữ cuối, và KHÔNG có gì khác: không dùng công cụ, không "
    "ghi hay mở tệp, không tóm tắt việc đã làm, không hỏi lại, không lời dẫn "
    "trước hay sau, không rào ```. Nếu lời nhắc bảo ghi kết quả ra tệp hoặc "
    "đặt tên tệp, hãy hiểu là: in TOÀN BỘ nội dung tệp ấy làm câu trả lời. "
    "Câu trả lời phải BẮT ĐẦU NGAY bằng chữ đầu tiên của văn bản — không có "
    "câu mở đầu kiểu \"I'll…\", \"Let me…\", \"Here is…\", không kể lại bạn "
    "sắp làm gì.")

#: Lời dặn thêm khi lời gọi KÈM ẢNH (đọc chữ bìa, chấm bìa, soát bìa…).
#:
#: Claude Code gọi bằng `-p` không nhận ảnh qua stdin, nhưng công cụ `Read` của
#: nó mở được tệp ảnh và mô hình NHÌN thấy ảnh ấy. Nên ảnh được ghi tạm vào chính
#: thư mục rỗng, và `Read` là công cụ DUY NHẤT được mở ra cho lượt ấy.
CHI_DAO_ANH = (
    " NGOẠI LỆ DUY NHẤT cho lượt này: hãy dùng công cụ Read để mở {0} trong "
    "thư mục làm việc hiện tại, đúng thứ tự, rồi trả lời dựa trên ảnh. Ngoài "
    "{1} ra vẫn không dùng công cụ nào khác.")

#: Rút sạch công cụ (lớp thứ hai, sau `--tools`). Cố ý KHÔNG cấm `Read`: đường đọc ảnh.
_CONG_CU_CAM = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash",
                "Task", "WebFetch", "WebSearch", "TodoWrite")


#: Cài đặt đè cho tiến trình viết (qua `--settings`, không ghi vào tệp cấu hình nào của chủ máy).
#:
#: ═══ `crossSessionInbound = refuse` — ĐO TRÊN LƯỢT THẬT 24/08/2026, TL4-T7/0012 ═══
#:
#: Một phiên khác gửi tin tới MỌI phiên trên máy — kể cả tiến trình viết nền;
#: nó bỏ bài đi trả lời tin.
#:
#: ═══ `claudeMdExcludes` — ĐO 12/10/2026 TRÊN MÁY NÀY ═══
#:
#: Thư mục rỗng `workspace/viet-max/<mã>` vẫn nằm DƯỚI thư mục tool, và Claude
#: Code tự nạp mọi `CLAUDE.md` / `CLAUDE.local.md` ở các thư mục cha — tức luật
#: vận hành VPS của chủ dự án lọt vào MỌI lượt viết kịch bản. Hỏi thẳng "ngữ
#: cảnh có luật nào về VPS không": không chặn → "CÓ — Luật cho mọi phiên
#: Claude…", 5.840 token đầu vào; chặn → "KHÔNG", 1.273 token.
CAI_DAT_CACH_LY = json.dumps({"crossSessionInbound": "refuse",
                              "claudeMdExcludes": ["**/CLAUDE.md", "**/CLAUDE.local.md"]},
                             separators=(",", ":"))

#: Chỉ nạp cài đặt "local" của thư mục làm việc — mà thư mục ấy RỖNG. Tức KHÔNG
#: nạp `~/.claude/settings.json` (máy khách có thể đã được Studio cắm khoá ShopAPI
#: vào `env` ở đó — `claude_code.cai_vao_may` — và Claude Code thấy khoá là dùng
#: khoá, lặng lẽ trừ ví). Phiên đăng nhập thuê bao nằm ở `.credentials.json`,
#: không phải cài đặt, nên vẫn dùng được (đo 12/10/2026).
NGUON_CAI_DAT = "local"


def _chi_dao(ten_anh: Sequence[str]) -> str:
    chu = CHI_DAO_VIET + " Hôm nay là ngày {0}.".format(_dt.date.today().isoformat())
    if ten_anh:
        ds = ", ".join("`{0}`".format(t) for t in ten_anh)
        chu += CHI_DAO_ANH.format(
            ("tệp ảnh " + ds) if len(ten_anh) == 1 else ("{0} tệp ảnh {1}".format(len(ten_anh), ds)),
            "các tệp ấy" if len(ten_anh) > 1 else "tệp ấy")
    return chu


def _ghi_anh_tam(thu_muc: str, data_url: str) -> str:
    """Ghi ảnh `data:<kiểu>;base64,…` ra tệp trong `thu_muc`. Trả về TÊN tệp."""
    dau, _, du_lieu = (data_url or "").partition(";base64,")
    kieu = dau.split(":", 1)[-1].strip().lower() or "image/jpeg"
    duoi = {"image/png": ".png", "image/webp": ".webp",
            "image/gif": ".gif"}.get(kieu, ".jpg")
    ten = "anh-{0}{1}".format(uuid.uuid4().hex[:8], duoi)
    with open(os.path.join(thu_muc, ten), "wb") as tep:
        tep.write(base64.b64decode(du_lieu))
    return ten


def _ds_anh(anh: Union[str, Sequence[str], None]) -> List[str]:
    if not anh:
        return []
    if isinstance(anh, str):
        return [anh]
    return [a for a in anh if isinstance(a, str) and a]


def _lenh(duong_claude: str, mo_hinh: str, ten_anh: Union[str, Sequence[str]] = "",
          effort: str = "") -> List[str]:
    """Dòng lệnh gọi CLI một lượt (`-p`) cho MỘT lượt viết.

    Lời nhắc đi qua **stdin**: dòng lệnh Windows chỉ chứa được ~32k ký tự.

    `--system-prompt` (THAY, không nối thêm) + `--tools ""` + `--strict-mcp-config`
    + `--disable-slash-commands` + `--no-session-persistence`: lượt viết là một
    lượt LLM gọn — đo 12/10/2026: 2.013 token đầu vào thay vì 37.104 (xem đầu
    tệp), và không để lại hàng nghìn tệp phiên trong `~/.claude/projects/`.

    KHÔNG `--permission-mode bypassPermissions`. `--disallowedTools` nhận nhiều
    giá trị nên phải đứng CUỐI — mọi cờ đặt sau nó bị nuốt làm tên công cụ.
    """
    ds_anh = _ds_anh(ten_anh)
    lenh = [duong_claude, "--print", "--output-format", "json",
            "--model", mo_hinh,
            "--settings", CAI_DAT_CACH_LY, "--setting-sources", NGUON_CAI_DAT,
            "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"]
    if effort in MUC_SUY_NGHI:
        lenh += ["--effort", effort]
    lenh += ["--system-prompt", _chi_dao(ds_anh),
             "--tools", "Read" if ds_anh else ""]
    return lenh + ["--disallowedTools", *_CONG_CU_CAM]


def _boc_goi(chu: str) -> Dict[str, Any]:
    """Khối JSON `type == "result"` Claude Code in ra (có bản in dòng cảnh báo trước nó)."""
    tho = (chu or "").strip()
    goi: Any = None
    try:
        goi = json.loads(tho)
    except ValueError:
        for dong in tho.splitlines():
            dong = dong.strip()
            if not dong.startswith("{"):
                continue
            try:
                thu = json.loads(dong)
            except ValueError:
                continue
            if isinstance(thu, dict) and thu.get("type") == "result":
                goi = thu
    if not isinstance(goi, dict):
        raise RuntimeError("Claude Code không trả về kết quả đọc được.")
    return goi


def _ket_tu_goi(goi: Dict[str, Any]) -> str:
    if goi.get("is_error"):
        raise RuntimeError("Claude Code báo lỗi: {0}".format(
            str(goi.get("result") or goi.get("subtype") or "không rõ")[:200]))
    ket = goi.get("result")
    if not isinstance(ket, str) or not ket.strip():
        raise RuntimeError("Claude Code trả về nội dung rỗng.")
    return ket.strip()


def _boc_ket_qua(chu: str) -> str:
    """Bóc trường `result` khỏi JSON Claude Code in ra. Hỏng thì ném lỗi rõ."""
    return _ket_tu_goi(_boc_goi(chu))


def gio_han_theo_token(toi_da_token: int) -> float:
    """Giây chờ một lượt: sàn `GIAY_CHO_MAC_DINH`, lượt xin nhiều chữ được đợi thêm (~25 token/giây), trần 1 giờ."""
    try:
        tok = int(toi_da_token or 0)
    except (TypeError, ValueError):
        tok = 0
    return max(GIAY_CHO_MAC_DINH, min(3600.0, tok / 25.0 + 300.0))


# ── Suất tiến trình `claude` cả máy ─────────────────────────────────────────

THU_MUC_SUAT = "suat"


class HetGioChoSuat(TimeoutError):
    """Đợi quá `cho_toi_da` giây vẫn chưa có suất."""


def _duong_suat(goc: str) -> str:
    return os.path.join(goc, THU_MUC_RONG, THU_MUC_SUAT)


def _suat_con_song(duong: str, bay_gio: float) -> bool:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        # Vừa tạo mà chưa kịp ghi JSON — coi như đang giữ, trừ khi đã quá lâu.
        try:
            return bay_gio - os.path.getmtime(duong) < 60.0
        except OSError:
            return False
    try:
        pid = int(du.get("pid") or 0)
        het = float(du.get("het_han") or 0.0)
    except (TypeError, ValueError, AttributeError):
        return False
    if het and bay_gio > het:
        return False
    from .khe import pid_con_song  # noqa: PLC0415

    return pid_con_song(pid)


def so_suat_dang_giu(goc: str = "") -> int:
    thu_muc = _duong_suat(goc or GOC_TOOL)
    try:
        ten = [t for t in os.listdir(thu_muc) if t.endswith(".json")]
    except OSError:
        return 0
    bay_gio = time.time()
    return sum(1 for t in ten if _suat_con_song(os.path.join(thu_muc, t), bay_gio))


@contextlib.contextmanager
def giu_suat(goc: str = "", *, so_suat: Optional[int] = None, viec: str = "",
             kiem_dung: Optional[Callable[[], None]] = None,
             on_log: Optional[Callable[[str], None]] = None,
             cho_toi_da: Optional[float] = None, gio_han: float = GIAY_CHO_MAC_DINH,
             nhip: float = 1.0, ngu: Callable[[float], None] = time.sleep) -> Iterator[int]:
    """Giữ MỘT suất tiến trình `claude` của cả máy trong lúc khối lệnh chạy.

    N suất = tệp `workspace/viet-max/suat/<i>.json` tạo bằng `O_EXCL` (không có
    khe hở đọc-rồi-ghi giữa các tiến trình). Suất của tiến trình đã chết, hay
    quá hạn (`gio_han` + 10 phút — Windows tái dùng PID), tự được dọn. Đợi thì
    hỏi đĩa cục bộ mỗi `nhip` giây (không mạng) và hỏi `kiem_dung` mỗi nhịp —
    bấm Dừng là dừng ngay. Quá `cho_toi_da` → `HetGioChoSuat`.
    """
    goc = goc or GOC_TOOL
    n = max(1, int(so_suat or so_song_song(goc)))
    thu_muc = _duong_suat(goc)
    os.makedirs(thu_muc, exist_ok=True)
    bat_dau = time.time()
    da_bao = False
    duong = ""
    while not duong:
        if kiem_dung is not None:
            kiem_dung()
        bay_gio = time.time()
        noi_dung = {"pid": os.getpid(), "luc": bay_gio, "het_han": bay_gio + float(gio_han) + 600.0,
                    "viec": str(viec or "")[:120]}
        dau = int.from_bytes(os.urandom(1), "little") % n
        for k in range(n):
            thu = os.path.join(thu_muc, "{0}.json".format((dau + k) % n))
            if os.path.exists(thu) and not _suat_con_song(thu, bay_gio):
                from .khe import xoa_tep_ben_vung  # noqa: PLC0415

                xoa_tep_ben_vung(thu)
            try:
                fd = os.open(thu, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except OSError:
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as tep:
                json.dump(noi_dung, tep, ensure_ascii=False)
            duong = thu
            break
        if duong:
            break
        da_cho = time.time() - bat_dau
        if cho_toi_da is not None and da_cho >= cho_toi_da:
            raise HetGioChoSuat("đợi {0:.0f} giây vẫn chưa có suất Claude ({1}/{1} đang chạy)".format(da_cho, n))
        if not da_bao and da_cho >= 20.0 and on_log is not None:
            da_bao = True
            on_log("  chờ lượt Claude Max: {0}/{0} tiến trình đang viết (trần đặt ở Cài đặt)…".format(n))
        ngu(max(0.05, nhip))
    try:
        yield n
    finally:
        from .khe import xoa_tep_ben_vung  # noqa: PLC0415

        xoa_tep_ben_vung(duong)


# ── Sổ dùng thuê bao ────────────────────────────────────────────────────────

TEP_SO_DUNG = "so-dung.jsonl"
#: Quá ngần này byte thì đẩy sang `so-dung.1.jsonl` (đè bản cũ) — sổ không phình mãi.
TRAN_SO_DUNG_BYTE = 8 * 1024 * 1024
_KHOA_SO = threading.Lock()


def _duong_so_dung(goc: str) -> str:
    return os.path.join(goc or GOC_TOOL, THU_MUC_RONG, TEP_SO_DUNG)


def ghi_so_dung(goc: str, muc: Dict[str, Any]) -> None:
    """Nối một dòng JSON vào `workspace/viet-max/so-dung.jsonl`. Không bao giờ ném lỗi."""
    try:
        dong = dict(muc)
        dong.setdefault("luc", _dt.datetime.now().isoformat(timespec="seconds"))
        dong.setdefault("pid", os.getpid())
        duong = _duong_so_dung(goc)
        with _KHOA_SO:
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            try:
                if os.path.getsize(duong) > TRAN_SO_DUNG_BYTE:
                    os.replace(duong, duong[:-len(".jsonl")] + ".1.jsonl")
            except OSError:
                pass
            with open(duong, "a", encoding="utf-8") as tep:
                tep.write(json.dumps(dong, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — sổ hỏng không được làm hỏng lượt viết
        pass


def tom_tat_so_dung(goc: str = "", gio: float = 24.0,
                    bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Tải thuê bao trong `gio` giờ qua: số lượt, giây, theo model, theo việc, số lượt hỏng."""
    bay_gio = bay_gio or _dt.datetime.now()
    moc = bay_gio - _dt.timedelta(hours=float(gio))
    ra: Dict[str, Any] = {"gio": gio, "luot": 0, "hong": 0, "giay": 0.0, "token_vao": 0, "token_ra": 0,
                          "theo_model": {}, "theo_viec": {}}
    try:
        with open(_duong_so_dung(goc), "r", encoding="utf-8") as tep:
            dong = tep.readlines()[-200000:]
    except OSError:
        return ra
    for d in dong:
        try:
            m = json.loads(d)
            luc = _dt.datetime.fromisoformat(str(m.get("luc")))
        except (ValueError, TypeError):
            continue
        if luc < moc:
            continue
        ra["luot"] += 1
        if not m.get("ok"):
            ra["hong"] += 1
        try:
            ra["giay"] += float(m.get("giay") or 0)
            ra["token_vao"] += int(m.get("token_vao") or 0)
            ra["token_ra"] += int(m.get("token_ra") or 0)
        except (TypeError, ValueError):
            pass
        mh = str(m.get("mo_hinh") or "?")
        ra["theo_model"][mh] = ra["theo_model"].get(mh, 0) + 1
        viec = re.split(r"[:/]", str(m.get("viec") or "?"))[0][:40] or "?"
        ra["theo_viec"][viec] = ra["theo_viec"].get(viec, 0) + 1
    ra["giay"] = round(ra["giay"], 1)
    return ra


# ── Trạng thái cho gác tổng ("Việc của bạn") ────────────────────────────────

TEP_TRANG_THAI = "trang-thai.json"
_KHOA_TT = threading.Lock()
_GHI_OK_CUOI = {"luc": 0.0}


def _duong_trang_thai(goc: str) -> str:
    return os.path.join(goc or GOC_TOOL, THU_MUC_RONG, TEP_TRANG_THAI)


def doc_trang_thai(goc: str = "") -> Dict[str, Any]:
    """`{"can_thang": {...}, "chua_dang_nhap": {...}, "hong": {...}, "ok_cuoi": epoch}` — mục nào có là sự cố còn đó.
    Đọc bởi `core.chot_an_toan.kiem_claude_max` (gác tổng, mỗi 15 phút)."""
    try:
        with open(_duong_trang_thai(goc), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def _sua_trang_thai(goc: str, sua: Callable[[Dict[str, Any]], bool]) -> None:
    try:
        with _KHOA_TT:
            du = doc_trang_thai(goc)
            if not sua(du):
                return
            duong = _duong_trang_thai(goc)
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            tam = "{0}.{1}.tam".format(duong, os.getpid())
            with open(tam, "w", encoding="utf-8") as tep:
                json.dump(du, tep, ensure_ascii=False, indent=1)
            os.replace(tam, duong)
    except Exception:  # noqa: BLE001 — trạng thái hỏng không được làm hỏng lượt viết
        pass


def _danh_dau_ok(goc: str, bay_gio: float) -> None:
    """Viết được → xoá mọi sự cố đang treo (gác tổng thôi báo). Ghi `ok_cuoi` thưa (≤ 1 lần/10 phút/tiến trình)."""
    du = doc_trang_thai(goc)
    co_su_co = any(k in du for k in ("can_thang", "chua_dang_nhap", "hong"))
    if not co_su_co and bay_gio - _GHI_OK_CUOI["luc"] < 600.0:
        return
    _GHI_OK_CUOI["luc"] = bay_gio

    def sua(d: Dict[str, Any]) -> bool:
        for k in ("can_thang", "chua_dang_nhap", "hong"):
            d.pop(k, None)
        d["ok_cuoi"] = bay_gio
        return True

    _sua_trang_thai(goc, sua)


def la_loi_dang_nhap(loi: BaseException) -> bool:
    chu = _chu_cua_loi(loi)
    return any(x in chu for x in ("log in", "login", "logged", "authenticat", "unauthorized", "401",
                                  "oauth", "credential", "đăng nhập"))


def _bao_khan(goc: str, loai: str, chuyen_gi: str, can_lam_gi: str, neu_khong_lam: str) -> None:
    """Báo RA NGOÀI ngay (Telegram/webhook nếu chủ máy cấu hình — `core.bao_dong` tự chống lặp 24 giờ). Gác tổng đọc
    `trang-thai.json` để hiện ở "Việc của bạn" + `loi-chay-max.md` (`core.chot_an_toan.kiem_claude_max`)."""
    try:
        from . import bao_dong  # noqa: PLC0415

        bao_dong.bao_dong_khan(loai, chuyen_gi, can_lam_gi, neu_khong_lam, goc=goc)
    except Exception:  # noqa: BLE001
        pass


def _bao_can_thang(goc: str, den: float, bay_gio: float) -> None:
    def sua(d: Dict[str, Any]) -> bool:
        cu = d.get("can_thang") if isinstance(d.get("can_thang"), dict) else {}
        d["can_thang"] = {"luc": bay_gio, "tu": cu.get("tu") or bay_gio, "mo_lai": den,
                          "lan": int(cu.get("lan") or 0) + 1}
        return True

    _sua_trang_thai(goc, sua)
    _bao_khan(goc, "claude_max_can_han_muc",
              "Thuê bao Claude Max của máy đã cạn hạn mức ở mọi model — phần viết chữ (kịch bản, tiêu đề, chọn "
              "content…) đang ĐỢI, dự kiến mở lại khoảng {0} rồi tự chạy tiếp.".format(_gio_ngan(den)),
              "Không bắt buộc: đợi là tool tự viết tiếp. Muốn chạy ngay thì thêm hạn mức ở claude.ai/settings/usage, "
              "hoặc vào Cài đặt → Viết chữ bằng → Ví ShopAPI.",
              "Video ra chậm tới khi hạn mức mở lại; tool KHÔNG tự chuyển sang ví.")


def _bao_hong_cuoi(goc: str, loi: Optional[BaseException], bay_gio: float) -> None:
    if loi is None:
        return
    dang_nhap = la_loi_dang_nhap(loi)

    def sua(d: Dict[str, Any]) -> bool:
        ten = "chua_dang_nhap" if dang_nhap else "hong"
        cu = d.get(ten) if isinstance(d.get(ten), dict) else {}
        d[ten] = {"luc": bay_gio, "tu": cu.get("tu") or bay_gio, "lan": int(cu.get("lan") or 0) + 1,
                  "loi": str(loi)[:240]}
        return True

    _sua_trang_thai(goc, sua)
    if dang_nhap:
        _bao_khan(goc, "claude_max_chua_dang_nhap",
                  "Claude Code trên máy không viết được: chưa đăng nhập hoặc phiên đăng nhập thuê bao Claude đã hết "
                  "hạn.",
                  "Mở Claude Code trên máy này (VS Code hoặc terminal), gõ /login và đăng nhập lại tài khoản Claude "
                  "Max. Xong tool tự chạy lại.",
                  "Mọi khâu viết chữ dừng — không có kịch bản/tiêu đề mới, kênh ngừng ra video.")


# ── Một lượt viết ───────────────────────────────────────────────────────────


def _chu_tien_trinh() -> str:
    """Chủ của tiến trình `claude` trong sổ `core.tien_trinh_con`: chỉ GIAO DIỆN mới là `gui` (mở giao diện lên là
    giết xác `gui` cũ). Lượt của giám đốc, trạm nền, bộ não, máy ảo… là việc tách rời — không được để mở giao diện
    giết giữa chừng."""
    from .tien_trinh_con import CHU_GUI, CHU_TU_CHAY  # noqa: PLC0415

    try:
        ten = os.path.basename(str(sys.argv[0] or "")).lower()
    except (IndexError, TypeError):
        ten = ""
    return CHU_GUI if ten == "shopapi_studio_qt.py" else CHU_TU_CHAY


def viet_bang_max(
    loi_nhac: str,
    *,
    goc: str,
    mo_hinh: str = MO_HINH_TOT_NHAT,
    kiem_dung: Optional[Callable[[], None]] = None,
    gio_han: float = GIAY_CHO_MAC_DINH,
    mo_tien_trinh: Optional[Callable[..., Any]] = None,
    anh: Union[str, Sequence[str]] = "",
    effort: str = "",
    viec: str = "",
    on_log: Optional[Callable[[str], None]] = None,
    so_suat: Optional[int] = None,
) -> str:
    """Một lượt nhờ Claude Code viết, trên phiên đăng nhập của máy. Trả về chữ.

    `anh`: một hay nhiều ảnh `data:<kiểu>;base64,…` — ghi tạm vào thư mục rỗng
    cho Claude Code `Read`, xoá ngay khi xong. `mo_tien_trinh` thay được để bài
    kiểm chạy không cần Claude Code. Giữ một suất (`giu_suat`) suốt lượt; ghi
    một dòng sổ dùng (`ghi_so_dung`).

    **Chạy ở luồng nền** — không bao giờ gọi từ luồng vẽ.
    """
    from .claude_code import moi_truong_max  # noqa: PLC0415 — tránh vòng nhập

    if mo_tien_trinh is None and os.environ.get(BIEN_CAM_CHAY_THAT) == "1":
        raise RuntimeError("bài kiểm không được chạy Claude Code thật ({0}=1)".format(BIEN_CAM_CHAY_THAT))
    duong = co_claude_code()
    if not duong and mo_tien_trinh is None:
        raise RuntimeError("máy chưa cài Claude Code")
    ds_anh = _ds_anh(anh)
    moi_truong = moi_truong_max()
    # Không cập nhật/đo đạc nền ở mỗi lượt viết (hàng trăm lượt/ngày) — chỉ việc cần.
    moi_truong["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"

    with giu_suat(goc, so_suat=so_suat, viec=viec, kiem_dung=kiem_dung, on_log=on_log, gio_han=gio_han):
        # ═══ MỖI LƯỢT GỌI MỘT THƯ MỤC RIÊNG ═══
        #
        # Đo 24/08/2026: 3–4 lượt SONG SONG trong cùng một thư mục là có lượt
        # thoát mã 1 không một dòng lý do. Mỗi lượt một thư mục con rồi xoá.
        thu_muc = os.path.join(goc, THU_MUC_RONG, uuid.uuid4().hex[:8])
        os.makedirs(thu_muc, exist_ok=True)
        try:
            ten_anh = [_ghi_anh_tam(thu_muc, a) for a in ds_anh]
            return _chay(mo_tien_trinh or subprocess.Popen, duong or "claude",
                         mo_hinh, thu_muc, ten_anh, loi_nhac, kiem_dung, gio_han,
                         moi_truong, effort=effort, viec=viec)
        finally:
            shutil.rmtree(thu_muc, ignore_errors=True)


def _so_lieu_goi(goi: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Token / model thật / ước tính USD (giá API, chỉ để so tải — thuê bao không trừ tiền) từ khối kết quả."""
    if not isinstance(goi, dict):
        return {}
    ra: Dict[str, Any] = {}
    u = goi.get("usage") if isinstance(goi.get("usage"), dict) else {}
    try:
        ra["token_vao"] = int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0) \
            + int(u.get("cache_read_input_tokens") or 0)
        ra["token_ra"] = int(u.get("output_tokens") or 0)
    except (TypeError, ValueError):
        pass
    mu = goi.get("modelUsage")
    if isinstance(mu, dict) and mu:
        ra["mo_hinh_that"] = sorted(str(k) for k in mu)
    if goi.get("total_cost_usd") is not None:
        ra["usd_uoc"] = goi.get("total_cost_usd")
    if goi.get("num_turns") is not None:
        ra["luot"] = goi.get("num_turns")
    return ra


def _chay(mo, duong: str, mo_hinh: str, thu_muc: str, ten_anh: Union[str, Sequence[str]],
          loi_nhac: str, kiem_dung, gio_han: float, moi_truong, effort: str = "",
          viec: str = "") -> str:
    """Bật tiến trình, đưa lời nhắc qua stdin, canh dừng, bóc kết quả, ghi sổ dùng."""
    ds_anh = _ds_anh(ten_anh)
    vao = len(loi_nhac)
    if ds_anh:
        loi_nhac = ("(Ảnh cần xem nằm ở {0} trong thư mục làm việc — mở bằng Read trước khi trả lời: {1}.)\n\n"
                    "{2}".format("tệp" if len(ds_anh) == 1 else "các tệp",
                                 ", ".join("[ẢNH {0}] = `{1}`".format(i, t) for i, t in enumerate(ds_anh, 1)),
                                 loi_nhac))
    from .tien_trinh_con import bo_ghi_nhan, ghi_nhan  # noqa: PLC0415

    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    t0 = time.time()
    tien_trinh = mo(_lenh(duong, mo_hinh, ds_anh, effort), cwd=thu_muc,
                    env=moi_truong, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    creationflags=co)
    # Đo 24/08/2026: giết tool giữa lúc `claude` đang viết thì nó vẫn chạy nốt
    # bảy phút. Ghi nhận để tắt tool là nó tắt, mở tool là dọn xác nếu còn.
    # `thu_muc` = <gốc>/workspace/viet-max/<mã lượt> → lùi ba cấp là gốc tool.
    goc_tool = os.path.dirname(os.path.dirname(os.path.dirname(thu_muc)))
    try:
        ghi_nhan(tien_trinh, goc_tool, "claude", chu=_chu_tien_trinh())
    except TypeError:  # đồ giả / bản cũ không nhận `chu`
        ghi_nhan(tien_trinh, goc_tool, "claude")
    so: Dict[str, Any] = {"mo_hinh": mo_hinh, "viec": str(viec or "")[:120], "vao": vao, "anh": len(ds_anh),
                          "effort": effort or ""}
    try:
        tho = _doi_tho(tien_trinh, loi_nhac, kiem_dung, gio_han)
        goi = _boc_goi(tho)
        so.update(_so_lieu_goi(goi))
        ket = _ket_tu_goi(goi)
        so.update({"ok": True, "ra": len(ket)})
        return ket
    except RuntimeError as loi:
        _ghi_loi_cuoi(os.path.dirname(thu_muc), loi, mo_hinh, len(loi_nhac))
        ra_tho = getattr(loi, "chi_tiet", ("", ""))[0]
        if ra_tho:
            try:
                so.update(_so_lieu_goi(_boc_goi(ra_tho)))
            except RuntimeError:
                pass
        so.update({"ok": False, "loi": str(loi)[:200]})
        raise
    except BaseException as loi:  # bấm Dừng (Cancelled…) — vẫn ghi sổ rồi ném nguyên
        so.update({"ok": False, "loi": "dừng: " + type(loi).__name__})
        raise
    finally:
        so["giay"] = round(time.time() - t0, 1)
        ghi_so_dung(goc_tool, so)
        bo_ghi_nhan(tien_trinh, goc_tool)


#: Tệp ghi lại các lần Claude Code thoát lỗi, nằm ở `workspace/viet-max/`.
TEP_LOI_CUOI = "loi-gan-nhat.txt"


def _dau_va_duoi(chu: str, moi_dau: int = 1200) -> str:
    """Giữ ĐẦU và ĐUÔI của một luồng dài, bỏ khúc giữa (JSON của Claude Code để `"result"` ở CUỐI)."""
    chu = str(chu or "")
    if len(chu) <= moi_dau * 2:
        return chu
    return "{0}\n…[bỏ {1} ký tự giữa]…\n{2}".format(
        chu[:moi_dau], len(chu) - moi_dau * 2, chu[-moi_dau:])


def _ghi_loi_cuoi(thu_muc_cha: str, loi: BaseException, mo_hinh: str,
                  do_dai_loi_nhac: int) -> None:
    """Nối một mục vào `workspace/viet-max/loi-gan-nhat.txt` (giữ ~40 KB cuối). Không bao giờ làm hỏng lượt viết."""
    try:
        os.makedirs(thu_muc_cha, exist_ok=True)
        tep = os.path.join(thu_muc_cha, TEP_LOI_CUOI)
        ra, err = getattr(loi, "chi_tiet", ("", ""))
        muc = ("\n=== {0} | {1} | lời nhắc {2} ký tự\n{3}\n--- stdout ({4} ký tự):\n{5}"
               "\n--- stderr ({6} ký tự):\n{7}\n").format(
                   time.strftime("%Y-%m-%d %H:%M:%S"), mo_hinh, do_dai_loi_nhac,
                   str(loi)[:300], len(ra), _dau_va_duoi(ra),
                   len(err), _dau_va_duoi(err))
        cu = ""
        try:
            with open(tep, encoding="utf-8") as t:
                cu = t.read()
        except OSError:
            pass
        with open(tep, "w", encoding="utf-8") as t:
            t.write((cu + muc)[-40000:])
    except Exception:  # noqa: BLE001 — ghi sổ lỗi không được làm hỏng gì
        pass


def _doi_tho(tien_trinh, loi_nhac: str, kiem_dung, gio_han: float) -> str:
    """Đưa lời nhắc, canh dừng, trả stdout NGUYÊN VĂN (thoát lỗi thì ném, kèm `chi_tiet`)."""

    # ═══ ĐỌC Ở LUỒNG RIÊNG, CANH DỪNG Ở LUỒNG NÀY ═══
    #
    # `communicate` chạy ở luồng phụ (khối JSON to hơn bộ đệm ống của Windows,
    # đọc từng dòng ở đây là kẹt cả hai bên), luồng này chỉ ngóng cờ dừng mỗi
    # nửa giây — canh MỘT TIẾN TRÌNH TRÊN MÁY, không phải hỏi máy chủ.
    hop: dict = {}

    def _doi() -> None:
        try:
            hop["ra"], hop["loi"] = tien_trinh.communicate(input=loi_nhac)
        except Exception as loi:  # noqa: BLE001 — mang về luồng chính xử lý
            hop["nem"] = loi

    luong = threading.Thread(target=_doi, daemon=True)
    luong.start()
    da_cho = 0.0
    while luong.is_alive():
        luong.join(0.5)
        da_cho += 0.5
        if kiem_dung is not None:
            try:
                kiem_dung()
            except BaseException:
                tien_trinh.kill()
                raise
        if da_cho >= gio_han:
            tien_trinh.kill()
            raise RuntimeError(
                "Claude Code chưa viết xong sau {0:.0f} giây".format(gio_han))
    if "nem" in hop:
        raise RuntimeError("không chạy được Claude Code: {0}".format(
            str(hop["nem"])[:200]))
    if tien_trinh.returncode != 0:
        # stderr là chỗ Claude Code nói vì sao: chưa đăng nhập, hết hạn mức…
        ly_do = str(hop.get("loi") or hop.get("ra") or "").strip()[:200]
        loi = RuntimeError("Claude Code thoát lỗi (mã {0}): {1}".format(
            tien_trinh.returncode, ly_do or "không nói lý do"))
        loi.chi_tiet = (str(hop.get("ra") or ""), str(hop.get("loi") or ""))
        raise loi
    return str(hop.get("ra") or "")


def _doi_ket_qua(tien_trinh, loi_nhac: str, kiem_dung, gio_han: float) -> str:
    """Đưa lời nhắc, canh dừng, bóc kết quả."""
    return _boc_ket_qua(_doi_tho(tien_trinh, loi_nhac, kiem_dung, gio_han))


#: Nhịp chờ giữa hai lần thử lại Claude Code, giây. Giãn dần.
NHIP_THU_LAI = (15.0, 30.0, 60.0, 120.0, 300.0)


def mang_toi_anthropic(giay: float = 4.0) -> bool:
    """Máy có mở được kết nối tới máy chủ Anthropic không (một cú bắt tay TCP,
    không gửi gì, không tốn gì)."""
    try:
        with socket.create_connection(("api.anthropic.com", 443), timeout=giay):
            return True
    except OSError:
        return False


def chan_doan_loi(loi: BaseException, kiem_mang=mang_toi_anthropic) -> str:
    """Một câu tiếng người giải thích vì sao Claude Code không viết được.

    Thứ tự xét: lời Claude Code nói (chưa đăng nhập / hạn mức / quá tải) →
    bắt tay mạng tới Anthropic → còn lại là "lỗi lẻ, xem tệp sổ lỗi".
    """
    ra, err = getattr(loi, "chi_tiet", ("", ""))
    chu = (str(loi) + " " + str(ra) + " " + str(err)).lower()
    if any(x in chu for x in ("log in", "login", "logged", "authenticat",
                              "unauthorized", "401", "oauth", "credential")):
        return ("Claude Code CHƯA ĐĂNG NHẬP — mở tab “Agent xây tool”, gõ /login "
                "rồi chạy tiếp")
    if la_het_han_muc(loi):
        return ("model này đã CẠN hạn mức thuê bao — tool tụt xuống bậc model "
                "dưới ngay, không đợi")
    if any(x in chu for x in ("rate limit", "429", "overloaded", "529",
                              "too many")):
        return ("máy chủ Anthropic quá tải hoặc nhịp gọi quá dày — tool đợi rồi "
                "thử lại, không cần làm gì")
    if "chưa viết xong sau" in chu:
        return "quá giờ chờ — mạng chậm hoặc bài quá dài; tool thử lại"
    try:
        co_mang = bool(kiem_mang())
    except Exception:  # noqa: BLE001
        co_mang = False
    if not co_mang:
        return ("máy KHÔNG nối được tới Anthropic — mạng rớt hoặc đường truyền "
                "đang kín (máy này đang tải/đẩy gì nặng không?); tool thử lại")
    return ("mạng bình thường, Claude Code thoát mà không nói lý do — lỗi lẻ, "
            "tool thử lại; chi tiết ở workspace/viet-max/" + TEP_LOI_CUOI)


# ── Bậc thang model: hết hạn mức thì tụt xuống ──────────────────────────────
#
# ═══ VÌ SAO PHẢI TÁCH "HẾT HẠN MỨC" KHỎI "QUÁ TẢI" ═══
#
#   quá tải / 429 / 529   → máy chủ đang đông. Đợi 15–300 giây là qua.
#   hết hạn mức thuê bao  → cửa sổ dùng của model NÀY đã cạn, mở lại tính
#                           bằng GIỜ. Model bên dưới đang rảnh — đi sang đó.

#: ═══ DẤU MẠNH: CÂU CHỮ NGƯỜI ĐỌC ĐƯỢC, THẮNG CẢ MÃ LỖI ═══
#:
#: Lượt 0052 (26/08/2026): Claude Code báo cạn hạn mức **bằng chính mã 429**
#: (`"result":"You've reached your Fable 5 limit. Switch to another model…"`).
#: Bản đầu cho "nghẽn tạm thắng" → năm lần thử lại trên model đã cạn, mất 8
#: phút 15 giây. Nên câu chữ mô tả **thắng** mã trạng thái.
_DAU_HET_HAN_MUC = (
    "usage limit", "limit reached", "reached your limit", "quota",
    "resets at", "reset at", "will reset", "out of tokens", "insufficient",
    "exhausted", "upgrade to increase",
    # Nguyên văn bản Claude Code hiện tại (đo lượt 0052).
    "switch to another model", "manage usage credits",
)

#: `reached your Fable 5 limit`, `reach your weekly limit` — tên model nằm chen giữa.
_MAU_HET_HAN_MUC = re.compile(r"reach\w*\s+your\s+[^.]{0,60}limit", re.I)

#: Chữ chỉ là NGHẼN TẠM — chỉ xét ĐẾN khi không có dấu mạnh nào ở trên.
_DAU_NGHEN_TAM = ("overloaded", "529", "too many requests", "rate limit",
                  "rate_limit_error", "429")

#: Dấu YẾU: chữ "limit" đi cùng một trong mấy động từ — nghẽn tạm thắng nó.
_DONG_TU_HAN_MUC = ("reach", "reset", "upgrade", "exceed")

_MAU_GIO_MO_LAI = re.compile(
    r"reset[s]?(?:\s+\w+)?\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)


def _chu_cua_loi(loi: BaseException) -> str:
    """Cả câu lỗi lẫn stdout/stderr nguyên văn, gộp lại, chữ thường."""
    ra, err = getattr(loi, "chi_tiet", ("", ""))
    return (str(loi) + " " + str(ra) + " " + str(err)).lower()


def la_het_han_muc(loi: BaseException) -> bool:
    """Lỗi này là **cạn hạn mức của model**, hay chỉ là nghẽn tạm? (câu chữ > mã nghẽn > "limit"+động từ)"""
    chu = _chu_cua_loi(loi)
    if any(x in chu for x in _DAU_HET_HAN_MUC) or _MAU_HET_HAN_MUC.search(chu):
        return True
    if any(x in chu for x in _DAU_NGHEN_TAM):
        return False
    return "limit" in chu and any(x in chu for x in _DONG_TU_HAN_MUC)


#: Câu Claude Code nói khi model KHÔNG DÙNG ĐƯỢC trên máy/tài khoản này.
_DAU_MODEL_HONG = ("model not found", "model_not_found", "invalid model",
                   "unknown model", "unsupported model", "not available",
                   "does not have access", "no access to")

#: Model không dùng được thì khoá một ngày.
GIAY_KHOA_MODEL_HONG = 86400.0


def ly_do_tut_bac(loi: BaseException) -> str:
    """`"han_muc"` (cửa sổ dùng đã cạn), `"hong"` (model máy/tài khoản này không dùng được), hoặc `""` (không tụt)."""
    if la_het_han_muc(loi):
        return "han_muc"
    chu = _chu_cua_loi(loi)
    if any(x in chu for x in _DAU_NGHEN_TAM):
        return ""
    return "hong" if any(x in chu for x in _DAU_MODEL_HONG) else ""


def gio_mo_lai(loi: BaseException, bay_gio: float) -> float:
    """Mốc (epoch) nên thử lại model này, đọc từ chính câu Claude Code nói ("…reset at 3pm"); không đọc được thì
    `GIAY_KHOA_MAC_DINH`. Trần một ngày."""
    tim = _MAU_GIO_MO_LAI.search(_chu_cua_loi(loi))
    if not tim:
        return bay_gio + GIAY_KHOA_MAC_DINH
    try:
        gio = int(tim.group(1))
        phut = int(tim.group(2) or 0)
    except (TypeError, ValueError):
        return bay_gio + GIAY_KHOA_MAC_DINH
    chieu = (tim.group(3) or "").lower()
    if chieu == "pm" and gio < 12:
        gio += 12
    elif chieu == "am" and gio == 12:
        gio = 0
    if not (0 <= gio <= 23 and 0 <= phut <= 59):
        return bay_gio + GIAY_KHOA_MAC_DINH
    cuc_bo = time.localtime(bay_gio)
    moc = time.mktime((cuc_bo.tm_year, cuc_bo.tm_mon, cuc_bo.tm_mday,
                       gio, phut, 0, 0, 0, -1))
    if moc <= bay_gio:  # giờ ấy hôm nay đã qua → là giờ của ngày mai
        moc += 86400.0
    return min(moc, bay_gio + 86400.0)


def duong_han_muc(goc: str) -> str:
    return os.path.join(goc, THU_MUC_RONG, TEP_HAN_MUC)


def doc_han_muc(goc: str) -> dict:
    """Sổ khoá đã ghi. Tệp hỏng/thiếu thì coi như chưa khoá model nào."""
    try:
        with open(duong_han_muc(goc), encoding="utf-8") as t:
            so = json.load(t)
    except (OSError, ValueError):
        return {}
    if not isinstance(so, dict):
        return {}
    ra = {}
    for ma, den in so.items():
        try:
            ra[str(ma)] = float(den)
        except (TypeError, ValueError):
            continue
    return ra


def ghi_han_muc(goc: str, ma: str, den_luc: float) -> float:
    """Khoá `ma` tới mốc `den_luc`. Trả lại chính mốc ấy cho nơi gọi ghi nhật ký."""
    so = doc_han_muc(goc)
    so[str(ma)] = float(den_luc)
    try:
        os.makedirs(os.path.join(goc, THU_MUC_RONG), exist_ok=True)
        tam = "{0}.{1}.tmp".format(duong_han_muc(goc), os.getpid())
        with open(tam, "w", encoding="utf-8") as t:
            json.dump(so, t, ensure_ascii=False, indent=2)
        os.replace(tam, duong_han_muc(goc))
    except OSError:
        pass  # ghi sổ hỏng thì bậc thang vẫn chạy trong lượt này
    return float(den_luc)


def mo_hinh_dang_dung(goc: str, bay_gio: Optional[Callable[[], float]] = None
                      ) -> str:
    """Bậc cao nhất của thang mà hạn mức đã mở lại. Khoá hết thì trả bậc **sắp mở sớm nhất** và cứ thử — sổ khoá là
    phỏng đoán từ câu lỗi; thà tốn một lượt gọi hỏng còn hơn đứng im khi hạn mức thật ra đã mở."""
    gio = (bay_gio or time.time)()
    so = doc_han_muc(goc)
    thang = thang_mo_hinh(goc)
    for ma in thang:
        if so.get(ma, 0.0) <= gio:
            return ma
    return min(thang, key=lambda m: so.get(m, 0.0))


def _moc_mo_som_nhat(goc: str, bay_gio: float) -> float:
    so = doc_han_muc(goc)
    return min(max(so.get(m, 0.0), bay_gio) for m in thang_mo_hinh(goc))


def _ca_thang_dang_khoa(goc: str, bay_gio: float) -> bool:
    so = doc_han_muc(goc)
    return all(so.get(m, 0.0) > bay_gio for m in thang_mo_hinh(goc))


def _gio_ngan(moc: float) -> str:
    """`1755691200.0` → `"14:20"` — cho nhật ký, khách đọc được."""
    try:
        return time.strftime("%H:%M", time.localtime(moc))
    except (OSError, ValueError, OverflowError):
        return "?"


#: Cạn CẢ thang thì đợi tới giờ mở lại gần nhất, cộng dồn tối đa ngần này giây
#: cho MỘT lượt viết (cửa sổ hạn mức của gói Max là 5 tiếng) — rồi mới ném lỗi.
GIAY_CHO_CAN_THANG_TOI_DA = 6 * 3600.0
#: Ngủ từng khúc ngần này giây trong lúc đợi hạn mức, để nút Dừng nhạy.
NHIP_NGU_CAN_THANG = 10.0


def dung_goi_chat_max(goc: str, *,
                      on_log: Optional[Callable[[str], None]] = None,
                      kiem_dung: Optional[Callable[[], None]] = None,
                      viet: Optional[Callable[..., str]] = None,
                      so_lan: int = 1 + len(NHIP_THU_LAI),
                      ngu: Callable[[float], None] = time.sleep,
                      kiem_mang: Callable[[], bool] = mang_toi_anthropic,
                      bay_gio: Callable[[], float] = time.time,
                      cho_can_thang_toi_da: float = GIAY_CHO_CAN_THANG_TOI_DA,
                      viec: str = "",
                      ) -> Callable[..., str]:
    """Dựng hàm `goi_chat` đi **chỉ Claude Code**, hỏng thì thử lại.

    ═══ KHÔNG CÓ ĐƯỜNG LUI VỀ VÍ ═══

    Chủ dự án, 24/08/2026, sau khi thấy lượt 0020 và 0022 rẽ sang ví vì một
    cú thoát lỗi lẻ: *"lỗi thì phải retry đủ không thể gãy thế được nhá, đã
    nói máy này là claude max 20 thì cứ thế mà làm đừng cho nó đi nhầm"*.

    Nên: thử lại `so_lan` lần theo `NHIP_THU_LAI`; cạn cả thang model thì đợi
    hạn mức mở lại (tối đa `cho_can_thang_toi_da`, KHÔNG tính vào `so_lan`, có
    báo người); vẫn hỏng thì **ném lỗi nói rõ**.

    `viet`, `ngu`, `bay_gio` thay được để bài kiểm không cần Claude Code thật.
    """
    viet_that = viet or viet_bang_max

    def _di_het_thang(loi_nhac: str, anh: Any, them: Dict[str, Any]):
        """Đi từ bậc cao xuống bậc thấp, dừng ngay khi viết được.

        Trả `(chữ, None, False)` nếu viết được, `(None, lỗi, cạn_cả_thang)` nếu hết đường. Tụt bậc **không ngủ và
        không tiêu một lần thử lại nào**."""
        loi_cuoi: Optional[BaseException] = None
        vi_sao_cuoi = ""
        thang = thang_mo_hinh(goc)
        for _ in range(len(thang)):
            ma = mo_hinh_dang_dung(goc, bay_gio=bay_gio)
            t0 = time.time()
            try:
                # `mo_hinh` nơi gọi truyền vào là model của đường ví — đường
                # thuê bao cố ý KHÔNG dùng nó: xem `MO_HINH_TOT_NHAT`.
                chu = viet_that(loi_nhac, goc=goc, mo_hinh=ma,
                                kiem_dung=kiem_dung, anh=anh, **them)
                if on_log is not None:
                    on_log("  [Claude Max] {0} · {1:.0f} giây · {2} chữ.".format(ma, time.time() - t0, len(chu or "")))
                return chu, None, False
            except Exception as loi:  # noqa: BLE001 — tụt bậc, không rẽ ví
                if kiem_dung is not None:
                    kiem_dung()
                loi_cuoi = loi
                vi_sao = ly_do_tut_bac(loi)
                vi_sao_cuoi = vi_sao
                if not vi_sao:
                    return None, loi_cuoi, False
                den = ghi_han_muc(goc, ma, gio_mo_lai(loi, bay_gio())
                                  if vi_sao == "han_muc"
                                  else bay_gio() + GIAY_KHOA_MODEL_HONG)
                ke = mo_hinh_dang_dung(goc, bay_gio=bay_gio)
                if on_log is not None:
                    on_log("  {0} {1} — {2}.".format(
                        ma,
                        "hết hạn mức thuê bao (mở lại khoảng {0})".format(
                            _gio_ngan(den)) if vi_sao == "han_muc"
                        else "máy này không dùng được model ấy",
                        "đổi ngay sang " + ke if ke != ma
                        else "cả thang model đều tắc"))
                if ke == ma:
                    break
        can = vi_sao_cuoi == "han_muc" and _ca_thang_dang_khoa(goc, bay_gio())
        return None, loi_cuoi, can

    def _ngu_chia(giay: float) -> None:
        con = float(giay)
        while con > 0:
            buoc = min(NHIP_NGU_CAN_THANG, con)
            ngu(buoc)
            con -= buoc
            if kiem_dung is not None:
                kiem_dung()

    def goi(loi_nhac: str, mo_hinh: str = MO_HINH_TOT_NHAT,
            khoa: str = "", toi_da_token: int = 8192, anh: Any = "") -> str:
        them = {"gio_han": gio_han_theo_token(toi_da_token), "viec": str(khoa or viec or "")[:120],
                "effort": muc_suy_nghi(goc), "on_log": on_log}
        loi_cuoi: Optional[BaseException] = None
        lan = 0
        da_cho_can = 0.0
        while True:
            chu, loi, can = _di_het_thang(loi_nhac, anh, them)
            if chu is not None:
                _danh_dau_ok(goc, bay_gio())
                return chu
            loi_cuoi = loi or loi_cuoi
            if can and da_cho_can < cho_can_thang_toi_da:
                # ═══ CẠN CẢ THANG: ĐỢI HẠN MỨC MỞ LẠI, BÁO NGƯỜI, RỒI TỰ CHẠY TIẾP ═══
                #
                # Không rẽ ví (luật 24/08), không hạ xuống model yếu (luật "không
                # đăng sản phẩm kém"), và KHÔNG chết im lặng: gác tổng đọc
                # `trang-thai.json` để hiện ở "Việc của bạn".
                bg = bay_gio()
                den = _moc_mo_som_nhat(goc, bg)
                cho = max(NHIP_NGU_CAN_THANG, min(den - bg + 30.0, cho_can_thang_toi_da - da_cho_can))
                _bao_can_thang(goc, den, bg)
                if on_log is not None:
                    on_log("  Thuê bao Claude Max cạn hạn mức ở MỌI model ({0}) — đợi {1:.0f} phút (tới khoảng "
                           "{2}) rồi tự viết tiếp; KHÔNG chuyển sang ví.".format(
                               ", ".join(thang_mo_hinh(goc)), cho / 60.0, _gio_ngan(bg + cho)))
                _ngu_chia(cho)
                da_cho_can += cho
                continue
            con = lan < so_lan - 1
            cho = NHIP_THU_LAI[min(lan, len(NHIP_THU_LAI) - 1)]
            if on_log is not None:
                on_log("  Claude Code không viết được (lần {0}/{1}): {2}"
                       "{3}".format(lan + 1, so_lan, str(loi_cuoi)[:120],
                                    " — thử lại sau {0:.0f} giây, không "
                                    "chuyển sang ví.".format(cho)
                                    if con else "."))
                if loi_cuoi is not None:
                    on_log("    vì sao: " + chan_doan_loi(loi_cuoi, kiem_mang))
            if not con:
                break
            ngu(cho)
            if kiem_dung is not None:
                kiem_dung()
            lan += 1
        _bao_hong_cuoi(goc, loi_cuoi, bay_gio())
        raise RuntimeError(
            "Claude Code không viết được sau {0} lần thử ({1}). Máy này đặt "
            "viết chữ bằng thuê bao Claude nên tôi KHÔNG chuyển sang ví. "
            "Kiểm tra Claude Code còn đăng nhập không, hoặc đổi “Viết chữ bằng” "
            "sang “Ví ShopAPI” trong Cài đặt.".format(
                so_lan, str(loi_cuoi)[:160]))

    return goi


# ── Dòng lệnh: xem đường đang dùng / tải thuê bao / thử một lượt ────────────


def _main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError, OSError):
        pass
    p = argparse.ArgumentParser(prog="python -m core.viet_max",
                                description="Đường viết chữ bằng thuê bao Claude Max của máy")
    p.add_argument("--goc", default=GOC_TOOL)
    p.add_argument("--so-dung", action="store_true", help="tải thuê bao trong --gio giờ qua")
    p.add_argument("--gio", type=float, default=24.0)
    p.add_argument("--thu", default="", help="viết thử MỘT lượt thật với lời nhắc này (tốn hạn mức thuê bao)")
    a = p.parse_args(argv)
    duong, ly_do = duong_viet_chu(a.goc)
    print("Đường viết chữ: {0} — {1}".format({"max": "THUÊ BAO CLAUDE MAX", "vi": "ví ShopAPI",
                                               "loi": "LỖI CÀI ĐẶT"}.get(duong, duong), ly_do))
    print("Claude Code: {0}".format(co_claude_code() or "KHÔNG THẤY"))
    print("Thang model: {0} · đang dùng {1} · suy nghĩ {2} · tối đa {3} tiến trình (đang giữ {4})".format(
        " → ".join(thang_mo_hinh(a.goc)), mo_hinh_dang_dung(a.goc), muc_suy_nghi(a.goc), so_song_song(a.goc),
        so_suat_dang_giu(a.goc)))
    tt = doc_trang_thai(a.goc)
    if any(k in tt for k in ("can_thang", "chua_dang_nhap", "hong")):
        print("Sự cố đang treo: " + json.dumps({k: tt[k] for k in ("can_thang", "chua_dang_nhap", "hong")
                                               if k in tt}, ensure_ascii=False))
    if a.so_dung:
        tom = tom_tat_so_dung(a.goc, a.gio)
        print("{0:g} giờ qua: {1} lượt ({2} hỏng), {3:.0f} phút chạy, {4:,} token vào / {5:,} token ra".format(
            a.gio, tom["luot"], tom["hong"], tom["giay"] / 60.0, tom["token_vao"], tom["token_ra"]))
        print("  theo model: " + ", ".join("{0} {1}".format(k, v) for k, v in sorted(
            tom["theo_model"].items(), key=lambda x: -x[1])))
        print("  theo việc:  " + ", ".join("{0} {1}".format(k, v) for k, v in sorted(
            tom["theo_viec"].items(), key=lambda x: -x[1])[:15]))
    if a.thu:
        if duong != "max":
            print("Không viết thử: máy không đi đường thuê bao.")
            return 1
        print(goi_tin_nhan_max([{"role": "user", "content": a.thu}], goc=a.goc, on_log=print))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
