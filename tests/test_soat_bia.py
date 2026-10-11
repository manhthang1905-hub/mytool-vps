"""Soát chữ ảnh bìa + dải tối + vòng bìa mới (12/10/2026, `core/soat_bia.py`, `core/do_bia.soi_dai_toi`,
cổng `core/auto_khau._cong_chu_bia`, `_khau_thumbnail`).

Chẩn đoán 12/10/2026: bìa TL1-0021 in 「意かれない 無意識に意きつける」 (đúng: 惹), bìa TL2-0021 vẽ lại có dải tối đè
ngang ảnh, giám khảo mọi-tấm-bị-loại thì giao "tấm ít chữ nhất". Ảnh TỔNG HỢP (PIL), AI GIẢ — không mạng, không
ảnh/tên kênh thật."""

from __future__ import annotations

import base64
import io
import json
import os
import random
import types

import pytest
from PIL import Image, ImageDraw

from core import auto_khau, do_bia, soat_bia
from core import bia_theo_khuon as btk
from core.auto import LuotChay

SAI = "意かれない 無意識に意きつける"
DUNG = "惹かれない 無意識に惹きつける"
TIEU_DE = "【脳科学】人を惹きつける人が無意識にしている5つのこと"


# ── chuẩn hoá / so chữ ───────────────────────────────────────────────────────


def test_khop_chu_tung_ky_tu():
    assert soat_bia.khop_chu("惹かれない\n無意識に惹きつける", DUNG)
    assert not soat_bia.khop_chu(SAI, DUNG)                      # 意 ≠ 惹 — một ký tự cũng trượt
    assert soat_bia.khop_chu("、、惹かれない 無意識に惹きつける", DUNG)   # dấu câu bị bỏ
    assert soat_bia.khop_chu("くく惹かれない無意識に惹きつける", DUNG)    # ≤ 2 ký tự thừa ở đầu (vệt sáng đọc nhầm)
    assert not soat_bia.khop_chu("くくく惹かれない無意識に惹きつける", DUNG)
    assert not soat_bia.khop_chu("惹かれない無意識", DUNG)       # thiếu chữ
    assert soat_bia.khop_chu("７つの習慣", "7つの習慣")           # NFKC


def test_nghi_sai_kanji_bat_y_thay_nha():
    nguon = TIEU_DE + "\n人を引きつける人には共通点があります。"
    g = soat_bia.nghi_sai_kanji(SAI, nguon)
    assert g and g[0]["sai"] == "意きつける" and "惹きつける" in g[0]["goi_y"]
    assert soat_bia.nghi_sai_kanji(DUNG, nguon) == []           # chữ đúng: không gợi ý bậy
    assert soat_bia.nghi_sai_kanji("人生後半で 強くなる男たち", "人生の後半から強くなっていく人") == []


# ── soát chính tả bằng AI giả ─────────────────────────────────────────────────


class _AiSoat:
    """Biên tập viên giả: chữ có 意 → sai, đưa bản sửa 惹; chữ khác → đúng. Ghi lại mọi lời nhắc."""

    def __init__(self, hong=False, sua_bay=False):
        self.loi_nhac = []
        self.hong = hong
        self.sua_bay = sua_bay

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        self.loi_nhac.append(loi_nhac)
        if self.hong:
            raise RuntimeError("cổng quá tải")
        chu = loi_nhac.split("THUMBNAIL TEXT (a space only marks a line break): 「", 1)[1].split("」", 1)[0]
        if "意き" in chu or "意か" in chu:
            moi = "hoàn toàn khác hẳn câu cũ rồi nhé" if self.sua_bay else chu.replace("意か", "惹か").replace(
                "意き", "惹き")
            return json.dumps({"dung": False, "loi": [{"sai": "意", "dung": "惹", "ly_do": "wrong kanji"}],
                               "chu_sua": moi}, ensure_ascii=False)
        return json.dumps({"dung": True, "loi": [], "chu_sua": ""})


def test_soat_chu_sua_va_soat_lai():
    ai = _AiSoat()
    r = soat_bia.soat_chu(ai, SAI, tieu_de=TIEU_DE, ngu_canh="人を引きつける人", thang=("m1",))
    assert r["ok"] is True and r["sua"] is True and r["chu"] == DUNG, r
    assert len(ai.loi_nhac) == 2 and "「" + DUNG + "」" in ai.loi_nhac[1]      # lượt 2 soát lại BẢN SỬA
    assert "意きつける" in ai.loi_nhac[0] and "Machine check" in ai.loi_nhac[0]  # gợi ý máy đi kèm


