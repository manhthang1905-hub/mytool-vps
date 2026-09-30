"""Tệp khán giả → tuyến con bằng từ khoá (06/09/2026, theo cách phân của chủ dự án)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import doi_thu_kenh as so  # noqa: E402
from core import tuyen_con as tc  # noqa: E402
from core.phan_tuyen import MA_LECH_NHIP, MA_TRUNG_NIEN  # noqa: E402

KENH = "TL4-T7"


@pytest.mark.parametrize("tieu_de, tep, chu_de", [
    ("SNSをしない人の特徴", MA_LECH_NHIP, "khong-sns"),
    ("スポーツに興味がない人の脳が持っている特殊な報酬回路の正体", MA_LECH_NHIP, "khong-the-thao"),
    ("【60万回再生】家にいたい人の脳が、実は高性能な理由", MA_LECH_NHIP, "o-nha"),
    ("友達が少ない人の、本当の理由", MA_LECH_NHIP, "it-ban"),
    ("【心理学】独り言が多い人の「恐ろしい特徴」", MA_LECH_NHIP, "noi-mot-minh"),
    ("人混みが苦手な人の、本当の理由", MA_LECH_NHIP, "dam-dong-met"),
    ("一人が好きな人の、本当の理由", MA_LECH_NHIP, "mot-minh"),
    ("【心理学】なぜか部屋が汚くなる人の「恐ろしい特徴」｜片付けられない人に隠された4つの才能", MA_TRUNG_NIEN, "don-nha"),
    ("50代から人生が変わる「幸せな環境」の作り方7選", MA_TRUNG_NIEN, "tuoi-tac"),
    ("最近物忘れが増えた人へ｜脳は年齢ではなく「使い方」で若返る", MA_TRUNG_NIEN, "tri-nho"),
    ("性格が悪い人が必ずとる行動", tc.MA_CANH_GIAC, "ke-doc-hai"),
    ("IQ130以上の人が無意識にやっている10の習慣", tc.MA_THAP, "hoc-van-iq"),
    ("猫が一匹いれば幸せな人、その本当の理由", tc.MA_TO_MO, "dong-vat"),
    ("なぜかよく道を聞かれる人の意外すぎる5つの才能", tc.MA_TO_MO, "thoi-quen-vat"),
])
def test_nhan_dien_theo_tu_khoa(tieu_de, tep, chu_de):
    assert tc.nhan_dien(tieu_de) == (tep, chu_de)


@pytest.mark.parametrize("tieu_de", ["【雑学】人生後半で化ける人の特徴", "たった3日で脳の処理速度が40倍になる勉強法", ""])
def test_khong_nhan_ra_thi_none(tieu_de):
    assert tc.nhan_dien(tieu_de) is None


def test_thu_tu_uu_tien_mot_tieu_de_dinh_nhieu_nhom():
    # tuổi thắng lệch nhịp (PHÂN XỬ: tuổi là nhân vật chính → trung niên)
    assert tc.nhan_dien("60代で一人が好きな人の特徴")[0] == MA_TRUNG_NIEN
    # trong tệp lệch nhịp: SNS trước "một mình" (chủ đề cụ thể thắng chủ đề chung)
    assert tc.nhan_dien("一人が好きでSNSをしない人") == (MA_LECH_NHIP, "khong-sns")


def test_dien_chu_de_khong_de_nhan_tep_da_co(tmp_path):
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    cot = so.cot_mac_dinh()
    o = {c: i for i, c in enumerate(cot)}

    def dong(td, link, tep=""):
        d = [""] * len(cot)
        d[o["Tiêu đề video"]], d[o["Link video"]], d[o["Kênh"]], d[o[so.COT_TUYEN]] = td, link, "k", tep
        return d
    hang = [dong("SNSをしない人の特徴", "https://www.youtube.com/watch?v=aaaaaaaaaaa"),
            dong("猫が好きな人の本当の理由", "https://www.youtube.com/watch?v=bbbbbbbbbbb", tep=MA_LECH_NHIP),  # người đã đặt tệp khác
            dong("たった3日で脳が40倍", "https://www.youtube.com/watch?v=ccccccccccc")]
    so.luu_bang(goc, KENH, cot, hang)
    dem = tc.dien_chu_de(goc, KENH)
    assert dem == {"chu_de": 1, "tep_moi": 1, "xem": 3}
    cot, hang = so.doc_bang(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    r = {h[o["Link video"]][-11:]: (h[o[so.COT_TUYEN]], h[o[so.COT_CHU_DE]]) for h in hang}
    assert r["aaaaaaaaaaa"] == (MA_LECH_NHIP, "khong-sns")
    assert r["bbbbbbbbbbb"] == (MA_LECH_NHIP, ""), "nhãn tệp người đặt giữ nguyên; chủ đề của tệp khác thì để trống"
    assert r["ccccccccccc"] == ("", "")
    assert tc.ten_chu_de("khong-sns") == "không dùng mạng xã hội" and tc.ten_chu_de("la") == "la"


def test_so_content_moi_co_cot_chu_de_sau_tuyen():
    cot = so.cot_mac_dinh()
    assert cot.index(so.COT_CHU_DE) == cot.index(so.COT_TUYEN) + 1


# ── 29/09/2026: tệp là việc của AI đọc nghĩa; regex chỉ là đường lùi ─────────────


def _bang_ai(tmp_path, nhan_tuyen):
    import json
    import datetime as dt
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu" / "nhan-tuyen").mkdir(parents=True)
    with open(os.path.join(goc, "CHANNEL", KENH, "nghien-cuu", "nhan-tuyen", KENH + ".json"), "w",
              encoding="utf-8") as t:
        json.dump({l: {"ma": "", "do_tin": 40, "ngay": dt.date.today().isoformat()} for l in nhan_tuyen}, t)
    cot = so.cot_mac_dinh()
    o = {c: i for i, c in enumerate(cot)}

    def dong(td, ma, ngay, dau):
        d = [""] * len(cot)
        d[o["Tiêu đề video"]], d[o["Link video"]], d[o["Kênh"]] = td, "https://www.youtube.com/watch?v=" + ma, "k"
        d[o["Ngày đăng"]], d[o[so.COT_LAN_DAU]] = ngay, dau
        return d
    return goc, cot, dong


def test_dien_chu_de_che_do_ai_de_trong_dong_moi(tmp_path):
    import datetime as dt
    hom_nay = dt.date(2026, 9, 29)
    goc, cot, dong = _bang_ai(tmp_path, ["https://www.youtube.com/watch?v=bbbbbbbbbbb"])
    hang = [dong("SNSをしない人の特徴", "aaaaaaaaaaa", "2026-09-25", "2026-09-28"),        # mới → để AI
            dong("友達が少ない人の、本当の理由", "bbbbbbbbbbb", "2026-09-20", "2026-09-21"),  # AI đã hỏi, chưa chắc
            dong("一人が好きな人の、本当の理由", "ccccccccccc", "2026-06-01", "2026-09-01"),  # cũ → regex
            dong("人混みが苦手な人の、本当の理由", "ddddddddddd", "2026-09-20", "2026-09-20")]  # AI bỏ sót >2 ngày
    so.luu_bang(goc, KENH, cot, hang)
    dem = tc.dien_chu_de(goc, KENH, hom_nay=hom_nay)
    assert dem["de_cho_ai"] == 2 and dem["tep_moi"] == 2, dem
    cot, hang = so.doc_bang(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    r = {h[o["Link video"]][-11:]: h[o[so.COT_TUYEN]] for h in hang}
    assert r["aaaaaaaaaaa"] == "" and r["bbbbbbbbbbb"] == ""
    assert r["ccccccccccc"] == MA_LECH_NHIP and r["ddddddddddd"] == MA_LECH_NHIP
    # ép tắt chế độ AI → y như cũ
    assert tc.dien_chu_de(goc, KENH, de_cho_ai=False, hom_nay=hom_nay)["tep_moi"] == 2


def test_tep_theo_nghia_uu_tien_nhan_trong_so(tmp_path):
    goc = str(tmp_path)
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    cot = so.cot_mac_dinh()
    o = {c: i for i, c in enumerate(cot)}
    d = [""] * len(cot)
    d[o["Tiêu đề video"]], d[o["Link video"]], d[o[so.COT_TUYEN]] = \
        "猫が一匹いれば幸せな人", "https://www.youtube.com/watch?v=eeeeeeeeeee", MA_LECH_NHIP
    so.luu_bang(goc, KENH, cot, [d])
    assert tc.tep_theo_nghia(goc, KENH, "猫が一匹いれば幸せな人", "https://youtu.be/eeeeeeeeeee") == (MA_LECH_NHIP, "so")
    assert tc.tep_theo_nghia(goc, KENH, "SNSをしない人の特徴") == (MA_LECH_NHIP, "regex")
    assert tc.tep_theo_nghia(goc, KENH, "たった3日で脳が40倍") is None
