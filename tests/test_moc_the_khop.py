"""05/10: so mốc thẻ theo giây (MM:SS:FF), cho lệch 1 khung hình."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vm"))
import may_dang_dom as m  # noqa: E402


def test_lech_mot_khung_van_khop():
    thay = ["08:27:23", "10:32:23", "12:38:00", "14:42:00", "16:47:00"]
    mong = ["08:28:00", "10:33:00", "12:38:00", "14:42:00", "16:47:00"]
    assert m.moc_the_khop(thay, mong)


def test_thua_the_khong_khop():
    assert not m.moc_the_khop(["10:52:00", "10:52:00"], ["10:52:00"])


def test_lech_xa_khong_khop():
    assert not m.moc_the_khop(["00:00:00", "12:38:00"], ["08:28:00", "12:38:00"])


def test_chu_hong_khong_khop():
    assert not m.moc_the_khop(["abc"], ["08:28:00"])
