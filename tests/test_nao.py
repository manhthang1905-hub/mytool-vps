"""Tests `core/nao.py` — CLI bộ não: giới hạn, hiệu lực vào dây chuyền, quyền theo thành tích, lệnh `claude` của phiên.
Không mạng, không chạy `claude` thật; mọi thứ trong `tmp_path`."""

import datetime as dt
import json
import os

from core import nao, tu_hoc

HOM_NAY = dt.datetime(2026, 10, 3, 4, 10)
NGAY_KIEM = "2026-10-10"


def _goc(tmp_path):
    for ma in ("KA", "KB"):
        d = tmp_path / "CHANNEL" / ma
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text('nhom: "n1"\n', encoding="utf-8")
    return str(tmp_path)


def _chay(goc, *argv, bay_gio=HOM_NAY):
    """`(mã thoát, hành động mới nhất hoặc None)` — qua đúng đường CLI (parse → chay_lenh)."""
    argv = list(argv)
    if "--ly-do" not in argv and (argv[0] in ("thu", "tranh", "de-xuat") or (argv[0] == "bai-hoc" and "them" in argv)):
        argv += ["--ly-do", "video X có hiển thị 48h = 120, CTR 3,1% so với trung vị 300"]
    try:
        nao.chay_lenh(nao._parser().parse_args(argv), goc, bay_gio)
        return 0
    except nao.TuChoi as loi:
        return str(loi)


def _thu(goc, kenh="KA", truc="cum", gt="x", n="2", *them):
    return _chay(goc, "thu", "--kenh", kenh, "--truc", truc, "--gia-tri", gt, "--so-video", n,
                 "--du-doan", "2 video kế của kênh thuộc cụm x có hiển thị 48h >= trung vị", "--kiem-ngay", NGAY_KIEM, *them)


def test_gioi_han_tu_choi_dung(tmp_path):
    if True:
        goc = _goc(tmp_path)
        # thiếu dự đoán / ngày kiểm
        assert "du-doan" in _chay(goc, "thu", "--kenh", "KA", "--truc", "cum", "--gia-tri", "x", "--so-video", "1",
                                  "--kiem-ngay", NGAY_KIEM)
        assert "kiem-ngay" in _chay(goc, "thu", "--kenh", "KA", "--truc", "cum", "--gia-tri", "x", "--so-video", "1",
                                    "--du-doan", "một dự đoán đủ dài để đo", "--kiem-ngay", "2026-10-01")
        # quá 2 video
        assert "so-video" in _thu(goc, n="3")
        # kênh không tồn tại
        assert "không tồn tại" in _thu(goc, kenh="ZZ")
        # tranh quá 14 ngày
        assert "ngay" in _chay(goc, "tranh", "--kenh", "KA", "--truc", "cum", "--gia-tri", "y", "--ngay", "15",
                               "--du-doan", "một dự đoán đủ dài để đo", "--kiem-ngay", NGAY_KIEM)
        # trục lạ
        assert "chưa được dây chuyền đọc" in _thu(goc, truc="mau_sac")
        assert "chưa được dây chuyền đọc" in _thu(goc, truc="cong_thuc", gt="vph")
        assert "ly-do" in _chay(goc, "thu", "--kenh", "KA", "--truc", "cum", "--gia-tri", "x", "--so-video", "1", "--ly-do", "ngắn",
                                "--du-doan", "một dự đoán đủ dài để đo", "--kiem-ngay", NGAY_KIEM)
        assert nao.doc_hanh_dong(goc) == []   # từ chối thì không ghi gì


def test_moi_kenh_truc_mot_thu_va_toi_da_ba_moi_ngay(tmp_path):
    goc = _goc(tmp_path)
    assert _thu(goc) == 0
    assert "đang mở" in _thu(goc, gt="z")                      # (KA, cum) đã có một thử mở
    assert _thu(goc, kenh="KB") == 0                           # kênh khác thì được
    assert _thu(goc, truc="kieu_tieu_de", gt="cau_hoi") == 0   # trục khác thì được
    assert "3/3" in _thu(goc, kenh="KB", truc="hook", gt="canh_bao")   # hành động thứ 4 trong ngày
    assert len(nao.doc_hanh_dong(goc)) == 3
    # sang ngày sau thì được lại
    assert _chay(goc, "tranh", "--kenh", "KA", "--truc", "cum", "--gia-tri", "q", "--ngay", "3",
                 "--du-doan", "một dự đoán đủ dài để đo", "--kiem-ngay", "2026-10-12",
                 bay_gio=HOM_NAY + dt.timedelta(days=1)) == 0


