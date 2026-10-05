"""MÁY KÉO VIEW CHÉO (DOM/CDP) — kênh LỚN đưa video kênh EM vào danh sách phát công khai của mình.

Kế hoạch (việc nào, kênh nào, danh sách phát nào, vì sao, giới hạn, cách đo): `core/keo_cheo.py`.
Tệp này chỉ làm MỘT việc trên Chrome RIÊNG của kênh lớn (đã đăng nhập kênh đó):

    trang xem https://www.youtube.com/watch?v=<id>  →  nút «Lưu» (thẳng, hoặc qua «⋯ Thao tác khác»)
    →  hộp «Lưu vào…»: tìm hàng ĐÚNG TÊN danh sách phát (so nguyên văn sau chuẩn hoá NFKC)
    →  tích  →  đọc lại «đã tích»  →  đóng  →  MỞ LẠI hộp, xác nhận vẫn tích (đọc lại thật)  →  đóng.

Cách chạy:

    python vm/keo_cheo_dom.py --kenh TL4-T7 --video <id> --ds "おすすめ" [--thu | --doc-hop]
    python vm/keo_cheo_dom.py --ke-hoach [--kenh TL4-T7] [--thu | --doc-hop]   # việc hôm nay, lần lượt từng Chrome
    python vm/keo_cheo_dom.py --in-ke-hoach                                     # chỉ in kế hoạch (không Chrome)
    python vm/keo_cheo_dom.py --hoc-ds --kenh TL4-T7 [--video <id công khai của kênh>]   # HỌC tên danh sách phát

    --hoc-ds   mở hộp Lưu trên một video công khai của CHÍNH kênh, đọc mọi tên danh sách phát → sổ học
               `workspace/keo-cheo/ds-kenh.json` (kế hoạch dùng khi kenh.yaml/ho-so không có) — KHÔNG tích.
               `--ke-hoach` tự chạy việc `hoc_ds` mà kế hoạch đưa ra, rồi lập lại kế hoạch cho kênh đó và
               thêm luôn trong cùng phiên Chrome. Mọi lượt mở hộp (trừ --thu) cũng ghi lại sổ học.

    --thu      tìm nút Lưu trên trang xem, KHÔNG bấm gì (kiểm bộ chọn trang xem + đúng kênh)
    --doc-hop  bấm «Lưu» để MỞ hộp, đọc danh sách phát + trạng thái tích của đích, đóng — KHÔNG tích

Luật an toàn (như máy đăng/bình luận DOM): giữ khoá máy (`agent.giu_khoa_may_chung`), van IPv4 mở là
không nối, xác minh ĐÚNG kênh (UC ghim `logs/kenh-uc.json` qua `MayDangDom.lay_uc` — cũng TẠM đặt giao
diện `vi`), cuối phiên `ngon_ngu_tam.tra` TRẢ ngôn ngữ gốc; chỉ đóng tab của mình; Chrome do máy này mở
thì đóng lại. Chỉ tích ĐÚNG MỘT hàng khớp nguyên văn; hàng đã tích sẵn → `da_co`, không bấm (bấm lần
nữa là BỎ tích). Không bao giờ tạo danh sách phát mới, không bỏ tích hàng nào.

Mã thoát: 0 xong · 1 có việc hỏng · 3 đường DOM không dùng được · 4 bị chặn an toàn.
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
DUONG_BAO_CAO = os.path.join(THU_MUC_LOG, "keo-cheo-cuoi.json")
#: 8765–8775 là dải trạm có thể lùi sang (`core/tram_nen.py`) — khoá máy này đứng ngoài dải.
CONG_KHOA = 8781
URL_XEM = "https://www.youtube.com/watch?v={id}"

MA_XONG, MA_HONG, MA_LUI, MA_CHAN = 0, 1, 3, 4
CHE_DO = ("that", "thu", "doc_hop")

#: Khoá `phan_tu` máy này cần trong studio-selectors.json.
KHOA_KEO_CHEO = ("kc_nut_luu", "kc_nut_them", "kc_menu_luu", "kc_hop_luu", "kc_hang_ds",
                 "kc_ten_ds", "kc_o_tich", "kc_dong_hop")

log = logging.getLogger("keo_cheo_dom")


class LoiKeoCheo(Exception):
    def __init__(self, buoc: str, ly_do: str):
        super().__init__("{0}: {1}".format(buoc, ly_do))
        self.buoc = buoc
        self.ly_do = ly_do


def chuan_ten(s) -> str:
    """So tên danh sách phát: NFKC, gộp khoảng trắng, bỏ đầu cuối (không đổi hoa/thường)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def _hang_hop(hop: dict) -> list:
    """`[{ten, chu_hang}]` của mọi hàng đọc được — thứ sổ học danh sách phát (`ds-kenh.json`) cần."""
    return [{"ten": chuan_ten(h.get("ten")), "chu_hang": str(h.get("chu_hang") or "")[:120]}
            for h in (hop or {}).get("hang") or [] if chuan_ten(h.get("ten"))]


