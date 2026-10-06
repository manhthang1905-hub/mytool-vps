/* BẢN ĐỒ CHIẾN DỊCH lục giác — mỗi vùng đề tài là một cụm ô lục giác (số ô ∝ lượt xem/tháng), bố cục tất định
   (cùng dữ liệu → cùng bản đồ), sương mù chiến tranh, phóng/kéo/vừa khung, bản đồ nhỏ. Không thư viện ngoài. */
(function () {
  "use strict";
  const MT = window.MT, NS = "http://www.w3.org/2000/svg";
  const S = 20, R3 = Math.sqrt(3), HW = S * R3, SO_O = 300;
  const DINH = [0, 1, 2, 3, 4, 5].map(k => { const a = Math.PI / 180 * (60 * k - 90); return [S * Math.cos(a), S * Math.sin(a)]; });
  // cạnh k (đỉnh k → k+1) giáp ô láng giềng nào — lưới «odd-r» (hàng lẻ lệch phải nửa ô): ĐB, Đ, ĐN, TN, T, TB
  const KE = [[[0, -1], [1, 0], [0, 1], [-1, 1], [-1, 0], [-1, -1]], [[1, -1], [1, 0], [1, 1], [0, 1], [-1, 0], [0, -1]]];
  const tamO = (c, r) => [HW * (c + 0.5 * (r & 1)), S * 1.5 * r];
  const khoa = (c, r) => c + "," + r;
  const nhieu = s => (MT.bam(s) % 1000) / 1000;
  const f1 = v => Math.round(v * 10) / 10;

  function squarify(items, x, y, w, h) {
    const out = [], tong = items.reduce((s, i) => s + i.v, 0); if (!tong) return out;
    const sc = (w * h) / tong; let ds = items.map(i => ({...i, a: i.v * sc}));
    const worst = (row, side) => { const s = row.reduce((t, r) => t + r.a, 0), mx = Math.max(...row.map(r => r.a)), mn = Math.min(...row.map(r => r.a));
      return Math.max(side * side * mx / (s * s), (s * s) / (side * side * mn)); };
    while (ds.length) {
      const side = Math.min(w, h); let row = [ds[0]], i = 1;
      while (i < ds.length && worst(row.concat([ds[i]]), side) <= worst(row, side)) { row.push(ds[i]); i++; }
      const s = row.reduce((t, r) => t + r.a, 0);
      if (w >= h) { const cw = s / h; let cy = y; for (const r of row) { const ch = r.a / cw; out.push({...r, x, y: cy, w: cw, h: ch}); cy += ch; } x += cw; w -= cw; }
      else { const ch = s / w; let cx = x; for (const r of row) { const cw2 = r.a / ch; out.push({...r, x: cx, y, w: cw2, h: ch}); cx += cw2; } y += ch; h -= ch; }
      ds = ds.slice(i);
    }
    return out;
  }

  /* Bố cục: đảo hình bầu dục, hạt giống theo treemap, các vùng «mọc» đồng thời tới đủ số ô. */
  function boCuc(dsVao) {
    const ds = dsVao.slice().sort((a, b) => b.v - a.v || (a.ma < b.ma ? -1 : 1));
    const tong = ds.reduce((s, z) => s + z.v, 0) || 1;
    const n = ds.map(z => Math.max(2, Math.round(SO_O * z.v / tong))), Tt = n.reduce((a, b) => a + b, 0);
    let R = Math.max(5, Math.ceil(Math.sqrt(Tt * 1.12 / 0.785 / 1.33))), C, o;
    for (let lan = 0; lan < 12; lan++, R++) {
      C = Math.max(7, Math.ceil(R * 1.33)); o = new Map();
      const Wp = HW * C, Hp = S * 1.5 * R, cx = Wp / 2 - HW / 2, cy = Hp / 2 - S * .75;
      for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) {
        const [x, y] = tamO(c, r), k = khoa(c, r);
        if (((x - cx) / (Wp / 2)) ** 2 + ((y - cy) / (Hp / 2)) ** 2 <= 1 + (nhieu("bo" + k) - .5) * .24) o.set(k, {c, r, x, y, k});
      }
      if (o.size >= Tt * 1.04) break;
    }
    const lang = q => KE[q.r & 1].map(([dc, dr]) => khoa(q.c + dc, q.r + dr));
    const chu = new Map(), dem = n.map(() => 0), bien = ds.map(() => new Set()), hat = [];
    const nhan = (k, i) => {
      chu.set(k, i); dem[i]++; bien.forEach(b => b.delete(k));
      for (const kk of lang(o.get(k))) if (o.has(kk) && !chu.has(kk)) bien[i].add(kk);
    };
    const Wp = HW * C, Hp = S * 1.5 * R;
    const hop = squarify(ds.map((z, i) => ({i, v: n[i]})), -HW / 2, -S, Wp, Hp).sort((a, b) => a.i - b.i);
    for (const h of hop) {
      const mx = h.x + h.w / 2, my = h.y + h.h / 2; let tot = null, d = Infinity;
      for (const q of o.values()) if (!chu.has(q.k)) { const dd = (q.x - mx) ** 2 + (q.y - my) ** 2; if (dd < d) { d = dd; tot = q; } }
      if (!tot) break;
      hat[h.i] = [tot.x, tot.y]; nhan(tot.k, h.i);
    }
    for (;;) {
      let i = -1, tl = Infinity;
      for (let j = 0; j < ds.length; j++) if (dem[j] < n[j] && bien[j].size) { const t = dem[j] / n[j]; if (t < tl) { tl = t; i = j; } }
      if (i < 0) break;
      let tot = null, bc = Infinity;
      for (const kk of bien[i]) {
        const q = o.get(kk), c = Math.hypot(q.x - hat[i][0], q.y - hat[i][1]) / S + nhieu(kk + "|" + ds[i].ma) * 1.4;
        if (c < bc) { bc = c; tot = kk; }
      }
      nhan(tot, i);
    }
    const vung = ds.map((z, i) => {
      const o_ = [...chu.entries()].filter(e => e[1] === i).map(e => o.get(e[0]));
      const mx = o_.reduce((s, q) => s + q.x, 0) / (o_.length || 1), my = o_.reduce((s, q) => s + q.y, 0) / (o_.length || 1);
      let neo = o_[0];
      o_.forEach(q => { if ((q.x - mx) ** 2 + (q.y - my) ** 2 < (neo.x - mx) ** 2 + (neo.y - my) ** 2) neo = q; });
      return {ma: z.ma, i, o: o_, neo: neo ? [neo.x, neo.y] : [0, 0],
        hop: o_.length ? [Math.min(...o_.map(q => q.x)) - HW / 2, Math.min(...o_.map(q => q.y)) - S, Math.max(...o_.map(q => q.x)) + HW / 2, Math.max(...o_.map(q => q.y)) + S] : [0, 0, 0, 0]};
    });
    const xs = [...o.values()];
    return {o, chu, vung, theoMa: Object.fromEntries(vung.map(v => [v.ma, v])),
      hop: [Math.min(...xs.map(q => q.x)) - HW / 2, Math.min(...xs.map(q => q.y)) - S, Math.max(...xs.map(q => q.x)) + HW / 2, Math.max(...xs.map(q => q.y)) + S]};
  }

  const hexD = q => "M" + DINH.map(([dx, dy]) => f1(q.x + dx) + " " + f1(q.y + dy)).join("L") + "Z";
  function vienD(bc, laTrong) {      // cạnh ngoài của tập ô (laTrong(khoá láng giềng) = cùng nhóm?)
    let d = "";
    for (const q of bc) KE[q.r & 1].forEach(([dc, dr], k) => {
      if (!laTrong(khoa(q.c + dc, q.r + dr))) {
        const a = DINH[k], b = DINH[(k + 1) % 6];
        d += `M${f1(q.x + a[0])} ${f1(q.y + a[1])}L${f1(q.x + b[0])} ${f1(q.y + b[1])}`;
      }
    });
    return d;
  }
  function catDong(s, n) {
    const tu = String(s).split(/(?<=[\s/])/); const dong = [""];
    for (const t of tu) { if ((dong[dong.length - 1] + t).trim().length > n && dong[dong.length - 1]) { if (dong.length === 2) { dong[1] = dong[1].trim() + "…"; break; } dong.push(""); } dong[dong.length - 1] += t; }
    return dong.map(x => x.trim()).filter(Boolean);
  }
  const rongChu = (s, px) => [...String(s)].reduce((w, c) => w + (c.codePointAt(0) > 0x2e80 ? px : px * .6), 0);

  /* ---------------- trạng thái + vẽ ---------------- */
  const BD = {view: null, bo: null, khoaBo: "", hop: null, mo: null};
  let hen = 0;

  function ve(hop, mo) {
    BD.hop = hop; BD.mo = mo;
    const khoaBo = mo.vung.map(z => z.ma + ":" + Math.max(2, Math.round(SO_O * z.v / (mo.vung.reduce((s, x) => s + x.v, 0) || 1)))).join("|");
    if (khoaBo !== BD.khoaBo) { BD.bo = boCuc(mo.vung); BD.khoaBo = khoaBo; BD.view = null; }
    const bo = BD.bo, theo = Object.fromEntries(mo.vung.map(z => [z.ma, z]));
    const datTat = [...bo.o.values()], hoang = datTat.filter(q => !bo.chu.has(q.k));
    let s = `<svg class="bd-svg" xmlns="${NS}" role="img" aria-label="Bản đồ chiến dịch"><defs>
      <pattern id="bd-bien" width="64" height="32" patternUnits="userSpaceOnUse"><path d="M0 24q8-6 16 0t16 0t16 0t16 0" fill="none" stroke="rgba(96,165,250,.07)" stroke-width="1.2"/></pattern>
      <pattern id="bd-dia" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(28)"><path d="M0 7h14" stroke="rgba(255,255,255,.045)" stroke-width="1"/><circle cx="3" cy="3" r=".9" fill="rgba(0,0,0,.25)"/></pattern>
      <radialGradient id="bd-may"><stop offset="0" stop-color="#9fb2cf" stop-opacity=".22"/><stop offset="1" stop-color="#9fb2cf" stop-opacity="0"/></radialGradient>
      <pattern id="bd-suong" width="150" height="110" patternUnits="userSpaceOnUse"><rect width="150" height="110" fill="#0b111d"/>
        <circle cx="30" cy="30" r="42" fill="url(#bd-may)"/><circle cx="110" cy="70" r="50" fill="url(#bd-may)"/><circle cx="140" cy="10" r="30" fill="url(#bd-may)"/><circle cx="-5" cy="95" r="34" fill="url(#bd-may)"/></pattern>
      <marker id="bd-mui" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#2ee6c5"/></marker>
      <marker id="bd-mui-v" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#fbbf24"/></marker>
      <linearGradient id="bd-co" x1="0" x2="1"><stop offset="0" stop-color="#7f1d1d"/><stop offset="1" stop-color="#dc2626"/></linearGradient>
    </defs><rect class="bd-bien" width="100%" height="100%" fill="url(#bd-bien)"/>
    <g class="bd-the-gioi"><path class="bd-bo-bien" d="${vienD(datTat, k => bo.o.has(k))}"/>
    <g id="bd-dat">${hoang.length ? `<path class="bd-hoang" d="${hoang.map(hexD).join("")}"/>` : ""}`;
    for (const v of bo.vung) {
      const z = theo[v.ma];
      s += `<path class="bd-o ${z.lop}" data-ma="${MT.esc(v.ma)}" fill="${z.mau}" d="${v.o.map(hexD).join("")}"/>`;
    }
    s += `</g><path class="bd-luoi" d="${datTat.map(hexD).join("")}"/><path class="bd-dia" d="${datTat.map(hexD).join("")}"/>`;
    for (const v of bo.vung) {
      const z = theo[v.ma], d = vienD(v.o, k => bo.chu.get(k) === v.i);
      const lop = ["bd-vien", z.vienTa ? "ta" : "", mo.coQuanChon && mo.coQuanChon.has(v.ma) ? "quan" : "", mo.chonVung === v.ma ? "chon" : "", mo.biDanh && mo.biDanh.has(v.ma) ? "bi-danh" : ""].join(" ");
      s += `${z.vienTa || lop.includes("quan") || lop.includes("chon") || lop.includes("bi-danh") ? `<path class="bd-hao ${lop}" data-ma="${MT.esc(v.ma)}" d="${d}"/>` : ""}<path class="${lop}" data-ma="${MT.esc(v.ma)}" d="${d}"/>`;
    }
    for (const v of bo.vung) if (theo[v.ma].suong) s += `<path class="bd-suong" data-ma="${MT.esc(v.ma)}" d="${v.o.map(hexD).join("")}"/>`;
    s += `<g class="bd-cac-nhan">`;
    for (const v of bo.vung) {
      const z = theo[v.ma], fs = MT.kep(8.5 + Math.sqrt(v.o.length) * 1.55, 9.5, 21), dong = catDong(z.ten, v.o.length > 14 ? 16 : 12);
      const y0 = v.neo[1] - (dong.length - 1) * fs * .55 - (z.chiSo ? fs * .35 : 0);
      s += `<text class="bd-nhan ${z.suong ? "mo" : ""}" data-ma="${MT.esc(v.ma)}" data-fs="${f1(fs)}" x="${f1(v.neo[0])}" y="${f1(y0)}" style="font-size:${f1(fs)}px">` +
        dong.map((t, j) => `<tspan x="${f1(v.neo[0])}" dy="${j ? f1(fs * 1.08) : 0}">${MT.esc(t)}</tspan>`).join("") +
        (z.chiSo ? `<tspan class="bd-chi" x="${f1(v.neo[0])}" dy="${f1(fs * 1.12)}" style="font-size:${f1(fs * .74)}px">${MT.esc(z.chiSo)}</tspan>` : "") + `</text>`;
    }
    s += `</g></g><g class="bd-ghim"></g></svg>
      <div class="bd-nut" role="group" aria-label="Điều khiển bản đồ"><button data-bd="+" title="Phóng to (+)">+</button><button data-bd="-" title="Thu nhỏ (−)">−</button><button data-bd="f" title="Vừa khung (F)">${MT.ic("target")}</button></div>
      <svg class="bd-mini" aria-hidden="true"><use href="#bd-dat"/><rect class="bd-khung"/></svg>`;
    hop.innerHTML = s;
    const svg = hop.querySelector(".bd-svg"), mini = hop.querySelector(".bd-mini");
    const [x0, y0, x1, y1] = bo.hop;
    mini.setAttribute("viewBox", `${f1(x0)} ${f1(y0)} ${f1(x1 - x0)} ${f1(y1 - y0)}`);
    gan(svg, mini);
    // hộp chữ (toạ độ thế giới) để ẩn nhãn đè nhau — nhãn vùng lớn được ưu tiên
    BD.nhan = [...svg.querySelectorAll(".bd-nhan")].map(t => {
      let b = {x: 0, y: 0, width: 0, height: 0}; try { b = t.getBBox(); } catch (e) { /* chưa vẽ */ }
      return {t, b, n: (bo.theoMa[t.dataset.ma] || {o: []}).o.length, fs: Number(t.dataset.fs)};
    }).sort((a, b) => b.n - a.n);
    veGhim();
    if (!BD.view) fit(); else apDung();
  }

  /* ghim (quân cờ, lửa, cờ trùm, mũi tên) vẽ theo toạ độ MÀN HÌNH để giữ cỡ cố định khi phóng */
  function veGhim() {
    const mo = BD.mo, bo = BD.bo, svg = BD.hop.querySelector(".bd-svg");
    if (!svg || !BD.view) return;
    const {k, tx, ty} = BD.view, P = (x, y) => [x * k + tx, y * k + ty];
    const g = svg.querySelector(".bd-ghim");
    let s = "";
    const nhaQuan = {};
    (mo.quan || []).forEach(q => { if (bo.theoMa[q.nha]) (nhaQuan[q.nha] = nhaQuan[q.nha] || []).push(q); });
    const toaQuan = {};
    Object.keys(nhaQuan).forEach(ma => {
      const v = bo.theoMa[ma], fs = MT.kep(8.5 + Math.sqrt(v.o.length) * 1.55, 9.5, 21);
      const [ax, ay] = P(v.neo[0], v.neo[1]), ds = nhaQuan[ma], hang = 3;
      ds.forEach((q, j) => {
        const r = Math.floor(j / hang), trongHang = Math.min(hang, ds.length - r * hang), c = j % hang;
        const w = 30 + q.nhan.length * 7;
        const x = ax + (c - (trongHang - 1) / 2) * 62, y = ay + Math.max(16, fs * k * 1.25) + 12 + r * 26;
        toaQuan[q.ma] = [x, y, w];
      });
    });
    const tamV = ma => { const v = bo.theoMa[ma]; return v ? P(v.neo[0], v.neo[1]) : null; };
    const cong = (a, b, kk) => { const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1];
      return {d: `M${f1(a[0])} ${f1(a[1])}Q${f1(mx - dy * kk)} ${f1(my + dx * kk)} ${f1(b[0])} ${f1(b[1])}`, m: [mx - dy * kk / 2, my + dx * kk / 2]}; };
    // đề xuất tấn công (kênh đang chọn)
    (mo.deXuat || []).forEach((x, j) => {
      const a = toaQuan[x.tu], b = tamV(x.dich); if (!a || !b || Math.hypot(a[0] - b[0], a[1] - b[1]) < 24) return;
      const c = cong([a[0], a[1]], b, j % 2 ? -.2 : .2);
      s += `<path class="bd-dx" d="${c.d}" marker-end="url(#bd-mui-v)"/><g transform="translate(${f1(c.m[0])},${f1(c.m[1])})"><rect x="-15" y="-10" width="30" height="20" rx="6" fill="#fbbf24"/><text class="bd-dx-so" y="4" text-anchor="middle">${Math.round(x.diem)}</text></g>`;
    });
    // lệnh tấn công (video sắp lên sóng)
    (mo.quan || []).forEach(q => {
      const a = toaQuan[q.ma], b = q.dich && q.dich !== q.nha ? tamV(q.dich) : null; if (!a || !b) return;
      const c = cong([a[0], a[1] - 11], b, .2), id = "bd-ml-" + MT.bam(q.ma);
      s += `<path id="${id}" class="bd-lenh ${q.sang ? "sang" : ""}" d="${c.d}" marker-end="url(#bd-mui)"/>`;
      s += `<g class="bd-ngam" transform="translate(${f1(b[0])},${f1(b[1])})"><circle r="11"/><circle r="4"/><path d="M-16 0h6M10 0h6M0-16v6M0 10v6"/></g>`;
      if (q.sang && !MT.giamChuyenDong) s += `<g class="bd-ma-quan"><circle r="5"/><animateMotion dur="1.8s" repeatCount="indefinite" rotate="auto"><mpath href="#${id}"/></animateMotion></g>`;
    });
    // lửa điểm nóng
    (mo.vung || []).forEach(z => {
      if (!z.lua) return; const v = bo.theoMa[z.ma]; if (!v) return;
      const [x, y] = P(v.hop[2] - S * .9, v.hop[1] + S * 1.1);
      s += `<g class="bd-lua" data-ma="${MT.esc(z.ma)}" transform="translate(${f1(x)},${f1(y)})"><circle class="bd-lua-song" r="11"/><circle r="11" class="bd-lua-nen"/>
        <path d="M0-7c3 3 5 5 5 8a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-7z" class="bd-lua-ngon"/>${z.lua > 1 ? `<text x="9" y="-6" class="bd-lua-so">${z.lua}</text>` : ""}</g>`;
    });
    // cờ trùm
    (mo.trum || []).forEach(t => {
      const v = bo.theoMa[t.nha]; if (!v) return;
      const gon = kichThuoc()[0] < 560, [x, y] = P(v.hop[0] + S * .7, v.hop[1] + S * .5), chu = gon ? `#${t.hang}` : `#${t.hang} ${t.ten}`, cat = chu.length > 16 ? chu.slice(0, 15) + "…" : chu, w = rongChu(cat, 11) + 30;
      s += `<g class="bd-trum" data-trum="${MT.esc(t.ten)}" transform="translate(${f1(x)},${f1(y)})" tabindex="0" role="button" aria-label="Hồ sơ địch ${MT.esc(t.ten)}">
        <path d="M0 0v34" class="bd-trum-cot"/><path d="M1 0h${f1(w)}l-8 10 8 10H1z" fill="url(#bd-co)" class="bd-trum-co"/>
        <path transform="translate(6,4) scale(.5)" d="m2 6 4 11h12l4-11-6 5-4-7-4 7z" fill="#fbbf24"/><text x="21" y="14" class="bd-trum-chu">${MT.esc(cat)}</text></g>`;
    });
    // quân ta
    (mo.quan || []).forEach(q => {
      const t = toaQuan[q.ma]; if (!t) return;
      const [x, y, w] = t;
      s += `<g class="bd-quan ${q.chon ? "chon" : ""}" data-quan="${MT.esc(q.ma)}" transform="translate(${f1(x - w / 2)},${f1(y - 11)})" tabindex="0" role="button" aria-label="Quân ${MT.esc(q.ma)}"><g class="bd-nhun" style="animation-delay:-${(MT.bam(q.ma) % 34) / 10}s">
        <rect width="${f1(w)}" height="22" rx="11" class="bd-quan-than"/><circle cx="11" cy="11" r="10" class="bd-quan-cap"/><text x="11" y="15" text-anchor="middle" class="bd-quan-so">${q.cap}</text>
        <text x="${f1(24 + (w - 28) / 2)}" y="15" text-anchor="middle" class="bd-quan-chu">${MT.esc(q.nhan)}</text></g></g>`;
    });
    g.innerHTML = s;
    g.querySelectorAll(".bd-quan").forEach(e => {
      const ma = e.dataset.quan;
      e.addEventListener("pointerenter", ev => { if (!BD.keo) mo.cb.tipQuan(ma, ev); });
      e.addEventListener("pointermove", MT.tipDoi); e.addEventListener("pointerleave", MT.tipAn);
      e.addEventListener("click", ev => { ev.stopPropagation(); if (!BD.daKeo) mo.cb.chonQuan(ma); });
      e.addEventListener("keydown", ev => { if (ev.key === "Enter") mo.cb.chonQuan(ma); });
    });
    g.querySelectorAll(".bd-trum").forEach(e => {
      const ten = e.dataset.trum;
      e.addEventListener("pointerenter", ev => { if (!BD.keo) MT.tip(`<h4>${MT.esc(ten)}</h4><div class="mo">Thành trì của trùm — bấm để xem hồ sơ địch</div>`, ev); });
      e.addEventListener("pointermove", MT.tipDoi); e.addEventListener("pointerleave", MT.tipAn);
      e.addEventListener("click", ev => { ev.stopPropagation(); if (!BD.daKeo) { MT.tipAn(); mo.cb.moTrum(ten); } });
      e.addEventListener("keydown", ev => { if (ev.key === "Enter") mo.cb.moTrum(ten); });
    });
    g.querySelectorAll(".bd-lua").forEach(e => {
      e.addEventListener("pointerenter", ev => { if (!BD.keo) mo.cb.tipVung(e.dataset.ma, ev); });
      e.addEventListener("pointermove", MT.tipDoi); e.addEventListener("pointerleave", MT.tipAn);
      e.addEventListener("click", ev => { ev.stopPropagation(); if (!BD.daKeo) mo.cb.moVung(e.dataset.ma); });
    });
  }

  /* ---------------- khung nhìn ---------------- */
  function kichThuoc() { const r = BD.hop.getBoundingClientRect(); return [r.width || 800, r.height || 500]; }
  function fit() {
    const [W, H] = kichThuoc(), [x0, y0, x1, y1] = BD.bo.hop, k = Math.min(W / (x1 - x0), H / (y1 - y0)) * .94;
    BD.kFit = k;
    BD.view = {k, tx: (W - (x1 - x0) * k) / 2 - x0 * k, ty: (H - (y1 - y0) * k) / 2 - y0 * k};
    apDung();
  }
  function zoomTai(f, px, py) {
    const v = BD.view; if (!v) return;
    const [W, H] = kichThuoc(); if (px == null) { px = W / 2; py = H / 2; }
    const k2 = MT.kep(v.k * f, BD.kFit * .7, BD.kFit * 7);
    v.tx = px - (px - v.tx) * k2 / v.k; v.ty = py - (py - v.ty) * k2 / v.k; v.k = k2;
    apDung();
  }
  function apDung() {
    if (hen) return;
    hen = requestAnimationFrame(() => {
      hen = 0;
      const svg = BD.hop && BD.hop.querySelector(".bd-svg"); if (!svg || !BD.view) return;
      const {k, tx, ty} = BD.view;
      svg.querySelector(".bd-the-gioi").setAttribute("transform", `translate(${f1(tx)},${f1(ty)}) scale(${k.toFixed(4)})`);
      const nhan = [];
      (BD.nhan || []).forEach(x => {
        const r = [x.b.x * k - 2, x.b.y * k - 1, (x.b.x + x.b.width) * k + 2, (x.b.y + x.b.height) * k + 1];
        const hien = x.fs * k >= 8.6 && !nhan.some(q => r[0] < q[2] && r[2] > q[0] && r[1] < q[3] && r[3] > q[1]);
        if (hien) nhan.push(r);
        x.t.style.display = hien ? "" : "none";
      });
      const [W, H] = kichThuoc(), kh = BD.hop.querySelector(".bd-khung");
      if (kh) { kh.setAttribute("x", f1(-tx / k)); kh.setAttribute("y", f1(-ty / k)); kh.setAttribute("width", f1(W / k)); kh.setAttribute("height", f1(H / k)); }
      veGhim();
    });
  }

  /* ---------------- tương tác ---------------- */
  function gan(svg, mini) {
    const mo = BD.mo, hop = BD.hop;
    const phan = ma => svg.querySelectorAll(`[data-ma="${CSS.escape(ma)}"]`);
    svg.querySelectorAll(".bd-o").forEach(e => {
      const ma = e.dataset.ma;
      e.addEventListener("pointerenter", ev => { if (BD.keo) return; phan(ma).forEach(x => x.classList.add("ro")); mo.cb.tipVung(ma, ev); });
      e.addEventListener("pointermove", ev => { if (!BD.keo) MT.tipDoi(ev); });
      e.addEventListener("pointerleave", () => { phan(ma).forEach(x => x.classList.remove("ro")); MT.tipAn(); });
      e.addEventListener("click", () => { if (!BD.daKeo) { MT.tipAn(); mo.cb.moVung(ma); } });
    });
    svg.addEventListener("wheel", ev => {
      ev.preventDefault(); const r = svg.getBoundingClientRect();
      zoomTai(Math.exp(-ev.deltaY * (ev.deltaMode ? 0.05 : 0.0016)), ev.clientX - r.left, ev.clientY - r.top);
    }, {passive: false});
    const tro = new Map(); let dau = null;
    svg.addEventListener("pointerdown", ev => {
      tro.set(ev.pointerId, [ev.clientX, ev.clientY]); BD.daKeo = false;
      dau = {v: {...BD.view}, p: [...tro.values()].map(p => p.slice())};
    });
    svg.addEventListener("pointermove", ev => {
      if (!tro.has(ev.pointerId) || !dau) return;
      tro.set(ev.pointerId, [ev.clientX, ev.clientY]);
      const ps = [...tro.values()], r = svg.getBoundingClientRect();
      if (ps.length === 1 && dau.p.length === 1) {
        const dx = ps[0][0] - dau.p[0][0], dy = ps[0][1] - dau.p[0][1];
        if (!BD.keo && Math.hypot(dx, dy) > 5) { BD.keo = true; BD.daKeo = true; MT.tipAn(); svg.setPointerCapture(ev.pointerId); svg.classList.add("dang-keo"); }
        if (BD.keo) { BD.view.tx = dau.v.tx + dx; BD.view.ty = dau.v.ty + dy; apDung(); }
      } else if (ps.length === 2 && dau.p.length === 2) {
        const d0 = Math.hypot(dau.p[0][0] - dau.p[1][0], dau.p[0][1] - dau.p[1][1]), d1 = Math.hypot(ps[0][0] - ps[1][0], ps[0][1] - ps[1][1]);
        const mx = (ps[0][0] + ps[1][0]) / 2 - r.left, my = (ps[0][1] + ps[1][1]) / 2 - r.top;
        BD.view = {...dau.v}; BD.keo = true; BD.daKeo = true;
        zoomTai(d1 / (d0 || 1), mx, my);
      }
    });
    const tha = ev => {
      tro.delete(ev.pointerId);
      if (!tro.size) { BD.keo = false; svg.classList.remove("dang-keo"); dau = null; setTimeout(() => { BD.daKeo = false; }, 0); }
      else dau = {v: {...BD.view}, p: [...tro.values()].map(p => p.slice())};
    };
    svg.addEventListener("pointerup", tha); svg.addEventListener("pointercancel", tha);
    svg.addEventListener("dblclick", ev => { const r = svg.getBoundingClientRect(); zoomTai(1.7, ev.clientX - r.left, ev.clientY - r.top); });
    hop.querySelectorAll("[data-bd]").forEach(b => b.addEventListener("click", () => {
      const c = b.dataset.bd; if (c === "f") fit(); else zoomTai(c === "+" ? 1.4 : 1 / 1.4);
    }));
    mini.addEventListener("click", ev => {
      const r = mini.getBoundingClientRect(), vb = mini.viewBox.baseVal;
      const sc = Math.min(r.width / vb.width, r.height / vb.height), ox = (r.width - vb.width * sc) / 2, oy = (r.height - vb.height * sc) / 2;
      const wx = vb.x + (ev.clientX - r.left - ox) / sc, wy = vb.y + (ev.clientY - r.top - oy) / sc, [W, H] = kichThuoc();
      BD.view.tx = W / 2 - wx * BD.view.k; BD.view.ty = H / 2 - wy * BD.view.k; apDung();
    });
  }

  /* đổi màu theo một ngày (tua lại diễn biến): mau[ma] = {lop, mau, chiSo} */
  function toMau(mau) {
    const svg = BD.hop && BD.hop.querySelector(".bd-svg"); if (!svg) return;
    svg.querySelectorAll(".bd-o").forEach(e => {
      const m = mau[e.dataset.ma];
      e.setAttribute("class", "bd-o " + (m ? m.lop : "s-khong"));
      e.setAttribute("fill", m ? m.mau : "#1a2233");
    });
    svg.querySelectorAll(".bd-nhan").forEach(t => {
      const m = mau[t.dataset.ma], c = t.querySelector(".bd-chi");
      if (c) c.textContent = m ? m.chiSo : "chưa có số";
    });
  }

  document.addEventListener("keydown", ev => {
    if (!BD.hop || ev.ctrlKey || ev.metaKey || ev.altKey || /INPUT|SELECT|TEXTAREA/.test((ev.target || {}).tagName || "")) return;
    if (ev.key === "f" || ev.key === "F") fit();
    else if (ev.key === "+" || ev.key === "=") zoomTai(1.4);
    else if (ev.key === "-" || ev.key === "_") zoomTai(1 / 1.4);
  });

  /* chớp một vùng (tấn công / chiếm đất) — vài nhịp rồi tự gỡ */
  function nhay(ma, lop) {
    const svg = BD.hop && BD.hop.querySelector(".bd-svg"); if (!svg || MT.giamChuyenDong) return;
    svg.querySelectorAll(`.bd-o[data-ma="${CSS.escape(ma)}"]`).forEach(e => { e.classList.remove(lop); void e.getBBox(); e.classList.add(lop); setTimeout(() => e.classList.remove(lop), 2400); });
  }
  MT.banDo = {ve, fit, zoomTai, toMau, boCuc, nhay, veGhim: () => apDung(), BD};
})();
