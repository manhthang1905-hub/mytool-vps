"""MyTool đang chạy trên VPS, cạnh chính thư mục `vm/` nó phải nuôi.

═══ KIẾN TRÚC (chốt ở `vm/KE-HOACH-5-KENH.md`, bước E) ═══

Trên VPS, thứ DUY NHẤT hiện ra màn hình là MyTool đầy đủ (bản Studio này).
`vm/` có thể nằm ngay BÊN TRONG MyTool để cả máy chỉ cần một thư mục; bản cài
cũ đặt `vm/` cạnh MyTool vẫn được đọc để nâng cấp không làm gián đoạn máy.

Dấu hiệu là một tệp `vps.json` NẰM NGAY TRONG thư mục MyTool (cạnh
`shopapi_studio_qt.py`)::

    {"vm_dir": "vm", ...}

Bộ cài (`vm/cai_dat_vps.py`, việc của một phiên khác) ghi tệp này một lần lúc
cài; mọi thứ trong tệp này CHỈ ĐỌC, không ghi.

Không import Qt — module này chạy sớm trong `main()` của
`shopapi_studio_qt.py`, kể cả khi PyQt5 hỏng, và cũng phải test được không
cần dựng cửa sổ nào.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Sequence, Tuple

__all__ = ["TEN_MARKER", "la_vps", "doc", "thu_muc_vm", "trang_mo_dau",
           "loc_trang", "gioi_han_song_song", "gioi_han_theo_loai",
           "TRANG_VPS", "KHOA_TRANG_VPS", "KHOA_TRANG_TRUNG_TAM",
           "NHOM_VPS", "TRANG_NANG_CAO"]

#: Tên tệp dấu hiệu, nằm cạnh `shopapi_studio_qt.py`.
TEN_MARKER = "vps.json"

#: Khoá trang mở đầu khi ở chế độ VPS — một màn Kênh duy nhất.
KHOA_TRANG_TRUNG_TAM = "tong-quan"


def _duong_marker(goc: str) -> str:
    return os.path.join(goc, TEN_MARKER)


def la_vps(goc: str) -> bool:
    """Máy này có đang chạy MyTool ở "chế độ VPS" không — chỉ nhìn tệp có
    mặt hay không, không đọc nội dung (đọc hỏng thì việc khác lo, câu hỏi
    của hàm này chỉ là "có" hay "không")."""
    try:
        return os.path.isfile(_duong_marker(goc))
    except OSError:
        return False


#: Trần mặc định cho lớp "api" khi `workspace/cai-dat.json` chưa có khoá
#: `tran_api_vps`, hay tệp hỏng/thiếu. Xem `gioi_han_song_song`.
_TRAN_API_VPS_MAC_DINH = 6
#: Kẹp `tran_api_vps` trong khoảng này — 0 hay âm là tự khoá máy, một số quá
#: lớn gõ nhầm (vd "600") là lại giẫm vào đúng lỗi Đợt 1 sửa.
#:
#: ═══ 8 → 48 NGÀY 30/09/2026 ═══
#:
#: Trần 8 cũ gộp hai thứ khác hẳn nhau làm một: số job CHỜ máy chủ (luồng nằm
#: trên `Event`, vài MB, không CPU) và số luồng TẢI/GIẢI MÃ kết quả về đĩa (thứ
#: thật sự ăn RAM/băng thông). Nay hai thứ tách ra: số tải/giải mã có trần riêng
#: (`core/auto_khau.py::_tran_luong_cuc_bo` + `core/bang_thong.py`), nên trần ở
#: đây chỉ còn là số job chờ — 48 khớp `auto_khau.TRAN_LUONG_MAY` (mốc đo
#: 15/08/2026: 48 job cùng lúc nhanh nhất, 117 thì chậm gấp bốn).
_TRAN_API_VPS_MIN, _TRAN_API_VPS_MAX = 1, 48


def _tran_api_vps(goc: str) -> int:
    """Đọc `tran_api_vps` từ `workspace/cai-dat.json`. Mặc định 6, kẹp 1..48.

    Đọc trực tiếp, không qua `core.cai_dat` — module này chủ ý không kéo theo
    module `core` nào khác (xem ghi chú đầu tệp: phải chạy được sớm, không Qt,
    không phụ thuộc gì hỏng là cả tool không mở lên được). Tệp thiếu, hỏng,
    thiếu khoá, hay khoá không phải số đều lặng lẽ lùi về mặc định — một tệp
    cài đặt gõ tay sai không được phép làm khâu sản xuất chết cứng.
    """
    try:
        with open(os.path.join(goc, "workspace", "cai-dat.json"), "r",
                 encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return _TRAN_API_VPS_MAC_DINH
    if not isinstance(du, dict):
        return _TRAN_API_VPS_MAC_DINH
    try:
        gia_tri = int(du.get("tran_api_vps", _TRAN_API_VPS_MAC_DINH))
    except (TypeError, ValueError):
        return _TRAN_API_VPS_MAC_DINH
    return max(_TRAN_API_VPS_MIN, min(_TRAN_API_VPS_MAX, gia_tri))


def gioi_han_song_song(goc: str, so_luong: int, lop: str = "nang") -> int:
    """Giới hạn số việc song song khi chạy trên VPS, theo LỚP việc.

    Đây là chính sách toàn máy, không phải một tuỳ chọn giao diện. Nhờ vậy cấu
    hình cũ, nút chạy tay hay giới hạn máy chủ cao cũng không thể vô tình làm
    nhiều Chrome/FFmpeg/video cùng tranh RAM trên VPS 24/7.

    ═══ HAI LỚP (chốt ở `workspace/LO-TRINH-PHAT-HANH-V3.md`, "Luật điều phối") ═══

    * ``"nang"`` (mặc định, HÀNH VI CŨ giữ nguyên) — Chrome, FFmpeg, Whisper:
      việc ăn CPU/RAM của chính máy này. Trên VPS luôn ép về 1, bất kể
      `so_luong` xin bao nhiêu — nhiều việc nặng cùng lúc từng làm VPS cạn RAM
      (xem `CLAUDE.local.md`, sự cố 26/09/2026).
    * ``"api"`` — việc chỉ CHỜ máy chủ ShopAPI trả kết quả (ảnh, clip, giọng
      đọc, kịch bản…), không ăn CPU cục bộ trong lúc chờ, nên chạy song song
      không tranh tài nguyên máy như việc "nang". Trên VPS được phép chạy tới
      `tran_api_vps` (`workspace/cai-dat.json`, mặc định 6, kẹp 1..48) thay
      vì bị ép về 1 — đây là nút thắt số 1 mà Đợt 1 mục 1.1 gỡ. Đây là số job
      CHỜ máy chủ của MỘT kênh; tổng cả máy còn một trần nữa
      (`core/khe.py::giu_job`, khoá `tran_api_tong`, và trần động của
      `GET /v1/me`).

      Mở song song lớp "api" KHÔNG được làm nhịp hỏi job dày hơn: mọi nơi gọi
      đều đã dùng chung một `SoTheoDoi` (một luồng nền hỏi `GET /v1/jobs` mỗi
      ~30 giây cho cả mẻ — xem `core/auto_khau.py::SoTheoDoi`) chứ không phải
      mỗi luồng tự hỏi, nên tăng số luồng ở đây không tăng số lượt hỏi máy
      chủ. Số luồng TẢI kết quả về đĩa vẫn có trần riêng
      (`core/auto_khau.py::_tran_luong_cuc_bo`, ≤ RAM/CPU máy) — hàm này chỉ
      quyết định số việc *xin phép chạy song song*, không mở thêm đường lên
      nào chưa có sẵn trần.
    """
    try:
        n = max(1, int(so_luong))
    except (TypeError, ValueError):
        n = 1
    if not (goc and la_vps(goc)):
        return n
    if lop == "api":
        return min(n, _tran_api_vps(goc))
    return 1


def gioi_han_theo_loai(goc: str, cac_loai: Dict[str, int],
                       lop: str = "nang") -> Dict[str, int]:
    """Áp chính sách tuần tự cho bảng ``loại job -> sức chứa``."""
    return {k: gioi_han_song_song(goc, v, lop=lop) for k, v in cac_loai.items()}


def doc(goc: str) -> Dict[str, Any]:
    """Đọc `vps.json`. Không có tệp, hay tệp hỏng, đều trả về `{}` —
    đường khởi động không được ném lỗi vì một tệp cấu hình xấu."""
    try:
        with open(_duong_marker(goc), "r", encoding="utf-8") as tep:
            gia_tri = json.load(tep)
    except (OSError, ValueError):
        return {}
    return gia_tri if isinstance(gia_tri, dict) else {}


def thu_muc_vm(goc: str) -> str:
    """Thư mục `vm/` anh em mà máy này phải giám sát — đã kiểm tồn tại.

    Ném `FileNotFoundError` khi không ở chế độ VPS, thiếu khoá `vm_dir`,
    hay đường dẫn đó không còn là một thư mục (bị xoá, đổi tên, ổ đĩa rớt).
    Nơi gọi (móc khởi động) tự bọc `try/except` — lỗi ở đây không được
    chặn tool mở lên, chỉ là giám sát không bật được.
    """
    du = doc(goc)
    vm_dir = str(du.get("vm_dir") or "").strip()
    if not vm_dir:
        raise FileNotFoundError(
            "vps.json không có 'vm_dir' — bộ cài VPS chưa ghi xong hoặc tệp hỏng")
    # Đường tương đối luôn tính từ chính MyTool, không phụ thuộc thư mục hiện
    # hành của shortcut / Task Scheduler. Nhờ vậy cả thư mục MyTool có thể
    # được chuyển ổ hoặc đổi tên mà `vps.json` không hỏng.
    if not os.path.isabs(vm_dir):
        vm_dir = os.path.abspath(os.path.join(goc, vm_dir))
    if not os.path.isdir(vm_dir):
        raise FileNotFoundError(
            "vm_dir trong vps.json không phải thư mục đang có: {0}".format(vm_dir))
    return vm_dir


def trang_mo_dau(goc: str) -> Optional[str]:
    """Trang mở đầu khi MyTool chạy ở chế độ VPS, hay `None` để giữ mặc
    định thường (`CuaSoChinh.TRANG_DAU`).

    Thuần đọc — vỏ Qt (`ui_qt/app.py`, việc của một phiên khác) là nơi
    thật sự dùng giá trị này để chọn trang mở đầu.
    """
    return KHOA_TRANG_TRUNG_TAM if la_vps(goc) else None


#: ═══ BẢY TRANG: "Bảng điều khiển" hằng ngày + sáu trang quy trình gập lại ═══
#:
#: Thiết kế lại 29/09/2026 (`workspace/THIET-KE-BANG-DIEU-KHIEN.md`, Việc 2):
#: mở tool phải trả lời "kênh có ổn không / tôi cần làm gì / kết quả ra sao"
#: trong 5 giây — đó là "tong-quan" (nay là `TrangBangDieuKhien`, đứng riêng
#: nhóm "HẰNG NGÀY"). Sáu trang cũ theo quy trình (xem toàn cảnh → nghiên cứu →
#: chọn content → sản xuất → đăng/chăm → cài đặt) không mất tính năng nào,
#: chỉ gập vào nhóm "Nâng cao" trên thanh bên (`TRANG_NANG_CAO`,
#: `ui_qt/app.py::ThanhBen`).
#:
#: Khoá "tong-quan" GIỮ NGUYÊN (trang mở đầu/test/hướng dẫn không đổi khoá) dù
#: lớp dựng ra nó đổi từ `TrangTongQuanVps` sang `TrangBangDieuKhien` — số liệu
#: kênh cũ (bảng "Tình hình từng kênh") dời sang khoá mới "so-lieu-vps".
#:
#: Tab "VPS" (`chrome-sạch` → `ui_qt/trang_vps.py`) vẫn bị bỏ: nó dùng để thuê
#: máy ảo rồi Remote Desktop vào máy, nên vô nghĩa khi đang ngồi ngay trên VPS.
#: Phần trạm 8765 và tiện ích vẫn nằm trong `Hệ thống`.
#:
#: Bớt trang ở đây cũng bớt việc lúc mở tool vì `_dung_cac_trang()` dựng mọi
#: trang có trong thanh bên ngay lúc khởi động.
TRANG_VPS = (
    ("tong-quan", "", "Bảng điều khiển"),
    ("so-lieu-vps", "", "Số liệu kênh"),
    ("nghien-cuu-vps", "", "Nghiên cứu"),
    ("chon-content-vps", "", "Chọn nội dung"),
    ("san-xuat-vps", "", "Sản xuất"),
    ("dang-cham-soc-vps", "", "Lịch đăng"),
    # Viết MỘT dấu `&`, y như mọi nhãn khác trong `ui_qt.app.TRANG`: Qt coi `&`
    # trong nhãn nút là phím tắt và giấu nó đi, nên `ThanhBen` tự nhân đôi lúc
    # dựng nút. Nhân đôi sẵn ở đây là nhân đôi hai lần → hiện ra "Máy && Ví".
    ("he-thong", "", "Cài đặt"),
)

#: Khoá của bảy trang trên — để nơi khác hỏi "khoá này có ở chế độ VPS không".
KHOA_TRANG_VPS = tuple(muc[0] for muc in TRANG_VPS)

#: Tiêu đề nhóm trên thanh bên VPS: chỉ "Bảng điều khiển" có tiêu đề riêng —
#: sáu trang còn lại đứng dưới nút gập "Nâng cao ▸/▾" (`ThanhBen`, `gap=`),
#: không có tiêu đề nhóm nào khác (khác máy nhà, xem `ui_qt.app.NHOM_TRANG`).
NHOM_VPS = {"tong-quan": "HẰNG NGÀY"}

#: Sáu trang gập trong nhóm "Nâng cao" — mọi khoá của `TRANG_VPS` trừ
#: "tong-quan". Thứ tự giữ ĐÚNG thứ tự trong `TRANG_VPS` (quy trình vận hành).
TRANG_NANG_CAO = tuple(k for k in KHOA_TRANG_VPS if k != KHOA_TRANG_TRUNG_TAM)


def loc_trang(
    goc: str, trang: Sequence[Tuple[str, str, str]]
) -> Tuple[Tuple[str, str, str], ...]:
    """Danh sách trang thanh bên: sáu trang VPS, hay nguyên danh sách máy nhà.

    Nhận `trang` thay vì tự đọc `ui_qt.app.TRANG` để module này (không được
    import Qt) khỏi phải kéo theo `ui_qt` — nơi gọi (`CuaSoChinh.__init__`)
    tự truyền `self.TRANG_SAN_PHAM` vào.

    Ở chế độ VPS hàm này **thay** danh sách chứ không lọc nó: sáu trang VPS là
    các vỏ gom theo quy trình, không phải các mục có sẵn trong `ui_qt.app.TRANG` (thêm
    chúng vào đó là máy nhà cũng mọc các tab thừa).
    """
    if not la_vps(goc):
        return tuple(trang)
    return tuple(TRANG_VPS)
