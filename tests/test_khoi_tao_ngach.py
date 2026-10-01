"""Khởi tạo ngách bằng AI (`core/khoi_tao_ngach.py`) + chạy khô ĐẦU–CUỐI một ngách giả "nấu ăn tại gia · VN · vi".

Mọi lời gọi tốn tiền đều là đồ giả: một CLIENT GIẢ trả lời mọi lượt AI đi qua đúng đường thật
(`goi_van_ban` → `client.request("POST", "/v1/chat/completions")`) và GHI LẠI từng lời nhắc; tìm
YouTube / quét kênh là hàm giả trả dữ liệu cố định. Chỉ ghi trong `tmp_path` (khuôn `_KHUON` chép từ
kho) — không đụng CHANNEL thật, workspace, vm/.

Bài đầu–cuối chứng minh: khởi tạo → hộp thư đối thủ → chuỗi Một nút (chốt đối thủ theo nghĩa, kiểm
ngách bằng LLM, quét content) → `ung_vien_xep_hang` CHỌN ĐƯỢC NGUỒN bằng VPH (giai đoạn "moi") →
`_chon_nguon` (biên tập viên AI) → `chay_mot_ngay(che_do="thu")` lập lượt sản xuất; và KHÔNG lời
nhắc nào gửi đi còn mang tâm lý / Nhật / chữ Nhật.
"""

from __future__ import annotations

import datetime as dt
import functools
import io
import json
import os
import re
import shutil
import sys

import pytest

from core import khoi_tao_ngach as ktn

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = "BEP-1"
CHU_JA = re.compile(r"[぀-ヿ㐀-鿿]")


# ── dữ liệu giả ───────────────────────────────────────────────────────────────────────────────────

HO_SO = {
    "mo_ta_ngach": "Nấu ăn tại gia tiếng Việt — công thức món nhà làm từng bước",
    "dang_thang": "công thức một món cụ thể, làm theo là ra đúng món",
    "mo_ta_cho_loc_ai": "Thuộc ngách: video dạy nấu MỘT món cụ thể ở bếp nhà. Không thuộc ngách: mukbang, review quán, "
                        "vlog du lịch, tin tức.",
    "luat_chon": ["Chỉ chọn video dạy nấu một món cụ thể; review quán/ăn thử là lệch ngách."],
    "tieu_chi_doi_thu": ["kênh nói tiếng Việt", "nội dung chính là dạy nấu món nhà làm",
                         "hợp khán giả Việt Nam nấu ở nhà", "video dài có lời đọc"],
    "khan_gia_mo_ta": "người Việt 25–55 tuổi nấu cơm nhà, xem trên điện thoại",
    "tep_khan_gia": [{"ma": "1", "ten": "Người mới tập nấu, sợ hỏng món", "ten_ngan": "Mới tập nấu"},
                     {"ma": "nau-lau-nam", "ten": "Người nấu lâu năm tìm mẹo nhanh", "ten_ngan": "Nấu lâu năm"}],
    "cum": {"Món mặn": {"ten": "Món mặn", "tu": ["kho", "xào", "chiên"]},
            "banh": {"ten": "Bánh", "tu": ["bánh"]}},
    "ngach": {"tu": ["nấu ăn", "công thức"], "tu_lac": ["mukbang", "review quán"]},
    "tu_manh": ["cách làm", "công thức"], "tu_yeu": ["món", "nấu"],
    "tu_loai_tru": ["review phim", "bóng đá"], "ten_kenh_loai_tru": ["tóm tắt"],
    "handle_loai_tru": ["reup"], "tu_kenh_hien_nhien": ["tin tức"], "handle_hien_nhien": ["news"],
    "tu_tieu_de_hien_nhien": ["trực tiếp"], "tu_tuoi": [], "tu_chan_dung": [], "tu_cach_lam": [],
    "mau_tieu_de": "kênh YouTube nấu ăn tại gia tiếng Việt",
    "mo_ta_kenh_cho_ai": "Kênh của tôi làm lại công thức nấu ăn nhà làm cho khán giả Việt Nam.",
    "dang_thang_cho_ai": "công thức một món cụ thể",
    "luat_kenh_nguon": {"dung": "dạy nấu từng món", "gan": "có dạy nấu nhưng lẫn vlog", "lac": "mukbang, review"},
    "mo_ta_phan_cum": "tiếng Việt (ngách nấu ăn)", "nhan_the_loai_mau": "",
    "vi_du_phan_cum": "(cách luộc trứng không phải cụm bánh)",
    "luat_nan_khuon": ["Viết lại theo đúng hình dạng các tiêu đề mẫu: tên món + lời hứa kết quả.",
                       "Giữ ngoặc/nhãn đầu câu nếu đó là mồi câu."],
    "the_loai_en": "home cooking",
    "tu_khoa_tim": ["cách làm thịt kho", "món ngon mỗi ngày", "nấu ăn tại nhà"],
    "giong_van": "Vietnamese — warm, natural, conversational",
    "ten_kenh_goi_y": "Bếp Nhà Mình",
    "thi_truong": {"mui_gio": "Asia/Ho_Chi_Minh", "gio_dang_goi_y": "19:30", "quy_mo": "nho",
                   "ctr_trang_chu_muc_tieu": 5.5},
    "bia_chuan_ngach": {"so_bia_mau": 120, "chu": {"mau_chinh": ["vang", "trang"], "tu_khoa_mau_khac": "do",
                                                   "so_tang": [2, 3]},
                        "nen": {"loai": "canh_minh_hoa", "anh_sang": "am"}, "nhan_vat": {"bieu_cam_ro": True}},
}

