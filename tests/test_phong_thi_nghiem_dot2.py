"""Phòng thí nghiệm chọn content — ĐỢT 2 (12/10/2026): tầng 1 công bằng, ghi công chính xác, hậu nghiệm có tiên nghiệm
tầng 1, luật quyết, chia khe Thompson phân tầng (nối `chien_luoc.xep_hang`), sổ lượt, tab trực quan, mục não + lệnh
`gia-thuyet-moi`.

Số giả hoàn toàn trong tmp_path (mã video giả 11 ký tự, kênh giả) — không mạng, không AI, không đụng cây thật.
"""

from __future__ import annotations

import io
import json
import os
import random

import pytest

from core.phong_thi_nghiem import _chung as c
from core.phong_thi_nghiem import chia_khe, dac_trung, danh_gia, gia_thuyet, luat

NGAY = "2026-10-10"


def _kho(goc, kenh, ngay, dong, t):
    ds = [dac_trung.mo_rong(dict({"ma": m, "luc": t, "view_tv": 100.0, "_du": True}, **x)) for m, x in dong.items()]
    dac_trung.ghi_kho(goc, kenh, ngay, ds)


def _yaml(goc, kenh, *dong):
    p = os.path.join(goc, "CHANNEL", kenh, "kenh.yaml")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(("ten: {0}".format(kenh),) + dong) + "\n")


# ── tầng 1 công bằng ────────────────────────────────────────────────────────

def test_tang1_cong_bang_mot_lan_ket_qua_no_va_ba_muc_nen(tmp_path, monkeypatch):
    goc = str(tmp_path)
    t0 = c.epoch_luc(NGAY + " 06:00")
    # A, B: to (gấp 10) và trẻ — đều NỔ; C..F: nhỏ, cũ — không nổ. Chọn A thì "thắng" vũ trụ nhưng KHÔNG hơn cùng tầng.
    _kho(goc, "KA", NGAY, {"vidFairA001": {"view": 1000, "vuot": 10.0, "tuoi_ngay": 2.0},
                           "vidFairB001": {"view": 1000, "vuot": 10.0, "tuoi_ngay": 2.0},
                           "vidFairC001": {"view": 200, "vuot": 2.0, "tuoi_ngay": 20.0},
                           "vidFairD001": {"view": 200, "vuot": 2.0, "tuoi_ngay": 20.0},
                           "vidFairE001": {"view": 200, "vuot": 2.0, "tuoi_ngay": 20.0},
                           "vidFairF001": {"view": 200, "vuot": 2.0, "tuoi_ngay": 20.0}}, t0)
    _kho(goc, "KA", c.cong_ngay(NGAY, 1), {"vidFairA001": {"view": 1100, "vuot": 11.0, "tuoi_ngay": 3.0}},
         t0 + c.NGAY_GIAY)
    _kho(goc, "KA", c.cong_ngay(NGAY, 7), {"vidFairA001": {"view": 1700}, "vidFairB001": {"view": 1600},
                                           "vidFairC001": {"view": 210}, "vidFairD001": {"view": 200},
                                           "vidFairE001": {"view": 250}, "vidFairF001": {"view": 200}},
         t0 + 7 * c.NGAY_GIAY)
    reg = [{"id": "H-T", "phien_ban": 1, "loai": "trong_so", "trang_thai": "bong",
            "tham_so": {"cong": [{"f": "vuot", "op": ">=", "v": 5}], "trong_so": {"log_vuot": 1}}}]

    def L(ngay, *ma):
        return {"kenh": "KA", "gt": "H-T", "pb": 1, "ngay": ngay,
                "top": [{"ma": m, "v": 1000 if ngay == NGAY else 1100, "tv": 100,
                         "t": t0 if ngay == NGAY else t0 + c.NGAY_GIAY} for m in ma]}
    logs = [L(NGAY, "vidFairA001"), L(c.cong_ngay(NGAY, 1), "vidFairA001")]    # A nằm top 2 ngày → tính MỘT lần
    monkeypatch.setattr(danh_gia, "N_O_TANG", 1)
    r = danh_gia.tang_thi_truong_cong_bang(goc, logs, ["KA"], reg)
    o = r["theo_kenh"]["KA"]["H-T"]
    z = o["7n_no"]
    assert r["cach"] == "lan_dau" and o["n_lap_bo"] == 1 and z["n"] == 1 and z["hit"] == 1
    assert z["nen"] == pytest.approx(2 / 6, abs=1e-3) and z["nang"] == pytest.approx(1 - 2 / 6, abs=1e-3)
    assert z["nen_tang"] == 1.0 and z["nang_tang"] == 0.0         # cùng tầng gấp×tuổi: B cũng nổ → không có kỹ năng
    assert z["nen_cong"] == 1.0 and z["nang_cong"] == 0.0         # tập qua cổng (gấp ≥ 5) = {A, B}
    assert r["chung"]["H-T"]["7n_no"]["n"] == 1
    assert danh_gia.o_tang(10.0, 2.0, 5) == (5, 0, 1) and danh_gia.o_tang(None, None, None) == (-1, -1, -1)
    assert danh_gia.o_tang(0.5, 40.0, 0) == (0, 3, 0)                    # ô gấp × tuổi × đà (còn tăng/ngày)
    p = danh_gia.duong_nen(goc, "KA", NGAY)
    assert os.path.isfile(p)                                        # mẫu nền nhớ lại → lần sau không đọc kho
    monkeypatch.setattr(dac_trung, "doc_kho", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("đọc lại kho")))
    r2 = danh_gia.tang_thi_truong_cong_bang(goc, logs[:1], ["KA"], reg)
    assert r2["theo_kenh"]["KA"]["H-T"]["7n_no"]["hit"] == 1


