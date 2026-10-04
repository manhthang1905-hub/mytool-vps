"""Kỹ năng MỞ KÊNH (`core/mo_kenh.py`, 04/10/2026): luật số kênh, đặt mã, chọn giọng, `chuan-bi` dựng đủ tệp, `kich-hoat`
đợi thiết lập xong mới bật `tu_chay`. Mọi thứ trong tmp; LLM + ảnh + Chrome + mạng thay bằng hàm giả."""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

GOC_REPO = Path(__file__).resolve().parent.parent
if str(GOC_REPO) not in sys.path:
    sys.path.append(str(GOC_REPO))

from core import mo_kenh as mk  # noqa: E402

NOW = dt.datetime(2026, 10, 4, 14, 0)
LUAT_ANH_EM = ("GÓC CỦA KÊNH: ĐỌC KẺ ĐỘC HẠI — đặc điểm kẻ xấu, kẻ ghen tị, kẻ thao túng | ĐỊNH HƯỚNG: nhận ra và tự vệ, không dạy thao túng | "
               "Trọng tâm là người tử tế bị lợi dụng thì lệch góc | Ưu tiên nguồn 12–32 phút, còn tăng view/ngày.")
LUAT_MOI = ("GÓC CỦA KÊNH: CHÍNH NGƯỜI TỬ TẾ — chịu đựng lâu, bị coi thường, giới hạn của sự nhẫn nhịn, lặng lẽ giữ khoảng cách và thôi cho đi, "
            "ưu tiên cụm cắt duyên và tự trọng | ĐỊNH HƯỚNG BẮT BUỘC: giúp người xem nhận ra mình bị lợi dụng và tự vệ, không dạy thao túng hay trả thù, "
            "không chẩn đoán bệnh | Trọng tâm là đọc kẻ độc hại thì lệch góc, thuộc kênh anh em | Ưu tiên nguồn 12–32 phút, còn tăng view mỗi ngày.")


def _yaml(**kv):
    return "\n".join("{0}: {1}".format(k, v if isinstance(v, (bool, int)) and not isinstance(v, str) else '"{0}"'.format(v)) for k, v in kv.items()) + "\n"


def _kenh(goc, ma, **kv):
    d = Path(goc) / "CHANNEL" / ma
    d.mkdir(parents=True, exist_ok=True)
    kv.setdefault("ma", ma)
    (d / "kenh.yaml").write_text("# ghi chú cũ của kênh gốc\n" + _yaml(**kv).replace("true\n", "true\n"), encoding="utf-8")
    return d


def _thi_truong(goc, tep: dict, ngay="2026-10-01"):
    d = Path(goc) / "workspace" / "chuan-bi-kenh-moi"
    d.mkdir(parents=True, exist_ok=True)
    (d / "thi-truong.json").write_text(json.dumps({"ngay": ngay, "nguon": "thử", "tep": tep}), encoding="utf-8")


@pytest.fixture()
def goc(tmp_path):
    g = tmp_path / "MyTool"
    g.mkdir()
    return str(g)


# ── 1) mã kênh ──────────────────────────────────────────────────────────────────
def test_phan_ma_va_ma_nhan_ban():
    assert mk.phan_ma("TL4-T7-K2") == {"goc": "TL4-T7", "k": 2, "tien": "TL", "so": 4, "hau": "T7"}
    assert mk.phan_ma("TL4-T7-v2")["goc"] == "TL4-T7" and mk.phan_ma("TL4-T7-v2")["k"] == 1
    cac = ["TL4-T7", "TL4-T7-v2", "TL4-T7-K2", "TL6-T7"]
    assert mk.ma_nhan_ban(cac, "TL4-T7") == "TL4-T7-K3"          # K2 đã có → K3
    assert mk.ma_nhan_ban(cac, "TL6-T7") == "TL6-T7-K2"
    assert mk.ma_nhan_ban(cac, "TL4-T7-K2") == "TL4-T7-K3"       # gốc là bản nhân vẫn đếm theo gốc
    assert mk.ma_nhan_ban(["TL6-T7"], "TL6-T7", ton_tai=lambda m: m == "TL6-T7-K2") == "TL6-T7-K3"


def test_ma_tep_moi_danh_so_tiep():
    cac = ["TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7", "TL4-T7-v2", "TL4-T7-K2", "TL5-T7", "TL6-T7", "TL6-T7-K2"]
    assert mk.ma_tep_moi(cac) == "TL7-T7"
    assert mk.ma_tep_moi(cac, ton_tai=lambda m: m == "TL7-T7") == "TL8-T7"
    assert mk.ma_tep_moi(["K1"]) == "K2"
    assert mk.ma_tep_moi([]) == "K1"                              # VPS mới, chưa mẫu mã


