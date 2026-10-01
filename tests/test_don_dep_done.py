"""Luật BỐN `core/don_dep.py` (dọn media nặng trong gói DONE) + van ổ / dọn mạnh
`core/don_dep_mo_rong.py` + trần theo ổ đĩa `core/cong_suat.py` (01/10/2026).

Toàn bộ trong `tmp_path`, không mạng, không đụng PROJECTS/DONE thật.
"""

from __future__ import annotations

import datetime
import json
import os
import time

from core import cong_suat, don_dep, don_dep_mo_rong, ke_hoach_dang
from core.auto import MA_KHAU, TEP_TRANG_THAI, XONG, duong_luot

KENH = "K1"
MA = "K1-0001"
BAY_GIO = datetime.datetime(2026, 10, 5, 12, 0)
LICH_CU = "02/10/2026 12:00"     # 72 giờ trước BAY_GIO
LICH_MOI = "04/10/2026 20:00"    # 16 giờ trước BAY_GIO


def _ghi(duong, chu="x"):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _nhi_phan(duong, so_byte):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "wb") as tep:
        tep.write(b"\x00" * so_byte)


def _kenh(goc, **khoa):
    done = os.path.join(goc, "DONE", KENH)
    os.makedirs(done, exist_ok=True)
    d = os.path.join(goc, "CHANNEL", KENH)
    os.makedirs(d, exist_ok=True)
    cai = {"ma": KENH, "tu_don": "true", "thu_muc_done": done.replace("\\", "/")}
    cai.update(khoa)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join("{0}: {1}".format(k, v) for k, v in cai.items()) + "\n")
    return done


def _goi(done, ma=MA, mp4=5000, moc=None):
    g = os.path.join(done, ma)
    _nhi_phan(os.path.join(g, "8-video.mp4"), mp4)
    _ghi(os.path.join(g, "3-phu-de.srt"))
    _ghi(os.path.join(g, "1-binh-luan.txt"))
    _nhi_phan(os.path.join(g, "CHON-thumb_001.jpg"), 300)
    _ghi(os.path.join(g, "qa-ket-qua.json"), "{}")
    if moc is not None:
        for t in os.listdir(g):
            os.utime(os.path.join(g, t), (moc, moc))
    return g


def _so(goc, **muc_theo_ma):
    d = os.path.join(goc, "vm", "logs")
    os.makedirs(d, exist_ok=True)
    du = {"{0}/{1}".format(KENH, ma): m for ma, m in muc_theo_ma.items()}
    with open(os.path.join(d, "so-video-id.json"), "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False)


def _da_dang(lich=LICH_CU, hau_kiem="ok: thời lượng 839s khớp tệp 838.9s", **them):
    m = {"video_id": "abc", "trang_thai": "xac-nhan", "lich": lich,
         "tai_xong_luc": "2026-10-01 00:00:00", "hau_kiem": hau_kiem}
    m.update(them)
    return m


def _luot_xong(goc, luot="0001", xong=True):
    d = duong_luot(goc, KENH, luot)
    tt = XONG if xong else "cho"
    _ghi(os.path.join(d, TEP_TRANG_THAI), json.dumps({
        "ma_kenh": KENH, "ma_luot": luot, "dau_vao": {}, "tao_luc": 0.0,
        "khau": {m: {"ma": m, "trang_thai": tt, "so_lan": 1, "loi": "", "bat_dau": 0.0,
                     "ket_thuc": 0.0, "ghi_chu": {}} for m in MA_KHAU}}))
    _ghi(os.path.join(d, "3-phu-de.srt"))
    _nhi_phan(os.path.join(d, "5-anh", "a.png"), 7000)
    return d


def _moc_cu():
    return datetime.datetime(2026, 9, 30, 12, 0).timestamp()


# ── Luật BỐN ─────────────────────────────────────────────────────────────────


def test_goi_da_dang_xac_nhan_hau_kiem_qua_48h_chi_xoa_media(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    g = _goi(done, moc=_moc_cu())
    _so(goc, **{MA: _da_dang()})
    ket = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO)
    assert not os.path.exists(os.path.join(g, "8-video.mp4"))
    for giu in ("3-phu-de.srt", "1-binh-luan.txt", "CHON-thumb_001.jpg", "qa-ket-qua.json"):
        assert os.path.isfile(os.path.join(g, giu)), giu
    assert ket["tong_bytes"] == 5000
    assert os.path.isfile(os.path.join(g, don_dep.TEN_MARKER))
    log = open(os.path.join(goc, "CHANNEL", KENH, "tu-chay", don_dep.TEN_LOG), encoding="utf-8").read()
    assert MA in log and "DONE" in log


def test_chua_qua_48h_cong_khai_khong_dung(tmp_path):
    goc = str(tmp_path)
    g = _goi(_kenh(goc), moc=_moc_cu())
    _so(goc, **{MA: _da_dang(lich=LICH_MOI)})
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO) == []
    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO)
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))


