"""Tests `core/nao_bo_phan/do_thi.py` — đồ thị thần kinh của não bộ phận (trang `/nao-do-thi`): nút/dây + trần, dây
đồng kích hoạt, xung tăng dần theo con trỏ, `no-ron.json` chặn lách thư mục, đường 8790. Não giả dựng bằng
`nbp.ghi` + `nbp.gom` trong `tmp_path`; kênh giả `KA`/`KB`, mã gói giả."""

import contextlib
import io
import json
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from http.server import ThreadingHTTPServer

import pytest

from core import nao_bo_phan as nbp
from core.nao_bo_phan import _chung as C
from core.nao_bo_phan import do_thi

NGAY = 86400.0
KENH = ("KA", "KB")


def _goc(tmp_path):
    for k in KENH:
        d = tmp_path / "CHANNEL" / k
        d.mkdir(parents=True, exist_ok=True)
        (d / "kenh.yaml").write_text("nhom: n1\n", encoding="utf-8")
    C._KENH.clear()
    return str(tmp_path)


@contextlib.contextmanager
def _db(goc):
    con = sqlite3.connect(C.duong_db(goc))
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _id_loi(bp, nd):
    return "{0}/loi/{1}".format(bp, nbp.chu_ky(nd, KENH))


def _bai_ngu(goc, bp, ma, ung_ho, noi=()):
    """Bài tự rút (giấc ngủ) viết thẳng vào vault — `gom` không đụng, chỉ đưa vào chỉ mục."""
    than = ["# Bài {0} rút từ giấc ngủ".format(ma), "", "## Liên kết", "- " + C.lk(bp + "/so-tay", "Sổ tay"),
            "- " + C.lk_the("kenh/KA")] + (["- nối: " + " · ".join(C.lk(t) for t in noi)] if noi else [])
    p = os.path.join(C.duong_vault(goc), bp, "bai-hoc", ma + ".md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(C.ve_ghi_chu({"loai": "bai-hoc", "id": ma, "bo_phan": bp, "nguon": "ngu", "trang_thai": "dang-dung",
                                "alpha": 5, "beta": 1, "n": len(ung_ho), "kenh": ["KA"], "pham_vi": ["kenh/KA"],
                                "vao_loi_nhac": True, "ung_ho": list(ung_ho), "phan_doi": [], "noi": list(noi)},
                               "\n".join(than)))
    return "{0}/bai-hoc/{1}".format(bp, ma)