def test_thu_lam_rut_tra_1_va_tru_luot(tmp_path):
    goc = _goc(tmp_path)
    assert _thu(goc, gt="Tình Cảm", n="2") == 0
    r = tu_hoc.rut(goc, "KA", "cum", ["Tình Cảm", "khac"])
    assert r["Tình Cảm"] == 1.0 and r["khac"] < 1.0
    assert nao.he_so_cum(goc, "KA", "tình cảm", 1.1) == nao.HE_SO_CUM_THU
    assert nao.he_so_cum(goc, "KA", "khac", 1.1) == 1.1
    assert nao.he_so_cum(goc, "KB", "tình cảm", 1.1) == 1.1    # kênh khác không bị ảnh hưởng
    tu_hoc.ghi_van(goc, "KA", "KA-0001", {"cum": "Tình Cảm"})
    hd = nao.doc_hanh_dong(goc)[0]
    assert hd["tham_so"]["da_dung"] == 1 and hd["trang_thai"] == "mo"
    tu_hoc.ghi_van(goc, "KA", "KA-0001", {"cum": "Tình Cảm"})       # ghi lại CÙNG ván: không trừ thêm
    assert nao.doc_hanh_dong(goc)[0]["tham_so"]["da_dung"] == 1
    tu_hoc.ghi_van(goc, "KA", "KA-0002", {"cum": "khac"})           # giá trị khác: không trừ
    assert nao.doc_hanh_dong(goc)[0]["tham_so"]["da_dung"] == 1
    tu_hoc.ghi_van(goc, "KA", "KA-0003", {"cum": "Tình Cảm"})
    hd = nao.doc_hanh_dong(goc)[0]
    assert hd["tham_so"]["da_dung"] == 2 and hd["trang_thai"] == "xong" and hd["cham"] is None   # hết lượt, chờ chấm
    assert tu_hoc.rut(goc, "KA", "cum", ["Tình Cảm"])["Tình Cảm"] < 1.0                          # hết hiệu lực
    # thử một ván có nhãn khác trục không động tới thử đã xong
    assert nao.tru_luot(goc, "KA", {"cum": "Tình Cảm"}) == 0


