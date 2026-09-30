"""Nạp MẮT CÀO vào trình duyệt kênh qua DevTools — mỗi lần mở, không phải một lần cài.

═══ VÌ SAO CÓ TỆP NÀY (22/09/2026) ═══

Đo trên máy thật, bốn bộ trình duyệt kênh (`<MÃ>\\<MÃ>.exe`, launcher kiểu
PortableApps bọc Chromium 143/151):

1. Launcher CHUYỂN NGUYÊN mọi cờ tới `chrome.exe` — không phải nó ăn mất cờ.
2. Chromium này PHỚT LỜ `--load-extension` (Google vô hiệu từ bản 137). Cửa sau
   `--disable-features=DisableLoadExtensionCommandLineSwitch` đã thử HAI LẦN,
   không tác dụng. Hệ quả đã đo: ba hồ sơ kênh mới (TL1/TL2/TL3-T7) không có một
   mục extension nào của tool trong `Secure Preferences`, `CHANNEL/<MÃ>/chi-so/`
   của chúng không tồn tại — từ đêm 21/09 mọi phiên của ba kênh ấy chạy RỖNG.
3. TL4-T7 vẫn cào được nhờ hồ sơ nó còn đăng ký BỀN (`location=4`, từ lần bấm
   *Load unpacked* TAY ngày xưa) trỏ vào thư mục PHẲNG `vm\\tien-ich` — bản 2.6.2
   cũ, KHÔNG phải `vm\\tien-ich\\TL4-T7` (2.7.1) mà agent tải mới mỗi lần khởi động.
4. Đường sống duy nhất đã chứng minh chạy: mở cổng DevTools, gọi
   `Extensions.loadUnpacked` → extension chạy thật. NHƯNG đăng ký ấy KHÔNG BỀN:
   mở lại bình thường là mất ⇒ phải nạp lại MỖI LẦN mở trình duyệt.

Nên bài kiểm ở đây canh đúng ba điều dễ bị làm sai về sau: (a) mọi lần mở trình
duyệt MỚI đều nạp lại mắt cào, (b) trượt thì phiên vẫn ĐI TIẾP và sổ ghi rõ là
"cào rỗng", (c) kênh đã có đăng ký bền thì kích hoạt lại ĐÚNG đường bền qua
DevTools (cùng extension/id, không tạo bản thứ hai).

KHÔNG tiến trình thật, KHÔNG cổng thật, KHÔNG ghi vào nhật ký thật — `Popen`,
`urlopen`, gói `websocket` và đồng hồ đều bị bẻ.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import types

import pytest

MA_GIA = "afiknmoaknibpdogpfhbbgdkhlojlhfd"     # id thật DevTools đã trả 22/09
TEN_MAT_CAO = "Chỉ số kênh YouTube"             # đúng `name` trong manifest thật


def _nap_agent(tmp_path):
    """`vm/agent.py` — thử CẢ HAI chỗ nó có thể nằm, và BẺ MỌI ĐƯỜNG GHI.

    Giống `test_loi_thoai_trinh_duyet._nap_agent` và vì cùng một lý do: `agent.GOC`
    là thư mục của chính `agent.py`, mọi đường ghi suy ra từ đó. Không bẻ thì bài
    kiểm ghi thẳng vào `vm/agent.log` — nhật ký THẬT chủ dự án đọc mỗi sáng (đã
    dính thật 22/09/2026: 110 dòng của một kênh "K1" không tồn tại).

    Ở đây `GOC` trỏ vào `tmp_path/vm` (KHÔNG phải `tmp_path`) để `tim_chrome` tự dò
    ra `tmp_path/<MÃ>/<MÃ>.exe` đúng nếp thật — vm/ nằm CẠNH các bộ trình duyệt kênh.
    """
    goc_tool = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for duong in (os.path.join(goc_tool, "vm", "agent.py"),
                  os.path.join(os.path.dirname(goc_tool), "vm", "agent.py")):
        if os.path.isfile(duong):
            spec = importlib.util.spec_from_file_location("vm_agent_ext", duong)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            goc_vm = os.path.join(str(tmp_path), "vm")
            os.makedirs(goc_vm, exist_ok=True)
            mod.GOC = goc_vm
            mod.THU_MUC_TIEN_ICH = os.path.join(goc_vm, "tien-ich")
            mod.nhat_ky = []
            mod.ghi = mod.nhat_ky.append
            return mod
    pytest.skip("không tìm thấy vm/agent.py ở cả hai chỗ")


# ── Dựng một cái máy giả: 4 kênh, mỗi kênh một exe + một hồ sơ ───────────────


def _may_gia(agent, tmp_path, kenh="TL1-T7", cac_kenh=None, mat_cao=True,
             ho_so=True, phien_ban="2.7.1"):
    """Trả `cau_hinh` của một máy nhiều kênh, có exe giả + hồ sơ giả trên đĩa."""
    cac_kenh = list(cac_kenh or ["TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7"])
    for ma in cac_kenh:
        thu_muc = tmp_path / ma
        thu_muc.mkdir(exist_ok=True)
        (thu_muc / (ma + ".exe")).write_bytes(b"launcher")
        if ho_so:
            (thu_muc / "Data" / "profile" / "Default").mkdir(parents=True,
                                                             exist_ok=True)
    if mat_cao:
        _mat_cao(agent.THU_MUC_TIEN_ICH + os.sep + kenh, phien_ban=phien_ban,
                 ma_kenh=kenh)
    return {"kenh": kenh, "cac_kenh": cac_kenh, "tram": "http://tram:1"}


def _mat_cao(thu_muc, phien_ban="2.7.1", ten=TEN_MAT_CAO, ma_kenh="TL1-T7",
             them=None):
    """Viết một bộ extension giả (manifest + vài tệp) vào `thu_muc`."""
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "manifest.json"), "w", encoding="utf-8") as tep:
        json.dump({"name": ten, "version": phien_ban, "manifest_version": 3},
                  tep, ensure_ascii=False)
    with open(os.path.join(thu_muc, "background.js"), "w", encoding="utf-8") as tep:
        tep.write("// bản {0}\n".format(phien_ban))
    with open(os.path.join(thu_muc, "cau-hinh.json"), "w", encoding="utf-8") as tep:
        json.dump({"host": "http://tram:1", "ma_kenh": ma_kenh}, tep)
    for ten_tep, chu in (them or {}).items():
        with open(os.path.join(thu_muc, ten_tep), "w", encoding="utf-8") as tep:
            tep.write(chu)
    return thu_muc


def _secure_prefs(tmp_path, kenh, cac_muc):
    """Viết `Secure Preferences` giả cho hồ sơ của `kenh`.

    `cac_muc`: list `(location, path)` — đúng hai trường agent soi.
    """
    duong = tmp_path / kenh / "Data" / "profile" / "Default"
    duong.mkdir(parents=True, exist_ok=True)
    goi = {"extensions": {"settings": {
        "ma{0}".format(i): {"location": loc, "path": str(p), "state": 1}
        for i, (loc, p) in enumerate(cac_muc)}}}
    with open(duong / "Secure Preferences", "w", encoding="utf-8") as tep:
        json.dump(goi, tep, ensure_ascii=False)
    return duong


class _WSGia:
    """Websocket giả — ghi lại mọi khung gửi, trả đúng hình đáp của DevTools."""

    def __init__(self, so_tay, tra_ve=None, loi=None):
        self.so_tay = so_tay
        self.tra_ve = tra_ve
        self.loi = loi
        self.dong = False

    def send(self, chu):
        self.so_tay.append(("ws.send", json.loads(chu)))

    def recv(self):
        khung = self.so_tay[-1][1]
        if self.loi:
            return json.dumps({"id": khung["id"], "error": {"message": self.loi}})
        return json.dumps({"id": khung["id"],
                           "result": {"id": self.tra_ve or MA_GIA}})

    def close(self):
        self.dong = True


def _be_mang(agent, monkeypatch, so_tay, dap_json_version=True, ws=None,
             thieu_websocket=False):
    """Bẻ MỌI đường ra ngoài: `/json/version`, gói `websocket`, và `Popen`."""
    def _urlopen(url, timeout=None):
        so_tay.append(("urlopen", str(url)))
        if not dap_json_version:
            raise OSError("cổng chưa dựng")
        return io.BytesIO(json.dumps({
            "Browser": "Chrome/143.0.0.0",
            "webSocketDebuggerUrl": "ws://127.0.0.1/devtools/browser/x",
        }).encode("utf-8"))

    monkeypatch.setattr(agent.urllib.request, "urlopen", _urlopen)
    if thieu_websocket:
        # `None` trong sys.modules -> `import websocket` ném ImportError. Đúng
        # cảnh máy ảo chưa `pip install websocket-client`.
        monkeypatch.setitem(sys.modules, "websocket", None)
    else:
        gia = types.ModuleType("websocket")
        gia.create_connection = lambda url, timeout=None: (
            so_tay.append(("create_connection", url)) or (ws or _WSGia(so_tay)))
        monkeypatch.setitem(sys.modules, "websocket", gia)
    monkeypatch.setattr(agent.subprocess, "Popen",
                        lambda lenh, **_k: so_tay.append(("popen", lenh)) or type(
                            "TT", (), {"terminate": lambda self: None})())
    monkeypatch.setattr(agent, "_chrome_dang_chay", lambda _c: False)


class _DongHoGia:
    """Đồng hồ giả: `sleep` chỉ nhích kim. Bài kiểm nhờ nó đo được "có tôn trọng
    hạn 40 giây không" mà không thật sự ngồi chờ 40 giây."""

    def __init__(self):
        self.kim = 1000.0
        self.so_lan_ngu = 0

    def be(self, agent, monkeypatch):
        monkeypatch.setattr(agent.time, "monotonic", lambda: self.kim)

        def _ngu(giay):
            self.kim += float(giay)
            self.so_lan_ngu += 1
        monkeypatch.setattr(agent.time, "sleep", _ngu)
        return self


