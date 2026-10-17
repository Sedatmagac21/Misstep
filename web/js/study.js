// "Ders çalış": a lesson per topic plus a chat assistant that answers from the notes and uploaded files.
import { t } from "./i18n.js";
import { noteHTML } from "./analysis.js";
import { download } from "./analysis.js";
import { $, $$, api, busy, errText, esc, icon, masteryColor, md, modal, pct, toast } from "./ui.js";

const store = {
  get(k) { try { return JSON.parse(sessionStorage.getItem(k) || "[]"); } catch { return []; } },
  set(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v.slice(-30))); } catch { /* private mode */ } },
};

export async function study(el, params) {
  const [topics, progress] = await Promise.all([api("/api/topics"), api("/api/progress").catch(() => null)]);
  const mastery = progress ? Object.fromEntries(progress.topics.map((x) => [x.key, x.mastery])) : {};
  const key = params.get("topic") || progress?.recommendation?.topic_key || topics[0].key;
  let tab = params.get("chat") ? "chat" : params.get("research") ? "research" : "lesson";
  el.innerHTML = `<div class="study-grid">
    <div class="card study-nav"><h2 style="margin-bottom:12px">${t("study_t")}</h2>
      <div class="list">${topics.map((x) => `<a class="li ${x.key === key ? "on" : ""}" href="#/app/study?topic=${encodeURIComponent(x.key)}${tab === "chat" ? "&chat=1" : ""}">
        <span class="dot" style="background:${masteryColor(mastery[x.key])}"></span><div><div class="t" style="font-size:14px">${esc(x.name)}</div>
        <div class="s">${mastery[x.key] == null ? t("not_seen") : pct(mastery[x.key]) + " " + t("mastery")}</div></div></a>`).join("")}</div></div>
    <div><div class="seg study-tabs" id="stabs"><button data-tab="lesson">${icon("book")} ${t("tab_lesson")}</button><button data-tab="chat">${icon("spark")} ${t("tab_chat")}</button><button data-tab="research">${icon("search")} ${t("tab_research")}</button></div>
      <div id="pane" style="margin-top:14px"><div class="skeleton" style="height:300px"></div></div></div></div>`;
  const s = await api(`/api/study/${encodeURIComponent(key)}`);
  const show = () => {
    $$("#stabs button", el).forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
    if (tab === "lesson") lesson($("#pane", el), s, key);
    else if (tab === "chat") chat($("#pane", el), s, key);
    else researchPane($("#pane", el), s, key);
  };
  $$("#stabs button", el).forEach((b) => b.addEventListener("click", () => { tab = b.dataset.tab; show(); }));
  show();
}

function lesson(pane, s, key) {
  pane.innerHTML = `<div class="lesson">
    <div class="welcome" style="padding:24px 26px"><div><h2 style="font-size:24px">${esc(s.name)}</h2><p>${t("study_p")}</p></div>
      <div class="actions"><a class="btn btn-primary" href="#/app/practice?topic=${encodeURIComponent(key)}&level=easy&count=5">${icon("target")}${t("try_now")}</a>
      <button class="btn btn-light" id="to-chat">${icon("spark")}${t("ask_assistant")}</button>
      <button class="btn btn-light" id="rep">${icon("download")}${t("topic_report")}</button></div></div>
    ${s.rules.map((r) => `<div class="rule-card">
      <h3>${icon("target")} ${esc(r.name)} ${r.mastery != null && r.seen ? `<span class="chip" style="margin-left:auto">${t("your_mastery")}: ${pct(r.mastery)}</span>` : ""}</h3>
      <p class="muted" style="margin-top:6px">${esc(r.misconception)}</p>
      <div class="compare"><div class="w"><b>✗ ${t("wrong_way")}</b><span class="mono">${esc(r.example)}</span></div><div class="r"><b>✓ ${t("right_way")}</b>${esc(r.correct_rule)}</div></div>
      ${r.note ? `<details style="margin-top:14px"><summary style="cursor:pointer;font-weight:700;color:var(--coral-d)">${t("note_t")}: ${esc(r.note.title)}</summary>${noteHTML(r.note.text)}</details>` : ""}
    </div>`).join("")}</div>`;
  $("#to-chat", pane).addEventListener("click", () => $('#stabs [data-tab="chat"]').click());
  $("#rep", pane).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true, t("rep_busy"));
    try { const r = await api(`/api/study/${encodeURIComponent(key)}/report.pdf`, { raw: true }); download(await r.blob(), `misstep-${t("topic_report_file")}.pdf`); }
    catch (err) { toast(errText(err), true); }
    busy(btn, false);
  });
}