def hang_cua(hop: dict, ten: str) -> list:
    """Các hàng trong hộp có tên KHỚP NGUYÊN VĂN (sau chuẩn hoá) với `ten`."""
    dich = chuan_ten(ten)
    return [h for h in (hop or {}).get("hang") or [] if chuan_ten(h.get("ten")) == dich]


# ── JS chạy trong thế giới riêng của TrangStudio (dùng `window.__yd`) ─────────

_JS_LOC_CHU = r"""
(function(spec){
  const Y = window.__yd; if (!Y) return {khop: false, loi: 'chưa có __yd'};
  const roots = Y.goc(), chu = (spec.chu || []).map(Y.chuan);
  const ds = spec.chon || [];
  for (let i = 0; i < ds.length; i++) {
    let els = []; try { els = Y.qsa(roots, ds[i]).filter(Y.hien); } catch (e) { continue; }
    for (const e of els) {
      const t = Y.chuan(e.innerText), a = Y.chuan(e.getAttribute('aria-label'));
      if (chu.indexOf(t) >= 0 || chu.indexOf(a) >= 0) return Y.tra(e, 'chon#' + (i + 1), ds[i], els.length);
    }
  }
  return {khop: false};
})(%s)
"""

_JS_DOC_HOP = r"""
(function(sHop, sHang, sTen, sTich){
  const Y = window.__yd; if (!Y) return {hop: false, hang: [], loi: 'chưa có __yd'};
  const roots = Y.goc();
  let hop = null, cach = '';
  const dsHop = sHop.chon || [];
  for (let i = 0; i < dsHop.length && !hop; i++) {
    let x = []; try { x = Y.qsa(roots, dsHop[i]).filter(Y.hien); } catch (e) {}
    if (x.length) { hop = x[x.length - 1]; cach = 'chon#' + (i + 1); }
  }
  if (!hop) return {hop: false, hang: []};
  let rows = [];
  for (const s of (sHang.chon || [])) { try { rows = Y.trong(hop, s).filter(Y.hien); } catch (e) { rows = []; } if (rows.length) break; }
  rows = rows.filter(r => !rows.some(o => o !== r && Y.chua(o, r)));
  const ra = [];
  for (const r of rows) {
    let ten = '';
    for (const s of (sTen.chon || [])) {
      let x = []; try { x = Y.trong(r, s).filter(Y.hien); } catch (e) {}
      if (x.length) { ten = Y.chuan(x[0].innerText || x[0].getAttribute('title') || ''); if (ten) break; }
    }
    if (!ten) ten = Y.chuan(String(r.innerText || r.getAttribute('aria-label') || '').split('\n')[0]);
    let nut = null;
    for (const s of (sTich.chon || [])) {
      let x = []; try { x = Y.trong(r, s).filter(Y.hien); } catch (e) {}
      if (x.length) { nut = x[0]; break; }
    }
    const ung = [r].concat(nut ? [nut] : []).concat(Y.trong(r, '[aria-checked],[aria-pressed],[aria-selected],input[type=checkbox]'));
    let chon = null;
    for (const c of ung) {
      if (c.tagName === 'INPUT' && c.type === 'checkbox') { chon = !!c.checked; break; }
      for (const at of ['aria-checked', 'aria-pressed', 'aria-selected']) {
        const v = c.getAttribute(at);
        if (v === 'true' || v === 'false') { chon = (v === 'true'); break; }
      }
      if (chon !== null) break;
    }
    const o = Y.tra(nut || r, 'kc_hang', '', 1);
    o.khoa = 'kc_hang_ds'; o.ten = ten; o.chon = chon; o.chu_hang = Y.chuan(r.innerText).slice(0, 120);
    ra.push(o);
  }
  return {hop: true, cach: cach, mo_ta_hop: Y.moTa(hop), hang: ra};
})(%s, %s, %s, %s)
"""


