"""MÁY DANH SÁCH PHÁT CHỦ ĐỀ (DOM/CDP, 16/10/2026) — tạo + lấp + đọc lại danh sách phát theo kế hoạch
`CHANNEL/<k>/nghien-cuu/danh-sach-phat.json` (phần thuần + LLM: `core/danh_sach_phat.py`).

Một lượt = MỘT kênh:
  1. Kế hoạch (NGOÀI khe trình duyệt): chưa có → LLM lập (phễu chuẩn, Claude Max lùi ví); có rồi → xếp video mới.
  2. Phiên Chrome kênh qua khung chung `studio_may_dom.chay_phien` — cùng bảo vệ mọi máy DOM: khung cấm 02–07 + :55–:05,
     van IPv4, máy đăng dở, phiên đăng sắp tới / gói chờ tải (nhường), khoá máy `.khoa-may` (dựng / phụ đề / tải lên),
     khoá Chrome theo kênh, Chrome kênh đang mở → hoãn; UC ghim + giao diện vi TẠM, cuối phiên TRẢ hl=ja.
  3. Tên đã có trên kênh = bảng Studio «Danh sách phát» ∪ ô «Danh sách phát» của trang sửa một video (đọc, không tích). Đếm phân trang lớn hơn số tên
     đọc được → KHÔNG tạo (chống trùng). Tên trong kế hoạch đã có → DÙNG LẠI (không đổi tên/mô tả). Thiếu → tạo Công
     khai + mô tả (`thiet_lap_kenh_dom.Studio.tao_ds_phat`), mốc «đã bấm Tạo» ghi đĩa TRƯỚC khi bấm; lượt sau chưa thấy
     trong `CHO_TAO_LAI_PHUT` phút thì đợi, không tạo lại.
  4. Thêm video, tốt trước, CHỈ QUA STUDIO (`MayStudio.them`, 16/10/2026 — chủ: KHÔNG mở trang xem bằng tài khoản kênh:
     phát video như chủ kênh là không tự nhiên, bẩn số liệu, lại chậm): trang sửa `studio.youtube.com/video/<id>/edit` →
     ô «Danh sách phát» (bộ chọn đo sẵn của máy đăng: playlist_mo / playlist_muc / playlist_ten / playlist_xong) → tích
     ĐÚNG MỘT hàng khớp nguyên văn → Xong → Lưu (chỉ khi tiêu đề không lệch) → MỞ LẠI trang, đọc lại «đã tích». Hàng tích
     sẵn → «đã có», không bấm (bấm nữa là BỎ tích). Mỗi kết quả ghi đĩa ngay.
     (Chọn nhiều ở Nội dung → «Thêm vào danh sách phát» nhanh hơn nhưng bộ chọn chưa đo trên Studio thật — chưa dùng.)
  5. Đọc lại: bảng Studio (tên, chế độ, số video ≥ số đã xác nhận) → ảnh + so khớp.
Không xoá / đổi tên danh sách nào, không bỏ video khỏi danh sách, không đổi tiêu đề / mô tả / chế độ của video, không gõ
mật khẩu / 2FA (đăng xuất → ghi `dang_xuat` vào kế hoạch + báo động, thoát 20).

Chạy:  python vm/danh_sach_phat_dom.py --kenh TL4-T7 [--ke-hoach] [--bo-qua-khung]
Mã thoát: 0 xong · 10 hoãn / còn việc (đã tiến) · 20 cần người · 30 không có việc · 1 lỗi (không tiến được).
Skill D15 (`core/ky_nang.py`) gọi lệnh này; bộ tự kích hoạt: tối đa MỘT việc nặng mỗi lượt, hỏng 3 lần → nghỉ 24 giờ.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional

GOC = os.path.dirname(os.path.abspath(__file__))                 # vm/
GOC_TOOL = os.path.dirname(GOC)                                  # MyTool/
for _d in (GOC, GOC_TOOL):
    if _d not in sys.path:
        sys.path.append(_d)
import thiet_lap_kenh_dom as tl  # noqa: E402
import studio_may_dom as smd  # noqa: E402
from core import danh_sach_phat as dsp  # noqa: E402

MA_XONG, MA_LOI = 0, 1
MA_HOAN, MA_CAN_NGUOI, MA_KHONG_CAN = smd.MA_HOAN, smd.MA_CAN_NGUOI, smd.MA_KHONG_CAN
CHE_DO = "danh_sach_phat"
#: Phiên dự kiến (`studio_may_dom.DU_KIEN_PHUT`) ≤ 18 phút: bộ tự kích hoạt chạy phút :35 mà cửa :55–:05 phải trống
#: (`khung_gio_tron`) → mỗi phiên thêm có trần; còn việc thì thoát 10, lượt sau (giờ sau) làm tiếp.
TOI_DA_THEM_PHIEN = 25
NGAN_SACH_PHUT = 14
CHO_TAO_LAI_PHUT = 30

#: Hàng bảng «Danh sách phát» của Studio: tên, chữ cả hàng (chế độ, số video), các liên kết (mã danh sách), chữ TỪNG Ô
#: (`div[role=cell]`) + tên CỘT (`ytcp-table-header [role=columnheader]`). Đo 16/10/2026 (Studio vi): cột «Danh sách
#: phát | Loại | Chế độ hiển thị | Lần cập nhật gần nhất | Số lượng video | Lượt xem» — số CUỐI hàng là LƯỢT XEM, không
#: phải số video (đọc nhầm → "0 video (Studio)"); ảnh nhỏ đầu hàng còn in số video lần nữa.
_JS_HANG = "(() => {" + tl._JS_CHUNG + r"""
  const s = q('ytcp-playlist-section-content') || q('ytcp-playlist-section'); if (!s) return null;
  const cot = qa('ytcp-table-header [role=columnheader], [role=columnheader]', s).filter(hien).map(c => (c.innerText || '').trim());
  return qa('ytcp-playlist-row', s).filter(hien).map(r => {
    const a = q('h3.playlist-title a, a.playlist-title-link, #video-title', r);
    return {ten: a ? (a.innerText || '').trim() : '', chu: (r.innerText || '').trim().slice(0, 400),
            o: qa('[role=cell]', r).map(c => (c.innerText || '').trim().slice(0, 120)), cot: cot.slice(0, 12),
            href: qa('a[href]', r).map(x => x.getAttribute('href') || '').slice(0, 8)}; });
})()"""
#: Cột «Số lượng video» (vi / en / ja).
RE_COT_SO_VIDEO = re.compile(r"^(số (lượng )?video|video count|videos?|動画(の)?数|動画)$", re.I)

SO_LAN_DOC_TICH = 10                     # dò trạng thái tích sau khi bấm (× 0,5 giây)


def duong_ket(kenh: str) -> str:
    return os.path.join(smd.thu_muc_so(), kenh + ".danh-sach-phat.json")


# ═══════════════════════════ HÀM THUẦN (có test) ═════════════════════════════
def co_ten(ten_kenh: Any, ten: str) -> bool:
    k = dsp.chuan_ten(ten).casefold()
    return any(dsp.chuan_ten(x).casefold() == k for x in ten_kenh or ())


def quyet_tao(d: Dict[str, Any], ten_kenh: Any, luc: float) -> str:
    """Danh sách CHƯA tạo → "co_san" (tên đã có trên kênh: dùng lại) | "cho" (vừa bấm Tạo < CHO_TAO_LAI_PHUT phút mà
    chưa thấy — đợi, không tạo trùng) | "tao"."""
    if co_ten(ten_kenh, d.get("ten")):
        return "co_san"
    bam = dsp._doc_luc(d.get("luc_bam_tao"))  # noqa: SLF001
    if bam and luc - bam.timestamp() < CHO_TAO_LAI_PHUT * 60:
        return "cho"
    return "tao"


def viec_them(ke: Dict[str, Any]) -> List[tuple]:
    """[(danh sách, mã video)] còn chờ thêm, theo thứ tự kế hoạch (danh sách mạnh trước, video tốt trước)."""
    bo = set((ke.get("video_bo") or {}).keys())
    return [(d, v) for d in ke.get("danh_sach") or [] if d.get("trang_thai") == dsp.DA_TAO and not dsp.la_cua_chu(d)
            for v in d.get("video") or [] if v not in (d.get("da_them") or []) and v not in bo]


def ma_danh_sach(href: Any) -> str:
    for h in href or ():
        m = re.search(r"(?:/playlist/|[?&]list=)([A-Za-z0-9_-]{12,})", str(h or ""))
        if m:
            return m.group(1)
    return ""


def _so(x: Any) -> Optional[int]:
    s = re.sub(r"[\s.,  ]", "", str(x or ""))
    return int(s) if re.fullmatch(r"\d{1,7}", s) else None


def so_video_hang(chu: Any, o: Any = None, cot: Any = None) -> Optional[int]:
    """Số video của một hàng bảng Studio. Có chữ từng ô + tên cột → ô của cột «Số lượng video». Không có → chữ cả hàng:
    các dòng chỉ là số; ≥ 2 dòng thì số video là dòng ÁP CHÓT (dòng cuối = cột «Lượt xem»; đo 16/10/2026), 1 dòng thì
    chính nó (khuôn cũ không có cột lượt xem)."""
    o, cot = list(o or []), [str(c or "").strip() for c in cot or []]
    i = next((k for k, c in enumerate(cot) if RE_COT_SO_VIDEO.match(c)), None)
    if i is not None and len(o) == len(cot):
        return _so(o[i])
    so = [x.strip() for x in str(chu or "").splitlines() if _so(x.strip()) is not None]
    if not so:
        return None
    return _so(so[-2] if len(so) >= 2 else so[-1])


def gop_ten(*ds: Any) -> List[str]:
    """Gộp các danh sách tên, bỏ trùng theo `chuan_ten` + casefold (NFKC: «｜» toàn khổ = «|» nửa khổ), giữ bản ĐẦU
    TIÊN gặp (bảng Studio trước — đúng chữ như trên kênh)."""
    ra: List[str] = []
    da: set = set()
    for d in ds:
        for x in d or ():
            k = dsp.chuan_ten(x).casefold()
            if k and k not in da:
                da.add(k)
                ra.append(str(x).strip())
    return ra


def ma_thoat(ket: Dict[str, Any], ke: Dict[str, Any]) -> int:
    """0 hết việc · 10 còn việc mà phiên đã tiến (lượt sau làm tiếp, không tính hỏng) · 1 còn việc, không tiến."""
    vc = dsp.viec_con(ke)
    if not vc["chua_tao"] and not vc["cho_them"]:
        return MA_XONG
    return MA_HOAN if (ket.get("tao") or [x for x in ket.get("them") or [] if x.get("kq") == "xac_nhan"]) else MA_LOI


# ═══════════════════════════ DOM ════════════════════════════════════════════
def _url_ds(S) -> str:
    return "https://studio.youtube.com/channel/{0}/content/playlists".format(S.uc)


def doc_bang_studio(S, han: float = 20.0) -> Dict[str, Any]:
    """Trang Studio «Danh sách phát»: {ten, dem, hang}. Không đọc được → LoiMuc (không bao giờ coi là trống)."""
    S.mo(_url_ds(S), "ytcp-playlist-section")
    du, het = None, time.monotonic() + han
    while True:
        du = S.js(tl._JS_DEM_DS_PHAT)                                # noqa: SLF001
        if (du and (du.get("hang") or du.get("trong"))) or time.monotonic() >= het:
            break
        S.ngu(1.5)
    if not isinstance(du, dict):
        raise tl.LoiMuc("không đọc được bảng danh sách phát Studio")
    hang = S.js(_JS_HANG) or []
    ten = gop_ten([str(x) for x in du.get("ten") or []], [h["ten"] for h in hang if h.get("ten")])
    return {"ten": ten, "dem": tl.dem_ds_phat(du), "hang": hang}


def ten_tren_kenh(S, may, ke: Dict[str, Any], ghi) -> List[str]:
    """Bảng Studio ∪ ô «Danh sách phát» trang sửa một video của kế hoạch (KHÔNG tích). Studio đếm nhiều hơn số tên đọc
    được → LoiMuc."""
    b = doc_bang_studio(S)
    if b["dem"] is not None and b["dem"] > len(b["ten"]):
        raise tl.LoiMuc("Studio có {0} danh sách phát mà chỉ đọc được {1} tên — không tạo mù (chống trùng)".format(
            b["dem"], len(b["ten"])))
    ten = list(b["ten"])
    vid = next((v for d in ke.get("danh_sach") or [] for v in d.get("video") or []), "")
    if vid:
        h = may.doc_ten(vid)
        if h is not None:
            ten = gop_ten(ten, [x for x in h if x])    # ô trang sửa trả tên đã NFKC («|») — cùng danh sách, không kể 2 lần
        else:
            ghi("ô «Danh sách phát» trang sửa không đọc được — chỉ dựa bảng Studio")
    ten = gop_ten(ten)
    ghi("danh sách phát đang có trên kênh: {0}".format(" ¦ ".join(ten) or "—"))
    return ten


def tao_thieu(S, ke: Dict[str, Any], ten_kenh: List[str], luu: Callable[[], None], ghi, ket: Dict[str, Any]) -> None:
    for d in [d for d in ke.get("danh_sach") or [] if d.get("trang_thai") != dsp.DA_TAO]:
        q = quyet_tao(d, ten_kenh, time.time())
        if q == "co_san":
            d.update(trang_thai=dsp.DA_TAO, tai_dung=not d.get("luc_bam_tao"), luc_tao=dsp._luc())  # noqa: SLF001
            if d["tai_dung"]:                                        # có từ trước kế hoạch = CỦA CHỦ: để yên
                dsp.chuan_cua_chu(ke)
            ghi("«{0}» đã có trên kênh — {1}".format(d["ten"], "CỦA CHỦ: chỉ khớp tên lúc tải lên, không thêm video"
                                                      if d["tai_dung"] else "lần bấm Tạo trước đã lên"))
            ket["tao"].append({"ten": d["ten"], "kq": "dung_lai" if d["tai_dung"] else "da_len"})
            luu()
            continue
        if q == "cho":
            ket["loi"].append("«{0}»: vừa bấm Tạo lúc {1} mà chưa thấy — đợi lượt sau".format(d["ten"], d["luc_bam_tao"]))
            continue
        try:
            S.mo(_url_ds(S), "ytcp-playlist-section")
            S.ngu(2.0)
            d["luc_bam_tao"] = dsp._luc()                            # noqa: SLF001 — ghi TRƯỚC khi bấm: chết giữa chừng
            luu()                                                    # thì lượt sau không tạo trùng
            S.tao_ds_phat(d["ten"], d.get("mo_ta") or "")
            S.ngu(3.0)
            b = doc_bang_studio(S)
        except tl.CanNguoi:
            raise
        except Exception as e:  # noqa: BLE001
            d["loi"], d["loi_cuoi"] = int(d.get("loi") or 0) + 1, str(e)[:200]
            ket["loi"].append("tạo «{0}»: {1}".format(d["ten"], str(e)[:160]))
            S.chup("dsp-tao-hong")
            luu()
            continue
        if co_ten(b["ten"], d["ten"]):
            d.update(trang_thai=dsp.DA_TAO, luc_tao=dsp._luc(), tai_dung=False)  # noqa: SLF001
            ten_kenh.append(d["ten"])
            ket["tao"].append({"ten": d["ten"], "kq": "tao"})
            ghi("đã tạo danh sách phát «{0}» (Công khai, có mô tả) — đọc lại thấy trên Studio".format(d["ten"]))
        else:
            ket["loi"].append("«{0}»: bấm Tạo xong chưa thấy trên Studio — lượt sau đọc lại".format(d["ten"]))
        luu()


def them_video(S, md, agent, kenh: str, ke: Dict[str, Any], may, luu, ghi, ket: Dict[str, Any], t0: float,
               ngu=time.sleep) -> None:
    hong_ds: set = set()
    dem = 0
    for d, vid in viec_them(ke):
        if d["ma"] in hong_ds:
            continue
        if dem >= TOI_DA_THEM_PHIEN or time.monotonic() - t0 > NGAN_SACH_PHUT * 60:
            ket["dung"] = "hết suất phiên ({0} lần thêm / {1} phút) — lượt sau làm tiếp".format(dem, NGAN_SACH_PHUT)
            break
        try:
            smd._kiem_dung(agent, kenh)                              # noqa: SLF001 — agent đòi Chrome / khung cấm / việc đăng
            r = tl.khung_gio_tron(time.time(), 3 + len(ke.get("danh_sach") or []))   # chừa giờ đọc lại trước :55
            if r:
                raise tl.Hoan(r)
        except tl.Hoan as h:
            ket["dung"] = str(h)
            break
        if dem:
            ngu(random.uniform(2.0, 5.0))
        kq = may.them(vid, d["ten"])
        dem += 1
        if str(kq.get("ket") or "").startswith("loi:tim_ds"):      # ô không có tên này: lỗi của DANH SÁCH, không
            d["loi"], d["loi_cuoi"] = int(d.get("loi") or 0) + 1, str(kq["ket"])[:200]   # của video — dừng danh sách
            hong_ds.add(d["ma"])
            ket["loi"].append("«{0}»: {1}".format(d["ten"], str(kq["ket"])[:160]))
            luu()
            continue
        r = dsp.ghi_ket_video(ke, d, vid, str(kq.get("ket") or ""))
        ket["them"].append({"ds": d["ten"], "video": vid, "ket": kq.get("ket"), "kq": r, "anh": kq.get("anh", "")})
        if r != "xac_nhan":
            ket["loi"].append("{0} → «{1}»: {2}{3}".format(vid, d["ten"], str(kq.get("ket"))[:140], " (BỎ video)" if r == "bo" else ""))
        luu()


def doc_lai(S, ke: Dict[str, Any], ghi) -> Dict[str, Any]:
    """Đọc lại CHỈ trên Studio: bảng «Danh sách phát» (+ ảnh) — có tên, Công khai, số video ≥ số đã xác nhận."""
    ra: Dict[str, Any] = {"luc": dsp._luc(), "ds": {}, "anh": []}  # noqa: SLF001
    try:
        b = doc_bang_studio(S)
        ra["anh"].append(S.bang_chung("dsp-doc-lai-studio").get("anh", ""))
    except Exception as e:  # noqa: BLE001
        ra["loi"] = "bảng Studio: {0}".format(str(e)[:160])
        return ra
    for d in [d for d in ke.get("danh_sach") or [] if d.get("trang_thai") == dsp.DA_TAO]:
        h = next((h for h in b["hang"] if dsp.chuan_ten(h.get("ten")) == dsp.chuan_ten(d["ten"])), None)
        so = so_video_hang((h or {}).get("chu"), (h or {}).get("o"), (h or {}).get("cot"))
        o: Dict[str, Any] = {"thay_studio": h is not None or co_ten(b["ten"], d["ten"]), "so_video_studio": so,
                             "ma": ma_danh_sach((h or {}).get("href")), "xac_nhan": len(d.get("da_them") or [])}
        o["cong_khai"] = bool(re.search(r"công khai|public|公開", str((h or {}).get("chu") or ""), re.I)) if h else None
        o["khop"] = bool(o["thay_studio"] and (so is None or so >= o["xac_nhan"]))
        d["doc_lai"] = dict(o, luc=ra["luc"])
        ra["ds"][d["ten"]] = o
        ghi("đọc lại «{0}»: Studio {1} · {2} · {3} video (Studio) / {4} đã xác nhận{5}".format(
            d["ten"], "thấy" if o["thay_studio"] else "KHÔNG thấy", "Công khai" if o["cong_khai"] else "chế độ ?", so,
            o["xac_nhan"], "" if o["khop"] else " · LỆCH"))
    return ra


# ═══════════════════════════ THÊM QUA STUDIO ════════════════════════════════
class LoiThem(Exception):
    def __init__(self, buoc: str, ly_do: str):
        super().__init__("{0}: {1}".format(buoc, ly_do))
        self.buoc, self.ly_do = buoc, ly_do


def khop_hang(chu: Any, ten: str) -> bool:
    """Chữ một hàng của ô «Danh sách phát» khớp NGUYÊN VĂN tên (cả khối hoặc một dòng; NFKC, gộp khoảng trắng)."""
    dich = dsp.chuan_ten(ten)
    return dich in [dsp.chuan_ten(chu)] + [dsp.chuan_ten(x) for x in str(chu or "").splitlines()]


class MayStudio:
    """Thêm video vào danh sách phát trên TRANG SỬA VIDEO của Studio (không bao giờ mở trang xem). Bộ chọn dùng chung
    với hộp danh sách phát của máy đăng (`vm/studio-selectors.json`). Phiên phải mở với `cho_luu=True` (nút Lưu của
    trang sửa nằm trong `cam_bam` mặc định). `them` trả {ket: ok | da_co | loi:<bước>: <lý do>}."""

    def __init__(self, S, ghi, ngu=None):
        self.S, self.st, self.ghi = S, S.st, ghi
        self.ngu = ngu or S.ngu

    def _mo(self, vid: str) -> None:
        smd._mo_trang_sua(self.S, vid)                               # noqa: SLF001 — đăng xuất → DangXuat

    def _mo_hop(self) -> None:
        if not self.st.co("playlist_muc"):
            self.st.bam("playlist_mo", hau_dieu_kien=lambda: self.st.co("playlist_muc"), han_hau=15)

    def _dong_hop(self) -> None:
        if self.st.co("playlist_xong"):
            self.st.bam("playlist_xong", hau_dieu_kien=lambda: not self.st.co("playlist_muc"), han_hau=10)
        elif self.st.co("playlist_muc"):
            self.st.phim("Escape")
            self.ngu(1)

    def _bo_thay_doi(self) -> None:
        """Đóng ô (nếu mở) và bỏ mọi thay đổi chưa lưu — rời trang không lưu nhầm."""
        try:
            if self.st.co("playlist_muc"):
                self._dong_hop()
        except Exception:  # noqa: BLE001
            pass
        if not smd.luu_dang_tat(self.S):
            smd.huy_thay_doi(self.S, self.ghi)

    def _hang(self) -> List[Dict[str, Any]]:
        pt0 = self.st.tim("playlist_muc", han=5)
        if not pt0:
            return []
        ra = []
        for i in range(int(pt0.get("so") or 1)):
            pt = self.st.tim("playlist_muc", han=0, thu=i)
            if not pt:
                continue
            chu = self.st.doc_chu(pt) or ""
            if not str(chu).strip():                                 # ô tick không có chữ — tên ở li bao nó
                tp = self.st.tim("playlist_ten", han=0, thu=i)
                chu = (self.st.doc_chu(tp) if tp else "") or ""
            ac = str(self.st.doc_thuoc_tinh(pt, "aria-checked") or "")
            ra.append({"i": i, "pt": pt, "ten": str(chu), "chon": True if ac == "true" else False if ac == "false" else None})
        return ra

    def doc_ten(self, vid: str) -> Optional[List[str]]:
        """Tên mọi danh sách phát trong ô của trang sửa `vid` (không tích); hỏng → None."""
        try:
            self._mo(vid)
            self._mo_hop()
            ten = [dsp.chuan_ten(str(h["ten"]).strip().splitlines()[0]) for h in self._hang() if str(h["ten"]).strip()]
            self._bo_thay_doi()
            return [t for t in ten if t]
        except (smd.DangXuat, tl.CanNguoi):
            raise
        except Exception as e:  # noqa: BLE001
            self.ghi("đọc ô danh sách phát {0} hỏng: {1}".format(vid, str(e)[:120]))
            try:
                self._bo_thay_doi()
            except Exception:  # noqa: BLE001
                pass
            return None

    def them(self, vid: str, ten: str) -> Dict[str, Any]:
        kq: Dict[str, Any] = {"video_id": vid, "danh_sach_phat": ten, "ket": "", "cach": "studio_trang_sua"}
        buoc = "mo"
        try:
            self._mo(vid)
            td0 = smd.mdd_chuan(self.st.doc_chu("tieu_de") or "")
            if not smd.luu_dang_tat(self.S):                          # trang có thay đổi lạ từ trước → bỏ, không lưu nhầm
                smd.huy_thay_doi(self.S, self.ghi)
            buoc = "tim_ds"
            self._mo_hop()
            hang = self._hang()
            khop = [h for h in hang if khop_hang(h["ten"], ten)]
            if len(khop) != 1:
                self._bo_thay_doi()
                raise LoiThem("tim_ds", "{0} hàng tên «{1}» trong ô danh sách phát (có: {2})".format(
                    len(khop), ten, " | ".join(dsp.chuan_ten(h["ten"])[:30] for h in hang[:12]) or "—"))
            h = khop[0]
            if h["chon"] is None:
                self._bo_thay_doi()
                raise LoiThem("trang_thai", "không đọc được trạng thái tích của «{0}»".format(ten))
            if h["chon"]:
                self._bo_thay_doi()
                kq["ket"] = "da_co"
                self.ghi("«{0}» đã có video {1} — không bấm (bấm nữa là bỏ tích)".format(ten, vid))
                return kq
            buoc = "tich"
            self.st.bam(h["pt"])                                     # MỘT lần duy nhất
            tich = ""
            for _ in range(SO_LAN_DOC_TICH):
                self.ngu(0.5)
                pt = self.st.tim("playlist_muc", han=0, thu=h["i"])
                tich = str(self.st.doc_thuoc_tinh(pt, "aria-checked") or "") if pt else ""
                if tich == "true":
                    break
            if tich != "true":
                self._bo_thay_doi()
                raise LoiThem("tich", "bấm «{0}» một lần mà ô chưa tích ({1!r}) — đã huỷ, không lưu".format(ten, tich))
            self._dong_hop()
            buoc = "luu"
            if smd.mdd_chuan(self.st.doc_chu("tieu_de") or "") != td0:
                smd.huy_thay_doi(self.S, self.ghi)
                raise LoiThem("luu", "tiêu đề trên trang sửa lệch — đã huỷ, không lưu")
            if smd.luu_dang_tat(self.S):
                raise LoiThem("luu", "tích xong mà nút Lưu không sáng")
            self.st.bam("sua_luu", hau_dieu_kien=lambda: smd.luu_dang_tat(self.S), han_hau=smd.CHO_LUU_GIAY)
            self.ngu(3)
            buoc = "doc_lai"
            self._mo(vid)
            self._mo_hop()
            k2 = [x for x in self._hang() if khop_hang(x["ten"], ten)]
            sau = k2[0]["chon"] if len(k2) == 1 else None
            self._bo_thay_doi()
            kq["tich_mo_lai"] = sau
            if sau is not True:
                raise LoiThem("doc_lai", "mở lại trang sửa: «{0}» {1}".format(
                    ten, "KHÔNG tích (YouTube chưa lưu?)" if sau is False else "không đọc được trạng thái"))
            kq["ket"] = "ok"
            self.ghi("đã thêm {0} vào «{1}» qua Studio (trang sửa → Lưu); mở lại trang: đã tích".format(vid, ten))
        except (smd.DangXuat, tl.CanNguoi):
            raise
        except LoiThem as e:
            kq["ket"] = "loi:{0}: {1}".format(e.buoc, e.ly_do)
        except Exception as e:  # noqa: BLE001 — lỗi CDP/bấm: ghi bước, bỏ thay đổi, không chết im lặng
            kq["ket"] = "loi:{0}: {1}".format(buoc, str(e)[:200])
            try:
                self._bo_thay_doi()
            except Exception:  # noqa: BLE001
                pass
        if kq["ket"].startswith("loi"):
            self.ghi("thêm {0} → «{1}»: {2}".format(vid, ten, kq["ket"]))
            kq["anh"] = self.S.bang_chung("dsp-them-loi-" + vid).get("anh", "")
        return kq


# ═══════════════════════════ CHẠY ═══════════════════════════════════════════
def ten_da_biet(goc: str, kenh: str) -> List[str]:
    """Tên danh sách phát đã biết của kênh (không mở Chrome): lần kiểm thương hiệu (bảng Studio) + sổ học hộp Lưu của
    kéo chéo — gợi ý cho LLM (dùng lại đúng tên nếu hợp, còn lại đặt tên khác)."""
    ten: List[str] = []
    try:
        with open(tl.duong_thuong_hieu(kenh), encoding="utf-8") as tep:
            ten += [str(x) for x in ((json.load(tep) or {}).get("ds_phat") or {}).get("ten") or []]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        from core import keo_cheo  # noqa: PLC0415
        ten += [str(x) for x in (keo_cheo.doc_ds_kenh(keo_cheo.thu_muc_mac_dinh(goc)).get(kenh) or {}).get("ten") or []]
    except Exception:  # noqa: BLE001
        pass
    return [t for t in dict.fromkeys(dsp.chuan_ten(x) for x in ten) if t and t.lower() not in ("watch later", "xem sau")]


def _goi_vi(ghi):
    from core.cum_y_nghia import goi_vi  # noqa: PLC0415
    return goi_vi(GOC_TOOL, ghi)


def _bao_dang_xuat(kenh: str, ke: Dict[str, Any]) -> None:
    try:
        from core import bao_dong  # noqa: PLC0415
        bao_dong.bao_dong("danh_sach_phat_dang_xuat", "Chrome kênh {0} bị đăng xuất YouTube — máy danh sách phát dừng".format(kenh),
                          "Đăng nhập lại Chrome Portable của kênh (máy không gõ mật khẩu). Máy tự thử lại sau {0:.0f} giờ.".format(
                              dsp.GIO_CHO_DANG_NHAP), goc=GOC_TOOL, kenh=kenh)
    except Exception:  # noqa: BLE001
        pass


def chay(kenh: str, ghi, *, chi_ke_hoach: bool = False, bo_qua_khung: bool = False, goi=None, phien=None,
         goc: str = GOC_TOOL) -> int:
    if dsp.ten_yaml(goc, kenh):
        ghi("{0}: kenh.yaml đã khai danh_sach_phat_kenh — việc của K14, bỏ".format(kenh))
        return MA_KHONG_CAN
    ok, ly = dsp.duoc_phat(goc, kenh)
    if not ok:
        ghi("{0}: {1} — bỏ".format(kenh, ly))
        return MA_KHONG_CAN
    try:
        ke, viec = dsp.cap_nhat_ke_hoach(goc, kenh, goi if goi is not None else _goi_vi(ghi), ds_co=ten_da_biet(goc, kenh),
                                         log=ghi)
    except ValueError as e:
        ghi("{0}: chưa lập được kế hoạch: {1}".format(kenh, e))
        return MA_KHONG_CAN
    except Exception as e:  # noqa: BLE001
        ghi("{0}: kế hoạch danh sách phát hỏng: {1}".format(kenh, str(e)[:300]))
        return MA_LOI
    ghi("{0}: kế hoạch — {1}".format(kenh, viec or "không đổi"))
    dsp.in_ke_hoach(ke, ghi)
    if chi_ke_hoach:
        return MA_XONG
    vc = dsp.viec_con(ke)
    if not vc["chua_tao"] and not vc["cho_them"]:
        ghi("{0}: không có việc trên YouTube".format(kenh))
        return MA_KHONG_CAN

    def luu():
        dsp.ghi(goc, kenh, ke)

    def lam(S, md, agent):
        t0 = time.monotonic()
        ket: Dict[str, Any] = {"luc": dsp._luc(), "tao": [], "them": [], "loi": [], "dung": ""}  # noqa: SLF001
        may = MayStudio(S, ghi)
        try:
            ten = ten_tren_kenh(S, may, ke, ghi)
            tao_thieu(S, ke, ten, luu, ghi, ket)
            them_video(S, md, agent, kenh, ke, may, luu, ghi, ket, t0)
        except tl.LoiMuc as e:
            ket["loi"].append(str(e)[:200])
            S.chup("dsp-loi")
        ket["doc_lai"] = doc_lai(S, ke, ghi)
        luu()
        return ket

    ma, kq = (phien or smd.chay_phien)(kenh, ghi, lam, CHE_DO, bo_qua_khung=bo_qua_khung, cho_luu=True)
    if ma == MA_CAN_NGUOI:
        if kq == "dang-xuat":
            ke["dang_xuat"] = {"luc": dsp._luc(), "ly_do": "Chrome kênh bị đăng xuất YouTube"}  # noqa: SLF001
            luu()
            _bao_dang_xuat(kenh, ke)
        return ma
    if ma != MA_XONG or not isinstance(kq, dict):
        return ma
    ke.pop("dang_xuat", None)
    luu()
    ma = ma_thoat(kq, ke)
    kq.update(ma_thoat=ma, viec_con=dsp.viec_con(ke))
    smd._ghi_json(duong_ket(kenh), kq)                              # noqa: SLF001
    ghi("{0}: xong phiên — tạo {1} · xác nhận {2} video · lỗi {3}{4} → mã {5}".format(
        kenh, len(kq["tao"]), sum(1 for x in kq["them"] if x["kq"] == "xac_nhan"), len(kq["loi"]),
        " · dừng: " + kq["dung"] if kq["dung"] else "", ma))
    return ma


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Máy danh sách phát chủ đề (một kênh mỗi lượt)")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--ke-hoach", action="store_true", help="chỉ lập/cập nhật kế hoạch (LLM), không mở Chrome")
    ap.add_argument("--bo-qua-khung", action="store_true", help="bỏ khung giờ cấm (vẫn giữ mọi bảo vệ khác)")
    a = ap.parse_args(argv)
    ghi = smd._nhat_ky(a.kenh)                                      # noqa: SLF001
    return chay(a.kenh, ghi, chi_ke_hoach=a.ke_hoach, bo_qua_khung=a.bo_qua_khung)


if __name__ == "__main__":
    sys.exit(main())
