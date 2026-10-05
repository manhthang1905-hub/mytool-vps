"""Báo động RA NGOÀI máy — Telegram / webhook, mặc định TẮT, có chống spam.

## Vì sao KHÔNG mở rộng `core.alerts`

`core.alerts` (ví sắp cạn) cố ý THUẦN TUÝ — không gọi mạng, không đụng giao
diện — xem đúng câu đó ở docstring `assess_balance`: *"Thuần tuý — không gọi
mạng, không đụng giao diện — nên test được bằng số dựng tay."* Nhét việc gọi
Telegram/webhook (I/O mạng, có thể treo, có thể lộ token) thẳng vào đó là phá
hợp đồng ấy — mọi test hiện có của `alerts.py` (và test mới của module này)
sẽ phải phân biệt "tính toán thuần" với "có gọi mạng", dễ lẫn.

Nên: `core.bao_dong` là module RIÊNG, chỉ lo một việc — bắn một dòng chữ RA
NGOÀI máy qua một hoặc nhiều "đường dây" đã cấu hình. `core.alerts` (hoặc bất
kỳ chỗ nào khác trong tool phát hiện sự cố) gọi sang đây qua hàm công khai
:func:`bao_dong`; xem thêm :func:`core.alerts.canh_bao_ra_ngoai` — cầu nối mỏng
giữa hai module, KHÔNG đụng vào tính thuần tuý của `assess_balance`.

## Cấu hình: `bao-dong.json` — KHÔNG nằm trong `config.json`/`secrets.json`

Ba lý do tách riêng:

1. `config.json` là HỢP ĐỒNG CỐ ĐỊNH (xem đầu `core/config.py`) — thêm trường
   vào đó là thêm nghĩa vụ tương thích ngược cho một file vốn không liên quan
   gì tới việc báo động.
2. Token bot Telegram / URL webhook (có thể mang key trong query string) là bí
   mật, nhưng `secrets.json` hiện chỉ chứa đúng ba thứ (`api_key`,
   `refresh_token`, `account_email`) mà `core.config` biết cách đọc/ghi/di
   trú — nhét thêm vào đó buộc phải sửa `Config`/`to_secrets`, lan sang một
   module không liên quan.
3. Quan trọng nhất: **THIẾU FILE = TẮT HẲN, không lỗi.** Một file cấu hình
   riêng, độc lập, rỗng-là-tắt, giúp việc "chưa cấu hình thì im lặng" trở
   thành hành vi TỰ NHIÊN (không tìm thấy file) thay vì phải nhớ thêm một cờ
   `bat_bao_dong` nằm lẫn trong file khác.

Định dạng (mọi trường đều tuỳ chọn — thiếu `telegram` VÀ `webhook` thì coi như
chưa cấu hình gì, `bao_dong()` không làm gì cả):

```json
{
  "enabled": true,
  "cooldown_giay": 3600,
  "cooldown_khan_giay": 86400,
  "cooldown_nhac_giay": 3600,
  "telegram": {
    "bot_token": "123456789:AAExampleTokenKhongPhaiThat",
    "chat_id": "987654321"
  },
  "webhook": {
    "url": "https://example.com/hoi-chuong-bao-dong",
    "headers": { "Authorization": "Bearer vi-du-khong-phai-that" }
  }
}
```

* `enabled`: công tắc tắt nhanh không cần xoá token (mặc định `true` NẾU file
  tồn tại — file không tồn tại thì mặc định coi như tắt, xem trên).
* `cooldown_giay`: khoảng lặng tối thiểu giữa hai lần bắn CÙNG `loai` sự cố ở
  mức mặc định (`"thuong"`). Mặc định :data:`COOLDOWN_MAC_DINH_GIAY` (1 giờ).
* `cooldown_khan_giay`: khoảng lặng cho mức `"khan"` — mặc định
  :data:`COOLDOWN_KHAN_MAC_DINH_GIAY` (24 giờ). Xem mục "Ba mức" bên dưới.
* `cooldown_nhac_giay`: khoảng lặng cho mức `"nhac"` — mặc định cũng 1 giờ,
  chỉ để tránh xếp cùng một tin vào hàng đợi bản tin quá nhiều lần một ngày.
* `telegram`: cần cả `bot_token` lẫn `chat_id` mới tính là đã cấu hình. Lấy
  `chat_id` bằng cách nhắn bot rồi gọi `getUpdates`, hoặc dùng @userinfobot.
* `webhook`: cần `url`; `headers` tuỳ chọn (vd thêm khoá xác thực riêng của
  dịch vụ nhận — Slack incoming webhook, n8n, Discord (qua adapter), ...).

Bật CẢ HAI đường cùng lúc thì `bao_dong()` bắn cả hai — không đường nào loại
trừ đường nào; một đường lỗi không chặn đường kia (xem :func:`bao_dong`).

## Vì sao `urllib.request` chứ không phải `requests`

`core/*.py` khác gọi mạng qua `urllib.request` thuần chuẩn (xem
`core/mang_an_toan.py`, `core/anh_doi_thu.py`...) — không phải vì thiếu
`requests` trong `requirements.txt`, mà để khỏi kéo thêm phụ thuộc cho một
việc gọn (POST JSON, không cần session/retry phức tạp). Theo đúng nếp đó.

## Chống spam: vì sao khoá theo (`loai`, `kenh`), không khoá toàn cục

Một sự cố (vd trạm chết) có thể được PHÁT HIỆN LẠI mỗi nhịp kiểm tra trong khi
một sự cố KHÁC (vd ví cạn) xảy ra đúng lúc đó — khoá TOÀN CỤC sẽ làm sự cố thứ
hai bị nuốt mất chỉ vì tới sau sự cố thứ nhất chưa đầy 1 giờ. Khoá theo `loai`
(một chuỗi tự đặt, vd `"tram_chet"`, `"vi_can"`, `"dia_day"`) thì mỗi loại sự
cố có đồng hồ chống spam RIÊNG — đúng tinh thần "công cụ chạy nhiều năm không
ai ngồi xem": báo đủ để không bỏ sót, không báo dồn tới mức bị tắt thông báo.

Từ bản này, khoá còn có thêm chiều thứ hai TUỲ CHỌN: `kenh` (mã kênh YouTube,
vd `"TL1"`). Kênh A hết tiền và kênh B hết tiền là HAI sự cố độc lập của hai
chủ thể khác nhau — nếu chỉ khoá theo `loai="vi_can"` thì báo xong cho kênh A
sẽ che mất báo động của kênh B suốt cả giờ tiếp theo. Không truyền `kenh` thì
khoá hoạt động y hệt bản cũ (chỉ theo `loai`) — mọi lời gọi hiện có
(`qa_truoc_dang`, `alerts.canh_bao_ra_ngoai`) không cần sửa gì vẫn đúng.

## Chống lặp SỐNG TRÊN ĐĨA (`workspace/bao-dong-da-gui.json`), không còn RAM

Bản trước đây nhớ mốc "lần bắn gần nhất" trong một `dict` cấp module
(`_LAN_BAN_CUOI`) — sống và chết theo TIẾN TRÌNH PYTHON. Vô dụng trong thực tế
vận hành: `tu_chay.py --tat-ca` chạy lại mỗi lần lịch Windows kích hoạt (mỗi
ngày), `gac_tong.py` (kế hoạch V3) dự kiến chạy lại mỗi 15 phút bằng
`schtasks` — mỗi lần đều là một TIẾN TRÌNH PYTHON MỚI, RAM rỗng, "khoảng lặng"
coi như chưa từng tồn tại. Kết quả thật: báo động dội lại từ đầu mỗi lần tiến
trình mới khởi động, đúng thứ mà cơ chế chống spam sinh ra để tránh.

Nên bộ nhớ chống lặp chuyển hẳn xuống file `workspace/bao-dong-da-gui.json`
(hàm :func:`_doc_kho`/:func:`_ghi_kho`), đọc lại mỗi lần gọi, ghi lại ngay sau
mỗi lần cập nhật. Ghi NGUYÊN TỬ: viết ra một file `.tmp` cạnh rồi `os.replace`
sang tên thật — `os.replace` trên cùng một ổ đĩa là thao tác nguyên tử của hệ
điều hành, nên một tiến trình khác đọc đúng lúc đó luôn thấy file CŨ nguyên
vẹn hoặc file MỚI nguyên vẹn, không bao giờ thấy nửa file JSON dở dang (khác
hẳn việc ghi đè trực tiếp, có thể để lại file rỗng/half-written nếu tiến trình
bị giết giữa chừng — đúng kiểu sự cố mà máy chạy nhiều năm không người trông
sẽ gặp).

Khoá `threading.Lock()` (`_KHOA`) chỉ bảo vệ được các luồng CÙNG một tiến
trình; giữa hai tiến trình khác nhau gọi gần như đồng thời, "ai ghi sau thắng"
— chấp nhận được vì báo động là chuyện thưa (vài phút một lần là dày), không
phải chỗ cần khoá file mức hệ điều hành.

## Ba mức báo động: `thuong` (mặc định) / `khan` / `nhac`

| Mức | Khi nào dùng | Hành vi |
|---|---|---|
| `thuong` | mặc định, y hệt bản cũ | bắn ngay (nếu qua khoảng lặng `cooldown_giay`) |
| `khan` | việc CON NGƯỜI phải làm, càng để lâu càng hại (ví cạn, license hết hạn, kênh bị đăng xuất...) | bắn NGAY lần đầu, sau đó nhắc lại mỗi `cooldown_khan_giay` (mặc định 24 giờ) MIỄN LÀ nơi gọi còn tiếp tục gọi (tức sự cố còn tồn tại) — dùng :func:`bao_dong_khan` |
| `nhac` | thông tin đáng biết nhưng KHÔNG khẩn (vd "hôm nay kênh X không có video mới") | KHÔNG bắn ngay — xếp vào hàng đợi `workspace/bao-dong-da-gui.json` (khoá `nhac_cho_ban_tin`) để module bản tin ngày (kế hoạch V4: "Bản tin 08:00") gom lại thành MỘT tin/ngày; lấy ra bằng :func:`lay_va_xoa_cac_tin_nhac` |

Mức `khan` không cần một cờ "đã xử lý xong chưa" riêng: chừng nào nơi gọi còn
phát hiện sự cố và còn gọi `bao_dong_khan`, chừng đó vẫn còn nhắc (mỗi 24h);
sự cố tự hết thì nơi gọi tự ngừng gọi, nhắc cũng tự dừng theo — không cần sổ
sách "đã giải quyết" riêng.

## Khuôn tin bắt buộc cho mức `khan`: Chuyện gì — Bạn cần làm gì — Nếu không làm thì sao

Người đọc tin là chủ kênh YouTube, KHÔNG PHẢI lập trình viên — một tin báo lỗi
kiểu kỹ thuật ("HTTP 402", "invalid_grant", "ENOSPC") vô nghĩa với họ và chỉ
gây hoang mang. :func:`khuon_tin_khan` (và lối tắt :func:`bao_dong_khan`) ép
mọi tin mức `khan` vào đúng 3 dòng, luôn theo thứ tự:

1. Chuyện gì — sự thật, không thuật ngữ.
2. Bạn cần làm gì — MỘT hành động cụ thể, làm được ngay.
3. Nếu không làm thì sao — hậu quả thật nếu bỏ qua (mất video, mất kênh, máy
   ngừng chạy...), không dọa suông.

Mọi module sau này phát ra báo động khẩn (kế hoạch gia cố: `gac_tong.py` V3,
cảnh báo ví V8, cảnh báo OAuth V10, license Windows V5...) PHẢI đi qua hàm này
thay vì tự ghép chuỗi, để chủ dự án luôn đọc được tin theo đúng MỘT khuôn dù
tin đến từ việc nào.

## Gửi thất bại KHÔNG được làm chết tiến trình gọi

Mất mạng, bot bị chặn, sai token... đều là chuyện bình thường của một máy
chạy một mình nhiều năm. `bao_dong()` (và `bao_dong_khan()`) không bao giờ
ném lỗi — gặp lỗi khi gửi thì:

1. Ghi 1 dòng vào `workspace/bao-dong-loi.log` (xem :func:`_ghi_that_bai`) —
   để có gỡ tay được thì có log đọc.
2. Ghi "gửi thất bại lần cuối lúc..." vào `trang_thai` trong
   `workspace/bao-dong-da-gui.json` — để một giao diện Tổng quan (việc sau,
   CHƯA làm ở bản này) đọc ra và hiện cho chủ dự án thấy MÀ KHÔNG PHẢI đi lục
   log thô. Đọc bằng :func:`doc_trang_thai_gui`.
3. Trả `False` — không ném `Exception`.

## Kiểm IPv6 tới `api.telegram.org`: `python -m core.bao_dong --kiem`

Một số VPS (xem `CLAUDE.local.md`, mục "Mạng chỉ có IPv6") chỉ có địa chỉ
IPv6 — nếu `api.telegram.org` không có bản ghi DNS AAAA (IPv6), máy đó KHÔNG
BAO GIỜ gửi được Telegram trực tiếp, và triệu chứng duy nhất là "gửi thất bại"
lặp lại mãi mà không rõ vì sao. Lệnh:

```
python -m core.bao_dong --kiem
```

CHỈ phân giải DNS (không gửi tin, không mở kết nối HTTP nào tới Telegram), in
ra máy này thấy bản ghi AAAA hay không, và nếu KHÔNG thấy thì in kèm hướng xử
lý (dùng đường `webhook` đã có sẵn trỏ tới một dịch vụ trung chuyển có IPv4,
hoặc bật NAT64/DNS64 phía nhà cung cấp) — chỉ IN hướng dẫn, không tự cài gì.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import mang_an_toan

__all__ = [
    "BAO_DONG_FILENAME",
    "DA_GUI_FILENAME",
    "LOI_LOG_FILENAME",
    "COOLDOWN_MAC_DINH_GIAY",
    "COOLDOWN_KHAN_MAC_DINH_GIAY",
    "MUC_THUONG",
    "MUC_KHAN",
    "MUC_NHAC",
    "bao_dong_path_for",
    "doc_cau_hinh_bao_dong",
    "bao_dong",
    "bao_dong_khan",
    "khuon_tin_khan",
    "quen_lich_su_chong_spam",
    "doc_trang_thai_gui",
    "lay_va_xoa_cac_tin_nhac",
]

#: Tên file cấu hình — nằm cạnh `config.json`/`secrets.json` nhưng KHÔNG phải
#: một trong hai file đó (xem lý do ở đầu module).
BAO_DONG_FILENAME = "bao-dong.json"

#: Kho chống lặp — nằm trong `workspace/` vì đây là dữ liệu VẬN HÀNH tool tự
#: sinh ra (như mọi thứ khác trong `workspace/`), không phải cấu hình do
#: người dùng điền tay như `bao-dong.json`.
DA_GUI_FILENAME = "bao-dong-da-gui.json"

#: Nhật ký gửi thất bại — một dòng mỗi lần gửi lỗi, xem :func:`_ghi_that_bai`.
LOI_LOG_FILENAME = "bao-dong-loi.log"

#: Mức mặc định — hành vi y hệt bản trước khi có "khan"/"nhac".
MUC_THUONG = "thuong"
#: Mức khẩn — gửi ngay, nhắc lại đều đặn, khuôn tin 3 dòng bắt buộc.
MUC_KHAN = "khan"
#: Mức nhắc — không gửi ngay, gộp vào hàng đợi cho bản tin ngày.
MUC_NHAC = "nhac"

#: Khoảng lặng mặc định giữa hai lần bắn CÙNG một `loai` (mức `thuong`/`nhac`).
#: 1 giờ: đủ ngắn để chủ dự án biết sự cố còn đang diễn ra (không phải chỉ một
#: lần rồi im), đủ dài để một vòng lặp kiểm tra chạy mỗi vài phút không dội
#: bom hộp thoại Telegram — chạy nhiều năm mà báo dồn dập thì việc đầu tiên
#: chủ dự án làm là tắt hẳn thông báo, mất tác dụng của cả hệ thống.
COOLDOWN_MAC_DINH_GIAY = 3600.0
#: Khoảng lặng mặc định cho mức `khan`: 24 giờ — đủ để không dội bom, nhưng
#: vẫn nhắc lại MỖI NGÀY chừng nào sự cố (vd ví vẫn cạn) còn tồn tại.
COOLDOWN_KHAN_MAC_DINH_GIAY = 86400.0

#: Thư mục gốc mặc định (MyTool/) — dùng khi nơi gọi không tự truyền `goc`,
#: để hàm công khai :func:`bao_dong` gọi được với đúng 3 tham số như mô tả.
_GOC_MAC_DINH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Bảo vệ đọc-sửa-ghi kho chống lặp giữa các LUỒNG cùng một tiến trình. Giữa
#: các TIẾN TRÌNH khác nhau, an toàn dựa vào ghi nguyên tử (`os.replace`) —
#: xem mục "Chống lặp SỐNG TRÊN ĐĨA" ở đầu file.
_KHOA = threading.Lock()


def bao_dong_path_for(goc: str) -> str:
    """`<goc>` (thư mục chứa `config.json`) → đường dẫn `bao-dong.json`.

    Cùng khuôn với :func:`core.secrets.secrets_path_for` — nhận thư mục gốc
    thay vì tự đoán, vì `core/*.py` khác cũng luôn nhận `goc`/`base_dir` từ
    nơi gọi (GUI, `tu_chay.py`...) chứ không tự suy ra vị trí cài đặt.
    """
    return os.path.join(goc, BAO_DONG_FILENAME)


def doc_cau_hinh_bao_dong(goc: str) -> Optional[Dict[str, Any]]:
    """Đọc `bao-dong.json`. Không có file / file hỏng → `None` (im lặng)."""
    try:
        with open(bao_dong_path_for(goc), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return None
    return du_lieu if isinstance(du_lieu, dict) else None


def _kenh_telegram(cfg: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    tg = cfg.get("telegram")
    if not isinstance(tg, dict):
        return None
    token = str(tg.get("bot_token") or "").strip()
    chat_id = str(tg.get("chat_id") or "").strip()
    if not token or not chat_id:
        return None
    return token, chat_id


def _kenh_webhook(cfg: Dict[str, Any]) -> Optional[Tuple[str, Optional[Dict[str, str]]]]:
    wh = cfg.get("webhook")
    if not isinstance(wh, dict):
        return None
    url = str(wh.get("url") or "").strip()
    if not url:
        return None
    headers = wh.get("headers")
    return url, (dict(headers) if isinstance(headers, dict) else None)


def _http_post(
    url: str,
    payload: Dict[str, Any],
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10.0,
) -> None:
    """Điểm DUY NHẤT chạm mạng của module này.

    Tách riêng thành hàm nhỏ để test monkeypatch ĐÚNG một chỗ này — không ai
    được gọi mạng thật trong bộ test (xem `MyTool/tests/test_bao_dong.py`).
    """
    tieu_de = {}
    if headers:
        tieu_de.update({str(k): str(v) for k, v in headers.items()})
    # Đi qua `core/mang_an_toan` chứ không `urlopen` trần: tool mang theo bộ
    # chứng chỉ của chính nó vì kho gốc của Windows hỏng theo đủ kiểu ngoài
    # tầm tay khách (xem docstring tệp ấy). Ở đây còn một lý do riêng — thân
    # yêu cầu này mang khoá bot Telegram, chen được giữa đường là đọc được nó.
    mang_an_toan.dang_json(url, payload, cho=timeout, headers=tieu_de)


# ── Kho chống lặp trên đĩa ──────────────────────────────────────────────────


def _duong_kho(goc: str) -> str:
    """`<goc>` → đường dẫn `workspace/bao-dong-da-gui.json`."""
    return os.path.join(goc, "workspace", DA_GUI_FILENAME)


def _duong_loi_log(goc: str) -> str:
    """`<goc>` → đường dẫn `workspace/bao-dong-loi.log`."""
    return os.path.join(goc, "workspace", LOI_LOG_FILENAME)


def _kho_rong() -> Dict[str, Any]:
    return {"da_gui": {}, "trang_thai": {}, "nhac_cho_ban_tin": {}}


def _doc_kho(goc: str) -> Dict[str, Any]:
    """Đọc kho chống lặp. File thiếu/hỏng → kho rỗng, KHÔNG ném lỗi — một file
    trạng thái hỏng không được làm chết luồng đang cố báo động."""
    try:
        with open(_duong_kho(goc), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return _kho_rong()
    if not isinstance(du_lieu, dict):
        return _kho_rong()
    for khoa in ("da_gui", "trang_thai", "nhac_cho_ban_tin"):
        if not isinstance(du_lieu.get(khoa), dict):
            du_lieu[khoa] = {}
    return du_lieu


def _ghi_kho(goc: str, kho: Dict[str, Any]) -> None:
    """Ghi kho NGUYÊN TỬ: `.tmp` rồi `os.replace` — xem giải thích ở đầu file.

    Ghi lỗi (đĩa đầy, mất quyền...) bị NUỐT ở đây: mất một lần cập nhật chống
    lặp không đáng để làm sập luồng đang cố báo động, lần gọi sau ghi lại
    bình thường.
    """
    try:
        duong = _duong_kho(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(kho, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def _khoa_chong_lap(loai: str, kenh: Optional[str]) -> str:
    """(`loai`, `kenh`) → một chuỗi khoá duy nhất. Không có `kenh` thì khoá
    y hệt bản cũ (chỉ `loai`) — giữ tương thích với dữ liệu/hành vi cũ."""
    ma = str(loai)
    ke = str(kenh).strip() if kenh else ""
    return "{0}::{1}".format(ma, ke) if ke else ma


def _cooldown_cho_muc(cfg: Dict[str, Any], muc: str) -> float:
    if muc == MUC_KHAN:
        khoa_cfg, mac_dinh = "cooldown_khan_giay", COOLDOWN_KHAN_MAC_DINH_GIAY
    elif muc == MUC_NHAC:
        khoa_cfg, mac_dinh = "cooldown_nhac_giay", COOLDOWN_MAC_DINH_GIAY
    else:
        khoa_cfg, mac_dinh = "cooldown_giay", COOLDOWN_MAC_DINH_GIAY
    try:
        cooldown = float(cfg.get(khoa_cfg, mac_dinh))
    except (TypeError, ValueError):
        cooldown = mac_dinh
    return max(0.0, cooldown)


def _qua_khoang_lang(goc: str, khoa: str, cooldown_giay: float, bay_gio: float) -> bool:
    """`True` nếu ĐANG trong khoảng lặng chống spam cho khoá này (nên bỏ qua
    lần bắn này). Đọc/ghi qua file `workspace/bao-dong-da-gui.json` — KHÔNG
    còn qua biến RAM của bản cũ (xem mục "Chống lặp SỐNG TRÊN ĐĨA" đầu file).

    Khi KHÔNG bị chặn, tự cập nhật mốc "lần bắn gần nhất" ngay — kể cả nếu
    lần bắn này rốt cuộc gửi thất bại (mạng lỗi, token sai...): sự cố dai
    dẳng mà kênh báo cũng đang hỏng thì dội liên tục mỗi vài giây cũng vô
    ích, cứ để nhịp sau thử lại — từ 06/10/2026 nhịp đó là 15'/30'/60'… (lùi
    dần, xem `THU_LAI_SAU_LOI_GIAY`) chứ không phải trọn `cooldown_giay`.
    """
    with _KHOA:
        kho = _doc_kho(goc)
        ban_ghi = kho["da_gui"].get(khoa)
        lan_cuoi = None
        if isinstance(ban_ghi, dict):
            try:
                lan_cuoi = float(ban_ghi.get("lan_cuoi"))
            except (TypeError, ValueError):
                lan_cuoi = None
        if lan_cuoi is not None and (bay_gio - lan_cuoi) < cooldown_giay:
            return True
        moi: Dict[str, Any] = {"lan_cuoi": bay_gio}
        if isinstance(ban_ghi, dict) and ban_ghi.get("so_lan_loi"):
            moi["so_lan_loi"] = ban_ghi.get("so_lan_loi")  # giữ đếm lỗi liền cho `_hen_thu_lai_sau_loi`
        kho["da_gui"][khoa] = moi
        _ghi_kho(goc, kho)
        return False


#: Gửi HỎNG (mất mạng, Telegram chập) thì KHÔNG tiêu trọn khoảng lặng của mức
#: (24 giờ với `khan`): thử lại sau 15', rồi 30', 60'… (gấp đôi mỗi lần hỏng liền),
#: kẹp ở chính khoảng lặng. Trước 06/10/2026: mạng chập đúng lúc báo "kênh 2 ngày
#: không đăng" là tin đó im tới 24 giờ sau dù mạng có lại sau 5 phút.
THU_LAI_SAU_LOI_GIAY = 900.0


def _hen_thu_lai_sau_loi(goc: str, khoa: str, cooldown_giay: float, luc: float) -> None:
    """Lùi mốc `lan_cuoi` của `khoa` để lần gọi kế được bắn lại sớm (xem
    `THU_LAI_SAU_LOI_GIAY`). Không ném lỗi."""
    try:
        with _KHOA:
            kho = _doc_kho(goc)
            ban_ghi = kho["da_gui"].get(khoa)
            ban_ghi = dict(ban_ghi) if isinstance(ban_ghi, dict) else {}
            try:
                n = int(ban_ghi.get("so_lan_loi") or 0) + 1
            except (TypeError, ValueError):
                n = 1
            cho = min(float(cooldown_giay), THU_LAI_SAU_LOI_GIAY * (2 ** min(n - 1, 16)))
            ban_ghi.update({"lan_cuoi": luc - float(cooldown_giay) + cho, "so_lan_loi": n})
            kho["da_gui"][khoa] = ban_ghi
            _ghi_kho(goc, kho)
    except Exception:  # noqa: BLE001
        pass


def _xoa_dem_loi(goc: str, khoa: str) -> None:
    try:
        with _KHOA:
            kho = _doc_kho(goc)
            ban_ghi = kho["da_gui"].get(khoa)
            if isinstance(ban_ghi, dict) and ban_ghi.pop("so_lan_loi", None) is not None:
                _ghi_kho(goc, kho)
    except Exception:  # noqa: BLE001
        pass


def quen_lich_su_chong_spam(
    loai: Optional[str] = None,
    *,
    goc: Optional[str] = None,
    kenh: Optional[str] = None,
) -> None:
    """Xoá bộ nhớ chống spam trên ĐĨA (`workspace/bao-dong-da-gui.json`).

    `loai=None` → xoá hết. `loai` kèm `kenh` → xoá đúng một khoá (`loai`,
    `kenh`). `loai` KHÔNG kèm `kenh` → xoá khoá không-kênh VÀ mọi khoá có
    kênh của `loai` đó — để lời gọi cũ không biết khái niệm `kenh` (vd nút
    "Gửi thử một tin" ở `ui_qt/trang_may_vi.py`, gọi
    `quen_lich_su_chong_spam("thu-tin")`) vẫn xoá sạch đúng như hành vi cũ.

    Dùng cho test, hoặc khi chủ dự án vừa xử lý xong một sự cố và muốn được
    báo ngay nếu nó tái phát.
    """
    thu_muc = goc if goc is not None else _GOC_MAC_DINH
    with _KHOA:
        kho = _doc_kho(thu_muc)
        if loai is None:
            kho["da_gui"] = {}
        elif kenh is not None:
            kho["da_gui"].pop(_khoa_chong_lap(loai, kenh), None)
        else:
            tien_to = "{0}::".format(loai)
            for k in list(kho["da_gui"].keys()):
                if k == str(loai) or k.startswith(tien_to):
                    kho["da_gui"].pop(k, None)
        _ghi_kho(thu_muc, kho)


# ── Gửi thất bại: log + trạng thái cho giao diện Tổng quan (việc sau) ───────


def _ghi_that_bai(goc: str, loai: str, loi: BaseException, luc: float) -> None:
    """Gửi thất bại (mất mạng, bot hỏng...) — KHÔNG ném lỗi tiếp (hàm này
    đang XỬ LÝ một lỗi rồi). Ghi 1 dòng vào `workspace/bao-dong-loi.log`, và
    cập nhật `trang_thai.gui_that_bai_lan_cuoi` trong kho để một giao diện
    Tổng quan (việc sau, CHƯA làm ở bản này) đọc ra mà không phải lục log thô
    — xem :func:`doc_trang_thai_gui`.
    """
    try:
        dong_thoi_gian = datetime.fromtimestamp(luc).strftime("%Y-%m-%d %H:%M:%S")
    except (OverflowError, OSError, ValueError):
        dong_thoi_gian = str(luc)
    dong = "[{0}] loai={1} loi={2}\n".format(dong_thoi_gian, loai, str(loi)[:300])
    try:
        duong = _duong_loi_log(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write(dong)
    except OSError:
        pass
    try:
        with _KHOA:
            kho = _doc_kho(goc)
            kho["trang_thai"]["gui_that_bai_lan_cuoi"] = luc
            kho["trang_thai"]["loai_that_bai_lan_cuoi"] = str(loai)
            kho["trang_thai"]["loi_that_bai_lan_cuoi"] = str(loi)[:300]
            _ghi_kho(goc, kho)
    except Exception:  # noqa: BLE001 — hàm này đang xử lý lỗi, không được ném thêm
        pass


def doc_trang_thai_gui(goc: Optional[str] = None) -> Dict[str, Any]:
    """Đọc trạng thái gửi gần nhất (`trang_thai` trong kho chống lặp).

    Dành cho một giao diện Tổng quan sau này hiện dòng "gửi thất bại lần cuối
    lúc..." — CHƯA có giao diện đó ở bản này, hàm này chỉ mở sẵn đường đọc.
    Chưa từng thất bại lần nào / kho chưa tồn tại → dict rỗng.
    """
    thu_muc = goc if goc is not None else _GOC_MAC_DINH
    return dict(_doc_kho(thu_muc).get("trang_thai") or {})


# ── Hàng đợi mức "nhắc" — gộp vào bản tin ngày (kế hoạch V4) ────────────────


def _hang_doi_nhac_them(
    goc: str,
    khoa: str,
    loai: str,
    kenh: Optional[str],
    tieu_de: str,
    chi_tiet: str,
    luc: float,
) -> None:
    with _KHOA:
        kho = _doc_kho(goc)
        kho["nhac_cho_ban_tin"][khoa] = {
            "loai": str(loai),
            "kenh": (str(kenh) if kenh else None),
            "tieu_de": str(tieu_de),
            "chi_tiet": str(chi_tiet),
            "luc": luc,
        }
        _ghi_kho(goc, kho)


def lay_va_xoa_cac_tin_nhac(goc: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lấy hết các tin mức `nhac` đang chờ RỒI XOÁ khỏi hàng đợi.

    Dành cho module bản tin ngày (kế hoạch gia cố V4: "Bản tin 08:00 hằng
    ngày") gộp lại thành MỘT tin thay vì bắn rời rạc suốt ngày. Gọi một lần là
    TIÊU THỤ HẾT — tin đã lấy ra không xuất hiện lại ở lần gọi sau, đúng tinh
    thần "nhắc gộp một lần", khác với mức `khan` (nhắc LẶP LẠI mỗi 24h chừng
    nào sự cố còn tồn tại).
    """
    thu_muc = goc if goc is not None else _GOC_MAC_DINH
    with _KHOA:
        kho = _doc_kho(thu_muc)
        hang_doi = kho.get("nhac_cho_ban_tin") or {}
        if not hang_doi:
            return []
        ra = list(hang_doi.values())
        kho["nhac_cho_ban_tin"] = {}
        _ghi_kho(thu_muc, kho)
    return ra


