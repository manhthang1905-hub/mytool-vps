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


def test_gan_kieu_khuon_hop_dong_to_nhan_hop_dinh():
    """Khuôn hộp (13/10 tối): dòng CỰC TO nhận kiểu tầng "đinh" của khuôn (hộp TRẮNG chữ ĐỎ giữa các hộp đỏ), các dòng
    khác nhận kiểu chung; đỏ khuôn đọc lệch (#C8402F) chuẩn về đỏ sẫm bìa thắng #BE392B, chữ trắng / chữ đỏ sẫm."""
    hai = btk.gan_kieu_khuon([{"vi_tri": "tren", "phan_mau": [{"chu": "一人でコレを"}]},
                              {"vi_tri": "duoi", "to": True, "phan_mau": [{"chu": "天才"}]}], KC_HOP)
    assert [t["mau_khoi"] for t in hai] == ["#BE392B", "#FFFFFF"]
    assert hai[0]["phan_mau"][0]["mau"] == "#FFFFFF" and hai[1]["phan_mau"][0]["mau"] == "#BE392B"
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
    assert bc["cach"] == "hop" and bc["font"] == btk.FONT_HOP, "đo theo bố cục hộp, phông bo tròn của kho"
    hop = [d["hop"] for d in bc["dong"]]
    assert all(b[1] < a[3] and b[1] > a[1] for a, b in zip(hop, hop[1:])), "hộp sau đè NHẸ lên đáy hộp trước"
    assert all(b[0] > a[0] for a, b in zip(hop, hop[1:])), "so le: mỗi dòng lùi vào một chút"
    assert sum(1 for d in bc["dong"] if d["to"]) == 1 and max(bc["dong"], key=lambda d: d["cao_pct"])["to"]
    assert max(d["cao_pct"] for d in bc["dong"]) >= 18.0, "đúng một dòng CỰC TO"
    assert all(d["cao_pct"] >= 7.0 for d in bc["dong"]), "dòng vừa vẫn đọc được trên điện thoại"
    im = Image.open(dich).convert("RGB")
    for d in bc["dong"]:
        x0, y0, x1, y1 = d["hop"]
        assert x1 <= 1280 * 0.72 and y0 >= 0 and y1 <= 720, "cột hộp chữ ở nửa trái, trong khung"
        mau = im.getpixel((int(x0) + 8, int((y0 + y1) / 2)))   # mép trái trong hộp (lề, không có chữ)
        assert mau in (btk.HOP_DO_SAU, (255, 255, 255)), mau
        vien = im.getpixel((int(x0) + 1, int((y0 + y1) / 2)))  # viền nâu sẫm mảnh tách hộp khỏi nền
        assert sum(vien) < 200, vien


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
    assert bc["cach"] == "chinh_xac" and "hop_chu" not in bc, "chữ trần: cổng đo như cũ"
    assert not btk._tim_font("", "人生後半", "ja").endswith(btk.FONT_HOP), "chữ trần giữ phông cũ"  # noqa: SLF001
    cn = btk.khuon_tu_chuan_ngach({"chu": {}})
    assert btk.gan_kieu_khuon(btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", cn), cn) == \
        btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", cn)
    assert not btk.kieu_hop(KC_TRAN) and not btk.kieu_hop(cn) and btk.kieu_hop(KC_HOP)


# ── 13/10/2026 tối: bìa kiểu hộp đạt chuẩn bìa thắng (thứ bậc, phông, hộp, nền, ẩn dụ) + cổng đo hộp ─────────────


def _chu(tang) -> list:
    return [("*" if t.get("to") else "") + "".join(("^" if p.get("nho") else "") + p["chu"] for p in t["phan_mau"])
            for t in tang]