def test_tranh_tra_0_toi_het_han(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    goc_hl = nao.hieu_luc   # `rut` đọc giờ thật — ghim về HOM_NAY để test không phụ thuộc ngày chạy
    monkeypatch.setattr(nao, "hieu_luc", lambda g, k, t, bay_gio=None: goc_hl(g, k, t, bay_gio or HOM_NAY))
    assert _chay(goc, "tranh", "--kenh", "KA", "--truc", "kieu_tieu_de", "--gia-tri", "canh_bao", "--ngay", "2",
                 "--du-doan", "tiêu đề cảnh báo không còn lọt 2 video tới", "--kiem-ngay", NGAY_KIEM) == 0
    r = tu_hoc.rut(goc, "KA", "kieu_tieu_de", ["canh_bao", "cau_hoi"])
    assert r["canh_bao"] == 0.0 and r["cau_hoi"] > 0
    assert nao.hieu_luc(goc, "KA", "kieu_tieu_de", HOM_NAY + dt.timedelta(days=1)) == {"canh_bao": 0.0}
    assert nao.hieu_luc(goc, "KA", "kieu_tieu_de", HOM_NAY + dt.timedelta(days=3)) == {}    # quá hạn
    # `thu` đúng giá trị đang bị `tranh` thì từ chối (và ngược lại)
    assert "tranh" in _thu(goc, truc="kieu_tieu_de", gt="canh_bao", n="1")


def test_huy(tmp_path):
    goc = _goc(tmp_path)
    assert _thu(goc, gt="x") == 0
    assert tu_hoc.rut(goc, "KA", "cum", ["x"])["x"] == 1.0
    hd_id = nao.doc_hanh_dong(goc)[0]["id"]
    assert _chay(goc, "huy", hd_id) == 0
    assert nao.doc_hanh_dong(goc)[0]["trang_thai"] == "huy"
    assert tu_hoc.rut(goc, "KA", "cum", ["x"])["x"] < 1.0
    assert "chỉ huỷ được" in _chay(goc, "huy", hd_id)              # đã huỷ rồi
    assert "không có" in _chay(goc, "huy", "n999")
    assert _thu(goc, gt="x") == 0                                  # huỷ rồi thì mở lại thử được


def test_cham_va_quyen_theo_thanh_tich(tmp_path):
    goc = _goc(tmp_path)
    assert _thu(goc) == 0
    hd_id = nao.doc_hanh_dong(goc)[0]["id"]
    assert "lý do" in _chay(goc, "cham", hd_id, "dung", " ")
    assert _chay(goc, "cham", hd_id, "sai", "hiển thị 48h của 2 video = 120 và 90 < trung vị 300") == 0
    d = nao.doc_hanh_dong(goc)[0]
    assert d["cham"] == "sai" and d["trang_thai"] == "xong" and "trung vị" in d["ghi_chu_cham"]
    assert nao.han_muc_ngay(nao.doc_hanh_dong(goc)) == 3           # mới 1 hành động chấm: chưa co quyền
    # 10 hành động đã chấm, đúng 4/10 < 50% → còn 1 hành động mỗi ngày
    ds = [{"id": "n{0:03d}".format(i), "luc": "2026-09-0{0}T05:00:00".format(1 + i % 9), "lenh": "de-xuat",
           "tham_so": {"noi_dung": "x"}, "trang_thai": "xong", "cham": "dung" if i < 4 else "sai"} for i in range(10)]
    nao.ghi_hanh_dong(goc, ds)
    assert nao.ti_le_dung(ds) == (4, 10) and nao.han_muc_ngay(ds) == 1
    assert _thu(goc, kenh="KB") == 0
    assert "1/1" in _thu(goc, kenh="KB", truc="hook", gt="canh_bao")
    # 6/10 đúng thì giữ quyền đầy đủ
    nao.ghi_hanh_dong(goc, [dict(d, cham="dung" if i < 6 else "sai") for i, d in enumerate(ds)])
    assert nao.han_muc_ngay(nao.doc_hanh_dong(goc)) == 3
    # cộng/trừ bài học không tính vào tỉ lệ
    assert nao.ti_le_dung([{"cham": "sai", "khong_tinh": True}]) == (0, 0)


def test_de_xuat_hien_trong_viec_cua_ban(tmp_path):
    from core import bang_dieu_khien as bdk

    goc = _goc(tmp_path)
    assert _chay(goc, "de-xuat", "Mở kênh TL5 cho cụm tiền bạc", "--du-doan", "chủ duyệt thì kênh mới có 100 sub sau 30 ngày",
                 "--kiem-ngay", NGAY_KIEM) == 0
    viec = bdk.viec_cua_ban(goc, anh={"kenh": []}, bay_gio=HOM_NAY)
    mine = [v for v in viec if v["khoa"].startswith("nao:")]
    assert len(mine) == 1 and "Mở kênh TL5" in mine[0]["chu"] and mine[0]["xong_tay"]
    bdk.danh_dau_xong(goc, mine[0]["khoa"])                         # chủ bấm "đã xử lý" → biến mất
    assert not [v for v in bdk.viec_cua_ban(goc, anh={"kenh": []}, bay_gio=HOM_NAY) if v["khoa"].startswith("nao:")]


def test_de_xuat_mo_qua_7_ngay_tu_dong_het_han_va_nao_thay_trong_xem(tmp_path):
    from core import bang_dieu_khien as bdk

    goc = _goc(tmp_path)
    assert _chay(goc, "de-xuat", "Mở kênh TL5 cho cụm tiền bạc", "--du-doan", "chủ duyệt thì kênh mới có 100 sub sau 30 ngày",
                 "--kiem-ngay", NGAY_KIEM) == 0
    # đúng 7 ngày: còn mở; thuần đọc không ghi
    bay7 = HOM_NAY + dt.timedelta(days=7)
    assert nao.don_het_han(goc, bay_gio=bay7) is False
    assert nao.doc_hanh_dong(goc)[0]["trang_thai"] == "mo"
    # sang ngày thứ 8: hiện cho chủ biến mất ngay (kể cả trước khi dọn ghi đĩa)
    bay8 = HOM_NAY + dt.timedelta(days=8)
    assert not [v for v in bdk.viec_cua_ban(goc, anh={"kenh": []}, bay_gio=bay8) if v["khoa"].startswith("nao:")]
    assert nao.doc_hanh_dong(goc)[0]["trang_thai"] == "mo", "viec_cua_ban chỉ đọc"
    # dọn ghi đĩa: trạng thái het_han, và `xem` báo để bộ não tự quyết lại
    assert nao.don_het_han(goc, bay_gio=bay8) is True
    hd = nao.doc_hanh_dong(goc)[0]
    assert hd["trang_thai"] == "het_han" and hd["het_han_luc"] == "2026-10-11"
    assert nao.viec_de_xuat(goc, bay8) == []
    bc = nao.bao_cao(goc, bay8)
    assert "ĐỀ XUẤT CỦA NÃO HẾT HẠN" in bc and "Mở kênh TL5" in bc and "ĐÃ ĐÓNG" in bc
    assert nao.don_het_han(goc, bay_gio=bay8) is False, "chạy lại không đổi gì"
    # đề xuất mới (hôm nay) vẫn hiện bình thường
    assert _chay(goc, "de-xuat", "Đổi giờ đăng TL2", "--du-doan", "giờ mới tăng hiển thị 48h của kênh TL2", "--kiem-ngay",
                 "2026-10-18", bay_gio=bay8) == 0
    assert [d["khoa"] for d in nao.viec_de_xuat(goc, bay8)] == ["nao:n002"]


def test_xem_in_muc_giam_doc_kenh_nho_xem(tmp_path):
    from core.giam_doc import ghi_viec_may

    goc = _goc(tmp_path)
    assert "(không có)" in nao.bao_cao(goc, HOM_NAY).split("GIÁM ĐỐC KÊNH NHỜ XEM")[1]
    assert ghi_viec_may(goc, "KA", "Mở YouTube Studio xem video X có hiển thị 48h thấp không", "may", bay_gio=HOM_NAY)
    bc = nao.bao_cao(goc, HOM_NAY)
    assert "GIÁM ĐỐC KÊNH NHỜ XEM" in bc and "[KA] Mở YouTube Studio xem video X" in bc


def test_uu_tien_nguon(tmp_path):
    goc = _goc(tmp_path)
    assert "link" in _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "abc", "--ly-do", "view 120k trong 5 ngày, đúng cụm tiền bạc",
                           "--du-doan", "một dự đoán đủ dài để đo", "--kiem-ngay", NGAY_KIEM)
    assert _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "https://youtu.be/AAAAAAAAAAA", "--ly-do",
                 "view 120k trong 5 ngày, đúng cụm tiền bạc", "--du-doan", "video này vào top 3 hiển thị 48h của kênh",
                 "--kiem-ngay", NGAY_KIEM) == 0
    ds = [{"ma": "m1", "link": "https://www.youtube.com/watch?v=BBBBBBBBBBB", "diem": 50},
          {"ma": "m2", "link": "https://www.youtube.com/watch?v=AAAAAAAAAAA&t=3", "diem": 10}]
    ra = nao.ap_uu_tien(goc, "KA", ds)
    assert [u["ma"] for u in ra] == ["m2", "m1"] and ra[0]["diem"] > 1000 and ds[1]["diem"] == 10   # không đổi bản gốc
    assert nao.ap_uu_tien(goc, "KB", ds) == ds                         # kênh khác: không đổi
    assert "Bộ não đề cử" in nao.dong_de_cu(goc, "KA")[0] and "view 120k" in nao.dong_de_cu(goc, "KA")[0]
    assert ra[0]["ep_chon"] is True and ra[0]["de_cu_nao"] == "n001"
    # 12/10/2026: CÓ MẶT trong bảng mà lượt chọn nguồn khác → KHÔNG xong (chỉ đếm bỏ qua).
    assert nao.dung_xong_de_cu(goc, "KA") == 1
    assert nao.dong_de_cu(goc, "KA")
    # Được chọn → đang sản xuất, vẫn mở; chỉ gói BÀN GIAO dùng đúng link mới đóng `xong`.
    nao.ap_uu_tien(goc, "KA", ds)
    nao.dung_xong_de_cu(goc, "KA", chon="https://youtu.be/AAAAAAAAAAA")
    d = [x for x in nao.doc_hanh_dong(goc) if x.get("lenh") == "uu-tien-nguon"][0]
    assert d["trang_thai"] == "mo" and d["tham_so"]["chon_luc"]
    assert nao.ghi_ban_giao(goc, "KA", "KA-0007", "https://youtu.be/BBBBBBBBBBB") == []    # link khác: không đóng
    assert nao.ghi_ban_giao(goc, "KA", "KA-0007", "https://www.youtube.com/watch?v=AAAAAAAAAAA") == ["n001"]
    d = [x for x in nao.doc_hanh_dong(goc) if x.get("lenh") == "uu-tien-nguon"][0]
    assert d["trang_thai"] == "xong" and d["tham_so"]["goi"] == ["KA-0007"] and not d.get("khong_tinh")
    assert "→ KA-0007" in nao.dong_hanh_dong(d)
    assert nao.ap_uu_tien(goc, "KA", ds) == ds and nao.dong_de_cu(goc, "KA") == []


