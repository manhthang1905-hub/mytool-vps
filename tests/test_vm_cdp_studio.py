"""Động cơ CDP + bộ chọn Studio của máy đăng DOM (Việc A, thiết kế
`workspace/THIET-KE-MAY-DANG-DOM.md` mục 1, 2.1, 10).

Không gọi mạng, không mở Chrome: websocket GIẢ trả lời theo kịch bản, và một
trang HTML tĩnh giả để khớp bộ chọn bằng `html.parser`.
"""

from __future__ import annotations

import collections
import json
import random
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp as cdp_mod  # noqa: E402
import cdp_studio  # noqa: E402


# ── websocket giả ──────────────────────────────────────────────────────────

class WsGia:
    """Websocket giả: `tra_loi(goi_da_gui) -> list[dict]` sinh các gói Chrome
    trả về; `recv` hết hàng thì ném TimeoutError (đúng kiểu hết hạn)."""

    def __init__(self, tra_loi=None):
        self.den = collections.deque()
        self.da_gui = []
        self.tra_loi = tra_loi or (lambda g: [{"id": g["id"], "result": {}}])
        self.dong_ = False

    def send(self, s):
        g = json.loads(s)
        self.da_gui.append(g)
        for x in self.tra_loi(g) or []:
            self.den.append(json.dumps(x) if not isinstance(x, str) else x)

    def recv(self):
        if self.den:
            x = self.den.popleft()
            if isinstance(x, BaseException):
                raise x
            return x
        raise TimeoutError("hết hàng")

    def settimeout(self, _t):
        pass

    def close(self):
        self.dong_ = True


class TestBoChonJson:
    def test_du_khoa_va_dung_cau_truc(self):
        bo = cdp_studio.doc_bo_chon()
        assert cdp_studio.kiem_bo_chon(bo) == []
        for k in cdp_studio.KHOA_BAT_BUOC:
            assert k in bo["phan_tu"], k

    def test_danh_sach_kiem_chi_dung_khoa_co_that(self):
        bo = cdp_studio.doc_bo_chon()
        for k in bo["kiem_muc_1"] + bo["kiem_muc_2"]:
            assert k in bo["phan_tu"], k

    def test_url_mau_dien_duoc(self):
        bo = cdp_studio.doc_bo_chon()
        u = bo["url"]
        assert "UCabc" in u["upload"].format(uc="UCabc")
        assert "/video/xyz/edit" in u["sua"].format(id="xyz")
        assert "%E7%8C%AB" in u["loc_tieu_de"].format(uc="UC1", q="%E7%8C%AB")

    def test_kiem_bo_chon_bat_loi(self):
        bo = cdp_studio.doc_bo_chon()
        hong = json.loads(json.dumps(bo))
        del hong["phan_tu"]["nut_tiep"]
        hong["phan_tu"]["tieu_de"]["chon"] = ["#title-textarea [aria-label='x"]
        loi = cdp_studio.kiem_bo_chon(hong)
        assert any("nut_tiep" in x for x in loi)
        assert any("tieu_de" in x for x in loi)

    def test_cam_bam_co_nut_phan_hoi(self):
        cam = cdp_studio.doc_bo_chon()["cam_bam"]
        assert "phản hồi" in cam["aria_chua"]
        assert "ytcp-feedback-button" in cam["chon"]