class TrangXem:
    """Trang xem youtube.com trên một `cdp_studio.TrangStudio` (cùng thế giới JS riêng, cùng `bam` có
    kiểm đích). Bài kiểm thay bằng trang giả cùng giao diện: mo_video/url/tim/tim_loc_chu/bam/doc_hop/
    phim_esc/chup."""

    def __init__(self, tr, bo: dict):
        self.tr = tr
        self.bo = bo
        self.du_phong = getattr(tr, "du_phong", {})

    def _spec(self, khoa: str) -> dict:
        return dict(((self.bo.get("phan_tu") or {}).get(khoa)) or {})

    def mo_video(self, vid: str) -> None:
        url = str((self.bo.get("url") or {}).get("xem") or URL_XEM).format(id=vid)
        self.tr.mo(url, han=60)

    def url(self) -> str:
        return self.tr.url()

    def tim(self, khoa: str):
        return self.tr.tim(khoa, han=0)

    def tim_loc_chu(self, khoa: str):
        spec = self._spec(khoa)
        kq = self.tr.js_tho(_JS_LOC_CHU % json.dumps(
            {"chon": spec.get("chon") or [], "chu": spec.get("chu") or []}, ensure_ascii=False))
        if isinstance(kq, dict) and kq.get("khop"):
            kq["khoa"] = khoa
            return kq
        return None

    def bam(self, pt) -> None:
        self.tr.bam(pt)

    def doc_hop(self) -> dict:
        doi = [json.dumps({"chon": self._spec(k).get("chon") or []}, ensure_ascii=False)
               for k in ("kc_hop_luu", "kc_hang_ds", "kc_ten_ds", "kc_o_tich")]
        kq = self.tr.js_tho(_JS_DOC_HOP % tuple(doi))
        return kq if isinstance(kq, dict) else {"hop": False, "hang": []}

    def phim_esc(self) -> None:
        self.tr.phim("Escape")

    def chup(self, nhan: str) -> str:
        return self.tr.chup(nhan)


