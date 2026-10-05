"""05/10: máy đăng tự ép Studio về tiếng Việt (cookie PREF hl=vi) trước khi đăng."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vm"))
import may_dang_dom as m  # noqa: E402


class CdpGia:
    def __init__(self, tab, doi_duoc=True):
        self.tab, self.doi_duoc, self.dat = tab, doi_duoc, []

    def goi(self, lenh, tham, sid=None, han=None):
        if lenh == "Network.getCookies":
            return {"cookies": [{"name": "PREF", "value": "tz=Asia.Tokyo&hl=ja&f6=40000000", "expires": 123.0}]}
        if lenh == "Network.setCookie":
            self.dat.append(tham)
            if self.doi_duoc:
                self.tab.lang = "vi-VN"
            return {"success": True}
        return {}


class TabGia:
    def __init__(self, lang, doi_duoc=True):
        self.lang, self.sid, self.mo_ = lang, "s1", []
        self.cdp = CdpGia(self, doi_duoc)

    def js_tho(self, bt):
        return self.lang

    def mo(self, url, han=60):
        self.mo_.append(url)


def _may():
    may = m.MayDangDom.__new__(m.MayDangDom)
    may.kenh, may.bo, may.uc, may.ngu, may.nk = "K", {"url": {"studio": "https://studio.youtube.com/"}}, "UC1", lambda s: None, lambda s: None
    return may


def test_da_tieng_viet_khong_dung_cookie():
    tb = TabGia("vi-VN")
    _may()._ep_ngon_ngu_dang(tb)
    assert tb.cdp.dat == [] and tb.mo_ == []


def test_tieng_nhat_dat_cookie_giu_cap_khac():
    tb = TabGia("ja-JP")
    _may()._ep_ngon_ngu_dang(tb)
    c = tb.cdp.dat[0]
    assert c["value"] == "tz=Asia.Tokyo&f6=40000000&hl=vi" and c["expires"] == 123.0
    assert tb.mo_ and tb.lang == "vi-VN"


def test_khong_doi_duoc_thi_loi_truoc():
    with pytest.raises(m.LoiTruoc):
        _may()._ep_ngon_ngu_dang(TabGia("ja-JP", doi_duoc=False))


def test_trang_gia_khong_co_cdp_bo_qua():
    _may()._ep_ngon_ngu_dang(object())