def test_de_cu_bi_bo_qua_3_luot_thi_dong_khong_tinh(tmp_path):
    goc = _goc(tmp_path)
    assert _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "https://youtu.be/DDDDDDDDDDD", "--ly-do",
                 "view 120k trong 5 ngày, đúng cụm tiền bạc", "--du-doan", "video này vào top 3 hiển thị 48h của kênh",
                 "--kiem-ngay", NGAY_KIEM) == 0
    ds = [{"ma": "m1", "link": "https://www.youtube.com/watch?v=DDDDDDDDDDD", "diem": 50}]
    for _ in range(nao.DE_CU_VANG_TOI_DA):
        nao.ap_uu_tien(goc, "KA", ds)
        nao.dung_xong_de_cu(goc, "KA", chon="https://youtu.be/EEEEEEEEEEE")
    d = [x for x in nao.doc_hanh_dong(goc) if x.get("lenh") == "uu-tien-nguon"][0]
    assert d["trang_thai"] == "xong" and d.get("khong_tinh") and "không được chọn" in d["ghi_chu_cham"]
    assert not d["tham_so"].get("goi")


def test_xem_in_chuoi_de_cu_goi_ket_qua(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    assert _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "https://youtu.be/FFFFFFFFFFF", "--ly-do",
                 "view 120k trong 5 ngày, đúng cụm tiền bạc", "--du-doan", "video này vào top 3 hiển thị 48h của kênh",
                 "--kiem-ngay", NGAY_KIEM) == 0
    nao.ghi_ban_giao(goc, "KA", "KA-0009", "https://youtu.be/FFFFFFFFFFF")
    monkeypatch.setattr(nao, "ket_qua_goi", lambda _g, _k, goi: ["{0}: kết quả THẮNG (phân vị 90 @100h)".format(g)
                                                                for g in goi or []])
    bc = "\n".join(nao.bao_cao_hanh_dong(goc))
    assert "→ KA-0009: kết quả THẮNG" in bc and "n001 →" in bc


