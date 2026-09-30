"""Biên tập viên AI (`core/bien_tap_content.py`, 29/09/2026) — không mạng, `goi_chat` giả.

Canh: hợp đồng trả về (thứ tự link + lý do + dự đoán) · bối cảnh đủ khối (định vị, khán giả,
video mình, lời thoại, đã làm) · thang mô hình mạnh nhất trước + lùi bậc khi hỏng · JSON hỏng /
AI loại hết / không có goi_chat → None (điểm móc giữ thứ tự công thức) · lưu quyết định ·
`danh_gia_lai` nối nguồn → gói → số 48h và nuôi lại bối cảnh lần sau.
"""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bien_tap_content as bt  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402

K = "TLX-T7"
LUC = dt.datetime(2026, 9, 29, 23, 5)


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as t:
        t.write(chu)


def _goc(tmp_path):
    goc = str(tmp_path)
    k = os.path.join(goc, "CHANNEL", K)
    _ghi(os.path.join(k, "kenh.yaml"), 'ma: "{0}"\nten: "テスト図鑑"\nngon_ngu: "ja"\nphut_muc_tieu: 15\n'.format(K))
    _ghi(os.path.join(k, "nghien-cuu", "tuyen.csv"),
         "Mã,Tên tuyến,Kênh của tôi,Trạng thái,Insight,Lúc bấm họ đang,Họ cần,Từ khoá nhận biết,Mô tả,Ghi chú\n"
         "to-mo,Người tò mò,{0},đang đánh,Thói quen này nói gì về tôi?,thoải mái,được tặng điều thú vị,"
         "làm vườn · mèo,Đời ổn,\n".format(K))
    cot = so.cot_mac_dinh()
    o = {c: i for i, c in enumerate(cot)}
    hang = []
    for ma, td, view in (("aaaaaaaaaaa", "猫が好きな人の特徴", "120000"), ("bbbbbbbbbbb", "庭いじりが好きな人", "80000"),
                         ("ccccccccccc", "一人旅にハマる人", "50000")):
        d = [""] * len(cot)
        d[o["Kênh"]], d[o["Tiêu đề video"]], d[o["Link video"]] = "心理ラボ", td, "https://www.youtube.com/watch?v=" + ma
        d[o["View"]], d[o["Ngày đăng"]], d[o["Mô tả"]] = view, "2026-09-20", "説明 " + td
        hang.append(d)
    so.luu_bang(goc, K, cot, hang)
    return goc


UV = [{"nguon": "vph", "ma": "aaaaaaaaaaa", "link": "https://www.youtube.com/watch?v=aaaaaaaaaaa",
       "tieu_de": "猫が好きな人の特徴", "kenh": "心理ラボ", "diem": 90, "vph": 500, "dot_bien": 12.0},
      {"nguon": "vph", "ma": "bbbbbbbbbbb", "link": "https://www.youtube.com/watch?v=bbbbbbbbbbb",
       "tieu_de": "庭いじりが好きな人", "kenh": "心理ラボ", "diem": 80},
      {"nguon": "vph", "ma": "ccccccccccc", "link": "https://www.youtube.com/watch?v=ccccccccccc",
       "tieu_de": "一人旅にハマる人", "kenh": "心理ラボ", "diem": 70}]

TRA_LOI = json.dumps({
    "nhan_dinh": "Tệp tò mò cần thói quen vô hại.",
    "chon": [{"u": 2, "ly_do": "làm vườn đúng cửa vào", "vi_sao_no": "tò mò", "chuyen_duoc": "55+ làm vườn",
              "ctr": 5.8, "avd_giay": 400, "ket_cuc": "thắng", "rui_ro": "nguồn chậm"},
             {"u": "U1", "ly_do": "mèo", "ctr": "4–5%", "ket_cuc": "vừa"}],
    "con_lai": [],
    "loai": {"3": "một mình = tệp khác"}}, ensure_ascii=False)


