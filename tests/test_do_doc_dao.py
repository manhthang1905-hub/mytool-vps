# -*- coding: utf-8 -*-
"""Cổng độ độc đáo kịch bản (`core/do_doc_dao.py`, 15/10/2026): phép đo chép nguồn + cổng viết lại trong khâu
kịch bản. Chữ tiếng Nhật GIẢ (sinh ngẫu nhiên có hạt), không gọi AI thật, không ghi vào gốc tool."""

from __future__ import annotations

import json
import os
import random
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import do_doc_dao as ddd  # noqa: E402
from core.auto import LuotChay, TrangThaiKhau  # noqa: E402
from core.auto_khau import BoiCanh, _do_doc, _ghi_doc_dao_cuoi, _khau_kich_ban  # noqa: E402
from core.kenh import Kenh  # noqa: E402

_KANA = [chr(c) for c in range(0x3041, 0x3094)] + list("日月火水木金土山川田人口目耳手足心生活時間毎朝夜家族友達仕事休息健康料理散歩電車駅店茶本")


def _chu(hat: int, n: int) -> str:
    """Văn tiếng Nhật giả ~`n` ký tự: câu ngẫu nhiên, có 、。 và xuống dòng. Hai hạt khác nhau ≈ không trùng."""
    r = random.Random(hat)
    ra, dai = [], 0
    while dai < n:
        cau = "".join(r.choice(_KANA) for _ in range(r.randint(12, 30))) + r.choice("。、！？")
        ra.append(cau + ("\n" if r.random() < 0.3 else ""))
        dai += len(cau)
    return "".join(ra)


@pytest.fixture(autouse=True)
def _thao_van_nhip():
    """Van nhịp gọi chung của tiến trình — mở rộng cho bài kiểm (cùng nết `test_kich_ban_sach_truoc_voice`)."""
    from core import su_co

    cu = su_co.NHIP
    su_co.NHIP = su_co.NhipGoi(moi_phut=1_000_000)
    try:
        yield
    finally:
        su_co.NHIP = cu


# ── 1. PHÉP ĐO ───────────────────────────────────────────────────────────────

class TestDoTrung:
    def test_giong_het_la_1_khac_han_la_0(self):
        a, b = _chu(1, 3000), _chu(2, 3000)
        assert ddd.do_trung(a, a)["ti_le"] == 1.0
        do = ddd.do_trung(a, b)
        assert do["ti_le"] == 0.0 and do["so_doan"] == 0 and do["vi_du"] == []

    def test_chep_mot_nua_ra_khoang_mot_nua(self):
        nguon = _chu(3, 4000)
        kb = nguon[:2000] + _chu(4, 2000)
        assert 0.4 < ddd.do_trung(kb, nguon)["ti_le"] < 0.6

    def test_bo_dau_cau_khoang_trang_the_va_nfkc(self):
        nguon = "今日は、いい天気ですね。散歩に行きましょう！ＡＢＣ体操も忘れずに。"
        kb = "[sighs] 今日は いい天気ですね\n散歩に 行きましょう…abc体操も、忘れずに"
        assert ddd.do_trung(kb, nguon)["ti_le"] == 1.0

    def test_doan_chep_in_bang_chu_goc_dai_nhat_truoc(self):
        nguon = _chu(5, 3000)
        dai, ngan = nguon[500:800], nguon[1500:1530]
        kb = _chu(6, 600) + dai + _chu(7, 600) + ngan + _chu(8, 600)
        do = ddd.do_trung(kb, nguon)
        assert do["so_doan"] == 2
        assert do["dai_nhat"] >= 250
        # đoạn dài nhất đứng đầu, in lại bằng chữ của kịch bản (có dấu câu), cắt trần `TRAN_DOAN`
        dau = do["vi_du"][0].rstrip("…").replace(" / ", "")
        assert dau and dau[:40] in dai.replace("\n", "")

    def test_nguon_khac_tieng_gan_co(self):
        assert ddd.do_trung(_chu(9, 2000), "This is an English transcript about daily life. " * 40)["khac_tieng"]

    def test_nhanh(self):
        import time

        a, b = _chu(10, 20000), _chu(11, 20000)
        t = time.time()
        ddd.do_trung(a, b)
        assert time.time() - t < 1.0


