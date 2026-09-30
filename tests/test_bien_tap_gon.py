"""Đề bài biên tập GỌN (B5/B6 `workspace/THIET-KE-CHIEN-LUOC.md`) — `core/bien_tap_content.py`.

* Kênh KHÔNG khai `de_bai_bien_tap` → lời nhắc y hệt DE_BAI cũ (không thêm khối nào).
* Kênh khai `de_bai_bien_tap: "gon"` → MỤC TIÊU + TIÊU CHÍ + DỮ LIỆU + cùng khối TRẢ LỜI; không số cứng
  của thị trường Nhật khi kênh/ngách khai giá trị riêng; mặc định = hằng cũ; khối nhóm chỉ khi kênh
  còn < 6 video đủ 48h; bài học kênh không lặp khối TỰ SỬA / INSIGHT nhóm.
* `<<BAI_HOC>>` của `auto_khau._khoi_khan_gia`.
Không mạng: không gọi AI (chỉ dựng lời nhắc).
"""

from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bien_tap_content as bt  # noqa: E402
from core.chien_luoc import bai_hoc, ngu_canh  # noqa: E402

UV = [{"link": "https://youtu.be/AAAAAAAAAAA", "ma": "AAAAAAAAAAA", "tieu_de": "nguồn A", "kenh": "Z",
       "hang_cong_thuc": 1, "noi_dung": "..."}]


def _kenh(goc, ma="K1", **cai):
    kd = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(kd, exist_ok=True)
    with io.open(os.path.join(kd, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "{0}"\n'.format(ma) + "".join('{0}: "{1}"\n'.format(k, v) for k, v in cai.items()))
    return kd


def _loi_nhac(goc, ma="K1"):
    bc = bt.dung_boi_canh(goc, ma)
    return bc, bt.dung_loi_nhac(bc, UV, 3)


def test_kenh_khong_khai_giu_nguyen_de_bai_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc)
    bc, ln = _loi_nhac(goc)
    assert "_de_bai" not in bc and "bai_hoc_kenh" not in bc
    assert ln == bt.DE_BAI.format(so_uv=1, so_chon=3, thang=bt._ngan_so(bt.NGUONG_THANG_48H),
                                  truot=bt._ngan_so(bt.NGUONG_TRUOT_48H), ung_vien=bt._khoi_ung_vien(UV),
                                  **{k: (v or "(trống)") for k, v in bc.items() if not k.startswith("_")})
    assert ln.startswith("═══ MỤC TIÊU KÊNH")


def test_gon_bo_so_cung_nhat_khi_kenh_khai_gia_tri_rieng(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, de_bai_bien_tap="gon", ngon_ngu="vi", quoc_gia="VN",
          khan_gia_mo_ta="người Việt 25–44, xem điện thoại", ctr_trang_chu_thang="~7–9%",
          ctr_trang_chu_truot="~2–4%", ctr_trang_chu_muc_tieu="6.5", luat_chon="Chỉ món ăn gia đình | Không review nhà hàng")
    bc, ln = _loi_nhac(goc)
    assert bc["_de_bai"] == bt.DE_BAI_GON
    than = ln[:ln.index("═══ TRẢ LỜI ═══")]
    for cam in ("Nhật", "55+", "5,5–6,2%", "精神年齢", "お金持ち", "TÂM LÝ"):
        assert cam not in than, cam
    for co in ("tiếng Việt", "người Việt 25–44", "~7–9%", "~2–4%", "≥ 6.5%", "- Chỉ món ăn gia đình",
               "- Không review nhà hàng", "═══ MỤC TIÊU ═══", "═══ TIÊU CHÍ ═══", "═══ DỮ LIỆU ═══"):
        assert co in than, co
    # khối TRẢ LỜI: đúng khuôn cũ (bộ đọc `doc_ket_qua` không đổi)
    assert ln.endswith(bt.DE_BAI[bt.DE_BAI.index("═══ TRẢ LỜI ═══"):].format(so_chon=3, so_uv=1))
    assert ln.count("{") == ln.count("}")


def test_gon_mac_dinh_bang_hang_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, de_bai_bien_tap="gon")
    _bc, ln = _loi_nhac(goc)
    assert bt.MAC_DINH_KHAN_GIA in ln and bt.MAC_DINH_CTR_THANG in ln and "tiếng Nhật" in ln
    assert bt.MAC_DINH_LUAT_NGACH[0] in ln
    assert "“thắng” ≥" not in ln and '"thắng" ≥ 6' in ln  # ngưỡng kênh (sàn V7 6.000), không 20.000


