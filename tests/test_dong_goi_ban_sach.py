"""Đóng gói bản sạch (`scripts/dong_goi_ban_sach.py`, 22/10/2026): loại dữ liệu ngách máy đầu, tài liệu gốc gói, soi
chuỗi riêng máy, zip tất định. Chỉ `tmp_path`, không git, không mạng."""
from __future__ import annotations

import importlib.util
import os
import zipfile

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("dong_goi_ban_sach", os.path.join(GOC_KHO, "scripts", "dong_goi_ban_sach.py"))
dg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dg)


def test_loai_tru_du_lieu_ngach_may_dau():
    assert dg.bi_loai("CHANNEL/_NHOM/tam-ly-nhat/ngach.yaml") and dg.bi_loai("CHANNEL/_NHOM/x/INSIGHT-CHON-CONTENT.md")
    assert dg.bi_loai("chia-se/bai-hoc/vps-a-ngach.json")
    assert not dg.bi_loai("CHANNEL/_KHUON/ngach-mau.yaml") and not dg.bi_loai("core/khoi_tao_vps.py")


def test_tai_lieu_goc_va_quet_chuoi(tmp_path):
    tep = {"docs/ban-sach/HUONG-DAN.txt": b"a\nb\n", "docs/ban-sach/PROMPT-SESSION-MAY-MOI.md": b"p",
           "docs/ban-sach/BAI-HOC-VPS-1.md": b"b", "docs/ban-sach/khoi-tao-mau/ngach.txt": b"chu_de: x",
           "core/a.py": "KÊNH_THẬT_XYZ = 1".encode("utf-8")}
    goc = dg.tai_lieu_goc(tep)
    assert goc["HUONG-DAN.txt"] == b"a\r\nb\r\n" and "khoi-tao/ngach.txt" in goc and "kho/DAT-CHROME-VAO-DAY.txt" in goc
    chan = dg.quet_chuoi(tep, ["KÊNH_THẬT_XYZ"])
    assert chan and "core/a.py" in chan[0] and "KÊNH_THẬT_XYZ" not in chan[0]          # không in chuỗi thật
    may = tmp_path / "may"
    (may / "CHANNEL" / "K1" / "chi-so" / "AbCdEfGhIj1").mkdir(parents=True)
    (may / "CHANNEL" / "K1" / "kenh.yaml").write_text('ten: "Kênh Thật Một — ghi chú"\nhandle: "@kenhthat1"\n', encoding="utf-8")
    assert dg.chuoi_may(str(may)) == ["@kenhthat1", "AbCdEfGhIj1", "Kênh Thật Một"]


def test_zip_tat_dinh(tmp_path):
    tai = tmp_path / "models" / "m.bin"
    tai.parent.mkdir(parents=True)
    tai.write_bytes(b"\0" * 10)
    luc = (2026, 10, 22, 0, 0, 0)
    ra = []
    for i in range(2):
        dich = str(tmp_path / "ra{0}".format(i) / "g.zip")
        dg.ghi_zip(dich, {"b.py": b"x", "a.py": b"y"}, {"HUONG-DAN.txt": b"h"}, [("models/m.bin", str(tai))], luc,
                   {"cap-nhat.json": b"{}"})
        with open(dich, "rb") as f:
            ra.append(f.read())
    assert ra[0] == ra[1]
    ten = zipfile.ZipFile(str(tmp_path / "ra0" / "g.zip")).namelist()
    assert ten == sorted(ten) and "MyTool/cap-nhat.json" in ten and "HUONG-DAN.txt" in ten