def test_de_cu_vang_mat_khoi_bang_khong_bi_tinh_la_da_dung(tmp_path):
    """04/10: đề cử mà link KHÔNG có trong danh sách ứng viên thì không `xong` ngay; vắng 3 lượt → đóng, không tính."""
    goc = _goc(tmp_path)
    assert _chay(goc, "uu-tien-nguon", "--kenh", "KA", "--link", "https://youtu.be/CCCCCCCCCCC", "--ly-do",
                 "view 120k trong 5 ngày, đúng cụm tiền bạc", "--du-doan", "video này vào top 3 hiển thị 48h của kênh",
                 "--kiem-ngay", NGAY_KIEM) == 0
    ds = [{"ma": "m1", "link": "https://www.youtube.com/watch?v=BBBBBBBBBBB", "diem": 50}]
    for _ in range(nao.DE_CU_VANG_TOI_DA - 1):
        assert nao.ap_uu_tien(goc, "KA", ds) == ds
        nao.dung_xong_de_cu(goc, "KA")
        assert nao.dong_de_cu(goc, "KA")                                  # vẫn mở
    nao.ap_uu_tien(goc, "KA", ds)
    nao.dung_xong_de_cu(goc, "KA")
    d = [x for x in nao.doc_hanh_dong(goc) if x.get("lenh") == "uu-tien-nguon"][0]
    assert d["trang_thai"] == "xong" and d.get("khong_tinh") and "không vào danh sách" in d["ghi_chu_cham"]


def _de_cu(goc, ma, kenh="KA", bay_gio=HOM_NAY):
    assert _chay(goc, "uu-tien-nguon", "--kenh", kenh, "--link", "https://youtu.be/" + ma, "--ly-do",
                 "view 120k trong 5 ngày, đúng cụm tiền bạc", "--du-doan", "video này vào top 3 hiển thị 48h của kênh",
                 "--kiem-ngay", (bay_gio + dt.timedelta(days=7)).strftime("%Y-%m-%d"), bay_gio=bay_gio) == 0
    return nao.doc_hanh_dong(goc)[-1]["id"]


def _hd(goc, id_):
    return next(x for x in nao.doc_hanh_dong(goc) if x["id"] == id_)


def test_de_cu_khong_hop_le_dong_ngay_la_khong_thuc_hien(tmp_path):
    """20/10/2026: lượt chọn thật phát hiện nguồn không hợp lệ (đã làm / anh em giữ / cổng cứng / phủ quyết / trùng ý)
    → đề cử đóng NGAY là KHÔNG THỰC HIỆN ĐƯỢC kèm lý do, không đợi 3 lượt, không bao giờ "sai"."""
    goc = _goc(tmp_path)
    a = _de_cu(goc, "AAAAAAAAAAA")
    nao.ghi_khong_duoc("KA", a, "nguồn đã làm / đang được kênh anh em giữ")
    nao.ghi_khong_duoc("KB", a, "kênh khác — không đụng")
    assert nao.dung_xong_de_cu(goc, "KA", chon="https://youtu.be/ZZZZZZZZZZZ") == 1
    d = _hd(goc, a)
    assert (d["trang_thai"], d["cham"], d["khong_tinh"]) == ("xong", nao.CHAM_KHONG_THUC_HIEN, True)
    assert d["ghi_chu_cham"] == "không thực hiện được: nguồn đã làm / đang được kênh anh em giữ"
    assert nao.ti_le_dung(nao.doc_hanh_dong(goc)) == (0, 0) and "KB" in nao._DE_CU_KHONG_DUOC


