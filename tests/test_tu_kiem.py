"""Tự kiểm kết quả (`core/tu_kiem.py`) — mạng giả, dữ liệu dựng tay, không gửi báo động thật."""
import datetime as _dt
import io
import json
import os

import pytest

from core import tu_kiem as tk

BAY = _dt.datetime(2026, 10, 17, 12, 0)


def _ghi(p, du):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(du, f, ensure_ascii=False)


def _anh(p, mau):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1280, 720), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for i, (x, y) in enumerate(mau):
        d.rectangle([x, y, x + 300, y + 200], fill=(40 * i % 255, 0, 0))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p, "JPEG")
    with open(p, "rb") as f:
        return f.read()


@pytest.fixture(autouse=True)
def _khong_bao_that(monkeypatch):
    from core import bao_dong
    monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: True)
    # không bao giờ sinh tiến trình thật (bật lại vận hành / giấc ngủ não) trong test
    monkeypatch.setitem(tk.THU_LAI_BO_CHAY, "van_hanh", lambda K, m: (True, "giả"))
    monkeypatch.setitem(tk.THU_LAI_BO_CHAY, "nao_ngu", lambda K, m: (True, "giả"))


def _mang(bang):
    def tai(url):
        for k, v in bang.items():
            if k in url:
                return v
        return 404, b""
    return tai


def test_dang_cong_khai_va_rieng_tu(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), {
        "TL1-T7/TL1-T7-0031": {"video_id": "AAAAAAAAAAA", "lich": "17/10/2026 05:00"},
        "TL2-T7/TL2-T7-0030": {"video_id": "BBBBBBBBBBB", "lich": "17/10/2026 05:00"},
        "TL3-T7/TL3-T7-0028": {"video_id": "CCCCCCCCCCC", "lich": "17/10/2026 20:00"}})
    tai = _mang({"AAAAAAAAAAA": (200, json.dumps({"title": "t"}).encode()), "BBBBBBBBBBB": (401, b"")})
    K = tk.BoiCanh(goc, bay=BAY, tai=tai, kenh_ds=["TL1-T7", "TL2-T7", "TL3-T7"], so={})
    tt = {m["kenh"]: m["tt"] for m in tk.kiem_dang(K)}
    assert tt == {"TL1-T7": tk.DAT, "TL2-T7": tk.HONG, "TL3-T7": tk.CHO}


def test_can_xac_minh_dien_thoai_thanh_viec_nguoi(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "can-xac-minh-dt.json"), {
        "TL5-T7": {"tu": "2026-10-17 01:33:01", "lan_cuoi": "2026-10-17 07:40:33", "ma": "TL5-T7-0001"},
        "TL9-T7": {"tu": "2026-10-17 01:00:00", "lan_cuoi": "2026-10-17 01:00:00", "ma": "TL9-T7-0001"}})
    K = tk.BoiCanh(goc, bay=BAY, tai=_mang({}), kenh_ds=["TL5-T7"], so={})
    ra = [m for m in tk.kiem_dang(K) if m["khoa"].startswith("xac-minh-dt:")]
    assert [m["kenh"] for m in ra] == ["TL5-T7"]
    assert ra[0]["nguoi"] is True and "youtube.com/verify" in ra[0]["can_lam"]


def test_doi_bia_so_van_tay_va_thu_lai(tmp_path, monkeypatch):
    goc = str(tmp_path)
    dung = os.path.join(goc, "bia", "dung.jpg")
    _anh(dung, [(100, 100), (700, 400)])
    khac = _anh(os.path.join(goc, "bia", "khac.jpg"), [(600, 50), (50, 450), (900, 300)])
    hang = [{"id": "x:bia", "buoc": "bia", "kenh": "TL1-T7", "ma_goi": "TL1-T7-0026", "video_id": "VVVVVVVVVVV",
             "anh": dung, "trang_thai": "xong", "them_luc": "2026-10-16T13:34:51", "ket_luc": "2026-10-16 13:36:52"}]
    _ghi(os.path.join(goc, "vm", "logs", "hang-sua.json"), {"viec": hang})
    with open(dung, "rb") as f:
        tai_dung = _mang({"VVVVVVVVVVV/maxres": (200, f.read())})
    K = tk.BoiCanh(goc, bay=BAY, tai=tai_dung, kenh_ds=["TL1-T7"], so={})
    m = tk.kiem_hang_sua(K)[0]
    assert m["tt"] == tk.DAT and m["lech"] <= tk.LECH_DAT
    K = tk.BoiCanh(goc, bay=BAY, tai=_mang({"VVVVVVVVVVV/maxres": (200, khac)}), kenh_ds=["TL1-T7"], so={})
    ds = tk.kiem_hang_sua(K)
    assert ds[0]["tt"] == tk.HONG
    from core import cong_chu
    monkeypatch.setattr(cong_chu, "kiem_dau", lambda p: "")
    tk.xu_ly(K, ds, {})
    assert ds[0]["tt"] == tk.THU_LAI
    with io.open(os.path.join(goc, "vm", "logs", "hang-sua.json"), encoding="utf-8") as f:
        assert json.load(f)["viec"][0]["trang_thai"] == "cho"