def test_thu_bac_mot_dong_cuc_to_dung_cach_chia_bia_duyet():
    """Đường lùi máy chia đúng như bìa chủ duyệt 13/10; luôn ĐÚNG MỘT dòng cực to ≤ 5 ký tự, không phải dòng đầu."""
    assert _chu(btk.tach_chu_mac_dinh("同じ車に長く乗る人のほとんどが", KC_HOP)) == ["同じ車に長く", "*乗る人の", "ほとんどが"]
    assert _chu(btk.tach_chu_mac_dinh("一人で『コレ』をする人は上位1%の天才かも", KC_HOP)) == \
        ["一人で『コレ』を", "する人は上位1%の", "*天才^かも"]
    for chu in ("富裕層が掃除に執着する本当の理由", "実は独り言が多い人は", "高級ブランドに興味がない人々の本当の正体",
                "低IQの人の思考の癖"):
        tang = btk.tach_chu_mac_dinh(chu, KC_HOP)
        to = [t for t in tang if t.get("to")]
        assert 1 <= len(tang) <= 4 and len(to) == 1 and not tang[0].get("to"), _chu(tang)
        assert len(btk._chuan("".join(p["chu"] for p in to[0]["phan_mau"] if not p.get("nho")))) <= 5  # noqa: SLF001
        assert btk._chuan("".join(btk.chu_cua_tang(t) for t in tang)) == btk._chuan(chu), "giữ trọn chữ"  # noqa: SLF001


def _goi_gia(*tra_loi):
    ds = list(tra_loi)

    def goi(loi_nhac, **_kw):
        goi.lan.append(loi_nhac)
        return ds.pop(0) if ds else "{}"
    goi.lan = []
    return goi


_CANH = [{"canh": "the figure polishing an old car while a crowd admires a new one", "net_mat": "proud smile"}]


def test_viet_bien_the_hop_ai_chen_dau_va_may_giu_luat():
    """AI chỉ CHÈN dấu | [ ] ( ); bỏ chữ / tự chế dấu → lượt sửa → vẫn sai thì chia máy; dòng to do AI chọn được ưu
    tiên khi hợp luật hình, dòng to quá dài thì máy chia nhỏ (「上位1%の天才かも」 → 上位1%の / 天才(かも))."""
    import json as _json
    hook = "一人で『コレ』をする人は上位1%の天才かも"
    g = _goi_gia(_json.dumps({"chu": ["一人で|『コレ』を|する人は上位1%の|[天才(かも)]"], "bien_the": _CANH}))
    bt = btk.viet_bien_the(g, KC_HOP, tieu_de="t", chu_bia=hook, n=2, co_dinh_chu=True)
    assert not bt.get("chu_tang_lui") and _chu(bt["chu_tang"])[-1] == "*天才^かも"
    assert bt["bien_the"][0]["canh"].startswith("the figure") and len(bt["bien_the"]) == 2
    assert "LEFT" in g.lan[0] and "{" not in g.lan[0].split("Return JSON")[0], "lời nhắc đã điền đủ"
    g = _goi_gia(_json.dumps({"chu": ["一人で|『コレ』をする人は|[上位1%の天才(かも)]"], "bien_the": _CANH}))
    bt = btk.viet_bien_the(g, KC_HOP, tieu_de="t", chu_bia=hook, n=1, co_dinh_chu=True)
    assert _chu(bt["chu_tang"])[-1] == "*天才^かも" and "".join(btk.chu_cua_tang(t) for t in bt["chu_tang"]) == hook
    con = btk.chon_tang_hop([[{"phan_mau": [{"chu": "一人で『コレ』を"}]},
                              {"to": True, "phan_mau": [{"chu": "する人は上位1%の天才かも"}]}]])
    assert _chu(con) == ["一人で『コレ』を", "する人は上位1%の", "*天才^かも"], "dòng to quá dài → chia nhỏ"
    # AI bỏ chữ (luật "các đoạn theo thứ tự" cũ cho qua) rồi tự chế dấu `{ }` → hai lượt đều loại → chia máy
    g = _goi_gia(_json.dumps({"chu": "一人で|[コレ]|天才(かも)", "bien_the": _CANH}),
                 _json.dumps({"chu": "一人で{『コレ』を|する人は}上位1%の|[天才(かも)]"}))
    bt = btk.viet_bien_the(g, KC_HOP, tieu_de="t", chu_bia=hook, n=1, co_dinh_chu=True)
    assert len(g.lan) == 2 and "does NOT contain the hook exactly" in g.lan[1]
    assert bt.get("chu_tang_lui") and _chu(bt["chu_tang"]) == ["一人で『コレ』を", "する人は上位1%の", "*天才^かも"]
    assert bt["bien_the"][0]["canh"] == _CANH[0]["canh"], "cảnh của lượt đầu được giữ"


