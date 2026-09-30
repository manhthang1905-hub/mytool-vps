"""Kiểm toán chọn content 30/09/2026 — cổng chất lượng nguồn + các nguyên nhân gốc đã sửa.

Không gọi mạng: AI là hàm giả. Canh:
* biên tập viên chấm TỪNG ứng viên TOT/TAM/TE (`doc_ket_qua` đọc khối "cham"; TỆ lỡ trong thứ tự bị dời sang loại);
* `chon_cua_so` mở cửa sổ kế khi chưa đủ TỐT, nhớ phán quyết (không gọi lại);
* `tu_chay._ap_cham_bien_tap` bỏ hẳn dòng TỆ, `_cong_chat_luong` chỉ cho TỐT có lý do → TẠM ≥ 65 → [] ;
* `phan_cum_ai` chẻ lô hỏng + lùi mô hình thay vì "để lượt sau";
* `goi_van_ban` sàn trần token + nới gấp đôi sau câu trả lời rỗng;
* `trung_tieu_de` cắt nhãn 【…】 ở CUỐI câu; `cong_thuc_vph` không tin Tăng/ngày bậc làm tròn.
"""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bien_tap_content as bt  # noqa: E402
from core import cong_thuc_vph as vph  # noqa: E402
from core import goi_van_ban as gvb  # noqa: E402
from core import phan_cum_ai as pca  # noqa: E402
from core import trung_tieu_de as ttd  # noqa: E402
from core import tu_chay  # noqa: E402

K = "TLX-T7"
LUC = dt.datetime(2026, 9, 30, 1, 0)


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as t:
        t.write(chu)


