"""Hồ sơ video (`core/ho_so_video.py`) — Việc 3 của
`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

Ba nhóm bài, không gọi mạng, không cần Qt:

1. `tao_ho_so`: xây hồ sơ từ một thư mục lượt AUTO giả — đọc đúng tiêu đề/chữ
   bìa, bản kịch bản/hook đã chọn + điểm (từ văn bản tự do `1-cham-diem.txt`),
   ảnh bìa đang dùng, sao lưu ảnh bìa lâu dài.
2. `cap_nhat_chi_so`: fixture CHÉP nguyên số liệu Studio THẬT của TL3-T7
   (`vea03c3caae`, hai lần chụp 22h/56h thật, CTR 6,5%/9,73%) — chốt đúng khung
   giờ 24h/48h, nối `video_id` qua tiêu đề, idempotent, cờ số liệu cũ.
3. `bu_ho_so`: bù hồ sơ cho gói đã bàn giao trước — từ lượt AUTO còn sống, và
   lùi về bản tối giản khi thư mục lượt đã bị dọn; idempotent; bỏ qua dòng
   chưa từng bàn giao.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ban_giao_dang  # noqa: E402
from core import ho_so_video as hv  # noqa: E402
from core import ke_hoach_dang  # noqa: E402
from core.auto import duong_luot  # noqa: E402

GOC_THAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAY_GIO = dt.datetime(2026, 9, 28, 15, 0, 0)


# ── 1. `tao_ho_so` — xây hồ sơ từ một thư mục lượt AUTO giả ───────────────────


_CHAM_DIEM_MAU = """\
- Bản A: 3792 ký tự ≈ 14,0 phút đọc (nhắm 15,0 phút ≈ 4050 ký tự, lệch -6%), trùng nguyên văn bản gốc 4%
- Bản B: 3941 ký tự ≈ 14,6 phút đọc (nhắm 15,0 phút ≈ 4050 ký tự, lệch -3%), trùng nguyên văn bản gốc 4%
- Bản C: 3631 ký tự ≈ 13,4 phút đọc (nhắm 15,0 phút ≈ 4050 ký tự, lệch -10%), trùng nguyên văn bản gốc 7%

Chọn: bản B
Điểm: {"A": 6, "B": 8, "C": 7}
Lý do: bản B giữ nhịp tốt nhất.

── HOOK ──
- Bản A: 170 ký tự, trùng nguyên văn bản gốc 0%
- Bản B: 174 ký tự, trùng nguyên văn bản gốc 0%