def _nao(tmp_path):
    """X (giọng) gặp ở gói 1, 2, 3 · Y (ảnh) ở gói 1, 2 + KB · Z (đăng) chỉ gói 1 · W im 20 ngày · cảnh báo dự phòng ·
    bài tự rút L (bằng chứng = X ở gói 1, 2), L2 nối L · một bài bản chiếu đang dùng (sổ sản xuất)."""
    goc = _goc(tmp_path)
    bg = time.time()

    def loi(bp, goi, nd, luc, khoa, kenh="KA"):
        assert nbp.ghi(goc, bp, "loi", kenh=kenh, ma_goi=goi, noi_dung=nd, luc=luc, khoa=khoa, nguon="so-ngay")

    for i, goi in enumerate(("KA-0001", "KA-0002", "KA-0003")):
        loi("giong-doc", goi, "lỗi X đọc hỏng", bg - 3600 * (i + 1), "x%d" % i)
    for i, goi in enumerate(("KA-0001", "KA-0002")):
        loi("anh-clip", goi, "máy chủ ảnh treo", bg - 3600 * (i + 1) - 60, "y%d" % i)
    loi("anh-clip", "KB-0009", "máy chủ ảnh treo", bg - 7200, "y9", kenh="KB")
    loi("dang-video", "KA-0001", "nút tải lên không thấy", bg - 3000, "z0")
    loi("suc-khoe-may", "", "ổ đĩa đầy từ lâu", bg - 20 * NGAY, "w0", kenh="")
    assert nbp.ghi(goc, "dang-video", "loi", kenh="KB", noi_dung="bộ chọn dự phòng đã cứu", luc=bg - 1800, khoa="c0",
                   so={"kieu": "DU PHONG", "khoa_dom": "nut_tiep"}, nguon="nhat-ky-vm")
    assert nbp.ghi(goc, "chon-content", "ket_qua", kenh="KA", ma_goi="KA-0004", noi_dung="KA-0004: thang",
                   so={"ket": "thang"}, luc=bg - 120, khoa="k0")
    assert nbp.ghi(goc, "chon-content", "chon", kenh="KA", noi_dung="chọn đề tài", luc=bg - 60, khoa="ch0")
    with _db(goc) as con:
        bang_chung = [r[0] for r in con.execute("SELECT id FROM su_kien WHERE khoa IN ('x0', 'x1') ORDER BY id")]
    L = _bai_ngu(goc, "giong-doc", "BH-Naaaa001", bang_chung)
    L2 = _bai_ngu(goc, "giong-doc", "BH-Naaaa002", [], noi=[L])
    p = os.path.join(goc, "CHANNEL", "KA", "nghien-cuu", "bai-hoc-san-xuat.json")
    os.makedirs(os.path.dirname(p))
    with io.open(p, "w", encoding="utf-8") as tep:
        json.dump({"bai_hoc": [{"truc": "tieu_de", "cum": "c1", "do_tin_cay": "cao", "so_mau": 4,
                                "quan_sat": "Tiêu đề có con số thắng 3/4 video"}]}, tep, ensure_ascii=False)
    nbp.gom(goc, bay_gio=bg)
    ids = {"X": _id_loi("giong-doc", "lỗi X đọc hỏng"), "Y": _id_loi("anh-clip", "máy chủ ảnh treo"),
           "Z": _id_loi("dang-video", "nút tải lên không thấy"), "W": _id_loi("suc-khoe-may", "ổ đĩa đầy từ lâu"),
           "CB": _id_loi("dang-video", "bộ chọn dự phòng đã cứu"), "L": L, "L2": L2}
    return goc, ids


def _dong(du):
    return {(l["source"], l["target"]): l["trong_so"] for l in du["day"] if l["loai"] == "dong"}


# ── đồ thị ───────────────────────────────────────────────────────────────────

def test_do_thi_nut_day_va_dong_kich_hoat(tmp_path):
    goc, ids = _nao(tmp_path)
    du = do_thi.do_thi(goc)
    nut = {n["id"]: n for n in du["nut"]}
    assert du["co_kho"] and len(nut) == len(du["nut"])
    for n in du["nut"]:
        assert {"id", "nhom", "ten", "bo_phan", "trang_thai", "kich_thuoc", "mau", "tep"} <= set(n), n
    assert nut[do_thi.TRUNG_TAM]["nhom"] == "trung-tam" and nut[do_thi.TRUNG_TAM]["tep"] == "_ban-do"
    assert [n["id"] for n in du["nut"] if n["nhom"] == "bo-phan"] == list(C.BO_PHAN)
    assert nut["giong-doc"]["so_loi"] == 1 and nut["giong-doc"]["so_bai"] == 2 and nut["giong-doc"]["su_kien_7"] == 3
    assert nut[ids["X"]]["nhom"] == "loi" and nut[ids["X"]]["mau"] == C.DANG
    assert nut[ids["X"]]["kich_thuoc"] > nut[ids["Z"]]["kich_thuoc"]
    assert nut[ids["CB"]]["nhom"] == "canh-bao" and nut[ids["CB"]]["mau"] == "canh-bao"
    assert nut[ids["L"]]["nhom"] == "bai-hoc" and nut[ids["L"]]["mau"] == C.DANG_DUNG
    assert ids["W"] not in nut                                          # đã hết, im quá 14 ngày → không vẽ
    ban_chieu = [n for n in du["nut"] if n["bo_phan"] == "tieu-de" and n["nhom"] == "bai-hoc"]
    assert len(ban_chieu) == 1 and ban_chieu[0]["mau"] == C.DANG_DUNG
    assert "thuc-the/kenh/KA" in nut and nut["thuc-the/kenh/KA"]["nhom"] == "thuc-the"
    assert "thuc-the/bo-chon/nut_tiep" not in nut                       # chỉ một nơ-ron nối → bỏ
    for l in du["day"]:
        assert {"source", "target", "loai", "trong_so"} <= set(l) and l["source"] in nut and l["target"] in nut, l
    loai = Counter(l["loai"] for l in du["day"])
    assert loai["goc"] == 15 and loai["the"] >= 3
    assert loai["thuoc"] == sum(1 for n in du["nut"] if n["nhom"] in ("loi", "canh-bao", "bai-hoc"))
    assert {(l["source"], l["target"]) for l in du["day"] if l["loai"] == "noi"} == {(ids["L2"], ids["L"])}
    # cùng cháy thì nối: X–Y chung 2 gói, L (bằng chứng = X ở gói 1, 2) chung 2 với X và Y; Z chỉ chung 1 → không nối
    dong = _dong(du)
    assert dong == {tuple(sorted((ids["X"], ids["Y"]))): 2, tuple(sorted((ids["L"], ids["X"]))): 2,
                    tuple(sorted((ids["L"], ids["Y"]))): 2}
    assert du["dem"]["dong"] == 3 and du["dem"]["nut"] == len(du["nut"]) and du["dem"]["loi_dang"] >= 3