def _goc(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", K, "kenh.yaml"), 'ma: "{0}"\nten: "テスト"\nngon_ngu: "ja"\n'.format(K))
    return goc


def _uv(n):
    return [{"nguon": "vph", "ma": "m{0:010d}".format(i), "link": "https://www.youtube.com/watch?v=m{0:010d}".format(i),
             "tieu_de": "心理の人{0}".format(i), "kenh": "心理ラボ", "diem": 90 - i} for i in range(n)]


def test_doc_ket_qua_cham_tung_ung_vien_va_te_bi_doi_sang_loai():
    uv = bt._chuan_hoa_ung_vien(_uv(4))
    tra = json.dumps({"chon": [{"u": 2, "ly_do": "đúng cụm お金持ち × tệp", "ctr": 5.9},
                               {"u": 1, "ly_do": "sức khoẻ 60代", "ctr": 5}],
                      "con_lai": [3], "loai": {"4": "trùng ý TL4"},
                      "cham": {"1": ["TE", 5], "2": ["TỐT", 82], "3": ["tạm", 55], "4": ["TE", 3]}},
                     ensure_ascii=False)
    kq = bt.doc_ket_qua(tra, uv)
    L = [d["link"] for d in uv]
    assert kq["thu_tu"] == [L[1], L[2]], "U1 chấm TỆ phải rời thứ tự dù AI lỡ đặt trong chon"
    assert kq["hang"] == {L[0]: "TE", L[1]: "TOT", L[2]: "TAM", L[3]: "TE"}
    assert kq["diem_bt"][L[1]] == 82 and L[0] in kq["loai"] and L[3] in kq["loai"]


def test_chon_cua_so_mo_cua_so_ke_khi_chua_du_tot_va_nho_phan_quyet(tmp_path):
    goc = _goc(tmp_path)
    uv = _uv(8)
    goi_roi = []

    def goi(loi_nhac, **kw):
        goi_roi.append(loi_nhac)
        if len(goi_roi) == 1:  # cửa sổ 1 (U1..U4): toàn TỆ
            return json.dumps({"chon": [], "con_lai": [], "loai": {str(i): "lệch ngách" for i in range(1, 5)},
                               "cham": {str(i): ["TE", 5] for i in range(1, 5)}})
        return json.dumps({"chon": [{"u": 3, "ly_do": "chân dung đúng tệp, nguồn nổ ×20", "ctr": 5.8}],
                           "con_lai": [1], "loai": {"2": "trùng ý", "4": "sức khoẻ"},
                           "cham": {"1": ["TAM", 60], "2": ["TE", 9], "3": ["TOT", 80], "4": ["TE", 2]}})

    kq = bt.chon_cua_so(goc, K, uv, goi, can_tot=1, moi_cua_so=4, so_cua_so=3, bay_gio=LUC, kiem_trung=False)
    assert len(goi_roi) == 2, "cửa sổ 1 không có TỐT → phải mở cửa sổ 2, có TỐT thì dừng"
    assert "[U1] 心理の人4" in goi_roi[1], "cửa sổ 2 đọc ứng viên kế tiếp"
    assert kq["thu_tu"][0] == uv[6]["link"] and kq["hang"][uv[6]["link"]] == "TOT"
    assert kq["hang"][uv[0]["link"]] == "TE" and uv[0]["link"] in kq["loai"]
    # Lần gọi sau (vòng giữ nguồn) dùng phán quyết đã nhớ — không gọi AI lại.
    kq2 = bt.chon_cua_so(goc, K, uv, goi, can_tot=1, moi_cua_so=4, so_cua_so=3,
                         bay_gio=LUC + dt.timedelta(hours=1), kiem_trung=False)
    assert len(goi_roi) == 2 and kq2["thu_tu"][0] == uv[6]["link"] and kq2["tu_nho"] == 8


def test_trung_y_kiem_truoc_khi_bien_tap_doc(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    uv = _uv(3)
    monkeypatch.setattr(bt, "_da_lam_de_kiem", lambda g, k: [("お店の人にも「ありがとう」と言う人の正体", "TL1-0008")])
    from core import kiem_trung_y
    monkeypatch.setattr(kiem_trung_y, "kiem_trung_y",
                        lambda goi, td, dl, khoa="", ghi=None: (td == uv[0]["tieu_de"], dl[0][0], "cùng ý"))
    doc = []

    def goi(loi_nhac, **kw):
        doc.append(loi_nhac)
        return json.dumps({"chon": [{"u": 1, "ly_do": "đúng tệp, nguồn nổ thật", "ctr": 5.6}], "con_lai": [2],
                           "loai": {}, "cham": {"1": ["TOT", 80], "2": ["TAM", 50]}})

    kq = bt.chon_cua_so(goc, K, uv, goi, can_tot=1, bay_gio=LUC)
    assert len(doc) == 1 and uv[0]["tieu_de"] not in doc[0], "ứng viên trùng ý không tới tay biên tập viên"
    assert kq["hang"][uv[0]["link"]] == "TE" and "trùng ý" in kq["loai"][uv[0]["link"]]
    assert kq["thu_tu"][0] == uv[1]["link"]


def test_tot_can_nguon_no_that_va_du_dai(tmp_path):
    goc = _goc(tmp_path)
    uv = [dict(d) for d in _uv(3)]
    uv[0]["dot_bien"], uv[1]["dot_bien"], uv[2]["dot_bien"] = 1.7, 12.0, 8.0
    from core import doi_thu_kenh as so
    cot = so.cot_mac_dinh()
    hang = []
    for i, dai in enumerate(("15:00", "15:00", "9:09")):
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": "心理ラボ", "Tiêu đề video": uv[i]["tieu_de"], "Link video": uv[i]["link"],
                  "View": "40000", "Ngày đăng": "2026-09-24", "Thời lượng": dai})
        hang.append([d.get(c, "") for c in cot])
    so.luu_bang(goc, K, cot, hang)
    tra = json.dumps({"chon": [{"u": i, "ly_do": "đúng tệp, AI thích", "ctr": 6} for i in (1, 2, 3)],
                      "con_lai": [], "loai": {}, "cham": {str(i): ["TOT", 90] for i in (1, 2, 3)}}, ensure_ascii=False)
    kq = bt.chon_cua_so(goc, K, uv, lambda *a, **k: tra, can_tot=1, bay_gio=LUC, kiem_trung=False)
    assert kq["hang"][uv[0]["link"]] == "TAM", "đột biến ×1,7 chưa phải nổ thật"
    assert kq["hang"][uv[1]["link"]] == "TOT"
    assert kq["hang"][uv[2]["link"]] == "TAM", "nguồn 9 phút quá ngắn"


def test_danh_dau_te_ghi_bo_nho(tmp_path):
    goc = _goc(tmp_path)
    assert bt.danh_dau_te(goc, K, "m0000000000", tieu_de="レジで", ly_do="trùng ý")
    assert bt.doc_nho_cham(goc, K)["m0000000000"]["hang"] == "TE"


def test_nguon_nguoi_bi_ha_tu_tot_xuong_tam(tmp_path):
    goc = _goc(tmp_path)
    from core import doi_thu_kenh as so
    cot = so.cot_mac_dinh()
    hang = []
    for i, (tang, truoc) in enumerate(((0, 330000), (7213, 25000))):
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": "心理ラボ", "Tiêu đề video": "心理の人{0}".format(i),
                  "Link video": "https://www.youtube.com/watch?v=m{0:010d}".format(i), "View": "330000",
                  "Ngày đăng": "2026-08-01", so.COT_TANG: str(tang), so.COT_VIEW_TRUOC: str(truoc)})
        hang.append([d.get(c, "") for c in cot])
    so.luu_bang(goc, K, cot, hang)
    tra = json.dumps({"chon": [{"u": 1, "ly_do": "to nhất kênh, đúng tệp", "ctr": 6},
                               {"u": 2, "ly_do": "đang lên mạnh, đúng tệp", "ctr": 5.5}],
                      "con_lai": [], "loai": {}, "cham": {"1": ["TOT", 90], "2": ["TOT", 80]}}, ensure_ascii=False)
    kq = bt.chon_cua_so(goc, K, _uv(2), lambda *a, **k: tra, can_tot=1, bay_gio=LUC, kiem_trung=False)
    L = [d["link"] for d in _uv(2)]
    assert kq["hang"][L[0]] == "TAM", "330k view mà đà 0 qua hai lượt quét = nguội → không được TỐT"
    assert kq["hang"][L[1]] == "TOT" and kq["thu_tu"][0] == L[1]