Chọn hook: bản A
Điểm: {"A": 7, "B": 6, "C": 4}
Lý do: bản A móc nối chữ bìa tốt nhất.
"""


def _dung_luot_gia(goc, kenh, luot, *, tieu_de="Tiêu đề giả", chu_bia="Chữ bìa giả",
                   ten_thumb="CHON-thumb_002.png"):
    thu_muc = duong_luot(goc, kenh, luot)
    os.makedirs(os.path.join(thu_muc, "7-thumbnail"), exist_ok=True)
    with io.open(os.path.join(thu_muc, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: {0}\nTHUMB: {1}\n".format(tieu_de, chu_bia))
    with io.open(os.path.join(thu_muc, "1-cham-diem.txt"), "w", encoding="utf-8") as tep:
        tep.write(_CHAM_DIEM_MAU)
    with io.open(os.path.join(thu_muc, "7-thumbnail", ten_thumb), "wb") as tep:
        tep.write(b"\xff\xd8\xff\xe0FAKE-JPEG-DATA")
    return thu_muc


def test_tao_ho_so_doc_du_tieu_de_chu_bia_kich_ban_hook():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        _dung_luot_gia(goc, "K1", "0001")
        duong = hv.tao_ho_so(goc, "K1", "0001", "K1-0001")
        assert os.path.isfile(duong)
        ho_so = hv.doc_ho_so(goc, "K1", "K1-0001")
        assert ho_so["tieu_de"] == "Tiêu đề giả"
        assert ho_so["chu_bia"] == "Chữ bìa giả"
        assert ho_so["kich_ban"]["ban_chon"] == "B"
        assert ho_so["kich_ban"]["diem"] == {"A": 6, "B": 8, "C": 7}
        assert ho_so["kich_ban"]["ky_tu_ban_chon"] == 3941
        assert ho_so["kich_ban"]["hook_chon"] == "A"
        assert ho_so["kich_ban"]["hook_diem"] == {"A": 7, "B": 6, "C": 4}
        assert ho_so["video_id"] is None and ho_so["chi_so"] == {}


def test_tao_ho_so_nhan_dung_anh_bia_va_kieu_va_sao_luu_lau_dai():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        _dung_luot_gia(goc, "K1", "0002", ten_thumb="CHON-thumb_002.png")
        hv.tao_ho_so(goc, "K1", "0002", "K1-0002")
        ho_so = hv.doc_ho_so(goc, "K1", "K1-0002")
        assert ho_so["thumbnail"]["tep"] == "CHON-thumb_002.png"
        assert ho_so["thumbnail"]["kieu"] == "dramatic_scene"
        assert ho_so["thumbnail"]["chon_boi"] == "nguoi"
        # Bản sao ảnh bìa lâu dài phải tồn tại — độc lập với thư mục lượt AUTO.
        duong_anh = hv.duong_anh_ho_so(goc, "K1", "K1-0002")
        assert os.path.isfile(duong_anh)


def test_tao_ho_so_khong_co_chon_thi_lay_tam_dau_va_ghi_nguon_luat():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        thu_muc = duong_luot(goc, "K1", "0003")
        os.makedirs(os.path.join(thu_muc, "7-thumbnail"), exist_ok=True)
        with io.open(os.path.join(thu_muc, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
            tep.write("TITLE: X\n")
        with io.open(os.path.join(thu_muc, "7-thumbnail", "thumb_001.png"), "wb") as tep:
            tep.write(b"\xff\xd8\xff\xe0FAKE")
        hv.tao_ho_so(goc, "K1", "0003", "K1-0003")
        ho_so = hv.doc_ho_so(goc, "K1", "K1-0003")
        assert ho_so["thumbnail"]["tep"] == "thumb_001.png"
        assert ho_so["thumbnail"]["kieu"] == "portrait_main"
        assert ho_so["thumbnail"]["chon_boi"] == "luat"


def test_tao_ho_so_thieu_moi_tep_van_khong_nem_loi():
    """Lượt gần như trống (thiếu tiêu đề, kịch bản, ảnh bìa, video) — hồ sơ vẫn
    ghi được, đúng khung rỗng, không ném lỗi."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        os.makedirs(duong_luot(goc, "K1", "0004"), exist_ok=True)
        duong = hv.tao_ho_so(goc, "K1", "0004", "K1-0004")
        ho_so = hv.doc_ho_so(goc, "K1", "K1-0004")
        assert os.path.isfile(duong)
        assert ho_so["tieu_de"] == "" and ho_so["thumbnail"]["tep"] == ""


def test_doc_cham_diem_tach_dung_kich_ban_va_hook():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        duong = os.path.join(tmp, "1-cham-diem.txt")
        with io.open(duong, "w", encoding="utf-8") as tep:
            tep.write(_CHAM_DIEM_MAU)
        ra = hv._doc_cham_diem(duong)
        assert ra["so_ky_tu"] == {"A": 3792, "B": 3941, "C": 3631}
        assert ra["ban_chon"] == "B"
        assert ra["hook_chon"] == "A"
        assert ra["hook_diem"] == {"A": 7, "B": 6, "C": 4}


# ── 2. `cap_nhat_chi_so` — trên số liệu Studio THẬT của TL3-T7 (chép fixture) ──


