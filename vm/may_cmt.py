# -*- coding: utf-8 -*-
"""
MAY TRA LOI BINH LUAN cua tool VM (MyTool VM) - ban CHINH CHU, sua thang o day.
Goc: cmt.py cua kho upload cu (kho github khac - tu nay khong dong bo nua).
Cau tra loi UU TIEN viet bang key cua MY TOOL qua tram (/van-ban), Gemini du phong.

CMT — Tu dong tra loi binh luan YouTube cho NHIEU KENH.

Cach dung:
    python cmt.py setup <ten_kenh>   Tao token cho 1 kenh (mo dung browser cua kenh)
    python cmt.py setup              Tao token cho TAT CA kenh (1 lenh xong het)
    python cmt.py test  <ten_kenh>   Scan + reply toi da 10 comment cho 1 kenh
    python cmt.py                     Production: chay tat ca kenh co token, lap moi 12h

Cau truc:
    upload/clients/<bat_ky>.json     Client OAuth (da Publish). Ten tuy y -> dung chung moi kenh.
                                     Hoac clients/<kenh>.json -> rieng tung kenh (uu tien).
    upload/tokens/<kenh>.json        Token YouTube moi kenh (tu refresh khi het han)
    upload/replied/<kenh>.txt        Trang thai comment da reply moi kenh
    upload/transcripts/<vid>.txt     Cache transcript dung chung
    upload/da-dang-cmt-moi/<kenh>.txt  Ma goi DONE da tu dang BINH LUAN MO DAU (idempotent)

Binh luan MO DAU (tu 1-binh-luan.txt cua goi DONE/<kenh>/<ma_goi>/): tool TU
DANG qua API ngay dau moi lan chay cho 1 kenh (xem dang_binh_luan_moi()).
YouTube Data API v3 KHONG co cach GHIM (pin) - ghim van la VIEC TAY, tool chi
ghi lai o CHANNEL/<kenh>/can-ghim.md kem link video de bam 1 cai.
"""
import os, sys, json, time, re, random, webbrowser, subprocess
from datetime import datetime, timezone

# Ep stdout/stderr ve UTF-8 — tranh UnicodeEncodeError khi in emoji/ky tu Unicode
# tren console cp1252 (vd khi 'start' mo cua so moi khong giu chcp 65001).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Console: TAT QuickEdit (click nham vao cmd KHONG con lam treo script) + xep goc tren PHAI
try:
    import ctypes as _ct
    _k = _ct.windll.kernel32
    _hin = _k.GetStdHandle(-10)            # STD_INPUT_HANDLE
    _m = _ct.c_uint()
    if _k.GetConsoleMode(_hin, _ct.byref(_m)):
        _k.SetConsoleMode(_hin, (_m.value & ~0x0040) | 0x0080)
    _hw = _k.GetConsoleWindow()
    if _hw:
        _ct.windll.user32.MoveWindow(_hw, 780, 0, 770, 430, True)
except Exception:
    pass

_THIEU_THU_VIEN = ""
try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.errors import HttpError
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
    from google_auth_oauthlib.flow import InstalledAppFlow
    import requests
except ImportError as _e:   # chay CAI-DAT-VPS.bat de cai; loi bao ro khi chay that
    build = Credentials = Request = HttpError = None
    YouTubeTranscriptApi = TranscriptsDisabled = NoTranscriptFound = None
    InstalledAppFlow = requests = None
    _THIEU_THU_VIEN = str(_e)

# ========== CAU HINH ==========
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _kho(ten):
    """Thu muc du lieu <ten>: uu tien ngay canh may nay; chua co ma thu muc
    CHA co san (VM cu, du lieu con nam trong thu muc upload) thi dung tiep."""
    o_day = os.path.join(BASE_DIR, ten)
    o_cha = os.path.join(os.path.dirname(BASE_DIR), ten)
    if not os.path.isdir(o_day) and os.path.isdir(o_cha):
        return o_cha
    return o_day


CLIENTS_DIR = _kho("clients")   # client_secret RIENG moi kenh: clients/<kenh>.json
TOKENS_DIR = _kho("tokens")     # token sau OAuth: tokens/<kenh>.json
REPLIED_DIR = _kho("replied")
TRANS_DIR = _kho("transcripts")
CLIENT_SECRET_FILE = (os.path.join(BASE_DIR, "client_secret.json")
                      if os.path.isfile(os.path.join(BASE_DIR, "client_secret.json"))
                      else os.path.join(os.path.dirname(BASE_DIR), "client_secret.json"))  # fallback dung chung (neu kenh chua co rieng)

DEBUG_PORT = 9222  # cong remote-debugging de DrissionPage attach vao browser kenh

DRY_RUN = False                  # True: chi in, khong dang
POSTS_PER_RUN = 20               # Toi da reply MOI / kenh / chu ky (cong bang giua cac kenh + an toan).
                                 # Khong bo cmt nao: chu ky sau lam tiep cmt con lai (seen luu lai).
                                 # Tran cung that su la QUOTA YouTube (~200 reply/ngay/project).
# Gian cach NGAU NHIEN giua 2 reply -> go nhu nguoi that, chong bi YouTube coi spam (QUAN TRONG NHAT)
REPLY_DELAY_MIN = 40             # giay (toi thieu giua 2 reply)
REPLY_DELAY_MAX = 180            # giay (toi da)
RUN_INTERVAL_HOURS = 12          # Production: chu ky chay lai (co them jitter ngau nhien)

# Pool API sinh reply (OpenAI-compatible, qua IPv6)
USE_POOL = False          # TAT pool -> chi dung Gemini de tra loi cmt (pool hay loi 401)
REPLY_API_BASE = "http://[2001:ee0:b004:3001::10]:8318/v1"
REPLY_API_KEY = "sk_cliproxy_local"
REPLY_MODEL = "claude-sonnet-4-6"
REPLY_TIMEOUT = 150       # giay - pool gateway hien chay cham (~60s/request)
REPLY_MAX_RETRIES = 3     # so lan thu lai khi goi API loi
REPLY_RETRY_WAIT = 5      # giay cho giua moi lan retry

# Du phong: Gemini (mien phi, chay qua IPv6) khi pool loi.
# KEY doc tu config.json -> KHONG hardcode/push GitHub (key lo se bi Google ban!).
# Lay key mien phi tai: https://aistudio.google.com/apikey  -> bo vao config.json: "GEMINI_API_KEY": "..."
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY = ""        # 1 key (tuong thich cu)
GEMINI_API_KEYS = []       # NHIEU key (moi browser/account 1 key) -> xoay vong chia quota
# luc setup moi kenh: tu tao 1 Gemini key (click CHUOT THAT) cho account do, gom lai.
# Moi account chi tao 1 lan -> sach (Google chi chan khi 1 account tao key nhieu lan lien tiep).
GEMINI_AUTOKEY = True
GEMINI_KEY_CHANNELS = []    # chrome (kenh) DA lay key -> bo qua, moi chrome chi lay 1 lan
try:
    with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as _cf:
        _cfg_cmt = json.load(_cf)
    GEMINI_API_KEY = _cfg_cmt.get("GEMINI_API_KEY", "")
    GEMINI_API_KEYS = list(_cfg_cmt.get("GEMINI_API_KEYS", []))
    GEMINI_KEY_CHANNELS = list(_cfg_cmt.get("GEMINI_KEY_CHANNELS", []))
    GEMINI_MODEL = _cfg_cmt.get("GEMINI_MODEL", GEMINI_MODEL)
    GEMINI_AUTOKEY = _cfg_cmt.get("GEMINI_AUTOKEY", True)
except Exception:
    pass


def _all_gemini_keys():
    """Tat ca Gemini key co (list + key le), bo trung."""
    keys = []
    for k in (GEMINI_API_KEYS + [GEMINI_API_KEY]):
        if k and k not in keys:
            keys.append(k)
    return keys

# Ngon ngu reply theo hau to kenh -T<n> (vd TL1-T1 / TH2-T1 -> Spanish)
LANG_MAP = {
    1: "Spanish", 2: "Vietnamese", 3: "English", 4: "French", 5: "German",
    6: "Portuguese", 7: "Japanese", 8: "Korean", 9: "Italian", 10: "Turkish",
}

# Che do chon ngon ngu reply:
#   "channel" - tra loi theo ngon ngu KENH (kenh.yaml `ngon_ngu`, lui ve hau to -T<n>); chua ro -> theo binh luan
#   "comment" - tra loi theo dung ngon ngu cua tung BINH LUAN
REPLY_LANG_MODE = "channel"

