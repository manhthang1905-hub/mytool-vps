"""Agent chạy TRÊN MÁY ẢO của kênh — vòng lặp hỏi việc từ trạm của tool.

Xem bức tranh và các quyết định ở `vm/KE-HOACH.md`. Tóm tắt luật của tệp này:

* **Chỉ thư viện chuẩn.** Máy ảo có Python là chạy — không pip, không cài gì.
* **Chỉ GỌI VỀ trạm, không mở cổng nào.** Mỗi lượt hỏi là một nhịp tim.
* **Hỏng thì chờ rồi hỏi lại, đừng chết.** Máy nhà tắt tool, mạng chập — agent
  cứ kiên nhẫn; nó là thứ chạy 24/7 không ai nhìn.
* Nhịp hỏi 30 giây — đúng luật chung của cả dây chuyền: hỏi dày hơn không làm
  việc xong sớm hơn, chỉ tốn đường truyền.

Việc nhận được (`loai`):

    quet-studio     mở Chrome vào Studio để extension cào, đợi rồi báo xong
    quet-trang-chu  mở Chrome vào trang chủ YouTube — extension (từ v2.3.0)
                    gom các kênh được đề xuất, gửi về sổ đối thủ của trạm
    dang-video      tải kế hoạch đăng của kênh về máy ảo; máy có điền
                    `tool_dang` (đường tới tool đăng D:\\upload) thì mở nó lên
    tra-loi-binh-luan (giai đoạn 5 — bản này báo "chưa làm được")

Lịch cố định (giai đoạn 2): điền `"gio_quet": "07:30"` vào config là mỗi ngày
đến giờ ấy agent tự quét Studio (và trang chủ, nếu bật `quet_trang_chu_hang_
ngay`) — không cần ai ra lệnh. Lệnh tay từ tool luôn được làm TRƯỚC lịch.

Chạy: `python agent.py` (hoặc nhấp đúp `CHAY-AGENT.bat`).
"""

from __future__ import annotations

import csv
import ctypes
import io
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile

#: Nhịp hỏi việc. 30 giây — lệnh tới chậm nhất nửa phút, đủ nhanh cho việc
#: tính bằng phút, đủ thưa để không nện trạm.
NHIP_GIAY = 30

#: Đợi bao lâu cho một lượt quét Studio trước khi đóng Chrome. Extension tự
#: chụp lần lượt các video; đo thật mỗi video chừng một phút.
CHO_QUET_GIAY = 8 * 60

#: Thư mục gốc của agent — MỌI đường ghi (`agent.log`, `trang-thai.json`,
#: `dang-lam.json`, `tien-ich/`, `.khoa-may` dùng chung với `core.tu_chay`…)
#: suy ra từ đây. Mặc định là thư mục CHỨA CHÍNH `agent.py` (máy ảo thật).
#:
#: Đợt 0.2 cô lập test (29/09/2026, kiểm toán): bộ `pytest` nạp module này
#: bằng `importlib` thẳng từ đường dẫn THẬT (`vm/agent.py`), nên nếu bài kiểm
#: quên tự bẻ `GOC` — như `TestAgentGoiVe` trong `tests/test_vm_agent.py` đã
#: quên — nó ghi thẳng vào NHẬT KÝ THẬT của máy ảo đang chạy (đo được: hơn
#: 1.167 dòng "vm-thu"/"pytest-of" lẫn vào `vm/agent.log` thật). Biến môi
#: trường `SHOPAPI_VM_GOC` là LƯỚI AN TOÀN THỨ HAI (lưới thứ nhất vẫn là tự
#: bẻ `GOC` trong từng bài, như `tests/test_loi_thoai_trinh_duyet._nap_agent`
#: đã làm): `tests/conftest.py` đặt biến này về một `tmp_path` cho MỌI bài,
#: nên bài nào QUÊN tự bẻ cũng không còn chạm được tới đĩa thật. Máy ảo thật
#: không đặt biến này bao giờ nên hành vi sản xuất không đổi.
GOC = os.environ.get("SHOPAPI_VM_GOC") or os.path.dirname(os.path.abspath(__file__))

# Khoá tài nguyên dùng chung với ``core.tu_chay`` khi ``vm/`` nằm trong MyTool.
# Agent vẫn chạy độc lập như cũ nếu được chép sang máy khác không có ``vps.json``.
_KHOA_MAY_DANG_GIU = False


def _duong_khoa_may_chung() -> str:
    goc_tool = os.path.dirname(GOC)
    if not os.path.isfile(os.path.join(goc_tool, "vps.json")):
        return ""
    return os.path.join(goc_tool, "workspace", "tu-chay", ".khoa-may")