class KeoCheo:
    """Một việc kéo chéo trên trang xem (thật: `TrangXem`; kiểm: trang giả)."""

    #: Số lượt dò × `ngu(NGHI)` — đếm lượt (không đồng hồ) nên trang giả chạy tức thì.
    SO_LAN_CHO = 20
    NGHI = 0.5

    def __init__(self, trang, nhat_ky=None, ngu=None):
        self.trang = trang
        self.nk = nhat_ky or log.info
        self.ngu = ngu or time.sleep
        self.buoc = ""

    def _cho(self, ham, so_lan: int = None):
        for _ in range(int(so_lan or self.SO_LAN_CHO)):
            kq = ham()
            if kq:
                return kq
            self.ngu(self.NGHI)
        return ham()

    def _hop_co_hang(self):
        h = self.trang.doc_hop()
        return h if h.get("hop") and h.get("hang") else None

    def _hop_da_dong(self) -> bool:
        return not self.trang.doc_hop().get("hop")

    def tim_nut_luu(self):
        """`(phần tử, cách)` — cách `truc_tiep` (nút Lưu cạnh Thích/Chia sẻ) | `menu` (nằm trong «⋯»)."""
        def thu():
            pt = self.trang.tim("kc_nut_luu")
            if pt:
                return pt, "truc_tiep"
            pm = self.trang.tim("kc_nut_them")
            if pm:
                return pm, "menu"
            return None
        return self._cho(thu) or (None, "")

    def mo_hop(self) -> dict:
        self.buoc = "nut_luu"
        pt, cach = self.tim_nut_luu()
        if not pt:
            raise LoiKeoCheo("nut_luu", "không thấy nút Lưu trên trang xem (video riêng tư/đã gỡ, hay bộ chọn lệch)")
        self.trang.bam(pt)
        if cach == "menu":
            self.buoc = "menu_luu"
            pm = self._cho(lambda: self.trang.tim_loc_chu("kc_menu_luu"), so_lan=10)
            if not pm:
                self.trang.phim_esc()
                raise LoiKeoCheo("menu_luu", "mở «⋯» nhưng không thấy mục Lưu/保存/Save")
            self.trang.bam(pm)
        self.buoc = "hop_luu"
        hop = self._cho(self._hop_co_hang)
        if not hop:
            raise LoiKeoCheo("hop_luu", "bấm Lưu mà không thấy hộp danh sách phát (có hàng)")
        return hop

    def dong_hop(self) -> None:
        self.buoc = "dong_hop"
        pt = self.trang.tim("kc_dong_hop")
        if pt:
            try:
                self.trang.bam(pt)
            except Exception as loi:  # noqa: BLE001 — nút đóng hụt thì Escape
                self.nk("đóng hộp Lưu bằng nút hụt ({0}) — Escape".format(str(loi)[:80]))
                self.trang.phim_esc()
        else:
            self.trang.phim_esc()
        if self._cho(self._hop_da_dong, so_lan=10):
            return
        self.trang.phim_esc()
        if not self._cho(self._hop_da_dong, so_lan=6):
            raise LoiKeoCheo("dong_hop", "hộp Lưu không đóng (nút đóng + 2 lần Escape)")

    def _dong_im(self) -> None:
        try:
            if not self._hop_da_dong():
                self.dong_hop()
        except Exception:  # noqa: BLE001 — đường lỗi: không che lỗi gốc
            pass

    def _mot_hang(self, hop: dict, ten: str) -> dict:
        khop = hang_cua(hop, ten)
        if not khop:
            co = [h.get("ten") for h in hop.get("hang") or []]
            raise LoiKeoCheo("tim_ds", "không có danh sách phát «{0}» trong hộp (có: {1})".format(
                ten, " | ".join(str(x) for x in co[:15]) or "—"))
        if len(khop) > 1:
            raise LoiKeoCheo("tim_ds", "{0} hàng cùng tên «{1}» — không đoán".format(len(khop), ten))
        h = khop[0]
        if h.get("chon") is None:
            raise LoiKeoCheo("trang_thai", "không đọc được trạng thái tích của «{0}»".format(ten))
        return h

    def hoc_ds(self, vid: str) -> dict:
        """HỌC tên danh sách phát: mở trang xem `vid` → bấm Lưu → đọc mọi hàng → đóng. KHÔNG tích gì.
        Trả `{ket: hoc_ds:ok | loi:<bước>: <lý do>, hang_hop: [{ten, chu_hang}]}`."""
        kq = {"video_id": vid, "che_do": "hoc_ds", "ket": "", "luc": time.strftime("%Y-%m-%d %H:%M:%S")}
        hop_mo = False
        try:
            self.buoc = "mo"
            self.trang.mo_video(vid)
            u = str(self.trang.url() or "")
            if vid not in u:
                raise LoiKeoCheo("mo", "trang xem không phải video {0} (url {1})".format(vid, u[:100]))
            hop = self.mo_hop()
            hop_mo = True
            kq["hang_hop"] = _hang_hop(hop)
            if not kq["hang_hop"]:
                raise LoiKeoCheo("hop_luu", "hộp Lưu mở nhưng không đọc được tên hàng nào")
            self.dong_hop()
            hop_mo = False
            kq["ket"] = "hoc_ds:ok"
            self.nk("học danh sách phát qua {0}: {1}".format(vid, " | ".join(h["ten"] for h in kq["hang_hop"])))
        except LoiKeoCheo as loi:
            kq["ket"] = "loi:{0}: {1}".format(loi.buoc, loi.ly_do)
            kq["loi_buoc"] = loi.buoc
        except Exception as loi:  # noqa: BLE001
            kq["ket"] = "loi:{0}: {1}".format(self.buoc or "?", str(loi)[:200])
            kq["loi_buoc"] = self.buoc or "?"
        if kq["ket"].startswith("loi"):
            self.nk("học danh sách phát qua {0}: {1}".format(vid, kq["ket"]))
            if hop_mo:
                self._dong_im()
            try:
                kq["anh"] = self.trang.chup("keo-cheo-hoc-loi-{0}".format(vid))
            except Exception:  # noqa: BLE001
                pass
        return kq

    def them(self, vid: str, ten_ds: str, che_do: str = "that") -> dict:
        """Thêm `vid` vào danh sách phát `ten_ds`. `che_do`: that | thu (không bấm gì) | doc_hop (mở hộp,
        đọc, đóng — không tích). Trả `{ket: ok|da_co|thu:ok|doc_hop:<tt>|loi:<bước>: <lý do>, ...}`."""
        if che_do not in CHE_DO:
            raise ValueError("che_do phải là một trong {0}".format(CHE_DO))
        kq = {"video_id": vid, "danh_sach_phat": ten_ds, "che_do": che_do, "ket": "",
              "luc": time.strftime("%Y-%m-%d %H:%M:%S")}
        hop_mo = False
        try:
            self.buoc = "mo"
            self.trang.mo_video(vid)
            u = str(self.trang.url() or "")
            if vid not in u:
                raise LoiKeoCheo("mo", "trang xem không phải video {0} (url {1})".format(vid, u[:100]))
            if che_do == "thu":
                self.buoc = "nut_luu"
                pt, cach = self.tim_nut_luu()
                if not pt:
                    raise LoiKeoCheo("nut_luu", "không thấy nút Lưu trên trang xem")
                kq["nut_luu"] = "{0} ({1})".format(cach, pt.get("cach") or pt.get("mo_ta") or "")
                kq["ket"] = "thu:ok"
                return kq
            hop = self.mo_hop()
            hop_mo = True
            kq["danh_sach_co"] = [h.get("ten") for h in hop.get("hang") or []]
            kq["hang_hop"] = _hang_hop(hop)
            self.buoc = "tim_ds"
            h = self._mot_hang(hop, ten_ds)
            if che_do == "doc_hop":
                kq["ket"] = "doc_hop:" + ("da_tich" if h["chon"] else "chua_tich")
                self.dong_hop()
                hop_mo = False
                return kq
            if h["chon"]:
                self.nk("«{0}» đã có video {1} — không bấm (bấm nữa là bỏ tích)".format(ten_ds, vid))
                kq["ket"] = "da_co"
                self.dong_hop()
                hop_mo = False
                return kq
            self.buoc = "tich"
            self.trang.bam(h)

            def da_tich():
                k = hang_cua(self.trang.doc_hop(), ten_ds)
                return len(k) == 1 and k[0].get("chon") is True
            if not self._cho(da_tich, so_lan=16):
                raise LoiKeoCheo("tich", "đã bấm «{0}» nhưng hộp chưa hiện tích".format(ten_ds))
            self.dong_hop()
            hop_mo = False
            self.ngu(2.0)
            self.buoc = "doc_lai"
            hop2 = self.mo_hop()
            hop_mo = True
            k2 = hang_cua(hop2, ten_ds)
            ok = len(k2) == 1 and k2[0].get("chon") is True
            self.dong_hop()
            hop_mo = False
            if not ok:
                raise LoiKeoCheo("doc_lai", "mở lại hộp: «{0}» KHÔNG còn tích (YouTube chưa lưu?)".format(ten_ds))
            kq["ket"] = "ok"
            self.nk("đã thêm {0} vào «{1}» — đọc lại: đã tích".format(vid, ten_ds))
        except LoiKeoCheo as loi:
            kq["ket"] = "loi:{0}: {1}".format(loi.buoc, loi.ly_do)
            kq["loi_buoc"] = loi.buoc
        except Exception as loi:  # noqa: BLE001 — lỗi CDP/bấm: ghi bước đang làm, không chết im lặng
            kq["ket"] = "loi:{0}: {1}".format(self.buoc or "?", str(loi)[:200])
            kq["loi_buoc"] = self.buoc or "?"
        if kq["ket"].startswith("loi"):
            self.nk("kéo chéo {0} → «{1}»: {2}".format(vid, ten_ds, kq["ket"]))
            if hop_mo:
                self._dong_im()
            try:
                kq["anh"] = self.trang.chup("keo-cheo-loi-{0}".format(vid))
            except Exception:  # noqa: BLE001
                pass
        return kq