# ── 2) luật số kênh + điều kiện nhân bản ────────────────────────────────────────────
def _dung_thi_truong(goc, ngay="2026-10-01", thang=2):
    _kenh(goc, "TL6-T7", nhom="g", tep="t8", ngon_ngu="ja")
    _kenh(goc, "TL2-T7", nhom="g", tep="t4", ngon_ngu="ja")
    _thi_truong(goc, {
        "8": {"ten": "Tâm lý đen", "nguon_no_thang": 47.0, "trang_chu": "len", "he_so_trang_chu": 1.44},
        "4": {"ten": "Trung niên", "nguon_no_thang": 26.0, "trang_chu": "giam", "he_so_trang_chu": 0.68},
        "9": {"ten": "Tệp mới chưa kênh", "nguon_no_thang": 31.0, "trang_chu": "on", "he_so_trang_chu": 1.02},
        "5": {"ten": "Nhỏ", "nguon_no_thang": 14.0, "trang_chu": "len", "he_so_trang_chu": 1.3},
    }, ngay=ngay)
    return [{"ma": "TL6-T7", "thang_tong": thang}, {"ma": "TL2-T7", "thang_tong": 5}]


def _map_tep(monkeypatch):
    """Khoá tệp trong thi-truong.json → tên tệp trong kenh.yaml (bản thật dùng `tuyen_noi_dung.ma_tep`)."""
    import core.tuyen_noi_dung as tn

    monkeypatch.setattr(tn, "ma_tep", lambda t, goc=None: {"8": "t8", "4": "t4", "9": "t9", "5": "t5"}.get(str(t), str(t) if t else ""))


def test_luat_so_kenh_va_nhan_ban(goc, monkeypatch):
    _map_tep(monkeypatch)
    bang = _dung_thi_truong(goc, thang=2)
    kq = mk.de_xuat(goc, bang=bang, bay_gio=NOW)
    theo = {t["tep"]: t for t in kq["tep"]}
    # tệp 8: 47 ÷ 15 = 3 tối đa, đang có 1, kênh đầu thắng 2 ≥ 2 → NHÂN BẢN TL6-T7-K2
    t8 = theo["t8"]
    assert t8["toi_da"] == 3 and t8["mo"] and t8["loai"] == "nhan_ban" and t8["ma_de_xuat"] == "TL6-T7-K2" and t8["kenh_goc"] == "TL6-T7"
    assert "47,0" in t8["ly_do"] and "= tối đa 3" in t8["ly_do"] and "ĐỀ XUẤT MỞ" in t8["ly_do"]
    # tệp 4: trang chủ GIẢM → tối đa 0 dù nguồn 26
    assert theo["t4"]["toi_da"] == 0 and not theo["t4"]["mo"]
    # tệp 5: nguồn 14 < 15 → 0
    assert theo["t5"]["toi_da"] == 0 and not theo["t5"]["mo"]
    # tệp 9: chưa có kênh, 31 ÷ 15 = 2 → TỆP MỚI, đánh số tiếp
    t9 = theo["t9"]
    assert t9["mo"] and t9["loai"] == "tep_moi" and t9["ma_de_xuat"] == "TL7-T7" and t9["nhom"] == "g"
    assert [t["tep"] for t in kq["de_xuat"]] == ["t8", "t9"] and kq["de_xuat"][0]["thu_tu"] == 1       # lớn hơn trước
    assert "NÊN MỞ" in kq["tom_tat"]


def test_nhan_ban_chi_khi_kenh_dau_thang_2(goc, monkeypatch):
    _map_tep(monkeypatch)
    kq = mk.de_xuat(goc, bang=_dung_thi_truong(goc, thang=1), bay_gio=NOW)
    t8 = {t["tep"]: t for t in kq["tep"]}["t8"]
    assert not t8["mo"] and t8["thang_kenh_dau"] == 1 and "chờ kênh đầu thắng" in t8["ly_do"]
    assert "t8" not in [d["tep"] for d in kq["de_xuat"]]


def test_so_lieu_cu_hoac_thieu_khong_de_xuat(goc, monkeypatch):
    _map_tep(monkeypatch)
    kq = mk.de_xuat(goc, bang=_dung_thi_truong(goc, ngay="2026-08-01", thang=9), bay_gio=NOW)
    assert kq["de_xuat"] == [] and any("cũ quá" in c for c in kq["canh_bao"])
    g2 = os.path.join(os.path.dirname(goc), "trong")
    os.makedirs(g2)
    kq = mk.de_xuat(g2, bang=[], bay_gio=NOW)
    assert kq["de_xuat"] == [] and any("chưa có" in c for c in kq["canh_bao"])


