"""ADN phong cách bìa (`core/adn_bia`, 22/10/2026) — ảnh tổng hợp nhỏ, không mạng, không AI."""

from __future__ import annotations

import json
import math
import os

import pytest
from PIL import Image, ImageDraw

from core import adn_bia
from core import bia_lo
from core import bia_theo_khuon as btk

TIM, HO_PHACH, CAM = (40, 12, 64), (125, 72, 24), (235, 125, 30)


def _canh(duong: str, nen, *, vang: int = 0, x_nv: float = 0.5) -> str:
    """Cảnh tổng hợp 640×360: nền một màu (lệch nhẹ `vang`) + quầng nhân vật CAM (như bìa TL3)."""
    im = Image.new("RGB", (640, 360), tuple(max(0, min(255, c + vang)) for c in nen))
    v = ImageDraw.Draw(im)
    cx = int(640 * x_nv)
    v.ellipse((cx - 70, 60, cx + 70, 200), fill=CAM, outline=(0, 0, 0), width=6)
    v.rectangle((cx - 12, 200, cx + 12, 330), fill=(10, 10, 10))
    im.save(duong)
    return duong


def _chu_nghieng(duong: str, goc: float, nen=(150, 120, 90)) -> str:
    """Ba dòng "chữ" giả (ô trắng viền đen dày, có nét đen bên trong) XOAY `goc` độ (+ = lên về bên phải)."""
    lop = Image.new("RGBA", (640, 360), (0, 0, 0, 0))
    v = ImageDraw.Draw(lop)
    for hang, y in enumerate((60, 150, 240)):
        for k in range(9 - hang):
            x = 70 + k * 52
            v.rectangle((x, y, x + 42, y + 56), fill=(255, 255, 255), outline=(0, 0, 0), width=5)
            v.line((x + 8, y + 28, x + 34, y + 28), fill=(0, 0, 0), width=4)
    lop = lop.rotate(goc, resample=Image.BICUBIC, center=(320, 180))
    im = Image.new("RGBA", (640, 360), nen + (255,))
    Image.alpha_composite(im, lop).convert("RGB").save(duong)
    return duong


def _thang(tmp_path, n=4, nen=TIM, w=(9000, 6.0)):
    return [(adn_bia.do_adn(_canh(str(tmp_path / "w{0}.png".format(i)), nen, vang=3 * i, x_nv=0.4 + 0.05 * i)),
             w[0] * w[1] / 100.0) for i in range(n)]


def test_cong_sac_tim_dat_ho_phach_truot(tmp_path):
    dich = adn_bia.tong_hop(_thang(tmp_path))
    assert dich["nguong_hue"] >= adn_bia.HUE_NGUONG_SAN and "purple" in " ".join(dich["ten_mau"])
    tim = adn_bia.do_adn(_canh(str(tmp_path / "tim.png"), TIM, vang=-4, x_nv=0.6))
    ho = adn_bia.do_adn(_canh(str(tmp_path / "ho.png"), HO_PHACH))
    assert adn_bia.kiem(tim, dich) == []
    ly = adn_bia.kiem(ho, dich)
    assert ly and ly[0].startswith("bảng màu lệch bìa thắng")
    assert adn_bia.hellinger(ho["hue"], dich["hue"]) > dich["nguong_hue"] >= adn_bia.hellinger(tim["hue"], dich["hue"])


def test_kenh_toi_chan_canh_sang_tru_o_kham_pha(tmp_path):
    dich = adn_bia.tong_hop(_thang(tmp_path))
    assert dich["toi"] is True and dich["nguong_sang"] is not None
    sang = adn_bia.do_adn(_canh(str(tmp_path / "sang.png"), (150, 90, 200)))  # cùng tông tím nhưng SÁNG
    ly = adn_bia.kiem(sang, dich)
    assert any(x.startswith("cảnh sáng hơn bìa thắng") for x in ly)
    assert not any(x.startswith("cảnh sáng") for x in adn_bia.kiem(sang, dich, kham_pha=True))


def test_it_bang_chung_khong_bat_cong(tmp_path):
    dich = adn_bia.tong_hop(_thang(tmp_path, n=3, w=(1000, 3.0)))  # tổng 90 lượt bấm < BAM_CONG
    assert dich["nguong_hue"] is None and dich["nguong_sang"] is None
    assert adn_bia.kiem(adn_bia.do_adn(_canh(str(tmp_path / "ho.png"), HO_PHACH)), dich) == []
    assert adn_bia.tong_hop([]) == {}


