"""Trạm nhận chạy NỀN + chó giữ nhà (`core/tram_nen.py`, `core/canh_tram.py`).

KHÔNG bài nào ở đây mở cổng 8765 thật, không bài nào sinh tiến trình thật, và
không bài nào gọi `schtasks` thật. Máy chạy bộ test này cũng chính là máy dựng
đang chạy tool thật — đụng vào cổng/lịch của nó là phá đúng thứ ta vừa sửa.
Mọi chỗ chạm ra ngoài đều có seam: `do_tram`/`do` (hỏi cổng), `dung_tram` (dựng
trạm), `sinh` (sinh tiến trình), `chay_lenh` (gọi schtasks).
"""

from __future__ import annotations

import os

from core import canh_tram, lich_tu_chay, tram_nen


# ── đồ giả ───────────────────────────────────────────────────────────────────


class TramGia:
    """Đóng thế `core.chi_so_ytb.tram.Tram` — chỉ đủ phần `chay()` đụng tới."""

    def __init__(self, cong: int = 8765, loi_khi_bat: Exception = None):
        self.cong = cong
        self._loi = loi_khi_bat
        self.so_lan_bat = 0
        self.so_lan_tat = 0

    def bat(self):
        self.so_lan_bat += 1
        if self._loi is not None:
            raise self._loi

    def tat(self):
        self.so_lan_tat += 1


def _ghi_gom(kho):
    return lambda dong: kho.append(str(dong))


# ── chay(): nhường khi đã có trạm khác ───────────────────────────────────────


def test_da_co_tram_khac_nghe_thi_khong_mo_cong_thu_hai(tmp_path):
    """Luật "một cổng một chủ" (ui_qt/tram_chung.py): thấy có tiếng đáp là lui."""
    kho = []
    da_dung = []

    def dung_tram(goc, cong, ghi):
        da_dung.append(cong)
        return TramGia()

    ma = tram_nen.chay(str(tmp_path), ghi=_ghi_gom(kho),
                       do_tram=lambda cong: True, dung_tram=dung_tram)
    assert ma == 0
    assert da_dung == [], "đã có trạm khác mà vẫn dựng trạm thứ hai"
    assert any("NHƯỜNG" in d for d in kho)
    assert not os.path.isfile(tram_nen.duong_dau_tich(str(tmp_path)))


def test_hoi_dung_cong_duoc_yeu_cau(tmp_path):
    da_hoi = []
    tram_nen.chay(str(tmp_path), 8790, ghi=_ghi_gom([]),
                  do_tram=lambda cong: da_hoi.append(cong) or True,
                  dung_tram=lambda *a: TramGia())
    assert da_hoi == [8790]


# ── chay(): bật thật (trạm giả) rồi dừng ─────────────────────────────────────


def test_bat_duoc_thi_ghi_dau_tich_roi_xoa_khi_lui(tmp_path):
    goc = str(tmp_path)
    tram = TramGia(cong=8765)
    kho = []
    thay_dau_tich = []

    def dung_khi():
        thay_dau_tich.append(os.path.isfile(tram_nen.duong_dau_tich(goc)))
        return True

    ma = tram_nen.chay(goc, ghi=_ghi_gom(kho), do_tram=lambda c: False,
                       dung_tram=lambda *a: tram, nhip=0.01, dung_khi=dung_khi)
    assert ma == 0
    assert tram.so_lan_bat == 1 and tram.so_lan_tat == 1
    assert thay_dau_tich == [True], "đang chạy mà không có dấu tích trên đĩa"
    # Lui xong phải dọn sạch: dấu tích còn nằm lại là lần mở tool sau ngồi chờ
    # 8 giây cho một tiến trình đã chết.
    assert not os.path.isfile(tram_nen.duong_dau_tich(goc))
    assert not os.path.isfile(tram_nen.duong_co_nhuong(goc))


