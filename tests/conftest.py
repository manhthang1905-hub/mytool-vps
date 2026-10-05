"""Dọn trạng thái dùng chung TRƯỚC mỗi bài kiểm.

Tool có mấy thứ cố ý sống suốt tiến trình — đúng cho lúc chạy thật, sai cho lúc
chạy test:

* `core.su_co.NHIP` là **một** cái van 48 lượt gọi/phút cho cả tool. Bài kiểm nào
  chạy khâu Tự động cũng nhả vé vào van ấy, và vé sống 60 giây — dài hơn cả mẻ
  test. Chạy trọn `tests/` thì `test_nan_do_dai.py` để lại 46 vé, ngay sau nó
  `test_nhip_thu_lai.py` xin thêm là chạm trần: van chặn, mà hàm `ngu` trong bài
  kiểm chỉ ghi lại con số chứ không ngủ thật, nên vòng chờ quay hàng triệu lượt
  rồi bài kiểm hỏng. Chạy riêng file ấy lại xanh — đúng dạng hỏng "tuỳ thứ tự"
  làm người ta mất buổi đi tìm một lỗi không có.
* `core.anh_len._NHO` nhớ URL ảnh đã đẩy theo `(tên tệp, cỡ, lần sửa)`. Hai bài
  kiểm khác nhau đều dựng `nv1.png` cùng cỡ trong `tmp_path` riêng là **trùng
  khoá**, và bài sau nhận URL của bài trước.

Cả hai đều là trạng thái tiến trình, không phải trạng thái của bài kiểm. Dọn ở
đây một lần cho mọi file, thay vì bắt từng bài tự nhớ.
"""

from __future__ import annotations

import os
import pytest

# ═══ BỘ TEST KHÔNG BAO GIỜ ĐƯỢC NGHE CỔNG NHẬN THẬT (8765) ═══
#
# 07/09/2026: chủ dự án mở tool, nhận "cổng 8765 đang bị chương trình khác giữ".
# Thủ phạm là một lượt `pytest` của chính tool đang chạy — nó dựng trang giữ
# trạm, trang tự bật trạm trên cổng mặc định, và giữ suốt lượt chạy (có lượt
# treo hàng giờ). Ép 0 = cổng ngẫu nhiên: test vẫn chạy đủ, tool vẫn mở được.
os.environ.setdefault("SHOPAPI_TRAM_CONG", "0")

# Hội đồng quyết định (`core/giam_doc/hoi_dong.py`, 01/10/2026) gọi 5 lượt LLM thay 1 — bài kiểm cũ dùng LLM giả
# trả MỘT câu cố định cho đường một lượt. Tắt mặc định; bài kiểm hội đồng tự bật (`monkeypatch.setenv`).
os.environ.setdefault("SHOPAPI_HOI_DONG", "0")



@pytest.fixture(autouse=True)
def _don_trang_thai_dung_chung():
    try:
        from core import su_co

        su_co.NHIP._moc = []
    except Exception:  # noqa: BLE001 — thiếu module thì không có gì phải dọn
        pass
    try:
        from core import anh_len

        anh_len.xoa_nho()
    except Exception:  # noqa: BLE001
        pass
    yield


@pytest.fixture(autouse=True)
def _co_lap_vm_agent_goc(tmp_path_factory, monkeypatch):
    """Lưới an toàn THỨ HAI chặn bài kiểm ghi vào nhật ký/`trang-thai.json`
    THẬT của máy ảo (Đợt 0.2 cô lập test, kiểm toán 29/09/2026).

    Lưới thứ nhất là từng bài TỰ bẻ `agent.GOC` sau khi tự `importlib` nạp
    `vm/agent.py` (xem `tests/test_loi_thoai_trinh_duyet._nap_agent`) — nhưng
    quên một chỗ là đủ rò: đo được hơn 1.167 dòng "vm-thu"/"pytest-of" lẫn
    vào `vm/agent.log` thật (có dòng ngay trong ngày kiểm toán). `vm/agent.py`
    giờ đọc `SHOPAPI_VM_GOC` NGAY LÚC MODULE CHẠY (mọi hằng số suy ra từ `GOC`,
    như `THU_MUC_TIEN_ICH`, ăn theo đúng luôn — không cần vá riêng từng cái
    như lưới thứ nhất phải làm). Đặt biến này ở đây, MỘT chỗ cho mọi bài, thì
    bài nào lỡ quên tự bẻ `GOC` cũng không chạm được đĩa thật nữa.

    Đặt cho MỌI bài kiểm (không chỉ bài đụng `vm/`) vì rẻ (`tmp_path` đã có
    sẵn) và vô hại — biến chỉ được đọc trong `vm/agent.py`, máy ảo thật không
    bao giờ tự đặt biến này nên hành vi sản xuất không đổi.

    Bài nào tự bẻ `agent.GOC` bằng `monkeypatch.setattr` SAU khi nạp module
    thì lưới này không cản gì — `setattr` áp thẳng lên đối tượng module, luôn
    thắng giá trị nạp từ biến môi trường lúc `exec_module`.
    """
    # Thư mục RIÊNG (`tmp_path_factory`), KHÔNG nằm trong `tmp_path` của bài: bài nào
    # liệt kê `tmp_path` (vd `test_dung_video_quet` — mỗi thư mục con là một dự án)
    # sẽ thấy thêm một thư mục lạ "vm-goc-mac-dinh" và đỏ oan.
    goc = tmp_path_factory.mktemp("vm-goc-mac-dinh")
    # `vm/` LUÔN tồn tại như một thư mục thật trên máy ảo — tạo trước để
    # hành vi giống hệt sản xuất (`open(..., "a")` của `ghi()` cần thư mục
    # cha có sẵn; thiếu nó thì lượt ghi âm thầm rơi vào `except OSError: pass`
    # và bài kiểm không phát hiện được chỗ lẽ ra phải ghi mà không ghi).
    goc.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SHOPAPI_VM_GOC", str(goc))
    yield


@pytest.fixture(autouse=True)
def _ram_du_mac_dinh(monkeypatch):
    """RAM THẬT của máy đang chạy `pytest` không được rò vào bài kiểm.

    `core.tu_chay._ram_trong_gb()` đọc RAM thật để chặn sản xuất khi máy dưới
    3 GB trống (van an toàn cho VPS đang chạy thật, xem `RAM_TRONG_TOI_THIEU_GB`)
    — nhưng máy dev/VPS đang mở nhiều phiên song song thì RAM thật cũng tụt
    dưới ngưỡng đó bất cứ lúc nào (đo 26/09/2026: 1,5 GB trống), làm cả chục
    bài `test_tu_chay.py`/`test_van_dia_trong.py` tự dưng đỏ vì MÁY, không
    phải vì mã sai — `run["bo_nho"]["du"] = False` cướp đường trước khi bài
    kiểm kịp chạm tới nhánh ngân sách/đĩa nó thật sự muốn kiểm.

    Giả RAM DƯ DẢ (99 GB) làm mặc định cho MỌI bài. Bài nào cố ý kiểm đúng
    van RAM này thì tự `monkeypatch.setattr(tu_chay, "_ram_trong_gb", ...)`
    ngay trong thân bài — chạy SAU fixture này (cùng một `monkeypatch`) nên
    vẫn thắng bình thường, không cần sửa gì ở đây.
    """
    try:
        from core import tu_chay

        monkeypatch.setattr(tu_chay, "_ram_trong_gb", lambda: 99.0)
    except Exception:  # noqa: BLE001 — thiếu module thì không có gì phải giả
        pass
    yield