def test_do_thi_tran_nut_va_dong(tmp_path, monkeypatch):
    goc, ids = _nao(tmp_path)
    monkeypatch.setattr(do_thi, "TRAN_NUT", 20)
    monkeypatch.setattr(do_thi, "TRAN_THE", 1)
    monkeypatch.setattr(do_thi, "TRAN_DONG", 1)
    du = do_thi.do_thi(goc)
    assert len(du["nut"]) <= 20
    giu = {n["id"] for n in du["nut"] if n["nhom"] in ("loi", "canh-bao", "bai-hoc")}
    assert giu == {ids["X"], ids["Y"], ids["Z"]}                        # giữ nơ-ron sôi động nhất
    assert len(_dong(du)) == 1 and sum(1 for n in du["nut"] if n["nhom"] == "thuc-the") <= 1
    monkeypatch.setattr(do_thi, "TRAN_NUT", 600)
    monkeypatch.setattr(do_thi, "DONG_TOI_THIEU", 3)
    assert _dong(do_thi.do_thi(goc)) == {}


def test_khong_co_kho_va_chi_doc(tmp_path):
    trong = str(tmp_path / "trong")
    du = do_thi.do_thi(trong)
    assert not du["co_kho"] and len(du["nut"]) == 16 and len(du["day"]) == 15
    assert do_thi.song(trong)["xung"] == [] and not os.path.exists(C.duong_db(trong))
    goc, ids = _nao(tmp_path / "nao-gia")
    with open(C.duong_db(goc), "rb") as tep:
        truoc = tep.read()
    assert do_thi.do_thi(goc)["co_kho"] and do_thi.song(goc)["con_tro"]["tu"] and do_thi.no_ron(goc, ids["X"])
    with open(C.duong_db(goc), "rb") as tep:
        assert tep.read() == truoc                                      # kết nối chỉ đọc: kho không đổi một byte


# ── xung ─────────────────────────────────────────────────────────────────────

