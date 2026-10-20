"""NHÃN NGHĨA TIÊU ĐỀ (G2 bản 2, 20/10/2026, `core/nhan_nghia.py` + khối nghĩa của `core/gia_tri.py` + kỹ năng D24).
LLM GIẢ (hàm trả chữ dựng sẵn), không mạng, không ví, dữ liệu giả rất nhỏ."""
from __future__ import annotations

import datetime as _dt
import io
import json
import math
import os
import random

import numpy as np

from core import gia_tri as gt
from core import nhan_nghia as nn

D_NHO = 1 << 10


def _ma(**doi):
    """Một chuỗi mã hợp lệ (giá trị đầu của mỗi trường, đổi theo `doi`) + chủ đề."""
    p = [doi.get(t[0], t[2][0]) for t in nn.TRUONG]
    return "|".join(p) + "|" + doi.get("chu_de", "brain aging habits")


def _goi_gia(tra_loi):
    """`tra_loi(de_bai, khoa) -> str`; ghi lại các lượt gọi; cộng usage giả."""
    goi_ds = []

    def goi(de, khoa, so_dung):
        goi_ds.append((de, khoa))
        so_dung["token_vao"] = int(so_dung.get("token_vao") or 0) + 1000
        so_dung["token_ra"] = int(so_dung.get("token_ra") or 0) + 500
        so_dung["luot"] = int(so_dung.get("luot") or 0) + 1
        return tra_loi(de, khoa)
    goi.ds = goi_ds
    return goi


def _so_tieu_de(de):
    return sum(1 for d in de.split("Titles:\n", 1)[1].split("\n\n", 1)[0].splitlines() if d.strip())


def test_doc_mot_chat_va_bo_ma_la():
    x = nn.doc_mot(_ma(hua="secret", cuoc="3", chu_de="Dementia  Early Signs, Now"))
    assert x["n"]["hua"] == "secret" and x["n"]["cuoc"] == "3" and x["c"] == "dementia early signs, now"
    y = nn.doc_mot(_ma(hua="banana"))                                  # 1 mã lạ → trường đó None, vẫn nhận
    assert y is not None and y["n"]["hua"] is None
    assert nn.doc_mot(_ma(hua="x", cam="x", tam="x")) is None          # quá nhiều mã lạ → bỏ
    assert nn.doc_mot("secret|60s") is None and nn.doc_mot(None) is None
    z = nn.doc_mot(_ma(nguoc="yes", hoi="no"))
    assert z["n"]["nguoc"] == "y" and z["n"]["hoi"] == "n"


def test_doc_tra_loi_json_rao_va_mang():
    chu = "```json\n" + json.dumps({"1": _ma(), "2": "rác", "3": _ma(hua="list"), "9": _ma()}) + "\n```"
    ra = nn.doc_tra_loi(chu, 3)
    assert set(ra) == {0, 2} and ra[2]["n"]["hua"] == "list"
    assert set(nn.doc_tra_loi(json.dumps([_ma(), _ma()]), 2)) == {0, 1}
    assert nn.doc_tra_loi("không phải json", 3) == {}


def test_de_bai_va_khoa_lo_co_dinh():
    de = nn.de_bai(["秘密の習慣", "老後の不安"], ngach="niche X")
    assert "1. 秘密の習慣" in de and "2. 老後の不安" in de and "niche X" in de
    for t in nn.TRUONG:
        assert t[2][0] in de
    k1, k2 = nn.khoa_lo(["a", "b"]), nn.khoa_lo(["a", "b"])
    assert k1 == k2 and k1 != nn.khoa_lo(["b", "a"]) and k1.isascii()
    assert nn.bam("ＡＢ  c") == nn.bam("AB c")                          # NFKC + gộp khoảng trắng


def test_gan_lo_sua_mot_lan_chi_tieu_de_hong():
    def tra(de, khoa):
        n = _so_tieu_de(de)
        if not khoa.endswith(":sua"):
            return json.dumps({str(i + 1): (_ma() if i % 2 == 0 else "hỏng") for i in range(n)})
        return json.dumps({str(i + 1): _ma(hua="warning") for i in range(n)})
    goi = _goi_gia(tra)
    nhan, sd = nn.gan_lo(goi, ["t%d" % i for i in range(6)], ngach="n")
    assert len(goi.ds) == 2 and goi.ds[1][1].endswith(":sua") and _so_tieu_de(goi.ds[1][0]) == 3
    assert set(nhan) == set(range(6)) and nhan[1]["n"]["hua"] == "warning" and nhan[0]["n"]["hua"] == "secret"
    assert sd["token_vao"] == 2000 and sd["luot"] == 2 and nn.tien_micro(sd) == 2000 * 1750 + 1000 * 8750


