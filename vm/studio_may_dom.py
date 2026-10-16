"""MÁY STUDIO (16/10/2026) — bộ chạy DOM cho HÀNG VIỆC MÁY CÓ KIỂU (`core.giam_doc.doc_viec_may_kieu`, khoá `viec_may`
của `nao/viec-tu-giam-doc.json`). Chủ: "mục đích cuối VPS này auto 100%". Phần thuần (ứng viên bìa, cổng, đọc chữ sức
khoẻ, luật trạng thái): `core/studio_may.py`.

  --test-compare   việc `studio_test_compare` (đo Studio vi 16/10/2026): trang sửa video → nút «Thử nghiệm A/B» DƯỚI ô
                   Tiêu đề (`ab_nut` — bản mới gộp thử tiêu đề + bìa, thay «Thử nghiệm và so sánh» cũ) → hộp: chip «Chỉ
                   hình thu nhỏ» (`ab_chip_bia`; mặc định Studio chọn «Chỉ tiêu đề» — máy KHÔNG thử tiêu đề) → ô 1 = bìa A
                   đang chạy (Studio điền sẵn; trống thì tải bản `i.ytimg.com`) → ô 2/3 = ứng viên tốt nhất CÒN LẠI của
                   video (`sm.ung_vien_bia`: hồ sơ `-bia-2/-bia-3`, `7-thumbnail/` của lượt, gói DONE; xếp điểm giám khảo;
                   KHÔNG BAO GIỜ tải tấm trượt cổng `do_bia.cham_tep`) → «Thiết lập thử nghiệm» (`ab_thiet_lap`) → Lưu nếu
                   trang sửa còn thay đổi (chỉ khi tiêu đề không lệch) → ĐỌC LẠI gói Studio `videoCreatorExperiment` (rỗng
                   = chưa có thử nghiệm). Video đã có thử nghiệm → ghi lại, không đụng; không đọc được gói → không đặt mù.
                   Kênh chưa có tính năng nâng cao (sổ chặn ghim / nút tắt) → `bo`, không báo chủ (mục "xác minh điện
                   thoại" tuỳ chọn đã gánh). Không còn ứng viên → `bo`, không mở Chrome.
  --suc-khoe       việc `studio_kiem_suc_khoe` (CHỈ ĐỌC): bảng điều khiển, `youtube.com/features` (Cài đặt → Kênh → «Điều
                   kiện sử dụng tính năng»), Kiếm tiền (YPP, «nội dung dùng lại»), Phát hiện nội dung → Bản quyền, danh
                   sách video (ô «Thông báo») → `ket = {canh_bao, chi_tiet, trang, anh, muc}`; THẤY cảnh báo / gậy / nội
                   dung dùng lại / video bị hạn chế → `can_nguoi`, không thì `xong`. Mỗi kênh mở Chrome tối đa 1 lần / 3
                   ngày (lần đọc còn mới thì đóng việc bằng kết quả ấy).
  --tham-do        (dev, CHỈ ĐỌC) ảnh + bản đồ DOM + chữ các trang trên; `--video ID [--mo-hop [--bam REGEX]]` mở hộp
                   «Thử nghiệm A/B» (bấm thêm trong hộp) rồi ĐÓNG không lưu → `vm/logs/studio-may/<K>.tham-do.json`.

Luật như mọi máy DOM (`thiet_lap_kenh_dom.chay_thuong_hieu`): khung cấm 02:00–07:00 + phút :55–:05; van IPv4 mở → hoãn
(Chrome kênh KHÔNG BAO GIỜ mở khi IPv4 bật — `cdp.ket_noi_kenh` kiểm lại sát lúc mở); máy đăng dở / phiên kênh sắp tới /
gói chờ tải / ghim chờ → nhường; khoá máy `.khoa-may` (khe nặng: dựng, phụ đề, tải lên) bận → hoãn, không ép; Chrome kênh
đang mở (việc khác dùng) → hoãn; khoá Chrome theo kênh của `nuoi_trang_chu`. Hoãn = thoát 10, việc giữ NGUYÊN `cho`.
Không gõ mật khẩu / 2FA, không tự đăng nhập: hồ sơ bị đăng xuất → việc `loi` lý do "dang-xuat" (thoát 20). Không xoá gì
trên YouTube, không đổi tiêu đề / mô tả / chế độ hiển thị. Mỗi lượt MỘT kênh (skill D13/D14 `core/ky_nang.py`, bộ tự kích
hoạt mỗi giờ :35, tối đa một việc nặng mỗi lượt; hỏng 3 lần → nghỉ 24 giờ; việc `loi` 5 lần → `bo`).

Chạy:  python vm/studio_may_dom.py --kenh TL1-T7 --test-compare [--thu | --khong-luu] [--viec m-…]
       python vm/studio_may_dom.py --kenh TL4-T7 --suc-khoe
       python vm/studio_may_dom.py --kenh TL1-T7 --tham-do [--video ID [--mo-hop]]
Mã thoát: 0 xong · 10 hoãn · 20 cần người (đăng xuất / xác minh) · 30 không có việc · 1 lỗi.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.abspath(__file__))                 # vm/
GOC_TOOL = os.path.dirname(GOC)                                  # MyTool/
for _d in (GOC, GOC_TOOL):          # chỉ NỐI ĐUÔI (như thiet_lap_kenh_dom: không đổi thứ tự sys.path của người nạp)
    if _d not in sys.path:
        sys.path.append(_d)
import thiet_lap_kenh_dom as tl  # noqa: E402 — Studio, khoá, khung cấm, chặn, mở Chrome: dùng CHUNG
from core import studio_may as sm  # noqa: E402

nuoi = tl.nuoi
MA_XONG, MA_LOI = 0, 1
MA_HOAN, MA_CAN_NGUOI, MA_KHONG_CAN = tl.MA_HOAN, tl.MA_CAN_NGUOI, tl.MA_KHONG_CAN
DU_KIEN_PHUT = {"test": 15, "suc_khoe": 8, "tham_do": 12}
#: Phiên đăng của BẤT KỲ kênh nào (agent, `trang-thai.json`) tới hạn trong [−90', dự kiến + ngần này phút] → nhường.
NHUONG_PHIEN_PHUT = 20
NHUONG_PHIEN_QUA_HAN_PHUT = 90
#: Việc nền: số `uu_tien` của khe "nang" càng LỚN càng nhường (đăng = 1, sản xuất = 2).
UU_TIEN_KHOA = 3
TOI_DA_VIDEO_PHIEN = 4
CHO_LUU_GIAY = 45

LOAI_TEST, LOAI_SUC_KHOE = "studio_test_compare", "studio_kiem_suc_khoe"


class DangXuat(Exception):
    """Hồ sơ Chrome kênh bị đăng xuất YouTube — việc của người (đăng nhập), máy không bao giờ gõ mật khẩu."""


def thu_muc_so() -> str:
    return os.path.join(GOC, "logs", "studio-may")


def _nhat_ky(kenh: str):
    os.makedirs(thu_muc_so(), exist_ok=True)
    duong = os.path.join(thu_muc_so(), kenh + ".log")

    def ghi(dong):
        nuoi.canh_tien_trien.danh_dau()
        chu = "{0} {1}".format(time.strftime("%Y-%m-%d %H:%M:%S"), dong)
        try:
            print(chu, flush=True)
        except (OSError, UnicodeEncodeError):
            pass
        try:
            with open(duong, "a", encoding="utf-8") as tep:
                tep.write(chu + "\n")
        except OSError:
            pass
    return ghi


def _ghi_json(duong: str, du: Any) -> str:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong + ".tmp", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tmp", duong)
    return duong


# ═══════════════════════════ HÀM THUẦN (có test) ═════════════════════════════
def phien_sap_toi(tt: Dict[str, Any], luc: float, phut: float, qua_han_phut: float = NHUONG_PHIEN_QUA_HAN_PHUT) -> str:
    """Phiên đăng của kênh nào (mục tiêu `phien_muc_tieu@<k>@<ngày>` chưa chạy hôm nay) rơi vào [luc − qua_han, luc + phut]
    → lý do; không thì ""."""
    hom = time.strftime("%Y-%m-%d", time.localtime(luc))
    lt = time.localtime(luc)
    for khoa, gio in (tt or {}).items():
        if not (str(khoa).startswith("phien_muc_tieu@") and str(khoa).endswith("@" + hom) and isinstance(gio, str)):
            continue
        k = str(khoa).split("@")[1]
        if str(tt.get("phien_cuoi@" + k) or "") == hom:
            continue
        m = re.match(r"^\s*(\d{1,2}):(\d{2})", gio)
        if not m:
            continue
        moc = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2)), 0, 0, 0, -1))
        if -qua_han_phut * 60 <= moc - luc <= phut * 60:
            return "phiên đăng kênh {0} lúc {1} sắp/đang tới — nhường".format(k, gio.strip())
    return ""


def phan_loai_thu_nghiem(chu: Any) -> str:
    """Chữ khối Hình thu nhỏ của trang sửa → "dang_chay" | "xong" | "" (chưa có thử nghiệm). Đa ngôn ngữ."""
    s = " ".join(str(chu or "").split()).lower()
    if re.search(r"đang (chạy|thử nghiệm|kiểm tra)|thử nghiệm đang|test (is )?(running|in progress)|testing|実施中|テスト中", s):
        return "dang_chay"
    if re.search(r"(đã|thử nghiệm) (hoàn tất|kết thúc|xong)|kết quả thử nghiệm|test (complete|completed|ended|results?)|"
                 r"テスト(が)?(完了|終了)|結果", s):
        return "xong"
    return ""


def phan_tich_thu_nghiem(exp: Any) -> Dict[str, Any]:
    """`videoCreatorExperiment` trong gói Studio của video (`get_creator_videos`; đo 16/10/2026: video chưa thử nghiệm = `{}`)
    → {co, trang_thai: dang_chay | xong | co, so_bia}. Không biết khuôn thật của thử nghiệm đang chạy nên đọc RỘNG: chuỗi
    trạng thái kiểu RUNNING/ACTIVE/COMPLETE…, số bìa = danh sách dài nhất mang tên nhánh/ảnh (không thấy → None, không so)."""
    if not isinstance(exp, dict) or not exp:
        return {"co": False, "trang_thai": "", "so_bia": None}
    chu, ds_dai = [], []

    def duyet(x, khoa=""):
        if isinstance(x, dict):
            for k, v in x.items():
                duyet(v, str(k))
        elif isinstance(x, list):
            if x and re.search(r"arm|variant|treatment|thumbnail|image|still", khoa, re.I):
                ds_dai.append(len(x))
            for y in x:
                duyet(y, khoa)
        elif isinstance(x, str) and re.search(r"state|status", khoa, re.I):
            chu.append(x)
    duyet(exp)
    s = " ".join(chu).upper()
    tt = ("xong" if re.search(r"COMPLET|FINISH|ENDED|CONCLUD|DONE|STOPPED|WINNER", s) else
          "dang_chay" if re.search(r"RUNNING|ACTIVE|PROGRESS|STARTED|PENDING|SCHEDULED|LIVE", s) else "co")
    return {"co": True, "trang_thai": tt, "so_bia": max(ds_dai) if ds_dai else None, "trang_thai_tho": s[:120]}


#: 16/10/2026 đo thật (Studio vi): nút «Thử nghiệm A/B» nằm DƯỚI ô Tiêu đề của trang sửa (bản mới gộp thử tiêu đề + bìa);
#: tên cũ «Thử nghiệm và so sánh» ở khối Hình thu nhỏ giữ làm dự phòng.
RE_NUT_TEST = r"(thử nghiệm a\s*/\s*b|a\s*/\s*b\s*test|a\s*/\s*b\s*テスト|thử nghiệm và so sánh|test\s*(&|and)\s*compare|テストと比較)"
RE_KHONG_QUYEN = re.compile(r"tính năng nâng cao|advanced features?|高度な機能|xác minh (số )?điện thoại|verify (your )?phone|"
                            r"電話番号(の|を)?確認|không đủ điều kiện|not eligible|ご利用いただけません|chưa (có|được) quyền", re.I)
RE_TIEU_DE_TEST = re.compile(r"(thử nghiệm|test).{0,20}(tiêu đề|title)|(tiêu đề|title).{0,20}(thử nghiệm|test)|タイトル", re.I)


def url_trang_suc_khoe(uc: str) -> List[Tuple[str, str]]:
    """(tên, URL) các trang đọc sức khoẻ (đo 16/10/2026): `youtube.com/features` mở Cài đặt → Kênh → «Điều kiện sử dụng
    tính năng» (3 bậc cơ bản / trung / nâng cao); `/monetization` = YPP; `/copyright` = Phát hiện nội dung → Bản quyền;
    `/videos/upload` = danh sách video (ô «Thông báo», trống = "—")."""
    s = "https://studio.youtube.com/channel/{0}".format(uc)
    return [("bang_dieu_khien", s), ("tinh_nang", "https://www.youtube.com/features"), ("kiem_tien", s + "/monetization"),
            ("ban_quyen", s + "/copyright"), ("noi_dung", s + "/videos/upload")]


def dang_xuat_url(url: str) -> bool:
    return tl.phat_hien_chan(url, "", "") == "dang_xuat"


# ═══════════════════════════ JS ═════════════════════════════════════════════
_JS_TRANG = """(() => { const Y = window.__yd; const hop = Y.qsa(Y.goc(), 'tp-yt-paper-dialog, ytcp-dialog, [role=dialog]').filter(Y.hien)
  .map(d => (d.innerText || '').trim()).filter(x => x);
  return {url: location.href, lang: document.documentElement.lang || '', chu: (document.body ? document.body.innerText : '').slice(0, 15000),
          hop: hop.join('\\n----\\n').slice(0, 8000)}; })()"""

#: Khối «Hình thu nhỏ» của trang sửa + nút «Thử nghiệm và so sánh»: chữ khối, ảnh, nút (chữ/aria/tắt/tâm điểm).
_JS_KHOI_BIA = """((reSrc) => { const Y = window.__yd, re = new RegExp(reSrc, 'i');
  const khoi = Y.qsa(Y.goc(), 'ytcp-video-custom-still-editor, ytcp-thumbnails-compact-editor, ytcp-video-thumbnail-editor, ytcp-thumbnail-editor, #still-picker, ytcp-thumbnails-compact-editor-desktop').filter(Y.hien);
  let k = khoi.length ? khoi[0] : null; while (k && k.parentElement && (k.innerText || '').length < 30) k = k.parentElement;
  const nut = [];
  for (const e of Y.qsa(Y.goc(), 'ytcp-button, button, [role=button], a, tp-yt-paper-button, ytcp-icon-button')) {
    if (!Y.hien(e)) continue; const nh = Y.chuan((e.getAttribute('aria-label') || '') + ' ' + (e.innerText || ''));
    if (!re.test(nh) || nh.length > 120) continue; const r = e.getBoundingClientRect();
    nut.push({chu: nh.slice(0, 100), tag: e.tagName.toLowerCase(), id: e.id || '', tat: Y.tat(e), x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height}); }
  nut.sort((a, b) => a.w * a.h - b.w * b.h);
  const chuK = k ? (k.innerText || '').trim().slice(0, 1500) : '';
  const anh = k ? Y.trong(k, 'img').filter(Y.hien).map(i => i.src || '').filter(x => x).slice(0, 8) : [];
  return {khoi: khoi.map(e => e.tagName.toLowerCase()), chu: chuK, anh: anh, nut: nut.slice(0, 4),
          html: k ? k.outerHTML.slice(0, 6000) : ''}; })"""

#: Hộp «Thử nghiệm và so sánh» đang mở: chữ, ô tải ảnh (input file), nút, ảnh, lựa chọn (radio/tab).
_JS_HOP_TEST = """(() => { const Y = window.__yd;
  const hop = Y.qsa(Y.goc(), 'tp-yt-paper-dialog, ytcp-dialog, [role=dialog], ytcp-ab-test-dialog').filter(Y.hien).filter(d => (d.innerText || '').trim());
  if (!hop.length) return null; const d = hop[hop.length - 1];
  const nut = Y.trong(d, 'ytcp-button, button, [role=button], [role=radio], [role=tab], tp-yt-paper-radio-button, [role=checkbox], [role=option]')
    .filter(Y.hien).map(e => { const r = e.getBoundingClientRect();
      return {chu: Y.chuan((e.getAttribute('aria-label') || '') + ' ' + (e.innerText || '')).slice(0, 80), tag: e.tagName.toLowerCase(), id: e.id || '',
              tat: Y.tat(e), chon: e.getAttribute('aria-checked') || e.getAttribute('aria-selected') || e.getAttribute('checked') || '', x: r.x + r.width / 2, y: r.y + r.height / 2}; });
  const tep = Y.trong(d, 'input[type=file]').map(i => ({id: i.id || '', ten: i.name || '', accept: i.accept || '', nhieu: !!i.multiple}));
  const anh = Y.trong(d, 'img').filter(Y.hien).map(i => i.src || '').filter(x => x);
  return {tag: d.tagName.toLowerCase(), chu: (d.innerText || '').trim().slice(0, 4000), nut: nut.slice(0, 40), tep: tep, anh: anh.slice(0, 10),
          html: d.outerHTML.slice(0, 12000)}; })()"""

#: Ô bìa của hộp «Thử nghiệm A/B» (đo 16/10/2026: 3 × `ytcp-thumbnail-uploader` — ô 1 có sẵn bìa đang chạy
#: `button#preview-button`, ô trống có `button#select-button` «Thêm hình thu nhỏ», mỗi ô một `input#file-loader` ẩn).
#: Ghim phần tử (Y.tra) để bấm bằng chuột thật / đặt tệp.
_JS_O_BIA_HOP = """(() => { const Y = window.__yd;
  const hop = Y.qsa(Y.goc(), 'tp-yt-paper-dialog, ytcp-dialog, [role=dialog]').filter(Y.hien).filter(d => (d.innerText || '').trim());
  if (!hop.length) return null; const d = hop[hop.length - 1];
  const o = Y.trong(d, 'ytcp-thumbnail-uploader').filter(Y.hien);
  return o.map((u, i) => { const xem = Y.trong(u, '#preview-button').filter(Y.hien)[0], them = Y.trong(u, '#select-button').filter(Y.hien)[0];
    const tep = Y.trong(u, 'input[type=file]')[0], img = Y.trong(u, 'img').filter(Y.hien).map(x => x.src || '').filter(x => x);
    return {i: i, co_anh: !!xem || (img.length > 0 && !them), them: them ? Y.tra(them, 'o_bia', '#select-button', 1) : null,
            tep: tep ? Y.tra(tep, 'o_bia', 'input[type=file]', 1) : null, anh: img.slice(0, 2), chu: Y.chuan(u.innerText).slice(0, 80)}; }); })()"""
#: Chip loại thử nghiệm của hộp: `ytcp-chip#chip-0` Chỉ tiêu đề · `#chip-1` Chỉ hình thu nhỏ · `#chip-2` Tiêu đề và hình thu nhỏ.
RE_CHIP_BIA = r"^(chỉ hình thu nhỏ|thumbnail only|サムネイルのみ)"
RE_CHIP_TIEU_DE = r"^(chỉ tiêu đề|title only|タイトルのみ)"
RE_NUT_THIET_LAP = r"^(thiết lập thử nghiệm|set (up )?test|start test|テストを設定|テストを開始)"
RE_NUT_XAC_NHAN = r"^(thiết lập|bắt đầu|xác nhận|tiếp tục|ok|đồng ý|set test|start|confirm|continue|開始|確認|続行)"


# ═══════════════════════════ PHIÊN CHUNG ════════════════════════════════════
def chrome_dang_mo(agent, cfg: dict, kenh: str, cdp_mod=None) -> str:
    """"" nếu Chrome kênh ĐANG TẮT; không thì lý do (việc khác đang dùng trình duyệt kênh — không chen)."""
    try:
        ch = agent.cau_hinh_kenh(cfg, kenh)
        if cdp_mod is not None and cdp_mod.hoi_phien_ban(agent._cong_devtools(ch)):  # noqa: SLF001
            return "Chrome kênh {0} đang mở (cổng DevTools đáp) — việc khác đang dùng".format(kenh)
        chrome = agent.tim_chrome(ch)
        if not chrome:
            return "không thấy trình duyệt kênh {0}".format(kenh)
        if agent._chrome_dang_chay(chrome):  # noqa: SLF001
            return "Chrome kênh {0} đang chạy — việc khác đang dùng".format(kenh)
    except Exception as loi:  # noqa: BLE001 — không chắc thì không chen
        return "không kiểm được Chrome kênh: {0}".format(str(loi)[:100])
    return ""


def ly_do_hoan(agent, cfg: dict, kenh: str, luc: float, du_kien: float, bo_qua_khung: bool = False, cdp_mod=None) -> str:
    """Bảo vệ TRƯỚC khi mở Chrome (cùng luật các máy DOM khác). "" = được chạy."""
    if not bo_qua_khung:
        r = tl.khung_cam(luc, du_kien) or tl.khung_gio_tron(luc, du_kien)
        if r:
            return r
    try:
        tl.kiem_truoc_khi_chay(agent, kenh)                 # van IPv4 + máy đăng dở (cả vm/logs lẫn logs/)
    except tl.Hoan as h:
        return str(h)
    r = nuoi.viec_dang_cho(agent, luc, kenh)                # phiên kênh này sắp tới / gói chờ tải / ghim chờ
    if r:
        return "nhường: " + r
    try:
        r = phien_sap_toi(agent._doc_trang_thai(cfg), luc, du_kien + NHUONG_PHIEN_PHUT)  # noqa: SLF001
    except Exception:  # noqa: BLE001
        r = ""
    if r:
        return r
    return chrome_dang_mo(agent, cfg, kenh, cdp_mod)


def chay_phien(kenh: str, ghi, lam: Callable[..., Any], che_do: str, bo_qua_khung: bool = False, cho_luu: bool = False,
               rng=None) -> Tuple[int, Any]:
    """Khung chung (như `thiet_lap_kenh_dom.chay_thuong_hieu`): bảo vệ → khoá → Chrome kênh (máy này tự mở, đóng cuối
    phiên) → Studio (UC ghim, giao diện vi tạm) → `lam(S, md)` → đóng tab/Chrome, TRẢ ngôn ngữ, nhả khoá.
    `cho_luu`: luồng ĐƯỢC bấm Lưu trang sửa (`cam_bam_sua_video`). Trả (mã, kết quả `lam` | lý do)."""
    rng = rng or random.Random()
    luc0 = time.time()
    agent = nuoi._nap_agent(ghi)                                    # noqa: SLF001
    try:
        cfg = tl._cfg_kenh(agent, kenh)                             # noqa: SLF001
        cdp_mod, cdp_studio = tl._nap_cdp()                         # noqa: SLF001
    except Exception as loi:  # noqa: BLE001
        ghi("hoãn: không đọc được cấu hình agent: {0}".format(str(loi)[:160]))
        return MA_HOAN, "không đọc được cấu hình agent"
    r = ly_do_hoan(agent, cfg, kenh, luc0, DU_KIEN_PHUT.get(che_do, 15), bo_qua_khung, cdp_mod)
    if r:
        ghi("hoãn: " + r)
        return MA_HOAN, r
    if not nuoi.giu_khoa("_studio-may", thu_muc_so()):
        ghi("hoãn: đang có phiên máy Studio khác")
        return MA_HOAN, "đang có phiên máy Studio khác"
    khoa_may = khoa_kenh = False
    cdp = md = S = None
    try:
        if not agent.giu_khoa_may_chung(viec="studio_may", kenh=kenh, uu_tien=UU_TIEN_KHOA):
            raise tl.Hoan("khoá máy (.khoa-may) đang bận — không ép")
        khoa_may = True
        if not nuoi.giu_khoa(kenh):
            raise tl.Hoan("kênh {0} đang có tiến trình khác giữ khoá Chrome".format(kenh))
        khoa_kenh = True
        nuoi.xoa_co_dung(kenh)
        r = chrome_dang_mo(agent, cfg, kenh, cdp_mod) or nuoi.duoc_mo_them(len(nuoi.cac_kenh_dang_nuoi()), nuoi.ram_trong_gb())
        if r:
            raise tl.Hoan(r)
        if agent.van_ipv4_mo():
            raise tl.Hoan("van IPv4 đang mở")
        import may_dang_dom as mdd                                  # noqa: PLC0415 — sau _nap_cdp: đúng vm/
        ch = agent.cau_hinh_kenh(cfg, kenh)
        try:
            agent.ghi_che_do_mat_cao(ch, False)                     # Chrome mở cho việc Studio — mắt cào KHÔNG quét
        except Exception:  # noqa: BLE001
            pass
        try:
            cdp = cdp_mod.ket_noi_kenh(cfg, kenh, nhat_ky=ghi)      # tự kiểm van IPv4 lần nữa sát lúc mở
        except cdp_mod.CdpKhongDung as e:
            raise tl.Hoan("không nối được Chrome kênh: {0} (mã {1})".format(e.ly_do, e.ma))
        ghi("── MÁY STUDIO {0} [{1}] — Chrome cổng {2}{3} ──".format(kenh, che_do, cdp.cong,
                                                                  " (máy này tự mở)" if cdp.tu_mo else " (có sẵn — chỉ TAB của mình)"))
        nuoi.canh_tien_trien.bat_canh(lambda: (cdp_mod.dong_trinh_duyet(cdp) if cdp.tu_mo else cdp.dong()), ghi=ghi)
        bo = cdp_studio.doc_bo_chon()
        if cho_luu:     # nút Lưu của trang sửa nằm trong `cam_bam` cho mọi luồng khác — riêng luồng này được bấm
            cam = dict(bo.get("cam_bam_sua_video") or {}) or dict(bo.get("cam_bam") or {}, chon=[
                s for s in (bo.get("cam_bam") or {}).get("chon") or [] if "#save" not in s])
            bo = dict(bo, cam_bam={k: x for k, x in cam.items() if k != "ghi_chu"})
        thu_muc_anh = os.path.join(thu_muc_so(), kenh)
        md = mdd.MayDangDom(kenh, bo, lambda: cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=ghi, thu_muc_dom=thu_muc_anh, rng=rng),
                            mdd.SoVideoId(), bao=None, thu_muc_done="", nhat_ky=ghi)
        S = tl.Studio(md.tab_b(), ghi, thu_muc_anh)
        try:
            S.uc = md.lay_uc()                                      # đúng UC đã ghim + tạm giao diện vi (trả lại cuối phiên)
        except mdd.DungKenh as e:
            raise tl.CanNguoi(str(e))
        except Exception:  # noqa: BLE001
            if dang_xuat_url(S.url()):
                raise DangXuat("Chrome kênh {0} bị đăng xuất YouTube ({1})".format(kenh, S.url()[:60]))
            S.kiem_chan()
            raise
        if dang_xuat_url(S.url()):
            raise DangXuat("Chrome kênh {0} bị đăng xuất YouTube".format(kenh))
        return MA_XONG, lam(S, md, agent)
    except DangXuat as e:
        ghi("DỪNG — {0} (đăng nhập là việc của người, máy không gõ mật khẩu)".format(e))
        if S:
            S.chup("dang-xuat")
        return MA_CAN_NGUOI, "dang-xuat"
    except tl.CanNguoi as c:
        ghi("DỪNG — cần người: {0}".format(c))
        if S:
            S.chup("can-nguoi")
        return MA_CAN_NGUOI, ("dang-xuat" if "đăng xuất" in str(c) or "đăng nhập" in str(c) else str(c)[:200])
    except tl.Hoan as h:
        ghi("hoãn: {0}".format(h))
        return MA_HOAN, str(h)
    except Exception as e:  # noqa: BLE001
        ghi("PHIÊN LỖI: {0}".format(str(e)[:300]))
        if S:
            S.chup("studio-may-loi")
        return MA_LOI, str(e)[:300]
    finally:
        try:
            if md is not None:
                md.dong_het()                                       # CHỈ tab của phiên này
            if cdp is not None:
                try:
                    import ngon_ngu_tam  # noqa: PLC0415
                    ngon_ngu_tam.tra(cdp, kenh, ghi)
                except Exception as e:  # noqa: BLE001
                    ghi("trả ngôn ngữ giao diện lỗi: {0}".format(str(e)[:120]))
                if cdp.tu_mo:
                    ghi("đóng Chrome kênh {0} (máy này đã mở): {1}".format(
                        kenh, "đã đóng" if cdp_mod.dong_trinh_duyet(cdp) else "CỔNG CHƯA ĐÓNG"))
                    tl.don_launcher_mo_coi(kenh, ghi)
                else:
                    cdp.dong()
        finally:
            if khoa_kenh:
                nuoi.xoa_co_dung(kenh)
                nuoi.nha_khoa(kenh)
            if khoa_may:
                agent.nha_khoa_may_chung()
            nuoi.nha_khoa("_studio-may", thu_muc_so())


def _kiem_dung(agent, kenh: str) -> None:
    """Giữa hai video: agent đòi Chrome kênh (cờ `.dung`), khung cấm, việc đăng chờ → DỪNG lịch sự (Hoan)."""
    r = tl.ly_do_dung(agent, kenh, time.time())
    if r:
        raise tl.Hoan("dừng giữa chừng: " + r)


def _cho(S, ham, han: float, buoc: float = 1.0):
    het = time.monotonic() + han
    while True:
        try:
            v = ham()
        except Exception:  # noqa: BLE001
            v = None
        if v or time.monotonic() >= het:
            return v
        S.ngu(buoc)


def _mo_trang_sua(S, vid: str) -> None:
    S.st.mo("https://studio.youtube.com/video/{0}/edit".format(vid), han=60)
    if dang_xuat_url(S.url()):
        raise DangXuat("bị đăng xuất khi mở trang sửa")
    if not S.st.tim("tieu_de", han=40):
        raise tl.LoiMuc("trang sửa video {0} không dựng xong (không thấy ô tiêu đề)".format(vid))
    S.ngu(3)


def doc_khoi_bia(S) -> Dict[str, Any]:
    """Đọc khối Hình thu nhỏ + nút «Thử nghiệm và so sánh» (chỉ đọc). Thêm `thu_nghiem` = dang_chay | xong | ""."""
    du = S.js("({0})({1})".format(_JS_KHOI_BIA, json.dumps(RE_NUT_TEST))) or {}
    du["thu_nghiem"] = phan_loai_thu_nghiem(du.get("chu"))
    return du


# ═══════════════════════════ THĂM DÒ (CHỈ ĐỌC) ══════════════════════════════
def tham_do(S, md, agent, kenh: str, ghi, video: str = "", mo_hop: bool = False, bam: Any = ()) -> Dict[str, Any]:
    kq: Dict[str, Any] = {"kenh": kenh, "luc": time.strftime("%Y-%m-%d %H:%M:%S"), "trang": {}}
    for ten, url in ([] if video else url_trang_suc_khoe(S.uc)):
        try:
            S.st.mo(url, han=60)
            S.ngu(6)
            du = S.js(_JS_TRANG) or {}
            bc = S.st.ghi_bang_chung("tham-do-" + ten)
            kq["trang"][ten] = {"url": du.get("url"), "chu": du.get("chu"), "hop": du.get("hop"), "anh": bc.get("anh"),
                                "ban_do": bc.get("ban_do")}
            ghi("   {0}: {1} — {2} ký tự, hộp {3} ký tự".format(ten, str(du.get("url"))[:90], len(du.get("chu") or ""),
                                                                 len(du.get("hop") or "")))
        except Exception as e:  # noqa: BLE001
            kq["trang"][ten] = {"loi": str(e)[:200]}
            ghi("   {0}: LỖI {1}".format(ten, str(e)[:160]))
        _kiem_dung(agent, kenh)
    if video:
        try:        # gói JSON Studio của video (bắt `get_creator_videos` lúc mở trang sửa): khoá nào nói về thử nghiệm
            ds = S.st.bat_json("https://studio.youtube.com/video/{0}/edit".format(video), "get_creator_videos", han=30) or []
            goi = next((v for g in ds for v in ((g or {}).get("videos") or []) if str(v.get("videoId") or "") == video), None)
            kq["goi_khoa"] = sorted(goi.keys()) if isinstance(goi, dict) else None
            kq["goi_thu_nghiem"] = {k: v for k, v in (goi or {}).items() if re.search(r"xperiment|abtest|ab_test|test", k, re.I)}
            ghi("   gói Studio: {0} khoá · thử nghiệm: {1}".format(len(kq["goi_khoa"] or []), json.dumps(kq["goi_thu_nghiem"])[:300]))
        except Exception as e:  # noqa: BLE001
            ghi("   bắt gói Studio lỗi: {0}".format(str(e)[:120]))
        _mo_trang_sua(S, video)
        kb = doc_khoi_bia(S)
        bc = S.st.ghi_bang_chung("tham-do-sua-" + video)
        kq["sua"] = dict(kb, anh_chup=bc.get("anh"), ban_do=bc.get("ban_do"))
        ghi("   trang sửa {0}: khối {1} · thử nghiệm «{2}» · nút: {3}".format(video, kb.get("khoi"), kb.get("thu_nghiem"),
                                                                           [n.get("chu") for n in kb.get("nut") or []]))
        nut = [n for n in kb.get("nut") or [] if not n.get("tat")]
        if mo_hop and nut:
            S.st._bam_diem(round(nut[0]["x"], 1), round(nut[0]["y"], 1))    # noqa: SLF001
            S.ngu(5)
            hop = _cho(S, lambda: S.js(_JS_HOP_TEST), 20)
            bc = S.st.ghi_bang_chung("tham-do-hop-" + video)
            kq["hop"] = dict(hop or {}, anh_chup=bc.get("anh"), ban_do=bc.get("ban_do"))
            ghi("   hộp thử nghiệm: {0}".format(" ".join(str((hop or {}).get("chu") or "(không thấy hộp)").split())[:600]))
            for i, re_bam in enumerate(bam or ()):          # (dev) bấm tiếp trong hộp theo chữ — vẫn KHÔNG lưu
                n = [x for x in ((S.js(_JS_HOP_TEST) or {}).get("nut") or []) if re.search(re_bam, x.get("chu") or "", re.I)]
                if not n:
                    ghi("   không thấy nút «{0}» trong hộp".format(re_bam))
                    break
                S.st._bam_diem(round(n[0]["x"], 1), round(n[0]["y"], 1))    # noqa: SLF001
                S.ngu(4)
                hop = S.js(_JS_HOP_TEST) or {}
                bc = S.st.ghi_bang_chung("tham-do-hop-{0}-{1}".format(i + 1, video))
                kq["hop_{0}".format(i + 1)] = dict(hop, anh_chup=bc.get("anh"), ban_do=bc.get("ban_do"))
                ghi("   sau khi bấm «{0}»: {1}".format(n[0]["chu"], " ".join(str(hop.get("chu") or "").split())[:600]))
            dong_hop_khong_luu(S, ghi)
            kq["sau_dong"] = {"luu_tat": luu_dang_tat(S)}
            ghi("   đã đóng hộp — nút Lưu trang sửa {0}".format("TẮT (không có gì đổi)" if kq["sau_dong"]["luu_tat"]
                                                                  else "BẬT — huỷ thay đổi"))
            if not kq["sau_dong"]["luu_tat"]:
                huy_thay_doi(S, ghi)
    _ghi_json(os.path.join(thu_muc_so(), "{0}.tham-do.json".format(kenh)), kq)
    return kq


def luu_dang_tat(S) -> bool:
    pt = S.st.tim("sua_luu", han=3, cho_tat=True)
    return bool(pt is None or pt.get("tat"))


def huy_thay_doi(S, ghi) -> None:
    """Bỏ mọi thay đổi chưa lưu (nút «Huỷ thay đổi» của trang sửa) — rời trang không lưu nhầm."""
    try:
        if S.st.co("sua_huy_thay_doi"):
            S.st.bam("sua_huy_thay_doi", han_hau=5)
            S.ngu(2)
    except Exception as e:  # noqa: BLE001
        ghi("   huỷ thay đổi hỏng: {0}".format(str(e)[:120]))


def dong_hop_khong_luu(S, ghi) -> None:
    """Đóng hộp đang mở KHÔNG lưu: nút Huỷ / Đóng của hộp, không được thì Escape."""
    for _ in range(3):
        hop = S.js(_JS_HOP_TEST)
        if not hop:
            return
        nut = [n for n in hop.get("nut") or [] if re.search(r"^(huỷ|hủy|cancel|キャンセル|đóng|close|閉じる)\b", n.get("chu") or "", re.I)
               and not n.get("tat")]
        if nut:
            S.st._bam_diem(round(nut[0]["x"], 1), round(nut[0]["y"], 1))    # noqa: SLF001
        else:
            S.st.phim("Escape")
        S.ngu(2)
        hop2 = S.js(_JS_HOP_TEST)
        if hop2 and re.search(r"(bỏ|huỷ|hủy) (thay đổi|thử nghiệm)|discard|破棄", str(hop2.get("chu") or ""), re.I):
            xn = [n for n in hop2.get("nut") or [] if re.search(r"^(bỏ|huỷ|hủy|discard|破棄)", n.get("chu") or "", re.I)]
            if xn:
                S.st._bam_diem(round(xn[0]["x"], 1), round(xn[0]["y"], 1))  # noqa: SLF001
                S.ngu(2)
    ghi("   (!) hộp vẫn mở sau 3 lần đóng")


# ═══════════════════════════ CHẠY THEO CHẾ ĐỘ ═══════════════════════════════
def _bay() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _cap_nhat(goc: str, id_viec: str, ghi, **truong) -> None:
    from core import giam_doc  # noqa: PLC0415
    giam_doc.cap_nhat_viec_may_kieu(goc, id_viec, **truong)
    ket = truong.get("ket") or {}
    ghi("   việc {0} → {1}{2}".format(id_viec, truong.get("trang_thai", "?"),
                                     " — " + str(ket.get("ly_do") or ket.get("chi_tiet") or "")[:200] if ket else ""))


def _viec(goc: str, loai: str, kenh: str, chi_viec: str = "") -> List[Dict[str, Any]]:
    from core import giam_doc  # noqa: PLC0415
    return [m for m in giam_doc.doc_viec_may_kieu(goc, loai) if m.get("kenh") == kenh and (not chi_viec or m.get("id") == chi_viec)]


def _ket_phien_hong(goc: str, ids: List[str], ma: int, ly: Any, ghi) -> None:
    """Phiên không làm xong: hoãn → việc về `cho` (không tính lần thử); đăng xuất / lỗi → `loi` (5 lần thành `bo`)."""
    for i in ids:
        if ma == MA_HOAN:
            _cap_nhat(goc, i, ghi, trang_thai="cho")
        else:
            _cap_nhat(goc, i, ghi, trang_thai="loi", ket={"ly_do": "dang-xuat" if ly == "dang-xuat" else str(ly)[:300],
                                                          "luc": _bay()})


# ── studio_kiem_suc_khoe ─────────────────────────────────────────────────────
def doc_trang_suc_khoe(S, agent, kenh: str, ghi) -> Dict[str, Dict[str, Any]]:
    """Mở từng trang sức khoẻ (CHỈ ĐỌC): chữ trang + chữ hộp (Cài đặt mở dạng hộp), ảnh bằng chứng."""
    trang: Dict[str, Dict[str, Any]] = {}
    for ten, url in url_trang_suc_khoe(S.uc):
        _kiem_dung(agent, kenh)
        try:
            S.st.mo(url, han=60)
            if dang_xuat_url(S.url()):
                raise DangXuat("bị đăng xuất khi mở {0}".format(ten))
            du = _cho(S, lambda: (lambda d: d if len(str(d.get("chu") or "")) + len(str(d.get("hop") or "")) > 300 else None)(
                S.js(_JS_TRANG) or {}), 30, 1.5) or (S.js(_JS_TRANG) or {})
            S.ngu(3)
            du = S.js(_JS_TRANG) or du
            bc = S.st.ghi_bang_chung("suc-khoe-" + ten)
            chu = "\n".join(x for x in (str(du.get("hop") or ""), str(du.get("chu") or "")) if x)
            trang[ten] = {"url": str(du.get("url") or "")[:200], "chu": chu, "anh": bc.get("anh") or ""}
            ghi("   {0}: {1} ký tự · {2}".format(ten, len(chu), str(du.get("url"))[:90]))
        except DangXuat:
            raise
        except Exception as e:  # noqa: BLE001 — một trang hỏng: đọc tiếp trang khác
            trang[ten] = {"url": url, "chu": "", "loi": str(e)[:200], "anh": ""}
            ghi("   {0}: LỖI {1}".format(ten, str(e)[:160]))
    return trang


def chay_suc_khoe(kenh: str, ghi, bo_qua_khung: bool = False, chi_viec: str = "", rng=None, phien=None) -> int:
    goc = GOC_TOOL
    ds = _viec(goc, LOAI_SUC_KHOE, kenh, chi_viec)
    if not ds:
        ghi("không có việc đọc sức khoẻ Studio của {0}".format(kenh))
        return MA_KHONG_CAN
    import datetime as _dt  # noqa: PLC0415
    cu = sm.con_moi_suc_khoe(goc, kenh, _dt.datetime.now())
    if cu:      # tối đa 1 lần / 3 ngày / kênh: đóng việc bằng lần đọc còn mới, không mở Chrome
        ket = {k: cu.get(k) for k in ("canh_bao", "chi_tiet", "trang", "anh", "muc")}
        ket.update(tu_lan_doc=cu.get("luc"), luc=_bay())
        for m in ds:
            _cap_nhat(goc, m["id"], ghi, trang_thai="can_nguoi" if cu.get("canh_bao") else "xong", ket=ket)
        return MA_XONG
    ma, r = (phien or chay_phien)(kenh, ghi, lambda S, md, agent: doc_trang_suc_khoe(S, agent, kenh, ghi), "suc_khoe",
                                  bo_qua_khung=bo_qua_khung, rng=rng)
    if ma != MA_XONG:
        _ket_phien_hong(goc, [] if ma == MA_HOAN else [m["id"] for m in ds], ma, r, ghi)
        return ma
    trang = r or {}
    kq = sm.doc_suc_khoe({t: {"chu": v.get("chu")} for t, v in trang.items()})
    if not kq["doc_duoc"]:
        _ket_phien_hong(goc, [m["id"] for m in ds], MA_LOI, "không đọc được trang Studio nào", ghi)
        return MA_LOI
    anh = next((v.get("anh") for v in trang.values() if v.get("anh")), "")
    ket = {"canh_bao": kq["canh_bao"], "chi_tiet": kq["chi_tiet"], "muc": kq["muc"], "anh": anh, "luc": _bay(),
           "trang": {t: {"url": v.get("url"), "anh": v.get("anh"), "loi": v.get("loi", "")} for t, v in trang.items()}}
    _ghi_json(sm.duong_ket_suc_khoe(goc, kenh), dict(ket, kenh=kenh, chu={t: str(v.get("chu") or "")[:15000]
                                                                        for t, v in trang.items()}))
    ghi("*** SỨC KHOẺ STUDIO {0}: {1} ***".format(kenh, kq["chi_tiet"][:300]))
    for m in ds:
        _cap_nhat(goc, m["id"], ghi, trang_thai="can_nguoi" if kq["canh_bao"] else "xong", ket=ket)
    return MA_XONG


# ── studio_test_compare ──────────────────────────────────────────────────────
def _gon(s: Any, n: int = 300) -> str:
    return " ".join(str(s or "").split())[:n]


def doc_trang_sua(S, vid: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Mở trang sửa, BẮT gói Studio của video (`get_creator_videos` → `videoCreatorExperiment`) + đọc khối bìa / nút «Thử
    nghiệm A/B». Gói None = không đọc được trạng thái thử nghiệm (người gọi KHÔNG đặt thử nghiệm mù)."""
    url = "https://studio.youtube.com/video/{0}/edit".format(vid)
    goi = None
    try:
        ds = S.st.bat_json(url, "get_creator_videos", han=30) or []
        goi = next((v for g in ds for v in ((g or {}).get("videos") or []) if str(v.get("videoId") or "") == vid), None)
    except Exception:  # noqa: BLE001
        S.st.mo(url, han=60)
    if dang_xuat_url(S.url()):
        raise DangXuat("bị đăng xuất khi mở trang sửa")
    if not S.st.tim("tieu_de", han=40):
        raise tl.LoiMuc("trang sửa video {0} không dựng xong (không thấy ô tiêu đề)".format(vid))
    S.ngu(3)
    return goi, doc_khoi_bia(S)


