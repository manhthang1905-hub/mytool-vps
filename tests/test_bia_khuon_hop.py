"""Khuôn bìa CỦA CHÍNH KÊNH đo từ bìa thật (13/10/2026, `core/bia_theo_khuon.py`).

Kênh có bìa thắng dạng HỘP chữ (chữ trắng trên hộp đỏ bo góc xếp chồng nửa trái, nhân vật cỡ vừa nửa phải, cảnh
gần-ảnh-chụp): luật bằng chứng đưa khuôn tới khai thác, vòng thử vẫn chặn trước khi khai thác, số đo của khuôn
thắng luật ngách chung, bộ vẽ vẽ ĐÚNG hộp + vẫn đo độ đọc được. Tấm chữ trần / chuẩn ngách giữ nguyên.

Ảnh TỔNG HỢP bằng PIL, không gọi mạng, không dữ liệu kênh thật."""

from __future__ import annotations

import io
import os
import random

import pytest
from PIL import Image, ImageDraw

from core import bia_theo_khuon as btk
from core import chon_bia
from core import do_bia
from core import khuon_bia as kb
from core.kenh import TEP_KENH, duong_kenh

DO = "#C8402F"
KC_HOP = {
    "nen_mau_chu_dao": "warm amber #8A5A3A", "nen_kieu": "near_photo",
    "nhan_vat": {"vi_tri": "phai", "co_pct": 40, "tu_the": "standing", "net_mat": "knowing smile"},
    "chu": {"so_tang": 3, "tang": [
        {"vi_tri": "tren", "noi_dung": "AAAA", "mau": ["#FFFFFF"], "khoi_nen": True, "mau_khoi": DO, "canh": "trai"},
        {"vi_tri": "giua", "noi_dung": "BBBB", "mau": ["#FFFFFF"], "khoi_nen": True, "mau_khoi": DO, "canh": "trai"},
        {"vi_tri": "duoi", "noi_dung": "CCCC", "mau": [DO], "khoi_nen": True, "mau_khoi": "#FFFFFF",
         "canh": "trai"}]}}
KC_TRAN = {"nhan_vat": {"vi_tri": "giua", "co_pct": 55},
           "chu": {"tang": [{"vi_tri": "tren", "mau": ["#FFFFFF"], "khoi_nen": False},
                            {"vi_tri": "duoi", "mau": ["#FF0000", "#FFFF00"], "khoi_nen": False}]}}


