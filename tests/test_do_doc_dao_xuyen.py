# -*- coding: utf-8 -*-
"""Đo trùng XUYÊN NGÔN NGỮ (`core/do_doc_dao.py`, 16/10/2026): nguồn tiếng Anh → dịch MỘT lần (cache
`0-tu-lieu-ja.txt`) → gióng câu với kịch bản → cùng cổng viết lại. Chữ GIẢ, bản dịch giả, không gọi AI thật."""

from __future__ import annotations

import os
import random
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import do_doc_dao as ddd  # noqa: E402
from core.auto import LuotChay, TrangThaiKhau  # noqa: E402
from core.auto_khau import BoiCanh, _khau_kich_ban  # noqa: E402
from core.kenh import Kenh  # noqa: E402

_KANA = [chr(c) for c in range(0x3041, 0x3094)] + list("日月火水木金土山川田人口目耳手足心生活時間毎朝夜家族友達仕事休息健康料理散歩電車駅店茶本")
_KATA = [chr(c) for c in range(0x30A1, 0x30F4)]


def _cau(r: random.Random) -> str:
    return "".join(r.choice(_KANA + _KATA) for _ in range(r.randint(18, 34))) + "。"


def _van(hat: int, so_cau: int) -> str:
    r = random.Random(hat)
    return "\n".join(_cau(r) for _ in range(so_cau))


def _dich_lai(van: str, hat: int, ti_le_doi: float = 0.1) -> str:
    """"Bản dịch độc lập" của cùng nội dung: mỗi câu đổi ngẫu nhiên ~`ti_le_doi` ký tự (khác chữ, cùng ý)."""
    r = random.Random(hat)
    ra = []
    for dong in van.splitlines():
        ra.append("".join(r.choice(_KANA) if c != "。" and r.random() < ti_le_doi else c for c in dong))
    return "\n".join(ra)


def _anh(hat: int, so_cau: int = 60) -> str:
    r = random.Random(hat)
    tu = ["morning", "closet", "energy", "decision", "simple", "train", "office", "habit", "choose", "clothes", "life"]
    return " ".join(" ".join(r.choice(tu) for _ in range(r.randint(8, 16))).capitalize() + "." for _ in range(so_cau))


def _kiem_qua(_moi, _goc):
    return ""


@pytest.fixture(autouse=True)
def _thao_van_nhip():
    from core import su_co

    cu = su_co.NHIP
    su_co.NHIP = su_co.NhipGoi(moi_phut=1_000_000)
    try:
        yield
    finally:
        su_co.NHIP = cu


# ── 1. GIÓNG CÂU ─────────────────────────────────────────────────────────────

class TestDoXuyen:
    def test_tach_cau_bo_ngat_va_cau_ngan(self):
        ds = ddd.tach_cau("はい。\n今日は朝から電車で仕事へ向かいます。---\n---\nThe morning train is full. Next one.")
        assert [c for c, _ in ds] == ["今日は朝から電車で仕事へ向かいます。", "The morning train is full."]

    def test_ban_dich_tung_cau_diem_cao_viet_lai_that_diem_thap(self):
        kb = _van(1, 60)
        dich = _dich_lai(kb, 2)                                    # cùng câu, đổi 10% chữ
        sat = ddd.do_xuyen(kb, dich)
        assert sat["ti_le"] > 0.9 and sat["so_cau"] == 60 and sat["vi_du"]
        la = ddd.do_xuyen(_van(3, 60), dich)                       # kịch bản khác hẳn
        assert la["ti_le"] < 0.05 and la["so_khop"] < 3
        nua = "\n".join(kb.splitlines()[:30] + _van(4, 30).splitlines())
        assert 0.4 < ddd.do_xuyen(nua, dich)["ti_le"] < 0.6        # nửa bài dịch sát

    def test_cau_bi_tach_doi_van_khop_cap_cau_lien(self):
        r = random.Random(5)
        a, b = _cau(r), _cau(r)
        dich = a + "\n" + b
        kb = a[:-1] + b                                            # kịch bản gộp hai câu nguồn thành một
        assert ddd.do_xuyen(kb, dich)["ti_le"] == 1.0

    def test_rong(self):
        assert ddd.do_xuyen("", _van(6, 5))["ti_le"] == 0.0 and ddd.do_xuyen(_van(6, 5), "")["so_cau"] == 5


# ── 2. CỔNG ──────────────────────────────────────────────────────────────────

class _Dich:
    def __init__(self, tra):
        self.tra, self.goi = tra, 0

    def __call__(self, nguon):
        self.goi += 1
        if isinstance(self.tra, Exception):
            raise self.tra
        return self.tra