def test_thieu_hau_kiem_hoac_chua_xac_nhan_khong_dung(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    for ma in ("K1-0001", "K1-0002", "K1-0003", "K1-0004", "K1-0005"):
        _goi(done, ma=ma, moc=_moc_cu())
    _so(goc, **{"K1-0001": _da_dang(hau_kiem=""),
                "K1-0002": _da_dang(hau_kiem="lech: 839s ≠ 700s"),
                "K1-0003": _da_dang(trang_thai="da-len-lich"),
                "K1-0004": {"trang_thai": "dang-tai", "lich": LICH_CU}})
    # K1-0005: không có trong sổ (chưa đăng)
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO) == []


def test_video_dung_lai_sau_luc_tai_khong_dung(tmp_path):
    goc = str(tmp_path)
    g = _goi(_kenh(goc))  # mtime = bây giờ thật (> tai_xong_luc 01/10)
    _so(goc, **{MA: _da_dang()})
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=datetime.datetime.now()
                                 + datetime.timedelta(days=30)) == []
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))


def test_goi_bo_chi_xoa_sau_7_ngay(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    cot = list(ke_hoach_dang.COT)
    d = {t: "" for t in cot}
    d.update({"Mã gói": MA, "Ghi chú": "Bỏ, không đăng — trùng nội dung"})
    ke_hoach_dang.luu_bang(goc, KENH, [[d[t] for t in cot]], cot)
    _so(goc)
    moc = datetime.datetime(2026, 10, 1, 12, 0).timestamp()
    g = _goi(done, moc=moc)
    os.utime(g, (moc, moc))
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=datetime.datetime(2026, 10, 5, 12)) == []
    u = don_dep.ung_vien_done(goc, KENH, bay_gio=datetime.datetime(2026, 10, 9, 12))
    assert [x["ma_goi"] for x in u] == [MA] and "Bỏ" in u[0]["ly_do"]


def test_hardlink_chi_tinh_giai_phong_khi_xoa_het_lien_ket(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    g = _goi(done, moc=_moc_cu())
    luot = _luot_xong(goc, "0001", xong=True)
    os.link(os.path.join(g, "8-video.mp4"), os.path.join(luot, "8-video.mp4"))
    assert don_dep.byte_giai_phong([os.path.join(g, "8-video.mp4")]) == 0
    _so(goc, **{MA: _da_dang()})
    u = don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO)
    assert len(u) == 1 and u[0]["bytes"] == 5000
    ket = don_dep.don_done(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO)
    assert ket["tong_bytes"] == 5000
    assert not os.path.exists(os.path.join(luot, "8-video.mp4"))
    assert os.path.isfile(os.path.join(luot, "3-phu-de.srt"))


def test_hardlink_luot_chua_xong_khong_dung_ban_trong_luot(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    g = _goi(done, moc=_moc_cu())
    luot = _luot_xong(goc, "0001", xong=False)
    os.link(os.path.join(g, "8-video.mp4"), os.path.join(luot, "8-video.mp4"))
    _so(goc, **{MA: _da_dang()})
    ket = don_dep.don_done(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO)
    assert os.path.isfile(os.path.join(luot, "8-video.mp4"))
    assert ket["tong_bytes"] == 0  # còn một liên kết sống → chưa lấy lại byte nào


def test_dang_tai_len_thi_khong_dung(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    _goi(done, moc=_moc_cu())
    _goi(done, ma="K1-0002", moc=_moc_cu())
    _so(goc, **{MA: _da_dang(), "K1-0002": _da_dang()})
    _ghi(os.path.join(goc, "vm", "logs", "dang-dodang.json"), json.dumps({"kenh": KENH, "ma": MA}))
    assert [u["ma_goi"] for u in don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO)] == ["K1-0002"]
    _ghi(os.path.join(goc, "vm", "logs", "dang-dodang.json"), "hỏng")
    assert don_dep.ung_vien_done(goc, KENH, bay_gio=BAY_GIO) == []


def test_luat_mot_khong_con_xoa_ca_goi_done(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    g = _goi(done)
    luot = _luot_xong(goc, "0001")
    cot = list(ke_hoach_dang.COT)
    d = {t: "" for t in cot}
    d.update({"Mã gói": MA, "Ngày đăng": "01/10/2026", "Giờ đăng": "23:00",
              "Trạng thái đăng": "ĐÃ ĐĂNG"})
    ke_hoach_dang.luu_bang(goc, KENH, [[d[t] for t in cot]], cot)
    u = don_dep.ung_vien_don(goc, KENH, bay_gio=BAY_GIO)
    assert u and os.path.join(luot, "5-anh") in u[0]["duong"]
    assert all(not p.startswith(done) for x in u for p in x["duong"])
    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO)  # sổ máy đăng trống
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))
    assert os.path.isfile(os.path.join(g, "3-phu-de.srt"))