class TestCdp:
    def test_khop_dung_id_va_xep_hang_su_kien(self):
        def tl(g):
            return [{"method": "Page.loadEventFired", "sessionId": "S1", "params": {"t": 1}},
                    {"id": g["id"] + 100, "result": {"sai": True}},
                    {"id": g["id"], "result": {"dung": True}}]
        c = cdp_mod.Cdp(WsGia(tl))
        assert c.goi("X.y") == {"dung": True}
        assert c.cho_su_kien("Page.loadEventFired", han=0.2, sid="S1") == {"t": 1}

    def test_sessionid_di_kem_lenh(self):
        ws = WsGia()
        c = cdp_mod.Cdp(ws)
        c.goi("Page.enable", sid="S9")
        assert ws.da_gui[-1]["sessionId"] == "S9"

    def test_het_han(self):
        c = cdp_mod.Cdp(WsGia(lambda g: []))
        with pytest.raises(cdp_mod.CdpHetHan):
            c.goi("Chrome.imLang", han=0.2)
        with pytest.raises(cdp_mod.CdpHetHan):
            c.cho_su_kien("Page.fileChooserOpened", han=0.2)

    def test_loi_devtools(self):
        c = cdp_mod.Cdp(WsGia(lambda g: [{"id": g["id"], "error": {"message": "không có"}}]))
        with pytest.raises(cdp_mod.CdpLoi) as e:
            c.goi("A.b")
        assert "không có" in str(e.value)
        assert not isinstance(e.value, cdp_mod.CdpHetHan)

    def test_dut(self):
        ws = WsGia(lambda g: [])
        ws.den.append(ConnectionResetError("reset"))
        c = cdp_mod.Cdp(ws)
        with pytest.raises(cdp_mod.CdpDut):
            c.goi("A.b", han=1)
        ws2 = WsGia(lambda g: [""])
        with pytest.raises(cdp_mod.CdpDut):
            cdp_mod.Cdp(ws2).goi("A.b", han=1)

    def _hop_thoai(self, loai, sid, giu):
        ws = WsGia(lambda g: ([{"method": "Page.javascriptDialogOpening", "sessionId": sid,
                                "params": {"type": loai, "message": "Rời trang?"}},
                               {"id": g["id"], "result": {}}] if g["method"] == "X.y"
                              else [{"id": g["id"], "result": {}}]))
        c = cdp_mod.Cdp(ws)
        c.giu_tab |= giu
        c.goi("X.y")
        tl = [g for g in ws.da_gui if g["method"] == "Page.handleJavaScriptDialog"]
        assert len(tl) == 1 and tl[0]["sessionId"] == sid
        return tl[0]["params"]["accept"]

    def test_chinh_sach_hop_thoai(self):
        # beforeunload trên tab đang tải (giữ) → TỪ CHỐI; tab khác → chấp nhận
        assert self._hop_thoai("beforeunload", "A", {"A"}) is False
        assert self._hop_thoai("beforeunload", "B", {"A"}) is True
        assert self._hop_thoai("confirm", "A", {"A"}) is True
        assert self._hop_thoai("alert", "A", set()) is True

    def test_luu_hop_chon_tep(self):
        ws = WsGia(lambda g: [{"method": "Page.fileChooserOpened", "sessionId": "S1",
                               "params": {"backendNodeId": 42, "mode": "selectSingle"}},
                              {"id": g["id"], "result": {}}])
        c = cdp_mod.Cdp(ws)
        c.goi("X.y")
        assert c.tep_cho["S1"]["backendNodeId"] == 42

    def test_tao_tab_khong_bat_runtime(self):
        def tl(g):
            m = g["method"]
            if m == "Target.createTarget":
                return [{"id": g["id"], "result": {"targetId": "T1"}}]
            if m == "Target.attachToTarget":
                return [{"id": g["id"], "result": {"sessionId": "S1"}}]
            return [{"id": g["id"], "result": {}}]
        ws = WsGia(tl)
        c = cdp_mod.Cdp(ws)
        assert c.tao_tab() == ("T1", "S1")
        cac = [g["method"] for g in ws.da_gui]
        assert "Runtime.enable" not in cac
        assert "Page.setInterceptFileChooserDialog" in cac
        assert ws.da_gui[1]["params"]["flatten"] is True


# ── TrangStudio trên websocket giả kịch bản ────────────────────────────────

