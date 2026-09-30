"""**Bốn kênh trong nhóm KÉO NHAU ở bộ chọn nguồn** — `nhom_kenh.doc_bang_nhom` +
`tu_chay.cong_diem_anh_em`.

`ghi_bang_nhom` viết `CHANNEL/_NHOM/<nhóm>/bang-nhom.csv` mỗi ngày ("kênh nào đang thắng
cụm nào") nhưng trước nhánh này không ai đọc nó lúc chọn nguồn — chỉ màn hình
`trung_tam._nhom()`. Bốn kênh chia nhau đối thủ và done-list mà không chia nhau bài học.

Bốn điều các bài dưới đây canh, theo đúng thứ tự rủi ro:

1. **Bảng thiếu → hành vi Y NGUYÊN.** Không một thứ hạng nào đổi. Đây là hợp đồng với
   đêm nay: ba kênh em chưa chắc có bảng, và một tính năng "cải thiện" không được phép
   làm kênh ra 0 video.
2. **(a) Trọng số anh em nhỏ hơn của chính mình** — trần cột cụm × `he_so_tien_nghiem`
   (B7 30/09/2026: 0,35 × k/(k+n48), kênh chưa có video 48h → 10,5/100; trước là hằng một nửa,
   15/100), CỘNG THÊM trần "không bao giờ qua ứng viên TỰ THẮNG của kênh mình".
3. **(b) Không kéo kênh em ra khỏi TỆP của nó** — ứng viên ngoài tệp KHÔNG được cộng, dù
   cụm của nó đang thắng ở kênh anh em. Vi phạm điều này là phá cả chiến lược bốn tệp.
4. **Ưu tiên "có lời thoại trong kho" (`_uu_tien_co_kho`) vẫn là tiếng nói cuối cùng** —
   điểm anh em không được lật nó. Một nguồn điểm cao mà khâu kịch bản không sản xuất
   được vẫn là 0 video.

Không mạng, không ví, không đụng `CHANNEL/` thật: mọi bài dựng kênh giả trong `tmp_path`.
"""

from __future__ import annotations

import csv
import json
import os

from core import cong_thuc_v7 as v7
from core import nhom_kenh
from core import tu_chay

NHOM = "tam-ly-nhat"
TEP_TRUNG_NIEN = "nguoi-trung-nien-thu-gon-doi-song"
TEP_LECH_NHIP = "nguoi-song-lech-nhip-so-dong"

#: ═══ TIÊU ĐỀ THẬT (tiếng Nhật) — vì cả hai cổng đều đọc tiếng Nhật ═══
#:
#: Cổng cụm (`cong_thuc_v7.cum_cua_tieu_de`) và cổng tệp (`tuyen_con.nhan_dien`) đều nhận
#: bằng từ khoá tiếng Nhật. Tiêu đề tiếng Việt cho ra "không cụm nào, không tệp nào" —
#: bài kiểm sẽ XANH vì không cộng gì cả, đúng thứ nó định chứng minh là sai.
#:
#: * `TD_DON`      — 片付け → cụm `don-dep`, tệp TRUNG NIÊN (chủ đề `don-nha`).
#: * `TD_TRI_NHO`  — 物忘れ → KHÔNG cụm nào, tệp TRUNG NIÊN. Ứng viên "trung tính".
#: * `TD_MOT_MINH` — 一人/知的 → cụm `mot-minh`+`tri-tue`, tệp LỆCH NHỊP (≠ tệp kênh thử).
TD_DON = "部屋の片付けができない人の本当の理由"
TD_TRI_NHO = "物忘れが増えた人の脳で起きていること"
TD_MOT_MINH = "一人が好きな人だけに現れる5つの知的特徴"

#: Ba dòng bảng nhóm của KÊNH ANH EM (TL4-T7, tệp lệch nhịp) — hai dòng cụm `don-dep`
#: và một dòng cụm `mot-minh`/`tri-tue`, tất cả đều vượt ngưỡng thắng.
HANG_ANH_EM = (
    ("TL4-T7", TEP_LECH_NHIP, "【心理学】片付けをしない人の意外な知性", "aaaaaaaaaaa", 181062),
    ("TL4-T7", TEP_LECH_NHIP, "断捨離をした人の暮らしが変わる理由", "bbbbbbbbbbb", 135132),
    ("TL4-T7", TEP_LECH_NHIP, TD_MOT_MINH, "ccccccccccc", 136170),
)

NO_LOG = lambda *_a, **_k: None  # noqa: E731