def test_don_khan_dung_ca_luat_bon(tmp_path):
    goc = str(tmp_path)
    g = _goi(_kenh(goc), moc=_moc_cu())
    _so(goc, **{MA: _da_dang()})
    so = iter([1.0, 50.0])
    ket = don_dep.don_khan(goc, [KENH], nguong_gb=6.0, bay_gio=BAY_GIO,
                           con_trong_gb_fn=lambda _g: next(so))
    assert ket["da_giai_phong_bytes"] == 5000
    assert not os.path.exists(os.path.join(g, "8-video.mp4"))


# ── Van ổ + dọn mạnh ─────────────────────────────────────────────────────────


def test_van_o_ba_muc_va_tu_mo_lai(tmp_path):
    goc = str(tmp_path)
    goi = []

    def manh(g, ds, bay_gio=None):
        goi.append(1)
        return {"tong_bytes": 123, "theo_muc": {"done": 123}}

    t = datetime.datetime(2026, 10, 1, 12, 0)
    o = don_dep_mo_rong.van_o(goc, [KENH], con_trong_gb=20.0, bay_gio=t, don_manh_fn=manh)
    assert o["muc"] == "ok" and o["duoc_mo_moi"] and not goi
    o = don_dep_mo_rong.van_o(goc, [KENH], con_trong_gb=10.0, bay_gio=t, don_manh_fn=manh)
    assert o["muc"] == "chan" and not o["duoc_mo_moi"] and o["duoc_lam_do"] and not goi
    o = don_dep_mo_rong.van_o(goc, [KENH], con_trong_gb=5.0, bay_gio=t, don_manh_fn=manh)
    assert o["muc"] == "khan" and not o["duoc_lam_do"] and goi == [1]
    assert o["don_manh"]["tong_bytes"] == 123
    # 5 phút sau vẫn khẩn → không dọn mạnh lại (giãn 20')
    o = don_dep_mo_rong.van_o(goc, [KENH], con_trong_gb=5.0,
                              bay_gio=t + datetime.timedelta(minutes=5), don_manh_fn=manh)
    assert goi == [1]
    o = don_dep_mo_rong.van_o(goc, [KENH], con_trong_gb=30.0,
                              bay_gio=t + datetime.timedelta(minutes=30), don_manh_fn=manh)
    assert o["muc"] == "ok" and o["duoc_mo_moi"] and o.get("mo_lai_luc")
    assert don_dep_mo_rong.doc_trang_thai_o(goc)["muc"] == "ok"


def test_van_o_khong_do_duoc_thi_khong_chan(tmp_path):
    def hong(_g):
        raise OSError("x")
    o = don_dep_mo_rong.van_o(str(tmp_path), [], con_trong_gb_fn=hong)
    assert o["muc"] == "khong_ro" and o["duoc_mo_moi"]


def test_don_manh_dung_pham_vi(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc)
    bay_gio = datetime.datetime.now()
    cu = time.time() - 20 * 86400
    # lượt đã bàn giao (gói có mp4 trong DONE) → xoá nặng; lượt chưa xong → không đụng
    l1 = _luot_xong(goc, "0001", xong=True)
    os.utime(os.path.join(l1, TEP_TRANG_THAI), (cu, cu))
    _goi(done, ma="K1-0001")
    l2 = _luot_xong(goc, "0002", xong=False)
    os.utime(os.path.join(l2, TEP_TRANG_THAI), (cu, cu))
    # ban-va cũ: giữ GHI-CHU.md; ban-va mới: giữ hết
    bv_cu = os.path.join(goc, "workspace", "ban-va", "2026-09-01-x")
    _ghi(os.path.join(bv_cu, "GHI-CHU.md"))
    _nhi_phan(os.path.join(bv_cu, "core", "a.py"), 100)
    for r, _d, fs in os.walk(bv_cu):
        for f in fs:
            os.utime(os.path.join(r, f), (cu, cu))
    bv_moi = os.path.join(goc, "workspace", "ban-va", "2026-10-01-y")
    _nhi_phan(os.path.join(bv_moi, "core", "b.py"), 100)
    bia = os.path.join(goc, "workspace", "thu-bia-tl3")
    _nhi_phan(os.path.join(bia, "a.png"), 100)
    os.utime(os.path.join(bia, "a.png"), (cu, cu))
    py = os.path.join(goc, "workspace", "pytest-final")
    _nhi_phan(os.path.join(py, "t.txt"), 100)
    os.utime(os.path.join(py, "t.txt"), (cu, cu))

    ket = don_dep_mo_rong.don_manh(goc, [KENH], bay_gio=bay_gio)
    assert not os.path.exists(os.path.join(l1, "5-anh"))
    assert os.path.isfile(os.path.join(l1, "3-phu-de.srt"))
    assert os.path.isdir(os.path.join(l2, "5-anh"))
    assert os.path.isfile(os.path.join(bv_cu, "GHI-CHU.md"))
    assert not os.path.exists(os.path.join(bv_cu, "core", "a.py"))
    assert os.path.isfile(os.path.join(bv_moi, "core", "b.py"))
    assert not os.path.exists(bia) and not os.path.exists(py)
    assert ket["theo_muc"]["projects_ban_giao"] == 7000
    assert ket["tong_bytes"] >= 7000 + 300


