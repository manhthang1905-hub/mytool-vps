"""Đường thu số Studio — khoá đúng những chỗ hỏng thật đo ngày 12/10/2026.

Chẩn đoán `workspace/chan-doan/view-giam-2026-10-12.md` (mục 6, D1–D4) và
`nao-vong-hoc-2026-10-12.md` (mục 3):

* bản chụp rỗng 18–39% từ 06/10, > 120h tuổi chỉ 17% có số — gốc: lượt chụp CHỒNG nhau trên một tab
  (khoá `dangChay` không nguyên tử), gói rơi nhầm nhãn, lượt rỗng vẫn được chấm "xong";
* nhãn tuổi sai (thư mục "142h" chụp lúc 94h; một bộ số nằm ở 106h/118h/119h);
* TL2-T7 mất số toàn kênh 07–11/10 mà phiên nào cũng "xong";
* `-vidGiac99a` nằm trong thư mục `vidGiac99a` (trạm cắt '-' đầu mã).

Phần tiện ích (JS) chỉ kiểm được bằng cách ĐỌC mã (như `test_chup_so_lieu_day_du.py`) và kiểm cú
pháp bằng esprima nếu máy có — không chạy được Chrome ở đây.
"""

from __future__ import annotations

import datetime as _dt
import importlib.util
import io
import json
import os
import re
import time
import urllib.request
from pathlib import Path

import pytest

from core import chi_so_ytb as cs
from core import gac_tong
from core.chi_so_ytb import suc_khoe as sk
from core.chi_so_ytb import tram as T

GOC = Path(__file__).resolve().parent.parent
EXT = GOC / "core" / "ytb_extension"


def _nen() -> str:
    """Mã `background.js` BỎ các dòng chú thích nguyên dòng — chú thích kể chuyện bản cũ
    (`while (dangChay) …`, `await st(...)`) không được làm bài kiểm mã đỏ/xanh oan."""
    chu = (EXT / "background.js").read_text(encoding="utf-8")
    return "\n".join(d for d in chu.splitlines() if not d.lstrip().startswith("//"))


def _iso(epoch: float) -> str:
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _ban_chup(kd: Path, vid: str, nhan: str, *, dang: float, luc: float, co_so: bool,
              thong_tin: bool = True, hop_le=None):
    """Một bản chụp đúng hình dạng trạm ghi ra: `_thong-tin.json` (tiện ích ≥ 2.10) + `tong-quan.json`."""
    snap = kd / vid / nhan
    (snap / "raw").mkdir(parents=True, exist_ok=True)
    (snap / "raw" / "goi.json").write_text(json.dumps({"captured_at": _iso(luc)}), encoding="utf-8")
    if thong_tin:
        tt = {"kenh": "K", "id": vid, "label": nhan, "ngay_dang": _iso(dang), "chup_luc": _iso(luc),
              "tuoi_gio_that": round((luc - dang) / 3600, 2)}
        if hop_le is not None:
            tt["hop_le"] = hop_le
        (snap / "_thong-tin.json").write_text(json.dumps(tt), encoding="utf-8")
    tq = {"video_id": vid, "impressions": 1000 if co_so else None, "views": 50 if co_so else None}
    (snap / "tong-quan.json").write_text(json.dumps(tq), encoding="utf-8")
    return snap


# ═══════════════════════════════════════════════════════════════════════════
# D4 — mã video bắt đầu bằng '-' / có '_'
# ═══════════════════════════════════════════════════════════════════════════