# ── 2. CỔNG (thuần, AI giả) ─────────────────────────────────────────────────

def _kiem_qua(_moi, _goc):
    return ""


class TestQuaCong:
    def test_duoi_nguong_khong_goi_ai(self):
        nguon = _chu(20, 3000)
        goi = []
        ban, bb = ddd.qua_cong(_chu(21, 3000), nguon, viet=lambda *a: goi.append(a) or "x", kiem=_kiem_qua)
        assert not goi and not bb["viet_lai"] and bb["lan"] == []

    def test_tren_nguong_goi_ai_va_giu_ban_it_chep_hon(self):
        nguon = _chu(22, 3000)
        moi = _chu(23, 3000)
        goi = []

        def viet(ban, so_do, lan, nhac):
            goi.append((lan, so_do["ti_le"], len(so_do["vi_du"])))
            return moi

        ban, bb = ddd.qua_cong(nguon, nguon, viet=viet, kiem=_kiem_qua)
        assert ban == moi and bb["viet_lai"] and bb["truoc"] == 1.0 and bb["sau"] < 0.05
        assert len(goi) == 1 and goi[0][2] > 0          # đoạn chép được đưa cho AI
        assert not bb["canh_bao"]

    def test_ban_viet_lai_chep_hon_thi_bo(self):
        nguon = _chu(24, 3000)
        kb = nguon[:900] + _chu(25, 2100)                  # ~30% chép
        ban, bb = ddd.qua_cong(kb, nguon, viet=lambda *a: nguon, kiem=_kiem_qua)
        assert ban == kb and not bb["viet_lai"]
        assert "không bớt chép" in bb["lan"][0]["ly_do"]

    def test_van_cao_thi_thu_them_mot_lan_roi_canh_bao_va_di_tiep(self):
        nguon = _chu(26, 3000)
        lan_goi = []

        def viet(ban, so_do, lan, nhac):
            lan_goi.append((lan, nhac))
            return nguon[:2000] + _chu(27 + lan, 1000)       # vẫn ~66% chép, nhưng ít hơn 100%

        ban, bb = ddd.qua_cong(nguon, nguon, viet=viet, kiem=_kiem_qua)
        assert [x[0] for x in lan_goi] == [1, 2] and lan_goi[1][1]   # lần 2 có lời nhắc lại
        assert bb["viet_lai"] and bb["sau"] > ddd.NGUONG_CHAN and bb["canh_bao"]

    def test_ai_hong_khong_nem_loi(self):
        nguon = _chu(30, 3000)

        def viet(*_a):
            raise RuntimeError("máy chủ quá tải")

        ban, bb = ddd.qua_cong(nguon, nguon, viet=viet, kiem=_kiem_qua)
        assert ban == nguon and len(bb["lan"]) == 2 and "lỗi gọi AI" in bb["lan"][0]["ly_do"] and bb["canh_bao"]

    def test_lenh_dung_van_xuyen_qua(self):
        class Dung(Exception):
            pass

        def viet(*_a):
            raise Dung()

        with pytest.raises(Dung):
            ddd.qua_cong(_chu(31, 2000), _chu(31, 2000), viet=viet, kiem=_kiem_qua, khong_nuot=(Dung,))

    def test_kenh_tat_chi_do(self):
        nguon = _chu(32, 3000)
        ban, bb = ddd.qua_cong(nguon, nguon, viet=None, kiem=_kiem_qua)
        assert ban == nguon and bb["truoc"] == 1.0 and not bb["lan"] and "tắt" in bb["ghi_chu"]

    def test_bat_theo_kenh(self):
        assert ddd.bat(Kenh(ma="A")) and not ddd.bat(Kenh(ma="A", doc_dao=False))

        class K:
            doc_dao = "false"

        assert not ddd.bat(K())

    def test_doc_kenh_doc_khoa_yaml(self):
        from core.kenh import doc_kenh

        with tempfile.TemporaryDirectory() as goc:
            os.makedirs(os.path.join(goc, "CHANNEL", "KX"))
            with open(os.path.join(goc, "CHANNEL", "KX", "kenh.yaml"), "w", encoding="utf-8") as t:
                t.write('ma: "KX"\ndoc_dao: false\n')
            assert doc_kenh(goc, "KX").doc_dao is False
            os.makedirs(os.path.join(goc, "CHANNEL", "KY"))
            with open(os.path.join(goc, "CHANNEL", "KY", "kenh.yaml"), "w", encoding="utf-8") as t:
                t.write('ma: "KY"\n')
            assert doc_kenh(goc, "KY").doc_dao is True