def _kenh(goc: str, ma: str = "KH", them: str = "") -> None:
    os.makedirs(duong_kenh(goc, ma), exist_ok=True)
    with io.open(os.path.join(duong_kenh(goc, ma), TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "{0}"\n{1}'.format(ma, them))


def _khuon(ctr: float, imp: float, tv, thu: str = "dat") -> dict:
    return {"video_id": "vidKHUON001", "nguon": "kenh", "anh_that": True, "ctr": ctr, "imp": imp,
            "trung_vi_ctr_that": tv, "khuon_chu": KC_HOP, "tep": "",
            "thu": {"trang_thai": thu, "so_lan": 0 if thu == "cho_thu" else 1}}


def _nen_am_ron() -> Image.Image:
    rnd = random.Random(3)
    im = Image.new("RGB", (1280, 720), (150, 95, 60))
    d = ImageDraw.Draw(im)
    for _ in range(500):
        x, y = rnd.randrange(1280), rnd.randrange(720)
        d.rectangle([x, y, x + rnd.randrange(10, 80), y + rnd.randrange(4, 30)],
                    fill=rnd.choice([(120, 70, 40), (200, 140, 90), (90, 55, 30), (230, 180, 120)]))
    return im


def _can_font():
    if not btk._tim_font("", "一人でコレ", "ja"):  # noqa: SLF001
        pytest.skip("máy không có font Nhật")


# ── luật bằng chứng → khai thác ──────────────────────────────────────────────


def test_luat_bang_chung_mot_cau():
    ch = dict(ctr_min=7.0, imp_min=10000, imp_lon=50000)
    assert btk.du_bang_chung(7.71, 31666, trung_vi=4.9, **ch)          # vế 1
    assert btk.du_bang_chung(5.9, 106000, trung_vi=4.9, **ch)          # vế 2: hiển thị lớn, trên trung vị
    assert not btk.du_bang_chung(9.0, 3000, trung_vi=4.9, **ch)        # CTR cao nhưng ít hiển thị
    assert not btk.du_bang_chung(4.0, 300000, trung_vi=4.9, **ch)      # hiển thị lớn, dưới trung vị
    assert not btk.du_bang_chung(5.9, 106000, trung_vi=None, **ch)     # chưa đo trung vị: chỉ vế 1


def test_khai_thac_khuon_hien_thi_lon_ctr_tren_trung_vi(tmp_path):
    goc = str(tmp_path)
    _kenh(goc)
    tt = btk.trang_thai_khai_thac(goc, "KH", _khuon(5.9, 106000, 4.9))
    assert tt["che_do"] == "khai_thac", tt["ly_do"]
    assert btk.trang_thai_khai_thac(goc, "KH", _khuon(5.9, 106000, 6.2))["che_do"] == "tham_do"
    assert btk.trang_thai_khai_thac(goc, "KH", _khuon(7.71, 31666, 4.9))["che_do"] == "khai_thac"
    assert btk.trang_thai_khai_thac(goc, "KH", _khuon(9.0, 3000, 4.9))["che_do"] == "tham_do"


def test_vong_thu_van_chan_truoc_khi_khai_thac(tmp_path):
    goc = str(tmp_path)
    _kenh(goc)
    kieu_goc = [("portrait_main", "x"), ("dramatic_scene", "y"), ("youtube_ctr", "z")]
    kb._ghi_khuon(goc, "KH", _khuon(5.9, 106000, 4.9, thu="cho_thu"))  # noqa: SLF001
    kh = btk.ke_hoach_bia(goc, "KH", ma_goi="KH-0001", so_thumbnail=5, kieu_goc=kieu_goc)
    assert kh["che_do"] == "can_thu", "khuôn mới phải qua vòng tạo thử, không được khai thác thẳng"
    kb.ghi_ket_qua_thu(goc, "KH", dat=True, chi_tiet={})
    kh = btk.ke_hoach_bia(goc, "KH", ma_goi="KH-0001", so_thumbnail=5, kieu_goc=kieu_goc)
    assert kh["che_do"] == "khai_thac" and any(m["nhom"] == "khuon" for m in kh["muc"])


# ── số đo của khuôn thắng luật ngách chung ───────────────────────────────────


def test_khuon_do_co_nhan_vat_thay_luat_30_phan_tram():
    p = btk.loi_nhac_theo_khuon(KC_HOP, phong_cach="flat", bien_the={})
    assert "about 40% of frame height" in p and btk.NHAN_VAT_LON not in p
    q = btk.loi_nhac_theo_khuon({"nhan_vat": {"vi_tri": "phai"}}, phong_cach="flat", bien_the={})
    assert btk.NHAN_VAT_LON in q, "khuôn không đo cỡ nhân vật thì giữ luật ≥30%"


def test_nen_gan_anh_that_cam_nguoi_that_nhung_giu_canh():
    cam = "no real humans, no photorealism, no 3D, no watermark"
    p = btk.loi_nhac_theo_khuon(KC_HOP, phong_cach="flat", bien_the={}, cam=cam)
    assert btk.CAM_NGUOI_THAT in p and btk.CAM_ANH_THAT not in p
    assert "near-photographic" in p and "no photorealism" not in p and "no real humans" in p
    q = btk.loi_nhac_theo_khuon(KC_TRAN, phong_cach="flat", bien_the={}, cam=cam)
    assert btk.CAM_ANH_THAT in q and "no photorealism" in q


def test_loi_nhac_chu_hop_va_vung_trong_ben_trai():
    tang = btk.tach_chu_mac_dinh("一人でコレやってる人は 上位1%の天才", KC_HOP)
    p = btk.loi_nhac_theo_khuon(KC_HOP, phong_cach="flat", bien_the={}, chu_tang=tang, chu_do_ma_ve=True)
    assert "the LEFT 62% of the frame" in p
    m = btk.loi_nhac_theo_khuon(KC_HOP, phong_cach="flat", bien_the={}, chu_tang=tang, chu_do_ma_ve=False)
    assert "rounded box" in m and "huge bare lettering" not in m


def test_chuan_hoa_giu_mau_hop_canh_va_kieu_nen():
    kc = btk.chuan_hoa_khuon_chu({"nen_kieu": "near_photo", "chu": {"tang": [
        {"vi_tri": "tren", "noi_dung": "x", "khoi_nen": True, "mau_khoi": "#c8402f box", "canh": "TRAI"}]}})
    t = kc["chu"]["tang"][0]
    assert kc["nen_kieu"] == "near_photo" and t["mau_khoi"] == "#C8402F" and t["canh"] == "trai"


def test_gan_kieu_khuon_dau_cuoi():
    hai = btk.gan_kieu_khuon([{"vi_tri": "tren"}, {"vi_tri": "duoi"}], KC_HOP)
    assert [t["mau_khoi"] for t in hai] == [DO, "#FFFFFF"], "tầng đầu ↔ đầu, tầng cuối ↔ cuối"
    assert all(t["khoi_nen"] and t["canh"] == "trai" for t in hai)
    tran = btk.gan_kieu_khuon([{"vi_tri": "tren"}, {"vi_tri": "duoi"}], KC_TRAN)
    assert all("khoi_nen" not in t and "mau_khoi" not in t for t in tran)


def test_giam_khao_thu_khuon_khong_viet_cung_nhan_vat_va_chu_tran():
    assert "orange" not in btk.LOI_NHAC_CHAM_THEO_KHUON
    assert "solid boxes" in btk.LOI_NHAC_CHAM_THEO_KHUON
    assert "NOT dai_toi" in chon_bia._LOI_NHAC_GIAM_KHAO  # noqa: SLF001


# ── bộ vẽ: hộp của khuôn ─────────────────────────────────────────────────────


def test_ve_hop_khuon_ra_hop_dung_mau_va_bao_cao_doc_duoc(tmp_path):
    _can_font()
    nen = tmp_path / "nen.png"
    _nen_am_ron().save(nen)
    dich = str(tmp_path / "thumb_007.png")
    tang = btk.tach_chu_mac_dinh("一人でコレやってる人は 上位1%の天才", KC_HOP)
    bc: dict = {}
    assert btk.ve_chu_len_anh(str(nen), dich, btk.bo_tri_chu("khuon", tang, KC_HOP), bao_cao=bc)
    assert bc["dat"] is True, do_bia.tom_tat(bc)
    assert {d["kieu"] for d in bc["dong"]} == {"hop_khuon"}
    assert all(d["co_khung"] for d in bc["dong"])
    bo = bc["bo_cuc"]
    assert bo["so_khung"] == len(bc["dong"]) and not bo["chong_khung"], "mỗi dòng một hộp, không chồng"
    assert bo["dt_khung"] == 0.0, "hộp của khuôn là thiết kế, không tính là khung bộ vẽ thêm"
    assert os.path.isfile(do_bia.duong_bao_cao(dich)) and do_bia.cham_tep(dich).get("dat") is True
    hop = sorted((d["hop"] for d in bc["dong"]), key=lambda h: h[1])
    assert hop[0][1] < 720 * 0.1, "cột hộp chữ bắt đầu từ góc trên"
    assert all(b[1] >= a[3] for a, b in zip(hop, hop[1:])), "các hộp xếp liền một cột, không đè nhau"
    assert all(d["cao_pct"] >= 9.0 for d in bc["dong"]), "mỗi dòng có hộp đủ lớn trên điện thoại"
    im = Image.open(dich).convert("RGB")
    for d in bc["dong"]:
        x0, y0, x1, y1 = d["hop"]
        assert x1 <= 1280 * btk.COT_CHU_KHOI + 10, "cột hộp chữ ở nửa trái"
        mau = im.getpixel((int(x0) + 4, int((y0 + y1) / 2)))   # mép trái trong hộp (lề, không có chữ)
        assert mau in ((200, 64, 47), (255, 255, 255)), mau


def test_hop_khuon_chu_trung_mau_hop_duoc_doi_cho_doc_duoc(tmp_path):
    _can_font()
    nen = tmp_path / "nen.png"
    _nen_am_ron().save(nen)
    tang = btk.gan_kieu_khuon([{"vi_tri": "tren", "phan_mau": [{"chu": "一人でコレ", "mau": DO}]},
                               {"vi_tri": "duoi", "phan_mau": [{"chu": "上位1%の天才", "mau": "#FFFFFF"}]}],
                              {"chu": {"tang": [dict(KC_HOP["chu"]["tang"][0]), dict(KC_HOP["chu"]["tang"][0])]}})
    bc: dict = {}
    btk.ve_chu_len_anh(str(nen), str(tmp_path / "t.png"), btk.bo_tri_chu("khuon", tang), bao_cao=bc)
    assert bc["dat"] is True and bc["dong"][0]["mau_chu"][0] != DO, do_bia.tom_tat(bc)


def test_tam_chu_tran_giu_duong_cu(tmp_path):
    _can_font()
    tang = btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", KC_TRAN)
    assert all(not t.get("khoi_nen") for t in tang)
    bt = btk.bo_tri_chu("khuon", tang, KC_TRAN)
    assert all(t["vung"] == (0.0, 1.0) and t["can"] == "giua" for t in bt)
    nen = tmp_path / "nen.png"
    _nen_am_ron().save(nen)
    bc: dict = {}
    btk.ve_chu_len_anh(str(nen), str(tmp_path / "t.png"), bt, bao_cao=bc)
    assert "hop_khuon" not in {d["kieu"] for d in bc["dong"]}
    cn = btk.khuon_tu_chuan_ngach({"chu": {}})
    assert btk.gan_kieu_khuon(btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", cn), cn) == \
        btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", cn)