def test_tien_nghiem_tang1_yeu_va_hau_nghiem_co_dich():
    t1 = {"chung": {"H-A": {"7n_no": {"n": 40, "nang_tang": 0.10, "nang": 0.4}},
                    "H-B": {"7n_no": {"n": 10, "nang_tang": 0.30}}}}
    tn = danh_gia.tien_nghiem_tang1(t1, 0.4, ["H-A", "H-B", "H-C"])
    import math
    assert tn["H-A"] == (pytest.approx(0.4 + 0.15 * math.tanh(1.0), abs=1e-4), danh_gia.KAPPA_TANG1)
    assert tn["H-B"] == (0.4, 0.0) and tn["H-C"] == (0.4, 0.0)      # n < 30 / không có số → không ảnh hưởng
    cn = {"nen_kenh": {"KA": {"n": 3, "diem": 1.0}}, "theo_kenh": {"KA": {"H-A": {"n": 2, "diem": 1.0}}}}
    g = (1.0 + 1) / (3 + 2)
    hn0 = danh_gia.hau_nghiem(cn, ["H-A"], ["KA"])
    hn1 = danh_gia.hau_nghiem(cn, ["H-A"], ["KA"], tien_nghiem={"H-A": (0.9, 1.0)})
    assert hn0["chung"]["H-A"]["a"] == pytest.approx(2 * g + 1.0, abs=1e-3)
    assert hn1["chung"]["H-A"]["a"] - hn0["chung"]["H-A"]["a"] == pytest.approx(0.9, abs=1e-3)
    assert hn1["chung"]["H-A"]["b"] - hn0["chung"]["H-A"]["b"] == pytest.approx(0.1, abs=1e-3)
    assert hn1["theo_kenh"]["KA"]["H-A"]["tb"] > hn0["theo_kenh"]["KA"]["H-A"]["tb"]


def test_p_tot_nhat_hai_bac_tat_dinh_va_ton_trong_du_lieu():
    muc = {"H-A": (8.0, 2.0), "H-B": (2.0, 8.0)}
    p = danh_gia.p_tot_nhat_hai_bac(muc, {"H-A": (3.0, 4.0), "H-B": (0.0, 4.0)}, "kenh:KA", n=2000)
    assert p["H-A"] > 0.9 and p == danh_gia.p_tot_nhat_hai_bac(muc, {"H-A": (3.0, 4.0), "H-B": (0.0, 4.0)},
                                                                "kenh:KA", n=2000)
    assert danh_gia.p_tot_nhat_hai_bac(muc, {"H-A": (0.0, 0.0)}, "x") == {"H-A": 1.0}


# ── tầng 2: ghi công chính xác ──────────────────────────────────────────────

def test_ghi_cong_chinh_xac_cua_khe_khong_dem_trung():
    sx = {"KA": [{"ma_goi": "KA-0001", "ma": "vidExact001", "ngay": "2026-10-05", "nhan": "thang", "diem": 1.0,
                  "gia_thuyet": "H-B", "ptn_pb": 1},
                 {"ma_goi": "KA-0002", "ma": "vidExact002", "ngay": "2026-10-06", "nhan": "truot", "diem": 0.0,
                  "gia_thuyet": "H-A", "ptn_pb": 1},
                 {"ma_goi": "KA-0003", "ma": "vidExact003", "ngay": "2026-10-06", "nhan": "thang", "diem": 1.0,
                  "gia_thuyet": "H-B", "ptn_pb": 7}]}                           # phiên bản cũ → không ghi công
    logs = [{"kenh": "KA", "gt": "H-A", "pb": 1, "ngay": "2026-10-04", "top": [{"ma": "vidExact001"}]},
            {"kenh": "KA", "gt": "H-A", "pb": 1, "ngay": "2026-10-05", "top": [{"ma": "vidExact002"}]}]
    r = danh_gia.tang_cau_noi(sx, logs, {"H-A": 1, "H-B": 1})
    a, b = r["theo_kenh"]["KA"]["H-A"], r["theo_kenh"]["KA"]["H-B"]
    assert (b["n"], b["n_chinh_xac"], b["thang"], b["diem"]) == (1, 1, 1, 1.0)   # H-B không có nhật ký mà vẫn được
    assert (a["n"], a["n_chinh_xac"], a["thang"]) == (2, 1, 1)                    # S2 vừa bóng vừa khe → đếm 1 lần
    assert a["n_ngoai"] == 1                                                       # S3 ngoài top của H-A