def test_dang_ky_mot_kenh_mot_lan(goc, monkeypatch):
    _map_tep(monkeypatch)
    kq = mk.de_xuat(goc, bang=_dung_thi_truong(goc), bay_gio=NOW)
    assert mk.dang_ky(goc, kq, NOW) == "TL6-T7-K2"
    assert mk.dang_mo(goc) == ["TL6-T7-K2"]
    assert mk.dang_ky(goc, kq, NOW) == ""                          # đang mở một kênh → không thêm kênh thứ hai
    st = mk.doc_trang_thai(goc)
    assert st["kenh"]["TL6-T7-K2"]["trang_thai"] == "de_xuat" and st["ngay_de_xuat_cuoi"] == "2026-10-04"


def test_che_do_tat_khong_dang_ky(goc, monkeypatch):
    _map_tep(monkeypatch)
    (Path(goc) / "workspace").mkdir(exist_ok=True)
    (Path(goc) / "workspace" / "cai-dat.json").write_text('{"mo_kenh": "tat"}', encoding="utf-8")
    kq = mk.de_xuat(goc, bang=_dung_thi_truong(goc), bay_gio=NOW)
    assert mk.dang_ky(goc, kq, NOW) == "" and mk.che_do(goc) == "tat" and mk.can_lam(goc, NOW) == ""


# ── 3) giọng ────────────────────────────────────────────────────────────────────────
def test_chon_giong_khong_trung_kenh_cung_tep():
    kho = [{"voice_id": "A", "ky_tu_moi_phut": 270}, {"voice_id": "B", "ky_tu_moi_phut": 273}, {"voice_id": "C", "ky_tu_moi_phut": 268}]
    assert mk.chon_giong(kho, ["A", "C"])["voice_id"] == "B"
    assert mk.chon_giong(kho, ["B"], {"A": 5, "C": 1})["voice_id"] == "C"           # ít dùng nhất trong nhóm
    assert mk.chon_giong(kho, ["A", "B", "C"]) is None                              # hết giọng khác tệp


def test_kho_giong_khoi_dau_va_gom_giong_dang_dung(goc):
    _kenh(goc, "X1", nhom="g", tep="t", voice_id="ZZZ", ky_tu_moi_phut=281)
    (Path(goc) / "CHANNEL" / "_NHOM" / "g").mkdir(parents=True)
    kho = mk.doc_kho_giong(goc, "g")
    ids = [x["voice_id"] for x in kho]
    assert ids[:3] == ["b34JylakFZPlGS0BnwyY", "GxxMAMfQkDlnqjpzjLHH", "T7yYq3WpB94yAuOXraRi"]
    assert [x["ky_tu_moi_phut"] for x in kho[:3]] == [270, 273, 268] and "ZZZ" in ids
    assert os.path.isfile(mk.duong_kho_giong(goc, "g"))                             # tạo nếu chưa có
    assert mk.doc_kho_giong(goc, "g")[3]["voice_id"] == "ZZZ"                      # đọc lại từ tệp


# ── 4) kiểm góc (số do mã) ───────────────────────────────────────────────────────────
def _goc_hop_le(**de):
    d = {"goc": "Người tử tế bị lợi dụng", "luat_chon": LUAT_MOI, "giong_van": "warm, gentle", "ten_goi_y": "やさしさの境界線",
         "danh_sach_phat_kenh": ["優しさの限界", "我慢のサイン", "断る練習", "距離の置き方", "自分を守る習慣"],
         "nhan_vat": {"default_character_prompt": "A round-faced illustrated woman in a soft green cardigan, calm warm eyes, simple shapes, full body",
                      "default_character_lock": "round face, green cardigan", "reference_lock": "The attached image IS the character.",
                      "engagement_rules": "The viewer is kind and tired."}}
    d.update(de)
    return d


def test_kiem_goc_bat_goc_trung_anh_em():
    anh_em = [{"ma": "TL6-T7", "luat_chon": LUAT_ANH_EM, "danh_sach_phat_kenh": "A | B"}]
    assert mk.kiem_goc(_goc_hop_le(), anh_em) == []
    loi = mk.kiem_goc(_goc_hop_le(luat_chon=LUAT_ANH_EM + " " + LUAT_ANH_EM), anh_em)
    assert any("giống kênh TL6-T7" in x for x in loi)
    assert any("trùng tên danh sách phát" in x for x in mk.kiem_goc(_goc_hop_le(danh_sach_phat_kenh=["A", "x1", "x2", "x3", "x4"]), anh_em))
    assert mk.do_giong_goc("abc def ghi", "abc def ghi") == 1.0 and mk.do_giong_goc("甲乙丙丁", "戊己庚辛") == 0.0
    assert mk.kiem_goc(_goc_hop_le(luat_chon="ngắn"), [])                            # quá ngắn


