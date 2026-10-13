"""Tests `core/nao_bo_phan` — bộ gom trên cây giả: từng nguồn → đúng bộ phận, con trỏ tăng dần, nhìn lùi 14 ngày,
tệp hỏng không dừng lượt gom, bản chiếu bài học (α/β, gạch → nghỉ, biến khỏi nguồn → nghỉ), vault Obsidian.
Mã giả (`AAAAAAAAAAA`), kênh giả `KA`/`KB`."""

import contextlib
import json
import os
import sqlite3
import time

from core import nao_bo_phan as nbp
from core.nao_bo_phan import _chung as C

NGAY = 86400.0
VID = "AAAAAAAAAAA"


def _ts(bg, gio, mau="%Y-%m-%d %H:%M:%S"):
    return time.strftime(mau, time.localtime(bg - gio * 3600))


def _ghi(p, noi_dung):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(noi_dung if isinstance(noi_dung, str) else json.dumps(noi_dung, ensure_ascii=False))


def _jsonl(ds):
    return "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in ds)


@contextlib.contextmanager
def _db(goc):
    con = sqlite3.connect(C.duong_db(goc))
    try:
        yield con
    finally:
        con.close()


def _cay(tmp_path, bg):
    g = str(tmp_path)
    j = lambda *p: os.path.join(g, *p)  # noqa: E731
    for k in ("KA", "KB"):
        _ghi(j("CHANNEL", k, "kenh.yaml"), "nhom: n1\n")
    os.makedirs(j("CHANNEL", "_KHUON", "x"))
    os.makedirs(j("CHANNEL", "VO-RONG"))                            # vỏ rỗng: không phải kênh
    hom_nay = _ts(bg, 0, "%Y-%m-%d")
    _ghi(j("CHANNEL", "KA", "tu-chay", hom_nay + ".json"), {"ngay": hom_nay, "kenh": "KA", "runs": [
        {"ma_luot": "0001", "nguon": {"ma": VID, "tieu_de": "đề tài thử", "diem": 80, "cong_thuc": "vph",
                                      "ly_do": ["vph cao"]},
         "san_xuat": {"khau_hong": ["giong-doc"], "loi": "",
                      "loi_dung": "Dừng ở “Đọc thành giọng”: tải kết quả hỏng (400) cho job job_abc123def456ghi789"},
         "ban_giao": {"da_ban_giao": True, "ly_do_trong": "tu_duyet: false — để trống ngày giờ", "loi": ""},
         "bo": True, "ly_do_bo": "đã tự phục hồi (nhặt lại) 3 lần mà vẫn chưa xong",
         "phuc_hoi": {"so_lan": 3, "loai_loi_truoc": ""}},
        {"tham_chieu_ma_luot": "0001", "tham_chieu_ngay": hom_nay},
        {"ma_luot": "0002", "san_xuat": None,
         "ban_giao": {"da_ban_giao": False, "loi": "KHÔNG bàn giao KA-0002: chất lượng chưa đạt"}}]})
    _ghi(j("CHANNEL", "KB", "tu-chay", hom_nay + ".json"), "{hỏng")      # tệp hỏng → cảnh báo, đi tiếp
    luot = j("PROJECTS", "AUTO", "KA", "0001")
    _ghi(os.path.join(luot, "trang-thai.json"), {"ma_kenh": "KA", "ma_luot": "0001", "khau": {
        "kich-ban": {"trang_thai": "xong", "so_lan": 1, "loi": "", "bat_dau": bg - 7200, "ket_thuc": bg - 7000},
        "giong-doc": {"trang_thai": "hong", "so_lan": 3, "loi": "tải kết quả hỏng (400) cho job job_zzz999yyy888xxx",
                      "bat_dau": bg - 7000, "ket_thuc": bg - 6000},
        "anh": {"trang_thai": "cho", "so_lan": 0, "loi": "", "bat_dau": None, "ket_thuc": None}}})
    _ghi(os.path.join(luot, "9-chat-luong.json"), {
        "luc": _ts(bg, 1).replace(" ", "T"), "ma_goi": "KA-0001", "kenh": "KA", "dat": True, "diem": 95,
        "loi": [{"ma": "kb_mo_dau", "muc": "canh_bao", "chi_tiet": "phần mở đầu 162s", "sua": ""}],
        "da_sua": ["chuẩn hoá tiếng -15 LUFS"], "lam_lai": [3, 5], "da_lam_lai": {}})
    _ghi(j("vm", "logs", "so-video-id.json"), {
        "KA/KA-0001": {"video_id": VID, "trang_thai": "xac-nhan", "lan_tai_moi": 2, "cap_nhat": _ts(bg, 2)},
        "KB/KB-0001": {"video_id": "", "trang_thai": "loi-tai", "lan_tai_moi": 1, "cap_nhat": _ts(bg, 2)}})
    _ghi(j("vm", "logs", "cmt-dom.json"), {
        VID: {"kenh": "KA", "ma": "KA-0001", "trang_thai": "da-ghim", "lan_gui": 1, "cap_nhat": _ts(bg, 3)},
        "_kenh:KA": {"can_xac_minh": _ts(bg, 3)}})
    _ghi(j("vm", "logs", "cmt-dom.log"), "".join([
        _ts(bg, 3) + ",100 INFO: mở Chrome kênh KA theo agent\n",
        _ts(bg, 3) + ",200 INFO: DU PHONG xem_menu_ghim: khớp bằng chu (Ghim)\n",
        _ts(bg, 3) + ",300 ERROR: KA-0001: bình luận mồi/ghim hỏng: đã bấm Ghim nhưng KHÔNG thấy huy hiệu\n"]))
    _ghi(j("vm", "logs", "dang-dom.log"), "".join([
        _ts(bg, 4) + ",100 INFO: mở Chrome kênh KB theo agent\n",
        _ts(bg, 4) + ",200 INFO: DU PHONG nut_thumbnail: khớp bằng chu (Tải tệp lên)\n",
        _ts(bg, 4) + ",250 INFO: TU CHUA nut_thumbnail: khớp bằng bộ chọn tự chữa ytcp-x\n",
        _ts(bg, 4) + ",300 WARNING: CẢNH BÁO kế hoạch trùng tiêu đề\n"]))
    _ghi(j("vm", "logs", "tu-chua-dom.jsonl"), _jsonl([
        {"luc": _ts(bg, 4), "khoa": "nut_thumbnail", "ket": "chua", "chon": "ytcp-x", "ly_do": "đổi bộ chọn"}]))
    _ghi(j("workspace", "gac-tong", hom_nay + ".jsonl"), _jsonl([
        {"loai": "ram_thap", "kenh": "", "chuyen_gi": "RAM máy chỉ còn 1.2 GB trống.", "luc": _ts(bg, 5)},
        {"loai": "tai_len_hong", "kenh": "KB", "chuyen_gi": "Máy đăng kênh KB không nhận ra ô tiêu đề",
         "dedupe_khoa": "tai_len_hong:KB:x", "luc": hom_nay + "T00:00:01"},
        {"loai": "tai_len_hong", "kenh": "KB", "chuyen_gi": "Máy đăng kênh KB không nhận ra ô tiêu đề",
         "dedupe_khoa": "tai_len_hong:KB:x", "luc": hom_nay + "T00:15:01"},   # nhắc lại cùng sự cố → không tính thêm
        {"loai": "tu_sua:don_khoa_may_chet", "kenh": "", "chuyen_gi": "Xoá khoá chết", "luc": _ts(bg, 5)},
        {"loai": "giam_doc_viec", "kenh": "KA", "chuyen_gi": "Giám đốc kênh KA: xem số", "luc": _ts(bg, 5)},
        {"loai": "khong_video_moi", "kenh": "KA", "chuyen_gi": "Kênh KA chưa có video", "luc": _ts(bg, 5)},
        {"loai": "ram_thap", "kenh": "", "chuyen_gi": "sự kiện quá cũ", "luc": _ts(bg, 24 * 30)}]) + "{dong hong\n")
    cu = j("workspace", "gac-tong", "2020-01-01.jsonl")                 # tệp im từ trước cửa sổ 14 ngày
    _ghi(cu, _jsonl([{"loai": "ram_thap", "chuyen_gi": "cũ", "luc": _ts(bg, 1)}]))
    os.utime(cu, (bg - 40 * NGAY, bg - 40 * NGAY))
    _ghi(j("workspace", "viet-max", "so-dung.jsonl"), _jsonl([
        {"viec": "KA:0001:chat:thumb:abc", "ok": True, "giay": 80.0, "luc": _ts(bg, 6).replace(" ", "T"), "pid": 1},
        {"viec": "KA:0001:chat:2-viet.md", "ok": False, "loi": "hết hạn mức", "giay": 3.0,
         "luc": _ts(bg, 6).replace(" ", "T"), "pid": 2}]))
    _ghi(j("CHANNEL", "_NHOM", "n1", "radar", "quyet-dinh.jsonl"), _jsonl([
        {"luc": _ts(bg, 7).replace(" ", "T"), "ma": VID, "kenh_nguon": "đối thủ", "view": 900.0, "gan": "KA",
         "quyet": "bo", "vi_sao": "view 900 < 3.000"}]))
    _ghi(j("CHANNEL", "KA", "tu-hoc", "van.json"), {
        "KA-0001": {"ma_goi": "KA-0001", "ket": "thang", "ket_pv": 88.0, "ket_tuoi": 120.0, "thuoc": 1},
        "KA-0002": {"ma_goi": "KA-0002", "thuoc": 1}})
    _ghi(j("workspace", "tu-chay", "tu-chay.log"), "".join("[{0}] {1}\n".format(_ts(bg, 1), x) for x in (
        "[KA] [ĐANG] Tạo ảnh từng cảnh (có tiêu ví)",
        "[KA]   lần 1 hỏng (đợi 12 phút mà máy chủ vẫn chưa trả kết quả) — thử lại sau 5 giây.",
        "[KA] Xong `--tat-ca` — không lỗi.",
        "[KA] đường viết chữ: hết hạn mức thì tụt bậc ngay, hỏng vì lý do khác thì thử lại",
        "[KB] [HỎNG] Dừng ở “Dựng video hoàn thiện”. Mọi thứ đã làm vẫn còn")))
    # sổ bài học giám đốc: bài X có 2 video ủng hộ + 1 phản bác; bài Y bị chủ gạch
    gd = j("CHANNEL", "KA", "giam-doc")
    phieu = lambda v, h, truc="tieu_de", gt="nhan_x": {  # noqa: E731
        "truc": truc, "gia_tri": gt, "huong": h, "cum": "", "cau": "nhãn X làm CTR 2.1% < trung vị 3.0%",
        "video_id": v, "moc": "96h", "so_dan": [{"so": 2.1, "nguon": "v:x/96h/ctr"}], "luc": _ts(bg, 30)}
    _ghi(os.path.join(gd, "bai-hoc.jsonl"), _jsonl([phieu("AAAAAAAAAA1", "-"), phieu("AAAAAAAAAA2", "-"),
                                                    phieu("AAAAAAAAAA3", "+"), phieu("AAAAAAAAAA1", "+"),
                                                    phieu("AAAAAAAAAA4", "+", "hook", "cau_hoi")]))
    _ghi(os.path.join(gd, "bai-hoc-gach.jsonl"), _jsonl([{"ma_bai": "kn:hook|cau_hoi|"}]))
    _ghi(j("CHANNEL", "KA", "nghien-cuu", "bai-hoc-san-xuat.json"), {"kenh": "KA", "bai_hoc": [
        {"truc": "thumbnail_ctr", "cum": "", "quan_sat": "kiểu A: CTR trung vị 4,9% (n=5)", "so_mau": 5,
         "do_tin_cay": "cao", "video_dan_chung": [VID], "ngay_cap_nhat": hom_nay}]})
    C._KENH.clear()
    return g


