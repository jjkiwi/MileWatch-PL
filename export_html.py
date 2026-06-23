"""Generuje samodzielny plik HTML z promocjami - "eksport na inne urzadzenie".

Plik jest w 100% samowystarczalny: dane sa wstrzykniete jako JSON, a filtrowanie
dziala po stronie przegladarki (czysty JS, bez serwera). Mozna go:
  * otworzyc dwuklikiem na dowolnym urzadzeniu (dziala offline),
  * wyslac mailem / komunikatorem,
  * wrzucic na darmowy GitHub Pages, zeby dostac wspoldzielony link (patrz README).
"""

import html
import json
from datetime import datetime, timezone

from digest import is_relevant
from models import Promotion
from scoring import score_promo


def promotions_to_dicts(promotions: list[Promotion], profile: dict) -> list[dict]:
    out = []
    for p in promotions:
        out.append({
            "tytul": p.tytul,
            "typ": p.typ,
            "bonus_pct": p.bonus_pct,
            "partner": p.partner,
            "wazne_do": p.wazne_do,
            "regiony": p.regiony,
            "zrodlo_url": p.zrodlo_url,
            "zrodlo_nazwa": p.zrodlo_nazwa,
            "streszczenie": p.streszczenie,
            "widziane": (p.pierwszy_raz_widziane or "")[:10],
            "profil": is_relevant(p, profile),
            "score": score_promo(p),
        })
    return out


def render_html(promotions: list[Promotion], profile: dict) -> str:
    data = promotions_to_dicts(promotions, profile)
    data_json = json.dumps(data, ensure_ascii=False)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    count = len(data)

    # Uwaga: dane wstrzykujemy jako JSON do <script>; zamykajacy tag rozbijamy,
    # zeby zlosliwy ciag "</script>" w danych nie zepsul strony.
    safe_json = data_json.replace("</", "<\\/")

    return TEMPLATE.replace("__DATA__", safe_json) \
                   .replace("__GENERATED__", html.escape(generated)) \
                   .replace("__COUNT__", str(count))


