"""Phát hiện tụt + tự chẩn đoán (`core/bat_thuong.py`) — chuỗi dựng tay, AI/mạng giả."""
import json
import os

from core import bat_thuong as bt

GIO = 3600.0


def _video(i, ht, ctr=4.0, browse=80.0, nhan="trung_binh", avd=30.0):
    return {"ma": "v{0:010d}".format(i), "dang": 1_790_000_000 + i * 86400.0, "ngay": "2026-10-{0:02d}".format(1 + i % 28),
            "hien_thi": ht, "ctr": ctr, "avd": avd, "browse": browse, "sub_1k": 2.0, "nhan": nhan, "tuoi_max": 200}


def _chuoi():
    tot = [_video(i, 5000 + 100 * i, nhan="thang") for i in range(8)]
    sup = [_video(8 + i, 500, ctr=1.8, browse=30.0, nhan="truot") for i in range(4)]
    return tot + sup


def test_phat_hien_tut_va_khong_phan_o_48h():
    ds = _chuoi()
    bay = ds[-1]["dang"] + 100 * GIO
    p = bt.phat_hien(ds, bay=bay)
    assert p["du"] and "hien_thi" in p["tut"] and "browse" in p["tut"] and "ctr" in p["tut"]
    # video mới nhất mới 48 giờ: chưa vào cửa sổ phán (cửa sổ lùi một video)
    p48 = bt.phat_hien(ds, bay=ds[-1]["dang"] + 48 * GIO)
    assert ds[-1]["ma"] not in p48["cua_so"]


def test_khong_tut_khi_on_dinh_va_kenh_chua_duoc_phat():
    on = [_video(i, 5000, nhan="thang") for i in range(12)]
    assert bt.phat_hien(on, bay=on[-1]["dang"] + 100 * GIO)["tut"] == []
    chet = [_video(i, 10, nhan="truot") for i in range(12)]
    p = bt.phat_hien(chet, bay=chet[-1]["dang"] + 100 * GIO)
    assert not p["du"] and "chưa được phát" in p["ly_do"]


def test_tut_phu_mot_minh_chi_canh_bao():
    ds = [_video(i, 5000, nhan="thang") for i in range(9)] + [_video(9 + i, 5000, avd=10.0, nhan="thang") for i in range(3)]
    p = bt.phat_hien(ds, bay=ds[-1]["dang"] + 100 * GIO)
    assert p["tut"] == [] and p["canh_bao"] == ["avd"]


def test_lich_su_cho_ngay_bat_dau_dot_tut():
    ds = _chuoi()
    ls = bt.lich_su(ds)
    assert ls and all("hien_thi" in x["tut"] or "ctr" in x["tut"] for x in ls)
    assert bt.bat_dau_tut(ls, ds) == ds[8]["ngay"] or bt.bat_dau_tut(ls, ds) in [x["ngay"] for x in ds[6:10]]


def test_chay_kenh_chan_doan_va_tu_lam(tmp_path, monkeypatch):
    goc = str(tmp_path)
    ds = _chuoi()
    monkeypatch.setattr(bt, "tin_hieu_kenh", lambda g, k: ds)
    import time
    monkeypatch.setattr(time, "time", lambda: ds[-1]["dang"] + 100 * GIO)
    sai = {"vid": ds[-1]["ma"], "ma": "K-0012", "ok": False, "cach": "doc2", "ly_do": "chữ trên ảnh 「意」≠「惹」",
           "chu": "惹かれる"}
    monkeypatch.setattr(bt, "chan_doan", lambda *a, **k: {
        "bia_sai_chu": [sai], "bia": [sai], "kieu": {"lech": False}, "de_tai": {"lech": False},
        "san_xuat": {"co_loi": False, "avd_tut": False, "qc_kem": []}})
    ab = []
    monkeypatch.setattr(bt, "xep_ab", lambda g, k, d, p, thu=False: ab.append(p["cua_so"]) or ["x"])
    kq = bt.chay_kenh(goc, "K", goi=lambda *a, **k: "")
    assert kq["phat_hien"]["tut"] and kq["lam"]["sua_bia"][0]["ma"] == "K-0012" and ab
    assert "bìa sai chữ" in kq["gay"][0]
    hang = json.load(open(bt.duong_hang_sua_bia(goc), encoding="utf-8"))["viec"]
    assert len(hang) == 1 and hang[0]["trang_thai"] == "cho"
    bt.chay_kenh(goc, "K", goi=lambda *a, **k: "")                         # chạy lại: không xếp trùng
    assert len(json.load(open(bt.duong_hang_sua_bia(goc), encoding="utf-8"))["viec"]) == 1
    assert os.path.isfile(os.path.join(goc, "workspace", "tu-kiem", "bat-thuong", "K.json"))