# ── chạy trên Chrome thật ───────────────────────────────────────────────────

def chuan_bi_bo(bo: dict) -> tuple:
    """`(bộ chọn dùng cho máy này, [lỗi])` — `cam_bam_keo_cheo` (nếu có) thay `cam_bam`."""
    bo = copy.deepcopy(bo or {})
    loi = []
    pt = bo.get("phan_tu") or {}
    for k in KHOA_KEO_CHEO:
        if k not in pt:
            loi.append("thiếu khoá phan_tu.{0}".format(k))
    if bo.get("cam_bam_keo_cheo"):
        bo["cam_bam"] = {k: v for k, v in bo["cam_bam_keo_cheo"].items() if k != "ghi_chu"}
    return bo, loi


def _kc():
    if GOC_TOOL not in sys.path:
        sys.path.insert(0, GOC_TOOL)
    from core import keo_cheo  # noqa: PLC0415
    return keo_cheo


def _thu_muc_so() -> str:
    return _kc().thu_muc_mac_dinh(GOC_TOOL)


#: Lỗi ở các bước này = hộp Lưu không đọc được → lượt sau phải học lại danh sách phát của kênh.
BUOC_HOC_LAI = ("hop_luu", "trang_thai", "menu_luu")


def ghi_sau_viec(kenh: str, hd: dict, kq: dict, che_do: str, thu_muc: str, ghi_so: bool = True) -> None:
    """Sổ sách sau MỘT việc: tên hàng hộp Lưu đọc được → sổ học `ds-kenh.json` (mọi chế độ trừ `thu`);
    hộp không đọc được → đánh dấu học lại; việc `them` thật → sổ đã thêm `da-them.json`."""
    try:
        kc = _kc()
        vid = str(hd.get("video_id") or "")
        if kq.get("hang_hop"):
            kc.ghi_ds_kenh(thu_muc, kenh, kq["hang_hop"], video=vid)
        elif str(kq.get("loi_buoc") or "") in BUOC_HOC_LAI:
            kc.danh_dau_can_hoc(thu_muc, kenh, kq.get("ket") or "")
        if (hd.get("viec") or "them") == "them" and che_do == "that" and ghi_so:
            kc.ghi_ket_qua(thu_muc, hd, kq["ket"], chi_tiet={k: v for k, v in kq.items() if k != "ket"})
    except Exception as loi:  # noqa: BLE001 — không ghi được sổ: báo to, việc trên YouTube đã xong
        log.error("KHÔNG ghi được sổ kéo chéo (%s) — việc %s/%s: %s", loi, hd.get("kenh_chu"),
                  hd.get("video_id"), kq.get("ket"))


