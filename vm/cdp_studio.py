"""Thao tác trên trang YouTube Studio bằng DOM qua CDP — `TrangStudio`.

Thiết kế: `workspace/THIET-KE-MAY-DANG-DOM.md` mục 2.1 + hợp đồng mục 10.

Mọi bộ chọn nằm ở `vm/studio-selectors.json` (sửa không cần code). Mỗi khoá có
`chon` (thử lần lượt — `chon#1` là đường CHÍNH, còn lại là DỰ PHÒNG) và `chu`
(dự phòng cuối: so chữ/aria-label BẰNG của nút). Khớp bằng dự phòng thì ghi
`DU PHONG` — `--kiem-dom` báo mức cảnh báo để người sửa JSON biết bộ chọn
chính đã lệch.

Thao tác CÓ XÁC MINH (không bấm mù như đường ảnh):

* `bam`: cuộn vào giữa → đọc lại khung → `elementFromPoint` ở điểm định bấm
  phải là chính phần tử/con của nó (bị che → thử điểm khác trong khung → dẹp
  hộp lạ/hộp che, ẩn tooltip → chờ → dò lại khoá, tối đa 4 lần; hết lần mới
  `el.click()` cho nút an toàn `BAM_JS_AN_TOAN`) →
  từ chối nếu là nút "Gửi ý kiến phản hồi" (`cam_bam` — nghi nguồn hộp "Allow
  … see this tab?") → `Input.dispatchMouseEvent` (isTrusted) vài bước di chuột
  lệch nhẹ rồi nhấn/nhả ở điểm ngẫu nhiên trong 35% nửa kích thước → kiểm hậu
  điều kiện.
* `go`: bấm ô → Ctrl+A → `Input.insertText` (nhiều dòng: từng dòng + phím
  Enter) → ĐỌC LẠI so chuẩn hoá; lệch → thử lại 1 lần → vẫn lệch = lỗi.
* `dat_tep`: bấm nút → chờ `Page.fileChooserOpened` (hộp chọn tệp Windows đã
  bị chặn) → `DOM.setFileInputFiles`.

JS chạy trong THẾ GIỚI RIÊNG "yd" (`Page.createIsolatedWorld`) — trang không
thấy biến của mình, và mình không bật `Runtime.enable`.
"""

from __future__ import annotations

import base64
import json
import os
import random
import re
import time
import unicodedata

from cdp import CdpLoi, CdpHetHan

GOC = os.path.dirname(os.path.abspath(__file__))
DUONG_BO_CHON = os.path.join(GOC, "studio-selectors.json")
THU_MUC_DOM = os.path.join(GOC, "logs", "dom")
GIU_BO_BANG_CHUNG = 50

#: Khoá mà luồng đăng + --kiem-dom cần — test canh JSON phải đủ.
KHOA_BAT_BUOC = (
    "hop_upload", "nut_chon_tep", "o_tep_video", "link_video", "tieu_de", "mo_ta",
    "nut_thumbnail", "playlist_mo", "playlist_muc", "playlist_xong", "khong_tre_em",
    "hien_them", "ai_co", "o_the", "the_da_co", "tien_do", "nut_tiep", "buoc_hien_thi",
    "phu_de_them", "mhkt_nhap", "mhkt_them", "the_them", "len_lich_mo", "o_ngay_mo",
    "o_ngay", "o_gio", "nut_xong", "hop_da_xong", "dong_hop_da_xong", "dong_hop_upload",
    "hang_video", "hang_tieu_de", "hang_sua_nhap", "hien_thi_trang_sua",
)
KHOA_URL = ("studio", "upload", "danh_sach", "loc_tieu_de", "sua")

#: Số lần thử khi điểm bấm bị che (mỗi lần: cuộn giữa → điểm khác → dẹp che → chờ).
SO_LAN_BAM_CHE = 4
#: Khoá được phép bấm bằng JS (`el.click()`) khi bấm thật bị che cả
#: SO_LAN_BAM_CHE lần — chỉ nút AN TOÀN (đi tiếp / mở trình soạn / Xong phụ đề /
#: đóng hộp con), hậu điều kiện vẫn kiểm. Ghi đè: `bam_js_an_toan` trong JSON.
BAM_JS_AN_TOAN = ("nut_tiep", "the_them", "phu_de_xong", "hop_con_huy", "the_dong_chon")


class LoiThaoTac(Exception):
    """Một thao tác trên trang không làm được (không thấy, bị che, đọc lại lệch...)."""

    def __init__(self, khoa: str, ly_do: str):
        super().__init__("{0}: {1}".format(khoa, ly_do))
        self.khoa = khoa
        self.ly_do = ly_do


def doc_bo_chon(duong: str = None) -> dict:
    with open(duong or DUONG_BO_CHON, "r", encoding="utf-8") as tep:
        return json.load(tep)


def kiem_bo_chon(bo: dict) -> list:
    """Danh sách lỗi cấu trúc của tệp bộ chọn ([] = ổn)."""
    loi = []
    pt = (bo or {}).get("phan_tu") or {}
    for k in KHOA_BAT_BUOC:
        if k not in pt:
            loi.append("thiếu khoá phan_tu.{0}".format(k))
    for k, spec in pt.items():
        if not isinstance(spec, dict):
            loi.append("{0}: không phải object".format(k))
            continue
        chon = spec.get("chon") or []
        chu = spec.get("chu") or []
        if not isinstance(chon, list) or not isinstance(chu, list):
            loi.append("{0}: chon/chu phải là mảng".format(k))
        if not chon and not chu:
            loi.append("{0}: không có chon lẫn chu".format(k))
        for s in chon:
            if not isinstance(s, str) or not s.strip():
                loi.append("{0}: bộ chọn rỗng".format(k))
            elif s.count("[") != s.count("]") or s.count("(") != s.count(")") \
                    or s.count("'") % 2 or s.count('"') % 2:
                loi.append("{0}: bộ chọn lệch ngoặc/nháy: {1}".format(k, s))
    url = (bo or {}).get("url") or {}
    for k in KHOA_URL:
        if k not in url:
            loi.append("thiếu url.{0}".format(k))
    if "{uc}" not in str(url.get("upload", "")) or "{id}" not in str(url.get("sua", "")):
        loi.append("url.upload phải có {uc}, url.sua phải có {id}")
    if "{q}" not in str(url.get("loc_tieu_de", "")):
        loi.append("url.loc_tieu_de phải có {q}")
    cam = (bo or {}).get("cam_bam") or {}
    if not cam.get("aria_chua") or not cam.get("chon"):
        loi.append("thiếu cam_bam")
    return loi


