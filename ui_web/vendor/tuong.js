/* HỒ SƠ TƯỚNG — bấm một kênh ở bất kỳ đâu → bảng toàn màn: cấp, kinh nghiệm, quân số, dự báo YPP, lịch sử trận
   (ảnh bìa + kết quả 48 giờ), cây kỹ năng, chăm kênh. Dữ liệu: /tuong.json?kenh= (chỉ đọc). Cần chung.js. */
(function () {
  "use strict";
  const MT = window.MT, {esc, so, fmt, ic} = MT;
  const MOC_CAP = [0, 10, 50, 100, 250, 500, 1000, 2000, 3000, 4000];
  const TEN_CAP = ["Tân binh", "Tân binh", "Trinh sát", "Trinh sát", "Chiến binh", "Chiến binh", "Tinh nhuệ", "Tinh nhuệ", "Chỉ huy", "Huyền thoại"];
  MT.cap = gio => { let c = 1; MOC_CAP.forEach((m, i) => { if ((Number(gio) || 0) >= m) c = i + 1; }); return c; };
  MT.TEN_CAP = TEN_CAP; MT.MOC_CAP = MOC_CAP;
  const hue = ma => 150 + MT.bam(ma) % 80;
  const KET = {thang: ["THẮNG", "thang"], thua: ["THUA", "thua"], cho: ["CHỜ 48H", "cho"], khong_do: ["KHÔNG ĐO ĐƯỢC", "kd"]};
  const TT_KN = {dat: ["Đã mở", "dat", "check"], thieu: ["Chưa mở", "thieu", "lock"], loi: ["Hỏng", "loi", "alert"], cho: ["Đang chờ", "cho", "hourglass"], "-": ["Không áp dụng", "khong", "x"]};
  const TEN_LOAI = {khoi_tao: "Khởi tạo", dinh_ky: "Định kỳ", sua_chua: "Sửa chữa", mo_rong: "Mở rộng"};
  let DU = null, TAB = "tran", MA = "", HOOK = {};

  MT.moTuong = async (ma, hook) => {
    MA = ma; HOOK = hook || {}; TAB = "tran";
    MT.am("mo");
    const hop = MT.moHop(`<span class="mo">Hồ sơ tướng</span> ${esc(ma)}`, `<div class="trong" style="padding:40px">Đang gọi hồ sơ…</div>`, "tuong-hop");
    try { DU = await MT.taiJSON("/tuong.json?kenh=" + encodeURIComponent(ma)); } catch (e) { DU = {loi: e.message}; }
    if (!hop.isConnected) return;
    if (DU.loi) { hop.querySelector(".hop-lon-than").innerHTML = `<div class="trong" style="padding:40px">Không đọc được hồ sơ: ${esc(DU.loi)}</div>`; return; }
    ve(hop);
  };

  function ve(hop) {
    const d = DU, cs = d.chi_so || {}, y = d.ypp || {}, tt = d.thanh_tich || {};
    const gio = Number(cs.gio != null ? cs.gio : y.gio) || 0, dk = Number(cs.dang_ky != null ? cs.dang_ky : y.dang_ky) || 0;
    const c = MT.cap(gio), ke = MOC_CAP[c] || 4000, pG = MT.kep(gio / 4000, 0, 1), pS = MT.kep(dk / 1000, 0, 1);
    const nhan = MT.boMaNgan ? d.kenh : d.kenh;
    const anhDai = d.logo ? `<img src="/logo/${encodeURIComponent(d.kenh)}.png" alt="">` : `<span>${esc(String(nhan).split("-")[0])}</span>`;
    const ngayYpp = y.trang_thai === "dat" ? "Đã đủ điều kiện" : y.ngay_du_kien ? `${y.ngay_du_kien.slice(8, 10)}/${y.ngay_du_kien.slice(5, 7)}/${y.ngay_du_kien.slice(0, 4)}` : "chưa đủ số";
    const TT_YPP = {dat: "đã đạt", gan: "≤ 14 ngày nữa", dang_len: "đang lên", cham: "đang chậm", chua_du_so: "cần ≥ 3 lần chụp"};
    const tiLe = tt.ti_le, chuoi = tt.chuoi || 0;
    hop.querySelector(".hop-lon-tieu").innerHTML = `<span class="mo">Hồ sơ tướng</span> ${esc(d.kenh)}`;
    hop.querySelector(".hop-lon-than").innerHTML = `
      <div class="tg-dau" style="--h:${hue(d.kenh)}">
        <div class="tg-mat ${c >= 10 ? "huyen" : ""}">${anhDai}<b class="tg-cap">CẤP ${c}</b></div>
        <div class="tg-ten"><div class="tg-ma">${esc(d.kenh)}</div><div class="tg-jp">${esc(d.ten || "")}</div>
          <div class="tg-chip"><span class="chip vang">${ic("star")}${TEN_CAP[c - 1]}</span>${d.nhip_dang ? `<span class="chip">${ic("calendar")}lên sóng ${esc(d.nhip_dang)}</span>` : ""}
            ${tiLe != null ? `<span class="chip ${tiLe >= 50 ? "ta" : tiLe >= 25 ? "tranh" : "dich"}">${ic("trophy")}thắng ${so(tiLe, 0)}% · ${tt.thang}/${tt.so_tran}</span>` : ""}
            ${chuoi >= 2 ? `<span class="chip ${tt.chuoi_loai === "thang" ? "ta" : "dich"}">${ic(tt.chuoi_loai === "thang" ? "flame" : "trend")}chuỗi ${chuoi} ${tt.chuoi_loai === "thang" ? "thắng" : "thua"}</span>` : ""}</div>
          <div class="tg-thanh"><div class="dong"><span>KINH NGHIỆM · GIỜ XEM</span><b>${so(gio, gio < 10 ? 1 : 0)} / 4.000</b></div><div class="thanh-tien vang xp"><b style="width:${(pG * 100).toFixed(1)}%"></b></div>
            <div class="mo rat-nho">${c >= 10 ? "đủ giờ YPP" : `cấp ${c + 1} ở ${so(ke)} giờ · còn ${so(Math.max(0, ke - gio))} giờ`}</div></div>
          <div class="tg-thanh"><div class="dong"><span>QUÂN SỐ · ĐĂNG KÝ</span><b>${so(dk)} / 1.000</b></div><div class="thanh-tien hp"><b style="width:${(pS * 100).toFixed(1)}%"></b></div></div>
        </div>
        <div class="tg-ypp">${MT.vong(Math.min(pG, pS), 120, "var(--vang)", `${so(Math.min(pG, pS) * 100, 0)}%`, "YPP", 9)}
          <div class="tg-ypp-chu"><small>DỰ BÁO ĐỦ YPP</small><b>${esc(ngayYpp)}</b><span>${esc(TT_YPP[y.trang_thai] || "")}${y.toc_gio ? ` · +${so(y.toc_gio * 7, 0)} giờ/tuần` : ""}</span></div></div>
      </div>
      <div class="tg-chi">
        ${[["eye", "Xem 28 ngày", fmt(cs.xem)], ["hourglass", "Giờ xem 28 ngày", fmt(Math.round(cs.gio || 0))], ["users", "Đăng ký", fmt(cs.dang_ky)],
           ["frame", "Hiển thị 28 ngày", fmt(cs.hien_thi)], ["target", "CTR 28 ngày", cs.ctr != null ? so(cs.ctr, 2) + "%" : "—"], ["trend", "CTR trung vị (mốc đầu)", tt.ctr_trung_vi != null ? so(tt.ctr_trung_vi, 2) + "%" : "—"]]
          .map(([i, n, g]) => `<div><small>${ic(i)}${n}</small><b>${g}</b></div>`).join("")}
      </div>
      <div class="tg-tab phan-doan" role="tablist">${[["tran", "Chiến tích", "swords"], ["ky", "Cây kỹ năng", "layers"], ["cham", "Chăm kênh", "heart"]]
        .map(([k, n, i]) => `<button class="${TAB === k ? "on" : ""}" data-tab="${k}">${ic(i)} ${n}</button>`).join("")}
        ${HOOK.banDo ? `<button data-ban-do="1">${ic("map")} Xem trên bản đồ</button>` : ""}</div>
      <div class="tg-than" id="tg-than"></div>`;
    hop.querySelectorAll("[data-tab]").forEach(b => b.addEventListener("click", () => { TAB = b.dataset.tab; MT.am("bam"); hop.querySelectorAll("[data-tab]").forEach(x => x.classList.toggle("on", x === b)); veTab(hop); }));
    const bd = hop.querySelector("[data-ban-do]"); if (bd) bd.addEventListener("click", () => { MT.dongHop(); HOOK.banDo(d.kenh); });
    veTab(hop);
  }

  function veTab(hop) {
    const than = hop.querySelector("#tg-than"), d = DU;
    if (TAB === "tran") {
      const ds = d.tran || [];
      than.innerHTML = ds.length ? `<div class="tg-tran">${ds.map(t => {
        const k = KET[t.ket] || KET.cho;
        const link = t.video_id ? `https://www.youtube.com/watch?v=${encodeURIComponent(t.video_id)}` : "";
        return `<a class="tran-the ${k[1]}" ${link ? `href="${link}" target="_blank" rel="noopener"` : ""}>
          <div class="tran-anh">${t.anh ? `<img loading="lazy" src="/anh-bia/${encodeURIComponent(d.kenh)}/${encodeURIComponent(t.ma)}.jpg" alt="">` : `<span>${ic("image")}</span>`}<i class="dau-moc ${k[1]}">${k[0]}</i></div>
          <div class="tran-noi"><b title="${esc(t.tieu_de)}">${esc(t.tieu_de || t.ma)}</b>
            <div class="tran-meta"><span>${t.ngay ? esc(t.ngay.slice(8, 10) + "/" + t.ngay.slice(5, 7)) : "—"}</span>${t.hien_thi != null ? `<span>${ic("eye")}${fmt(t.hien_thi)}</span>` : ""}${t.ctr != null ? `<span>CTR ${so(t.ctr, 2)}%</span>` : ""}${t.moc ? `<span class="mo2">@${esc(t.moc)}</span>` : ""}</div></div></a>`;
      }).join("")}</div>` : '<div class="trong">Chưa có trận nào (chưa có video bàn giao).</div>';
    } else if (TAB === "ky") {
      than.innerHTML = `<div class="kn-chu">${Object.entries(TT_KN).map(([, v]) => `<span class="kn-nhan ${v[1]}">${ic(v[2])}${v[0]}</span>`).join("")}</div><div class="kn-cay" id="kn-cay"></div>`;
      veCay(than.querySelector("#kn-cay"), d.ky_nang || []);
    } else {
      const n = d.nuoi || {}, b = d.binh_luan || {}, h = d.hoc || {};
      than.innerHTML = `<div class="tg-cham">
        <div class="the-nho"><h5>${ic("eye")}Nuôi trang chủ</h5><div class="so-to">${n.pct_chu_de != null ? so(n.pct_chu_de, 0) + "%" : "—"}</div><div class="mo nho">đúng chủ đề · mục tiêu > 90%</div>
          <div class="thanh-tien ${n.pct_chu_de >= 90 ? "" : "vang"}" style="margin-top:8px"><b style="width:${MT.kep(n.pct_chu_de || 0, 0, 100)}%"></b></div>
          <div class="mo rat-nho" style="margin-top:6px">${esc({dat: "đã đạt, đã tắt nuôi", dang_nuoi: "đang nuôi"}[n.trang_thai] || n.trang_thai || "chưa bật")} · ${so(n.so_phien || 0)} phiên · ${so(n.so_lan_do || 0)} lần đo${n.luc ? " · " + esc(n.luc) : ""}</div>
          ${(n.chuoi || []).filter(x => x != null).length > 1 ? MT.spark(n.chuoi.filter(x => x != null), "var(--ta)") : ""}</div>
        <div class="the-nho"><h5>${ic("message")}Bình luận hôm nay</h5><div class="so-to">${so(b.tra_loi || 0)}</div><div class="mo nho">đã trả lời · bỏ qua ${so(b.bo_qua || 0)} · lỗi ${so(b.loi || 0)} · ${so(b.phien || 0)} phiên</div></div>
        <div class="the-nho"><h5>${ic("brain")}Tín hiệu học</h5>
          <div class="hoc-ds">${[["Ván đã ghi", h.van], ["Có kết quả", h.co_ket], ["Thiếu số 48h", h.thieu_48h, 1], ["Studio rỗng", h.studio_rong, 1], ["Chờ tới mốc", h.cho_moc], ["Không đo được", h.khong_do, 1], ["Ván không nhãn cụm", h.khong_cum, 1]]
            .map(([n2, v, xau]) => `<div><span>${n2}</span><b class="${xau && v ? "dich-c" : ""}">${v == null ? "—" : so(v)}</b></div>`).join("")}
            <div><span>Chấm ván lần cuối</span><b class="${h.van_cu_gio > 48 ? "dich-c" : ""}">${h.van_cu_gio == null ? "chưa" : so(h.van_cu_gio, 0) + " giờ trước"}</b></div></div></div>
      </div>`;
    }
  }

  /* cây kỹ năng: cột = độ sâu phụ thuộc; đường nối từ kỹ năng cần → kỹ năng sau */
  function veCay(hop, ds) {
    const theo = Object.fromEntries(ds.map(k => [k.ma, k])), sau = {};
    const sau_ = m => { if (sau[m] != null) return sau[m]; sau[m] = 0; const k = theo[m];
      const can = (k.can || []).filter(x => theo[x]); sau[m] = can.length ? 1 + Math.max(...can.map(sau_)) : 0; return sau[m]; };
    ds.forEach(k => sau_(k.ma));
    const cot = {};
    ds.slice().sort((a, b) => (a.loai > b.loai ? 1 : a.loai < b.loai ? -1 : 0) || (a.ma < b.ma ? -1 : 1)).forEach(k => { (cot[sau[k.ma]] = cot[sau[k.ma]] || []).push(k); });
    const W = 196, H = 58, GX = 64, GY = 14, so_cot = Object.keys(cot).length, cao = Math.max(...Object.values(cot).map(c => c.length));
    const vt = {};
    Object.keys(cot).forEach(ci => cot[ci].forEach((k, j) => { vt[k.ma] = [Number(ci) * (W + GX), j * (H + GY)]; }));
    const rong = so_cot * (W + GX) - GX, caoPx = cao * (H + GY) - GY;
    let svg = `<svg class="kn-day" width="${rong}" height="${caoPx}" aria-hidden="true">`;
    ds.forEach(k => (k.can || []).filter(x => vt[x]).forEach(x => {
      const [x1, y1] = vt[x], [x2, y2] = vt[k.ma], a = [x1 + W, y1 + H / 2], b = [x2, y2 + H / 2], mx = (a[0] + b[0]) / 2;
      svg += `<path class="${theo[x].tt === "dat" ? "mo-khoa" : ""}" d="M${a[0]} ${a[1]}C${mx} ${a[1]} ${mx} ${b[1]} ${b[0]} ${b[1]}"/>`;
    }));
    svg += "</svg>";
    hop.style.width = rong + "px"; hop.style.height = caoPx + "px";
    hop.innerHTML = svg + ds.map(k => { const t = TT_KN[k.tt] || TT_KN["-"], [x, y] = vt[k.ma], nguoi = (k.can || []).some(c => String(c).startsWith("nguoi:"));
      return `<div class="kn-nut ${t[1]}" data-ma="${esc(k.ma)}" style="left:${x}px;top:${y}px;width:${W}px;height:${H}px" tabindex="0">
        <span class="kn-ic">${ic(t[2])}</span><div style="min-width:0"><small>${esc(k.ma)} · ${esc(TEN_LOAI[k.loai] || k.loai)}${nguoi ? " · cần người" : ""}</small><b>${esc(k.ten)}</b></div></div>`; }).join("");
    hop.querySelectorAll(".kn-nut").forEach(e => {
      const k = theo[e.dataset.ma], t = TT_KN[k.tt] || TT_KN["-"];
      const tip = ev => MT.tip(`<h4>${esc(k.ma)} · ${esc(k.ten)}</h4><div style="margin-bottom:6px"><span class="chip">${t[0]}</span></div><div class="mo" style="margin-bottom:6px">${esc(k.mo_ta || "")}</div>
        ${k.ghi_chu ? `<div class="dong"><span>Kiểm</span><b style="max-width:220px;text-align:right">${esc(k.ghi_chu)}</b></div>` : ""}
        ${(k.can || []).length ? `<div class="dong"><span>Cần trước</span><b>${k.can.map(esc).join(", ")}</b></div>` : ""}
        ${k.lenh ? `<div class="mo rat-nho" style="margin-top:6px;font-family:var(--f-ma)">${esc(k.lenh)}</div>` : ""}`, ev);
      e.addEventListener("pointerenter", tip); e.addEventListener("pointermove", MT.tipDoi); e.addEventListener("pointerleave", MT.tipAn);
      e.addEventListener("focus", () => { const r = e.getBoundingClientRect(); tip({clientX: r.right, clientY: r.top}); }); e.addEventListener("blur", MT.tipAn);
    });
  }
})();
