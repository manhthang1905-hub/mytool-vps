"""Test trang «Não» của Trung tâm trực quan (dữ liệu giả, thư mục tạm): sổ hành động, log phiên, trí nhớ,
bài học, che khoá, chỉ đọc."""
import datetime as dt
import json
import os

from core import nao_truc_quan as nt

BAY = dt.datetime(2026, 10, 20, 9, 0, 0)


def _ghi(p, chu):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)


def _gia(tmp_path):
    g = str(tmp_path)
    _ghi(os.path.join(g, "vm", "cai-dat-tool.json"), json.dumps({"kenh": {"KB-A": {}, "KA-B": {}}}))
    hd = [
        {"id": "n001", "luc": "2026-10-10T04:12:00", "lenh": "thu", "tham_so": {"kenh": "KA-B", "truc": "cum", "gia_tri": "x",
         "so_video": 2, "da_dung": 2}, "ly_do": "lý do có số 123", "du_doan": "2 video kế có CTR ≥ 5%", "kiem_ngay": "2026-10-15",
         "trang_thai": "xong", "cham": "dung", "ghi_chu_cham": "CTR 6,1%", "cham_luc": "2026-10-15T04:20:00"},
        {"id": "n002", "luc": "2026-10-11T04:12:00", "lenh": "tranh", "tham_so": {"kenh": "KB-A", "truc": "hook", "gia_tri": "y",
         "ngay": 3, "het_han": "2026-10-14"}, "du_doan": "3 video kế hiển thị > 50", "kiem_ngay": "2026-10-16",
         "trang_thai": "mo", "cham": "sai", "ghi_chu_cham": "chỉ 20", "cham_luc": "2026-10-17T04:20:00"},
        {"id": "n003", "luc": "2026-10-18T04:12:00", "lenh": "de-xuat", "tham_so": {"noi_dung": "mở thêm khe đăng"},
         "du_doan": "đề xuất có ích cho kênh", "kiem_ngay": "2026-10-19", "trang_thai": "mo", "cham": None},
        {"id": "n004", "luc": "2026-10-20T04:12:00", "lenh": "thu", "tham_so": {"kenh": "KB-A", "truc": "cum", "gia_tri": "z",
         "so_video": 1, "da_dung": 0}, "du_doan": "1 video kế thắng mốc 48h", "kiem_ngay": "2026-10-25",
         "trang_thai": "mo", "cham": None},
        {"id": "n005", "luc": "2026-10-20T04:13:00", "lenh": "bai-hoc", "tham_so": {"kenh": "KB-A", "thao_tac": "them",
         "noi_dung": "bìa chữ to có 3 video thắng"}, "trang_thai": "xong", "cham": None, "khong_tinh": True},
        {"id": "n006", "luc": "2026-10-01T04:13:00", "lenh": "de-xuat", "tham_so": {"noi_dung": "cũ quá hạn"},
         "du_doan": "chủ xử lý trong tuần", "kiem_ngay": "2026-10-05", "trang_thai": "mo", "cham": None},
    ]
    _ghi(os.path.join(g, "nao", "hanh-dong.json"), json.dumps(hd, ensure_ascii=False))
    log = "\n".join([
        "04:10:00 === BAT DAU PHIEN 2026-10-20 · model m · tối đa 40 lượt · hết giờ 30 phút",
        "04:10:00 lệnh: claude.exe --print --output-format stream-json",
        "04:10:05 [não] Bắt đầu. ## Bước 1: Nhớ lại - đọc trí nhớ - đọc nhật ký",
        "04:10:06 [Read] nao/tri-nho/MEMORY.md",
        "04:10:06    → 1 # Trí nhớ",
        "04:10:07 [Bash] python -m core.nao xem --key " + "sk-" + "abcdefghijklmnopqrstuvwxyz",
        "04:10:08    → LỖI không chạy được",
        "04:10:09 [Read] nao/nhat-ky/x.md",
        "04:11:00 [não] ## Quyết định **KHÔNG thêm** hành động. 1. Ngưỡng CTR 9% 2. Chờ kiểm "
        "Bearer abcdefghijklmnop0123 token=supersecretvalue 0123456789abcdef0123456789abcdef",
        "04:11:01 KET QUA: thanh cong · mã 0 · 12 lượt · 120.5s · chi phí ước tính 1.25 USD",
        "04:11:01 tóm tắt của não: ## Quyết định **KHÔNG thêm** hành động.",
        "04:11:01 nhật ký ngày: có",
    ]) + "\n"
    _ghi(os.path.join(g, "nao", "nhat-ky", "phien-2026-10-20.log"), log)
    _ghi(os.path.join(g, "nao", "nhat-ky", "phien-2026-10-19.log"),
         "04:10:00 === BAT DAU PHIEN 2026-10-19\n04:12:00 KET QUA: that bai · mã 1 · None lượt · 3.0s · chi phí ước tính ? USD\n")
    _ghi(os.path.join(g, "nao", "nhat-ky", "2026-10-20.md"), "# nhật ký\n")
    _ghi(os.path.join(g, "nao", "tri-nho", "MEMORY.md"), "# Trí nhớ\n\nDòng một\nDòng hai\nDòng ba\n")
    _ghi(os.path.join(g, "nao", "tri-nho", "su-that.md"),
         "---\nname: su-that\ndescription: mô tả ngắn\nmetadata:\n  type: project\n---\n\nThân bài một\n\nThân bài hai\n")
    _ghi(os.path.join(g, "nao", "ky-nang", "doc-so.md"), "kỹ năng\n")
    for k in ("KB-A", "KA-B"):
        _ghi(os.path.join(g, "CHANNEL", k, "kenh.yaml"), "ten: Kenh gia\n")
    bh = [{"truc": "cum", "gia_tri": "x", "huong": "+", "cum": "x", "cau": "Cụm x thắng 3 video 48h", "video_id": "v%d" % i,
           "moc": "48h", "luc": "2026-10-1%dT00:10:00" % i, "bong": False} for i in range(1, 4)]
    bh.append({"truc": "tu_do", "gia_tri": "tu_do:aa", "huong": "+", "cum": "", "cau": "Bìa chữ to 2 video", "video_id": "nao-2026-10-20",
               "moc": "nao", "luc": "2026-10-20T04:13:00", "loai": "delta", "nguon": "nao"})
    bh.append({"truc": "hook", "gia_tri": "h", "huong": "+", "cum": "", "cau": "Hook h 1 video", "video_id": "v9",
               "moc": "48h", "luc": "2026-10-12T00:00:00"})
    bh += [{"truc": "hook", "gia_tri": "h", "huong": "-", "cum": "", "cau": "Hook h phản 2 video", "video_id": "w%d" % i,
            "moc": "48h", "luc": "2026-10-13T00:00:00"} for i in range(3)]
    _ghi(os.path.join(g, "CHANNEL", "KB-A", "giam-doc", "bai-hoc.jsonl"),
         "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in bh))
    return g


def _anh_chup(g):
    ra = {}
    for goc_con, _t, cac in os.walk(g):
        for t in cac:
            p = os.path.join(goc_con, t)
            with open(p, "rb") as tep:
                ra[p] = tep.read()
    return ra


def test_tinh_du_cac_muc_va_chi_doc(tmp_path):
    g = _gia(tmp_path)
    truoc = _anh_chup(g)
    d = nt.tinh(g, BAY)
    assert _anh_chup(g) == truoc                       # không ghi/sửa tệp nào (kể cả hết hạn chỉ tính)
    assert d["kenh"] == ["KA-B", "KB-A"]
    diem = d["diem"]
    assert (diem["dung"], diem["da_cham"], diem["ti_le"]) == (1, 2, 50.0)
    assert diem["hom_nay"] == 1 and diem["han_muc"] == 3        # n005 khong_tinh không tính
    assert diem["toi_han"] == 1                                  # n003 kiểm 19/10 chưa chấm
    assert diem["dang_mo"] == 2                                  # n003, n004 (n002 tranh hết hạn → xong; n006 → het_han)
    assert diem["bai_hoc_nao"] == 1
    ids = [x["id"] for x in d["hanh_dong"]]
    assert ids[0] == "n005" and ids[-1] == "n006"                # mới → cũ
    tt = {x["id"]: x["trang_thai"] for x in d["hanh_dong"]}
    assert tt["n002"] == "xong" and tt["n006"] == "het_han"
    assert d["lan_cuoi"]["ngay"] == "2026-10-20" and d["lan_cuoi"]["thanh_cong"] and d["lan_cuoi"]["ma"] == 0
    assert d["lan_cuoi"]["luot"] == "12" and d["lan_cuoi"]["usd"] == "1.25"


def test_chuoi_ti_le_cong_don_theo_ngay_cham(tmp_path):
    g = _gia(tmp_path)
    c = nt.tinh(g, BAY)["chuoi_ti_le"]
    assert [(x["ngay"], x["dung"], x["tong"], x["ti_le"]) for x in c] == [("2026-10-15", 1, 1, 100.0),
                                                                          ("2026-10-17", 1, 2, 50.0)]


def test_phien_gom_cong_cu_tach_dong_va_che_khoa(tmp_path):
    g = _gia(tmp_path)
    d = nt.tinh(g, BAY)
    ph = d["phien"]
    assert [p["ngay"] for p in ph] == ["2026-10-20", "2026-10-19"]
    assert ph[1]["ket_qua"]["thanh_cong"] is False and ph[1]["ket_qua"]["ma"] == 1 and not ph[1]["nhat_ky"]
    khoi = ph[0]["khoi"]
    loai = [k["loai"] for k in khoi]
    assert loai == ["bat_dau", "nghi", "cong_cu", "nghi", "ket", "ghi_chu"]   # tóm tắt trùng lời cuối → bỏ; dòng lệnh bỏ
    cc = khoi[2]
    assert cc["so"] == 3 and cc["loi"] == 1 and cc["tom"] == "Read×2, Bash"
    assert khoi[1]["dong"] == ["Bắt đầu.", "## Bước 1: Nhớ lại", "- đọc trí nhớ", "- đọc nhật ký"]
    assert khoi[3]["dong"][:2] == ["## Quyết định", "**KHÔNG thêm** hành động."]
    toan = json.dumps(d, ensure_ascii=False)
    for bi_mat in (("sk-" + "abcdefghij"), "abcdefghijklmnop0123", "supersecretvalue", "0123456789abcdef0123456789abcdef"):
        assert bi_mat not in toan


def test_phien_cat_60_dong_giu_phan_ket(tmp_path):
    dong = ["04:00:00 === BAT DAU PHIEN x"]
    for i in range(30):
        dong.append("04:%02d:00 [não] đoạn %d - ý một - ý hai" % (i % 60, i))
        dong.append("04:%02d:01 [Read] tệp %d" % (i % 60, i))
    dong.append("05:00:00 [não] KẾT LUẬN CUỐI")
    dong.append("05:00:01 KET QUA: thanh cong · mã 0 · 1 lượt · 1s · chi phí ước tính 0.1 USD")
    ph = nt.doc_phien(dong, toi_da=60)
    assert ph["so_dong"] <= 60 and ph["an"] > 0
    assert ph["khoi"][-1]["loai"] == "ket" and ph["khoi"][-2]["dong"] == ["KẾT LUẬN CUỐI"]


def test_tri_nho_va_ky_nang(tmp_path):
    g = _gia(tmp_path)
    t = nt.tinh(g, BAY)["tri_nho"]
    assert [x["ten"] for x in t["tep"]][0] == "MEMORY.md"
    m = {x["ten"]: x for x in t["tep"]}
    assert m["MEMORY.md"]["dau"] == ["# Trí nhớ", "Dòng một", "Dòng hai"]
    assert m["su-that.md"]["dau"] == ["mô tả ngắn", "Thân bài một", "Thân bài hai"]
    assert m["MEMORY.md"]["co"] > 0 and len(m["MEMORY.md"]["sua"]) == 16
    assert t["ky_nang"] == ["doc-so.md"]


def test_bai_hoc_dang_ap_bo_bai_bo(tmp_path):
    g = _gia(tmp_path)
    b = nt.tinh(g, BAY)["bai_hoc"]
    assert b["dem"]["bo"] == 1                                     # hook h: 1 ủng hộ, 3 phản → bỏ
    assert [x["noi_dung"] for x in b["ds"]] == ["Bìa chữ to 2 video", "Cụm x thắng 3 video 48h"]
    nao_bai, kn_bai = b["ds"]
    assert nao_bai["nguon"] == "não" and nao_bai["kenh"] == "KB-A" and nao_bai["luc"] == "2026-10-20 04:13"
    assert kn_bai["trang_thai"] == "that" and kn_bai["cong"] == 3 and kn_bai["nguon"] == "khám nghiệm"


def test_thieu_du_lieu_khong_vo(tmp_path):
    d = nt.tinh(str(tmp_path), BAY)
    assert d["hanh_dong"] == [] and d["phien"] == [] and d["lan_cuoi"] == {"co": False}
    assert d["tri_nho"] == {"tep": [], "ky_nang": []} and d["bai_hoc"]["ds"] == []
    assert d["diem"]["ti_le"] is None and d["chuoi_ti_le"] == []


def test_muc_hong_chi_bao_loi_muc_do(tmp_path, monkeypatch):
    g = _gia(tmp_path)
    monkeypatch.setattr(nt, "tri_nho", lambda goc: 1 / 0)
    d = nt.tinh(g, BAY)
    assert "ZeroDivisionError" in d["tri_nho"]["loi"] and isinstance(d["hanh_dong"], list)


def test_che():
    s = nt.che("a sk-ABCDEFGH12345 b Bearer xyz.abc-123456 api_key=\"abcdef123\" ghp_" + "a" * 30 + " " + "f" * 40)
    assert "ABCDEFGH" not in s and "xyz.abc" not in s and "abcdef123" not in s and "aaaa" not in s and "ffff" not in s
    assert nt.che("CTR 9.47% video tAHCp1") == "CTR 9.47% video tAHCp1"


def test_may_chu_phuc_vu_trang_va_json(tmp_path, monkeypatch):
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from core import truc_quan

    g = _gia(tmp_path)
    monkeypatch.setattr(nt, "GOC", g)
    monkeypatch.setattr(nt, "_NHO", {"luc": 0.0, "du": None})
    sv = ThreadingHTTPServer(("127.0.0.1", 0), truc_quan._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        goc = "http://127.0.0.1:{0}".format(sv.server_address[1])
        trang = urllib.request.urlopen(goc + "/nao", timeout=10).read().decode("utf-8")
        assert "/nao.json" in trang and 'class="tab on" href="/nao"' in trang
        du = json.loads(urllib.request.urlopen(goc + "/nao.json", timeout=30).read().decode("utf-8"))
        assert du["kenh"] == ["KA-B", "KB-A"] and du["diem"]["da_cham"] == 2
    finally:
        sv.shutdown()
        sv.server_close()
    for ten in ("chien-truong.html", "truc-quan.html"):
        with open(os.path.join(truc_quan.GOC, "ui_web", ten), encoding="utf-8") as tep:
            assert 'href="/nao"' in tep.read()
