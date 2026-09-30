"""Chó giữ nhà cho trạm 8765: trạm chết thì bật lại, không đợi ai để ý.

═══ VÌ SAO KHÔNG CHỈ CẦN "BẬT TRẠM NỀN" LÀ XONG ═══

`core/tram_nen.py` tách được trạm ra khỏi cửa sổ Qt, nhưng nó vẫn chỉ là một
tiến trình — mà tiến trình nào cũng chết được: hết RAM, Windows Update khởi động
lại máy, một ngoại lệ lạ trong luồng ổ cắm. Trạm chết là `vm/nguon_tool.py` mất
đường lấy kế hoạch đăng (`GET /ke-hoach?kenh=X`) và video sản xuất xong nằm lại
trong thư mục — **không lỗi, không cảnh báo, không ai biết**. Đúng cảnh đo được
lúc 17:47 ngày 21/09/2026: `vm/agent.log` đầy `WinError 10061 … actively refused`
suốt nhiều giờ mà không ai hay.

Nên phải có một thứ ĐỨNG NGOÀI hỏi lại định kỳ: "cổng còn trả lời không?".

═══ AI CANH CHO CON CHÓ GIỮ NHÀ ═══

Câu hỏi thật của mọi watchdog. Câu trả lời ở đây: **Task Scheduler của Windows**.

`mot_luot()` là một lượt kiểm ĐƠN LẺ — hỏi, thấy chết thì bật lại, rồi thoát.
Lịch `ShopAPI-CanhTram` (xem `core/lich_tu_chay.dang_ky_canh_tram`) gọi nó mỗi
vài phút. Vòng lặp bền nhất là vòng lặp ta KHÔNG tự viết: Task Scheduler là dịch
vụ của hệ điều hành, nó sống lâu hơn mọi tiến trình Python của tool, và nó tự
chạy lại sau mỗi lần khởi động máy.

`canh()` (vòng lặp tự giữ, gọi qua `tram_nen.py --canh`) vẫn còn — tiện lúc gỡ
lỗi, hoặc cho máy không đặt lịch được — nhưng nó KHÔNG phải đường chính.

═══ HỎI BẰNG GÓI DÒ, KHÔNG BẰNG "CÓ TIẾN TRÌNH PYTHON NÀO KHÔNG" ═══

Câu hỏi đúng không phải "có tiến trình nào tên python đang chạy không" (máy dựng
lúc nào cũng có vài con) mà là "**có ai còn trả lời ở cổng 8765 không**". Hỏi
đúng bằng gói `shopapi-tram?` mà máy ảo dùng — cùng một câu hỏi, cùng một câu
trả lời. Trạm của GUI đáp thì cũng tính là sống: chó giữ nhà không phân biệt ai
đang phục vụ, nó chỉ quan tâm CÓ người phục vụ.

═══ KHÔNG ĐẺ ĐÀN ═══

Bật xong là CHỜ trạm lên tiếng rồi mới kết luận. Thiếu bước chờ này thì mỗi lượt
kiểm lại đẻ thêm một tiến trình (bản trước chưa kịp bind xong) — và bản thứ hai
tuy sẽ tự nhường (`tram_nen.chay` hỏi cổng trước khi mở), nhưng vẫn là rác.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Callable, List, Optional, Tuple

from . import tram_nen
from .chi_so_ytb.tram import CONG_MAC_DINH
from .loi_tat import _pythonw_cho  # cùng cách dò Python thật với core/lich_tu_chay

__all__ = ["TEN_KICH_BAN", "duong_kich_ban", "lenh_bat_tram_nen", "bat_tram_nen",
           "mot_luot", "canh", "NHIP_CANH_GIAY"]

#: Điểm vào chạy trạm nền, nằm ngay gốc thư mục tool (cạnh `tu_chay.py`).
TEN_KICH_BAN = "tram_nen.py"

#: Nhịp mặc định của `canh()` — vòng lặp tự giữ. Lịch Task Scheduler dùng phút
#: chứ không dùng con số này.
NHIP_CANH_GIAY = 120.0

#: Chờ trạm vừa bật lên tiếng tối đa ngần này giây. Bật `Tram` chỉ tốn chưa tới
#: một giây; 20 giây là chừa chỗ cho máy đang tải nặng và cho `pythonw` khởi
#: động lạnh (nạp Python + core/ lần đầu).
CHO_LEN_GIAY = 20.0

#: `[lệnh...] -> pid` (0 = không sinh được) — chỗ bài kiểm thay đồ giả, để không
#: bao giờ có một tiến trình thật nào mọc ra trong lượt chạy test.
SinhTienTrinh = Callable[[List[str]], int]


def duong_kich_ban(goc: str) -> str:
    return os.path.join(os.path.abspath(goc), TEN_KICH_BAN)


def lenh_bat_tram_nen(goc: str, cong: Optional[int] = None) -> List[str]:
    """Câu lệnh bật trạm nền: `pythonw tram_nen.py [--cong N]`.

    `pythonw.exe` chứ không `python.exe`: không cửa sổ đen nào chớp lên giữa
    đêm (cùng luật với `CHAY-GON.vbs` và `core/lich_tu_chay`). Dò đường Python
    bằng `_pythonw_cho` — gọi trần `pythonw` có thể trúng bản giả của Microsoft
    Store và máy chạy tốt cả tuần bỗng "Python was not found".
    """
    lenh = [_pythonw_cho(goc), duong_kich_ban(goc)]
    if cong is not None:
        lenh += ["--cong", str(int(cong))]
    return lenh


def _sinh_mac_dinh(lenh: List[str]) -> int:
    """Sinh một tiến trình SỐNG LÂU HƠN người gọi.

    `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`: lượt kiểm của Task Scheduler
    chạy xong là thoát ngay, mà trạm nền thì phải ở lại. Không tách ra thì con
    chết theo mẹ và chó giữ nhà thành ra vô dụng — cứ 5 phút bật một trạm sống
    được 5 giây.

    Cũng vì thế mà `stdin/stdout/stderr` đều trỏ vào hư vô: giữ lại tay cầm của
    tiến trình cha là giữ luôn sợi dây trói nó vào cha.
    """
    co = 0
    for ten in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"):
        co |= getattr(subprocess, ten, 0)
    try:
        con = subprocess.Popen(  # noqa: S603 — lệnh do chính tool dựng, không nhận từ ngoài
            lenh, close_fds=True, creationflags=co,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.path.dirname(lenh[1]) if len(lenh) > 1 else None)
    except (OSError, ValueError):
        return 0
    return int(con.pid or 0)


def bat_tram_nen(goc: str, cong: Optional[int] = None, *,
                 sinh: SinhTienTrinh = _sinh_mac_dinh) -> Tuple[bool, str]:
    """Bật một tiến trình trạm nền. Trả `(đã sinh được chưa, câu giải thích)`.

    KHÔNG kiểm cổng ở đây — đó là việc của `mot_luot`. Hàm này chỉ lo phần
    "gọi đúng lệnh"; bản thân `tram_nen.chay()` cũng tự hỏi cổng lần nữa trước
    khi mở, nên một lượt gọi thừa cũng không sinh ra trạm thứ hai.
    """
    kich_ban = duong_kich_ban(goc)
    if not os.path.isfile(kich_ban):
        return False, "không thấy {0} trong thư mục tool".format(TEN_KICH_BAN)
    pid = sinh(lenh_bat_tram_nen(goc, cong))
    if not pid:
        return False, "không sinh được tiến trình trạm nền"
    return True, "đã bật trạm nền (pid {0})".format(pid)


def mot_luot(goc: str, cong: int = CONG_MAC_DINH, *,
             do: Callable[[int], bool] = tram_nen.co_tram_dang_nghe,
             go_cua: Callable[[int], bool] = tram_nen.dap_http,
             sinh: SinhTienTrinh = _sinh_mac_dinh,
             cho_len_giay: float = CHO_LEN_GIAY,
             ngu: Callable[[float], None] = time.sleep,
             ghi: Optional[Callable[[str], None]] = None) -> Tuple[bool, str]:
    """MỘT lượt kiểm: trạm còn sống thì thôi, chết thì bật lại rồi chờ nó lên.

    Trả `(trạm có sống sau lượt này không, câu giải thích)`.

    Hai câu hỏi, không phải một. `do` (gói dò UDP) chỉ nói "cổng này có một
    trạm của tool" — rẻ, và là cách duy nhất tìm ra trạm đã LÙI cổng. `go_cua`
    (một lượt `GET /ke-hoach`) mới nói "nó có THẬT SỰ phục vụ không", vì hai
    thứ chạy ở hai luồng khác nhau và luồng HTTP kẹt được một mình.

    Trạm còn thở UDP mà câm HTTP thì KHÔNG bật thêm bản nào: cổng vẫn đang bị
    giữ, bản mới chỉ bind hỏng rồi chết. Lượt kiểm trả `False` để Task Scheduler
    ghi mã thoát khác 0 — hỏng mà NHÌN THẤY, thay vì im lặng.
    """
    goc = os.path.abspath(goc)
    ghi = ghi or tram_nen.bo_log(goc)

    dang_song = tram_nen.tim_tram_dang_song(cong, do=do)
    if dang_song is not None:
        if go_cua(dang_song):
            return True, "trạm đang sống ở cổng {0} — không phải làm gì".format(dang_song)
        ghi("cổng {0} còn đáp gói dò nhưng KHÔNG trả lời /ke-hoach — trạm kẹt "
            "luồng HTTP. Không bật thêm bản nào (cổng vẫn bị giữ); phải tắt tay "
            "tiến trình đang giữ cổng rồi để lượt kiểm sau bật lại."
            .format(dang_song))
        return False, ("trạm ở cổng {0} kẹt: đáp gói dò nhưng câm HTTP"
                       .format(dang_song))

    ghi("KHÔNG ai trả lời ở cổng {0} (và các cổng lùi) — máy ảo đang mất đường "
        "lấy kế hoạch đăng. Bật lại trạm nền.".format(cong))
    ok, loi_nhan = bat_tram_nen(goc, None if cong == CONG_MAC_DINH else cong, sinh=sinh)
    if not ok:
        ghi("bật lại HỎNG: " + loi_nhan)
        return False, loi_nhan

    han = time.time() + max(0.0, float(cho_len_giay))
    while time.time() < han:
        len_roi = tram_nen.tim_tram_dang_song(cong, do=do)
        if len_roi is not None and go_cua(len_roi):
            ghi("{0}, đã nghe được ở cổng {1}".format(loi_nhan, len_roi))
            return True, "{0}, đang nghe cổng {1}".format(loi_nhan, len_roi)
        ngu(1.0)
    ghi("{0} nhưng sau {1:.0f} giây vẫn chưa ai trả lời — xem {2}"
        .format(loi_nhan, cho_len_giay, tram_nen.duong_log(goc)))
    return False, "{0} nhưng trạm chưa lên tiếng".format(loi_nhan)


def canh(goc: str, cong: int = CONG_MAC_DINH, *,
         nhip: float = NHIP_CANH_GIAY, so_luot: Optional[int] = None,
         do: Callable[[int], bool] = tram_nen.co_tram_dang_nghe,
         go_cua: Callable[[int], bool] = tram_nen.dap_http,
         sinh: SinhTienTrinh = _sinh_mac_dinh,
         ngu: Callable[[float], None] = time.sleep,
         ghi: Optional[Callable[[str], None]] = None) -> int:
    """Vòng lặp tự giữ: kiểm mỗi `nhip` giây, mãi mãi (hay `so_luot` lượt).

    Đường phụ — đường chính là lịch Task Scheduler gọi `mot_luot` (xem đầu
    tệp). `so_luot` là cửa cho bài kiểm: chạy đúng mấy lượt rồi trả về.
    """
    goc = os.path.abspath(goc)
    ghi = ghi or tram_nen.bo_log(goc)
    ghi("chó giữ nhà bắt đầu canh cổng {0}, mỗi {1:.0f} giây một lượt"
        .format(cong, nhip))
    luot = 0
    try:
        while so_luot is None or luot < int(so_luot):
            luot += 1
            mot_luot(goc, cong, do=do, go_cua=go_cua, sinh=sinh, ngu=ngu, ghi=ghi)
            if so_luot is not None and luot >= int(so_luot):
                break
            ngu(max(1.0, float(nhip)))
    except KeyboardInterrupt:
        ghi("Ctrl+C — chó giữ nhà nghỉ")
    return 0
