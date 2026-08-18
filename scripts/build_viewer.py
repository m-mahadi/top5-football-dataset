"""Generate the human-facing card viewer: a single self-contained HTML file with
the player data embedded. Companion to data/master/player_seasons.csv (the
machine surface) and data/master/players.json (the structured surface).
"""
import json

CARDS = json.load(open('data/master/players.json', encoding='utf-8'))
# keep players with a real sample so the roster stays scannable
CARDS = [c for c in CARDS
         if any((s.get('nineties') or 0) >= 8 for s in c['seasons'])]

PCT_LABELS = [
    ('npxg_p90', 'Non-penalty xG'), ('xa_p90', 'Expected assists'),
    ('xgchain_p90', 'xG chain'), ('shots_p90', 'Shots'),
    ('key_passes_p90', 'Key passes'), ('dribbles_p90', 'Dribbles'),
    ('touches_p90', 'Touches'), ('opp_half_passes_p90', 'Passes in opp half'),
    ('final_third_passes_p90', 'Final-third passes'), ('pass_acc', 'Pass accuracy'),
    ('press_att3rd_p90', 'Press wins, att third'), ('recoveries_p90', 'Ball recoveries'),
    ('tackles_p90', 'Tackles'), ('interceptions_p90', 'Interceptions'),
    ('clearances_p90', 'Clearances'), ('aerial_pct', 'Aerial duels won'),
    ('ground_duel_pct', 'Ground duels won'), ('fouled_p90', 'Fouls won'),
]

data = json.dumps(CARDS, ensure_ascii=False, separators=(',', ':'))
labels = json.dumps(PCT_LABELS, ensure_ascii=False, separators=(',', ':'))

