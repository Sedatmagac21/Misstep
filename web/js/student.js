// Student pages: dashboard, homework, mistake notebook, profile (the profile is shared by every role).
import { t } from "./i18n.js";
import { dailyBars, heatmap, masteryBars } from "./charts.js";
import { testRow } from "./practice.js";
import { $, $$, api, busy, errText, esc, fmtDate, icon, masteryColor, pct, toast } from "./ui.js";

// ---------- dashboard ----------
export async function dashboard(el, _params, ctx) {
  const [p, asg, tests] = await Promise.all([api("/api/progress"), api("/api/assignments").catch(() => []), api("/api/tests").catch(() => [])]);
  const name = ctx.state.user.name.split(" ")[0];
  const todayN = p.today.correct + p.today.wrong;
  const sub = p.total === 0 ? t("dash_sub_new") : todayN ? t("dash_sub", { n: todayN }) : t("dash_sub_zero", { s: p.streak });
  const diff = p.week - p.prev_week;
  const open = asg.filter((a) => a.done < a.count);
  el.innerHTML = `<div class="grid">
    <div class="welcome"><div><h2>${t("hello")}, ${esc(name)} 👋</h2><p>${sub}</p></div>
      <div class="actions"><a class="btn btn-primary" href="#/app/check">${icon("camera")}${t("m_check")}</a><a class="btn btn-light" href="#/app/practice">${icon("target")}${t("start_test")}</a></div></div>
    <div class="grid g4">
      <div class="card kpi"><span class="l">${icon("layers")}${t("k_total")}</span><span class="v">${p.total}</span><span class="d">${t("correct")} ${p.correct}</span></div>
      <div class="card kpi"><span class="l">${icon("target")}${t("k_acc")}</span><span class="v">${pct(p.accuracy)}</span><span class="d">${t("today")}: ${p.today.correct}/${todayN}</span></div>
      <div class="card kpi"><span class="l">${icon("flame")}${t("k_streak")}</span><span class="v">${p.streak} <span style="font-size:16px;color:var(--muted)">${t("days")}</span></span><span class="d">${t("today")}: ${todayN}</span></div>
      <div class="card kpi"><span class="l">${icon("trend")}${t("k_week")}</span><span class="v">${p.week}</span><span class="d"><span class="${diff >= 0 ? "up" : "down"}">${diff >= 0 ? "+" : ""}${diff}</span> ${t("vs_last")}</span></div>
    </div>
    <div class="grid g-main">
      <div class="card"><div class="card-h"><div><h2>${t("heat_t")}</h2><p>${t("heat_p")}</p></div></div>${heatmap(p.days)}</div>
      <div class="card" style="display:flex;flex-direction:column;gap:14px">
        ${p.recommendation ? `<div><span class="chip amber">${icon("spark")}${t("rec_t")}</span>
          <h3 style="font-size:19px;margin-top:12px">${esc(p.recommendation.topic)}</h3><p class="muted" style="font-size:14px;margin-top:4px">${esc(p.recommendation.name)}</p>
          <p style="font-size:14px;margin-top:8px">${t("rec_p")}</p>
          <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap"><a class="btn btn-primary btn-sm" href="#/app/practice?topic=${encodeURIComponent(p.recommendation.topic_key)}&count=5">${t("practice_this")}</a>
          <a class="btn btn-ghost btn-sm" href="#/app/study?topic=${encodeURIComponent(p.recommendation.topic_key)}">${t("study_this")}</a></div></div>`
          : `<div class="empty">${icon("spark")}<h3>${t("rec_t")}</h3><p>${t("dash_sub_new")}</p></div>`}
        ${open.length ? `<div style="border-top:1px solid var(--line-2);padding-top:14px"><div style="font-weight:800;font-size:14px;margin-bottom:8px">${t("m_assignments")}</div>
          ${open.slice(0, 2).map((a) => `<a class="li" href="#/app/practice?assignment=${a.id}" style="display:flex;gap:10px;align-items:center;padding:8px 0">
            <span class="ic coral" style="width:34px;height:34px;border-radius:10px;display:grid;place-items:center">${icon("clipboard")}</span>
            <span><b style="font-size:14px">${esc(a.title)}</b><br><span class="muted" style="font-size:12.5px">${t("asg_progress", { d: a.done, n: a.count })}${a.due ? ` · ${t("asg_due")} ${fmtDate(a.due)}` : ""}</span></span></a>`).join("")}</div>` : ""}
      </div>
    </div>
    <div class="grid g2">
      <div class="card"><div class="card-h"><div><h2>${t("daily_t")}</h2><p>${t("daily_p")}</p></div></div>${dailyBars(p.days)}</div>
      <div class="card"><div class="card-h"><div><h2>${t("topics_t")}</h2><p>${t("topics_p")}</p></div></div>${masteryBars(p.topics.map((x) => ({ name: x.name, mastery: x.mastery })))}</div>
    </div>
    <div class="card"><div class="card-h"><div><h2>${t("weak_t")}</h2><p>${t("weak_p")}</p></div></div>
      ${p.weakest.length ? `<div class="list">${p.weakest.map((w) => `<div class="li"><span class="dot" style="background:${masteryColor(w.mastery)}"></span>
        <div><div class="t">${esc(w.name)}</div><div class="s">${esc(w.topic)} · ${esc(w.misconception)}</div></div>
        <div class="end"><span class="chip">${pct(w.mastery)} ${t("mastery")}</span><a class="btn btn-ghost btn-sm" href="#/app/practice?rules=${encodeURIComponent(w.id)}&count=5">${t("practice_this")}</a></div></div>`).join("")}</div>`
        : `<div class="empty">${icon("chart")}<p>${t("dash_sub_new")}</p></div>`}
    </div>
    ${tests.length ? `<div class="card"><div class="card-h"><div><h2>${t("past_tests")}</h2><p>${t("past_tests_p")}</p></div><a class="btn btn-ghost btn-sm" href="#/app/practice">${t("start_test")}</a></div>
      <div class="list">${tests.slice(0, 4).map(testRow).join("")}</div></div>` : ""}</div>`;
}

