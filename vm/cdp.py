"""Nối Chrome kênh qua Chrome DevTools Protocol (CDP) — động cơ của máy đăng DOM.

Thiết kế: `workspace/THIET-KE-MAY-DANG-DOM.md` mục 1 (duyệt 29/09/2026).

Vì sao có tệp này: máy đăng cũ (`may_dang.py`, PyAutoGUI dò ảnh) gãy liên tục
28/09 — Chrome 143→151 làm nút lệch tỉ lệ, hộp "Allow … see this tab?" đè lên,
mỗi lần hỏng để lại một bản nháp thừa trên kênh. Máy mới nói chuyện THẲNG với
Chrome kênh qua cổng DevTools mà agent đã mở hằng ngày để nạp mắt cào
(`agent._cong_devtools`: 9300 + vị trí kênh) — không dò ảnh, không cần màn hình.

Luật của tệp:

* **Chỉ thư viện chuẩn + `websocket-client`** (đã cài sẵn, bản 1.9.0 — mạng
  VPS chỉ IPv6, KHÔNG cài thêm gì). Không playwright/pyppeteer/selenium.
* **Không `Runtime.enable`**, không `--enable-automation`: mọi JS chạy trong một
  thế giới riêng (isolated world) — trang không thấy được mình.
* **Không bao giờ giết Chrome.** Không `taskkill`, không
  `close_browsers_gently_in_rdp`. Chrome do agent mở thì agent đóng; chỉ khi
  CHÍNH máy này phải mở Chrome (chạy tay) thì đóng lại bằng `Browser.close`
  rồi chờ cổng đóng.
* **Van IPv4:** `agent.van_ipv4_mo()` có cờ là không nối (mã thoát 4) — Chrome
  kênh không bao giờ được sống khi IPv4 đang bật (CLAUDE.local.md luật 1).
"""

from __future__ import annotations

import collections
import json
import os
import socket
import sys
import time
import urllib.request

GOC = os.path.dirname(os.path.abspath(__file__))

__all__ = ["CdpLoi", "CdpHetHan", "CdpDut", "CdpKhongDung", "Cdp",
           "hoi_phien_ban", "ket_noi_kenh", "dong_trinh_duyet", "cong_con_mo"]


class CdpLoi(Exception):
    """DevTools trả `error` cho một lệnh (hoặc lỗi chung của lớp CDP)."""


class CdpHetHan(CdpLoi):
    """Quá hạn chờ trả lời / chờ sự kiện."""


class CdpDut(CdpLoi):
    """Đường websocket tới Chrome đã đứt (Chrome tắt, tab đóng...)."""


class CdpKhongDung(Exception):
    """Không dùng được đường DOM — kèm MÃ THOÁT theo hợp đồng mục 8:
    3 = chưa chạm kênh, được lùi về đường ảnh; 4 = bị chặn an toàn (van IPv4,
    khoá máy, sai kênh) — KHÔNG lùi."""

    def __init__(self, ma: int, ly_do: str):
        super().__init__(ly_do)
        self.ma = int(ma)
        self.ly_do = ly_do


def _loi_het_han_ws() -> tuple:
    """Các kiểu ngoại lệ nghĩa là "recv hết hạn, chưa có gì" (không phải đứt)."""
    loai = [TimeoutError, socket.timeout]
    try:
        import websocket  # gói websocket-client
        loai.append(websocket.WebSocketTimeoutException)
    except Exception:  # noqa: BLE001 — thiếu gói thì chỉ còn kiểu chuẩn
        pass
    return tuple(loai)


_HET_HAN = _loi_het_han_ws()


def hoi_phien_ban(cong: int, han: float = 2.0) -> dict:
    """`GET http://127.0.0.1:<cổng>/json/version` — {} nếu cổng không đáp."""
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:{0}/json/version".format(int(cong)),
                timeout=han) as tra_loi:
            goi = json.loads(tra_loi.read().decode("utf-8", "replace"))
        return goi if isinstance(goi, dict) else {}
    except Exception:  # noqa: BLE001 — cổng đóng là chuyện thường
        return {}


def cong_con_mo(cong: int) -> bool:
    return bool(hoi_phien_ban(cong, han=0.5))