STYLE = {k: "{0} for Vietnamese home cooks (rewritten)".format(k) for k in ktn.KHOA_STYLE_VIET_LAI}
STYLE["cultural_metaphors"] = "joy: steam rising from a pot | worry: a burnt pan"


def _so_muc(text: str, mau: str = r"(?m)^\s*(\d+)\. ") -> int:
    yeu = text.split("═══ YÊU CẦU ═══")[-1]
    return len(set(re.findall(mau, yeu))) or 1


class ClientGia:
    """Thay ví ShopAPI: trả lời mọi lượt AI theo loại đề bài, ghi lại từng lời nhắc."""

    api_key = None  # `goi_van_ban._client_khong_tu_thu_lai` dựng client em không được → dùng chính nó

    def __init__(self) -> None:
        self.loi_nhac: list = []

    def request(self, method, path, json=None, idempotency_key=None, **kw):  # noqa: A002 — giống SDK
        msgs = (json or {}).get("messages") or []
        text = "\n".join(m["content"] if isinstance(m.get("content"), str)
                         else " ".join(x.get("text", "") for x in m["content"] if isinstance(x, dict))
                         for m in msgs)
        self.loi_nhac.append(text)
        return {"choices": [{"message": {"content": self._tra(text)}}]}

    def _tra(self, t: str) -> str:
        import json as _j

        if "dựng HỒ SƠ NGÁCH" in t:
            return _j.dumps(HO_SO, ensure_ascii=False)
        if "VIẾT LẠI nó cho kênh mới" in t:
            goc = t.split("=== LỜI NHẮC GỐC", 1)[1].split("===\n", 1)[1]
            return "(bản cho ngách nấu ăn tại gia)\n" + goc.replace("psychology", "home cooking")
        if "Viết lại 8 khoá phong cách" in t:
            return _j.dumps(STYLE, ensure_ascii=False)
        if "chọn ĐỐI THỦ để nghiên cứu" in t:
            return _j.dumps({"ket": "doi_thu", "diem": 85, "ly_do": "dạy nấu từng món", "tuyen": ["món mặn"],
                             "khac": ""}, ensure_ascii=False)
        if "kiểm DANH BẠ ĐỐI THỦ" in t or "Lượt kiểm trước đã xếp" in t:
            n = len(re.findall(r"(?m)^(\d+)\. Kênh:", t))
            return _j.dumps({str(i): {"k": "giu", "ly_do": "đúng ngách nấu ăn"} for i in range(1, n + 1)},
                            ensure_ascii=False)
        if "Bạn lọc NGUỒN" in t:
            return _j.dumps({str(i): "dung" for i in range(1, _so_muc(t) + 1)})
        if "Bạn gán mỗi tiêu đề video" in t:
            return _j.dumps({str(i): {"ma": "t1", "do_tin": 90} for i in range(1, _so_muc(t) + 1)})
        if "Một bộ LUẬT CHỮ" in t:
            return _j.dumps({str(i): "luat" for i in range(1, _so_muc(t) + 1)})
        if "BIÊN TẬP VIÊN NỘI DUNG" in t:
            n = max([int(x) for x in re.findall(r"\bU(\d+)\b", t)] or [1])
            return _j.dumps({"nhan_dinh": "kênh mới, cần nguồn đang nổ", "chon": [
                {"u": 1, "ly_do": "nguồn đột biến", "vi_sao_no": "món quen", "chuyen_duoc": "đúng tệp",
                 "ctr": 5.5, "avd_giay": 300, "ket_cuc": "thắng", "rui_ro": "ít", "giup_ypp": "kéo sub"}],
                "con_lai": [], "loai": {}, "cham": {str(i): ["TOT" if i == 1 else "TAM", 80] for i in range(1, n + 1)}},
                ensure_ascii=False)
        return "{}"


