"""14/10/2026: skill tự kích hoạt (`core/ky_nang.py` điều kiện + `core/ky_nang_tu.py` bộ chạy) — cây thư mục giả,
tiến trình con giả, đồng hồ cố định. Tên kênh / mã video / tiêu đề đều GIẢ."""
import contextlib
import datetime as dt
import json
import os
import sys
import time

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import ky_nang as kn  # noqa: E402
from core import ky_nang_tu as knt  # noqa: E402

BAY = dt.datetime(2026, 10, 14, 10, 35)
GIO = {"bay": BAY}


@pytest.fixture(autouse=True)
def dong_ho(monkeypatch):
    GIO["bay"] = BAY
    monkeypatch.setattr(kn, "_gio", lambda: GIO["bay"])
    nao = []
    from core import nao_bo_phan
    monkeypatch.setattr(nao_bo_phan, "ghi", lambda goc, bp, loai, **kw: nao.append((bp, loai, kw)) or True)
    return nao


def _goc(tmp_path, kenh=("KA",), them=""):
    g = tmp_path
    (g / "vm" / "logs" / "kiem-dom").mkdir(parents=True, exist_ok=True)
    (g / "workspace").mkdir(exist_ok=True)
    (g / "vm" / "cai-dat-tool.json").write_text(json.dumps(
        {"kenh": {k: {"cach_dang": "tu_dong", "tu_dang": True} for k in kenh}}), encoding="utf-8")
    for k in kenh:
        d = g / "CHANNEL" / k
        d.mkdir(parents=True, exist_ok=True)
        (d / "kenh.yaml").write_text('tu_chay: true\nvoice_id: "giong-gia"\nnhip_dang: "05:00"\nngan_sach_ngay: 1000\n'
                                     + them, encoding="utf-8")
        (g / "vm" / "logs" / "kiem-dom" / (k + ".json")).write_text(
            json.dumps({"ok": True, "ngay": "2026-10-14 07:00:00"}), encoding="utf-8")
    return str(g)


# ── bộ chạy, trên skill giả ───────────────────────────────────────────────────

def _skill(ma, dung=True, nang=False, tu_ap=True, nhip=24.0, toan_may=False):
    trang = {"dung": dung}
    k = kn.KyNang(ma, "skill " + ma, "sua_chua", "thử", "thử", lambda g, kk: (kn.DAT, ""), [],
                  dieu_kien=lambda g, kk: (trang["dung"], "lý do " + ma), chay=["lenh-gia", ma], nhip_gio=nhip,
                  tu_ap=tu_ap, nang=nang, toan_may=toan_may)
    return k, trang


class Chay:
    """Tiến trình con giả: ghi lệnh; `ma` = mã thoát; `sau(lenh)` = việc làm xong (đổi cây thư mục / trạng thái)."""

    def __init__(self, ma=0, sau=None):
        self.goi, self.ma, self.sau = [], ma, sau

    def __call__(self, lenh, cwd, han):
        self.goi.append(list(lenh))
        if self.sau:
            self.sau(lenh)
        return self.ma, "đầu ra giả"


def _danh_muc(monkeypatch, *ds):
    monkeypatch.setattr(kn, "DANH_MUC", [k for k, _t in ds])
    return [t for _k, t in ds]


def _so(goc):
    return knt.doc_so(goc)


