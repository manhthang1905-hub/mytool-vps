"""TẠO KÊNH THƯƠNG HIỆU MỚI trên youtube.com cho MỘT kênh (19/10/2026) — làm như người thật, MỘT lần cho mỗi kênh.

Dùng khi: mở kênh mới (lần đầu), mở rộng, hoặc kênh bị "không được phân phối" và cần kênh thương hiệu thay thế.

Luồng (trong Chrome Portable của chính kênh, hồ sơ `Data\\profile`, đã đăng nhập bằng `core/dang_nhap_gmail`):
  1. Chặn trước: trong khung cấm (02:00–07:00, 60 phút trước 05:00/20:00) → hoãn; Chrome kênh đang mở → hoãn;
     chưa có tên dự kiến (`workspace/mo-kenh/trang-thai.json: ten_goi_y`) → không làm.
  2. Xác minh TÀI KHOẢN: đọc email trên youtube.com/account; khác email trong kho → DỪNG (`sai_danh_tinh`).
  3. Tên: NFKC + bỏ/thay ký tự YouTube từ chối (19/10: «：» toàn khổ làm hỏng) → `ten` cuối ghi vào sổ.
  4. ĐỌC DANH SÁCH kênh của tài khoản (channel_switcher: tên + clientCacheKey + signinUrl). Đã có kênh trùng tên (so NFKC)
     hoặc UC trong sổ → DÙNG LẠI (`da_co`), KHÔNG tạo thêm. Không đọc được danh sách → không tạo.
     Sổ ghi đã bấm Tạo mà chưa thấy kênh → KHÔNG bấm lại (19/10 thử lại đã đẻ kênh TRÙNG), báo người.
  5. Tạo: hộp thoại Tạo kênh → gõ tên/handle → bấm (ghi dấu `da_bam_tao` TRƯỚC khi bấm) → đọc lại danh sách: kênh MỚI xuất hiện.
  6. Chọn kênh mới: mở `signinUrl` (pageid) của mục có clientCacheKey == UC đích; lần tải Studio KẾ TIẾP mới đổi
     → tải lại Studio đọc UC tới khi = UC đích.
  7. Ghim UC vào `vm/logs/kenh-uc.json` (như máy đăng ghim lần đầu). Chỉ ghi đè UC cũ khi UC cũ là kênh KHÁC của CÙNG tài khoản.
  8. Ghi `vm/logs/tao-kenh/<K>.json` (mã UC, tên cuối, thời điểm, đã chọn/ghim chưa).

An toàn: gặp đăng nhập lại / CAPTCHA / xác minh điện thoại → DỪNG, `can_nguoi`, không thử lại trong 6 giờ.
Không bao giờ xoá kênh. Mọi kết quả chỉ là mã + lý do ngắn; không in email/mật khẩu/cookie.

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
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

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


# 19/10: «：» toàn khổ làm hộp Tạo kênh từ chối. NFKC trước (toàn khổ → thường), rồi thay dấu phân cách hay bị từ chối
# bằng «・» (tên CJK) / khoảng trắng, bỏ ký tự cấm + ký tự điều khiển/ẩn. YouTube: tên kênh tối đa 50 ký tự.
KY_TU_THAY = ":;|/\\"
KY_TU_BO = '<>"@#{}[]'
DAI_TOI_DA_TEN = 50
MAU_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")


def lam_sach_ten(ten: Any) -> str:
    """Tên kênh YouTube nhận được: NFKC, thay/bỏ ký tự hay bị từ chối, gọn khoảng trắng, ≤ 50 ký tự ('' nếu rỗng)."""
    s = unicodedata.normalize("NFKC", str(ten or ""))
    nga = "・" if MAU_CJK.search(s) else " "
    ra = []
    for c in s:
        if c in KY_TU_THAY:
            ra.append(nga)
        elif c in KY_TU_BO or unicodedata.category(c) in ("Cc", "Cf", "Co", "Cs", "Cn"):
            continue
        else:
            ra.append(c)
    s = re.sub(r"\s+", " ", "".join(ra))
    s = re.sub(r"\s*・[\s・]*", "・", s)                               # «A ： B» → «A・B», không «・・»
    return s.strip(" ・-")[:DAI_TOI_DA_TEN].strip(" ・-")


def khoa_ten(ten: Any) -> str:
    """Khoá so tên kênh: đã làm sạch + NFKC + bỏ khoảng trắng + không phân biệt hoa thường."""
    return re.sub(r"\s+", "", lam_sach_ten(ten)).casefold()


def uc_cua_khoa(key: Any) -> str:
    """clientCacheKey của channel_switcher = UC bỏ tiền tố «UC»."""
    k = str(key or "").strip()
    return "" if not k else (k if k.startswith("UC") else "UC" + k)


def tim_kenh_dung_lai(ds: Iterable[dict], cac_ten: Iterable[str], uc_so: str = "") -> Optional[dict]:
    """Kênh ĐÃ CÓ trên tài khoản nên dùng lại: đúng UC trong sổ trước, rồi trùng tên (so `khoa_ten`). None nếu không có."""
    ds = [k for k in (ds or []) if k.get("uc")]
    if uc_so:
        for k in ds:
            if k["uc"] == uc_so:
                return k
    khoa = {khoa_ten(t) for t in cac_ten if khoa_ten(t)}
    for k in ds:
        if khoa_ten(k.get("ten")) in khoa:
            return k
    return None


def kenh_moi_xuat_hien(truoc: Iterable[str], sau: Iterable[dict], cac_ten: Iterable[str]) -> Optional[dict]:
    """Sau khi bấm Tạo: kênh có UC CHƯA có trong `truoc`; nhiều kênh mới → chọn cái trùng tên, không rõ thì None."""
    moi = [k for k in (sau or []) if k.get("uc") and k["uc"] not in set(truoc or ())]
    if len(moi) == 1:
        return moi[0]
    return tim_kenh_dung_lai(moi, cac_ten)


def duong_ghim_uc(goc: str = GOC) -> str:
    return os.path.join(goc, "vm", "logs", "kenh-uc.json")


def ghim_uc(kenh: str, uc: str, uc_tai_khoan: Iterable[str], goc: str = GOC) -> Tuple[bool, str, str]:
    """Ghim UC kênh vào `vm/logs/kenh-uc.json` như máy đăng (`MayDangDom.lay_uc` ghim lần đầu). (đã_ghim, lý do, UC cũ).
    Đang ghim UC KHÁC: chỉ ghi đè khi UC cũ là kênh khác của CÙNG tài khoản (vd kênh cá nhân trước khi chọn kênh thương hiệu);
    ngược lại KHÔNG đụng (chốt an toàn của máy đăng)."""
    duong = duong_ghim_uc(goc)
    try:
        with open(duong, encoding="utf-8") as f:
            ghim = json.load(f) or {}
        if not isinstance(ghim, dict):
            return False, "kenh-uc.json không đúng dạng — không ghi", ""
    except FileNotFoundError:
        ghim = {}
    except (OSError, ValueError) as e:
        return False, "không đọc được kenh-uc.json ({0}) — không ghi".format(type(e).__name__), ""
    cu = str(ghim.get(kenh) or "")
    if cu == uc:
        return True, "đã ghim sẵn", cu
    if cu and cu not in set(uc_tai_khoan or ()):
        return False, "kenh-uc.json đang ghim UC khác không thuộc tài khoản này — chủ kiểm", cu
    ghim[kenh] = uc
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(ghim, f, ensure_ascii=False, indent=1)
    os.replace(tam, duong)
    return True, ("ghim lần đầu" if not cu else "đổi ghim từ kênh cũ cùng tài khoản"), cu


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


JS_DS_KENH = r"""
  return JSON.stringify(Array.from(document.querySelectorAll('ytd-account-item-renderer')).map(function (a) {
    var d = a.data || {}, t = (d.serviceEndpoint || {}).selectActiveIdentityEndpoint, ts = (t && t.supportedTokens) || [];
    var key = '', url = '';
    ts.forEach(function (x) {
      if (x.offlineCacheKeyToken) key = x.offlineCacheKeyToken.clientCacheKey;
      if (x.accountSigninToken) url = x.accountSigninToken.signinUrl;
    });
    var n = d.accountName || {}, ten = n.simpleText || (n.runs || []).map(function (r) { return r.text; }).join('');
    if (!ten) ten = ((a.innerText || '').trim().split('\n')[0] || '');
    return {ten: ten.trim(), key: key || '', url: url || '', chon: !!d.isSelected};
  }));