def test_song_tang_dan_theo_con_tro(tmp_path, monkeypatch):
    goc, ids = _nao(tmp_path)
    dau = do_thi.song(goc)                                              # lần đầu: chỉ 10 phút qua
    assert sorted(x["loai"] for x in dau["xung"]) == ["chon", "ket_qua"]
    assert next(x for x in dau["xung"] if x["loai"] == "ket_qua")["ket"] == "thang"
    with _db(goc) as con:
        dinh = con.execute("SELECT MAX(id) FROM su_kien").fetchone()[0]
    ct = dau["con_tro"]
    assert ct == {"tu": dinh, "dung": 0, "ngu": 0}
    assert do_thi.song(goc, ct["tu"], ct["dung"], ct["ngu"])["xung"] == []
    assert nbp.ghi(goc, "giong-doc", "loi", kenh="KA", ma_goi="KA-0005", noi_dung="lỗi X đọc hỏng", khoa="x5",
                   luc=time.time() - 5 * NGAY)                         # lúc cũ vẫn là xung MỚI (theo id)
    with _db(goc) as con:
        con.execute("INSERT INTO dung(quyet_dinh, bo_phan, bai_hoc, doi_chung, luc) VALUES (?,?,?,?,?)",
                    ("KA-0006:kich_ban:2026-10-13", "giong-doc", json.dumps([ids["L"]]), 0, time.time()))
        con.execute("INSERT INTO giac_ngu(luc, bo_phan, tu_id, den_id, de_xuat, ap, bo, giay, chi_tiet, loi) "
                    "VALUES (?,?,?,?,?,?,?,?,?, '')", (time.time(), "giong-doc", 1, 9, 2, 1, 1, 3.0,
                                                       json.dumps({"ap": [{"lenh": "them", "id": "BH-Naaaa002"}]})))
    moi = do_thi.song(goc, ct["tu"], ct["dung"], ct["ngu"])
    theo = {x["loai"]: x for x in moi["xung"]}
    assert sorted(theo) == ["dung", "loi", "ngu"] and len(moi["xung"]) == 3
    assert theo["loi"]["no_ron"] == [ids["X"]] and theo["loi"]["kenh"] == "KA" and theo["loi"]["id"] == dinh + 1
    assert theo["dung"]["no_ron"] == [ids["L"]] and theo["dung"]["kenh"] == "KA" and theo["dung"]["id"] == "d1"
    assert theo["ngu"]["no_ron"] == [ids["L2"]] and "áp 1/2" in theo["ngu"]["chu"]
    assert moi["con_tro"] == {"tu": dinh + 1, "dung": 1, "ngu": 1} and moi["dem"]["ngu_cuoi"]
    ct = moi["con_tro"]
    assert do_thi.song(goc, ct["tu"], ct["dung"], ct["ngu"])["xung"] == []
    monkeypatch.setattr(do_thi, "TRAN_XUNG", 3)                        # tồn đọng → chỉ xung mới nhất
    for i in range(5):
        assert nbp.ghi(goc, "dieu-phoi", "do", noi_dung="nhịp %d" % i, khoa="n%d" % i)
    ton = do_thi.song(goc, ct["tu"], ct["dung"], ct["ngu"])
    assert [x["chu"] for x in ton["xung"]] == ["nhịp 2", "nhịp 3", "nhịp 4"] and ton["con_tro"]["tu"] == dinh + 6
    assert do_thi.song(goc, 10 ** 9)["con_tro"]["tu"] == dinh + 6      # kho dựng lại (id lùi) → như lần đầu


# ── chữ một nốt ──────────────────────────────────────────────────────────────

def test_no_ron_chan_lach_thu_muc(tmp_path):
    goc, ids = _nao(tmp_path)
    x = do_thi.no_ron(goc, ids["X"])
    assert x["dau"]["loai"] == "loi" and "## Quan sát" in x["than"] and x["id"] == ids["X"]
    assert do_thi.no_ron(goc, "_ban-do")["dau"]["loai"] == "ban-do"
    assert do_thi.no_ron(goc, "giong-doc/so-tay")["than"].startswith("# Sổ tay")
    assert do_thi.no_ron(goc, "thuc-the/kenh/KA")["dau"]["loai"] == "kenh"
    with io.open(os.path.join(goc, "nao", "bi-mat.md"), "w", encoding="utf-8") as tep:
        tep.write("---\nloai: bi-mat\n---\nkhông được đọc\n")
    for xau in ("../bi-mat", "giong-doc/../../bi-mat", "../bo-phan", "..", ".", "", "/giong-doc/so-tay",
                "giong-doc//so-tay", "giong-doc/./so-tay", "giong-doc\\so-tay", "..\\bi-mat", "C:/Windows/win",
                "giong-doc/so-tay\x00", "khong-co/loi/abc", "x" * 400):
        assert do_thi.no_ron(goc, xau) is None, xau