BAY_GIO = dt.datetime.now()
NGAY = (BAY_GIO.date() - dt.timedelta(days=2)).isoformat()
KENH_NGUON = {
    "UCbepA000000000000000001": ("Bếp Nhà A", [("saoSAOsao01", "Cách làm thịt kho trứng mềm thơm không bị đắng", 30000),
                                               ("aaaaaaaaa01", "Canh chua cá lóc miền Tây", 2000),
                                               ("aaaaaaaaa02", "Rau muống xào tỏi xanh giòn", 2400),
                                               ("aaaaaaaaa03", "Cá kho tộ đậm đà", 1800)]),
    "UCbepB000000000000000002": ("Bếp Nhà B", [("bbbbbbbbb01", "Chè đậu xanh nước cốt dừa", 1500),
                                               ("bbbbbbbbb02", "Sinh tố bơ sánh mịn", 1600),
                                               ("bbbbbbbbb03", "Bánh flan mềm mịn tại nhà", 1700)]),
}


def _tim_gia(q, *, limit=20, lang=""):
    from core.youtube import SearchHit

    ra = []
    for cid, (ten, vids) in KENH_NGUON.items():
        for ma, td, view in vids[:2]:
            ra.append(SearchHit(video_id=ma, title=td, url="https://www.youtube.com/watch?v=" + ma, views=view,
                                channel_name=ten, channel_id=cid))
    ra.append(SearchHit(video_id="phimPHIM001", title="Review phim hay nhất", views=90000,
                        channel_name="Phim Hay", channel_id="UCphim00000000000000003"))
    return ra


def _kenh_gia(link: str):
    from core.youtube import Channel, Video

    for cid, (ten, vids) in KENH_NGUON.items():
        if cid in link:
            return Channel(input_url=link, name=ten, channel_id=cid, channel_url=link, subscribers=12000,
                           videos=[Video(video_id=ma, title=td, url="https://www.youtube.com/watch?v=" + ma,
                                         views=v, duration_s=900, upload_date=NGAY, channel_name=ten,
                                         channel_id=cid) for ma, td, v in vids], complete=True)
    return Channel(input_url=link, name="?", channel_url=link)


def _lay_kenh(link, **kw):
    return _kenh_gia(link)


def _thu_thap(inputs, **kw):
    return [_kenh_gia(v) for _k, v in inputs], []


def _goc(tmp_path) -> str:
    goc = str(tmp_path / "MyTool")
    shutil.copytree(os.path.join(GOC_KHO, "CHANNEL", "_KHUON"), os.path.join(goc, "CHANNEL", "_KHUON"))
    return goc


def _anh_gia(prompt: str, dich: str) -> str:
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    with open(dich, "wb") as tep:
        tep.write(b"\x89PNG\r\n\x1a\n" + b"0" * 2000)
    return dich