def test_soat_chu_dung_thi_giu_nguyen_mot_luot():
    ai = _AiSoat()
    r = soat_bia.soat_chu(ai, "人生後半で 強くなる男たち", tieu_de="人生の後半", thang=("m1",))
    assert r["ok"] is True and not r["sua"] and len(ai.loi_nhac) == 1


def test_soat_chu_ai_hong_la_CHUA_soat_khong_phai_dat():
    r = soat_bia.soat_chu(_AiSoat(hong=True), SAI, thang=("m1", "m2"))
    assert r["ok"] is None and r["chu"] == SAI


def test_soat_chu_ban_sua_khac_xa_thi_khong_nhan():
    r = soat_bia.soat_chu(_AiSoat(sua_bay=True), SAI, thang=("m1",))
    assert r["ok"] is False and r["chu"] == SAI and not r["sua"]


# ── đọc MÙ chữ trên ảnh ──────────────────────────────────────────────────────


def _mau_tb(url: str):
    raw = base64.b64decode(url.split(",", 1)[1])
    im = Image.open(io.BytesIO(raw)).convert("RGB").resize((8, 8))
    px = list(im.getdata())
    return tuple(sum(p[i] for p in px) // len(px) for i in range(3))


class _AiDoc:
    """AI đọc ảnh giả: nhìn MÀU nền của ảnh để biết "trên ảnh in gì" (bảng `theo_mau`), lần lượt theo `kich_ban`."""

    def __init__(self, theo_mau=None, kich_ban=None, hong=False):
        self.theo_mau = theo_mau or {}
        self.kich_ban = list(kich_ban or [])
        self.loi_nhac = []
        self.hong = hong

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        self.loi_nhac.append(loi_nhac)
        if self.hong:
            raise RuntimeError("mạng rớt")
        if "THUMBNAIL TEXT" in loi_nhac:                         # lượt soát chính tả (無意識 có 意 — đúng)
            chu = loi_nhac.split("「", 1)[1].split("」", 1)[0]
            return json.dumps({"dung": "意か" not in chu and "意き" not in chu, "loi": [], "chu_sua": ""})
        if self.kich_ban:
            chu = self.kich_ban.pop(0)
        else:
            m = _mau_tb(anh[0])
            chu = min(self.theo_mau.items(), key=lambda kv: sum(abs(a - b) for a, b in zip(kv[0], m)))[1]
        return json.dumps({"dong": chu.split(" "), "chu_thua": [], "ky_tu_hong": False, "vet_xoa": False},
                          ensure_ascii=False)


def test_kiem_chu_anh_doc_mu_va_da_so(tmp_path):
    tep = str(tmp_path / "a.png")
    Image.new("RGB", (1280, 720), (30, 30, 30)).save(tep)
    ai = _AiDoc(kich_ban=[DUNG, DUNG])
    r = soat_bia.kiem_chu_anh(ai, tep, DUNG, thang=("m",))
    assert r["dat"] is True and len(r["doc"]) == 2
    assert all(DUNG not in ln and "惹" not in ln for ln in ai.loi_nhac), "lời nhắc đọc ảnh không được lộ chữ mong đợi"
    r = soat_bia.kiem_chu_anh(_AiDoc(kich_ban=[SAI, SAI]), tep, DUNG, thang=("m",))
    assert r["dat"] is False and "≠ chữ đã soát" in r["ly_do"][0]
    ai = _AiDoc(kich_ban=[DUNG, SAI, SAI])                        # vênh → lượt thứ ba phân xử
    r = soat_bia.kiem_chu_anh(ai, tep, DUNG, thang=("m",))
    assert r["dat"] is False and len(r["doc"]) == 3
    r = soat_bia.kiem_chu_anh(_AiDoc(kich_ban=[SAI, DUNG, DUNG]), tep, DUNG, thang=("m",))
    assert r["dat"] is True


def test_kiem_chu_anh_ai_hong_la_None(tmp_path):
    tep = str(tmp_path / "a.png")
    Image.new("RGB", (1280, 720), (30, 30, 30)).save(tep)
    assert soat_bia.kiem_chu_anh(_AiDoc(hong=True), tep, DUNG, thang=("m",))["dat"] is None
    assert soat_bia.kiem_chu_anh(None, tep, DUNG)["dat"] is None


def test_chu_thua_vet_chu_cu_la_truot(tmp_path):
    tep = str(tmp_path / "a.png")
    Image.new("RGB", (1280, 720), (30, 30, 30)).save(tep)

    def ai(loi_nhac, **kw):
        return json.dumps({"dong": ["人生後半で", "強くなる男たち"], "chu_thua": ["人生後"], "ky_tu_hong": False,
                           "vet_xoa": True}, ensure_ascii=False)
    r = soat_bia.kiem_chu_anh(ai, tep, "人生後半で 強くなる男たち", thang=("m",))
    assert r["dat"] is False and any("vết" in x for x in r["ly_do"])


# ── dải tối mờ (đo điểm ảnh) ─────────────────────────────────────────────────


def _canh_ve(seed=3) -> Image.Image:
    """Tranh "căn phòng" có vân: nền ấm + kệ sách sọc dọc + nhân vật tròn bên trái."""
    rnd = random.Random(seed)
    im = Image.new("RGB", (1280, 720), (150, 95, 55))
    d = ImageDraw.Draw(im)
    for x in range(0, 1280, 22):
        c = rnd.randrange(60, 220)
        d.rectangle([x, 0, x + rnd.randrange(8, 18), 720], fill=(c, int(c * 0.65), int(c * 0.4)))
    for y in range(0, 720, 90):
        d.rectangle([0, y, 1280, y + 6], fill=(70, 40, 25))
    d.ellipse([90, 60, 400, 370], fill=(245, 245, 245), outline=(10, 10, 10), width=8)
    d.rectangle([150, 360, 340, 700], fill=(30, 30, 50))
    return im


def _phu_dai(im: Image.Image, hop, alpha=0.66, mau=(14, 10, 22)) -> Image.Image:
    lop = Image.new("RGBA", im.size, mau + (0,))
    mn = Image.new("L", im.size, 0)
    ImageDraw.Draw(mn).rounded_rectangle(hop, radius=20, fill=int(255 * alpha))
    lop.putalpha(mn)
    return Image.alpha_composite(im.convert("RGBA"), lop).convert("RGB")


def test_soi_dai_toi_bat_dai_toi_mo_kieu_TL2():
    nen = _canh_ve()
    assert not do_bia.soi_dai_toi(nen)["co"]
    loi = _phu_dai(nen, (20, 250, 1280, 650))                   # dải tối 66% phủ ngang, đè nửa người
    r = do_bia.soi_dai_toi(loi)
    assert r["co"] and r["dt_max"] >= 0.4, r
    assert do_bia.dai_toi_moi(loi, nen)["co"]                   # so với nền sạch: dải là do vẽ đè
    assert not do_bia.dai_toi_moi(loi, loi)["co"]               # nguồn cũng có → không phải lỗi mới


def test_soi_dai_toi_khong_bat_khoi_mau_dac_thiet_ke():
    nen = Image.new("RGB", (1280, 720), (245, 236, 215))        # nền kem trơn + hộp cam đặc (thiết kế mô hình vẽ)
    d = ImageDraw.Draw(nen)
    d.rectangle([60, 60, 900, 300], fill=(240, 160, 40))
    d.rectangle([60, 330, 900, 600], fill=(240, 160, 40))
    assert not do_bia.soi_dai_toi(nen)["co"]
    den = _canh_ve()                                            # hộp ĐEN đặc chữ trắng trên tranh
    ImageDraw.Draw(den).rounded_rectangle([40, 40, 760, 380], radius=24, fill=(18, 18, 18))
    assert not do_bia.soi_dai_toi(den)["co"]


def test_bo_cuc_dat_chan_khung_lon_va_che_chu_the():
    assert not do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 1, "chong_khung": False, "che_chu_the": 0.1,
                                             "dt_khung": 0.5}})
    assert not do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 1, "chong_khung": False, "che_chu_the": 0.1,
                                             "che_chu_the_phan": 0.4}})
    assert not do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 0, "dai_toi": "dải tối mờ 60% khung"}})
    assert do_bia.bo_cuc_dat({"bo_cuc": {"so_khung": 1, "chong_khung": False, "che_chu_the": 0.1,
                                         "dt_khung": 0.12, "che_chu_the_phan": 0.05}})
    import numpy as np
    m = np.zeros((72, 128), dtype=bool)
    m[:, :32] = True                                             # chủ thể: 1/4 trái
    assert do_bia.phan_chu_the_bi_che(m, [(0, 360, 1280, 720)], 1280, 720) == pytest.approx(0.5, abs=0.02)
    assert do_bia.dien_tich_hop([(0, 0, 640, 720), (320, 0, 960, 720)], 1280, 720) == pytest.approx(0.75, abs=0.02)


