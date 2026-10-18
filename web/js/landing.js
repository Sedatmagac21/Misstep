// Public pages: landing, about, contact. Includes the 3D hero scene.
import { t, getLang } from "./i18n.js";
import { $, $$, api, brand, countUp, errText, esc, icon, langSwitch, reveal, tilt, toast, busy } from "./ui.js";

// ---------- 3D scene: a slowly turning sphere of maths symbols ----------
const GLYPHS = ["x²", "√", "=", "π", "+", "−", "(a+b)²", "3x", "÷", "∑", "x", "y", "½", "≠", "a/b", "2ab", "x³", "∞", "≤", "Δ", "7", "4", "(x+3)", "−(x+3)", "f(x)"];

export function sphere(canvas, { count = 90, radius = 0.36, color = "255,255,255", accent = "255,90,95" } = {}) {
  const ctx = canvas.getContext("2d");
  const pts = [];
  for (let i = 0; i < count; i++) {  // golden-spiral points on a sphere
    const y = 1 - (i / (count - 1)) * 2, r = Math.sqrt(1 - y * y), phi = i * Math.PI * (3 - Math.sqrt(5));
    pts.push({ x: Math.cos(phi) * r, y, z: Math.sin(phi) * r, g: GLYPHS[i % GLYPHS.length], hot: i % 11 === 0 });
  }
  let rx = 0.3, ry = 0, tx = 0, ty = 0, raf, w = 0, h = 0, dpr = 1;
  const resize = () => {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    w = canvas.clientWidth; h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
  };
  const onMove = (e) => { tx = (e.clientX / innerWidth - 0.5) * 0.8; ty = (e.clientY / innerHeight - 0.5) * 0.5; };
  addEventListener("mousemove", onMove);
  addEventListener("resize", resize);
  resize();
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const frame = () => {
    if (!canvas.isConnected) { removeEventListener("mousemove", onMove); removeEventListener("resize", resize); return; }
    ry += still ? 0 : 0.0022; rx += (0.25 + ty - rx) * 0.04;
    const yaw = ry + tx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const R = Math.min(w, h) * radius, cx = w / 2, cy = h / 2;
    const proj = pts.map((p) => {
      let x = p.x * Math.cos(yaw) - p.z * Math.sin(yaw), z = p.x * Math.sin(yaw) + p.z * Math.cos(yaw), y = p.y;
      const y2 = y * Math.cos(rx) - z * Math.sin(rx); z = y * Math.sin(rx) + z * Math.cos(rx); y = y2;
      const s = 2.4 / (2.4 + z);
      return { ...p, sx: cx + x * R * s, sy: cy + y * R * s, s, z };
    }).sort((a, b) => b.z - a.z);
    // faint links between near neighbours give the sphere its 3D shape
    ctx.lineWidth = 1;
    for (let i = 0; i < proj.length; i++) for (let j = i + 1; j < proj.length; j++) {
      const a = proj[i], b = proj[j], d = Math.hypot(a.sx - b.sx, a.sy - b.sy);
      if (d < R * 0.32) { ctx.strokeStyle = `rgba(${color},${0.07 * (1 - d / (R * 0.32)) * (a.s + b.s)})`; ctx.beginPath(); ctx.moveTo(a.sx, a.sy); ctx.lineTo(b.sx, b.sy); ctx.stroke(); }
    }
    for (const p of proj) {
      const alpha = Math.max(0.12, Math.min(1, (p.s - 0.55) * 1.6));
      ctx.font = `${p.hot ? 700 : 500} ${Math.round((p.hot ? 17 : 13) * p.s)}px ui-monospace, Menlo, monospace`;
      ctx.fillStyle = p.hot ? `rgba(${accent},${alpha})` : `rgba(${color},${alpha * 0.75})`;
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(p.g, p.sx, p.sy);
    }
    raf = requestAnimationFrame(frame);
  };
  frame();
  return () => cancelAnimationFrame(raf);
}

