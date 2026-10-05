"""Bài học sản xuất (`core/bai_hoc_san_xuat.py`) — Bước 1+2+3 của bản thiết kế đã duyệt
`workspace/THIET-KE-BAI-HOC-SAN-XUAT.md`.

Bước 1+2 (đã có từ trước): KHÔNG ai gọi module — bài kiểm chỉ chốt: rút số đúng, ngưỡng độ
tin cậy đúng mốc n, và tệp `bai-hoc-san-xuat.json` không bao giờ mất một bài học `cao` cũ
khi số liệu mới mâu thuẫn với nó. Ba nhóm bài:

1. Ngưỡng `thap`/`vua`/`cao` đúng mốc n (<3, 3-5, ≥6) — cả bằng hàm thuần lẫn trên dữ
   liệu giả dựng disk đầy đủ (CTR×cụm, AVD×độ dài, CTR×concept ảnh bìa).
2. Lưu/đọc giữ lịch sử: mâu thuẫn với một bài `cao` đã lưu thì KHÔNG xoá, chỉ hạ tin cậy.
3. Chạy trên số liệu THẬT của TL4-T7 (`CHANNEL/TL4-T7/chi-so/`) và cả 4 kênh không crash —
   kênh mới (TL1/TL2/TL3-T7) chưa đủ video đủ tuổi phải trả rỗng, không ném lỗi.

Bước 3 (mới, cuối tệp): `xuat_markdown()` — bản người đọc. Test CHỈ dùng `tmp_path`/dữ liệu
giả (không ghi vào `CHANNEL/` thật của kho từ bài kiểm tự động); chạy trên số liệu THẬT của
4 kênh để lấy vài dòng cho báo cáo được làm THỦ CÔNG một lần, ngoài `pytest` (xem GHI-CHU.md
của bản vá `2026-09-26-bai-hoc-san-xuat-b3`).

Không gọi mạng, không cần Qt.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bai_hoc_san_xuat as bh  # noqa: E402
from core.auto import duong_luot  # noqa: E402
from core.kenh import duong_kenh  # noqa: E402

GOC_THAT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAY_GIO = dt.datetime(2026, 9, 26, 12, 0, 0)

# Ba câu tiêu đề tiếng Nhật PROVEN khớp đúng một cụm duy nhất trong cấu hình mặc định của
# `cong_thuc_v7` (chốt bằng cách gọi thật `cum_cua_tieu_de` trước khi đưa vào bài kiểm —
# xem NHAT-KY-PHAT-TRIEN.md của bản vá này). Không suy đoán từ khoá, không chép nguyên văn
# tiêu đề thật của kênh nào để khỏi lẫn với dữ liệu thật khi đọc log.
_TIEU_DE_MOT_MINH = [
    "ずっと一人でいる人にしかわからないこと",
    "一人が好きな人の脳が実は特別な理由その1",
    "一人が好きな人の脳が実は特別な理由その2",
    "一人が好きな人の脳が実は特別な理由その3",
    "一人が好きな人の脳が実は特別な理由その4",
    "一人が好きな人の脳が実は特別な理由その5",
]
_TIEU_DE_VAT_CHAT = [
    "お金持ちが絶対にしない5つの習慣その1",
    "お金持ちが絶対にしない5つの習慣その2",
    "お金持ちが絶対にしない5つの習慣その3",
    "お金持ちが絶対にしない5つの習慣その4",
]
_TIEU_DE_TRI_TUE = [
    "知能が高い人だけが気づいている真実その1",
    "知能が高い人だけが気づいている真実その2",
]
_TIEU_DE_DON_DEP = ["掃除が好きな人の心理学的特徴"]


def test_cum_du_dung_truoc_khi_dung_lam_du_lieu_gia():
    """Chốt trước: bốn nhóm tiêu đề giả THẬT SỰ rơi đúng một cụm, không lẫn cụm khác —
    nếu bài này đỏ thì mọi bài dưới đây đang kiểm nhầm cụm, không phải kiểm module."""
    from core import cong_thuc_v7 as v7
    for t in _TIEU_DE_MOT_MINH:
        assert v7.cum_cua_tieu_de(t) == ["mot-minh"], t
    for t in _TIEU_DE_VAT_CHAT:
        assert v7.cum_cua_tieu_de(t) == ["vat-chat"], t
    for t in _TIEU_DE_TRI_TUE:
        assert v7.cum_cua_tieu_de(t) == ["tri-tue"], t
    for t in _TIEU_DE_DON_DEP:
        assert v7.cum_cua_tieu_de(t) == ["don-dep"], t


# ── 1. Ngưỡng độ tin cậy — hàm thuần, không đụng đĩa ──────────────────────────


def test_muc_tin_cay_dung_moc_n():
    for n in (0, 1, 2):
        assert bh._muc_tin_cay(n) == "thap", n
    for n in (3, 4, 5):
        assert bh._muc_tin_cay(n) == "vua", n
    for n in (6, 7, 50):
        assert bh._muc_tin_cay(n) == "cao", n


def _vh(ma, ctr=None, avd_pct=None, avd_giay=None, thoi_luong_giay=None, cum=None, thumb=""):
    return bh.VideoHoc(ma=ma, tieu_de=ma, ngay_dang="2026-01-01", tuoi_gio=999,
                       thoi_luong_giay=thoi_luong_giay, impressions=1000, ctr=ctr,
                       avd_giay=avd_giay, avd_pct=avd_pct, cum=cum or [], thumb_version_desc=thumb)


def test_bai_hoc_tieu_de_cum_ba_muc_tin_cay_tu_video_hoc():
    """Không qua đĩa: dựng thẳng `VideoHoc` để chốt đúng số n → đúng độ tin cậy,
    không phụ thuộc bộ từ khoá cụm có đổi hay không."""
    videos = (
        [_vh("cao{0}".format(i), ctr=5.0 + i, cum=["cao-cum"]) for i in range(6)]
        + [_vh("vua{0}".format(i), ctr=3.0 + i, cum=["vua-cum"]) for i in range(4)]
        + [_vh("thap{0}".format(i), ctr=7.0 + i, cum=["thap-cum"]) for i in range(2)]
    )
    ra = {b.cum: b for b in bh._bai_hoc_tieu_de_cum(videos, "2026-09-26")}
    assert ra["cao-cum"].do_tin_cay == "cao" and ra["cao-cum"].so_mau == 6
    assert ra["vua-cum"].do_tin_cay == "vua" and ra["vua-cum"].so_mau == 4
    assert ra["thap-cum"].do_tin_cay == "thap" and ra["thap-cum"].so_mau == 2
    # Câu quan sát phải có SỐ — không phải một luật trống
    assert "%" in ra["cao-cum"].quan_sat and "n=6" in ra["cao-cum"].quan_sat


def test_bai_hoc_do_dai_avd_chia_ngan_dai_theo_trung_vi():
    """Trục `do_dai_avd` dùng AVD tính bằng GIÂY (không phải %, đổi 29/09/2026 — AVD% thiên vị
    video ngắn một cách ảo, xem docstring `bh._bai_hoc_do_dai_avd`)."""
    ngan = [_vh("n{0}".format(i), avd_giay=240.0, thoi_luong_giay=600) for i in range(4)]
    dai = [_vh("d{0}".format(i), avd_giay=300.0, thoi_luong_giay=1200) for i in range(4)]
    ra = bh._bai_hoc_do_dai_avd(ngan + dai, "2026-09-26")
    assert len(ra) == 1
    b = ra[0]
    assert b.truc == "do_dai_avd" and b.cum == ""
    assert b.so_mau == 4 and b.do_tin_cay == "vua"
    assert "ngắn" in b.quan_sat and "dài" in b.quan_sat
    assert b.quan_sat.startswith("dài"), "nhóm AVD giây cao hơn (dài) phải đứng đầu câu"
    assert "4:00" in b.quan_sat and "5:00" in b.quan_sat, "AVD phải in dạng mm:ss, không phải %"


def test_bai_hoc_do_dai_avd_rong_khi_thieu_mot_nhom():
    """Toàn bộ video cùng phía trung vị (không tách được ngắn/dài) → không bịa ra so sánh."""
    ds = [_vh("v{0}".format(i), avd_giay=270.0, thoi_luong_giay=900) for i in range(5)]
    assert bh._bai_hoc_do_dai_avd(ds, "2026-09-26") == []


# ── Ảnh bìa: tên tệp → version_desc ────────────────────────────────────────────


def test_version_desc_tu_ten_anh():
    assert bh._version_desc_tu_ten_anh("CHON-thumb_001.png") == "portrait_main"
    assert bh._version_desc_tu_ten_anh("CHON-thumb_002.jpg") == "dramatic_scene"
    assert bh._version_desc_tu_ten_anh("thumb_003.png") == "youtube_ctr"
    assert bh._version_desc_tu_ten_anh("CHON-anh-la.jpg") == ""
    assert bh._version_desc_tu_ten_anh("CHON-thumb_999.png") == ""


def test_bai_hoc_thumbnail_ctr_uu_tien_trong_cum_va_co_dong_gop_chung():
    videos = (
        [_vh("a{0}".format(i), ctr=6.0 + i, cum=["mot-minh"], thumb="dramatic_scene")
         for i in range(3)]
        + [_vh("b{0}".format(i), ctr=3.0 + i, cum=["mot-minh"], thumb="portrait_main")
           for i in range(3)]
    )
    ra = bh._bai_hoc_thumbnail_ctr(videos, "2026-09-26")
    truc_cum = {(b.truc, b.cum) for b in ra}
    assert ("thumbnail_ctr", "mot-minh") in truc_cum, "phải có dòng so trong cùng cụm"
    assert ("thumbnail_ctr", "") in truc_cum, "phải có dòng gộp cả kênh làm phao"
    dong_cum = next(b for b in ra if b.cum == "mot-minh")
    assert dong_cum.quan_sat.startswith("dramatic_scene"), "concept CTR cao hơn phải dẫn đầu"


def test_bai_hoc_thumbnail_ctr_rong_khi_chi_mot_concept():
    videos = [_vh("a{0}".format(i), ctr=5.0, cum=["x"], thumb="portrait_main") for i in range(5)]
    assert bh._bai_hoc_thumbnail_ctr(videos, "2026-09-26") == []


# ── 2. Lưu/đọc — giữ lịch sử khi mâu thuẫn ─────────────────────────────────────


def test_luu_doc_bai_hoc_roundtrip(tmp_path):
    goc = str(tmp_path)
    b1 = bh.BaiHoc(truc="tieu_de_cum", cum="vat-chat", quan_sat="vat-chat: CTR trung vị 6,0% (n=6)",
                   so_mau=6, do_tin_cay="cao", video_dan_chung=["a", "b"], ngay_cap_nhat="2026-09-01")
    duong = bh.luu_bai_hoc(goc, "K1", [b1])
    assert os.path.isfile(duong)
    assert not os.path.isfile(duong + ".tmp"), "không được để sót tệp .tmp sau khi ghi"
    lai = bh.doc_bai_hoc(goc, "K1")
    assert lai == [b1]


def test_doc_bai_hoc_chua_co_tep_tra_rong(tmp_path):
    assert bh.doc_bai_hoc(str(tmp_path), "KHONG-TON-TAI") == []


def test_doc_bai_hoc_tep_hong_tra_rong_khong_nem_loi(tmp_path):
    goc = str(tmp_path)
    duong = bh.duong_tep_bai_hoc(goc, "K1")
    os.makedirs(os.path.dirname(duong))
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write("{ dữ liệu hỏng không phải json")
    assert bh.doc_bai_hoc(goc, "K1") == []


def test_mau_thuan_ha_tin_cay_khong_xoa_bai_cao(tmp_path):
    goc = str(tmp_path)
    cu = bh.BaiHoc(truc="tieu_de_cum", cum="vat-chat",
                   quan_sat="vat-chat: CTR trung vị 6,0% (n=6) — kênh 4,0% (n=10)",
                   so_mau=6, do_tin_cay="cao", video_dan_chung=["a"], ngay_cap_nhat="2026-09-01")
    bh.luu_bai_hoc(goc, "K1", [cu])

    moi = bh.BaiHoc(truc="tieu_de_cum", cum="vat-chat",
                    quan_sat="mot-minh: CTR trung vị 7,0% (n=8) — kênh 4,0% (n=14)",
                    so_mau=8, do_tin_cay="cao", video_dan_chung=["c"], ngay_cap_nhat="2026-09-20")
    bh.luu_bai_hoc(goc, "K1", [moi])

    ds = bh.doc_bai_hoc(goc, "K1")
    assert len(ds) == 2, "phải giữ CẢ HAI dòng, không ghi đè"
    cao_cu = [b for b in ds if b.do_tin_cay == "cao"]
    assert len(cao_cu) == 1 and cao_cu[0].quan_sat == cu.quan_sat, "bài `cao` cũ không được sửa"
    ha = [b for b in ds if b is not cao_cu[0]][0]
    assert ha.do_tin_cay == "vua", "bài mới mâu thuẫn phải bị hạ tin cậy, không phải xoá bài cũ"
    assert "mâu thuẫn" in ha.quan_sat


def test_khong_mau_thuan_thi_thay_the_khong_phinh_file(tmp_path):
    """Bài mới CÙNG hướng kết luận (chỉ thêm mẫu) → thay thế, không giữ cả hai dòng trùng ý."""
    goc = str(tmp_path)
    v1 = bh.BaiHoc(truc="do_dai_avd", cum="", quan_sat="ngắn: AVD trung vị 38,0% (n=6) — dài: 29,0% (n=6)",
                   so_mau=6, do_tin_cay="cao", ngay_cap_nhat="2026-09-01")
    bh.luu_bai_hoc(goc, "K1", [v1])
    v2 = bh.BaiHoc(truc="do_dai_avd", cum="", quan_sat="ngắn: AVD trung vị 39,0% (n=8) — dài: 28,0% (n=8)",
                   so_mau=8, do_tin_cay="cao", ngay_cap_nhat="2026-09-15")
    bh.luu_bai_hoc(goc, "K1", [v2])
    ds = bh.doc_bai_hoc(goc, "K1")
    assert len(ds) == 1
    assert ds[0].quan_sat == v2.quan_sat


def test_luu_bai_hoc_ghi_nguyen_tu_dung_dinh_dang(tmp_path):
    goc = str(tmp_path)
    duong = bh.luu_bai_hoc(goc, "K1", [])
    goi = json.load(io.open(duong, encoding="utf-8"))
    assert goi["kenh"] == "K1"
    assert "cap_nhat_luc" in goi and goi["bai_hoc"] == []


# ── 3. Trên đĩa: dựng số liệu Studio giả cho 4 kênh khác biệt độ tin cậy ───────


def _ghi_video(goc, kenh, ma, moc_gio, *, tieu_de, ngay_dang, ctr, avd_pct,
               thoi_luong_giay, impressions=5000):
    """Một bản chụp Studio giả: `_thong-tin.json` (tiêu đề/ngày/độ dài, do extension ghi)
    + `tong-quan.json` (số đã giải mã) — đúng hình dạng thật, không có `raw/` (không cần,
    xem `chi_so_ytb.gom.gom` chỉ glob `tong-quan.json`)."""
    thu_muc = os.path.join(duong_kenh(goc, kenh), "chi-so", ma, "{0}h".format(moc_gio))
    os.makedirs(thu_muc, exist_ok=True)
    with io.open(os.path.join(thu_muc, "_thong-tin.json"), "w", encoding="utf-8") as tep:
        json.dump({"kenh": kenh, "id": ma, "label": "{0}h".format(moc_gio),
                   "tieu_de": tieu_de, "thoi_luong": thoi_luong_giay, "gio": moc_gio,
                   "ngay_dang": ngay_dang}, tep, ensure_ascii=False)
    with io.open(os.path.join(thu_muc, "tong-quan.json"), "w", encoding="utf-8") as tep:
        json.dump({"video_id": ma, "gio_sau_dang": moc_gio, "thoi_luong_giay": thoi_luong_giay,
                   "impressions": impressions, "ctr": ctr, "avd_pct": avd_pct,
                   "avd_giay": (int(thoi_luong_giay * avd_pct / 100)
                                if thoi_luong_giay and avd_pct is not None else None)},
                  tep, ensure_ascii=False)


def _ma_video(so: int) -> str:
    """11 ký tự — `video_cua_kenh`/`doc_kenh` chỉ nhận thư mục mã đúng độ dài của YouTube."""
    return "SYN{0:08d}".format(so)


def _dung_kenh_gia(goc: str, kenh: str) -> None:
    """12 video: 6 `mot-minh` (→ cao), 4 `vat-chat` (→ vua), 2 `tri-tue` (→ thap) — cộng một
    video quá trẻ (phải bị loại) và một video thiếu AVD (phải bị loại). Độ dài chia đúng nửa
    ngắn/dài để trục `do_dai_avd` cũng chốt `cao` (n=6/6) trong cùng một lần dựng.
    """
    ngay_moc = dt.datetime(2026, 9, 1, 12, 0, 0)  # 25 ngày trước BAY_GIO — dư sức ≥168h
    so = 0
    nhom = ([(t, "mot-minh") for t in _TIEU_DE_MOT_MINH]
           + [(t, "vat-chat") for t in _TIEU_DE_VAT_CHAT]
           + [(t, "tri-tue") for t in _TIEU_DE_TRI_TUE])
    for i, (tieu_de, _cum) in enumerate(nhom):
        so += 1
        ngan_hay_dai = 600 if i % 2 == 0 else 1200
        avd = 40.0 - i if ngan_hay_dai == 600 else 25.0 - i * 0.3
        _ghi_video(goc, kenh, _ma_video(so), 336,
                  tieu_de=tieu_de, ngay_dang=ngay_moc.isoformat(),
                  ctr=4.0 + (i % 5) * 0.5, avd_pct=round(avd, 1), thoi_luong_giay=ngan_hay_dai)
    # Quá trẻ (24 giờ tuổi) — phải bị `video_du_tuoi_de_hoc` loại vì chưa đủ 168h.
    so += 1
    _ghi_video(goc, kenh, _ma_video(so), 24,
              tieu_de=_TIEU_DE_DON_DEP[0], ngay_dang=(BAY_GIO - dt.timedelta(hours=24)).isoformat(),
              ctr=9.9, avd_pct=50.0, thoi_luong_giay=800)
    # Đủ tuổi nhưng THIẾU avd_pct — phải bị loại vì không đủ ctr/avd/impressions.
    so += 1
    _ghi_video(goc, kenh, _ma_video(so), 336,
              tieu_de="値段が高くても買う人の共通点その1", ngay_dang=ngay_moc.isoformat(),
              ctr=9.9, avd_pct=None, thoi_luong_giay=800)


def test_video_du_tuoi_de_hoc_loc_dung_tuoi_va_du_so(tmp_path):
    goc = str(tmp_path)
    _dung_kenh_gia(goc, "GIA-K1")
    videos = bh.video_du_tuoi_de_hoc(goc, "GIA-K1", bay_gio=BAY_GIO)
    # 12 video đủ tuổi + đủ số — video quá trẻ và video thiếu AVD phải KHÔNG có mặt.
    assert len(videos) == 12
    mot_minh = [v for v in videos if "mot-minh" in v.cum]
    assert len(mot_minh) == 6


def test_rut_bai_hoc_tren_du_lieu_gia_du_ca_ba_muc_tin_cay(tmp_path):
    goc = str(tmp_path)
    _dung_kenh_gia(goc, "GIA-K1")
    bai_hoc = bh.rut_bai_hoc(goc, "GIA-K1", bay_gio=BAY_GIO)
    theo_cum = {(b.truc, b.cum): b for b in bai_hoc}
    assert theo_cum[("tieu_de_cum", "mot-minh")].do_tin_cay == "cao"
    assert theo_cum[("tieu_de_cum", "vat-chat")].do_tin_cay == "vua"
    assert theo_cum[("tieu_de_cum", "tri-tue")].do_tin_cay == "thap"
    do_dai = theo_cum[("do_dai_avd", "")]
    assert do_dai.do_tin_cay == "cao" and do_dai.so_mau == 6
    # Đây CHÍNH LÀ hiện tượng "ảo số học" insight 29/09/2026 mô tả: dữ liệu giả dựng ở
    # `_dung_kenh_gia` cho AVD% cao hơn ở nhóm NGẮN (thiên lệch cơ học của AVD%), nhưng AVD
    # GIÂY (đúng cách đo giữ chân thật) lại cho nhóm DÀI cao hơn — đổi trục sang giây phải lật
    # đúng kết luận này, không phải giữ nguyên "ngắn thắng" từ công thức cũ.
    assert do_dai.quan_sat.startswith("dài"), "AVD GIÂY của nhóm dài cao hơn phải dẫn đầu"
    # Chưa dựng PROJECTS/AUTO trong bài này → không có ảnh bìa nối được, trục thumbnail_ctr
    # phải vắng mặt một cách đàng hoàng, không phải một dòng rỗng/giả.
    assert not any(b.truc == "thumbnail_ctr" for b in bai_hoc)


def test_video_qua_tre_va_thieu_avd_khong_lot_duoc(tmp_path):
    goc = str(tmp_path)
    _dung_kenh_gia(goc, "GIA-K1")
    videos = bh.video_du_tuoi_de_hoc(goc, "GIA-K1", bay_gio=BAY_GIO)
    ma_co = {v.ma for v in videos}
    assert _ma_video(13) not in ma_co, "video 24h tuổi phải bị loại (chưa đủ 168h)"
    assert _ma_video(14) not in ma_co, "video thiếu avd_pct phải bị loại"


# ── Bước 2: nối CHON-*.jpg → version_desc → CTR qua lượt AUTO đã đăng ─────────


def test_video_du_tuoi_de_hoc_noi_duoc_thumbnail_da_chon(tmp_path):
    goc = str(tmp_path)
    kenh = "GIA-THUMB"
    ngay_moc = dt.datetime(2026, 9, 1, 12, 0, 0)
    du_lieu = [
        (1, "dramatic_scene", "thumb_002", "一人が好きな人の脳が実は特別な理由その1", 7.0),
        (2, "portrait_main", "thumb_001", "一人が好きな人の脳が実は特別な理由その2", 3.0),
        (3, "youtube_ctr", "thumb_003", "一人が好きな人の脳が実は特別な理由その3", 5.0),
    ]
    for so, _concept, ten_thumb, tieu_de, ctr in du_lieu:
        _ghi_video(goc, kenh, _ma_video(so), 336, tieu_de=tieu_de,
                  ngay_dang=ngay_moc.isoformat(), ctr=ctr, avd_pct=30.0, thoi_luong_giay=800)
        luot = duong_luot(goc, kenh, "{0:04d}".format(so))
        os.makedirs(os.path.join(luot, "7-thumbnail"), exist_ok=True)
        with io.open(os.path.join(luot, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
            tep.write("TITLE: {0}\n".format(tieu_de))
        with io.open(os.path.join(luot, "7-thumbnail", "CHON-{0}.png".format(ten_thumb)),
                    "wb") as tep:
            tep.write(b"\x89PNG")

    videos = bh.video_du_tuoi_de_hoc(goc, kenh, bay_gio=BAY_GIO)
    theo_ma = {v.ma: v for v in videos}
    assert theo_ma[_ma_video(1)].thumb_version_desc == "dramatic_scene"
    assert theo_ma[_ma_video(2)].thumb_version_desc == "portrait_main"
    assert theo_ma[_ma_video(3)].thumb_version_desc == "youtube_ctr"

    bai_hoc = bh.rut_bai_hoc(goc, kenh, bay_gio=BAY_GIO)
    dong_chung = next(b for b in bai_hoc if b.truc == "thumbnail_ctr" and b.cum == "")
    assert dong_chung.quan_sat.startswith("dramatic_scene"), "concept CTR cao nhất phải dẫn đầu"


# ── 4. Trên số liệu THẬT (TL4-T7) và cả 4 kênh — không crash, không tốn tiền ──


def test_tren_du_lieu_that_tl4_t7_co_ca_ba_muc_tin_cay():
    """`CHANNEL/TL4-T7/chi-so/` là số liệu Studio THẬT đã có sẵn trong kho — không dựng giả,
    không gọi mạng. `bay_gio` cố định để bài kiểm không tự đổi kết quả theo ngày chạy (một
    video (`v18718ee920`) sẽ vượt mốc 168h trong vài ngày tới nếu dùng "bây giờ" thật)."""
    if not os.path.isdir(os.path.join(GOC_THAT, "CHANNEL", "TL4-T7", "chi-so")):
        import pytest
        pytest.skip("không có số liệu kênh thật (bản clone sạch / máy khác)")
    videos = bh.video_du_tuoi_de_hoc(GOC_THAT, "TL4-T7", bay_gio=BAY_GIO)
    assert len(videos) >= 10, "kênh có số liệu thật, phải rút được một lượng video hợp lý"
    bai_hoc = bh.rut_bai_hoc(GOC_THAT, "TL4-T7", bay_gio=BAY_GIO)
    assert bai_hoc, "kênh có lịch sử dài phải rút được ít nhất một bài học"
    for b in bai_hoc:
        assert b.truc in ("tieu_de_cum", "do_dai_avd", "thumbnail_ctr",
                          "ctr_browse_48h", "sub_1k_view")
        assert b.do_tin_cay in ("thap", "vua", "cao")
        # Bất biến của module: độ tin cậy phải luôn KHỚP đúng mốc n, dù trục nào đi nữa.
        assert b.do_tin_cay == bh._muc_tin_cay(b.so_mau)
    muc = {(b.truc, b.cum): b.do_tin_cay for b in bai_hoc}
    assert muc.get(("tieu_de_cum", "mot-minh")) == "cao", "cụm lớn nhất của TL4-T7 phải đạt cao"


def test_ca_bon_kenh_khong_crash_kenh_moi_tra_rong_dang_hoang():
    """TL1/TL2/TL3-T7 là kênh MỚI, gần như chắc chắn chưa có video nào ≥7 ngày tuổi — phải trả
    danh sách rỗng một cách đàng hoàng, không phải ném lỗi vì thiếu `kenh.yaml`/thư mục con."""
    for kenh in ("TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7"):
        bai_hoc = bh.rut_bai_hoc(GOC_THAT, kenh, bay_gio=BAY_GIO)
        assert isinstance(bai_hoc, list)


def test_kenh_khong_ton_tai_tra_rong():
    assert bh.video_du_tuoi_de_hoc(GOC_THAT, "KHONG-TON-TAI-XYZ", bay_gio=BAY_GIO) == []
    assert bh.rut_bai_hoc(GOC_THAT, "KHONG-TON-TAI-XYZ", bay_gio=BAY_GIO) == []


# ── 5. Bước 3: `xuat_markdown()` — bản người đọc, khuôn CONG-THUC-V7.md ───────


def test_xuat_markdown_chua_du_du_lieu_noi_ro_thay_vi_de_trong(tmp_path):
    goc = str(tmp_path)
    duong = bh.xuat_markdown(goc, "KENH-MOI-TINH", bay_gio=BAY_GIO)
    assert os.path.basename(duong) == "BAI-HOC-SAN-XUAT.md"
    noi_dung = io.open(duong, encoding="utf-8").read()
    assert "chưa đủ dữ liệu (cần video ≥7 ngày tuổi)" in noi_dung.lower()
    # Kênh trống thì KHÔNG được vẽ ra ba mục — đó là bịa bằng chứng cho thứ chưa có.
    assert "## 1." not in noi_dung and "## 2." not in noi_dung


def test_xuat_markdown_theo_dung_khuon_ba_muc(tmp_path):
    goc = str(tmp_path)
    _dung_kenh_gia(goc, "GIA-MD1")
    duong = bh.xuat_markdown(goc, "GIA-MD1", bay_gio=BAY_GIO)
    noi_dung = io.open(duong, encoding="utf-8").read()

    for de_muc in ("## 1. LUẬT ĐANG DÙNG", "## 2. BẰNG CHỨNG", "## 3. VIỆC CÒN TREO"):
        assert de_muc in noi_dung, de_muc

    # Trục có bài học thật thì phải thấy đúng con số đã tính, không phải chữ trơn.
    assert "CAO" in noi_dung and "mot-minh" in noi_dung
    assert "VUA" in noi_dung and "vat-chat" in noi_dung
    assert "THAP" in noi_dung and "tri-tue" in noi_dung
    # Trục rỗng (chưa dựng PROJECTS/AUTO trong bài này) phải nói rõ lý do, không im lặng.
    assert "chưa nối được ảnh bìa" in noi_dung
    # Bảng bằng chứng phải có dẫn chứng bằng TIÊU ĐỀ (dễ đọc), không phải trơ mã video 11 ký tự.
    co_tieu_de = any(t[:8] in noi_dung for t in _TIEU_DE_MOT_MINH)
    assert co_tieu_de, "bảng bằng chứng phải in tiêu đề video, không chỉ mã"
    # Ghi ra tệp JSON đồng thời (đi qua rut_bai_hoc + luu_bai_hoc) — không chỉ có bản .md.
    assert os.path.isfile(bh.duong_tep_bai_hoc(goc, "GIA-MD1"))


def test_xuat_markdown_giu_lich_su_khi_mau_thuan(tmp_path):
    """Đã có một bài `cao` kết luận NGƯỢC với số liệu thật — `xuat_markdown` phải nói cho
    người đọc biết đang có mâu thuẫn, không âm thầm ghi đè bằng số mới."""
    goc = str(tmp_path)
    kenh = "GIA-MD2"
    _dung_kenh_gia(goc, kenh)
    # Bài cũ mô phỏng kết luận theo AVD% (nhóm NGẮN dẫn đầu) — số liệu thật của `_dung_kenh_gia`
    # tính bằng AVD GIÂY lại cho nhóm DÀI dẫn đầu (xem
    # `test_rut_bai_hoc_tren_du_lieu_gia_du_ca_ba_muc_tin_cay`), nên hai bên NGƯỢC nhãn dẫn đầu
    # — đúng kịch bản mâu thuẫn mà `_hop_nhat` phải phát hiện.
    cu = bh.BaiHoc(
        truc="do_dai_avd", cum="",
        quan_sat="ngắn (≤15,0 phút): AVD trung vị 5:00 (n=6) — dài (>15,0 phút): 3:00 (n=6)",
        so_mau=6, do_tin_cay="cao", video_dan_chung=["x"], ngay_cap_nhat="2026-01-01")
    bh.luu_bai_hoc(goc, kenh, [cu])

    duong = bh.xuat_markdown(goc, kenh, bay_gio=BAY_GIO)
    noi_dung = io.open(duong, encoding="utf-8").read()
    assert "mâu thuẫn" in noi_dung
    assert "ngắn (≤15,0 phút): AVD trung vị 5:00" in noi_dung, "bài cũ phải còn nguyên trong .md"

    # Và JSON trên đĩa thật sự giữ cả hai — không phải .md nói suông.
    ds = bh.doc_bai_hoc(goc, kenh)
    do_dai = [b for b in ds if b.truc == "do_dai_avd"]
    assert len(do_dai) == 2
    assert any(b.do_tin_cay == "cao" and b.quan_sat == cu.quan_sat for b in do_dai)


def test_xuat_markdown_goi_lai_khong_phinh_file_khi_khong_mau_thuan(tmp_path):
    """Gọi `xuat_markdown` hai lần liên tiếp trên CÙNG số liệu (đúng nếp nút bấm — người
    dùng có thể bấm lại) không được nhân đôi bài học."""
    goc = str(tmp_path)
    kenh = "GIA-MD3"
    _dung_kenh_gia(goc, kenh)
    bh.xuat_markdown(goc, kenh, bay_gio=BAY_GIO)
    so_lan_1 = len(bh.doc_bai_hoc(goc, kenh))
    bh.xuat_markdown(goc, kenh, bay_gio=BAY_GIO)
    so_lan_2 = len(bh.doc_bai_hoc(goc, kenh))
    assert so_lan_1 == so_lan_2 and so_lan_1 > 0
