"""Công thức V7 — ba đường mới ngày 29/09/2026 (`core/cong_thuc_v7.py`).

1. Cổng "bắt buộc có trong bảng đề xuất" có ĐƯỜNG LÙI: TL3-T7 ra 0 ứng viên vì video thắng
   chỉ 4% view từ đề xuất (bảng mỏng) → cổng loại sạch cả sổ.
2. Kênh em THỪA HƯỞNG cụm thắng của kênh anh em cùng `nhom` (hệ số ~0,5), số riêng thắng dần.
3. Xu hướng cụm trên trang chủ máy ảo (±, có trần).

Không gọi mạng, không cần Qt.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os

from core import cong_thuc_v7 as v7
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so

BAY_GIO = dt.datetime(2026, 9, 29, 12, 0)

M = "moneyMONEY1"   # お金持ち — cụm vat-chat
Q = "iqIQiqIQiq1"   # IQ — cụm tri-tue
O = "oneONEone01"   # 一人 — cụm mot-minh
D = "donDONdon01"   # 部屋/片付け — cụm don-dep
UNG_VIEN = [
    (M, "お金持ちほど絶対に買わないもの", "300000"),
    (Q, "IQが高い人だけが持っている特徴", "250000"),
    (O, "一人が好きな人の意外な特徴", "220000"),
    (D, "部屋を片付けられない人の特徴", "210000"),
]


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _kenh_yaml(goc, kenh, nhom=""):
    _ghi(os.path.join(goc, "CHANNEL", kenh, "kenh.yaml"),
         "ten: {0}\n".format(kenh) + ('nhom: "{0}"\n'.format(nhom) if nhom else ""))


def _video(goc, kenh, ma, tieu_de, i48, *, related=None):
    d = os.path.join(goc, "CHANNEL", kenh, "chi-so", ma)
    _ghi(os.path.join(d, "13h", "_thong-tin.json"),
         json.dumps({"tieu_de": tieu_de, "ngay_dang": "2026-09-10T00:00:00.000Z"}))
    _ghi(os.path.join(d, "13h", "tong-quan.json"), json.dumps({"impressions": 100}))
    tq = {"impressions": i48, "gio_sau_dang": 48}
    if related is not None:
        tq["traffic"] = {"related": related, "browse": 100 - related}
    _ghi(os.path.join(d, "48h", "tong-quan.json"), json.dumps(tq))


def _bang_de_xuat(goc, kenh, ma_minh, dong):
    """`traffic-related.csv` Studio xuất cho video `ma_minh`: `dong = [(mã, lượt xem)]`."""
    hang = ["Traffic source,Source type,Source title,Thumbnail impressions,Thumbnail click-through rate (%),"
            "Views,Engaged views,Average view duration,Watch time (hours)",
            "Total,,,20000,6.0,2000,1900,0:06:00,200"]
    for ma, xem in dong:
        hang.append("YT_RELATED.{0},Content,x,{1},9.0,{2},{2},0:08:00,1".format(ma, xem * 10, xem))
    _ghi(os.path.join(goc, "CHANNEL", kenh, "chi-so", ma_minh, "48h", "traffic-related.csv"),
         "\n".join(hang) + "\n")


def _so_content(goc, kenh):
    cot = so.cot_mac_dinh()
    hang = []
    for ma, td, view in UNG_VIEN:
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": "心理ch", "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": view, so.COT_TANG: "1000", "Thời lượng": "18:00", "Ngày đăng": "2026-09-05"})
        hang.append([d[c] for c in cot])
    so.luu_bang(goc, kenh, cot, hang)
    cot2 = list(db.COT)
    d = dict.fromkeys(cot2, "")
    d.update({"Kênh": "心理ch", "Trạng thái": db.THEO_DOI, "View TV": "20000",
              "Link kênh": "https://www.youtube.com/@shinrich"})
    db.luu(goc, kenh, cot2, [[d[c] for c in cot2]])


def _sua_cau_hinh(goc, kenh, **khoi):
    ch, duong = v7.nap_cau_hinh(goc, kenh)
    for k, gt in khoi.items():
        ch[k] = dict(ch.get(k) or {}, **gt)
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump(ch, tep, ensure_ascii=False)


def _theo_ma(kq):
    return {d.ma: d for d in kq.ung_vien}


# ── 1. Đường lùi cổng bảng đề xuất ──────────────────────────────────────────

def _kenh_co_video_thang(tmp_path, xem_A, related):
    goc = str(tmp_path)
    _kenh_yaml(goc, "K")
    _video(goc, "K", "winWINwin01", "お金持ちが絶対にしないこと", 50000, related=related)
    _bang_de_xuat(goc, "K", "winWINwin01", [(M, xem_A)])
    _so_content(goc, "K")
    return goc


def test_bang_de_xuat_mong_thi_cong_tat_khong_ra_0_ung_vien(tmp_path):
    """Ca TL3-T7: video thắng chỉ vài chục lượt xem từ đề xuất → cổng không được loại sạch."""
    goc = _kenh_co_video_thang(tmp_path, xem_A=15, related=4.5)
    kq = v7.cham(goc, "K", bay_gio=BAY_GIO)
    assert {M, Q, O, D} <= set(_theo_ma(kq)), [d.bi_loai for d in kq.bi_loai]
    assert any("TẮT" in c and "lượt xem" in c for c in kq.canh_bao), kq.canh_bao
    assert any("Đường lùi" in g for g in kq.ghi_chu)


def test_ty_le_view_de_xuat_thap_thi_cong_tat(tmp_path):
    """Bảng đủ lượt xem nhưng video thắng sống nhờ trang chủ (3% từ đề xuất) → cổng tắt."""
    goc = _kenh_co_video_thang(tmp_path, xem_A=600, related=3.0)
    kq = v7.cham(goc, "K", bay_gio=BAY_GIO)
    assert Q in _theo_ma(kq)
    assert any("TẮT" in c and "trang chủ" in c for c in kq.canh_bao), kq.canh_bao


def test_cong_bat_nhung_qua_it_nguoi_qua_thi_tu_noi(tmp_path):
    """Bảng dày, đề xuất 20% — cổng bật; nhưng chỉ 1 ứng viên có dòng riêng (< 5) → nới."""
    goc = _kenh_co_video_thang(tmp_path, xem_A=600, related=20.0)
    kq = v7.cham(goc, "K", bay_gio=BAY_GIO)
    theo = _theo_ma(kq)
    assert {M, Q, O, D} <= set(theo)
    assert theo[M].pool_diem is not None, "M có dòng riêng thì vẫn ăn điểm bảng đầy đủ"
    assert any("cổng bảng đề xuất đã nới" in x for x in theo[Q].ly_do)
    assert any("NỚI" in c for c in kq.canh_bao)


def test_cong_bat_va_du_nguoi_qua_thi_van_loai_nhu_cu(tmp_path):
    """Đủ ứng viên có dòng riêng → cổng giữ nguyên nghĩa cũ (bài học V13/V14 21/09)."""
    goc = _kenh_co_video_thang(tmp_path, xem_A=600, related=20.0)
    _sua_cau_hinh(goc, "K", pool={"so_ung_vien_toi_thieu": 1})
    kq = v7.cham(goc, "K", bay_gio=BAY_GIO)
    assert [d.ma for d in kq.ung_vien] == [M]
    ly = {d.ma: d.bi_loai for d in kq.bi_loai}
    assert ly[Q] == "không có trong bảng đề xuất của video thắng"


# ── 2. Thừa hưởng cụm thắng trong nhóm ──────────────────────────────────────

def _nhom(tmp_path, nhom_em="g"):
    goc = str(tmp_path)
    _kenh_yaml(goc, "ANH", "g")
    _kenh_yaml(goc, "EM", nhom_em)
    # Kênh anh em: 2/2 video tiền thắng, 1 video một mình trượt.
    _video(goc, "ANH", "anhMONEY001", "お金持ちに見えない人の特徴", 50000)
    _video(goc, "ANH", "anhMONEY002", "高級ブランドに興味がない人", 30000)
    _video(goc, "ANH", "anhALONE001", "一人が好きな人の理由", 1000)
    _so_content(goc, "EM")
    return goc


def test_kenh_em_thua_huong_cum_thang_cua_anh_em(tmp_path):
    goc = _nhom(tmp_path)
    kq = v7.cham(goc, "EM", bay_gio=BAY_GIO)
    theo = _theo_ma(kq)
    # (0,5 + 0,5 × 1,0) × (2 + 0,5)/(2 + 1) × 30 × 0,35 × 0,5 (ngoài tệp) = 4,4
    # 30/09/2026 (B7, THIET-KE-CHIEN-LUOC.md mục 6): hệ số 0,5 → 0,35, ngoài tệp 0,8 → 0,5 — số nhóm
    # chỉ là tiên nghiệm yếu. Trước B7 bài này là 10,0.
    assert theo[M].diem_cum == 4.4 and theo[M].thua_huong == "ANH", theo[M].ly_do
    assert any("thừa hưởng" in x and "ANH" in x for x in theo[M].ly_do)
    assert theo[O].diem_cum == 0 and not theo[O].thua_huong, "cụm không thắng ở anh em thì không mượn"
    assert "vat-chat" in kq.thua_huong
    assert theo[M].diem > theo[O].diem


def test_kenh_khong_nhom_khong_thua_huong(tmp_path):
    goc = _nhom(tmp_path, nhom_em="")
    kq = v7.cham(goc, "EM", bay_gio=BAY_GIO)
    assert _theo_ma(kq)[M].diem_cum == 0 and not kq.thua_huong


def test_dung_tep_cua_kenh_thi_khong_bi_nhan_he_so_ngoai_tep(tmp_path):
    goc = _nhom(tmp_path)
    ch, duong = v7.nap_cau_hinh(goc, "EM")
    ch["cum"]["tep-giau"] = {"ten": "tệp thử", "tu": ["買わない"]}
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump(ch, tep, ensure_ascii=False)
    kq = v7.cham(goc, "EM", bay_gio=BAY_GIO)
    # 30 × 0,8333 × 0,35 (B7; trước là 0,5 → 12,5) = 8,8
    assert _theo_ma(kq)[M].diem_cum == 8.8


def test_so_rieng_thang_dan_so_thua_huong(tmp_path):
    """Kênh em đã tự thử 3 video tiền (đủ 48h, đều trượt) → điểm thừa hưởng cụm tiền về 0."""
    goc = _nhom(tmp_path)
    for i in range(3):
        _video(goc, "EM", "emMONEY000" + str(i), "お金持ちの習慣 " + str(i), 900)
    kq = v7.cham(goc, "EM", bay_gio=BAY_GIO)
    assert _theo_ma(kq)[M].diem_cum == 0


def test_du_video_thang_rieng_thi_tat_thua_huong(tmp_path):
    goc = _nhom(tmp_path)
    for i in range(3):
        _video(goc, "EM", "emALONE000" + str(i), "一人が好きな人 " + str(i), 20000)
    kq = v7.cham(goc, "EM", bay_gio=BAY_GIO)
    assert not kq.thua_huong and _theo_ma(kq)[M].diem_cum == 0
    assert any("tắt" in g for g in kq.ghi_chu)
    assert _theo_ma(kq)[O].diem_cum > 0, "cụm một mình giờ là cụm thắng của chính kênh"


def test_cau_hinh_cho_tep_mang_theo_khoi_moi():
    ch = v7.cau_hinh_cho_tep(v7.CAU_HINH_MAC_DINH, "")
    # B7 (30/09/2026): mặc định mới 0,35 (trước 0,5).
    assert ch["thua_huong_nhom"]["he_so"] == 0.35 and ch["xu_huong_cum"]["bat"] is True


# ── 2b. B7 (30/09/2026): thừa hưởng nhóm = tiên nghiệm YẾU, giảm theo số video riêng ──

def test_he_so_tien_nghiem_giam_theo_so_video_rieng():
    gia = [round(v7.he_so_tien_nghiem(n, 0.35, k=2, tat_khi=6), 3) for n in (0, 1, 2, 4, 5, 6, 9)]
    assert gia == [0.35, 0.233, 0.175, 0.117, 0.1, 0.0, 0.0]
    assert v7.he_so_tien_nghiem(3, 0.35, k=0, tat_khi=0) == 0.35, "k ≤ 0 = không giảm, tat_khi ≤ 0 = không tắt"


def test_video_rieng_48h_o_cum_khac_van_giam_he_so_muon(tmp_path):
    """Kênh em đã có 1 video riêng đủ 48h (cụm một mình, không thắng) → hệ số × 2/3 cho MỌI cụm."""
    goc = _nhom(tmp_path)
    _video(goc, "EM", "emALONE0001", "一人が好きな人の本音", 900)
    theo = _theo_ma(v7.cham(goc, "EM", bay_gio=BAY_GIO))
    # 30 × 0,8333 × 0,35 × 2/(2+1) × 0,5 (ngoài tệp) = 2,9
    assert theo[M].diem_cum == 2.9 and theo[M].thua_huong == "ANH", theo[M].ly_do


def test_mot_video_rieng_truot_trong_cum_bo_phan_muon_cua_cum(tmp_path):
    """Trước B7: 1 video tiền trượt chỉ trừ 1/3 hệ số — giờ bỏ hẳn phần mượn của cụm tiền."""
    goc = _nhom(tmp_path)
    _video(goc, "EM", "emMONEY0001", "お金持ちの習慣", 900)
    theo = _theo_ma(v7.cham(goc, "EM", bay_gio=BAY_GIO))
    assert theo[M].diem_cum == 0 and not theo[M].thua_huong


def test_du_video_rieng_48h_thi_tat_thua_huong(tmp_path):
    goc = _nhom(tmp_path)
    for i in range(6):
        _video(goc, "EM", "emALONE000" + str(i), "一人が好きな人 " + str(i), 900)
    kq = v7.cham(goc, "EM", bay_gio=BAY_GIO)
    assert not kq.thua_huong and _theo_ma(kq)[M].diem_cum == 0
    assert any("tắt" in g and "đủ 48h" in g for g in kq.ghi_chu), kq.ghi_chu


# ── 3. Xu hướng cụm trên trang chủ máy ảo ───────────────────────────────────

def _trang_chu(goc, kenh):
    cot = ["Lúc quét", "Vị trí", "Kệ", "Mã video", "Tiêu đề", "Kênh", "Link kênh", "Lượt xem",
           "Đăng", "Dài", "Short", "Bị loại", "Lượt tải"]
    hang = []

    def them(ngay, n, n_iq, n_don):
        for i in range(n):
            td = "IQが高い人" if i < n_iq else ("部屋が汚い人" if i < n_iq + n_don else "今日のニュース")
            hang.append({"Lúc quét": ngay + " 08:00", "Mã video": "v{0}{1:04d}".format(ngay[-2:], i), "Tiêu đề": td})
    for ngay in ("2026-09-27", "2026-09-28"):          # 7 ngày gần nhất: IQ 10%, dọn 2,5%
        them(ngay, 200, 20, 5)
    for ngay in ("2026-09-10", "2026-09-15", "2026-09-20", "2026-09-21"):  # trước đó: IQ 2%, dọn 10%
        them(ngay, 200, 4, 20)
    duong = os.path.join(so.thu_muc_nghien_cuu(goc, kenh), "trang-chu.csv")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.DictWriter(tep, fieldnames=cot)
        w.writeheader()
        for r in hang:
            w.writerow(r)


def test_xu_huong_cum_nhe_co_tran_va_vao_bao_cao(tmp_path):
    goc = str(tmp_path)
    _kenh_yaml(goc, "K")
    _so_content(goc, "K")
    _trang_chu(goc, "K")
    kq = v7.cham(goc, "K", bay_gio=BAY_GIO)
    tran = v7.CAU_HINH_MAC_DINH["xu_huong_cum"]["tran"]
    assert 0 < kq.xu_huong["tri-tue"]["diem"] <= tran
    assert -tran <= kq.xu_huong["don-dep"]["diem"] < 0
    theo = _theo_ma(kq)
    assert theo[Q].diem_xu_huong > 0 and theo[D].diem_xu_huong < 0
    assert any("đang lên" in x for x in theo[Q].ly_do)
    f_csv, f_md = v7.luu_bao_cao(goc, "K", kq, hom_nay=BAY_GIO.date())
    with io.open(f_csv, encoding="utf-8-sig") as tep:
        dau = next(csv.reader(tep))
    assert "Xu hướng" in dau and "Thừa hưởng" in dau
    with io.open(f_md, encoding="utf-8") as tep:
        md = tep.read()
    assert "Đường lùi và tín hiệu nhóm" in md and "Xu hướng cụm" in md


def test_trang_chu_qua_it_dong_thi_khong_cong_tru(tmp_path):
    goc = str(tmp_path)
    _kenh_yaml(goc, "K")
    _so_content(goc, "K")
    kq = v7.cham(goc, "K", bay_gio=BAY_GIO)
    assert not kq.xu_huong and all(d.diem_xu_huong == 0 for d in kq.ung_vien)
