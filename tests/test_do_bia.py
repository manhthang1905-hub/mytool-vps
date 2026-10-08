"""Đo độ đọc được của ảnh bìa + kiểu chữ theo nền (core/do_bia.py, 09/10/2026).

Ảnh TỔNG HỢP bằng PIL (nền sáng / tối / ấm-rối) — không dùng ảnh/tên kênh thật."""

from __future__ import annotations

import os
import random

import pytest
from PIL import Image, ImageDraw, ImageFont

from core import bia_theo_khuon as btk
from core import do_bia


def _nen(kieu: str) -> Image.Image:
    rnd = random.Random(7)
    mau = {"sang": (245, 236, 215), "toi": (20, 10, 40), "am_ron": (200, 110, 40), "cam": (230, 120, 30)}[kieu]
    im = Image.new("RGB", (1280, 720), mau)
    if kieu == "am_ron":
        d = ImageDraw.Draw(im)
        for _ in range(600):
            x, y = rnd.randrange(1280), rnd.randrange(720)
            c = rnd.choice([(150, 70, 20), (240, 160, 70), (110, 50, 15), (230, 120, 30)])
            d.rectangle([x, y, x + rnd.randrange(10, 80), y + rnd.randrange(4, 30)], fill=c)
    return im


def _font_nhat():
    duong = btk._tim_font("", "人生後半", "ja")  # noqa: SLF001
    if not duong:
        pytest.skip("máy không có font Nhật")
    return duong


TANG = btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", {})  # trắng trên; ĐỎ + VÀNG dưới (màu khuôn cũ)


# ── số đo cơ bản ──────────────────────────────────────────────────────────────


def test_tuong_phan_wcag_chuan():
    assert do_bia.ti_le_tuong_phan(1.0, 0.0) == pytest.approx(21.0)
    assert do_bia.ti_le_tuong_phan(do_bia.do_sang((255, 255, 255)), do_bia.do_sang((0, 0, 0))) == pytest.approx(21.0)
    assert do_bia.do_sang((128, 128, 128)) == pytest.approx(0.2158, abs=1e-3)


def test_chu_do_tren_nen_cam_TRUOT():
    arr, canh = do_bia.mang_nen(_nen("cam"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 1100, 600), [(232, 32, 42)], vien_mau=None, vien_px=0,
                            cao_px=130, H=720)
    assert not d["dat"] and d["tuong_phan"] < 3.0


def test_chu_do_vien_den_tren_nen_am_ron_TRUOT_vien_khong_cuu():
    arr, canh = do_bia.mang_nen(_nen("am_ron"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 1100, 560), [(232, 32, 42)], vien_mau=(10, 8, 14), vien_px=12,
                            cao_px=110, H=720)
    assert not d["dat"]


def test_chu_trang_vien_den_tren_nen_toi_DAT():
    arr, canh = do_bia.mang_nen(_nen("toi"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 1100, 560), [(255, 255, 255)], vien_mau=(10, 8, 14),
                            vien_px=12, cao_px=110, H=720)
    assert d["dat"] and d["tuong_phan"] > 10


def test_chu_nho_TRUOT_du_tuong_phan_cao():
    arr, canh = do_bia.mang_nen(_nen("toi"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 600, 440), [(255, 255, 255)], vien_mau=(10, 8, 14), vien_px=4,
                            cao_px=30, H=720)
    assert not d["dat"] and any("chữ nhỏ" in x for x in d["ly_do"])


def test_khong_co_dong_chinh_lon_thi_bia_TRUOT():
    d = do_bia.cham_dong(l_chu=[1.0], l_vien=0.0, vien_px=10, cao_px=80, H=720, l_nen=[0.01] * 50)
    assert d["dat"]                                         # dòng tự nó đạt (11%)…
    bc = do_bia.tong_hop([d, dict(d)])
    assert bc["dat"] is False and "dòng chính" in bc["ly_do"][0]   # …nhưng bìa không có dòng ≥ 14%


def test_nhom_doc_duoc():
    assert do_bia.nhom_doc_duoc(None, None) == ""
    assert do_bia.nhom_doc_duoc(90, True) == "cao"
    assert do_bia.nhom_doc_duoc(60, True) == "vua"
    assert do_bia.nhom_doc_duoc(95, False) == "thap"


# ── kiểu chữ theo nền lúc VẼ ─────────────────────────────────────────────────