class ChromeGia:
    """Trả lời CDP cho TrangStudio: thế giới riêng, `window.__yd.<ham>(…)`."""

    def __init__(self):
        self.ham = {}
        self.chuot = []
        self.phim = []
        self.chen = []
        self.dat_tep = []
        self.mo_hop_tep_khi_bam = False
        self.ws = WsGia(self._tl)

    def _tl(self, g):
        m, p = g["method"], g.get("params") or {}
        sid = g.get("sessionId")
        r = {}
        them = []
        if m == "Page.getFrameTree":
            r = {"frameTree": {"frame": {"id": "F1"}}}
        elif m == "Page.createIsolatedWorld":
            assert p["worldName"] == "yd"
            r = {"executionContextId": 7}
        elif m == "Runtime.evaluate":
            assert p["contextId"] == 7
            bt = p["expression"]
            if bt.startswith("((function(CAM)"):
                r = {"result": {"type": "boolean", "value": True}}
            else:
                mm = re.match(r"window\.__yd\.(\w+)\((.*)\)$", bt, re.S)
                ten, doi = mm.group(1), json.loads("[" + mm.group(2) + "]")
                gia_tri = self.ham[ten](*doi) if ten in self.ham else None
                r = ({"result": {"value": gia_tri}} if p.get("returnByValue")
                     else {"result": {"objectId": "OBJ-" + str(doi[0])}})
        elif m == "Input.dispatchMouseEvent":
            self.chuot.append(p)
            if p["type"] == "mouseReleased" and self.mo_hop_tep_khi_bam:
                them.append({"method": "Page.fileChooserOpened", "sessionId": sid,
                             "params": {"backendNodeId": 99, "mode": "selectSingle"}})
        elif m == "Input.dispatchKeyEvent":
            self.phim.append(p)
        elif m == "Input.insertText":
            self.chen.append(p["text"])
        elif m == "DOM.setFileInputFiles":
            self.dat_tep.append(p)
        return [{"id": g["id"], "result": r}] + them


def _trang(chrome, bo=None):
    c = cdp_mod.Cdp(chrome.ws)
    nk = []
    t = cdp_studio.TrangStudio(c, "T1", "S1", bo_chon=bo or cdp_studio.doc_bo_chon(),
                               nhat_ky=nk.append, ngu=lambda s: None, rng=random.Random(3))
    return t, nk


RECT = {"x": 100.0, "y": 200.0, "w": 80.0, "h": 30.0}


def _pt(**kw):
    d = {"khop": True, "cach": "chon#1", "sel": "#x", "so": 1, "id": "p1", "tag": "ytcp-button",
         "rect": dict(RECT), "tat": False, "cam": "", "mo_ta": "ytcp-button#x"}
    d.update(kw)
    return d