# ── 3. TRONG KHÂU KỊCH BẢN (đường dây thật, AI giả) ─────────────────────────

class _AI:
    """`2-viet` chép nguyên nguồn; lời nhắc viết lại (khoá `doc-dao`) trả `viet_lai(loi_nhac)`; `3-sua` trả nguyên bài."""

    def __init__(self, nguon, viet_lai, ban_viet=None):
        self.nguon, self.viet_lai, self.lan = nguon, viet_lai, []
        self.ban_viet = nguon if ban_viet is None else ban_viet

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.lan.append((khoa, loi_nhac))
        if "doc-dao" in khoa:
            return self.viet_lai(loi_nhac)
        if "3-sua.md" in khoa:
            return loi_nhac[len("rà soát "):]
        return self.ban_viet


def _kenh(**kw):
    mac = dict(ma="T-DD", ngon_ngu="ja", voice_id="v", phut_muc_tieu=10, ky_tu_moi_phut=300,
               prompt={"2-viet.md": "viết <<COMPETITOR_TRANSCRIPT>>", "3-sua.md": "rà soát <<DRAFT>>"})
    mac.update(kw)
    return Kenh(**mac)


def _chay(d, ai, kenh=None):
    with open(os.path.join(d, "0-tu-lieu.txt"), "w", encoding="utf-8") as t:
        t.write(ai.nguon)
    log = []
    bc = BoiCanh(goc=".", kenh=kenh or _kenh(), goi_chat=ai, on_log=log.append, ngu=lambda _g: None,
                 tai_anh=lambda *_a, **_k: b"")
    luot = LuotChay(ma_kenh=bc.kenh.ma, ma_luot="T01", thu_muc=d, dau_vao={"tieu_de": "テスト動画", "chu_bia": "テスト"})
    _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))
    with open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as t:
        kb = t.read().strip()
    return kb, ddd.doc_bien_ban(d), log