# ── luật quyết ──────────────────────────────────────────────────────────────

def _so_gt(goc, *muc):
    du = {"phien_ban": 1, "k": 10, "gia_thuyet": [dict({"phien_ban": 1, "loai": "trong_so", "mo_ta": "giả thuyết giả",
                                                         "tham_so": {"trong_so": {"log_vuot": 1}}}, **m) for m in muc]}
    c.ghi_json(gia_thuyet.duong(goc), du)


def _bang_luat():
    def o(n, p, diem=None):
        return {"n": n, "diem": diem if diem is not None else n / 2.0, "tb": 0.5, "ci90": [0.3, 0.7], "p_tot_nhat": p,
                "a": 3.0, "b": 3.0, "thang": n // 2}
    return {
        "gia_thuyet": {g: {"trang_thai": tt, "phien_ban": 1} for g, tt in (
            ("H-A", "song"), ("H-B", "song"), ("H-C", "song"), ("H-D", "bong"), ("H-E", "song"), ("H-F", "bong"),
            ("H-G", "bong"))},
        "ngay_bong": {"KA": {"H-F": 9, "H-G": 3, "H-D": 9}},
        "tang1": {"chung": {"H-F": {"7n_no": {"n": 40, "hit": 20, "nen_tang": 0.2}},
                            "H-D": {"7n_no": {"n": 40, "hit": 4, "nen_tang": 0.2}}}},
        "tang2": {"theo_kenh": {"KA": {"H-A": o(9, 0.85), "H-B": o(9, 0.02), "H-C": o(2, 0.01), "H-F": o(0, 0.1),
                                       "H-G": o(0, 0.1), "H-D": o(1, 0.02)},
                                "KB": {"H-A": o(5, 0.60), "H-E": o(9, 0.01)}},
                  "chung": {"H-A": o(14, 0.70), "H-B": o(10, 0.01), "H-C": o(2, 0.001), "H-D": o(8, 0.2),
                            "H-E": o(9, 0.02), "H-F": o(0, 0.05), "H-G": o(0, 0.02)}}}


def test_luat_dan_dau_loai_mo_thu_tot_nghiep_va_khong_hanh_dong_n_nho(tmp_path):
    goc = str(tmp_path)
    _so_gt(goc, *({"id": g, "trang_thai": tt} for g, tt in (("H-A", "song"), ("H-B", "song"), ("H-C", "song"),
                                                            ("H-D", "bong"), ("H-E", "song"), ("H-F", "bong"),
                                                            ("H-G", "bong"))))
    bang = _bang_luat()
    r = luat.ap_dung(goc, bang)
    ka = r["kenh"]["KA"]
    assert ka["H-A"] == "dan_dau" and ka["H-B"] == "loai" and ka["H-C"] == ""     # H-C: n = 2 → không bao giờ
    assert ka["H-F"] == "thu" and ka["H-G"] == "" and ka["H-D"] == ""              # H-D kẹt sàn tầng 1 (10% < 20%)
    assert r["kenh"]["KB"]["H-E"] == ""                      # thua H-A chỉ có n 5 < 8 → chưa đủ bằng chứng để loại
    assert r["chung"] == {"H-B": "loai", "H-D": "song", "H-E": "loai"}   # toàn danh mục: đối thủ H-A đã đo n 14
    so = {g["id"]: g["trang_thai"] for g in c.doc_json(gia_thuyet.duong(goc))["gia_thuyet"]}
    assert so["H-B"] == "loai" and so["H-D"] == "song" and bang["gia_thuyet"]["H-B"]["trang_thai"] == "loai"
    qd = luat.doc_quyet_dinh(goc)
    loai = {(x["loai"], x["kenh"], x["gt"]) for x in qd}
    assert ("dan_dau", "KA", "H-A") in loai and ("loai_kenh", "KA", "H-B") in loai and ("mo_thu", "KA", "H-F") in loai
    assert ("loai_chung", "", "H-B") in loai and ("tot_nghiep", "", "H-D") in loai
    x = next(x for x in qd if x["loai"] == "loai_kenh")
    assert x["n"] == 9 and x["p_tot_nhat"] == 0.02 and x["doi_thu"]["gt"] == "H-A" and "n = 9" in x["ly_do"]
    # quyết định dựa phán quyết thật (dẫn đầu / loại / tốt nghiệp) không bao giờ ở n ≤ 2 ("mở thử" dựa bóng + tầng 1)
    assert all(x["n"] > 2 for x in qd if x["loai"] in ("dan_dau", "loai_kenh", "loai_chung", "tot_nghiep"))
    # lần hai: không có thay đổi vai → không ghi thêm
    bang2 = _bang_luat()
    bang2["gia_thuyet"]["H-B"]["trang_thai"] = "loai"
    bang2["gia_thuyet"]["H-D"]["trang_thai"] = "song"
    bang2["gia_thuyet"]["H-E"]["trang_thai"] = "loai"
    luat.ap_dung(goc, bang2)
    assert len(luat.doc_quyet_dinh(goc)) == len(qd)


def test_luat_loai_chung_can_doi_thu_da_do():
    bang = _bang_luat()
    assert luat.vai_theo_bang(bang["tang2"]["chung"], "H-E")[0] == "loai"           # đối thủ H-A n 14 ≥ 8
    bang["tang2"]["chung"]["H-A"]["n"] = 5
    bang["tang2"]["chung"]["H-D"]["p_tot_nhat"] = 0.05
    assert luat.vai_theo_bang(bang["tang2"]["chung"], "H-E")[0] == ""               # đối thủ dẫn chỉ 5 video


# ── chia khe ────────────────────────────────────────────────────────────────

def _bang_khe():
    def o(n, diem, p, a, b):
        return {"n": n, "diem": diem, "p_tot_nhat": p, "tb": a / (a + b), "a": a, "b": b, "ci90": [0.1, 0.9]}
    return {"ngay": NGAY, "gia_thuyet": {"H-A": {"trang_thai": "song", "phien_ban": 1},
                                         "H-B": {"trang_thai": "song", "phien_ban": 1},
                                         "H-C": {"trang_thai": "bong", "phien_ban": 1},
                                         "H-X": {"trang_thai": "loai", "phien_ban": 1}},
            "ngay_bong": {"KA": {"H-C": 9}},
            "tang1": {"chung": {"H-C": {"7n_no": {"n": 50, "hit": 25, "nen_tang": 0.1}}}},
            "tang2": {"chung": {"H-A": o(20, 15, 0.8, 16, 6), "H-B": o(20, 6, 0.1, 7, 15), "H-C": o(0, 0, 0.1, 1, 1),
                                "H-X": o(20, 20, 0.9, 30, 2)},
                      "theo_kenh": {"KA": {"H-A": o(10, 8, 0.8, 11, 3), "H-B": o(10, 3, 0.05, 4.5, 9.5),
                                           "H-C": o(0, 0, 0.15, 2, 2), "H-X": o(9, 9, 0.9, 12, 1)}}}}


def test_phan_bo_thompson_tat_dinh_san_kham_pha_tran_tuan_va_loai(tmp_path):
    goc, bang = str(tmp_path), _bang_khe()
    du, vai, chan = chia_khe.du_dieu_kien(goc, "KA", bang, ngay=NGAY)
    assert du == ["H-A", "H-B", "H-C"] and vai["H-C"] == "thu" and "H-X" in chan    # loại toàn danh mục → không khe
    k1 = chia_khe.phan_bo(goc, "KA", ngay=NGAY, so_luot=0, bang=bang)
    assert k1 == chia_khe.phan_bo(goc, "KA", ngay=NGAY, so_luot=0, bang=bang)        # tất định (trạm = vòng chọn)
    assert k1["thu_tu"][0] == k1["gia_thuyet"] and sorted(k1["thu_tu"]) == ["H-A", "H-B", "H-C"]
    r = random.Random(7)
    dem = {}
    for _ in range(3000):
        g = chia_khe.phan_bo(goc, "KA", ngay=NGAY, bang=bang, rng=r)["gia_thuyet"]
        dem[g] = dem.get(g, 0) + 1
    khong_dan = (dem.get("H-B", 0) + dem.get("H-C", 0)) / 3000.0
    assert khong_dan >= 0.15 and dem["H-A"] > dem.get("H-B", 0)                      # sàn khám phá ≥ 15%
    r0 = random.Random(7)
    dem0 = {}
    for _ in range(1000):
        g = chia_khe.phan_bo(goc, "KA", ngay=NGAY, bang=bang, rng=r0, kham_pha=1.0)["gia_thuyet"]
        dem0[g] = dem0.get(g, 0) + 1
    assert "H-A" not in dem0                                                            # khám phá = không dẫn đầu
    # trần 1 khe/kênh/tuần cho giả thuyết mới (đếm sổ lượt)
    p = os.path.join(goc, "CHANNEL", "KA", "tu-chay", c.cong_ngay(NGAY, -3) + ".json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    c.ghi_json(p, {"runs": [{"nguon": {"gia_thuyet": "H-C", "ma": "vidSlot0001"}},
                            {"nguon": {"gia_thuyet": "H-A"}, "bo": True}]})
    assert chia_khe.so_khe(goc, "KA", NGAY) == {"H-C": 1}
    du2, _v, chan2 = chia_khe.du_dieu_kien(goc, "KA", bang, ngay=NGAY)
    assert du2 == ["H-A", "H-B"] and "1/1" in chan2["H-C"]
    mp = chia_khe.mo_phong(goc, "KA", ngay=NGAY, bang=bang, so_lan=500)
    assert set(mp["ti_le"]) == {"H-A", "H-B"} and sum(mp["ti_le"].values()) == pytest.approx(1.0, abs=0.01)
    assert chia_khe.phan_bo(goc, "KZ", ngay=NGAY, bang=bang)["cach"] == "khong_co"


