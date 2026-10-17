// Teacher pages: class overview, class management, homework, worksheet generator.
import { t } from "./i18n.js";
import { heatmap, masteryBars } from "./charts.js";
import { download } from "./analysis.js";
import { generatorForm } from "./practice.js";
import { $, $$, api, busy, errText, esc, fmtDate, icon, initials, masteryColor, modal, pct, toast } from "./ui.js";

const LEVELS = ["easy", "medium", "hard"];

function newClassCard() {
  return `<div class="card"><h2>${t("t_new_class")}</h2>
    <div style="display:flex;gap:8px;margin-top:12px"><input class="input" id="cn" placeholder="${esc(t("t_class_name"))}: 8-A"><button class="btn btn-primary" id="cb">${icon("plus")}${t("t_create")}</button></div></div>`;
}
function wireNewClass(el, after) {
  $("#cb", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true);
    try { await api("/api/classes", { method: "POST", body: { name: $("#cn", el).value } }); after(); }
    catch (err) { toast(errText(err), true); busy(btn, false); }
  });
}

async function studentModal(id, name) {
  const m = modal(`<div style="display:flex;align-items:center;gap:12px"><div class="avatar-s">${esc(initials(name))}</div><h3>${esc(name)}</h3>
    <button class="btn btn-ghost btn-sm" data-close style="margin-left:auto">${t("close")}</button></div><div id="sm"><div class="skeleton" style="height:200px"></div></div>`);
  m.querySelector(".modal").style.width = "min(860px, 100%)";
  const p = await api(`/api/progress?student_id=${id}`);
  m.querySelector("#sm").innerHTML = `<div class="grid g4" style="grid-template-columns:repeat(4,1fr)">
      <div class="kpi"><span class="l">${t("k_total")}</span><span class="v">${p.total}</span></div>
      <div class="kpi"><span class="l">${t("k_acc")}</span><span class="v">${pct(p.accuracy)}</span></div>
      <div class="kpi"><span class="l">${t("k_streak")}</span><span class="v">${p.streak}</span></div>
      <div class="kpi"><span class="l">${t("k_week")}</span><span class="v">${p.week}</span></div></div>
    <div style="margin-top:14px">${heatmap(p.days)}</div>
    <div style="margin-top:16px">${masteryBars(p.topics.map((x) => ({ name: x.name, mastery: x.mastery })))}</div>`;
}

