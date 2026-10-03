"""Đặt lịch chạy `tu_chay.py --tat-ca` MỖI NGÀY bằng Task Scheduler của Windows.

═══ VÌ SAO CẦN TỆP NÀY ═══

`core/tu_chay.py` đã lo trọn một ngày cho MỘT kênh, và `tu_chay.py --tat-ca` lo
lần lượt MỌI kênh có `tu_chay: true`. Nhưng tới giờ vẫn phải có người tự tay mở
cửa sổ dòng lệnh chạy nó. Kế hoạch "kênh tự chạy 100%" (`vm/KE-HOACH-5-KENH.md`,
bước E: *"lịch 1 lần/ngày chạy tu_chay.py --tat-ca"*) cần một cái đồng hồ: VPS
bật lịch, tới giờ tự chạy, không ai bấm gì.

Windows đã có sẵn đồng hồ ấy — Task Scheduler (`schtasks.exe`). Mô-đun này chỉ
là một lớp bọc mỏng: DỰNG đúng câu lệnh, ĐỌC lại trạng thái, và HỦY khi khách
không muốn tự chạy nữa. Không tự viết bộ lập lịch riêng.

═══ CHẠY BẰNG `pythonw`, ĐÚNG NGƯỜI DÙNG, CHỈ KHI ĐÃ ĐĂNG NHẬP ═══

* `pythonw.exe` chứ không phải `python.exe` — không cửa sổ đen nào bật lên lúc
  2 giờ sáng không ai ngồi xem (cùng luật với `CHAY-GON.vbs`).
* KHÔNG khai `/RU`/`/RP` — bỏ trống thì `schtasks` mặc định chạy việc bằng
  CHÍNH người dùng đang đặt lịch, kiểu đăng nhập "chỉ khi đã đăng nhập", không
  cần lưu mật khẩu. Đúng thứ VPS cần: `secrets.json` mã hoá bằng DPAPI của
  Windows chỉ đọc được trong phiên đăng nhập của đúng người dùng đó — VPS phải
  ở trạng thái ĐANG ĐĂNG NHẬP (không log off) để việc chạy được, và đó là điều
  kiện có chủ đích chứ không phải thiếu sót.
* KHÔNG dựng "thư mục làm việc" qua `/TR` (kiểu `cmd /c cd /d ... && ...`) —
  `schtasks /Create` bản dòng lệnh không có cờ đặt "Start in" (chỉ có ở XML).
  Không cần bù: `tu_chay.py` tự tìm thư mục của chính nó bằng
  `os.path.dirname(os.path.abspath(__file__))` (biến `BASE_DIR` đầu tệp đó),
  không phụ thuộc thư mục hiện hành lúc bị gọi. Bọc qua `cmd.exe` chỉ thêm một
  cửa sổ đen chớp qua trước khi `pythonw` (vốn không cửa sổ) chạy — tốn công
  mà không được gì.

═══ PYTHON THẬT, KHÔNG PHẢI BẢN GIẢ WINDOWSAPPS ═══

Xem ghi chú đầu `CHAY-QT.bat`: gọi trần `python`/`pythonw` có thể trúng bản giả
của Microsoft Store (App execution alias) — máy chạy tốt qua đêm bỗng "Python
was not found". Tool ĐANG CHẠY để gọi `dang_ky()` đã tự vượt qua cửa đó rồi
(mở lên được nghĩa là đang chạy bằng `.venv` hoặc bằng Python thật đã dò được).
Nên dùng lại đúng cách dò của `core/loi_tat._pythonw_cho` (`.venv/Scripts/
pythonw.exe` trước, rồi `pythonw.exe` cạnh `sys.executable`, cuối cùng mới
`sys.executable`) thay vì gọi "pythonw" trần và cầu may.

═══ MỌI LỆNH HỆ THỐNG QUA MỘT CỬA (`chay_lenh`) ═══

CLAUDE.md luật 3: bài kiểm không được gọi mạng, và ở tệp này là không được gọi
`schtasks` thật (đổi lịch chạy thật của máy đang chạy test là chuyện không ai
muốn). Mọi hàm công khai nhận tham số `chay_lenh` — mặc định gọi `schtasks.exe`
thật, bài kiểm truyền đồ giả.

`schtasks` xuất theo BẢNG MÃ HỆ THỐNG, không phải UTF-8 (cùng sự cố đã ghi ở
`tests/test_giai_ma_lenh_he_thong.py` cho `netsh`/`tasklist`) — luôn khai
`encoding="utf-8", errors="replace"`.

═══ ĐỌC TRẠNG THÁI: CỘT THEO VỊ TRÍ, KHÔNG THEO TÊN ═══

`schtasks /Query /V /FO CSV` dịch TÊN cột theo ngôn ngữ Windows đang cài (máy
tiếng Việt ra "Lần chạy cuối" chứ không phải "Last Run Time"), nhưng THỨ TỰ cột
là cố định bất kể ngôn ngữ. `trang_thai()` thử so tên cột tiếng Anh trước (máy
Windows tiếng Anh, phần lớn VPS thuê ngoài); không khớp thì lùi về đúng VỊ TRÍ
cột theo lược đồ chuẩn của `schtasks` — máy Windows tiếng Việt vẫn đọc đúng.
"""

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import unicodedata
from typing import Callable, Dict, List, Optional, Tuple