# ── Cổng riêng từng kênh ────────────────────────────────────────────────────


class TestCongRiengTungKenh:
    def test_moi_kenh_mot_cong_on_dinh(self, tmp_path):
        """Bốn kênh mở cùng máy phải có bốn cổng KHÁC nhau, và cùng một kênh
        phải ra cùng một số qua các lần chạy (soi tay mới lần được)."""
        agent = _nap_agent(tmp_path)
        cac_kenh = ["TL1-T7", "TL2-T7", "TL3-T7", "TL4-T7"]
        cong = [agent._cong_devtools({"kenh": k, "cac_kenh": cac_kenh})
                for k in cac_kenh]
        assert cong == [9300, 9301, 9302, 9303]
        assert len(set(cong)) == len(cong)

    def test_khong_dung_cong_nao_cua_tool(self, tmp_path):
        """8765 trạm, 8767 khoá agent, 8768/8769 khoá may_dang/may_cmt."""
        agent = _nap_agent(tmp_path)
        cac_kenh = ["K{0}".format(i) for i in range(10)]
        cong = {agent._cong_devtools({"kenh": k, "cac_kenh": cac_kenh})
                for k in cac_kenh}
        assert not (cong & {8765, 8767, 8768, 8769})

    def test_may_mot_kenh_va_kenh_la_ve_cong_goc(self, tmp_path):
        agent = _nap_agent(tmp_path)
        assert agent._cong_devtools({"kenh": "TL9-T7"}) == 9300
        assert agent._cong_devtools(None) == 9300
        assert agent._cong_devtools({"kenh": "LA", "cac_kenh": ["A", "B"]}) == 9300

    def test_dong_lenh_mang_dung_cong_cua_kenh(self, tmp_path):
        """Cờ trên dòng lệnh phải là cổng CỦA KÊNH ẤY — sai cổng là hai kênh
        giành nhau một cửa DevTools."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL3-T7")
        lenh = agent._lenh_chrome("C:/x.exe", "https://y", cau_hinh)
        assert "--remote-debugging-port=9302" in lenh
        assert "--remote-allow-origins=*" in lenh
        assert "--enable-unsafe-extension-debugging" in lenh
        assert lenh[-1] == "https://y", "URL luôn đứng CUỐI"
        assert not any("DisableLoadExtensionCommandLineSwitch" in c for c in lenh), \
            "cờ ấy đã đo là VÔ TÁC DỤNG trên Chromium 143/151 — đừng thêm lại"

    def test_chua_co_mat_cao_thi_khong_deo_co_rong(self, tmp_path):
        """29/09/2026 (Việc C): cổng DevTools + cờ mục 1 nay LUÔN có mặt (máy
        đăng DOM/CDP cần nối vào MỌI cửa sổ Chrome, kể cả kênh chưa có mắt
        cào) — chỉ còn CỜ RIÊNG của việc NẠP EXTENSION (`--load-extension`,
        `--enable-unsafe-extension-debugging`) là "cỏ rỗng" phải vắng mặt khi
        chưa có `manifest.json` trên đĩa. Xem `vm/agent.py::_lenh_chrome`."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7", mat_cao=False)
        lenh = agent._lenh_chrome("C:/x.exe", "https://y", cau_hinh)
        assert lenh[0] == "C:/x.exe" and lenh[-1] == "https://y"
        assert "--remote-debugging-port=9300" in lenh, "cổng DevTools vô điều kiện"
        assert not any("--load-extension" in c for c in lenh), \
            "chưa có mắt cào trên đĩa thì không có gì để nạp"
        assert "--enable-unsafe-extension-debugging" not in lenh, \
            "cờ riêng của việc nạp extension — chưa có mắt cào thì không cần"


