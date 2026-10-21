"""MÁY CỘNG SỰ (DOM/CDP) — mời kênh ta khác làm CỘNG SỰ của một video đang lên, và nhận lời mời trên Chrome kênh kia.

Kế hoạch (video nào, mời ai, đợt A/B, trần, đo): `core/cong_su.py`. Tệp này chỉ thao tác Chrome RIÊNG từng kênh:

    MỜI  (Chrome kênh nguồn): Studio trang sửa video → «Hiện thêm» → khối Cộng tác → hộp mời → dán link kênh (UC
         ghim) → chọn ĐÚNG kênh trong gợi ý → Mời/Thêm → Lưu → đọc lại hàng «đang chờ» (+ link mời nếu có)
    NHẬN (Chrome kênh được mời, ĐÚNG UC ghim): mở link mời / trang lời mời trong Studio → Chấp nhận → đọc lại

Cách chạy (chủ 21/10/2026: «không mở Chrome thêm — tích hợp vào cùng lúc, các kênh làm lần lượt»):

    python vm/cong_su_dom.py --phien --kenh K --trong-phien   # BƯỚC «cộng sự» trong PHIÊN ngày của kênh K (agent gọi,
                                                             # Chrome kênh đang mở sẵn, khoá máy agent đang giữ):
                                                             # nhận lời mời gửi tới K, rồi gửi lời mời của K
    python vm/cong_su_dom.py --phien --kenh K [--thu]         # cùng việc, chạy tay một kênh (tự giữ khoá máy)
    python vm/cong_su_dom.py --tham-do --kenh K --video V   # CHỈ ĐỌC: mở khối + hộp Cộng tác, đọc, Hủy — không lưu
    python vm/cong_su_dom.py --ke-hoach [--thu]          # (tay) mọi việc tới hạn, lần lượt từng kênh

    --thu      mở trang, dò khối/hộp, đọc trạng thái — KHÔNG gõ, KHÔNG mời, KHÔNG nhận

Luật an toàn (như kéo chéo/máy đăng DOM): giữ khoá máy (`agent.giu_khoa_may_chung`), van IPv4 mở là không nối, xác
minh ĐÚNG kênh (UC ghim `logs/kenh-uc.json` qua `MayDangDom.lay_uc` — tạm giao diện `vi`, cuối phiên trả lại); chỉ đóng
tab của mình; Chrome do máy này mở thì đóng lại; ngoài khung giờ cấm (`core.cong_su.trong_gio_cam`). Không đụng tiêu
đề/bìa/mô tả — trước khi Lưu, nếu trang báo thay đổi NGOÀI khối cộng tác thì huỷ. Hộp cảnh báo/hạn chế về cộng tác →
`core.cong_su.dat_dung` (dừng cả tính năng + Việc của bạn). Không xoá cộng sự, không gỡ lời mời.

Mã thoát: 0 xong · 1 có việc hỏng · 3 đường DOM không dùng được · 4 bị chặn an toàn/khoá bận (bộ chạy skill: hoãn).
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import random
import re
import socket
import sys
import time
import unicodedata

GOC = os.path.dirname(os.path.abspath(__file__))
if GOC not in sys.path:
    sys.path.insert(0, GOC)
GOC_TOOL = os.path.dirname(GOC)

THU_MUC_LOG = os.path.join(GOC, "logs")
DUONG_BAO_CAO = os.path.join(THU_MUC_LOG, "cong-su-cuoi.json")
#: Ngoài dải trạm 8765–8775 và khoá kéo chéo 8781.
CONG_KHOA = 8782
MA_XONG, MA_HONG, MA_LUI, MA_CHAN = 0, 1, 3, 4

#: Khoá `phan_tu` máy này cần trong studio-selectors.json.
KHOA_CONG_SU = ("cs_khoi", "cs_nut_mo", "cs_hop", "cs_o_tim", "cs_goi_y", "cs_het_cho", "cs_hop_xong",
                "cs_hop_huy", "cs_hang", "cs_nut_nhan", "cs_canh_bao")

log = logging.getLogger("cong_su_dom")


def _cs():
    if GOC_TOOL not in sys.path:
        sys.path.append(GOC_TOOL)
    from core import cong_su  # noqa: PLC0415
    return cong_su


class LoiCongSu(Exception):
    def __init__(self, buoc: str, ly_do: str):
        super().__init__("{0}: {1}".format(buoc, ly_do))
        self.buoc = buoc
        self.ly_do = ly_do


class CanhBaoYouTube(LoiCongSu):
    """YouTube hiện hộp cảnh báo/hạn chế về cộng tác — dừng cả tính năng."""


class KhongCoTinhNang(LoiCongSu):
    """Kênh này không có khối Cộng tác (chưa đủ điều kiện, cần xác minh điện thoại / tính năng nâng cao)."""


def chuan(s) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


# ── JS chạy trong thế giới riêng của TrangStudio (`window.__yd`) ────────────

#: Đọc khối/hộp cộng tác: mọi hàng (tên, handle, UC trong href, trạng thái chữ), ô tìm, chữ trần, link mời.
_JS_DOC = r"""
(function(spec){
  const Y = window.__yd; if (!Y) return {loi: 'chưa có __yd'};
  const roots = Y.goc();
  const mot = (s, trong) => { for (const c of (s.chon || [])) { let x = []; try { x = (trong ? Y.trong(trong, c) : Y.qsa(roots, c)).filter(Y.hien); } catch (e) {} if (x.length) return x; } return []; };
  const hop = mot(spec.cs_hop)[0] || null, khoi = mot(spec.cs_khoi)[0] || null;
  const vung = hop || khoi;
  const ra = {hop: !!hop, khoi: !!khoi, mo_ta: vung ? Y.moTa(vung) : '', chu: vung ? String(vung.innerText || '').slice(0, 3000) : '', hang: [], link: []};
  if (!vung) return ra;
  for (const r of mot(spec.cs_hang, vung)) {
    const hrefs = Y.trong(r, 'a[href]').map(a => a.href);
    const html = String(r.outerHTML || '');
    const uc = (html.match(/UC[A-Za-z0-9_-]{22}/g) || []);
    const ten = Y.trong(r, '[test-id=channel-name], .channel-name')[0];
    const nhan = Y.trong(r, '[test-id=collaborator-badge], ytcp-badge')[0];
    ra.hang.push({chu: Y.chuan(r.innerText).slice(0, 300), hrefs: hrefs.slice(0, 6), uc: Array.from(new Set(uc)).slice(0, 4),
                  ten: ten ? Y.chuan(ten.innerText) : '', nhan: nhan ? Y.chuan(nhan.innerText) : '',
                  state: nhan ? String(nhan.getAttribute('state') || '') : ''});
  }
  for (const a of Y.trong(vung, 'a[href], input[readonly], [data-link]')) {
    const v = a.href || a.value || a.getAttribute('data-link') || '';
    if (/youtube\.com|youtu\.be/.test(v)) ra.link.push(v);
  }
  const o = mot(spec.cs_o_tim, vung)[0];
  ra.o_tim = o ? Y.moTa(o) : '';
  return ra;
})(%s)
"""

#: Gợi ý kênh sau khi gõ (đo 21/10/2026: `ytcp-channel-picker-list tp-yt-paper-item.channel` — `#display-name` +
#: `#channel-info` «@handle • N người đăng ký»; KHÔNG có UC trong DOM): [{id (đã ghim), ten, handle, chu}].
_JS_GOI_Y = r"""
(function(spec){
  const Y = window.__yd; if (!Y) return [];
  const roots = Y.goc(), ra = [];
  for (const c of (spec.chon || [])) {
    let x = []; try { x = Y.qsa(roots, c).filter(Y.hien); } catch (e) {}
    for (const e of x) {
      const o = Y.tra(e, 'cs_goi_y', c, x.length);
      const ten = Y.trong(e, '#display-name')[0], ci = Y.trong(e, '#channel-info')[0];
      o.ten = ten ? Y.chuan(ten.innerText) : '';
      o.info = ci ? Y.chuan(ci.innerText) : '';
      o.handle = (o.info.match(/@[^\s•]+/) || [''])[0];
      o.chu = Y.chuan(e.innerText).slice(0, 200);
      o.uc = Array.from(new Set(String(e.outerHTML || '').match(/UC[A-Za-z0-9_-]{22}/g) || [])).slice(0, 4);
      ra.push(o);
    }
    if (ra.length) break;
  }
  return ra;
})(%s)
"""

#: Hộp cảnh báo / hạn chế đang hiện (chữ) — '' nếu không.
_JS_CANH_BAO = r"""
(function(spec){
  const Y = window.__yd; if (!Y) return '';
  const roots = Y.goc(), chu = (spec.chu || []).map(s => s.toLowerCase()), ra = [];
  for (const c of (spec.chon || [])) {
    let x = []; try { x = Y.qsa(roots, c).filter(Y.hien); } catch (e) {}
    for (const e of x) {
      const t = Y.chuan(e.innerText).toLowerCase();
      if (chu.some(w => w && t.indexOf(w) >= 0)) ra.push(Y.chuan(e.innerText).slice(0, 400));
    }
  }
  return ra.join(' | ');
})(%s)
"""


#: Hàng của video `vid` + nút Chấp nhận trong hàng (chữ khớp nguyên văn) — hoặc nút Chấp nhận ở trang đơn (link mời).
_JS_HANG_VIDEO = r"""
(function(spec, vid){
  const Y = window.__yd; if (!Y) return {hang: false};
  const roots = Y.goc(), chu = (spec.chu || []).map(Y.chuan);
  const nutTrong = function(goc){
    for (const c of (spec.nut || [])) { let x = []; try { x = (goc ? Y.trong(goc, c) : Y.qsa(roots, c)).filter(Y.hien); } catch (e) {}
      for (const e of x) { const t = Y.chuan(e.innerText), a = Y.chuan(e.getAttribute('aria-label'));
        if (!chu.length || chu.indexOf(t) >= 0 || chu.indexOf(a) >= 0) return Y.tra(e, 'cs_nut_nhan', c, x.length); } }
    const ds = goc ? Y.trong(goc, Y.UNG_CHU) : Y.qsa(roots, Y.UNG_CHU);
    for (const e of ds) { if (!Y.hien(e)) continue; const t = Y.chuan(e.innerText), a = Y.chuan(e.getAttribute('aria-label'));
      if (chu.indexOf(t) >= 0 || chu.indexOf(a) >= 0) return Y.tra(e, 'cs_nut_nhan', 'chu', 1); }
    return null;
  };
  for (const c of (spec.hang || [])) {
    let x = []; try { x = Y.qsa(roots, c).filter(Y.hien); } catch (e) {}
    for (const r of x) {
      if (String(r.outerHTML || '').indexOf(vid) < 0) continue;
      return {hang: true, chu: Y.chuan(r.innerText).slice(0, 400), nut: nutTrong(r)};
    }
  }
  if (/\/(invite|collab)/i.test(location.href) && String(document.documentElement.outerHTML).indexOf(vid) >= 0) {
    return {hang: true, chu: 'trang lời mời', nut: nutTrong(null)};
  }
  return {hang: false};
})(%s, %s)
"""


class TrangCongSu:
    """Bọc `cdp_studio.TrangStudio` cho máy cộng sự. Bài kiểm thay bằng trang giả cùng giao diện:
    mo/url/tim/bam/go/phim/doc/goi_y/canh_bao/ghi_chan_doan."""

    def __init__(self, tr, bo: dict):
        self.tr = tr
        self.bo = bo
        self.du_phong = getattr(tr, "du_phong", {})

    def _spec(self, khoa: str) -> dict:
        return dict(((self.bo.get("phan_tu") or {}).get(khoa)) or {})

    def mo(self, url: str) -> None:
        self.tr.mo(url, han=60)

    def url(self) -> str:
        return self.tr.url()

    def tim(self, khoa: str, han: float = 0):
        return self.tr.tim(khoa, han=han, tu_chua=False)

    def bam(self, pt) -> None:
        self.tr.bam(pt)

    def go(self, khoa: str, chu: str) -> str:
        return self.tr.go(khoa, chu)

    def phim(self, ten: str) -> None:
        self.tr.phim(ten)

    def doc(self) -> dict:
        spec = {k: {"chon": self._spec(k).get("chon") or []} for k in ("cs_hop", "cs_khoi", "cs_hang", "cs_o_tim")}
        kq = self.tr.js_tho(_JS_DOC % json.dumps(spec, ensure_ascii=False))
        return kq if isinstance(kq, dict) else {"hop": False, "khoi": False, "hang": [], "link": []}

    def hien(self, khoa: str) -> bool:
        """Phần tử TRẠNG THÁI (vd «Bạn đã đạt đến giới hạn tạo lời mời») đang hiện?"""
        try:
            return bool(self.tr.tim(khoa, han=0, tu_chua=False))
        except Exception:  # noqa: BLE001
            return False

    def hang_video(self, vid: str) -> dict:
        """Hàng (tab Video cộng tác / trang lời mời) mang video `vid` + nút Chấp nhận trong hàng (nếu có)."""
        spec = {"hang": self._spec("cs_hang_tab").get("chon") or ["ytcp-video-row"],
                "nut": self._spec("cs_nut_nhan").get("chon") or [], "chu": self._spec("cs_nut_nhan").get("chu") or []}
        kq = self.tr.js_tho(_JS_HANG_VIDEO % (json.dumps(spec, ensure_ascii=False), json.dumps(vid)))
        return kq if isinstance(kq, dict) else {"hang": False}

    def goi_y(self) -> list:
        kq = self.tr.js_tho(_JS_GOI_Y % json.dumps({"chon": self._spec("cs_goi_y").get("chon") or []},
                                                    ensure_ascii=False))
        return kq if isinstance(kq, list) else []

    def canh_bao(self) -> str:
        s = self._spec("cs_canh_bao")
        try:
            return str(self.tr.js_tho(_JS_CANH_BAO % json.dumps({"chon": s.get("chon") or [], "chu": s.get("chu") or []},
                                                                ensure_ascii=False)) or "")
        except Exception:  # noqa: BLE001
            return ""

    def ghi_chan_doan(self, nhan: str) -> dict:
        try:
            return dict(self.tr.ghi_bang_chung(nhan) or {})
        except Exception as loi:  # noqa: BLE001
            return {"loi_bang_chung": str(loi)[:120]}


class MayCongSu:
    """Các bước trên trang (thật: `TrangCongSu`; kiểm: trang giả). Đếm lượt (không đồng hồ) để trang giả chạy tức thì."""

    SO_LAN_CHO = 20
    NGHI = 0.5

    def __init__(self, trang, bo: dict, nhat_ky=None, ngu=None, nghi_giay=(20, 60), rng=None):
        self.trang = trang
        self.bo = bo
        self.nk = nhat_ky or log.info
        self.ngu = ngu or time.sleep
        self.nghi_giay = tuple(nghi_giay or (20, 60))
        self.rng = rng or random.Random()
        self.uc = ""

    # ── tiện ích ─────────────────────────────────────────────────────────
    def _cho(self, ham, so_lan: int = None):
        for _ in range(int(so_lan or self.SO_LAN_CHO)):
            kq = ham()
            if kq:
                return kq
            self.ngu(self.NGHI)
        return ham()

    def nghi_nguoi(self) -> None:
        a, b = self.nghi_giay
        self.ngu(self.rng.uniform(float(a), float(b)))

    def _url(self, ten: str, **kw) -> str:
        return str((self.bo.get("url") or {}).get(ten) or "").format(**kw)

    def kiem_canh_bao(self, buoc: str) -> None:
        cb = self.trang.canh_bao()
        if cb:
            bc = self.trang.ghi_chan_doan("cong-su-canh-bao")
            raise CanhBaoYouTube(buoc, "YouTube cảnh báo/hạn chế: {0} · bằng chứng {1}".format(
                cb[:200], bc.get("anh") or ""))

    # ── kênh nguồn: mở khối + hộp ───────────────────────────────────────
    def mo_trang_sua(self, vid: str) -> None:
        self.trang.mo(self._url("sua", id=vid))
        if not self._cho(lambda: self.trang.tim("tieu_de"), so_lan=60):
            raise LoiCongSu("trang_sua", "không thấy trang sửa video {0}".format(vid))
        if self.trang.tim("cs_khoi"):
            return                         # đã mở sẵn — KHÔNG bấm (nút lúc này là «Ẩn bớt»)
        ht = self.trang.tim("hien_them")
        if ht:
            try:
                self.trang.bam(ht)
            except Exception as loi:  # noqa: BLE001 — đã mở sẵn thì nút đổi thành «Ẩn bớt»
                self.nk("bấm Hiện thêm: {0}".format(str(loi)[:100]))
            self.ngu(1.5)

    def mo_hop(self) -> dict:
        khoi = self._cho(lambda: self.trang.tim("cs_khoi"), so_lan=10)
        if not khoi:
            self.trang.ghi_chan_doan("cong-su-khong-khoi")
            raise KhongCoTinhNang("cs_khoi", "trang sửa không có khối Cộng tác")
        nut = self._cho(lambda: self.trang.tim("cs_nut_mo"), so_lan=6)
        if nut:
            self.trang.bam(nut)
            self.ngu(1.5)
        self.kiem_canh_bao("mo_hop")
        hop = self._cho(lambda: (lambda d: d if d.get("hop") or d.get("o_tim") else None)(self.trang.doc()), so_lan=12)
        if not hop:
            self.trang.ghi_chan_doan("cong-su-khong-hop")
            raise LoiCongSu("cs_hop", "bấm mở mà không thấy hộp/ô mời cộng sự")
        return hop

    @staticmethod
    def da_co(hop: dict, uc: str, handle: str = "", ten: str = "") -> dict:
        """Hàng của kênh đã có trong hộp (đang chờ hoặc đang hoạt động) — {} nếu chưa. Đo 21/10/2026 (video TL4 có 4
        cộng sự): hàng = `div.collaborator` trong hộp, chỉ mang TÊN kênh (`[test-id=channel-name]`) + nhãn
        (`ytcp-badge[test-id=collaborator-badge]`, state="complete" «Cộng sự đang hoạt động») — so TÊN nguyên văn
        (tên kênh ta khác nhau; @handle/UC nếu hàng có). Dự phòng: @handle trong CHỮ khối khi hộp ĐÓNG."""
        mau = re.compile(r"(^|[\s(])@?{0}(?=[\s•)]|$)".format(re.escape(chuan(handle).lstrip("@"))), re.I) if handle else None
        for h in (hop or {}).get("hang") or []:
            if uc and (uc in (h.get("uc") or []) or any(uc in x for x in h.get("hrefs") or [])):
                return h
            if ten and h.get("ten") and chuan(h["ten"]) == chuan(ten):
                return h
            if mau and mau.search(chuan(h.get("chu"))):
                return h
        if mau and not (hop or {}).get("hop"):
            chu = chuan((hop or {}).get("chu"))
            m = mau.search(chu)
            if m:
                return {"chu": chu[max(0, m.start() - 80): m.end() + 80], "tu_chu_khoi": True}
        return {}

    @staticmethod
    def trang_thai_hang(h: dict) -> str:
        """"nhan" (cộng sự đang hoạt động) | "cho" (đã mời, chưa nhận) | "" (không có hàng)."""
        if not h:
            return ""
        if str(h.get("state") or "") == "complete":
            return "nhan"
        t = chuan(" ".join(str(h.get(k) or "") for k in ("nhan", "chu"))).lower()
        if any(w in t for w in ("đang hoạt động", "active", "有効")):
            return "nhan"
        return "cho"

    @staticmethod
    def _cung_handle(a: str, b: str) -> bool:
        return bool(a) and bool(b) and chuan(a).lower().lstrip("@") == chuan(b).lower().lstrip("@")

    def moi_mot(self, n: dict) -> dict:
        """Mời MỘT kênh trong hộp đang mở: gõ @handle (ô chỉ tìm theo tên/@handle) → chọn gợi ý có ĐÚNG @handle (duy
        nhất trên YouTube) → hàng vào danh sách chờ của hộp. Không có @handle → không mời (không chọn mù theo tên)."""
        hd = chuan(n.get("handle"))
        if not hd:
            raise LoiCongSu("cs_handle", "chưa biết @handle của kênh {0} (trang kênh công khai không đọc được)".format(
                n.get("kenh")))
        if self.trang.hien("cs_het_cho"):
            raise LoiCongSu("cs_het_cho", "YouTube: đã đạt giới hạn tạo lời mời (tối đa)")
        self.trang.go("cs_o_tim", hd if hd.startswith("@") else "@" + hd)
        self.ngu(2.5)
        goi = self._cho(lambda: [g for g in self.trang.goi_y() if self._cung_handle(g.get("handle"), hd)], so_lan=16)
        if self.trang.hien("cs_het_cho"):
            raise LoiCongSu("cs_het_cho", "YouTube: đã đạt giới hạn tạo lời mời (tối đa)")
        if not goi:
            raise LoiCongSu("cs_goi_y", "không có gợi ý mang đúng {0} — {1} gợi ý khác".format(hd, len(self.trang.goi_y())))
        if len(goi) > 1:
            raise LoiCongSu("cs_goi_y", "{0} gợi ý cùng {1} — không chọn mù".format(len(goi), hd))
        self.trang.bam(goi[0])
        self.ngu(1.5)
        self.kiem_canh_bao("chon_kenh")
        nut = self.trang.tim("cs_nut_moi") if (self.bo.get("phan_tu") or {}).get("cs_nut_moi") else None
        if nut:
            self.trang.bam(nut)
            self.ngu(1.5)
        self.kiem_canh_bao("moi")
        return {"ok": True, "ten": goi[0].get("ten", ""),
                "goi_y": "{0} {1}".format(goi[0].get("ten", ""), goi[0].get("handle", ""))[:120]}

    def dong_hop(self) -> None:
        """Đóng hộp KHÔNG lưu (nút Hủy; Esc không đóng hộp này — đo 21/10/2026)."""
        huy = self.trang.tim("cs_hop_huy")
        if huy:
            try:
                self.trang.bam(huy)
                self.ngu(1.0)
                return
            except Exception as loi:  # noqa: BLE001
                self.nk("bấm Hủy hộp cộng sự: {0}".format(str(loi)[:100]))
        self.trang.phim("Escape")

    def luu(self) -> None:
        x = self.trang.tim("cs_hop_xong")
        if x:
            self.trang.bam(x)
            self.ngu(1.5)
        self.kiem_canh_bao("xong_hop")
        luu = self.trang.tim("sua_luu")
        if luu and not luu.get("tat"):
            self.trang.bam(luu)
            self.ngu(3.0)
        self.kiem_canh_bao("luu")

    def moi(self, vid: str, nguoi: list, che_do: str = "that") -> list:
        """Mời các kênh `nguoi` [{kenh, uc, link_kenh}] trên video `vid`. Trả [{kenh, ket, link?, ly_do?}] —
        ket: `da_moi` | `da_co` (đã ở sẵn trong khối) | `da_nhan` | `thu:…` | `loi:…` | `tran` (YouTube hết chỗ)."""
        self.mo_trang_sua(vid)
        self.kiem_canh_bao("trang_sua")
        truoc = self.trang.doc()            # khối khi hộp CHƯA mở: cộng sự đã có / đang chờ
        hop = self.mo_hop()
        ra = []
        if che_do == "thu":
            self.nk("THỬ {0}: khối Cộng tác có, hộp {1}, {2} hàng đọc được, hết chỗ: {3} — {4}".format(
                vid, "mở" if hop.get("hop") else "?", len(hop.get("hang") or []), self.trang.hien("cs_het_cho"),
                chuan(hop.get("chu"))[:160]))
            self.nk("THỬ {0}: khối trước khi mở hộp — {1}".format(vid, chuan(truoc.get("chu"))[:300]))
            for n in nguoi:
                h = self.da_co(truoc, n.get("uc"), n.get("handle"), n.get("ten")) or self.da_co(hop, n.get("uc"), n.get("handle"), n.get("ten"))
                ra.append({"kenh": n["kenh"], "ket": "thu:" + (self.trang_thai_hang(h) or "chua_moi"),
                           "het_cho": self.trang.hien("cs_het_cho")})
            self.dong_hop()
            return ra
        moi_duoc = 0
        for i, n in enumerate(nguoi):
            h = self.da_co(truoc, n.get("uc"), n.get("handle"), n.get("ten")) or self.da_co(hop, n.get("uc"), n.get("handle"), n.get("ten"))
            if h:
                tt = self.trang_thai_hang(h)
                ra.append({"kenh": n["kenh"], "ket": "da_nhan" if tt == "nhan" else "da_co"})
                continue
            if i and moi_duoc:
                self.nghi_nguoi()
            try:
                kq = self.moi_mot(n)
                ra.append({"kenh": n["kenh"], "ket": "da_moi", "goi_y": kq.get("goi_y"), "ten": kq.get("ten")})
                moi_duoc += 1
            except CanhBaoYouTube:
                raise
            except Exception as loi:  # noqa: BLE001 — một kênh hỏng không làm hỏng cả lô
                ly = str(loi)[:200]
                het = isinstance(loi, LoiCongSu) and loi.buoc == "cs_het_cho"
                ra.append({"kenh": n["kenh"], "ket": "tran" if het else "loi:" + ly})
                self.trang.ghi_chan_doan("cong-su-moi-loi")
                if het:                         # hết chỗ: các kênh sau cũng không mời được
                    for m in nguoi[i + 1:]:
                        ra.append({"kenh": m["kenh"], "ket": "tran"})
                    break
        if not moi_duoc:
            self.dong_hop()
        if moi_duoc:
            self.luu()
            self.ngu(2.0)
            hop2 = self.mo_hop()            # hàng cộng sự nằm TRONG hộp — mở lại để đọc lại thật
            for r in ra:
                if r["ket"] != "da_moi":
                    continue
                n = next(x for x in nguoi if x["kenh"] == r["kenh"])
                h = self.da_co(hop2, n.get("uc"), n.get("handle"), n.get("ten") or r.get("ten"))
                if not h:
                    r["ket"] = "loi:sau khi Lưu mở lại hộp không thấy hàng của kênh"
                else:
                    r["trang_thai_hop"] = h.get("nhan") or self.trang_thai_hang(h)
                    r["link"] = next((l for l in hop2.get("link") or [] if "invite" in l or "collab" in l), "")
            self.dong_hop()
        return ra

    # ── kênh được mời: nhận ─────────────────────────────────────────────
    def nhan(self, viec: dict, che_do: str = "that") -> dict:
        """Kênh được mời nhận lời: link mời (nếu Studio đưa) hoặc tab «Video cộng tác» của trang Nội dung
        (`url.cs_loi_moi`, đo 21/10/2026: …/videos/collaboration — hàng `ytcp-video-row` của video cộng tác) → hàng
        mang ĐÚNG video id → nút Chấp nhận trong hàng (chữ khớp NGUYÊN VĂN `cs_nut_nhan.chu`) → đọc lại.
        Hàng có mà không còn nút Chấp nhận = đã nhận sẵn."""
        vid = str(viec.get("video_id") or "")
        url = viec.get("link") or self._url("cs_loi_moi", id=vid, uc=self.uc)
        if not url:
            raise LoiCongSu("cs_link", "không có link mời và studio-selectors.json chưa có url.cs_loi_moi")
        self.trang.mo(url)
        self.ngu(4.0)
        self.kiem_canh_bao("mo_loi_moi")
        r = self._cho(lambda: (lambda x: x if x.get("hang") else None)(self.trang.hang_video(vid)), so_lan=24)             or self.trang.hang_video(vid)
        if not r.get("hang"):
            self.trang.ghi_chan_doan("cong-su-chua-co-loi-moi")
            raise LoiCongSu("cs_hang", "chưa thấy lời mời/video {0} ở {1}".format(vid, self.trang.url()[:100]))
        nut = r.get("nut")
        if not nut:
            return {"ket": "da_nhan_san", "chu": r.get("chu", "")[:200]}
        if che_do == "thu":
            return {"ket": "thu:co_nut_nhan", "chu": r.get("chu", "")[:200]}
        self.trang.bam(nut)
        self.ngu(2.0)
        xn = self.trang.tim("cs_xac_nhan_nhan") if (self.bo.get("phan_tu") or {}).get("cs_xac_nhan_nhan") else None
        if xn:
            self.trang.bam(xn)
            self.ngu(2.0)
        self.kiem_canh_bao("nhan")
        sau = self._cho(lambda: (lambda x: x if x.get("hang") and not x.get("nut") else None)(
            self.trang.hang_video(vid)), so_lan=16)
        if not sau:
            self.trang.ghi_chan_doan("cong-su-nhan-chua-an")
            raise LoiCongSu("cs_nut_nhan", "bấm Chấp nhận xong nút vẫn còn / hàng mất")
        return {"ket": "da_nhan", "chu": sau.get("chu", "")[:200]}


# ── chạy trên Chrome thật ───────────────────────────────────────────────────

def chuan_bi_bo(bo: dict) -> tuple:
    bo = copy.deepcopy(bo or {})
    pt = bo.get("phan_tu") or {}
    loi = ["thiếu khoá phan_tu.{0}".format(k) for k in KHOA_CONG_SU if k not in pt]
    if bo.get("cam_bam_cong_su"):
        bo["cam_bam"] = {k: v for k, v in bo["cam_bam_cong_su"].items() if k != "ghi_chu"}
    return bo, loi


def _ghi_ket(cs, viec: dict, kq: list) -> None:
    """Sổ sau một lượt MỜI: trạng thái từng kênh vào hàng + sổ + não."""
    bay = time.strftime("%Y-%m-%d %H:%M:%S")
    for r in kq:
        k, ket = r["kenh"], str(r["ket"])
        if ket in ("da_moi", "da_co"):
            cs.cap_nhat_nguoi(GOC_TOOL, viec["id"], k, trang_thai=cs.TT_DA_MOI, luc_moi=bay, link=r.get("link") or "",
                              goi_y=r.get("goi_y") or "")
        elif ket == "da_nhan":
            cs.cap_nhat_nguoi(GOC_TOOL, viec["id"], k, trang_thai=cs.TT_DA_NHAN, luc_nhan=bay, luc_moi=bay)
        elif ket == "tran":
            cs.cap_nhat_nguoi(GOC_TOOL, viec["id"], k, trang_thai=cs.TT_BO_QUA, ly_do="YouTube báo hết chỗ cộng sự")
        elif ket.startswith("loi"):
            cs.ghi_loi(GOC_TOOL, viec["id"], k, "moi", ket)
        cs.ghi_su_kien(GOC_TOOL, "moi", kenh=viec["kenh"], video_id=viec["video_id"], kenh_moi=k, ket=ket,
                       nao_loai="loi" if ket.startswith("loi") else ("ket_qua" if ket in ("da_moi", "da_co") else ""),
                       noi_dung="mời {0} làm cộng sự video {1}: {2}".format(k, viec["video_id"], ket))


def chay_kenh(kenh: str, viec: list, che_do: str = "that", tu_giu: bool = True, ngu=None) -> tuple:
    """Mọi việc (mời hoặc nhận) của MỘT kênh trên Chrome của nó. Trả `(mã thoát, [kết quả])`."""
    import agent  # noqa: PLC0415
    import cdp as cdp_mod  # noqa: PLC0415
    import cdp_studio  # noqa: PLC0415
    import may_dang_dom as mdd  # noqa: PLC0415

    cs = _cs()
    cai = cs.doc_cai(GOC_TOOL)
    ngu = ngu or time.sleep
    ra = []
    if tu_giu and not agent.giu_khoa_may_chung(viec="cong_su", kenh=kenh, uu_tien=1):
        log.warning("%s: khoá máy (.khoa-may) bận — để lượt sau", kenh)
        return MA_CHAN, ra
    cdp = md = None
    try:
        if agent.van_ipv4_mo():
            log.error("van IPv4 đang mở — không nối Chrome kênh")
            return MA_CHAN, ra
        bo_goc = cdp_studio.doc_bo_chon()
        loi_bo = cdp_studio.kiem_bo_chon(bo_goc)
        bo, loi_cs = chuan_bi_bo(bo_goc)
        if loi_bo or loi_cs:
            log.error("studio-selectors.json lỗi: %s", "; ".join(loi_bo + loi_cs))
            return MA_LUI, ra
        try:
            cdp = cdp_mod.ket_noi_kenh(agent.doc_cau_hinh(), kenh, nhat_ky=log.info)
        except cdp_mod.CdpKhongDung as loi:
            # đo 21/10/2026: đóng Chrome xong, trình khởi chạy portable còn sống ~5 phút → «đang chạy nhưng KHÔNG có
            # cổng DevTools» (mã 3). Tạm thời — HOÃN (4), việc còn tới hạn ở lượt sau; kẹt lâu thì tự kiểm 48 giờ báo.
            log.error("không dùng được đường DOM: %s (mã %d) — hoãn", loi.ly_do, loi.ma)
            return MA_CHAN, ra

        def tao_trang():
            return cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=log.info, thu_muc_dom=cdp_studio.THU_MUC_DOM)

        md = mdd.MayDangDom(kenh, bo, tao_trang, mdd.SoVideoId(), bao=None, thu_muc_done="", nhat_ky=log.info)
        try:
            md.lay_uc()      # ĐÚNG kênh (UC ghim) — sai là DỪNG, không thao tác gì
        except mdd.DungKenh as loi:
            log.error("%s", loi)
            return MA_CHAN, ra
        except Exception as loi:  # noqa: BLE001
            log.error("không đọc được UC kênh %s: %s", kenh, loi)
            return MA_LUI, ra
        may = MayCongSu(TrangCongSu(md.tab_b(), bo), bo, nhat_ky=log.info, ngu=ngu,
                        nghi_giay=cai.get("nghi_giay") or (20, 60))
        may.uc = md.uc
        for i, v in enumerate(viec):
            if i:
                may.nghi_nguoi()
            try:
                if v["viec"] == "moi":
                    for n in v["nguoi"]:
                        if not n.get("handle") and n.get("uc"):
                            n.update(cs.ho_so_cong_khai(GOC_TOOL, n["uc"]))
                    kq = may.moi(v["video_id"], v["nguoi"], che_do)
                    log.info("%s: mời trên %s → %s", kenh, v["video_id"], ", ".join(
                        "{0}:{1}".format(r["kenh"], r["ket"]) for r in kq))
                    if che_do == "that":
                        _ghi_ket(cs, v, kq)
                    ra.append(dict(v, ket=kq))
                else:
                    kq1 = may.nhan(v, che_do)
                    log.info("%s: nhận lời mời video %s → %s", kenh, v["video_id"], kq1["ket"])
                    if che_do == "that":
                        bay = time.strftime("%Y-%m-%d %H:%M:%S")
                        cs.cap_nhat_nguoi(GOC_TOOL, v["id"], kenh, trang_thai=cs.TT_DA_NHAN, luc_nhan=bay)
                        cs.ghi_su_kien(GOC_TOOL, "nhan", kenh=kenh, video_id=v["video_id"], ket=kq1["ket"],
                                       nao_loai="ket_qua", noi_dung="{0} nhận làm cộng sự video {1} của {2}".format(
                                           kenh, v["video_id"], v.get("kenh_nguon")))
                    ra.append(dict(v, ket=kq1["ket"]))
            except CanhBaoYouTube as loi:
                log.error("%s: %s — DỪNG tính năng cộng sự", kenh, loi)
                if che_do == "that":
                    cs.dat_dung(GOC_TOOL, loi.ly_do, kenh=kenh, bang_chung=loi.buoc)
                ra.append(dict(v, ket="loi:canh_bao: " + loi.ly_do))
                return MA_HONG, ra
            except KhongCoTinhNang as loi:
                log.warning("%s: %s — việc người", kenh, loi)
                if che_do == "that":
                    _khong_tinh_nang(cs, kenh, v, loi.ly_do)
                ra.append(dict(v, ket="loi:khong_tinh_nang: " + loi.ly_do))
            except Exception as loi:  # noqa: BLE001
                log.error("%s: việc %s %s hỏng: %s", kenh, v["viec"], v["video_id"], loi)
                if che_do == "that":
                    if v["viec"] == "moi":
                        for n in v["nguoi"]:
                            cs.ghi_loi(GOC_TOOL, v["id"], n["kenh"], "moi", str(loi))
                    else:
                        cs.ghi_loi(GOC_TOOL, v["id"], kenh, "nhan", str(loi))
                    cs.ghi_su_kien(GOC_TOOL, "loi", kenh=kenh, video_id=v["video_id"], buoc=v["viec"],
                                   ly_do=str(loi)[:200], nao_loai="loi")
                ra.append(dict(v, ket="loi:" + str(loi)[:200]))
        hong = any(str(x.get("ket")).startswith("loi") or (isinstance(x.get("ket"), list) and any(
            str(r["ket"]).startswith("loi") for r in x["ket"])) for x in ra)
        return (MA_HONG if hong else MA_XONG), ra
    except Exception as loi:  # noqa: BLE001 — không chết im lặng
        log.exception("lỗi không lường: %s", loi)
        return MA_HONG, ra
    finally:
        if md is not None:
            md.dong_het()
        if cdp is not None:
            try:
                import ngon_ngu_tam  # noqa: PLC0415
                ngon_ngu_tam.tra(cdp, kenh, log.info)
            except Exception as loi:  # noqa: BLE001
                log.warning("trả ngôn ngữ giao diện %s lỗi: %s", kenh, loi)
            if cdp.tu_mo and tu_giu:
                ok = cdp_mod.dong_trinh_duyet(cdp)
                log.info("đóng Chrome kênh %s (máy này đã mở): %s", kenh, "cổng đã đóng" if ok else "CỔNG CHƯA ĐÓNG sau 20s")
            else:
                cdp.dong()
        if tu_giu:
            agent.nha_khoa_may_chung()


def _khong_tinh_nang(cs, kenh: str, v: dict, ly_do: str) -> None:
    """Kênh thiếu tính năng cộng tác → việc người (xác minh / tính năng nâng cao), bỏ qua kênh đó."""
    can = "youtube.com/verify — bật tính năng nâng cao (xác minh điện thoại) cho kênh {0}".format(kenh)
    if v["viec"] == "moi":        # kênh NGUỒN không mời được: cả lô chờ người
        cs.cap_nhat_muc(GOC_TOOL, v["id"], trang_thai="cho_nguoi", can_lam=can, ly_do=ly_do)
        for n in v["nguoi"]:
            cs.cap_nhat_nguoi(GOC_TOOL, v["id"], n["kenh"], trang_thai=cs.TT_BO_QUA, can_nguoi=True, can_lam=can,
                              ly_do="kênh nguồn {0}: {1}".format(kenh, ly_do))
    else:
        cs.cap_nhat_nguoi(GOC_TOOL, v["id"], kenh, trang_thai=cs.TT_BO_QUA, can_nguoi=True, can_lam=can, ly_do=ly_do)
    cs.ghi_su_kien(GOC_TOOL, "khong_tinh_nang", kenh=kenh, video_id=v["video_id"], ly_do=ly_do, nao_loai="loi")


# ── CLI ─────────────────────────────────────────────────────────────────────

_O_KHOA = None


def _khoa_mot_minh(cong: int = CONG_KHOA) -> bool:
    global _O_KHOA
    try:
        _O_KHOA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA.bind(("127.0.0.1", cong))
        _O_KHOA.listen(1)
        return True
    except OSError:
        return False


def _cai_nhat_ky() -> None:
    os.makedirs(THU_MUC_LOG, exist_ok=True)
    tay = [logging.StreamHandler(sys.stdout)]
    try:
        from logging.handlers import RotatingFileHandler  # noqa: PLC0415
        tay.append(RotatingFileHandler(os.path.join(THU_MUC_LOG, "cong-su.log"), maxBytes=2 * 1024 * 1024,
                                       backupCount=2, encoding="utf-8"))
    except OSError:
        pass
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    for t in tay:
        t.setFormatter(fmt)
        log.addHandler(t)
    log.setLevel(logging.INFO)


def chay_ke_hoach(che_do: str = "that", tu_giu: bool = True, ngu=None, chay=None) -> tuple:
    """Việc tới hạn: MỜI trước (theo kênh nguồn), lập lại danh sách, rồi NHẬN (theo kênh được mời) — một Chrome một lúc.
    `chay` (kiểm) thay `chay_kenh`."""
    import datetime as _dt  # noqa: PLC0415
    cs = _cs()
    chay = chay or chay_kenh
    cai = cs.doc_cai(GOC_TOOL)
    tat_ca, ma_cuoi = [], MA_XONG
    for vong in ("moi", "nhan"):
        bay = _dt.datetime.now()
        if cs.dang_dung(GOC_TOOL):
            log.error("cộng sự đang DỪNG (workspace/cong-su/dung.json) — không làm gì")
            return MA_CHAN, tat_ca
        cam = cs.trong_gio_cam(bay, cai)
        if cam:
            log.info("%s — để lượt sau", cam)
            return (MA_CHAN if not tat_ca else ma_cuoi), tat_ca
        viec = [v for v in cs.viec_dom(GOC_TOOL, bay, cai) if v["viec"] == vong]
        theo_kenh = {}
        for v in viec:
            theo_kenh.setdefault(v["kenh"], []).append(v)
        for kenh, ds in theo_kenh.items():
            log.info("kênh %s: %d việc %s (%s)", kenh, len(ds), vong, che_do)
            ma, ra = chay(kenh, ds, che_do, tu_giu=tu_giu, ngu=ngu)
            tat_ca += ra or [dict(v, ket="loi:khong_chay: mã {0}".format(ma)) for v in ds]
            if ma != MA_XONG:
                ma_cuoi = ma if ma_cuoi == MA_XONG else max(ma_cuoi, ma)
            if ma == MA_CHAN and not ra:
                return ma_cuoi, tat_ca           # khoá bận / chặn an toàn: dừng lượt, không ép
        if che_do != "that":
            break                                # lượt thử không ghi gì → vòng nhận không có việc mới
    return ma_cuoi, tat_ca


def _doc_lenh(argv):
    ap = argparse.ArgumentParser(prog="cong_su_dom.py")
    ap.add_argument("--ke-hoach", action="store_true", help="chạy việc tới hạn trong workspace/cong-su/hang.json")
    ap.add_argument("--phien", action="store_true", help="với --kenh: bước cộng sự của MỘT kênh (nhận rồi mời)")
    ap.add_argument("--thu", action="store_true", help="dò khối/hộp/nút, đọc trạng thái — KHÔNG gõ, mời, nhận")
    ap.add_argument("--tham-do", action="store_true", help="với --kenh --video: mở khối + hộp Cộng tác, đọc, Hủy (chỉ đọc)")
    ap.add_argument("--kenh", default="")
    ap.add_argument("--video", default="")
    ap.add_argument("--trong-phien", action="store_true", help="agent gọi giữa phiên — không tự giữ khoá máy")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = _doc_lenh(sys.argv[1:] if argv is None else argv)
    _cai_nhat_ky()
    che_do = "thu" if a.thu else "that"
    if not (a.ke_hoach or (a.phien and a.kenh)
            or (a.tham_do and a.kenh and re.fullmatch(r"[A-Za-z0-9_-]{11}", a.video or ""))):
        log.error("cần --phien --kenh K, --ke-hoach, hoặc --tham-do --kenh K --video <videoId>")
        return MA_HONG
    if a.phien:
        cs = _cs()
        ok, ly = cs.can_dom(GOC_TOOL, kenh=a.kenh)
        if not ok:
            log.info("cộng sự %s: %s — bỏ qua bước", a.kenh, ly)    # không việc → KHÔNG nối/mở Chrome
            return MA_XONG
    if not _khoa_mot_minh():
        log.error("đã có một máy cộng sự khác đang chạy (cổng %d) — thoát", CONG_KHOA)
        return MA_CHAN
    if a.phien:
        viec = cs.viec_dom(GOC_TOOL, kenh=a.kenh)
        log.info("cộng sự %s: %s", a.kenh, ly)
        ma, tat_ca = chay_kenh(a.kenh, viec, che_do, tu_giu=not a.trong_phien)
    elif a.tham_do:
        che_do = "thu"
        ma, tat_ca = chay_kenh(a.kenh, [{"viec": "moi", "id": "", "kenh": a.kenh, "video_id": a.video, "nguoi": []}],
                               "thu", tu_giu=not a.trong_phien)
    else:
        ma, tat_ca = chay_ke_hoach(che_do, tu_giu=not a.trong_phien)
    try:
        os.makedirs(THU_MUC_LOG, exist_ok=True)
        with open(DUONG_BAO_CAO, "w", encoding="utf-8") as tep:
            json.dump({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "che_do": che_do, "ma_thoat": ma, "viec": tat_ca},
                      tep, ensure_ascii=False, indent=1, default=str)
    except OSError:
        pass
    try:
        import agent  # noqa: PLC0415
        agent.ghi("cộng sự DOM [{0}]: {1} việc · mã {2}".format(che_do, len(tat_ca), ma))
    except Exception:  # noqa: BLE001
        pass
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
