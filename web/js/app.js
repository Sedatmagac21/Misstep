// Router and the signed-in app shell.
import { setLang, t } from "./i18n.js";
import { renderAbout, renderContact, renderLanding } from "./landing.js";
import { renderLogin, renderRegister } from "./auth.js";
import { $, $$, api, brand, esc, icon, initials, langSwitch } from "./ui.js";
import * as S from "./student.js";
import { check } from "./analysis.js";
import { practice } from "./practice.js";
import { resources } from "./resources.js";
import { study } from "./study.js";
import { hunt } from "./hunt.js";
import * as TP from "./teacher.js";
import * as PP from "./parent.js";

const root = document.getElementById("app");
export const state = { user: null, me: null };

// [page, icon, render] or a group [key, icon, null, [sub pages]] that opens under its parent
const MENUS = {
  student: [
    ["g_study", [["dashboard", "home", S.dashboard], ["solve", "target", null, [["practice", "wand", practice], ["check", "steps", check], ["hunt", "search", hunt]]],
      ["assignments", "clipboard", S.assignments]]],
    ["g_learn", [["study", "book", study], ["resources", "library", resources], ["mistakes", "notebook", S.mistakes]]],
    ["g_account", [["profile", "user", S.profile]]],
  ],
  teacher: [
    ["g_manage", [["overview", "grid", TP.overview], ["classes", "users", TP.classes], ["assignments", "clipboard", TP.assignments]]],
    ["g_prepare", [["generator", "print", TP.generator], ["resources", "library", resources]]],
    ["g_account", [["profile", "user", S.profile]]],
  ],
  parent: [
    ["g_family", [["child", "heart", PP.child]]],
    ["g_account", [["profile", "user", S.profile]]],
  ],
};
const TITLES = { dashboard: "m_dashboard", solve: "m_solve", check: "m_check", practice: "m_practice", assignments: "m_assignments", study: "m_study",
  resources: "m_resources", mistakes: "m_mistakes", profile: "m_profile", overview: "m_overview", classes: "m_classes",
  generator: "m_generator", child: "m_child", hunt: "m_hunt" };
const pages = (menu) => menu.flatMap(([, items]) => items).flatMap((it) => (it[3] ? it[3] : [it]));
const HOME = { student: "dashboard", teacher: "overview", parent: "child" };

export async function refreshMe() {
  const me = await api("/api/me");
  state.me = me; state.user = me.user;
  return me;
}

export const go = (path) => { location.hash = path; };

function parseHash() {
  const raw = location.hash.replace(/^#/, "") || "/";
  const [path, query = ""] = raw.split("?");
  return { parts: path.split("/").filter(Boolean), params: new URLSearchParams(query) };
}

async function route() {
  const { parts, params } = parseHash();
  scrollTo(0, 0);
  if (parts[0] !== "app") {
    if (parts[0] === "login") return renderLogin(root, onLogin, state.user);
    if (parts[0] === "register") return state.user ? go(`/app/${HOME[state.user.role]}`) : renderRegister(root, onLogin, params);
    if (parts[0] === "about") return renderAbout(root);
    if (parts[0] === "contact") return renderContact(root);
    await renderLanding(root);
    if (state.user) { // signed-in visitors see who they are, can go back, or switch account
      const right = $(".site-nav .right", root), u = state.user;
      right.innerHTML = `${langSwitch()}<span class="who"><span class="avatar-s">${esc(initials(u.name))}</span><span><b>${esc(u.name)}</b><small>${t("role_" + u.role)}</small></span></span>
        <a class="btn btn-ghost btn-sm" href="#/login">${t("switch_acc")}</a><a class="btn btn-primary btn-sm" href="#/app/${HOME[u.role]}">${t("go_app")}</a>`;
    }
    wireDemoRoles(root);
    return;
  }
  if (!state.user) return go("/login");
  const page = parts[1] || HOME[state.user.role];
  const menu = MENUS[state.user.role];
  const entry = pages(menu).find(([k]) => k === page);
  if (!entry) return go(`/app/${HOME[state.user.role]}`);
  renderShell(page);
  const content = $("#content");
  content.innerHTML = `<div class="skeleton" style="height:140px"></div>`;
  try { await entry[2](content, params, { state, go, refreshMe }); }
  catch (e) {
    if (e.message === "err_auth") { state.user = null; return go("/login"); }
    content.innerHTML = `<div class="callout coral">${icon("alert")}<span>${esc(t(e.message) === e.message ? t("err_generic") : t(e.message))}</span></div>`;
  }
}

function renderShell(page) {
  const u = state.user, menu = MENUS[u.role];
  root.innerHTML = `<div class="shell">
    <aside class="sidebar" id="sidebar">${brand(true)}
      <nav>${menu.map(([g, items]) => `<div class="grp">${t(g)}</div>${items.map(([k, ic, , kids]) => {
        if (!kids) return `<a href="#/app/${k}" class="${k === page ? "on" : ""}">${icon(ic)}<span>${t(TITLES[k])}</span></a>`;
        const open = kids.some(([c]) => c === page);
        return `<button class="nav-grp ${open ? "open" : ""}" data-grp="${k}">${icon(ic)}<span>${t(TITLES[k])}</span><svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 6 6 6-6 6"/></svg></button>
          <div class="sub ${open ? "open" : ""}">${kids.map(([c, cic]) => `<a href="#/app/${c}" class="${c === page ? "on" : ""}">${icon(cic)}<span>${t(TITLES[c])}</span></a>`).join("")}</div>`;
      }).join("")}`).join("")}</nav>
      <div class="me"><div class="avatar-s">${esc(initials(u.name))}</div><div><div class="n">${esc(u.name)}</div><div class="r">${t("role_" + u.role)}</div></div>
        <button id="logout" title="${t("logout")}" aria-label="${t("logout")}">${icon("logout")}</button></div>
    </aside>
    <div class="main-area">
      <div class="topbar"><button class="btn btn-ghost btn-sm burger" id="burger" aria-label="Menu">${icon("menu")}</button>
        <h1>${t(TITLES[page])}</h1><div class="right">${langSwitch()}</div></div>
      <div class="content" id="content"></div>
    </div></div>`;
  $("#logout").addEventListener("click", async () => { await api("/api/logout", { method: "POST" }); state.user = null; go("/"); });
  $("#burger").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  $$("#sidebar nav a").forEach((a) => a.addEventListener("click", () => $("#sidebar").classList.remove("open")));
  $$("#sidebar .nav-grp").forEach((b) => b.addEventListener("click", () => {
    b.classList.toggle("open"); b.nextElementSibling.classList.toggle("open");
  }));
}

const isDemo = (u) => /@demo\.misstep$/.test(u.email || "");
// any [data-demo-role] button signs in as that demo account, from the landing page or the app's top bar
function wireDemoRoles(scope) {
  $$("[data-demo-role]", scope).forEach((b) => b.addEventListener("click", async () => {
    if (state.user && isDemo(state.user) && state.user.role === b.dataset.demoRole) return go(`/app/${HOME[state.user.role]}`);
    b.disabled = true;
    const r = await api("/api/demo-login", { method: "POST", body: { role: b.dataset.demoRole } });
    await onLogin(r.user);
    route();
  }));
}

async function onLogin(user) {
  state.user = user;
  await refreshMe();
  go(`/app/${HOME[user.role]}`);
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-lang]");
  if (!b) return;
  setLang(b.dataset.lang);
  route();
});

addEventListener("hashchange", route);
(async () => {
  try { await refreshMe(); } catch { /* offline or first start */ }
  route();
})();
