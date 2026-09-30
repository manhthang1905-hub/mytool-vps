"""Mục lục (目次) trong mô tả video lấy MỐC THẬT từ SRT, không bịa.

Chủ dự án, 03/09/2026: *"fix tool để về sau nó làm đúng loại mô tả có
[timestamps]"*. Khâu SEO chạy từ lúc viết kịch bản — chưa có giọng đọc nên
không thể biết chương nào rơi phút nào; `_chen_muc_luc_seo` chèn 目次 vào
`1-seo.txt` ngay sau khi SRT ra đời, bằng ghép chuỗi thuần.

Bài kiểm chốt:
  1. Rút chương từ dấu `---`: chương đầu 00:00 lấy câu mở màn làm nhãn.
  2. Nhãn cụt ("では、") được ghép thêm câu ngay sau — không có chương 2 chữ.
  3. Dưới 3 chương → trả [], vì YouTube không nhận mục lục ngắn hơn.
  4. Chèn vào 1-seo.txt: khối 目次 nằm TRONG DESCRIPTION, trước dòng hashtag.
  5. Chạy lại không chèn đúp; thiếu 1-seo.txt không nổ lỗi.
"""

from __future__ import annotations

import os

from core.auto_khau import _chen_muc_luc_seo, _muc_luc_tu_srt


def _srt(*cau: "tuple[str, str]") -> str:
    khoi = []
    for i, (moc, chu) in enumerate(cau, 1):
        khoi.append("{0}\n{1} --> {1}\n{2}".format(i, moc, chu))
    return "\n\n".join(khoi) + "\n"


SRT_3_CHUONG = _srt(
    ("00:00:00,180", "夜の部屋に、小さな明かり。"),
    ("00:00:59,030", "--- 一つ目は、予測できない愛情です。"),
    ("00:03:31,960", "--- では、"),
    ("00:03:32,660", "この防衛は日常でどんな姿になるのでしょう。"),
    ("00:13:27,400", "--- あなたは、壊れてなどいません。"),
)


def test_rut_chuong_va_moc():
    muc = _muc_luc_tu_srt(SRT_3_CHUONG)
    assert muc[0] == "00:00 夜の部屋に、小さな明かり"
    assert muc[1] == "00:59 一つ目は、予測できない愛情です"
    assert muc[-1] == "13:27 あなたは、壊れてなどいません"


def test_nhan_cut_ghep_cau_sau():
    muc = _muc_luc_tu_srt(SRT_3_CHUONG)
    assert muc[2] == "03:31 では、この防衛は日常でどんな姿になるのでしょう"


def test_nhan_chuong_la_ca_cau_khong_dung_o_dau_phay_va_khong_trung():
    """TL4-T7-v2/0001 (09/09/2026): phụ đề tách dòng ở dấu phẩy, hai chương cùng
    mở bằng 「一つ目の特徴は、」 ra hai nhãn y hệt nhau trong mục lục."""
    it = _srt(
        ("00:00:00,000", "にぎやかな集まりから帰った夜、"),
        ("00:00:03,000", "一人の部屋でようやく息がつけた。"),
        ("00:00:47,000", "--- 一つ目の特徴は、"),
        ("00:00:49,000", "このすぐ後にお伝えします。"),
        ("00:00:52,000", "その前に、常識を覆す事実を知ってください。"),
        ("00:02:14,000", "--- 一つ目の特徴は、"),
        ("00:02:16,000", "答えを外に求める前に、"),
        ("00:02:18,000", "一人で立ち止まって考える習慣です。"),
        ("00:04:04,000", "--- 二つ目の特徴は、感情を細かく言葉にできることです。"),
    )
    muc = _muc_luc_tu_srt(it)
    assert muc[0] == "00:00 にぎやかな集まりから帰った夜、一人の部屋でようやく息がつけた"
    assert muc[1] == "00:47 一つ目の特徴は、このすぐ後にお伝えします"
    assert muc[2] == "02:14 一つ目の特徴は、答えを外に求める前に、一人で立ち止まって考える習慣です"
    assert muc[3] == "04:04 二つ目の特徴は、感情を細かく言葉にできることです"
    assert len({m.split(" ", 1)[1] for m in muc}) == len(muc), "không có hai nhãn trùng"


def test_duoi_3_chuong_tra_rong():
    it = _srt(("00:00:00,000", "mở màn."), ("00:00:30,000", "--- phần hai."))
    assert _muc_luc_tu_srt(it) == []


class _BC:
    def __init__(self, ngon_ngu="ja"):
        self.kenh = type("K", (), {"ngon_ngu": ngon_ngu})()
        self.dong = []

    def ghi(self, chu):
        self.dong.append(chu)


def test_chen_truoc_hashtag_va_khong_dup(tmp_path):
    d = str(tmp_path)
    srt = os.path.join(d, "3-phu-de.srt")
    with open(srt, "w", encoding="utf-8") as f:
        f.write(SRT_3_CHUONG)
    seo = os.path.join(d, "1-seo.txt")
    with open(seo, "w", encoding="utf-8") as f:
        f.write("DESCRIPTION:\nmô tả.\n\n#tag1 #tag2\n\nHASHTAGS:\n#tag1 #tag2\n")
    bc = _BC()
    _chen_muc_luc_seo(bc, d, srt)
    chu = open(seo, encoding="utf-8").read()
    assert "📌 目次" in chu
    # 目次 nằm trước dòng hashtag chốt DESCRIPTION, tức trước cả nhãn HASHTAGS:.
    assert chu.index("目次") < chu.index("#tag1")
    assert chu.index("00:59") < chu.index("HASHTAGS:")
    # Chạy lại: không chèn đúp.
    _chen_muc_luc_seo(bc, d, srt)
    assert open(seo, encoding="utf-8").read().count("目次") == 1


