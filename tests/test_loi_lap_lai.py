"""Sổ tay lỗi lặp lại (`core/loi_lap_lai.py`) — dữ liệu dựng tay, không mạng, không đụng máy thật."""
import datetime as _dt
import json
import os

from core import loi_lap_lai as ll


def _ghi(p, du):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def test_la_loi_bo_dong_thong_tin():
    assert ll.la_loi("[HỎNG] Dừng ở “Tạo clip từng cảnh”.")
    assert ll.la_loi("cảnh 4: máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá mới (1/2).")
    assert not ll.la_loi("clip: 5 xong (3 đã có sẵn, không làm lại).")
    assert not ll.la_loi("cảnh 3: máy chủ vẫn đang làm, đã đợi 5 phút…")
    assert not ll.la_loi("kéo chéo DOM [that]: 3 việc · ok 3 · lỗi 0 · mã 0")


def test_mau_gop_bien_the_va_phan_lop():
    a = ll.mau_loi("[TL1-T7] cảnh 12: máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá mới (1/2).", ["TL1-T7"])
    b = ll.mau_loi("cảnh 99: máy chủ nhận việc rồi bỏ đó — đặt lại bằng khoá mới (2/2).", ["TL1-T7"])
    assert a == b
    assert ll.phan_lop(a) == "shopapi_tam"
    assert ll.phan_lop("ERROR: [youtube] abc: Video unavailable") == "nguon_mat"
    assert ll.phan_lop("chưa xong hết — Dừng ở “Tạo clip từng cảnh”: cảnh 3 không làm được clip thật") == "luot_ket"


def test_dao_dem_mot_lan_moi_su_viec(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "cai-dat-tool.json"), {"kenh": {"TL1-T7": {}}})
    bay = _dt.datetime(2026, 10, 17, 12, 0)
    dong = "\n".join("[2026-10-17 10:{0:02d}:00] [TL1-T7] cảnh {0}: máy chủ treo 2 lần với cùng ảnh + lời nhắc".format(i)
                     for i in range(0, 30, 3))
    _ghi(os.path.join(goc, "workspace", "tu-chay", "tu-chay.log"), dong + "\n")
    _ghi(os.path.join(goc, "workspace", "tu-chay", "dieu-phoi-TL1-T7.log"), dong + "\n")   # cùng sự việc ghi 2 nơi
    kq = ll.dao(goc, bay=bay.timestamp())
    g = kq["nhom"][0]
    assert g["so"] == 10 and g["kenh"] == {"TL1-T7": 10} and g["bai"] == "shopapi_tam"
    assert "Top" in ll.bang_md(kq)


def test_viec_doi_lau():
    so = [{"luc": "2026-10-17 01:35:00", "ma": "D13", "kenh": "TL1-T7", "quyet": "bo_qua", "ly_do": "khoá máy bận"},
          {"luc": "2026-10-17 05:35:00", "ma": "D13", "kenh": "TL1-T7", "quyet": "hoan", "ly_do": "hoãn"},
          {"luc": "2026-10-17 01:35:00", "ma": "D15", "kenh": "TL2-T7", "quyet": "bo_qua", "ly_do": "x"},
          {"luc": "2026-10-17 03:35:00", "ma": "D15", "kenh": "TL2-T7", "quyet": "xong", "ly_do": "đạt"}]
    ra = ll.viec_doi_lau(so, _dt.datetime(2026, 10, 17, 9, 0))
    assert [(x["ma"], x["kenh"]) for x in ra] == [("D13", "TL1-T7")] and ra[0]["gio"] >= 7


def _so_luot(goc, kenh, ngay, run):
    _ghi(os.path.join(goc, "CHANNEL", kenh, "tu-chay", ngay + ".json"), {"ngay": ngay, "kenh": kenh, "runs": [run]})


def test_luot_ket_nguon_mat_can_hai_bang_chung(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "cai-dat-tool.json"), {"kenh": {"TL1-T7": {}}})
    bay = _dt.datetime(2026, 10, 17, 12, 0).timestamp()
    _so_luot(goc, "TL1-T7", "2026-10-17", {"ma_luot": "0032", "nguon": {"ma": "87AWiO-Zna4"},
                                           "phuc_hoi": {"so_lan": 12, "lan_dau_luc": bay - 40 * 3600},
                                           "san_xuat": {"loi_dung": "Dừng ở “Viết kịch bản”: không lấy được lời thoại"}})
    goi = []
    # chưa có dòng log → không bỏ
    ra = ll.sua_luot_ket(goc, bay=bay, kiem_nguon=lambda v: True, bo_luot=lambda *a: goi.append(a) or (True, "ok"))
    assert ra[0]["quyet"] in ("bao", "cho") and not goi
    _ghi(os.path.join(goc, "workspace", "tu-chay", "dieu-phoi-TL1-T7.log"),
         "ERROR: [youtube] 87AWiO-Zna4: Video unavailable\n")
    ra = ll.sua_luot_ket(goc, bay=bay, kiem_nguon=lambda v: True, bo_luot=lambda *a: goi.append(a) or (True, "ok"))
    assert ra[0]["quyet"] == "bo" and ra[0]["da_bo"] and goi[0][1:4] == ("TL1-T7", "2026-10-17", "0032")
    # --thu không bỏ
    goi.clear()
    ll.sua_luot_ket(goc, thu=True, bay=bay, kiem_nguon=lambda v: True, bo_luot=lambda *a: goi.append(a) or (True, ""))
    assert not goi


def test_luot_ket_clip_bo_sau_72_gio(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "cai-dat-tool.json"), {"kenh": {"TL6-T7": {}}})
    bay = _dt.datetime(2026, 10, 17, 12, 0).timestamp()
    run = {"ma_luot": "0012", "phuc_hoi": {"so_lan": 67, "lan_dau_luc": bay - 30 * 3600},
           "san_xuat": {"loi_dung": "cảnh 138 không làm được clip thật — cần người xem"}}
    _so_luot(goc, "TL6-T7", "2026-10-15", run)
    assert ll.sua_luot_ket(goc, bay=bay, bo_luot=lambda *a: (True, ""))[0]["quyet"] == "bao"
    run["phuc_hoi"]["lan_dau_luc"] = bay - 80 * 3600
    _so_luot(goc, "TL6-T7", "2026-10-15", run)
    assert ll.sua_luot_ket(goc, bay=bay, bo_luot=lambda *a: (True, ""))[0]["quyet"] == "bo"
    run["bo"] = True
    _so_luot(goc, "TL6-T7", "2026-10-15", run)
    assert ll.sua_luot_ket(goc, bay=bay) == []


def test_trang_xem_hong():
    assert ll.trang_xem_hong("87AWiO-Zna4", tai=lambda u: b'"playabilityStatus":{"status":"ERROR"}') is True
    assert ll.trang_xem_hong("87AWiO-Zna4", tai=lambda u: b'"playabilityStatus":{"status":"OK"}') is False
    assert ll.trang_xem_hong("87AWiO-Zna4", tai=lambda u: None) is None
    assert ll.trang_xem_hong("xấu") is None