def test_gan_lo_goi_hong_khong_sua():
    def tra(de, khoa):
        raise RuntimeError("mạng")
    goi = _goi_gia(tra)
    nhan, sd = nn.gan_lo(goi, ["a", "b"])
    assert nhan == {} and len(goi.ds) == 1 and "loi" in sd


def test_gan_ghi_nho_dem_chi_va_khong_hoi_lai(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(nn, "_ngach", lambda: "n")
    goi = _goi_gia(lambda de, khoa: json.dumps({str(i + 1): _ma() for i in range(_so_tieu_de(de))}))
    td = ["題%d" % i for i in range(23)] + ["題1", "  題2 "]          # trùng (sau chuẩn hoá) → hỏi một lần
    bc = nn.gan(goc, td, goi=goi, lo=10, so_luong=2, in_ra=lambda *_a: None)
    assert bc["can"] == 23 and bc["da"] == 23 and bc["lo"] == 3 and len(goi.ds) == 3
    nho = nn.doc_nho(goc)
    assert len(nho) == 23 and nn.tra(goc, "題5")["n"]["hua"] == "secret"
    c = nn.tong_chi(goc)
    assert c["lo"] == 3 and c["dat"] == 23 and c["token_vao"] == 3000 and c["vnd"] == round(c["micro"] / 1e6, 1)
    bc2 = nn.gan(goc, td, goi=goi, in_ra=lambda *_a: None)
    assert bc2["can"] == 0 and len(goi.ds) == 3                         # đã có nhãn → không gọi lại


def test_gan_dung_khi_uoc_vuot_tran(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(nn, "_ngach", lambda: "n")
    goi = _goi_gia(lambda de, khoa: json.dumps({str(i + 1): _ma() for i in range(_so_tieu_de(de))}))
    bc = nn.gan(goc, ["x%d" % i for i in range(200)], goi=goi, lo=5, so_luong=1, tran_vnd=1.0,
                in_ra=lambda *_a: None)
    assert bc.get("dung_vi_tran") and bc["lo"] == 3 and len(goi.ds) == 3


def test_cai_dat_tat(tmp_path):
    goc = str(tmp_path)
    assert nn.bat(goc)
    os.makedirs(os.path.join(goc, "workspace"))
    with io.open(os.path.join(goc, "workspace", "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump({nn.KHOA_CAI: False, nn.KHOA_KHOI: False}, tep)
    assert not nn.bat(goc) and nn.can_chay(goc)[0] is False
    assert nn.khoi_tin_hieu(goc) == ""


# ── khối nghĩa trong hàm giá trị ────────────────────────────────────────────


def test_khoa_nghia_cac_khoi():
    ng = nn.doc_mot(_ma(hua="secret", tuoi="60s", cuoc="3", sac="neg", chu_de="lonely old age"))
    k = dict(gt.khoa_nghia(ng, "vung-a"))
    assert k["t:hua=secret"] == 1.0 and k["o:cuoc"] == 1.0 and k["o:sac"] == -1.0
    assert abs(k["cd:lonely"] - 1 / math.sqrt(3)) < 1e-12
    assert "x:tuoi=60s|hua=secret" in k and "x:vung=vung-a|hua=secret" in k
    assert gt.khoa_nghia(None) == [("nghia_thieu", 1.0)]
    assert all(a.startswith("t:") for a, _b in gt.khoa_nghia(ng, None, khoi=("t",)))
    r, c, v = gt.bam_nghia([{"nghia": ng, "vung": None}, {"nghia": None}], d=D_NHO)
    assert set(r.tolist()) == {0, 1} and c.max() < D_NHO and len(c) == len(v)


def _video(kenh, i, view, tieu_de, dang):
    return {"vid": "v%s%03d" % (kenh, i), "kenh": kenh, "ten_kenh": kenh, "tieu_de": tieu_de,
            "dang": _dt.date.fromisoformat(dang), "chup": _dt.date(2026, 10, 19), "view": float(view), "dai": 600.0,
            "subs": 1000.0, "nguon": "kenh-do"}


def _du_lieu_nghia(seed=3):
    """Tiêu đề ngẫu nhiên (chữ không mang tín hiệu); NHÃN «hua=secret» → nổ ×6, «warning» → ×0,3, «list» (phổ biến
    nhất = mốc) ×1. Chỉ khối nghĩa học được."""
    rnd = random.Random(seed)
    ds, nhan = [], {}
    goc_ngay = _dt.date(2026, 6, 1)
    for k in range(12):
        quy_mo = 10 ** rnd.uniform(2, 5)
        for i in range(60):
            u = rnd.random()
            hua, he = ("secret", 6.0) if u < 0.3 else (("warning", 0.3) if u < 0.5 else ("list", 1.0))
            td = "".join(rnd.choice("あいうえおかきくけこ") for _ in range(6)) + str(i)
            nhan[td] = nn.doc_mot(_ma(hua=hua, chu_de="x y"))
            v = quy_mo * he * math.exp(rnd.gauss(0, 0.3))
            ds.append(_video("K%02d" % k, i, v, td, (goc_ngay + _dt.timedelta(days=rnd.randint(0, 120))).isoformat()))
    return ds, nhan


def test_hoc_co_nghia_vuot_ban_1_va_luu_nap(tmp_path):
    ds0, nhan = _du_lieu_nghia()
    ds, _tt = gt.tinh_nhan(ds0)
    for x in ds:
        x["nghia"] = nhan[x["tieu_de"]]
    m1 = gt.huan_luyen_mo_hinh(ds, "y_no", lam_thu=(10.0,), d=D_NHO)
    m2 = gt.huan_luyen_mo_hinh(ds, "y_no", lam_thu=(10.0,), d=D_NHO, nghia=True, lam_nghia_thu=(10.0, 1.0),
                               d_nghia=D_NHO)
    assert m2["kiem"]["nghia"] and m2["kiem"]["rho_giu_y_no"] > 0.4
    assert m2["kiem"]["rho_giu_y_no"] > (m1["kiem"]["rho_giu_y_no"] or 0) + 0.2
    # nhớ đệm nhãn trên đĩa → du_doan_nhieu tự gắn nhãn cho tiêu đề ứng viên
    goc = str(tmp_path)
    a, b = next(t for t, v in nhan.items() if v["n"]["hua"] == "secret"), next(
        t for t, v in nhan.items() if v["n"]["hua"] == "list")
    nn._noi_dong(nn.duong_nho(goc), [{"h": nn.bam(t), "v": nn.PHIEN_BAN, "n": nhan[t]["n"], "c": nhan[t]["c"]}  # noqa: SLF001
                                     for t in (a, b)])
    gt.luu(goc, m2, {"luc_hoc": "2026-10-20 22:00:00", "kiem": m2["kiem"]})
    gt._DEM_MH.clear()  # noqa: SLF001
    mh = gt.nap(goc)
    assert mh["d_nghia"] == D_NHO and list(mh["khoi"]) == list(gt.KHOI_NGHIA)
    pa, pb = gt.du_doan_nhieu(goc, [a, b])
    assert pa is not None and pb is not None and pa > pb + 0.5
    x = [{"tieu_de": a}]
    assert gt.gan_nghia(goc, x) == 1.0 and x[0]["nghia"]["n"]["hua"] == "secret"


def test_phan_tich_bao_cao_va_khoi(tmp_path):
    ds0, nhan = _du_lieu_nghia(seed=5)
    ds, _tt = gt.tinh_nhan(ds0)
    for x in ds:
        x["nghia"] = nhan[x["tieu_de"]]
    pt = nn.phan_tich(ds, n_min=50)
    by = {r["khoa"]: r for r in pt["nhan"]}
    assert by["hua=secret"]["dieu_chinh_pp"] > 10 and by["hua=secret"]["lift"] > 1.5 and by["hua=secret"]["on_dinh"]
    assert "hua=list" not in by and by["hua=secret"]["so_voi"] == "hua=list"      # mốc = giá trị phổ biến nhất
    assert by["hua=warning"]["dieu_chinh_pp"] < 0
    goc = str(tmp_path)
    md = nn.bao_cao(goc, pt, luc="2026-10-20 23:00")
    assert "kiểu hứa hẹn: bí mật" in md and os.path.isfile(os.path.join(nn.thu_muc(goc), nn.TEP_BAO_CAO))
    k = nn.khoi_tin_hieu(goc)
    assert k.startswith("TÍN HIỆU THỊ TRƯỜNG") and "kiểu hứa hẹn: bí mật" in k and "so với «danh sách»" in k


def test_ky_nang_d24():
    from core import ky_nang as kn
    from core import ky_nang_tu as knt
    k = kn.theo_ma("D24")
    assert k and k.tu_ap and k.toan_may and not k.nang and knt.BO_PHAN["D24"] == "chon-content"
    assert "--toi-da" in k.chay("g", "")
