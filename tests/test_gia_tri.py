"""HÀM GIÁ TRỊ (G2 bản 1, 20/10/2026, `core/gia_tri.py` + kỹ năng D23) và BẢNG ĐIỂM THẮNG (G1, `core/chien_truong.
bang_diem`, `core/bat_thuong.thi_phan_dung_yen`). Dữ liệu giả rất nhỏ, không mạng, không tải mô hình, không LLM."""
from __future__ import annotations

import datetime as _dt
import io
import json
import math
import os
import random

import numpy as np

from core import gia_tri as gt

D_NHO = 1 << 10


def _ghi(p, du):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as tep:
        if isinstance(du, str):
            tep.write(du)
        else:
            json.dump(du, tep, ensure_ascii=False)


def test_bam_ngram_co_dinh_va_dung_dong():
    r, c, v = gt.bam_ngram(["あい", "", "あい"], d=D_NHO)
    assert set(r.tolist()) == {0, 2}                      # dòng rỗng không có ô nào
    a = sorted(c[r == 0].tolist())
    assert a == sorted(c[r == 2].tolist())               # cùng chữ → cùng ô (băm cố định)
    assert len(a) == 3                                    # あ, い, あい (n-gram 3 không có)
    assert np.allclose(v[r == 0], 1 / math.sqrt(3))
    r2, c2, _v2 = gt.bam_ngram(["あい"], d=D_NHO)
    assert sorted(c2.tolist()) == a                       # không phụ thuộc vị trí trong lô
    assert c.max() < D_NHO


def test_spearman_va_lift():
    assert gt.spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) == 1.0
    assert gt.spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == -1.0
    assert gt.spearman([1, 1, 1, 1], [1, 2, 3, 4]) is None
    y = np.array([2.0] * 10 + [0.0] * 90)                # 10% nổ
    p = np.concatenate([np.ones(10), np.zeros(90)])
    lf = gt.lift_top(y, p)
    assert lf["nen"] == 0.1 and lf["top"] == 1.0 and lf["lift"] == 10.0


def test_nen_lang_gieng():
    v = np.array([1.0, 2.0, 3.0, 10.0, 20.0])
    ra = gt._nen_lang_gieng(v, k=10)  # noqa: SLF001 — ít hơn k video: nền = trung vị mọi video KHÁC
    for i in range(5):
        assert ra[i] == np.median(np.delete(v, i))
    v = np.arange(20, dtype=float)
    ra = gt._nen_lang_gieng(v, k=4)  # noqa: SLF001
    assert ra[10] == np.median([8, 9, 11, 12]) and ra[0] == np.median([1, 2, 3, 4]) and ra[19] == np.median([15, 16, 17, 18])


def _video(kenh, i, view, tieu_de, dang, chup="2026-10-19"):
    return {"vid": "v%s%03d" % (kenh, i), "kenh": kenh, "ten_kenh": kenh, "tieu_de": tieu_de,
            "dang": _dt.date.fromisoformat(dang), "chup": _dt.date.fromisoformat(chup), "view": float(view), "dai": 600.0,
            "subs": 1000.0, "nguon": "kenh-do"}


def test_tinh_nhan_so_trung_vi_kenh_cung_tuoi():
    ds = [_video("A", i, 1000, "t", "2026-10-01") for i in range(6)] + [_video("A", 9, 9000, "t", "2026-10-01")]
    ds += [_video("B", i, 100000, "t", "2026-10-01") for i in range(3)]        # kênh B < 5 video khác → bỏ
    ds += [_video("A", 20, 5000, "t", "2026-10-17")]                          # < 7 ngày tuổi → bỏ
    ra, tt = gt.tinh_nhan(ds)
    assert tt["n"] == 7 and {x["kenh"] for x in ra} == {"A"}
    no = {x["vid"]: x["y_no"] for x in ra}
    assert abs(no["vA009"] - math.log1p(9000) + math.log1p(1000)) < 1e-9     # gấp 9 trung vị kênh
    assert abs(no["vA000"]) < 1e-9