# ── Khuôn tin bắt buộc cho mức "khan" ────────────────────────────────────────


def khuon_tin_khan(chuyen_gi: str, can_lam_gi: str, neu_khong_lam: str) -> Tuple[str, str]:
    """Dựng (`tieu_de`, `chi_tiet`) đúng KHUÔN 3 DÒNG bắt buộc cho mức `khan`:
    Chuyện gì — Bạn cần làm gì — Nếu không làm thì sao.

    Đây là chỗ DUY NHẤT quyết định hình dạng của một tin khẩn — mọi module
    sau này (kế hoạch gia cố: `gac_tong.py` V3, cảnh báo ví V8, cảnh báo OAuth
    V10, license Windows V5...) nên gọi hàm này (hoặc lối tắt
    :func:`bao_dong_khan`) thay vì tự ghép chuỗi tay, để tin nào cũng đọc
    được như nhau dù đến từ việc gì.

    Viết bằng tiếng Việt người thường — KHÔNG dùng từ kỹ thuật ("token",
    "schema", "endpoint", "invalid_grant"...); người đọc là chủ kênh YouTube,
    không phải lập trình viên. Ba tham số nên là câu hoàn chỉnh, ngắn gọn:

    * `chuyen_gi`: sự thật đang xảy ra, không thuật ngữ.
    * `can_lam_gi`: MỘT hành động cụ thể, làm được ngay.
    * `neu_khong_lam`: hậu quả THẬT nếu bỏ qua — không doạ suông.

    Kết quả ghép với nhau (như :func:`bao_dong` vẫn làm: `tieu_de\\nchi_tiet`)
    ra đúng 3 dòng:

        <chuyen_gi>
        Bạn cần làm gì: <can_lam_gi>
        Nếu không làm thì sao: <neu_khong_lam>
    """
    chuyen_gi = str(chuyen_gi).strip()
    can_lam_gi = str(can_lam_gi).strip()
    neu_khong_lam = str(neu_khong_lam).strip()
    chi_tiet = "Bạn cần làm gì: {0}\nNếu không làm thì sao: {1}".format(
        can_lam_gi, neu_khong_lam)
    return chuyen_gi, chi_tiet


