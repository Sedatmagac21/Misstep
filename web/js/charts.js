// Charts drawn as plain SVG: study calendar, daily bars, mastery bars, accuracy ring.
import { getLang, t } from "./i18n.js";
import { esc, masteryColor, pct } from "./ui.js";

const GREENS = ["#EBEDF0", "#9BE9A8", "#40C463", "#30A14E", "#216E39"];
const level = (n) => (n === 0 ? 0 : n <= 2 ? 1 : n <= 5 ? 2 : n <= 8 ? 3 : 4);
const loc = () => (getLang() === "en" ? "en-GB" : "tr-TR");

export function heatmap(days) {
  // days: oldest -> newest, one per day; draw full weeks (Monday first) ending today
  const cell = 13, gap = 3, last = new Date(days[days.length - 1].date);
  const weekday = (last.getDay() + 6) % 7;
  const total = 26 * 7 - (6 - weekday);
  const slice = days.slice(-total);
  const weeks = Math.ceil((slice.length + (6 - weekday)) / 7);
  const W = weeks * (cell + gap) + 30, H = 7 * (cell + gap) + 22;
  let rects = "", months = "", lastMonth = -1;
  slice.forEach((d, i) => {
    const w = Math.floor(i / 7), dow = i % 7, n = d.correct + d.wrong;
    const date = new Date(d.date);
    if (dow === 0 && date.getMonth() !== lastMonth) {
      lastMonth = date.getMonth();
      months += `<text x="${30 + w * (cell + gap)}" y="10" font-size="10" fill="#64748B">${date.toLocaleDateString(loc(), { month: "short" })}</text>`;
    }
    const tip = `${date.toLocaleDateString(loc(), { day: "numeric", month: "long" })}: ${n} · ${t("correct")} ${d.correct}, ${t("wrong")} ${d.wrong}`;
    rects += `<rect x="${30 + w * (cell + gap)}" y="${18 + dow * (cell + gap)}" width="${cell}" height="${cell}" rx="3" fill="${GREENS[level(n)]}"><title>${esc(tip)}</title></rect>`;
  });
  const dayNames = getLang() === "en" ? ["Mon", "", "Wed", "", "Fri", "", ""] : ["Pzt", "", "Çar", "", "Cum", "", ""];
  const labels = dayNames.map((n, i) => n ? `<text x="0" y="${28 + i * (cell + gap)}" font-size="10" fill="#64748B">${n}</text>` : "").join("");
  return `<div class="heat"><svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;min-width:${W}px;max-width:${Math.round(W * 1.45)}px" role="img" aria-label="${esc(t("heat_t"))}">${months}${labels}${rects}</svg></div>
    <div class="legend" style="margin-top:10px;justify-content:flex-end">${t("less")} ${GREENS.map((c) => `<i style="background:${c}"></i>`).join("")} ${t("more")}</div>`;
}