# ── Dàn dựng ────────────────────────────────────────────────────────────────


def _kenh(goc, ma, *, nhom=NHOM, tep=TEP_TRUNG_NIEN):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    dong = ['ma: "{0}"'.format(ma), 'ngon_ngu: "ja"', 'engine: "veo3"', "phut_muc_tieu: 10"]
    if nhom:
        dong.append('nhom: "{0}"'.format(nhom))
    if tep:
        dong.append('tep: "{0}"'.format(tep))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep_yaml:
        tep_yaml.write("\n".join(dong) + "\n")
    return thu_muc


def _cong_thuc_v7(goc, ma, **cai):
    """Ghi `cong-thuc-v7.json`. Không có khoá `tep` → `co_cau_hinh_v7` trả True ngay (kênh
    tự tay khai V7, như TL4-T7); có `tep` → còn phải qua `da_co_video_thang`."""
    nc = os.path.join(goc, "CHANNEL", ma, "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, v7.TEP_CAU_HINH), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


def _ghi_bang_nhom(goc, hang=HANG_ANH_EM, *, nhom=NHOM):
    """Bảng nhóm THẬT (đúng `COT_BANG_NHOM`), không phải đồ giả — để bài kiểm đi qua
    chính `doc_bang_nhom`, kể cả phần đọc CSV/BOM."""
    thu_muc = nhom_kenh.duong_thu_muc_nhom(goc, nhom)
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, nhom_kenh.TEP_BANG_NHOM)
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        but = csv.DictWriter(tep, fieldnames=list(nhom_kenh.COT_BANG_NHOM))
        but.writeheader()
        for ma_k, tep_id, tieu_de, ma_v, hien_thi in hang:
            but.writerow({"Kênh": ma_k, "Tệp": tep_id, "Tiêu đề": tieu_de, "Mã video": ma_v,
                          "Ngày đăng": "2026-09-16", "Lượt hiển thị": hien_thi,
                          "Tỷ lệ bấm": "5.41%", "Xem TB": "4:02", "Lượt xem": 4723,
                          "Đăng ký": 7})
    return duong


class _DongV7Gia:
    """Đủ những gì `ung_vien_xep_hang` đọc bằng `getattr` — kèm `diem_cum` (điểm cụm CỦA
    CHÍNH KÊNH MÌNH), thứ quyết định ứng viên nào là "TỰ THẮNG"."""

    def __init__(self, ma, tieu_de, diem, *, diem_cum=0.0, loai="Nên làm"):
        self.ma, self.tieu_de, self.diem, self.diem_cum = ma, tieu_de, diem, diem_cum
        self.link = "https://youtu.be/" + ma
        self.kenh, self.loai, self.ly_do, self.bi_loai = "Z", loai, [], ""


class _KetQuaV7Gia:
    def __init__(self, ung_vien):
        self.ung_vien = ung_vien


def _cham_v7_gia(*ds):
    return lambda _g, _k: _KetQuaV7Gia(list(ds))


def _dong_mot_nut(ma, tieu_de, *, view=0.0, vuot=0.0, tang=0.0):
    return {"link": "https://youtu.be/" + ma, "tieu_de": tieu_de, "kenh": "Z",
            "view": view, "vuot": vuot, "tang": tang, "diem": 0}


def _xep(goc, ma_kenh, co_v7_truoc, *, cham_v7=None, moi=None, log=None):
    return tu_chay.ung_vien_xep_hang(
        goc, ma_kenh, co_v7_truoc, set(), cham_v7=cham_v7,
        doc_danh_sach=(lambda *_a: {"moi": list(moi or [])}), log=log or NO_LOG)


# ── 1) Hàm ĐỌC bảng nhóm ────────────────────────────────────────────────────


def test_doc_bang_nhom_thieu_hong_hoac_khong_thuoc_nhom_thi_rong(tmp_path):
    """Tệp thiếu / nội dung rác / nhóm lạ → `{}`, không ném lỗi. Vòng chọn nguồn 02:00
    không được vỡ vì một bảng PHỤ."""
    goc = str(tmp_path)
    assert nhom_kenh.doc_bang_nhom(goc, NHOM) == {}
    assert nhom_kenh.doc_bang_nhom(goc, "") == {}

    thu_muc = nhom_kenh.duong_thu_muc_nhom(goc, NHOM)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, nhom_kenh.TEP_BANG_NHOM), "wb") as tep:
        tep.write(b"\x00\x01 kh\xf4ng ph\xe3i CSV \x00")
    assert nhom_kenh.doc_bang_nhom(goc, NHOM) == {}