export async function overview(el) {
  const classes = await api("/api/classes");
  if (!classes.length) {
    el.innerHTML = `<div class="grid g-main" style="align-items:start"><div class="card"><div class="empty">${icon("users")}<h3>${t("t_no_class")}</h3><p>${t("t_no_class_p")}</p></div></div>${newClassCard()}</div>`;
    return wireNewClass(el, () => overview(el));
  }
  const asg = await api("/api/assignments");
  const students = classes.flatMap((c) => c.students);
  const active = students.filter((s) => s.week > 0).length;
  const total = classes.reduce((a, c) => a + c.total, 0);
  const acc = total ? classes.reduce((a, c) => a + (c.accuracy || 0) * c.total, 0) / total : null;
  el.innerHTML = `<div class="grid">
    <div class="grid g4">
      <div class="card kpi"><span class="l">${icon("users")}${t("t_students")}</span><span class="v">${students.length}</span><span class="d">${classes.length} ${t("m_classes").toLowerCase()}</span></div>
      <div class="card kpi"><span class="l">${icon("flame")}${t("t_active")}</span><span class="v">${active}</span><span class="d">/ ${students.length}</span></div>
      <div class="card kpi"><span class="l">${icon("target")}${t("t_class_acc")}</span><span class="v">${pct(acc)}</span><span class="d">${total} ${t("questions")}</span></div>
      <div class="card kpi"><span class="l">${icon("clipboard")}${t("t_asg")}</span><span class="v">${asg.length}</span><span class="d"><a href="#/app/assignments" style="color:var(--coral-d);font-weight:700">${t("t_new_asg")} →</a></span></div>
    </div>
    ${classes.map((c) => `<div class="card">
      <div class="card-h"><div><h2 style="font-size:20px"><a href="#/app/classes?id=${c.id}">${esc(c.name)} →</a></h2><p>${c.students.length} ${t("t_students").toLowerCase()} · ${t("t_class_acc")} ${pct(c.accuracy)}</p></div>
        <div class="code-box" title="${esc(t("t_code_share"))}">${esc(c.code)}<button data-copy="${esc(c.code)}">${t("copy")}</button></div></div>
      ${c.students.length ? `
      <div class="grid g-main" style="align-items:start">
        <div><div style="font-weight:800;margin-bottom:4px">${t("t_matrix")}</div><p class="muted" style="font-size:13px;margin-bottom:10px">${t("t_matrix_p")}</p>
          <div style="overflow-x:auto"><table class="tbl"><thead><tr><th>${t("t_students")}</th>${c.topics.map((tp) => `<th class="topic-h" title="${esc(tp.name)}">${esc(tp.name)}</th>`).join("")}<th>${t("k_acc")}</th><th>${t("t_last")}</th></tr></thead>
          <tbody>${c.students.map((s) => `<tr class="click" data-sid="${s.id}" data-sn="${esc(s.name)}"><td><b>${esc(s.name)}</b></td>
            ${c.topics.map((tp) => { const m = s.topics[tp.key]; return `<td style="text-align:center"><span class="cell-m" style="background:${masteryColor(m)};color:${m == null ? "#94A3B8" : "#fff"}">${m == null ? "–" : Math.round(m * 100)}</span></td>`; }).join("")}
            <td>${pct(s.accuracy)}</td><td class="muted">${fmtDate(s.last_active)}</td></tr>`).join("")}</tbody></table></div></div>
        <div><div style="font-weight:800;margin-bottom:10px">${t("t_common")}</div>
          <div class="list">${c.weak.map((w) => `<div class="li"><span class="dot" style="background:${masteryColor(w.mastery)}"></span><div><div class="t">${esc(w.name)}</div><div class="s">${esc(w.misconception)}</div></div><div class="end"><span class="chip">${pct(w.mastery)}</span></div></div>`).join("")}</div>
          <a class="btn btn-primary btn-sm" style="margin-top:12px" href="#/app/assignments">${icon("clipboard")}${t("t_new_asg")}</a></div>
      </div>` : `<div class="empty">${icon("users")}<p>${t("t_no_students")}</p><p style="margin-top:8px">${t("t_code_share")}: <b class="mono">${esc(c.code)}</b></p></div>`}
    </div>`).join("")}</div>`;
  $$("[data-copy]", el).forEach((b) => b.addEventListener("click", () => { navigator.clipboard?.writeText(b.dataset.copy); toast(t("copied")); }));
  $$("tr[data-sid]", el).forEach((tr) => tr.addEventListener("click", () => studentModal(tr.dataset.sid, tr.dataset.sn)));
}

// columns of the sortable class table: [key, label, value for sorting, cell html]
const COLS = [
  ["name", "name", (s) => s.name.toLocaleLowerCase("tr"), (s) => `<b>${esc(s.name)}</b>`],
  ["total", "c_total", (s) => s.total, (s) => s.total],
  ["correct", "correct", (s) => s.correct, (s) => `<span style="color:#1E7B3A;font-weight:700">${s.correct}</span>`],
  ["wrong", "c_wrong", (s) => s.wrong, (s) => `<span style="color:#C62828;font-weight:700">${s.wrong}</span>`],
  ["accuracy", "k_acc", (s) => s.accuracy ?? -1, (s) => `<span class="cell-m" style="background:${masteryColor(s.accuracy)};color:${s.accuracy == null ? "#94A3B8" : "#fff"}">${pct(s.accuracy)}</span>`],
  ["week", "k_week", (s) => s.week, (s) => s.week],
  ["streak", "c_streak", (s) => s.streak, (s) => `${s.streak ? icon("flame") : ""}${s.streak}`],
  ["homework", "c_hw", (s) => s.homework ?? -1, (s) => (s.homework == null ? "–" : pct(s.homework))],
  ["last_active", "c_last", (s) => s.last_active || "", (s) => `<span class="muted">${s.last_active ? fmtDate(s.last_active) : "–"}</span>`],
  ["weakest", "t_weakest", (s) => s.weakest?.mastery ?? 2, (s) => (s.weakest ? `<span class="chip coral">${esc(s.weakest.name)}</span>` : "–")],
];

