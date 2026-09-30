"""Giờ khán giả online + "khán giả của bạn còn xem gì" (insight #7, #8 — 29/09/2026).

Canh ba việc mới trong `core/chi_so_ytb/giai_ma.py` (đọc), `core/nghien_cuu_chung.py`
(kho chung nhóm) và `core/xep_lich.py::goi_y_khe` (gợi ý, không tự đổi `nhip_dang`).

Fixture raw ở `tests/du-lieu/build_audience_*` là bản THẬT chép nguyên từ
`CHANNEL/TL4-T7/chi-so/kenh/kenh-20260929/` (mảng `hourlyUsersOnline` 168 ô) và
`CHANNEL/TL1-T7/nghien-cuu/doi-thu.csv` thật (kênh `UCFb9vrcZtNaIWam3vf2xOTw` đã
theo dõi dưới dạng link `/channel/<id>`) — không gọi mạng.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.chi_so_ytb import giai_ma  # noqa: E402
from core import nghien_cuu_chung as ncc  # noqa: E402
from core import xep_lich  # noqa: E402

DU_LIEU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "du-lieu")
RAW_DAY_DU = os.path.join(DU_LIEU, "build_audience_day_du", "raw")
RAW_KENH_MOI = os.path.join(DU_LIEU, "build_audience_kenh_moi", "raw")
RAW_CU_HON = os.path.join(DU_LIEU, "build_audience_cu_hon", "raw")

# 5 ID kênh thật trong fixture `build_audience_day_du` (channelCompetitionCardData).
ID_DA_BIET = "UCFb9vrcZtNaIWam3vf2xOTw"     # đã có trong doi-thu.csv thật của TL1-T7
IDS_CANH_TRANH = {"UCFb9vrcZtNaIWam3vf2xOTw", "UCbCvztp767wlz9HyvX56iqg",
                  "UC24giqozylTeMlUglZYleQw", "UC9CjC8_gEBJyUZCCxILHLpg",
                  "UCHkZKf9_2QSOlgqNqMZAHuw"}


def _kenh(goc, ma, nhom=""):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(d, "nghien-cuu"), exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("ma: {0}\nngon_ngu: ja\n".format(ma) + ("nhom: {0}\n".format(nhom) if nhom else ""))
    return d


def _doi_thu_csv(goc, ma, link_da_theo_doi):
    """Sổ đối thủ tối giản, đúng cột thật của `danh_ba_doi_thu.COT`, theo dõi 1 kênh
    dưới dạng link `/channel/<id>` — đúng hình dạng bắt gặp thật trong `doi-thu.csv`
    của TL1-T7 (dòng "知らないと一生損するお金の話-..." )."""
    p = os.path.join(goc, "CHANNEL", ma, "nghien-cuu", "doi-thu.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8-sig") as tep:
        tep.write("Kênh,Tuyến,Trạng thái,Subs,Tuổi (tháng),View/tháng,Vượt quy mô,Im lặng,"
                  "Mới 7 ngày,Số video,Dài TV,View TV,Cửa,Điểm,Lý do,Đăng gần nhất,Quét lúc,"
                  "Lần đầu thấy,Ghi chú,Link kênh\n")
        tep.write('Kênh đã biết,,theo dõi,1720,,,,,,,,,,,,,,,,{0}\n'.format(link_da_theo_doi))


# ───────────────────────────────────── giờ khán giả online (giai_ma) ──────


def test_doc_gio_online_lay_dung_mang_168_o():
    tho = giai_ma.doc_gio_online(RAW_DAY_DU)
    assert tho is not None
    assert len(tho["mang_utc"]) == 168
    assert tho["captured_at"] == "2026-09-29T01:28:27.180Z"


def test_doc_gio_online_bo_qua_kenh_moi_mang_toan_khong():
    """Kênh mới, Studio chưa đủ 28 ngày dữ liệu → mảng toàn 0 → coi như chưa có."""
    assert giai_ma.doc_gio_online(RAW_KENH_MOI) is None


def test_quy_doi_gio_online_khop_dinh_day_insight_that():
    """Đỉnh/đáy quy đổi phải khớp đúng hai mốc insight #7 đã đối chiếu bằng hiển thị
    thật 29/09/2026: JST đỉnh 20–21h ≈0,97, đáy 03–04h ≈0,50."""
    tho = giai_ma.doc_gio_online(RAW_DAY_DU)
    ra = giai_ma._quy_doi_gio_online(tho["mang_utc"], tho["captured_at"])
    assert ra["dinh"]["jst"]["gio"] in (20, 21)
    assert abs(ra["dinh"]["jst"]["gia_tri"] - 0.97) < 0.01
    assert ra["day"]["jst"]["gio"] in (3, 4)
    assert abs(ra["day"]["jst"]["gia_tri"] - 0.50) < 0.01
    # VPS = JST − 2 (máy đặt múi giờ VN, UTC+7 — xem `vm/may_dang.py`)
    assert ra["dinh"]["vps"]["gio"] == (ra["dinh"]["jst"]["gio"] - 2) % 24
    assert len(ra["gio_x_thu_utc"]) == 7 and all(len(h) == 24 for h in ra["gio_x_thu_utc"])


def test_cap_nhat_gio_online_ghi_tep_va_khong_ghi_thua(tmp_path):
    chi_so = str(tmp_path / "CHANNEL" / "TL4-T7" / "chi-so")
    os.makedirs(chi_so, exist_ok=True)
    ra = giai_ma.cap_nhat_gio_online(RAW_DAY_DU, chi_so)
    assert ra is not None
    duong = os.path.join(chi_so, "gio-online.json")
    assert os.path.isfile(duong)
    with open(duong, encoding="utf-8") as tep:
        tren_dia = json.load(tep)
    assert tren_dia["dinh"]["jst"]["gio"] in (20, 21)
    # gọi lại đúng lượt raw cũ — không ghi thừa (captured_at không mới hơn)
    assert giai_ma.cap_nhat_gio_online(RAW_DAY_DU, chi_so) is None


def test_cap_nhat_gio_online_khong_de_ban_cu_ghi_de_ban_moi(tmp_path):
    """Bản MỚI đã lưu rồi thì một lượt raw CŨ HƠN gọi sau không được ghi đè."""
    chi_so = str(tmp_path / "CHANNEL" / "TL4-T7" / "chi-so")
    os.makedirs(chi_so, exist_ok=True)
    assert giai_ma.cap_nhat_gio_online(RAW_DAY_DU, chi_so) is not None       # mới, 2026-09-29
    assert giai_ma.cap_nhat_gio_online(RAW_CU_HON, chi_so) is None          # cũ hơn, 2026-09-20 — bị chặn
    with open(os.path.join(chi_so, "gio-online.json"), encoding="utf-8") as tep:
        assert json.load(tep)["cap_nhat"] == "2026-09-29T01:28:27.180Z"


# ───────────────────────────────────── khán giả cũng xem (giai_ma + nghien_cuu_chung) ──


def test_doc_khan_gia_cung_xem_lay_dung_id():
    tho = giai_ma.doc_khan_gia_cung_xem(RAW_DAY_DU)
    assert tho is not None
    assert set(tho["kenh_canh_tranh"]) == IDS_CANH_TRANH
    assert {v["video_id"] for v in tho["video_dang_xem"]} == {"ItU1H33KqMw", "1XGzIqTWSQ0"}


def test_doc_khan_gia_cung_xem_khong_co_card_tra_none():
    assert giai_ma.doc_khan_gia_cung_xem(RAW_KENH_MOI) is None


def test_cap_nhat_khan_gia_cung_xem_loc_dung_ung_vien_va_ghi_kho_nhom(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "TL4-T7", "tam-ly-nhat")
    _kenh(goc, "TL1-T7", "tam-ly-nhat")
    _doi_thu_csv(goc, "TL1-T7", "https://www.youtube.com/channel/{0}".format(ID_DA_BIET))

    ban_ghi = giai_ma.cap_nhat_khan_gia_cung_xem(goc, "TL4-T7", RAW_DAY_DU)
    assert ban_ghi is not None
    assert ban_ghi["nguon"] == "khan_gia_cung_xem"
    ids_ung_vien = {u["channel_id"] for u in ban_ghi["ung_vien_doi_thu_uu_tien"]}
    assert ID_DA_BIET not in ids_ung_vien, "kênh đã theo dõi (dù ở kênh khác cùng nhóm) không được lên ứng viên"
    # 5 kênh cạnh tranh + 2 kênh trong audienceInterests, trừ ID_DA_BIET, trừ trùng lặp
    assert ids_ung_vien == (IDS_CANH_TRANH | {"UC2jGalazV4L7CvXeKD4_VDA", "UCbCvztp767wlz9HyvX56iqg"}) - {ID_DA_BIET}

    # ghi vào kho NHÓM — kênh khác trong nhóm đọc lại được (thư mục CHANNEL/_NHOM/tam-ly-nhat/nghien-cuu/)
    duong_nhom = os.path.join(goc, "CHANNEL", "_NHOM", "tam-ly-nhat", "nghien-cuu", "khan-gia-cung-xem.json")
    assert os.path.isfile(duong_nhom)
    assert ncc.khan_gia_cung_xem_doc(goc, "TL1-T7") == ncc.khan_gia_cung_xem_doc(goc, "TL4-T7")
    assert "TL4-T7" in ncc.khan_gia_cung_xem_doc(goc, "TL1-T7")


def test_cap_nhat_khan_gia_cung_xem_kenh_khong_nhom_dung_kho_rieng(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "DOC-LAP")           # không khai `nhom`
    ban_ghi = giai_ma.cap_nhat_khan_gia_cung_xem(goc, "DOC-LAP", RAW_DAY_DU)
    assert ban_ghi is not None
    assert not os.path.isdir(os.path.join(goc, "CHANNEL", "_NHOM"))
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "DOC-LAP", "nghien-cuu", "khan-gia-cung-xem.json"))


def test_nghien_cuu_chung_khan_gia_cung_xem_doc_ghi_truc_tiep(tmp_path):
    """Hàm đọc/ghi tự nó (không qua giai_ma) — API mà nơi khác có thể tái dùng."""
    goc = str(tmp_path)
    _kenh(goc, "X")
    assert ncc.khan_gia_cung_xem_doc(goc, "X") == {}
    ncc.khan_gia_cung_xem_ghi(goc, "X", {"X": {"nguon": "khan_gia_cung_xem", "kenh_canh_tranh": ["UCabc"]}})
    assert ncc.khan_gia_cung_xem_doc(goc, "X")["X"]["kenh_canh_tranh"] == ["UCabc"]
    # gộp, không mất khoá cũ
    ncc.khan_gia_cung_xem_ghi(goc, "X", {"Y": {"nguon": "khan_gia_cung_xem", "kenh_canh_tranh": ["UCxyz"]}})
    kho = ncc.khan_gia_cung_xem_doc(goc, "X")
    assert set(kho) == {"X", "Y"}


# ───────────────────────────────────── gom.py: hàm tiện ích gộp cả hai ─────


def test_gom_cap_nhat_gio_online_va_khan_gia(tmp_path):
    from core.chi_so_ytb import gom as _gom

    goc = str(tmp_path)
    _kenh(goc, "TL4-T7", "tam-ly-nhat")
    kenh_dir = os.path.join(goc, "CHANNEL", "TL4-T7", "chi-so")
    raw_dich = os.path.join(kenh_dir, "kenh", "kenh-20260929", "raw")
    os.makedirs(raw_dich, exist_ok=True)
    with open(os.path.join(RAW_DAY_DU, os.listdir(RAW_DAY_DU)[0]), encoding="utf-8") as ng:
        noi_dung = ng.read()
    with open(os.path.join(raw_dich, os.listdir(RAW_DAY_DU)[0]), "w", encoding="utf-8") as tep:
        tep.write(noi_dung)

    ra = _gom.cap_nhat_gio_online_va_khan_gia(goc, "TL4-T7", kenh_dir)
    assert ra["gio_online"] is not None
    assert ra["khan_gia_cung_xem"] is not None
    assert os.path.isfile(os.path.join(kenh_dir, "gio-online.json"))


# ───────────────────────────────────── xep_lich.goi_y_khe ──────────────────


def test_goi_y_khe_rong_khi_chua_co_gio_online(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "TL4-T7")
    ra = xep_lich.goi_y_khe(goc, "TL4-T7")
    assert ra["khe_de_xuat"] == []
    assert "ly_do" in ra and ra["ly_do"]


def test_goi_y_khe_de_xuat_truoc_dinh_dung_dot_thu_12_13h(tmp_path):
    """Khe đề xuất phải khiến đợt quét trang chủ đầu tiên (+12–13h sau khi đăng,
    `CHANNEL/TL4-T7/CLAUDE.md` dòng 46) rơi đúng đỉnh khán giả online — khớp với
    gợi ý A/B thật của insight #7: đăng ~05:00 giờ VPS (=07:00 JST)."""
    goc = str(tmp_path)
    _kenh(goc, "TL4-T7")
    chi_so = os.path.join(goc, "CHANNEL", "TL4-T7", "chi-so")
    os.makedirs(chi_so, exist_ok=True)
    giai_ma.cap_nhat_gio_online(RAW_DAY_DU, chi_so)

    ra = xep_lich.goi_y_khe(goc, "TL4-T7")
    assert ra["khe_de_xuat"], "phải có gợi ý khi đã có gio-online.json hợp lệ"
    for khe in ra["khe_de_xuat"]:
        gio = int(khe.split(":")[0])
        # đăng ở giờ này + 12..13h phải rơi vào khung đỉnh (đỉnh VPS ± 1h, bao dung sai số làm tròn)
        dinh = ra["dinh_online_vps"]["gio"]
        khoang_cach = min(min(x, 24 - x) for x in ((gio + d - dinh) % 24 for d in (12, 13)))
        assert khoang_cach <= 1, "khe {0} không khiến đợt quét +12-13h rơi đúng đỉnh {1}h VPS".format(khe, dinh)
    assert "05:00" in ra["khe_de_xuat"]


def test_goi_y_khe_khong_dung_toi_nhip_dang(tmp_path):
    """CHỈ GỢI Ý — không tự đổi `nhip_dang` trong `kenh.yaml`."""
    goc = str(tmp_path)
    d = _kenh(goc, "TL4-T7")
    with open(os.path.join(d, "kenh.yaml"), "a", encoding="utf-8") as tep:
        tep.write('nhip_dang: "12:00, 20:00"\n')
    with open(os.path.join(d, "kenh.yaml"), encoding="utf-8") as tep:
        truoc = tep.read()
    chi_so = os.path.join(goc, "CHANNEL", "TL4-T7", "chi-so")
    os.makedirs(chi_so, exist_ok=True)
    giai_ma.cap_nhat_gio_online(RAW_DAY_DU, chi_so)
    xep_lich.goi_y_khe(goc, "TL4-T7")
    with open(os.path.join(d, "kenh.yaml"), encoding="utf-8") as tep:
        sau = tep.read()
    assert truoc == sau
