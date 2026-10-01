"""DỜI LỊCH video đã hẹn giờ (`vm/may_dang_dom.py --doi-lich`, 01/10/2026 — giãn nhịp đăng).

Hàm thuần + luồng trang sửa trên trang GIẢ — không Chrome, không ghi vm/logs thật (sổ/hàng trong tmp_path).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import cdp_studio  # noqa: E402
import may_dang_dom as mdd  # noqa: E402

BAY = datetime(2026, 10, 1, 16, 40)


def test_hang_doi_lich_bo_video_sap_cong_khai_va_viec_xong():
    hang = [
        {"id": "a", "kenh": "K", "video_id": "v1", "lich_cu": "01/10/2026 20:00", "lich_moi": "03/10/2026 05:00"},
        {"id": "b", "kenh": "K", "video_id": "v2", "lich_cu": "01/10/2026 18:00", "lich_moi": "03/10/2026 05:00"},
        {"id": "c", "kenh": "K", "video_id": "v3", "lich_cu": "02/10/2026 05:00", "lich_moi": "05/10/2026 05:00",
         "trang_thai": "xong"},
        {"id": "d", "kenh": "K", "video_id": "v4", "lich_cu": "02/10/2026 08:00", "lich_moi": "07/10/2026 05:00",
         "trang_thai": "loi", "lan_loi": 1},
        {"id": "e", "kenh": "X", "video_id": "v5", "lich_cu": "02/10/2026 08:00", "lich_moi": "07/10/2026 05:00"},
    ]
    # b còn 80 phút (< 90) → để nguyên; c đã xong; e kênh khác; gấp trước
    assert [v["id"] for v in mdd.hang_doi_lich_kenh(hang, "K", BAY)] == ["a", "d"]
    hang[3]["lan_loi"] = mdd.DOI_LICH_TOI_DA_LOI
    assert [v["id"] for v in mdd.hang_doi_lich_kenh(hang, "K", BAY)] == ["a"]


def test_bo_chon_co_nut_xong_hop_hien_thi_va_cli():
    bo = cdp_studio.doc_bo_chon()
    assert cdp_studio.kiem_bo_chon(bo) == []
    assert "ytcp-video-visibility-edit-popup #save-button" in bo["phan_tu"]["sua_hop_xong"]["chon"]
    a = mdd._doc_lenh(["--kenh", "K", "--doi-lich", "--kiem-dom", "--video", "x"])
    assert a.doi_lich and a.kiem_dom and a.video == "x"


class _So:
    def __init__(self, duong):
        self.duong = str(duong)
        self.du = {"K/K-0002": {"video_id": "v1", "trang_thai": "xac-nhan", "lich": "01/10/2026 20:00"}}

    def lay(self, k):
        return dict(self.du.get(k) or {})

    def cap_nhat(self, k, **t):
        self.du.setdefault(k, {}).update(t)

    def doc(self):
        return self.du


def test_doi_lich_cap_nhat_hang_va_so_khong_ghi_tool(tmp_path, monkeypatch):
    duong = tmp_path / "hang-doi-lich.json"
    duong.write_text(json.dumps({"viec": [{"id": "doi-K-0002", "kenh": "K", "ma_goi": "K-0002", "video_id": "v1",
                                           "lich_cu": "01/10/2026 20:00", "lich_moi": "03/10/2026 05:00"}]}),
                     encoding="utf-8")
    may = mdd.MayDangDom.__new__(mdd.MayDangDom)
    may.kenh = "K"
    may.so = _So(tmp_path / "so-video-id.json")       # sổ GIẢ trong tmp → không ghi kế hoạch/hồ sơ tool
    may.nk = lambda *_a, **_k: None
    may._canh_bao = lambda *_a, **_k: None
    may.bay_gio = lambda: BAY
    may.con_han = lambda *_a: True
    monkeypatch.setattr(mdd.MayDangDom, "doi_lich_mot", lambda self, khoa, vid, lich, chi_kiem=False: {
        "ket": "ok", "ly_do": "", "lich_truoc": "01/10/2026 20:00", "lich_doc_lai": lich.strftime("%d/%m/%Y %H:%M")})
    assert may.doi_lich(mdd.hang_doi_lich_kenh(mdd.doc_hang_sua(str(duong)), "K", BAY), str(duong)) == mdd.MA_XONG
    v = mdd.doc_hang_sua(str(duong))[0]
    assert v["trang_thai"] == "xong" and v["lich_doc_lai"] == "03/10/2026 05:00" and "ghi_tool" not in v
    m = may.so.du["K/K-0002"]
    assert m["lich"] == m["lich_dat"] == "03/10/2026 05:00" and m["lich_truoc_doi"] == "01/10/2026 20:00"


def test_vi_pham_nhip_khong_tai_goi_sat_video_da_hen():
    so = {"K/K-0001": {"video_id": "v1", "trang_thai": "xac-nhan", "lich": "01/10/2026 20:00"},
          "K/K-0003": {"video_id": "", "trang_thai": "dang-tai", "lich": ""},
          "X/X-0001": {"video_id": "v9", "trang_thai": "xac-nhan", "lich": "02/10/2026 05:00"}}
    d = {"ma": "K-0002", "ngay": "02/10/2026", "gio": "05:00"}
    assert "dưới 2 ngày" in mdd.vi_pham_nhip(d, so, "K", 2)
    assert mdd.vi_pham_nhip(dict(d, ngay="03/10/2026"), so, "K", 2) == ""
    assert mdd.vi_pham_nhip(d, so, "K", 1) == ""                  # nhịp 1 ngày: luật cũ
    assert mdd.vi_pham_nhip(dict(d, ma="K-0001"), so, "K", 2) == ""   # chính nó không tính