class TestTrangStudioBam:
    def _chrome(self, **pt):
        ch = ChromeGia()
        ch.ham["tim"] = lambda spec, o: _pt(**pt)
        ch.ham["cuon"] = lambda i: {"rect": dict(RECT), "hien": True, "tat": False, "cam": pt.get("cam", "")}
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": True}
        return ch

    def test_diem_bam_trong_khung_35_phan_tram(self):
        ch = self._chrome()
        t, _ = _trang(ch)
        t.bam("nut_tiep")
        nhan = [e for e in ch.chuot if e["type"] == "mousePressed"]
        nha = [e for e in ch.chuot if e["type"] == "mouseReleased"]
        di = [e for e in ch.chuot if e["type"] == "mouseMoved"]
        assert len(nhan) == 1 and len(nha) == 1 and 3 <= len(di) <= 6
        x, y = nhan[0]["x"], nhan[0]["y"]
        assert 140 - 14 - 0.1 <= x <= 140 + 14 + 0.1
        assert 215 - 5.25 - 0.1 <= y <= 215 + 5.25 + 0.1
        assert (nha[0]["x"], nha[0]["y"]) == (x, y)
        assert nhan[0]["button"] == "left" and nhan[0]["clickCount"] == 1
        assert di[-1]["x"] == x and di[-1]["y"] == y

    def test_diem_bam_ham_thuan(self):
        rng = random.Random(0)
        for _ in range(200):
            x, y = cdp_studio.diem_bam(RECT, rng)
            assert 125.9 <= x <= 154.1 and 209.6 <= y <= 220.4

    def test_tu_choi_nut_cam(self):
        ch = self._chrome(cam="aria chứa phản hồi")
        t, _ = _trang(ch)
        with pytest.raises(cdp_studio.LoiThaoTac) as e:
            t.bam("nut_tiep")
        assert "cấm" in str(e.value)
        assert ch.chuot == []

    def test_bi_che_khong_bam(self):
        ch = self._chrome()
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": False, "ly_do": "bị che bởi tp-yt-paper-dialog", "che": "p9"}
        ch.ham["hopLa"] = lambda ds, che, *a: []
        t, _ = _trang(ch)
        with pytest.raises(cdp_studio.LoiThaoTac):
            t.bam("nut_tiep")
        assert not [e for e in ch.chuot if e["type"] == "mousePressed"]

    def test_bi_che_mai_nut_an_toan_thi_bam_js(self):
        """30/09: nut_tiep bị che 4 lần liền → el.click() (nút an toàn), hậu điều kiện vẫn kiểm."""
        ch = self._chrome()
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": False, "ly_do": "bị che bởi div", "che": "p9"}
        ch.ham["hopLa"] = lambda ds, che, *a: []
        ch.ham["diemTrong"] = lambda i: {"ok": False}
        ch.ham["loaiChe"] = lambda i: "khac"
        goi_js = []
        ch.ham["bamJs"] = lambda i: goi_js.append(i) or {"ok": True, "mo_ta": "button"}
        t, nk = _trang(ch)
        t.bam("nut_tiep", hau_dieu_kien=lambda: True)
        assert goi_js == ["p1"]
        assert not [e for e in ch.chuot if e["type"] == "mousePressed"]
        assert sum("(lần " in s for s in nk) == cdp_studio.SO_LAN_BAM_CHE
        assert any("BẤM BẰNG JS" in s for s in nk)
        # hậu điều kiện hỏng sau bấm JS → vẫn là lỗi
        with pytest.raises(cdp_studio.LoiThaoTac):
            t.bam("nut_tiep", hau_dieu_kien=lambda: False, han_hau=0)

    def test_bi_che_mai_nut_khong_an_toan_khong_bam_js(self):
        ch = self._chrome()
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": False, "ly_do": "bị che bởi div", "che": "p9"}
        ch.ham["hopLa"] = lambda ds, che, *a: []
        goi_js = []
        ch.ham["bamJs"] = lambda i: goi_js.append(i) or {"ok": True}
        t, _ = _trang(ch)
        with pytest.raises(cdp_studio.LoiThaoTac) as e:
            t.bam("mhkt_mau")
        assert goi_js == [] and "bị che" in str(e.value)

    def test_bi_che_mot_phan_bam_diem_khac(self):
        """Thanh cuộn/panel đè một phần (div#scrollbar) → bấm điểm khác không bị che."""
        ch = self._chrome()
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": False, "ly_do": "bị che bởi div#scrollbar", "che": "p9"}
        ch.ham["diemTrong"] = lambda i: {"ok": True, "x": 112.0, "y": 215.0}
        t, _ = _trang(ch)
        t.bam("nut_tiep")
        nhan = [e for e in ch.chuot if e["type"] == "mousePressed"]
        assert len(nhan) == 1 and (nhan[0]["x"], nhan[0]["y"]) == (112.0, 215.0)

    def test_bi_che_tam_thoi_cho_roi_bam_lai(self):
        """Backdrop đang mờ dần: lần 1–2 bị che, lần 3 trúng → bấm thật, không JS."""
        ch = self._chrome()
        lan = {"n": 0}

        def trung(i, x, y):
            lan["n"] += 1
            return {"ok": lan["n"] >= 3, "ly_do": "bị che bởi tp-yt-iron-overlay-backdrop", "che": "p9"}
        ch.ham["trungDiem"] = trung
        ch.ham["hopLa"] = lambda ds, che, *a: []
        ch.ham["loaiChe"] = lambda i: "man"
        goi_js = []
        ch.ham["bamJs"] = lambda i: goi_js.append(i) or {"ok": True}
        t, _ = _trang(ch)
        t.bam("phu_de_xong")
        assert goi_js == [] and len([e for e in ch.chuot if e["type"] == "mousePressed"]) == 1

    def test_bi_che_do_lai_khoa(self):
        """the_menu_video khớp nhầm bằng chữ rồi bị chính mục menu che → dò lại khoá, bấm phần tử mới."""
        ch = self._chrome()
        dem = {"tim": 0}

        def tim(spec, o):
            dem["tim"] += 1
            return _pt(id="p1" if dem["tim"] == 1 else "p7")
        ch.ham["tim"] = tim
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": i == "p7", "ly_do": "bị che bởi tp-yt-paper-item#text-item-0",
                                                "che": "p9"}
        ch.ham["hopLa"] = lambda ds, che, *a: []
        t, _ = _trang(ch)
        assert t.bam("the_menu_video")["id"] == "p7"

    def test_tooltip_che_thi_an(self):
        ch = self._chrome()
        lan = {"n": 0}

        def trung(i, x, y):
            lan["n"] += 1
            return {"ok": lan["n"] > 1, "ly_do": "bị che bởi tp-yt-paper-tooltip", "che": "p9"}
        ch.ham["trungDiem"] = trung
        ch.ham["loaiChe"] = lambda i: "tooltip"
        an = []
        ch.ham["anTooltip"] = lambda i: an.append(i) or "tp-yt-paper-tooltip"
        t, nk = _trang(ch)
        t.bam("the_them")
        assert an == ["p9"] and any("ẩn tooltip" in s for s in nk)

    def test_bi_che_don_hop_la_roi_bam(self):
        ch = self._chrome()
        lan = {"n": 0}

        def trung(i, x, y):
            lan["n"] += 1
            return {"ok": True} if lan["n"] > 1 else {"ok": False, "ly_do": "bị che", "che": "p9"}
        ch.ham["trungDiem"] = trung
        ch.ham["hopLa"] = lambda ds, che, *a: [_pt(id="p10", sel="ytcp-warm-welcome-dialog")]
        t, nk = _trang(ch)
        t.bam("nut_tiep")
        # 1 cú bấm dẹp hộp lạ + 1 cú bấm nút thật
        assert len([e for e in ch.chuot if e["type"] == "mousePressed"]) == 2
        assert any("dẹp hộp lạ" in s for s in nk)

    def test_vo_hieu_khong_bam(self):
        ch = self._chrome()
        ch.ham["cuon"] = lambda i: {"rect": dict(RECT), "hien": True, "tat": True, "cam": ""}
        t, _ = _trang(ch)
        with pytest.raises(cdp_studio.LoiThaoTac):
            t.bam("nut_tiep")

    def test_hau_dieu_kien(self):
        ch = self._chrome()
        t, _ = _trang(ch)
        with pytest.raises(cdp_studio.LoiThaoTac):
            t.bam("nut_tiep", hau_dieu_kien=lambda: False, han_hau=0.05)
        t.bam("nut_tiep", hau_dieu_kien=lambda: True)

    def test_du_phong_duoc_ghi(self):
        ch = self._chrome(cach="chon#2", sel="#next-button")
        t, nk = _trang(ch)
        assert t.tim("nut_tiep", han=0)["cach"] == "chon#2"
        assert t.du_phong == {"nut_tiep": "chon#2"}
        assert any("DU PHONG nut_tiep" in s for s in nk)


