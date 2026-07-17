#!/usr/bin/env python3
"""Web demo for the /search/stream SSE endpoint.

Serves a single-page app on DEMO_PORT (default 7200) that streams
node-level progress from the research graph in real time.
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

API_URL = os.environ.get("API_URL", "http://localhost:7100")
DEMO_PORT = int(os.environ.get("DEMO_PORT", "7200"))

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deep Research</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f6f8fa;--bg2:#ffffff;--bg3:#eef1f5;--border:#d0d7de;
  --text:#1f2328;--muted:#656d76;--blue:#0969da;--green:#1a7f37;
  --yellow:#9a6700;--purple:#8250df;--red:#cf222e;
  --mono:"JetBrains Mono","Fira Code","Cascadia Code",monospace;
}}
body{{
  background:var(--bg);color:var(--text);
  font-family:system-ui,-apple-system,sans-serif;
  font-size:14px;line-height:1.6;
  height:100vh;display:flex;flex-direction:column;
}}

/* ── header ── */
header{{
  border-bottom:1px solid var(--border);padding:12px 24px;
  display:flex;align-items:center;gap:10px;flex-shrink:0;
}}
header h1{{font-size:15px;font-weight:600}}
header .dot{{width:8px;height:8px;border-radius:50%;background:var(--blue)}}

/* ── layout ── */
.layout{{
  flex:1;display:grid;grid-template-columns:2fr 8fr;
  gap:20px;padding:20px;overflow:hidden;
}}
.left{{display:flex;flex-direction:column;gap:14px;overflow:hidden;min-width:0}}
.right{{overflow-y:auto;min-width:0;padding-right:4px}}

/* ── form ── */
.form-card{{
  background:var(--bg2);border:1px solid var(--border);border-radius:8px;
  padding:14px;display:flex;flex-direction:column;gap:10px;flex-shrink:0;
}}
.field{{display:flex;flex-direction:column;gap:4px}}
.field label,.sf label{{
  font-size:11px;color:var(--muted);font-weight:500;
  text-transform:uppercase;letter-spacing:.04em;
}}
input[type=text]{{
  background:var(--bg3);border:1px solid var(--border);border-radius:5px;
  color:var(--text);font-size:13px;padding:7px 10px;width:100%;outline:none;
}}
input[type=text]:focus{{border-color:var(--blue)}}
.sf{{display:flex;flex-direction:column;gap:3px}}
.sf label{{display:flex;justify-content:space-between}}
.sf label span{{color:var(--blue)}}
input[type=range]{{width:100%;accent-color:var(--blue);cursor:pointer}}
#search-btn{{
  background:var(--blue);color:#000;border:none;border-radius:5px;
  font-size:13px;font-weight:600;padding:8px 16px;cursor:pointer;width:100%;
}}
#search-btn:hover{{opacity:.85}}
#search-btn:disabled{{opacity:.4;cursor:not-allowed}}

/* ── log ── */
.log-card{{
  flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:8px;
  display:flex;flex-direction:column;overflow:hidden;min-height:0;
}}
.log-hdr{{
  padding:8px 12px;border-bottom:1px solid var(--border);
  font-size:11px;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em;flex-shrink:0;
}}
#log{{
  flex:1;overflow-y:auto;padding:6px 0;
  font-family:var(--mono);font-size:11px;line-height:1.5;
}}

/* node row */
.nr{{
  display:flex;align-items:center;gap:5px;
  padding:2px 10px;min-height:22px;
  animation:fi .12s ease;
}}
@keyframes fi{{from{{opacity:0;transform:translateY(2px)}}to{{opacity:1;transform:none}}}}
.ns{{
  width:12px;height:12px;flex-shrink:0;
  display:flex;align-items:center;justify-content:center;font-size:9px;
}}
.ns.run::after{{
  content:'';display:block;width:8px;height:8px;
  border:1.5px solid var(--border);border-top-color:var(--blue);
  border-radius:50%;animation:sp .6s linear infinite;
}}
@keyframes sp{{to{{transform:rotate(360deg)}}}}
.ns.ok::after{{content:'\\2713';color:var(--green)}}
.ns.err::after{{content:'\\2717';color:var(--red)}}
.nn{{color:var(--muted);white-space:nowrap;font-size:11px}}
.nd{{
  color:var(--text);font-size:10.5px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}}
.nd em{{color:var(--yellow);font-style:normal}}

/* subgraph group */
.sg{{margin:3px 0}}
.sg-hdr{{
  display:flex;align-items:center;gap:5px;
  padding:3px 10px;min-height:22px;
}}
.tt{{
  background:#f3f0ff;color:var(--purple);
  font-size:10px;padding:1px 6px;border-radius:3px;
  max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}}
.sg-body{{
  margin-left:6px;padding-left:8px;border-left:2px solid var(--border);
}}

.log-empty{{
  padding:20px 12px;color:var(--muted);text-align:center;font-size:11px;
}}

/* ── right panel ── */
.rp-state{{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  height:100%;color:var(--muted);gap:14px;font-size:13px;
}}
.sp-lg{{
  width:28px;height:28px;
  border:3px solid var(--border);border-top-color:var(--blue);
  border-radius:50%;animation:sp .8s linear infinite;
}}

/* results */
.topics-row{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}}
.topic-chip{{
  background:#f3f0ff;color:var(--purple);font-size:12px;
  padding:4px 10px;border-radius:12px;border:1px solid #d4c9f7;
}}
.papers-grid{{display:flex;flex-direction:column;gap:10px}}
.paper-card{{
  background:var(--bg2);border:1px solid var(--border);border-radius:8px;
  padding:14px 16px;display:grid;grid-template-columns:44px 1fr;gap:12px;
  transition:border-color .15s;
}}
.paper-card:hover{{border-color:var(--blue)}}
.p-rank{{font-size:13px;font-weight:700;color:var(--muted);text-align:right}}
.p-score{{font-size:10px;color:var(--yellow);font-family:var(--mono);text-align:right;margin-top:2px}}
.p-title{{font-size:14px;font-weight:600;margin-bottom:3px}}
.p-title a{{color:inherit;text-decoration:none}}
.p-title a:hover{{color:var(--blue)}}
.p-meta{{font-size:12px;color:var(--muted);margin-bottom:4px}}
.p-summary{{
  font-size:12.5px;color:var(--muted);line-height:1.5;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
</style>
</head>
<body>

<header>
  <div class="dot"></div>
  <h1>Deep Research</h1>
</header>

<main class="layout">
  <!-- Left: form + execution log -->
  <div class="left">
    <div class="form-card">
      <div class="field">
        <label>Query</label>
        <input type="text" id="query" placeholder="e.g. retrieval augmented generation" value="retrieval augmented generation">
      </div>
      <div class="sf">
        <label>Topics <span id="v-topics">3</span></label>
        <input type="range" id="num_topics" min="1" max="6" value="3"
               oninput="document.getElementById('v-topics').textContent=this.value">
      </div>
      <div class="sf">
        <label>Attempts <span id="v-attempts">2</span></label>
        <input type="range" id="max_attempts" min="1" max="5" value="2"
               oninput="document.getElementById('v-attempts').textContent=this.value">
      </div>
      <div class="sf">
        <label>Top K <span id="v-topk">10</span></label>
        <input type="range" id="top_k" min="1" max="20" value="10"
               oninput="document.getElementById('v-topk').textContent=this.value">
      </div>
      <button id="search-btn" onclick="runSearch()">Search</button>
    </div>

    <div class="log-card">
      <div class="log-hdr">Execution</div>
      <div id="log">
        <div class="log-empty">Run a search to see execution.</div>
      </div>
    </div>
  </div>

  <!-- Right: loading / results -->
  <div class="right">
    <div id="idle" class="rp-state">Run a search to see results.</div>
    <div id="loading" class="rp-state" style="display:none">
      <div class="sp-lg"></div>
      Searching...
    </div>
    <div id="results" style="display:none">
      <div id="topics-row" class="topics-row"></div>
      <div id="papers-grid" class="papers-grid"></div>
    </div>
  </div>
</main>

<script>
const API_URL = '{API_URL}';
const SUB = new Set(['generate_query','search','judge','generate_feedback','emit']);

/* ── helpers ── */
function esc(s) {{
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}}
function scrollLog() {{
  const el = document.getElementById('log');
  el.scrollTop = el.scrollHeight;
}}

/* ── state ── */
const sgs = new Map();   // topic -> {{ el, hdr, body, nodes: Map }}
const mains = new Map(); // node  -> el

/* ── dom builders ── */
function mkRow(name) {{
  const r = document.createElement('div');
  r.className = 'nr';
  r.innerHTML =
    '<span class="ns"></span>' +
    `<span class="nn">${{esc(name)}}</span>` +
    '<span class="nd"></span>';
  return r;
}}
function setRun(el) {{
  el.querySelector('.ns').className = 'ns run';
  el.querySelector('.nd').innerHTML = '';
}}
function setOk(el, html) {{
  el.querySelector('.ns').className = 'ns ok';
  if (html) el.querySelector('.nd').innerHTML = html;
}}
function setErr(el, msg) {{
  el.querySelector('.ns').className = 'ns err';
  el.querySelector('.nd').textContent = msg;
}}

/* ── get-or-create ── */
function mainNode(node) {{
  if (mains.has(node)) return mains.get(node);
  const r = mkRow(node);
  document.getElementById('log').appendChild(r);
  mains.set(node, r);
  return r;
}}
function sgGroup(topic) {{
  if (sgs.has(topic)) return sgs.get(topic);
  const el = document.createElement('div');
  el.className = 'sg';
  const hdr = document.createElement('div');
  hdr.className = 'sg-hdr';
  hdr.innerHTML =
    '<span class="ns run"></span>' +
    `<span class="tt">${{esc(topic)}}</span>` +
    '<span class="nd"></span>';
  const body = document.createElement('div');
  body.className = 'sg-body';
  el.appendChild(hdr);
  el.appendChild(body);
  document.getElementById('log').appendChild(el);
  const o = {{ el, hdr, body, nodes: new Map() }};
  sgs.set(topic, o);
  return o;
}}
function subNode(topic, node) {{
  const g = sgGroup(topic);
  if (g.nodes.has(node)) return g.nodes.get(node);
  const r = mkRow(node);
  g.body.appendChild(r);
  g.nodes.set(node, r);
  return r;
}}

/* ── event handlers ── */
function onStart(d) {{
  const {{ node, topic }} = d;
  if (node === 'search_subgraph') {{
    sgGroup(topic);
  }} else if (SUB.has(node) && topic) {{
    setRun(subNode(topic, node));
  }} else {{
    setRun(mainNode(node));
  }}
  scrollLog();
}}

function onEnd(d) {{
  const {{ node, topic }} = d;
  let dt = '';

  if (node === 'generate_topics') {{
    dt = (d.topics || []).map(t => `<em>${{esc(t)}}</em>`).join(', ');
  }} else if (node === 'generate_query') {{
    dt = `<em>${{esc(d.search_query || '')}}</em>`;
  }} else if (node === 'search') {{
    dt = `<em>${{d.papers_found ?? 0}}</em> papers`;
  }} else if (node === 'judge') {{
    dt = `<em>${{d.papers_relevant ?? 0}}</em> relevant`;
  }} else if (node === 'generate_feedback') {{
    const fb = (d.feedback || '').slice(0, 60);
    dt = esc(fb) + (d.feedback && d.feedback.length > 60 ? '...' : '');
  }} else if (node === 'emit') {{
    dt = 'done';
  }} else if (node === 'search_subgraph') {{
    dt = `<em>${{d.papers_emitted ?? 0}}</em> papers`;
  }} else if (node === 'collect_and_rank') {{
    dt = `<em>${{d.papers_count ?? 0}}</em> papers`;
  }}

  if (node === 'search_subgraph') {{
    const g = sgGroup(topic);
    setOk(g.hdr, dt);
  }} else if (SUB.has(node) && topic) {{
    setOk(subNode(topic, node), dt);
  }} else {{
    setOk(mainNode(node), dt);
  }}
  scrollLog();
}}

/* ── right panel ── */
function rpState(s) {{
  document.getElementById('idle').style.display    = s === 'idle'    ? 'flex'  : 'none';
  document.getElementById('loading').style.display = s === 'loading' ? 'flex'  : 'none';
  document.getElementById('results').style.display = s === 'results' ? 'block' : 'none';
}}

function showResults(data) {{
  const topics = data.topics || [];
  const papers = data.papers || [];

  const tr = document.getElementById('topics-row');
  tr.innerHTML = '';
  topics.forEach(t => {{
    const c = document.createElement('span');
    c.className = 'topic-chip';
    c.textContent = t;
    tr.appendChild(c);
  }});

  const gr = document.getElementById('papers-grid');
  gr.innerHTML = '';
  papers.forEach((p, i) => {{
    const id = p.id || '';
    const url = id ? `https://huggingface.co/papers/${{id}}` : '#';
    const score = (p.relevance_score || 0).toFixed(2);
    const authors = (p.authors || []).slice(0, 3).join(', ');
    const summary = (p.summary || '').slice(0, 220);
    const card = document.createElement('div');
    card.className = 'paper-card';
    card.innerHTML = `
      <div>
        <div class="p-rank">${{i + 1}}</div>
        <div class="p-score">${{score}}</div>
      </div>
      <div>
        <div class="p-title"><a href="${{url}}" target="_blank">${{esc(p.title || 'Untitled')}}</a></div>
        ${{authors ? `<div class="p-meta">${{esc(authors)}}</div>` : ''}}
        ${{summary ? `<div class="p-summary">${{esc(summary)}}${{p.summary && p.summary.length > 220 ? '...' : ''}}</div>` : ''}}
      </div>`;
    gr.appendChild(card);
  }});
  rpState('results');
}}

/* ── search ── */
function clearAll() {{
  document.getElementById('log').innerHTML = '';
  sgs.clear();
  mains.clear();
}}

async function runSearch() {{
  const query = document.getElementById('query').value.trim();
  if (!query) return;

  const payload = {{
    query,
    num_topics: +document.getElementById('num_topics').value,
    max_attempts: +document.getElementById('max_attempts').value,
    top_k: +document.getElementById('top_k').value,
  }};

  clearAll();
  rpState('loading');
  document.getElementById('search-btn').disabled = true;

  try {{
    const resp = await fetch(`${{API_URL}}/search/stream`, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(payload),
    }});
    if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = '', et = null;

    while (true) {{
      const {{ done, value }} = await reader.read();
      if (done) break;
      buf += dec.decode(value, {{ stream: true }});
      const lines = buf.split('\\n');
      buf = lines.pop() ?? '';
      for (const ln of lines) {{
        if (ln.startsWith('event: ')) {{
          et = ln.slice(7).trim();
        }} else if (ln.startsWith('data: ')) {{
          let d;
          try {{ d = JSON.parse(ln.slice(6)); }} catch {{ continue; }}
          if (et === 'node_start')      onStart(d);
          else if (et === 'node_end')   onEnd(d);
          else if (et === 'done')       showResults(d);
          else if (et === 'error') {{
            const r = mainNode('error');
            setErr(r, d.error || 'Unknown error');
            rpState('idle');
          }}
        }} else if (ln === '') {{
          et = null;
        }}
      }}
    }}
  }} catch (err) {{
    const r = mainNode('error');
    setErr(r, err.message);
    rpState('idle');
  }} finally {{
    document.getElementById('search-btn').disabled = false;
  }}
}}

document.getElementById('query').addEventListener('keydown', e => {{
  if (e.key === 'Enter') runSearch();
}});
</script>
</body>
</html>
"""

# ── HTTP server ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", DEMO_PORT), Handler)
    print(f"Demo:  http://localhost:{DEMO_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
