"""SÀN CHẤT LƯỢNG của bìa lô (19/10/2026, `core/bia_lo.py` + `core/auto_khau.py`).

Màu (bão hoà / tương phản / dải sáng ≥ phân vị 25 bìa thắng), nhân vật (giám khảo + bộ dò đầu), điểm "bấm như bìa
thắng" ≥ sàn hiệu chỉnh → lô mới (tối đa 2) → giữ + báo. Ảnh TỔNG HỢP bằng PIL, LLM + mô hình ảnh GIẢ."""

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


def _soc(duong: str, w: int = 1280, h: int = 720) -> str:
    """Ảnh RỰC: sọc đỏ / xanh / vàng / đen — bão hoà + tương phản cao (kiểu bìa thắng)."""
    im = Image.new("RGB", (w, h), (20, 20, 20))
    d = ImageDraw.Draw(im)
    for i, mau in enumerate([(230, 30, 30), (30, 90, 220), (250, 210, 20), (15, 15, 15)] * 4):
        d.rectangle([i * w // 16, 0, (i + 1) * w // 16, h], fill=mau)
    im.save(duong)
    return duong


def _nhat(duong: str) -> str:
    """Ảnh NHẠT đơn sắc hồng đào (kiểu TL4-0005)."""
    im = Image.new("RGB", (1280, 720), (236, 205, 185))
    ImageDraw.Draw(im).ellipse([800, 200, 1000, 400], fill=(226, 196, 176))
    im.save(duong)
    return duong


def test_san_mau_phan_vi_25_bia_thang_loai_bia_nhat(tmp_path):
    thang = [_soc(str(tmp_path / "w{0}.jpg".format(i))) for i in range(4)]
    san = bia_lo.san_mau(thang)
    assert set(san) == {"bao_hoa", "tuong_phan", "dai_sang", "toi_thieu"} and all(
        san[k] > 0.2 and san["toi_thieu"][k] <= san[k] for k in ("bao_hoa", "tuong_phan", "dai_sang")), san
    nhat = _nhat(str(tmp_path / "nhat.jpg"))
    ly = bia_lo.kiem_mau(nhat, san)
    assert len(ly) == 3 and any("bão hoà" in x for x in ly), "bìa nhạt đơn sắc thấp cả ba số đo"
    assert bia_lo.kiem_mau(thang[0], san) == [], "bìa rực như bìa thắng đạt"
    assert bia_lo.san_mau(thang[:1]) == {} and bia_lo.kiem_mau(nhat, {}) == [], "< 2 bìa thắng → không có sàn"
    # loc_san: NHẠT HẲN (cả 3 số đo dưới bìa thắng nhạt nhất) → loại TRƯỚC giám khảo (không tốn lượt chấm)
    u = {"ma": "y01-1", "tep": nhat, "loai": ""}
    bia_lo.loc_san(u, {"mau": san, "dau": False})
    assert u["loai"].startswith("màu nhạt hẳn") and u["mau_do"]["bao_hoa"] < san["bao_hoa"]


def test_san_mau_2_tren_3_phan_vi_10(tmp_path, monkeypatch):
    """Chủ 19/10: đạt khi ≥ 2/3 số đo ≥ phân vị 10 bìa thắng; 2/3 dưới → dưới sàn MỀM (vẫn chấm, không loại); chỉ
    cả 3 dưới bìa thắng nhạt nhất mới loại cứng."""
    assert bia_lo.SAN_PHAN_VI == 10.0
    san = {"bao_hoa": 0.40, "tuong_phan": 0.24, "dai_sang": 0.80,
           "toi_thieu": {"bao_hoa": 0.30, "tuong_phan": 0.20, "dai_sang": 0.70}}
    for do, so_ly, han in (({"bao_hoa": 0.35, "tuong_phan": 0.25, "dai_sang": 0.85}, 0, 0),   # 1/3 dưới → đạt
                           ({"bao_hoa": 0.35, "tuong_phan": 0.22, "dai_sang": 0.85}, 2, 0),   # 2/3 dưới → mềm
                           ({"bao_hoa": 0.25, "tuong_phan": 0.15, "dai_sang": 0.60}, 3, 3)):  # nhạt hẳn
        monkeypatch.setattr(bia_lo, "do_mau", lambda tep, _d=do: dict(_d))
        assert len(bia_lo.kiem_mau("x", san)) == so_ly and len(bia_lo.nhat_han("x", san)) == han, do
    p = _soc(str(tmp_path / "c.jpg"))
    monkeypatch.setattr(bia_lo, "do_mau", lambda tep: {"bao_hoa": 0.35, "tuong_phan": 0.22, "dai_sang": 0.85})
    u = {"ma": "y01-1", "tep": p, "loai": "", "diem": {"bam_nhu_thang": 9}}
    bia_lo.loc_san(u, {"mau": san, "dau": False})
    assert u["loai"] == "" and u["mau_duoi"].startswith("màu nhạt hơn bìa thắng")
    assert bia_lo.kiem_san(u, {"bam": 7})[0].startswith("màu nhạt"), "dưới sàn mềm: không vào top khi còn tấm đạt"


def _dau(duong: str, nen=(200, 60, 40), co_dau: bool = True) -> str:
    """Nền đỏ + (tuỳ) nhân vật đầu tròn TRẮNG viền ĐEN."""
    im = Image.new("RGB", (1280, 720), nen)
    if co_dau:
        d = ImageDraw.Draw(im)
        d.ellipse([800, 180, 1000, 380], fill=(250, 250, 250), outline=(10, 10, 10), width=10)
        d.ellipse([860, 260, 875, 275], fill=(10, 10, 10))
        d.ellipse([925, 260, 940, 275], fill=(10, 10, 10))
    im.save(duong)
    return duong


def test_san_nhan_vat_bo_do_dau_va_giam_khao(tmp_path):
    nv = _dau(str(tmp_path / "nv1.png"), nen=(255, 255, 255))
    thang = [_dau(str(tmp_path / "w{0}.jpg".format(i))) for i in range(3)]
    assert bia_lo.dau_dung_duoc(nv, thang), "bắt được đầu trên nv1.png + mọi bìa thắng → dùng làm sàn"
    nguoi = Image.new("RGB", (700, 400), (255, 255, 255))
    ImageDraw.Draw(nguoi).rectangle([300, 40, 400, 380], fill=(90, 60, 40))  # nhân vật người tóc nâu: không bắt
    nguoi.save(str(tmp_path / "nguoi.png"))
    assert not bia_lo.dau_dung_duoc(str(tmp_path / "nguoi.png"), thang), "không bắt được trên nv1 → chỉ giám khảo"
    assert not bia_lo.dau_dung_duoc(nv, thang[:1] + [_dau(str(tmp_path / "x.jpg"), co_dau=False)] * 3)
    u = {"ma": "y02-1", "tep": _dau(str(tmp_path / "c.jpg"), co_dau=False), "loai": "", "dau": []}
    bia_lo.loc_san(u, {"mau": {}, "dau": True})
    # kiểm vàng thật 19/10: bộ dò loại oan tấm đúng nhân vật → chỉ GHI, giám khảo (so với nv1.png) quyết
    assert u["loai"] == "" and u["dau_may"] is False
    # giám khảo: nhân vật khác / người phụ có mặt chi tiết → loại; không nói gì → không loại
    kq = bia_lo.doc_cham_1({"ung_vien": [
        {"so": 1, "bam_nhu_thang": 8, "noi_dung": 8, "to_mo": 8, "ro_120": 8, "cam_xuc": 8, "phong_cach": 8,
         "nv": "DIFFERENT", "nguoi_khac": "faces"},
        {"so": 2, "bam_nhu_thang": 8, "noi_dung": 8, "to_mo": 8, "ro_120": 8, "cam_xuc": 8, "phong_cach": 8,
         "nv": "same", "nguoi_khac": "faded"},
        {"so": 3, "noi_dung": 8, "to_mo": 8, "ro_120": 8, "cam_xuc": 8, "phong_cach": 8}]}, 3)
    assert kq[1]["nv"] == "different" and "không phải nhân vật kênh" in bia_lo.lech_nhan_vat(kq[1])
    assert "mặt chi tiết" in bia_lo.lech_nhan_vat(kq[1])
    assert bia_lo.lech_nhan_vat(kq[2]) == "" and bia_lo.lech_nhan_vat(kq[3]) == ""


def test_giam_khao_nhin_anh_nhan_vat_va_loai_nhan_vat_lech(tmp_path):
    mau = [_soc(str(tmp_path / "m1.jpg")), _soc(str(tmp_path / "m2.jpg"))]
    nv = _dau(str(tmp_path / "nv1.png"), nen=(255, 255, 255))
    ds = []
    for i in range(1, 4):
        p = _soc(str(tmp_path / "y0{0}-1.jpg".format(i)))
        ds.append({"ma": "y0{0}-1".format(i), "y": i, "bien": 1, "tep": p, "nen": p, "loai": ""})
    cap = []

    def goi(loi_nhac, **kw):
        cap.append((loi_nhac, kw))
        if "strict art director" in loi_nhac:
            return json.dumps({"ung_vien": [
                {"so": i, "bam_nhu_thang": 8, "noi_dung": 7, "to_mo": 7, "ro_120": 7, "cam_xuc": 7, "phong_cach": 7,
                 "nv": "different" if i == 2 else "same", "nguoi_khac": "faded"} for i in (1, 2, 3)]})
        return "{}"
    xh = bia_lo.cham(goi, ds, mau=mau, tieu_de="t", chu_bia="c", thu_muc=str(tmp_path), log=lambda s: None,
                     ho_so={"nv": nv})
    p, kw = next((p, kw) for p, kw in cap if "strict art director" in p)
    assert "Image 3 is the channel's CHARACTER REFERENCE" in p and len(kw["anh"]) == 2 + 1 + 3 + 1
    by = {u["ma"]: u for u in xh}
    assert by["y02-1"]["loai"].startswith("nhân vật lệch kênh") and not by["y01-1"].get("loai")


def test_bia_thang_giau_trong_moi_nhom_la_thuoc_san(tmp_path):
    """Bìa thắng GIẤU chen vào MỌI nhóm vòng 1 (giữa nhóm); sàn của tấm = điểm bìa giấu cùng nhóm − 1."""
    mau = [_soc(str(tmp_path / "m1.jpg")), _soc(str(tmp_path / "m2.jpg"))]
    giau = _soc(str(tmp_path / "giau.jpg"))
    ds = []
    for i in range(1, 9):
        p = _soc(str(tmp_path / "y0{0}-1.jpg".format(i)))
        ds.append({"ma": "y0{0}-1".format(i), "y": i, "bien": 1, "tep": p, "nen": p, "loai": ""})
    nhom = []

    def goi(loi_nhac, **kw):
        if "strict art director" in loi_nhac:
            n = int(loi_nhac.split("numbered 1 to ", 1)[1].split(" ", 1)[0])
            nhom.append(n)
            # vị trí 3 (giữa nhóm) là bìa giấu: 9 điểm; ứng viên 1 = 8, còn lại 7
            return json.dumps({"ung_vien": [{"so": i, "bam_nhu_thang": 9 if i == 3 else 8 if i == 1 else 7,
                                             "noi_dung": 7, "to_mo": 7, "ro_120": 7, "cam_xuc": 7, "phong_cach": 7}
                                            for i in range(1, n + 1)]})
        return "{}"
    xh = bia_lo.cham(goi, ds, mau=mau, tieu_de="t", chu_bia="c", thu_muc=str(tmp_path), log=lambda s: None,
                     giau=giau)
    assert sorted(nhom) == [3, 7], "nhóm 6 + bìa giấu, nhóm 2 + bìa giấu"
    assert all(u.get("bam_giau") == 9 for u in xh) and len(xh) == 8, "bìa giấu không thành ứng viên"
    dat = [u["ma"] for u in xh if not bia_lo.kiem_san(u, {"bam": 7})]
    assert len(dat) == 2 and all(bia_lo.san_cua(u, {})[0] == 8.0 for u in xh), "sàn = 9 − 1, tấm 7 điểm trượt"


def test_kiem_san_bam_va_hieu_chinh(tmp_path):
    tm = str(tmp_path / "thang")
    os.makedirs(tm)
    assert bia_lo.san_bam(tm) == (bia_lo.SAN_BAM_MAC_DINH, "mac-dinh")
    assert bia_lo.hieu_chinh_san_bam(tm, 9.0) == 8.0 and bia_lo.san_bam(tm) == (8.0, "hieu-chinh")
    assert bia_lo.hieu_chinh_san_bam(tm, 5.0) == 7.0, "trung vị (9, 5) − 1 = 6, kẹp ≥ 7"
    san = {"bam": 7.0}
    assert bia_lo.kiem_san({"diem": {"bam_nhu_thang": 7}}, san) == []
    assert "< sàn 7" in bia_lo.kiem_san({"diem": {"bam_nhu_thang": 6}}, san)[0]
    assert bia_lo.kiem_san({"diem": {"to_mo": 9}}, san), "không có điểm bấm-như-bìa-thắng → không qua sàn"


def _goc(tmp_path) -> str:
    goc = str(tmp_path / "goc")
    os.makedirs(duong_kenh(goc, "KH"), exist_ok=True)
    with io.open(os.path.join(duong_kenh(goc, "KH"), TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "KH"\n')
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
    os.makedirs(os.path.join(luot, "7-thumbnail"), exist_ok=True)
    with io.open(os.path.join(luot, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: 同じ車に長く乗る人の特徴\nTHUMB: 同じ車に長く乗る人のほとんどが\n")
    # thư mục bìa thắng THEO NẾP (kenh.yaml chưa khai bia_lo_mau)
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    os.makedirs(tm)
    for i in (1, 2):
        Image.new("RGB", (1280, 720), (240, 220, 200)).save(os.path.join(tm, "{0}.jpg".format(i)))
    return goc


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


def _goi(bam: float):
    def goi(loi_nhac, **kw):
        if "CONCEPT DIRECTOR" in loi_nhac:
            assert "never recast it as another person" in loi_nhac, "đạo diễn phải nhận luật nhân vật kênh"
            return json.dumps({"chu": [], "y_tuong": [
                {"y": "c{0}".format(i), "manh_moi": "clue {0}".format(i), "doi_lap": "faded crowd",
                 "canh": "the figure doing thing {0} on the right".format(i), "mat": "smile", "tu_the": "standing"}
                for i in (1, 2)]})
        if "strict art director" in loi_nhac:
            n = int(loi_nhac.split("numbered 1 to ", 1)[1].split(" ", 1)[0])
            return json.dumps({"ung_vien": [{"so": i + 1, "bam_nhu_thang": bam, "noi_dung": 7, "to_mo": 7,
                                             "ro_120": 7, "cam_xuc": 7, "phong_cach": 7, "nv": "same",
                                             "nguoi_khac": "none"} for i in range(n)]})
        if "Read the text printed" in loi_nhac:
            return json.dumps({"dong": [], "chu_thua": []})
        return "{}"
    return goi


def test_chay_duoi_san_bam_khong_co_top_va_ghi_ho_so(tmp_path):
    if not bia_lo.btk._tim_font("", "同じ車に長く", "ja", kieu="hop"):  # noqa: SLF001
        pytest.skip("máy không có phông bìa kiểu hộp")
    goc = _goc(tmp_path)
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
    kq = bia_lo.chay(goc, "KH", thu_muc_luot=luot, ra=str(tmp_path / "ra"), so_y=2, moi_y=2, goi=_goi(5),
                     ve=_ve, log=lambda s: None, dan="IMPORTANT — the previous batch was REJECTED")
    assert kq["thu_muc_mau"].endswith(os.path.join("bia-kh", "thang")), "thư mục bìa thắng theo nếp"
    assert kq["top"] == [] and "kém bìa thắng" in kq["san_truot"] and kq["san"]["bam"] == bia_lo.SAN_BAM_MAC_DINH
    assert kq["du_phong"] and all(not u.get("loai") for u in kq["du_phong"]), "tấm dự phòng: đã chấm, qua lọc cứng"
    assert all(u.get("duoi_san") for u in kq["ung_vien"] if not u.get("loai"))
    ok = bia_lo.chay(goc, "KH", thu_muc_luot=luot, ra=str(tmp_path / "ra2"), so_y=2, moi_y=2, goi=_goi(8),
                     ve=_ve, log=lambda s: None)
    assert ok["top"] and not ok["san_truot"]
    chon = bia_lo.xuat_goi(ok, os.path.join(luot, "7-thumbnail"))
    assert chon["san"]["bam"] == 8 and chon["san"]["san_bam"] == bia_lo.SAN_BAM_MAC_DINH and chon["san"]["nv"] == "same"


def test_duoi_san_lo_moi_toi_da_hai_roi_giu_va_bao(tmp_path, monkeypatch):
    from core import auto_khau as ak
    goc = _goc(tmp_path)
    tm = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001", "7-thumbnail")
    luot = SimpleNamespace(thu_muc=os.path.dirname(tm), ma_luot="0001", ma_kenh="KH")
    bc = SimpleNamespace(goc=goc, kenh=SimpleNamespace(ma="KH"), ghi=lambda s: None)
    lan = {"n": 0}

    def lo(_bc, _luot, _tt):
        lan["n"] += 1
        raise ak.DuoiSanBia("bìa lô dưới sàn chất lượng: kém bìa thắng — tấm tốt nhất bấm như bìa thắng 6 < sàn 7; "
                            "4 tấm màu nhạt hơn bìa thắng")
    bao = []
    monkeypatch.setattr(ak, "_mot_lo_bia", lo)
    monkeypatch.setattr(ak, "_soat_chu_bia_luot", lambda *a: {})
    monkeypatch.setattr(ak, "_bao_bia_khong_dat", lambda *a: bao.append(a))
    with pytest.raises(RuntimeError, match="KHÔNG bàn giao"):
        ak._khau_thumbnail(bc)(luot, None)  # noqa: SLF001
    assert lan["n"] == 1 + bia_lo.SO_LO_SAN_THEM and bao, "lô đầu + 2 lô mới, rồi giữ + báo"
    dan = ak._loi_nhac_vong(tm)  # noqa: SLF001
    assert "pale, washed-out" in dan and "weaker than the channel's winners" in dan, "lô sau được dặn vì sao"


def test_bia_lo_luot_duoi_san_nem_duoi_san_bia(tmp_path, monkeypatch):
    from core import auto_khau as ak
    goc = _goc(tmp_path)
    luot = SimpleNamespace(thu_muc=os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001"), ma_luot="0001", ma_kenh="KH")
    bc = SimpleNamespace(goc=goc, kenh=SimpleNamespace(ma="KH", ngon_ngu="ja"), ghi=lambda s: None)
    monkeypatch.setattr(ak, "_goi_soat", lambda bc: _goi(5))
    monkeypatch.setattr(ak, "_HopThemAnh", lambda *a: None)
    monkeypatch.setattr(ak, "_hop_bia", lambda *a: None)
    monkeypatch.setattr(ak, "ThamChieu", lambda bc: None)
    monkeypatch.setattr(bia_lo, "chay", lambda *a, **k: {"top": [], "ung_vien": [{"loai": "", "tong": 60}],
                                                          "san_truot": "kém bìa thắng", "chi_phi": {}})
    with pytest.raises(ak.DuoiSanBia):
        ak._bia_lo_luot(bc, luot)  # noqa: SLF001
    # Chủ 19/10: lô thứ 3 (đã làm 2 lô mới) vẫn dưới sàn → DÙNG tấm bấm-như-bìa-thắng cao nhất, không giữ
    du = {"ma": "y01-1", "tong": 60, "diem": {"bam_nhu_thang": 6}, "duoi_san": ["bấm 6 < sàn 7"]}
    monkeypatch.setattr(bia_lo, "chay", lambda *a, **k: {"top": [], "ung_vien": [dict(du, loai="")],
                                                          "san_truot": "kém bìa thắng", "du_phong": [du],
                                                          "chi_phi": {}})
    xuat = []
    monkeypatch.setattr(bia_lo, "xuat_goi", lambda kq, tm: xuat.append(kq) or {"ly_do": "ok"})
    tm = os.path.join(luot.thu_muc, "7-thumbnail")
    with io.open(os.path.join(tm, "vong-bia.json"), "w", encoding="utf-8") as tep:
        json.dump({"vong": 1}, tep)
    with pytest.raises(ak.DuoiSanBia):
        ak._bia_lo_luot(bc, luot)  # noqa: SLF001 — mới 1 lô làm lại: còn lượt
    with io.open(os.path.join(tm, "vong-bia.json"), "w", encoding="utf-8") as tep:
        json.dump({"vong": bia_lo.SO_LO_SAN_THEM}, tep)
    ra = ak._bia_lo_luot(bc, luot)  # noqa: SLF001
    assert ra and xuat and xuat[0]["top"] == [du] and xuat[0]["duoi_san"] is True
