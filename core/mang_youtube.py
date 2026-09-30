"""Đường ra YouTube: **proxy** + **cookie của trình duyệt kênh**.

═══ BỆNH THẬT, VPS NÀY, ĐÊM 22/09/2026 ═══

02:00 sáng, ba kênh mới chạy tự động cùng chết ở khâu ĐẦU TIÊN (`kich-ban`), ba
lượt thử đều hỏng y hệt. Không phải mã sai — **YouTube chặn địa chỉ mạng của
máy này**. Đo thẳng trên máy, không đoán:

* `youtube-transcript-api` trả `IpBlocked`, nguyên văn:
  *"You are doing requests from an IP belonging to a cloud provider"*.
* `yt-dlp` không cookie: *"Sign in to confirm you're not a bot"* — trên **cả
  năm** kiểu `player_client` mà `KHACH_YOUTUBE` đang thử, tức đổi ứng dụng giả
  không còn cứu được nữa.
* `yt-dlp` **có cookie** lấy từ hồ sơ Chromium của kênh: lỗi chặn bot **biến
  mất**, nhưng đổi thành *"Requested format is not available"* — qua được cửa,
  nhưng YouTube không trả luồng nào.
* Video đối chứng `dQw4w9WgXcQ` (video nổi tiếng nhất hành tinh, chắc chắn còn
  sống) hỏng y hệt → không phải lỗi của một video cụ thể.
* `yt-dlp` đã là bản mới nhất (2026.08.19); nâng cấp không đổi gì.
* Nhưng **trình duyệt chống vân tay của kênh vào YouTube bình thường từ đúng IP
  ấy** — nó cào Studio và trang chủ xong ngay đêm đó.

Ghép lại: chặn nhắm vào **client không phải trình duyệt thật**, cộng thêm việc
IP này là IP trung tâm dữ liệu. Nên có hai nước cờ, và chúng bù nhau chứ không
thay nhau:

| Nước | Gỡ được gì | Không gỡ được gì |
|------|-----------|------------------|
| **cookie** trình duyệt kênh | cửa "chứng minh không phải máy" | IP vẫn là IP thuê |
| **proxy IP dân cư** | cái mác "máy chủ thuê" | cửa chặn bot (vẫn nên kèm cookie) |

═══ VÌ SAO LÀ MỘT TỆP RIÊNG, KHÔNG NHÉT VÀO `config.json` ═══

Đúng lý do của `core/bao_dong.py`: `config.json` là HỢP ĐỒNG CỐ ĐỊNH (xem đầu
`core/config.py`) và `secrets.json` là kho khoá API. Chuỗi proxy có kèm
user:pass nên nó là **bí mật của máy này**, không phải của khách — mà cũng
không phải khoá ví. Để riêng `mang-youtube.json` thì:

* khách bình thường **không có tệp này** → tool chạy y như trước, không một
  dòng lỗi nào, không một mili-giây nào chậm hơn (xem :func:`cac_nac`);
* chủ dự án đổi proxy lúc 2 giờ sáng chỉ phải sửa một tệp bốn dòng, không đụng
  vào tệp có khoá ví;
* đóng gói bản cập nhật không vô tình mang proxy của máy này đi phát cho khách.

═══ DẠNG TỆP `mang-youtube.json` ═══

Đặt **cạnh `config.json`** (tức trong thư mục `MyTool/`). Mọi khoá đều có thể
bỏ trống; thiếu tệp = thiếu tất cả = nết cũ.

```json
{
  "proxy": "http://user:pass@host:port",
  "dung_cookie": true,
  "kenh_lay_cookie": "TL3-T7",
  "thu_khong_proxy_truoc": true
}
```

| Khoá | Mặc định | Nghĩa |
|------|----------|-------|
| `proxy` | `""` | Chuỗi proxy cho **cả** `yt-dlp` lẫn `youtube-transcript-api` lẫn đường tải tệp phụ đề. Rỗng = không có nấc proxy nào. `http://`, `https://`, `socks5://` đều được — `yt-dlp` và `requests` cùng hiểu. |
| `dung_cookie` | `false` | Có mượn cookie của trình duyệt kênh không. |
| `kenh_lay_cookie` | `""` | Mã kênh, ví dụ `TL3-T7`. Hồ sơ suy ra là `<thư mục cha của MyTool>/<mã>/Data/profile`. |
| `thu_khong_proxy_truoc` | `true` | `true` = thử đường thẳng trước cho đỡ tốn proxy; `false` = đi thẳng qua proxy (dùng khi đã biết chắc IP máy bị chặn, để khỏi phí mỗi lượt hai lần hỏng). |
| `trinh_duyet` | `"chrome"` | Tên trình duyệt cho `yt-dlp` đọc kho cookie. Hồ sơ kênh là Chromium nên `chrome` là đúng. |
| `ho_so_cookie` | `""` | Đường dẫn hồ sơ khai thẳng, **đè** `kenh_lay_cookie`. Để dành cho hồ sơ nằm ngoài nếp đặt tên. |

⚠ **Trình duyệt phải ĐANG ĐÓNG** thì mới đọc được kho cookie của Chromium. Máy
này chạy chế độ phiên nên phần lớn thời gian nó đóng, nhưng lúc nó mở thì đọc
cookie hỏng — và khi ấy **đi tiếp không cookie** chứ không làm vỡ cả lượt (xem
:func:`kho_cookie`).

═══ ⚠ ĐO LẠI TRƯA 22/09/2026 — ĐỌC TRƯỚC KHI BẬT `dung_cookie` ═══

Đo lại chính máy này vài tiếng sau sự cố, trên cùng video đối chứng
`dQw4w9WgXcQ`, được ba con số trái ngược nhau và cả ba đều đáng nhớ:

1. **Nấc `thẳng` (không proxy, không cookie) CHẠY ĐƯỢC** — lấy về 487 chữ phụ
   đề do chính kênh làm. Tức cái chặn bot đêm qua **không vĩnh viễn**: nó lên
   xuống theo nhịp hỏi. Đây chính là lý do nấc `thẳng` phải luôn đứng đầu và
   phải được thử lại mỗi lượt, chứ không phải "đã chặn một lần thì cạch hẳn".
2. **`youtube-transcript-api` VẪN bị `IpBlocked`** cùng lúc đó, nguyên văn
   *"YouTube is blocking requests from your IP"*. Nghĩa là hai thư viện bị
   chặn theo hai nhịp khác nhau — giữ đủ bốn đường vẫn là đúng.
3. **Nấc `cookie` LÀM HỎNG chính lượt đang chạy được**: yt-dlp mượn 92 cookie
   từ hồ sơ `TL3-T7` (đọc ngon lành, trình duyệt đang đóng) rồi trả
   *"ERROR: [youtube] dQw4w9WgXcQ: The page needs to be reloaded."* — trong
   khi không cookie thì xong việc.

Nên `dung_cookie` mặc định **tắt**, và nấc `cookie` chỉ đứng SAU nấc `thẳng`.

⚠ **Và có một cái giá không được phép trả nhầm.** yt-dlp cảnh báo: mượn cookie
của một phiên YouTube **đang đăng nhập** làm YouTube xoay khoá phiên, và có ca
làm **văng luôn đăng nhập của chính trình duyệt ấy**. Trình duyệt kênh ở đây là
thứ dùng để ĐĂNG VIDEO. Mất đăng nhập của nó thì hỏng cả dây chuyền đăng, để
đổi lấy một đoạn lời thoại — đổi chác tệ hơn nhiều lần so với việc video đó
không lấy được script. Vì vậy: bật `dung_cookie` chỉ khi đã thử hết đường khác,
và tốt nhất là trỏ `ho_so_cookie` vào một hồ sơ trình duyệt **riêng, không dùng
để đăng bài**.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "MANG_FILENAME",
    "CauHinhMang",
    "Nac",
    "duong_dan_cau_hinh",
    "doc_cau_hinh",
    "duong_dan_ho_so",
    "cac_nac",
    "tuy_chon_ytdlp",
    "proxy_transcript",
    "phien_transcript",
    "kho_cookie",
    "mo_url_qua_proxy",
    "la_dau_chan_ip",
    "cau_loi_chan_ip",
    "quen_bo_nho_dem",
]

#: Tên tệp cấu hình — nằm cạnh `config.json`/`secrets.json` nhưng KHÔNG phải
#: một trong hai tệp đó (xem lý do ở đầu module).
MANG_FILENAME = "mang-youtube.json"

#: Thư mục gốc mặc định (`MyTool/`) — dùng khi nơi gọi không truyền `goc`.
#: Cùng lối với `core/bao_dong.py`.
_GOC_MAC_DINH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_KHOA = threading.Lock()
#: `đường dẫn tệp` -> `(dấu thời gian, cỡ tệp, cấu hình đã đọc)`.
_NHO_CAU_HINH: Dict[str, Tuple[float, int, "CauHinhMang"]] = {}
#: `đường dẫn hồ sơ` -> `(kho cookie hoặc None, lý do hỏng)`.
_NHO_COOKIE: Dict[str, Tuple[Any, str]] = {}


# ── Cấu hình ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CauHinhMang:
    """Nội dung `mang-youtube.json` sau khi đã đọc. Mặc định = nết cũ."""

    proxy: str = ""
    dung_cookie: bool = False
    kenh_lay_cookie: str = ""
    thu_khong_proxy_truoc: bool = True
    trinh_duyet: str = "chrome"
    ho_so_cookie: str = ""

    @property
    def trong(self) -> bool:
        """Không khai gì cả → tuyệt đối không đổi hành vi của tool."""
        return not self.proxy and not (
            self.dung_cookie and (self.kenh_lay_cookie or self.ho_so_cookie))


def duong_dan_cau_hinh(goc: str = "") -> str:
    """`<goc>` (thư mục chứa `config.json`) → đường dẫn `mang-youtube.json`."""
    return os.path.join(goc or _GOC_MAC_DINH, MANG_FILENAME)


def doc_cau_hinh(goc: str = "") -> CauHinhMang:
    """Đọc `mang-youtube.json`. Thiếu tệp / tệp hỏng → cấu hình RỖNG, im lặng.

    Im lặng là cố ý. Tệp này chỉ có trên máy chủ dự án; máy khách không bao giờ
    có, và một dòng cảnh báo vô nghĩa ở mỗi lượt gọi mạng thì chỉ làm nhật ký
    khó đọc hơn. Tệp có mà gõ sai JSON cũng vậy: thà chạy như cũ (rồi hỏng với
    câu lỗi chặn-IP nói rõ phải khai proxy) còn hơn giết cả lượt chạy đêm vì
    một dấu phẩy thừa.

    Nhớ theo `(dấu thời gian, cỡ tệp)`: `_extract` gọi hàm này ở **mọi** lượt ra
    mạng, mà mở tệp mỗi lượt thì vô ích. Sửa tệp là mốc đổi → tự đọc lại, không
    phải khởi động lại tool.
    """
    duong = duong_dan_cau_hinh(goc)
    try:
        st = os.stat(duong)
        moc = (st.st_mtime, st.st_size)
    except OSError:
        with _KHOA:
            _NHO_CAU_HINH.pop(duong, None)
        return CauHinhMang()

    with _KHOA:
        cu = _NHO_CAU_HINH.get(duong)
        if cu is not None and (cu[0], cu[1]) == moc:
            return cu[2]

    import json  # noqa: PLC0415 — chỉ cần khi thật sự có tệp

    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return CauHinhMang()
    if not isinstance(du_lieu, dict):
        return CauHinhMang()

    cau_hinh = CauHinhMang(
        proxy=str(du_lieu.get("proxy") or "").strip(),
        dung_cookie=bool(du_lieu.get("dung_cookie")),
        kenh_lay_cookie=str(du_lieu.get("kenh_lay_cookie") or "").strip(),
        # Khai thiếu thì mặc định THỬ ĐƯỜNG THẲNG TRƯỚC: proxy dân cư tính tiền
        # theo dung lượng, còn đường thẳng thì miễn phí.
        thu_khong_proxy_truoc=bool(du_lieu.get("thu_khong_proxy_truoc", True)),
        trinh_duyet=str(du_lieu.get("trinh_duyet") or "chrome").strip() or "chrome",
        ho_so_cookie=str(du_lieu.get("ho_so_cookie") or "").strip(),
    )
    with _KHOA:
        _NHO_CAU_HINH[duong] = (moc[0], moc[1], cau_hinh)
    return cau_hinh


def duong_dan_ho_so(cau_hinh: CauHinhMang, goc: str = "") -> str:
    """Hồ sơ Chromium của kênh: `<cha của MyTool>/<MÃ>/Data/profile`.

    Suy từ vị trí `MyTool/` chứ không viết cứng `C:\\Users\\<ten>\\…`:
    thư mục kênh và `MyTool` là anh em ruột trên mọi máy đang chạy (máy chủ dự
    án lẫn VPS), nên `dirname(goc)` luôn đúng, còn đường dẫn viết cứng thì sai
    ngay lần đầu ai đó đổi ổ đĩa.

    Rỗng khi: không bật `dung_cookie`, không khai kênh, hoặc thư mục không có
    thật — trường hợp cuối quan trọng nhất, vì khai sai mã kênh mà vẫn dựng nấc
    cookie thì mỗi lượt chạy tốn thêm một lần hỏng vô ích.
    """
    if not cau_hinh.dung_cookie:
        return ""
    if cau_hinh.ho_so_cookie:
        duong = cau_hinh.ho_so_cookie
    elif cau_hinh.kenh_lay_cookie:
        duong = os.path.join(os.path.dirname(goc or _GOC_MAC_DINH),
                             cau_hinh.kenh_lay_cookie, "Data", "profile")
    else:
        return ""
    return duong if os.path.isdir(duong) else ""


# ── Các nấc thử ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Nac:
    """Một nấc thử: đi bằng proxy nào, mượn cookie của hồ sơ nào."""

    ten: str = "thẳng"
    proxy: str = ""
    ho_so: str = ""
    trinh_duyet: str = "chrome"

    @property
    def tran(self) -> bool:
        """Nấc "y như trước": không proxy, không cookie."""
        return not self.proxy and not self.ho_so


#: Nấc mặc định — chính là hành vi của tool trước ngày 22/09/2026.
NAC_TRAN = Nac()


def cac_nac(cau_hinh: Optional[CauHinhMang] = None, goc: str = "") -> List[Nac]:
    """Thứ tự thử: **rẻ trước, đắt sau**. Luôn có ít nhất một nấc.

    Bốn nấc theo đúng thứ tự tiền và thời gian phải trả:

    1. `thẳng` — như trước, miễn phí, nhanh nhất.
    2. `cookie` — thêm một lần đọc kho cookie Chromium (~1 giây), vẫn miễn phí.
    3. `proxy` — bắt đầu tốn dung lượng proxy dân cư (tính tiền theo GB).
    4. `proxy+cookie` — đắt nhất, nhưng là nấc duy nhất gỡ được **cả hai** cửa.

    `thu_khong_proxy_truoc=False` thì bỏ hai nấc đầu: khi đã biết chắc IP này bị
    chặn, hai nấc ấy chỉ là hai lần hỏng có sẵn kết quả, nhân với hàng trăm
    video một đêm thì thành hàng giờ chờ vô ích.

    Không khai gì → đúng **một** nấc `thẳng`, tức tool chạy y hệt bản cũ: không
    thử thêm lần nào, không chậm thêm một mili-giây nào.

    >>> [n.ten for n in cac_nac(CauHinhMang())]
    ['thẳng']
    >>> [n.ten for n in cac_nac(CauHinhMang(proxy='http://p'))]
    ['thẳng', 'proxy']
    >>> [n.ten for n in cac_nac(CauHinhMang(proxy='http://p',
    ...                                     thu_khong_proxy_truoc=False))]
    ['proxy']
    """
    cau_hinh = cau_hinh if cau_hinh is not None else doc_cau_hinh(goc)
    ho_so = duong_dan_ho_so(cau_hinh, goc)
    trinh = cau_hinh.trinh_duyet

    nac: List[Nac] = []
    # Không có proxy thì `thu_khong_proxy_truoc` vô nghĩa — vẫn phải đi đường
    # thẳng, vì bỏ nốt nấc này là trả về danh sách rỗng và tool câm luôn.
    if cau_hinh.thu_khong_proxy_truoc or not cau_hinh.proxy:
        nac.append(NAC_TRAN)
        if ho_so:
            nac.append(Nac("cookie", ho_so=ho_so, trinh_duyet=trinh))
    if cau_hinh.proxy:
        nac.append(Nac("proxy", proxy=cau_hinh.proxy))
        if ho_so:
            nac.append(Nac("proxy+cookie", proxy=cau_hinh.proxy, ho_so=ho_so,
                           trinh_duyet=trinh))
    return nac or [NAC_TRAN]


# ── Đổi một nấc thành tuỳ chọn cho từng thư viện ─────────────────────────────


def tuy_chon_ytdlp(nac: Nac) -> Dict[str, Any]:
    """Nấc → mấy khoá cần thêm vào tuỳ chọn `yt-dlp`. Nấc trần → `{}`.

    `{}` chứ không phải `{"proxy": None}`: trả về khoá rỗng thì `base.update()`
    ở `core/youtube.py::_extract` vẫn ghi đè, và một ngày nào đó yt-dlp đổi ý
    nghĩa của `proxy=None` là tool đổi hành vi mà không ai biết vì sao.

    Bộ bốn `(trình duyệt, hồ sơ, keyring, container)` là đúng dạng `yt-dlp` đòi
    ở `cookiesfrombrowser` — cũng chính là bộ đã đo được trên máy này.

    >>> tuy_chon_ytdlp(NAC_TRAN)
    {}
    >>> tuy_chon_ytdlp(Nac('proxy', proxy='http://p'))
    {'proxy': 'http://p'}
    """
    tuy: Dict[str, Any] = {}
    if nac.proxy:
        tuy["proxy"] = nac.proxy
    if nac.ho_so:
        tuy["cookiesfrombrowser"] = (nac.trinh_duyet, nac.ho_so, None, None)
    return tuy


def proxy_transcript(nac: Nac):
    """Nấc → `ProxyConfig` cho `youtube-transcript-api`. Không proxy → `None`.

    Bản 1.x của thư viện nhận proxy qua **hàm dựng**
    (`YouTubeTranscriptApi(proxy_config=…)`), không phải qua biến môi trường —
    đọc thẳng mã của bản đang cài (1.2.4) chứ không đoán. `GenericProxyConfig`
    chỉ khai một trong hai `http_url`/`https_url` là nó tự dùng cho cả hai, ở
    đây khai đủ cả hai cho khỏi phụ thuộc vào nết ấy.
    """
    if not nac.proxy:
        return None
    try:
        from youtube_transcript_api.proxies import GenericProxyConfig  # noqa: PLC0415
    except ImportError:  # pragma: no cover — bản thư viện quá cũ
        return None
    try:
        return GenericProxyConfig(http_url=nac.proxy, https_url=nac.proxy)
    except Exception:  # noqa: BLE001 — chuỗi proxy gõ sai thì đi tiếp không proxy
        return None


def kho_cookie(nac: Nac, ghi: Optional[Callable[[str], None]] = None):
    """Đọc kho cookie Chromium của kênh. Hỏng → `None` **và đi tiếp**.

    ═══ VÌ SAO HỎNG THÌ KHÔNG ĐƯỢC LÀM VỠ CẢ LƯỢT ═══

    Kho cookie của Chromium là một tệp SQLite bị **khoá khi trình duyệt đang
    mở**. Máy này chạy chế độ phiên nên trình duyệt kênh đóng phần lớn thời
    gian — nhưng "phần lớn" không phải "luôn luôn", và lượt chạy đêm rơi đúng
    lúc nó mở là chuyện sẽ xảy ra. Khi ấy việc đúng là chạy tiếp không cookie
    (biết đâu đường thẳng vẫn qua) chứ không phải ném lỗi giết cả khâu.

    Vẫn **ghi một dòng nhật ký nói rõ vì sao**: đọc log lúc 2 giờ sáng mà thấy
    "không lấy được lời thoại" trống trơn thì không ai đoán ra là tại trình
    duyệt đang mở.

    Nhớ kết quả theo hồ sơ (cả khi hỏng): một lượt chạy có hàng chục video, mà
    mỗi lần đọc kho cookie là một lần giải mã cả tệp SQLite.
    """
    if not nac.ho_so:
        return None
    with _KHOA:
        cu = _NHO_COOKIE.get(nac.ho_so)
    if cu is not None:
        if cu[1] and ghi is not None:
            ghi("    (vẫn không đọc được cookie: {0})".format(cu[1]))
        return cu[0]

    jar, ly_do = None, ""
    try:
        from yt_dlp.cookies import extract_cookies_from_browser  # noqa: PLC0415

        jar = extract_cookies_from_browser(nac.trinh_duyet, nac.ho_so)
    except Exception as loi:  # noqa: BLE001 — trình duyệt đang mở, hồ sơ lạ…
        jar, ly_do = None, str(loi)[:160]
        if ghi is not None:
            ghi("    không đọc được cookie của trình duyệt kênh ({0}) — đi tiếp "
                "KHÔNG cookie. Thường là trình duyệt đang mở nên kho cookie bị "
                "khoá; đóng nó rồi chạy lại thì có cookie.".format(ly_do))
    with _KHOA:
        _NHO_COOKIE[nac.ho_so] = (jar, ly_do)
    return jar


def phien_transcript(nac: Nac, ghi: Optional[Callable[[str], None]] = None):
    """Phiên `requests` mang sẵn cookie cho `youtube-transcript-api`.

    Bản 1.x nhận `http_client` là một `requests.Session`, và đó là chỗ **duy
    nhất** nhét cookie vào được — thư viện không có tham số cookie riêng. Dựng
    phiên chỉ khi nấc này có hồ sơ và đọc được cookie; không thì trả `None` để
    nơi gọi dùng phiên mặc định của thư viện.
    """
    jar = kho_cookie(nac, ghi)
    if jar is None:
        return None
    try:
        import requests  # noqa: PLC0415

        phien = requests.Session()
        for banh in jar:
            phien.cookies.set_cookie(banh)
    except Exception:  # noqa: BLE001 — không dựng được phiên thì đi tiếp không cookie
        return None
    return phien


def mo_url_qua_proxy(proxy: str):
    """Hàm mở URL đi qua proxy, dùng thay `urlopen` khi tải tệp phụ đề.

    Tệp phụ đề KHÔNG đi qua `yt-dlp` — `core/script_video.py::_tai_chu` tự tải
    bằng `urllib`. Quên chỗ này là proxy chỉ áp một nửa: `yt-dlp` xin được địa
    chỉ tệp phụ đề qua IP dân cư, rồi máy lại tải tệp ấy bằng chính cái IP máy
    chủ vừa bị chặn — và những địa chỉ ấy có ràng theo IP.

    Giữ bộ gốc chứng chỉ của `core/mang_an_toan`: đi qua proxy không phải lý do
    để tin kho chứng chỉ của hệ điều hành ít hơn hay nhiều hơn.
    """
    import urllib.request  # noqa: PLC0415

    tay = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})]
    try:
        from .mang_an_toan import boi_canh_ssl  # noqa: PLC0415

        tay.append(urllib.request.HTTPSHandler(context=boi_canh_ssl()))
    except Exception:  # noqa: BLE001 — thiếu certifi thì dùng kho hệ điều hành
        pass
    return urllib.request.build_opener(*tay).open


# ── Nhận ra "bị chặn theo IP" và nói bằng tiếng người ─────────────────────────

#: Dấu hiệu **chắc chắn** là chặn theo địa chỉ mạng. Đều là nguyên văn đo được
#: trên máy này đêm 22/09/2026, hạ hết về chữ thường.
_DAU_CHAC = (
    "not a bot",                              # "Sign in to confirm you're not a bot"
    "ip belonging to a cloud provider",       # nguyên văn của youtube-transcript-api
    "ipblocked",
    "requestblocked",
    "your ip has been blocked",
)

#: Dấu hiệu **nghi ngờ**: một mình nó chưa đủ kết tội (một video hỏng thật cũng
#: ra câu này), nhưng gặp trên video đối chứng `dQw4w9WgXcQ` thì chính là bộ
#: mặt thứ hai của cùng một cái chặn — YouTube cho qua cửa bot rồi không trả
#: luồng nào.
_DAU_NGHI = (
    "requested format is not available",
    "no video formats found",
    "failed to extract any player response",
    "po token",
    "potokenrequired",
)
# Cố ý KHÔNG có "429" ở đây. `core/script_video.py::_tai_chu` đã có câu riêng
# cho nó ("YouTube chặn tải phụ đề (lỗi 429)") và đã biết chờ rồi hỏi lại —
# 429 là chặn theo *nhịp hỏi*, một phút sau là qua, không phải chặn theo địa
# chỉ mạng. Gộp nó vào đây là bắt chủ dự án đi thuê proxy để chữa một thứ tự
# khỏi sau vài giây.


def la_dau_chan_ip(chu: str) -> str:
    """Câu lỗi này có phải dấu chặn-theo-IP không? → `"chac"` / `"nghi"` / `""`.

    >>> la_dau_chan_ip("ERROR: Sign in to confirm you're not a bot")
    'chac'
    >>> la_dau_chan_ip("Requested format is not available")
    'nghi'
    >>> la_dau_chan_ip("Video unavailable")
    ''
    """
    # Nháy đơn cong (’) là nháy YouTube thật sự trả về; đổi về nháy thẳng để
    # một chuỗi mẫu bắt được cả hai kiểu.
    text = str(chu or "").replace("\u2019", "'").lower()
    if any(dau in text for dau in _DAU_CHAC):
        return "chac"
    if any(dau in text for dau in _DAU_NGHI):
        return "nghi"
    return ""


def cau_loi_chan_ip(muc: str, goc_loi: str = "") -> str:
    """Câu lỗi cho **người thường** đọc lúc 2 giờ sáng qua báo cáo ngày.

    Câu cũ ném nguyên văn lỗi `yt-dlp` — *"Requested format is not available"* —
    và câu đó nói sai bản chất theo đúng hướng tệ nhất: nó nghe như video hỏng,
    nên việc chủ dự án sẽ làm là đổi video, rồi video nào cũng thế, rồi mất một
    đêm. Câu đúng phải nói **ai chặn**, **chặn cái gì**, và **gỡ bằng cách nào**
    — cả ba trong một câu.

    Vẫn đính nguyên văn lỗi gốc ở cuối (cắt ngắn): người sửa mã cần nó, mà người
    đọc báo cáo thì đã có đủ ý ở câu trước dấu ngoặc.
    """
    if muc == "chac":
        cau = ("YouTube đang chặn địa chỉ mạng của máy này (IP máy chủ thuê) — "
               "không phải video thiếu phụ đề. Cần khai proxy IP dân cư trong "
               "mang-youtube.json (đặt cạnh config.json) rồi chạy lại.")
    else:
        cau = ("YouTube không trả luồng nào cho máy này, gần như chắc là đang "
               "chặn địa chỉ mạng của máy chủ thuê. Cần khai proxy IP dân cư "
               "trong mang-youtube.json (đặt cạnh config.json) rồi chạy lại.")
    tho = " ".join(str(goc_loi or "").split())[:140]
    return "{0} (dấu hiệu: {1})".format(cau, tho) if tho else cau


#: Dấu hiệu **đọc kho cookie hỏng**: trình duyệt kênh đang mở nên tệp SQLite
#: bị khoá, hoặc hồ sơ vừa bị dọn.
_DAU_KHO_COOKIE = (
    "could not copy",
    "database is locked",
    "unable to open database",
    "failed to decrypt",
    "cookie",
    "keyring",
)

#: Dấu hiệu **cookie mượn được nhưng YouTube không nhận**. Đo trên máy này
#: 22/09/2026 với hồ sơ `TL3-T7` (92 cookie đọc ra ngon lành).
_DAU_COOKIE_CHET = (
    "the page needs to be reloaded",
)

LOI_COOKIE = ("không đọc được cookie của trình duyệt kênh (thường là trình duyệt "
              "đang mở nên kho cookie bị khoá) — đi tiếp KHÔNG cookie")

#: ⚠ Câu này quan trọng hơn vẻ ngoài của nó — xem phần cảnh báo ở đầu module.
LOI_COOKIE_CHET = ("YouTube không nhận cookie mượn từ trình duyệt kênh (“The page "
                   "needs to be reloaded”) — đi tiếp KHÔNG cookie. Nếu lặp lại, "
                   "hãy TẮT dung_cookie: mượn cookie của phiên đang đăng nhập có "
                   "thể làm văng luôn đăng nhập của trình duyệt kênh ấy")


def la_loi_cookie(chu: str) -> bool:
    """Lỗi này là chuyện của cookie chứ không phải YouTube chặn IP?

    Dùng để nhật ký nói đúng thủ phạm: một nấc `cookie` hỏng vì trình duyệt
    đang mở và một nấc `cookie` hỏng vì YouTube chặn là hai chuyện khác hẳn
    nhau, mà nguyên văn lỗi thì lẫn vào nhau.

    >>> la_loi_cookie("Could not copy Chrome cookie database")
    True
    >>> la_loi_cookie("ERROR: [youtube] abc: The page needs to be reloaded.")
    True
    >>> la_loi_cookie("Sign in to confirm you're not a bot")
    False
    """
    text = str(chu or "").lower()
    return any(dau in text for dau in _DAU_KHO_COOKIE + _DAU_COOKIE_CHET)


def giai_thich_loi_cookie(chu: str) -> str:
    """Câu nói cho người đọc nhật ký biết cookie hỏng kiểu nào và làm gì tiếp.

    Hai kiểu hỏng, hai việc phải làm khác hẳn nhau — gộp làm một là dắt người
    đọc đi sai đường:

    * **đọc không ra** → đóng trình duyệt kênh rồi chạy lại là xong;
    * **đọc ra mà YouTube không nhận** → chạy lại bao nhiêu lần cũng thế, và
      còn phải cân nhắc TẮT hẳn `dung_cookie` (xem cảnh báo đầu module).

    >>> giai_thich_loi_cookie("The page needs to be reloaded") == LOI_COOKIE_CHET
    True
    """
    text = str(chu or "").lower()
    if any(dau in text for dau in _DAU_COOKIE_CHET):
        return LOI_COOKIE_CHET
    return LOI_COOKIE


def quen_bo_nho_dem() -> None:
    """Xoá mọi thứ đang nhớ. Chỉ để bài kiểm chạy độc lập với nhau."""
    with _KHOA:
        _NHO_CAU_HINH.clear()
        _NHO_COOKIE.clear()