export async function classes(el, params) {
  const list = await api("/api/classes");
  const sel = list.find((c) => String(c.id) === params.get("id"));
  if (sel) return classDetail(el, sel);
  el.innerHTML = `<div class="grid g-main" style="align-items:start">
    <div class="grid">${list.length ? list.map((c) => `<a class="card class-card" href="#/app/classes?id=${c.id}">
      <div class="card-h"><div><h2 style="font-size:19px">${esc(c.name)}</h2><p>${c.students.length} ${t("t_students").toLowerCase()} · ${t("t_class_acc")} ${pct(c.accuracy)} · ${t("k_week")} ${c.week}</p></div>
        <div class="code-box" title="${esc(t("t_code_share"))}">${esc(c.code)}<button data-copy="${esc(c.code)}">${t("copy")}</button></div></div>
      <div class="class-mini">${c.students.slice(0, 8).map((s) => `<span class="avatar-s" title="${esc(s.name)}" style="background:${masteryColor(s.accuracy)}">${esc(initials(s.name))}</span>`).join("")}
        <span class="go">${t("c_open")} ${icon("arrow")}</span></div></a>`).join("")
      : `<div class="card"><div class="empty">${icon("users")}<h3>${t("t_no_class")}</h3><p>${t("t_no_class_p")}</p></div></div>`}</div>
    ${newClassCard()}</div>`;
  wireNewClass(el, () => classes(el, params));
  $$("[data-copy]", el).forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); navigator.clipboard?.writeText(b.dataset.copy); toast(t("copied")); }));
}

function classDetail(el, c) {
  let key = "accuracy", dir = 1; // ascending accuracy first: who needs help is on top
  el.innerHTML = `<div class="grid class-detail">
    <div class="welcome" style="padding:22px 26px"><div><a href="#/app/classes" class="muted" style="font-size:13px;font-weight:700">← ${t("m_classes")}</a>
      <h2 style="margin-top:4px">${esc(c.name)}</h2><p>${c.students.length} ${t("t_students").toLowerCase()} · ${t("t_code_share")}: <b class="mono">${esc(c.code)}</b></p></div>
      <div class="actions"><button class="btn btn-primary" id="rep">${icon("download")}${t("c_report")}</button><a class="btn btn-light" href="#/app/assignments">${icon("clipboard")}${t("t_new_asg")}</a></div></div>
    <div class="grid g4">
      <div class="card kpi"><span class="l">${icon("users")}${t("t_students")}</span><span class="v">${c.students.length}</span><span class="d">${c.students.filter((s) => s.week).length} ${t("t_active").toLowerCase()}</span></div>
      <div class="card kpi"><span class="l">${icon("layers")}${t("k_week")}</span><span class="v">${c.week}</span><span class="d">${t("questions")}</span></div>
      <div class="card kpi"><span class="l">${icon("target")}${t("c_week_acc")}</span><span class="v">${pct(c.week_accuracy)}</span><span class="d">${t("t_class_acc")} ${pct(c.accuracy)}</span></div>
      <div class="card kpi"><span class="l">${icon("alert")}${t("c_need")}</span><span class="v">${c.students.filter((s) => !s.week || (s.week_accuracy != null && s.week_accuracy < 0.5)).length}</span><span class="d">${t("c_need_d")}</span></div></div>
    <div class="card"><div class="card-h"><div><h2>${t("c_table")}</h2><p>${t("c_table_p")}</p></div>
      <div class="search" style="max-width:240px">${icon("search")}<input class="input" id="flt" placeholder="${esc(t("c_filter"))}"></div></div>
      ${c.students.length ? `<div style="overflow-x:auto"><table class="tbl sortable"><thead><tr>${COLS.map(([k, l]) => `<th data-k="${k}"><button>${t(l)}<span class="ar"></span></button></th>`).join("")}</tr></thead><tbody id="rows"></tbody></table></div>`
        : `<div class="empty">${icon("users")}<p>${t("t_no_students")}</p></div>`}</div>
    <div class="grid g2" style="align-items:start">
      <div class="card"><div class="card-h"><div><h2>${t("topics_t")}</h2><p>${t("c_topics_p")}</p></div></div>${masteryBars(c.topic_mastery.map((x) => ({ name: x.name, mastery: x.mastery })))}</div>
      <div class="card"><div class="card-h"><div><h2>${t("t_common")}</h2></div></div>
        <div class="list">${c.weak.map((w) => `<div class="li"><span class="dot" style="background:${masteryColor(w.mastery)}"></span><div><div class="t">${esc(w.name)}</div><div class="s">${esc(w.misconception)}</div></div><div class="end"><span class="chip">${pct(w.mastery)}</span></div></div>`).join("") || `<p class="muted">–</p>`}</div></div>
    </div></div>`;
  const body = $("#rows", el);
  const draw = () => {
    const q = ($("#flt", el).value || "").toLocaleLowerCase("tr");
    const col = COLS.find(([k]) => k === key);
    const rows = c.students.filter((s) => s.name.toLocaleLowerCase("tr").includes(q))
      .sort((a, b) => { const x = col[2](a), y = col[2](b); return (x < y ? -1 : x > y ? 1 : 0) * dir; });
    body.innerHTML = rows.map((s) => `<tr class="click" data-sid="${s.id}" data-sn="${esc(s.name)}">${COLS.map(([, , , cell]) => `<td>${cell(s)}</td>`).join("")}</tr>`).join("");
    $$("th[data-k]", el).forEach((th) => { th.classList.toggle("on", th.dataset.k === key); th.querySelector(".ar").textContent = th.dataset.k === key ? (dir > 0 ? "▲" : "▼") : "↕"; });
    $$("tr[data-sid]", body).forEach((tr) => tr.addEventListener("click", () => studentModal(tr.dataset.sid, tr.dataset.sn)));
  };
  if (body) {
    $$("th[data-k]", el).forEach((th) => th.addEventListener("click", () => {
      if (key === th.dataset.k) dir = -dir; else { key = th.dataset.k; dir = key === "name" || key === "accuracy" || key === "weakest" ? 1 : -1; }
      draw();
    }));
    $("#flt", el).addEventListener("input", draw);
    draw();
  }
  $("#rep", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true);
    try {
      const resp = await api(`/api/classes/${c.id}/report.pdf`, { raw: true });
      download(await resp.blob(), `misstep-${c.name}-${t("c_report_file")}.pdf`);
    } catch (err) { toast(errText(err), true); }
    busy(btn, false);
  });
}