class TestTrongKhauKichBan:
    def test_cong_viet_lai_truoc_ra_soat_va_ghi_bien_ban(self):
        nguon, moi = _chu(40, 4500), _chu(41, 3000)
        ai = _AI(nguon, lambda _ln: moi, ban_viet=nguon[:3000])
        with tempfile.TemporaryDirectory() as d:
            kb, bb, log = _chay(d, ai)
            assert not os.path.exists(os.path.join(d, ddd.TEP_NHAP))       # nháp dọn sau khi ghi bài
        assert kb == moi.strip()
        assert bb["truoc"] == 1.0 and bb["sau"] < 0.05 and bb["cuoi"] < 0.05 and bb["viet_lai"]
        assert bb["bat"] is True and bb["bam_vao"] and bb["luot"] == "T01"
        khoa = [x[0] for x in ai.lan]
        i_dd = next(i for i, x in enumerate(khoa) if "doc-dao" in x)
        i_sua = next(i for i, x in enumerate(khoa) if "3-sua.md" in x)
        assert i_dd < i_sua                                               # cổng chạy TRƯỚC rà soát
        assert ai.lan[i_sua][1].endswith(moi.strip())                     # rà soát nhận bản đã qua cổng
        ln = ai.lan[i_dd][1]
        assert "TUYỆT ĐỐI KHÔNG DÙNG LẠI" in ln and "「" in ln
        assert nguon[3600:3640] not in ln                                  # KHÔNG đưa bản gốc vào lời nhắc viết lại
        assert any("độ độc đáo" in x for x in log)

    def test_ban_viet_lai_qua_ngan_bi_loai(self):
        nguon = _chu(42, 3000)
        ai = _AI(nguon, lambda _ln: _chu(43, 1400))                        # hụt ~50% — ngoài dung sai 15%
        with tempfile.TemporaryDirectory() as d:
            kb, bb, _log = _chay(d, ai)
        assert _do_doc(kb) >= 2500 and not bb["viet_lai"]
        assert bb["lan"] and all(not x["nhan"] and "độ dài" in x["ly_do"] for x in bb["lan"])
        assert bb["cuoi"] == 1.0 and bb["canh_bao"]                        # cảnh báo, nhưng KHÔNG chặn lượt

    def test_ban_viet_lai_lech_20_phan_tram_van_nhan(self):
        """18/10/2026 (TL1-T7/0033): bản hết chép lệch độ dài 17–21% từng bị loại → giữ bản chép 46%. Nay cổng độc đáo
        chịu lệch tới max(2 × dung sai, 30%)."""
        nguon = _chu(47, 3000)
        ai = _AI(nguon, lambda _ln: _chu(48, 2400))                        # −20% — ngoài 15% của kênh, trong 30%
        with tempfile.TemporaryDirectory() as d:
            kb, bb, _log = _chay(d, ai)
        assert bb["viet_lai"] and bb["cuoi"] < 0.05 and not bb["canh_bao"]

    def test_kenh_tat_khong_goi_viet_lai(self):
        nguon = _chu(44, 3000)
        ai = _AI(nguon, lambda _ln: pytest.fail("kênh tắt mà vẫn gọi viết lại"))
        with tempfile.TemporaryDirectory() as d:
            kb, bb, _log = _chay(d, ai, kenh=_kenh(doc_dao=False))
        assert not any("doc-dao" in x[0] for x in ai.lan)
        assert bb["bat"] is False and bb["truoc"] == 1.0 and bb["cuoi"] == 1.0

    def test_chay_tiep_dung_lai_ban_da_viet(self):
        nguon, moi = _chu(45, 3000), _chu(46, 3000)
        ai = _AI(nguon, lambda _ln: moi)
        with tempfile.TemporaryDirectory() as d:
            _chay(d, ai)
            # giả lượt đứt sau cổng: xoá bài + rà soát, giữ biên bản + nháp cổng
            os.remove(os.path.join(d, "1-kich-ban.txt"))
            with open(os.path.join(d, ddd.TEP_NHAP), "w", encoding="utf-8") as t:
                t.write(moi)
            ai2 = _AI(nguon, lambda _ln: pytest.fail("chạy tiếp mà gọi viết lại lần nữa"))
            kb, bb, _log = _chay(d, ai2)
        assert kb == moi.strip() and bb["viet_lai"]

    def test_ai_hong_thi_di_tiep_va_lan_sau_thu_lai(self):
        nguon, moi = _chu(47, 3000), _chu(48, 3000)

        def hong(_ln):
            raise RuntimeError("máy chủ quá tải")

        with tempfile.TemporaryDirectory() as d:
            kb, bb, _log = _chay(d, _AI(nguon, hong))                     # cổng hỏng: lượt vẫn ra bài
            assert kb == nguon.strip() and bb["lan"] and bb["lan"][0].get("loi") and bb["canh_bao"]
            os.remove(os.path.join(d, "1-kich-ban.txt"))
            kb, bb, _log = _chay(d, _AI(nguon, lambda _ln: moi))          # chạy lại: thử lại, không "dùng lại" bản hỏng
        assert kb == moi.strip() and bb["viet_lai"]


# ── 4. NÃO + HỒ SƠ + BÁO CÁO ────────────────────────────────────────────────