def _yc(**thay) -> ktn.YeuCau:
    tham = dict(chu_de="nấu ăn tại gia", quoc_gia="VN", ngon_ngu="vi",
                kenh_mau=["https://www.youtube.com/@bepnhaA"], tu_khoa=["món ngon"], ma_kenh=K)
    tham.update(thay)
    return ktn.YeuCau(**tham)


def _mot_nut_gia(client):
    from core import mot_nut
    from core.doi_thu import lay_du_lieu

    def chay(goc, kenh, *, client=None, on_log=None, cancel=None, **kw):
        return mot_nut.chay(goc, kenh, client=client, lay_kenh=_lay_kenh,
                            lay_du_lieu=functools.partial(lay_du_lieu, thu_thap=_thu_thap),
                            on_log=on_log, cancel=cancel)
    return chay


@pytest.fixture(autouse=True)
def _tat_cua_ngung_hoat_dong(monkeypatch):
    from core import kiem_ngach_doi_thu as kn
    monkeypatch.setattr(kn, "NGAY_IM", 10 ** 6)


def _khoi_tao(goc, client, **thay):
    return ktn.khoi_tao(goc, _yc(**thay), client=client, tim=_tim_gia, lay_kenh=_lay_kenh, tao_anh=_anh_gia,
                        chay_mot_nut=_mot_nut_gia(client), log=lambda m: None)


# ── từng mảnh ────────────────────────────────────────────────────────────────────────────────────


def test_chuan_hoa_ho_so_ma_tep_va_bo_tu_khong_roi_ve_tieng_nhat():
    hs = ktn.chuan_hoa_ho_so(HO_SO, _yc().chuan())
    ma = [t["ma"] for t in hs["tep_khan_gia"]]
    assert ma[0] == "moi-tap-nau" and "1" not in ma, "mã số trơn đụng mã tệp tâm lý Nhật → slug"
    assert hs["tu_tuoi"] == [ktn.KHONG_KHOP], "bộ từ rỗng phải chặn đường lùi về chữ Nhật"
    assert hs["thi_truong"]["bac_lam_tron_view"][0] == {"duoi": 1000, "bac": 1}
    assert hs["thi_truong"]["mui_gio"] == "Asia/Ho_Chi_Minh" and hs["thi_truong"]["bac_view_manh"] == 30000
    assert hs["bia_chuan_ngach"]["so_bia_mau"] == 0, "chuẩn bìa do AI ước — chưa đo"
    assert "mon-man" in hs["cum"] and hs["chu_de_con_mac_dinh"] is False


def test_kiem_loi_nhac_chan_ban_mat_cho_dien_hay_dinh_dang():
    cu = "Viết bằng <<NGON_NGU>>.\nTITLE: x\n{\"chon\": \"A\"}\n`portrait_main`"
    assert ktn.kiem_loi_nhac(cu, cu + " thêm") == ""
    assert "NGON_NGU" in ktn.kiem_loi_nhac(cu, "Viết bằng tiếng Việt.\nTITLE: x\n{\"chon\": 1}\n`portrait_main`")
    assert "khoá JSON" in ktn.kiem_loi_nhac(cu, "Viết bằng <<NGON_NGU>>.\nTITLE: x\n`portrait_main`")


def test_gio_dang_doi_sang_gio_vps():
    # 19:30 giờ Việt Nam → giờ VPS: VPS chạy UTC+7 thì giữ nguyên; luôn là HH:MM hợp lệ.
    gio = ktn._gio_vps("19:30", "VN", "Asia/Ho_Chi_Minh")
    assert re.match(r"^\d{2}:\d{2}$", gio)
    lech = (dt.datetime.now().astimezone().utcoffset().total_seconds() / 3600.0)
    if lech == 7:
        assert gio == "19:30"


