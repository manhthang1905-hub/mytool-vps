"""Chạy `tu_chay.py` cho từng kênh, LẶP LẠI tới khi có `8-video.mp4`.

═══ VÌ SAO CÓ TỆP NÀY (22/09/2026) ═══

Chiều 22/09 ba kênh chạy SONG SONG: hơn 400 việc ảnh/clip đổ vào nhà máy ảnh
cùng lúc, và nó trả `503 engine_unavailable` ("không có chỗ nào nhận việc").
Tool bên trong đã thử lại đúng cách (không bị trừ tiền, không mất phần đã làm),
nhưng lượt chạy bị treo ở đó tới khi phiên điều khiển tắt, và tiến trình chết
theo — mất cả đêm mà không ra video.

Hai việc tệp này làm, đều là thứ `tu_chay.py` một mình không làm được:

1. **Chạy LẦN LƯỢT, không song song.** Một kênh một lúc. Chậm hơn nhưng không
   tự chặn mình — đúng luật 4 trong `CLAUDE.md` (hỏi dày/bắn dày không làm việc
   xong sớm hơn, chỉ lấy mất CPU và đường truyền của chính máy chủ đang làm).
2. **Chạy LẠI khi lượt trước chết giữa chừng.** `tu_chay.py` vốn đã biết làm
   tiếp lượt dở (`_tim_run_chua_xong`, và mỗi khâu có vân tay nên ảnh/clip đã
   có không làm lại). Nên chạy lại là tiếp tục, không phải bắt đầu từ đầu —
   tiền đã tiêu không mất.

Không hỏi máy chủ bằng cách nào khác, không đụng vào lượt đang chạy. Dừng bằng
Ctrl+C hoặc đóng tiến trình.

Dùng:  python chay-den-khi-xong.py TL1-T7 TL2-T7 TL3-T7
"""
from __future__ import annotations

import datetime as _dt
import os
import subprocess
import sys
import time

GOC = os.path.dirname(os.path.abspath(__file__))

#: Tối đa bao nhiêu lượt chạy lại cho MỘT kênh trước khi bỏ và sang kênh sau.
#: 12 lượt × (một lượt chạy tới khi kẹt) là quá đủ cho một đợt máy chủ bận;
#: nhiều hơn nữa thì vấn đề không phải "bận tạm" và cần người xem.
SO_LUOT_TOI_DA = 12

#: Nghỉ giữa hai lượt chạy lại của cùng một kênh. Máy chủ vừa báo hết chỗ thì
#: quay lại sau ba phút; nện lại ngay chỉ làm nó bận thêm.
NGHI_GIAY = 180


def _ghi(chu: str) -> None:
    dong = "[{0}] {1}".format(_dt.datetime.now().strftime("%H:%M:%S"), chu)
    print(dong, flush=True)


def _duong_video(kenh: str) -> str:
    thu_muc = os.path.join(GOC, "PROJECTS", "AUTO", kenh)
    if not os.path.isdir(thu_muc):
        return ""
    for ten in sorted(os.listdir(thu_muc), reverse=True):
        video = os.path.join(thu_muc, ten, "8-video.mp4")
        if os.path.isfile(video):
            return video
    return ""


def _dem(kenh: str, ten: str) -> int:
    thu_muc = os.path.join(GOC, "PROJECTS", "AUTO", kenh)
    tong = 0
    if os.path.isdir(thu_muc):
        for luot in os.listdir(thu_muc):
            duong = os.path.join(thu_muc, luot, ten)
            if os.path.isdir(duong):
                tong += len(os.listdir(duong))
    return tong


def chay_mot_kenh(kenh: str) -> bool:
    """Chạy tới khi kênh này có video, hoặc hết lượt. `True` nếu có video."""
    video = _duong_video(kenh)
    if video:
        _ghi("{0}: ĐÃ CÓ video sẵn — bỏ qua ({1})".format(kenh, video))
        return True
    nhat_ky = os.path.join(GOC, "workspace", "tu-chay",
                           "chay-den-khi-xong-{0}.log".format(kenh))
    os.makedirs(os.path.dirname(nhat_ky), exist_ok=True)
    for luot in range(1, SO_LUOT_TOI_DA + 1):
        _ghi("{0}: lượt {1}/{2} — ảnh {3}, clip {4}".format(
            kenh, luot, SO_LUOT_TOI_DA, _dem(kenh, "5-anh"), _dem(kenh, "6-clip")))
        with open(nhat_ky, "a", encoding="utf-8") as tep:
            tep.write("\n===== lượt {0} lúc {1} =====\n".format(
                luot, _dt.datetime.now().isoformat(timespec="seconds")))
            tep.flush()
            try:
                subprocess.run(
                    [sys.executable, "-u", "-X", "utf8",
                     os.path.join(GOC, "tu_chay.py"), "--kenh", kenh],
                    cwd=GOC, stdout=tep, stderr=subprocess.STDOUT, timeout=6 * 3600)
            except subprocess.TimeoutExpired:
                tep.write("\n(lượt này quá 6 giờ — cắt, sẽ chạy lại)\n")
            except Exception as loi:  # noqa: BLE001 — một lượt hỏng không được dừng cả bộ
                tep.write("\n(lượt này hỏng: {0})\n".format(loi))
        video = _duong_video(kenh)
        if video:
            _ghi("{0}: ✅ XONG VIDEO — {1:.0f} MB".format(
                kenh, os.path.getsize(video) / 1048576))
            return True
        if luot < SO_LUOT_TOI_DA:
            _ghi("{0}: chưa ra video — nghỉ {1}s rồi chạy tiếp (phần đã làm giữ nguyên)"
                 .format(kenh, NGHI_GIAY))
            time.sleep(NGHI_GIAY)
    _ghi("{0}: ✕ hết {1} lượt vẫn chưa ra video — cần người xem".format(
        kenh, SO_LUOT_TOI_DA))
    return False


def main() -> int:
    cac_kenh = sys.argv[1:] or ["TL1-T7", "TL2-T7", "TL3-T7"]
    _ghi("bắt đầu, chạy LẦN LƯỢT: " + ", ".join(cac_kenh))
    xong = []
    for kenh in cac_kenh:
        if chay_mot_kenh(kenh):
            xong.append(kenh)
    _ghi("kết thúc — có video: {0}/{1} ({2})".format(
        len(xong), len(cac_kenh), ", ".join(xong) or "không kênh nào"))
    return 0 if len(xong) == len(cac_kenh) else 1


if __name__ == "__main__":
    raise SystemExit(main())
