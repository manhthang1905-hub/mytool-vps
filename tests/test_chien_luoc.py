"""Gói `core/chien_luoc/` — sổ đăng ký, `NguCanh`, trộn nhiều công thức, thăm dò tất định (B2–B3).

Hành vi khi KHÔNG khai `chien_luoc` được canh từng byte ở `test_chien_luoc_golden.py`; bài này canh
phần mới. Không mạng, không ví, kênh giả trong `tmp_path`.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import types

from core import chien_luoc
from core import cong_thuc_vph
from core import tu_chay
from core.chien_luoc import ngu_canh

from test_chien_luoc_golden import _doc, dung_kenh_gia, seam_gia

NO_LOG = lambda *_a, **_k: None  # noqa: E731


def _dong(ma, td, diem=50, nguon="vph"):
    return {"nguon": nguon, "ma": ma, "link": "https://youtu.be/" + ma, "tieu_de": td, "kenh": "Z",
            "diem": diem, "loai": "", "ly_do": []}


def _kenh(goc, ma, *dong_yaml):
    tm = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(tm, exist_ok=True)
    with io.open(os.path.join(tm, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(('ma: "{0}"'.format(ma),) + dong_yaml) + "\n")
    return ma


VPH = [_dong("vvvvvvvvv01", "賢い人の特徴", 90), _dong("vvvvvvvvv02", "優しい人の特徴", 80),
       _dong("CHUNG000001", "繊細な人の特徴", 70), _dong("vvvvvvvvv03", "静かな人の特徴", 60)]
MOT_NUT = {"moi": [
    {"link": "https://youtu.be/mmmmmmmmm01", "tieu_de": "孤独な人の特徴", "view": 900000, "vuot": 9},
    {"link": "https://youtu.be/CHUNG000001", "tieu_de": "繊細な人の特徴", "view": 800000, "vuot": 8},
    {"link": "https://youtu.be/mmmmmmmmm02", "tieu_de": "頭がいい人の口癖", "view": 700000, "vuot": 7},
    {"link": "https://youtu.be/mmmmmmmmm03", "tieu_de": "嫌われる人の特徴", "view": 600000, "vuot": 6}]}


def _xep(goc, ma, co_v7=False, log=None):
    return tu_chay.ung_vien_xep_hang(goc, ma, co_v7, set(), cham_vph=lambda _g, _k: [dict(d) for d in VPH],
                                     doc_danh_sach=lambda _g, _k: json.loads(json.dumps(MOT_NUT)),
                                     log=log or NO_LOG)


# ── sổ đăng ký ──────────────────────────────────────────────────────────────

def test_so_dang_ky_tu_phat_hien_va_bo_mau():
    so = chien_luoc.so_dang_ky(tai_lai=True)
    assert list(so)[:3] == ["v7", "vph", "mot_nut"]
    assert "ten_cong_thuc" not in so and "_mau" not in so and "ngu_canh" not in so
    for m in so.values():
        assert m.TEN and callable(m.cham) and callable(m.ap_dung) and hasattr(m, "LUI_KHI_RONG")
    assert tu_chay.CONG_THUC_NGUON == chien_luoc.mo_ta_cong_thuc()


# ── NguCanh ─────────────────────────────────────────────────────────────────

def test_ngu_canh_giai_doan_ypp_muc_tieu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'tep: "tep-a"', "ypp_sub: 562", "ypp_gio: 4100")
    nc = ngu_canh.dung(goc, "A", co_v7=True)
    assert nc.giai_doan == "dang_len" and nc.ypp["thieu"] == "sub" and nc.ypp["nguon"] == "kenh_yaml"
    dong = nc.muc_tieu().split("\n")
    assert len(dong) == 3 and "thiếu 438 sub" in dong[0] and "tep-a" in dong[1] and "CTR" in dong[2]
    assert ngu_canh.dung(goc, "A", co_v7=False).giai_doan == "moi"
    _kenh(goc, "B", "da_kiem_tien: true", "bien_tap_ai: false")
    nc_b = ngu_canh.dung(goc, "B", co_v7=True)
    assert nc_b.giai_doan == "kiem_tien" and nc_b.cai("bien_tap_ai", True) is False
    assert nc_b.thi_truong["quoc_gia"] == "JP" and isinstance(nc_b.ket_qua_cong_thuc, dict)


def test_loc_chay_lai_cho_cung_ket_qua_va_chi_log_mot_lan(tmp_path):
    log = []
    nc = ngu_canh.dung(str(tmp_path), "A", co_v7=False, loai_tru={"LOAI0000001"},
                       da_lam_tieu_de=[("賢い人の特徴", "video A-1")], log=log.append)
    ds = [_dong("LOAI0000001", "x"), _dong("aaaaaaaaa01", "【心理学】賢い人の特徴"),
          _dong("bbbbbbbbb01", "優しい人の特徴"), _dong("bbbbbbbbb02", "優しい人の特徴"), _dong("", "không mã")]
    ds[4]["link"] = ""
    lan1 = nc.loc(ds)
    assert [d["ma"] for d in lan1] == ["bbbbbbbbb01"]
    assert nc.loc(lan1) == lan1 and nc.loc(ds) == lan1
    assert len([x for x in log if "trùng tiêu đề" in x]) == 1


# ── kế hoạch ────────────────────────────────────────────────────────────────

def test_khong_khai_chien_luoc_la_luat_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    kh = chien_luoc.ke_hoach(ngu_canh.dung(goc, "A", co_v7=False))
    assert kh.cu and kh.trong_so == {"vph": 1.0} and not kh.tham_do
    ds = _xep(goc, "A")
    assert all("cong_thuc" not in d and "tin_hieu" not in d for d in ds), "luật cũ không gắn khoá mới"


def test_tu_dong_theo_giai_doan(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "tu_dong"', "chien_luoc_tham_do: 0")
    kh = chien_luoc.ke_hoach(ngu_canh.dung(goc, "A", co_v7=False))
    assert not kh.cu and kh.trong_so == {"vph": 0.8, "mot_nut": 0.2}
    kh = chien_luoc.ke_hoach(ngu_canh.dung(goc, "A", co_v7=True))
    assert list(kh.trong_so) == ["v7", "vph"] and abs(kh.trong_so["v7"] - 0.8) < 1e-9


def test_bo_ten_la_va_cong_thuc_chua_dung_duoc(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.7, v7:0.3, khong_co:1"')
    log = []
    kh = chien_luoc.ke_hoach(ngu_canh.dung(goc, "A", co_v7=False, log=log.append))
    assert kh.trong_so == {"vph": 1.0} and any("khong_co" in g for g in kh.ghi_chu)
    assert any("v7" in g and "chưa dùng được" in g for g in kh.ghi_chu)


# ── trộn ────────────────────────────────────────────────────────────────────

def test_mot_cong_thuc_trong_chien_luoc_trung_thu_tu_bang_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "CU")
    _kenh(goc, "MOI", 'chien_luoc: "vph"')
    cu, moi = _xep(goc, "CU"), _xep(goc, "MOI")
    assert [d["ma"] for d in moi] == [d["ma"] for d in cu]
    assert all(d["cong_thuc"] == "vph" and d["tham_do"] is False for d in moi)


def test_tron_theo_thu_hang_khu_trung_va_ghi_cong_thuc_khac(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.5, mot_nut:0.5"', "chien_luoc_tham_do: 0")
    log = []
    ds = _xep(goc, "A", log=log.append)
    assert [(d["ma"], d["cong_thuc"]) for d in ds] == [
        ("vvvvvvvvv01", "vph"), ("mmmmmmmmm01", "mot_nut"), ("vvvvvvvvv02", "vph"),
        ("CHUNG000001", "mot_nut"), ("vvvvvvvvv03", "vph"), ("mmmmmmmmm02", "mot_nut"),
        ("mmmmmmmmm03", "mot_nut")]
    chung = [d for d in ds if d["ma"] == "CHUNG000001"]
    assert len(chung) == 1 and chung[0]["tin_hieu"]["cong_thuc_khac"] == ["vph"]
    assert any("chiến lược VPH 50% + MOT_NUT 50%" in x for x in log)


def test_trong_so_lech_thi_cong_thuc_nang_ra_nhieu_hon(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:3, mot_nut:1"', "chien_luoc_tham_do: 0")
    ds = _xep(goc, "A")
    assert [d["cong_thuc"] for d in ds[:4]].count("vph") == 3


def test_bang_rong_khong_lui_vao_cong_thuc_da_co_trong_ke_hoach(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.5, mot_nut:0.5"', "chien_luoc_tham_do: 0")
    ds = tu_chay.ung_vien_xep_hang(goc, "A", False, set(), cham_vph=lambda _g, _k: [],
                                   doc_danh_sach=lambda _g, _k: json.loads(json.dumps(MOT_NUT)))
    assert [d["ma"] for d in ds] == ["mmmmmmmmm01", "CHUNG000001", "mmmmmmmmm02", "mmmmmmmmm03"]
    assert {d["cong_thuc"] for d in ds} == {"mot_nut"}


# ── thăm dò tất định ────────────────────────────────────────────────────────

def test_luot_tham_do_dua_bang_it_n_nhat_len_truoc(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.8, mot_nut:0.2"', "chien_luoc_tham_do: 100")
    log = []
    ds = _xep(goc, "A", log=log.append)
    assert [d["cong_thuc"] for d in ds[:4]] == ["mot_nut"] * 4 and all(d["tham_do"] for d in ds[:4])
    assert not any(d["tham_do"] for d in ds[4:]) and any("THĂM DÒ" in x for x in log)
    # ép khai thác (nơi gọi lùi): không còn dòng thăm dò
    nc = ngu_canh.dung(goc, "A", co_v7=False, cham_vph=lambda _g, _k: [dict(d) for d in VPH],
                       doc_danh_sach=lambda _g, _k: json.loads(json.dumps(MOT_NUT)))
    assert not any(d["tham_do"] for d in chien_luoc.xep_hang(nc, tham_do=False))


def test_tham_do_tat_dinh_theo_kenh_ngay_so_luot(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.8, mot_nut:0.2"', "chien_luoc_tham_do: 50")
    nc = ngu_canh.dung(goc, "A", co_v7=False)
    ngay = nc.bay_gio.date().isoformat()
    mong = int(hashlib.sha1("A|{0}|0".format(ngay).encode("utf-8")).hexdigest(), 16) % 100
    assert chien_luoc._so_tham_do(nc) == mong
    # trạm và vòng chọn nguồn gọi cùng hàm → cùng bảng
    assert _xep(goc, "A") == _xep(goc, "A")
    # mở thêm lượt trong ngày → đổi hạt giống
    duong = tu_chay.duong_bao_cao_ngay(goc, "A", ngay)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump({"runs": [{}, {}]}, tep)
    nc2 = ngu_canh.dung(goc, "A", co_v7=False)
    assert nc2.so_luot_hom_nay == 2
    assert chien_luoc._so_tham_do(nc2) == int(hashlib.sha1(
        "A|{0}|2".format(ngay).encode("utf-8")).hexdigest(), 16) % 100


def test_luot_tham_do_khong_qua_cong_thi_lui_ve_khai_thac(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.8, mot_nut:0.2"', "chien_luoc_tham_do: 100", "phan_cum_ai: false")
    monkeypatch.setattr(cong_thuc_vph, "ung_vien_chon_nguon", lambda _g, _k, **_kw: [dict(d) for d in VPH])
    monkeypatch.setattr(tu_chay, "_bien_tap_ai", lambda _g, _k, ds, *_a: ds)
    # Cổng giả: bảng nào có dòng thăm dò thì không ai qua; bảng khai thác thì qua.
    monkeypatch.setattr(tu_chay, "_cong_chat_luong",
                        lambda ds, _log: [] if any(d.get("tham_do") for d in ds) else ds)
    log = []
    nguon = tu_chay._chon_nguon(goc, "A", False, set(), None,
                                lambda _g, _k: json.loads(json.dumps(MOT_NUT)), log.append,
                                goi_chat=lambda *_a, **_k: "")
    assert nguon["ma"] == "vvvvvvvvv01" and nguon["tham_do"] is False and nguon["cong_thuc"] == "vph"
    assert any("lùi về bảng khai thác" in x for x in log)


def test_run_nguon_ghi_cong_thuc_va_tham_do(tmp_path):
    goc = str(tmp_path)
    fx = _doc("v7-bang-nhom")
    ma = dung_kenh_gia(goc, fx)
    cham_v7, _doc_ds, _vph = seam_gia(fx)
    ket = tu_chay.chay_mot_ngay(goc, ma, che_do="thu", on_log=NO_LOG, chay_mot_nut=lambda *a, **k: None,
                                cham_v7=cham_v7)
    assert ket["run"]["nguon"]["cong_thuc"] == "v7" and ket["run"]["nguon"]["tham_do"] is False


def test_mau_chep_duoc_thanh_cong_thuc(tmp_path):
    """`_mau.py` chạy được nguyên trạng (ap_dung 0 → bộ điều phối bỏ qua)."""
    from core.chien_luoc import _mau

    nc = ngu_canh.dung(str(tmp_path), "A", co_v7=False)
    assert _mau.ap_dung(nc) == 0.0 and _mau.cham(nc) == []


# ── việc dở 30/09 (B7, thị trường Một nút, cụm chưa thử, luat_chon) ─────────

MN_NHO = {"moi": [
    {"link": "https://youtu.be/nhoNHO00001", "tieu_de": "A", "view": 40000, "vuot": 2},
    {"link": "https://youtu.be/toTO0000001", "tieu_de": "B", "view": 90000, "vuot": 1}]}


def test_mot_nut_bac_view_theo_thi_truong(tmp_path):
    """Mặc định = hằng cũ (100.000 → cả hai cùng bậc, vượt quyết); kênh khai `bac_view_manh` thì bậc đổi."""
    goc = str(tmp_path)
    _kenh(goc, "JP", 'cong_thuc_chon: "mot_nut"')
    _kenh(goc, "VI", 'cong_thuc_chon: "mot_nut"', "bac_view_manh: 50000")

    def xep(k):
        return [d["ma"] for d in tu_chay.ung_vien_xep_hang(
            goc, k, False, set(), doc_danh_sach=lambda _g, _k: json.loads(json.dumps(MN_NHO)))]
    assert xep("JP") == ["nhoNHO00001", "toTO0000001"]
    assert xep("VI") == ["toTO0000001", "nhoNHO00001"]


def test_diem_anh_em_tat_khi_kenh_du_video_rieng_48h(tmp_path, monkeypatch):
    """B7: cùng `he_so_tien_nghiem` với V7 — đủ `tat_khi_video_48h` (6) video riêng thì không mượn nữa."""
    from core import cong_thuc_v7 as v7

    goc = str(tmp_path)
    fx = _doc("v7-bang-nhom")
    ma = dung_kenh_gia(goc, fx)
    cham_v7, doc_ds, _vph = seam_gia(fx)
    co = tu_chay.ung_vien_xep_hang(goc, ma, True, set(), cham_v7=cham_v7, doc_danh_sach=doc_ds)
    assert any(d.get("diem_anh_em") for d in co)
    monkeypatch.setattr(v7, "video_cua_kenh",
                        lambda *_a, **_k: [types.SimpleNamespace(hien_thi_48h=1000)] * 6)
    log = []
    khong = tu_chay.ung_vien_xep_hang(goc, ma, True, set(), cham_v7=cham_v7, doc_danh_sach=doc_ds,
                                      log=log.append)
    assert not any(d.get("diem_anh_em") for d in khong) and any("điểm anh em tắt" in x for x in log)


def test_kenh_moi_luot_tham_do_uu_tien_cum_chua_thu(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh(goc, "A", 'chien_luoc: "vph:0.8, mot_nut:0.2"', "chien_luoc_tham_do: 100")
    cum = {"孤独な人の特徴": ["co-don"], "繊細な人の特徴": ["nhay-cam"], "頭がいい人の口癖": ["tri-tue"],
           "嫌われる人の特徴": ["co-don"]}
    monkeypatch.setattr(ngu_canh.NguCanh, "cum_cua", lambda self, td: list(cum.get(td, [])))
    monkeypatch.setattr(ngu_canh.NguCanh, "cum_da_thu", property(lambda self: {"co-don"}))
    ds = _xep(goc, "A")
    dau = [(d["ma"], d["tin_hieu"].get("cum_chua_thu")) for d in ds[:4]]
    assert dau == [("CHUNG000001", ["nhay-cam"]), ("mmmmmmmmm02", ["tri-tue"]),
                   ("mmmmmmmmm01", None), ("mmmmmmmmm03", None)]
    # kênh đã qua V7 (giai đoạn khác "moi") thì giữ nguyên thứ tự công thức
    ds_v7 = tu_chay.ung_vien_xep_hang(goc, "A", True, set(), cham_vph=lambda _g, _k: [dict(d) for d in VPH],
                                      doc_danh_sach=lambda _g, _k: json.loads(json.dumps(MOT_NUT)))
    assert all("cum_chua_thu" not in d.get("tin_hieu", {}) for d in ds_v7)


def test_luat_chon_kenh_yaml_truoc_ngach(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "luat_chon:", "  - 'chỉ nấu ăn gia đình'", "  - 'không mẹo vặt'")
    assert ngu_canh.dung(goc, "A", co_v7=False).luat_chon == ["chỉ nấu ăn gia đình", "không mẹo vặt"]
    _kenh(goc, "B")
    assert ngu_canh.dung(goc, "B", co_v7=False).luat_chon == []
