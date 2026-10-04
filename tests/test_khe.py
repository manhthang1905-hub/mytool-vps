"""Bài kiểm `core/khe.py` — khe tài nguyên liên tiến trình.

MỌI đường dẫn trong file này đi qua `tmp_path` — không bài nào được đụng
`workspace/khe/` hay `workspace/tu-chay/.khoa-may` THẬT của kho này (luật RAM/
an toàn ở CLAUDE.local.md và chỉ đạo của việc này).
"""

from __future__ import annotations

import json
import multiprocessing
import os
import threading
import time

import pytest

from core import khe


# ── Việc chạy trong TIẾN TRÌNH CON (phải là hàm module-level để pickle được) ─


def _tien_trinh_giu_nang(goc: str, thoi_gian_giu: float, hang_doi) -> None:
    from core import khe as _khe  # import lại trong tiến trình con (spawn)

    with _khe.giu(goc, "nang", "test-loai-tru", cho_toi_da=15,
                  nhip_kiem_giay=0.1) as _huy:
        hang_doi.put((os.getpid(), "bat_dau", time.time()))
        time.sleep(thoi_gian_giu)
        hang_doi.put((os.getpid(), "ket_thuc", time.time()))


#: PID không tồn tại trên bất kỳ Windows thật nào (đủ lớn, không chẵn theo
#: quy tắc cấp phát PID của Windows) — dùng để mô phỏng "chủ khoá đã chết" mà
#: KHÔNG cần spawn rồi giết một tiến trình thật. Cách đó (đã thử) bị Windows
#: TÁI SỬ DỤNG PID gần như ngay lập tức khi máy đang spawn nhiều tiến trình
#: liên tục (đúng tình huống của chính bộ test này) — `OpenProcess` thấy PID
#: sống lại thật vì một tiến trình HOÀN TOÀN KHÁC vừa được cấp đúng PID đó,
#: không phải lỗi của `pid_con_song`. Một số PID không tưởng thì không có rủi
#: ro trùng này.
PID_GIA_DA_CHET = 999999999


# ── Loại trừ tuyệt đối khe "nang" giữa hai TIẾN TRÌNH THẬT ─────────────────


def test_loai_tru_nang_giua_hai_tien_trinh_that(tmp_path):
    goc = str(tmp_path)
    ctx = multiprocessing.get_context("spawn")
    hang_doi = ctx.Queue()
    p1 = ctx.Process(target=_tien_trinh_giu_nang, args=(goc, 0.6, hang_doi))
    p2 = ctx.Process(target=_tien_trinh_giu_nang, args=(goc, 0.6, hang_doi))
    p1.start()
    time.sleep(0.15)  # p1 gần chắc chắn giành khe trước
    p2.start()
    p1.join(timeout=20)
    p2.join(timeout=20)
    assert p1.exitcode == 0
    assert p2.exitcode == 0

    theo_pid: dict = {}
    while not hang_doi.empty():
        pid, nhan, luc = hang_doi.get()
        theo_pid.setdefault(pid, {})[nhan] = luc
    assert len(theo_pid) == 2, "cả hai tiến trình đều phải giành được khe (lần lượt)"
    (a, b) = list(theo_pid.values())
    # Không được chồng nhau: quãng của bên này phải kết thúc trước khi bên kia
    # bắt đầu, theo MỘT trong hai chiều.
    khong_chong = (a["ket_thuc"] <= b["bat_dau"]) or (b["ket_thuc"] <= a["bat_dau"])
    assert khong_chong, "hai tiến trình đã giữ khe NANG cùng lúc: {0} / {1}".format(a, b)

    # Sau khi cả hai đã nhả, khe phải trống hẳn.
    assert khe.trang_thai(goc)["nang"] is None


# ── PID chết giành lại NGAY (không có luật "12 giờ") ────────────────────────