class TestCongXuyen:
    def test_tren_nguong_viet_lai_va_cache(self):
        kb, nguon = _van(10, 60), _anh(10)
        dich, moi, goi = _Dich(_dich_lai(kb, 11)), _van(12, 60), []

        def viet(ban, so_do, lan, nhac):
            goi.append(so_do)
            return moi

        with tempfile.TemporaryDirectory() as d:
            ban, bb = ddd.qua_cong(kb, nguon, viet=viet, kiem=_kiem_qua, dich=dich, thu_muc=d)
            assert ban == moi and bb["viet_lai"] and bb["che_do"] == "xuyen" and bb["khac_tieng"]
            assert bb["truoc"] > 0.9 and bb["sau"] < 0.05 and bb["xuyen"]["dich"] == "moi"
            assert "câu của nó là bản dịch sát" in goi[0]["mo_ta"] and goi[0]["vi_du"]
            with open(os.path.join(d, ddd.TEP_DICH), encoding="utf-8") as t:
                assert t.readline().strip() == "#nguon:" + ddd.bam(nguon)
            ban2, bb2 = ddd.qua_cong(kb, nguon, viet=viet, kiem=_kiem_qua, dich=dich, thu_muc=d)
            assert dich.goi == 1 and bb2["xuyen"]["dich"] == "cache"          # lần 2 dùng cache, không gọi AI
            ddd.qua_cong(kb, nguon + " Extra sentence here.", viet=viet, kiem=_kiem_qua, dich=dich, thu_muc=d)
            assert dich.goi == 2                                              # nguồn đổi → dịch lại
            assert ddd.do_xuyen_cuoi(d, kb, nguon + " Extra sentence here.")["ti_le"] > 0.9
            assert ddd.do_xuyen_cuoi(d, kb, nguon) is None                   # cache là của nguồn khác

    def test_duoi_nguong_khong_viet(self):
        kb, nguon = _van(13, 60), _anh(13)
        with tempfile.TemporaryDirectory() as d:
            ban, bb = ddd.qua_cong(kb, nguon, viet=lambda *a: pytest.fail("không được viết lại"), kiem=_kiem_qua,
                                   dich=_Dich(_van(14, 60)), thu_muc=d)
        assert ban == kb and bb["che_do"] == "xuyen" and bb["truoc"] <= ddd.NGUONG_XUYEN_VIET_LAI and not bb["lan"]

    def test_van_cao_thu_lan_hai_roi_canh_bao_di_tiep(self):
        kb, nguon = _van(15, 60), _anh(15)
        dong = kb.splitlines()
        lan_goi = []

        def viet(ban, so_do, lan, nhac):
            lan_goi.append(lan)
            return "\n".join(dong[:45 - 5 * lan] + _van(16 + lan, 15 + 5 * lan).splitlines())   # bớt dần, vẫn > chặn

        ban, bb = ddd.qua_cong(kb, nguon, viet=viet, kiem=_kiem_qua, dich=_Dich(kb))
        assert lan_goi == [1, 2] and bb["viet_lai"] and bb["sau"] > ddd.NGUONG_XUYEN_CHAN and bb["canh_bao"]
        assert "câu dịch sát" in bb["canh_bao"] and bb["xuyen"]["sau"] == bb["sau"]

    @pytest.mark.parametrize("tra", [RuntimeError("Claude Max hết hạn mức"), "", "短い"])
    def test_dich_hong_khong_chan(self, tra):
        kb, nguon = _van(20, 40), _anh(20)
        with tempfile.TemporaryDirectory() as d:
            ban, bb = ddd.qua_cong(kb, nguon, viet=lambda *a: pytest.fail("không đo được thì không viết"),
                                   kiem=_kiem_qua, dich=_Dich(tra), thu_muc=d)
            assert not os.path.exists(os.path.join(d, ddd.TEP_DICH))
        assert ban == kb and "dịch nguồn hỏng" in bb["ghi_chu"] and bb["xuyen"]["dich"].startswith("loi")

    def test_lenh_dung_khi_dang_dich_van_xuyen_qua(self):
        class Dung(Exception):
            pass

        with pytest.raises(Dung):
            ddd.qua_cong(_van(23, 30), _anh(23), viet=lambda *a: "x", kiem=_kiem_qua, dich=_Dich(Dung()),
                         khong_nuot=(Dung,))

    def test_khong_co_ham_dich_giu_nep_cu(self):
        ban, bb = ddd.qua_cong(_van(21, 30), _anh(21), viet=lambda *a: "x", kiem=_kiem_qua)
        assert "không viết lại" in bb["ghi_chu"] and "xuyen" not in bb and bb["che_do"] == "ky_tu"

    def test_kenh_tat_chi_do_xuyen(self):
        kb = _van(22, 40)
        ban, bb = ddd.qua_cong(kb, _anh(22), viet=None, kiem=_kiem_qua, dich=_Dich(kb))
        assert ban == kb and bb["truoc"] == 1.0 and "tắt" in bb["ghi_chu"]


# ── 3. TRONG KHÂU KỊCH BẢN (đường dây thật, AI giả) ─────────────────────────

