"""Tab «Hành trình» (8790): chữ riêng máy → mặc định trung tính; trang dùng chung hệ giao diện, không CDN."""
import json
import os
import re

from core import truc_quan as tq


def test_noi_dung_rieng_may_roi_mac_dinh(tmp_path):
    d = tq.noi_dung_hanh_trinh(str(tmp_path))          # máy chưa có tệp riêng → bản mặc định trong kho
    assert d["_nguon"] == "mac_dinh" and d["ban_dich"] and d["lo_trinh"]
    rieng = tmp_path / "workspace" / "hanh-trinh"
    rieng.mkdir(parents=True)
    (rieng / "noi-dung.json").write_text(json.dumps({"ban_dich": [{"hoc": "a", "luat": "b"}]}), encoding="utf-8")
    assert tq.noi_dung_hanh_trinh(str(tmp_path))["_nguon"] == "may"
    (rieng / "noi-dung.json").write_text("{hỏng", encoding="utf-8")
    assert tq.noi_dung_hanh_trinh(str(tmp_path))["_nguon"] == "mac_dinh"
    assert tq.noi_dung_gioi_thieu(str(tmp_path))["slides"]         # Giới thiệu vẫn đọc như cũ


def test_mac_dinh_trung_tinh_va_trang_khong_cdn():
    with open(os.path.join(tq.VENDOR, "hanh-trinh-mac-dinh.json"), encoding="utf-8") as tep:
        md = tep.read()
    assert not re.search(r"TL\d|[぀-ヿ]|\d{1,3}\.\d{3}", md)       # không mã/tên kênh, không số liệu máy này
    so_khoa = {d.get("so") for d in json.loads(md)["ban_dich"]}
    with open(os.path.join(tq.GOC, "ui_web", "hanh-trinh.html"), encoding="utf-8") as tep:
        s = tep.read()
    assert "/vendor/he-thong.css" in s and "/vendor/chung.js" in s
    assert not re.search(r"""(src|href)=["']https?://""", s)
    for k in so_khoa:                                   # mọi khoá số trong bản mặc định đều có hàm số sống
        assert re.search(r"\b" + k + r": \(\) =>", s), k
    for ten in ("chien-truong", "truc-quan", "nao", "nao-do-thi", "phong-thi-nghiem", "gioi-thieu"):
        with open(os.path.join(tq.GOC, "ui_web", ten + ".html"), encoding="utf-8") as tep:
            assert 'href="/hanh-trinh"' in tep.read(), ten
