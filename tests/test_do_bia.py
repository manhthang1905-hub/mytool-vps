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
    mau = {"sang": (245, 236, 215), "toi": (20, 10, 40), "am_ron": (200, 110, 40), "cam": (230, 120, 30),
           "go_nau": (96, 42, 26), "xanh_den": (50, 65, 115), "loang": (245, 236, 215)}[kieu]
    im = Image.new("RGB", (1280, 720), mau)
    d = ImageDraw.Draw(im)
    if kieu in ("am_ron", "go_nau"):
        bang = {"am_ron": [(150, 70, 20), (240, 160, 70), (110, 50, 15), (230, 120, 30)],
                "go_nau": [(70, 30, 18), (120, 58, 34), (60, 26, 14), (140, 70, 40)]}[kieu]
        for _ in range(600):
            x, y = rnd.randrange(1280), rnd.randrange(720)
            d.rectangle([x, y, x + rnd.randrange(10, 80), y + rnd.randrange(4, 30)], fill=rnd.choice(bang))
    if kieu == "loang":  # nửa trái kem, nửa phải tường tối (kiểu bìa có cửa mở vào phòng tối)
        d.rectangle([560, 0, 1280, 720], fill=(28, 30, 40))
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


def test_chu_do_vien_den_tren_go_nau_do_TRUOT_vien_khong_cuu():
    # Kiểu bìa chủ dự án chấm YẾU 09/10: đỏ viền đen dày trên gỗ nâu đỏ — viền đen ↔ gỗ tối không tách.
    arr, canh = do_bia.mang_nen(_nen("go_nau"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 1100, 560), [(217, 33, 33)], vien_mau=(10, 8, 14), vien_px=12,
                            cao_px=110, H=720)
    assert not d["dat"] and d["vien_day"]


def test_chu_trang_vien_den_day_tren_nen_kem_DAT_vien_ganh():
    # Chủ dự án 09/10: chữ trắng viền đen DÀY trên nền kem đọc rõ — "chỉ viền gánh" không được là lỗi.
    arr, canh = do_bia.mang_nen(_nen("sang"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 1100, 540), [(255, 255, 255)], vien_mau=(10, 8, 14),
                            vien_px=12, cao_px=120, H=720)
    assert d["dat"] and d["ganh"] == "vien" and d["tuong_phan_nen"] < 1.3, d
    assert not any("gánh" in x for x in d["canh_bao"])


def test_vien_mong_so_voi_net_chu_khong_ganh():
    arr, canh = do_bia.mang_nen(_nen("sang"))
    d = do_bia.cham_dong_ve(arr, canh, (100, 400, 1100, 560), [(255, 255, 255)], vien_mau=(10, 8, 14),
                            vien_px=5, cao_px=140, H=720)     # 1,25 px ở 320×180 nhưng chỉ 3,6% nét chữ
    assert not d["dat"] and not d["vien_day"] and "viền mỏng" in d["ly_do"][0]


def test_nen_loang_nua_kem_nua_toi_DAT():
    # Bộ đo v1 lấy phía xấu của chữ (kem) và của viền (tối) RIÊNG RẼ → trượt oan bìa đọc rõ.
    arr, canh = do_bia.mang_nen(_nen("loang"))
    d = do_bia.cham_dong_ve(arr, canh, (60, 80, 1200, 210), [(255, 255, 255)], vien_mau=(10, 8, 14),
                            vien_px=12, cao_px=125, H=720)
    assert d["dat"] and d["tuong_phan"] > 5, d


def test_chu_do_rat_lon_tren_xanh_den_DAT_nho_sac_do_chu_nho_thi_khong():
    arr, canh = do_bia.mang_nen(_nen("xanh_den"))
    lon = do_bia.cham_dong_ve(arr, canh, (60, 450, 700, 610), [(246, 4, 2)], vien_mau=(10, 8, 14), vien_px=14,
                              cao_px=140, H=720)
    assert lon["dat"] and "sac_do" in lon["ganh"], lon
    nho = do_bia.cham_dong_ve(arr, canh, (60, 450, 700, 520), [(246, 4, 2)], vien_mau=(10, 8, 14), vien_px=6,
                              cao_px=60, H=720)
    assert not nho["dat"]


def test_nguong_theo_co_chu():
    assert do_bia.nguong_theo_co(5) == pytest.approx(4.5)
    assert do_bia.nguong_theo_co(7) == pytest.approx(4.5)
    assert do_bia.nguong_theo_co(12) == pytest.approx(3.0)
    assert do_bia.nguong_theo_co(15) == pytest.approx(2.85)
    assert do_bia.nguong_theo_co(30) == pytest.approx(2.7)