def _tim_khoa(S, khoa: str, han: float = 2.0) -> Optional[Dict[str, Any]]:
    """Phần tử theo khoá `vm/studio-selectors.json` (bản JSON cũ chưa có khoá → None, người gọi lùi về dò theo chữ).
    `han` < `tu_chua_dom.NGUONG_HAN`: không gọi bộ tự chữa AI cho bước phụ."""
    if khoa not in ((getattr(S.st, "bo", None) or {}).get("phan_tu") or {}):
        return None
    try:
        return S.st.tim(khoa, han=han, cho_tat=True)
    except Exception:  # noqa: BLE001
        return None


def _nut_hop(S, re_src: str, ca_tat: bool = False) -> Optional[Dict[str, Any]]:
    return next((n for n in ((S.js(_JS_HOP_TEST) or {}).get("nut") or [])
                 if re.search(re_src, n.get("chu") or "", re.I) and (ca_tat or not n.get("tat"))), None)


def _dat_tep_o(S, o: Dict[str, Any], duong: str) -> str:
    """Tải `duong` vào MỘT ô bìa trống của hộp: bấm «Thêm hình thu nhỏ» → bắt hộp chọn tệp → DOM.setFileInputFiles;
    dự phòng: đặt thẳng vào `input#file-loader` ẩn của ô. Trả cách đã dùng."""
    cdp, sid = S.st.cdp, S.st.sid
    duong = os.path.abspath(duong)
    if o.get("them"):
        cdp.tep_cho.pop(sid, None)
        try:
            S.st.bam(o["them"])
            het = time.monotonic() + 10
            while time.monotonic() < het:
                p = cdp.tep_cho.pop(sid, None)
                if p and p.get("backendNodeId"):
                    cdp.goi("DOM.setFileInputFiles", {"files": [duong], "backendNodeId": p["backendNodeId"]}, sid=sid, han=30)
                    return "hop_chon_tep"
                cdp.bom(0.3)
        except Exception:  # noqa: BLE001 — lùi về ô tệp ẩn
            pass
    if o.get("tep"):
        oid = S.st._js("lay", o["tep"]["id"], gia_tri=False)       # noqa: SLF001
        if oid:
            cdp.goi("DOM.setFileInputFiles", {"files": [duong], "objectId": oid}, sid=sid, han=30)
            return "o_tep"
    raise tl.LoiMuc("không tải được bìa vào ô {0}".format(o.get("i")))


