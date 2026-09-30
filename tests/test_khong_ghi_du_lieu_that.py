"""Lưới an toàn cuối: KHÔNG bài kiểm nào được đụng vào dữ liệu THẬT của VPS.

Kiểm toán 29/09/2026 (Đợt 0.2 cô lập test): đo được hơn 1.167 dòng
"vm-thu"/"pytest-of" lẫn vào `vm/agent.log` THẬT — nhật ký chủ dự án đọc mỗi
sáng để biết đêm qua máy ảo làm gì (có dòng ngay trong ngày kiểm toán, 12:39).
Thủ phạm: một số bài trong `tests/test_vm_agent.py` nạp `vm/agent.py` bằng
`importlib` thẳng từ đường dẫn thật nhưng QUÊN tự bẻ `agent.GOC` sang
`tmp_path` — mọi lượt `ghi()`/`_luu_trang_thai()` sau đó rơi thẳng vào đĩa
thật (xem lịch sử tương tự đã vá 22/09/2026 ở `test_loi_thoai_trinh_duyet.py`).

Vá THẬT (không phải bài này): `vm/agent.py` đọc biến môi trường
`SHOPAPI_VM_GOC` ngay lúc module chạy; `tests/conftest.py` (fixture autouse
`_co_lap_vm_agent_goc`) đặt biến đó về một `tmp_path` cho MỌI bài — kể cả bài
quên tự bẻ `GOC`. Bài NÀY chỉ đứng canh: chụp mtime + hash bốn tệp trạng thái
THẬT của VPS trước/sau khi nạp `vm/agent.py` KHÔNG bẻ gì cả (đúng kiểu bài đã
quên) và gọi các hàm ghi của nó — bốn tệp phải NGUYÊN VẸN. Ai lỡ xoá fixture
kia, hay đổi `vm/agent.py` để không còn đọc biến môi trường nữa, bài này đỏ
NGAY tại đây thay vì lộ ra ở nhật ký thật hôm sau.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Bốn tệp trạng thái THẬT nêu trong kiểm toán — mọi thứ agent hoặc
#: `core.tien_trinh_con` có thể lỡ tay ghi vào khi một bài kiểm quên cô lập.
_DUONG_THAT = {
    "agent.log": os.path.join(GOC_KHO, "vm", "agent.log"),
    "trang-thai.json": os.path.join(GOC_KHO, "vm", "trang-thai.json"),
    "tien-trinh-con.json": os.path.join(GOC_KHO, "workspace", "tien-trinh-con.json"),
    "khoa-may": os.path.join(GOC_KHO, "workspace", "tu-chay", ".khoa-may"),
}


def _chup(duong_theo_ten: dict) -> dict:
    """`{tên: (mtime_ns, sha256) | None}` — `None` = tệp chưa tồn tại (bình
    thường trên máy dev sạch; bài vẫn kiểm được vì so sánh chụp-với-chụp,
    không đòi tệp phải có sẵn)."""
    ket_qua = {}
    for ten, duong in duong_theo_ten.items():
        try:
            mtime_ns = os.stat(duong).st_mtime_ns
            with open(duong, "rb") as tep:
                bam = hashlib.sha256(tep.read()).hexdigest()
            ket_qua[ten] = (mtime_ns, bam)
        except OSError:
            ket_qua[ten] = None
    return ket_qua


def _nap_agent_KHONG_be_goc():
    """Y HỆT một bài kiểm ĐÃ QUÊN cô lập: nạp thẳng `vm/agent.py` từ đường
    dẫn thật, không `monkeypatch.setattr(agent, "GOC", ...)` gì cả. Lưới an
    toàn PHẢI đến từ fixture autouse trong `conftest.py`, không phải từ bài
    kiểm tự giác — nếu bài phải tự bẻ `GOC` thì lưới không còn tác dụng cho
    bài THẬT SỰ quên (đúng như 4 bài từng quên trong `TestAgentGoiVe`)."""
    duong = os.path.join(GOC_KHO, "vm", "agent.py")
    spec = importlib.util.spec_from_file_location("vm_agent_khong_be_goc", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_autouse_da_dat_bien_moi_truong(monkeypatch):
    """Chốt tiền đề: nếu fixture `_co_lap_vm_agent_goc` biến mất khỏi
    `conftest.py`, bài này đỏ ở ĐÂY — rõ ràng hơn nhiều so với việc đỏ ở bài
    dưới (mà lý do thật có thể bị hiểu nhầm là do mã `agent.py`)."""
    assert os.environ.get("SHOPAPI_VM_GOC"), (
        "thiếu SHOPAPI_VM_GOC — fixture autouse _co_lap_vm_agent_goc trong "
        "tests/conftest.py đã bị xoá hoặc không còn chạy")


def test_agent_quen_be_goc_van_khong_dung_toi_dia_that():
    truoc = _chup(_DUONG_THAT)

    agent = _nap_agent_KHONG_be_goc()
    # `GOC` phải đến từ biến môi trường (fixture autouse), TUYỆT ĐỐI không
    # phải thư mục `vm/` thật — đây là điều kiện để phần còn lại của bài có
    # ý nghĩa (nếu dòng này đỏ thì lưới an toàn đã hỏng TỪ GỐC).
    duong_vm_that = os.path.join(GOC_KHO, "vm")
    assert os.path.normcase(os.path.normpath(agent.GOC)) != os.path.normcase(
        os.path.normpath(duong_vm_that)), (
        "agent.GOC vẫn trỏ vào vm/ THẬT — SHOPAPI_VM_GOC không có hiệu lực")

    # Y hệt việc `TestAgentGoiVe` từng làm mà quên cô lập: ghi nhật ký + lưu
    # trang-thai.json bằng đúng những hàm ghi thật của agent.
    agent.ghi("dòng thử — test_khong_ghi_du_lieu_that, không được rơi vào đĩa thật")
    agent._luu_trang_thai({"kenh": "KENH-MA-GIA-CUA-BAI-KIEM"},
                          quet_cuoi="2026-09-29T00:00:00")

    # Lượt ghi ở trên PHẢI thật sự xảy ra — chỉ là phải rơi vào tmp_path
    # (qua SHOPAPI_VM_GOC), không phải rơi vào đĩa thật.
    assert os.path.isfile(agent._duong_nhat_ky())
    assert os.path.isfile(agent._duong_trang_thai({}))

    sau = _chup(_DUONG_THAT)
    assert sau == truoc, (
        "một hoặc nhiều tệp trạng thái THẬT của VPS đã bị bài kiểm chạm vào "
        "— xem SHOPAPI_VM_GOC (vm/agent.py) và fixture _co_lap_vm_agent_goc "
        "(tests/conftest.py)")
