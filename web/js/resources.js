// "Kaynaklar": Misstep's notes plus files the student or their teacher uploaded (PDF, Word, text).
import { t } from "./i18n.js";
import { noteHTML } from "./analysis.js";
import { $, $$, api, busy, errText, esc, fmtDate, icon, modal, toast } from "./ui.js";

const KIND = { pdf: ["PDF", "coral"], docx: ["DOCX", "blue"], md: ["MD", "navy"], txt: ["TXT", ""] };
const size = (b) => (b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`);

export async function resources(el, _params, ctx) {
  const teacher = ctx.state.user.role === "teacher";
  let filter = "all";
  el.innerHTML = `<div class="grid">
    <div class="grid g-main" style="align-items:stretch">
      <div class="card"><div class="card-h"><div><h2>${t("res_t")}</h2><p>${teacher ? t("res_p_teacher") : t("res_p2")}</p></div></div>
        <div class="search">${icon("search")}<input class="input" id="q" placeholder="${esc(t("res_search"))}"></div>
        <div class="seg" id="filters" style="margin-top:14px">${["all", "mine", ...(teacher ? [] : ["shared"]), "note"].map((f) => `<button data-f="${f}">${t("rf_" + f)}</button>`).join("")}</div></div>
      <div class="card"><h2 class="h-ic" style="margin-bottom:6px">${icon("upload")} ${t("up_t")}</h2><p class="muted" style="font-size:13.5px;margin-bottom:12px">${teacher ? t("up_p_teacher") : t("up_p")}</p>
        <label class="drop small" id="drop">${icon("file")}<b id="fname">${t("up_drop")}</b><p class="muted" style="font-size:12.5px;margin-top:2px">PDF · Word (.docx) · TXT · MD · ≤ 15 MB</p>
          <input type="file" id="file" accept=".pdf,.docx,.txt,.md"></label>
        <input class="input" id="title" style="margin-top:10px" placeholder="${esc(t("up_title"))}">
        <button class="btn btn-primary" id="up" style="width:100%;margin-top:10px" disabled>${icon("upload")}${t("up_btn")}</button></div>
    </div>
    <div id="out"></div></div>`;
  let file = null;
  const setFile = (f) => {
    if (!f) return;
    file = f; $("#fname", el).textContent = f.name; $("#up", el).disabled = false;
    if (!$("#title", el).value) $("#title", el).value = f.name.replace(/\.[^.]+$/, "");
  };
  const drop = $("#drop", el);
  $("#file", el).addEventListener("change", (e) => setFile(e.target.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); setFile(e.dataTransfer.files[0]); });
  $("#up", el).addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    busy(btn, true, t("up_busy"));
    try {
      const form = new FormData(); form.append("file", file); form.append("title", $("#title", el).value);
      const d = await api("/api/documents", { method: "POST", form });
      toast(t("up_ok", { n: d.passages }));
      file = null; $("#title", el).value = ""; $("#fname", el).textContent = t("up_drop");
      await load();
    } catch (err) { toast(errText(err), true); }
    busy(btn, false); btn.disabled = !file;
  });

  let docs = [], notes = [];
  async function load() {
    [docs, notes] = await Promise.all([api("/api/documents"), api("/api/resources")]);
    draw();
  }
  function draw(hits = null) {
    $$("#filters button", el).forEach((b) => b.classList.toggle("on", b.dataset.f === filter));
    const out = $("#out", el);
    if (hits) {
      out.innerHTML = `<div class="card"><div class="card-h"><div><h2>${t("res_hits", { n: hits.length })}</h2><p>${t("res_hits_p")}</p></div></div>
        ${hits.length ? `<div class="list">${hits.map((h, k) => `<div class="li" style="align-items:flex-start"><span class="chip ${h.source === "note" ? "blue" : "amber"}">${t(h.source === "note" ? "src_note" : h.source === "mine" ? "src_mine" : "src_shared")}</span>
          <div style="flex:1;min-width:0"><div class="t">${esc(h.title)}</div><div class="s clamp">${esc(h.text.replace(/\*\*|^#+\s*|\s#+\s/gm, " ").slice(0, 260))}</div></div>
          <div class="end"><button class="btn btn-ghost btn-sm" data-hit="${k}">${t("open")}</button></div></div>`).join("")}</div>` : `<div class="empty">${icon("search")}<p>${t("res_none")}</p></div>`}</div>`;
      $$("[data-hit]", out).forEach((b) => b.addEventListener("click", () => {
        const h = hits[Number(b.dataset.hit)];
        modal(`<div style="display:flex;align-items:center;gap:10px"><h3>${esc(h.title)}</h3><button class="btn btn-ghost btn-sm" data-close style="margin-left:auto">${t("close")}</button></div><div style="margin-top:12px;max-height:60vh;overflow:auto">${noteHTML(h.text)}</div>`);
      }));
      return;
    }
    const shownDocs = docs.filter((d) => filter === "all" || (filter === "mine" && d.mine) || (filter === "shared" && !d.mine));
    out.innerHTML = `${filter !== "note" ? `<div class="card" style="margin-bottom:20px"><div class="card-h"><div><h2>${t(filter === "shared" ? "rf_shared" : "res_files")}</h2><p>${t("res_files_p")}</p></div></div>
        ${shownDocs.length ? `<div class="doc-grid">${shownDocs.map((d) => `<div class="doc-card">
          <span class="doc-ic ${KIND[d.kind]?.[1] || ""}">${KIND[d.kind]?.[0] || "?"}</span>
          <div class="doc-m"><b>${esc(d.title)}</b><span>${d.mine ? t("src_mine") : esc(d.owner)} · ${fmtDate(d.created)} · ${size(d.size)} · ${t("passages_n", { n: d.passages })}</span></div>
          <div class="doc-a"><button class="btn btn-ghost btn-sm" data-view="${d.id}">${t("open")}</button><a class="btn btn-ghost btn-sm" href="/api/documents/${d.id}/file" aria-label="${t("download")}">${icon("download")}</a>
            ${d.mine ? `<button class="btn btn-ghost btn-sm danger" data-del="${d.id}" aria-label="${t("delete")}">${icon("x")}</button>` : ""}</div></div>`).join("")}</div>`
          : `<div class="empty" style="padding:24px">${icon("file")}<p>${filter === "shared" ? t("res_shared_empty") : t("res_files_empty")}</p></div>`}</div>` : ""}
      ${filter === "all" || filter === "note" ? `<div class="card-h" style="margin:4px 2px 12px"><div><h2>${t("rf_note")}</h2><p>${t("res_notes_p")}</p></div></div>
        <div class="grid g2">${notes.map((c, k) => `<div class="res-card"><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">${c.topic ? `<span class="chip">${esc(c.topic)}</span>` : `<span class="chip navy">${t("res_all")}</span>`}</div>
          <h3>${esc(c.title)}</h3><div class="body">${noteHTML(c.text)}</div>
          <button class="btn btn-ghost btn-sm" style="align-self:flex-start" data-k="${k}">${t("read_more")}</button></div>`).join("")}</div>` : ""}`;
    $$("[data-k]", out).forEach((b) => b.addEventListener("click", () => {
      const card = b.closest(".res-card"); card.classList.toggle("open"); b.textContent = card.classList.contains("open") ? t("show_less") : t("read_more");
    }));
    $$("[data-view]", out).forEach((b) => b.addEventListener("click", async () => {
      const d = await api(`/api/documents/${b.dataset.view}`);
      modal(`<div style="display:flex;align-items:center;gap:10px"><h3>${esc(d.title)}</h3><span class="chip">${esc(d.filename)}</span><button class="btn btn-ghost btn-sm" data-close style="margin-left:auto">${t("close")}</button></div>
        <div class="doc-text">${esc(d.text)}</div>`).querySelector(".modal").style.width = "min(820px, 100%)";
    }));
    $$("[data-del]", out).forEach((b) => b.addEventListener("click", async () => {
      if (!confirm(t("del_confirm"))) return;
      try { await api(`/api/documents/${b.dataset.del}`, { method: "DELETE" }); toast(t("deleted")); load(); } catch (err) { toast(errText(err), true); }
    }));
  }
  $$("#filters button", el).forEach((b) => b.addEventListener("click", () => { filter = b.dataset.f; $("#q", el).value = ""; draw(); }));
  let timer;
  $("#q", el).addEventListener("input", (e) => {
    clearTimeout(timer);
    const q = e.target.value.trim();
    timer = setTimeout(async () => draw(q ? await api(`/api/resources?q=${encodeURIComponent(q)}`) : null), 300);
  });
  await load();
}