def test_co_chia_khe_mac_dinh_yaml_tep_va_bien_moi_truong(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")
    monkeypatch.delenv("MYTOOL_PTN_CHIA_KHE", raising=False)
    for k in ("TL1-T7", "KA", "KB"):
        _yaml(goc, k)
    assert chia_khe.bat(goc, "TL1-T7")[0] and not chia_khe.bat(goc, "KA")[0]          # mặc định trong mã
    c.ghi_json(os.path.join(c.thu_muc_chung(goc), chia_khe.TEP_CAU_HINH), {"kenh": {"KA": True}, "mac_dinh": False})
    assert chia_khe.bat(goc, "KA")[0] and not chia_khe.bat(goc, "TL1-T7")[0]          # tệp cấu hình đè mặc định
    _yaml(goc, "KB", "phong_thi_nghiem_chia_khe: true")
    assert chia_khe.bat(goc, "KB") == (True, "kenh.yaml phong_thi_nghiem_chia_khe")
    monkeypatch.setenv("MYTOOL_PTN_CHIA_KHE", "0")
    assert not chia_khe.bat(goc, "KB")[0]
    monkeypatch.setenv("MYTOOL_PTN_CHIA_KHE", "1")
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "0")
    assert not chia_khe.bat(goc, "KB")[0]                                              # phòng thí nghiệm tắt → tắt