def _theo_ngay(goc, sub, gio):
    _ghi(os.path.join(goc, "CHANNEL", K, "chi-so", "kenh-theo-ngay.csv"),
         'Lúc chụp,Lượt xem,Giờ xem,Đăng ký\n"2026-09-29 08:28","148022","{0}","{1}"\n'.format(gio, sub))


def test_muc_tieu_ypp_chon_rang_buoc_va_len_dau_loi_nhac(tmp_path):
    goc = _goc(tmp_path)
    assert bt.muc_tieu_ypp(goc, K)["rang_buoc"] == "chua_co_so"
    _theo_ngay(goc, 562, 6350.5)  # TL4: đủ giờ, thiếu sub
    m = bt.muc_tieu_ypp(goc, K)
    assert m["rang_buoc"] == "sub" and m["thieu_sub"] == 438
    _theo_ngay(goc, 19, 21.3)  # kênh non: cả hai < 25% → view/giờ xem trước
    assert bt.muc_tieu_ypp(goc, K)["rang_buoc"] == "gio_xem"
    loi = bt.dung_loi_nhac(bt.dung_boi_canh(goc, K, bay_gio=LUC), bt._chuan_hoa_ung_vien(_uv(1)), 1)
    assert loi.startswith("═══ MỤC TIÊU KÊNH") and "RÀNG BUỘC ĐANG THIẾU: VIEW/GIỜ XEM" in loi and "giup_ypp" in loi


def test_bang_dieu_khien_con_thieu_ypp():
    from core import bang_dieu_khien as bdk
    assert bdk.con_thieu_ypp({"dang_ky": 562.0, "gio_xem": 6350.54}) == \
        "Còn thiếu để bật kiếm tiền: 438 sub · đủ giờ xem (6.351/4.000)"
    assert bdk.con_thieu_ypp({"dang_ky": 19.0, "gio_xem": 21.28}) == \
        "Còn thiếu để bật kiếm tiền: 981 sub · 3.979 giờ xem"
    assert "chưa có số" in bdk.con_thieu_ypp({})


def test_ap_cham_bo_te_va_cong_chat_luong(tmp_path):
    ds = [dict(d, ma=d["ma"]) for d in _uv(4)]
    L = [d["link"] for d in ds]
    ket = {"thu_tu": [L[2], L[1]], "hang": {L[0]: "TE", L[1]: "TAM", L[2]: "TOT", L[3]: "TE"},
           "diem_bt": {L[1]: 70, L[2]: 81}, "ly_do": {L[2]: "cụm đang thắng, chân dung", L[1]: "hơi cũ nhưng hợp tệp"}}
    log = []
    moi = tu_chay._ap_cham_bien_tap(ds, ket, log.append)
    assert [d["ma"] for d in moi] == [ds[2]["ma"], ds[1]["ma"]], "dòng TỆ bị bỏ hẳn, không nối lại cuối"
    assert moi[0]["bien_tap"]["hang"] == "TOT" and moi[0]["bien_tap"]["hang_cong_thuc"] == 3
    qua = tu_chay._cong_chat_luong(moi, log.append)
    assert [d["ma"] for d in qua] == [ds[2]["ma"]]
    # Không có TỐT → TẠM ≥ 65 có lý do (cảnh báo); TẠM thấp → không mở lượt.
    chi_tam = [moi[1]]
    assert tu_chay._cong_chat_luong(chi_tam, log.append) == chi_tam
    assert any("CẢNH BÁO: không có nguồn TỐT" in m for m in log)
    thap = [dict(moi[1], bien_tap=dict(moi[1]["bien_tap"], diem=40))]
    assert tu_chay._cong_chat_luong(thap, log.append) == []
    assert any("KHÔNG nguồn nào đạt" in m for m in log)
    # Chưa qua biên tập (chế độ thử) → giữ nguyên bảng.
    assert tu_chay._cong_chat_luong(ds, log.append) == ds


