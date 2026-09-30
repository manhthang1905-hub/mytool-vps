"""Chốt ứng viên đối thủ bằng máy — bốn cửa, quyết định ghi lý do, không đụng trạng thái khách đặt tay.

Số liệu thật 05/09/2026 (72 kênh): 44 bỏ đều vì lý do máy đo được. Mấy bài này dựng đúng các
hình dạng ấy bằng ảnh chụp kênh giả (không mạng, không AI).
"""

import datetime as _dt
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chot_doi_thu as cdt  # noqa: E402
from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import loc_doi_thu as loc  # noqa: E402
from core.youtube import Channel, Video  # noqa: E402

KENH = "TL4-T7"
LECH = ["一人が好きな人の、本当の理由", "友達が少ない人の、本当の理由", "SNSをやらない人だけが、気づいていること",
        "人混みが苦手な人の、本当の理由", "「一人でいても寂しくない人」の脳が、静かに強い理由"]
GIA = ["60代で本当に品がある人の家にないもの", "老後が幸せな人に共通すること", "50代からの生き方",
       "定年後にやるべきこと", "70代でも若い人の習慣"]
CHUNG = ["人生がうまくいく人の7つの習慣", "脳を幸せにする10の方法", "朝のルーティン", "幸せになる3つの習慣",
         "運動を続けると起きること"]


def _ngay(cach: int) -> str:
    """Ngày đăng TƯƠNG ĐỐI hôm nay — cửa "ngừng hoạt động" (30/09/2026) đo theo ngày thật."""
    return (_dt.date.today() - _dt.timedelta(days=cach)).isoformat()


def _kenh(ten, link, subs, tieu_de, view=5000, dai=900, cach_ngay=3):
    vids = [Video(video_id="v%02d" % i, title=t, url="https://www.youtube.com/watch?v=v%02d" % i,
                  views=view, duration_s=dai, upload_date=_ngay(cach_ngay + i))
            for i, t in enumerate(tieu_de)]
    return Channel(input_url=link, name=ten, channel_url=link, subscribers=subs, videos=vids)


def _lay(kho):
    def lay_kenh(link, **kw):
        if link not in kho:
            raise RuntimeError("kênh chết")
        return kho[link]
    return lay_kenh


def _goc(tmp_path):
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    return str(tmp_path)


@pytest.mark.parametrize("ten, link, subs, tieu_de, view, dai, tt, ly_do_co", [
    ("ズレは才能", "https://www.youtube.com/@zure", 7700, LECH * 5, 10000, 570, db.THEO_DOI, "khớp tuyến 100%"),
    ("ちょっと元気になれる心理学", "https://www.youtube.com/@genki", 1950, CHUNG * 5, 1350, 780, db.THEO_DOI, "máy chấm"),
    # KHÔNG PHẢI kênh tâm lý → bỏ (ẩn): thể loại, sai tiếng, không dấu hiệu
    ("大人の心理雑学", "https://www.youtube.com/@zatsu", 5890, LECH * 5, 3800, 960, db.BO, "雑学"),
    ("本要約チャンネル", "https://www.youtube.com/@youyaku", 1_800_000, CHUNG * 5, 58000, 2200, db.BO, "要約"),
    ("Carrom King", "https://www.youtube.com/@carrom", 3_820_000, ["Carrom trick shots"] * 25, 1400, 230, db.BO, "không phải tiếng"),
    ("Barry Nobles", "https://www.youtube.com/@barry", 188000, ["今日の話"] * 25, 13000, 900, db.BO, "không phải kênh tâm lý"),
    # Kênh tâm lý ở góc khác của thị trường → vẫn "theo dõi" (quét), ghi chú nói góc nào
    # (07/09: "tạm ngưng mày cho vào danh sách làm gì" — thị trường thì quét hết)
    ("心のオアシス", "https://www.youtube.com/@oasis", 370, LECH * 5, 626, 900, db.THEO_DOI, "còn nhỏ"),
    ("ココロゴー", "https://www.youtube.com/@gogo", 1980, LECH * 5, 1400, 2700, db.THEO_DOI, "khác khổ"),
    ("Golden Life Handbook", "https://www.youtube.com/@golden", 5660, GIA * 5, 7650, 1200, db.THEO_DOI, "tệp 55+"),
    # 07/09: kênh lớn mà không có dấu hiệu tâm lý → bỏ (PIVOT 4 triệu subs từng lọt vào vì "quá lớn" xét trước)
    ("PIVOT 公式", "https://www.youtube.com/@pivot", 4_060_000, ["最新脳科学 読書"] * 25, 121500, 900, db.BO, "kênh lớn"),
    ("心理カウンセラー・ラッキー", "https://www.youtube.com/@lucky", 652_000, CHUNG * 5, 30000, 900, db.THEO_DOI, "quá lớn"),
    ("pure life diary", "https://www.youtube.com/@pure", 46300, CHUNG * 4 + ["一人時間の使い方"], 4350, 880, None, "gần ngách"),
])
def test_quyet_bon_cua(ten, link, subs, tieu_de, view, dai, tt, ly_do_co):
    uv = cdt.do_ung_vien(link, lang="ja", phut_muc_tieu=15, lay_kenh=_lay({link: _kenh(ten, link, subs, tieu_de, view, dai)}))
    ket, ly_do = cdt.quyet(uv)
    assert ket == tt, (ket, ly_do)
    assert ly_do_co in ly_do, ly_do