def bao_dong_khan(
    loai: str,
    chuyen_gi: str,
    can_lam_gi: str,
    neu_khong_lam: str,
    *,
    goc: Optional[str] = None,
    kenh: Optional[str] = None,
    bay_gio: Optional[float] = None,
) -> bool:
    """Lối tắt mức `khan` — helper CHUNG mà `gac_tong`, ví, OAuth (các việc
    V3/V8/V10 của kế hoạch gia cố) gọi thay vì tự ghép chuỗi tay.

    Tự dựng đúng khuôn 3 dòng (:func:`khuon_tin_khan`) rồi gọi :func:`bao_dong`
    với `muc="khan"` — gửi NGAY lần đầu, sau đó nhắc lại mỗi
    `cooldown_khan_giay` (mặc định 24 giờ) nếu nơi gọi còn tiếp tục gọi (tức
    sự cố còn tồn tại).
    """
    tieu_de, chi_tiet = khuon_tin_khan(chuyen_gi, can_lam_gi, neu_khong_lam)
    return bao_dong(
        loai, tieu_de, chi_tiet, goc=goc, kenh=kenh, bay_gio=bay_gio, muc=MUC_KHAN)


def bao_dong(
    loai: str,
    tieu_de: str,
    chi_tiet: str = "",
    *,
    goc: Optional[str] = None,
    bay_gio: Optional[float] = None,
    muc: str = MUC_THUONG,
    kenh: Optional[str] = None,
) -> bool:
    """API công khai — MỌI nơi trong tool phát hiện sự cố gọi hàm này.

    `loai`: mã ngắn tự đặt, DÙNG LÀM KHOÁ CHỐNG SPAM (vd `"vi_can"`,
    `"tram_chet"`, `"dia_day"`, `"lich_bo_lo"`) — cùng loại thì tối đa một lần
    mỗi khoảng lặng của mức đang dùng, khác loại thì độc lập nhau.
    `tieu_de`/`chi_tiet`: chữ hiện trong tin nhắn — `chi_tiet` có thể rỗng.
    Với mức `khan`, dựng hai chuỗi này bằng :func:`khuon_tin_khan` (hoặc gọi
    thẳng :func:`bao_dong_khan`) để giữ đúng khuôn 3 dòng bắt buộc.
    `goc`: thư mục chứa `bao-dong.json` (mặc định thư mục gốc MyTool — truyền
    tay khi gọi từ test hoặc từ một cài đặt không nằm ở vị trí mặc định).

    Hai tham số MỚI (mọi lời gọi cũ không truyền vẫn chạy Y HỆT bản trước):

    `muc`: `"thuong"` (mặc định) | `"khan"` | `"nhac"` — xem bảng "Ba mức báo
    động" ở đầu module. Mức `"nhac"` KHÔNG gửi mạng ngay, chỉ xếp vào hàng đợi
    (:func:`lay_va_xoa_cac_tin_nhac`) — hàm vẫn trả `True` vì tin đã được xử
    lý đúng ý định của mức đó (gộp lại, không bắn rời rạc).
    `kenh`: mã kênh YouTube liên quan (vd `"TL1"`), tuỳ chọn — chống lặp khoá
    theo CẶP (`loai`, `kenh`) để sự cố của kênh này không che mất sự cố CÙNG
    loại của kênh khác. Không truyền thì khoá y hệt bản cũ (chỉ theo `loai`).

    Trả `True` nếu đã BẮN (thử gửi) tới ít nhất một kênh và không kênh nào ném
    lỗi, HOẶC đã xếp thành công vào hàng đợi mức `nhac`; trả `False` khi: chưa
    cấu hình, cấu hình tắt (`enabled: false`), đang trong khoảng lặng chống
    spam, hoặc mọi kênh gửi mạng đều lỗi.

    KHÔNG BAO GIỜ ném lỗi ra ngoài — hàm báo sự cố mà chính nó làm sập luồng
    đang cố báo sự cố thì còn tệ hơn im lặng. Gửi lỗi được ghi vào
    `workspace/bao-dong-loi.log` và vào trạng thái đọc được qua
    :func:`doc_trang_thai_gui` — xem mục "Gửi thất bại" ở đầu module.
    """
    try:
        thu_muc = goc if goc is not None else _GOC_MAC_DINH
        cfg = doc_cau_hinh_bao_dong(thu_muc)
        if not cfg or not bool(cfg.get("enabled", True)):
            return False

        tg = _kenh_telegram(cfg)
        wh = _kenh_webhook(cfg)
        if not tg and not wh:
            return False  # file có nhưng chưa điền đường nào -> coi như chưa cấu hình

        muc_dung = str(muc or MUC_THUONG).strip().lower()
        if muc_dung not in (MUC_THUONG, MUC_KHAN, MUC_NHAC):
            muc_dung = MUC_THUONG

        cooldown = _cooldown_cho_muc(cfg, muc_dung)
        luc = bay_gio if bay_gio is not None else time.time()
        khoa = _khoa_chong_lap(loai, kenh)

        if _qua_khoang_lang(thu_muc, khoa, cooldown, luc):
            return False

        if muc_dung == MUC_NHAC:
            # Mức nhắc: KHÔNG bắn ngay — gộp vào hàng đợi cho bản tin ngày.
            _hang_doi_nhac_them(thu_muc, khoa, loai, kenh, tieu_de, chi_tiet, luc)
            return True

        van_ban = tieu_de if not chi_tiet else "{0}\n{1}".format(tieu_de, chi_tiet)
        da_gui = False
        loi_gan_nhat: Optional[BaseException] = None

        if tg:
            token, chat_id = tg
            try:
                _http_post(
                    "https://api.telegram.org/bot{0}/sendMessage".format(token),
                    {"chat_id": chat_id, "text": van_ban},
                )
                da_gui = True
            except Exception as loi:  # noqa: BLE001 — một kênh hỏng không được chặn kênh kia
                loi_gan_nhat = loi

        if wh:
            url, headers = wh
            try:
                _http_post(
                    url,
                    {
                        "loai": loai,
                        "kenh": kenh,
                        "muc": muc_dung,
                        "tieu_de": tieu_de,
                        "chi_tiet": chi_tiet,
                        "luc": luc,
                    },
                    headers=headers,
                )
                da_gui = True
            except Exception as loi:  # noqa: BLE001
                loi_gan_nhat = loi

        if not da_gui and loi_gan_nhat is not None:
            _ghi_that_bai(thu_muc, loai, loi_gan_nhat, luc)
            _hen_thu_lai_sau_loi(thu_muc, khoa, cooldown, luc)
        elif da_gui:
            _xoa_dem_loi(thu_muc, khoa)

        return da_gui
    except Exception:  # noqa: BLE001 — xem lời hứa "không bao giờ ném lỗi" ở trên
        return False