@pytest.mark.parametrize("kieu", ["sang", "toi", "am_ron"])
def test_ve_thich_nghi_DAT_tren_moi_nen(tmp_path, kieu):
    _font_nhat()
    nen = tmp_path / "nen.png"
    _nen(kieu).save(nen)
    dich = str(tmp_path / "thumb_001.png")
    bc: dict = {}
    assert btk.ve_chu_len_anh(str(nen), dich, btk.bo_tri_chu("khuon", TANG), bao_cao=bc)
    assert bc["dat"] is True, do_bia.tom_tat(bc)
    assert bc["cach"] == "chinh_xac" and bc["tuong_phan_min"] >= 3.0
    # báo cáo nằm cạnh ảnh; bộ chấm MÙ (không biết gì về cách vẽ) cũng thấy ĐẠT
    assert os.path.isfile(do_bia.duong_bao_cao(dich))
    mu = do_bia.cham_anh(dich)
    assert mu["tin_cay"] and mu["dat"] is True, do_bia.tom_tat(mu)


def test_nen_sang_chon_chu_TOI_vien_trang(tmp_path):
    _font_nhat()
    nen = tmp_path / "nen.png"
    _nen("sang").save(nen)
    bc: dict = {}
    btk.ve_chu_len_anh(str(nen), str(tmp_path / "t.png"), btk.bo_tri_chu("khuon", TANG), bao_cao=bc)
    dong1 = bc["dong"][0]
    assert dong1["vien_mau"] == "#FFFFFF"
    assert do_bia.do_sang(tuple(int(dong1["mau_chu"][0][i:i + 2], 16) for i in (1, 3, 5))) < 0.05


def test_mau_nhan_do_bi_doi_tren_nen_am_ron(tmp_path):
    _font_nhat()
    nen = tmp_path / "nen.png"
    _nen("am_ron").save(nen)
    bc: dict = {}
    btk.ve_chu_len_anh(str(nen), str(tmp_path / "t.png"), btk.bo_tri_chu("khuon", TANG), bao_cao=bc)
    mau = [m for d in bc["dong"] for m in d["mau_chu"]]
    assert "#E8202A" not in mau          # đỏ khuôn trượt trên nền ấm-rối → đổi màu nhấn đạt


def _bia_kieu_cu(nen: Image.Image, font_duong: str) -> Image.Image:
    """Bìa vẽ theo KIỂU CŨ: đỏ + viền đen mỏng, đặt thẳng lên nền ấm-rối."""
    im = nen.copy()
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font_duong, 150)
    d.text((60, 60), "人生後半で", font=f, fill=(232, 32, 42), stroke_width=6, stroke_fill=(10, 8, 14))
    d.text((60, 400), "強くなる男", font=f, fill=(232, 32, 42), stroke_width=6, stroke_fill=(10, 8, 14))
    return im


def test_cham_mu_bia_kieu_cu_do_tren_nen_am_TRUOT():
    im = _bia_kieu_cu(_nen("am_ron"), _font_nhat())
    bc = do_bia.cham_anh(im)
    assert bc["tin_cay"] and bc["dat"] is False, do_bia.tom_tat(bc)


def test_ve_lai_tu_anh_ghep_DAT_khong_goi_AI(tmp_path):
    im = _bia_kieu_cu(_nen("am_ron"), _font_nhat())
    dich = str(tmp_path / "lai.png")
    bc: dict = {}
    assert do_bia.ve_lai_tu_anh_ghep(im, do_bia._chia_tang("人生後半で強くなる男"), dich, bao_cao=bc)  # noqa: SLF001
    assert bc["dat"] is True, do_bia.tom_tat(bc)
    assert do_bia.cham_tep(dich)["dat"] is True


def test_chia_tang_cat_sau_tro_tu_khong_cat_giua_tu():
    tang = do_bia._chia_tang("気を遣う人ほど雑に扱われる理由")  # noqa: SLF001
    assert btk.chu_cua_tang(tang[0]) == "気を遣う人ほど"
    assert btk.chu_cua_tang(tang[1]) == "雑に扱われる理由"


# ── báo cáo cạnh ảnh: đúng ảnh mới dùng ───────────────────────────────────────


