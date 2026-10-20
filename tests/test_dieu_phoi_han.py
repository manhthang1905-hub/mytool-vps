"""Điều phối xếp làn theo HẠN khe đăng (20/10/2026): kênh mới trước, hạn sớm trước, lượt dở thắng khi cùng khung hạn;
`xep_lich.han_san_xuat`; chia trần máy chủ cho các lượt đang chạy (`auto_khau._suat_chia_luot`). Không mạng, `tmp_path`."""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

from core import auto, auto_khau, dieu_phoi, khe, xep_lich
from core.kenh import doc_kenh
from tests.test_dieu_phoi import _ke_hoach, _kenh, _vps

BAY = _dt.datetime(2026, 10, 20, 9, 0)


def _c(ma, gio=None, **them):
    c = {"ma": ma, "chay": True, "diem": -1.0}
    if gio is not None:
        c["han_ts"] = (BAY + _dt.timedelta(hours=gio)).timestamp()
    c.update(them)
    return c


def _xep(*cac):
    return [c["ma"] for c in sorted(cac, key=lambda c: dieu_phoi.khoa_xep(c, BAY))]


def test_kenh_moi_truoc_roi_han_som_truoc():
    assert _xep(_c("A", 30), _c("B", 5), _c("M", 20, kenh_moi=True)) == ["M", "B", "A"]


def test_luot_do_chi_thang_khi_cung_khung_han():
    # cùng khung 3 giờ → lượt dở trước; lượt dở hạn xa (30h) không chen trước kênh hạn gần (5h)
    assert _xep(_c("A", 4.5), _c("D", 5.5, luot_do=True, diem=-1000.0)) == ["D", "A"]
    assert _xep(_c("A", 5), _c("D", 30, luot_do=True, diem=-1000.0)) == ["A", "D"]


def test_khong_phat_luon_sau_va_khong_han_cuoi_nhom():
    assert _xep(_c("X", 1, khong_phat=True), _c("Y"), _c("Z", 40)) == ["Z", "Y", "X"]


def test_han_san_xuat_bo_qua_khe_da_co_va_goi_cho_lich(tmp_path):
    goc = str(tmp_path)
    _vps(goc)
    _kenh(goc, "K1", nhip_dang='"20:00"')
    k = doc_kenh(goc, "K1")
    h = xep_lich.han_san_xuat(goc, "K1", k, bay_gio=BAY)
    assert h["chua_co_video"] is True and h["han"] == _dt.datetime(2026, 10, 20, 20, 0)
    # 20/10 đã có gói hẹn; một gói "Sẵn sàng" chưa lịch sẽ lấp 21/10 → hạn chưa phủ là 22/10 20:00
    _ke_hoach(goc, "K1", {"Mã gói": "K1-1", "Ngày đăng": "20/10/2026", "Giờ đăng": "20:00", "Sẵn sàng": "x"},
              {"Mã gói": "K1-2", "Sẵn sàng": "x"})
    h = xep_lich.han_san_xuat(goc, "K1", k, bay_gio=BAY)
    assert h["chua_co_video"] is False and h["han"] == _dt.datetime(2026, 10, 22, 20, 0)


def test_nhip_sinh_kenh_moi_truoc_luot_do_han_xa(tmp_path):
    goc = str(tmp_path)
    _vps(goc, lan_api=1)
    _kenh(goc, "A", nhip_dang='"20:00"')
    _kenh(goc, "M", nhip_dang='"20:00"')
    # A: có lượt dở + kho đầy tới 23/10 (hạn xa); M: kênh mới chưa có video
    _ke_hoach(goc, "A", *[{"Mã gói": "A-{0}".format(i), "Ngày đăng": "{0}/10/2026".format(19 + i),
                           "Giờ đăng": "20:00", "Sẵn sàng": "x"} for i in range(1, 5)])
    luot = auto.moi_luot(goc, "A", "0001", {"link": "x", "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)
    so = os.path.join(goc, "CHANNEL", "A", "tu-chay")
    os.makedirs(so, exist_ok=True)
    with open(os.path.join(so, "2026-10-20.json"), "w", encoding="utf-8") as tep:
        json.dump({"ngay": "2026-10-20", "kenh": "A", "nhat_ky": [],
                   "runs": [{"ma_luot": "0001", "san_xuat": {"da_chay": True}}]}, tep)
    sinh = []
    ra = dieu_phoi.nhip(goc, bay_gio=BAY, ram=10.0, dia_gb=30.0,
                        sinh=lambda g, ma: sinh.append(ma) or 1000 + len(sinh), log=lambda d: None)
    assert sinh == ["M"]
    ly = {c["ma"]: c["ly_do"] for c in ra["kenh"]}
    assert "kênh mới" in ly["M"] and "lượt dở" in ly["A"] and "hạn khe 24/10 20:00" in ly["A"]


def test_suat_chia_luot_theo_so_lan_dang_lam(tmp_path):
    goc = str(tmp_path)
    _vps(goc, lan_api=4, tran_api_tong=120)

    class _Bc:
        pass

    bc = _Bc()
    bc.goc = goc
    assert auto_khau._suat_chia_luot(bc, "image", 186) == 186          # không lượt điều phối → như cũ
    os.makedirs(khe.duong_thu_muc_khe(goc), exist_ok=True)
    for i in range(4):
        with open(khe.duong_khoa_api(goc, i), "w", encoding="utf-8") as tep:
            json.dump({"pid": os.getpid(), "loai": "api", "kenh": "K{0}".format(i), "bat_dau": time.time()}, tep)
    assert auto_khau._suat_chia_luot(bc, "image", 186) == 30            # 120 suất toàn máy / 4 lượt
    assert auto_khau._suat_chia_luot(bc, "video", 832) == 30
    assert auto_khau._suat_chia_luot(bc, "tts", 3) == 3                 # sàn 4 nhưng không quá trần máy chủ
    assert auto_khau._suat_chia_luot(bc, "image", 10) == 4              # ceil(10/4)=3 < sàn 4
