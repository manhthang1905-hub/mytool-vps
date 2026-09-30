# -*- coding: utf-8 -*-
"""core/cap_nhat_git.py — phần THUẦN (không mạng, không git thật, không tiến trình thật).

Nằm trong `core.dong_bo_git.TEST_NHANH`: chạy trước mỗi `day`/`keo`, nên phải nhanh.
Đường git thật (hai bản clone, đẩy tranh nhau) ở `tests/test_cap_nhat_git_that.py`.
"""

import json

from core import cap_nhat_git as cng


def test_semver_tang_va_so():
    assert cng.phan_tich("﻿2.132.0\n") == (2, 132, 0)
    assert cng.phan_tich("2.132") is None and cng.phan_tich("<html>") is None
    assert cng.tang("2.132.0") == "2.132.1"
    assert cng.tang("2.132.7", "minor") == "2.133.0"
    assert cng.tang("2.132.7", "major") == "3.0.0"
    assert cng.moi_hon("2.10.0", "2.9.9") and not cng.moi_hon("2.9.9", "2.10.0")
    assert not cng.moi_hon("rac", "1.0.0")


def test_changelog_dung_muc_moi_roi_chen_moi_nhat_len_tren():
    goc = "# Nhật ký phát hành\n\nGiới thiệu.\n\n## [3.0.0-dev]\n\n- cũ\n"
    mot = cng.them_dong_changelog(goc, "2.133.0", "2026-09-30", "vps-jp1", "feat: cập nhật\nmới")
    assert mot.index(cng.DAU_MUC_CHANGELOG) < mot.index("## [3.0.0-dev]")
    assert "- **2.133.0** — 2026-09-30 — `vps-jp1` — feat: cập nhật mới" in mot
    hai = cng.them_dong_changelog(mot, "2.133.1", "2026-10-01", "vps-us2", "fix: x")
    ds = cng.doc_changelog(hai)
    assert [d["phien_ban"] for d in ds] == ["2.133.1", "2.133.0"]
    assert ds[0] == {"phien_ban": "2.133.1", "ngay": "2026-10-01", "may": "vps-us2", "noi_dung": "fix: x"}
    assert hai.count(cng.DAU_MUC_CHANGELOG) == 1 and "- cũ" in hai


def test_cau_hinh_mac_dinh_bat_tu_dong_va_kho_moi(tmp_path):
    cfg = cng.doc_cau_hinh(str(tmp_path))
    assert cfg["tu_dong_cap_nhat"] is True
    assert cfg["kho"] == "manhthang1905-hub/mytool-vps" and cfg["nhanh"] == "main"
    (tmp_path / "cap-nhat.json").write_text('{"kho": "", "tu_dong_cap_nhat": "khong"}', encoding="utf-8")
    assert cng.doc_cau_hinh(str(tmp_path))["tu_dong_cap_nhat"] is True   # chỉ `false` mới tắt
    (tmp_path / "cap-nhat.json").write_text(
        '{"kho": "https://github.com/a/b.git", "tu_dong_cap_nhat": false}', encoding="utf-8")
    cfg = cng.doc_cau_hinh(str(tmp_path))
    assert cfg["tu_dong_cap_nhat"] is False and cfg["kho"] == "a/b"


def test_dat_tu_dong_giu_khoa_khac(tmp_path):
    (tmp_path / "cap-nhat.json").write_text(json.dumps({"dong_bo_git": {"ma_may": "may-a"}}), encoding="utf-8")
    assert cng.dat_tu_dong(str(tmp_path), False)
    du = json.loads((tmp_path / "cap-nhat.json").read_text(encoding="utf-8"))
    assert du["tu_dong_cap_nhat"] is False and du["dong_bo_git"] == {"ma_may": "may-a"}
    assert du["kho"] == cng.KHO_MAC_DINH
    assert cng.doc_trang_thai(str(tmp_path))["tu_dong"] is False


def _gia_lap(monkeypatch, tt, ly_do=()):
    monkeypatch.setattr(cng, "kiem", lambda goc, **_k: cng.ghi_trang_thai(goc, **tt))
    monkeypatch.setattr(cng.dbg, "ly_do_chua_ranh", lambda goc, bay_gio=None: list(ly_do))
    monkeypatch.setattr(cng.dbg, "la_kho_git", lambda goc: True)
    monkeypatch.setattr(cng.dbg, "tep_doi_cuc_bo", lambda goc: list(tt.get("co_sua_chua_day") or []))