@pytest.mark.parametrize("goc", [6.0, -5.0, 0.0])
def test_do_goc_nghieng_dong_chu(tmp_path, goc):
    d = adn_bia.do_adn(_chu_nghieng(str(tmp_path / "c.png"), goc))
    assert d["so_dong"] >= 2
    assert abs(d["goc_chu"] - goc) <= 1.0, d["goc_dong"]
    assert d["nghieng"] is (abs(goc) >= adn_bia.GOC_THANG)


def test_goc_ve_theo_ho_va_dai_theo_chu():
    def bia(g, gd=None, nghieng=True):
        return {"hue": [1.0] + [0.0] * 11, "sang_nen": 0.5, "goc_chu": g, "nghieng": nghieng, "goc_dai": gd}
    ho_dai = adn_bia.tong_hop([(bia(8.25, 9.5), 13000), (bia(5.25, 3.2), 11000)])
    gv = adn_bia.goc_ve(ho_dai)
    assert gv == {"nghieng": 8.0, "nghieng_dai": 8.0}, gv  # kẹp GOC_VE_TOI_DA; dải đi cùng chữ
    thang = adn_bia.tong_hop([(bia(0.25, None, False), 3700), (bia(0.5, None, False), 2700)])
    assert adn_bia.goc_ve(thang) == {}
    chi_dai = adn_bia.tong_hop([(bia(0.0, 4.0, False), 5000), (bia(0.3, 3.0, False), 4000)])
    assert adn_bia.goc_ve(chi_dai) == {"nghieng_dai": 4.0}  # chữ thẳng, dải nghiêng đo được
    # họ không có ADN → lùi ADN kênh
    assert adn_bia.goc_ve({}, ho_dai) == gv


def test_cau_lenh_va_ghi_chu_giam_khao(tmp_path):
    dich = adn_bia.tong_hop(_thang(tmp_path), [({"kieu_sang": "glow", "mau": ["deep purple"], "ta": "Glowing."}, 1)])
    cau = adn_bia.cau_lenh(dich)
    assert "DARK scene" in cau and "deep purple" in cau and "glow" in cau and cau.endswith(".")
    assert "dark scene" in adn_bia.ghi_chu_giam_khao(dich)
    assert adn_bia.cau_lenh({}) == "" and adn_bia.ghi_chu_giam_khao(None) == ""


def test_adn_thu_muc_theo_ho_cache_va_bo(tmp_path, monkeypatch):
    tm = tmp_path / "thang"
    tm.mkdir()
    bia = []
    for i, ho in enumerate(("tran", "dai", "tran"), 1):
        _canh(str(tm / "{0}.jpg".format(i)), TIM, vang=2 * i)
        bia.append({"tep": "{0}.jpg".format(i), "video_id": "V{0}".format(i), "imp": 30000, "ctr": 5.0, "kieu": ho})
    (tm / "thang.json").write_text(json.dumps({"bia": bia}), encoding="utf-8")
    goc = str(tmp_path / "goc")
    a = adn_bia.adn_thu_muc(str(tm), goc=goc)
    assert a["kenh"]["n"] == 3 and set(a["ho"]) == {"tran", "dai"} and a["ho"]["tran"]["n"] == 2
    assert os.path.isfile(str(tm / adn_bia.TEP_THANG)) and os.path.isfile(os.path.join(goc, adn_bia.TEP_CACHE))
    # lần sau: cache (không đo lại ảnh nào)
    monkeypatch.setattr(adn_bia, "do_adn", lambda *a, **k: (_ for _ in ()).throw(AssertionError("đo lại")))
    assert adn_bia.adn_thu_muc(str(tm), goc=goc)["khoa"] == a["khoa"]
    # bỏ một bìa (bìa thắng giấu / bỏ-một-ra): không ghi đè cache tổng hợp
    b = adn_bia.adn_thu_muc(str(tm), goc=goc, bo=[str(tm / "1.jpg")])
    assert b["kenh"]["n"] == 2
    # chạy thử: không ghi gì
    tm2 = tmp_path / "thang2"
    tm2.mkdir()
    monkeypatch.undo()
    _canh(str(tm2 / "a.jpg"), TIM)
    adn_bia.adn_thu_muc(str(tm2), goc=str(tmp_path / "goc2"), ghi=False)
    assert not os.path.exists(str(tm2 / adn_bia.TEP_THANG)) and not os.path.exists(str(tmp_path / "goc2"))


