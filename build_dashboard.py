"""Збирає статичний дашборд docs/index.html з даних пошуку (docs/data.json)."""
import json

TEMPLATE = r'''<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Можливості для лікарні: дашборд пошуку</title>
<style>
:root {
  --bg: #F2F5F3; --surface: #FFFFFF; --surface-2: #EAF0ED; --ink: #12201D; --muted: #5B6E69; --line: #D6E0DC;
  --accent: #0B6B5D; --accent-ink: #FFFFFF; --accent-soft: #D9EFE9; --new: #B3261E; --new-soft: #FBE4E1;
  --c-eu: #2F5DA8; --c-partnership: #7A4FA3; --c-training: #9A5B12; --c-grant: #0B6B5D; --c-aid: #A23B72; --c-other: #6B6F7A;
  --font: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #0E1715; --surface: #15211E; --surface-2: #1C2B27; --ink: #E5EEEB; --muted: #8FA39E; --line: #263632;
    --accent: #4FC3A8; --accent-ink: #08211B; --accent-soft: #17332D; --new: #FF8A80; --new-soft: #3A1E1C;
    --c-eu: #86AEEF; --c-partnership: #C3A0E6; --c-training: #E5A25A; --c-grant: #4FC3A8; --c-aid: #E58BBA; --c-other: #A3A8B5; color-scheme: dark; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font); font-size: 15px; line-height: 1.45; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { margin: 0; font-size: 26px; letter-spacing: -0.02em; line-height: 1.15; }
h2 { margin: 0 0 12px; font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 600; }
.top { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 16px; align-items: baseline; margin-bottom: 18px; }
.upd { color: var(--muted); font-family: var(--mono); font-size: 13px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); border: 1px solid var(--line); border-radius: 8px; background: var(--surface); margin-bottom: 18px; }
.tile { padding: 14px 16px; border-right: 1px solid var(--line); min-width: 0; }
.tile:last-child { border-right: 0; }
.tile .k { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.tile .v { margin-top: 4px; font-family: var(--mono); font-size: 26px; font-variant-numeric: tabular-nums; }
.tile .v.hot { color: var(--new); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 18px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-width: 0; }
.bar { display: grid; grid-template-columns: minmax(0, 150px) 1fr 36px; gap: 10px; align-items: center; padding: 4px 0; width: 100%; background: none; border: 0; text-align: left; cursor: pointer; color: inherit; font: inherit; }
.bar:hover .lbl { text-decoration: underline; }
.bar .lbl { font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar .track { height: 10px; background: var(--surface-2); border-radius: 3px; overflow: hidden; }
.bar .fill { height: 100%; background: var(--c); min-width: 2px; }
.bar .n { font-family: var(--mono); font-size: 13px; text-align: right; font-variant-numeric: tabular-nums; }
.spark { width: 100%; height: 64px; display: block; }
.spark rect { fill: var(--accent); }
.spark .zero { fill: var(--line); }
.spark-cap { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); font-family: var(--mono); margin-top: 4px; }
.tools { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; align-items: center; }
.chip { border: 1px solid var(--line); background: transparent; border-radius: 999px; padding: 5px 12px; cursor: pointer; font: inherit; font-size: 14px; color: inherit; }
.chip[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
input[type=search] { flex: 1 1 220px; min-width: 0; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; font: inherit; color: inherit; }
.list { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.item { padding: 12px 16px; border-top: 1px solid var(--line); }
.item:first-child { border-top: 0; }
.item a { color: var(--ink); font-weight: 600; text-decoration: none; overflow-wrap: anywhere; }
.item a:hover { color: var(--accent); text-decoration: underline; }
.meta { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 3px; font-size: 13px; color: var(--muted); align-items: center; }
.tag { font-size: 12px; font-weight: 600; display: inline-flex; gap: 6px; align-items: center; color: var(--ink); }
.tag::before { content: ""; width: 8px; height: 8px; border-radius: 2px; background: var(--c); }
.new { font-size: 11px; font-weight: 700; color: var(--new); background: var(--new-soft); border-radius: 4px; padding: 0 6px; }
.snip { margin: 4px 0 0; font-size: 14px; color: var(--muted); overflow-wrap: anywhere; }
.empty { padding: 36px 16px; text-align: center; color: var(--muted); }
.more { display: block; width: 100%; padding: 12px; border: 0; border-top: 1px solid var(--line); background: var(--surface-2); cursor: pointer; font: inherit; color: inherit; }
.status { font-size: 14px; }
.status ul { margin: 6px 0 0; padding-left: 18px; color: var(--muted); }
.foot { margin-top: 18px; color: var(--muted); font-size: 13px; }
@media (max-width: 640px) { .tile { border-right: 0; border-bottom: 1px solid var(--line); } .tile:last-child { border-bottom: 0; } }
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <h1>Можливості для лікарні</h1>
    <div class="upd" id="upd"></div>
  </div>
  <section class="tiles" id="tiles"></section>
  <section class="grid">
    <div class="card"><h2>За категоріями</h2><div id="cats"></div></div>
    <div class="card"><h2>За джерелами</h2><div id="srcs"></div></div>
    <div class="card"><h2>Нові записи за 30 днів</h2><svg class="spark" id="spark" viewBox="0 0 300 64" preserveAspectRatio="none" role="img" aria-label="Нові записи за останні 30 днів"></svg><div class="spark-cap" id="spark-cap"></div>
      <div class="status" id="status" style="margin-top:14px"></div></div>
  </section>
  <h2>Знахідки</h2>
  <div class="tools"><div id="chips" style="display:flex;flex-wrap:wrap;gap:6px"></div><input type="search" id="q" placeholder="Пошук за назвою, джерелом, текстом"></div>
  <div class="list" id="list"></div>
  <p class="foot">Записи збирає автоматичний пошук. Він не читає умови й дедлайни: відкрийте джерело й перевірте, чи ваш заклад може бути заявником.</p>
</div>
<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  var D = JSON.parse(document.getElementById("data").textContent);
  var CATS = D.categories, ITEMS = D.items || [], TODAY = D.today;
  var cat = "all", q = "", shown = 50;
  var $ = function (id) { return document.getElementById(id); };
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function fmt(iso) { if (!iso) return ""; var p = iso.split("-"); return p[2] + "." + p[1] + "." + p[0]; }
  function dayNum(iso) { var p = iso.split("-").map(Number); return Math.round(Date.UTC(p[0], p[1] - 1, p[2]) / 864e5); }
  function age(it) { return dayNum(TODAY) - dayNum(it.first_seen); }
  function safe(u) { return /^https?:\/\//i.test(u || "") ? u : null; }
  function count(list, key) { var m = {}; list.forEach(function (i) { m[i[key]] = (m[i[key]] || 0) + 1; }); return m; }

  $("upd").textContent = D.updated ? "Оновлено " + D.updated : "";

  function tiles() {
    var box = $("tiles"); box.textContent = "";
    var nToday = ITEMS.filter(function (i) { return age(i) === 0; }).length;
    var n7 = ITEMS.filter(function (i) { return age(i) < 7; }).length;
    var n30 = ITEMS.filter(function (i) { return age(i) < 30; }).length;
    [["Нових сьогодні", nToday, nToday > 0], ["За 7 днів", n7, false], ["За 30 днів", n30, false], ["Усього в базі", ITEMS.length, false]].forEach(function (t) {
      var d = el("div", "tile"); d.appendChild(el("div", "k", t[0])); d.appendChild(el("div", "v" + (t[2] ? " hot" : ""), String(t[1]))); box.appendChild(d);
    });
  }
  function bars(boxId, counts, labels, colorOf, onClick) {
    var box = $(boxId); box.textContent = "";
    var keys = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; }).slice(0, 8);
    if (!keys.length) { box.appendChild(el("div", "status", "Поки немає даних.")); return; }
    var max = counts[keys[0]];
    keys.forEach(function (k) {
      var b = el("button", "bar"); b.type = "button"; b.style.setProperty("--c", colorOf(k));
      b.appendChild(el("span", "lbl", labels(k)));
      var tr = el("span", "track"), f = el("span", "fill"); f.style.width = Math.round(counts[k] / max * 100) + "%"; tr.appendChild(f); b.appendChild(tr);
      b.appendChild(el("span", "n", String(counts[k])));
      b.addEventListener("click", function () { onClick(k); });
      box.appendChild(b);
    });
  }
  function spark() {
    var svg = $("spark"); svg.textContent = "";
    var days = [], base = dayNum(TODAY);
    for (var i = 29; i >= 0; i--) days.push(0);
    ITEMS.forEach(function (it) { var a = age(it); if (a >= 0 && a < 30) days[29 - a]++; });
    var max = Math.max.apply(null, days.concat([1])), ns = "http://www.w3.org/2000/svg";
    days.forEach(function (v, i) {
      var r = document.createElementNS(ns, "rect"), h = v ? Math.max(3, v / max * 60) : 2;
      r.setAttribute("x", i * 10 + 1); r.setAttribute("width", 8); r.setAttribute("y", 64 - h); r.setAttribute("height", h);
      if (!v) r.setAttribute("class", "zero");
      svg.appendChild(r);
    });
    var cap = $("spark-cap"); cap.textContent = ""; cap.appendChild(el("span", "", "30 днів тому")); cap.appendChild(el("span", "", "сьогодні, макс. " + max + " за день"));
  }
  function status() {
    var box = $("status"); box.textContent = "";
    var f = D.failed || [];
    if (!f.length) { box.textContent = "Усі джерела відповіли під час останнього запуску."; return; }
    box.appendChild(el("strong", "", "Не відповіли під час останнього запуску: " + f.length));
    var ul = el("ul"); f.forEach(function (x) { ul.appendChild(el("li", "", x.name)); }); box.appendChild(ul);
  }
  function chips() {
    var box = $("chips"); box.textContent = "";
    var counts = count(ITEMS, "category");
    [["all", "Усі", ITEMS.length]].concat(Object.keys(CATS).map(function (k) { return [k, CATS[k], counts[k] || 0]; })).forEach(function (c) {
      if (c[0] !== "all" && !c[2]) return;
      var b = el("button", "chip", c[1] + " " + c[2]); b.type = "button"; b.setAttribute("aria-pressed", String(cat === c[0]));
      b.addEventListener("click", function () { cat = c[0]; shown = 50; render(); }); box.appendChild(b);
    });
  }
  function list() {
    var box = $("list"); box.textContent = "";
    var ql = q.toLowerCase();
    var rows = ITEMS.filter(function (i) {
      if (cat !== "all" && i.category !== cat) return false;
      return !ql || (i.title + " " + i.source + " " + (i.snippet || "")).toLowerCase().indexOf(ql) >= 0;
    });
    if (!rows.length) { box.appendChild(el("div", "empty", ITEMS.length ? "Нічого не знайдено за цими фільтрами." : "Знахідок поки немає. Вони з'являться після першого запуску пошуку.")); return; }
    rows.slice(0, shown).forEach(function (i) {
      var d = el("div", "item"), u = safe(i.link);
      if (u) { var a = el("a", "", i.title || "Без назви"); a.href = u; a.target = "_blank"; a.rel = "noopener noreferrer"; d.appendChild(a); } else d.appendChild(el("strong", "", i.title || "Без назви"));
      var m = el("div", "meta"), t = el("span", "tag", CATS[i.category] || "Інше"); t.style.setProperty("--c", "var(--c-" + i.category + ")"); m.appendChild(t);
      m.appendChild(el("span", "", i.source));
      m.appendChild(el("span", "", "знайдено " + fmt(i.first_seen)));
      if (i.date) m.appendChild(el("span", "", "дата джерела " + fmt(i.date)));
      if (age(i) === 0) m.appendChild(el("span", "new", "НОВЕ"));
      d.appendChild(m);
      if (i.snippet) d.appendChild(el("p", "snip", i.snippet));
      box.appendChild(d);
    });
    if (rows.length > shown) { var b = el("button", "more", "Показати ще (" + (rows.length - shown) + ")"); b.type = "button"; b.addEventListener("click", function () { shown += 50; list(); }); box.appendChild(b); }
  }
  function render() { chips(); list(); }

  tiles(); spark(); status();
  bars("cats", count(ITEMS, "category"), function (k) { return CATS[k] || k; }, function (k) { return "var(--c-" + k + ")"; }, function (k) { cat = k; shown = 50; render(); });
  bars("srcs", count(ITEMS, "source"), function (k) { return k; }, function () { return "var(--accent)"; }, function (k) { q = k; $("q").value = k; shown = 50; render(); });
  $("q").addEventListener("input", function () { q = this.value.trim(); shown = 50; list(); });
  render();
})();
</script>
</body>
</html>
'''


def build(data):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload)
