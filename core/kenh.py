"""Sổ đăng ký **kênh** — thứ mà luồng AUTO đọc để biết phải làm ra cái gì.

═══ MỘT KÊNH LÀ MỘT THƯ MỤC ═══

Toàn bộ "tính cách" của một kênh nằm trong `CHANNEL/<mã kênh>/`, không nằm rải
rác trong mã nguồn:

    CHANNEL/TL1-T1/
      kenh.yaml        ai xem, tiếng gì, dài bao nhiêu, giọng nào, engine nào
      style.yaml       nhìn như thế nào — màu, nét vẽ, đạo cụ, bối cảnh văn hoá
      nv/nv1.png       nhân vật tham chiếu; mọi ảnh sinh ra phải giống người này
      prompt/          chuỗi lời nhắc 1→7, chạy lần lượt để ra kịch bản và cảnh

Người dùng thêm kênh mới bằng cách **chép một thư mục rồi sửa chữ trong đó** —
không phải sửa code, không phải nhờ ai. Đó là điều kiện để luồng AUTO thật sự
tự chạy được với 10 kênh chứ không phải một kênh.

═══ TUYỆT ĐỐI KHÔNG CÓ KHOÁ TRONG THƯ MỤC KÊNH ═══

Mấy tool cũ để khoá sống ngay trong tệp cấu hình của từng dự án — khoá router,
khoá tài khoản đọc giọng, cả kho tài khoản. Chép nguyên nết ấy sang đây là một
ngày nào đó người dùng gửi thư mục kênh cho người khác dùng chung và cho luôn
cái ví.

Nên `kiem_kenh()` **quét và từ chối** mọi tệp cấu hình kênh có mùi khoá. Tiền
trong luồng AUTO đi qua đúng một cửa: ví ShopAPI mà tool đã đăng nhập sẵn.

Module thuần tuý: không mạng, không giao diện. Chỉ đọc và kiểm thư mục.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "THU_MUC_KENH", "TEP_KENH", "TEP_STYLE", "BUOC_PROMPT", "nhan_ban_kenh",
    "TEP_CHIEN_LUOC",
    "Kenh", "duong_kenh", "liet_ke_kenh", "doc_kenh", "kiem_kenh",
    "doc_yaml", "co_mui_khoa", "GIU_NGUYEN", "ten_khung",
    "CHE_DO_TIEU_DE", "ten_che_do",
]

#: Thư mục chứa mọi kênh, nằm cạnh `shopapi_studio_qt.py`.
THU_MUC_KENH = "CHANNEL"

TEP_KENH = "kenh.yaml"
TEP_STYLE = "style.yaml"
#: Tệp khai chiến lược, chỉ có ở kênh dựng từ khuôn có chiến lược.
TEP_CHIEN_LUOC = "chien-luoc.yaml"
THU_MUC_NV = "nv"
THU_MUC_PROMPT = "prompt"

#: Chuỗi bước làm kịch bản, chạy **đúng thứ tự này**. Tên tệp bắt đầu bằng số vì
#: người dùng phải nhìn thư mục là biết cái nào chạy trước — họ sẽ sửa mấy tệp
#: này thường xuyên hơn sửa bất cứ thứ gì khác trong tool.
#:
#: Bảy bước chép theo dây chuyền đã chạy thật ở `D:\\CONTENT` (title_thumb →
#: write_oneshot → check_fix → adapt → review → seo), cộng thêm bước 7 mà tool
#: cũ để ở nơi khác: viết lời nhắc tạo ảnh/clip cho từng cảnh.
BUOC_PROMPT = (
    ("1-tieu-de.md", "Đặt tiêu đề và chữ trên ảnh bìa"),
    # Chỉ chiến lược "cover" dùng bước này. Kênh không có tệp thì dây chuyền
    # bỏ qua — cùng nết với mọi bước không bắt buộc khác.
    ("2a-phan-tich.md", "Đọc bản gốc: hay chỗ nào, chưa hay chỗ nào"),
    ("2-viet.md", "Viết kịch bản lời đọc"),
    # Chỉ chạy khi kênh khai `so_ban_nhap` > 1: viết nhiều bản rồi chấm, chọn
    # một. Chủ dự án, 25/08/2026: *"cho nó viết nhiều lần, và chấm điểm các
    # lần tức là chọn bản tốt nhất"*.
    ("2b-cham.md", "Chấm các bản viết, chọn bản tốt nhất"),
    # Chỉ chạy khi kênh bật `hoan_thien`: sửa điểm yếu, phát huy điểm mạnh bộ
    # chấm chỉ ra, làm mượt — rồi bộ chấm so lại, không hơn thì giữ bản chọn.
    ("2c-hoan-thien.md", "Hoàn thiện bản đã chọn: sửa điểm yếu, phát huy điểm mạnh"),
    # Chỉ chạy khi kênh khai `so_ban_hook` > 1: viết riêng vài đoạn mở, chấm
    # theo tiêu chí riêng của hook, rồi thay vào bản đã chọn. Chủ dự án,
    # 04/09/2026: *"bước viết hook sẽ riêng và có tiêu chí chấm riêng"*.
    ("2d-hook.md", "Viết riêng đoạn mở đầu (hook)"),
    ("2e-cham-hook.md", "Chấm các đoạn mở, chọn hook tốt nhất"),
    # Vá hook đã chọn theo đúng lời chê của bộ chấm — chỗ DUY NHẤT hook có thể
    # vượt bản gốc, vì các bản viết ra đều bắt chước hook đối thủ nên thừa
    # hưởng cả điểm yếu của nó.
    ("2f-va-hook.md", "Vá đoạn mở đã chọn theo lời chê"),
    # Chỉ chạy khi kênh khai `so_vong_cham` > 0: chấm bản GHÉP XONG như một
    # bài (bản đồ rớt so với gốc, có bình luận người xem gốc + số giữ chân đã
    # đo của kênh), vá vài bản cùng một lời chê, chấm so, lặp vài vòng. Chủ dự
    # án, 09/09/2026: *"chấm sửa xong chấm lại vài lần cũng được… mục đích cuối
    # ra được content hay khán giả yêu thích và họ xem đến hết"*.
    ("2g-cham-toan-bai.md", "Chấm bản ghép xong như một bài, so với gốc và người xem gốc"),
    ("2h-va-toan-bai.md", "Vá chỗ kém nhất bộ chấm chỉ ra (viết vài bản, chấm so)"),
    ("3-sua.md", "Rà soát: sửa lệch tiếng, tách câu, chèn thẻ"),
    # Chỉ chạy khi kênh khai `so_vong_cham` > 0: một lượt AI nghe lại bản ĐÃ rà
    # soát bằng tai người bản ngữ — rà soát là bước viết cuối, trước đó không ai gác.
    ("2i-kiem-doc.md", "Gác bản đọc: so bản trước/sau rà soát bằng tai người bản ngữ"),
    ("4-do-dai.md", "Nắn cho đúng độ dài"),
    ("5-hoan-thien.md", "Đọc lại lần cuối cho mượt"),
    ("6-seo.md", "Mô tả, hashtag, từ khoá"),
    # Bình luận để GHIM ngay sau khi đăng. Không phải trang trí: đo trên TL4-T7
    # ngày 05/09/2026, kênh có **3 người xem cũ trong 28 ngày** (99% là người
    # mới, không ai quay lại) và video mới nhất không một bình luận nào. Bình
    # luận ghim là chỗ rẻ nhất để mở lời — nhưng chỉ ăn khi nó nhắc lại đúng câu
    # hỏi kịch bản ĐÃ hỏi ở cuối video và tự trả lời trước một câu; câu hỏi ghim
    # mà không ai trả lời thì đọc như một lời nhờ vả.
    ("6b-binh-luan.md", "Bình luận để ghim sau khi đăng"),
    # Bản đồ hình cho CẢ video trước khi chia khúc: chương, bối cảnh, mạch cảm
    # xúc, câu bản lề. Thiếu tệp thì khâu chia cảnh chạy như trước, không có
    # bản đồ (xem `core/auto_khau._ke_hoach_hinh`). Thêm 25/08/2026 sau khi soi
    # 487 cảnh của ba lượt TL4-T7: 9 khúc chia song song không biết nhau nên
    # mỗi 5 giây một ẩn dụ rời, cả video không có chương, không có chỗ đổi bối
    # cảnh — thứ giữ chân người xem video dài.
    ("7-ke-hoach.md", "Bản đồ hình cho cả video: chương, bối cảnh, câu bản lề"),
    ("7-canh.md", "Chia cảnh theo nghĩa, viết lời nhắc ảnh và clip"),
    ("8-thumbnail.md", "Viết lời nhắc ba ảnh bìa"),
    ("9-nhac.md", "Viết lời nhắc nhạc nền"),
)

#: Bước bắt buộc phải có thì luồng AUTO mới chạy nổi. Bước 6 (SEO) thiếu thì vẫn
#: ra được video, chỉ là không có sẵn phần mô tả để dán lên YouTube.
BUOC_BAT_BUOC = ("2-viet.md", "7-canh.md")


@dataclass
class Kenh:
    """Một kênh đã đọc xong từ đĩa."""

    ma: str = ""
    ten: str = ""
    #: Mã ngôn ngữ ISO ngắn: `es`, `vi`, `en`…
    ngon_ngu: str = ""
    #: Tên ngôn ngữ viết cho AI đọc: "Spanish — natural, second person (tú)".
    giong_van: str = ""
    #: Độ dài video nhắm tới, tính bằng phút.
    phut_muc_tieu: float = 10.0
    #: Số ký tự đọc được trong một phút của tiếng này. Dùng để quy phút → ký tự
    #: cho bước nắn độ dài. Đo từ giọng thật, không đoán.
    ky_tu_moi_phut: int = 900
    #: Lệch bao nhiêu thì mới gọi bước nắn độ dài. 0 = lấy `CHENH_CHO_PHEP`.
    #:
    #: Mỗi kênh chịu được một mức khác nhau, và đó là quyết định của người làm
    #: kênh chứ không phải một hằng số chung. TL4-T7 khai 0,30 — chủ dự án,
    #: 04/09/2026: *"về độ dài tao không quá quan trọng trong khoảng từ 10-15
    #: phút"*; và đo bốn lượt thật thì bước viết đã tự về đích, bước nắn không
    #: phải chạy lần nào.
    chenh_cho_phep: float = 0.0
    #: Bám độ dài THEO VIDEO GỐC thay vì theo `phut_muc_tieu`.
    #:
    #: Kênh remake kiểu "gần như giống đối thủ nhất" muốn video dài đúng bằng
    #: video đối thủ, không phải một con số phút cố định. Bật cờ này thì mục tiêu
    #: độ dài của bước viết = số ký tự tư liệu đối thủ (`CHARS_GOC`), và chốt
    #: chặn "kịch bản quá ngắn" cũng đo theo bản gốc chứ không theo 20 phút.
    #:
    #: `phut_muc_tieu` khi ấy không còn dẫn dắt độ dài — để nguyên cũng được.
    #: Thường đi kèm việc BỎ `prompt/4-do-dai.md` để không nắn về mốc cố định.
    do_dai_theo_goc: bool = False
    #: Bước viết viết mấy bản rồi chấm chọn một. 1 = viết một bản, không chấm
    #: (mặc định — khách đi ví thì mỗi bản là một lượt trừ tiền). Kênh chạy
    #: bằng thuê bao Claude đặt 3: ba bản + một lượt chấm, không tốn thêm gì.
    #: Cần thêm `prompt/2b-cham.md`; thiếu tệp ấy thì chọn theo số đo (độ dài,
    #: mức trùng nguyên văn).
    so_ban_nhap: int = 1
    #: ═══ VIẾT RIÊNG ĐOẠN MỞ ĐẦU (HOOK), CHỌN LỌC RIÊNG ═══
    #:
    #: Chủ dự án, 04/09/2026: *"bước viết hook sẽ riêng và có tiêu chí chấm
    #: riêng cũng viết hook vài lần để chọn bản ok"*. Lý do đo được: mở đầu là
    #: chỗ rớt nhiều nhất, mà bộ chấm cả bài chấm 60 giây đầu chung với thân
    #: bài nên một bản mở sai kiểu vẫn thắng nhờ thân bài tốt.
    #:
    #: Bước này chạy SAU khi đã chọn bản cả bài: viết `so_ban_hook` đoạn mở
    #: bằng `prompt/2d-hook.md`, chấm bằng `prompt/2e-cham-hook.md`, rồi THAY
    #: đoạn mở cũ. 0 hoặc 1 = tắt. Thiếu một trong hai tệp lời nhắc cũng tắt.
    so_ban_hook: int = 0
    #: Cách kể bằng hình cho khâu bảng cảnh + ảnh (chủ dự án 25/08/2026, kênh
    #: truyện cổ tích): "" / "mot_nhan_vat" = đường cũ (một nhân vật cố định
    #: `nv1.png`, lời nhắc `7-canh.md`); "tu_xay" = AI đọc phim, tự dựng dàn
    #: nhân vật (có giai đoạn trang phục) + bối cảnh, kế hoạch đạo diễn, ảnh
    #: tham chiếu từng nhân vật — cùng dây chuyền với tab Prompt Visuals;
    #: "nhan_vat_va_boi_canh" = như tu_xay nhưng giữ `nv1.png` của kênh làm
    #: nhân vật chính. Kênh không khai khoá này đi đúng đường cũ.
    che_do_ke: str = ""
    #: ĐỘ DÀI TỰ DO: không nhắm phút, không nắn, không chấm độ dài — bài dài
    #: ngắn theo câu chuyện. Chủ dự án 25/08/2026 cho kênh truyện cổ tích:
    #: *"không cần giới hạn thời gian hay ký tự ở prompt"*. Chỉ còn một sàn
    #: tuyệt đối chống bản rỗng / AI hỏi lại (`SAN_KICH_BAN_TU_DO`).
    do_dai_tu_do: bool = False
    #: Chế độ nối cảnh gửi clip với `frame_mode: start_frame` — khung hình đầu clip
    #: CHÍNH LÀ ảnh gửi (Flow "Frames"), thay vì Veo tự dựng lại bố cục. Cần cổng
    #: ShopAPI đã nhận trường này (26/08/2026). Bật thì clip nối vào khung cuối
    #: clip trước không khựng, và diễn tiếp video→video được với cả Veo 3.
    khung_dau: bool = False
    #: Chấm từng tấm ảnh với ảnh tham chiếu, lệch quá thì vẽ thêm và giữ tấm
    #: hơn (`auto_khau._cham_va_ve_lai`). Mặc định TẮT: mỗi lượt chấm là một
    #: lời gọi chữ, mỗi lần vẽ lại là một tấm ảnh — kênh của khách không tự
    #: dưng đắt lên.
    cham_anh: bool = False
    #: Vẽ thêm một tấm ảnh KHUNG CUỐI cho mỗi cảnh rồi ghim clip CẢ HAI đầu
    #: (`auto_khau._anh_khung_cuoi`). Tốn thêm một tấm ảnh mỗi cảnh, đổi lại
    #: đuôi clip không trôi — đo 27/08/2026: cảnh 11 đi 2 → 4 điểm, cảnh 2 đi
    #: 3 → 4. Mặc định TẮT.
    ghim_hai_dau: bool = False
    #: "tên 1 | tên 2 | …" — danh sách phát thật của kênh; rỗng = hành vi cũ.
    danh_sach_phat_kenh: str = ""
    #: Sau khi dựng xong `8-video.mp4`: đưa video vào CapCut (bản máy tính,
    #: phải cài sẵn) rồi TỰ BẤM Xuất, ra thêm `9-video-capcut.mp4` — video
    #: được chính CapCut mã hoá lại. Chủ dự án 28/08/2026: *"video sau khi
    #: xong tao còn cho vào capcut"*; 02/09/2026 muốn bước ấy tự động. Chạy
    #: trên máy, miễn phí, nhưng CapCut sẽ tự mở tự bấm trên màn hình — nên
    #: mặc định TẮT, chỉ bật cho kênh nào chủ ý dùng. Xem `core/capcut.py`.
    xuat_capcut: bool = False
    #: Nghỉ mấy giây giữa hai PHẦN của kịch bản (dòng `---` trong bản đọc).
    #:
    #: Khoảng lặng THẬT, chèn lúc ghép tiếng — không phải thẻ `[long pause]`,
    #: thứ mà nhà máy giọng nói lúc nghe lúc không. Khán giả có chỗ chuyển
    #: mình giữa các phần, người dựng nhìn sóng âm là thấy ngay chỗ cắt.
    #: 0 = không nghỉ, chạy y như trước.
    giay_nghi_phan: float = 1.2
    #: Sau khi chấm chọn bản, HOÀN THIỆN chính bản đó theo nhận xét của bộ
    #: chấm: sửa điểm yếu, phát huy điểm mạnh, làm mượt (`prompt/2c-hoan-thien.md`,
    #: hai lượt gọi nữa: hoàn thiện + chấm so lại). Chủ dự án, 25/08/2026:
    #: *"chỉnh lại bài đó để hoàn thiện các điểm yếu và nổi bật phát huy điểm
    #: tốt, làm mượt lại"*. Tắt sẵn — khách đi ví thì đó là hai lượt chữ nữa;
    #: kênh chạy thuê bao bật lên không tốn gì. Khoá cũ `va_cho_rot` trong
    #: kenh.yaml vẫn được đọc như cờ này.
    hoan_thien: bool = False
    #: ═══ VÒNG CHẤM TOÀN BÀI → VÁ → CHẤM SO (`core/vong_cham_sua.py`) ═══
    #:
    #: Số vòng tối đa chấm bản GHÉP XONG rồi vá chỗ kém nhất. 0 = tắt (mặc
    #: định — mỗi vòng là ~3 lượt chữ). Cần `prompt/2g-cham-toan-bai.md` và
    #: `2h-va-toan-bai.md`; thiếu một tệp thì tắt. Kênh thuê bao đặt 3.
    so_vong_cham: int = 0
    #: Mỗi vòng vá mấy bản rồi chấm so — "làm nhiều rồi chọn", không sửa một
    #: lần rồi tin. 2 là đủ để có cái mà chọn.
    so_ban_va: int = 2
    #: ═══ KÊNH MẪU CỦA TOOL hay KÊNH RIÊNG CỦA KHÁCH ═══
    #:
    #: Chủ dự án, 26/08/2026: *"các template đó tao có cập nhật nên nếu khách
    #: dùng và tùy chỉnh thì khi update sẽ bị đè, nên tao muốn những template
    #: khách tạo sẽ không bị đè"*. Hai cờ, mỗi cờ một việc:
    #:
    #: * `mau_cua_tool: true` — kênh mẫu ship kèm tool. Cập nhật tool **ghi
    #:   đè** nó (để khách nhận bản mẫu mới hơn). Giao diện gắn nhãn "mẫu" và
    #:   mời Nhân bản trước khi sửa.
    #: * `kenh_rieng: true` — kênh khách tạo (Tạo kênh mới) hoặc nhân bản từ
    #:   mẫu. Cập nhật tool **không bao giờ** đụng vào (`core/safe_update`).
    #:
    #: Kênh cũ không có cờ nào (tạo trước 26/08/2026): không phải mẫu, và vì
    #: bản mới không mang theo thư mục cùng tên nên cập nhật cũng không đụng.
    mau_cua_tool: bool = False
    kenh_rieng: bool = False
    #: Chế độ đặt TIÊU ĐỀ và CHỮ BÌA — bám bản gốc hay đặt lại theo chất kênh.
    #:
    #: `"faithful"` (mặc định) — bám sát tiêu đề đối thủ, chỉ dịch và bản địa
    #: hoá, giữ nguyên lời hứa/mồi tò mò. Nết cũ của mọi kênh trước đây.
    #: `"restyled"` — viết lại tiêu đề theo giọng riêng của kênh, chỉ giữ lõi
    #: lời hứa. Dành cho kênh có bản sắc riêng, không cố giống đối thủ.
    #: `"nguyen_goc"` — LẤY NGUYÊN tiêu đề đối thủ, và ĐỌC chữ trên ảnh bìa đối
    #: thủ làm chữ bìa. Không gọi AI viết lại — bỏ hẳn lượt gọi ấy. Dành cho kênh
    #: remake "gần như giống đối thủ nhất". Đọc ảnh bìa hỏng thì chữ bìa lấy
    #: đúng tiêu đề đối thủ (đường lui, không bao giờ làm vỡ lượt chạy).
    #:
    #: Lời nhắc `prompt/1-tieu-de.md` VỐN đã có sẵn hai nhánh `faithful`/
    #: `restyled` qua ô `<<MODE>>`; hai giá trị ấy chỉ chọn nhánh nào được điền
    #: vào. Trước đây luồng AUTO đóng cứng `faithful`, nên nhánh `restyled` viết
    #: trong lời nhắc chưa bao giờ chạy — cờ này mở nó ra mà không đụng nội dung
    #: lời nhắc. Riêng `nguyen_goc` KHÔNG chạy lời nhắc này.
    che_do_tieu_de: str = "faithful"
    #: Nhãn thể loại 【...】 kênh muốn thấy ở ĐẦU tiêu đề khi dùng `nguyen_goc`. Rỗng (mặc định) = không
    #: đụng gì — nết cũ.
    #:
    #: Chủ dự án, 18/09/2026: video 13 lấy nguyên tiêu đề đối thủ 【雑学】昔より物欲が減った人の心理, nhưng
    #: 【雑学】 là nhãn của KÊNH NGUỒN, không phải của kênh mình. Tra thật bằng yt-dlp trên kênh sống: 9/12
    #: video đã đăng có nhãn khoa học tâm lý/não bộ ở đầu, và cả năm video gần nhất theo Công thức V7
    #: (V8–V12) đều có. `nguyen_goc` giữ NGUYÊN phần nội dung (đã chứng minh có người bấm) nhưng nhãn đầu
    #: là chuyện "cửa hàng nào khán giả quen bước vào" — chuyện của kênh nhận, không phải kênh nguồn.
    nhan_tieu_de: str = ""
    #: `nguyen_goc`: sau khi gỡ chữ ký kênh nguồn, nhờ AI NẮN VỎ CÂU về khuôn tiêu đề đang thắng
    #: của chính kênh (mẫu đọc từ `chi-so/`, không viết cứng). Luận điểm giữ nguyên.
    #:
    #: Chủ dự án, 21/09/2026: *"không lấy 100% được vì from đang win của kênh mình nó hơi khác với
    #: kênh khác"*. Đúng — nguồn của V10/V11/V12 đến từ ひととき心理学・心理ラボ・心理学のおやつ, vốn
    #: viết cùng khuôn nên bê nguyên được; còn các nguồn mới để nhãn ở cuối câu, kèm hashtag và
    #: tên kênh họ. Tắt (mặc định) thì hành vi y như cũ: chỉ chuẩn hoá nhãn đầu.
    nan_khuon_tieu_de: bool = False
    #: ═══ VIỆC 5 — N BẢN TIÊU ĐỀ + CHẤM THEO CTR THẬT (`core/auto_khau.py`, nhánh
    #: `nguyen_goc`, 29/09/2026, `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`) ═══
    #:
    #: >0 thì ngoài "đối chứng" (tiêu đề nguồn đã gỡ chữ ký) và bản nắn khuôn (nếu
    #: `nan_khuon_tieu_de` bật), tool còn xin thêm NGẦN NÀY cách đặt tên khác trong
    #: MỘT lượt gọi ngắn, rồi CHẤM cả rổ ứng viên qua `viet_nhieu_ban.cham_va_chon`
    #: với khuôn có bảng CTR THẬT của kênh (+ nhóm) — thay vì lấy đúng một bản mù
    #: như trước. 0 = tắt hẳn, giữ nết cũ (chỉ đối chứng/nắn khuôn đơn, không chấm
    #: nhiều bản, không ghi `1-tieu-de-cham.json`). Mặc định BẬT (4 bản) — cùng
    #: triết lý "cờ tắt theo kênh trong kenh.yaml, mặc định bật" của cả bản thiết
    #: kế (đầu tệp `THIET-KE-DUNG-VA-VONG-HOC.md`).
    so_tieu_de: int = 4
    #: Mã giọng đọc trên cổng ShopAPI.
    voice_id: str = ""
    #: Engine dựng clip — quyết định trần độ dài mỗi cảnh (veo3 8s, seedance 10s).
    engine: str = "veo3"
    #: Mô hình AI viết kịch bản và lời nhắc.
    mo_hinh: str = "claude-sonnet-5"
    #: Chữ hoa cho chữ trên ảnh bìa hay không. Tiếng Nhật/Hàn không có chữ hoa
    #: nên kênh tiếng ấy phải để `false`, viết hoa là ra chữ hỏng.
    chu_bia_hoa: bool = True
    #: Số ảnh bìa sinh ra để người dùng chọn. Tool cũ làm 3 bản khác kiểu nhau
    #: (chân dung, cảnh kịch tính…) rồi người chọn tay — giữ nguyên nết đó.
    so_thumbnail: int = 3

    # ── Cách dựng video, cài một lần cho cả kênh ─────────────────────────────
    #
    # Chủ dự án, 14/08/2026: *"các vấn đề về edit có thể có template"*.
    #
    # Đây là những thứ mọi video của một kênh làm giống hệt nhau, nên hỏi từng
    # lượt là hỏi thừa. Cài ở kênh một lần rồi thôi.

    #: Đốt phụ đề thẳng vào hình hay không.
    #:
    #: `True` hợp với kênh đăng lên Facebook/TikTok — chỗ người xem tắt tiếng
    #: và phụ đề rời không hiện. `False` hợp với kênh chỉ đăng YouTube: tải tệp
    #: `.srt` lên riêng thì người xem bật/tắt được, đổi cỡ chữ được, và YouTube
    #: đọc được nội dung để đề xuất video — chữ đốt vào hình thì nó mù.
    dot_phu_de: bool = True

    #: Giữ lại TIẾNG CẢNH của từng clip (tiếng bước chân, chim hót, nước, gió).
    #:
    #: ═══ VÌ SAO CÓ Ô NÀY ═══
    #:
    #: Khâu dựng vốn vứt sạch tiếng của clip (`-an` lúc cắt) và chỉ giữ giọng
    #: đọc. Chủ dự án 28/08/2026: *"những âm thanh không phải người nói có thể
    #: giữ lại được không — kiểu nó sẽ làm cho video sinh động hơn… bỏ nhạc nền
    #: của video gốc và âm thanh người nói, giữ các âm thanh phụ (ví dụ tiếng
    #: bước chân, chim hót…)"*.
    #:
    #: Không tách được nhạc/lời ra khỏi tiếng động sau khi engine đã trộn. Nên
    #: chặn ở ĐẦU VÀO: bật ô này thì khâu clip ghim thêm một câu bắt engine chỉ
    #: làm tiếng nền và tiếng động, cấm nhạc và cấm mọi lời nói
    #: (`core/auto_khau.LUAT_TIENG_CANH`). Đo trên phim `openstory/0008`: lời
    #: nhắc do AI viết có `ambient:`/`sfx:` ở 25/30 cảnh nhưng **0/30** cảnh
    #: nhắc "no music, no speech" — nên câu ấy phải do tool ghim, không trông
    #: vào AI nhớ.
    #:
    #: Khâu dựng còn xuất riêng `8-tieng-canh.m4a` để mang sang CapCut trộn
    #: tay: khách dựng lại ở đó thì cần đường tiếng rời, không cần bản đã trộn.
    giu_tieng_canh: bool = False

    #: Độ to tiếng cảnh trong `8-video.mp4`, lúc KHÔNG có giọng đọc.
    #:
    #: Chủ dự án 28/08/2026: *"cái âm thanh video thì cần bé hơn, vì bản chất
    #: là có lồng voice — nếu âm thanh phụ to quá thì nó bị lấn mất voice; và
    #: đôi khi nó có nhạc nền nên nếu bé hơn chút sẽ không bị át nhạc nền sau
    #: thêm vào"*.
    #:
    #: Đo trên phim `openstory/0008` mới thấy vì sao 0,7 lấn: tiếng cảnh có
    #: **trung bình** rất nhỏ (-31,3 dB) nhưng **đỉnh** ngang hẳn giọng đọc
    #: (-1,6 dB so với -1,4 dB) — một tiếng nước bắn, một tiếng gỗ va là vọt
    #: lên bằng lời kể. Nên phải nhìn đỉnh, không nhìn trung bình.
    #:
    #: 0,35 (bằng nửa mức cũ, tức -9 dB) đưa đỉnh tiếng cảnh xuống -10,7 dB,
    #: thấp hơn đỉnh giọng đọc 9,3 dB, và chừa chỗ cho nhạc nền khách tự chèn ở
    #: CapCut sau này.
    #:
    #: ⚠ Ô này chỉ đổi bản đã trộn. Tệp `8-tieng-canh.m4a` xuất riêng luôn giữ
    #: **mức gốc** — khách chỉnh to nhỏ ở CapCut, đưa cho họ bản đã hạ sẵn là
    #: lấy mất quyền ấy.
    am_luong_tieng_canh: float = 0.35

    #: Ngưỡng nhận ra tiếng người trong clip — trên mức này thì tắt tiếng clip.
    #:
    #: Mặc định 0 nghĩa là *dùng ngưỡng chung* `tieng_canh.NGUONG_TIENG_NGUOI`
    #: (0,25), chỗ có khoảng trống đo được giữa ồn nền và tiếng nói.
    #:
    #: Có ô riêng vì phép đo bám **nhịp âm tiết 3–6 Hz**, mà không phải kênh
    #: nào cũng chỉ có tiếng nói rơi vào nhịp ấy. Phiên `kho-github-77` nêu ca
    #: thật 28/08/2026: kênh timelapse có tiếng chợ đông và tiếng người hò hét
    #: lúc cháy — tiếng đám đông cũng dồn vào 300–3400 Hz và cũng dập dình, nên
    #: có thể bị bắt oan. Kênh ấy nâng ngưỡng của mình lên là xong, không phải
    #: lung lay ngưỡng chung vốn có khoảng trống thật đỡ lưng.
    nguong_tieng_nguoi: float = 0.0

    #: Độ phân giải video ra: `"Giữ nguyên"`, `"1080p"`, `"1440p"` hay `"4K"`.
    #:
    #: ═══ VÌ SAO PHẢI CÓ Ô NÀY ═══
    #:
    #: Đường dựng của tab Tự động trước đây **không có bước đổi độ phân giải
    #: nào**, nên video ra đúng bằng độ phân giải nhà cung cấp trả về. Đo
    #: 16/08/2026 trên bảy lượt thật: mọi clip và mọi video đều **1280×720** —
    #: chưa tới 1080p, trong khi khách vẫn tải lên YouTube như video thường.
    #:
    #: `videos.create` không có tham số xin bản to hơn, nên chỗ duy nhất nắn
    #: được là lúc mã hoá lần cuối.
    #:
    #: ═══ NÓI THẬT VỀ CÁI ĐƯỢC ═══
    #:
    #: Phóng 720p lên 4K **không tạo thêm chi tiết thật** — phần nét thêm ra là
    #: máy đoán. Cái được thật nằm ở chỗ khác: YouTube cấp bộ mã hoá tốt hơn
    #: cho video tải lên ở 2160p, nên người xem ở 1080p vẫn thấy sạch hơn.
    #: Đó là hành vi YouTube có quyền đổi bất cứ lúc nào.
    #:
    #: **Rỗng là mặc định**, nghĩa là *"lấy theo cài đặt chung của tool"*
    #: (`core/cai_dat.py`, khoá `do_phan_giai`, đang để `"1080p"`). Khai ở đây chỉ
    #: khi kênh này cần khác cả nhà — ví dụ kênh làm nhanh lấy số lượng thì để
    #: `"Giữ nguyên"` cho khâu dựng đỡ lâu.
    do_phan_giai: str = ""

    #: Tệp nhạc nền, đường dẫn tính từ thư mục kênh (ví dụ `nhac/nen.mp3`).
    #:
    #: Rỗng = không có nhạc. Cổng ShopAPI **không bán nhạc**, nên đây phải là
    #: tệp khách tự có — mua, tải từ kho miễn phí bản quyền, hoặc tự làm. Tool
    #: không đi tải nhạc ở đâu về hộ: nhạc dính bản quyền là kênh ăn gậy, và
    #: đó là thứ tool không được phép quyết thay người.
    nhac_nen: str = ""

    #: Nhạc nhỏ hơn giọng đọc bao nhiêu lần. 0.12 = nhạc còn 12% độ to.
    #:
    #: ═══ CHỈ CÒN DÙNG CHO ĐƯỜNG LUI ═══
    #:
    #: Từ 16/08/2026 nhạc **tự lùi khi có giọng đọc và tự lên lại khi giọng
    #: ngừng** (`core/tron_tieng.py`), nên độ to nhạc lúc không có lời lấy theo
    #: `tron_tieng.AM_LUONG_NE` chứ không lấy theo số này nữa.
    #:
    #: Số này chỉ còn được dùng khi bản FFmpeg trong máy thiếu bộ lọc
    #: `sidechaincompress` và phải quay về cách cũ — hạ nhạc đều suốt cả video.
    #: Với cách cũ thì 0.12 vẫn đúng, và lý do cũ vẫn đúng: nhạc để **lấp
    #: khoảng lặng**, không để nghe. To hơn 0.2 là người xem phải căng tai nghe
    #: lời, vì hạ đều thì nhạc không biết đường tránh chỗ nào.
    am_luong_nhac: float = 0.12

    # ── Dựng theo PHẦN (Việc 2, `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`) ────
    #
    # Chủ kênh 28/09/2026: mỗi phần (chương) có hiệu ứng chuyển + nghỉ 3 giây
    # trước khi sang phần mới; mỗi phần một nhạc nền cố định −18 dB dưới
    # giọng, phần dài thì ghép 2–3 bài mượt; sang phần mới đổi nhạc, im ~2s.
    # Trước đó họ sửa TAY mọi video bằng CapCut. Xem `core/phan_video.py`.
    #
    # Mặc định BẬT (quyết định 10: "cờ 0₫ bật") — trừ `ngat_phan_tu_dong`, cờ
    # duy nhất tốn một lượt gọi chữ. Kênh không có giọng đọc (timelapse) thì
    # khâu dựng tự bỏ qua; kho nhạc trống thì dựng không nhạc.

    #: Khoảng nghỉ giữa hai phần TRONG VIDEO (giây). Giọng nghỉ ngắn hơn (lượt
    #: cũ 1,2s) thì khâu dựng tự chèn thêm lặng cho đủ. 0 = tắt cả việc dựng
    #: theo phần, dựng y như trước.
    giay_nghi_chuyen_phan: float = 3.0
    #: Hiệu ứng chuyển phần: `"den"` (tối dần rồi sáng dần), `"trang"`,
    #: `"khong"` (chỉ nghỉ + đổi nhạc, không hiệu ứng hình).
    chuyen_phan: str = "den"
    #: Mỗi chiều mờ dài bấy nhiêu giây.
    giay_chuyen_phan: float = 1.0
    #: Chọn nhạc nền theo từng phần từ kho nhạc chuẩn hoá (`core/kho_nhac.py`).
    #: Kênh đã khai `nhac_nen` (một tệp cố định) thì cờ này không có tác dụng.
    nhac_theo_phan: bool = True
    #: Thư mục nhạc THÔ (chỉ đọc), tính từ gốc tool; bản chuẩn hoá nằm ở
    #: `workspace/kho-nhac/`.
    kho_nhac: str = "PROJECTS/music"
    #: Nhạc nhỏ hơn giọng đọc bao nhiêu dB (CapCut chủ kênh: −18).
    nhac_duoi_giong_db: float = 18.0
    #: Nhạc im bấy nhiêu giây trong khoảng nghỉ giữa hai phần.
    nhac_nghi_giua_phan: float = 2.0
    #: Phần dài hơn một bài thì nối bài kế, hoà tiếng bấy nhiêu giây.
    nhac_noi_bai_giay: float = 4.0
    #: Bài ≥6 phút mà < 3 phần (thiếu dòng `---`) thì một lượt gọi chữ ngắn xin
    #: AI chèn dấu ngắt, không đổi chữ nào (lệch một chữ là vứt). Mặc định tắt
    #: vì tốn tiền; kênh tự chạy bật.
    ngat_phan_tu_dong: bool = False
    #: Dựng MỘT LẦN NÉN (30/09/2026): không ghi bản cắt trung gian `crf 14`,
    #: từng clip giải mã thẳng vào lượt nén cuối — xem `auto_khau._chay_ong`.
    #: Mặc định tắt; hỏng thì tự lùi về đường cũ ngay trong lượt.
    dung_mot_lan: bool = False

    #: ═══ VÒNG HỌC TRƯỚC MỖI LƯỢT (`core/vong_hoc.py`, Việc 3, 28/09/2026) ═══
    #:
    #: Bật thì `tu_chay._chay_mot_ngay_trong_khoa` gọi `vong_hoc.truoc_luot(...)`
    #: làm bước "0) Học từ số liệu" NGAY TRƯỚC "1) Nghiên cứu": chuẩn hoá kho
    #: nhạc, bù/cập nhật hồ sơ video (`CHANNEL/<kênh>/ho-so-video/`) + nối số
    #: liệu Studio thật, rồi rút bài học sản xuất (debounce). Bốn bước đều
    #: 0₫ (trừ khi Việc 4 — khuôn ảnh bìa thắng — bật thêm một lượt mô tả ảnh),
    #: mỗi bước tự `try/except` riêng — KHÔNG BAO GIỜ chặn sản xuất/chặn đăng,
    #: hỏng bước nào chỉ ghi log rồi bỏ qua đúng bước đó. Mặc định BẬT (quyết
    #: định 10 bản thiết kế: "cờ 0₫ bật").
    vong_hoc: bool = True

    #: ═══ VIỆC 4 — CHỌN ẢNH BÌA BẰNG AI (`core/khuon_bia.py`, `core/chon_bia.py`, 28/09/2026) ═══
    #:
    #: Bật thì khâu ảnh bìa (`auto_khau._khau_thumbnail`) gọi thêm `chon_bia.chon(...)`
    #: NGAY SAU khi đã sinh đủ `so_thumbnail` tấm: giám khảo AI NHÌN ẢNH chấm
    #: từng tấm rồi xuất `7-thumbnail/CHON-thumb_00N.jpg` —
    #: `ban_giao_dang._tim_thumb` đã ưu tiên tệp `CHON-*` từ trước. Mặc định
    #: BẰNG CHÍNH `tu_chay` của kênh (quyết định 10 bản thiết kế): kênh chạy tự
    #: động không người trông thì bật kèm luôn (chi phí rất nhỏ, xem mục 4 bản
    #: thiết kế), kênh chạy tay/đang thử thì tắt để không phát sinh chi phí bất
    #: ngờ giữa lúc thử nghiệm. Không khai trong `kenh.yaml` = lấy đúng giá trị
    #: `tu_chay`; khai tường minh thì làm chủ hẳn cờ này.
    chon_bia_ai: bool = False
    #: Chấm mỗi ảnh mấy LƯỢT — thứ tự A-G ĐẢO LẠI ở mỗi lượt rồi lấy trung bình,
    #: giảm may rủi một lượt chấm lệch vì vị trí. 2 là đủ để trung bình còn rẻ.
    so_luot_cham_bia: int = 2
    #: Mô hình riêng cho lượt chấm ảnh bìa. Rỗng (mặc định) = dùng `mo_hinh` của kênh.
    mo_hinh_cham_bia: str = ""
    #: Thêm kiểu ảnh bìa thứ 7 `khuon_thang` — dựng lại đúng BỐ CỤC của ảnh bìa
    #: đang có CTR cao nhất của kênh (hoặc của NHÓM khi kênh chưa đủ mẫu, xem
    #: `khuon_bia.tim_video_thang`). Tắt thì `KIEU_THUMB` vẫn còn 7 phần tử
    #: (mã không đổi thứ tự bao giờ) nhưng tấm thứ 7 không được sinh trừ khi
    #: `so_thumbnail` cũng đủ 7.
    bia_khuon_thang: bool = True
    #: Giám khảo được phép CHỌN một tấm không phải hạng nhất khi nó thuộc kiểu
    #: ÍT DÙNG hơn trong 10 hồ sơ gần nhất và điểm không kém hạng nhất quá 3% —
    #: tránh cả kênh dồn mãi về đúng một kiểu thắng đầu tiên.
    bia_kham_pha: bool = True
    #: Cho phép MƯỢN khuôn ảnh bìa thắng của kênh KHÁC cùng nhóm khi chính kênh
    #: chưa đủ mẫu riêng (`khuon_bia.tim_video_thang`). MẶC ĐỊNH TẮT (30/09/2026,
    #: Việc 4b) — mỗi kênh có tệp khán giả riêng, khuôn thắng của kênh khác không
    #: chắc đúng gu khán giả kênh này; kênh chưa đủ dữ liệu thì THĂM DÒ CÓ CHỦ ĐÍCH
    #: (`bia_kham_pha`) thay vì giả vờ đã có khuôn. Bật lại (true) cho máy nào
    #: muốn dùng chung khuôn nhóm như cũ.
    bia_khuon_nhom: bool = False

    #: ═══ VIỆC 5b — KIỂM TRÙNG Ý BẰNG LLM (`core/kiem_trung_y.py`, 29/09/2026) ═══
    #:
    #: `core/trung_tieu_de.py` so CHỮ (`SequenceMatcher`, ngưỡng 0,80) — bắt tốt ca
    #: chép gần nguyên văn nhưng bỏ lọt ca CÙNG Ý KHÁC DIỄN ĐẠT (ca thật: ứng viên
    #: một tiêu đề đối thủ cùng cụm IQ so với tiêu đề TL3-T7-0001
    #: đã làm 「考えすぎる人の頭の中はこんな世界」 chỉ đạt điểm chữ 0,485 — đảo trật tự
    #: 「IQが低い」/「低IQ」 khiến so THEO KÝ TỰ chấm thấp dù CÙNG chủ đề "IQ thấp").
    #:
    #: Bật thì NGAY TRƯỚC KHI CHỐT nguồn (`tu_chay._chon_nguon`, dùng chung cho cả
    #: nhánh Công thức V7 lẫn nhánh "Một nút"), ứng viên đứng đầu bảng được hỏi
    #: thêm MỘT lượt AI ngắn: "có CÙNG CHỦ ĐỀ/LUẬN ĐIỂM với video nào kênh đã làm
    #: không" (khác góc nhìn rõ ràng thì KHÔNG tính trùng) — trùng thì loại, thử
    #: ứng viên kế, tối đa 3 lượt gọi AI cho MỖI lượt chọn nguồn. LLM lỗi (mạng,
    #: JSON sai dạng…) → bỏ qua lớp này, không chặn chọn nguồn.
    #:
    #: `che_do="thu"` (chạy thử, xem `tu_chay.chay_mot_ngay`) KHÔNG BAO GIỜ gọi lớp
    #: này — lời hứa "chọn nguồn không tốn một đồng nào" của chế độ thử đứng trước;
    #: xem cách `_chay_mot_ngay_trong_khoa` chỉ đưa `goi_chat` thật khi `che_do ==
    #: "that"`. Mặc định BẬT — chi phí chỉ 1-3 lượt chữ ngắn mỗi lượt chọn nguồn.
    kiem_trung_y: bool = True

    # ── Kênh tự chạy (không người trông, `core/tu_chay.py`) ──────────────────
    #
    # Một kênh chạy trên VPS, một lượt một ngày, không ai ngồi bấm gì. Các
    # khoá dưới đây chỉ có tác dụng khi đọc qua `core/tu_chay.py` — tab Tự
    # động (chạy tay, có người ngồi xem) không đụng tới chúng.

    #: Bật thì kênh này nằm trong `tu_chay.kenh_tu_chay()` — CLI
    #: `python tu_chay.py --tat-ca` chạy nó mỗi ngày. Tắt (mặc định) = kênh
    #: vẫn chạy tay như trước, `tu_chay.py` bỏ qua hẳn.
    tu_chay: bool = False
    #: Tự điền ngày giờ đăng vào `ke-hoach-dang/ke-hoach.csv` ngay sau khi bàn
    #: giao — máy ảo đăng đúng giờ đó, KHÔNG CẦN AI DUYỆT LẠI. Tắt (mặc định)
    #: = ngày giờ để TRỐNG, chính bạn gõ tay vào bảng kế hoạch khi ưng — van an
    #: toàn cho người mới bật `tu_chay` mà chưa tin tool hoàn toàn.
    tu_duyet: bool = False
    #: Giờ đăng cố định mỗi ngày khi `tu_duyet: true`, dạng `"HH:MM"` (ví dụ
    #: `"20:00"`). Rỗng = không tự đặt được dù `tu_duyet` có bật.
    gio_dang: str = ""
    #: Trần chi tiêu MỘT NGÀY của kênh này, tính bằng ĐỒNG. 0 = chưa khai —
    #: `tu_chay.py` ở chế độ thật (`--thu` tắt) SẼ TỪ CHỐI sản xuất khi trần
    #: bằng 0: chạy không người trông mà không có trần là tiêu tiền không giới hạn.
    ngan_sach_ngay: int = 0
    #: Thư mục `done` mà máy ảo nhìn thấy qua ổ chia sẻ (xem
    #: `core/ban_giao_dang.py`) — nơi tool chép gói mp4+srt+ảnh bìa sau khi
    #: sản xuất xong. Rỗng = sản xuất xong nhưng KHÔNG bàn giao; tool nói rõ lý
    #: do trong báo cáo chứ không lặng lẽ bỏ qua.
    thu_muc_done: str = ""
    #: Số video một ngày. 1 (mặc định) — `tu_chay.py` không tạo quá số này
    #: trong một ngày cho một kênh, dù gọi lại nhiều lần trong ngày.
    video_moi_ngay: int = 1
    #: Nhịp đăng của kênh. 2 = mỗi hai ngày mới cần một video. Vòng tự chạy
    #: dựa vào lần đăng thật gần nhất để không sản xuất tích kho.
    chu_ky_dang_ngay: int = 1
    #: Chỉ chốt nguồn và sản xuất khi còn không quá ngần này giờ tới lịch đăng
    #: kế tiếp. 0 = tắt van thời gian để giữ tương thích cho kênh cũ.
    san_xuat_truoc_gio: int = 0
    #: Gói "Sẵn sàng" mà CHƯA đăng quá ngần này NGÀY thì KHÔNG còn tính là gói
    #: CHẶN cửa sản xuất (`core.tu_chay._cua_so_san_xuat`) nữa.
    #:
    #: ═══ VÌ SAO CÓ KHOÁ NÀY (chẩn đoán 28/09/2026) ═══
    #:
    #: Chủ kênh đăng video TAY trên YouTube (Studio, hẹn giờ của chính
    #: YouTube…) chứ không qua tool, và không biết/không muốn bấm "Đã đăng thủ
    #: công" trong tool — thấy quản lý thủ công quá khó. Cửa `_cua_so_san_xuat`
    #: coi mọi gói "Sẵn sàng" chưa có "Trạng thái đăng" là đang CHỜ, và không
    #: mở nguồn mới khi còn gói chờ — nếu chủ kênh không bao giờ bấm nút đó thì
    #: kênh ĐỨNG IM VĨNH VIỄN dù video đã lên sóng thật từ lâu.
    #:
    #: Mặc định 3 ngày — đủ để chủ kênh đăng theo nhịp bình thường, không đủ
    #: để một gói bị quên khoá cả kênh mãi mãi. KHÔNG xoá gì, KHÔNG đổi trạng
    #: thái dòng kế hoạch — chỉ THÔI CHẶN cửa sản xuất; `core.tu_nhan_da_dang`
    #: (tự nhận video đã đăng qua Studio) vẫn nhận ra và đánh dấu đúng khi chủ
    #: kênh đăng muộn hơn cả mốc này. `0` = tắt van này (chờ vô hạn như trước).
    cho_dang_toi_da_ngay: int = 3
    #: ═══ NHIỀU KHE ĐĂNG/NGÀY + KHO ĐỆM (29/09/2026, `core/xep_lich.py`) ═══
    #:
    #: `nhip_dang` — các giờ đăng trong ngày, vd `"12:00, 20:00"` hay
    #: `["12:00", "20:00"]`. Rỗng (mặc định) = `[gio_dang]` như cũ. Khai
    #: `nhip_dang` + `tu_duyet: true` thì bật chế độ mới: gói QA đạt được xếp
    #: vào khe trống sớm nhất ≥ bây giờ + `bien_xu_ly_gio`, và cửa chặn cứng
    #: "còn gói chờ đăng" được thay bằng KHO ĐỆM (`kho_dem_ngay` × số khe/ngày).
    nhip_dang: List[str] = field(default_factory=list)
    #: Số ngày video đã xếp lịch trước (kho đệm). Chỉ dùng khi khai `nhip_dang`.
    kho_dem_ngay: int = 3
    #: Biên (giờ) giữa lúc xếp lịch và giờ công khai — đủ để tải lên + YouTube xử lý.
    bien_xu_ly_gio: float = 12.0
    #: Clip engine hết hạn mức/không khả dụng mà đã tới hạn chót (giờ đăng của gói
    #: trừ ngần này giờ) thì cảnh thiếu clip được dựng từ chính ảnh cảnh bằng
    #: chuyển động máy nhẹ; trước hạn chót thì chờ engine (`core/clip_tu_anh.py`).
    han_clip_truoc_gio_dang: float = 6.0
    #: Trần số lượt sản xuất MỖI NGÀY của kênh. 0 = dùng `video_moi_ngay` (cũ).
    video_toi_da_ngay: int = 0
    #: Chủ dự án, 18/09/2026: video đăng xong rồi thì ảnh/clip/mp3 nặng của lượt
    #: đó chỉ còn chiếm đĩa VPS chứ không ai dùng lại — bật cờ này để tool TỰ
    #: XOÁ chúng sau khi đăng (`core/don_dep.py`). Tắt (mặc định) = không đụng
    #: gì, giữ nguyên nết cũ. Chữ/ảnh bìa đã chọn/metadata KHÔNG bao giờ bị xoá
    #: dù cờ này bật — chỉ ảnh cảnh, clip, mp3 giọng đọc, video đã dựng.
    tu_don: bool = False
    #: Chờ bao nhiêu GIỜ sau khi đăng mới xoá — hạn ân xá phòng khi YouTube xử
    #: lý hỏng và phải tải lại. 24 (mặc định). Chỉ có tác dụng khi `tu_don: true`.
    don_sau_gio: int = 24
    #: GIỮ TỐI ĐA BAO NHIÊU LƯỢT của kênh này trên đĩa — luật dọn thứ hai của
    #: `core/don_dep.py`, KHÔNG phụ thuộc "đã đăng".
    #:
    #: ═══ VÌ SAO CÓ KHOÁ NÀY (đo thật 24/09/2026) ═══
    #:
    #: `tu_don` + `don_sau_gio` chỉ xoá lượt có "Trạng thái đăng" ∈
    #: `don_dep.TRANG_THAI_DA_DANG`. Máy tự chạy hai ngày, chủ dự án chưa duyệt
    #: /đăng lượt nào → KHÔNG lượt nào thoả điều kiện → `PROJECTS/` phình lên
    #: **10,4 GB với 12 lượt** (TL1 5 lượt, TL2 3, TL3 4; lượt nặng nhất
    #: `TL3-T7/0002` một mình 2,4 GB) trên ổ C chỉ 49,4 GB. Chủ dự án:
    #: *"hằng ngày có tải dữ liệu kênh về thì cũng phải có logic dọn dẹp"*.
    #:
    #: Nên cần một trần KHÔNG hỏi tới trạng thái đăng: giữ N lượt MỚI NHẤT,
    #: lượt cũ hơn thì xoá phần NẶNG dù chưa đăng. Tệp nhỏ (`0-doi-thu.txt`,
    #: kịch bản, `3-phu-de.srt`, `4-canh.json`, bìa đã chọn, `trang-thai.json`)
    #: vẫn giữ nguyên — vòng học và chặn remake trùng còn đọc chúng.
    #:
    #: `0` (mặc định) = TẮT luật này, hành vi y như trước khoá này ra đời. Luật
    #: này vẫn nằm sau cờ `tu_don`: kênh chưa bật `tu_don` thì không bao giờ bị
    #: xoá tự động, dù đặt số ở đây.
    giu_toi_da_luot: int = 0
    #: Giữ báo cáo ngày (`workspace/tu-chay/<ngày>.*`,
    #: `CHANNEL/<kênh>/tu-chay/<ngày>.json`) bao nhiêu NGÀY trước khi
    #: `core/don_dep_mo_rong.py` dọn — cũng nằm sau cờ `tu_don`, cùng nguyên
    #: tắc với `don_sau_gio`/`giu_toi_da_luot` ở trên. Mặc định
    #: `don_dep_mo_rong.GIU_NGAY_BAO_CAO_MAC_DINH` (180 — nửa năm, đủ rộng để
    #: không ai mất báo cáo còn cần đọc lại).
    don_mo_rong_giu_ngay: int = 0

    #: NGÀY KÊNH BẮT ĐẦU LÀM NỘI DUNG CỦA TOOL NÀY, dạng ISO `"YYYY-MM-DD"`.
    #: Video đăng TRƯỚC ngày này không được tính vào số liệu và vòng học.
    #:
    #: ═══ VÌ SAO CÓ Ô NÀY ═══
    #:
    #: Bốn kênh đang chạy đều là kênh YouTube CÓ SẴN, đổi sang làm tâm lý Nhật —
    #: trên kênh còn nguyên video của đời trước, và extension cào Studio thì cào
    #: TẤT CẢ. Đo trên `CHANNEL/TL4-T7/chi-so/` (22/09/2026): `v8754af58fc` "Mở
    #: hộp con quay Infinity Nado 5" đăng 2018-12-27 có **35.701 lượt hiển thị,
    #: CTR 7,97%** — vượt xa ngưỡng THẮNG, nên nó tự nhận là "video thắng" của
    #: một kênh tâm lý, kéo theo cụm chủ đề và cả khuôn tiêu đề mẫu.
    #:
    #: Rỗng (mặc định) = không lọc gì, hành vi y như trước khoá này ra đời. Lý do
    #: và các chỗ cắm bộ lọc: `core/chi_so_ytb/loc_video.py`.
    ngay_bat_dau: str = ""

    #: Toàn bộ `style.yaml`, giữ nguyên để đưa thẳng cho bước viết lời nhắc.
    #: Nội dung `chien-luoc.yaml` nếu kênh dựng từ khuôn có chiến lược.
    #: Rỗng nghĩa là kênh chạy đường mặc định (remake).
    #:
    #: Để ở đây chứ không để trong khuôn vì kênh phải TỰ CHỨA: mấy con số như
    #: `tran_viet_lai` là thứ người dùng sẽ muốn nắn riêng cho từng kênh.
    chien_luoc: Dict[str, Any] = field(default_factory=dict)

    style: Dict[str, Any] = field(default_factory=dict)
    #: Đường dẫn ảnh nhân vật tham chiếu (thường là `nv/nv1.png`).
    anh_nv: List[str] = field(default_factory=list)
    #: Nội dung từng bước lời nhắc, khoá là tên tệp.
    prompt: Dict[str, str] = field(default_factory=dict)

    #: ═══ NHÓM KÊNH CÙNG NGÁCH (`core/nhom_kenh.py`) ═══
    #:
    #: Kế hoạch một VPS chạy nhiều kênh cùng ngách, mỗi kênh đánh một TỆP khán
    #: giả riêng (xem `CHANNEL/TL4-T7/nghien-cuu/BAN-DO-TEP-KHAN-GIA.md`), rồi
    #: các kênh "kéo nhau lên": không remake trùng nguồn, chia sẻ đối thủ mới
    #: dò được, so sánh video nào đang thắng.
    #:
    #: `nhom` — tên nhóm; rỗng = kênh đứng một mình, không đồng bộ với ai.
    #: `tep`  — mã/tên tệp khán giả kênh này đánh (ví dụ "1", "4") — chỉ để
    #: hiển thị và để bảng chéo kênh biết dán nhãn nào, không có logic riêng.
    nhom: str = ""
    tep: str = ""

    duong: str = ""

    @property
    def ky_tu_muc_tieu(self) -> int:
        """Số ký tự kịch bản cần có để đọc ra đúng `phut_muc_tieu`."""
        return int(round(self.phut_muc_tieu * max(1, self.ky_tu_moi_phut)))

    @property
    def ten_hien(self) -> str:
        return self.ten or self.ma


def duong_kenh(goc: str, ma: str = "") -> str:
    thu_muc = os.path.join(goc, THU_MUC_KENH)
    return os.path.join(thu_muc, ma) if ma else thu_muc


def _duong_tu_goc(goc: str, gia_tri: Any) -> str:
    """Đường cấu hình tương đối luôn bám gốc MyTool, không bám cwd."""
    duong = str(gia_tri or "").strip()
    if duong and not os.path.isabs(duong):
        return os.path.abspath(os.path.join(goc, duong))
    return duong


def liet_ke_kenh(goc: str) -> List[str]:
    """Tên các kênh đang có, xếp theo bảng chữ cái.

    Thư mục bắt đầu bằng `_` hoặc `.` bị bỏ qua — chỗ để người dùng cất bản
    nháp và bản mẫu mà không hiện ra trên giao diện.
    """
    thu_muc = duong_kenh(goc)
    try:
        muc = os.listdir(thu_muc)
    except OSError:
        return []
    ra = [t for t in muc
          if not t.startswith((".", "_"))
          and os.path.isfile(os.path.join(thu_muc, t, TEP_KENH))]
    return sorted(ra)


#: Ký tự không được có trong mã kênh (tên thư mục trên Windows).
_KY_TU_CAM_MA = '<>:"/\\|?*'


def kiem_ma_kenh_moi(goc: str, ma: str) -> str:
    """Câu lỗi nếu `ma` không dùng được làm mã kênh mới; rỗng nếu dùng được."""
    ma = (ma or "").strip()
    if not ma:
        return "Chưa đặt mã kênh. Mã là tên thư mục trong CHANNEL/, ví dụ TL4-T7-rieng."
    if ma.startswith((".", "_")):
        return ("Mã kênh không được bắt đầu bằng dấu chấm hay gạch dưới — tool "
                "coi những thư mục đó là bản nháp và không hiện chúng ra.")
    xau = [c for c in _KY_TU_CAM_MA if c in ma]
    if xau:
        return "Mã kênh không được chứa {0}".format(" ".join(xau))
    if ma.rstrip() != ma or ma.endswith("."):
        return "Mã kênh không được kết thúc bằng dấu cách hay dấu chấm."
    if os.path.exists(duong_kenh(goc, ma)):
        return ("Đã có kênh “{0}” rồi. Đặt mã khác — tôi không đè lên kênh "
                "đang có.".format(ma))
    return ""


def nhan_ban_kenh(goc: str, ma_goc: str, ma_moi: str, ten_moi: str = "") -> str:
    """Chép kênh `ma_goc` thành kênh RIÊNG `ma_moi`. Trả về đường dẫn kênh mới.

    ═══ VÌ SAO CÓ NÚT NÀY ═══

    Chủ dự án, 26/08/2026: *"các template đó tao có cập nhật nên nếu khách
    dùng và tùy chỉnh thì khi update sẽ bị đè, nên tao muốn những template
    khách tạo sẽ không bị đè… thêm tính năng nhân bản để khách nhân bản và
    giữ cho mình để tùy chỉnh"*.

    Bản sao mang đủ mọi thứ của kênh gốc (prompt, style, ảnh nhân vật, nhạc),
    chỉ khác `kenh.yaml`: `ma`/`ten` mới, bỏ cờ `mau_cua_tool`, thêm
    `kenh_rieng: true` — từ đó cập nhật tool không đụng vào nữa. Lượt chạy
    (`PROJECTS/AUTO/<mã>`) không chép: đó là sản phẩm của kênh cũ.
    """
    import shutil  # noqa: PLC0415
    from .dong_bo_kenh import dat_khoa_yaml  # noqa: PLC0415

    ma_goc = (ma_goc or "").strip()
    ma_moi = (ma_moi or "").strip()
    nguon = duong_kenh(goc, ma_goc)
    if not ma_goc or not os.path.isfile(os.path.join(nguon, TEP_KENH)):
        raise ValueError("Không thấy kênh “{0}” để nhân bản.".format(ma_goc))
    loi = kiem_ma_kenh_moi(goc, ma_moi)
    if loi:
        raise ValueError(loi)
    dich = duong_kenh(goc, ma_moi)
    shutil.copytree(nguon, dich, ignore=shutil.ignore_patterns(
        "__pycache__", "*.tam", "*.pyc"))
    duong = os.path.join(dich, TEP_KENH)
    with open(duong, "r", encoding="utf-8") as tep:
        chu = tep.read()
    # Bỏ cờ mẫu (nếu có) — bản sao không còn là mẫu của tool.
    chu = "\n".join(d for d in chu.split("\n")
                    if not d.strip().startswith("mau_cua_tool:"))
    chu = dat_khoa_yaml(chu, "ma", ma_moi, nhay=True)
    if (ten_moi or "").strip():
        chu = dat_khoa_yaml(chu, "ten", ten_moi.strip(), nhay=True)
    chu = dat_khoa_yaml(chu, "kenh_rieng", "true")
    dau = ("# ============================================================================\n"
           "#  KÊNH RIÊNG CỦA BẠN — nhân bản từ kênh mẫu “{0}”.\n"
           "#  Sửa thoải mái: cập nhật tool KHÔNG đụng vào kênh này (kenh_rieng: true).\n"
           "#  Kênh mẫu “{0}” thì được cập nhật theo tool — muốn xem bản mẫu mới\n"
           "#  có gì hay thì mở nó ở Quản lý kênh rồi chép tay sang đây.\n"
           "# ============================================================================\n"
           ).format(ma_goc)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(dau + chu)
    os.replace(tam, duong)
    return dich


# ── Đọc YAML mà không bắt khách cài thêm gì ──────────────────────────────────


def doc_yaml(duong: str) -> Dict[str, Any]:
    """Đọc một tệp YAML đơn giản. Không có tệp thì trả về `{}`.

    Dùng `PyYAML` nếu máy có; không có thì rơi về bộ đọc tối giản ở dưới. Lý do
    không bắt buộc `PyYAML`: `requirements.txt` của tool là thứ khách chạy một
    lần lúc cài, và mỗi dòng thêm vào đó là một cửa nữa để hỏng trên máy lạ.
    Tệp cấu hình kênh chỉ dùng `khoá: giá trị` và danh sách gạch đầu dòng — bộ
    đọc tối giản đủ dùng, còn ai đã có `PyYAML` thì được bản đầy đủ.
    """
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            tho = tep.read()
    except OSError:
        return {}
    try:
        import yaml  # noqa: PLC0415

        gia_tri = yaml.safe_load(tho)
        return gia_tri if isinstance(gia_tri, dict) else {}
    except ImportError:
        return _yaml_toi_gian(tho)
    except Exception:  # noqa: BLE001 — YAML hỏng thì thử bộ đọc thô
        return _yaml_toi_gian(tho)


def _yaml_toi_gian(tho: str) -> Dict[str, Any]:
    """Bộ đọc YAML đủ cho `kenh.yaml`: `khoá: giá trị` và danh sách `- mục`."""
    ra: Dict[str, Any] = {}
    khoa_hien: Optional[str] = None
    for dong in tho.splitlines():
        if not dong.strip() or dong.lstrip().startswith("#"):
            continue
        if dong.startswith((" ", "\t")) and dong.strip().startswith("- "):
            if khoa_hien:
                ra.setdefault(khoa_hien, [])
                if isinstance(ra[khoa_hien], list):
                    ra[khoa_hien].append(_go_nhay(dong.strip()[2:]))
            continue
        if dong.strip().startswith("- "):
            continue
        if ":" not in dong:
            continue
        khoa, _, gia_tri = dong.partition(":")
        khoa = khoa.strip()
        gia_tri = gia_tri.strip()
        khoa_hien = khoa
        ra[khoa] = _go_nhay(gia_tri) if gia_tri else ""
    return ra


def _go_nhay(chu: str) -> Any:
    chu = chu.strip()
    if len(chu) >= 2 and chu[0] == chu[-1] and chu[0] in "'\"":
        return chu[1:-1]
    thap = chu.lower()
    if thap in ("true", "yes"):
        return True
    if thap in ("false", "no"):
        return False
    try:
        return int(chu)
    except ValueError:
        pass
    try:
        return float(chu)
    except ValueError:
        return chu


# ── Đọc một kênh ─────────────────────────────────────────────────────────────


def doc_kenh(goc: str, ma: str) -> Kenh:
    """Đọc trọn một kênh từ đĩa. Không ném lỗi — thiếu gì thì `kiem_kenh` nói.

    Cố ý **không** ném khi thiếu tệp: giao diện cần dựng được danh sách kênh kể
    cả khi một kênh làm dở, để nói cho người dùng biết kênh nào thiếu gì. Ném ở
    đây thì cả tab trắng vì một thư mục hỏng.
    """
    thu_muc = duong_kenh(goc, ma)
    cai = doc_yaml(os.path.join(thu_muc, TEP_KENH))
    # Đọc trước — `chon_bia_ai` (Việc 4) mặc định BẰNG giá trị này (quyết định
    # 10 bản thiết kế), nên cần có sẵn trước khi dựng `Kenh(...)` ở dưới.
    _tu_chay_val = _co(cai.get("tu_chay"))
    kenh = Kenh(
        ma=str(cai.get("ma") or ma),
        ten=str(cai.get("ten") or ""),
        ngon_ngu=str(cai.get("ngon_ngu") or ""),
        giong_van=str(cai.get("giong_van") or ""),
        phut_muc_tieu=_so(cai.get("phut_muc_tieu"), 10.0),
        ky_tu_moi_phut=int(_so(cai.get("ky_tu_moi_phut"), 900)),
        # Trần 0,5: nới quá đó thì "13 phút" nghĩa là "6,5 tới 19,5" — con số
        # mục tiêu hết nghĩa, và bước nắn không bao giờ chạy nữa.
        chenh_cho_phep=min(0.5, max(0.0, _so(cai.get("chenh_cho_phep"), 0.0))),
        do_dai_theo_goc=bool(cai.get("do_dai_theo_goc", False)),
        so_ban_nhap=min(5, max(1, int(_so(cai.get("so_ban_nhap"), 1)))),
        so_ban_hook=min(6, max(0, int(_so(cai.get("so_ban_hook"), 0)))),
        che_do_ke=str(cai.get("che_do_ke") or "").strip(),
        do_dai_tu_do=bool(cai.get("do_dai_tu_do", False)),
        khung_dau=bool(cai.get("khung_dau", False)),
        cham_anh=bool(cai.get("cham_anh", False)),
        ghim_hai_dau=bool(cai.get("ghim_hai_dau", False)),
        danh_sach_phat_kenh=str(cai.get("danh_sach_phat_kenh") or "").strip(),
        xuat_capcut=bool(cai.get("xuat_capcut", False)),
        hoan_thien=bool(cai.get("hoan_thien", cai.get("va_cho_rot", False))),
        so_vong_cham=min(5, max(0, int(_so(cai.get("so_vong_cham"), 0)))),
        so_ban_va=min(4, max(1, int(_so(cai.get("so_ban_va"), 2)))),
        mau_cua_tool=_co(cai.get("mau_cua_tool")),
        kenh_rieng=_co(cai.get("kenh_rieng")),
        che_do_tieu_de=ten_che_do(cai.get("che_do_tieu_de")),
        nhan_tieu_de=str(cai.get("nhan_tieu_de") or "").strip(),
        nan_khuon_tieu_de=_co(cai.get("nan_khuon_tieu_de")),
        # Việc 5 — trần 8: gõ nhầm một số lớn không được làm phình một lượt gọi
        # (mỗi bản một dòng trong cùng lời nhắc) thành một khối chữ khổng lồ.
        so_tieu_de=max(0, min(8, int(_so(cai.get("so_tieu_de"), 4)))),
        voice_id=str(cai.get("voice_id") or ""),
        engine=str(cai.get("engine") or "veo3"),
        mo_hinh=str(cai.get("mo_hinh") or "claude-sonnet-5"),
        chu_bia_hoa=bool(cai.get("chu_bia_hoa", True)),
        so_thumbnail=max(1, int(_so(cai.get("so_thumbnail"), 3))),
        # Nhịp nghỉ giữa các phần: 0 = tắt. Không cho số âm (FFmpeg dựng
        # tệp lặng dài âm giây là hỏng lệnh nối).
        giay_nghi_phan=max(0.0, float(_so(cai.get("giay_nghi_phan"), 1.2))),
        dot_phu_de=bool(cai.get("dot_phu_de", True)),
        giu_tieng_canh=bool(cai.get("giu_tieng_canh", False)),
        am_luong_tieng_canh=max(0.0, min(1.0, float(
            cai.get("am_luong_tieng_canh", 0.35) or 0.35))),
        nguong_tieng_nguoi=max(0.0, min(1.0, float(
            cai.get("nguong_tieng_nguoi", 0.0) or 0.0))),
        # Gõ sai tên độ phân giải thì quay về "Giữ nguyên" chứ không ném lỗi:
        # một chữ gõ nhầm trong `kenh.yaml` không đáng làm chết cả lượt chạy.
        do_phan_giai=ten_khung(cai.get("do_phan_giai")),
        nhac_nen=str(cai.get("nhac_nen") or ""),
        # Kẹp trong 0..1. Số âm làm FFmpeg đảo pha, số lớn hơn 1 làm nhạc át
        # hẳn giọng đọc — cả hai đều là gõ nhầm chứ không ai cố ý.
        am_luong_nhac=min(1.0, max(0.0, _so(cai.get("am_luong_nhac"), 0.12))),
        # Dựng theo phần (Việc 2). Kẹp số: gõ nhầm không được làm hỏng khâu
        # dựng — nghỉ âm thành 0 (tắt), nghỉ quá 10s coi như gõ nhầm → 10.
        giay_nghi_chuyen_phan=min(10.0, max(0.0, _so(
            cai.get("giay_nghi_chuyen_phan"), 3.0))),
        chuyen_phan=_kieu_chuyen(cai.get("chuyen_phan")),
        giay_chuyen_phan=min(3.0, max(0.1, _so(cai.get("giay_chuyen_phan"), 1.0))),
        nhac_theo_phan=_co_mac_dinh(cai.get("nhac_theo_phan"), True),
        kho_nhac=str(cai.get("kho_nhac") or "PROJECTS/music").strip(),
        nhac_duoi_giong_db=min(40.0, max(6.0, _so(cai.get("nhac_duoi_giong_db"), 18.0))),
        nhac_nghi_giua_phan=min(10.0, max(0.0, _so(cai.get("nhac_nghi_giua_phan"), 2.0))),
        nhac_noi_bai_giay=min(10.0, max(1.0, _so(cai.get("nhac_noi_bai_giay"), 4.0))),
        ngat_phan_tu_dong=_co(cai.get("ngat_phan_tu_dong")),
        dung_mot_lan=_co(cai.get("dung_mot_lan")),
        vong_hoc=_co_mac_dinh(cai.get("vong_hoc"), True),
        # Việc 4 — chọn ảnh bìa bằng AI. Xem docstring các trường ở khai báo lớp.
        chon_bia_ai=_co_mac_dinh(cai.get("chon_bia_ai"), _tu_chay_val),
        so_luot_cham_bia=max(1, min(4, int(_so(cai.get("so_luot_cham_bia"), 2)))),
        mo_hinh_cham_bia=str(cai.get("mo_hinh_cham_bia") or "").strip(),
        bia_khuon_thang=_co_mac_dinh(cai.get("bia_khuon_thang"), True),
        bia_kham_pha=_co_mac_dinh(cai.get("bia_kham_pha"), True),
        bia_khuon_nhom=_co_mac_dinh(cai.get("bia_khuon_nhom"), False),
        # Việc 5b — xem docstring trường `kiem_trung_y` ở khai báo lớp.
        kiem_trung_y=_co_mac_dinh(cai.get("kiem_trung_y"), True),
        tu_chay=_tu_chay_val,
        tu_duyet=_co(cai.get("tu_duyet")),
        gio_dang=str(cai.get("gio_dang") or "").strip(),
        ngan_sach_ngay=max(0, int(_so(cai.get("ngan_sach_ngay"), 0))),
        # Cho phép ghi `DONE/TL1-T7` để cả thư mục MyTool có thể chuyển sang
        # ổ/máy khác. Đường tương đối luôn bám gốc MyTool, không bám thư mục
        # hiện hành (Task Scheduler thường chạy từ System32).
        thu_muc_done=_duong_tu_goc(goc, cai.get("thu_muc_done")),
        video_moi_ngay=max(1, int(_so(cai.get("video_moi_ngay"), 1))),
        chu_ky_dang_ngay=max(1, int(_so(cai.get("chu_ky_dang_ngay"), 1))),
        san_xuat_truoc_gio=max(0, int(_so(cai.get("san_xuat_truoc_gio"), 0))),
        cho_dang_toi_da_ngay=max(0, int(_so(cai.get("cho_dang_toi_da_ngay"), 3))),
        nhip_dang=_nhip_dang(cai.get("nhip_dang")),
        kho_dem_ngay=min(14, max(1, int(_so(cai.get("kho_dem_ngay"), 3)))),
        bien_xu_ly_gio=min(72.0, max(1.0, _so(cai.get("bien_xu_ly_gio"), 12.0))),
        han_clip_truoc_gio_dang=min(48.0, max(0.0, _so(cai.get("han_clip_truoc_gio_dang"), 6.0))),
        video_toi_da_ngay=min(24, max(0, int(_so(cai.get("video_toi_da_ngay"), 0)))),
        tu_don=_co(cai.get("tu_don")),
        don_sau_gio=max(0, int(_so(cai.get("don_sau_gio"), 24))),
        # Âm là gõ nhầm, và âm ở đây nghĩa là "giữ ít hơn 0 lượt" — kẹp về 0
        # (tắt) chứ không để nó thành một trần xoá sạch mọi lượt.
        giu_toi_da_luot=max(0, int(_so(cai.get("giu_toi_da_luot"), 0))),
        # `0` (mặc định) = chưa khai, `core.don_dep_mo_rong` tự lùi về
        # `GIU_NGAY_BAO_CAO_MAC_DINH`. Kẹp về 0 khi âm, cùng lý do với
        # `giu_toi_da_luot` ở trên.
        don_mo_rong_giu_ngay=max(0, int(_so(cai.get("don_mo_rong_giu_ngay"), 0))),
        # Chuẩn hoá qua `loc_video.chuan_ngay`: PyYAML đổi `ngay_bat_dau:
        # 2026-08-22` KHÔNG bọc nháy thành `datetime.date`, và một ngày gõ sai
        # ("2026-13-45") phải thành rỗng — tức là KHÔNG LỌC — chứ không được
        # thành một mốc vô nghĩa loại sạch mọi video của kênh.
        ngay_bat_dau=_ngay_bat_dau(cai.get("ngay_bat_dau")),
        style=doc_yaml(os.path.join(thu_muc, TEP_STYLE)),
        chien_luoc=doc_yaml(os.path.join(thu_muc, TEP_CHIEN_LUOC)),
        nhom=str(cai.get("nhom") or "").strip(),
        tep=str(cai.get("tep") or "").strip(),
        duong=thu_muc,
    )
    kenh.anh_nv = _anh_trong(os.path.join(thu_muc, THU_MUC_NV))
    kenh.prompt = _doc_prompt(os.path.join(thu_muc, THU_MUC_PROMPT))
    return kenh


def _nhip_dang(gia_tri) -> List[str]:
    """`nhip_dang` → `["HH:MM", …]`; hỏng/thiếu → `[]` (= dùng `gio_dang` cũ)."""
    try:
        from .xep_lich import chuan_hoa_nhip  # noqa: PLC0415

        return chuan_hoa_nhip(gia_tri)
    except Exception:  # noqa: BLE001 — một khoá gõ sai không được làm hỏng cả kênh
        return []


def _ngay_bat_dau(gia_tri) -> str:
    """`ngay_bat_dau` về dạng `"YYYY-MM-DD"`; không đọc được thì rỗng (= không lọc).

    Dùng lại đúng bộ chuẩn hoá của bộ lọc số liệu để hai bên không bao giờ hiểu
    một giá trị theo hai cách. Không nhập được `core.chi_so_ytb` (bản rút gọn,
    thiếu mô-đun) thì đọc thô — `core/kenh.py` phải nạp được trong mọi hoàn cảnh.
    """
    try:
        from .chi_so_ytb.loc_video import chuan_ngay  # noqa: PLC0415
    except Exception:  # noqa: BLE001
        chu = str(gia_tri or "").strip()[:10]
        return chu if re.fullmatch(r"\d{4}-\d{2}-\d{2}", chu) else ""
    return chuan_ngay(gia_tri)


def _co(gia_tri) -> bool:
    """`true`/`yes`/`1` (bất kể hoa thường) là bật; còn lại là tắt."""
    if isinstance(gia_tri, bool):
        return gia_tri
    return str(gia_tri or "").strip().lower() in ("true", "yes", "1")


def _co_mac_dinh(gia_tri, mac_dinh: bool) -> bool:
    """Như `_co`, nhưng KHÔNG khai (hoặc để trống) thì lấy `mac_dinh`."""
    if gia_tri is None or (isinstance(gia_tri, str) and not gia_tri.strip()):
        return mac_dinh
    return _co(gia_tri)


def _kieu_chuyen(gia_tri) -> str:
    """`chuyen_phan`: den/trang/khong; gõ lạ thì về `den` (mặc định)."""
    chu = str(gia_tri or "").strip().lower()
    return chu if chu in ("den", "trang", "khong") else "den"


def _so(gia_tri, mac_dinh: float) -> float:
    try:
        return float(gia_tri)
    except (TypeError, ValueError):
        return mac_dinh


#: Mã tiếng → tên gọi tiếng Việt, để lời nhắc nói "viết bằng tiếng Nhật" thay
#: vì "viết bằng ja". Chủ dự án, 25/08/2026: *"viết bằng ja thì phải rõ là viết
#: bằng ngôn ngữ tiếng Nhật"*. Thiếu mã nào thì trả lại chính mã ấy.
#: Đủ ~70 thứ tiếng bộ đọc đang chạy hỗ trợ. Bỏ Cebuano vì không có mã hai chữ.
_TEN_TIENG = {
    "ja": "tiếng Nhật", "vi": "tiếng Việt", "en": "tiếng Anh", "zh": "tiếng Trung",
    "ko": "tiếng Hàn", "es": "tiếng Tây Ban Nha", "fr": "tiếng Pháp",
    "de": "tiếng Đức", "pt": "tiếng Bồ Đào Nha", "it": "tiếng Ý", "ru": "tiếng Nga",
    "th": "tiếng Thái", "id": "tiếng Indonesia", "ms": "tiếng Mã Lai",
    "ar": "tiếng Ả Rập", "hi": "tiếng Hindi", "tr": "tiếng Thổ Nhĩ Kỳ",
    "nl": "tiếng Hà Lan", "pl": "tiếng Ba Lan", "tl": "tiếng Philippines",
    # Châu Á còn lại
    "jv": "tiếng Java", "bn": "tiếng Bengal", "ta": "tiếng Tamil", "te": "tiếng Telugu",
    "mr": "tiếng Marathi", "gu": "tiếng Gujarat", "kn": "tiếng Kannada",
    "ml": "tiếng Malayalam", "pa": "tiếng Punjab", "ur": "tiếng Urdu", "ne": "tiếng Nepal",
    "as": "tiếng Assam", "sd": "tiếng Sindhi", "ps": "tiếng Pashto", "fa": "tiếng Ba Tư",
    "he": "tiếng Do Thái", "az": "tiếng Azerbaijan", "kk": "tiếng Kazakh",
    "ky": "tiếng Kyrgyz", "hy": "tiếng Armenia", "ka": "tiếng Gruzia",
    # Châu Âu
    "uk": "tiếng Ukraina", "be": "tiếng Belarus", "cs": "tiếng Séc", "sk": "tiếng Slovakia",
    "sl": "tiếng Slovenia", "hu": "tiếng Hungary", "ro": "tiếng Romania",
    "bg": "tiếng Bulgaria", "sr": "tiếng Serbia", "hr": "tiếng Croatia", "bs": "tiếng Bosnia",
    "mk": "tiếng Macedonia", "el": "tiếng Hy Lạp", "ca": "tiếng Catalan", "gl": "tiếng Galicia",
    "lb": "tiếng Luxembourg", "sv": "tiếng Thụy Điển", "da": "tiếng Đan Mạch",
    "no": "tiếng Na Uy", "fi": "tiếng Phần Lan", "is": "tiếng Iceland", "et": "tiếng Estonia",
    "lv": "tiếng Latvia", "lt": "tiếng Litva", "ga": "tiếng Ireland", "cy": "tiếng Wales",
    # Châu Phi
    "af": "tiếng Afrikaans", "sw": "tiếng Swahili", "ha": "tiếng Hausa", "so": "tiếng Somali",
    "ny": "tiếng Chichewa", "ln": "tiếng Lingala",
}


def ten_tieng(ma: str) -> str:
    """`"ja"` → `"tiếng Nhật"`; mã lạ thì trả nguyên mã (còn hơn trả rỗng)."""
    chu = str(ma or "").strip().lower()
    return _TEN_TIENG.get(chu[:2], chu) if chu else ""


#: Thứ tự bày trong ô chọn ngôn ngữ giọng đọc: tiếng khách hay làm kênh lên đầu.
_THU_TU_TIENG = ("vi", "en", "ja", "ko", "zh", "es", "pt", "fr", "de", "id", "th")

#: `[(mã, tên)]` cho ô chọn ngôn ngữ ở những chỗ tạo giọng đọc.
DANH_SACH_TIENG = [(ma, _TEN_TIENG[ma]) for ma in _THU_TU_TIENG] + sorted(
    ((ma, ten) for ma, ten in _TEN_TIENG.items() if ma not in _THU_TU_TIENG),
    key=lambda c: c[1])


def ma_ngon_ngu_tts(ma: str) -> str:
    """Mã ngôn ngữ (ISO 639-1, hai chữ) gửi kèm việc đọc — hoặc rỗng.

    ═══ ĐO NGÀY 08/09/2026: MÁY CHỦ HIỆN ĐANG BỎ QUA MÃ NÀY ═══

    Gửi thì máy chủ vẫn nhận (202) — nó bỏ qua mọi trường lạ chứ không báo lỗi
    — nhưng audio **không đổi**. Ba thước đo độc lập, đều trên job thật:

    * **Thời lượng.** Chín lượt đọc cùng một câu tiếng Việt, giọng `vi_female_01`:
      không mã 7,88 s · ghim `vi` 7,93 s · ghim `en` (sai hẳn) 7,99 s. Chênh
      giữa các nhóm 0,05–0,11 s, trong khi nhiễu của riêng một nhóm lên tới
      0,65 s. Lặp lại với giọng đa ngữ + chữ Nhật: chênh 0,24–0,78 s, nhiễu 1,28 s.
    * **Băm tệp.** Mọi tệp một băm khác nhau → audio sinh lại mỗi lượt, nên
      trùng cỡ tệp chỉ là trùng độ dài, không phải cùng một bản.
    * **Nghe lại bằng `faster-whisper`.** Tám tệp tiếng Nhật, kể cả những lượt
      ghim SAI mã (`vi`), đều nghe ra tiếng Nhật đúng, tin cậy 0,99–1,00. Nếu
      mã được nghe theo thì chữ Nhật đọc bằng âm Việt phải nát, không thể thế.

    Vì vậy **đừng hứa với khách rằng chọn mã làm giọng hay hơn, cũng đừng doạ
    rằng chọn nhầm là hỏng** — hôm nay không điều nào đúng. Đường dây phía
    client giữ nguyên vì nó đúng và không tốn gì: ngày máy chủ dùng đến trường
    này thì cả khách bản cũ cũng được hưởng, không cần cập nhật tool.

    Kênh khai `ngon_ngu` tự do (`ja`, `ja-JP`, `Japanese`…): chỉ lấy khi hai
    chữ đầu là chữ cái; còn lại trả rỗng — thà không mã còn hơn mã sai.
    """
    chu = str(ma or "").strip().lower()[:2]
    return chu if len(chu) == 2 and chu.isalpha() and chu.isascii() else ""


#: Tên độ phân giải giữ nguyên cỡ nhà cung cấp trả về.
GIU_NGUYEN = "Giữ nguyên"


def ten_khung(gia_tri) -> str:
    """Nắn tên độ phân giải khách gõ về một trong các tên tool hiểu.

    Nhận cả `4k`, `4K`, `2160p`, `2160` — người ta gọi cùng một thứ bằng nhiều
    tên, và bắt gõ đúng một kiểu là bắt nhầm người.

    Trả về **chuỗi rỗng** khi không khai gì, hoặc khai một thứ tool không hiểu.
    Rỗng nghĩa là *"chưa nói gì, lấy theo cài đặt chung"* — khác hẳn
    `"Giữ nguyên"`, vốn là một lựa chọn có chủ ý.

    Phân biệt hai cái đó là điều kiện để có hai tầng cài đặt mà không rối: gõ
    sai một chữ trong `kenh.yaml` thì rơi về cài đặt chung của tool, chứ không
    lặng lẽ tắt mất tính năng.
    """
    chu = str(gia_tri or "").strip().lower().replace(" ", "")
    if not chu:
        return ""
    # Cả bản có dấu lẫn bản không dấu. Chính tool ghi xuống `kenh.yaml` bản có
    # dấu ("Giữ nguyên"), còn người gõ tay thì hay gõ không dấu — thiếu một
    # trong hai là ô chọn của chính mình lưu xong đọc lại không ra.
    if chu in ("giữnguyên", "giunguyen", "gốc", "goc",
               "không", "khong", "none", "nguyên", "nguyen"):
        return GIU_NGUYEN
    if chu in ("4k", "2160p", "2160", "uhd"):
        return "4K"
    if chu in ("1440p", "1440", "2k", "qhd"):
        return "1440p"
    if chu in ("1080p", "1080", "fullhd", "fhd"):
        return "1080p"
    return ""


#: Ba chế độ đặt tiêu đề. `faithful`/`restyled` là hai nhánh lời nhắc
#: `1-tieu-de.md` hiểu; `nguyen_goc` lấy nguyên tiêu đề đối thủ + đọc ảnh bìa,
#: không chạy lời nhắc.
CHE_DO_TIEU_DE = ("faithful", "restyled", "nguyen_goc")


def ten_che_do(gia_tri) -> str:
    """Nắn tên chế độ tiêu đề về giá trị hiểu được; gõ sai thì về "faithful".

    Rơi về `"faithful"` (bám bản gốc) khi bỏ trống hoặc gõ một chữ tool không
    hiểu — nết an toàn, đúng hành vi mọi kênh cũ, chứ không lặng lẽ tắt bước đặt
    tên vì một chữ gõ nhầm. Muốn kênh tự đặt lại tiêu đề thì khai `restyled`;
    muốn lấy nguyên tiêu đề + chữ bìa đối thủ thì khai `nguyen_goc`.
    """
    chu = str(gia_tri or "").strip().lower()
    return chu if chu in CHE_DO_TIEU_DE else "faithful"


def _anh_trong(thu_muc: str) -> List[str]:
    try:
        muc = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    duoi = (".png", ".jpg", ".jpeg", ".webp")
    return [os.path.join(thu_muc, t) for t in muc if t.lower().endswith(duoi)]


def _doc_prompt(thu_muc: str) -> Dict[str, str]:
    ra: Dict[str, str] = {}
    for ten, _mo_ta in BUOC_PROMPT:
        try:
            with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
                ra[ten] = tep.read()
        except OSError:
            continue
    return ra


# ── Kiểm kênh, và chặn khoá lọt vào ──────────────────────────────────────────

#: Dấu vết khoá thật. Bắt theo **hình dạng khoá**, không bắt theo tên khoá: đặt
#: tên là `abc` mà giá trị là `sk-...` thì vẫn là khoá.
_DAU_VET_KHOA = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}"
    r"|sk_[A-Za-z0-9]{16,}"
    r"|wk_[A-Za-z0-9]{16,}"
    r"|AIza[A-Za-z0-9_\-]{20,}"
    r"|ya29\.[A-Za-z0-9_\-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


def co_mui_khoa(chu: str) -> str:
    """Trả về đoạn khớp đầu tiên nếu chuỗi có vẻ chứa khoá, rỗng nếu sạch."""
    khop = _DAU_VET_KHOA.search(chu or "")
    return khop.group(0)[:12] + "…" if khop else ""


def kiem_kenh(kenh: Kenh) -> List[str]:
    """Kênh này còn thiếu gì. Rỗng nghĩa là chạy được.

    Mỗi câu phải nói **thiếu gì và sửa ở đâu** — người đọc nó là người không
    biết lập trình, đang nhìn một thư mục họ tự chép ra.
    """
    thieu: List[str] = []
    if not kenh.ma:
        thieu.append("Thiếu mã kênh — thêm dòng `ma:` vào {0}.".format(TEP_KENH))
    if not kenh.ngon_ngu:
        thieu.append("Chưa biết kênh nói tiếng gì — thêm `ngon_ngu:` vào {0} "
                     "(ví dụ `es`, `vi`, `en`).".format(TEP_KENH))
    # Kênh timelapse không có lời đọc và không có nhân vật, và nó tự dựng bảng
    # cảnh từ bảng mốc thời gian chứ không qua hai bước lời nhắc kia. Đòi nó đủ
    # bốn thứ ấy là bắt người dùng đi tìm cách chữa một lỗi không có thật.
    ke_thuong = str(getattr(kenh, "che_do_ke", "") or "").strip() != "timelapse"
    if ke_thuong:
        if not kenh.voice_id:
            thieu.append("Chưa chọn giọng đọc — thêm `voice_id:` vào {0}. Mã "
                         "giọng lấy ở tab Voice.".format(TEP_KENH))
        if not kenh.anh_nv:
            thieu.append("Chưa có ảnh nhân vật tham chiếu — bỏ một tệp .png vào "
                         "thư mục `{0}/`. Thiếu nó thì mỗi cảnh ra một nhân vật "
                         "khác nhau.".format(THU_MUC_NV))
    if not kenh.style.get("image_style"):
        thieu.append("Chưa tả kênh nhìn như thế nào — thêm `image_style:` vào "
                     "{0}.".format(TEP_STYLE))
    for ten in BUOC_BAT_BUOC:
        if not ke_thuong and ten in ("2-viet.md", "7-canh.md"):
            continue
        if not (kenh.prompt.get(ten) or "").strip():
            mo_ta = dict(BUOC_PROMPT).get(ten, ten)
            thieu.append("Thiếu bước “{0}” — tạo tệp `{1}/{2}`.".format(
                mo_ta, THU_MUC_PROMPT, ten))

    # ═══ CHẶN KHOÁ ═══
    #
    # Quét cả cấu hình lẫn lời nhắc: người dùng chép thư mục kênh từ tool cũ
    # sang thì rất dễ mang theo cả dòng khoá router nằm trong đó.
    for ten, noi_dung in [(TEP_KENH, _tho(kenh.duong, TEP_KENH)),
                          (TEP_STYLE, _tho(kenh.duong, TEP_STYLE))] \
            + [("{0}/{1}".format(THU_MUC_PROMPT, k), v)
               for k, v in sorted(kenh.prompt.items())]:
        dau = co_mui_khoa(noi_dung)
        if dau:
            thieu.append(
                "Tệp `{0}` có vẻ chứa một khoá API ({1}). Xoá dòng đó đi — "
                "luồng AUTO dùng ví ShopAPI của tool, kênh không cần khoá "
                "riêng, và để khoá ở đây là ai cầm thư mục kênh cũng tiêu được "
                "tiền của bạn.".format(ten, dau))
    return thieu


def _tho(thu_muc: str, ten: str) -> str:
    try:
        with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""
