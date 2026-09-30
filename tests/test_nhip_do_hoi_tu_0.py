"""Nhà máy khởi động lại (trần 0 → 200) thì nhịp phải LEO NHANH lại — 30/09/2026.

Sự cố 16:25 ngày 30/09: worker nhà máy khởi động lại, trần ảnh máy chủ báo
0 → 8 → 200 trong ~1,5 phút. Tool từng tự cắt một lần trong buổi (tắt
`_leo_nhanh`), nên sau khi trần hồi nó bỏ ngoài tai lời mời `cho_trong` và chỉ
bò +1 mỗi cửa sổ — cả máy kẹt ~1 job ảnh. Xem ShopAPI ghi chú cùng ngày.
"""
from __future__ import annotations

import core  # noqa: F401 — nhập trước để tìm thấy SDK trong _sdk/
from shopapi._nhip_do import CHO_KHI_DUNG, NhipDo  # noqa: E402


class _DongHo:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _qua_quang_dung_va_tham_do(nhip, dh):
    dh.t += CHO_KHI_DUNG + 1
    assert nhip.cho_phep() == 1, "hết quãng dừng phải thăm dò MỘT job"
    nhip.xong()                        # job thăm dò được nhận


def test_tran_hoi_tu_0_len_200_thi_nhip_leo_nhanh():
    dh = _DongHo()
    nhip = NhipDo(_dong_ho=dh)
    nhip.dat_tran(0)
    _qua_quang_dung_va_tham_do(nhip, dh)
    nhip.dat_tran(200)
    nhip.moi_vao(cho_trong=200)
    assert nhip.cho_phep() >= 100, "trần hồi từ 0 phải leo nhanh, không đứng ở 1"


def test_da_tung_tu_cat_roi_nha_may_dung_van_leo_nhanh_lai():
    dh = _DongHo()
    nhip = NhipDo(_dong_ho=dh)
    nhip.dat_tran(200)
    nhip.ghi_nhan_tu_choi(429, None, None)   # tự cắt một lần trong buổi
    nhip.dat_tran(0)                         # nhà máy khởi động lại
    _qua_quang_dung_va_tham_do(nhip, dh)
    nhip.dat_tran(200)
    nhip.moi_vao(cho_trong=200)
    assert nhip.cho_phep() >= 100


def test_bao_nhip_doc_ma_o_status():
    """SDK đặt mã HTTP ở `.status`; `_bao_nhip` phải đọc được để 429 tới vòng dò."""
    from core.jobs import KIND_IMAGE, JobManager

    class _Loi(Exception):
        status = 429
        code = "rate_limited"
        retry_after = None

    class _NhipGhi:
        def __init__(self):
            self.goi = []

        def ghi_nhan_tu_choi(self, status, code, retry_after):
            self.goi.append(status)

    jm = JobManager.__new__(JobManager)
    ghi = _NhipGhi()
    jm._nhip = {KIND_IMAGE: ghi}
    jm._tu_do_nhip = True
    jm._bao_nhip(KIND_IMAGE, _Loi())
    assert ghi.goi == [429]