def _goi(tra=TRA_LOI, ghi=None, hong=()):
    def goi(loi_nhac, **kw):
        if ghi is not None:
            ghi.append((loi_nhac, kw))
        if kw.get("mo_hinh") in hong:
            raise RuntimeError("hết hạn mức " + kw.get("mo_hinh"))
        return tra
    return goi


def test_chon_tra_dung_hop_dong_va_luu_quyet_dinh(tmp_path):
    goc = _goc(tmp_path)
    goi_roi = []
    kq = bt.chon(goc, K, UV, _goi(ghi=goi_roi), so_chon=2, bay_gio=LUC)
    assert kq["thu_tu"] == [UV[1]["link"], UV[0]["link"]], "AI đảo thứ tự; ứng viên bị loại không có mặt"
    assert kq["ly_do"][UV[1]["link"]] == "làm vườn đúng cửa vào"
    assert kq["du_doan"][UV[1]["link"]]["ctr"] == "5.8" and kq["du_doan"][UV[0]["link"]]["ctr_so"] == 4.5
    assert kq["loai"] == {UV[2]["link"]: "một mình = tệp khác"}
    assert os.path.isfile(kq["tep"]) and os.path.basename(kq["tep"]) == "2026-09-29-2305.json"
    luu = json.load(open(kq["tep"], encoding="utf-8"))
    assert luu["mo_hinh"] == "claude-fable-5" and luu["thu_tu"] == kq["thu_tu"]
    loi_nhac, kw = goi_roi[0]
    assert kw["mo_hinh"] == "claude-fable-5", "bước này dùng mô hình MẠNH NHẤT"
    for khoi in ("ĐỊNH VỊ KÊNH", "Người tò mò", "KHÁN GIẢ THẬT", "CẢ NHÓM ĐÃ LÀM", "[U3]", "MÔ TẢ VIDEO",
                 "×12.0", "心理ラボ"):
        assert khoi in loi_nhac, khoi


def test_loi_thoai_trong_kho_duoc_dua_vao(tmp_path):
    goc = _goc(tmp_path)
    from core import loi_thoai
    loi_thoai.ghi(goc, K, "aaaaaaaaaaa", text="猫を飼う人は" * 200, tieu_de="猫が好きな人の特徴")
    goi_roi = []
    bt.chon(goc, K, UV, _goi(ghi=goi_roi), bay_gio=LUC, luu=False)
    assert "LỜI THOẠI (trích" in goi_roi[0][0] and "猫を飼う人は" in goi_roi[0][0]


def test_lui_bac_mo_hinh_khi_hong_va_mo_hinh_rieng_cua_kenh(tmp_path):
    goc = _goc(tmp_path)
    goi_roi = []
    kq = bt.chon(goc, K, UV, _goi(ghi=goi_roi, hong=("claude-fable-5",)), bay_gio=LUC, luu=False)
    assert [kw["mo_hinh"] for _p, kw in goi_roi] == ["claude-fable-5", "claude-opus-5"]
    assert kq is not None and kq["mo_hinh"] == "claude-opus-5"
    with open(os.path.join(goc, "CHANNEL", K, "kenh.yaml"), "a", encoding="utf-8") as t:
        t.write('mo_hinh_bien_tap: "claude-opus-5"\n')
    assert bt.thang_mo_hinh(goc, K)[:2] == ["claude-opus-5", "claude-fable-5"]


def test_none_khi_khong_the_quyet(tmp_path):
    goc = _goc(tmp_path)
    nhat_ky = []
    assert bt.chon(goc, K, UV, None, ghi=nhat_ky.append) is None
    assert bt.chon(goc, K, [], _goi()) is None
    assert bt.chon(goc, K, UV, _goi(tra="Xin lỗi, tôi không thể"), ghi=nhat_ky.append, bay_gio=LUC) is None
    loai_het = json.dumps({"chon": [], "con_lai": [], "loai": {"1": "a", "2": "b", "3": "c"}})
    assert bt.chon(goc, K, UV, _goi(tra=loai_het), ghi=nhat_ky.append, bay_gio=LUC) is None
    assert any("CẢNH BÁO: AI loại cả 3" in m for m in nhat_ky), "loại hết phải nói to, không im lặng"
    assert any("giữ thứ tự công thức" in m for m in nhat_ky)


