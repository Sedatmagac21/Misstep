// Parent page: every linked child at a glance, then one child's progress, homework and tests.
import { t } from "./i18n.js";
import { dailyBars, heatmap, masteryBars, ring } from "./charts.js";
import { testRow } from "./practice.js";
import { $, $$, api, busy, errText, esc, fmtDate, icon, initials, masteryColor, pct, toast } from "./ui.js";

const weekAcc = (p) => {
  const last7 = p.days.slice(-7), c = last7.reduce((a, d) => a + d.correct, 0), n = last7.reduce((a, d) => a + d.correct + d.wrong, 0);
  return n ? c / n : null;
};

export async function child(el, params, ctx) {
  const me = await ctx.refreshMe();
  const kids = me.children || [];
  const addCard = `<div class="kid-card add" id="add"><span class="kid-av">${icon("plus")}</span><b>${t("p_add")}</b>
    <div class="add-f"><input class="input mono" id="fc" maxlength="6" placeholder="ABC123"><button class="btn btn-dark btn-sm" id="fb">${t("p_link_btn")}</button></div>
    <span class="muted" style="font-size:12.5px">${t("p_link_p")}</span></div>`;
  if (!kids.length) {
    el.innerHTML = `<div class="grid"><div class="card"><div class="empty">${icon("heart")}<h3>${t("p_none")}</h3><p>${t("p_link_p")}</p></div></div><div class="kid-row">${addCard}</div></div>`;
    return wire();
  }
  const all = await Promise.all(kids.map((k) => api(`/api/progress?student_id=${k.id}`)));
  const idx = Math.max(0, kids.findIndex((k) => String(k.id) === params.get("id")));
  const kid = kids[idx], p = all[idx];
  const [asg, tests] = await Promise.all([api(`/api/assignments?student_id=${kid.id}`).catch(() => []), api(`/api/tests?student_id=${kid.id}`).catch(() => [])]);
  const first = esc(kid.name.split(" ")[0]);
  const weakTopic = [...p.topics].filter((x) => x.mastery != null).sort((a, b) => a.mastery - b.mastery)[0];
  const acc = weekAcc(p);
  const openHw = asg.filter((a) => a.done < a.count);
  el.innerHTML = `<div class="grid">
    <div><div class="sec-t">${t("p_kids")} <span class="muted">· ${kids.length}</span></div>
      <div class="kid-row">${kids.map((k, i) => {
        const kp = all[i], ka = weekAcc(kp);
        return `<button class="kid-card ${i === idx ? "on" : ""}" data-kid="${k.id}"><span class="kid-av">${esc(initials(k.name))}</span>
          <b>${esc(k.name)}</b><span class="muted" style="font-size:13px">${t("grade_n", { n: k.grade })}</span>
          <div class="kid-stats"><span><b>${kp.week}</b> ${t("p_q_week")}</span><span><b style="color:${masteryColor(ka)}">${pct(ka)}</b> ${t("k_acc").toLowerCase()}</span><span>${icon("flame")}<b>${kp.streak}</b></span></div></button>`;
      }).join("")}${addCard}</div></div>
    <div class="welcome"><div class="avatar-s" style="width:56px;height:56px;font-size:20px;border-radius:16px">${esc(initials(kid.name))}</div>
      <div><h2>${esc(kid.name)}</h2><p>${t("grade_n", { n: kid.grade })} · ${p.last_active ? t("p_last", { d: fmtDate(p.last_active) }) : t("p_sub")}</p></div></div>
    <div class="grid g-main" style="align-items:start">
      <div class="card"><div class="card-h"><div><h2>${t("p_week")}</h2></div></div>
        <div class="result-ring">${ring(p.week ? acc : null, 120)}
          <p style="font-size:16px;line-height:1.6">${p.week ? t("p_summary", { n: first, w: p.week, a: Math.round((acc || 0) * 100), t: esc(weakTopic ? weakTopic.name : "–") }) : t("p_summary_zero", { n: first })}</p></div>
        <div class="grid g3" style="margin-top:18px;grid-template-columns:repeat(3,1fr)">
          <div class="kpi"><span class="l">${icon("flame")}${t("k_streak")}</span><span class="v">${p.streak}</span></div>
          <div class="kpi"><span class="l">${icon("layers")}${t("k_total")}</span><span class="v">${p.total}</span></div>
          <div class="kpi"><span class="l">${icon("target")}${t("k_acc")}</span><span class="v">${pct(p.accuracy)}</span></div></div></div>
      <div class="card"><div class="card-h"><div><h2>${t("p_hw")}</h2><p>${openHw.length ? t("p_hw_open", { n: openHw.length }) : t("p_hw_p")}</p></div></div>
        ${asg.length ? `<div class="list">${asg.map((a) => {
          const done = a.done >= a.count, late = !done && a.due && new Date(a.due) < new Date(new Date().toDateString());
          return `<div class="li" style="align-items:flex-start"><span class="ic ${done ? "green" : late ? "coral" : "amber"} sq">${icon(done ? "checkc" : "clipboard")}</span>
            <div style="flex:1;min-width:0"><div class="t">${esc(a.title)}</div><div class="s">${esc(a.class_name)} · ${esc(a.topics.join(", "))}${a.due ? ` · ${t("asg_due")} ${fmtDate(a.due)}` : ""}</div>
              <div class="track thin"><div style="width:${(a.done / a.count) * 100}%;background:${done ? "#1E9E5A" : "#FCA311"}"></div></div></div>
            <div class="end"><span class="chip ${done ? "green" : late ? "coral" : ""}">${done ? t("asg_done") : late ? t("p_late") : t("asg_progress", { d: a.done, n: a.count })}</span></div></div>`;
        }).join("")}</div>` : `<div class="empty" style="padding:20px">${icon("clipboard")}<p>${t("p_hw_none")}</p></div>`}</div>
    </div>
    <div class="card"><div class="card-h"><div><h2>${t("heat_t")}</h2><p>${t("heat_p")}</p></div></div>${heatmap(p.days)}</div>
    <div class="grid g2">
      <div class="card"><div class="card-h"><div><h2>${t("daily_t")}</h2><p>${t("daily_p")}</p></div></div>${dailyBars(p.days)}</div>
      <div class="card"><div class="card-h"><div><h2>${t("topics_t")}</h2><p>${t("topics_p")}</p></div></div>${masteryBars(p.topics.map((x) => ({ name: x.name, mastery: x.mastery })))}</div>
    </div>
    <div class="grid g2" style="align-items:start">
      <div class="card"><div class="card-h"><div><h2>${t("p_tests_t")}</h2><p>${t("p_tests_p")}</p></div></div>
        ${tests.length ? `<div class="list">${tests.slice(0, 5).map(testRow).join("")}</div>` : `<p class="muted">${t("past_tests_empty")}</p>`}</div>
      <div class="card"><div class="card-h"><div><h2>${t("weak_t")}</h2></div></div>
        ${p.weakest.length ? `<div class="list">${p.weakest.map((w) => `<div class="li"><span class="dot" style="background:${masteryColor(w.mastery)}"></span><div><div class="t">${esc(w.name)}</div><div class="s">${esc(w.topic)}</div></div><div class="end"><span class="chip">${pct(w.mastery)}</span></div></div>`).join("")}</div>` : `<p class="muted">${t("dash_sub_new")}</p>`}
        <div class="callout blue" style="margin-top:14px">${icon("heart")}<div><b>${t("p_tip_t")}</b><br>${t("p_tip")}</div></div></div>
    </div>
  </div>`;
  $$("[data-kid]", el).forEach((b) => b.addEventListener("click", () => ctx.go(`/app/child?id=${b.dataset.kid}`)));
  wire();

  function wire() {
    $("#fb", el).addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      busy(btn, true);
      try { const k = await api("/api/link-child", { method: "POST", body: { code: $("#fc", el).value } }); toast(t("p_linked", { n: k.name })); ctx.go(`/app/child?id=${k.id}&r=${Date.now()}`); }
      catch (err) { toast(errText(err), true); busy(btn, false); }
    });
  }
}