def test_thieu_seo_khong_no(tmp_path):
    _chen_muc_luc_seo(_BC(), str(tmp_path), os.path.join(str(tmp_path), "x.srt"))

# ── Việc 2 (28/09/2026): mục lục theo PHẦN — mốc giữa khoảng nghỉ, THAY khối cũ ──

SEO_CO_KHOI = ("応援なしで成功できる人が…\n\n#応援なしで成功 #脳科学\n\n"
               "━━━━━━━━━━━━━━\n📌 目次\n00:00 cũ\n01:33 cũ hai\n03:20 cũ ba\n"
               "━━━━━━━━━━━━━━")


def test_dat_muc_luc_thay_khoi_cu_va_idempotent(tmp_path):
    from core.phan_video import dat_muc_luc_seo

    seo = tmp_path / "1-seo.txt"
    seo.write_text(SEO_CO_KHOI, encoding="utf-8")
    dong = ["00:00 mở", "01:35 hai", "03:23 ba"]
    assert dat_muc_luc_seo(str(seo), dong, "ja") == "thay"
    chu = seo.read_text(encoding="utf-8")
    assert chu.count("目次") == 1 and "cũ" not in chu
    assert "01:35 hai" in chu and chu.index("#応援") < chu.index("目次")
    assert dat_muc_luc_seo(str(seo), dong, "ja") == "giu"
    assert seo.read_text(encoding="utf-8") == chu, "chạy lại không đổi một byte"


def test_dat_muc_luc_chen_khi_chua_co_va_go_khi_duoi_3_chuong(tmp_path):
    from core.phan_video import dat_muc_luc_seo

    seo = tmp_path / "1-seo.txt"
    seo.write_text("DESCRIPTION:\nmô tả.\n\n#a #b\n\nHASHTAGS:\n#a #b\n", encoding="utf-8")
    assert dat_muc_luc_seo(str(seo), ["00:00 a", "00:30 b", "01:00 c"], "vi") == "chen"
    chu = seo.read_text(encoding="utf-8")
    assert "📌 Chapters" in chu and chu.index("Chapters") < chu.index("HASHTAGS:")
    assert dat_muc_luc_seo(str(seo), [], "vi") == "go"
    assert "Chapters" not in seo.read_text(encoding="utf-8")


def test_muc_luc_theo_phan_moc_giua_nghi_va_nhan_khong_dau_ngat(tmp_path):
    from core.phan_video import KeHoach, RanhGioi, bang_bu, muc_luc, sach_srt
    from core.phu_de import doc_srt, viet_srt

    # Câu mở phần nằm TRONG khoảng lặng (bộ ép đặt sớm) — phải được dời ra.
    ranh = [RanhGioi(57.5, 58.9), RanhGioi(210.5, 211.8), RanhGioi(805.4, 806.6)]
    kh = KeHoach(tong_giong=900.0, ranh=ranh, bu=bang_bu(ranh, 3.0), giay_nghi=3.0)
    srt = _srt(
        ("00:00:00,180", "夜の部屋に、小さな明かり。"),
        ("00:00:58,000", "--- 一つ目は、予測できない愛情です。"),
        ("00:03:31,000", "--- では、"),
        ("00:03:32,660", "この防衛は日常でどんな姿になるのでしょう。"),
        ("00:13:26,000", "--- あなたは、壊れてなどいません。"),
    )
    p = str(tmp_path / "8.srt")
    viet_srt(p, sach_srt(doc_srt(srt), kh))
    muc = muc_luc(kh, open(p, encoding="utf-8").read())
    assert muc[0] == "00:00 夜の部屋に、小さな明かり"
    # Chương 2 ở floor(m'_1) = floor((57,5 + 58,9+1,6)/2) = 59.
    assert muc[1] == "00:59 一つ目は、予測できない愛情です"
    assert muc[2].startswith("03:3") and "では、この防衛は" in muc[2]
    assert all("---" not in m for m in muc)
    assert muc[3].startswith("13:")
    # Đưa SRT THÔ + lam_sach=True ra cùng kết quả.
    assert muc_luc(kh, srt, lam_sach=True) == muc


def test_chen_muc_luc_seo_uu_tien_2_phan_json(tmp_path):
    import json

    d = str(tmp_path)
    srt = os.path.join(d, "3-phu-de.srt")
    with open(srt, "w", encoding="utf-8") as f:
        f.write(SRT_3_CHUONG)
    with open(os.path.join(d, "2-phan.json"), "w", encoding="utf-8") as f:
        json.dump({"giay_nghi": 3.0, "tong": 900.0, "phan": [
            {"so": 1, "bat_dau": 0.0, "het_loi": 57.5},
            {"so": 2, "bat_dau": 60.5, "het_loi": 210.0},
            {"so": 3, "bat_dau": 213.0, "het_loi": 806.0},
            {"so": 4, "bat_dau": 809.0, "het_loi": 900.0}]}, f)
    seo = os.path.join(d, "1-seo.txt")
    with open(seo, "w", encoding="utf-8") as f:
        f.write(SEO_CO_KHOI)

    class K:
        ngon_ngu = "ja"
        giay_nghi_chuyen_phan = 3.0

    bc = _BC()
    bc.kenh = K()
    _chen_muc_luc_seo(bc, d, srt)
    chu = open(seo, encoding="utf-8").read()
    assert chu.count("目次") == 1 and "cũ" not in chu, "khối cũ bị THAY, không chèn đúp"
    assert "00:59 " in chu, "mốc = floor(giữa khoảng nghỉ 57,5–60,5)"
    assert "13:27 " in chu
