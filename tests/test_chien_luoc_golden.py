"""GOLDEN của bộ chọn nguồn (B1 thiết kế chiến lược, 30/09/2026).

Mỗi `tests/du-lieu/chien-luoc/<ten>.json` là một KÊNH GIẢ (kenh.yaml, bảng nhóm, cong-thuc-v7.json,
bảng VPH / V7 / Một nút giả). Bài này chạy `tu_chay.ung_vien_xep_hang` và `tu_chay._chon_nguon`
(không ví, không mạng) rồi so ĐẦU RA + NHẬT KÝ với `<ten>.golden.json` TỪNG BYTE.

Bản chụp đầu tiên được ghi bằng mã TRƯỚC khi tách gói `core/chien_luoc/` — tức là hợp đồng
"không khai `chien_luoc` thì chạy y hệt hôm nay". Thiếu tệp golden thì bài tự ghi rồi xanh (lần
đầu); muốn chụp lại có chủ ý: xoá tệp `.golden.json` rồi chạy lại, và ghi lý do vào NHAT-KY.
"""

from __future__ import annotations

import csv
import io
import json
import os
import types

import pytest

from core import cong_thuc_v7 as v7
from core import cong_thuc_vph
from core import nhom_kenh
from core import tu_chay

THU_MUC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "du-lieu", "chien-luoc")
NHOM = "tam-ly-nhat"
TEP_LECH_NHIP = "nguoi-song-lech-nhip-so-dong"
HANG_ANH_EM = (
    ("TL4-T7", TEP_LECH_NHIP, "【心理学】片付けをしない人の意外な知性", "aaaaaaaaaaa", 181062),
    ("TL4-T7", TEP_LECH_NHIP, "断捨離をした人の暮らしが変わる理由", "bbbbbbbbbbb", 135132),
    ("TL4-T7", TEP_LECH_NHIP, "一人が好きな人だけに現れる5つの知的特徴", "ccccccccccc", 136170),
)


def _fixture_ten():
    return sorted(t[:-5] for t in os.listdir(THU_MUC)
                  if t.endswith(".json") and not t.endswith(".golden.json"))


def _doc(ten):
    with io.open(os.path.join(THU_MUC, ten + ".json"), encoding="utf-8") as tep:
        return json.load(tep)


def dung_kenh_gia(goc, fx):
    """Dựng kênh giả của một fixture trong `goc` — dùng chung cho các bài `test_chien_luoc*`."""
    ma = fx["kenh"]
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    with io.open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(fx.get("kenh_yaml") or []) + "\n")
    if fx.get("cong_thuc_v7") is not None:
        nc = os.path.join(thu_muc, "nghien-cuu")
        os.makedirs(nc, exist_ok=True)
        with io.open(os.path.join(nc, v7.TEP_CAU_HINH), "w", encoding="utf-8") as tep:
            json.dump(fx["cong_thuc_v7"], tep, ensure_ascii=False)
    if fx.get("bang_nhom"):
        tm = nhom_kenh.duong_thu_muc_nhom(goc, NHOM)
        os.makedirs(tm, exist_ok=True)
        with open(os.path.join(tm, nhom_kenh.TEP_BANG_NHOM), "w", encoding="utf-8-sig",
                  newline="") as tep:
            but = csv.DictWriter(tep, fieldnames=list(nhom_kenh.COT_BANG_NHOM))
            but.writeheader()
            for ma_k, tep_id, tieu_de, ma_v, hien_thi in HANG_ANH_EM:
                but.writerow({"Kênh": ma_k, "Tệp": tep_id, "Tiêu đề": tieu_de, "Mã video": ma_v,
                              "Ngày đăng": "2026-09-16", "Lượt hiển thị": hien_thi,
                              "Tỷ lệ bấm": "5.41%", "Xem TB": "4:02", "Lượt xem": 4723,
                              "Đăng ký": 7})
    return ma


def seam_gia(fx):
    """`(cham_v7, doc_danh_sach, vph)` giả của fixture — `vph` thay `cong_thuc_vph.ung_vien_chon_nguon`."""
    def cham_v7(_g, _k):
        if fx.get("v7_loi"):
            raise RuntimeError(fx["v7_loi"])
        return types.SimpleNamespace(
            ung_vien=[types.SimpleNamespace(**d) for d in (fx.get("v7") or [])])

    def doc_danh_sach(_g, _k):
        return json.loads(json.dumps(fx.get("mot_nut") or {}))

    def vph(_g, _k, **_kw):
        if fx.get("vph_loi"):
            raise RuntimeError(fx["vph_loi"])
        return json.loads(json.dumps(fx.get("vph") or []))

    return cham_v7, doc_danh_sach, vph


def chup(goc, fx, monkeypatch):
    """Đầu ra + nhật ký của `ung_vien_xep_hang` và `_chon_nguon` cho một fixture."""
    ma = dung_kenh_gia(goc, fx)
    cham_v7, doc_ds, vph = seam_gia(fx)
    monkeypatch.setattr(cong_thuc_vph, "ung_vien_chon_nguon", vph)
    da_lam = [tuple(x) for x in fx.get("da_lam_tieu_de") or []]
    log1 = []
    ds = tu_chay.ung_vien_xep_hang(goc, ma, bool(fx["co_v7_truoc"]), set(fx.get("loai_tru") or []),
                                   cham_v7=cham_v7, doc_danh_sach=doc_ds, log=log1.append,
                                   da_lam_tieu_de=da_lam)
    log2 = []
    nguon = tu_chay._chon_nguon(goc, ma, bool(fx["co_v7_truoc"]), set(fx.get("loai_tru") or []),
                                cham_v7, doc_ds, log2.append, da_lam_tieu_de=da_lam)
    return {"ung_vien_xep_hang": {"ds": ds, "log": log1},
            "_chon_nguon": {"nguon": nguon, "log": log2}}


def _chuoi(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


@pytest.mark.parametrize("ten", _fixture_ten())
def test_golden_chon_nguon(ten, tmp_path, monkeypatch):
    fx = _doc(ten)
    thuc = _chuoi(chup(str(tmp_path), fx, monkeypatch))
    assert str(tmp_path) not in thuc, "đầu ra không được mang đường dẫn tạm (golden phải tất định)"
    duong = os.path.join(THU_MUC, ten + ".golden.json")
    if not os.path.isfile(duong):
        with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
            tep.write(thuc)
        return
    with io.open(duong, encoding="utf-8", newline="") as tep:
        mong = tep.read()
    assert thuc == mong, "lệch golden {0} — bộ chọn nguồn đã đổi hành vi".format(ten)