def chuan_chu(s) -> str:
    """Chuẩn hoá để so chữ: NFKC, gộp khoảng trắng, bỏ đầu cuối."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def chuan_nhieu_dong(s) -> str:
    """Chuẩn hoá chữ NHIỀU DÒNG (mô tả): giữ xuống dòng, bỏ khoảng trắng cuối dòng."""
    s = unicodedata.normalize("NFKC", str(s or "")).replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace(" ", " ")
    return "\n".join(d.rstrip() for d in s.split("\n")).strip("\n").strip()


def khop_doc_lai(mong: str, doc: str) -> str:
    """So chữ đọc lại. Trả 'dung' | 'gan' (chỉ lệch dòng TRỐNG — contenteditable
    hay nhân đôi dòng trống) | 'lech'. 'gan' vẫn chấp nhận: dòng có chữ và thứ
    tự xuống dòng giữa chúng còn nguyên — đúng thứ cần giữ cho mục 目次."""
    a, b = chuan_nhieu_dong(mong), chuan_nhieu_dong(doc)
    if a == b:
        return "dung"
    la = [d for d in a.split("\n") if d.strip()]
    lb = [d for d in b.split("\n") if d.strip()]
    if la == lb:
        return "gan"
    return "lech"


def diem_bam(rect: dict, rng=None) -> tuple:
    """Điểm bấm ngẫu nhiên trong 35% nửa kích thước quanh tâm khung."""
    rng = rng or random
    x, y = float(rect["x"]), float(rect["y"])
    w, h = float(rect["w"]), float(rect["h"])
    cx, cy = x + w / 2.0, y + h / 2.0
    dx = rng.uniform(-0.35, 0.35) * w / 2.0
    dy = rng.uniform(-0.35, 0.35) * h / 2.0
    return round(cx + dx, 1), round(cy + dy, 1)


# ── JS trong thế giới riêng ─────────────────────────────────────────────
# Cài một lần mỗi ngữ cảnh (điều hướng là mất → tự cài lại). Trả về JSON thuần.
_JS_CAI = r"""
(function(CAM){
if (window.__yd && window.__yd.v === 7) { window.__yd.cam_spec = CAM; return true; }
const Y = {v: 7, ghim: {}, dem: 0, cam_spec: CAM};
Y.chuan = s => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
Y.goc = function(){
  const ra = [document], q = [document];
  while (q.length) { const r = q.pop();
    const all = r.querySelectorAll('*');
    for (let i = 0; i < all.length; i++) { const s = all[i].shadowRoot;
      if (s) { ra.push(s); q.push(s); } } }
  return ra;
};
Y.qsa = function(roots, sel){
  const ra = [], thay = new Set();
  for (const r of roots) { for (const e of r.querySelectorAll(sel)) {
    if (!thay.has(e)) { thay.add(e); ra.push(e); } } }
  return ra;
};
Y.trong = function(e, sel){          // tìm trong e (kể cả shadowRoot bên trong)
  const roots = [e]; const q = [e];
  while (q.length) { const r = q.pop();
    for (const x of r.querySelectorAll('*')) { if (x.shadowRoot) { roots.push(x.shadowRoot); q.push(x.shadowRoot); } } }
  return Y.qsa(roots, sel);
};
Y.hien = function(e){
  if (!e || !e.isConnected) return false;
  const r = e.getBoundingClientRect();
  if (r.width < 1 || r.height < 1) return false;
  if (e.checkVisibility && !e.checkVisibility({checkOpacity: true, checkVisibilityCSS: true})) return false;
  const cs = getComputedStyle(e);
  if (cs.visibility === 'hidden' || cs.display === 'none') return false;
  return true;
};
Y.tat = function(e){
  const t = x => x && (x.getAttribute('aria-disabled') === 'true' || x.hasAttribute('disabled'));
  if (t(e)) return true;
  const c = e.closest ? e.closest('ytcp-button,tp-yt-paper-button,tp-yt-paper-radio-button,button,tp-yt-paper-icon-button,ytcp-icon-button') : null;
  return !!(c && c !== e && t(c));
};
Y.chaCua = n => n.parentNode ? (n.parentNode.host || n.parentNode) : (n.host || null);
Y.cam = function(e){
  const C = Y.cam_spec || {};
  const chua = (C.aria_chua || []).map(s => s.toLowerCase());
  let n = e, sau = 0;
  while (n && n.nodeType === 1 && sau < 8) {
    for (const s of (C.chon || [])) { try { if (n.matches(s)) return 'khớp ' + s; } catch (err) {} }
    const a = ((n.getAttribute('aria-label') || '') + ' ' + (n.getAttribute('title') || '')).toLowerCase();
    for (const w of chua) if (w && a.indexOf(w) >= 0) return 'aria chứa ' + w;
    n = Y.chaCua(n); sau++;
  }
  const t = Y.chuan(e.innerText).toLowerCase();
  if (t.length < 40) for (const w of chua) if (w && t.indexOf(w) >= 0) return 'chữ chứa ' + w;
  return '';
};
Y.moTa = function(e){
  if (!e || e.nodeType !== 1) return String(e);
  let s = e.tagName.toLowerCase();
  if (e.id) s += '#' + e.id;
  const a = e.getAttribute('aria-label'); if (a) s += '[aria-label="' + a.slice(0, 40) + '"]';
  return s;
};
Y.khung = e => { const r = e.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; };
Y.tra = function(e, cach, sel, so){
  if (Y.dem > 800) { Y.ghim = {}; Y.dem = 0; }
  const id = 'p' + (++Y.dem); Y.ghim[id] = e;
  return {khop: true, cach: cach, sel: sel, so: so, id: id, tag: e.tagName.toLowerCase(),
          rect: Y.khung(e), tat: Y.tat(e), cam: Y.cam(e), mo_ta: Y.moTa(e)};
};
Y.UNG_CHU = 'ytcp-button, button, [role=button], [role=radio], [role=tab], [role=menuitem], [role=option], [role=checkbox], tp-yt-paper-radio-button, tp-yt-paper-item, tp-yt-paper-button, ytcp-ve, a';
Y.tim = function(spec, o){
  o = o || {}; const roots = o.trong && Y.ghim[o.trong] ? null : Y.goc();
  const qsa = sel => (o.trong && Y.ghim[o.trong]) ? Y.trong(Y.ghim[o.trong], sel) : Y.qsa(roots, sel);
  const hop = e => (o.an || spec.an || Y.hien(e)) && (o.cho_tat || !Y.tat(e));
  const ds = spec.chon || [], loi = [];
  for (let i = 0; i < ds.length; i++) {
    let els; try { els = qsa(ds[i]); } catch (err) { loi.push(ds[i]); continue; }
    const ok = els.filter(hop);
    if (ok.length) { const e = ok[Math.min(o.thu || 0, ok.length - 1)];
      return Y.tra(e, 'chon#' + (i + 1), ds[i], ok.length); }
  }
  const chu = (spec.chu || []).map(Y.chuan);
  if (chu.length) {
    for (const e of qsa(Y.UNG_CHU)) {
      if (!hop(e)) continue;
      const t = Y.chuan(e.innerText), a = Y.chuan(e.getAttribute('aria-label'));
      if (chu.indexOf(t) >= 0 || chu.indexOf(a) >= 0) return Y.tra(e, 'chu', t || a, 1);
    }
  }
  return {khop: false, loi_bo_chon: loi};
};
Y.timChua = function(spec, s){       // phần tử khớp spec mà outerHTML chứa s (id video trong ảnh)
  const roots = Y.goc();
  for (const sel of (spec.chon || [])) { let els; try { els = Y.qsa(roots, sel); } catch (err) { continue; }
    for (const e of els) if (Y.hien(e) && e.outerHTML.indexOf(s) >= 0) return Y.tra(e, 'chua', sel, 1); }
  return {khop: false};
};
Y.docTatCa = function(spec){        // chữ + value của MỌI phần tử hiện khớp spec (đọc lại hàng loạt)
  const roots = Y.goc(), ra = [];
  for (const sel of (spec.chon || [])) { let els; try { els = Y.qsa(roots, sel); } catch (err) { continue; }
    for (const e of els) { if (!Y.hien(e)) continue; const i = e.querySelector ? e.querySelector('input') : null;
      ra.push({chu: Y.chuan(e.innerText), value: i ? i.value : (e.value || ''), y: Math.round(e.getBoundingClientRect().y)}); }
    if (ra.length) break; }
  return ra;
};
Y.cuon = function(id){
  const e = Y.ghim[id]; if (!e || !e.isConnected) return null;
  e.scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});
  return {rect: Y.khung(e), hien: Y.hien(e), tat: Y.tat(e), cam: Y.cam(e)};
};
Y.chua = function(a, b){ let n = b; while (n) { if (n === a) return true; n = Y.chaCua(n); } return false; };
Y.trungDiem = function(id, x, y){
  const e = Y.ghim[id]; if (!e || !e.isConnected) return {ok: false, ly_do: 'mất phần tử'};
  let h = document.elementFromPoint(x, y);
  while (h && h.shadowRoot) { const h2 = h.shadowRoot.elementFromPoint(x, y); if (!h2 || h2 === h) break; h = h2; }
  if (!h) return {ok: false, ly_do: 'không có gì ở điểm bấm'};
  if (Y.chua(e, h)) return {ok: true};
  if (Y.chua(h, e)) {
    const re = Y.khung(e), rh = Y.khung(h);
    if (rh.w * rh.h <= Math.max(4 * re.w * re.h, 2500) && h !== document.body && h !== document.documentElement)
      return {ok: true, ghi_chu: 'trúng cha sát ' + Y.moTa(h)};
  }
  const idChe = 'p' + (++Y.dem); Y.ghim[idChe] = h;
  return {ok: false, ly_do: 'bị che bởi ' + Y.moTa(h), che: idChe};
};
// Điểm KHÁC trong khung phần tử mà không bị che (thanh cuộn/tooltip/panel chỉ
// đè một phần — đo 29–30/09: "bị che bởi div#scrollbar").
Y.diemTrong = function(id){
  const e = Y.ghim[id]; if (!e || !e.isConnected) return {ok: false};
  const r = e.getBoundingClientRect(), W = window.innerWidth, H = window.innerHeight;
  const fx = [0.5, 0.3, 0.7, 0.15, 0.85], fy = [0.5, 0.25, 0.75];
  for (const b of fy) for (const a of fx) {
    const x = r.x + r.width * a, y = r.y + r.height * b;
    if (x < 1 || y < 1 || x > W - 1 || y > H - 1) continue;
    let h = document.elementFromPoint(x, y);
    while (h && h.shadowRoot) { const h2 = h.shadowRoot.elementFromPoint(x, y); if (!h2 || h2 === h) break; h = h2; }
    if (h && Y.chua(e, h)) return {ok: true, x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10};
  }
  return {ok: false};
};
// Loại phần tử đang che: tooltip | man (scrim/backdrop) | xem_truoc (panel xem
// trước phụ đề của trình soạn phụ đề) | menu | khac.
Y.loaiChe = function(cheId){
  let n = Y.ghim[cheId], sau = 0;
  while (n && n.nodeType === 1 && sau < 14) {
    const t = n.tagName.toLowerCase();
    if (t.indexOf('tooltip') >= 0 || n.getAttribute('role') === 'tooltip') return 'tooltip';
    if (t.indexOf('backdrop') >= 0 || t.indexOf('scrim') >= 0) return 'man';
    if (t === 'ytve-preview-panel' || t === 'ytve-captions-editor-modal') return 'xem_truoc';
    if (t === 'tp-yt-paper-listbox' || t === 'ytcp-text-menu' || n.getAttribute('role') === 'listbox'
        || n.getAttribute('role') === 'menu') return 'menu';
    n = Y.chaCua(n); sau++;
  }
  return 'khac';
};
// Ẩn tooltip đang che (chỉ tooltip — phần trang trí, không đổi trạng thái).
Y.anTooltip = function(cheId){
  let n = Y.ghim[cheId], sau = 0;
  while (n && n.nodeType === 1 && sau < 14) {
    const t = n.tagName.toLowerCase();
    if (t.indexOf('tooltip') >= 0 || n.getAttribute('role') === 'tooltip') {
      n.style.visibility = 'hidden'; n.style.pointerEvents = 'none'; return Y.moTa(n); }
    n = Y.chaCua(n); sau++;
  }
  return '';
};
// Bấm bằng JS (el.click()) — chỉ dùng cho nút AN TOÀN khi bấm thật bị che mãi.
Y.bamJs = function(id){
  const e = Y.ghim[id]; if (!e || !e.isConnected) return {ok: false, ly_do: 'mất phần tử'};
  if (Y.tat(e)) return {ok: false, ly_do: 'nút đang bị vô hiệu'};
  const b = e.tagName === 'BUTTON' ? e : (Y.trong(e, 'button').filter(Y.hien)[0] || e);
  b.click();
  return {ok: true, mo_ta: Y.moTa(b)};
};
Y.chu = function(id){ const e = Y.ghim[id]; if (!e) return null;
  if ('value' in e && (e.tagName === 'INPUT' || e.tagName === 'TEXTAREA')) return e.value;
  return e.innerText; };
