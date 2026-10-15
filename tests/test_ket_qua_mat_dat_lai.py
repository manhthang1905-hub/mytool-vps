"""`/v1/jobs/{id}/download` trả 400/404/410 = kết quả job KHÔNG CÒN → đặt lại bằng khoá mới.

Đo 11/10/2026: sau ~6 giờ ShopAPI tắt TTS, lượt nhặt lại gửi đúng khoá cũ → cổng phát lại job cũ →
`/download` trả 400 → `LoiTaiVe(400)` → `CHET` → khâu giọng đọc dừng; ba lần nhặt lại y hệt → trần
L3 bỏ HẲN lượt dở. Tải lại đúng job ấy không bao giờ khỏi; chỉ job MỚI (khoá mới) mới có tệp.

Không gọi mạng, không tốn tiền: mọi lời gọi ShopAPI đều là đồ giả.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import auto_khau, su_co, tu_chay  # noqa: E402
from core.su_co import DAU_KET_QUA_MAT, LoiTaiVe  # noqa: E402


class _BoiCanhGia:
    def __init__(self):
        self.dong = []

    def ghi(self, d):
        self.dong.append(d)

    def kiem_dung(self):
        return None


def _tai_gia(monkeypatch, ma_loi):
    """`_tai_ket_qua` giả: lần thứ i ném `LoiTaiVe(ma_loi[i])` (0 = tải xong, ghi tệp)."""
    da_tai = []

    def tai(bc, goi, chi_so, dich):
        da_tai.append(goi.get("id"))
        ma = ma_loi[len(da_tai) - 1] if len(da_tai) <= len(ma_loi) else 0
        if ma:
            raise LoiTaiVe("tải kết quả hỏng ({0}) cho job {1}".format(ma, goi.get("id")), ma)
        with open(dich, "wb") as t:
            t.write(b"ok")
        return dich

    monkeypatch.setattr(auto_khau, "_tai_ket_qua", tai)
    return da_tai


def test_400_thi_dat_lai_bang_khoa_moi_roi_tai_duoc(monkeypatch, tmp_path):
    da_tai = _tai_gia(monkeypatch, [400])
    hau_to = []

    def dat_lai(h):
        hau_to.append(h)
        return {"id": "job_moi"}

    bc = _BoiCanhGia()
    dich = str(tmp_path / "1.mp3")
    assert auto_khau._tai_ket_qua_dat_lai(bc, {"id": "job_cu"}, dich, dat_lai, "đoạn 5") == dich
    assert da_tai == ["job_cu", "job_moi"]
    assert len(hau_to) == 1 and hau_to[0].startswith(":mat:k1-")
    assert any("không còn giữ kết quả job job_cu" in d and "(1/2)" in d for d in bc.dong), bc.dong


@pytest.mark.parametrize("ma", [404, 410])
def test_404_410_cung_dat_lai(monkeypatch, tmp_path, ma):
    _tai_gia(monkeypatch, [ma])
    goi_lai = []
    auto_khau._tai_ket_qua_dat_lai(_BoiCanhGia(), {"id": "a"}, str(tmp_path / "x"),
                                   lambda h: goi_lai.append(h) or {"id": "b"})
    assert len(goi_lai) == 1


def test_het_hai_lan_dat_lai_thi_nem_cau_phia_may_chu(monkeypatch, tmp_path):
    """Tối đa 2 lần đặt lại (cùng trần "nhận việc rồi bỏ đó") — không vòng vô hạn."""
    da_tai = _tai_gia(monkeypatch, [400, 400, 400, 400, 400])
    hau_to = []

    def dat_lai(h):
        hau_to.append(h)
        return {"id": "job_{0}".format(len(hau_to))}

    with pytest.raises(LoiTaiVe) as bat:
        auto_khau._tai_ket_qua_dat_lai(_BoiCanhGia(), {"id": "job_0"}, str(tmp_path / "x"),
                                       dat_lai, "đoạn 5")
    assert len(hau_to) == auto_khau.SO_DAT_LAI_KET_QUA_MAT == 2
    assert len(da_tai) == 3
    assert len(set(hau_to)) == 2, "mỗi lần đặt lại một khoá khác"
    cau = str(bat.value)
    assert cau.startswith(DAU_KET_QUA_MAT) and bat.value.status == 400
    # Lần nhặt sau đọc lại CÂU LỖI từ sổ (không còn ngoại lệ gốc): phải ra phía máy chủ.
    assert su_co.phan_loai(RuntimeError(cau)) == su_co.TAM_NGHI
    assert su_co.phan_loai(bat.value) == su_co.TAM_NGHI
    assert tu_chay._dung_vi_phia_shopapi({"san_xuat": {"loi": "giong-doc: " + cau}})


def test_cau_phia_may_chu_mien_tran_L3(monkeypatch, tmp_path):
    """Đúng lỗi của TL1-T7/0025: 3 lần nhặt lại mà câu dừng là kết quả mất → KHÔNG bỏ hẳn lượt."""
    import datetime as dt

    _tai_gia(monkeypatch, [400, 400, 400])
    with pytest.raises(LoiTaiVe) as bat:
        auto_khau._tai_ket_qua_dat_lai(_BoiCanhGia(), {"id": "j"}, str(tmp_path / "x"),
                                       lambda h: {"id": "j" + h})
    run = {"san_xuat": {"loi": str(bat.value)},
           "phuc_hoi": {"so_lan": tu_chay.TRAN_SO_LAN_PHUC_HOI}}
    hom_nay = dt.date.today()
    ly_do = tu_chay._ly_do_vuot_tran_phuc_hoi(run, hom_nay, hom_nay.isoformat())
    assert "chạm trần" not in ly_do, ly_do
    # Đối chứng: câu cũ ("tải kết quả hỏng (400)") vẫn chạm trần như trước.
    run_cu = {"san_xuat": {"loi": "tải kết quả hỏng (400) cho job job_x"},
              "phuc_hoi": {"so_lan": tu_chay.TRAN_SO_LAN_PHUC_HOI}}
    assert "chạm trần" in tu_chay._ly_do_vuot_tran_phuc_hoi(run_cu, hom_nay, hom_nay.isoformat())


@pytest.mark.parametrize("ma", [500, 503, 403])
def test_ma_khac_khong_dat_lai(monkeypatch, tmp_path, ma):
    """5xx là trục trặc tạm (`_tai_ket_qua` tự kiên nhẫn); 403 không phải "kết quả mất"."""
    _tai_gia(monkeypatch, [ma])
    with pytest.raises(LoiTaiVe) as bat:
        auto_khau._tai_ket_qua_dat_lai(_BoiCanhGia(), {"id": "a"}, str(tmp_path / "x"),
                                       lambda h: pytest.fail("không được đặt lại"))
    assert bat.value.status == ma
    assert not str(bat.value).startswith(DAU_KET_QUA_MAT)


def test_5xx_van_kien_nhan_trong_tai_ket_qua(monkeypatch):
    """Hành vi cũ giữ nguyên: 500 thoáng qua thì đợi rồi tải lại ĐÚNG job, không đặt lại."""
    lan = {"n": 0}

    def mot_lan(bc, goi, chi_so, dich):
        lan["n"] += 1
        if lan["n"] == 1:
            raise LoiTaiVe("tải kết quả hỏng (500) cho job job_x", 500)
        return dich

    import functools

    monkeypatch.setattr(auto_khau, "_tai_ket_qua_mot_lan", mot_lan)
    ngu = []  # đừng ngủ thật — `goi_kien_nhan` nhận hàm ngủ qua tham số
    monkeypatch.setattr(auto_khau, "_tai_ket_qua",
                        functools.partial(auto_khau._tai_ket_qua, ngu=ngu.append))
    assert auto_khau._tai_ket_qua_dat_lai(_BoiCanhGia(), {"id": "job_x"}, "a.mp3",
                                          lambda h: pytest.fail("không được đặt lại")) == "a.mp3"
    assert lan["n"] == 2 and ngu


def test_duoi_khoa_khong_trung_khoa_thoat_ket():
    """Vòng "nhận việc rồi bỏ đó" dùng `khoa_thoat_ket(1)` trong CÙNG phút → trùng là cổng phát lại
    đúng job đã mất kết quả."""
    for lan in (1, 2):
        assert auto_khau.khoa_dat_lai_ket_qua_mat(lan) != auto_khau.khoa_thoat_ket(lan)
        assert auto_khau.khoa_dat_lai_ket_qua_mat(lan).endswith(auto_khau.khoa_thoat_ket(lan))


# ── Đường thật: khâu giọng đọc (đúng chỗ TL1-T7/0025 dừng) ───────────────────


def _dung_khau_giong_doc(monkeypatch, tmp_path, ma_loi):
    d = tmp_path / "0025"
    d.mkdir()
    (d / "1-kich-ban.txt").write_text("Một câu kịch bản ngắn để đọc.", encoding="utf-8")
    luot = SimpleNamespace(thu_muc=str(d), ma_luot="0025", ma_kenh="x")
    kenh = SimpleNamespace(voice_id="v1", giay_nghi_phan=0.0, ngon_ngu="")
    nhat_ky = []
    bc = SimpleNamespace(kenh=kenh, ghi=nhat_ky.append, kiem_dung=lambda: None, nhip_hoi=1.0,
                         ffmpeg="", client=SimpleNamespace(tts=SimpleNamespace(create=None)))
    khoa_da_gui = []

    def tao_job(_bc, _ham, **kw):
        khoa_da_gui.append(kw["idempotency_key"])
        return {"id": "job_{0}".format(len(khoa_da_gui)), "status": "succeeded"}

    monkeypatch.setattr(auto_khau, "_tao_job", tao_job)
    monkeypatch.setattr(auto_khau, "_cho_job", lambda _bc, job, **kw: job)
    monkeypatch.setattr(auto_khau, "SoTheoDoi", lambda *_a, **_k: SimpleNamespace(dong=lambda: None))
    monkeypatch.setattr(auto_khau, "_chen_the_cam_xuc", lambda _bc, _l, chu: chu)
    monkeypatch.setattr(auto_khau, "khoa_viec", lambda _l, viec, so, *_a: "K:{0}:{1}".format(viec, so))
    monkeypatch.setattr(auto_khau, "_chay_song_song",
                        lambda _bc, muc, lam, _ten, **_k: [lam(m) for m in muc])
    monkeypatch.setattr(auto_khau, "_bi_xen_am_dau", lambda *_a: False)
    monkeypatch.setattr(auto_khau, "_noi_mp3", lambda *_a, **_k: None)
    monkeypatch.setattr(auto_khau, "_lam_sach_ket_qua", lambda *_a: None)
    monkeypatch.setattr(auto_khau, "_ghi_phan_giong", lambda *_a: 0)
    da_tai = _tai_gia(monkeypatch, ma_loi)
    return auto_khau._khau_giong_doc(bc), luot, khoa_da_gui, da_tai, nhat_ky


def test_khau_giong_doc_400_luc_tai_thi_doc_lai_bang_khoa_moi(monkeypatch, tmp_path):
    lam, luot, khoa, da_tai, nhat_ky = _dung_khau_giong_doc(monkeypatch, tmp_path, [400])
    lam(luot, None)
    assert khoa[0] == "K:tts:1", "lần đầu vẫn khoá ổn định (chống trả tiền hai lần)"
    assert len(khoa) == 2 and khoa[1].startswith("K:tts:1:mat:k1-")
    assert da_tai == ["job_1", "job_2"]
    assert os.path.isfile(os.path.join(luot.thu_muc, "2-doan", "001.mp3"))
    assert any("đặt lại bằng khoá mới (1/2)" in d for d in nhat_ky), nhat_ky


def test_khau_giong_doc_het_luot_thi_cau_dung_la_phia_may_chu(monkeypatch, tmp_path):
    lam, luot, khoa, _da_tai, _nk = _dung_khau_giong_doc(monkeypatch, tmp_path, [400, 400, 400])
    with pytest.raises(LoiTaiVe) as bat:
        lam(luot, None)
    assert len(khoa) == 3, "đúng 1 lần đầu + 2 lần đặt lại"
    assert su_co.phan_loai(RuntimeError(str(bat.value))) in tu_chay._LOAI_LOI_CHO_NGOAI


# ── Đường thật: khâu ảnh cảnh (giữ đúng lời nhắc ĐÃ ra job) ──────────────────


def test_anh_canh_400_thi_ve_lai_dung_loi_nhac_da_viet_lai(monkeypatch, tmp_path):
    c = {"scene_id": 7, "img_prompt": "cheeks flushing, a cat"}
    luot = SimpleNamespace(thu_muc=str(tmp_path), ma_luot="0001", ma_kenh="x")
    goi = []

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None):
        goi.append((prompt, khoa))
        if "flushing" in prompt:
            raise RuntimeError("content_rejected: bị bộ lọc từ chối")
        return {"id": "job_{0}".format(len(goi))}

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(auto_khau, "_viet_lai_khi_bi_tu_choi", lambda *_a: "rosy, a cat")
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda *_a: None)
    monkeypatch.setattr(auto_khau, "_cham_va_ve_lai", lambda *_a, **_k: None)
    monkeypatch.setattr(auto_khau, "khoa_viec", lambda _l, viec, so, ln, *a: "K:{0}:{1}".format(ln, ":".join(a)))
    _tai_gia(monkeypatch, [400])
    bc = SimpleNamespace(ghi=lambda *_a: None, kiem_dung=lambda: None)
    hop = SimpleNamespace(lay=lambda: [])
    tep = str(tmp_path / "7.png")
    auto_khau._lam_anh_canh(bc, luot, c, tep, hop)
    assert [p for p, _k in goi] == ["cheeks flushing, a cat", "rosy, a cat", "rosy, a cat"]
    assert goi[2][1].startswith(goi[1][1] + ":mat:k1-"), goi
    assert os.path.isfile(tep)