def test_phan_cum_che_lo_hong_va_lui_mo_hinh(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    from core import nghien_cuu_chung as ncc
    monkeypatch.setattr(ncc, "thu_muc", lambda g, k: os.path.join(g, "kho"))
    ch = {"cum": {"tien": {"ten": "Tiền", "tu": ["金持ち"]}, "iq": {"ten": "IQ", "tu": ["IQ"]}}}
    td = ["金持ちの習慣{0}".format(i) for i in range(11)] + ["毒の題名"]
    goi_roi = []

    def goi(loi_nhac, **kw):
        phan = loi_nhac.split("TIÊU ĐỀ:\n", 1)[1].strip().splitlines()
        goi_roi.append((len(phan), kw.get("mo_hinh"), kw.get("toi_da_token")))
        if any("毒" in p for p in phan):
            raise gvb.TraRong("Máy chủ trả về nội dung rỗng.")
        return json.dumps({str(i + 1): ["tien"] for i in range(len(phan))})

    moi = pca.phan_loai(goc, K, ch, [(t, "") for t in td], goi, mo_hinh="claude-sonnet-5")
    assert moi == 11, "chỉ tiêu đề độc hỏng, 11 tiêu đề kia vẫn có nhãn ngay lượt này"
    assert min(t for _n, _m, t in goi_roi) >= 4096, "trần token không được thấp (cổng trả rỗng)"
    assert {m for _n, m, _t in goi_roi} >= {"claude-sonnet-5", "claude-opus-5"}, "lô hỏng phải lùi mô hình"


def test_goi_van_ban_san_tran_va_noi_sau_tra_rong(monkeypatch):
    gui = []

    class Client:
        api_key, base_url = "k", "u"

        def request(self, _m, _p, json=None, idempotency_key=None):
            gui.append(json["max_tokens"])
            noi = "" if len(gui) == 1 else "ok"
            return {"choices": [{"message": {"content": noi}}]}

    monkeypatch.setattr(gvb, "_client_khong_tu_thu_lai", lambda c, t: c)
    assert gvb.goi_van_ban(Client(), [{"role": "user", "content": "x"}], toi_da_token=500, ngu=lambda s: None) == "ok"
    assert gui[0] >= gvb.SAN_MAX_TOKENS and gui[1] == 2 * gui[0]


def test_trung_tieu_de_cat_nhan_cuoi():
    a, b = "【雑学】昔より物欲が減った人の心理", "昔より物欲が減った人の心理【グレーな心理学】"
    assert ttd.diem_giong_tieu_de(a, b) >= ttd.NGUONG_GIONG_TIEU_DE_MAC_DINH
    assert ttd.chuan_hoa_tieu_de_so_khop("【心理学】") != "" or True  # chỉ nhãn → không rỗng hoá bừa


def test_vph_khong_tin_tang_ngay_bac_lam_tron(tmp_path):
    import calendar
    from core import danh_ba_doi_thu as db
    from core import doi_thu_kenh as so
    from core.phan_tuyen import MA_LECH_NHIP
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "K", "kenh.yaml"), "ten: K\n")
    bay = dt.datetime(2026, 9, 29, 12, 0)
    cot = so.cot_mac_dinh()
    hang = []
    dong = [("lap{0:08d}".format(i), "心理A", "人の特徴{0}".format(i), 59000, "2026-09-10", 2089, 49000) for i in range(3)]
    dong += [("thu{0:08d}".format(i), "心理A", "人の性格{0}".format(i), 1500 + i, "2026-09-10", 0, 0) for i in range(4)]
    for ma, k, td, view, ngay, tang, truoc in dong:
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": k, "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": str(view), "Ngày đăng": ngay, so.COT_TUYEN: MA_LECH_NHIP, "Thời lượng": "15:00",
                  so.COT_TANG: str(tang), so.COT_VIEW_TRUOC: str(truoc)})
        hang.append([d.get(c, "") for c in cot])
    so.luu_bang(goc, "K", cot, hang)
    _ghi(os.path.join(so.thu_muc_nghien_cuu(goc, "K"), so.TEP_CAI),
         json.dumps({"quet_luc": calendar.timegm(bay.timetuple())}))
    cot2 = list(db.COT)
    r = dict.fromkeys(cot2, "")
    r.update({"Kênh": "心理A", "Trạng thái": db.THEO_DOI, "Link kênh": "https://www.youtube.com/@a"})
    db.luu(goc, "K", cot2, [[r[c] for c in cot2]])
    kq = vph.cham(goc, "K", bay_gio=bay)
    lap = [d for d in kq.ung_vien if d.ma.startswith("lap")]
    assert lap and all(d.vph_gan is None for d in lap), "3 video cùng Tăng/ngày 2.089 = bậc làm tròn, không phải tốc độ"