class _AI:
    def __init__(self, kb, ban_dich, viet_lai):
        self.kb, self.ban_dich, self.viet_lai, self.lan = kb, ban_dich, viet_lai, []

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.lan.append((khoa, loi_nhac))
        if "doc-dao:dich" in khoa:
            if isinstance(self.ban_dich, Exception):
                raise self.ban_dich
            return self.ban_dich
        if "doc-dao" in khoa:
            return self.viet_lai
        if "3-sua.md" in khoa:
            return loi_nhac[len("rà soát "):]
        return self.kb


def _chay(d, ai, nguon):
    with open(os.path.join(d, "0-tu-lieu.txt"), "w", encoding="utf-8") as t:
        t.write(nguon)
    k = Kenh(ma="T-DX", ngon_ngu="ja", voice_id="v", phut_muc_tieu=0, ky_tu_moi_phut=300,
             prompt={"2-viet.md": "viết <<COMPETITOR_TRANSCRIPT>>", "3-sua.md": "rà soát <<DRAFT>>"})
    bc = BoiCanh(goc=".", kenh=k, goi_chat=ai, on_log=lambda _s: None, ngu=lambda _g: None,
                 tai_anh=lambda *_a, **_k: b"")
    luot = LuotChay(ma_kenh=k.ma, ma_luot="T01", thu_muc=d, dau_vao={"tieu_de": "テスト動画", "chu_bia": "テスト"})
    _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))
    with open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as t:
        return t.read().strip(), ddd.doc_bien_ban(d)


class TestTrongKhau:
    def test_nguon_anh_dich_mot_lan_roi_viet_lai(self):
        kb, moi = _van(30, 60), _van(31, 60)
        ai = _AI(kb, _dich_lai(kb, 32), moi)
        with tempfile.TemporaryDirectory() as d:
            ra, bb = _chay(d, ai, _anh(30))
            assert os.path.isfile(os.path.join(d, ddd.TEP_DICH))
            ho_so = ddd.tom_tat_ho_so(d)
        assert ra == moi.strip() and bb["che_do"] == "xuyen" and bb["viet_lai"] and bb["truoc"] > 0.9
        assert bb["xuyen"]["cuoi"] < 0.05 and ho_so["che_do"] == "xuyen" and ho_so["xuyen"] < 0.05
        assert sum("doc-dao:dich" in x[0] for x in ai.lan) == 1
        ln = next(x[1] for x in ai.lan if "doc-dao:v1" in x[0])
        assert "bản dịch sát từng câu" in ln and "<<" not in ln

    def test_dich_hong_luot_van_ra_bai(self):
        kb = _van(33, 60)
        ai = _AI(kb, RuntimeError("Claude Max hỏng, ví cạn"), "")
        with tempfile.TemporaryDirectory() as d:
            ra, bb = _chay(d, ai, _anh(33))
        assert ra == kb.strip() and "dịch nguồn hỏng" in bb["ghi_chu"] and not bb["viet_lai"]
        assert not any("doc-dao:v" in x[0] for x in ai.lan)


# ── 4. BÁO CÁO ───────────────────────────────────────────────────────────────

def test_bao_cao_xuyen_cache_ngoai_projects_va_tran_goi():
    with tempfile.TemporaryDirectory() as goc, tempfile.TemporaryDirectory() as cache:
        kb = _van(40, 40)
        for ten, nguon in (("0001", _anh(41)), ("0002", _anh(42)), ("0003", _van(43, 40))):
            d = os.path.join(goc, "PROJECTS", "AUTO", "KB", ten)
            os.makedirs(d)
            for tep, chu in (("0-tu-lieu.txt", nguon), ("1-kich-ban.txt", kb)):
                with open(os.path.join(d, tep), "w", encoding="utf-8") as t:
                    t.write(chu)
        dich = _Dich(_dich_lai(kb, 44))
        xu = ddd._XuyenBaoCao(cache, dich, con_lai=1)  # noqa: SLF001
        ds = {x["luot"]: x for x in ddd.bang_luot(goc, "KB", 10, xu)}
        assert dich.goi == 1 and xu.da_goi == 1
        assert ds["0001"]["cau_sat"] is None and ds["0001"]["dich"] == "chưa dịch"          # hết trần gọi
        assert ds["0002"]["cau_sat"] > 0.9 and ds["0002"]["dich"] == "mới"
        assert ds["0003"]["cau_sat"] is not None and not ds["0003"]["khac_tieng"]
        assert os.listdir(cache) == ["KB-0002.txt"]
        for ten in ("0001", "0002"):
            assert ddd.TEP_DICH not in os.listdir(os.path.join(goc, "PROJECTS", "AUTO", "KB", ten))
        chu = ddd.bao_cao(goc, ["KB"], 10, xuyen=ddd._XuyenBaoCao(cache))  # noqa: SLF001
        assert "câu sát" in chu and "(bản dịch: cache)" in chu and "câu dịch sát: trung vị" in chu
        assert ddd.main(["--goc", goc, "--kenh", "KB", "--xuyen", "--cache-dich", cache]) == 0