const srcChips = (sources, k) => (sources?.length ? `<div class="src">${sources.map((c, j) => `<button class="chip chip-btn ${c.source === "note" ? "blue" : "amber"}" data-src="${k}:${j}">K${j + 1} · ${esc(c.title)}${c.source !== "note" ? ` · ${t(c.source === "mine" ? "src_mine" : "src_shared")}` : ""}</button>`).join("")}</div>` : "");
const showSource = (c) => modal(`<div style="display:flex;align-items:center;gap:10px"><h3>${esc(c.title)}</h3><button class="btn btn-ghost btn-sm" data-close style="margin-left:auto">${t("close")}</button></div>
  <div style="margin-top:12px;max-height:60vh;overflow:auto">${noteHTML(c.text)}</div>`);

// "Derin araştırma": plan -> one retrieval + answer per sub-question -> summary, each a real request so progress is honest
function researchPane(pane, s, key) {
  const sk = `ms_research_${key}`;
  let last = null;
  try { last = JSON.parse(sessionStorage.getItem(sk) || "null"); } catch { /* private mode */ }
  pane.innerHTML = `<div class="card research">
    <div class="chat-h" style="padding:0 0 14px"><span class="bot">${icon("search")}</span><div><b>${t("rs_t")}</b><div class="muted" style="font-size:13px">${t("rs_p")}</div></div></div>
    <form id="rf" class="rs-in"><textarea class="input" id="rq" rows="2" placeholder="${esc(t("rs_ph"))}"></textarea>
      <button class="btn btn-primary" id="rgo">${icon("search")}${t("rs_go")}</button></form>
    <div class="chat-sugg" style="padding:10px 0 0">${["rq1", "rq2", "rq3"].map((k) => `<button class="chip chip-btn" data-q="${k}">${t(k, { t: s.name })}</button>`).join("")}</div>
    <div id="rprog"></div></div><div id="rout" style="margin-top:16px"></div>`;
  const input = $("#rq", pane);
  $$("[data-q]", pane).forEach((b) => b.addEventListener("click", () => { input.value = b.textContent; $("#rf", pane).requestSubmit(); }));
  if (last) result(last);
  $("#rf", pane).addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    const go = $("#rgo", pane);
    busy(go, true, t("rs_busy"));
    $("#rout", pane).innerHTML = "";
    const prog = $("#rprog", pane);
    const stages = [{ label: t("rs_plan"), st: "run" }];
    const draw = () => { prog.innerHTML = `<ol class="rs-prog">${stages.map((x) => `<li class="${x.st}"><span class="nd">${x.st === "done" ? icon("check") : x.st === "run" ? '<span class="spin dark"></span>' : ""}</span><span>${esc(x.label)}</span></li>`).join("")}</ol>`; };
    draw();
    try {
      const plan = await api("/api/research/plan", { method: "POST", body: { question, topic: key } });
      stages[0].st = "done";
      plan.steps.forEach((q) => stages.push({ label: q, st: "wait" }));
      stages.push({ label: t("rs_sum"), st: "wait" });
      const steps = [];
      for (let i = 0; i < plan.steps.length; i++) {
        stages[i + 1].st = "run"; draw();
        steps.push(await api("/api/research/step", { method: "POST", body: { question, topic: key, sub: plan.steps[i], steps: steps.map(({ answer }) => ({ answer })) } }));
        stages[i + 1].st = "done";
      }
      stages[stages.length - 1].st = "run"; draw();
      const sum = await api("/api/research/summary", { method: "POST", body: { question, topic: key, steps: steps.map(({ q, answer }) => ({ q, answer })) } });
      stages[stages.length - 1].st = "done"; draw();
      last = { question, steps, ...sum, by_model: plan.by_model || steps.some((x) => x.by_model) || sum.by_model };
      try { sessionStorage.setItem(sk, JSON.stringify(last)); } catch { /* private mode */ }
      result(last);
    } catch (err) { toast(errText(err), true); }
    busy(go, false);
  });

  function result(r) {
    const out = $("#rout", pane);
    out.innerHTML = `<div class="card">
      <div class="card-h"><div><span class="chip ${r.by_model ? "blue" : ""}">${r.by_model ? t("by_gemma") : t("rs_extractive")}</span><h2 style="margin-top:8px">${esc(r.question)}</h2></div>
        <button class="btn btn-dark btn-sm" id="rpdf">${icon("download")}${t("rs_pdf")}</button></div>
      <div class="rs-sum">${md(r.summary || "")}</div>
      <div class="rs-steps">${r.steps.map((x, k) => `<details ${k === 0 ? "open" : ""}><summary><b>${k + 1}</b>${esc(x.q)}</summary><div class="b">${md(x.answer || t("rs_none"))}${srcChips(x.sources, k)}</div></details>`).join("")}</div>
      ${r.rules?.length ? `<h3 style="margin:18px 0 8px">${t("rs_rules")}</h3><div class="grid g2">${r.rules.map((x) => `<div class="callout amber">${icon("alert")}<div><b>${esc(x.name)}</b><br>${esc(x.misconception)}<br><a href="#/app/practice?rules=${encodeURIComponent(x.id)}&level=medium&count=5" style="font-weight:700;color:var(--coral-d)">${t("hunt_practice")} →</a></div></div>`).join("")}</div>` : ""}
      ${r.questions?.length ? `<h3 style="margin:18px 0 8px">${t("rs_try")}</h3><div class="list">${r.questions.map((q, k) => `<div class="li" style="align-items:flex-start"><b style="width:24px">${k + 1}.</b><div style="flex:1"><div class="s">${esc(q.instruction)}</div><div class="t mono">${esc(q.problem_display)}</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px">${q.choices.map((c, j) => `<button class="chip chip-btn" data-a="${k}:${j}">${"ABCD"[j]}) ${esc(c)}</button>`).join("")}</div></div></div>`).join("")}</div>` : ""}
    </div>`;
    $$("[data-src]", out).forEach((b) => b.addEventListener("click", () => { const [k, j] = b.dataset.src.split(":").map(Number); showSource(r.steps[k].sources[j]); }));
    $$("[data-a]", out).forEach((b) => b.addEventListener("click", () => {
      const [k, j] = b.dataset.a.split(":").map(Number), q = r.questions[k];
      b.closest("div").querySelectorAll("[data-a]").forEach((x, i) => { x.disabled = true; if (i === q.answer_index) x.classList.add("green"); });
      if (j !== q.answer_index) b.classList.add("coral");
    }));
    $("#rpdf", out).addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      busy(btn, true);
      try {
        const resp = await api("/api/research/report.pdf", { method: "POST", raw: true, body: { question: r.question, summary: r.summary, steps: r.steps, rules: r.rules, questions: r.questions } });
        download(await resp.blob(), `misstep-${t("rs_file")}.pdf`);
      } catch (err) { toast(errText(err), true); }
      busy(btn, false);
    });
  }
}

