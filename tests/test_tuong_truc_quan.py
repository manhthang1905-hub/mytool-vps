"""Vòng 4 Trung tâm trực quan (dữ liệu giả, thư mục tạm): hồ sơ tướng, lịch sử trận, kinh tế, đồng hồ, đầy đủ,
đường ảnh bìa/logo kiểm chặt (chặn lách thư mục), chỉ đọc, nguồn hỏng không vỡ."""
import datetime as dt
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from core import tuong_truc_quan as tq

BAY = dt.datetime(2026, 10, 6, 12, 0, 0)


def _ghi(p, chu, nhi=False):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb" if nhi else "w", **({} if nhi else {"encoding": "utf-8", "newline": "\n"})) as tep:
        tep.write(chu)


def _gia(tmp_path):
    g = str(tmp_path)
    _ghi(os.path.join(g, "vm", "cai-dat-tool.json"), json.dumps({"gio_phien": "07:30", "kenh": {"KA-B": {}, "KC-D": {"quet_ngay_gio": "03:33"}}}))
    _ghi(os.path.join(g, "vm", "agent.py"), 'QUET_NGAY_GIO_MAC_DINH = "02:10"\nQUET_NGAY_CACH_PHUT = 30\nGIO_KEO_CHEO = (9, 20)\n')
    k = os.path.join(g, "CHANNEL", "KA-B")
    _ghi(os.path.join(k, "kenh.yaml"), 'ten: "Kenh A — mo ta"\nnhip_dang: "05:00"\n')
    _ghi(os.path.join(k, "ke-hoach-dang", "ke-hoach.csv"),
         "Mã gói,Ngày đăng,Giờ đăng,Tiêu đề\nKA-B-0001,03/10/2026,05:00,Tran mot\nKA-B-0002,04/10/2026,05:00,Tran hai\n"
         "KA-B-0003,05/10/2026,05:00,Tran ba\nKA-B-0009,09/10/2026,05:00,Chua len song\n")
    for ma, hs in (("KA-B-0001", {"chi_so": {"48h": {"impressions": 1200, "ctr": 4.5, "views": 80}}}),
                   ("KA-B-0002", {"chi_so": {"72h": {"impressions": 300, "ctr": 2.0}}}),
                   ("KA-B-0003", {}), ("KA-B-0009", {})):
        _ghi(os.path.join(k, "ho-so-video", ma + ".json"), json.dumps(dict(hs, ma_goi=ma, video_id="v" + ma[-1])))
    _ghi(os.path.join(k, "ho-so-video", "anh", "KA-B-0001.jpg"), b"\xff\xd8jpg", True)
    _ghi(os.path.join(k, "thiet-lap", "logo.png"), b"\x89PNG", True)
    _ghi(os.path.join(g, "CHANNEL", "bi-mat.jpg"), b"x", True)
    _ghi(os.path.join(k, "tu-hoc", "van.json"), json.dumps({"KA-B-0001": {"ket48": "thang"}, "KA-B-0002": {"ket48": "truot"},
                                                           "KA-B-0003": {"khong_do": "2026-10-06"}}))
    _ghi(os.path.join(k, "chi-so", "kenh-theo-ngay.csv"),
         "Lúc chụp,Lượt xem,Giờ xem,Đăng ký,Lượt hiển thị,Tỷ lệ bấm\n2026-10-05 02:00,100,10,5,900,3.1\n2026-10-06 02:00,150,12.5,7,1200,3.4\n")
    _ghi(os.path.join(g, "workspace", "vi", "so-du.json"), json.dumps({"luc": BAY.timestamp(), "vnd": 900000}))
    _ghi(os.path.join(g, "workspace", "vi", "trang-thai.json"), json.dumps({"danh_gia": {"uoc_video_vnd": 100000, "du_video": 9, "muc": "ok"}}))
    t0 = dt.datetime(2026, 10, 5, 10).timestamp()
    _ghi(os.path.join(g, "workspace", "vi", "lich-su-so-du.jsonl"), "".join(json.dumps({"luc": t0 + i * 3600 * 6, "vnd": v}) + "\n"
                                                                         for i, v in enumerate([1000000, 980000, 970000, 950000, 900000])))
    _ghi(os.path.join(g, "workspace", "tu-chay", "dieu-phoi-KA-B.log"), "[2026-10-06 08:00:00] [KA-B]   cổng khai trần job cùng lúc: ảnh 9, clip 4, giọng 2 (x)\n")
    _ghi(os.path.join(g, "workspace", "tu-chay", "tu-chay.log"), "[2026-10-06 09:15:00] [KA-B]   kho clip của cổng hết hạn mức hôm nay\n")
    _ghi(os.path.join(g, "workspace", "tu-chay", "cho-clip", "KA-B.json"), json.dumps({"kenh": "KA-B", "han": "2026-10-06T23:00:00", "luc": BAY.timestamp() - 60}))
    _ghi(os.path.join(g, "vm", "logs", "cmt-dom.log"), "2026-10-06 07:39:56,524 INFO: kênh KA-B: trả lời 3 · bỏ qua 1 · lỗi 0\n"
                                                      "2026-10-05 07:39:56,524 INFO: kênh KA-B: trả lời 9 · bỏ qua 0 · lỗi 0\n")
    _ghi(os.path.join(g, "vm", "logs", "nuoi-trang-chu", "KA-B.json"), json.dumps({"trang_thai": "dat", "lan_do": [{"luc": "x", "pct_chu_de": 95.0}]}))
    _ghi(os.path.join(g, "workspace", "keo-cheo", "da-them.json"), json.dumps({"muc": [{"ngay": "2026-10-06", "kenh_chu": "KC-D", "kenh_video": "KA-B", "ket": "ok",
                                                                                  "du_doan": {"kiem_sau_ngay": 7}, "do_sau": {"ket": "keo_duoc", "tang": 50}}]}))
    _ghi(os.path.join(g, "workspace", "bao-cao-ngay", "2026-10-06.md"), "# Báo cáo\n- dòng sk-" + "abcdefghijklmnopqrstuv\n")
    return g