def test_dau_tich_ghi_dung_cong_that_va_pid(tmp_path):
    goc = str(tmp_path)
    doc = {}

    def dung_khi():
        doc.update(tram_nen.doc_dau_tich(goc))
        return True

    # Trạm lùi cổng (8765 bận vì một thứ KHÔNG phải trạm) — dấu tích phải ghi
    # số cổng THẬT, không phải số đã xin.
    tram_nen.chay(goc, ghi=_ghi_gom([]), do_tram=lambda c: False,
                  dung_tram=lambda *a: TramGia(cong=8768), nhip=0.01,
                  dung_khi=dung_khi)
    assert doc.get("cong") == 8768
    assert doc.get("pid") == os.getpid()


def test_co_xin_nhuong_thi_lui_ngay(tmp_path):
    goc = str(tmp_path)
    tram = TramGia()
    kho = []
    lan = {"n": 0}

    def dung_khi():
        # Lượt đầu đặt cờ xuống rồi nói "chưa dừng" — vòng lặp phải tự thấy cờ.
        lan["n"] += 1
        if lan["n"] == 1:
            os.makedirs(tram_nen.thu_muc_dau_tich(goc), exist_ok=True)
            open(tram_nen.duong_co_nhuong(goc), "w").close()
        return False

    tram_nen.chay(goc, ghi=_ghi_gom(kho), do_tram=lambda c: False,
                  dung_tram=lambda *a: tram, nhip=0.01, dung_khi=dung_khi)
    assert lan["n"] == 1
    assert tram.so_lan_tat == 1
    assert any("xin lại cổng" in d for d in kho)


def test_co_cu_con_nam_lai_thi_xoa_truoc_khi_bat(tmp_path):
    """Cờ cũ sót lại (lần nhường trước bị cắt ngang) không được giết trạm mới.

    Không dọn thì chó giữ nhà cứ 5 phút đẻ một con rồi mất một con, mãi mãi.
    """
    goc = str(tmp_path)
    os.makedirs(tram_nen.thu_muc_dau_tich(goc), exist_ok=True)
    open(tram_nen.duong_co_nhuong(goc), "w").close()
    tram = TramGia()
    song = []

    def dung_khi():
        song.append(os.path.isfile(tram_nen.duong_dau_tich(goc)))
        return True

    tram_nen.chay(goc, ghi=_ghi_gom([]), do_tram=lambda c: False,
                  dung_tram=lambda *a: tram, nhip=0.01, dung_khi=dung_khi)
    assert song == [True], "cờ cũ làm trạm mới chết ngay khi vừa bật"


def test_bat_hong_thi_tra_ma_1_va_khong_de_lai_dau_tich(tmp_path):
    goc = str(tmp_path)
    kho = []
    ma = tram_nen.chay(goc, ghi=_ghi_gom(kho), do_tram=lambda c: False,
                       dung_tram=lambda *a: TramGia(loi_khi_bat=OSError("cổng bận")))
    assert ma == 1
    assert any("không bật được" in d for d in kho)
    assert not os.path.isfile(tram_nen.duong_dau_tich(goc))


# ── xin_nhuong() ─────────────────────────────────────────────────────────────


def test_xin_nhuong_khi_khong_co_ban_nen_nao(tmp_path):
    ok, loi_nhan = tram_nen.xin_nhuong(str(tmp_path))
    assert ok is False
    assert "không có" in loi_nhan
    assert not os.path.isfile(tram_nen.duong_co_nhuong(str(tmp_path)))


def test_xin_nhuong_thanh_cong_va_don_co(tmp_path):
    goc = str(tmp_path)
    os.makedirs(tram_nen.thu_muc_dau_tich(goc), exist_ok=True)
    with open(tram_nen.duong_dau_tich(goc), "w", encoding="utf-8") as tep:
        tep.write('{"pid": 1, "cong": 8765}')

    def ngu(_giay):
        # Đóng vai bản nền: thấy cờ thì xoá dấu tích của mình rồi thoát.
        if os.path.isfile(tram_nen.duong_co_nhuong(goc)):
            os.remove(tram_nen.duong_dau_tich(goc))

    ok, loi_nhan = tram_nen.xin_nhuong(goc, cho_giay=5.0, ngu=ngu,
                                       do_tram=lambda c: True)
    assert ok is True
    assert "đã lui" in loi_nhan
    # Cờ PHẢI biến mất: để lại là bản nền bật sau đó thấy cờ và tự thoát ngay.
    assert not os.path.isfile(tram_nen.duong_co_nhuong(goc))