def test_tieu_de_khop_nfkc(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "hang-sua.json"), {"viec": [
        {"id": "t:tieu_de", "buoc": "tieu_de", "kenh": "TL1-T7", "video_id": "TTTTTTTTTTT", "tieu_de": "【脳科学】Ａ｜Ｂ",
         "trang_thai": "xong", "ket_luc": "2026-10-17 04:24:41"}]})
    K = tk.BoiCanh(goc, bay=BAY, tai=_mang({"TTTTTTTTTTT": (200, json.dumps({"title": "【脳科学】A|B"}).encode())}),
                   kenh_ds=["TL1-T7"], so={})
    assert tk.kiem_hang_sua(K)[0]["tt"] == tk.DAT


def test_dsp_trang_cong_khai(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "TL1-T7", "nghien-cuu", "danh-sach-phat.json"), {"danh_sach": [
        {"ten": "A", "ma": "p1", "da_them": ["v1aaaaaaaaa", "v2aaaaaaaaa"], "luc_tao": "2026-10-16 08:00:00",
         "doc_lai": {"ma": "PLxx"}}]})
    trang = '"videoId":"v1aaaaaaaaa"'.encode()
    K = tk.BoiCanh(goc, bay=BAY, tai=_mang({"playlist?list=PLxx": (200, trang)}), kenh_ds=["TL1-T7"], so={})
    ds = tk.kiem_dsp(K)
    assert ds[0]["tt"] == tk.HONG and ds[0]["thieu"] == ["v2aaaaaaaaa"]
    tk.xu_ly(K, ds, {})
    from core import danh_sach_phat as dsp
    assert dsp.doc(goc, "TL1-T7")["danh_sach"][0]["da_them"] == ["v1aaaaaaaaa"]


def test_ab_thieu_started(tmp_path, monkeypatch):
    from core.giam_doc import _tu_dong as td
    viec = [{"id": "m-1", "loai": td.LOAI_TEST_COMPARE, "kenh": "TL2-T7", "trang_thai": "xong",
             "cap_nhat": "2026-10-16T08:36:25", "ket": {"video": {"a": {"ket": "da_dat", "doc_lai": {}}}}},
            {"id": "m-2", "loai": td.LOAI_AB_TIEU_DE, "kenh": "TL2-T7", "trang_thai": "cho",
             "tao_luc": "2026-10-15T00:00:00", "video_ids": ["b"]}]
    monkeypatch.setattr(td, "doc_viec_may_kieu", lambda goc, loai=None, tt=None: viec)
    K = tk.BoiCanh(str(tmp_path), bay=BAY, tai=_mang({}), kenh_ds=["TL2-T7"], so={})
    tt = {m["id_viec"]: m["tt"] for m in tk.kiem_ab(K)}
    assert tt == {"m-1": tk.HONG, "m-2": tk.HONG}


def test_ghim_cho_xac_minh_la_viec_nguoi(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), {"TL5-T7/TL5-T7-0010": {"video_id": "GGGGGGGGGGG",
                                                                                      "lich": "16/10/2026 05:00"}})
    _ghi(os.path.join(goc, "vm", "logs", "cmt-dom.json"), {"_kenh:TL5-T7": {"cho_xac_minh_tu": "2026-10-17 01:13:09"}})
    K = tk.BoiCanh(goc, bay=BAY, tai=_mang({}), kenh_ds=["TL5-T7"], so={})
    m = tk.kiem_ghim(K)[0]
    assert m["tt"] == tk.CHO and m["nguoi"]