# ── 5) chuan-bi tạo đủ tệp ────────────────────────────────────────────────────────────
def _dung_kenh_goc(goc):
    d = _kenh(goc, "TL6-T7", nhom="g", tep="t8", ngon_ngu="ja", ten="kênh gốc", voice_id="T7yYq3WpB94yAuOXraRi", ky_tu_moi_phut=268,
              luat_chon=LUAT_ANH_EM, danh_sach_phat_kenh="A | B | C", tu_chay=True, nuoi_trang_chu=True, thiet_lap_kenh=False,
              ngon_ngu_tai_khoan_dich="ja", mau_cua_tool="true", gio_dang="20:00")
    (d / "style.yaml").write_text('style_name: "mochi"\nthumbnail_style: "winning thumbnail style"\ndefault_character_prompt: "old mochi"\n'
                                  'default_character_lock: "old lock"\nreference_lock: "old ref"\nengagement_rules: "old viewers"\n', encoding="utf-8")
    (d / "prompt").mkdir()
    (d / "prompt" / "2-viet.md").write_text("prompt viết", encoding="utf-8")
    (d / "prompt" / "cai-dat.json").write_text("{}", encoding="utf-8")
    (d / "chi-so").mkdir()
    (d / "chi-so" / "so-cua-kenh-goc.csv").write_text("x", encoding="utf-8")
    (d / "nv").mkdir()
    (d / "nv" / "nv1.png").write_bytes(b"x" * 10)
    n = Path(goc) / "CHANNEL" / "_NHOM" / "g"
    n.mkdir(parents=True)
    (n / "ngach.yaml").write_text("mo_ta_ngach: Tâm lý học tiếng Nhật\nngon_ngu_nguon: ja\nthi_truong:\n  quoc_gia: JP\n  ngon_ngu: ja\n", encoding="utf-8")
    return d


class Gia:
    def __init__(self, goi_tra):
        self.goi_tra = list(goi_tra)
        self.goi_dem = 0
        self.anh = []
        self.chrome = []
        self.handle_hoi = []

    def goi(self, loi_nhac, **kw):
        self.goi_dem += 1
        return self.goi_tra.pop(0) if len(self.goi_tra) > 1 else self.goi_tra[0]

    def tao_anh(self, prompt, dich, tham_chieu=()):
        self.anh.append(dich)
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        Path(dich).write_bytes(b"png" * 400)
        return dich

    def tao_ho_so(self, kenh, goc, **kw):
        from core import thiet_lap_kenh as tl

        hs = {"ten": "やさしさの境界線", "handle": "@yasashisa-kyokai", "mo_ta": "x" * 700, "tu_khoa": ["a", "b"], "danh_sach_phat": [{"ten": "p1"}],
              "quoc_gia": "JP", "logo": "logo.png", "banner": "banner.png", "hinh_mo": "hinh-mo.png"}
        d = tl.thu_muc_thiet_lap(kenh, goc)
        os.makedirs(d, exist_ok=True)
        for t in ("logo.png", "banner.png", "hinh-mo.png"):
            Path(d, t).write_bytes(b"i")
        tl.ghi_ho_so(kenh, hs, goc)
        return hs

    def kiem_handle(self, h):
        self.handle_hoi.append(h)
        return len(self.handle_hoi) > 1                  # lần đầu: đã có người dùng → thử biến thể

    def chep_chrome(self, goc, ma, log=print, **kw):
        self.chrome.append(ma)
        return "da_chep", "chép giả"


def _chay_chuan_bi(goc, gia, ma="TL6-T7-K2", **kw):
    hang = {"tep": "t8", "nhom": "g", "loai": "nhan_ban", "kenh_goc": "TL6-T7", "ly_do": "47,0 nguồn nổ", "ten_tep": "Tâm lý đen"}
    mk.luu_trang_thai(goc, {"kenh": {ma: dict(hang, trang_thai="de_xuat", kiem_cuoi=0, loi="")}, "ngay_de_xuat_cuoi": "2026-10-04"})
    return mk.chuan_bi(goc, ma, goi=gia.goi, tao_anh=gia.tao_anh, tao_ho_so=gia.tao_ho_so, kiem_handle=gia.kiem_handle,
                       chep_chrome=gia.chep_chrome, gieo=lambda *a, **k: None, log=lambda s: None, bay_gio=NOW, **kw)


