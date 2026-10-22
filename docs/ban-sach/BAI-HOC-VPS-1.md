# Bài học từ VPS đầu (09–10/2026) — đọc trước khi vận hành máy mới

Mỗi bài: chuyện gì đã xảy ra → luật rút ra → chỗ trong mã. Không có tên kênh, số liệu hay tài khoản thật.

## Kênh, tài khoản, Chrome
- **Tài khoản không được phân phối ("mail hỏng") là lỗi tài khoản, không phải nội dung.** Dấu hiệu: ≥ 10 video đăng
  ≥ 72 giờ, trung vị lượt hiển thị < 100, không video nào > 500 (kênh tốt trung vị hàng trăm). → kênh thay GIỮ NGUYÊN
  mọi thứ (nhân vật, style, prompt, giọng, nhịp) chỉ đổi mã/Chrome/tài khoản/UC. `core/thay_kenh.py` (D20), kho Chrome
  `<cha>\kho\`, `core/kho_chrome.py`. Số liệu/não của kênh trả kho KHÔNG được tính vào học tập.
- **Kênh MỚI đánh vùng mới thì nhân vật mới phải viết lại MỌI chỗ tả nhân vật** (style.yaml + mọi prompt/*.md), rồi mã
  kiểm không còn chữ của nhân vật cũ. Từng chỉ thay một dòng `default_character_lock` → ảnh cảnh vẽ nhân vật của kênh gốc.
  `core/mo_kenh.viet_lai_nhan_vat_cu`, `core/nhan_vat_nhat_quan.py`.
- **Tài khoản kho phải có kênh THƯƠNG HIỆU và Studio phải trỏ đúng UC trước khi thiết lập**, không thì thiết lập sửa
  nhầm kênh cá nhân. `vm/tao_kenh_thuong_hieu.py` (không tạo trùng, ghim UC `vm/logs/kenh-uc.json`), rồi mới 11/11.
- **Kênh mới gặp hộp «Chào mừng YouTube Studio»** và vài hộp lần đầu — máy thiết lập đã xử lý; gặp hộp lạ thì ghi việc
  người, không bấm bừa.
- **Kênh tái sử dụng còn video rác cũ**: mọi số liệu/vòng học chỉ tính video do tool làm hoặc đăng sau mốc bắt đầu ngách.
- **Không bao giờ tự đăng nhập Google.** Chủ đăng nhập tay trong Chrome kho; máy chỉ đọc cookie để biết đã đăng nhập.

## Mạng, Studio, ngôn ngữ
- **IPv4 phải tắt khi Chrome kênh đang mở** (danh tính kênh gắn IPv6 của máy). VPS chỉ IPv6: proxy IPv4 vô dụng;
  yt-dlp/transcript từ VPS bị chặn ("IP cloud") → lời thoại đối thủ lấy bằng chính Chrome kênh (đọc
  `captionTracks` trong trang, `core/ytb_extension/loi-thoai.js`).
- **Ngôn ngữ hiển thị / Địa điểm của kênh là việc MỘT LẦN** trong skill thiết lập kênh, làm trên menu youtube.com như
  người rồi ĐỌC LẠI; không đặt lại mỗi lượt đăng. Máy đăng chỉ TẠM đổi giao diện trong phiên rồi trả lại
  (`vm/ngon_ngu_tam.py`). Địa điểm suy từ quốc gia của ngách, không từ ngôn ngữ giao diện.
- **Ngôn ngữ tài khoản theo quốc gia** chỉ bật khi đã chứng minh đăng thật qua Studio ngôn ngữ đó
  (`workspace/cai-dat.json: ngon_ngu_tai_khoan_chung_minh`).

## Bìa và ảnh
- **Bìa sai chữ là tối kỵ**: soát chữ trước khi vẽ, đọc lại chữ trên ảnh 2 lần độc lập khớp từng ký tự, dấu `chu_khop`
  + sha1; mọi lối ra YouTube từ chối bìa không dấu. Ưu tiên chữ do mã vẽ. `core/cong_chu.py`.
- **Bìa theo SỐ LIỆU, không theo ý**: mẫu thắng = bìa thật nhiều lượt bấm (hiển thị × CTR) của chính kênh, tự dựng lại
  hằng ngày, không lọc kiểu; kiểu chữ chọn theo CTR có thăm dò; vòng CTR 48h/7 ngày. Phải bám cả **ADN phong cách**
  (sắc màu chủ đạo, nền tối/sáng, góc nghiêng chữ/dải, vị trí nhân vật) — từng có bìa mới lệch màu nền tím → nâu dù
  đúng "họ chữ". `core/bia_du_lieu.py`, `core/bia_lo.py`, D21.
- **A/B bìa bằng «Thử nghiệm A/B» của Studio** (cần kênh đã xác minh điện thoại), chỉ thử bìa, không đụng video thắng.
- **Ảnh cảnh**: mỗi cảnh N ứng viên → giám khảo nhìn (khớp lời đọc, giọng ấm/không kinh dị, lỗi hình, phong cách, đúng
  nhân vật) → dưới ngưỡng thì viết lại prompt theo lý do. Cấm mũi tên/dấu, lưới ô, chữ trên ảnh. `core/chon_anh_canh.py`.
- Học bìa từ ảnh THẬT trên `i.ytimg.com` (chủ có thể đã đổi tay), không từ tệp tool làm.

## Nội dung
- Chọn content quyết định ~80%: đối thủ đúng ngách + video nổ (≥ 5–8× trung vị kênh nguồn) + đà tăng; đọc NGHĨA bằng
  LLM, khán giả là điều kiện cứng (từng lọt nguồn có nhân vật học sinh vào kênh nhắm người lớn).
- Kịch bản không được chép nguồn: cổng độc đáo (`core/do_doc_dao.py`, trùng > 15% → viết lại giọng kênh).
- Luôn khai nhãn "nội dung có AI". Không xoá dấu chìm, không giả chữ ký, không đổi tên tệp để giấu AI.
- Đăng đều ~1 video/ngày/kênh; đăng dồn làm hiển thị tụt.

## Tăng trưởng
- Nút nghẽn YPP thường là ĐĂNG KÝ: hình mờ, trang chủ kênh + trailer, ghim bình luận, câu kêu gọi giữa video.
- **Cộng sự (Collaborators)**: mỗi ngày top 5 video tăng view 48h của CẢ nhóm → mời các kênh còn lại làm cộng sự.
  Trong hộp con «Mời người cộng tác», sau khi chọn kênh phải bấm **«Tạo đường liên kết»**, đọc link mới, đóng hộp; bên
  được mời mở link để nhận. Tìm kênh theo @handle/tên (dán UC không ra). Chạy trong phiên Chrome ngày của kênh, không
  mở Chrome riêng. `core/cong_su.py`, `vm/cong_su_dom.py` (D25/D26).
- Trang chủ của tài khoản phải luôn ≥ 90% đúng chủ đề: đo lại theo lượt quét sẵn có, tụt thì tự nuôi lại
  (`vm/nuoi_trang_chu.py`, D18). Trang chủ trôi khỏi chủ đề thì nghiên cứu đối thủ sai theo.

## Vận hành
- Một việc nặng mỗi lúc (từng có nhiều agent chạy test toàn kho làm máy cạn RAM, treo). Việc nặng xếp hàng, không bỏ.
- Bật máy là mọi thứ tự chạy (`core/van_hanh.py`); thành phần chạy lâu phải có: đường tự bật, chó canh, dọn khoá cũ.
- Không chết im lặng: lỗi thì tự thử lại hoặc ghi "Việc của bạn" bằng câu người thường hiểu, có nhắc lại.
- Ổ đĩa < 10 GB thì dừng dựng mới và báo; video đã lên YouTube thì tự xoá tệp nặng.
- Kho clip ShopAPI có hạn mức theo ngày (VPS đầu cần ~1.000–1.400 clip/ngày cho 8 kênh) — thiếu thì hỏi chủ nạp thêm
  hay giảm nhịp, không hạ chất lượng.