def _chep_chi_so_that_tl3(goc: str, kenh: str) -> None:
    """Chép NGUYÊN `CHANNEL/TL3-T7/chi-so/vea03c3caae` thật (hai lần chụp thật
    22h/56h, CTR đo được 6,5%/9,73%) vào một kênh giả — kiểm trên đúng SỐ THẬT
    mà không đụng `CHANNEL/TL3-T7` thật.

    30/09/2026: kênh thật chụp thêm mốc 165h — chỉ chép ĐÚNG hai lần chụp 22h/56h
    mà bài kiểm được viết cho, để số thật mới về không làm đỏ bài."""
    nguon = os.path.join(GOC_THAT, "CHANNEL", "TL3-T7", "chi-so", "vea03c3caae")
    dich = os.path.join(goc, "CHANNEL", kenh, "chi-so", "vea03c3caae")
    if not os.path.isdir(nguon):
        # Kho chung (30/09/2026): số liệu kênh thật KHÔNG lên kho, và video id thật
        # trong tệp này đã được thay bằng id giả — máy nào có đúng thư mục này mới chạy.
        pytest.skip("cần số liệu Studio thật CHANNEL/TL3-T7/chi-so/<id> của máy nguồn")

    def _bo_moc_khac(thu_muc, ten):
        if os.path.normpath(thu_muc) != os.path.normpath(nguon):
            return []
        return [t for t in ten if t.endswith("h") and t[:-1].isdigit() and t not in ("22h", "56h")]

    shutil.copytree(nguon, dich, ignore=_bo_moc_khac)


_TIEU_DE_THAT_TL3_0001 = "【脳科学】考えすぎる人の頭の中はこんな世界"


def test_cap_nhat_chi_so_chia_dung_khung_24h_48h_tu_so_lieu_that():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "TESTK-TL3"
        _chep_chi_so_that_tl3(goc, kenh)
        hv._luu_ho_so(goc, kenh, "TESTK-TL3-0001",
                      {"tieu_de": _TIEU_DE_THAT_TL3_0001, "video_id": None, "chi_so": {}})

        tt = hv.cap_nhat_chi_so(goc, kenh, bay_gio=BAY_GIO)
        assert tt["noi_video_id"] == 1
        assert tt["cap_nhat_moc"] == 2  # đúng hai lần chụp thật (22h, 56h)

        ho_so = hv.doc_ho_so(goc, kenh, "TESTK-TL3-0001")
        assert ho_so["video_id"] == "vea03c3caae"
        assert ho_so["chi_so"]["24h"]["ctr"] == 6.5
        assert ho_so["chi_so"]["24h"]["moc_gio_that"] == 22
        assert ho_so["chi_so"]["48h"]["ctr"] == 9.73
        assert ho_so["chi_so"]["48h"]["moc_gio_that"] == 56
        assert ho_so["so_lieu_moi_nhat"]["moc"] == "48h"
        assert ho_so["so_lieu_moi_nhat"]["ctr"] == 9.73
        # Lần chụp 56h thật là 2026-09-25 19:19 — cách BAY_GIO (28/09 15:00) hơn 36 giờ.
        assert tt["so_lieu_cu"] == ["TESTK-TL3-0001"]


def test_cap_nhat_chi_so_idempotent_khong_dem_lai_khi_khong_co_gi_moi():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "TESTK-TL3B"
        _chep_chi_so_that_tl3(goc, kenh)
        hv._luu_ho_so(goc, kenh, "TESTK-TL3B-0001",
                      {"tieu_de": _TIEU_DE_THAT_TL3_0001, "video_id": None, "chi_so": {}})

        tt1 = hv.cap_nhat_chi_so(goc, kenh, bay_gio=BAY_GIO)
        assert tt1["cap_nhat_moc"] == 2 and tt1["noi_video_id"] == 1
        tt2 = hv.cap_nhat_chi_so(goc, kenh, bay_gio=BAY_GIO)
        assert tt2["cap_nhat_moc"] == 0 and tt2["noi_video_id"] == 0, (
            "gọi lại không có số liệu mới thì không được đếm lại")


def test_cap_nhat_chi_so_khong_khop_tieu_de_thi_giu_nguyen_khong_nem_loi():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "TESTK-TL3C"
        _chep_chi_so_that_tl3(goc, kenh)
        hv._luu_ho_so(goc, kenh, "TESTK-TL3C-0009",
                      {"tieu_de": "Tiêu đề hoàn toàn không khớp video nào",
                       "video_id": None, "chi_so": {}})
        tt = hv.cap_nhat_chi_so(goc, kenh, bay_gio=BAY_GIO)
        assert tt == {"noi_video_id": 0, "cap_nhat_moc": 0, "so_lieu_cu": []}
        ho_so = hv.doc_ho_so(goc, kenh, "TESTK-TL3C-0009")
        assert ho_so["video_id"] is None and ho_so["chi_so"] == {}