def test_chuan_bi_tao_du_tep(goc):
    _dung_kenh_goc(goc)
    gia = Gia([json.dumps(_goc_hop_le())])
    d = _chay_chuan_bi(goc, gia)
    k = Path(goc) / "CHANNEL" / "TL6-T7-K2"
    from core.kenh import doc_yaml

    y = doc_yaml(str(k / "kenh.yaml"))
    assert y["ma"] == "TL6-T7-K2" and y["tep"] == "t8" and y["nhom"] == "g" and y["ngon_ngu"] == "ja"
    assert y["luat_chon"].startswith("GÓC CỦA KÊNH: CHÍNH NGƯỜI TỬ TẾ") and "ĐỌC KẺ ĐỘC HẠI" not in y["luat_chon"].split("|")[0]
    assert y["danh_sach_phat_kenh"].split(" | ")[0] == "優しさの限界" and len(y["danh_sach_phat_kenh"].split(" | ")) == 5
    # nhịp + công tắc: CHƯA tự chạy cho tới kich-hoat
    assert str(y["tu_chay"]).lower() == "false" and str(y["nuoi_trang_chu"]).lower() == "false" and str(y["thiet_lap_kenh"]).lower() == "false"
    assert y["gio_dang"] == "05:00" and y["nhip_dang"] == "05:00" and str(y["chu_ky_dang_ngay"]) == "1" and str(y["san_xuat_truoc_gio"]) == "24"
    assert str(y["tu_duyet"]).lower() == "true" and y["thu_muc_done"] == "DONE/TL6-T7-K2" and y["chien_luoc"] == "tu_dong"
    assert y.get("ngon_ngu_tai_khoan_dich", "") == ""                                # khoá của kênh gốc KHÔNG bị chép sang
    assert "mau_cua_tool" not in y
    # giọng: khác kênh cùng tệp (TL6-T7 dùng T7yY…), lấy từ kho với ký tự/phút đã đo
    assert y["voice_id"] != "T7yYq3WpB94yAuOXraRi" and y["voice_id"] in ("b34JylakFZPlGS0BnwyY", "GxxMAMfQkDlnqjpzjLHH")
    assert int(y["ky_tu_moi_phut"]) in (270, 273)
    # style: kiểu hình thắng giữ, khoá nhân vật viết lại
    s = (k / "style.yaml").read_text(encoding="utf-8")
    assert 'thumbnail_style: "winning thumbnail style"' in s and "round-faced illustrated woman" in s and "old mochi" not in s
    # prompt/ chỉ chép *.md; không chép số liệu của kênh gốc
    assert (k / "prompt" / "2-viet.md").is_file() and not (k / "prompt" / "cai-dat.json").exists() and not (k / "chi-so").exists()
    # ảnh nhân vật + hồ sơ + handle biến thể (handle gốc đã có người dùng) + DONE + Chrome + trạng thái
    assert (k / "nv" / "nv1.png").is_file() and gia.anh and "nv1.png" in gia.anh[0]
    hs = json.loads((k / "thiet-lap" / "ho-so.json").read_text(encoding="utf-8"))
    assert hs["handle"] == "@yasashisa-kyokai-jp" and gia.handle_hoi[:2] == ["yasashisa-kyokai", "yasashisa-kyokai-jp"]
    assert (Path(goc) / "DONE" / "TL6-T7-K2").is_dir() and gia.chrome == ["TL6-T7-K2"]
    assert d["trang_thai"] == "cho_chrome" and mk.doc_trang_thai(goc)["kenh"]["TL6-T7-K2"]["voice_id"] == y["voice_id"]
    # chạy lại: không hỏi LLM lần nữa, không đè kênh
    n_goi = gia.goi_dem
    _chay_chuan_bi(goc, gia)
    assert gia.goi_dem == n_goi


def test_chuan_bi_ngon_ngu_tai_khoan_chi_khi_da_chung_minh(goc):
    _dung_kenh_goc(goc)
    (Path(goc) / "workspace").mkdir(exist_ok=True)
    (Path(goc) / "workspace" / "cai-dat.json").write_text('{"ngon_ngu_tai_khoan_chung_minh": ["ja"]}', encoding="utf-8")
    _chay_chuan_bi(goc, Gia([json.dumps(_goc_hop_le())]))
    assert mk._kenh_yaml(goc, "TL6-T7-K2")["ngon_ngu_tai_khoan_dich"] == "ja"
    assert mk.ngon_ngu_dich_bat_cho(goc, "ja") and not mk.ngon_ngu_dich_bat_cho(goc, "vi")


def test_chuan_bi_loai_goc_trung_va_khong_dung_kenh(goc):
    _dung_kenh_goc(goc)
    trung = _goc_hop_le(luat_chon=LUAT_ANH_EM + " " + LUAT_ANH_EM)
    gia = Gia([json.dumps(trung)])
    with pytest.raises(RuntimeError, match="góc"):
        _chay_chuan_bi(goc, gia)
    assert gia.goi_dem == 2                                                       # hỏi lại một lần rồi bỏ
    assert not (Path(goc) / "CHANNEL" / "TL6-T7-K2").exists()                     # không để kênh dở dang