class TestTrangStudioGo:
    def _chrome(self, doc):
        ch = ChromeGia()
        ch.ham["tim"] = lambda spec, o: _pt()
        ch.ham["cuon"] = lambda i: {"rect": dict(RECT), "hien": True, "tat": False, "cam": ""}
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": True}
        ch.ham["chonHet"] = lambda i: True
        ch.ham["chu"] = doc
        return ch

    def test_nhieu_dong_chen_tung_dong_va_enter(self):
        mo_ta = "dòng 1\n📌目次\n00:00 mở đầu"
        ch = self._chrome(lambda i: mo_ta)
        t, _ = _trang(ch)
        assert t.go("mo_ta", mo_ta) == mo_ta
        assert ch.chen == ["dòng 1", "📌目次", "00:00 mở đầu"]
        enter = [p for p in ch.phim if p.get("key") == "Enter" and p["type"] == "keyDown"]
        assert len(enter) == 2
        ctrl_a = [p for p in ch.phim if p.get("key") == "a"]
        assert ctrl_a and ctrl_a[0]["modifiers"] == 2

    def test_doc_lai_lech_hai_lan_thi_loi(self):
        ch = self._chrome(lambda i: "dòng 1dòng 2")   # mất xuống dòng
        t, _ = _trang(ch)
        with pytest.raises(cdp_studio.LoiThaoTac):
            t.go("mo_ta", "dòng 1\ndòng 2")

    def test_khop_doc_lai(self):
        assert cdp_studio.khop_doc_lai("a\nb", "a\nb  \n") == "dung"
        assert cdp_studio.khop_doc_lai("a\n\nb", "a\n\n\nb") == "gan"
        assert cdp_studio.khop_doc_lai("a\nb", "ab") == "lech"