def test_bao_cao_theo_van_tay(tmp_path):
    _font_nhat()
    nen = tmp_path / "nen.png"
    _nen("toi").save(nen)
    png = str(tmp_path / "thumb_003.png")
    btk.ve_chu_len_anh(str(nen), png, btk.bo_tri_chu("khuon", TANG))
    chon = str(tmp_path / "CHON-thumb_003.jpg")
    Image.open(png).convert("RGB").save(chon, quality=90)
    assert do_bia.cham_tep(chon)["cach"] == "chinh_xac"         # jpg xuất lại vẫn dùng báo cáo chính xác
    Image.new("RGB", (1280, 720), (200, 200, 200)).save(chon)   # ảnh khác hẳn → không dùng báo cáo cũ
    assert do_bia.cham_tep(chon)["cach"] != "chinh_xac"


# ── nối dây: chọn bìa, QA, hồ sơ, tự học ─────────────────────────────────────


def test_chon_bia_loai_tam_kho_doc_khi_co_tam_dat(tmp_path):
    from core import chon_bia
    font = _font_nhat()
    tot = str(tmp_path / "thumb_001.png")
    nen = tmp_path / "nen.png"
    _nen("toi").save(nen)
    btk.ve_chu_len_anh(str(nen), tot, btk.bo_tri_chu("khuon", TANG))
    xau = str(tmp_path / "thumb_002.png")
    _bia_kieu_cu(_nen("am_ron"), font).save(xau)
    ds = [chon_bia._KetQuaCham(so=1, tong=50.0), chon_bia._KetQuaCham(so=2, tong=90.0)]  # noqa: SLF001
    chon_bia._loai_kho_doc(ds, {1: tot, 2: xau}, lambda _s: None)  # noqa: SLF001
    assert ds[0].loai == "" and ds[1].loai.startswith("khó đọc")


def test_chon_bia_khong_loai_khi_khong_tam_nao_dat(tmp_path):
    from core import chon_bia
    xau = str(tmp_path / "thumb_002.png")
    _bia_kieu_cu(_nen("am_ron"), _font_nhat()).save(xau)
    ds = [chon_bia._KetQuaCham(so=2, tong=90.0)]  # noqa: SLF001
    chon_bia._loai_kho_doc(ds, {2: xau}, lambda _s: None)  # noqa: SLF001
    assert ds[0].loai == ""


def test_qa_chan_bia_kho_doc(tmp_path):
    from core import qa_truoc_dang
    tep = str(tmp_path / "CHON-thumb_002.jpg")
    _bia_kieu_cu(_nen("am_ron"), _font_nhat()).save(tep, quality=90)
    loi, _cb = qa_truoc_dang._kiem_thumbnail(tep)  # noqa: SLF001
    assert any("khó đọc" in x for x in loi)


def test_qa_anh_khong_chu_chi_canh_bao(tmp_path):
    from core import qa_truoc_dang
    tep = str(tmp_path / "CHON-thumb_001.jpg")
    _nen("sang").save(tep, quality=90)
    loi, cb = qa_truoc_dang._kiem_thumbnail(tep)  # noqa: SLF001
    assert not loi and any("không đo được" in x for x in cb)


class _BC:
    """Bối cảnh giả tối thiểu cho cổng đọc được của khâu bìa."""

    def __init__(self, che_do="nguyen_goc"):
        import types
        self.goc = ""
        self.kenh = types.SimpleNamespace(ma="KX", ngon_ngu="ja", che_do_tieu_de=che_do)
        self.dong = []

    def ghi(self, s):
        self.dong.append(s)


def _thu_muc_bia(tmp_path, font):
    import json
    tm = tmp_path / "7-thumbnail"
    tm.mkdir()
    _bia_kieu_cu(_nen("am_ron"), font).save(tm / "thumb_002.png")
    Image.open(tm / "thumb_002.png").convert("RGB").save(tm / "CHON-thumb_002.jpg", quality=90)
    return tm, json


def test_cong_doc_duoc_doi_sang_tam_khac_dat(tmp_path):
    from core import auto_khau
    tm, json = _thu_muc_bia(tmp_path, _font_nhat())
    nen = tmp_path / "nen.png"
    _nen("toi").save(nen)
    btk.ve_chu_len_anh(str(nen), str(tm / "thumb_001.png"), btk.bo_tri_chu("khuon", TANG))
    (tm / "chon-bia.json").write_text(json.dumps({"chon": {"so": 2, "tep": "CHON-thumb_002.jpg"}, "ung_vien": [
        {"so": 2, "tong_diem": 90, "loai": ""}, {"so": 1, "tong_diem": 60, "loai": ""}]}), encoding="utf-8")
    r = auto_khau._cong_doc_duoc_bia(_BC(), None, str(tm), "人生後半で 強くなる男たち")  # noqa: SLF001
    assert r["tep"] == "CHON-thumb_001.jpg" and r["bao_cao"]["dat"] is True
    assert not (tm / "CHON-thumb_002.jpg").exists() and (tm / "_truoc-do-bia" / "CHON-thumb_002.jpg").exists()


