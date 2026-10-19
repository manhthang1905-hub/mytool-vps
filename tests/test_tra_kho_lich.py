"""19/10: kênh TRẢ KHO không còn bị lịch tự động mở Chrome (quét ngày ~30', phiên, ghim, sửa, thiết lập, nuôi, kéo chéo).
Một cổng chung ở agent (`kenh_lich`, đọc lại mỗi nhịp) + bộ chọn kênh của các tiến trình con. `lay-lai` mở lại ngay."""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
for _p in (str(GOC), str(GOC / "vm")):
    if _p not in sys.path:
        sys.path.append(_p)


def _nap_agent(tmp_path):
    spec = importlib.util.spec_from_file_location("agent_tra_kho", GOC / "vm" / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.GOC = str(tmp_path / "vm")
    mod.THU_MUC_TIEN_ICH = str(tmp_path / "tien-ich")
    return mod


def _kenh(goc: Path, ma: str, them: str = ""):
    d = goc / "CHANNEL" / ma
    d.mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text('ten: "x"\nnhom: "g1"\ntu_chay: true\nthiet_lap_kenh: true\nnuoi_trang_chu: true\n' + them,
                                 encoding="utf-8")
    return d


def _luc(h, m):
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, h, m, 0, 0, 0, -1))


def test_doc_dau_tra_kho_tu_kenh_yaml(tmp_path):
    ag = _nap_agent(tmp_path)
    _kenh(tmp_path, "A")
    _kenh(tmp_path, "B", 'tra_kho: "2026-10-19"   # trả kho\n')
    _kenh(tmp_path, "C", 'tra_kho: ""\n')
    g = str(tmp_path)
    assert ag.kenh_tra_kho("A", g) == "" and ag.kenh_tra_kho("C", g) == "" and ag.kenh_tra_kho("KHONG-CO", g) == ""
    assert ag.kenh_tra_kho("B", g) == "2026-10-19"
    assert ag.kenh_lich(["A", "B", "C", "KHONG-CO"], g) == ["A", "C", "KHONG-CO"]
    ag.GOC = str(tmp_path / "vm")                                   # mặc định: thư mục cha của vm/
    assert ag.kenh_lich(["B", "A"]) == ["A"]


def test_tra_kho_roi_lay_lai_thi_lich_mo_lai(tmp_path):
    from core import tra_kho
    ag = _nap_agent(tmp_path)
    _kenh(tmp_path, "A")
    _kenh(tmp_path, "B")
    g = str(tmp_path)
    tra_kho.tra(g, "B", thay="A")
    assert ag.kenh_lich(["A", "B"], g) == ["A"]
    tra_kho.lay_lai(g, "B")
    assert ag.kenh_lich(["A", "B"], g) == ["A", "B"]
    y = (tmp_path / "CHANNEL" / "B" / "kenh.yaml").read_text(encoding="utf-8")
    assert "tu_chay: true" in y and "thiet_lap_kenh: true" in y and "nuoi_trang_chu: true" in y


def test_quet_ngay_bo_kenh_tra_kho_khong_doi_gio_kenh_khac(tmp_path, monkeypatch):
    """Danh sách lịch bỏ kênh trả kho nhưng giờ quét so le vẫn theo vị trí GỐC trong cac_kenh."""
    ag = _nap_agent(tmp_path)
    monkeypatch.setattr(ag, "van_ipv4_mo", lambda: False)
    monkeypatch.setattr(ag, "tim_chrome", lambda ch: "C:/x.exe")
    monkeypatch.setattr(ag, "giu_khoa_may_chung", lambda viec="", kenh="", uu_tien=1: True)
    monkeypatch.setattr(ag, "nha_khoa_may_chung", lambda: None)
    chay = []
    monkeypatch.setattr(ag, "chay_quet_ngay_mot_kenh", lambda cau, ch, kenh: chay.append(kenh) or {"xong": True})
    monkeypatch.setattr(ag, "_VI_TRI_KENH", {"A": 0, "B": 1, "C": 2})
    cau = {"thu_muc_du_lieu": str(tmp_path)}
    hl = {k: {"kenh": k} for k in "ABC"}
    lich = ["A", "C"]                                               # B trả kho
    assert ag.chay_quet_ngay(cau, hl, lich, bay_gio=_luc(2, 10)) is True and chay == ["A"]
    # C vẫn quét lúc 03:10 (vị trí gốc 2), KHÔNG dời lên 02:40 (chỗ của B)
    assert ag.chay_quet_ngay(cau, hl, lich, bay_gio=_luc(2, 45)) is False and chay == ["A"]
    assert ag.chay_quet_ngay(cau, hl, lich, bay_gio=_luc(3, 10)) is True and chay == ["A", "C"]
    assert "B" not in chay


def test_thiet_lap_kenh_bo_kenh_tra_kho_du_cong_tac_con_bat(tmp_path):
    import thiet_lap_kenh_dom as t
    _kenh(tmp_path, "TK-GIA-A", 'tra_kho: "2026-10-19"\n')
    ra, ly = t.kenh_den_luot(time.time(), (), str(tmp_path), ram=64, nang_ban=False)
    assert "TK-GIA-A" not in ra and "trả kho" in ly["TK-GIA-A"]


def test_nuoi_trang_chu_bo_kenh_tra_kho_du_cong_tac_con_bat(tmp_path, monkeypatch):
    import nuoi_trang_chu as n
    _kenh(tmp_path, "TK-GIA-B", 'tra_kho: "2026-10-19"\n')
    monkeypatch.setattr(n, "cac_kenh_dang_nuoi", lambda *a, **k: [])
    monkeypatch.setattr(n, "cac_kenh_nuoi_lai", lambda *a, **k: [])
    ra, ly = n.kenh_den_luot(time.time(), (), str(tmp_path), ram=64, nang_ban=False)
    assert "TK-GIA-B" not in ra and "trả kho" in ly["TK-GIA-B"]


def test_keo_cheo_kenh_tra_kho_dung_ngoai(tmp_path):
    from core import keo_cheo
    _kenh(tmp_path, "A")
    _kenh(tmp_path, "B", 'tra_kho: "2026-10-19"\n')
    _kenh(tmp_path, "C")
    assert keo_cheo._cac_nhom(str(tmp_path)) == {"g1": ["A", "C"]}