def test_ve_chu_bao_cao_dien_tich_khung(tmp_path):
    if not btk._tim_font("", "人生後半", "ja"):  # noqa: SLF001
        pytest.skip("máy không có font Nhật")
    im = Image.new("RGB", (1280, 720), (250, 250, 250))         # nền sọc: chữ viền mảnh cần khung
    d = ImageDraw.Draw(im)
    for x in range(0, 1280, 8):
        d.rectangle([x, 0, x + 3, 720], fill=(8, 8, 8))
    nen = str(tmp_path / "nen.png")
    im.save(nen)
    bc: dict = {}
    tang = btk.tach_chu_mac_dinh("人生後半で 強くなる男たち", {})
    btk.ve_chu_len_anh(nen, str(tmp_path / "t.png"), btk.bo_tri_chu("khuon", tang), bao_cao=bc)
    bo = bc["bo_cuc"]
    assert "dt_khung" in bo and "che_chu_the_phan" in bo
    if bo["so_khung"]:
        assert bo["dt_khung"] > 0


# ── cổng chữ trên ảnh của khâu bìa ───────────────────────────────────────────


def _bc(goc, goi_chat, dong):
    kenh = types.SimpleNamespace(ma="KX", ngon_ngu="ja", che_do_tieu_de="nguyen_goc", mo_hinh="m",
                                 chon_bia_ai=True, so_luot_cham_bia=1, mo_hinh_cham_bia="", bia_kham_pha=False)
    return auto_khau.BoiCanh(goc=goc, kenh=kenh, goi_chat=goi_chat, on_log=dong.append, ngu=lambda _s: None)


