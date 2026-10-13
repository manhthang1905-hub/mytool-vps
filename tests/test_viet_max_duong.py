"""Đường viết chữ bằng thuê bao Claude Max cho MỌI việc chữ (12/10/2026).

Chủ dự án: *"phần viết đang dùng api của shopapi — tuy nhiên việc content rất quan trọng nên sẽ dùng claude 20x trên
máy này — dùng mode claude opus 5.5 — và áp dụng cho các kênh khác"*.

Không bài nào chạy Claude Code thật hay chạm mạng: tiến trình/lượt viết là đồ giả; `tests/conftest.py` còn chặn cứng
việc sinh `claude` thật (`MYTOOL_KHONG_CHAY_CLAUDE=1`).
"""

from __future__ import annotations

import json
import os

import pytest

from core import cai_dat, viet_max
from core.goi_van_ban import CHI_TRA_NOI_DUNG, dang_qua_vi, goi_van_ban, khoi_anh, qua_vi, tin_nhan_viet


@pytest.fixture(autouse=True)
def _sach(monkeypatch):
    viet_max.xoa_nho_duong()
    monkeypatch.delenv("MYTOOL_VIET_CHU", raising=False)
    yield
    viet_max.xoa_nho_duong()


def _co_max(monkeypatch, dang_nhap=True, co=True):
    monkeypatch.setattr("core.viet_max.co_claude_code", lambda: "C:/gia/claude.exe" if co else "")
    monkeypatch.setattr("core.claude_code.co_phien_dang_nhap", lambda: dang_nhap)


def _json_xong(chu, model="claude-opus-5-5"):
    return json.dumps({"type": "result", "is_error": False, "result": chu,
                       "usage": {"input_tokens": 3, "cache_creation_input_tokens": 2000,
                                 "cache_read_input_tokens": 10, "output_tokens": 42},
                       "modelUsage": {model: {}, "claude-haiku-5-5": {}}, "total_cost_usd": 0.02})


class _TienTrinhGia:
    def __init__(self, ra="", loi="", ma=0):
        self._ra, self._loi, self.returncode = ra, loi, ma

    def communicate(self, input=None):  # noqa: A002
        self.dau_vao = input
        return self._ra, self._loi

    def kill(self):
        pass


# ── Một bộ dò CLI chung ──────────────────────────────────────────────────────


class TestTimClaude:
    def test_khong_co_trong_path_thi_lay_ban_extension_moi_nhat(self, tmp_path, monkeypatch):
        from core import claude_code

        monkeypatch.setattr(claude_code, "tim_lenh", lambda *a, **k: "")
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("HOME", str(tmp_path))
        ten = "claude.exe" if os.name == "nt" else "claude"
        for pb in ("2.1.9", "2.1.296", "2.1.30"):
            d = tmp_path / ".vscode" / "extensions" / "anthropic.claude-code-{0}-win32-x64".format(pb) \
                / "resources" / "native-binary"
            d.mkdir(parents=True)
            (d / ten).write_bytes(b"")
        assert "2.1.296" in claude_code.tim_claude()

    def test_path_thang_extension(self, monkeypatch):
        from core import claude_code

        monkeypatch.setattr(claude_code, "tim_lenh", lambda *a, **k: "C:/path/claude.cmd")
        assert claude_code.tim_claude() == "C:/path/claude.cmd"

    def test_nao_dung_chung_bo_do(self, monkeypatch):
        from core import nao

        monkeypatch.setattr("core.claude_code.tim_claude", lambda goc="": "C:/chung/claude.exe")
        assert nao.tim_claude("x") == "C:/chung/claude.exe"

    def test_phien_dang_nhap_chi_nhin_co_hay_khong(self, tmp_path, monkeypatch):
        from core import claude_code

        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        assert claude_code.co_phien_dang_nhap() is False
        (tmp_path / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {"refreshToken": "gia"}}),
                                                    encoding="utf-8")
        assert claude_code.co_phien_dang_nhap() is True
        (tmp_path / ".credentials.json").write_text("{ rác", encoding="utf-8")
        assert claude_code.co_phien_dang_nhap() is False