def _du_lieu_gia(n_kenh=12, n_video=60, seed=1):
    """Tiêu đề có «秘密» → nổ ×6; còn lại nhiễu. Đăng rải 120 ngày."""
    rnd = random.Random(seed)
    ds = []
    goc_ngay = _dt.date(2026, 6, 1)
    for k in range(n_kenh):
        quy_mo = 10 ** rnd.uniform(2, 5)
        for i in range(n_video):
            co = rnd.random() < 0.3
            td = ("【心理学】" if rnd.random() < 0.5 else "") + ("秘密の" if co else "普通の") + rnd.choice(
                ["人", "習慣", "特徴", "老後", "脳"]) + str(rnd.randint(1, 9))
            v = quy_mo * (6.0 if co else 1.0) * math.exp(rnd.gauss(0, 0.3))
            ds.append(_video("K%02d" % k, i, v, td, (goc_ngay + _dt.timedelta(days=rnd.randint(0, 120))).isoformat()))
    return ds


def test_hoc_tren_du_lieu_gia_vuot_moc_va_luu_nap(tmp_path):
    ds, _tt = gt.tinh_nhan(_du_lieu_gia())
    mh = gt.huan_luyen_mo_hinh(ds, "y_no", lam_thu=(3.0, 30.0), d=D_NHO)
    k = mh["kiem"]
    assert k["n_giu"] > 50 and k["rho_giu_y_no"] > 0.4
    assert k["lift_10"]["lift"] and k["lift_10"]["lift"] > 1.5
    y = np.array([x["y_no"] for x in ds])
    moc = gt.moc_don_gian(ds, np.setdiff1d(np.arange(len(ds)), mh["giu"]), mh["giu"], y)
    assert moc["do_dai"]["rho"] is None or moc["do_dai"]["rho"] < k["rho_giu_y_no"]
    goc = str(tmp_path)
    gt.luu(goc, mh, {"luc_hoc": "2026-10-20 01:35:00", "kiem": k})
    gt._DEM_MH.clear()  # noqa: SLF001
    a = gt.du_doan(goc, "秘密の習慣3")
    b = gt.du_doan(goc, "普通の習慣3")
    assert a is not None and b is not None and a > b
    assert gt.du_doan(str(tmp_path / "khong-co"), "秘密") is None              # chưa có mô hình → None, không ném
    assert len(gt.du_doan_nhieu(goc, ["a", "b", "c"])) == 3


def test_luu_giu_toi_da_va_con_tro(tmp_path):
    ds, _tt = gt.tinh_nhan(_du_lieu_gia(n_kenh=6, n_video=30))
    mh = gt.huan_luyen_mo_hinh(ds, "y_no", lam_thu=(10.0,), d=D_NHO)
    goc = str(tmp_path)
    for i in range(gt.GIU_TOI_DA + 2):
        p = gt.luu(goc, mh, {"luc_hoc": "x"})
        os.utime(p, (i, i))
    tep = sorted(os.listdir(gt.thu_muc(goc)))
    assert len([t for t in tep if t.startswith("mo-hinh-")]) <= gt.GIU_TOI_DA
    hh = json.load(open(gt.duong_hien_hanh(goc), encoding="utf-8"))
    assert hh["tep"] in tep