def _dem(con, **dk):
    w = " AND ".join("{0} = ?".format(k) for k in dk)
    return con.execute("SELECT COUNT(*) FROM su_kien WHERE " + w, tuple(dk.values())).fetchone()[0]


def test_gom_moi_nguon(tmp_path):
    bg = time.time()
    goc = _cay(tmp_path, bg)
    tk = nbp.gom(goc, bay_gio=bg)
    assert C.cac_kenh(goc) == ["KA", "KB"]                              # bỏ `_KHUON`, vỏ rỗng không kenh.yaml
    assert tk["canh_bao"] == {"so-ngay": 1}                              # sổ ngày KB hỏng: đếm, không dừng
    with _db(goc) as con:
        d = lambda **k: _dem(con, **k)  # noqa: E731
        # sổ ngày: chọn nguồn, bỏ lượt, phục hồi, bàn giao hỏng; "để trống mà vẫn bàn giao" KHÔNG là lỗi
        assert d(nguon="so-ngay", bo_phan="chon-content", loai="chon") == 1
        assert d(bo_phan="dieu-phoi", loai="loi", nguon="so-ngay") == 1
        assert d(bo_phan="dieu-phoi", loai="sua", nguon="so-ngay") == 1
        assert d(bo_phan="ban-giao", loai="loi") == 1
        # lỗi giọng đọc của lượt 0001: sổ ngày + trang-thai.json báo cùng một lỗi → MỘT sự kiện
        assert d(bo_phan="giong-doc", loai="loi") == 1
        assert d(nguon="trang-thai", loai="do") == 2                    # khâu đã kết thúc (xong/hỏng), bỏ "cho"
        assert d(bo_phan="kiem-chat-luong", loai="loi", chu_ky=C.bam("qa:kb_mo_dau")) == 1
        assert d(bo_phan="kiem-chat-luong", loai="sua") == 2 and d(bo_phan="kiem-chat-luong", loai="ket_qua") == 1
        # máy ảo
        assert d(nguon="so-video-id", loai="ket_qua") == 1 and d(nguon="so-video-id", loai="loi") == 2
        assert d(nguon="cmt-dom", loai="ket_qua") == 1 and d(nguon="cmt-dom", loai="loi") == 1
        assert d(nguon="cmt-dom.log", bo_phan="binh-luan", loai="loi") == 2
        dom = C.bam("dom:nut_thumbnail")
        assert con.execute("SELECT bo_phan, kenh FROM su_kien WHERE nguon='dang-dom.log'").fetchall() == \
            [("dang-video", "KB")] * 2                                   # kênh = kênh nhắc gần nhất; WARNING bỏ
        assert d(chu_ky=dom, loai="loi") == 1 and d(chu_ky=dom, loai="sua", nguon="tu-chua-dom") == 1
        assert d(chu_ky=C.bam("dom-du-phong:nut_thumbnail"), loai="loi") == 1   # DU PHONG: nơ-ron cảnh báo riêng
        # gác tổng: bộ phận theo loại; quá cũ bị lọc; dòng hỏng bỏ qua; tệp cũ không đọc
        gac = sorted(r[0] for r in con.execute("SELECT bo_phan || ':' || loai FROM su_kien WHERE nguon='gac-tong'"))
        assert gac == ["dang-video:loi", "dieu-phoi:do", "dieu-phoi:loi", "suc-khoe-may:loi", "suc-khoe-may:sua"]
        # viết Max: thumb → bìa (đo), hỏng → kịch bản (lỗi); radar → chọn content của kênh được gán; ván đã phán
        assert d(nguon="viet-max", bo_phan="bia", loai="do") == 1 and d(nguon="viet-max", bo_phan="kich-ban",
                                                                        loai="loi") == 1
        assert d(nguon="radar", bo_phan="chon-content", loai="chon", kenh="KA") == 1
        assert d(nguon="van", loai="ket_qua") == 1
        # tu-chay.log: lỗi rõ ràng → khâu đang chạy của kênh; câu "không lỗi"/giải thích không tính
        assert con.execute("SELECT bo_phan, kenh FROM su_kien WHERE nguon='tu-chay.log' ORDER BY bo_phan").fetchall() \
            == [("anh-clip", "KA"), ("dung-video", "KB")]