def _luot_bia(tmp_path, chu=DUNG):
    d = tmp_path / "PROJECTS" / "AUTO" / "KX" / "0001"
    (d / "7-thumbnail").mkdir(parents=True)
    (d / "1-tieu-de.txt").write_text("TITLE: {0}\nTHUMB: {1}\n".format(TIEU_DE, chu), encoding="utf-8")
    (d / "1-kich-ban.txt").write_text("人を引きつける人には共通点があります。", encoding="utf-8")
    return LuotChay(ma_kenh="KX", ma_luot="0001", thu_muc=str(d)), str(d / "7-thumbnail")


_MAU = {1: (40, 40, 160), 2: (160, 40, 40), 3: (40, 160, 40)}


def _bo_bia(tm, chon_so=2):
    """Ba tấm màu khác nhau; tấm chọn = `chon_so` (điểm cao nhất), xuất CHON + chon-bia.json như giám khảo."""
    from core import chon_bia
    for so, mau in _MAU.items():
        Image.new("RGB", (1280, 720), mau).save(os.path.join(tm, "thumb_{0:03d}.png".format(so)))
    chon_bia._xuat_jpg(os.path.join(tm, "thumb_{0:03d}.png".format(chon_so)),  # noqa: SLF001
                       os.path.join(tm, "CHON-thumb_{0:03d}.jpg".format(chon_so)))
    uv = [{"so": so, "tong_diem": {2: 90, 1: 70, 3: 50}[so], "loai": "", "kieu": "k{0}".format(so)} for so in _MAU]
    with open(os.path.join(tm, "chon-bia.json"), "w", encoding="utf-8") as tep:
        json.dump({"chon": {"so": chon_so, "tep": "CHON-thumb_{0:03d}.jpg".format(chon_so), "chon_boi": "ai"},
                   "ung_vien": uv}, tep, ensure_ascii=False)


def test_cong_chu_bia_loai_tam_sai_chu_doi_tam_ke(tmp_path):
    luot, tm = _luot_bia(tmp_path)
    _bo_bia(tm)
    ai = _AiDoc(theo_mau={_MAU[1]: DUNG, _MAU[2]: SAI, _MAU[3]: DUNG})
    dong: list = []
    bc = _bc(str(tmp_path), ai, dong)
    r = auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert r.get("doi") and r["tep"] == "CHON-thumb_001.jpg", (r, dong)
    assert os.path.isfile(os.path.join(tm, "_bi-loai", "CHON-thumb_002.jpg"))
    du = json.load(open(os.path.join(tm, "chon-bia.json"), encoding="utf-8"))
    assert du["chon"]["so"] == 1 and any(u["so"] == 2 and "cổng chữ" in u["loai"] for u in du["ung_vien"])
    r = auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert r["dat"] is True, (r, dong)
    n = len(ai.loi_nhac)
    assert auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)["dat"] is True  # noqa: SLF001
    assert len(ai.loi_nhac) == n, "cùng ảnh + cùng chữ: dùng sổ, không gọi AI lần hai"