# ── đường 8790 ───────────────────────────────────────────────────────────────

@contextlib.contextmanager
def _may_chu():
    from core import truc_quan
    sv = ThreadingHTTPServer(("127.0.0.1", 0), truc_quan._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        yield "http://127.0.0.1:{0}".format(sv.server_address[1])
    finally:
        sv.shutdown()
        sv.server_close()


def _lay(url):
    r = urllib.request.urlopen(url, timeout=20)
    return r.headers["Content-Type"], r.read()


def test_duong_json_qua_bo_xu_ly(tmp_path, monkeypatch):
    from core import truc_quan
    goc, ids = _nao(tmp_path)
    monkeypatch.setattr(truc_quan, "GOC", goc)
    monkeypatch.setattr(do_thi, "_NHO", {"luc": 0.0, "du": None, "goc": ""})
    with _may_chu() as url:
        loai, du = _lay(url + "/nao-bo-phan/do-thi.json")
        du = json.loads(du)
        assert loai.startswith("application/json") and du["co_kho"] and ids["X"] in {n["id"] for n in du["nut"]}
        assert len(du["nut"]) == len(do_thi.do_thi(goc)["nut"])
        s = json.loads(_lay(url + "/nao-bo-phan/song.json")[1])
        ct = s["con_tro"]
        assert len(s["xung"]) == 2 and ct["tu"] > 0
        assert json.loads(_lay(url + "/nao-bo-phan/song.json?tu={tu}&dung={dung}&ngu={ngu}".format(**ct))[1])[
            "xung"] == []
        assert json.loads(_lay(url + "/nao-bo-phan/song.json?tu=abc")[1])["con_tro"]["tu"] == ct["tu"]
        x = json.loads(_lay(url + "/nao-bo-phan/no-ron.json?id=" + urllib.parse.quote(ids["X"]))[1])
        assert x["dau"]["loai"] == "loi"
        for xau in ("/nao-bo-phan/no-ron.json?id=..%2Fbo-phan", "/nao-bo-phan/no-ron.json?id=..%5C..%5Cx",
                    "/nao-bo-phan/no-ron.json", "/nao-bo-phan/la.json"):
            with pytest.raises(urllib.error.HTTPError) as loi:
                urllib.request.urlopen(url + xau, timeout=20)
            assert loi.value.code == 404, xau


def test_trang_do_thi_va_thu_vien_tu_chua():
    from core import truc_quan
    with _may_chu() as url:
        loai, trang = _lay(url + "/nao-do-thi")
        trang = trang.decode("utf-8")
        assert loai.startswith("text/html") and 'class="tab on" href="/nao-do-thi"' in trang
        assert "/vendor/force-graph.min.js" in trang and "/nao-bo-phan/song.json" in trang
        assert "/nao-bo-phan/no-ron.json" in trang and "emitParticle" in trang
        assert "/nao.json" in _lay(url + "/nao")[1].decode("utf-8")         # tab Não cũ vẫn đúng trang
        loai, js = _lay(url + "/vendor/force-graph.min.js")
        assert loai.startswith("text/javascript") and js.startswith(b"/*! force-graph 1.52.0") and b"MIT License" in js
    assert not re.search(r"""(src|href)=["']https?://""", trang)            # không tải gì từ mạng ngoài
    for duong in re.findall(r"""(?:src|href)=["']/vendor/([^"'?]+)""", trang):
        assert os.path.isfile(os.path.join(truc_quan.VENDOR, duong)), duong
    for ten in ("chien-truong.html", "truc-quan.html", "nao.html", "phong-thi-nghiem.html", "gioi-thieu.html"):
        with io.open(os.path.join(truc_quan.GOC, "ui_web", ten), encoding="utf-8") as tep:
            assert 'href="/nao-do-thi"' in tep.read(), ten