def test_nhieu_de_cu_giu_cho_lan_luot_va_chon_tay_khong_tinh_vang(tmp_path):
    """20/10/2026: kênh có nhiều đề cử → lượt này tiêu đề cử cũ nhất (đầu bảng), các đề cử còn lại GIỮ CHỖ (không đếm
    vắng / bỏ qua); người chốt tay cũng không làm đề cử mất lượt."""
    goc = _goc(tmp_path)
    a = _de_cu(goc, "AAAAAAAAAAA", bay_gio=HOM_NAY)
    b = _de_cu(goc, "BBBBBBBBBBB", bay_gio=HOM_NAY + dt.timedelta(minutes=5))
    ds = [{"ma": "m0", "link": "https://youtu.be/CCCCCCCCCCC", "diem": 90},
          {"ma": "mb", "link": "https://youtu.be/BBBBBBBBBBB", "diem": 50},
          {"ma": "ma", "link": "https://youtu.be/AAAAAAAAAAA", "diem": 10}]
    ra = nao.ap_uu_tien(goc, "KA", ds)
    assert [u["ma"] for u in ra] == ["ma", "mb", "m0"] and "_giu_cho" not in ra[0]      # cũ nhất trước
    nao.dung_xong_de_cu(goc, "KA", chon=ra[0]["link"])
    assert _hd(goc, a)["tham_so"]["chon_luc"] and _hd(goc, b)["trang_thai"] == "mo"
    assert _hd(goc, b)["tham_so"].get("giu_cho_luc") and not _hd(goc, b)["tham_so"].get("lan_bo_qua")
    for _ in range(nao.DE_CU_VANG_TOI_DA + 1):                                         # chốt tay nhiều lượt
        nao.ap_uu_tien(goc, "KA", ds)
        nao.dung_xong_de_cu(goc, "KA", chon="https://youtu.be/CCCCCCCCCCC", chon_tay=True)
    d = _hd(goc, b)
    assert d["trang_thai"] == "mo" and not d["tham_so"].get("lan_bo_qua") and not d["tham_so"].get("lan_vang")


def test_cham_de_cu_chua_ra_goi_thanh_khong_thuc_hien_va_ti_le_chi_tinh_da_lam(tmp_path):
    goc = _goc(tmp_path)
    a = _de_cu(goc, "AAAAAAAAAAA")
    assert _chay(goc, "cham", a, "sai", "chưa có video nào làm từ đúng link này") == 0
    d = _hd(goc, a)
    assert d["cham"] == nao.CHAM_KHONG_THUC_HIEN and d["khong_tinh"] and "não định chấm sai" in d["ghi_chu_cham"]
    b = _de_cu(goc, "BBBBBBBBBBB")
    nao.ghi_ban_giao(goc, "KA", "KA-0001", "https://youtu.be/BBBBBBBBBBB")
    assert _chay(goc, "cham", b, "dung", "phân vị 70 @96h ≥ 50") == 0 and _hd(goc, b)["cham"] == "dung"
    # dòng CŨ: chấm "sai" khi chưa ra gói → bỏ khi tính (không sửa sổ); dòng cũ nêu đúng video thật → vẫn tính
    cu = [{"id": "x1", "lenh": "uu-tien-nguon", "tham_so": {"kenh": "KA"}, "trang_thai": "xong", "cham": "sai",
           "ghi_chu_cham": "Hạn 14/10: không gói bàn giao nào làm từ link"},
          {"id": "x2", "lenh": "uu-tien-nguon", "tham_so": {"kenh": "KA"}, "trang_thai": "xong", "cham": "sai",
           "ghi_chu_cham": "video KA FAKEvid0011 @47h chỉ có 1.244 hiển thị < 6.000"}]
    ds = nao.doc_hanh_dong(goc) + cu
    assert nao.ti_le_dung(ds) == (1, 2) and [nao.da_thuc_hien(x) for x in cu] == [False, True]


def test_ti_le_dung_bo_kenh_tra_kho(tmp_path):
    goc = _goc(tmp_path)
    with open(os.path.join(goc, "CHANNEL", "KB", "kenh.yaml"), "a", encoding="utf-8") as tep:
        tep.write("tra_kho: 2026-10-19\n")
    ds = [{"id": "t1", "lenh": "thu", "tham_so": {"kenh": "KA"}, "cham": "dung"},
          {"id": "t2", "lenh": "thu", "tham_so": {"kenh": "KB"}, "cham": "sai"}]
    assert nao.ti_le_dung(ds) == (1, 2) and nao.ti_le_dung(ds, goc) == (1, 1)


