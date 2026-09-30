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