def mdd_chuan(s: Any) -> str:
    return " ".join(str(s or "").split())


def _so_o_co_anh(S) -> int:
    return sum(1 for o in (S.js(_JS_O_BIA_HOP) or []) if o.get("co_anh"))


def test_mot_video(S, vid: str, kh: Dict[str, Any], ghi, thu: bool = False, khong_luu: bool = False) -> Dict[str, Any]:
    """MỘT video (đo Studio vi 16/10/2026): trang sửa → gói Studio `videoCreatorExperiment` (đã có thử nghiệm → ghi lại,
    không đụng) → nút «Thử nghiệm A/B» (`ytcp-button#ab-test-button`, dưới ô Tiêu đề) → chip «Chỉ hình thu nhỏ» → ô 1 = bìa
    đang chạy (Studio điền sẵn; trống thì tải bìa A) → tải ứng viên vào ô 2/3 → «Thiết lập thử nghiệm» → (Lưu nếu trang
    sửa còn thay đổi) → ĐỌC LẠI gói Studio. Trả {ket, ly_do, trang_thai, so_bia, tieu_de_test, anh…}."""
    goi, kb = doc_trang_sua(S, vid)
    ra: Dict[str, Any] = {"anh_truoc": S.st.ghi_bang_chung("test-truoc-" + vid).get("anh") or ""}
    tn = phan_tich_thu_nghiem((goi or {}).get("videoCreatorExperiment"))
    ghi("   {0}: gói Studio {1} · thử nghiệm {2} · nút {3}".format(vid, "có" if goi else "KHÔNG ĐỌC ĐƯỢC", tn,
                                                              [(n.get("chu"), n.get("tat")) for n in kb.get("nut") or []]))
    if tn["co"]:
        return dict(ra, ket=sm.KV_DA_CO, trang_thai=tn["trang_thai"], so_bia=tn["so_bia"])
    if goi is None:
        return dict(ra, ket=sm.KV_LOI, ly_do="không đọc được gói Studio của video (trạng thái thử nghiệm) — không đặt mù")
    pt = _tim_khoa(S, "ab_nut")                      # `ytcp-button#ab-test-button` (studio-selectors.json)
    nut = ([dict(pt, x=pt["rect"]["x"] + pt["rect"]["w"] / 2.0, y=pt["rect"]["y"] + pt["rect"]["h"] / 2.0)] if pt and not pt.get("tat")
           else [n for n in kb.get("nut") or [] if not n.get("tat")])
    if not nut:
        if (pt and pt.get("tat")) or kb.get("nut") or RE_KHONG_QUYEN.search(str(kb.get("chu") or "")):
            return dict(ra, ket=sm.KV_KHONG_QUYEN, ly_do="nút «Thử nghiệm A/B» bị tắt — kênh chưa có tính năng nâng cao")
        return dict(ra, ket=sm.KV_LOI, ly_do="không thấy nút «Thử nghiệm A/B» trên trang sửa")
    if thu:
        return dict(ra, ket="doc", ly_do="chỉ đọc (--thu)")
    tep = [u.get("tai_len") or u.get("tep") for u in kh.get("chon") or []][:sm.TOI_DA_UNG_VIEN]
    if not tep:
        return dict(ra, ket=sm.KV_KHONG_UNG_VIEN)
    # ── hộp «Thử nghiệm A/B» ──
    if pt and not pt.get("tat"):
        S.st.bam(pt)                                 # bấm có kiểm đích (cuộn vào giữa, không bị che, không phần tử cấm)
    else:
        S.st._bam_diem(round(nut[0]["x"], 1), round(nut[0]["y"], 1))    # noqa: SLF001
    hop = _cho(S, lambda: S.js(_JS_HOP_TEST), 20)
    if not hop:
        return dict(ra, ket=sm.KV_LOI, ly_do="bấm «Thử nghiệm A/B» mà hộp không mở")
    chu_hop = str(hop.get("chu") or "")
    ra["tieu_de_test"] = bool(_nut_hop(S, RE_CHIP_TIEU_DE, True) or RE_TIEU_DE_TEST.search(chu_hop))
    try:
        if RE_KHONG_QUYEN.search(chu_hop):
            return dict(ra, ket=sm.KV_KHONG_QUYEN, ly_do="Studio: " + _gon(chu_hop, 200))
        chip = _nut_hop(S, RE_CHIP_BIA, True)
        if not chip:
            return dict(ra, ket=sm.KV_LOI, ly_do="hộp Thử nghiệm A/B không có lựa chọn «Chỉ hình thu nhỏ»: " + _gon(chu_hop, 160))
        if str(chip.get("chon")) != "true":
            S.st._bam_diem(round(chip["x"], 1), round(chip["y"], 1))  # noqa: SLF001
            S.ngu(2)
        if not _cho(S, lambda: str((_nut_hop(S, RE_CHIP_BIA, True) or {}).get("chon")) == "true"
                    and len(S.js(_JS_O_BIA_HOP) or []) >= 2, 10):
            return dict(ra, ket=sm.KV_LOI, ly_do="không chọn được «Chỉ hình thu nhỏ» / không thấy ô bìa")
        o = S.js(_JS_O_BIA_HOP) or []
        if not o[0].get("co_anh"):                   # ô 1 phải là bìa ĐANG chạy — Studio thường điền sẵn
            if not kh.get("anh_a"):
                return dict(ra, ket=sm.KV_LOI, ly_do="ô 1 trống mà không có bìa A (i.ytimg.com) để tải")
            ra["o1"] = _dat_tep_o(S, o[0], sm.tep_tai_len(kh["anh_a"], os.path.join(thu_muc_so(), "tai-len")))
            _cho(S, lambda: _so_o_co_anh(S) >= 1, 40, 2)
        for i, duong in enumerate(tep, 1):
            truoc = _so_o_co_anh(S)
            o = [x for x in (S.js(_JS_O_BIA_HOP) or []) if not x.get("co_anh")]
            if not o:
                break
            cach = _dat_tep_o(S, o[0], duong)
            ok = _cho(S, lambda: _so_o_co_anh(S) > truoc, 60, 2)
            ghi("   {0}: ô bìa {1} ← {2} ({3}) {4}".format(vid, i + 1, os.path.basename(duong), cach, "ĐÃ HIỆN" if ok else "CHƯA HIỆN"))
            if not ok:
                loi = _gon((S.js(_JS_HOP_TEST) or {}).get("chu"), 200)
                return dict(ra, ket=sm.KV_LOI, ly_do="tải bìa {0} vào hộp không hiện ({1})".format(os.path.basename(duong), loi))
        so_bia = _so_o_co_anh(S)
        ra["so_bia"] = so_bia
        ra["anh_hop"] = S.st.ghi_bang_chung("test-hop-" + vid).get("anh") or ""
        if so_bia != 1 + len(tep):
            return dict(ra, ket=sm.KV_LOI, ly_do="hộp có {0} bìa, mong {1}".format(so_bia, 1 + len(tep)))
        nut_tl = _cho(S, lambda: (lambda k: k if k and not k.get("tat") else None)(_tim_khoa(S, "ab_thiet_lap"))
                      or _nut_hop(S, RE_NUT_THIET_LAP), 20)
        if not nut_tl:
            return dict(ra, ket=sm.KV_LOI, ly_do="nút «Thiết lập thử nghiệm» vẫn tắt: " +
                        _gon((S.js(_JS_HOP_TEST) or {}).get("chu"), 200))
        if khong_luu:
            return dict(ra, ket="khong_luu", ly_do="đã điền {0} bìa, «Thiết lập thử nghiệm» bật — KHÔNG lưu".format(so_bia))
        if nut_tl.get("rect"):
            S.st.bam(nut_tl)
        else:
            S.st._bam_diem(round(nut_tl["x"], 1), round(nut_tl["y"], 1))  # noqa: SLF001
        ghi("   {0}: đã bấm «Thiết lập thử nghiệm» ({1} bìa)".format(vid, so_bia))
        S.ngu(4)
        for _ in range(2):                           # hộp xác nhận (nếu có) — nút đồng ý của CHÍNH hộp đang mở
            if not S.js(_JS_HOP_TEST):
                break
            xn = _nut_hop(S, RE_NUT_XAC_NHAN)
            if not xn or re.search(RE_CHIP_BIA + "|" + RE_CHIP_TIEU_DE, xn.get("chu") or "", re.I):
                break
            S.st._bam_diem(round(xn["x"], 1), round(xn["y"], 1))  # noqa: SLF001
            S.ngu(4)
        if not _cho(S, lambda: not S.js(_JS_HOP_TEST), 45, 2):
            return dict(ra, ket=sm.KV_LOI, ly_do="bấm «Thiết lập thử nghiệm» mà hộp không đóng: " +
                        _gon((S.js(_JS_HOP_TEST) or {}).get("chu"), 200))
    finally:
        try:
            if S.js(_JS_HOP_TEST):
                dong_hop_khong_luu(S, ghi)
        except Exception:  # noqa: BLE001
            pass
    ra["anh_sau_hop"] = S.st.ghi_bang_chung("test-sau-hop-" + vid).get("anh") or ""
    if not luu_dang_tat(S):                          # trang sửa còn thay đổi chưa lưu → Lưu (luồng này được phép)
        tieu_de = mdd_chuan(S.st.doc_chu("tieu_de") or "")
        if goi.get("title") and tieu_de != mdd_chuan(goi.get("title")):   # chỉ được đổi thử nghiệm — tiêu đề lệch thì bỏ
            huy_thay_doi(S, ghi)
            return dict(ra, ket=sm.KV_LOI, ly_do="trang sửa có thay đổi lạ (tiêu đề lệch) — đã huỷ, không lưu")
        S.st.bam("sua_luu", hau_dieu_kien=lambda: luu_dang_tat(S), han_hau=CHO_LUU_GIAY)
        ghi("   {0}: đã bấm Lưu trang sửa".format(vid))
        S.ngu(3)
    # ── ĐỌC LẠI: gói Studio phải có thử nghiệm, đúng số bìa (nếu gói ghi số) ──
    tn2, kb2 = {"co": False, "so_bia": None}, {}
    for lan in range(3):
        S.ngu(5 + 5 * lan)
        goi2, kb2 = doc_trang_sua(S, vid)
        tn2 = phan_tich_thu_nghiem((goi2 or {}).get("videoCreatorExperiment"))
        if tn2["co"]:
            break
    ra["anh_doc_lai"] = S.st.ghi_bang_chung("test-doc-lai-" + vid).get("anh") or ""
    ra["doc_lai"] = dict(tn2, nut=[n.get("chu") for n in kb2.get("nut") or []])
    ghi("   {0}: ĐỌC LẠI thử nghiệm {1}".format(vid, ra["doc_lai"]))
    if not tn2["co"]:
        return dict(ra, ket=sm.KV_LOI, ly_do="đọc lại: gói Studio chưa có thử nghiệm (videoCreatorExperiment rỗng)")
    if tn2["so_bia"] is not None and tn2["so_bia"] != ra["so_bia"]:
        return dict(ra, ket=sm.KV_LOI, ly_do="đọc lại: thử nghiệm có {0} bìa, mong {1}".format(tn2["so_bia"], ra["so_bia"]))
    return dict(ra, ket=sm.KV_DA_DAT, trang_thai=tn2["trang_thai"])