def test_gom_tang_dan_con_tro(tmp_path):
    bg = time.time()
    goc = _cay(tmp_path, bg)
    nbp.gom(goc, bay_gio=bg)
    with _db(goc) as con:
        n0 = con.execute("SELECT COUNT(*) FROM su_kien").fetchone()[0]
    tk = nbp.gom(goc, bay_gio=bg)
    assert sum(sum(v.values()) for v in tk["them"].values()) == 0 and tk["ghi_tep"] == 0
    log = os.path.join(goc, "workspace", "tu-chay", "tu-chay.log")
    with open(log, "a", encoding="utf-8", newline="\n") as tep:
        tep.write("[{0}] [KA]   lần 2 hỏng (đợi 12 phút mà máy chủ vẫn chưa trả kết quả) — hết lượt thử.\n".format(
            _ts(bg, 0.5)))
        tep.write("[{0}] [KA]   lần 3 hỏng (dòng đang ghi dở".format(_ts(bg, 0.4)))     # chưa xuống dòng → đợi
    tk = nbp.gom(goc, bay_gio=bg)
    assert tk["them"] == {"anh-clip": {"loi": 1}}                       # khâu "ảnh" nhớ qua con trỏ
    # tệp bị xoay vòng (ngắn lại, đầu tệp khác) → đọc từ đầu; dòng cũ không trùng nhờ khoá
    _ghi(log, "[{0}] [KB] Traceback (most recent call last): ValueError\n".format(_ts(bg, 0.2)))
    tk = nbp.gom(goc, bay_gio=bg)
    assert tk["them"] == {"dieu-phoi": {"loi": 1}}
    with _db(goc) as con:
        assert con.execute("SELECT COUNT(*) FROM su_kien").fetchone()[0] == n0 + 2


