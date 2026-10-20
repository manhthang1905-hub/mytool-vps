"""TỰ KIỂM KẾT QUẢ (17/10/2026) — mọi việc máy tự làm đều có KỲ VỌNG + HẠN; quá hạn thì đọc lại từ NGUỒN THẬT.

═══ VÌ SAO ═══ Chủ 17/10: *"nhiều ngày mày giám sát, giờ nên xem lại logic để mọi thứ hoạt động auto, tự fix, tự hoàn
thiện"*. Những ngày qua người giám sát phải tự kiểm: đổi bìa xếp hàng đêm có lên YouTube không, thử nghiệm A/B có
STARTED không, danh sách phát có đủ video không (bộ đọc từng báo 0), video hôm nay có công khai không, bộ não / giấc ngủ
/ skill có chạy không, máy có giữ nhịp 1 video/ngày/kênh không. Tệp này làm đúng việc ấy bằng mã.

═══ KỲ VỌNG (suy từ sổ của chính bộ chạy — không phải nối vào từng bộ chạy) ═══
  dang       video hẹn lịch (`vm/logs/so-video-id.json` `lich`) → oEmbed công khai sau giờ hẹn + 1 giờ
  doi_bia    hàng sửa (`vm/logs/hang-sua.json`, bước bia/doi_bia `xong`) → bìa `i.ytimg.com` TRÙNG vân tay (dHash 256
             bit) tệp đã xếp (lệch ≤ 20 đạt, ≥ 40 hỏng, giữa = chưa chắc — kiểm lại); mục `cho` quá 30 giờ = trễ
  tieu_de    hàng sửa bước tieu_de `xong` → tiêu đề oEmbed = tiêu đề đã đổi (NFKC; video đang A/B thì bỏ)
  ab         việc máy `studio_test_compare`/`studio_ab_tieu_de` (`giam_doc.doc_viec_may_kieu`): `xong`+`da_dat` phải có
             đọc lại STARTED; còn mở quá 36 giờ = đói suất
  dsp        danh sách phát (`nghien-cuu/danh-sach-phat.json` `da_them`) → trang danh sách phát CÔNG KHAI có đủ video
  ghim       video lên sóng 6–72 giờ → `vm/logs/cmt-dom.json` `da-ghim` (kênh chờ xác minh điện thoại = việc người)
  nao        phiên sáng hôm nay, giấc ngủ ≤ 30 giờ, sổ skill có dòng trong 26 giờ
  van_hanh   `workspace/van-hanh/trang-thai.json` tươi ≤ 20 phút và mọi thành phần sống
  nhip       kênh tự chạy: sau 21:00 phải có video hẹn cho ngày mai; 3 ngày qua ngày nào cũng có video lên sóng;
             mỗi ngày trống một mục `nhip:khe` kèm NGUYÊN NHÂN (xếp lịch muộn / gói bị giữ / tải hỏng / thiếu gói)
API `ghi_ky_vong(goc, loai, kenh, khoa, viec, han, ...)` cho bộ chạy nào muốn khai thẳng kỳ vọng của mình.

═══ HỎNG THÌ ═══ (1) thử lại qua ĐÚNG bộ chạy, tối đa `SO_THU_LAI` lần: mở lại mục hàng sửa (máy DOM `--sua-video`),
mở lại việc máy (D13), bỏ video thiếu khỏi `da_them` (D15 thêm lại), bật lại lượt canh vận hành, chạy lại giấc ngủ não;
(2) hết lượt thử → phân loại nguyên nhân từ log (`core.loi_lap_lai.SO_TAY`); (3) lớp máy tự sửa → sổ tay sửa
(`loi_lap_lai.chay_so_tay`, chạy đầu mỗi lượt); (4) còn lại → MỘT báo động gộp mỗi ngày (`core.bao_dong`) + dòng
`workspace/loi-chay-max.md` + sự kiện não bộ phận. Việc CHỈ người làm được → "Việc của bạn".

Báo cáo ngày `workspace/tu-kiem/<ngày>.json` (ghi lại mỗi lượt), sổ trạng thái `workspace/tu-kiem/so.json`.
Lịch: gác tổng mỗi 15 phút (`nhip`). Không mở Chrome, không xoá gì trên YouTube, không bật công tắc tiền nào.

    python -X utf8 -m core.tu_kiem [--thu] [--goc G]     một lượt (--thu: chỉ đọc + in, không thử lại / sửa / ghi)
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import re
import sys
import time
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

DAT, HONG, CHO, TU_SUA, MO, THU_LAI = "dat", "hong", "cho", "tu_sua", "mo", "thu_lai"
NHAN = {DAT: "đạt", HONG: "hỏng", CHO: "chờ", TU_SUA: "máy đã tự sửa", MO: "còn mở", THU_LAI: "đang thử lại"}
SO_THU_LAI = 2
LECH_DAT, LECH_HONG = 20, 40
GIO_TRE_HANG_SUA, GIO_TRE_VIEC_MAY = 30.0, 36.0
GIO_SAU_LICH = 1.0
NGAY_XEM_LAI = 7
PHUT_KIEM_LAI = 60.0
TOI_DA_MANG_LUOT = 40
PHUT_VAN_HANH_CU = 20.0
GIO_NGU_CU, GIO_SO_SKILL_CU = 30.0, 26.0
GIO_NHIP_TOI = 21
THU_MUC = ("workspace", "tu-kiem")

Tai = Callable[[str], Tuple[int, bytes]]


# ── tiện ích ───────────────────────────────────────────────────────────────────

def _json(*phan: str) -> Any:
    try:
        with io.open(os.path.join(*phan), encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)


def _thu_muc(goc: str) -> str:
    return os.path.join(goc, *THU_MUC)


def _gio(chu: Any) -> Optional[_dt.datetime]:
    s = str(chu or "").strip()
    for dang in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(s[:19] if "T" in s or s[:4].isdigit() else s, dang)
        except ValueError:
            continue
    return None


def _iso(t: Optional[_dt.datetime]) -> str:
    return t.isoformat(timespec="minutes") if t else ""


def chuan(chu: Any) -> str:
    """So tiêu đề: NFKC, bỏ khoảng trắng."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(chu or "")))


def tai_that(url: str) -> Tuple[int, bytes]:
    """GET công khai (HTTPS) → (mã HTTP, thân). Lỗi mạng → (0, b'')."""
    import urllib.error  # noqa: PLC0415
    try:
        from .mang_an_toan import mo_url  # noqa: PLC0415
        with mo_url(url, cho=15, headers={"Accept-Language": "ja,en;q=0.8"}) as ph:
            return int(getattr(ph, "status", 200) or 200), ph.read()
    except urllib.error.HTTPError as loi:
        return int(loi.code or 0), b""
    except Exception:  # noqa: BLE001
        return 0, b""


def van_tay(du: Any) -> Optional[List[int]]:
    """dHash 16×16 (256 bit) của ảnh (đường dẫn hoặc bytes). Ảnh 4:3 có viền (hqdefault) → cắt 16:9 giữa."""
    try:
        from PIL import Image  # noqa: PLC0415
        im = Image.open(io.BytesIO(du) if isinstance(du, (bytes, bytearray)) else du)
        w, h = im.size
        if h and abs(w / h - 4 / 3) < 0.05:
            ch = int(w * 9 / 16)
            im = im.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
        im = im.convert("L").resize((17, 16))
        p = list(im.tobytes())
        return [1 if p[r * 17 + c] > p[r * 17 + c + 1] else 0 for r in range(16) for c in range(16)]
    except Exception:  # noqa: BLE001
        return None


def lech(a: Optional[List[int]], b: Optional[List[int]]) -> Optional[int]:
    if not a or not b or len(a) != len(b):
        return None
    return sum(x != y for x, y in zip(a, b))