class TestMaVideoGiuNguyen:
    def test_an_toan_ma_giu_gach_dau_va_gach_duoi(self):
        for ma in ("-vidGiac99a", "vidGiab3048", "vidGiad1110", "abcdefghij-", "vidGia9181a"):
            assert T.an_toan_ma(ma) == ma
        # `an_toan` (cho nhãn/tên tệp) vẫn cắt như cũ — đó đúng là chỗ đã làm mất dấu '-'.
        assert T.an_toan("-vidGiac99a") == "vidGiac99a"

    def test_an_toan_ma_khong_treo_ra_ngoai(self):
        for xau in ("../../etc/passwd", "..\\..\\Windows", "/tuyet/doi", "C:\\Windows", "..", "", "---"):
            ra = T.an_toan_ma(xau)
            assert "." not in ra and "/" not in ra and "\\" not in ra and ":" not in ra
            assert ra.strip("-_"), ra
        assert T.an_toan_ma("..") == "x" and T.an_toan_ma("") == "x"

    def test_tram_ghi_goi_va_anh_vao_dung_thu_muc_co_gach_dau(self, tmp_path):
        (tmp_path / "CHANNEL" / "TL2-T7" / "prompt").mkdir(parents=True)
        tram = T.Tram(goc=str(tmp_path))
        tram.TRE_TOM_TAT_IM_GIAY = 3600          # không chạy bảng tóm tắt trong bài này
        assert tram.nhan_capture({"kenh": "TL2-T7", "id": "-vidGiac99a", "label": "153h", "ten": "a.json",
                                  "goi": {"url": "x/get_cards", "request": {}, "response": {}}}) == "ok"
        assert tram.nhan_anh({"kenh": "TL2-T7", "id": "-vidGiac99a", "label": "153h", "ten": "x_tong-quan",
                              "anh": "", "chu": "Lượt hiển thị 1.537", "loi": ""}) == "ok"
        cs_ = tmp_path / "CHANNEL" / "TL2-T7" / "chi-so"
        assert (cs_ / "-vidGiac99a" / "153h" / "raw" / "a.json").is_file()
        assert (cs_ / "-vidGiac99a" / "153h" / "anh" / "x_tong-quan.txt").is_file()
        assert not (cs_ / "vidGiac99a").exists()
        tram.tat()

    def test_sua_thu_muc_da_mat_gach_doi_ten_va_gop(self, tmp_path):
        kd = tmp_path / "chi-so"
        dang = time.time() - 200 * 3600
        # Thư mục mất dấu (trạm cũ) — hai mốc; một mốc trùng với thư mục đúng tên đã có.
        _ban_chup(kd, "vidGiac99a", "153h", dang=dang, luc=dang + 153 * 3600, co_so=True)
        snap = _ban_chup(kd, "vidGiac99a", "177h", dang=dang, luc=dang + 177 * 3600, co_so=True)
        for p in (kd / "vidGiac99a").rglob("_thong-tin.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            d["id"] = "-vidGiac99a"
            p.write_text(json.dumps(d), encoding="utf-8")
        assert snap.exists()
        _ban_chup(kd, "-vidGiac99a", "177h", dang=dang, luc=dang + 177 * 3600, co_so=True)
        # Một thư mục 10 ký tự KHÔNG khai mã nào thì không được đụng.
        (kd / "abcdefghij" / "1h").mkdir(parents=True)
        assert sk.va_thu_muc_ma_bi_cat(str(kd)) == 1
        assert (kd / "-vidGiac99a" / "153h" / "tong-quan.json").is_file()
        assert (kd / "-vidGiac99a" / "177h" / "tong-quan.json").is_file()
        assert (kd / "abcdefghij").is_dir()
        # Không xoá dữ liệu: tệp trùng tên ở hai nơi thì bản cũ còn nằm lại nguồn.
        assert (kd / "vidGiac99a" / "177h" / "tong-quan.json").is_file()
        # Bộ đọc (đòi 11 ký tự) giờ thấy video.
        assert "-vidGiac99a" in [os.path.basename(p) for p in sk._thu_muc_video(str(kd))]

    def test_doc_kenh_tu_sua_thu_muc_mat_gach(self, tmp_path):
        kd = tmp_path / "UCkenh"
        dang = time.time() - 100 * 3600
        _ban_chup(kd, "vidGiac99a", "50h", dang=dang, luc=dang + 50 * 3600, co_so=True)
        # Đúng như đĩa thật: gói (và bộ giải mã) biết mã ĐÚNG, chỉ tên thư mục bị cắt.
        for ten, khoa in (("_thong-tin.json", "id"), ("tong-quan.json", "video_id")):
            p = kd / "vidGiac99a" / "50h" / ten
            d = json.loads(p.read_text(encoding="utf-8"))
            d[khoa] = "-vidGiac99a"
            p.write_text(json.dumps(d), encoding="utf-8")
        bg = cs.doc_kenh("UCkenh", goc=str(tmp_path), moc="")
        assert [b.video_id for b in bg] == ["-vidGiac99a"]
        assert (kd / "-vidGiac99a").is_dir() and not (kd / "vidGiac99a").exists()


# ═══════════════════════════════════════════════════════════════════════════
# D1 — bản rỗng phải ghi rõ là KHÔNG hợp lệ
# ═══════════════════════════════════════════════════════════════════════════


class TestBanRongGhiRo:
    def test_tong_quan_rong_ghi_hop_le_false_va_ly_do(self, tmp_path):
        kd = tmp_path / "UCkenh"
        dang = time.time() - 300 * 3600
        snap = _ban_chup(kd, "vidGia685d6", "142h", dang=dang, luc=dang + 142 * 3600, co_so=False,
                         hop_le=False)
        tt = json.loads((snap / "_thong-tin.json").read_text(encoding="utf-8"))
        tt["ly_do"] = "không có gói chỉ số sau 3 lần thử"
        (snap / "_thong-tin.json").write_text(json.dumps(tt), encoding="utf-8")
        _ban_chup(kd, "vidGia685d6", "94h", dang=dang, luc=dang + 94 * 3600, co_so=True)
        bg = cs.doc_kenh("UCkenh", goc=str(tmp_path), moc="")
        assert [b.moc_gio for b in bg] == [94], "bản rỗng không được thành một dòng số"
        q = json.loads((snap / "tong-quan.json").read_text(encoding="utf-8"))
        assert q["hop_le"] is False and "3 lần thử" in q["ly_do_khong_hop_le"]
        assert q["chup_luc"] == tt["chup_luc"] and q["tuoi_gio_that"] == pytest.approx(142, abs=0.1)
        q94 = json.loads((kd / "vidGia685d6" / "94h" / "tong-quan.json").read_text(encoding="utf-8"))
        assert q94["hop_le"] is True

    def test_tram_ghi_gio_nhan_va_bao_khong_hop_le(self, tmp_path):
        os.makedirs(tmp_path / "CHANNEL" / "TL4-T7")
        t = T.Tram(cong=0, goc=str(tmp_path))
        nhat_ky = []
        t._ghi = nhat_ky.append
        t.bat()
        cong = t._may.server_address[1]
        try:
            r = urllib.request.Request(
                f"http://127.0.0.1:{cong}/done",
                data=json.dumps({"kenh": "TL4-T7", "id": "-abcdefghij", "label": "238h", "gio": 238,
                                 "hop_le": False, "ly_do": "không có gói chỉ số sau 3 lần thử",
                                 "chup_luc": "2026-10-11T20:20:14.000Z"}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(r, timeout=5).read()
        finally:
            t.tat()
        p = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "-abcdefghij" / "238h" / "_thong-tin.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["hop_le"] is False and d["tram_nhan_luc"]
        assert any("KHÔNG HỢP LỆ" in x for x in nhat_ky)


# ═══════════════════════════════════════════════════════════════════════════
# Danh sách chụp bù + sức khoẻ
# ═══════════════════════════════════════════════════════════════════════════


class TestChupBu:
    def test_chi_xin_video_thieu_so_moi(self, tmp_path):
        kd = tmp_path / "chi-so"
        bay = time.time()
        d1 = bay - 143 * 3600                       # 143h: có số lúc 94h (49h trước) → THIẾU
        _ban_chup(kd, "vidGia685d6", "94h", dang=d1, luc=d1 + 94 * 3600, co_so=True)
        _ban_chup(kd, "vidGia685d6", "142h", dang=d1, luc=bay - 3600, co_so=False, hop_le=False)
        d2 = bay - 100 * 3600                       # 100h: có số 2h trước → ĐỦ
        _ban_chup(kd, "vidGiaa25e1", "98h", dang=d2, luc=bay - 2 * 3600, co_so=True)
        d3 = bay - 300 * 3600                       # 300h: chưa từng có số → THIẾU, đứng ĐẦU
        _ban_chup(kd, "vidGia5ad92", "286h", dang=d3, luc=bay - 14 * 3600, co_so=False)
        d4 = bay - 10 * 3600                        # 10h: còn non, để báo thức mốc dày lo
        _ban_chup(kd, "vidGia0308d", "6h", dang=d4, luc=d4 + 6 * 3600, co_so=False)
        d5 = bay - 40 * 24 * 3600                   # 40 ngày: quá 31 ngày → thôi
        _ban_chup(kd, "vidGiaff186", "700h", dang=d5, luc=d5 + 700 * 3600, co_so=True)
        ds = sk.can_chup_bu(str(kd), bay_gio=bay)
        assert [d["video_id"] for d in ds] == ["vidGia5ad92", "vidGia685d6"]
        assert "chưa" in ds[0]["ly_do"] and "94h" in ds[1]["ly_do"]

    def test_ngoai_pham_vi_kenh_thi_khong_xin(self, tmp_path):
        kd = tmp_path / "chi-so"
        bay = time.time()
        d = bay - 100 * 3600
        _ban_chup(kd, "vidGia685d6", "50h", dang=d, luc=d + 50 * 3600, co_so=True)
        tuong_lai = (_dt.datetime.now() + _dt.timedelta(days=2)).strftime("%Y-%m-%d")
        assert sk.can_chup_bu(str(kd), bay_gio=bay, moc=tuong_lai) == []
        assert len(sk.can_chup_bu(str(kd), bay_gio=bay, moc="")) == 1

    def test_tram_tra_danh_sach_qua_http(self, tmp_path):
        kd = tmp_path / "CHANNEL" / "TL1-T7" / "chi-so"
        (tmp_path / "CHANNEL" / "TL1-T7" / "prompt").mkdir(parents=True)
        d = time.time() - 143 * 3600
        _ban_chup(kd, "vidGia685d6", "94h", dang=d, luc=d + 94 * 3600, co_so=True)
        t = T.Tram(cong=0, goc=str(tmp_path))
        t.bat()
        cong = t._may.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{cong}/chup-bu?kenh=TL1-T7", timeout=10) as f:
                j = json.loads(f.read().decode("utf-8"))
            with urllib.request.urlopen(f"http://127.0.0.1:{cong}/chup-bu?kenh=KHONG-CO", timeout=10) as f:
                j2 = json.loads(f.read().decode("utf-8"))
        finally:
            t.tat()
        assert [x["video_id"] for x in j["video"]] == ["vidGia685d6"]
        assert j2 == {"video": []}


class TestSucKhoe:
    def test_tuoi_so_va_ti_le_rong_cua_luot_cuoi(self, tmp_path):
        kd = tmp_path / "chi-so"
        bay = _dt.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0).timestamp()
        sang = bay - 3600                            # lượt quét "sáng nay" (11:00 — không vắt qua nửa đêm)
        dang = bay - 200 * 3600
        # 4 video chụp sáng nay: A có số; B rỗng; C rỗng rồi chụp lại trong lượt ra số (không tính rỗng);
        # D có raw chưa giải mã (chưa tính).
        _ban_chup(kd, "AAAAAAAAAAA", "199h", dang=dang, luc=sang, co_so=True)
        _ban_chup(kd, "BBBBBBBBBBB", "199h", dang=dang, luc=sang, co_so=False, hop_le=False)
        _ban_chup(kd, "CCCCCCCCCCC", "199h", dang=dang, luc=sang, co_so=False, hop_le=False)
        _ban_chup(kd, "CCCCCCCCCCC", "200h", dang=dang, luc=sang + 600, co_so=True)
        snap = _ban_chup(kd, "DDDDDDDDDDD", "199h", dang=dang, luc=sang, co_so=False)
        (snap / "tong-quan.json").unlink()
        # Gói lạc nhãn (không có `_thong-tin.json`) không phải một lượt chụp.
        _ban_chup(kd, "EEEEEEEEEEE", "23h", dang=dang, luc=sang, co_so=False, thong_tin=False)
        # Số toàn kênh: bản có số 30 giờ trước, bản hôm nay chỉ có `subs` (không tính).
        for ten, luc, tq in (("kenh-hom-qua", bay - 30 * 3600, {"views": 5, "watch_hours": 1.0}),
                             ("tay-hom-nay", sang, {"subs": 310})):
            k = kd / "kenh" / ten
            (k / "raw").mkdir(parents=True)
            (k / "raw" / "g.json").write_text(json.dumps({"captured_at": _iso(luc)}), encoding="utf-8")
            (k / "tong-quan.json").write_text(json.dumps(tq), encoding="utf-8")
        s = sk.suc_khoe(str(kd), bay_gio=bay)
        assert s["kenh_tuoi_gio"] == pytest.approx(30, abs=0.2)
        assert s["video_tuoi_gio"] == pytest.approx(1 - 600 / 3600, abs=0.1)
        lc = s["luot_cuoi"]
        assert (lc["tong"], lc["rong"], lc["video_rong"]) == (3, 1, ["BBBBBBBBBBB"])


# ═══════════════════════════════════════════════════════════════════════════
# Báo động (người gác → workspace/loi-chay-max.md)
# ═══════════════════════════════════════════════════════════════════════════


def _snap_gac(sk_=None, tu_chay=True):
    return {"tu_chay": tu_chay, "ke_hoach": [], "runs_hom_nay": [], "nhat_ky_hom_nay": [],
            "kiem_dom": None, "chi_so_tuoi_gio": 1.0, "chi_so_suc_khoe": sk_}


def _sk(kenh=2.0, video=2.0, tong=10, rong=0, ngay="2026-10-12"):
    return {"kenh_tuoi_gio": kenh, "co_thu_muc_kenh": True, "video_tuoi_gio": video, "so_video": 10,
            "luot_cuoi": {"ngay": ngay, "tong": tong, "rong": rong,
                          "ti_le_rong": (rong / tong) if tong else None,
                          "video_rong": ["v%010d" % i for i in range(rong)]}}


class TestBaoDongSoLieu:
    def test_so_kenh_cu_qua_24h_thi_bao(self):
        # TL2-T7 thật: số toàn kênh dừng 06/10 — 6 ngày.
        ds = gac_tong._kiem_du_lieu_chi_so("TL2-T7", _snap_gac(_sk(kenh=6 * 24.0)))
        assert [d["loai"] for d in ds] == ["so_lieu_chi_so_cu"]
        assert "TOÀN KÊNH" in ds[0]["chuyen_gi"] and ds[0]["dedupe_khoa"] == "chi_so_cu:TL2-T7"
        assert ds[0]["lap_gio"] == 24.0

    def test_trong_dung_sai_lich_quet_thi_im(self):
        nguong = gac_tong.NGUONG_SO_LIEU_CU_GIO + gac_tong.DUNG_SAI_LICH_QUET_GIO
        assert gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(_sk(kenh=nguong - 0.5, video=25.0))) == []
        ds = gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(_sk(kenh=2.0, video=nguong + 1)))
        assert len(ds) == 1 and "VIDEO" in ds[0]["chuyen_gi"]

    def test_luot_quet_qua_20_phan_tram_rong_thi_bao(self):
        ds = gac_tong._kiem_du_lieu_chi_so("TL1-T7", _snap_gac(_sk(tong=16, rong=12)))
        assert [d["loai"] for d in ds] == ["ban_chup_rong"]
        assert "12/16" in ds[0]["chuyen_gi"] and ds[0]["dedupe_khoa"] == "chi_so_rong:TL1-T7:2026-10-12"
        assert gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(_sk(tong=10, rong=2))) == [], "20% chưa QUÁ 20%"
        assert gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(_sk(tong=2, rong=2))) == [], "mẫu quá nhỏ"

    def test_kenh_ngung_theo_doi_va_thieu_du_lieu_thi_im(self):
        assert gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(None)) == []
        cu = _sk(kenh=30 * 24.0, video=30 * 24.0)
        assert gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(cu, tu_chay=False)) == []
        assert len(gac_tong._kiem_du_lieu_chi_so("K", _snap_gac(cu, tu_chay=True))) == 1

    def test_kiem_su_co_goi_kiem_moi_va_ghi_loi_chay_max(self, tmp_path):
        anh = {"luc": "2026-10-12T09:00:00", "goc": str(tmp_path),
               "kenh": {"TL2-T7": _snap_gac(_sk(kenh=100.0, tong=19, rong=14))}, "may": {}}
        ds = [d for d in gac_tong.kiem_su_co(anh) if d["kenh"] == "TL2-T7"]
        assert {"so_lieu_chi_so_cu", "ban_chup_rong"} <= {d["loai"] for d in ds}
        gac_tong.bao_cao_su_co(str(tmp_path), anh, ds, bay_gio=_dt.datetime(2026, 10, 12, 9, 0),
                               gui_khan=lambda *a, **k: True, gui_thuong=lambda *a, **k: True)
        md = (tmp_path / "workspace" / "loi-chay-max.md").read_text(encoding="utf-8")
        assert "TL2-T7" in md and "không ra số Studio" in md and "TOÀN KÊNH" in md