def test_xep_hop_so_le_de_nhe_vua_khung_va_ne_nhan_vat():
    def do_rong(chu, co):
        return len(chu) * co
    dong = [{"chu": "一人でコレを"}, {"chu": "する人は上位1の"}, {"chu": "天才", "duoi": "かも", "to": True}]
    W, H = 1280, 720
    g = btk.xep_hop_chu(dong, W, H, do_rong)
    hop = [x["hop"] for x in g]
    assert g[2]["co"] > 1.5 * max(g[0]["co"], g[1]["co"]), "đúng một dòng cực to"
    assert abs((hop[1][0] - hop[0][0]) - W * btk.HOP_SO_LE) < 1 and hop[2][0] > hop[1][0], "so le"
    assert all(abs(b[1] - (a[3] - btk.HOP_DE * c["co"])) < 1 for a, b, c in zip(hop, hop[1:], g)), "đè nhẹ"
    assert all(0 <= h[0] and h[2] <= W and 0 <= h[1] and h[3] <= H for h in hop), "trong khung"
    assert all(abs((h[2] - h[0]) - (do_rong(d["chu"], x["co"]) + (do_rong(d.get("duoi", ""), x["co_duoi"])
                                                                   + 0.06 * x["co"] if d.get("duoi") else 0)
                                     + 2 * btk.HOP_LE_NGANG * x["co"])) < 1 for h, d, x in zip(hop, dong, g)), "ôm sát"
    nv = (0.58 * W, 0.15 * H, W, H)  # nhân vật bên phải
    g2 = btk.xep_hop_chu(dong, W, H, do_rong, tranh=[nv])
    assert all(x["hop"][2] <= nv[0] for x in g2 if x["hop"][3] > nv[1]), "hộp chữ không lấn vào nhân vật"
    assert g2[2]["co"] >= 0.75 * g[2]["co"], "chữ vẫn là nhân vật chính"
    g3 = btk.xep_hop_chu(dong, W, H, do_rong, canh="phai", tranh=[(0, 0, 0.42 * W, H)])
    assert all(x["hop"][0] >= 0.42 * W and x["hop"][2] <= W for x in g3), "cột phải: soi gương"


def test_phong_bo_tron_cua_kho_cho_kieu_hop():
    d = btk._tim_font("", "天才かも", "ja", kieu="hop")  # noqa: SLF001
    assert d.endswith(btk.FONT_HOP) and os.path.dirname(d) == btk._THU_MUC_FONT_KHO  # noqa: SLF001
    assert os.path.isfile(os.path.join(btk._THU_MUC_FONT_KHO, "OFL.txt")), "giấy phép OFL đi kèm"  # noqa: SLF001
    assert not btk._tim_font("", "天才かも", "ja").endswith(btk.FONT_HOP), "chữ trần: phông cũ"  # noqa: SLF001
    assert not btk._tim_font("", "된장찌개", "ko", kieu="hop").endswith(btk.FONT_HOP), "Hangul: phông Hàn"  # noqa: SLF001
    assert not btk._font_du_chu(d, "天才\U0001F600") and btk._font_du_chu(d, "上位1%の天才かも")  # noqa: SLF001
    assert btk.bo_font_cho("一人の時間", "ja")[0] == "NotoSansJP-Black.otf"


def _nen_be() -> Image.Image:
    im = Image.new("RGB", (1280, 720), (238, 214, 190))
    ImageDraw.Draw(im).ellipse([860, 180, 1160, 480], fill=(250, 250, 250), outline=(10, 10, 10), width=10)
    return im