// what to show when Gemma could not answer: the exact reason, the command that fixes it, and the source sentences
function offlineHTML(m) {
  const d = m.issue || {};
  const why = d.state === "offline" ? t("mi_offline") : d.state === "no_model" ? t("mi_no_model", { m: esc(d.model) }) : d.detail ? esc(d.detail) : t("mi_error");
  return `<div class="model-issue"><b>${icon("alert")} ${t("mi_t")}</b><p>${why}</p>
      ${d.fix ? `<p>${t("mi_fix")} <code>${esc(d.fix)}</code></p>` : ""}
      ${d.state === "no_model" && d.installed?.length ? `<p class="muted">${t("mi_installed")}: ${d.installed.map(esc).join(", ")}</p>` : ""}</div>
    ${m.content ? `<div class="mi-src-t">${t("mi_from_src")}</div>${md(m.content)}` : `<p>${t("chat_offline")}</p>`}`;
}

function chat(pane, s, key) {
  const sk = `ms_chat_${key}`;
  const msgs = store.get(sk);
  pane.innerHTML = `<div class="card chat">
    <div class="chat-h"><span class="bot">${icon("spark")}</span><div><b>${t("chat_t")}</b><div class="muted" style="font-size:13px">${t("chat_p", { t: esc(s.name) })}</div></div>
      <button class="btn btn-ghost btn-sm" id="clear" style="margin-left:auto">${icon("refresh")}${t("chat_clear")}</button></div>
    <div class="chat-log" id="log"></div>
    <div class="chat-sugg" id="sugg">${["cs1", "cs2", "cs3", "cs4"].map((k) => `<button class="chip chip-btn" data-s="${k}">${t(k)}</button>`).join("")}</div>
    <form class="chat-in" id="f"><textarea class="input" id="m" rows="1" placeholder="${esc(t("chat_ph"))}"></textarea>
      <button class="btn btn-primary" id="send" aria-label="${t("send")}">${icon("arrow")}</button></form>
    <div class="hint" style="padding:0 18px 14px">${icon("shield")} ${t("chat_note")}</div></div>`;
  const log = $("#log", pane);
  const bubble = (m, k) => m.role === "user"
    ? `<div class="msg me"><div class="b">${esc(m.content)}</div></div>`
    : `<div class="msg bot"><span class="av">${icon("spark")}</span><div class="b">${m.by_model ? md(m.content) : offlineHTML(m)}
        ${m.sources?.length ? `<div class="src">${m.sources.map((c, j) => `<button class="chip chip-btn ${c.source === "note" ? "blue" : "amber"}" data-src="${k}:${j}">K${j + 1} · ${esc(c.title)}${c.source !== "note" ? ` · ${t(c.source === "mine" ? "src_mine" : "src_shared")}` : ""}</button>`).join("")}</div>` : ""}</div></div>`;
  const render = (typing = false) => {
    log.innerHTML = (msgs.length ? "" : `<div class="chat-empty">${icon("spark")}<p>${t("chat_empty")}</p></div>`) + msgs.map(bubble).join("")
      + (typing ? `<div class="msg bot"><span class="av">${icon("spark")}</span><div class="b"><div class="typing"><i></i><i></i><i></i></div></div></div>` : "");
    log.scrollTop = log.scrollHeight;
    $$("[data-src]", log).forEach((b) => b.addEventListener("click", () => {
      const [k, j] = b.dataset.src.split(":").map(Number), c = msgs[k].sources[j];
      modal(`<div style="display:flex;align-items:center;gap:10px"><h3>${esc(c.title)}</h3><button class="btn btn-ghost btn-sm" data-close style="margin-left:auto">${t("close")}</button></div>
        <div style="margin-top:12px;max-height:60vh;overflow:auto">${noteHTML(c.text)}</div>`);
    }));
  };
  render();
  const input = $("#m", pane);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#f", pane).requestSubmit(); } });
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = `${Math.min(140, input.scrollHeight)}px`; });
  $$("[data-s]", pane).forEach((b) => b.addEventListener("click", () => { input.value = t(b.dataset.s); $("#f", pane).requestSubmit(); }));
  $("#clear", pane).addEventListener("click", () => { msgs.length = 0; store.set(sk, msgs); render(); });
  $("#f", pane).addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const history = msgs.filter((m) => m.role === "user" || m.by_model).map(({ role, content }) => ({ role, content }));
    msgs.push({ role: "user", content: text });
    input.value = ""; input.style.height = "auto";
    $("#send", pane).disabled = true;
    render(true);
    try {
      const r = await api("/api/chat", { method: "POST", body: { message: text, history, topic: key } });
      msgs.push({ role: "assistant", content: r.by_model ? r.answer : r.fallback || "", by_model: r.by_model, sources: r.sources, issue: r.model_issue });
    } catch {
      msgs.push({ role: "assistant", content: t("err_generic"), by_model: false, sources: [] });
    }
    store.set(sk, msgs);
    $("#send", pane).disabled = false;
    render();
  });
}
