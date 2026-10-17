// Log in and sign up pages.
import { t } from "./i18n.js";
import { sphere } from "./landing.js";
import { $, $$, api, brand, busy, errText, esc, icon, langSwitch } from "./ui.js";

function shell(inner) {
  const rows = [["3x − (x + 3) = 7", ""], ["3x − x + 3 = 7", "bad"], ["2x + 3 = 7", "warn"], ["x = 2", "warn"]];
  return `<div class="auth">
    <aside class="side"><canvas id="auth-sphere"></canvas>
      <div class="side-top">${brand(true)}</div>
      <div class="side-mid">
        <div class="mini-paper">${rows.map(([l, c], i) => `<div class="r ${c}"><span class="n">${i + 1}</span><span class="mono">${l}</span>${c === "bad" ? `<span class="tag">${t("au_err")}</span>` : ""}</div>`).join("")}
          <div class="v">${icon("target")}<span>${t("au_diag")}</span></div></div>
        <h2>${t("auth_quote_t")}</h2><p>${t("auth_quote_p")}</p>
        <ul class="au-points">${[["shield", "au_p1"], ["lock", "au_p2"], ["chart", "au_p3"]].map(([ic, k]) => `<li>${icon(ic)}<span>${t(k)}</span></li>`).join("")}</ul>
      </div>
      <div class="side-foot">${t("au_foot")}</div>
    </aside>
    <main class="main"><div class="au-top"><a href="#/" class="au-back">← ${t("au_home")}</a>${langSwitch()}</div>${inner}
      <p class="au-legal">${icon("lock")} ${t("au_legal")}</p></main></div>`;
}

const field = (name, type, label, ic, extra = "") => `<div class="field"><label for="f-${name}">${label}</label>
  <div class="in-ic">${icon(ic)}<input class="input" id="f-${name}" name="${name}" type="${type}" ${extra} required>${type === "password" ? `<button type="button" class="eye" data-eye aria-label="${t("au_show")}">${icon("eye")}</button>` : ""}</div></div>`;

function wireEyes(root) {
  $$("[data-eye]", root).forEach((b) => b.addEventListener("click", () => {
    const inp = b.previousElementSibling; inp.type = inp.type === "password" ? "text" : "password"; b.classList.toggle("on");
  }));
}

function demoButtons() {
  return `<div class="divider">${t("or_demo")}</div>
    <div class="demo-cards">${[["student", "graduation"], ["teacher", "clipboard"], ["parent", "heart"]].map(([r, ic]) =>
      `<button type="button" class="demo-card" data-demo="${r}">${icon(ic)}<b>${t("role_" + r)}</b><small>${t("au_demo_" + r)}</small></button>`).join("")}</div>`;
}

function wireDemo(root, onLogin) {
  $$("[data-demo]", root).forEach((b) => b.addEventListener("click", async () => {
    b.classList.add("busy"); b.disabled = true;
    try { const r = await api("/api/demo-login", { method: "POST", body: { role: b.dataset.demo } }); onLogin(r.user); }
    catch (e) { b.classList.remove("busy"); b.disabled = false; showErr(root, e); }
  }));
}

const showErr = (root, e) => { $("#ferr", root).innerHTML = `<div class="form-error">${esc(errText(e))}</div>`; };

export function renderLogin(root, onLogin, current = null) {
  root.innerHTML = shell(`<form id="f" novalidate>
      <div class="mobile-only">${brand()}</div>
      <h1>${t("login_t")}</h1><p class="sub">${t("login_sub")}</p>
      ${current ? `<div class="callout blue">${icon("user")}<span>${t("signed_as", { n: esc(current.name), r: t("role_" + current.role) })}</span></div>` : ""}
      ${field("email", "email", t("email"), "mail", 'autocomplete="email" placeholder="ad@okul.com"')}
      ${field("password", "password", t("password"), "lock", 'autocomplete="current-password" placeholder="••••••"')}
      <div id="ferr"></div>
      <button class="btn btn-primary btn-lg" type="submit">${t("login")} ${icon("arrow")}</button>
      ${demoButtons()}
      <p class="muted" style="text-align:center;font-size:14px">${t("no_account")} <a href="#/register" style="color:var(--coral);font-weight:700">${t("register")}</a></p>
    </form>`);
  sphere($("#auth-sphere", root), { count: 46, radius: 0.36 });
  wireEyes(root);
  $("#f", root).addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector("button[type=submit]");
    busy(btn, true);
    try { const r = await api("/api/login", { method: "POST", body: Object.fromEntries(new FormData(e.target)) }); onLogin(r.user); }
    catch (err) { busy(btn, false); showErr(root, err); }
  });
  wireDemo(root, onLogin);
}