def test_doc_video_bo_trung_va_bo_kenh_ta(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "g", "nghien-cuu", "kenh-do.json"), {
        "u1": {"ngay": "2026-10-19", "ch": {"name": "DT", "channel_id": "UC1", "subscribers": 500, "videos": [
            {"video_id": "aaaaaaaaaaa", "title": "x", "views": 10, "duration_s": 60, "upload_date": "2026-10-01"}]}},
        "u2": {"ngay": "2026-10-19", "ch": {"name": "TA", "channel_id": "UC2", "subscribers": 5, "videos": [
            {"video_id": "bbbbbbbbbbb", "title": "y", "views": 10, "duration_s": 60, "upload_date": "2026-10-01"}]}}})
    _ghi(os.path.join(goc, "CHANNEL", "K1", "nghien-cuu", "content.csv"),
         "Kênh,Tiêu đề video,Link video,Ngày đăng,Thời lượng,View\n"
         "DT,x,https://www.youtube.com/watch?v=aaaaaaaaaaa,2026-10-01,1:00,99\n"
         "DT,z,https://www.youtube.com/watch?v=ccccccccccc,2026-09-01,10:41,50\n")
    ds = {x["vid"]: x for x in gt.doc_video(goc, bo_ten={"TA"})}
    assert set(ds) == {"aaaaaaaaaaa", "ccccccccccc"}
    assert ds["aaaaaaaaaaa"]["nguon"] == "kenh-do" and ds["aaaaaaaaaaa"]["view"] == 10
    assert ds["ccccccccccc"]["kenh"] == "UC1" and ds["ccccccccccc"]["dai"] == 641 and ds["ccccccccccc"]["subs"] == 500


def test_can_chay_gio_vang_va_nhip(tmp_path):
    goc = str(tmp_path)
    assert gt.can_chay(goc, _dt.datetime(2026, 10, 20, 1, 35))[0] is False          # chưa có dữ liệu
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "g", "nghien-cuu", "kenh-do.json"), {})
    assert gt.can_chay(goc, _dt.datetime(2026, 10, 20, 1, 35))[0] is True
    assert gt.can_chay(goc, _dt.datetime(2026, 10, 20, 14, 35))[0] is False         # giờ sản xuất
    _ghi(gt.duong_hien_hanh(goc), {"luc_hoc": "2026-10-18 01:35:00"})
    assert gt.can_chay(goc, _dt.datetime(2026, 10, 20, 1, 35))[0] is False          # mới 2 ngày
    assert gt.can_chay(goc, _dt.datetime(2026, 10, 26, 1, 35))[0] is True


def test_cong_san_xuat():
    k = {"rho_giu_y_no": 0.35}
    assert gt.dat_cong(k, {"doi_dau": {"n": 25, "mo_hinh_rho_w": 0.3, "llm_rho_w": 0.2}})[0] is True
    assert gt.dat_cong(k, {"doi_dau": {"n": 15, "mo_hinh_rho_w": 0.3, "llm_rho_w": 0.2}})[0] is False
    assert gt.dat_cong(k, {"doi_dau": {"n": 25, "mo_hinh_rho_w": 0.1, "llm_rho_w": 0.2}})[0] is False
    assert gt.dat_cong({"rho_giu_y_no": 0.2}, {"doi_dau": {"n": 25, "mo_hinh_rho_w": 0.3, "llm_rho_w": 0.2}})[0] is False


def test_hieu_chuan_ghi_bo_cham_gia_tri(tmp_path):
    from core import hieu_chuan as hc
    assert {"gia_tri_tieu_de", "gia_tri_de_tai"} <= set(hc.BO_CHAM)
    goc = str(tmp_path)
    hs = {"ma_goi": "K1-0001", "video_id": "v1", "tieu_de": "秘密の習慣", "thoi_luong_giay": 600,
          "tieu_de_cham": {"chon": 1, "diem": {"A": 5, "B": 7},
                           "ung_vien": [{"ten": "đối chứng", "tieu_de": "普通の人"}, {"ten": "bản 2", "tieu_de": "秘密の習慣"}]}}
    assert hc._dong_gia_tri(goc, "K1", "K1-0001", hs, "") == []                    # noqa: SLF001 — chưa có mô hình
    ds, _tt = gt.tinh_nhan(_du_lieu_gia(n_kenh=6, n_video=40))
    gt.luu(goc, gt.huan_luyen_mo_hinh(ds, "y_no", lam_thu=(10.0,), d=D_NHO), {"luc_hoc": "x"})
    gt._DEM_MH.clear()  # noqa: SLF001
    dong = hc._dong_gia_tri(goc, "K1", "K1-0001", hs, "")  # noqa: SLF001
    bo = {d["bo_cham"]: d for d in dong}
    assert set(bo) == {"gia_tri_tieu_de", "gia_tri_de_tai"} and all(d["chon"] for d in dong)
    assert bo["gia_tri_tieu_de"]["diem"] > bo["gia_tri_de_tai"]["diem"]
    # phân vị thước chung không bị chia/trừ trung vị kênh khi gộp
    cap = hc._cap(dong, {"K1": {"K1-0001": {"pv": 80.0}}}, "pv", {"K1": {"ctr": 5.0}})  # noqa: SLF001
    assert cap and all(c[1] == 80.0 for c in cap)