def test_chuyen_doi_ep_chon_va_so_ngay(tmp_path):
    goc = _goc(tmp_path)
    bg = dt.datetime(2026, 10, 20, 7, 0)
    a = _de_cu(goc, "AAAAAAAAAAA", bay_gio=bg - dt.timedelta(days=1))
    b = _de_cu(goc, "BBBBBBBBBBB", bay_gio=bg - dt.timedelta(days=1))
    _de_cu(goc, "CCCCCCCCCCC", bay_gio=bg - dt.timedelta(days=1))
    nao.ghi_ban_giao(goc, "KA", "KA-0002", "https://youtu.be/AAAAAAAAAAA")
    nao.ghi_khong_duoc("KA", b, "vướng cổng chất lượng “lạc ngách”")
    nao.dung_xong_de_cu(goc, "KA", chon="https://youtu.be/ZZZZZZZZZZZ", bay_gio=bg)
    cd = nao.chuyen_doi_ep_chon(goc, 14, bay_gio=bg)
    assert (cd["tao"], cd["ra_goi"], cd["khong_thuc_hien"], cd["dang_mo"], cd["ti_le"]) == (3, 1, 1, 1, 0.5)
    assert "vướng cổng chất lượng “…”" in cd["ly_do"] and "ra gói 1 (50%" in nao.dong_chuyen_doi(cd)
    assert "Ép chọn → ra gói" in "\n".join(nao.bao_cao_hanh_dong(goc, bg))
    for _ in range(2):                                                      # một dòng mỗi ngày (ghi lại thì thay)
        nao.ghi_chuyen_doi(goc, bg)
    with open(os.path.join(nao.duong_nao(goc), "nhat-ky", nao.TEP_CHUYEN_DOI), encoding="utf-8") as tep:
        dong = [json.loads(x) for x in tep.read().splitlines() if x.strip()]
    assert len(dong) == 1 and dong[0]["hom_qua"] == {"tao": 3, "ra_goi": 1} and dong[0]["cua_so_14"]["ra_goi"] == 1


def test_tu_chay_ghi_de_cu_bi_bien_tap_loai(tmp_path):
    from core import tu_chay

    nao._DE_CU_KHONG_DUOC.clear()
    truoc = [{"ma": "AAAAAAAAAAA", "ep_chon": True, "de_cu_nao": "n007"}, {"ma": "BBBBBBBBBBB"}]
    tu_chay._ghi_ep_chon_bi_loai("KA", truoc, [truoc[1]], {"ly_do": {"AAAAAAAAAAA": "trùng ý video đã làm X"}})
    assert nao._DE_CU_KHONG_DUOC["KA"]["n007"].startswith("biên tập AI phủ quyết: trùng ý")
    nao._DE_CU_KHONG_DUOC.clear()


def test_bai_hoc_cong_tru_nguon_nao(tmp_path):
    from core.giam_doc import kham_nghiem as kn

    goc = _goc(tmp_path)
    gd = tmp_path / "CHANNEL" / "KA" / "giam-doc"
    gd.mkdir()
    luc = HOM_NAY.isoformat()
    dong = {"truc": "hook", "gia_tri": "canh_bao", "huong": "+", "cum": "", "cau": "hook cảnh báo giữ chân 41% ở 30s",
            "khoa": "hook|canh_bao|+|", "video_id": "v1", "moc": "48h", "so_dan": [], "bong": False, "luc": luc}
    (gd / "bai-hoc.jsonl").write_text(json.dumps(dong, ensure_ascii=False) + "\n", encoding="utf-8")
    id_bai = kn.doc_bai_hoc(goc, "KA", bay_gio=HOM_NAY)[0]["id"]
    assert _chay(goc, "bai-hoc", "--kenh", "KA", "cong", id_bai) == 0
    b = kn.doc_bai_hoc(goc, "KA", bay_gio=HOM_NAY)[0]
    assert b["cong"] == 2
    assert any(json.loads(x).get("nguon") == "nao" for x in (gd / "bai-hoc.jsonl").read_text(encoding="utf-8").splitlines())
    assert "hôm nay đã" in _chay(goc, "bai-hoc", "--kenh", "KA", "cong", id_bai)     # cùng ngày không cộng hai lần
    assert "không có bài" in _chay(goc, "bai-hoc", "--kenh", "KA", "tru", "bffffff")
    assert "chữ số" in _chay(goc, "bai-hoc", "--kenh", "KA", "them", "một bài học không có số",
                             "--du-doan", "một dự đoán đủ dài để đo", "--kiem-ngay", NGAY_KIEM)
    # cộng/trừ không tính vào hạn mức ngày
    assert all(d.get("khong_tinh") for d in nao.doc_hanh_dong(goc))


