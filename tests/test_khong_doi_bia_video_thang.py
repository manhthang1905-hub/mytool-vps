"""19/10/2026: không lối nào được đổi bìa video đang THẮNG (S06 từng thay nhầm bìa CTR 9,7%)."""

from __future__ import annotations

import os

import pytest

from core import do_bia, ho_so_video


def _goc(tmp_path, hang):
    cs = tmp_path / "CHANNEL" / "K1" / "chi-so"
    cs.mkdir(parents=True)
    dong = ["Tiêu đề,Mã video,Ngày đăng,Lượt hiển thị,Tỷ lệ bấm"] + [
        "t{0},{1},2026-10-01,{2},{3}%".format(i, v, h, c) for i, (v, h, c) in enumerate(hang)]
    (cs / "bang-tom-tat.csv").write_text("\n".join(dong), encoding="utf-8")
    return str(tmp_path)


@pytest.fixture
def ho_so(monkeypatch):
    monkeypatch.setattr(ho_so_video, "doc_ho_so", lambda goc, k, ma: {"video_id": ma.split("-")[-1]})


def test_video_thang_bi_chan(tmp_path, ho_so):
    goc = _goc(tmp_path, [("AAA", 20000, 9.7), ("BBB", 3000, 3.0), ("CCC", 2000, 4.0), ("DDD", 1500, 2.0)])
    assert do_bia.video_dang_thang(goc, "K1", "K1-AAA")
    assert do_bia.video_dang_thang(goc, "K1", "K1-DDD") == ""


def test_khong_co_so_lieu_thi_khong_chan(tmp_path, ho_so):
    assert do_bia.video_dang_thang(str(tmp_path), "K1", "K1-AAA") == ""


def test_xep_doi_bia_tu_choi_video_thang(tmp_path, ho_so, monkeypatch):
    goc = _goc(tmp_path, [("AAA", 20000, 9.7), ("BBB", 3000, 3.0), ("CCC", 2000, 4.0)])
    anh = tmp_path / "b.jpg"
    anh.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="THẮNG"):
        do_bia.xep_doi_bia(goc, "K1", "K1-AAA", str(anh), ghi=lambda *_a: None)
    assert os.path.isfile(str(anh))