// ---------- assignments ----------
export async function assignments(el) {
  const list = await api("/api/assignments");
  el.innerHTML = `<div class="grid g-main" style="align-items:start">
    <div class="card"><div class="card-h"><div><h2>${t("asg_t")}</h2><p>${t("asg_p")}</p></div></div>
      ${list.length ? `<div class="list">${list.map((a) => {
        const done = a.done >= a.count;
        return `<div class="li"><span class="ic ${done ? "green" : "coral"}" style="width:42px;height:42px;border-radius:12px;display:grid;place-items:center;flex:none">${icon(done ? "checkc" : "clipboard")}</span>
          <div style="flex:1;min-width:0"><div class="t">${esc(a.title)}</div><div class="s">${esc(a.class_name)} · ${esc(a.topics.join(", "))} · ${t("lv_" + a.level)}${a.due ? ` · ${t("asg_due")} ${fmtDate(a.due)}` : ""}</div>
            <div class="track" style="height:6px;background:var(--line-2);border-radius:9px;margin-top:8px;overflow:hidden"><div style="height:100%;width:${(a.done / a.count) * 100}%;background:${done ? "#1E9E5A" : "#FF5A5F"}"></div></div></div>
          <div class="end"><span class="chip">${t("asg_progress", { d: a.done, n: a.count })}</span>${done ? `<span class="chip green">${t("asg_done")}</span>` : `<a class="btn btn-primary btn-sm" href="#/app/practice?assignment=${a.id}">${t("asg_start")}</a>`}</div></div>`;
      }).join("")}</div>` : `<div class="empty">${icon("clipboard")}<h3>${t("asg_empty")}</h3><p>${t("asg_empty_s")}</p></div>`}
    </div>
    ${joinCard()}
  </div>`;
  wireJoin(el, () => assignments(el));
}

const joinCard = () => `<div class="card"><h2>${t("join_t")}</h2><p class="muted" style="font-size:14px;margin:4px 0 14px">${t("join_p")}</p>
  <div style="display:flex;gap:8px"><input class="input mono" id="jc" maxlength="6" style="text-transform:uppercase;letter-spacing:.12em" placeholder="ABC123"><button class="btn btn-dark" id="jb">${t("join_btn")}</button></div></div>`;
function wireJoin(el, after) {
  $("#jb", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true);
    try { const c = await api("/api/join-class", { method: "POST", body: { code: $("#jc", el).value } }); toast(t("joined", { c: c.name })); after(); }
    catch (err) { toast(errText(err), true); busy(btn, false); }
  });
}