// ---------- shared chrome ----------
export function siteNav(solid = false) {
  return `<header class="site-nav ${solid ? "solid" : ""}" id="site-nav"><div class="wrap">
    ${brand(!solid)}
    <nav class="links">
      <a href="#/" data-scroll="how">${t("nav_how")}</a><a href="#/" data-scroll="features">${t("nav_features")}</a>
      <a href="#/" data-scroll="roles">${t("nav_roles")}</a><a href="#/" data-scroll="pricing">${t("nav_pricing")}</a><a href="#/about">${t("nav_about")}</a><a href="#/contact">${t("nav_contact")}</a>
    </nav>
    <div class="right">${langSwitch()}
      <a class="btn btn-ghost btn-sm" href="#/login">${t("login")}</a>
      <a class="btn btn-primary btn-sm" href="#/register">${t("register")}</a>
    </div></div></header>`;
}

export function footer() {
  return `<footer class="footer"><div class="wrap">
    <div class="cols">
      <div>${brand(true)}<p style="margin-top:14px;max-width:320px;font-size:14.5px">${t("foot_desc")}</p></div>
      <div><h4>${t("foot_product")}</h4><a href="#/" data-scroll="how">${t("nav_how")}</a><a href="#/" data-scroll="features">${t("nav_features")}</a><a href="#/register">${t("register")}</a></div>
      <div><h4>${t("foot_company")}</h4><a href="#/about">${t("nav_about")}</a><a href="#/contact">${t("nav_contact")}</a></div>
      <div><h4>${t("foot_legal")}</h4><a href="#/about">${t("foot_privacy")}</a><a href="#/about">${t("foot_license")}</a></div>
    </div>
    <div class="base"><span>© 2026 Misstep · ${t("foot_made")}</span><span>Gemma 4 · SymPy · Ollama</span></div>
  </div></footer>`;
}

function wireChrome(root) {
  const nav = $("#site-nav", root);
  const solidAlways = nav.classList.contains("solid") && !root.querySelector(".hero");
  const onScroll = () => { if (!nav.isConnected) return removeEventListener("scroll", onScroll); if (!solidAlways) nav.classList.toggle("solid", scrollY > 30); };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  $$("[data-scroll]", root).forEach((a) => a.addEventListener("click", (e) => {
    const target = document.getElementById(a.dataset.scroll);
    if (target) { e.preventDefault(); target.scrollIntoView({ behavior: "smooth" }); }
    else { sessionStorage.setItem("ms_scroll", a.dataset.scroll); }
  }));
  reveal(root); tilt(root); countUp(root);
}