def _dat_dau_tich(goc, cong=8765, pid=999999):
    os.makedirs(tram_nen.thu_muc_dau_tich(goc), exist_ok=True)
    with open(tram_nen.duong_dau_tich(goc), "w", encoding="utf-8") as tep:
        tep.write('{{"pid": {0}, "cong": {1}}}'.format(pid, cong))


def test_xin_nhuong_het_gio_ma_van_con_tieng_dap_thi_giu_nguyen_dau_tich(tmp_path):
    """Xoá dấu tích của một tiến trình ĐANG CHẠY là tự nói dối mình: lần đòi
    sau sẽ bảo "không có bản nền nào" trong khi cổng vẫn bị giữ."""
    goc = str(tmp_path)
    _dat_dau_tich(goc)
    ok, loi_nhan = tram_nen.xin_nhuong(goc, cho_giay=0.0, ngu=lambda g: None,
                                       do_tram=lambda c: True)
    assert ok is False
    assert "vẫn giữ cổng" in loi_nhan
    assert os.path.isfile(tram_nen.duong_dau_tich(goc))
    assert not os.path.isfile(tram_nen.duong_co_nhuong(goc))


def test_xin_nhuong_het_gio_va_cam_han_thi_don_dau_tich(tmp_path):
    goc = str(tmp_path)
    _dat_dau_tich(goc)
    lan = {"n": 0}

    def do_tram(_cong):
        lan["n"] += 1
        return lan["n"] == 1   # còn đáp lúc vào, câm hẳn lúc hỏi lại

    ok, loi_nhan = tram_nen.xin_nhuong(goc, cho_giay=0.0, ngu=lambda g: None,
                                       do_tram=do_tram)
    assert ok is False
    assert "đã dọn" in loi_nhan
    assert not os.path.isfile(tram_nen.duong_dau_tich(goc))
    assert not os.path.isfile(tram_nen.duong_co_nhuong(goc))


def test_xin_nhuong_khong_ai_dap_thi_ve_ngay_khong_cho(tmp_path):
    """Chạy trên LUỒNG GIAO DIỆN: mỗi giây chờ là một giây cửa sổ đơ. Bản nền
    bị giết ngang để lại dấu tích mà không còn ai đọc cờ — phải nhận ra ngay
    bằng một gói dò, không ngồi đợi đủ 8 giây cho một cái xác."""
    goc = str(tmp_path)
    os.makedirs(tram_nen.thu_muc_dau_tich(goc), exist_ok=True)
    with open(tram_nen.duong_dau_tich(goc), "w", encoding="utf-8") as tep:
        tep.write('{"pid": 999999, "cong": 8768}')
    da_cho = []
    da_hoi = []
    ok, loi_nhan = tram_nen.xin_nhuong(
        goc, ngu=lambda g: da_cho.append(g),
        do_tram=lambda c: da_hoi.append(c) or False)
    assert ok is False
    assert da_cho == [], "ngồi chờ một tiến trình đã chết"
    assert da_hoi == [8768], "phải hỏi đúng cổng ghi trong dấu tích"
    assert "đã dọn" in loi_nhan
    assert not os.path.isfile(tram_nen.duong_dau_tich(goc))
    # Chưa từng đặt cờ thì cũng không được để lại cờ.
    assert not os.path.isfile(tram_nen.duong_co_nhuong(goc))


# ── tim_tram_dang_song(): phải dò cả dải cổng lùi ────────────────────────────


def test_tim_thay_o_cong_goc(tmp_path):
    assert tram_nen.tim_tram_dang_song(8765, do=lambda c: c == 8765) == 8765


def test_tim_thay_o_cong_da_lui():
    """`tram.bat()` được lùi 8765 -> 8775 khi một thứ KHÔNG phải trạm giữ cổng.
    Chó giữ nhà chỉ nhìn 8765 thì tưởng trạm chết và đẻ thêm một bản nữa."""
    assert tram_nen.tim_tram_dang_song(8765, do=lambda c: c == 8770) == 8770