def test_ghi_nao_chi_cho_luot_that():
    from core.nao_bo_phan.kho import mo

    with tempfile.TemporaryDirectory() as goc:
        mo(goc).close()                                                    # não đã có
        d = os.path.join(goc, "PROJECTS", "AUTO", "KN", "0007")
        os.makedirs(d)
        nguon = _chu(50, 3000)
        bc = BoiCanh(goc=goc, kenh=_kenh(ma="KN"), goi_chat=lambda *a, **k: "", on_log=lambda _s: None)
        luot = LuotChay(ma_kenh="KN", ma_luot="0007", thu_muc=d, dau_vao={})
        _ghi_doc_dao_cuoi(bc, luot, bc.kenh, nguon[:1500] + _chu(51, 1500), nguon)
        _ghi_doc_dao_cuoi(bc, luot, bc.kenh, nguon[:1500] + _chu(51, 1500), nguon)   # lần 2: trùng khoá, bỏ qua
        con = sqlite3.connect(os.path.join(goc, "nao", "bo-phan.db"))
        dong = con.execute("SELECT bo_phan, loai, kenh, ma_goi, so FROM su_kien").fetchall()
        con.close()
        assert len(dong) == 1 and dong[0][:4] == ("kich-ban", "do", "KN", "KN-0007")
        assert 0.4 < json.loads(dong[0][4])["trung_cuoi"] < 0.6
        assert 0.4 < ddd.doc_bien_ban(d)["cuoi"] < 0.6
        # thư mục lượt NGOÀI PROJECTS/AUTO (bài kiểm, công cụ dev) → không ghi não
        with tempfile.TemporaryDirectory() as ngoai:
            _ghi_doc_dao_cuoi(bc, LuotChay(ma_kenh="KN", ma_luot="0008", thu_muc=ngoai, dau_vao={}), bc.kenh,
                              nguon, nguon)
        con = sqlite3.connect(os.path.join(goc, "nao", "bo-phan.db"))
        assert con.execute("SELECT COUNT(*) FROM su_kien").fetchone()[0] == 1
        con.close()


def test_ho_so_video_co_muc_chep():
    from core import ho_so_video as hv

    with tempfile.TemporaryDirectory() as goc:
        d = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
        os.makedirs(d)
        nguon = _chu(60, 3000)
        for ten, chu in (("0-tu-lieu.txt", nguon), ("1-kich-ban.txt", nguon[:1500] + _chu(61, 1500))):
            with open(os.path.join(d, ten), "w", encoding="utf-8") as t:
                t.write(chu)
        hs = hv._xay_ho_so(goc, "KH", d, "KH-0001")  # noqa: SLF001 — lượt cũ chưa có biên bản: đo lại
        assert hs["doc_dao"]["nguon"] == "do_lai" and 0.4 < hs["trung_nguon"] < 0.6
        ddd.ghi_bien_ban(d, {"truoc": 0.9, "sau": 0.1, "cuoi": 0.08, "lan": [{"lan": 1}], "viet_lai": True})
        hs = hv._xay_ho_so(goc, "KH", d, "KH-0001")  # noqa: SLF001
        assert hs["trung_nguon"] == 0.08 and hs["doc_dao"]["viet_lai"] and hs["doc_dao"]["so_lan"] == 1
        assert hv._khung_ho_so("KH", "KH-0002")["trung_nguon"] is None  # noqa: SLF001


def test_bao_cao_chi_doc():
    with tempfile.TemporaryDirectory() as goc:
        nguon = _chu(70, 3000)
        for i, kb in enumerate((nguon, _chu(71, 3000), nguon[:1500] + _chu(72, 1500)), 1):
            d = os.path.join(goc, "PROJECTS", "AUTO", "KB", "{0:04d}".format(i))
            os.makedirs(d)
            for ten, chu in (("0-tu-lieu.txt", nguon), ("1-kich-ban.txt", kb)):
                with open(os.path.join(d, ten), "w", encoding="utf-8") as t:
                    t.write(chu)
        truoc = sorted(os.listdir(os.path.join(goc, "PROJECTS", "AUTO", "KB", "0001")))
        ds = ddd.bang_luot(goc, "KB", n=2)
        assert [x["luot"] for x in ds] == ["0002", "0003"]
        chu = ddd.bao_cao(goc, ["KB"], n=20)
        assert "100%" in chu and "trung vị" in chu and "≥60%: 1" in chu
        assert sorted(os.listdir(os.path.join(goc, "PROJECTS", "AUTO", "KB", "0001"))) == truoc  # không ghi gì
        assert ddd.main(["--goc", goc, "--kenh", "KB", "--n", "5"]) == 0