def test_pid_chet_gianh_lai_ngay(tmp_path):
    """Chủ khoá cũ đã CHẾT -> giành lại NGAY, không có luật "khoá cũ 12 giờ
    vẫn giành" như `core/tu_chay.py` cũ.

    Dựng khoá cũ bằng tay với một PID không thể tồn tại (`PID_GIA_DA_CHET`)
    thay vì spawn-rồi-giết một tiến trình thật: đã thử cách đó và bị Windows
    TÁI SỬ DỤNG lại đúng PID vừa giết trong vài mili-giây (máy đang spawn liên
    tục vì chính bộ test này), làm `pid_con_song` thấy "sống" một cách CHÍNH
    XÁC — chỉ là sống bởi một tiến trình khác hẳn. Xem `test_loai_tru_nang_
    giua_hai_tien_trinh_that` cho phần dùng tiến trình thật (ở đó cả hai đều
    ĐANG SỐNG suốt lúc kiểm, nên không dính rủi ro tái sử dụng PID này)."""
    goc = str(tmp_path)
    duong = khe.duong_khoa_nang(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump({"pid": PID_GIA_DA_CHET, "nguon": "khe", "loai": "nang",
                  "viec": "test-chet-bang-tay", "kenh": "", "uu_tien": 2,
                  "bat_dau": time.time() - 60.0, "han_giay": None}, tep)
    assert not khe.pid_con_song(PID_GIA_DA_CHET)

    bat_dau = time.time()
    with khe.giu(goc, "nang", "sau-khi-chet", cho_toi_da=5,
                nhip_kiem_giay=0.1) as _huy:
        da_giu = True
    # Giành lại gần như ngay lập tức — không phải đợi một khoảng "12 giờ" nào.
    assert da_giu
    assert time.time() - bat_dau < 2.0


# ── Vé của tiến trình chết tự dọn khi liệt kê hàng chờ ──────────────────────


def test_ve_cua_tien_trinh_chet_tu_don(tmp_path):
    goc = str(tmp_path)
    duong_ve = os.path.join(khe.duong_cho(goc), "{0}-abc123.json".format(PID_GIA_DA_CHET))
    os.makedirs(os.path.dirname(duong_ve), exist_ok=True)
    with open(duong_ve, "w", encoding="utf-8") as tep:
        json.dump({"pid": PID_GIA_DA_CHET, "id": "abc123", "loai": "nang", "viec": "x",
                  "kenh": "", "uu_tien": 2, "han": None, "luc_xin": time.time()},
                 tep)
    assert os.path.isfile(duong_ve)

    trang = khe.trang_thai(goc)
    assert trang["cho"] == []
    assert not os.path.isfile(duong_ve)


# ── Xếp hàng theo ưu tiên (khớp lão hoá +1 bậc/2 giờ của core/uu_tien.py) ───


def test_xep_hang_theo_uu_tien_thang_fifo(tmp_path):
    goc = str(tmp_path)
    thu_tu = []
    khoa_thu_tu = threading.Lock()

    def _ghi(ten):
        with khoa_thu_tu:
            thu_tu.append(ten)

    # Một luồng giữ khe "nang" trước, hai luồng khác xếp hàng phía sau.
    giu_dau = threading.Event()
    tha_dau = threading.Event()

    def _giu_khe_dau():
        with khe.giu(goc, "nang", "dau", uu_tien=2, cho_toi_da=10,
                    nhip_kiem_giay=0.05) as _huy:
            _ghi("dau")
            giu_dau.set()
            tha_dau.wait(5.0)

    def _cho_thap(uu_tien, ten):
        giu_dau.wait(5.0)
        with khe.giu(goc, "nang", ten, uu_tien=uu_tien, cho_toi_da=10,
                    nhip_kiem_giay=0.05) as _huy:
            _ghi(ten)

    t_dau = threading.Thread(target=_giu_khe_dau)
    t_dau.start()
    giu_dau.wait(5.0)

    # "thap-uu-tien" (số P LỚN, tới sau nhưng đăng ký TRƯỚC) xin trước;
    # "gap" (số P NHỎ hơn, mô phỏng một việc đã được lão hoá tới mức gấp) xin
    # SAU một chút — phải THẮNG "thap-uu-tien" dù đăng ký muộn hơn.
    t_thap = threading.Thread(target=_cho_thap, args=(4, "thap-uu-tien"))
    t_thap.start()
    time.sleep(0.3)  # đảm bảo vé "thap-uu-tien" đã nằm trên đĩa trước
    t_gap = threading.Thread(target=_cho_thap, args=(0, "gap"))
    t_gap.start()
    time.sleep(0.3)  # đảm bảo vé "gap" cũng đã nằm trên đĩa trước khi nhả khe đầu

    tha_dau.set()
    t_dau.join(timeout=10)
    t_thap.join(timeout=10)
    t_gap.join(timeout=10)

    assert thu_tu[0] == "dau"
    assert thu_tu[1] == "gap", "vé ưu tiên cao hơn (số nhỏ hơn) phải thắng dù đăng ký sau: {0}".format(thu_tu)
    assert thu_tu[2] == "thap-uu-tien"


# ── Vượt han_giay -> Event bị set (không giết) + ghi nhật ký ────────────────


def test_vuot_han_giay_dat_event_khong_giet(tmp_path):
    goc = str(tmp_path)
    with khe.giu(goc, "nang", "viec-cham", han_giay=0.2) as huy:
        assert not huy.is_set()
        time.sleep(0.5)
        assert huy.is_set(), "vượt han_giay phải tự set Event, không cần ai giết"
    # Tiến trình vẫn sống bình thường tới đây — không có ngoại lệ nào bị ném ra
    # chỉ vì vượt trần thời gian giữ.
    dong = _doc_nhat_ky(goc)
    ca_vuot_han = [d for d in dong if d.get("viec_nk") == "vuot_han"]
    assert ca_vuot_han, "phải có dòng nhật ký 'vuot_han'"
    assert ca_vuot_han[0]["viec"] == "viec-cham"


def test_huy_tu_ben_ngoai_cung_duoc_khe_su_dung(tmp_path):
    """`huy` do CALLER truyền vào (ví dụ Event của nút Dừng) cũng bị SET khi
    vượt han_giay — mã có sẵn kiểm `huy.is_set()` được lợi mà không cần sửa."""
    goc = str(tmp_path)
    huy_nut_dung = threading.Event()
    with khe.giu(goc, "nang", "viec-cham", han_giay=0.2, huy=huy_nut_dung) as huy_tra_ve:
        assert huy_tra_ve is huy_nut_dung
        time.sleep(0.5)
        assert huy_nut_dung.is_set()


# ── Tương thích đọc bởi mã cũ (core/tu_chay.py) ─────────────────────────────


def test_tuong_thich_doc_boi_ma_cu_tu_chay(tmp_path):
    from core import tu_chay

    goc = str(tmp_path)
    with khe.giu(goc, "nang", "dang-giu-boi-khe", cho_toi_da=5) as _huy:
        # Mã CŨ (core/tu_chay.giu_khoa_may) phải THẤY khe này đang bị giữ, vì
        # nó đọc đúng đường `.khoa-may` và chỉ cần hai khoá `pid`/`bat_dau`.
        duoc, ly_do = tu_chay.giu_khoa_may(goc)
        assert duoc is False
        assert "PID" in ly_do or "khác" in ly_do

    # Sau khi khe.py nhả, mã cũ phải giành được bình thường.
    duoc2, _ = tu_chay.giu_khoa_may(goc)
    assert duoc2 is True
    tu_chay.nha_khoa_may(goc)


def test_duong_khoa_nang_dung_ten_cu(tmp_path):
    goc = str(tmp_path)
    assert khe.duong_khoa_nang(goc) == os.path.join(
        goc, "workspace", "tu-chay", ".khoa-may")


# ── thu_giu — một lần thử, không xếp hàng ───────────────────────────────────


def test_thu_giu_thanh_cong_roi_bi_chan(tmp_path):
    goc = str(tmp_path)
    phien = khe.thu_giu(goc, "nang", "viec-1")
    assert phien is not None
    phien2 = khe.thu_giu(goc, "nang", "viec-2")
    assert phien2 is None  # đã có người giữ (chính tiến trình test, còn sống)
    phien.nha()
    phien3 = khe.thu_giu(goc, "nang", "viec-3")
    assert phien3 is not None
    phien3.nha()


def test_thu_giu_dung_duoc_nhu_context_manager(tmp_path):
    goc = str(tmp_path)
    phien = khe.thu_giu(goc, "nang", "viec-cm")
    assert phien is not None
    with phien as huy:
        assert isinstance(huy, threading.Event)
    assert khe.trang_thai(goc)["nang"] is None


# ── Lớp "api" — N khe song song ─────────────────────────────────────────────


def test_api_hai_lan_chay_song_song_lan_thu_ba_xep_hang(tmp_path):
    goc = str(tmp_path)
    _ghi_cai_dat(goc, {"lan_api": 2})
    assert khe.so_lan_api(goc) == 2

    p1 = khe.thu_giu(goc, "api", "viec-a")
    p2 = khe.thu_giu(goc, "api", "viec-b")
    assert p1 is not None and p2 is not None
    p3 = khe.thu_giu(goc, "api", "viec-c")
    assert p3 is None  # cả hai làn đều bận

    p1.nha()
    p3b = khe.thu_giu(goc, "api", "viec-c")
    assert p3b is not None
    p2.nha()
    p3b.nha()


def test_so_lan_api_doc_cai_dat_va_kep_1_4(tmp_path):
    goc = str(tmp_path)
    _ghi_cai_dat(goc, {"lan_api": 99})
    assert khe.so_lan_api(goc) == 4
    _ghi_cai_dat(goc, {"lan_api": 0})
    assert khe.so_lan_api(goc) == 1
    _ghi_cai_dat(goc, {"lan_api": "khong-phai-so"})
    # Giá trị hỏng -> lùi về công thức RAM (dùng ram_tong_gb truyền tay để bài
    # kiểm không phụ thuộc RAM thật của máy chạy CI).
    assert khe.so_lan_api(goc, ram_tong_gb=16.0) == 3  # floor((16-6)/3) = 3


def test_so_lan_api_khong_co_cai_dat_dung_cong_thuc_ram():
    goc = os.path.join("khong-ton-tai-" + str(time.time()))
    assert khe._tinh_lan_api_mac_dinh(6.0) == 1
    assert khe._tinh_lan_api_mac_dinh(9.0) == 1
    assert khe._tinh_lan_api_mac_dinh(15.0) == 3
    assert khe._tinh_lan_api_mac_dinh(30.0) == 4  # kẹp trần 4 dù công thức ra 8
    assert khe._tinh_lan_api_mac_dinh(None) == 1


# ── cho_toi_da -> KheHetGio ──────────────────────────────────────────────────


def _giu_o_luong_khac(goc):
    """Khe "nang" giữ bởi MỘT LUỒNG KHÁC (29/09/2026: cùng luồng lồng nhau giờ là
    TÁI NHẬP, xem test_khe_tai_nhap.py) — trả (Event nhả, luồng)."""
    da_giu, nha = threading.Event(), threading.Event()

    def _giu():
        with khe.giu(goc, "nang", "giu-lau", cho_toi_da=30):
            da_giu.set()
            nha.wait(10)
    t = threading.Thread(target=_giu)
    t.start()
    assert da_giu.wait(5)
    return nha, t


def test_cho_toi_da_het_gio_nem_loi(tmp_path):
    goc = str(tmp_path)
    nha, t = _giu_o_luong_khac(goc)
    try:
        with pytest.raises(khe.KheHetGio):
            with khe.giu(goc, "nang", "khong-kip", cho_toi_da=0.3,
                        nhip_kiem_giay=0.05):
                pass
    finally:
        nha.set()
        t.join(5)


def test_huy_dat_truoc_khi_xin_nem_kheDaHuy(tmp_path):
    goc = str(tmp_path)
    nha, t = _giu_o_luong_khac(goc)
    try:
        huy_ngoai = threading.Event()
        huy_ngoai.set()
        with pytest.raises(khe.KheDaHuy):
            with khe.giu(goc, "nang", "bi-huy-truoc", huy=huy_ngoai,
                        nhip_kiem_giay=0.05):
                pass
    finally:
        nha.set()
        t.join(5)


# ── trang_thai() ─────────────────────────────────────────────────────────────


def test_trang_thai_bao_dung_ai_dang_giu(tmp_path):
    goc = str(tmp_path)
    _ghi_cai_dat(goc, {"lan_api": 1})  # cố định 1 làn "api" để so được chính xác
    assert khe.trang_thai(goc) == {"nang": None, "api": [None], "cho": []}
    with khe.giu(goc, "nang", "viec-x", kenh="TL1") as _huy:
        tt = khe.trang_thai(goc)
        assert tt["nang"]["viec"] == "viec-x"
        assert tt["nang"]["kenh"] == "TL1"
        assert tt["nang"]["pid"] == os.getpid()
    assert khe.trang_thai(goc)["nang"] is None


# ── phụ trợ ──────────────────────────────────────────────────────────────────


def _ghi_cai_dat(goc: str, cai: dict) -> None:
    duong = os.path.join(goc, "workspace", "cai-dat.json")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(cai, tep)


def _doc_nhat_ky(goc: str):
    duong = khe.duong_nhat_ky(goc)
    if not os.path.isfile(duong):
        return []
    with open(duong, "r", encoding="utf-8") as tep:
        return [json.loads(dong) for dong in tep if dong.strip()]


# ── Suất JOB toàn máy (`giu_job`, 30/09/2026) ───────────────────────────────


def _ghi_tran_tong(goc: str, n) -> None:
    duong = os.path.join(goc, "workspace", "cai-dat.json")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump({"tran_api_tong": n}, tep)


class TestGiuJobToanMay:
    def test_tran_api_tong_mac_dinh_96_va_kep(self, tmp_path):
        goc = str(tmp_path)
        assert khe.tran_api_tong(goc) == 96
        _ghi_tran_tong(goc, 0)
        assert khe.tran_api_tong(goc) == 1
        _ghi_tran_tong(goc, 99999)
        assert khe.tran_api_tong(goc) == 512
        _ghi_tran_tong(goc, "khong-phai-so")
        assert khe.tran_api_tong(goc) == 96

    def test_khong_vuot_tran_tong_giua_nhieu_luong(self, tmp_path):
        goc = str(tmp_path)
        _ghi_tran_tong(goc, 3)
        dang = [0]
        cao_nhat = [0]
        khoa = threading.Lock()

        def mot():
            with khe.giu_job(goc, "image", tran_may_chu=189, cho_toi_da=20,
                             nhip_kiem_giay=0.02):
                with khoa:
                    dang[0] += 1
                    cao_nhat[0] = max(cao_nhat[0], dang[0])
                time.sleep(0.05)
                with khoa:
                    dang[0] -= 1

        luong = [threading.Thread(target=mot) for _ in range(12)]
        for t in luong:
            t.start()
        for t in luong:
            t.join(timeout=30)
        assert cao_nhat[0] == 3
        assert khe.so_job_dang_giu(goc, "image") == 0

    def test_tran_may_chu_thap_thi_theo_may_chu(self, tmp_path):
        """Máy chủ khai 1 (đo 16:25 ngày 30/09) → cả máy chỉ 1 job loại đó."""
        goc = str(tmp_path)
        with khe.giu_job(goc, "image", tran_may_chu=1) as n:
            assert n == 1
            with pytest.raises(khe.KheHetGio):
                with khe.giu_job(goc, "image", tran_may_chu=1, cho_toi_da=0.2,
                                 nhip_kiem_giay=0.02):
                    pass
            # Loại khác không chung suất.
            with khe.giu_job(goc, "video", tran_may_chu=1, cho_toi_da=1):
                pass

    def test_suat_cua_tien_trinh_chet_duoc_don(self, tmp_path):
        goc = str(tmp_path)
        thu_muc = khe.duong_thu_muc_job(goc, "image")
        os.makedirs(thu_muc, exist_ok=True)
        with open(os.path.join(thu_muc, "0.json"), "w", encoding="utf-8") as tep:
            json.dump({"pid": PID_GIA_DA_CHET, "bat_dau": time.time()}, tep)
        khe._DON_JOB.clear()
        with khe.giu_job(goc, "image", tran_may_chu=1, cho_toi_da=5,
                         nhip_kiem_giay=0.02):
            assert khe.so_job_dang_giu(goc, "image") == 1

    def test_kiem_dung_nem_len_nguyen(self, tmp_path):
        goc = str(tmp_path)

        class _Dung(Exception):
            pass

        def kiem():
            raise _Dung()

        with khe.giu_job(goc, "image", tran_may_chu=1):
            with pytest.raises(_Dung):
                with khe.giu_job(goc, "image", tran_may_chu=1, kiem_dung=kiem):
                    pass


# ── Cờ "đang chờ tải lên" (04/10/2026) ──────────────────────────────────────


def test_co_cho_tai_len_chan_san_xuat_nhung_khong_chan_viec_dang(tmp_path):
    goc = str(tmp_path)
    assert khe.co_cho_tai_len(goc) is False
    khe.dat_co_cho_tai_len(goc, True)
    assert khe.co_cho_tai_len(goc) is True
    assert khe.thu_giu(goc, "nang", "dung") is None            # sản xuất nhường dù khe trống
    assert khe.thu_giu(goc, "nang", "quet", uu_tien=1) is None  # quét cũng nhường
    p = khe.thu_giu(goc, "nang", "tai_len", uu_tien=1)          # việc đăng vào ngay
    assert p is not None
    p.nha()
    khe.dat_co_cho_tai_len(goc, False)                          # tải xong gỡ cờ
    assert khe.co_cho_tai_len(goc) is False
    q = khe.thu_giu(goc, "nang", "dung")
    assert q is not None
    q.nha()


def test_co_cho_tai_len_het_han_thi_san_xuat_chay_tiep(tmp_path):
    goc = str(tmp_path)
    khe.dat_co_cho_tai_len(goc, True)
    duong = khe._duong_co_cho_tai_len(goc)
    du = json.load(open(duong, encoding="utf-8"))
    du["luc"] = time.time() - khe.TUOI_CO_CHO_TAI_LEN_GIAY - 5
    json.dump(du, open(duong, "w", encoding="utf-8"))
    assert khe.co_cho_tai_len(goc) is False
    q = khe.thu_giu(goc, "nang", "dung")
    assert q is not None
    q.nha()
