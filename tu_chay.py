"""CLI: chạy chu kỳ ngày cho kênh "tự chạy" — không mở giao diện.

    python tu_chay.py --kenh TL4-T7           chạy THẬT một kênh (tốn ví)
    python tu_chay.py --kenh TL4-T7 --thu      chế độ THỬ: chọn nguồn, không tốn tiền
    python tu_chay.py --tat-ca                 mọi kênh có `tu_chay: true`, lần lượt
    python tu_chay.py --tat-ca --thu           như trên, chế độ thử
    python tu_chay.py --dieu-phoi              MỘT nhịp bộ điều phối (lịch ShopAPI-DieuPhoi, 10')

Dùng đúng `config.json` / kho bí mật của thư mục này — cùng ví ShopAPI mà tab
"Tự động" của giao diện đang dùng. Mai kia trạm chạy lệnh này qua lịch của VPS,
một lần một kênh một ngày; xem `core/tu_chay.py` cho luật đầy đủ (nghiên cứu →
chọn nguồn → van ngân sách → sản xuất → bàn giao).

═══ CHẾ ĐỘ ĐIỀU PHỐI (29/09/2026, `core/dieu_phoi.py`) ═══

Máy VPS + `workspace/cai-dat.json: "dieu_phoi": true`:
  * `--kenh X` KHÔNG giữ `.khoa-may` cả lượt nữa — giữ MỘT làn API (`core.khe`)
    + khoá kênh; phụ đề/dựng/nối giọng/QA giữ khe "nang" quanh đúng khâu đó.
    Chờ làn quá 50 phút (hoặc 2 phút khi do điều phối sinh) → thoát mã 3.
  * `--tat-ca` = đồng bộ nhóm + bảo trì rẻ từng kênh + dọn đĩa + sổ ngày, rồi
    MỘT nhịp điều phối (sinh lượt tách rời cho kênh thiếu kho đệm nhất).
Tắt → y như trước (và chờ `.khoa-may` giờ có trần 50 phút → mã 3).
"""

from __future__ import annotations

import argparse
import atexit
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.api import build_client  # noqa: E402
from core.config import CONFIG_FILENAME, load_config  # noqa: E402
from core.tu_chay import (bo_log_tat_ca, chay_nhieu_kenh, chay_tat_ca,
                          giu_khoa_may, nha_khoa_may)  # noqa: E402

#: Trần chờ `.khoa-may` (chế độ cũ) / làn API (điều phối) trước khi thoát mã 3.
TRAN_CHO_KHOA_GIAY = 50 * 60
MA_THOAT_HET_GIO = 3


def _nhan_ket_qua(dong: dict) -> str:
    """V2-tối-giản (chẩn đoán 26/09/2026): nhãn in trước mỗi dòng kết quả một
    kênh. Máy đứng im CHỜ MỘT NGƯỜI (vd còn gói chờ đăng) không còn được gọi
    là "[OK]" — xem `core.tu_chay.chay_mot_ngay`/`finalize`."""
    if dong.get("cho_nguoi"):
        return "[CHỜ NGƯỜI] "
    return "[OK]  " if dong["ok"] else "[LỖI] "


def _ma_thoat(bao_cao: dict) -> int:
    """Mã thoát của tiến trình — V2-tối-giản, ba mức, không xây thêm hệ trạng
    thái nào khác:

    * `1`  — có kênh thật sự LỖI (`bao_cao["co_loi"]`, không đổi so với trước).
    * `2`  — KHÔNG kênh nào lỗi, nhưng MỌI kênh (đã chạy) đều đang CHỜ NGƯỜI
      (còn gói chờ đăng) — máy rảnh vì người chưa bấm nút, không phải vì
      không có gì để làm; lịch Windows/gac_tong đọc mã này để biết cần nhắc.
    * `0`  — còn lại (ít nhất một kênh chạy trơn tru bình thường, hoặc không
      có kênh nào để chạy).
    * `3`  — chờ khoá (làn API / `.khoa-may`) quá 50 phút, bỏ lượt này.
    """
    if bao_cao.get("co_loi"):
        return 1
    ket_qua = bao_cao.get("ket_qua") or []
    if ket_qua and all(d.get("cho_nguoi") for d in ket_qua):
        return 2
    return 0


def _log_kenh(ma: str):
    """Lượt một kênh ở chế độ điều phối: ghi `tu-chay.log` (có tiền tố kênh —
    nhiều lượt song song cùng ghi) VÀ in ra nhật ký riêng của tiến trình."""
    ghi_dia = bo_log_tat_ca(BASE_DIR, in_console=False)

    def log(dong: str) -> None:
        ghi_dia("[{0}] {1}".format(ma, dong))
        if sys.stdout is not None:
            try:
                print(dong)
            except Exception:  # noqa: BLE001
                pass
    return log