def _pid_con_song(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        ra = subprocess.run(
            ["tasklist", "/FI", "PID eq {0}".format(pid), "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # Không có quyền đọc danh sách tiến trình thì phải giả định chủ khoá
        # vẫn sống. Xoá khoá khi không chắc chắn có thể làm hai việc nặng chạy đôi.
        if ra.returncode != 0:
            return True
        return str(pid) in (ra.stdout or "")
    except Exception:  # noqa: BLE001
        return True


#: Phiên giữ khe "nang" qua `core/khe.py` (Đợt 1.5, 29/09/2026) — None khi
#: đang dùng đường cũ hoặc chưa giữ.
_PHIEN_KHE = None
_KHE_MOD = {"da_thu": False, "mod": None}


def _nap_khe():
    """Nạp `core/khe.py` của MyTool (CHỈ thư viện chuẩn — đúng luật `vm/`) như
    một mô-đun đứng riêng, không kéo cả gói `core`. Không có (vm/ chép sang máy
    khác) → None, dùng đường khoá cũ."""
    if _KHE_MOD["da_thu"]:
        return _KHE_MOD["mod"]
    _KHE_MOD["da_thu"] = True
    duong = os.path.join(os.path.dirname(GOC), "core", "khe.py")
    if not os.path.isfile(duong):
        return None
    try:
        import importlib.util  # noqa: PLC0415

        spec = importlib.util.spec_from_file_location("_khe_chung_vm", duong)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _KHE_MOD["mod"] = mod
    except Exception:  # noqa: BLE001 — nạp hỏng thì lùi về khoá cũ, agent vẫn sống
        _KHE_MOD["mod"] = None
    return _KHE_MOD["mod"]


def giu_khoa_may_chung(viec: str = "phien", kenh: str = "", uu_tien: int = 1) -> bool:
    """Giành quyền chạy đúng một việc nặng trên VPS; không có MyTool thì bỏ qua.

    Đợt 1.5 (29/09/2026): có `core/khe.py` thì xin khe "nang" qua đó (MỘT lần
    thử, không xếp hàng — nhịp tim 30 giây tự thử lại), kèm `viec` (quet /
    tai_len / viec) + `uu_tien` để sản xuất song song xếp hàng đúng luật và
    `core.bang_thong` biết lúc nào đang tải lên. Cùng tệp `.khoa-may`, cùng
    luật PID — mã cũ vẫn đọc được."""
    global _KHOA_MAY_DANG_GIU, _PHIEN_KHE
    duong = _duong_khoa_may_chung()
    if not duong:
        return True
    if _KHOA_MAY_DANG_GIU:
        return True
    if kenh and not _nhuong_kenh_nuoi(kenh):    # kênh đang được nuôi trang chủ: báo dừng, đợi đóng Chrome
        return False
    k = _nap_khe()
    if k is not None:
        try:
            phien = k.thu_giu(os.path.dirname(GOC), "nang", viec=viec, kenh=kenh,
                              uu_tien=uu_tien, han_giay=(40 * 60 if viec == "tai_len" else 45 * 60))
        except Exception:  # noqa: BLE001 — khe hỏng thì lùi về khoá cũ
            phien = None
            k = None
        if k is not None:
            if phien is None:
                if viec in ("tai_len", "phien", "viec"):    # việc ĐĂNG hụt khe: dựng cờ để sản xuất/quét nhường
                    try:
                        k.dat_co_cho_tai_len(os.path.dirname(GOC), True)
                    except Exception:  # noqa: BLE001
                        pass
                return False
            if viec in ("tai_len", "phien", "viec"):
                try:
                    k.dat_co_cho_tai_len(os.path.dirname(GOC), False)
                except Exception:  # noqa: BLE001
                    pass
            _PHIEN_KHE = phien
            _KHOA_MAY_DANG_GIU = True
            return True
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    for _lan in range(2):
        try:
            fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as tep:
                json.dump({"pid": os.getpid(), "bat_dau": time.time(),
                           "nguon": "agent-chrome"}, tep)
            _KHOA_MAY_DANG_GIU = True
            return True
        except FileExistsError:
            try:
                with open(duong, "r", encoding="utf-8") as tep:
                    cu = json.load(tep)
                pid = int(cu.get("pid") or 0)
                bat_dau = float(cu.get("bat_dau") or 0)
            except (OSError, ValueError, TypeError):
                pid, bat_dau = 0, 0
            if pid and time.time() - bat_dau < 12 * 3600 and _pid_con_song(pid):
                return False
            try:
                os.remove(duong)
            except OSError:
                return False
    return False


def doi_viec_khoa_may(viec: str) -> None:
    """Đổi nhãn `viec` của khe đang giữ (vd phiên sắp tải lên → "tai_len" để
    `core.bang_thong` tạm dừng tải về). Chỉ khi chính tiến trình này giữ."""
    duong = _duong_khoa_may_chung()
    if not duong or not _KHOA_MAY_DANG_GIU:
        return
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        if int(du.get("pid") or 0) != os.getpid():
            return
        du["viec"] = viec
        tam = duong + ".doi-viec.tam"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False)
        os.replace(tam, duong)
    except (OSError, ValueError, TypeError):
        pass


def nha_khoa_may_chung() -> None:
    global _KHOA_MAY_DANG_GIU, _PHIEN_KHE
    duong = _duong_khoa_may_chung()
    if not duong:
        return
    if _PHIEN_KHE is not None:
        try:
            _PHIEN_KHE.nha()
        except Exception:  # noqa: BLE001
            pass
        _PHIEN_KHE = None
        _KHOA_MAY_DANG_GIU = False
        return
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            pid = int((json.load(tep) or {}).get("pid") or 0)
        if pid == os.getpid():
            os.remove(duong)
    except (OSError, ValueError, TypeError):
        pass
    _KHOA_MAY_DANG_GIU = False


def doc_cau_hinh() -> dict:
    with open(os.path.join(GOC, "config.json"), "r", encoding="utf-8") as tep:
        return json.load(tep)


#: Quá ngưỡng này (byte) thì `ghi()` xoay vòng nhật ký — chạy nhiều năm không
#: ai dọn thì `agent.log` phình vô hạn (đã thấy thực tế hơn 700KB chỉ sau vài
#: tuần). 5MB: đủ dài để mở ra đọc lại vài ngày gần nhất khi cần soi sự cố,
#: đủ ngắn để không bao giờ thành vấn đề trên một ổ đĩa máy ảo bé.
NHAT_KY_TOI_DA_BYTE = 5 * 1024 * 1024

#: Giữ tối đa bấy nhiêu bản cũ (`agent.log.1` .. `agent.log.3`) — đủ để lần
#: lại vài vòng xoay gần nhất mà không tích luỹ vô hạn theo năm.
NHAT_KY_SO_BAN_CU = 3


def _duong_nhat_ky() -> str:
    return os.path.join(GOC, "agent.log")


def _xoay_nhat_ky_neu_can() -> None:
    """Đổi `agent.log` -> `agent.log.1` (đẩy lùi các bản cũ hơn) khi vượt
    ngưỡng. Dùng `os.replace` (ghi đè NGUYÊN TỬ trên cả Windows lẫn POSIX,
    khác `os.rename` vốn kén trên Windows nếu đích đã tồn tại) nên an toàn dù
    có tiến trình khác đang xoay cùng lúc — tệ nhất là mất một bản cũ, không
    bao giờ hỏng/kẹt file. `ghi()` mở rồi đóng file ngay mỗi lần gọi (không
    giữ handle sống) nên không có chuyện xoay vòng bị chặn vì file đang mở.
    """
    duong = _duong_nhat_ky()
    try:
        if os.path.getsize(duong) < NHAT_KY_TOI_DA_BYTE:
            return
    except OSError:
        return  # chưa có file agent.log -> chưa cần xoay
    for i in range(NHAT_KY_SO_BAN_CU - 1, 0, -1):
        try:
            os.replace("{0}.{1}".format(duong, i), "{0}.{1}".format(duong, i + 1))
        except OSError:
            pass  # không có bản .i -> bỏ qua, không phải lỗi
    try:
        os.replace(duong, duong + ".1")
    except OSError:
        pass  # tiến trình khác vừa xoay xong -> bỏ qua, lần ghi kế mở file mới


def ghi(dong: str) -> None:
    chu = "{0} {1}".format(time.strftime("%H:%M:%S"), dong)
    print(chu, flush=True)
    try:
        _xoay_nhat_ky_neu_can()
        with open(_duong_nhat_ky(), "a", encoding="utf-8") as tep:
            tep.write(chu + "\n")
    except OSError:
        pass


def _goi(tram: str, duong: str, du_lieu: dict = None, cho: float = 20.0) -> dict:
    """Một lượt gọi trạm. Ném lỗi ra cho vòng ngoài xử — nó biết phải chờ."""
    url = tram.rstrip("/") + duong
    if du_lieu is None:
        yeu_cau = urllib.request.Request(url)
    else:
        yeu_cau = urllib.request.Request(
            url, data=json.dumps(du_lieu, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(yeu_cau, timeout=cho) as tra_loi:
        chu = tra_loi.read().decode("utf-8", "replace")
    try:
        return json.loads(chu)
    except ValueError:
        return {"chu": chu}


def chon_tram(cau_hinh: dict, in_ra=None) -> dict:
    """Chốt địa chỉ trạm từ các ứng viên tool đã điền sẵn lúc đóng gói.

    Đường đơn giản nhất (chủ dự án, 02/09/2026: *"bên tool chỉ cần setup để
    thư mục vm chuẩn... sau đó copy sang bên vm là được kết nối"*): tool ghi
    sẵn MỌI địa chỉ của máy nó vào `tram_ung_vien` trong config trước khi
    người dùng chép thư mục vm/ đi. Ghi nhiều vì máy ảo cạnh nhà thì với
    được địa chỉ mạng trong, VPS thuê ngoài thì phải đi địa chỉ IPv6 toàn
    cầu — agent cứ thử lần lượt, cái nào đáp thì chốt vào `tram`.

    Không cái nào đáp (tool đang tắt?) thì giữ cái đầu — vòng hỏi việc vốn
    chịu được trạm im, và lúc trạm im lâu nó sẽ gọi lại hàm này.
    """
    ung = [d for d in ([str(cau_hinh.get("tram") or "")] +
                       [str(d) for d in (cau_hinh.get("tram_ung_vien") or [])])
           if d]
    ung = list(dict.fromkeys(ung))
    if not ung:
        if in_ra:
            in_ra("config chưa có địa chỉ trạm nào — trên tool bấm "
                  "'Tạo bộ cài VM' rồi chép lại thư mục vm/ sang đây.")
        return cau_hinh
    # Câm lặng lúc dò là người dùng tưởng treo (02/09: "sao rồi không thấy
    # gì") — nên có in_ra thì nói từng bước, kể cả khi chỉ một ứng viên.
    if in_ra:
        in_ra("thử gọi trạm ({0} địa chỉ, mỗi địa chỉ chờ tối đa 4 giây)..."
              .format(len(ung)))
    for d in ung:
        try:
            dap = _goi(d, "/trang-thai", cho=4.0).get("ok")
        except Exception:  # noqa: BLE001 — ứng viên chết là chuyện dự tính
            dap = False
        if in_ra:
            in_ra("  {0} ... {1}".format(d, "ĐÁP ✓" if dap else "lặng"))
        if dap:
            cau_hinh["tram"] = d
            if in_ra:
                in_ra("NỐI ĐƯỢC TRẠM ✓ — cứ để cửa sổ này mở, agent tự làm "
                      "việc. Trên tool, tab Máy VM sẽ thấy máy này trong "
                      "vòng nửa phút.")
            return cau_hinh
    cau_hinh["tram"] = ung[0]
    if in_ra:
        in_ra("CHƯA GỌI ĐƯỢC TRẠM NÀO. Kiểm tra bên máy chính: tool đang "
              "mở chưa? mục Chỉ số kênh đã bấm 'Bật cổng nhận' chưa? "
              "Agent vẫn chạy và tự thử lại đều — không phải làm lại gì "
              "ở đây.")
    return cau_hinh


def tim_tram(cong: int = 8765, cho_giay: float = 3.0, dich=None,
             dich6=None) -> str:
    """Tự dò trạm trong mạng — hú một gói UDP, trạm nghe thấy là đáp.

    Địa chỉ trạm là câu hỏi khó nhất với người không rành mạng — nên không
    hỏi nữa: lấy địa chỉ NGUỒN của gói đáp làm địa chỉ trạm. Không thấy thì
    trả "" để bộ cài hỏi tay (đường lùi, không phải đường chính).

    Hú CẢ HAI TẦNG: quảng bá IPv4 và multicast IPv6 (ff02::1 — "mọi máy
    cùng dây"). Máy ảo của chủ dự án có con chỉ chạy IPv6 — thiếu tầng này
    là bên đó điếc hẳn. IPv6 không có quảng bá, và gói multicast phải chỉ
    rõ đi ra ngả nào, nên hú một vòng qua từng cạc mạng.
    """
    cac_o = []

    def mo(gia_dinh):
        try:
            o = socket.socket(gia_dinh, socket.SOCK_DGRAM)
            o.settimeout(0.2)
            cac_o.append(o)
            return o
        except OSError:
            return None

    o4 = mo(socket.AF_INET)
    o6 = mo(socket.AF_INET6)
    try:
        if o4 is not None:
            try:
                o4.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except OSError:
                pass
            for noi in (dich if dich is not None else ["255.255.255.255"]):
                try:
                    o4.sendto(b"shopapi-tram?", (noi, cong))
                except OSError:
                    pass
        if o6 is not None:
            for noi in (dich6 if dich6 is not None else ["ff02::1"]):
                if noi == "ff02::1":
                    try:
                        cac_nga = [i for i, _t in socket.if_nameindex()]
                    except OSError:
                        cac_nga = [0]
                    for nga in cac_nga:
                        try:
                            o6.setsockopt(
                                socket.IPPROTO_IPV6,
                                socket.IPV6_MULTICAST_IF,
                                struct.pack("I", nga))
                            o6.sendto(b"shopapi-tram?", (noi, cong))
                        except OSError:
                            pass
                else:
                    try:
                        o6.sendto(b"shopapi-tram?", (noi, cong))
                    except OSError:
                        pass

        het = time.time() + cho_giay
        while time.time() < het:
            for o in cac_o:
                try:
                    goi, nguon = o.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:
                    # Windows: gói dội "cổng đóng" (WinError 10054) nổ ngay
                    # trên recvfrom — không phải hết giờ, chỉ là chưa ai đáp
                    # ở tầng đó. Nghe tiếp tới hạn.
                    continue
                try:
                    du_lieu = json.loads(goi.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if du_lieu.get("shopapi_tram"):
                    return _dia_chi_tram(nguon, du_lieu, cong)
    finally:
        for o in cac_o:
            try:
                o.close()
            except OSError:
                pass
    return ""


def _dia_chi_tram(nguon, du_lieu, cong_mac_dinh: int) -> str:
    """Địa chỉ trạm từ một gói giới thiệu: NGUỒN gói + số cổng trong gói."""
    ip = str(nguon[0]).split("%")[0]
    so_cong = int(du_lieu.get("cong") or cong_mac_dinh)
    if ":" not in ip:
        return "http://{0}:{1}".format(ip, so_cong)
    # IPv6 phải bọc ngoặc vuông; địa chỉ "cùng dây" (fe80…) còn phải kèm số
    # ngả về máy này, %-mã-hoá thành %25 cho urllib nuốt được.
    if ip.lower().startswith("fe80") and len(nguon) > 3 and nguon[3]:
        ip = "{0}%25{1}".format(ip, nguon[3])
    return "http://[{0}]:{1}".format(ip, so_cong)


def cho_gioi_thieu(cong: int = 8765, cho_giay: float = 600.0,
                   in_ra=None) -> str:
    """VPS thuê ngoài: gói quảng bá không với tới trạm, nhưng TOOL biết địa
    chỉ VPS (tab VPS đã lưu). Nên đảo chiều: ngồi im nghe cổng UDP, trên tool
    bấm "Kết nối máy ảo VPS" là trạm gửi sang một gói giới thiệu — lấy địa
    chỉ NGUỒN của gói làm địa chỉ trạm, vẫn không phải gõ gì.

    Chủ dự án, 02/09/2026: *"tool đang có cái vps tl4-t7 nó có ip của ipv6
    mà"* — đúng, và đây là chỗ dùng cái địa chỉ đó.
    """
    cac_o = []
    for gia_dinh, dia_chi in ((socket.AF_INET, "0.0.0.0"),
                              (socket.AF_INET6, "::")):
        try:
            o = socket.socket(gia_dinh, socket.SOCK_DGRAM)
            o.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if gia_dinh == socket.AF_INET6:
                try:
                    o.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                except OSError:
                    pass
            o.bind((dia_chi, cong))
            o.settimeout(1.0)
            cac_o.append(o)
        except OSError:
            pass
    if not cac_o:
        return ""
    try:
        het = time.time() + cho_giay
        bao_luc = 0.0
        while time.time() < het:
            if in_ra and time.time() - bao_luc >= 60:
                bao_luc = time.time()
                in_ra("  ... van dang cho tool goi sang (con {0} phut)".format(
                    max(1, int((het - time.time()) / 60))))
            for o in cac_o:
                try:
                    goi, nguon = o.recvfrom(256)
                except socket.timeout:
                    continue
                except OSError:
                    continue
                try:
                    du_lieu = json.loads(goi.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if du_lieu.get("shopapi_tram"):
                    return _dia_chi_tram(nguon, du_lieu, cong)
    finally:
        for o in cac_o:
            try:
                o.close()
            except OSError:
                pass
    return ""


def _cac_goc_trinh_duyet() -> list:
    """Các thư mục có thể chứa bộ Chrome của kênh.

    Nếp cũ đặt ``vm`` cạnh thẳng ``TL1-T7``. Bản gọn hiện tại đặt ``vm`` bên
    trong ``MyTool`` còn bốn bộ Chrome vẫn nằm cạnh ``MyTool``. Nhận diện lớp
    bọc bằng dấu vết của tool để không quét rộng bừa sang thư mục ông.
    """
    cha = os.path.dirname(GOC)
    ra = [cha]
    if (os.path.isfile(os.path.join(cha, "vps.json"))
            or os.path.isdir(os.path.join(cha, "CHANNEL"))):
        ra.append(os.path.dirname(cha))
    return list(dict.fromkeys(os.path.abspath(x) for x in ra if x))


def doan_cac_kenh() -> list:
    """Đoán MỌI kênh nằm cạnh vm/ theo nếp `<MÃ>\\<MÃ>.exe`.

    Một VPS giờ phục vụ tới 5 kênh CÙNG NICHE, mỗi kênh một trình duyệt
    riêng nằm SIBLING nhau (`C:\\...\\TL\\TL4-T7\\TL4-T7.exe`,
    `C:\\...\\TL\\KENH2\\KENH2.exe`...) — trả về TẤT CẢ, để bộ cài
    (`cai_dat_vm.py`) đóng gói thẳng vào `cac_kenh`, không ai phải gõ tay.
    """
    thay = []
    for cha in _cac_goc_trinh_duyet():
        try:
            for ten in sorted(os.listdir(cha)):
                if os.path.isfile(os.path.join(cha, ten, ten + ".exe")) or \
                        os.path.isfile(os.path.join(cha, ten, ten, ten + ".exe")):
                    thay.append(ten)
        except OSError:
            pass
    return list(dict.fromkeys(thay))


def doan_kenh() -> str:
    """Đoán mã kênh khi máy CHỈ phục vụ một kênh (nếp cũ, một máy một kênh).

    Thư mục vm nằm cạnh Chrome của kênh (nếp của tool đăng) — quét các thư
    mục hàng xóm, thấy đúng MỘT bộ dạng `<X>\\<X>.exe` thì X là mã kênh.
    Thấy nhiều hay không thấy thì trả "" — đoán bừa còn tệ hơn hỏi (máy
    nhiều kênh thì dùng :func:`doan_cac_kenh`, không qua hàm này).
    """
    thay = doan_cac_kenh()
    return thay[0] if len(thay) == 1 else ""


def danh_sach_kenh(cau_hinh: dict) -> list:
    """Mọi kênh máy NÀY phục vụ.

    `cac_kenh` (bộ cài đóng gói cho VPS nhiều kênh) thắng nếu có; không thì
    về kênh đơn `kenh` (nếp một-máy-một-kênh cũ — giữ NGUYÊN cho mọi máy
    đang chạy, không đụng gì tới chúng).
    """
    nhieu = [str(k).strip() for k in (cau_hinh.get("cac_kenh") or []) if str(k).strip()]
    if nhieu:
        return list(dict.fromkeys(nhieu))
    don = str(cau_hinh.get("kenh") or "").strip()
    return [don] if don else []


def cau_hinh_kenh(cau_hinh: dict, kenh: str) -> dict:
    """Cấu hình hiệu lực CHO MỘT KÊNH, rút từ cấu hình chung của máy.

    Máy nhiều kênh: mỗi kênh một Chrome riêng (nếp `<MÃ>\\<MÃ>.exe` cạnh
    nhau) — trường `chrome` đơn trong config chỉ còn nghĩa khi máy CHỈ một
    kênh (nếp cũ); máy nhiều kênh thì để `tim_chrome` tự dò theo đúng kênh,
    trừ khi tool điền rõ trong `chrome_theo_kenh`.
    """
    ra = dict(cau_hinh)
    ra["kenh"] = kenh
    rieng = (cau_hinh.get("chrome_theo_kenh") or {}).get(kenh, "")
    nhieu = len(danh_sach_kenh(cau_hinh)) > 1
    ra["chrome"] = rieng or ("" if nhieu else cau_hinh.get("chrome", ""))
    return ra


def hoi_viec(cau_hinh: dict, kenh: str = None) -> dict:
    q = urllib.parse.urlencode({
        "kenh": kenh if kenh is not None else (cau_hinh.get("kenh") or "kenh"),
        "may": cau_hinh.get("ten_may") or socket.gethostname(),
    })
    return _goi(cau_hinh["tram"], "/viec?" + q)


#: Khoá mà TOOL được phép chỉnh từ xa. Phải khớp `core/vm_cai_dat.py` (có test
#: canh hai đầu). Địa chỉ trạm / mã kênh / đường Chrome / tool đăng KHÔNG nằm
#: đây: trạm là cổng không mật khẩu, không để nó đổi được "chương trình nào
#: sẽ chạy" trên máy này.
KHOA_TU_TOOL = ("gio_quet", "quet_trang_chu_hang_ngay", "cho_quet_giay",
                "cho_trang_chu_giay", "dong_chrome_sau_quet", "giu_chrome_mo",
                "tu_dang", "tu_tra_loi_cmt",
                "lay_loi_thoai", "cho_loi_thoai_giay",
                "che_do_phien", "phien_truoc_phut", "gio_phien",
                "cach_dang", "binh_luan_dom", "cmt_toi_da_phien", "ghim_dom")


def ap_cai_dat_tool(cau_hinh: dict, tu_tool, kenh_chinh: str = None) -> dict:
    """Cấu hình hiệu lực = config của máy + thiết lập tool đẩy xuống (thắng).

    Chỉ nhận đúng các khoá trong :data:`KHOA_TU_TOOL` — trạm lạ có đẩy gì
    khác cũng rơi ra ngoài.

    `kenh_chinh`: kênh ĐẦU của máy (nếp cũ / máy một-kênh) — chỉ kênh này
    mới ghi đè khoá TOP-LEVEL của `cai-dat-tool.json` (để GUI/may_dang/
    may_cmt đời cũ đọc thẳng vẫn ra một giá trị hợp lý); bỏ trống nghĩa là
    "luôn ghi top-level" — nếp gọi đơn-kênh cũ.
    """
    ra = dict(cau_hinh)
    if isinstance(tu_tool, dict):
        for khoa in KHOA_TU_TOOL:
            if khoa in tu_tool:
                ra[khoa] = tu_tool[khoa]
    kenh = str(ra.get("kenh") or "")
    la_chinh = (kenh_chinh is None) or (not kenh) or (kenh == kenh_chinh)
    _chep_cho_gui(ra, kenh=kenh, la_kenh_chinh=la_chinh)
    return ra


_GUI_DA_CHEP = {"chu": ""}      # bản đã ghi lần trước — chỉ ghi khi ĐỔI


def _don_kenh_cu_khoi_cai_dat_tool(cac_kenh) -> None:
    """Bỏ các khối kênh không còn thuộc VPS này.

    ``_chep_cho_gui`` cố ý đọc-ghép từng kênh trong một nhịp tim, nhưng
    nếu danh sách kênh bị rút gọn thì các khối cũ sẽ nằm lại mãi. Dọn
    một lần khi agent khởi động để GUI đăng/chăm kênh chỉ thấy đúng
    những kênh còn trong ``config.json``.
    """
    duong = os.path.join(GOC, "cai-dat-tool.json")
    try:
        with open(duong, encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError):
        return
    if not isinstance(goi, dict) or not isinstance(goi.get("kenh"), dict):
        return
    hop_le = {str(k) for k in cac_kenh if str(k).strip()}
    sach = {k: v for k, v in goi["kenh"].items() if k in hop_le}
    if sach == goi["kenh"]:
        return
    goi["kenh"] = sach
    tam = duong + ".tmp"
    try:
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(goi, tep, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tam, duong)
    except OSError:
        try:
            os.remove(tam)
        except OSError:
            pass


def _chep_cho_gui(hieu_luc: dict, kenh: str = "", la_kenh_chinh: bool = True) -> None:
    """Chép thiết lập hiệu lực + địa chỉ trạm xuống `cai-dat-tool.json`.

    GUI tool đăng (may_dang.py/may_cmt.py, nằm cạnh) đọc tệp này để biết: có
    được tự đăng không (`tu_dang`), có được tự trả lời bình luận không
    (`tu_tra_loi_cmt`), và trạm ở đâu (`tram` — cmt.py nhờ trạm viết câu trả
    lời bằng key của tool). Ghi nguyên tử, và chỉ ghi khi nội dung đổi để
    khỏi mài đĩa mỗi 30 giây.

    Máy NHIỀU kênh: mỗi kênh một khối riêng dưới khoá `"kenh"` — hàm này
    ĐỌC LẠI tệp trước khi ghi (vòng lặp `chay()` gọi nó mỗi kênh một lần
    trong cùng một nhịp tim; không đọc lại thì kênh sau ghi đè mất kênh
    trước). Khoá TOP-LEVEL (đời cũ) chỉ mang giá trị của kênh CHÍNH
    (`la_kenh_chinh`), để bên đọc cũ (chỉ biết một kênh) vẫn ra thứ dùng
    được.
    """
    goi = {}
    duong = os.path.join(GOC, "cai-dat-tool.json")
    try:
        with open(duong, encoding="utf-8") as tep:
            co_san = json.load(tep)
        if isinstance(co_san, dict):
            goi = co_san
    except (OSError, ValueError):
        pass
    rieng = {khoa: hieu_luc.get(khoa) for khoa in KHOA_TU_TOOL
             if khoa in hieu_luc}
    if kenh:
        theo_kenh = goi.get("kenh")
        if not isinstance(theo_kenh, dict):
            theo_kenh = {}
        theo_kenh[kenh] = rieng
        goi["kenh"] = theo_kenh
    if la_kenh_chinh or not kenh:
        goi.update(rieng)
    goi["tram"] = str(hieu_luc.get("tram") or "")
    chu = json.dumps(goi, ensure_ascii=False, indent=1, sort_keys=True)
    if chu == _GUI_DA_CHEP["chu"]:
        return
    try:
        with open(duong + ".tmp", "w", encoding="utf-8") as tep:
            tep.write(chu)
        os.replace(duong + ".tmp", duong)
        _GUI_DA_CHEP["chu"] = chu
    except OSError:
        pass


def bao_xong(cau_hinh: dict, so: int, ket_qua: str = "", loi: str = "",
            kenh: str = None) -> None:
    _goi(cau_hinh["tram"], "/viec-xong", {
        "kenh": kenh if kenh is not None else cau_hinh.get("kenh"), "id": so,
        "ket_qua": ket_qua, "loi": loi})


# ── Mắt cào (extension) — agent tự lo, không bắt ai cài tay ─────────────────

#: Thư mục extension nằm cạnh agent trên máy ảo.
THU_MUC_TIEN_ICH = os.path.join(GOC, "tien-ich")


def _thu_muc_tien_ich_kenh(cau_hinh: dict) -> str:
    """Thư mục mắt cào HIỆU LỰC cho kênh trong `cau_hinh`.

    Máy NHIỀU kênh: mỗi kênh một cửa sổ Chrome riêng — nếu dùng CHUNG một
    thư mục `tien-ich/` (một `cau-hinh.json` với một `ma_kenh`) thì mọi
    kênh khác sẽ bị extension báo NHẦM số liệu về đúng MỘT kênh đó. Nên
    máy nhiều kênh có `tien-ich/<kênh>/` riêng.

    01/10/2026: máy MỘT kênh cũng dùng `tien-ich/<kênh>/` — một bố cục cho mọi máy (VPS mới khởi tạo
    ngách bằng AI, `che-do.json`/`cau-hinh.json` luôn ở thư mục riêng của kênh). Ngoại lệ giữ nếp cũ:
    máy một kênh ĐÃ chạy mắt cào ở thư mục PHẲNG (có `tien-ich/manifest.json`) mà chưa có bản riêng →
    giữ phẳng: extension nạp không đóng gói đổi đường là đổi ID, mất kho video của mắt cào.
    """
    kenh = str(cau_hinh.get("kenh") or "")
    if not kenh:
        return THU_MUC_TIEN_ICH
    rieng = os.path.join(THU_MUC_TIEN_ICH, kenh)
    if len(danh_sach_kenh(cau_hinh)) > 1:
        return rieng
    if (os.path.isfile(os.path.join(THU_MUC_TIEN_ICH, "manifest.json"))
            and not os.path.isfile(os.path.join(rieng, "manifest.json"))):
        return THU_MUC_TIEN_ICH
    return rieng


def bao_dam_tien_ich(cau_hinh: dict) -> str:
    """Tải extension từ trạm về cạnh agent, tự điền địa chỉ trạm + mã kênh.

    Chủ dự án, 02/09/2026: *"đã cài tool bên vm rồi mà vẫn cần extension à…
    sao không để tool xử lý"*. Extension vẫn là con mắt duy nhất đọc được gói
    số liệu nội bộ của Studio — nhưng việc CÀI nó thì tool lo: trạm phát bản
    đang có (`GET /tien-ich`), agent bung ra đây và mở Chrome kèm cờ
    `--load-extension`. Trả về đường thư mục extension, hoặc "" nếu chưa tải
    được (trạm tắt) — lúc ấy dùng bản đã có trên đĩa nếu có.

    Máy nhiều kênh: gọi hàm này MỖI KÊNH một lần (`cau_hinh["kenh"]` khác
    nhau) — mỗi lượt tải vào đúng thư mục riêng của kênh đó, xem
    :func:`_thu_muc_tien_ich_kenh`.
    """
    thu_muc = _thu_muc_tien_ich_kenh(cau_hinh)
    try:
        url = cau_hinh["tram"].rstrip("/") + "/tien-ich"
        with urllib.request.urlopen(url, timeout=30) as tra_loi:
            goi = tra_loi.read()
        with zipfile.ZipFile(io.BytesIO(goi)) as z:
            z.extractall(thu_muc)
        # Điền cấu hình để extension tự biết trạm + kênh, khỏi ai gõ popup.
        with open(os.path.join(thu_muc, "cau-hinh.json"), "w",
                  encoding="utf-8") as tep:
            json.dump({"host": cau_hinh.get("tram", "").rstrip("/"),
                       "ma_kenh": cau_hinh.get("kenh", "")},
                      tep, ensure_ascii=False, indent=1)
        nen = doi_ten_nen_theo_ban(thu_muc)
        ghi("đã cập nhật extension từ trạm → " + thu_muc + (" (nền {0})".format(nen) if nen else ""))
        return thu_muc
    except Exception as loi:  # noqa: BLE001 — trạm tắt thì dùng bản đã có
        if os.path.isfile(os.path.join(thu_muc, "manifest.json")):
            return thu_muc
        ghi("chưa tải được extension từ trạm ({0})".format(str(loi)[:120]))
        return ""


def doi_ten_nen_theo_ban(thu_muc: str) -> str:
    """Chép `background.js` thành `nen-<sha1 8 ký tự>.js` và trỏ `manifest.json`
    (`background.service_worker`) vào đó. Trả tên tệp, "" nếu không làm được.

    ═══ VÌ SAO (đo thật 30/09/2026 22:40) ═══ Chrome kênh giữ bản service worker
    CŨ của mắt cào trong bộ nhớ đệm service worker của hồ sơ: đĩa đã là 2.9.0
    (manifest mới, `nâng cấp 2.8.0 → 2.9.0` hiện trong nhật ký) mà trong worker
    `typeof choPhepQuet === "undefined"` — mã cũ vẫn chạy, cổng quét vô hiệu.
    Đổi URL script theo nội dung buộc Chrome đăng ký worker mới mỗi khi mã đổi."""
    try:
        with open(os.path.join(thu_muc, "background.js"), "rb") as tep:
            ma = tep.read()
        import hashlib  # noqa: PLC0415
        ten = "nen-{0}.js".format(hashlib.sha1(ma).hexdigest()[:8])
        duong_mf = os.path.join(thu_muc, "manifest.json")
        with open(duong_mf, "r", encoding="utf-8") as tep:
            mf = json.load(tep)
        with open(os.path.join(thu_muc, ten), "wb") as tep:
            tep.write(ma)
        mf.setdefault("background", {})["service_worker"] = ten
        tam = duong_mf + ".tam"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(mf, tep, ensure_ascii=False, indent=2)
        os.replace(tam, duong_mf)
        for cu in os.listdir(thu_muc):
            if cu.startswith("nen-") and cu.endswith(".js") and cu != ten:
                try:
                    os.remove(os.path.join(thu_muc, cu))
                except OSError:
                    pass
        return ten
    except (OSError, ValueError):
        return ""


# ── Nạp mắt cào qua DevTools — đường sống duy nhất trên Chromium ≥137 ───────
#
# Bối cảnh đầy đủ nằm trong chú thích của :func:`_lenh_chrome`. Tóm một câu: cờ
# `--load-extension` đã CHẾT trên các bộ trình duyệt kênh (Chromium 143/151), nên
# mỗi lần agent mở trình duyệt nó phải tự nối vào DevTools của chính cửa sổ vừa mở
# và gọi `Extensions.loadUnpacked`. Đăng ký kiểu ấy không bền (mở lại là mất) —
# đó là lý do việc này nằm ở ĐƯỜNG MỞ TRÌNH DUYỆT, không phải ở bước cài một lần.

#: Cổng DevTools của kênh = hằng này + VỊ TRÍ kênh trong `cac_kenh`.
#:
#: Vì sao 9300: các cổng tool đang dùng nằm ở 8765 (trạm), 8767 (khoá một-mình
#: agent), 8768/8769 (khoá may_dang/may_cmt). 9300+ cách xa cả nhóm ấy nên không
#: bao giờ giành nhau. Vì sao theo VỊ TRÍ chứ không băm tên kênh: bốn kênh mở
#: cùng lúc phải có bốn cổng KHÁC nhau và ỔN ĐỊNH giữa các lần chạy (soi tay
#: `http://127.0.0.1:9301/json/version` là biết đang xem kênh thứ hai).
CONG_DEVTOOLS_GOC = 9300

#: Chờ tối đa bấy nhiêu giây cho `/json/version` của cửa sổ vừa mở. Đo thật:
#: launcher PortableApps bung Chromium mất ~5–12 giây trên VPS này. 40 giây là
#: mức có biên rộng; hết hạn thì ĐI TIẾP (phiên còn phải đăng, có hạn giờ thật).
CHO_DEVTOOLS_GIAY = 40


def _cong_devtools(cau_hinh: dict = None, kenh: str = "") -> int:
    """Cổng DevTools riêng của một kênh — xem :data:`CONG_DEVTOOLS_GOC`.

    Kênh không nằm trong `cac_kenh` (máy một-kênh nếp cũ, hoặc lời gọi không
    truyền cấu hình) thì dùng thẳng cổng gốc: máy ấy chỉ có một trình duyệt.
    """
    cau_hinh = cau_hinh or {}
    kenh = str(kenh or cau_hinh.get("kenh") or "")
    try:
        vi_tri = danh_sach_kenh(cau_hinh).index(kenh)
    except ValueError:
        vi_tri = 0
    return CONG_DEVTOOLS_GOC + vi_tri


def _thu_muc_ho_so_kenh(cau_hinh: dict, chrome: str = "") -> str:
    """Thư mục HỒ SƠ (user data, mức `Default`) của trình duyệt kênh, hoặc "".

    Suy từ chỗ đặt exe — nếp PortableApps của bốn bộ trình duyệt kênh là
    `<MÃ>\\<MÃ>.exe` + `<MÃ>\\Data\\profile\\Default` (đã kiểm trên đĩa
    22/09/2026). Thêm nếp `User Data\\Default` cho Chrome Portable đời cũ.
    Chỉ dùng để ĐỌC `Secure Preferences`; agent không bao giờ ghi vào đây.
    """
    chrome = chrome or tim_chrome(cau_hinh)
    if not chrome:
        return ""
    canh = os.path.dirname(chrome)
    for duong in (os.path.join(canh, "Data", "profile", "Default"),
                  os.path.join(canh, "User Data", "Default")):
        if os.path.isdir(duong):
            return duong
    return ""


def _ten_mat_cao(thu_muc: str) -> str:
    """Tên khai trong `manifest.json` của mắt cào ở `thu_muc` (hoặc "")."""
    try:
        with open(os.path.join(thu_muc, "manifest.json"), encoding="utf-8") as tep:
            return str((json.load(tep) or {}).get("name") or "")
    except (OSError, ValueError):
        return ""


def _dang_ky_ben_tien_ich(cau_hinh: dict, chrome: str = "") -> str:
    """Hồ sơ kênh có sẵn đăng ký BỀN cho mắt cào không — trả ĐƯỜNG thư mục ấy.

    ═══ VÌ SAO PHẢI HỎI CÂU NÀY TRƯỚC KHI NẠP (22/09/2026) ═══

    TL4-T7 vẫn cào được suốt trong khi ba kênh mới chạy rỗng, và KHÔNG phải nhờ cờ
    dòng lệnh: hồ sơ nó còn một đăng ký "unpacked" (`location == 4`, từ lần bấm
    *Load unpacked* TAY ngày xưa) trỏ vào thư mục PHẲNG `vm\\tien-ich` — tức nó đang
    chạy bản 2.6.2 cũ, KHÔNG phải `vm\\tien-ich\\TL4-T7` (2.7.1) mà agent tải mới mỗi
    lần khởi động. Nạp thêm bản 2.7.1 qua DevTools vào đúng cửa sổ ấy là có HAI mắt
    cào cùng cào một Studio, cùng gửi số về trạm — không ai muốn thế.

    Nên luật là: có đăng ký bền thì KHÔNG nạp qua DevTools, mà ĐỒNG BỘ mã mới vào
    đúng thư mục nó đang trỏ (xem :func:`dong_bo_tien_ich_ben`).

    Chỉ nhận mục thoả CẢ BA: `location == 4`, `path` CÒN TỒN TẠI trên đĩa và có
    `manifest.json` (hồ sơ TL4-T7 còn một mục chết trỏ `TL4-T7\\extension` — thư mục
    không có manifest, chính Chrome cũng bỏ qua), và tên trong manifest khớp tên mắt
    cào của tool (để một extension unpacked nào khác của chủ kênh không bị tính là
    "đã có mắt cào").

    Đọc không được (`Secure Preferences` khuyết/hỏng/đang bị Chrome giữ) thì trả ""
    — coi như KHÔNG có đăng ký bền và cứ nạp: thà chạy đôi một hôm còn hơn cào rỗng.
    """
    ho_so = _thu_muc_ho_so_kenh(cau_hinh, chrome)
    if not ho_so:
        return ""
    ten_can = _ten_mat_cao(_thu_muc_tien_ich_kenh(cau_hinh))
    if not ten_can:
        return ""          # chưa có mắt cào trên đĩa thì không có gì mà so
    try:
        with open(os.path.join(ho_so, "Secure Preferences"), encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError, UnicodeDecodeError):
        return ""
    muc = ((goi or {}).get("extensions") or {}).get("settings")
    if not isinstance(muc, dict):
        return ""
    for _ma, trang_thai in muc.items():
        if not isinstance(trang_thai, dict):
            continue
        try:
            if int(trang_thai.get("location") or 0) != 4:
                continue
        except (TypeError, ValueError):
            continue
        duong = str(trang_thai.get("path") or "")
        if not duong:
            continue
        if not os.path.isabs(duong):
            # Chrome ghi đường TƯƠNG ĐỐI với thư mục hồ sơ cho vài kiểu cài.
            duong = os.path.join(ho_so, duong)
        # ═══ VẾT TẠM CỦA CHÍNH MÌNH KHÔNG PHẢI ĐĂNG KÝ BỀN (22/09/2026, 11:48) ═══
        #
        # Nạp qua DevTools (`Extensions.loadUnpacked`) cũng để lại một mục
        # `location == 4` trỏ đúng thư mục per-kênh — nhưng Chrome GỠ mục ấy ngay
        # lần mở kế (đo thật: nạp 11:19, giết cứng, mở lại 11:48 → mục biến mất).
        # Nếu trình duyệt bị đóng bằng `taskkill /F` thì mục còn nằm trên đĩa
        # GIỮA hai phiên, và hàm này đã nhìn thấy nó, kết luận "TL1-T7 dùng bản
        # bền" rồi BỎ nạp DevTools → Chrome mở lên, gỡ mục, và phiên chạy KHÔNG
        # có mắt cào (kho lưu trữ của extension không được ghi một byte nào).
        # Cùng lúc hồ sơ TL2-T7 còn nguyên vết `tien-ich\TL2-T7` chờ dính y hệt.
        #
        # Đăng ký bền THẬT (TL4-T7) trỏ thư mục phẳng `vm\tien-ich` — không bao
        # giờ trùng thư mục per-kênh. Nên: đường trùng thư mục per-kênh → bỏ qua.
        if os.path.normcase(os.path.normpath(duong)) == os.path.normcase(
                os.path.normpath(_thu_muc_tien_ich_kenh(cau_hinh))):
            continue
        if _ten_mat_cao(duong) == ten_can:
            return os.path.normpath(duong)
    return ""


def dong_bo_tien_ich_ben(cau_hinh: dict, chrome: str = "") -> str:
    """Chép mã mắt cào MỚI vào thư mục mà đăng ký BỀN của hồ sơ đang trỏ.

    Gọi lúc KHỞI ĐỘNG agent (trình duyệt đang đóng), ngay sau
    :func:`bao_dam_tien_ich` — không gọi lúc mở trình duyệt: ghi đè mã của một
    extension đang chạy là kiểu làm Chrome tự tắt nó giữa phiên.

    Giữ NGUYÊN `cau-hinh.json` của thư mục đích: đó là thứ duy nhất khác nhau
    giữa các kênh (`{"host":…, "ma_kenh":…}`), và đăng ký bền có thể trỏ vào
    thư mục PHẲNG dùng chung (TL4-T7 chính là ca ấy) — chép `cau-hinh.json` của
    kênh khác vào đó là mắt cào báo số về SAI kênh.

    Trả đường thư mục đã đồng bộ, hoặc "" nếu không có đăng ký bền / không có gì
    để chép. Không có đăng ký bền là chuyện BÌNH THƯỜNG (ba kênh mới) — lúc ấy
    đường nạp là DevTools, xem :func:`mo_chrome_kenh`.
    """
    ben = _dang_ky_ben_tien_ich(cau_hinh, chrome)
    nguon = _thu_muc_tien_ich_kenh(cau_hinh)
    if not ben or os.path.normpath(ben) == os.path.normpath(nguon):
        return ""
    da_chep = 0
    for goc_con, _thu_muc_con, cac_tep in os.walk(nguon):
        rel = os.path.relpath(goc_con, nguon)
        dich_con = ben if rel == "." else os.path.join(ben, rel)
        # Đăng ký bền của TL4-T7 trỏ vào thư mục CHA của `nguon`
        # (`vm\tien-ich` ⊃ `vm\tien-ich\TL4-T7`) — đi vào thư mục con của
        # chính mình là chép lòng vòng, nên chặn ở đây.
        if os.path.normpath(dich_con) == os.path.normpath(goc_con):
            continue
        try:
            os.makedirs(dich_con, exist_ok=True)
        except OSError:
            continue
        for ten in cac_tep:
            if ten in ("cau-hinh.json", TEP_CHE_DO_MAT_CAO):
                continue        # của thư mục ĐÍCH mới đúng kênh — đừng đụng
            try:
                shutil.copyfile(os.path.join(goc_con, ten),
                                os.path.join(dich_con, ten))
                da_chep += 1
            except OSError:
                pass
    if not da_chep:
        return ""
    ghi("extension: {0} dùng bản bền ở {1}, đã đồng bộ lên {2} ({3} tệp)".format(
        cau_hinh.get("kenh") or "kênh", ben,
        _phien_ban_mat_cao(nguon) or "bản mới", da_chep))
    return ben


def _phien_ban_mat_cao(thu_muc: str) -> str:
    try:
        with open(os.path.join(thu_muc, "manifest.json"), encoding="utf-8") as tep:
            return str((json.load(tep) or {}).get("version") or "")
    except (OSError, ValueError):
        return ""


# ── CỔNG QUÉT của mắt cào (30/09/2026) ──────────────────────────────────────
#
# Chủ kênh: "vừa đăng video mới vừa quét". Mỗi lần agent mở Chrome kênh (đăng,
# tải bổ sung, ghim bình luận) mắt cào tự chạy chùm báo thức quá hạn ngay trong
# lúc máy đăng lái Studio. Nay mỗi kênh có đúng MỘT việc QUÉT NGÀY
# (:func:`chay_quet_ngay`) và mắt cào chỉ quét trong cửa sổ đó: agent ghi
# `che-do.json` vào thư mục mắt cào (đọc thẳng từ đĩa mỗi lần — tiện ích chưa
# đóng gói — nên đổi là có hiệu lực ngay). Mặc định ở chế độ phiên là CHẶN
# (ghi lúc agent khởi động và sau mỗi lượt quét); chỉ lượt quét ghi CHO PHÉP
# kèm hạn + mã lượt. Xem `core/ytb_extension/background.js: choPhepQuet`.

TEP_CHE_DO_MAT_CAO = "che-do.json"


def _cac_thu_muc_mat_cao(cau_hinh: dict) -> list:
    """Thư mục mắt cào của kênh: bản per-kênh + (nếu có) thư mục đăng ký BỀN."""
    ra = [_thu_muc_tien_ich_kenh(cau_hinh)]
    try:
        ben = _dang_ky_ben_tien_ich(cau_hinh)
    except Exception:  # noqa: BLE001 — hồ sơ lạ: chỉ ghi bản per-kênh
        ben = ""
    if ben and os.path.normcase(os.path.normpath(ben)) not in [
            os.path.normcase(os.path.normpath(x)) for x in ra]:
        ra.append(ben)
    return ra


def ghi_che_do_mat_cao(cau_hinh: dict, quet, han_giay: float = 0.0, ma: str = "") -> None:
    """`quet=True`: cho phép quét tới bây giờ + `han_giay`; `False`: CHẶN (Chrome
    mở cho việc đăng/bình luận); `None`: xoá tệp — tự do như nếp cũ (máy một
    kênh giữ Chrome 24/7). Ghi nguyên tử; hỏng ghi thì thôi (không làm vỡ việc)."""
    goi = {"che_do": "phien",
           "quet_den": int((time.time() + max(0.0, float(han_giay or 0))) * 1000) if quet else 0,
           "ma": str(ma or ""), "ghi_luc": time.strftime("%Y-%m-%d %H:%M:%S"),
           "vi_sao": "QUÉT NGÀY" if quet else "Chrome mở cho việc đăng/bình luận — không quét"}
    for thu_muc in _cac_thu_muc_mat_cao(cau_hinh):
        if not os.path.isdir(thu_muc):
            continue
        duong = os.path.join(thu_muc, TEP_CHE_DO_MAT_CAO)
        try:
            if quet is None:
                if os.path.exists(duong):
                    os.remove(duong)
                continue
            tam = duong + ".tam"
            with open(tam, "w", encoding="utf-8") as tep:
                json.dump(goi, tep, ensure_ascii=False, indent=1)
            os.replace(tam, duong)
        except OSError:
            pass


def _mat_cao_bao_xong(cau_hinh: dict, ma: str) -> bool:
    """Mắt cào đã báo xong lượt `ma` chưa: nó đổi tab làm việc sang
    `nghi.html?quet_xong=<ma>` — đọc danh sách tab ở cổng DevTools của kênh
    (không phụ thuộc trạm: cờ `/quet-xong` của trạm chỉ bị xoá khi trạm GIAO
    việc quét, nên lượt QUÉT NGÀY tự chạy sẽ thấy cờ cũ của hôm trước)."""
    if not ma:
        return False
    try:
        with urllib.request.urlopen("http://127.0.0.1:{0}/json/list".format(
                _cong_devtools(cau_hinh)), timeout=3) as tra_loi:
            ds = json.loads(tra_loi.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — cổng chưa dựng/đã đóng: coi như chưa xong
        return False
    can = "quet_xong=" + urllib.parse.quote(str(ma), safe="")
    return any(can in str((t or {}).get("url") or "") for t in (ds or []) if isinstance(t, dict))


def _cho_devtools(cong: int, cho_giay: float = CHO_DEVTOOLS_GIAY) -> str:
    """Chờ cửa sổ vừa mở dựng xong cổng DevTools — trả `webSocketDebuggerUrl`.

    Hỏi `http://127.0.0.1:<cổng>/json/version` mỗi giây tới khi có đáp hoặc hết
    hạn. Trả "" là hết hạn — người gọi PHẢI đi tiếp (đừng ném ra tới mức làm vỡ
    phiên), chỉ ghi sổ cho rõ.
    """
    han = time.monotonic() + max(1.0, float(cho_giay))
    while True:
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:{0}/json/version".format(cong),
                    timeout=2) as tra_loi:
                goi = json.loads(tra_loi.read().decode("utf-8", "replace"))
            duong = str((goi or {}).get("webSocketDebuggerUrl") or "")
            if duong:
                return duong
        except Exception:  # noqa: BLE001 — chưa dựng xong là chuyện thường
            pass
        if time.monotonic() >= han:
            return ""
        time.sleep(1)


def _nap_extension_qua_devtools(cong: int, thu_muc: str,
                                cho_giay: float = CHO_DEVTOOLS_GIAY) -> str:
    """Gọi `Extensions.loadUnpacked` vào cửa sổ đang mở ở `cong`. Trả ID extension.

    Đã chạy thật 22/09/2026: gửi
    `{"method":"Extensions.loadUnpacked","params":{"path":"…\\tien-ich\\TL1-T7"}}`
    → `{"result":{"id":"afiknmoaknibpdogpfhbbgdkhlojlhfd"}}`, extension chạy thật.

    Ném `RuntimeError` với lý do NGẮN, ĐỌC ĐƯỢC cho mọi kiểu trượt (cổng không
    đáp, thiếu gói `websocket-client`, DevTools trả lỗi) — người gọi ghi nguyên
    câu ấy vào sổ rồi đi tiếp.
    """
    duong_ws = _cho_devtools(cong, cho_giay)
    if not duong_ws:
        raise RuntimeError("cổng DevTools {0} không đáp sau {1}s".format(
            cong, int(cho_giay)))
    try:
        import websocket           # gói `websocket-client`, KHÔNG phải `websockets`
    except ImportError:
        raise RuntimeError("thiếu gói websocket-client trên máy này "
                           "(pip install websocket-client)")
    ws = websocket.create_connection(duong_ws, timeout=30)
    try:
        ws.send(json.dumps({"id": 1, "method": "Extensions.loadUnpacked",
                            "params": {"path": thu_muc}}))
        for _ in range(200):
            tra = json.loads(ws.recv())
            if not isinstance(tra, dict) or tra.get("id") != 1:
                continue          # sự kiện DevTools đi ngang — bỏ qua
            if tra.get("error"):
                raise RuntimeError("DevTools từ chối: {0}".format(
                    str((tra.get("error") or {}).get("message") or tra["error"])[:120]))
            return str((tra.get("result") or {}).get("id") or "")
        raise RuntimeError("DevTools không trả lời loadUnpacked")
    finally:
        try:
            ws.close()
        except Exception:  # noqa: BLE001 — đóng được thì tốt, không thì thôi
            pass


def tim_chrome(cau_hinh: dict) -> str:
    """Chrome của kênh — điền trong config thì lấy, không thì TỰ TÌM.

    Chủ dự án, 02/09/2026: *"cái tool upload trước nó theo logic là để thư
    mục cạnh cái Chrome đó"* — giữ đúng nếp ấy: chép thư mục `vm/` vào CẠNH
    Chrome của kênh là agent tự thấy, khỏi khai đường dẫn. Dò quanh thư mục
    cha của agent: Chrome Portable, rồi bộ trình duyệt riêng của kênh
    (`<kênh>\\<kênh>.exe` kiểu GPM).
    """
    duong = str(cau_hinh.get("chrome") or "")
    if duong and os.path.isfile(duong):
        return duong
    kenh = str(cau_hinh.get("kenh") or "")
    ung_vien = [os.path.join(GOC, "GoogleChromePortable.exe")]
    for cha in _cac_goc_trinh_duyet():
        ung_vien += [
            os.path.join(cha, "GoogleChromePortable.exe"),
            os.path.join(cha, "GoogleChromePortable", "GoogleChromePortable.exe"),
        ]
        if kenh:
            ung_vien += [
                os.path.join(cha, kenh, kenh + ".exe"),
                os.path.join(cha, kenh, kenh, kenh + ".exe"),
            ]
    for duong in ung_vien:
        if os.path.isfile(duong):
            return duong
    return ""


def _lenh_chrome(chrome: str, url: str, cau_hinh: dict = None) -> list:
    """Dòng lệnh mở Chrome — cổng DevTools + cờ mục 1 LUÔN có, thêm cờ nạp
    extension khi mắt đã nằm trên đĩa.

    Trình duyệt nào không nhận cờ (Chrome chính hãng bản mới đã bỏ nó) thì
    cờ rơi qua vô hại — lúc ấy extension cần được cài tay MỘT lần từ đúng
    thư mục `tien-ich` cạnh agent (đã có sẵn trên máy, không phải chép gì).

    `cau_hinh` (tuỳ chọn): máy nhiều kênh thì mắt của TỪNG kênh nằm ở thư
    mục riêng (`_thu_muc_tien_ich_kenh`) — không truyền thì dùng thư mục
    phẳng cũ (một-kênh), khớp mọi lời gọi đời trước. Cùng `cau_hinh` quyết
    định CỔNG DevTools qua :func:`_cong_devtools` (theo vị trí kênh).
    """
    thu_muc = (_thu_muc_tien_ich_kenh(cau_hinh) if cau_hinh is not None
               else THU_MUC_TIEN_ICH)
    lenh = [chrome]
    # ═══ CỔNG DEVTOOLS VÔ ĐIỀU KIỆN (Việc C, 29/09/2026) ═══
    #
    # Trước đây cổng + cờ DevTools chỉ được thêm khi mắt cào (`manifest.json`)
    # đã nằm trên đĩa — đúng cho việc NẠP EXTENSION, nhưng máy đăng DOM/CDP
    # (`vm/cdp.py`, `workspace/THIET-KE-MAY-DANG-DOM.md` mục 1) cần nối CDP
    # vào MỌI cửa sổ Chrome kênh agent mở ra, kể cả kênh chưa có mắt cào.
    # Thiếu cổng thì `cdp.ket_noi_kenh` gặp "Chrome không cổng" (mã thoát 3)
    # ngay từ đầu, không đăng được gì dù đường DOM đang bật.
    #
    # Cờ mục 1 khác (ẩn "Restore pages?", tắt throttle nền, bỏ chặn trình
    # duyệt lần đầu…) đi kèm luôn vì không hại gì cho nếp cũ (chỉ nạp mắt
    # cào) và cần thiết cho luồng DOM chạy êm — không có `--enable-automation`,
    # không có `--headless` (thiết kế cấm rõ, tránh lộ diện tự động hoá).
    lenh.append("--remote-debugging-port={0}".format(_cong_devtools(cau_hinh)))
    lenh.append("--remote-allow-origins=*")
    lenh.append("--hide-crash-restore-bubble")
    lenh.append("--disable-backgrounding-occluded-windows")
    lenh.append("--disable-renderer-backgrounding")
    lenh.append("--disable-background-timer-throttling")
    lenh.append("--disable-features=CalculateNativeWinOcclusion")
    lenh.append("--no-first-run")
    lenh.append("--no-default-browser-check")
    if os.path.isfile(os.path.join(thu_muc, "manifest.json")):
        # ═══ VÌ SAO CÓ BA CỜ DEVTOOLS, VÀ VÌ SAO `--load-extension` CHỈ CÒN LÀ MỒI ═══
        # (đo trên máy thật ngày 22/09/2026 — đừng chẩn lại, và đừng "tối ưu" bỏ đi)
        #
        # 1. Launcher `<MÃ>\<MÃ>.exe` CHUYỂN NGUYÊN mọi cờ tới `chrome.exe` (đọc dòng
        #    lệnh tiến trình: `--user-data-dir`, `--load-extension`, URL đều tới nơi).
        #    Nên KHÔNG phải launcher ăn mất cờ.
        # 2. Cả bốn bộ là Chromium 143/151. Từ bản 137 Google VÔ HIỆU `--load-extension`:
        #    cờ tới nơi, Chrome đọc rồi BỎ. Hệ quả đo được: ba hồ sơ mới (TL1/TL2/TL3-T7)
        #    không có một mục extension nào của tool trong `Secure Preferences`, và
        #    `CHANNEL/<MÃ>/chi-so/` của chúng không tồn tại — từ đêm 21/09 mọi phiên của
        #    ba kênh ấy chạy RỖNG: không cào Studio, không gom đối thủ, không hút lời thoại.
        # 3. Cửa sau `--disable-features=DisableLoadExtensionCommandLineSwitch` ĐÃ THỬ
        #    HAI LẦN (kể cả đóng nhẹ để Chrome kịp ghi hồ sơ): KHÔNG tác dụng trên bản
        #    này. Nên cờ ấy đã bị BỎ khỏi đây — đừng thêm lại, nó chỉ làm tưởng là xong.
        # 4. Đường sống duy nhất đã chứng minh chạy: mở cổng DevTools rồi gọi
        #    `Extensions.loadUnpacked` (xem :func:`_nap_extension_qua_devtools`) —
        #    extension chạy thật, tự tạo `Local Extension Settings/<id>`. NHƯNG đăng ký
        #    ấy KHÔNG BỀN: mở lại bình thường là mất ⇒ phải nạp lại MỖI LẦN mở, nên ba
        #    cờ này phải có mặt trên MỌI lần khởi động trình duyệt kênh.
        #
        # `--load-extension` vẫn giữ làm MỒI vô hại: bản Chrome/Chromium nào còn nhận nó
        # (máy cũ, bản Portable đời trước) thì mắt cào sống ngay từ giây đầu, khỏi chờ
        # DevTools; bản mới bỏ qua thì đã có đường số 4 gánh.
        #
        # Cổng + `--remote-allow-origins=*` đã có ở trên (vô điều kiện) — chỉ còn
        # thiếu cờ RIÊNG của việc nạp extension qua DevTools.
        # Không có cờ này thì `Extensions.loadUnpacked` bị DevTools từ chối.
        lenh.append("--enable-unsafe-extension-debugging")
        lenh.append("--load-extension=" + thu_muc)
    lenh.append(url)
    return lenh


def _chrome_dang_chay(chrome: str) -> bool:
    """Chrome của kênh có đang chạy không — hỏi `tasklist` theo tên exe.

    Hỏi theo TÊN chứ không giữ handle tiến trình: bản Portable/GPM là một
    launcher, nó đẻ Chrome thật rồi có thể tự thoát — giữ handle là tưởng
    Chrome chết trong khi nó đang sống, và agent sẽ mở CHỒNG cửa sổ mãi.

    ═══ MÁY NHIỀU KÊNH: KHÔNG HỎI TÊN CHUNG `chrome.exe` (22/09/2026) ═══

    `chrome.exe` là tên tiến trình con của CẢ BỐN bộ trình duyệt kênh. Máy chạy
    chế độ phiên (một kênh một lúc), nên khi phiên trước vừa đóng mà tiến trình
    `chrome.exe` của nó chưa chết hẳn, kênh KẾ TIẾP bị trả lời "đang chạy" →
    :func:`mo_chrome_kenh` tưởng chỉ cần chuyển URL nên BỎ bước nạp mắt cào →
    cả phiên chạy rỗng.

    Đo thật: phiên TL2-T7 mở lúc 14:51:35, ngay sau phiên TL1-T7 vừa đóng —
    không có dòng "extension: đã nạp", kết quả "lời thoại — 0 lấy được · 8 chưa
    về"; trong khi TL1 (14:45) và TL3 (14:59), mở lúc không kênh nào vừa đóng,
    đều nạp được và lấy được chữ.

    Nên khi máy khai nhiều kênh, chỉ hỏi ĐÚNG tên launcher của kênh này
    (`<MÃ>.exe`) — bốn bộ có bốn tên khác nhau. Máy một kênh (nếp cũ) giữ
    nguyên cách hỏi cả `chrome.exe`, vì ở đó không có ai để lẫn.
    """
    ten = os.path.basename(chrome)
    # Launcher riêng của kênh (`TL2-T7.exe`) thì hỏi ĐÚNG nó; chỉ máy dùng thẳng
    # `chrome.exe` mới phải hỏi tên chung.
    ung_vien = {ten} if ten.lower() != "chrome.exe" else {"chrome.exe"}
    for ung in ung_vien:
        try:
            ra = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq " + ung, "/NH"],
                # `tasklist` xuất theo BẢNG MÃ HỆ THỐNG, không phải UTF-8 —
                # xem sự cố 06/09/2026 ở `chrome_sach.ipv6_tren_may`.
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=15)
            if ung.lower() in (ra.stdout or "").lower():
                return True
        except Exception:  # noqa: BLE001 — hỏi không được thì coi như đang chạy
            return True    # thà không mở thêm còn hơn mở chồng
    return False


def mo_chrome_kenh(cau_hinh: dict, url: str, chrome: str = "",
                   da_chay: bool = None, quet=None, ma_quet: str = "",
                   han_quet: float = 0.0) -> "subprocess.Popen":
    """MỞ trình duyệt kênh — CỬA DUY NHẤT của agent, và là chỗ nạp mắt cào.

    ═══ VÌ SAO MỌI LỜI GỌI PHẢI ĐI QUA ĐÂY (22/09/2026) ═══

    Trên Chromium 143/151 của bốn bộ trình duyệt kênh, cờ `--load-extension` đã
    chết và đăng ký `Extensions.loadUnpacked` KHÔNG BỀN (mở lại là mất). Nghĩa là
    "cài extension" không còn là việc làm MỘT LẦN — nó là một bước của MỖI LẦN mở
    trình duyệt. Chừng nào còn một chỗ trong agent gọi thẳng `Popen(_lenh_chrome
    (...))`, chỗ ấy sẽ mở ra một cửa sổ MÙ và cả bước đó chạy rỗng (đúng thứ đã xảy
    ra với ba kênh mới từ đêm 21/09: không cào Studio, không gom đối thủ, không hút
    lời thoại — "8 chưa về").

    Trình tự, đúng thứ đã chạy thật:

    1. Hỏi TRƯỚC khi mở: trình duyệt đã chạy chưa (`da_chay`). Đang chạy thì lệnh
       Popen chỉ CHUYỂN URL cho cửa sổ cũ — cửa sổ ấy đã nạp mắt cào lúc nó sinh
       ra, nạp lần nữa là hai bản cùng cào.
    2. Popen với :func:`_lenh_chrome` (đã kèm ba cờ DevTools).
    3. Cửa sổ MỚI: có đăng ký bền trong hồ sơ thì thôi (xem
       :func:`_dang_ky_ben_tien_ich`); không thì chờ `/json/version` rồi
       `Extensions.loadUnpacked`.

    Trượt ở bước 3 KHÔNG được làm vỡ phiên — phiên còn phải đăng, việc có hạn giờ
    thật. Nhưng dòng sổ phải đủ để đọc buổi sáng là biết ngay phiên đêm qua có mắt
    hay không, vì đó là khác biệt giữa "cào được" và "chạy rỗng".

    Trả về đối tượng `Popen` (người gọi có thể `terminate()` như trước).

    `quet` (30/09/2026, CỔNG QUÉT): True = lượt QUÉT NGÀY — ghi `che-do.json`
    cho phép mắt cào quét tới hạn `han_quet` giây, mã lượt `ma_quet`; False =
    Chrome mở cho việc đăng/bình luận — ghi CHẶN; None = không đụng tệp (mặc
    định ở chế độ phiên đã là CHẶN, xem :func:`ghi_che_do_mat_cao`).
    """
    chrome = chrome or tim_chrome(cau_hinh)
    if quet is not None:
        ghi_che_do_mat_cao(cau_hinh, bool(quet), han_quet, ma_quet)
    if da_chay is None:
        da_chay = _chrome_dang_chay(chrome)
    con = subprocess.Popen(_lenh_chrome(chrome, url, cau_hinh))
    if da_chay:
        return con          # chỉ chuyển URL cho cửa sổ đang mở — không nạp lại
    kenh = str(cau_hinh.get("kenh") or "") or "kênh"
    thu_muc = _thu_muc_tien_ich_kenh(cau_hinh)
    if not os.path.isfile(os.path.join(thu_muc, "manifest.json")):
        ghi("extension: KHÔNG nạp được (chưa có mắt cào ở {0}) — "
            "phiên này cào rỗng".format(thu_muc))
        return con
    try:
        ben = _dang_ky_ben_tien_ich(cau_hinh, chrome)
    except Exception as loi:  # noqa: BLE001 — hồ sơ lạ cũng không được làm vỡ phiên
        ben = ""
        ghi("extension: không đọc được hồ sơ {0} ({1}) — cứ nạp qua DevTools".format(
            kenh, str(loi)[:80]))
    # Đăng ký bền có thể hiện trong Secure Preferences nhưng service worker
    # vẫn không sống (đo thật TL4 26/09: Chrome mở, không có target extension,
    # cả phiên cào rỗng). Nạp lại CHÍNH đường bền qua DevTools chỉ kích hoạt
    # lại cùng extension/id, không tạo bản thứ hai.
    thu_muc_nap = ben or thu_muc
    try:
        # Truyền hạn chờ RÕ RÀNG (không nhờ giá trị mặc định của tham số): hạn là
        # thứ cần đổi được từ một chỗ, và bài kiểm cần bẻ nó để khỏi ngồi chờ thật.
        ma = _nap_extension_qua_devtools(_cong_devtools(cau_hinh), thu_muc_nap,
                                         CHO_DEVTOOLS_GIAY)
        ghi(("extension: đã kích hoạt bản bền {0} vào {1} qua DevTools ({2})" if ben
             else "extension: đã nạp {0} vào {1} qua DevTools").format(
            ma or "(DevTools không trả id)", kenh, thu_muc_nap))
    except Exception as loi:  # noqa: BLE001 — cào rỗng còn hơn vỡ phiên
        ghi("extension: KHÔNG nạp được ({0}) — phiên này cào rỗng".format(
            str(loi)[:160]))
    return con


def van_ipv4_mo() -> bool:
    """CỜ VAN IPv4 (`vm/van-ipv4.json`) — luật sắt của chủ kênh: Chrome
    KHÔNG BAO GIỜ được sống khi IPv4 đang bật (02/09/2026: "chrome mở thì
    bắt buộc là ipv4 phải tắt rồi").

    Ai bật IPv4 (máy đăng chép file SMB, bảng cập nhật tải GitHub) phải cắm
    cờ này TRƯỚC khi bật và nhổ sau khi tắt. Agent thấy cờ là ĐỨNG IM:
    không nuôi Chrome, không quét. Cờ già quá 30 phút coi như chủ cờ chết
    giữa chừng — bỏ qua để kênh không tê liệt vĩnh viễn (và người bật sau
    cùng vẫn tự tắt IPv4 trong nhánh finally của nó).
    """
    try:
        gia = time.time() - os.path.getmtime(os.path.join(GOC, "van-ipv4.json"))
    except OSError:
        return False
    return gia <= 1800


def giu_chrome(cau_hinh: dict) -> None:
    """Nuôi Chrome: chết thì mở lại — extension nhờ vậy luôn sống.

    Chủ dự án, 02/09/2026: *"chrome phải bật thì extension mới hoạt động
    được — tức là cái tool nó phải kiểm soát all"*. Đúng: extension tự chụp
    theo mốc 24/48/72 giờ chỉ khi Chrome đang chạy, nên agent chịu trách
    nhiệm giữ nó chạy. Tắt được từ tool (núm `giu_chrome_mo`).
    """
    if not bool(cau_hinh.get("giu_chrome_mo", True)):
        return
    if van_ipv4_mo():
        return   # IPv4 đang bật (van cắm cờ) — cấm mở Chrome lúc này
    chrome = tim_chrome(cau_hinh)
    if not chrome or _chrome_dang_chay(chrome):
        return
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    # `da_chay=False`: vừa hỏi `_chrome_dang_chay` ngay trên, khỏi hỏi `tasklist`
    # lần thứ hai mỗi nhịp tim. Cửa sổ này là cửa sổ MỚI ⇒ phải nạp mắt cào.
    mo_chrome_kenh(cau_hinh, url, chrome, da_chay=False)
    ghi("Chrome đang tắt — đã mở lại ({0}{1})".format(
        os.path.basename(chrome),
        " · kênh " + cau_hinh["kenh"] if cau_hinh.get("kenh") else ""))


# ── Các việc ─────────────────────────────────────────────────────────────────


def _cho_extension_bao_xong(cau_hinh: dict, gioi_han_giay: float, ma: str = "") -> bool:
    """Chờ tối đa `gioi_han_giay` cho tiện ích báo "hết hàng" qua trạm.

    Đợt 2, kiểm toán #10 (29/09/2026): trước đây agent `time.sleep` TRỌN
    `CHO_QUET_GIAY` (480s mặc định) mỗi lượt quét dù tiện ích chụp xong sớm
    hơn nhiều — nhân hàng chục lượt/ngày là hàng giờ ngủ oan. Tiện ích mới
    (`core/ytb_extension/background.js`) tự biết lúc hết video để chụp và
    POST `/quet-xong` về trạm; ở đây hỏi lại trạm (`GET /quet-xong`) mỗi nhịp
    tim (`NHIP_GIAY`) thay vì ngủ một lần, tỉnh sớm khi có cờ.

    Cố tình dùng `time.sleep` (không phải `threading.Event.wait`): không có
    luồng nào khác đặt cờ dừng ở đây — agent là một vòng lặp MỘT luồng, đúng
    luật đầu tệp ("Chỉ GỌI VỀ trạm") — nên hai cách chờ hệt nhau về hành vi,
    nhưng `time.sleep` giữ được đúng chỗ móc mà cả bộ test đã quen dùng
    (`monkeypatch.setattr(agent.time, "sleep", ...)`, sáu chỗ trong
    `tests/`) — đổi sang một hàm chờ khác là một bẫy ngủ thật hàng phút mà
    các bài kiểm đó không hay biết để mock.

    Trả `True` nếu tỉnh sớm vì có cờ, `False` nếu ngủ hết giờ (tiện ích cũ
    không báo — đúng hệt hành vi `time.sleep` cũ, tương thích ngược).

    `ma` (30/09/2026): mã lượt QUÉT NGÀY — có mã thì tín hiệu xong là tab
    `nghi.html?quet_xong=<ma>` trên cổng DevTools của kênh (xem
    :func:`_mat_cao_bao_xong`); cờ trạm KHÔNG dùng nữa vì nó chỉ được xoá lúc
    trạm giao việc, lượt tự chạy sẽ thấy cờ cũ và tỉnh oan ngay nhịp đầu.
    """
    con_lai = max(0.0, float(gioi_han_giay))
    tram = str(cau_hinh.get("tram") or "")
    kenh = str(cau_hinh.get("kenh") or "")
    if not ma and (not tram or not kenh):
        time.sleep(con_lai)  # không biết hỏi ai — ngủ hệt bản cũ
        return False
    duong = "/quet-xong?kenh=" + urllib.parse.quote(kenh)
    while con_lai > 0:
        buoc = min(float(NHIP_GIAY), con_lai)
        time.sleep(buoc)
        con_lai -= buoc
        if ma:
            if _mat_cao_bao_xong(cau_hinh, ma):
                return True
            continue
        try:
            if _goi(tram, duong, cho=10.0).get("xong"):
                return True
        except Exception:  # noqa: BLE001 — trạm im/mạng chập: cứ chờ tiếp
            pass
    return False


def quet_studio(cau_hinh: dict, cho_giay: float = None, ma: str = "",
                han_quet: float = None) -> str:
    """Mở Chrome của kênh vào Studio để EXTENSION cào — agent chỉ mở và đợi.

    Extension mới là tay cào (nó chép được gói số liệu nội bộ của Studio —
    thứ bấm chuột không lấy nổi, xem KE-HOACH.md). Chrome mở sẵn thì thôi
    dùng luôn: mở chồng cửa sổ chỉ tổ giành phiên của nhau.

    30/09/2026: đây là VIỆC QUÉT → mở CỔNG QUÉT (mã lượt `ma`, hạn `han_quet`);
    mắt cào báo xong bằng tab `quet_xong=<ma>`, chờ tối đa `cho_giay`.
    """
    if van_ipv4_mo():
        raise RuntimeError("van IPv4 đang mở (máy đăng đang chép file) — giao lại lệnh sau ít phút")
    chrome = tim_chrome(cau_hinh)
    url = cau_hinh.get("studio_url") or "https://studio.youtube.com"
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    gioi_han = float(cho_giay or cau_hinh.get("cho_quet_giay") or CHO_QUET_GIAY)
    ma = str(ma or int(time.time()))
    # CỔNG QUÉT MỞ cho lượt này (mã `ma`) — mắt cào đọc tệp ngay lúc nạp.
    ghi_che_do_mat_cao(cau_hinh, True, float(han_quet or gioi_han + 15 * 60), ma)
    con = mo_chrome_kenh(cau_hinh, url, chrome)
    ghi("đã mở Studio, chờ extension cào (tối đa ~{0} phút, lượt {1})…".format(
        int(gioi_han // 60), ma))
    tinh_som = _cho_extension_bao_xong(cau_hinh, gioi_han, ma=ma)
    if tinh_som:
        ghi("tiện ích báo đã quét xong — khỏi chờ hết {0} phút".format(int(gioi_han // 60)))
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass
    # Nói rõ luật chụp kẻo tưởng hỏng (02/09: "có nhận lệnh nhưng không
    # thấy cào" — thật ra extension chỉ chụp phần TỚI HẠN, đúng thiết kế
    # chống chụp trùng mốc).
    if tinh_som:
        return ("tiện ích báo xong lượt {0} — đã chụp phần TỚI HẠN (cấp kênh + "
                "video vừa chạm mốc)".format(ma))
    return ("đã mở Studio cho extension cào (chờ hết {0} phút, tiện ích chưa báo "
            "xong) — nó chỉ chụp phần TỚI HẠN (cấp kênh + video vừa chạm mốc); "
            "video chưa tới mốc kế thì không chụp lại, xem Lịch trong popup tiện ích"
            .format(int(gioi_han // 60)))


def quet_trang_chu(cau_hinh: dict) -> str:
    """Mở trang chủ YouTube của phiên kênh — extension gom đối thủ và tự gửi.

    Agent lại chỉ mở và đợi: mắt đọc là `trang-chu.js` của extension (nó cuộn
    vài màn, gom link kênh, POST /doi-thu về trạm). Xem vm/KE-HOACH.md GĐ3.
    """
    if van_ipv4_mo():
        raise RuntimeError("van IPv4 đang mở (máy đăng đang chép file) — giao lại lệnh sau ít phút")
    chrome = tim_chrome(cau_hinh)
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    con = mo_chrome_kenh(cau_hinh, "https://www.youtube.com/", chrome)
    cho = float(cau_hinh.get("cho_trang_chu_giay") or 90)
    ghi("đã mở trang chủ, chờ extension gom đối thủ (~{0}s)…".format(int(cho)))
    time.sleep(cho)
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass
    return "đã mở trang chủ cho extension gom đối thủ"


#: Chờ bao nhiêu giây cho MỖI video trong danh sách lấy lời thoại.
#:
#: ═══ VÌ SAO 12 GIÂY, VÀ VÌ SAO PHẢI CÓ TRẦN ═══
#:
#: Extension (`core/ytb_extension/loi-thoai.js` + hàng đợi trong `background.js`) mở
#: từng video, bấm mở bảng phụ đề, gom chữ, gửi về trạm, rồi NGHỈ 4–8 GIÂY ngẫu nhiên
#: mới sang video kế — đi như người xem, vì đây là trình duyệt đang đăng nhập tài khoản
#: kênh. Một video vậy tốn ~5–10 giây; 12 giây là mức chờ có biên, không phải mức đo
#: được rồi cắt sát.
#:
#: Trần là phần quan trọng hơn con số: lấy lời thoại là bước PHỤ trong phiên. Phiên còn
#: phải ĐĂNG và TRẢ LỜI BÌNH LUẬN — hai việc có hạn giờ thật (video lên sóng đúng giờ).
#: Bước phụ treo là cả phiên trễ, nên hết hạn là đi tiếp, xong hay chưa cũng vậy: phần
#: hút được đã nằm ở trạm rồi (extension gửi TỪNG video một, không gom tới cuối), và
#: phần chưa hút thì phiên mai lấy tiếp.
CHO_MOI_VIDEO_LOI_THOAI_GIAY = 25


def lay_loi_thoai(cau_hinh: dict) -> dict:
    """Mở trình duyệt kênh đi HÚT LỜI THOẠI các video trạm đang cần. Bước PHỤ.

    ═══ VÌ SAO BƯỚC NÀY TỒN TẠI (22/09/2026) ═══

    Khâu đầu của sản xuất ở nhà (`kich-ban`) cần LỜI THOẠI video đối thủ. Đường cũ là
    `yt-dlp`/`youtube-transcript-api` gọi thẳng từ VPS — và đêm 22/09/2026 cả ba kênh
    chết ở đúng đó: YouTube chặn theo ĐỊA CHỈ MẠNG (`IpBlocked`, *"IP belonging to a
    cloud provider"*), và chặn nặng dần theo số lượt hỏi. Cookie, đổi `player_client`,
    nâng yt-dlp, proxy: không cứu được.

    Thứ vẫn vào YouTube bình thường từ đúng địa chỉ ấy là TRÌNH DUYỆT NÀY — phiên
    Chromium chống vân tay của kênh (đêm 21/09/2026 chạy trọn 4 phiên không lỗi). Nên
    bước này mở nó vào trang `watch` và để extension hút bảng phụ đề như một người xem
    bình thường bấm "文字起こしを表示".

    Đứng SAU quét trang chủ và TRƯỚC đăng: trang chủ là chỗ đổ ĐỐI THỦ mới về trạm, nên
    chạy sau nó thì bảng xếp hạng trạm dùng để chọn "cần lấy video nào" là bảng mới nhất
    trong ngày. Còn trước đăng vì đăng là việc có hạn giờ thật.

    Tắt được bằng khoá `lay_loi_thoai` (mặc định BẬT) — tool đẩy xuống qua
    `GET /viec` như `tu_dang`/`tu_tra_loi_cmt`, xem `KHOA_TU_TOOL` và
    `core/vm_cai_dat.py`.

    Trả `{"lay_duoc", "khong_co", "loi", "giao", "cho_giay", "ghi_chu"}` cho nhật ký
    phiên. Agent KHÔNG tự đếm được (extension gửi thẳng về trạm, không qua đây) nên nó
    chụp số liệu kho TRƯỚC và SAU rồi lấy hiệu — `GET /loi-thoai/can-lay` trả kèm ô
    `kho` đúng để làm việc đó.
    """
    ket = {"lay_duoc": 0, "khong_co": 0, "loi": 0, "giao": 0, "cho_giay": 0, "ghi_chu": ""}
    if not bool(cau_hinh.get("lay_loi_thoai", True)):
        ket["ghi_chu"] = "tắt bằng cấu hình lay_loi_thoai"
        return ket
    if van_ipv4_mo():
        ket["ghi_chu"] = "van IPv4 đang mở (máy đăng đang chép file) — bỏ bước này"
        return ket
    kenh = cau_hinh.get("kenh") or "kenh"
    truoc = _goi(cau_hinh["tram"], "/loi-thoai/can-lay?" + urllib.parse.urlencode(
        {"kenh": kenh, "k": 8}))
    ds = [v for v in (truoc.get("video") or [])
          if isinstance(v, dict) and str(v.get("video_id") or "")]
    kho_truoc = truoc.get("kho") or {}
    if truoc.get("loi"):
        ket["ghi_chu"] = "trạm nói: " + str(truoc["loi"])[:150]
        return ket
    if not ds:
        ket["ghi_chu"] = "trạm không cần lấy video nào (kho đã đủ đầu bảng)"
        return ket
    ket["giao"] = len(ds)

    chrome = tim_chrome(cau_hinh)
    if not chrome:
        raise RuntimeError(
            "không thấy Chrome của kênh — đặt thư mục vm CẠNH Chrome (đúng "
            "nếp tool đăng) hoặc điền chrome=... trong config.json")
    # Chỉ mở video ĐẦU kèm dấu `shopapi_lt=1`; extension tự hỏi trạm danh sách rồi tự
    # điều hướng chính cái tab ấy sang các video còn lại. Agent KHÔNG lái từng video:
    # nhịp nghỉ 4–8 giây phải do bên trong trang giữ (nó biết lúc nào bảng phụ đề nạp
    # xong), còn agent ở ngoài chỉ biết đồng hồ.
    url = "https://www.youtube.com/watch?v={0}&shopapi_lt=1".format(ds[0]["video_id"])
    con = mo_chrome_kenh(cau_hinh, url, chrome)
    cho = float(cau_hinh.get("cho_loi_thoai_giay") or 0) or (
        len(ds) * CHO_MOI_VIDEO_LOI_THOAI_GIAY)
    ket["cho_giay"] = int(cho)
    ghi("đã mở trang xem để hút lời thoại {0} video, chờ tối đa ~{1}s…".format(
        len(ds), int(cho)))
    time.sleep(cho)
    if bool(cau_hinh.get("dong_chrome_sau_quet", False)):
        try:
            con.terminate()
        except OSError:
            pass

    # Hiệu số kho TRƯỚC/SAU. Lượt hỏi thứ hai này cũng là lượt hỏi RẺ (trạm đọc thư
    # mục kho trên đĩa, không gọi mạng) — và nó là cách duy nhất agent biết bước vừa
    # rồi có ra chữ hay chỉ mở tab cho vui.
    try:
        sau = _goi(cau_hinh["tram"], "/loi-thoai/can-lay?" + urllib.parse.urlencode(
            {"kenh": kenh, "k": 1}))
        kho_sau = sau.get("kho") or {}
    except Exception as loi:  # noqa: BLE001 — không đếm được thì vẫn báo phần biết chắc
        ket["ghi_chu"] = "không đếm lại được kho ({0})".format(str(loi)[:80])
        return ket
    ket["lay_duoc"] = max(0, int(kho_sau.get("co") or 0) - int(kho_truoc.get("co") or 0))
    ket["khong_co"] = max(0, int(kho_sau.get("khong_co") or 0)
                          - int(kho_truoc.get("khong_co") or 0))
    ket["loi"] = max(0, len(ds) - ket["lay_duoc"] - ket["khong_co"])
    return ket


def tim_tool_dang(cau_hinh: dict = None) -> str:
    """Tool đăng nằm ở đâu — điền rõ thì theo, không thì tự tìm cạnh bên.

    Nếp thư mục của chủ dự án: vm/ nằm trong thư mục tool đăng (D:\\upload),
    cạnh `dang-tool.py` (bản đã nối nguồn tool, do `ghep_tool_dang` sinh).
    CHỈ tự nhận `dang-tool.py` — không tự chạy `dang.py` gốc: bản gốc đọc
    trang tính, tự mở nó là hai nguồn lịch giẫm nhau.
    """
    ro = str((cau_hinh or {}).get("tool_dang") or "").strip()
    if ro:
        return ro if os.path.isfile(ro) else ""
    ung = os.path.join(os.path.dirname(GOC), "dang-tool.py")
    return ung if os.path.isfile(ung) else ""


_TOOL_DANG = {"tt": None}       # tiến trình tool đăng mà agent đang nuôi


def giu_tool_dang(cau_hinh: dict) -> None:
    """Nuôi tool đăng như nuôi Chrome — chết là mở lại.

    Chủ dự án, 02/09/2026: *"tích hợp cái tool upload để tao bật tool đó là
    all mọi thứ"*. Đảo lại cho đúng một đầu mối: trên máy ảo chỉ có MỘT con
    chạy là agent; agent nuôi Chrome (để extension cào) và nuôi luôn tool
    đăng (để lịch đăng chạy) — máy bật lên là đủ cả, không phải mở gì thêm.

    Theo dõi bằng chính tay cầm tiến trình (agent là người mở duy nhất —
    khoá `mot_minh` bảo đảm), nên không đụng bài dò tên kiểu Chrome.
    """
    if (os.path.isfile(os.path.join(GOC, "giao_dien.py"))
            or os.path.isfile(os.path.join(os.path.dirname(GOC),
                                           "tool_gui.py"))):
        # Có bảng điều khiển (giao_dien.py của MyTool VM, hoặc tool_gui.py
        # của kho upload cũ nằm cạnh) thì BẢNG là người nuôi dang/cmt —
        # agent mà cũng nuôi là HAI người mở tool đăng, một video đăng hai
        # lần. Một việc một chủ.
        return
    duong = tim_tool_dang(cau_hinh)
    if not duong:
        return
    tt = _TOOL_DANG.get("tt")
    if tt is not None and tt.poll() is None:
        return
    if duong.lower().endswith(".py"):
        lenh = [sys.executable, duong]
    elif os.name == "nt" and duong.lower().endswith((".bat", ".cmd")):
        lenh = ["cmd", "/c", duong]
    else:
        lenh = [duong]
    _TOOL_DANG["tt"] = subprocess.Popen(lenh,
                                        cwd=os.path.dirname(duong) or None)
    ghi("tool đăng {0}: {1}".format(
        "mở lại (đã tắt)" if tt is not None else "mở", duong))


def dang_video(cau_hinh: dict) -> str:
    """Tải kế hoạch đăng của kênh về máy ảo; có tool đăng thì mở nó lên.

    Giai đoạn 4 mới đi nửa đường: kế hoạch VỀ được máy ảo (tệp
    `ke-hoach-<kênh>.csv` cạnh agent), còn tay đăng vẫn là con tool có sẵn
    (`D:\\upload`) — điền đường của nó vào `tool_dang` là agent mở giúp.
    Chưa điền thì nói thật kế hoạch đã về và nằm đâu.
    """
    kenh = cau_hinh.get("kenh") or "kenh"
    chu = ""
    url = cau_hinh["tram"].rstrip("/") + "/ke-hoach?" + urllib.parse.urlencode(
        {"kenh": kenh})
    with urllib.request.urlopen(url, timeout=20) as tra_loi:
        chu = tra_loi.read().decode("utf-8", "replace")
    if not chu.strip():
        return "kênh chưa có kế hoạch đăng (CHANNEL/{0}/ke-hoach-dang/)".format(kenh)
    thu_muc = cau_hinh.get("thu_muc_du_lieu") or GOC
    duong = os.path.join(thu_muc, "ke-hoach-{0}.csv".format(kenh))
    with open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        tep.write(chu)
    so_dong = max(0, len([d for d in chu.splitlines() if d.strip()]) - 1)
    tool_dang = cau_hinh.get("tool_dang") or ""
    if tool_dang and os.path.isfile(tool_dang):
        lenh = (["cmd", "/c", tool_dang] if os.name == "nt"
                and tool_dang.lower().endswith((".bat", ".cmd"))
                else [tool_dang])
        subprocess.Popen(lenh, cwd=os.path.dirname(tool_dang) or None)
        return "kế hoạch {0} dòng đã về {1}; đã mở tool đăng".format(so_dong, duong)
    return ("kế hoạch {0} dòng đã về {1}; chưa nối tool đăng — điền "
            "tool_dang vào config.json".format(so_dong, duong))


def _duong_dang_lam(duong: str = "") -> str:
    return duong or os.path.join(GOC, "dang-lam.json")


def viec_dang_lam(duong: str = "", han_giay: float = 15 * 60) -> dict:
    """Việc agent NÀY (hay bản trước) đang làm dở — {} nếu không có hoặc dấu đã quá `han_giay`.

    01:39 07/09/2026: chủ dự án mở thêm một cửa sổ agent trên máy ảo để XEM; bản mới "dọn agent
    cũ rồi thay chỗ" đúng lúc bản cũ đang quét trang chủ (việc #2) → việc chết không ai báo,
    tool bên nhà ngồi chờ. Dấu này để bản mới biết mà đứng ngoài.
    """
    try:
        with open(_duong_dang_lam(duong), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        if time.time() - float(d.get("tu") or 0) > han_giay:
            return {}
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def lam_viec(cau_hinh: dict, viec: dict) -> str:
    loai = str(viec.get("loai") or "")
    duong = _duong_dang_lam()
    try:
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"id": viec.get("id"), "loai": loai, "tu": time.time(),
                      "pid": os.getpid(),
                      "kenh": viec.get("kenh") or cau_hinh.get("kenh") or ""}, tep)
    except OSError:
        pass
    la_quet = loai in ("quet-studio", "quet-trang-chu")
    try:
        if loai == "quet-studio":
            return quet_studio(cau_hinh)
        if loai == "quet-trang-chu":
            # Lệnh TAY từ tool là việc quét — mở cổng quét cho lượt này.
            ghi_che_do_mat_cao(cau_hinh, True, float(cau_hinh.get("cho_trang_chu_giay") or 90) + 600)
            return quet_trang_chu(cau_hinh)
        if loai == "dang-video":
            return dang_video(cau_hinh)
        # Các việc chưa tới giai đoạn — NÓI THẬT thay vì im lặng nuốt lệnh.
        raise RuntimeError("bản agent này chưa làm được việc '{0}' — xem lộ trình "
                           "trong vm/KE-HOACH.md".format(loai))
    finally:
        if la_quet and che_do_phien_bat(cau_hinh, cau_hinh):
            ghi_che_do_mat_cao(cau_hinh, False)   # xong lệnh quét tay → đóng cổng lại
        try:
            os.remove(duong)
        except OSError:
            pass


# ── Lịch cố định hằng ngày (giai đoạn 2) ─────────────────────────────────────


def den_gio_quet(gio_quet: str, quet_cuoi: str, bay_gio: float = None) -> bool:
    """Hôm nay đã tới giờ quét mà chưa quét chưa? Hàm thuần để test được.

    `gio_quet` dạng "07:30"; `quet_cuoi` là ngày đã quét gần nhất ("2026-09-01").
    Mở agent SAU giờ hẹn vẫn quét bù trong ngày — máy ảo khởi động lại lúc nào
    không ai hứa trước.
    """
    if not gio_quet:
        return False
    try:
        gio, phut = (int(x) for x in str(gio_quet).split(":", 1))
    except (TypeError, ValueError):
        return False
    luc = time.localtime(bay_gio if bay_gio is not None else time.time())
    hom_nay = time.strftime("%Y-%m-%d", luc)
    if quet_cuoi == hom_nay:
        return False
    return (luc.tm_hour, luc.tm_min) >= (gio, phut)


def _duong_trang_thai(cau_hinh: dict) -> str:
    return os.path.join(cau_hinh.get("thu_muc_du_lieu") or GOC, "trang-thai.json")


def _doc_trang_thai(cau_hinh: dict) -> dict:
    try:
        with open(_duong_trang_thai(cau_hinh), "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
        return du_lieu if isinstance(du_lieu, dict) else {}
    except (OSError, ValueError):
        return {}


#: Khoá dạng `...@YYYY-MM-DD` cũ hơn ngần này (ngày) bị dọn khỏi
#: `trang-thai.json` mỗi lần lưu — không dọn thì mỗi kênh mỗi ngày đẻ thêm một
#: khoá `phien_muc_tieu@<kênh>@<ngày>` (xem :func:`_muc_tieu_phien_hom_nay`),
#: chạy 4 kênh nhiều năm không ai dọn thì file cứ lớn dần mãi. 60 ngày: dài
#: hơn mọi cửa sổ so sánh "hôm nay so với N ngày trước" mà tool đang dùng ở
#: bất kỳ đâu (xa nhất là báo cáo theo tháng), nên không khoá nào còn Ý NGHĨA
#: mà bị dọn nhầm — khoá này chỉ đọc lại ĐÚNG NGÀY hôm nó được ghi (một lần
#: tính "giờ phiên mục tiêu" mỗi ngày), quá ngày đó là bỏ luôn không đọc lại,
#: nên xoá sau 60 ngày không đổi hành vi gì, chỉ dọn rác.
TRANG_THAI_GIU_NGAY = 60

#: `@YYYY-MM-DD` ở CUỐI khoá. Khoá không mang ngày ở cuối (vd
#: `quet_cuoi@<kênh>@<khe>` — `<khe>` là giờ "HH:MM", không phải ngày) không
#: khớp mẫu này nên được GIỮ NGUYÊN — đó là khoá số lượng cố định (một
#: khoá/kênh/khe), không nở theo thời gian, không cần dọn.
_MAU_KHOA_THEO_NGAY = re.compile(r"@(\d{4}-\d{2}-\d{2})$")


def _don_trang_thai_theo_ngay(tt: dict, *, bay_gio: float = None,
                              giu_ngay: int = TRANG_THAI_GIU_NGAY) -> dict:
    """Trả về BẢN SAO của `tt` đã bỏ các khoá `...@YYYY-MM-DD` cũ hơn
    `giu_ngay` ngày. Thuần tuý (không đụng đĩa) để test bằng dict dựng tay."""
    luc = bay_gio if bay_gio is not None else time.time()
    han = time.strftime("%Y-%m-%d", time.localtime(luc - giu_ngay * 86400))
    ket_qua = {}
    for khoa, gia in tt.items():
        khop = _MAU_KHOA_THEO_NGAY.search(khoa)
        if khop and khop.group(1) < han:
            continue
        ket_qua[khoa] = gia
    return ket_qua


def _luu_trang_thai(cau_hinh: dict, **thay_doi) -> None:
    tt = _doc_trang_thai(cau_hinh)
    tt.update(thay_doi)
    tt = _don_trang_thai_theo_ngay(tt)
    try:
        with open(_duong_trang_thai(cau_hinh), "w", encoding="utf-8") as tep:
            json.dump(tt, tep, ensure_ascii=False, indent=1)
    except OSError:
        pass


def viec_theo_lich(cau_hinh: dict, la_kenh_dau: bool = True) -> None:
    """Đến giờ hẹn thì tự quét — lệnh tay luôn được xử TRƯỚC lịch.

    `gio_quet` nhận NHIỀU khe cách nhau dấu phẩy ("07:30,19:30") — chủ dự
    án hỏi 02/09 "quét mấy lần 1 ngày": hai khe là đủ (số liệu phân tích
    nằm ở các mốc 24/48/72h do extension tự chụp khi Chrome sống; khe quét
    chỉ là lưới an toàn — sáng bắt sóng sau giờ đăng, tối chốt ngày). Mỗi
    khe một mốc riêng.

    Máy NHIỀU kênh: mỗi kênh có mốc RIÊNG (`quet_cuoi@<kênh>@<khe>`) — kênh
    nào cũng dùng chung một Studio/lịch nhưng khác Chrome. Mốc cũ đời
    một-kênh (`quet_cuoi@<khe>` / `quet_cuoi`, không mang mã kênh) chỉ được
    kế thừa cho khe đầu và CHỈ khi không có kênh (máy một-kênh) hoặc đây là
    kênh CHÍNH (`la_kenh_dau`) — máy vừa nâng cấp lên nhiều kênh thì các
    kênh 2..5 không được "thừa hưởng" lịch sử của kênh đầu.
    """
    tt = _doc_trang_thai(cau_hinh)
    kenh = str(cau_hinh.get("kenh") or "")
    cac_khe = [g.strip() for g in str(cau_hinh.get("gio_quet") or "").split(",")
               if g.strip()]
    khe_toi = None
    for khe in cac_khe:
        khoa = "quet_cuoi@{0}@{1}".format(kenh, khe) if kenh else "quet_cuoi@" + khe
        da = str(tt.get(khoa) or "")
        if not da and (not kenh or la_kenh_dau):
            da = str(tt.get("quet_cuoi@" + khe)
                     or (tt.get("quet_cuoi") if khe == cac_khe[0] else "") or "")
        if den_gio_quet(khe, da):
            khe_toi = khe
            break
    if khe_toi is None:
        return
    if van_ipv4_mo():
        # KHÔNG ghi mốc — van nhổ là lượt sau tới giờ vẫn quét được.
        ghi("đến giờ quét nhưng van IPv4 đang mở (máy đăng đang chép file) "
            "— hoãn, thử lại nhịp sau")
        return
    ghi("đến giờ quét hằng ngày (khe {0}{1})".format(
        khe_toi, " · kênh " + kenh if kenh else ""))
    # Ghi mốc TRƯỚC khi quét: lượt quét kéo dài nhiều phút, hỏng giữa chừng
    # cũng không được quét dồn dập cả ngày — khe sau/mai lại tới lượt.
    hom_nay = time.strftime("%Y-%m-%d")
    khoa_moi = "quet_cuoi@{0}@{1}".format(kenh, khe_toi) if kenh else "quet_cuoi@" + khe_toi
    thay = {khoa_moi: hom_nay}
    if not kenh:
        thay["quet_cuoi"] = hom_nay
    _luu_trang_thai(cau_hinh, **thay)
    try:
        ghi(quet_studio(cau_hinh))
    except Exception as loi:  # noqa: BLE001 — lịch hỏng hôm nay, mai vẫn chạy
        ghi("quét theo lịch hỏng: {0}".format(loi))
    if bool(cau_hinh.get("quet_trang_chu_hang_ngay", False)):
        try:
            ghi(quet_trang_chu(cau_hinh))
        except Exception as loi:  # noqa: BLE001
            ghi("quét trang chủ theo lịch hỏng: {0}".format(loi))


# ── Chế độ PHIÊN (5 kênh/1 VPS — bước A, 18/09/2026) ─────────────────────────
#
# Quyết định chủ dự án 18/09: máy nhiều kênh KHÔNG giữ 5 trình duyệt sống
# 24/7 nữa — mỗi kênh một PHIÊN/ngày, ngay trước giờ đăng của nó: mở trình
# duyệt kênh đó → quét Studio + trang chủ → đăng ĐÚNG kênh đó → trả lời cmt
# ĐÚNG kênh đó → đóng trình duyệt → sang kênh kế. Không phiên nào chạy chồng
# nhau (Chrome/PyAutoGUI chỉ có một màn hình). Xem vm/KE-HOACH.md.


def che_do_phien_bat(cau_hinh: dict, cai_dat_kenh_chinh: dict = None) -> bool:
    """Chế độ phiên có đang BẬT hiệu lực trên máy này không.

    `cai_dat_kenh_chinh`: cấu hình hiệu lực của KÊNH CHÍNH (khoá `che_do_phien`
    do tool đẩy xuống qua `/viec`) — None/thiếu khoá/`None` nghĩa là TỰ ĐỘNG:
    máy phục vụ ≥2 kênh (một VPS nhiều kênh) thì BẬT; máy MỘT kênh (nếp cũ,
    mọi VM đang sống) thì TẮT — không đổi hành vi VM nào đang chạy trừ khi
    chủ dự án tự ép `true`/`false` từ tool.
    """
    gia = (cai_dat_kenh_chinh or {}).get("che_do_phien")
    if gia is None:
        return len(danh_sach_kenh(cau_hinh)) >= 2
    return bool(gia)


def _phan_tich_ngay(s: str):
    for dinh in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return time.strptime(str(s).strip(), dinh)
        except ValueError:
            continue
    return None


def _phan_tich_gio(s: str):
    for dinh in ("%H:%M:%S", "%H:%M"):
        try:
            return time.strptime(str(s).strip(), dinh)
        except ValueError:
            continue
    return None


def gio_dang_som_nhat_hom_nay(chu_csv: str, hom_nay_ymd=None) -> str:
    """Giờ đăng SỚM NHẤT của kênh, đúng HÔM NAY, trong kế hoạch (CSV thô của
    `GET /ke-hoach` — khuôn cột của `core/ke_hoach_dang.py`). Dòng phải có
    "Sẵn sàng" và CHƯA có "Trạng thái đăng" (chưa đăng). "" nếu kênh không có
    gì đăng hôm nay — bên gọi dùng mốc mặc định (`gio_phien`).
    """
    if not chu_csv or not chu_csv.strip():
        return ""
    hom_nay_ymd = tuple(hom_nay_ymd or time.localtime()[:3])
    dong = list(csv.reader(io.StringIO(chu_csv)))
    if not dong:
        return ""
    cot = [str(o) for o in dong[0]]

    def o(ten):
        return cot.index(ten) if ten in cot else None

    i_ngay, i_gio = o("Ngày đăng"), o("Giờ đăng")
    i_ss, i_tt = o("Sẵn sàng"), o("Trạng thái đăng")
    if i_ngay is None or i_gio is None:
        return ""
    som_nhat, phut_som_nhat = "", None
    for d in dong[1:]:
        if len(d) <= max(i_ngay, i_gio):
            continue
        if i_ss is not None and not (len(d) > i_ss and str(d[i_ss]).strip()):
            continue
        if i_tt is not None and len(d) > i_tt and str(d[i_tt]).strip():
            continue    # đã đăng rồi
        ngay = _phan_tich_ngay(d[i_ngay])
        if ngay is None or ngay[:3] != hom_nay_ymd:
            continue
        gio_chu = str(d[i_gio]).strip()
        tm = _phan_tich_gio(gio_chu)
        if tm is None:
            continue
        phut = tm.tm_hour * 60 + tm.tm_min
        if phut_som_nhat is None or phut < phut_som_nhat:
            som_nhat, phut_som_nhat = gio_chu, phut
    return som_nhat


def gio_phien_muc_tieu(gio_dang: str, phien_truoc_phut=None,
                       gio_phien_mac_dinh: str = None) -> str:
    """"HH:MM" mục tiêu phiên hôm nay: giờ đăng sớm nhất trừ lùi
    `phien_truoc_phut` phút; kênh không có gì đăng hôm nay (`gio_dang` rỗng)
    thì dùng mốc mặc định `gio_phien_mac_dinh` (quét + trả lời cmt vẫn chạy).
    """
    mac_dinh = str(gio_phien_mac_dinh or "07:30")
    if not gio_dang:
        return mac_dinh
    tm = _phan_tich_gio(gio_dang)
    if tm is None:
        return mac_dinh
    lui = int(phien_truoc_phut) if str(phien_truoc_phut or "").strip() else 60
    tong_phut = max(0, tm.tm_hour * 60 + tm.tm_min - lui)
    return "{0:02d}:{1:02d}".format((tong_phut // 60) % 24, tong_phut % 60)


def den_gio_phien(gio_muc_tieu: str, phien_cuoi: str, bay_gio: float = None) -> bool:
    """Đã tới giờ phiên hôm nay mà phiên CHƯA CHẠY chưa? Cùng khuôn
    `den_gio_quet`, khác chỗ đây là MỘT phiên/ngày (không nhiều khe)."""
    if not gio_muc_tieu:
        return False
    tm = _phan_tich_gio(gio_muc_tieu)
    if tm is None:
        return False
    luc = time.localtime(bay_gio if bay_gio is not None else time.time())
    hom_nay = time.strftime("%Y-%m-%d", luc)
    if phien_cuoi == hom_nay:
        return False
    return (luc.tm_hour, luc.tm_min) >= (tm.tm_hour, tm.tm_min)


def _muc_tieu_phien_hom_nay(cau_hinh: dict, cau_hinh_kenh: dict, kenh: str) -> str:
    """"HH:MM" mục tiêu phiên HÔM NAY của một kênh — tính MỘT LẦN/ngày (một
    lượt `GET /ke-hoach`) rồi CẤT vào trang-thai.json; các nhịp tim sau chỉ so
    giờ với mốc đã cất, không hỏi mạng lại (luật CLAUDE.md: hỏi dày không làm
    việc xong sớm hơn, chỉ tốn đường truyền/CPU trạm).
    """
    hom_nay = time.strftime("%Y-%m-%d")
    khoa = "phien_muc_tieu@{0}@{1}".format(kenh, hom_nay)
    da = _doc_trang_thai(cau_hinh).get(khoa)
    if isinstance(da, str) and da:
        return da
    tram = str(cau_hinh_kenh.get("tram") or "")
    if not tram:
        return ""
    try:
        url = tram.rstrip("/") + "/ke-hoach?" + urllib.parse.urlencode({"kenh": kenh})
        with urllib.request.urlopen(url, timeout=20) as tra_loi:
            chu = tra_loi.read().decode("utf-8-sig", "replace")
    except Exception:  # noqa: BLE001 — trạm tắt/mạng chập: thử lại nhịp sau, KHÔNG cất mốc rỗng
        return ""
    gio_dang = gio_dang_som_nhat_hom_nay(chu)
    muc_tieu = gio_phien_muc_tieu(gio_dang, cau_hinh_kenh.get("phien_truoc_phut"),
                                  cau_hinh_kenh.get("gio_phien"))
    _luu_trang_thai(cau_hinh, **{khoa: muc_tieu})
    ghi("kênh {0}: phiên hôm nay lúc {1}{2}".format(
        kenh, muc_tieu, " (đăng lúc {0})".format(gio_dang) if gio_dang
        else " (không có gì đăng hôm nay — mốc mặc định)"))
    return muc_tieu


def dong_chrome_kenh(cau_hinh_kenh: dict) -> None:
    """Đóng ĐÚNG trình duyệt của kênh, kể cả launcher Portable đã tách con.

    `TL1-T7.exe`... chỉ là launcher. Sau khi sinh `chrome.exe`, cây Chromium
    có thể đã tách khỏi launcher; `taskkill /IM TL1-T7.exe /T` khi đó báo xong
    nhưng 10--20 tiến trình con vẫn giữ vài GB RAM. Hàng đợi tưởng đã sang
    kênh kế tiếp và bốn cụm Chrome chồng dần lên nhau — đúng nguyên nhân VPS
    quá tải rồi tắt.

    Mỗi kênh đã có cổng DevTools riêng, nên gửi `Browser.close` vào đúng cổng
    là cách vừa chính xác vừa cho Chrome kịp ghi hồ sơ. `taskkill` launcher chỉ
    còn là LƯỚI CUỐI cho bản Chromium không mở được DevTools.

    ═══ THỨ TỰ: Browser.close → CHỜ CỔNG ĐÓNG → taskkill (Việc C, 29/09/2026) ═══

    Bản trước gửi `Browser.close` rồi `taskkill /F` NGAY LẬP TỨC, và chỉ SAU
    ĐÓ mới chờ cổng đóng — Chrome bị giết đột ngột (chưa kịp tự thoát sạch từ
    `Browser.close`) nên coi phiên là crash, lần mở kế hiện hộp "Restore
    pages?" (thiết kế mục 0, "Lỗi 2"). Đảo lại: chờ CHÍNH `Browser.close` tự
    đóng cổng trước (tối đa 10 giây, Chrome thoát sạch), `taskkill` chỉ còn
    là lưới vớt khi `Browser.close` không gửi được/không tự đóng — không bao
    giờ đua với một Chrome đang tự thoát bình thường.
    """
    if van_ipv4_mo():
        return
    chrome = tim_chrome(cau_hinh_kenh)
    if not chrome:
        return
    cong = _cong_devtools(cau_hinh_kenh)
    da_dong = False
    try:
        # Không dùng `_cho_devtools` ở đây: đóng là thao tác cuối phiên, cổng
        # không có thì phải rơi qua taskkill ngay chứ không đợi thêm 40 giây.
        with urllib.request.urlopen(
                "http://127.0.0.1:{0}/json/version".format(cong),
                timeout=2) as tra_loi:
            goi = json.loads(tra_loi.read().decode("utf-8", "replace"))
        duong_ws = str((goi or {}).get("webSocketDebuggerUrl") or "")
        if duong_ws:
            import websocket  # gói websocket-client đã dùng để nạp extension
            ws = websocket.create_connection(duong_ws, timeout=5)
            try:
                ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
            finally:
                ws.close()
            da_dong = True
    except Exception:  # noqa: BLE001 — còn lưới taskkill phía dưới
        pass
    if da_dong:
        # Chờ tối đa 10 giây để Chrome tự thoát SẠCH (ghi hồ sơ, không crash)
        # trước khi nghĩ tới taskkill. Không dựa vào launcher vì nó có thể
        # chết trước cây Chromium.
        for _ in range(20):
            try:
                urllib.request.urlopen(
                    "http://127.0.0.1:{0}/json/version".format(cong),
                    timeout=0.5).close()
            except Exception:  # cổng đã đóng = cây Chromium đang thoát
                da_dong = "xong"
                break
            time.sleep(0.5)
    if da_dong == "xong":
        # Browser.close đã tự đóng cổng sạch. 04/10/2026: launcher Portable `<K>.exe` của kênh mới hay KẸT lại
        # sau khi cây Chromium đã thoát → lần mở kế `_chrome_dang_chay` tưởng còn chạy, không mở lại → "Chrome
        # đang chạy nhưng KHÔNG có cổng DevTools" (mã 3). Đợi nó tự thoát ~6", còn thì tắt ĐÚNG launcher đó.
        _don_launcher_sot(os.path.basename(chrome))
        return
    # LƯỚI CUỐI: Browser.close không gửi được, hoặc cổng vẫn còn sau 10 giây
    # chờ (Chrome kẹt/không tự thoát) — chỉ lúc này mới taskkill.
    ten = os.path.basename(chrome)
    try:
        subprocess.run(["taskkill", "/F", "/IM", ten, "/T"],
                       capture_output=True, timeout=15)
    except Exception:  # noqa: BLE001 — không đóng được thì thôi, phiên sau vẫn thử
        pass


def _don_launcher_sot(ten_exe: str, cho_giay: float = 6.0) -> bool:
    """Launcher còn sót sau khi Chrome đã thoát sạch → tắt theo TÊN (không /T: cây Chromium đã đóng cổng).
    Không áp cho tên chung `chrome.exe`. Trả True nếu đã phải tắt."""
    if not ten_exe or ten_exe.lower() == "chrome.exe":
        return False

    def con_song() -> bool:
        try:
            ra = subprocess.run(["tasklist", "/FI", "IMAGENAME eq {0}".format(ten_exe), "/NH"],
                                capture_output=True, text=True, timeout=10,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return ten_exe.lower() in (ra.stdout or "").lower()
        except Exception:  # noqa: BLE001
            return False
    het = time.monotonic() + cho_giay
    while con_song():
        if time.monotonic() >= het:
            try:
                subprocess.run(["taskkill", "/F", "/IM", ten_exe], capture_output=True, timeout=15,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                ghi("đã tắt launcher {0} kẹt sau khi Chrome đóng".format(ten_exe))
            except Exception:  # noqa: BLE001
                pass
            return True
        time.sleep(1)
    return False


#: Mã thoát GIẢ của :func:`_chay_mot_lan` khi tiến trình không hề chạy được
#: (thiếu tệp, `Popen` hỏng) hay bị buộc dừng vì quá hạn — không bao giờ
#: trùng mã thoát THẬT của các tool con (0/1/3/4, xem đầu `may_dang_dom.py`),
#: để :func:`chon_duong_dang` không hiểu lầm "không chạy được" thành "DOM báo
#: mã 3 thật".
MA_KHONG_CHAY = -1
MA_QUA_HAN = -2


def _chay_mot_lan(duong_py: str, kenh: str, nhan: str, han_giay: float,
                  co_gi_them: "Sequence[str]" = ("--mot-lan",)) -> "Tuple[str, int]":
    """Chạy MỘT LẦN một tool con (`may_dang.py`/`may_dang_dom.py`/`may_cmt.py`)
    cho ĐÚNG một kênh (`--kenh X <co_gi_them>`), đợi xong hay hết hạn.

    Trả `(câu tóm tắt cho nhật ký phiên, mã thoát)`. Mã thoát dùng
    :data:`MA_KHONG_CHAY`/:data:`MA_QUA_HAN` cho hai đường KHÔNG chạy được
    thật sự (khác `may_dang_dom.py` không tự chạy được nốt nào) — thêm ở
    Việc C (29/09/2026) để :func:`chon_duong_dang` biết mà quyết định có lùi
    đường ảnh hay không (trước đó hàm chỉ trả câu chữ, không mã gì để so).

    Cả `may_dang.py`/`may_dang_dom.py`/`may_cmt.py` đều tự giữ khoá một-mình
    riêng: dù chế độ phiên gọi MỘT LƯỢT thế này hay nếp cũ tự chạy vòng lặp,
    không bao giờ có hai tiến trình cùng đăng/cùng trả lời một lúc.
    """
    if not duong_py or not os.path.isfile(duong_py):
        return ("{0}: không thấy {1}".format(nhan, os.path.basename(duong_py or "?")),
                MA_KHONG_CHAY)
    bat_dau = time.time()
    lenh = [sys.executable, duong_py, "--kenh", kenh] + list(co_gi_them)
    try:
        con = subprocess.Popen(lenh, cwd=os.path.dirname(duong_py) or None)
    except OSError as loi:
        return "{0}: không mở được ({1})".format(nhan, loi), MA_KHONG_CHAY
    try:
        ma = con.wait(timeout=han_giay)
    except subprocess.TimeoutExpired:
        try:
            con.kill()
        except OSError:
            pass
        return ("{0}: QUÁ HẠN {1} phút — đã buộc dừng".format(nhan, int(han_giay // 60)),
                MA_QUA_HAN)
    phut = (time.time() - bat_dau) / 60.0
    return "{0}: xong ({1:.0f} phút, mã {2})".format(nhan, phut, ma), ma


def co_desktop_dau_vao() -> bool:
    """Phiên desktop đầu vào (bàn phím/chuột) có còn sống không — RDP NGẮT
    (mất kết nối, phiên vẫn đăng nhập) thì còn; RDP ĐĂNG XUẤT thì mất.

    Đường ảnh (PyAutoGUI) cần vẽ+bấm THẬT trên desktop; đường DOM (CDP) thì
    không — nên đây là điều kiện `chon_duong_dang` hỏi TRƯỚC khi cho lùi
    sang đường ảnh (mục 7 bản thiết kế). `OpenInputDesktop` trả NULL khi
    không còn desktop đầu vào để mở.

    Trả `True` trên máy không phải Windows (không kiểm được — đừng CHẶN lùi
    chỉ vì lý do ngoài ý muốn của môi trường test/CI).
    """
    if sys.platform != "win32":
        return True
    try:
        h = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)
        if not h:
            return False
        try:
            ctypes.windll.user32.CloseDesktop(h)
        except Exception:  # noqa: BLE001 — đóng hỏng thì thôi, đã biết có desktop rồi
            pass
        return True
    except Exception:  # noqa: BLE001 — kiểm hỏng thì đừng chặn đường lùi
        return True


def chon_duong_dang(cach: str, ma_dom, co_desktop: bool) -> str:
    """Hàm THUẦN (mục 8 bản thiết kế): từ `cach_dang` của kênh + mã thoát máy
    đăng DOM vừa chạy (`None` = chưa từng chạy DOM trong bước này) + có
    desktop đầu vào không → quyết định "xong" (đã đăng xong qua DOM, không
    làm gì thêm), "anh" (lùi sang đường ảnh `may_dang.py`), hay "dung" (dừng,
    KHÔNG lùi — nháp đã chạm kênh hoặc bị chặn an toàn; lùi lúc này có nguy
    cơ đăng đôi/đăng nhầm).

    Bảng mã thoát `may_dang_dom.py` (đầu tệp đó, mục 8 bản thiết kế):
    0 xong · 1 hỏng SAU khi chạm kênh, đã có videoId (KHÔNG lùi — lượt sau
    tự tiếp nháp) · 3 đường DOM không dùng được TRƯỚC khi chạm kênh (được
    lùi) · 4 bị chặn an toàn, vd van IPv4/khoá máy (KHÔNG lùi).

    `cach` = "anh": không đi qua đường DOM — trả thẳng "anh" (nếp cũ).
    `cach` = "dom": CHỈ dùng DOM, không có lưới ảnh (chủ dự án đã ép tay) —
    hỏng thì "dung", không tự ý lùi.
    `cach` = "tu_dong": lùi CHỈ KHI mã DOM đúng 3 VÀ còn desktop cho đường
    ảnh dùng — hai điều kiện phải đúng CẢ HAI, thiếu một cũng là "dung".
    """
    if cach not in ("dom", "tu_dong"):
        return "anh"
    if ma_dom == 0:
        return "xong"
    if cach == "tu_dong" and ma_dom == 3 and co_desktop:
        return "anh"
    return "dung"


def co_token_oauth(kenh: str) -> bool:
    """Kênh đã có token OAuth cho `may_cmt.py` (YouTube Data API) chưa — cùng chỗ
    `may_cmt._kho("tokens")` tìm: `vm/tokens/<k>.json`, lùi thư mục cha."""
    for thu_muc in (os.path.join(GOC, "tokens"), os.path.join(os.path.dirname(GOC), "tokens")):
        if os.path.isfile(os.path.join(thu_muc, "{0}.json".format(kenh))):
            return True
    return False


def chon_may_cmt(binh_luan_dom, tu_dang: bool, co_token: bool) -> str:
    """Hàm THUẦN: máy bình luận cho phiên — "dom" (`may_cmt_dom.py`) hay "api"
    (`may_cmt.py`, nếp cũ). DOM khi cờ `binh_luan_dom` bật (mặc định bật; `None`
    = chưa ai đặt = bật), kênh đang `tu_dang`, và CHƯA có token OAuth — có token
    thì API chạy như cũ (một trong hai, không bao giờ cả hai cùng trả lời)."""
    bat = True if binh_luan_dom is None else bool(binh_luan_dom)
    return "dom" if (bat and tu_dang and not co_token) else "api"


def _mo_chrome_viec_dang(ch: dict) -> bool:
    """Mở Chrome kênh cho việc ĐĂNG/BÌNH LUẬN (cổng quét CHẶN) nếu chưa chạy,
    chờ cổng DevTools. Trả True nếu có Chrome để dùng."""
    chrome = tim_chrome(ch)
    if not chrome:
        return False
    ghi_che_do_mat_cao(ch, False)
    if not _chrome_dang_chay(chrome):
        mo_chrome_kenh(ch, ch.get("studio_url") or "https://studio.youtube.com", chrome,
                       da_chay=False)
        _cho_devtools(_cong_devtools(ch), CHO_DEVTOOLS_GIAY)
    return True


def chay_mot_phien(cau_hinh: dict, cau_hinh_kenh: dict, kenh: str) -> dict:
    """MỘT phiên của một kênh: (kiểm DOM) → đăng (một kênh, một lượt) → trả
    lời cmt (một kênh, một lượt) → đóng trình duyệt.

    30/09/2026 (chủ kênh: "vừa đăng video mới vừa quét"): phiên KHÔNG còn quét
    Studio/trang chủ/lời thoại — đó là việc QUÉT NGÀY riêng (:func:`chay_quet_ngay`,
    khung đêm), và Chrome mở cho phiên có cổng quét CHẶN (mắt cào đứng im). Kết
    quả phiên chép lại kết quả QUÉT NGÀY gần nhất vào `quet_studio`/`quet_trang_chu`
    để giao diện (tong_quan_vps, trang_trung_tam) vẫn đọc được như cũ.

    Từng bước tự bọc lỗi — một bước hỏng không chặn các bước sau (chủ dự án
    cần biết THẬT sự thể, không cần phiên "sạch tuyệt đối"); đăng/trả lời cmt
    tự bỏ qua bên trong nếu kênh đang TẮT núm tương ứng
    (`may_dang._tu_dang_bat` / `may_cmt._tu_tra_loi_bat`), agent không phải
    biết trước để lọc.
    """
    ket_qua = {"kenh": kenh, "bat_dau": time.strftime("%Y-%m-%d %H:%M:%S")}
    cach_dang = str(cau_hinh_kenh.get("cach_dang") or "anh")
    ghi("── PHIÊN kênh {0} bắt đầu ──".format(kenh))
    qn = _doc_trang_thai(cau_hinh).get("quet_ngay_ket@" + kenh) or {}
    if isinstance(qn, dict) and qn:
        for khoa in ("quet_studio", "quet_trang_chu", "loi_thoai", "du_lieu_da_ve"):
            if khoa in qn:
                ket_qua[khoa] = qn[khoa]
        ket_qua["quet_ngay"] = str(qn.get("ket_thuc") or qn.get("bat_dau") or "")
    if bool(cau_hinh_kenh.get("tu_dang")) or bool(cau_hinh_kenh.get("tu_tra_loi_cmt")):
        try:
            _mo_chrome_viec_dang(cau_hinh_kenh)
        except Exception as loi:  # noqa: BLE001 — máy con tự mở Chrome nếu cần
            ghi("phiên kênh {0}: mở Chrome lỗi: {1}".format(kenh, loi))
    else:
        ghi("phiên kênh {0}: tắt cả tự đăng lẫn tự trả lời bình luận — không mở Chrome".format(kenh))
    if cach_dang != "anh":
        # Mục 5 bản thiết kế: đầu MỖI PHIÊN (ngay sau quét Studio, Chrome kênh
        # đang mở sẵn) dò mức 1 (chỉ đọc, không đăng gì) xem bộ chọn DOM còn
        # khớp Studio không — có nhật ký SỚM cho chủ dự án; không thay cho
        # quyết định lùi thật (đó là việc của `chon_duong_dang` ở bước đăng
        # dưới, dựa trên mã thoát CỦA CHÍNH lượt đăng, không phải lượt kiểm
        # này). `--trong-phien` BẮT BUỘC — thiếu nó máy DOM tự giữ `.khoa-may`
        # và vấp khoá agent đang giữ cho cả phiên → mã 4 (bị chặn an toàn).
        try:
            msg_kd, _ma_kd = _chay_mot_lan(
                os.path.join(GOC, "may_dang_dom.py"), kenh, "kiểm DOM",
                han_giay=180.0, co_gi_them=("--kiem-dom", "--trong-phien"))
        except Exception as loi:  # noqa: BLE001 — bước PHỤ hỏng, phiên vẫn đi tiếp
            msg_kd = "kiểm DOM: lỗi {0}".format(loi)
        ket_qua["kiem_dom"] = msg_kd
        ghi("phiên kênh {0}: {1}".format(kenh, msg_kd))
    han_dang = float(cau_hinh.get("phien_han_dang_giay") or 90 * 60)
    # Đợt 1.5: sắp tải lên — đổi nhãn khe "nang" sang "tai_len" để sản xuất
    # song song tạm dừng tải kết quả về (`core.bang_thong`, CLAUDE.md luật 5).
    doi_viec_khoa_may("tai_len")
    if cach_dang in ("dom", "tu_dong"):
        # Đường DOM/CDP (thay đường dò ảnh) — BẮT BUỘC `--trong-phien` (cùng
        # lý do bước kiểm DOM ở trên). Quyết định có lùi đường ảnh hay không
        # là hàm THUẦN `chon_duong_dang`, dựa đúng mã thoát của LƯỢT ĐĂNG này
        # (không phải lượt kiểm DOM đầu phiên).
        msg_dang, ma_dom = _chay_mot_lan(
            os.path.join(GOC, "may_dang_dom.py"), kenh, "đăng (DOM)",
            han_giay=han_dang, co_gi_them=("--mot-lan", "--trong-phien"))
        ket_qua["dang"] = msg_dang
        buoc = chon_duong_dang(cach_dang, ma_dom, co_desktop_dau_vao())
        if buoc == "anh":
            msg_anh, _ma_anh = _chay_mot_lan(
                os.path.join(GOC, "may_dang.py"), kenh, "đăng (ảnh, lùi từ DOM)",
                han_giay=han_dang)
            ket_qua["dang"] = msg_dang + " → " + msg_anh
    else:
        msg_dang, _ma_anh = _chay_mot_lan(
            os.path.join(GOC, "may_dang.py"), kenh, "đăng", han_giay=han_dang)
        ket_qua["dang"] = msg_dang
    ghi("phiên kênh {0}: {1}".format(kenh, ket_qua["dang"]))
    # Bình luận (29/09/2026): chưa kênh nào có OAuth (vm/tokens trống) → may_cmt.py
    # API không làm được gì; máy bình luận DOM (`may_cmt_dom.py`) làm cả bình luận
    # mồi + GHIM + trả lời ngay trong Chrome kênh đang mở. Có token thì giữ API như cũ.
    may_cmt = chon_may_cmt(cau_hinh_kenh.get("binh_luan_dom", True),
                           bool(cau_hinh_kenh.get("tu_dang")), co_token_oauth(kenh))
    if may_cmt == "dom":
        doi_viec_khoa_may("binh_luan")
        msg_cmt, _ma_cmt = _chay_mot_lan(
            os.path.join(GOC, "may_cmt_dom.py"), kenh, "bình luận (DOM)",
            han_giay=float(cau_hinh.get("phien_han_cmt_giay") or 30 * 60),
            co_gi_them=("--mot-lan", "--trong-phien"))
    else:
        msg_cmt, _ma_cmt = _chay_mot_lan(
            os.path.join(GOC, "may_cmt.py"), kenh, "trả lời cmt",
            han_giay=float(cau_hinh.get("phien_han_cmt_giay") or 30 * 60))
    ket_qua["cmt"] = msg_cmt
    ghi("phiên kênh {0}: {1}".format(kenh, ket_qua["cmt"]))
    dong_chrome_kenh(cau_hinh_kenh)
    ket_qua["ket_thuc"] = time.strftime("%Y-%m-%d %H:%M:%S")
    ghi("── PHIÊN kênh {0} xong ──".format(kenh))
    return ket_qua


def _phien_loi_khong_thay_chrome(ket_qua: dict) -> bool:
    """Phiên có hụt nguồn dữ liệu chỉ vì chưa nhận ra Chrome hay không."""
    cac = [str((ket_qua or {}).get(k) or "").lower()
           for k in ("quet_studio", "quet_trang_chu")]
    return any(("không thấy chrome" in s or "khong thay chrome" in s) for s in cac)


def _du_lieu_kenh_da_ve_hom_nay(cau_hinh: dict, kenh: str, ngay: str = None):
    """True/False nếu MyTool cùng máy có đủ hai bảng kênh của hôm nay; None nếu không kiểm được.

    Agent chép độc lập sang một VPS khác vẫn hoạt động như cũ. Chỉ bản gọn có
    ``vps.json`` cạnh ``vm/`` mới dùng phép xác nhận này.

    01/10/2026: `ngay` ("YYYY-MM-DD") = ngày BẮT ĐẦU lượt quét — lượt bắt đầu trước
    nửa đêm mà xong sau 00:00 (TL3 23:48 → 00:00:52) tính cho ngày bắt đầu: bảng
    ghi trong ngày ấy HOẶC muộn hơn đều là đủ (trước đây so với ngày lúc kết thúc
    → báo "chưa đủ" oan).
    """
    goc_tool = os.path.dirname(GOC)
    if not os.path.isfile(os.path.join(goc_tool, "vps.json")):
        return None
    thu_muc_rieng = str(cau_hinh.get("thu_muc_du_lieu") or "").strip()
    if thu_muc_rieng and os.path.abspath(thu_muc_rieng) != os.path.abspath(GOC):
        return None  # bài kiểm/máy cài kiểu khác: không nhìn nhầm dữ liệu thật cạnh mã nguồn
    thu_muc = os.path.join(goc_tool, "CHANNEL", kenh, "chi-so")
    hom_nay = str(ngay or "")[:10] or time.strftime("%Y-%m-%d")
    for ten in ("bang-tom-tat.csv", "kenh-theo-ngay.csv"):
        try:
            ngay_tep = time.strftime("%Y-%m-%d", time.localtime(
                os.path.getmtime(os.path.join(thu_muc, ten))))
        except OSError:
            # 04/10/2026: kênh MỚI chưa có video nào lên YouTube thì Studio không có bảng kênh để về —
            # "chưa đủ" ở đây là oan, lượt quét lặp 3 lần/ngày giữ Chrome + khe nặng ~1,5 giờ vô ích.
            return None if not _kenh_da_co_video(kenh) else False
        if ngay_tep < hom_nay:
            return False
    return True


#: Trang chủ của kênh chỉ là nguồn đối thủ đáng tin khi lần đo nuôi trang chủ gần nhất > ngưỡng này (%).
TRANG_CHU_TIN_CAY_PCT = 90.0


def trang_chu_tin_cay(kenh: str) -> Tuple[bool, str]:
    """04/10/2026 (chủ dự án): trang chủ kênh mới / chưa nuôi xong toàn chủ đề linh tinh → cào về là rác.
    Chỉ cào khi `kenh.yaml` khai `trang_chu_tin_cay: true` (TL4-T7 — chủ xác nhận) HOẶC lần đo gần nhất
    của `vm/logs/nuoi-trang-chu/<kênh>.json` có % chủ đề > TRANG_CHU_TIN_CAY_PCT. Đọc hỏng → không cào."""
    try:
        with open(os.path.join(os.path.dirname(GOC), "CHANNEL", kenh, "kenh.yaml"), "r", encoding="utf-8") as tep:
            if re.search(r"(?m)^trang_chu_tin_cay:\s*true\s*$", tep.read()):
                return True, "chủ xác nhận trang chủ tin cậy"
    except OSError:
        pass
    try:
        with open(os.path.join(GOC, "logs", "nuoi-trang-chu", kenh + ".json"), "r", encoding="utf-8") as tep:
            lan = (json.load(tep) or {}).get("lan_do") or []
    except (OSError, ValueError):
        lan = []
    if not lan:
        return False, "trang chủ chưa đo độ đúng chủ đề (nuôi trang chủ chưa đo)"
    pct = float(lan[-1].get("pct_chu_de") or 0)
    if pct > TRANG_CHU_TIN_CAY_PCT:
        return True, "trang chủ {0:.0f}% đúng chủ đề".format(pct)
    return False, "trang chủ mới {0:.0f}% đúng chủ đề (cần > {1:.0f}%) — đang nuôi".format(pct, TRANG_CHU_TIN_CAY_PCT)


def _kenh_da_co_video(kenh: str) -> bool:
    """Sổ videoId có ít nhất một video của kênh đã tải lên (có video_id)."""
    so = _doc_so_video_id()
    return any(str(k).startswith(kenh + "/") and isinstance(v, dict) and v.get("video_id")
               for k, v in so.items())


def _lan_thu_du_lieu_qua_ngan(ket_qua: dict, cau_hinh_kenh: dict) -> bool:
    """Nhận ra lần tự chữa cũ đã chạy với cấu hình chờ 1 giây và chưa thể có dữ liệu."""
    if int(cau_hinh_kenh.get("cho_quet_giay") or 0) < 60:
        return False
    try:
        dau = time.mktime(time.strptime(str(ket_qua.get("thu_lai_du_lieu") or ""),
                                        "%Y-%m-%d %H:%M:%S"))
        cuoi = time.mktime(time.strptime(str(ket_qua.get("ket_thuc") or ""),
                                         "%Y-%m-%d %H:%M:%S"))
    except (TypeError, ValueError, OverflowError):
        return False
    return 0 <= cuoi - dau < 60


def can_thu_lai_du_lieu(cau_hinh: dict, cau_hinh_kenh: dict, kenh: str,
                        hom_nay: str = None) -> bool:
    """Cho tự chữa đúng MỘT lần khi phiên hôm nay hụt Chrome nhưng nay đã tìm thấy.

    Không mở lại khâu đăng/cmt, không lặp vô hạn: cờ theo kênh+ngày được ghi
    trước lúc thử. Nhờ vậy sửa đường dẫn/chép lại Chrome xong thì agent tự làm
    mới số liệu, còn lỗi thật vẫn chờ người xem thay vì nện VPS cả ngày.
    """
    hom_nay = hom_nay or time.strftime("%Y-%m-%d")
    trang = _doc_trang_thai(cau_hinh)
    if str(trang.get("phien_cuoi@" + kenh) or "") != hom_nay:
        return False
    ket = trang.get("phien_ket_qua@" + kenh) or {}
    qua_ngan = _lan_thu_du_lieu_qua_ngan(ket, cau_hinh_kenh)
    thieu = _du_lieu_kenh_da_ve_hom_nay(cau_hinh, kenh) is False
    khoa = ("thu_lai_du_lieu_v3" if thieu else
            "thu_lai_du_lieu_v2" if qua_ngan else "thu_lai_du_lieu")
    if trang.get("{0}@{1}@{2}".format(khoa, kenh, hom_nay)):
        return False
    return (_phien_loi_khong_thay_chrome(ket) or qua_ngan or thieu) and bool(
        tim_chrome(cau_hinh_kenh))


def chay_lai_du_lieu(cau_hinh: dict, cau_hinh_kenh: dict, kenh: str) -> dict:
    """Tự chữa nguồn số liệu, tuần tự và luôn đóng Chrome khi xong."""
    cu = _doc_trang_thai(cau_hinh).get("phien_ket_qua@" + kenh) or {}
    ket_qua = dict(cu) if isinstance(cu, dict) else {}
    ket_qua["kenh"] = kenh
    ket_qua["thu_lai_du_lieu"] = time.strftime("%Y-%m-%d %H:%M:%S")
    cau_hinh_phien = dict(cau_hinh_kenh)
    cau_hinh_phien["dong_chrome_sau_quet"] = False
    ghi("── TỰ CHỮA dữ liệu kênh {0} bắt đầu ──".format(kenh))
    try:
        try:
            ket_qua["quet_studio"] = quet_studio(cau_hinh_phien)
        except Exception as loi:  # noqa: BLE001 — ghi kết quả thật, không chặn bước sau
            ket_qua["quet_studio"] = "lỗi: {0}".format(loi)
        try:
            ket_qua["quet_trang_chu"] = quet_trang_chu(cau_hinh_phien)
        except Exception as loi:  # noqa: BLE001
            ket_qua["quet_trang_chu"] = "lỗi: {0}".format(loi)
    finally:
        dong_chrome_kenh(cau_hinh_kenh)
    ket_qua["ket_thuc"] = time.strftime("%Y-%m-%d %H:%M:%S")
    ket_qua["du_lieu_da_ve"] = _du_lieu_kenh_da_ve_hom_nay(cau_hinh, kenh)
    if ket_qua["du_lieu_da_ve"] is False:
        ghi("kênh {0}: Chrome đã chạy nhưng hai bảng số liệu chưa về đủ — đánh dấu lỗi để theo dõi".format(kenh))
    ghi("── TỰ CHỮA dữ liệu kênh {0} xong, đã đóng Chrome ──".format(kenh))
    return ket_qua


def _phien_cuoi_kenh(cau_hinh: dict, kenh: str) -> str:
    return str(_doc_trang_thai(cau_hinh).get("phien_cuoi@" + kenh) or "")


def chay_hang_doi_phien(cau_hinh: dict, hieu_luc: dict, cac_kenh: list) -> bool:
    """MỘT bước của hàng đợi phiên — gọi mỗi nhịp tim (30s) từ `chay()`.

    Xét MỌI kênh đã tới giờ phiên hôm nay mà chưa chạy, chọn kênh có mục tiêu
    SỚM NHẤT (hai kênh cùng phút → kênh đứng trước theo tên, ổn định), CHẠY
    ĐÚNG MỘT phiên rồi trả về ngay — không bao giờ chạy song song (Chrome/
    PyAutoGUI chỉ có một màn hình). Phiên trễ hay kéo dài tự đẩy lùi phiên kế
    vì nhịp tim sau mới xét lại danh sách. Việc TAY từ tool (`GET /viec`) đi
    qua đường khác (vòng ngoài `chay()`, chạy TRƯỚC bước này trong cùng nhịp
    tim) — cùng một luồng một tiến trình nên không bao giờ chồng lên phiên.

    Trả True nếu vừa chạy một phiên (gọi nơi cần biết có việc vừa xảy ra).
    """
    # 30/09/2026: bỏ bước "tự chữa dữ liệu" (quét lại Studio khi phiên hụt số
    # liệu) — phiên không còn quét; việc QUÉT NGÀY (:func:`chay_quet_ngay`) tự
    # thử lại trong ngày khi số liệu chưa về. `can_thu_lai_du_lieu`/
    # `chay_lai_du_lieu` giữ lại cho lệnh tay/tương thích, hàng đợi không gọi.
    ung_vien = []
    for kenh in cac_kenh:
        ch = hieu_luc.get(kenh) or {}
        muc_tieu = _muc_tieu_phien_hom_nay(cau_hinh, ch, kenh)
        if not muc_tieu:
            continue
        if den_gio_phien(muc_tieu, _phien_cuoi_kenh(cau_hinh, kenh)):
            ung_vien.append((muc_tieu, kenh))
    if not ung_vien:
        return False
    ung_vien.sort()

    # ═══ XOAY VÒNG ỨNG VIÊN (chẩn đoán 28/09/2026, "việc C") ═══
    #
    # Bản trước chỉ thử ĐÚNG kênh đứng đầu (`ung_vien[0]`) — hụt cửa (van
    # IPv4 đang mở, hay chưa giành được khoá máy dùng chung) là bỏ NGUYÊN
    # nhịp tim này, kể cả khi có kênh KHÁC trong `ung_vien` cũng đã đến hạn.
    # Hai cửa chặn hiện tại (`van_ipv4_mo`, `giu_khoa_may_chung`) là trạng
    # thái CHUNG CỦA CẢ MÁY — kênh nào thử cũng vấp đúng cửa đó, nên xoay
    # vòng không "phá" được một cửa đang khoá thật; giá trị của nó là (a) một
    # cửa CHẶN-THEO-KÊNH thêm sau này (vd Chrome kênh đó không mở được) không
    # còn làm đói mọi kênh khác nữa, và (b) dòng log giờ liệt kê ĐỦ mọi kênh
    # đang chờ (không chỉ kênh đứng đầu) — chẩn đoán sự cố sau này khỏi phải
    # suy luận từ log rời rạc như đợt 26→28/09.
    if van_ipv4_mo():
        ghi("đến giờ phiên kênh {0} nhưng van IPv4 đang mở — hoãn, thử nhịp sau"
           .format(", ".join(kenh for _muc, kenh in ung_vien)))
        return False
    for _muc_tieu, kenh in ung_vien:
        if not giu_khoa_may_chung(viec="quet", kenh=kenh, uu_tien=1):
            continue  # cửa CHUNG cả máy — ứng viên kế cũng sẽ vấp y hệt, thử tiếp
                      # cho tới hết danh sách (đề phòng cửa chặn-theo-kênh sau này)
        # Ghi mốc TRƯỚC khi chạy: phiên kéo dài hàng chục phút, hỏng/tắt tool
        # giữa chừng không được chạy dồn dập lại — mai mới tới lượt (cùng
        # triết lý `viec_theo_lich`).
        try:
            _luu_trang_thai(cau_hinh, **{"phien_cuoi@" + kenh: time.strftime("%Y-%m-%d")})
            ket_qua = chay_mot_phien(cau_hinh, hieu_luc[kenh], kenh)
            _luu_trang_thai(cau_hinh, **{"phien_ket_qua@" + kenh: ket_qua})
        finally:
            nha_khoa_may_chung()
        return True
    ghi("kênh {0}: đang chờ việc nặng hiện tại xong rồi mới chạy phiên"
       .format(", ".join(kenh for _muc, kenh in ung_vien)))
    return False


# ── QUÉT NGÀY: mỗi kênh MỘT việc quét độc lập mỗi ngày (30/09/2026) ─────────
#
# Chủ kênh: "vừa đăng video mới vừa quét". Trước đây MỌI lần Chrome kênh mở
# (phiên trước giờ đăng, tải bổ sung ~25', ghim sớm ~20') mắt cào đều tự chạy
# chùm báo thức quá hạn, và phiên còn tự quét Studio + trang chủ + lời thoại
# trước khi đăng. Nay: mỗi kênh đúng một việc QUÉT NGÀY = Studio (mắt cào) +
# trang chủ + lời thoại, trong khe Chrome dùng chung (khoá máy "nang", viec
# "quet" — không bao giờ trùng việc đăng), ở khung vắng ban đêm:
# `quet_ngay_gio` (mặc định 02:10 giờ VPS — tránh :55–:05 khi `tu_chay` giành
# khoá) + vị trí kênh × `quet_ngay_cach_phut` (30) → 02:10, 02:40, 03:10,
# 03:40 cho 4 kênh; đo 26–30/09: 02:00–04:00 không có phiên/tải bổ sung nào.
# Hai khoá đặt trong vm/config.json (chung) — không có thì dùng mặc định.
# Hỏng (không mở được Chrome, số liệu chưa về) thì thử lại sau
# `QUET_NGAY_THU_LAI_PHUT`, tối đa `QUET_NGAY_TOI_DA_LAN` lượt/ngày. Mọi lần mở
# Chrome khác: cổng quét CHẶN (xem :func:`ghi_che_do_mat_cao`).
#
# ĐỘ TRỄ SỐ LIỆU (ghi rõ theo yêu cầu): một bản chụp/ngày/kênh lúc ~02–04h.
# Mốc 24h/48h/72h của vòng học, hồ sơ video, bìa dùng bản chụp GẦN NHẤT theo
# tuổi THẬT (`core/chi_so_ytb/gom.tuoi_that_gio`) — lệch tối đa ±12 giờ so với
# mốc danh nghĩa; `cong_thuc_v7` nhận cửa sổ 13h (10–16) / 48h (44–54) hoặc nội
# suy giữa hai bản chụp ≤30 giờ. Số view 48h cho thẻ video lấy từ bản QUÉT NGÀY
# gần nhất (≤30 giờ tuổi), quá hạn mới đọc nhanh (may_dang_dom.link_the).

QUET_NGAY_GIO_MAC_DINH = "02:10"
QUET_NGAY_CACH_PHUT = 30
QUET_NGAY_TOI_DA_LAN = 3
QUET_NGAY_THU_LAI_PHUT = 45
#: Chờ mắt cào báo xong tối đa (giây). Chrome giờ chỉ mở MỘT lần/ngày để quét,
#: nên một lượt phải gánh: chụp kênh (3 trang) + mọi video tới mốc (≤5 ngày:
#: chụp đầy ~1 phút; ngày 6–30: chụp nhẹ ~10 giây). Mắt cào báo xong sớm thì đi tiếp.
CHO_QUET_NGAY_GIAY = 25 * 60


def gio_quet_ngay_kenh(ch: dict, vi_tri: int) -> str:
    """"HH:MM" QUÉT NGÀY của kênh thứ `vi_tri` (0 = đầu) — hàm thuần."""
    goc = _phan_tich_gio(str(ch.get("quet_ngay_gio") or QUET_NGAY_GIO_MAC_DINH)) or \
        _phan_tich_gio(QUET_NGAY_GIO_MAC_DINH)
    try:
        cach = int(ch.get("quet_ngay_cach_phut") if ch.get("quet_ngay_cach_phut") is not None
                   else QUET_NGAY_CACH_PHUT)
    except (TypeError, ValueError):
        cach = QUET_NGAY_CACH_PHUT
    phut = (goc.tm_hour * 60 + goc.tm_min + max(0, int(vi_tri)) * max(0, cach)) % (24 * 60)
    return "{0:02d}:{1:02d}".format(phut // 60, phut % 60)


def quet_ngay_den_han(muc: dict, gio: str, bay_gio: float = None,
                      toi_da_lan: int = QUET_NGAY_TOI_DA_LAN,
                      thu_lai_phut: float = QUET_NGAY_THU_LAI_PHUT) -> bool:
    """Hàm THUẦN: kênh có tới lượt QUÉT NGÀY không. `muc` = trạng thái hôm nay
    `{"lan", "luc", "xong"}` (khoá `quet_ngay@<kênh>@<ngày>`)."""
    muc = muc if isinstance(muc, dict) else {}
    if muc.get("xong") or int(muc.get("lan") or 0) >= int(toi_da_lan):
        return False
    tm = _phan_tich_gio(gio)
    if tm is None:
        return False
    luc = time.time() if bay_gio is None else bay_gio
    lt = time.localtime(luc)
    if (lt.tm_hour, lt.tm_min) < (tm.tm_hour, tm.tm_min):
        return False
    cuoi = float(muc.get("luc") or 0)
    return not cuoi or luc - cuoi >= float(thu_lai_phut) * 60


def chay_quet_ngay_mot_kenh(cau_hinh: dict, ch: dict, kenh: str) -> dict:
    """MỘT lượt QUÉT NGÀY cho một kênh: mở Chrome (cổng quét MỞ) → mắt cào
    quét Studio tới khi báo xong / hết `cho_quet_ngay_giay` → trang chủ → lời
    thoại → đóng cổng + đóng Chrome. Trả kết quả; `xong` = số liệu đã về
    (hoặc không kiểm được) — `False` thì lịch tự thử lại."""
    ket = {"kenh": kenh, "bat_dau": time.strftime("%Y-%m-%d %H:%M:%S")}
    ch_phien = dict(ch)
    ch_phien["dong_chrome_sau_quet"] = False
    ma = str(int(time.time()))
    cho = float(ch.get("cho_quet_ngay_giay") or CHO_QUET_NGAY_GIAY)
    tong = (cho + float(ch.get("cho_trang_chu_giay") or 90)
            + 8 * CHO_MOI_VIDEO_LOI_THOAI_GIAY + 10 * 60)
    ghi("── QUÉT NGÀY kênh {0} bắt đầu (lượt {1}) ──".format(kenh, ma))
    try:
        chrome = tim_chrome(ch)
        if chrome and _chrome_dang_chay(chrome):
            # Chrome sót từ việc trước (cổng quét đang CHẶN, mắt cào có khi chưa
            # nạp): đóng êm rồi mở lại cho lượt quét. Khoá máy đang ở tay mình —
            # không có lượt tải lên nào đang chạy.
            dong_chrome_kenh(ch)
        try:
            ket["quet_studio"] = quet_studio(ch_phien, cho_giay=cho, ma=ma, han_quet=tong)
        except Exception as loi:  # noqa: BLE001 — bước hỏng, lượt vẫn đi tiếp
            ket["quet_studio"] = "lỗi: {0}".format(loi)
            ghi("QUÉT NGÀY kênh {0}: Studio lỗi: {1}".format(kenh, loi))
        tin_tc, ly_tc = trang_chu_tin_cay(kenh)
        if bool(ch.get("quet_trang_chu_hang_ngay", True)) and not tin_tc:
            ket["quet_trang_chu"] = "bỏ: " + ly_tc
            ghi("QUÉT NGÀY kênh {0}: KHÔNG cào trang chủ — {1}".format(kenh, ly_tc))
        elif bool(ch.get("quet_trang_chu_hang_ngay", True)):
            try:
                ket["quet_trang_chu"] = quet_trang_chu(ch_phien)
            except Exception as loi:  # noqa: BLE001
                ket["quet_trang_chu"] = "lỗi: {0}".format(loi)
                ghi("QUÉT NGÀY kênh {0}: trang chủ lỗi: {1}".format(kenh, loi))
        try:
            ket["loi_thoai"] = lay_loi_thoai(ch_phien)
        except Exception as loi:  # noqa: BLE001 — bước PHỤ
            ket["loi_thoai"] = {"lay_duoc": 0, "khong_co": 0, "loi": 0,
                                "ghi_chu": "lỗi: {0}".format(str(loi)[:200])}
        lt = ket["loi_thoai"]
        ghi("QUÉT NGÀY kênh {0}: lời thoại — {1} lấy được · {2} không có bảng phụ đề · "
            "{3} chưa về{4}".format(kenh, lt.get("lay_duoc", 0), lt.get("khong_co", 0),
                                    lt.get("loi", 0),
                                    " (" + lt["ghi_chu"] + ")" if lt.get("ghi_chu") else ""))
    finally:
        ghi_che_do_mat_cao(ch, False)
        dong_chrome_kenh(ch)
    ket["ket_thuc"] = time.strftime("%Y-%m-%d %H:%M:%S")
    # Lượt vắt qua nửa đêm tính cho NGÀY BẮT ĐẦU (01/10/2026).
    ket["du_lieu_da_ve"] = _du_lieu_kenh_da_ve_hom_nay(cau_hinh, kenh, ngay=ket["bat_dau"][:10])
    loi_studio = str(ket.get("quet_studio") or "").startswith("lỗi")
    ket["xong"] = (not loi_studio) and ket["du_lieu_da_ve"] is not False
    ghi("── QUÉT NGÀY kênh {0} {1} ──".format(
        kenh, "xong" if ket["xong"] else "CHƯA ĐỦ ({0}) — sẽ thử lại trong ngày".format(
            "Studio lỗi" if loi_studio else "số liệu hôm nay chưa về")))
    return ket


def chay_quet_ngay(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, bay_gio: float = None,
                   chay_mot=None) -> bool:
    """MỘT bước QUÉT NGÀY (gọi mỗi nhịp tim sau hàng đợi phiên). Chạy đúng một
    kênh đã tới giờ (sớm nhất trước) rồi trả True. `chay_mot` là seam test."""
    luc = time.time() if bay_gio is None else bay_gio
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    tt = _doc_trang_thai(cau_hinh)
    ung_vien = []
    for vi_tri, kenh in enumerate(cac_kenh):
        ch = hieu_luc.get(kenh) or {}
        gio = gio_quet_ngay_kenh(ch, vi_tri)
        khoa = "quet_ngay@{0}@{1}".format(kenh, hom_nay)
        muc = tt.get(khoa) if isinstance(tt.get(khoa), dict) else {}
        if quet_ngay_den_han(muc, gio, luc):
            ung_vien.append((gio, vi_tri, kenh, ch, khoa, muc))
    if not ung_vien:
        return False
    ung_vien.sort(key=lambda x: x[:2])
    gio, _vt, kenh, ch, khoa, muc = ung_vien[0]
    if van_ipv4_mo():
        ghi("QUÉT NGÀY kênh {0} hoãn: van IPv4 đang mở".format(kenh))
        return False
    if os.path.exists(os.path.join(GOC, "logs", "dang-dodang.json")):
        ghi("QUÉT NGÀY kênh {0} hoãn: đang có máy đăng dở (dang-dodang.json)".format(kenh))
        return False
    if not tim_chrome(ch):
        _luu_trang_thai(cau_hinh, **{khoa: dict(muc, lan=int(muc.get("lan") or 0) + 1, luc=luc,
                                              xong=False, ket="không thấy Chrome của kênh")})
        ghi("QUÉT NGÀY kênh {0}: không thấy Chrome của kênh".format(kenh))
        return False
    if not giu_khoa_may_chung(viec="quet", kenh=kenh, uu_tien=1):
        return False    # khe Chrome đang bận (sản xuất/phiên) — nhịp sau thử lại, KHÔNG tính lượt
    try:
        # Ghi lượt TRƯỚC khi chạy: tắt giữa chừng không được quét dồn dập.
        _luu_trang_thai(cau_hinh, **{khoa: dict(muc, lan=int(muc.get("lan") or 0) + 1,
                                              luc=luc, xong=False, gio=gio)})
        ket = (chay_mot or chay_quet_ngay_mot_kenh)(cau_hinh, ch, kenh)
        tt2 = _doc_trang_thai(cau_hinh)
        muc2 = tt2.get(khoa) if isinstance(tt2.get(khoa), dict) else {}
        muc2 = dict(muc2, xong=bool(ket.get("xong")), ket=str(ket.get("quet_studio") or "")[:200])
        # Giao diện đọc `phien_ket_qua@<kênh>` (quet_studio/quet_trang_chu) — chép
        # kết quả QUÉT NGÀY vào đó, giữ nguyên các trường của phiên.
        cu = tt2.get("phien_ket_qua@" + kenh)
        pk = dict(cu) if isinstance(cu, dict) else {"kenh": kenh}
        for k in ("quet_studio", "quet_trang_chu", "loi_thoai", "du_lieu_da_ve"):
            if k in ket:
                pk[k] = ket[k]
        pk["quet_ngay"] = ket.get("ket_thuc") or ""
        _luu_trang_thai(cau_hinh, **{khoa: muc2, "quet_ngay_ket@" + kenh: ket,
                                     "phien_ket_qua@" + kenh: pk})
    finally:
        nha_khoa_may_chung()
    return True


# ── Tải lên BỔ SUNG trong ngày (29/09/2026, chủ dự án duyệt tự động hoàn toàn) ──
#
# Phiên kênh chạy MỘT lần/ngày (~07:30 khi không có gì đăng hôm nay, hoặc 60
# phút trước giờ đăng). Gói nào sản xuất xong SAU phiên (TL2 mở lượt 20:00,
# bàn giao ~23:00, hẹn 20:00 hôm sau) chỉ được tải lên ở phiên HÔM SAU — sát
# giờ đăng, rủi ro lỡ lịch. Bước này: mỗi ~25 phút, khi máy rảnh (không phiên,
# khoá máy trống, không ai đang đăng), kênh nào bật `tu_dang` + `cach_dang`
# ≠ "anh" mà kế hoạch có gói "Sẵn sàng" hẹn trong (bây giờ + 2 giờ, bây giờ + 7
# ngày] chưa có videoId trong sổ → mở Chrome kênh (đúng `mo_chrome_kenh`), chạy
# máy đăng DOM ở chế độ cửa sổ, đóng Chrome êm.

#: Chu kỳ xét tải bổ sung (giây).
CHU_KY_TAI_BO_SUNG_GIAY = 25 * 60
#: Gói hẹn SỚM hơn bây giờ + chừng này giờ thì để phiên kênh lo (phiên chạy trước
#: giờ đăng 60 phút) — không chen tải bổ sung sát giờ.
BIEN_TAI_BO_SUNG_GIO = 2.0
#: Nhìn xa tối đa (ngày). Chủ kênh 01/10: video làm xong là tải + hẹn lịch luôn, không để nằm
#: chờ trên máy (nhịp thưa 1 video/2 ngày làm lịch xa hơn 7 ngày) → 30 ngày.
CUA_SO_TAI_BO_SUNG_NGAY = 30
#: Trần số LƯỢT tải bổ sung mỗi kênh mỗi ngày.
#: 30/09/2026: 3 → 8. Nhịp mới 6 khe/ngày (TL1–TL3) + lượt hỏng phải tải lại —
#: trần 3 làm TL1 hết lượt từ 12:14 (0009 hỏng, 0012 chờ) trong khi còn 2 khe
#: hôm sau chưa có video. Chặn vòng vô hạn vẫn còn: trần lượt/gói bên dưới +
#: trần 2 lần tải mới/gói/ngày của máy DOM (`lan_tai_moi`).
TAI_BO_SUNG_TOI_DA_LUOT_NGAY = 8
#: Trần số lượt tải bổ sung chứa CÙNG một gói mỗi ngày (gói kẹt kiểu "báo chủ
#: kênh" không được kéo Chrome mở lại mỗi 25 phút).
TAI_BO_SUNG_TOI_DA_LUOT_GOI_NGAY = 2
#: Khớp `may_dang_dom.TRAN_TAI_MOI_NGAY` — số lần TẢI MỚI một gói mỗi ngày.
TAI_MOI_TOI_DA_GOI_NGAY = 2
#: Khớp `may_dang_dom.TAI_LEN_TOI_DA_NGAY` — số gói TẢI MỚI mỗi kênh mỗi ngày.
TAI_LEN_TOI_DA_KENH_NGAY = 6
#: Trạng thái sổ videoId của một lượt DỞ/HỎNG (máy DOM sẽ để kệ nháp, tải mới).
#: 30/09/2026: + "tai-hong" — hậu kiểm tải lên hỏng (may_dang_dom.hau_kiem_tai_len).
TT_SO_CHUA_XONG = ("nhap", "dang-tai", "loi-tai", "tai-hong")
_TAI_BO_SUNG = {"luc": 0.0, "cuoi": {}}


def _doc_so_video_id() -> dict:
    try:
        with open(os.path.join(GOC, "logs", "so-video-id.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def ma_can_tai_bo_sung(chu_csv: str, kenh: str, so: dict, bay_gio: float = None,
                       bien_gio: float = BIEN_TAI_BO_SUNG_GIO,
                       cua_so_ngay: float = CUA_SO_TAI_BO_SUNG_NGAY) -> list:
    """Hàm THUẦN: mã gói của `kenh` cần tải bổ sung — "Sẵn sàng" có chữ,
    chưa đăng (Trạng thái đăng trống hoặc "ĐANG ĐĂNG · nháp …" của lượt hỏng),
    Ngày/Giờ đăng trong (bây giờ + biên, bây giờ + cửa sổ], và trong sổ
    `so-video-id.json` CHƯA có videoId — hoặc có id nhưng lượt đó DỞ/HỎNG
    (`TT_SO_CHUA_XONG`: luật chủ kênh 30/09 — kệ nháp, lượt sau tải mới) và gói
    chưa tải mới đủ `TAI_MOI_TOI_DA_GOI_NGAY` lần hôm nay.

    30/09/2026 (TL1-T7-0009 kẹt từ 12:14): bản trước bỏ MỌI gói có videoId
    trong sổ và mọi dòng có Trạng thái đăng — gói hỏng để lại nháp không bao giờ
    được tải bổ sung lại. Gói chưa có id chịu thêm trần kênh
    `TAI_LEN_TOI_DA_KENH_NGAY` (khớp `may_dang_dom.gioi_han_tai_moi`) để không mở
    Chrome cho một lượt mà máy DOM sẽ bỏ gói ngay."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(bay_gio))
    so = so or {}
    da_tai_moi = sum(1 for k, m in so.items()
                     if str(k).startswith(kenh + "/") and isinstance(m, dict)
                     and m.get("ngay_tai") == hom_nay)
    con_cho = max(0, TAI_LEN_TOI_DA_KENH_NGAY - da_tai_moi)
    try:
        dong = list(csv.reader(io.StringIO(chu_csv or "")))
    except csv.Error:
        return []
    if not dong:
        return []
    cot = [str(o).strip() for o in dong[0]]

    def o(d, ten):
        i = cot.index(ten) if ten in cot else -1
        return str(d[i]).strip() if 0 <= i < len(d) else ""
    tu = bay_gio + bien_gio * 3600
    den = bay_gio + cua_so_ngay * 86400
    ra = []
    for d in dong[1:]:
        ma = o(d, "Mã gói")
        tt = o(d, "Trạng thái đăng")
        if not ma or not o(d, "Sẵn sàng") or (tt and not tt.upper().startswith("ĐANG ĐĂNG")):
            continue
        muc = so.get("{0}/{1}".format(kenh, ma)) or {}
        if not isinstance(muc, dict):
            muc = {}
        lan = int(muc.get("lan_tai_moi") or 0) if muc.get("ngay_tai") == hom_nay else 0
        co_id = bool(muc.get("video_id"))
        if co_id and muc.get("trang_thai") not in TT_SO_CHUA_XONG:
            continue    # đã hẹn lịch / xác nhận — phiên kênh lo phần kiểm
        if (co_id or muc.get("trang_thai") in TT_SO_CHUA_XONG) and lan >= TAI_MOI_TOI_DA_GOI_NGAY:
            continue    # đã tải mới đủ trần hôm nay — mai tính lại
        ngay, gio = _phan_tich_ngay(o(d, "Ngày đăng")), _phan_tich_gio(o(d, "Giờ đăng"))
        if not ngay or not gio:
            continue
        try:
            moc = time.mktime((ngay.tm_year, ngay.tm_mon, ngay.tm_mday,
                               gio.tm_hour, gio.tm_min, 0, 0, 0, -1))
        except (OverflowError, ValueError):
            continue
        if not (tu < moc <= den):
            continue
        if not co_id:
            if con_cho <= 0:
                continue    # máy DOM sẽ bỏ gói này (trần gói tải mới/kênh/ngày)
            con_cho -= 1
        ra.append(ma)
    return ra


def _khe_tai_bo_sung_mo(bay_gio: float = None) -> bool:
    """Tránh phút :55–:05 — `tu_chay` (lịch mỗi giờ) giành khoá máy lúc :00."""
    phut = time.localtime(time.time() if bay_gio is None else bay_gio).tm_min
    return 5 < phut < 55


def chay_tai_bo_sung(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, bay_gio: float = None,
                     tai_ke_hoach=None, chay_con=None) -> bool:
    """MỘT bước tải bổ sung (gọi mỗi nhịp tim, tự giãn theo chu kỳ). Trả True
    nếu vừa chạy máy đăng cho một kênh. `tai_ke_hoach(cau_hinh_kenh, kenh)`
    và `chay_con(...)` là seam cho bài kiểm."""
    luc = time.time() if bay_gio is None else bay_gio
    if luc - _TAI_BO_SUNG["luc"] < CHU_KY_TAI_BO_SUNG_GIAY:
        return False
    if not _khe_tai_bo_sung_mo(luc):
        return False
    _TAI_BO_SUNG["luc"] = luc
    if tai_ke_hoach is None:
        def tai_ke_hoach(ch, kenh):
            if GOC not in sys.path:
                sys.path.insert(0, GOC)
            import nguon_tool  # noqa: PLC0415 — chỉ thư viện chuẩn
            return nguon_tool._tai_csv(ch, kenh)
    chay_con = chay_con or _chay_mot_lan
    so = _doc_so_video_id()
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    tt = _doc_trang_thai(cau_hinh)
    cuoi = _TAI_BO_SUNG.setdefault("cuoi", {})
    # XOAY VÒNG CÔNG BẰNG (30/09/2026): bản trước duyệt `cac_kenh` theo thứ tự
    # cố định và chạy kênh ĐẦU TIÊN có việc — kênh đứng trước luôn thắng. Giờ gom
    # đủ ứng viên rồi xếp: ít lượt hôm nay nhất → lâu chưa được chạy nhất → thứ tự.
    ung_vien = []
    for thu_tu, kenh in enumerate(cac_kenh):
        ch = hieu_luc.get(kenh) or {}
        if not bool(ch.get("tu_dang")) or str(ch.get("cach_dang") or "anh") == "anh":
            continue
        khoa_dem = "tai_bo_sung@{0}@{1}".format(kenh, hom_nay)
        da_chay = int(tt.get(khoa_dem) or 0)
        try:
            can = ma_can_tai_bo_sung(tai_ke_hoach(ch, kenh), kenh, so, luc)
        except Exception as loi:  # noqa: BLE001 — đọc kế hoạch hỏng thì chờ lượt sau
            ghi("tải bổ sung kênh {0}: không đọc được kế hoạch ({1})".format(kenh, str(loi)[:80]))
            continue
        khoa_goi = "tai_bo_sung_goi@{0}@{1}".format(kenh, hom_nay)
        dem_goi = tt.get(khoa_goi) if isinstance(tt.get(khoa_goi), dict) else {}
        het_luot = [m for m in can if int(dem_goi.get(m) or 0) >= TAI_BO_SUNG_TOI_DA_LUOT_GOI_NGAY]
        if da_chay >= TAI_BO_SUNG_TOI_DA_LUOT_NGAY:
            het_luot, can = can, []
        else:
            can = [m for m in can if m not in het_luot]
        # 03/10/2026: chạm trần thì GHI LÝ DO (1 lần/kênh/ngày) — trước đây im lặng.
        bao = _TAI_BO_SUNG.setdefault("da_bao", set())
        if het_luot and (kenh, hom_nay) not in bao:
            bao.add((kenh, hom_nay))
            ghi("tải bổ sung kênh {0}: bỏ qua {1} — hết lượt hôm nay (kênh {2}/{3}, gói ≤{4}); "
                "thử lại sau 00:00".format(kenh, ", ".join(het_luot), da_chay,
                                           TAI_BO_SUNG_TOI_DA_LUOT_NGAY,
                                           TAI_BO_SUNG_TOI_DA_LUOT_GOI_NGAY))
        if not can:
            continue
        ung_vien.append((da_chay, float(cuoi.get(kenh) or 0.0), thu_tu, kenh, ch, can,
                         khoa_dem, khoa_goi, dem_goi))
    ung_vien.sort(key=lambda x: x[:3])
    for da_chay, _cuoi, _tt, kenh, ch, can, khoa_dem, khoa_goi, dem_goi in ung_vien[:1]:
        if van_ipv4_mo():
            ghi("tải bổ sung kênh {0} ({1}) hoãn: van IPv4 đang mở".format(kenh, ", ".join(can)))
            return False
        if os.path.exists(os.path.join(GOC, "logs", "dang-dodang.json")):
            ghi("tải bổ sung kênh {0} hoãn: đang có máy đăng dở (dang-dodang.json)".format(kenh))
            return False
        if not giu_khoa_may_chung(viec="tai_len", kenh=kenh, uu_tien=1):
            # 04/10/2026: hụt khoá → thử lại sau ~1' (không đợi đủ chu kỳ 25'): cờ "chờ tải lên" chỉ sống 5',
            # sản xuất nhường ở khâu kế — phải có mặt để giành khe ngay khi khe nhả.
            _TAI_BO_SUNG["luc"] = luc - CHU_KY_TAI_BO_SUNG_GIAY + 60
            if not _TAI_BO_SUNG.get("bao_hoan") == (kenh, hom_nay):
                _TAI_BO_SUNG["bao_hoan"] = (kenh, hom_nay)
                ghi("tải bổ sung kênh {0} ({1}) hoãn: máy đang bận việc nặng (sản xuất/phiên) — "
                    "đã dựng cờ ưu tiên, thử lại mỗi phút".format(kenh, ", ".join(can)))
            return False
        _TAI_BO_SUNG.pop("bao_hoan", None)
        try:
            dem_moi = dict(dem_goi)
            for m in can:
                dem_moi[m] = int(dem_moi.get(m) or 0) + 1
            _luu_trang_thai(cau_hinh, **{khoa_dem: da_chay + 1, khoa_goi: dem_moi})
            cuoi[kenh] = luc
            ghi("── TẢI BỔ SUNG kênh {0}: {1} ──".format(kenh, ", ".join(can)))
            chrome = tim_chrome(ch)
            ghi_che_do_mat_cao(ch, False)   # Chrome mở cho việc đăng/bình luận — mắt cào KHÔNG quét
            if chrome and not _chrome_dang_chay(chrome):
                mo_chrome_kenh(ch, ch.get("studio_url") or "https://studio.youtube.com", chrome,
                               da_chay=False)
                _cho_devtools(_cong_devtools(ch), CHO_DEVTOOLS_GIAY)
            msg, _ma = chay_con(
                os.path.join(GOC, "may_dang_dom.py"), kenh, "tải bổ sung (DOM)",
                han_giay=float(cau_hinh.get("phien_han_dang_giay") or 90 * 60),
                co_gi_them=("--mot-lan", "--trong-phien",
                            "--cua-so-gio", str(int(CUA_SO_TAI_BO_SUNG_NGAY * 24)),
                            "--bien-gio", str(BIEN_TAI_BO_SUNG_GIO),
                            "--toi-da-ngay", str(TAI_LEN_TOI_DA_KENH_NGAY)))
            ghi("tải bổ sung kênh {0}: {1}".format(kenh, msg))
            # 04/10/2026 (7 kênh): tải xong (mã 0) mà còn kênh khác chờ → nhịp sau làm luôn, không đợi đủ
            # CHU_KY_TAI_BO_SUNG_GIAY (25') — mỗi lượt chỉ ~4', 7 kênh đợi lần lượt mất ~3 giờ vô ích.
            if _ma == 0 and len(ung_vien) > 1:
                _TAI_BO_SUNG["luc"] = 0.0
        finally:
            try:
                dong_chrome_kenh(ch)
            finally:
                nha_khoa_may_chung()
        return True
    return False


# ── NUÔI TRANG CHỦ (03/10/2026): mỗi ~10 phút mở tiến trình con vm/nuoi_trang_chu.py cho từng kênh đủ điều kiện ──
CHU_KY_NUOI_TRANG_CHU_GIAY = 10 * 60
_NUOI_TRANG_CHU = {"luc": 0.0, "con": {}, "ly": {}}


def _nhuong_kenh_nuoi(kenh: str, cho_giay: float = 120.0) -> bool:
    """Kênh đang được NUÔI trang chủ thì ghi cờ `.dung`, đợi phiên nuôi đóng Chrome (<= 2 phút).
    False = chưa nhường được (việc đăng hoãn, nhịp sau thử lại). Mọi việc đăng đều đi qua
    `giu_khoa_may_chung(kenh=...)` nên móc ở đó là đủ."""
    thu_muc = os.path.join(GOC, "logs", "nuoi-trang-chu")
    khoa = os.path.join(thu_muc, kenh + ".khoa")
    try:
        with open(khoa, "r", encoding="utf-8") as tep:
            pid = int(json.load(tep).get("pid") or 0)
        if not _pid_con_song(pid):
            return True
        with open(os.path.join(thu_muc, kenh + ".dung"), "w", encoding="utf-8") as tep:
            tep.write(str(time.time()))
    except (OSError, ValueError, TypeError, AttributeError):
        return True
    ghi("kênh {0} đang được nuôi trang chủ — báo dừng sớm, đợi đóng Chrome".format(kenh))
    han = time.monotonic() + cho_giay
    while os.path.exists(khoa) and _pid_con_song(pid) and time.monotonic() < han:
        time.sleep(2)
    if os.path.exists(khoa) and _pid_con_song(pid):
        ghi("kênh {0}: phiên nuôi chưa đóng Chrome sau {1:.0f}s — hoãn việc, thử lại nhịp sau".format(kenh, cho_giay))
        return False
    return True


def chay_nuoi_trang_chu(bay_gio: float = None, mo_con=None) -> int:
    """MỘT bước nuôi trang chủ (gọi mỗi nhịp tim, tự giãn 10 phút). Mỗi kênh đủ điều kiện một tiến trình
    con (tối đa 4 Chrome + RAM >= 4 GB do `kenh_den_luot` canh). Trả số con đang chạy."""
    luc = time.time() if bay_gio is None else bay_gio
    con = _NUOI_TRANG_CHU["con"]
    for k in [k for k, c in con.items() if c.poll() is not None]:
        ghi("nuôi trang chủ kênh {0}: tiến trình con xong (mã {1})".format(k, con.pop(k).returncode))
    if luc - _NUOI_TRANG_CHU["luc"] < CHU_KY_NUOI_TRANG_CHU_GIAY:
        return len(con)
    _NUOI_TRANG_CHU["luc"] = luc
    sys.path.insert(0, GOC) if GOC not in sys.path else None
    import nuoi_trang_chu  # noqa: PLC0415 — chỉ thư viện chuẩn khi nạp
    ra, ly = nuoi_trang_chu.kenh_den_luot(luc, set(con))
    if ra and van_ipv4_mo():
        ly, ra = dict(ly, **{k: "van IPv4 đang mở" for k in ra}), []
    for k, r in ly.items():     # mỗi lần bỏ qua ghi lý do, chỉ khi lý do đổi (bỏ số đếm lùi)
        if _NUOI_TRANG_CHU["ly"].get(k) != re.sub(r"\d+", "#", r):
            _NUOI_TRANG_CHU["ly"][k] = re.sub(r"\d+", "#", r)
            ghi("nuôi trang chủ kênh {0}: bỏ qua — {1}".format(k, r[:150]))
    for k in ra:
        _NUOI_TRANG_CHU["ly"].pop(k, None)
        ghi("── NUÔI TRANG CHỦ kênh {0}: mở tiến trình con ──".format(k))
        con[k] = (mo_con or subprocess.Popen)(
            [sys.executable, os.path.join(GOC, "nuoi_trang_chu.py"), "--kenh", k], cwd=GOC,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return len(con)


# ── THIẾT LẬP KÊNH (03/10/2026): kênh `thiet_lap_kenh: true` chưa `xong` → mở tiến trình con vm/thiet_lap_kenh_dom.py ──
#   Điền hồ sơ kênh (tên, handle, mô tả, logo, banner, từ khoá, mặc định tải lên, danh sách phát) vào Studio MỘT LẦN.
#   Cùng khoá `<kênh>.khoa` với nuôi trang chủ nên `_nhuong_kenh_nuoi` ở trên nhường được cho việc đăng; tuần tự từng kênh.
CHU_KY_THIET_LAP_KENH_GIAY = 10 * 60
_THIET_LAP_KENH = {"luc": 0.0, "con": {}, "ly": {}}


def chay_thiet_lap_kenh(bay_gio: float = None, mo_con=None) -> int:
    """MỘT bước thiết lập kênh (gọi mỗi nhịp tim, tự giãn 10 phút). Trả số tiến trình con đang chạy."""
    luc = time.time() if bay_gio is None else bay_gio
    con = _THIET_LAP_KENH["con"]
    for k in [k for k, c in con.items() if c.poll() is not None]:
        ghi("thiết lập kênh {0}: tiến trình con xong (mã {1})".format(k, con.pop(k).returncode))
    if luc - _THIET_LAP_KENH["luc"] < CHU_KY_THIET_LAP_KENH_GIAY:
        return len(con)
    _THIET_LAP_KENH["luc"] = luc
    sys.path.insert(0, GOC) if GOC not in sys.path else None
    import thiet_lap_kenh_dom  # noqa: PLC0415 — chỉ thư viện chuẩn khi nạp
    ra, ly = thiet_lap_kenh_dom.kenh_den_luot(luc, set(con))
    if ra and van_ipv4_mo():
        ly, ra = dict(ly, **{k: "van IPv4 đang mở" for k in ra}), []
    for k, r in ly.items():     # chỉ ghi khi lý do đổi (bỏ số đếm lùi)
        if _THIET_LAP_KENH["ly"].get(k) != re.sub(r"\d+", "#", r):
            _THIET_LAP_KENH["ly"][k] = re.sub(r"\d+", "#", r)
            ghi("thiết lập kênh {0}: bỏ qua — {1}".format(k, r[:150]))
    for k in ra:
        _THIET_LAP_KENH["ly"].pop(k, None)
        ghi("── THIẾT LẬP KÊNH {0}: mở tiến trình con ──".format(k))
        con[k] = (mo_con or subprocess.Popen)(
            [sys.executable, os.path.join(GOC, "thiet_lap_kenh_dom.py"), "--kenh", k], cwd=GOC,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return len(con)


# ── GHIM SỚM bình luận mồi (29/09/2026) ─────────────────────────────────────
#
# Video đăng qua máy DOM được YouTube tự công khai đúng giờ hẹn (vd 20:00), còn
# phiên kênh hôm sau mới chạy. Bình luận mồi ghim ngay giờ đầu là lúc có người xem
# nhất — nên mỗi ~20 phút, khi máy rảnh, kênh nào có video trong sổ videoId đã tới
# giờ công khai (≥5 phút, ≤72 giờ) mà sổ bình luận chưa `da_ghim` → mở Chrome kênh,
# chạy `may_cmt_dom.py --chi-moi --trong-phien`, đóng Chrome. Giữ khe "nang" như tải lên.

CHU_KY_GHIM_SOM_GIAY = 20 * 60
GHIM_SOM_TRE_PHUT = 5
GHIM_SOM_CUA_SO_GIO = 72
GHIM_SOM_TOI_DA_LUOT_NGAY = 4
_GHIM_SOM = {"luc": 0.0}


def _doc_so_cmt_dom() -> dict:
    try:
        with open(os.path.join(GOC, "logs", "cmt-dom.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else {}
    except (OSError, ValueError):
        return {}


def video_can_ghim_som(so_video: dict, so_cmt: dict, kenh: str, bay_gio: float = None,
                       tre_phut: float = GHIM_SOM_TRE_PHUT,
                       cua_so_gio: float = GHIM_SOM_CUA_SO_GIO,
                       ghim_bat: bool = True) -> list:
    """Hàm THUẦN: mã gói của `kenh` (trong sổ videoId, đã xác nhận lịch) vừa tới
    giờ công khai — lich + tre_phut ≤ bây giờ ≤ lich + cua_so_gio — mà sổ bình luận
    DOM chưa ghim / chưa kết thúc (tắt bình luận, ghim khác, thiếu chữ) / chưa
    biết hôm nay là kênh bị chặn ghim (chờ chủ kênh xác minh).

    30/09/2026: `ghim_bat=False` (kênh `ghim_dom=false`) thì gói đã có bình luận
    mồi (`da_dang_moi`) là XONG — bản trước coi "chưa ghim" là chưa xong nên cứ 20
    phút lại mở Chrome TL3 cho TL3-T7-0005 chỉ để máy bình luận báo "ghim TẮT".
    Bật ghim lại thì gói chưa `da_ghim` được xét lại như cũ."""
    bay_gio = time.time() if bay_gio is None else bay_gio
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(bay_gio))
    ra = []
    for khoa, muc in sorted((so_video or {}).items()):
        if not isinstance(muc, dict) or not str(khoa).startswith(kenh + "/"):
            continue
        vid = str(muc.get("video_id") or "")
        if not vid or muc.get("trang_thai") not in ("xac-nhan", "da-len-lich"):
            continue
        try:
            moc = time.mktime(time.strptime(str(muc.get("lich") or ""), "%d/%m/%Y %H:%M"))
        except (ValueError, OverflowError):
            continue
        if not (moc + tre_phut * 60 <= bay_gio <= moc + cua_so_gio * 3600):
            continue
        c = (so_cmt or {}).get(vid) or {}
        if c.get("da_ghim") or c.get("trang_thai") in ("tat-binh-luan", "ghim-khac", "khong-co-van-ban"):
            continue
        if not ghim_bat and c.get("da_dang_moi"):
            continue
        if c.get("trang_thai") == "cho-xac-minh" and str(c.get("ghim_cho_xac_minh") or "")[:10] == hom_nay:
            continue
        ra.append(str(khoa).split("/", 1)[1])
    return ra


def chay_ghim_som(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, bay_gio: float = None,
                  chay_con=None) -> bool:
    """MỘT bước ghim sớm (gọi mỗi nhịp tim khi không vừa chạy phiên/tải bổ sung,
    tự giãn theo chu kỳ). Trả True nếu vừa chạy máy bình luận cho một kênh."""
    luc = time.time() if bay_gio is None else bay_gio
    if luc - _GHIM_SOM["luc"] < CHU_KY_GHIM_SOM_GIAY:
        return False
    if not _khe_tai_bo_sung_mo(luc):
        return False
    _GHIM_SOM["luc"] = luc
    chay_con = chay_con or _chay_mot_lan
    so_video, so_cmt = _doc_so_video_id(), _doc_so_cmt_dom()
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    for kenh in cac_kenh:
        ch = hieu_luc.get(kenh) or {}
        if chon_may_cmt(ch.get("binh_luan_dom", True), bool(ch.get("tu_dang")),
                        co_token_oauth(kenh)) != "dom":
            continue
        khoa_dem = "ghim_som@{0}@{1}".format(kenh, hom_nay)
        da_chay = int(_doc_trang_thai(cau_hinh).get(khoa_dem) or 0)
        if da_chay >= GHIM_SOM_TOI_DA_LUOT_NGAY:
            continue
        # `ghim_dom` do tool đẩy xuống (KHOA_TU_TOOL); vắng thì theo mặc định của
        # `may_cmt_dom.doc_cai_dat` (False) — hai đầu phải cùng một nghĩa.
        can = video_can_ghim_som(so_video, so_cmt, kenh, luc,
                                 ghim_bat=bool(ch.get("ghim_dom", False)))
        if not can:
            continue
        if van_ipv4_mo():
            ghi("ghim sớm kênh {0} ({1}) hoãn: van IPv4 đang mở".format(kenh, ", ".join(can)))
            return False
        if os.path.exists(os.path.join(GOC, "logs", "dang-dodang.json")):
            ghi("ghim sớm kênh {0} hoãn: đang có máy đăng dở (dang-dodang.json)".format(kenh))
            return False
        if not giu_khoa_may_chung(viec="binh_luan", kenh=kenh, uu_tien=1):
            ghi("ghim sớm kênh {0} ({1}) hoãn: máy đang bận việc nặng".format(kenh, ", ".join(can)))
            return False
        try:
            _luu_trang_thai(cau_hinh, **{khoa_dem: da_chay + 1})
            ghi("── GHIM SỚM bình luận mồi kênh {0}: {1} ──".format(kenh, ", ".join(can)))
            chrome = tim_chrome(ch)
            ghi_che_do_mat_cao(ch, False)   # Chrome mở cho việc đăng/bình luận — mắt cào KHÔNG quét
            if chrome and not _chrome_dang_chay(chrome):
                mo_chrome_kenh(ch, ch.get("studio_url") or "https://studio.youtube.com", chrome,
                               da_chay=False)
                _cho_devtools(_cong_devtools(ch), CHO_DEVTOOLS_GIAY)
            msg, _ma = chay_con(
                os.path.join(GOC, "may_cmt_dom.py"), kenh, "ghim sớm (DOM)",
                han_giay=float(cau_hinh.get("phien_han_cmt_giay") or 20 * 60),
                co_gi_them=("--chi-moi", "--trong-phien"))
            ghi("ghim sớm kênh {0}: {1}".format(kenh, msg))
        finally:
            try:
                dong_chrome_kenh(ch)
            finally:
                nha_khoa_may_chung()
        return True
    return False


# ── BÙ MÀN HÌNH KẾT THÚC video đã đăng mà thiếu (01/10/2026) ────────────────
#
# Video lên kênh với sổ `mhkt` = bo / lỗi / rỗng (bước MHKT là PHỤ — hỏng vẫn lên
# lịch) tự vào HÀNG BÙ của đêm sau (`may_dang_dom.hang_bu_mhkt`). Giờ vắng:
# `bu_mhkt_tu`–`bu_mhkt_den` (mặc định 02:00–05:00), chỉ SAU khi lượt QUÉT NGÀY
# hôm nay của chính kênh đã xong (hoặc hết lượt), không khi phiên kênh nào sắp
# tới trong `BU_MHKT_NHUONG_PHIEN_PHUT` hay lượt quét của kênh khác sắp tới
# trong `BU_MHKT_NHUONG_QUET_PHUT`, tránh :55–:05; giữ khe Chrome dùng chung
# (viec "bu_mhkt"), cổng quét CHẶN. Mỗi kênh tối đa `BU_MHKT_TOI_DA_DEM` video/đêm
# (`--toi-da-video`), tối đa `BU_MHKT_LUOT_DEM` lượt mở Chrome/kênh/đêm. Hạn một
# lượt = tới mốc sớm nhất trong (hết khung, phiên kế −10', quét kế) — trần 30'.
# Máy đăng DOM làm từng video: trang sửa → nhập từ video đã có MHKT / dựng mẫu
# → Lưu → đọc lại; sổ `mhkt=ok:bu` hoặc `khong-the` + lý do; `mhkt-thieu.json`.

BU_MHKT_TU_MAC_DINH = "02:00"
BU_MHKT_DEN_MAC_DINH = "05:00"
BU_MHKT_TOI_DA_DEM = 3
BU_MHKT_LUOT_DEM = 2
BU_MHKT_NHUONG_PHIEN_PHUT = 20
BU_MHKT_NHUONG_QUET_PHUT = 10
#: Lượt bù ngắn hơn ngần này (phút) thì không mở Chrome.
BU_MHKT_TOI_THIEU_PHUT = 8
BU_MHKT_TRAN_PHUT = 30
CHU_KY_BU_MHKT_GIAY = 5 * 60
_BU_MHKT = {"luc": 0.0}


def _mdd():
    """Nạp `may_dang_dom` (cạnh agent.py) cho các hàm thuần của sổ videoId."""
    thu_muc = os.path.dirname(os.path.abspath(__file__))
    if thu_muc not in sys.path:
        sys.path.insert(0, thu_muc)
    import may_dang_dom  # noqa: PLC0415 — chỉ thư viện chuẩn
    return may_dang_dom


def _moc_gio_hom_nay(gio: str, luc: float):
    tm = _phan_tich_gio(str(gio or ""))
    if tm is None:
        return None
    lt = time.localtime(luc)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, tm.tm_hour, tm.tm_min, 0, 0, 0, -1))


def _quet_ngay_ket_thuc(muc: dict) -> bool:
    """Lượt QUÉT NGÀY hôm nay của kênh đã xong hẳn (xong hoặc hết lượt thử)."""
    muc = muc if isinstance(muc, dict) else {}
    return bool(muc.get("xong")) or int(muc.get("lan") or 0) >= QUET_NGAY_TOI_DA_LAN


def han_bu_mhkt(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, kenh: str, luc: float,
                tt: dict = None) -> tuple:
    """Hàm (gần) thuần: (số giây được chạy lượt bù của `kenh` lúc `luc`, lý do nếu 0).
    Chỉ đọc trạng thái đã cất (`trang-thai.json`) — không hỏi mạng."""
    tt = _doc_trang_thai(cau_hinh) if tt is None else tt
    ch = hieu_luc.get(kenh) or {}
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    tu = _moc_gio_hom_nay(ch.get("bu_mhkt_tu") or BU_MHKT_TU_MAC_DINH, luc)
    den = _moc_gio_hom_nay(ch.get("bu_mhkt_den") or BU_MHKT_DEN_MAC_DINH, luc)
    if tu is None or den is None or not (tu <= luc < den):
        return 0.0, "ngoài khung giờ vắng"
    if not _khe_tai_bo_sung_mo(luc):
        return 0.0, "phút :55–:05"
    if not _quet_ngay_ket_thuc(tt.get("quet_ngay@{0}@{1}".format(kenh, hom_nay))):
        return 0.0, "chờ QUÉT NGÀY của kênh xong"
    han = min(float(den) - 5 * 60, luc + BU_MHKT_TRAN_PHUT * 60)
    for vt, k in enumerate(cac_kenh):
        chk = hieu_luc.get(k) or {}
        # Phiên kênh (đăng) hôm nay chưa chạy: nhường, và kết thúc trước nó 10'.
        muc_phien = tt.get("phien_muc_tieu@{0}@{1}".format(k, hom_nay))
        if isinstance(muc_phien, str) and muc_phien and str(tt.get("phien_cuoi@" + k) or "") != hom_nay:
            moc = _moc_gio_hom_nay(muc_phien, luc)
            if moc is not None:
                if moc - luc < BU_MHKT_NHUONG_PHIEN_PHUT * 60:
                    return 0.0, "phiên kênh {0} lúc {1} sắp/đang tới".format(k, muc_phien)
                han = min(han, moc - 10 * 60)
        # Lượt QUÉT NGÀY của kênh khác chưa xong: nhường, và kết thúc trước lượt kế.
        if k == kenh:
            continue
        mq = tt.get("quet_ngay@{0}@{1}".format(k, hom_nay))
        mq = mq if isinstance(mq, dict) else {}
        if _quet_ngay_ket_thuc(mq):
            continue
        moc_q = _moc_gio_hom_nay(gio_quet_ngay_kenh(chk, vt), luc)
        if moc_q is None:
            continue
        if mq.get("luc"):
            moc_q = max(moc_q, float(mq.get("luc") or 0) + QUET_NGAY_THU_LAI_PHUT * 60)
        if moc_q - luc < BU_MHKT_NHUONG_QUET_PHUT * 60:
            return 0.0, "QUÉT NGÀY kênh {0} sắp/đang tới".format(k)
        han = min(han, moc_q)
    con = han - luc
    if con < BU_MHKT_TOI_THIEU_PHUT * 60:
        return 0.0, "không đủ {0} phút trước việc kế".format(BU_MHKT_TOI_THIEU_PHUT)
    return con, ""


def chay_bu_mhkt(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, bay_gio: float = None,
                 chay_con=None) -> bool:
    """MỘT bước BÙ MHKT (gọi mỗi nhịp tim sau QUÉT NGÀY, trước tải bổ sung; tự
    giãn `CHU_KY_BU_MHKT_GIAY`). Chọn MỘT kênh có hàng bù (ít lượt đêm nay nhất
    trước), chạy `may_dang_dom.py --bu-mhkt` trong khe Chrome. Trả True nếu vừa chạy."""
    luc = time.time() if bay_gio is None else bay_gio
    if luc - _BU_MHKT["luc"] < CHU_KY_BU_MHKT_GIAY:
        return False
    _BU_MHKT["luc"] = luc
    chay_con = chay_con or _chay_mot_lan
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    tt = _doc_trang_thai(cau_hinh)
    so = _doc_so_video_id()
    try:
        mdd = _mdd()
    except Exception as loi:  # noqa: BLE001 — thiếu máy đăng DOM: không có gì để bù
        ghi("bù MHKT: không nạp được may_dang_dom ({0})".format(str(loi)[:100]))
        return False
    ung_vien = []
    for thu_tu, kenh in enumerate(cac_kenh):
        ch = hieu_luc.get(kenh) or {}
        if ch.get("bu_mhkt") is False or not bool(ch.get("tu_dang")) \
                or str(ch.get("cach_dang") or "anh") == "anh":
            continue
        toi_da = int(ch.get("bu_mhkt_toi_da_dem") or BU_MHKT_TOI_DA_DEM)
        hang = mdd.hang_bu_mhkt(so, kenh, hom_nay, toi_da)
        if not hang:
            continue
        khoa_dem = "bu_mhkt@{0}@{1}".format(kenh, hom_nay)
        da_chay = int(tt.get(khoa_dem) or 0)
        if da_chay >= BU_MHKT_LUOT_DEM:
            continue
        ung_vien.append((da_chay, thu_tu, kenh, ch, hang, khoa_dem, toi_da))
    if not ung_vien:
        return False
    ung_vien.sort(key=lambda x: x[:2])
    chon = None
    for uv in ung_vien:
        con, _ly_do = han_bu_mhkt(cau_hinh, hieu_luc, cac_kenh, uv[2], luc, tt)
        if con > 0:
            chon = uv
            break
    if chon is None:
        return False
    da_chay, _tt, kenh, ch, hang, khoa_dem, toi_da = chon
    if van_ipv4_mo():
        ghi("bù MHKT kênh {0} hoãn: van IPv4 đang mở".format(kenh))
        return False
    if os.path.exists(os.path.join(GOC, "logs", "dang-dodang.json")):
        ghi("bù MHKT kênh {0} hoãn: đang có máy đăng dở (dang-dodang.json)".format(kenh))
        return False
    if not tim_chrome(ch):
        return False
    if not giu_khoa_may_chung(viec="bu_mhkt", kenh=kenh, uu_tien=1):
        ghi("bù MHKT kênh {0} hoãn: máy đang bận việc nặng".format(kenh))
        return False
    try:
        _luu_trang_thai(cau_hinh, **{khoa_dem: da_chay + 1})
        ghi("── BÙ MHKT kênh {0}: {1} (hạn {2:.0f} phút) ──".format(
            kenh, ", ".join(k.split("/", 1)[-1] for k, _v in hang), con / 60))
        chrome = tim_chrome(ch)
        ghi_che_do_mat_cao(ch, False)   # Chrome mở để sửa video — mắt cào KHÔNG quét
        if chrome and not _chrome_dang_chay(chrome):
            mo_chrome_kenh(ch, ch.get("studio_url") or "https://studio.youtube.com", chrome,
                           da_chay=False)
            _cho_devtools(_cong_devtools(ch), CHO_DEVTOOLS_GIAY)
        msg, _ma = chay_con(
            os.path.join(GOC, "may_dang_dom.py"), kenh, "bù MHKT (DOM)",
            han_giay=con + 3 * 60,
            co_gi_them=("--bu-mhkt", "--trong-phien", "--toi-da-video", str(toi_da),
                        "--han-giay", str(int(con + 5 * 60))))
        ghi("bù MHKT kênh {0}: {1}".format(kenh, msg))
        try:
            sau = _doc_so_video_id()
            for k, _v in hang:
                m = sau.get(k) or {}
                if m.get("mhkt_bu_ngay") == hom_nay:
                    ghi("bù MHKT {0}: {1}{2}".format(k.split("/", 1)[-1], m.get("mhkt_bu_ket"),
                                                     " — " + str(m.get("mhkt_bu_ly_do")) if m.get("mhkt_bu_ly_do") else ""))
                    if m.get("mhkt_bu_ket") == "loi" and int(m.get("mhkt_bu_loi_lan") or 0) >= mdd.BU_MHKT_TOI_DA_LOI:
                        ghi("CẢNH BÁO bù MHKT {0}: hỏng {1} đêm — thôi tự bù, chủ kênh xem mhkt-thieu.json".format(
                            k, m.get("mhkt_bu_loi_lan")))
        except Exception:  # noqa: BLE001 — chỉ là dòng nhật ký
            pass
    finally:
        try:
            dong_chrome_kenh(ch)
        finally:
            nha_khoa_may_chung()
    return True


# ── SỬA VIDEO CŨ — cứu CTR thấp (01/10/2026) ────────────────────────────────
#
# Giám đốc kênh (`core/giam_doc/cuu_ctr.py`) xếp việc đổi tiêu đề / bìa vào
# `logs/hang-sua.json` (chủ đã duyệt, hoặc kênh đã đủ thành tích tự áp). Bước này
# chạy ĐÚNG khe giờ vắng của bù MHKT (`han_bu_mhkt`: 02:00–05:00, sau QUÉT NGÀY
# của kênh, nhường quét kênh khác, tránh :55–:05), giữ khe Chrome dùng chung
# (viec "sua_video"), và KHÔNG sửa trong 60 phút trước phiên đăng của bất kỳ
# kênh nào (`SUA_NHUONG_PHIEN_PHUT`). Máy DOM: `may_dang_dom.py --sua-video`
# (trang sửa → gõ/tải lên → đọc lại → Lưu → đọc lại), kết quả `logs/sua-cuoi.json`.

SUA_NHUONG_PHIEN_PHUT = 60
CHU_KY_SUA_VIDEO_GIAY = 5 * 60
SUA_LUOT_DEM = 2
_SUA_VIDEO = {"luc": 0.0}


def han_sua_video(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, kenh: str, luc: float,
                  tt: dict = None) -> tuple:
    """(số giây được chạy lượt sửa của `kenh`, lý do nếu 0) — luật khe của bù MHKT + nhường 60' trước MỌI
    phiên đăng còn chưa chạy hôm nay. Hàm (gần) thuần, chỉ đọc trạng thái đã cất."""
    tt = _doc_trang_thai(cau_hinh) if tt is None else tt
    con, ly_do = han_bu_mhkt(cau_hinh, hieu_luc, cac_kenh, kenh, luc, tt)
    if con <= 0:
        return con, ly_do
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    for k in cac_kenh:
        muc_phien = tt.get("phien_muc_tieu@{0}@{1}".format(k, hom_nay))
        if isinstance(muc_phien, str) and muc_phien and str(tt.get("phien_cuoi@" + k) or "") != hom_nay:
            moc = _moc_gio_hom_nay(muc_phien, luc)
            if moc is not None and moc - luc < SUA_NHUONG_PHIEN_PHUT * 60 + BU_MHKT_TOI_THIEU_PHUT * 60:
                return 0.0, "phiên kênh {0} lúc {1} trong 60 phút tới — không sửa video".format(k, muc_phien)
            if moc is not None:
                con = min(con, moc - SUA_NHUONG_PHIEN_PHUT * 60 - luc)
    if con < BU_MHKT_TOI_THIEU_PHUT * 60:
        return 0.0, "không đủ {0} phút trước việc kế".format(BU_MHKT_TOI_THIEU_PHUT)
    return con, ""


def chay_sua_video(cau_hinh: dict, hieu_luc: dict, cac_kenh: list, bay_gio: float = None,
                   chay_con=None) -> bool:
    """MỘT bước SỬA VIDEO CŨ (mỗi nhịp tim sau bù MHKT; tự giãn `CHU_KY_SUA_VIDEO_GIAY`). Chọn MỘT kênh có
    việc trong `logs/hang-sua.json` (ít lượt đêm nay nhất trước), chạy `may_dang_dom.py --sua-video` trong
    khe Chrome. Trả True nếu vừa chạy."""
    luc = time.time() if bay_gio is None else bay_gio
    if luc - _SUA_VIDEO["luc"] < CHU_KY_SUA_VIDEO_GIAY:
        return False
    _SUA_VIDEO["luc"] = luc
    chay_con = chay_con or _chay_mot_lan
    hom_nay = time.strftime("%Y-%m-%d", time.localtime(luc))
    try:
        mdd = _mdd()
    except Exception as loi:  # noqa: BLE001
        ghi("sửa video: không nạp được may_dang_dom ({0})".format(str(loi)[:100]))
        return False
    hang = mdd.doc_hang_sua(os.path.join(GOC, "logs", "hang-sua.json"))
    if not hang:
        return False
    tt = _doc_trang_thai(cau_hinh)
    ung_vien = []
    for thu_tu, kenh in enumerate(cac_kenh):
        ch = hieu_luc.get(kenh) or {}
        if ch.get("sua_video") is False or str(ch.get("cach_dang") or "anh") == "anh":
            continue
        viec = mdd.hang_sua_kenh(hang, kenh, hom_nay, mdd.SUA_TOI_DA_DEM)
        if not viec:
            continue
        khoa_dem = "sua_video@{0}@{1}".format(kenh, hom_nay)
        da_chay = int(tt.get(khoa_dem) or 0)
        if da_chay >= SUA_LUOT_DEM:
            continue
        ung_vien.append((da_chay, thu_tu, kenh, ch, viec, khoa_dem))
    if not ung_vien:
        return False
    ung_vien.sort(key=lambda x: x[:2])
    chon, con = None, 0.0
    for uv in ung_vien:
        con, _ly_do = han_sua_video(cau_hinh, hieu_luc, cac_kenh, uv[2], luc, tt)
        if con > 0:
            chon = uv
            break
    if chon is None:
        return False
    da_chay, _tt, kenh, ch, viec, khoa_dem = chon
    if van_ipv4_mo():
        ghi("sửa video kênh {0} hoãn: van IPv4 đang mở".format(kenh))
        return False
    if os.path.exists(os.path.join(GOC, "logs", "dang-dodang.json")):
        ghi("sửa video kênh {0} hoãn: đang có máy đăng dở (dang-dodang.json)".format(kenh))
        return False
    if not tim_chrome(ch):
        return False
    if not giu_khoa_may_chung(viec="sua_video", kenh=kenh, uu_tien=1):
        ghi("sửa video kênh {0} hoãn: máy đang bận việc nặng".format(kenh))
        return False
    try:
        _luu_trang_thai(cau_hinh, **{khoa_dem: da_chay + 1})
        ghi("── SỬA VIDEO kênh {0}: {1} (hạn {2:.0f} phút) ──".format(
            kenh, ", ".join("{0}[{1}]".format(v["video_id"], v.get("buoc")) for v in viec), con / 60))
        chrome = tim_chrome(ch)
        ghi_che_do_mat_cao(ch, False)   # Chrome mở để sửa video — mắt cào KHÔNG quét
        if chrome and not _chrome_dang_chay(chrome):
            mo_chrome_kenh(ch, ch.get("studio_url") or "https://studio.youtube.com", chrome, da_chay=False)
            _cho_devtools(_cong_devtools(ch), CHO_DEVTOOLS_GIAY)
        msg, _ma = chay_con(
            os.path.join(GOC, "may_dang_dom.py"), kenh, "sửa video (DOM)", han_giay=con + 3 * 60,
            co_gi_them=("--sua-video", "--trong-phien", "--toi-da-video", str(mdd.SUA_TOI_DA_DEM),
                        "--han-giay", str(int(con + 5 * 60))))
        ghi("sửa video kênh {0}: {1}".format(kenh, msg))
        try:
            for v in mdd.doc_hang_sua(os.path.join(GOC, "logs", "hang-sua.json")):
                if v.get("kenh") == kenh and v.get("thu_ngay") == hom_nay and any(v.get("id") == x.get("id") for x in viec):
                    ghi("sửa video {0} [{1}]: {2}{3}".format(v.get("video_id"), v.get("buoc"), v.get("trang_thai"),
                                                         " — " + str(v.get("ly_do")) if v.get("ly_do") else ""))
                    if v.get("trang_thai") == "loi" and int(v.get("lan_loi") or 0) >= mdd.SUA_TOI_DA_LOI:
                        ghi("CẢNH BÁO sửa video {0}: hỏng {1} lần — thôi, giám đốc kênh ghi lỗi vào sổ duyệt".format(
                            v.get("video_id"), v.get("lan_loi")))
        except Exception:  # noqa: BLE001 — chỉ là dòng nhật ký
            pass
    finally:
        try:
            dong_chrome_kenh(ch)
        finally:
            nha_khoa_may_chung()
    return True


# ── Vòng đời ─────────────────────────────────────────────────────────────────


_O_MOT_MINH = None      # giữ tham chiếu — ổ khoá sống theo tiến trình


#: Vừa thay chỗ một agent xong thì trong chừng này giây KHÔNG được thay tiếp.
#:
#: ═══ VÌ SAO CÓ CỬA NÀY (21/09/2026) ═══
#:
#: Máy này có HAI bộ giám sát cùng nuôi ba con của `vm/`, mỗi bộ một mình một
#: cõi và không biết bộ kia tồn tại: `MyTool/core/giam_sat_vm.py` (chạy trong
#: tiến trình Qt của tool) và `vm/giao_dien.py` (bảng điều khiển riêng của
#: vm). Cả hai đều dùng `taskkill /F /T`.
#:
#: Khi cả hai cùng chạy thì thành vòng luẩn quẩn: A đẻ agent → agent mới thấy
#: cổng 8767 đang bị agent của B giữ → giết nó (kèm CẢ CÂY CON, tức Chrome
#: của kênh) → B thấy con mình chết → đẻ lại → giết agent của A → lặp mãi.
#:
#: Đo trên `agent.log` ngày 21/09/2026: 278 dòng "đã dọn agent cũ" nhưng chỉ
#: 14 lần khởi động thật, và các lần dọn đi theo CẶP cách nhau 8–9 giây. Kèm
#: theo là 238 dòng "Chrome đang tắt — đã mở lại". Thư mục Crashpad của trình
#: duyệt RỖNG và Nhật ký sự kiện Windows không có Application Error nào cho
#: `chrome.exe`/`TL4-T7.exe` — tức Chrome không tự hỏng, nó BỊ GIẾT.
#:
#: Cửa này cắt vòng lặp ở chỗ rẻ nhất: bản thứ hai chịu thua và thoát, thay vì
#: giành lại. Vẫn giữ nguyên nết cũ cho người dùng thật — nhấp đúp mở cửa sổ
#: mới vẫn thay chỗ được, chỉ là không thay hai lần trong vòng hai phút.
#: Muốn ép thay ngay thì `python agent.py --thay`.
CHONG_GIANH_CHO_GIAY = 120.0


def _luc_thay_cho_gan_nhat(duong: str) -> float:
    """Mốc thời gian lần thay chỗ gần nhất, 0 nếu chưa có/đọc không được."""
    try:
        with open(duong, "r", encoding="ascii") as tep:
            return float(tep.read().strip())
    except (OSError, ValueError):
        return 0.0


def _ghi_luc_thay_cho(duong: str) -> None:
    try:
        with open(duong, "w", encoding="ascii") as tep:
            tep.write(repr(time.time()))
    except OSError:
        pass


def mot_minh(cong: int = 8767, duong_pid: str = "", thay: bool = False, duong_dang_lam: str = "") -> bool:
    """Chỉ MỘT agent mỗi máy — bản mới tự DỌN bản cũ rồi thay chỗ.

    TRỪ khi bản cũ đang làm dở một việc (`dang-lam.json` còn tươi, xem `viec_dang_lam`): mở
    thêm cửa sổ để XEM không được giết việc đang chạy. Muốn thay thật thì `python agent.py --thay`.

    Chủ dự án, 02/09/2026: *"thiết kế để... không có bug khi dùng dài hạn"*.
    Bug dài hạn số một của loại chương trình này là XÁC SỐNG: nhấp đúp hai
    lần là hai agent cùng hỏi việc, cùng nuôi Chrome, cùng đăng video.

    Ổ khoá là một cổng TCP chỉ nghe 127.0.0.1: tiến trình chết kiểu gì HĐH
    cũng tự nhả cổng — không có khoá mồ côi như lock file. `agent.pid` chỉ
    để bản mới biết PID bản cũ mà dọn (taskkill cả cây — bản cũ có thể đang
    cầm tool đăng con).
    """
    global _O_MOT_MINH
    duong_pid = duong_pid or os.path.join(GOC, "agent.pid")
    for lan in range(2):
        try:
            o = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # KHÔNG SO_REUSEADDR: trên Windows, bind mặc định là độc quyền —
            # đúng thứ một ổ khoá cần.
            o.bind(("127.0.0.1", int(cong)))
            o.listen(1)
            _O_MOT_MINH = o
            try:
                with open(duong_pid, "w", encoding="ascii") as tep:
                    tep.write(str(os.getpid()))
            except OSError:
                pass
            return True
        except OSError:
            if lan:
                break
            try:
                with open(duong_pid, "r", encoding="ascii") as tep:
                    pid = int(tep.read().strip())
            except (OSError, ValueError):
                return False
            if pid and pid != os.getpid():
                duong_thay = duong_pid + ".thay-cho"
                cach = time.time() - _luc_thay_cho_gan_nhat(duong_thay)
                if not thay and 0 <= cach < CHONG_GIANH_CHO_GIAY:
                    ghi("agent PID {0} vừa được thay chỗ {1:.0f} giây trước — bản này THOÁT thay vì "
                        "giành lại. Hai bộ giám sát (tool và bảng điều khiển vm) đang cùng nuôi "
                        "agent; giành qua lại sẽ giết cả Chrome của kênh. Chỉ nên để MỘT bộ chạy. "
                        "Muốn ép thay: python agent.py --thay".format(pid, cach))
                    return False
                do = viec_dang_lam(duong_dang_lam)
                if do and not thay:
                    ghi("agent PID {0} ĐANG LÀM việc #{1} [{2}] từ {3} — bản này KHÔNG thay chỗ để "
                        "khỏi giết việc đang chạy. Cửa sổ này chỉ để xem: đọc agent.log. Muốn thay "
                        "thật: python agent.py --thay".format(
                            pid, do.get("id"), do.get("loai"),
                            time.strftime("%H:%M", time.localtime(float(do.get("tu") or 0)))))
                    return False
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                               capture_output=True)
                # Ghi mốc NGAY SAU khi giết: bản kế tiếp (nếu bộ giám sát kia
                # lại đẻ ra) đọc mốc này rồi chịu thua, không giành lại nữa.
                _ghi_luc_thay_cho(duong_thay)
                ghi("đã dọn agent cũ (PID {0}) — bản này thay chỗ".format(pid))
                # ``taskkill`` có thể trả về trước khi Windows thực sự thu hồi socket.
                # Chờ tiến trình chết hẳn để lần bind kế không báo nhầm còn agent khác.
                for _cho in range(20):
                    if not _pid_con_song(pid):
                        break
                    time.sleep(0.25)
                time.sleep(0.25)
    return False


def chay(cau_hinh: dict, mot_vong: bool = False) -> None:
    """Vòng đời của agent — MỘT tiến trình cho CẢ MÁY, dù máy phục vụ một
    kênh (nếp cũ) hay tới NĂM kênh cùng niche (một VPS, mỗi kênh một Chrome
    `<MÃ>\\<MÃ>.exe` cạnh nhau). Mỗi nhịp tim (30s) lần lượt hỏi việc CHO
    TỪNG KÊNH — lệnh vẫn tới chậm nhất 30 giây/kênh, không nện trạm dày hơn;
    việc chạy TUẦN TỰ (một job xong mới tới lượt kênh kế) vì Chrome/PyAutoGUI
    chỉ có một cửa sổ màn hình để dùng chung.
    """
    if not mot_vong and not mot_minh(thay="--thay" in sys.argv):
        ghi("một agent khác đang chạy — thoát, không chạy đôi (chạy đôi là hỏi việc đôi, "
            "đăng video đôi). Cửa sổ này tự đóng sau 20 giây.")
        time.sleep(20)
        return
    if not cau_hinh.get("ten_may"):
        # Config đóng gói sẵn từ tool để trống tên máy — lấy tên máy THẬT
        # lúc chạy, không phải tên máy đã đóng gói.
        cau_hinh["ten_may"] = os.environ.get("COMPUTERNAME", "vm")
    cac_kenh = danh_sach_kenh(cau_hinh) or [cau_hinh.get("kenh") or "kenh"]
    kenh_chinh = cac_kenh[0]
    _don_kenh_cu_khoi_cai_dat_tool(cac_kenh)
    if len(cac_kenh) > 1:
        ghi("agent {0} kênh ({1}), máy {2}".format(
            len(cac_kenh), ", ".join(cac_kenh), cau_hinh.get("ten_may")))
    else:
        ghi("agent kênh {0}, máy {1}".format(cac_kenh[0], cau_hinh.get("ten_may")))
    cau_hinh = chon_tram(cau_hinh, in_ra=ghi)
    ghi("hỏi việc {0} mỗi {1}s{2}".format(
        cau_hinh.get("tram"), NHIP_GIAY,
        " (lần lượt {0} kênh mỗi nhịp)".format(len(cac_kenh))
        if len(cac_kenh) > 1 else ""))
    hieu_luc = {}                  # cấu hình hiệu lực CỦA TỪNG KÊNH
    for kenh in cac_kenh:
        hieu_luc[kenh] = cau_hinh_kenh(cau_hinh, kenh)
        chrome = tim_chrome(hieu_luc[kenh])
        ghi("Chrome kênh {0}: {1}".format(
            kenh, chrome or "CHƯA THẤY — đặt vm cạnh Chrome hoặc điền "
                            "chrome/chrome_theo_kenh trong config"))
    if not mot_vong and che_do_phien_bat(cau_hinh, hieu_luc.get(kenh_chinh)):
        # Nếu Windows/agent tắt giữa phiên, Chrome con không luôn chết theo cha.
        # Dọn mọi trình duyệt do hàng đợi quản lý trước lượt mới để không có hai
        # kênh cùng chiếm RAM rồi mới bắt đầu lại kênh dang dở từ checkpoint.
        for kenh in cac_kenh:
            dong_chrome_kenh(hieu_luc[kenh])
        ghi("đã dọn Chrome còn sót từ phiên trước — hàng đợi bắt đầu từ một kênh")
    # Mắt cào: tải bản mới nhất từ trạm về cạnh agent (trạm tắt thì dùng bản
    # đã có). Không bắt ai mở chrome://extensions nữa. Mỗi kênh một lượt —
    # máy nhiều kênh thì mỗi kênh tự có thư mục riêng (không báo nhầm kênh).
    #
    # Kênh nào có đăng ký BỀN trong hồ sơ (TL4-T7: `location=4` trỏ thư mục phẳng
    # `vm\tien-ich`, bản 2.6.2 từ lần bấm *Load unpacked* tay ngày xưa) thì bản mới
    # được chép ĐÈ vào đúng thư mục ấy — làm NGAY ĐÂY, lúc trình duyệt còn đóng, chứ
    # không lúc mở: ghi đè mã một extension đang chạy là kiểu làm Chrome tự tắt nó
    # giữa phiên. Kênh ấy sau đó vẫn chạy đường cũ, không nạp DevTools (tránh hai bản
    # cùng cào); ba kênh mới không có đăng ký bền nên đi đường DevTools mỗi lần mở.
    if not mot_vong:
        for kenh in cac_kenh:
            if bao_dam_tien_ich(hieu_luc[kenh]):
                try:
                    dong_bo_tien_ich_ben(hieu_luc[kenh])
                # Chép không được thì kênh ấy chạy bản cũ — vẫn cào, không vỡ.
                except Exception as loi:  # noqa: BLE001
                    ghi("extension: không đồng bộ được bản bền cho kênh {0} "
                        "({1})".format(kenh, str(loi)[:120]))
        # CỔNG QUÉT (30/09/2026): chế độ phiên → mặc định CHẶN (chỉ QUÉT NGÀY mở);
        # máy một kênh nếp cũ → xoá tệp, mắt cào tự do như trước.
        phien = che_do_phien_bat(cau_hinh, hieu_luc.get(kenh_chinh))
        for kenh in cac_kenh:
            ghi_che_do_mat_cao(hieu_luc[kenh], False if phien else None)
        if phien:
            ghi("QUÉT NGÀY: {0} — mắt cào chỉ quét trong lượt này; Chrome mở để đăng/bình luận "
                "thì cổng quét CHẶN".format(", ".join(
                    "{0} {1}".format(k, gio_quet_ngay_kenh(hieu_luc[k], i))
                    for i, k in enumerate(cac_kenh))))
    hong_lien_tiep = 0
    while True:
        co_loi = False
        for kenh in cac_kenh:
            try:
                tra = hoi_viec(cau_hinh, kenh=kenh)
                if "viec" in tra or "cai_dat" in tra:
                    # Trạm đời mới: việc + thiết lập đi cùng một nhịp tim.
                    # Thiết lập của TOOL thắng config máy — tool là nơi
                    # kiểm soát; chỉ kênh CHÍNH mới ghi đè khoá top-level
                    # của cai-dat-tool.json (đời đọc cũ chỉ biết một kênh).
                    hieu_luc[kenh] = ap_cai_dat_tool(
                        cau_hinh_kenh(cau_hinh, kenh), tra.get("cai_dat"),
                        kenh_chinh=kenh_chinh)
                    viec = tra.get("viec") or {}
                else:
                    viec = tra          # trạm đời cũ: trả thẳng việc
                if viec and viec.get("id"):
                    ghi("nhận việc #{0} [{1}] kênh {2}".format(
                        viec["id"], viec.get("loai"), kenh))
                    try:
                        da_bao_cho = False
                        while not giu_khoa_may_chung(viec="viec", kenh=kenh, uu_tien=1):
                            if not da_bao_cho:
                                ghi("việc #{0}: đang xếp hàng sau việc nặng hiện tại".format(viec["id"]))
                                da_bao_cho = True
                            time.sleep(NHIP_GIAY)
                        try:
                            ket_qua = lam_viec(hieu_luc[kenh], viec)
                        finally:
                            nha_khoa_may_chung()
                        bao_xong(cau_hinh, int(viec["id"]), ket_qua=ket_qua, kenh=kenh)
                        ghi("xong việc #{0} kênh {1}".format(viec["id"], kenh))
                    except Exception as loi:  # noqa: BLE001 — một việc hỏng, agent sống
                        bao_xong(cau_hinh, int(viec["id"]), loi=str(loi), kenh=kenh)
                        ghi("việc #{0} kênh {1} hỏng: {2}".format(viec["id"], kenh, loi))
            except Exception as loi:  # noqa: BLE001 — trạm tắt/mạng chập là chuyện thường
                co_loi = True
                if hong_lien_tiep in (0, 9) or hong_lien_tiep % 120 == 0:
                    ghi("chưa gọi được trạm cho kênh {0} ({1}) — cứ thử lại đều".format(
                        kenh, str(loi)[:120]))
        hong_lien_tiep = hong_lien_tiep + 1 if co_loi else 0
        if co_loi and hong_lien_tiep % 10 == 0:
            # Im lâu có khi không phải trạm tắt mà là địa chỉ đổi (IPv6
            # nhà mạng cấp lại) — dò lại các ứng viên đã đóng gói, rồi
            # ngồi nghe loa gọi của trạm một lát: trạm bật là nó tự réo
            # các VPS đã lưu mỗi ~60 giây, nghe 65 giây là đủ một vòng.
            cau_hinh = chon_tram(cau_hinh)
            ra = cho_gioi_thieu(cong=8765, cho_giay=65.0)
            if ra:
                cau_hinh["tram"] = ra
                ghi("trạm gọi sang giới thiệu: {0}".format(ra))
        # CHẾ ĐỘ PHIÊN (18/09, máy nhiều kênh): thay TOÀN BỘ lưới "giữ Chrome
        # sống 24/7 + quét theo khe + nuôi tool đăng tự lặp" bằng hàng đợi
        # phiên MỘT-KÊNH-MỘT-LÚC — xem `chay_hang_doi_phien`. Việc TAY (vòng
        # trên, `hoi_viec`/`lam_viec`) đã chạy XONG cho nhịp tim này rồi mới
        # tới đây, cùng một luồng — không bao giờ chồng lên phiên.
        if che_do_phien_bat(cau_hinh, hieu_luc.get(kenh_chinh)):
            vua_chay_phien = False
            try:
                vua_chay_phien = chay_hang_doi_phien(cau_hinh, hieu_luc, cac_kenh)
            except Exception as loi:  # noqa: BLE001 — một phiên hỏng, agent sống, mai lại tới lượt
                ghi("hàng đợi phiên hỏng: {0}".format(loi))
            # Tải lên BỔ SUNG — 04/10/2026: đứng TRƯỚC quét ngày (luật ưu tiên "đăng đúng giờ > quét Studio");
            # trước đây một lượt quét ~25' mở ra ngay sau khởi động, video chờ tải phải đợi.
            vua_tai = False
            if not vua_chay_phien and not mot_vong:
                try:
                    vua_tai = chay_tai_bo_sung(cau_hinh, hieu_luc, cac_kenh)
                except Exception as loi:  # noqa: BLE001 — bước phụ hỏng, agent sống
                    ghi("tải bổ sung hỏng: {0}".format(loi))
                vua_chay_phien = vua_tai
            # QUÉT NGÀY (30/09/2026) — việc quét độc lập, khung đêm, sau phiên
            # (phiên có hạn giờ thật) và sau tải bổ sung.
            if not vua_chay_phien and not mot_vong:
                try:
                    vua_chay_phien = chay_quet_ngay(cau_hinh, hieu_luc, cac_kenh)
                except Exception as loi:  # noqa: BLE001 — bước hỏng, agent sống, lịch tự thử lại
                    ghi("QUÉT NGÀY hỏng: {0}".format(loi))
            # BÙ MHKT video cũ (01/10/2026) — giờ vắng, sau QUÉT NGÀY của kênh.
            if not vua_chay_phien and not mot_vong:
                try:
                    vua_chay_phien = chay_bu_mhkt(cau_hinh, hieu_luc, cac_kenh)
                except Exception as loi:  # noqa: BLE001 — bước phụ hỏng, agent sống, đêm sau thử lại
                    ghi("bù MHKT hỏng: {0}".format(loi))
            # SỬA VIDEO CŨ (01/10/2026, cứu CTR thấp) — cùng khe giờ vắng của bù MHKT.
            if not vua_chay_phien and not mot_vong:
                try:
                    vua_chay_phien = chay_sua_video(cau_hinh, hieu_luc, cac_kenh)
                except Exception as loi:  # noqa: BLE001 — bước phụ hỏng, agent sống, đêm sau thử lại
                    ghi("sửa video hỏng: {0}".format(loi))
            # (Tải lên bổ sung đã chạy ở đầu nhịp — xem trên.)
            if not vua_chay_phien and not mot_vong:
                # Ghim sớm bình luận mồi cho video vừa công khai (máy bình luận DOM).
                if not vua_tai:
                    try:
                        chay_ghim_som(cau_hinh, hieu_luc, cac_kenh)
                    except Exception as loi:  # noqa: BLE001 — bước phụ hỏng, agent sống
                        ghi("ghim sớm hỏng: {0}".format(loi))
                try:
                    chay_nuoi_trang_chu()
                except Exception as loi:  # noqa: BLE001 — bước phụ hỏng, agent sống
                    ghi("nuôi trang chủ hỏng: {0}".format(loi))
                try:
                    chay_thiet_lap_kenh()
                except Exception as loi:  # noqa: BLE001 — bước phụ hỏng, agent sống
                    ghi("thiết lập kênh hỏng: {0}".format(loi))
        else:
            # Lịch cố định + giữ Chrome chạy cả khi trạm tắt: quét Studio
            # không cần trạm sống (extension tự ghi vào Tải xuống khi không
            # có trạm). Dùng cấu hình HIỆU LỰC — trạm tắt thì giữ thiết lập
            # tool đẩy xuống lần cuối. Mỗi kênh làm riêng — một kênh hỏng
            # không kéo kênh khác. (Nếp CŨ — máy một-kênh hoặc chưa bật phiên.)
            for kenh in cac_kenh:
                try:
                    viec_theo_lich(hieu_luc[kenh], la_kenh_dau=(kenh == kenh_chinh))
                except Exception as loi:  # noqa: BLE001
                    ghi("lịch hằng ngày hỏng (kênh {0}): {1}".format(kenh, loi))
                # Nuôi Chrome mỗi vòng: chết thì mở lại để extension luôn sống.
                try:
                    giu_chrome(hieu_luc[kenh])
                except Exception as loi:  # noqa: BLE001
                    ghi("giữ Chrome hỏng (kênh {0}): {1}".format(kenh, loi))
            # Nuôi tool đăng — CHỈ MỘT lần/máy (không phải một lần/kênh): tool
            # đăng đã tự quét MỌI kênh cạnh nó (discover_channels) trong một
            # tiến trình duy nhất, "bật máy là all mọi thứ" (02/09).
            try:
                giu_tool_dang(hieu_luc[kenh_chinh])
            except Exception as loi:  # noqa: BLE001
                ghi("giữ tool đăng hỏng: {0}".format(loi))
        if mot_vong:
            return
        # Chờ giãn dần khi trạm im ắng lâu (tối đa 5 phút) — máy nhà tắt tool
        # qua đêm thì agent không việc gì phải hỏi đều 30 giây suốt đêm.
        time.sleep(min(NHIP_GIAY * max(1, hong_lien_tiep // 10 + 1), 300))


if __name__ == "__main__":
    chay(doc_cau_hinh())