class Cdp:
    """Một kết nối websocket CẤP TRÌNH DUYỆT, đồng bộ, chế độ `flatten`.

    `goi()` gửi một lệnh rồi đọc tới đúng trả lời mang id của nó; sự kiện đi
    ngang được xử lý ngay (hộp thoại JS, hộp chọn tệp) rồi xếp hàng cho
    `cho_su_kien()`.

    Chính sách hộp thoại JS (mục 6): alert/confirm/prompt/beforeunload → chấp
    nhận; RIÊNG beforeunload trên tab đang giữ (`giu_tab` — tab A khi video
    chưa tải xong) → TỪ CHỐI, để không rời trang giữa lúc đang tải lên.
    """

    HANG_TOI_DA = 1000

    def __init__(self, ws, nhat_ky=None):
        self._ws = ws
        self._id = 0
        self.hang = collections.deque(maxlen=self.HANG_TOI_DA)
        self.tep_cho = {}          # sessionId -> params của Page.fileChooserOpened
        self.giu_tab = set()       # sessionId không được rời trang (beforeunload)
        self.hop_thoai = []        # sổ các hộp thoại JS đã gặp
        self.nhat_ky = nhat_ky or (lambda _s: None)
        self.dut = False
        self.cong = 0
        self.tu_mo = False          # Chrome do CHÍNH máy này mở (phải tự đóng)
        self.phien_ban = ""

    # ── mở / đóng ────────────────────────────────────────────────────────
    @classmethod
    def mo(cls, ws_url: str, han: float = 30.0, nhat_ky=None) -> "Cdp":
        try:
            import websocket  # gói websocket-client, KHÔNG phải `websockets`
        except ImportError:
            raise CdpKhongDung(3, "thiếu gói websocket-client")
        # suppress_origin: không gửi Origin — không phụ thuộc cờ
        # --remote-allow-origins=* (sẽ siết sau 30/09, xem thiết kế mục 1).
        ws = websocket.create_connection(ws_url, timeout=han, suppress_origin=True)
        return cls(ws, nhat_ky=nhat_ky)

    def dong(self) -> None:
        try:
            self._ws.close()
        except Exception:  # noqa: BLE001
            pass

    # ── gửi / nhận ───────────────────────────────────────────────────────
    def _gui(self, method: str, params: dict = None, sid: str = None) -> int:
        self._id += 1
        goi = {"id": self._id, "method": method, "params": params or {}}
        if sid:
            goi["sessionId"] = sid
        try:
            self._ws.send(json.dumps(goi, ensure_ascii=False))
        except _HET_HAN:
            raise CdpHetHan("gửi {0} quá hạn".format(method))
        except Exception as loi:  # noqa: BLE001
            self.dut = True
            raise CdpDut("gửi {0} hỏng: {1}".format(method, loi))
        return self._id

    def _nhan(self, con_lai: float):
        """Một gói từ Chrome, hoặc None nếu hết `con_lai` giây mà chưa có."""
        if con_lai <= 0:
            return None
        try:
            self._ws.settimeout(max(0.05, float(con_lai)))
        except Exception:  # noqa: BLE001 — ws giả trong test có thể không có
            pass
        try:
            tho = self._ws.recv()
        except _HET_HAN:
            return None
        except Exception as loi:  # noqa: BLE001 — mọi kiểu còn lại = đứt
            self.dut = True
            raise CdpDut("đường DevTools đứt: {0}".format(str(loi)[:120]))
        if tho is None or tho == "" or tho == b"":
            # websocket-client trả '' khi nhận khung ĐÓNG.
            self.dut = True
            raise CdpDut("Chrome đóng đường DevTools")
        try:
            goi = json.loads(tho)
        except ValueError:
            return {}
        return goi if isinstance(goi, dict) else {}

    def _xu_ly(self, goi: dict) -> None:
        """Sự kiện đi ngang (hoặc trả lời của lệnh không ai chờ)."""
        if not goi or "id" in goi:
            return
        ten = goi.get("method") or ""
        sid = goi.get("sessionId")
        p = goi.get("params") or {}
        if ten == "Page.javascriptDialogOpening":
            loai = str(p.get("type") or "")
            chap_nhan = not (loai == "beforeunload" and sid in self.giu_tab)
            self.hop_thoai.append({"loai": loai, "chu": str(p.get("message") or "")[:200],
                                   "chap_nhan": chap_nhan, "sid": sid,
                                   "luc": time.strftime("%H:%M:%S")})
            self.nhat_ky("hộp thoại JS {0} «{1}» → {2}".format(
                loai, str(p.get("message") or "")[:80],
                "chấp nhận" if chap_nhan else "TỪ CHỐI (đang tải lên)"))
            try:
                # Không chờ trả lời: đang ở giữa vòng đọc của một lệnh khác.
                self._gui("Page.handleJavaScriptDialog", {"accept": chap_nhan}, sid)
            except CdpLoi:
                pass
        elif ten == "Page.fileChooserOpened":
            self.tep_cho[sid] = p
        elif ten in ("Inspector.detached", "Target.detachedFromTarget"):
            self.nhat_ky("DevTools: {0}".format(ten))
        self.hang.append(goi)

    def goi(self, method: str, params: dict = None, sid: str = None,
            han: float = 30.0) -> dict:
        """Gửi lệnh, chờ ĐÚNG trả lời của nó. Ném CdpLoi/CdpHetHan/CdpDut."""
        ma = self._gui(method, params, sid)
        het = time.monotonic() + float(han)
        while True:
            con = het - time.monotonic()
            if con <= 0:
                raise CdpHetHan("{0} quá {1:.0f}s".format(method, han))
            goi = self._nhan(con)
            if goi is None:
                continue
            if goi.get("id") == ma:
                if goi.get("error"):
                    loi = goi["error"]
                    raise CdpLoi("{0}: {1}".format(
                        method, (loi.get("message") if isinstance(loi, dict) else loi)))
                return goi.get("result") or {}
            self._xu_ly(goi)

    def bom(self, han: float = 0.2) -> None:
        """Đọc và xử lý sự kiện đang chờ trong tối đa `han` giây."""
        het = time.monotonic() + max(0.0, float(han))
        while True:
            con = het - time.monotonic()
            if con <= 0:
                return
            goi = self._nhan(con)
            if goi is None:
                return
            self._xu_ly(goi)

    def cho_su_kien(self, ten: str, han: float = 10.0, sid: str = None,
                    loc=None) -> dict:
        """Chờ một sự kiện `ten` (của `sid` nếu truyền). Ném CdpHetHan."""
        def khop(g):
            return (g.get("method") == ten and (sid is None or g.get("sessionId") == sid)
                    and (loc is None or loc(g.get("params") or {})))
        for g in list(self.hang):
            if khop(g):
                self.hang.remove(g)
                return g.get("params") or {}
        het = time.monotonic() + float(han)
        while True:
            con = het - time.monotonic()
            if con <= 0:
                raise CdpHetHan("chờ sự kiện {0} quá {1:.0f}s".format(ten, han))
            goi = self._nhan(con)
            if goi is None:
                continue
            self._xu_ly(goi)
            if khop(goi):
                try:
                    self.hang.remove(goi)
                except ValueError:
                    pass
                return goi.get("params") or {}

    def xoa_su_kien(self, ten: str, sid: str = None) -> None:
        for g in list(self.hang):
            if g.get("method") == ten and (sid is None or g.get("sessionId") == sid):
                self.hang.remove(g)

    # ── tab ──────────────────────────────────────────────────────────────
    def tao_tab(self, url: str = "about:blank") -> tuple:
        """TAB RIÊNG của máy đăng (không đụng tab của mắt cào/người dùng).

        Trả (targetId, sessionId). Bật đúng những gì cần (mục 1.5):
        Page.enable, chặn hộp chọn tệp Windows, giả lập focus. KHÔNG
        Runtime.enable."""
        tid = self.goi("Target.createTarget", {"url": url})["targetId"]
        sid = self.goi("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        self.goi("Page.enable", sid=sid)
        self.goi("Page.setInterceptFileChooserDialog", {"enabled": True}, sid=sid)
        try:
            self.goi("Emulation.setFocusEmulationEnabled", {"enabled": True}, sid=sid)
        except CdpLoi:
            pass
        return tid, sid

    def dong_tab(self, target_id: str) -> None:
        try:
            self.goi("Target.closeTarget", {"targetId": target_id}, han=10)
        except CdpLoi:
            pass


def ket_noi_kenh(cfg: dict, kenh: str, nhat_ky=None, cho_phep_mo: bool = True,
                 url_mo: str = "https://studio.youtube.com") -> Cdp:
    """Nối vào Chrome của kênh (mục 1.1–1.4). Ném CdpKhongDung(mã, lý do).

    1. Van IPv4 có cờ → mã 4.
    2. Cổng DevTools của kênh đáp → dùng lại Chrome đang mở (phiên agent giữ
       mở suốt phiên, `dong_chrome_sau_quet=False`).
       Không đáp mà `<MÃ>.exe` đang chạy → Chrome không cổng → mã 3 (lùi ảnh).
       Không đáp, chưa chạy → mở ĐÚNG như agent (`agent.mo_chrome_kenh`, kèm
       nạp mắt cào) rồi chờ cổng.
    """
    nhat_ky = nhat_ky or (lambda _s: None)
    if GOC not in sys.path:
        sys.path.insert(0, GOC)
    import agent  # noqa: PLC0415 — import an toàn (không chạy gì lúc nạp)

    if agent.van_ipv4_mo():
        raise CdpKhongDung(4, "van IPv4 đang mở (vm/van-ipv4.json) — cấm mở/nối Chrome kênh")
    ch = agent.cau_hinh_kenh(cfg, kenh)
    cong = agent._cong_devtools(ch)
    pb = hoi_phien_ban(cong)
    tu_mo = False
    if not pb:
        chrome = agent.tim_chrome(ch)
        if not chrome:
            raise CdpKhongDung(3, "không thấy trình duyệt kênh {0}".format(kenh))
        if agent._chrome_dang_chay(chrome):
            raise CdpKhongDung(3, "Chrome kênh {0} đang chạy nhưng KHÔNG có cổng DevTools {1}"
                               .format(kenh, cong))
        if not cho_phep_mo:
            raise CdpKhongDung(3, "Chrome kênh {0} chưa mở".format(kenh))
        if agent.van_ipv4_mo():      # kiểm lại sát lúc mở
            raise CdpKhongDung(4, "van IPv4 đang mở — không mở Chrome kênh")
        nhat_ky("mở Chrome kênh {0} theo agent.mo_chrome_kenh (cổng {1})".format(kenh, cong))
        agent.mo_chrome_kenh(ch, url_mo, chrome, da_chay=False)
        tu_mo = True
        if not agent._cho_devtools(cong, agent.CHO_DEVTOOLS_GIAY):
            raise CdpKhongDung(3, "mở Chrome kênh {0} nhưng cổng {1} không đáp".format(kenh, cong))
        pb = hoi_phien_ban(cong)
    ws_url = str(pb.get("webSocketDebuggerUrl") or "")
    if not ws_url:
        raise CdpKhongDung(3, "cổng {0} không trả webSocketDebuggerUrl".format(cong))
    try:
        cdp = Cdp.mo(ws_url, nhat_ky=nhat_ky)
    except CdpKhongDung:
        raise
    except Exception as loi:  # noqa: BLE001
        raise CdpKhongDung(3, "không nối được websocket DevTools: {0}".format(str(loi)[:120]))
    cdp.cong = cong
    cdp.tu_mo = tu_mo
    cdp.phien_ban = str(pb.get("Browser") or "")
    try:
        ver = cdp.goi("Browser.getVersion", han=10)
        cdp.phien_ban = str(ver.get("product") or cdp.phien_ban)
    except CdpLoi:
        pass
    # Hộp "Allow studio.youtube.com to see this tab?" (mục 6): từ chối quyền
    # chụp màn hình cho Studio ngay đầu phiên.
    try:
        cdp.goi("Browser.setPermission", {
            "permission": {"name": "display-capture"}, "setting": "denied",
            "origin": "https://studio.youtube.com"}, han=10)
    except CdpLoi as loi:
        nhat_ky("không đặt được quyền display-capture=denied ({0}) — đi tiếp".format(
            str(loi)[:100]))
    return cdp


def dong_trinh_duyet(cdp: Cdp, cho_giay: float = 20.0) -> bool:
    """Đóng Chrome ĐÚNG CÁCH (chỉ dùng khi chính máy này đã mở nó): gửi
    `Browser.close` rồi chờ cổng DevTools đóng. KHÔNG taskkill — Chrome bị
    giết là lần mở sau hiện "Restore pages?" (lỗi 2 của agent, mục 0).
    Trả True nếu cổng đã đóng trong hạn."""
    cong = cdp.cong
    # ═══ ĐÓNG TỪNG TAB TRƯỚC, Browser.close SAU (đo 29/09/2026) ═══
    # Sau mỗi lần đóng bằng Browser.close, `Preferences` của cả 4 hồ sơ kênh
    # mang `exit_type: "Crashed"` — Chrome coi là tắt đột ngột (nguồn hộp
    # "Restore pages?"). Đóng TAB CUỐI thì Chrome thoát như người dùng bấm X.
    try:
        ds = cdp.goi("Target.getTargets", han=10).get("targetInfos") or []
        for t in ds:
            if t.get("type") == "page":
                cdp._gui("Target.closeTarget", {"targetId": t["targetId"]})
                time.sleep(0.3)
    except CdpLoi:
        pass
    het = time.monotonic() + cho_giay / 2.0
    while time.monotonic() < het:
        if not cong_con_mo(cong):
            cdp.dong()
            return True
        time.sleep(0.5)
    try:
        cdp._gui("Browser.close")
    except CdpLoi:
        pass
    cdp.dong()
    het = time.monotonic() + cho_giay / 2.0
    while time.monotonic() < het:
        if not cong_con_mo(cong):
            return True
        time.sleep(0.5)
    return not cong_con_mo(cong)
