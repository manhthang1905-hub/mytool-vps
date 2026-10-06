"""Bài kiểm `core/ban_giao_dang.py` — xuất gói bàn giao cho máy ảo đăng.

29/09/2026: `xuat_goi` đổi tệp VIDEO (`TEP_VIDEO`, nặng nhất) từ `shutil.copy2`
sang `os.link` (hardlink) khi nguồn/đích cùng ổ đĩa — tức thời, không đọc/ghi
lại toàn bộ nội dung. Hai bài dưới canh: (1) hardlink THẬT SỰ xảy ra (không
phải bản sao độc lập), (2) khi `os.link` không dùng được (khác ổ đĩa, hay bất
kỳ lỗi nào) thì lùi về `copy2` vẫn ra tệp đúng nội dung.

Toàn bộ dùng `tmp_path` của pytest, không gọi mạng.
"""

from __future__ import annotations

import os

from core import ban_giao_dang

MA_GOI = "TL4-T7-0009"


def _dung_luot(tmp_path, noi_dung_video=b"noi dung video gia"):
    d = tmp_path / "luot"
    (d / "7-thumbnail").mkdir(parents=True)
    (d / ban_giao_dang.TEP_VIDEO).write_bytes(noi_dung_video)
    (d / ban_giao_dang.TEP_SRT).write_text("1\n", encoding="utf-8")
    (d / "7-thumbnail" / "CHON-a.jpg").write_bytes(b"jpg")
    return d


def test_xuat_goi_hardlink_video_cung_o_dia(tmp_path):
    """Nguồn/đích cùng ổ đĩa (cùng `tmp_path`) — video ở đích phải là HARDLINK
    của nguồn, không phải bản sao độc lập."""
    d = _dung_luot(tmp_path)
    dich = ban_giao_dang.xuat_goi(str(d), str(tmp_path / "done"), MA_GOI)

    nguon_video = os.path.join(str(d), ban_giao_dang.TEP_VIDEO)
    dich_video = os.path.join(dich, ban_giao_dang.TEP_VIDEO)
    assert os.path.isfile(dich_video)

    st_nguon = os.stat(nguon_video)
    st_dich = os.stat(dich_video)
    # Cùng inode + cùng thiết bị = hardlink thật (NTFS qua Python dùng được cả
    # hai cách so này).
    assert st_nguon.st_ino == st_dich.st_ino
    assert st_dich.st_nlink >= 2

    # Các tệp KHÁC (srt, ảnh bìa) vẫn là copy2 như cũ — không phải hardlink.
    nguon_srt = os.path.join(str(d), ban_giao_dang.TEP_SRT)
    dich_srt = os.path.join(dich, ban_giao_dang.TEP_SRT)
    assert os.stat(nguon_srt).st_ino != os.stat(dich_srt).st_ino


def test_xuat_goi_lui_ve_copy2_khi_os_link_hong(tmp_path, monkeypatch):
    """Giả lập `os.link` ném `OSError` (như khi khác ổ đĩa) — vẫn phải ra
    đúng tệp video, chỉ là bản SAO độc lập thay vì hardlink."""
    noi_dung = b"noi dung video gia khac o dia"
    d = _dung_luot(tmp_path, noi_dung_video=noi_dung)

    goc_link = os.link

    def _link_luon_hong(*a, **kw):
        raise OSError("giả lập khác ổ đĩa — không hardlink được")

    monkeypatch.setattr(os, "link", _link_luon_hong)

    dich = ban_giao_dang.xuat_goi(str(d), str(tmp_path / "done"), MA_GOI)
    dich_video = os.path.join(dich, ban_giao_dang.TEP_VIDEO)
    assert os.path.isfile(dich_video)
    with open(dich_video, "rb") as tep:
        assert tep.read() == noi_dung

    # os.link không được gọi thật (đã bị thay), nhưng phần còn lại của tool
    # (đọc file) vẫn phải hoạt động bình thường — khôi phục lại cho sạch.
    monkeypatch.setattr(os, "link", goc_link)


def test_chon_danh_sach_phat_khop_chinh_xac():
    from core.ban_giao_dang import chon_danh_sach_phat
    ds = "A one | B two | C three"
    assert chon_danh_sach_phat(ds, "t", "m", lambda de: "B two") == "B two"
    assert chon_danh_sach_phat(ds, "t", "m", lambda de: "Answer: C three") == "C three"
    assert chon_danh_sach_phat(ds, "t", "m", lambda de: "khong co") == ""
    assert chon_danh_sach_phat("", "t", "m", lambda de: "A") == ""
    assert chon_danh_sach_phat(ds, "t", "m", None) == ""

    def hong(de):
        raise RuntimeError("x")
    assert chon_danh_sach_phat(ds, "t", "m", hong) == ""


