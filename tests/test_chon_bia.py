"""Chọn ảnh bìa bằng giám khảo AI (`core/chon_bia.py`) — Việc 4 của
`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

Không gọi mạng, không cần Qt. Ảnh ứng viên là ảnh THẬT (Pillow, khối màu đặc)
ghi ra đĩa — `chon_bia` mở ảnh bằng Pillow nên không thể giả bằng bytes rác.

Năm nhóm bài, đúng danh sách "Test" của bản thiết kế:

1. `goi_chat` giả trả JSON — tổng điểm tính Ở MÁY theo đúng trọng số.
2. Luật loại (sai chữ / chữ vỡ / nhân vật dị dạng).
3. Đảo thứ tự nhãn A-G mỗi lượt — điểm vẫn quy đúng về ứng viên gốc.
4. Khám phá (kiểu kém hạng nhất ≤3%, ít dùng hơn).
5. Xuất jpg ≤2MB 1280×720; lùi khi `goi_chat` ném lỗi/không có.
"""

from __future__ import annotations

import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image  # noqa: E402

from core import chon_bia as cb  # noqa: E402
from core import ho_so_video as hv  # noqa: E402
from core import khuon_bia as kb  # noqa: E402
from core.kenh import duong_kenh, TEP_KENH  # noqa: E402


def _ghi_kenh_yaml(goc: str, ma: str) -> None:
    thu_muc = duong_kenh(goc, ma)
    os.makedirs(thu_muc, exist_ok=True)
    with io.open(os.path.join(thu_muc, TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "{0}"\n'.format(ma))


def _dung_ung_vien(thu_muc: str, so: int, mau=(200, 50, 50)) -> str:
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, "thumb_{0:03d}.png".format(so))
    Image.new("RGB", (1376, 768), mau).save(duong, format="PNG")
    return duong


def _goi_chat_diem(diem_theo_nhan: dict, *, loi_nang_theo_nhan=None, chu_theo_nhan=None):
    """Giả `goi_chat` — trả điểm CỐ ĐỊNH theo NHÃN (A/B/C…), bất kể ảnh nào
    được xếp vào nhãn đó (giám khảo giả không "nhìn" ảnh, chỉ theo kịch bản)."""
    def goi(loi_nhac, mo_hinh="claude-sonnet-5", khoa="", toi_da_token=8192, anh=None):
        cac = []
        for nhan, diem in diem_theo_nhan.items():
            cac.append({
                "nhan": nhan, "diem": diem,
                "chu_doc_ra": (chu_theo_nhan or {}).get(nhan, ""),
                "loi_nang": (loi_nang_theo_nhan or {}).get(nhan, []),
                "ly_do": "vì lý do giả {0}".format(nhan),
            })
        return json.dumps({"cac_anh": cac})
    return goi


_DIEM_10 = {"suc_hut_click": 10, "doc_duoc_co_nho": 10, "tuong_phan": 10,
           "cam_xuc": 10, "hop_noi_dung": 10, "bam_khuon_thang": 0, "khac_video_gan_day": 10}
_DIEM_2 = {"suc_hut_click": 2, "doc_duoc_co_nho": 2, "tuong_phan": 2,
          "cam_xuc": 2, "hop_noi_dung": 2, "bam_khuon_thang": 0, "khac_video_gan_day": 2}


# ── 1. Tổng điểm tính Ở MÁY theo đúng trọng số ────────────────────────────────


def test_tong_diem_cao_nhat_thang_va_xuat_chon(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))

    goi_chat = _goi_chat_diem({"A": _DIEM_10, "B": _DIEM_2})
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1, seed=1)
    assert ket is not None
    assert os.path.isfile(os.path.join(thu_muc, ket["tep"]))

    du = cb.doc_chon_bia(thu_muc)
    diem_theo_so = {u["so"]: u["tong_diem"] for u in du["ung_vien"]}
    thang_so = du["chon"]["so"]
    assert diem_theo_so[thang_so] == max(diem_theo_so.values())
    # Không có khuôn thắng (`bam_khuon_thang` không góp) — trọng số còn lại
    # (0,80) phải được CHIA LẠI cho đủ 100 điểm khi mọi tiêu chí khác chấm 10.
    assert diem_theo_so[thang_so] == 100.0


# ── 2. Luật loại ──────────────────────────────────────────────────────────────


def test_chu_vo_bi_loai_du_diem_cao_nhat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))

    goi_chat = _goi_chat_diem({"A": _DIEM_10, "B": _DIEM_2},
                              loi_nang_theo_nhan={"A": ["chu_vo"]})
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1, seed=1)
    du = cb.doc_chon_bia(thu_muc)
    assert du["chon"]["so"] != None
    loai_theo_so = {u["so"]: u["loai"] for u in du["ung_vien"]}
    thang_so = du["chon"]["so"]
    assert loai_theo_so[thang_so] == "", "ứng viên bị LOẠI không được thắng dù điểm cao hơn"