def test_cong_hop_do_chu_tren_hop_dat_va_truot_dung(tmp_path):
    """Cổng đo bìa kiểu hộp trên CHÍNH tệp giao: trắng trên đỏ sẫm ĐẠT (bộ dò mù cũ trượt oan: coi hộp đỏ là "màu chữ");
    chữ trắng trên hộp hồng nhạt TRƯỢT (chữ↔hộp); hộp cùng màu nền, không viền → TRƯỢT (hộp lẫn vào nền)."""
    _can_font()
    nen = tmp_path / "nen.png"
    _nen_be().save(nen)
    tang = btk.tach_chu_mac_dinh("同じ車に長く乗る人のほとんどが", KC_HOP)
    dich = str(tmp_path / "thumb_007.png")
    bc: dict = {}
    btk.ve_chu_len_anh(str(nen), dich, btk.bo_tri_chu("khuon", tang, KC_HOP), bao_cao=bc)
    assert bc["dat"] is True and bc["hop_chu"], do_bia.tom_tat(bc)
    jpg = str(tmp_path / "CHON-thumb_007.jpg")
    chon_bia._xuat_jpg(dich, jpg)  # noqa: SLF001
    b = do_bia.cham_tep(jpg)
    assert b["dat"] is True and b["cach"] == "hop" and b["bo_cuc"]["chong_khung"] is False, do_bia.tom_tat(b)
    assert max(d["cao_pct"] for d in b["dong"]) >= 18.0 and not do_bia.ly_do_bo_cuc(b)
    assert not do_bia.dai_toi_moi(jpg, str(nen)).get("co"), "bóng hộp không phải dải tối mờ"
    # chữ trắng trên hộp hồng nhạt
    im = _nen_be()
    ve = ImageDraw.Draw(im)
    from PIL import ImageFont
    f = ImageFont.truetype(btk._tim_font("", "天才", "ja", kieu="hop"), 200)  # noqa: SLF001
    ve.rounded_rectangle([60, 260, 560, 500], radius=30, fill=(244, 184, 176))
    ve.text((100, 270), "天才", font=f, fill=(255, 255, 255))
    hop = [{"hop": [60, 260, 560, 500], "chu": "天才", "cao_px": 170, "mau_chu": "#FFFFFF", "mau_hop": "#F4B8B0",
            "vien_px": 0, "to": True}]
    kq = do_bia.cham_hop(im, hop)
    assert kq["dat"] is False and "chữ↔hộp" in " ".join(kq["ly_do"]), kq["ly_do"]
    # hộp cùng màu nền be, không viền
    im2 = _nen_be()
    ve2 = ImageDraw.Draw(im2)
    ve2.rounded_rectangle([60, 260, 560, 500], radius=30, fill=(232, 210, 186))
    ve2.text((100, 270), "天才", font=f, fill=(40, 20, 10))
    kq2 = do_bia.cham_hop(im2, [dict(hop[0], mau_chu="#28140A", mau_hop="#E8D2BA")])
    assert kq2["dat"] is False and "hộp lẫn vào nền" in " ".join(kq2["ly_do"]), kq2["ly_do"]


def test_loi_nhac_nen_hop_phang_sang_an_du_khong_chu():
    p = btk.loi_nhac_hop_chu(KC_HOP, bien_the={"canh": "the figure reading alone while a party goes on behind.",
                                               "net_mat": "peaceful smile", "tu_the": "sitting"})
    assert "FLAT VECTOR" in p and "NOT dark" in p and "reading alone while a party goes on behind" in p
    assert "peaceful smile" in p and "price tags" in p and "silhouettes" in p
    assert "%" not in p.replace("percentages", ""), "không con số % (mô hình vẽ 'LEFT 55%' thành chữ)"
    assert "character" in p and "right side" in p and "left half" in p
    q = btk.loi_nhac_hop_chu(KC_HOP, bien_the={}, nen="soft pastel blue flat vector")
    assert "soft pastel blue flat vector" in q and "the figure reacting" in q


def test_ke_hoach_khuon_hop_chu_luon_do_ma_ve(tmp_path):
    goc = str(tmp_path)
    _kenh(goc)
    kb._ghi_khuon(goc, "KH", _khuon(5.9, 106000, 4.9))  # noqa: SLF001
    kh = btk.ke_hoach_bia(goc, "KH", ma_goi="KH-0002", so_thumbnail=5,
                          kieu_goc=[("portrait_main", "x"), ("dramatic_scene", "y")])
    assert kh["che_do"] == "khai_thac"
    assert all(m["ve_chu"] == "ma" for m in kh["muc"] if m["nhom"] == "khuon")
    assert btk.cau_hinh_kenh(goc, "KH")["bia_hop_nen"] == ""