def test_soat_bia_song_trung_dau_khong_goi_ai(tmp_path, monkeypatch):
    from PIL import Image
    from core import cong_chu, studio_may
    goc = str(tmp_path)
    p = os.path.join(goc, "bia.jpg")
    Image.new("RGB", (1280, 720), (10, 200, 30)).save(p)
    with open(p, "rb") as f:
        du = f.read()
    monkeypatch.setattr(studio_may, "ma_goi_cua_video", lambda g, k, v: "K-0001")
    monkeypatch.setattr(bt, "_tep_co_dau", lambda g, k, v, m: [p])
    goi = []
    kq = bt.soat_bia_song(goc, "K", ["VVVVVVVVVVV"], lambda *a, **k: goi.append(1) or "",
                          tai=lambda u: (200, du))
    assert kq[0]["ok"] is True and kq[0]["cach"] == "dau" and goi == []
    monkeypatch.setattr(bt, "_tep_co_dau", lambda g, k, v, m: [])
    monkeypatch.setattr(cong_chu, "_chu_mong_goi", lambda g, k, m: {"chu": "惹かれる"})
    monkeypatch.setattr(cong_chu, "kiem_anh", lambda goi, tep, chu, khoa="": {"ok": False, "ly_do": ["sai kanji"]})
    kq = bt.soat_bia_song(goc, "K", ["VVVVVVVVVVV"], lambda *a, **k: "", tai=lambda u: (200, du))
    assert kq[0]["ok"] is False and "sai kanji" in kq[0]["ly_do"]


def test_sua_bia_xong_va_hong(tmp_path, monkeypatch):
    from core import cong_chu
    goc = str(tmp_path)
    bt.xep_sua_bia(goc, "K", [{"vid": "VVVVVVVVVVV", "ma": "K-0001", "chu": "惹かれる", "ly_do": "sai"}])
    monkeypatch.setattr(cong_chu, "_ngu_canh", lambda g, k, m: {"tieu_de": "t", "ngu_canh": ""})
    monkeypatch.setattr(cong_chu, "chot_chu", lambda goi, chu, **k: {"ok": True, "chu": chu})
    monkeypatch.setattr(cong_chu, "xac_minh", lambda goi, tep, chu, **k: {"ok": tep.endswith("2.jpg")})
    xep = []
    kq = bt.sua_bia(goc, "K", goi=lambda *a, **k: "", chay_lo=lambda **k: {"top": [{"tep": "a1.jpg"}, {"tep": "a2.jpg"}]},
                    xep=lambda *a, **k: xep.append(a))
    assert kq["ket"] == "xong" and kq["anh"] == "a2.jpg" and xep[0][2] == "K-0001"
    assert bt.viec_sua_bia(goc, "K") == []
    bt.xep_sua_bia(goc, "K", [{"vid": "WWWWWWWWWWW", "ma": "K-0002", "chu": "x", "ly_do": "sai"}])
    kq = bt.sua_bia(goc, "K", goi=lambda *a, **k: "", chay_lo=lambda **k: {"top": []}, xep=lambda *a, **k: None)
    assert kq["ket"] == "hong" and bt.viec_sua_bia(goc, "K")[0]["lan"] == 1     # giữ việc, lần sau thử lại