def test_cong_doc_duoc_ve_lai_tam_da_chon(tmp_path):
    from core import auto_khau
    tm, _json = _thu_muc_bia(tmp_path, _font_nhat())
    r = auto_khau._cong_doc_duoc_bia(_BC(), None, str(tm), "人生後半で 強くなる男")  # noqa: SLF001
    assert r["sua"].startswith("vẽ lại") and r["bao_cao"]["dat"] is True
    assert do_bia.cham_tep(str(tm / "CHON-thumb_002.jpg"))["dat"] is True


def test_cong_doc_duoc_het_cach_thi_CHAN(tmp_path, monkeypatch):
    from core import auto_khau
    tm, _json = _thu_muc_bia(tmp_path, _font_nhat())
    monkeypatch.setattr(do_bia, "ve_lai_tu_anh_ghep", lambda *a, **k: k["bao_cao"].update(
        {"dat": False, "diem": 10, "ly_do": ["giả"]}) or True)
    with pytest.raises(RuntimeError, match="KHÔNG bàn giao"):
        auto_khau._cong_doc_duoc_bia(_BC(), None, str(tm), "人生後半で 強くなる男")  # noqa: SLF001


def test_xep_doi_bia_ghi_hang_sua_cho_may_dom(tmp_path):
    import json
    from core import ho_so_video
    from core.giam_doc import cuu_ctr
    _font_nhat()
    goc = str(tmp_path)
    os.makedirs(ho_so_video.duong_thu_muc_ho_so(goc, "KX"), exist_ok=True)
    with open(ho_so_video.duong_tep_ho_so(goc, "KX", "KX-0001"), "w", encoding="utf-8") as tep:
        json.dump(dict(ho_so_video._khung_ho_so("KX", "KX-0001"), video_id="vidGIA00001"), tep)  # noqa: SLF001
    nen = tmp_path / "nen.png"
    _nen("toi").save(nen)
    moi = str(tmp_path / "moi.png")
    btk.ve_chu_len_anh(str(nen), moi, btk.bo_tri_chu("khuon", TANG))
    r = do_bia.xep_doi_bia(goc, "KX", "KX-0001", moi, ghi=lambda _s: None)
    hang = cuu_ctr.doc_hang(goc)
    assert len(hang) == 1 and hang[0]["buoc"] == "bia" and hang[0]["anh"] == os.path.abspath(moi)
    assert hang[0]["video_id"] == "vidGIA00001" and hang[0]["trang_thai"] == "cho" and r["viec"]
    hs = ho_so_video.doc_ho_so(goc, "KX", "KX-0001")
    assert hs["lich_su_sua"] and hs["thumbnail"]["bia_doc_duoc"] in ("cao", "vua")
    # bìa TRƯỢT thì không xếp
    xau = str(tmp_path / "xau.png")
    _bia_kieu_cu(_nen("am_ron"), _font_nhat()).save(xau)
    with pytest.raises(RuntimeError, match="chưa ĐẠT"):
        do_bia.xep_doi_bia(goc, "KX", "KX-0001", xau, ghi=lambda _s: None)


def test_ho_so_va_truc_hoc_bia_doc_duoc():
    from core import ho_so_video, tu_hoc
    bc = do_bia.tong_hop([do_bia.cham_dong(l_chu=[1.0], l_vien=0.0, vien_px=10, cao_px=140, H=720,
                                           l_nen=[0.01] * 50)])
    th = ho_so_video._doc_duoc_bia("", bc)  # noqa: SLF001
    assert th["bia_doc_duoc"] == "cao" and th["bia_tuong_phan_min"] > 10 and th["bia_diem"] >= 75
    assert "bia_doc_duoc" in tu_hoc.TRUC and "bia_doc_duoc" in tu_hoc.TRUC_BAO_BI
    assert tu_hoc._nhan_do({"thumbnail": th})["bia_doc_duoc"] == "cao"  # noqa: SLF001
    assert "bia_doc_duoc" not in tu_hoc._nhan_do({"thumbnail": {}})  # noqa: SLF001
