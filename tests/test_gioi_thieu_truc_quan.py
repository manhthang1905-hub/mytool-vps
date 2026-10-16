"""Trang «Giới thiệu» (8790, web cuộn kể hành trình Domain Translator): chữ riêng máy → mặc định trung tính; trang
dùng chung hệ giao diện, không CDN; tab «Hành trình» cũ đã gộp vào đây."""
import json
import os
import re

from core import truc_quan as tq

NEO = ("mo-dau", "muc-tieu", "bai-toan", "domain-translator", "lo-trinh", "ban-dich", "cach-may-lam", "doi-kenh", "kinh-te", "nguoi-may")


def test_noi_dung_rieng_may_roi_mac_dinh(tmp_path):
    d = tq.noi_dung_gioi_thieu(str(tmp_path))          # máy chưa có tệp riêng → bản mặc định trong kho
    assert d["_nguon"] == "mac_dinh" and d["ban_dich"]["dong"] and d["lo_trinh"]["moc"]
    rieng = tmp_path / "workspace" / "gioi-thieu"
    rieng.mkdir(parents=True)
    (rieng / "noi-dung.json").write_text(json.dumps({"ban_dich": {"dong": [{"hoc": "a", "luat": "b"}]}}), encoding="utf-8")
    assert tq.noi_dung_gioi_thieu(str(tmp_path))["_nguon"] == "may"
    (rieng / "noi-dung.json").write_text(json.dumps({"slides": [{"loai": "bia"}]}), encoding="utf-8")   # schema slide cũ
    assert tq.noi_dung_gioi_thieu(str(tmp_path))["_nguon"] == "mac_dinh"
    (rieng / "noi-dung.json").write_text("{hỏng", encoding="utf-8")
    assert tq.noi_dung_gioi_thieu(str(tmp_path))["_nguon"] == "mac_dinh"


def test_mac_dinh_trung_tinh_va_trang_khong_cdn():
    with open(os.path.join(tq.VENDOR, "gioi-thieu-mac-dinh.json"), encoding="utf-8") as tep:
        md = tep.read()
    assert not re.search(r"TL\d|[぀-ヿ]|\d{1,3}\.\d{3}", md)       # không mã/tên kênh, không số liệu máy này
    d = json.loads(md)
    assert all(k in d["muc_tieu"] for k in ("usd", "thang", "rpm", "video_kenh_thang", "ty_gia"))
    so_khoa = {x.get("so") for x in d["ban_dich"]["dong"] + d["cach_may_lam"]["the"] + d["domain_translator"]["buoc"]} - {None}
    with open(os.path.join(tq.GOC, "ui_web", "gioi-thieu.html"), encoding="utf-8") as tep:
        s = tep.read()
    assert "/vendor/he-thong.css" in s and "/vendor/chung.js" in s
    assert not re.search(r"""(src|href)=["']https?://""", s)
    for neo in NEO:
        assert 'id="{0}"'.format(neo) in s, neo
    for k in so_khoa:                                   # mọi khoá số trong bản mặc định đều có hàm số sống
        assert re.search(r"\b" + k + r": \(\) =>", s), k
    assert not os.path.exists(os.path.join(tq.GOC, "ui_web", "hanh-trinh.html"))
    for ten in ("chien-truong", "truc-quan", "nao", "nao-do-thi", "phong-thi-nghiem", "gioi-thieu"):
        with open(os.path.join(tq.GOC, "ui_web", ten + ".html"), encoding="utf-8") as tep:
            t = tep.read()
        assert 'href="/gioi-thieu"' in t and 'href="/hanh-trinh"' not in t, ten