def chay_viec(may, kenh: str, viec: list, che_do: str = "that", thu_muc: str = None, them_sau=None,
              ngu=None, ghi_so: bool = True, du_phong=None) -> list:
    """Chạy lần lượt các việc của MỘT kênh lớn trên một `KeoCheo` đã nối: `hoc_ds` trước, rồi `them`.
    Có việc học thành công và `them_sau` → gọi `them_sau()` (lập lại kế hoạch cho kênh này, sổ học đã
    mới) và nối các việc `them` mới vào CÙNG phiên Chrome. Trả [việc + `ket` + `chi_tiet`]."""
    ngu = ngu or time.sleep
    thu_muc = thu_muc or _thu_muc_so()
    loai = lambda hd: hd.get("viec") or "them"  # noqa: E731
    hang = [hd for hd in viec if loai(hd) == "hoc_ds"] + [hd for hd in viec if loai(hd) == "them"]
    ra = []
    da_hoc = False
    i = 0
    while i < len(hang):
        hd = hang[i]
        i += 1
        vid = str(hd.get("video_id") or "")
        if loai(hd) == "hoc_ds":
            if che_do == "thu":
                log.info("%s: --thu không mở hộp Lưu — bỏ việc học danh sách phát", kenh)
                ra.append(dict(hd, ket="thu:bo_qua_hoc_ds"))
                continue
            if not vid:
                ra.append(dict(hd, ket="loi:khong_video: không biết video công khai nào của {0} — chạy {1}".format(
                    kenh, hd.get("lenh") or "--hoc-ds --video <id>")))
                continue
            if ra:
                ngu(random.uniform(4.0, 9.0))
            kq = may.hoc_ds(vid)
            da_hoc = da_hoc or kq["ket"] == "hoc_ds:ok"
        else:
            if ra:
                ngu(random.uniform(4.0, 9.0))
            kq = may.them(vid, str(hd["danh_sach_phat"]), che_do)
        if du_phong is not None:
            kq["du_phong"] = dict(du_phong() or {})
        log.info("%s: [%s/%s] %s%s: %s", kenh, loai(hd), che_do, vid,
                 " → «{0}»".format(hd.get("danh_sach_phat")) if loai(hd) == "them" else "", kq["ket"])
        ghi_sau_viec(kenh, hd, kq, che_do, thu_muc, ghi_so)
        ra.append(dict(hd, ket=kq["ket"], chi_tiet=kq))
        if i == len(hang) and da_hoc and them_sau is not None:
            co = {str(h.get("video_id")) for h in hang if loai(h) == "them"}
            try:
                moi = [h for h in (them_sau() or []) if loai(h) == "them" and str(h.get("video_id")) not in co]
            except Exception as loi:  # noqa: BLE001
                log.warning("%s: lập lại kế hoạch sau khi học danh sách phát lỗi: %s", kenh, loi)
                moi = []
            them_sau = None
            if moi:
                log.info("%s: học xong danh sách phát → thêm %d việc mới", kenh, len(moi))
                hang += moi
    return ra