def test_kenh_chet_khong_nem_va_khong_vao_danh_ba(tmp_path):
    goc = _goc(tmp_path)
    so.luu_doi_thu(goc, KENH, "https://www.youtube.com/@chet\nhttps://www.youtube.com/@zure\n")
    kho = {"https://www.youtube.com/@zure": _kenh("ズレは才能", "https://www.youtube.com/@zure", 7700, LECH * 5, 10000, 570)}
    hoi, _r = _hoi_gia({"ズレは才能": "doi_thu"})
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho), client=object(), hoi=hoi,
                   mo_ta_kenh="x")
    assert dem["cham"] == 2 and dem["loi"] == 1 and dem["theo_doi"] == 1
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    assert [h[o["Link kênh"]] for h in hang] == ["https://www.youtube.com/@zure"]
    assert hang[0][o["Trạng thái"]] == db.THEO_DOI and "khớp tuyến" in hang[0][o["Ghi chú"]]
    assert hang[0][o["Subs"]] == "7700" and hang[0][o["View TV"]] == "10000"
    # kênh chết còn nằm hộp thư — lượt sau chấm lại
    assert db.hop_thu(goc, KENH) == ["https://www.youtube.com/@chet"]


def test_chot_ghi_bo_va_de_lai_hop_thu_dung_cho(tmp_path):
    goc = _goc(tmp_path)
    links = ["https://www.youtube.com/@zatsu", "https://www.youtube.com/@pure", "https://www.youtube.com/@golden"]
    so.luu_doi_thu(goc, KENH, "\n".join(links) + "\n")
    kho = {links[0]: _kenh("大人の心理雑学", links[0], 5890, LECH * 5, 3800, 960),
           links[1]: _kenh("pure life diary", links[1], 46300, CHUNG * 4 + ["一人時間の使い方"], 4350, 880),
           links[2]: _kenh("Golden Life Handbook", links[2], 5660, GIA * 5, 7650, 1200)}
    nhat_ky = []
    hoi, _r = _hoi_gia({"大人の心理雑学": "khong", "pure life diary": "doi_thu", "Golden Life Handbook": "doi_thu"})
    # 30/09/2026: vào "theo dõi" chỉ khi LLM phán đúng ngách
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho), on_log=nhat_ky.append,
                   client=object(), hoi=hoi, mo_ta_kenh="x")
    # 07/09: thị trường quét hết — 雑学 bỏ (ẩn); 'gần ngách' và 'tệp 55+' vào theo dõi với ghi chú góc thị trường
    assert (dem["theo_doi"], dem["bo"], dem.get("tam_ngung", 0), dem["o_lai"]) == (2, 1, 0, 0)
    assert dem["bo_links"] == [links[0]]
    assert db.hop_thu(goc, KENH) == [], "hộp thư phải tự rỗng — không để kênh 'chờ bạn quyết'"
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    tt = {h[o["Link kênh"]]: (h[o["Trạng thái"]], h[o["Ghi chú"]], h[o["Lần đầu thấy"]]) for h in hang}
    assert tt[links[1]][0] == db.THEO_DOI and "gần ngách" in tt[links[1]][1]
    assert tt[links[2]][0] == db.THEO_DOI and "tệp 55+" in tt[links[2]][1]
    assert len(tt[links[0]][2]) == 10, "kênh mới vào sổ phải có 'Lần đầu thấy'"
    assert set(db.dang_theo_doi(goc, KENH)) == {links[1], links[2]}
    assert any("chốt danh bạ" in m for m in nhat_ky)