def test_nhip_co_ban_moi_may_ranh_thi_sinh_keo(tmp_path, monkeypatch):
    _gia_lap(monkeypatch, {"ban_moi": "2.134.0", "sha_xa": "abc", "kiem_epoch": 0})
    sinh = []
    tt = cng.nhip(str(tmp_path), bat_buoc_kiem=True, sinh=lambda g, t: sinh.append(t) or 4242)
    assert tt["quyet"] == "ap" and sinh and sinh[0][0] == "keo" and "--ep" not in sinh[0]


def test_nhip_may_ban_thi_cho_khong_sinh(tmp_path, monkeypatch):
    _gia_lap(monkeypatch, {"ban_moi": "2.134.0"}, ly_do=["ngoài khung phút :15–:45"])
    sinh = []
    tt = cng.nhip(str(tmp_path), bat_buoc_kiem=True, sinh=lambda g, t: sinh.append(t) or 1)
    assert tt["quyet"] == "cho" and not sinh and "15" in tt["quyet_ly_do"]


def test_nhip_tat_tu_dong_chi_bao_nhung_hen_thi_van_ap(tmp_path, monkeypatch):
    (tmp_path / "cap-nhat.json").write_text('{"tu_dong_cap_nhat": false}', encoding="utf-8")
    _gia_lap(monkeypatch, {"ban_moi": "2.134.0"})
    sinh = []
    tt = cng.nhip(str(tmp_path), bat_buoc_kiem=True, sinh=lambda g, t: sinh.append(t) or 1)
    assert tt["quyet"] == "khong" and not sinh
    cng.ghi_trang_thai(str(tmp_path), hen_cap_nhat=True)
    tt = cng.nhip(str(tmp_path), bat_buoc_kiem=True, sinh=lambda g, t: sinh.append(t) or 1)
    assert tt["quyet"] == "ap" and "--ep" in sinh[0]


def test_nhip_may_co_sua_chua_day_khong_ap(tmp_path, monkeypatch):
    _gia_lap(monkeypatch, {"ban_moi": "2.134.0", "co_sua_chua_day": [" M core/x.py"]})
    sinh = []
    tt = cng.nhip(str(tmp_path), bat_buoc_kiem=True, sinh=lambda g, t: sinh.append(t) or 1)
    assert tt["quyet"] == "khong" and not sinh and "chưa đẩy" in tt["quyet_ly_do"]


def test_nhip_bo_qua_ban_da_lui(tmp_path, monkeypatch):
    _gia_lap(monkeypatch, {"ban_moi": "2.134.0", "sha_xa": "abc", "bo_qua_sha": "abc"})
    sinh = []
    tt = cng.nhip(str(tmp_path), bat_buoc_kiem=True, sinh=lambda g, t: sinh.append(t) or 1)
    assert tt["quyet"] == "khong" and not sinh and "bỏ qua" in tt["quyet_ly_do"]


def test_khoa_mot_luot_cap_nhat(tmp_path):
    goc = str(tmp_path)
    assert cng.giu_khoa(goc, "keo") and cng.dang_cap_nhat(goc)["viec"] == "keo"
    cng.nha_khoa(goc)
    assert cng.dang_cap_nhat(goc) == {}
    (tmp_path / "workspace" / "cap-nhat" / "dang-cap-nhat.json").write_text(
        json.dumps({"pid": 999999, "tu_luc": 1e10}), encoding="utf-8")
    assert cng.dang_cap_nhat(goc) == {}          # PID chết → khoá bỏ qua


def test_mo_ta_giao_dien_noi_ro_cho_nguoi_thuong():
    from ui_qt.cap_nhat import mo_ta_trang_thai

    mt = mo_ta_trang_thai({"hien_tai": "2.133.0", "ban_moi": "2.133.1", "kiem_luc": "2026-09-30 23:30",
                           "thay_doi": [{"phien_ban": "2.133.1", "ngay": "2026-09-30", "may": "vps-jp1",
                                         "noi_dung": "sửa tài liệu"}],
                           "quyet": "cho", "quyet_ly_do": "ngoài khung phút :15–:45",
                           "co_sua_chua_day": [" M vm/a.py"],
                           "cap_nhat_cuoi": {"luc": "2026-09-30 22:15", "ket_qua": "thanh_cong",
                                             "chi_tiet": "đã cập nhật 2.132.0 → 2.133.0"}},
                          {"tu_dong_cap_nhat": True})
    assert mt["hien_tai"] == "Phiên bản hiện tại: 2.133.0" and mt["ban_moi"] == "Bản mới: 2.133.1"
    assert "sửa tài liệu" in mt["thay_doi"] and "30/09" in mt["thay_doi"]
    assert "khi máy rảnh" in mt["trang_thai"] and "23:30 30/09" in mt["trang_thai"]
    assert "đã cập nhật" in mt["trang_thai"] and "vm/a.py" in mt["sua"]