def _dung_kenh_chia_khe(goc, yaml_them=("phong_thi_nghiem_chia_khe: true",)):
    _yaml(goc, "KA", 'chien_luoc: "vph:1"', *yaml_them)
    t = c.epoch_luc(NGAY + " 06:00")
    _kho(goc, "KA", NGAY, {"vidLabX0001": {"view": 9000, "vuot": 90.0, "dai_phut": 15, "kenh_nguon": "kenh-x",
                                           "tieu_de": "ジャンプ仮名一"},
                           "vidLabX0002": {"view": 3000, "vuot": 30.0, "dai_phut": 14, "kenh_nguon": "kenh-x",
                                           "tieu_de": "ジャンプ仮名二"},
                           "vidVphV0001": {"view": 2000, "vuot": 20.0, "dai_phut": 13, "kenh_nguon": "kenh-y",
                                           "tieu_de": "共通仮名話"},
                           "vidLabX0003": {"view": 400, "vuot": 4.0, "dai_phut": 15, "kenh_nguon": "kenh-x",
                                           "tieu_de": "小さい仮名"}}, t)
    _so_gt(goc, {"id": "H-VPH", "loai": "dung_san", "trang_thai": "song", "tham_so": {"cot": "vph_diem"}},
           {"id": "H-X", "trang_thai": "bong", "tham_so": {"cong": [{"f": "vuot", "op": ">=", "v": 8}],
                                                            "trong_so": {"log_vuot": 1}}})

    def o(n, diem, p, a, b):
        return {"n": n, "diem": diem, "p_tot_nhat": p, "tb": a / (a + b), "a": a, "b": b, "ci90": [0.1, 0.9]}
    bang = {"ngay": NGAY, "luc": NGAY + "T05:00:00", "kenh": ["KA"],
            "gia_thuyet": {"H-VPH": {"trang_thai": "song", "phien_ban": 1}, "H-X": {"trang_thai": "bong",
                                                                                     "phien_ban": 1}},
            "ngay_bong": {"KA": {"H-X": 10}}, "tang1": {"chung": {"H-X": {"7n_no": {"n": 40, "hit": 30,
                                                                                    "nen_tang": 0.1}}}},
            "tang2": {"chung": {"H-VPH": o(20, 2, 0.01, 2, 30), "H-X": o(9, 8, 0.99, 40, 2)},
                      "theo_kenh": {"KA": {"H-VPH": o(5, 1, 0.01, 1.5, 12), "H-X": o(9, 8, 0.99, 30, 2)}}}}
    c.ghi_json(danh_gia.duong_bang(goc), bang)