def test_nguon_tool_doc_cot_danh_sach_phat():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vm"))
    import nguon_tool as nt
    csv_ = "Mã gói,Tiêu đề,Sẵn sàng,Danh sách phát\nK-1,T,x,B two\nK-2,T,x,\n"
    hang = nt._dung_hang(csv_, "K", "EDIT XONG")
    assert hang[0][nt.O_DSP] == "B two" and hang[1][nt.O_DSP] == ""


def test_chon_danh_sach_phat_qua_han_tra_rong():
    """05/10: AI treo (ShopAPI mất mạng) không được chặn bàn giao."""
    import time as _t
    from core.ban_giao_dang import chon_danh_sach_phat as _chon

    def cham(de):
        _t.sleep(5)
        return "A"
    t0 = _t.monotonic()
    assert _chon("A | B", "t", "m", cham, han_giay=0.3) == ""
    assert _t.monotonic() - t0 < 2


def test_chon_danh_sach_phat_trong_han_van_chon():
    from core.ban_giao_dang import chon_danh_sach_phat as _chon
    assert _chon("A | B", "t", "m", lambda de: "B", han_giay=5) == "B"


# ═══ LUẬT 07/10/2026: KHÔNG BÀN GIAO VIDEO THIẾU CLIP THẬT (1c) + KHE MỚI KHI LỠ GIỜ (1d) ═══

import datetime as _dt  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402

from core import ke_hoach_dang, qa_truoc_dang  # noqa: E402


def _goc_co_luot(tmp_path, *, tu_anh=None, thieu=(), so_canh=3, kenh_them=""):
    """Gốc giả: CHANNEL/K1/kenh.yaml + PROJECTS/AUTO/K1/0001 đủ bộ bàn giao."""
    goc = tmp_path / "goc"
    (goc / "CHANNEL" / "K1").mkdir(parents=True)
    (goc / "CHANNEL" / "K1" / "kenh.yaml").write_text(
        "ma: K1\nthu_muc_done: DONE/K1\n" + kenh_them, encoding="utf-8")
    d = goc / "PROJECTS" / "AUTO" / "K1" / "0001"
    (d / "7-thumbnail").mkdir(parents=True)
    (d / "6-clip").mkdir()
    (d / ban_giao_dang.TEP_VIDEO).write_bytes(b"video")
    (d / ban_giao_dang.TEP_SRT).write_text("1\n", encoding="utf-8")
    (d / "7-thumbnail" / "CHON-a.jpg").write_bytes(b"jpg")
    (d / "1-tieu-de.txt").write_text("TITLE: tieu de thu\n", encoding="utf-8")
    (d / "4-canh.json").write_text(json.dumps([{"scene_id": i} for i in range(1, so_canh + 1)]),
                                   encoding="utf-8")
    for i in range(1, so_canh + 1):
        if i not in thieu:
            (d / "6-clip" / "{0}.mp4".format(i)).write_bytes(b"clip")
    if tu_anh:
        (d / "6-clip" / "tu-anh.json").write_text(json.dumps({"canh": list(tu_anh), "tong": so_canh}),
                                                  encoding="utf-8")
    return str(goc), str(d)


@pytest.fixture()
def qa_dat(monkeypatch):
    monkeypatch.setattr(qa_truoc_dang, "kiem_thu_muc_goi", lambda *a, **k: qa_truoc_dang.KetQuaQA())


def test_kiem_clip_that(tmp_path):
    _g, d = _goc_co_luot(tmp_path)
    assert ban_giao_dang.kiem_clip_that(d)["loi"] == []
    _g, d = _goc_co_luot(tmp_path / "b", tu_anh=[2])
    kq = ban_giao_dang.kiem_clip_that(d)
    assert kq["tu_anh"] == [2] and kq["that"] == 2 and "DỰNG TỪ ẢNH" in kq["loi"][0]
    _g, d = _goc_co_luot(tmp_path / "c", thieu=(3,))
    assert "thiếu clip thật cho 1/3 cảnh (3)" in ban_giao_dang.kiem_clip_that(d)["loi"][0]
    assert ban_giao_dang.kiem_clip_that(d, kiem_thieu=False)["loi"] == []


@pytest.mark.parametrize("cach", ["tu_anh", "thieu"])
def test_ban_giao_tu_choi_goi_khong_du_clip_that(tmp_path, qa_dat, cach):
    goc, _d = _goc_co_luot(tmp_path, **({"tu_anh": [1, 3]} if cach == "tu_anh" else {"thieu": (2,)}))
    with pytest.raises(RuntimeError, match="KHÔNG bàn giao K1-0001"):
        ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"),
                               ngay="08/10/2026", gio="05:00")
    assert not os.path.exists(os.path.join(goc, "DONE", "K1", "K1-0001")), "không chép gói"
    assert ke_hoach_dang.doc_bang(goc, "K1")[1] == [], "không mọc dòng kế hoạch"


