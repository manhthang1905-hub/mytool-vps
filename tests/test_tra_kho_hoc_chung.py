"""20/10/2026 — kênh TRẢ KHO không còn vào việc học / gộp số chung: nhóm (mượn chéo ×0,3), bảng nhóm, phòng thí
nghiệm, báo cáo ngày (YPP), tỉ lệ đúng của não. Dòng cũ của chúng GIỮ trên đĩa, chỉ bỏ khi tính. Cây giả trong tmp."""

import csv
import os

import pytest

from core import nhom_kenh

KENH = ("KA", "KB", "KC")


def _goc(tmp_path, tra=("KC",)):
    for k in KENH:
        d = tmp_path / "CHANNEL" / k
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text('nhom: "n1"\ntep: "t-{0}"\n'.format(k.lower()) +
                                     ("tra_kho: 2026-10-19\n" if k in tra else ""), encoding="utf-8")
    return str(tmp_path)


def test_thanh_vien_nhom_bo_kenh_tra_kho(tmp_path):
    goc = _goc(tmp_path)
    assert nhom_kenh.thanh_vien(goc, "KA") == ["KA", "KB"]
    assert nhom_kenh.thanh_vien(goc, "KC") == ["KA", "KB", "KC"]          # chính nó vẫn thấy mình (đọc lịch sử)


def test_doc_bang_nhom_bo_dong_cu_cua_kenh_tra_kho(tmp_path):
    goc = _goc(tmp_path)
    tm = nhom_kenh.duong_thu_muc_nhom(goc, "n1")
    os.makedirs(tm, exist_ok=True)
    with open(os.path.join(tm, nhom_kenh.TEP_BANG_NHOM), "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=list(nhom_kenh.COT_BANG_NHOM), extrasaction="ignore")
        w.writeheader()
        for k in ("KB", "KC"):                                          # bảng viết TRƯỚC khi KC trả kho
            w.writerow({"Kênh": k, "Tiêu đề": "tiêu đề {0}".format(k), "Lượt hiển thị": "99999"})
    ra = nhom_kenh.doc_bang_nhom(goc, "n1", cum_cua=lambda td: ["c1"], nguong_hien_thi=10)
    assert ra == {"c1": {"KB": 0.75}}


def test_phong_thi_nghiem_va_bao_cao_ngay_bo_kenh_tra_kho(tmp_path, monkeypatch):
    from core import ypp
    from core.phong_thi_nghiem import danh_gia, nhat_ky

    goc = _goc(tmp_path)
    assert danh_gia.kenh_phong_thi_nghiem(goc) == ["KA", "KB"]
    assert "KC" not in ypp.cac_kenh(goc)

    class _Dung(Exception):
        pass

    thay = {}

    def doc(_g, **kw):
        thay.update(kw)
        raise _Dung()
    monkeypatch.setattr(nhat_ky, "doc", doc)
    with pytest.raises(_Dung):                                          # truyền tay cả KC vẫn bị bỏ
        danh_gia.chay(goc, kenh_ds=["KA", "KC"], ghi=False, ap_luat=False)
    assert thay["kenh"] == ["KA"]


def test_ti_le_dung_nao_bo_kenh_tra_kho(tmp_path):
    from core import nao

    goc = _goc(tmp_path)
    ds = [{"lenh": "thu", "tham_so": {"kenh": "KC"}, "cham": "sai"}, {"lenh": "thu", "tham_so": {"kenh": "KA"},
                                                                        "cham": "dung"}]
    assert nao.ti_le_dung(ds, goc) == (1, 1)