VPH_GIA = [{"nguon": "vph", "ma": "vidVphV0001", "link": "https://youtu.be/vidVphV0001", "tieu_de": "共通仮名話",
            "kenh": "kenh-y", "diem": 80, "loai": "", "ly_do": []},
           {"nguon": "vph", "ma": "vidVphV0002", "link": "https://youtu.be/vidVphV0002", "tieu_de": "別の仮名話",
            "kenh": "kenh-y", "diem": 70, "loai": "", "ly_do": []}]


def _xep(goc, log=None):
    from core import tu_chay
    return tu_chay.ung_vien_xep_hang(goc, "KA", False, set(), cham_vph=lambda _g, _k: [dict(d) for d in VPH_GIA],
                                     doc_danh_sach=lambda _g, _k: {}, log=log or (lambda *_a: None))


def test_chia_khe_trong_bo_dieu_phoi_bang_dau_lui_va_tat(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")
    monkeypatch.delenv("MYTOOL_PTN_CHIA_KHE", raising=False)
    monkeypatch.setattr(chia_khe, "KHAM_PHA", 0.0)
    monkeypatch.setattr(c, "hom_nay", lambda: NGAY)
    import datetime as dt
    from core.chien_luoc import ngu_canh
    goc_dung = ngu_canh.dung
    monkeypatch.setattr(ngu_canh, "dung", lambda *a, **k: goc_dung(*a, **dict(k, bay_gio=dt.datetime(2026, 10, 10, 9))))
    _dung_kenh_chia_khe(goc)
    log = []
    ds = _xep(goc, log.append)
    assert [d["ma"] for d in ds] == ["vidLabX0001", "vidLabX0002", "vidVphV0001", "vidVphV0002"]
    assert [d["gia_thuyet"] for d in ds] == ["H-X", "H-X", "H-X", "H-VPH"]
    assert all(d["gia_thuyet_khe"] == "H-X" and d["ptn"]["pb"] == 1 and d["tham_do"] is False for d in ds)
    assert ds[2]["gia_thuyet_khac"] == ["H-VPH"] and ds[0]["cong_thuc"] == "ptn" and ds[3]["cong_thuc"] == "vph"
    assert ds[0]["tieu_de"] == "ジャンプ仮名一" and ds[0]["link"].endswith("vidLabX0001")
    assert any("phòng thí nghiệm chia khe: lượt này → H-X" in x for x in log)
    # cờ tắt → luật cũ, không gắn khoá phòng thí nghiệm
    _yaml(goc, "KA", 'chien_luoc: "vph:1"', "phong_thi_nghiem_chia_khe: false")
    ds2 = _xep(goc)
    assert [d["ma"] for d in ds2] == ["vidVphV0001", "vidVphV0002"] and not any("gia_thuyet" in d for d in ds2)
    # kênh chưa có số trong bảng → luật cũ
    _yaml(goc, "KA", 'chien_luoc: "vph:1"', "phong_thi_nghiem_chia_khe: true")
    c.ghi_json(danh_gia.duong_bang(goc), {"tang2": {"theo_kenh": {}}})
    assert not any("gia_thuyet" in d for d in _xep(goc))


def test_chot_nguon_va_cua_kho_loi_thoai_giu_dung_gia_thuyet(monkeypatch):
    ng = {"ma": "vidPick0001", "gia_thuyet": "H-X", "gia_thuyet_khe": "H-X", "ptn": {"pb": 2}, "ep_chon": True}
    chia_khe.chot_nguon(ng)
    assert ng["gia_thuyet"] == "" and ng["gia_thuyet_bo"] == "H-X" and ng["ptn"]["khong_ghi_cong"] == "bộ não ép chọn"
    ng2 = {"ma": "vidPick0002", "gia_thuyet": "H-X", "gia_thuyet_khe": "H-X", "ptn": {"pb": 2}}
    chia_khe.chot_nguon(ng2)
    assert ng2["gia_thuyet"] == "H-X" and ng2["ptn_pb"] == 2
    from core import loi_thoai, tu_chay
    co = {"vidPick0005", "vidPick0004"}
    monkeypatch.setattr(loi_thoai, "co_loi_thoai", lambda _g, _k, ma: ma in co)
    ds = [{"ma": "vidPick0003", "gia_thuyet": "H-X", "gia_thuyet_khe": "H-X"},
          {"ma": "vidPick0004", "gia_thuyet": "H-VPH", "gia_thuyet_khe": "H-X"},
          {"ma": "vidPick0005", "gia_thuyet": "H-X", "gia_thuyet_khe": "H-X"}]
    assert tu_chay._uu_tien_co_kho("", "KA", ds, lambda *_a: None)["ma"] == "vidPick0005"
    assert tu_chay._uu_tien_co_kho("", "KA", ds[:2], lambda *_a: None)["ma"] == "vidPick0003"   # không nhảy bảng
    cu = [{"ma": "vidPick0003"}, {"ma": "vidPick0004"}]
    assert tu_chay._uu_tien_co_kho("", "KA", cu, lambda *_a: None)["ma"] == "vidPick0004"       # luật cũ y nguyên


def test_so_luot_mang_gia_thuyet_vao_ho_so(tmp_path):
    from core import ho_so_video
    goc = str(tmp_path)
    _yaml(goc, "KA")
    p = os.path.join(goc, "CHANNEL", "KA", "tu-chay", NGAY + ".json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    c.ghi_json(p, {"runs": [{"ma_luot": "0001", "nguon": {"link": "https://youtu.be/vidBook0001", "ma": "vidBook0001",
                                                          "gia_thuyet": "H-X", "gia_thuyet_khe": "H-X",
                                                          "ptn": {"pb": 3}, "ptn_pb": 3},
                             "ban_giao": {"ma_goi": "KA-0001"}}]})
    g = ho_so_video.nguon_cua_goi(goc, "KA")["KA-0001"]
    assert (g["gia_thuyet"], g["gia_thuyet_khe"], g["ptn_pb"]) == ("H-X", "H-X", 3)