"""


class TrinhDuyet:
    """Các thao tác Chrome (DrissionPage) mà luồng cần — tách ra để test bằng đồ giả."""

    def __init__(self, page):
        self.page = page

    def mo(self, url: str) -> None:
        _cho_tai(self.page, url)

    def url(self) -> str:
        return str(self.page.url or "")

    def chu(self) -> str:
        return _chu_trang(self.page)

    def ds_kenh(self) -> Optional[List[dict]]:
        """Mọi kênh của tài khoản trên channel_switcher: [{ten, uc, url(signinUrl), chon}]; None nếu không đọc được."""
        try:
            _cho_tai(self.page, TRANG_CHUYEN_KENH)
            han = time.time() + 20
            while time.time() < han:
                du = [k for k in json.loads(self.page.run_js(JS_DS_KENH) or "[]") if k.get("key")]
                if du:
                    return [{"ten": k.get("ten") or "", "uc": uc_cua_khoa(k.get("key")), "url": k.get("url") or "",
                             "chon": bool(k.get("chon"))} for k in du]
                time.sleep(1.5)
        except Exception:  # noqa: BLE001
            pass
        return None

    def tao_kenh(self, ten: str, handle: str) -> bool:
        mo = False
        for lan in range(2):  # trang đôi khi tải chậm: tải lại tài khoản rồi thử thêm một lần
            if lan:
                _cho_tai(self.page, TRANG_TAI_KHOAN)
                time.sleep(3)
            mo = _mo_hop_thoai_tao(self.page)
            if mo:
                break
        return bool(mo) and _dien_va_bam_tao(self.page, ten, handle)

    def uc_studio(self) -> str:
        """Tải Studio, đọc UC kênh đang chọn từ URL chuyển hướng ('' nếu không thấy)."""
        try:
            self.page.get("https://studio.youtube.com/")
            for _ in range(30):
                uc = tim_uc_trong_url(str(self.page.url or "").replace("studio.youtube.com", "youtube.com"))
                if uc:
                    return uc
                time.sleep(1)
        except Exception:  # noqa: BLE001
            pass
        return ""

    def ngu(self, giay: float) -> None:
        time.sleep(giay)


def chon_kenh(td, muc: dict, ngu=None, so_lan_tai: int = 3) -> Tuple[bool, str]:
    """Chọn kênh `muc` (mục channel_switcher) như YouTube: mở `signinUrl` (có pageid), rồi TẢI LẠI Studio tới khi UC = đích
    (chỉ lần tải Studio KẾ TIẾP mới đổi kênh). (đạt, UC Studio đọc được cuối)."""
    ngu = ngu or td.ngu
    dich = muc.get("uc") or ""
    uc = td.uc_studio()
    if uc == dich:
        return True, uc
    url = str(muc.get("url") or "")
    if not url.startswith("/signin?") or "pageid=" not in url:
        return False, uc
    td.mo("https://www.youtube.com" + url)
    ngu(5)
    for _ in range(so_lan_tai):
        uc = td.uc_studio()
        if uc == dich:
            return True, uc
        ngu(5)
    return False, uc


def chay_luong(td, kenh: str, ten_goc: str, handle: str, kho_email: str, so_cu: Dict[str, Any],
               thu: bool = False, goc: str = GOC, ghi: Callable[[str], None] = print, ngu=None,
               ghi_dau=None, cho_kenh_moi: float = 40.0) -> Dict[str, Any]:
    """Luồng trong Chrome đã mở (td = TrinhDuyet hoặc đồ giả). Trả kết quả để ghi sổ.
    `ghi_dau(du)`: ghi sổ dấu `da_bam_tao` NGAY trước khi bấm Tạo (đứt giữa chừng vẫn không bấm lại)."""
    ngu = ngu or td.ngu
    ten = lam_sach_ten(ten_goc)
    ket: Dict[str, Any] = {"ket_qua": "hong", "ly_do": "chưa chạy", "ten": ten, "uc": ""}
    if ten != ten_goc:
        ket["ten_goc"] = ten_goc
        ghi("tên dự kiến có ký tự YouTube hay từ chối → dùng «{0}»".format(ten))
    if not ten:
        return {**ket, "ly_do": "tên kênh sau khi làm sạch bị rỗng"}
    if so_cu.get("da_bam_tao"):
        ket["da_bam_tao"] = so_cu["da_bam_tao"]
    td.mo(TRANG_TAI_KHOAN)
    if dang_bi_chan_dang_nhap(td.url()):
        return {**ket, "ket_qua": "can_nguoi", "ly_do": "Chrome đòi đăng nhập lại"}
    that = tim_email_trong_chu(td.chu())
    if that and kho_email and that != kho_email:
        return {**ket, "ket_qua": "sai_danh_tinh", "ly_do": "tài khoản trong Chrome không phải tài khoản của kênh"}
    if not that:
        return {**ket, "ket_qua": "chua_xac_minh", "ly_do": "không đọc được email tài khoản — không tạo kênh"}

    # Danh sách kênh của tài khoản TRƯỚC mọi việc: thiếu danh sách thì không biết có trùng không → không tạo.
    ds = td.ds_kenh()
    if not ds:
        return {**ket, "ket_qua": "chua_xac_minh", "ly_do": "không đọc được danh sách kênh của tài khoản — không tạo (tránh trùng)"}
    cac_ten = [ten, ten_goc]
    uc_so = str(so_cu.get("uc") or "")
    muc = tim_kenh_dung_lai(ds, cac_ten, uc_so)
    dau = so_cu.get("da_bam_tao") or {}
    if not muc and dau:
        muc = kenh_moi_xuat_hien(dau.get("truoc") or [], ds, cac_ten + [dau.get("ten") or ""])
    if muc:
        ket.update(ket_qua="da_co", ly_do="kênh đã có trên tài khoản — dùng lại, không tạo thêm", uc=muc["uc"], ten=muc.get("ten") or ten)
    elif uc_so and so_cu.get("ket_qua") in ("ok", "da_co"):
        return {**ket, "ket_qua": "can_nguoi", "uc": uc_so,
                "ly_do": "sổ ghi đã có kênh thương hiệu nhưng không thấy trên tài khoản đang đăng nhập — kiểm tay, không tạo thêm"}
    elif dau:
        return {**ket, "ket_qua": "can_nguoi",
                "ly_do": "đã bấm Tạo lúc {0} mà chưa thấy kênh trên tài khoản — kiểm tay, KHÔNG tạo lại (tránh trùng)".format(dau.get("luc") or "?")}
    elif thu:
        return {**ket, "ket_qua": "chi_doc", "ly_do": "chưa có kênh tên này — chạy lại không --thu để tạo"}
    else:
        if not handle:
            return {**ket, "ly_do": "chưa có handle dự kiến (handle trong trang trạng thái mở kênh)"}
        dau = {"luc": _bay_gio().strftime("%Y-%m-%d %H:%M"), "ten": ten, "truoc": [k["uc"] for k in ds]}
        if ghi_dau:
            ghi_dau({**ket, "ket_qua": "dang_tao", "ly_do": "đang bấm Tạo", "da_bam_tao": dau})
        da_bam = td.tao_kenh(ten, handle)
        han, muc, sau = (cho_kenh_moi if da_bam else 8.0), None, None
        while True:
            ngu(8)
            han -= 8
            sau = td.ds_kenh()
            muc = kenh_moi_xuat_hien(dau["truoc"], sau or [], cac_ten)
            if muc or han <= 0:
                break
        if not da_bam and not muc and sau:
            # chắc chắn chưa có kênh mới (đã đọc lại danh sách) → gỡ dấu, lượt sau được thử lại
            if ghi_dau:
                ghi_dau({**ket, "ly_do": "không mở/gõ/bấm được hộp thoại tạo kênh (chưa bấm Tạo)"})
            return {**ket, "ly_do": "không mở/gõ/bấm được hộp thoại tạo kênh (handle có thể đã có người dùng)"}
        ket["da_bam_tao"] = dau
        if not muc:
            # KHÔNG bấm tạo lần nữa dù chưa thấy: lần trước "chưa thấy" nhưng kênh đã được tạo → trùng.
            return {**ket, "ket_qua": "chua_xac_minh", "ly_do": "đã bấm Tạo, chưa thấy kênh mới trên tài khoản — lượt sau đọc lại, không tạo lại"}
        ket.update(ket_qua="ok", ly_do="đã tạo kênh thương hiệu", uc=muc["uc"], ten=muc.get("ten") or ten)
    if thu:
        return {**ket, "ket_qua": "chi_doc", "ly_do": "đã có kênh (chỉ đọc: không chọn/ghim)"}

    # Chọn kênh trong Chrome kênh + ghim UC (máy đăng/quét dừng nếu Studio lệch UC ghim).
    ok, uc_doc = chon_kenh(td, muc, ngu)
    ket["chon_kenh"] = ok
    if not ok:
        return {**ket, "ket_qua": "chua_xac_minh",
                "ly_do": "{0}; chưa chuyển được Studio sang kênh này (Studio đang {1}) — lượt sau thử lại".format(
                    ket["ly_do"], "kênh khác" if uc_doc else "không đọc được")}
    da_ghim, ly_ghim, uc_cu = ghim_uc(kenh, muc["uc"], [k["uc"] for k in ds], goc)
    ket["ghim_uc"] = da_ghim
    if uc_cu and uc_cu != muc["uc"]:
        ket["uc_ghim_cu"] = uc_cu
    ghi("Studio đã chọn kênh mới; ghim UC: {0}".format(ly_ghim))
    if not da_ghim:
        return {**ket, "ket_qua": "chua_xac_minh", "ly_do": "{0}; {1}".format(ket["ly_do"], ly_ghim)}
    ket["ly_do"] += "; Studio đã chọn kênh này, UC đã ghim"
    return ket


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
    # 20/10: Chrome lấy từ KHO CHROME (`chrome_kho`, core/thay_kenh) do CHỦ đăng nhập tay — tài khoản trong Chrome CHÍNH
    # là tài khoản kênh, kho bí mật không có email: chỉ cần đọc được email trên trang tài khoản (không so).
    tu_kho = bool(str(d.get("chrome_kho") or "").strip())
    duoc, ma, ly = quyet_dinh_truoc_khi_chay(ten, kho_email or ("(chrome-kho)" if tu_kho else ""),
                                             "ok" if (thu or tu_kho or dn_ket in ("", "chua_thu")) else dn_ket,
                                             dn.chrome_dang_chay(mo_kenh.thu_muc_chrome(goc, kenh)),
                                             bo_khung=bo_khung)
    if not duoc:
        ket = {"ket_qua": ma, "ly_do": ly, "ten": ten}
        ghi("tạo kênh thương hiệu {0}: {1} — {2}".format(kenh, ma, ly))
        return ket

    so_cu = doc_so(kenh, goc)
    page = None
    ket: Dict[str, Any] = {"ket_qua": "hong", "ly_do": "chưa chạy", "ten": ten, "uc": ""}

    def ghi_dau(du):
        ghi_so(kenh, {**du, "luc": _bay_gio().strftime("%Y-%m-%d %H:%M")}, goc)

    try:
        page = _mo_chrome_kenh(goc, kenh)
        ket = chay_luong(TrinhDuyet(page), kenh, ten, handle, kho_email, so_cu, thu=thu, goc=goc, ghi=ghi,
                         ghi_dau=None if thu else ghi_dau)
    except Exception as e:  # noqa: BLE001 — một lỗi không được làm gác tổng chết
        ket = {"ket_qua": "hong", "ly_do": "{0}: {1}".format(type(e).__name__, str(e)[:120]), "ten": ten, "uc": ""}
        dau = doc_so(kenh, goc).get("da_bam_tao") or so_cu.get("da_bam_tao")   # dấu ghi trước khi bấm Tạo: GIỮ
        if dau:
            ket["da_bam_tao"] = dau
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
