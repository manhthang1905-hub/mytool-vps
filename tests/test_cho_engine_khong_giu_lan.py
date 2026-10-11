"""12/10/2026: lượt CHỜ ENGINE phía máy chủ (TTS sập/đóng/hàng chờ dài) NHẢ LÀN, chờ NGOÀI tiến trình.

Sự cố 10/10/2026: TTS của cổng tắt ~8 giờ, 4 lượt ngồi ở khâu giọng giữ cả 4 làn API. Giờ: khâu ghi dấu
`workspace/tu-chay/cho-engine/<engine>/<kênh>.json`, `auto.chay` dừng gọn, tiến trình thoát; điều phối
không sinh kênh đó tới giờ thăm dò; L3 không tính lần nhặt thăm dò. Không mạng, không tiến trình thật,
đồng hồ giả.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time
from types import SimpleNamespace

import pytest

from core import auto, auto_khau as ak, cho_engine, dieu_phoi, khe, su_co, tu_chay
from core import su_kien_truc_quan
from core.kenh import Kenh
from core.su_co import LoiChoEngine

from tests.test_dieu_phoi import _kenh, _vps

# Câu THẬT của cổng ngày 10/10/2026.
TAM_DONG = 'Dịch vụ "tts" đang tạm đóng để khắc phục sự cố. Bạn KHÔNG bị trừ tiền. Vui lòng thử lại sau.'
KHONG_ENGINE = 'Hệ thống không có engine nào phục vụ loại yêu cầu "tts".'
HANG_CHO_6G = ("Hàng chờ giọng nói đang quá dài: yêu cầu này sẽ đứng thứ 24 và ước tính phải chờ khoảng "
               "6 giờ 4 phút — dài hơn mức hệ thống cho phép. Bạn KHÔNG bị trừ tiền.")
HANG_CHO_CUT = ("Hàng chờ giọng nói đang quá dài: yêu cầu này sẽ đứng thứ 24 và ước tính phải chờ khoảng "
                "17 giờ 47 ph")
NHA_MAY = ("Nhà máy giọng nói hiện không có chỗ nào nhận việc nên yêu cầu này chưa được nhận. "
           "Bạn KHÔNG bị trừ tiền.")


# ── su_co: loại mới, nhịp rỗng ──────────────────────────────────────────────


def test_loi_cho_engine_phan_loai_ca_khi_doc_lai_tu_so():
    loi = LoiChoEngine("tts", TAM_DONG)
    assert su_co.phan_loai(loi) == su_co.CHO_ENGINE
    assert str(loi).startswith(su_co.DAU_CHO_ENGINE)
    # sổ ngày chỉ lưu CHUỖI (kèm tiền tố tên khâu) — vẫn nhận ra
    assert su_co.phan_loai(RuntimeError("Dừng ở “Đọc thành giọng”: " + str(loi))) == su_co.CHO_ENGINE
    assert su_co.CHO_ENGINE in tu_chay._LOAI_LOI_CHO_NGOAI


def test_goi_kien_nhan_nem_ngay_khong_ngu():
    ngu = []

    def ham():
        raise LoiChoEngine("tts", TAM_DONG)

    with pytest.raises(LoiChoEngine):
        su_co.goi_kien_nhan(ham, ngu=ngu.append)
    assert ngu == []


# ── cho_engine: nhận dạng ───────────────────────────────────────────────────


def test_uoc_hang_cho():
    assert cho_engine.uoc_hang_cho_giay(HANG_CHO_6G) == 6 * 3600 + 4 * 60
    assert cho_engine.uoc_hang_cho_giay(HANG_CHO_CUT) == 17 * 3600 + 47 * 60
    assert cho_engine.uoc_hang_cho_giay("ước tính phải chờ khoảng 45 phút") == 45 * 60
    assert cho_engine.uoc_hang_cho_giay("vui lòng chờ khoảng vài phút") is None
    assert cho_engine.uoc_hang_cho_giay(TAM_DONG) is None


@pytest.mark.parametrize("cau", [TAM_DONG, KHONG_ENGINE, HANG_CHO_6G, HANG_CHO_CUT,
                                 "Kho tài khoản giọng nói đã dùng hết hạn mức credit hôm nay."])
def test_chuyen_ra_cho_ngay(cau):
    ly_do, _uoc = cho_engine.ly_do_cho_ngay(RuntimeError(cau))
    assert ly_do


@pytest.mark.parametrize("cau", [NHA_MAY, "ước tính phải chờ khoảng 10 phút. Bạn KHÔNG bị trừ tiền.",
                                 "502 Bad Gateway", "Không đủ số dư, nạp thêm",
                                 "đợi 25 phút mà máy chủ vẫn chưa trả kết quả"])
def test_khong_chuyen_ra_cho_ngay(cau):
    assert cho_engine.ly_do_cho_ngay(RuntimeError(cau)) == ("", None)


def test_canh_engine_cho_ngan_roi_moi_chuyen():
    dong = {"t": 1000.0}
    canh = cho_engine.CanhEngine("tts", cho_ngan=300, dong_ho=lambda: dong["t"])
    canh.xet(RuntimeError(NHA_MAY))                    # lỗi đầu: bắt đầu đếm
    dong["t"] += 299
    canh.xet(RuntimeError("502 Bad Gateway"))          # vẫn trong chờ ngắn
    canh.tot()                                         # có lời gọi thành công → đếm lại
    dong["t"] += 200
    canh.xet(RuntimeError(NHA_MAY))
    dong["t"] += 299
    canh.xet(RuntimeError(NHA_MAY))
    canh.xet(RuntimeError("Không đủ số dư"))           # ví: không phải engine, không đếm
    dong["t"] += 1
    with pytest.raises(LoiChoEngine) as bat:
        canh.xet(RuntimeError(NHA_MAY))
    assert bat.value.engine == "tts" and "5 phút" in bat.value.ly_do
    with pytest.raises(LoiChoEngine):
        canh.xet(RuntimeError(TAM_DONG))                # câu "tạm đóng": ngay, không đợi


def test_tham_do_nhanh():
    def client(me=None, loi=None):
        def request(_m, _p):
            if loi:
                raise loi
            return me
        return SimpleNamespace(request=request)

    assert "= 0" in cho_engine.tham_do_nhanh(client({"limits": {"concurrent_jobs": {"tts": 0}}}), "tts")
    ly = cho_engine.tham_do_nhanh(client({"limits": {"concurrent_jobs": {"tts": 0},
                                                     "concurrent_jobs_detail": {"tts": {"reason": "bảo trì"}}}}),
                                  "tts")
    assert "bảo trì" in ly
    assert cho_engine.tham_do_nhanh(client({"limits": {"concurrent_jobs": {"tts": 1}}}), "tts") == ""
    assert cho_engine.tham_do_nhanh(client({"limits": {}}), "tts") == ""          # không biết → để gọi thật
    assert cho_engine.tham_do_nhanh(client(loi=OSError("mạng")), "tts") == ""
    assert cho_engine.tham_do_nhanh(None, "tts") == ""


# ── khe: dấu chờ engine ─────────────────────────────────────────────────────


def test_dau_cho_engine_ghi_doc_xoa(tmp_path):
    goc = str(tmp_path)
    assert khe.doc_cho_engine(goc) == {}
    khe.ghi_cho_engine(goc, "tts", "K1", {"ma_luot": "0025", "tham_do_luc": 2000.0})
    assert os.path.isfile(os.path.join(goc, "workspace", "tu-chay", "cho-engine", "tts", "K1.json"))
    du = khe.doc_cho_engine(goc)["K1"]
    assert (du["engine"], du["kenh"], du["ma_luot"], du["tham_do_luc"]) == ("tts", "K1", "0025", 2000.0)
    # kênh chờ hai engine → lấy giờ thăm dò MUỘN nhất
    khe.ghi_cho_engine(goc, "image", "K1", {"tham_do_luc": 3000.0})
    assert khe.doc_cho_engine(goc)["K1"]["engine"] == "image"
    assert khe.doc_cho_engine(goc, "tts")["K1"]["engine"] == "tts"
    khe.xoa_cho_engine(goc, "image", "K1")
    khe.xoa_cho_engine(goc, "tts", "K1")
    assert khe.doc_cho_engine(goc) == {}


def test_dau_cho_engine_qua_cu_bi_don(tmp_path):
    goc = str(tmp_path)
    khe.ghi_cho_engine(goc, "tts", "K1", {"tham_do_luc": 1.0})
    duong = khe.duong_cho_engine(goc, "tts", "K1")
    with open(duong, "r", encoding="utf-8") as tep:
        du = json.load(tep)
    du["luc"] = time.time() - khe.TUOI_TOI_DA_CHO_ENGINE_GIAY - 1
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump(du, tep)
    assert khe.doc_cho_engine(goc) == {}
    assert not os.path.exists(duong)


# ── cho_engine.bao_cho: lần chờ, giờ thăm dò, báo người một lần ─────────────


def test_bao_cho_dem_lan_giu_moc_va_bao_mot_lan(tmp_path, monkeypatch):
    goc = str(tmp_path)
    bao = []
    from core import bao_dong

    monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: bao.append(a[0]))
    t0 = 1_800_000_000.0
    nhat = []
    du = cho_engine.bao_cho(goc, "K1", LoiChoEngine("tts", TAM_DONG), ma_luot="0025",
                            khau="giong-doc", ghi=nhat.append, bay_gio=t0)
    assert du["so_lan"] == 1 and du["tham_do_luc"] == t0 + 30 * 60 and du["tu_luc"] == t0
    assert any("[CHỜ ENGINE]" in d and "NHẢ LÀN" in d for d in nhat)
    # hàng chờ khai 6 giờ → giãn tới tối đa 2 giờ
    du = cho_engine.bao_cho(goc, "K1", LoiChoEngine("tts", HANG_CHO_6G, 6 * 3600.0), ma_luot="0025",
                            bay_gio=t0 + 1800)
    assert du["so_lan"] == 2 and du["tu_luc"] == t0 and du["tham_do_luc"] == t0 + 1800 + 2 * 3600
    for i in range(3, 6):
        du = cho_engine.bao_cho(goc, "K1", LoiChoEngine("tts", TAM_DONG), ma_luot="0025",
                                bay_gio=t0 + 3600 * (i - 1))
    assert du["so_lan"] == 5 and du["tham_do_luc"] - (t0 + 3600 * 4) == 60 * 60   # lần ≥5: 60'
    assert bao == []
    cho_engine.bao_cho(goc, "K1", LoiChoEngine("tts", TAM_DONG), ma_luot="0025", bay_gio=t0 + 6 * 3600)
    cho_engine.bao_cho(goc, "K1", LoiChoEngine("tts", TAM_DONG), ma_luot="0025", bay_gio=t0 + 7 * 3600)
    assert bao == ["cho_engine_lau"]                                              # đúng một lần
    # lượt KHÁC của kênh → đếm lại từ đầu
    du = cho_engine.bao_cho(goc, "K1", LoiChoEngine("tts", TAM_DONG), ma_luot="0026", bay_gio=t0 + 8 * 3600)
    assert du["so_lan"] == 1 and du["tu_luc"] == t0 + 8 * 3600
    cho_engine.xoa(goc, "tts", "K1")
    assert cho_engine.dau_cua(goc, "tts", "K1") == {}


# ── khâu giọng đọc thật (đồ giả mạng) ───────────────────────────────────────


class _TtsGia:
    def __init__(self, loi=None):
        self.loi = loi            # callable(lan) -> Exception | None
        self.goi = []

    def create(self, **kw):
        self.goi.append(kw)
        e = self.loi(len(self.goi)) if self.loi else None
        if e is not None:
            raise e
        return {"id": "job_{0}".format(len(self.goi)), "status": "succeeded"}


def _khau(monkeypatch, tmp_path, tts, *, me=None, so_cau=1, kich_ban=None):
    goc = str(tmp_path)
    d = tmp_path / "PROJECTS" / "AUTO" / "K1" / "0025"
    d.mkdir(parents=True)
    (d / "1-kich-ban.txt").write_text(
        kich_ban or "\n\n".join(["Câu kịch bản số {0}.".format(i) for i in range(so_cau)]), encoding="utf-8")
    luot = auto.LuotChay(ma_kenh="K1", ma_luot="0025", thu_muc=str(d))
    dong = {"t": 1_800_000_000.0}
    ngu = []

    def ngu_gia(g):
        ngu.append(g)
        dong["t"] += g

    def request(_m, _p):
        if me is None:
            raise OSError("không hỏi")
        return me

    client = SimpleNamespace(tts=tts, request=request)
    nhat = []
    bc = ak.BoiCanh(goc=goc, kenh=Kenh(ma="K1", voice_id="v1"), goi_chat=lambda *a, **k: "",
                    client=client, on_log=nhat.append, ngu=ngu_gia)
    monkeypatch.setattr(ak, "_gio_may", lambda: dong["t"])
    monkeypatch.setattr(cho_engine, "_gio", lambda: dong["t"])
    monkeypatch.setattr(ak, "_chen_the_cam_xuc", lambda _bc, _l, chu: chu)
    monkeypatch.setattr(ak, "SoTheoDoi", lambda *_a, **_k: SimpleNamespace(dong=lambda: None))
    monkeypatch.setattr(ak, "_so_luong", lambda *_a, **_k: 3)
    monkeypatch.setattr(ak, "_cho_job", lambda _bc, job, **kw: job)

    def tai(_bc, _goi, tep, _doc, _ten=""):
        with open(tep, "wb") as t:
            t.write(b"mp3")
        return tep

    monkeypatch.setattr(ak, "_tai_ket_qua_dat_lai", tai)
    monkeypatch.setattr(ak, "_bi_xen_am_dau", lambda *_a: False)
    monkeypatch.setattr(ak, "_noi_mp3", lambda _bc, _m, dich, **_k: open(dich, "wb").close())
    monkeypatch.setattr(ak, "_doi_cao_do_giong", lambda *_a: False)
    monkeypatch.setattr(ak, "_lam_sach_ket_qua", lambda *_a: None)
    monkeypatch.setattr(ak, "_ghi_phan_giong", lambda *_a: 0)
    return goc, bc, luot, ak._khau_giong_doc(bc), dong, ngu, nhat


def test_tam_dong_thi_ghi_dau_va_thoat_ngay(monkeypatch, tmp_path):
    tts = _TtsGia(lambda _n: RuntimeError(TAM_DONG))
    goc, _bc, luot, lam, dong, ngu, _nhat = _khau(monkeypatch, tmp_path, tts)
    t0 = dong["t"]
    with pytest.raises(LoiChoEngine):
        lam(luot, None)
    assert len(tts.goi) == 1 and sum(ngu) == 0, "không ngồi đợi thang ~14 phút trong lượt"
    du = khe.doc_cho_engine(goc)["K1"]
    assert (du["engine"], du["ma_luot"], du["khau"], du["so_lan"]) == ("tts", "0025", "giong-doc", 1)
    assert du["tham_do_luc"] == t0 + 30 * 60 and "tạm đóng" in du["ly_do"]


def test_nha_may_nghi_cho_ngan_5_phut_roi_moi_thoat(monkeypatch, tmp_path):
    tts = _TtsGia(lambda _n: RuntimeError(NHA_MAY))
    goc, _bc, luot, lam, dong, ngu, _nhat = _khau(monkeypatch, tmp_path, tts)
    t0 = dong["t"]
    with pytest.raises(LoiChoEngine):
        lam(luot, None)
    da_cho = dong["t"] - t0
    assert cho_engine.GIAY_CHO_NGAN <= da_cho < 10 * 60, da_cho     # thang NHA_MAY_NGHI ~16' bị cắt
    assert len(tts.goi) >= 2
    assert khe.doc_cho_engine(goc)["K1"]["so_lan"] == 1


def test_nhieu_doan_tam_dong_ca_me_dung_giu_doan_da_co(monkeypatch, tmp_path):
    """Nhiều đoạn đọc song song: đoạn có sẵn trên đĩa không gửi lại; một luồng gặp "tạm đóng" → gạt
    chốt, cả mẻ dừng, ném đúng `LoiChoEngine` (không phải `Cancelled` như người bấm Dừng)."""
    tts = _TtsGia(lambda _n: RuntimeError(TAM_DONG))
    dai = "\n\n".join(["Đoạn số {0}. ".format(i) + "あ" * 700 for i in range(5)])
    goc, _bc, luot, lam, _dong, ngu, _nhat = _khau(monkeypatch, tmp_path, tts, kich_ban=dai)
    thu = os.path.join(luot.thu_muc, "2-doan")
    os.makedirs(thu)
    with open(os.path.join(thu, "001.mp3"), "wb") as t:
        t.write(b"cu")
    with pytest.raises(LoiChoEngine):
        lam(luot, None)
    with open(os.path.join(thu, "001.mp3"), "rb") as t:
        assert t.read() == b"cu"
    assert all("Đoạn số 0" not in kw["text"] for kw in tts.goi)
    assert 1 <= len(tts.goi) <= 4 and sum(ngu) == 0
    assert khe.doc_cho_engine(goc)["K1"]["so_lan"] == 1


def test_sinh_lai_tham_do_re_truoc_khi_gui_viec(monkeypatch, tmp_path):
    tts = _TtsGia()
    goc, _bc, luot, lam, dong, _ngu, _nhat = _khau(
        monkeypatch, tmp_path, tts, me={"limits": {"concurrent_jobs": {"tts": 0}}})
    khe.ghi_cho_engine(goc, "tts", "K1", {"ma_luot": "0025", "so_lan": 1, "tu_luc": dong["t"] - 1800,
                                         "tham_do_luc": dong["t"] - 1})
    with pytest.raises(LoiChoEngine):
        lam(luot, None)
    assert tts.goi == [], "nhà máy còn dừng (trần 0) → không gửi việc nào"
    du = khe.doc_cho_engine(goc)["K1"]
    assert du["so_lan"] == 2 and du["tu_luc"] == dong["t"] - 1800


def test_sinh_lai_engine_co_lai_thi_lam_tiep_va_go_dau(monkeypatch, tmp_path):
    tts = _TtsGia()
    goc, _bc, luot, lam, dong, _ngu, nhat = _khau(
        monkeypatch, tmp_path, tts, me={"limits": {"concurrent_jobs": {"tts": 3}}})
    khe.ghi_cho_engine(goc, "tts", "K1", {"ma_luot": "0025", "so_lan": 3, "tham_do_luc": dong["t"] - 1})
    ra = lam(luot, None)
    assert ra["so_doan"] == 1 and len(tts.goi) == 1
    assert os.path.isfile(os.path.join(luot.thu_muc, "2-doan", "001.mp3"))
    assert khe.doc_cho_engine(goc) == {}
    assert any("thăm dò engine giọng" in d for d in nhat)


def test_auto_chay_dung_gon_khong_dot_luot_thu(tmp_path):
    goc = str(tmp_path)
    luot = auto.moi_luot(goc, "K1", "0025")
    goi = []

    def giong(_l, _tt):
        goi.append(1)
        raise LoiChoEngine("tts", TAM_DONG)

    sau = []
    viec = {"kich-ban": lambda _l, _tt: {}, "giong-doc": giong,
            "phu-de": lambda _l, _tt: sau.append(1)}
    nhat = []
    ngu = []
    auto.chay(luot, viec, on_log=nhat.append, ngu=ngu.append)
    tt = luot.tt("giong-doc")
    assert goi == [1] and ngu == [] and sau == []
    assert tt.trang_thai == auto.HONG and tt.loi.startswith(su_co.DAU_CHO_ENGINE)
    assert any(d.startswith("[CHỜ ENGINE]") for d in nhat)
    assert su_co.phan_loai(RuntimeError(auto.tom_tat(luot))) == su_co.CHO_ENGINE


# ── tu_chay: L3 không tính lần thăm dò ─────────────────────────────────────


def _run_cho(so_lan=3, gio_truoc=50):
    bay = _dt.datetime.now()
    return {"ma_luot": "0025",
            "san_xuat": {"loi_dung": "Dừng ở “Đọc thành giọng”: câu lạ", "khau_hong": ["giong-doc"],
                         "cho_engine": {"engine": "tts", "luc": (bay - _dt.timedelta(hours=8)).timestamp(),
                                        "tu": "2026-10-10T12:30:00", "tham_do": "2026-10-10T21:00:00"}},
            "phuc_hoi": {"so_lan": so_lan, "loai_loi_truoc": "chet",
                         "lan_dau_luc": (bay - _dt.timedelta(hours=gio_truoc)).timestamp()}}


def test_l3_luot_cho_engine_khong_bi_bo():
    hom = _dt.date.today()
    run = _run_cho()
    run["san_xuat"]["loi"] = "lỗi lạ không rõ"
    assert tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom, hom.isoformat()) == ""
    # đối chứng: bỏ dấu chờ engine thì trần chặn như cũ
    run["san_xuat"].pop("cho_engine")
    assert tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom, hom.isoformat())
    # cửa sổ quét 7 ngày vẫn là lưới an toàn cuối
    run = _run_cho()
    cu = (hom - _dt.timedelta(days=tu_chay.SO_NGAY_QUET_LUOT_CHUA_XONG - 1)).isoformat()
    assert "cửa sổ" in tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom, cu)


def test_l3_gio_cho_engine_khong_tinh_vao_tran_48_gio():
    hom = _dt.date.today()
    run = _run_cho(so_lan=1, gio_truoc=50)
    tu_chay._ghi_nhan_tham_do_engine(run)
    assert run["phuc_hoi"]["so_lan"] == 1, "thăm dò không tăng số lần phục hồi"
    assert 7.9 * 3600 < run["phuc_hoi"]["giay_cho_engine"] < 8.1 * 3600
    run["san_xuat"].pop("cho_engine")        # engine có lại, lượt hỏng vì chuyện khác
    run["san_xuat"]["loi_dung"] = TAM_DONG
    assert tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom, hom.isoformat()) == ""   # 50h − 8h chờ < 48h
    run["phuc_hoi"]["giay_cho_engine"] = 0
    assert "48" in tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom, hom.isoformat())


def test_ghi_cho_engine_vao_so_va_go(tmp_path):
    goc = str(tmp_path)
    nhat = []
    run = {"san_xuat": {"xong_het": False, "da_chay": True}}
    khe.ghi_cho_engine(goc, "tts", "K1", {"ma_luot": "0025", "tham_do": "2026-10-10T13:00:00",
                                         "tham_do_luc": 1.0, "ly_do": TAM_DONG})
    tu_chay._ghi_cho_engine_vao_so(goc, "K1", "0024", run, nhat.append)   # dấu của lượt khác
    assert "cho_engine" not in run["san_xuat"]
    tu_chay._ghi_cho_engine_vao_so(goc, "K1", "0025", run, nhat.append)
    assert run["san_xuat"]["cho_engine"]["engine"] == "tts"
    assert "chờ engine tts" in tu_chay._tom_tat_dong("K1", dict(run, ma_luot="0025", nguon={}), "that")
    khe.xoa_cho_engine(goc, "tts", "K1")
    tu_chay._ghi_cho_engine_vao_so(goc, "K1", "0025", run, nhat.append)
    assert "cho_engine" not in run["san_xuat"]


def test_bo_luot_go_dau_cho_engine(tmp_path):
    goc = str(tmp_path)
    khe.ghi_cho_engine(goc, "tts", "K1", {"ma_luot": "0025", "tham_do_luc": 1.0})
    tu_chay._go_dau_cho_engine(goc, "K1", {"ma_luot": "0099"})
    assert "K1" in khe.doc_cho_engine(goc)
    tu_chay._go_dau_cho_engine(goc, "K1", {"ma_luot": "0025"})
    assert khe.doc_cho_engine(goc) == {}


# ── dieu_phoi: lượt chờ engine không giữ làn, sinh lại khi tới giờ thăm dò ──


BAY_GIO = _dt.datetime(2026, 10, 10, 13, 0)


def _may(goc, so_kenh, cho, *, tham_do_sau_phut, **cai):
    _vps(goc, lan_api=4, **cai)
    ma = ["K{0}".format(i) for i in range(1, so_kenh + 1)]
    for m in ma:
        _kenh(goc, m)
    for m in ma[:cho]:
        khe.ghi_cho_engine(goc, "tts", m, {
            "ma_luot": "0001", "tham_do_luc": (BAY_GIO + _dt.timedelta(minutes=tham_do_sau_phut)).timestamp(),
            "tham_do": (BAY_GIO + _dt.timedelta(minutes=tham_do_sau_phut)).isoformat()})
    return ma


def _nhip(goc, monkeypatch, luot_do):
    monkeypatch.setattr(dieu_phoi, "_co_luot_do", lambda _g, ma, _d: ma in luot_do)
    sinh = []
    nhat = []
    ra = dieu_phoi.nhip(goc, bay_gio=BAY_GIO, ram=10.0, dia_gb=30.0,
                        sinh=lambda g, m: sinh.append(m) or 5000 + len(sinh), log=nhat.append)
    return ra, sinh, nhat


def test_nhip_4_luot_cho_tts_khong_giu_lan_kenh_khac_vao_lam(tmp_path, monkeypatch):
    """Đúng cảnh 10/10: 4 kênh kẹt ở giọng, 2 kênh cần viết kịch bản → giờ 2 kênh kia được sinh."""
    goc = str(tmp_path)
    _may(goc, 6, 4, tham_do_sau_phut=25)
    ra, sinh, nhat = _nhip(goc, monkeypatch, {"K1", "K2", "K3", "K4"})
    assert ra["so_cho_engine"] == 4 and ra["so_dang"] == 0
    assert sinh == ["K5", "K6"]
    k1 = next(c for c in ra["kenh"] if c["ma"] == "K1")
    assert k1["ly_do"] == "chờ engine tts tới 13:25 (đã nhả làn)" and not k1["chay"]
    assert any("4 chờ engine (đã nhả làn)" in d for d in nhat)


def test_nhip_toi_gio_tham_do_thi_sinh_lai_luot_do_truoc(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _may(goc, 6, 4, tham_do_sau_phut=-1)
    ra, sinh, _nhat = _nhip(goc, monkeypatch, {"K1", "K2", "K3", "K4"})
    assert sinh == ["K1", "K2", "K3", "K4"], "lượt dở (thăm dò) đi trước, đúng 4 làn"
    assert ra["so_cho_engine"] == 0
    assert all(c["ly_do"] == "lượt dở — thăm dò lại engine tts" for c in ra["kenh"] if c["ma"] in sinh)


def test_nhip_tham_do_van_xep_lan_nhu_luot_thuong(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _may(goc, 6, 4, tham_do_sau_phut=-1)
    # 2 kênh đang chạy thật (giữ khoá kênh) → chỉ còn 2 làn
    for m in ("K5", "K6"):
        kh = os.path.join(goc, "CHANNEL", m, "tu-chay", ".khoa")
        os.makedirs(os.path.dirname(kh), exist_ok=True)
        with open(kh, "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    ra, sinh, _nhat = _nhip(goc, monkeypatch, {"K1", "K2", "K3", "K4"})
    assert sinh == ["K1", "K2"] and ra["lan_trong"] == 2


def test_dau_cua_kenh_khong_co_luot_do_bi_bo_qua(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _may(goc, 2, 1, tham_do_sau_phut=60)
    ra, sinh, _nhat = _nhip(goc, monkeypatch, set())
    assert "K1" in sinh and ra["so_cho_engine"] == 0


# ── trực quan ───────────────────────────────────────────────────────────────


def test_truc_quan_doc_kenh_cho_engine(tmp_path):
    goc = str(tmp_path)
    khe.ghi_cho_engine(goc, "tts", "K1", {"ma_luot": "0025", "tham_do": "2026-10-10T13:30:00",
                                         "tu": "2026-10-10T12:30:00", "so_lan": 2, "ly_do": TAM_DONG,
                                         "tham_do_luc": 1.0})
    ds = su_kien_truc_quan.cho_engine(goc, _dt.datetime.now())
    assert ds == [{"kenh": "K1", "engine": "tts", "tham_do": "2026-10-10 13:30", "tu": "2026-10-10 12:30",
                   "so_lan": 2, "ly_do": ds[0]["ly_do"]}]
    assert "tạm đóng" in ds[0]["ly_do"]