def _anh_chup(g):
    ra = {}
    for goc_con, _t, cac in os.walk(g):
        for t in cac:
            with open(os.path.join(goc_con, t), "rb") as tep:
                ra[os.path.join(goc_con, t)] = tep.read()
    return ra


def test_ho_so_tuong_tran_va_chuoi(tmp_path, monkeypatch):
    g = _gia(tmp_path)
    monkeypatch.setattr(tq, "cay_ky_nang", lambda goc, kenh: [{"ma": "K01", "tt": "dat"}])
    monkeypatch.setattr(tq, "_hoc", lambda goc, kenh, bay: {"van": 3})
    truoc = _anh_chup(g)
    d = tq.ho_so_tuong(g, "KA-B", BAY)
    assert _anh_chup(g) == truoc
    assert d["ten"] == "Kenh A" and d["logo"] is True and d["nhip_dang"] == "05:00"
    assert d["chi_so"]["gio"] == 12.5 and d["chi_so"]["dang_ky"] == 7
    tran = {t["ma"]: t for t in d["tran"]}
    assert "KA-B-0009" not in tran                                   # chưa lên sóng
    assert [t["ma"] for t in d["tran"]] == ["KA-B-0003", "KA-B-0002", "KA-B-0001"]
    assert tran["KA-B-0001"]["ket"] == "thang" and tran["KA-B-0001"]["hien_thi"] == 1200 and tran["KA-B-0001"]["anh"]
    assert tran["KA-B-0002"]["ket"] == "thua" and tran["KA-B-0002"]["moc"] == "72h"
    assert tran["KA-B-0003"]["ket"] == "khong_do"
    tt = d["thanh_tich"]
    assert (tt["so_tran"], tt["thang"], tt["ti_le"], tt["chuoi"], tt["chuoi_loai"]) == (2, 1, 50.0, 1, "thua")
    assert d["binh_luan"] == {"tra_loi": 3, "bo_qua": 1, "loi": 0, "phien": 1}
    assert "ypp" in d and d["ky_nang"][0]["ma"] == "K01"
    assert tq.ho_so_tuong(g, "KHONG-CO", BAY) == {"loi": "không có kênh này"}


def test_duong_anh_chan_lach(tmp_path):
    g = _gia(tmp_path)
    assert tq.duong_anh(g, "bia", "KA-B", "KA-B-0001").endswith("KA-B-0001.jpg")
    assert tq.duong_anh(g, "logo", "KA-B").endswith("logo.png")
    for loai, k, ma in (("bia", "KA-B", "../../bi-mat"), ("bia", "KA-B", "..\\x"), ("bia", "..", "bi-mat"), ("bia", "KX", "KA-B-0001"),
                        ("bia", "KA-B", "KA-B-0002"), ("logo", "KC-D", ""), ("khac", "KA-B", "KA-B-0001"), ("bia", "KA-B", "")):
        assert tq.duong_anh(g, loai, k, ma) is None, (loai, k, ma)