def test_kenh_da_chet_thi_bo_luon_loi_tam_thi_thu_lai(tmp_path):
    goc = _goc(tmp_path)
    chet, tam = "https://www.youtube.com/@chet", "https://www.youtube.com/@tam"
    so.luu_doi_thu(goc, KENH, chet + "\n" + tam + "\n")

    def lay_kenh(link, **kw):
        raise RuntimeError("This channel does not exist." if link == chet else "HTTP Error 503: Service Unavailable temporarily")
    dem = cdt.chot(goc, KENH, lang="ja", lay_kenh=lay_kenh)
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    tt = {h[o["Link kênh"]]: h[o["Trạng thái"]] for h in hang}
    assert tt.get(chet) == db.BO, "kênh không tồn tại → bỏ luôn, không giữ trong hộp thư thử lại mãi"
    assert "không còn" in ghi_chu(hang, o, chet)
    assert tam not in tt and db.hop_thu(goc, KENH) == [tam], "lỗi TẠM (503) thì ở lại hộp thư, lượt sau thử lại"
    assert dem["o_lai"] == 0 and dem["loi"] == 1


def ghi_chu(hang, o, link):
    return next(h[o["Ghi chú"]] for h in hang if h[o["Link kênh"]] == link)


def test_khong_doi_trang_thai_khach_dat_tay(tmp_path):
    """Máy chỉ chấm thư chưa mở; kênh khách đã đặt 'theo dõi' bằng tay không bị máy lật thành 'bỏ'."""
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@zatsu"
    cot, hang = db.doc(goc, KENH)
    hang = db.gop_cham(cot, hang, [db.BanGhi(ten="大人の心理雑学", link=link)])
    db.luu(goc, KENH, cot, hang)
    so.luu_doi_thu(goc, KENH, link + "\n")
    assert db.hop_thu(goc, KENH) == [], "đã ở danh bạ thì không còn là thư chưa mở"
    dem = cdt.chot(goc, KENH, lang="ja", lay_kenh=_lay({link: _kenh("大人の心理雑学", link, 5890, LECH * 5)}))
    assert dem["cham"] == 0
    assert db.dang_theo_doi(goc, KENH) == [link]


def _hoi_gia(bang):
    """AI giả: trả DanhGia theo TÊN kênh; ghi lại ai đã bị hỏi."""
    hoi_roi = []

    def hoi(client, so_do, **kw):
        hoi_roi.append(so_do.ten)
        ket = bang.get(so_do.ten)
        if ket == "loi":
            raise RuntimeError("AI sập")
        return loc.DanhGia(ket=ket or "gan", diem=80 if ket == "doi_thu" else 30,
                           ly_do="lý do AI " + so_do.ten, tuyen=["lệch nhịp"] if ket == "doi_thu" else [])
    return hoi, hoi_roi


