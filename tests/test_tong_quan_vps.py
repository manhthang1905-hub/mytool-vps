from __future__ import annotations

import csv
import os
import types

from core import tong_quan_vps as tq


def _ghi_csv(duong, hang):
    os.makedirs(os.path.dirname(str(duong)), exist_ok=True)
    cot = list(hang[0])
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        ghi = csv.DictWriter(tep, fieldnames=cot)
        ghi.writeheader()
        ghi.writerows(hang)


def test_tom_tat_phan_tich_doc_doi_thu_va_v7(tmp_path):
    d = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    d.mkdir(parents=True)
    (d / "doi-thu.txt").write_text("a\nb\n", encoding="utf-8")
    _ghi_csv(d / "doi-thu.csv", [
        {"Kênh": "A", "Trạng thái": "theo dõi", "Điểm": "7", "Vượt quy mô": "2", "Subs": "10"},
        {"Kênh": "B", "Trạng thái": "bỏ", "Điểm": "99", "Vượt quy mô": "9", "Subs": "20"},
        {"Kênh": "C", "Trạng thái": "theo dõi", "Điểm": "8", "Vượt quy mô": "1", "Subs": "5"},
    ])
    _ghi_csv(d / "content.csv", [
        {"Tiêu đề video": "Một"}, {"Tiêu đề video": "Hai"},
    ])
    _ghi_csv(d / "cham-v7-2026-09-25.csv", [
        {"Hạng": "1", "Điểm": "80", "Loại": "Làm ngay", "Tiêu đề": "Nên làm"},
        {"Hạng": "2", "Điểm": "40", "Loại": "Bỏ", "Tiêu đề": "Không làm"},
    ])
    ket = tq.tom_tat_phan_tich(str(tmp_path), "K1")
    assert ket["doi_thu"]["so_link"] == 2
    assert ket["doi_thu"]["so_kenh"] == 2
    assert ket["doi_thu"]["top"][0]["Kênh"] == "C"
    assert ket["noi_dung"]["so_video"] == 2
    assert ket["v7"]["so_ung_vien"] == 1
    assert ket["v7"]["top"][0]["Tiêu đề"] == "Nên làm"


def test_v7_khong_co_ung_vien_van_hien_ly_do_bi_bo(tmp_path):
    d = tmp_path / "CHANNEL" / "K1" / "nghien-cuu"
    d.mkdir(parents=True)
    _ghi_csv(d / "cham-v7-2026-09-25.csv", [
        {"Hạng": "1", "Điểm": "42", "Loại": "Bỏ", "Tiêu đề": "A", "Lý do": "thiếu tín hiệu"},
    ])
    ket = tq.tom_tat_phan_tich(str(tmp_path), "K1")
    assert ket["v7"]["so_ung_vien"] == 0
    assert ket["v7"]["top"][0]["Loại"] == "Bỏ"


def test_canh_bao_windows_nhan_dung_wlms_het_han(monkeypatch):
    monkeypatch.setattr(tq.os, "name", "nt")
    monkeypatch.setattr(tq.subprocess, "run", lambda *_a, **_k: types.SimpleNamespace(
        stdout="Date: 2026-09-25T01:40:16.798\nThe process wlms.exe\n"
               "The license period for this installation of Windows has expired."))
    ket = tq.canh_bao_windows()
    assert ket["muc"] == "loi"
    assert "tự tắt" in ket["chi_tiet"]


def test_canh_bao_windows_khong_bao_nham_restart_binh_thuong(monkeypatch):
    monkeypatch.setattr(tq.os, "name", "nt")
    monkeypatch.setattr(tq.subprocess, "run", lambda *_a, **_k: types.SimpleNamespace(
        stdout="The process shutdown.exe initiated restart"))
    assert tq.canh_bao_windows() == {}