def test_sai_chu_bi_loai_khi_che_do_chu_bia_co_dinh(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))

    goi_chat = _goi_chat_diem(
        {"A": _DIEM_10, "B": _DIEM_2},
        chu_theo_nhan={"A": "chữ hoàn toàn khác", "B": "chữ bìa mong đợi"})
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="chữ bìa mong đợi", chu_bia_co_dinh=True,
                 goi_chat=goi_chat, so_luot_cham=1, seed=1)
    du = cb.doc_chon_bia(thu_muc)
    loai_theo_so = {u["so"]: u["loai"] for u in du["ung_vien"]}
    thang_so = du["chon"]["so"]
    assert loai_theo_so[thang_so] == ""


def test_chu_qua_dai_bi_loai_du_diem_cao_nhat(tmp_path):
    """Thêm 29/09/2026 (insight tâm lý Nhật): chữ đọc ra > 14 ký tự (không tính dấu câu/
    khoảng trắng) bị LOẠI THẲNG, kể cả khi khớp đúng `chu_bia` mong đợi và điểm cao nhất —
    khán giả thật 55+ xem nhiều trên TV/điện thoại, chữ dài không đọc được."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))

    chu_dai = "một câu chữ bìa rất là dài quá mười bốn ký tự"  # >> 14 ký tự sau chuẩn hoá
    goi_chat = _goi_chat_diem(
        {"A": _DIEM_10, "B": _DIEM_2},
        chu_theo_nhan={"A": chu_dai, "B": "ngắn gọn"})
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia=chu_dai, goi_chat=goi_chat, so_luot_cham=1, seed=1)
    du = cb.doc_chon_bia(thu_muc)
    loai_theo_so = {u["so"]: u["loai"] for u in du["ung_vien"]}
    thang_so = du["chon"]["so"]
    assert loai_theo_so[thang_so] == "", "ứng viên chữ quá dài không được thắng dù điểm cao hơn"
    assert du["chon"]["chu_doc_ra"] == "ngắn gọn"


def test_moi_ung_vien_bi_loai_chon_it_chu_nhat_va_canh_bao(tmp_path):
    """Cả hai ứng viên đều chữ quá dài (mọi tấm bị loại) — vẫn phải ra MỘT tấm (không chặn
    sản xuất): chọn tấm ÍT CHỮ NHẤT trong hai, và ghi cảnh báo."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))

    chu_rat_dai = "một câu chữ bìa cực kỳ dài vượt xa mười bốn ký tự cho phép"
    chu_hoi_dai = "chữ hơi dài hai mươi mốt ký tự nha"  # >20 (trần 30/09/2026)
    goi_chat = _goi_chat_diem(
        {"A": _DIEM_10, "B": _DIEM_2},
        chu_theo_nhan={"A": chu_rat_dai, "B": chu_hoi_dai})
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1, seed=1)
    assert ket is not None
    du = cb.doc_chon_bia(thu_muc)
    assert du["chon"]["canh_bao"], "phải ghi cảnh báo khi mọi ứng viên bị loại"
    assert du["chon"]["chu_doc_ra"] == chu_hoi_dai, "phải chọn tấm ÍT CHỮ HƠN trong hai tấm xấu"
    assert all(u["loai"] for u in du["ung_vien"]), "cả hai ứng viên đều phải mang lý do loại"


# ── 3. Đảo thứ tự nhãn — điểm vẫn quy đúng về ứng viên gốc ───────────────────


def test_mot_luot_cham_dao_nhan_van_quy_dung_ve_so_goc(tmp_path):
    thu_muc = os.path.join(str(tmp_path), "thumb")
    d1 = _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    d2 = _dung_ung_vien(thu_muc, 2, (50, 200, 50))
    ung_vien = [cb.UngVienBia(so=1, duong=d1, kieu="portrait_main"),
               cb.UngVienBia(so=2, duong=d2, kieu="dramatic_scene")]

    # Tự tính TRƯỚC permutation mà `rng.shuffle` sẽ ra, với CÙNG hạt giống và
    # CÙNG thứ tự đưa vào — đúng thao tác mà `_mot_luot_cham` sẽ làm.
    rng_du_doan = random.Random(7)
    thu_tu = list(ung_vien)
    rng_du_doan.shuffle(thu_tu)
    nhan_theo_so_du_doan = {u.so: cb._CHU_A_G[i] for i, u in enumerate(thu_tu)}

    goi_chat = _goi_chat_diem({"A": _DIEM_10, "B": _DIEM_2})
    ket = cb._mot_luot_cham(
        goi_chat, ung_vien, tieu_de="T", chu_bia="C", mo_dau="", khuon_thang=None,
        anh_gan_day=(), mo_hinh="", khoa="k", rng=random.Random(7))

    for so, nhan in nhan_theo_so_du_doan.items():
        diem_mong_doi = _DIEM_10 if nhan == "A" else _DIEM_2
        assert ket[so].diem["suc_hut_click"] == diem_mong_doi["suc_hut_click"], (
            "điểm của nhãn {0} phải quy đúng về ứng viên {1} sau khi đảo".format(nhan, so))


