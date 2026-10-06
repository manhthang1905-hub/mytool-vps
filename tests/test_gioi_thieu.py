"""Tab «Giới thiệu» của Trung tâm trực quan: trang trình chiếu, nội dung riêng của máy → bản mặc định trung tính,
và bản mặc định đi theo kho chung không mang số liệu/mã kênh/câu chuyện riêng của máy nào."""
import json
import os
import re
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from core import truc_quan as tq

LOAI = {"bia", "muc_luc", "cau_noi", "the", "so_lon", "bang", "bac_thang", "lan", "hai_cot", "so_do_vong",
        "day_chuyen", "chuoi", "ban_do", "nao", "trung_tam", "ket"}


def _mac_dinh():
    with open(os.path.join(tq.VENDOR, "gioi-thieu-mac-dinh.json"), encoding="utf-8") as tep:
        return tep.read()


def test_noi_dung_rieng_may_roi_ve_mac_dinh(tmp_path):
    g = str(tmp_path)
    d = tq.noi_dung_gioi_thieu(g)
    assert d["_nguon"] == "mac_dinh" and len(d["slides"]) >= 10
    p = os.path.join(g, "workspace", "gioi-thieu", "noi-dung.json")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as tep:
        tep.write("{hỏng")
    assert tq.noi_dung_gioi_thieu(g)["_nguon"] == "mac_dinh"            # tệp hỏng → mặc định, không vỡ
    with open(p, "w", encoding="utf-8") as tep:
        json.dump({"slides": [{"loai": "bia", "tieu": "Máy riêng"}]}, tep, ensure_ascii=False)
    d = tq.noi_dung_gioi_thieu(g)
    assert d["_nguon"] == "may" and d["slides"][0]["tieu"] == "Máy riêng"


def test_mac_dinh_trung_tinh_va_dung_loai():
    s = _mac_dinh()
    assert not re.search(r"\bTL\d", s)                                  # không mã kênh
    assert not re.search(r"[぀-ヿ一-鿿]", s)            # không tiêu đề/kênh tiếng Nhật thật
    assert "youtube.com/watch" not in s and "@" not in s
    d = json.loads(s)
    assert {x["loai"] for x in d["slides"]} <= LOAI
    for p in re.findall(r"\{\{([^}|]+)", s):                            # số thật chỉ từ các nguồn đã có
        assert p.split(".")[0] in ("ct", "dl", "nao", "sk", "tinh"), p
    assert any(x.get("chuong") == "Hướng đi" for x in d["slides"])


def test_may_chu_phuc_vu_trang_va_noi_dung(tmp_path, monkeypatch):
    monkeypatch.setattr(tq, "GOC", str(tmp_path))
    with open(os.path.join(tq.VENDOR, "..", "gioi-thieu.html"), encoding="utf-8") as tep:
        trang_goc = tep.read()
    os.makedirs(os.path.join(str(tmp_path), "ui_web"))
    with open(os.path.join(str(tmp_path), "ui_web", "gioi-thieu.html"), "w", encoding="utf-8") as tep:
        tep.write(trang_goc)
    sv = ThreadingHTTPServer(("127.0.0.1", 0), tq._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        goc = "http://127.0.0.1:{0}".format(sv.server_address[1])
        trang = urllib.request.urlopen(goc + "/gioi-thieu", timeout=10).read().decode("utf-8")
        assert 'class="tab on" href="/gioi-thieu"' in trang and "/gioi-thieu.json" in trang
        d = json.loads(urllib.request.urlopen(goc + "/gioi-thieu.json", timeout=10).read().decode("utf-8"))
        assert d["_nguon"] == "mac_dinh" and d["slides"]
    finally:
        sv.shutdown()
        sv.server_close()


def test_bon_trang_co_tab_gioi_thieu():
    for ten in ("chien-truong.html", "truc-quan.html", "nao.html", "gioi-thieu.html"):
        with open(os.path.join(tq.GOC, "ui_web", ten), encoding="utf-8") as tep:
            assert 'href="/gioi-thieu"' in tep.read(), ten
    with open(os.path.join(tq.VENDOR, "chung.js"), encoding="utf-8") as tep:
        assert '"4": "/gioi-thieu"' in tep.read()
