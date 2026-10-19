"""D18 ĐO TỪ LẦN QUÉT SẴN CÓ (19/10/2026) — `vm/nuoi_trang_chu.py: do_tu_quet / quet_moi_nhat / kiem_quet` + skill D18
+ ô Tự kiểm "lịch quét trang chủ". Không Chrome, không mạng, LLM giả."""

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path

import pytest

GOC_KHO = Path(__file__).resolve().parent.parent
VM = GOC_KHO / "vm"
for _d in (str(GOC_KHO), str(VM)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import nuoi_trang_chu as n  # noqa: E402

BAY = time.mktime((2026, 10, 19, 9, 0, 0, 0, 0, -1))     # đồng hồ cố định của bài kiểm
COT = ("Lúc quét", "Vị trí", "Kệ", "Mã video", "Tiêu đề", "Kênh", "Link kênh", "Lượt xem", "Đăng", "Dài", "Short",
       "Bị loại", "Lượt tải")


def _ma(p, i):
    return "{0}{1:09d}".format(p, i)          # 11 ký tự


def dong(luc, so, p="aa", tu=1, buoc=1, tieu=None, **them):
    """`so` dòng của MỘT lần quét: vị trí tu, tu+buoc, …; tiêu đề mặc định "ngach <i>"."""
    ra = []
    for k in range(so):
        vt = tu + k * buoc
        x = dict.fromkeys(COT, "")
        x.update({"Lúc quét": luc, "Vị trí": str(vt), "Mã video": _ma(p, vt), "Tiêu đề": (tieu or "ngach {0}").format(vt),
                  "Kênh": "kenh" + str(vt % 7), "Lượt tải": "1"})
        x.update(them)
        ra.append(x)
    return ra


def ghi_csv(goc, k, ds):
    d = Path(goc) / "CHANNEL" / k / "nghien-cuu"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "trang-chu.csv", "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(COT))
        w.writeheader()
        w.writerows(ds)
    t = time.time() + len(ds)                  # mtime đổi chắc chắn giữa các lần ghi trong cùng giây
    os.utime(d / "trang-chu.csv", (t, t))


def them_csv(goc, k, ds):
    d = Path(goc) / "CHANNEL" / k / "nghien-cuu" / "trang-chu.csv"
    cu = list(csv.DictReader(open(d, encoding="utf-8-sig")))
    ghi_csv(goc, k, cu + ds)


class LLM:
    """Giả `goi(prompt)`: nhãn theo tiêu đề — "ngach" → dung_ngach, "tamly" → dung_chu_de, còn lại lac_de."""

    def __init__(self):
        self.goi = 0
        self.o = 0

    def __call__(self, prompt):
        self.goi += 1
        phan = prompt.split("Danh sách (số|tiêu đề|kênh):\n", 1)[1].split("\nChỉ trả JSON", 1)[0]
        ra = []
        for d in phan.splitlines():
            i, tieu = d.split("|")[:2]
            self.o += 1
            nhan = "dung_ngach" if "ngach" in tieu else ("dung_chu_de" if "tamly" in tieu else "lac_de")
            ra.append({"i": int(i), "nhan": nhan, "tam_ly": nhan != "lac_de"})
        return json.dumps(ra)


@pytest.fixture
def goc(tmp_path, monkeypatch):
    g = str(tmp_path)
    thu = tmp_path / "vm" / "logs" / "nuoi-trang-chu"
    thu.mkdir(parents=True)
    monkeypatch.setattr(n, "THU_MUC_SO", str(thu))
    monkeypatch.setattr(n, "THU_MUC_KHOA", None)
    monkeypatch.setattr(n, "GOC_TOOL", g)
    monkeypatch.setattr(n, "ghi_nao", lambda *a, **k: None)
    monkeypatch.setattr(n, "bao_dong_duy_tri", lambda *a, **k: None)      # không bao giờ gửi báo động thật từ bài kiểm
    for k in ("K", "R", "S"):
        d = tmp_path / "CHANNEL" / k
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text('ten: "Kenh — tam ly"\nngon_ngu: "en"\ntu_chay: true\nnuoi_trang_chu: false\n',
                                     encoding="utf-8")
        (thu / (k + ".json")).write_text(json.dumps({"kenh": k, "trang_thai": "dat", "da_tat_yaml": "x", "lan_do": [
            {"luc": "2026-10-04 15:00", "n": 30, "pct_chu_de": 96.7, "pct_ngach": 40.0, "dem": {}, "dat": True}]}),
            encoding="utf-8")
    return g


# ── nhận lần quét của CHÍNH kênh (bỏ dòng gộp nhóm) ─────────────────────────
def test_nhan_lan_quet_cua_kenh_bo_dong_gop_nhom():
    ds = (dong("2026-10-19 02:50", 40) + dong("2026-10-19 02:51", 10, tu=41, **{"Lượt tải": "3"})
          + dong("2026-10-19 05:16", 12, p="bb", tu=3, buoc=7))           # dòng GỘP từ lần quét kênh anh em: vị trí thưa
    lan = n.cac_lan_quet(ds)
    assert [(l, len(x)) for l, x in lan] == [("2026-10-19 02:50", 50), ("2026-10-19 05:16", 12)]
    assert n.la_quet_cua_kenh(lan[0][1]) and not n.la_quet_cua_kenh(lan[1][1])
    q = n.quet_moi_nhat("K", dong=ds)
    assert q["luc"] == "2026-10-19 02:50" and q["tong"] == 50 and len(q["o"]) == n.SO_O_DO
    assert [x["vi_tri"] for x in q["o"]][:3] == [1, 2, 3]
    assert n.quet_moi_nhat("K", dong=dong("2026-10-19 05:16", 12, p="bb", tu=3, buoc=7)) == {}


def test_loc_o_hop_le_khong_bo_phan_quyet_lien_quan():
    ds = dong("2026-10-19 02:50", 45)
    ds[0]["Short"] = "x"
    ds[1]["Bị loại"] = "short"
    ds[2]["Kệ"] = "ニュース速報"
    ds[3]["Mã video"] = "ngan"
    ds[4]["Tiêu đề"] = ""
    ds[5]["Mã video"] = ds[6]["Mã video"]                      # trùng
    ds[7]["Loại"] = "quang_cao"
    ds[8]["Bị loại"] = "không đúng tiếng"                       # phán quyết LIÊN QUAN của mắt cào: VẪN vào thước
    ds[9]["Bị loại"] = "từ loại trừ"
    q = n.quet_moi_nhat("K", dong=ds)
    assert q["bo"] == {"short": 2, "ke": 1, "ma_hong": 1, "khong_ten": 1, "trung": 1, "quang_cao": 1}
    ids = [x["id"] for x in q["o"]]
    assert len(ids) == n.SO_O_DO and len(set(ids)) == n.SO_O_DO
    assert ds[8]["Mã video"] in ids and ds[9]["Mã video"] in ids and ds[0]["Mã video"] not in ids
    assert n.ly_do_bo_o(ds[8]) == "" and n.ly_do_bo_o(ds[2]) == "ke"


# ── phát hiện lần quét mới + cache theo mã video ─────────────────────────────
def test_lan_quet_moi_va_cache_tai_dung(goc):
    ghi_csv(goc, "K", dong("2026-10-18 02:50", 35))
    bay = n._luc_so("2026-10-19 09:00")
    q = n.kiem_quet("K", goc, luc=bay)
    assert q["moi"] and q["luc_quet"] == "2026-10-18 02:50" and not q["cu"]
    llm, dong_log = LLM(), []
    assert n.do_tu_quet("K", dong_log.append, goi=llm, goc=goc, luc=BAY) == 0
    assert llm.goi == 2 and llm.o == 60                         # hai lượt bầu độc lập, khớp → không cần lượt ba
    dt = n.doc_duy_tri("K")
    assert dt["luc_quet_do"] == "2026-10-18 02:50" and dt["quet_cuoi"]["pct_chu_de"] == 100.0
    assert dt["quet_cuoi"]["pct_ngach"] == 100.0 and dt["che_do"] == "duy_tri"
    so = n.doc_so("K")
    assert so["lan_do"][-1]["nguon"] == "quet" and so["lan_do"][-1]["luc"] == "2026-10-18 02:50"
    assert not n.kiem_quet("K", goc, luc=bay)["moi"]
    # tệp không có lần quét mới → không gọi LLM
    assert n.do_tu_quet("K", dong_log.append, goi=llm, goc=goc, luc=BAY) == n.MA_KHONG_CAN and llm.goi == 2
    # lần quét mới cùng các ô cũ → đo lại, 0 lượt LLM (cache)
    them_csv(goc, "K", dong("2026-10-19 02:50", 35))
    assert n.kiem_quet("K", goc, luc=bay)["moi"]
    assert n.do_tu_quet("K", dong_log.append, goi=llm, goc=goc, luc=BAY) == 0 and llm.goi == 2
    assert n.doc_duy_tri("K")["quet_cuoi"]["o_moi"] == 0
    # mtime không đổi → kiem_quet dùng bản ghi trong sổ duy trì, không cần đọc tệp
    dt = n.doc_duy_tri("K")
    assert dt["quet_mtime"] == os.path.getmtime(n.duong_trang_chu("K", goc)) and dt["luc_quet_moi"] == "2026-10-19 02:50"


def test_lan_quet_qua_it_o_ghi_nhan_khong_tinh(goc):
    ghi_csv(goc, "K", dong("2026-10-18 02:50", 32, Short="x"))
    llm = LLM()
    assert n.do_tu_quet("K", lambda s: None, goi=llm, goc=goc, luc=BAY) == 0 and llm.goi == 0
    dt = n.doc_duy_tri("K")
    assert dt["quet_cuoi"]["khong_tinh"] and not n.kiem_quet("K", goc, dt, BAY)["moi"]
    assert len(n.doc_so("K")["lan_do"]) == 1                   # chỉ lần đo phiên cũ, lần quét không tính


def test_llm_loi_thi_thu_lai_luot_sau(goc):
    ghi_csv(goc, "K", dong("2026-10-18 02:50", 35))
    assert n.do_tu_quet("K", lambda s: None, goi=lambda p: "không phải JSON", goc=goc, luc=BAY) == 1
    assert n.kiem_quet("K", goc, luc=BAY)["moi"]                # chưa ghi luc_quet_do → lượt sau thử lại


# ── quyết định theo ngưỡng ──────────────────────────────────────────────────
def test_duoi_90_nuoi_lai_hai_lan_quet_dat_lien_ve_duy_tri(goc):
    llm = LLM()
    # lần quét 1: 24 ô ngách + 6 lạc đề = 80% → nuôi lại
    ds = dong("2026-10-16 02:50", 24, p="a1") + dong("2026-10-16 02:50", 11, p="x1", tu=25, tieu="nau an {0}")
    ghi_csv(goc, "K", ds)
    assert n.do_tu_quet("K", lambda s: None, goi=llm, goc=goc, luc=n._luc_so("2026-10-16 09:00")) == 0
    dt = n.doc_duy_tri("K")
    assert dt["che_do"] == "nuoi_lai" and dt["quet_cuoi"]["pct_chu_de"] == 80.0
    assert "K" in n.cac_kenh_nuoi_lai()                          # agent.chay_nuoi_trang_chu sẽ mở phiên nuôi như cũ
    # lần quét 2 đạt (100%) → mới 1 lần đạt, vẫn nuôi lại
    them_csv(goc, "K", dong("2026-10-17 02:50", 35, p="a2"))
    assert n.do_tu_quet("K", lambda s: None, goi=llm, goc=goc, luc=n._luc_so("2026-10-17 09:00")) == 0
    dt = n.doc_duy_tri("K")
    assert dt["che_do"] == "nuoi_lai" and dt["dat_lien"] == 1
    # lần quét 3 đạt → 2 lần quét đạt liền → về duy trì
    them_csv(goc, "K", dong("2026-10-18 02:50", 35, p="a3"))
    assert n.do_tu_quet("K", lambda s: None, goi=llm, goc=goc, luc=n._luc_so("2026-10-18 09:00")) == 0
    dt = n.doc_duy_tri("K")
    assert dt["che_do"] == "duy_tri" and dt["lich_su"][-1]["su_kien"] == "ve_duy_tri"


def test_nuoi_lai_qua_7_ngay_van_bao_dong(goc, monkeypatch):
    bao = []
    monkeypatch.setattr(n, "bao_dong_duy_tri", lambda kenh, so, dt, loai, ghi: bao.append(loai))
    thu = Path(n.THU_MUC_SO)
    (thu / "K.duy-tri.json").write_text(json.dumps({"kenh": "K", "che_do": "nuoi_lai", "tu_luc": time.time() - 8 * 86400,
                                                    "phien_nuoi_lai": 9}), encoding="utf-8")
    ghi_csv(goc, "K", dong("2026-10-18 02:50", 24, p="a1") + dong("2026-10-18 02:50", 11, p="x1", tu=25, tieu="game {0}"))
    assert n.do_tu_quet("K", lambda s: None, goi=LLM(), goc=goc, luc=BAY) == 0
    assert bao == ["khong_hieu_qua"]


# ── dữ liệu quét cũ > 3 ngày: báo MỘT lần ở Tự kiểm ─────────────────────────
def test_quet_cu_bao_mot_lan_o_tu_kiem(goc):
    from core import tu_kiem as tk
    ghi_csv(goc, "K", dong("2026-10-14 02:50", 35))
    assert n.do_tu_quet("K", lambda s: None, goi=LLM(), goc=goc, luc=n._luc_so("2026-10-15 09:00")) == 0
    bay = _dt.datetime(2026, 10, 19, 9, 0)
    t = n.tom_tat_duy_tri("K", goc, bay.timestamp())
    assert t["quet_cu"] and not t["quet_chan"] and t["tt"] == "cho" and "lịch quét hỏng" in t["cau"]
    K = tk.BoiCanh(goc, bay=bay, tai=lambda u: (-1, b""), kenh_ds=["K"], so={})
    ds = [m for m in tk.kiem_trang_chu(K) if m["khoa"].startswith("trang_chu_quet:")]
    assert len(ds) == 1 and ds[0]["tt"] == tk.HONG and "2026-10-14 02:50" in ds[0]["bang_chung"]
    # đã báo hôm qua (cùng lần quét cũ) → hôm nay chỉ CHỜ, không báo lại
    K2 = tk.BoiCanh(goc, bay=bay, tai=lambda u: (-1, b""), kenh_ds=["K"],
                    so={"muc": {ds[0]["khoa"]: {"lan_dau_hong": "2026-10-18T09:00:00", "tt": tk.MO}}})
    ds2 = [m for m in tk.kiem_trang_chu(K2) if m["khoa"].startswith("trang_chu_quet:")]
    assert ds2[0]["tt"] == tk.CHO and "đã báo 2026-10-18" in ds2[0]["bang_chung"]
    # còn mới → không có ô lịch quét
    K3 = tk.BoiCanh(goc, bay=_dt.datetime(2026, 10, 16, 9, 0), tai=lambda u: (-1, b""), kenh_ds=["K"], so={})
    assert not [m for m in tk.kiem_trang_chu(K3) if m["khoa"].startswith("trang_chu_quet:")]


def test_quet_cu_vi_cong_tin_cay_khong_phai_lich_hong(goc):
    from core import tu_kiem as tk
    (Path(n.THU_MUC_SO) / "K.json").write_text(json.dumps({"kenh": "K", "trang_thai": "dat", "da_tat_yaml": "x", "lan_do": [
        {"luc": "2026-10-13 15:00", "n": 30, "pct_chu_de": 80.0, "pct_ngach": 40.0, "dem": {}, "dat": False}]}),
        encoding="utf-8")                                       # phiên nuôi đo 80% → agent ngừng cào trang chủ
    ds = dong("2026-10-14 02:50", 24, p="a1") + dong("2026-10-14 02:50", 11, p="x1", tu=25, tieu="nhac {0}")
    ghi_csv(goc, "K", ds)
    assert n.do_tu_quet("K", lambda s: None, goi=LLM(), goc=goc, luc=n._luc_so("2026-10-15 09:00")) == 0
    bay = _dt.datetime(2026, 10, 19, 9, 0)
    t = n.tom_tat_duy_tri("K", goc, bay.timestamp())
    assert t["quet_cu"] and "tạm không cào" in t["quet_chan"] and "lịch quét hỏng" not in t["ly_do_han"]
    K = tk.BoiCanh(goc, bay=bay, tai=lambda u: (-1, b""), kenh_ds=["K"], so={})
    assert not [m for m in tk.kiem_trang_chu(K) if m["khoa"].startswith("trang_chu_quet:")]


# ── bỏ kênh theo dữ liệu: trả kho / tu_chay: false ──────────────────────────
def test_bo_kenh_tra_kho_va_tu_chay_false(goc, monkeypatch):
    from core import ky_nang as kn
    from core import tu_kiem as tk
    (Path(goc) / "CHANNEL" / "R" / "kenh.yaml").write_text(
        'ngon_ngu: "en"\ntu_chay: false\nnuoi_trang_chu: false\ntra_kho: "2026-10-19"\nthay_boi: "R-K2"\n', encoding="utf-8")
    (Path(goc) / "CHANNEL" / "S" / "kenh.yaml").write_text('ngon_ngu: "en"\ntu_chay: false   # chủ dừng\n', encoding="utf-8")
    for k in ("K", "R", "S"):
        ghi_csv(goc, k, dong("2026-10-18 02:50", 35))
    assert "trả kho 2026-10-19" in n.bo_qua_kenh("R", goc) and "R-K2" in n.bo_qua_kenh("R", goc)
    assert "tu_chay: false" in n.bo_qua_kenh("S", goc) and n.bo_qua_kenh("K", goc) == ""
    monkeypatch.setattr(kn, "_gio", lambda: _dt.datetime(2026, 10, 18, 10, 0))
    assert kn.d_duy_tri_trang_chu(goc, "K")[0] is True
    for k in ("R", "S"):
        dung, ly = kn.d_duy_tri_trang_chu(goc, k)
        assert not dung and ly == n.bo_qua_kenh(k, goc)
        assert kn.k_duy_tri_trang_chu(goc, k)[0] == kn.KHONG
        assert n.do_tu_quet(k, lambda s: None, goi=LLM(), goc=goc, luc=BAY) == n.MA_KHONG_CAN
        assert n.tom_tat_duy_tri(k, goc)["tt"] == ""
    K = tk.BoiCanh(goc, bay=_dt.datetime(2026, 10, 25, 9, 0), tai=lambda u: (-1, b""), kenh_ds=["K", "R", "S"], so={})
    assert {m["kenh"] for m in tk.kiem_trang_chu(K)} == {"K"}
    # kênh trả kho đang ở nuoi_lai trong sổ máy → agent KHÔNG mở phiên nuôi
    (Path(n.THU_MUC_SO) / "R.duy-tri.json").write_text(json.dumps({"kenh": "R", "che_do": "nuoi_lai"}), encoding="utf-8")
    ra, ly = n.kenh_den_luot(time.mktime((2026, 10, 19, 12, 0, 0, 0, 0, -1)), goc=goc, ram=16.0, nang_ban=False)
    assert "R" not in ra and "trả kho" in ly["R"]


# ── D18 nhẹ, không Chrome ───────────────────────────────────────────────────
def test_d18_nhe_khong_mo_chrome(goc, monkeypatch):
    from core import ky_nang as kn
    from core import ky_nang_tu as knt

    def cam(*a, **k):
        raise AssertionError("D18 không được mở Chrome / DOM")
    for ten in ("chay_do", "_nap_agent", "doc_o_trang_chu", "tra_ngon_ngu", "Tab"):
        monkeypatch.setattr(n, ten, cam)
    k = kn.theo_ma("D18")
    assert not k.nang and k.tu_ap and k.mot_kenh and k.han_phut <= 15 and "D18" not in knt.UU_TIEN_NANG
    assert k.lenh.endswith("--tu-quet") and "--do" not in k.lenh
    assert k.chay(goc, "K")[-3:] == ["--kenh", "K", "--tu-quet"] and "--do" not in k.chay(goc, "K")
    bay = _dt.datetime.now()
    monkeypatch.setattr(kn, "_gio", lambda: bay.replace(hour=3, minute=0))   # 03:00 — khung cấm Chrome không còn chặn
    luc_q = (bay - _dt.timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")
    ghi_csv(goc, "K", dong(luc_q, 35))
    dung, ly = kn.d_duy_tri_trang_chu(goc, "K")
    assert dung and luc_q + " chưa đo" in ly
    monkeypatch.setattr(n, "tao_llm", lambda: LLM())
    assert n.main(["--kenh", "K", "--tu-quet"]) == 0
    assert kn.d_duy_tri_trang_chu(goc, "K") == (False, "đã đo lần quét {0} — chờ lần quét kế".format(luc_q))
    assert kn.k_duy_tri_trang_chu(goc, "K")[0] == kn.DAT


def test_phien_nuoi_dang_giu_so_thi_hoan(goc, monkeypatch):
    ghi_csv(goc, "K", dong("2026-10-18 02:50", 35))
    monkeypatch.setattr(n, "cac_kenh_dang_nuoi", lambda thu_muc=None: ["K"])
    llm = LLM()
    assert n.do_tu_quet("K", lambda s: None, goi=llm, goc=goc, luc=BAY) == n.MA_HOAN and llm.goi == 0
    assert n.kiem_quet("K", goc, luc=BAY)["moi"]


def test_lan_do_tu_quet_khong_dong_cong_quet_cua_agent(tmp_path):
    """agent.trang_chu_tin_cay: lần đo `nguon: quet` (D18) không đóng cổng cào — đóng thì hết lần quét mới để đo."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("agent_tu_quet", GOC_KHO / "vm" / "agent.py")
    ag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ag)
    ag.GOC = str(tmp_path / "vm")
    thu = tmp_path / "vm" / "logs" / "nuoi-trang-chu"
    thu.mkdir(parents=True)
    (tmp_path / "CHANNEL" / "A").mkdir(parents=True)
    (tmp_path / "CHANNEL" / "A" / "kenh.yaml").write_text("nuoi_trang_chu: false\n", encoding="utf-8")

    def so(*lan):
        (thu / "A.json").write_text(json.dumps({"lan_do": [{"pct_chu_de": p, "nguon": ng} for p, ng in lan]}), encoding="utf-8")
    so((96.7, "phien"), (70.0, "quet"))
    assert ag.trang_chu_tin_cay("A")[0] is True                 # lần quét 70% không đóng cổng
    so((96.7, "phien"), (70.0, "quet"), (80.0, "phien"))
    assert ag.trang_chu_tin_cay("A")[0] is False                # phiên nuôi đo 80% → đóng như cũ
    so((70.0, "quet"),)
    assert ag.trang_chu_tin_cay("A")[0] is False                # chưa có lần đo phiên nào → như cũ (chưa đo)


def test_lan_quet_cu_qua_khong_do(goc):
    """Lần quét mới nhất đã quá 3 ngày (vd trang-chu.csv chép từ kênh gốc lúc tạo kênh) không phải trang chủ hiện tại."""
    ghi_csv(goc, "K", dong("2026-10-05 05:16", 35))
    q = n.kiem_quet("K", goc, luc=BAY)
    assert q["cu"] and not q["moi"]
    llm = LLM()
    assert n.do_tu_quet("K", lambda s: None, goi=llm, goc=goc, luc=BAY) == n.MA_KHONG_CAN and llm.goi == 0
