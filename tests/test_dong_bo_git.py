# -*- coding: utf-8 -*-
"""core/dong_bo_git.py — phần THUẦN (không mạng, không git thật, không tiến trình thật).

Nằm trong `TEST_NHANH`: chạy trước mỗi `day`/`keo` trên máy sản xuất, nên phải nhanh.
"""

import datetime as dt
import json
import os

from core import dong_bo_git as d


def test_cau_hinh_mac_dinh_tat_tu_keo(tmp_path):
    cfg = d.doc_cau_hinh(str(tmp_path))
    assert cfg["tu_keo"] is False
    assert cfg["gio"] == "03:40"
    assert cfg["ma_may"].startswith("may-")


def test_cau_hinh_doc_khoa_dong_bo_git(tmp_path):
    (tmp_path / "cap-nhat.json").write_text(json.dumps(
        {"kho": "", "dong_bo_git": {"tu_keo": True, "gio": "25:99", "ma_may": "VPS 2 Nhat"}}),
        encoding="utf-8")
    cfg = d.doc_cau_hinh(str(tmp_path))
    assert cfg["tu_keo"] is True
    assert cfg["gio"] == "03:40"          # giờ hỏng -> mặc định
    assert cfg["ma_may"] == "vps-2-nhat"  # chuẩn hoá tên tệp


def test_tu_keo_chi_bat_khi_dung_true(tmp_path):
    (tmp_path / "cap-nhat.json").write_text('{"dong_bo_git": {"tu_keo": "yes"}}', encoding="utf-8")
    assert d.doc_cau_hinh(str(tmp_path))["tu_keo"] is False


def test_dang_quan_ly_can_ca_git_lan_tu_keo(tmp_path):
    (tmp_path / "cap-nhat.json").write_text('{"dong_bo_git": {"tu_keo": true}}', encoding="utf-8")
    assert d.dang_quan_ly(str(tmp_path)) is False
    (tmp_path / ".git").mkdir()
    assert d.dang_quan_ly(str(tmp_path)) is True


def test_sua_ssh_config_doi_hostname_trong_dung_khoi(tmp_path):
    p = tmp_path / "config"
    p.write_text("Host khac\n    HostName 1.2.3.4\n\nHost github-mytool\n    HostName 2a00::1\n"
                 "    User git\n", encoding="utf-8")
    assert d.sua_ssh_config("2a00::2", duong=str(p)) is True
    chu = p.read_text(encoding="utf-8")
    assert "HostName 1.2.3.4" in chu and "HostName 2a00::2" in chu and "2a00::1" not in chu
    assert d.sua_ssh_config("2a00::2", duong=str(p)) is False  # không đổi thì không ghi


def test_sua_ssh_config_them_khoi_khi_chua_co(tmp_path):
    p = tmp_path / "ssh" / "config"
    assert d.sua_ssh_config("github.com", duong=str(p)) is True
    chu = p.read_text(encoding="utf-8")
    assert "Host github-mytool" in chu and "HostKeyAlias github.com" in chu


def test_quet_them_bat_khoa_email_duong_va_tu_cam(tmp_path):
    (tmp_path / "a.py").write_text(
        "K = 'sk-" + "A" * 30 + "'\n"
        "M = 'nguoi" + "@" + "thatsu.com'\n"
        "P = r'C:" + "\\Users\\thanh\\Desktop'\n"
        "T = 'KenhThatSo1'\n", encoding="utf-8")
    ra = d.quet_them(str(tmp_path), ["a.py"], tu_cam=[("tên kênh thật", "KenhThatSo1")])
    loai = {x[1] for x in ra}
    assert {"khoá API dạng sk-…", "email", "đường tuyệt đối có tên người dùng", "tên kênh thật"} <= loai


def test_quet_them_bo_qua_mau_va_cho_bien(tmp_path):
    (tmp_path / "b.md").write_text(
        "mail: ban" + "@" + "example.com, git" + "@" + "github.com\n"
        "đường: C:" + "\\Users\\<ten>\\MyTool, %USERPROFILE%\n"
        "k = 'sk-" + "B" * 30 + "'  # " + d.DAU_BO_QUA + "\n", encoding="utf-8")
    assert d.quet_them(str(tmp_path), ["b.md"], tu_cam=[]) == []


def test_bien_dich_bao_loi_cu_phap(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "hong.py").write_text("def (:\n", encoding="utf-8")
    loi = d.bien_dich(str(tmp_path), ["ok.py", "hong.py", "khong-co.py", "README.md"])
    assert len(loi) == 1 and loi[0].startswith("hong.py")
    assert not (tmp_path / "__pycache__").exists()


def test_trong_khung_phut_15_45():
    assert d.trong_khung(dt.datetime(2026, 9, 30, 3, 15))
    assert d.trong_khung(dt.datetime(2026, 9, 30, 3, 45))
    assert not d.trong_khung(dt.datetime(2026, 9, 30, 3, 46))
    assert not d.trong_khung(dt.datetime(2026, 9, 30, 3, 5))


def test_tim_tien_trinh_dung_duong_khong_nham_ten_na_na():
    goc = os.path.join("C:" + os.sep, "Tool", "MyTool")
    vm = os.path.join(goc, "vm")
    ds = [(1, '"pythonw.exe" "{0}"'.format(os.path.join(goc, "shopapi_studio_qt.py"))),
          (2, "python.exe -u {0}".format(os.path.join(vm, "may_dang_dom.py"))),
          (3, "python.exe -u {0} --kenh X".format(os.path.join(vm, "may_dang.py"))),
          (4, "python.exe {0}".format(os.path.join("C:" + os.sep, "Khac", "shopapi_studio_qt.py")))]
    assert d._tim(ds, goc, "shopapi_studio_qt.py") == [1]
    assert d._tim(ds, vm, "may_dang.py") == [3]


def test_keo_tat_thi_thoat_ngay(tmp_path):
    ra = []
    assert d.keo(str(tmp_path), in_ra=ra.append) == 0
    assert "TẮT" in ra[0]


def test_nhan_bai_hoc_ngoai_chi_lay_may_khac(tmp_path):
    (tmp_path / "cap-nhat.json").write_text('{"dong_bo_git": {"ma_may": "may-a"}}', encoding="utf-8")
    cs = tmp_path / "chia-se" / "bai-hoc"
    cs.mkdir(parents=True)
    (tmp_path / "CHANNEL" / "_NHOM" / "ngach-x").mkdir(parents=True)
    for ma in ("may-a", "may-b"):
        (cs / "{0}-ngach-x.json".format(ma)).write_text(
            json.dumps({"ma_may": ma, "ngach": "ngach-x", "bai_hoc": []}), encoding="utf-8")
    (cs / "may-c-ngach-y.json").write_text(json.dumps({"ma_may": "may-c", "ngach": "ngach-y"}),
                                           encoding="utf-8")
    assert d.nhan_bai_hoc_ngoai(str(tmp_path), in_ra=lambda s: None) == 1
    assert os.listdir(tmp_path / "CHANNEL" / "_NHOM" / "ngach-x" / "bai-hoc-ngoai") == ["may-b-ngach-x.json"]