class TestDatTep:
    def test_hop_chon_tep_roi_setfileinputfiles(self, tmp_path):
        tep = tmp_path / "8-video.mp4"
        tep.write_bytes(b"x")
        ch = ChromeGia()
        ch.ham["tim"] = lambda spec, o: _pt()
        ch.ham["cuon"] = lambda i: {"rect": dict(RECT), "hien": True, "tat": False, "cam": ""}
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": True}
        ch.mo_hop_tep_khi_bam = True
        t, _ = _trang(ch)
        assert t.dat_tep("nut_chon_tep", str(tep)) == "hop_chon_tep"
        assert ch.dat_tep == [{"files": [str(tep)], "backendNodeId": 99}]

    def test_du_phong_o_tep_an(self, tmp_path):
        tep = tmp_path / "a.srt"
        tep.write_text("1")
        ch = ChromeGia()
        ch.ham["tim"] = lambda spec, o: _pt()
        ch.ham["cuon"] = lambda i: {"rect": dict(RECT), "hien": True, "tat": False, "cam": ""}
        ch.ham["trungDiem"] = lambda i, x, y: {"ok": True}
        t, _ = _trang(ch)
        assert t.dat_tep("nut_chon_tep", str(tep), khoa_input="o_tep_video", han=0.3) == "o_tep"
        assert ch.dat_tep[0]["objectId"].startswith("OBJ-")

    def test_khong_co_tep(self, tmp_path):
        t, _ = _trang(ChromeGia())
        with pytest.raises(cdp_studio.LoiThaoTac):
            t.dat_tep("nut_chon_tep", str(tmp_path / "khong-co.mp4"))


def test_don_bang_chung_giu_50(tmp_path):
    for i in range(60):
        for duoi in (".png", "-ban-do.json"):
            (tmp_path / "20260929-10{0:04d}-kiem-x{1}".format(i, duoi)).write_text("x")
    cdp_studio.don_bang_chung(str(tmp_path), giu=50)
    con = sorted(p.name for p in tmp_path.iterdir() if p.name != "vm-goc-mac-dinh")   # thư mục của conftest
    assert len(con) == 100
    assert con[0].startswith("20260929-100010")


