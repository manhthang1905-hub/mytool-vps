# Nhật ký phát hành

Rút gọn từ `NHAT-KY-PHAT-TRIEN.md` (nhật ký chi tiết máy — mỗi mục có ngày,
lý do sửa, tệp đụng tới, kết quả test). Tệp này chỉ ghi TÍNH NĂNG CHÍNH, cho
người cần biết "bản mới có gì" mà không cần đọc hết nhật ký chi tiết.

## Các bản đẩy lên kho chung (tự ghi bởi `dong_bo_git day`, mới nhất ở trên)

- **2.163.0** — 2026-10-06 — `vps-jp1` — feat(tu-hoc+keo-cheo): vong hoc kin — nhan chuan, ket qua so trung vi 48h/CTR, lenh chien truong vao chon content (+30% toi da), nao thay ket qua lan thu, bai hoc vao loi nhac tieu de/bia, canh bao hoc (agent J); playlist tu tim: ho-so/thi…
- **2.162.0** — 2026-10-06 — `vps-jp1` — feat(ben-bi): kiem toan chay 1 nam — gac tong boc loi tung buoc + nhip tim + han 40', don khoa PID chet an toan, hoi sinh agent, bao dong mot lan/ngay + Telegram thu lai, kiem import vm/ truoc cap nhat, agent chay_ben (agent I)
- **2.161.0** — 2026-10-06 — `vps-jp1` — feat(trung-tam): tab Nao — bang diem, dong suy nghi, hanh dong+du doan+cham, tri nho, bai hoc (agent L); bao cao ngay tach hom nay/ngay mai; K17 khong ap khi trang chu tin cay
- **2.160.0** — 2026-10-06 — `vps-jp1` — feat(don-dia): don file nang video da len (them 8-nhac-nen), xoay log theo co, van o 10GB bao dong 24h/lan, nhip don tu gac tong (agent G)
- **2.159.0** — 2026-10-06 — `vps-jp1` — feat(keo-cheo): keo view cheo qua danh sach phat kenh lon (ke hoach core/keo_cheo + may DOM vm/keo_cheo_dom, agent F); chien truong chia dat theo vong, phat trung vung
- **2.158.1** — 2026-10-06 — `vps-jp1` — feat(chien-truong): chia vung AI hang ngay cho video doi thu moi; de bai/ten ngach lay tu ngach.yaml (may khac chu de khac); bao cao ngay gop kenh cung trang thai
- **2.158.0** — 2026-10-06 — `vps-jp1` — feat: tu chua bo chon DOM Studio bang AI (agent A) + bao cao suc khoe hang ngay qua Telegram (agent E)
- **2.157.1** — 2026-10-06 — `vps-jp1` — test(nao_goi_y): tieu de gia, khong dung tieu de kenh that
- **2.157.0** — 2026-10-06 — `vps-jp1` — feat(nao): muc VIEC BAT BUOC XEM — nhan ban video thang, gach bai hoc bi bac bo (agent D); test nao khong phu thuoc ngay
- **2.156.0** — 2026-10-06 — `vps-jp1` — feat(chien truong): lich su thi phan theo ngay + bieu do, diem co hoi tung vung (thang mu), lenh tac chien cho tung kenh (agent C)
- **2.155.0** — 2026-10-06 — `vps-jp1` — feat(ypp): du bao ngay dat 4000h/1000 dang ky moi kenh, canh bao khi gan/dat, skill D07 (agent B)
- **2.154.0** — 2026-10-06 — `vps-jp1` — feat(chien truong): ban do thi phan nhu tran danh - quy mo ngach/thang, thi phan ta, BXH doi thu, diem nong, quan ta; AI chia vung theo nghia + gop vung
- **2.153.1** — 2026-10-05 — `vps-jp1` — chore: dua ui_web/ (trang truc quan) vao danh sach trang
- **2.153.0** — 2026-10-05 — `vps-jp1` — feat(truc quan): Trung tam truc quan chi doc - day chuyen isometric, the kenh, chi tiet, su kien (core/truc_quan.py + ui_web/truc-quan.html, cong 8770)
- **2.152.4** — 2026-10-05 — `vps-jp1` — fix(quet ngay): kenh moi chua co bang theo ngay (Studio tre) ma bang tom tat da ve = du; het quet lap 3 lan/ngay
- **2.152.3** — 2026-10-05 — `vps-jp1` — fix(ky nang): tu hoc kenh san xuat may khac = khong ap
- **2.152.2** — 2026-10-05 — `vps-jp1` — chore(ky nang): OAuth/token = khong dung (binh luan DOM); mo ta D03
- **2.152.1** — 2026-10-05 — `vps-jp1` — feat(binh luan DOM): tra loi dung NOI DUNG video (loi thoai tu phu de goi), dung ngon ngu kenh (viet lai neu sai), khong kaomoji, khong sua lung khan gia
- **2.152.0** — 2026-10-05 — `vps-jp1` — fix(vong hoc): khe nang ban chi doi kho nhac, van hoc tu so lieu (TL1-3 khong hoc tu 03/10); feat: danh muc skill core/ky_nang + docs/KY-NANG.md; token hong -> binh luan DOM; kho bi mat DPAPI
- **2.151.1** — 2026-10-05 — `vps-jp1` — fix(dang dom): doc ten danh sach phat o li/label (o tick khong co chu) - truoc day video kenh moi luon vao danh sach dau
- **2.151.0** — 2026-10-05 — `vps-jp1` — feat(dom): ngon ngu hien thi kenh giu dung nuoc kenh; may dang/binh luan TAM dung vi roi TRA lai (logs/hl-tam, ben khi chet giua chung) - chay duoc moi ngon ngu VPS
- **2.150.6** — 2026-10-05 — `vps-jp1` — feat(thiet lap kenh): dia diem xem la buoc 1 lan cua skill (youtube.com avatar -> Dia diem -> nuoc kenh, doc lai menu); may dang chi kiem giao dien; sua nhan nut avatar vi
- **2.150.5** — 2026-10-05 — `vps-jp1` — feat(dang dom): dat dia diem xem YouTube (cookie PREF gl) theo nuoc cua kenh (ngon_ngu noi dung / dia_diem_xem) moi lan vao Studio
- **2.150.4** — 2026-10-05 — `vps-jp1` — fix(bia): goc_* khong chep ngoai hinh nhan vat doi thu - chi vi tri/co/dang; doc bia doi thu khong ta toc/mat/quan ao
- **2.150.3** — 2026-10-05 — `vps-jp1` — fix(tu chay): luot da dung xong ma chua ban giao (tien trinh chet giua ban giao) duoc nhat lai de ban giao bu
- **2.150.2** — 2026-10-05 — `vps-jp1` — fix(ban giao): AI chon danh sach phat co tran 120s - ShopAPI treo khong giu khe nang/chan ban giao
- **2.150.1** — 2026-10-05 — `vps-jp1` — fix(the): so moc the theo giay MM:SS:FF, cho lech 1 khung hinh (truoc day chua the nao duoc luu)
- **2.150.0** — 2026-10-05 — `vps-jp1` — fix(dang dom): tu ep Studio ve tieng Viet (cookie PREF hl=vi) truoc khi dang; nhan chu xu ly tieng Nhat lam bang chung tai xong
- **2.149.26** — 2026-10-05 — `vps-jp1` — Quet ngay: kenh chi bi doi du so lieu khi da co video CONG KHAI (lich da qua), khong phai chi moi tai len
- **2.149.25** — 2026-10-05 — `vps-jp1` — Bo nao: luat ghi ngay bai hoc bi bac bo/xac nhan (khong tinh quota), nhan ban video thang lon khi con nong
- **2.149.24** — 2026-10-04 — `vps-jp1` — dat_ngon_ngu: them duong cookie PREF hl (code)
- **2.149.23** — 2026-10-04 — `vps-jp1` — dat_ngon_ngu: duong du phong cookie PREF hl=<dich> (giu cap khac) khi tai khoan Google da doi ma Studio van chua doi
- **2.149.22** — 2026-10-04 — `vps-jp1` — fix(thiet lap kenh): Xuat ban that bai khong bao DAT sai (bang chung anh cong khai + doc loi Studio), bo ten/handle khi bi chan, --mo-lai giu tu choi, nut Luu ngon ngu dung dich
- **2.149.21** — 2026-10-04 — `vps-jp1` — Nuoi trang chu: chi bam Khong quan tam khi chac chan lac de (khac ngon ngu, hoac LLM noi khong phai tam ly) - tranh bam nham video tam ly lech ngach
- **2.149.20** — 2026-10-04 — `vps-jp1` — Nhip tim: ghi trong luc cho extension cao Studio (~25 phut) de bo canh khong khoi dong lai nham agent luc quet dem
- **2.149.19** — 2026-10-04 — `vps-jp1` — fix(agent): nhip tim + gac tong dung agent treo; luong canh tien trinh con nuoi/thiet lap; tran 120 phut
- **2.149.18** — 2026-10-04 — `vps-jp1` — Thiet lap kenh: danh muc mac dinh tai len luon la Giao duc (khong de LLM chon), kenh.yaml danh_muc de doi neu can
- **2.149.17** — 2026-10-04 — `vps-jp1` — Nuoi trang chu: noi dung khac quoc gia/ngon ngu = lac de (chan bang ma: kenh Nhat tieu de khong kana); bam Khong quan tam dau phien va moi lan ve trang chu (toi da 30/phien)
- **2.149.16** — 2026-10-04 — `vps-jp1` — Canh bao kiem DOM: ket qua HONG cu hon mot luot dang thanh cong cua kenh thi het hieu luc (kenh moi bi bao khan moi gio)
- **2.149.15** — 2026-10-04 — `vps-jp1` — Nuoi trang chu: do % chu de ngay dau phien va giua phien (truoc day chi do cuoi phien, phien hay bi ngat nen khong co lan do nao); dat ngay dau phien thi dung
- **2.149.14** — 2026-10-04 — `vps-jp1` — Thiet lap kenh: Studio tu choi doi ten/handle (gioi han 2 lan/14 ngay cua YouTube) -> cho 14 ngay roi tu thu lai, khong bat nguoi; khong mo Chrome moi ngay khi chi con ten/handle cho
- **2.149.13** — 2026-10-04 — `vps-jp1` — Dong Chrome kenh: tat launcher Portable con sot sau khi Chrome dong sach (loi 'Chrome dang chay nhung khong co cong DevTools' ma 3 o kenh moi)
- **2.149.12** — 2026-10-04 — `vps-jp1` — Mo kenh tu dong (core/mo_kenh: de-xuat/chuan-bi/kich-hoat) + ngon ngu tai khoan theo quoc gia (ngon_ngu_tai_khoan_dich) + mau ngay/nut Studio tieng Nhat
- **2.149.11** — 2026-10-04 — `vps-jp1` — Studio tiếng Việt: bước ngôn ngữ tài khoản (thiet_lap_kenh_dom) + đọc ngày kiểu Hàn '2026. 10. 5.' (may_dang_dom) + test
- **2.149.10** — 2026-10-04 — `vps-jp1` — May dang DOM: nhan chu trang thai Studio tieng Han (TL6-T7-K2 Studio tieng Han, ket o 'tien do ?')
- **2.149.9** — 2026-10-04 — `vps-jp1` — Tai bo sung: hut khoa thi thu lai moi phut (co uu tien tai len song 5 phut, truoc day doi 25 phut nen co het han)
- **2.149.8** — 2026-10-04 — `vps-jp1` — Agent: tai bo sung chay TRUOC quet ngay (dang dung gio > quet Studio); test phien cap nhat cho kenh moi chua co video
- **2.149.7** — 2026-10-04 — `vps-jp1` — Tai bo sung: tai xong ma con kenh khac cho thi lam ngay kenh ke (khong doi 25 phut) - 7 kenh
- **2.149.6** — 2026-10-04 — `vps-jp1` — May dang DOM: kenh moi chua co video nao thi danh sach trong khong chan tai len (truoc day hong_truoc ma 3)
- **2.149.5** — 2026-10-04 — `vps-jp1` — uu tien tai len hon san xuat (co cho-tai-len trong khe), nuoi trang chu theo CPU<75%, cong tac Nuoi trang chu trong cai dat kenh
- **2.149.4** — 2026-10-04 — `vps-jp1` — Quet ngay: chi cao trang chu kenh tin cay (kenh.yaml trang_chu_tin_cay: true, hoac lan do nuoi trang chu gan nhat > 90% chu de) - trang chu kenh moi linh tinh la du lieu rac
- **2.149.3** — 2026-10-04 — `vps-jp1` — Kiem DOM: kenh moi chua co video thi danh sach trong khong bi bao HONG hang_video/hang_tieu_de
- **2.149.2** — 2026-10-04 — `vps-jp1` — Quet ngay: kenh moi chua co video nao thi khong coi la CHUA DU (tranh quet lai 3 lan/ngay giu Chrome + khe nang vo ich)
- **2.149.1** — 2026-10-04 — `vps-jp1` — Ghep kenh vao may dang: kenh chua co may-ao.json tu bat tu_dang + cach_dang tu_dong (4 kenh moi lam xong video ma may dang bo qua)
- **2.149.0** — 2026-10-04 — `vps-jp1` — Tu dong hoa dot 1: loc Viec cua ban (cho so -> nhat ky, xem Studio -> bo nao), giam doc tu nang/ha quyen theo thanh tich, cuu_ctr tu ap kenh <1000 sub, de-xuat nao het han 7 ngay, lich tat tu dang ky lai
- **2.148.4** — 2026-10-04 — `vps-jp1` — Bo nao: de cu uu-tien-nguon chi tinh da dung khi link that su co trong danh sach ung vien; vang 3 luot thi dong khong tinh diem
- **2.148.3** — 2026-10-04 — `vps-jp1` — xep_lich: goi 'Bo' khong giu khe va khong tinh vao kho dem (TL6-T7-K2 bo vi trung nguon van chan san xuat)
- **2.148.2** — 2026-10-04 — `vps-jp1` — fix: chong trung nguon khi nhan nuoi luot mo coi + luot thu khong thanh mo coi
- **2.148.1** — 2026-10-04 — `vps-jp1` — thiet_lap_kenh: doc lai handle theo trang cong khai, doi o anh dung cham, sua bo chon danh sach phat
- **2.148.0** — 2026-10-04 — `vps-jp1` — Thiet lap kenh tu dong (core/thiet_lap_kenh ho so: ten/handle/mo ta SEO/tu khoa/danh sach phat/mac dinh tai len + logo/banner/hinh mo; vm/thiet_lap_kenh_dom dien Studio, doc lai xac nhan, chi doi muc khac, luat doi ten/handle; agent tu cha…
- **2.147.1** — 2026-10-03 — `vps-jp1` — Nuoi trang chu: chong loi NoneType khi trinh phat chua nap/dang quang cao
- **2.147.0** — 2026-10-03 — `vps-jp1` — Nuoi trang chu (cong tac nuoi_trang_chu): Chrome kenh xem video doi thu THANG (view>=30k va >=2x trung vi kenh do, <=60 ngay), 70% ngach/30% chu de, tat tieng, thoi luong ngau nhien, Khong quan tam muc lac de; dat >90% chu de thi tu tat; s…
- **2.146.0** — 2026-10-03 — `vps-jp1` — Bo nao (kieu Hermes/Claude Code): core/nao.py CLI an toan (thu/tranh/bai-hoc/uu-tien-nguon/de-xuat, gioi han + quyen theo ti le dung, ngay kiem >= luc co so 48h), phien Claude Code headless 04:10 hang ngay (ShopAPI-Nao), nao/CLAUDE.md 6 bu…
- **2.145.0** — 2026-10-03 — `vps-jp1` — Vong tu hoc dot 3: so bai hoc co bo dem cong/tru (kieu ExpeL/ACE, delta <=3 thao tac/video, that khi >=3 video xac nhan, chu gach = bo); hieu chinh du doan bien tap (lech CTR/AVD, ti le dung) dua vao loi nhac + so do chinh xac
- **2.144.0** — 2026-10-03 — `vps-jp1` — Vong tu hoc dot 2: truc kieu_tieu_de + hook (nhan theo nghia do LLM tra kem luc cham, regex chi la duong lui), Thompson he so 0.9-1.1 khi chon tieu de/hook/kieu bia, ghi nhan vao ho so + van
- **2.143.0** — 2026-10-03 — `vps-jp1` — Vong tu hoc dot 1 (kieu AI co vua): core/tu_hoc ghi van (nuoc di + du doan) luc ban giao, cham ket qua 48h/7 ngay (gio xem), bang diem Beta + tien nghiem nhom, Thompson sampling he so cum 0.8-1.2 trong xep hang nguon
- **2.142.0** — 2026-10-03 — `vps-jp1` — Giao dien VPS moi (cot icon, danh sach kenh, tab, cot phai Viec cua ban/Canh bao/Sap dang, dai trang thai); san xuat dung han (M1 chon content cho khe M2, san_xuat_truoc_gio); tai bo sung ghi ly do khi het luot; bang dieu hanh: lich tiep t…
- **2.141.8** — 2026-10-01 — `vps-jp1` — feat: tu chon danh sach phat theo de tai (kenh.yaml danh_sach_phat_kenh -> cot Danh sach phat -> may dang)
- **2.141.7** — 2026-10-01 — `vps-jp1` — doi thu: ba duong vao mot cua duyet, 4 dieu kien, trang thai het tu hoi sinh, co AI (thi giac)
- **2.141.6** — 2026-10-01 — `vps-jp1` — feat(tong giam doc): LUAT SO KENH theo do lon thi truong + kenh -K2 la kenh YouTube rieng - tong.py: so_kenh_toi_da (nguon no/thang / 15, chi khi trang chu len/on dinh), bang_so_kenh (tep -> toi da / dang co / de xuat mo, kenh thu 2+ cho k…
- **2.141.5** — 2026-10-01 — `vps-jp1` — Máy đăng: video làm xong tải + hẹn lịch luôn (cửa sổ 7 → 30 ngày)
- **2.141.4** — 2026-10-01 — `vps-jp1` — Dọn: video đã lên YouTube là xoá ngay file nặng + ảnh; gói Bỏ xoá ngay
- **2.141.3** — 2026-10-01 — `vps-jp1` — Gọn luật dọn DONE (một luật 3 ngày) + van ổ 10 GB
- **2.141.2** — 2026-10-01 — `vps-jp1` — Dọn DONE sau khi đăng + chặn ổ đầy + trần theo ổ
- **2.141.1** — 2026-10-01 — `vps-jp1` — Giãn lịch đăng theo nhịp ngày + dời lịch video đã hẹn + sản xuất theo nhịp
- **2.141.0** — 2026-10-01 — `vps-jp1` — Cứu video CTR thấp (đổi tiêu đề/bìa, duyệt 3 lần đầu) + vá lỗ bản chụp + giờ online + bìa
- **2.140.2** — 2026-10-01 — `vps-jp1` — Trang chủ: lưu CSV thử lại khi tệp đích đang bị mở (WinError 5 làm hỏng lượt nghiên cứu TL2)
- **2.140.1** — 2026-10-01 — `vps-jp1` — Phòng điều hành: ẩn việc ghim khi kênh tắt ghim; nút Sai loại bài học mọi nguồn khỏi lời nhắc; số 1709.0 → 1709
- **2.140.0** — 2026-10-01 — `vps-jp1` — Bảng điều khiển: phòng điều hành công ty
- **2.139.0** — 2026-10-01 — `vps-jp1` — Đội chuyên gia + hội đồng quyết định + sổ độ chính xác; sửa đo công suất cửa sổ gần
- **2.138.0** — 2026-10-01 — `vps-jp1` — Công ty YouTube (gọn): khám nghiệm video + bài học + tổng giám đốc gợi ý
- **2.137.2** — 2026-10-01 — `vps-jp1` — Ví: chi ngày theo số thật (độ tụt ví/chi phí lượt), cảnh báo đúng số ngày còn
- **2.137.1** — 2026-10-01 — `vps-jp1` — Gác tổng: cảnh báo 'hẹn lịch chưa tải' chỉ KHẨN khi còn ≤3 giờ (bớt báo động nhiễu)
- **2.137.0** — 2026-10-01 — `vps-jp1` — Giám đốc kênh: nối vào gác tổng/biên tập/hồ sơ; sửa ngưỡng thắng kênh ít video; TL3 chế độ gợi ý
- **2.136.1** — 2026-10-01 — `vps-jp1` — Golden giữ LF trên clone Windows (.gitattributes)
- **2.136.0** — 2026-10-01 — `vps-jp1` — VPS mới: khởi tạo ngách bằng AI + bỏ chỗ cứng Nhật
- **2.135.0** — 2026-10-01 — `vps-jp1` — Giám đốc kênh: gói lõi + 5 plugin đợt 1 (chưa nối)
- **2.134.1** — 2026-10-01 — `vps-jp1` — Máy đăng: bù MHKT video cũ giờ vắng
- **2.134.0** — 2026-10-01 — `vps-jp1` — Gọn kho: một README, một bộ luật, 3 tài liệu; bỏ luồng cài ZIP cũ
- **2.133.3** — 2026-10-01 — `vps-jp1` — Gọn kho: bỏ mã chết, công cụ cũ, bản trùng; README mới
- **2.133.2** — 2026-09-30 — `vps-jp1` — Máy đăng: quét ngày độc lập, MHKT dựng từ mẫu, chờ tải xong 100% + hậu kiểm
- **2.133.1** — 2026-09-30 — `vps-jp1` — docs(nhieu-vps): thêm dòng xem nhanh phiên bản (bản vá thử đường tự cập nhật)
- **2.133.0** — 2026-09-30 — `vps-jp1` — feat(cap-nhat): một hệ cập nhật git duy nhất — day tự nâng phiên bản + CHANGELOG + tag; máy tự kiểm ~30' và tự nhận bản mới lúc rảnh (mặc định bật, tắt trong Cài đặt); khung Cập nhật trên giao diện; bỏ lịch 03:40; A17 kho đọc cap-nhat.json

## [3.0.0-dev] — 22/09/2026 – 29/09/2026

Chuẩn bị phát hành v3.0 (sản phẩm nhiều VPS, nhiều ngách) — xem
`workspace/LO-TRINH-PHAT-HANH-V3.md` cho lộ trình đầy đủ.

### Giao diện & vận hành VPS

- Thiết kế lại giao diện VPS: gộp 6 tab rời thành trang **Trung tâm**, sau
  đó thành **Bảng điều khiển** — mở tool trả lời ngay ba câu "kênh có ổn
  không / tôi cần làm gì / kết quả ra sao" (khối Việc của bạn, Dòng máy,
  Thẻ kênh lớn theo từng kênh, xem `README-VPS.md`).
- Gộp toàn bộ thư mục VPS về một `MyTool\` duy nhất (bỏ cấu trúc nhiều thư
  mục rời rạc của bản trước).
- Bảng điều khiển: cảnh báo Windows sắp hết hạn, sửa 5 lỗi phát hiện trên
  dữ liệu thật sau khi khởi động lại máy.
- Cài VPS từ bản clone git thẳng (`CAI-DAT-VPS.bat` + `vm/cai_dat_tu_kho.py`,
  MỚI) — thay thế cho phải đóng gói `vm/goi-vps/` trên máy nhà rồi chép
  sang; thêm `websocket-client` (từng thiếu, làm máy đăng DOM hỏng trên máy
  sạch), lùi nguồn tải cho máy chỉ IPv6. Đi kèm `core/kiem_may.py` — bảng
  OK/THIẾU kiểm máy đã sẵn sàng tự chạy chưa.
- `.gitignore` vá lỗ lọt dữ liệu riêng máy/kênh (nhật ký kênh thật, hồ sơ
  video, trạng thái `vm/`); đổi chặn hồ sơ trình duyệt kênh sang chặn THEO
  CẤU TRÚC (`Data/profile`, `App/Chrome-bin`) thay vì theo tên `TL*`.
- Tài liệu vận hành mới: `README-VPS.md`, `docs/THEM-KENH.md`,
  `docs/DOI-CHU-DE.md`, `docs/BAN-DO-MODULE.md`.

### Điều phối tài nguyên (nền tảng cho nhiều kênh/nhiều VPS)

- Đo công suất thật của máy (`core/cong_suat.py`) trước khi sửa điều phối —
  số nền để so sánh trước/sau.
- Tách lớp song song **API** (gọi máy chủ, chạy song song nhiều làn) và
  **nặng** (Chrome/FFmpeg/Whisper, độc quyền một lượt) — sửa nút thắt từng
  ép mọi việc VPS về song song = 1, kéo dài khâu ảnh gấp nhiều lần.
- Khe tài nguyên liên tiến trình + hàng đợi ưu tiên P0–P4 + đệm sổ job dùng
  chung toàn máy (`core/khe.py`, `core/uu_tien.py`, `core/so_job_chung.py`,
  `core/bang_thong.py`) — module mới, thuần, sẵn sàng để nối vào bộ điều
  phối chính ở đợt kế tiếp.

### Sản xuất & chất lượng nội dung

- Sản xuất theo đúng nhịp đăng, tự ghi nhận khi có người đăng tay, tự phục
  hồi khi lượt trước dở dang.
- Một hàng đợi tuần tự cho toàn VPS — chặn hai lượt việc NẶNG chạy chồng
  nhau (Chrome + FFmpeg cùng lúc từng làm máy đơ).
- `core/bai_hoc_san_xuat.py` (MỚI) — vòng phản hồi: kênh tự học từ video đã
  đăng để cải thiện lượt sau.
- `core/qa_truoc_dang.py` (MỚI) — cổng kiểm chất lượng trước khi bàn giao
  cho máy đăng, chặn video lỗi lọt lên kênh thật.
- Hồ sơ video + vòng học chạy trước MỖI lượt sản xuất (không chỉ sau).
- Khuôn ảnh bìa "thắng" + giám khảo AI tự chọn ảnh bìa tốt nhất trong nhiều
  bản.
- N bản tiêu đề mỗi video + chấm điểm CTR dự đoán; kiểm trùng Ý TƯỞNG bằng
  LLM (không chỉ trùng chữ).
- Kho nhạc nền chuẩn hoá tăng dần (`core/kho_nhac.py`), dựng video theo
  PHẦN (nghỉ giữa phần, chuyển cảnh, nhạc đổi theo phần, phụ đề/mục lục
  đồng bộ).
- Chặn vượt cửa nhịp đăng + chống làm trùng nội dung theo TIÊU ĐỀ.

### Đăng video & bình luận

- **Máy đăng DOM/CDP** (MỚI) — đăng video qua Chrome DevTools Protocol thay
  vì chỉ giả lập chuột/phím; nối vào phiên kênh (`vm/agent.py`), trạm nội
  bộ, và kế hoạch đăng (`core/ke_hoach_dang.py`); đã thử đăng thật liên
  tiếp trên kênh thật.
- Máy đăng: dò ảnh đa tỉ lệ (sửa lỗi 0/1 mã im lặng), dẹp vật cản (hộp xin
  quyền, lỗi End Screen), bỏ lệnh xoá đệ quy `%TEMP%` nguy hiểm.
- Nhường phiên kênh cho `vm/agent.py` đúng trước giờ đăng — không để lượt
  sản xuất nặng giữ máy tới lỡ giờ.
- Tự nhận diện video đã đăng (không đứng im chờ mãi vì "quên" một gói).
- Báo động Telegram bền vững khi có sự cố cần người can thiệp.
- Bật tự động hoàn toàn cho các kênh đã qua thử nghiệm DOM đạt yêu cầu; hỗ
  trợ tải lên bổ sung trong ngày (không chỉ một lượt cố định).

### Dọn dẹp & xử lý sự cố

- Dọn hậu quả sau khi bỏ thư mục khuôn `_KHUON`/`_MAU-GON`; mở rộng cơ chế
  dọn đĩa (không chờ "đã đăng" mới dọn, có luật dọn sớm hơn).
- Lượt sản xuất "kẹt" tự phát hiện và tự xử lý (bốn mức xử lý khác nhau
  theo mức độ kẹt); sửa hai lỗi thật phát hiện sau khi triển khai.

---

Bản trước (2.x) — xem lịch sử `NHAT-KY-PHAT-TRIEN.md` trước ngày 22/09/2026.