def test_che_do_thu_khong_ghi_gi_khong_goi_gi(tmp_path):
    goc = _goc(tmp_path)
    truoc = sorted(os.listdir(os.path.join(goc, "CHANNEL")))
    client = ClientGia()
    kq = ktn.khoi_tao(goc, _yc(thu=True), client=client, tim=lambda *a, **k: pytest.fail("không được tìm"),
                      tao_anh=lambda *a: pytest.fail("không được tạo ảnh"), log=lambda m: None)
    assert client.loi_nhac == [], "chế độ thử không được gọi AI"
    assert sorted(os.listdir(os.path.join(goc, "CHANNEL"))) == truoc, "chế độ thử không được ghi gì"
    assert kq.thu and set(ktn.CAN_VIET_LAI) <= set(kq.loi_nhac_viet_lai)


def test_khong_co_khuon_kenh_thi_bao_ro(tmp_path):
    goc = str(tmp_path / "MyTool")
    os.makedirs(os.path.join(goc, "CHANNEL", "_KHUON"))
    with pytest.raises(RuntimeError, match="khuôn kênh"):
        ktn.khoi_tao(goc, _yc(), client=ClientGia(), tim=_tim_gia, log=lambda m: None)


# ── đầu–cuối ─────────────────────────────────────────────────────────────────────────────────────