def test_cap_nhat_chi_so_kenh_chua_co_ho_so_tra_rong():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tt = hv.cap_nhat_chi_so(str(tmp), "KHONG-TON-TAI", bay_gio=BAY_GIO)
        assert tt == {"noi_video_id": 0, "cap_nhat_moc": 0, "so_lieu_cu": []}


def test_cap_nhat_chi_so_nhan_ca_ban_chup_qua_240h_khong_con_bi_bo():
    """Tái hiện lỗi 29/09/2026 (`TL1-T7-0001`): tiện ích ĐÃ chụp một mốc 300 giờ
    tuổi (~12,5 ngày — quá trần "7d" cũ là 240h), nhưng bản cũ của `_ten_moc`
    trả `""` cho giờ đó nên `cap_nhat_chi_so` bỏ qua thẳng — hồ sơ đứng im ở
    lần chụp cũ mãi mãi dù có số mới nằm ngay trên đĩa. Không cần khớp qua
    tiêu đề: ghi thẳng `video_id` vào hồ sơ để cô lập đúng hành vi của khung
    giờ, không lẫn với luật nối tiêu đề (đã có bài kiểm riêng ở trên)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "TESTK-NGAY"
        video_id = "abcdefghijk"
        snap = os.path.join(goc, "CHANNEL", kenh, "chi-so", video_id, "300h")
        os.makedirs(snap, exist_ok=True)
        with io.open(os.path.join(snap, "tong-quan.json"), "w", encoding="utf-8") as tep:
            json.dump({
                "video_id": video_id, "impressions": 9000, "ctr": 4.4, "views": 500,
                "avd_pct": 38, "avd_giay": 210, "gio_sau_dang": 300,
                "ngay_dang": "2026-08-01",
            }, tep, ensure_ascii=False)

        hv._luu_ho_so(goc, kenh, "TESTK-NGAY-0001",
                      {"tieu_de": "", "video_id": video_id, "chi_so": {}})

        tt = hv.cap_nhat_chi_so(goc, kenh, bay_gio=BAY_GIO)
        assert tt["cap_nhat_moc"] == 1, tt

        ho_so = hv.doc_ho_so(goc, kenh, "TESTK-NGAY-0001")
        assert ho_so["chi_so"]["ngay12"]["impressions"] == 9000   # 300 // 24 = 12
        assert ho_so["chi_so"]["ngay12"]["ctr"] == 4.4
        assert ho_so["so_lieu_moi_nhat"]["moc"] == "ngay12"
        assert ho_so["so_lieu_moi_nhat"]["impressions"] == 9000


def test_ten_moc_dung_bon_khung_gio():
    assert hv._ten_moc(18) == "24h"
    assert hv._ten_moc(22) == "24h"
    assert hv._ten_moc(35.9) == "24h"
    assert hv._ten_moc(36) == "48h"
    assert hv._ten_moc(56) == "48h"
    assert hv._ten_moc(60) == "72h"
    assert hv._ten_moc(95.9) == "72h"
    assert hv._ten_moc(144) == "7d"
    assert hv._ten_moc(239.9) == "7d"
    assert hv._ten_moc(None) == ""


def test_ten_moc_ngoai_bon_khung_thi_bucket_theo_ngay_khong_con_bi_bo(): # 29/09/2026
    """Trước đây MỌI giờ ngoài bốn khung tay (kể cả khe hở 96–144h, và MỌI giờ
    sau 240h) bị `_ten_moc` trả `""` rồi `cap_nhat_chi_so` bỏ luôn — đúng lỗi
    khiến `TL1-T7-0001` kẹt số liệu "7d" nhiều ngày dù tiện ích đã chụp thêm.
    Giờ mỗi NGÀY tuổi (24h) trong 30 ngày đầu nhận một khoá `ngayN` riêng."""
    assert hv._ten_moc(17.9) == "ngay0"          # trước 24h — chưa từng có khung
    assert hv._ten_moc(96) == "ngay4"            # đúng khe hở 96–144h (ngày 4–6)
    assert hv._ten_moc(143.9) == "ngay5"
    assert hv._ten_moc(240) == "ngay10"          # ngay sau "7d" — trước đây mất hẳn
    assert hv._ten_moc(336) == "ngay14"          # mốc 336h (14 ngày) tiện ích có chụp
    assert hv._ten_moc(672) == "ngay28"          # mốc 672h (28 ngày) tiện ích có chụp
    assert hv._ten_moc(719.9) == "ngay29"        # sát trần 30 ngày
    assert hv._ten_moc(720) == ""                # ngoài 30 ngày — không ai còn đọc
    assert hv._ten_moc(1000) == ""


# ── 3. `bu_ho_so` — bù hồ sơ cho gói đã bàn giao trước ─────────────────────────


def _dung_ke_hoach(goc, kenh, dong_them):
    cot = list(ke_hoach_dang.COT)
    hang = []
    for d in dong_them:
        dong = {ten: "" for ten in cot}
        dong.update(d)
        hang.append([dong.get(ten, "") for ten in cot])
    ke_hoach_dang.luu_bang(goc, kenh, hang, cot)


def test_bu_ho_so_tu_luot_con_song_tren_dia():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "K2"
        _dung_luot_gia(goc, kenh, "0001", tieu_de="Video đã đăng")
        _dung_ke_hoach(goc, kenh, [
            {"Mã gói": "K2-0001", "Tiêu đề": "Video đã đăng",
             "Trạng thái đăng": "ĐÃ ĐĂNG (tay)"},
        ])
        moi = hv.bu_ho_so(goc, kenh)
        assert moi == ["K2-0001"]
        ho_so = hv.doc_ho_so(goc, kenh, "K2-0001")
        assert ho_so["tieu_de"] == "Video đã đăng"
        assert ho_so["nguon_bu"].startswith("PROJECTS/AUTO")


def test_bu_ho_so_idempotent_bo_qua_da_co_ho_so():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "K3"
        _dung_luot_gia(goc, kenh, "0001", tieu_de="Video X")
        _dung_ke_hoach(goc, kenh, [
            {"Mã gói": "K3-0001", "Tiêu đề": "Video X", "Sẵn sàng": "x"},
        ])
        assert hv.bu_ho_so(goc, kenh) == ["K3-0001"]
        assert hv.bu_ho_so(goc, kenh) == [], "gọi lại không được tạo trùng/báo lại"


def test_bu_ho_so_bo_qua_dong_chua_ban_giao():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "K4"
        _dung_ke_hoach(goc, kenh, [
            {"Mã gói": "K4-0001", "Tiêu đề": "Chưa bàn giao"},  # Sẵn sàng và Trạng thái đều rỗng
        ])
        assert hv.bu_ho_so(goc, kenh) == []
        assert hv.doc_ho_so(goc, kenh, "K4-0001") is None


def test_bu_ho_so_lui_ve_ban_toi_gian_khi_luot_da_bi_don():
    """Thư mục `PROJECTS/AUTO/<kênh>/<lượt>` không còn (đã bị `don_dep` xoá) —
    vẫn bù được hồ sơ tối giản từ `DONE/` + kế hoạch, ghi rõ nguồn thiếu."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        goc = tmp
        kenh = "K5"
        thu_muc_goi = os.path.join(goc, "DONE", kenh, "K5-0001")
        os.makedirs(thu_muc_goi, exist_ok=True)
        with io.open(os.path.join(thu_muc_goi, "thumb.jpg"), "wb") as tep:
            tep.write(b"\xff\xd8\xff\xe0FAKE")
        _dung_ke_hoach(goc, kenh, [
            {"Mã gói": "K5-0001", "Tiêu đề": "Video đã dọn", "Sẵn sàng": "x"},
        ])
        moi = hv.bu_ho_so(goc, kenh)
        assert moi == ["K5-0001"]
        ho_so = hv.doc_ho_so(goc, kenh, "K5-0001")
        assert ho_so["tieu_de"] == "Video đã dọn"
        assert "đã bị dọn" in ho_so["nguon_bu"]
        assert os.path.isfile(hv.duong_anh_ho_so(goc, kenh, "K5-0001"))


