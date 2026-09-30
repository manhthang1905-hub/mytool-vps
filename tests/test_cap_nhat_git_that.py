# -*- coding: utf-8 -*-
"""Hệ cập nhật với GIT THẬT, kho "GitHub" là một kho trần trong tmp_path.

Ba bản clone = ba máy: đẩy tự nâng phiên bản, hai máy đẩy tranh nhau (bị từ
chối → rebase → tăng lại số, không trùng), `--chi` không cuốn tệp dở của người
khác, máy kia kiểm thấy bản mới + changelog, `keo` áp ff-only, `lui` quay lại và
bỏ qua bản đó. Không mạng; kiểm khói/khung giờ/khởi động lại được thay bằng giả.
"""

import os
import subprocess

import pytest

from core import cap_nhat_git as cng
from core import dong_bo_git as d


def _g(thu_muc, *ts):
    ra = subprocess.run(["git", *ts], cwd=str(thu_muc), capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    assert ra.returncode == 0, (ts, ra.stdout, ra.stderr)
    return ra.stdout.strip()


def _clone(kho, dich, ma_may):
    _g(dich.parent, "clone", "-q", str(kho), dich.name)
    (dich / "cap-nhat.json").write_text(
        '{"dong_bo_git": {"ma_may": "%s", "xuat_bai_hoc": false, "khoi_dong_lai": false, '
        '"theo_doi_phut": 0}}' % ma_may, encoding="utf-8")
    return dich


@pytest.fixture()
def may(tmp_path, monkeypatch):
    kho = tmp_path / "kho.git"
    _g(tmp_path, "init", "-q", "--bare", "-b", "main", str(kho))
    goc = tmp_path / "khoi-tao"
    _g(tmp_path, "clone", "-q", str(kho), "khoi-tao")
    (goc / "VERSION").write_text("1.0.0", encoding="utf-8")
    (goc / "CHANGELOG.md").write_text("# Nhật ký phát hành\n\nGiới thiệu.\n\n## [cũ]\n\n- x\n", encoding="utf-8")
    (goc / ".gitignore").write_text("cap-nhat.json\nworkspace/\n", encoding="utf-8")
    (goc / "a.txt").write_text("a\n", encoding="utf-8")
    _g(goc, "add", "-A")
    _g(goc, "-c", "user.email=t@t.invalid", "-c", "user.name=t", "commit", "-q", "-m", "goc")
    _g(goc, "push", "-q", "origin", "HEAD:main")
    monkeypatch.setattr(d, "kiem_khoi", lambda goc, **_k: [])
    monkeypatch.setattr(d, "quet_bi_mat", lambda goc, tep: [])
    monkeypatch.setattr(d, "ly_do_chua_ranh", lambda goc, bay_gio=None: [])
    monkeypatch.setattr(d, "_dung_ban_kiem", lambda goc, ref, in_ra: [])
    return {"kho": kho, "A": _clone(kho, tmp_path / "A", "may-a"), "B": _clone(kho, tmp_path / "B", "may-b"),
            "C": _clone(kho, tmp_path / "C", "may-c")}


def _ver_kho(m):
    return _g(m["kho"], "show", "main:VERSION")


def test_day_tu_nang_phien_ban_changelog_tag(may):
    a = may["A"]
    (a / "a.txt").write_text("a2\n", encoding="utf-8")
    assert d.day(str(a), "sửa a", in_ra=lambda s: None) == 0
    assert _ver_kho(may) == "1.0.1"
    assert "v1.0.1" in _g(may["kho"], "tag", "--list")
    cl = _g(may["kho"], "show", "main:CHANGELOG.md")
    assert "- **1.0.1** — " in cl and "`may-a` — sửa a" in cl
    # --minor từ máy B: B chưa kéo, day tự rebase lên 1.0.1 rồi mới tăng
    (may["B"] / "b.txt").write_text("b\n", encoding="utf-8")
    assert d.day(str(may["B"]), "thêm b", muc="minor", in_ra=lambda s: None) == 0
    assert _ver_kho(may) == "1.1.0"
    ds = cng.doc_changelog(_g(may["kho"], "show", "main:CHANGELOG.md"))
    assert [x["phien_ban"] for x in ds] == ["1.1.0", "1.0.1"]


def test_hai_may_day_tranh_nhau_khong_trung_so(may, monkeypatch):
    a, c = may["A"], may["C"]
    (a / "a.txt").write_text("a3\n", encoding="utf-8")
    that = d._chay
    da_chen = []

    def chay(lenh, **k):
        if "push" in lenh and not da_chen:
            da_chen.append(1)   # máy C đẩy xen vào ĐÚNG lúc A sắp đẩy
            (c / "c.txt").write_text("c\n", encoding="utf-8")
            assert d.day(str(c), "máy c", in_ra=lambda s: None) == 0
        return that(lenh, **k)
    monkeypatch.setattr(d, "_chay", chay)
    ra = []
    assert d.day(str(a), "máy a", in_ra=ra.append) == 0, ra
    assert _ver_kho(may) == "1.0.2"            # C lấy 1.0.1, A tăng lại thành 1.0.2
    the = _g(may["kho"], "tag", "--list").split()
    assert "v1.0.1" in the and "v1.0.2" in the
    assert [x["phien_ban"] for x in cng.doc_changelog(_g(may["kho"], "show", "main:CHANGELOG.md"))] == \
        ["1.0.2", "1.0.1"]


def test_day_chi_tep_chon_giu_nguyen_tep_do_cua_nguoi_khac(may):
    a = may["A"]
    (a / "a.txt").write_text("cua toi\n", encoding="utf-8")
    (a / "do_dang.txt").write_text("cua agent khac\n", encoding="utf-8")
    assert d.day(str(a), "chỉ a", chi=["a.txt"], in_ra=lambda s: None) == 0
    assert "do_dang.txt" not in _g(may["kho"], "ls-tree", "--name-only", "main")
    assert (a / "do_dang.txt").read_text(encoding="utf-8") == "cua agent khac\n"
    assert "?? do_dang.txt" in _g(a, "status", "--porcelain")


def test_may_kia_kiem_thay_ban_moi_roi_keo_va_quay_lai(may):
    a, b = may["A"], may["B"]
    (a / "a.txt").write_text("a4\n", encoding="utf-8")
    assert d.day(str(a), "bản vá nhỏ", in_ra=lambda s: None) == 0
    tt = cng.kiem(str(b))
    assert tt["hien_tai"] == "1.0.0" and tt["ban_moi"] == "1.0.1"
    assert [x["noi_dung"] for x in tt["thay_doi"]] == ["bản vá nhỏ"]
    assert d.keo(str(b), cho_toi_da_phut=0, in_ra=lambda s: None) == 0
    assert (b / "VERSION").read_text(encoding="utf-8") == "1.0.1"
    tt = cng.doc_trang_thai(str(b))
    assert tt["cap_nhat_cuoi"]["ket_qua"] == "thanh_cong" and tt["ban_moi"] == ""
    assert cng.tag_lui(str(b))
    # Quay lại bản trước: về 1.0.0, và bản 1.0.1 trên kho bị bỏ qua
    assert d.lui_ban(str(b), in_ra=lambda s: None) == 0
    assert (b / "VERSION").read_text(encoding="utf-8") == "1.0.0"
    tt = cng.kiem(str(b))
    viec, ly = cng.quyet_dinh(str(b), tt, cng.doc_cau_hinh(str(b)))
    assert viec == "khong" and "bỏ qua" in ly
    # Có bản MỚI HƠN thì tự động nhận lại như thường
    (a / "a.txt").write_text("a5\n", encoding="utf-8")
    assert d.day(str(a), "bản sau", in_ra=lambda s: None) == 0
    tt = cng.kiem(str(b))
    assert cng.quyet_dinh(str(b), tt, cng.doc_cau_hinh(str(b)))[0] == "ap"


def test_keo_khong_de_khi_may_co_sua_chua_day(may):
    a, b = may["A"], may["B"]
    (a / "a.txt").write_text("a6\n", encoding="utf-8")
    assert d.day(str(a), "x", in_ra=lambda s: None) == 0
    (b / "a.txt").write_text("sua tay tren may b\n", encoding="utf-8")
    assert d.keo(str(b), cho_toi_da_phut=0, in_ra=lambda s: None) == 3
    assert (b / "a.txt").read_text(encoding="utf-8") == "sua tay tren may b\n"
    assert cng.doc_trang_thai(str(b))["co_sua_chua_day"]