def test_kinh_te_dong_ho_day_du(tmp_path):
    g = _gia(tmp_path)
    kt = tq.kinh_te(g, BAY)
    assert kt["vi"]["so_du"] == 900000 and kt["vi"]["chi_hom_qua"] == 30000 and kt["vi"]["chi_hom_nay"] == 70000
    assert kt["tran_job"] == {"luc": "2026-10-06 08:00:00", "anh": 9, "clip": 4, "giong": 2}
    assert kt["het_han_muc"]["clip"] == "2026-10-06 09:15:00" and kt["loi_nguon"] == {}
    dh = tq.dong_ho(g, BAY)
    gio = {(e["loai"], e["kenh"]): e["gio"] for e in dh["su_kien"]}
    assert gio[("quet", "KA-B")] == "02:10" and gio[("quet", "KC-D")] == "03:33"
    assert gio[("len_song", "KA-B")] == "05:00" and gio[("phien", "KA-B,KC-D")] == "07:30" and gio[("han_clip", "KA-B")] == "23:00"
    assert any(e["loai"] == "keo_cheo" and e["gio"] == "09:00" and e["den"] == "20:00" for e in dh["su_kien"])
    dd = tq.day_du(g, BAY)
    assert dd["binh_luan"]["KA-B"]["tra_loi"] == 3
    assert dd["keo_cheo"][0]["do"]["ket"] == "keo_duoc" and dd["nuoi"]["KA-B"]["pct_chu_de"] == 95.0
    assert dd["bao_cao"]["moi_nhat"] == "2026-10-06" and "abcdefghijklmnop" not in dd["bao_cao"]["noi_dung"]
    assert dd["tran"]["KA-B"]["thanh_tich"]["thang"] == 1 and dd["tran"]["KA-B"]["max_hien_thi"] == 1200


def test_thieu_du_lieu_khong_vo(tmp_path):
    g = str(tmp_path)
    assert tq.kinh_te(g, BAY)["vi"]["so_du"] is None
    assert tq.dong_ho(g, BAY)["su_kien"] is not None
    assert tq.day_du(g, BAY)["kenh"] == []


@pytest.fixture()
def may_chu(tmp_path, monkeypatch):
    from core import truc_quan
    g = _gia(tmp_path)
    monkeypatch.setattr(tq, "GOC", g)
    monkeypatch.setattr(tq, "_NHO", {})
    monkeypatch.setattr(tq, "cay_ky_nang", lambda goc, kenh: [])
    sv = ThreadingHTTPServer(("127.0.0.1", 0), truc_quan._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        yield "http://127.0.0.1:{0}".format(sv.server_address[1])
    finally:
        sv.shutdown()
        sv.server_close()


def test_may_chu_duong_moi(may_chu):
    d = json.loads(urllib.request.urlopen(may_chu + "/tuong.json?kenh=KA-B", timeout=30).read().decode("utf-8"))
    assert d["kenh"] == "KA-B" and d["tran"]
    for u in ("/kinh-te.json", "/dong-ho.json", "/day-du.json"):
        assert isinstance(json.loads(urllib.request.urlopen(may_chu + u, timeout=30).read().decode("utf-8")), dict)
    r = urllib.request.urlopen(may_chu + "/anh-bia/KA-B/KA-B-0001.jpg", timeout=10)
    assert r.headers["Content-Type"] == "image/jpeg" and r.read() == b"\xff\xd8jpg"
    assert urllib.request.urlopen(may_chu + "/logo/KA-B.png", timeout=10).headers["Content-Type"] == "image/png"
    for xau in ("/anh-bia/KA-B/..%2F..%2Fbi-mat.jpg", "/anh-bia/../CHANNEL/bi-mat.jpg", "/anh-bia/KA-B/KA-B-0002.jpg",
                "/logo/KC-D.png", "/anh-bia/KA-B/KA-B-0001.png", "/logo/..%2Fbi-mat.png"):
        with pytest.raises(urllib.error.HTTPError) as loi:
            urllib.request.urlopen(may_chu + xau, timeout=10)
        assert loi.value.code == 404, xau