# ── Trình tự: mở → chờ cổng → loadUnpacked ──────────────────────────────────


class TestTrinhTuNap:
    def test_popen_roi_cho_json_version_roi_loadUnpacked(self, tmp_path,
                                                         monkeypatch):
        """Đúng trình tự đã chạy thật 22/09/2026, và ĐÚNG path của kênh."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL2-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://studio.youtube.com")

        buoc = [b[0] for b in so_tay]
        assert buoc == ["popen", "urlopen", "create_connection", "ws.send"], \
            "mở trình duyệt TRƯỚC, hỏi /json/version SAU, rồi mới nạp"
        assert "9301" in so_tay[1][1], "phải hỏi đúng cổng của kênh thứ hai"
        khung = so_tay[3][1]
        assert khung["method"] == "Extensions.loadUnpacked"
        assert khung["params"]["path"] == os.path.join(
            agent.THU_MUC_TIEN_ICH, "TL2-T7"), \
            "phải nạp thư mục RIÊNG của kênh (dùng chung là báo nhầm kênh)"
        assert any("đã nạp" in d and MA_GIA in d and "TL2-T7" in d
                   for d in agent.nhat_ky), agent.nhat_ky

    def test_moi_lan_mo_MOI_deu_nap_lai(self, tmp_path, monkeypatch):
        """Đăng ký DevTools KHÔNG BỀN (đã đo: mở lại là mất) — nên ba lần mở
        trình duyệt mới là ba lần nạp, không được "nhớ đã nạp rồi"."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)
        for _ in range(3):
            agent.mo_chrome_kenh(cau_hinh, "https://www.youtube.com/")
        assert [b[0] for b in so_tay].count("ws.send") == 3

    def test_chi_chuyen_url_cho_cua_so_dang_chay_thi_KHONG_nap_lai(
            self, tmp_path, monkeypatch):
        """Trình duyệt đang chạy: `Popen` chỉ chuyển URL cho cửa sổ cũ — cửa sổ ấy
        đã có mắt cào từ lúc sinh ra. Nạp lần nữa là HAI bản cùng cào một Studio."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        monkeypatch.setattr(agent, "_chrome_dang_chay", lambda _c: True)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://www.youtube.com/")

        assert [b[0] for b in so_tay] == ["popen"]
        assert not any("extension:" in d for d in agent.nhat_ky)

    def test_hoi_dang_chay_TRUOC_khi_popen(self, tmp_path, monkeypatch):
        """Hỏi SAU khi Popen thì lúc nào cũng thấy "đang chạy" (chính mình vừa
        mở) ⇒ không bao giờ nạp nữa ⇒ cào rỗng mãi."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)
        monkeypatch.setattr(agent, "_chrome_dang_chay",
                            lambda _c: so_tay.append(("hoi-dang-chay", "")) or False)

        agent.mo_chrome_kenh(cau_hinh, "https://www.youtube.com/")

        buoc = [b[0] for b in so_tay]
        assert buoc.index("hoi-dang-chay") < buoc.index("popen")

    def test_nguoi_goi_da_biet_thi_khong_hoi_tasklist_lan_hai(self, tmp_path,
                                                              monkeypatch):
        """`giu_chrome` vừa hỏi `_chrome_dang_chay` xong — truyền xuống là đủ."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)
        monkeypatch.setattr(agent, "_chrome_dang_chay",
                            lambda _c: pytest.fail("đã truyền da_chay thì đừng hỏi lại"))
        agent.mo_chrome_kenh(cau_hinh, "https://y", da_chay=False)
        assert [b[0] for b in so_tay].count("ws.send") == 1


# ── Trượt thì phiên ĐI TIẾP, nhưng sổ phải nói rõ ────────────────────────────


class TestTruotThiDiTiep:
    def test_cong_khong_dap_thi_khong_treo_va_ghi_so(self, tmp_path, monkeypatch):
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay, dap_json_version=False)
        dong_ho = _DongHoGia().be(agent, monkeypatch)

        con = agent.mo_chrome_kenh(cau_hinh, "https://studio.youtube.com")

        assert con is not None, "phiên phải đi tiếp — có đối tượng tiến trình"
        assert dong_ho.kim - 1000.0 <= agent.CHO_DEVTOOLS_GIAY + 2, \
            "không được chờ quá hạn: phiên còn phải ĐĂNG, việc có hạn giờ thật"
        assert dong_ho.so_lan_ngu >= 2, "phải thật sự thử lại nhiều lượt trong hạn"
        assert not any(b[0] == "create_connection" for b in so_tay)
        dong = [d for d in agent.nhat_ky if "extension:" in d]
        assert len(dong) == 1 and "KHÔNG nạp được" in dong[0]
        assert "cào rỗng" in dong[0] and "9300" in dong[0], dong[0]

    def test_thieu_goi_websocket_cung_kieu_xu_ly(self, tmp_path, monkeypatch):
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay, thieu_websocket=True)
        _DongHoGia().be(agent, monkeypatch)

        con = agent.mo_chrome_kenh(cau_hinh, "https://y")

        assert con is not None
        dong = [d for d in agent.nhat_ky if "extension:" in d]
        assert len(dong) == 1 and "KHÔNG nạp được" in dong[0]
        assert "websocket" in dong[0] and "cào rỗng" in dong[0], dong[0]

    def test_devtools_tu_choi_thi_ghi_ly_do_ma_phien_van_di(self, tmp_path,
                                                            monkeypatch):
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        so_tay = []
        ws = _WSGia(so_tay, loi="Failed to load extension from path")
        _be_mang(agent, monkeypatch, so_tay, ws=ws)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://y")

        dong = [d for d in agent.nhat_ky if "extension:" in d]
        assert len(dong) == 1 and "KHÔNG nạp được" in dong[0]
        assert "Failed to load extension" in dong[0]
        assert ws.dong, "phải đóng websocket dù nạp trượt"

    def test_chua_co_mat_cao_tren_dia_thi_noi_that_la_cao_rong(self, tmp_path,
                                                               monkeypatch):
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7", mat_cao=False)
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://y")

        assert [b[0] for b in so_tay] == ["popen"]
        assert any("cào rỗng" in d for d in agent.nhat_ky), agent.nhat_ky


# ── Chống chạy đôi: kênh đã có đăng ký BỀN ──────────────────────────────────


class TestDangKyBen:
    def test_co_dang_ky_ben_thi_kich_hoat_lai_dung_duong_ben(self, tmp_path, monkeypatch):
        """Đúng ca TL4-T7: hồ sơ còn `location=4` trỏ thư mục PHẲNG `vm/tien-ich`.
        Kích hoạt lại chính đường ấy không sinh extension thứ hai."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL4-T7")
        phang = _mat_cao(agent.THU_MUC_TIEN_ICH, phien_ban="2.6.2",
                         ma_kenh="TL4-T7")
        _secure_prefs(tmp_path, "TL4-T7", [(4, phang)])
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://studio.youtube.com")

        assert [b[0] for b in so_tay] == ["popen", "urlopen", "create_connection", "ws.send"]
        khung = [b[1] for b in so_tay if b[0] == "ws.send"][0]
        assert os.path.normpath(khung["params"]["path"]) == os.path.normpath(phang)
        dong = [d for d in agent.nhat_ky if "extension:" in d]
        assert len(dong) == 1 and "kích hoạt bản bền" in dong[0]
        assert os.path.normpath(phang) in dong[0] and "TL4-T7" in dong[0]

    def test_duong_dan_chet_trong_prefs_bi_BO_QUA(self, tmp_path, monkeypatch):
        """Hồ sơ TL4-T7 thật còn một mục `location=4` trỏ `TL4-T7\\extension` —
        thư mục KHÔNG có manifest, chính Chrome cũng bỏ qua. Tính nó là "đã có
        mắt cào" thì kênh ấy cào rỗng mà agent tưởng xong việc."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL4-T7")
        _secure_prefs(tmp_path, "TL4-T7", [
            (4, tmp_path / "TL4-T7" / "extension"),        # không tồn tại
            (4, tmp_path / "TL4-T7" / "Data"),             # có thật, không manifest
        ])
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://y")

        assert [b[0] for b in so_tay][-1] == "ws.send", "phải nạp qua DevTools"
        assert any("đã nạp" in d for d in agent.nhat_ky)

    def test_extension_la_cua_chu_kenh_khong_tinh_la_mat_cao(self, tmp_path,
                                                             monkeypatch):
        """Chủ kênh cài tay một extension unpacked khác (chặn quảng cáo…) thì đó
        KHÔNG phải mắt cào của tool — vẫn phải nạp."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL2-T7")
        la = _mat_cao(str(tmp_path / "ext-la"), ten="Một extension khác")
        _secure_prefs(tmp_path, "TL2-T7", [(4, la)])
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://y")

        assert [b[0] for b in so_tay][-1] == "ws.send"

    def test_khong_doc_duoc_prefs_thi_cu_nap(self, tmp_path, monkeypatch):
        """Thà chạy đôi một hôm còn hơn cào rỗng — và ba kênh mới thì hồ sơ
        KHÔNG có mục nào, đây là đường đi thường ngày của chúng."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        duong = tmp_path / "TL1-T7" / "Data" / "profile" / "Default"
        with open(duong / "Secure Preferences", "w", encoding="utf-8") as tep:
            tep.write("{ khong phai JSON")
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        agent.mo_chrome_kenh(cau_hinh, "https://y")

        assert [b[0] for b in so_tay][-1] == "ws.send"

    def test_khong_co_ho_so_tren_dia_cung_cu_nap(self, tmp_path, monkeypatch):
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7", ho_so=False)
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)
        agent.mo_chrome_kenh(cau_hinh, "https://y")
        assert [b[0] for b in so_tay][-1] == "ws.send"


# ── Đồng bộ mã mới vào thư mục mà đăng ký bền đang trỏ ──────────────────────


class TestDongBoBanBen:
    def _dung_ca_TL4(self, tmp_path):
        """Dựng ĐÚNG hình đo được của TL4-T7: đăng ký bền trỏ thư mục PHẲNG
        `vm/tien-ich` (bản 2.6.2), còn agent tải bản mới vào `vm/tien-ich/TL4-T7`
        (2.7.1) — thư mục CON của chính nó."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL4-T7", phien_ban="2.7.1")
        phang = _mat_cao(agent.THU_MUC_TIEN_ICH, phien_ban="2.6.2",
                         ma_kenh="TL4-T7", them={"cu-khong-con-dung.js": "// cũ"})
        _secure_prefs(tmp_path, "TL4-T7", [(4, phang)])
        return agent, cau_hinh, phang

    def test_chep_de_ma_moi_nhung_GIU_cau_hinh_json(self, tmp_path):
        agent, cau_hinh, phang = self._dung_ca_TL4(tmp_path)
        cu = json.load(open(os.path.join(phang, "cau-hinh.json"), encoding="utf-8"))

        ra = agent.dong_bo_tien_ich_ben(cau_hinh)

        assert os.path.normpath(ra) == os.path.normpath(phang)
        moi = json.load(open(os.path.join(phang, "manifest.json"), encoding="utf-8"))
        assert moi["version"] == "2.7.1", "thư mục bền phải được nâng lên bản mới"
        with open(os.path.join(phang, "background.js"), encoding="utf-8") as tep:
            assert "2.7.1" in tep.read()
        sau = json.load(open(os.path.join(phang, "cau-hinh.json"), encoding="utf-8"))
        assert sau == cu, \
            "cau-hinh.json của thư mục ĐÍCH mới đúng kênh — chép đè là báo nhầm kênh"
        assert any("bản bền" in d and "2.7.1" in d for d in agent.nhat_ky), \
            agent.nhat_ky

    def test_khong_chep_long_vong_vao_chinh_minh(self, tmp_path):
        """Nguồn `vm/tien-ich/TL4-T7` nằm TRONG đích `vm/tien-ich` — đi vào thư
        mục con của chính mình là chép lòng vòng."""
        agent, cau_hinh, phang = self._dung_ca_TL4(tmp_path)
        agent.dong_bo_tien_ich_ben(cau_hinh)
        assert not os.path.exists(os.path.join(phang, "TL4-T7", "TL4-T7"))
        nguon = os.path.join(phang, "TL4-T7")
        goi = json.load(open(os.path.join(nguon, "cau-hinh.json"), encoding="utf-8"))
        assert goi["ma_kenh"] == "TL4-T7", "thư mục nguồn không được bị sửa"

    def test_khong_co_dang_ky_ben_thi_khong_chep_gi(self, tmp_path):
        """Ba kênh mới: không có đăng ký bền ⇒ không có gì để đồng bộ, và KHÔNG
        được ghi một dòng làm chủ dự án tưởng chúng đã có bản bền."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        assert agent.dong_bo_tien_ich_ben(cau_hinh) == ""
        assert not any("bản bền" in d for d in agent.nhat_ky)

    def test_dang_ky_ben_tro_dung_thu_muc_nguon_thi_thoi(self, tmp_path):
        """Đích == nguồn (máy nào từng bấm *Load unpacked* vào đúng thư mục riêng
        của kênh) — chép lên chính mình là vô nghĩa."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        rieng = os.path.join(agent.THU_MUC_TIEN_ICH, "TL1-T7")
        _secure_prefs(tmp_path, "TL1-T7", [(4, rieng)])
        assert agent.dong_bo_tien_ich_ben(cau_hinh) == ""