def test_khong_ai_dap_thi_none():
    assert tram_nen.tim_tram_dang_song(8765, do=lambda c: False) is None


# ── dap_http(): gõ cửa thật đường máy ảo hay gõ ──────────────────────────────


def test_go_cua_cong_khong_ai_nghe_thi_false():
    """Cổng 1 trên máy này không ai nghe — nối hỏng ngay, không mở cổng nào."""
    assert tram_nen.dap_http(1, cho_giay=0.5) is False


class _NoiGia:
    """Đóng thế `http.client.HTTPConnection` — ghi lại đã gõ cửa ở đâu."""

    da_goi = []

    def __init__(self, may, cong, timeout=None):
        self.da_goi.append((may, cong, timeout))
        self.duong = None

    def request(self, cach, duong):
        self.duong = duong
        self.da_goi.append((cach, duong))

    def getresponse(self):
        return type("Tra", (), {"status": self.MA})()

    def close(self):
        pass


def test_go_cua_404_van_tinh_la_co_nguoi_phuc_vu(monkeypatch):
    """403 (cổng chặn) hay 404 nghĩa là máy chủ VẪN nghe và vẫn trả lời, chỉ
    là trả lời khác. Chỉ im lặng / 5xx mới là chết."""
    import http.client

    for ma, mong_doi in ((200, True), (403, True), (404, True), (500, False)):
        lop = type("Noi", (_NoiGia,), {"MA": ma, "da_goi": []})
        monkeypatch.setattr(http.client, "HTTPConnection", lop)
        assert tram_nen.dap_http(8765) is mong_doi, ma


def test_go_cua_dung_duong_ke_hoach_chi_doc(monkeypatch):
    """Đường gõ cửa phải là `/ke-hoach` — nó CHỈ đọc một tệp CSV, không tạo
    thư mục, không ghi gì, không đẻ dòng nhật ký nào. Và phải gõ thẳng
    127.0.0.1, không qua proxy nào."""
    import http.client

    lop = type("Noi", (_NoiGia,), {"MA": 200, "da_goi": []})
    monkeypatch.setattr(http.client, "HTTPConnection", lop)
    assert tram_nen.dap_http(8790, cho_giay=3.0) is True
    assert lop.da_goi[0] == ("127.0.0.1", 8790, 3.0)
    cach, duong = lop.da_goi[1]
    assert cach == "GET"
    assert duong.startswith("/ke-hoach?kenh=")
    assert tram_nen.KENH_GO_CUA in duong


def test_khong_ai_trong_core_dung_urlopen_tran():
    """`tests/test_mang_an_toan.py` cấm `urlopen` trần trong `core/` — chốt
    lại ngay cạnh chỗ dễ vi phạm nhất, để lần sửa sau thấy liền."""
    with open(tram_nen.__file__, encoding="utf-8") as tep:
        ma = tep.read()
    assert "urlopen(" not in ma


# ── chó giữ nhà ──────────────────────────────────────────────────────────────


def _kich_ban_gia(goc):
    os.makedirs(goc, exist_ok=True)
    with open(os.path.join(goc, "tram_nen.py"), "w", encoding="utf-8") as tep:
        tep.write("# giả\n")


def test_tram_con_song_thi_khong_sinh_gi(tmp_path):
    _kich_ban_gia(str(tmp_path))
    da_sinh = []
    song, loi_nhan = canh_tram.mot_luot(
        str(tmp_path), do=lambda c: c == 8765, go_cua=lambda c: True,
        sinh=lambda l: da_sinh.append(l) or 123, ghi=_ghi_gom([]))
    assert song is True
    assert da_sinh == [], "trạm đang sống mà vẫn bật thêm một bản nữa"