def test_doc_nhin_loc_gia_tri():
    kq = adn_bia.doc_nhin({"bia": [{"so": 1, "anh_sang": "Dark", "kieu_sang": "glow", "mau": ["Deep Purple", " "],
                                    "bo_cuc_chu": "tilted", "nhan_vat": {"co": "large", "vi_tri": "x"}, "ta": "a  b"},
                                   {"so": 9, "anh_sang": "dark"}, {"so": "z"}]}, 2)
    assert list(kq) == [1] and kq[1]["anh_sang"] == "dark" and kq[1]["mau"] == ["deep purple"]
    assert kq[1]["nv_vi_tri"] == "" and kq[1]["ta"] == "a b" and kq[1]["bo_cuc_chu"] == "tilted"


# ── bộ vẽ: dòng xoay ────────────────────────────────────────────────────────


def _can_font():
    if not btk._tim_font("", "同じ車に長く", "ja"):  # noqa: SLF001
        pytest.skip("máy không có phông Nhật")


def test_hop_xoay_va_goc_dong_ve():
    h = (100.0, 100.0, 500.0, 200.0)
    x0, y0, x1, y1 = btk.hop_xoay(h, 8.0)
    assert y0 < 100 and y1 > 200 and x0 > 90 and x1 < 510
    # + = phía phải đi LÊN
    assert btk.xoay_diem(500, 150, (300, 150), 8.0)[1] < 150
    doan = btk.hop_xoay_doan(h, 8.0)
    assert len(doan) == 6 and all((d[3] - d[1]) < (y1 - y0) for d in doan)
    g = {"t": {"nghieng": 8.0}, "hop": h, "kieu": {}}
    assert btk.goc_dong_ve(g, 1280, 720) == 8.0
    assert btk.goc_dong_ve(dict(g, kieu={"khung": {"mau": (0, 0, 0)}}), 1280, 720) == 0.0
    # dòng sát mép trên: dời xuống cho đủ chỗ xoay (góc giữ nguyên)
    goc, dy = btk.bo_tri_xoay(dict(g, hop=(100.0, 10.0, 900.0, 160.0)), 1280, 720)
    assert goc == 8.0 and 0 < dy <= btk.DOI_XOAY * 720
    sat = dict(g, hop=(5.0, 5.0, 1275.0, 200.0))  # dòng cả bề ngang: xoay tràn ngang → thu góc / vẽ thẳng
    assert abs(btk.goc_dong_ve(sat, 1280, 720)) < 8.0
    assert btk.goc_dong_ve({"t": {}, "hop": h, "kieu": {}}, 1280, 720) == 0.0


def test_ve_chu_xoay_bao_cao_va_do_lai_goc(tmp_path):
    _can_font()
    nen = Image.new("RGB", (1280, 720), (150, 110, 80))
    tang = [{"vi_tri": "tren", "phan_mau": [{"chu": "同じ車に長く", "mau": "#FFFFFF"}], "vung": (0.0, 1.0),
             "can": "trai", "mot_dong": True, "co_toi_da_pct": 22, "nghieng": 6.0},
            {"vi_tri": "duoi", "phan_mau": [{"chu": "乗る人ほど", "mau": "#FFFFFF"}], "vung": (0.0, 1.0),
             "can": "trai", "mot_dong": True, "co_toi_da_pct": 22, "nghieng": 6.0}]
    bc: dict = {}
    dich = str(tmp_path / "x.png")
    assert btk.ve_chu_len_anh("", dich, tang, anh_nen=nen, bao_cao=bc, cho_khung=False,
                              uu_tien_kieu=bia_lo.UU_TIEN_VIEN_DEN)
    dong = bc.get("dong") or []
    assert dong and all(d.get("nghieng") == 6.0 and d.get("hop_xoay") and len(d.get("hop_xoay_ds") or []) == 6
                        for d in dong)
    d = adn_bia.do_adn(dich)
    assert d["nghieng"] and abs(d["goc_chu"] - 6.0) <= 1.5, d["goc_dong"]
    # không có `nghieng`: y như cũ (không khoá xoay trong báo cáo)
    bc2: dict = {}
    btk.ve_chu_len_anh("", str(tmp_path / "y.png"), [{k: v for k, v in t.items() if k != "nghieng"} for t in tang],
                       anh_nen=nen, bao_cao=bc2, cho_khung=False, uu_tien_kieu=bia_lo.UU_TIEN_VIEN_DEN)
    assert not any("nghieng" in x for x in bc2.get("dong") or [])


