"""Trung tâm trực quan: đường tĩnh /vendor/ (phông, CSS/JS dùng chung) — chỉ thư mục ui_web/vendor, chỉ đuôi
trong danh sách trắng, chặn lách thư mục; 3 trang dùng chung hệ giao diện và không phụ thuộc CDN."""
import os
import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from core import truc_quan as tq


def _ghi(p, du=b"x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as tep:
        tep.write(du)


def test_tep_tinh_chi_trong_vendor_va_dung_duoi(tmp_path):
    goc = tmp_path / "vendor"
    _ghi(str(goc / "he-thong.css"))
    _ghi(str(goc / "fonts" / "a.woff2"))
    _ghi(str(goc / "bi-mat.json"))
    _ghi(str(tmp_path / "ngoai.css"))
    g = str(goc)
    assert tq.tep_tinh("/vendor/he-thong.css?v=3", g) == os.path.realpath(str(goc / "he-thong.css"))
    assert tq.tep_tinh("/vendor/fonts/a.woff2", g) == os.path.realpath(str(goc / "fonts" / "a.woff2"))
    for xau in ("/vendor/../ngoai.css", "/vendor/%2e%2e/ngoai.css", "/vendor/fonts/../../ngoai.css",
                "/vendor/..%5Cngoai.css", "/vendor/%2e%2e%2fngoai.css", "/vendor//etc/x.css", "/vendor/C:/x.css",
                "/vendor/bi-mat.json", "/vendor/khong-co.css", "/vendor/", "/khac/he-thong.css", "/vendor/fonts"):
        assert tq.tep_tinh(xau, g) is None, xau


@pytest.fixture()
def may_chu():
    sv = ThreadingHTTPServer(("127.0.0.1", 0), tq._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        yield "http://127.0.0.1:{0}".format(sv.server_address[1])
    finally:
        sv.shutdown()
        sv.server_close()


def test_may_chu_phuc_vu_vendor_va_chan_lach(may_chu):
    r = urllib.request.urlopen(may_chu + "/vendor/he-thong.css", timeout=10)
    assert r.status == 200 and r.headers["Content-Type"].startswith("text/css")
    assert b"--ta:" in r.read()
    r = urllib.request.urlopen(may_chu + "/vendor/chung.js", timeout=10)
    assert r.headers["Content-Type"].startswith("text/javascript")
    phong = sorted(x for x in os.listdir(os.path.join(tq.VENDOR, "fonts")) if x.endswith(".woff2"))
    assert phong
    r = urllib.request.urlopen(may_chu + "/vendor/fonts/" + phong[0], timeout=10)
    assert r.headers["Content-Type"] == "font/woff2" and r.read(4) == b"wOF2"
    for xau in ("/vendor/../core/truc_quan.py", "/vendor/%2e%2e/%2e%2e/core/truc_quan.py", "/vendor/..%5C..%5Ccore%5Ctruc_quan.py"):
        with pytest.raises(urllib.error.HTTPError) as loi:
            urllib.request.urlopen(may_chu + xau, timeout=10)
        assert loi.value.code == 404


def test_ba_trang_dung_chung_he_giao_dien_khong_cdn():
    for ten in ("chien-truong.html", "truc-quan.html", "nao.html"):
        with open(os.path.join(tq.GOC, "ui_web", ten), encoding="utf-8") as tep:
            s = tep.read()
        assert "/vendor/he-thong.css" in s and "/vendor/chung.js" in s, ten
        assert not re.search(r"""(src|href)=["']https?://""", s), ten           # không tải gì từ mạng ngoài
        assert 'href="/"' in s and 'href="/hau-can"' in s and 'href="/nao"' in s, ten
    for ten, js in (("chien-truong.html", "ban-do.js"),):        # bản đồ lục giác + mọi tệp vendor trang gọi đều có thật
        with open(os.path.join(tq.GOC, "ui_web", ten), encoding="utf-8") as tep:
            s = tep.read()
        assert "/vendor/" + js in s
        for duong in re.findall(r"""(?:src|href)=["']/vendor/([^"'?]+)""", s):
            assert os.path.isfile(os.path.join(tq.VENDOR, duong)), duong
    with open(os.path.join(tq.VENDOR, "he-thong.css"), encoding="utf-8") as tep:
        css = tep.read()
    for url in re.findall(r"url\((fonts/[^)]+)\)", css):          # mọi phông khai báo đều có thật
        assert os.path.isfile(os.path.join(tq.VENDOR, url)), url
    assert "prefers-reduced-motion" in css
