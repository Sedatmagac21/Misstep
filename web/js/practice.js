// "Soru üret": build a test (topic, difficulty or adaptive, count, free request), take it, then see the evaluation.
import { t } from "./i18n.js";
import { levelPath, pie } from "./charts.js";
import { counterHTML, explanationHTML, stepsHTML } from "./analysis.js";
import { $, $$, api, busy, errText, esc, fmtDate, icon, masteryColor, pct, toast } from "./ui.js";

export const LEVELS = ["easy", "medium", "hard"];
export const lvlBars = (lv) => `<span class="lvl">${[0, 1, 2].map((i) => `<i class="${i <= LEVELS.indexOf(lv) ? "f" : ""}"></i>`).join("")}</span>`;
const fmtTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

// ---------- the form (also used by the teacher's generate & print page) ----------
export async function generatorForm(el, { params, progress = null, onResult, student = false }) {
  const topics = await api("/api/topics");
  const mastery = progress ? Object.fromEntries(progress.topics.map((x) => [x.key, x.mastery])) : {};
  const rec = progress?.recommendation?.topic_key;
  const rules = (params.get("rules") || "").split(",").filter(Boolean);
  const chosen = new Set(params.get("topic") ? [params.get("topic")] : rules.length ? [] : rec ? [rec] : []);
  const levels = student ? [...LEVELS, "adaptive"] : LEVELS;
  let level = levels.includes(params.get("level")) ? params.get("level") : "medium";
  let count = Math.min(20, Math.max(1, Number(params.get("count")) || (student ? 10 : 5)));
  const ruleNames = rules.length ? topics.flatMap((x) => x.rules).filter((r) => rules.includes(r.id)).map((r) => r.name) : [];
  el.innerHTML = `<div class="gen-panel">
    ${ruleNames.length ? `<div class="callout coral" id="rules-note">${icon("notebook")}<div><b>${t("from_mistakes")}</b><br>${esc(ruleNames.join(", "))}
      <button class="link-btn" id="clear-rules">${t("clear")}</button></div></div>` : ""}
    <div id="topic-step" class="${ruleNames.length ? "hidden" : ""}"><div class="step-h"><b>1</b>${t("step_topic")}</div>
      <div class="topic-grid" id="tg">
        <button class="topic-btn" data-t=""><span class="t">${t("all_topics")}</span><span class="s">13 ${t("trap_of")}</span></button>
        ${topics.map((x) => `<button class="topic-btn ${x.key === rec ? "rec" : ""}" data-rec="${t("recommended")}" data-t="${esc(x.key)}"><span class="t">${esc(x.name)}</span>
          ${progress ? `<span class="mini"><i style="width:${Math.round((mastery[x.key] ?? 0) * 100)}%;background:${masteryColor(mastery[x.key])}"></i></span><span class="s">${mastery[x.key] == null ? t("not_seen") : pct(mastery[x.key]) + " " + t("mastery")}</span>`
          : `<span class="s">${x.rules.length} ${t("trap_of")}</span>`}</button>`).join("")}
      </div></div>
    <div><div class="step-h"><b>2</b>${t("step_level")}</div>
      <div class="level-pick ${student ? "four" : ""}" id="lp">${levels.map((lv) => `<button data-lv="${lv}" class="${lv === "adaptive" ? "ad" : ""}"><b>${lv === "adaptive" ? icon("trend") : lvlBars(lv)} ${t("lv_" + lv)}</b><small>${t("lv_" + lv + "_d")}</small></button>`).join("")}</div></div>
    <div><div class="step-h"><b>3</b>${t("step_count")}</div>
      <div class="range-row"><input type="range" min="1" max="20" value="${count}" id="cnt"><span class="val" id="cntv">${count}</span></div>
      <div class="presets">${[5, 10, 15, 20].map((n) => `<button class="chip chip-btn" data-n="${n}">${n} ${t("questions")}</button>`).join("")}</div></div>
    <div><div class="step-h"><b>4</b>${t("step_prompt")}</div>
      <textarea class="input" id="prompt" rows="2" style="min-height:64px" placeholder="${esc(t("prompt_ph"))}"></textarea>
      <div class="presets" style="margin-top:8px">${["pr_ex1", "pr_ex2", "pr_ex3"].map((k) => `<button class="chip chip-btn" data-pr="${k}">${t(k)}</button>`).join("")}</div>
      <div class="hint" style="margin-top:6px">${t("prompt_hint")}</div>
      <div class="toggles"><label class="switch"><input type="checkbox" id="story"><span class="tg"></span>${t("story_toggle")}</label>
        ${student ? `<label class="switch"><input type="checkbox" id="instant"><span class="tg"></span>${t("instant_toggle")}</label>` : ""}</div></div>
    <button class="btn btn-primary btn-lg" id="gen">${icon(student ? "target" : "wand")}${student ? t("start_test") : t("gen_btn")}</button>
  </div>`;
  const sync = () => {
    $$("#tg .topic-btn", el).forEach((b) => b.classList.toggle("on", b.dataset.t ? chosen.has(b.dataset.t) : chosen.size === 0));
    $$("#lp button", el).forEach((b) => b.classList.toggle("on", b.dataset.lv === level));
    $("#cntv", el).textContent = count; $("#cnt", el).value = count;
  };
  $$("#tg .topic-btn", el).forEach((b) => b.addEventListener("click", () => {
    if (!b.dataset.t) chosen.clear(); else chosen.has(b.dataset.t) ? chosen.delete(b.dataset.t) : chosen.add(b.dataset.t);
    sync();
  }));
  $$("#lp button", el).forEach((b) => b.addEventListener("click", () => { level = b.dataset.lv; sync(); }));
  $("#cnt", el).addEventListener("input", (e) => { count = Number(e.target.value); sync(); });
  $$("[data-n]", el).forEach((b) => b.addEventListener("click", () => { count = Number(b.dataset.n); sync(); }));
  $$("[data-pr]", el).forEach((b) => b.addEventListener("click", () => { $("#prompt", el).value = t(b.dataset.pr); }));
  $("#clear-rules", el)?.addEventListener("click", () => { rules.length = 0; $("#rules-note", el).remove(); $("#topic-step", el).classList.remove("hidden"); });
  sync();
  $("#gen", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    const settings = { topics: [...chosen], rules: [...rules], level, count, prompt: $("#prompt", el).value, story: $("#story", el).checked,
      instant: student && $("#instant", el).checked, adaptive: level === "adaptive" };
    busy(btn, true, t("generating"));
    try {
      const r = await api("/api/generate", { method: "POST", body: { ...settings, level: settings.adaptive ? "medium" : level, count: settings.adaptive ? 1 : count } });
      busy(btn, false);
      onResult(r, settings);
    } catch (err) { toast(errText(err), true); busy(btn, false); }
  });
}