# ── Chọn đường ───────────────────────────────────────────────────────────────


class TestChonDuong:
    def test_tu_dong_co_claude_da_dang_nhap_thi_thue_bao(self, tmp_path, monkeypatch):
        _co_max(monkeypatch)
        assert viet_max.duong_viet_chu(str(tmp_path))[0] == "max"

    def test_tu_dong_chua_dang_nhap_hoac_chua_cai_thi_vi(self, tmp_path, monkeypatch):
        _co_max(monkeypatch, dang_nhap=False)
        assert viet_max.duong_viet_chu(str(tmp_path))[0] == "vi"
        viet_max.xoa_nho_duong()
        _co_max(monkeypatch, co=False)
        assert viet_max.duong_viet_chu(str(tmp_path))[0] == "vi"

    def test_chon_vi_thang_ca_bien_ep(self, tmp_path, monkeypatch):
        _co_max(monkeypatch)
        monkeypatch.setenv("MYTOOL_VIET_CHU", "max")
        cai_dat.dat(str(tmp_path), "viet_chu_bang", "vi")
        assert viet_max.duong_viet_chu(str(tmp_path))[0] == "vi"

    def test_ep_thue_bao_ma_khong_co_claude_thi_loi_ro_khong_lang_le_di_vi(self, tmp_path, monkeypatch):
        _co_max(monkeypatch, co=False)
        cai_dat.dat(str(tmp_path), "viet_chu_bang", "claude_max")
        duong, ly_do = viet_max.duong_viet_chu(str(tmp_path))
        assert duong == "loi" and "chưa có Claude Code" in ly_do

    def test_khoa_cu_bat_van_hieu_la_thue_bao(self, tmp_path, monkeypatch):
        _co_max(monkeypatch, dang_nhap=False)
        monkeypatch.setenv("MYTOOL_VIET_CHU", "vi")
        cai_dat.dat(str(tmp_path), "kich_ban_bang_claude_code", True)
        assert viet_max.duong_viet_chu(str(tmp_path))[0] == "max"

    def test_bien_ep_vi_cua_bo_test(self, tmp_path, monkeypatch):
        _co_max(monkeypatch)
        monkeypatch.setenv("MYTOOL_VIET_CHU", "vi")
        assert viet_max.duong_viet_chu(str(tmp_path))[0] == "vi"

    def test_sua_cai_dat_co_hieu_luc_ngay(self, tmp_path, monkeypatch):
        _co_max(monkeypatch)
        goc = str(tmp_path)
        assert viet_max.duong_viet_chu(goc)[0] == "max"
        cai_dat.dat(goc, "viet_chu_bang", "vi")
        os.utime(cai_dat.duong_tep(goc), (1, 1))  # mtime khác hẳn → khoá nhớ khác
        assert viet_max.duong_viet_chu(goc)[0] == "vi"


class TestThangModel:
    def test_mac_dinh_opus_5_5_dung_dau(self, tmp_path):
        assert viet_max.thang_mo_hinh(str(tmp_path)) == (
            "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-sonnet-5")

    def test_doi_model_dau_trong_cai_dat(self, tmp_path):
        cai_dat.dat(str(tmp_path), "claude_max_mo_hinh", "claude-fable-5-1")
        assert viet_max.thang_mo_hinh(str(tmp_path))[:2] == ("claude-fable-5-1", "claude-opus-5-5")
        cai_dat.dat(str(tmp_path), "claude_max_mo_hinh", "claude-opus-5")
        assert viet_max.thang_mo_hinh(str(tmp_path)).count("claude-opus-5") == 1

    def test_ten_rac_thi_ve_mac_dinh(self, tmp_path):
        cai_dat.dat(str(tmp_path), "claude_max_mo_hinh", "gpt; rm -rf")
        assert viet_max.thang_mo_hinh(str(tmp_path))[0] == "claude-opus-5-5"


# ── Gói hội thoại ────────────────────────────────────────────────────────────