# ── giả thuyết mới của não, mục não, trực quan ──────────────────────────────

def test_nao_de_xuat_gia_thuyet_moi_kiem_va_han_muc(tmp_path):
    from core import nao
    goc = str(tmp_path)
    _yaml(goc, "KA")
    os.makedirs(os.path.join(goc, "CHANNEL", "KA", "nghien-cuu"), exist_ok=True)
    io.open(os.path.join(goc, "CHANNEL", "KA", "nghien-cuu", "content.csv"), "w", encoding="utf-8").write("Kênh\n")
    _kho(goc, "KA", NGAY, {"vidNew00001": {"view": 900, "vuot": 9.0, "dai_phut": 15, "trong_pool": 1.0},
                           "vidNew00002": {"view": 300, "vuot": 3.0, "dai_phut": 15}}, c.epoch_luc(NGAY + " 06:00"))

    def chay(*a):
        return nao.chay_lenh(nao._parser().parse_args(["gia-thuyet-moi"] + list(a)), goc)
    ly = "--ly-do=pool cùng cụm nổ 50% vs 12% rút ngẫu nhiên cùng tầng, n 93"
    out = chay("--id", "H-POOL-GAP", "--mo-ta", "pool khán giả + nguồn gấp ≥ 5", "--trong-so",
               "log_pool_xem:1, log_vuot:0.5", "--cong", "vuot>=5; trong_pool co", "--tran", "log_vuot:3.9", ly)
    assert "ĐÃ GHI giả thuyết H-POOL-GAP" in out and "KA {0}: 1 qua cổng".format(NGAY) in out
    g = next(x for x in c.doc_json(gia_thuyet.duong(goc))["gia_thuyet"] if x["id"] == "H-POOL-GAP")
    assert g["trang_thai"] == "bong" and g["tao_boi"] == "nao" and g["tham_so"]["cong"][1] == {"f": "trong_pool",
                                                                                              "op": "co"}
    assert luat.doc_quyet_dinh(goc)[-1]["loai"] == "de_xuat_moi"
    with pytest.raises(nao.TuChoi, match="đã có"):
        chay("--id", "H-POOL-GAP", "--mo-ta", "trùng id giả thuyết", "--trong-so", "log_vuot:1", ly)
    with pytest.raises(nao.TuChoi, match="không có trong kho"):
        chay("--id", "H-LA", "--mo-ta", "đặc trưng không tồn tại", "--trong-so", "so_la:1", ly)
    with pytest.raises(nao.TuChoi, match="cổng quá chặt"):
        chay("--id", "H-CHET", "--mo-ta", "cổng không ai qua nổi", "--trong-so", "log_vuot:1", "--cong",
             "vuot>=500", ly)
    with pytest.raises(nao.TuChoi, match="lý lẽ"):
        chay("--id", "H-NGAN", "--mo-ta", "lý do quá ngắn ở đây", "--trong-so", "log_vuot:1", "--ly-do", "ngắn")
    chay("--id", "H-THU-HAI", "--mo-ta", "giả thuyết thứ hai tuần này", "--trong-so", "log_vuot:1", ly)
    with pytest.raises(nao.TuChoi, match="7 ngày"):
        chay("--id", "H-THU-BA", "--mo-ta", "giả thuyết thứ ba tuần này", "--trong-so", "log_vuot:1", ly)
    assert "ĐẶC TRƯNG SỐ" in chay("--dac-trung")