def test_doc_bang_nhom_gom_theo_cum_va_kenh_lam_muot_laplace(tmp_path):
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    bang = nhom_kenh.doc_bang_nhom(goc, NHOM)
    # `don-dep`: 2 video, cả hai thắng → (2+0,5)/(2+1); `mot-minh`: 1/1 → (1+0,5)/(1+1).
    assert bang["don-dep"] == {"TL4-T7": round(2.5 / 3.0, 3)}
    assert bang["mot-minh"] == {"TL4-T7": 0.75}
    # Cụm KHÔNG có video thắng nào thì không có mặt — "chưa thắng" không phải tín hiệu.
    assert nhom_kenh.doc_bang_nhom(goc, NHOM, nguong_hien_thi=10 ** 9) == {}
    # `bo_kenh`: đây là tín hiệu ANH EM, thành tích của chính mình không tính vào.
    assert nhom_kenh.doc_bang_nhom(goc, NHOM, bo_kenh=("TL4-T7",)) == {}


def test_doc_bang_nhom_dung_bo_cum_cua_nguoi_doc(tmp_path):
    """Bảng không có cột "Cụm" — cụm do NGƯỜI ĐỌC phân loại, nên cấu hình kênh em (có
    thêm cụm `tep-*`) đọc ra tên cụm của chính nó."""
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    ch = v7.cau_hinh_cho_tep(v7.CAU_HINH_MAC_DINH, TEP_TRUNG_NIEN)
    bang = nhom_kenh.doc_bang_nhom(goc, NHOM, cum_cua=lambda td: v7.cum_cua_tieu_de(td, ch))
    assert "tep-don-nha" in bang and bang["tep-don-nha"]["TL4-T7"] > 0
    # `cum_cua` nổ → `{}`, không ném ra ngoài.
    def no(_td):
        raise RuntimeError("bộ nhận cụm hỏng")

    assert nhom_kenh.doc_bang_nhom(goc, NHOM, cum_cua=no) == {}


# ── 2) Bảng THIẾU → hành vi y như cũ ────────────────────────────────────────


def test_khong_co_bang_nhom_thi_thu_hang_y_nguyen_ca_hai_che_do(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")

    ds_v7 = _xep(goc, "TL2-T7", True, cham_v7=_cham_v7_gia(
        _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70), _DongV7Gia("BBBBBBBBBBB", TD_DON, 60)))
    assert [d["ma"] for d in ds_v7] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert all("diem_anh_em" not in d for d in ds_v7)

    ds_mn = _xep(goc, "TL2-T7", False, moi=[
        _dong_mot_nut("CCCCCCCCCCC", TD_TRI_NHO, view=500_000, vuot=9.0),
        _dong_mot_nut("DDDDDDDDDDD", TD_DON, view=200_000, vuot=4.0)])
    assert [d["ma"] for d in ds_mn] == ["CCCCCCCCCCC", "DDDDDDDDDDD"]
    assert all("diem_anh_em" not in d for d in ds_mn)


def test_kenh_khong_thuoc_nhom_hoac_chua_khai_tep_thi_khong_cong(tmp_path):
    """Không khai `nhom` → đứng một mình. Khai `nhom` mà thiếu `tep` → KHÔNG cộng, vì
    không canh được ràng buộc (b) "ứng viên phải còn trong tệp của kênh"."""
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "MOT-MINH", nhom="", tep=TEP_TRUNG_NIEN)
    _kenh(goc, "THIEU-TEP", tep="")
    for ma in ("MOT-MINH", "THIEU-TEP"):
        _cong_thuc_v7(goc, ma)
        ds = _xep(goc, ma, True, cham_v7=_cham_v7_gia(
            _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70), _DongV7Gia("BBBBBBBBBBB", TD_DON, 60)))
        assert [d["ma"] for d in ds] == ["AAAAAAAAAAA", "BBBBBBBBBBB"], ma
        assert all("diem_anh_em" not in d for d in ds), ma


# ── 3) CÓ bảng → cộng điểm, có ghi lý do ────────────────────────────────────