// ---------- the page ----------
export async function practice(el, params, ctx) {
  if (params.get("assignment")) {
    el.innerHTML = `<div class="card"><div class="skeleton" style="height:220px"></div></div>`;
    const r = await api("/api/generate", { method: "POST", body: { assignment_id: Number(params.get("assignment")) } });
    return runTest(el, r, { level: r.level, count: r.made, assignment: true, title: r.title }, ctx);
  }
  const progress = await api("/api/progress").catch(() => null);
  const tests = await api("/api/tests").catch(() => []);
  el.innerHTML = `<div class="grid g-main" style="align-items:start">
    <div class="card"><div class="card-h"><div><h2>${t("prac_t")}</h2><p>${t("prac_p")}</p></div></div><div id="form"></div></div>
    <div class="grid" style="position:sticky;top:96px">
      <div class="card side-how"><h3>${icon("shield")} ${t("how_test_t")}</h3>
        <ul><li>${icon("check")}${t("how_test_1")}</li><li>${icon("check")}${t("how_test_2")}</li><li>${icon("check")}${t("how_test_3")}</li><li>${icon("check")}${t("how_test_4")}</li></ul></div>
      <div class="card"><h3 style="margin-bottom:10px">${t("past_tests")}</h3>
        ${tests.length ? `<div class="list">${tests.slice(0, 5).map(testRow).join("")}</div>` : `<p class="muted" style="font-size:14px">${t("past_tests_empty")}</p>`}</div>
    </div></div>`;
  await generatorForm($("#form", el), { params, progress, student: true, onResult: (r, settings) => runTest(el, r, settings, ctx) });
}