def test_cong_chu_bia_giam_khao_hong_van_doi_sang_tam_khac(tmp_path):
    """Giám khảo hỏng → đường lùi "luat" (không bảng điểm): tấm lùi sai chữ thì thử các tấm khác của lô, không
    làm lô mới ngay."""
    luot, tm = _luot_bia(tmp_path)
    _bo_bia(tm)
    with open(os.path.join(tm, "chon-bia.json"), "w", encoding="utf-8") as tep:
        json.dump({"chon": {"so": 2, "tep": "CHON-thumb_002.jpg", "chon_boi": "luat"}, "ung_vien": []}, tep)
    ai = _AiDoc(theo_mau={_MAU[1]: SAI, _MAU[2]: SAI, _MAU[3]: DUNG})
    bc = _bc(str(tmp_path), ai, [])
    assert auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)["tep"] == "CHON-thumb_001.jpg"  # noqa: SLF001
    assert auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)["tep"] == "CHON-thumb_003.jpg"  # noqa: SLF001
    assert auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)["dat"] is True  # noqa: SLF001


def test_cong_chu_bia_het_tam_thi_HetBiaDat(tmp_path):
    luot, tm = _luot_bia(tmp_path)
    _bo_bia(tm)
    ai = _AiDoc(theo_mau={_MAU[1]: SAI, _MAU[2]: SAI, _MAU[3]: SAI})
    bc = _bc(str(tmp_path), ai, [])
    with pytest.raises(auto_khau.HetBiaDat):
        for _ in range(5):
            auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert not [t for t in os.listdir(tm) if t.startswith("CHON-")]


def test_cong_chu_bia_ai_hong_khong_bao_gio_la_dat(tmp_path):
    luot, tm = _luot_bia(tmp_path)
    _bo_bia(tm)
    bc = _bc(str(tmp_path), _AiDoc(hong=True), [])
    with pytest.raises(RuntimeError) as e:
        auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert not isinstance(e.value, auto_khau.HetBiaDat) and "thử lại" in str(e.value)


def test_cong_chu_bia_chan_dai_toi_ve_de_so_voi_ban_truoc(tmp_path):
    """Kiểu TL2-0021: `CHON-*` bị lệnh vẽ lại thay bằng bản có dải tối; bản trước nằm ở `_truoc-do-bia/`."""
    luot, tm = _luot_bia(tmp_path, chu="人生後半で 強くなる男たち")
    from core import chon_bia
    goc_anh = _canh_ve()
    os.makedirs(os.path.join(tm, "_truoc-do-bia"))
    goc_anh.save(os.path.join(tm, "_truoc-do-bia", "CHON-thumb_013.jpg"), quality=92)
    _phu_dai(goc_anh, (20, 250, 1280, 650)).save(os.path.join(tm, "x.png"))
    chon_bia._xuat_jpg(os.path.join(tm, "x.png"), os.path.join(tm, "CHON-thumb_013.jpg"))  # noqa: SLF001
    os.remove(os.path.join(tm, "x.png"))
    with open(os.path.join(tm, "chon-bia.json"), "w", encoding="utf-8") as tep:
        json.dump({"chon": {"so": 13, "tep": "CHON-thumb_013.jpg", "chon_boi": "ai"},
                   "ung_vien": [{"so": 13, "tong_diem": 62, "loai": ""}]}, tep)
    ai = _AiDoc(kich_ban=["人生後半で 強くなる男たち"] * 4)
    with pytest.raises(auto_khau.HetBiaDat) as e:
        auto_khau._cong_chu_bia(_bc(str(tmp_path), ai, []), luot, tm, "人生後半で 強くなる男たち")  # noqa: SLF001
    assert "dải tối" in str(e.value)
    assert not any("Read the text" in x for x in ai.loi_nhac), "lỗi bố cục: khỏi tốn lượt đọc chữ"


# ── soát chữ trước khi vẽ + vòng bìa mới ─────────────────────────────────────