def test_dap_goi_do_nhung_cam_http_thi_bao_ket_va_khong_sinh(tmp_path):
    """Tai dò UDP và máy chủ HTTP chạy ở HAI luồng khác nhau — luồng HTTP kẹt
    được một mình. Tin mỗi gói dò là báo "vẫn sống" cho đúng cảnh đang hỏng."""
    _kich_ban_gia(str(tmp_path))
    da_sinh = []
    kho = []
    song, loi_nhan = canh_tram.mot_luot(
        str(tmp_path), do=lambda c: c == 8765, go_cua=lambda c: False,
        sinh=lambda l: da_sinh.append(l) or 1, ghi=_ghi_gom(kho))
    assert song is False, "phải báo hỏng để Task Scheduler ghi mã khác 0"
    assert "kẹt" in loi_nhan
    # Cổng vẫn bị giữ — bản mới chỉ bind hỏng rồi chết, sinh ra là sinh rác.
    assert da_sinh == []
    assert any("câm HTTP" in d or "KHÔNG trả lời" in d for d in kho)


def test_tram_chet_thi_bat_lai_va_cho_no_len(tmp_path):
    goc = str(tmp_path)
    _kich_ban_gia(goc)
    trang_thai = {"len": False}
    da_sinh = []

    def sinh(lenh):
        da_sinh.append(lenh)
        trang_thai["len"] = True   # tiến trình mới lên tiếng ngay
        return 4242

    kho = []
    song, loi_nhan = canh_tram.mot_luot(
        goc, do=lambda c: trang_thai["len"] and c == 8765,
        go_cua=lambda c: trang_thai["len"], sinh=sinh,
        ngu=lambda g: None, ghi=_ghi_gom(kho))
    assert song is True
    assert len(da_sinh) == 1, "một lượt kiểm chỉ được sinh ĐÚNG một tiến trình"
    lenh = da_sinh[0]
    assert lenh[1] == os.path.join(goc, "tram_nen.py")
    assert "pythonw" in lenh[0].lower() or lenh[0] == "", lenh[0]
    assert any("KHÔNG ai trả lời" in d for d in kho)


def test_bat_len_roi_ma_van_cam_thi_bao_that(tmp_path):
    goc = str(tmp_path)
    _kich_ban_gia(goc)
    song, loi_nhan = canh_tram.mot_luot(
        goc, do=lambda c: False, go_cua=lambda c: False, sinh=lambda l: 7,
        cho_len_giay=0.0, ngu=lambda g: None, ghi=_ghi_gom([]))
    assert song is False
    assert "chưa lên tiếng" in loi_nhan


def test_thieu_kich_ban_thi_noi_that_khong_sinh(tmp_path):
    da_sinh = []
    song, loi_nhan = canh_tram.mot_luot(
        str(tmp_path), do=lambda c: False, go_cua=lambda c: False,
        sinh=lambda l: da_sinh.append(l) or 1, ghi=_ghi_gom([]))
    assert song is False
    assert "tram_nen.py" in loi_nhan
    assert da_sinh == []


def test_lenh_bat_tram_nen_co_cong_khi_khac_mac_dinh(tmp_path):
    lenh = canh_tram.lenh_bat_tram_nen(str(tmp_path), 8790)
    assert lenh[-2:] == ["--cong", "8790"]
    assert canh_tram.lenh_bat_tram_nen(str(tmp_path))[-1].endswith("tram_nen.py")


def test_canh_chay_dung_so_luot(tmp_path):
    goc = str(tmp_path)
    _kich_ban_gia(goc)
    luot = []
    canh_tram.canh(goc, so_luot=3, do=lambda c: luot.append(c) or True,
                   go_cua=lambda c: True, sinh=lambda l: 0, ngu=lambda g: None,
                   ghi=_ghi_gom([]))
    # Mỗi lượt hỏi đúng cổng gốc một lần (trả lời ngay nên không dò tiếp dải lùi).
    assert luot == [8765, 8765, 8765]


# ── lịch Windows cho chó giữ nhà ─────────────────────────────────────────────