# ── `python -m core.bao_dong --kiem`: CHỈ phân giải DNS, không gửi tin ──────


def _kiem_ipv6_telegram(ten_may: str = "api.telegram.org") -> int:
    """Phân giải DNS `ten_may` và in kết luận về IPv6 — KHÔNG gửi bất kỳ tin
    nào, KHÔNG mở kết nối HTTP/HTTPS tới `ten_may`, chỉ tra DNS (đúng phạm vi
    xin phép: "chỉ phân giải DNS, không gửi tin").

    Trả mã thoát: `0` = có AAAA (ổn với máy chỉ-IPv6), `1` = không phân giải
    được DNS (mất mạng/DNS chặn), `2` = phân giải được nhưng KHÔNG có AAAA.
    """
    print("Đang phân giải DNS cho {0} (không gửi tin, không kết nối)...".format(ten_may))
    try:
        ket_qua = socket.getaddrinfo(ten_may, 443, proto=socket.IPPROTO_TCP)
    except OSError as loi:
        print("KHÔNG phân giải được DNS: {0}".format(loi))
        print("Máy có thể đang mất mạng, hoặc DNS đang chặn tên miền này.")
        return 1

    dia_chi_v6 = sorted({bo[4][0] for bo in ket_qua if bo[0] == socket.AF_INET6})
    dia_chi_v4 = sorted({bo[4][0] for bo in ket_qua if bo[0] == socket.AF_INET})
    print("Bản ghi IPv6 (AAAA): {0}".format(", ".join(dia_chi_v6) if dia_chi_v6 else "KHÔNG có"))
    print("Bản ghi IPv4 (A):    {0}".format(", ".join(dia_chi_v4) if dia_chi_v4 else "không có"))

    if dia_chi_v6:
        print(
            "\nKẾT LUẬN: {0} CÓ bản ghi IPv6 — máy chỉ chạy IPv6 vẫn gọi thẳng "
            "được, không cần sửa gì thêm.".format(ten_may)
        )
        return 0

    print(
        "\nKẾT LUẬN: {0} KHÔNG có bản ghi IPv6 (chỉ IPv4). Máy chỉ có IPv6 sẽ "
        "KHÔNG gọi thẳng được Telegram — mọi lần gửi sẽ thất bại và bị ghi vào "
        "workspace/bao-dong-loi.log.".format(ten_may)
    )
    print("HƯỚNG XỬ LÝ (chỉ in hướng dẫn — KHÔNG tự cài đặt gì ở đây):")
    print("  1. Dùng đường 'webhook' đã có sẵn trong bao-dong.json, trỏ tới một")
    print("     dịch vụ trung chuyển có IPv4 (vd một Cloudflare Worker, hoặc một")
    print("     máy/dịch vụ khác — n8n, Make... — nhận webhook rồi tự gọi tiếp")
    print("     sang Telegram Bot API hộ).")
    print("  2. Hoặc bật NAT64/DNS64 phía nhà cung cấp VPS (nếu họ có), để tên")
    print("     miền chỉ-IPv4 được dịch tạm sang IPv6 khi máy này gọi ra ngoài.")
    return 2


def _main(argv: Optional[List[str]] = None) -> int:
    # Console mặc định của Windows (cp1252/cp437) không in được tiếng Việt có
    # dấu — ép UTF-8 ngay tại đây để `python -m core.bao_dong --kiem` chạy
    # được thẳng trong một cửa sổ terminal bình thường, không cần người dùng
    # tự đặt PYTHONUTF8=1 trước. Môi trường không cho reconfigure (vd bị bọc
    # lại/redirect) thì bỏ qua, không được làm chết lệnh kiểm tra vì lý do này.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    danh_sach = sys.argv[1:] if argv is None else argv
    if "--kiem" in danh_sach:
        return _kiem_ipv6_telegram()
    print("Dùng: python -m core.bao_dong --kiem")
    print("  (chỉ kiểm DNS IPv6 tới api.telegram.org — KHÔNG gửi tin, không cài gì)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