# ═══════════════════════════════════════════════════════════════════════════
# Agent: phiên chỉ "xong" khi số TOÀN KÊNH hôm nay đã về
# ═══════════════════════════════════════════════════════════════════════════


def _nap_agent():
    spec = importlib.util.spec_from_file_location("vm_agent_thu_so", GOC / "vm" / "agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_phien_chua_xong_khi_thieu_so_toan_kenh_hom_nay(tmp_path, monkeypatch):
    agent = _nap_agent()
    vm = tmp_path / "vm"
    vm.mkdir()
    (tmp_path / "vps.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(agent, "GOC", str(vm))
    monkeypatch.setattr(agent, "_kenh_da_co_video", lambda k: True)
    cs_ = tmp_path / "CHANNEL" / "TL2-T7" / "chi-so"
    cs_.mkdir(parents=True)
    for ten in ("bang-tom-tat.csv", "kenh-theo-ngay.csv"):
        (cs_ / ten).write_text("x", encoding="utf-8")         # bảng VẼ LẠI hôm nay (như TL2 07–11/10)
    (cs_ / "kenh" / "kenh-20261006" / "raw").mkdir(parents=True)
    (cs_ / "kenh" / "kenh-20261006" / "raw" / "g.json").write_text("{}", encoding="utf-8")
    assert agent._du_lieu_kenh_da_ve_hom_nay({}, "TL2-T7") is False
    hom_nay = time.strftime("%Y%m%d")
    (cs_ / "kenh" / ("kenh-" + hom_nay) / "raw").mkdir(parents=True)
    assert agent._du_lieu_kenh_da_ve_hom_nay({}, "TL2-T7") is False, "thư mục rỗng chưa phải có số"
    (cs_ / "kenh" / ("kenh-" + hom_nay) / "raw" / "g.json").write_text("{}", encoding="utf-8")
    assert agent._du_lieu_kenh_da_ve_hom_nay({}, "TL2-T7") is True


# ═══════════════════════════════════════════════════════════════════════════
# Tiện ích (đọc mã) — khoá tab, nhãn, cờ hợp lệ, nhịp ảnh, chụp bù
# ═══════════════════════════════════════════════════════════════════════════


def _than_ham(nen: str, ten: str, dai: int = 6000) -> str:
    i = nen.index(ten)
    return nen[i:i + dai]


class TestTienIch:
    def test_khoa_tab_nguyen_tu_khong_con_co_dangChay(self):
        nen = _nen()
        assert "function xinTab" in nen and "function nhaTab" in nen and "function moiTab" in nen
        assert not re.search(r"\bdangChay\s*=", nen) and "while (dangChay" not in nen
        assert "kenhDangCho" not in nen.replace("`kenhDangCho`", "")
        # Chỉ người cầm mã mới nhả được; giữ quá hạn thì người kế lấy lại.
        nha = _than_ham(nen, "function nhaTab", 400)
        assert "chuTab.ma !== ma" in nha
        assert "HAN_GIU_TAB_MS" in _than_ham(nen, "function moiTab", 600)
        # Mọi đường dùng tab đều xin khoá.
        for ham in ("async function chupVideoThat", "async function chupKenh", "async function khamPha"):
            assert "await xinTab(" in _than_ham(nen, ham, 4500), ham

    def test_nhan_lay_truoc_moi_await_va_phai_dung_video(self):
        nen = _nen()
        than = _than_ham(nen, "async function luuCapture", 2500)
        assert than.index("const nhan = nhanHienTai;") < than.index("await ")
        assert "nhan.videoId === vid" in than
        assert "c.maLink === nhan.maLink" in nen, "chỉ đếm gói của đúng link đang mở"

    def test_chi_danh_dau_xong_khi_goi_cua_dung_video_co_so(self):
        nen = _nen()
        assert "function coSoJoin" in nen and "TOTALS_SUMS" in nen and "'VIDEO'" in nen
        than = _than_ham(nen, "async function chupVideoThat", 9000)
        assert "if (r.coSo) coSo = true;" in than
        assert "hop_le: coSo" in than
        for khoa in ("chup_luc", "tuoi_gio_that", "moc_du_dinh", "ly_do"):
            assert khoa in than, khoa
        assert "if (!coSo) {" in than and than.index("if (!coSo) {") < than.index("luu('daChup'")
        assert "NGHI_THU_LAI_MS" in than, "chưa có số thì phải thử lại, giãn dần"

    def test_nhan_luon_theo_tuoi_that(self):
        than = _than_ham(_nen(), "async function chupVideoThat", 5000)
        assert "const label = tuoi != null ? `${Math.round(tuoi)}h`" in than

    def test_khong_con_bao_thuc_no_ngay_cho_tung_moc_da_qua(self):
        dl = _than_ham(_nen(), "async function datLich", 6000)
        assert "create(ten, { when: Date.now() + 2000 })" not in dl
        assert "`bu|${id}`" in dl and "TOI_DA_LUOT_THU_VIDEO" in dl

    def test_so_kenh_chi_ghi_dau_ngay_khi_co_so(self):
        than = _than_ham(_nen(), "async function chupKenh", 3500)
        assert "if (coSo) await luu('kenh_ngay_cuoi'" in than
        assert "xinTab('chụp kênh', 2)" in than, "kênh xếp hàng ƯU TIÊN trên mọi video"

    def test_anh_co_nhip_va_moi_loi_goi_co_han(self):
        nen = _nen()
        assert "KHOANG_CHUP_ANH_MS" in nen and "MAX_CAPTURE_VISIBLE_TAB_CALLS_PER_SECOND" in nen
        assert "coHan(chrome.scripting.executeScript" in _than_ham(nen, "async function docChu", 200)
        assert "coHan(chrome.scripting.executeScript" in _than_ham(nen, "async function xuatCSV", 200)
        for duong in ("'/capture'", "'/anh'", "'/done'"):
            i = nen.index(duong)
            assert "fetchCoHan(host + " + duong in nen[i - 40:i + len(duong)], duong
        assert "tab không ở trang Studio" in _than_ham(nen, "async function chupAnh", 900)

    def test_hoi_tram_danh_sach_chup_bu_dau_luot(self):
        nen = _nen()
        assert "/chup-bu?kenh=" in nen
        assert "chupBuTuTram()" in _than_ham(nen, "async function batDauQuetNeuCan", 2500)

    def test_cu_phap_hop_le(self):
        esprima = pytest.importorskip("esprima")
        src = _nen().replace("??", "||")
        src = re.sub(r"\?\.(?=[A-Za-z_$\[(])", ".", src)
        esprima.parseScript(src)

    def test_manifest_nang_ban(self):
        mf = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))
        assert tuple(int(x) for x in mf["version"].split(".")) >= (2, 10, 0)
