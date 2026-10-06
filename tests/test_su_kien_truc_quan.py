"""Chiến báo của Trung tâm trực quan (dữ liệu giả, thư mục tạm): video ta lên sóng, lệnh/chấm của não, sự cố,
kho clip; mỗi nguồn hỏng riêng không làm vỡ cả gói; chỉ đọc; che khoá."""
import datetime as dt
import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from core import su_kien_truc_quan as sk

BAY = dt.datetime(2026, 10, 6, 11, 0, 0)


def _ghi(p, chu):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)


def _gia(tmp_path):
    g = str(tmp_path)
    _ghi(os.path.join(g, "vm", "cai-dat-tool.json"), json.dumps({"kenh": {"KA-B": {}, "KA-B-K2": {}}}))
    _ghi(os.path.join(g, "vm", "logs", "so-video-id.json"), json.dumps({
        "KA-B/KA-B-0001": {"video_id": "vid1", "lich": "06/10/2026 05:00"},
        "KA-B/KA-B-0002": {"video_id": "vid2", "lich": "07/10/2026 05:00"},          # chưa tới giờ → chưa tấn công
        "KA-B/KA-B-0000": {"video_id": "vid0", "lich": "01/09/2026 05:00"},          # quá 14 ngày
        "KA-B-K2/KA-B-K2-0001": {"video_id": "", "lich": "05/10/2026 05:00"},        # chưa có id
        "hong": {"video_id": "x"},
    }))
    _ghi(os.path.join(g, "CHANNEL", "KA-B", "ke-hoach-dang", "ke-hoach.csv"),
         "Mã gói,Ngày đăng,Giờ đăng,Tiêu đề\nKA-B-0001,06/10/2026,05:00,【心理学】静かに離れる人\n")
    _ghi(os.path.join(g, "nao", "hanh-dong.json"), json.dumps([
        {"id": "n001", "luc": "2026-10-03T04:12:00", "lenh": "thu", "tham_so": {"kenh": "KA-B", "truc": "cum", "gia_tri": "x"},
         "du_doan": "2 video kế CTR ≥ 5%", "kiem_ngay": "2026-10-05", "trang_thai": "xong", "cham": "dung",
         "ghi_chu_cham": "CTR 6,1%", "cham_luc": "2026-10-05T04:20:00"},
        {"id": "n002", "luc": "2026-10-06T04:12:00", "lenh": "de-xuat", "tham_so": {"noi_dung": "khoá sk-" + "abcdefghijklmnopqrstu"},
         "du_doan": "có ích", "kiem_ngay": "2026-10-09", "trang_thai": "mo", "cham": None},
    ], ensure_ascii=False))
    _ghi(os.path.join(g, "workspace", "loi-chay-max.md"), "\n".join([
        "# Sổ lỗi",
        "- [2026-10-06 02:32] **thuong** — Lượt KA-B-K2 hỏng khâu clip.",
        "- [2026-10-06 03:00] **nhac** — chỉ nhắc, bỏ.",
        "- [2026-09-01 03:00] **khan** — quá cũ.",
        "- [2026-10-05 22:00] **khan** — Máy quá tải.",
    ]) + "\n")
    _ghi(os.path.join(g, "workspace", "tu-chay", "tu-chay.log"), "\n".join([
        "[2026-10-05 23:00:00] [KA-B]   kho clip của cổng hết hạn mức hôm nay — hôm qua, không tính",
        "[2026-10-06 08:08:01] [KA-B]   kho clip của cổng hết hạn mức hôm nay — làm nốt ảnh đã",
        "[2026-10-06 09:00:00] [KA-B]   viết kịch bản",
        "[2026-10-06 10:36:10] [KA-B]   kho clip của cổng hết hạn mức — còn 200 cảnh chưa có clip; chờ engine",
    ]) + "\n")
    _ghi(os.path.join(g, "workspace", "tu-chay", "cho-clip", "KA-B.json"),
         json.dumps({"pid": 1, "kenh": "KA-B", "han": "2026-10-06T23:00:00", "tu": "2026-10-06T10:15:57", "luc": BAY.timestamp() - 60}))
    _ghi(os.path.join(g, "workspace", "tu-chay", "cho-clip", "KA-B-K2.json"),
         json.dumps({"pid": 2, "kenh": "KA-B-K2", "han": "2026-10-06T23:00:00", "luc": BAY.timestamp() - 3 * 3600}))   # ôi → bỏ
    return g