def test_ung_vien_ai_bo_sot_duoc_noi_cuoi_theo_thu_tu_cong_thuc():
    tra = json.dumps({"chon": [{"u": 3, "ly_do": "x", "ctr": 5}], "con_lai": [], "loai": {}})
    uv = bt._chuan_hoa_ung_vien(UV)
    kq = bt.doc_ket_qua(tra, uv)
    assert kq["thu_tu"] == [UV[2]["link"], UV[0]["link"], UV[1]["link"]]


def test_danh_gia_lai_noi_du_doan_voi_so_48h_va_nuoi_boi_canh(tmp_path):
    goc = _goc(tmp_path)
    kq = bt.chon(goc, K, UV, _goi(), so_chon=2, bay_gio=LUC)
    k = os.path.join(goc, "CHANNEL", K)
    # nguồn bbbbbbbbbbb đã sản xuất thành gói TLX-T7-0003, video đã có số 48h
    _ghi(os.path.join(k, "tu-chay", "2026-09-30.json"), json.dumps({"runs": [
        {"ma_luot": "0003", "nguon": {"ma": "bbbbbbbbbbb", "link": UV[1]["link"], "tieu_de": "庭いじりが好きな人"},
         "ban_giao": {"ma_goi": K + "-0003"}}]}))
    _ghi(os.path.join(k, "ho-so-video", K + "-0003.json"), json.dumps({
        "ma_goi": K + "-0003", "tieu_de": "【雑学】庭いじりが好きな人", "video_id": "zzzzzzzzzzz",
        "chi_so": {"48h": {"impressions": 1800, "ctr": 3.1, "views": 120, "avd_giay": 300}}}))
    phan_hoi = json.dumps({"ca": {"1": "Kênh non, trang chủ chưa thử rộng."}, "bai_hoc": ["Kênh <100 sub: hạ CTR 2 điểm."]},
                          ensure_ascii=False)
    kq2 = bt.danh_gia_lai(goc, K, goi_chat=_goi(tra=phan_hoi), bay_gio=LUC + dt.timedelta(days=3))
    assert kq2["moi"] == 1
    dg = json.load(open(os.path.join(k, "nghien-cuu", "bien-tap", "danh-gia.json"), encoding="utf-8"))
    b = dg["ban_ghi"][0]
    assert b["ma_goi"] == K + "-0003" and b["dung"] is False and b["ket_cuc_that"] == "trượt"
    assert b["lech_ctr"] == round(3.1 - 5.8, 2) and "Kênh non" in b["vi_sao_sai"]
    assert os.path.isfile(os.path.join(k, "nghien-cuu", "bien-tap", "BAI-HOC-BIEN-TAP.md"))
    # chấm rồi thì không chấm lại
    assert bt.danh_gia_lai(goc, K, bay_gio=LUC + dt.timedelta(days=4))["moi"] == 0
    # lần chọn sau thấy bài học "tự sửa"
    goi_roi = []
    bt.chon(goc, K, UV, _goi(ghi=goi_roi), bay_gio=LUC + dt.timedelta(days=4), luu=False)
    assert "Kênh <100 sub: hạ CTR 2 điểm." in goi_roi[0][0] and "SAI" in goi_roi[0][0]
    assert kq["tep"]


def test_khong_bao_gio_nem_loi(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    monkeypatch.setattr(bt, "dung_boi_canh", lambda *a, **k: 1 / 0)
    nhat_ky = []
    assert bt.chon(goc, K, UV, _goi(), ghi=nhat_ky.append) is None
    assert any("hỏng ngoài dự kiến" in m for m in nhat_ky)


def test_dang_bat_mac_dinh_va_tat_duoc(tmp_path):
    goc = _goc(tmp_path)
    assert bt.dang_bat(goc, K) is True
    with open(os.path.join(goc, "CHANNEL", K, "kenh.yaml"), "a", encoding="utf-8") as t:
        t.write("bien_tap_ai: false\n")
    assert bt.dang_bat(goc, K) is False