class TestPhangTinNhan:
    def test_bo_cau_he_thong_chung_giu_cau_rieng(self):
        ln, anh = viet_max.phang_tin_nhan(tin_nhan_viet("viết tiêu đề"))
        assert ln == "viết tiêu đề" and anh == [] and CHI_TRA_NOI_DUNG not in ln
        ln, _ = viet_max.phang_tin_nhan([{"role": "system", "content": "Bạn là biên tập viên."},
                                         {"role": "user", "content": "chấm bản nháp"}])
        assert ln.index("Bạn là biên tập viên.") < ln.index("chấm bản nháp")

    def test_anh_tach_ra_dung_thu_tu_va_danh_dau_cho(self):
        a1, a2 = "data:image/png;base64,QUFB", "data:image/jpeg;base64,QkJC"
        ln, anh = viet_max.phang_tin_nhan(tin_nhan_viet(
            [{"type": "text", "text": "so hai bìa"}, khoi_anh(a1), khoi_anh(a2)]))
        assert anh == [a1, a2]
        assert "[ẢNH 1]" in ln and "[ẢNH 2]" in ln and "so hai bìa" in ln

    def test_nhieu_luot_thanh_hoi_thoai_truoc_do(self):
        ln, _ = viet_max.phang_tin_nhan([{"role": "user", "content": "câu một"},
                                         {"role": "assistant", "content": "đáp một"},
                                         {"role": "user", "content": "câu hai"}])
        assert ln.index("đáp một") < ln.index("TIN NHẮN CẦN TRẢ LỜI") < ln.index("câu hai")


# ── goi_van_ban rẽ đường ─────────────────────────────────────────────────────


class _ClientCam:
    """Client ví mà ĐỤNG vào là bài kiểm đỏ — đường thuê bao không được chạm ví."""

    def request(self, *a, **k):
        raise AssertionError("đi nhầm sang ví ShopAPI")


class _ClientVi:
    def __init__(self):
        self.goi = 0

    def request(self, *_a, **_k):
        self.goi += 1
        return {"choices": [{"message": {"content": "chữ từ ví"}}]}