def tai_bia_a(goc: str, kenh: str, vid: str, ghi, tai=None) -> str:
    """Bìa A = bìa ĐANG chạy trên YouTube: `i.ytimg.com/vi/<id>/maxresdefault.jpg` (lùi hqdefault) — như
    `core.khuon_bia.anh_that`, nhưng lưu ở sổ của máy này (`vm/logs/studio-may/<K>/bia-a/`), không đụng CHANNEL/."""
    if tai is None:
        from core.khuon_bia import _tai_url as tai  # noqa: PLC0415
    dich = os.path.join(thu_muc_so(), kenh, "bia-a", "{0}.jpg".format(vid))
    for ten in ("maxresdefault", "hqdefault"):
        du = tai("https://i.ytimg.com/vi/{0}/{1}.jpg".format(vid, ten))
        if du:
            os.makedirs(os.path.dirname(dich), exist_ok=True)
            with open(dich + ".tmp", "wb") as tep:
                tep.write(du)
            os.replace(dich + ".tmp", dich)
            return dich
    ghi("   (!) không tải được bìa đang chạy của {0} từ i.ytimg.com".format(vid))
    return dich if os.path.isfile(dich) else ""


def ke_hoach_video(goc: str, kenh: str, vid: str, ghi, tai=None, cham=None) -> Dict[str, Any]:
    """Không mở Chrome: mã gói, bìa A, ứng viên B/C đã qua cổng (bản tải lên chuẩn)."""
    ma_goi = sm.ma_goi_cua_video(goc, kenh, vid)
    a = tai_bia_a(goc, kenh, vid, ghi, tai)
    hs = os.path.join(goc, "CHANNEL", kenh, "ho-so-video", "anh", ma_goi + ".jpg") if ma_goi else ""
    chon, bo = sm.ung_vien_bia(goc, kenh, ma_goi, [x for x in (a, hs) if x], cham=cham) if ma_goi else ([], [])
    tep = []
    for u in chon:
        try:
            tep.append(sm.tep_tai_len(u["tep"], os.path.join(thu_muc_so(), kenh, "tai-len")))
        except Exception as e:  # noqa: BLE001
            bo.append(dict(u, ly_do="không dựng được bản tải lên: {0}".format(str(e)[:80])))
    chon = [dict(u, tai_len=t) for u, t in zip(chon, tep)]
    ghi("   {0} ({1}): bìa A {2} · ứng viên {3} · bỏ {4}".format(
        vid, ma_goi or "?", "có" if a else "KHÔNG", [os.path.basename(u["tep"]) + " gk={0}".format(u.get("diem_gk")) for u in chon],
        ["{0}: {1}".format(os.path.basename(u["tep"]), u.get("ly_do")) for u in bo][:4]))
    return {"ma_goi": ma_goi, "anh_a": a, "chon": chon, "bo": [{k: u.get(k) for k in ("tep", "nguon", "ly_do")} for u in bo]}


