"""TẠO KÊNH THƯƠNG HIỆU MỚI trên youtube.com cho MỘT kênh (19/10/2026) — làm như người thật, MỘT lần cho mỗi kênh.

Dùng khi: mở kênh mới (lần đầu), mở rộng, hoặc kênh bị "không được phân phối" và cần kênh thương hiệu thay thế.

Luồng (trong Chrome Portable của chính kênh, hồ sơ `Data\\profile`, đã đăng nhập bằng `core/dang_nhap_gmail`):
  1. Chặn trước: trong khung cấm (02:00–07:00, 60 phút trước 05:00/20:00) → hoãn; Chrome kênh đang mở → hoãn;
     chưa có tên dự kiến (`workspace/mo-kenh/trang-thai.json: ten_goi_y`) → không làm.
  2. Xác minh TÀI KHOẢN: đọc email trên youtube.com/account; khác email trong kho → DỪNG (`sai_danh_tinh`).
  3. Đã có kênh tên đó (channel_switcher) → ghi `da_co`, không tạo trùng.
  4. Tạo: youtube.com/create_channel → điền tên → xác nhận → đọc lại URL `/channel/UC…` và tên trên trang.
  5. Chọn kênh mới: mở trang kênh mới làm trang cuối rồi đóng Chrome (kênh mới là kênh đang chọn).
  6. Ghi `vm/logs/tao-kenh/<K>.json` (mã UC, tên, thời điểm). Không ghi kenh-uc.json (việc của tl-17).

An toàn: gặp đăng nhập lại / CAPTCHA / xác minh điện thoại → DỪNG, `can_nguoi`, không thử lại trong 6 giờ.
Mọi kết quả chỉ là mã + lý do ngắn; không in email/mật khẩu/cookie.

Chạy:  python vm/tao_kenh_thuong_hieu.py --kenh TL5-T7-K2 [--thu]
       --thu : chỉ đọc (email, kênh đã có) — không tạo.
Mã thoát: 0 xong/đã có · 10 hoãn · 20 cần người · 1 lỗi/chặn.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
from typing import Any, Callable, Dict, Optional

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if GOC not in sys.path:  # chạy thẳng `python vm/tao_kenh_thuong_hieu.py` cần thấy gói core/
    sys.path.insert(0, GOC)
PORT_GO = 9590  # cổng DevTools riêng, tránh dải 9300+ của VM
TRANG_TAI_KHOAN = "https://www.youtube.com/account"
TRANG_CHUYEN_KENH = "https://www.youtube.com/channel_switcher"
TRANG_TAO_KENH = "https://www.youtube.com/create_channel"
HET_GIO_CHO = 25.0
CHU_NUT_TAO = ("Tạo", "Create", "作成", "Crear", "만들기")  # nút xác nhận tạo kênh (vi/en/ja/es)
CHU_TRANG_DANG_NHAP = ("accounts.google.com/signin", "accounts.google.com/v3/signin", "accounts.google.com/servicelogin")
MAU_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@gmail\.com", re.IGNORECASE)
MAU_UC = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]{20,})")


# ── thuần: kiểm được không cần Chrome ─────────────────────────────────────────

def _bay_gio(luc: Optional[float] = None) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(luc) if luc is not None else _dt.datetime.now()


def khung_cam_hien_tai(luc: Optional[float] = None) -> str:
    """Lý do đang trong khung cấm ('' nếu được chạy) — cùng luật với vm/nuoi_trang_chu.py."""
    try:
        from vm import nuoi_trang_chu as nuoi  # noqa: PLC0415
        return nuoi.khung_cam(luc if luc is not None else time.time(), 10.0)
    except Exception:  # noqa: BLE001 — không nạp được luật → cấm cho chắc
        return "không nạp được luật khung cấm"


def tim_email_trong_chu(chu: str) -> str:
    """Email Gmail đầu tiên xuất hiện trên trang tài khoản ('' nếu không thấy)."""
    m = MAU_EMAIL.search(chu or "")
    return m.group(0).lower() if m else ""


def tim_uc_trong_url(url: str) -> str:
    m = MAU_UC.search(url or "")
    return m.group(1) if m else ""


def dang_bi_chan_dang_nhap(url: str) -> bool:
    u = (url or "").lower()
    return any(p in u for p in CHU_TRANG_DANG_NHAP)


def quyet_dinh_truoc_khi_chay(ten: str, kho_email: str, dang_nhap_ket: str,
                              chrome_dang_chay: bool, luc: Optional[float] = None,
                              bo_khung: bool = False) -> tuple:
    """(được_chạy, mã, lý_do). Thứ tự chặn: khung cấm → thiếu tên → chưa xác minh đăng nhập → Chrome đang mở."""
    cam = "" if bo_khung else khung_cam_hien_tai(luc)
    if cam:
        return False, "hoan", cam
    if not (ten or "").strip():
        return False, "hong", "chưa có tên kênh dự kiến (ten_goi_y)"
    if not kho_email:
        return False, "hong", "kho chưa có tài khoản Gmail cho kênh này"
    if dang_nhap_ket != "ok":
        return False, "hong", "chưa đăng nhập xác minh được tài khoản (dang_nhap_ket={0})".format(dang_nhap_ket or "chưa thử")
    if chrome_dang_chay:
        return False, "hoan", "Chrome kênh đang mở — đóng rồi làm tiếp"
    return True, "", ""


def ten_co_trong_trang(ten: str, chu_trang: str) -> bool:
    """Tên kênh đã nằm trong danh sách kênh (so khớp không phân biệt hoa thường, bỏ khoảng trắng thừa)."""
    if not ten:
        return False
    gon = lambda s: re.sub(r"\s+", " ", s or "").strip().lower()  # noqa: E731
    return gon(ten) in gon(chu_trang)


# ── sổ kết quả ───────────────────────────────────────────────────────────────

def duong_so(kenh: str, goc: str = GOC) -> str:
    return os.path.join(goc, "vm", "logs", "tao-kenh", kenh + ".json")


def ghi_so(kenh: str, du: Dict[str, Any], goc: str = GOC) -> None:
    duong = duong_so(kenh, goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du, f, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def doc_so(kenh: str, goc: str = GOC) -> Dict[str, Any]:
    try:
        with open(duong_so(kenh, goc), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


# ── trình duyệt (DrissionPage, Chrome của chính kênh) ───────────────────────

def _mo_chrome_kenh(goc: str, kenh: str):
    from DrissionPage import ChromiumOptions, ChromiumPage  # noqa: PLC0415
    from core.mo_kenh import thu_muc_chrome  # noqa: PLC0415
    exe = thu_muc_chrome(goc, kenh)
    chrome = os.path.join(os.path.dirname(os.path.abspath(exe)), "App", "Chrome-bin", "chrome.exe")
    profile = os.path.join(os.path.dirname(os.path.abspath(exe)), "Data", "profile")
    co = ChromiumOptions(read_file=False)
    co.set_user_data_path(profile)
    co.set_local_port(PORT_GO)
    if os.path.isfile(chrome):
        co.set_browser_path(chrome)
    co.set_argument("--lang=vi")
    return ChromiumPage(co)


def _chu_trang(page) -> str:
    try:
        return str(page.run_js("return document.body ? document.body.innerText : ''") or "")
    except Exception:  # noqa: BLE001
        return ""


def _cho_tai(page, url: str) -> None:
    page.get(url)
    deadline = time.time() + HET_GIO_CHO
    while time.time() < deadline:
        if page.url and not str(page.url).startswith("about:"):
            break
        time.sleep(0.5)
    time.sleep(2)


MO_TAO_LINKS = ("새 채널 만들기", "채널 만들기", "Create a new channel", "Create a channel", "Create new channel", "Tạo kênh mới",
                "Tạo kênh", "チャンネルを作成", "新しいチャンネルを作成")
NUT_XAC_NHAN = ("Create channel", "채널 만들기", "Tạo kênh", "チャンネルを作成", "作成", "만들기", "Create", "Tạo")


O_NHAP_HOP_LE = """
  Array.from(document.querySelectorAll('input')).filter(e => e.offsetParent !== null &&
      !/search|검색|tìm|tim kiếm/i.test((e.placeholder||'') + ' ' + (e.getAttribute('aria-label')||'')))