def test_muc_nao_va_tab_truc_quan(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")
    monkeypatch.setattr(c, "hom_nay", lambda: NGAY)
    _dung_kenh_chia_khe(goc)
    b = danh_gia.doc_bang(goc)
    b["tang2"]["theo_kenh"]["KA"]["H-X"]["n"] = 6        # P 99% với n 6/8 → "sắp tới ngưỡng dẫn đầu"
    c.ghi_json(danh_gia.duong_bang(goc), b)
    luat.ghi_quyet_dinh(goc, [{"luc": NGAY + "T05:00:00", "ngay": NGAY, "loai": "mo_thu", "ten": "mở thử", "kenh": "KA",
                               "gt": "H-X", "n": 9, "ly_do": "bóng 10 ngày; tầng 1 qua sàn"}])
    from core.phong_thi_nghiem import bao_cao_nao, truc_quan
    d = "\n".join(bao_cao_nao.dong_nao(goc))
    assert "KA [chia khe BẬT]" in d and "H-X" in d and "thêm 2 video" in d and "gia-thuyet-moi" in d
    assert "mở thử H-X @KA" in d
    du = truc_quan.tinh(goc)
    k = du["kenh"][0]
    assert k["ma"] == "KA" and k["chia_khe"] is True and du["quyet_dinh"][0]["gt"] == "H-X"
    r = {x["gt"]: x for x in k["bang"]}
    assert r["H-X"]["vai"] == "thu" and r["H-X"]["ti_le_khe"] is not None and r["H-X"]["tang1"]["n"] == 40
    json.dumps(du, ensure_ascii=False)                    # trang JSON được


def test_trang_phong_thi_nghiem_dung_he_giao_dien_va_moi_trang_co_tab():
    from core import truc_quan as tq
    import re
    for ten in ("chien-truong.html", "truc-quan.html", "nao.html", "gioi-thieu.html", "phong-thi-nghiem.html"):
        with open(os.path.join(tq.GOC, "ui_web", ten), encoding="utf-8") as tep:
            s = tep.read()
        assert 'href="/phong-thi-nghiem"' in s, ten
    with open(os.path.join(tq.GOC, "ui_web", "phong-thi-nghiem.html"), encoding="utf-8") as tep:
        s = tep.read()
    assert "/vendor/he-thong.css" in s and "/vendor/chung.js" in s and "/phong-thi-nghiem.json" in s
    assert not re.search(r"""(src|href)=["']https?://""", s)
    with open(os.path.join(tq.VENDOR, "chung.js"), encoding="utf-8") as tep:
        assert "flask:" in tep.read()


def test_may_chu_phuc_vu_tab_phong_thi_nghiem():
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer
    from core import truc_quan as tq
    sv = ThreadingHTTPServer(("127.0.0.1", 0), tq._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        u = "http://127.0.0.1:{0}".format(sv.server_address[1])
        r = urllib.request.urlopen(u + "/phong-thi-nghiem", timeout=20)
        assert r.status == 200 and "Phòng thí nghiệm".encode("utf-8") in r.read()
        r = urllib.request.urlopen(u + "/phong-thi-nghiem.json", timeout=60)
        assert r.status == 200 and isinstance(json.loads(r.read().decode("utf-8")), dict)
    finally:
        sv.shutdown()
        sv.server_close()


def test_danh_gia_chay_ghi_lich_su_trang_thai_va_bang_moi(tmp_path, monkeypatch):
    from test_phong_thi_nghiem import _dung_goc
    from core.phong_thi_nghiem import chay
    monkeypatch.setenv("MYTOOL_PHONG_THI_NGHIEM", "1")
    goc = str(tmp_path)
    _dung_goc(goc)
    r = chay.chay_nguoc(goc, ["KA"], tu="2026-10-07", den="2026-10-09")
    b = r["bang"]
    assert b["phien_ban"] == 2 and b["tang1"]["cach"] == "lan_dau" and "tang1_cu" in b
    assert b["ngay_bong"]["KA"]["H-DOT-BIEN"] >= 1 and "tien_nghiem_tang1" in b
    assert "quyet_dinh" in b and os.path.isfile(luat.duong_trang_thai(goc))
    assert len(danh_gia.doc_lich_su(goc)) == 1
    danh_gia.chay(goc, kenh_ds=["KA"])
    assert len(danh_gia.doc_lich_su(goc)) == 1                                    # một dòng / ngày
    s = io.open(r["bao_cao"], encoding="utf-8").read()
    assert "TRƯỚC / SAU" in s and "Chia khe sản xuất" in s and "Vũ trụ ứng viên" in s
    assert os.path.isfile(danh_gia.duong_nen(goc, "KA", "2026-10-08"))