def test_ve_dai_len_xoay_theo_dong():
    nen = Image.new("RGB", (1280, 720), (230, 230, 230))
    tang = [{"phan_mau": [{"chu": "あいう"}], "dai": "#B3191E", "nghieng_dai": 6.0}]
    dong = [{"ten": "あいう", "hop": [100, 300, 900, 420]}]
    import numpy as np
    a = np.asarray(bia_lo.ve_dai_len(nen, tang, dong)).astype(int)
    do = (a[..., 0] > 150) & (a[..., 1] < 60)

    def mep_tren(x: int) -> int:
        return int(np.nonzero(do[:, x])[0].min())
    assert mep_tren(200) - mep_tren(800) > 40  # dải lên về bên phải ~ tan(6°) × 600 ≈ 63 px
    thang = np.asarray(bia_lo.ve_dai_len(nen, [dict(tang[0], nghieng_dai=0)], dong)).astype(int)
    do2 = (thang[..., 0] > 150) & (thang[..., 1] < 60)
    assert abs(int(np.nonzero(do2[:, 200])[0].min()) - int(np.nonzero(do2[:, 800])[0].min())) <= 3


# ── tích hợp bìa lô ─────────────────────────────────────────────────────────


def test_bo_tri_tran_gan_goc_ve():
    tang = [{"phan_mau": [{"chu": "あいうえ", "vai": "nen"}], "to": True}, {"phan_mau": [{"chu": "かきく", "vai": "nen"}]}]
    hs = {"bo_cuc": "trai", "goc_ve": {"nghieng": 7.0, "nghieng_dai": 7.0}, "dai_moi_dong": "#1E6B3A"}
    t2 = bia_lo._bo_tri_tran([dict(t) for t in tang], hs, 6, "trai")  # noqa: SLF001
    assert all(t["nghieng"] == 7.0 and t["nghieng_dai"] == 7.0 and t["dai"] == "#1E6B3A" for t in t2)
    t3 = bia_lo._bo_tri_tran([dict(t) for t in tang], {"bo_cuc": "trai", "goc_ve": {}}, 6, "trai")  # noqa: SLF001
    assert not any("nghieng" in t for t in t3)


def test_loc_san_adn_duoi_kiem_san_va_ly_do(tmp_path):
    k = adn_bia.tong_hop(_thang(tmp_path))
    san = {"mau": {}, "bam": 7.0, "adn": bia_lo.san_adn({"adn_kenh": k})}
    assert san["adn"]["nguong_hue"] == k["nguong_hue"]
    ho = {"ma": "y01-1", "tep": _canh(str(tmp_path / "ho.png"), HO_PHACH), "loai": ""}
    tim = {"ma": "y02-1", "tep": _canh(str(tmp_path / "tim.png"), TIM, x_nv=0.55), "loai": ""}
    sang = {"ma": "p-1", "tep": _canh(str(tmp_path / "sang.png"), (150, 90, 200)), "loai": ""}
    for u in (ho, tim):
        bia_lo.loc_san(u, san)
    bia_lo.loc_san(sang, san, kham_pha=True)
    assert ho["adn_duoi"].startswith("lệch ADN bìa thắng") and ho["adn"]["kc_hue"] > k["nguong_hue"]
    assert not tim.get("adn_duoi") and tim["adn"]["kc_hue"] <= k["nguong_hue"]
    assert not str(sang.get("adn_duoi") or "").count("cảnh sáng")  # ô khám phá: miễn sàn nền tối
    ho["diem"] = {"bam_nhu_thang": 9.0}
    assert any(x.startswith("lệch ADN") for x in bia_lo.kiem_san(ho, san))
    assert "lệch ADN bìa thắng" in bia_lo.ly_do_san_truot([ho], san)
    # chưa có ADN kênh / chưa đủ bằng chứng → không có sàn
    assert bia_lo.san_adn({}) == {} and bia_lo.san_adn({"adn_kenh": dict(k, nguong_hue=None, nguong_sang=None)}) == {}