# ── Trang HTML tĩnh giả + khớp bộ chọn bằng html.parser ────────────────────

class _Nut:
    def __init__(self, tag, attrs, cha):
        self.tag, self.attrs, self.cha = tag, dict(attrs), cha
        self.con = []


class _Cay(HTMLParser):
    RONG = {"input", "br", "img", "meta", "link"}

    def __init__(self, html):
        super().__init__()
        self.goc = _Nut("#goc", {}, None)
        self._cur = self.goc
        self.tat_ca = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        n = _Nut(tag, [(k, v if v is not None else "") for k, v in attrs], self._cur)
        self._cur.con.append(n)
        self.tat_ca.append(n)
        if tag not in self.RONG:
            self._cur = n

    def handle_endtag(self, tag):
        n = self._cur
        while n is not self.goc and n.tag != tag:
            n = n.cha
        if n is not self.goc:
            self._cur = n.cha


_PHAN = re.compile(r"""([a-zA-Z][\w-]*)|#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:([*^]?=)(?:'([^']*)'|"([^"]*)"|([^\]]*)))?\]""")


def _khop_don(n, don):
    vt = 0
    for m in _PHAN.finditer(don):
        if m.start() != vt:
            return None     # cú pháp ngoài tập con → không kiểm
        vt = m.end()
        tag, i, cls, ten, op = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        gt = m.group(6) if m.group(6) is not None else (m.group(7) if m.group(7) is not None else m.group(8))
        if tag and n.tag != tag.lower():
            return False
        if i and n.attrs.get("id") != i:
            return False
        if cls and cls not in n.attrs.get("class", "").split():
            return False
        if ten:
            if ten not in n.attrs:
                return False
            v = n.attrs.get(ten, "")
            if op == "=" and v != gt:
                return False
            if op == "*=" and gt not in v:
                return False
    return vt == len(don)


def khop_bo_chon(cay, sel):
    """querySelectorAll tập con (tag/#id/.class/[attr(=|*=)v] + hậu duệ). None = ngoài tập con."""
    if any(c in sel for c in ":>+~,"):
        return None
    phan = sel.split()
    ra = []
    for n in cay.tat_ca:
        k = _khop_don(n, phan[-1])
        if k is None:
            return None
        if not k:
            continue
        cha, j = n.cha, len(phan) - 2
        while j >= 0 and cha is not None:
            if _khop_don(cha, phan[j]):
                j -= 1
            cha = cha.cha
        if j < 0:
            ra.append(n)
    return ra