# ── 4. Khám phá ───────────────────────────────────────────────────────────────


def test_kham_pha_chon_hang_nhi_khi_kem_it_va_it_dung_hon(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    # 10 hồ sơ gần đây đều dùng "portrait_main" — "dramatic_scene" chưa từng
    # dùng, nên ÍT DÙNG HƠN hẳn.
    thu_muc_ho_so = hv.duong_thu_muc_ho_so(goc, "K1")
    os.makedirs(thu_muc_ho_so, exist_ok=True)
    for i in range(10):
        ma_goi = "K1-{0:04d}".format(i)
        with io.open(os.path.join(thu_muc_ho_so, ma_goi + ".json"), "w", encoding="utf-8") as tep:
            json.dump({"thumbnail": {"kieu": "portrait_main"}}, tep)

    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))  # portrait_main — hạng nhất (điểm nhỉnh hơn 1%)
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))  # dramatic_scene — hạng nhì, ít dùng hơn

    diem_a = dict(_DIEM_10)
    diem_b = dict(_DIEM_10)
    diem_b["suc_hut_click"] = 9.5  # kém một chút, vẫn trong ngưỡng khám phá 3%
    goi_chat = _goi_chat_diem({"A": diem_a, "B": diem_b})
    ket = cb.chon(goc, "K1", thu_muc,
                 ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1,
                 kham_pha_bat=True, seed=0)
    du = cb.doc_chon_bia(thu_muc)
    assert du["chon"]["chon_boi"] == "kham_pha"
    assert du["chon"]["kieu"] == "dramatic_scene"


def test_kham_pha_nguong_rong_khi_chua_co_khuon_rieng(tmp_path):
    """30/09/2026, Việc 4b: kênh CHƯA có khuôn riêng (không có
    `khuon-bia-thang.json`) dùng ngưỡng khám phá RỘNG HƠN hẳn
    (`NGUONG_KHAM_PHA_PCT_CHUA_CO_KHUON_RIENG = 20.0`) — một ứng viên kém
    hạng nhất ~15 điểm (vượt ngưỡng 3.0 cũ, còn trong ngưỡng 20.0 mới) vẫn
    được chuyển sang nếu thuộc kiểu ÍT DÙNG hơn."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc_ho_so = hv.duong_thu_muc_ho_so(goc, "K1")
    os.makedirs(thu_muc_ho_so, exist_ok=True)
    for i in range(10):
        ma_goi = "K1-{0:04d}".format(i)
        with io.open(os.path.join(thu_muc_ho_so, ma_goi + ".json"), "w", encoding="utf-8") as tep:
            json.dump({"thumbnail": {"kieu": "portrait_main"}}, tep)

    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))  # portrait_main — hạng nhất
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))  # dramatic_scene — hạng nhì, ít dùng hơn

    diem_a = dict(_DIEM_10)
    diem_b = dict(_DIEM_10)
    diem_b["suc_hut_click"] = 5.2  # kém ~15 điểm — vượt ngưỡng cũ 3.0, trong ngưỡng mới 20.0
    goi_chat = _goi_chat_diem({"A": diem_a, "B": diem_b})
    ket = cb.chon(goc, "K1", thu_muc,
                 ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1,
                 kham_pha_bat=True, seed=0)
    du = cb.doc_chon_bia(thu_muc)
    assert du["co_khuon_thang"] is False
    assert du["chon"]["chon_boi"] == "kham_pha"
    assert du["chon"]["kieu"] == "dramatic_scene"
    assert "chưa có khuôn riêng" in du["chon"]["ly_do"]


def test_khuon_het_hieu_luc_coi_nhu_chua_co_khuon(tmp_path):
    """Một `khuon-bia-thang.json` với `het_hieu_luc: true` (migrate 30/09/2026,
    khuôn mượn nhóm cũ) phải bị LỌC ngay khi đọc — `chon()` coi như KHÔNG có
    khuôn thắng: `co_khuon_thang` False, và vẫn dùng ngưỡng khám phá RỘNG
    (không phải ngưỡng 3.0 hẹp của khuôn còn hợp lệ)."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    kb._ghi_khuon(goc, "K1", {
        "video_id": "vid-cu", "kenh_goc": "TL3-T7", "ctr": 9.73, "imp": 19618,
        "nguon": "nhom", "khuon_chu": {"bo_cuc": "chân dung"},
        "ngay_so_lieu": "2026-09-20 08:00",
        "het_hieu_luc": True, "ghi_chu_het_hieu_luc": "tắt mượn khuôn nhóm",
    })

    thu_muc_ho_so = hv.duong_thu_muc_ho_so(goc, "K1")
    os.makedirs(thu_muc_ho_so, exist_ok=True)
    for i in range(10):
        ma_goi = "K1-{0:04d}".format(i)
        with io.open(os.path.join(thu_muc_ho_so, ma_goi + ".json"), "w", encoding="utf-8") as tep:
            json.dump({"thumbnail": {"kieu": "portrait_main"}}, tep)

    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))

    diem_a = dict(_DIEM_10)
    diem_b = dict(_DIEM_10)
    diem_b["suc_hut_click"] = 5.2
    goi_chat = _goi_chat_diem({"A": diem_a, "B": diem_b})
    cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
           tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1,
           kham_pha_bat=True, seed=0)
    du = cb.doc_chon_bia(thu_muc)
    assert du["co_khuon_thang"] is False
    assert du["chon"]["chon_boi"] == "kham_pha"
    assert du["chon"]["kieu"] == "dramatic_scene"


