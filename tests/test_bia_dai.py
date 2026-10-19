"""Chữ bìa ĐẬM như bìa thắng (19/10/2026, `core/bia_lo.py`): dải/khối nền sau dòng từ khoá đo trên bìa thắng, độ
đậm nét theo mật độ nét bìa thắng, bề khối chữ ~2/3 khung khi bìa thắng như vậy — mục tiêu từ SỐ ĐO, không cứng.

Ảnh TỔNG HỢP bằng PIL."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from core import bia_lo
from core import bia_theo_khuon as btk


def _can_font():
    if not btk._tim_font("", "悠々自適", "ja"):  # noqa: SLF001
        pytest.skip("máy không có phông chữ trần")


def _bia_thang_co_dai(duong: str) -> str:
    """Bìa thắng giả: nền kem, DẢI đỏ sẫm sau một dòng chữ trắng viền đen dày (y 0,30–0,50), dòng khác không dải."""
    im = Image.new("RGB", (1280, 720), (238, 226, 200))
    d = ImageDraw.Draw(im)
    d.polygon([(30, 216), (800, 210), (790, 360), (20, 365)], fill=(140, 18, 20))
    f = btk._tim_font("", "悠々自適", "ja")  # noqa: SLF001
    from PIL import ImageFont
    font = ImageFont.truetype(f, 120)
    d.text((40, 225), "悠々自適", font=font, fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
    d.text((40, 450), "暮らす人", font=font, fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
    im.save(duong)
    return duong


def test_do_dai_tren_bia_thang_va_muc_tieu(tmp_path):
    _can_font()
    im = Image.open(_bia_thang_co_dai(str(tmp_path / "w.jpg"))).convert("RGB")
    du = {"dong": [{"chu": "悠々自適", "x0": 0.02, "x1": 0.66, "y0": 0.29, "y1": 0.51, "mau": "white", "tu_khoa": True,
                    "nen": "red"},
                   {"chu": "暮らす人", "x0": 0.02, "x1": 0.66, "y0": 0.6, "y1": 0.82, "mau": "white", "nen": "none"}],
          "nhan_vat": {"x0": 0.7, "x1": 0.95, "y0": 0.1, "y1": 0.95}, "vien": "very_thick"}
    do = bia_lo.doc_do_bo_cuc(du, im)
    assert do["dai_tu_khoa"], "dải đỏ sẫm sau dòng từ khoá được xác nhận trên điểm ảnh"
    r, g, b = btk._mau_rgb(do["dai_tu_khoa"])  # noqa: SLF001
    assert r > 100 and g < 60 and b < 60
    assert do["dong"][1]["dai"] == "", "dòng không dải (AI nói none) → không dải"
    assert 0.1 < do["mat_do_chu"] < 0.9
    # AI nói có dải nhưng điểm ảnh không có (nền trơn) → không dải
    tron = Image.new("RGB", (1280, 720), (238, 226, 200))
    assert bia_lo.mau_dai_do(tron, [0.02, 0.6, 0.66, 0.82]) == ""
    # mục tiêu: dải chỉ khi bìa thắng mang ≥ nửa trọng số có dải
    co = dict(do, so_dong=2)
    khong = dict(do, so_dong=2, dai_tu_khoa="")
    assert bia_lo.tong_hop_bo_cuc([(co, 10), (khong, 3)])["dai_tu_khoa"] == do["dai_tu_khoa"]
    assert "dai_tu_khoa" not in bia_lo.tong_hop_bo_cuc([(co, 3), (khong, 10)])


def _hs(mt) -> dict:
    return {"kieu": "tran", "bo_cuc": "trai", "mau_nen": "#FFFFFF", "mau_do": "#F70403", "mau_vang": "#FBF90D",
            "uu_tien": bia_lo.UU_TIEN_VIEN_DEN, "muc_tieu": mt}


MT = {"so_dong": 3, "so_dong_min": 3, "so_dong_max": 4, "dt_dong_pct": 45.0, "cao_chinh_pct": 28.0, "ti_le_chinh": 1.4,
      "khe_max": 0.0, "ky_tu_dong": 5, "rong_khoi": 0.69, "vien": "very_thick", "tu_khoa_do": True, "ben_nv": "phai"}


def test_ve_dai_sau_dong_tu_khoa_va_bo_cuc_rong(tmp_path):
    _can_font()
    tang = bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", _hs(dict(MT, dai_tu_khoa="#8C1214")),
                                   cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"])
    co_dai = [t for t in tang if t.get("dai")]
    assert co_dai and all(t.get("to") or any(p["mau"] == "#F70403" for p in t["phan_mau"]) for t in co_dai)
    assert not [t for t in bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", _hs(MT),
                                                   cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"]) if t.get("dai")], \
        "bìa thắng không có dải → không vẽ dải (không cứng)"
    assert bia_lo.cach_bo_cuc_tran("trai", MT)[0][0] == 0.69, "cột chữ rộng ~2/3 khung như bìa thắng đo được"
    assert bia_lo.cach_bo_cuc_tran("trai", dict(MT, rong_khoi=0.95))[0][0] == 0.75
    # vẽ thật: điểm ảnh đỏ sẫm của dải nằm sau dòng từ khoá, không ở dòng khác
    nen = Image.new("RGB", (1280, 720), (236, 222, 196))
    ImageDraw.Draw(nen).ellipse([950, 120, 1150, 320], fill=(250, 250, 250), outline=(10, 10, 10), width=8)
    p = str(tmp_path / "y01-1-nen.png")
    nen.save(p)
    uv = {"ma": "y01-1", "nen": p}
    bia_lo.dung_bia(uv, tang, ho_so=_hs(dict(MT, dai_tu_khoa="#8C1214")))
    im = Image.open(uv["tep"]).convert("RGB")
    bc = __import__("core.do_bia", fromlist=["x"]).doc_bao_cao(uv["tep"])
    hop = {d["ten"]: d["hop"] for d in bc["dong"]}

    def sam(h) -> int:
        return sum(1 for x in range(int(h[0]), int(h[2]), 6) for y in range(int(h[1]), int(h[3]), 6)
                   if (lambda q: 110 < q[0] < 175 and q[1] < 45 and q[2] < 45)(im.getpixel((x, y))))
    k = next(t for t in co_dai if t.get("to"))
    khac = next(t for t in tang if not t.get("dai"))
    assert sam(hop[btk.chu_cua_tang(k)]) > 20 and sam(hop[btk.chu_cua_tang(khac)]) == 0


def test_do_dam_theo_mat_do_net_bia_thang():
    _can_font()
    hs = _hs(dict(MT))
    nhe = bia_lo._chon_dam(bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", _hs(MT),  # noqa: SLF001
                                                    cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"]),
                           dict(hs, muc_tieu=dict(MT, mat_do_chu=0.05)))
    nang = bia_lo._chon_dam(bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", _hs(MT),  # noqa: SLF001
                                                     cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"]),
                            dict(hs, muc_tieu=dict(MT, mat_do_chu=0.95)))
    assert nhe == bia_lo.DAM_THU[0] and nang == bia_lo.DAM_THU[-1], (nhe, nang)
    t = bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", _hs(dict(MT, mat_do_chu=0.95)),
                                cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"])
    assert {x.get("dam_pct") for x in t} == {bia_lo.DAM_THU[-1]}
    assert all("dam_pct" not in x for x in bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", _hs(MT),
                                                                    cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"]))


def test_chu_ngan_thi_chu_to_hon_va_khong_cat_giua_tu():
    """Kiểm vàng TL2 19/10: chữ bìa 12 ký tự vs bìa thắng ~25 → mục tiêu diện tích × √r, chữ to `he_co`; tách từ khoá
    đỏ không cắt giữa từ (「引き受けない」 không thành 「引」+「き受けない」)."""
    mt = bia_lo.muc_tieu_theo_chu(dict(MT, so_dong=5, ky_tu_dong=5, dt_dong_pct=41.6), "引き受けない自分で決める")
    assert mt["he_co"] == 1.4 and abs(mt["dt_dong_pct"] - 41.6 * (12 / 25) ** 0.5) < 0.2 and mt["dt_goc"] == 41.6
    dai = bia_lo.muc_tieu_theo_chu(dict(MT, so_dong=3, ky_tu_dong=4), "年金だけで悠々自適に暮らす人はこっそり")
    assert "he_co" not in dai, "chữ dài như bìa thắng: giữ mục tiêu"
    ra = bia_lo._tach_tu_khoa_do([{"phan_mau": [{"chu": "引き受けない", "vai": "do"}]}])  # noqa: SLF001
    assert [btk.chu_cua_tang(t) for t in ra] == ["引き受けない"]
    ra = bia_lo._tach_tu_khoa_do([{"phan_mau": [{"chu": "お金じゃない", "vai": "do"}]}])  # noqa: SLF001
    assert [btk.chu_cua_tang(t) for t in ra] == ["お金", "じゃない"]


def test_do_bo_cuc_bia_thang_hong_thi_do_lai(tmp_path):
    """Bìa thắng nặng ký nhất đo hỏng (AI trả toạ độ px → bỏ hết dòng) không được rơi khỏi mục tiêu: đo lại, khoá mới."""
    import json
    import os
    tm = tmp_path / "thang"
    tm.mkdir()
    Image.new("RGB", (1280, 720), (238, 226, 200)).save(str(tm / "1.jpg"))
    lan = []

    def goi(loi_nhac, **kw):
        lan.append(kw["khoa"])
        if len(lan) == 1:  # lần đầu: toạ độ px (không dùng được)
            return json.dumps({"dong": [{"chu": "あ", "x0": 10, "x1": 600, "y0": 20, "y1": 200, "mau": "white"}]})
        return json.dumps({"dong": [{"chu": "あいう", "x0": 0.02, "x1": 0.6, "y0": 0.1, "y1": 0.4, "mau": "white",
                                     "tu_khoa": True, "nen": "none"}],
                           "nhan_vat": {"x0": 0.7, "x1": 0.95, "y0": 0.1, "y1": 0.95}, "vien": "thick"})
    mt = bia_lo.bo_cuc_thang("G", "KH", str(tm), goi=goi, log=lambda s: None)
    assert len(lan) == 2 and lan[0] != lan[1] and mt.get("so_dong") == 1
    assert os.path.isfile(str(tm / bia_lo.TEP_BO_CUC_THANG))