def test_bai_hoc_ban_chieu(tmp_path):
    bg = time.time()
    goc = _cay(tmp_path, bg)
    nbp.gom(goc, bay_gio=bg)
    v = os.path.join(goc, "nao", "bo-phan")
    ds = {}
    for bp in ("tieu-de", "kich-ban", "bia"):
        for ten in os.listdir(os.path.join(v, bp, "bai-hoc")):
            dau, than = C.doc_ghi_chu(C.doc_chu(os.path.join(v, bp, "bai-hoc", ten)))
            ds[(bp, dau["truc"])] = (dau, than)
    dau, than = ds[("tieu-de", "tieu_de")]                              # phiếu đầu "−" là hướng bài; A1 chỉ một phiếu
    assert (dau["alpha"], dau["beta"], dau["n"], dau["trang_thai"], dau["kenh"]) == (3, 2, 3, C.THU_THACH, "KA")
    assert "## Bằng chứng" in than and "AAAAAAAAAA3` (phản bác" in than and "[[bo-phan/thuc-the/kenh/KA|KA]]" in than
    assert ds[("kich-ban", "hook")][0]["trang_thai"] == C.NGHI         # chủ gạch → nghỉ
    sx = ds[("bia", "thumbnail_ctr")][0]
    assert (sx["alpha"], sx["beta"], sx["n"], sx["trang_thai"]) == (3, 1, 5, C.DANG_DUNG)
    so_tay = C.doc_chu(os.path.join(v, "bia", "so-tay.md"))
    assert "Bài học tốt nhất" in so_tay and "**0.75**" in so_tay        # n ≥ 3 vào sổ tay
    # bài biến khỏi nguồn → chuyển "nghi", không xoá
    _ghi(os.path.join(goc, "CHANNEL", "KA", "nghien-cuu", "bai-hoc-san-xuat.json"), {"kenh": "KA", "bai_hoc": []})
    nbp.gom(goc, bay_gio=bg)
    ten = os.listdir(os.path.join(v, "bia", "bai-hoc"))
    assert len(ten) == 1 and C.doc_ghi_chu(C.doc_chu(os.path.join(v, "bia", "bai-hoc", ten[0])))[0][
        "trang_thai"] == C.NGHI