def test_khong_kham_pha_khi_tat_co(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))
    diem_a = dict(_DIEM_10)
    diem_b = dict(_DIEM_10)
    diem_b["suc_hut_click"] = 9.5
    goi_chat = _goi_chat_diem({"A": diem_a, "B": diem_b})
    ket = cb.chon(goc, "K1", thu_muc,
                 ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1,
                 kham_pha_bat=False, seed=0)
    du = cb.doc_chon_bia(thu_muc)
    assert du["chon"]["chon_boi"] == "ai"


# ── 5. Xuất jpg + đường lùi ────────────────────────────────────────────────────


def test_xuat_jpg_duoi_2mb_dung_kich_thuoc(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    goi_chat = _goi_chat_diem({"A": _DIEM_10})
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat, so_luot_cham=1, seed=1)
    duong = os.path.join(thu_muc, ket["tep"])
    assert os.path.getsize(duong) < cb.TRAN_DUNG_LUONG
    with Image.open(duong) as im:
        assert im.size == (1280, 720)
        assert im.format == "JPEG"


def test_da_co_chon_cua_nguoi_thi_giu_nguyen(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))
    with io.open(os.path.join(thu_muc, "CHON-thumb_002.jpg"), "wb") as tep:
        tep.write(b"\xff\xd8\xff\xe0ANH-NGUOI-CHON")

    goi = {"n": 0}

    def goi_chat_khong_duoc_goi(*a, **kw):
        goi["n"] += 1
        raise AssertionError("không được chấm khi đã có CHON- của người")

    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_chat_khong_duoc_goi, so_luot_cham=1)
    assert ket["chon_boi"] == "nguoi"
    assert ket["tep"] == "CHON-thumb_002.jpg"
    assert goi["n"] == 0


def test_khong_co_goi_chat_dung_duong_lui_khong_nem_loi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))
    _dung_ung_vien(thu_muc, 2, (50, 200, 50))
    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main", 2: "dramatic_scene"},
                 tieu_de="T", chu_bia="C", goi_chat=None, so_luot_cham=1)
    assert ket is not None
    assert ket["chon_boi"] == "luat"
    assert os.path.isfile(os.path.join(thu_muc, ket["tep"]))


def test_goi_chat_nem_loi_van_ra_jpg_khong_chan(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb")
    _dung_ung_vien(thu_muc, 1, (200, 50, 50))

    def goi_hong(*a, **kw):
        raise RuntimeError("mạng rớt giả lập")

    ket = cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={1: "portrait_main"},
                 tieu_de="T", chu_bia="C", goi_chat=goi_hong, so_luot_cham=1)
    assert ket is not None
    assert ket["chon_boi"] == "luat"
    assert os.path.isfile(os.path.join(thu_muc, ket["tep"]))


def test_thu_muc_trong_tra_none(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    thu_muc = os.path.join(str(tmp_path), "thumb-trong")
    os.makedirs(thu_muc, exist_ok=True)
    assert cb.chon(goc, "K1", thu_muc, ten_kieu_theo_so={}, goi_chat=None) is None


# ── Mối nối tên tệp ↔ kiểu (kiểu thứ 7, Việc 4) ───────────────────────────────


def test_kieu_thu_bay_la_khuon_thang():
    from core.auto_khau import KIEU_THUMB
    assert len(KIEU_THUMB) == 7
    assert KIEU_THUMB[-1][0] == "khuon_thang"
    assert hv._version_desc_tu_ten_anh("CHON-thumb_007.jpg") == "khuon_thang"
