"""Khuôn ảnh bìa thắng (`core/khuon_bia.py`) — Việc 4 của
`workspace/THIET-KE-DUNG-VA-VONG-HOC.md`.

Không gọi mạng, không cần Qt. `tai_anh` (tham số của `anh_da_dang`/`cap_nhat`)
luôn được truyền một hàm GIẢ trong các bài này — không lượt nào chạm Internet.

Bốn nhóm bài:

1. `tim_video_thang`: dựng lại đúng tình huống TL3/TL1 thật (28/09/2026) —
   kênh đủ CTR thắng bằng chính nó; kênh không đủ mượn khuôn NHÓM.
2. `cap_nhat`: ghi `khuon-bia-thang.json`, chỉ gọi AI khi người thắng đổi,
   giữ lịch sử, không xoá khuôn cũ khi lượt sau chưa đủ số liệu.
3. Cờ AVD thấp → `chi_hoc_bo_cuc`.
4. `doc_bai_hoc_anh_bia` — câu chèn vào lời nhắc sinh ảnh bìa.
"""

from __future__ import annotations

import io
import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ho_so_video as hv  # noqa: E402
from core import khuon_bia as kb  # noqa: E402
from core.kenh import duong_kenh, TEP_KENH  # noqa: E402


def _ghi_kenh_yaml(goc: str, ma: str, *, nhom: str = "",
                   bia_khuon_nhom: Optional[bool] = None) -> None:
    thu_muc = duong_kenh(goc, ma)
    os.makedirs(thu_muc, exist_ok=True)
    with io.open(os.path.join(thu_muc, TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "{0}"\n'.format(ma))
        if nhom:
            tep.write('nhom: "{0}"\n'.format(nhom))
        if bia_khuon_nhom is not None:
            tep.write('bia_khuon_nhom: {0}\n'.format("true" if bia_khuon_nhom else "false"))


def _ghi_ho_so(goc: str, kenh: str, ma_goi: str, *, video_id: str, ctr: float,
               imp: float, moc_gio: float, avd_pct=None, ten_moc: str = "48h",
               tieu_de: str = "") -> None:
    thu_muc = hv.duong_thu_muc_ho_so(goc, kenh)
    os.makedirs(thu_muc, exist_ok=True)
    ho_so = {
        "ma_goi": ma_goi, "kenh": kenh, "tieu_de": tieu_de or ma_goi,
        "video_id": video_id, "thumbnail": {"tep": "thumb_001.png"},
        "chi_so": {ten_moc: {"impressions": imp, "ctr": ctr, "avd_pct": avd_pct,
                             "moc_gio_that": moc_gio, "luc_chup": "2026-09-25 19:19"}},
    }
    with io.open(os.path.join(thu_muc, "{0}.json".format(ma_goi)), "w", encoding="utf-8") as tep:
        json.dump(ho_so, tep, ensure_ascii=False)


def _tai_anh_gia(url: str):
    return b"\xff\xd8\xff\xe0FAKE-JPEG"


def _them_video_nen_thap(goc: str, kenh: str, *, tu: int = 900) -> None:
    """Hai video CTR THẤP của CHÍNH kênh — với chỉ một video, kênh không có gì
    để so (trung vị = chính nó, không ai tự thắng nổi 1,3× chính mình). Cần
    ≥3 mẫu RIÊNG để `tim_video_thang` dùng trung vị của chính kênh (bản thiết
    kế mục "Khuôn thắng" — <3 mẫu mới lùi về trung vị NHÓM)."""
    for i in range(2):
        _ghi_ho_so(goc, kenh, "{0}-{1:04d}".format(kenh, tu + i),
                  video_id="vid-nen-{0}".format(tu + i), ctr=1.0, imp=1500, moc_gio=48)


# ── 1. `tim_video_thang` — đúng tình huống TL3/TL1 thật (28/09/2026) ─────────


def test_kenh_du_ctr_tu_thang_bang_chinh_no(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _them_video_nen_thap(goc, "K3")  # đủ ≥3 mẫu RIÊNG để tự làm chuẩn cho mình
    thang = kb.tim_video_thang(goc, "K3")
    assert thang is not None
    assert thang["video_id"] == "vid-thang"
    assert thang["nguon"] == "kenh"


def test_bat_co_thi_muon_khuon_nhom_nhu_cu(tmp_path):
    """Tái hiện đúng số đo thật 28/09/2026: TL3 (CTR 9,73%) thắng, TL1 (CTR
    3,14%) không đạt ngưỡng của chính nó lẫn ngưỡng nhóm. Cơ chế MƯỢN vẫn còn
    hoạt động khi cờ `cho_phep_muon_nhom` được BẬT TƯỜNG MINH (mặc định đã
    đổi thành TẮT từ 30/09/2026, Việc 4b — xem `test_mac_dinh_khong_muon_*`)."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3", nhom="tam-ly-gia")
    _ghi_kenh_yaml(goc, "K1", nhom="tam-ly-gia")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _ghi_ho_so(goc, "K1", "K1-0001", video_id="vid-thua", ctr=3.14, imp=1754,
              moc_gio=56, avd_pct=35.0)

    thang_k3 = kb.tim_video_thang(goc, "K3", cho_phep_muon_nhom=True)
    assert thang_k3["video_id"] == "vid-thang" and thang_k3["nguon"] == "kenh"

    thang_k1 = kb.tim_video_thang(goc, "K1", cho_phep_muon_nhom=True)
    assert thang_k1 is not None
    assert thang_k1["video_id"] == "vid-thang", "K1 phải MƯỢN đúng video đang thắng của K3"
    assert thang_k1["nguon"] == "nhom"


def test_mac_dinh_khong_muon_khuon_nhom(tmp_path):
    """30/09/2026, Việc 4b: KHÔNG truyền `cho_phep_muon_nhom` và không khai
    `bia_khuon_nhom` trong `kenh.yaml` — mặc định giờ là TẮT, K1 phải trả
    `None` dù K3 đang thắng thật (đúng dữ liệu K3/K1 y hệt bài mượn cũ)."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3", nhom="tam-ly-gia")
    _ghi_kenh_yaml(goc, "K1", nhom="tam-ly-gia")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _them_video_nen_thap(goc, "K3")  # ≥3 mẫu RIÊNG — K3 tự làm chuẩn cho chính nó (tier-1)
    _ghi_ho_so(goc, "K1", "K1-0001", video_id="vid-thua", ctr=3.14, imp=1754,
              moc_gio=56, avd_pct=35.0)

    assert kb.tim_video_thang(goc, "K3")["nguon"] == "kenh"
    assert kb.tim_video_thang(goc, "K1") is None


def test_doc_co_muon_nhom_tu_kenh_yaml(tmp_path):
    """Không truyền tham số tường minh, nhưng `kenh.yaml` của K1 tự khai
    `bia_khuon_nhom: true` — `tim_video_thang` phải TỰ ĐỌC cờ này và vẫn mượn
    được, chốt đường đọc cấu hình tự động (không chỉ đường truyền tham số)."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3", nhom="tam-ly-gia")
    _ghi_kenh_yaml(goc, "K1", nhom="tam-ly-gia", bia_khuon_nhom=True)
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _ghi_ho_so(goc, "K1", "K1-0001", video_id="vid-thua", ctr=3.14, imp=1754,
              moc_gio=56, avd_pct=35.0)

    thang_k1 = kb.tim_video_thang(goc, "K1")
    assert thang_k1 is not None
    assert thang_k1["video_id"] == "vid-thang"
    assert thang_k1["nguon"] == "nhom"


def test_khong_ai_dat_nguong_tra_none(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    _ghi_ho_so(goc, "K1", "K1-0001", video_id="v1", ctr=2.0, imp=1200, moc_gio=48)
    assert kb.tim_video_thang(goc, "K1") is None


def test_bo_qua_diem_chup_ngoai_khung_36_96h(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    # Chụp ở 22h (ngoài khung, tên mốc "24h" không nằm trong _MOC_CHAP_NHAN)
    # thì không được coi là ứng viên dù CTR rất cao.
    _ghi_ho_so(goc, "K1", "K1-0001", video_id="v1", ctr=50.0, imp=5000, moc_gio=22,
              ten_moc="24h")
    assert kb.tim_video_thang(goc, "K1") is None


def test_duoi_nguong_impressions_thi_loai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K1")
    _ghi_ho_so(goc, "K1", "K1-0001", video_id="v1", ctr=50.0, imp=999, moc_gio=48)
    assert kb.tim_video_thang(goc, "K1") is None


# ── 2. `cap_nhat` — ghi khuôn, gọi AI đúng lúc, giữ lịch sử ──────────────────


def _goi_chat_gia(so_lan: dict):
    def goi(loi_nhac, mo_hinh="claude-sonnet-5", khoa="", toi_da_token=8192, anh=""):
        so_lan["n"] = so_lan.get("n", 0) + 1
        return json.dumps({
            "bo_cuc": "chân dung cận mặt, lệch trái", "mau_sac": "đỏ/đen",
            "anh_sang": "một nguồn sáng ấm từ trên", "vi_tri_chu": "khối chữ to nửa trên",
            "kieu_chu": "viền đen dày", "diem_hut_mat": "ánh mắt nhân vật",
        })
    return goi


def test_cap_nhat_ghi_khuon_va_goi_ai_dung_mot_lan(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _them_video_nen_thap(goc, "K3")
    so_lan = {}
    ket = kb.cap_nhat(goc, "K3", _goi_chat_gia(so_lan), tai_anh=_tai_anh_gia)
    assert ket is not None
    assert ket["video_id"] == "vid-thang"
    assert ket["khuon_chu"]["bo_cuc"].startswith("chân dung")
    assert so_lan["n"] == 1

    tren_dia = kb.doc_khuon(goc, "K3")
    assert tren_dia["video_id"] == "vid-thang"
    assert len(tren_dia["lich_su"]) == 1

    # Gọi lại lần 2, CÙNG người thắng (số đo có thể tăng nhẹ) — KHÔNG được
    # gọi AI thêm lần nào (giữ khuôn chữ cũ, chỉ cập nhật số đo).
    ket2 = kb.cap_nhat(goc, "K3", _goi_chat_gia(so_lan), tai_anh=_tai_anh_gia)
    assert ket2 is not None
    assert so_lan["n"] == 1, "người thắng không đổi thì không được tốn thêm lượt AI"
    assert len(kb.doc_khuon(goc, "K3")["lich_su"]) == 1


def test_cap_nhat_khong_goi_chat_van_ghi_video_thang_khong_co_khuon_chu(tmp_path):
    """`vong_hoc.truoc_luot` gọi trước Việc 4 luôn truyền `goi_chat=None` — Việc
    4 vẫn phải ghi lại VIDEO THẮNG (để test theo sau, hoặc lượt gọi có goi_chat
    thật sau này bổ sung khuôn chữ), chỉ là chưa có khuôn chữ."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _them_video_nen_thap(goc, "K3")
    ket = kb.cap_nhat(goc, "K3", None, tai_anh=_tai_anh_gia)
    assert ket is not None
    assert ket["video_id"] == "vid-thang"
    assert ket["khuon_chu"] == {}


def test_cap_nhat_nguoi_thang_doi_thi_goi_lai_ai_va_them_lich_su(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-cu", ctr=9.73, imp=19618, moc_gio=56)
    _them_video_nen_thap(goc, "K3")
    so_lan = {}
    kb.cap_nhat(goc, "K3", _goi_chat_gia(so_lan), tai_anh=_tai_anh_gia)
    assert so_lan["n"] == 1

    # Video mới thắng đậm hơn.
    _ghi_ho_so(goc, "K3", "K3-0002", video_id="vid-moi", ctr=15.0, imp=20000, moc_gio=48)
    ket = kb.cap_nhat(goc, "K3", _goi_chat_gia(so_lan), tai_anh=_tai_anh_gia)
    assert ket["video_id"] == "vid-moi"
    assert so_lan["n"] == 2, "người thắng ĐỔI thì phải gọi AI lại"
    assert len(kb.doc_khuon(goc, "K3")["lich_su"]) == 2


def test_cap_nhat_chua_ai_thang_thi_khong_ghi_gi_va_giu_khuon_cu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618, moc_gio=56)
    _them_video_nen_thap(goc, "K3")
    kb.cap_nhat(goc, "K3", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    cu = kb.doc_khuon(goc, "K3")
    assert cu is not None

    # Lượt sau: hồ sơ mới chưa có đủ số liệu (chưa nối video_id) — không có
    # ứng viên nào đạt ngưỡng nữa trong tính toán (giả lập kênh vừa mất dữ liệu).
    import shutil
    shutil.rmtree(hv.duong_thu_muc_ho_so(goc, "K3"))
    os.makedirs(hv.duong_thu_muc_ho_so(goc, "K3"))
    ket = kb.cap_nhat(goc, "K3", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    assert ket is None
    # Khuôn cũ vẫn còn nguyên — MỘT lượt chưa đủ số liệu không xoá khuôn cũ.
    assert kb.doc_khuon(goc, "K3") == cu


# ── 3. Cờ AVD thấp ────────────────────────────────────────────────────────────


def test_avd_thap_hon_han_trung_vi_thi_gan_co_chi_hoc_bo_cuc(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    # Hai video đủ tuổi khác, AVD cao (38%, 40%) — trung vị ~39%; video THẮNG
    # avd 20% < 0,6×39% ≈ 23,4% → phải gắn cờ.
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _ghi_ho_so(goc, "K3", "K3-0002", video_id="vid-b", ctr=1.0, imp=1500,
              moc_gio=48, avd_pct=38.0)
    _ghi_ho_so(goc, "K3", "K3-0003", video_id="vid-c", ctr=1.0, imp=1500,
              moc_gio=48, avd_pct=40.0)
    ket = kb.cap_nhat(goc, "K3", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    assert ket["chi_hoc_bo_cuc"] is True


def test_avd_gan_trung_vi_thi_khong_gan_co(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=35.0)
    _ghi_ho_so(goc, "K3", "K3-0002", video_id="vid-b", ctr=1.0, imp=1500,
              moc_gio=48, avd_pct=36.0)
    _ghi_ho_so(goc, "K3", "K3-0003", video_id="vid-c", ctr=1.0, imp=1500,
              moc_gio=48, avd_pct=34.0)
    ket = kb.cap_nhat(goc, "K3", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    assert ket["chi_hoc_bo_cuc"] is False


# ── 4. `doc_bai_hoc_anh_bia` ──────────────────────────────────────────────────


def test_doc_bai_hoc_anh_bia_placeholder_khi_chua_co_khuon(tmp_path):
    """30/09/2026, Việc 4b: không còn trả `""` — trả câu placeholder cố định
    để lời nhắc sinh ảnh bìa luôn có một câu để chèn."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    assert kb.doc_bai_hoc_anh_bia(goc, "K3") == (
        "(kênh chưa có dữ liệu thumbnail riêng — đang thử nghiệm nhiều kiểu)")


def test_doc_bai_hoc_anh_bia_placeholder_khi_khuon_het_hieu_luc(tmp_path):
    """Khuôn có đủ `video_id`/`khuon_chu` nhưng bị đánh dấu `het_hieu_luc`
    (migrate 30/09/2026, khuôn mượn nhóm cũ của TL1-T7/TL2-T7) — phải trả
    đúng câu placeholder, KHÔNG render khuôn chữ cũ."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _them_video_nen_thap(goc, "K3")
    kb.cap_nhat(goc, "K3", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    khuon = kb.doc_khuon(goc, "K3")
    khuon["het_hieu_luc"] = True
    kb._ghi_khuon(goc, "K3", khuon)
    assert kb.doc_bai_hoc_anh_bia(goc, "K3") == (
        "(kênh chưa có dữ liệu thumbnail riêng — đang thử nghiệm nhiều kiểu)")


# ── 5. 13/10/2026 — ứng viên từ video THẬT (`chi-so/`) + luật bằng chứng một câu ──


def _ghi_chi_so(goc: str, kenh: str, ma: str, *, ngay: str, moc, tieu_de: str = "") -> None:
    """Một video THẬT trong `chi-so/<ma>/<Nh>/` (không hồ sơ) — `moc` = [(giờ, hiển thị, ctr), …]."""
    for gio, imp, ctr in moc:
        d = os.path.join(duong_kenh(goc, kenh), "chi-so", ma, "{0}h".format(gio))
        os.makedirs(d, exist_ok=True)
        with io.open(os.path.join(d, "tong-quan.json"), "w", encoding="utf-8") as tep:
            json.dump({"impressions": imp, "ctr": ctr, "views": imp * ctr / 100.0}, tep)
        with io.open(os.path.join(d, "_thong-tin.json"), "w", encoding="utf-8") as tep:
            json.dump({"tieu_de": tieu_de or ma, "ngay_dang": ngay + "T11:00:00.000Z"}, tep)


def _kenh_that(goc: str, ma: str = "K4", ngay_bat_dau: str = "") -> None:
    _ghi_kenh_yaml(goc, ma)
    if ngay_bat_dau:
        with io.open(os.path.join(duong_kenh(goc, ma), TEP_KENH), "a", encoding="utf-8") as tep:
            tep.write('ngay_bat_dau: "{0}"\n'.format(ngay_bat_dau))
    for i, (imp, ctr) in enumerate([(5000, 3.0), (8000, 4.0), (9000, 4.5), (6000, 5.0), (7000, 5.5)]):
        _ghi_chi_so(goc, ma, "vidNEN{0:05d}".format(i), ngay="2026-09-0{0}".format(i + 1),
                    moc=[(48, imp / 2, ctr + 1), (200, imp, ctr)])


def test_ung_vien_tu_chi_so_khong_can_ho_so(tmp_path):
    """Kênh chuyển máy: KHÔNG có hồ sơ nào, mọi video thắng chỉ có trong `chi-so/` — vẫn ra khuôn (bản chụp
    MUỘN NHẤT), `ma_goi` rỗng."""
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidTHANG001", ngay="2026-09-20", tieu_de="video thắng",
                moc=[(48, 9000, 9.0), (300, 31666, 7.71)])
    thang = kb.tim_video_thang(goc, "K4")
    assert thang is not None and thang["video_id"] == "vidTHANG001"
    assert thang["ma_goi"] == "" and thang["nguon"] == "kenh"
    assert thang["ctr"] == 7.71 and thang["impressions"] == 31666
    assert thang["trung_vi_ctr_that"] is not None


def test_ngay_bat_dau_loai_video_doi_truoc(tmp_path):
    goc = str(tmp_path)
    _kenh_that(goc, ngay_bat_dau="2026-08-22")
    _ghi_chi_so(goc, "K4", "vidCU000001", ngay="2018-12-27", moc=[(400, 35701, 7.97)])
    assert kb.tim_video_thang(goc, "K4") is None, "video đời trước của kênh không được làm khuôn"


def test_video_chua_du_36h_khong_lam_ung_vien(tmp_path):
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidNON00001", ngay="2026-10-12", moc=[(20, 40000, 12.0)])
    assert kb.tim_video_thang(goc, "K4") is None


def test_luat_bang_chung_hien_thi_lon_tren_trung_vi(tmp_path):
    """CTR 5,9% / 106k hiển thị (trên trung vị kênh 4,5%) ĐẠT; 9% / 3k hiển thị (CTR cao, ít hiển thị) không."""
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidLON00001", ngay="2026-09-10", moc=[(300, 106000, 5.9)])
    _ghi_chi_so(goc, "K4", "vidIT000001", ngay="2026-09-11", moc=[(300, 3000, 9.0)])
    thang = kb.tim_video_thang(goc, "K4")
    assert thang is not None and thang["video_id"] == "vidLON00001"
    assert thang["trung_vi_ctr_that"] < 5.9


def test_luat_bang_chung_chon_ctr_cao_nhat_trong_cac_ung_vien_dat(tmp_path):
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidLON00001", ngay="2026-09-10", moc=[(300, 106000, 5.9)])
    _ghi_chi_so(goc, "K4", "vidCAO00001", ngay="2026-09-12", moc=[(300, 31666, 7.71)])
    assert kb.tim_video_thang(goc, "K4")["video_id"] == "vidCAO00001"


def test_hien_thi_lon_duoi_trung_vi_khong_dat(tmp_path):
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidLON00002", ngay="2026-09-10", moc=[(300, 200000, 3.2)])
    assert kb.tim_video_thang(goc, "K4") is None


def test_cap_nhat_khuon_tu_chi_so_dung_bia_that_va_ghi_trung_vi(tmp_path):
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidTHANG001", ngay="2026-09-20", moc=[(300, 31666, 7.71)])
    url_da_tai = []

    def tai(url):
        url_da_tai.append(url)
        return b"\xff\xd8\xff\xe0FAKE-JPEG"
    ket = kb.cap_nhat(goc, "K4", _goi_chat_gia({}), tai_anh=tai)
    assert ket["video_id"] == "vidTHANG001" and ket["anh_that"] is True
    assert url_da_tai and "vidTHANG001" in url_da_tai[0]
    assert ket["tep"].endswith("vidTHANG001-that.jpg")
    assert ket["trung_vi_ctr_that"] is not None
    assert ket["thu"]["trang_thai"] == "cho_thu", "khuôn mới vẫn phải qua vòng tạo thử"


def test_doc_bai_hoc_anh_bia_co_so_do_va_khuon_chu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, "K3")
    _ghi_ho_so(goc, "K3", "K3-0001", video_id="vid-thang", ctr=9.73, imp=19618,
              moc_gio=56, avd_pct=20.0)
    _them_video_nen_thap(goc, "K3")
    kb.cap_nhat(goc, "K3", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    chu = kb.doc_bai_hoc_anh_bia(goc, "K3")
    assert "9.73" in chu or "9,73" in chu
    assert "chân dung" in chu


# ── 6. 16/10/2026 — vế NỚI của luật bằng chứng (không video nào đạt luật chặt) ──


def test_luat_noi_chon_bia_nhieu_luot_bam_nhat_khi_khong_ai_dat_luat_chat(tmp_path):
    """Kênh không video nào đạt CTR ≥ 7% / ≥ 10k hay ≥ 50k: bìa thật ≥ 10k hiển thị, CTR ≥ 1,2 × trung vị kênh làm
    khuôn — nhiều LƯỢT BẤM (hiển thị × CTR) nhất thắng; dưới 1,2 × trung vị thì không."""
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidNOI00001", ngay="2026-09-10", moc=[(300, 25000, 6.0)])   # 1.500 lượt bấm
    _ghi_chi_so(goc, "K4", "vidNOI00002", ngay="2026-09-11", moc=[(300, 12000, 6.5)])   # 780 lượt bấm
    _ghi_chi_so(goc, "K4", "vidDUOI0001", ngay="2026-09-12", moc=[(300, 30000, 5.0)])   # = trung vị, < 1,2×
    thang = kb.tim_video_thang(goc, "K4")
    assert thang["video_id"] == "vidNOI00001" and thang["luat"] == "noi"
    dat, luat = kb.dat_bang_chung(goc, "K4", kb._ung_vien_cua_kenh(goc, "K4"))  # noqa: SLF001
    assert luat == "noi" and [u.video_id for u in dat] == ["vidNOI00001", "vidNOI00002"]
    # có video đạt luật CHẶT → luật chặt thắng như cũ, vế nới không xét
    _ghi_chi_so(goc, "K4", "vidCAO00001", ngay="2026-09-13", moc=[(300, 31666, 7.71)])
    t2 = kb.tim_video_thang(goc, "K4")
    assert t2["video_id"] == "vidCAO00001" and t2["luat"] == "chat"


def test_luat_noi_khuon_duoc_khai_thac_cung_luat(tmp_path):
    from core import bia_theo_khuon as btk
    goc = str(tmp_path)
    _kenh_that(goc)
    _ghi_chi_so(goc, "K4", "vidNOI00001", ngay="2026-09-10", moc=[(300, 25000, 6.0)])
    ket = kb.cap_nhat(goc, "K4", _goi_chat_gia({}), tai_anh=_tai_anh_gia)
    assert ket["video_id"] == "vidNOI00001" and ket["luat_bang_chung"] == "noi"
    tt = btk.trang_thai_khai_thac(goc, "K4")
    assert tt["che_do"] == "khai_thac", tt["ly_do"]
    kh = kb.doc_khuon(goc, "K4")
    kh["luat_bang_chung"] = ""                     # khuôn không chọn bằng vế nới → luật chặt như cũ: thăm dò
    assert btk.trang_thai_khai_thac(goc, "K4", kh)["che_do"] == "tham_do"
    assert btk.du_bang_chung(6.0, 25000, ctr_min=7, imp_min=10000, imp_lon=50000, trung_vi=4.5, noi=True)
    assert not btk.du_bang_chung(6.0, 9000, ctr_min=7, imp_min=10000, imp_lon=50000, trung_vi=4.5, noi=True)