def test_co_bang_thi_ung_vien_cung_cum_dang_thang_o_kenh_anh_em_duoc_cong(tmp_path):
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    nhat_ky = []
    ds = _xep(goc, "TL2-T7", True, log=nhat_ky.append, cham_v7=_cham_v7_gia(
        _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70), _DongV7Gia("BBBBBBBBBBB", TD_DON, 65)))
    # B7 (30/09/2026): trần = 30 × 0,35 (tiên nghiệm, 0 video riêng 48h) = 10,5; 10,5 × 0,833 ≈ 8,7.
    # 65 + 8,7 = 73,7 > 70 → ứng viên được cộng lên đầu bảng. (Trước B7: 60 + 15 × 0,833 = 72,5.)
    theo_ma = {d["ma"]: d for d in ds}
    assert theo_ma["BBBBBBBBBBB"]["diem_anh_em"] == 8.7
    assert theo_ma["BBBBBBBBBBB"]["anh_em"]["kenh"] == "TL4-T7"
    assert theo_ma["BBBBBBBBBBB"]["anh_em"]["cum"] == "don-dep"
    assert [d["ma"] for d in ds] == ["BBBBBBBBBBB", "AAAAAAAAAAA"]
    # Ứng viên KHÔNG chạm cụm nào đang thắng thì không có khoá nào mới.
    assert "diem_anh_em" not in theo_ma["AAAAAAAAAAA"]
    assert any("đang thắng ở kênh anh em TL4-T7" in l for l in theo_ma["BBBBBBBBBBB"]["ly_do"])
    assert any("KÉO NHAU" in d for d in nhat_ky)


def test_trong_so_anh_em_khong_qua_mot_nua_cot_cum(tmp_path):
    """RÀNG BUỘC (a), phần trần cứng: dù chỉ số thắng của cụm có bằng 100%, điểm anh em
    không bao giờ vượt cột cụm × tiên nghiệm (B7: 0,35 khi kênh chưa có video riêng 48h)."""
    goc = str(tmp_path)
    # Một dòng duy nhất, thắng → chỉ số 0,75; thêm chín dòng thắng nữa → tiến sát 1,0.
    hang = tuple(("TL4-T7", TEP_LECH_NHIP, "断捨離をした人の暮らしが変わる理由{0}".format(i),
                  "d{0}ddddddddd".format(i), 500_000) for i in range(10))
    _ghi_bang_nhom(goc, hang)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    ds = _xep(goc, "TL2-T7", True,
              cham_v7=_cham_v7_gia(_DongV7Gia("BBBBBBBBBBB", TD_DON, 10)))
    # Trần viết bằng SỐ THẬT (0,35 × cột cụm, B7), không lấy lại hằng trong mã — nếu
    # lấy lại thì ai nâng hằng số ấy lên 1,0 vẫn thấy bài này xanh.
    nua_cot_cum = v7.CAU_HINH_MAC_DINH["trong_so"]["cum"] * 0.35
    assert not hasattr(tu_chay, "TY_LE_DIEM_ANH_EM"), "B7: không còn hằng riêng cho điểm anh em"
    assert 0 < ds[0]["diem_anh_em"] <= nua_cot_cum
    assert nhom_kenh.doc_bang_nhom(goc, NHOM)["don-dep"]["TL4-T7"] > 0.9  # chỉ số gần 1


def test_khong_bao_gio_vuot_ung_vien_TU_THANG_cua_chinh_kenh(tmp_path):
    """RÀNG BUỘC (a), phần quan trọng hơn: ứng viên nhờ tín hiệu anh em được nâng lên SÁT
    ứng viên mà CHÍNH kênh mình đã chứng minh thắng (`diem_cum > 0`) — không được qua.

    Số Studio của chính kênh, ở đúng mốc 48 giờ, trên đúng tệp của nó là bằng chứng mạnh
    hơn hẳn một dòng bảng nhóm đo bằng hiển thị trọn đời của một kênh đánh tệp khác.
    """
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    tu_thang = _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 80, diem_cum=22.0)
    nho_anh_em = _DongV7Gia("BBBBBBBBBBB", TD_DON, 75)
    ds = _xep(goc, "TL2-T7", True, cham_v7=_cham_v7_gia(tu_thang, nho_anh_em))
    theo_ma = {d["ma"]: d for d in ds}
    # Trần thô là 8,7 (B7) nhưng trần "tự thắng" chỉ cho 80 − 75 − 1 = 4.
    assert theo_ma["BBBBBBBBBBB"]["diem_anh_em"] == 4.0
    diem_hieu_luc = (theo_ma["BBBBBBBBBBB"]["diem"]
                     + theo_ma["BBBBBBBBBBB"]["diem_anh_em"])
    assert diem_hieu_luc < theo_ma["AAAAAAAAAAA"]["diem"]
    assert [d["ma"] for d in ds] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]