export async function assignments(el) {
  const [cls, topics, list] = await Promise.all([api("/api/classes"), api("/api/topics"), api("/api/assignments")]);
  const chosen = new Set();
  let level = "medium";
  el.innerHTML = `<div class="grid g-main" style="align-items:start">
    <div class="grid">${list.length ? list.map((a) => `<div class="card">
      <div class="card-h"><div><h2>${esc(a.title)}</h2><p>${esc(a.class_name)} · ${esc(a.topics.join(", "))} · ${t("lv_" + a.level)} · ${a.count} ${t("questions")}${a.due ? ` · ${t("asg_due")} ${fmtDate(a.due)}` : ""}</p></div></div>
      <div style="font-weight:700;font-size:13px;margin-bottom:8px">${t("t_asg_progress")}</div>
      <div class="bars-list">${a.progress.map((p) => `<div class="bar-row"><span class="name">${esc(p.student)}</span><span class="pct">${t("asg_progress", { d: p.done, n: a.count })} · ${t("correct")} ${p.right}</span>
        <div class="track"><div class="fill" style="width:${(p.done / a.count) * 100}%;background:${p.done >= a.count ? "#1E9E5A" : "#FCA311"}"></div></div></div>`).join("") || `<p class="muted">${t("t_no_students")}</p>`}</div>
    </div>`).join("") : `<div class="card"><div class="empty">${icon("clipboard")}<h3>${t("asg_empty")}</h3></div></div>`}</div>
    <div class="card" style="position:sticky;top:96px"><h2 style="margin-bottom:14px">${t("t_new_asg")}</h2>
      ${cls.length ? `<div class="field"><label>${t("t_asg_title")}</label><input class="input" id="at" placeholder="${esc(t("t_asg_title"))}"></div>
      <div class="field" style="margin-top:12px"><label>${t("t_asg_class")}</label><select class="input" id="ac">${cls.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></div>
      <div class="field" style="margin-top:12px"><label>${t("topic")}</label><div style="display:flex;flex-wrap:wrap;gap:6px" id="atp">${topics.map((x) => `<button class="chip" style="border:0;cursor:pointer" data-t="${esc(x.key)}">${esc(x.name)}</button>`).join("")}</div></div>
      <div class="field" style="margin-top:12px"><label>${t("level")}</label><div class="seg" id="alv">${LEVELS.map((lv) => `<button data-lv="${lv}">${t("lv_" + lv)}</button>`).join("")}</div></div>
      <div class="grid g2" style="margin-top:12px"><div class="field"><label>${t("step_count")}</label><input class="input" id="an" type="number" min="1" max="20" value="10"></div>
        <div class="field"><label>${t("t_asg_due")}</label><input class="input" id="ad" type="date"></div></div>
      <button class="btn btn-primary" id="ab" style="width:100%;margin-top:16px">${icon("clipboard")}${t("t_asg_create")}</button>`
      : `<p class="muted">${t("t_no_class_p")}</p><a class="btn btn-primary btn-sm" style="margin-top:10px" href="#/app/classes">${t("t_new_class")}</a>`}
    </div></div>`;
  if (!cls.length) return;
  const sync = () => {
    $$("#atp [data-t]", el).forEach((b) => { b.className = `chip ${chosen.has(b.dataset.t) ? "coral" : ""}`; });
    $$("#alv button", el).forEach((b) => b.classList.toggle("on", b.dataset.lv === level));
  };
  $$("#atp [data-t]", el).forEach((b) => b.addEventListener("click", () => { chosen.has(b.dataset.t) ? chosen.delete(b.dataset.t) : chosen.add(b.dataset.t); sync(); }));
  $$("#alv button", el).forEach((b) => b.addEventListener("click", () => { level = b.dataset.lv; sync(); }));
  sync();
  $("#ab", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true);
    try {
      await api("/api/assignments", { method: "POST", body: { class_id: Number($("#ac", el).value), title: $("#at", el).value, topics: [...chosen], level,
        count: Math.min(20, Math.max(1, Number($("#an", el).value) || 10)), due: $("#ad", el).value || null } });
      toast(t("t_asg_made")); assignments(el);
    } catch (err) { toast(errText(err), true); busy(btn, false); }
  });
}