def chay_kenh(kenh: str, viec: list, che_do: str = "that", tu_giu: bool = True,
              ghi_so: bool = True, ngu=None, them_sau=None) -> tuple:
    """Mọi việc của MỘT kênh lớn trên Chrome của nó. Trả `(mã thoát, [kết quả])`."""
    import agent  # noqa: PLC0415
    import cdp as cdp_mod  # noqa: PLC0415
    import cdp_studio  # noqa: PLC0415
    import may_dang_dom as mdd  # noqa: PLC0415

    ngu = ngu or time.sleep
    ra = []
    if tu_giu and not agent.giu_khoa_may_chung(viec="keo_cheo", kenh=kenh, uu_tien=1):
        log.error("%s: không giữ được khoá máy (.khoa-may) — có việc nặng đang chạy; không ép", kenh)
        return MA_CHAN, ra
    cdp = None
    md = None
    try:
        if agent.van_ipv4_mo():
            log.error("van IPv4 đang mở — không nối Chrome kênh")
            return MA_CHAN, ra
        cfg = agent.doc_cau_hinh()
        bo_goc = cdp_studio.doc_bo_chon()
        loi_bo = cdp_studio.kiem_bo_chon(bo_goc)
        bo, loi_kc = chuan_bi_bo(bo_goc)
        if loi_bo or loi_kc:
            log.error("studio-selectors.json lỗi: %s", "; ".join(loi_bo + loi_kc))
            return MA_LUI, ra
        try:
            cdp = cdp_mod.ket_noi_kenh(cfg, kenh, nhat_ky=log.info)
        except cdp_mod.CdpKhongDung as loi:
            log.error("không dùng được đường DOM: %s (mã %d)", loi.ly_do, loi.ma)
            return loi.ma, ra
        log.info("đã nối Chrome kênh %s (%s, cổng %s%s)", kenh, cdp.phien_ban, cdp.cong,
                 ", máy này tự mở" if cdp.tu_mo else "")

        def tao_trang():
            return cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=log.info, thu_muc_dom=cdp_studio.THU_MUC_DOM)

        md = mdd.MayDangDom(kenh, bo, tao_trang, mdd.SoVideoId(), bao=None, thu_muc_done="", nhat_ky=log.info)
        try:
            md.lay_uc()   # đúng kênh (UC ghim) + tạm giao diện vi; `finally` trả ngôn ngữ gốc
        except mdd.DungKenh as loi:
            log.error("%s", loi)
            return MA_CHAN, ra
        except Exception as loi:  # noqa: BLE001
            log.error("không đọc được UC kênh %s: %s", kenh, loi)
            return MA_LUI, ra
        trang = TrangXem(md.tab_b(), bo)
        may = KeoCheo(trang, nhat_ky=log.info)
        ra = chay_viec(may, kenh, viec, che_do, them_sau=them_sau, ngu=ngu, ghi_so=ghi_so,
                       du_phong=lambda: trang.du_phong)
        return (MA_HONG if any(str(x["ket"]).startswith("loi") for x in ra) else MA_XONG), ra
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
                log.info("đóng Chrome kênh %s (máy này đã mở): %s", kenh,
                         "cổng đã đóng" if ok else "CỔNG CHƯA ĐÓNG sau 20s")
            else:
                cdp.dong()
        if tu_giu:
            agent.nha_khoa_may_chung()


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
        tay.append(RotatingFileHandler(os.path.join(THU_MUC_LOG, "keo-cheo.log"),
                                       maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8"))
    except OSError:
        pass
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    for t in tay:
        t.setFormatter(fmt)
        log.addHandler(t)
    log.setLevel(logging.INFO)


def _doc_lenh(argv):
    ap = argparse.ArgumentParser(prog="keo_cheo_dom.py")
    ap.add_argument("--kenh", help="kênh LỚN (Chrome của nó); với --ke-hoach: chỉ chạy kênh này")
    ap.add_argument("--video", help="videoId của kênh em")
    ap.add_argument("--ds", help="tên danh sách phát của kênh lớn (khớp nguyên văn)")
    ap.add_argument("--kenh-video", default="", help="kênh em sở hữu video (để ghi mốc đo; bỏ trống = tự tìm)")
    ap.add_argument("--ke-hoach", action="store_true", help="chạy kế hoạch hôm nay (core.keo_cheo.lap_ke_hoach)")
    ap.add_argument("--in-ke-hoach", action="store_true", help="chỉ in kế hoạch hôm nay, không Chrome")
    ap.add_argument("--ngay", default="", help="YYYY-MM-DD cho --ke-hoach/--in-ke-hoach (mặc định hôm nay)")
    ap.add_argument("--thu", action="store_true", help="dò nút Lưu, KHÔNG bấm gì")
    ap.add_argument("--doc-hop", action="store_true", help="mở hộp Lưu, đọc trạng thái, đóng — KHÔNG tích")
    ap.add_argument("--hoc-ds", action="store_true",
                    help="với --kenh: mở một video công khai của kênh, đọc tên danh sách phát trong hộp Lưu, ghi "
                         "workspace/keo-cheo/ds-kenh.json — KHÔNG tích (--video để chọn video)")
    ap.add_argument("--trong-phien", action="store_true", help="agent gọi giữa phiên — không tự giữ khoá máy")
    return ap.parse_args(argv)


def _ke_hoach(ngay: str, do: bool = False) -> list:
    """Kế hoạch hôm nay; `do` (chỉ lượt THẬT) — trước đó đo các lần thêm đã đủ ngày (ghi `do_sau` vào sổ)."""
    if GOC_TOOL not in sys.path:
        sys.path.insert(0, GOC_TOOL)
    from core import keo_cheo  # noqa: PLC0415
    if not do:
        return keo_cheo.lap_ke_hoach(GOC_TOOL, ngay or None, nhat_ky=log.info)
    try:
        for m in keo_cheo.do_hieu_qua(GOC_TOOL):
            log.info("đo kéo chéo %s → %s (%s): %s", m.get("video_id"), m.get("kenh_chu"),
                     m.get("danh_sach_phat"), (m.get("do_sau") or {}).get("ket"))
    except Exception as loi:  # noqa: BLE001 — đo hỏng không chặn việc hôm nay
        log.warning("đo hiệu quả kéo chéo lỗi: %s", loi)
    return keo_cheo.lap_ke_hoach(GOC_TOOL, ngay or None, nhat_ky=log.info)


def _viec_tay(a) -> dict:
    hd = {"kenh_chu": a.kenh, "danh_sach_phat": a.ds, "video_id": a.video, "kenh_video": a.kenh_video,
          "cum": "", "cach_chon": "tay", "ly_do": "lệnh tay", "ngay": time.strftime("%Y-%m-%d")}
    try:
        if GOC_TOOL not in sys.path:
            sys.path.insert(0, GOC_TOOL)
        from core import keo_cheo  # noqa: PLC0415
        duong_so = os.path.join(GOC, "logs", "so-video-id.json")
        if not hd["kenh_video"]:
            hd["kenh_video"] = keo_cheo.tim_kenh_cua_video(GOC_TOOL, a.video, duong_so)
        if hd["kenh_video"]:
            hd["du_doan"] = keo_cheo.du_doan_cho(GOC_TOOL, hd["kenh_video"], a.video)
    except Exception as loi:  # noqa: BLE001 — thiếu mốc đo không chặn lệnh tay
        log.warning("không lấy được mốc đo cho %s: %s", a.video, loi)
    return hd


def main(argv=None) -> int:
    a = _doc_lenh(sys.argv[1:] if argv is None else argv)
    _cai_nhat_ky()
    che_do = "thu" if a.thu else ("doc_hop" if a.doc_hop else "that")
    if a.thu and a.doc_hop:
        log.error("--thu và --doc-hop: chọn một")
        return MA_HONG
    if a.in_ke_hoach:
        for hd in _ke_hoach(a.ngay):
            if (hd.get("viec") or "them") == "them":
                log.info("[them] %s → «%s»: %s (%s) — %s", hd["kenh_chu"], hd["danh_sach_phat"], hd["video_id"],
                         hd["kenh_video"], hd["ly_do"])
            else:
                log.info("[%s] %s — %s", hd.get("viec"), hd["kenh_chu"], hd["ly_do"])
        return MA_XONG
    them_sau = {}
    if a.hoc_ds:
        if not a.kenh:
            log.error("--hoc-ds cần --kenh")
            return MA_HONG
        vid = a.video or ""
        if not vid:
            try:
                vid = _kc().video_de_hoc(GOC_TOOL, a.kenh, os.path.join(GOC, "logs", "so-video-id.json"))
            except Exception as loi:  # noqa: BLE001
                log.warning("không tìm được video công khai của %s: %s", a.kenh, loi)
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or ""):
            log.error("không biết video công khai nào của %s — chạy lại với --video <videoId công khai của kênh>",
                      a.kenh)
            return MA_HONG
        viec = [{"viec": "hoc_ds", "kenh_chu": a.kenh, "video_id": vid, "ly_do": "lệnh tay --hoc-ds"}]
        che_do = "doc_hop" if che_do == "that" else che_do
    elif a.ke_hoach:
        ke = _ke_hoach(a.ngay, do=che_do == "that")
        for hd in ke:
            if hd.get("viec") == "bao":
                log.warning("CẦN NGƯỜI: %s", hd["ly_do"])
        viec = [hd for hd in ke if (hd.get("viec") or "them") in ("them", "hoc_ds")
                and (not a.kenh or hd["kenh_chu"] == a.kenh)]
        for k in {hd["kenh_chu"] for hd in viec if hd.get("viec") == "hoc_ds"}:
            # học xong danh sách phát → lập lại kế hoạch cho kênh này, chạy luôn trong CÙNG phiên Chrome
            them_sau[k] = (lambda kk: lambda: [h for h in _ke_hoach(a.ngay) if h.get("kenh_chu") == kk])(k)
    else:
        if not (a.kenh and a.video and a.ds):
            log.error("cần --kenh, --video, --ds (hoặc --ke-hoach)")
            return MA_HONG
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", a.video):
            log.error("--video %r không phải videoId", a.video)
            return MA_HONG
        hd = _viec_tay(a)
        if hd.get("kenh_video") == a.kenh:
            log.error("video %s là của CHÍNH kênh %s — kéo chéo chỉ cho video kênh em", a.video, a.kenh)
            return MA_HONG
        viec = [hd]
    if not viec:
        log.info("kéo chéo: không có việc nào hôm nay")
        return MA_XONG
    if not _khoa_mot_minh():
        log.error("đã có một máy kéo chéo khác đang chạy (cổng %d) — thoát", CONG_KHOA)
        return MA_CHAN
    theo_kenh = {}
    for hd in viec:
        theo_kenh.setdefault(hd["kenh_chu"], []).append(hd)
    ma_cuoi = MA_XONG
    tat_ca = []
    for kenh, ds in theo_kenh.items():          # MỘT Chrome một lúc
        log.info("kênh %s: %d việc kéo chéo (%s)", kenh, len(ds), che_do)
        ma, ra = chay_kenh(kenh, ds, che_do, tu_giu=not a.trong_phien, them_sau=them_sau.get(kenh))
        tat_ca += ra or [dict(hd, ket="loi:khong_chay: mã {0}".format(ma)) for hd in ds]
        if ma != MA_XONG:
            ma_cuoi = ma if ma_cuoi == MA_XONG else max(ma_cuoi, ma)
    try:
        os.makedirs(THU_MUC_LOG, exist_ok=True)
        with open(DUONG_BAO_CAO, "w", encoding="utf-8") as tep:
            json.dump({"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "che_do": che_do, "ma_thoat": ma_cuoi,
                       "viec": tat_ca}, tep, ensure_ascii=False, indent=1, default=str)
    except OSError:
        pass
    try:
        import agent  # noqa: PLC0415
        agent.ghi("kéo chéo DOM [{0}]: {1} việc · ok {2} · lỗi {3} · mã {4}".format(
            che_do, len(tat_ca), sum(1 for x in tat_ca if str(x.get("ket")) in ("ok", "da_co", "hoc_ds:ok")),
            sum(1 for x in tat_ca if str(x.get("ket")).startswith("loi")), ma_cuoi))
    except Exception:  # noqa: BLE001
        pass
    return ma_cuoi


if __name__ == "__main__":
    raise SystemExit(main())
