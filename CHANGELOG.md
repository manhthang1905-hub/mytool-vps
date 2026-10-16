# Nhật ký phát hành

Rút gọn từ `NHAT-KY-PHAT-TRIEN.md` (nhật ký chi tiết máy — mỗi mục có ngày,
lý do sửa, tệp đụng tới, kết quả test). Tệp này chỉ ghi TÍNH NĂNG CHÍNH, cho
người cần biết "bản mới có gì" mà không cần đọc hết nhật ký chi tiết.

## Các bản đẩy lên kho chung (tự ghi bởi `dong_bo_git day`, mới nhất ở trên)

- **2.210.0** — 2026-10-16 — `vps-jp1` — feat(danh-sach-phat): danh sach phat chu de tu dong - AI chia video theo nghia, tao tren Studio, them video CHI qua trang sua Studio (khong mo trang xem), chi video cua chinh kenh, khong dung danh sach cua chu; video moi vao dung danh sach…
- **2.209.2** — 2026-10-16 — `vps-jp1` — docs(kien-thuc): luat chu du an cho moi ngach/moi may (chat luong, cong chu bia, khong lach YouTube, hoc dung cho, van hanh) + CLAUDE.md tro toi
- **2.209.1** — 2026-10-16 — `vps-jp1` — fix(cai-dat): may moi tu dang ky du 4 lich nao hoc + ky nang (KyNang, NaoBoPhan, NaoBoPhan-Ngu, PhongThiNghiem) - truoc day dang ky tay tren VPS dau
- **2.209.0** — 2026-10-16 — `vps-jp1` — feat(van-hanh): khoi dong + tu hoi phuc - so dang ky 4 thanh phan (Qt, tram 8765, agent may dang, truc quan 8790) kiem song/bat lai khi chet, khong dung tien trinh dang dang/dung; don khoa cu sau khoi dong; bao cao khoi dong; task ShopAPI-…
- **2.208.0** — 2026-10-16 — `vps-jp1` — feat(bia): cong chu bia tuyet doi - soat chu truoc khi ve, 2 lan doc mu doc lap phai khop tung ky tu, dau chu_khop sha1, moi loi ra YouTube (dang/doi bia/A-B) tu choi bia chua dong dau; S05 dong dau goi cho; TL1 len bia_lo theo bia thang t…
- **2.207.0** — 2026-10-16 — `vps-jp1` — feat(studio-may): bo tu lam viec Studio - D13 tu bat Thu nghiem A/B hinh thu nho (ung vien qua cong do_bia, khong dung tieu de), D14 doc suc khoe kenh (gay/canh bao/noi dung dung lai, chi bao nguoi khi co that); chung cua gac DOM + van IPv4
- **2.206.0** — 2026-10-16 — `vps-jp1` — feat(viec-tu-dong): Viec cua ban chi con viec NGUOI - phan loai nguoi/may, ghim gop 1 dong + ghim bu video cu, tu doi tieu de co rao (chu duyet 16/10), tu xoa Chrome ban cu (chu duyet 16/10), de xuat nao + kiem suc khoe vao hang may co kieu
- **2.205.1** — 2026-10-15 — `vps-jp1` — fix(lam-sach): GO HAN doi cao do giong (phá SynthID am thanh = lach nhan dien AI, trai chinh sach spam YouTube) - bo ham, cong tac Cai dat va loi goi o khau giong; test khoa khong cho them lai
- **2.205.0** — 2026-10-15 — `vps-jp1` — feat(doc-dao): cong do doc dao kich ban - do % chuoi 10 ky tu chep nguon, tren 15% viet lai bang giong kenh (toi da 2 lan, khong chan luot), bien ban 1-doc-dao.json, ho so video + nao kich-ban, kenh.yaml doc_dao, CLI bao cao
- **2.204.0** — 2026-10-14 — `vps-jp1` — feat(bia-lo): lo bia theo KIEU CHU cua chinh kenh — khuon hop (TL4) giu nguyen, khuon chu tran (TL2/TL3) ve bang bo ve chu tran voi mau/vien/to mau tu khoa cua khuon, 1 dong cuc to, khong de nhan vat (nhan dau cam TL3); mau bia thang + mo …
- **2.203.0** — 2026-10-14 — `vps-jp1` — feat(ky-nang): ky nang tu kich hoat (chu 14/10: dong goi viec lam tay thanh skill tu chay khi du dieu kien) — moi skill khai dieu_kien/chay/nhip/tu_ap; bo chay tu-kich-hoat moi gio (1 viec nang/luot, giu khoa may, tranh :55-:05, 3 lan hong…
- **2.202.0** — 2026-10-14 — `vps-jp1` — feat(thiet-lap): bat tab Trang chu + video gioi thieu (nguoi chua dang ky) + video noi bat + muc Video pho bien cho TL1-4 (chu duyet 14/10), mo ta kenh TL1; co --dat-trang-chu / --dat-mo-ta / --khong-luu (chay thu)
- **2.201.0** — 2026-10-14 — `vps-jp1` — feat(thiet-lap): kiem thuong hieu (chi doc) + gan hinh mo Dang ky — TL1-4 truoc deu THIEU hinh mo, nay da gan (toan video, doc lai dung); sua chon thoi gian hinh mo (ENTIRE); kiem co dang dang do ca vm/logs
- **2.200.1** — 2026-10-14 — `vps-jp1` — fix(kenh): doc_yaml bo ky tu BOM ket giua tep (TL1-3 nhan ban tu khuon TL4 mang U+FEFF -> PyYAML hong -> lui bo doc toi gian, khoi long nhau bi lam phang lang le)
- **2.200.0** — 2026-10-14 — `vps-jp1` — feat(bia-lo): ve vai chuc bia roi chon (chu 14/10) — dao dien y tuong doc kich ban (6-8 y, 5 khuon manh moi cua bia thang: ke ra chinh danh sach / mot minh vs dam dong / ben trong dau / mat manh + viec la / bi phan xet; tranh cach hieu hie…
- **2.199.0** — 2026-10-13 — `vps-jp1` — feat(bia-khuon): bia kieu hop chu dat chuan bia thang that (chu: 'thumb xau, khong hut nhu thumb da win') — 1 dong CUC TO, phong M PLUS Rounded 1c Black (OFL, fonts/), hop do sat chu so le + bong + vien, nen vector phang sang am lay bia th…
- **2.198.0** — 2026-10-13 — `vps-jp1` — feat(nao-do-thi): ban do nao 3D phat sang (3d-force-graph 1.80.0 + three r183 UnrealBloomPass 0.85/0.55/0.12, vendor MIT) — cham sang theo bo phan (15 thuy tren 2 ban cau), co theo so lan hoc, do sang theo trang thai, vo nao ~5.900 hat tu …
- **2.197.1** — 2026-10-13 — `vps-jp1` — fix(truc-quan): chi so kenh dung nguon YPP — dang ky TRON DOI + gio xem 365 ngay + gio/ngay TB 7 ngay (truoc lay tong 28 ngay truot: TL4 564 thay 716, gio/ngay am); 'video mai' bo video da qua gio dang; gop tab Do thi nao vao tab Nao (ban …
- **2.197.0** — 2026-10-13 — `vps-jp1` — feat(viet-max): luat chu 13/10 — Claude Max HET TOKEN hoac LOI thi viet bang ShopAPI (thay luat 24/08 khong lui vi): ca thang can han muc -> lui vi ngay, hong 2 lan -> lui vi; nhan dung 'hit your weekly limit' (kem 429 truoc bi doc la nghe…
- **2.196.0** — 2026-10-13 — `vps-jp1` — fix(bia-khuon): khuon bia thang lay ca video THAT cua kenh trong chi-so (kenh chuyen may nhu TL4 khong co ho so); bang chung: CTR>=7%&>=10k HOAC >=50k hien thi & CTR>=trung vi kenh; khuon cua kenh de luat chung (co nhan vat, hop chu ve ban…
- **2.195.0** — 2026-10-13 — `vps-jp1` — feat(nao-do-thi): do thi than kinh song cua nao 15 bo phan tren 8790 (/nao-do-thi) — force-graph 1.52.0 (MIT, vendor), no-ron loi/bai hoc quanh bo phan, canh 'cung phat thi noi' theo goi/kenh-ngay, xung song tu su kien/dung/giac ngu; API c…
- **2.194.2** — 2026-10-13 — `vps-jp1` — feat(truc-quan): mo cho may CUNG MANG doc (chu 13/10 — session shopapi.vn keo du lieu day len web): workspace/truc-quan/cai-dat.json mo_lan hoac --lan -> nghe :: hai ngan xep (IPv4+IPv6), JSON co CORS *; tuong lua chi LocalSubnet; mac dinh…
- **2.194.1** — 2026-10-13 — `vps-jp1` — fix(nao-bo-phan): giac ngu bo ket qua video < 50 hien thi (YouTube khong phat — loi mail, khong phai content thua): dem dau rut 'TL5 tranh tuyen nguoi cao tuoi 3/3 truot' trong khi do la chinh ngach TL5
- **2.194.0** — 2026-10-13 — `vps-jp1` — feat(nao-bo-phan): dot 2 — giac ngu dem (ma tinh so + cap hong/duoc, Claude Max Opus chi ra lenh sua co ma su kien, ma kiem roi moi ap), canh bao tach khoi loi, thuc the khau/engine/bo chon/ma kiem, nhat ky tung bo phan, ky-lai; so tay vao…
- **2.193.1** — 2026-10-13 — `vps-jp1` — fix(dang-dom): hien_thi_trang_sua — dua bo chon tu chua ytcp-video-metadata-editor-sidepanel (khop that >=28 luot dang tu 12/10) len bo chon chinh, giu 2 bo cu du phong (nao bo phan phat hien: TU CHUA lap 28 lan)
- **2.193.0** — 2026-10-13 — `vps-jp1` — feat(nao-bo-phan): dot 1 — nao chung cho 15 bo phan: ghi su kien, gom tang dan tu cac so san co, no-ron loi (dang xay ra/tam lang/da het/tai phat), ban chieu bai hoc, so tay bo phan, chi muc FTS5, nho() ~5ms; nao xem in loi dang tang
- **2.192.0** — 2026-10-13 — `vps-jp1` — feat(doi-thu-chung): phan tang doi thu (loi/dang len/nhe/ngoai) + quet theo tang — 1812 la tri nho hop thu, khong phai so doi thu; tang 1: 60 quet hang ngay, 2: 168 ~2,4 ngay, 3: 118 hang tuan, ngoai 1466
- **2.191.0** — 2026-10-13 — `vps-jp1` — fix(ban-giao,ghim): kenh tu chay thieu thu_muc_done mac dinh DONE/<ma> (TL4-T7/0001 xong ma khong ban giao); nhan huy hieu ghim theo chu o giao dien binh luan moi (ghim that len ma bao hong)
- **2.190.1** — 2026-10-13 — `vps-jp1` — fix(kenh-khong-phat): luat chu 13/10 — can 10 video lien khong duoc phan phoi moi bao, KHONG dung san xuat (cu lam cu dang), loi bao de nghi doi mail (kenh moi tren tai khoan Google khac)
- **2.190.0** — 2026-10-13 — `vps-jp1` — feat(doi-thu-chung): so doi thu chung ca nhom (1 dong/kenh, quet + AI kiem ngach 1 lan, giu moi ghi chu tay), het quet lai khi kenh moi bat; ghi kenh-do.json theo dot (het ghi lai 27MB moi kenh); radar dot bien toan thi truong + ep chon ch…
- **2.189.0** — 2026-10-12 — `vps-jp1` — feat(sub): do sub/1k dung (bo o trong khong tinh 0), don bay chuyen doi sub cho kenh gan YPP — cau moi giua bai 25-40% + hua video tiep (A/B), MHKT bat buoc nut Dang ky, binh luan hoi + moi nhe (A/B), link video lien quan trong mo ta; nao …
- **2.188.0** — 2026-10-12 — `vps-jp1` — feat(nao+danh-muc): phat hien kenh khong duoc phat (dung san xuat moi, bao chu + danh sach kiem Studio, tu chay lai); chuong trinh nao moi (bang danh muc, radar no, san khoang trong, A/B bia, giu chan theo doan); phien nao doi quet xong; Y…
- **2.187.0** — 2026-10-12 — `vps-jp1` — feat(viet-max): moi viec chu content di Claude Max (thue bao may) model claude-opus-5-5 — ke ca nao, giam doc, bien tap, SEO, chu bia; tu dong bat khi may co CLI dang nhap; toi da 3 tien trinh; het han muc tut bac, can thang thi doi + bao,…
- **2.186.0** — 2026-10-12 — `vps-jp1` — feat(phong-thi-nghiem): dot 2 — do tang 1 cong bang (dem 1 lan, so cung o), chia khe Thompson phan tang theo kenh (kham pha 15%), luat dan dau/loai, tab Phong thi nghiem (8790), nao doc bang + de xuat gia thuyet
- **2.185.0** — 2026-10-12 — `vps-jp1` — feat(phong-thi-nghiem): dot 1 — vu tru ung vien 3 nguon + loc doi thu that, kho dac trung, so gia thuyet (7 bo cham), nhat ky bong top-10 hang ngay, do tang thi truong + ghi cong cheo, chay nguoc lich su
- **2.184.0** — 2026-10-12 — `vps-jp1` — feat(chon-content): V7 chon theo HANG top-10 + trong so theo bang chung (no 30, khuon 15, dang len 0), chia khe V7/VPH, bien tap chi phu quyet (+Brier), ep chon cua nao, kiem trung y mien bien the video thang, chu quyen vung de tai
- **2.183.0** — 2026-10-12 — `vps-jp1` — feat(bia): soat chinh ta chu bia (AI) truoc khi ve + doc lai chu tren anh; chan dai toi/khung che nhan vat; giam khao loai het thi lam lo bia moi (toi da 3), khong xuat tam 'it chu nhat'
- **2.182.0** — 2026-10-12 — `vps-jp1` — feat(thuoc-thang): mot thuoc thang chung — phan vi cung tuoi, phan tu >=96h (khong phan @48h), ban chup hop le moi nhat, dong cung sau 168h; thay o V7, tu hoc, giam doc, nao_goi_y
- **2.181.2** — 2026-10-12 — `vps-jp1` — fix(chi-so): tien ich 2.10.0 — khoa tab that (het chup chong), chi tinh co so khi dung video, nhan tuoi that, chup bu moc muon /chup-bu, so kenh TL2, ma video dau '-', bao dong so cu/rong
- **2.181.1** — 2026-10-12 — `vps-jp1` — fix(giam-doc): quyen tu ap can KY NANG (hon ti le nen >=15 diem, dung >=2 video thang) — doan 'truot' moi video dat 93% khong con duoc tu ap; bai hoc khong tu ap
- **2.181.0** — 2026-10-12 — `vps-jp1` — feat(cho-engine): luot cho engine giong ShopAPI (sap/tam dong/hang cho dai) ghi dau cho, nha lan va thoat; dieu phoi sinh lai khi toi gio tham do; khong tinh L3
- **2.180.16** — 2026-10-12 — `vps-jp1` — fix(muc-luc): chen 目次 vao cuoi phan DESCRIPTION (truoc KEYWORDS/TAGS), khong noi sau KEYWORDS — the rac 206 ky tu TL6-K2/0007
- **2.180.15** — 2026-10-12 — `vps-jp1` — fix(dang-dom): hop 'van dang kiem tra noi dung' -> Da hieu; loc the rac; lam not nhap da tai thay vi tai ban moi; lenh --hoan-tat
- **2.180.14** — 2026-10-12 — `vps-jp1` — fix(clip): canh treo 2 lan cung anh+loi nhac thi vao thang duong cuu (viet lai loi nhac, ve lai anh doi bo cuc) — anh bo cuc moi ~48' thay vi ~100'
- **2.180.13** — 2026-10-11 — `vps-jp1` — fix(su-co): 'may chu van chua tra ket qua' (job treo phia may chu) la cho tiep, khong phai CHET
- **2.180.12** — 2026-10-11 — `vps-jp1` — fix(job): ket qua job mat (download 400/404/410) — dat lai bang khoa moi toi da 2 lan; het lan thi bao loi phia may chu (mien tran L3)
- **2.180.11** — 2026-10-11 — `vps-jp1` — fix(clip): loi nhac anh lanh ma clip treo — doi bo cuc khung hinh thay vi bo ca video vi mot canh (TL1/0026 172/173 clip)
- **2.180.10** — 2026-10-10 — `vps-jp1` — fix(su-co): cau tool tu viet 'cong ShopAPI ngung nhan viec... phia may chu' la nha may nghi — L3 da bo oan TL1/0024, TL6/0006
- **2.180.9** — 2026-10-10 — `vps-jp1` — fix(tu-chay): luot dung vi phia ShopAPI (engine tat/tam nghi/het kho) mien tran 3 lan nhat lai cua L3 — TTS tat ca buoi, TL1/TL6 suyt bi bo
- **2.180.8** — 2026-10-10 — `vps-jp1` — fix(su-co): 'khong co engine nao phuc vu tts' la nha may nghi (cho, thu lai) chu khong phai CHET — tranh tran L3 bo oan luot do khi ShopAPI tat TTS
- **2.180.7** — 2026-10-10 — `vps-jp1` — fix(mhkt): chon hang phan tu MHKT duoc bam JS khi bi div#touch-area che (sua gio 20s cuoi)
- **2.180.6** — 2026-10-09 — `vps-jp1` — fix(tu-chay): cong chat luong mo lai khau clip thi xoa bo dem tu phuc hoi (tran L3 khong bo oan luot dang sua)
- **2.180.5** — 2026-10-09 — `vps-jp1` — fix(chat-luong): vuot tran 30 canh thi lam lai phan con suat (trung/den truoc, roi clip tinh) thay vi chan thang — TL2-T7-0022
- **2.180.4** — 2026-10-09 — `vps-jp1` — fix(agent): keo cheo bi chan tam (ma 4, khoa may ban) thu lai sau 30 phut, toi da 6 lan/ngay — truoc day mat ca ngay
- **2.180.3** — 2026-10-09 — `vps-jp1` — fix(agent): cho tram /loi-thoai/can-lay 120s (kenh moi mat 24s, 4 kenh moi timed out moi ngay, khong hut duoc loi thoai doi thu)
- **2.180.2** — 2026-10-09 — `vps-jp1` — fix(mhkt): Studio bao 'chi trong 20 giay cuoi' -> doi gio bat dau vao trong cua so roi Luu (TL2 that bai lap)
- **2.180.1** — 2026-10-09 — `vps-jp1` — fix(do-bia): hieu chinh vien day + nguong theo co chu; ve lai tren nen sach khong khung, khong che nhan vat; cong khong bao gio lam bia te hon goc
- **2.180.0** — 2026-10-09 — `vps-jp1` — feat(muc-luc): 6-10 chuong ten theo noi dung (AI + du phong sach), luat mo dau khong chao/xin dang ky 60s dau, tieu de 28-38 ky tu mac dinh
- **2.179.0** — 2026-10-09 — `vps-jp1` — feat(chat-luong): cong chat luong thanh pham luc ban giao — do tieng/phu de/hinh/clip tinh/mo ta, tu sua, chan; truc chat_luong; sua test vong_hoc_kin khong phu thuoc ngay
- **2.178.1** — 2026-10-09 — `vps-jp1` — test(vong-hoc-kin): khong phu thuoc ngay chay
- **2.178.0** — 2026-10-09 — `vps-jp1` — feat(bia): do do de doc anh bia (tuong phan chu/nen tung dong, co chu tren dien thoai) — ve chu theo nen (sang/toi/am-roi: doi mau, vien day, khung mo), cong chan bia kho doc (doi tam, ve lai, rut gon, khong ban giao), truc hoc bia_doc_duo…
- **2.177.1** — 2026-10-08 — `vps-jp1` — fix(ben-bi): bao 'khong san xuat' khoa theo ma goi + ngay dang — goi lam lai (cung ma, ngay moi) la video moi; het bao khan sai 36h (08/10 13:17)
- **2.177.0** — 2026-10-07 — `vps-jp1` — feat(tu-hoc): gan nhan cum theo NGHIA (LLM, nho dem, toi da 60 tieu de/luot) khi bo cum tu khoa tra rong; bu nhan hoi to cho van cu; picker luon ghi cum_tu_hoc + cum_nguon; khac la mot canh tay that
- **2.176.1** — 2026-10-07 — `vps-jp1` — fix(dieu-phoi): van nghet RAM nho so lan cu va tu tra lai khi RAM trong >=4GB lien tuc 30' — truoc day ha mot lan la ket 1 lan mai (07/10 00:02)
- **2.176.0** — 2026-10-07 — `vps-jp1` — feat(chat-luong): khong bao gio dang san pham kem — kho clip het han muc chi cho/thu lai (bo dung canh tu anh, bo giu hinh khi thieu clip), cuu canh bi tu choi noi dung roi bao nguoi; ban giao + may dang tu choi goi con clip tu anh; lenh l…
- **2.175.0** — 2026-10-07 — `vps-jp1` — fix(tu-hoc): cham ket qua muon 96-240h (kenh non duoc day muon, 48h chi ~28% so cuoi) thay vi 48h; bien tap xep video theo so muon + gan sao video thang; chu bia 10-20 ky tu (ja/zh/ko) viet lai khi lech khung; truc do chu_bia_dai, mo_dau
- **2.174.2** — 2026-10-07 — `vps-jp1` — fix(may-dang): doc view 48h them goc repo vao sys.path truoc khi nhap core — het 'No module named core' lam may dang HONG SAU khi tai len (TL1 07/10 01:07)
- **2.174.1** — 2026-10-06 — `vps-jp1` — fix(gac-tong): co tran tong thi chi bao 'qua nhieu tu_chay' khi vuot tran tong — luot cho clip quay lai lam la hop le (het bao khan sai 21:02-21:47)
- **2.174.0** — 2026-10-06 — `vps-jp1` — feat(trung-tam): vong 4 — ho so tuong (chien tich co anh bia, thang/thua 48h, du bao YPP), cay ky nang, dong ho chien dich, kinh te + kho dan anh/clip/giong, loi tien tri, tong ket tran, 32 thanh tuu, cham kenh day du
- **2.173.0** — 2026-10-06 — `vps-jp1` — feat(trung-tam): tab Gioi thieu — trinh chieu 27 trang 5 chuong (bai toan, huong di Domain Translator, cach may lam, kha thi, lo trinh), so that tu JSON, che do nguoi noi, toan man hinh; noi dung rieng may o workspace/gioi-thieu, ban mac d…
- **2.172.1** — 2026-10-06 — `vps-jp1` — fix(gac-tong): bao 'qua nhieu tu_chay' tru luot cho kho clip + tran tong 7; chi dem luot kenh (bo chinh lenh PowerShell, dieu phoi, vo cmd) — het bao khan sai 11/7
- **2.172.0** — 2026-10-06 — `vps-jp1` — feat(trung-tam): vong 2 kieu game — ban do luc giac co suong mu, ban do nho, phong/keo, ho so dich + diem yeu, chien bao (/su-kien.json), len cap/thanh tuu/mua giai, tua dien bien, xe hang tren bang chuyen + kho dan clip, hoi dong chien lu…
- **2.171.0** — 2026-10-06 — `vps-jp1` — feat(trung-tam): giao dien kieu game chien thuat — ban do chien dich (quan co, vuong mien boss, lua diem nong, mui ten tan cong), thanh tai nguyen, nhiem vu, quan doan, thanh tuu; Hau can kieu xuong; Nao kieu Tong tham muu; font/vendor off…
- **2.170.1** — 2026-10-06 — `vps-jp1` — feat(dieu-phoi): luot dang cho kho clip khong chiem lan API (dau cho-clip/<kenh>.json, pid song + tuoi <45'); tran tong 7 luot
- **2.170.0** — 2026-10-06 — `vps-jp1` — feat(clip): kho clip ShopAPI het han muc -> cho engine (20'/lan) toi han chot = gio dang - 6h, roi dung canh thieu tu chinh anh canh (Ken Burns, dung do dai); su_co HET_HAN_MUC; ho so ghi clip_tu_anh
- **2.169.0** — 2026-10-06 — `vps-jp1` — fix(gop-lai): nen gz raw chi so >7 ngay + moi noi doc raw qua kho_raw (agent P) — ban 2.164.0 da roi mat 9 tep nay; raw da nen tu 06/10 01:40 nay doc lai duoc
- **2.168.5** — 2026-10-06 — `vps-jp1` — fix(chi-so): doc so tong tu goi join (moc >=24h Studio khong con the overview), khung rong khong de + danh dau chup lai, lui moc xap xi >=22h, chot khong do duoc sau 7 ngay; bao cao tach Studio rong / cho moc
- **2.168.4** — 2026-10-06 — `vps-jp1` — fix(tram): lui cong bo qua cong khoa danh rieng (8767-8771, 8781) — tranh chiem cong may dang/binh luan lam chung thoat im lang
- **2.168.3** — 2026-10-06 — `vps-jp1` — fix(trung-tam): doi cong 8770 -> 8790 — 8770 la cong khoa may dang DOM, trung tam chiem lam may dang thoat ma 4
- **2.168.2** — 2026-10-06 — `vps-jp1` — fix(selectors): ngon_ngu_video them ko/th/id/es/pt/fr/de (phan bi mat khi hop H)
- **2.168.1** — 2026-10-06 — `vps-jp1` — docs: trung tam chi huy (3 tab), ben bi 365 ngay, keo cheo + tu chua DOM + ngon ngu tam, ban do module moi, README (agent tai lieu)
- **2.168.0** — 2026-10-06 — `vps-jp1` — test+fix (agent H, phan con lai): bo test xanh tren clone sach; may/ngach khac tieng — font Han/La-tinh, tran chu bia, muc luc theo tieng, kenh thu 2, ho so Studio tu ngach, Whisper ma ngan, xac minh/ghim Han; conftest khong ghi nhip tim th…
- **2.167.0** — 2026-10-06 — `vps-jp1` — test+fix: bo test xanh tren clone sach (28→0 loi); may/ngach khac tieng: font Han/La-tinh, ngon_ngu_video ko+, muc luc theo tieng, kenh thu 2 nhan tep trong, ho so Studio tu ngach, Whisper ma ngan, xac minh/ghim tieng Han; conftest khong gh…
- **2.166.0** — 2026-10-06 — `vps-jp1` — feat(agent): buoc keo cheo 1 lan/ngay 09-20h qua hang doi Chrome (tran 60', khong khi IPv4 mo/con khac); ky nang D08
- **2.165.1** — 2026-10-06 — `vps-jp1` — fix(keo-cheo): xac nhan tich bang mo lai hop, khong bam lan 2, ghi so da_co + do hieu qua; anh chan doan truoc khi dong hop (agent F)
- **2.165.0** — 2026-10-06 — `vps-jp1` — fix(an-toan): bo du lieu kenh that khoi test/fixture o HEAD; bo quet them token/cookie/id Studio/CSV du lieu, quet --lich-su, che khi in; .gitignore chan moi do sau (agent O)
- **2.164.1** — 2026-10-06 — `vps-jp1` — fix(keo-cheo): tim lai nut Luu moi lan bam, cho hang nut on dinh, lui sang menu ..., anh chan doan khi loi (agent F) — da hoc playlist that 2 kenh lon
- **2.164.0** — 2026-10-06 — `vps-jp1` — feat(chi-so): nen gz raw chi so cu >7 ngay, moi noi doc deu doc duoc .json.gz, chung minh ket qua giong het (agent P); gac tong xoa tep .py rong o goc che module vm/
- **2.163.1** — 2026-10-06 — `vps-jp1` — fix(keo-cheo): vm/ luon thang goc repo trong sys.path (tep .py rong o goc tung che vm/cdp_studio)
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
- **2.146.0** — 2026-10-03 — `vps-jp1` — Bo nao (kieu Hermes/Claude Code): core/nao.py CLI an toan (thu/tranh/bai-hoc/uu-tien-nguon/de-xuat, gioi han + quyen theo ti le dung, ngay kiem >= luc co so 48h), phien Claude Code chay nen 04:10 hang ngay (ShopAPI-Nao), nao/CLAUDE.md 6 bu…
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
