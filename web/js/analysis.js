// "Soru çözümü analizi": a student's own solution, checked step by step.
import { t } from "./i18n.js";
import { $, $$, api, busy, errText, esc, fmtDate, icon, md, toast } from "./ui.js";

const STATUS = { given: "s_given", ok: "s_ok", error: "s_error", consistent: "s_consistent", unreadable: "s_unreadable" };
const EXAMPLES = {
  ex1: "3x - (x + 3) = 7\n3x - x + 3 = 7\n2x + 3 = 7\nx = 2",
  ex2: "x/2 + x/3 = 5\n2x/5 = 5\nx = 25/2",
  ex3: "2(x + 4) = 18\n2x + 8 = 18\n2x = 10\nx = 5",
};

export function noteHTML(text) {
  return `<div class="note-body">${String(text || "").split("\n").filter((l) => l.trim()).map((line) => {
    const m = line.match(/^(Neden yanlış|Sayıyla kontrol|İpucu|Why it is wrong|Check with numbers|Tip):\s*(.*)$/);
    return m ? `<p><span class="lbl">${esc(m[1])}:</span> ${md(m[2])}</p>` : `<p>${md(line.replace(/^#+\s*/, ""))}</p>`;
  }).join("")}</div>`;
}

export function sourceChips(sources) {
  return (sources || []).map((c, i) => `<span class="chip ${c.source === "note" ? "blue" : "amber"}">K${i + 1} · ${esc(c.title)}</span>`).join("");
}

export function explanationHTML(r) {
  if (!r.explanation) return "";
  return `<div class="explain"><div class="explain-h">${icon("spark")} ${t("explain_t")}</div>
    <div class="body">${r.explained_by_model ? md(r.explanation) : noteHTML(r.explanation)}</div>
    <div class="src">${r.explained_by_model ? `<span class="chip coral">${icon("spark")}${t("by_model")}</span>` : `<span class="chip">${icon("book")}${t("by_note")}</span>`}${sourceChips(r.sources)}</div></div>`;
}

// The checked lines as a vertical timeline; the first wrong step opens up to show what changed.
export function stepsHTML(r) {
  const prevOf = (i) => [...r.steps.slice(0, i)].reverse().find((s) => s.status !== "unreadable");
  return `<ol class="stepper">${r.steps.map((s, i) => {
    const isErr = i === r.first_error, prev = isErr ? prevOf(i) : null;
    return `<li class="st ${s.status}"><span class="node">${s.status === "ok" || s.status === "given" ? icon(s.status === "ok" ? "check" : "info") : s.status === "error" ? icon("x") : i + 1}</span>
      <div class="st-body"><div class="st-top"><span class="st-n">${t("step_n", { n: i + 1 })}</span><span class="chip ${{ ok: "green", error: "coral", consistent: "amber", given: "navy" }[s.status] || ""}">${t(STATUS[s.status])}</span></div>
        <div class="st-line mono">${esc(s.pretty)}</div>
        ${isErr && prev ? `<div class="st-diff"><div><span>${t("prev_line")}</span><b class="mono">${esc(prev.pretty)}</b></div>${icon("arrow")}<div class="bad"><span>${t("your_line")}</span><b class="mono">${esc(s.pretty)}</b></div></div>` : ""}
        ${s.status === "consistent" ? `<div class="st-note">${t("consistent_note")}</div>` : ""}
        ${s.status === "unreadable" && s.note ? `<div class="st-note">${esc(s.note)}</div>` : ""}</div></li>`;
  }).join("")}</ol>`;
}

export function verdictHTML(r) {
  const n = r.steps.length, okN = r.steps.filter((s) => s.status === "ok").length;
  const stats = `<div class="v-stats"><span><b>${n}</b> ${t("v_lines")}</span><span><b>${okN}</b> ${t("v_ok")}</span>${r.first_error != null ? `<span><b>${r.first_error + 1}.</b> ${t("v_first")}</span>` : ""}</div>`;
  if (r.first_error == null && r.final_correct !== false) {
    return `<div class="verdict good">${icon("checkc")}<div><h3>${t("all_ok_t")}</h3><p>${t("all_ok_p")}</p>${stats}</div></div>`;
  }
  if (r.first_error == null) {
    return `<div class="verdict warn">${icon("alert")}<div><h3>${t("wrong_final_t")}</h3><p>${t("wrong_final_p")}</p>${stats}</div></div>`;
  }
  return `<div class="verdict bad">${icon("alert")}<div><h3>${t("first_error", { n: r.first_error + 1 })}</h3><p>${r.diagnosis ? esc(r.diagnosis.rule.name) : t("no_pattern")}</p>${stats}</div></div>`;
}

export function diagnosisHTML(r) {
  if (!r.diagnosis) return "";
  const d = r.diagnosis;
  return `<div class="diag"><div class="k">${t("diag_k")} · ${d.confidence === "kesin" ? t("conf_exact") : t("conf_likely")}</div>
    <h3>${esc(d.rule.name)}</h3><p>${esc(d.rule.misconception)}</p>
    <div class="compare dark"><div class="w"><b>✗ ${t("wrong_way")}</b><span class="mono">${esc(d.rule.example)}</span></div><div class="r"><b>✓ ${t("right_way")}</b>${esc(d.rule.correct_rule)}</div></div></div>`;
}

export const counterHTML = (r) => r.counterexample ? `<div class="callout blue">${icon("info")}<div><b>${t("counter_t")}</b><br>${esc(r.counterexample)}</div></div>` : "";

export function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

export async function check(el, _params, ctx) {
  const student = ctx?.state.user.role === "student";
  const [health, firstHistory] = await Promise.all([api("/api/health").catch(() => ({ model_ok: false })),
    student ? api("/api/analyses").catch(() => []) : []]);
  el.innerHTML = `<div class="grid">
    <div class="an-hero"><div><span class="eyebrow-s">${icon("steps")} ${t("an_k")}</span><h2>${t("an_t")}</h2><p>${t("an_p")}</p></div>
      <ol class="an-how"><li><b>1</b>${t("an_h1")}</li><li><b>2</b>${t("an_h2")}</li><li><b>3</b>${t("an_h3")}</li></ol></div>
    <div class="grid g-an" style="align-items:start">
    <div class="card"><div class="card-h"><div><h2>${t("check_t")}</h2><p>${t("check_p")}</p></div></div>
      ${health.model_ok ? "" : `<div class="callout amber" style="margin-bottom:14px">${icon("info")}<span>${t("model_off")}</span></div>`}
      <div class="seg tabs-mini" id="tabs"><button data-tab="photo" class="on">${icon("camera")} ${t("tab_photo")}</button><button data-tab="type">${icon("code")} ${t("tab_type")}</button></div>
      <div id="tab-photo">
        <label class="drop" id="drop">${icon("upload")}<b>${t("drop_t")}</b><p class="muted" style="font-size:13.5px;margin-top:4px">${t("drop_p")}</p>
          <input type="file" accept="image/*" id="file"></label>
        <button class="btn btn-dark" id="read" style="margin-top:12px;width:100%" disabled>${icon("spark")}${t("read_btn")}</button>
        <div id="read-msg" style="margin-top:10px"></div>
      </div>
      <div class="field" style="margin-top:16px"><label>${t("lines_label")}</label>
        <textarea class="input mono" id="lines" rows="7" placeholder="${esc(t("lines_ph"))}"></textarea></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center"><span class="muted" style="font-size:13px">${t("examples")}:</span>
        ${Object.keys(EXAMPLES).map((k) => `<button class="chip chip-btn" data-ex="${k}">${t(k)}</button>`).join("")}</div>
      <button class="btn btn-primary btn-lg" id="go" style="width:100%;margin-top:16px">${icon("steps")}${t("check_btn")}</button>
    </div>
    <div class="card" id="result"><div class="empty">${icon("steps")}<h3>${t("result_empty")}</h3><p>${t("result_empty_p")}</p></div></div>
    </div>
    ${student ? `<div class="card"><div class="card-h"><div><h2>${t("an_hist_t")}</h2><p>${t("an_hist_p")}</p></div></div><div id="hist"></div></div>` : ""}
  </div>`;
  let file = null;
  const showTab = (name) => {
    $$("#tabs button", el).forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
    $("#tab-photo", el).classList.toggle("hidden", name !== "photo");
  };
  $$("#tabs button", el).forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  const drop = $("#drop", el);
  const setFile = (f) => {
    if (!f) return;
    file = f;
    drop.innerHTML = `<img src="${URL.createObjectURL(f)}" alt=""><input type="file" accept="image/*" id="file">`;
    $("#file", el).addEventListener("change", (e) => setFile(e.target.files[0]));
    $("#read", el).disabled = !health.model_ok;
  };
  $("#file", el).addEventListener("change", (e) => setFile(e.target.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); setFile(e.dataTransfer.files[0]); });
  $("#read", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true, t("reading"));
    try {
      const form = new FormData(); form.append("file", file);
      const r = await api("/api/read-image", { method: "POST", form });
      $("#lines", el).value = r.lines.map((l) => l.text).join("\n");
      $("#read-msg", el).innerHTML = `<div class="callout green">${icon("checkc")}<span>${t("read_ok", { n: r.lines.length })}</span></div>`;
    } catch (err) { $("#read-msg", el).innerHTML = `<div class="callout coral">${icon("alert")}<span>${esc(errText(err))}</span></div>`; }
    busy(btn, false);
  });
  $$("[data-ex]", el).forEach((b) => b.addEventListener("click", () => { $("#lines", el).value = EXAMPLES[b.dataset.ex]; showTab("type"); }));
  let history = firstHistory;
  const drawHistory = () => {
    const box = $("#hist", el);
    if (!box) return;
    box.innerHTML = history.length ? `<div class="hist">${history.map((h, k) => `<button class="hist-i" data-h="${k}"><span class="dot" style="background:${h.correct ? "#1E9E5A" : "#FF5A5F"}"></span>
        <span class="mono">${esc(h.problem)}</span><span class="muted">${fmtDate(h.ts)} · ${h.correct ? t("an_ok") : h.rule ? esc(h.rule.name) : t("first_error", { n: (h.first_error ?? 0) + 1 })}</span></button>`).join("")}</div>`
      : `<p class="muted">${t("an_hist_empty")}</p>`;
    $$("[data-h]", box).forEach((b) => b.addEventListener("click", () => {
      $("#lines", el).value = history[Number(b.dataset.h)].lines.join("\n"); showTab("type"); $("#go", el).click();
    }));
  };
  const refreshHistory = async () => { history = await api("/api/analyses").catch(() => history); drawHistory(); };
  drawHistory();
  $("#go", el).addEventListener("click", (e) => run(e.currentTarget));

  async function run(btn) {
    const lines = $("#lines", el).value.split("\n").filter((l) => l.trim());
    const res = $("#result", el);
    if (lines.length < 2) { toast(t("err_lines"), true); return; }
    busy(btn, true, t("checking"));
    res.innerHTML = `<div class="skeleton" style="height:90px;margin-bottom:12px"></div><div class="skeleton" style="height:220px"></div>`;
    try {
      // the verdict comes from SymPy in a moment; Gemma's explanation is fetched afterwards
      const r = await api("/api/check", { method: "POST", body: { lines, explain: false } });
      const rule = r.diagnosis?.rule.id;
      res.innerHTML = `${verdictHTML(r)}<div class="an-body">${stepsHTML(r)}${diagnosisHTML(r)}${counterHTML(r)}
        ${r.first_error != null ? `<div id="expl"><div class="explain loading"><div class="explain-h">${icon("spark")} ${t("explain_t")}</div><div class="typing"><i></i><i></i><i></i></div><span class="muted" style="font-size:13px">${t("explaining")}</span></div></div>` : ""}</div>
        <div class="an-actions">
          ${rule ? `<a class="btn btn-primary btn-sm" href="#/app/practice?rules=${encodeURIComponent(rule)}&count=5">${icon("target")}${t("practice_btn")}</a>` : ""}
          ${rule && student ? `<a class="btn btn-ghost btn-sm" href="#/app/study?topic=${encodeURIComponent(r.practice_topic)}&chat=1">${icon("spark")}${t("ask_assistant")}</a>` : ""}
          <button class="btn btn-ghost btn-sm" id="pdf">${icon("file")}${t("pdf_btn")}</button></div>`;
      $("#pdf", el).addEventListener("click", async (ev) => {
        const b = ev.currentTarget; busy(b, true);
        try { download(await (await api("/api/report.pdf", { method: "POST", body: { lines, explain: false }, raw: true })).blob(), "misstep-rapor.pdf"); }
        catch (err) { toast(errText(err), true); }
        busy(b, false);
      });
      busy(btn, false);
      if (student) refreshHistory();
      if (r.first_error != null) {
        const x = await api("/api/check-explain", { method: "POST", body: { lines } }).catch(() => null);
        const slot = $("#expl", el);
        if (slot) slot.innerHTML = x && x.explanation ? explanationHTML(x) : "";
      }
    } catch (err) { res.innerHTML = `<div class="callout coral">${icon("alert")}<span>${esc(errText(err))}</span></div>`; busy(btn, false); }
  }
}