def test_soat_chu_bia_luot_sua_tieu_de_va_doi_tam_cu(tmp_path):
    luot, tm = _luot_bia(tmp_path, chu=SAI)
    Image.new("RGB", (64, 36), (1, 2, 3)).save(os.path.join(tm, "thumb_001.png"))
    with open(os.path.join(tm, "ke-hoach-bia.json"), "w", encoding="utf-8") as tep:
        json.dump({"muc": [{"so": 1, "chu_du_kien": SAI.replace(" ", "")}]}, tep, ensure_ascii=False)
    dong: list = []
    r = auto_khau._soat_chu_bia_luot(_bc(str(tmp_path), _AiSoat(), dong), luot)  # noqa: SLF001
    assert r["sua"] and r["chu"] == DUNG and r["chu_cu"] == SAI
    assert "THUMB: " + DUNG in open(os.path.join(luot.thu_muc, "1-tieu-de.txt"), encoding="utf-8").read()
    assert not os.path.exists(os.path.join(tm, "thumb_001.png"))
    assert os.path.isfile(os.path.join(tm, "_chu-sai-1", "thumb_001.png"))
    assert os.path.isfile(os.path.join(tm, "_chu-sai-1", "ke-hoach-bia.json"))
    assert auto_khau._hau_to_khoa_bia(tm, DUNG).startswith(":c")  # noqa: SLF001 — khoá chat/ảnh đổi theo chữ mới


def test_soat_chu_bia_luot_chu_nguoi_dua_khong_tu_sua(tmp_path):
    luot, tm = _luot_bia(tmp_path, chu=SAI)
    luot.dau_vao["chu_bia"] = SAI
    dong: list = []
    r = auto_khau._soat_chu_bia_luot(_bc(str(tmp_path), _AiSoat(), dong), luot)  # noqa: SLF001
    assert r.get("nguoi_dua") and "THUMB: " + SAI in open(os.path.join(luot.thu_muc, "1-tieu-de.txt"),
                                                          encoding="utf-8").read()


def test_khau_bia_lam_lo_moi_roi_chan_va_bao(tmp_path, monkeypatch):
    luot, tm = _luot_bia(tmp_path)
    dong: list = []
    bc = _bc(str(tmp_path), _AiSoat(), dong)
    lan = {"n": 0}

    def lo_hong(_bc, _luot, _tt):
        lan["n"] += 1
        Image.new("RGB", (64, 36), (9, 9, 9)).save(os.path.join(tm, "thumb_001.png"))
        raise auto_khau.HetBiaDat("giám khảo loại mọi tấm — nhân vật dị dạng ×7")
    bao = []
    monkeypatch.setattr(auto_khau, "_mot_lo_bia", lo_hong)
    monkeypatch.setattr(auto_khau, "_bao_bia_khong_dat", lambda *a: bao.append(a))
    with pytest.raises(RuntimeError, match="KHÔNG bàn giao"):
        auto_khau._khau_thumbnail(bc)(luot, None)
    assert lan["n"] == auto_khau.BIA_SO_VONG_TOI_DA + 1 and bao
    assert sorted(t for t in os.listdir(tm) if t.startswith("_vong-")) == [
        "_vong-{0}".format(i) for i in range(1, auto_khau.BIA_SO_VONG_TOI_DA + 1)]
    assert json.load(open(os.path.join(tm, "vong-bia.json"), encoding="utf-8"))["vong"] == auto_khau.BIA_SO_VONG_TOI_DA
    dan = auto_khau._loi_nhac_vong(tm)  # noqa: SLF001
    assert "attempt #" in dan and "deformed character" in dan
    # chạy lại khi đã hết vòng: không làm thêm lô nào (không đốt tiền), vẫn chặn
    with pytest.raises(RuntimeError):
        auto_khau._khau_thumbnail(bc)(luot, None)
    assert lan["n"] == auto_khau.BIA_SO_VONG_TOI_DA + 2


def test_khau_bia_lo_moi_dat_thi_giao(tmp_path, monkeypatch):
    luot, tm = _luot_bia(tmp_path)
    bc = _bc(str(tmp_path), _AiSoat(), [])
    lan = {"n": 0}

    def lo(_bc, _luot, _tt):
        lan["n"] += 1
        if lan["n"] == 1:
            raise auto_khau.HetBiaDat("mọi tấm bìa hợp lệ đều hỏng ở cổng chữ")
        return {"so_thumbnail": 7}
    monkeypatch.setattr(auto_khau, "_mot_lo_bia", lo)
    ket = auto_khau._khau_thumbnail(bc)(luot, None)
    assert ket["so_thumbnail"] == 7 and lan["n"] == 2
    assert auto_khau._hau_to_khoa_bia(tm) == ":lo1"  # noqa: SLF001 — lô 2 có khoá việc mới
