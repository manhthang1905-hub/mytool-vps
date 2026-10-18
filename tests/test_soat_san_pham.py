"""Soát sản phẩm hằng tuần + vòng cải tiến (`core/soat_san_pham.py`) — AI / vẽ giả, không mạng."""
import json
import os

from core import soat_san_pham as ss


def _m(nd, giong=9, loi=9, pc=9, ron=False, tong=None):
    d = {"noi_dung": nd, "giong": giong, "loi": loi, "phong_cach": pc}
    return {"diem": d, "kinh_di": ron, "tong": tong if tong is not None else min(d.values()), "ly_do": "x", "sua": ""}


def test_ti_le_va_xau_hon():
    t = ss.ti_le_anh([_m(3), _m(8), _m(9, giong=5), None])
    assert t["n"] == 3 and t["noi_dung_hong"] == 33.3 and t["ron"] == 33.3 and t["dat_ca"] == 33.3
    assert ss.xau_hon({"noi_dung_hong": 10, "ron": 0, "dat_ca": 60}, {"n": 20, "noi_dung_hong": 30, "ron": 2,
                                                                     "dat_ca": 40}) == ["noi_dung_hong", "dat_ca"]
    assert ss.xau_hon({}, {"n": 20, "noi_dung_hong": 45, "ron": 12, "dat_ca": 20}) == ["noi_dung_hong", "ron"]
    assert ss.xau_hon({}, {"n": 0}) == []


def test_dat_thanh():
    truoc = [_m(3), _m(4), _m(5), _m(8)]
    ok, cau = ss.dat_thanh(truoc, [_m(8), _m(7), _m(8), _m(9)])
    assert ok, cau
    ok, cau = ss.dat_thanh(truoc, [_m(8), _m(7), _m(8, ron=True), _m(9)])
    assert not ok and "rợn mới 1" in cau
    assert not ss.dat_thanh(truoc, [_m(4), _m(4), _m(5), _m(8)])[0]
    assert not ss.dat_thanh(truoc[:2], [_m(9), _m(9)])[0]


def _kenh_gia(goc, kenh="K"):
    d = os.path.join(goc, "CHANNEL", kenh, "prompt")
    os.makedirs(d)
    with open(os.path.join(d, "7-canh.md"), "w", encoding="utf-8") as f:
        f.write("# khuôn cảnh\n")
    with open(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write('ma: "K"\n')


def test_cai_tien_qua_thanh_thi_sao_luu_roi_ap(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh_gia(goc)
    canh = [{"so": i, "tep": "", "loi_doc": "câu {0}".format(i), "ai": "nv1", "prompt": "a calm scene number {0} "
             "with the reference character at a desk".format(i) * 2} for i in range(1, 5)]
    cham = [_m(3), _m(4), _m(4), _m(5)]
    monkeypatch.setattr(ss, "cham_mot", lambda goi, tep, **k: _m(8))
    goi = lambda ln, **k: "Show the literal moment of the line with its key object." if "ONE short rule" in ln \
        else "a new warm scene showing the reference character holding the key object of the narration line"  # noqa: E731
    ve = lambda ln, n, khoa, dich: [d for d in dich]  # noqa: E731
    kq = ss.cai_tien_anh(goc, "K", canh, cham, goi=goi, ve=ve, log=lambda s: None)
    assert kq["ket"] == "dat" and kq["da_ap"], kq
    noi = open(os.path.join(goc, "CHANNEL", "K", "prompt", "7-canh.md"), encoding="utf-8").read()
    assert ss.DAU in noi and "literal moment" in noi and noi.startswith("# khuôn cảnh")
    assert os.path.isfile(os.path.join(kq["da_ap"], "7-canh.md")) and os.path.isfile(os.path.join(kq["da_ap"], "GHI-CHU.md"))
    # lần sau: THAY khối cũ, không chồng thêm
    ss.ap_luat(goc, "K", "Rule two.", "đo lại")
    noi = open(os.path.join(goc, "CHANNEL", "K", "prompt", "7-canh.md"), encoding="utf-8").read()
    assert noi.count(ss.DAU) == 1 and "Rule two." in noi and "literal moment" not in noi


def test_cai_tien_khong_qua_thanh_thi_khong_doi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh_gia(goc)
    canh = [{"so": i, "tep": "", "loi_doc": "c", "ai": "nv1", "prompt": "a scene with the reference character " * 3}
            for i in range(1, 5)]
    monkeypatch.setattr(ss, "cham_mot", lambda goi, tep, **k: _m(4))
    goi = lambda ln, **k: "Some rule that is long enough." if "ONE short rule" in ln \
        else "another scene with the reference character at the table today"  # noqa: E731
    kq = ss.cai_tien_anh(goc, "K", canh, [_m(3)] * 4, goi=goi, ve=lambda ln, n, k, d: list(d), log=lambda s: None)
    assert kq["ket"] == "khong_dat" and not kq["da_ap"]
    assert open(os.path.join(goc, "CHANNEL", "K", "prompt", "7-canh.md"), encoding="utf-8").read() == "# khuôn cảnh\n"


def test_soat_kenh_ghi_so_va_mo_cai_tien(tmp_path, monkeypatch):
    from core import bat_thuong
    goc = str(tmp_path)
    monkeypatch.setattr(bat_thuong, "tin_hieu_kenh", lambda g, k: [])
    monkeypatch.setattr(bat_thuong, "soat_bia_song", lambda *a, **k: [])
    monkeypatch.setattr(ss, "mau_canh", lambda g, k: {"luot": "0001", "canh": [{"so": 1, "tep": "a", "loi_doc": "",
                                                                                "ai": "", "prompt": ""}] * 5})
    monkeypatch.setattr(ss, "cham_mot", lambda *a, **k: _m(3))
    monkeypatch.setattr(ss, "doc_dao", lambda g, k, thu=False: {"n": 10, "ti_le_chep": 10.0})
    goi_ct = []
    monkeypatch.setattr(ss, "cai_tien_anh", lambda *a, **k: goi_ct.append(1) or {"ket": "khong_dat"})
    kq = ss.soat_kenh(goc, "K", goi=lambda *a, **k: "", ve=lambda *a: [])
    assert kq["anh"]["noi_dung_hong"] == 100.0 and kq["anh_xau"] and goi_ct == [1]
    assert len(ss.doc_lich_su(goc, "K")) == 1 and ss.can_chay(goc, "K")[0] is False
    kq = ss.soat_kenh(goc, "K", thu=True, goi=lambda *a, **k: "")
    assert kq["cai_tien"]["ket"] == "se_chay" and len(ss.doc_lich_su(goc, "K")) == 1   # chạy thử không ghi


def test_mau_canh_lay_deu(tmp_path):
    goc = str(tmp_path)
    tm = os.path.join(goc, "PROJECTS", "AUTO", "K", "0003")
    os.makedirs(os.path.join(tm, "5-anh"))
    with open(os.path.join(tm, "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump([{"scene_id": i, "srt_text": "s{0}".format(i), "img_prompt": "p"} for i in range(1, 61)], f)
    for i in range(1, 61):
        open(os.path.join(tm, "5-anh", "{0}.png".format(i)), "wb").close()
    m = ss.mau_canh(goc, "K", 20)
    assert m["luot"] == "0003" and len(m["canh"]) == 20 and m["canh"][0]["so"] == 1 and m["canh"][1]["so"] == 4
