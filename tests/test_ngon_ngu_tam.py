"""05/10: máy DOM tạm đổi hl=vi rồi TRẢ lại ngôn ngữ hiển thị gốc của kênh (mọi ngôn ngữ, mọi VPS)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vm"))
import may_dang_dom as m  # noqa: E402
import ngon_ngu_tam as nt  # noqa: E402


class TrinhDuyetGia:
    """CDP cấp trình duyệt giả: một cookie PREF; Storage.* đọc/ghi."""

    def __init__(self, pref="tz=Asia.Tokyo&gl=JP&hl=ja", hong=False):
        self.pref, self.hong = pref, hong

    def goi(self, lenh, tham=None, sid=None, han=None):
        if self.hong:
            raise RuntimeError("cdp dứt")
        if lenh == "Storage.getCookies":
            return {"cookies": [{"name": "PREF", "domain": ".youtube.com", "value": self.pref, "expires": 9e9}]}
        if lenh == "Storage.setCookies":
            self.pref = tham["cookies"][0]["value"]
            return {}
        return {}


def test_ham_thuan():
    assert nt.hl_cua("tz=x&hl=ja&gl=JP") == "ja"
    assert nt.pref_voi_hl("tz=x&hl=vi&gl=JP", "ja") == "tz=x&gl=JP&hl=ja"
    assert nt.pref_voi_hl("tz=x&hl=vi", nt.KHONG_CO) == "tz=x"


def test_ghi_tam_giu_goc_lan_dau(tmp_path):
    assert nt.ghi_tam("K", "ja", thu_muc=str(tmp_path))
    assert not nt.ghi_tam("K", "vi", thu_muc=str(tmp_path))      # lần đổi thứ hai không đè gốc
    assert nt.doc_tam("K", thu_muc=str(tmp_path))["hl_goc"] == "ja"


def test_tra_lai_goc_va_xoa_tep(tmp_path):
    nt.ghi_tam("K", "ja", thu_muc=str(tmp_path))
    br = TrinhDuyetGia(pref="tz=x&gl=JP&hl=vi")
    assert nt.tra(br, "K", thu_muc=str(tmp_path)) == "ok:ja"
    assert br.pref == "tz=x&gl=JP&hl=ja" and not nt.doc_tam("K", thu_muc=str(tmp_path))


def test_goc_khong_co_hl_thi_bo_cap_hl(tmp_path):
    nt.ghi_tam("K", "", thu_muc=str(tmp_path))
    br = TrinhDuyetGia(pref="gl=JP&hl=vi")
    assert nt.tra(br, "K", thu_muc=str(tmp_path)) == "ok:" + nt.KHONG_CO and br.pref == "gl=JP"


def test_khong_co_tep_thi_khong_dung(tmp_path):
    br = TrinhDuyetGia(pref="hl=vi")
    assert nt.tra(br, "K", thu_muc=str(tmp_path)) == "" and br.pref == "hl=vi"


def test_loi_cdp_giu_tep_de_lan_sau(tmp_path):
    nt.ghi_tam("K", "ja", thu_muc=str(tmp_path))
    assert nt.tra(TrinhDuyetGia(hong=True), "K", thu_muc=str(tmp_path)).startswith("loi:")
    assert nt.doc_tam("K", thu_muc=str(tmp_path))["hl_goc"] == "ja"


class CdpTab:
    def __init__(self, tab):
        self.tab, self.dat = tab, []

    def goi(self, lenh, tham, sid=None, han=None):
        if lenh == "Network.getCookies":
            return {"cookies": [{"name": "PREF", "value": "gl=JP&hl=ja", "expires": 9e9}]}
        if lenh == "Network.setCookie":
            self.dat.append(tham)
            self.tab.lang = "vi-VN"
            return {"success": True}
        return {}


class TabGia:
    def __init__(self, lang):
        self.lang, self.sid, self.mo_ = lang, "s1", []
        self.cdp = CdpTab(self)

    def js_tho(self, bt):
        return self.lang

    def mo(self, url, han=60):
        self.mo_.append(url)


def _may(tmp_path):
    may = m.MayDangDom.__new__(m.MayDangDom)
    may.kenh, may.bo, may.uc, may.ngu, may.nk = "K", {"url": {"studio": "https://studio.youtube.com/"}}, "UC1", \
        lambda s: None, lambda s: None
    may.thu_muc_hl_tam = str(tmp_path)
    return may


def test_vong_tron_ja_vi_ja(tmp_path):
    """Kênh Nhật: máy đăng tạm vi (ghi gốc ja) → cuối phiên trả ja."""
    tb = TabGia("ja-JP")
    _may(tmp_path)._ep_ngon_ngu_dang(tb)
    assert "hl=vi" in tb.cdp.dat[0]["value"] and "gl=JP" in tb.cdp.dat[0]["value"]
    assert nt.doc_tam("K", thu_muc=str(tmp_path))["hl_goc"] == "ja"
    br = TrinhDuyetGia(pref=tb.cdp.dat[0]["value"])
    assert nt.tra(br, "K", thu_muc=str(tmp_path)) == "ok:ja" and nt.hl_cua(br.pref) == "ja"


def test_da_dung_ngon_ngu_may_thi_khong_ghi_tam(tmp_path):
    tb = TabGia("vi-VN")
    _may(tmp_path)._ep_ngon_ngu_dang(tb)
    assert tb.cdp.dat == [] and not nt.doc_tam("K", thu_muc=str(tmp_path))