class TestGoiVanBanReDuong:
    def test_may_thue_bao_thi_moi_viec_chu_di_claude_code(self, tmp_path, monkeypatch):
        _co_max(monkeypatch)
        nhan = {}

        def viet(ln, **k):
            nhan.update(k, ln=ln)
            return "タイトル案"

        monkeypatch.setattr("core.viet_max.viet_bang_max", viet)
        a1 = "data:image/png;base64,QUFB"
        ra = goi_van_ban(_ClientCam(), tin_nhan_viet([{"type": "text", "text": "đọc bìa"}, khoi_anh(a1)]),
                         mo_hinh="claude-haiku-4-5", toi_da_token=64, khoa="TL9:0001:tieu-de",
                         goc=str(tmp_path), ngu=lambda _g: None)
        assert ra == "タイトル案"
        assert nhan["mo_hinh"] == "claude-opus-5-5", "model của ví không lây sang thuê bao"
        assert nhan["anh"] == [a1] and nhan["viec"].startswith("TL9:0001")
        assert nhan["effort"] == "high"

    def test_loi_nhac_anh_clip_van_di_vi(self, tmp_path, monkeypatch):
        _co_max(monkeypatch)
        monkeypatch.setattr("core.viet_max.viet_bang_max",
                            lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được đi thuê bao")))
        c = _ClientVi()
        assert goi_van_ban(c, tin_nhan_viet("cảnh 1 prompt"), qua_vi=True, goc=str(tmp_path)) == "chữ từ ví"
        with qua_vi():
            assert dang_qua_vi()
            assert goi_van_ban(c, tin_nhan_viet("cảnh 2"), goc=str(tmp_path)) == "chữ từ ví"
        assert not dang_qua_vi() and c.goi == 2

    def test_cai_dat_ep_thue_bao_ma_thieu_claude_thi_nem_loi_khong_tieu_vi(self, tmp_path, monkeypatch):
        """Luật cũ 24/08 — giờ chỉ còn khi chủ TẮT `viet_lui_vi` (13/10/2026: mặc định lùi ví)."""
        _co_max(monkeypatch, co=False)
        cai_dat.dat(str(tmp_path), "viet_chu_bang", "claude_max")
        cai_dat.dat(str(tmp_path), "viet_lui_vi", False)
        with pytest.raises(RuntimeError, match="chưa có Claude Code"):
            goi_van_ban(_ClientCam(), tin_nhan_viet("x"), goc=str(tmp_path))

    def test_ep_thue_bao_ma_thieu_claude_thi_lui_vi_mac_dinh(self, tmp_path, monkeypatch):
        """Luật chủ 13/10/2026: Claude Max hết token hoặc lỗi → ShopAPI."""
        _co_max(monkeypatch, co=False)
        cai_dat.dat(str(tmp_path), "viet_chu_bang", "claude_max")
        c = _ClientVi()
        assert goi_van_ban(c, tin_nhan_viet("x"), goc=str(tmp_path)) == "chữ từ ví" and c.goi == 1

    def test_may_khach_khong_thue_bao_thi_vi_nhu_cu(self, tmp_path, monkeypatch):
        _co_max(monkeypatch, co=False)
        c = _ClientVi()
        assert goi_van_ban(c, tin_nhan_viet("x"), goc=str(tmp_path)) == "chữ từ ví" and c.goi == 1

    def test_khau_auto_qua_vi_chi_trong_khoi_loi_nhac_anh(self, tmp_path):
        from core.auto_khau import _goi

        thay = []

        class Kenh:
            mo_hinh = "claude-sonnet-5"

        class Bc:
            on_log = None
            ngu = staticmethod(lambda _g: None)
            kenh = Kenh()

            @staticmethod
            def goi_chat(*_a, **_k):
                thay.append(dang_qua_vi())
                return "ok"

            def ghi(self, _d):
                pass

            def kiem_dung(self):
                pass

        _goi(Bc(), "viết", "k1")
        _goi(Bc(), "cảnh", "k2", qua_vi=True)
        assert thay == [False, True] and not dang_qua_vi()


# ── Suất tiến trình cả máy ───────────────────────────────────────────────────


class TestSuat:
    def test_het_suat_thi_doi_roi_het_gio(self, tmp_path):
        goc = str(tmp_path)
        with viet_max.giu_suat(goc, so_suat=2):
            with viet_max.giu_suat(goc, so_suat=2):
                assert viet_max.so_suat_dang_giu(goc) == 2
                with pytest.raises(viet_max.HetGioChoSuat):
                    with viet_max.giu_suat(goc, so_suat=2, cho_toi_da=0.0, ngu=lambda _g: None):
                        pass
        assert viet_max.so_suat_dang_giu(goc) == 0

    def test_suat_cua_tien_trinh_chet_duoc_don(self, tmp_path):
        goc = str(tmp_path)
        d = tmp_path / "workspace" / "viet-max" / "suat"
        d.mkdir(parents=True)
        (d / "0.json").write_text(json.dumps({"pid": 0, "luc": 1, "het_han": 9e12}), encoding="utf-8")
        with viet_max.giu_suat(goc, so_suat=1, cho_toi_da=0.0, ngu=lambda _g: None) as n:
            assert n == 1

    def test_bam_dung_khi_dang_doi(self, tmp_path):
        class Dung(Exception):
            pass

        dem = {"n": 0}

        def kiem():
            dem["n"] += 1
            if dem["n"] > 2:
                raise Dung()

        goc = str(tmp_path)
        with viet_max.giu_suat(goc, so_suat=1):
            with pytest.raises(Dung):
                with viet_max.giu_suat(goc, so_suat=1, kiem_dung=kiem, ngu=lambda _g: None):
                    pass

    def test_so_suat_mac_dinh_va_kep(self, tmp_path):
        assert viet_max.so_song_song(str(tmp_path)) == 3
        cai_dat.dat(str(tmp_path), "claude_max_song_song", 99)
        assert viet_max.so_song_song(str(tmp_path)) == viet_max.SONG_SONG_TOI_DA


# ── Sổ dùng + một lượt viết ──────────────────────────────────────────────────


class TestSoDung:
    def test_luot_viet_ghi_so_model_giay_token(self, tmp_path):
        goc = str(tmp_path)
        ra = viet_max.viet_bang_max("viết", goc=goc, mo_hinh="claude-opus-5-5", viec="TL9:0001:2c",
                                    mo_tien_trinh=lambda *a, **k: _TienTrinhGia(_json_xong("bản nháp")))
        assert ra == "bản nháp"
        dong = (tmp_path / "workspace" / "viet-max" / "so-dung.jsonl").read_text(encoding="utf-8").splitlines()
        m = json.loads(dong[-1])
        assert m["ok"] is True and m["mo_hinh"] == "claude-opus-5-5" and m["token_vao"] == 2013
        assert m["token_ra"] == 42 and "claude-opus-5-5" in m["mo_hinh_that"] and m["viec"] == "TL9:0001:2c"
        tom = viet_max.tom_tat_so_dung(goc)
        assert tom["luot"] == 1 and tom["theo_model"] == {"claude-opus-5-5": 1} and tom["theo_viec"] == {"TL9": 1}

    def test_luot_hong_cung_ghi_so(self, tmp_path):
        goc = str(tmp_path)
        with pytest.raises(RuntimeError):
            viet_max.viet_bang_max("viết", goc=goc,
                                   mo_tien_trinh=lambda *a, **k: _TienTrinhGia("", "Please run /login", 1))
        assert viet_max.tom_tat_so_dung(goc)["hong"] == 1

    def test_bo_test_khong_bao_gio_chay_claude_that(self, tmp_path):
        with pytest.raises(RuntimeError, match="không được chạy Claude Code thật"):
            viet_max.viet_bang_max("viết", goc=str(tmp_path))

    def test_tien_trinh_ngoai_giao_dien_khong_bi_giao_dien_giet(self):
        from core.tien_trinh_con import CHU_TU_CHAY

        assert viet_max._chu_tien_trinh() == CHU_TU_CHAY  # noqa: SLF001


# ── Cạn cả thang: đợi, báo người, tự chạy tiếp ───────────────────────────────


def _loi(chu):
    loi = RuntimeError(chu)
    loi.chi_tiet = ("", "")
    return loi


class _DongHo:
    def __init__(self, t=1_000_000.0):
        self.t = t
        self.ngu: list = []

    def __call__(self):
        return self.t

    def ngu_gia(self, g):
        self.ngu.append(g)
        self.t += g


class TestCanCaThang:
    def test_doi_toi_gio_mo_lai_roi_tu_viet_tiep_khong_re_vi(self, tmp_path):
        goc = str(tmp_path)
        dh = _DongHo()
        goi_voi = []

        def viet(ln, **k):
            goi_voi.append(k["mo_hinh"])
            if len(goi_voi) <= 4:
                raise _loi("You've reached your limit. Switch to another model")
            return "kịch bản"

        dong = []
        goi = viet_max.dung_goi_chat_max(goc, viet=viet, ngu=dh.ngu_gia, bay_gio=dh, kiem_mang=lambda: True,
                                         on_log=dong.append)
        assert goi("viết") == "kịch bản"
        assert goi_voi[:4] == list(viet_max.THANG_MO_HINH) and goi_voi[4] == "claude-opus-5-5"
        assert sum(dh.ngu) >= viet_max.GIAY_KHOA_MAC_DINH, "phải đợi tới khi hạn mức mở lại"
        assert max(dh.ngu) <= viet_max.NHIP_NGU_CAN_THANG, "ngủ từng khúc để nút Dừng nhạy"
        assert any("MỌI model" in d and "KHÔNG chuyển sang ví" in d for d in dong)
        assert "can_thang" not in viet_max.doc_trang_thai(goc), "viết được rồi thì gỡ sự cố"

    def test_dang_doi_thi_gac_tong_thay_su_co(self, tmp_path):
        from core import chot_an_toan

        goc = str(tmp_path)
        dh = _DongHo(t=__import__("time").time())

        def viet(ln, **k):
            raise _loi("usage limit reached")

        thay = []

        def ngu(g):
            if not thay:
                thay.append(chot_an_toan.kiem_claude_max(goc))
            dh.ngu_gia(g)

        goi = viet_max.dung_goi_chat_max(goc, viet=viet, ngu=ngu, bay_gio=dh, kiem_mang=lambda: True, so_lan=1,
                                         cho_can_thang_toi_da=120.0)
        with pytest.raises(RuntimeError, match="KHÔNG chuyển sang ví"):
            goi("viết")
        assert thay and [s["loai"] for s in thay[0]] == ["claude_max_can_han_muc"]
        assert thay[0][0]["muc"] == "khan" and "claude.ai/settings/usage" in thay[0][0]["can_lam_gi"]

    def test_chua_dang_nhap_thi_ghi_su_co_cho_nguoi(self, tmp_path):
        from core import chot_an_toan

        goc = str(tmp_path)

        def viet(ln, **k):
            raise _loi("Invalid API key · Please run /login")

        goi = viet_max.dung_goi_chat_max(goc, viet=viet, ngu=lambda _g: None, kiem_mang=lambda: True, so_lan=2)
        with pytest.raises(RuntimeError):
            goi("viết")
        su_co = chot_an_toan.kiem_claude_max(goc)
        assert [s["loai"] for s in su_co] == ["claude_max_chua_dang_nhap"] and "/login" in su_co[0]["can_lam_gi"]

    def test_su_co_cu_khong_con_bao(self, tmp_path):
        from core import chot_an_toan

        d = tmp_path / "workspace" / "viet-max"
        d.mkdir(parents=True)
        (d / "trang-thai.json").write_text(json.dumps({"can_thang": {"luc": 1.0, "mo_lai": 2.0},
                                                       "hong": {"luc": 9e12, "lan": 1}}), encoding="utf-8")
        assert chot_an_toan.kiem_claude_max(str(tmp_path)) == []

    def test_loai_su_co_hien_o_viec_cua_ban(self):
        from core import gac_tong

        for loai in ("claude_max_can_han_muc", "claude_max_chua_dang_nhap", "claude_max_hong"):
            assert loai in gac_tong.LOAI_CANH_BAO_MAY


# ── Bộ não chạy trên phiên đăng nhập Max ─────────────────────────────────────


class TestBoNao:
    def test_moi_truong_phien_max_khong_co_khoa(self, tmp_path, monkeypatch):
        from core import nao

        monkeypatch.setenv("ANTHROPIC_API_KEY", "khoa-gia")
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "khoa-gia")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://vi.gia")
        mt, _k = nao.moi_truong_phien(str(tmp_path), qua_max=True)
        assert not [k for k in mt if k.startswith("ANTHROPIC_")]
        assert mt["PYTHONPATH"].startswith(str(tmp_path))
        mt_vi, _k = nao.moi_truong_phien(str(tmp_path), qua_max=False)
        assert "ANTHROPIC_BASE_URL" in mt_vi

    def test_lenh_max_giu_nguyen_quyen_chi_bot_mcp(self, tmp_path):
        from core import nao

        lenh = nao.lenh_phien("claude", str(tmp_path), mo_hinh="claude-opus-5-5")
        moi = nao._them_co_max(lenh)  # noqa: SLF001
        them = ["--strict-mcp-config", "--setting-sources", "project,local"]
        assert moi[2:5] == them and moi[:2] + moi[5:] == lenh
        assert moi[moi.index("--permission-mode") + 1] == "dontAsk"
        assert moi[moi.index("--model") + 1] == "claude-opus-5-5"


class TestGiamDoc:
    def test_vi_chan_nhung_may_thue_bao_van_goi_duoc(self, tmp_path, monkeypatch):
        from core.giam_doc import quan_ly

        monkeypatch.setattr(quan_ly, "vi_cho_phep", lambda _g: "ví cạn")
        monkeypatch.setattr("core.goi_van_ban.dung_thue_bao", lambda goc="": True)
        assert quan_ly.goi_chat_that(str(tmp_path)) is not None
        monkeypatch.setattr("core.goi_van_ban.dung_thue_bao", lambda goc="": False)
        assert quan_ly.goi_chat_that(str(tmp_path)) is None
