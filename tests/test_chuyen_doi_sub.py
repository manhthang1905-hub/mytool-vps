"""Chuyển đổi SUB (12/10/2026): đo sub/1k đúng cặp bản chụp + các đòn bẩy (CTA giữa bài, bình luận, MHKT, mô tả).

Mọi bài chạy trên thư mục tạm, mã video GIẢ, không có tên kênh thật.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

from core import chuyen_doi_sub as cds  # noqa: E402
from core.kenh import Kenh  # noqa: E402

BAY = datetime(2026, 10, 12, 9, 0)


def _ghi_csv(p, cot, hang):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cot)
        w.writeheader()
        for h in hang:
            w.writerow(h)


def _bang(goc, kenh, hang):
    cot = ["Tiêu đề", "Mã video", "Ngày đăng", "Dài", "Lượt xem", "Đăng ký", cds.COT_SUB, cds.COT_XEM, cds.COT_MOC]
    _ghi_csv(os.path.join(goc, "CHANNEL", kenh, "chi-so", "bang-tom-tat.csv"), cot, hang)


# ── 1. Đo ────────────────────────────────────────────────────────────────────

def test_cap_sub_xem_o_trong_khong_phai_so_khong():
    # Ô "Đăng ký" trống (gói join không có sub) → None, KHÔNG phải (0, view mới nhất).
    assert cds.cap_sub_xem({"Đăng ký": "", "Lượt xem": "6788"}) is None
    # Hai cột mới thắng: cặp của CÙNG bản chụp có số đăng ký.
    assert cds.cap_sub_xem({"Đăng ký": "", "Lượt xem": "6788", cds.COT_SUB: "5", cds.COT_XEM: "900"}) == (5, 900)
    # Bảng cũ (chưa có cột mới) mà ô có số → dùng như cũ.
    assert cds.cap_sub_xem({"Đăng ký": "7", "Lượt xem": "1000"}) == (7, 1000)
    assert cds.cap_sub_xem({"Đăng ký": "0", "Lượt xem": ""}) is None


def test_chon_ban_do_sub_lay_ban_co_sub_nhieu_view_nhat():
    class B:
        def __init__(self, moc, views, subs):
            self.moc_gio, self.views, self.subs = moc, views, subs

    ds = [B(22, 28, 0), B(119, 6788, None), B(48, 640, 3), B(None, 500, 2)]
    b = cds.chon_ban_do_sub(ds)
    assert (b.moc_gio, b.views, b.subs) == (48, 640, 3)
    assert cds.chon_ban_do_sub([B(5, 10, None)]) is None


def test_xuat_tom_tat_ghi_cot_cap_sub(tmp_path):
    """Bản 22h (tab tổng quan, có sub) + bản 106h (gói join, KHÔNG sub) → cột mới mang cặp của bản 22h."""
    from core import chi_so_ytb

    kd = tmp_path / "CHANNEL" / "KX" / "chi-so" / "FAKEvid0001"
    for moc, luc, q in (("22h", "2026-10-01T22:00:00Z", {"views": 40, "subs": 1, "impressions": 300}),
                        ("106h", "2026-10-05T10:00:00Z", {"views": 900, "impressions": 4000, "nguon_tong": "join"})):
        (kd / moc / "raw").mkdir(parents=True)
        tho = kd / moc / "raw" / "20261001-000000_tab-reach_yta_web-join_1.json"
        tho.write_text(json.dumps({"captured_at": luc, "response": {}}), encoding="utf-8")
        os.utime(tho, (1.0e9, 1.0e9))              # gói raw CŨ hơn bản giải mã → không giải lại
        q.update(video_id="FAKEvid0001", gio_sau_dang=int(moc[:-1]), tieu_de="video giả", ngay_dang="2026-10-01",
                 phien_giai_ma=2)
        (kd / moc / "tong-quan.json").write_text(json.dumps(q), encoding="utf-8")
    p = chi_so_ytb.xuat_tom_tat("KX", str(tmp_path / "CHANNEL"))
    rows = list(csv.DictReader(io.open(p, encoding="utf-8-sig")))
    assert len(rows) == 1
    r = rows[0]
    assert r["Lượt xem"] == "900" and r["Đăng ký"] == ""
    assert (r[cds.COT_SUB], r[cds.COT_XEM], r[cds.COT_MOC]) == ("1", "40", "22h")


def test_ket_qua_va_bien_tap_dung_cap_sub(tmp_path):
    goc = str(tmp_path)
    _bang(goc, "KX", [
        {"Mã video": "FAKEvid0001", "Lượt xem": "6788", "Đăng ký": "", cds.COT_SUB: "5", cds.COT_XEM: "1000"},
        {"Mã video": "FAKEvid0002", "Lượt xem": "2000", "Đăng ký": "", cds.COT_SUB: "", cds.COT_XEM: ""},
        {"Mã video": "FAKEvid0003", "Lượt xem": "500", "Đăng ký": "2", cds.COT_SUB: "2", cds.COT_XEM: "500"}])
    from core import bien_tap_content
    from core.chien_luoc import ket_qua

    for ham in (ket_qua._sub_theo_video, bien_tap_content._sub_theo_video):  # noqa: SLF001
        ra = ham(goc, "KX")
        assert ra == {"FAKEvid0001": (5.0, 1000.0), "FAKEvid0003": (2.0, 500.0)}, ham
    assert cds.sub_theo_video(goc, "KX")["FAKEvid0001"] == (5.0, 1000.0)


# ── 2. Cài đặt + chia nhánh ─────────────────────────────────────────────────

def _kenh(**kw):
    k = Kenh(ma="KX", ngon_ngu="ja", ky_tu_moi_phut=300)
    k.chuyen_doi_sub = kw
    return k


def test_chia_nhanh_co_dinh_va_xen_deu():
    a = [cds.chia_nhanh("KX", "{0:04d}".format(i), "cta_giua", 0.7) for i in range(1, 41)]
    assert a == [cds.chia_nhanh("KX", "{0:04d}".format(i), "cta_giua", 0.7) for i in range(1, 41)]
    assert 25 <= sum(a) <= 31, sum(a)
    chuoi = max(len(s) for s in "".join("1" if x else "0" for x in a).split("1"))
    assert chuoi <= 2, "nhóm đối chứng phải xen đều, không dồn cục"
    assert cds.chia_nhanh("KX", "abc", "cta_giua", 1.0) is True
    assert cds.chia_nhanh("KX", "abc", "cta_giua", 0.0) is False


def test_quyet_dinh_luot_ghi_mot_lan_chay_lai_giu_nguyen(tmp_path):
    goc, d = str(tmp_path), str(tmp_path / "luot")
    os.makedirs(d)
    k = _kenh(bat=True, cta_giua="ab", binh_luan=True, ti_le_bat=1.0)
    qd = cds.quyet_dinh_luot(goc, k, d, "KX", "0007", bay_gio=BAY)
    assert qd["kenh_bat"] and qd["binh_luan"]["bat"]
    assert (qd["cta_giua"]["bat"], qd["cta_giua"]["che_do"], qd["cta_giua"]["ti_le"]) == (True, "ab", 1.0)
    assert os.path.isfile(os.path.join(d, cds.TEP_LUOT))
    # Đổi cài đặt sau khi đã chốt → chạy lại vẫn đúng nhánh cũ (lời nhắc + khoá chat của lượt không đổi giữa chừng).
    k2 = _kenh(bat=False)
    assert cds.quyet_dinh_luot(goc, k2, d, "KX", "0007", bay_gio=BAY)["cta_giua"]["bat"] is True


def test_ti_le_thich_ung_vong_hoc(tmp_path, monkeypatch):
    assert cds.ti_le_thich_ung(0.7, {"ket": "BẬT thắng", "ti_so": 1.6})[0] == cds.TI_LE_THANG
    assert cds.ti_le_thich_ung(0.7, {"ket": "BẬT thua", "ti_so": 0.6})[0] == cds.TI_LE_THUA
    assert cds.ti_le_thich_ung(0.7, {"ket": "chưa đủ mẫu"})[0] == 0.7
    # quyet_dinh_luot dùng tỉ lệ đã học, ghi lý do.
    monkeypatch.setattr(cds, "danh_gia_ab", lambda goc, k: {"cta_giua": {"ket": "BẬT thua", "ti_so": 0.5}})
    d = str(tmp_path / "luot")
    os.makedirs(d)
    qd = cds.quyet_dinh_luot(str(tmp_path), _kenh(bat=True), d, "KX", "0003", bay_gio=BAY)
    assert qd["cta_giua"]["ti_le"] == cds.TI_LE_THUA and "thua" in qd["cta_giua"]["vi_sao"]
    assert qd["binh_luan"]["ti_le"] == 0.7


def test_kenh_tat_thi_moi_nhanh_tat(tmp_path):
    d = str(tmp_path / "luot")
    os.makedirs(d)
    qd = cds.quyet_dinh_luot(str(tmp_path), _kenh(bat=False), d, "KX", "0001", bay_gio=BAY)
    assert not qd["kenh_bat"] and not cds.nhanh_bat(qd, "cta_giua") and not cds.nhanh_bat(qd, "binh_luan")


def test_auto_bat_theo_tam_ypp(tmp_path, monkeypatch):
    from core import ypp

    monkeypatch.setattr(ypp, "du_bao", lambda goc, kenh, bg=None: {"trang_thai": "dang_len", "ngay_toi": 22.0,
                                                                   "dang_ky": 317, "gio": 4187})
    assert cds.kenh_bat(str(tmp_path), _kenh(), BAY)[0] is True
    monkeypatch.setattr(ypp, "du_bao", lambda goc, kenh, bg=None: {"trang_thai": "dang_len", "ngay_toi": 300.0,
                                                                   "dang_ky": 40, "gio": 90})
    bat, ly_do = cds.kenh_bat(str(tmp_path), _kenh(), BAY)
    assert bat is False and "chưa trong tầm" in ly_do
    monkeypatch.setattr(ypp, "du_bao", lambda goc, kenh, bg=None: {"trang_thai": "dat"})
    assert cds.kenh_bat(str(tmp_path), _kenh(), BAY)[0] is False
    # Bật tay thắng "auto".
    assert cds.kenh_bat(str(tmp_path), _kenh(bat=True), BAY)[0] is True


# ── 3. Luật lời nhắc ────────────────────────────────────────────────────────

QD_BAT = {"phien": 1, "cta_giua": {"bat": True, "che_do": "ab"}, "binh_luan": {"bat": True, "che_do": "ab"},
          "lien_quan": ["video cũ giả một", "video cũ giả hai"]}
QD_TAT = {"phien": 1, "cta_giua": {"bat": False, "che_do": "ab"}, "binh_luan": {"bat": False, "che_do": "ab"}}


def test_luat_dang_ky_vi_tri_va_khong_vao_giay_dau():
    k = _kenh()
    ra = cds.them_luat_dang_ky("Viết.\n\nbản gốc:\n<<COMPETITOR_TRANSCRIPT>>", k, QD_BAT, muc_tieu_kt=6000)
    assert ra.endswith("<<COMPETITOR_TRANSCRIPT>>") and ra.index("LUẬT MỜI ĐĂNG KÝ") < ra.index("bản gốc:")
    for cum in ("25–40%", "1500–2400", "60 giây đầu", "GIÁ TRỊ", "video TIẾP THEO", "video cũ giả một"):
        assert cum in ra, cum
    # Nhánh TẮT: lời nhắc y nguyên (nhóm đối chứng).
    assert cds.them_luat_dang_ky("Viết.\n<<DRAFT>>", k, QD_TAT) == "Viết.\n<<DRAFT>>"
    assert cds.them_luat_dang_ky("A<<LUAT_DANG_KY>>B", k, QD_TAT) == "AB"
    # Bước viết lại phía sau chỉ nhận câu GIỮ.
    g = cds.them_luat_dang_ky("Nắn.\n<<DRAFT>>", k, QD_BAT, giu=True)
    assert "GIỮ ĐÒN BẨY" in g and "LUẬT MỜI ĐĂNG KÝ" not in g and g.endswith("<<DRAFT>>")


def test_auto_khau_doi_luat_4_khi_bat():
    from core import auto_khau as ak

    k = _kenh()
    goc = ak.them_luat_mo_dau("Viết.\n<<COMPETITOR_TRANSCRIPT>>", k)
    assert ak.LUAT_4_CU in goc
    bat = ak._luat_sub(goc, k, QD_BAT, muc_tieu_kt=6000)  # noqa: SLF001
    assert ak.LUAT_4_CU not in bat and "LUẬT MỜI ĐĂNG KÝ bên dưới" in bat and "KHÔNG chào hỏi" in bat
    assert bat.index("LUẬT MỞ ĐẦU") < bat.index("═══ LUẬT MỜI ĐĂNG KÝ") < bat.index("<<COMPETITOR_TRANSCRIPT>>")
    assert ak._luat_sub(goc, k, QD_TAT) == goc  # noqa: SLF001
    assert ak._luat_sub(goc, k, {}) == goc  # noqa: SLF001 — không có quyết định (lỗi/lượt cũ) → như cũ
    # Hàm cũ vẫn nhận tham số mới mà không đổi nết mặc định.
    assert ak.luat_mo_dau(k) == ak.luat_mo_dau(k, cta_giua=False)
    assert "LUẬT MỜI ĐĂNG KÝ" in ak.luat_mo_dau(k, cta_giua=True)


def test_luat_binh_luan():
    khuon = "# PINNED COMMENT\n<<SCRIPT_ENDING>>\nrules"
    assert cds.them_luat_binh_luan(khuon, QD_TAT) == khuon
    ra = cds.them_luat_binh_luan(khuon, QD_BAT)
    assert ra.startswith(khuon) and "ONE short line" in ra and "subscribe" in ra and "No begging, no links" in ra


# ── 4. Đo kịch bản ──────────────────────────────────────────────────────────

def test_do_kich_ban_vi_tri_cau_moi():
    k = _kenh()
    than = "あ" * 3000
    giua = than[:900] + "ここまで見てくださった方は、ぜひチャンネル登録をお願いします。" + than[900:]
    ket = giua + "次回は、この続きをお話しします。チャンネル登録して待っていてください。"
    d = cds.do_kich_ban(ket, k)
    assert d["giua"] and d["ket"] and d["hua_tiep"] and not d["som"]
    som = cds.do_kich_ban("チャンネル登録お願いします。" + than, k)
    assert som["som"] and not som["giua"]
    assert cds.do_kich_ban("", k)["ky_tu"] == 0
    en = cds.do_kich_ban("x" * 2000 + " please subscribe " + "y" * 3000, k)
    assert en["giua"]


def test_ghi_do_kich_ban_luot_cu(tmp_path):
    d = str(tmp_path)
    qd = cds.ghi_do_kich_ban(d, "あ" * 100, _kenh())
    assert qd["phien"] == 0 and qd["do"]["ky_tu"] == 100
    assert json.load(open(os.path.join(d, cds.TEP_LUOT), encoding="utf-8"))["do"]["ky_tu"] == 100


# ── 5. Mô tả: link video liên quan ──────────────────────────────────────────

def test_lien_ket_mo_ta(tmp_path):
    goc = str(tmp_path)
    _bang(goc, "KX", [{"Tiêu đề": "video cũ A", "Mã video": "FAKEvid000A", "Lượt xem": "5000"},
                      {"Tiêu đề": "video cũ B", "Mã video": "FAKEvid000B", "Lượt xem": "800"}])
    k = _kenh(bat=True)
    hoi = []
    moi, ghi = cds.them_lien_ket_mo_ta(goc, k, "video mới", "mô tả\n00:00 mở đầu", lambda de: hoi.append(de) or "2",
                                       bay_gio=BAY)
    assert moi.startswith("mô tả\n00:00 mở đầu\n\n▼ あわせて観たい動画\nvideo cũ B\nhttps://youtu.be/FAKEvid000B")
    assert "FAKEvid000B" in ghi and "video cũ A" in hoi[0]
    # Chạy lại: mô tả đã có link → không nối hai lần.
    assert cds.them_lien_ket_mo_ta(goc, k, "video mới", moi, lambda de: "1", bay_gio=BAY)[0] == moi
    # AI hỏng → video nhiều view nhất (không lọc từ khoá).
    def hong(de):
        raise RuntimeError("x")
    assert "FAKEvid000A" in cds.them_lien_ket_mo_ta(goc, k, "video mới", "mô tả", hong, bay_gio=BAY)[0]
    # Kênh tắt hoặc tắt riêng mục này → giữ nguyên.
    assert cds.them_lien_ket_mo_ta(goc, _kenh(bat=False), "v", "mô tả", lambda de: "1", bay_gio=BAY)[0] == "mô tả"
    assert cds.them_lien_ket_mo_ta(goc, _kenh(bat=True, mo_ta_lien_ket=False), "v", "mô tả", None,
                                   bay_gio=BAY)[0] == "mô tả"


# ── 6. MHKT + A/B + não ─────────────────────────────────────────────────────

def test_phan_loai_mhkt():
    assert cds.phan_loai_mhkt(["Đăng ký: kênh giả", "Video: Phù hợp nhất với người xem"]) == {
        "doc_duoc": True, "dang_ky": True, "video": True, "phu_hop": True}
    thieu = cds.phan_loai_mhkt(["Video: Video đã tải lên gần đây nhất", "Danh sách phát: ds giả"])
    assert thieu["doc_duoc"] and thieu["dang_ky"] is False and thieu["phu_hop"] is False
    assert cds.phan_loai_mhkt(["(có thành phần)"])["dang_ky"] is None
    assert cds.phan_loai_mhkt(["Subscribe: x", "Video: Best for viewer"])["phu_hop"] is True


def test_danh_gia_ab_va_dong_nao(tmp_path):
    goc = str(tmp_path)
    hang, hs_dir = [], tmp_path / "CHANNEL" / "KX" / "ho-so-video"
    hs_dir.mkdir(parents=True)
    for i in range(14):
        vid = "FAKEvid{0:04d}".format(i)
        bat = i % 2 == 0
        hang.append({"Mã video": vid, "Lượt xem": "1000", cds.COT_SUB: "6" if bat else "3", cds.COT_XEM: "1000"})
        (hs_dir / "KX-{0:04d}.json".format(i)).write_text(json.dumps({
            "video_id": vid, "luot": "{0:04d}".format(i),
            cds.KHOA_HO_SO: {"phien": 1, "cta_giua": {"bat": bat, "che_do": "ab"},
                             "binh_luan": {"bat": True, "che_do": "bat"}}}), encoding="utf-8")
    _bang(goc, "KX", hang)
    ab = cds.danh_gia_ab(goc, "KX")
    o = ab["cta_giua"]
    assert (o["bat"]["n"], o["tat"]["n"], o["bat"]["sub_1k"], o["tat"]["sub_1k"]) == (7, 7, 6.0, 3.0)
    assert o["ti_so"] == 2.0 and o["ket"] == "BẬT thắng" and o["khoang"][0] > 1
    assert ab["binh_luan"]["bat"]["n"] == 0, "nhánh không phải A/B không vào phép so"
    (tmp_path / "vm" / "logs").mkdir(parents=True)
    (tmp_path / "vm" / "logs" / "so-video-id.json").write_text(json.dumps({
        "KX/KX-0001": {"video_id": "FAKEvid0001", "mhkt": "ok:mau", "mhkt_doc_lai": "Đăng ký: k | Video: x"},
        "KX/KX-0002": {"video_id": "FAKEvid0002", "mhkt": "ok:nhap", "mhkt_bu_doc_lai": "Video: x | Danh sách phát: y"},
        "KX/KX-0003": {"video_id": "FAKEvid0003", "mhkt": "bo"}}), encoding="utf-8")
    dong = cds.dong_nao(goc, "KX", _kenh(bat=True), bay_gio=BAY)
    chu = "\n".join(dong)
    assert "Sub/1k view" in chu and "video đo được 4,50" in chu
    assert "MHKT có nút Đăng ký 1/3 (thiếu 1, chưa đọc 0, không có 1)" in chu
    assert "BẬT thắng" in chu and "danh sách phát chủ đề: CHƯA khai" in chu


def test_kenh_yaml_doc_khoi_chuyen_doi_sub(tmp_path):
    from core.kenh import doc_kenh, duong_kenh

    d = duong_kenh(str(tmp_path), "KX")
    os.makedirs(d)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write("ma: KX\nngon_ngu: ja\nchuyen_doi_sub:\n  bat: true\n  cta_giua: ab\n  ti_le_bat: 0.5\n")
    k = doc_kenh(str(tmp_path), "KX")
    cd = cds.cai_dat(k)
    assert cd["bat"] is True and cd["cta_giua"] == "ab" and cd["ti_le_bat"] == 0.5 and cd["binh_luan"] == "ab"
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as f:
        f.write("ma: KX\nngon_ngu: ja\n")
    assert cds.cai_dat(doc_kenh(str(tmp_path), "KX")) == cds.MAC_DINH


# ── 7. Máy đăng: MHKT phải có nút Đăng ký ───────────────────────────────────

VM = GOC / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))


def test_may_dang_bo_nguon_thieu_dang_ky_va_danh_sach():
    import may_dang_dom as mdd  # noqa: PLC0415

    so = {"K/1": {"video_id": "FAKEvid0001", "trang_thai": "xac-nhan", "mhkt": "ok:bu",
                  "mhkt_bu_doc_lai": "Video: a | Danh sách phát: b"},
          "K/2": {"video_id": "FAKEvid0002", "trang_thai": "xac-nhan", "mhkt": "ok:mau",
                  "mhkt_doc_lai": "Đăng ký: k | Video: x"},
          "K/3": {"video_id": "FAKEvid0003", "trang_thai": "xac-nhan", "mhkt": "ok"}}
    assert list(mdd.danh_sach_mhkt_thieu_dang_ky(so)) == ["K/1"]
    assert mdd.phan_loai_mhkt(["Đăng ký: k"])["dang_ky"] is True


def test_bu_mhkt_nguon_thieu_dang_ky_thi_dung_mau(tmp_path):
    """Video nguồn có MHKT nhưng THIẾU nút Đăng ký (sổ chưa biết) → đọc hàng trước khi Lưu → huỷ bản nhập → dựng mẫu."""
    import may_dang_dom as mdd  # noqa: PLC0415
    from test_vm_bu_mhkt import K, TrangSuaGia, _may, _muc  # noqa: PLC0415

    class TrangThieuDk(TrangSuaGia):
        def bam(self, x, **kw):
            ra = super().bam(x, **kw)
            if (x.get("khoa") if isinstance(x, dict) else x) == "mhkt_chon_video" and self.soan == "soan":
                self.hang = ["Video: Video đã tải lên gần đây nhất", "Danh sách phát: ds giả"]
            return ra

    tr = TrangThieuDk({"FAKEvid0009": {"dai": 800}}, nguon_co_mhkt={"FAKEnguon09": True})
    m = _may(tmp_path, tr)
    m.so.cap_nhat(K + "/0001", **_muc("FAKEnguon09", "ok"))
    m.so.cap_nhat(K + "/0009", **_muc("FAKEvid0009", "bo"))
    kq = m.bu_mhkt_mot(K + "/0009", "FAKEvid0009")
    assert kq["ket"] == "ok" and kq["mhkt_bu_cach"] == "mau"
    assert "Đăng ký" in m.so.lay(K + "/0009")["mhkt_bu_doc_lai"]
    # Sổ đã biết nguồn thiếu nút → không đưa vào danh sách nguồn nữa.
    m.so.cap_nhat(K + "/0001", mhkt_bu_doc_lai="Video: a | Danh sách phát: b")
    assert "FAKEnguon09" not in [v for v, _t in m._nguon_mhkt()]  # noqa: SLF001
    m.mhkt_bat_buoc_dk = False
    assert "FAKEnguon09" in [v for v, _t in m._nguon_mhkt()]  # noqa: SLF001
    assert list(mdd.danh_sach_mhkt_thieu_dang_ky(m.so.doc())) == [K + "/0001"], "video mới đã có nút; nguồn thì thiếu"


def test_nao_chuong_trinh_co_dong_sub(tmp_path, monkeypatch):
    from core import nao_chuong_trinh as nct

    monkeypatch.setattr(cds, "dong_nao", lambda goc, k, bay_gio=None: ["    Sub/1k view: GIẢ"])
    ra = nct.dong_danh_muc(str(tmp_path), ["KX"], BAY)
    assert "    Sub/1k view: GIẢ" in ra
