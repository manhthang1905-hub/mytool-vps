"""Phòng thí nghiệm chọn content (`core/phong_thi_nghiem`, đợt 1 — 12/10/2026).

Số giả hoàn toàn trong tmp_path (mã video giả 11 ký tự, tên kênh giả) — không mạng, không AI, không đụng cây thật.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import random

import pytest

from core import thuoc_thang as tt
from core.phong_thi_nghiem import _chung as c
from core.phong_thi_nghiem import chay, dac_trung, danh_gia, gia_thuyet, nguon, nhat_ky, vu_tru

NGAY = "2026-10-10"
MOC = c.moc_cuoi_ngay(NGAY)
LUC_QUET = c.epoch_luc("2026-10-10 05:00")


def _ngay_truoc(n):
    return c.cong_ngay(NGAY, -n)


def _dong_sach(ma, kenh, *, tuoi, view, dai="15:00", tang="", td=None, tuyen=""):
    return {"Kênh": kenh, "Tiêu đề video": td or "tiêu đề {0}".format(ma), "Tiêu đề (Việt)": "",
            "Link video": "https://www.youtube.com/watch?v=" + ma, "Ngày đăng": _ngay_truoc(tuoi),
            "Thời lượng": dai, "View": str(view), "Tăng/ngày": str(tang), "View lần trước": "",
            "Tuyến / Kênh": tuyen, "Mô tả": "", "Đã làm": ""}


def _dong_ba(kenh, *, tt_="theo dõi", tv="1000", ghi="✓ AI kiểm ngách 11/10: đúng ngách", ai="có"):
    return {"Kênh": kenh, "Trạng thái": tt_, "AI": ai, "Subs": "50000", "View TV": tv, "Quét lúc": "2026-10-10 05:00",
            "Ghi chú": ghi, "Link kênh": "https://www.youtube.com/@" + kenh}


def _tc(luc, ma, kenh, *, view="7000", dang=None, dai="14:00", short="", bi_loai=""):
    return {"Lúc quét": luc, "Mã video": ma, "Tiêu đề": "trang chủ " + ma, "Kênh": kenh, "Lượt xem": view,
            "Đăng": dang or _ngay_truoc(3), "Dài": dai, "Short": short, "Bị loại": bi_loai}


def _the_gioi(**kw):
    sach = [
        _dong_sach("vidLabA0001", "kenh-a", tuoi=5, view=20000, tang=3000, td="賢い仮名人物が静かに暮らす理由"),
        _dong_sach("vidLabA0002", "kenh-a", tuoi=60, view=1500),                      # cũ, thường → bỏ
        _dong_sach("vidLabA0003", "kenh-a", tuoi=90, view=50000),                     # cũ nhưng gấp 50× → giữ
        _dong_sach("vidLabA0004", "kenh-a", tuoi=4, view=9000),                       # nhóm đã làm 08/10 → bỏ
        _dong_sach("vidLabA0005", "kenh-a", tuoi=4, view=9000),                       # làm 12/10 (sau mốc) → giữ
        _dong_sach("vidLabA0006", "kenh-a", tuoi=4, view=9000, dai="2:30"),           # ngắn → bỏ
        _dong_sach("vidMinh0001", "kenh-a", tuoi=4, view=9000),                       # video của ta → bỏ
        _dong_sach("vidLabN0001", "kenh-nho", tuoi=3, view=600),
        _dong_sach("vidLabL0001", "kenh-lac", tuoi=3, view=9000),
        _dong_sach("vidLabK0001", "kenh-lac2", tuoi=3, view=9000),
        _dong_sach("vidLabH0001", "kenh-het", tuoi=3, view=9000),
        _dong_sach("vidLabI0001", "kenh-im", tuoi=60, view=9000),
        _dong_sach("vidLabS0001", "kenh-an", tuoi=3, view=9000),
        _dong_sach("vidLabB0001", "kenh-b", tuoi=6, view=9000, dai="13:00", td="お金の仮名テスト話"),
        _dong_sach("vidLabX0001", "kenh-ngoai", tuoi=3, view=9000),
    ]
    ba = [_dong_ba("kenh-a"), _dong_ba("kenh-b", tv="900"), _dong_ba("kenh-nho", tv="60"),
          _dong_ba("kenh-lac", ghi="AI kiểm ngách 30/09: lạc ngách ‖ trước: theo dõi"),
          _dong_ba("kenh-lac2", ghi=""), _dong_ba("kenh-het", tt_="hết"), _dong_ba("kenh-im", tv="800"),
          _dong_ba("kenh-an", tv="700")]
    tc = [_tc("2026-10-09 10:00", "vidLabA0001", "kenh-a"), _tc("2026-10-08 10:00", "vidLabB0001", "kenh-b"),
          _tc("2026-10-05 10:00", "vidLabA0003", "kenh-a"),
          _tc("2026-10-09 11:00", "vidLabT0001", "kenh-a", dang=_ngay_truoc(3)),
          _tc("2026-10-09 11:00", "vidLabU0001", "kenh-la"),
          _tc("2026-10-11 09:00", "vidLabF0001", "kenh-a"),                           # sau mốc → không thấy
          _tc("2026-10-09 12:00", "vidLabZ0001", "kenh-a", short="x"),
          _tc("2026-10-09 12:00", "vidLabN0002", "kenh-nho"), _tc("2026-10-01 12:00", "vidLabI0002", "kenh-im")]
    pool = [{"ma": "vidLabB0001", "tieu_de": "お金の仮名テスト話", "hien_thi": 500.0, "bam": 6.0, "xem": 40.0,
             "avd": 300.0, "bam_tb": 4.0, "avd_tb": 250.0, "video_minh": "vidMinh0001", "thang": True},
            {"ma": "vidLabP0001", "tieu_de": "賢い仮名の特徴", "hien_thi": 300.0, "bam": 5.0, "xem": 20.0, "avd": 200.0,
             "bam_tb": 4.0, "avd_tb": 250.0, "video_minh": "vidMinh0001", "thang": True}]
    vm = [{"ma": "vidMinh0001", "tieu_de": "賢い仮名人物の休日の過ごし方", "nhan": "thang", "nong": False,
           "nguon_td": "賢い仮名人物が好む場所"},
          {"ma": "vidMinh0002", "tieu_de": "仮名テスト部屋の話", "nhan": "truot", "nong": False, "nguon_td": ""}]

    def cum(td):
        return ["tri-tue"] if "賢い" in td else (["vat-chat"] if "お金" in td else [])

    tg = nguon.TheGioi(
        kenh="KA", ngay=NGAY, moc=MOC, che_do="nguoc", sach=sach, danh_ba=ba,
        kenh_ai={"https://www.youtube.com/@kenh-lac2": "bo"}, trang_chu=tc, pool=pool, video_minh=vm,
        ma_cua_nhom={"vidMinh0001", "vidMinh0002"}, da_lam={"vidLabA0004": "2026-10-08", "vidLabA0005": "2026-10-12"},
        anh_em=["KA", "KB"], v7={"vidLabA0001": {"diem": 50.0, "hang": 1}, "vidLabB0001": {"diem": 40.0, "hang": 2}},
        cum_cua=cum, nhan_y=lambda td: "", vung_ai={},
        ban_do_vung={"vung": {"tri-tue": {"chu": "KB"}, "vat-chat": {"chu": "KA"}}},
        thi_truong={"tri-tue": {"dich": 5e6, "ta": 0.0, "thi_phan": 0.1, "tang": 0.3},
                    "vat-chat": {"dich": 2e6, "ta": 10.0, "thi_phan": 0.2, "tang": -0.1}},
        lich_su_view={"vidLabA0001": [(LUC_QUET - 3 * c.NGAY_GIAY, 14000.0)]})
    for k, v in kw.items():
        setattr(tg, k, v)
    return tg


# ── vũ trụ + luật đối thủ thật ──────────────────────────────────────────────

def test_vu_tru_loc_doi_thu_that_va_ghi_ly_do():
    vt = vu_tru.dung(_the_gioi())
    k = vt.kenh
    assert k["kenh-a"]["ok"] and k["kenh-b"]["ok"]
    assert k["kenh-nho"]["ly_do"].startswith("kênh quá nhỏ")
    assert k["kenh-lac"]["ly_do"] == "AI: lạc ngách" and k["kenh-lac2"]["ly_do"] == "AI: lạc ngách"
    assert k["kenh-het"]["ly_do"].startswith("sổ: kênh hết")
    assert k["kenh-im"]["ly_do"].startswith("không đăng video dài")
    assert k["kenh-an"]["ly_do"].startswith("chưa có bằng chứng khán giả")
    ma = {u["ma"]: u for u in vt.ung_vien}
    assert set(ma) == {"vidLabA0001", "vidLabA0003", "vidLabA0005", "vidLabB0001", "vidLabP0001", "vidLabT0001"}
    assert ma["vidLabA0001"]["nguon"] == {"doi_thu", "trang_chu"}
    assert ma["vidLabB0001"]["nguon"] == {"doi_thu", "pool", "trang_chu"}
    assert ma["vidLabP0001"]["nguon"] == {"pool"} and ma["vidLabP0001"]["kenh_ro"] == 0
    assert ma["vidLabT0001"]["nguon"] == {"trang_chu"} and ma["vidLabT0001"]["view"] == 7000
    bo = vt.thong_ke["video_bo"]
    for ly in ("nhóm đã làm", "video ngắn < 4 phút", "video của ta", "kênh ngoài sổ đối thủ",
               "trang chủ: kênh ngoài sổ đối thủ", "cũ > 30 ngày, không đột biến"):
        assert bo.get(ly) == 1, ly
    assert vt.thong_ke["kenh_dat"] == 2 and vt.thong_ke["n_vu_tru"] == 6


def test_kho_dac_trung_mot_dong():
    tg = _the_gioi()
    kho = {d["ma"]: d for d in dac_trung.dung_kho(tg, vu_tru.dung(tg))}
    a = kho["vidLabA0001"]
    assert a["vuot"] == pytest.approx(20.0) and a["dai_tot"] == 1.0 and a["tang_duong"] == 1.0
    assert a["v7_diem"] == 50.0 and a["v7_hang"] == 1
    assert a["cum"] == "tri-tue" and a["vung"] == "tri-tue" and a["vung_chu"] == "KB"
    assert a["vung_cua_anh_em"] == 1.0 and a["vung_cua_minh"] == 0.0 and a["vung_thi_truong"] == 5e6
    assert a["thang_cum"] == 1.0 and a["co_thang"] == 1.0 and a["giong_thang_chu"] > 0.2
    assert a["tc_ngay"] == 1.0 and a["trong_pool"] == 0.0 and a["pool_cum_xem"] == 20.0
    assert a["da_tang_3n"] == pytest.approx(2.0, rel=1e-3)        # (20.000 − 14.000) / 3 ngày / trung vị 1.000
    b = kho["vidLabB0001"]
    assert b["trong_pool"] == 1.0 and b["pool_xem"] == 40.0 and b["pool_thang_xem"] == 40.0
    assert b["pool_diem"] == pytest.approx((30 + 10) / (20 + 10) * (48 + 10) / (40 + 10), rel=1e-3)
    assert b["vung_cua_minh"] == 1.0 and b["vuot"] == pytest.approx(10.0)
    assert kho["vidLabP0001"]["kenh_ro"] == 0.0 and kho["vidLabP0001"]["vuot"] is None
    assert all(d["vph_nguon"] in ("xap_xi", "") for d in kho.values())


def test_anh_chup_kho_doc_lai_giu_thu_hang(tmp_path):
    tg = _the_gioi()
    kho = dac_trung.dung_kho(tg, vu_tru.dung(tg))
    reg, k = gia_thuyet.nap(str(tmp_path))
    chay.danh_dau_du(kho, reg)
    dac_trung.ghi_kho(str(tmp_path), "KA", NGAY, kho)
    lai = dac_trung.doc_kho(str(tmp_path), "KA", NGAY)
    assert dac_trung.ngay_co_kho(str(tmp_path), "KA") == [NGAY]
    for g in reg:
        assert ([d["ma"] for d, _x in gia_thuyet.xep_hang(g, kho, k)[0]]
                == [d["ma"] for d, _x in gia_thuyet.xep_hang(g, lai, k)[0]]), g["id"]


# ── sổ giả thuyết + bộ chấm ─────────────────────────────────────────────────

def test_so_gia_thuyet_hat_giong_giu_muc_sua_tay(tmp_path):
    goc = str(tmp_path)
    reg, k = gia_thuyet.nap(goc)
    ids = [g["id"] for g in reg]
    assert ids[:7] == ["H-V7", "H-VPH", "H-POOL", "H-DOT-BIEN", "H-NHAN-BAN", "H-KHOANG-TRONG", "H-AI"] and k == 10
    p = gia_thuyet.duong(goc)
    du = c.doc_json(p)
    for g in du["gia_thuyet"]:
        if g["id"] == "H-DOT-BIEN":
            g["tham_so"]["cong"][0]["v"] = 25
            g["phien_ban"] = 2
    du["gia_thuyet"] = [g for g in du["gia_thuyet"] if g["id"] != "H-AI"]
    du["gia_thuyet"].append({"id": "H-MOI", "loai": "trong_so", "trang_thai": "bong", "tao_boi": "nao",
                             "tham_so": {"trong_so": {"log_vuot": 1}}})
    du["gia_thuyet"].append({"id": "H-HONG", "loai": "la", "tham_so": {}})
    c.ghi_json(p, du)
    reg2, _k = gia_thuyet.nap(goc)
    m = {g["id"]: g for g in reg2}
    assert m["H-DOT-BIEN"]["tham_so"]["cong"][0]["v"] == 25 and m["H-DOT-BIEN"]["phien_ban"] == 2
    assert "H-AI" in m and "H-MOI" in m and "H-HONG" not in m
    assert any(g["id"] == "H-HONG" for g in c.doc_json(p)["gia_thuyet"])     # mục hỏng KHÔNG bị xoá khỏi sổ


def test_bo_cham_cong_hoac_tran_va_hoa():
    rows = [dac_trung.mo_rong(d) for d in (
        {"ma": "vidLabR0001", "vuot": 100.0, "view": 1, "dai_phut": 15, "tang_ngay": 5},
        {"ma": "vidLabR0002", "vuot": 60.0, "view": 2, "dai_phut": 15, "tang_ngay": 5},   # cùng điểm (trần) → hoà
        {"ma": "vidLabR0003", "vuot": 9.0, "view": 3, "dai_phut": 25, "tang_ngay": 5},
        {"ma": "vidLabR0004", "vuot": None, "view": 4, "dai_phut": 15},
    )]
    gt = {"id": "H-T", "loai": "trong_so", "tham_so": {
        "cong": [{"op": "hoac", "v": [{"f": "dai_tot", "op": "co"}, {"f": "vuot", "op": "<", "v": 10}]},
                 {"f": "vuot", "op": ">=", "v": 8}, {"f": "kenh_ro", "op": "khong"}],
        "trong_so": {"log_vuot": 1.0, "tang_duong": 0.5}, "tran": {"log_vuot": 3.912}}}
    top, n = gia_thuyet.xep_hang(gt, rows, 10)
    assert n == 3 and [d["ma"] for d, _x in top] == ["vidLabR0001", "vidLabR0002", "vidLabR0003"]
    assert top[0][1] == top[1][1] == pytest.approx(3.912 + 0.5)
    ds = {"id": "H-S", "loai": "dung_san", "tham_so": {"cot": "v", "phu": "-h"}}
    r2 = [{"ma": "vidLabQ0001", "v": 5, "h": 3}, {"ma": "vidLabQ0002", "v": 5, "h": 1}, {"ma": "vidLabQ0003"}]
    top, n = gia_thuyet.xep_hang(ds, r2, 10)
    assert n == 2 and [d["ma"] for d, _x in top] == ["vidLabQ0002", "vidLabQ0001"]
    llm = {"id": "H-L", "loai": "llm", "tham_so": {}}
    top, n = gia_thuyet.xep_hang(llm, r2, 1, ket_ai={"vidLabQ0003": 80, "vidLabQ0001": 20})
    assert n == 2 and top[0][0]["ma"] == "vidLabQ0003"


def test_hat_giong_cham_duoc_tren_kho_gia():
    tg = _the_gioi()
    kho = dac_trung.dung_kho(tg, vu_tru.dung(tg))
    hg = {g["id"]: g for g in gia_thuyet.HAT_GIONG}
    top = {i: [d["ma"] for d, _x in gia_thuyet.xep_hang(g, kho, 10)[0]] for i, g in hg.items()}
    assert top["H-V7"] == ["vidLabA0001", "vidLabB0001"]
    # gấp ≥ 8 và dài 12–21: A0003 (50×) > A0001 (20× + còn tăng) > B0001 (10×) > A0005 (9×); T0001 7× không đạt
    assert top["H-DOT-BIEN"] == ["vidLabA0003", "vidLabA0001", "vidLabB0001", "vidLabA0005"]
    assert "vidLabA0001" in top["H-NHAN-BAN"]                                   # cùng cụm + giống tiêu đề video thắng
    assert "vidLabA0001" not in top["H-KHOANG-TRONG"]                           # vùng của kênh anh em
    assert top["H-AI"] == []


# ── nhật ký bóng ────────────────────────────────────────────────────────────

def test_nhat_ky_chi_noi_khong_ghi_trung(tmp_path):
    goc = str(tmp_path)
    gt = {"id": "H-T", "phien_ban": 1}
    d1 = nhat_ky.dong(NGAY, "KA", gt, [({"ma": "vidLabA0001", "view": 1.0, "view_tv": 2.0, "luc": 3.0}, 1.5)],
                      n_du=1, n_vu_tru=9, k=10, che_do="nguoc")
    assert nhat_ky.ghi(goc, [d1]) == 1
    assert nhat_ky.ghi(goc, [dict(d1, top=[])]) == 0                          # cùng khoá → không ghi lại
    assert nhat_ky.ghi(goc, [dict(d1, pb=2)]) == 1                              # phiên bản mới → dòng mới
    assert nhat_ky.da_co(goc, "KA", NGAY) == {("H-T", 1), ("H-T", 2)}
    ds = nhat_ky.doc(goc, tu=NGAY, den=NGAY, kenh=["KA"])
    assert len(ds) == 2 and ds[0]["top"][0]["ma"] == "vidLabA0001" and ds[0]["che_do"] == "nguoc"
    assert nhat_ky.doc(goc, tu=c.cong_ngay(NGAY, 1)) == []
    assert nhat_ky.moi_nhat(goc, "KA", "H-T", den=NGAY)["pb"] == 2
    assert nhat_ky.moi_nhat(goc, "KA", "H-T", den=c.cong_ngay(NGAY, 9)) is None


# ── tầng 1 ──────────────────────────────────────────────────────────────────

def test_tang_thi_truong_ti_le_nen_va_nang(tmp_path):
    goc = str(tmp_path)
    d0 = "2026-10-01"
    t0 = c.epoch_luc(d0 + " 06:00")

    def kho(views, t):
        return [dac_trung.mo_rong({"ma": m, "view": v, "luc": t, "view_tv": 100.0}) for m, v in views.items()]
    dac_trung.ghi_kho(goc, "KA", d0, kho({"vidLabT0001": 1000, "vidLabT0002": 1000, "vidLabT0003": 1000,
                                          "vidLabT0004": 1000}, t0))
    dac_trung.ghi_kho(goc, "KA", "2026-10-04", kho({"vidLabT0001": 1300, "vidLabT0002": 1050, "vidLabT0003": 1000,
                                                    "vidLabT0004": 1500}, t0 + 3 * c.NGAY_GIAY))
    dac_trung.ghi_kho(goc, "KB", "2026-10-08", kho({"vidLabT0001": 2000, "vidLabT0002": 1100}, t0 + 7 * c.NGAY_GIAY))
    log = {"ngay": d0, "kenh": "KA", "gt": "H-T", "pb": 1,
           "top": [{"ma": "vidLabT0001", "v": 1000, "t": t0, "tv": 100}, {"ma": "vidLabT0002", "v": 1000, "t": t0, "tv": 100}]}
    log_b = dict(log, kenh="KB")                                                 # cùng video ở kênh khác: gộp bỏ trùng
    r = danh_gia.tang_thi_truong(goc, [log, log_b], ["KA", "KB"])
    a = r["theo_kenh"]["KA"]["H-T"]
    assert a["3n"]["n"] == 2 and a["3n"]["hit"] == 1 and a["3n"]["ti_le"] == 0.5
    assert a["3n"]["nen"] == 0.5 and a["3n"]["nang"] == 0.0                     # nền: T1, T4 lên / 4 video
    assert a["7n"]["n"] == 2 and a["7n"]["hit"] == 2
    assert r["chung"]["H-T"]["3n"]["n"] == 2                                     # KB không có ảnh nền ngày đó → bỏ
    lo, hi = a["3n"]["ci90"]
    assert 0 < lo < 0.5 < hi < 1


# ── tầng 2 + hậu nghiệm ─────────────────────────────────────────────────────

def _san_xuat():
    return {"KA": [{"ma_goi": "KA-0001", "ma": "vidLabS0001", "ngay": "2026-10-05", "nhan": "thang", "diem": 1.0},
                   {"ma_goi": "KA-0002", "ma": "vidLabS0002", "ngay": "2026-10-06", "nhan": "truot", "diem": 0.0},
                   {"ma_goi": "KA-0003", "ma": "vidLabS0003", "ngay": "2026-10-07", "nhan": "chua_du", "diem": None}],
            "KB": [{"ma_goi": "KB-0001", "ma": "vidLabS0004", "ngay": "2026-10-05", "nhan": "trung_binh", "diem": 0.5}]}


def _logs():
    def L(k, gt, ngay, *ma):
        return {"kenh": k, "gt": gt, "pb": 1, "ngay": ngay, "top": [{"ma": m} for m in ma]}
    return [L("KA", "H-A", "2026-10-04", "vidLabS0001"), L("KA", "H-A", "2026-10-05", "vidLabS0002", "vidLabS0001"),
            L("KA", "H-A", "2026-10-06", "vidLabS0003"), L("KA", "H-B", "2026-10-04", "vidLabS0009"),
            L("KA", "H-B", "2026-10-05", "vidLabS0002"), L("KB", "H-A", "2026-10-04", "vidLabS0004"),
            dict(L("KA", "H-A", "2026-10-04", "vidLabS0002"), pb=9)]                  # phiên bản cũ → bỏ qua


def test_tang_cau_noi_ghi_cong_dung_nhat_ky_hom_truoc():
    r = danh_gia.tang_cau_noi(_san_xuat(), _logs(), {"H-A": 1, "H-B": 1})
    a, b = r["theo_kenh"]["KA"]["H-A"], r["theo_kenh"]["KA"]["H-B"]
    assert (a["n"], a["diem"], a["cho"], a["n_ngoai"]) == (2, 1.0, 1, 0)
    assert [v["nhat_ky"] for v in a["video"]] == ["2026-10-04", "2026-10-05"]   # S1 ghi theo nhật ký 04/10, không 05/10
    assert (b["n"], b["diem"], b["n_ngoai"], b["diem_ngoai"]) == (1, 0.0, 1, 1.0)
    assert r["theo_kenh"]["KB"]["H-A"]["n"] == 1 and "H-B" not in r["theo_kenh"]["KB"]
    assert r["nen_kenh"]["KA"] == {"n": 2, "diem": 1.0, "cho": 1}


def test_hau_nghiem_phan_tang_va_p_tot_nhat_tat_dinh():
    cn = danh_gia.tang_cau_noi(_san_xuat(), _logs(), {"H-A": 1, "H-B": 1})
    hn = danh_gia.hau_nghiem(cn, ["H-A", "H-B"], ["KA", "KB", "KC"])
    assert hn["g"] == 0.5
    assert hn["chung"]["H-A"]["tb"] == 0.5 and hn["chung"]["H-B"]["tb"] == pytest.approx(1 / 3, abs=1e-3)
    ka = hn["theo_kenh"]["KA"]
    assert (ka["H-A"]["a"], ka["H-A"]["b"]) == (3.0, 3.0)
    assert ka["H-B"]["tb"] == pytest.approx((4 / 3) / 5, abs=1e-3)
    assert ka["H-A"]["p_tot_nhat"] > ka["H-B"]["p_tot_nhat"]
    assert ka["H-A"]["p_tot_nhat"] + ka["H-B"]["p_tot_nhat"] == pytest.approx(1.0, abs=1e-3)
    kc = hn["theo_kenh"]["KC"]                                                    # kênh chưa có số → co về mức chung
    assert kc["H-A"]["tb"] == pytest.approx(hn["chung"]["H-A"]["tb"], abs=1e-3) and kc["H-A"]["n"] == 0
    assert kc["H-A"]["luat"] == "chưa chạy bóng" and kc["H-A"]["p_tot_nhat"] is None
    assert hn["theo_kenh"]["KB"]["H-A"]["p_tot_nhat"] == 1.0 and hn["theo_kenh"]["KB"]["H-B"]["p_tot_nhat"] is None
    assert ka["H-A"]["luat"].startswith("chưa đủ n")
    hn2 = danh_gia.hau_nghiem(cn, ["H-A", "H-B"], ["KA", "KB", "KC"])
    assert hn2["theo_kenh"]["KA"]["H-A"]["p_tot_nhat"] == ka["H-A"]["p_tot_nhat"]


def test_beta_va_khoang_tin():
    assert danh_gia.betainc(2, 3, 0.4) == pytest.approx(0.5248, abs=1e-4)
    assert danh_gia.beta_ppf(0.05, 1, 1) == pytest.approx(0.05, abs=1e-6)
    assert danh_gia.beta_ppf(0.5, 2, 2) == pytest.approx(0.5, abs=1e-6)
    lo, hi = danh_gia.ci90(11, 31)
    assert lo < 10 / 40 < hi and hi - lo < 0.25


def test_chon_gia_thuyet_cho_khe_thompson_kham_pha_bo_loai():
    bang = {"gia_thuyet": {"H-A": {"trang_thai": "song"}, "H-B": {"trang_thai": "bong"}, "H-C": {"trang_thai": "loai"}},
            "nhat_ky_gan": {"KA": ["H-A", "H-B", "H-C"]},
            "tang2": {"theo_kenh": {"KA": {"H-A": {"a": 30, "b": 5, "p_tot_nhat": 0.95},
                                           "H-B": {"a": 2, "b": 10, "p_tot_nhat": 0.05},
                                           "H-C": {"a": 50, "b": 1, "p_tot_nhat": 0.0}}}, "chung": {}}}
    r = danh_gia.chon_gia_thuyet_cho_khe("", "KA", bang=bang, rng=random.Random(1), kham_pha=0.0)
    assert r["gia_thuyet"] == "H-A" and r["cach"] == "thompson" and r["dan_dau"] == "H-A" and "H-C" not in r["rut"]
    r = danh_gia.chon_gia_thuyet_cho_khe("", "KA", bang=bang, rng=random.Random(1), kham_pha=1.0)
    assert r["gia_thuyet"] == "H-B" and r["cach"] == "kham_pha"
    assert danh_gia.chon_gia_thuyet_cho_khe("", "KZ", bang=bang)["cach"] == "khong_co"
    chi_a = dict(bang, nhat_ky_gan={"KA": ["H-A"]})                               # H-B không có ứng viên gần đây
    r = danh_gia.chon_gia_thuyet_cho_khe("", "KA", bang=chi_a, rng=random.Random(1), kham_pha=1.0)
    assert r["gia_thuyet"] == "H-A" and list(r["rut"]) == ["H-A"]
    assert danh_gia.posterior("", "KA", bang=bang)["H-A"] == (30.0, 5.0)


# ── không rò thông tin tương lai ────────────────────────────────────────────

def test_pool_va_nhan_thang_cat_dung_moc():
    b1 = {"dong": [{"ma": "vidLabP0001", "hien_thi": 10, "bam": 5, "xem": 3, "avd": 100}], "bam": 4, "avd": 100,
          "hien_thi": 10, "xem": 3}
    b2 = {"dong": [{"ma": "vidLabP0002", "hien_thi": 50, "bam": 5, "xem": 9, "avd": 100},
                   {"ma": "vidMinh0002", "hien_thi": 5, "bam": 5, "xem": 1, "avd": 100}], "bam": 4, "avd": 100,
          "hien_thi": 50, "xem": 9}
    bang = [("vidMinh0001", 100.0, b1), ("vidMinh0001", 200.0, b2)]
    assert [p["ma"] for p in nguon.pool_tai_moc(bang, 150.0, set(), set())] == ["vidLabP0001"]
    assert [p["ma"] for p in nguon.pool_tai_moc(bang, 250.0, {"vidMinh0001"}, {"vidMinh0002"})] == ["vidLabP0002"]
    assert nguon.pool_tai_moc(bang, 250.0, {"vidMinh0001"}, set())[0]["thang"] is True
    dang = c.epoch_luc("2026-10-01 00:00")
    ch = tt.Chuoi(ma="vidMinh0001", dang=dang, diem=[
        tt.Diem(tuoi=50, hien_thi=100.0, xem=10.0, luc=dang + 50 * 3600),
        tt.Diem(tuoi=120, hien_thi=30000.0, xem=3000.0, luc=dang + 120 * 3600)])
    vm = {"vidMinh0001": {"ma": "vidMinh0001", "tieu_de": "t", "dang": dang, "chuoi": ch}}
    assert nguon.nhan_tai_moc(vm, dang + 60 * 3600)["vidMinh0001"].nhan == "chua_du"
    assert nguon.nhan_tai_moc(vm, dang + 200 * 3600)["vidMinh0001"].nhan == "thang"
    assert nguon.nhan_tai_moc(vm, dang - 10) == {}                                  # chưa đăng lúc mốc
    rows = [{"Lúc quét": "2026-10-10 23:59"}, {"Lúc quét": "2026-10-11 00:01"}]
    assert len(nguon.loc_trang_chu(rows, NGAY)) == 1


def _ghi_csv(duong, rows):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    cot = list(rows[0].keys()) if rows else ["x"]
    with io.open(duong, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cot)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def test_bang_v7_cu_dung_lai_diem_ban_5(tmp_path):
    goc = str(tmp_path)
    cot = ["Hạng", "Điểm", "Loại", "Cụm", "Bảng đề xuất", "Nổ", "Đang lên", "Khuôn", "Xu hướng", "Dài", "Link", "Lý do"]

    def r(h, diem, no, len_, khuon, dai, ma):
        return dict(zip(cot, [h, diem, "Bỏ", 0, 0, no, len_, khuon, 0, dai, "https://www.youtube.com/watch?v=" + ma, ""]))
    _ghi_csv(os.path.join(goc, "CHANNEL", "KA", "nghien-cuu", "cham-v7-2026-10-05.csv"),
             [r(1, 30, 10, 15, 5, "15:00", "vidLabV0001"), r(2, 25, 20, 0, 5, "35:00", "vidLabV0002")])
    v7, d = nguon.bang_v7_ngay(goc, "KA", "2026-10-06")
    assert d == "2026-10-05"
    assert v7["vidLabV0002"]["hang"] == 1 and v7["vidLabV0002"]["diem"] == pytest.approx(36.0)   # Nổ 20×1,5 + dạng 6
    assert v7["vidLabV0001"]["diem"] == pytest.approx(15 + 9)                                     # Nổ 15 + dài 9
    _ghi_csv(os.path.join(goc, "CHANNEL", "KA", "nghien-cuu", "cham-v7-2026-10-12.csv"),
             [r(1, 40, 30, 0, 15, "15:00", "vidLabV0003")])
    v7, d = nguon.bang_v7_ngay(goc, "KA", "2026-10-12")
    assert d == "2026-10-12" and v7["vidLabV0003"]["diem"] == 40.0
    assert nguon.bang_v7_ngay(goc, "KA", "2026-10-20") == ({}, "")


# ── trên đĩa: chạy ngược + hằng ngày + cờ ───────────────────────────────────

def _dung_goc(goc):
    for k in ("KA", "KB"):
        p = os.path.join(goc, "CHANNEL", k, "kenh.yaml")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as f:
            f.write("ten: {0}\nnhom: nhom-thu\n".format(k))
    tg = _the_gioi()
    nc = os.path.join(goc, "CHANNEL", "KA", "nghien-cuu")
    sach = [dict(r) for r in tg.sach]
    _ghi_csv(os.path.join(nc, "content.csv"), sach)
    _ghi_csv(os.path.join(nc, "doi-thu.csv"), tg.danh_ba)
    _ghi_csv(os.path.join(nc, "trang-chu.csv"), tg.trang_chu)
    cu = [dict(r, View=str(int(float(r["View"]) * 0.7))) for r in sach]
    _ghi_csv(os.path.join(nc, "sao-luu", "content-2026-10-09.csv"), cu)
    _ghi_csv(os.path.join(nc, "sao-luu", "doi-thu-2026-10-09.csv"), tg.danh_ba)
    _ghi_csv(os.path.join(nc, "cham-v7-2026-10-08.csv"), [
        {"Hạng": 1, "Điểm": 40, "Loại": "Bỏ", "Cụm": 0, "Bảng đề xuất": 0, "Nổ": 30, "Đang lên": 0, "Khuôn": 10,
         "Xu hướng": 0, "Dài": "15:00", "Link": "https://www.youtube.com/watch?v=vidLabA0001", "Lý do": ""}])
    tc = os.path.join(goc, "CHANNEL", "KA", "tu-chay")
    os.makedirs(tc, exist_ok=True)
    with io.open(os.path.join(tc, "2026-10-09.json"), "w", encoding="utf-8") as f:
        json.dump({"ngay": "2026-10-09", "kenh": "KA", "runs": [
            {"ma_luot": "0001", "nguon": {"nguon": "vph", "cong_thuc": "vph", "ma": "vidLabA0001",
                                          "link": "https://www.youtube.com/watch?v=vidLabA0001", "tieu_de": "x"},
             "ban_giao": {"ma_goi": "KA-0001"}}]}, f)


def test_chay_nguoc_hang_ngay_va_co_tat(tmp_path, monkeypatch):
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")
    goc = str(tmp_path)
    _dung_goc(goc)
    r = chay.chay_nguoc(goc, ["KA"], tu="2026-10-07", den="2026-10-09")
    assert sorted(r["kenh"]["KA"]) == ["2026-10-08", "2026-10-09"]            # từ (sao lưu sớm nhất − 1)
    logs = nhat_ky.doc(goc, kenh=["KA"])
    assert {x["ngay"] for x in logs} == {"2026-10-08", "2026-10-09"} and all(x["che_do"] == "nguoc" for x in logs)
    v7_08 = next(x for x in logs if x["ngay"] == "2026-10-08" and x["gt"] == "H-V7")
    assert [i["ma"] for i in v7_08["top"]] == ["vidLabA0001"]
    a08 = next(i for x in logs if x["ngay"] == "2026-10-08" and x["gt"] == "H-DOT-BIEN" for i in x["top"]
               if i["ma"] == "vidLabA0001")
    assert a08["v"] == 14000                                                        # sổ lúc hết 08/10 = bản sao lưu 09/10
    assert dac_trung.ngay_co_kho(goc, "KA") == ["2026-10-08", "2026-10-09"]
    assert os.path.isfile(r["bao_cao"]) and "Vũ trụ ứng viên" in io.open(r["bao_cao"], encoding="utf-8").read()
    bang = danh_gia.doc_bang(goc)
    assert bang["so_nhat_ky"] == len(logs) and "H-DOT-BIEN" in bang["tang2"]["theo_kenh"]["KA"]
    # chạy ngược lần hai: không ghi lại
    assert sum(chay.chay_nguoc(goc, ["KA"], tu="2026-10-07", den="2026-10-09", bao_cao=False)["kenh"]["KA"].values()) == 0
    # hằng ngày
    bg = c.moc_cuoi_ngay("2026-10-11") + 3600
    t = chay.chay_ngay(goc, "KA", ngay="2026-10-12", danh_gia_lai=False, bay_gio=bg)
    assert t["ghi"] >= 5 and t["n_vu_tru"] > 0
    assert all(x["che_do"] == "that" for x in nhat_ky.doc(goc, tu="2026-10-12"))
    assert chay.chay_ngay(goc, "KA", ngay="2026-10-12", bay_gio=bg)["bo_qua"].startswith("đã ghi")
    # sổ đứng im quá 4 ngày (kênh sản xuất ở máy khác) → không ghi
    assert chay.chay_ngay(goc, "KA", ngay="2026-10-20", bay_gio=c.moc_cuoi_ngay("2026-10-20"),
                          danh_gia_lai=False)["bo_qua"].startswith("sổ đối thủ quét lần cuối")
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "0")
    assert chay.chay_ngay(goc, "KA", ngay="2026-10-13")["bo_qua"].startswith("tắt")
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")
    with io.open(os.path.join(goc, "CHANNEL", "KA", "kenh.yaml"), "a", encoding="utf-8") as f:
        f.write("phong_thi_nghiem: false\n")
    assert not chay.bat(goc, "KA") and chay.bat(goc, "KB")


def test_h_ai_mot_luot_goi_moi_ngay_co_tran(tmp_path):
    from core.phong_thi_nghiem import ai

    goc = str(tmp_path)
    tg = _the_gioi()
    kho = dac_trung.dung_kho(tg, vu_tru.dung(tg))
    gt = next(g for g in gia_thuyet.HAT_GIONG if g["id"] == "H-AI")
    goi_lan = []

    def goi(de_bai, **kw):
        goi_lan.append(kw.get("mo_hinh"))
        assert "ỨNG VIÊN" in de_bai and "賢い仮名人物" in de_bai
        return json.dumps({str(i): 90 - i for i in range(1, 60)})
    ket = ai.chay(goc, "KA", NGAY, kho, gt, {"H-V7": ["vidLabB0001", "vidLabA0001"]}, tg.video_minh, goi=goi)
    assert len(goi_lan) == 1 and goi_lan[0] == "claude-fable-5"
    assert ket["vidLabB0001"] == 89 and ket["vidLabA0001"] == 88               # thứ tự: top của giả thuyết khác trước
    assert ai.chay(goc, "KA", NGAY, kho, gt, {}, tg.video_minh, goi=goi) == ket and len(goi_lan) == 1  # nhớ trong ngày
    top, n = gia_thuyet.xep_hang(gt, kho, 10, ket_ai=ket)
    assert top[0][0]["ma"] == "vidLabB0001" and n == len(ket)

    hong = []

    def goi_hong(de_bai, **kw):
        hong.append(1)
        raise RuntimeError("mạng giả hỏng")
    for _ in range(4):
        assert ai.chay(goc, "KA", "2026-10-11", kho, gt, {}, tg.video_minh, goi=goi_hong) == {}
    assert len(hong) == 2                                                          # 1 lượt + 1 lần thử lại, rồi thôi


def test_khong_bao_gio_chan_san_xuat(tmp_path, monkeypatch):
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")

    def hong(*_a, **_k):
        raise RuntimeError("hỏng giả")
    monkeypatch.setattr(chay, "chay_ngay", hong)
    ghi = []
    r = chay.chay_ngay_an_toan(str(tmp_path), "KA", log=ghi.append)
    assert "hỏng giả" in r["loi"] and any("phòng thí nghiệm hỏng" in g for g in ghi)
    from core import mot_nut

    ghi2 = []
    mot_nut._phong_thi_nghiem(str(tmp_path), "KA", None, None, ghi2.append)     # không ném
    assert any("phòng thí nghiệm hỏng" in g for g in ghi2)