def test_sat_ung_vien_tu_thang_thi_khong_cong_dong_nao(tmp_path):
    """Đã kề sát ứng viên tự thắng (79 vs 80) thì trần "tự thắng" bằng 0 — không cộng, và
    không thêm khoá `anh_em` (sổ ngày không được báo "kéo nhau" khi chẳng kéo gì)."""
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    ds = _xep(goc, "TL2-T7", True, cham_v7=_cham_v7_gia(
        _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 80, diem_cum=22.0),
        _DongV7Gia("BBBBBBBBBBB", TD_DON, 79)))
    assert [d["ma"] for d in ds] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert all("diem_anh_em" not in d and "anh_em" not in d for d in ds)


# ── 4) RÀNG BUỘC (b): không kéo kênh em ra khỏi tệp của nó ──────────────────


def test_ung_vien_NGOAI_TEP_khong_duoc_cong_du_cum_dang_thang_o_kenh_khac(tmp_path):
    """`TD_MOT_MINH` thuộc cụm `mot-minh`+`tri-tue` — CẢ HAI đang thắng ở TL4-T7 trong
    bảng nhóm. Nhưng `tuyen_con.nhan_dien` xếp nó vào tệp LỆCH NHỊP, không phải tệp
    TRUNG NIÊN của kênh đang chọn → KHÔNG một điểm nào.

    Đây là bài canh chiến lược bốn tệp: cộng ở đây là dần dần biến TL1/TL2/TL3 thành ba
    bản sao của TL4-T7.
    """
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    assert "mot-minh" in nhom_kenh.doc_bang_nhom(goc, NHOM)  # cụm ấy ĐANG thắng thật
    ds = _xep(goc, "TL2-T7", True, cham_v7=_cham_v7_gia(
        _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70),
        _DongV7Gia("BBBBBBBBBBB", TD_MOT_MINH, 60)))
    assert [d["ma"] for d in ds] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert all("diem_anh_em" not in d for d in ds)


def test_cung_cum_nhung_kenh_anh_em_khac_tep_van_cong_khi_ung_vien_dung_tep(tmp_path):
    """Mặt kia của ràng buộc (b): điều bị chặn là ỨNG VIÊN lệch tệp, KHÔNG phải kênh anh
    em lệch tệp. TL4-T7 đánh tệp lệch nhịp, nhưng cụm `don-dep` nó thắng vẫn nói được
    điều gì đó cho một ứng viên `don-dep` NẰM TRONG tệp trung niên."""
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    ds = _xep(goc, "TL2-T7", True,
              cham_v7=_cham_v7_gia(_DongV7Gia("BBBBBBBBBBB", TD_DON, 60)))
    assert ds[0]["anh_em"]["kenh"] == "TL4-T7"


# ── 5) Chế độ TRƯỚC V7 (kênh em mới, chỉ số trắng) ──────────────────────────


def test_truoc_v7_tin_hieu_anh_em_la_mot_bit_trong_cung_bac_view(tmp_path):
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    ds = _xep(goc, "TL2-T7", False, moi=[
        _dong_mot_nut("CCCCCCCCCCC", TD_TRI_NHO, view=500_000, vuot=9.0),
        _dong_mot_nut("DDDDDDDDDDD", TD_DON, view=200_000, vuot=4.0)])
    assert [d["ma"] for d in ds] == ["DDDDDDDDDDD", "CCCCCCCCCCC"]
    assert ds[0]["diem_anh_em"] > 0


def test_truoc_v7_khong_bao_gio_vuot_BAC_VIEW(tmp_path):
    """Bậc view (`NGUONG_BAC_VIEW`) là bằng chứng cứng DUY NHẤT một kênh chỉ số trắng
    đang có — một bit tín hiệu nhóm không được lật nó."""
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    ds = _xep(goc, "TL2-T7", False, moi=[
        _dong_mot_nut("CCCCCCCCCCC", TD_TRI_NHO, view=500_000, vuot=9.0),
        _dong_mot_nut("DDDDDDDDDDD", TD_DON, view=20_000, vuot=4.0)])
    assert [d["ma"] for d in ds] == ["CCCCCCCCCCC", "DDDDDDDDDDD"]
    assert ds[1]["diem_anh_em"] > 0  # vẫn được ghi nhận, chỉ không được vượt bậc


# ── 6) Kho lời thoại vẫn là tiếng nói cuối cùng ─────────────────────────────