def test_ky_nang_d23():
    from core import ky_nang as kn
    from core import ky_nang_tu as knt
    k = kn.theo_ma("D23")
    assert k and k.tu_ap and k.toan_may and not k.nang and knt.BO_PHAN["D23"] == "chon-content"


# ── G1 ──────────────────────────────────────────────────────────────────────


def test_bang_diem_hang_khoang_cach_muc_tieu():
    from core import chien_truong as ct
    dich = {"d%02d" % i: float(1000 * (20 - i)) for i in range(15)}     # 20k, 19k, … 6k
    quan = [{"ma": "TA1", "view_28": 2000.0}, {"ma": "TA2", "view_28": 19500.0}, {"ma": "TA3", "view_28": 0.0}]
    ls = [{"ngay": "2026-10-13", "tong": {"dich": 200000, "ta": 1000, "thi_phan": 0.5},
           "quan": {"TA1": {"view_28": 1000.0}}, "bang_diem": {"hang": {"TA1": 19}}}]
    bd = ct.bang_diem(dich, quan, ls, _dt.date(2026, 10, 20))
    assert bd["nguong_top"] == 12000                 # hạng 10 giữa 15 địch + 3 ta: 20,19.5,19,…,12k
    t2 = bd["kenh"]["TA2"]
    assert t2["hang"] == 2 and t2["trong_top"] and t2["tang_tuan_pct"] == 0.0
    t1 = bd["kenh"]["TA1"]
    assert t1["hang"] == 17 and t1["gap"] == 6.0 and not t1["trong_top"]
    assert abs(t1["muc_tieu_tuan"] - 2000 * 6 ** (1 / ct.TUAN_MUC_TIEU)) <= 1
    assert t1["view_7"] == 1000 and t1["hang_7"] == 19 and t1["doi_thi_phan_7"] > 0
    assert bd["kenh"]["TA3"]["gap"] is None and bd["tot_nhat"] == "TA2"
    assert bd["ngay_7"] == "2026-10-13"


def test_thi_phan_dung_yen_va_bao_mot_lan_moi_tuan(tmp_path, monkeypatch):
    from core import bat_thuong as bt
    ls = [{"ngay": "2026-10-%02d" % d, "tong": {"thi_phan": 0.23 + 0.001 * (d % 3)},
           "quan": {"TA1": {"view_28": 1000}}, "bang_diem": {"nguong_top": 3200000, "hang": {"TA1": 40}}}
          for d in range(6, 21)]
    r = bt.thi_phan_dung_yen(ls)
    assert r["dung_yen"] and r["ngay_cu"] == "2026-10-13" and r["ngay_moi"] == "2026-10-20"
    ghi = []
    monkeypatch.setattr(bt, "_nao", lambda *a, **k: ghi.append((a, k)))
    dong = bt.bao_thi_phan(str(tmp_path), lich_su=ls)
    assert any("ĐỨNG YÊN" in d for d in dong) and any("TA1 #40" in d for d in dong)
    assert len(ghi) == 1 and ghi[0][0][2] == "chon-content" and ghi[0][0][5] == "thi-phan-dung-yen:2026-W43"
    bt.bao_thi_phan(str(tmp_path), lich_su=ls, thu=True)
    assert len(ghi) == 1                              # chạy thử: không ghi
    tang = [dict(x) for x in ls]
    tang[-1] = dict(tang[-1], tong={"thi_phan": 0.40})
    assert bt.thi_phan_dung_yen(tang)["dung_yen"] is False
    assert bt.thi_phan_dung_yen(ls[-3:]) is None      # chưa đủ 7 ngày