# ── Trần theo ổ đĩa ──────────────────────────────────────────────────────────


def test_tran_o_dia_chua_do_duoc_thi_none(tmp_path):
    o = cong_suat.tran_theo_o_dia(str(tmp_path), con_trong_gb=30.0)
    assert o["tran_video_ngay"] is None


def test_tran_o_dia_tinh_dung_cong_thuc(tmp_path):
    goc = str(tmp_path)
    done = _kenh(goc, tu_chay="true", giu_toi_da_luot=1)
    mb = 1024 ** 2
    g = _goi(done, mp4=20 * mb)
    _so(goc, **{MA: _da_dang(lich="01/01/2099 00:00")})
    luot = _luot_xong(goc, "0002")
    _nhi_phan(os.path.join(luot, "8-video.mp4"), 60 * mb)
    o = cong_suat.tran_theo_o_dia(goc, con_trong_gb=20.0)
    assert o["mau_luot"] == 1 and o["mau_video"] == 1 and o["tran_video_ngay"] is not None
    g_luot, g_video = o["gb_moi_luot"], o["gb_moi_video_done"]
    assert abs(g_video - 20 / 1024) < 0.01 and abs(g_luot - 60 / 1024) < 0.01
    # trần = (ngân sách − cố định) / (GB video × ngày DONE) + trùng/ngày DONE
    ngan_sach = 20.0 + o["dang_dung_gb"] - 12.0
    co_dinh = 1 * (1 + 1) * (60 * mb + 7000) / 1024 ** 3
    du_kien = (ngan_sach - co_dinh) / (g_video * o["ngay_nam_done"]) + 1 / o["ngay_nam_done"]
    assert abs(o["tran_video_ngay"] - du_kien) < 0.6
    assert os.path.isfile(os.path.join(g, "8-video.mp4"))  # hàm chỉ đọc


def test_nhip_dieu_phoi_o_duoi_12gb_khong_sinh_luot_moi(tmp_path):
    from core import dieu_phoi

    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vps.json"), "{}")
    _ghi(os.path.join(goc, "workspace", "cai-dat.json"), json.dumps({"dieu_phoi": True, "lan_api": 2}))
    _ghi(os.path.join(goc, "CHANNEL", "K2", "kenh.yaml"), "\n".join([
        'ma: "K2"', 'ngon_ngu: "ja"', 'engine: "veo3"', "phut_muc_tieu: 10", "tu_chay: true",
        "tu_duyet: true", "ngan_sach_ngay: 5000000", 'nhip_dang: "12:00, 20:00"',
        "video_toi_da_ngay: 4"]) + "\n")
    bay_gio = datetime.datetime(2026, 9, 29, 14, 0)
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=bay_gio, ram=10.0, dia_gb=10.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1, log=lambda d: None)
    assert sinh == [] and "ổ đĩa" in ra["chan"] and ra["o_dia"]["muc"] == "chan"
    ra = dieu_phoi.nhip(goc, bay_gio=bay_gio, ram=10.0, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1, log=lambda d: None)
    assert sinh == ["K2"] and ra["o_dia"]["muc"] == "ok"


def test_cong_suat_hien_tai_lay_o_dia_lam_nut_that(tmp_path, monkeypatch):
    monkeypatch.setattr(cong_suat, "tran_theo_o_dia",
                        lambda goc, so_kenh=None: {"tran_video_ngay": 0.5, "gb_moi_video": 1.1})
    cs = cong_suat.cong_suat_hien_tai(str(tmp_path))
    assert cs["nut_that"] == "ổ đĩa" and cs["tran_video_ngay_o_dia"] == 0.5
    assert "ổ:" in cong_suat.cau_mot_dong(cs)
    from core.giam_doc import tong
    assert tong.tran_may(cs) == 0.5
