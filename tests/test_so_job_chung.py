"""Bài kiểm `core/so_job_chung.py` — bộ đệm sổ job ShopAPI TOÀN MÁY.

Ba "tiến trình" giả lập bằng BA LUỒNG thật dùng chung một `tmp_path` (đúng cơ
chế thật: điều phối bằng tệp trên đĩa, không phải bằng bộ nhớ trong tiến
trình) — cố ý KHÔNG dùng `multiprocessing` ở đây vì cái cần kiểm là "khoá tệp
có thật sự chặn được lượt hỏi thứ hai", không phải "tiến trình có tách biệt
hay không". Đồng hồ GIẢ (đưa qua `gio_ham`) để bài kiểm không phải chờ 30
giây thật; độ trễ THẬT nhỏ (0,05s) bên trong client giả để mở đủ khe hở cho
hai luồng thua cuộc thật sự gặp khoá đang bị giữ (nếu không thì luồng đầu đã
ghi xong đệm trước khi hai luồng kia kịp đọc, che mất phần "chờ khoá" đang
muốn kiểm)."""

from __future__ import annotations

import json
import os
import threading
import time

from core import so_job_chung as sjc


class _ClientGia:
    def __init__(self, do_tre_giay: float = 0.05):
        self.so_lan_goi = 0
        self._khoa = threading.Lock()
        self._do_tre = do_tre_giay
        self.jobs = self

    def list(self, status: str, limit: int, cursor=None):
        with self._khoa:
            self.so_lan_goi += 1
        time.sleep(self._do_tre)
        if status == "succeeded" and cursor is None:
            return {"data": [{"id": "job-1", "status": "succeeded"}],
                   "has_more": False, "next_cursor": None}
        return {"data": [], "has_more": False, "next_cursor": None}


def _chay_song_song(ham, so_luong: int):
    """Chạy `ham()` trên `so_luong` luồng, bắt đầu gần như cùng lúc."""
    hang_rao = threading.Barrier(so_luong)
    ket_qua = [None] * so_luong

    def _boc(i):
        hang_rao.wait(timeout=5.0)
        ket_qua[i] = ham()

    luong = [threading.Thread(target=_boc, args=(i,)) for i in range(so_luong)]
    for l in luong:
        l.start()
    for l in luong:
        l.join(timeout=10.0)
    return ket_qua


def test_ba_luong_dung_chung_dem_chi_mot_luot_hoi(tmp_path):
    goc = str(tmp_path)
    client = _ClientGia(do_tre_giay=0.08)
    dong_ho = [1_000_000.0]

    def _gio():
        return dong_ho[0]

    def _lay():
        return sjc.lay(goc, client, gio_ham=_gio, ngu=time.sleep,
                       cho_toi_da=5.0, buoc_cho=0.01)

    # Mỗi VÒNG hỏi thật gọi `jobs.list` hai lần (một cho "succeeded", một cho
    # "failed" — giống hệt `SoTheoDoi._mot_luot`, xem `sjc.TRANG_THAI_MAC_DINH`).
    # Cái cần kiểm là số VÒNG không tăng theo số tiến trình, nên so bằng bội
    # số của `len(TRANG_THAI_MAC_DINH)`, không phải bằng 1.
    goi_moi_vong = len(sjc.TRANG_THAI_MAC_DINH)

    ket_qua = _chay_song_song(_lay, 3)
    assert client.so_lan_goi == goi_moi_vong, (
        "3 'tiến trình' cùng lúc chỉ được hỏi ĐÚNG 1 vòng (={0} lượt gọi jobs.list), "
        "hỏi được {1}".format(goi_moi_vong, client.so_lan_goi))
    for r in ket_qua:
        assert r is not None
        assert r["jobs"]["job-1"]["status"] == "succeeded"
        assert r["luc_ghi"] == dong_ho[0]

    # Đệm còn tươi (đồng hồ giả CHƯA nhích) — gọi thêm lần nữa vẫn không hỏi.
    sjc.lay(goc, client, gio_ham=_gio)
    assert client.so_lan_goi == goi_moi_vong

    # Đồng hồ giả nhích quá TUOI_TUOI_GIAY -> đệm cũ -> đúng 1 VÒNG hỏi MỚI
    # cho cả ba "tiến trình" tiếp theo (không tăng theo số tiến trình).
    # Nhường một nhịp thật ngắn cho hệ điều hành dọn xong ba luồng của vòng
    # trước — chạy chung với các bài multiprocessing nặng của `test_khe.py`
    # trong CÙNG một tiến trình pytest có thể làm bộ lập lịch luồng trễ nhịp.
    time.sleep(0.1)
    dong_ho[0] += sjc.TUOI_TUOI_GIAY + 1.0
    ket_qua2 = _chay_song_song(_lay, 3)
    assert client.so_lan_goi == goi_moi_vong * 2
    for r in ket_qua2:
        assert r["luc_ghi"] == dong_ho[0]


def test_dem_ghi_xuong_dia_nguyen_tu(tmp_path):
    goc = str(tmp_path)
    client = _ClientGia(do_tre_giay=0.0)
    sjc.lay(goc, client, cho_toi_da=5.0)
    duong = sjc.duong_dem(goc)
    assert os.path.isfile(duong)
    with open(duong, "r", encoding="utf-8") as tep:
        du = json.load(tep)
    assert "job-1" in du["jobs"]
    # Không để lại tệp tạm nào.
    con_lai = os.listdir(os.path.dirname(duong))
    assert all(not t.endswith(".tam") for t in con_lai)


def test_khoa_duoc_nha_sau_khi_hoi_xong(tmp_path):
    goc = str(tmp_path)
    client = _ClientGia(do_tre_giay=0.0)
    sjc.lay(goc, client, cho_toi_da=5.0)
    assert not os.path.isfile(sjc.duong_khoa(goc))


def test_dem_tuoi_bien_35_giay():
    assert sjc._dem_con_tuoi({"luc_ghi": 100.0}, 134.9, sjc.TUOI_TUOI_GIAY)
    assert not sjc._dem_con_tuoi({"luc_ghi": 100.0}, 135.0, sjc.TUOI_TUOI_GIAY)
    assert not sjc._dem_con_tuoi(None, 100.0, sjc.TUOI_TUOI_GIAY)
    assert not sjc._dem_con_tuoi({}, 100.0, sjc.TUOI_TUOI_GIAY)


def test_khoa_cu_da_chet_duoc_don_va_tu_hoi_lai(tmp_path):
    goc = str(tmp_path)
    duong_k = sjc.duong_khoa(goc)
    os.makedirs(os.path.dirname(duong_k), exist_ok=True)
    with open(duong_k, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999999, "bat_dau": time.time() - 999}, tep)

    client = _ClientGia(do_tre_giay=0.0)
    ket_qua = sjc.lay(goc, client, cho_toi_da=5.0)
    assert client.so_lan_goi == len(sjc.TRANG_THAI_MAC_DINH)  # một vòng, dọn khoá cũ rồi tự hỏi
    assert ket_qua["jobs"]["job-1"]["status"] == "succeeded"
    assert not os.path.isfile(duong_k)
