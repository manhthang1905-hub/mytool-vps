"""Test bộ điều phối đăng nhập Gmail kênh (core/dang_nhap_gmail.py) — không mở Chrome, không gọi mạng."""
import json
import sys

import pytest

from core import dang_nhap_gmail as dn

# Giá trị GIẢ chỉ dùng trong test — không phải tài khoản thật.
MK_GIA = "gia-tri-test-khong-that"
TOTP_GIA = "AAAABBBBCCCCDDDD"


@pytest.fixture
def goc(tmp_path, monkeypatch):
    # Cây giả: <goc>/vm (kho), <goc>/../<MÃ>/<MÃ>.exe (Chrome Portable)
    goc = tmp_path / "MyTool"
    (goc / "vm").mkdir(parents=True)
    (goc / "vm" / "kho_bi_mat.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(dn, "chrome_dang_chay", lambda exe: False)
    return str(goc)


def _kho(monkeypatch, tk):
    fake = type(sys)("kho_bi_mat")
    fake.tai_khoan = lambda ma: tk
    monkeypatch.setitem(sys.modules, "kho_bi_mat", fake)


def _chay_gia(stdout_dong_cuoi, ghi_argv=None):
    def chay(argv, dau_vao, cwd, timeout):
        if ghi_argv is not None:
            ghi_argv.append((argv, dau_vao))
        return 0, "log tien trinh\n" + stdout_dong_cuoi + "\n"
    return chay


def test_thieu_tai_khoan_khong_chay_gi(goc, monkeypatch):
    _kho(monkeypatch, {})
    goi = []
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=_chay_gia("{}", goi))
    assert kq["ket_qua"] == "thieu_tai_khoan"
    assert goi == []


def test_chrome_kenh_dang_mo_thi_chan(goc, monkeypatch):
    _kho(monkeypatch, {"email": "kenh@example.test", "mat_khau": MK_GIA, "totp": ""})
    monkeypatch.setattr(dn, "chrome_dang_chay", lambda exe: True)
    goi = []
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=_chay_gia("{}", goi))
    assert kq["ket_qua"] == "chrome_dang_chay"
    assert goi == []


def test_thanh_cong_mat_khau_di_qua_stdin_khong_qua_argv(goc, monkeypatch):
    _kho(monkeypatch, {"email": "KENH@example.test", "mat_khau": MK_GIA, "totp": TOTP_GIA})
    goi = []
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=_chay_gia(
        json.dumps({"ket_qua": "ok", "ly_do": "xong", "email_that": "kenh@example.test"}), goi))
    assert kq == {"ket_qua": "ok", "ly_do": "xong", "email_that": "kenh@example.test"}
    argv, dau_vao = goi[0]
    assert MK_GIA not in " ".join(argv)          # bí mật KHÔNG lên dòng lệnh
    assert json.loads(dau_vao)["mat_khau"] == MK_GIA
    assert "--thu-muc-profile" in argv and "--khong-cookie" in argv
    assert argv[argv.index("--thu-muc-profile") + 1].replace("\\", "/").endswith("TL9-T7/Data/profile") \
        or "Data" in argv[argv.index("--thu-muc-profile") + 1]


def test_sai_danh_tinh_bi_chan_o_day(goc, monkeypatch):
    _kho(monkeypatch, {"email": "kenh@example.test", "mat_khau": MK_GIA, "totp": ""})
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=_chay_gia(
        json.dumps({"ket_qua": "ok", "ly_do": "xong", "email_that": "khac@example.test"})))
    assert kq["ket_qua"] == "sai_danh_tinh"


def test_captcha_chi_bao_nguoi(goc, monkeypatch):
    _kho(monkeypatch, {"email": "kenh@example.test", "mat_khau": MK_GIA, "totp": ""})
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=_chay_gia(
        json.dumps({"ket_qua": "captcha", "ly_do": "Google đòi CAPTCHA"})))
    assert kq["ket_qua"] == "captcha"


def test_khong_co_json_thi_hong(goc, monkeypatch):
    _kho(monkeypatch, {"email": "kenh@example.test", "mat_khau": MK_GIA, "totp": ""})
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=lambda a, d, c, t: (1, "loi tro\n"))
    assert kq["ket_qua"] == "hong"


def test_ket_qua_khong_chua_mat_khau_hay_cookie(goc, monkeypatch):
    _kho(monkeypatch, {"email": "kenh@example.test", "mat_khau": MK_GIA, "totp": TOTP_GIA})
    kq = dn.dang_nhap_kenh(goc, "TL9-T7", chay=_chay_gia(
        json.dumps({"ket_qua": "ok", "ly_do": "xong", "email_that": "kenh@example.test",
                    "cookies": [{"name": "SID", "value": "bi-mat"}]})))
    texte = json.dumps(kq)
    assert MK_GIA not in texte and TOTP_GIA not in texte and "bi-mat" not in texte
