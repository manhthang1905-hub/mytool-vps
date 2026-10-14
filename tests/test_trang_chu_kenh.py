"""Trang chủ kênh (14/10/2026): HÀM THUẦN của `vm/thiet_lap_kenh_dom.py` cho `--dat-trang-chu` / `--dat-mo-ta` — chọn
video giới thiệu + video nổi bật từ `bang-tom-tat.csv` (hiển thị × tỷ lệ bấm, video dài, đủ tuổi, từ ngày bắt đầu, phải
«Công khai»), nhận phần «Video phổ biến», làm sạch + kiểm mô tả kênh tiếng Nhật. Không Chrome, không mạng."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
VM = GOC / "vm"
for _p in (str(GOC), str(VM)):
    if _p not in sys.path:
        sys.path.append(_p)

import thiet_lap_kenh_dom as t  # noqa: E402

HOM_NAY = date(2026, 10, 14)


def _h(vid, ngay, ht, tl, dai="12:30", tieu_de=None):
    return {"Tiêu đề": tieu_de or "動画 " + vid, "Mã video": vid, "Ngày đăng": ngay, "Dài": dai,
            "Lượt hiển thị": str(ht), "Tỷ lệ bấm": tl}


# ── đọc số ──
def test_giay_dai_ty_le_so_nguyen():
    assert t.giay_dai("13:05") == 785 and t.giay_dai("1:02:03") == 3723
    assert t.giay_dai("") is None and t.giay_dai("abc") is None and t.giay_dai("12") is None
    assert abs(t.ty_le_so("5.29%") - 0.0529) < 1e-9 and abs(t.ty_le_so("5,29 %") - 0.0529) < 1e-9
    assert t.ty_le_so("") == 0.0 and t.ty_le_so("0%") == 0.0
    assert t.so_nguyen("35330") == 35330 and t.so_nguyen("35,330") == 35330 and t.so_nguyen("") == 0


# ── xếp ứng viên ──
def test_xep_theo_hien_thi_nhan_ty_le_bam():
    hang = [_h("aaaaaaaaaaa", "2026-10-01", 13718, "6.77%"),     # ≈ 928.7
            _h("bbbbbbbbbbb", "2026-10-05", 35330, "5.29%"),     # ≈ 1869 — tốt nhất
            _h("ccccccccccc", "2026-10-02", 5182, "3.31%")]
    ds = t.xep_video_gioi_thieu(hang, "2026-09-21", HOM_NAY)
    assert [x["vid"] for x in ds] == ["bbbbbbbbbbb", "aaaaaaaaaaa", "ccccccccccc"]
    assert ds[0]["diem"] == round(35330 * 0.0529, 1) and ds[0]["dai"] == 750


def test_loai_video_moi_cu_ngan_va_khong_co_bam():
    hang = [_h("moi00000000", "2026-10-08", 99999, "9%"),          # 6 ngày tuổi — chưa đủ 7
            _h("du7ngay0000", "2026-10-07", 100, "2%"),            # đúng 7 ngày — nhận
            _h("truocmoc000", "2026-09-20", 99999, "9%"),          # trước ngày bắt đầu (khuôn cũ)
            _h("shorts00000", "2026-10-01", 99999, "9%", dai="0:58"),
            _h("bamkhong000", "2026-10-01", 500, "0%"),
            _h("ma-sai", "2026-10-01", 99999, "9%"),
            _h("ngaysai0000", "", 99999, "9%")]
    assert [x["vid"] for x in t.xep_video_gioi_thieu(hang, "2026-09-21", HOM_NAY)] == ["du7ngay0000"]


def test_khong_co_ngay_bat_dau_va_trung_ma():
    hang = [_h("aaaaaaaaaaa", "2026-08-01", 1000, "5%"), _h("aaaaaaaaaaa", "2026-08-01", 2000, "5%")]
    ds = t.xep_video_gioi_thieu(hang, "", HOM_NAY)
    assert len(ds) == 1 and ds[0]["hien_thi"] == 2000


# ── chọn theo «Công khai» ──
def test_chon_hai_cong_khai_dau_bang_bo_qua_rieng_tu_va_khong_thay():
    uv = [{"vid": v, "tieu_de": v} for v in ("v1", "v2", "v3", "v4")]
    gt, nb, bo = t.chon_gioi_thieu(uv, {"v1": "rieng_tu", "v2": "cong_khai", "v4": "cong_khai"})
    assert gt["vid"] == "v2" and nb["vid"] == "v4"
    assert len(bo) == 2 and "Studio: rieng_tu" in bo[0] and "không thấy trên Studio" in bo[1]


def test_chon_khi_chi_mot_hoac_khong_co_cong_khai():
    uv = [{"vid": "v1"}, {"vid": "v2"}]
    assert t.chon_gioi_thieu(uv, {"v1": "cong_khai", "v2": "da_len_lich"})[:2] == ({"vid": "v1"}, None)
    assert t.chon_gioi_thieu(uv, {})[:2] == (None, None)
    assert t.chon_gioi_thieu([], {}) == (None, None, [])


# ── bố cục ──
def test_co_phan_pho_bien_da_ngon_ngu():
    assert t.co_phan_pho_bien(["Dành cho bạn", "Video phổ biến (22)"])
    assert t.co_phan_pho_bien("おすすめ\n人気の動画")
    assert t.co_phan_pho_bien(["Popular videos"])
    assert not t.co_phan_pho_bien(["Video (22)", "Danh sách phát đã tạo (2)"]) and not t.co_phan_pho_bien(None)


# ── thẻ Trang chủ: đọc bố cục / menu / hộp chọn (DOM đo 14/10 trên TL2-T7, thăm dò không lưu) ──
def _bo_cuc(bat=False, trailer="", them_tat=None, pho_bien=False):
    phan = [{"tag": "ytcp-shelf-list-item", "hien": True, "chu": "Dành cho bạn YouTube đề xuất nội dung mới dựa trên mối quan tâm"},
            {"tag": "ytcp-shelf-list-item", "hien": True, "chu": "Video (23) 16:08 14:33 17:33"},
            {"tag": "ytcp-shelf-list-item", "hien": True, "chu": "Danh sách phát đã tạo (2) 23 84"}]
    if pho_bien:
        phan.append({"tag": "ytcp-shelf-list-item", "hien": True, "chu": "Video phổ biến (23) 18:41 14:17"})
    tl = [{"tag": "ytcp-spotlight-trailer-video-item", "hien": bool(trailer),
           "chu": ("Video giới thiệu kênh cho người chưa đăng ký Tiêu đề video " + trailer) if trailer else "", "ma": ["aaaaaaaaaaa"] if trailer else []}]
    return {"bat": bat, "ke": True, "them": {"hien": True, "tat": (not bat) if them_tat is None else them_tat},
            "phan": phan, "trailer": tl, "noi_bat": [{"tag": "ytcp-spotlight-featured-video-item", "hien": False, "chu": "", "ma": []}],
            "hop_chon": False}


def test_tom_trang_chu_tat_va_chua_dat():
    t0 = t.tom_trang_chu(_bo_cuc())
    assert t0["bat"] is False and t0["them_tat"] is True and t0["hop_chon"] is False
    assert t0["trailer"] == {"co": False, "tieu_de": "", "ma": []} and t0["noi_bat"]["co"] is False
    assert t0["phan"][0].startswith("Dành cho bạn") and len(t0["phan"][0]) <= 40
    assert t0["phan"][1:] == ["Video", "Danh sách phát đã tạo"] and t0["pho_bien"] is False


def test_tom_trang_chu_da_dat():
    t1 = t.tom_trang_chu(_bo_cuc(bat=True, trailer="【心理学】テスト用の架空タイトルその一", pho_bien=True))
    assert t1["bat"] is True and t1["them_tat"] is False and t1["pho_bien"] is True
    assert t1["trailer"]["co"] and t1["trailer"]["tieu_de"] == "【心理学】テスト用の架空タイトルその一"
    assert t1["trailer"]["ma"] == ["aaaaaaaaaaa"]


def test_tom_trang_chu_khong_doc_duoc():
    t9 = t.tom_trang_chu(None)
    assert t9["bat"] is None and t9["them_tat"] is None and t9["phan"] == []
    assert t.tom_trang_chu({"bat": "true"})["bat"] is None          # sai kiểu → không đoán


def test_khop_tieu_de():
    assert t.khop_tieu_de("【脳科学】架空の題名", "【脳科学】架空の題名 ")
    assert t.khop_tieu_de("【脳科学】架空の題名｜「テスト用」と感じさせる人の…", "【脳科学】架空の題名｜「テスト用」と感じさせる人の共通点")
    assert not t.khop_tieu_de("【脳科学】架空", "【脳科学】架空の題名｜「テスト用」")       # đầu quá ngắn
    assert not t.khop_tieu_de("", "x") and not t.khop_tieu_de("動画A", "動画B")


MENU = [{"chu": "Video giới thiệu kênh", "test_id": "SHELF_TYPE_SPOTLIGHT_TRAILER_VIDEO", "tat": False, "x": 1, "y": 1},
        {"chu": "Video nổi bật (dành cho người đăng ký cũ)", "test_id": "", "tat": False, "x": 1, "y": 2},
        {"chu": "Video", "test_id": "", "tat": True, "x": 1, "y": 3},
        {"chu": "Video phổ biến", "test_id": "", "tat": False, "x": 1, "y": 4},
        {"chu": "Kênh nổi bật", "test_id": "", "tat": False, "x": 1, "y": 5}]


def test_chon_muc_phan():
    assert t.chon_muc_phan(MENU, t.RE_MUC_TRAILER)["y"] == 1
    assert t.chon_muc_phan(MENU, t.RE_MUC_NOI_BAT)["y"] == 2            # không nhầm «Kênh nổi bật»
    assert t.chon_muc_phan(MENU, t.RE_MUC_PHO_BIEN)["y"] == 4           # không nhầm «Video»
    assert t.chon_muc_phan(MENU[2:3], t.RE_MUC_PHO_BIEN) is None and t.chon_muc_phan(None, t.RE_MUC_TRAILER) is None


def test_chon_the_video_dung_ma():
    the = [{"tieu_de": "A", "ma": "aaaaaaaaaaa", "hien": True, "tat": False},
           {"tieu_de": "B", "ma": "bbbbbbbbbbb", "hien": True, "tat": False}]
    assert t.chon_the_video(the, "bbbbbbbbbbb")["tieu_de"] == "B"
    assert t.chon_the_video(the, "ccccccccccc") is None and t.chon_the_video(the, "") is None
    assert t.chon_the_video(the + [dict(the[1])], "bbbbbbbbbbb") is None            # trùng mã → không đoán
    assert t.chon_the_video([dict(the[0], tat=True)], "aaaaaaaaaaa") is None


# ── mô tả kênh ──
MO_TA_DAT = ("人間関係や日々の小さな違和感を、心理学と脳科学の視点からやさしくひもとくチャンネルです。\n\n"
             "「なぜあの人はああするのか」「自分はどんなタイプなのか」——身近な疑問を、根拠のある知見とともに、"
             "ゆっくり聞ける動画でお届けします。自分のことも、まわりの人のことも、少し好きになれるはずです。\n\n"
             "新しい発見を見逃さないよう、よろしければチャンネル登録をお願いします。")


def test_lam_sach_mo_ta():
    assert t.lam_sach_mo_ta_kenh("```\n「本文です」\n```") == "本文です"
    assert t.lam_sach_mo_ta_kenh("  一行目  \r\n\r\n\r\n\r\n二行目 ") == "一行目\n\n二行目"


def test_kiem_mo_ta_dat_va_do_dai():
    assert 150 <= t.do_dai_mo_ta(MO_TA_DAT) <= 300
    assert t.kiem_mo_ta_kenh(MO_TA_DAT) == []
    assert any("dài" in x for x in t.kiem_mo_ta_kenh("短いです。"))
    assert any("dài" in x for x in t.kiem_mo_ta_kenh(MO_TA_DAT * 3))


def test_kiem_mo_ta_bat_loi_noi_dung():
    assert any("tiếng Nhật" in x for x in t.kiem_mo_ta_kenh("Psychology " * 20))
    assert any("link" in x for x in t.kiem_mo_ta_kenh(MO_TA_DAT[:200] + " https://example.com"))
    assert any("link" in x for x in t.kiem_mo_ta_kenh(MO_TA_DAT[:200] + " @kenh"))
    assert any("< >" in x for x in t.kiem_mo_ta_kenh(MO_TA_DAT[:200] + "<登録>"))
    assert any("markdown" in x for x in t.kiem_mo_ta_kenh("**" + MO_TA_DAT[:200] + "**"))


def test_loi_nhac_mo_ta_mang_du_du_kien():
    p = t.loi_nhac_mo_ta_kenh("テスト心理チャンネル", {"ten": "架空の自分図鑑 — tâm lý", "luat_chon": "心理", "giong_van": "ていねい体"},
                              ["【脳科学】架空の題名"], ["日常の心理を解説します。\n登録してね"])
    assert "テスト心理チャンネル" in p and "架空の題名" in p and "ていねい体" in p
    assert "日常の心理を解説します。 / 登録してね" in p and "150-300" in p