def test_bu_ho_so_ke_hoach_trong_tra_rong():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        assert hv.bu_ho_so(str(tmp), "KHONG-TON-TAI") == []


# ── 4. `ghi_video_id` — nối id TRỰC TIẾP (Việc C, máy đăng DOM, 29/09/2026) ──


def test_ghi_video_id_dat_vao_ho_so_da_co(tmp_path):
    goc = str(tmp_path)
    os.makedirs(hv.duong_thu_muc_ho_so(goc, "TL1-T7"))
    hv._ghi_json(hv.duong_tep_ho_so(goc, "TL1-T7", "TL1-T7-0007"),
                 hv._khung_ho_so("TL1-T7", "TL1-T7-0007"))
    ok = hv.ghi_video_id(goc, "TL1-T7", "TL1-T7-0007", "abcDEF123", "30/09/2026 20:00")
    assert ok is True
    ho_so = hv.doc_ho_so(goc, "TL1-T7", "TL1-T7-0007")
    assert ho_so["video_id"] == "abcDEF123"
    assert ho_so["lich_dang"] == "30/09/2026 20:00"


def test_ghi_video_id_tu_tao_khung_khi_chua_co_ho_so(tmp_path):
    """Gói đăng trước khi hồ sơ hoá có / chưa kịp bù — không được để mất
    video_id chỉ vì chưa có tệp hồ sơ."""
    goc = str(tmp_path)
    ok = hv.ghi_video_id(goc, "TL1-T7", "TL1-T7-9999", "xyz789")
    assert ok is True
    ho_so = hv.doc_ho_so(goc, "TL1-T7", "TL1-T7-9999")
    assert ho_so is not None and ho_so["video_id"] == "xyz789"
    assert "lich_dang" not in ho_so, "không truyền lich thì đừng bịa trường rỗng"