def test_ban_giao_du_clip_that_ghi_dau_nguon_clip(tmp_path, qa_dat):
    goc, _d = _goc_co_luot(tmp_path)
    ma, moi = ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"),
                                     ngay="08/10/2026", gio="05:00")
    assert (ma, moi) == ("K1-0001", True)
    du = json.loads(open(os.path.join(goc, "DONE", "K1", ma, ban_giao_dang.TEP_NGUON_CLIP),
                         encoding="utf-8").read())
    assert du["dat"] is True and du["that"] == 3 and du["tong"] == 3 and du["tu_anh"] == []


def test_kenh_tu_bat_clip_tu_anh_thi_ban_giao_duoc(tmp_path, qa_dat):
    goc, _d = _goc_co_luot(tmp_path, tu_anh=[2], kenh_them="clip_tu_anh: true\n")
    ma, _m = ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"))
    du = json.loads(open(os.path.join(goc, "DONE", "K1", ma, ban_giao_dang.TEP_NGUON_CLIP),
                         encoding="utf-8").read())
    assert du["dat"] is True and du["cho_phep_tu_anh"] is True and du["tu_anh"] == [2]


def test_mo_khoa_qa_khong_mo_goi_clip_tu_anh(tmp_path):
    goc, _d = _goc_co_luot(tmp_path, tu_anh=[1])
    goi = os.path.join(goc, "DONE", "K1", "K1-0001")
    os.makedirs(goi)
    with open(os.path.join(goi, qa_truoc_dang.TEN_TEP_KET_QUA), "w", encoding="utf-8") as tep:
        tep.write("x")
    ke_hoach_dang.luu_bang(goc, "K1", [_dong_ke_hoach(**{"Mã gói": "K1-0001"})])
    goi_kiem = []
    ra = ban_giao_dang.kiem_lai_goi_ket(goc, "K1", kiem=lambda *a: goi_kiem.append(a))
    assert ra[0]["ket_qua"] == "chua_dat" and "DỰNG TỪ ẢNH" in ra[0]["loi"][0]
    assert goi_kiem == []


def _dong_ke_hoach(**gia_tri):
    dong = {t: "" for t in ke_hoach_dang.COT}
    dong.update(gia_tri)
    return [dong[t] for t in ke_hoach_dang.COT]


def test_ban_giao_lai_goi_lo_gio_lay_khe_moi(tmp_path, qa_dat):
    """1d — dòng kế hoạch cũ đã QUA giờ, chưa tải (vd gói chờ clip quá giờ đăng) →
    bàn giao lại đổi sang khe mới vừa tính, không giữ giờ đã trôi."""
    goc, _d = _goc_co_luot(tmp_path)
    ke_hoach_dang.luu_bang(goc, "K1", [_dong_ke_hoach(**{
        "Mã gói": "K1-0001", "Ngày đăng": "07/10/2020", "Giờ đăng": "05:00", "Sẵn sàng": "x"})])
    ban_giao_dang.ban_giao(goc, "K1", "0001", os.path.join(goc, "DONE", "K1"),
                           ngay="08/10/2026", gio="05:00")
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    assert len(hang) == 1
    assert (hang[0][cot.index("Ngày đăng")], hang[0][cot.index("Giờ đăng")]) == ("08/10/2026", "05:00")


def test_lam_tuoi_lich_cu_khong_dung_dong_tuong_lai_hay_da_tai(tmp_path):
    goc = str(tmp_path)
    cot = list(ke_hoach_dang.COT)
    hang = [_dong_ke_hoach(**{"Mã gói": "A", "Ngày đăng": "09/10/2026", "Giờ đăng": "05:00"}),
            _dong_ke_hoach(**{"Mã gói": "B", "Ngày đăng": "06/10/2026", "Giờ đăng": "05:00",
                              "Video ID": "VIDxxxxxxxx"}),
            _dong_ke_hoach(**{"Mã gói": "C", "Ngày đăng": "06/10/2026", "Giờ đăng": "05:00",
                              "Trạng thái đăng": "ĐÃ ĐĂNG"}),
            _dong_ke_hoach(**{"Mã gói": "D"})]
    luc = _dt.datetime(2026, 10, 7, 9, 0)
    for ma in ("A", "B", "C", "D"):
        assert not ban_giao_dang._lam_tuoi_lich_cu(goc, "K1", ma, cot, hang, "08/10/2026", "05:00",
                                                   bay_gio=luc), ma