def test_cua_ai_chi_hoi_kenh_qua_cua_may_va_quyet_theo_ai(tmp_path):
    """Có ví: máy định theo dõi/để lại → hỏi AI; AI 'doi_thu' vào, 'gan'/'khong' bỏ. 29/09/2026: kênh
    máy định BỎ bằng TỪ KHOÁ (雑学 ở tên) cũng được hỏi — chỉ bỏ HIỂN NHIÊN mới không hỏi."""
    goc = _goc(tmp_path)
    links = {n: "https://www.youtube.com/@" + n for n in ("zure", "genki", "pure", "zatsu", "sap")}
    so.luu_doi_thu(goc, KENH, "\n".join(links.values()) + "\n")
    kho = {links["zure"]: _kenh("ズレは才能", links["zure"], 7700, LECH * 5, 10000, 570),
           links["genki"]: _kenh("ちょっと元気になれる心理学", links["genki"], 1950, CHUNG * 5, 1350, 780),
           links["pure"]: _kenh("pure life diary", links["pure"], 46300, CHUNG * 4 + ["一人時間の使い方"], 4350, 880),
           links["zatsu"]: _kenh("大人の心理雑学", links["zatsu"], 5890, LECH * 5, 3800, 960),
           links["sap"]: _kenh("心理サップ", links["sap"], 3000, CHUNG * 5, 2000, 800)}
    hoi, hoi_roi = _hoi_gia({"ズレは才能": "doi_thu", "ちょっと元気になれる心理学": "khong",
                             "pure life diary": "doi_thu", "心理サップ": "loi"})
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho), client=object(), mo_ta_kenh="kênh tâm lý",
                   hoi=hoi)
    assert "大人の心理雑学" in hoi_roi, "bỏ bằng TỪ KHOÁ (雑学) thì phải để AI đọc nghĩa"
    assert sorted(hoi_roi) == sorted(["ズレは才能", "ちょっと元気になれる心理学", "pure life diary", "心理サップ",
                                      "大人の心理雑学"])
    assert dem["ai_hoi"] == 4 and dem["ai_loai"] == 1, dem     # 'sap' AI sập → không tính là hỏi được
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    tt = {h[o["Kênh"]]: (h[o["Trạng thái"]], h[o["Ghi chú"]], h[o["Tuyến"]]) for h in hang}
    assert tt["ズレは才能"][0] == db.THEO_DOI and tt["ズレは才能"][1].startswith("AI: đối thủ") and tt["ズレは才能"][2] == "lệch nhịp"
    assert tt["pure life diary"][0] == db.THEO_DOI, "máy định 'gần' nhưng AI nói đối thủ → vào"
    assert tt["ちょっと元気になれる心理学"][0] == db.BO and "không phải kênh tâm lý — AI" in tt["ちょっと元気になれる心理学"][1]
    assert tt["大人の心理雑学"][0] == db.BO
    # 30/09/2026: AI sập → KHÔNG vào "theo dõi" bằng quyết định máy — ở lại hộp thư, lượt sau hỏi lại
    assert "心理サップ" not in tt and db.hop_thu(goc, KENH) == [links["sap"]] and dem["o_lai"] == 1


def test_ai_khong_doc_duoc_thi_giu_quyet_dinh_may_va_ghi_dau_cau_tra_loi(tmp_path):
    """06/09: 記憶博士 bị 'bỏ' chỉ vì AI trả về thứ không phải JSON. Không đọc được = không có ý kiến."""
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@zure"
    so.luu_doi_thu(goc, KENH, link + "\n")

    def hoi(client, so_do, **kw):
        return loc.DanhGia(ket="gan", ly_do="AI trả lời không đọc được — xem lại tay", khac="Xin lỗi, tôi không thể")
    nhat_ky = []
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, client=object(), mo_ta_kenh="x", hoi=hoi,
                   lay_kenh=_lay({link: _kenh("ズレは才能", link, 7700, LECH * 5, 10000, 570)}), on_log=nhat_ky.append)
    assert dem["theo_doi"] == 0 and dem["bo"] == 0 and dem["ai_hoi"] == 0 and dem["ai_khong_doc"] == 1
    assert db.hop_thu(goc, KENH) == [link], "AI không đọc được → không vào theo dõi bằng máy; ở lại hộp thư"
    assert any("Xin lỗi, tôi không thể" in m for m in nhat_ky), "đầu câu trả lời phải vào nhật ký để lần sau biết AI nói gì"