def test_lenh_phien_allowedtools_va_khong_bypass(tmp_path):
    lenh = nao.lenh_phien("C:/x/claude.exe", str(tmp_path))
    chuoi = " ".join(lenh)
    assert "bypassPermissions" not in chuoi and "dangerously" not in chuoi
    assert lenh[lenh.index("--permission-mode") + 1] == "dontAsk"
    cho = lenh[lenh.index("--allowedTools") + 1].split(",")
    assert {"Read", "Grep", "Glob"} <= set(cho)
    assert "Bash(python -m core.nao *)" in cho
    assert not [c for c in cho if c.startswith("Bash") and "core.nao" not in c]          # Bash chỉ cho core.nao
    ghi = [c for c in cho if c.startswith(("Write", "Edit"))]
    assert "Write" not in cho and "Edit" not in cho                                     # không có quyền ghi trần
    goc_mau = nao._mau(str(tmp_path), "nao")
    assert goc_mau.startswith("//") and len(ghi) == 6
    assert all(c.split("(")[1].startswith((goc_mau + "/tri-nho/", goc_mau + "/nhat-ky/", goc_mau + "/ky-nang/")) for c in ghi)
    cam = lenh[lenh.index("--disallowedTools") + 1].split(",")
    assert "Write({0}/hanh-dong.json)".format(goc_mau) in cam and "WebFetch" in cam
    assert lenh[lenh.index("--add-dir") + 1] == str(tmp_path)
    assert lenh[lenh.index("--max-turns") + 1] == "40"
    assert lenh[lenh.index("--model") + 1] == "claude-fable-5"
    assert "--print" in lenh and lenh[-1] != nao.CAU_HOI_PHIEN       # lời nhắc đi qua stdin, không nằm trên dòng lệnh
    assert "--max-turns" not in nao.lenh_phien("claude", str(tmp_path), so_luot=None)


def test_chuan_bi_va_khoa_phien(tmp_path):
    goc = str(tmp_path)
    nao.chuan_bi_thu_muc(goc)
    for sub in ("tri-nho", "nhat-ky", "ky-nang"):
        assert os.path.isdir(os.path.join(goc, "nao", sub))
    assert os.path.isfile(os.path.join(goc, "nao", "tri-nho", "MEMORY.md"))
    assert nao.lay_khoa(goc) is True
    assert nao.lay_khoa(goc) is False        # đang có phiên (cùng pid còn sống) → không chạy chồng
    nao.tra_khoa(goc)
    assert nao.lay_khoa(goc) is True
    nao.tra_khoa(goc)


def test_log_khong_lo_khoa():
    khoa = "sk" + "-" + "abcdefghijklmnopqrstuvwxyz0123456789"   # khoá GIẢ, ghép chuỗi để quét bí mật không báo nhầm
    assert khoa not in nao._che("env ANTHROPIC_API_KEY=" + khoa + " ok", khoa)
    assert "Bearer" not in nao._che("Authorization: Bearer abcdefghijklmnop1234", "")


def test_bao_cao_chay_duoc_voi_kho_rong(tmp_path):
    goc = _goc(tmp_path)
    ra = nao.bao_cao(goc, HOM_NAY)
    assert "BÁO CÁO CHO BỘ NÃO" in ra and "ĐỌC SÂU" in ra and ra.count("\n") <= 250
    assert "TỪ CHỐI" in _chay_chu(goc, "bang-diem", "ZZ")


def _chay_chu(goc, *argv):
    try:
        return nao.chay_lenh(nao._parser().parse_args(list(argv)), goc, HOM_NAY)
    except nao.TuChoi as loi:
        return "TỪ CHỐI: " + str(loi)


def test_dang_ky_lich_nao_06_45(tmp_path):
    from core import lich_tu_chay as ltc

    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "nao.py").write_text("", encoding="utf-8")
    goi = []
    ok, _ = ltc.dang_ky_nao(str(tmp_path), chay_lenh=lambda l: (goi.append(l) or (0, "")))
    assert ok and goi[0][:4] == ["schtasks", "/Create", "/TN", "ShopAPI-Nao"]
    assert goi[0][goi[0].index("/SC") + 1] == "DAILY" and goi[0][goi[0].index("/ST") + 1] == "06:45"
    assert "-m core.nao phien" in goi[0][goi[0].index("/TR") + 1]
    assert ltc.dang_ky_nao(str(tmp_path), "25:00", chay_lenh=lambda l: (0, ""))[0] is False


def test_khoa_ghi_va_vo_ghi_nguyen_tu(tmp_path):
    goc = _goc(tmp_path)
    with nao._khoa_hd(goc) as k1:
        assert k1.co and os.path.isfile(os.path.join(goc, "nao", ".khoa-hd"))
        with nao._khoa_hd(goc) as k2:           # lồng nhau cùng tiến trình: không tự chặn mình
            assert not k2.co
        assert os.path.isfile(os.path.join(goc, "nao", ".khoa-hd"))
    assert not os.path.exists(os.path.join(goc, "nao", ".khoa-hd"))
    assert _thu(goc, truc="hook", gt="canh_bao", n="1") == 0 and len(nao.doc_hanh_dong(goc)) == 1   # đường ghi qua vỏ có khoá
    assert not os.path.exists(os.path.join(goc, "nao", ".khoa-hd"))


def test_lenh_phien_co_chi_dao_noi_them(tmp_path):
    lenh = nao.lenh_phien("claude", str(tmp_path))
    nd = lenh[lenh.index("--append-system-prompt") + 1]
    assert "TUẦN TỰ" in nd and "tri-nho/MEMORY.md" in nd
