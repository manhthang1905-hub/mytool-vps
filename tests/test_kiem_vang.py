"""KIỂM VÀNG bìa — hồi quy đầu-cuối sau mọi thay đổi (19/10/2026, `core/bia_lo.py` mục 6 + kỹ năng D19).

Vân tay (mã bìa, style.yaml, 8-thumbnail.md, khoá bia_* kenh.yaml, thư mục bìa thắng) đổi → nên chạy; lô thật giả
→ tờ so 3 hàng + đối chiếu cùng giám khảo (bìa thắng giấu hiệu chỉnh sàn) → đạt/trượt; trượt → dây chuyền GIỮ bìa
mới + báo. LLM + mô hình ảnh GIẢ, ảnh tổng hợp PIL."""

from __future__ import annotations

import io
import json
import os
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from core import bia_lo
from core.kenh import TEP_KENH, duong_kenh


@pytest.fixture(autouse=True)
def _khong_xoa_dau(monkeypatch):
    from core import xoa_dau_anh
    monkeypatch.setattr(xoa_dau_anh, "xoa_dau_tep", lambda duong, *a, **k: None)


def _goc(tmp_path, so_thang: int = 4) -> str:
    goc = str(tmp_path / "goc")
    dk = duong_kenh(goc, "KH")
    os.makedirs(os.path.join(dk, "prompt"), exist_ok=True)
    with io.open(os.path.join(dk, TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "KH"\nbia_lo: true\n')
    with io.open(os.path.join(dk, "style.yaml"), "w", encoding="utf-8") as tep:
        tep.write('default_character_lock: "round white head"\n')
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0002")
    os.makedirs(os.path.join(luot, "7-thumbnail"), exist_ok=True)
    with io.open(os.path.join(luot, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: 同じ車に長く乗る人の特徴\nTHUMB: 同じ車に長く乗る人のほとんどが\n")
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    os.makedirs(tm)
    for i in range(1, so_thang + 1):
        Image.new("RGB", (1280, 720), (240, 220 - 5 * i, 200)).save(os.path.join(tm, "{0}.jpg".format(i)))
    # 2 video đang chạy (bìa thật đã tải về hồ sơ)
    from core import khuon_bia
    os.makedirs(os.path.join(dk, "chi-so"), exist_ok=True)
    with io.open(os.path.join(dk, "chi-so", "bang-tom-tat.csv"), "w", encoding="utf-8-sig") as tep:
        tep.write("Tiêu đề,Mã video,Ngày đăng,Lượt hiển thị,Tỷ lệ bấm\nA,VIDGIA01,2026-10-17,10,0%\n"
                  "B,VIDGIA02,2026-10-18,10,0%\n")
    for v in ("VIDGIA01", "VIDGIA02"):
        p = khuon_bia.duong_anh_that(goc, "KH", v)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        Image.new("RGB", (1280, 720), (230, 200, 190)).save(p)
    return goc


def test_khuc_ham_va_van_tay_doi_dung_cho(tmp_path):
    chu = "X = 1\n\ndef a(x):\n    return 1\n\n\n@deco\ndef b():\n    pass\n\nclass C(Exception):\n    pass\n"
    assert bia_lo._khuc_ham(chu, "a").startswith("def a(") and "def b" not in bia_lo._khuc_ham(chu, "a")  # noqa: SLF001
    assert bia_lo._khuc_ham(chu, "C").startswith("class C") and bia_lo._khuc_ham(chu, "zz") == ""  # noqa: SLF001
    goc = _goc(tmp_path)
    dk = duong_kenh(goc, "KH")
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    vt0 = bia_lo.van_tay_vang(goc, "KH")
    # tệp đệm máy tự ghi + khoá kenh.yaml không phải bia_* → KHÔNG đổi
    bia_lo._ghi_json(os.path.join(tm, bia_lo.TEP_MAU_THANG), {"x": 1})  # noqa: SLF001
    bia_lo._ghi_json(os.path.join(tm, bia_lo.TEP_SAN_BAM), {"san": 7})  # noqa: SLF001
    with io.open(os.path.join(dk, TEP_KENH), "a", encoding="utf-8") as tep:
        tep.write("tu_chay: true\n")
    assert bia_lo.van_tay_vang(goc, "KH") == vt0
    cac = []
    for sua in (lambda: io.open(os.path.join(dk, "style.yaml"), "a", encoding="utf-8").write("x: 1\n"),
                lambda: io.open(os.path.join(dk, "prompt", "8-thumbnail.md"), "w", encoding="utf-8").write("p"),
                lambda: io.open(os.path.join(dk, TEP_KENH), "a", encoding="utf-8").write("bia_lo_kieu: tran\n"),
                lambda: Image.new("RGB", (1280, 720), (1, 2, 3)).save(os.path.join(tm, "2.jpg"))):
        sua()
        cac.append(bia_lo.van_tay_vang(goc, "KH"))
    assert len(set([vt0] + cac)) == 5, "mỗi thay đổi (style, prompt bìa, khoá bia_*, bìa thắng) đổi vân tay"


def test_can_kiem_vang_va_giu(tmp_path):
    goc = _goc(tmp_path)
    assert bia_lo.kenh_san_xuat(goc) == ["KH"] and bia_lo.luot_moi_nhat(goc, "KH").endswith("0002")
    assert bia_lo.can_kiem_vang(goc, "KH") == (True, "chưa kiểm vàng bìa lần nào")
    vt = bia_lo.van_tay_vang(goc, "KH")
    bia_lo._ghi_vang(goc, "KH", {"van_tay": vt, "dat": True, "ts": 0, "luc": "x"})  # noqa: SLF001
    assert bia_lo.can_kiem_vang(goc, "KH")[0] is False and bia_lo.vang_chan(goc, "KH") == ""
    import time
    bia_lo._ghi_vang(goc, "KH", {"van_tay": vt, "dat": False, "ts": time.time(), "ly_do": ["kém"]})  # noqa: SLF001
    assert bia_lo.can_kiem_vang(goc, "KH")[0] is False, "trượt vừa xong: chưa thử lại (không đốt tiền)"
    # Chủ 19/10: mặc định CHỈ CẢNH BÁO — trượt (kể cả các dòng TRƯỢT có sẵn trong trang-thai.json) không giữ gì
    assert bia_lo.vang_chan(goc, "KH") == "" and not bia_lo.giu_theo_vang(goc, "KH")
    from core import cai_dat
    cai_dat.ghi(goc, {"kiem_vang_giu": True})
    assert "kém" in bia_lo.vang_chan(goc, "KH"), "ô Cài đặt bật → giữ"
    tep_k = os.path.join(duong_kenh(goc, "KH"), TEP_KENH)
    goc_k = io.open(tep_k, encoding="utf-8").read()
    with io.open(tep_k, "w", encoding="utf-8") as tep:
        tep.write(goc_k + "kiem_vang_giu: false\n")
    assert bia_lo.vang_chan(goc, "KH") == "", "kenh.yaml từng kênh thắng ô chung"
    with io.open(tep_k, "w", encoding="utf-8") as tep:
        tep.write(goc_k + "kiem_vang_giu: true\n")
    cai_dat.ghi(goc, {"kiem_vang_giu": False})
    assert bia_lo.giu_theo_vang(goc, "KH") and "kém" in bia_lo.vang_chan(goc, "KH"), "chọn giữ (từng kênh) → giữ"
    assert bia_lo.can_kiem_vang(goc, "KH", bay_gio=time.time() + 25 * 3600)[0] is True, "trượt > 24 giờ → thử lại"
    bia_lo._ghi_vang(goc, "KH", {"van_tay": "khac", "dat": False, "ts": time.time()})  # noqa: SLF001
    assert bia_lo.can_kiem_vang(goc, "KH")[0] is True, "vân tay đổi → kiểm lại ngay"
    assert bia_lo.vang_chan(goc, "KH"), "đang trượt thì vẫn GIỮ cho tới khi một lần kiểm vàng đạt"
    # dây chuyền: kiểm vàng trượt → GIỮ bìa mới (không vẽ lô) + báo
    from core import auto_khau as ak
    goi_lo = []
    import core.bia_lo as bl
    orig = bl.chay
    bl.chay = lambda *a, **k: goi_lo.append(1)
    try:
        bc = SimpleNamespace(goc=goc, kenh=SimpleNamespace(ma="KH", ngon_ngu="ja"), ghi=lambda s: None)
        luot = SimpleNamespace(thu_muc=os.path.join(goc, "PROJECTS", "AUTO", "KH", "0002"), ma_luot="0002",
                               ma_kenh="KH")
        with pytest.raises(RuntimeError, match="GIỮ"):
            ak._bia_lo_luot(bc, luot)  # noqa: SLF001
    finally:
        bl.chay = orig
    assert goi_lo == [], "giữ thì không vẽ lô (không trả tiền ảnh)"
    with io.open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8") as tep:
        assert "kiểm vàng" in tep.read()


def _nen(d: str) -> None:
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (238, 214, 190))
    dr = ImageDraw.Draw(im)
    dr.rectangle([0.62 * W, 0.66 * H, 0.97 * W, 0.86 * H], fill=(190, 110, 60), outline=(60, 30, 20), width=6)
    dr.ellipse([0.70 * W, 0.28 * H, 0.83 * W, 0.52 * H], fill=(250, 250, 250), outline=(12, 12, 12), width=8)
    im.save(d)


def _ve(loi_nhac, n, k, cac_dich):
    for d in cac_dich[:n]:
        _nen(d)
    return list(cac_dich[:n])


def _goi(bam_moi: float, bam_thang: float = 8):
    lan = []

    def goi(loi_nhac, **kw):
        lan.append(kw.get("khoa", ""))
        if "CONCEPT DIRECTOR" in loi_nhac:
            return json.dumps({"chu": [], "y_tuong": [
                {"y": "c{0}".format(i), "manh_moi": "clue {0}".format(i), "doi_lap": "faded crowd",
                 "canh": "the figure doing thing {0} on the right".format(i), "mat": "smile", "tu_the": "standing"}
                for i in (1, 2)]})
        if "strict art director" in loi_nhac:
            n = int(loi_nhac.split("numbered 1 to ", 1)[1].split(" ", 1)[0])
            doi = ":doi-chieu:" in kw.get("khoa", "")
            # đối chiếu: [mới1, đang1, GIẤU, mới2, đang2, …] — tấm số 3 là bìa thắng giấu
            return json.dumps({"ung_vien": [{"so": i + 1, "bam_nhu_thang": bam_thang if (doi and i == 2) else bam_moi,
                                             "noi_dung": 7, "to_mo": 7, "ro_120": 7, "cam_xuc": 7, "phong_cach": 7,
                                             "nv": "same", "nguoi_khac": "none"} for i in range(n)]})
        if "Read the text printed" in loi_nhac:
            return json.dumps({"dong": [], "chu_thua": []})
        return "{}"
    goi.lan = lan
    return goi


def _font_hop():
    if not bia_lo.btk._tim_font("", "同じ車に長く", "ja", kieu="hop"):  # noqa: SLF001
        pytest.skip("máy không có phông bìa kiểu hộp")


def test_kiem_vang_dat_hieu_chinh_san_va_to_so(tmp_path):
    _font_hop()
    goc = _goc(tmp_path)
    goi = _goi(8, bam_thang=9)
    m = bia_lo.kiem_vang(goc, "KH", goi=goi, ve=_ve, ra=str(tmp_path / "kv"), log=lambda s: None, tai=False)
    assert m["dat"] is True and m["ly_do"] == [] and m["giau"] == "4.jpg", m
    assert m["diem_giau"] == 9 and m["san_bam"] == 8.0, "sàn = điểm bìa thắng giấu − 1"
    assert bia_lo.san_bam(m["thu_muc_mau"]) == (8.0, "hieu-chinh")
    assert os.path.isfile(m["to"]) and len(m["diem"]["dang"]) == 2 and m["diem"]["moi"][0] == 8
    assert any(":doi-chieu:" in k for k in goi.lan), "đối chiếu bằng cùng giám khảo"
    assert bia_lo.doc_vang(goc)["KH"]["van_tay"] == bia_lo.van_tay_vang(goc, "KH")
    assert bia_lo.can_kiem_vang(goc, "KH")[0] is False and bia_lo.vang_chan(goc, "KH") == ""


def test_kiem_vang_truot_thi_giu_va_bao(tmp_path):
    _font_hop()
    goc = _goc(tmp_path)
    m = bia_lo.kiem_vang(goc, "KH", goi=_goi(5, bam_thang=8), ve=_ve, ra=str(tmp_path / "kv"), log=lambda s: None,
                         tai=False)
    assert m["dat"] is False and any("sàn" in x for x in m["ly_do"]), m["ly_do"]
    assert os.path.isfile(m["to"]), "trượt vẫn có tờ so (hàng MỚI = tấm điểm cao nhất dù dưới sàn)"
    assert m["che_do"] == "canh_bao" and bia_lo.vang_chan(goc, "KH") == "", "mặc định chỉ cảnh báo, không giữ"
    with io.open(os.path.join(goc, "workspace", "loi-chay-max.md"), encoding="utf-8") as tep:
        chu = tep.read()
    assert "Kiểm vàng bìa kênh KH TRƯỢT" in chu and "chỉ cảnh báo" in chu and chu.count("TRƯỢT") == 1, "một báo động"


def test_kiem_vang_khong_co_bia_thang_la_truot_co_ly_do(tmp_path):
    goc = _goc(tmp_path, so_thang=0)
    m = bia_lo.kiem_vang(goc, "KH", goi=_goi(8), ve=_ve, ra=str(tmp_path / "kv"), log=lambda s: None, tai=False)
    assert m["dat"] is False and "thư mục bìa thắng" in m["ly_do"][0]


def test_chua_khai_kieu_thi_theo_phieu_bia_thang(tmp_path):
    """Kênh chưa có khuôn + chưa khai `bia_lo_kieu` (TL6/TL5/TL6-K2 trước khi chủ áp khoá): kiểu chữ theo phiếu các
    bìa thắng trong thư mục, không lùi khuôn hộp mặc định."""
    goc = _goc(tmp_path, so_thang=3)

    def goi(loi_nhac, **kw):
        if "best-performing" in loi_nhac:
            return json.dumps({"bia": [{"so": i, "kieu_chu": "bare" if i < 3 else "box", "chu": "x", "ta": "t"}
                                       for i in (1, 2, 3)], "hinh": "h", "nen": "n"})
        return "{}"
    hs = bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)
    assert hs["kieu"] == "tran" and hs["nguon_kieu"] == "phieu-bia-thang" and hs["bo_cuc"] == "trai"
    with io.open(os.path.join(duong_kenh(goc, "KH"), TEP_KENH), "a", encoding="utf-8") as tep:
        tep.write('bia_lo_kieu: "hop"\n')
    assert bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)["kieu"] == "hop", "khoá của chủ thắng phiếu"


def test_ky_nang_d18_tu_kich_hoat(tmp_path):
    from core import ky_nang as kn
    k = kn.theo_ma("D19")
    assert k and k.tu_ap and k.dieu_kien and k.mot_kenh
    assert k.chay("G", "KH")[-4:] == ["core.bia_lo", "--kiem-vang", "--kenh", "KH"]
    goc = _goc(tmp_path)
    assert k.dieu_kien(goc, "KH")[0] is True and k.kiem(goc, "KH")[0] == kn.THIEU
    assert k.kiem(goc, "KHAC")[0] == kn.KHONG