def test_nhip_thieu_video_ngay_mai(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), {
        "TL1-T7/a": {"video_id": "x1", "lich": "15/10/2026 05:00"}, "TL1-T7/b": {"video_id": "x2",
                                                                           "lich": "16/10/2026 05:00"},
        "TL1-T7/c": {"video_id": "x3", "lich": "17/10/2026 05:00"}})
    monkeypatch.setattr(tk, "_kenh_tu_chay", lambda g, k: True)
    K = tk.BoiCanh(goc, bay=BAY.replace(hour=22), tai=_mang({}), kenh_ds=["TL1-T7"], so={})
    tt = {m["khoa"].split(":")[1]: m["tt"] for m in tk.kiem_nhip(K)}
    assert tt == {"mai": tk.HONG, "3ngay": tk.DAT}


def test_nhip_luot_ket_da_bo_thanh_tu_sua(tmp_path, monkeypatch):
    goc = str(tmp_path)
    monkeypatch.setattr(tk, "_kenh_tu_chay", lambda g, k: True)
    K = tk.BoiCanh(goc, bay=BAY.replace(hour=22), tai=_mang({}), kenh_ds=["TL1-T7"], so={})
    ds = tk.kiem_nhip(K)
    so_tay = {"luot_ket": [{"kenh": "TL1-T7", "ma_luot": "0032", "lop": "nguon_mat", "ly_do": "gỡ", "loi": "",
                            "da_bo": True}]}
    tk.xu_ly(K, ds, so_tay)
    assert {m["tt"] for m in ds} == {tk.TU_SUA}


def test_nhip_mot_luot_bao_gop_mot_lan_moi_ngay(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), {"TL2-T7/x": {"video_id": "BBBBBBBBBBB",
                                                                           "lich": "17/10/2026 05:00"}})
    goi = []
    from core import bao_dong
    monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **k: goi.append(a) or True)
    tai = _mang({"BBBBBBBBBBB": (404, b"")})
    for phut in (0, 20):
        kq = tk.nhip(goc, bay=BAY.replace(minute=phut), tai=tai, so_tay={}, kenh_ds=["TL2-T7"])
    assert len(goi) == 1
    assert os.path.isfile(os.path.join(goc, "workspace", "tu-kiem", "2026-10-17.json"))
    assert "Tự kiểm" in kq["dong"]
    assert tk.o_truc_quan(goc)["luc"].startswith("2026-10-17")                    # mới nhất trên đĩa, không theo đồng hồ
    assert tk.o_truc_quan(goc, BAY)["luc"].startswith("2026-10-17") and tk.o_truc_quan(goc, BAY.replace(day=16)) ["dat"] == 0


def test_bang_dieu_khien_mot_dong_may_va_viec_nguoi(tmp_path):
    from core import bang_dieu_khien as bdk
    goc = str(tmp_path)
    m = {"loai": "ghim", "kenh": "TL5-T7", "khoa": "ghim:x", "viec": "bình luận ghim", "tt": tk.CHO, "nguoi": True,
         "bang_chung": "kênh chờ xác minh điện thoại", "can_lam": "youtube.com/verify — xác minh số điện thoại kênh TL5-T7"}
    _ghi(os.path.join(goc, "workspace", "tu-kiem", "2026-10-17.json"),
         {"luc": "2026-10-17T12:00:00", "tom_tat": {"dat": 5, "tu_sua": 1, "mo": 0, "thu_lai": 0}, "dong": "Tự kiểm 17/10",
          "muc": [m], "nguoi": [m]})
    may = []
    viec = bdk.viec_cua_ban(goc, anh={"kenh": []}, may_tu_lam=may)
    assert any(x["khoa"] == "may:tu-kiem" and "Tự kiểm 17/10" in x["chu"] for x in may)
    assert [v for v in viec if v["khoa"].startswith("tu-kiem:TL5-T7")]


def test_kiem_duong_max(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "workspace", "cai-dat.json"), {"viet_chu_bang": "vi"})
    p = os.path.join(goc, "workspace", "viet-max", "so-dung.jsonl")
    os.makedirs(os.path.dirname(p))
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps({"luc": "2020-01-01 00:00:00", "viec": "cu"}) + "\n")
    K = tk.BoiCanh(goc, bay=BAY, tai=_mang({}), kenh_ds=[], so={})
    assert tk.kiem_duong_max(K)[0]["tt"] == tk.DAT
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps({"luc": "2099-01-01 00:00:00", "viec": "nao-bo-phan-ngu:bia"}) + "\n")
    m = tk.kiem_duong_max(K)[0]
    assert m["tt"] == tk.HONG and "nao-bo-phan-ngu" in m["bang_chung"]


def test_van_tay_lech():
    a = [0, 1] * 128
    assert tk.lech(a, a) == 0 and tk.lech(a, [1, 0] * 128) == 256 and tk.lech(a, None) is None