def test_dang_ky_canh_tram_dung_ten_viec_va_nhip(tmp_path):
    goc = str(tmp_path)
    _kich_ban_gia(goc)
    goi = []
    ok, loi_nhan = lich_tu_chay.dang_ky_canh_tram(
        goc, 5, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is True
    canh = goi[0]
    assert canh[canh.index("/TN") + 1] == lich_tu_chay.TEN_VIEC_CANH
    assert canh[canh.index("/SC") + 1] == "MINUTE"
    assert canh[canh.index("/MO") + 1] == "5"
    assert "/F" in canh
    # Mặc định KHÔNG /RU: chạy bằng chính người dùng, kiểu "chỉ khi đã đăng
    # nhập" — cùng luật DPAPI với việc tự chạy.
    assert "/RU" not in canh and "/RP" not in canh
    assert canh[canh.index("/TR") + 1].endswith('tram_nen.py" --kiem')
    # Việc thứ hai: một lượt kiểm ngay lúc đăng nhập.
    dang_nhap = goi[1]
    assert dang_nhap[dang_nhap.index("/TN") + 1] == lich_tu_chay.TEN_VIEC_TRAM_DANG_NHAP
    assert dang_nhap[dang_nhap.index("/SC") + 1] == "ONLOGON"


def test_dang_ky_canh_tram_bo_viec_luc_dang_nhap(tmp_path):
    goc = str(tmp_path)
    _kich_ban_gia(goc)
    goi = []
    lich_tu_chay.dang_ky_canh_tram(goc, 5, luc_dang_nhap=False,
                                   chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert len(goi) == 1


def test_dang_ky_canh_tram_du_chua_dang_nhap_thi_chay_bang_he_thong(tmp_path):
    """Đường lách ràng buộc "phải đã đăng nhập" — và phải đổi ONLOGON→ONSTART,
    vì "lúc SYSTEM đăng nhập" là chuyện không có thật."""
    goc = str(tmp_path)
    _kich_ban_gia(goc)
    goi = []
    ok, loi_nhan = lich_tu_chay.dang_ky_canh_tram(
        goc, 5, du_chua_dang_nhap=True, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is True
    for lenh in goi:
        assert lenh[lenh.index("/RU") + 1] == "SYSTEM"
    assert goi[1][goi[1].index("/SC") + 1] == "ONSTART"
    assert "không cần ai đăng nhập" in loi_nhan.lower()


def test_dang_ky_canh_tram_nhip_sai_thi_tu_choi_khong_goi_lenh(tmp_path):
    _kich_ban_gia(str(tmp_path))
    goi = []
    ok, loi_nhan = lich_tu_chay.dang_ky_canh_tram(
        str(tmp_path), 0, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is False and goi == []


def test_dang_ky_canh_tram_thieu_kich_ban_thi_tu_choi(tmp_path):
    goi = []
    ok, loi_nhan = lich_tu_chay.dang_ky_canh_tram(
        str(tmp_path), 5, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is False
    assert "tram_nen.py" in loi_nhan
    assert goi == []


def test_dang_ky_canh_tram_viec_chinh_hong_thi_bao_that(tmp_path):
    _kich_ban_gia(str(tmp_path))
    ok, loi_nhan = lich_tu_chay.dang_ky_canh_tram(
        str(tmp_path), 5, chay_lenh=lambda l: (1, "ERROR: Access is denied."))
    assert ok is False
    assert "Access is denied" in loi_nhan


def test_dang_ky_canh_tram_viec_phu_hong_van_coi_la_xong(tmp_path):
    """Đồng hồ 5 phút mới là thứ không thể thiếu; lượt kiểm lúc đăng nhập
    chỉ rút ngắn quãng trống sau khi khởi động lại."""
    _kich_ban_gia(str(tmp_path))
    lan = {"n": 0}

    def chay_lenh(lenh):
        lan["n"] += 1
        return (0, "") if lan["n"] == 1 else (1, "ERROR: Access is denied.")

    ok, loi_nhan = lich_tu_chay.dang_ky_canh_tram(str(tmp_path), 5, chay_lenh=chay_lenh)
    assert ok is True
    assert "KHÔNG đặt được" in loi_nhan


def test_huy_canh_tram_xoa_ca_hai_viec(tmp_path):
    goi = []
    ok, loi_nhan = lich_tu_chay.huy_canh_tram(
        str(tmp_path), chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is True
    ten = [l[l.index("/TN") + 1] for l in goi]
    assert ten == [lich_tu_chay.TEN_VIEC_CANH, lich_tu_chay.TEN_VIEC_TRAM_DANG_NHAP]


def test_huy_canh_tram_chua_tung_dat_thi_khong_bao_do(tmp_path):
    ok, loi_nhan = lich_tu_chay.huy_canh_tram(
        str(tmp_path),
        chay_lenh=lambda l: (1, 'ERROR: The specified task name "x" does not exist.'))
    assert ok is True
    assert "Chưa từng" in loi_nhan


def test_trang_thai_canh_tram_hoi_dung_ten_viec(tmp_path):
    goi = []
    lich_tu_chay.trang_thai_canh_tram(
        str(tmp_path), chay_lenh=lambda l: goi.append(l) or (1, ""))
    assert goi[0][goi[0].index("/TN") + 1] == lich_tu_chay.TEN_VIEC_CANH


def test_ket_qua_cuoi_cua_viec_canh_noi_ve_tram_khong_ve_kenh():
    """Cùng mã 0, hai nghĩa khác hẳn — nói nhầm câu là đọc nhầm máy."""
    assert "trạm 8765" in lich_tu_chay._dien_giai_ket_qua(
        "0", "21/09/2026 17:47:00", ten_viec=lich_tu_chay.TEN_VIEC_CANH)
    assert "kênh" in lich_tu_chay._dien_giai_ket_qua("0", "21/09/2026 02:00:00")


# ── giao diện đòi lại cổng lúc mở tool ───────────────────────────────────────


def test_khoi_dong_vps_doi_cong_truoc_khi_bao_dam_tram(monkeypatch, tmp_path):
    """Thứ tự sai là cổng trống trơn: `bao_dam_bat()` gặp cổng bận rồi từ chối,
    và lúc bản nền lui xong thì không còn ai gọi lại."""
    from core import che_do_vps, khoi_dong_vps

    monkeypatch.setattr(che_do_vps, "la_vps", lambda goc: True)
    thu_tu = []
    monkeypatch.setattr(khoi_dong_vps, "_doi_lai_cong",
                        lambda goc: thu_tu.append("doi-cong"))
    monkeypatch.setattr(khoi_dong_vps, "_bao_dam_tram",
                        lambda app: thu_tu.append("bao-dam-tram"))
    monkeypatch.setattr(khoi_dong_vps, "_bat_giam_sat",
                        lambda app, goc: thu_tu.append("giam-sat"))
    khoi_dong_vps._khoi_dong(object(), str(tmp_path))
    assert thu_tu == ["doi-cong", "bao-dam-tram", "giam-sat"]


def test_doi_lai_cong_nuot_loi(monkeypatch, tmp_path):
    """Đòi hụt thì giao diện vẫn phải mở lên được."""
    from core import khoi_dong_vps

    def no(goc, **kw):
        raise RuntimeError("đĩa hỏng")

    monkeypatch.setattr(tram_nen, "xin_nhuong", no)
    khoi_dong_vps._doi_lai_cong(str(tmp_path))  # không được ném


# ── điểm vào không được kéo theo Qt ──────────────────────────────────────────


def test_khong_mo_dun_nao_o_day_import_qt():
    """Cả dây chuyền trạm nền phải chạy được bằng `pythonw` trần, không PyQt5."""
    for mo_dun in (tram_nen, canh_tram):
        with open(mo_dun.__file__, encoding="utf-8") as tep:
            ma = tep.read()
        assert "PyQt5" not in ma, mo_dun.__file__
        assert "import ui_qt" not in ma and "from ui_qt" not in ma


def test_diem_vao_o_goc_ton_tai_va_khong_import_qt():
    goc = os.path.dirname(os.path.dirname(os.path.abspath(tram_nen.__file__)))
    duong = os.path.join(goc, "tram_nen.py")
    assert os.path.isfile(duong), "thiếu điểm vào tram_nen.py ở gốc MyTool"
    with open(duong, encoding="utf-8") as tep:
        ma = tep.read()
    assert "PyQt5" not in ma
    for che_do in ("--canh", "--kiem", "--tat", "--cong"):
        assert che_do in ma
