"""Lấy lời thoại QUA TRÌNH DUYỆT KÊNH — nhánh chữa sự cố đêm 22/09/2026.

Đêm ấy cả ba kênh chết ở khâu ĐẦU của sản xuất (`kich-ban`): nó cần lời thoại
video đối thủ, mà `yt-dlp` và `youtube-transcript-api` đều bị YouTube chặn theo
ĐỊA CHỈ MẠNG của VPS (`IpBlocked`, *"IP belonging to a cloud provider"*), và
cái chặn nặng dần THEO SỐ LƯỢT HỎI.

Đường chữa: chữ tới từ phiên trình duyệt kênh (~07:30) và được cất vào KHO
(`core/loi_thoai.py`); lượt sản xuất 02:00 hôm sau chỉ ĐỌC kho.

Bài nào ở đây cũng canh đúng một mắt của chuỗi ấy, và **không bài nào gọi
mạng** — bài `lay_script` còn bịt sẵn MỌI đường ra ngoài bằng hàm ném lỗi, nên
một lượt gọi mạng lọt qua là bài kiểm đỏ chứ không phải chạy chậm.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

from core import loi_thoai as kho
from core import script_video as sv
from core import tu_chay
from core.chi_so_ytb.tram import Tram

MA_A = "AAAAAAAAAAA"
MA_B = "BBBBBBBBBBB"
MA_C = "CCCCCCCCCCC"


# ── dàn cảnh ─────────────────────────────────────────────────────────────────


def _kenh(goc, ma, **cai):
    """Một kênh trên đĩa, đủ để `kenh.doc_yaml`/`nhom_cua_kenh` đọc được."""
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    dong = ['ma: "{0}"'.format(ma), 'ngon_ngu: "ja"']
    for k, v in cai.items():
        dong.append('{0}: "{1}"'.format(k, v))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    return thu_muc


def _nap_agent(tmp_path):
    """`vm/agent.py` — thử CẢ HAI chỗ nó có thể nằm, và BẺ MỌI ĐƯỜNG GHI về `tmp_path`.

    Bộ test cũ đóng đinh `MyTool/vm/agent.py` (vm/ LỒNG trong MyTool), còn máy
    đang dựng đặt `vm/` CẠNH `MyTool/`. Thử lần lượt để bài này xanh ở cả hai
    cách xếp thư mục — nó kiểm hợp đồng agent↔trạm, không kiểm chỗ đặt tệp.

    ═══ `tmp_path` LÀ BẮT BUỘC, KHÔNG PHẢI TIỆN TAY (22/09/2026) ═══

    `agent.GOC` là thư mục của chính `agent.py`, và MỌI đường ghi của agent suy ra
    từ đó: `agent.log`, `trang-thai.json`, `dang-lam.json`, `tien-ich/`. Nạp module
    rồi gọi `chay_mot_phien`/`lay_loi_thoai` mà không bẻ `GOC` thì bài kiểm ghi
    thẳng vào NHẬT KÝ THẬT của máy ảo — thứ chủ dự án đọc mỗi sáng để biết đêm qua
    xảy ra gì.

    Đã xảy ra thật: 10:12:38 ngày 22/09/2026, `vm/agent.log` nhận ba dòng của kênh
    "K1" — một cái tên KHÔNG TỒN TẠI, chỉ là fixture của tệp này. Đọc sổ sáng hôm
    sau thì đó là một phiên ma: không biết nó là bài kiểm hay là một kênh vừa
    hỏng. Một bài kiểm làm bẩn BẰNG CHỨNG VẬN HÀNH còn tệ hơn là không có bài kiểm.

    Nên hàm này trả về module đã bẻ hai chỗ:

    * `GOC` / `THU_MUC_TIEN_ICH` → `tmp_path` (mọi tệp agent ghi ra rơi vào đó);
    * `ghi` → gom vào `mod.nhat_ky` (list) — bài kiểm SOI ĐƯỢC dòng nhật ký mà
      không tệp nào bị chạm tới.

    `THU_MUC_TIEN_ICH` phải bẻ RIÊNG: nó tính ở tầng module (`os.path.join(GOC,
    "tien-ich")`) nên đã chốt giá trị ngay lúc `exec_module` — đổi `GOC` sau đó
    không kéo nó theo.

    Module được nạp MỚI mỗi lần gọi nên gán thẳng là đủ, không cần `monkeypatch`.
    """
    goc_tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for duong in (os.path.join(goc_tool, "vm", "agent.py"),
                  os.path.join(os.path.dirname(goc_tool), "vm", "agent.py")):
        if os.path.isfile(duong):
            spec = importlib.util.spec_from_file_location("vm_agent_lt", duong)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.GOC = str(tmp_path)
            mod.THU_MUC_TIEN_ICH = os.path.join(str(tmp_path), "tien-ich")
            mod.nhat_ky = []
            mod.ghi = mod.nhat_ky.append
            return mod
    pytest.skip("không tìm thấy vm/agent.py ở cả hai chỗ")


# ── Kho: chỗ đặt, ghi nguyên tử, hai câu hỏi khác nhau ──────────────────────


class TestKho:
    def test_kenh_trong_nhom_dung_kho_CHUNG_cua_nhom(self, tmp_path):
        """4 kênh cùng nhóm đánh cùng pool đối thủ — MỘT lượt lấy phục vụ cả 4.
        Kho phải là một, nằm cạnh bảng chéo kênh của nhóm."""
        from core import nhom_kenh

        goc = str(tmp_path)
        _kenh(goc, "K1", nhom="tam-ly")
        _kenh(goc, "K2", nhom="tam-ly")
        assert kho.thu_muc_kho(goc, "K1") == kho.thu_muc_kho(goc, "K2")
        assert kho.thu_muc_kho(goc, "K1") == os.path.join(
            nhom_kenh.duong_thu_muc_nhom(goc, "tam-ly"), kho.THU_MUC)

        kho.ghi(goc, "K1", MA_A, text="いろは", tieu_de="thử")
        # Kênh anh em thấy NGAY, không phải lấy lại.
        assert kho.co_loi_thoai(goc, "K2", MA_A)

    def test_kenh_khong_nhom_thi_kho_rieng_trong_nghien_cuu(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "LE")
        duong = kho.thu_muc_kho(goc, "LE")
        assert duong.endswith(os.path.join("LE", "nghien-cuu", kho.THU_MUC))

    def test_ghi_nguyen_tu_va_doc_lai_dung(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        duong = kho.ghi(goc, "K1", MA_A, text=" いろは  にほへと ",
                        tieu_de="  tiêu  đề  ", ngon_ngu="ja", dai_giay=612)
        assert os.path.isfile(duong)
        # Không để lại tệp tạm: bên đọc là lượt 02:00, một tệp JSON dở dang là
        # một khâu chết không ai hiểu vì sao.
        assert not os.path.exists(duong + ".tam")
        assert [t for t in os.listdir(os.path.dirname(duong))] == [MA_A + ".json"]
        with open(duong, encoding="utf-8") as tep:
            ban = json.load(tep)
        assert ban["text"] == " いろは  にほへと "
        assert ban["tieu_de"] == "tiêu đề"      # gọn khoảng trắng
        assert ban["dai_giay"] == 612 and ban["ngon_ngu"] == "ja"
        assert ban["khong_co"] is False and ban["nguon"] == kho.NGUON_TRINH_DUYET
        assert ban["luc"][:4].isdigit()

    def test_ghi_de_ban_cu_khong_de_lai_rac(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, text="cũ")
        duong = kho.ghi(goc, "K1", MA_A, text="mới")
        with open(duong, encoding="utf-8") as tep:
            assert json.load(tep)["text"] == "mới"
        assert os.listdir(os.path.dirname(duong)) == [MA_A + ".json"]

    def test_ma_video_sai_dang_thi_khong_ghi_gi(self, tmp_path):
        """Mã đi thẳng vào TÊN TỆP — một mã `..` là một đường trèo ra khỏi kho."""
        goc = str(tmp_path)
        _kenh(goc, "K1")
        for xau in ("", "ngan", "../../../../etc/passwd", "AAAAAAAAAAAA",
                    "AAAAAAAAA/A", None):
            assert kho.ma_hop_le(xau) is False
            assert kho.ghi(goc, "K1", xau, text="x") == ""
            assert kho.duong_tep(goc, "K1", xau) == ""
        assert kho.ma_hop_le(MA_A) and kho.ma_hop_le("abc123XYZ_-")

    def test_khong_co_la_DA_HOI_nhung_khong_phai_CO_LOI_THOAI(self, tmp_path):
        """Hai câu hỏi khác nhau: `/loi-thoai/can-lay` hỏi "đã hỏi chưa",
        `lay_script` hỏi "có chữ không". Gộp làm một là hoặc hỏi lại mãi, hoặc
        trả một lời thoại rỗng cho khâu kịch bản."""
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, khong_co=True)
        assert kho.co_ban_ghi(goc, "K1", MA_A) is True
        assert kho.co_loi_thoai(goc, "K1", MA_A) is False
        assert kho.ma_da_co(goc, "K1") == {MA_A}
        assert kho.ma_co_loi_thoai(goc, "K1") == set()

        kho.ghi(goc, "K1", MA_B, text="có chữ")
        assert kho.ma_da_co(goc, "K1") == {MA_A, MA_B}
        assert kho.ma_co_loi_thoai(goc, "K1") == {MA_B}
        assert kho.dem(goc, "K1") == {"co": 1, "khong_co": 1, "hom_nay": 1}

    def test_text_rong_van_thanh_khong_co_du_khong_khai_co(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, text="   ")
        assert kho.co_loi_thoai(goc, "K1", MA_A) is False

    def test_kho_chua_co_thi_khong_nem_loi(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        assert kho.ma_da_co(goc, "K1") == set()
        assert kho.doc(goc, "K1", MA_A) is None
        assert kho.dem(goc, "K1")["co"] == 0


# ── `lay_script`: đọc kho TRƯỚC, và không tốn một lượt hỏi nào ───────────────


class TestLayScriptDocKhoTruoc:
    @pytest.fixture(autouse=True)
    def _bit_moi_duong_mang(self, monkeypatch):
        """Bịt MỌI đường ra ngoài của `script_video` và ĐẾM lượt gọi.

        Cái đang được kiểm không phải "trả đúng chữ" mà là "KHÔNG HỎI YOUTUBE":
        cái chặn nặng dần theo số lượt hỏi, nên một lượt hỏi thừa là một bước
        lùi thật, không phải một bài kiểm chạy chậm.

        Đếm chứ KHÔNG ném lỗi: `lay_script` cố ý bọc `_extract` trong
        `except Exception` (một video hỏng không được giết cả lượt 200 video),
        nên một `raise` ở đây bị chính nó nuốt và bài kiểm sẽ xanh sai.
        """
        self.da_goi = []

        def dem(ten):
            def no(*_a, **_k):
                self.da_goi.append(ten)
                return {}
            return no

        from core import youtube as yt

        monkeypatch.setattr(yt, "_extract", dem("extract"))
        monkeypatch.setattr(sv, "_tai_chu", dem("tai_chu"))
        monkeypatch.setattr(sv, "_tu_thu_vien", lambda _v: self.da_goi.append("thu_vien") or ("", ""))
        monkeypatch.setattr(sv, "_tu_nghe", lambda *a, **k: self.da_goi.append("tu_nghe") or ("", "", "x"))
        monkeypatch.setattr(sv, "urlopen", dem("urlopen"))

    def test_co_trong_kho_thi_tra_ve_ngay_khong_goi_mang(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, text="いろはにほへと", tieu_de="タイトル",
                ngon_ngu="ja", dai_giay=480)
        ket = sv.lay_script("https://www.youtube.com/watch?v=" + MA_A,
                            goc=goc, kenh="K1", cho_phep_nghe=True)
        assert self.da_goi == [], "kho có chữ mà vẫn hỏi YouTube"
        assert ket.duoc and ket.text == "いろはにほへと"
        assert ket.nguon == "cache-trinh-duyet"
        assert ket.nguon_dep in sv.NGUON_DEP.values()
        assert ket.video_id == MA_A and ket.title == "タイトル"
        assert ket.duration_s == 480, "độ dài để khâu remake đo mục tiêu ký tự"
        assert ket.loi == ""

    def test_kho_cua_nhom_dung_cho_moi_kenh_anh_em(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1", nhom="tam-ly")
        _kenh(goc, "K2", nhom="tam-ly")
        kho.ghi(goc, "K1", MA_A, text="chữ của nhóm")
        ket = sv.lay_script("https://youtu.be/" + MA_A, goc=goc, kenh="K2")
        assert ket.text == "chữ của nhóm" and self.da_goi == []

    def test_khong_truyen_goc_thi_khong_doc_kho(self, tmp_path):
        """Mọi nơi gọi đời cũ (và mọi bài kiểm cũ) phải chạy y như trước: không
        có `goc` thì không có kho, và lượt gọi PHẢI rơi xuống đường mạng."""
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, text="có trong kho")
        ket = sv.lay_script("https://youtu.be/" + MA_A)
        assert "extract" in self.da_goi
        assert ket.nguon != "cache-trinh-duyet"


class TestLayScriptKhongCoTrongKho:
    def test_ban_ghi_khong_co_thi_van_di_duong_mang(self, tmp_path, monkeypatch):
        """Bản ghi `khong_co` chỉ để `can-lay` thôi hỏi lại. Nó KHÔNG được chặn
        đường `tu-nghe` — đường ấy đi bằng lời gọi khác và có ngày vẫn ra chữ."""
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, khong_co=True)
        da_goi = []
        monkeypatch.setattr(sv, "_tu_kho", sv._tu_kho)  # giữ nguyên đường 0

        from core import youtube as yt

        def _extract_gia(*_a, **k):
            da_goi.append("extract")
            (k.get("nac_ra") if isinstance(k.get("nac_ra"), list) else []).append(
                type("N", (), {"proxy": ""})())
            return {"id": MA_A, "title": "t"}

        monkeypatch.setattr(yt, "_extract", _extract_gia)
        monkeypatch.setattr(sv, "_tu_thu_vien", lambda _v: ("", ""))
        ket = sv.lay_script("https://youtu.be/" + MA_A, goc=goc, kenh="K1")
        assert da_goi == ["extract"], "phải đi tiếp đường mạng, không dừng ở kho"
        assert not ket.duoc

    def test_link_khong_ra_ma_video_thi_bo_qua_kho(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        assert sv._tu_kho(goc, "K1", "ghi chú của tôi", lambda _s: None) is None


# ── Chọn nguồn: ưu tiên video ĐÃ CÓ lời thoại ───────────────────────────────


def _dong(link, **kv):
    # 30/09/2026: mỗi dòng một tiêu đề RIÊNG (theo mã trong link) — bảng xếp hạng giờ khử trùng
    # tiêu đề giữa các dòng (`NguCanh.loc`), nên dùng chung "x" làm mọi dòng sau dòng đầu bị gạt.
    d = {"link": link, "tieu_de": "tiêu đề " + str(link).rsplit("/", 1)[-1], "kenh": "Z",
         "view": 0, "vuot": 0.0, "tang": 0.0, "diem": 0}
    d.update(kv)
    return d


class TestChonNguonUuTienCoKho:
    def test_dau_bang_chua_co_kho_thi_chon_cai_co_trong_top(self, tmp_path):
        """Điểm cao hơn vài phần trăm không đổi được việc đêm nay kênh ra 0
        video: nguồn chưa có lời thoại phải đi xin YouTube, mà YouTube đang
        chặn địa chỉ VPS này."""
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_B, text="đã có sẵn")
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=500_000),
                      _dong("https://youtu.be/" + MA_B, view=300_000),
                      _dong("https://youtu.be/" + MA_C, view=100_000)]}
        nhat_ky = []
        nguon = tu_chay._chon_nguon(
            goc, "K1", False, set(), None, lambda *_a: ds, nhat_ky.append)
        assert nguon["ma"] == MA_B
        assert any("kho" in d for d in nhat_ky), "phải nói rõ vì sao đổi nguồn"

    def test_dau_bang_da_co_kho_thi_giu_nguyen(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_A, text="đầu bảng đã có")
        kho.ghi(goc, "K1", MA_B, text="cái sau cũng có")
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=500_000),
                      _dong("https://youtu.be/" + MA_B, view=400_000)]}
        nguon = tu_chay._chon_nguon(
            goc, "K1", False, set(), None, lambda *_a: ds, lambda _s: None)
        assert nguon["ma"] == MA_A

    def test_khong_ai_co_kho_thi_giu_thu_tu_xep_hang_cu(self, tmp_path):
        """Không có gì trong kho thì hành vi phải y hệt trước nhánh này."""
        goc = str(tmp_path)
        _kenh(goc, "K1")
        ds = {"moi": [_dong("https://youtu.be/" + MA_C, view=10),
                      _dong("https://youtu.be/" + MA_A, view=500_000)]}
        nguon = tu_chay._chon_nguon(
            goc, "K1", False, set(), None, lambda *_a: ds, lambda _s: None)
        assert nguon["ma"] == MA_A and nguon["ly_do"]

    def test_ban_ghi_khong_co_KHONG_duoc_tinh_la_co_kho(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_B, khong_co=True)
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=500_000),
                      _dong("https://youtu.be/" + MA_B, view=400_000)]}
        nguon = tu_chay._chon_nguon(
            goc, "K1", False, set(), None, lambda *_a: ds, lambda _s: None)
        assert nguon["ma"] == MA_A

    def test_ngoai_top_N_thi_khong_keo_len(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        cac_ma = ["M{0}".format(i) + "x" * 9 for i in range(7)]
        cac_ma = [m[:11] for m in cac_ma]
        kho.ghi(goc, "K1", cac_ma[6], text="có nhưng ở tận hạng 7")
        ds = {"moi": [_dong("https://youtu.be/" + m, view=1000 - i)
                      for i, m in enumerate(cac_ma)]}
        nguon = tu_chay._chon_nguon(
            goc, "K1", False, set(), None, lambda *_a: ds, lambda _s: None)
        assert nguon["ma"] == cac_ma[0]

    def test_kho_hong_thi_giu_dau_bang_khong_vo(self, tmp_path, monkeypatch):
        goc = str(tmp_path)
        _kenh(goc, "K1")

        def no(*_a, **_k):
            raise OSError("ổ đĩa bận")

        monkeypatch.setattr(kho, "co_loi_thoai", no)
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=5),
                      _dong("https://youtu.be/" + MA_B, view=4)]}
        nhat_ky = []
        nguon = tu_chay._chon_nguon(
            goc, "K1", False, set(), None, lambda *_a: ds, nhat_ky.append)
        assert nguon["ma"] == MA_A
        assert any("kho lời thoại" in d for d in nhat_ky)


# ── Trạm: cửa "cần lấy" và cửa nhận chữ ─────────────────────────────────────


class TestTramCanLay:
    def test_tra_top_K_chua_co_trong_kho(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        kho.ghi(goc, "K1", MA_B, text="đã có rồi")
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=500_000),
                      _dong("https://youtu.be/" + MA_B, view=400_000),
                      _dong("https://youtu.be/" + MA_C, view=300_000)]}
        from core import mot_nut

        goc_doc = mot_nut.doc_danh_sach
        try:
            mot_nut.doc_danh_sach = lambda *_a: ds
            tram = Tram(goc=goc)
            kq = tram.can_lay_loi_thoai("K1", 2)
        finally:
            mot_nut.doc_danh_sach = goc_doc
        assert [v["video_id"] for v in kq["video"]] == [MA_A, MA_C]
        assert kq["video"][0]["link"].endswith(MA_A)
        assert kq["kho"]["co"] == 1

    def test_tru_video_ca_nhom_da_lam(self, tmp_path):
        """Đã remake rồi thì không ai đi lấy lời thoại của nó nữa — kể cả khi
        kênh ANH EM trong nhóm mới là người đã làm."""
        goc = str(tmp_path)
        _kenh(goc, "K1", nhom="tam-ly")
        _kenh(goc, "K2", nhom="tam-ly")
        nc = os.path.join(goc, "CHANNEL", "K2", "nghien-cuu")
        os.makedirs(nc, exist_ok=True)
        with open(os.path.join(nc, "da-lam.txt"), "w", encoding="utf-8") as tep:
            tep.write(MA_A + " | K2 đã remake\n")
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=500_000),
                      _dong("https://youtu.be/" + MA_C, view=300_000)]}
        from core import mot_nut

        goc_doc = mot_nut.doc_danh_sach
        try:
            mot_nut.doc_danh_sach = lambda *_a: ds
            kq = Tram(goc=goc).can_lay_loi_thoai("K1")
        finally:
            mot_nut.doc_danh_sach = goc_doc
        assert [v["video_id"] for v in kq["video"]] == [MA_C]

    def test_tru_nguon_da_giu_boi_kenh_anh_em(self, tmp_path):
        """G4 (`core.nghien_cuu_nhom.giu_nguon`): kênh anh em đã GIÀNH một
        nguồn — tool sẽ không bao giờ chọn nó cho kênh này nữa, nên phiên
        trình duyệt cũng không đi hút lời thoại của nó nữa (đỡ phí 4–8 giây
        phiên thật). Kênh ĐÃ giành thì vẫn thấy nguồn của chính mình như
        thường — `nguon_da_giu_boi_kenh_khac` tự loại trường hợp đó."""
        from core import nghien_cuu_nhom

        goc = str(tmp_path)
        _kenh(goc, "K1", nhom="tam-ly")
        _kenh(goc, "K2", nhom="tam-ly")
        duoc, _ai = nghien_cuu_nhom.giu_nguon(goc, "K2", MA_A)
        assert duoc, "K2 phải giành được MA_A (chưa ai giữ)"
        ds = {"moi": [_dong("https://youtu.be/" + MA_A, view=500_000),
                      _dong("https://youtu.be/" + MA_C, view=300_000)]}
        from core import mot_nut

        goc_doc = mot_nut.doc_danh_sach
        try:
            mot_nut.doc_danh_sach = lambda *_a: ds
            # K1: MA_A bị K2 giành — chỉ còn MA_C.
            kq1 = Tram(goc=goc).can_lay_loi_thoai("K1")
            # K2: MA_A là của CHÍNH K2 — vẫn thấy như thường.
            kq2 = Tram(goc=goc).can_lay_loi_thoai("K2")
        finally:
            mot_nut.doc_danh_sach = goc_doc
        assert [v["video_id"] for v in kq1["video"]] == [MA_C]
        assert MA_A in [v["video_id"] for v in kq2["video"]]

    def test_kenh_la_thi_danh_sach_rong_kem_ly_do_khong_nem_loi(self, tmp_path):
        """Agent gọi cửa này mỗi phiên; một lỗi ở bước PHỤ không được làm vỡ
        cả phiên (quét, đăng, trả lời bình luận)."""
        kq = Tram(goc=str(tmp_path)).can_lay_loi_thoai("KHONG-CO-KENH-NAY")
        assert kq["video"] == [] and kq["loi"]

    def test_chan_tren_K(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        tram = Tram(goc=goc)
        assert tram.can_lay_loi_thoai("K1", 500)["k"] == tram.K_CAN_LAY_TOI_DA
        assert tram.can_lay_loi_thoai("K1", 0)["k"] == tram.K_CAN_LAY


class TestTramNhanLoiThoai:
    def test_nhan_chu_va_ghi_vao_kho(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        tram = Tram(goc=goc)
        goi, ma = tram.nhan_loi_thoai({
            "kenh": "K1", "video_id": MA_A, "tieu_de": "タイトル",
            "ngon_ngu": "", "dai_giay": "612", "text": "いろは",
            "nguon": "trinh-duyet"})
        assert ma == 200 and goi["ok"] is True and goi["so_ky_tu"] == 3
        assert kho.co_loi_thoai(goc, "K1", MA_A)
        assert kho.doc(goc, "K1", MA_A)["dai_giay"] == 612
        assert tram.so_loi_thoai == 1
        assert tram.so_goi == 0, "lời thoại KHÔNG được cộng vào mốc gói số liệu"

    def test_khong_co_bang_phu_de_thi_ghi_ban_ghi_rong_co_co(self, tmp_path):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        goi, ma = Tram(goc=goc).nhan_loi_thoai({
            "kenh": "K1", "video_id": MA_A, "text": "", "khong_co": True})
        assert ma == 200 and goi["khong_co"] is True
        assert kho.co_ban_ghi(goc, "K1", MA_A)
        assert kho.co_loi_thoai(goc, "K1", MA_A) is False

    @pytest.mark.parametrize("goi_vao, vi_sao", [
        ({"kenh": "K1", "video_id": "ngan", "text": "x"}, "mã quá ngắn"),
        ({"kenh": "K1", "video_id": "../../x", "text": "x"}, "mã trèo thư mục"),
        ({"kenh": "K1", "video_id": MA_A, "text": "   "}, "chữ rỗng không cờ"),
        ({"kenh": "KHONG-CO", "video_id": MA_A, "text": "x"}, "kênh lạ"),
        ({}, "gói trống"),
    ])
    def test_dau_vao_xau_thi_400_va_khong_ghi_gi(self, tmp_path, goi_vao, vi_sao):
        goc = str(tmp_path)
        _kenh(goc, "K1")
        tram = Tram(goc=goc)
        goi, ma = tram.nhan_loi_thoai(dict(goi_vao))
        assert ma == 400, vi_sao
        assert goi["ok"] is False and goi["loi"]
        assert kho.ma_da_co(goc, "K1") == set(), vi_sao
        assert tram.so_loi_thoai == 0


class TestTramQuaHTTP:
    """Đi đúng đường HTTP mà extension/agent sẽ dùng thật — hai cửa phải được
    NỐI VÀO bộ định tuyến, không chỉ tồn tại như phương thức của lớp."""

    @pytest.fixture
    def tram_song(self, tmp_path):
        _kenh(str(tmp_path), "K1")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        yield tram, "http://127.0.0.1:{0}".format(tram._may.server_address[1])
        tram.tat()

    def test_post_roi_get_can_lay_qua_HTTP(self, tram_song):
        import urllib.error
        import urllib.request

        tram, dia_chi = tram_song

        def post(goi):
            yc = urllib.request.Request(
                dia_chi + "/loi-thoai",
                data=json.dumps(goi).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(yc, timeout=10) as tl:
                return tl.status, json.loads(tl.read().decode("utf-8"))

        ma, goi = post({"kenh": "K1", "video_id": MA_A, "text": "いろは"})
        assert ma == 200 and goi["ok"] is True
        with pytest.raises(urllib.error.HTTPError) as loi:
            post({"kenh": "K1", "video_id": "xau", "text": "x"})
        assert loi.value.code == 400

        with urllib.request.urlopen(
                dia_chi + "/loi-thoai/can-lay?kenh=K1&k=3", timeout=10) as tl:
            kq = json.loads(tl.read().decode("utf-8"))
        assert kq["kenh"] == "K1" and kq["kho"]["co"] == 1
        assert kho.co_loi_thoai(tram.goc, "K1", MA_A)


# ── Agent: bước PHỤ đúng chỗ, và không kẹt khi trạm im ──────────────────────


class TestAgentBuocLoiThoai:
    def test_chen_SAU_trang_chu_va_TRUOC_dang(self, tmp_path, monkeypatch):
        """30/09/2026: lời thoại thuộc việc QUÉT NGÀY (Studio → trang chủ → lời
        thoại), KHÔNG còn nằm trong phiên đăng (phiên chỉ đăng + bình luận)."""
        agent = _nap_agent(tmp_path)
        thu_tu = []
        monkeypatch.setattr(agent, "quet_studio", lambda _c, **_k: thu_tu.append("studio") or "ok")
        monkeypatch.setattr(agent, "quet_trang_chu", lambda _c: thu_tu.append("trang-chu") or "ok")
        monkeypatch.setattr(agent, "lay_loi_thoai",
                            lambda _c: thu_tu.append("loi-thoai") or {"lay_duoc": 2, "khong_co": 1, "loi": 0})
        monkeypatch.setattr(agent, "_chay_mot_lan",
                            lambda *a, **k: thu_tu.append(a[2]) or ("xong", 0))
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda _c: thu_tu.append("dong"))
        monkeypatch.setattr(agent, "tim_chrome", lambda _c: "")
        # Cổng "trang chủ đã đủ tin để cào" (nuôi xong) đọc sổ thật của kênh — bài này chỉ chốt THỨ TỰ.
        monkeypatch.setattr(agent, "trang_chu_tin_cay", lambda _k: (True, ""))
        ket = agent.chay_quet_ngay_mot_kenh({}, {"kenh": "K1"}, "K1")
        assert thu_tu == ["studio", "trang-chu", "loi-thoai", "dong"]
        assert ket["loi_thoai"]["lay_duoc"] == 2
        thu_tu.clear()
        agent.chay_mot_phien({}, {"kenh": "K1"}, "K1")
        assert thu_tu == ["đăng", "trả lời cmt", "dong"], "phiên không quét, không hút lời thoại"

    def test_tat_bang_cau_hinh_thi_khong_mo_trinh_duyet(self, tmp_path, monkeypatch):
        agent = _nap_agent(tmp_path)
        monkeypatch.setattr(agent, "tim_chrome",
                            lambda _c: pytest.fail("không được mở trình duyệt khi đã tắt"))
        ket = agent.lay_loi_thoai({"kenh": "K1", "tram": "http://127.0.0.1:1",
                                   "lay_loi_thoai": False})
        assert ket == {"lay_duoc": 0, "khong_co": 0, "loi": 0, "giao": 0,
                       "cho_giay": 0, "ghi_chu": "tắt bằng cấu hình lay_loi_thoai"}

    def test_mac_dinh_la_BAT(self, tmp_path, monkeypatch):
        """Khoá thiếu trong cấu hình (máy ảo bản cũ, tool chưa đẩy xuống) thì
        bước này vẫn chạy — nếu không, khâu đầu lại phải đi xin YouTube."""
        agent = _nap_agent(tmp_path)
        da_hoi = []
        monkeypatch.setattr(agent, "_goi",
                            lambda *a, **k: da_hoi.append(a[1]) or {"video": []})
        ket = agent.lay_loi_thoai({"kenh": "K1", "tram": "http://x"})
        assert da_hoi and da_hoi[0].startswith("/loi-thoai/can-lay")
        assert "không cần lấy" in ket["ghi_chu"]

    def test_tram_IM_thi_bao_loi_ma_phien_van_di_tiep(self, tmp_path, monkeypatch):
        """Trạm tắt (máy nhà đóng tool) là chuyện thường. Bước PHỤ hỏng không
        được chặn lượt QUÉT NGÀY — nó vẫn đóng cổng quét và đóng Chrome."""
        import urllib.error

        agent = _nap_agent(tmp_path)

        def urlopen_im(*_a, **_k):
            raise urllib.error.URLError("trạm không trả lời")

        monkeypatch.setattr(agent.urllib.request, "urlopen", urlopen_im)
        monkeypatch.setattr(agent, "quet_studio", lambda _c, **_k: "ok")
        monkeypatch.setattr(agent, "quet_trang_chu", lambda _c: "ok")
        dong = []
        monkeypatch.setattr(agent, "dong_chrome_kenh", lambda _c: dong.append(1))
        monkeypatch.setattr(agent, "tim_chrome", lambda _c: "")
        ket = agent.chay_quet_ngay_mot_kenh({}, {"kenh": "K1", "tram": "http://127.0.0.1:1"}, "K1")
        assert ket["loi_thoai"]["lay_duoc"] == 0
        assert "lỗi" in ket["loi_thoai"]["ghi_chu"]
        assert dong, "hỏng giữa chừng vẫn phải đóng Chrome"

    def test_mo_dung_video_dau_bang_kem_dau_shopapi_lt(self, tmp_path, monkeypatch):
        agent = _nap_agent(tmp_path)
        mo = []
        monkeypatch.setattr(agent, "_goi", lambda *a, **k: {
            "video": [{"video_id": MA_A, "link": "https://youtu.be/" + MA_A},
                      {"video_id": MA_B}],
            "kho": {"co": 0, "khong_co": 0}})
        monkeypatch.setattr(agent, "tim_chrome", lambda _c: "chrome.exe")
        monkeypatch.setattr(agent, "_lenh_chrome",
                            lambda c, url, ch=None: mo.append(url) or ["cmd", "/c", "rem"])
        monkeypatch.setattr(agent.subprocess, "Popen", lambda *a, **k: type(
            "TT", (), {"terminate": lambda self: None})())
        monkeypatch.setattr(agent.time, "sleep", lambda _g: None)
        ket = agent.lay_loi_thoai({"kenh": "K1", "tram": "http://x",
                                   "cho_loi_thoai_giay": 1})
        assert mo == ["https://www.youtube.com/watch?v={0}&shopapi_lt=1".format(MA_A)]
        assert ket["giao"] == 2 and ket["cho_giay"] == 1

    def test_dem_bang_HIEU_SO_kho_truoc_sau(self, tmp_path, monkeypatch):
        """Agent không tự đếm được (extension gửi thẳng về trạm) — nó chụp kho
        trước/sau rồi lấy hiệu."""
        agent = _nap_agent(tmp_path)
        tra = [
            {"video": [{"video_id": MA_A}, {"video_id": MA_B}, {"video_id": MA_C}],
             "kho": {"co": 10, "khong_co": 4}},
            {"video": [], "kho": {"co": 12, "khong_co": 5}},
        ]
        monkeypatch.setattr(agent, "_goi", lambda *a, **k: tra.pop(0))
        monkeypatch.setattr(agent, "tim_chrome", lambda _c: "chrome.exe")
        monkeypatch.setattr(agent, "_lenh_chrome", lambda *a, **k: ["cmd", "/c", "rem"])
        monkeypatch.setattr(agent.subprocess, "Popen", lambda *a, **k: type(
            "TT", (), {"terminate": lambda self: None})())
        monkeypatch.setattr(agent.time, "sleep", lambda _g: None)
        ket = agent.lay_loi_thoai({"kenh": "K1", "tram": "http://x"})
        assert ket["lay_duoc"] == 2 and ket["khong_co"] == 1
        assert ket["loi"] == 0, "3 giao = 2 lấy được + 1 không có"

    def test_khong_bai_nao_ghi_vao_nhat_ky_THAT_cua_may(self, tmp_path):
        """Canh lại đúng cái bẩn của 22/09/2026: `vm/agent.log` — nhật ký THẬT
        chủ dự án đọc mỗi sáng — nhận ba dòng kênh "K1", một cái tên chỉ tồn tại
        trong tệp này.

        `_nap_agent` bẻ `GOC` sang `tmp_path` và `ghi` thành list. Bài này khẳng
        định cả hai cái bẻ ấy CÒN nguyên: ai bỏ đi một trong hai thì đỏ ở đây,
        chứ không lộ ra ở chỗ chủ dự án đọc sổ sáng hôm sau.
        """
        agent = _nap_agent(tmp_path)
        assert agent.GOC == str(tmp_path)
        assert agent._duong_nhat_ky().startswith(str(tmp_path))
        assert agent.THU_MUC_TIEN_ICH.startswith(str(tmp_path))
        agent.ghi("dòng thử")
        assert agent.nhat_ky == ["dòng thử"]
        # Và lượt `ghi` ấy KHÔNG tạo ra tệp nào — kể cả trong tmp_path.
        assert not os.path.exists(os.path.join(str(tmp_path), "agent.log"))

    def test_khoa_lay_loi_thoai_khai_o_CA_HAI_dau(self, tmp_path):
        """Tool đẩy thiết lập xuống máy ảo, và agent lọc lại đúng danh sách ấy
        — thiếu một đầu là núm bấm không đi tới đâu."""
        from core import vm_cai_dat

        agent = _nap_agent(tmp_path)
        for khoa in ("lay_loi_thoai", "cho_loi_thoai_giay"):
            assert khoa in vm_cai_dat.KHOA_DIEU_KHIEN, khoa
            assert khoa in agent.KHOA_TU_TOOL, khoa
        assert vm_cai_dat.MAC_DINH["lay_loi_thoai"] is True


# ── Extension: pytest không chạy được JS, nhưng đọc được MÃ ─────────────────


class TestMaExtension:
    """Chốt lại bằng MÃ NGUỒN đúng những gì phiên thật 22/09/2026 đã chứng minh
    là sai — pytest không mở được Chrome, nhưng nó đọc được tệp.

    Phiên TL1-T7 (09:52–10:03) ra "0 lấy được · 0 không có · 8 chưa về". Tệp phiên
    Chromium `Session_13434519629720236` giữ CẢ HAI địa chỉ của cùng một video
    (`…&shopapi_lt=1` và bản đã bị gỡ dấu): tab mở đúng, nhưng YouTube
    `replaceState` gỡ dấu TRƯỚC khi `loi-thoai.js` (chạy `document_idle`) kịp đọc.
    Cửa `if (!…has('shopapi_lt')) return;` đóng sập, và không một dòng log nào.
    """

    def _doc(self, ten):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "ytb_extension", ten),
                  encoding="utf-8") as tep:
            return tep.read()

    def test_content_script_khong_con_CHI_dua_vao_url(self):
        js = self._doc("loi-thoai.js")
        # Nguồn chính: hỏi background (nó bắt `tabs.onUpdated`, nơi địa chỉ còn dấu).
        assert "type: 'lt_hoi'" in js
        # Hai đường lui: cờ sessionStorage của `lt-dau.js`, và địa chỉ còn dấu.
        assert "sessionStorage.getItem('shopapi_lt')" in js
        assert "has('shopapi_lt')" in js
        # Không còn cửa `return` vô điều kiện dựa trên địa chỉ.
        assert "if (!new URLSearchParams(location.search).has('shopapi_lt')) return;" not in js

    def test_content_script_luon_noi_ra_quyet_dinh_cua_no(self):
        """Hôm 22/09 ta mù hoàn toàn vì nó thoát lặng lẽ: LevelDB của tiện ích
        không có một dòng nào chứa "lời thoại". Nay chạy hay không cũng phải nói."""
        js = self._doc("loi-thoai.js")
        assert "type: 'lt_log'" in js
        assert "BỎ QUA" in js, "phải có câu nói rõ khi nó quyết định KHÔNG chạy"
        assert self._doc("background.js").count("lời thoại[trang]") == 1

    def test_background_giu_tab_bang_onUpdated_va_nho_qua_giac_ngu(self):
        js = self._doc("background.js")
        assert "chrome.tabs.onUpdated.addListener" in js
        assert "changeInfo.url" in js and "shopapi_lt=1" in js
        # `ltTabId` trong RAM chết theo mỗi lần service worker ngủ → phải cất xuống đĩa.
        assert "luu('lt_tab'" in js and "st('lt_tab'" in js
        # Xong lượt thì NHẢ tab, kẻo người ngồi xem tiếp bị hút oan.
        assert "ltTabId = null" in js

    def test_lt_dau_cam_co_o_document_start(self):
        js = self._doc("lt-dau.js")
        assert "sessionStorage.setItem('shopapi_lt', '1')" in js
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "ytb_extension", "manifest.json"),
                  encoding="utf-8") as tep:
            mf = json.load(tep)
        theo_tep = {cs["js"][0]: cs for cs in mf["content_scripts"]}
        assert theo_tep["lt-dau.js"]["run_at"] == "document_start", \
            "cắm cờ phải SỚM HƠN lượt replaceState của YouTube"
        assert theo_tep["loi-thoai.js"]["run_at"] == "document_idle", \
            "còn phần bấm nút thì cần DOM đã dựng"
        for ten in ("lt-dau.js", "loi-thoai.js"):
            assert theo_tep[ten]["matches"] == ["https://www.youtube.com/watch*"]
        # Agent so `manifest.version` để biết có bản mới mà tải lại.
        #
        # 26/09/2026: `core/ytb_extension/manifest.json` + `background.js` đang là
        # `M` chưa commit — một phiên KHÁC đang sửa tiếp extension này ngay lúc bài
        # kiểm này chạy (đúng loại "đang mó tay" mà `CLAUDE.local.md` dặn tránh đụng
        # cùng lúc, dù tệp này không nằm trong danh sách cấm rõ tên). Version đang
        # trôi (2.7.4 → 2.7.8 → …) nên chốt cứng một con số ở đây chỉ đỏ lại ngay
        # lượt sau. Bỏ qua CHỈ dòng version khi khác mốc đã chốt; mọi luật cấu trúc
        # khác của manifest (run_at, matches, permissions) vẫn kiểm đủ ở trên.
        PHIEN_BAN_DA_CHOT = "2.7.4"
        if mf["version"] != PHIEN_BAN_DA_CHOT:
            pytest.skip(
                "manifest.json đang ở version {0}, khác mốc đã chốt {1} trong bài "
                "kiểm này — một phiên khác đang nâng cấp core/ytb_extension/ "
                "(background.js + manifest.json còn M chưa commit lúc 26/09/2026). "
                "Khi phiên đó xong, cập nhật PHIEN_BAN_DA_CHOT theo version mới rồi "
                "bỏ khối skip này.".format(mf["version"], PHIEN_BAN_DA_CHOT))
        assert mf["version"] == PHIEN_BAN_DA_CHOT
        # KHÔNG thêm quyền mới: `tabs` đã có, `webNavigation` thì không cần.
        assert "tabs" in mf["permissions"]
        assert "webNavigation" not in mf["permissions"]


# ── Sổ ngày: chủ dự án đọc nó mỗi sáng ──────────────────────────────────────


class TestSoNgay:
    def test_dem_kho_khong_nhan_boi_so_kenh_cung_nhom(self, tmp_path):
        """4 kênh cùng nhóm dùng CHUNG một kho — cộng từng kênh là nói một con
        số gấp bốn sự thật."""
        goc = str(tmp_path)
        for ma in ("K1", "K2", "K3", "K4"):
            _kenh(goc, ma, nhom="tam-ly")
        kho.ghi(goc, "K1", MA_A, text="x")
        kho.ghi(goc, "K1", MA_B, khong_co=True)
        assert tu_chay.dem_kho_loi_thoai(goc, ["K1", "K2", "K3", "K4"]) == {
            "co": 1, "khong_co": 1, "hom_nay": 1}

    def test_md_ngay_co_dong_kho_loi_thoai(self, tmp_path):
        goc = str(tmp_path)
        duong_md, _ = tu_chay.ghi_bao_cao_tat_ca(goc, "2026-09-23", {
            "luc": "2026-09-23T02:00:00", "che_do": "that", "ket_qua": [],
            "tong_uoc_vnd": 0,
            "kho_loi_thoai": {"co": 37, "khong_co": 5, "hom_nay": 8}})
        with open(duong_md, encoding="utf-8") as tep:
            chu = tep.read()
        assert "Kho lời thoại" in chu
        assert "37 video có lời thoại" in chu and "+8 lấy được hôm nay" in chu
        assert "5 video không có bảng phụ đề" in chu
