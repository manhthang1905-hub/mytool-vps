"""**Kho lời thoại** — lời thoại video đối thủ lấy bằng TRÌNH DUYỆT KÊNH, cất
lại cho cả nhóm dùng chung.

═══ VÌ SAO PHẢI CÓ KHO NÀY (ĐÊM 22/09/2026) ═══

Khâu đầu của sản xuất (`kich-ban`, xem `core/auto_khau.py` ~2100) cần LỜI THOẠI
của video đối thủ làm nguyên liệu. Nó lấy qua `core.script_video.lay_script`,
và đường ấy đi bằng `yt-dlp` / `youtube-transcript-api` — cả hai **bị YouTube
chặn theo địa chỉ mạng của VPS này**: `IpBlocked`, nguyên văn *"You are doing
requests from an IP belonging to a cloud provider"*. Đêm 22/09/2026 cả ba kênh
chết ở đúng khâu này. Đã thử cookie, đổi `player_client`, nâng `yt-dlp`, cắm
proxy (`core/mang_youtube.py`): không cứu được đường tải tiếng, và mỗi lượt thử
lại làm cái chặn nặng thêm — nó nặng dần **theo số lượt hỏi**.

NHƯNG từ ĐÚNG địa chỉ mạng ấy, **trình duyệt kênh** (Chromium chống vân tay,
`C:\\Users\\...\\TL\\<MÃ>\\<MÃ>.exe`) vào YouTube bình thường: mỗi ngày
`vm/agent.py` chạy một PHIÊN cho từng kênh, mở Studio rồi mở trang chủ, và
extension trong `vm/tien-ich/<MÃ>/` cào số liệu gửi về trạm. Đêm 21/09/2026
chạy trọn 4 phiên không lỗi.

Nên lời thoại không lấy bằng cách hỏi YouTube nữa: **lấy bằng mắt của phiên
trình duyệt** (bảng "Show transcript" trên trang `watch`), rồi cất vào kho này.
Hai dòng chảy tách hẳn nhau về thời gian:

* ~07:30 — phiên trình duyệt chạy, ĐỔ VÀO kho (một lượt ~8 video, đi như người
  xem: chờ 4–8 giây mỗi video).
* 02:00 — sản xuất (`tu_chay.py --tat-ca`, không cửa sổ, KHÔNG có trình duyệt) chỉ
  ĐỌC kho. Không gọi mạng, không tốn một lượt hỏi nào.

═══ KHO DÙNG CHUNG CẢ NHÓM, KHÔNG PHẢI RIÊNG TỪNG KÊNH ═══

4 kênh trong một nhóm đánh cùng một pool đối thủ (xem `core/nhom_kenh.py`), nên
một lượt lấy phục vụ được cả 4. Kho của nhóm nằm CẠNH bảng chéo kênh, đúng chỗ
`nhom_kenh.duong_thu_muc_nhom` đã đặt:

    CHANNEL/_NHOM/<nhóm>/loi-thoai/<video_id>.json

Kênh KHÔNG thuộc nhóm nào (`kenh.yaml` không khai `nhom`) thì cất trong thư mục
nghiên cứu của chính nó — cùng chỗ với mọi dữ liệu nghiên cứu khác của kênh:

    CHANNEL/<MÃ>/nghien-cuu/loi-thoai/<video_id>.json

═══ BẢN GHI RỖNG CÓ CỜ `khong_co` — VÌ "KHÔNG CÓ" CŨNG LÀ MỘT CÂU TRẢ LỜI ═══

Video tắt phụ đề thì mở trang `watch` bao nhiêu lần cũng không có bảng transcript
nào. Không ghi lại việc ấy thì phiên nào cũng hỏi lại đúng những video ấy, và
mỗi lượt hỏi là 4–8 giây của một phiên trình duyệt thật. Nên "không có" được
cất thành một bản ghi `{"khong_co": true, "text": ""}`:

* `co_ban_ghi()` trả `True` → `/loi-thoai/can-lay` thôi hỏi video ấy;
* `co_loi_thoai()` trả `False` → `lay_script` KHÔNG trả về từ kho, mà vẫn đi
  các đường mạng cũ như chưa có gì (có ngày đường `tu-nghe` vẫn ra chữ).

Hai câu hỏi khác nhau, hai hàm khác nhau — gộp làm một là hoặc hỏi lại mãi,
hoặc trả về một lời thoại rỗng cho khâu kịch bản.

Module thuần: không mạng, không Qt. Ghi nguyên tử (`.tam` + `os.replace`) theo
đúng nết `nhom_kenh.ghi_bang_nhom` / `dong_bo_kenh` ở cạnh — một lượt ghi bị
ngắt giữa chừng (máy ảo tắt, ổ đĩa bận) không bao giờ để lại tệp JSON dở dang
mà 02:00 hôm sau đọc vào.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

__all__ = [
    "THU_MUC", "NGUON_TRINH_DUYET", "MAX_TEXT", "ma_hop_le",
    "thu_muc_kho", "duong_tep", "doc", "ghi",
    "co_ban_ghi", "co_loi_thoai", "ma_da_co", "ma_co_loi_thoai", "dem",
]

#: Tên thư mục kho, dùng cho CẢ hai chỗ (nhóm và kênh lẻ) — một tên để `grep`
#: ra hết, và để người mở thư mục bằng tay nhận ra ngay nó là cùng một thứ.
THU_MUC = "loi-thoai"

#: Giá trị `nguon` cho bản ghi do extension trên trình duyệt kênh gửi về.
NGUON_TRINH_DUYET = "trinh-duyet"

#: Cắt lời thoại còn ngần này ký tự trước khi ghi — khớp `script_video.MAX_SCRIPT`.
#: Một bản gỡ băng dài hơn thế thì phần thừa không mang thêm thông tin cho khâu
#: kịch bản, mà lại là một tệp JSON hàng trăm KB nhân với hàng trăm video.
MAX_TEXT = 30000

#: Mã video YouTube: ĐÚNG 11 ký tự base64-url. Kiểm ở đây vì mã đi vào TÊN TỆP
#: — một mã chứa `..` hay `/` là một đường trèo ra khỏi kho (gói mạng của
#: extension không phải nguồn đáng tin, xem `chi_so_ytb/tram.an_toan`).
_MA_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")


def ma_hop_le(video_id) -> bool:
    """Mã này có đúng dạng mã video YouTube không (11 ký tự `[A-Za-z0-9_-]`)."""
    return bool(_MA_VIDEO.match(str(video_id or "")))


def thu_muc_kho(goc: str, ma_kenh: str) -> str:
    """Kho lời thoại HIỆU LỰC của một kênh.

    Kênh có khai `nhom` trong `kenh.yaml` → kho CHUNG của nhóm
    (`CHANNEL/_NHOM/<nhóm>/loi-thoai/`, cạnh `bang-nhom.csv` mà
    `nhom_kenh.ghi_bang_nhom` ghi). Không khai → kho riêng
    (`CHANNEL/<MÃ>/nghien-cuu/loi-thoai/`).

    Đọc `kenh.yaml` hỏng (thiếu tệp, YAML vỡ) thì rơi về kho riêng của kênh —
    thà một kho hẹp hơn còn dùng được, hơn là ném lỗi lên giữa khâu kịch bản.
    """
    # Nhập muộn: `nhom_kenh` kéo theo `da_lam`/`trang_chu`/`doi_thu_kenh`, còn
    # module này bị `script_video` nhập — nhập sớm là một vòng nhập chỉ chờ
    # ngày ai đó thêm một dòng import nữa là khép lại.
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    nhom = ""
    try:
        from . import nhom_kenh  # noqa: PLC0415

        nhom = nhom_kenh.nhom_cua_kenh(goc, ma_kenh)
    except Exception:  # noqa: BLE001 — không đọc được nhóm thì dùng kho riêng
        nhom = ""
    if nhom:
        from . import nhom_kenh  # noqa: PLC0415

        return os.path.join(nhom_kenh.duong_thu_muc_nhom(goc, nhom), THU_MUC)
    return os.path.join(thu_muc_nghien_cuu(goc, ma_kenh), THU_MUC)


def duong_tep(goc: str, ma_kenh: str, video_id: str) -> str:
    """Đường tệp kho của một video. Mã sai dạng → `""` (không bao giờ dựng
    đường dẫn từ chuỗi chưa kiểm)."""
    if not ma_hop_le(video_id):
        return ""
    return os.path.join(thu_muc_kho(goc, ma_kenh), str(video_id) + ".json")


def doc(goc: str, ma_kenh: str, video_id: str) -> Optional[Dict[str, object]]:
    """Bản ghi kho của một video, `None` nếu chưa có / đọc không ra.

    Trả về CẢ bản ghi `khong_co` (lời thoại rỗng) — nơi gọi tự phân biệt bằng
    khoá `khong_co`/`text`, xem `co_ban_ghi` và `co_loi_thoai`.
    """
    duong = duong_tep(goc, ma_kenh, video_id)
    if not duong:
        return None
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return None
    return du if isinstance(du, dict) else None


def ghi(goc: str, ma_kenh: str, video_id: str, *, text: str = "",
        tieu_de: str = "", ngon_ngu: str = "", dai_giay: int = 0,
        nguon: str = NGUON_TRINH_DUYET, khong_co: bool = False,
        luc: str = "") -> str:
    """Cất một bản ghi vào kho. Trả về đường tệp đã ghi, `""` nếu mã sai dạng.

    Ghi NGUYÊN TỬ: tệp `.tam` rồi `os.replace`. Lượt ghi đi từ một gói mạng của
    máy ảo, và bên nhận (02:00 sáng hôm sau) đọc thẳng tệp này — một tệp JSON
    cắt dở giữa chừng là một khâu kịch bản chết mà không ai hiểu vì sao.

    `khong_co=True` (hoặc `text` rỗng) ghi một bản ghi RỖNG có cờ: nghĩa là
    "video này đã hỏi rồi, nó KHÔNG có bảng phụ đề" — để phiên sau thôi hỏi lại.
    """
    duong = duong_tep(goc, ma_kenh, video_id)
    if not duong:
        return ""
    # Chỉ có khoảng trắng cũng là RỖNG. Bản phụ đề của một video nhạc (hay một
    # lượt hút nửa vời) về đúng như thế, và cất nó thành "có lời thoại" nghĩa là
    # khâu kịch bản nhận một tư liệu trắng rồi đổ lỗi cho video.
    chu = str(text or "")[:MAX_TEXT]
    if not chu.strip():
        chu = ""
    ban_ghi = {
        "video_id": str(video_id),
        "tieu_de": " ".join(str(tieu_de or "").split())[:300],
        "ngon_ngu": str(ngon_ngu or "")[:20],
        "text": chu,
        "so_ky_tu": len(chu),
        "dai_giay": max(0, int(dai_giay or 0)),
        "nguon": str(nguon or NGUON_TRINH_DUYET)[:40],
        "khong_co": bool(khong_co or not chu),
        "luc": str(luc or datetime.now().isoformat(timespec="seconds")),
        "kenh_lay": str(ma_kenh or ""),
    }
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(ban_ghi, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)
    return duong


def co_ban_ghi(goc: str, ma_kenh: str, video_id: str) -> bool:
    """Video này ĐÃ HỎI chưa (kể cả lượt hỏi ra "không có phụ đề")?

    Đây là câu hỏi của `/loi-thoai/can-lay`: đã hỏi rồi thì thôi, đừng tiêu
    thêm 4–8 giây của một phiên trình duyệt thật cho cùng một video.
    """
    duong = duong_tep(goc, ma_kenh, video_id)
    return bool(duong) and os.path.isfile(duong)


def co_loi_thoai(goc: str, ma_kenh: str, video_id: str) -> bool:
    """Kho có lời thoại THẬT (chữ không rỗng) của video này không?

    Đây là câu hỏi của `script_video.lay_script` và của vòng xếp hạng nguồn
    (`tu_chay._chon_nguon`) — bản ghi `khong_co` KHÔNG tính, vì nó không viết
    được một dòng kịch bản nào.
    """
    ban = doc(goc, ma_kenh, video_id)
    return bool(ban) and not ban.get("khong_co") and bool(str(ban.get("text") or ""))


def _ma_trong_kho(goc: str, ma_kenh: str) -> List[str]:
    try:
        ten_tep = os.listdir(thu_muc_kho(goc, ma_kenh))
    except OSError:
        return []          # chưa có kho là trạng thái bình thường của kênh mới
    return sorted(t[:-5] for t in ten_tep
                  if t.endswith(".json") and ma_hop_le(t[:-5]))


def ma_da_co(goc: str, ma_kenh: str) -> Set[str]:
    """Mọi mã video ĐÃ HỎI trong kho của kênh (kể cả bản ghi `khong_co`)."""
    return set(_ma_trong_kho(goc, ma_kenh))


def ma_co_loi_thoai(goc: str, ma_kenh: str) -> Set[str]:
    """Mọi mã video CÓ lời thoại thật trong kho.

    Đọc từng tệp: kho một nhóm cỡ vài trăm tệp JSON, và vòng chọn nguồn chỉ
    chạy một lần mỗi đêm mỗi kênh — không đáng dựng thêm một tệp mục lục để
    rồi phải lo nó lệch với thư mục.
    """
    return {ma for ma in _ma_trong_kho(goc, ma_kenh)
            if co_loi_thoai(goc, ma_kenh, ma)}


def dem(goc: str, ma_kenh: str, *, hom_nay: str = "") -> Dict[str, int]:
    """Đếm kho của một kênh — cho sổ ngày (`workspace/tu-chay/<ngày>.md`).

    Trả `{"co": số video có lời thoại, "khong_co": số video đã hỏi mà không có,
    "hom_nay": số bản ghi lấy được TRONG NGÀY `hom_nay` (dạng `2026-09-22`)}`.

    Chủ dự án đọc sổ ngày mỗi sáng, và hai con số ấy là thứ nói được ngay sáng
    hôm sau rằng phiên trình duyệt đêm qua có đổ được gì vào kho hay không —
    chứ không phải chờ tới lúc khâu kịch bản chết mới biết.
    """
    hom_nay = str(hom_nay or datetime.now().strftime("%Y-%m-%d"))
    ket = {"co": 0, "khong_co": 0, "hom_nay": 0}
    for ma in _ma_trong_kho(goc, ma_kenh):
        ban = doc(goc, ma_kenh, ma) or {}
        co_chu = not ban.get("khong_co") and bool(str(ban.get("text") or ""))
        ket["co" if co_chu else "khong_co"] += 1
        if co_chu and str(ban.get("luc") or "").startswith(hom_nay):
            ket["hom_nay"] += 1
    return ket