def test_vault_obsidian(tmp_path):
    bg = time.time()
    goc = _cay(tmp_path, bg)
    tk = nbp.gom(goc, bay_gio=bg)
    v = os.path.join(goc, "nao", "bo-phan")
    assert os.path.isfile(os.path.join(v, "_ban-do.md")) and os.path.isfile(os.path.join(v, "thuc-the", "kenh", "KA.md"))
    assert all(os.path.isfile(os.path.join(v, bp, "so-tay.md")) for bp in C.BO_PHAN)
    p = os.path.join(v, "giong-doc", "loi", nbp.chu_ky("tải kết quả hỏng (400) cho job job_abc123def456ghi789",
                                                       ["KA", "KB"]) + ".md")
    dau, than = C.doc_ghi_chu(C.doc_chu(p))
    assert {"chu_ky", "bo_phan", "trang_thai", "so_lan", "so_lan_7_ngay", "lan_dau", "lan_cuoi", "kenh"} <= set(dau)
    assert dau["trang_thai"] == C.DANG and dau["kenh"] == ["KA"] and dau["nguon"] == ["so-ngay"]
    assert than.startswith("# tải kết quả hỏng (#) cho job <ma>") and "## Quan sát" in than and "## Liên kết" in than
    assert tk["no_ron"]["giong-doc"][C.DANG] == 1 and tk["chi_muc"]["loi"] >= 10
    # cách sửa đã thử gắn vào nơ-ron TU CHUA cùng khoá bộ chọn; DU PHONG là nơ-ron CẢNH BÁO riêng
    dom = C.doc_chu(os.path.join(v, "dang-video", "loi", C.bam("dom:nut_thumbnail") + ".md"))
    assert "## Cách sửa đã thử" in dom and "chưa đủ 7 ngày" in dom and "muc: loi" in dom
    dp = C.doc_chu(os.path.join(v, "dang-video", "loi", C.bam("dom-du-phong:nut_thumbnail") + ".md"))
    assert "muc: canh-bao" in dp and "[[bo-phan/thuc-the/bo-chon/nut_thumbnail|bộ chọn nut_thumbnail]]" in dp
    with _db(goc) as con:
        assert con.execute("SELECT COUNT(*) FROM lien_ket WHERE tu LIKE 'giong-doc/loi/%' AND "
                           "toi = 'thuc-the/kenh/KA'").fetchone()[0] == 1
    assert nbp.nho(goc, "dang-video", "nut_thumbnail tự chữa ytcp-x")[0]["id"] == \
        "dang-video/loi/" + C.bam("dom:nut_thumbnail")
