"""21/10/2026 — nhân vật nhất quán: kênh lấy khuôn kênh gốc không được giữ chữ tả nhân vật CŨ (`core/nhan_vat_nhat_quan`,
`mo_kenh.dung_kenh`), kênh THAY vì tài khoản không được phân phối giữ NGUYÊN mọi thứ (`mo_kenh.nhan_ban_giu_nguyen`),
tự kiểm hằng ngày (`tu_kiem.kiem_nhan_vat`), giám khảo ảnh cảnh lấy ẢNH tham chiếu làm chuẩn (`chon_anh_canh`).
Mọi thứ trong tmp; AI thay bằng hàm giả. Mã kênh là mã giả."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

GOC_REPO = Path(__file__).resolve().parent.parent
if str(GOC_REPO) not in sys.path:
    sys.path.append(str(GOC_REPO))

from core import chon_anh_canh as cac  # noqa: E402
from core import mo_kenh as mk  # noqa: E402
from core import nhan_vat_nhat_quan as nv  # noqa: E402
from core import tu_kiem  # noqa: E402

NOW = dt.datetime(2026, 10, 21, 9, 0)
LOCK_GOC = ("round pure-white mochi head with no hair, two dark dot eyes, faint pink cheeks, mustard-yellow knit cardigan "
            "over white collared shirt, dark indigo trousers, fine indigo-brown outline, painterly texture, expression free "
            "per scene")
REF_GOC = ("The ATTACHED reference image IS the character — match the round white mochi head, dot eyes, faint pink cheeks, "
           "mustard knit cardigan over a white collared shirt and indigo trousers exactly.")
LOCK_MOI = "Japanese man, early 30s, wire-rimmed glasses, messy dark hair, dark turtleneck, contemplative intellectual expression"
PROMPT_MOI = ("A sharp Japanese man in his early 30s with wire-rimmed glasses, messy dark hair, a dark turtleneck sweater, "
              "illustrated in a clean anime psychological thriller art style.")


def _style(lock, ref, prompt, image_style, them=""):
    return ("# ===\n#  PHONG CÁCH KÊNH GỐC — linh vật đầu mochi, áo mustard\n# ===\n\n"
            'style_name: "mochi_head_painterly_mustard"\n'
            'image_style: "{0}"\n'
            'palette: "mustard cardigan (#D9A441), warm amber light (#F0B65A)"\n'
            'negative_prompt: "no photorealism, no second mustard-cardigan figure"\n'
            'reference_lock: "{1}"\n'
            'default_character_prompt: "{2}"\n'
            'default_character_lock: "{3}"\n'
            'engagement_rules: "viewers are kind"\n'
            'audience_culture_note: "office pantry, cafe table"\n{4}').format(image_style, ref, prompt, lock, them)


MD_7 = ("You are a storyboard director.\r\n\r\n## THE REFERENCE CHARACTER\r\n\r\nIt is the only white mochi-headed figure in "
        "a mustard knit cardigan; others are beige figures.\r\n\r\n## STYLE\r\n\r\n<<IMAGE_STYLE>>\r\n")


def _kenh(goc, ma, style, md=MD_7, kenh_yaml=None):
    d = Path(goc) / "CHANNEL" / ma
    (d / "prompt").mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text(kenh_yaml or 'ma: "{0}"\nnhom: "g"\ntep: "t"\n'.format(ma), encoding="utf-8")
    (d / "style.yaml").write_text(style, encoding="utf-8")
    (d / "prompt" / "7-canh.md").write_bytes(md.encode("utf-8"))
    (d / "prompt" / "2-viet.md").write_text("viết bài, không nói về nhân vật", encoding="utf-8")
    return d


@pytest.fixture()
def goc(tmp_path):
    g = tmp_path / "MyTool"
    g.mkdir()
    return str(g)


# ── từ cũ (thuần) ────────────────────────────────────────────────────────────────
def test_tu_cu_rut_net_nhan_vat_cu_khong_rut_tu_chung():
    tu = nv.tu_cu([LOCK_GOC, REF_GOC], [LOCK_MOI, PROMPT_MOI])
    for t in ("mochi", "mustard", "dot eyes", "pink cheeks", "indigo", "pure-white", "painterly", "collared"):
        assert t in tu, t
    for t in ("eyes", "hair", "dark", "glasses", "shirt", "outline", "texture", "scene", "expression"):
        assert t not in tu, t
    assert nv.tu_cu([LOCK_MOI], [LOCK_MOI, PROMPT_MOI]) == []                           # cùng nhân vật → không gì
    # kiểu vẽ giữ nguyên họ → từ kiểu vẽ KHÔNG thành từ cũ
    tu2 = nv.tu_cu(["older person in nostalgic anime style, chestnut-brown cardigan, round brown-rimmed glasses"],
                   ["elderly woman, silver short bob, soft cream cardigan, Ghibli-like soft painting"])
    assert "chestnut" in tu2 and "brown-rimmed" in tu2 and "anime" not in tu2 and "nostalgic" not in tu2


def test_tim_theo_ranh_gioi_tu():
    assert nv.tim("https://www.youtube.com/@kimochi_shikumi", ["mochi"]) == []
    assert nv.tim('style_name: "mochi_head_painterly"', ["mochi"]) == ["mochi"]
    assert nv.tim("a pure white head", ["pure-white"]) == ["pure-white"]


# ── viết lại (AI giả + mã kiểm) ──────────────────────────────────────────────────────
def _tra_sach(style_moi="clean anime"):
    def goi(loi_nhac):
        muc = json.loads(loi_nhac[loi_nhac.index("ITEMS TO REWRITE (JSON):") + 24:loi_nhac.rindex("Return ONE JSON")].strip())
        s = {k: ("clean_anime_turtleneck" if k == "style_name" else "{0} illustration of the man in a dark turtleneck "
                 "with wire-rimmed glasses, cool slate palette ({1})".format(style_moi, k)) for k in muc["style"]}
        d = {i: v.replace("It is the only white mochi-headed figure in a mustard knit cardigan; others are beige figures.",
                          "He is the only man in a dark turtleneck; others are ordinary people.") for i, v in muc["doan"].items()}
        goi.dem += 1
        return json.dumps({"style": s, "doan": d})
    goi.dem = 0
    return goi


def test_viet_lai_thu_muc_het_tu_cu_giu_khoa_nhan_vat_va_cho_giu(goc):
    d = _kenh(goc, "K-MOI", _style(LOCK_MOI, "The attached image IS the character.", PROMPT_MOI,
                                   "Soft painterly illustration. The reference character is a round white mochi-headed "
                                   "figure in a mustard-yellow cardigan."))
    tu = nv.tu_cu([LOCK_GOC, REF_GOC], [LOCK_MOI, PROMPT_MOI])
    cham = nv.quet_thu_muc(str(d), tu)
    assert "style.yaml:image_style" in cham and "style.yaml#dau" in cham and any(c.startswith("prompt/7-canh.md#") for c in cham)
    assert not any(c.startswith("prompt/2-viet.md") for c in cham)
    # lượt 1 AI còn sót "mochi" → mã loại, hỏi lại; lượt 2 sạch → ghi
    sach = _tra_sach()
    luot = []

    def goi(p):
        luot.append(p)
        if len(luot) == 1:
            return json.dumps({"style": {"image_style": "still a mochi figure"}, "doan": {}})
        return sach(p)
    kq = nv.viet_lai_thu_muc(str(d), tu, goi, lock=LOCK_MOI, prompt=PROMPT_MOI, log=lambda s: None)
    assert len(luot) == 2 and "REJECTED BY CODE CHECKS" in luot[1] and "mochi" in luot[0]
    assert nv.quet_thu_muc(str(d), tu) == {}
    s = (d / "style.yaml").read_text(encoding="utf-8")
    assert 'default_character_lock: "{0}"'.format(LOCK_MOI) in s and 'engagement_rules: "viewers are kind"' in s
    assert 'audience_culture_note: "office pantry, cafe table"' in s                       # khoá không dính: giữ nguyên
    assert set(kq["khoa"]) >= {"image_style", "palette", "negative_prompt", "style_name", "reference_lock"}
    md = (d / "prompt" / "7-canh.md").read_bytes().decode("utf-8")
    assert "<<IMAGE_STYLE>>" in md and "\r\n" in md and "He is the only man in a dark turtleneck" in md
    assert (d / "prompt" / "2-viet.md").read_text(encoding="utf-8") == "viết bài, không nói về nhân vật"


def test_viet_lai_hong_thi_nem_va_khong_ghi_gi(goc):
    d = _kenh(goc, "K-MOI", _style(LOCK_MOI, "x", PROMPT_MOI, "a round white mochi-headed figure"))
    truoc = (d / "style.yaml").read_text(encoding="utf-8")
    tu = nv.tu_cu([LOCK_GOC, REF_GOC], [LOCK_MOI, PROMPT_MOI])
    with pytest.raises(nv.LoiNhanVat):
        nv.viet_lai_thu_muc(str(d), tu, lambda p: '{"style": {}, "doan": {}}', lock=LOCK_MOI, prompt=PROMPT_MOI,
                            log=lambda s: None)
    assert (d / "style.yaml").read_text(encoding="utf-8") == truoc


# ── mo_kenh: kênh mới (nhân vật mới) phải viết lại; thiếu AI thì không dựng ───────────
def test_mo_kenh_viet_lai_nhan_vat_cu_khi_lay_khuon(goc):
    nguon = _kenh(goc, "K-GOC", _style(LOCK_GOC, REF_GOC, "old mochi prompt", "a round white mochi-headed figure"))
    dich = _kenh(goc, "K-MOI", _style(LOCK_MOI, "The attached image IS the character.", PROMPT_MOI,
                                      "a round white mochi-headed figure in a mustard cardigan"))
    goi = _tra_sach()
    kq = mk.viet_lai_nhan_vat_cu(str(nguon), str(dich), goi, log=lambda s: None)
    assert goi.dem == 1 and kq["sua"] and nv.quet_thu_muc(str(dich), kq["tu"]) == {}
    with pytest.raises(RuntimeError):
        d2 = _kenh(goc, "K-MOI2", _style(LOCK_MOI, "x", PROMPT_MOI, "a mochi figure"))
        mk.viet_lai_nhan_vat_cu(str(nguon), str(d2), None, log=lambda s: None)
    # cùng nhân vật (khuôn của chính nó) → không gọi AI
    d3 = _kenh(goc, "K-GIONG", _style(LOCK_GOC, REF_GOC, "old mochi prompt", "a round white mochi-headed figure"))
    goi3 = _tra_sach()
    assert mk.viet_lai_nhan_vat_cu(str(nguon), str(d3), goi3, log=lambda s: None)["sua"] == [] and goi3.dem == 0


# ── mo_kenh: kênh THAY giữ nguyên mọi thứ, không gọi AI, giọng kênh cũ ──────────────
def test_chuan_bi_kenh_thay_giu_nguyen_moi_thu(goc):
    ky = ('# ghi chú của kênh cũ\nma: "TLx-T7-K2"\nten: "Tên kênh"\nnhom: "g"\ntep: "t"\nngon_ngu: "ja"\n'
          'voice_id: "V-CU"   # giọng riêng\nky_tu_moi_phut: 271\ngio_dang: "20:00"\nnhip_dang: "20:00"\n'
          'luat_chon: "luật chọn của kênh cũ"\ndanh_sach_phat_kenh: "A | B | C"\nbia_lo_mau: "workspace/bia-x/thang"\n'
          'tu_chay: false\nnuoi_trang_chu: false\nthiet_lap_kenh: false\ntra_kho: "2026-10-20"\nthay_boi: "TLx-T7-K3"\n'
          'thu_muc_done: "DONE/TLx-T7-K2"\n')
    cu = _kenh(goc, "TLx-T7-K2", _style(LOCK_GOC, REF_GOC, "old mochi prompt", "a round white mochi-headed figure"),
               kenh_yaml=ky)
    (cu / "nv").mkdir()
    (cu / "nv" / "nv1.png").write_bytes(b"png" * 100)
    (cu / "thiet-lap").mkdir()
    (cu / "thiet-lap" / "ho-so.json").write_text(json.dumps({"ten": "ブランド名", "handle": "@brand", "logo": "logo.png"}),
                                                 encoding="utf-8")
    (cu / "thiet-lap" / "logo.png").write_bytes(b"i")
    (cu / "tu-hoc").mkdir()
    (cu / "tu-hoc" / "van.json").write_text("{}", encoding="utf-8")
    (cu / "chi-so").mkdir()
    (cu / "chi-so" / "bang-tom-tat.csv").write_text("x", encoding="utf-8")
    (cu / "may-ao.json").write_text(json.dumps({"tu_dang": False, "ghim_dom": False}), encoding="utf-8")
    (cu / "tra-kho.json").write_text(json.dumps({"kenh": {"tu_chay": True, "nuoi_trang_chu": False},
                                                 "may_ao": {"tu_dang": True, "ghim_dom": True}}), encoding="utf-8")
    hang = {"tep": "t", "nhom": "g", "loai": "thay_kenh_tu_dong", "kenh_goc": "TLx-T7-K2", "tu_dong": True,
            "giu_nguyen": True, "can_thuong_hieu": True}
    mk.luu_trang_thai(goc, {"kenh": {"TLx-T7-K3": dict(hang, trang_thai="de_xuat", kiem_cuoi=0, loi="")}})
    goi_dem, anh = [], []

    def ho_so(kenh, g, **kw):
        from core import thiet_lap_kenh as tl
        return tl.doc_ho_so(kenh, g)
    d = mk.chuan_bi(goc, "TLx-T7-K3", goi=lambda p, **k: goi_dem.append(p) or "{}",
                    tao_anh=lambda p, dich, **k: anh.append(dich), tao_ho_so=ho_so, kiem_handle=lambda h: h != "brand",
                    chep_chrome=lambda g, m, log=print, **k: ("da_chep", "giả"), gieo=lambda *a, **k: None,
                    log=lambda s: None, bay_gio=NOW)
    moi = Path(goc) / "CHANNEL" / "TLx-T7-K3"
    assert not goi_dem and not anh                                                        # không AI, không vẽ nhân vật mới
    for rel in ("style.yaml", "prompt/7-canh.md", "prompt/2-viet.md", "nv/nv1.png", "thiet-lap/logo.png", "tu-hoc/van.json"):
        assert (moi / rel).read_bytes() == (cu / rel).read_bytes(), rel
    assert not (moi / "chi-so").exists() and not (moi / "tra-kho.json").exists()
    from core.kenh import doc_yaml
    y, yc = doc_yaml(str(moi / "kenh.yaml")), doc_yaml(str(cu / "kenh.yaml"))
    assert y["ma"] == "TLx-T7-K3" and y["thay_cho"] == "TLx-T7-K2" and y["thu_muc_done"] == "DONE/TLx-T7-K3"
    assert y["voice_id"] == "V-CU" and str(y["ky_tu_moi_phut"]) == "271" and d["voice_id"] == "V-CU"
    for k in ("ten", "gio_dang", "nhip_dang", "luat_chon", "danh_sach_phat_kenh", "bia_lo_mau", "ngon_ngu", "tep", "nhom"):
        assert y[k] == yc[k], k
    assert y.get("tra_kho", "") == "" and y.get("thay_boi", "") == "" and str(y["tu_chay"]).lower() == "false"
    hs = json.loads((moi / "thiet-lap" / "ho-so.json").read_text(encoding="utf-8"))
    assert hs["ten"] == "ブランド名" and hs["handle"] != "@brand"                          # handle cũ đã có chủ → biến thể
    ma_ao = json.loads((moi / "may-ao.json").read_text(encoding="utf-8"))
    assert ma_ao["tu_dang"] is False and ma_ao["ghim_dom"] is True                       # công tắc gốc trước trả kho
    assert nv.kenh_goc_cua(goc, "TLx-T7-K3") == ""                                        # tự kiểm không so với kênh cũ


def test_kich_hoat_kenh_thay_giu_cong_tac_nuoi_trang_chu_cu(goc, tmp_path):
    cu = _kenh(goc, "TLx-T7-K2", _style(LOCK_GOC, REF_GOC, "p", "x"))
    (cu / "tra-kho.json").write_text(json.dumps({"kenh": {"nuoi_trang_chu": False}}), encoding="utf-8")
    _kenh(goc, "TLx-T7-K3", _style(LOCK_GOC, REF_GOC, "p", "x"),
          kenh_yaml='ma: "TLx-T7-K3"\nnhom: "g"\nnuoi_trang_chu: false\nthiet_lap_kenh: false\n')
    exe = Path(goc).parent / "TLx-T7-K3" / "TLx-T7-K3.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ")
    mk.luu_trang_thai(goc, {"kenh": {"TLx-T7-K3": {"trang_thai": "cho_chrome", "loai": "thay_kenh", "kenh_goc": "TLx-T7-K2"}}})
    r = mk.kich_hoat(goc, "TLx-T7-K3", kiem_dang_nhap=lambda e: (True, ""), them_vao_vm=lambda *a, **k: None,
                     log=lambda s: None, bay_gio=NOW)
    y = mk._kenh_yaml(goc, "TLx-T7-K3")
    assert r["trang_thai"] == "dang_thiet_lap" and str(y["thiet_lap_kenh"]).lower() == "true"
    assert str(y["nuoi_trang_chu"]).lower() == "false"


# ── tự kiểm hằng ngày ───────────────────────────────────────────────────────────────
def test_tu_kiem_nhan_vat_hong_thi_thu_lai_qua_bo_chay(goc, monkeypatch):
    _kenh(goc, "K-GOC", _style(LOCK_GOC, REF_GOC, "p", "a round white mochi-headed figure"))
    _kenh(goc, "K-MOI", _style(LOCK_MOI, "x", PROMPT_MOI, "a round white mochi-headed figure"),
          kenh_yaml='# KÊNH K-MOI — dựng bởi mo_kenh. Tệp t; lấy khuôn kiểu hình + prompt từ K-GOC.\nma: "K-MOI"\n')
    _kenh(goc, "K-RIENG", _style(LOCK_MOI, "x", PROMPT_MOI, "a man in a turtleneck"))
    K = tu_kiem.BoiCanh(goc, bay=NOW, thu=True, kenh_ds=["K-GOC", "K-MOI", "K-RIENG"], so={"muc": {}})
    ds = tu_kiem.kiem_nhan_vat(K)
    assert [(m["kenh"], m["tt"]) for m in ds] == [("K-MOI", tu_kiem.HONG)]
    assert ds[0]["thu_lai"] == "nhan_vat" and ds[0]["kenh_goc"] == "K-GOC" and "mochi" in ds[0]["bang_chung"]
    sinh = []
    monkeypatch.setattr(tu_kiem, "_sinh", lambda K_, lenh, ten: sinh.append(lenh) or (True, "đã chạy"))
    K2 = tu_kiem.BoiCanh(goc, bay=NOW, kenh_ds=["K-MOI"], so={"muc": {}})
    tu_kiem.xu_ly(K2, tu_kiem.kiem_nhan_vat(K2), {})
    assert sinh and sinh[0][-4:] == ["sua", "K-MOI", "--goc-kenh", "K-GOC"]


# ── giám khảo ảnh cảnh: ảnh tham chiếu là chuẩn ─────────────────────────────────────
def test_giam_khao_loai_tam_khac_nhan_vat_tham_chieu():
    co_ref = cac.loi_nhac_cham(loi_doc="x", mo_ta="the reference character", phong_cach="mochi style", so_tham_chieu=1,
                               so_ung_vien=2)
    assert "ONLY truth" in co_ref and '"khac_nhan_vat": the main character' in co_ref
    khong_ref = cac.loi_nhac_cham(loi_doc="x", mo_ta="", phong_cach="", so_tham_chieu=0, so_ung_vien=2)
    assert '"khac_nhan_vat": the main character' not in khong_ref
    kq = cac.doc_cham({"ung_vien": [
        {"so": 1, "noi_dung": 9, "giong": 9, "loi": 9, "phong_cach": 9, "nhan_vat": 10, "khac_nhan_vat": True},
        {"so": 2, "noi_dung": 7, "giong": 8, "loi": 8, "phong_cach": 8, "nhan_vat": 9}]}, 2)
    assert kq[1]["tong"] == 0.0 and "khac_nhan_vat" in kq[1]["co"] and kq[2]["tong"] == 7.0
    ung = [{"tep": "a", "vong": 0, "so": 1, "cham": kq[1]}, {"tep": "b", "vong": 0, "so": 2, "cham": kq[2]}]
    assert cac.xep_hang(ung)[0]["tep"] == "b"
    assert "NOT the reference character" in cac.ghi_chu_viet_lai(ung)