# ========== KHOI TAO ==========
for _d in (CLIENTS_DIR, TOKENS_DIR, REPLIED_DIR, TRANS_DIR):
    os.makedirs(_d, exist_ok=True)


# ========== TOKEN / OAUTH THEO KENH ==========
def token_path(channel):
    return os.path.join(TOKENS_DIR, f"{channel}.json")


def client_secret_path(channel):
    """Client_secret cho kenh. Tra None neu KHONG co client phu hop (KHONG fallback client_secret.json cu).
    1) clients/<kenh>.json            -> RIENG kenh nay (uu tien tuyet doi)
    2) clients/ chi co DUNG 1 file .json -> dung CHUNG cho moi kenh (ten gi cung duoc)
    3) Nhieu file -> dung file .json KHONG trung ten kenh nao (client chung)."""
    try:
        files = [n for n in sorted(os.listdir(CLIENTS_DIR)) if n.lower().endswith(".json")]
    except Exception:
        files = []

    # 1) Trung dung ten kenh
    exact = f"{channel}.json".lower()
    for n in files:
        if n.lower() == exact:
            return os.path.join(CLIENTS_DIR, n)
    # 2) Chi 1 file -> client dung chung
    if len(files) == 1:
        return os.path.join(CLIENTS_DIR, files[0])
    # 3) Nhieu file -> file khong trung ten kenh nao (client chung)
    channel_files = {f"{c}.json".lower() for c in discover_channels()}
    for n in files:
        if n.lower() not in channel_files:
            return os.path.join(CLIENTS_DIR, n)
    return None


def channel_browser_exe(channel):
    """Browser da dang nhap YouTube cua kenh: ...\\TL\\<kenh>\\<kenh>.exe"""
    parent = os.path.dirname(BASE_DIR)  # ...\TL  (cap tren upload)
    return os.path.join(parent, channel, f"{channel}.exe")


def save_credentials(channel, creds):
    with open(token_path(channel), "w", encoding="utf-8") as f:
        f.write(creds.to_json())


def load_credentials(channel):
    """Doc token cua kenh. Tu refresh neu het han. None neu chua co / khong refresh duoc."""
    tp = token_path(channel)
    if not os.path.exists(tp):
        return None
    try:
        creds = Credentials.from_authorized_user_file(tp, SCOPES)
    except Exception as e:
        print(f"⚠️ {channel}: token loi ({e}).")
        return None

    if creds and creds.valid:
        ghi_trang_thai_token(channel, "tot")
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(channel, creds)
            print(f"🔄 {channel}: da refresh token.")
            ghi_trang_thai_token(channel, "tot")
            return creds
        except Exception as e:
            print(f"⚠️ {channel}: refresh token that bai ({type(e).__name__}). Hay chay: setup_oauth.py --kenh {channel}")
            # 05/10: ghi HỎNG để agent quay về bình luận DOM (trước đây tệp token còn đó → agent vẫn chọn API → kênh mất bình luận)
            ghi_trang_thai_token(channel, "hong", type(e).__name__)
            return None
    ghi_trang_thai_token(channel, "hong", "token khong co refresh_token")
    return None