def test_tu_ap_false_chi_bao_khong_bao_gio_chay(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X10", tu_ap=False))
    c = Chay()
    for _ in range(3):
        knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert c.goi == []
    so = _so(goc)
    assert [x["quyet"] for x in so] == ["nen_chay"]          # ghi một lần, không phình mỗi lượt


def test_nhip_gio_va_xong(tmp_path, monkeypatch, dong_ho):
    goc = _goc(tmp_path)
    (t,) = _danh_muc(monkeypatch, _skill("X01", nhip=24))
    c = Chay(sau=lambda lenh: t.update(dung=False))
    knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 1 and _so(goc)[-1]["quyet"] == "xong"
    assert dong_ho[-1][1] == "ket_qua" and dong_ho[-1][2]["kenh"] == "KA"   # sự kiện não: kết quả
    t["dung"] = True                                               # điều kiện đúng lại ngay
    GIO["bay"] = BAY + dt.timedelta(hours=5)
    ds = knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 1 and ds[0]["quyet"] == "cho_nhip"
    GIO["bay"] = BAY + dt.timedelta(hours=25)
    knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 2


def test_mot_viec_nang_moi_luot_viec_nhe_van_chay(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    ts = _danh_muc(monkeypatch, _skill("S04", nang=True), _skill("S03", nang=True), _skill("X02"))
    c = Chay(sau=lambda lenh: ts[{"S04": 0, "S03": 1, "X02": 2}[lenh[1]]].update(dung=False))
    ds = {x["ma"]: x for x in knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)}
    assert [g[1] for g in c.goi] == ["X02", "S03"]                 # nhẹ trước, rồi đúng MỘT việc nặng gấp nhất
    assert ds["S04"]["quyet"] == "bo_qua" and "việc nặng" in ds["S04"]["ly_do"]


def test_khoa_may_ban_thi_de_luot_sau(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("S03", nang=True), _skill("X02"))
    p = tmp_path / "workspace" / "tu-chay"
    p.mkdir(parents=True)
    (p / ".khoa-may").write_text(json.dumps({"pid": os.getpid(), "bat_dau": time.time()}), encoding="utf-8")
    c = Chay(ma=0)
    ds = {x["ma"]: x for x in knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)}
    assert [g[1] for g in c.goi] == ["X02"]
    assert ds["S03"]["quyet"] == "bo_qua" and "khoá máy bận" in ds["S03"]["ly_do"]
    assert (p / ".khoa-may").exists()                              # không bao giờ ép / xoá khoá người khác


def test_ve_xep_hang_khoa_may_cung_la_ban(tmp_path):
    goc = _goc(tmp_path)
    cho = tmp_path / "workspace" / "khe" / "cho"
    cho.mkdir(parents=True)
    (cho / "1-a.json").write_text(json.dumps({"pid": os.getpid(), "loai": "nang"}), encoding="utf-8")
    assert "xếp hàng" in knt.khoa_may_ban(goc)
    (cho / "1-a.json").write_text(json.dumps({"pid": os.getpid(), "loai": "api"}), encoding="utf-8")
    assert knt.khoa_may_ban(goc) == ""


@pytest.mark.parametrize("phut", [55, 59, 0, 4])
def test_phut_55_den_05_bo_luot(tmp_path, monkeypatch, phut):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X01"))
    GIO["bay"] = BAY.replace(minute=phut)
    c = Chay()
    assert knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None) == []
    assert c.goi == [] and _so(goc) == []


def test_hong_3_lan_lien_tam_dung_24_gio_va_bao(tmp_path, monkeypatch, dong_ho):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X01", nhip=1))
    bao = []
    from core import bao_dong
    monkeypatch.setattr(bao_dong, "bao_dong", lambda *a, **kw: bao.append((a, kw)) or True)
    c = Chay(ma=1)
    for gio in (0, 2, 4):
        GIO["bay"] = BAY + dt.timedelta(hours=gio)
        knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 3 and len(bao) == 1 and "hỏng 3 lần" in bao[0][0][1]
    assert dong_ho[-1][1] == "loi"
    GIO["bay"] = BAY + dt.timedelta(hours=6)
    ds = knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 3 and ds[0]["quyet"] == "tam_dung"
    viec = knt.viec_cua_ban(goc)
    assert any(v["khoa"].startswith("ky-nang-dung:X01:KA:") for v in viec)
    GIO["bay"] = BAY + dt.timedelta(hours=4 + 25)               # hết 24 giờ → thử lại một lần
    knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 4


