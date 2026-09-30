"""Trạm nhận chạy NỀN — không cần cửa sổ Qt, không cần ai đăng nhập ngồi nhìn.

═══ VÌ SAO CẦN TỆP NÀY ═══

Trạm HTTP 8765 (`core/chi_so_ytb/tram.py`) là ĐƯỜNG DUY NHẤT máy ảo lấy được kế
hoạch đăng: `vm/nguon_tool.py` chỉ biết mỗi `GET /ke-hoach?kenh=X`. Nhưng tới
19/09/2026 trạm ấy chỉ được dựng ở MỘT chỗ — `ui_qt/trang_chi_so_ytb.py` (thẻ
"trạm nhận" của tab VPS & Máy VM) — tức nó **sống nhờ tiến trình Qt của MyTool**.
Cửa sổ tắt, Qt sập, hay người dùng lỡ bấm X là cổng 8765 chết theo.

Đo THẬT trên máy dựng lúc 17:47 ngày 21/09/2026: không tiến trình nào nghe cổng
8765, tiến trình Python duy nhất còn sống là `vm/agent.py`, và `vm/agent.log` đầy
dòng `WinError 10061 … actively refused`. Hệ quả im lặng nhất có thể: video đã
sản xuất xong nằm chết trong thư mục — không lỗi, không cảnh báo, không bao giờ
lên sóng. Máy có `AutoAdminLogon=1` và lối tắt trong Startup, nên lúc KHỞI ĐỘNG
máy thì tool có bật; nhưng tool sập giữa chừng thì không ai bật lại.

Mô-đun này tách cái trạm ra khỏi cửa sổ: cùng đúng lớp `Tram` sẵn có, chỉ khác
là chạy trong một tiến trình trần (`pythonw tram_nen.py`), giữ mình sống, và
không import một dòng Qt nào.

═══ MỘT CỔNG, MỘT CHỦ — AI NHƯỜNG AI ═══

`ui_qt/tram_chung.py` đã chốt luật "nguồn sự thật duy nhất": chỉ MỘT nơi được
giữ cổng 8765. `tram.bat()` còn đi xa hơn — thấy cổng bận thì hỏi thẳng bằng gói
dò UDP `shopapi-tram?`; nếu thứ đang giữ là MỘT TRẠM KHÁC của tool thì nó TỪ
CHỐI lùi cổng (lùi là có hai trạm cùng sống, máy ảo gọi về trúng bản nào là ngẫu
nhiên — đúng sự cố đêm 07/09/2026).

Bản nền này tôn trọng đúng luật ấy, hai chiều:

* **Lúc bật** — hỏi `shopapi-tram?` trước. Có tiếng đáp nghĩa là GUI (hoặc một
  bản nền khác) đang giữ: bản nền GHI NHẬT KÝ rồi tự thoát, không đụng vào cổng.
  Nhường, không tranh.
* **Lúc GUI mở lên sau** — GUI là bản ĐẦY ĐỦ (có nút bấm, có nhãn trạng thái,
  có ví để viết hộ bình luận), nên nó được quyền đòi lại cổng. Nó gọi
  `xin_nhuong()`: một tệp cờ được đặt xuống `workspace/tram-nen/`, bản nền thấy
  cờ thì tắt trạm, xoá dấu tích rồi thoát. `core/khoi_dong_vps.py` gọi hàm ấy
  ngay trước `bao_dam_bat()`.

Không thêm cổng nào cho việc bắt tay này: tệp cờ trên đĩa là đủ, hai tiến trình
vốn đã cùng đọc ghi một thư mục tool.

═══ KHÔNG QT, VÀ KHÔNG GỌI MẠNG LÚC NẠP ═══

Mọi thứ nặng (`core.api`, `core.vps_rieng`, `core.goi_van_ban`) nhập BÊN TRONG
hàm, lúc thật sự cần. Nạp mô-đun này phải rẻ và phải an toàn trong bộ test —
bài kiểm nhập nó để gọi `xin_nhuong`/`con_song` mà không được dựng cổng nào.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .chi_so_ytb.tram import CONG_MAC_DINH, SO_CONG_LUI, Tram, tram_khac_dang_giu

__all__ = [
    "CONG_MAC_DINH", "thu_muc_dau_tich", "duong_dau_tich", "duong_co_nhuong",
    "duong_log", "bo_log", "doc_dau_tich", "co_tram_dang_nghe", "dap_http",
    "tim_tram_dang_song", "xin_nhuong", "chay",
]

#: Log xoay kiểu đơn giản nhất — đầy thì xoá, ghi lại từ đầu (cùng nếp
#: `core/tu_chay._ghi_dong_log`). Trạm nền chạy hàng tuần không nghỉ, không
#: chốt trần là một ngày nào đó nó ăn hết đĩa của máy dựng.
GIOI_HAN_LOG_BYTE = 2 * 1024 * 1024

#: Bao lâu ngó tệp cờ "xin nhường" một lần. 2 giây: người vừa mở tool không
#: phải ngồi đợi, mà cũng không phải một vòng lặp bận.
NHIP_NGO_CO = 2.0

#: `xin_nhuong` chờ bản nền lui tối đa ngần này giây. Tắt một `ThreadingHTTPServer`
#: chỉ tốn vài trăm mili-giây; 8 giây là đã rộng rãi cho máy đang tải nặng.
CHO_NHUONG_GIAY = 8.0


# ── chỗ để dấu vết trên đĩa ──────────────────────────────────────────────────


def thu_muc_dau_tich(goc: str) -> str:
    return os.path.join(os.path.abspath(goc), "workspace", "tram-nen")


def duong_dau_tich(goc: str) -> str:
    """Tệp "bản nền đang chạy": `{pid, cong, luc}`.

    Có tệp KHÔNG chắc chắn là tiến trình còn sống (máy mất điện thì tệp nằm
    lại) — nên nơi nào cần chắc thì hỏi cổng bằng gói dò, đừng tin mỗi tệp.
    """
    return os.path.join(thu_muc_dau_tich(goc), "dang-chay.json")


def duong_co_nhuong(goc: str) -> str:
    """Tệp cờ: "có tệp này nghĩa là bản nền hãy lui, GUI đòi lại cổng"."""
    return os.path.join(thu_muc_dau_tich(goc), "xin-nhuong")


def duong_log(goc: str) -> str:
    return os.path.join(thu_muc_dau_tich(goc), "tram-nen.log")


def bo_log(goc: str, *, in_console: bool = True,
           gioi_han_byte: int = GIOI_HAN_LOG_BYTE) -> Callable[[str], None]:
    """Hàm ghi nhật ký cho tiến trình nền.

    Chạy bằng `pythonw.exe` thì KHÔNG có console — `sys.stdout` có thể là
    `None` và gọi `print()` lúc đó ném `AttributeError` giữa chừng. Tệp log
    trên đĩa là nơi DUY NHẤT đọc lại được đêm qua đã xảy ra gì (cùng lý lẽ
    với `core/tu_chay.bo_log_tat_ca`).
    """
    duong = duong_log(goc)

    def ghi(dong: str) -> None:
        try:
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            try:
                if os.path.getsize(duong) > gioi_han_byte:
                    os.remove(duong)
            except OSError:
                pass
            moc = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(duong, "a", encoding="utf-8") as tep:
                tep.write("[{0}] {1}\n".format(moc, dong))
        except OSError:
            pass  # ghi log hỏng không được phép giết cái trạm đang phục vụ
        if in_console and sys.stdout is not None:
            try:
                print(dong)
            except Exception:  # noqa: BLE001 — console vừa đóng thì kệ, đã ghi đĩa
                pass

    return ghi


def doc_dau_tich(goc: str) -> Dict[str, Any]:
    """Đọc tệp dấu tích. Không có / hỏng đều trả `{}` — không ném."""
    try:
        with open(duong_dau_tich(goc), "r", encoding="utf-8") as tep:
            gia_tri = json.load(tep)
    except (OSError, ValueError):
        return {}
    return gia_tri if isinstance(gia_tri, dict) else {}


def _ghi_dau_tich(goc: str, cong: int) -> None:
    try:
        os.makedirs(thu_muc_dau_tich(goc), exist_ok=True)
        with open(duong_dau_tich(goc), "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "cong": int(cong),
                       "luc": _dt.datetime.now().isoformat(timespec="seconds")},
                      tep, ensure_ascii=False)
    except OSError:
        pass


def _xoa(duong: str) -> None:
    try:
        os.remove(duong)
    except OSError:
        pass


# ── hỏi cổng: có trạm nào đang nghe không ────────────────────────────────────


def co_tram_dang_nghe(cong: int = CONG_MAC_DINH) -> bool:
    """Có MỘT TRẠM của tool đang nghe `cong` không (GUI hay nền đều tính).

    Hỏi bằng đúng gói dò UDP mà máy ảo dùng — im lặng nghĩa là không phải
    trạm. Một lớp mỏng quanh `tram.tram_khac_dang_giu`, để bài kiểm có chỗ
    thay đồ giả mà không phải vá vào mô-đun trạm.
    """
    return tram_khac_dang_giu(int(cong))


#: Mã kênh dùng cho lượt gõ cửa HTTP. Không trùng kênh thật nào, và đường
#: `/ke-hoach` chỉ ĐỌC một tệp CSV (xem `core/ke_hoach_dang.doc_van_ban`) —
#: gõ cửa không tạo thư mục, không ghi gì, không đẻ dòng nhật ký nào.
KENH_GO_CUA = "__canh-tram__"


def dap_http(cong: int, *, cho_giay: float = 5.0) -> bool:
    """Cổng HTTP có THẬT SỰ phục vụ không — hỏi đúng đường máy ảo hay hỏi.

    Khác `co_tram_dang_nghe`, và khác ở chỗ quan trọng: tai dò UDP chạy trong
    LUỒNG RIÊNG với máy chủ HTTP. Một trạm kẹt luồng HTTP (khoá chéo, đĩa treo)
    vẫn đáp `shopapi-tram?` ngon lành trong khi `vm/nguon_tool.py` gõ
    `/ke-hoach` thì câm. Chó giữ nhà mà chỉ tin gói dò thì đúng cảnh ấy nó báo
    "vẫn sống" — im lặng y như lúc chưa có chó giữ nhà.

    Bất cứ mã HTTP nào dưới 500 cũng tính là "có người phục vụ": 403 (cổng
    chặn) hay 404 nghĩa là máy chủ vẫn nghe và vẫn trả lời, chỉ là trả lời
    khác. Chỉ im lặng, nối hỏng, hay 5xx mới là chết.

    ═══ `http.client` CHỨ KHÔNG `urlopen` ═══

    Hai lý do, cả hai đều là lỗi thật chực chờ:

    * `urlopen` ĐỌC biến môi trường `HTTP_PROXY`. Máy dựng có đặt proxy là một
      lượt gõ cửa `127.0.0.1` bị đẩy vòng qua proxy, hỏng vô cớ — rồi chó giữ
      nhà kết luận trạm chết và bật thêm bản nữa.
    * `tests/test_mang_an_toan.py` cấm `urlopen` trần trong `core/` vì kho
      chứng chỉ của máy khách không đáng tin. Ở đây không có TLS nào để mà
      tin, nhưng luật là luật và `http.client` vốn hợp hơn cho một lượt gõ cửa
      localhost: không proxy, không chứng chỉ, không gì cả.
    """
    import http.client  # noqa: PLC0415

    noi = http.client.HTTPConnection("127.0.0.1", int(cong),
                                     timeout=float(cho_giay))
    try:
        noi.request("GET", "/ke-hoach?kenh=" + KENH_GO_CUA)
        return int(noi.getresponse().status) < 500
    except Exception:  # noqa: BLE001 — nối hỏng, quá giờ, trả lời rác: đều là "chết"
        return False
    finally:
        try:
            noi.close()
        except Exception:  # noqa: BLE001
            pass


def tim_tram_dang_song(cong: int = CONG_MAC_DINH, *,
                       so_lui: int = SO_CONG_LUI,
                       do: Callable[[int], bool] = co_tram_dang_nghe
                       ) -> Optional[int]:
    """Số cổng của trạm đang sống, hay `None` nếu không đâu trả lời.

    Vì sao phải dò cả dải chứ không chỉ 8765: `tram.bat()` được phép LÙI cổng
    (8765 → 8775) khi một thứ KHÔNG PHẢI trạm giữ mất cổng gốc — máy ảo vẫn
    tìm ra vì nó dò UDP chứ không đóng đinh số. Chó giữ nhà mà chỉ nhìn 8765
    thì sẽ tưởng trạm chết và đẻ thêm một bản nữa, mỗi 5 phút một con.
    """
    cong = int(cong)
    for buoc in range(max(1, int(so_lui) + 1)):
        if do(cong + buoc):
            return cong + buoc
    return None


# ── bắt tay nhường cổng ──────────────────────────────────────────────────────


def xin_nhuong(goc: str, *, cho_giay: float = CHO_NHUONG_GIAY,
               ngu: Callable[[float], None] = time.sleep,
               do_tram: Callable[[int], bool] = co_tram_dang_nghe
               ) -> Tuple[bool, str]:
    """GUI đòi lại cổng: bảo bản nền (nếu có) lui, rồi chờ nó lui xong.

    Trả `(đã có bản nền lui hay không, câu giải thích)`.

    ═══ HỎI CỔNG TRƯỚC, RỒI MỚI CHỜ ═══

    Hàm này chạy trên LUỒNG GIAO DIỆN (`core/khoi_dong_vps`), nên mỗi giây nó
    đứng chờ là một giây cửa sổ đơ. Mà ca hay gặp nhất lại đúng là ca tệ nhất:
    trạm nền bị giết ngang (máy mất điện, Task Manager) thì `dang-chay.json`
    nằm lại mà không còn ai đọc cờ — chờ đủ 8 giây cho một cái xác. Nên hỏi
    cổng bằng gói dò trước: không ai đáp thì đó là xác, dọn rồi về ngay.

    Dọn dẹp là phần quan trọng còn lại. Hai thứ có thể nằm lại:

    * **dấu tích cũ** — xoá đi, đừng để lần mở tool nào cũng đứng chờ cho một
      tiến trình đã chết từ tuần trước.
    * **cờ xin nhường** — nếu để lại, bản nền do chó giữ nhà bật lên sau đó sẽ
      thấy cờ và tự thoát ngay, thành ra trạm không bao giờ sống nổi. Nên cờ
      luôn bị xoá trước khi hàm này trả về, dù kết quả thế nào.
    """
    if not os.path.isfile(duong_dau_tich(goc)):
        return False, "không có bản trạm nền nào đang chạy"
    dau = doc_dau_tich(goc)
    try:
        cong_cu = int(dau.get("cong") or CONG_MAC_DINH)
    except (TypeError, ValueError):
        cong_cu = CONG_MAC_DINH
    if not do_tram(cong_cu):
        _xoa(duong_dau_tich(goc))
        return False, ("dấu tích cũ: không ai trả lời ở cổng {0}, coi như bản "
                       "nền đã chết — đã dọn".format(cong_cu))
    co = duong_co_nhuong(goc)
    try:
        os.makedirs(thu_muc_dau_tich(goc), exist_ok=True)
        with open(co, "w", encoding="utf-8") as tep:
            tep.write(_dt.datetime.now().isoformat(timespec="seconds"))
    except OSError as loi:
        return False, "không đặt được cờ xin nhường: {0}".format(loi)

    han = time.time() + max(0.0, float(cho_giay))
    try:
        while time.time() < han:
            if not os.path.isfile(duong_dau_tich(goc)):
                return True, "trạm nền đã lui, cổng trống cho giao diện"
            ngu(0.2)
    finally:
        _xoa(co)
    # Hết giờ. Hỏi lại lần nữa trước khi kết luận: còn tiếng đáp nghĩa là bản
    # nền vẫn sống, chỉ chậm — xoá dấu tích của một tiến trình đang chạy là tự
    # nói dối mình, lần đòi sau sẽ bảo "không có bản nền nào" trong khi cổng
    # vẫn bị giữ. Câm hẳn thì mới là xác, lúc ấy mới dọn.
    if do_tram(cong_cu):
        return False, ("trạm nền vẫn giữ cổng {0} sau {1:.0f} giây — giao diện "
                       "chưa lấy lại được cổng".format(cong_cu, cho_giay))
    _xoa(duong_dau_tich(goc))
    return False, ("trạm nền không lui sau {0:.0f} giây và cũng không còn trả "
                   "lời — coi như dấu tích cũ và đã dọn".format(cho_giay))


# ── đồ nghề của trạm khi chạy không có giao diện ─────────────────────────────


def _dia_chi_vps(goc: str) -> List[str]:
    """Địa chỉ các VPS đã lưu ở tab VPS — để trạm tự gọi sang giới thiệu mình.

    Bản GUI (`trang_chi_so_ytb._dia_chi_vps`) còn cộng thêm danh sách máy THUÊ
    lấy về từ máy chủ ShopAPI. Bản nền cố ý KHÔNG gọi mạng: nó phải bật được cả
    khi chưa đăng nhập, và danh sách máy riêng trên đĩa đã đủ cho việc bắt tay.
    """
    try:
        from core import vps as v  # noqa: PLC0415
        from core.vps_rieng import KhoVpsRieng  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — thiếu mô-đun thì thôi loa gọi, trạm vẫn nhận
        return []
    ra: List[str] = []
    try:
        for m in KhoVpsRieng(goc).doc():
            d = v.may_chu_rdp({"ket_noi": {"ipv6": m.dia_chi, "dia_chi": m.dia_chi}})
            if d:
                ra.append(d)
    except Exception:  # noqa: BLE001 — tệp hỏng thì danh sách rỗng, không chết trạm
        return []
    return list(dict.fromkeys(ra))


def _bo_viet_ho(goc: str) -> Callable[[str], str]:
    """Cửa `POST /van-ban`: viết chữ hộ máy ảo bằng ví của tool.

    Dựng client LƯỜI — chỉ lúc máy ảo hỏi thật mới đọc `config.json` và nối
    máy chủ. Chưa đăng nhập thì ném lỗi cho trạm trả 500, và bên máy ảo đã có
    sẵn đường lùi về Gemini dự phòng (xem `vm/` — cùng luật với bản GUI).
    """
    hop: Dict[str, Any] = {}

    def viet(de_bai: str) -> str:
        client = hop.get("client")
        if client is None:
            from core.api import build_client  # noqa: PLC0415
            from core.config import CONFIG_FILENAME, load_config  # noqa: PLC0415

            cau_hinh = load_config(os.path.join(goc, CONFIG_FILENAME))
            if cau_hinh.problem:
                raise RuntimeError("tool chưa đăng nhập được: " + cau_hinh.problem)
            client = hop["client"] = build_client(cau_hinh)
        from core.goi_van_ban import goi_van_ban  # noqa: PLC0415

        return goi_van_ban(client, [{"role": "user", "content": de_bai}])

    return viet


def _dung_tram(goc: str, cong: Optional[int], ghi: Callable[[str], None]) -> Tram:
    return Tram(goc=goc, ghi=ghi,
                nguon_khach=lambda: _dia_chi_vps(goc),
                goi_van_ban=_bo_viet_ho(goc),
                **({"cong": int(cong)} if cong is not None else {}))


# ── vòng đời ─────────────────────────────────────────────────────────────────


def chay(goc: str, cong: Optional[int] = None, *,
         ghi: Optional[Callable[[str], None]] = None,
         do_tram: Callable[[int], bool] = co_tram_dang_nghe,
         dung_tram: Callable[[str, Optional[int], Callable[[str], None]], Tram] = _dung_tram,
         nhip: float = NHIP_NGO_CO,
         dung_khi: Optional[Callable[[], bool]] = None) -> int:
    """Bật trạm nền và giữ tiến trình sống tới khi có người xin nhường.

    Trả mã thoát cho `sys.exit`: `0` là "không có gì sai" (kể cả khi tự nhường
    vì đã có trạm khác), `1` là "không mở được cổng".

    `dung_khi` là cửa cho bài kiểm: trả `True` thì vòng chờ dừng ngay — bài
    kiểm không phải ngồi đợi đồng hồ thật, và không tệp cờ nào phải tồn tại.
    """
    goc = os.path.abspath(goc)
    ghi = ghi or bo_log(goc)
    so_cong = CONG_MAC_DINH if cong is None else int(cong)

    # Cờ cũ còn nằm lại (lần nhường trước bị cắt ngang) thì xoá TRƯỚC khi bật —
    # không thì trạm vừa lên đã tự thấy cờ và lui, và chó giữ nhà cứ 5 phút lại
    # đẻ một con rồi mất một con, mãi mãi.
    _xoa(duong_co_nhuong(goc))

    if do_tram(so_cong):
        ghi("cổng {0} đã có một trạm của tool đang nghe — bản nền NHƯỜNG, không "
            "mở cổng thứ hai (một cổng một chủ, xem ui_qt/tram_chung.py)"
            .format(so_cong))
        return 0

    tram = dung_tram(goc, cong, ghi)
    try:
        tram.bat()
    except OSError as loi:
        ghi("không bật được trạm nền: {0}".format(loi))
        return 1

    _ghi_dau_tich(goc, tram.cong)
    ghi("trạm nền đang nghe cổng {0} (pid {1}) — không cần cửa sổ nào mở"
        .format(tram.cong, os.getpid()))
    try:
        _cho_toi_khi_nhuong(goc, ghi, nhip=nhip, dung_khi=dung_khi)
    finally:
        try:
            tram.tat()
        except Exception:  # noqa: BLE001 — tắt hụt thì thôi, tiến trình sắp chết
            pass
        _xoa(duong_dau_tich(goc))
        _xoa(duong_co_nhuong(goc))
    ghi("trạm nền đã dừng")
    return 0


def _cho_toi_khi_nhuong(goc: str, ghi: Callable[[str], None], *,
                        nhip: float = NHIP_NGO_CO,
                        dung_khi: Optional[Callable[[], bool]] = None) -> None:
    """Giữ tiến trình sống. Tỉnh dậy khi có cờ nhường, Ctrl+C, hay `dung_khi`.

    `Event.wait` chứ không `sleep` dày: nó tỉnh ngay lúc được gọi `set()`, nên
    một ngày nào đó thêm đường tắt từ bên ngoài thì không phải viết lại vòng.
    """
    nghi = threading.Event()
    co = duong_co_nhuong(goc)
    try:
        while True:
            if dung_khi is not None and dung_khi():
                ghi("có lệnh dừng từ nơi gọi — trạm nền lui")
                return
            if os.path.isfile(co):
                ghi("giao diện xin lại cổng — trạm nền lui, nhường cho bản GUI")
                return
            if nghi.wait(max(0.05, float(nhip))):
                return
    except KeyboardInterrupt:
        ghi("Ctrl+C — trạm nền lui")