from .loi_tat import _pythonw_cho  # dùng lại đúng cách dò Python thật, xem docstring trên

__all__ = ["TEN_VIEC", "TEN_VIEC_CANH", "TEN_VIEC_TRAM_DANG_NHAP",
           "dang_ky", "huy", "trang_thai",
           "dang_ky_canh_tram", "huy_canh_tram", "trang_thai_canh_tram",
           "TEN_VIEC_DIEU_PHOI", "dang_ky_dieu_phoi", "huy_dieu_phoi",
           "TEN_VIEC_GAC_TONG", "dang_ky_gac_tong", "huy_gac_tong",
           "trang_thai_gac_tong",
           "TEN_VIEC_DONG_BO_GIT", "dang_ky_dong_bo_git", "huy_dong_bo_git",
           "TEN_VIEC_NAO", "dang_ky_nao", "huy_nao"]

#: Tên việc trong Task Scheduler — một tool chỉ một việc, tìm/xoá/đọc lại bằng
#: đúng tên này. Đổi tên là bỏ rơi việc cũ đã đăng ký trên máy khách.
TEN_VIEC = "ShopAPI-TuChay"

#: Việc thứ hai: chó giữ nhà cho trạm 8765 (`core/canh_tram.py`). Lặp mỗi vài
#: phút — vòng lặp bền nhất là vòng lặp ta KHÔNG tự viết.
TEN_VIEC_CANH = "ShopAPI-CanhTram"

#: Việc thứ ba, bé tí: chạy ĐÚNG MỘT lượt kiểm ngay lúc đăng nhập, để quãng
#: trống sau khi máy khởi động lại không kéo dài tới `phut` phút.
TEN_VIEC_TRAM_DANG_NHAP = "ShopAPI-TramLucDangNhap"

#: `[lệnh...] -> (mã thoát, chữ in ra gộp stdout+stderr)` — chữ ký của seam.
ChayLenh = Callable[[List[str]], Tuple[int, str]]

_MAU_GIO = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

#: Vị trí cột (0-based) trong `schtasks /Query /V /FO CSV` — lược đồ chuẩn,
#: KHÔNG đổi theo ngôn ngữ Windows (chỉ có nhãn cột là dịch). Dùng khi so tên
#: cột tiếng Anh không khớp (máy Windows đã đổi ngôn ngữ hiển thị).
_VI_TRI_MAC_DINH = {"Last Run Time": 5, "Last Result": 6, "Start Time": 19}