// ---------- landing ----------
export async function renderLanding(root) {
  const lines = ["3x − (x + 3) = 7", "3x − x + 3 = 7", "2x + 3 = 7", "x = 2"];
  root.innerHTML = `${siteNav()}
  <section class="hero"><div class="grid-bg"></div><div class="wrap">
    <div>
      <div class="eyebrow"><b>${t("hero_eyebrow")}</b>${t("hero_eyebrow_t")}</div>
      <h1>${t("hero_title_1")} <span class="hl">${t("hero_title_2")}</span>${getLang() === "en" ? "" : " "}${t("hero_title_3")}</h1>
      <p class="lead">${t("hero_lead")}</p>
      <div class="cta"><a class="btn btn-primary btn-lg" href="#/register">${t("start_free")} ${icon("arrow")}</a>
        <a class="btn btn-light btn-lg" href="#/" data-scroll="how">${t("see_how")}</a></div>
      <div class="try-demo"><span>${icon("spark")} ${t("try_demo")}</span>${[["student", "graduation"], ["teacher", "clipboard"], ["parent", "heart"]].map(([r, ic]) =>
        `<button class="btn btn-light btn-sm" data-demo-role="${r}">${icon(ic)}${t("role_" + r)}</button>`).join("")}</div>
      <div class="badges"><span>${icon("shield")}${t("hero_b1")}</span><span>${icon("lock")}${t("hero_b2")}</span><span>${icon("code")}${t("hero_b3")}</span></div>
    </div>
    <div class="stage" id="stage"><canvas id="sphere"></canvas>
      <div class="paper" id="paper">
        <div class="ph"><span>${t("paper_title")}</span><span id="paper-st">${t("paper_checking")}</span></div>
        ${lines.map((l, i) => `<div class="row" data-i="${i}"><span class="n">${i + 1}</span><span>${l}</span><span class="st"></span></div>`).join("")}
        <div class="verdict" id="verdict">${t("paper_verdict")}</div>
      </div>
      <div class="float-card a"><span>${t("float_a")}</span><b>${t("float_a_v")}</b></div>
      <div class="float-card b"><span>${t("float_b")}</span><b>${t("float_b_v")}</b></div>
    </div>
  </div></section>

  <section class="section" id="how"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("how_k")}</div><h2>${t("how_t")}</h2><p>${t("how_p")}</p></div>
    <div class="steps">
      ${[["camera", "how1", "Gemma 4"], ["shield", "how2", "SymPy"], ["target", "how3", "Bug library"], ["spark", "how4", "RAG"]].map(([ic, k, who], i) => `
        <div class="step reveal"><div class="ic">${icon(ic)}<i>${i + 1}</i></div><h3>${t(k + "_t")}</h3><p>${t(k + "_p")}</p><div class="who"><span class="chip">${who}</span></div></div>`).join("")}
    </div>
  </div></section>

  <section class="section alt" id="features"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("feat_k")}</div><h2>${t("feat_t")}</h2><p>${t("feat_p")}</p></div>
    <div class="features">
      ${[["steps", "coral", "f1"], ["wand", "amber", "f2"], ["target", "navy", "f3"], ["book", "blue", "f4"], ["chart", "green", "f5"], ["users", "coral", "f6"]].map(([ic, c, k]) => `
        <div class="feature reveal" data-tilt><div class="glow"></div><div class="ic ${c}">${icon(ic)}</div><h3>${t(k + "_t")}</h3><p>${t(k + "_p")}</p></div>`).join("")}
    </div>
  </div></section>

  <section class="section" id="roles"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("roles_k")}</div><h2>${t("roles_t")}</h2></div>
    <div class="roles">
      ${[["student", "graduation", "coral", "rs"], ["teacher", "clipboard", "navy", "rt"], ["parent", "heart", "amber", "rp"]].map(([r, ic, c, k]) => `
        <div class="role-card reveal"><div class="top"><div class="avatar ic ${c}">${icon(ic)}</div><h3>${t("r_" + r)}</h3></div>
          <ul>${[1, 2, 3, 4].map((n) => `<li>${icon("check")}<span>${t(k + n)}</span></li>`).join("")}</ul>
          <a class="btn ${r === "student" ? "btn-primary" : "btn-ghost"}" href="#/register?role=${r}">${t("as_" + r)}</a></div>`).join("")}
    </div>
  </div></section>

  <section class="section alt" id="why"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("why_k")}</div><h2>${t("why_t")}</h2><p>${t("why_p")}</p></div>
    <div class="compare-t reveal"><div class="ch"><span></span><span>${t("why_c1")}</span><span class="me">${brand()}</span></div>
      ${[[1, 1], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0]].map(([n, other]) => `<div class="cr"><span>${t("why_r" + n)}</span>
        <span class="${other ? "y" : "n"}">${icon(other ? "check" : "x")}</span><span class="y me">${icon("check")}</span></div>`).join("")}</div>
  </div></section>

  <section class="section" id="pricing"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("pr_k")}</div><h2>${t("pr_t")}</h2><p>${t("pr_p")}</p></div>
    <div class="plans">${[["free", "graduation", "/register?role=student"], ["tutor", "clipboard", "/register?role=teacher"], ["school", "users", "/contact"]].map(([k, ic, href]) => `
      <div class="plan reveal ${k === "tutor" ? "hot" : ""}">${k === "tutor" ? `<span class="ribbon">${t("pr_hot")}</span>` : ""}
        <div class="ic">${icon(ic)}</div><h3>${t("pl_" + k)}</h3><p class="muted">${t("pl_" + k + "_d")}</p>
        <div class="price"><b>${t("pl_" + k + "_p")}</b><span>${t("pl_" + k + "_u")}</span></div>
        <ul>${[1, 2, 3, 4].map((n) => `<li>${icon("check")}<span>${t("pl_" + k + n)}</span></li>`).join("")}</ul>
        <a class="btn ${k === "tutor" ? "btn-primary" : "btn-ghost"}" href="#${href}">${t("pl_" + k + "_cta")}</a></div>`).join("")}</div>
    <div class="earn reveal" id="earn"><div><div class="kicker">${t("earn_k")}</div><h3>${t("earn_t")}</h3><p class="muted">${t("earn_p")}</p>
        <label>${t("earn_n")} <b id="en-v"></b><input type="range" id="en" min="5" max="60" value="20"></label>
        <label>${t("earn_f")} <b id="ef-v"></b><input type="range" id="ef" min="100" max="1000" step="50" value="300"></label></div>
      <div class="earn-out"><span>${t("earn_out")}</span><b id="e-total"></b><small id="e-note"></small></div></div>
    <p class="muted" style="text-align:center;font-size:12.5px;margin-top:14px">${t("pr_note")}</p>
  </div></section>

  <section class="section" style="padding-top:0"><div class="wrap">
    <div class="stats-band reveal" id="stats">
      ${["users", "solutions", "answers", "rules"].map((k) => `<div class="stat"><b data-k="${k}">0</b><span>${t("stats_" + k)}</span></div>`).join("")}
    </div>
    <p class="muted" style="text-align:center;font-size:12.5px;margin-top:12px">${t("stats_note")}</p>
  </div></section>

  <section class="section alt"><div class="wrap">
    <div class="vm">
      <div class="vm-card v reveal"><div class="k">${t("vision_k")}</div><h3>${t("vision_t")}</h3><p>${t("vision_p")}</p><div class="big">V</div></div>
      <div class="vm-card m reveal"><div class="k">${t("mission_k")}</div><h3>${t("mission_t")}</h3><p>${t("mission_p")}</p><div class="big">M</div></div>
    </div>
  </div></section>

  <section class="section"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("tech_k")}</div><h2>${t("tech_t")}</h2></div>
    <div class="tech">${["t1", "t2", "t3", "t4"].map((k) => `<div class="tech-card reveal"><div class="t">${t(k)}</div><p>${t(k + "_p")}</p></div>`).join("")}</div>
  </div></section>

  <section class="section alt"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("faq_k")}</div><h2>${t("faq_t")}</h2></div>
    <div class="faq">${[1, 2, 3, 4].map((n) => `<details class="reveal"><summary>${t("q" + n)}</summary><p>${t("a" + n)}</p></details>`).join("")}</div>
  </div></section>

  <section class="section"><div class="wrap"><div class="cta-band reveal"><h2>${t("cta_t")}</h2><p>${t("cta_p")}</p>
    <a class="btn btn-lg" href="#/register">${t("start_free")} ${icon("arrow")}</a></div></div></section>
  ${footer()}`;

  sphere($("#sphere", root));
  wireChrome(root);
  animatePaper(root);
  wireEarn(root);
  const stage = $("#stage", root), paper = $("#paper", root);
  stage.addEventListener("mousemove", (e) => {
    const r = stage.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
    paper.style.transform = `translate(-50%,-50%) rotateY(${-16 + x * 18}deg) rotateX(${8 - y * 14}deg)`;
  });
  stage.addEventListener("mouseleave", () => { paper.style.transform = ""; });
  const pending = sessionStorage.getItem("ms_scroll");
  if (pending) { sessionStorage.removeItem("ms_scroll"); setTimeout(() => document.getElementById(pending)?.scrollIntoView(), 50); }

  try {
    const s = await api("/api/stats");
    for (const k of ["users", "solutions", "answers", "rules"]) {
      const el = root.querySelector(`[data-k="${k}"]`);
      if (el) el.dataset.count = s[k];
    }
    countUp($("#stats", root));
  } catch { /* stats are decoration */ }
}

