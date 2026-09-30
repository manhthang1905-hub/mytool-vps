"""Ngữ cảnh kênh cho các công thức chọn nguồn — `NguCanh`.

═══ GIAO DIỆN ĐÃ CHỐT (30/09/2026, agent A) — agent B/C chỉ ĐỌC, không đổi tên ═══

    nc = ngu_canh.dung(goc, ma_kenh, *, co_v7, loai_tru=(), da_lam_tieu_de=(), log=None,
                       bay_gio=None, nguong_giong=0.80,
                       cham_v7=None, doc_danh_sach=None, cham_vph=None)

  Định danh ........ nc.goc, nc.ma_kenh, nc.bay_gio (datetime), nc.nhom, nc.tep
                     nc.cai(khoa, mac_dinh)          một khoá kenh.yaml (bool đọc được "false"/"0"…)
                     nc.cho_phep_tep_gia  bool — kenh.yaml `cho_phep_tep_gia` (30/09/2026): kênh nhắm
                                     tệp NGƯỜI GIÀ → công thức KHÔNG loại nguồn chỉ vì mốc tuổi
                                     (`phan_tuyen.cho_phep_tep_gia`); mặc định False
  Ngách/thị trường . nc.ngach        HoSoNgach (core.ho_so_ngach.doc_ngach; hỏng → HoSoNgach() rỗng)
                     nc.thi_truong   dict: quoc_gia, ngon_ngu, mui_gio, khung_gio_dang, phut_muc_tieu,
                                     bia_toi_da_ky_tu, bac_lam_tron_view, ctr_trang_chu_muc_tieu, mua_vu,
                                     bac_view_manh, tran_vuot (bảng Một nút)
                                     (kenh.yaml > ngach.yaml `thi_truong:` > MAC_DINH_THI_TRUONG; None = nơi
                                     gọi dùng hằng của chính nó)
  Giai đoạn ........ nc.giai_doan    "moi" | "dang_len" | "kiem_tien"
                     nc.ypp          {"sub", "gio", "thieu": "sub"|"gio"|"ca_hai"|"", "nguon"}
                     nc.luat_chon    list[str] — luật chọn nguồn THEO NGHĨA (kenh.yaml > ngach.yaml
                                     `luat_chon`), cho mọi lời nhắc AI chọn/lọc nguồn; [] = ngách chưa khai
  Dữ liệu học ...... nc.co_v7 (bool), nc.so_video_48h (int)
                     nc.bai_hoc      list[BaiHoc] — core.chien_luoc.bai_hoc.doc(goc, kenh, "chon") (agent B)
                     nc.ket_qua(ngay=28) / nc.ket_qua_cong_thuc
                                     {ct: {n, thang, truot, …}} — core.chien_luoc.ket_qua.thong_ke (agent B)
                     nc.so_luot_hom_nay  số lượt đã mở trong sổ tu-chay/<ngày>.json (cho thăm dò tất định)
                     nc.cum_da_thu   set mã cụm kênh ĐÃ làm (tiêu đề đã làm → V7 `cum_cua_tieu_de`, nhãn AI trước)
                     nc.cum_cua(td)  list mã cụm của một tiêu đề (cùng bộ cụm V7 của kênh)
  Bộ lọc ........... nc.loai_tru, nc.da_lam_tieu_de, nc.nguong_giong
                     nc.loc(ds)      bỏ dòng thiếu mã / trong loai_tru / trùng tiêu đề đã làm / trùng tiêu đề
                                     dòng trên. Chạy lại bao nhiêu lần cũng ra cùng kết quả; mỗi tiêu đề
                                     trùng chỉ log MỘT lần cho cả ngữ cảnh.
  Mục tiêu ......... nc.muc_tieu()   chuỗi 3 dòng cho mọi lời nhắc
  Seam bài kiểm .... nc.cham_v7, nc.doc_danh_sach, nc.cham_vph (None = hàm thật)
  Nhật ký .......... nc.ghi(dong)

═══ DÒNG CHUẨN (mỗi công thức `cham(nc)` trả list các dict này, mạnh nhất trước) ═══

  Khoá cũ (giữ nguyên tên — trạm, biên tập viên, sổ lượt đọc thẳng):
    nguon (= TEN của công thức), ma, link, tieu_de, kenh (kênh NGUỒN), diem (thang riêng của công
    thức), loai, view, vph, dot_bien, tuoi_gio, cum, tuyen, ly_do[]
  Khoá riêng của công thức giữ ở gốc dòng như hôm nay (diem_cum, thua_huong, diem_anh_em, anh_em…).
  Khoá bộ điều phối GẮN THÊM khi kênh khai `chien_luoc` (trộn nhiều công thức):
    cong_thuc (= TEN công thức đã ra dòng này), tham_do (bool),
    tin_hieu{cong_thuc_khac: [..], cum_chua_thu: [..] (kênh "moi", lượt thăm dò)}
  Bí danh chỉ trong tài liệu: kenh_nguon = kenh, ti_so_dot_bien = dot_bien.

Mọi trường nặng (ngách, YPP, video 48h, bài học, kết quả) là THUỘC TÍNH LƯỜI: chỉ đọc đĩa khi có
người hỏi, hỏng thì rỗng. Nên dựng `NguCanh` ở mỗi lượt xếp hạng (cả trạm `/loi-thoai/can-lay`)
không tốn thêm gì cho kênh chưa khai `chien_luoc`.
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .. import doi_thu_kenh as so
from .. import trung_tieu_de

GIAI_DOAN = ("moi", "dang_len", "kiem_tien")
YPP_SUB = 1000
YPP_GIO = 4000

#: Mặc định thị trường khi cả kenh.yaml lẫn ngach.yaml đều không khai. `None` = "không có mặc
#: định chung — nơi gọi giữ hằng số của chính nó" (vd. khung giờ đăng nằm ở kenh.yaml từng kênh).
MAC_DINH_THI_TRUONG: Dict[str, Any] = {
    "quoc_gia": "JP", "ngon_ngu": "ja", "mui_gio": "Asia/Tokyo", "khung_gio_dang": None,
    "phut_muc_tieu": None, "bia_toi_da_ky_tu": None, "bac_lam_tron_view": None,
    "ctr_trang_chu_muc_tieu": 5.0, "mua_vu": [],
    # Bảng Một nút (core/chien_luoc/mot_nut.py): None = hằng cũ (100.000 view, vượt ×25 — cỡ thị trường Nhật).
    "bac_view_manh": None, "tran_vuot": None,
}


def _sai(gt: Any) -> bool:
    return str(gt).strip().lower() in ("false", "0", "khong", "không", "no", "off", "")


@dataclass
class NguCanh:
    goc: str
    ma_kenh: str
    co_v7: bool = False
    loai_tru: frozenset = frozenset()
    da_lam_tieu_de: Tuple[Tuple[str, str], ...] = ()
    nguong_giong: float = trung_tieu_de.NGUONG_GIONG_TIEU_DE_MAC_DINH
    bay_gio: _dt.datetime = field(default_factory=_dt.datetime.now)
    log: Optional[Callable[[str], None]] = None
    cham_v7: Optional[Callable[..., Any]] = None
    doc_danh_sach: Optional[Callable[..., Any]] = None
    cham_vph: Optional[Callable[..., Any]] = None
    # Bộ nhớ của `loc` — kết quả so tiêu đề đã làm (theo tiêu đề thô) và tiêu đề đã log.
    _nho_trung: Dict[str, Any] = field(default_factory=dict, repr=False)
    _da_bao: set = field(default_factory=set, repr=False)
    _nho_ket_qua: Dict[int, Dict[str, Any]] = field(default_factory=dict, repr=False)

    # ── nhật ký, cấu hình kênh ──────────────────────────────────────────────
    def ghi(self, dong: str) -> None:
        if self.log is not None:
            self.log(dong)

    @cached_property
    def _kenh_yaml(self) -> Dict[str, Any]:
        try:
            from ..kenh import TEP_KENH, doc_yaml, duong_kenh  # noqa: PLC0415

            return doc_yaml(os.path.join(duong_kenh(self.goc, self.ma_kenh), TEP_KENH)) or {}
        except Exception:  # noqa: BLE001
            return {}

    def cai(self, khoa: str, mac_dinh: Any = None) -> Any:
        """Như `tu_chay._cai_kenh` (cùng luật đọc bool), nhưng đọc kenh.yaml MỘT lần cho cả ngữ cảnh."""
        gt = self._kenh_yaml.get(khoa, mac_dinh)
        if isinstance(mac_dinh, bool) and isinstance(gt, str):
            return not _sai(gt)
        return gt if gt is not None else mac_dinh

    @cached_property
    def nhom(self) -> str:
        return str(self.cai("nhom", "") or "").strip()

    @cached_property
    def tep(self) -> str:
        return str(self.cai("tep", "") or "").strip()

    @cached_property
    def cho_phep_tep_gia(self) -> bool:
        return self.cai("cho_phep_tep_gia", False) is True

    # ── ngách, thị trường ───────────────────────────────────────────────────
    @cached_property
    def ngach(self) -> Any:
        try:
            from .. import ho_so_ngach  # noqa: PLC0415

            return ho_so_ngach.doc_ngach(self.goc, self.ma_kenh)
        except Exception:  # noqa: BLE001
            try:
                from ..ho_so_ngach import HoSoNgach  # noqa: PLC0415

                return HoSoNgach()
            except Exception:  # noqa: BLE001
                return None

    @cached_property
    def thi_truong(self) -> Dict[str, Any]:
        ra = dict(MAC_DINH_THI_TRUONG)
        tu_ngach = getattr(self.ngach, "thi_truong", None)
        if isinstance(tu_ngach, dict):
            ra.update({k: v for k, v in tu_ngach.items() if v not in (None, "")})
        for k in MAC_DINH_THI_TRUONG:
            gt = self._kenh_yaml.get(k)
            if gt not in (None, ""):
                ra[k] = gt
        return ra

    # ── giai đoạn, YPP ──────────────────────────────────────────────────────
    @cached_property
    def ypp(self) -> Dict[str, Any]:
        """`sub`/`gio` ưu tiên kenh.yaml `ypp_sub`/`ypp_gio` (số TRỌN ĐỜI người vận hành ghi); không có
        thì lấy khối `tong-quan.json` cấp kênh mới nhất — số ĐÓ LÀ 28 NGÀY, chưa phải trọn đời (nhãn
        `nguon` nói rõ), nên chỉ dùng để viết mục tiêu, KHÔNG dùng để kết luận "đã kiếm tiền"."""
        sub, gio, nguon = self.cai("ypp_sub", None), self.cai("ypp_gio", None), "kenh_yaml"
        if sub is None and gio is None:
            du = _tong_quan_kenh_moi_nhat(self.goc, self.ma_kenh)
            sub, gio, nguon = du.get("subs"), du.get("watch_hours"), ("28_ngay" if du else "")
        try:
            sub = None if sub in (None, "") else int(float(sub))
        except (TypeError, ValueError):
            sub = None
        try:
            gio = None if gio in (None, "") else float(gio)
        except (TypeError, ValueError):
            gio = None
        thieu = ""
        if sub is not None and gio is not None:
            thieu_sub, thieu_gio = sub < YPP_SUB, gio < YPP_GIO
            thieu = "ca_hai" if thieu_sub and thieu_gio else "sub" if thieu_sub else "gio" if thieu_gio else ""
        return {"sub": sub, "gio": gio, "thieu": thieu, "nguon": nguon}

    @cached_property
    def giai_doan(self) -> str:
        if not self.co_v7:
            return "moi"
        if self.cai("da_kiem_tien", False) is True:
            return "kiem_tien"
        y = self.ypp
        if y["nguon"] == "kenh_yaml" and y["sub"] is not None and y["gio"] is not None and not y["thieu"]:
            return "kiem_tien"
        return "dang_len"

    # ── dữ liệu học ─────────────────────────────────────────────────────────
    @cached_property
    def so_video_48h(self) -> int:
        try:
            from .. import cong_thuc_v7 as v7  # noqa: PLC0415

            ch, _ = v7.nap_cau_hinh(self.goc, self.ma_kenh, ghi_neu_thieu=False)
            return sum(1 for v in v7.video_cua_kenh(self.goc, self.ma_kenh, ch)
                       if getattr(v, "hien_thi_48h", None) is not None)
        except Exception:  # noqa: BLE001
            return 0

    @cached_property
    def _ch_v7(self) -> Dict[str, Any]:
        """Cấu hình V7 của kênh (chỉ đọc, không ghi mặc định ra đĩa) + bộ nhớ phân cụm theo nghĩa."""
        try:
            from .. import cong_thuc_v7 as v7  # noqa: PLC0415

            ch, _ = v7.nap_cau_hinh(self.goc, self.ma_kenh, ghi_neu_thieu=False)
            v7.nap_phan_cum(self.goc, self.ma_kenh, ch)
            return ch
        except Exception:  # noqa: BLE001
            return {}

    def cum_cua(self, tieu_de: str) -> List[str]:
        """Mã cụm của một tiêu đề — ĐÚNG bộ nhận cụm V7 (`cum_cua_tieu_de`: nhãn AI theo nghĩa trước,
        từ khoá chỉ là đường lùi), không phải một bộ phân loại thứ hai."""
        if not tieu_de:
            return []
        try:
            from .. import cong_thuc_v7 as v7  # noqa: PLC0415

            return list(v7.cum_cua_tieu_de(tieu_de, self._ch_v7 or None) or [])
        except Exception:  # noqa: BLE001
            return []

    @cached_property
    def cum_da_thu(self) -> set:
        """Cụm kênh đã làm ít nhất một lần (mọi tiêu đề ĐÃ LÀM của CHÍNH kênh, không tính nhóm)."""
        try:
            from .. import trung_tieu_de as ttd  # noqa: PLC0415

            ds = ttd.doc_tieu_de_da_lam(self.goc, self.ma_kenh)
        except Exception:  # noqa: BLE001
            return set()
        ra: set = set()
        for td, _mo_ta in ds or ():
            ra.update(self.cum_cua(str(td or "")))
        return ra

    @cached_property
    def luat_chon(self) -> List[str]:
        gt = self._kenh_yaml.get("luat_chon")
        if gt in (None, "", []):
            gt = getattr(self.ngach, "luat_chon", None)
        if isinstance(gt, str):
            gt = [x.strip() for x in gt.split("|") if x.strip()]
        return [str(x) for x in (gt or []) if str(x).strip()]

    @cached_property
    def bai_hoc(self) -> List[Dict[str, Any]]:
        try:
            from . import bai_hoc as bh  # noqa: PLC0415 — module của agent B, có thể chưa có

            return list(bh.doc(self.goc, self.ma_kenh, "chon") or [])
        except Exception:  # noqa: BLE001
            return []

    def ket_qua(self, ngay: int = 28) -> Dict[str, Dict[str, Any]]:
        if ngay not in self._nho_ket_qua:
            try:
                from . import ket_qua as kq  # noqa: PLC0415 — module của agent B, có thể chưa có

                self._nho_ket_qua[ngay] = dict(kq.thong_ke(self.goc, self.ma_kenh, ngay=ngay) or {})
            except Exception:  # noqa: BLE001
                self._nho_ket_qua[ngay] = {}
        return self._nho_ket_qua[ngay]

    @property
    def ket_qua_cong_thuc(self) -> Dict[str, Dict[str, Any]]:
        return self.ket_qua(28)

    @cached_property
    def so_luot_hom_nay(self) -> int:
        """Số lượt trong sổ `tu-chay/<ngày>.json` — vòng chọn nguồn đọc TRƯỚC khi ghi lượt mới, trạm đọc
        cùng tệp, nên hai bên tính ra cùng một số (xem thăm dò tất định ở `chien_luoc.ke_hoach`)."""
        try:
            from .. import tu_chay  # noqa: PLC0415

            duong = tu_chay.duong_bao_cao_ngay(self.goc, self.ma_kenh, self.bay_gio.date().isoformat())
            with io.open(duong, encoding="utf-8") as tep:
                return len((json.load(tep) or {}).get("runs") or [])
        except Exception:  # noqa: BLE001
            return 0

    # ── bộ lọc chung ────────────────────────────────────────────────────────
    def _trung_da_lam(self, tieu_de: str) -> Any:
        if tieu_de not in self._nho_trung:
            self._nho_trung[tieu_de] = trung_tieu_de.tim_tieu_de_trung(
                tieu_de, self.da_lam_tieu_de, self.nguong_giong)
        return self._nho_trung[tieu_de]

    def loc(self, ds: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Thân `_bi_trung_tieu_de` cũ của `tu_chay.ung_vien_xep_hang`, dời ra (28–30/09/2026):

        * thiếu mã / mã trong `loai_tru` → bỏ;
        * cùng tiêu đề (chuẩn hoá, bỏ nhãn đầu/cuối) với dòng XẾP TRÊN trong chính `ds` → bỏ;
        * trùng một tiêu đề đã làm (`da_lam_tieu_de`, ngưỡng `nguong_giong`) → bỏ + log.

        Trả BẢN SAO từng dòng (`dict(d, ma=ma)`), giữ thứ tự. Bộ nhớ "tiêu đề đã thấy" tạo mới mỗi lần
        gọi nên chạy lại cho cùng kết quả; dòng log "loại … vì trùng tiêu đề" chỉ in một lần cho mỗi
        tiêu đề (chuẩn hoá) trong cả ngữ cảnh — đúng như bản cũ, nơi VPH rơi về Một nút dùng chung một
        bộ nhớ."""
        da_thay: set = set()
        ra: List[Dict[str, Any]] = []
        for d in ds:
            ma = str(d.get("ma") or so.ma_video(str(d.get("link") or "")) or "")
            if not ma or ma in self.loai_tru:
                continue
            tieu_de = str(d.get("tieu_de") or "")
            khoa_td = trung_tieu_de.chuan_hoa_tieu_de_so_khop(tieu_de) if tieu_de else ""
            if khoa_td:
                if khoa_td in da_thay:
                    continue
                da_thay.add(khoa_td)
            if self.da_lam_tieu_de and tieu_de:
                trung = self._trung_da_lam(tieu_de)
                if trung is not None:
                    if (khoa_td or tieu_de) not in self._da_bao:
                        self._da_bao.add(khoa_td or tieu_de)
                        _cu, mo_ta, diem = trung
                        self.ghi("  loại {0} vì trùng tiêu đề với {1} (giống {2:.0%}): “{3}”."
                                 .format(ma, mo_ta, diem, tieu_de[:70]))
                    continue
            ra.append(dict(d, ma=ma))
        return ra

    # ── mục tiêu 3 dòng ─────────────────────────────────────────────────────
    def muc_tieu(self) -> str:
        ten_gd = {"moi": "Kênh mới", "dang_len": "Kênh đang lên", "kiem_tien": "Kênh đã kiếm tiền"}[self.giai_doan]
        y = self.ypp
        if self.giai_doan == "kiem_tien":
            d1 = "{0} — tối đa view và giờ xem trên chính tệp của kênh.".format(ten_gd)
        elif y["thieu"] == "sub":
            d1 = "{0}, thiếu {1} sub để bật kiếm tiền (giờ xem đã đủ).".format(ten_gd, YPP_SUB - y["sub"])
        elif y["thieu"] == "gio":
            d1 = "{0}, thiếu {1:.0f} giờ xem để bật kiếm tiền (sub đã đủ).".format(ten_gd, YPP_GIO - y["gio"])
        elif y["thieu"] == "ca_hai":
            d1 = "{0}, thiếu {1} sub và {2:.0f} giờ xem để bật kiếm tiền.".format(
                ten_gd, YPP_SUB - y["sub"], YPP_GIO - y["gio"])
        else:
            d1 = "{0}.".format(ten_gd)
        if y["nguon"] == "28_ngay" and y["thieu"]:
            d1 = d1[:-1] + " (số 28 ngày — chưa phải trọn đời)."
        d2 = "Tệp: {0}.".format(self.tep or "(chưa khai tep trong kenh.yaml)")
        ctr, nhan = self.thi_truong.get("ctr_trang_chu_muc_tieu"), "mặc định ngách"
        for b in self.bai_hoc:
            if "ctr" in str(b.get("truc") or "").lower() and int(b.get("n") or 0) >= 3 and b.get("muc_tieu"):
                ctr, nhan = b.get("muc_tieu"), "bài học kênh, n={0}".format(b.get("n"))
                break
        d3 = ("Video phải đạt CTR trang chủ ≥ {0:g}% @48h ({1}).".format(float(ctr), nhan)
              if ctr not in (None, "") else "Video phải thắng trên chính tệp của kênh ở mốc 48h.")
        return "\n".join((d1, d2, d3))