def _chay_lenh_mac_dinh(lenh: List[str]) -> Tuple[int, str]:
    """Gọi một lệnh hệ thống THẬT, trả `(mã thoát, chữ in ra gộp cả hai luồng)`."""
    try:
        ra = subprocess.run(
            lenh, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as loi:
        return 1, str(loi)
    return ra.returncode, (ra.stdout or "") + (ra.stderr or "")


def _duong_tu_chay(goc: str) -> str:
    return os.path.join(os.path.abspath(goc), "tu_chay.py")


def _lenh_chay(goc: str) -> str:
    """Câu lệnh Task Scheduler sẽ gọi mỗi ngày — `pythonw tu_chay.py --tat-ca`.

    Bọc từng phần trong nháy kép: đường cài tool có thể có dấu cách (ví dụ
    `D:\\New folder\\...`), và đây là giá trị của `/TR` — Windows sẽ tự
    tách lại đúng chương trình/đối số theo cặp nháy kép này lúc việc chạy.
    """
    py = _pythonw_cho(goc)
    kich_ban = _duong_tu_chay(goc)
    return '"{0}" "{1}" --tat-ca'.format(py, kich_ban)


#: Bao lâu thử lại một lượt trong ngày (phút). 60 là cân giữa hai phía: đủ dày
#: để một đợt máy chủ bận qua đi là có lượt kế nhặt tiếp, đủ thưa để lượt lặp
#: không chen vào giữa lượt đang chạy (một video mất 2–4 giờ, và khoá độc quyền
#: sẽ chặn lượt chen — nên đây chỉ là chuyện đỡ tốn vài giây đọc sổ).
NHIP_THU_LAI_PHUT = 60

#: Lặp tới khi nào. `23:59` = hết ngày, rồi lượt DAILY hôm sau bắt đầu lại.
KEO_DAI_LAP = "23:59"


def dang_ky(goc: str, gio: str = "02:00", *,
           chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đăng ký (hoặc đăng ký LẠI) việc chạy `tu_chay.py --tat-ca` mỗi ngày lúc `gio`.

    Gọi lại nhiều lần là AN TOÀN — `/F` ghi đè việc cũ cùng tên, không sinh ra
    việc thứ hai chạy song song.
    """
    gio = (gio or "").strip()
    if not _MAU_GIO.match(gio):
        return False, "Giờ chạy phải theo dạng HH:MM (ví dụ 02:00) — nhận “{0}”.".format(gio)
    if not os.path.isfile(_duong_tu_chay(goc)):
        return False, "Không thấy tu_chay.py trong thư mục tool — không đặt lịch được."

    lenh = ["schtasks", "/Create", "/TN", TEN_VIEC, "/SC", "DAILY", "/ST", gio,
            # ═══ LẶP TRONG NGÀY = TỰ THỬ LẠI (22/09/2026) ═══
            #
            # Trước đây việc này chạy ĐÚNG MỘT LẦN lúc `gio`. Lượt ấy hỏng vì
            # chuyện tạm thời thì cả ngày nằm im, tới mai mới có lượt sau.
            #
            # Đã cắn thật chiều 22/09: nhà máy ảnh trả `503 engine_unavailable`
            # ("không có chỗ nào nhận việc"), lượt chạy đứng chờ tới khi tiến
            # trình bị tắt — ba kênh dừng ở 116/141, 100/108 và 0/172 ảnh, mất
            # cả buổi mà không ra video nào.
            #
            # Chủ dự án: *"tao mở tool máy này sẽ không bao giờ tắt và tao cũng
            # không vào nên tao muốn công việc tự fix tự retry"*.
            #
            # Lặp lại là đủ để tự chữa, và KHÔNG cần thêm một dòng logic nào
            # mới, vì `core/tu_chay.py` đã có sẵn cả ba lớp chặn:
            #   · khoá độc quyền `CHANNEL/<kênh>/tu-chay/.khoa` — lượt sau tới
            #     lúc lượt trước còn chạy thì thoát ngay, không chạy đôi;
            #   · `_tim_run_chua_xong` — nhặt đúng lượt dở (kể cả của hôm qua)
            #     và làm TIẾP, không mở video mới;
            #   · vân tay từng khâu — ảnh/clip đã có thì bỏ qua, tiền đã tiêu
            #     không tiêu lại.
            # Nên một lượt lặp khi mọi thứ đã xong chỉ tốn vài giây đọc sổ.
            "/RI", str(NHIP_THU_LAI_PHUT), "/DU", KEO_DAI_LAP,
            "/TR", _lenh_chay(goc), "/F"]
    ma, ra = chay_lenh(lenh)
    if ma != 0:
        return False, ("Không đặt được lịch tự chạy — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(không rõ, mã thoát {0})".format(ma)))
    return True, ("Đã đặt lịch: mỗi ngày {0} tool tự chạy mọi kênh có bật "
                  "“tu_chay”, và TỰ THỬ LẠI mỗi {1} phút tới hết ngày nếu lượt "
                  "trước chưa xong (máy chủ bận, mạng rớt, máy khởi động lại…). "
                  "Máy phải ở trạng thái ĐÃ ĐĂNG NHẬP thì việc mới chạy được."
                  ).format(gio, NHIP_THU_LAI_PHUT)


def _xoa_viec(ten_viec: str, chay_lenh: ChayLenh) -> Tuple[bool, bool]:
    """Xoá một việc theo tên. Trả `(xoá được / vốn không có, có thật sự xoá không)`.

    Tách ra vì từ 21/09/2026 tool có BA việc trong Task Scheduler (tự chạy, chó
    giữ nhà, một lượt kiểm lúc đăng nhập) — cùng một lẽ "chưa có thì không phải
    lỗi", chép ba lần là ba chỗ để lệch nhau.
    """
    ma, ra = chay_lenh(["schtasks", "/Delete", "/TN", ten_viec, "/F"])
    if ma == 0:
        return True, True
    chu = _bo_dau(ra)
    if "khong tim thay" in chu or "cannot find" in chu or "does not exist" in chu \
            or "khong ton tai" in chu:
        return True, False
    return False, False


def huy(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Bỏ lịch tự chạy. Chưa từng đăng ký (hoặc đã bị xoá tay) thì coi như xong,
    không phải lỗi — khách bấm "Tắt tự chạy" hai lần không nên thấy báo đỏ."""
    ma, ra = chay_lenh(["schtasks", "/Delete", "/TN", TEN_VIEC, "/F"])
    if ma == 0:
        return True, "Đã tắt lịch tự chạy — từ giờ không ai gọi tu_chay.py nữa cho tới khi bạn bật lại."
    chu = _bo_dau(ra)
    if "khong tim thay" in chu or "cannot find" in chu or "does not exist" in chu \
            or "khong ton tai" in chu:
        return True, "Chưa từng đặt lịch tự chạy — không có gì để tắt."
    return False, ("Không tắt được lịch tự chạy — Windows báo: {0}"
                   .format(ra.strip()[:300] or "(không rõ, mã thoát {0})".format(ma)))


def trang_thai(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh,
               ten_viec: str = TEN_VIEC) -> Dict[str, object]:
    """Đọc lại việc đã đăng ký chưa, giờ chạy, lần chạy cuối và kết quả lần đó.

    Trả `{"da_dang_ky": bool, "gio": str, "lan_chay_cuoi": str, "ket_qua_cuoi": str}`.
    Không đọc được (chưa đăng ký, `schtasks` hỏng) thì trả bộ giá trị rỗng —
    không ném lỗi, giao diện chỉ cần biết "chưa có" để hiện đúng nút bấm.

    `ten_viec` mặc định là việc tự chạy; `trang_thai_canh_tram` truyền tên việc
    chó giữ nhà vào đây — cùng một cách đọc CSV, cùng một bẫy tên cột dịch theo
    ngôn ngữ Windows.
    """
    rong: Dict[str, object] = {"da_dang_ky": False, "gio": "", "lan_chay_cuoi": "",
                               "ket_qua_cuoi": ""}
    ma, ra = chay_lenh(["schtasks", "/Query", "/TN", ten_viec, "/V", "/FO", "CSV"])
    if ma != 0:
        return rong
    hang = _doc_csv(ra)
    if len(hang) < 2:
        return rong
    tieu_de, du_lieu = hang[0], hang[-1]  # dòng cuối: việc lặp mỗi ngày chỉ có một dòng dữ liệu

    def cot(ten_cot: str) -> str:
        i = _tim_cot(tieu_de, ten_cot)
        if i is None:
            i = _VI_TRI_MAC_DINH.get(ten_cot)
        if i is None or not (0 <= i < len(du_lieu)):
            return ""
        return du_lieu[i].strip()

    gio = cot("Start Time")
    lan_chay_cuoi = cot("Last Run Time")
    if lan_chay_cuoi.upper() in ("N/A", "NEVER", ""):
        lan_chay_cuoi = ""
    return {
        "da_dang_ky": True,
        "gio": gio,
        "lan_chay_cuoi": lan_chay_cuoi,
        "ket_qua_cuoi": _dien_giai_ket_qua(cot("Last Result"), lan_chay_cuoi,
                                           ten_viec=ten_viec),
    }


# ── chó giữ nhà cho trạm 8765 ─────────────────────────────────────────────────
#
# ═══ VÌ SAO LẠI LÀ MỘT VIỆC LẶP CHỨ KHÔNG PHẢI MỘT TIẾN TRÌNH CANH ═══
#
# Một tiến trình canh cũng chết được như thứ nó canh — và lúc ấy không ai canh
# nó. Task Scheduler thì khác: nó là DỊCH VỤ của Windows, sống lâu hơn mọi tiến
# trình Python của tool và tự có lại sau mỗi lần khởi động máy. Nên việc đăng ký
# ở đây gọi `tram_nen.py --kiem` — MỘT lượt hỏi cổng rồi thoát — và để cái đồng
# hồ của hệ điều hành làm phần lặp.
#
# ═══ RÀNG BUỘC "PHẢI ĐÃ ĐĂNG NHẬP", VÀ ĐƯỜNG LÁCH ═══
#
# Mặc định (không `/RU`) việc chạy bằng chính người dùng đang đặt lịch, kiểu
# "chỉ khi đã đăng nhập" — xem ghi chú đầu tệp về DPAPI. Máy dựng hiện có
# `AutoAdminLogon=1` nên khởi động xong là đã đăng nhập sẵn, ràng buộc này
# trong thực tế không cắn. Nhưng nó CẮN THẬT ở hai ca: người bấm "Đăng xuất"
# (log off) thay vì chỉ đóng cửa sổ RDP, và máy khởi động lại mà autologon
# hỏng (đổi mật khẩu, chính sách nhóm).
#
# Đường lách: `du_chua_dang_nhap=True` → `/RU SYSTEM /RL HIGHEST` và dùng
# `ONSTART` thay cho `ONLOGON`. Việc chạy được cả khi màn hình đăng nhập còn
# đang khoá. Đánh đổi PHẢI biết trước:
#
#   · `secrets.json` mã hoá bằng DPAPI của người dùng — tài khoản SYSTEM KHÔNG
#     mở được. Trạm vẫn nhận số liệu và vẫn trả `/ke-hoach` bình thường (hai
#     việc ấy chỉ đụng tệp trong `CHANNEL/`), nhưng cửa `POST /van-ban` (viết
#     hộ bình luận bằng ví của tool) sẽ trả lỗi — bên máy ảo tự lùi về Gemini
#     dự phòng, đúng đường đã thiết kế sẵn.
#   · Tệp do SYSTEM ghi vào `CHANNEL/` mang chủ sở hữu khác; phần lớn trường
#     hợp vẫn đọc được, nhưng đây là thứ chưa đo trên máy thật.
#
# Vì hai đánh đổi ấy, mặc định vẫn là `False`. Ai cần thì bật có ý thức.


def _duong_tram_nen(goc: str) -> str:
    return os.path.join(os.path.abspath(goc), "tram_nen.py")


def _lenh_canh_tram(goc: str) -> str:
    """Câu lệnh cho `/TR`: `pythonw tram_nen.py --kiem`.

    Cùng luật nháy kép với `_lenh_chay` (đường cài có thể có dấu cách) và cùng
    cách dò Python thật (`_pythonw_cho`, tránh bản giả WindowsApps).
    """
    return '"{0}" "{1}" --kiem'.format(_pythonw_cho(goc), _duong_tram_nen(goc))


def dang_ky_canh_tram(goc: str, phut: int = 5, *,
                      luc_dang_nhap: bool = True,
                      du_chua_dang_nhap: bool = False,
                      chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đặt lịch chó giữ nhà: cứ `phut` phút kiểm trạm 8765 một lượt.

    Đăng ký HAI việc (gọi lại nhiều lần vẫn an toàn, `/F` ghi đè):

    * `ShopAPI-CanhTram` — `/SC MINUTE /MO <phut>`, cái đồng hồ thật.
    * `ShopAPI-TramLucDangNhap` — `/SC ONLOGON`, chạy đúng một lượt ngay lúc
      đăng nhập, để quãng trống sau khi máy khởi động lại không kéo tới `phut`
      phút. Tắt bằng `luc_dang_nhap=False`.

    Trả `(thành công, câu giải thích)`. Việc thứ hai hỏng KHÔNG làm hỏng cả
    lượt — cái đồng hồ 5 phút mới là thứ không thể thiếu.
    """
    try:
        phut = int(phut)
    except (TypeError, ValueError):
        phut = 0
    if not 1 <= phut <= 1439:
        return False, ("Nhịp kiểm phải từ 1 tới 1439 phút — nhận “{0}”."
                       .format(phut))
    if not os.path.isfile(_duong_tram_nen(goc)):
        return False, "Không thấy tram_nen.py trong thư mục tool — không đặt lịch được."

    tr = _lenh_canh_tram(goc)
    nhu_he_thong = ["/RU", "SYSTEM", "/RL", "HIGHEST"] if du_chua_dang_nhap else []
    lenh = (["schtasks", "/Create", "/TN", TEN_VIEC_CANH, "/SC", "MINUTE",
             "/MO", str(phut), "/TR", tr] + nhu_he_thong + ["/F"])
    ma, ra = chay_lenh(lenh)
    if ma != 0:
        return False, ("Không đặt được lịch canh trạm — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(không rõ, mã thoát {0})".format(ma)))

    them = ""
    if luc_dang_nhap:
        # ONSTART khi chạy bằng SYSTEM (không cần ai đăng nhập), ONLOGON khi
        # chạy bằng người dùng thường — ONLOGON + SYSTEM là vô nghĩa.
        kieu = "ONSTART" if du_chua_dang_nhap else "ONLOGON"
        ma2, ra2 = chay_lenh(["schtasks", "/Create", "/TN", TEN_VIEC_TRAM_DANG_NHAP,
                              "/SC", kieu, "/TR", tr] + nhu_he_thong + ["/F"])
        them = ("" if ma2 == 0 else
                " (lượt kiểm lúc {0} KHÔNG đặt được: {1})"
                .format("khởi động máy" if du_chua_dang_nhap else "đăng nhập",
                        ra2.strip()[:150] or "mã thoát {0}".format(ma2)))

    khi_nao = ("Việc chạy bằng tài khoản SYSTEM nên KHÔNG cần ai đăng nhập — "
               "đổi lại cửa “viết hộ bình luận” sẽ không mở được ví (xem ghi "
               "chú trong core/lich_tu_chay.py)."
               if du_chua_dang_nhap else
               "Máy phải ở trạng thái ĐÃ ĐĂNG NHẬP thì việc mới chạy được.")
    return True, ("Đã đặt lịch canh trạm: mỗi {0} phút kiểm cổng 8765 một lượt, "
                  "chết thì tự bật lại. {1}{2}").format(phut, khi_nao, them)


def huy_canh_tram(goc: str, *,
                  chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Bỏ cả hai việc canh trạm. Chưa từng đăng ký thì coi như xong, không lỗi."""
    da_xoa = []
    hong = []
    for ten in (TEN_VIEC_CANH, TEN_VIEC_TRAM_DANG_NHAP):
        ok, that_su = _xoa_viec(ten, chay_lenh)
        if not ok:
            hong.append(ten)
        elif that_su:
            da_xoa.append(ten)
    if hong:
        return False, ("Không tắt được lịch canh trạm: {0}. Thử mở Task "
                       "Scheduler xoá tay.".format(", ".join(hong)))
    if not da_xoa:
        return True, "Chưa từng đặt lịch canh trạm — không có gì để tắt."
    return True, ("Đã tắt lịch canh trạm ({0}). Từ giờ trạm 8765 chết thì "
                  "KHÔNG ai bật lại.".format(", ".join(da_xoa)))


def trang_thai_canh_tram(goc: str, *,
                         chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Dict[str, object]:
    """Trạng thái việc chó giữ nhà — cùng bộ khoá với `trang_thai()`."""
    return trang_thai(goc, chay_lenh=chay_lenh, ten_viec=TEN_VIEC_CANH)


# ── phụ trợ ───────────────────────────────────────────────────────────────────


def _doc_csv(chu: str) -> List[List[str]]:
    try:
        return [dong for dong in csv.reader(io.StringIO(chu)) if dong]
    except csv.Error:
        return []


def _tim_cot(tieu_de: List[str], ten: str) -> Optional[int]:
    ten = ten.strip().lower()
    for i, h in enumerate(tieu_de):
        if h.strip().lower() == ten:
            return i
    return None


def _bo_dau(chu: str) -> str:
    """Chữ thường, bỏ dấu — so khớp thô câu lỗi `schtasks` dù máy chạy ngôn ngữ nào."""
    chu = unicodedata.normalize("NFKD", chu or "")
    return "".join(c for c in chu if not unicodedata.combining(c)).lower()


def _dien_giai_ket_qua(ma: str, lan_chay_cuoi: str, *,
                       ten_viec: str = TEN_VIEC) -> str:
    if not lan_chay_cuoi:
        return "chưa chạy lần nào"
    ma = (ma or "").strip()
    if not ma:
        return ""
    try:
        so = int(ma, 0)  # "0", "1", hoặc dạng hex "0x1" mà schtasks đôi khi in
    except ValueError:
        return ma
    # Cùng một con số, hai nghĩa khác hẳn: với việc tự chạy, 0 là "mọi kênh
    # xong"; với chó giữ nhà, 0 chỉ là "sau lượt kiểm ấy đã có trạm phục vụ"
    # (xem mã thoát của `tram_nen.py --kiem`). Nói nhầm câu là đọc nhầm máy.
    if ten_viec in (TEN_VIEC_CANH, TEN_VIEC_TRAM_DANG_NHAP):
        if so == 0:
            return "trạm 8765 có người phục vụ (mã 0)"
        return "trạm 8765 KHÔNG ai trả lời sau lượt kiểm (mã thoát {0})".format(so)
    if so == 0:
        return "chạy xong, không kênh nào lỗi (mã 0)"
    return "có kênh lỗi hoặc dừng giữa chừng (mã thoát {0})".format(so)

# ── Bộ điều phối sản xuất song song (29/09/2026, `core/dieu_phoi.py`) ────────

#: Việc thứ tư: mỗi 10 phút một nhịp điều phối (`tu_chay.py --dieu-phoi`) —
#: sinh lượt sản xuất tách rời cho kênh thiếu kho đệm nhất khi còn làn API.
TEN_VIEC_DIEU_PHOI = "ShopAPI-DieuPhoi"


def dang_ky_dieu_phoi(goc: str, phut: int = 10, *,
                      chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đặt lịch `ShopAPI-DieuPhoi` (`/SC MINUTE /MO <phut>`, `/F` ghi đè).

    Nhịp chỉ ĐỌC đĩa và sinh tiến trình — không tốn ví, không việc nặng; tắt
    điều phối (`cai-dat.json: dieu_phoi: false`) thì mỗi nhịp thoát ngay."""
    try:
        phut = int(phut)
    except (TypeError, ValueError):
        phut = 0
    if not 1 <= phut <= 1439:
        return False, "Nhịp điều phối phải từ 1 tới 1439 phút — nhận “{0}”.".format(phut)
    if not os.path.isfile(_duong_tu_chay(goc)):
        return False, "Không thấy tu_chay.py trong thư mục tool — không đặt lịch được."
    tr = '"{0}" "{1}" --dieu-phoi'.format(_pythonw_cho(goc), _duong_tu_chay(goc))
    # Lệch 5 phút khỏi mốc :00 — lịch `ShopAPI-TuChay` (`--tat-ca`) chạy đúng :00,
    # hai nhịp cùng giây chỉ tổ tranh khoá kênh của nhau.
    import datetime as _dt  # noqa: PLC0415

    bat_dau = _dt.datetime.now() + _dt.timedelta(minutes=1)
    while bat_dau.minute % 10 != 5:
        bat_dau += _dt.timedelta(minutes=1)
    ma, ra = chay_lenh(["schtasks", "/Create", "/TN", TEN_VIEC_DIEU_PHOI, "/SC", "MINUTE",
                        "/MO", str(phut), "/ST", bat_dau.strftime("%H:%M"), "/TR", tr, "/F"])
    if ma != 0:
        return False, ("Không đặt được lịch điều phối — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(mã thoát {0})".format(ma)))
    return True, "Đã đặt lịch điều phối: mỗi {0} phút một nhịp.".format(phut)


def huy_dieu_phoi(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Gỡ lịch `ShopAPI-DieuPhoi` (không có thì coi như xong)."""
    ma, ra = chay_lenh(["schtasks", "/Delete", "/TN", TEN_VIEC_DIEU_PHOI, "/F"])
    if ma == 0:
        return True, "Đã gỡ lịch điều phối."
    return True, "Lịch điều phối không có sẵn — không cần gỡ ({0}).".format(ra.strip()[:120])


# ── Người gác tổng (29/09/2026 tối, V3 "CÁCH NỐI SAU" #1, `core/gac_tong.py`) ─
#
# Việc thứ năm: mỗi 15 phút chạy `python -m core.gac_tong --mot-luot` — MỘT
# lượt đọc đĩa, không tốn ví (`core.gac_tong.chup_trang_thai` chủ đích KHÔNG
# gọi mạng). Cùng nguyên tắc "PHẢI ĐÃ ĐĂNG NHẬP, KHÔNG /RU SYSTEM" của
# `dang_ky`/`dang_ky_canh_tram` ở trên: `core.bang_dieu_khien`/`core.kenh` mà
# `gac_tong` gọi qua CÓ THỂ chạm Chrome/màn hình gián tiếp trong tương lai —
# giữ nguyên tắc "cần DPAPI/màn hình/Chrome thì không SYSTEM" (xem
# `workspace/ban-va/2026-09-29-dot3-tin-cay/GHI-CHU.md` mục "CÁCH NỐI SAU" #1).

TEN_VIEC_GAC_TONG = "ShopAPI-GacTong"

#: Nhịp mặc định — kế hoạch V3 nói "mỗi 15 phút".
NHIP_GAC_TONG_PHUT = 15


def _duong_gac_tong_module(goc: str) -> str:
    """`python -m core.gac_tong` chạy bằng MODULE (`-m`), không phải đường
    tệp `.py` trực tiếp — `core/gac_tong.py` tự dò gốc tool qua
    `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` (xem
    `core/gac_tong.py::_main`), không phụ thuộc thư mục hiện hành lúc
    `schtasks` gọi (cùng lý do `_lenh_chay` ở trên không bọc `cmd /c cd /d`)."""
    return os.path.join(os.path.abspath(goc), "core", "gac_tong.py")


def _lenh_gac_tong(goc: str) -> str:
    return '"{0}" -m core.gac_tong --mot-luot'.format(_pythonw_cho(goc))


def dang_ky_gac_tong(goc: str, phut: int = NHIP_GAC_TONG_PHUT, *,
                     chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đặt lịch `ShopAPI-GacTong`: mỗi `phut` phút chạy MỘT lượt
    `python -m core.gac_tong --mot-luot` (`/SC MINUTE /MO <phut>`, `/F` ghi
    đè — gọi lại nhiều lần vẫn an toàn). `pythonw`, không cửa sổ, KHÔNG
    `/RU`/`/RP` (chạy bằng chính người dùng Administrator đang đăng nhập,
    xem ghi chú trên).

    `-m core.gac_tong` cần chạy với thư mục làm việc LÀ gốc tool (để
    `python -m` tìm thấy gói `core`) — dùng `/TR "<pythonw>" -m core.gac_tong
    --mot-luot` qua `cmd /c cd /d "<goc>" && ...` là cách DUY NHẤT `schtasks`
    dòng lệnh hỗ trợ "Start in" (xem ghi chú `_lenh_chay` ở trên: bản thân
    `tu_chay.py`/`tram_nen.py` né việc này bằng cách tự dò `BASE_DIR`, nhưng
    `python -m` thì bắt buộc phải đứng đúng thư mục trước khi gọi)."""
    try:
        phut = int(phut)
    except (TypeError, ValueError):
        phut = 0
    if not 1 <= phut <= 1439:
        return False, "Nhịp gác tổng phải từ 1 tới 1439 phút — nhận “{0}”.".format(phut)
    if not os.path.isfile(_duong_gac_tong_module(goc)):
        return False, "Không thấy core/gac_tong.py trong thư mục tool — không đặt lịch được."

    tr = 'cmd /c cd /d "{0}" && {1}'.format(os.path.abspath(goc), _lenh_gac_tong(goc))
    ma, ra = chay_lenh(["schtasks", "/Create", "/TN", TEN_VIEC_GAC_TONG, "/SC", "MINUTE",
                        "/MO", str(phut), "/TR", tr, "/F"])
    if ma != 0:
        return False, ("Không đặt được lịch gác tổng — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(không rõ, mã thoát {0})".format(ma)))
    return True, ("Đã đặt lịch gác tổng: mỗi {0} phút tự kiểm sự cố (đọc đĩa, "
                  "không tốn ví), ghi workspace/tinh-trang.json và tự sửa vài "
                  "ca rõ ràng (khoá chết, tiến trình treo). Máy phải ở trạng "
                  "thái ĐÃ ĐĂNG NHẬP thì việc mới chạy được.").format(phut)


def huy_gac_tong(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Bỏ lịch gác tổng. Chưa từng đăng ký thì coi như xong, không phải lỗi."""
    ok, that_su = _xoa_viec(TEN_VIEC_GAC_TONG, chay_lenh)
    if not ok:
        return False, "Không tắt được lịch gác tổng — thử mở Task Scheduler xoá tay."
    if not that_su:
        return True, "Chưa từng đặt lịch gác tổng — không có gì để tắt."
    return True, "Đã tắt lịch gác tổng — từ giờ không ai tự kiểm sự cố mỗi 15 phút nữa."


def trang_thai_gac_tong(goc: str, *,
                        chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Dict[str, object]:
    """Trạng thái việc gác tổng — cùng bộ đọc CSV với `trang_thai()`."""
    return trang_thai(goc, chay_lenh=chay_lenh, ten_viec=TEN_VIEC_GAC_TONG)


# ── Đồng bộ kho chung GitHub (30/09/2026, `core/dong_bo_git.py`) ────────────
#
# Việc thứ sáu: mỗi ngày một lượt `python -m core.dong_bo_git keo` vào giờ vắng
# (mặc định 03:40, khoá `dong_bo_git.gio` trong `cap-nhat.json`). Bật/tắt thật
# sự nằm ở khoá `dong_bo_git.tu_keo` — lịch có chạy mà khoá tắt thì thoát ngay.
# `keo` tự chờ khung :15–:45 + máy rảnh (tối đa `cho_toi_da_phut`), nên lịch
# chỉ cần một mốc/ngày. Cùng nguyên tắc "đã đăng nhập, không /RU SYSTEM" với
# `dang_ky_gac_tong` (khởi động lại giao diện cần đúng phiên người dùng).

TEN_VIEC_DONG_BO_GIT = "ShopAPI-DongBoGit"


def _lenh_dong_bo_git(goc: str) -> str:
    return '"{0}" -m core.dong_bo_git keo'.format(_pythonw_cho(goc))


def dang_ky_dong_bo_git(goc: str, gio: str = "03:40", *,
                        chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đặt lịch `ShopAPI-DongBoGit` (`/SC DAILY /ST <gio>`, `/F` ghi đè)."""
    gio = (gio or "").strip()
    if not _MAU_GIO.match(gio):
        return False, "Giờ phải theo dạng HH:MM (ví dụ 03:40) — nhận “{0}”.".format(gio)
    if not os.path.isfile(os.path.join(os.path.abspath(goc), "core", "dong_bo_git.py")):
        return False, "Không thấy core/dong_bo_git.py — không đặt lịch được."
    tr = 'cmd /c cd /d "{0}" && {1}'.format(os.path.abspath(goc), _lenh_dong_bo_git(goc))
    ma, ra = chay_lenh(["schtasks", "/Create", "/TN", TEN_VIEC_DONG_BO_GIT, "/SC", "DAILY",
                        "/ST", gio, "/TR", tr, "/F"])
    if ma != 0:
        return False, ("Không đặt được lịch đồng bộ kho — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(mã thoát {0})".format(ma)))
    return True, ("Đã đặt lịch: mỗi ngày {0} tool tự kéo bản mới từ kho chung (chỉ áp "
                  "khi cap-nhat.json bật dong_bo_git.tu_keo, trong khung :15–:45, lúc máy rảnh).").format(gio)


def huy_dong_bo_git(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Gỡ lịch `ShopAPI-DongBoGit` (chưa có thì coi như xong)."""
    ok, that_su = _xoa_viec(TEN_VIEC_DONG_BO_GIT, chay_lenh)
    if not ok:
        return False, "Không gỡ được lịch đồng bộ kho — thử mở Task Scheduler xoá tay."
    return True, ("Đã gỡ lịch đồng bộ kho." if that_su else "Chưa từng đặt lịch đồng bộ kho.")


# ── Bộ não (03/10/2026, `core/nao.py`) ───────────────────────────────────────
#
# Việc thứ bảy: mỗi sáng một phiên Claude Code "bộ não" (`python -m core.nao phien`) — đọc số, tự chấm các
# hành động cũ, rồi chỉnh hướng qua CLI an toàn. 04:10 = SAU lượt quét Studio 02:10–03:55, TRƯỚC sản xuất 05:00.
# Cùng nguyên tắc "đã đăng nhập, không /RU SYSTEM" với các việc khác (cần phiên người dùng để tìm claude).

TEN_VIEC_NAO = "ShopAPI-Nao"


def _lenh_nao(goc: str) -> str:
    return '"{0}" -m core.nao phien'.format(_pythonw_cho(goc))


def dang_ky_nao(goc: str, gio: str = "04:10", *,
                chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Đặt lịch `ShopAPI-Nao` (`/SC DAILY /ST <gio>`, `/F` ghi đè). Mỗi ngày chỉ một phiên (khoá + log ngày)."""
    gio = (gio or "").strip()
    if not _MAU_GIO.match(gio):
        return False, "Giờ phải theo dạng HH:MM (ví dụ 04:10) — nhận “{0}”.".format(gio)
    if not os.path.isfile(os.path.join(os.path.abspath(goc), "core", "nao.py")):
        return False, "Không thấy core/nao.py — không đặt lịch bộ não được."
    tr = 'cmd /c cd /d "{0}" && {1}'.format(os.path.abspath(goc), _lenh_nao(goc))
    ma, ra = chay_lenh(["schtasks", "/Create", "/TN", TEN_VIEC_NAO, "/SC", "DAILY",
                        "/ST", gio, "/TR", tr, "/F"])
    if ma != 0:
        return False, ("Không đặt được lịch bộ não — Windows báo: {0}"
                       .format(ra.strip()[:300] or "(mã thoát {0})".format(ma)))
    return True, "Đã đặt lịch: mỗi ngày {0} một phiên bộ não (Claude Code đọc số, tự chấm, chỉnh hướng).".format(gio)


def huy_nao(goc: str, *, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """Gỡ lịch `ShopAPI-Nao` (chưa có thì coi như xong)."""
    ok, that_su = _xoa_viec(TEN_VIEC_NAO, chay_lenh)
    if not ok:
        return False, "Không gỡ được lịch bộ não — thử mở Task Scheduler xoá tay."
    return True, ("Đã gỡ lịch bộ não." if that_su else "Chưa từng đặt lịch bộ não.")