// "Side hustle" calculator: what a tutor earns running Misstep-backed weekly follow-ups for paying students.
const TUTOR_PLAN = 499;
function wireEarn(root) {
  const n = $("#en", root), f = $("#ef", root);
  const tl = (v) => `${v.toLocaleString(getLang() === "en" ? "en-US" : "tr-TR")} ₺`;
  const draw = () => {
    const students = Number(n.value), fee = Number(f.value), net = students * fee - TUTOR_PLAN;
    $("#en-v", root).textContent = students; $("#ef-v", root).textContent = tl(fee);
    $("#e-total", root).textContent = tl(net);
    $("#e-note", root).textContent = t("earn_note", { g: tl(students * fee), p: tl(TUTOR_PLAN) });
  };
  [n, f].forEach((i) => i.addEventListener("input", draw));
  draw();
}

function animatePaper(root) {
  const rows = $$(".paper .row", root), st = $("#paper-st", root), verdict = $("#verdict", root);
  const states = ["ok", "bad", "dim", "dim"];
  let i = 0;
  const tick = () => {
    if (!root.isConnected || !rows[0]?.isConnected) return;
    if (i === 0) { rows.forEach((r) => { r.className = "row"; r.querySelector(".st").textContent = ""; }); verdict.classList.remove("show"); st.textContent = t("paper_checking"); }
    if (i < rows.length) {
      const s = states[i];
      rows[i].classList.add(s);
      rows[i].querySelector(".st").textContent = s === "ok" ? (i === 0 ? "" : t("st_ok")) : s === "bad" ? t("st_err") : "";
      if (s === "bad") { verdict.classList.add("show"); st.textContent = "✓"; }
      i++;
      setTimeout(tick, i === 2 ? 1800 : 700);
    } else { i = 0; setTimeout(tick, 4200); }
  };
  rows[0].classList.add("ok");
  setTimeout(tick, 600);
}

