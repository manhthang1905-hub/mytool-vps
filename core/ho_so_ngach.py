"""**Hồ sơ ngách** — tách chủ đề "tâm lý × Nhật" ra khỏi mã, để một VPS khác chạy CHỦ ĐỀ KHÁC
(nấu ăn, tài chính, làm đẹp…) không phải sửa `core/*.py`.

═══ VÌ SAO CÓ MODULE NÀY ═══

Lộ trình v3.0 (`workspace/LO-TRINH-PHAT-HANH-V3.md`, mục A1–A5) liệt chín chỗ trong `core/`
đang hardcode từ khoá/tiêu chí của đúng MỘT ngách — "tâm lý học tiếng Nhật" — ngay trong mã:
cụm chủ đề, từ nhận "chân dung người" hay "cách làm", từ loại trừ 雑学/要約, mốc tuổi 50代/60代,
năm tệp khán giả… Một VPS chạy ngách khác (ví dụ "nấu ăn tiếng Việt") sẽ bị các hằng số tiếng
Nhật này lọc sai mọi ứng viên — không phải vì logic sai, mà vì logic đúng cho MỘT NGÁCH KHÁC.

Module này KHÔNG viết lại logic — nó chỉ cho logic đó một chỗ để HỎI: *"ngách của kênh này
dùng bộ từ khoá nào?"*. Nơi gọi vẫn giữ hằng số cũ làm MẶC ĐỊNH; `doc_ngach` chỉ trả về giá trị
THAY THẾ khi kênh thuộc một NHÓM đã khai `ngach.yaml`. Không có nhóm, không có tệp — mọi hàm
trả về hồ sơ RỖNG, và nơi gọi tự lùi về hằng số cũ: bốn kênh TL1–TL4 (chưa có `ngach.yaml`)
chạy Y HỆT trước khi module này tồn tại.

═══ NGÁCH LÀ CỦA NHÓM, KHÔNG PHẢI CỦA KÊNH ═══

`core/nhom_kenh.py` đã có khái niệm "nhóm" (`kenh.yaml: nhom`) — vài kênh cùng ngách, mỗi kênh
đánh một TỆP khán giả riêng. Hồ sơ ngách vì thế cũng gắn vào NHÓM, không vào từng kênh:

    CHANNEL/<kênh>/kenh.yaml            nhom: "tam-ly-nhat"
    CHANNEL/_NHOM/tam-ly-nhat/ngach.yaml  ← hồ sơ ngách của CẢ NHÓM

Kênh không khai `nhom`, hoặc nhóm chưa có `ngach.yaml`, đều rơi về hồ sơ rỗng — không phải lỗi,
là trạng thái bình thường của kênh đứng một mình (TL4-T7 gốc, hay bất kỳ kênh nào chưa xếp nhóm).

═══ KHÔNG PHỤ THUỘC `nhom_kenh` ═══

Cố ý KHÔNG `import` `core.nhom_kenh`: module đó (và các module sẽ dùng hồ sơ ngách —
`trang_chu`, `cong_thuc_v7`…) nhập NGƯỢC lại module này, nên nhập `nhom_kenh` ở đây sẽ tạo
vòng tròn ngay khi các module kia lớn lên. Đọc thẳng `kenh.yaml: nhom` bằng `core.kenh` (module
lá, không nhập gì trong `core/`), và tự ráp đường dẫn `_NHOM/<nhóm>/ngach.yaml` — đúng hai việc
`nhom_kenh.nhom_cua_kenh`/`duong_thu_muc_nhom` làm, chép lại ở đây vì chúng quá nhỏ để đáng một
lần nhập.

═══ HỎNG THÌ LÙI, KHÔNG NÉM LỖI ═══

Thiếu tệp, thiếu `nhom`, `ngach.yaml` không phải YAML hợp lệ, PyYAML chưa cài, khoá sai kiểu
(chuỗi thay vì danh sách…) — mọi trường hợp đều trả hồ sơ RỖNG và ghi một dòng `logging.warning`
(trừ "thiếu tệp/thiếu nhóm", đó là trạng thái bình thường, không log). Vòng chọn nguồn hằng đêm
không được vỡ vì một tệp cấu hình gõ tay sai.

Không mạng, không Qt.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .kenh import TEP_KENH, doc_yaml, duong_kenh

__all__ = [
    "TEN_TEP_NGACH", "THU_MUC_NHOM", "HoSoNgach", "duong_ngach_yaml",
    "nhom_cua_kenh", "doc_ngach_tho", "doc_ngach",
]

_log = logging.getLogger(__name__)

TEN_TEP_NGACH = "ngach.yaml"
#: Trùng `nhom_kenh.THU_MUC_NHOM` — chép hằng số, không nhập module (xem docstring đầu file).
THU_MUC_NHOM = "_NHOM"

#: Khoá kiểu DANH SÁCH CHUỖI — sai kiểu (không phải list, hoặc list chứa thứ không phải chuỗi)
#: thì coi khoá đó là THIẾU, không cố ép kiểu (ép sai âm thầm còn nguy hơn bỏ qua).
_KHOA_DS_CHUOI = (
    "tu_manh", "tu_yeu", "tu_loai_tru", "ten_kenh_loai_tru", "handle_loai_tru",
    "tu_tuoi", "tu_chan_dung", "tu_cach_lam",
    # 30/09/2026 — Đợt 4 áp lên bản sống: các bộ từ còn cứng trong mã mà bản nháp chưa có khoá.
    "tu_tuoi_them", "tu_ghep_khong_phai_nguoi", "ten_kenh_dung_ngach", "tu_khop_nguon", "tu_go_toi",
    "tu_kenh_hien_nhien", "handle_hien_nhien", "tu_tieu_de_hien_nhien", "dau_moc_tuoi_kenh",
    "luat_chon",
)

#: Khoá CHUỖI (mô tả, lời nhắc) — `str(...).strip()`, không khai thì "".
_KHOA_CHUOI = (
    "mo_ta_ngach", "dang_thang", "mau_tieu_de", "mo_ta_kenh_cho_ai", "dang_thang_cho_ai",
    "mo_ta_phan_cum", "nhan_the_loai_mau", "vi_du_phan_cum",
)


def _ten_thu_muc_an_toan(ten: str) -> str:
    """Tên nhóm → tên thư mục dùng được trên Windows — chép `doi_thu_kenh.ten_kenh_an_toan`,
    không nhập module đó để giữ `ho_so_ngach` là module LÁ (xem docstring đầu file)."""
    ten = " ".join(str(ten or "").split())
    for xau in r'\/:*?"<>|':
        ten = ten.replace(xau, "-")
    return ten.strip(" .")


@dataclass
class HoSoNgach:
    """Hồ sơ ngách của một NHÓM kênh — mọi trường RỖNG nghĩa là "dùng mặc định của mã".

    Không có trường nào ở đây là bắt buộc: `ngach.yaml` chỉ cần khai những khoá nơi gọi thật sự
    muốn THAY, các khoá còn lại cứ để trống và nơi gọi tự lùi về hằng số cũ của nó.
    """

    #: Đường dẫn `ngach.yaml` đã đọc — `""` nghĩa là hồ sơ RỖNG (không có nhóm, hoặc nhóm chưa
    #: có tệp). Dùng để phân biệt "rỗng vì không có" với "rỗng vì mọi khoá đều bỏ trống".
    nguon: str = ""
    #: Tên nhóm đã tìm ra tệp này cho (rỗng nếu kênh không thuộc nhóm nào).
    nhom: str = ""

    # ── Mô tả (chỉ để người/AI đọc, không đi vào phép lọc) ──
    mo_ta_ngach: str = ""
    ngon_ngu_nguon: str = ""
    dang_thang: str = ""

    # ── Lọc trang chủ / ứng viên đối thủ (core/trang_chu.py) ──
    tu_manh: List[str] = field(default_factory=list)
    tu_yeu: List[str] = field(default_factory=list)
    tu_loai_tru: List[str] = field(default_factory=list)
    ten_kenh_loai_tru: List[str] = field(default_factory=list)
    handle_loai_tru: List[str] = field(default_factory=list)

    # ── Tiền lọc rẻ ca HIỂN NHIÊN + thẻ tuổi của kênh nguồn (core/trang_chu.py) ──
    tu_kenh_hien_nhien: List[str] = field(default_factory=list)
    handle_hien_nhien: List[str] = field(default_factory=list)
    tu_tieu_de_hien_nhien: List[str] = field(default_factory=list)
    dau_moc_tuoi_kenh: List[str] = field(default_factory=list)

    # ── Cổng tuổi / dạng chân dung-cách làm (core/phan_tuyen.py, core/cong_thuc_v7.py) ──
    #: Mốc tuổi là NHÂN VẬT CHÍNH (= `phan_tuyen.DAU_MOC_TUOI`) — phan_tuyen, chot_doi_thu, VPH, V7.
    tu_tuoi: List[str] = field(default_factory=list)
    #: V7 cộng THÊM ngoài `tu_tuoi` (= `cong_thuc_v7.CAU_HINH_MAC_DINH["tu_tuoi"]`, khoá "tu_tuoi"
    #: của cong-thuc-v7.json). Tách riêng vì hai bộ khác nhau; gộp là đổi điểm.
    tu_tuoi_them: List[str] = field(default_factory=list)
    tu_chan_dung: List[str] = field(default_factory=list)
    tu_cach_lam: List[str] = field(default_factory=list)
    tu_ghep_khong_phai_nguoi: List[str] = field(default_factory=list)

    # ── Chốt đối thủ (core/chot_doi_thu.py) ──
    #: Tên kênh tự khai đúng ngách (= `TEN_KENH_TAM_LY`).
    ten_kenh_dung_ngach: List[str] = field(default_factory=list)
    #: Từ khoá tuyến chính của nguồn, nối "|" thành regex (= `TU_KHOP_LECH_NHIP`).
    tu_khop_nguon: List[str] = field(default_factory=list)
    #: Khuôn "gỡ tội" (= `TU_GO_TOI`).
    tu_go_toi: List[str] = field(default_factory=list)

    #: `True` = dùng bảng chủ đề con dựng sẵn trong mã (`tuyen_con.CHU_DE`, của ngách tâm lý Nhật).
    #: Ngách khác để `False`: không khớp nhầm (vd chữ La-tinh "SNS").
    chu_de_con_mac_dinh: bool = False

    # ── Cụm chủ đề để chấm Công thức V7 (core/cong_thuc_v7.py) ──
    cum: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── Ngách của KÊNH NGUỒN — cửa 5 Công thức V7 (core/cong_thuc_v7.py, khoá "ngach") ──
    ngach_tu: List[str] = field(default_factory=list)
    ngach_tu_lac: List[str] = field(default_factory=list)

    # ── Tệp khán giả (core/trung_tam.py, core/tuyen_noi_dung.py, core/tuyen_con.py) ──
    #: `[{"ma": "1", "ten": "...", "ten_ngan": "..."}, ...]`
    tep_khan_gia: List[Dict[str, str]] = field(default_factory=list)

    # ── Lời nhắc AI ──
    #: Chèn vào `auto_khau.de_bai_nan_khuon`: "Bạn đặt tiêu đề cho một {mau_tieu_de}."
    mau_tieu_de: str = ""
    #: Câu mở đầu `cong_thuc_v7_ai.de_bai_kenh` — mô tả kênh cho AI đọc catalogue nguồn.
    mo_ta_kenh_cho_ai: str = ""
    #: Cụm từ "dạng video đang thắng" trong cùng đề bài (rỗng → `dang_thang`).
    dang_thang_cho_ai: str = ""
    #: `{"dung": câu, "gan": câu, "lac": câu}` — ba mức ngách của KÊNH NGUỒN trong đề bài đó.
    luat_kenh_nguon: Dict[str, str] = field(default_factory=dict)
    #: `phan_cum_ai.de_bai`: mô tả video ("tiếng Nhật (ngách tâm lý)"), nhãn ngoặc mẫu, câu ví dụ.
    mo_ta_phan_cum: str = ""
    nhan_the_loai_mau: str = ""
    vi_du_phan_cum: str = ""
    #: Luật chọn nguồn theo NGHĨA cho biên tập viên AI (danh sách câu ngắn).
    luat_chon: List[str] = field(default_factory=list)

    # ── Thị trường (quốc gia/ngôn ngữ) — thô như trong tệp; `ngu_canh.thi_truong` trộn với
    # kenh.yaml và mặc định. Khoá: quoc_gia, ngon_ngu, mui_gio, bac_lam_tron_view, …
    thi_truong: Dict[str, Any] = field(default_factory=dict)

    def co(self) -> bool:
        """Có hồ sơ thật (đọc được tệp) hay không — `False` thì mọi trường ở trên đều là mặc
        định rỗng, nơi gọi nên lùi về hằng số cũ của chính nó."""
        return bool(self.nguon)


def duong_ngach_yaml(goc: str, nhom: str) -> str:
    """Đường dẫn `ngach.yaml` của một nhóm — không kiểm tệp có tồn tại hay không."""
    return os.path.join(duong_kenh(goc), THU_MUC_NHOM, _ten_thu_muc_an_toan(nhom), TEN_TEP_NGACH)


def nhom_cua_kenh(goc: str, ma_kenh: str) -> str:
    """`nhom` khai trong `kenh.yaml` của một kênh — `""` nếu không thuộc nhóm nào.

    Chép từ `nhom_kenh.nhom_cua_kenh` — xem "KHÔNG PHỤ THUỘC `nhom_kenh`" ở docstring đầu file.
    """
    cai = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH))
    return str(cai.get("nhom") or "").strip()


def _doc_yaml_day_du(duong: str) -> Optional[Dict[str, Any]]:
    """Đọc TOÀN VĂN một tệp YAML (có cấu trúc lồng: dict-trong-dict, list-trong-dict) bằng
    PyYAML thật — khác `core.kenh.doc_yaml` (bộ đọc tối giản chỉ cho `kenh.yaml`/`style.yaml`
    phẳng). `ngach.yaml` có `cum`/`tep_khan_gia` lồng nhau nên cần PyYAML thật.

    Trả `None` khi: không có tệp (bình thường, không log), không cài PyYAML, cú pháp sai, hoặc
    nội dung không phải một mapping ở gốc — mọi trường hợp `None` đều là "lùi mặc định".
    """
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            tho = tep.read()
    except OSError:
        return None
    try:
        import yaml  # noqa: PLC0415 — chỉ nạp khi thật sự cần đọc ngach.yaml
    except ImportError:
        _log.warning("ho_so_ngach: %s có ngach.yaml nhưng máy chưa cài PyYAML — lùi mặc định", duong)
        return None
    try:
        du_lieu = yaml.safe_load(tho)
    except Exception as loi:  # noqa: BLE001 — YAML hỏng không được làm vỡ vòng chọn nguồn
        _log.warning("ho_so_ngach: %s không đọc được (%s) — lùi mặc định", duong, loi)
        return None
    if du_lieu is None:
        return {}
    if not isinstance(du_lieu, dict):
        _log.warning("ho_so_ngach: %s không phải một mapping YAML (gốc là %s) — lùi mặc định",
                      duong, type(du_lieu).__name__)
        return None
    return du_lieu


def doc_ngach_tho(goc: str, nhom: str) -> Optional[Dict[str, Any]]:
    """Nội dung THÔ (chưa ráp thành `HoSoNgach`) của `ngach.yaml` một nhóm, hoặc `None`."""
    nhom = (nhom or "").strip()
    if not nhom:
        return None
    return _doc_yaml_day_du(duong_ngach_yaml(goc, nhom))


def _ds_chuoi(tho: Dict[str, Any], khoa: str, duong: str) -> List[str]:
    gt = tho.get(khoa)
    if gt is None:
        return []
    if not isinstance(gt, list) or not all(isinstance(x, str) for x in gt):
        _log.warning("ho_so_ngach: %s khoá %r phải là danh sách chuỗi, bỏ qua khoá này", duong, khoa)
        return []
    return list(gt)


def _dict_tho(tho: Dict[str, Any], khoa: str, duong: str) -> Dict[str, Any]:
    gt = tho.get(khoa)
    if gt is None:
        return {}
    if not isinstance(gt, dict):
        _log.warning("ho_so_ngach: %s khoá %r phải là mapping, bỏ qua khoá này", duong, khoa)
        return {}
    return dict(gt)


def _dict_chuoi(tho: Dict[str, Any], khoa: str, duong: str) -> Dict[str, str]:
    return {str(k): str(v).strip() for k, v in _dict_tho(tho, khoa, duong).items()
            if isinstance(v, str) and v.strip()}


def _cum_tho(tho: Dict[str, Any], duong: str) -> Dict[str, Dict[str, Any]]:
    gt = tho.get("cum")
    if gt is None:
        return {}
    if not isinstance(gt, dict):
        _log.warning("ho_so_ngach: %s khoá 'cum' phải là mapping, bỏ qua khoá này", duong)
        return {}
    ra: Dict[str, Dict[str, Any]] = {}
    for ma, c in gt.items():
        if not isinstance(c, dict):
            _log.warning("ho_so_ngach: %s cum.%s không phải mapping, bỏ qua", duong, ma)
            continue
        tu = c.get("tu") or []
        if not isinstance(tu, list) or not all(isinstance(x, str) for x in tu):
            _log.warning("ho_so_ngach: %s cum.%s.tu phải là danh sách chuỗi, bỏ qua cụm này", duong, ma)
            continue
        ra[str(ma)] = {"ten": str(c.get("ten") or ma), "tu": list(tu)}
    return ra


def _tep_khan_gia_tho(tho: Dict[str, Any], duong: str) -> List[Dict[str, str]]:
    gt = tho.get("tep_khan_gia")
    if gt is None:
        return []
    if not isinstance(gt, list):
        _log.warning("ho_so_ngach: %s khoá 'tep_khan_gia' phải là danh sách, bỏ qua khoá này", duong)
        return []
    ra: List[Dict[str, str]] = []
    for i, d in enumerate(gt):
        if not isinstance(d, dict) or not str(d.get("ma") or "").strip():
            _log.warning("ho_so_ngach: %s tep_khan_gia[%d] thiếu 'ma', bỏ qua dòng này", duong, i)
            continue
        dong = {
            "ma": str(d.get("ma")).strip(),
            "ten": str(d.get("ten") or "").strip(),
            "ten_ngan": str(d.get("ten_ngan") or "").strip(),
        }
        # 30/09/2026: `ma_tuyen` (tuỳ chọn) = mã tuyến trong tuyen.csv/kenh.yaml `tep` của tệp này
        # (vd. '7' → nguoi-cao-tuoi-dang-song-tuoi-gia) — `tuyen_noi_dung.ma_tep` đọc. Chỉ ghi khi có.
        if str(d.get("ma_tuyen") or "").strip():
            dong["ma_tuyen"] = str(d.get("ma_tuyen")).strip()
        ra.append(dong)
    return ra


def doc_ngach(goc: str, ma_kenh: str) -> HoSoNgach:
    """Hồ sơ ngách của kênh `ma_kenh` — tìm NHÓM của nó rồi đọc `ngach.yaml` của nhóm đó.

    Không thuộc nhóm nào, nhóm chưa có `ngach.yaml`, hay tệp hỏng → `HoSoNgach()` RỖNG
    (`.co() == False`) — nơi gọi lùi về hằng số cũ, KHÔNG có ngoại lệ nào ném ra khỏi hàm này.
    """
    ma_kenh = (ma_kenh or "").strip()
    if not ma_kenh:
        return HoSoNgach()
    nhom = nhom_cua_kenh(goc, ma_kenh)
    if not nhom:
        return HoSoNgach()
    duong = duong_ngach_yaml(goc, nhom)
    tho = _doc_yaml_day_du(duong)
    if tho is None:
        return HoSoNgach(nhom=nhom)

    ng = tho.get("ngach") if isinstance(tho.get("ngach"), dict) else {}
    ngach_tu = ng.get("tu") if isinstance(ng, dict) else None
    ngach_tu_lac = ng.get("tu_lac") if isinstance(ng, dict) else None

    return HoSoNgach(
        nguon=duong,
        nhom=nhom,
        ngon_ngu_nguon=str(tho.get("ngon_ngu_nguon") or "").strip().lower(),
        **{k: str(tho.get(k) or "").strip() for k in _KHOA_CHUOI},
        **{k: _ds_chuoi(tho, k, duong) for k in _KHOA_DS_CHUOI},
        chu_de_con_mac_dinh=tho.get("chu_de_con_mac_dinh") is True,
        luat_kenh_nguon=_dict_chuoi(tho, "luat_kenh_nguon", duong),
        thi_truong=_dict_tho(tho, "thi_truong", duong),
        cum=_cum_tho(tho, duong),
        ngach_tu=list(ngach_tu) if isinstance(ngach_tu, list) and all(isinstance(x, str) for x in ngach_tu) else [],
        ngach_tu_lac=list(ngach_tu_lac) if isinstance(ngach_tu_lac, list)
        and all(isinstance(x, str) for x in ngach_tu_lac) else [],
        tep_khan_gia=_tep_khan_gia_tho(tho, duong),
    )
