# -*- coding: utf-8 -*-
"""13/10/2026 — luật chủ: Claude Max hết token hoặc lỗi → viết bằng ShopAPI.

Ca gốc đêm 13/10: thuê bao chạm hạn mức TUẦN ("You've hit your weekly limit · resets Oct 18, 11pm", kèm 429) — bị
đọc thành nghẽn tạm, 1,5 giờ thử lại Opus đã cạn, không tụt bậc, không lùi ví.
"""
import pytest

from core import goi_van_ban as gvb
from core import viet_max as vm

KHONG_NGU = {"ngu": lambda _giay: None}


class LoiCli(Exception):
    def __init__(self, chu):
        super().__init__(chu)
        self.chi_tiet = (chu, "")


TUAN = LoiCli('{"is_error":true,"result":"You\'ve hit your weekly limit · resets Oct 18, 11pm",'
              '"api_error_status":429,"error":"rate_limit_error"}')


def test_nhan_ra_han_muc_tuan_du_kem_429():
    assert vm.la_het_han_muc(TUAN)
    assert vm.ly_do_tut_bac(TUAN) == "han_muc"
    assert not vm.la_het_han_muc(LoiCli("429 Too Many Requests — overloaded"))


def _goi(tmp_path, viet, **kw):
    goc = str(tmp_path)
    return vm.dung_goi_chat_max(goc, viet=viet, kiem_mang=lambda: True, lui_vi=True, **KHONG_NGU, **kw)


def test_hong_hai_lan_thi_lui_vi(tmp_path):
    dem = []

    def viet(*_a, **_k):
        dem.append(1)
        raise LoiCli("Claude Code thoát lỗi (mã 1): lỗi lẻ")
    with pytest.raises(vm.MaxKhongDung) as e:
        _goi(tmp_path, viet)("x")
    assert not e.value.can and len(dem) == vm.SO_LAN_TRUOC_LUI_VI


def test_can_ca_thang_thi_lui_vi_ngay_khong_doi(tmp_path):
    dem = []

    def viet(*_a, **_k):
        dem.append(1)
        raise TUAN
    with pytest.raises(vm.MaxKhongDung) as e:
        _goi(tmp_path, viet)("x")
    assert e.value.can and len(dem) == len(vm.thang_mo_hinh(str(tmp_path)))     # mỗi bậc một lần, không đợi
    dem.clear()
    with pytest.raises(vm.MaxKhongDung) as e2:                 # lượt sau: thang đang khoá → lùi ngay, không gọi CLI
        _goi(tmp_path, viet)("y")
    assert e2.value.can and dem == []


def test_tat_lui_vi_thi_hanh_vi_cu(tmp_path):
    def viet(*_a, **_k):
        raise LoiCli("Claude Code thoát lỗi (mã 1): lỗi lẻ")
    goi = vm.dung_goi_chat_max(str(tmp_path), viet=viet, kiem_mang=lambda: True, lui_vi=False, so_lan=2,
                               **KHONG_NGU)
    with pytest.raises(RuntimeError) as e:
        goi("x")
    assert not isinstance(e.value, vm.MaxKhongDung) and "KHÔNG chuyển sang ví" in str(e.value)


class MayChuGia:
    def __init__(self):
        self.goi = 0

    def request(self, _method, _path, *, json=None, idempotency_key=None, **_k):
        self.goi += 1
        return {"choices": [{"message": {"content": "viết bằng ví"}}]}


def test_goi_van_ban_max_khong_dung_thi_viet_bang_shopapi(monkeypatch):
    monkeypatch.setattr(vm, "duong_viet_chu", lambda goc="": ("max", ""))

    def max_hong(*_a, **_k):
        raise vm.MaxKhongDung("thuê bao Claude Max đang cạn hạn mức", can=True)
    monkeypatch.setattr(vm, "goi_tin_nhan_max", max_hong)
    may, nk = MayChuGia(), []
    ra = gvb.goi_van_ban(may, [{"role": "user", "content": "x"}], on_log=nk.append, **KHONG_NGU)
    assert ra == "viết bằng ví" and may.goi == 1
    assert any("viết bằng ShopAPI" in d for d in nk)


def test_goi_van_ban_khong_co_client_thi_van_bao_loi_max(monkeypatch):
    monkeypatch.setattr(vm, "duong_viet_chu", lambda goc="": ("max", ""))

    def max_hong(*_a, **_k):
        raise vm.MaxKhongDung("hỏng", can=False)
    monkeypatch.setattr(vm, "goi_tin_nhan_max", max_hong)
    with pytest.raises(vm.MaxKhongDung):
        gvb.goi_van_ban(None, [{"role": "user", "content": "x"}], **KHONG_NGU)
