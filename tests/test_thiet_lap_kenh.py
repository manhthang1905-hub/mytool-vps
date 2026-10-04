"""Tự thiết lập kênh YouTube (03/10/2026): HÀM THUẦN của `core/thiet_lap_kenh.py` (hồ sơ) và
`vm/thiet_lap_kenh_dom.py` (so khác biệt, luật đổi tên/handle, sổ, chỗ nối agent). Không Chrome, không mạng."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
for _p in (str(GOC), str(VM)):
    if _p not in sys.path:
        sys.path.append(_p)

import nuoi_trang_chu as n  # noqa: E402
import thiet_lap_kenh_dom as t  # noqa: E402
from core import thiet_lap_kenh as tl  # noqa: E402

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageChops  # noqa: E402

MO_TA = "「自分のペースで生きたい」。そう感じているあなたのための心理学チャンネルです。" + "休日は家でゆっくり過ごしたい。" * 25
GUIDE = """# Thiết lập

## 1. TLX-A — 凪の心理学

- **Tuyến:** x

### Bước 1 · Tên kênh và handle

| | Tên | Handle | Vì sao |
|---|---|---|---|
| ★ Khuyên dùng | **凪の心理学** (なぎ) | `@nagi-shinri` | x |

```
凪の心理学
```

```
nagi-shinri
```

### Bước 2 · Mô tả kênh (xxx ký tự)

```
%s
```

### Bước 3 · Ảnh hồ sơ

![logo](TLX-A/logo.png)

Chữ trên banner (code vẽ): 凪の心理学 · 波立たない心で。 · 2日に1本

### Bước 6 · Từ khoá kênh (3 cụm)

```
心理学, 自分のペース, マイペース
```

### Bước 7 · Danh sách phát (2 cái)

1. **家が好きな人の心理**
   家で過ごす時間を大切にする人の話。

2. **味方のふりをする人（フレネミー）**
   見分け方と距離の取り方。

### Bước 8 · Giọng đọc