// ---------- about ----------
export function renderAbout(root) {
  root.innerHTML = `${siteNav()}
  <section class="page-hero"><div class="wrap"><h1>${t("about_t")}</h1><p>${t("about_p")}</p></div></section>
  <section class="section alt"><div class="wrap two">
    <div class="prose">
      ${[1, 2, 3, 4].map((n) => `<h2 class="reveal">${t("about_h" + n)}</h2><p class="reveal">${t("about_s" + n)}</p>`).join("")}
    </div>
    <div style="display:flex;flex-direction:column;gap:16px;position:sticky;top:100px">
      <div class="vm-card v reveal" style="padding:28px"><div class="k">${t("vision_k")}</div><h3 style="font-size:20px">${t("vision_t")}</h3><p style="font-size:14.5px">${t("vision_p")}</p></div>
      <div class="vm-card m reveal" style="padding:28px"><div class="k">${t("mission_k")}</div><h3 style="font-size:20px">${t("mission_t")}</h3><p style="font-size:14.5px">${t("mission_p")}</p></div>
      <div class="card reveal"><h2>${t("about_team")}</h2><p class="muted" style="margin-top:6px;font-size:14.5px">${t("about_team_p")}</p></div>
    </div>
  </div></section>
  <section class="section"><div class="wrap">
    <div class="section-head reveal"><div class="kicker">${t("tech_k")}</div><h2>${t("tech_t")}</h2></div>
    <div class="tech">${["t1", "t2", "t3", "t4"].map((k) => `<div class="tech-card reveal"><div class="t">${t(k)}</div><p>${t(k + "_p")}</p></div>`).join("")}</div>
  </div></section>
  <section class="section alt" id="eval"><div class="wrap">
    <div class="section-head"><div class="kicker">${t("evs_k")}</div><h2>${t("ev_set_t")}</h2><p>${t("ev_set_p")}</p></div>
    <div id="evbox"><div class="skeleton" style="height:140px"></div></div>
  </div></section>
  ${footer()}`;
  wireChrome(root);
  api("/api/eval").then((r) => {
    const show = (x) => (x == null ? "–" : `${Math.round(x * 100)}`);
    $("#evbox", root).innerHTML = `<div class="eval-grid">${[["step_accuracy", "ev_m1"], ["rule_top1", "ev_m2"], ["false_alarm_rate", "ev_m3"], ["slip_honesty", "ev_m4"]].map(([k, l]) =>
      `<div class="eval-kpi"><b>${show(r[k])}<small>%</small></b><span>${t(l)}</span></div>`).join("")}</div>
      <p class="muted" style="margin-top:14px;font-size:14px">${t("ev_meta", { n: r.cases, c: r.correct_solutions, w: r.with_mistake, r: r.rules_covered, ms: r.avg_ms })}</p>
      ${r.failures.length ? `<div class="callout amber" style="margin-top:12px">${icon("alert")}<div><b>${t("ev_fail_t", { n: r.failures.length })}</b><br>${r.failures.map((f) => `<span class="mono">${esc(f.id)}</span>: ${t("ev_fail", { e: f.expected_rule || t("ev_slip"), g: f.got_rule || t("ev_none") })}`).join("<br>")}</div></div>` : ""}
      <p class="hint" style="margin-top:12px">${icon("code")} <span class="mono">python -m misstep.evaluate</span> · eval/cases.jsonl</p>`;
  }).catch(() => { $("#evbox", root).innerHTML = ""; });
}