def test_ghi_video_id_rong_thi_khong_lam_gi():
    ok = hv.ghi_video_id("/khong/ton/tai", "TL1-T7", "TL1-T7-0007", "")
    assert ok is False


# ── 4. Công thức + thăm dò (B4 bộ máy chiến lược, 30/09/2026) ─────────────────


def _ghi_so_luot(goc, kenh, ngay, runs):
    duong = os.path.join(goc, "CHANNEL", kenh, "tu-chay", "{0}.json".format(ngay))
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump({"runs": runs}, tep, ensure_ascii=False)


def test_tao_ho_so_ghi_cong_thuc_va_tham_do_tra_qua_so_luot(tmp_path):
    goc = str(tmp_path)
    _dung_luot_gia(goc, "K1", "0007")
    # lượt vừa chọn nguồn: sổ đã checkpoint TRƯỚC bàn giao (ma_goi còn rỗng → suy từ ma_luot)
    _ghi_so_luot(goc, "K1", "2026-09-30", [{
        "ma_luot": "0007", "ban_giao": {"ma_goi": ""},
        "nguon": {"nguon": "vph", "cong_thuc": "v7", "tham_do": True, "link": "https://youtu.be/SRC00000007"}}])
    hv.tao_ho_so(goc, "K1", "0007", "K1-0007")
    ho_so = hv.doc_ho_so(goc, "K1", "K1-0007")
    assert ho_so["cong_thuc"] == "v7" and ho_so["tham_do"] is True


def test_tao_ho_so_so_luot_cu_chi_co_nhan_nguon_va_thieu_so(tmp_path):
    goc = str(tmp_path)
    _dung_luot_gia(goc, "K1", "0001")
    _dung_luot_gia(goc, "K1", "0002")
    _ghi_so_luot(goc, "K1", "2026-09-22", [{
        "ma_luot": "0001", "ban_giao": {"ma_goi": "K1-0001"},
        "nguon": {"nguon": "mot_nut", "link": "https://youtu.be/SRC00000001"}}])
    hv.tao_ho_so(goc, "K1", "0001", "K1-0001")
    hv.tao_ho_so(goc, "K1", "0002", "K1-0002")  # không có trong sổ → khung mặc định
    assert hv.doc_ho_so(goc, "K1", "K1-0001")["cong_thuc"] == "mot_nut"
    ho_so = hv.doc_ho_so(goc, "K1", "K1-0002")
    assert ho_so["cong_thuc"] == "" and ho_so["tham_do"] is False