export const testRow = (x) => {
  const score = x.total ? x.correct / x.total : 0;
  return `<div class="li"><span class="score-pill" style="background:${masteryColor(score)}">${Math.round(score * 100)}</span>
    <div><div class="t">${x.correct}/${x.total} ${t("correct").toLowerCase()} · ${x.adaptive ? t("lv_adaptive") : t("lv_" + (x.level || "medium"))}</div>
    <div class="s">${fmtDate(x.created)} · ${fmtTime(x.seconds || 0)}${x.weak?.length ? ` · ${esc(x.weak[0])}` : ""}</div></div></div>`;
};

// ---------- taking the test ----------
function runTest(el, gen, settings, ctx) {
  const total = settings.adaptive ? settings.count : gen.questions.length;
  const items = gen.questions.map((q) => ({ q, state: null }));  // state: {picked, correct, answer_index, rule, mode, html, secs}
  const rules = settings.rules?.length ? settings.rules : gen.rules || [];
  let i = 0, picked = null, mode = "choice", loadingNext = false;
  const t0 = Date.now();
  let qStart = Date.now();
  const timer = setInterval(() => { const tm = $("#tm", el); if (!tm) return clearInterval(timer); tm.textContent = fmtTime((Date.now() - t0) / 1000); }, 1000);
  const answered = () => items.filter((x) => x.state && x.state.picked !== -1).length;

  const head = () => `<div class="test-head card">
      <div class="th-l"><span class="chip navy">${settings.assignment ? icon("clipboard") + esc(t("m_assignments")) : settings.adaptive ? icon("trend") + t("lv_adaptive") : lvlBars(settings.level) + " " + t("lv_" + settings.level)}</span>
        ${gen.understood ? `<span class="chip blue" title="${gen.by_model ? esc(t("by_model_req")) : esc(t("by_kw_req"))}">${icon("wand")}${esc(gen.understood)}</span>` : ""}
        ${gen.made < gen.requested && !settings.adaptive ? `<span class="chip amber">${t("made_less", { m: gen.made, r: gen.requested })}</span>` : ""}</div>
      <div class="th-r"><span class="timer">${icon("calendar")}<b id="tm">${fmtTime((Date.now() - t0) / 1000)}</b></span>
        <button class="btn btn-ghost btn-sm" id="finish">${t("finish_test")}</button></div></div>`;

  const draw = () => {
    const item = items[i], q = item.q, st = item.state;
    const done = st && st.picked !== -1;
    const adaptiveChip = settings.adaptive && i > 0 ? (() => {
      const prev = items[i - 1].q.level, up = LEVELS.indexOf(q.level) - LEVELS.indexOf(prev);
      return up ? `<span class="chip ${up > 0 ? "coral" : "green"}">${up > 0 ? "↑ " + t("ad_up") : "↓ " + t("ad_down")}</span>` : `<span class="chip">${t("ad_same")}</span>`;
    })() : "";
    el.innerHTML = `${head()}<div class="card">
      <div class="quiz-top"><b style="white-space:nowrap">${t("q_of", { i: i + 1, n: total })}</b><div class="prog"><i style="width:${(answered() / total) * 100}%"></i></div></div>
      ${settings.adaptive ? "" : `<div class="dots" style="margin-bottom:18px">${items.map((x, k) => `<i class="${k === i ? "cur" : ""} ${x.state ? (x.state.picked === -1 ? "b" : settings.instant ? (x.state.correct ? "r" : "w") : "a") : ""}" data-k="${k}">${k + 1}</i>`).join("")}</div>`}
      <div class="qcard">
        <div class="meta"><span class="chip">${esc(q.topic)}</span><span class="chip">${lvlBars(q.level)} ${t("lv_" + q.level)}</span>${adaptiveChip}<span class="chip green">${icon("shield")}${t("verified")}</span></div>
        <div class="ins">${esc(q.instruction)}</div>
        ${q.story ? `<div class="story">${icon("book")} ${esc(q.story)}</div>` : ""}
        <div class="prob">${esc(q.problem_display)}</div>
        ${q.is_equation && !done ? `<div class="seg" style="margin-bottom:16px"><button data-m="choice" class="${mode === "choice" ? "on" : ""}">${t("mode_choice")}</button><button data-m="steps" class="${mode === "steps" ? "on" : ""}">${t("mode_steps")}</button></div>` : ""}
        <div id="body"></div>
      </div></div>`;
    $$(".dots i", el).forEach((d) => d.addEventListener("click", () => { i = Number(d.dataset.k); picked = null; mode = "choice"; qStart = Date.now(); draw(); }));
    $$("[data-m]", el).forEach((b) => b.addEventListener("click", () => { mode = b.dataset.m; draw(); }));
    $("#finish", el).addEventListener("click", () => {
      const left = total - answered();
      if (left > 0 && !confirm(t("finish_confirm", { n: left }))) return;
      finish();
    });
    const body = $("#body", el);
    if (done) {
      body.innerHTML = `${choicesHTML(q, st)}${settings.instant || st.mode === "steps" ? st.html : `<div class="callout navy-l">${icon("lock")}<span>${t("saved_answer")}</span></div>`}
        <div class="qfoot">${nextBtn()}</div>`;
      wireNext();
      return;
    }
    if (mode === "steps" && q.is_equation) {
      body.innerHTML = `<textarea class="input mono" id="st" rows="5" placeholder="${esc(t("steps_ph"))}"></textarea>
        <div class="qfoot"><button class="btn btn-ghost" id="skip">${t("skip_btn")}</button><button class="btn btn-primary" id="chk">${icon("steps")}${t("steps_btn")}</button></div>`;
      $("#skip", el).addEventListener("click", skip);
      $("#chk", el).addEventListener("click", async (e) => {
        const lines = $("#st", el).value.split("\n").filter((l) => l.trim());
        if (!lines.length) return;
        const btn = e.currentTarget;
        busy(btn, true, t("checking"));
        try {
          const r = await api("/api/solve-steps", { method: "POST", body: { question_id: q.id, lines } });
          const tail = r.solved || r.first_error != null ? "" : `<div class="callout amber">${icon("info")}<span>${t("correct_answer")}: <b class="mono">${esc(r.answer)}</b></span></div>`;
          item.state = { picked: -2, correct: r.solved, answer_index: r.answer_index, answer: r.answer, rule: r.rule, mode: "steps", lines,
            html: `<div class="fb-steps">${stepsHTML(r)}${counterHTML(r)}${tail}</div>`, secs: (Date.now() - qStart) / 1000 };
          afterAnswer();
        } catch (err) { toast(errText(err), true); busy(btn, false); }
      });
      return;
    }
    body.innerHTML = `${choicesHTML(q, null)}<div class="qfoot"><button class="btn btn-ghost" id="skip">${t("skip_btn")}</button>
      <button class="btn btn-primary" id="ans" ${picked == null ? "disabled" : ""}>${settings.instant ? t("answer_btn") : t("answer_next_btn")}</button></div>`;
    $$(".choice", el).forEach((b) => b.addEventListener("click", () => {
      picked = Number(b.dataset.c);
      $$(".choice", el).forEach((c) => c.classList.toggle("sel", Number(c.dataset.c) === picked));
      $("#ans", el).disabled = false;
    }));
    $("#skip", el).addEventListener("click", skip);
    $("#ans", el).addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      busy(btn, true);
      try {
        const r = await api("/api/answer", { method: "POST", body: { question_id: q.id, choice: picked } });
        item.state = { ...r, picked, mode: "choice", html: feedbackHTML(r), secs: (Date.now() - qStart) / 1000 };
        picked = null;
        afterAnswer();
      } catch (err) { toast(errText(err), true); busy(btn, false); }
    });
  };

  const choicesHTML = (q, st) => `<div class="choices">${q.choices.map((c, k) => {
    let cls = "";
    if (st && st.mode !== "steps") cls = settings.instant ? (k === st.answer_index ? "right" : k === st.picked ? "wrong" : "") : k === st.picked ? "sel" : "";
    return `<button class="choice ${cls}" data-c="${k}" ${st ? "disabled" : ""}><span class="L">${"ABCD"[k]}</span>${esc(c)}</button>`;
  }).join("")}</div>`;
  const nextBtn = () => `<button class="btn btn-dark" id="next">${isLast() ? t("finish_btn") : t("next_btn")} ${icon("arrow")}</button>`;
  const isLast = () => (settings.adaptive ? items.length >= total : items.every((x) => x.state));
  const wireNext = () => $("#next", el)?.addEventListener("click", goNext);

  function skip() {  // left blank; a blank question can still be answered later from its dot
    items[i].state = { picked: -1, correct: null, secs: (Date.now() - qStart) / 1000 };
    goNext();
  }

  function afterAnswer() {
    if (settings.instant || items[i].state.mode === "steps") return draw();
    goNext();
  }

  async function goNext() {
    picked = null; mode = "choice"; qStart = Date.now();
    if (settings.adaptive) {
      if (items.length >= total) return finish();
      if (loadingNext) return;
      loadingNext = true;
      const last = items[items.length - 1];
      const idx = LEVELS.indexOf(last.q.level);
      const lv = last.state?.correct ? LEVELS[Math.min(2, idx + 1)] : last.state?.correct === false ? LEVELS[Math.max(0, idx - 1)] : last.q.level;
      el.querySelector("#body")?.insertAdjacentHTML("beforeend", `<div class="callout navy-l" style="margin-top:12px"><span class="spin dark"></span><span>${t("ad_loading")}</span></div>`);
      try {
        const r = await api("/api/generate", { method: "POST", body: { topics: settings.topics, rules, level: lv, count: 1, story: settings.story } });
        items.push({ q: r.questions[0], state: null });
        i = items.length - 1;
      } catch (err) { toast(errText(err), true); }
      loadingNext = false;
      return draw();
    }
    const open = items.findIndex((x, k) => k > i && !x.state);
    const anyOpen = open >= 0 ? open : items.findIndex((x) => !x.state);  // blanks are revisited only from their dots
    if (anyOpen < 0) return finish();
    i = anyOpen; draw();
  }

  function finish() {
    clearInterval(timer);
    evaluation(el, items, settings, (Date.now() - t0) / 1000, total, ctx);
  }
  draw();
}

