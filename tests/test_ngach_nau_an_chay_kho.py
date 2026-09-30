"""Chạy khô một kênh giả ngách "nấu ăn tiếng Việt" — tiêu chí 4 của "Sẵn sàng v3.0" (B8).

Kênh mới (chưa có V7) thuộc nhóm `nau-an-vi`, hồ sơ ngách = đúng khuôn mẫu thật của kho
(`CHANNEL/_KHUON/ngach-mau.yaml`, ví dụ nấu ăn). Chứng minh luật ngách/quốc gia đi từ YAML, không
cứng trong mã:
  * `tuyen.csv` gieo từ `tep_khan_gia` của hồ sơ (kênh gốc không có tuyến tiếng Nhật nào);
  * `ung_vien_xep_hang` (đúng hàm vòng chọn nguồn và trạm dùng) CHỌN ĐƯỢC NGUỒN qua VPH;
  * từ loại trừ là của NGÁCH ("review phim" bị loại), còn từ loại trừ tiếng Nhật mặc định không
    còn tham gia ("BGM" — có trong `phan_tuyen.TU_LOAI_TRU` — không làm rơi một video nấu ăn);
  * bậc làm tròn view lấy từ `thi_truong.bac_lam_tron_view` (VN: "1,2 N"), không phải bậc 万.

Chỉ đĩa trong `tmp_path`, không mạng, không ví.
"""

from __future__ import annotations

import calendar
import datetime as dt
import io
import json
import os
import shutil

from core import cong_thuc_vph as vph
from core import danh_ba_doi_thu as db
from core import doi_thu_kenh as so
from core import mot_nut
from core import tu_chay
from core import tuyen_noi_dung as tn
from core.ho_so_ngach import doc_ngach
from core.phan_tuyen import TU_LOAI_TRU

GOC_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KHUON = os.path.join(GOC_KHO, "CHANNEL", "_KHUON", "ngach-mau.yaml")
K = "NAU-AN"
SAO = "saoSAOsao01"      # 2 ngày tuổi, gấp ~14 lần video cùng tuổi của kênh nguồn
BGM = "bgmBGMbgm01"      # video nấu ăn có chữ "BGM" — từ loại trừ tiếng Nhật, KHÔNG của ngách này
PHIM = "phimPHIM001"     # "review phim" — từ loại trừ CỦA NGÁCH


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _dung_kenh(tmp_path):
    goc = str(tmp_path)
    nhom = os.path.join(goc, "CHANNEL", "_NHOM", "nau-an-vi")
    os.makedirs(nhom)
    shutil.copyfile(KHUON, os.path.join(nhom, "ngach.yaml"))
    _ghi(os.path.join(goc, "CHANNEL", K, "kenh.yaml"),
         'ten: {0}\nnhom: "nau-an-vi"\nngon_ngu: vi\ntep: "1"\n'.format(K))
    assert tn.gieo_cho_kenh(goc, K, K, "1") >= 1, "tuyen.csv phải gieo được từ tep_khan_gia của hồ sơ"

    bay_gio = dt.datetime.utcnow()
    ngay = (bay_gio.date() - dt.timedelta(days=2)).isoformat()
    dong = [
        (SAO, "Bếp Nhà A", "Cách làm thịt kho trứng mềm thơm không bị đắng", 30000),
        ("aaaaaaaaa01", "Bếp Nhà A", "Canh chua cá lóc miền Tây", 2000),
        ("aaaaaaaaa02", "Bếp Nhà A", "Rau muống xào tỏi xanh giòn", 2400),
        ("aaaaaaaaa03", "Bếp Nhà A", "Cá kho tộ đậm đà", 1800),
        (BGM, "Bếp Nhà B", "Cách làm bánh flan mềm mịn — nhạc BGM nhẹ nhàng", 26000),
        ("bbbbbbbbb01", "Bếp Nhà B", "Chè đậu xanh nước cốt dừa", 1500),
        ("bbbbbbbbb02", "Bếp Nhà B", "Sinh tố bơ sánh mịn", 1600),
        ("bbbbbbbbb03", "Bếp Nhà B", "Trà sữa trân châu tại nhà", 1700),
        (PHIM, "Bếp Nhà B", "Review phim ẩm thực hay nhất năm", 90000),
    ]
    cot = so.cot_mac_dinh()
    hang = []
    for ma, kenh_nguon, td, view in dong:
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": kenh_nguon, "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": str(view), "Ngày đăng": ngay, so.COT_TUYEN: "1", "Thời lượng": "15:00"})
        hang.append([d.get(c, "") for c in cot])
    so.luu_bang(goc, K, cot, hang)
    _ghi(os.path.join(so.thu_muc_nghien_cuu(goc, K), so.TEP_CAI),
         json.dumps({"quet_luc": calendar.timegm(bay_gio.timetuple())}))
    cot2 = list(db.COT)
    h2 = []
    for ten in ("Bếp Nhà A", "Bếp Nhà B"):
        r = dict.fromkeys(cot2, "")
        r.update({"Kênh": ten, "Trạng thái": db.THEO_DOI, "Link kênh": "https://www.youtube.com/@" + ten[-1]})
        h2.append([r[c] for c in cot2])
    db.luu(goc, K, cot2, h2)
    return goc


def test_ho_so_nau_an_doc_tu_khuon_that(tmp_path):
    goc = _dung_kenh(tmp_path)
    hs = doc_ngach(goc, K)
    assert hs.co() and hs.thi_truong.get("quoc_gia") == "VN"
    assert not set(hs.tu_loai_tru) & set(TU_LOAI_TRU), "khuôn nấu ăn không được mang từ loại trừ tiếng Nhật"
    assert mot_nut.tuyen_dang_danh(goc, K) == ["1"]


def test_kenh_nau_an_chay_kho_chon_duoc_nguon(tmp_path):
    goc = _dung_kenh(tmp_path)
    nhat_ky = []
    ds = tu_chay.ung_vien_xep_hang(goc, K, False, set(), log=nhat_ky.append)
    ma = [d.get("ma") for d in ds]
    assert ds, "kênh ngách nấu ăn phải chọn được nguồn: {0}".format(nhat_ky)
    assert ds[0]["ma"] in (SAO, BGM) and ds[0].get("nguon") == "vph", ds[0]
    assert SAO in ma
    assert BGM in ma, "chữ BGM (từ loại trừ tiếng Nhật) không được loại video nấu ăn của ngách này"
    assert PHIM not in ma, "từ loại trừ CỦA NGÁCH ('review phim') phải loại"


def test_bac_lam_tron_view_theo_thi_truong_vn(tmp_path):
    goc = _dung_kenh(tmp_path)
    bac = vph.bac_lam_tron_tu_ngach(doc_ngach(goc, K))
    assert vph._bac_hien_thi(135_000, bac) == 1_000 and vph._bac_hien_thi(5_000, bac) == 100
    assert vph._bac_hien_thi(2_500_000, bac) == 100_000   # "2,5 Tr" — khác bậc 万 của tiếng Nhật
    assert vph._bac_hien_thi_jp(2_500_000) == 10_000