def _chay_kenh_dieu_phoi(args, che_do: str) -> int:
    from core import dieu_phoi, khe  # noqa: PLC0415

    log = _log_kenh(args.kenh)
    cho = 120 if args.tu_dieu_phoi else TRAN_CHO_KHOA_GIAY
    config = load_config(os.path.join(BASE_DIR, CONFIG_FILENAME))
    if config.problem:
        log("Không đọc được cấu hình: " + config.problem)
        return 1
    try:
        with khe.giu(BASE_DIR, khe.LOP_API, viec="san_xuat", kenh=args.kenh, uu_tien=2,
                     cho_toi_da=cho):
            log("── lượt điều phối kênh {0} (PID {1}) — giữ 1 làn API ──".format(
                args.kenh, os.getpid()))
            dieu_phoi.cai_moc_tien_trinh(BASE_DIR, kenh=args.kenh, ghi=log)
            client = build_client(config)
            ngay = time.strftime("%Y-%m-%d")
            _so_truoc, chi_truoc = dieu_phoi._chi_hom_nay(BASE_DIR, args.kenh, ngay)  # noqa: SLF001
            bao_cao = chay_nhieu_kenh(BASE_DIR, [args.kenh], client=client, che_do=che_do,
                                      on_log=log)
            _so_sau, chi_sau = dieu_phoi._chi_hom_nay(BASE_DIR, args.kenh, ngay)  # noqa: SLF001
    except khe.KheHetGio as loi:
        log("Chờ làn sản xuất quá {0:.0f} phút — bỏ lượt này (mã 3): {1}".format(cho / 60, loi))
        return MA_THOAT_HET_GIO
    for dong in bao_cao["ket_qua"]:
        log(_nhan_ket_qua(dong) + dong["tom_tat"])
    try:
        dieu_phoi.ghi_so_ngay_luot(BASE_DIR, bao_cao["ket_qua"],
                                   tong_uoc_vnd=max(0, chi_sau - chi_truoc))
    except Exception as loi:  # noqa: BLE001 — sổ chung hỏng không đổi kết quả lượt
        log("  (không ghi được sổ ngày dùng chung: {0})".format(str(loi)[:150]))
    return _ma_thoat(bao_cao)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chạy chu kỳ ngày cho kênh tự chạy.")
    nhom = ap.add_mutually_exclusive_group(required=True)
    nhom.add_argument("--kenh", help="Mã một kênh, ví dụ TL4-T7 (đúng tên thư mục trong CHANNEL/).")
    nhom.add_argument("--tat-ca", action="store_true",
                      help="Mọi kênh có `tu_chay: true` trong kenh.yaml, chạy LẦN LƯỢT.")
    nhom.add_argument("--dieu-phoi", action="store_true",
                      help="Một nhịp bộ điều phối (sinh lượt song song) — lịch ShopAPI-DieuPhoi.")
    ap.add_argument("--thu", action="store_true",
                    help="Chế độ thử: nghiên cứu + chọn nguồn, KHÔNG sản xuất, không tốn ví.")
    ap.add_argument("--tu-dieu-phoi", action="store_true",
                    help="(nội bộ) lượt do bộ điều phối sinh — chờ làn tối đa 2 phút.")
    args = ap.parse_args(argv)

    che_do = "thu" if args.thu else "that"

    from core import dieu_phoi  # noqa: PLC0415

    if args.dieu_phoi:
        log = bo_log_tat_ca(BASE_DIR, in_console=True)
        try:
            ket = dieu_phoi.nhip(BASE_DIR)
        except Exception as loi:  # noqa: BLE001 — pythonw không có console, phải tự ghi
            log("[ĐIỀU PHỐI] LỖI NGOÀI DỰ KIẾN: {0}".format(loi))
            return 1
        return 0 if ket.get("bat") is not False else 0

    dieu_phoi_bat = dieu_phoi.bat(BASE_DIR) and not args.thu
    if dieu_phoi_bat and args.kenh:
        return _chay_kenh_dieu_phoi(args, che_do)

    # Khoá TOÀN VPS trước cả bước đọc khoá API. Như vậy lịch Windows vừa thức
    # dậy sẽ rời ngay nếu một lượt bấm tay đang dựng video, dù cấu hình của tài
    # khoản chạy lịch có khác tài khoản đang mở giao diện.
    # Khoá riêng từng kênh chỉ
    # ngăn trùng cùng kênh; nó từng cho lịch chạy TL1/TL2 đồng thời với một cú
    # bấm tay đang dựng TL3 và làm máy quá tải thật.
    # Điều phối BẬT: `--tat-ca` chỉ bảo trì + sinh lượt, KHÔNG giữ `.khoa-may`
    # (việc nặng tự giữ khe "nang" quanh đúng khâu của nó); `--thu` không làm
    # việc nặng nên cũng không cần khoá máy.
    log_khoa = bo_log_tat_ca(BASE_DIR) if args.tat_ca else print
    can_khoa_may = not dieu_phoi_bat and not (args.thu and dieu_phoi.bat(BASE_DIR))
    if can_khoa_may:
        ok_khoa, ly_do_khoa = giu_khoa_may(BASE_DIR)
        if not ok_khoa:
            if not os.path.isfile(os.path.join(BASE_DIR, "vps.json")):
                log_khoa("Bỏ qua lượt này: " + ly_do_khoa)
                return 0
            log_khoa("Đang xếp hàng: " + ly_do_khoa)
            bat_dau_cho = time.time()
            while not ok_khoa:
                if time.time() - bat_dau_cho > TRAN_CHO_KHOA_GIAY:
                    log_khoa("Chờ khoá máy quá {0} phút — bỏ lượt này (mã 3).".format(
                        TRAN_CHO_KHOA_GIAY // 60))
                    return MA_THOAT_HET_GIO
                time.sleep(30)
                ok_khoa, ly_do_khoa = giu_khoa_may(BASE_DIR)
            log_khoa("Việc trước đã xong — bắt đầu lượt sản xuất tuần tự.")
        # `atexit` là lưới cuối cho mọi nhánh return/ngoại lệ. Hàm nhả chỉ xóa khi
        # chính PID này sở hữu nên gọi thêm ở đường bình thường cũng an toàn.
        atexit.register(nha_khoa_may, BASE_DIR)

    config = load_config(os.path.join(BASE_DIR, CONFIG_FILENAME))
    if config.problem:
        log_khoa("Không đọc được cấu hình: " + config.problem)
        nha_khoa_may(BASE_DIR)
        return 1
    client = build_client(config)

    if args.tat_ca:
        # `pythonw.exe` (Task Scheduler gọi tới, xem `core/lich_tu_chay.py`)
        # không có console — mọi dòng in phải qua đường ghi-đĩa an toàn này,
        # KHÔNG được gọi `print()` trực tiếp ở nhánh này.
        log = bo_log_tat_ca(BASE_DIR)
        log("─" * 60)
        log("Bắt đầu `tu_chay.py --tat-ca` (chế độ {0}{1}).".format(
            che_do, " · điều phối" if dieu_phoi_bat else ""))
        try:
            if dieu_phoi_bat:
                bao_cao = chay_tat_ca(BASE_DIR, client=client, che_do=che_do, on_log=log,
                                      chay_mot_ngay_fn=dieu_phoi.bao_tri_kenh)
            else:
                bao_cao = chay_tat_ca(BASE_DIR, client=client, che_do=che_do, on_log=log)
        except Exception as loi:  # noqa: BLE001 — không ai đọc traceback trên console pythonw, phải tự ghi
            log("LỖI NGOÀI DỰ KIẾN, dừng --tat-ca: {0}".format(loi))
            nha_khoa_may(BASE_DIR)
            return 1
        log("")
        for dong in bao_cao["ket_qua"]:
            log(_nhan_ket_qua(dong) + dong["tom_tat"])
        log("Xong `--tat-ca` — {0}.".format("CÓ lỗi" if bao_cao["co_loi"] else "không lỗi"))
        ma_ra = _ma_thoat(bao_cao)
        nha_khoa_may(BASE_DIR)
        if dieu_phoi_bat:
            try:
                dieu_phoi.nhip(BASE_DIR)
            except Exception as loi:  # noqa: BLE001
                log("[ĐIỀU PHỐI] nhịp cuối --tat-ca hỏng: {0}".format(loi))
        return ma_ra

    bao_cao = chay_nhieu_kenh(BASE_DIR, [args.kenh], client=client, che_do=che_do, on_log=print)
    print("")
    for dong in bao_cao["ket_qua"]:
        print(_nhan_ket_qua(dong) + dong["tom_tat"])
    ma_ra = _ma_thoat(bao_cao)
    nha_khoa_may(BASE_DIR)
    return ma_ra


if __name__ == "__main__":
    sys.exit(main())
