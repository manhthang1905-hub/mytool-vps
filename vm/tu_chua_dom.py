"""Máy đăng TỰ CHỮA bộ chọn DOM khi YouTube đổi Studio — `TuChuaDom`.

Vì sao: mỗi lần Studio đổi giao diện, MỌI bộ chọn của một khoá trong
`vm/studio-selectors.json` có thể hụt cùng lúc → đăng video đứng tới khi có
người sửa JSON. Ở đây, khi `TrangStudio.tim(khoa)` hụt HẲN (hết hạn chờ, không
bộ chọn lẫn chữ nào khớp), máy hỏi AI (ví ShopAPI) đề xuất tối đa 3 bộ chọn CSS
mới dựa trên bản đồ DOM đang hiện, rồi TỰ KIỂM từng bộ chọn ngay trên trang
trước khi nhận.

Luật an toàn:

* Chỉ ĐỌC/TÌM — bộ chữa không bấm, không gõ, không dò bằng thao tác; phần tử
  tìm được vẫn đi qua mọi kiểm của người gọi (`cam_bam`, hậu điều kiện...).
* Kiểm trên trang: khoá một phần tử → đúng 1 phần tử hiện khớp; khoá danh sách
  → ≥1; thẻ/vai trò hợp lý với loại khoá; có chữ gợi ý thì chữ/aria-label của
  phần tử phải chứa một gợi ý; phần tử cấm (`cam`) bị loại.
* Bộ chọn đã nhận ghi vào tệp RIÊNG `vm/logs/studio-selectors-tu-chua.json`
  (không bao giờ sửa `studio-selectors.json`), `doc_bo_chon()` gộp vào với ưu
  tiên cao nhất. Người sửa JSON (đổi `chon`) → bản tự chữa của khoá ấy tự bỏ.
* Hạn mức: tối đa `TOI_DA_MOI_KHOA_NGAY` lần hỏi AI mỗi khoá mỗi ngày, hỏi hụt
  thì nhớ 1 giờ không hỏi lại; tắt hẳn bằng `TL_TU_CHUA_DOM=0`.
* Bộ chọn tự chữa về sau hụt (mà gốc khớp lại, hoặc hụt hết) → bỏ, lùi về gốc.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata

GOC = os.path.dirname(os.path.abspath(__file__))
THU_MUC_LOG = os.path.join(GOC, "logs")
DUONG_TU_CHUA = os.path.join(THU_MUC_LOG, "studio-selectors-tu-chua.json")
DUONG_DEM = os.path.join(THU_MUC_LOG, "tu-chua-dom-dem.json")
DUONG_NHAT_KY = os.path.join(THU_MUC_LOG, "tu-chua-dom.jsonl")

BIEN_TAT = "TL_TU_CHUA_DOM"
#: Lần hỏi AI tối đa cho MỘT khoá trong một ngày (mọi tiến trình cộng dồn).
TOI_DA_MOI_KHOA_NGAY = 3
#: Lần hỏi AI tối đa trong một phiên (một tab) — chặn chuỗi lỗi kéo dài phiên.
TOI_DA_MOI_PHIEN = 6
#: Hỏi hụt → không hỏi lại khoá ấy trong chừng này giây.
HAN_AM = 3600
#: Chỉ chữa khi người gọi CHỜ thật (≥ chừng này giây): `co()`/`cho_mat()` dò
#: han=0 để biết phần tử VẮNG — chữa ở đó là sai nghĩa.
NGUONG_HAN = 3.0
#: Số phần tử của bản đồ DOM gửi AI (đã xếp theo độ liên quan).
SO_UNG_VIEN = 250
TOI_DA_UNG_VIEN_AI = 3
DAI_BO_CHON = 300

#: Khoá chỉ dùng để DÒ TRẠNG THÁI (vắng là bình thường) — không bao giờ chữa.
#: Thêm `"khong_tu_chua": true` vào khoá trong JSON để loại khoá khác.
KHOA_KHONG_TU_CHUA = frozenset((
    "the_da_co", "hop_da_xong", "danh_sach_trong", "tien_do", "nut_phan_hoi",
    "nut_thu_lai", "hop_con_huy", "mhkt_mau_video_dk", "mhkt_phan_tu", "the_muc_ten",
    "xem_bl_tat", "xem_huy_hieu_ghim", "xem_hop_xac_minh", "xem_hop_xac_minh_huy",
    "xem_menu_ghim", "sc_trong", "sc_bo_loc_phan_hoi", "o_tep_video", "sua_bia_input",
    "the_moc_o",
))
#: Khoá DANH SÁCH (nhiều phần tử cùng loại): chấp nhận ≥1 khớp.
KHOA_DANH_SACH = frozenset((
    "playlist_muc", "playlist_ten", "the_da_co", "mhkt_mau", "mhkt_chon_video",
    "mhkt_video_dau", "mhkt_phan_tu", "the_chon_ds", "the_chon_video", "the_muc_ten",
    "the_moc", "the_dau_phat", "the_loai_dau", "hang_video", "hang_tieu_de", "hang_che_do",
    "hang_ngay", "hang_sua_nhap", "xem_luong", "xem_noi_dung", "xem_tac_gia", "sc_luong",
    "sc_noi_dung", "sc_tac_gia", "sc_nut_tra_loi", "xem_menu",
))
#: Mục đích ngắn của các khoá chính (cho AI hiểu cần tìm gì).
MO_TA_KHOA = {
    "hop_upload": "hộp thoại tải video lên (khung chính của luồng đăng)",
    "nut_chon_tep": "nút 'Chọn tệp' trong hộp tải lên",
    "link_video": "đường dẫn youtu.be/<id> của video vừa tải trong hộp tải lên",
    "tieu_de": "ô soạn TIÊU ĐỀ video (contenteditable)",
    "mo_ta": "ô soạn MÔ TẢ video (contenteditable)",
    "nut_thumbnail": "nút tải ảnh thu nhỏ (bìa) lên",
    "playlist_mo": "nút mở danh sách chọn playlist",
    "playlist_muc": "ô tick của từng playlist trong hộp chọn playlist",
    "playlist_xong": "nút 'Xong' của hộp chọn playlist",
    "khong_tre_em": "nút radio 'Không, nội dung này không dành cho trẻ em'",
    "hien_them": "nút 'Hiện thêm' mở phần cài đặt nâng cao",
    "ai_co": "nút radio 'Có' cho câu hỏi nội dung bị thay đổi/tổng hợp (AI)",
    "o_the": "ô nhập THẺ (tags) của video",
    "nut_tiep": "nút 'Tiếp' sang bước sau của hộp tải lên",
    "buoc_hien_thi": "bước 'Chế độ hiển thị' trên thanh bước của hộp tải lên",
    "len_lich_mo": "nút mở phần 'Lên lịch'",
    "o_ngay_mo": "nút mở bộ chọn ngày lên lịch",
    "o_ngay": "ô nhập NGÀY lên lịch",
    "o_gio": "ô nhập GIỜ lên lịch",
    "nut_xong": "nút cuối 'Lên lịch'/'Lưu' của hộp tải lên",
    "dong_hop_da_xong": "nút đóng hộp báo đã tải xong",
    "dong_hop_upload": "nút đóng (X) hộp tải lên",
    "hien_thi_trang_sua": "khung 'Chế độ hiển thị' trên trang sửa video",
    "hang_video": "từng hàng video trong danh sách nội dung của kênh",
}

_THE_CAM = frozenset(("html", "body", "head", "script", "style", "ytcp-app", "ytd-app", "meta", "link"))
_THE_KHOI_TRON = frozenset((
    "div", "span", "p", "li", "ul", "ol", "section", "img", "svg", "path", "label", "table",
    "tr", "td", "h1", "h2", "h3", "h4", "h5", "h6", "iron-icon", "yt-icon", "tp-yt-iron-icon",
))
_VAI_NUT = frozenset(("button", "radio", "checkbox", "menuitem", "tab", "option", "link", "switch",
                      "menuitemcheckbox", "menuitemradio", "combobox"))
_TU_BO = frozenset(("div", "span", "input", "button", "type", "file", "aria", "label", "href", "role",
                    "true", "false", "name", "class", "text", "contenteditable"))


def bat() -> bool:
    """Công tắc chung: `TL_TU_CHUA_DOM=0|false|off|khong` → tắt hẳn (không chữa,
    không gộp tệp tự chữa — Studio chạy đúng như JSON gốc)."""
    return str(os.environ.get(BIEN_TAT, "1")).strip().lower() not in ("0", "false", "off", "khong", "no")


def _chuan(s) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s or ""))).strip()


def _gon(s, n: int = 200) -> str:
    s = _chuan(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def _doc_json(duong: str) -> dict:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ghi_json(duong: str, d: dict) -> None:
    """Ghi nguyên tử (tệp tạm + os.replace) — tiến trình khác đọc giữa chừng không vỡ."""
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(d, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def bo_chon_hop_le(s) -> bool:
    """Cùng luật cú pháp với `cdp_studio.kiem_bo_chon` (ngoặc/nháy cân) + giới hạn độ dài."""
    if not isinstance(s, str) or not s.strip() or len(s) > DAI_BO_CHON:
        return False
    if s.count("[") != s.count("]") or s.count("(") != s.count(")") or s.count("'") % 2 or s.count('"') % 2:
        return False
    return not any(x in s.lower() for x in ("javascript:", "<", "{", "}"))


# ── tệp tự chữa (gộp lúc nạp) ────────────────────────────────────────────

def doc_tu_chua(duong: str = None) -> dict:
    return _doc_json(duong or DUONG_TU_CHUA)


def ap_tu_chua(bo: dict, tu_chua: dict, kiem=None) -> dict:
    """Gộp bản tự chữa vào bộ chọn: `chon` mới đứng ĐẦU (ưu tiên cao nhất), dấu
    `_tu_chua` ghi những bộ chọn nào là tự chữa (để biết mà bỏ khi hụt). Bỏ qua
    khoá mà người đã sửa `chon` trong JSON kể từ lúc chữa (`chon_cu` khác). Gộp
    xong mà `kiem` (kiem_bo_chon) báo thêm lỗi → trả bộ gốc nguyên vẹn."""
    if not bat() or not isinstance(tu_chua, dict) or not tu_chua or not isinstance(bo, dict):
        return bo
    pt = dict(bo.get("phan_tu") or {})
    doi = False
    for k, m in tu_chua.items():
        spec = pt.get(k)
        if not isinstance(spec, dict) or not isinstance(m, dict) or spec.get("khong_tu_chua"):
            continue
        moi = [s for s in (m.get("chon") or []) if bo_chon_hop_le(s)]
        if not moi:
            continue
        goc = list(spec.get("chon") or [])
        cu = m.get("chon_cu")
        if isinstance(cu, list) and cu != goc:
            continue
        pt[k] = dict(spec, chon=moi + [s for s in goc if s not in moi], _tu_chua=moi)
        doi = True
    if not doi:
        return bo
    ra = dict(bo, phan_tu=pt)
    if kiem is not None:
        try:
            if len(kiem(ra)) > len(kiem(bo)):
                return bo
        except Exception:  # noqa: BLE001 — kiểm hỏng thì giữ bộ gốc cho chắc
            return bo
    return ra


# ── bản đồ DOM gọn cho AI ────────────────────────────────────────────────

def _token_cu(spec: dict) -> set:
    ra = set()
    for s in spec.get("chon") or []:
        for t in re.findall(r"[A-Za-z][\w-]{2,}", str(s)):
            t = t.lower()
            if t not in _TU_BO:
                ra.add(t)
    return ra


def rut_ban_do(ban_do: list, spec: dict, toi_da: int = SO_UNG_VIEN) -> list:
    """Chọn `toi_da` phần tử liên quan nhất (chữ khớp gợi ý > trùng tên thẻ/id/
    class với bộ chọn cũ > phần tử tương tác), giữ thứ tự DOM."""
    goi_y = [_chuan(c).lower() for c in (spec.get("chu") or []) if _chuan(c)]
    token = _token_cu(spec)
    cham = []
    for i, e in enumerate(ban_do or []):
        if not isinstance(e, dict):
            continue
        chu = (_chuan(e.get("chu")) + " " + _chuan(e.get("aria"))).lower()
        ten = " ".join(str(e.get(x) or "") for x in ("tag", "id", "cls", "name")).lower()
        d = 0
        if goi_y and any(g in chu for g in goi_y):
            d += 5
        if token and any(t in ten for t in token):
            d += 3
        if e.get("tag") in ("button", "input", "textarea", "a") or e.get("role"):
            d += 1
        cham.append((-d, i, e))
    cham.sort(key=lambda x: (x[0], x[1]))
    chon = sorted(cham[:toi_da], key=lambda x: x[1])
    return [e for _d, _i, e in chon]


def dong_ban_do(e: dict) -> str:
    s = str(e.get("tag") or "?")
    if e.get("id"):
        s += "#" + str(e["id"])
    cls = _chuan(e.get("cls"))
    if cls:
        s += "." + ".".join(cls.split(" ")[:3])
    for k in ("role", "name"):
        if e.get(k):
            s += " {0}={1}".format(k, e[k])
    if e.get("aria"):
        s += ' aria="{0}"'.format(_gon(e["aria"], 60))
    if e.get("chu"):
        s += ' chu="{0}"'.format(_gon(e["chu"], 50))
    if e.get("href"):
        s += " href=" + _gon(e["href"], 60)
    if e.get("tat"):
        s += " (tắt)"
    if e.get("sau"):
        s += " (s)"
    r = e.get("rect")
    if isinstance(r, list) and len(r) == 4:
        s += " @{0},{1},{2}x{3}".format(*r)
    return s


def loai_khoa(khoa: str) -> str:
    """'nhap' (ô gõ) | 'lien_ket' | 'nut' | 'khac' — đoán từ tên khoá để kiểm
    thẻ có hợp lý không (vd khoá ô gõ mà AI chỉ vào một <span> là sai)."""
    k = str(khoa)
    if k.startswith("link_"):
        return "lien_ket"
    if k.startswith(("nut_", "dong_")) or k.endswith((
            "_mo", "_xong", "_luu", "_them", "_nhap", "_huy", "_gui", "_tiep", "_tiep_tuc",
            "_xac_nhan", "_doi", "_tai", "_tai_tep", "_menu", "_tra_loi")) \
            or k in ("hien_them", "khong_tre_em", "ai_co", "nut_tiep", "buoc_hien_thi"):
        return "nut"
    if k in ("tieu_de", "mo_ta") or k.startswith("o_") or "_o_" in k or k.endswith(("_o", "_tim_video", "_input")):
        return "nhap"
    return "khac"


def mo_ta_khoa(khoa: str, spec: dict) -> str:
    ra = MO_TA_KHOA.get(khoa) or "phần tử '{0}' của YouTube Studio".format(str(khoa).replace("_", " "))
    if spec.get("ghi_chu"):
        ra += " — ghi chú: " + _gon(spec["ghi_chu"], 200)
    return ra


def de_bai(khoa: str, spec: dict, ban_do: list) -> str:
    cu = [s for s in (spec.get("chon") or []) if s not in (spec.get("_tu_chua") or [])]
    nhieu = khoa in KHOA_DANH_SACH
    dong = "\n".join(dong_ban_do(e) for e in ban_do)
    return (
        "Bạn sửa bộ chọn CSS cho trang YouTube Studio (giao diện vừa đổi nên bộ chọn cũ hụt).\n"
        "Khoá: {k}\nMục đích: {mt}\nBộ chọn cũ (đều KHÔNG còn khớp): {cu}\n"
        "Chữ / aria-label gợi ý: {chu}\nCần: {can}\n\n"
        "Bản đồ DOM — các phần tử ĐANG HIỆN, mỗi dòng: tag#id.class role= name= aria=\"\" chu=\"\" "
        "@x,y,rộngxcao; (s) = nằm trong shadow DOM; (tắt) = đang vô hiệu:\n{dong}\n\n"
        "Lưu ý: mỗi bộ chọn được chạy bằng querySelectorAll trên document VÀ trên từng shadowRoot "
        "riêng (một bộ chọn KHÔNG xuyên ranh giới shadow) — ưu tiên tag/id/thuộc tính của chính phần "
        "tử, chuỗi tổ tiên ngắn. Phần tử phải hiện duy nhất (trừ khi cần danh sách).\n"
        "Nếu phần tử KHÔNG có trên trang (trang đang ở trạng thái khác) thì trả \"chon\": [].\n"
        "Trả DUY NHẤT một JSON: {{\"chon\": [\"...\", \"...\"], \"ly_do\": \"ngắn\"}} — tối đa {n} bộ chọn, "
        "tốt nhất trước."
    ).format(k=khoa, mt=mo_ta_khoa(khoa, spec), cu=json.dumps(cu, ensure_ascii=False),
             chu=json.dumps(list(spec.get("chu") or []), ensure_ascii=False) if spec.get("chu") else "(không có)",
             can="DANH SÁCH nhiều phần tử cùng loại (≥1)" if nhieu else "MỘT phần tử duy nhất",
             dong=dong, n=TOI_DA_UNG_VIEN_AI)


def doc_tra_loi(tho: str) -> tuple:
    """(danh sách bộ chọn, lý do) từ trả lời AI; hỏng → ([], '')."""
    s = str(tho or "")
    for m in re.finditer(r"\{.*\}", s, re.S):
        try:
            d = json.loads(m.group(0))
        except ValueError:
            continue
        if isinstance(d, dict) and isinstance(d.get("chon"), list):
            ra = []
            for x in d["chon"]:
                x = str(x or "").strip() if isinstance(x, str) else ""
                if x and x not in ra:
                    ra.append(x)
            return ra[:TOI_DA_UNG_VIEN_AI], _gon(d.get("ly_do"), 200)
    return [], ""


# ── AI mặc định ──────────────────────────────────────────────────────────

def goi_ai_mac_dinh(ghi=None):
    """Hàm `goi_ai(prompt) -> str` qua ví ShopAPI của tool cùng máy
    (`core.giam_doc.quan_ly.goi_chat_that`); không có tool / van ví chặn /
    lỗi nạp → None (bộ chữa thành no-op)."""
    goc_tool = os.path.dirname(GOC)
    try:
        if goc_tool not in sys.path:
            sys.path.insert(0, goc_tool)
        from core.giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415
        g = goi_chat_that(goc_tool, ghi)
    except Exception as loi:  # noqa: BLE001 — không có tool/ví thì thôi chữa
        if ghi:
            ghi("tự chữa DOM: không nạp được AI ({0})".format(_gon(loi, 120)))
        return None
    if g is None:
        return None
    return lambda p: g(p, toi_da_token=800)


# ── bộ chữa ──────────────────────────────────────────────────────────────

class TuChuaDom:
    """Chữa một khoá hụt trên một `TrangStudio` (chỉ dùng `_js`, `ban_do`,
    `nhat_ky` của trang). Mọi lỗi bên trong đều nuốt — bộ chữa không bao giờ
    làm máy đăng hỏng thêm."""

    def __init__(self, goi_ai=None, duong_tu_chua: str = None, duong_dem: str = None,
                 duong_nhat_ky: str = None, bay_gio=None, toi_da_ngay: int = TOI_DA_MOI_KHOA_NGAY,
                 toi_da_phien: int = TOI_DA_MOI_PHIEN, han_am: float = HAN_AM):
        self._goi_ai = goi_ai
        self._da_nap_ai = goi_ai is not None
        self.duong_tu_chua = duong_tu_chua or DUONG_TU_CHUA
        self.duong_dem = duong_dem or DUONG_DEM
        self.duong_nhat_ky = duong_nhat_ky or DUONG_NHAT_KY
        self.bay_gio = bay_gio or time.time
        self.toi_da_ngay = int(toi_da_ngay)
        self.toi_da_phien = int(toi_da_phien)
        self.han_am = float(han_am)
        self.so_lan_phien = 0
        self._khong_ai = False

    # — sổ đếm / nhật ký —
    def _ngay(self) -> str:
        return time.strftime("%Y-%m-%d", time.localtime(self.bay_gio()))

    def _doc_dem(self) -> dict:
        d = _doc_json(self.duong_dem)
        if d.get("ngay") != self._ngay():
            # ngày mới: đếm lại từ 0, nhưng giữ hạn âm còn hiệu lực
            giu = {k: {"lan": 0, "am_den": m.get("am_den", 0)}
                   for k, m in (d.get("khoa") or {}).items()
                   if isinstance(m, dict) and float(m.get("am_den") or 0) > self.bay_gio()}
            d = {"ngay": self._ngay(), "khoa": giu}
        d.setdefault("khoa", {})
        return d

    def _ghi_nhat_ky(self, khoa: str, ket: str, chon: str = "", ly_do: str = "") -> None:
        try:
            os.makedirs(os.path.dirname(self.duong_nhat_ky) or ".", exist_ok=True)
            with open(self.duong_nhat_ky, "a", encoding="utf-8") as tep:
                tep.write(json.dumps({
                    "luc": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.bay_gio())),
                    "khoa": khoa, "ket": ket, "chon": _gon(chon, DAI_BO_CHON), "ly_do": _gon(ly_do, 200),
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def ly_do_khong_chua(self, khoa: str, spec: dict) -> str:
        """'' nếu được phép hỏi AI cho khoá này lúc này; không thì lý do."""
        if not bat():
            return "đã tắt ({0}=0)".format(BIEN_TAT)
        if khoa in KHOA_KHONG_TU_CHUA or spec.get("khong_tu_chua") or spec.get("an"):
            return "khoá dò trạng thái / phần tử ẩn"
        if self._khong_ai:
            return "không có AI"
        if self.so_lan_phien >= self.toi_da_phien:
            return "hết hạn mức phiên ({0})".format(self.toi_da_phien)
        m = self._doc_dem()["khoa"].get(khoa) or {}
        if float(m.get("am_den") or 0) > self.bay_gio():
            return "vừa hỏi hụt — chờ hạn âm"
        if int(m.get("lan") or 0) >= self.toi_da_ngay:
            return "hết hạn mức ngày ({0}/khoá)".format(self.toi_da_ngay)
        return ""

    def _dem_lan(self, khoa: str, am: bool = False) -> None:
        try:
            d = self._doc_dem()
            m = d["khoa"].setdefault(khoa, {"lan": 0, "am_den": 0})
            if am:
                m["am_den"] = self.bay_gio() + self.han_am
            else:
                m["lan"] = int(m.get("lan") or 0) + 1
            _ghi_json(self.duong_dem, d)
        except OSError:
            pass

    def _ai(self, ghi):
        if not self._da_nap_ai:
            self._da_nap_ai = True
            self._goi_ai = goi_ai_mac_dinh(ghi)
        return self._goi_ai

    # — kiểm ứng viên trên trang —
    def kiem_ung_vien(self, trang, khoa: str, spec: dict, sel: str) -> str:
        """'' nếu `sel` đạt; không thì lý do loại (đếm khớp, thẻ, chữ, cấm)."""
        if not bo_chon_hop_le(sel):
            return "cú pháp"
        if sel in (spec.get("chon") or []):
            return "trùng bộ chọn cũ (đã hụt)"
        try:
            kq = trang._js("tim", {"chon": [sel], "chu": [], "an": False}, {"cho_tat": True})
        except Exception as loi:  # noqa: BLE001
            return "lỗi JS: {0}".format(_gon(loi, 80))
        if not kq or not kq.get("khop"):
            return "khớp 0"
        so = int(kq.get("so") or 0)
        if khoa in KHOA_DANH_SACH:
            if so < 1:
                return "khớp 0"
        elif so != 1:
            return "khớp {0} (cần đúng 1)".format(so)
        if kq.get("cam"):
            return "phần tử cấm ({0})".format(_gon(kq["cam"], 60))
        tag = str(kq.get("tag") or "").lower()
        if tag in _THE_CAM:
            return "thẻ {0} không hợp lý".format(tag)
        pid = kq.get("id")

        def tt(ten):
            try:
                return str(trang._js("thuocTinh", pid, ten) or "")
            except Exception:  # noqa: BLE001
                return ""

        role = tt("role").lower()
        loai = loai_khoa(khoa)
        if loai == "nhap":
            if tag not in ("input", "textarea") and tt("contenteditable").lower() != "true" and role != "textbox":
                return "khoá ô gõ mà phần tử là {0}".format(tag)
        elif loai == "lien_ket":
            if tag != "a" and not tt("href"):
                return "khoá liên kết mà phần tử không có href"
        elif loai == "nut":
            if tag in _THE_KHOI_TRON and role not in _VAI_NUT:
                return "khoá nút mà phần tử là {0} không vai trò".format(tag)
        goi_y = [_chuan(c).lower() for c in (spec.get("chu") or []) if _chuan(c)]
        if goi_y:
            try:
                chu = _chuan(trang._js("chu", pid))[:200].lower()
            except Exception:  # noqa: BLE001
                chu = ""
            aria = _chuan(tt("aria-label")).lower()
            if not any(g in chu or g in aria for g in goi_y):
                return "chữ không khớp gợi ý ({0})".format(_gon(chu or aria, 60))
        return ""

    # — chữa —
    def chua(self, trang, khoa: str, spec: dict):
        """Hỏi AI + kiểm; đạt → ghi tệp tự chữa, trả [bộ chọn]; không → None."""
        ghi = getattr(trang, "nhat_ky", None) or (lambda _s: None)
        ly = self.ly_do_khong_chua(khoa, spec)
        if ly:
            return None
        try:
            bd = trang.ban_do(1500) or []
        except Exception:  # noqa: BLE001
            bd = []
        if not bd:
            return None
        goi = self._ai(ghi)
        if goi is None:
            self._khong_ai = True
            ghi("TU CHUA {0}: không có AI (van ví/cấu hình) — bỏ qua".format(khoa))
            return None
        self.so_lan_phien += 1
        self._dem_lan(khoa)
        try:
            tho = goi(de_bai(khoa, spec, rut_ban_do(bd, spec)))
        except Exception as loi:  # noqa: BLE001
            ghi("TU CHUA {0}: gọi AI lỗi: {1}".format(khoa, _gon(loi, 120)))
            self._ghi_nhat_ky(khoa, "loi_ai", "", str(loi))
            self._dem_lan(khoa, am=True)
            return None
        ung, ly_do_ai = doc_tra_loi(tho)
        loai = []
        for sel in ung:
            ly = self.kiem_ung_vien(trang, khoa, spec, sel)
            if not ly:
                self._luu(khoa, spec, sel, ly_do_ai)
                ghi("TU CHUA {0}: nhận bộ chọn mới {1!r} — {2}".format(khoa, sel, ly_do_ai))
                self._ghi_nhat_ky(khoa, "chua", sel, ly_do_ai)
                return [sel]
            loai.append("{0} → {1}".format(_gon(sel, 80), ly))
            self._ghi_nhat_ky(khoa, "loai", sel, ly)
        tom = "; ".join(loai) or "AI không đề xuất ({0})".format(ly_do_ai or "trả lời rỗng/không đọc được")
        ghi("TU CHUA {0}: không nhận ứng viên nào — {1}".format(khoa, _gon(tom, 200)))
        self._ghi_nhat_ky(khoa, "khong", "", tom)
        self._dem_lan(khoa, am=True)
        return None

    def _luu(self, khoa: str, spec: dict, sel: str, ly_do: str) -> None:
        d = doc_tu_chua(self.duong_tu_chua)
        tc = list(spec.get("_tu_chua") or [])
        d[khoa] = {"chon": [sel], "luc": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.bay_gio())),
                   "ly_do": _gon(ly_do, 200),
                   "chon_cu": [s for s in (spec.get("chon") or []) if s not in tc]}
        try:
            _ghi_json(self.duong_tu_chua, d)
        except OSError:
            pass

    def bo(self, khoa: str, ly_do: str, ghi=None) -> None:
        """Bỏ bản tự chữa của `khoa` khỏi tệp (bộ chọn tự chữa đã hụt)."""
        d = doc_tu_chua(self.duong_tu_chua)
        cu = d.pop(khoa, None)
        if cu is None:
            return
        try:
            _ghi_json(self.duong_tu_chua, d)
        except OSError:
            pass
        sel = ", ".join(str(s) for s in (cu.get("chon") or [])) if isinstance(cu, dict) else ""
        if ghi:
            ghi("TU CHUA {0}: bỏ bộ chọn tự chữa {1!r} — {2}".format(khoa, sel, ly_do))
        self._ghi_nhat_ky(khoa, "bo", sel, ly_do)