# ── Mọi cửa mở trình duyệt đều đi qua một chỗ ───────────────────────────────


class TestMoiCuaDeuQuaMotCho:
    @pytest.mark.parametrize("ten_buoc", ["quet_studio", "quet_trang_chu",
                                          "lay_loi_thoai", "giu_chrome"])
    def test_khong_buoc_nao_con_goi_Popen_thang(self, tmp_path, monkeypatch,
                                                ten_buoc):
        """Chừng nào còn MỘT chỗ gọi thẳng `Popen(_lenh_chrome(...))`, chỗ ấy mở
        ra một cửa sổ MÙ và cả bước đó chạy rỗng — đúng thứ đã xảy ra với ba kênh
        mới từ đêm 21/09 ("8 chưa về")."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        cau_hinh["cho_quet_giay"] = 0
        cau_hinh["cho_trang_chu_giay"] = 0
        cau_hinh["cho_loi_thoai_giay"] = 0
        da_mo = []
        monkeypatch.setattr(agent, "mo_chrome_kenh",
                            lambda ch, url, chrome="", da_chay=None: da_mo.append(url)
                            or type("TT", (), {"terminate": lambda self: None})())
        monkeypatch.setattr(agent.subprocess, "Popen",
                            lambda *a, **k: pytest.fail(
                                "phải mở qua mo_chrome_kenh, không Popen thẳng"))
        monkeypatch.setattr(agent.time, "sleep", lambda _g: None)
        monkeypatch.setattr(agent, "_chrome_dang_chay", lambda _c: False)
        monkeypatch.setattr(agent, "_goi", lambda *a, **k: {
            "video": [{"video_id": "aaaaaaaaaaa"}], "kho": {"co": 0, "khong_co": 0}})

        getattr(agent, ten_buoc)(cau_hinh)

        assert len(da_mo) == 1, "mỗi bước mở đúng một URL qua cửa chung"


# ── Vết tạm của chính DevTools KHÔNG được tính là đăng ký bền (22/09/2026, 11:48) ──


class TestVetTamDevTools:
    def test_muc_tro_thu_muc_per_kenh_thi_VAN_nap_qua_devtools(self, tmp_path,
                                                                monkeypatch):
        """Đo thật: nạp DevTools 11:19 → trình duyệt bị giết cứng → `Secure
        Preferences` còn mục `location=4` trỏ đúng `tien-ich/TL1-T7` → phiên 11:48
        agent tưởng "bản bền", bỏ nạp → Chrome mở lên gỡ mục ấy → phiên chạy KHÔNG
        có mắt cào. Mục trỏ thư mục per-kênh là vết của chính mình, phải bỏ qua."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL1-T7")
        per_kenh = os.path.join(agent.THU_MUC_TIEN_ICH, "TL1-T7")
        _secure_prefs(tmp_path, "TL1-T7", [(4, per_kenh)])
        so_tay = []
        _be_mang(agent, monkeypatch, so_tay)
        _DongHoGia().be(agent, monkeypatch)

        assert agent._dang_ky_ben_tien_ich(cau_hinh) == "", \
            "vết per-kênh không phải đăng ký bền"
        agent.mo_chrome_kenh(cau_hinh, "https://studio.youtube.com")

        buoc = [b[0] for b in so_tay]
        assert buoc == ["popen", "urlopen", "create_connection", "ws.send"], buoc
        assert any("đã nạp" in d and "TL1-T7" in d for d in agent.nhat_ky), agent.nhat_ky
        assert not any("bản bền" in d for d in agent.nhat_ky), agent.nhat_ky

    def test_thu_muc_phang_van_la_ben_nhu_cu(self, tmp_path, monkeypatch):
        """Đối chứng: đúng ca TL4-T7 (thư mục PHẲNG) vẫn được coi là bền."""
        agent = _nap_agent(tmp_path)
        cau_hinh = _may_gia(agent, tmp_path, kenh="TL4-T7")
        phang = _mat_cao(agent.THU_MUC_TIEN_ICH, phien_ban="2.6.2", ma_kenh="TL4-T7")
        _secure_prefs(tmp_path, "TL4-T7", [(4, phang)])
        assert agent._dang_ky_ben_tien_ich(cau_hinh) == os.path.normpath(phang)