xong
""" % MO_TA


def _anh(duong: Path, kt, mau=(40, 90, 140)):
    duong.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", kt, mau).save(duong)
    return duong


def _kenh_yaml(goc: Path, kenh: str, them: str = ""):
    d = goc / "CHANNEL" / kenh
    d.mkdir(parents=True, exist_ok=True)
    (d / "kenh.yaml").write_text('ten: "(tên tạm) — tâm lý"\nngon_ngu: "ja"\nnhom: "g1"\ntep: "t1"\n'
                                 'danh_sach_phat_kenh: "家が好きな人の心理 | 動じない人の心理"\n' + them, encoding="utf-8")
    return d


@pytest.fixture()
def goc_tam(tmp_path):
    """Kho giả: bộ thiết lập có sẵn cho TLX-A (ảnh KHÔNG đúng cỡ để thử cắt) + CHANNEL/TLX-A."""
    bo = tmp_path / "workspace" / "thiet-lap-kenh-moi"
    bo.mkdir(parents=True)
    (bo / "HUONG-DAN-THIET-LAP.md").write_text(GUIDE, encoding="utf-8")
    _anh(bo / "TLX-A" / "logo.png", (1000, 900))
    _anh(bo / "TLX-A" / "banner.png", (2560, 1440))
    _anh(bo / "TLX-A" / "watermark.png", (300, 300))
    _kenh_yaml(tmp_path, "TLX-A")
    return tmp_path


# ═══════════════════ PHẦN 1: HỒ SƠ ═══════════════════════════════════════════
def test_ho_so_tu_bo_san_du_truong_va_kich_thuoc(goc_tam):
    hs = tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    thu_muc = tl.thu_muc_thiet_lap("TLX-A", str(goc_tam))
    assert tl.kiem_ho_so(hs, thu_muc) == []
    for k in tl.TRUONG_BAT_BUOC:
        assert hs.get(k), k
    assert hs["ten"] == "凪の心理学" and hs["handle"] == "@nagi-shinri" and hs["nguon"] == "bo-san"
    # đúng từng chữ như hướng dẫn (không NFKC) + tên còn thiếu lấy từ kenh.yaml `danh_sach_phat_kenh`
    assert [d["ten"] for d in hs["danh_sach_phat"]] == ["家が好きな人の心理", "味方のふりをする人（フレネミー）", "動じない人の心理"]
    assert tl.kich_thuoc_anh(tl.duong_anh(hs, "logo", thu_muc)) == (800, 800)
    assert tl.kich_thuoc_anh(tl.duong_anh(hs, "banner", thu_muc)) == (2560, 1440)
    assert tl.kich_thuoc_anh(tl.duong_anh(hs, "hinh_mo", thu_muc)) == (150, 150)
    assert hs["mac_dinh_tai_len"]["ngon_ngu"] == "ja" and hs["mac_dinh_tai_len"]["danh_muc"] in tl.DANH_MUC
    assert hs["quoc_gia"] == "JP" and hs["banner_chu"][0] == "凪の心理学"


def test_tao_khong_ghi_de_tru_khi_lam_lai(goc_tam):
    tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    hs = tl.doc_ho_so("TLX-A", str(goc_tam))
    hs["ten"] = "TÊN CHỦ SỬA TAY"
    hs["mo_ta"] = "x" * 400
    tl.ghi_ho_so("TLX-A", hs, str(goc_tam))
    hs2 = tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    assert hs2["ten"] == "TÊN CHỦ SỬA TAY" and hs2["mo_ta"] == "x" * 400          # không ghi đè
    hs3 = tl.tao("TLX-A", str(goc_tam), lam_lai=["ten"], log=lambda s: None)
    assert hs3["ten"] == "凪の心理学" and hs3["mo_ta"] == "x" * 400                 # chỉ làm lại mục được yêu cầu


def test_tao_thieu_anh_thi_lam_lai_anh(goc_tam):
    tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    thu_muc = Path(tl.thu_muc_thiet_lap("TLX-A", str(goc_tam)))
    (thu_muc / "logo.png").unlink()
    hs = tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    assert (thu_muc / "logo.png").is_file() and tl.kiem_ho_so(hs, str(thu_muc)) == []


def test_ho_so_nhap_llm_va_anh_gia_cho_kenh_chua_co_bo_san(goc_tam):
    _kenh_yaml(goc_tam, "TLX-B", "")
    goi_goi = []

    def goi(p, **kw):
        goi_goi.append(p)
        return "```json\n" + json.dumps({
            "ten": "夜明けの心理学", "handle": "@Yoake-Shinri!", "tu_khoa_chinh": "心理学",
            "mo_ta": MO_TA, "tu_khoa": ["心理学", "夜", "朝"] + ["kw%d" % i for i in range(200)],
            "danh_sach_phat": [{"ten": "家が好きな人の心理", "mo_ta": "a"}, {"ten": "新しい", "mo_ta": "b"}],
            "danh_muc": "people", "banner_chu": ["夜明けの心理学", "朝のひとやすみ", "毎日7時"]}, ensure_ascii=False) + "\n```"

    ve = []

    def tao_anh(prompt, dich, tham_chieu=()):
        ve.append(prompt)
        _anh(Path(dich), (1600, 900), (10, 20, 30))
        return dich

    hs = tl.tao("TLX-B", str(goc_tam), goi=goi, tao_anh=tao_anh, log=lambda s: None)
    thu_muc = tl.thu_muc_thiet_lap("TLX-B", str(goc_tam))
    assert tl.kiem_ho_so(hs, thu_muc) == []
    assert hs["nguon"] == "llm" and hs["handle"] == "@yoake-shinri"                  # handle làm sạch
    assert len(tl.tu_khoa_chuoi(hs["tu_khoa"])) <= tl.GIOI_HAN_TU_KHOA
    assert hs["mac_dinh_tai_len"]["danh_muc"] == "people"
    assert len(goi_goi) == 1 and "ja" in goi_goi[0] and len(ve) == 2                  # 1 lượt LLM, 2 ảnh (logo, banner)
    assert tl.kich_thuoc_anh(tl.duong_anh(hs, "banner", thu_muc)) == (2560, 1440)


def test_llm_tra_rac_thi_bao_loi_sau_2_lan(goc_tam):
    _kenh_yaml(goc_tam, "TLX-C", "")
    lan = []
    with pytest.raises(RuntimeError):
        tl.sinh_bang_llm("TLX-C", str(goc_tam), lambda p, **k: (lan.append(1), "không phải json")[1])
    assert len(lan) == 2


def test_gioi_han_ky_tu_va_truong_thieu(goc_tam):
    hs = tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    thu_muc = tl.thu_muc_thiet_lap("TLX-A", str(goc_tam))
    assert any("mô tả dài" in x for x in tl.kiem_ho_so(dict(hs, mo_ta="あ" * 1001), thu_muc))
    assert any("mô tả ngắn" in x for x in tl.kiem_ho_so(dict(hs, mo_ta="あ" * 100), thu_muc))
    assert any("từ khoá dài" in x for x in tl.kiem_ho_so(dict(hs, tu_khoa=["あ" * 30] * 20), thu_muc))
    assert any("tên dài" in x for x in tl.kiem_ho_so(dict(hs, ten="x" * 51), thu_muc))
    assert any("handle" in x for x in tl.kiem_ho_so(dict(hs, handle="@a b"), thu_muc))
    assert any("handle" in x for x in tl.kiem_ho_so(dict(hs, handle="@" + "a" * 31), thu_muc))
    assert any("câu đầu" in x for x in tl.kiem_ho_so(dict(hs, tu_khoa_chinh="宇宙"), thu_muc))
    assert any("thiếu logo" in x for x in tl.kiem_ho_so({k: v for k, v in hs.items() if k != "logo"}, thu_muc))
    assert any("danh_muc" in x for x in tl.kiem_ho_so(dict(hs, mac_dinh_tai_len={"ngon_ngu": "ja", "danh_muc": "xxx"}), thu_muc))
    assert len(hs["mo_ta"]) <= tl.GIOI_HAN_MO_TA


def test_kich_thuoc_anh_sai_bi_bao(goc_tam):
    hs = tl.tao("TLX-A", str(goc_tam), log=lambda s: None)
    thu_muc = Path(tl.thu_muc_thiet_lap("TLX-A", str(goc_tam)))
    _anh(thu_muc / "logo.png", (640, 640))
    assert any("ảnh logo 640×640" in x for x in tl.kiem_ho_so(hs, str(thu_muc)))


def test_vung_an_toan_banner_o_giua_va_chu_nam_gon_trong_vung(tmp_path):
    assert tl.vung_an_toan() == (507, 508, 2053, 931)
    nen = _anh(tmp_path / "nen.png", (1600, 900), (20, 20, 20))
    dich = tmp_path / "b.png"
    tl.anh_banner_tu_nguon(str(nen), str(dich), ["凪の心理学", "波立たない心で、自分のペースを生きる。", "2日に1本・朝7時更新"])
    with Image.open(dich) as b:
        assert b.size == (2560, 1440)
        goc = Image.new("RGB", b.size, (20, 20, 20))
        hop = ImageChops.difference(b.convert("RGB"), goc).getbbox()
    x0, y0, x1, y1 = tl.vung_an_toan()
    assert hop is not None and hop[0] >= x0 and hop[1] >= y0 and hop[2] <= x1 and hop[3] <= y1, hop


def test_hinh_mo_tron_nen_trong(tmp_path):
    lg = _anh(tmp_path / "l.png", (800, 800), (200, 30, 30))
    d = tmp_path / "hm.png"
    tl.anh_hinh_mo_tu_logo(str(lg), str(d))
    with Image.open(d) as im:
        assert im.size == (150, 150) and im.mode == "RGBA"
        assert im.getpixel((0, 0))[3] == 0 and im.getpixel((75, 75))[3] == 255


def test_tu_khoa_chuoi_va_alias():
    assert tl.tu_khoa_chuoi(["a", " b ", ""]) == "a, b" and tl.tu_khoa_chuoi("a、b, c") == "a, b, c"
    assert "Giáo dục" in tl.ten_danh_muc("education") and "Tiếng Nhật" in tl.ten_ngon_ngu("ja") and "Nhật Bản" in tl.ten_quoc_gia("JP")
    assert tl.ten_danh_muc("khong-co") == ()


def test_ban_nhap_chuan_bi_khi_chua_vao_channel(tmp_path):
    (tmp_path / "workspace" / "chuan-bi-TLZ" / "CHANNEL" / "TLZ").mkdir(parents=True)
    assert "chuan-bi-TLZ" in tl.thu_muc_thiet_lap("TLZ", str(tmp_path))
    (tmp_path / "CHANNEL" / "TLZ").mkdir(parents=True)
    assert "chuan-bi" not in tl.thu_muc_thiet_lap("TLZ", str(tmp_path))


def test_hom_nay_4_kenh_moi_that_su_doc_duoc_tu_bo_san():
    """Bộ thật trong kho: 4 kênh mới đọc ra đủ tên/handle/mô tả/từ khoá/danh sách phát."""
    for k in ("TL4-T7-K2", "TL5-T7", "TL6-T7", "TL6-T7-K2"):
        b = tl.doc_bo_san(k, str(GOC))
        if not b:
            pytest.skip("kho này không có bộ thiết lập sẵn")
        assert b["ten"] and tl.handle_hop_le(b["handle"]) and len(b["mo_ta"]) >= tl.MO_TA_TOI_THIEU
        assert len(b["danh_sach_phat"]) == 5 and len(tl.tu_khoa_chuoi(b["tu_khoa"])) <= tl.GIOI_HAN_TU_KHOA


# ═══════════════════ PHẦN 2: SO KHÁC BIỆT ════════════════════════════════════
HS = {"ten": "年輪の心理学", "handle": "@nenrin-shinri", "mo_ta": "一行目。\n\n二行目。", "tu_khoa": ["心理学", "老後"],
      "quoc_gia": "JP", "logo": "logo.png", "banner": "banner.png", "hinh_mo": "hinh-mo.png",
      "mac_dinh_tai_len": {"ngon_ngu": "ja", "danh_muc": "education", "the": ["心理学", "老後"]},
      "danh_sach_phat": [{"ten": "A", "mo_ta": ""}, {"ten": "B", "mo_ta": ""}]}
HASH = {"logo": "h1", "banner": "h2", "hinh_mo": "h3"}


def ht_dung():
    return {"ngon_ngu_vi": True, "ten": "年輪の心理学", "handle": "nenrin-shinri", "mo_ta": "一行目。\n二行目。  ", "tu_khoa": ["老後", "心理学"],
            "quoc_gia": "Nhật Bản", "anh": {"logo": True, "banner": True, "hinh_mo": True},
            "mac_dinh": {"ngon_ngu_video": "Tiếng Nhật", "ngon_ngu_mo_ta": "Tiếng Nhật", "danh_muc": "Giáo dục", "the": ["老後", "心理学"]},
            "danh_sach_phat": ["A", "B", "C"]}


def so_da_dat_anh():
    so = t.so_moi("K")
    so["hash_anh"] = dict(HASH)
    for m in ("logo", "banner", "hinh_mo"):
        so["muc"][m] = {"tt": "dat"}
    return so


def test_ngon_ngu_studio():
    assert t.la_tieng_viet("vi-VN", "")
    assert not t.la_tieng_viet("ko-KR", "채널 대시보드 콘텐츠 분석")
    assert t.la_tieng_viet("", "Bảng điều khiển của kênh Nội dung Số liệu phân tích")
    assert not t.la_tieng_viet("ko-KR", "Nội dung")           # 1 chữ không đủ
    kh = t.khac_biet(HS, dict(ht_dung(), ngon_ngu_vi=False), so_da_dat_anh(), HASH)
    assert kh["ngon_ngu"]["khac"] is True
    assert t.khac_biet(HS, {k: v for k, v in ht_dung().items() if k != "ngon_ngu_vi"}, so_da_dat_anh(), HASH)["ngon_ngu"]["khac"] is None
    assert t.MUC[0] == "ngon_ngu" and "ngon_ngu" in t.TEN_MUC


def test_khac_biet_tat_ca_dung_thi_khong_sua_gi():
    kh = t.khac_biet(HS, ht_dung(), so_da_dat_anh(), HASH)
    assert {m: x["khac"] for m, x in kh.items()} == {m: False for m in t.MUC}


def test_khac_biet_chi_danh_dau_muc_khac():
    ht = ht_dung()
    ht["ten"] = "心理のものさし"
    ht["mo_ta"] = "cũ"
    ht["tu_khoa"] = ["心理学"]
    ht["danh_sach_phat"] = ["A"]
    ht["mac_dinh"]["danh_muc"] = "Không"
    kh = t.khac_biet(HS, ht, so_da_dat_anh(), HASH)
    khac = {m for m, x in kh.items() if x["khac"]}
    assert khac == {"ten", "mo_ta", "tu_khoa", "danh_sach_phat", "mac_dinh"}
    assert "danh mục" in kh["mac_dinh"]["ghi"] and kh["danh_sach_phat"]["ghi"].endswith("B")


def test_khac_biet_anh_chi_dung_khi_so_ghi_dung_tep_va_studio_co_anh():
    so = so_da_dat_anh()
    assert t.khac_biet(HS, ht_dung(), so, HASH)["banner"]["khac"] is False
    assert t.khac_biet(HS, ht_dung(), so, dict(HASH, banner="hX"))["banner"]["khac"] is True      # tệp đổi
    assert t.khac_biet(HS, ht_dung(), t.so_moi("K"), HASH)["logo"]["khac"] is True                 # chưa có sổ
    ht = ht_dung()
    ht["anh"]["banner"] = False
    assert t.khac_biet(HS, ht, so, HASH)["banner"]["khac"] is True                                 # Studio mất ảnh


def test_khac_biet_chua_doc_duoc_thi_none_khong_bi_coi_la_dung():
    kh = t.khac_biet(HS, {}, t.so_moi("K"), HASH)
    assert all(x["khac"] is None for x in kh.values())


def test_khac_biet_handle_that_la_bien_the():
    so = so_da_dat_anh()
    so["handle_that"] = "@nenrin-shinri-jp"
    ht = ht_dung()
    assert t.khac_biet(HS, ht, so, HASH)["handle"]["khac"] is True
    ht["handle"] = "nenrin-shinri-jp"
    assert t.khac_biet(HS, ht, so, HASH)["handle"]["khac"] is False


def test_mo_ta_lech_dong_trong_khong_tinh():
    assert t.mo_ta_giong("a\n\n\nb", "a\nb ") and not t.mo_ta_giong("a\nb", "a\nc")


# ═══════════════════ LUẬT ĐỔI TÊN / HANDLE ═══════════════════════════════════
NOW = time.mktime((2026, 10, 3, 12, 0, 0, 0, 0, -1))


def test_khong_doi_khi_giong_va_khong_ton_luot():
    so = t.so_moi("K")
    assert t.quyet_doi(so, "ten", "年輪の心理学", " 年輪の心理学 ", NOW)[0] == "giong"
    assert t.quyet_doi(so, "handle", "@Nenrin-Shinri", "nenrin-shinri", NOW)[0] == "giong"
    assert so["ngay_doi"]["ten"] == []


def test_doi_khi_khac_ghi_ngay_va_het_luot_sau_2_lan_trong_14_ngay():
    so = t.so_moi("K")
    assert t.quyet_doi(so, "ten", "cũ", "mới", NOW)[0] == "doi"
    t.ghi_doi(so, "ten", NOW)
    assert t.quyet_doi(so, "ten", "mới", "mới hơn", NOW + 3600)[0] == "doi"        # lượt thứ 2 còn
    t.ghi_doi(so, "ten", NOW + 3600)
    v, ly = t.quyet_doi(so, "ten", "mới hơn", "nữa", NOW + 7200)
    assert v == "cho" and "mở lại" in ly
    assert t.quyet_doi(so, "ten", "mới hơn", "nữa", NOW + 15 * 86400)[0] == "doi"  # qua 14 ngày
    assert t.quyet_doi(so, "handle", "a", "b", NOW + 7200)[0] == "doi"             # handle tính RIÊNG


def test_studio_tu_choi_thi_khong_thu_lai_cung_gia_tri():
    so = t.so_moi("K")
    t.ghi_tu_choi(so, "ten", "mới", "Studio từ chối", NOW)
    v, ly = t.quyet_doi(so, "ten", "cũ", "mới", NOW + 60)
    assert v == "tu_choi" and "không thử lại" in ly
    assert t.quyet_doi(so, "ten", "cũ", "giá trị khác", NOW + 60)[0] == "doi"      # giá trị khác thì được


def test_bien_the_handle_toi_da_3_va_hop_le():
    bt = t.bien_the_handle("@nagi-shinri", "ja")
    assert bt[0] == "nagi-shinri" and bt[1] == "nagi-shinri-jp" and len(bt) == 4
    assert len(set(x.lower() for x in bt)) == 4 and all(tl.handle_hop_le(x) for x in bt)
    dai = t.bien_the_handle("a" * 30, "ja")
    assert all(len(x) <= 30 for x in dai) and len(dai) <= 4


# ═══════════════════ TRẠNG THÁI / SỔ ═════════════════════════════════════════
def test_du_muc_dat_thi_xong():
    so = t.so_moi("K")
    assert t.tinh_trang(so)[0] == "dang_lam"
    for m in t.MUC:
        t.dat_muc(so, m, "x", NOW)
    assert t.tinh_trang(so)[0] == "xong"
    so["muc"]["banner"] = {"tt": "hong", "ly_do": "x"}
    assert t.tinh_trang(so)[0] == "hong"
    t.hong_muc(so, "ten", "Studio từ chối", tt="can_nguoi")
    tt, ly = t.tinh_trang(so)
    assert tt == "can_nguoi" and "tên kênh" in ly                                  # can_nguoi nặng hơn hong


def test_so_luu_doc_lai_va_chiu_so_hong(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "THU_MUC_SO", str(tmp_path))
    so = t.so_moi("K")
    t.dat_muc(so, "ten", "A", NOW)
    t.luu_so(so)
    assert t.doc_so("K")["muc"]["ten"]["tt"] == "dat" and (tmp_path / "K.md").is_file()
    (tmp_path / "K.json").write_text("{hỏng", encoding="utf-8")
    assert t.doc_so("K")["muc"]["ten"]["tt"] == "chua"                              # sổ hỏng → sổ mới, không ném
    (tmp_path / "K.json").write_text(json.dumps({"kenh": "K", "muc": {"ten": {"tt": "dat"}}}), encoding="utf-8")
    so2 = t.doc_so("K")
    assert set(so2["muc"]) == set(t.MUC) and so2["ngay_doi"]["handle"] == []         # điền khoá thiếu


def test_dang_dung_may_thu_khong_ghi_so(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "THU_MUC_SO", str(tmp_path))
    monkeypatch.setattr(t, "_KHONG_GHI_SO", True)
    t.luu_so(t.so_moi("K"))
    assert not list(tmp_path.glob("K.*"))


# ═══════════════════ KHUNG CẤM / SỐ LẦN / NHƯỜNG ═════════════════════════════
def luc(gio, phut=0, ngay=3):
    return time.mktime((2026, 10, ngay, gio, phut, 0, 0, 0, -1))


@pytest.mark.parametrize("gio,phut,cam", [(1, 59, False), (2, 0, True), (6, 59, True), (7, 0, False), (23, 0, False)])
def test_khung_cam_02_07(gio, phut, cam):
    assert (t.quyet_dinh(t.so_moi("K"), luc(gio, phut))[0] is False) is cam


def test_toi_da_2_phien_moi_ngay_va_hoan_khong_tinh():
    so = t.so_moi("K")
    so["phien"] = [{"ngay": "2026-10-03", "ket_qua": "hoãn: Chrome đang chạy"}]
    assert t.quyet_dinh(so, luc(10))[0] is True                                     # phiên hoãn không tính
    so["phien"] += [{"ngay": "2026-10-03", "ket_qua": "xong lượt"}, {"ngay": "2026-10-03", "ket_qua": "lỗi: x"}]
    ok, ly = t.quyet_dinh(so, luc(10))
    assert ok is False and "2 phiên" in ly
    assert t.quyet_dinh(so, luc(10, ngay=4))[0] is True                              # hôm sau lại được


def test_can_nguoi_va_xong_khong_chay_lai_nghi_sau_hong():
    so = t.so_moi("K")
    so["trang_thai"], so["ly_do"] = "can_nguoi", "CAPTCHA"
    ok, ly = t.quyet_dinh(so, luc(10))
    assert ok is False and "CAPTCHA" in ly
    so["trang_thai"] = "xong"
    assert t.quyet_dinh(so, luc(10)) == (False, "đã xong")
    so["trang_thai"], so["nghi_den_luc"] = "hong", luc(10, 30)
    assert t.quyet_dinh(so, luc(10, 0))[0] is False and t.quyet_dinh(so, luc(11, 0))[0] is True


# ═══════════════════ CHẶN: XÁC MINH / CAPTCHA / ĐĂNG NHẬP ════════════════════
@pytest.mark.parametrize("url,hop,trang,mong", [
    ("https://studio.youtube.com/channel/UC1/editing/profile", "", "Tùy chỉnh kênh Hồ sơ", ""),
    ("https://accounts.google.com/v3/signin/identifier", "", "", "dang_xuat"),
    ("https://accounts.google.com/signin/v2/challenge/pwd", "", "", "dang_xuat"),
    ("https://www.google.com/recaptcha/api2/", "", "", "captcha"),
    ("https://consent.youtube.com/m?continue=", "", "", "dong_y"),
    ("https://studio.youtube.com/channel/UC1", "Xác minh danh tính của bạn để tiếp tục", "", "xac_minh"),
    ("https://studio.youtube.com/channel/UC1", "Verify it's you", "", "xac_minh"),
    ("https://studio.youtube.com/channel/UC1", "本人確認が必要です", "", "xac_minh"),
    ("https://studio.youtube.com/channel/UC1", "Xác minh số điện thoại của bạn", "", "dien_thoai"),
    ("https://studio.youtube.com/channel/UC1", "Please confirm you are not a robot (CAPTCHA)", "", "captcha"),
    ("https://studio.youtube.com/channel/UC1", "", "Điều kiện sử dụng tính năng: xác minh số điện thoại", ""),   # trang Studio: chữ cả trang không tính
    ("https://www.youtube.com/", "", "Vui lòng xác minh số điện thoại", "dien_thoai"),
])
def test_phat_hien_chan(url, hop, trang, mong):
    assert t.phat_hien_chan(url, hop, trang) == mong


# ═══════════════════ kenh.yaml: BẬT / TẮT / TÊN ══════════════════════════════
def test_cong_tac_thiet_lap_kenh_bat_tat_va_khong_dung_kenh_khac(tmp_path):
    for k, v in (("A", "true"), ("B", "false"), ("C", "")):
        d = tmp_path / "CHANNEL" / k
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text('ten: "(tên tạm) — tâm lý"\n' + ("thiet_lap_kenh: %s\n" % v if v else "") + "nuoi_trang_chu: true\n", encoding="utf-8")
    nhap = tmp_path / "workspace" / "chuan-bi-D" / "CHANNEL" / "D"
    nhap.mkdir(parents=True)
    (nhap / "kenh.yaml").write_text("thiet_lap_kenh: true\n", encoding="utf-8")
    assert t.cac_kenh_bat(str(tmp_path)) == ["A", "D"]
    assert t.tat_thiet_lap("A", str(tmp_path)) and not t.thiet_lap_bat("A", str(tmp_path))
    assert "nuoi_trang_chu: true" in (tmp_path / "CHANNEL" / "A" / "kenh.yaml").read_text(encoding="utf-8")   # chỉ đổi đúng dòng
    assert t.tat_thiet_lap("B", str(tmp_path))                                                              # đã false: không lỗi
    assert t.cac_kenh_bat(str(tmp_path)) == ["D"]


def test_ghi_ten_yaml_chi_thay_ten_tam():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td) / "CHANNEL" / "A"
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text('ten: "(tên tạm) — tâm lý, người 65+"\nx: 1\n', encoding="utf-8")
        assert t.ghi_ten_yaml("A", "年輪の心理学", td)
        nd = (d / "kenh.yaml").read_text(encoding="utf-8")
        assert 'ten: "年輪の心理学 — tâm lý, người 65+"' in nd and "x: 1" in nd
        assert n.ten_kenh_cua_minh(td) == {"年輪の心理学"}                          # nuôi trang chủ cắt phần trước " — "
        assert not t.ghi_ten_yaml("A", "Tên khác", td)                              # đã là tên thật: không đè


# ═══════════════════ KÊNH ĐẾN LƯỢT (agent) ═══════════════════════════════════
@pytest.fixture()
def kho(tmp_path, monkeypatch):
    goc = tmp_path / "MyTool"
    for k in ("A", "B", "C"):
        d = goc / "CHANNEL" / k
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text("thiet_lap_kenh: true\n", encoding="utf-8")
        (tmp_path / k).mkdir()
        (tmp_path / k / (k + ".exe")).write_text("x")
    monkeypatch.setattr(t, "THU_MUC_SO", str(tmp_path / "so"))
    monkeypatch.setattr(t, "THU_MUC_KHOA_RIENG", str(tmp_path / "so"))
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path / "nuoi"))
    monkeypatch.setattr(n, "cac_kenh_dang_nuoi", lambda thu_muc=None: [])
    return goc


def test_kenh_den_luot_tuan_tu_mot_kenh_mot_luc(kho):
    ra, ly = t.kenh_den_luot(luc(10), (), str(kho), ram=16.0, nang_ban=False)
    assert ra == ["A"] and ly["B"].startswith("xếp hàng") and ly["C"].startswith("xếp hàng")
    ra, ly = t.kenh_den_luot(luc(10), {"A"}, str(kho), ram=16.0, nang_ban=False)      # A đang chạy: không mở thêm
    assert ra == [] and "tuần tự" in ly["B"] and ly["A"] == "đang thiết lập"


def test_kenh_den_luot_bo_qua_xong_can_nguoi_khung_cam_nuoi_va_thieu_chrome(kho, monkeypatch, tmp_path):
    so = t.so_moi("A")
    so["trang_thai"] = "xong"
    t.luu_so(so)
    so = t.so_moi("B")
    so["trang_thai"], so["ly_do"] = "can_nguoi", "CAPTCHA"
    t.luu_so(so)
    ra, ly = t.kenh_den_luot(luc(10), (), str(kho), ram=16.0, nang_ban=False)
    assert ra == ["C"] and ly["A"] == "đã xong" and "CAPTCHA" in ly["B"]
    assert t.kenh_den_luot(luc(3), (), str(kho), ram=16.0, nang_ban=False)[0] == []                    # khung cấm
    (tmp_path / "C" / "C.exe").unlink()
    ra, ly = t.kenh_den_luot(luc(10), (), str(kho), ram=16.0, nang_ban=False)
    assert ra == [] and "Chrome Portable" in ly["C"]
    (tmp_path / "C" / "C.exe").write_text("x")
    monkeypatch.setattr(n, "chu_khoa", lambda k, thu_muc=None: 4242 if (k == "C" and thu_muc is None) else 0)             # nuôi đang giữ Chrome C
    assert "nuôi" in t.kenh_den_luot(luc(10), (), str(kho), ram=16.0, nang_ban=False)[1]["C"]


def test_kenh_den_luot_khong_cho_khe_nang_nhung_nhuong_ram(kho):
    # 04/10: thiết lập kênh không tốn CPU → KHÔNG chờ khe nang (7 kênh sản xuất thì khe nang bận gần cả ngày)
    assert t.kenh_den_luot(luc(10), (), str(kho), ram=16.0, nang_ban=True)[0] != []
    ra, ly = t.kenh_den_luot(luc(10), (), str(kho), ram=1.0, nang_ban=False)
    assert ra == [] and any("RAM" in v or "ram" in v for v in ly.values())


def test_khoa_chung_voi_nuoi_trang_chu_khong_hai_tien_trinh_cung_mo_chrome(tmp_path, monkeypatch):
    monkeypatch.setattr(n, "THU_MUC_SO", str(tmp_path))
    assert n.giu_khoa("K") is True
    assert n.giu_khoa("K") is False                       # thiết lập (hoặc nuôi) thứ hai không giành được
    n.nha_khoa("K")
    assert n.giu_khoa("K") is True


def test_khong_dung_chrome_tl1_den_tl4_va_khong_bat_cho_kenh_dang_chay():
    """Kho thật: TL1–TL4 KHÔNG được bật thiết lập (kênh đang chạy, đã thiết lập)."""
    for k in ("TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7"):
        d = n.duong_kenh_yaml(k, str(GOC))
        if d:
            assert not t.thiet_lap_bat(k, str(GOC)), k


# ═══════════════════ MÓC Ở AGENT ═════════════════════════════════════════════
def _nap_agent(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("vm_agent_tlk", VM / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "GOC", str(tmp_path))
    logs = []
    monkeypatch.setattr(mod, "ghi", logs.append)
    mod._THIET_LAP_KENH.update(luc=0.0, con={}, ly={})
    return mod, logs


class _Con:
    def __init__(self, ma=None):
        self.returncode = ma

    def poll(self):
        return self.returncode


def test_agent_mo_tien_trinh_con_thiet_lap_ghi_ly_do_khi_doi(tmp_path, monkeypatch):
    mod, logs = _nap_agent(tmp_path, monkeypatch)
    ly = {"B": "đã chạy 2 phiên hôm nay"}
    monkeypatch.setattr(t, "kenh_den_luot", lambda tg, dang=(), goc=None, **k: (["A"] if "A" not in dang else [], dict(ly)))
    monkeypatch.setattr(mod, "van_ipv4_mo", lambda: False)
    lenh = []
    mo = lambda cmd, **kw: (lenh.append(cmd), _Con())[1]
    assert mod.chay_thiet_lap_kenh(100000.0, mo_con=mo) == 1
    assert lenh[0][-2:] == ["--kenh", "A"] and lenh[0][1].endswith("thiet_lap_kenh_dom.py")
    assert sum("bỏ qua" in x and "kênh B" in x for x in logs) == 1
    assert mod.chay_thiet_lap_kenh(100000.0 + 300, mo_con=mo) == 1                      # chưa tới 10 phút: im lặng
    ly["B"] = "đã chạy 1 phiên hôm nay"                                                  # chỉ đổi số: KHÔNG ghi lại
    mod.chay_thiet_lap_kenh(100000.0 + 700, mo_con=mo)
    assert sum("kênh B" in x and "bỏ qua" in x for x in logs) == 1
    assert len(lenh) == 1                                                                # đang chạy thì không mở thêm con


def test_agent_con_xong_duoc_don_va_van_ipv4_hoan(tmp_path, monkeypatch):
    mod, logs = _nap_agent(tmp_path, monkeypatch)
    monkeypatch.setattr(t, "kenh_den_luot", lambda tg, dang=(), goc=None, **k: (["A"], {}))
    monkeypatch.setattr(mod, "van_ipv4_mo", lambda: True)
    assert mod.chay_thiet_lap_kenh(100000.0, mo_con=lambda *a, **k: 1 / 0) == 0
    assert any("van IPv4" in x for x in logs)
    mod._THIET_LAP_KENH["con"]["A"] = _Con(0)
    mod.chay_thiet_lap_kenh(100001.0)
    assert not mod._THIET_LAP_KENH["con"] and any("xong (mã 0)" in x for x in logs)


def test_agent_goi_thiet_lap_trong_vong_lap_phu_va_nhuong_cho_viec_dang():
    nguon = (VM / "agent.py").read_text(encoding="utf-8")
    assert "chay_thiet_lap_kenh()" in nguon and "chay_nuoi_trang_chu()" in nguon
    assert nguon.index("chay_nuoi_trang_chu()") < nguon.index("chay_thiet_lap_kenh()")      # cùng chỗ, sau nuôi
    # việc đăng nhường cho thiết lập qua cùng khoá `<kênh>.khoa` của nuôi (`_nhuong_kenh_nuoi`)
    assert 'kenh + ".khoa"' in nguon and "_nhuong_kenh_nuoi" in nguon


# ═══════════════════ KHUÔN KÊNH MỚI ══════════════════════════════════════════
def test_khuon_kenh_mau_mac_dinh_bat_thiet_lap_va_khong_co_chu_thich_cuoi_dong():
    d = GOC / "CHANNEL" / "_KHUON" / "kenh-mau" / "kenh.yaml"
    nd = d.read_text(encoding="utf-8")
    assert any(x.strip() == "thiet_lap_kenh: true" for x in nd.splitlines())
    for x in nd.splitlines():
        if x.startswith("thiet_lap_kenh:"):
            assert "#" not in x                                                            # trình đọc không bỏ chú thích cuối dòng


def test_kenh_moi_dung_tu_khuon_co_thiet_lap_kenh_true():
    """`core.khoi_tao_ngach.buoc_kenh` chép khuôn → kenh.yaml kênh mới mang `thiet_lap_kenh: true`."""
    from core import khoi_tao_ngach as kt  # noqa: PLC0415
    nd = (GOC / "CHANNEL" / "_KHUON" / "kenh-mau" / kt.TEP_KENH).read_text(encoding="utf-8")
    nd2 = kt._dat_khoa(nd, "ma", "TLQ")
    assert "thiet_lap_kenh: true" in nd2
