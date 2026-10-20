"""20/10/2026 — trần video/ngày theo ổ đĩa: mô hình "thời gian sống của phần nặng" (đo từ sổ dọn), không còn lấy
"mọi kênh luôn đầy giu+1 lượt" làm phần cố định (bản cũ ra 0 video/ngày khi ổ còn 20 GB). Cây giả trong tmp, tệp thưa."""

import json
import os
import time

from core import cong_suat

MB = 1024 ** 2
GB = 1024.0 ** 3


def _tep(p, byte):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.truncate(byte)


def _luot(goc, kenh, luot, t0, nang_mb=0, video_mb=0, mtime=None):
    thu = os.path.join(goc, "PROJECTS", "AUTO", kenh, luot)
    os.makedirs(thu, exist_ok=True)
    with open(os.path.join(thu, "trang-thai.json"), "w", encoding="utf-8") as f:
        json.dump({"khau": {"kich-ban": {"bat_dau": t0, "ket_thuc": t0 + 600, "trang_thai": "xong"}}}, f)
    if nang_mb:
        _tep(os.path.join(thu, "6-clip", "1.mp4"), nang_mb * MB)
    if video_mb:
        _tep(os.path.join(thu, "8-video.mp4"), video_mb * MB)
    if mtime is not None:
        os.utime(thu, (mtime, mtime))
    return thu


def test_tran_o_dia_theo_thoi_gian_song_phan_nang(tmp_path):
    goc = str(tmp_path)
    bay = time.time()
    for k, bat in (("KA", True), ("KB", True), ("KC", False)):          # KC: tắt / trả kho — phần nặng kẹt
        d = tmp_path / "CHANNEL" / k
        (d / "tu-chay").mkdir(parents=True)
        (d / "kenh.yaml").write_text("tu_chay: {0}\ngiu_toi_da_luot: 3\n".format("true" if bat else "false"),
                                     encoding="utf-8")
    log = []
    for i in range(4):                                                  # 4 lượt đã dọn: giữ nặng đúng 0,5 ngày
        t0 = bay - (i + 2) * 86400
        _luot(goc, "KA", "{0:04d}".format(i + 1), t0)
        log.append("{0}\tgói KA-{1:04d}\txoá 18 mục\t{2} byte\tDONE: đã lên YouTube".format(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0 + 43200)), i + 1, 700 * MB))
    (tmp_path / "CHANNEL" / "KA" / "tu-chay" / "don-dep.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    _luot(goc, "KA", "0010", bay - 3600, nang_mb=40, video_mb=60)       # đang chờ lên: nặng sẽ được dọn
    _luot(goc, "KB", "0003", bay - 7200, nang_mb=40, video_mb=60)
    _luot(goc, "KB", "0001", bay - 20 * 86400, nang_mb=300, mtime=bay - 20 * 86400)   # hỏng bỏ dở, cũ: kẹt
    _luot(goc, "KC", "0005", bay - 3600, nang_mb=500, video_mb=60)      # kênh không tự chạy: kẹt
    o = cong_suat.tran_theo_o_dia(goc, con_trong_gb=12.0, bay_gio=bay)
    assert o["so_kenh"] == 2 and o["mau_giu_nang"] == 4 and abs(o["ngay_giu_nang"] - 0.5) < 0.01
    assert abs(o["nang_se_don_gb"] - 200 * MB / GB) < 0.01                 # 2 lượt × (40 + 60) MB; không tính kẹt
    g = 100 * MB / GB                                                    # lượt còn nguyên: 40 + 60 MB
    ngan_sach = 12.0 + 200 * MB / GB - cong_suat.NGUONG_O_CHAN_GB
    assert abs(o["ngan_sach_gb"] - round(ngan_sach, 1)) < 0.06
    assert abs(o["tran_video_ngay"] - ngan_sach / (g * 0.5)) < 0.2 and o["tran_video_ngay"] > 0
    assert "giữ ~0.5 ngày" in cong_suat.cau_o_dia(o) and o["chan_tren_projects_gb"] > 0


def test_tran_o_dia_het_ngan_sach_va_mac_dinh_khi_chua_do(tmp_path):
    goc = str(tmp_path)
    bay = time.time()
    d = tmp_path / "CHANNEL" / "KA"
    d.mkdir(parents=True)
    (d / "kenh.yaml").write_text("tu_chay: true\n", encoding="utf-8")
    _luot(goc, "KA", "0001", bay - 3600, video_mb=60)
    o = cong_suat.tran_theo_o_dia(goc, con_trong_gb=9.0, bay_gio=bay)    # dưới sàn: trần 0
    assert o["tran_video_ngay"] == 0.0 and o["ngay_giu_nang"] == cong_suat.NGAY_GIU_NANG_MAC_DINH
    assert cong_suat.tran_theo_o_dia(goc, con_trong_gb=20.0, bay_gio=bay)["tran_video_ngay"] > 0
