"""Test chiến trường: ảnh chụp lịch sử, công thức cơ hội, đề xuất tấn công (dữ liệu giả, thư mục tạm)."""
import datetime as dt

from core import chien_truong as ct
from core import chien_truong_lich_su as ls


def _du(thi_phan=1.0):
    return {"tong": {"dich": 1000, "ta": 10, "thi_phan": thi_phan},
            "vung": [{"ma": "a", "dich": 600, "ta": 10, "thi_phan": 1.6}, {"ma": "b", "dich": 400, "ta": 0, "thi_phan": 0}],
            "dich_top": [{"kenh": "X%d" % i, "view": 100 - i, "thi_phan": 5.0 - i * .1} for i in range(15)],
            "quan": [{"ma": "TL1", "gio_xem": 5, "dang_ky": 2, "view_28": 10}]}


def test_anh_chup_them_va_thay_cung_ngay(tmp_path):
    g = str(tmp_path)
    ls.ghi_anh_chup(g, _du(1.0), "2026-10-01")
    ls.ghi_anh_chup(g, _du(2.0), "2026-10-02")
    ls.ghi_anh_chup(g, _du(3.0), "2026-10-02")           # cùng ngày → thay
    dong = ls._doc_dong(g)
    assert [x["ngay"] for x in dong] == ["2026-10-01", "2026-10-02"]
    assert dong[1]["tong"]["thi_phan"] == 3.0
    assert len(dong[0]["dich_top"]) == 10 and dong[0]["quan"]["TL1"]["view_28"] == 10
    assert ls.co_anh_hom_nay(g, "2026-10-02") and not ls.co_anh_hom_nay(g, "2026-10-09")


def test_doc_lich_su_loc_ngay_va_file_thieu(tmp_path):
    g = str(tmp_path)
    assert ls.doc_lich_su(g) == [] and ls.chuoi_gon(g) == []
    hom = dt.date.today()
    ls.ghi_anh_chup(g, _du(), (hom - dt.timedelta(days=100)).isoformat())
    ls.ghi_anh_chup(g, _du(), hom.isoformat())
    assert len(ls.doc_lich_su(g, 60)) == 1
    c = ls.chuoi_gon(g, 30)
    assert c[0]["ngay"] == hom.isoformat() and c[0]["top_kenh"] == "X0"


def _vung(ma, dich, nong=100, top=0.5, ta=0, so_ta=0, ta_kenh=()):
    return {"ma": ma, "ten": ma, "dich": dich, "nong": nong, "ta": ta, "so_ta": so_ta, "thi_phan": 0.0,
            "dich_manh": [{"kenh": "K", "view": dich * top}], "ta_kenh": list(ta_kenh)}


def test_co_hoi_don_dieu_theo_cau():
    ds = [_vung("a", 1000), _vung("b", 100000), _vung("c", 10000000)]
    ct.tinh_co_hoi(ds)
    assert ds[0]["co_hoi"] < ds[1]["co_hoi"] < ds[2]["co_hoi"]
    assert all(0 <= z["co_hoi"] <= 100 for z in ds)


def test_co_hoi_dich_yeu_va_da_va_chan():
    ds = [_vung("manh", 1e6, top=0.9), _vung("yeu", 1e6, top=0.2)]
    ct.tinh_co_hoi(ds)
    assert ds[1]["co_hoi"] > ds[0]["co_hoi"]
    ds = [_vung("cham", 1e6, nong=10), _vung("nong", 1e6, nong=10000)]
    ct.tinh_co_hoi(ds)
    assert ds[1]["co_hoi"] > ds[0]["co_hoi"]
    dom = _vung("dom", 1e6, so_ta=5, ta=1e6)
    dom["thi_phan"] = 60.0
    co = _vung("co", 1e6, so_ta=1, ta=10)
    co["thi_phan"] = 0.1
    ct.tinh_co_hoi([dom, co])
    assert co["co_hoi"] > dom["co_hoi"]