Y.thuocTinh = function(id, ten){ const e = Y.ghim[id]; if (!e) return null;
  if (ten === 'value' || ten === 'href' || ten === 'checked') { const v = e[ten]; return v == null ? null : String(v); }
  return e.getAttribute(ten); };
Y.lay = id => Y.ghim[id] || null;
Y.focus = function(id){ const e = Y.ghim[id]; if (!e) return false; e.focus(); return document.activeElement ? Y.moTa(document.activeElement) : ''; };
Y.chonHet = function(id){ const e = Y.ghim[id]; if (!e) return false; e.focus();
  if (e.select) { e.select(); return true; }
  const s = document.getSelection(); s.removeAllRanges(); const r = document.createRange(); r.selectNodeContents(e); s.addRange(r); return true; };
Y.hopLa = function(ds, cheId, mucId){
  const roots = Y.goc(), ra = [];
  const che = cheId ? Y.ghim[cheId] : null;
  const muc = mucId ? Y.ghim[mucId] : null;
  const da = new Set();                        // một nút chỉ bấm một lần
  for (const h of ds) {
    let hops; try { hops = Y.qsa(roots, h.chon).filter(Y.hien); } catch (err) { continue; }
    for (const d of hops) {
      if (che && !Y.chua(d, che)) continue;
      if (muc && Y.chua(d, muc)) continue;     // hộp chứa chính nút đang bấm: không đóng
      for (const s of (h.dong || [])) {
        let nut; try { nut = Y.trong(d, s).filter(Y.hien); } catch (err) { continue; }
        if (nut.length) { if (!da.has(nut[0])) { da.add(nut[0]); ra.push(Y.tra(nut[0], 'hop_la', h.chon, 1)); } break; }
      }
    }
  }
  return ra;
};
Y.hang = function(specHang, specTieu, specNhap, specCheDo, specNgay){
  const roots = Y.goc(); let rows = [];
  for (const s of (specHang.chon || [])) { try { rows = Y.qsa(roots, s).filter(Y.hien); } catch (err) {} if (rows.length) break; }
  const ra = [];
  for (const r of rows) {
    const one = spec => { for (const s of ((spec || {}).chon || [])) { try { const x = Y.trong(r, s).filter(Y.hien); if (x.length) return x[0]; } catch (err) {} } return null; };
    const t = one(specTieu), n = one(specNhap), c = one(specCheDo), ng = one(specNgay);
    const hrefs = Y.trong(r, 'a[href]').map(a => a.href).concat(Y.trong(r, 'img[src]').map(i => i.src));
    const o = Y.tra(r, 'hang', '', 1);
    o.tieu_de = t ? Y.chuan(t.innerText) : ''; o.hrefs = hrefs;
    o.chu = String(r.innerText || '').slice(0, 1500);
    o.che_do = (c ? String(c.innerText || '') : '') + (ng ? '\n' + String(ng.innerText || '') : '');
    o.nut_nhap = n ? Y.tra(n, 'hang_sua_nhap', '', 1) : null;
    ra.push(o);
  }
  return ra;
};
Y.banDo = function(toiDa){
  const roots = Y.goc(), ra = [];
  for (const r of roots) { for (const e of r.querySelectorAll('*')) {
    const t = e.tagName.toLowerCase();
    const lay = t.startsWith('ytcp-') || t.startsWith('tp-yt-') || t.startsWith('ytve-') || t.startsWith('ytgn-')
      || e.hasAttribute('role') || t === 'input' || t === 'textarea' || t === 'button' || t === 'a'
      || e.getAttribute('contenteditable') === 'true';
    if (!lay || !Y.hien(e)) continue;
    const k = Y.khung(e);
    ra.push({tag: t, id: e.id || '', name: e.getAttribute('name') || '', role: e.getAttribute('role') || '',
      aria: (e.getAttribute('aria-label') || '').slice(0, 80), cls: String(e.className || '').slice(0, 60),
      chu: Y.chuan(e.innerText).slice(0, 60), href: t === 'a' ? String(e.href || '').slice(0, 120) : '',
      tat: Y.tat(e), sau: r !== document, rect: [Math.round(k.x), Math.round(k.y), Math.round(k.w), Math.round(k.h)]});
    if (ra.length >= toiDa) return ra;
  } }
  return ra;
};
window.__yd = Y; return true;
})
"""

_PHIM = {
    "Enter": ("Enter", "Enter", 13, "\r"),
    "Escape": ("Escape", "Escape", 27, ""),
    "Tab": ("Tab", "Tab", 9, ""),
    "Backspace": ("Backspace", "Backspace", 8, ""),
    "Delete": ("Delete", "Delete", 46, ""),
    "ArrowDown": ("ArrowDown", "ArrowDown", 40, ""),
    "ArrowUp": ("ArrowUp", "ArrowUp", 38, ""),
    "End": ("End", "End", 35, ""),
    "Home": ("Home", "Home", 36, ""),
}


class TrangStudio:
    """Một TAB Studio do máy đăng tự mở (hợp đồng mục 10).

    `cdp`: `cdp.Cdp` cấp trình duyệt; `sid`/`target_id` của tab. Không đụng tab
    khác của Chrome."""

    def __init__(self, cdp, target_id: str, sid: str, bo_chon: dict = None,
                 nhat_ky=None, thu_muc_dom: str = None, ngu=None, rng=None):
        self.cdp = cdp
        self.target_id = target_id
        self.sid = sid
        self.bo = bo_chon or doc_bo_chon()
        self.nhat_ky = nhat_ky or (lambda _s: None)
        self.thu_muc_dom = thu_muc_dom or THU_MUC_DOM
        self.ngu = ngu or time.sleep
        self.rng = rng or random.Random()
        self._ctx = None
        self._chuot = (self.rng.uniform(200, 600), self.rng.uniform(150, 400))
        self.du_phong = {}          # khoa -> cách khớp (khác chon#1)
        self.ghi_dom_day_du = False

    # ── tạo / đóng ───────────────────────────────────────────────────────
    @classmethod
    def mo_tab_moi(cls, cdp, bo_chon: dict = None, **kw) -> "TrangStudio":
        tid, sid = cdp.tao_tab("about:blank")
        return cls(cdp, tid, sid, bo_chon=bo_chon, **kw)

    def dong(self) -> None:
        self.cdp.giu_tab.discard(self.sid)
        self.cdp.dong_tab(self.target_id)

    def giu_khi_roi(self, giu: bool = True) -> None:
        """Tab đang tải video: beforeunload bị TỪ CHỐI (không rời trang)."""
        (self.cdp.giu_tab.add if giu else self.cdp.giu_tab.discard)(self.sid)

    def len_truoc(self) -> None:
        try:
            self.cdp.goi("Page.bringToFront", sid=self.sid, han=10)
        except CdpLoi:
            pass

    # ── JS ───────────────────────────────────────────────────────────────
    def _tao_the_gioi(self) -> int:
        cay = self.cdp.goi("Page.getFrameTree", sid=self.sid, han=15)
        fid = cay["frameTree"]["frame"]["id"]
        ctx = self.cdp.goi("Page.createIsolatedWorld",
                           {"frameId": fid, "worldName": "yd",
                            "grantUniveralAccess": False}, sid=self.sid,
                           han=15)["executionContextId"]
        cam = json.dumps(self.bo.get("cam_bam") or {}, ensure_ascii=False)
        self._eval_tho("({0})({1})".format(_JS_CAI.strip(), cam), ctx)
        self._ctx = ctx
        return ctx

    def _eval_tho(self, bieu_thuc: str, ctx: int, gia_tri: bool = True, han: float = 30.0):
        r = self.cdp.goi("Runtime.evaluate", {
            "expression": bieu_thuc, "contextId": ctx, "returnByValue": gia_tri,
            "awaitPromise": False, "userGesture": False}, sid=self.sid, han=han)
        if r.get("exceptionDetails"):
            ex = r["exceptionDetails"]
            chu = ((ex.get("exception") or {}).get("description") or ex.get("text") or "lỗi JS")
            raise CdpLoi("JS: {0}".format(str(chu)[:200]))
        kq = r.get("result") or {}
        return kq.get("value") if gia_tri else kq.get("objectId")

    def _js(self, ham: str, *doi, gia_tri: bool = True, han: float = 30.0):
        """Gọi `window.__yd.<ham>(...doi)` trong thế giới riêng; mất ngữ cảnh
        (vừa điều hướng) thì dựng lại thế giới + cài lại rồi thử 1 lần nữa."""
        bt = "window.__yd.{0}({1})".format(ham, ", ".join(
            json.dumps(d, ensure_ascii=False) for d in doi))
        for lan in range(2):
            try:
                ctx = self._ctx if self._ctx is not None else self._tao_the_gioi()
                return self._eval_tho(bt, ctx, gia_tri=gia_tri, han=han)
            except CdpHetHan:
                raise
            except CdpLoi as loi:
                s = str(loi)
                if lan == 0 and ("context" in s.lower() or "__yd" in s
                                 or "undefined" in s or "Cannot find" in s):
                    self._ctx = None
                    continue
                raise
        return None

    def js_tho(self, bieu_thuc: str):
        """Biểu thức JS tuỳ ý trong thế giới riêng (đọc location...)."""
        if self._ctx is None:
            self._tao_the_gioi()
        try:
            return self._eval_tho(bieu_thuc, self._ctx)
        except CdpLoi:
            self._tao_the_gioi()
            return self._eval_tho(bieu_thuc, self._ctx)

    # ── điều hướng ───────────────────────────────────────────────────────
    def mo(self, url: str, cho_khoa: str = None, han: float = 60.0):
        """Điều hướng tab tới `url`, chờ tải xong, rồi (nếu có) chờ `cho_khoa`.
        Trả kết quả `tim(cho_khoa)` (hoặc True)."""
        self.cdp.xoa_su_kien("Page.loadEventFired", self.sid)
        self._ctx = None
        r = self.cdp.goi("Page.navigate", {"url": url}, sid=self.sid, han=min(60, han))
        if r.get("errorText"):
            raise LoiThaoTac("mo", "điều hướng hỏng: {0}".format(r["errorText"]))
        try:
            self.cdp.cho_su_kien("Page.loadEventFired", han=han, sid=self.sid)
        except CdpHetHan:
            self.nhat_ky("trang {0} chưa báo tải xong sau {1:.0f}s — dò tiếp".format(url[:80], han))
        self._ctx = None
        if cho_khoa:
            return self.tim(cho_khoa, han=han)
        return True

    def url(self) -> str:
        try:
            return str(self.js_tho("location.href") or "")
        except CdpLoi:
            return ""

    # ── dò ───────────────────────────────────────────────────────────────
    def _spec(self, khoa: str) -> dict:
        pt = self.bo.get("phan_tu") or {}
        if khoa not in pt:
            raise LoiThaoTac(khoa, "không có trong studio-selectors.json")
        return pt[khoa]

    def tim(self, khoa: str, han: float = 10.0, hien: bool = True,
            cho_tat: bool = False, trong: dict = None, thu: int = 0):
        """Dò `khoa` tới khi thấy hoặc hết `han` giây (hỏi DOM cục bộ mỗi
        0,5–1s, không gọi mạng). Trả dict {khop, cach, rect, id, ...} hoặc None."""
        return self._tim_spec(khoa, self._spec(khoa), han, hien, cho_tat, trong, thu)

    def tim_chu(self, chu: list, han: float = 5.0, cho_tat: bool = False):
        """Dò nút/mục theo CHỮ bằng (mục menu ngôn ngữ...). Không tính dự phòng."""
        pt = self._tim_spec("chu:" + "|".join(chu), {"chon": [], "chu": list(chu)}, han, True,
                            cho_tat, None, 0, ghi_du_phong=False)
        return pt

    def _tim_spec(self, khoa, spec, han, hien=True, cho_tat=False, trong=None, thu=0,
                  ghi_du_phong=True):
        het = time.monotonic() + max(0.0, float(han))
        o = {"an": (not hien) or bool(spec.get("an")), "cho_tat": cho_tat, "thu": thu}
        if trong and trong.get("id"):
            o["trong"] = trong["id"]
        while True:
            try:
                kq = self._js("tim", {"chon": spec.get("chon") or [], "chu": spec.get("chu") or [],
                                      "an": bool(spec.get("an"))}, o)
            except CdpHetHan:
                kq = None
            except CdpLoi as loi:
                self.nhat_ky("dò {0} lỗi JS: {1}".format(khoa, str(loi)[:120]))
                kq = None
            if kq and kq.get("khop"):
                kq["khoa"] = khoa
                if ghi_du_phong and kq.get("cach") != "chon#1":
                    if self.du_phong.get(khoa) != kq.get("cach"):
                        self.nhat_ky("DU PHONG {0}: khớp bằng {1} ({2}) — phần tử {3}".format(
                            khoa, kq.get("cach"), kq.get("sel"), kq.get("mo_ta")))
                    self.du_phong[khoa] = kq.get("cach")
                return kq
            if time.monotonic() >= het:
                return None
            self.cdp.bom(0.1)
            self.ngu(self.rng.uniform(0.5, 1.0))

    def doc_tat_ca(self, khoa: str) -> list:
        """[{chu, value, y}] của mọi phần tử đang hiện khớp `khoa` (theo thứ tự DOM)."""
        try:
            return self._js("docTatCa", {"chon": self._spec(khoa).get("chon") or []}) or []
        except CdpLoi:
            return []

    def tim_chua(self, khoa: str, chuoi: str, han: float = 8.0):
        """Phần tử của `khoa` có outerHTML CHỨA `chuoi` (vd thẻ video mang id
        trong ảnh thu nhỏ — hộp chọn video của trình soạn Thẻ, đo 29/09)."""
        spec = self._spec(khoa)
        het = time.monotonic() + max(0.0, float(han))
        while True:
            try:
                kq = self._js("timChua", {"chon": spec.get("chon") or []}, str(chuoi))
            except CdpLoi:
                kq = None
            if kq and kq.get("khop"):
                kq["khoa"] = khoa
                return kq
            if time.monotonic() >= het:
                return None
            self.ngu(self.rng.uniform(0.5, 1.0))

    def co(self, khoa: str, **kw) -> bool:
        return self.tim(khoa, han=0, **kw) is not None

    def bi_che(self, khoa: str) -> bool:
        """`khoa` đang hiện nhưng tâm của nó bị phần tử khác đè (hộp con còn
        mở — đo 29/09: trình soạn thẻ che nút Tiếp mà nút vẫn "hiện")."""
        pt = self.tim(khoa, han=0, cho_tat=True)
        if not pt:
            return False
        r = pt["rect"]
        kd = self._js("trungDiem", pt["id"], r["x"] + r["w"] / 2.0, r["y"] + r["h"] / 2.0) or {}
        return not kd.get("ok")

    def cho_mat_ca_tat(self, khoa: str, han: float = 10.0) -> bool:
        """Như `cho_mat` nhưng tính cả phần tử đang TẮT (hộp còn mở mà nút mờ)."""
        het = time.monotonic() + han
        while True:
            if self.tim(khoa, han=0, cho_tat=True) is None:
                return True
            if time.monotonic() >= het:
                return False
            self.ngu(self.rng.uniform(0.5, 1.0))

    def cho_mat(self, khoa: str, han: float = 10.0) -> bool:
        """Chờ `khoa` BIẾN MẤT (hộp đóng...)."""
        het = time.monotonic() + han
        while True:
            if self.tim(khoa, han=0) is None:
                return True
            if time.monotonic() >= het:
                return False
            self.ngu(self.rng.uniform(0.5, 1.0))

    # ── chuột / phím ─────────────────────────────────────────────────────
    def _chuot_toi(self, x: float, y: float) -> None:
        x0, y0 = self._chuot
        buoc = self.rng.randint(3, 6)
        for i in range(1, buoc + 1):
            t = i / float(buoc)
            lech = 0 if i == buoc else 2
            xi = x0 + (x - x0) * t + self.rng.uniform(-lech, lech)
            yi = y0 + (y - y0) * t + self.rng.uniform(-lech, lech)
            self.cdp.goi("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": round(xi, 1), "y": round(yi, 1),
                "button": "none", "buttons": 0}, sid=self.sid, han=10)
            self.ngu(self.rng.uniform(0.01, 0.04))
        self._chuot = (x, y)

    def _bam_diem(self, x: float, y: float) -> None:
        self._chuot_toi(x, y)
        self.cdp.goi("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x, "y": y, "button": "left",
            "buttons": 1, "clickCount": 1}, sid=self.sid, han=10)
        self.ngu(self.rng.uniform(0.04, 0.12))
        self.cdp.goi("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x, "y": y, "button": "left",
            "buttons": 0, "clickCount": 1}, sid=self.sid, han=10)

    def bam(self, khoa_hoac_pt, hau_dieu_kien=None, han_hau: float = 10.0,
            han_tim: float = 10.0, cho_tat: bool = False) -> dict:
        """Bấm có kiểm đích. Ném LoiThaoTac nếu không thấy / bị che / cấm /
        hậu điều kiện không đạt. Trả phần tử đã bấm."""
        if isinstance(khoa_hoac_pt, dict):
            pt = khoa_hoac_pt
            khoa = pt.get("khoa") or pt.get("mo_ta") or "phần tử"
        else:
            khoa = khoa_hoac_pt
            pt = self.tim(khoa, han=han_tim, cho_tat=cho_tat)
            if not pt:
                raise LoiThaoTac(khoa, "không thấy")
        if pt.get("cam"):
            raise LoiThaoTac(khoa, "TỪ CHỐI bấm — phần tử cấm ({0})".format(pt["cam"]))
        # Bị che (đo 29–30/09: 42 lần/2 ngày — backdrop đang mờ dần, tooltip,
        # panel xem trước phụ đề, thanh cuộn, menu vừa mở): xử lý TẠI CHỖ —
        # cuộn vào giữa, thử điểm khác trong khung, dẹp/ẩn thứ che, chờ ngắn,
        # dò lại khoá, tối đa SO_LAN_BAM_CHE lần; cuối cùng mới `el.click()`
        # cho nút AN TOÀN. Hậu điều kiện vẫn kiểm như cũ.
        bam_js = False
        for lan in range(SO_LAN_BAM_CHE):
            cu = self._js("cuon", pt["id"])
            if not cu:
                raise LoiThaoTac(khoa, "phần tử đã mất khỏi trang")
            if cu.get("cam"):
                raise LoiThaoTac(khoa, "TỪ CHỐI bấm — phần tử cấm ({0})".format(cu["cam"]))
            if cu.get("tat") and not cho_tat:
                raise LoiThaoTac(khoa, "nút đang bị vô hiệu")
            self.ngu(self.rng.uniform(0.15, 0.35))
            cu = self._js("cuon", pt["id"]) or cu
            x, y = diem_bam(cu["rect"], self.rng)
            kd = self._js("trungDiem", pt["id"], x, y) or {}
            if kd.get("ok"):
                break
            dm = self._js("diemTrong", pt["id"]) or {}
            if dm.get("ok"):
                x, y = float(dm["x"]), float(dm["y"])
                self.nhat_ky("bấm {0}: {1} — bấm điểm khác không bị che ({2}, {3})".format(
                    khoa, kd.get("ly_do"), x, y))
                break
            ly_do = kd.get("ly_do") or "điểm bấm không trúng"
            self.nhat_ky("bấm {0}: {1} (lần {2}/{3})".format(khoa, ly_do, lan + 1, SO_LAN_BAM_CHE))
            if lan == SO_LAN_BAM_CHE - 1:
                if self._duoc_bam_js(khoa):
                    r = self._js("bamJs", pt["id"]) or {}
                    if r.get("ok"):
                        self.nhat_ky("bấm {0}: BẤM BẰNG JS (el.click) sau {1} lần bị che — {2}".format(
                            khoa, SO_LAN_BAM_CHE, r.get("mo_ta")))
                        bam_js = True
                        break
                    ly_do += " · bấm JS hụt: {0}".format(r.get("ly_do") or "không chạy")
                raise LoiThaoTac(khoa, ly_do)
            self._dep_che(kd.get("che"), lan, pt.get("id"))
            self.ngu(self.rng.uniform(0.5, 0.9) * (lan + 1))
            if not isinstance(khoa_hoac_pt, dict):
                # Dò lại: phần tử có thể vừa đổi (menu mở xong thì chon#1 mới
                # khớp — đo 30/09 the_menu_video khớp nhầm tab "Video" bằng chữ
                # rồi bị chính mục menu che).
                moi = self.tim(khoa, han=2, cho_tat=cho_tat)
                if moi:
                    if moi.get("cam"):
                        raise LoiThaoTac(khoa, "TỪ CHỐI bấm — phần tử cấm ({0})".format(moi["cam"]))
                    pt = moi
        if not bam_js:
            self._bam_diem(x, y)
        self.ngu(self.rng.uniform(0.4, 1.5))
        if hau_dieu_kien is not None:
            het = time.monotonic() + han_hau
            while not hau_dieu_kien():
                if time.monotonic() >= het:
                    raise LoiThaoTac(khoa, "bấm xong nhưng hậu điều kiện không đạt")
                self.ngu(self.rng.uniform(0.5, 1.0))
        return pt

    def _duoc_bam_js(self, khoa) -> bool:
        ds = self.bo.get("bam_js_an_toan")
        if not isinstance(ds, list):
            ds = BAM_JS_AN_TOAN
        return str(khoa) in ds

    def _dep_che(self, che, lan: int, muc: str = None) -> None:
        """Dẹp thứ đang che một lần: hộp lạ/hộp che CHỨA nó (`hop_la` +
        `hop_che` của JSON — vd trình soạn phụ đề sót lại thì bấm Xong của nó),
        ẩn tooltip. Backdrop/scrim thường đang mờ dần sau khi hộp con đóng →
        chỉ cần chờ (người gọi chờ). Không bấm Escape: đang trong hộp con
        (trình soạn Thẻ/MHKT) thì Escape có thể đóng luôn hộp của luồng đăng."""
        loai = ""
        try:
            loai = str(self._js("loaiChe", che) or "") if che else ""
        except CdpLoi:
            pass
        if loai == "tooltip":
            try:
                an = self._js("anTooltip", che)
                if an:
                    self.nhat_ky("ẩn tooltip đang che: {0}".format(an))
            except CdpLoi:
                pass
            return
        if self.don_hop_la(che=che, muc=muc) and loai:
            self.nhat_ky("đã dẹp thứ che loại {0} (lần {1})".format(loai, lan + 1))

    def phim(self, ten: str, n: int = 1, modifiers: int = 0) -> None:
        key, code, vk, text = _PHIM[ten]
        for _ in range(max(1, int(n))):
            xuong = {"type": "keyDown" if text else "rawKeyDown", "key": key, "code": code,
                     "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
                     "modifiers": modifiers}
            if text:
                xuong["text"] = text
                xuong["unmodifiedText"] = text
            self.cdp.goi("Input.dispatchKeyEvent", xuong, sid=self.sid, han=10)
            self.cdp.goi("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": key, "code": code, "windowsVirtualKeyCode": vk,
                "nativeVirtualKeyCode": vk, "modifiers": modifiers}, sid=self.sid, han=10)
            self.ngu(self.rng.uniform(0.05, 0.15))

    def _ctrl_a(self) -> None:
        for loai in ("rawKeyDown", "keyUp"):
            p = {"type": loai, "modifiers": 2, "key": "a", "code": "KeyA",
                 "windowsVirtualKeyCode": 65, "nativeVirtualKeyCode": 65}
            if loai == "rawKeyDown":
                p["commands"] = ["selectAll"]
            self.cdp.goi("Input.dispatchKeyEvent", p, sid=self.sid, han=10)
        self.ngu(self.rng.uniform(0.05, 0.15))

    def _chen(self, chu: str) -> None:
        dong = str(chu).replace("\r\n", "\n").replace("\r", "\n").split("\n")
        for i, d in enumerate(dong):
            if i:
                self.phim("Enter")
            if d:
                self.cdp.goi("Input.insertText", {"text": d}, sid=self.sid, han=30)
                self.ngu(self.rng.uniform(0.03, 0.12))

    def go_tho(self, khoa: str, chu: str, xoa: bool = True, han_tim: float = 10.0) -> None:
        """Gõ KHÔNG đọc lại (ô thẻ biến chữ thành chip, ô ngày/giờ đọc lại
        riêng sau Enter). `xoa`: Ctrl+A trước để thay nội dung cũ."""
        self.bam(khoa, han_tim=han_tim)
        if xoa:
            self._ctrl_a()
        self._chen(chu)
        self.ngu(self.rng.uniform(0.2, 0.5))

    def go(self, khoa: str, chu: str, han_tim: float = 10.0) -> str:
        """Gõ `chu` vào ô `khoa` (thay nội dung cũ), ĐỌC LẠI và so. Trả chữ đọc
        lại. Lệch sau 1 lần thử lại → LoiThaoTac."""
        doc = ""
        for lan in range(2):
            pt = self.bam(khoa, han_tim=han_tim)
            if lan == 0:
                self._ctrl_a()
            else:
                self._js("chonHet", pt["id"])
            if chu:
                self._chen(chu)
            else:
                self.phim("Delete")
            self.ngu(self.rng.uniform(0.3, 0.7))
            doc = self.doc_chu(khoa) or ""
            kq = khop_doc_lai(chu, doc)
            if kq != "lech":
                if kq == "gan":
                    self.nhat_ky("gõ {0}: đọc lại chỉ lệch dòng trống — chấp nhận".format(khoa))
                return doc
            self.nhat_ky("gõ {0}: đọc lại LỆCH (lần {1}) — {2!r}".format(
                khoa, lan + 1, chuan_chu(doc)[:80]))
        raise LoiThaoTac(khoa, "đọc lại lệch sau 2 lần gõ")

    # ── đọc ──────────────────────────────────────────────────────────────
    def doc_chu(self, khoa_hoac_pt, han: float = 5.0):
        pt = khoa_hoac_pt if isinstance(khoa_hoac_pt, dict) else self.tim(
            khoa_hoac_pt, han=han, cho_tat=True)
        if not pt:
            return None
        return self._js("chu", pt["id"])

    def doc_thuoc_tinh(self, khoa_hoac_pt, ten: str, han: float = 5.0):
        pt = khoa_hoac_pt if isinstance(khoa_hoac_pt, dict) else self.tim(
            khoa_hoac_pt, han=han, cho_tat=True)
        if not pt:
            return None
        return self._js("thuocTinh", pt["id"], ten)

    def bat_json(self, url: str, chua_url: str, han: float = 30.0, toi_da: int = 4) -> list:
        """Mở `url` trên tab này và BẮT thân JSON các phản hồi có URL chứa
        `chua_url` (vd `get_creator_videos`, `yta_web/get_cards`) — qua miền
        `Fetch` chỉ chặn đúng mẫu URL ấy (không bật `Network`, không đổi gì trên
        trang), đọc thân rồi CHO ĐI TIẾP ngay. Dùng cho hậu kiểm tải lên (thời
        lượng + trạng thái xử lý) và đọc nhanh view 48h khi QUÉT NGÀY đã cũ.
        Trả [] nếu không bắt được gì trong hạn — người gọi tự lùi đường khác."""
        ra = []
        mau = [{"urlPattern": "*" + chua_url + "*", "requestStage": "Response"}]
        try:
            self.cdp.goi("Fetch.enable", {"patterns": mau}, sid=self.sid, han=10)
        except CdpLoi:
            return ra
        try:
            self.cdp.xoa_su_kien("Fetch.requestPaused", self.sid)
            try:
                self.mo(url, han=min(60.0, float(han)))
            except (CdpLoi, LoiThaoTac) as loi:
                self.nhat_ky("bắt gói {0}: mở trang lỗi: {1}".format(chua_url, str(loi)[:100]))
            het = time.monotonic() + float(han)
            while len(ra) < toi_da:
                con = het - time.monotonic()
                if con <= 0:
                    break
                try:
                    p = self.cdp.cho_su_kien("Fetch.requestPaused", han=min(5.0, con), sid=self.sid)
                except CdpHetHan:
                    if ra:
                        break
                    continue
                rid = p.get("requestId")
                try:
                    b = self.cdp.goi("Fetch.getResponseBody", {"requestId": rid}, sid=self.sid, han=15)
                    chu = b.get("body") or ""
                    if b.get("base64Encoded"):
                        chu = base64.b64decode(chu).decode("utf-8", "replace")
                    try:
                        ra.append(json.loads(chu))
                    except ValueError:
                        pass
                except CdpLoi:
                    pass
                finally:
                    try:
                        self.cdp.goi("Fetch.continueRequest", {"requestId": rid}, sid=self.sid, han=10)
                    except CdpLoi:
                        pass
        finally:
            try:
                self.cdp.goi("Fetch.disable", {}, sid=self.sid, han=10)
            except CdpLoi:
                pass
        return ra

    def doc_hang(self) -> list:
        """Các hàng video đang hiện trên trang danh sách: {tieu_de, hrefs, chu,
        che_do, nut_nhap(pt|None), id}."""
        pt = self.bo.get("phan_tu") or {}
        try:
            return self._js("hang", pt.get("hang_video") or {}, pt.get("hang_tieu_de") or {},
                            pt.get("hang_sua_nhap") or {}, pt.get("hang_che_do") or {},
                            pt.get("hang_ngay") or {}) or []
        except CdpLoi as loi:
            self.nhat_ky("đọc hàng video lỗi: {0}".format(str(loi)[:120]))
            return []

    # ── tệp ──────────────────────────────────────────────────────────────
    def dat_tep(self, khoa_nut: str, duong: str, khoa_input: str = None,
                han: float = 8.0) -> str:
        """Bấm nút → chờ hộp chọn tệp (đã bị chặn) → DOM.setFileInputFiles.
        Dự phòng: ô input[type=file] ẩn (`khoa_input`). Trả cách đã dùng."""
        duong = os.path.abspath(duong)
        if not os.path.isfile(duong):
            raise LoiThaoTac(khoa_nut, "không có tệp {0}".format(duong))
        self.cdp.tep_cho.pop(self.sid, None)
        loi_bam = None
        try:
            self.bam(khoa_nut)
        except LoiThaoTac as loi:
            loi_bam = loi
        if loi_bam is None:
            het = time.monotonic() + han
            while time.monotonic() < het:
                p = self.cdp.tep_cho.pop(self.sid, None)
                if p and p.get("backendNodeId"):
                    self.cdp.goi("DOM.setFileInputFiles", {
                        "files": [duong], "backendNodeId": p["backendNodeId"]},
                        sid=self.sid, han=30)
                    return "hop_chon_tep"
                self.cdp.bom(0.3)
        if khoa_input:
            pt = self.tim(khoa_input, han=3, hien=False, cho_tat=True)
            if pt:
                oid = self._js("lay", pt["id"], gia_tri=False)
                if oid:
                    self.cdp.goi("DOM.setFileInputFiles", {"files": [duong], "objectId": oid},
                                 sid=self.sid, han=30)
                    self.nhat_ky("DU PHONG {0}: đặt tệp thẳng vào {1}".format(khoa_nut, khoa_input))
                    self.du_phong[khoa_nut] = "o_tep"
                    return "o_tep"
        raise LoiThaoTac(khoa_nut, "không mở được hộp chọn tệp{0}".format(
            " ({0})".format(loi_bam.ly_do) if loi_bam else ""))

    # ── hộp lạ ───────────────────────────────────────────────────────────
    def don_hop_la(self, che: str = None, muc: str = None) -> int:
        """Đóng hộp chào/khảo sát theo `hop_la`. `che`: chỉ đóng hộp CHỨA phần
        tử đang che (khi bấm bị che) — không đóng bừa hộp của luồng đăng.
        `muc`: id nút đang định bấm — hộp chứa chính nút ấy thì KHÔNG đóng."""
        ds = list(self.bo.get("hop_la") or [])
        if che:
            # `hop_che`: hộp của CHÍNH luồng đăng — chỉ đóng khi nó đang che
            # nút khác (trình soạn phụ đề sót lại → bấm Xong của nó).
            ds += list(self.bo.get("hop_che") or [])
        try:
            nut = (self._js("hopLa", ds, che, muc) if muc else self._js("hopLa", ds, che)) or []
        except CdpLoi:
            return 0
        so = 0
        for pt in nut:
            if pt.get("cam"):
                continue
            try:
                rect = pt["rect"]
                x, y = diem_bam(rect, self.rng)
                self.nhat_ky("dẹp hộp lạ {0} bằng {1}".format(pt.get("sel"), pt.get("mo_ta")))
                self._bam_diem(x, y)
                so += 1
                self.ngu(self.rng.uniform(0.4, 0.9))
            except CdpLoi:
                pass
        return so

    # ── bằng chứng ───────────────────────────────────────────────────────
    def chup(self, nhan: str, han: float = 15.0) -> str:
        try:
            r = self.cdp.goi("Page.captureScreenshot", {"format": "png"}, sid=self.sid, han=han)
        except CdpLoi as loi:
            self.nhat_ky("chụp {0} hụt: {1}".format(nhan, str(loi)[:80]))
            return ""
        os.makedirs(self.thu_muc_dom, exist_ok=True)
        duong = os.path.join(self.thu_muc_dom, "{0}-{1}.png".format(
            time.strftime("%Y%m%d-%H%M%S"), _an_toan(nhan)))
        with open(duong, "wb") as tep:
            tep.write(base64.b64decode(r.get("data") or ""))
        return duong

    def ban_do(self, toi_da: int = 4000) -> list:
        try:
            return self._js("banDo", toi_da, han=60) or []
        except CdpLoi as loi:
            self.nhat_ky("bản đồ DOM lỗi: {0}".format(str(loi)[:120]))
            return []

    def ghi_bang_chung(self, nhan: str) -> dict:
        """Ảnh + bản đồ DOM (+ outerHTML nếu bật) vào vm/logs/dom/, giữ 50 bộ."""
        os.makedirs(self.thu_muc_dom, exist_ok=True)
        tien_to = os.path.join(self.thu_muc_dom, "{0}-{1}".format(
            time.strftime("%Y%m%d-%H%M%S"), _an_toan(nhan)))
        anh = self.chup(nhan)
        bd = self.ban_do()
        with open(tien_to + "-ban-do.json", "w", encoding="utf-8") as tep:
            json.dump({"url": self.url(), "luc": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "nhan": nhan, "so": len(bd), "phan_tu": bd}, tep,
                      ensure_ascii=False, indent=0)
        if self.ghi_dom_day_du:
            try:
                html = self.js_tho("document.documentElement.outerHTML")
                with open(tien_to + "-dom.html", "w", encoding="utf-8") as tep:
                    tep.write(str(html or ""))
            except CdpLoi:
                pass
        don_bang_chung(self.thu_muc_dom)
        return {"anh": anh, "ban_do": tien_to + "-ban-do.json"}


def _an_toan(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(s or "x"))[:60].strip("-") or "x"


def don_bang_chung(thu_muc: str, giu: int = GIU_BO_BANG_CHUNG) -> int:
    """Giữ `giu` bộ bằng chứng mới nhất (bộ = cùng tiền tố thời gian-nhãn)."""
    try:
        ten = os.listdir(thu_muc)
    except OSError:
        return 0
    bo = {}
    for t in ten:
        m = re.match(r"^(\d{8}-\d{6}-[^.]*?)(-ban-do\.json|-dom\.html|\.png)$", t)
        if m:
            bo.setdefault(m.group(1), []).append(t)
    xoa = 0
    for k in sorted(bo)[:-giu] if len(bo) > giu else []:
        for t in bo[k]:
            try:
                os.remove(os.path.join(thu_muc, t))
                xoa += 1
            except OSError:
                pass
    return xoa