def test_chuan_bi_het_giong_khac_tep(goc):
    _dung_kenh_goc(goc)
    kho = Path(goc) / "CHANNEL" / "_NHOM" / "g" / "kho-giong.json"
    kho.write_text(json.dumps({"giong": [{"voice_id": "T7yYq3WpB94yAuOXraRi", "ky_tu_moi_phut": 268}]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="hết giọng"):
        _chay_chuan_bi(goc, Gia([json.dumps(_goc_hop_le())]))


def test_chuan_bi_thu_khong_ghi_gi(goc):
    _dung_kenh_goc(goc)
    hang = {"tep": "t8", "nhom": "g", "kenh_goc": "TL6-T7"}
    r = mk.chuan_bi(goc, "TL6-T7-K2", hang=hang, thu=True, log=lambda s: None)
    assert r == {"thu": True} and not (Path(goc) / "CHANNEL" / "TL6-T7-K2").exists()
    assert not (Path(goc) / "CHANNEL" / "_NHOM" / "g" / "kho-giong.json").exists()


# ── 6) kich-hoat: đợi thiết lập xong mới bật tu_chay ──────────────────────────────────────
def _san_sang_kich_hoat(goc, tmp_chrome=True):
    _dung_kenh_goc(goc)
    gia = Gia([json.dumps(_goc_hop_le())])
    _chay_chuan_bi(goc, gia)
    if tmp_chrome:
        exe = mk.thu_muc_chrome(goc, "TL6-T7-K2")
        os.makedirs(os.path.dirname(exe), exist_ok=True)
        Path(exe).write_bytes(b"MZ")
    return gia


def _yv(goc, khoa):
    return str(mk._kenh_yaml(goc, "TL6-T7-K2").get(khoa)).lower()


def test_kich_hoat_doi_dang_nhap_roi_doi_thiet_lap_xong(goc):
    _san_sang_kich_hoat(goc)
    ghep = []
    so = {"trang_thai": "dang_lam"}
    chung = dict(them_vao_vm=lambda vm, ma, chrome="": ghep.append((ma, chrome)), doc_so=lambda m: so, log=lambda s: None, bay_gio=NOW)
    # chưa đăng nhập: không đụng gì
    r = mk.kich_hoat(goc, "TL6-T7-K2", kiem_dang_nhap=lambda e: (False, "chưa thấy phiên đăng nhập"), **chung)
    assert r["trang_thai"] == "cho_chrome" and not ghep and _yv(goc, "thiet_lap_kenh") == "false" and _yv(goc, "tu_chay") == "false"
    # đã đăng nhập: ghép máy đăng + bật thiết lập kênh + nuôi trang chủ; tu_chay VẪN tắt
    r = mk.kich_hoat(goc, "TL6-T7-K2", kiem_dang_nhap=lambda e: (True, ""), **chung)
    assert r["trang_thai"] == "dang_thiet_lap" and ghep and ghep[0][0] == "TL6-T7-K2" and ghep[0][1].endswith("TL6-T7-K2.exe")
    assert _yv(goc, "thiet_lap_kenh") == "true" and _yv(goc, "nuoi_trang_chu") == "true" and _yv(goc, "tu_chay") == "false"
    # thiết lập đang chạy / cần người: vẫn chưa tu_chay
    r = mk.kich_hoat(goc, "TL6-T7-K2", **chung)
    assert r["trang_thai"] == "dang_thiet_lap" and _yv(goc, "tu_chay") == "false"
    so.update(trang_thai="can_nguoi", ly_do="hết lượt đổi handle")
    r = mk.kich_hoat(goc, "TL6-T7-K2", **chung)
    assert "cần người" in r["ly_do"] and _yv(goc, "tu_chay") == "false"
    assert "hết lượt đổi handle" in mk.viec_cua_ban(goc)[0]["chu"]
    # thiết lập XONG → mới bật tu_chay
    so.update(trang_thai="xong")
    r = mk.kich_hoat(goc, "TL6-T7-K2", **chung)
    assert r["trang_thai"] == "xong" and _yv(goc, "tu_chay") == "true"
    assert mk.dang_mo(goc) == [] and mk.viec_cua_ban(goc) == []


def test_kich_hoat_chua_co_chrome(goc):
    _san_sang_kich_hoat(goc, tmp_chrome=False)
    r = mk.kich_hoat(goc, "TL6-T7-K2", kiem_dang_nhap=lambda e: (True, ""), log=lambda s: None, bay_gio=NOW)
    assert r["trang_thai"] == "chuan_bi_xong" and "Chrome Portable" in r["ly_do"] and _yv(goc, "thiet_lap_kenh") == "false"
    assert "chép từ một Chrome Portable có sẵn" in mk.viec_cua_ban(goc)[0]["chu"]


def test_kich_hoat_ngon_ngu_tai_khoan_khi_da_chung_minh(goc):
    _san_sang_kich_hoat(goc)
    (Path(goc) / "workspace").mkdir(exist_ok=True)
    (Path(goc) / "workspace" / "cai-dat.json").write_text('{"ngon_ngu_tai_khoan_chung_minh": ["ja"]}', encoding="utf-8")
    mk.kich_hoat(goc, "TL6-T7-K2", kiem_dang_nhap=lambda e: (True, ""), them_vao_vm=lambda *a, **k: None, doc_so=lambda m: {}, log=lambda s: None, bay_gio=NOW)
    assert mk._kenh_yaml(goc, "TL6-T7-K2")["ngon_ngu_tai_khoan_dich"] == "ja"


# ── 7) việc của người: ĐÚNG MỘT việc ───────────────────────────────────────────────────────
def test_viec_cua_ban_dung_mot_viec(goc):
    _san_sang_kich_hoat(goc)
    v = mk.viec_cua_ban(goc)
    assert len(v) == 1 and v[0]["khoa"] == "mo-kenh:TL6-T7-K2"
    exe = mk.thu_muc_chrome(goc, "TL6-T7-K2")
    assert v[0]["chu"] == "Mở kênh TL6-T7-K2: tạo kênh YouTube và đăng nhập Chrome Portable tại {0}".format(exe)
    # thêm kênh thứ hai vào luồng cũng chỉ ra MỘT việc
    st = mk.doc_trang_thai(goc)
    st["kenh"]["TL7-T7"] = dict(st["kenh"]["TL6-T7-K2"])
    mk.luu_trang_thai(goc, st)
    assert len(mk.viec_cua_ban(goc)) == 1


def test_viec_hien_tren_bang_dieu_khien(goc, monkeypatch):
    _san_sang_kich_hoat(goc)
    from core import bang_dieu_khien as bdk

    ra = bdk.viec_cua_ban(goc, anh={"kenh": []}, bay_gio=NOW, so_du_micro=10 ** 12, trang_thai_may={}, co_client=True, gio_lich="x")
    mo = [v for v in ra if v["khoa"].startswith("mo-kenh:")]
    assert len(mo) == 1 and mo[0]["chu"].startswith("Mở kênh TL6-T7-K2:")


# ── 8) móc hằng ngày ────────────────────────────────────────────────────────────────────────
def test_nhip_chi_sinh_khi_den_han(goc, monkeypatch):
    _map_tep(monkeypatch)
    sinh = []
    # chưa có đề xuất nào, chưa từng chạy → đến hạn đề xuất định kỳ
    r = mk.nhip(goc, bay_gio=NOW, sinh=lambda g: sinh.append(g) or 4242)
    assert r["sinh"] and r["pid"] == 4242 and "đề xuất định kỳ" in r["ly_do"]
    # vừa đề xuất hôm nay → không sinh
    mk.luu_trang_thai(goc, {"kenh": {}, "ngay_de_xuat_cuoi": "2026-10-04"})
    assert mk.nhip(goc, bay_gio=NOW, sinh=lambda g: sinh.append(g) or 1)["sinh"] is False and len(sinh) == 1
    # 7 ngày sau → lại đến hạn
    assert mk.nhip(goc, bay_gio=NOW + dt.timedelta(days=7), thu=True)["ly_do"].startswith("(--thu) sẽ làm")
    # kênh chờ Chrome: kiểm lại tối đa mỗi 60 phút
    mk.luu_trang_thai(goc, {"kenh": {"X": {"trang_thai": "cho_chrome", "kiem_cuoi": NOW.timestamp() - 600}}, "ngay_de_xuat_cuoi": "2026-10-04"})
    assert not mk.can_lam(goc, NOW)
    assert mk.can_lam(goc, NOW + dt.timedelta(minutes=61)) == "kiểm X"


def test_tiep_tuc_de_xuat_dang_ky_chuan_bi_va_kich_hoat(goc, monkeypatch):
    _map_tep(monkeypatch)
    bang = _dung_thi_truong(goc, thang=2)
    goi_ham = []
    mk.tiep_tuc(goc, bay_gio=NOW, log=lambda s: None, de_xuat_ham=lambda g, bay_gio=None: mk.de_xuat(g, bang=bang, bay_gio=bay_gio),
                chuan_bi_ham=lambda g, ma, **k: goi_ham.append(("chuan_bi", ma)) or mk.doc_trang_thai(g)["kenh"][ma].update(trang_thai="cho_chrome")
                or None)
    assert goi_ham == [("chuan_bi", "TL6-T7-K2")]
    st = mk.doc_trang_thai(goc)
    assert st["ngay_de_xuat_cuoi"] == "2026-10-04" and st["kenh"]["TL6-T7-K2"]["tep"] == "t8"
    assert os.path.isfile(os.path.join(goc, "workspace", "mo-kenh", "de-xuat.json"))
    assert not os.path.exists(os.path.join(goc, "workspace", "mo-kenh", ".khoa"))        # nhả khoá


# ── 9) Chrome Portable + kiểm đăng nhập + handle ────────────────────────────────────────────
def test_chep_chrome_portable_khong_chep_phien_dang_nhap(tmp_path, monkeypatch):
    monkeypatch.setattr(mk, "GB_TRONG_TOI_THIEU", 0.0)
    goc = tmp_path / "MyTool"
    goc.mkdir()
    mau = tmp_path / "TL1-T7"
    (mau / "App" / "Chrome-bin").mkdir(parents=True)
    (mau / "App" / "Chrome-bin" / "chrome.exe").write_bytes(b"chrome")
    (mau / "Other").mkdir()
    (mau / "Other" / "x.txt").write_text("x")
    (mau / "Data" / "profile" / "Default").mkdir(parents=True)
    (mau / "Data" / "profile" / "Default" / "Cookies").write_bytes(b"BI-MAT-DANG-NHAP")
    (mau / "TL1-T7.exe").write_bytes(b"launcher")
    (mau / "help.html").write_text("h")
    assert mk.tim_chrome_mau(str(goc), tru="TL7-T7") == str(mau)
    tt, gc = mk.chep_chrome_portable(str(goc), "TL7-T7", log=lambda s: None)
    d = tmp_path / "TL7-T7"
    assert tt == "da_chep" and (d / "TL7-T7.exe").read_bytes() == b"launcher" and (d / "App" / "Chrome-bin" / "chrome.exe").is_file()
    assert (d / "Data" / "profile").is_dir() and not list((d / "Data" / "profile").iterdir())      # Data TRỐNG
    assert not (d / "TL1-T7.exe").exists() and not (tmp_path / "TL7-T7.dang-chep").exists()
    assert mk.chep_chrome_portable(str(goc), "TL7-T7", log=lambda s: None)[0] == "co_san"           # không đè
    (tmp_path / "TL8-T7").mkdir()                                                                  # thư mục có sẵn nhưng thiếu exe → không đè
    assert mk.chep_chrome_portable(str(goc), "TL8-T7", log=lambda s: None)[0] == "khong_chep"


def test_chep_chrome_het_cho(tmp_path, monkeypatch):
    monkeypatch.setattr(mk, "GB_TRONG_TOI_THIEU", 10 ** 9)
    goc = tmp_path / "MyTool"
    goc.mkdir()
    mau = tmp_path / "TL1-T7"
    (mau / "App" / "Chrome-bin").mkdir(parents=True)
    (mau / "App" / "Chrome-bin" / "chrome.exe").write_bytes(b"c")
    (mau / "TL1-T7.exe").write_bytes(b"l")
    tt, gc = mk.chep_chrome_portable(str(goc), "TL7-T7", log=lambda s: None)
    assert tt == "khong_chep" and "ổ còn" in gc and not (tmp_path / "TL7-T7").exists()


def _cookie_db(duong, ten, host):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    con = sqlite3.connect(duong)
    con.execute("create table cookies (host_key text, name text, value blob)")
    con.execute("insert into cookies values (?, ?, x'00')", (host, ten))
    con.commit()
    con.close()


def test_chrome_da_dang_nhap(tmp_path):
    exe = tmp_path / "K" / "K.exe"
    exe.parent.mkdir()
    assert mk.chrome_da_dang_nhap(str(exe))[0] is False                                  # chưa có hồ sơ
    db = exe.parent / "Data" / "profile" / "Default" / "Network" / "Cookies"
    _cookie_db(str(db), "NID", ".google.com")
    ok, ly = mk.chrome_da_dang_nhap(str(exe))
    assert ok is False and "chưa thấy phiên" in ly
    db.unlink()
    _cookie_db(str(db), "LOGIN_INFO", ".youtube.com")
    assert mk.chrome_da_dang_nhap(str(exe)) == (True, "")


def test_kiem_handle_va_bien_the():
    assert mk.kiem_handle_trong("abc", mo_url=lambda u: (404, "")) is True
    assert mk.kiem_handle_trong("abc", mo_url=lambda u: (200, '{"channelId":"UC1"}')) is False
    assert mk.kiem_handle_trong("abc", mo_url=lambda u: (200, "<html>consent</html>")) is None
    assert mk.kiem_handle_trong("abc", mo_url=lambda u: (_ for _ in ()).throw(OSError("mạng"))) is None
    ket = {"nagi": False, "nagi-jp": False, "nagi-2": True}
    assert mk.handle_ranh("@nagi", "ja", lambda h: ket.get(h)) == ("@nagi-2", "đổi từ @nagi vì đã có người dùng")
    assert mk.handle_ranh("nagi", "ja", lambda h: True)[0] == "@nagi"
    assert mk.handle_ranh("nagi", "ja", lambda h: None)[0] == "@nagi"                     # không kiểm được → giữ gốc
    assert mk.handle_ranh("nagi", "ja", lambda h: False)[1].startswith("4 biến thể")


def test_tom_tat_cho_nao_va_cli_xem(goc, capsys):
    mk.ghi_de_xuat(goc, {"ngay": "2026-10-04 13:47", "canh_bao": [], "de_xuat": [{"ma_de_xuat": "TL7-T7", "loai": "tep_moi", "ly_do": "nguồn nổ 31,0"}]})
    ra = "\n".join(mk.tom_tat_nao(goc))
    assert "NÊN MỞ TL7-T7" in ra and "31,0" in ra