def test_khong_co_vi_thi_khong_hoi_ai(tmp_path):
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@zure"
    so.luu_doi_thu(goc, KENH, link + "\n")
    hoi, hoi_roi = _hoi_gia({"ズレは才能": "khong"})
    dem = cdt.chot(goc, KENH, lang="ja", lay_kenh=_lay({link: _kenh("ズレは才能", link, 7700, LECH * 5, 10000, 570)}), hoi=hoi)
    # 30/09/2026: không ví, không phán quyết ngách nào trong kho → không vào theo dõi (ở lại hộp thư)
    assert hoi_roi == [] and dem["ai_hoi"] == 0 and dem["theo_doi"] == 0 and dem["o_lai"] == 1
    assert db.hop_thu(goc, KENH) == [link]


def _ghi_kho_ai(goc, link, ket, ly_do="x"):
    d = os.path.join(goc, "CHANNEL", KENH, "nghien-cuu")
    with open(os.path.join(d, "kenh-ai.json"), "w", encoding="utf-8") as t:
        json.dump({link.lower(): {"ket": {"giu": "doi_thu", "bo": "khong"}[ket], "ly_do": ly_do,
                                  "ngay": _dt.date.today().isoformat(), "kiem_ngach": ket, "kenh": "kiem-ngach"}}, t)


def test_barry_nobles_khop_tu_khoa_khong_du_de_vao_theo_doi(tmp_path):
    """Ca thật 29/09: kênh không tâm lý, 188k sub, 'khớp tuyến 12%' bằng regex → vào theo dõi TL1."""
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@barrynobles95"
    so.luu_doi_thu(goc, KENH, link + "\n")
    td = LECH[:3] + ["今日の話"] * 22                       # 3/25 = 12% khớp
    kho = {link: _kenh("Barry Nobles", link, 188000, td, 13000, 900)}
    # AI sập: KHÔNG được vào theo dõi
    hoi, _r = _hoi_gia({"Barry Nobles": "loi"})
    cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho), client=object(), hoi=hoi, mo_ta_kenh="x")
    assert db.dang_theo_doi(goc, KENH) == [] and db.hop_thu(goc, KENH) == [link]
    # kho nhóm đã phán "bỏ" (kênh anh em) → không kênh nào tự lật lại, kể cả không ví
    _ghi_kho_ai(goc, link, "bo", "kênh đời sống, không tâm lý")
    cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho))
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    assert hang[0][o["Trạng thái"]] == db.BO and "kho nhóm" in hang[0][o["Ghi chú"]]


def test_khong_vi_dung_phan_quyet_giu_cua_kho_nhom(tmp_path):
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@zure"
    so.luu_doi_thu(goc, KENH, link + "\n")
    _ghi_kho_ai(goc, link, "giu", "chân dung tâm lý")
    cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay({link: _kenh("ズレは才能", link, 7700, LECH * 5, 10000, 570)}))
    assert db.dang_theo_doi(goc, KENH) == [link]


