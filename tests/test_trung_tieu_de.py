"""Chống làm trùng NỘI DUNG theo TIÊU ĐỀ (`core/trung_tieu_de.py`).

Chẩn đoán 27→28/09/2026: TL1-T7 sản xuất 0006 rồi 0007 CÙNG một tiêu đề
tiếng Nhật, từ hai nguồn khác MÃ (chống trùng cũ chỉ so mã nên bỏ lọt). Bài
kiểm dưới đây dùng ĐÚNG cặp tiêu đề thật bắt được từ vụ đó, cộng dữ liệu thật
đo lại từ `CHANNEL/TL1-T7`/`TL3-T7` (không đoán ngưỡng).
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import trung_tieu_de as tt  # noqa: E402

KENH = "TL1-T7"

# Cặp tiêu đề THẬT của TL1-T7-0006/0007 (chẩn đoán 27→28/09/2026).
_TIEU_DE_NGUON_1 = "【心理学】朝いつも同じ夢を見る人、実は〇〇です。潜在意識が伝える深層心理"
_TIEU_DE_DAT = "【雑学】朝いつも同じ夢を見る人、実は〇〇です。潜在意識が伝える深層心理"


def _goc_auto(tmp_path, luot, *, tieu_de_nguon="", tieu_de_dat="", video_id="X"):
    d = tmp_path / "PROJECTS" / "AUTO" / KENH / luot
    d.mkdir(parents=True)
    if tieu_de_nguon:
        io.open(str(d / tt.TEP_NGUON), "w", encoding="utf-8").write(
            "TITLE: {0}\r\nVIDEO_ID: {1}\r\n".format(tieu_de_nguon, video_id))
    if tieu_de_dat:
        io.open(str(d / tt.TEP_TIEU_DE_DAT), "w", encoding="utf-8").write(
            "TITLE: {0}\r\n".format(tieu_de_dat))
    return str(tmp_path)


# ── chuẩn hoá + so khớp mờ ───────────────────────────────────────────────────


def test_chuan_hoa_bo_nhan_dau_cau():
    a = tt.chuan_hoa_tieu_de_so_khop("【心理学】" + "Cùng một câu")
    b = tt.chuan_hoa_tieu_de_so_khop("【雑学】" + "Cùng một câu")
    assert a == b  # hai nhãn khác nhau, còn lại giống hệt -> chuẩn hoá về CÙNG chuỗi


def test_diem_giong_cap_that_0006_0007_vuot_nguong_mac_dinh():
    """Đúng cặp tiêu đề thật gây ra vụ 27→28/09/2026 — phải đạt ngưỡng mặc định."""
    diem = tt.diem_giong_tieu_de(_TIEU_DE_NGUON_1, _TIEU_DE_DAT)
    assert diem >= tt.NGUONG_GIONG_TIEU_DE_MAC_DINH
    assert tt.trung_tieu_de(_TIEU_DE_NGUON_1, _TIEU_DE_DAT) is True


def test_de_khac_han_khong_bi_coi_la_trung():
    a = "【心理学】朝いつも同じ夢を見る人、実は〇〇です。潜在意識が伝える深層心理"
    b = "【雑学】何でも一人で抱える人の心理｜彼らはなぜ違う考え方をするのか？"
    assert tt.trung_tieu_de(a, b) is False


def test_rong_thi_khong_bao_gio_trung():
    assert tt.diem_giong_tieu_de("", "bất kỳ") == 0.0
    assert tt.diem_giong_tieu_de("bất kỳ", "") == 0.0


# ── đọc tiêu đề đã làm từ đĩa ────────────────────────────────────────────────


def test_doc_tieu_de_da_lam_gop_nguon_va_dat_tu_moi_luot(tmp_path):
    goc = _goc_auto(tmp_path, "0001", tieu_de_nguon="Nguồn gốc A", tieu_de_dat="Tiêu đề đặt A",
                    video_id="AAAAAAAAAAA")
    ra = dict(tt.doc_tieu_de_da_lam(goc, KENH))
    assert ra.get("Nguồn gốc A", "").startswith("lượt")
    assert ra.get("Tiêu đề đặt A", "").startswith("lượt")


def test_doc_tieu_de_da_lam_gop_ke_hoach_dang(tmp_path):
    from core import ke_hoach_dang

    goc = str(tmp_path)
    dong = {ten: "" for ten in ke_hoach_dang.COT}
    dong.update({"Mã gói": "TL1-T7-0006", "Tiêu đề": _TIEU_DE_DAT})
    ke_hoach_dang.luu_bang(goc, KENH, [[dong[ten] for ten in ke_hoach_dang.COT]])

    ra = tt.doc_tieu_de_da_lam(goc, KENH)
    titles = {td for td, _mo_ta in ra}
    assert _TIEU_DE_DAT in titles


def test_doc_tieu_de_da_lam_thu_muc_rong_tra_ve_rong(tmp_path):
    assert tt.doc_tieu_de_da_lam(str(tmp_path), KENH) == []


def test_tim_tieu_de_trung_tra_khop_diem_cao_nhat(tmp_path):
    # Nhãn 【…】/[…] bị cắt trước khi so — nguồn và tiêu đề đã đặt của CÙNG một
    # lượt (chỉ khác nhãn) chuẩn hoá về CÙNG một chuỗi, nên cả hai đạt 1.0;
    # ứng viên đề khác hẳn phải đạt điểm thấp hơn HẲN, không lẫn vào.
    da_lam = [("Chủ đề khác hẳn", "lượt X/0001"), (_TIEU_DE_NGUON_1, "lượt X/0006 (nguồn)"),
             (_TIEU_DE_DAT, "lượt X/0006 (đặt)")]
    trung = tt.tim_tieu_de_trung(_TIEU_DE_DAT, da_lam, tt.NGUONG_GIONG_TIEU_DE_MAC_DINH)
    assert trung is not None
    tieu_de_cu, mo_ta, diem = trung
    assert diem == 1.0  # khớp tuyệt đối (sau khi cắt nhãn) với lượt 0006
    assert mo_ta in ("lượt X/0006 (nguồn)", "lượt X/0006 (đặt)")


def test_tim_tieu_de_trung_none_khi_khong_dat_nguong():
    da_lam = [("Một chủ đề bất kỳ, chẳng liên quan gì", "lượt X/0001")]
    assert tt.tim_tieu_de_trung("Chủ đề hoàn toàn khác biệt", da_lam) is None


# ── kiểm trên DỮ LIỆU THẬT của kho này (TL1-T7, TL3-T7) — không phải đồ giả ──


def test_du_lieu_that_tl1_bon_ung_vien_trung_de_bi_bat():
    """Bốn ứng viên chẩn đoán chỉ ra (`CHANNEL/TL1-T7/nghien-cuu/content.csv`)
    phải trùng với tiêu đề TL1-T7-0006/0007 đã làm, ở ngưỡng mặc định."""
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(goc, "CHANNEL", "TL1-T7")):
        import pytest

        pytest.skip("không chạy trên máy không có dữ liệu thật CHANNEL/TL1-T7")

    da_lam = tt.doc_tieu_de_da_lam(goc, "TL1-T7")
    # Kho chung (30/09/2026): tiêu đề trong tệp này đã được ẨN DANH HOÁ (không lộ
    # kênh thật) — chỉ chạy được trên máy có đúng dữ liệu khớp các tiêu đề này.
    if not any("朝いつも同じ夢を見る人" in str(x[0] if isinstance(x, (tuple, list)) else x) for x in da_lam):
        import pytest

        pytest.skip("dữ liệu thật của máy này không khớp bộ tiêu đề đã ẩn danh hoá")
    ung_vien = {
        "9zRSyu_aZjU": "【衝撃】朝いつも同じ夢を見る人、実は〇〇です。潜在意識が伝える深層心理【心理学】",
        "XPnByxdqQZc": "【心理学】朝いつも同じ夢を見る人、実は〇〇です。老化ではなく、潜在意識が伝える深層心理",
        "GsDV2SVF9p4": "【心理学】50代以降で朝いつも同じ夢を見る人、実は〇〇です。潜在意識が伝える深層心理",
        "Cf4Wl-QZgIw": "朝いつも同じ夢を見る人、実は〇〇です。体内時計が伝える深層心理【心理学】",
    }
    for ma, tieu_de in ung_vien.items():
        trung = tt.tim_tieu_de_trung(tieu_de, da_lam, tt.NGUONG_GIONG_TIEU_DE_MAC_DINH)
        assert trung is not None, "{0} phải bị loại vì trùng tiêu đề (điểm quá thấp?)".format(ma)


def test_du_lieu_that_tl3_iq_thap_khong_bat_duoc_bang_so_ky_tu():
    """GHI NHẬN GIỚI HẠN ĐÃ BIẾT (không phải lỗi): `SL94HyyuLXs`
    "IQが低い人の頭の中で起きていること" và TL3-T7-0001 "低IQの人の頭の中は
    こんな世界" CÙNG chủ đề nhưng đảo trật tự từ tiếng Nhật ("IQが低い" đối
    "低IQ") — điểm giống (~0,485) THẤP hơn ngưỡng 0,80. Xem "NGƯỠNG 0,80" ở
    docstring đầu `core/trung_tieu_de.py` — hạ ngưỡng xuống mức bắt được ca
    này sẽ ăn sát trần nhiễu (0,303, đo trên toàn bộ 5 kênh) hơn mức an toàn."""
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(goc, "CHANNEL", "TL3-T7")):
        import pytest

        pytest.skip("không chạy trên máy không có dữ liệu thật CHANNEL/TL3-T7")

    da_lam = tt.doc_tieu_de_da_lam(goc, "TL3-T7")
    trung = tt.tim_tieu_de_trung("IQが低い人の頭の中で起きていること", da_lam,
                                 tt.NGUONG_GIONG_TIEU_DE_MAC_DINH)
    assert trung is None  # xác nhận giới hạn — KHÔNG cố sửa bằng cách hạ ngưỡng