export function dailyBars(days) {
  const d14 = days.slice(-14), max = Math.max(4, ...d14.map((d) => d.correct + d.wrong));
  const W = 560, H = 190, pad = 24, bw = (W - pad * 2) / 14;
  let bars = "";
  d14.forEach((d, i) => {
    const x = pad + i * bw + bw * 0.18, w = bw * 0.64;
    const hc = (d.correct / max) * (H - 50), hw = (d.wrong / max) * (H - 50), base = H - 26;
    const date = new Date(d.date);
    const tip = `${date.toLocaleDateString(loc(), { day: "numeric", month: "long" })}: ${t("correct")} ${d.correct}, ${t("wrong")} ${d.wrong}`;
    bars += `<g><title>${esc(tip)}</title>
      ${d.wrong ? `<rect x="${x}" y="${base - hc - hw}" width="${w}" height="${hw}" rx="4" fill="#FF5A5F"/>` : ""}
      ${d.correct ? `<rect x="${x}" y="${base - hc}" width="${w}" height="${hc}" rx="4" fill="#1E9E5A"/>` : ""}
      ${!d.correct && !d.wrong ? `<rect x="${x}" y="${base - 3}" width="${w}" height="3" rx="1.5" fill="#E4E8F0"/>` : ""}
      <text x="${x + w / 2}" y="${H - 8}" font-size="10.5" text-anchor="middle" fill="#64748B">${date.getDate()}</text></g>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto" role="img" aria-label="${esc(t("daily_t"))}">
    <line x1="${pad}" x2="${W - pad}" y1="${H - 26}" y2="${H - 26}" stroke="#E4E8F0"/>${bars}</svg>
    <div class="legend" style="gap:14px;margin-top:4px"><span><i style="background:#1E9E5A"></i> ${t("correct")}</span><span><i style="background:#FF5A5F"></i> ${t("wrong")}</span></div>`;
}

export function masteryBars(items) {
  // items: [{name, mastery|null, sub?}]
  return `<div class="bars-list">${items.map((it) => `
    <div class="bar-row ${it.mastery == null ? "unseen" : ""}"><span class="name">${esc(it.name)}${it.sub ? ` <span class="muted" style="font-weight:500;font-size:12.5px">· ${esc(it.sub)}</span>` : ""}</span>
      <span class="pct">${it.mastery == null ? t("not_seen") : pct(it.mastery)}</span>
      <div class="track"><div class="fill" style="width:${Math.round((it.mastery ?? 0) * 100)}%;background:${masteryColor(it.mastery)}"></div></div></div>`).join("")}</div>`;
}

export function ring(value, size = 120, label = "") {
  const r = size / 2 - 10, c = 2 * Math.PI * r, v = value ?? 0;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="${esc(label)}">
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="#EEF1F6" stroke-width="12"/>
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${masteryColor(v)}" stroke-width="12" stroke-linecap="round"
      stroke-dasharray="${c * v} ${c}" transform="rotate(-90 ${size / 2} ${size / 2})"/>
    <text x="50%" y="52%" text-anchor="middle" dominant-baseline="middle" font-size="${size / 5}" font-weight="800" fill="#0F172A">${value == null ? "–" : pct(value)}</text></svg>`;
}

export function pie(parts, size = 170, center = "", sub = "") {
  // parts: [{value, color, label}] drawn as a donut, largest share first
  const total = parts.reduce((a, p) => a + p.value, 0) || 1, r = size / 2 - 14, c = 2 * Math.PI * r;
  let off = 0, arcs = "";
  parts.forEach((p) => {
    if (!p.value) return;
    const len = (p.value / total) * c;
    arcs += `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${p.color}" stroke-width="22"
      stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}" transform="rotate(-90 ${size / 2} ${size / 2})"><title>${esc(p.label)}: ${p.value}</title></circle>`;
    off += len;
  });
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="${esc(parts.map((p) => `${p.label} ${p.value}`).join(", "))}">
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="#EEF1F6" stroke-width="22"/>${arcs}
    <text x="50%" y="${sub ? "47%" : "52%"}" text-anchor="middle" dominant-baseline="middle" font-size="${size / 6}" font-weight="800" fill="#0F172A">${esc(center)}</text>
    ${sub ? `<text x="50%" y="63%" text-anchor="middle" font-size="12" fill="#64748B">${esc(sub)}</text>` : ""}</svg>`;
}

export function levelPath(items) {
  // items: [{level: "easy"|"medium"|"hard", correct: bool|null}] for the adaptive test
  const L = ["easy", "medium", "hard"], W = Math.max(320, items.length * 44 + 70), H = 150, x0 = 64, dx = (W - x0 - 20) / Math.max(1, items.length - 1);
  const y = (lv) => 24 + (2 - L.indexOf(lv)) * 45;
  const pts = items.map((it, i) => [items.length === 1 ? x0 : x0 + i * dx, y(it.level)]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0]},${p[1]}`).join(" ");
  const labels = L.map((lv) => `<text x="0" y="${y(lv) + 4}" font-size="11.5" fill="#64748B">${t("lv_" + lv)}</text><line x1="${x0 - 10}" x2="${W - 10}" y1="${y(lv)}" y2="${y(lv)}" stroke="#EEF1F6"/>`).join("");
  const dots = items.map((it, i) => `<circle cx="${pts[i][0]}" cy="${pts[i][1]}" r="9" fill="${it.correct == null ? "#CBD3E1" : it.correct ? "#1E9E5A" : "#FF5A5F"}" stroke="#fff" stroke-width="3"><title>${i + 1}. ${t("lv_" + it.level)}</title></circle>
    <text x="${pts[i][0]}" y="${H - 4}" font-size="10.5" text-anchor="middle" fill="#64748B">${i + 1}</text>`).join("");
  return `<div style="overflow-x:auto"><svg viewBox="0 0 ${W} ${H}" style="width:100%;min-width:${Math.min(W, 520)}px;height:auto" role="img" aria-label="${esc(t("ad_path_t"))}">
    ${labels}<path d="${line}" fill="none" stroke="#14213D" stroke-width="2.5" stroke-linejoin="round"/>${dots}</svg></div>`;
}