def ghi_trang_thai_token(channel, tt, ly_do=""):
    """vm/logs/oauth/<kenh>.json = {tt: tot|hong, ly_do (TÊN lỗi, không giá trị token), luc}. Hỏng ghi thì thôi."""
    try:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "oauth")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{channel}.json"), "w", encoding="utf-8") as f:
            json.dump({"tt": tt, "ly_do": str(ly_do)[:80], "luc": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
    except Exception:
        pass


def _open_channel_browser_debug(browser_exe, port=DEBUG_PORT):
    """Dong browser kenh neu dang chay, mo lai voi cong remote-debugging de DrissionPage attach."""
    import urllib.request
    exe_name = os.path.basename(browser_exe)
    subprocess.run(f'taskkill /F /IM "{exe_name}" /T', shell=True, capture_output=True)
    time.sleep(1.5)
    subprocess.Popen([browser_exe, f"--remote-debugging-port={port}", "about:blank"])
    # Cho cong debug san sang
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def _click_contains(page, words, timeout=0.6):
    """Click phan tu (button/link/role) co text chua 1 trong cac tu. True neu click duoc."""
    words = [w.lower() for w in words]
    for sel in ("tag:button", "css:[role=button]", "tag:a", "css:[role=link]"):
        try:
            els = page.eles(sel, timeout=timeout)
        except Exception:
            els = []
        for e in els:
            try:
                t = (e.text or "").strip().lower()
            except Exception:
                continue
            if t and any(w in t for w in words):
                try:
                    e.click()
                    return True
                except Exception:
                    try:
                        e.click(by_js=True)
                        return True
                    except Exception:
                        pass
    return False


def _safe_click(el):
    """Click 1 element, thu ca by_js. True neu click duoc."""
    try:
        el.click()
        return True
    except Exception:
        try:
            el.click(by_js=True)
            return True
        except Exception:
            return False


def _pick_account(tab):
    """Chon tai khoan tren man 'Choose an account':
    1) Uu tien tai khoan THUONG HIEU (co 'YouTube', khong @).
    2) Neu khong co (tai khoan chi 1 kenh) -> chon tai khoan Gmail thuong (co @),
       bo qua 'Use another account'.
    True neu da chon duoc."""
    try:
        lis = list(tab.eles("tag:li", timeout=0.5))
    except Exception:
        lis = []
    # Pass 1: brand account (YouTube, khong @)
    for li in lis:
        t = (getattr(li, "text", "") or "")
        if "youtube" in t.lower() and "@" not in t:
            if _safe_click(li):
                return True
    # Pass 2: tai khoan gmail thuong (co @), bo qua 'use another account'
    for li in lis:
        t = (getattr(li, "text", "") or "")
        tl = t.lower()
        if "@" in t and "another account" not in tl and "tài khoản khác" not in tl:
            if _safe_click(li):
                return True
    return False


def _select_channel_account(page, timeout=1.0):
    """Tren man 'Chon tai khoan', chon dong KENH (co chu 'YouTube', khong phai @gmail)."""
    try:
        lis = page.eles("tag:li", timeout=timeout)
    except Exception:
        lis = []
    for li in lis:
        try:
            t = li.text or ""
        except Exception:
            continue
        if "youtube" in t.lower() and "@" not in t:
            try:
                li.click()
                return True
            except Exception:
                try:
                    li.click(by_js=True)
                    return True
                except Exception:
                    pass
    return False


def _oauth_tab(browser):
    """Tab dang o accounts.google.com (man OAuth that). Bo qua tab localhost cu/tab khac."""
    try:
        tabs = browser.get_tabs()
    except Exception:
        return None
    for t in tabs:
        try:
            if "accounts.google.com" in (t.url or ""):
                return t
        except Exception:
            pass
    return None


def _redirected(browser, redirect_host):
    """True khi co tab da redirect ve localhost:<dung port> (token sap cap)."""
    try:
        for t in browser.get_tabs():
            if redirect_host in (t.url or ""):
                return True
    except Exception:
        pass
    return False


def _auto_consent(browser, redirect_host, timeout=180):
    """Tu dong click qua cac man OAuth: chon kenh -> canh bao (Nang cao/Di toi) -> Tiep tuc.
    Luon thao tac tren tab accounts.google.com; check redirect theo DUNG port (tranh tab cu)."""
    end = time.time() + timeout
    while time.time() < end:
        if _redirected(browser, redirect_host):
            return True

        tab = _oauth_tab(browser)
        if tab is None:
            time.sleep(1.5)
            continue
        url = (tab.url or "").lower()

        # === Man CONSENT / CANH BAO (consentsummary, /oauth/v2/, warning) ===
        # KHONG chon account o day (dong mo ta scope co chu 'YouTube' de bi bam nham).
        if ("consentsummary" in url or "/oauth/v2/" in url
                or "warning" in url or "oauth/consent" in url):
            if _click_contains(tab, ["Nâng cao", "Advanced"]):
                time.sleep(1.0)
            if _click_contains(tab, ["không an toàn", "unsafe", "Đi tới", "Go to"]):
                time.sleep(2.5)
                continue
            _click_contains(tab, ["Chọn tất cả", "Select all"])
            if _click_contains(tab, ["Tiếp tục", "Continue", "Cho phép", "Allow"]):
                time.sleep(2.5)
                continue
            time.sleep(1.2)
            continue

        # === Man CHON TAI KHOAN ===
        # Uu tien tai khoan thuong hieu (YouTube); neu tai khoan chi 1 kenh -> chon Gmail thuong.
        if _pick_account(tab):
            time.sleep(3)
            continue

        time.sleep(1.5)

    return _redirected(browser, redirect_host)


def _real_click(ele):
    """Click element bang CHUOT THAT (PyAutoGUI) tai toa do man hinh cua no.
    isTrusted=true nhu nguoi -> tranh bot detection cua Google (CDP click bi chan)."""
    try:
        import pyautogui
        x, y = ele.rect.screen_midpoint
        pyautogui.moveTo(int(x), int(y), duration=0.5)
        time.sleep(0.3)
        pyautogui.click()
        return True
    except Exception as e:
        print(f"   real_click loi: {e}")
        return False


def _save_gemini_to_config(key, channel=None):
    """Them key vao GEMINI_API_KEYS + danh dau kenh da lay (GEMINI_KEY_CHANNELS). Khong trung."""
    cfg_path = os.path.join(BASE_DIR, "config.json")
    try:
        cfg = {}
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        keys = list(cfg.get("GEMINI_API_KEYS", []))
        if key not in keys:
            keys.append(key)
        cfg["GEMINI_API_KEYS"] = keys
        if channel:
            chs = list(cfg.get("GEMINI_KEY_CHANNELS", []))
            if channel not in chs:
                chs.append(channel)
            cfg["GEMINI_KEY_CHANNELS"] = chs
        cfg.setdefault("GEMINI_MODEL", GEMINI_MODEL)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"   ⚠️ Luu key vao config.json loi: {e}")
        return False


def _create_gemini_key(browser, wait_sec=180):
    """Mo AI Studio cho NGUOI tu tao Gemini key (thu cong -> tranh Google chan bot
    va tranh account bi flag). Tool TU BAT key 'AQ...' khi no hien trong trang.
    Tra key hoac None neu het gio."""
    try:
        tab = browser.latest_tab
        tab.get("https://aistudio.google.com/apikey")
        time.sleep(5)
        try:
            tab.set.window.max()
            tab.set.activate()
        except Exception:
            pass
        print("   👉 HAY TU TAO 1 GEMINI KEY trong cua so vua mo (lam tay, NHANH):")
        print("      'Create API key' -> chon/tao project -> 'Create key'.")
        print(f"      Tool se TU NHAN key roi tu dong dong browser (cho toi da {wait_sec}s)...")
        end = time.time() + wait_sec
        while time.time() < end:
            try:
                keys = re.findall(r"AQ\.[A-Za-z0-9_\-]{30,}", tab.html)
                if keys:
                    return sorted(set(keys), key=len, reverse=True)[0]
            except Exception:
                pass
            time.sleep(3)
        print(f"   ⚠️ Het {wait_sec}s chua thay key -> bo qua kenh nay.")
        return None
    except Exception as e:
        print(f"   ⚠️ Loi cho Gemini key: {str(e)[:100]}")
        return None


def setup_channel(channel):
    """Tao token cho 1 kenh — DrissionPage dieu khien browser kenh, tu click qua OAuth."""
    import wsgiref.simple_server
    import wsgiref.util

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # cho phep redirect http://localhost

    client_file = client_secret_path(channel)
    if not client_file or not os.path.isfile(client_file):
        print(f"❌ {channel}: KHONG co file client trong clients/. "
              f"Bo 1 file .json (OAuth client da Publish) vao clients/ roi chay lai.")
        return

    browser_exe = channel_browser_exe(channel)
    if not os.path.isfile(browser_exe):
        print(f"❌ Khong tim thay browser kenh: {browser_exe}")
        return

    # Local server bat code OAuth tra ve
    class _App:
        last_uri = None

        def __call__(self, environ, start_response):
            _App.last_uri = wsgiref.util.request_uri(environ)
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
            return ["<h2>Xac thuc thanh cong! Ban co the dong tab nay.</h2>".encode("utf-8")]

    class _Quiet(wsgiref.simple_server.WSGIRequestHandler):
        def log_message(self, *a):
            pass

    server = wsgiref.simple_server.make_server("localhost", 0, _App(), handler_class=_Quiet)
    server.timeout = 5
    redirect_host = f"localhost:{server.server_port}"

    flow = InstalledAppFlow.from_client_secrets_file(client_file, SCOPES)
    flow.redirect_uri = f"http://{redirect_host}/"
    # hl=en: ep man OAuth luon hien thi TIENG ANH du may/account ngon ngu gi
    # -> dam bao do nhan nut ('Continue'/'Allow'/'Advanced') chay dung tren moi may.
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", hl="en")

    print(f"🌐 Mo browser kenh {channel} (debug port {DEBUG_PORT})...")
    if not _open_channel_browser_debug(browser_exe, DEBUG_PORT):
        print(f"⚠️ Browser khong mo cong debug {DEBUG_PORT}. Thu lai sau.")
        server.server_close()
        return

    from DrissionPage import Chromium
    browser = Chromium(f"127.0.0.1:{DEBUG_PORT}")
    # Don tab cu (tranh tab localhost/oauth con sot lam nham tab)
    try:
        _tabs = browser.get_tabs()
        tab = _tabs[0]
        for _extra in _tabs[1:]:
            try:
                _extra.close()
            except Exception:
                pass
    except Exception:
        tab = browser.latest_tab
    tab.get(auth_url)
    time.sleep(6)

    print("🤖 Tu dong chon kenh + click qua man dong y...")
    _auto_consent(browser, redirect_host)
    # Du _auto_consent tra ve som, code OAuth van co the ve qua local server ben duoi -> cho tiep.

    # Cho code tra ve local server (toi da ~180s)
    waited = 0
    while _App.last_uri is None and waited < 180:
        server.handle_request()
        waited += 5
    server.server_close()

    if _App.last_uri is None:
        print(f"❌ {channel}: khong nhan duoc code OAuth. Thu lai.")
        return

    flow.fetch_token(authorization_response=_App.last_uri)
    save_credentials(channel, flow.credentials)
    print(f"✅ Da luu token: {token_path(channel)}")

    # TU DONG dong browser cua kenh sau khi lay token (taskkill thang, tranh DrissionPage treo)
    time.sleep(1)
    try:
        subprocess.run(
            f'taskkill /F /IM "{os.path.basename(browser_exe)}" /T',
            shell=True, capture_output=True,
        )
        print(f"🔒 Da dong browser kenh {channel}.")
    except Exception:
        pass


def youtube_from_creds(creds):
    import certifi, httplib2
    from google_auth_httplib2 import AuthorizedHttp
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    base_http = httplib2.Http(timeout=60, ca_certs=certifi.where())
    authed_http = AuthorizedHttp(creds, http=base_http)
    return build("youtube", "v3", http=authed_http, cache_discovery=False)


# ========== TIEN ICH YOUTUBE ==========
def my_channel_id(yt):
    """Lay channel id cua tai khoan (khong hoi tuong tac — chay nen duoc)."""
    res = yt.channels().list(part="id,snippet", mine=True).execute()
    items = res.get("items", [])
    if not items:
        raise ValueError("Khong tim thay channel nao lien ket voi tai khoan nay.")
    ch = items[0]
    if len(items) > 1:
        print(f"⚠️ Tai khoan co {len(items)} kenh, dung kenh dau: {ch['snippet']['title']}")
    print(f"✅ Kenh: {ch['snippet']['title']} ({ch['id']})")
    return ch["id"]


def uploads_playlist_id(yt, channel_id):
    res = yt.channels().list(part="contentDetails", id=channel_id).execute()
    return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def list_all_video_ids(yt, uploads_pl_id):
    vids, page_token = [], None
    while True:
        r = yt.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_pl_id,
            maxResults=50,
            pageToken=page_token
        ).execute()
        vids += [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        page_token = r.get("nextPageToken")
        if not page_token:
            break
    return vids


def fetch_all_threads_for_videos(yt, video_ids):
    total_videos = len(video_ids)
    print(f"📼 Found {total_videos} videos → scanning all comments...")
    for idx, vid in enumerate(video_ids, start=1):
        print(f"🔍 [{idx}/{total_videos}] Scanning video {vid} ...")
        page_token = None
        while True:
            try:
                r = yt.commentThreads().list(
                    part="snippet,replies",
                    videoId=vid,
                    order="time",
                    textFormat="plainText",
                    maxResults=100,
                    pageToken=page_token
                ).execute()
            except HttpError as e:
                msg = str(e)
                if "commentsDisabled" in msg or "forbidden" in msg:
                    print(f"⚠️ Skip video {vid}: comments disabled/private")
                else:
                    print(f"⚠️ Skip video {vid}: {e}")
                break
            for it in r.get("items", []):
                yield it, vid
            page_token = r.get("nextPageToken")
            if not page_token:
                break
        time.sleep(0.3)


# ========== LUU TRANG THAI (theo kenh) ==========
# replied/<kenh>.txt la lop CHONG TRUNG THU HAI (backstop), khong phai lop
# chinh: lop chinh la already_replied_by_me() hoi THANG YouTube API moi lan
# quet. Ly do van can file nay: commentThreads().list(part="replies") CHI
# nhung kem san vai reply dau cua moi thread (khong phan trang rieng) -> voi
# thread DONG nguoi tra loi, reply cu cua chinh minh co the khong nam trong
# so vai cai duoc tra ve, already_replied_by_me() se KHONG thay -> phai dua
# vao "id nay minh da tung reply" da luu o day.
#
# REPLIED_MAX_IDS gioi han so id giu lai de file nay khong phinh vo han qua
# nhieu nam x nhieu kenh. CAT AN TOAN nghia la: id bi bo phai la id THUC SU
# CU, khong phai id vua reply gan day. Vi vay KHONG duoc sap xep lai theo
# chu cai (id binh luan la chuoi doc lap voi thoi gian) roi cat -> lam vay co
# the giu id cu, bo mat id vua reply hom qua, gay reply TRUNG. Thay vao do:
# giu dung THU TU THOI GIAN (cu -> moi), id MOI duoc noi vao CUOI, cat tu DAU
# (id cu nhat) khi vuot han — xem _so_ke_toan_kenh()/save_state() ben duoi.
REPLIED_MAX_IDS = 5000


def state_path(channel):
    return os.path.join(REPLIED_DIR, f"{channel}.txt")


def load_state(channel):
    p = state_path(channel)
    if not os.path.exists(p):
        return set()
    with open(p, "r", encoding="utf-8") as f:
        return set(x.strip() for x in f if x.strip())


def _thu_tu_da_luu(channel):
    """Id da luu tren dia, DUNG THEO THU TU DONG hien co (cu -> moi theo lich
    su ghi, KHONG sap xep lai) — chi dung de MOI (lan dau) trong mot tien
    trinh cho mot kenh."""
    p = state_path(channel)
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8") as f:
        return [x.strip() for x in f if x.strip()]


# Bo nho TRONG TIEN TRINH: (REPLIED_DIR, kenh) -> [thu_tu_dang_ghi, da_tung_biet].
# Vi sao KHONG doc lai file tren dia moi lan save_state() de suy ra "id nao
# moi": mot khi da CAT bot id cu khoi dia (vuot REPLIED_MAX_IDS), id do bien
# mat khoi noi dung file — nhung `seen` (tap hop nguoi goi giu, page 867-958)
# KHONG BAO GIO tu quen mot id da tung add(). Neu chi so sanh voi noi dung
# TREN DIA, o lan luu KE TIEP id vua bi cat se bi tuong nham la "id MOI" (vi
# no khong con tren dia nua) roi bi noi lai vao CUOI danh sach — tuc la nhay
# vao vi tri "moi nhat", day nguoc mot id THAT SU moi hon ra ngoai. Chay vai
# chuc lan trong cung mot phien (mot phien co the dang > REPLIED_MAX_IDS/2
# comment moi cung luc, du hiem) se dao lon thu tu that. Giai phap: nho rieng
# mot tap `da_tung_biet` CHI TANG, khong bao gio bi cat theo `thu_tu` — id da
# ghi nhan mot lan trong tien trinh nay thi khong bao gio bi coi la "moi" lan
# thu hai, ke ca sau khi da bi cat khoi file that.
#
# Khoa theo (REPLIED_DIR, kenh) chu khong chi kenh: moi tien trinh (vd
# `--mot-lan` cho tung phien — kien truc hien tai, xem KE-HOACH.md) tu nhien
# co bo nho rieng; cung giup test doc lap nhau khi REPLIED_DIR duoc tro sang
# thu muc tam khac nhau moi test.
_BO_NHO_REPLIED = {}


def _so_ke_toan_kenh(channel):
    khoa = (REPLIED_DIR, channel)
    if khoa not in _BO_NHO_REPLIED:
        thu_tu_dau = _thu_tu_da_luu(channel)
        _BO_NHO_REPLIED[khoa] = [list(thu_tu_dau), set(thu_tu_dau)]
    return _BO_NHO_REPLIED[khoa]


def save_state(channel, seen):
    """Ghi lai so da-reply, giu THU TU THOI GIAN (khong sort chu cai, xem
    ghi chu o `_BO_NHO_REPLIED` phia tren) va cat bot id CU NHAT neu vuot
    REPLIED_MAX_IDS."""
    so_ke_toan = _so_ke_toan_kenh(channel)
    thu_tu, da_tung_biet = so_ke_toan
    moi = [cid for cid in seen if cid not in da_tung_biet]  # id CHUA TUNG ghi nhan trong tien trinh nay
    if moi:
        thu_tu.extend(moi)          # noi vao CUOI = moi nhat
        da_tung_biet.update(moi)
    if len(thu_tu) > REPLIED_MAX_IDS:
        del thu_tu[: len(thu_tu) - REPLIED_MAX_IDS]  # cat id CU NHAT o DAU danh sach
    with open(state_path(channel), "w", encoding="utf-8") as f:
        f.write("\n".join(thu_tu))


def _la_cua_chinh_kenh(author_channel_id, my_ch):
    """Binh luan (top-level) nay co phai CUA CHINH KENH dang tra loi khong?
    Ham THUAN, tach rieng de test duoc khong can goi API - xem process_channel()."""
    return bool(author_channel_id) and author_channel_id == my_ch


def already_replied_by_me(thread, my_ch):
    replies = (thread.get("replies") or {}).get("comments") or []
    for r in replies:
        author = ((r.get("snippet") or {}).get("authorChannelId") or {}).get("value")
        if author == my_ch:
            return True
    return False


def top_comment_info(thread):
    """Tra (id, ten_hien_thi, noi_dung, id_kenh_cua_nguoi_binh_luan).
    id_kenh_cua_nguoi_binh_luan dung de loai binh luan CUA CHINH KENH (xem
    process_channel) - vd binh luan mo dau tool vua tu dang (dang_binh_luan_moi)."""
    t = (thread.get("snippet") or {}).get("topLevelComment") or {}
    s = t.get("snippet") or {}
    author_ch = ((s.get("authorChannelId") or {}).get("value") or "")
    return (t.get("id"), s.get("authorDisplayName"),
            (s.get("textDisplay") or s.get("textOriginal") or "").strip(), author_ch)


# ========== LAY NOI DUNG VIDEO ==========
def fetch_and_cache_transcript(video_id, yt=None):
    cache_path = os.path.join(TRANS_DIR, f"{video_id}.txt")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    try:
        # API moi (youtube-transcript-api 1.x): instance .list()/.fetch()
        api = YouTubeTranscriptApi()
        fetched = None
        try:
            tlist = api.list(video_id)
            for tr in tlist:                 # lay transcript dau tien co san (ngon ngu nao cung duoc)
                try:
                    fetched = tr.fetch()
                    break
                except Exception:
                    continue
        except Exception:
            fetched = api.fetch(video_id)    # fallback: fetch mac dinh
        if fetched:
            text = " ".join((getattr(s, "text", "") or (s.get("text", "") if isinstance(s, dict) else "")) for s in fetched)
            if text.strip():
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(text)
                return text
    except (TranscriptsDisabled, NoTranscriptFound):
        pass
    except Exception as e:
        print("⚠️ Transcript fetch error:", e)

    if yt:
        try:
            r = yt.videos().list(part="snippet", id=video_id).execute()
            items = r.get("items", [])
            if items:
                desc = items[0]["snippet"].get("description", "")
                if desc.strip():
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(desc)
                    return desc
        except Exception as e:
            print("⚠️ Description fallback error:", e)

    with open(cache_path, "w", encoding="utf-8") as f:
        f.write("")
    return ""


def pick_relevant_snippet(transcript_text, comment_text, max_chars=900):
    if not transcript_text:
        return ""
    stop = set(["the","and","for","that","this","with","are","was","but","not","you","your","have","has","had","they","their","from","what","when","where","which","who","how","a","an","in","on","is","it","of","to"])
    tokens = re.findall(r"[A-Za-z0-9']{3,}", comment_text.lower())
    keywords = [t for t in tokens if t not in stop]
    sents = re.split(r'(?<=[.!?])\s+', transcript_text)
    if keywords:
        hits = [s.strip() for s in sents if any(k in s.lower() for k in keywords)]
        if hits:
            snippet = " ".join(hits)
            return snippet[:max_chars].strip()
    return transcript_text[:max_chars].strip()


# ========== SINH PHAN HOI ==========
def _tram_tool():
    """Dia chi TRAM cua tool o may nha — agent (vm/agent.py) chep xuong
    vm/cai-dat-tool.json moi nhip tim. Khong co file/khong co tram -> ""."""
    for duong in (os.path.join(BASE_DIR, "cai-dat-tool.json"),
                  os.path.join(BASE_DIR, "vm", "cai-dat-tool.json")):
        try:
            with open(duong, encoding="utf-8") as f:
                ra = str((json.load(f) or {}).get("tram") or "")
            if ra:
                return ra
        except Exception:
            continue
    return ""


def _reply_via_tool(prompt_text):
    """UU TIEN 1: nho TOOL o may nha viet — dung key cua tool, tru vi tool
    (chu du an 02/09: "cho no dung luon api key cua tool de tra loi").
    Key khong bao gio nam tren VM: minh gui de bai, tool viet ho.
    Loi gi cung raise -> roi xuong Gemini du phong."""
    tram = _tram_tool()
    if not tram:
        raise RuntimeError("chua co dia chi tram (agent chua chay?)")
    r = requests.post(tram.rstrip("/") + "/van-ban",
                      json={"de_bai": prompt_text}, timeout=REPLY_TIMEOUT)
    r.raise_for_status()
    reply = (r.json().get("chu") or "").strip()
    if not reply:
        raise RuntimeError("tram tra rong")
    return reply


def _reply_via_pool(prompt_text):
    """Goi Pool API (OpenAI-compatible). Tra text hoac raise."""
    r = requests.post(
        REPLY_API_BASE + "/chat/completions",
        headers={
            "Authorization": "Bearer " + REPLY_API_KEY,
            "Content-Type": "application/json",
            "Accept-Encoding": "identity",  # tranh loi gzip header sai tu gateway
        },
        json={
            "model": REPLY_MODEL,
            "messages": [{"role": "user", "content": prompt_text}],
            "max_tokens": 800,
        },
        timeout=REPLY_TIMEOUT,
    )
    r.raise_for_status()
    return (r.json()["choices"][0]["message"]["content"] or "").strip()


def _reply_via_gemini(prompt_text, key):
    """Du phong: Gemini REST (mien phi, qua IPv6) voi 1 key cu the. Tra text hoac raise."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={key}")
    r = requests.post(
        url,
        json={
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"maxOutputTokens": 800},
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return (data["candidates"][0]["content"]["parts"][0]["text"] or "").strip()


def gen_reply_with_prompt(prompt_text):
    """Sinh reply: TOOL truoc (key cua tool, qua tram cua may nha) -> pool
    (neu bat) -> XOAY VONG cac GEMINI key. Chu du an 02/09: "dung luon api
    key cua tool; luong cu dung key gemini thi de lam du phong".
    Het tat ca -> None (bo qua comment, khong spam)."""
    providers = [("tool", _reply_via_tool)]
    if USE_POOL:
        providers.append(("pool", _reply_via_pool))
    for i, gk in enumerate(_all_gemini_keys(), 1):
        providers.append((f"gemini#{i}", lambda p, k=gk: _reply_via_gemini(p, k)))

    for name, fn in providers:
        for attempt in range(1, REPLY_MAX_RETRIES + 1):
            err = None
            try:
                reply = (fn(prompt_text) or "").strip()
                if reply:
                    return reply   # tra NGUYEN VAN, khong cat 2 cau nua
                err = "reply rong"
            except Exception as e:
                err = str(e)[:140]
                # Loi auth/quota (401/403/429) -> retry vo ich, chuyen key/provider khac luon
                if "401" in err or "403" in err or "429" in err:
                    print(f"   ⚠️ {name} loi ({err[:40]}) -> chuyen key/provider khac.")
                    break
                # Tram tat / chua co dia chi -> retry vo ich, xuong Gemini luon
                if name == "tool" and ("chua co dia chi" in err
                                       or "Connection" in err or "connect" in err):
                    print(f"   ⚠️ tool loi ({err[:60]}) -> dung Gemini du phong.")
                    break
            print(f"   ⚠️ {name} loi (lan {attempt}/{REPLY_MAX_RETRIES}): {err}")
            if attempt < REPLY_MAX_RETRIES:
                time.sleep(REPLY_RETRY_WAIT)

    print("   ❌ Tat ca provider/key that bai -> BO QUA comment.")
    return None


def post_reply(yt, parent_id, text):
    body = {"snippet": {"parentId": parent_id, "textOriginal": text.strip()}}
    return yt.comments().insert(part="snippet", body=body).execute()


# ========== BINH LUAN MO DAU (dang tu dong ngay sau khi video len song) ==========
# QUAN TRONG - da doc lai tai lieu chinh thuc YouTube Data API v3 (tai nguyen
# Comments / CommentThreads): KHONG CO cach nao GHIM (pin) mot binh luan qua
# API. Khong co truong "isPinned"/"pinned" o bat ky dau (doc lan viet), khong
# co phuong thuc pin/unpin nao. Ghim CHI lam duoc BANG TAY tren giao dien that
# (may tinh: chuot phai vao binh luan -> Ghim; dien thoai: giu vao binh luan ->
# Ghim). Vi vay o day CHI tu DANG binh luan mo dau bang API
# (commentThreads().insert) - con GHIM la MOT VIEC TAY, ghi lai o
# CHANNEL/<kenh>/can-ghim.md kem link thang toi video de bam 1 cai la xong
# (xem _ghi_can_ghim() ben duoi). DUNG co gang "hack" ghim bang cach nao khac
# (vd DrissionPage dieu khien Chrome) - ngoai pham vi va rui ro dong tai khoan.

SEEDED_DIR = _kho("da-dang-cmt-moi")   # da-dang-cmt-moi/<kenh>.txt: ma goi DA dang binh luan mo dau (idempotent)
os.makedirs(SEEDED_DIR, exist_ok=True)

SEED_POSTS_PER_RUN = 5     # toi da bao nhieu binh luan mo dau dang MOI luot goi (an toan quota/spam)
SEED_DELAY_MIN = 5         # giay - gian cach giua 2 lan dang. Ngan hon REPLY_DELAY vi day la
SEED_DELAY_MAX = 20        # dang MOI (khong phai tra loi hang loat) nen it rui ro bi coi la spam hon.


def _seeded_state_path(channel):
    return os.path.join(SEEDED_DIR, f"{channel}.txt")


def _seeded_set(channel):
    p = _seeded_state_path(channel)
    if not os.path.exists(p):
        return set()
    with open(p, "r", encoding="utf-8") as f:
        return set(x.strip() for x in f if x.strip())


def _danh_dau_seeded(channel, ma_goi):
    if ma_goi in _seeded_set(channel):
        return
    with open(_seeded_state_path(channel), "a", encoding="utf-8") as f:
        f.write(ma_goi + "\n")


def _doc_tieu_de_goi(thu_muc_goi):
    """Doc dong 'TITLE: ...' trong 1-tieu-de.txt cua goi DONE. "" neu khong co
    (dung dinh dang voi core/ban_giao_dang.py::doc_gioi_thieu)."""
    duong = os.path.join(thu_muc_goi, "1-tieu-de.txt")
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as f:
            for dong in f:
                if dong.startswith("TITLE:"):
                    return dong[len("TITLE:"):].strip()
    except OSError:
        pass
    return ""


def _don_goi_binh_luan_moi(channel):
    """Cac goi DONE/<channel>/<ma_goi>/ co san 1-binh-luan.txt, theo THU TU TEN
    thu muc (== thu tu ma luot, cu truoc moi sau). Rong neu khong co thu muc
    DONE canh vm/ (nep vm dat rieng canh Chrome, khong co CHANNEL/DONE) - im
    lang bo qua, day la tinh nang THEM chu khong phai dieu kien bat buoc."""
    goc_done = os.path.join(os.path.dirname(BASE_DIR), "DONE", channel)
    try:
        ten_goi = sorted(os.listdir(goc_done))
    except OSError:
        return []
    ra = []
    for ten in ten_goi:
        thu_muc = os.path.join(goc_done, ten)
        duong_bl = os.path.join(thu_muc, "1-binh-luan.txt")
        if os.path.isdir(thu_muc) and os.path.isfile(duong_bl):
            ra.append({"ma_goi": ten, "thu_muc": thu_muc, "duong_bl": duong_bl})
    return ra


def _khop_tieu_de(a, b):
    """Hai tieu de co phai CUNG MOT video (cho phep sai khac nho do dau cau/
    khoang trang khi qua may API khac nhau)? Ham THUAN, khong goi mang."""
    import difflib
    a, b = (a or "").strip(), (b or "").strip()
    if not a or not b:
        return False
    if a == b:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.90


def tim_video_id_theo_tieu_de(yt, uploads_pl_id, tieu_de, so_video_gan_day=20):
    """Tim video KHOP tieu de trong so_video_gan_day video GAN DAY NHAT cua
    kenh (video vua dang luon nam dau danh sach uploads cua chinh chu kenh -
    playlist nay thay CA video rieng tu/hen gio vi ta dang xac thuc bang
    chinh OAuth cua kenh). Khop NHIEU video (hiem) -> lay video MOI NHAT theo
    publishedAt. Khong khop video nao -> None (video co the con dang xu ly/
    chua kip khop tieu de - THU LAI o luot sau, xem dang_binh_luan_moi())."""
    try:
        r = yt.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads_pl_id,
            maxResults=so_video_gan_day).execute()
    except HttpError as e:
        print(f"   ⚠️ Khong doc duoc danh sach video gan day: {e}")
        return None
    khop = []
    for it in r.get("items", []):
        sn = it.get("snippet") or {}
        if _khop_tieu_de(sn.get("title") or "", tieu_de):
            khop.append((sn.get("publishedAt") or "",
                        (it.get("contentDetails") or {}).get("videoId")))
    if not khop:
        return None
    khop.sort(key=lambda x: x[0], reverse=True)   # video MOI NHAT khop dung truoc
    return khop[0][1]


def post_seed_comment(yt, video_id, text):
    """Dang MOT binh luan MOI (top-level, khong phai reply) len video qua API.
    KHONG the ghim bang API - xem ghi chu dau muc BINH LUAN MO DAU o tren."""
    body = {"snippet": {"videoId": video_id,
                        "topLevelComment": {"snippet": {"textOriginal": text.strip()}}}}
    return yt.commentThreads().insert(part="snippet", body=body).execute()


def _ghi_can_ghim(channel, tieu_de, video_id, van_ban):
    """Ghi MOT dong vao CHANNEL/<kenh>/can-ghim.md - so viec TAY con lai
    (Ghim). Khong co thu muc CHANNEL (nep vm dat rieng, khong canh CHANNEL/)
    thi IM LANG bo qua - viec CHINH (dang binh luan) da xong, thieu mai so nay
    khong duoc lam tuong nhu ca luot that bai."""
    try:
        thu_muc = os.path.join(os.path.dirname(BASE_DIR), "CHANNEL", channel)
        if not os.path.isdir(thu_muc):
            return
        duong = os.path.join(thu_muc, "can-ghim.md")
        link = f"https://www.youtube.com/watch?v={video_id}"
        moi = (not os.path.isfile(duong)) or os.path.getsize(duong) == 0
        with open(duong, "a", encoding="utf-8") as f:
            if moi:
                f.write(
                    "# Việc tay còn lại: GHIM bình luận mở đầu\n\n"
                    "YouTube không cho ghim bình luận qua API — tool chỉ tự "
                    "ĐĂNG được, còn GHIM phải bấm tay (1 cái là xong). Mỗi "
                    "dòng dưới đây là một video vừa được tự đăng bình luận "
                    "mở đầu: mở link, bấm vào ĐÚNG bình luận có đoạn chữ in "
                    "dưới, chọn **Ghim**.\n\n")
            dong_dau = (van_ban.splitlines() or [""])[0][:120]
            f.write(f"- [{time.strftime('%Y-%m-%d %H:%M')}] **{tieu_de or video_id}**"
                    f" — {link}\n  > {dong_dau}\n")
    except OSError:
        pass


def dang_binh_luan_moi(channel, gioi_han=None):
    """Dang BINH LUAN MO DAU (tu 1-binh-luan.txt cua goi DONE) cho cac video
    VUA len song cua kenh - goi o DAU process_channel(), TRUOC khi quet tra
    loi vien (video vua dang la moi nhat, dang truoc thi bot tra loi vien
    khong bi lan voi thread nay - da co lop chan rieng o tren du sao, xem
    top_comment_info()/process_channel()).

    Idempotent: moi goi DONE (ma_goi) chi dang MOT LAN, nho o SEEDED_DIR.
    Video con hen gio/rieng tu/chua kip len playlist thi BO QUA lan nay
    (KHONG danh dau da-seed) - phien sau (ngay mai) tu thu lai, cho toi khi
    khop duoc video HOAC goi DONE bi don don (xem GHI-CHU trong bang va).

    Tra {"da_dang", "cho_video", "loi"} - so de process_channel() in 1 dong
    tom tat, khong lam gi voi loi (loi da tu in ben trong)."""
    ket = {"da_dang": 0, "cho_video": 0, "loi": 0}
    gioi_han = SEED_POSTS_PER_RUN if gioi_han is None else gioi_han
    goi_can_lam = [g for g in _don_goi_binh_luan_moi(channel)
                  if g["ma_goi"] not in _seeded_set(channel)]
    if not goi_can_lam:
        return ket

    creds = load_credentials(channel)
    if not creds:
        return ket   # chua co token - process_channel() da bao dong nay roi

    yt = youtube_from_creds(creds)
    try:
        my_ch = my_channel_id(yt)
        upl = uploads_playlist_id(yt, my_ch)
    except Exception as e:
        print(f"   ⚠️ dang_binh_luan_moi({channel}): khong doc duoc kenh ({e})")
        return ket

    for goi in goi_can_lam:
        if ket["da_dang"] >= gioi_han:
            break
        tieu_de = _doc_tieu_de_goi(goi["thu_muc"])
        if not tieu_de:
            continue   # khong ro tieu de -> khong khop duoc video nao, cho luot sau
        video_id = tim_video_id_theo_tieu_de(yt, upl, tieu_de)
        if not video_id:
            ket["cho_video"] += 1
            continue   # video chua len song/chua khop - THU LAI luot sau, KHONG seed
        try:
            with open(goi["duong_bl"], "r", encoding="utf-8", errors="replace") as f:
                van_ban = f.read().strip()
        except OSError:
            van_ban = ""
        if not van_ban:
            _danh_dau_seeded(channel, goi["ma_goi"])   # khong co gi de dang - dung thu lai
            continue
        try:
            post_seed_comment(yt, video_id, van_ban)
            _danh_dau_seeded(channel, goi["ma_goi"])
            _ghi_can_ghim(channel, tieu_de, video_id, van_ban)
            ket["da_dang"] += 1
            print(f"   💬 {channel}: da dang binh luan mo dau cho '{tieu_de[:50]}' "
                  f"({video_id}) - CON VIEC TAY: ghim no "
                  f"(xem CHANNEL/{channel}/can-ghim.md)")
            time.sleep(random.uniform(SEED_DELAY_MIN, SEED_DELAY_MAX))
        except HttpError as e:
            msg = str(e)
            ket["loi"] += 1
            if "commentsDisabled" in msg:
                # Video tat binh luan - dang lai bao nhieu lan cung vay hong,
                # danh dau seeded de dung thu vo ich.
                _danh_dau_seeded(channel, goi["ma_goi"])
                print(f"   ⚠️ {channel}: video '{tieu_de[:40]}' tat binh luan - bo qua han.")
            elif "quota" in msg.lower():
                print(f"   ⛔ {channel}: het quota API khi dang binh luan mo dau "
                      f"- dung, luot sau lam tiep.")
                break
            else:
                print(f"   ⚠️ {channel}: loi dang binh luan mo dau ({msg[:120]}) "
                      f"- thu lai luot sau.")
    return ket


# ========== XU LY 1 KENH ==========
#: Ma ngon ngu kenh.yaml `ngon_ngu` -> ten tieng Anh cho loi nhac (cung bang voi may_cmt_dom.NGON_NGU).
TEN_NGON_NGU = {"ja": "Japanese", "vi": "Vietnamese", "en": "English", "es": "Spanish",
                "fr": "French", "de": "German", "pt": "Portuguese", "ko": "Korean",
                "it": "Italian", "tr": "Turkish", "th": "Thai", "id": "Indonesian",
                "zh": "Chinese", "ru": "Russian", "hi": "Hindi", "ar": "Arabic"}


def _ngon_ngu_kenh_yaml(channel, goc_tool=None):
    """`ngon_ngu` trong CHANNEL/<kenh>/kenh.yaml (cung cach doc voi may_cmt_dom.doc_cai_dat). "" neu thieu."""
    goc_tool = goc_tool or os.path.dirname(BASE_DIR)
    try:
        with open(os.path.join(goc_tool, "CHANNEL", str(channel or "").strip(), "kenh.yaml"),
                  "r", encoding="utf-8") as tep:
            for dong in tep:
                m = re.match(r'^ngon_ngu:\s*"?([A-Za-z-]+)"?', dong)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return ""


def channel_language(channel, goc_tool=None):
    """Ngon ngu khan gia cua kenh. None neu khong ro.

    01/10/2026: lay tu kenh.yaml `ngon_ngu` TRUOC (VPS kenh/ngach/quoc gia khac dat ma kenh tuy y,
    vd "K1" - hau to -T<n> khong con mang nghia). Kenh khong co kenh.yaml canh tool (nep vm dat
    rieng) thi lui ve nep cu: hau to -T<n> (vd TL1-T1 -> Spanish)."""
    ma = _ngon_ngu_kenh_yaml(channel, goc_tool).lower().split("-")[0]
    if ma:
        return TEN_NGON_NGU.get(ma, ma)
    m = re.search(r"-T(\d+)\s*$", channel.strip(), re.IGNORECASE)
    if m:
        return LANG_MAP.get(int(m.group(1)))
    return None


def process_channel(channel, max_posts=POSTS_PER_RUN):
    print(f"\n────────── KENH: {channel} ──────────")
    creds = load_credentials(channel)
    if not creds:
        print(f"⏭️ {channel}: chua co token. Chay: python cmt.py setup {channel}")
        return

    # Dang binh luan MO DAU cho video vua len song TRUOC (tu 1-binh-luan.txt
    # cua goi DONE) - xem dang_binh_luan_moi(). Loi o day KHONG duoc chan
    # viec tra loi vien ben duoi (hai viec doc lap nhau).
    try:
        seed_ket = dang_binh_luan_moi(channel)
        if seed_ket["da_dang"] or seed_ket["cho_video"]:
            print(f"💬 {channel}: binh luan mo dau - da dang {seed_ket['da_dang']}, "
                  f"cho video len song/chua khop {seed_ket['cho_video']}")
    except Exception as e:
        print(f"⚠️ {channel}: loi dang binh luan mo dau ({e}) - bo qua, tiep tuc tra loi vien.")

    lang = channel_language(channel)
    print(f"🌐 Ngon ngu reply: {lang or '(theo ngon ngu binh luan)'}")

    yt = youtube_from_creds(creds)
    my_ch = my_channel_id(yt)

    seen = load_state(channel)
    posted = 0

    upl = uploads_playlist_id(yt, my_ch)
    video_ids = list_all_video_ids(yt, upl)
    print(f"📼 Found {len(video_ids)} videos. Scanning comments...")

    scanned = 0
    for th, vid in fetch_all_threads_for_videos(yt, video_ids):
        scanned += 1
        if not (th.get("snippet") or {}).get("canReply", True):
            continue
        cid, author, text, author_ch = top_comment_info(th)
        if already_replied_by_me(th, my_ch):
            if cid:
                seen.add(cid)
            continue
        if _la_cua_chinh_kenh(author_ch, my_ch):
            # Binh luan nay LA CUA CHINH KENH (vd binh luan mo dau tool vua tu
            # dang - xem dang_binh_luan_moi(), hoac chu kenh tu binh luan tay).
            # KHONG duoc tu tra loi CHINH MINH.
            if cid:
                seen.add(cid)
            continue

        if not cid or not text or cid in seen:
            continue

        # Lay transcript / description
        context_text = fetch_and_cache_transcript(vid, yt)
        snippet = pick_relevant_snippet(context_text, text, max_chars=900)

        if REPLY_LANG_MODE == "channel" and lang:
            lang_line = (
                f"IMPORTANT: Always reply in {lang} (this channel's audience language), "
                f"no matter what language the comment is written in.\n"
            )
            tail_line = f"Write ONLY the reply text, in {lang}."
        else:
            lang_line = (
                "IMPORTANT: Reply in the SAME language as the viewer's comment "
                "(detect it and match it exactly).\n"
            )
            tail_line = "Write ONLY the reply text, in the viewer's language."

        prompt = (
            "You are the channel owner replying to a comment on your own YouTube video.\n"
            + lang_line +
            "Sound like a REAL human typing casually — natural, warm, simple and down-to-earth, "
            "the way a normal person actually replies. Often 1 short sentence is enough (max 2). "
            "STRICTLY no emojis, no icons, no hashtags. "
            "Avoid any corporate or marketing tone, avoid stiff/over-formal phrasing and cliches. "
            "If the comment is hostile, stay calm and kind.\n"
        )
        if snippet:
            prompt += f"\nVideo context (for relevance only):\n{snippet}\n"
        prompt += f"\nViewer comment: {text}\n\n{tail_line}"

        reply = gen_reply_with_prompt(prompt)
        if not reply:
            # API loi -> KHONG post (tranh spam/sai ngon ngu). Khong them seen -> lan sau thu lai.
            print(f"   ⏭️ Bo qua comment (API loi, khong post): {text[:60]}")
            continue

        print(f"\n[{scanned}] 👤 {author}\n💬 {text}\n📝 {reply}")
        try:
            if not DRY_RUN:
                post_reply(yt, cid, reply)
                posted += 1
                # Ghi so reply HOM NAY cho kenh (de GUI hien tong quan)
                try:
                    import sys as _sys
                    _d = os.path.dirname(os.path.abspath(__file__))
                    if _d not in _sys.path:
                        _sys.path.insert(0, _d)
                    import stats
                    stats.bump(channel, "reply")
                except Exception:
                    pass
                # Gian NGAU NHIEN nhu nguoi that go -> tranh bi YouTube coi spam
                wait = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
                print(f"   ⏳ Cho {int(wait)}s roi reply tiep (gian chong spam)...")
                time.sleep(wait)
        except Exception as e:
            print("⚠️ Error posting:", e)
            # Het quota project -> dung kenh nay, chu ky sau lam tiep (KHONG danh dau seen -> khong mat cmt)
            if "quota" in str(e).lower():
                print(f"   ⛔ Het quota API -> dung kenh {channel}, chu ky sau lam tiep cmt con lai.")
                break
        # Danh dau + LUU NGAY sau moi comment -> bi ngat giua chung cung khong reply trung
        seen.add(cid)
        save_state(channel, seen)

        if posted >= max_posts:
            print(f"\n⏹️ Dat gioi han {max_posts} comment cho kenh {channel}. Tam dung.")
            break

    save_state(channel, seen)
    print(f"✅ {channel}: Scanned {scanned} | Posted {posted}")


def discover_channels():
    """Quet thu muc cung cap voi upload/ — moi kenh = folder co <ten>/<ten>.exe (giong dang.py)."""
    parent = os.path.dirname(BASE_DIR)  # ...\TL
    found = []
    try:
        for name in sorted(os.listdir(parent)):
            d = os.path.join(parent, name)
            if not os.path.isdir(d) or name.lower() == "upload":
                continue
            if os.path.isfile(os.path.join(d, f"{name}.exe")):
                found.append(name)
    except Exception as e:
        print(f"⚠️ Loi quet kenh: {e}")
    return found


def _tu_tra_loi_bat(channel):
    """Kenh nay co duoc TU TRA LOI BINH LUAN khong - doc thiet lap agent
    chep xuong (vm/cai-dat-tool.json, tool day xuong moi nhip tim).

    May NHIEU kenh (toi da 5, 1 VPS - vm/KE-HOACH.md): chi MOT tien trinh
    may_cmt.py cho ca may, run_all() lap qua tung kenh co token - kenh nao
    dang TAT thi BO QUA o day. Khong thay du lieu gi -> mac dinh BAT, dung
    nep vm_cai_dat.MAC_DINH (tu_tra_loi_cmt = True)."""
    duong = os.path.join(BASE_DIR, "cai-dat-tool.json")
    try:
        with open(duong, "r", encoding="utf-8") as f:
            du = json.load(f) or {}
    except Exception:
        return True
    theo_kenh = (du.get("kenh") or {}).get(channel)
    if isinstance(theo_kenh, dict) and "tu_tra_loi_cmt" in theo_kenh:
        return bool(theo_kenh["tu_tra_loi_cmt"])
    if "tu_tra_loi_cmt" in du:
        return bool(du["tu_tra_loi_cmt"])
    return True


def _doc_co_dong_lenh(argv):
    """Doc "--kenh X --mot-lan" tu dong lenh - che do PHIEN (agent.py goi
    subprocess MOT LUOT cho DUNG mot kenh, xem vm/KE-HOACH.md "5 kenh / 1 VPS
    - buoc A"). Tra (mot_lan: bool, kenh: str|None). Ham THUAN."""
    mot_lan = "--mot-lan" in argv
    kenh = None
    if "--kenh" in argv:
        i = argv.index("--kenh")
        if i + 1 < len(argv):
            kenh = argv[i + 1]
    return mot_lan, kenh


def run_all():
    channels = discover_channels()
    if not channels:
        print("⚠️ Khong tim thay kenh nao (folder <ten>/<ten>.exe).")
        return
    print(f"🚀 Phat hien {len(channels)} kenh: {channels}")
    for ch in channels:
        if not _tu_tra_loi_bat(ch):
            print(f"⏭️ {ch}: tu_tra_loi_cmt dang TAT (tool) -> bo qua.")
            continue
        try:
            process_channel(ch)  # tu bo qua neu kenh chua co token
        except Exception as e:
            print(f"⚠️ Loi kenh {ch}: {e}")


# ========== MAIN ==========
def collect_gemini_keys():
    """Pha 2 (sau khi co token): mo TUNG browser kenh -> NGUOI tu tao 1 Gemini key
    -> tool TU BAT key + luu vao POOL dung chung (config GEMINI_API_KEYS) -> dong browser.
    Cac key dung chung; reply xoay vong, key het quota -> tu sang key khac."""
    channels = discover_channels()
    if not channels:
        return
    done = set(GEMINI_KEY_CHANNELS)               # chrome DA lay key -> bo qua (moi chrome chi 1 lan)
    todo = [ch for ch in channels if ch not in done]
    have = set(_all_gemini_keys())
    if not todo:
        print(f"\n🔑 Tat ca {len(channels)} chrome DA co Gemini key -> bo qua.")
        return
    print(f"\n🔑 ===== LAY GEMINI KEY: {len(todo)} chrome CHUA co (bo qua {len(done)} da co) =====")
    print("   Moi chrome (= 1 gmail) tu tao 1 key (Create API key -> chon/tao project -> Create key).")
    print("   Tool tu nhan key -> dong chrome -> sang chrome tiep theo. Chrome da co key thi bo qua.")
    from DrissionPage import Chromium
    for ch in todo:
        browser_exe = channel_browser_exe(ch)
        if not os.path.isfile(browser_exe):
            continue
        print(f"\n----- {ch}: mo browser de lay Gemini key -----")
        if not _open_channel_browser_debug(browser_exe, DEBUG_PORT):
            print(f"   ⚠️ {ch}: browser khong mo cong debug, bo qua.")
            continue
        key = None
        try:
            browser = Chromium(f"127.0.0.1:{DEBUG_PORT}")
            key = _create_gemini_key(browser)
        except Exception as e:
            print(f"   ⚠️ {ch}: loi {str(e)[:80]}")
        if key:
            _save_gemini_to_config(key, ch)      # luu key + danh dau kenh DA xong
            have.add(key)
            print(f"   ✅ {ch}: da lay key ({key[:10]}...). Tong {len(have)} key.")
        else:
            print(f"   ⚠️ {ch}: CHUA lay duoc key -> chay lai se thu lai DUNG kenh nay (kenh xong da bo qua).")
        try:
            subprocess.run(f'taskkill /F /IM "{os.path.basename(browser_exe)}" /T',
                           shell=True, capture_output=True)
        except Exception:
            pass
        time.sleep(2)
    print(f"\n🔑 ===== XONG: tong {len(have)} Gemini key dung chung =====")


def setup_all_channels():
    """Setup token cho TAT CA kenh phat hien duoc (folder <ten>/<ten>.exe).
    Bo qua kenh da co token (xoa tokens/<ten>.json neu muon lam lai)."""
    channels = discover_channels()
    if not channels:
        print("⚠️ Khong tim thay kenh nao (folder <ten>/<ten>.exe).")
        return
    print(f"🔧 Setup token cho {len(channels)} kenh: {channels}")
    done = skip = fail = 0
    for ch in channels:
        if os.path.isfile(token_path(ch)):
            print(f"\n⏭️ {ch}: da co token -> bo qua (xoa tokens/{ch}.json neu muon lam lai).")
            skip += 1
            continue
        print(f"\n========== SETUP {ch} ==========")
        try:
            setup_channel(ch)
            if os.path.isfile(token_path(ch)):
                done += 1
            else:
                fail += 1
        except Exception as e:
            print(f"❌ Loi setup {ch}: {e}")
            fail += 1
    print(f"\n✅ XONG SETUP: {done} kenh moi co token, {skip} da co san, {fail} loi.")

    # Pha 2: lay Gemini key du phong (nguoi tu tao tay, tool bat) cho tung browser
    if GEMINI_AUTOKEY:
        collect_gemini_keys()


def _khoa_mot_minh(cong=8769):
    """Chi MOT may tra loi moi may - hai con la tra loi trung binh luan."""
    import socket
    global _O_KHOA
    try:
        _O_KHOA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA.bind(("127.0.0.1", cong))
        _O_KHOA.listen(1)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    if build is None:
        print("Thieu thu vien ({0}). Chay CAI-DAT-VPS.bat de cai roi mo lai.".format(
            _THIEU_THU_VIEN))
        raise SystemExit(1)
    if not _khoa_mot_minh():
        print("Da co mot may tra loi khac dang chay - thoat de khong tra loi trung.")
        raise SystemExit(0)
    args = sys.argv[1:]

    if args and args[0] == "setup":
        if len(args) >= 2:
            setup_channel(args[1])      # setup 1 kenh cu the
        else:
            setup_all_channels()        # setup TAT CA kenh (1 lenh xong het)
        # Giu cua so mo de doc ket qua; bam Enter -> dong -> GUI tu chay lai dang/cmt
        try:
            input("\n✅ Xong. Nhan Enter de dong cua so nay...")
        except Exception:
            pass

    elif args and args[0] == "test":
        if len(args) < 2:
            print("Dung: python cmt.py test <ten_kenh>")
        else:
            process_channel(args[1], max_posts=POSTS_PER_RUN)

    elif "--mot-lan" in args:
        # Che do PHIEN: MOT luot cho DUNG mot kenh, khong vong lap production
        # ben duoi - agent.py goi subprocess "--kenh X --mot-lan" ngay trong
        # phien cua kenh do. Van ton trong cong tac tu_tra_loi_cmt cua kenh
        # (giong run_all() - kenh dang TAT thi bo qua, khong ai khac giu cua).
        _mot_lan, _kenh = _doc_co_dong_lenh(args)
        if not _kenh:
            print("Dung: python cmt.py --kenh <ten_kenh> --mot-lan")
        elif not _tu_tra_loi_bat(_kenh):
            print(f"⏭️ {_kenh}: tu_tra_loi_cmt dang TAT (tool) -> bo qua.")
        else:
            process_channel(_kenh, max_posts=POSTS_PER_RUN)

    else:
        # Production: lap vo han, moi chu ky quet tat ca kenh co token
        while True:
            print("\n==============================")
            print(f"🚀 Bat dau luc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            try:
                run_all()
            except Exception as e:
                print("⚠️ Loi khi chay run_all():", e)
            print(f"✅ Hoan tat luc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            jitter = random.uniform(-1800, 1800)   # +-30 phut cho do deu dan nhu may
            wait = max(3600, RUN_INTERVAL_HOURS * 3600 + jitter)
            print(f"⏰ Cho ~{RUN_INTERVAL_HOURS} tieng (lech {int(jitter)}s) truoc lan chay tiep...\n")
            time.sleep(wait)