def test_loi_theo_kieu_va_loi_nhac_anh_mang_adn():
    hs = {"kieu": "hop", "adn_cau": "STYLE DNA: deep purple; a DARK scene.", "adn": {"toi": True, "hue": [1] + [0] * 11,
                                                                                      "ten_mau": ["deep violet purple"]}}
    lk = bia_lo.loi_theo_kieu(hs)
    assert "STYLE DNA" in lk["luat_canh"] and "never dark or gloomy" not in lk["luat_canh"]
    assert "dark scene" in lk["phong_cach_ta"]
    assert "STYLE DNA" not in bia_lo.loi_theo_kieu({"kieu": "hop"})["luat_canh"]
    y = {"y": "a", "manh_moi": "b", "canh": "c", "mat": "d"}
    assert "STYLE DNA: deep purple" in bia_lo.loi_nhac_anh(y, {}, ho_so=dict(hs, kieu="tran", san_nv=True))


# ── vòng học ─────────────────────────────────────────────────────────────────


def test_dong_ket_qua_moi_ghi_adn():
    from core import bia_du_lieu as bd
    rows = [{"video_id": "V1", "tuoi": 60.0, "imp": 5000, "ctr": 5.0, "ngay": "2026-10-20"}]
    may = {"V1": {"luot": "0001", "chi_so": {}, "thumb": {}, "doi_bia": False}}
    kq = bd.dong_ket_qua_moi(rows, may, {}, {}, [], adn={"V1": {"kc_hue": 0.7, "sang_nen": 0.3}})
    assert kq and kq[0]["adn"]["kc_hue"] == 0.7
    assert "adn" not in bd.dong_ket_qua_moi(rows, may, {}, {}, [])[0]


def test_bia_ab_giu_adn_bien_the():
    from core import bia_ab
    bt = [{"nhan": "A", "so": 1}, {"nhan": "B", "so": 2, "ma": "y01-2", "ho": "tran", "adn": {"kc_hue": 0.2}}]
    m = bia_ab.meta_ung_vien(bt, {"nguon": "ho-so:bia-2", "tep": "x.jpg"})
    assert m["adn"] == {"kc_hue": 0.2} and m["ma"] == "y01-2" and "diem_lo" in m
    assert "adn" not in bia_ab.meta_ung_vien([{"nhan": "B", "so": 2}], {"nguon": "ho-so:bia-2"})


def test_tuong_quan_ctr_va_hieu_chuan(tmp_path):
    from core import hieu_chuan
    from core.doi_thu_kenh import thu_muc_nghien_cuu
    goc = str(tmp_path)
    video = {"V{0}".format(i): {"imp": 4000 + 100 * i, "ctr": 8.0 - 0.5 * i, "adn": {
        "kc_hue": 0.1 + 0.05 * i, "sang_nen": 0.2, "ti_toi": 0.5, "goc_chu": 0.0}} for i in range(12)}
    tm = thu_muc_nghien_cuu(goc, "K1")
    os.makedirs(tm, exist_ok=True)
    with open(os.path.join(tm, adn_bia.TEP_KENH), "w", encoding="utf-8") as f:
        json.dump({"kenh": "K1", "dich": {"hue": [1] + [0] * 11}, "video": video}, f)
    tq = adn_bia.tuong_quan_ctr(adn_bia.doc_adn_kenh(goc, "K1"), hieu_chuan.spearman)
    assert tq["n"] == 12 and tq["kc_hue"]["rho"] < -0.9 and tq["sang_nen"]["rho"] is None
    ts: dict = {}
    ra = hieu_chuan.them_adn(goc, ts, ["K1", "K_KHONG"])
    assert set(ra) == {"K1"} and ts["adn"]["K1"]["di_cung_ctr"]["kc_hue"] < -0.9
    assert "ADN bìa đi cùng CTR: K1 kc_hue" in hieu_chuan.tom_tat({"adn": ra})
    assert math.isclose(adn_bia.hellinger([1, 0], [1, 0]), 0.0) and adn_bia.hellinger([1, 0], [0, 1]) == 1.0