def test_uu_tien_co_kho_van_giu_nguyen_sau_khi_cong_diem_anh_em(tmp_path, monkeypatch):
    """Điểm anh em đưa `TD_DON` lên đầu bảng, nhưng kho CHỈ có lời thoại của ứng viên kia
    → `_uu_tien_co_kho` vẫn đổi. YouTube đang chặn địa chỉ VPS này, nên nguồn không có
    lời thoại rất dễ thành 0 video — thứ tự ưu tiên ấy không được điểm anh em lật."""
    from core import loi_thoai as kho

    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    monkeypatch.setattr(kho, "co_loi_thoai",
                        lambda _g, _k, ma: ma == "AAAAAAAAAAA")
    nhat_ky = []
    nguon = tu_chay._chon_nguon(
        goc, "TL2-T7", True, set(),
        _cham_v7_gia(_DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70),
                     _DongV7Gia("BBBBBBBBBBB", TD_DON, 65)),  # B7: 65 + 8,7 > 70
        lambda *_a: {}, nhat_ky.append)
    assert nguon["ma"] == "AAAAAAAAAAA"
    assert any("ĐÃ CÓ lời thoại trong kho" in d for d in nhat_ky)


def test_bang_nhom_hong_khong_lam_vo_vong_chon_nguon(tmp_path, monkeypatch):
    """Điểm anh em là CẢI THIỆN, không phải điều kiện để chạy: `doc_bang_nhom` nổ thì vẫn
    chọn được nguồn, thứ hạng cũ giữ nguyên, và nhật ký nói thật."""
    goc = str(tmp_path)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")

    def no(*_a, **_k):
        raise OSError("ổ đĩa bận")

    monkeypatch.setattr(nhom_kenh, "doc_bang_nhom", no)
    nhat_ky = []
    ds = _xep(goc, "TL2-T7", True, log=nhat_ky.append, cham_v7=_cham_v7_gia(
        _DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70), _DongV7Gia("BBBBBBBBBBB", TD_DON, 60)))
    assert [d["ma"] for d in ds] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert any("không cộng được điểm anh em" in d for d in nhat_ky)


# ── 7) Sổ ngày dùng chung phải NÓI RA chuyện kéo nhau ───────────────────────


def test_so_ngay_ghi_mot_dong_keo_nhau_cho_moi_kenh(tmp_path):
    goc = str(tmp_path)
    _ghi_bang_nhom(goc)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    ket = tu_chay.chay_mot_ngay(
        goc, "TL2-T7", che_do="thu", on_log=NO_LOG, chay_mot_nut=lambda *a, **k: None,
        cham_v7=_cham_v7_gia(_DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70),
                             _DongV7Gia("BBBBBBBBBBB", TD_DON, 65)))  # B7: 65 + 8,7 > 70
    assert ket["run"]["nguon"]["ma"] == "BBBBBBBBBBB"
    assert "TL4-T7" in ket["keo_nhau"] and "+8.7" in ket["keo_nhau"]

    md = tu_chay._dung_md_tat_ca("2026-09-22", [{
        "luc": "02:00:00", "che_do": "that",
        "ket_qua": [{"kenh": "TL2-T7", "ok": True, "tom_tat": "TL2-T7: xong.",
                     "keo_nhau": ket["keo_nhau"]},
                    {"kenh": "TL1-T7", "ok": True, "tom_tat": "TL1-T7: xong.",
                     "keo_nhau": ""}]}])
    assert "- kéo nhau: " in md and "TL4-T7" in md
    # Kênh không được cộng gì thì KHÔNG thêm dòng nào — sổ không phình vì một câu rỗng.
    assert md.count("kéo nhau") == 1


def test_khong_cong_thi_so_ngay_khong_co_dong_nao(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "TL2-T7")
    _cong_thuc_v7(goc, "TL2-T7")
    ket = tu_chay.chay_mot_ngay(
        goc, "TL2-T7", che_do="thu", on_log=NO_LOG, chay_mot_nut=lambda *a, **k: None,
        cham_v7=_cham_v7_gia(_DongV7Gia("AAAAAAAAAAA", TD_TRI_NHO, 70)))
    assert ket["keo_nhau"] == ""
    assert "kéo nhau" not in tu_chay._dung_md_tat_ca("2026-09-22", [{
        "luc": "02:00:00", "che_do": "that",
        "ket_qua": [{"kenh": "TL2-T7", "ok": True, "tom_tat": "x",
                     "keo_nhau": ket["keo_nhau"]}]}])