def write_export(promotions: list[Promotion], profile: dict, out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render_html(promotions, profile))
    return out_path


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MileWatch PL - promocje Miles &amp; More</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; max-width: 820px;
         margin: 0 auto; padding: 1rem; color: #1a1a1a; background: #fafafa; }
  @media (prefers-color-scheme: dark) {
    body { color: #e8e8e8; background: #16181c; }
    .promo { background: #22252b !important; border-color: #333 !important; }
    .filters select, .filters input { background: #22252b; color: #e8e8e8; border: 1px solid #444; }
    .badge { background: #333 !important; color: #ddd; }
  }
  h1 { margin: 0; font-size: 1.5rem; }
  .subtitle { color: #888; margin: .25rem 0 1rem; font-size: .9rem; }
  .filters { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .filters select, .filters input { padding: .45rem; font-size: .9rem; border-radius: 6px;
         border: 1px solid #ccc; }
  .filters input { flex: 1; min-width: 140px; }
  .promos { list-style: none; padding: 0; margin: 0; }
  .promo { background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
           padding: .9rem 1rem; margin-bottom: .8rem; }
  .promo.profil { border-left: 4px solid #2a7a2a; }
  .promo.error { border-left: 4px solid #c0392b; background: #fff5f5; }
  .promo.tani { border-left: 4px solid #d35400; background: #fff8f2; }
  .promo.biznes { border-left: 4px solid #c79100; background: #fffdf3; }
  @media (prefers-color-scheme: dark) {
    .promo.error { background: #2c2020 !important; }
    .promo.tani { background: #2b2420 !important; }
    .promo.biznes { background: #2b2820 !important; }
  }
  .promo-head { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
  .badge { background: #eee; border-radius: 5px; padding: .15rem .5rem; font-size: .72rem;
           text-transform: uppercase; letter-spacing: .03em; }
  .bonus { color: #c47a00; font-weight: 700; }
  .score { background: #2a7a2a; color: #fff; border-radius: 5px; padding: .1rem .4rem;
           font-size: .72rem; font-weight: 700; }
  .tytul { font-weight: 600; }
  .tag-profil { color: #2a7a2a; font-size: .78rem; margin-left: auto; }
  .stresz { margin: .5rem 0; }
  .meta { display: flex; gap: 1rem; flex-wrap: wrap; font-size: .78rem; color: #888; }
  .src { font-size: .82rem; display: inline-block; margin-top: .4rem; }
  .empty { color: #888; font-style: italic; }
  footer { margin-top: 1.5rem; font-size: .75rem; color: #999; text-align: center; }
</style>
</head>
<body>
  <h1>MileWatch PL</h1>
  <p class="subtitle">Promocje Miles &amp; More &middot; <span id="count">__COUNT__</span> &middot;
     wygenerowano: __GENERATED__</p>

  <div class="filters">
    <input id="q" type="search" placeholder="Szukaj w tytule / streszczeniu...">
    <select id="fTyp"><option value="">Wszystkie typy</option></select>
    <select id="fPartner"><option value="">Wszyscy partnerzy</option></select>
    <select id="fRegion"><option value="">Wszystkie regiony</option></select>
    <label style="font-size:.85rem;display:flex;align-items:center;gap:.3rem;">
      <input type="checkbox" id="fProfil"> tylko z profilu
    </label>
  </div>

  <ul class="promos" id="list"></ul>
  <p class="empty" id="empty" style="display:none">Brak promocji dla wybranych filtrow.</p>

  <footer>MileWatch PL &mdash; darmowy tracker promocji Miles &amp; More.
     Plik dziala offline. Tresci opisane wlasnymi slowami; szczegoly w zrodle.</footer>

<script>
const DATA = __DATA__;
const TYPE_LABELS = { buy_miles:"kup mile", partner_bonus:"bonus partnera",
  mileage_bargain:"okazja milowa", card:"karta", other:"inne",
  error_fare:"BLAD CENOWY", great_deal:"tani lot / mega", business_class:"tania biznes" };

function uniq(arr){ return [...new Set(arr.filter(Boolean))].sort(); }
function fill(sel, vals){ for(const v of vals){ const o=document.createElement("option");
  o.value=v; o.textContent=v; sel.appendChild(o);} }

const PERLY = {error_fare:1, great_deal:1, business_class:1};
// Sortowanie: perelki z preferowanym wylotem na gorze, perelki zagraniczne nizej, reszta na koncu.
function _rank(p){
  const perla = !!PERLY[p.typ];
  const zagr = (p.regiony||[]).includes("Wylot zagraniczny");
  return perla ? (zagr ? 1 : 0) : 2;
}
DATA.sort((a,b)=> (_rank(a)-_rank(b)) || ((b.score||0)-(a.score||0)));

fill(document.getElementById("fTyp"), uniq(DATA.map(p=>p.typ)));
fill(document.getElementById("fPartner"), uniq(DATA.map(p=>p.partner)));
fill(document.getElementById("fRegion"), uniq(DATA.flatMap(p=>p.regiony||[])));

function esc(s){ const d=document.createElement("div"); d.textContent=s==null?"":s; return d.innerHTML; }

function render(){
  const q=document.getElementById("q").value.toLowerCase().trim();
  const ft=document.getElementById("fTyp").value;
  const fp=document.getElementById("fPartner").value;
  const fr=document.getElementById("fRegion").value;
  const fpr=document.getElementById("fProfil").checked;
  const list=document.getElementById("list"); list.innerHTML="";
  let shown=0;
  for(const p of DATA){
    if(ft && p.typ!==ft) continue;
    if(fp && p.partner!==fp) continue;
    if(fr && !(p.regiony||[]).includes(fr)) continue;
    if(fpr && !p.profil) continue;
    if(q && !((p.tytul||"").toLowerCase().includes(q) || (p.streszczenie||"").toLowerCase().includes(q))) continue;
    shown++;
    const li=document.createElement("li");
    const cls = p.typ==="error_fare" ? " error" : p.typ==="great_deal" ? " tani"
              : p.typ==="business_class" ? " biznes" : (p.profil?" profil":"");
    li.className="promo"+cls;
    const bonus = p.bonus_pct ? `<span class="bonus">+${p.bonus_pct}%</span>` : "";
    const tag = PERLY[p.typ] ? `<span class="tag-profil">&#9733; perelka</span>`
              : p.profil ? `<span class="tag-profil">&#10003; profil</span>` : "";
    const meta=[];
    if(p.partner) meta.push("Partner: "+esc(p.partner));
    if((p.regiony||[]).length) meta.push("Region: "+esc(p.regiony.join(", ")));
    if(p.wazne_do) meta.push("Wazne do: "+esc(p.wazne_do));
    if(p.widziane) meta.push("Widziane: "+esc(p.widziane));
    const score = (p.score!=null) ? `<span class="score">★ ${p.score}</span>` : "";
    li.innerHTML = `<div class="promo-head">
        <span class="badge">${esc(TYPE_LABELS[p.typ]||p.typ)}</span>${score}${bonus}
        <span class="tytul">${esc(p.tytul)}</span>${tag}</div>
      <p class="stresz">${esc(p.streszczenie)}</p>
      <div class="meta">${meta.map(m=>`<span>${m}</span>`).join("")}</div>
      ${p.zrodlo_url?`<a class="src" href="${esc(p.zrodlo_url)}" target="_blank" rel="noopener">Zrodlo: ${esc(p.zrodlo_nazwa||"link")}</a>`:""}`;
    list.appendChild(li);
  }
  document.getElementById("count").textContent=shown;
  document.getElementById("empty").style.display = shown? "none":"block";
}
for(const id of ["q","fTyp","fPartner","fRegion","fProfil"])
  document.getElementById(id).addEventListener("input", render);
render();
</script>
</body>
</html>
"""
