// "Hata Avı": a classmate's solution with one injected mistake. Find the wrong line, then name the misconception.
import { t } from "./i18n.js";
import { LEVELS, lvlBars } from "./practice.js";
import { $, $$, api, busy, errText, esc, icon, initials, toast } from "./ui.js";

export async function hunt(el, params) {
  let level = LEVELS.includes(params.get("level")) ? params.get("level") : "medium";
  let weak = params.get("weak") === "1";
  let stats = await api("/api/hunt/stats");
  let next = null; // the following puzzle is fetched while this one is solved
  const fetchHunt = () => api("/api/hunt/new", { method: "POST", body: { level, weak } });

  el.innerHTML = `<div class="grid">
    <div class="an-hero hunt-hero"><div><span class="chip coral">${icon("search")} ${t("hunt_badge")}</span><h2>${t("hunt_t")}</h2><p>${t("hunt_p")}</p></div>
      <div class="hunt-score" id="score"></div></div>
    <div class="grid g-main" style="align-items:start">
      <div id="board"><div class="skeleton" style="height:320px"></div></div>
      <div class="card"><h2 style="margin-bottom:12px">${t("hunt_settings")}</h2>
        <div class="field"><label>${t("level")}</label><div class="level-pick" id="lv">${LEVELS.map((l) => `<button data-lv="${l}"><b>${lvlBars(l)} ${t("lv_" + l)}</b></button>`).join("")}</div></div>
        <label class="switch" style="margin-top:14px"><input type="checkbox" id="weak" ${weak ? "checked" : ""}><span class="tg"></span>${t("hunt_weak")}</label>
        <div class="callout blue" style="margin-top:16px">${icon("info")}<div><b>${t("hunt_how_t")}</b><br>${t("hunt_how")}</div></div>
        <p class="hint" style="margin-top:12px">${icon("shield")} ${t("hunt_verified")}</p></div>
    </div></div>`;

  const drawScore = () => {
    $("#score", el).innerHTML = [["points", "spark", stats.points], ["solved", "checkc", `${stats.solved}/${stats.played}`], ["streak", "flame", stats.streak], ["best", "trend", stats.best]]
      .map(([k, ic, v]) => `<div><span>${icon(ic)}${t("hunt_" + k)}</span><b>${v}</b></div>`).join("");
  };
  const syncLevel = () => $$("#lv button", el).forEach((b) => b.classList.toggle("on", b.dataset.lv === level));
  $$("#lv button", el).forEach((b) => b.addEventListener("click", () => { level = b.dataset.lv; syncLevel(); next = null; play(); }));
  $("#weak", el).addEventListener("change", (e) => { weak = e.target.checked; next = null; play(); });
  drawScore(); syncLevel();

  async function play() {
    const board = $("#board", el);
    board.innerHTML = `<div class="card"><div class="empty">${icon("search")}<p>${t("hunt_loading")}</p></div></div>`;
    let h;
    try { h = await (next || fetchHunt()); } catch (err) { board.innerHTML = `<div class="callout coral">${icon("alert")}<span>${esc(errText(err))}</span></div>`; return; }
    next = fetchHunt().catch(() => null);
    let line = null, rule = null;
    board.innerHTML = `<div class="card hunt">
      <div class="hunt-who"><span class="avatar-s">${esc(initials(h.student))}</span><div><b>${t("hunt_whose", { n: esc(h.student) })}</b><div class="muted" style="font-size:13px">${esc(h.topic)} · ${t("lv_" + h.level)} · ${esc(h.instruction)}</div></div></div>
      <div class="step-h"><b>1</b>${t("hunt_q1")}</div>
      <div class="hunt-lines" id="lines">${h.lines.map((l, i) => `<button class="hl ${i === 0 ? "given" : ""}" data-i="${i}" ${i === 0 ? "disabled" : ""}><span class="n">${i + 1}</span><span class="mono">${esc(l)}</span>
        <span class="tag">${i === 0 ? t("given") : ""}</span></button>`).join("")}</div>
      <div id="q2" class="hidden"><div class="step-h"><b>2</b>${t("hunt_q2")}</div>
        <div class="hunt-opts">${h.options.map((o) => `<button class="opt" data-r="${o.id}"><b>${esc(o.name)}</b><span>${esc(o.misconception)}</span></button>`).join("")}</div></div>
      <button class="btn btn-primary" id="go" style="margin-top:18px" disabled>${icon("check")}${t("hunt_check")}</button>
      <div id="res"></div></div>`;
    const sync = () => {
      $$("#lines .hl", board).forEach((b) => b.classList.toggle("on", Number(b.dataset.i) === line));
      $$(".opt", board).forEach((b) => b.classList.toggle("on", b.dataset.r === rule));
      $("#q2", board).classList.toggle("hidden", line == null);
      $("#go", board).disabled = line == null || rule == null;
    };
    $$("#lines .hl", board).forEach((b) => b.addEventListener("click", () => { line = Number(b.dataset.i); sync(); }));
    $$(".opt", board).forEach((b) => b.addEventListener("click", () => { rule = b.dataset.r; sync(); }));
    $("#go", board).addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      busy(btn, true);
      let r;
      try { r = await api("/api/hunt/answer", { method: "POST", body: { hunt_id: h.id, line, rule } }); }
      catch (err) { toast(errText(err), true); busy(btn, false); return; }
      btn.remove();
      $$("#lines .hl, .opt", board).forEach((b) => { b.disabled = true; });
      $$("#lines .hl", board).forEach((b) => {
        const i = Number(b.dataset.i);
        b.classList.toggle("bad", i === r.wrong_index);
        b.classList.toggle("ok", i > 0 && i < r.wrong_index);
        if (i === r.wrong_index) b.querySelector(".tag").textContent = t("hunt_here");
        if (i === line && i !== r.wrong_index) b.classList.add("miss");
      });
      $$(".opt", board).forEach((b) => { b.classList.toggle("ok", b.dataset.r === r.rule.id); b.classList.toggle("miss", b.dataset.r === rule && rule !== r.rule.id); });
      const full = r.line_ok && r.rule_ok;
      stats = await api("/api/hunt/stats"); drawScore();
      $("#res", board).innerHTML = `<div class="verdict ${full ? "good" : r.line_ok ? "warn" : "bad"}" style="margin-top:18px">${icon(full ? "checkc" : "alert")}
        <div><h3>${full ? t("hunt_full") : r.line_ok ? t("hunt_half") : t("hunt_miss")} <span class="chip ${full ? "green" : ""}" style="margin-left:6px">+${r.points}</span></h3>
          <p><b>${esc(r.rule.name)}:</b> ${esc(r.rule.misconception)}</p><p style="margin-top:6px">✓ ${esc(r.rule.correct_rule)}</p>
          ${r.counterexample ? `<p class="muted" style="margin-top:6px">${esc(r.counterexample)}</p>` : ""}</div></div>
        <div style="display:flex;gap:10px;margin-top:14px;flex-wrap:wrap"><button class="btn btn-primary" id="again">${icon("arrow")}${t("hunt_next")}</button>
          <a class="btn btn-ghost" href="#/app/practice?rules=${encodeURIComponent(r.rule.id)}&level=${h.level}&count=5">${icon("target")}${t("hunt_practice")}</a></div>`;
      $("#again", board).addEventListener("click", play);
    });
  }
  play();
}