def test_kenh_ngung_dang_hon_30_ngay_thi_bo_khong_hoi_ai(tmp_path):
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@im"
    so.luu_doi_thu(goc, KENH, link + "\n")
    hoi, hoi_roi = _hoi_gia({"静かな心理": "doi_thu"})
    cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, client=object(), hoi=hoi, mo_ta_kenh="x",
             lay_kenh=_lay({link: _kenh("静かな心理", link, 9000, LECH * 5, 8000, 900, cach_ngay=45)}))
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    assert hoi_roi == [] and hang[0][o["Trạng thái"]] == db.BO and "ngừng hoạt động" in hang[0][o["Ghi chú"]]


def test_do_ung_vien_dem_dung_phan_tram():
    link = "https://www.youtube.com/@x"
    td = LECH[:2] + GIA[:3] + CHUNG[:5]           # 10 tiêu đề: 2 khớp, 3 già
    uv = cdt.do_ung_vien(link, lang="ja", lay_kenh=_lay({link: _kenh("心理ラボ", link, 1500, td)}))
    assert (uv.pct_khop, uv.pct_gia) == (20, 30) and uv.the_loai_loai is False


def test_kenh_ban_dua_tay_thi_may_khong_duoc_loai(tmp_path):
    """07/09: 大人の心理雑学 do chủ dự án dán vào bị máy bỏ vì tên có 雑学. Kênh người đưa = danh bạ."""
    goc = _goc(tmp_path)
    tay = "https://www.youtube.com/@shinrizatsugakuTV"
    may = "https://www.youtube.com/@kappumen"
    so.luu_doi_thu(goc, KENH, may)                       # máy ảo nhặt về → hộp thư
    assert so.them_ban_dua(goc, KENH, [tay, tay]) == 1   # khách dán → tệp riêng + hộp thư
    assert so.doc_ban_dua(goc, KENH) == [tay]
    assert sorted(db.hop_thu(goc, KENH)) == sorted([may, tay])
    assert cdt.kenh_ban_dua(goc, KENH) == {db.khoa(tay)}
    kho = {tay: _kenh("大人の心理雑学", tay, 5890, LECH * 5, 3800, 960),
           may: _kenh("カップ麺を待つ間に見たい雑学", may, 5000, CHUNG * 5, 3000, 900)}
    hoi_goi = []
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho), client=object(),
                   mo_ta_kenh="kênh tâm lý", hoi=lambda *a, **k: hoi_goi.append(1) or loc.DanhGia(ket="khong", diem=0, ly_do="x"))
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    tt = {db.khoa(h[o["Link kênh"]]): (h[o["Trạng thái"]], h[o["Ghi chú"]]) for h in hang}
    assert tt[db.khoa(tay)] == (db.THEO_DOI, cdt.GHI_CHU_BAN_DUA)
    assert tt[db.khoa(may)][0] == db.BO
    assert dem["ban_dua"] == 1
    # 29/09/2026: kênh máy ảo bị bỏ vì 雑学 ở tên (TỪ KHOÁ, không hiển nhiên) được AI đọc nghĩa một
    # lượt; kênh bạn đưa vẫn không tốn lượt nào.
    assert len(hoi_goi) == 1, "chỉ kênh máy ảo (bỏ bằng từ khoá) được hỏi; kênh bạn đưa không tốn lượt AI"