def test_chon_anh_mau_phong_cach_uu_tien_sang_sach(tmp_path):
    rnd = random.Random(5)
    sang = tmp_path / "sang.jpg"
    Image.new("RGB", (640, 360), (240, 222, 200)).save(sang)
    toi = tmp_path / "toi.jpg"
    im = Image.new("RGB", (640, 360), (40, 30, 30))
    d = ImageDraw.Draw(im)
    for _ in range(400):
        x, y = rnd.randrange(640), rnd.randrange(360)
        d.rectangle([x, y, x + 6, y + 6], fill=(rnd.randrange(255), 90, 60))
    im.save(toi)
    hong = tmp_path / "hong.jpg"
    hong.write_bytes(b"\xff\xd8\xff\xe0FAKE")
    ra = btk.chon_anh_mau_phong_cach([str(toi), str(hong), str(sang)])
    assert ra[0] == str(sang) and str(hong) not in ra and len(ra) == 2


def test_hop_them_anh_tai_nhieu_mau(tmp_path):
    from types import SimpleNamespace
    from core import auto_khau as ak
    a, b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    a.write_bytes(b"x")
    b.write_bytes(b"y")
    tai = []
    client = SimpleNamespace(uploads=SimpleNamespace(upload_file=lambda d: tai.append(d) or "https://u/" + d[-5:]))
    bc = SimpleNamespace(on_log=None, ngu=lambda s: None, kiem_dung=None, client=client)
    goc = SimpleNamespace(lay=lambda: ["https://nv"], lam_moi=lambda cu: ["https://nv2"])
    hop = ak._HopThemAnh(bc, goc, [str(a), str(b), str(tmp_path / "khong-co.jpg")])  # noqa: SLF001
    assert hop.lay() == ["https://nv", "https://u/a.jpg", "https://u/b.jpg"] and len(tai) == 2
    assert hop.lay() == ["https://nv", "https://u/a.jpg", "https://u/b.jpg"] and len(tai) == 2, "tải một lần"
    assert hop.lam_moi(hop.lay())[0] == "https://nv2" and len(tai) == 4
    mot = ak._HopThemAnh(bc, goc, str(a))  # noqa: SLF001 — một tấm như cũ
    assert mot.lay() == ["https://nv", "https://u/a.jpg"]


def test_khuon_hop_cap_nhat_ghi_mau_phong_cach(tmp_path):
    """Khuôn kiểu hộp: `khuon_bia.cap_nhat` ghi `tep_mau` (bìa thật sáng/sạch nhất của các video đủ bằng chứng)."""
    import json as _json
    goc = str(tmp_path)
    _kenh(goc)

    def chi_so(ma, imp, ctr):
        dd = os.path.join(duong_kenh(goc, "KH"), "chi-so", ma, "300h")
        os.makedirs(dd, exist_ok=True)
        with io.open(os.path.join(dd, "tong-quan.json"), "w", encoding="utf-8") as tep:
            _json.dump({"impressions": imp, "ctr": ctr, "views": imp * ctr / 100.0}, tep)
        with io.open(os.path.join(dd, "_thong-tin.json"), "w", encoding="utf-8") as tep:
            _json.dump({"tieu_de": ma, "ngay_dang": "2026-09-10T11:00:00.000Z"}, tep)
    for i, (imp, ctr) in enumerate([(5000, 3.0), (8000, 4.0), (9000, 4.5)]):
        chi_so("vidNEN{0:05d}".format(i), imp, ctr)
    chi_so("vidHOP00001", 106000, 5.9)
    chi_so("vidHOP00002", 200000, 5.2)

    def tai(url):
        buf = io.BytesIO()
        Image.new("RGB", (320, 180), (235, 215, 195) if "HOP00002" in url else (120, 80, 60)).save(buf, "JPEG")
        return buf.getvalue()

    def goi(loi_nhac, **_kw):
        return _json.dumps(dict(KC_HOP, bo_cuc="text boxes left"))
    ket = kb.cap_nhat(goc, "KH", goi, tai_anh=tai)
    assert btk.kieu_hop(ket["khuon_chu"]) and ket["video_id"] == "vidHOP00001"
    assert ket.get("tep_mau") and ket["tep_mau"][0].endswith("vidHOP00002-that.jpg"), ket.get("tep_mau")