def test_de_xuat_hinh_dang_va_uu_tien_cung_tep():
    ds = [_vung("a", 1e6, ta_kenh=["TL1"], so_ta=1), _vung("b", 1.2e6), _vung("c", 1e6, ta_kenh=["TL2"], so_ta=1),
          _vung(ct.KHAC, 9e7)]
    ct.tinh_co_hoi(ds)
    quan = [{"ma": "TL1", "ten": "k1", "so_video": 3}, {"ma": "TL9", "ten": "k9", "so_video": 0}]
    r = ct.de_xuat_tan_cong(ds, quan)
    assert [x["kenh"] for x in r] == ["TL1"]               # kênh chưa có video bị bỏ
    v = r[0]["vung"]
    assert len(v) == 2 and all({"ma", "ten", "co_hoi", "ly_do"} <= set(x) for x in v)
    assert ct.KHAC not in [x["ma"] for x in v]
    assert v[0]["ma"] == "a"                               # vùng kênh đã có video lên đầu
    assert v[0]["diem"] >= v[1]["diem"]


def test_chia_vung_ai_mot_lan_moi_ngay(tmp_path, monkeypatch):
    from core import chien_truong_ai as ai
    monkeypatch.setattr(ai, "TEP", str(tmp_path / "vung-ai.json"))
    goi = []
    monkeypatch.setattr(ai, "chay", lambda n, log=None: goi.append(n) or {"da_gan": 7})
    monkeypatch.setattr(ai, "gop", lambda *a, **k: {"truoc": 20, "sau": 9})
    bg = dt.datetime(2026, 10, 6, 7, 0)
    assert ai.chay_hang_ngay(lambda *_: None, bg) == "chia vùng AI: gán 7 video mới"
    assert ai.chay_hang_ngay(lambda *_: None, bg) == ""                      # cùng ngày → không gọi lại
    assert goi == [ai.NGAY_TOI_DA]
    ai.ghi(dict(ai.doc(), vung_moi={"moi-%d" % i: "v" for i in range(13)}))   # vùng vụn vượt trần → gộp
    assert "gộp 20→9" in ai.chay_hang_ngay(lambda *_: None, bg + dt.timedelta(days=1))


def test_mo_ta_ngach_khong_cung_chu_de(monkeypatch):
    monkeypatch.setattr(ct, "_cac_kenh", lambda: [])
    assert ct.mo_ta_ngach() == {"ten": "Ngách", "ngon_ngu": ""}
    from core import chien_truong_ai as ai
    assert "psycholog" not in ai._de_bai({"a": "A"}, [{"tieu_de": "t"}]).lower()


def test_de_xuat_toa_kenh_ra_nhieu_vung():
    """8 kênh không được cùng dồn 1 vùng: lệnh chính của mỗi kênh khác nhau khi còn đủ vùng tốt (phủ cả ngách)."""
    ds = [_vung("v%d" % i, 1e6 - i * 1e4) for i in range(10)]
    ct.tinh_co_hoi(ds)
    quan = [{"ma": "K%d" % i, "ten": "", "so_video": 1} for i in range(8)]
    r = ct.de_xuat_tan_cong(ds, quan)
    chinh = [x["vung"][0]["ma"] for x in r]
    assert len(set(chinh)) == 8 and all(len(x["vung"]) == 2 for x in r)
    # vùng vượt trội hẳn thì vẫn được cấp cho nhiều kênh (chịu phạt) — không cấm tuyệt đối
    ds2 = [_vung("sieu", 1e8), _vung("yeu1", 1e3), _vung("yeu2", 1e3)]
    ct.tinh_co_hoi(ds2)
    r2 = ct.de_xuat_tan_cong(ds2, quan[:3])
    assert sum(1 for x in r2 if x["vung"][0]["ma"] == "sieu") >= 2