def test_theo_nghia_ai_cuu_kenh_tu_khoa_dinh_bo_va_khong_hoi_ca_hien_nhien(tmp_path):
    """Insight #8: kênh 雑学 tâm lý là đối thủ thật. AI nói đối thủ → VÀO; kênh tóm sách / sai tiếng
    (hiển nhiên) → bỏ không hỏi; AI sập → giữ luật từ khoá (ghi rõ)."""
    goc = _goc(tmp_path)
    links = {n: "https://www.youtube.com/@" + n for n in ("zatsu", "youyaku", "carrom", "barry")}
    so.luu_doi_thu(goc, KENH, "\n".join(links.values()) + "\n")
    kho = {links["zatsu"]: _kenh("大人の心理雑学", links["zatsu"], 5890, LECH * 5, 3800, 960),
           links["youyaku"]: _kenh("本要約チャンネル", links["youyaku"], 1_800_000, CHUNG * 5, 58000, 2200),
           links["carrom"]: _kenh("Carrom King", links["carrom"], 3_820_000, ["Carrom trick shots"] * 25, 1400, 230),
           links["barry"]: _kenh("Barry Nobles", links["barry"], 188000, ["今日の話"] * 25, 13000, 900)}
    hoi, hoi_roi = _hoi_gia({"大人の心理雑学": "doi_thu", "Barry Nobles": "loi"})
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, lay_kenh=_lay(kho), client=object(),
                   mo_ta_kenh="kênh tâm lý", hoi=hoi)
    assert sorted(hoi_roi) == ["Barry Nobles", "大人の心理雑学"], hoi_roi
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    tt = {h[o["Kênh"]]: (h[o["Trạng thái"]], h[o["Ghi chú"]]) for h in hang}
    assert tt["大人の心理雑学"][0] == db.THEO_DOI and "lật luật từ khoá" in tt["大人の心理雑学"][1]
    assert tt["本要約チャンネル"][0] == db.BO and tt["Carrom King"][0] == db.BO
    assert tt["Barry Nobles"][0] == db.BO and "giữ luật từ khoá" in tt["Barry Nobles"][1]
    assert tt["Barry Nobles"][1].startswith(cdt.DAU_BO_TU_KHOA), "AI sập: lượt sau còn nhận ra để xét lại"
    assert dem["ai_cuu"] == 1


def test_khong_vi_thi_duong_cu_giu_nguyen_ghi_chu(tmp_path):
    goc = _goc(tmp_path)
    link = "https://www.youtube.com/@zatsu"
    so.luu_doi_thu(goc, KENH, link + "\n")
    cdt.chot(goc, KENH, lang="ja", lay_kenh=_lay({link: _kenh("大人の心理雑学", link, 5890, LECH * 5)}))
    cot, hang = db.doc(goc, KENH)
    o = db.chi_so_cot(list(cot))
    assert hang[0][o["Ghi chú"]] == "không phải kênh tâm lý: thể loại 雑学/要約/tóm sách"


def test_xet_lai_kenh_cu_bi_bo_bang_tu_khoa(tmp_path):
    """Kênh bản cũ đã 'bỏ' bằng từ khoá (Ghi chú 'không phải kênh tâm lý:') được chấm lại theo nghĩa
    ở lượt chốt có ví; kênh AI đã phán, hay bỏ hiển nhiên, thì không bị chọn lại."""
    goc = _goc(tmp_path)
    cu, ai_da = "https://www.youtube.com/@zatsu", "https://www.youtube.com/@genki"
    cot, hang = db.doc(goc, KENH)
    hang = db.gop_cham(cot, hang, [db.BanGhi(ten="大人の心理雑学", link=cu), db.BanGhi(ten="元気", link=ai_da)])
    hang = db.dat_trang_thai(cot, hang, [cu, ai_da], db.BO)
    hang = db._dat_cot(cot, hang, [cu], "Ghi chú", "không phải kênh tâm lý: thể loại 雑学/要約/tóm sách")  # noqa: SLF001
    hang = db._dat_cot(cot, hang, [ai_da], "Ghi chú", "không phải kênh tâm lý — AI: tự lực")  # noqa: SLF001
    db.luu(goc, KENH, cot, hang)
    hoi, hoi_roi = _hoi_gia({"大人の心理雑学": "doi_thu"})
    dem = cdt.chot(goc, KENH, lang="ja", phut_muc_tieu=15, client=object(), mo_ta_kenh="x", hoi=hoi,
                   lay_kenh=_lay({cu: _kenh("大人の心理雑学", cu, 5890, LECH * 5, 3800, 960)}))
    assert hoi_roi == ["大人の心理雑学"] and dem["xet_lai"]["ai_cuu"] == 1
    assert db.khoa(cu) in {db.khoa(l) for l in db.dang_theo_doi(goc, KENH)}