def _tong_quan_kenh_moi_nhat(goc: str, ma_kenh: str) -> Dict[str, Any]:
    """Cùng luật với `bien_tap_content._tong_quan_kenh_moi_nhat` (không nhập tệp ấy — agent B đang sửa)."""
    try:
        from ..kenh import duong_kenh  # noqa: PLC0415

        thu_muc = os.path.join(duong_kenh(goc, ma_kenh), "chi-so", "kenh")
        ten = sorted((t for t in os.listdir(thu_muc) if t.startswith("kenh-")), reverse=True)
    except Exception:  # noqa: BLE001
        return {}
    for t in ten:
        try:
            with io.open(os.path.join(thu_muc, t, "tong-quan.json"), encoding="utf-8") as tep:
                du = json.load(tep)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(du, dict) and (du.get("tuoi") or du.get("thiet_bi")):
            return du
    return {}


def dung(goc: str, ma_kenh: str, *, co_v7: bool, loai_tru: Any = (),
         da_lam_tieu_de: Optional[Sequence[Tuple[str, str]]] = (),
         log: Optional[Callable[[str], None]] = None, bay_gio: Optional[_dt.datetime] = None,
         nguong_giong: float = trung_tieu_de.NGUONG_GIONG_TIEU_DE_MAC_DINH,
         cham_v7: Optional[Callable[..., Any]] = None,
         doc_danh_sach: Optional[Callable[..., Any]] = None,
         cham_vph: Optional[Callable[..., Any]] = None) -> NguCanh:
    """Dựng ngữ cảnh — chỉ gán trường, không đọc đĩa (mọi thứ nặng đọc lười)."""
    return NguCanh(goc=goc, ma_kenh=ma_kenh, co_v7=bool(co_v7), loai_tru=frozenset(loai_tru or ()),
                   da_lam_tieu_de=tuple(tuple(x) for x in (da_lam_tieu_de or ())),
                   nguong_giong=nguong_giong, bay_gio=bay_gio or _dt.datetime.now(), log=log,
                   cham_v7=cham_v7, doc_danh_sach=doc_danh_sach, cham_vph=cham_vph)