// ---------- mistake notebook ----------
export async function mistakes(el) {
  const items = await api("/api/mistakes");
  const rules = [...new Set(items.filter((m) => m.rule).map((m) => m.rule.id))];
  el.innerHTML = `<div class="card"><div class="card-h"><div><h2>${t("mist_t")}</h2><p>${t("mist_p")}</p></div>
    ${rules.length ? `<a class="btn btn-primary btn-sm" href="#/app/practice?rules=${encodeURIComponent(rules.slice(0, 6).join(","))}&count=${Math.min(20, rules.length * 3)}">${icon("target")}${t("mist_test")}</a>` : ""}</div>
    ${items.length ? `<div class="list">${items.map((m) => `<div class="li" style="align-items:flex-start">
      <span class="ic coral" style="width:40px;height:40px;border-radius:12px;display:grid;place-items:center;flex:none">${icon(m.kind === "solution" ? "camera" : "target")}</span>
      <div style="min-width:0;flex:1"><div class="t mono" style="font-size:15.5px">${esc(m.problem)}</div>
        <div class="s" style="margin-top:4px">${fmtDate(m.ts)}${m.rule ? ` · <b style="color:var(--coral-d)">${esc(m.rule.name)}</b>` : ""}</div>
        ${m.picked ? `<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap"><span class="chip coral">${t("you_picked")}: ${esc(m.picked)}</span><span class="chip green">${t("correct_answer")}: ${esc(m.answer)}</span></div>` : ""}
        ${m.lines && m.kind === "solution" ? `<div class="mono muted" style="font-size:13px;margin-top:6px">${m.lines.slice(1).map(esc).join(" → ")}</div>` : ""}</div>
      ${m.rule ? `<div class="end"><a class="btn btn-ghost btn-sm" href="#/app/practice?rules=${encodeURIComponent(m.rule.id)}&count=5">${t("redo")}</a></div>` : ""}</div>`).join("")}</div>`
      : `<div class="empty">${icon("notebook")}<h3>${t("mist_empty")}</h3><p>${t("mist_empty_p")}</p></div>`}</div>`;
}

// ---------- profile ----------
export async function profile(el, _p, ctx) {
  const me = await ctx.refreshMe(), u = me.user;
  el.innerHTML = `<div class="grid g2" style="align-items:start">
    <div class="card"><h2 style="margin-bottom:16px">${t("prof_t")}</h2>
      <div class="field"><label>${t("name")}</label><input class="input" id="pn" value="${esc(u.name)}"></div>
      <div class="field" style="margin-top:12px"><label>${t("email")}</label><input class="input" value="${esc(u.email)}" disabled></div>
      ${u.role === "student" ? `<div class="field" style="margin-top:12px"><label>${t("grade")}</label><select class="input" id="pg">${[7, 8, 9, 10].map((g) => `<option value="${g}" ${g === u.grade ? "selected" : ""}>${t("grade_n", { n: g })}</option>`).join("")}</select></div>` : ""}
      <button class="btn btn-primary" id="ps" style="margin-top:16px">${t("save")}</button></div>
    <div class="grid">
      ${u.role === "student" ? `<div class="card"><h2>${t("prof_family")}</h2><p class="muted" style="font-size:14px;margin:4px 0 14px">${t("prof_family_p")}</p>
        <div class="code-box">${esc(u.family_code)}<button data-copy="${esc(u.family_code)}">${t("copy")}</button></div></div>
        <div class="card"><h2 style="margin-bottom:10px">${t("prof_classes")}</h2>${(me.classes || []).length ? `<div class="list">${me.classes.map((c) => `<div class="li"><span class="dot" style="background:var(--coral)"></span><div><div class="t">${esc(c.name)}</div><div class="s">${esc(c.teacher)}</div></div></div>`).join("")}</div>` : `<p class="muted">${t("asg_empty_s")}</p>`}</div>
        ${joinCard()}` : ""}
      ${u.role === "teacher" ? `<div class="card"><h2 style="margin-bottom:10px">${t("m_classes")}</h2>${(me.classes || []).map((c) => `<div class="li" style="display:flex;justify-content:space-between;align-items:center;padding:8px 0"><b>${esc(c.name)}</b><span class="code-box" style="font-size:14px">${esc(c.code)}<button data-copy="${esc(c.code)}">${t("copy")}</button></span></div>`).join("") || `<p class="muted">${t("t_no_class_p")}</p>`}</div>` : ""}
      ${u.role === "parent" ? `<div class="card"><h2 style="margin-bottom:10px">${t("m_child")}</h2>${(me.children || []).map((c) => `<div class="li" style="padding:8px 0"><b>${esc(c.name)}</b> <span class="muted">· ${t("grade_n", { n: c.grade })}</span></div>`).join("") || `<p class="muted">${t("p_none")}</p>`}</div>` : ""}
    </div></div>`;
  $("#ps", el).addEventListener("click", async () => {
    await api("/api/profile", { method: "POST", body: { name: $("#pn", el).value, grade: u.role === "student" ? Number($("#pg", el).value) : null } });
    await ctx.refreshMe(); toast(t("saved")); ctx.go("/app/profile?r=" + Date.now());
  });
  $$("[data-copy]", el).forEach((b) => b.addEventListener("click", () => { navigator.clipboard?.writeText(b.dataset.copy); toast(t("copied")); }));
  if (u.role === "student") wireJoin(el, () => profile(el, _p, ctx));
}