def test_khoi_tao_day_du_roi_chay_kho_toi_chon_nguon_va_lap_luot(tmp_path, capsys):
    from core import doi_thu_kenh as so
    from core import tu_chay
    from core.chien_luoc import ngu_canh
    from core.ho_so_ngach import doc_ngach, la_ngach_mac_dinh
    from core.kenh import doc_kenh, doc_yaml, kiem_kenh

    goc = _goc(tmp_path)
    client = ClientGia()
    kq = _khoi_tao(goc, client)

    # a) hồ sơ ngách
    hs = doc_ngach(goc, K)
    assert hs.co() and not la_ngach_mac_dinh(hs) and hs.thi_truong["quoc_gia"] == "VN"
    assert hs.tu_khoa_tim and hs.tieu_chi_doi_thu and hs.luat_nan_khuon and hs.the_loai_en == "home cooking"
    # b) kênh
    k = doc_kenh(goc, K)
    cai = doc_yaml(os.path.join(goc, "CHANNEL", K, "kenh.yaml"))
    assert k.ngon_ngu == "vi" and cai["nhom"] == "nau-an-tai-gia-vn" and cai["tep"] == "moi-tap-nau"
    assert cai["chien_luoc"] == "tu_dong" and cai["de_bai_bien_tap"] == "gon"
    assert cai["tu_chay"] is False and int(cai["ngan_sach_ngay"]) == 0 and cai["tu_duyet"] is False
    assert int(cai["ky_tu_moi_phut"]) == 832 and cai["chu_bia_hoa"] is True
    assert kiem_kenh(k) and all("giọng đọc" in x.lower() for x in kiem_kenh(k)), "chỉ còn thiếu giọng đọc"
    mau = os.path.join(goc, "CHANNEL", "_KHUON", "kenh-mau", "prompt")
    for ten in os.listdir(mau):
        moi = io.open(os.path.join(goc, "CHANNEL", K, "prompt", ten), encoding="utf-8").read()
        cu = io.open(os.path.join(mau, ten), encoding="utf-8").read()
        assert (moi != cu) == (ten in ktn.CAN_VIET_LAI), ten
    st = doc_yaml(os.path.join(goc, "CHANNEL", K, "style.yaml"))
    assert st["audience_language"].endswith("(rewritten)") and st["image_style"]
    assert os.path.isfile(os.path.join(goc, "CHANNEL", K, "nv", "nv1.png"))
    assert os.path.isfile(os.path.join(goc, "CHANNEL", K, "KHOI-TAO.md"))
    ch_v7 = json.load(io.open(os.path.join(so.thu_muc_nghien_cuu(goc, K), "cong-thuc-v7.json"), encoding="utf-8"))
    assert ch_v7["tep"] == "moi-tap-nau"
    # c) nghiên cứu: kênh mẫu + tìm kiếm vào hộp thư; "Phim Hay" bị loại theo bộ từ CỦA NGÁCH
    hop = so.doc_doi_thu(goc, K)
    assert "UCbepA000000000000000001" in hop and "UCphim" not in hop and "@bepnhaA" in hop
    from core import danh_ba_doi_thu as db
    assert any("UCbepA" in l for l in db.dang_theo_doi(goc, K)), kq.nghien_cuu
    cot, hang = so.doc_bang(goc, K)
    assert len(hang) >= 5, "quét content phải dựng kho nguồn"
    # Hôm sau: mắt cào gửi gói trang chủ / trang tìm kiếm → lượt Một nút lọc THEO NGHĨA bằng đề bài của ngách.
    from core.chi_so_ytb.tram import Tram
    Tram(goc=goc).nhan_trang_chu(K, [{"ma": "ccccccccc01", "tieu_de": "Cách làm gà rang muối giòn rụm",
                                       "ten_kenh": "Bếp Nhà C", "link_kenh": "https://www.youtube.com/@bepC",
                                       "short": False, "vi_tri": 1, "luot": 1, "ke": "tìm: món ngon mỗi ngày"}])

    def _tra(ma, lang="", cancel=None):
        return {"tieu_de": "Cách làm gà rang muối giòn rụm", "ten_kenh": "Bếp Nhà C",
                "link_kenh": "https://www.youtube.com/@bepC", "luot_xem": "5000", "dang": NGAY, "dai": "15:00",
                "short": False, "tags": ["nấu ăn"], "mo_ta": ""}
    from core import mot_nut
    from core.doi_thu import lay_du_lieu
    mot_nut.chay(goc, K, client=client, tra_video=_tra, lay_kenh=_lay_kenh,
                 lay_du_lieu=functools.partial(lay_du_lieu, thu_thap=_thu_thap))
    assert any("Bạn lọc NGUỒN cho một kênh YouTube tiếng Việt" in t for t in client.loi_nhac), \
        "lọc trang chủ phải dùng đề bài của ngách (không phải đề bài tâm lý Nhật)"
    # d) giai đoạn "moi" → VPH (+ thăm dò)
    nc = ngu_canh.dung(goc, K, co_v7=tu_chay.co_cau_hinh_v7(goc, K))
    assert nc.giai_doan == "moi"
    nhat_ky: list = []
    ds = tu_chay.ung_vien_xep_hang(goc, K, tu_chay.co_cau_hinh_v7(goc, K), set(), log=nhat_ky.append)
    assert ds and ds[0]["ma"] == "saoSAOsao01" and ds[0].get("cong_thuc") in ("vph", "mot_nut"), nhat_ky
    # biên tập viên AI chốt nguồn (đề bài gọn theo ngách)
    goi_chat = tu_chay._dung_goi_chat_mac_dinh(client, lambda m: None, None)
    nguon = tu_chay._chon_nguon(goc, K, False, set(), None, None, nhat_ky.append, goi_chat=goi_chat)
    assert nguon and nguon["ma"] == "saoSAOsao01", nhat_ky[-15:]
    # lập lượt sản xuất ở chế độ thử (không tốn ví)
    ket = tu_chay.chay_mot_ngay(goc, K, che_do="thu", chay_mot_nut=lambda *a, **kw: None,
                                video_da_lam_nhom=lambda g, m: set(), tieu_de_da_lam_nhom=lambda g, m: [],
                                on_log=lambda m: None)
    assert ket["ok"] and ket["run"] and ket["run"]["nguon"]["ma"], ket["tom_tat"]

    # Không lời nhắc nào gửi đi còn mang ngách cũ (trừ VÍ DỤ có chủ đích trong đề bài khởi tạo/viết lại).
    lech = []
    for t in client.loi_nhac:
        if "dựng HỒ SƠ NGÁCH" in t or "VIẾT LẠI nó cho kênh mới" in t or "Viết lại 8 khoá phong cách" in t:
            continue
        m = CHU_JA.search(t) or re.search(r"tâm lý|tiếng Nhật|khán giả Nhật|người Nhật|psycholog|Japanese", t, re.I)
        if m:
            lech.append("…{0}…  ⟵ trong lời nhắc: {1}".format(t[max(0, m.start() - 120):m.end() + 60], t[:80]))
    tom = "\n[chạy khô nấu ăn VN] {0} lượt AI · {1} dòng kho nguồn · ứng viên đầu: {2} ({3}) · lượt {4}".format(
        len(client.loi_nhac), len(hang), ds[0]["tieu_de"], ds[0].get("cong_thuc") or ds[0].get("nguon"),
        ket["run"]["ma_luot"])
    with capsys.disabled():
        ma = getattr(sys.stdout, "encoding", None) or "utf-8"   # console cp1252 không in nổi tiếng Việt
        print(tom.encode(ma, "replace").decode(ma, "replace"))
    assert not lech, "lời nhắc còn cứng tâm lý/Nhật:\n" + "\n---\n".join(lech[:3])