def _anh_chup(g):
    ra = {}
    for goc_con, _t, cac in os.walk(g):
        for t in cac:
            with open(os.path.join(goc_con, t), "rb") as tep:
                ra[os.path.join(goc_con, t)] = tep.read()
    return ra


def test_tinh_du_nguon_moi_den_cu_va_chi_doc(tmp_path):
    g = _gia(tmp_path)
    truoc = _anh_chup(g)
    d = sk.tinh(g, BAY, phan_cum=lambda td: "lang-le" if "離れる" in td else "")
    assert _anh_chup(g) == truoc
    assert d["kenh"] == ["KA-B", "KA-B-K2"] and d["loi_nguon"] == {}
    ds = d["su_kien"]
    assert [x["luc"] for x in ds] == sorted((x["luc"] for x in ds), reverse=True)
    tc = [x for x in ds if x["loai"] == "tan_cong"]
    assert len(tc) == 1 and tc[0]["kenh"] == "KA-B" and tc[0]["tieu_de"] == "【心理学】静かに離れる人"
    assert tc[0]["cum"] == "lang-le" and tc[0]["link"].endswith("vid1") and tc[0]["luc"] == "2026-10-06 05:00"
    lenh = {x["ma"]: x for x in ds if x["loai"] == "lenh_nao"}
    assert set(lenh) == {"n001", "n002"} and lenh["n001"]["kenh"] == "KA-B"
    cham = [x for x in ds if x["loai"] == "cham_nao"]
    assert len(cham) == 1 and cham[0]["ket"] == "dung" and cham[0]["luc"] == "2026-10-05 04:20"
    sc = [x for x in ds if x["loai"] == "su_co"]
    assert [x["luc"] for x in sc] == ["2026-10-06 02:32", "2026-10-05 22:00"]
    assert sc[0]["kenh"] == "KA-B-K2" and sc[1]["kenh"] == ""          # mã dài khớp trước mã ngắn
    hc = [x for x in ds if x["loai"] == "het_clip"]
    assert len(hc) == 1 and hc[0]["luc"] == "2026-10-06 08:08"
    kho = d["kho_clip"]
    assert kho["can"] and kho["tu"] == "2026-10-06 08:08:01" and kho["cuoi"] == "2026-10-06 10:36:10"
    assert kho["kenh_cho"] == [{"kenh": "KA-B", "han": "2026-10-06 23:00", "tu": "2026-10-06 10:15"}]
    assert "abcdefghijklmnop" not in json.dumps(d, ensure_ascii=False)          # khoá bị che


def test_nguon_hong_chi_bao_loi_nguon_do(tmp_path, monkeypatch):
    g = _gia(tmp_path)
    monkeypatch.setattr(sk, "lenh_nao", lambda goc, bay: 1 / 0)
    d = sk.tinh(g, BAY, phan_cum=lambda td: "")
    assert "ZeroDivisionError" in d["loi_nguon"]["lenh_nao"]
    assert any(x["loai"] == "tan_cong" for x in d["su_kien"])


def test_thieu_du_lieu_khong_vo(tmp_path):
    d = sk.tinh(str(tmp_path), BAY, phan_cum=lambda td: "")
    assert d["su_kien"] == [] and d["kho_clip"]["can"] is False and d["kho_clip"]["kenh_cho"] == []


def test_may_chu_phuc_vu_su_kien(tmp_path, monkeypatch):
    from core import truc_quan
    g = _gia(tmp_path)
    monkeypatch.setattr(sk, "GOC", g)
    monkeypatch.setattr(sk, "_NHO", {"luc": 0.0, "du": None})
    monkeypatch.setattr(sk, "_phan_cum_mac_dinh", lambda goc: None)
    sv = ThreadingHTTPServer(("127.0.0.1", 0), truc_quan._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        du = json.loads(urllib.request.urlopen("http://127.0.0.1:{0}/su-kien.json".format(sv.server_address[1]),
                                               timeout=30).read().decode("utf-8"))
        assert du["kenh"] == ["KA-B", "KA-B-K2"] and isinstance(du["su_kien"], list) and "kho_clip" in du
    finally:
        sv.shutdown()
        sv.server_close()
