"""Thử nâng nhịp đăng có rào (`core/nhip_thu`, 22/10/2026)."""
import datetime as dt
import os

from core import nhip_thu as nt


def _bang(goc, kenh, dong):
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "bang-tom-tat.csv"), "w", encoding="utf-8-sig") as f:
        f.write("Mã video,Ngày đăng,Lượt xem\n")
        for vid, ngay, xem in dong:
            f.write("{0},{1},{2}\n".format(vid, ngay, xem))


def _gia_ghi(monkeypatch):
    ghi = {}
    from core import trung_tam
    monkeypatch.setattr(trung_tam, "ghi_cai_kenh", lambda goc, kenh, **kw: ghi.setdefault(kenh, []).append(kw))
    monkeypatch.setattr(nt, "_kenh_yaml", lambda goc, kenh: {"video_moi_ngay": 1})
    return ghi


def test_tut_qua_nguong_thi_tra_nhip_cu(tmp_path, monkeypatch):
    goc = str(tmp_path)
    ghi = _gia_ghi(monkeypatch)
    bd = dt.date(2026, 10, 22)
    _bang(goc, "TLx-T7", [("A%d" % i, (bd - dt.timedelta(days=i + 1)).isoformat(), 1000) for i in range(6)])
    nt.bat_dau(goc, "TLx-T7", "05:00, 20:00", 2, bay_gio=bd)
    assert ghi["TLx-T7"][-1]["video_moi_ngay"] == 2
    _bang(goc, "TLx-T7", [("B%d" % i, (bd + dt.timedelta(days=i)).isoformat(), 500) for i in range(6)])
    assert nt.danh_gia(goc, bd + dt.timedelta(days=3))[0]["ket"] == "dang_thu"
    kq = nt.danh_gia(goc, bd + dt.timedelta(days=9))
    assert kq[0]["ket"] == "tra_lai" and ghi["TLx-T7"][-1]["video_moi_ngay"] == 1


def test_khong_tut_thi_giu(tmp_path, monkeypatch):
    goc = str(tmp_path)
    ghi = _gia_ghi(monkeypatch)
    bd = dt.date(2026, 10, 22)
    _bang(goc, "TLx-T7", [("A%d" % i, (bd - dt.timedelta(days=i + 1)).isoformat(), 1000) for i in range(6)])
    nt.bat_dau(goc, "TLx-T7", "05:00, 20:00", 2, bay_gio=bd)
    _bang(goc, "TLx-T7", [("B%d" % i, (bd + dt.timedelta(days=i)).isoformat(), 900) for i in range(8)])
    kq = nt.danh_gia(goc, bd + dt.timedelta(days=9))
    assert kq[0]["ket"] == "dat" and ghi["TLx-T7"][-1]["video_moi_ngay"] == 2