def test_rat_kho_doc_chi_khi_xa_duoi_nguong():
    def bia(l_chu):
        return do_bia.tong_hop([do_bia.cham_dong(l_chu=[l_chu], l_vien=None, vien_px=0, cao_px=150, H=720,
                                                 l_nen=[0.10] * 50)])
    nhe = bia(0.22)        # ~2,3:1 ở dòng 21% (ngưỡng 2,7) — trượt nhẹ
    nang = bia(0.12)       # ~1,15:1 — chìm hẳn
    assert nhe["dat"] is False and not do_bia.rat_kho_doc(nhe)
    assert nang["dat"] is False and do_bia.rat_kho_doc(nang)
    assert not do_bia.rat_kho_doc({"dat": None, "dong": []})


def test_cham_mu_chu_trang_vien_den_day_tren_nen_loang_DAT():
    font = ImageFont.truetype(_font_nhat(), 150)
    im = _nen("loang")
    ImageDraw.Draw(im).text((40, 60), "人と群れない人", font=font, fill=(252, 252, 250), stroke_width=14,
                            stroke_fill=(5, 5, 8))
    bc = do_bia.cham_anh(im)
    assert bc["tin_cay"] and bc["dat"] is True, do_bia.tom_tat(bc)


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


def _co_nen_sach(tm):
    """Biến thư mục bìa thành tấm CODE vẽ chữ: nền sạch `znen-thumb_002.png` + kế hoạch có chữ tầng."""
    _nen("am_ron").save(tm / "znen-thumb_002.png")
    btk.ghi_ke_hoach(str(tm), {"muc": [{"so": 2, "nhom": "khuon", "ve_chu": "ma", "chu_tang": TANG}]})


def test_cong_doc_duoc_ve_lai_tren_nen_sach_khong_khung(tmp_path):
    from core import auto_khau
    tm, _json = _thu_muc_bia(tmp_path, _font_nhat())
    _co_nen_sach(tm)
    r = auto_khau._cong_doc_duoc_bia(_BC(), None, str(tm), "人生後半で 強くなる男たち")  # noqa: SLF001
    assert r["sua"].startswith("vẽ lại trên nền sạch") and "không khung" in r["sua"], r
    bc = do_bia.cham_tep(str(tm / "CHON-thumb_002.jpg"))
    assert bc["dat"] is True and bc["bo_cuc"]["so_khung"] == 0 and do_bia.bo_cuc_dat(bc)


def test_cong_doc_duoc_khong_nen_sach_khong_xoa_chu_rat_kho_doc_thi_CHAN(tmp_path, monkeypatch):
    from core import auto_khau

    def cam(*_a, **_k):
        raise AssertionError("cổng không được xoá chữ cũ để vẽ lại khi không có nền sạch")
    monkeypatch.setattr(do_bia, "ve_lai_tu_anh_ghep", cam)
    tm, _json = _thu_muc_bia(tmp_path, _font_nhat())       # đỏ viền mảnh trên nền ấm-rối: RẤT khó đọc
    with pytest.raises(RuntimeError, match="KHÔNG bàn giao"):
        auto_khau._cong_doc_duoc_bia(_BC(), None, str(tm), "人生後半で 強くなる男")  # noqa: SLF001
    assert (tm / "CHON-thumb_002.jpg").exists() and not (tm / "_lam-lai").exists()


def _truot_nhe(**them):
    d = do_bia.cham_dong(l_chu=[0.22], l_vien=None, vien_px=0, cao_px=150, H=720, l_nen=[0.10] * 50)
    return dict(do_bia.tong_hop([d], cach="mu"), **them)


def test_cong_doc_duoc_truot_nhe_khong_nen_sach_GIU_GOC(tmp_path, monkeypatch):
    from core import auto_khau
    tm, _json = _thu_muc_bia(tmp_path, _font_nhat())
    goc = (tm / "CHON-thumb_002.jpg").read_bytes()
    monkeypatch.setattr(do_bia, "cham_tep", lambda _t: _truot_nhe())
    b = _BC()
    r = auto_khau._cong_doc_duoc_bia(b, None, str(tm), "人生後半で 強くなる男")  # noqa: SLF001
    assert r.get("giu_goc") and r["tep"] == "CHON-thumb_002.jpg" and r["sua"] == ""
    assert (tm / "CHON-thumb_002.jpg").read_bytes() == goc and any("GIỮ bản gốc" in s for s in b.dong)