HTML = """<title>Blaugrana Scout Room</title>
<style>
:root{
  --ink:#12172A; --ground:#F4F5F8; --surface:#FFFFFF; --surface-2:#EBEDF3;
  --line:#D8DCE6; --text:#12172A; --muted:#5C6480; --faint:#8E96AD;
  --garnet:#A50044; --blue:#2F5FD0; --gold:#B0810E;
  --tier1:#1F9160; --tier2:#5F9E3A; --tier3:#B0810E; --tier4:#C0603A; --tier5:#B23A34;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ink:#070A14; --ground:#0B1020; --surface:#151B2E; --surface-2:#1D2440;
    --line:#2A3352; --text:#E8EBF2; --muted:#98A1BB; --faint:#6B7493;
    --garnet:#E0407F; --blue:#6C97FF; --gold:#EDBB4B;
    --tier1:#37B87C; --tier2:#84C24E; --tier3:#EDBB4B; --tier4:#E08A54; --tier5:#D2544B;
  }
}
:root[data-theme="dark"]{
  --ink:#070A14; --ground:#0B1020; --surface:#151B2E; --surface-2:#1D2440;
  --line:#2A3352; --text:#E8EBF2; --muted:#98A1BB; --faint:#6B7493;
  --garnet:#E0407F; --blue:#6C97FF; --gold:#EDBB4B;
  --tier1:#37B87C; --tier2:#84C24E; --tier3:#EDBB4B; --tier4:#E08A54; --tier5:#D2544B;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--text);
  font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;
  font-size:15px; line-height:1.5;
}
.mono{font-family:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums}
.lbl{font-family:ui-monospace,"SF Mono",Menlo,monospace; font-size:10px;
  letter-spacing:.13em; text-transform:uppercase; color:var(--faint)}

header{
  display:flex; align-items:baseline; gap:16px; flex-wrap:wrap;
  padding:14px 20px; border-bottom:1px solid var(--line); background:var(--surface);
  position:sticky; top:0; z-index:5;
}
header h1{
  margin:0; font-size:17px; font-weight:800; letter-spacing:-.02em;
}
header h1 span{color:var(--garnet)}
.count{margin-left:auto}

.wrap{display:grid; grid-template-columns:320px minmax(0,1fr); min-height:calc(100vh - 52px)}
@media(max-width:860px){.wrap{grid-template-columns:1fr}
  aside{max-height:38vh; border-right:0; border-bottom:1px solid var(--line)}}

aside{border-right:1px solid var(--line); background:var(--surface);
  display:flex; flex-direction:column; overflow:hidden}
.controls{padding:12px; display:flex; flex-direction:column; gap:8px;
  border-bottom:1px solid var(--line)}
input,select{
  width:100%; padding:8px 10px; background:var(--ground); color:var(--text);
  border:1px solid var(--line); border-radius:4px; font:inherit; font-size:13px;
}
input:focus,select:focus{outline:2px solid var(--blue); outline-offset:1px}
.filters{display:flex; gap:8px}
.roster{overflow-y:auto; flex:1}
.row{
  display:grid; grid-template-columns:1fr auto auto; gap:8px; align-items:center;
  padding:7px 12px; cursor:pointer; border-bottom:1px solid var(--line);
  border-left:3px solid transparent;
}
.row:hover{background:var(--surface-2)}
.row[aria-current="true"]{background:var(--surface-2); border-left-color:var(--garnet)}
.row b{font-weight:600; font-size:13.5px; display:block; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis}
.row small{color:var(--faint); font-size:11px}
.ovr{font-size:12px; font-weight:700; padding:1px 6px; border-radius:3px;
  background:var(--surface-2); border:1px solid var(--line)}

main{padding:22px; overflow-x:hidden}
.empty{color:var(--muted); padding:40px; text-align:center}

.card-head{display:flex; gap:20px; flex-wrap:wrap; align-items:flex-start;
  padding-bottom:16px; border-bottom:2px solid var(--garnet)}
.name{font-size:30px; font-weight:800; letter-spacing:-.025em; margin:0;
  text-wrap:balance; line-height:1.1}
.sub{color:var(--muted); font-size:13.5px; margin-top:3px}
.money{margin-left:auto; text-align:right; display:flex; gap:22px}
.money div{display:flex; flex-direction:column; gap:2px}
.money .v{font-size:19px; font-weight:700}
.money .v.g{color:var(--garnet)}

.chips{display:flex; flex-wrap:wrap; gap:6px; margin:14px 0 0}
.chip{font-size:11px; padding:3px 9px; border-radius:99px; border:1px solid var(--line);
  background:var(--surface); color:var(--muted)}
.chip.on{border-color:var(--gold); color:var(--gold)}

h2.sec{font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--faint); margin:26px 0 10px; font-family:ui-monospace,Menlo,monospace;
  font-weight:600; display:flex; align-items:center; gap:10px}
h2.sec::after{content:""; flex:1; height:1px; background:var(--line)}

.grid{display:grid; gap:16px}
.g3{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.panel{background:var(--surface); border:1px solid var(--line); border-radius:6px;
  padding:13px 15px}
.panel h3{margin:0 0 9px; font-size:11px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--faint); font-family:ui-monospace,Menlo,monospace; font-weight:600}

.attr{display:flex; justify-content:space-between; align-items:center; gap:10px;
  padding:2.5px 0; font-size:13px}
.attr span:first-child{color:var(--muted)}
.val{font-weight:700; font-size:13px; min-width:26px; text-align:right;
  font-family:ui-monospace,Menlo,monospace}

.bars{display:flex; flex-direction:column; gap:7px}
.bar{display:grid; grid-template-columns:160px 1fr 38px; gap:10px; align-items:center;
  font-size:12.5px}
.bar .track{height:8px; background:var(--surface-2); border-radius:99px;
  overflow:hidden; border:1px solid var(--line)}
.bar .fill{height:100%; border-radius:99px}
.bar .pc{text-align:right; font-family:ui-monospace,Menlo,monospace; font-weight:700;
  font-size:12px}
.bar .nm{color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis}

.tbl-wrap{overflow-x:auto}
table{border-collapse:collapse; width:100%; font-size:13px; min-width:520px}
th{font-family:ui-monospace,Menlo,monospace; font-size:10px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--faint); text-align:right; font-weight:600;
  padding:6px 9px; border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
td{padding:6px 9px; border-bottom:1px solid var(--line);
  font-family:ui-monospace,Menlo,monospace; font-variant-numeric:tabular-nums;
  text-align:right}
tbody tr:last-child td{border-bottom:0}
.kv{display:grid; grid-template-columns:1fr auto; gap:3px 12px; font-size:12.5px}
.kv span:nth-child(odd){color:var(--muted)}
.kv span:nth-child(even){font-family:ui-monospace,Menlo,monospace; font-weight:600}
footer{padding:18px 22px; color:var(--faint); font-size:11.5px; border-top:1px solid var(--line)}
@media(prefers-reduced-motion:no-preference){.fill{transition:width .35s ease}}
</style>

<header>
  <h1>Blaugrana <span>Scout Room</span></h1>
  <span class="lbl">Top-5 leagues &middot; 2024/25 &amp; 2025/26</span>
  <span class="lbl count" id="count"></span>
</header>

<div class="wrap">
  <aside>
    <div class="controls">
      <input id="q" type="search" placeholder="Search player or club..." aria-label="Search players">
      <div class="filters">
        <select id="pos" aria-label="Position"><option value="">All positions</option>
          <option>FW</option><option>MF</option><option>DF</option><option>GK</option></select>
        <select id="lg" aria-label="League"><option value="">All leagues</option></select>
      </div>
    </div>
    <div class="roster" id="roster"></div>
  </aside>
  <main id="card"><p class="empty">Select a player.</p></main>
</div>

<footer>
  Machine-readable companion: <b>player_seasons.csv</b> (flat, one row per
  player-season) and <b>players.json</b> (nested). Percentiles are ranked within
  position group across the top-5 leagues. Attribute ratings are EA/SoFIFA
  scouted estimates, not measured; match data is FBref, Understat and SofaScore.
</footer>

<script id="DATA" type="application/json">__DATA__</script>
<script id="LABELS" type="application/json">__LABELS__</script>
<script>
const P = JSON.parse(document.getElementById('DATA').textContent);
const PCTL = JSON.parse(document.getElementById('LABELS').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const eur = v => v==null ? '—' : (v>=1e6 ? '€'+(v/1e6).toFixed(0)+'M' : '€'+(v/1e3).toFixed(0)+'K');

// FM-style tiering: the subject's own visual language for attribute quality
const tier = v => v>=85?'var(--tier1)':v>=75?'var(--tier2)':v>=65?'var(--tier3)':v>=55?'var(--tier4)':'var(--tier5)';
const pctColor = v => v>=80?'var(--tier1)':v>=60?'var(--tier2)':v>=40?'var(--tier3)':v>=20?'var(--tier4)':'var(--tier5)';

const lgs=[...new Set(P.map(p=>p.league))].sort();
$('#lg').insertAdjacentHTML('beforeend', lgs.map(l=>`<option>${esc(l)}</option>`).join(''));

let list=P, sel=null;
function filter(){
  const q=$('#q').value.trim().toLowerCase(), pos=$('#pos').value, lg=$('#lg').value;
  list = P.filter(p =>
    (!q || p.player.toLowerCase().includes(q) || (p.team||'').toLowerCase().includes(q)) &&
    (!pos || p.pos_group===pos) && (!lg || p.league===lg));
  $('#count').textContent = list.length+' of '+P.length+' players';
  $('#roster').innerHTML = list.slice(0,400).map((p,i)=>`
    <div class="row" data-i="${P.indexOf(p)}" role="button" tabindex="0"
         aria-current="${sel===P.indexOf(p)}">
      <span><b>${esc(p.player)}</b><small>${esc(p.team||'')}</small></span>
      <small class="mono">${esc(p.position||'')}</small>
      <span class="ovr mono">${p.identity.overall??'—'}</span>
    </div>`).join('');
}
function attrPanel(title, obj){
  const rows=Object.entries(obj||{}).map(([k,v])=>`
    <div class="attr"><span>${esc(k.replace(/_/g,' '))}</span>
      <span class="val" style="color:${tier(v)}">${v}</span></div>`).join('');
  return rows ? `<div class="panel"><h3>${title}</h3>${rows}</div>` : '';
}
function render(i){
  sel=i; const p=P[i], id=p.identity;
  const styles=(id.playstyles||'').split(/\\s{2,}|\\u2003/).filter(Boolean);
  const bars=PCTL.filter(([k])=>p.percentiles[k]!=null).map(([k,lab])=>{
    const v=p.percentiles[k];
    return `<div class="bar"><span class="nm">${lab}</span>
      <span class="track"><span class="fill" style="width:${v}%;background:${pctColor(v)}"></span></span>
      <span class="pc" style="color:${pctColor(v)}">${v}</span></div>`;}).join('');
  const rows=p.seasons.map(s=>`<tr><td>${esc(s.season)}</td><td>${esc(s.team||'')}</td>
      <td>${s.nineties??'—'}</td><td>${s.goals??'—'}</td><td>${s.assists??'—'}</td>
      <td>${s.xg??'—'}</td><td>${s.npxg??'—'}</td><td>${s.xa??'—'}</td>
      <td>${s.xg_chain??'—'}</td><td>${s.shots??'—'}</td></tr>`).join('');
  const last=p.seasons[p.seasons.length-1];
  const kv=o=>Object.entries(o||{}).map(([k,v])=>
    `<span>${esc(k.replace(/_/g,' '))}</span><span>${v}</span>`).join('');
  $('#card').innerHTML=`
    <div class="card-head">
      <div>
        <h1 class="name">${esc(p.player)}</h1>
        <div class="sub">${esc(p.team||'')} &middot; ${esc(p.league||'')} &middot;
          ${esc(p.position||'')}${id.best_position?' ('+esc(id.best_position)+' best)':''}
          &middot; age ${id.age??'—'}${id.height?' &middot; '+esc(id.height):''}${id.foot?' &middot; '+esc(id.foot)+' footed':''}</div>
      </div>
      <div class="money">
        <div><span class="lbl">Value</span><span class="v g">${eur(id.value_eur)}</span></div>
        <div><span class="lbl">Release</span><span class="v">${eur(id.release_clause_eur)}</span></div>
        <div><span class="lbl">Contract</span><span class="v">${id.contract_end??'—'}</span></div>
        <div><span class="lbl">OVR / POT</span><span class="v">${id.overall??'—'} / ${id.potential??'—'}</span></div>
      </div>
    </div>
    ${styles.length?`<div class="chips">${styles.map(s=>`<span class="chip on">${esc(s)}</span>`).join('')}</div>`:''}

    <h2 class="sec">Percentile rank vs ${esc(p.pos_group)} in top-5 leagues</h2>
    <div class="panel bars">${bars||'<span class="lbl">no ranked sample</span>'}</div>

    <h2 class="sec">Attributes &mdash; EA scouted ratings</h2>
    <div class="grid g3">
      ${attrPanel('Technical',p.attributes.technical)}
      ${attrPanel('Mental',p.attributes.mental)}
      ${attrPanel('Physical',p.attributes.physical)}
    </div>

    <h2 class="sec">Match output &mdash; actually played</h2>
    <div class="panel tbl-wrap"><table><thead><tr>
      <th>Season</th><th>Club</th><th>90s</th><th>G</th><th>A</th><th>xG</th>
      <th>npxG</th><th>xA</th><th>xGChain</th><th>Shots</th></tr></thead>
      <tbody>${rows}</tbody></table></div>

    <h2 class="sec">Detail &mdash; ${esc(last.season)}</h2>
    <div class="grid g3">
      <div class="panel"><h3>On the ball</h3><div class="kv">${kv(last.on_ball)}</div></div>
      <div class="panel"><h3>Defensive &amp; pressing</h3><div class="kv">${kv(last.defensive)}</div></div>
    </div>`;
  filter();
  document.querySelector('main').scrollTo({top:0});
}
$('#roster').addEventListener('click',e=>{const r=e.target.closest('.row'); if(r) render(+r.dataset.i);});
$('#roster').addEventListener('keydown',e=>{
  if(e.key==='Enter'||e.key===' '){const r=e.target.closest('.row'); if(r){e.preventDefault(); render(+r.dataset.i);}}});
['#q','#pos','#lg'].forEach(s=>$(s).addEventListener('input',filter));
filter();
render(P.findIndex(p=>p.player.includes('Pedri'))>=0?P.findIndex(p=>p.player.includes('Pedri')):0);
</script>
"""

out = HTML.replace('__DATA__', data).replace('__LABELS__', labels)
with open('output/player_cards.html', 'w', encoding='utf-8') as f:
    f.write(out)
import os
print('%d players -> output/player_cards.html (%.1f MB)'
      % (len(CARDS), os.path.getsize('output/player_cards.html') / 1e6))