"""


def _mo_hop_thoai_tao(page) -> bool:
    """Trên trang tài khoản: mở mục tạo kênh mới (liên kết /create_channel, có thể nằm trong menu avatar)
    → chờ hộp thoại có ô nhập tên. True nếu hộp thoại hiện ra."""
    js = """
      const chu = %s;
      let a = Array.from(document.querySelectorAll('a[href^="/create_channel"]')).find(e => e.offsetParent !== null);
      if (a) { a.click(); return 'da_bam'; }
      const el = Array.from(document.querySelectorAll('a, button, [role=button], tp-yt-paper-item, yt-formatted-string'))
          .find(e => e.offsetParent !== null && chu.some(t => (e.innerText||'').trim().startsWith(t)));
      if (!el) return 'khong_thay';
      (el.closest('a, button, [role=button], tp-yt-paper-item') || el).click(); return 'da_bam';
    """ % json.dumps(list(MO_TAO_LINKS), ensure_ascii=False)
    mo_menu = """
      const b = Array.from(document.querySelectorAll('button, yt-img-shadow, #avatar-btn, [role=button]'))
          .find(e => /계정 메뉴|Account menu|Trình đơn tài khoản|アカウント|Tài khoản/.test(e.getAttribute('aria-label')||''));
      if (b) { b.click(); return true; } return false;
    """
    # Đường chính (đã kiểm 19/10): trang chuyển kênh mở bảng chọn kênh → «Create a channel» trong bảng.
    try:
        _cho_tai(page, TRANG_CHUYEN_KENH)
        time.sleep(2)
        bam_bang = page.run_js("""
          const el = Array.from(document.querySelectorAll('*')).filter(e => e.childElementCount === 0 &&
              /^(Create a channel|Create a new channel|채널 만들기|새 채널 만들기|Tạo kênh|Tạo kênh mới|チャンネルを作成)$/.test((e.textContent||'').trim()) &&
              e.offsetParent !== null)[0];
          if (!el) return false;
          (el.closest('a,button,[role=button],tp-yt-paper-item,ytd-compact-link-renderer') || el).click();
          return true;
        """)
        if bam_bang:
            han = time.time() + 15
            while time.time() < han:
                if page.run_js("return (%s).length > 0" % O_NHAP_HOP_LE.strip()):
                    return True
                time.sleep(0.5)
    except Exception:  # noqa: BLE001
        pass
    # Đường dự phòng: liên kết /create_channel hoặc mục trong menu avatar.
    try:
        if page.run_js(js) != "da_bam":
            page.run_js(mo_menu)  # mục nằm trong menu avatar
            time.sleep(2)
            if page.run_js(js) != "da_bam":
                return False
    except Exception:  # noqa: BLE001
        return False
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            if page.run_js("return %s.length > 0" % O_NHAP_HOP_LE.strip()):
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5)
    return False


BIEN_THE_HANDLE = ("", "-tl", "-2", "-3")  # handle dự kiến; nếu trùng thì thử biến thể nhẹ (như thiet_lap_kenh_dom)
TRUNG_HANDLE = ("isn't available", "here's one available", "shorter handle", "không khả dụng", "already",
                "đã được sử dụng", "사용할 수 없", "더 짧은 핸들", "使用できません", "使用されて")


def _xoa_o_handle(page) -> bool:
    """Xoá ô handle (YouTube tự điền handle từ tên — phải xoá trước khi gõ). True nếu ô đã rỗng."""
    return bool(page.run_js("""
      const o = (%s)[1];
      const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      o.focus(); set.call(o, ''); o.dispatchEvent(new Event('input', {bubbles: true}));
      return o.value === '';
    """ % O_NHAP_HOP_LE.strip()))


def _dien_va_bam_tao(page, ten: str, handle: str) -> bool:
    """Gõ tên (ô 1) và handle (ô 2) bằng phím thật — YouTube không nhận giá trị gán bằng JS.
    Handle trùng → thử biến thể nhẹ. Chỉ bấm khi nút đã bật và không báo handle trùng. True nếu đã bấm."""
    from DrissionPage.common import Actions  # noqa: PLC0415
    o = O_NHAP_HOP_LE.strip()
    # Nút xác nhận PHẢI nằm trong hộp thoại (khối chứa ô handle): «채널 만들기» cũng là mục trong bảng chuyển kênh.
    bam = """
      const xn = %s;
      const o2 = (%s)[1];
      if (!o2) return false;
      let hop = o2;
      for (let i = 0; i < 14 && hop.parentElement; i++) {
        hop = hop.parentElement;
        if (hop.querySelectorAll('button, [role=button], yt-button-renderer, tp-yt-paper-button').length >= 2
            && /handle|핸들/i.test(hop.innerText || '')) break;
      }
      const bs = Array.from(hop.querySelectorAll('button, [role=button], yt-button-renderer, tp-yt-paper-button'));
      for (const t of xn) {
        const b = bs.find(e => (e.innerText||'').trim() === t && !e.disabled && e.getAttribute('aria-disabled') !== 'true');
        if (b) { b.click(); return true; }
      }
      return false;
    """ % (json.dumps(list(NUT_XAC_NHAN), ensure_ascii=False), o)
    trung = """
      const t = (document.body.innerText || '').toLowerCase();
      return %s.some(k => t.includes(k.toLowerCase()));
    """ % json.dumps(list(TRUNG_HANDLE), ensure_ascii=False)
    try:
        page.run_js("(%s)[0].focus();" % o)
        time.sleep(0.5)
        Actions(page).type(ten)
        time.sleep(1)
        for duoi in BIEN_THE_HANDLE:
            thu = handle + duoi
            if not _xoa_o_handle(page):
                return False
            page.run_js("(%s)[1].focus();" % o)
            time.sleep(0.5)
            Actions(page).type(thu)
            han = time.time() + 15
            while time.time() < han:
                time.sleep(1)
                if page.run_js(bam):  # nút chỉ bật khi handle hợp lệ — không bấm được trong 15 giây → biến thể kế
                    return True
            # sang biến thể kế tiếp
        return False
    except Exception:  # noqa: BLE001
        return False


def _uc_cua_ten(page, ten: str) -> str:
    """Mã UC của kênh có tên `ten` trên trang tài khoản (liên kết /channel/UC… gần chữ tên)."""
    try:
        href = page.run_js("""
          const ten = %s;
          const a = Array.from(document.querySelectorAll('a[href*="/channel/UC"]'))
              .find(e => (e.innerText||'').includes(ten) || (e.closest('div,ytd-channel-name') || {innerText:''}).innerText.includes(ten));
          return a ? a.getAttribute('href') : '';
        """ % json.dumps(ten, ensure_ascii=False))
        return tim_uc_trong_url(href or "")
    except Exception:  # noqa: BLE001
        return ""


# ── luồng chính ───────────────────────────────────────────────────────────────

def tao(kenh: str, *, goc: str = GOC, thu: bool = False, bo_khung: bool = False,
        ghi: Callable[[str], None] = print) -> Dict[str, Any]:
    """Chạy một lượt. Trả dict {"ket_qua","ly_do","uc","ten"} — không có email/cookie."""
    from core import dang_nhap_gmail as dn  # noqa: PLC0415
    from core import mo_kenh  # noqa: PLC0415

    st = mo_kenh.doc_trang_thai(goc)
    d = (st.get("kenh") or {}).get(kenh, {})
    ten = str(d.get("ten_goi_y") or "").strip()
    handle = str(d.get("handle") or "").strip().lstrip("@")
    dn_ket = str(d.get("dang_nhap_ket") or "")
    kho_email = ""
    try:
        vm = os.path.join(goc, "vm")
        if vm not in sys.path:
            sys.path.insert(0, vm)
        import kho_bi_mat  # noqa: PLC0415
        kho_email = str((kho_bi_mat.tai_khoan(kenh) or {}).get("email") or "").strip().lower()
    except Exception:  # noqa: BLE001
        kho_email = ""

    # Danh tính được xác minh TRONG luồng (email trên trang tài khoản phải khớp kho trước khi làm gì),
    # nên cổng dang_nhap_ket không cần chặn trước. Giữ tham số để nếu có trạng thái thật thì vẫn đọc được.
    duoc, ma, ly = quyet_dinh_truoc_khi_chay(ten, kho_email, "ok" if (thu or dn_ket in ("", "chua_thu")) else dn_ket,
                                             dn.chrome_dang_chay(mo_kenh.thu_muc_chrome(goc, kenh)),
                                             bo_khung=bo_khung)
    if not duoc:
        ket = {"ket_qua": ma, "ly_do": ly, "ten": ten}
        ghi("tạo kênh thương hiệu {0}: {1} — {2}".format(kenh, ma, ly))
        return ket

    page = None
    ket: Dict[str, Any] = {"ket_qua": "hong", "ly_do": "chưa chạy", "ten": ten, "uc": ""}
    try:
        page = _mo_chrome_kenh(goc, kenh)
        _cho_tai(page, TRANG_TAI_KHOAN)
        if dang_bi_chan_dang_nhap(page.url):
            return {**ket, "ket_qua": "can_nguoi", "ly_do": "Chrome đòi đăng nhập lại"}
        that = tim_email_trong_chu(_chu_trang(page))
        if that and kho_email and that != kho_email:
            return {**ket, "ket_qua": "sai_danh_tinh", "ly_do": "tài khoản trong Chrome không phải tài khoản của kênh"}
        if not that:
            return {**ket, "ket_qua": "chua_xac_minh", "ly_do": "không đọc được email tài khoản — không tạo kênh"}

        if ten_co_trong_trang(ten, _chu_trang(page)):
            ket = {"ket_qua": "da_co", "ly_do": "kênh tên này đã có trên tài khoản", "ten": ten,
                   "uc": _uc_cua_ten(page, ten)}
        elif thu:
            ket = {"ket_qua": "chi_doc", "ly_do": "chưa có kênh tên này — chạy lại không --thu để tạo", "ten": ten, "uc": ""}
        else:
            mo = False
            for lan in range(2):  # trang đôi khi tải chậm: tải lại tài khoản rồi thử thêm một lần
                if lan:
                    _cho_tai(page, TRANG_TAI_KHOAN)
                    time.sleep(3)
                mo = _mo_hop_thoai_tao(page)
                if mo:
                    break
            if not mo:
                return {**ket, "ket_qua": "hong", "ly_do": "không mở được hộp thoại tạo kênh — giao diện có thể đã đổi"}
            if not handle:
                return {**ket, "ket_qua": "hong", "ly_do": "chưa có handle dự kiến (handle trong trang trạng thái mở kênh)"}
            if not _dien_va_bam_tao(page, ten, handle):
                return {**ket, "ket_qua": "hong", "ly_do": "không gõ/bấm được (handle có thể đã có người dùng)"}
            time.sleep(8)
            _cho_tai(page, TRANG_TAI_KHOAN)
            if not ten_co_trong_trang(ten, _chu_trang(page)):
                return {**ket, "ket_qua": "hong", "ly_do": "đã bấm tạo nhưng chưa thấy kênh tên này trên tài khoản — kiểm tay"}
            uc = _uc_cua_ten(page, ten)
            if not uc:
                return {**ket, "ket_qua": "hong", "ly_do": "kênh đã hiện nhưng chưa lấy được mã UC — kiểm tay"}
            _cho_tai(page, "https://www.youtube.com/channel/" + uc)
            if not ten_co_trong_trang(ten, (page.title or "") + " " + _chu_trang(page)):
                return {**ket, "ket_qua": "hong", "ly_do": "trang kênh không khớp tên dự kiến — kiểm tay"}
            ket = {"ket_qua": "ok", "ly_do": "đã tạo kênh thương hiệu", "ten": ten, "uc": uc}
    except Exception as e:  # noqa: BLE001 — một lỗi không được làm gác tổng chết
        ket = {"ket_qua": "hong", "ly_do": "{0}: {1}".format(type(e).__name__, str(e)[:120]), "ten": ten, "uc": ""}
    finally:
        if page is not None:
            try:
                page.quit(timeout=5, force=True)  # buộc đóng: Chrome còn sót sẽ giữ cổng DevTools của lượt sau
            except Exception:  # noqa: BLE001
                pass

    if not thu:
        ghi_so(kenh, {**ket, "luc": _bay_gio().strftime("%Y-%m-%d %H:%M")}, goc)
    ghi("tạo kênh thương hiệu {0}: {1} — {2}".format(kenh, ket["ket_qua"], ket["ly_do"]))
    return ket


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Tạo kênh thương hiệu mới cho một kênh (làm như người thật).")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--thu", action="store_true", help="chỉ đọc: email + đã có kênh chưa, không tạo")
    ap.add_argument("--ngoai-khung", action="store_true",
                    help="bỏ khung giờ cấm — CHỈ cho kênh MỚI chưa có lịch đăng/quét (chủ xác nhận 19/10)")
    a = ap.parse_args(argv)
    ket = tao(a.kenh, thu=a.thu, bo_khung=a.ngoai_khung)
    print(json.dumps(ket, ensure_ascii=False))
    return {"ok": 0, "da_co": 0, "chi_doc": 0, "hoan": 10, "can_nguoi": 20}.get(ket["ket_qua"], 1)


if __name__ == "__main__":
    sys.exit(main())