def test_cong_doc_duoc_ve_lai_dat_nhung_che_chu_the_thi_GIU_GOC(tmp_path, monkeypatch):
    from core import auto_khau
    tm, _json = _thu_muc_bia(tmp_path, _font_nhat())
    _co_nen_sach(tm)
    goc = (tm / "CHON-thumb_002.jpg").read_bytes()
    monkeypatch.setattr(do_bia, "cham_tep", lambda _t: _truot_nhe())

    def ve_gia(_nen, dich, _tang, **k):  # điểm đo tốt hơn nhưng khung đè lên nhân vật
        Image.new("RGB", (1280, 720), (9, 9, 9)).save(dich)
        k["bao_cao"].update({"dat": True, "diem": 99, "dong": [{}],
                             "bo_cuc": {"so_khung": 2, "chong_khung": True, "che_chu_the": 0.6}})
        return True
    monkeypatch.setattr(btk, "ve_chu_len_anh", ve_gia)
    r = auto_khau._cong_doc_duoc_bia(_BC(), None, str(tm), "人生後半で 強くなる男")  # noqa: SLF001
    assert r.get("giu_goc") and (tm / "CHON-thumb_002.jpg").read_bytes() == goc


def test_qa_truot_nhe_chi_canh_bao(tmp_path, monkeypatch):
    from core import qa_truoc_dang
    tep = str(tmp_path / "CHON-thumb_002.jpg")
    _nen("sang").save(tep, quality=90)
    monkeypatch.setattr(do_bia, "cham_tep", lambda _t: _truot_nhe())
    loi, cb = qa_truoc_dang._kiem_thumbnail(tep)  # noqa: SLF001
    assert not loi and any("trượt nhẹ" in x for x in cb)


# ── chủ thể: khung nền không che nhân vật, không chồng khung ─────────────────


def _nen_soc():
    """Nền sọc trắng/đen 4 px — chữ VIỀN MẢNH (không gánh) trượt mọi màu nếu không có khung."""
    im = Image.new("RGB", (1280, 720), (250, 250, 250))
    d = ImageDraw.Draw(im)
    for x in range(0, 1280, 8):
        d.rectangle([x, 0, x + 3, 720], fill=(8, 8, 8))
    return im


def test_ban_do_chu_the_bat_vat_noi_bat():
    im = _nen("go_nau")
    ImageDraw.Draw(im).ellipse([860, 180, 1140, 460], fill=(250, 150, 30))
    m = do_bia.ban_do_chu_the(do_bia.mang_nen(im)[0])
    assert do_bia.che_chu_the(m, (860, 180, 1140, 460), 1280, 720) > 0.6
    assert do_bia.che_chu_the(m, (40, 500, 400, 700), 1280, 720) < 0.25


def test_khung_chi_khi_can_va_khong_de_len_chu_the():
    import numpy as np
    arr, canh = do_bia.mang_nen(_nen_soc())
    dong = [{"hop": (100, 300, 1100, 440), "mau_doan": [(255, 255, 255)], "vien_px": 2, "cao_px": 120}]
    (k, d), = do_bia.chon_kieu_khoi(arr, canh, dong, H=720)
    assert k.get("khung") and d["dat"]                               # cần khung thì mới có khung
    (k, d), = do_bia.chon_kieu_khoi(arr, canh, dong, H=720, cho_khung=False)
    assert not k.get("khung")
    toan_chu_the = np.ones((72, 128), dtype=bool)
    (k, d), = do_bia.chon_kieu_khoi(arr, canh, dong, H=720, chu_the=toan_chu_the)
    assert not k.get("khung")                                         # khung sẽ che chủ thể → không dùng


def test_bo_cuc_dat():
    assert do_bia.bo_cuc_dat({})                                      # bộ đo mù: không kết luận bố cục
    assert do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 1, "chong_khung": False, "che_chu_the": 0.1}})
    assert not do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 2, "chong_khung": True, "che_chu_the": 0.0}})
    assert not do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 1, "chong_khung": False, "che_chu_the": 0.5}})
    assert do_bia.khung_chong_nhau([(0, 0, 100, 100), (50, 50, 150, 150)])
    assert not do_bia.khung_chong_nhau([(0, 0, 100, 100), (0, 120, 100, 200)])


def test_bao_cao_bo_do_cu_bi_cham_lai(tmp_path):
    _font_nhat()
    nen = tmp_path / "nen.png"
    _nen("toi").save(nen)
    png = str(tmp_path / "thumb_003.png")
    btk.ve_chu_len_anh(str(nen), png, btk.bo_tri_chu("khuon", TANG))
    assert do_bia.cham_tep(png)["cach"] == "chinh_xac"
    import json
    p = do_bia.duong_bao_cao(png)
    du = json.load(open(p, encoding="utf-8"))
    du.pop("phien_ban")                                               # báo cáo của bộ đo v1
    json.dump(du, open(p, "w", encoding="utf-8"))
    assert do_bia.cham_tep(png)["cach"] == "mu"


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