#: Dựng theo bản đồ DOM THẬT (`vm/logs/dom/*-ban-do.json`, Studio 29/09/2026,
#: Chrome 151) cho phần đã đo; phần chưa đo (bước Thành phần/Hiển thị) theo
#: thiết kế. SỬA mỗi khi hiệu chỉnh studio-selectors.json.
TRANG_GIA = """
<ytcp-uploads-dialog><tp-yt-paper-dialog id="dialog" class="style-scope ytcp-uploads-dialog">
  <ytcp-send-feedback-button class="style-scope ytcp-uploads-dialog"><ytcp-button><button aria-label="Gửi ý kiến phản hồi"></button></ytcp-button></ytcp-send-feedback-button>
  <ytcp-button id="ytcp-uploads-dialog-close-button" class="style-scope ytcp-uploads-dialog"><button aria-label="Đóng"></button></ytcp-button>
  <ytcp-uploads-file-picker><ytcp-button id="select-files-button">Chọn tệp</ytcp-button>
    <input type="file" name="Filedata"></ytcp-uploads-file-picker>
  <ytcp-video-info><a href="https://youtu.be/abcdefghijk">link</a></ytcp-video-info>
  <ytcp-uploads-details>
    <ytcp-social-suggestions-textbox id="title-textarea"><div id="textbox" contenteditable="true"></div></ytcp-social-suggestions-textbox>
    <div id="description-container"><ytcp-social-suggestions-textbox id="description-textarea"><div id="textbox" contenteditable="true"></div></ytcp-social-suggestions-textbox></div>
    <ytcp-thumbnails-compact-editor-uploader><ytcp-button id="select-button">Tải tệp lên</ytcp-button></ytcp-thumbnails-compact-editor-uploader>
    <ytcp-video-metadata-playlists><ytcp-dropdown-trigger></ytcp-dropdown-trigger></ytcp-video-metadata-playlists>
    <tp-yt-paper-radio-button name="VIDEO_MADE_FOR_KIDS_NOT_MFK" aria-checked="false"></tp-yt-paper-radio-button>
    <ytcp-button id="toggle-button">Hiện thêm</ytcp-button>
    <tp-yt-paper-radio-button name="VIDEO_HAS_ALTERED_CONTENT_YES" aria-checked="false"></tp-yt-paper-radio-button>
    <div id="tags-container"><ytcp-free-text-chip-bar><input id="text-input"></ytcp-free-text-chip-bar></div>
  </ytcp-uploads-details>
  <ytcp-uploads-video-elements><ytcp-button id="subtitles-button">Thêm</ytcp-button>
  <ytcp-button id="import-from-video-button">Nhập từ video</ytcp-button><ytcp-button id="endscreens-button">Thêm</ytcp-button>
  <ytcp-button id="cards-button">Thêm</ytcp-button></ytcp-uploads-video-elements>
  <ytcp-button id="second-container-expand-button">Lên lịch</ytcp-button>
  <ytcp-date-picker><div id="datepicker-trigger"></div><tp-yt-paper-input><input></tp-yt-paper-input></ytcp-date-picker>
  <ytcp-form-input-container id="time-of-day-container"><input></ytcp-form-input-container>
  <ytcp-video-upload-progress><span class="progress-label">Đã tải lên</span></ytcp-video-upload-progress>
  <ytcp-button id="next-button">Tiếp</ytcp-button><ytcp-button id="done-button">Lên lịch</ytcp-button>
</tp-yt-paper-dialog></ytcp-uploads-dialog>
"""

KHOA_TRONG_TRANG_GIA = ("hop_upload", "nut_chon_tep", "o_tep_video", "link_video", "tieu_de", "mo_ta",
                        "nut_thumbnail", "playlist_mo", "khong_tre_em", "hien_them", "ai_co", "o_the",
                        "tien_do", "nut_tiep", "phu_de_them", "mhkt_nhap", "mhkt_them", "the_them",
                        "len_lich_mo", "o_ngay_mo", "o_ngay", "o_gio", "nut_xong", "dong_hop_upload",
                        "nut_phan_hoi")


def test_bo_chon_khop_trang_gia():
    """Mỗi khoá chính có ÍT NHẤT một bộ chọn (trong tập con kiểm được) khớp
    trang giả — và `chon#1` của `tieu_de`/`mo_ta` không lẫn nhau."""
    cay = _Cay(TRANG_GIA)
    pt = cdp_studio.doc_bo_chon()["phan_tu"]
    thieu = []
    for k in KHOA_TRONG_TRANG_GIA:
        ket = [khop_bo_chon(cay, s) for s in pt[k].get("chon") or []]
        kiem_duoc = [r for r in ket if r is not None]
        if kiem_duoc and not any(kiem_duoc):
            thieu.append(k)
    assert thieu == []
    td = khop_bo_chon(cay, pt["tieu_de"]["chon"][0])
    mt = khop_bo_chon(cay, pt["mo_ta"]["chon"][0])
    assert len(td) == 1 and len(mt) == 1 and td[0] is not mt[0]