def chay_test(kenh: str, ghi, thu: bool = False, khong_luu: bool = False, bo_qua_khung: bool = False,
              chi_viec: str = "", rng=None, tai=None, cham=None, phien=None) -> int:
    import datetime as _dt  # noqa: PLC0415
    goc = GOC_TOOL
    ds = _viec(goc, LOAI_TEST, kenh, chi_viec)
    if not ds:
        ghi("không có việc Thử nghiệm và so sánh của {0}".format(kenh))
        return MA_KHONG_CAN
    ghi_that = not (thu or khong_luu)
    try:
        with open(os.path.join(GOC, "logs", "cmt-dom.json"), "r", encoding="utf-8") as tep:
            so_cmt = json.load(tep)
    except (OSError, ValueError):
        so_cmt = {}
    ly = sm.thieu_tinh_nang(so_cmt, kenh, _dt.datetime.now())
    if ly and ghi_that:     # đã biết thiếu tính năng nâng cao → bỏ, không mở Chrome; mục "xác minh điện thoại" đã báo chủ
        for m in ds:
            _cap_nhat(goc, m["id"], ghi, trang_thai="bo", ket={"ly_do": ly, "luc": _bay()})
        return MA_XONG
    ke = {}
    for m in ds:
        for vid in m.get("video_ids") or []:
            if vid not in ke:
                ke[vid] = ke_hoach_video(goc, kenh, vid, ghi, tai, cham)
    can_studio = [m for m in ds if thu or any(ke[v]["chon"] for v in m.get("video_ids") or [])]
    for m in ds:
        if m not in can_studio and ghi_that:
            kv = {v: {"ket": sm.KV_KHONG_UNG_VIEN, "ma_goi": ke[v]["ma_goi"], "bo": ke[v]["bo"][:6]} for v in m["video_ids"]}
            tt, ly = sm.ket_viec_test(kv)
            _cap_nhat(goc, m["id"], ghi, trang_thai=tt, ket={"ly_do": ly, "video": kv, "luc": _bay()})
    if not can_studio:
        return MA_XONG
    dang: List[str] = []
    xong: List[str] = []

    def lam(S, md, agent):
        ra: Dict[str, Any] = {}
        for m in can_studio:
            if ghi_that:
                _cap_nhat(goc, m["id"], ghi, trang_thai="dang")
                dang.append(m["id"])
            kv: Dict[str, Dict[str, Any]] = {}
            for vid in (m.get("video_ids") or [])[:TOI_DA_VIDEO_PHIEN]:
                _kiem_dung(agent, kenh)
                kh = ke[vid]
                if not kh["chon"] and not thu:
                    kv[vid] = {"ket": sm.KV_KHONG_UNG_VIEN, "ma_goi": kh["ma_goi"], "bo": kh["bo"][:6]}
                    continue
                try:
                    kv[vid] = test_mot_video(S, vid, kh, ghi, thu=thu, khong_luu=khong_luu)
                except (DangXuat, tl.Hoan, tl.CanNguoi):
                    raise
                except Exception as e:  # noqa: BLE001 — một video hỏng: video kế vẫn làm
                    kv[vid] = {"ket": sm.KV_LOI, "ly_do": str(e)[:200]}
                    S.chup("test-loi-" + vid)
                    try:
                        dong_hop_khong_luu(S, ghi)
                        if not luu_dang_tat(S):
                            huy_thay_doi(S, ghi)
                    except Exception:  # noqa: BLE001
                        pass
                kv[vid].setdefault("ma_goi", kh["ma_goi"])
                if kv[vid].get("ket") != sm.KV_DA_DAT:      # không đặt được: không để thay đổi dở trên trang sửa
                    try:
                        if not luu_dang_tat(S):
                            huy_thay_doi(S, ghi)
                    except Exception:  # noqa: BLE001
                        pass
                if kv[vid].get("ket") == sm.KV_KHONG_QUYEN:
                    break
            tt, ly = sm.ket_viec_test(kv)
            ra[m["id"]] = {"trang_thai": tt, "ly_do": ly, "video": kv}
            if ghi_that:
                _cap_nhat(goc, m["id"], ghi, trang_thai=tt, ket={"ly_do": ly, "video": kv, "luc": _bay(),
                                                                  "tieu_de_test": any(x.get("tieu_de_test") for x in kv.values())})
                dang.remove(m["id"])
                xong.append(m["id"])
            if any(x.get("ket") == sm.KV_KHONG_QUYEN for x in kv.values()):
                for m2 in can_studio[can_studio.index(m) + 1:]:
                    if ghi_that:
                        _cap_nhat(goc, m2["id"], ghi, trang_thai="bo", ket={"ly_do": ly, "luc": _bay()})
                        xong.append(m2["id"])
                break
        return ra
    ma, r = (phien or chay_phien)(kenh, ghi, lam, "test", bo_qua_khung=bo_qua_khung, cho_luu=not thu, rng=rng)
    if ma != MA_XONG:
        _ket_phien_hong(goc, list(dang) if ma == MA_HOAN else
                        ([m["id"] for m in can_studio if m["id"] not in xong] if ghi_that else []), ma, r, ghi)
        return ma
    _ghi_json(os.path.join(thu_muc_so(), "{0}.test-compare.json".format(kenh)), {"kenh": kenh, "luc": _bay(), "thu": thu,
                                                                                  "khong_luu": khong_luu, "viec": r})
    if not ghi_that:
        return MA_XONG
    return MA_LOI if any(v.get("trang_thai") == "loi" for v in (r or {}).values()) else MA_XONG


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="Máy Studio: bộ chạy hàng việc máy có kiểu (Thử nghiệm và so sánh, sức khoẻ).")
    ap.add_argument("--kenh", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--test-compare", action="store_true", help="việc studio_test_compare của kênh")
    g.add_argument("--suc-khoe", action="store_true", help="việc studio_kiem_suc_khoe của kênh (CHỈ ĐỌC)")
    g.add_argument("--tham-do", action="store_true", help="(dev, CHỈ ĐỌC) ảnh + DOM + chữ các trang Studio")
    ap.add_argument("--video", default="", help="(--tham-do) đọc trang sửa của video này")
    ap.add_argument("--mo-hop", action="store_true", help="(--tham-do --video) mở hộp Thử nghiệm và so sánh rồi đóng, không lưu")
    ap.add_argument("--bam", action="append", default=[], help="(--tham-do --mo-hop, dev) bấm tiếp nút có chữ khớp regex trong hộp")
    ap.add_argument("--thu", action="store_true", help="(--test-compare) chỉ ĐỌC trạng thái thử nghiệm + in ứng viên, không đặt")
    ap.add_argument("--khong-luu", action="store_true", help="(--test-compare, dev) điền hộp rồi ĐÓNG không lưu")
    ap.add_argument("--viec", default="", help="chỉ việc có id này")
    ap.add_argument("--bo-qua-khung", action="store_true", help="(dev) bỏ khung cấm 02–07 + phút :55–:05")
    a = ap.parse_args(argv)
    ghi = _nhat_ky(a.kenh)
    if a.tham_do:
        ma, _kq = chay_phien(a.kenh, ghi, lambda S, md, agent: tham_do(S, md, agent, a.kenh, ghi, a.video, a.mo_hop, a.bam),
                             "tham_do", bo_qua_khung=a.bo_qua_khung)
        return ma
    if a.suc_khoe:
        return chay_suc_khoe(a.kenh, ghi, bo_qua_khung=a.bo_qua_khung, chi_viec=a.viec)
    return chay_test(a.kenh, ghi, thu=a.thu, khong_luu=a.khong_luu, bo_qua_khung=a.bo_qua_khung, chi_viec=a.viec)


if __name__ == "__main__":
    sys.exit(main())