def test_gon_khoi_nhom_chi_khi_kenh_it_so(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh(goc, de_bai_bien_tap="gon")
    monkeypatch.setattr(ngu_canh.NguCanh, "so_video_48h", property(lambda _s: 2))
    assert "INSIGHT NHÓM:" in _loi_nhac(goc)[1]
    monkeypatch.setattr(ngu_canh.NguCanh, "so_video_48h", property(lambda _s: 6))
    assert "INSIGHT NHÓM:" not in _loi_nhac(goc)[1]


def test_gon_bai_hoc_kenh_khong_lap_khoi_cu(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _kenh(goc, de_bai_bien_tap="gon")
    ds = [bai_hoc._bh("kenh", "giu_chan", "Kênh: còn 52% ở 2:00 (n=5).", 5, ["bien_tap"]),
          bai_hoc._bh("kenh", "bien_tap", "Lần trước đoán sai CTR (n=4).", 4, ["bien_tap"]),
          bai_hoc._bh("nhom", "insight_nhom", "Nhóm: cụm X thắng (n=9).", 9, ["bien_tap"])]
    monkeypatch.setattr(bai_hoc, "_tat_ca", lambda *_a, **_k: list(ds))
    bc = bt.dung_boi_canh(goc, "K1")
    assert bc["bai_hoc_kenh"] == "- Kênh: còn 52% ở 2:00 (n=5)."


def test_nguon_cua_goi_la_bi_danh_cua_ho_so_video(tmp_path):
    goc = str(tmp_path)
    kd = _kenh(goc)
    os.makedirs(os.path.join(kd, "tu-chay"))
    with io.open(os.path.join(kd, "tu-chay", "2026-09-29.json"), "w", encoding="utf-8") as tep:
        json.dump({"runs": [{"ma_luot": "0001", "ban_giao": {"ma_goi": "K1-0001"},
                             "nguon": {"nguon": "vph", "link": "https://youtu.be/SRC00000001"}}]}, tep)
    ng = bt._nguon_cua_goi(goc, "K1")["K1-0001"]
    assert ng["ma"] == "SRC00000001" and ng["cong_thuc"] == "vph"


def test_mo_ta_khan_gia_mac_dinh_jp_va_doc_quoc_gia():
    du = {"vung": {"JP": 91, "VN": 40}}
    assert "JP 91%" in bt._mo_ta_khan_gia(du)
    assert "VN 40%" in bt._mo_ta_khan_gia(du, "VN")


def test_o_bai_hoc_auto_khau(tmp_path, monkeypatch):
    from core import auto_khau

    class _K:
        ma = "K1-v2"

    class _Bc:
        goc = str(tmp_path)

    goi = []

    def gia(goc, ma, dung_cho, *a, **k):
        goi.append((ma, dung_cho))
        return "- bài kênh gốc (n=4)" if ma == "K1" else ""

    monkeypatch.setattr(bai_hoc, "khoi_chu", gia)
    assert auto_khau._khoi_bai_hoc_kich_ban(_Bc(), _K()) == "- bài kênh gốc (n=4)"
    assert goi == [("K1-v2", "kich_ban"), ("K1", "kich_ban")]
    monkeypatch.setattr(bai_hoc, "khoi_chu", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    assert auto_khau._khoi_bai_hoc_kich_ban(_Bc(), _K()) == "(chưa có)"