// ---------- contact ----------
export function renderContact(root) {
  root.innerHTML = `${siteNav()}
  <section class="page-hero"><div class="wrap"><h1>${t("contact_t")}</h1><p>${t("contact_p")}</p></div></section>
  <section class="section alt"><div class="wrap two">
    <form class="contact-card reveal" id="cform">
      <div class="grid g2"><div class="field"><label>${t("c_name")}</label><input class="input" name="name" required></div>
      <div class="field"><label>${t("c_email")}</label><input class="input" name="email" type="email" required></div></div>
      <div class="field"><label>${t("c_msg")}</label><textarea class="input" name="message" rows="6" required></textarea></div>
      <div id="cerr"></div>
      <button class="btn btn-primary" type="submit">${icon("mail")}${t("c_send")}</button>
    </form>
    <div class="info-list">
      ${[["graduation", "coral", "c_info1"], ["code", "navy", "c_info2"], ["lock", "amber", "c_info3"]].map(([ic, c, k]) => `
        <div class="it reveal"><div class="ic ${c}">${icon(ic)}</div><div><b>${t(k)}</b><p class="muted" style="font-size:14.5px">${t(k + "_p")}</p></div></div>`).join("")}
    </div>
  </div></section>
  ${footer()}`;
  wireChrome(root);
  $("#cform", root).addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target, btn = f.querySelector("button");
    busy(btn, true);
    try {
      await api("/api/contact", { method: "POST", body: Object.fromEntries(new FormData(f)) });
      f.reset(); $("#cerr", root).innerHTML = ""; toast(t("c_sent"));
    } catch (err) { $("#cerr", root).innerHTML = `<div class="form-error">${esc(errText(err))}</div>`; }
    busy(btn, false);
  });
}