def test_chay_lai_dung_lai_ho_so_va_nho_dem_ai(tmp_path):
    goc = _goc(tmp_path)
    client = ClientGia()
    _khoi_tao(goc, client, bo_nghien_cuu=True)
    so_luot = len(client.loi_nhac)
    # Đổi chủ đề CHÍNH kênh ấy, cùng nhóm: hồ sơ dùng lại, lời nhắc viết lại lấy từ nhớ đệm — 0 lượt AI mới.
    _khoi_tao(goc, client, bo_nghien_cuu=True, doi_chu_de=True)
    assert len(client.loi_nhac) == so_luot, "chạy lại không được trả tiền lần hai cho cùng câu hỏi"
    cu = os.path.join(goc, "CHANNEL", K, "khoi-tao-cu")
    assert os.path.isdir(cu) and os.listdir(cu), "đổi chủ đề phải cất bản cũ"


def test_tram_giao_cum_tim_kiem_xoay_vong_va_rong_cho_ngach_mac_dinh(tmp_path):
    from core.chi_so_ytb.tram import Tram

    goc = _goc(tmp_path)
    _khoi_tao(goc, ClientGia(), bo_nghien_cuu=True)
    tram = Tram(goc=goc)
    a = tram.can_tim_kiem(K, hom_nay=dt.date(2026, 10, 1))["tu_khoa"]
    b = tram.can_tim_kiem(K, hom_nay=dt.date(2026, 10, 2))["tu_khoa"]
    assert len(a) == 3 and a != b
    os.makedirs(os.path.join(goc, "CHANNEL", "TL9"))
    io.open(os.path.join(goc, "CHANNEL", "TL9", "kenh.yaml"), "w", encoding="utf-8").write("ma: TL9\n")
    assert tram.can_tim_kiem("TL9")["tu_khoa"] == [], "kênh không có hồ sơ ngách → không tìm gì (như cũ)"
    assert tram.ngon_ngu_kenh(K) == "vi"
    assert tram.can_lay_loi_thoai(K).get("ngon_ngu") == "vi"


def test_may_cmt_lay_ngon_ngu_tu_kenh_yaml(tmp_path):
    import importlib.util

    duong = os.path.join(GOC_KHO, "vm", "may_cmt.py")
    spec = importlib.util.spec_from_file_location("may_cmt_thu", duong)
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, "CHANNEL", "K1"))
    io.open(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"), "w", encoding="utf-8").write('ngon_ngu: "vi"\n')
    m = importlib.util.module_from_spec(spec)
    # Không chạy phần khởi tạo thư mục của module trên vm/ thật: đọc đúng hai hàm thuần cần soi.
    src = io.open(duong, encoding="utf-8").read()
    i, j = src.index("#: Ma ngon ngu kenh.yaml"), src.index("def process_channel")
    ns = {"os": os, "re": re, "BASE_DIR": os.path.join(goc, "vm"),
          "LANG_MAP": {7: "Japanese", 2: "Vietnamese"}}
    exec(compile(src[i:j], duong, "exec"), ns)  # noqa: S102 — chỉ hai hàm thuần
    assert ns["channel_language"]("K1") == "Vietnamese", "kenh.yaml thắng đuôi tên kênh"
    assert ns["channel_language"]("TL1-T7") == "Japanese", "không có kenh.yaml → nếp cũ -T<n>"
    assert ns["channel_language"]("ABC") is None
    del m
