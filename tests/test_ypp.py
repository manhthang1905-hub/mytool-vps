import datetime as dt
import json
import os

from core import ypp

NOW = dt.datetime(2026, 10, 6, 12, 0)


def _kenh(goc, k, dong):
    d = goc / "CHANNEL" / k / "chi-so"
    d.mkdir(parents=True, exist_ok=True)
    (d / "kenh-theo-ngay.csv").write_text(
        "﻿Lúc chụp,Lượt xem,Giờ xem,Đăng ký,Lượt hiển thị,Tỷ lệ bấm\n" +
        "".join('"{0}","1","{1}","{2}","",""\n'.format(t, g, s) for t, g, s in dong), encoding="utf-8")


def _chuoi(n, gio0, dg, dk0, ddk, ket=NOW):
    return [((ket - dt.timedelta(days=n - 1 - i)).strftime("%Y-%m-%d %H:%M"), gio0 + dg * i, dk0 + ddk * i) for i in range(n)]


def _khai(goc, *ks):
    (goc / "vm").mkdir(exist_ok=True)
    (goc / "vm" / "cai-dat-tool.json").write_text(json.dumps({"kenh": {k: {} for k in ks}}), encoding="utf-8")


def test_chua_du_so(tmp_path):
    _kenh(tmp_path, "A", _chuoi(2, 1, 1, 1, 1))
    assert ypp.du_bao(str(tmp_path), "A", NOW)["trang_thai"] == "chua_du_so"
    assert ypp.du_bao(str(tmp_path), "khong-co", NOW)["trang_thai"] == "chua_du_so"


def test_toc_do_eta_dang_len(tmp_path):
    _kenh(tmp_path, "A", _chuoi(8, 100, 10, 10, 2))
    r = ypp.du_bao(str(tmp_path), "A", NOW)
    assert abs(r["toc_gio"] - 10) < 1e-6 and abs(r["toc_dk"] - 2) < 1e-6
    assert r["gio"] == 170 and r["dang_ky"] == 24
    assert abs(r["ngay_gio"] - 383) < 1e-6 and abs(r["ngay_dk"] - 488) < 1e-6
    assert r["trang_thai"] == "dang_len"
    assert r["ngay_du_kien"] == (NOW + dt.timedelta(days=488)).strftime("%Y-%m-%d")


def test_cham_khi_khong_tang(tmp_path):
    _kenh(tmp_path, "A", _chuoi(5, 50, 0, 3, 0))
    r = ypp.du_bao(str(tmp_path), "A", NOW)
    assert r["trang_thai"] == "cham" and r["ngay_toi"] is None


def test_bo_chenh_am_va_ngoai_lai(tmp_path):
    ch = _chuoi(8, 100, 10, 10, 1)
    ch[4] = (ch[4][0], 5000, ch[4][2])  # nhảy rồi tụt: một chênh khổng lồ + một chênh âm
    _kenh(tmp_path, "A", ch)
    r = ypp.du_bao(str(tmp_path), "A", NOW)
    assert abs(r["toc_gio"] - 10) < 1e-6


def test_gan_va_dat(tmp_path):
    _kenh(tmp_path, "G", _chuoi(5, 3900, 20, 990, 2))
    _kenh(tmp_path, "D", _chuoi(5, 4100, 5, 1010, 1))
    assert ypp.du_bao(str(tmp_path), "G", NOW)["trang_thai"] == "gan"
    r = ypp.du_bao(str(tmp_path), "D", NOW)
    assert r["trang_thai"] == "dat" and r["ngay_toi"] == 0


def test_dat_can_ca_hai(tmp_path):
    _kenh(tmp_path, "A", _chuoi(5, 4100, 5, 10, 0))
    assert ypp.du_bao(str(tmp_path), "A", NOW)["trang_thai"] == "cham"


def test_canh_bao_dedupe_va_chi_noi_them(tmp_path):
    goc = tmp_path
    _khai(goc, "G", "D", "A")
    _kenh(goc, "G", _chuoi(5, 3900, 20, 990, 2))
    _kenh(goc, "D", _chuoi(5, 4100, 5, 1010, 1))
    _kenh(goc, "A", _chuoi(5, 1, 1, 1, 1))
    nen = str(tmp_path / "nen")
    tep = goc / "workspace" / "loi-chay-max.md"
    tep.parent.mkdir()
    tep.write_text("# Nhật ký\n- cũ", encoding="utf-8")  # không xuống dòng cuối
    ds = ypp.canh_bao(str(goc), nen, NOW)
    assert len(ds) == 2 and not os.path.exists(nen)  # thuần đọc
    assert any("**khan** · kênh D" in x for x in ds) and any("**thuong** · kênh G" in x for x in ds)
    assert all(x.startswith("- [2026-10-06 12:00] **") for x in ds)
    ypp.ghi_canh_bao(str(goc), nen, bay_gio=NOW)
    nd = tep.read_text(encoding="utf-8")
    assert nd.startswith("# Nhật ký\n- cũ\n- [2026-10-06 12:00]") and nd.count("\n- [") == 2
    assert ypp.ghi_canh_bao(str(goc), nen, bay_gio=NOW) == []  # đã báo: không lặp
    assert tep.read_text(encoding="utf-8") == nd
    # G từ gan lên dat: báo lại một dòng khan
    _kenh(goc, "G", _chuoi(5, 4100, 5, 1010, 1))
    ds = ypp.ghi_canh_bao(str(goc), nen, bay_gio=NOW)
    assert len(ds) == 1 and "**khan** · kênh G" in ds[0]
    assert tep.read_text(encoding="utf-8").startswith(nd)


def test_ky_nang_d07(tmp_path):
    from core import ky_nang
    k = ky_nang.theo_ma("D07")
    _kenh(tmp_path, "D", _chuoi(5, 4100, 5, 1010, 1))
    _kenh(tmp_path, "A", _chuoi(5, 100, 10, 10, 2))
    _kenh(tmp_path, "T", _chuoi(1, 1, 1, 1, 1))
    assert k.kiem(str(tmp_path), "D")[0] == ky_nang.DAT
    assert k.kiem(str(tmp_path), "A")[0] == ky_nang.CHO and "ETA" in k.kiem(str(tmp_path), "A")[1]
    assert k.kiem(str(tmp_path), "T")[0] == ky_nang.THIEU