class BoiCanh:
    """Một lượt: gốc, giờ, hàm tải (mock được), cờ thử, sổ trạng thái, ngân sách mạng."""

    def __init__(self, goc: str, *, bay: Optional[_dt.datetime] = None, tai: Optional[Tai] = None, thu: bool = False,
                 kenh_ds: Optional[List[str]] = None, so: Optional[Dict[str, Any]] = None):
        self.goc, self.bay, self.thu = goc, bay or _dt.datetime.now(), thu
        self._tai = tai or tai_that
        self.so = so if so is not None else doc_so(goc)
        self.mang = 0
        if kenh_ds is None:
            try:
                from .ky_nang import _cac_kenh  # noqa: PLC0415
                kenh_ds = _cac_kenh(goc)
            except Exception:  # noqa: BLE001
                kenh_ds = []
        self.kenh_ds = kenh_ds

    def tai(self, url: str) -> Tuple[int, bytes]:
        if self.mang >= TOI_DA_MANG_LUOT:
            return -1, b""
        self.mang += 1
        return self._tai(url)

    def oembed(self, vid: str) -> Tuple[int, Dict[str, Any]]:
        ma, du = self.tai("https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=" + vid)
        try:
            return ma, (json.loads(du.decode("utf-8")) if ma == 200 and du else {})
        except ValueError:
            return ma, {}

    def bia_song(self, vid: str) -> Optional[List[int]]:
        for ten in ("maxresdefault", "hqdefault"):
            ma, du = self.tai("https://i.ytimg.com/vi/{0}/{1}.jpg".format(vid, ten))
            if ma == 200 and du:
                v = van_tay(du)
                if v:
                    return v
            if ma == -1:
                return None
        return None

    def can_kiem(self, khoa: str) -> bool:
        """Mục đã ĐẠT thì không kiểm lại; mục khác kiểm lại sau ≥ `PHUT_KIEM_LAI` phút."""
        m = (self.so.get("muc") or {}).get(khoa) or {}
        if m.get("tt") == DAT:
            return False
        t = _gio(m.get("lan_kiem"))
        return t is None or (self.bay - t).total_seconds() >= PHUT_KIEM_LAI * 60

    def cu(self, khoa: str) -> Dict[str, Any]:
        return dict((self.so.get("muc") or {}).get(khoa) or {})


def _muc(loai: str, kenh: str, khoa: str, viec: str, han: Optional[_dt.datetime], tt: str, bang_chung: str = "",
         **them: Any) -> Dict[str, Any]:
    return dict({"loai": loai, "kenh": kenh, "khoa": khoa, "viec": viec, "han": _iso(han), "tt": tt,
                 "bang_chung": str(bang_chung)[:300]}, **them)


def _giu_cu(K: BoiCanh, loai: str, kenh: str, khoa: str, viec: str, han: Optional[_dt.datetime], **them: Any):
    """Chưa tới lượt kiểm lại → mang trạng thái cũ (đạt giữ đạt)."""
    c = K.cu(khoa)
    return _muc(loai, kenh, khoa, viec, han, c.get("tt_goc") or c.get("tt") or CHO, c.get("bang_chung") or "chưa tới "
                "lượt kiểm lại", **them)


# ── sổ trạng thái + kỳ vọng khai thẳng ─────────────────────────────────────────

def doc_so(goc: str) -> Dict[str, Any]:
    du = _json(_thu_muc(goc), "so.json")
    return du if isinstance(du, dict) else {"muc": {}, "bao": {}}