export async function generator(el, params) {
  el.innerHTML = `<div class="grid g-main" style="align-items:start">
    <div class="card"><div class="card-h"><div><h2>${t("t_gen_t")}</h2><p>${t("t_gen_p")}</p></div></div><div id="form"></div></div>
    <div class="card" id="out"><div class="empty">${icon("print")}<h3>${t("t_gen_t")}</h3><p>${t("f3_p")}</p></div></div></div>`;
  await generatorForm($("#form", el), { params, onResult: (r) => {
    const out = $("#out", el);
    $("#gen", el) && (() => { const b = $("#gen", el); b.disabled = false; if (b.dataset.label) b.innerHTML = b.dataset.label; })();
    out.innerHTML = `<div class="card-h"><div><h2>${r.made} ${t("questions")}</h2>${r.understood ? `<p>${t("understood")}: ${esc(r.understood)}</p>` : ""}</div>
      <button class="btn btn-dark btn-sm" id="ws">${icon("print")}${t("worksheet_btn")}</button></div>
      <div class="list">${r.questions.map((q, k) => `<div class="li" style="align-items:flex-start"><b style="width:26px">${k + 1}.</b>
        <div style="flex:1;min-width:0"><div class="s">${esc(q.instruction)} · ${t("lv_" + q.level)}</div>${q.story ? `<div class="s" style="color:#5E3E00">${esc(q.story)}</div>` : ""}<div class="t mono" style="font-size:16px;margin:4px 0">${esc(q.problem_display)}</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">${q.choices.map((c, j) => `<span class="chip ${j === q.answer_index ? "green" : q.traps[j] ? "coral" : ""}" title="${q.traps[j] ? esc(q.traps[j]) : ""}">${"ABCD"[j]}) ${esc(c)}</span>`).join("")}</div></div></div>`).join("")}</div>
      <p class="hint" style="margin-top:12px">${icon("shield", "")} ${t("verified")} · <span class="chip green">${t("answer_key")}</span> <span class="chip coral">${t("trap_of")}</span></p>`;
    $("#ws", el).addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      busy(btn, true);
      try {
        const resp = await api("/api/worksheet.pdf", { method: "POST", raw: true, body: { question_ids: r.questions.map((q) => q.id), title: t("t_gen_t") } });
        download(await resp.blob(), "misstep-calisma-kagidi.pdf");
      } catch (err) { toast(errText(err), true); }
      busy(btn, false);
    });
  } });
}