export function renderRegister(root, onLogin, params) {
  let role = ["student", "teacher", "parent"].includes(params.get("role")) ? params.get("role") : "student";
  root.innerHTML = shell(`<form id="f" novalidate>
      <h1>${t("register_t")}</h1><p class="sub">${t("register_sub")}</p>
      <div class="role-pick">${[["student", "graduation"], ["teacher", "clipboard"], ["parent", "heart"]].map(([r, ic]) =>
        `<button type="button" data-role="${r}" class="${r === role ? "on" : ""}">${icon(ic)}${t("role_" + r)}<small>${t("role_" + r + "_d")}</small></button>`).join("")}</div>
      ${field("name", "text", t("name"), "user", 'autocomplete="name"')}
      ${field("email", "email", t("email"), "mail", 'autocomplete="email" placeholder="ad@okul.com"')}
      <div>${field("password", "password", t("password"), "lock", 'autocomplete="new-password"')}
        <div class="pw-meter"><i></i><i></i><i></i></div><span class="hint" id="pwh">${t("pw_hint")}</span></div>
      <div class="grid g2" id="student-extra">
        <div class="field"><label>${t("grade")}</label><select class="input" name="grade">${[7, 8, 9, 10].map((g) => `<option value="${g}" ${g === 8 ? "selected" : ""}>${t("grade_n", { n: g })}</option>`).join("")}</select></div>
        <div class="field"><label>${t("class_code")}</label><input class="input mono" name="code_s" maxlength="6" style="text-transform:uppercase"></div>
      </div>
      <div class="field hidden" id="parent-extra"><label>${t("family_code_in")}</label><input class="input mono" name="code_p" maxlength="6" style="text-transform:uppercase"></div>
      <div id="ferr"></div>
      <button class="btn btn-primary btn-lg" type="submit">${t("register")} ${icon("arrow")}</button>
      ${demoButtons()}
      <p class="muted" style="text-align:center;font-size:14px">${t("have_account")} <a href="#/login" style="color:var(--coral);font-weight:700">${t("login")}</a></p>
    </form>`);
  sphere($("#auth-sphere", root), { count: 46, radius: 0.36 });
  wireEyes(root);
  $("#f-password", root).addEventListener("input", (e) => {
    const v = e.target.value, score = (v.length >= 6) + (v.length >= 10) + (/\d/.test(v) && /[a-zçğıöşü]/i.test(v));
    $$(".pw-meter i", root).forEach((i, k) => { i.className = k < score ? ["weak", "ok", "strong"][score - 1] : ""; });
    $("#pwh", root).textContent = v ? t(["pw_s0", "pw_s1", "pw_s2", "pw_s3"][score]) : t("pw_hint");
  });
  const sync = () => {
    $$("[data-role]", root).forEach((b) => b.classList.toggle("on", b.dataset.role === role));
    $("#student-extra", root).classList.toggle("hidden", role !== "student");
    $("#parent-extra", root).classList.toggle("hidden", role !== "parent");
  };
  $$("[data-role]", root).forEach((b) => b.addEventListener("click", () => { role = b.dataset.role; sync(); }));
  sync();
  $("#f", root).addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    const body = { name: f.name, email: f.email, password: f.password, role,
      grade: role === "student" ? Number(f.grade) : null, code: (role === "student" ? f.code_s : role === "parent" ? f.code_p : "") || "" };
    const btn = e.target.querySelector("button[type=submit]");
    busy(btn, true);
    try { const r = await api("/api/register", { method: "POST", body }); onLogin(r.user); }
    catch (err) { busy(btn, false); showErr(root, err); }
  });
  wireDemo(root, onLogin);
}