def ghi_ky_vong(goc: str, loai: str, kenh: str, khoa: str, viec: str, han: _dt.datetime, *,
                kiem: str = "", tham_so: Optional[Dict[str, Any]] = None) -> None:
    """Bộ chạy khai một kỳ vọng (vd `kiem="oembed_cong_khai"`, `tham_so={"video_id": …}`) — lượt tự kiểm sau hạn đọc lại."""
    p = os.path.join(_thu_muc(goc), "ky-vong.jsonl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "a", encoding="utf-8") as tep:
        tep.write(json.dumps({"loai": loai, "kenh": kenh, "khoa": khoa, "viec": viec, "han": _iso(han), "kiem": kiem,
                              "tham_so": tham_so or {}}, ensure_ascii=False) + "\n")


def kiem_ky_vong_khai(K: BoiCanh) -> List[Dict[str, Any]]:
    ra = []
    p = os.path.join(_thu_muc(K.goc), "ky-vong.jsonl")
    try:
        with io.open(p, encoding="utf-8") as tep:
            dong = [json.loads(d) for d in tep.readlines()[-500:] if d.strip()]
    except (OSError, ValueError):
        return ra
    for x in dong:
        han = _gio(x.get("han"))
        if not han or (K.bay - han).days > NGAY_XEM_LAI:
            continue
        khoa = "khai:" + str(x.get("khoa"))
        vid = str((x.get("tham_so") or {}).get("video_id") or "")
        if K.bay < han:
            ra.append(_muc(x.get("loai") or "khai", x.get("kenh") or "", khoa, x.get("viec") or "", han, CHO, "chưa tới hạn"))
        elif x.get("kiem") == "oembed_cong_khai" and vid:
            if not K.can_kiem(khoa):
                ra.append(_giu_cu(K, x.get("loai") or "khai", x.get("kenh") or "", khoa, x.get("viec") or "", han))
                continue
            ma, _d = K.oembed(vid)
            ra.append(_muc(x.get("loai") or "khai", x.get("kenh") or "", khoa, x.get("viec") or "", han,
                           DAT if ma == 200 else (CHO if ma <= 0 else HONG), "oEmbed {0}".format(ma)))
    return ra


# ── 1) video hôm nay công khai ─────────────────────────────────────────────────

def _dang_o_may_khac(goc: str, kenh: str) -> bool:
    try:
        from .ky_nang import _dang_o_may_khac as f  # noqa: PLC0415
        return bool(f(goc, kenh))
    except Exception:  # noqa: BLE001
        return False


def _so_video(goc: str) -> Dict[str, Any]:
    du = _json(goc, "vm", "logs", "so-video-id.json")
    return du if isinstance(du, dict) else {}


def kiem_dang(K: BoiCanh) -> List[Dict[str, Any]]:
    ra = []
    for khoa_so, m in _so_video(K.goc).items():
        if not isinstance(m, dict) or "/" not in khoa_so:
            continue
        kenh, ma_goi = khoa_so.split("/", 1)
        lich = _gio(m.get("lich_dat") or m.get("lich"))
        vid = str(m.get("video_id") or "")
        if kenh not in K.kenh_ds or not lich or not vid or _dang_o_may_khac(K.goc, kenh):
            continue
        if not (K.bay - _dt.timedelta(hours=36) <= lich <= K.bay + _dt.timedelta(hours=30)):
            continue
        han = lich + _dt.timedelta(hours=GIO_SAU_LICH)
        khoa = "dang:" + vid
        viec = "{0} lên công khai lúc {1:%d/%m %H:%M}".format(ma_goi, lich)
        if K.bay < han:
            ra.append(_muc("dang", kenh, khoa, viec, han, CHO, "chưa tới giờ", video_id=vid, ma_goi=ma_goi))
            continue
        if not K.can_kiem(khoa):
            ra.append(_giu_cu(K, "dang", kenh, khoa, viec, han, video_id=vid, ma_goi=ma_goi))
            continue
        ma, du = K.oembed(vid)
        tt = DAT if ma == 200 else (CHO if ma <= 0 else HONG)
        bc = ("công khai: 「{0}」".format(str(du.get("title") or "")[:60]) if ma == 200 else
              "oEmbed {0} — video {1} sau giờ hẹn (Studio: {2})".format(
                  ma, "riêng tư / chưa công khai" if ma in (401, 403) else "không tìm thấy" if ma == 404 else "?",
                  m.get("trang_thai_studio") or m.get("trang_thai") or "?"))
        ra.append(_muc("dang", kenh, khoa, viec, han, tt, bc, video_id=vid, ma_goi=ma_goi))
    # 20/10: máy đăng gặp hộp «xác minh số điện thoại» khi đặt bìa → giữ gói; 1 mục việc người mỗi kênh.
    xm = _json(K.goc, "vm", "logs", "can-xac-minh-dt.json")
    for kenh, m in (xm.items() if isinstance(xm, dict) else []):
        if kenh in K.kenh_ds and isinstance(m, dict):
            ra.append(_muc("dang", kenh, "xac-minh-dt:" + kenh, "đặt bìa tuỳ chỉnh {0}".format(m.get("ma") or ""),
                           _gio(m.get("lan_cuoi")), CHO, "YouTube đòi xác minh điện thoại từ {0} — máy đăng giữ gói "
                           "(không đăng thiếu bìa)".format(m.get("tu")), nguoi=True,
                           can_lam="youtube.com/verify — xác minh số điện thoại kênh {0}".format(kenh)))
    return ra


# ── 2) đổi bìa · 3) đổi tiêu đề (hàng sửa máy DOM) ────────────────────────────

def _hang_sua(goc: str) -> List[Dict[str, Any]]:
    du = _json(goc, "vm", "logs", "hang-sua.json")
    return [x for x in (du or {}).get("viec") or [] if isinstance(x, dict)] if isinstance(du, dict) else []


def _co_ab(goc: str, kenh: str, vid: str) -> bool:
    try:
        from . import ab_tieu_de as ab  # noqa: PLC0415
        m = ab.muc_cua(goc, kenh, vid)
        return bool(m and m.get("trang_thai") in (ab.TT_DA_DAT, ab.TT_DA_CO))
    except Exception:  # noqa: BLE001
        return False


def kiem_hang_sua(K: BoiCanh) -> List[Dict[str, Any]]:
    ra = []
    moi_nhat: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for v in _hang_sua(K.goc):
        moi_nhat[(str(v.get("video_id")), "bia" if v.get("buoc") in ("bia", "doi_bia") else str(v.get("buoc")))] = v
    for (vid, buoc), v in moi_nhat.items():
        kenh, tt_v = str(v.get("kenh") or ""), str(v.get("trang_thai") or "")
        if buoc not in ("bia", "tieu_de") or tt_v in ("huy", "bo") or kenh not in K.kenh_ds:
            continue
        them = _gio(v.get("them_luc"))
        ket = _gio(v.get("ket_luc"))
        khoa = "{0}:{1}:{2}".format("doi_bia" if buoc == "bia" else "tieu_de", vid, v.get("id"))
        loai = "doi_bia" if buoc == "bia" else "tieu_de"
        viec = "{0} {1} trên YouTube".format("bìa mới của" if buoc == "bia" else "tiêu đề mới của", v.get("ma_goi") or vid)
        them_f = dict(video_id=vid, ma_goi=v.get("ma_goi") or "", id_viec=v.get("id"), thu_lai="hang_sua")
        if tt_v != "xong":
            if them and (K.bay - them).total_seconds() / 3600.0 > GIO_TRE_HANG_SUA and (K.bay - them).days <= NGAY_XEM_LAI:
                ra.append(_muc(loai, kenh, khoa, viec, them + _dt.timedelta(hours=GIO_TRE_HANG_SUA), HONG,
                               "mục hàng sửa còn «{0}» sau {1:.0f} giờ (lỗi {2} lần: {3})".format(
                                   tt_v, (K.bay - them).total_seconds() / 3600.0, v.get("lan_loi") or 0,
                                   str(v.get("ly_do") or "")[:100]), tre=True, **them_f))
            continue
        if not ket or (K.bay - ket).days > NGAY_XEM_LAI:
            continue
        han = ket + _dt.timedelta(hours=1)
        if K.bay < han:
            ra.append(_muc(loai, kenh, khoa, viec, han, CHO, "chưa tới hạn", **them_f))
            continue
        if not K.can_kiem(khoa):
            ra.append(_giu_cu(K, loai, kenh, khoa, viec, han, **them_f))
            continue
        if buoc == "bia":
            mong = van_tay(str(v.get("anh") or "")) if os.path.isfile(str(v.get("anh") or "")) else None
            song = K.bia_song(vid)
            d = lech(song, mong)
            if mong is None:
                ra.append(_muc(loai, kenh, khoa, viec, han, CHO, "không còn tệp bìa đã xếp để so", **them_f))
            elif d is None:
                ra.append(_muc(loai, kenh, khoa, viec, han, CHO, "không tải được bìa i.ytimg.com", **them_f))
            else:
                tt = DAT if d <= LECH_DAT else HONG if d >= LECH_HONG else CHO
                ra.append(_muc(loai, kenh, khoa, viec, han, tt, "bìa đang chạy lệch vân tay {0}/256 so với tệp đã xếp "
                               "({1})".format(d, os.path.basename(str(v.get("anh")))), lech=d, **them_f))
        else:
            if _co_ab(K.goc, kenh, vid):
                ra.append(_muc(loai, kenh, khoa, viec, han, DAT, "video đang Thử nghiệm A/B — YouTube chọn tiêu đề",
                               **them_f))
                continue
            ma, du = K.oembed(vid)
            if ma != 200:
                ra.append(_muc(loai, kenh, khoa, viec, han, CHO, "oEmbed {0}".format(ma), **them_f))
                continue
            khop = chuan(du.get("title")) == chuan(v.get("tieu_de"))
            ra.append(_muc(loai, kenh, khoa, viec, han, DAT if khop else HONG,
                           "tiêu đề công khai 「{0}」{1}".format(str(du.get("title") or "")[:70],
                                                              "" if khop else " ≠ 「{0}」".format(
                                                                  str(v.get("tieu_de") or "")[:70])), **them_f))
    return ra


# ── 4) thử nghiệm A/B ──────────────────────────────────────────────────────────

def kiem_ab(K: BoiCanh) -> List[Dict[str, Any]]:
    try:
        from .giam_doc import _tu_dong as td  # noqa: PLC0415
        ds = td.doc_viec_may_kieu(K.goc, None, None)
        loai_ab = (td.LOAI_TEST_COMPARE, td.LOAI_AB_TIEU_DE)
    except Exception:  # noqa: BLE001
        return []
    ra = []
    for m in ds:
        if m.get("loai") not in loai_ab or m.get("kenh") not in K.kenh_ds:
            continue
        kenh, tt_m = str(m.get("kenh")), str(m.get("trang_thai") or "")
        tao, cn = _gio(m.get("tao_luc")), _gio(m.get("cap_nhat"))
        khoa = "ab:" + str(m.get("id"))
        viec = "Thử nghiệm A/B ({0} video) STARTED trên Studio".format(len(m.get("video_ids") or []))
        f = dict(id_viec=m.get("id"), thu_lai="viec_may")
        if tt_m in ("cho", "dang", "loi"):
            han = (tao or K.bay) + _dt.timedelta(hours=GIO_TRE_VIEC_MAY)
            ra.append(_muc("ab", kenh, khoa, viec, han, HONG if K.bay > han else CHO,
                           "việc máy còn «{0}» từ {1:%d/%m %H:%M} (thử {2} lần)".format(tt_m, tao or K.bay,
                                                                                     m.get("lan_thu") or 0),
                           tre=K.bay > han, **f))
            continue
        if tt_m != "xong" or not cn or (K.bay - cn).days > NGAY_XEM_LAI:
            continue
        thieu = []
        for vid, kv in ((m.get("ket") or {}).get("video") or {}).items():
            if isinstance(kv, dict) and kv.get("ket") == "da_dat":
                dl = kv.get("doc_lai") or {}
                if "STARTED" not in str(dl.get("trang_thai_tho") or "").upper() and dl.get("trang_thai") != "dang_chay":
                    thieu.append(vid)
        ra.append(_muc("ab", kenh, khoa, viec, cn, HONG if thieu else DAT,
                       "đọc lại Studio thiếu STARTED: " + ", ".join(thieu) if thieu else
                       "đọc lại Studio: STARTED ({0})".format(str((m.get("ket") or {}).get("ly_do") or "")[:120]), **f))
    return ra


# ── 5) danh sách phát ──────────────────────────────────────────────────────────

_RE_VID = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


def kiem_dsp(K: BoiCanh) -> List[Dict[str, Any]]:
    try:
        from . import danh_sach_phat as dsp  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        return []
    so_vid = _so_video(K.goc)
    chua_len = {str(m.get("video_id")) for m in so_vid.values() if isinstance(m, dict)
                and (_gio(m.get("lich_dat") or m.get("lich")) or K.bay) > K.bay}
    ra = []
    for kenh in K.kenh_ds:
        for d in dsp.doc(K.goc, kenh).get("danh_sach") or []:
            ma = str((d.get("doc_lai") or {}).get("ma") or "")
            them = [v for v in d.get("da_them") or [] if v not in chua_len]
            if not ma or not them:
                continue
            khoa = "dsp:{0}:{1}".format(kenh, ma)
            viec = "danh sách phát «{0}» có đủ {1} video (trang công khai)".format(d.get("ten"), len(them))
            han = (_gio(d.get("luc_tao")) or K.bay)
            f = dict(thu_lai="dsp", ma_ds=d.get("ma"), ma_playlist=ma)
            c = K.cu(khoa)
            if c.get("tt") == DAT and int(c.get("so") or 0) >= len(them):
                ra.append(_giu_cu(K, "dsp", kenh, khoa, viec, han, so=len(them), **f))
                continue
            if not K.can_kiem(khoa):
                ra.append(_giu_cu(K, "dsp", kenh, khoa, viec, han, so=len(them), **f))
                continue
            maht, du = K.tai("https://www.youtube.com/playlist?list=" + ma)
            if maht != 200 or not du:
                ra.append(_muc("dsp", kenh, khoa, viec, han, CHO, "không tải được trang danh sách phát ({0})".format(
                    maht), so=len(them), **f))
                continue
            co = set(_RE_VID.findall(du.decode("utf-8", "replace")))
            thieu = [v for v in them if v not in co]
            ra.append(_muc("dsp", kenh, khoa, viec, han, HONG if thieu else DAT,
                           "thiếu trên trang công khai: " + ", ".join(thieu) if thieu else
                           "trang công khai có đủ {0}/{0} video".format(len(them)), so=len(them), thieu=thieu, **f))
    return ra


# ── 6) ghim bình luận ──────────────────────────────────────────────────────────

def kiem_ghim(K: BoiCanh) -> List[Dict[str, Any]]:
    cmt = _json(K.goc, "vm", "logs", "cmt-dom.json")
    cmt = cmt if isinstance(cmt, dict) else {}
    ra = []
    for khoa_so, m in _so_video(K.goc).items():
        if not isinstance(m, dict) or "/" not in khoa_so:
            continue
        kenh = khoa_so.split("/", 1)[0]
        lich, vid = _gio(m.get("lich_dat") or m.get("lich")), str(m.get("video_id") or "")
        if kenh not in K.kenh_ds or not lich or not vid or not (6 <= (K.bay - lich).total_seconds() / 3600.0 <= 72):
            continue
        c = cmt.get(vid) if isinstance(cmt.get(vid), dict) else {}
        kk = cmt.get("_kenh:" + kenh) if isinstance(cmt.get("_kenh:" + kenh), dict) else {}
        han = lich + _dt.timedelta(hours=24)
        khoa = "ghim:" + vid
        viec = "bình luận ghim trên {0}".format(khoa_so.split("/", 1)[1])
        if c.get("trang_thai") == "da-ghim":
            ra.append(_muc("ghim", kenh, khoa, viec, han, DAT, "đã ghim {0}".format(c.get("da_ghim") or "")))
        elif kk.get("cho_xac_minh_tu"):
            ra.append(_muc("ghim", kenh, khoa, viec, han, CHO, "kênh chờ xác minh điện thoại từ {0} — YouTube chặn "
                           "ghim".format(kk.get("cho_xac_minh_tu")), nguoi=True,
                           can_lam="youtube.com/verify — xác minh số điện thoại kênh {0}".format(kenh)))
        else:
            ra.append(_muc("ghim", kenh, khoa, viec, han, HONG if K.bay > han else CHO,
                           "trạng thái «{0}», gửi {1} lần".format(c.get("trang_thai") or "chưa gửi", c.get("lan_gui") or 0)))
    return ra


# ── 7) bộ não / giấc ngủ / skill · 8) vận hành ────────────────────────────────

def kiem_nao(K: BoiCanh) -> List[Dict[str, Any]]:
    ra = []
    hom = K.bay.date().isoformat()
    nk = os.path.join(K.goc, "nao", "nhat-ky")
    han = _dt.datetime.combine(K.bay.date(), _dt.time(8, 30))
    try:
        with io.open(os.path.join(nk, "phien-{0}.log".format(hom)), encoding="utf-8", errors="replace") as tep:
            xong = "KET QUA: thanh cong" in tep.read()
    except OSError:
        xong = False
    xong = xong or os.path.isfile(os.path.join(nk, hom + ".md"))
    ra.append(_muc("nao", "", "nao:phien:" + hom, "phiên sáng của bộ não hôm nay", han,
                   DAT if xong else (HONG if K.bay > han else CHO), "nhật ký ngày có" if xong else "chưa có nhật ký ngày"))
    try:
        from .ky_nang import _nao_bp  # noqa: PLC0415
        _gom, ngu, co = _nao_bp(K.goc)
    except Exception:  # noqa: BLE001
        co, ngu = False, None
    if co:
        ok = ngu is not None and ngu <= GIO_NGU_CU
        ra.append(_muc("nao", "", "nao:ngu:" + hom, "giấc ngủ não bộ phận ≤ {0:.0f} giờ".format(GIO_NGU_CU), K.bay,
                       DAT if ok else HONG, "ngủ {0}".format("chưa lần nào" if ngu is None else "{0:.0f} giờ trước".format(ngu)),
                       thu_lai="nao_ngu"))
    p = os.path.join(K.goc, "workspace", "ky-nang", "so-chay.jsonl")
    tuoi = (time.time() - os.path.getmtime(p)) / 3600.0 if os.path.isfile(p) else None
    try:
        from .ky_nang_tu import doc_so as _ds  # noqa: PLC0415
        cuoi = _gio((_ds(K.goc, 50) or [{}])[-1].get("luc"))
        tuoi = (K.bay - cuoi).total_seconds() / 3600.0 if cuoi else tuoi
    except Exception:  # noqa: BLE001
        pass
    ra.append(_muc("nao", "", "nao:skill:" + hom, "skill tự kích hoạt có chạy (sổ ≤ {0:.0f} giờ)".format(GIO_SO_SKILL_CU),
                   K.bay, DAT if tuoi is not None and tuoi <= GIO_SO_SKILL_CU else HONG,
                   "dòng sổ cuối {0}".format("không có" if tuoi is None else "{0:.1f} giờ trước".format(tuoi)),
                   can_lam="xem tác vụ ShopAPI-KyNang (mỗi giờ :35) đã đăng ký chưa"))
    return ra


def kiem_van_hanh(K: BoiCanh) -> List[Dict[str, Any]]:
    du = _json(K.goc, "workspace", "van-hanh", "trang-thai.json")
    tt = (du or {}).get("tom_tat") or {} if isinstance(du, dict) else {}
    luc = float((du or {}).get("luc") or tt.get("luc") or 0) if isinstance(du, dict) else 0.0
    tuoi = (K.bay.timestamp() - luc) / 60.0 if luc else None
    khoa = "van_hanh:{0:%Y-%m-%d}".format(K.bay)
    if tuoi is None or tuoi > PHUT_VAN_HANH_CU:
        return [_muc("van_hanh", "", khoa, "lượt canh vận hành 5 phút còn chạy", K.bay, HONG,
                     "trang-thai.json {0}".format("không có" if tuoi is None else "cũ {0:.0f} phút".format(tuoi)),
                     thu_lai="van_hanh")]
    hong = [x.get("ten") or x.get("ma") for x in tt.get("ds") or [] if x.get("trang_thai") != "song"]
    return [_muc("van_hanh", "", khoa, "mọi thành phần vận hành sống", K.bay, HONG if hong else DAT,
                 "{0}/{1} sống{2}".format(tt.get("song"), tt.get("tong"), "; chưa sống: " + ", ".join(hong) if hong else ""))]


# ── 9) nhịp sản xuất ───────────────────────────────────────────────────────────

def _kenh_tu_chay(goc: str, kenh: str) -> bool:
    try:
        from .ky_nang import _kenh_yaml  # noqa: PLC0415
        y = _kenh_yaml(goc, kenh)
        if not y.get("tu_chay"):
            return False
        from . import kenh_khong_phat  # noqa: PLC0415
        return not kenh_khong_phat.dang_dung(goc, kenh)[0]
    except Exception:  # noqa: BLE001
        return False


def kiem_nhip(K: BoiCanh) -> List[Dict[str, Any]]:
    lich_theo: Dict[str, List[_dt.datetime]] = {}
    for khoa_so, m in _so_video(K.goc).items():
        if isinstance(m, dict) and "/" in khoa_so and m.get("video_id"):
            t = _gio(m.get("lich_dat") or m.get("lich"))
            if t:
                lich_theo.setdefault(khoa_so.split("/", 1)[0], []).append(t)
    ra = []
    mai = K.bay.date() + _dt.timedelta(days=1)
    for kenh in K.kenh_ds:
        if _dang_o_may_khac(K.goc, kenh) or not _kenh_tu_chay(K.goc, kenh):
            continue
        ds = lich_theo.get(kenh, [])
        co_mai = any(t.date() == mai for t in ds)
        han = _dt.datetime.combine(K.bay.date(), _dt.time(GIO_NHIP_TOI))
        ra.append(_muc("nhip", kenh, "nhip:mai:{0}:{1}".format(kenh, mai), "kênh có video hẹn cho {0:%d/%m}".format(mai),
                       han, DAT if co_mai else (HONG if K.bay >= han else CHO),
                       "đã hẹn {0} video ngày mai".format(sum(1 for t in ds if t.date() == mai))))
        thieu = [(K.bay.date() - _dt.timedelta(days=i)) for i in range(0, 3)
                 if not any(t.date() == K.bay.date() - _dt.timedelta(days=i) and t <= K.bay for t in ds)]
        thieu = [d for d in thieu if d < K.bay.date() or K.bay.hour >= 8]
        nhieu = [d for d in {t.date() for t in ds} if sum(1 for t in ds if t.date() == d) > 1
                 and (K.bay.date() - d).days < 3]
        khe = _khe_kenh(K.goc, kenh)
        nn = {d: nguyen_nhan_ngay_trong(K.goc, kenh, d, khe) for d in sorted(thieu)}
        ra.append(_muc("nhip", kenh, "nhip:3ngay:{0}:{1}".format(kenh, K.bay.date()), "1 video/ngày suốt 3 ngày qua",
                       K.bay, HONG if thieu else DAT,
                       ("ngày không có video lên sóng: " + ", ".join("{0:%d/%m} ({1})".format(d, nn[d]["ten"])
                                                                     for d in sorted(thieu))
                        if thieu else "đều 1 video/ngày") + ("; ngày dồn ≥ 2 video: " + ", ".join(
                            "{0:%d/%m}".format(d) for d in sorted(nhieu)) if nhieu else "")))
        # 19/10/2026: mỗi ngày trống (khe đã qua) là MỘT mục kèm NGUYÊN NHÂN — `xep_muon` là lỗi xếp lịch của máy
        # (video đã sẵn sàng kịp khe mà bị hẹn ngày sau), khác hẳn thiếu gói (sản xuất chậm/kẹt) hay gói bị giữ.
        for d, x in nn.items():
            if x["moc_khe"] is not None and x["moc_khe"] + _dt.timedelta(hours=GIO_SAU_LICH) > K.bay:
                continue
            ra.append(_muc("nhip", kenh, "nhip:khe:{0}:{1}".format(kenh, d), "khe {0:%d/%m} có video lên sóng".format(d),
                           x["moc_khe"], HONG, "{0}: {1}".format(x["ten"], x["chu"]), nguyen_nhan=x["loai"]))
    return ra


#: Nguyên nhân một ngày không có video (`nguyen_nhan_ngay_trong`).
TEN_NGUYEN_NHAN = {"xep_muon": "xếp lịch muộn", "giu_goi": "gói bị giữ/kẹt", "tai_hong": "tải lên hỏng",
                   "thieu_goi": "không có gói kịp giờ"}


def _khe_kenh(goc: str, kenh: str) -> List[str]:
    """Giờ đăng trong ngày của kênh (`nhip_dang`, không thì `gio_dang`) — rỗng nếu không đọc được."""
    try:
        from . import xep_lich  # noqa: PLC0415
        from .ky_nang import _kenh_yaml  # noqa: PLC0415
        y = _kenh_yaml(goc, kenh)
        return xep_lich.chuan_hoa_nhip(y.get("nhip_dang")) or xep_lich.chuan_hoa_nhip(y.get("gio_dang"))
    except Exception:  # noqa: BLE001
        return []


def nguyen_nhan_ngay_trong(goc: str, kenh: str, ngay: _dt.date, khe: Sequence[str]) -> Dict[str, Any]:
    """Vì sao ngày `ngay` của kênh không có video lên sóng → {loai, ten, chu, ma, moc_khe}.

    Thứ tự (bằng chứng mạnh trước): `xep_muon` — sổ máy đăng có video TẢI XONG trước khe đầu của ngày ≥ biên tải
    lên (`xep_lich.BIEN_TAI_TOI_THIEU_PHUT`) mà lại hẹn ngày SAU (ca TL2-T7-0032 19/10/2026); `giu_goi` — dòng kế hoạch
    "Sẵn sàng" hẹn đúng ngày đó mà chưa lên kênh (cổng bìa giữ, kẹt); `tai_hong` — bản tải ngày đó hỏng/nháp;
    còn lại `thieu_goi` — không có gói nào sẵn sàng kịp khe (sản xuất chậm/kẹt/bỏ lượt)."""
    from . import ke_hoach_dang, xep_lich  # noqa: PLC0415

    gio0 = (list(khe) or ["00:00"])[0]
    moc_khe = _dt.datetime.combine(ngay, _dt.time(int(gio0[:2]), int(gio0[3:])))
    bien = _dt.timedelta(minutes=xep_lich.BIEN_TAI_TOI_THIEU_PHUT)

    def ra(loai: str, chu: str, ma: str = "") -> Dict[str, Any]:
        return {"loai": loai, "ten": TEN_NGUYEN_NHAN[loai], "chu": chu, "ma": ma, "moc_khe": moc_khe}

    muon, hong = [], []
    for k, m in _so_video(goc).items():
        if not isinstance(m, dict) or not str(k).startswith(kenh + "/"):
            continue
        ma = str(k).split("/", 1)[-1]
        lich = _gio(m.get("lich_dat") or m.get("lich"))
        if m.get("trang_thai") in xep_lich.TT_SO_CHUA_LEN_KENH:
            if lich is not None and lich.date() == ngay:
                hong.append(ma)
            continue
        tai = _gio(m.get("tai_xong_luc")) or _gio(m.get("cap_nhat"))
        if m.get("video_id") and tai and lich and tai <= moc_khe - bien and lich.date() > ngay:
            muon.append((tai, ma, lich))
    if muon:
        tai, ma, lich = min(muon)
        return ra("xep_muon", "{0} tải xong {1:%d/%m %H:%M} (trước khe {2:%d/%m %H:%M} ≥ {3}') mà hẹn {4:%d/%m %H:%M}"
                  " — khe bị bỏ trống dù đã có video".format(ma, tai, moc_khe, xep_lich.BIEN_TAI_TOI_THIEU_PHUT, lich),
                  ma)
    try:
        cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    except Exception:  # noqa: BLE001
        cot, hang = [], []
    for d in (dict(zip(cot, h)) for h in hang):
        if (str(d.get("Ngày đăng") or "").strip() == ngay.strftime("%d/%m/%Y") and str(d.get("Sẵn sàng") or "").strip()
                and "ĐÃ ĐĂNG" not in str(d.get("Trạng thái đăng") or "").upper()):
            gc = str(d.get("Ghi chú") or d.get("Trạng thái đăng") or "").strip()
            return ra("giu_goi", "{0} hẹn {1} {2} nhưng chưa lên kênh{3}".format(
                d.get("Mã gói"), d.get("Ngày đăng"), d.get("Giờ đăng"), " — " + gc[:120] if gc else ""),
                str(d.get("Mã gói") or ""))
    if hong:
        return ra("tai_hong", "bản tải ngày {0:%d/%m} chưa lên kênh: {1}".format(ngay, ", ".join(sorted(hong))),
                  sorted(hong)[0])
    return ra("thieu_goi", "không có gói nào sẵn sàng trước khe {0:%d/%m %H:%M} (sản xuất chậm/kẹt hoặc bỏ lượt)"
              .format(moc_khe))


def kiem_duong_max(K: BoiCanh) -> List[Dict[str, Any]]:
    """Cài đặt chọn ví (`viet_chu_bang: "vi"`, chủ 17/10: Max hết token) mà sổ Claude Max (`workspace/viet-max/
    so-dung.jsonl`) còn có lượt MỚI HƠN lần đổi Cài đặt → còn một đường gọi Max sót (13–17/10: 81 lần "Claude Max hỏng")."""
    p_cai = os.path.join(K.goc, "workspace", "cai-dat.json")
    cai = _json(p_cai) or {}
    if str(cai.get("viet_chu_bang") or "").strip().lower() != "vi":
        return []
    moc = _dt.datetime.fromtimestamp(os.path.getmtime(p_cai)) if os.path.isfile(p_cai) else K.bay
    moi = []
    try:
        with io.open(os.path.join(K.goc, "workspace", "viet-max", "so-dung.jsonl"), encoding="utf-8") as tep:
            dong = tep.readlines()[-300:]
    except OSError:
        dong = []
    for d in dong:
        try:
            x = json.loads(d)
        except ValueError:
            continue
        t = _gio(x.get("luc")) if isinstance(x, dict) else None
        if t and t > moc + _dt.timedelta(minutes=5):
            moi.append(str(x.get("viec") or "?"))
    return [_muc("nao", "", "max:{0:%Y-%m-%d}".format(K.bay), "không còn đường gọi Claude Max khi Cài đặt chọn ví", K.bay,
                 HONG if moi else DAT, ("{0} lượt Max sau khi chọn ví: {1}".format(len(moi), ", ".join(
                     dict.fromkeys(moi))[:200]) if moi else "không lượt Max nào từ {0:%d/%m %H:%M}".format(moc)),
                 can_lam="báo người quản trị tool: còn mã gọi Max không qua viet_max.duong_viet_chu")]


def kiem_trang_chu(K: BoiCanh) -> List[Dict[str, Any]]:
    """19/10/2026 — trang chủ kênh ≥ 90% đúng chủ đề (sổ duy trì `vm/logs/nuoi-trang-chu/`, skill D18). Đạt = lần đo cuối
    đạt và còn mới; máy đang tự nuôi lại = đang thử lại (đã báo động thì ghi rõ — không báo gộp mỗi ngày nữa); chủ đang
    tắt nuôi mà dưới mục tiêu / Chrome cần đăng nhập lại = chờ người (Việc của bạn). Chỉ đọc đĩa."""
    try:
        from .ky_nang import _nap_vm  # noqa: PLC0415
        n = _nap_vm("nuoi_trang_chu")
    except Exception:  # noqa: BLE001
        return []
    ra = []
    for kenh in K.kenh_ds:
        if _dang_o_may_khac(K.goc, kenh):
            continue
        t = n.tom_tat_duy_tri(kenh, K.goc, K.bay.timestamp())
        if not t.get("tt"):
            continue
        tt = {"dat": DAT, "thu_lai": THU_LAI, "cho": CHO, "nguoi": CHO}[t["tt"]]
        them = {}
        if t["tt"] == "nguoi":
            them = {"nguoi": True, "can_lam": ("đăng nhập lại / giải CAPTCHA trong Chrome kênh {0} (máy không gõ mật khẩu)".format(kenh)
                                               if t["can_nguoi"] else
                                               "quyết: bật nuoi_trang_chu: true trong kenh.yaml kênh {0} để máy tự nuôi lại "
                                               "trang chủ (hiện chỉ đo)".format(kenh))}
        ra.append(_muc("trang_chu", kenh, "trang_chu:" + kenh, "trang chủ ≥ 90% đúng chủ đề (đo theo lần quét trang chủ)",
                       K.bay, tt, t["cau"], **them))
        if t.get("quet_cu") and not t.get("quet_chan"):
            # 19/10: D18 đo từ lần quét SẴN CÓ — quá 3 ngày không có lần quét mới = lịch quét trang chủ của kênh hỏng. Báo
            # MỘT lần (ngày đầu thấy: HỎNG → báo động gộp; ngày sau cùng lần quét cũ ấy: CHỜ), không mở Chrome bù.
            khoa = "trang_chu_quet:{0}:{1}".format(kenh, t.get("luc_quet") or "")
            dau = str(K.cu(khoa).get("lan_dau_hong") or "")[:10]
            ra.append(_muc("trang_chu", kenh, khoa, "lịch quét trang chủ còn chạy (có lần quét ≤ 3 ngày)", K.bay,
                           HONG if not dau or dau == K.bay.date().isoformat() else CHO,
                           "lịch quét trang chủ hỏng: lần quét cuối {0} ({1:.0f} ngày trước){2}".format(
                               t.get("luc_quet"), float(t.get("ngay_quet") or 0),
                               " — đã báo {0}".format(dau) if dau and dau != K.bay.date().isoformat() else "")))
    return ra


KIEM = (("dang", kiem_dang), ("hang_sua", kiem_hang_sua), ("ab", kiem_ab), ("dsp", kiem_dsp), ("ghim", kiem_ghim),
        ("nao", kiem_nao), ("van_hanh", kiem_van_hanh), ("nhip", kiem_nhip), ("khai", kiem_ky_vong_khai),
        ("max", kiem_duong_max), ("trang_chu", kiem_trang_chu))


# ── thử lại qua đúng bộ chạy ───────────────────────────────────────────────────

def _thu_lai_hang_sua(K: BoiCanh, m: Dict[str, Any]) -> Tuple[bool, str]:
    from .giam_doc import cuu_ctr  # noqa: PLC0415
    khoa = cuu_ctr.giu_khoa_hang(K.goc)
    if not khoa:
        return False, "hàng sửa đang bị khoá — lượt sau"
    try:
        ds = cuu_ctr.doc_hang(K.goc)
        v = next((x for x in ds if x.get("id") == m.get("id_viec")), None)
        if v is None:
            return False, "không còn mục hàng sửa"
        if v.get("buoc") in ("bia", "doi_bia") and v.get("anh"):
            from . import cong_chu  # noqa: PLC0415
            ly = cong_chu.kiem_dau(str(v["anh"]))
            if ly:
                return False, "bìa chưa có dấu cổng chữ — không xếp lại: " + ly
        v.update(trang_thai="cho", lan_loi=0, ly_do="tự kiểm: {0} — thử lại".format(m.get("bang_chung", "")[:120]))
        cuu_ctr._ghi_hang(K.goc, ds)  # noqa: SLF001
        return True, "mở lại mục hàng sửa — máy DOM làm ở khe đêm (hoặc S03 nếu gấp)"
    finally:
        try:
            os.remove(khoa)
        except OSError:
            pass


def _thu_lai_viec_may(K: BoiCanh, m: Dict[str, Any]) -> Tuple[bool, str]:
    from .giam_doc import _tu_dong as td  # noqa: PLC0415
    if m.get("tre"):
        return False, "việc còn mở — chờ suất (đã ưu tiên qua sổ tay nếu đói)"
    ok = td.cap_nhat_viec_may_kieu(K.goc, str(m.get("id_viec")), trang_thai="cho", lan_thu=0)
    return ok, "mở lại việc máy — D13 chạy lại" if ok else "không còn việc máy"


def _thu_lai_dsp(K: BoiCanh, m: Dict[str, Any]) -> Tuple[bool, str]:
    from . import danh_sach_phat as dsp  # noqa: PLC0415
    ke = dsp.doc(K.goc, m["kenh"])
    d = next((x for x in ke.get("danh_sach") or [] if x.get("ma") == m.get("ma_ds")), None)
    thieu = set(m.get("thieu") or [])
    if d is None or not thieu:
        return False, "không còn danh sách / không thiếu"
    d["da_them"] = [v for v in d.get("da_them") or [] if v not in thieu]
    dsp.ghi(K.goc, m["kenh"], ke)
    return True, "bỏ {0} video khỏi «đã thêm» — D15 thêm lại".format(len(thieu))


def _sinh(K: BoiCanh, lenh: List[str], ten: str) -> Tuple[bool, str]:
    from . import van_hanh  # noqa: PLC0415
    if not (os.path.isfile(os.path.join(K.goc, "van_hanh.py")) and os.path.isdir(os.path.join(K.goc, "core"))):
        return False, "gốc không phải thư mục tool (không sinh tiến trình)"
    pid = van_hanh._sinh_tach(lenh, K.goc, os.path.join(_thu_muc(K.goc), ten + ".log"))  # noqa: SLF001
    return bool(pid), "đã chạy lại ({0}, PID {1})".format(ten, pid)


def _thu_lai_van_hanh(K: BoiCanh, m: Dict[str, Any]) -> Tuple[bool, str]:
    from . import van_hanh  # noqa: PLC0415
    return _sinh(K, [van_hanh._pythonw(K.goc), os.path.join(K.goc, "van_hanh.py"), "mot-luot"], "van-hanh")  # noqa: SLF001


def _thu_lai_nao_ngu(K: BoiCanh, m: Dict[str, Any]) -> Tuple[bool, str]:
    from . import van_hanh  # noqa: PLC0415
    return _sinh(K, [van_hanh._pythonw(K.goc), "-X", "utf8", "-m", "core.nao_bo_phan", "ngu"], "nao-ngu")  # noqa: SLF001


THU_LAI_BO_CHAY: Dict[str, Callable[[BoiCanh, Dict[str, Any]], Tuple[bool, str]]] = {
    "hang_sua": _thu_lai_hang_sua, "viec_may": _thu_lai_viec_may, "dsp": _thu_lai_dsp, "van_hanh": _thu_lai_van_hanh,
    "nao_ngu": _thu_lai_nao_ngu}


# ── phân loại nguyên nhân + sửa ────────────────────────────────────────────────

def _dong_loi_gan(goc: str, kenh: str, bay: _dt.datetime, gio: float = 30.0) -> List[str]:
    from . import loi_lap_lai as ll  # noqa: PLC0415
    tu = bay.timestamp() - gio * 3600
    ra: List[Tuple[float, str]] = []
    nguon = [ll.doc_log_co_ngay(os.path.join(goc, "vm", "logs", "dang-dom.log"), "dang-dom"),
             ll.doc_log_chi_gio(os.path.join(goc, "vm", "agent.log"), "agent")]
    if kenh:
        nguon.append(ll.doc_log_co_ngay(os.path.join(goc, "workspace", "tu-chay", "dieu-phoi-{0}.log".format(kenh)),
                                        "tu-chay", kenh))
        nguon.append(ll.doc_log_co_ngay(os.path.join(goc, "vm", "logs", "studio-may", kenh + ".log"), "studio", kenh))
    for it in nguon:
        try:
            for luc, _n, k, chu in it:
                if luc >= tu and (not kenh or k == kenh or kenh in chu) and ll.la_loi(chu):
                    ra.append((luc, chu))
        except Exception:  # noqa: BLE001
            continue
    return [c for _l, c in sorted(ra)[-40:]]


def phan_loai(K: BoiCanh, m: Dict[str, Any], so_tay: Dict[str, Any]) -> Dict[str, Any]:
    """→ {bai, lop, ten, dong, sua}. Lượt kẹt / khoá chết / đói suất mà sổ tay vừa xử lý cho kênh này → `sua`."""
    from . import loi_lap_lai as ll  # noqa: PLC0415
    kenh = m.get("kenh") or ""
    for x in so_tay.get("luot_ket") or [] if isinstance(so_tay.get("luot_ket"), list) else []:
        if x.get("kenh") == kenh and m["loai"] in ("nhip", "dang"):
            b = ll.bai(x.get("lop") if x.get("lop") in ("nguon_mat",) else "luot_ket") or {}
            return dict(b, bai=b.get("ma"), dong="lượt {0}: {1}".format(x["ma_luot"], x["ly_do"] or x["loi"][:160]),
                        sua=("đã bỏ lượt kẹt {0}".format(x["ma_luot"]) if x.get("da_bo") else ""),
                        nguoi=False)
    for x in so_tay.get("viec_doi") or [] if isinstance(so_tay.get("viec_doi"), list) else []:
        if x.get("kenh") == kenh and m["loai"] in ("ab", "dsp", "doi_bia", "tieu_de"):
            b = ll.bai("viec_doi") or {}
            return dict(b, bai="viec_doi", dong="skill {0} chờ suất {1:.0f} giờ: {2}".format(x["ma"], x["gio"], x["ly_do"]),
                        sua="đã ưu tiên skill {0} lên đầu suất nặng".format(x["ma"]), nguoi=False)
    for chu in reversed(_dong_loi_gan(K.goc, kenh, K.bay)):
        ma = ll.phan_lop(chu)
        if ma:
            b = ll.bai(ma) or {}
            return dict(b, bai=ma, dong=chu[:200], sua="", nguoi=b.get("lop") == "nguoi")
    return {"bai": "", "lop": "", "ten": "chưa rõ nguyên nhân", "dong": "", "sua": "", "nguoi": False}


def xu_ly(K: BoiCanh, ds: List[Dict[str, Any]], so_tay: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Mục HỎNG: thử lại (≤ `SO_THU_LAI`) → phân loại → tự sửa / thử-lại-tạm / còn mở. Cập nhật `K.so`."""
    so_muc = K.so.setdefault("muc", {})
    luc = K.bay.isoformat(timespec="seconds")
    for m in ds:
        c = dict(so_muc.get(m["khoa"]) or {})
        kiem_moi = m["bang_chung"] != "chưa tới lượt kiểm lại"
        m["tt_goc"] = m.get("tt_goc") or m["tt"]
        if m["tt"] == HONG:
            c.setdefault("lan_dau_hong", luc)
            lan = int(c.get("lan_thu") or 0)
            ham = THU_LAI_BO_CHAY.get(str(m.get("thu_lai") or ""))
            if ham and lan < SO_THU_LAI and kiem_moi and not K.thu:
                try:
                    ok, cau = ham(K, m)
                except Exception as loi:  # noqa: BLE001
                    ok, cau = False, "thử lại lỗi: {0}".format(str(loi)[:120])
                c["lan_thu"] = lan + (1 if ok else 0)
                m.update(sua=cau, lan_thu=c["lan_thu"])
                if ok:
                    m["tt"] = THU_LAI
            elif ham and lan < SO_THU_LAI and K.thu:
                m.update(tt=THU_LAI, sua="(thử) sẽ thử lại qua bộ chạy «{0}»".format(m.get("thu_lai")))
            if m["tt"] == HONG:
                if kiem_moi or not c.get("nguyen_nhan"):
                    pl = phan_loai(K, m, so_tay)
                else:
                    pl = c.get("nguyen_nhan") or {}
                m["nguyen_nhan"] = pl
                if pl.get("sua"):
                    m.update(tt=TU_SUA, sua=pl["sua"])
                elif pl.get("lop") == "thu_lai" and (K.bay - (_gio(c.get("lan_dau_hong")) or K.bay)).total_seconds() < 86400:
                    m.update(tt=CHO, sua="lỗi tạm phía ShopAPI — bộ chạy tự thử lại (luật chủ)")
                elif pl.get("lop") == "cho_phien":
                    m.update(tt=CHO, sua="tự hồi ở phiên DOM kế — máy kiểm lại")
                else:
                    m["tt"] = MO
                    m["nguoi"] = bool(m.get("nguoi") or pl.get("nguoi"))
                c["nguyen_nhan"] = pl
        elif m["tt"] == DAT and c.get("tt") in (HONG, MO, THU_LAI, TU_SUA):
            m["sua"] = "đạt sau khi máy xử lý ({0})".format(c.get("sua") or c.get("tt"))
            m["da_sua_xong"] = True
        c.update(tt=m["tt"], tt_goc=m["tt_goc"], bang_chung=m["bang_chung"], loai=m["loai"], kenh=m["kenh"],
                 viec=m["viec"], sua=m.get("sua") or c.get("sua", ""), cap_nhat=luc)
        if kiem_moi:
            c["lan_kiem"] = luc
        if m.get("da_sua_xong"):
            c["da_sua_xong"] = True
        so_muc[m["khoa"]] = c
    # dọn mục cũ
    moc = (K.bay - _dt.timedelta(days=10)).isoformat()
    for k in [k for k, v in so_muc.items() if str(v.get("cap_nhat") or "") < moc]:
        so_muc.pop(k, None)
    return ds


# ── báo cáo · báo động gộp ─────────────────────────────────────────────────────

def tom_tat(ds: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    ra = {DAT: 0, TU_SUA: 0, MO: 0, CHO: 0, THU_LAI: 0}
    for m in ds:
        if m["tt"] == DAT and m.get("da_sua_xong"):
            ra[TU_SUA] += 1
        else:
            ra[m["tt"]] = ra.get(m["tt"], 0) + 1
    return ra


def dong_ngan(tt: Dict[str, int], bay: _dt.datetime) -> str:
    return "Tự kiểm {0:%d/%m %H:%M}: {1} đạt · {2} máy đã tự sửa · {3} đang thử lại · {4} còn mở".format(
        bay, tt.get(DAT, 0), tt.get(TU_SUA, 0), tt.get(THU_LAI, 0), tt.get(MO, 0))


def _bao_gop(K: BoiCanh, ds: List[Dict[str, Any]]) -> Optional[str]:
    """MỘT báo động gộp mỗi ngày: các mục còn mở chưa báo hôm nay. Trả câu đã báo (hoặc None)."""
    ngay = K.bay.date().isoformat()
    bao = K.so.setdefault("bao", {})
    for k in [k for k in bao if k < (K.bay.date() - _dt.timedelta(days=3)).isoformat()]:
        bao.pop(k, None)
    da = bao.setdefault(ngay, {"da_gui": False, "khoa": []})
    mo = [m for m in ds if m["tt"] == MO and m["khoa"] not in da["khoa"]]
    if not mo:
        return None
    dong = ["- {0}{1}: {2} — {3}{4}".format("[cần bạn] " if m.get("nguoi") else "", m["kenh"] or "máy", m["viec"],
                                            m["bang_chung"][:160], " · nguyên nhân: " + str(
                                                (m.get("nguyen_nhan") or {}).get("ten") or "") if m.get("nguyen_nhan")
                                            else "") for m in mo]
    tieu = "Tự kiểm: {0} việc máy chưa tự sửa được".format(len(mo))
    if K.thu:
        return tieu
    try:
        from . import gac_tong  # noqa: PLC0415
        gac_tong._ghi_loi_chay_max_md(K.goc, K.bay, [gac_tong._su_co(  # noqa: SLF001
            "tu_kiem:" + m["loai"], "thuong", "Tự kiểm: {0} — {1}".format(m["viec"], m["bang_chung"][:160]),
            kenh=m["kenh"]) for m in mo])
    except Exception:  # noqa: BLE001
        pass
    if not da["da_gui"]:
        try:
            from . import bao_dong  # noqa: PLC0415
            bao_dong.bao_dong("tu_kiem_ngay", tieu, "\n".join(dong)[:3500], goc=K.goc, muc=bao_dong.MUC_THUONG)
        except Exception:  # noqa: BLE001
            pass
        da["da_gui"] = True
    try:
        from . import nao_bo_phan  # noqa: PLC0415
        bp = {"dang": "dang-video", "doi_bia": "bia", "tieu_de": "tieu-de", "ab": "bia", "dsp": "tieu-de",
              "ghim": "binh-luan", "nao": "suc-khoe-may", "van_hanh": "suc-khoe-may", "nhip": "dieu-phoi"}
        for m in mo:
            nao_bo_phan.ghi(K.goc, bp.get(m["loai"], "dieu-phoi"), "loi", kenh=m["kenh"], ma_goi=m.get("ma_goi") or "",
                            noi_dung="tự kiểm: {0} — {1}".format(m["viec"], m["bang_chung"]), nguon="tu_kiem",
                            khoa="tu-kiem:{0}:{1}".format(ngay, m["khoa"]))
    except Exception:  # noqa: BLE001
        pass
    da["khoa"] = list(da["khoa"]) + [m["khoa"] for m in mo]
    return tieu


def nhip(goc: str, *, thu: bool = False, bay: Optional[_dt.datetime] = None, tai: Optional[Tai] = None,
         so_tay: Optional[Dict[str, Any]] = None, kenh_ds: Optional[List[str]] = None) -> Dict[str, Any]:
    """MỘT lượt (gác tổng mỗi 15 phút): sổ tay sửa → kiểm mọi kỳ vọng → thử lại / phân loại / sửa → báo cáo ngày."""
    K = BoiCanh(goc, bay=bay, tai=tai, thu=thu, kenh_ds=kenh_ds)
    if so_tay is None:
        try:
            from . import loi_lap_lai  # noqa: PLC0415
            so_tay = loi_lap_lai.chay_so_tay(goc, thu=thu)
        except Exception as loi:  # noqa: BLE001
            so_tay = {"loi": str(loi)[:200]}
    ds: List[Dict[str, Any]] = []
    loi_kiem: Dict[str, str] = {}
    for ten, ham in KIEM:
        try:
            ds += ham(K)
        except Exception as loi:  # noqa: BLE001 — một bộ kiểm hỏng không làm vỡ lượt
            loi_kiem[ten] = str(loi)[:200]
    xu_ly(K, ds, so_tay)
    tt = tom_tat(ds)
    bao = _bao_gop(K, ds)
    kq = {"luc": K.bay.isoformat(timespec="seconds"), "tom_tat": tt, "dong": dong_ngan(tt, K.bay), "mang": K.mang,
          "loi_kiem": loi_kiem, "bao": bao or "", "so_tay": so_tay, "muc": ds,
          "nguoi": [m for m in ds if m.get("nguoi") and m["tt"] in (MO, CHO)]}
    if not thu:
        _ghi_json(os.path.join(_thu_muc(goc), K.bay.date().isoformat() + ".json"), kq)
        _ghi_json(os.path.join(_thu_muc(goc), "so.json"), K.so)
    return kq


# ── cho bảng điều khiển ────────────────────────────────────────────────────────

def bao_cao_moi(goc: str, bay: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Báo cáo ngày MỚI NHẤT có trên đĩa (không muộn hơn `bay` nếu truyền) — không phụ thuộc đồng hồ máy."""
    import glob as _glob  # noqa: PLC0415
    ten = sorted(os.path.basename(p) for p in _glob.glob(os.path.join(_thu_muc(goc), "????-??-??.json")))
    if bay is not None:
        ten = [t for t in ten if t[:10] <= bay.date().isoformat()]
    for t in reversed(ten[-3:]):
        du = _json(_thu_muc(goc), t)
        if isinstance(du, dict):
            return du
    return {}


def o_truc_quan(goc: str, bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Ô «Tự kiểm» của 8790: {dat, tu_sua, thu_lai, mo, dong, luc, mo_ds} của báo cáo mới nhất."""
    du = bao_cao_moi(goc, bay_gio)
    tt = du.get("tom_tat") or {}
    return {"dat": tt.get(DAT, 0), "tu_sua": tt.get(TU_SUA, 0), "thu_lai": tt.get(THU_LAI, 0), "mo": tt.get(MO, 0),
            "luc": str(du.get("luc") or "")[:16].replace("T", " "), "dong": du.get("dong") or "",
            "mo_ds": ["{0}: {1}".format(m.get("kenh") or "máy", m.get("viec")) for m in du.get("muc") or []
                      if m.get("tt") == MO][:6]}


def viec_nguoi(goc: str) -> List[Dict[str, str]]:
    """Việc CHỈ người làm được mà tự kiểm thấy (gộp theo kênh + việc)."""
    du = bao_cao_moi(goc)
    ra: Dict[str, Dict[str, str]] = {}
    for m in du.get("nguoi") or []:
        k = "tu-kiem:{0}:{1}".format(m.get("kenh"), m.get("can_lam") or (m.get("nguyen_nhan") or {}).get("bai") or m["loai"])
        ra.setdefault(k, {"khoa": k, "kenh": m.get("kenh") or "",
                          "chu": "Tự kiểm: {0} — {1}".format(m.get("viec"), str(m.get("bang_chung"))[:140]),
                          "goi_y": "→ " + str(m.get("can_lam") or (m.get("nguyen_nhan") or {}).get("cach") or
                                              "xem workspace/tu-kiem/<ngày>.json")})
    return list(ra.values())


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse  # noqa: PLC0415
    p = argparse.ArgumentParser(prog="python -X utf8 -m core.tu_kiem")
    p.add_argument("--thu", action="store_true")
    p.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    kq = nhip(os.path.abspath(a.goc), thu=a.thu)
    if a.json:
        print(json.dumps(kq, ensure_ascii=False, indent=1))
        return 0
    print(kq["dong"], "· mạng", kq["mang"], "lượt", "· lỗi bộ kiểm: " + json.dumps(kq["loi_kiem"], ensure_ascii=False)
          if kq["loi_kiem"] else "")
    for m in sorted(kq["muc"], key=lambda m: (m["tt"] == DAT, m["loai"], m["kenh"])):
        nn = (m.get("nguyen_nhan") or {})
        print("  [{0:<13}] {1:<9} {2:<10} {3} — {4}{5}{6}".format(
            NHAN.get(m["tt"], m["tt"]), m["loai"], m["kenh"] or "(máy)", m["viec"][:70], m["bang_chung"][:130],
            "\n{0}↳ nguyên nhân: {1} ({2}) {3}".format(" " * 18, nn.get("ten"), nn.get("bai") or "-",
                                                        str(nn.get("dong") or "")[:140]) if nn else "",
            "\n{0}↳ {1}".format(" " * 18, m["sua"]) if m.get("sua") else ""))
    if kq["bao"]:
        print("BÁO ĐỘNG GỘP:", kq["bao"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