def test_hoan_khong_tinh_nhip_khong_tinh_hong(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X01", nhip=24))
    c = Chay(ma=10)
    for gio in range(4):
        GIO["bay"] = BAY + dt.timedelta(hours=gio)
        knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 4 and {x["quyet"] for x in _so(goc)} == {"hoan"}
    assert knt.hong_lien(_so(goc), "X01", "KA")[0] == 0


def test_xong_ma_dieu_kien_van_dung_cung_lenh_la_hong(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X01"))
    knt.tu_kich_hoat(goc, chay_lenh=Chay(ma=0), in_ra=lambda s: None)
    x = _so(goc)[-1]
    assert x["quyet"] == "hong" and "vẫn đúng" in x["ket"]


def test_cong_tac_chung_va_tat_rieng_kenh(tmp_path, monkeypatch):
    goc = _goc(tmp_path, kenh=("KA", "KB"))
    _danh_muc(monkeypatch, _skill("X01"))
    (tmp_path / "workspace" / "cai-dat.json").write_text(json.dumps({"ky_nang_tu_kich_hoat": False}), encoding="utf-8")
    c = Chay(sau=lambda lenh: None)
    ds = knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert c.goi == [] and {x["quyet"] for x in ds} == {"cong_tac_tat"}
    (tmp_path / "workspace" / "cai-dat.json").write_text(json.dumps({"ky_nang_tu_kich_hoat": True}), encoding="utf-8")
    with open(tmp_path / "CHANNEL" / "KA" / "kenh.yaml", "a", encoding="utf-8") as tep:
        tep.write("ky_nang_tat: [X01]\n")
    ds = {x["kenh"]: x for x in knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)}
    assert ds["KA"]["quyet"] == "tat_kenh" and len(c.goi) == 1


def test_thu_chi_in_khong_chay_khong_ghi(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X01", nang=True), _skill("X02", toan_may=True))
    c, dong = Chay(), []
    ds = knt.tu_kich_hoat(goc, thu=True, chay_lenh=c, in_ra=dong.append)
    assert c.goi == [] and not os.path.exists(knt.duong_so(goc))
    assert {(x["ma"], x["kenh"], x["quyet"]) for x in ds} == {("X01", "KA", "se_chay"), ("X02", "", "se_chay")}
    assert any("CHẠY THỬ" in d for d in dong)


def test_danh_muc_that_khai_du(tmp_path):
    co = [k for k in kn.DANH_MUC if k.dieu_kien is not None]
    assert {k.ma for k in co} == {"S02", "S03", "S04", "S05", "D09", "K20", "D10", "D11", "D12", "D13", "D14", "D15",
                               "D16", "D17", "S06", "D18", "D19", "D20"}
    for k in co:
        assert k.ma in knt.BO_PHAN
        assert (k.chay is not None) == k.tu_ap, k.ma
    assert not kn.theo_ma("D10").tu_ap and not kn.theo_ma("D11").tu_ap
    assert {k.ma for k in co if k.nang} == set(knt.UU_TIEN_NANG)
    assert all(k.han_phut >= 40 for k in co if k.ma in ("D16", "D17", "S06", "D19"))


def test_skill_mot_kenh_moi_luot(tmp_path, monkeypatch):
    """D16/D17/S06: việc nhẹ mà dài (nhiều lượt AI) — mỗi lượt chỉ MỘT kênh, kênh khác lượt sau."""
    goc = _goc(tmp_path, kenh=("KA", "KB", "KC"))
    k, _t = _skill("X09")
    k.mot_kenh = True
    _danh_muc(monkeypatch, (k, _t))
    c = Chay()
    ds = knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)
    assert len(c.goi) == 1
    assert sorted(x["quyet"] for x in ds) == ["bo_qua", "bo_qua", "hong"] or len([x for x in ds if x["quyet"] == "bo_qua"]) == 2


def test_viec_doi_suat_len_dau_suat_nang():
    a = {"ma": "D13", "kenh": "TL1", "nang": True}
    b = {"ma": "S03", "kenh": "TL2", "nang": True}
    assert sorted([a, b], key=lambda x: knt._thu_tu(x))[0] is b
    assert sorted([a, b], key=lambda x: knt._thu_tu(x, {"D13|TL1"}))[0] is a
    assert "ShopAPI-KyNang" in knt.lenh_lich("<MyTool>", py="<pythonw.exe>") and "/ST 00:35" in knt.lenh_lich("<g>", py="p")


# ── S02 · khám cấu hình kênh ──────────────────────────────────────────────────

GOC_YAML = 'tu_chay: true\nvoice_id: "giong-gia"\nnhip_dang: "05:00"\nngan_sach_ngay: 1000\nchuyen_doi_sub:\n  bat: true\n'


def _viet_yaml(tmp_path, chu, kenh="KA"):
    p = tmp_path / "CHANNEL" / kenh / "kenh.yaml"
    with open(p, "w", encoding="utf-8", newline="") as tep:
        tep.write(chu)
    return p


@pytest.mark.parametrize("ban", [
    GOC_YAML + "\ufeff  cta_giua: ab\n",                       # BOM đầu khối lồng: YAML chuẩn lặng lẽ mất khoá
    GOC_YAML + "\ufeff# --- khối nhân bản ---\ntep: \"x\"\n",   # BOM trước chú thích: YAML chuẩn ném lỗi
])
def test_s02_go_bom_khi_hai_bo_doc_cung_gia_tri(tmp_path, ban):
    goc = _goc(tmp_path)
    p = _viet_yaml(tmp_path, ban)
    try:
        hong = yaml.safe_load(ban) != yaml.safe_load(ban.replace("\ufeff", ""))
    except yaml.YAMLError:
        hong = True
    assert hong                                                    # tiền đề: YAML chuẩn đọc bản gốc sai
    assert kn.d_cau_hinh(goc, "KA")[0] is True and kn.k_cau_hinh(goc, "KA")[0] == kn.LOI
    truoc = yaml.safe_load(ban.replace("\ufeff", ""))
    ok, _ly = kn.go_bom(goc, "KA")
    sau = p.read_text(encoding="utf-8")
    assert ok and "\ufeff" not in sau and yaml.safe_load(sau) == truoc
    assert os.listdir(tmp_path / "workspace" / "sao-luu" / "kenh-yaml")
    assert kn.d_cau_hinh(goc, "KA")[0] is False and kn.k_cau_hinh(goc, "KA")[0] == kn.DAT


def test_s02_bom_lech_gia_tri_chi_bao_khong_sua(tmp_path):
    goc = _goc(tmp_path)
    ban = 'tu_chay: true\nvoice_id: "giong-gia"\ufeff\nnhip_dang: "05:00"\nngan_sach_ngay: 1000\n'
    p = _viet_yaml(tmp_path, ban)
    assert kn.kham_bom(ban)[0] == "bao"
    assert kn.d_cau_hinh(goc, "KA")[0] is False
    assert kn.go_bom(goc, "KA")[0] is False and p.read_text(encoding="utf-8") == ban
    assert any(v["khoa"] == "ky-nang:S02:KA:bom" for v in knt.viec_cua_ban(goc))


def test_s02_bom_dau_tep_khong_dung():
    assert kn.kham_bom("\ufeff" + GOC_YAML) == ("", "")


def test_s02_thieu_khoa_chi_bao_kem_goi_y_khong_tu_bat(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    ban = 'tu_chay: true\nthu_muc_done: ""\nvoice_id: ""\nngan_sach_ngay: 0\n'
    p = _viet_yaml(tmp_path, ban)
    assert kn.d_cau_hinh(goc, "KA")[0] is False and kn.k_cau_hinh(goc, "KA")[0] == kn.LOI
    v = [x for x in knt.viec_cua_ban(goc) if x["khoa"].startswith("ky-nang:S02:KA:")]
    assert len(v) == 1
    for khoa in ("thu_muc_done", "nhip_dang", "ngan_sach_ngay", "voice_id"):
        assert khoa in v[0]["chu"] and khoa in v[0]["goi_y"]
    knt.tu_kich_hoat(goc, chay_lenh=Chay(), in_ra=lambda s: None)
    assert p.read_text(encoding="utf-8") == ban                    # không bao giờ tự thêm / bật khoá


def test_s02_thieu_khoa_thu_muc_done_thi_mac_dinh_v2191(tmp_path):
    goc = _goc(tmp_path)                                           # kênh tự chạy không khai → DONE/<mã>
    assert not [x for x in knt.viec_cua_ban(goc) if x["khoa"].startswith("ky-nang:S02:")]


# ── S03 · đổi bìa gấp ─────────────────────────────────────────────────────────

def _bia(tmp_path, len_song, trang_thai="cho"):
    from core import ke_hoach_dang
    goc = _goc(tmp_path)
    (tmp_path / "vm" / "logs" / "hang-sua.json").write_text(json.dumps({"viec": [
        {"id": "gia-1:bia", "buoc": "bia", "kenh": "KA", "ma_goi": "KA-0001", "video_id": "AAAAAAAAAAA",
         "anh": "C:/gia/bia.jpg", "them_luc": "2026-10-14T09:00:00", "trang_thai": trang_thai, "lan_loi": "0"}]}),
        encoding="utf-8")
    dong = [""] * len(ke_hoach_dang.COT)
    dong[0], dong[1], dong[2] = "KA-0001", len_song.strftime("%d/%m/%Y"), len_song.strftime("%H:%M")
    ke_hoach_dang.luu_bang(goc, "KA", [dong])
    return goc


def test_s03_bia_gap_khi_video_sap_len_song(tmp_path):
    goc = _bia(tmp_path, BAY + dt.timedelta(hours=3))
    dung, ly = kn.d_bia_gap(goc, "KA")
    assert dung, ly
    lenh = kn.c_bia_gap(goc, "KA")
    assert lenh[-5:] == ["--kenh", "KA", "--sua-video", "--toi-da-video", "2"] and lenh[-6].endswith("may_dang_dom.py")


def test_s03_da_len_song_cung_gap(tmp_path):
    assert kn.d_bia_gap(_bia(tmp_path, BAY - dt.timedelta(days=2)), "KA")[0]


@pytest.mark.parametrize("gio, ly", [(dt.datetime(2026, 10, 15, 0, 30), "≤ 2 giờ"),
                                     (dt.datetime(2026, 10, 15, 3, 0), "khe đêm 02–05")])
def test_s03_gan_khe_dem_thi_de_agent(tmp_path, gio, ly):
    goc = _bia(tmp_path, BAY + dt.timedelta(hours=16))
    GIO["bay"] = gio
    dung, chu = kn.d_bia_gap(goc, "KA")
    assert not dung and ly in chu


def test_s03_con_xa_hoac_khong_con_viec(tmp_path):
    assert not kn.d_bia_gap(_bia(tmp_path, BAY + dt.timedelta(hours=20)), "KA")[0]
    assert not kn.d_bia_gap(_bia(tmp_path, BAY + dt.timedelta(hours=2), trang_thai="xong"), "KA")[0]


def test_s03_nhuong_phien_dang(tmp_path):
    goc = _bia(tmp_path, BAY + dt.timedelta(hours=3))
    (tmp_path / "vm" / "trang-thai.json").write_text(json.dumps({"phien_muc_tieu@KA@2026-10-14": "11:00"}), encoding="utf-8")
    dung, ly = kn.d_bia_gap(goc, "KA")
    assert not dung and "phiên kênh" in ly


# ── S04 · bàn giao lượt kẹt cấu hình ──────────────────────────────────────────

KET_CAU_HINH = "kênh chưa khai `thu_muc_done` trong kenh.yaml — sản xuất xong nhưng KHÔNG bàn giao"


def _ket(tmp_path, ly_do_trong=KET_CAU_HINH, loi="", video=True, bo=True):
    goc = _goc(tmp_path, them="tu_duyet: true\n")
    run = {"ma_luot": "0001", "nguon": {"ma": "nguon-gia", "link": ""},
           "ban_giao": {"da_ban_giao": False, "ma_goi": "", "ly_do_trong": ly_do_trong, "loi": loi}}
    if bo:
        run.update(bo=True, ly_do_bo="đã tự phục hồi 3 lần mà vẫn chưa xong", phuc_hoi={"so_lan": 3})
    d = tmp_path / "CHANNEL" / "KA" / "tu-chay"
    d.mkdir(parents=True)
    (d / "2026-10-13.json").write_text(json.dumps({"runs": [run]}, ensure_ascii=False), encoding="utf-8")
    luot = tmp_path / "PROJECTS" / "AUTO" / "KA" / "0001"
    luot.mkdir(parents=True)
    if video:
        (luot / "8-video.mp4").write_bytes(b"gia")
    (luot / "BO-VI-1.txt").write_text("dấu", encoding="utf-8")
    return goc


def test_s04_ket_cau_hinh_thi_ban_giao(tmp_path):
    goc = _ket(tmp_path)
    dung, ly = kn.d_ban_giao_ket(goc, "KA")
    assert dung and "0001" in ly
    assert kn.c_ban_giao_ket(goc, "KA")[-5:] == ["core.ban_giao_dang", "ban-giao-tay", "KA", "0001", "2026-10-13"]


@pytest.mark.parametrize("kw", [{"loi": "KHÔNG bàn giao KA-0001: chất lượng chưa đạt — khung đứng"},
                                {"ly_do_trong": "", "loi": "máy chủ ShopAPI trả 503 nhiều lần"},
                                {"video": False}])
def test_s04_khong_phai_loi_cau_hinh_thi_thoi(tmp_path, kw):
    assert not kn.d_ban_giao_ket(_ket(tmp_path, **kw), "KA")[0]


def test_s04_kenh_dang_chay_luot_thi_nhuong(tmp_path):
    goc = _ket(tmp_path)
    p = tmp_path / "workspace" / "khe"
    p.mkdir(parents=True)
    (p / "dieu-phoi.json").write_text(json.dumps({"kenh": [{"ma": "KA", "dang_chay": True}]}), encoding="utf-8")
    assert not kn.d_ban_giao_ket(goc, "KA")[0]


def _gia_ban_giao(monkeypatch, loi=None):
    from core import ban_giao_dang, chon_content, dieu_phoi, nao, tu_hoc, xep_lich
    goi = []

    def ban_giao(goc, kenh, luot, done, ngay="", gio=""):
        goi.append((kenh, luot, ngay, gio))
        if loi:
            raise RuntimeError(loi)
        return "KA-0001", True
    monkeypatch.setattr(ban_giao_dang, "ban_giao", ban_giao)
    monkeypatch.setattr(xep_lich, "khe_trong_som_nhat", lambda *a, **k: ("15/10/2026", "05:00"))
    monkeypatch.setattr(dieu_phoi, "giu_nang", lambda *a, **k: contextlib.nullcontext())
    monkeypatch.setattr(tu_hoc, "ghi_van_tu_luot", lambda *a, **k: None)
    monkeypatch.setattr(nao, "ghi_ban_giao", lambda *a, **k: [])
    monkeypatch.setattr(chon_content, "hoan_tat_lua_chon", lambda *a, **k: True)
    return goi


def test_ban_giao_tay_ghi_so_go_co_bo(tmp_path, monkeypatch):
    from core import ban_giao_dang
    goc = _ket(tmp_path)
    goi = _gia_ban_giao(monkeypatch)
    assert ban_giao_dang.ban_giao_tay(goc, "KA", "0001", "2026-10-13", ghi=lambda s: None) == 0
    assert goi == [("KA", "0001", "15/10/2026", "05:00")]
    run = json.loads((tmp_path / "CHANNEL" / "KA" / "tu-chay" / "2026-10-13.json").read_text(encoding="utf-8"))["runs"][0]
    assert run["ban_giao"]["da_ban_giao"] and run["ban_giao"]["ma_goi"] == "KA-0001" and run["ban_giao"]["ly_do_trong"] == ""
    assert "bo" not in run and "ly_do_bo" not in run and "phuc_hoi" not in run
    assert not (tmp_path / "PROJECTS" / "AUTO" / "KA" / "0001" / "BO-VI-1.txt").exists()
    assert (tmp_path / "workspace" / "sao-luu" / "bo-vi-KA-0001" / "BO-VI-1.txt").exists()
    assert not kn.d_ban_giao_ket(goc, "KA")[0]                     # chạy lại: không còn gì
    assert ban_giao_dang.ban_giao_tay(goc, "KA", "0001", "2026-10-13", ghi=lambda s: None) == 0 and len(goi) == 1


def test_ban_giao_tay_hong_ghi_loi_moi_khong_thu_mai(tmp_path, monkeypatch):
    from core import ban_giao_dang
    goc = _ket(tmp_path)
    _gia_ban_giao(monkeypatch, loi="KHÔNG bàn giao KA-0001: chất lượng chưa đạt — tiếng rè")
    assert ban_giao_dang.ban_giao_tay(goc, "KA", "0001", "2026-10-13", ghi=lambda s: None) == 1
    assert not kn.d_ban_giao_ket(goc, "KA")[0]                     # lý do mới là chất lượng → S04 thôi


# ── D09 · thương hiệu (hình mờ) · K20 · trang chủ ─────────────────────────────

def _thuong_hieu(tmp_path, **du):
    p = tmp_path / "vm" / "logs" / "thiet-lap-kenh"
    p.mkdir(parents=True, exist_ok=True)
    (p / "KA.thuong-hieu.json").write_text(json.dumps(dict({"kenh": "KA", "ket_qua": "xong"}, **du)), encoding="utf-8")


def test_d09_chua_kiem_thi_kiem_thieu_hinh_mo_thi_gan(tmp_path):
    goc = _goc(tmp_path)
    assert kn.d_thuong_hieu(goc, "KA")[0] and kn.c_thuong_hieu(goc, "KA")[-1] == "--kiem-thuong-hieu"
    _thuong_hieu(tmp_path, luc="2026-10-14 08:00:00", hinh_mo={"co": False})
    assert kn.d_thuong_hieu(goc, "KA")[0] and kn.c_thuong_hieu(goc, "KA")[-1] == "--dat-hinh-mo"
    _thuong_hieu(tmp_path, luc="2026-10-14 08:00:00", hinh_mo={"co": False}, dat_hinh_mo={"ket": "dat"})
    assert not kn.d_thuong_hieu(goc, "KA")[0] and kn.k_thuong_hieu(goc, "KA")[0] == kn.DAT
    _thuong_hieu(tmp_path, luc="2026-09-10 08:00:00", hinh_mo={"co": True})
    assert kn.d_thuong_hieu(goc, "KA")[0] and "cũ" in kn.d_thuong_hieu(goc, "KA")[1]


def test_d09_khung_cam_va_chrome_chua_dat(tmp_path):
    goc = _goc(tmp_path)
    GIO["bay"] = BAY.replace(hour=3)
    assert "khung cấm" in kn.d_thuong_hieu(goc, "KA")[1]
    GIO["bay"] = BAY
    (tmp_path / "vm" / "logs" / "kiem-dom" / "KA.json").write_text(json.dumps({"ok": False, "hong": ["x"]}), encoding="utf-8")
    assert not kn.d_thuong_hieu(goc, "KA")[0]


def _bang_tom_tat(tmp_path, *vid):
    d = tmp_path / "CHANNEL" / "KA" / "chi-so"
    d.mkdir(parents=True, exist_ok=True)
    dong = ["Mã video,Ngày đăng,Dài,Lượt hiển thị,Tỷ lệ bấm,Tiêu đề"]
    dong += ["{0},2026-09-20,12:00,{1},5%,テスト動画その{2}".format(v, 10000 - i * 1000, i) for i, v in enumerate(vid)]
    (d / "bang-tom-tat.csv").write_text("\n".join(dong) + "\n", encoding="utf-8")


def test_k20_trang_chu_tat_thi_dat(tmp_path):
    goc = _goc(tmp_path)
    assert "chờ D09" in kn.d_trang_chu(goc, "KA")[1]
    _thuong_hieu(tmp_path, luc="2026-10-14 08:00:00", trang_chu_bat=False, tieu_diem={"trailer": {"co": False}})
    assert not kn.d_trang_chu(goc, "KA")[0]                        # chưa có video đủ chuẩn
    _bang_tom_tat(tmp_path, "BBBBBBBBBBB")
    assert kn.d_trang_chu(goc, "KA")[0] and kn.c_trang_chu(goc, "KA")[-1] == "--dat-trang-chu"


def test_k20_hang_thang_doi_video_thang_nhat(tmp_path):
    goc = _goc(tmp_path)
    _bang_tom_tat(tmp_path, "BBBBBBBBBBB", "CCCCCCCCCCC")

    def dat(luc, vid):
        _thuong_hieu(tmp_path, luc=luc, dat_trang_chu={"ket": "dat", "doc_lai": {"bat": True, "trailer": {"co": True, "ma": [vid]}}})
    dat("2026-10-10 08:00:00", "CCCCCCCCCCC")
    assert not kn.d_trang_chu(goc, "KA")[0]                        # mới đặt 4 ngày
    dat("2026-09-10 08:00:00", "BBBBBBBBBBB")
    assert not kn.d_trang_chu(goc, "KA")[0]                        # vẫn là video thắng nhất
    dat("2026-09-10 08:00:00", "CCCCCCCCCCC")
    assert kn.d_trang_chu(goc, "KA")[0]                            # > 30 ngày và video thắng nhất đã đổi


# ── D10 · D11 (chỉ báo) · D12 ─────────────────────────────────────────────────

def test_d10_d11_chi_bao_khong_chay(tmp_path, monkeypatch):
    from core import bia_theo_khuon, chuyen_doi_sub, kenh_khong_phat
    goc = _goc(tmp_path)
    monkeypatch.setattr(kenh_khong_phat, "dang_dung", lambda *a, **k: (False, ""))
    monkeypatch.setattr(chuyen_doi_sub, "kenh_bat", lambda *a, **k: (False, "kenh.yaml tắt"))
    monkeypatch.setattr(bia_theo_khuon, "trang_thai_khai_thac", lambda *a, **k: {"che_do": "khai_thac", "ly_do": "khuôn đủ"})
    monkeypatch.setattr(kn, "DANH_MUC", [kn.theo_ma("D10"), kn.theo_ma("D11")])
    c = Chay()
    ds = {x["ma"]: x for x in knt.tu_kich_hoat(goc, chay_lenh=c, in_ra=lambda s: None)}
    assert c.goi == [] and ds["D10"]["quyet"] == ds["D11"]["quyet"] == "nen_chay"
    monkeypatch.setattr(kenh_khong_phat, "dang_dung", lambda *a, **k: (True, "không phát"))
    assert kn.k_don_bay_sub(goc, "KA")[0] == kn.KHONG
    with open(tmp_path / "CHANNEL" / "KA" / "kenh.yaml", "a", encoding="utf-8") as tep:
        tep.write("bia_lo: true\n")
    assert kn.k_bia_lo(goc, "KA")[0] == kn.DAT


def test_d12_gom_cu_thi_gom_ngu_cu_thi_bao(tmp_path):
    from core.nao_bo_phan import kho
    goc = _goc(tmp_path)
    assert kn.d_nao_bp(goc, "")[0]                                 # chưa có kho → gom lần đầu
    con = kho.mo(goc)
    kho.dat_meta(con, "gom_cuoi", "%.0f" % (BAY - dt.timedelta(hours=3)).timestamp())
    con.execute("INSERT INTO giac_ngu(luc, bo_phan, loi) VALUES (?, 'bia', '')", ((BAY - dt.timedelta(hours=40)).timestamp(),))
    con.commit()
    con.close()
    assert kn.d_nao_bp(goc, "")[0] and kn.k_nao_bp(goc, "")[0] == kn.LOI
    assert any(v["khoa"].startswith("ky-nang:D12:ngu:") for v in knt.viec_cua_ban(goc))
    con = kho.mo(goc)
    kho.dat_meta(con, "gom_cuoi", "%.0f" % (BAY - dt.timedelta(hours=1)).timestamp())
    con.execute("INSERT INTO giac_ngu(luc, bo_phan, loi) VALUES (?, 'bia', '')", ((BAY - dt.timedelta(hours=5)).timestamp(),))
    con.commit()
    con.close()
    assert not kn.d_nao_bp(goc, "")[0] and kn.k_nao_bp(goc, "")[0] == kn.DAT
    assert not [v for v in knt.viec_cua_ban(goc) if v["khoa"].startswith("ky-nang:D12:")]
    assert [x["kenh"] for x in knt.danh_gia(goc) if x["ma"] == "D12"] == [""]     # toàn máy: một lần


def test_bao_cao_ngay_co_dong_tu_kich_hoat(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    _danh_muc(monkeypatch, _skill("X10", tu_ap=False))
    dong = knt.dong_bao_cao(goc)
    assert any("Nên chạy" in d and "X10 KA" in d for d in dong)


def test_bang_8790_cay_ky_nang_co_tu_kich_hoat(tmp_path):
    from core import tuong_truc_quan
    goc = _goc(tmp_path)
    cay = {x["ma"]: x for x in tuong_truc_quan.cay_ky_nang(goc, "KA")}
    assert cay["D09"]["tu"]["quyet"] == "se_chay" and cay["D09"]["tu"]["nhan"] == "sẽ chạy"
    assert cay["K01"]["tu"] is None