function feedbackHTML(r) {
  if (r.correct) return `<div class="callout green">${icon("checkc")}<div><b>${t("right_t")}</b> ${t("right_p")}</div></div>`;
  return `<div class="callout coral">${icon("x")}<div><b>${t("wrong_t")}</b> ${t("correct_answer")}: <span class="mono" style="font-weight:700">${esc(r.answer)}</span>
    ${r.rule ? `<br>${t("reveals")} <b>${esc(r.rule.name)}</b>. ${t("see_in_eval")}` : `<br>${t("slip")}`}</div></div>`;
}

// ---------- evaluation ----------
function evaluation(el, items, settings, seconds, total, ctx) {
  const list = items.map((x) => ({ ...x, state: x.state || { picked: -1, correct: null } }));
  while (!settings.adaptive && list.length < total) list.push({ q: null, state: { picked: -1, correct: null } });
  const right = list.filter((x) => x.state.correct === true).length;
  const wrong = list.filter((x) => x.state.correct === false).length;
  const blank = total - right - wrong;
  const net = Math.max(0, right - wrong / 3);
  const score = total ? right / total : 0;
  const qs = list.filter((x) => x.q);

  // per topic and per revealed misconception
  const byTopic = {};
  qs.forEach((x) => { const k = x.q.topic; byTopic[k] = byTopic[k] || { n: 0, r: 0, key: x.q.topic_key }; byTopic[k].n++; if (x.state.correct) byTopic[k].r++; });
  const mis = {};
  let slips = 0;
  qs.forEach((x) => {
    if (x.state.correct !== false) return;
    if (x.state.rule) { const k = x.state.rule.id; mis[k] = mis[k] || { rule: x.state.rule, n: 0 }; mis[k].n++; } else slips++;
  });
  const misList = Object.values(mis).sort((a, b) => b.n - a.n);
  const strong = Object.entries(byTopic).filter(([, v]) => v.r / v.n >= 0.75).map(([k, v]) => ({ k, ...v }));
  const weakTopics = Object.entries(byTopic).filter(([, v]) => v.r / v.n < 0.5).map(([k, v]) => ({ k, ...v }));
  const byLevel = {};
  qs.forEach((x) => { const k = x.q.level; byLevel[k] = byLevel[k] || { n: 0, r: 0 }; byLevel[k].n++; if (x.state.correct) byLevel[k].r++; });
  const verdict = score >= 0.85 ? "ev_great" : score >= 0.6 ? "ev_good" : score >= 0.35 ? "ev_mid" : "ev_low";

  if (ctx?.state.user.role === "student") {
    api("/api/tests", { method: "POST", body: { data: { total, correct: right, wrong, blank, seconds: Math.round(seconds),
      level: settings.adaptive ? "adaptive" : settings.level, adaptive: settings.adaptive, topics: Object.keys(byTopic),
      weak: misList.map((m) => m.rule.name) } } }).catch(() => {});
  }
  const topicKey = (name) => byTopic[name]?.key;

  el.innerHTML = `<div class="grid">
    <div class="card eval-hero">
      <div class="eval-pie">${pie([{ value: right, color: "#1E9E5A", label: t("correct") }, { value: wrong, color: "#FF5A5F", label: t("wrong") }, { value: blank, color: "#CBD3E1", label: t("blank") }], 190, pct(score), t("success"))}
        <div class="legend col"><span><i style="background:#1E9E5A"></i>${t("correct")} <b>${right}</b></span><span><i style="background:#FF5A5F"></i>${t("wrong")} <b>${wrong}</b></span><span><i style="background:#CBD3E1"></i>${t("blank")} <b>${blank}</b></span></div></div>
      <div class="eval-sum"><span class="chip ${score >= 0.6 ? "green" : "amber"}">${icon("spark")}${t("ev_k")}</span>
        <h2>${t(verdict)}</h2><p class="muted">${t("ev_sub", { r: right, n: total })}</p>
        <div class="grid g4 ev-kpis">
          <div class="kpi"><span class="l">${t("net")}</span><span class="v">${net.toFixed(2).replace(/\.?0+$/, "")}</span><span class="d">${t("net_d")}</span></div>
          <div class="kpi"><span class="l">${t("time")}</span><span class="v">${fmtTime(seconds)}</span><span class="d">${t("per_q", { s: Math.round(seconds / Math.max(1, total)) })}</span></div>
          <div class="kpi"><span class="l">${t("level")}</span><span class="v" style="font-size:20px">${settings.adaptive ? t("lv_adaptive") : t("lv_" + settings.level)}</span><span class="d">${settings.adaptive ? t("ad_reached", { l: t("lv_" + (qs[qs.length - 1]?.q.level || "medium")) }) : `${total} ${t("questions")}`}</span></div>
          <div class="kpi"><span class="l">${t("misconceptions")}</span><span class="v">${misList.length}</span><span class="d">${slips ? t("slips_n", { n: slips }) : t("no_slips")}</span></div>
        </div>
        <div class="ev-actions">
          ${misList.length ? `<a class="btn btn-primary" href="#/app/practice?rules=${encodeURIComponent(misList.map((m) => m.rule.id).join(","))}&count=${Math.min(20, Math.max(5, misList.length * 3))}">${icon("target")}${t("ev_retry_weak")}</a>` : ""}
          <a class="btn ${misList.length ? "btn-ghost" : "btn-primary"}" href="#/app/practice?r=${Date.now()}">${icon("refresh")}${t("new_set")}</a>
          <a class="btn btn-ghost" href="#/app/dashboard">${t("m_dashboard")}</a></div>
      </div></div>
    <div class="grid g2" style="align-items:start">
      <div class="card"><div class="card-h"><div><h2>${icon("trend")} ${t("ev_strong")}</h2><p>${t("ev_strong_p")}</p></div></div>
        ${strong.length ? `<div class="list">${strong.map((s) => `<div class="li"><span class="ic green sq">${icon("checkc")}</span><div><div class="t">${esc(s.k)}</div><div class="s">${s.r}/${s.n} ${t("correct").toLowerCase()}</div></div></div>`).join("")}
          ${Object.entries(byLevel).filter(([, v]) => v.r === v.n && v.n > 1).map(([lv, v]) => `<div class="li"><span class="ic green sq">${lvlBars(lv)}</span><div><div class="t">${t("lv_" + lv)} ${t("questions")}</div><div class="s">${v.r}/${v.n}</div></div></div>`).join("")}</div>`
          : `<p class="muted">${t("ev_strong_none")}</p>`}</div>
      <div class="card"><div class="card-h"><div><h2>${icon("alert")} ${t("ev_weak")}</h2><p>${t("ev_weak_p")}</p></div></div>
        ${misList.length || weakTopics.length || slips ? `<div class="list">${misList.map((m) => `<div class="li" style="align-items:flex-start"><span class="ic coral sq">${m.n}×</span>
            <div style="flex:1;min-width:0"><div class="t">${esc(m.rule.name)}</div><div class="s">${esc(m.rule.misconception)}</div><div class="s" style="margin-top:4px"><b>${t("correct_rule")}:</b> ${esc(m.rule.correct_rule)}</div></div>
            <div class="end col"><a class="btn btn-primary btn-sm" href="#/app/practice?rules=${encodeURIComponent(m.rule.id)}&count=5">${t("practice_this")}</a></div></div>`).join("")}
          ${weakTopics.map((w) => `<div class="li"><span class="ic amber sq">${icon("book")}</span><div style="flex:1"><div class="t">${esc(w.k)}</div><div class="s">${w.r}/${w.n} ${t("correct").toLowerCase()}</div></div>
            ${topicKey(w.k) ? `<div class="end"><a class="btn btn-ghost btn-sm" href="#/app/study?topic=${encodeURIComponent(topicKey(w.k))}">${t("study_this")}</a></div>` : ""}</div>`).join("")}
          ${slips ? `<div class="li"><span class="ic sq">${icon("info")}</span><div><div class="t">${t("slips_t")}</div><div class="s">${t("slips_p", { n: slips })}</div></div></div>` : ""}</div>`
          : `<div class="okbox">${icon("checkc")}<div><b>${t("ev_weak_none")}</b></div></div>`}</div>
    </div>
    <div class="grid ${settings.adaptive ? "g2" : ""}" style="align-items:start">
      <div class="card"><div class="card-h"><div><h2>${t("ev_topics")}</h2></div></div>
        <div class="bars-list">${Object.entries(byTopic).map(([k, v]) => `<div class="bar-row"><span class="name">${esc(k)}</span><span class="pct">${v.r}/${v.n}</span>
          <div class="track"><div class="fill" style="width:${(v.r / v.n) * 100}%;background:${masteryColor(v.r / v.n)}"></div></div></div>`).join("")}</div></div>
      ${settings.adaptive ? `<div class="card"><div class="card-h"><div><h2>${t("ad_path_t")}</h2><p>${t("ad_path_p")}</p></div></div>${levelPath(qs.map((x) => ({ level: x.q.level, correct: x.state.correct })))}</div>` : ""}
    </div>
    <div class="card"><div class="card-h"><div><h2>${t("ev_review")}</h2><p>${t("ev_review_p")}</p></div></div>
      <div class="review">${qs.map((x, k) => {
        const s = x.state, status = s.correct === true ? "r" : s.correct === false ? "w" : "b";
        return `<div class="rv ${status}"><div class="rv-h"><span class="rv-n">${k + 1}</span><div class="rv-p"><div class="s">${esc(x.q.instruction)} · ${t("lv_" + x.q.level)}</div><div class="mono">${esc(x.q.problem_display)}</div></div>
          <span class="chip ${status === "r" ? "green" : status === "w" ? "coral" : ""}">${status === "r" ? t("correct") : status === "w" ? t("wrong") : t("blank")}</span></div>
          <div class="rv-a">${s.mode === "steps" ? `<span class="chip">${t("mode_steps")}</span>` : s.picked >= 0 ? `<span class="chip ${s.correct ? "green" : "coral"}">${t("you_picked")}: ${esc(x.q.choices[s.picked])}</span>` : ""}
            ${s.correct !== true && s.answer_index != null ? `<span class="chip green">${t("correct_answer")}: ${esc(x.q.choices[s.answer_index])}</span>` : ""}
            ${s.rule ? `<span class="chip navy">${esc(s.rule.name)}</span>` : ""}
            ${s.correct === false && s.mode !== "steps" ? `<button class="btn btn-ghost btn-sm" data-why="${k}">${icon("spark")}${t("why_btn")}</button>` : ""}
            ${s.correct === null ? `<span class="muted" style="font-size:13px">${t("blank_note")}</span>` : ""}</div>
          ${s.mode === "steps" && s.correct === false ? `<details class="rv-d"><summary>${t("see_steps")}</summary>${s.html}</details>` : ""}
          <div class="rv-x" id="rvx${k}"></div></div>`;
      }).join("")}</div></div>
  </div>`;
  $$("[data-why]", el).forEach((b) => b.addEventListener("click", async () => {
    const x = qs[Number(b.dataset.why)], slot = $(`#rvx${b.dataset.why}`, el);
    busy(b, true, t("explaining_s"));
    slot.innerHTML = `<div class="explain loading"><div class="typing"><i></i><i></i><i></i></div><span class="muted" style="font-size:13px">${t("explaining")}</span></div>`;
    try {
      const r = await api("/api/explain-answer", { method: "POST", body: { question_id: x.q.id, choice: x.state.picked } });
      slot.innerHTML = `<div class="rv-exp"><div class="rule-mini"><b>${esc(r.rule.name)}</b> · ${esc(r.rule.misconception)}</div>${counterHTML(r)}${explanationHTML(r)}</div>`;
      b.remove();
    } catch (err) { slot.innerHTML = `<div class="callout coral">${icon("alert")}<span>${esc(errText(err))}</span></div>`; busy(b, false); }
  }));
}
