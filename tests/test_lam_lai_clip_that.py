"""`python -m core.lam_lai_clip_that` — làm lại bằng clip thật các gói có cảnh dựng
từ ảnh (luật 07/10/2026). Cây giả trong `tmp_path`: không mạng, không YouTube.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os

import pytest

from core import auto, ke_hoach_dang, xep_lich
from core import lam_lai_clip_that as ll
from core.tu_chay import _tim_run_chua_xong

VID = "VIDxxxxxxx1"


def _ghi(duong, noi_dung, che_do="w"):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    if isinstance(noi_dung, (dict, list)):
        noi_dung = json.dumps(noi_dung, ensure_ascii=False)
    if isinstance(noi_dung, bytes):
        with open(duong, "wb") as tep:
            tep.write(noi_dung)
    else:
        with open(duong, che_do, encoding="utf-8") as tep:
            tep.write(noi_dung)


def _dong(**kv):
    d = {t: "" for t in ke_hoach_dang.COT}
    d.update(kv)
    return [d[t] for t in ke_hoach_dang.COT]


@pytest.fixture()
def cay(tmp_path, monkeypatch):
    goc = str(tmp_path / "goc")
    _ghi(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"), "ma: K1\nthu_muc_done: DONE/K1\n")
    d = os.path.join(goc, "PROJECTS", "AUTO", "K1", "0001")
    luot = auto.moi_luot(goc, "K1", "0001", {"link": "https://youtu.be/AAAAAAAAAAA"})
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    luot.tt("clip").ghi_chu = {"so_clip": 3, "clip_tu_anh": 2}
    auto.ghi_luot(luot)
    _ghi(os.path.join(d, "4-canh.json"), [{"scene_id": 1}, {"scene_id": 2}, {"scene_id": 3}])
    for n in (1, 2, 3):
        _ghi(os.path.join(d, "6-clip", "{0}.mp4".format(n)), b"clip")
        _ghi(os.path.join(d, "5-anh", "{0}.png".format(n)), b"png")
    _ghi(os.path.join(d, "6-clip", "tu-anh.json"), {"canh": [2, 3], "tong": 3})
    for t in ("8-video.mp4", "8-video.cu.mp4", "8-phan.json", "8-phu-de.srt"):
        _ghi(os.path.join(d, t), b"x")
    _ghi(os.path.join(d, "_cat", "1.mp4"), b"x")
    for t in ("1-kich-ban.txt", "2-giong-doc.mp3", "3-phu-de.srt", "7-thumbnail/CHON-a.jpg"):
        _ghi(os.path.join(d, t), b"giu")
    _ghi(os.path.join(goc, "DONE", "K1", "K1-0001", "8-video.mp4"), b"x")
    ke_hoach_dang.luu_bang(goc, "K1", [
        _dong(**{"Mã gói": "K1-0000", "Ngày đăng": "05/10/2026", "Giờ đăng": "05:00",
                 "Sẵn sàng": "x", "Trạng thái đăng": "ĐÃ ĐĂNG"}),
        _dong(**{"Mã gói": "K1-0001", "Ngày đăng": "07/10/2026", "Giờ đăng": "05:00",
                 "Sẵn sàng": "x", "Trạng thái đăng": "ĐANG ĐĂNG · nháp " + VID, "Video ID": VID})])
    _ghi(os.path.join(goc, "vm", "ke-hoach-K1.csv"),
         ke_hoach_dang.doc_van_ban(goc, "K1"))
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"),
         {"K1/K1-0001": {"video_id": VID, "trang_thai": "nhap", "lan_tai_moi": 1,
                         "ngay_tai": "2026-10-07", "id_cu": []},
          "K1/K1-0000": {"video_id": "VIDxxxxxxx0", "trang_thai": "xac-nhan"}})
    run = {"ma_luot": "0001", "nguon": {"ma": "AAAAAAAAAAA", "link": "https://youtu.be/AAAAAAAAAAA"},
           "san_xuat": {"da_chay": True, "xong_het": True, "khau_hong": [], "loi": ""},
           "ban_giao": {"da_ban_giao": True, "ma_goi": "K1-0001", "ngay_dang": "07/10/2026",
                        "gio_dang": "05:00", "ly_do_trong": "", "loi": ""},
           "phuc_hoi": {"so_lan": 2, "lan_dau_luc": 1.0}}
    _ghi(os.path.join(goc, "CHANNEL", "K1", "tu-chay", "2026-10-06.json"),
         {"ngay": "2026-10-06", "kenh": "K1", "runs": [run], "nhat_ky": []})
    _ghi(os.path.join(goc, "CHANNEL", "K1", "ho-so-video", "K1-0001.json"),
         {"ma_goi": "K1-0001", "video_id": VID, "clip_tu_anh": "2/3"})
    bao = []
    from core import bao_dong
    monkeypatch.setattr(bao_dong, "bao_dong_khan", lambda *a, **k: bao.append(a) or True)
    return type("Cay", (), {"goc": goc, "d": d, "bao": bao})


def _dau_cay(goc):
    ra = {}
    for g, _ds, ts in os.walk(goc):
        for t in ts:
            p = os.path.join(g, t)
            with open(p, "rb") as tep:
                ra[os.path.relpath(p, goc)] = hashlib.md5(tep.read()).hexdigest()
    return ra


def test_thu_chi_in_ke_hoach_khong_doi_gi(cay, capsys):
    truoc = _dau_cay(cay.goc)
    assert ll.main(["--tat-ca", "--thu", "--goc", cay.goc]) == 0
    ra = capsys.readouterr().out
    assert _dau_cay(cay.goc) == truoc, "--thu không được đổi một byte nào"
    assert "K1-0001" in ra and "2/3 cảnh là clip dựng từ ảnh" in ra
    assert "XOÁ dòng 07/10/2026 05:00" in ra and "CẤT videoId " + VID in ra
    assert "VIỆC CỦA CHỦ" in ra and VID in ra
    assert cay.bao == []


def test_lam_that_go_ban_giao_va_mo_lai_khau_clip(cay, capsys):
    goc, d = cay.goc, cay.d
    assert ll.main(["--kenh", "K1", "--ma", "0001", "--goc", goc]) == 0
    # Kế hoạch: dòng gói bị xoá (khe trả lại), dòng khác giữ.
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    assert [h[cot.index("Mã gói")] for h in hang] == ["K1-0000"]
    assert ("07/10/2026", "05:00") not in xep_lich.khe_da_dung(goc, "K1")
    with open(os.path.join(goc, "vm", "ke-hoach-K1.csv"), encoding="utf-8-sig") as tep:
        assert "K1-0001" not in tep.read()
    assert not os.path.exists(os.path.join(goc, "DONE", "K1", "K1-0001"))
    # Sổ máy đăng: id nháp cất vào id_cu, gói khác không đụng.
    so = json.load(open(os.path.join(goc, "vm", "logs", "so-video-id.json"), encoding="utf-8"))
    muc = so["K1/K1-0001"]
    assert muc["video_id"] == "" and muc["id_cu"] == [VID] and muc["lan_tai_moi"] == 0
    assert muc["trang_thai"] == ll.TRANG_THAI_SO_LAM_LAI and muc["ngay_tai"] == ""
    assert so["K1/K1-0000"]["video_id"] == "VIDxxxxxxx0"
    # Thư mục lượt: chỉ clip từ ảnh + video/tệp suy ra bị xoá.
    assert os.path.exists(os.path.join(d, "6-clip", "1.mp4"))
    for t in ("6-clip/2.mp4", "6-clip/3.mp4", "6-clip/tu-anh.json", "8-video.mp4",
              "8-video.cu.mp4", "8-phan.json", "8-phu-de.srt", "_cat"):
        assert not os.path.exists(os.path.join(d, t)), t
    for t in ("1-kich-ban.txt", "2-giong-doc.mp3", "3-phu-de.srt", "5-anh/2.png",
              "7-thumbnail/CHON-a.jpg", "4-canh.json"):
        assert os.path.exists(os.path.join(d, t)), t
    luot = auto.doc_luot(d)
    assert luot.tt("clip").trang_thai == auto.CHO and luot.tt("dung").trang_thai == auto.CHO
    assert luot.tt("clip").ghi_chu == {}
    assert luot.tt("anh").trang_thai == auto.XONG and luot.tt("thumbnail").trang_thai == auto.XONG
    # Sổ ngày: chưa bàn giao, chưa xong, phục hồi về 0 → tu_chay nhặt lại.
    so_ngay = json.load(open(os.path.join(goc, "CHANNEL", "K1", "tu-chay", "2026-10-06.json"),
                             encoding="utf-8"))
    r = so_ngay["runs"][0]
    assert r["ban_giao"]["da_ban_giao"] is False and r["ban_giao"]["ngay_dang"] == ""
    assert r["san_xuat"]["xong_het"] is False and "phuc_hoi" not in r
    assert r["lam_lai_clip_that"][0]["video_id_nhap"] == VID
    assert r["lam_lai_clip_that"][0]["ban_giao_cu"]["ngay_dang"] == "07/10/2026"
    assert _tim_run_chua_xong(goc, "K1", _dt.date(2026, 10, 7)) == ("2026-10-06", "0001")
    # Hồ sơ video + báo chủ + sao lưu.
    hs = json.load(open(os.path.join(goc, "CHANNEL", "K1", "ho-so-video", "K1-0001.json"),
                        encoding="utf-8"))
    assert "video_id" not in hs and hs["video_id_nhap_cu"] == VID
    md = open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8").read()
    assert VID in md and "xoá video" in md
    assert [a[0] for a in cay.bao] == ["nhap_clip_tu_anh"]
    sl = os.path.join(goc, "workspace", "sao-luu", "lam-lai-clip-that")
    (ten,) = os.listdir(sl)
    assert os.path.isfile(os.path.join(sl, ten, "vm", "logs", "so-video-id.json"))
    assert os.path.isfile(os.path.join(sl, ten, "PROJECTS", "AUTO", "K1", "0001", "6-clip",
                                       "tu-anh.json"))
    assert os.path.isfile(os.path.join(d, ll.TEP_DAU_LAM_LAI))
    # Chạy lại: không còn gì để làm.
    assert ll.tim_goi(goc) == []


def test_kenh_dang_chay_tu_chay_thi_khong_lam_that(cay, monkeypatch):
    _ghi(os.path.join(cay.goc, "CHANNEL", "K1", "tu-chay", ".khoa"), {"pid": os.getpid()})
    truoc = _dau_cay(cay.goc)
    assert ll.main(["--tat-ca", "--goc", cay.goc]) == 1
    sau = _dau_cay(cay.goc)
    # chỉ có thư mục sao lưu rỗng mới tạo — dữ liệu không đổi
    assert {k: v for k, v in sau.items() if "sao-luu" not in k} == truoc


def test_goi_chua_len_youtube_khong_bao_chu(cay):
    so = os.path.join(cay.goc, "vm", "logs", "so-video-id.json")
    _ghi(so, {})
    kh = ll.lap_ke_hoach(cay.goc, "K1", "0001")
    assert kh["so_video_id"] is None and not kh["chan"]
    assert ll.thuc_hien(cay.goc, kh, os.path.join(cay.goc, "sl"), ghi=lambda s: None)
    assert cay.bao == []
