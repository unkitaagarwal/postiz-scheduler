#!/usr/bin/env python3
"""
Postiz Bulk Scheduler
=====================
Run:   python3 postiz_scheduler.py
Then:  Browser opens automatically at http://localhost:8080

No third-party packages required — uses only Python's standard library.
"""

import json
import urllib.request
import urllib.error
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

POSTIZ_API = "https://api.postiz.com/public/v1"
PORT = 8080

# ─────────────────────────────────────────────────────────────────────────────
#  Embedded single-page HTML app
# ─────────────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Postiz Bulk Scheduler</title>
<style>
:root {
  --bg:      #0d0f18;
  --card:    #161926;
  --card2:   #1e2235;
  --border:  #2a2f47;
  --accent:  #7c6af7;
  --accentH: #9489f8;
  --text:    #dde1f5;
  --muted:   #7278a0;
  --success: #52c98b;
  --error:   #f06a8a;
  --warn:    #f0b96a;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  padding-bottom: 80px;
}
.container { max-width: 980px; margin: 0 auto; padding: 36px 24px; }

/* ── Typography ── */
h1  { font-size: 24px; font-weight: 700; letter-spacing: -0.4px; }
.subtitle { color: var(--muted); font-size: 14px; margin-top: 4px; }
.section-label {
  font-size: 10px; font-weight: 700; color: var(--muted);
  text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 12px;
}

/* ── Cards ── */
.card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px; margin-top: 22px;
}

/* ── Buttons ── */
.btn {
  display: inline-flex; align-items: center; gap: 7px;
  background: var(--accent); color: #fff; border: none;
  border-radius: 9px; padding: 10px 18px; font-size: 14px;
  font-weight: 600; cursor: pointer; transition: background .15s, transform .1s;
  white-space: nowrap; font-family: inherit;
}
.btn:hover { background: var(--accentH); }
.btn:active { transform: scale(.97); }
.btn:disabled { opacity: .45; cursor: not-allowed; transform: none; }
.btn-sm { padding: 7px 13px; font-size: 12px; border-radius: 7px; }
.btn-outline {
  background: transparent; border: 1px solid var(--border); color: var(--text);
}
.btn-outline:hover { background: var(--card2); border-color: var(--accent); }
.btn-success { background: var(--success); }
.btn-success:hover { background: #40b87a; }
.btn-danger  { background: transparent; border: 1px solid var(--error); color: var(--error); }
.btn-danger:hover  { background: rgba(240,106,138,.12); }
.link { color: var(--accent); text-decoration: none; font-size: 13px; }
.link:hover { text-decoration: underline; }

/* ── API key row ── */
.key-row { display: flex; gap: 10px; }
.key-input {
  flex: 1; background: var(--card2); border: 1px solid var(--border);
  border-radius: 9px; color: var(--text); font-size: 14px;
  padding: 10px 14px; outline: none; font-family: monospace;
  transition: border-color .2s;
}
.key-input:focus { border-color: var(--accent); }

/* ── Integrations ── */
.int-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.int-chip {
  display: flex; align-items: center; gap: 9px;
  background: var(--card2); border: 1px solid var(--border);
  border-radius: 9px; padding: 8px 13px; font-size: 13px;
}
.int-chip img { width: 26px; height: 26px; border-radius: 50%; object-fit: cover; }
.int-chip .pi { font-size: 18px; width: 26px; text-align: center; line-height: 1; }
.int-name { font-weight: 600; line-height: 1.2; }
.int-platform { font-size: 11px; color: var(--muted); margin-top: 1px; }

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed var(--border); border-radius: 12px;
  padding: 52px 20px; text-align: center; cursor: pointer;
  background: var(--card2); transition: border-color .2s, background .2s;
}
.drop-zone:hover, .drop-zone.drag-over {
  border-color: var(--accent); background: rgba(124,106,247,.07);
}
.dz-icon { font-size: 44px; display: block; margin-bottom: 14px; }
.drop-zone strong { font-size: 16px; }
.drop-zone p { color: var(--muted); font-size: 13px; margin-top: 6px; }

/* ── Queue header ── */
.queue-header {
  display: flex; align-items: center; justify-content: space-between;
  margin: 30px 0 16px;
}
.queue-title { font-size: 17px; font-weight: 700; }
.q-badge {
  background: var(--accent); color: #fff; border-radius: 20px;
  padding: 2px 9px; font-size: 12px; font-weight: 700; margin-left: 8px;
}
.queue-actions { display: flex; gap: 10px; }

/* ── Progress ── */
.progress-wrap { margin-bottom: 18px; }
.progress-row {
  display: flex; justify-content: space-between;
  font-size: 13px; color: var(--muted); margin-bottom: 7px;
}
.progress-track {
  background: var(--card2); border-radius: 4px; height: 5px; overflow: hidden;
}
.progress-fill {
  height: 100%; background: var(--accent); border-radius: 4px; transition: width .35s;
}

/* ── Post card ── */
.post-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 13px; padding: 18px; margin-bottom: 13px;
  transition: border-color .2s;
}
.post-card.st-done      { border-color: var(--success); }
.post-card.st-error     { border-color: var(--error); }
.post-card.st-uploading,
.post-card.st-scheduling { border-color: var(--accent); }

.card-top { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 16px; }
.thumb {
  width: 74px; height: 74px; border-radius: 9px; flex-shrink: 0;
  background: var(--card2); overflow: hidden;
  display: flex; align-items: center; justify-content: center; font-size: 28px;
}
.thumb video, .thumb img { width: 100%; height: 100%; object-fit: cover; }
.post-info { flex: 1; min-width: 0; }
.post-fname {
  font-weight: 600; font-size: 14px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.post-fsize { color: var(--muted); font-size: 12px; margin-top: 3px; }
.post-status-row { margin-top: 8px; }

.card-body { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 620px) { .card-body { grid-template-columns: 1fr; } }

.field-label {
  font-size: 10px; font-weight: 700; color: var(--muted);
  text-transform: uppercase; letter-spacing: .8px; margin-bottom: 7px;
}
.caption-ta {
  width: 100%; background: var(--card2); border: 1px solid var(--border);
  border-radius: 9px; color: var(--text); font-size: 13px;
  padding: 10px 13px; resize: vertical; min-height: 80px;
  outline: none; font-family: inherit; transition: border-color .2s; line-height: 1.5;
}
.caption-ta:focus { border-color: var(--accent); }
.dt-input {
  width: 100%; background: var(--card2); border: 1px solid var(--border);
  border-radius: 9px; color: var(--text); font-size: 13px;
  padding: 10px 13px; outline: none; appearance: none;
  cursor: pointer; transition: border-color .2s; font-family: inherit;
}
.dt-input:focus { border-color: var(--accent); }

/* ── Account chips (per-post) ── */
.acc-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.acc-chip {
  display: flex; align-items: center; gap: 6px;
  border: 1px solid var(--border); border-radius: 7px;
  padding: 5px 11px; font-size: 12px; cursor: pointer;
  background: var(--card2); user-select: none; transition: all .15s;
}
.acc-chip.selected {
  border-color: var(--accent); background: rgba(124,106,247,.14); color: var(--accent);
}
.acc-chip:hover:not(.selected) { border-color: var(--muted); }
.acc-chip img { width: 16px; height: 16px; border-radius: 50%; }
.acc-chip .spi { font-size: 14px; width: 16px; text-align: center; line-height: 1; }

/* ── Status badges ── */
.badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
}
.badge-pending    { background: rgba(114,120,160,.18); color: var(--muted); }
.badge-uploading  { background: rgba(124,106,247,.18); color: var(--accent); }
.badge-scheduling { background: rgba(240,185,106,.18); color: var(--warn); }
.badge-done       { background: rgba(82,201,139,.18);  color: var(--success); }
.badge-error      { background: rgba(240,106,138,.18); color: var(--error); }

/* ── Spinner ── */
.spin {
  width: 11px; height: 11px; border: 2px solid rgba(255,255,255,.25);
  border-top-color: currentColor; border-radius: 50%;
  animation: rot .65s linear infinite; flex-shrink: 0;
}
@keyframes rot { to { transform: rotate(360deg); } }

/* ── Toast ── */
.toast-wrap {
  position: fixed; bottom: 24px; right: 24px; z-index: 9999;
  display: flex; flex-direction: column; gap: 8px; pointer-events: none;
}
.toast {
  background: var(--card); border: 1px solid var(--border); border-radius: 11px;
  padding: 12px 16px; font-size: 13px; min-width: 240px; max-width: 360px;
  box-shadow: 0 10px 36px rgba(0,0,0,.5); pointer-events: auto;
  display: flex; align-items: center; gap: 10px;
  animation: tIn .28s ease both;
}
.toast.ok   { border-color: var(--success); }
.toast.fail { border-color: var(--error); }
@keyframes tIn  { from { transform: translateX(110%); opacity: 0; } }
@keyframes tOut { to   { transform: translateX(110%); opacity: 0; } }
.toast.bye { animation: tOut .28s ease forwards; }

/* ── Slideshow strip ── */
.slide-strip {
  display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px;
}
.slide-thumb {
  width: 52px; height: 52px; border-radius: 6px; object-fit: cover;
  border: 1px solid var(--border); flex-shrink: 0;
}
.slide-count {
  display: flex; align-items: center; justify-content: center;
  width: 52px; height: 52px; border-radius: 6px;
  background: var(--card2); border: 1px dashed var(--border);
  font-size: 12px; color: var(--muted); flex-shrink: 0;
}

/* ── Utility ── */
.hidden { display: none !important; }
.row { display: flex; align-items: center; gap: 10px; }
.spacer { flex: 1; }
</style>
</head>
<body>
<div class="container">

  <!-- ── Header ── -->
  <div style="display:flex;align-items:center;gap:14px;margin-bottom:30px">
    <span style="font-size:36px">🚀</span>
    <div>
      <h1>Postiz Bulk Scheduler</h1>
      <p class="subtitle">Upload videos &amp; images · Schedule to Instagram, TikTok, YouTube &amp; more</p>
    </div>
  </div>

  <!-- ── API Key ── -->
  <div class="card" id="apiCard">
    <div class="section-label">Postiz API Key</div>
    <div class="key-row">
      <input class="key-input" id="keyInput" type="password"
             placeholder="Paste your API key here…">
      <button class="btn" id="connectBtn" onclick="connect()">Connect</button>
    </div>
    <div style="margin-top:10px;font-size:12px;color:var(--muted)">
      Find it at
      <a class="link" href="https://platform.postiz.com/settings" target="_blank">
        platform.postiz.com → Settings → API Key
      </a>
      &nbsp;·&nbsp; Saved locally in your browser.
    </div>
  </div>

  <!-- ── Connected Accounts ── -->
  <div class="card hidden" id="intCard">
    <div class="row" style="margin-bottom:14px">
      <div class="section-label" style="margin:0">Connected Accounts</div>
      <div class="spacer"></div>
      <button class="btn btn-outline btn-sm" onclick="loadIntegrations()">↻ Refresh</button>
    </div>
    <div class="int-grid" id="intGrid">
      <span style="color:var(--muted);font-size:13px">Loading…</span>
    </div>
  </div>

  <!-- ── Drop Zone ── -->
  <div class="card hidden" id="dropCard">
    <div class="section-label">Add Files</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">

      <!-- Individual videos/images -->
      <div class="drop-zone" id="dropZone"
           onclick="document.getElementById('fileInput').click()">
        <span class="dz-icon">🎬</span>
        <strong>Videos &amp; Images</strong>
        <p>One post per file</p>
        <p style="margin-top:8px;font-size:11px;color:var(--muted)">MP4 · MOV · JPG · PNG</p>
      </div>

      <!-- Slideshow / carousel -->
      <div class="drop-zone" id="slideshowZone"
           onclick="document.getElementById('slideshowInput').click()"
           style="border-color: #7c6af755;">
        <span class="dz-icon">🖼️</span>
        <strong>Slideshow / Carousel</strong>
        <p>Select multiple images → one post</p>
        <p style="margin-top:8px;font-size:11px;color:var(--muted)">JPG · PNG · GIF</p>
      </div>
    </div>
    <input type="file" id="fileInput"      multiple accept="video/*,image/*" style="display:none">
    <input type="file" id="slideshowInput" multiple accept="image/*"         style="display:none">
  </div>

  <!-- ── Post Queue ── -->
  <div id="queueWrap" class="hidden">
    <div class="queue-header">
      <div>
        <span class="queue-title">Post Queue</span>
        <span class="q-badge" id="qBadge">0</span>
      </div>
      <div class="queue-actions">
        <button class="btn btn-outline btn-sm" onclick="clearQueue()">Clear All</button>
        <button class="btn btn-success" id="schedBtn" onclick="scheduleAll()">
          🚀 Schedule All
        </button>
      </div>
    </div>

    <!-- batch progress -->
    <div class="progress-wrap hidden" id="batchProgress">
      <div class="progress-row">
        <span id="progLabel">Scheduling…</span>
        <span id="progFrac">0 / 0</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" id="progFill" style="width:0%"></div>
      </div>
    </div>

    <div id="postList"></div>
  </div>
</div>

<!-- ── Toasts ── -->
<div class="toast-wrap" id="toasts"></div>

<script>
// ────────────────────────── State ──────────────────────────────────────────
const S = {
  apiKey:       localStorage.getItem("postiz_key") || "",
  integrations: [],
  posts:        [],   // see addFiles() for shape
  busy:         false
};

const ICONS = {
  instagram:"📷", tiktok:"🎵", youtube:"▶️", twitter:"🐦",
  linkedin:"💼", facebook:"📘", threads:"🧵", pinterest:"📌",
  bluesky:"🦋", reddit:"🤖", default:"📱"
};
const COLORS = {
  instagram:"#e1306c", tiktok:"#69c9d0", youtube:"#ff0000",
  twitter:"#1da1f2",   linkedin:"#0a66c2", facebook:"#1877f2",
  threads:"#aaa",      pinterest:"#e60023", bluesky:"#0085ff",
  reddit:"#ff4500",    default:"#7c6af7"
};

// ────────────────────────── Boot ───────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  if (S.apiKey) {
    document.getElementById("keyInput").value = S.apiKey;
    connect();
  }
  initDrop();
});

// ────────────────────────── API helpers ────────────────────────────────────
async function api(method, path, body, isForm) {
  const headers = { Authorization: S.apiKey };
  if (!isForm) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined
  });
  if (!res.ok) {
    const t = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${t.slice(0, 200)}`);
  }
  return res.json();
}

// ────────────────────────── Connect ────────────────────────────────────────
async function connect() {
  const key = document.getElementById("keyInput").value.trim();
  if (!key) { toast("Enter your API key first", "fail"); return; }
  S.apiKey = key;
  localStorage.setItem("postiz_key", key);

  const btn = document.getElementById("connectBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span> Connecting…`;

  try {
    await loadIntegrations();
    document.getElementById("intCard").classList.remove("hidden");
    document.getElementById("dropCard").classList.remove("hidden");
    toast(`Connected — ${S.integrations.length} account(s) found`, "ok");
    btn.textContent = "Reconnect";
  } catch (e) {
    toast("Connection failed: " + e.message, "fail");
    btn.textContent = "Connect";
  }
  btn.disabled = false;
}

async function loadIntegrations() {
  const data = await api("GET", "/integrations");
  S.integrations = Array.isArray(data)
    ? data
    : (data.integrations || data.data || data.results || []);
  renderInts();
  // refresh account chips in any open post cards
  S.posts && renderQueue();
}

// ────────────────────────── Render integrations ────────────────────────────
function renderInts() {
  const g = document.getElementById("intGrid");
  if (!S.integrations.length) {
    g.innerHTML = `<span style="color:var(--muted);font-size:13px">
      No accounts found — connect social accounts on platform.postiz.com first.</span>`;
    return;
  }
  g.innerHTML = S.integrations.map(i => {
    const pl = platform(i);
    const ic = ICONS[pl] || ICONS.default;
    const col = COLORS[pl] || COLORS.default;
    return `<div class="int-chip">
      ${i.picture
        ? `<img src="${i.picture}" onerror="this.style.display='none';this.nextElementSibling.style.display='inline'">`
        : ""}
      <span class="pi" style="${i.picture ? "display:none" : ""}">${ic}</span>
      <div>
        <div class="int-name">${esc(i.name || i.identifier || "Account")}</div>
        <div class="int-platform" style="color:${col}" title="identifier: ${esc(i.identifier||'')} | type: ${esc(i.type||'')} | provider: ${esc(i.provider||'')}">${pl || "(unknown)"}</div>
      </div>
    </div>`;
  }).join("");
}

function platform(i) {
  return ((i.identifier || i.type || i.provider || "")).toLowerCase();
}

// Detect whether a video has an audio track using the browser media API.
// Returns true = has audio, false = silent/no audio track.
// Falls back to true (assume audio) when the API is unavailable (e.g. Firefox).
async function videoHasAudio(objectUrl) {
  return new Promise(resolve => {
    const v = document.createElement("video");
    v.preload = "metadata";
    v.src = objectUrl;
    const finish = r => { v.src = ""; resolve(r); };
    v.onloadedmetadata = () => {
      if (v.audioTracks) finish(v.audioTracks.length > 0); // Chrome/Edge
      else               finish(true);  // can't tell → assume audio present
    };
    v.onerror = () => finish(false);
    setTimeout(() => finish(true), 4000); // safety fallback
  });
}

// Build platform-specific settings.
// needsMusic = true when the file is an image/slideshow OR a silent video —
// in those cases TikTok should add background music automatically.
function buildSettings(intId, title, needsMusic = false) {
  const int  = S.integrations.find(i => i.id === intId);
  const pl   = int ? platform(int) : "";
  const base = { title: (title || "").slice(0, 100) };

  // Use includes() so partial identifiers like "instagram-reel",
  // "instagram-business", "tiktok-business", etc. all match correctly.
  console.log(`[buildSettings] intId=${intId} platform="${pl}"`);

  let extra = {};

  if (pl.includes("tiktok")) {
    extra = {
      privacy_level:        "PUBLIC_TO_EVERYONE",
      duet:                 false,
      stitch:                 false,
      comment:                true,
      autoAddMusic:           needsMusic ? "yes" : "no",
      brand_content_toggle:   false,
      brand_organic_toggle:   false,
      content_posting_method: "DIRECT_POST"
    };
  } else if (pl.includes("youtube")) {
    extra = { type: "public" };
  } else if (pl.includes("linkedin")) {
    extra = { privacy_level: "PUBLIC" };
  } else if (pl.includes("instagram")) {
    extra = { content_posting_method: "DIRECT_POST" };
  } else if (pl.includes("facebook")) {
    extra = {};
  }
  // twitter / threads / bluesky / pinterest → base title only

  return { ...base, ...extra };
}

// ────────────────────────── Drop zone ──────────────────────────────────────
function initDrop() {
  // ── Regular files (one post per file) ──
  const zone = document.getElementById("dropZone");
  const inp  = document.getElementById("fileInput");
  zone.addEventListener("dragover",  e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", ()=> zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("drag-over");
    addFiles([...e.dataTransfer.files]);
  });
  inp.addEventListener("change", () => { addFiles([...inp.files]); inp.value = ""; });

  // ── Slideshow zone (all selected images → one carousel post) ──
  const szOne  = document.getElementById("slideshowZone");
  const szInp  = document.getElementById("slideshowInput");
  szOne.addEventListener("dragover",  e => { e.preventDefault(); szOne.classList.add("drag-over"); });
  szOne.addEventListener("dragleave", ()=> szOne.classList.remove("drag-over"));
  szOne.addEventListener("drop", e => {
    e.preventDefault(); szOne.classList.remove("drag-over");
    addSlideshow([...e.dataTransfer.files]);
  });
  szInp.addEventListener("change", () => { addSlideshow([...szInp.files]); szInp.value = ""; });
}

// ────────────────────────── Add slideshow (carousel) ───────────────────────
function addSlideshow(files) {
  const images = files.filter(f => f.type.startsWith("image/"));
  if (!images.length) { toast("Select image files for a slideshow", "fail"); return; }
  if (images.length < 2) { toast("Pick at least 2 images for a slideshow", "fail"); return; }

  // Sort by filename so numbered slides (01_, 02_, …) stay in order
  images.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

  S.posts.push({
    id:         `p${Date.now()}${Math.random().toString(36).slice(2)}`,
    slideshow:  true,                          // ← marks this as a carousel post
    files:      images,
    urls:       images.map(f => URL.createObjectURL(f)),
    caption:    "",
    accounts:   S.integrations.map(i => i.id),
    when:       defaultDT(),
    status:     "pending",
    err:        null
  });

  renderQueue();
  toast(`Added slideshow with ${images.length} slides`, "ok");
}

function addFiles(files) {
  const valid = files.filter(f => f.type.startsWith("video/") || f.type.startsWith("image/"));
  if (!valid.length) { toast("No valid video or image files", "fail"); return; }

  valid.forEach(f => {
    S.posts.push({
      id:       `p${Date.now()}${Math.random().toString(36).slice(2)}`,
      file:     f,
      url:      URL.createObjectURL(f),
      caption:  "",
      accounts: S.integrations.map(i => i.id),   // all selected by default
      when:     defaultDT(),
      status:   "pending",  // pending|uploading|scheduling|done|error
      err:      null
    });
  });

  renderQueue();
  toast(`Added ${valid.length} file(s) to queue`, "ok");
}

function defaultDT() {
  const d = new Date();
  d.setHours(d.getHours() + 1, 0, 0, 0);
  return d.toISOString().slice(0, 16);
}

// ────────────────────────── Render queue ───────────────────────────────────
function renderQueue() {
  const wrap = document.getElementById("queueWrap");
  const list = document.getElementById("postList");

  if (!S.posts.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  document.getElementById("qBadge").textContent = S.posts.length;

  list.innerHTML = S.posts.map(p => cardHTML(p)).join("");

  // Wire events
  S.posts.forEach(p => {
    // Caption
    byId(`cap-${p.id}`)?.addEventListener("input", e => { p.caption = e.target.value; });
    // Datetime
    byId(`dt-${p.id}`)?.addEventListener("change", e => { p.when = e.target.value; });
    // Remove button
    byId(`rm-${p.id}`)?.addEventListener("click", () => removePost(p.id));
    // Account chips
    S.integrations.forEach(i => {
      byId(`chip-${p.id}-${i.id}`)?.addEventListener("click", () => toggleAcc(p, i.id));
    });
  });
}

function toggleAcc(post, intId) {
  const idx = post.accounts.indexOf(intId);
  if (idx === -1) post.accounts.push(intId);
  else            post.accounts.splice(idx, 1);
  byId(`chip-${post.id}-${intId}`)?.classList.toggle("selected");
}

function accChipsHTML(p) {
  return S.integrations.map(i => {
    const pl  = platform(i);
    const ic  = ICONS[pl] || ICONS.default;
    const sel = p.accounts.includes(i.id);
    const nm  = (i.name || i.identifier || "Account").slice(0, 14);
    return `<div class="acc-chip ${sel ? "selected" : ""}" id="chip-${p.id}-${i.id}">
      ${i.picture
        ? `<img src="${i.picture}" onerror="this.style.display='none';this.nextElementSibling.style.display='inline'">
           <span class="spi" style="display:none">${ic}</span>`
        : `<span class="spi">${ic}</span>`}
      ${esc(nm)}
    </div>`;
  }).join("");
}

function cardHTML(p) {
  const editable = p.status === "pending" || p.status === "error";
  const stClass  = { pending:"", uploading:"st-uploading",
                     scheduling:"st-scheduling", done:"st-done", error:"st-error" }[p.status] || "";

  // ── Slideshow card ───────────────────────────────────────────────────────
  if (p.slideshow) {
    const MAX_PREVIEW = 6;
    const thumbs = p.urls.slice(0, MAX_PREVIEW).map((u, i) =>
      `<img class="slide-thumb" src="${u}" title="${esc(p.files[i].name)}">`
    ).join("");
    const extra = p.urls.length > MAX_PREVIEW
      ? `<div class="slide-count">+${p.urls.length - MAX_PREVIEW}</div>` : "";
    const totalSize = p.files.reduce((s, f) => s + f.size, 0);

    return `
<div class="post-card ${stClass}" id="pc-${p.id}">
  <div class="card-top">
    <div class="thumb" style="font-size:22px">🖼️×${p.files.length}</div>
    <div class="post-info">
      <div class="post-fname">Slideshow — ${p.files.length} slides</div>
      <div class="post-fsize">🖼️ ${fmtBytes(totalSize)} total · sorted by filename</div>
      <div class="post-status-row" id="sr-${p.id}">${badgeHTML(p)}</div>
      ${p.err ? `<div style="font-size:12px;color:var(--error);margin-top:4px">⚠ ${esc(p.err)}</div>` : ""}
    </div>
    ${editable ? `<button class="btn btn-danger btn-sm" id="rm-${p.id}" title="Remove">✕</button>` : ""}
  </div>
  <div class="slide-strip">${thumbs}${extra}</div>
  ${editable ? `
  <div class="card-body" style="margin-top:14px">
    <div>
      <div class="field-label">Caption</div>
      <textarea class="caption-ta" id="cap-${p.id}" placeholder="Write your caption…">${esc(p.caption)}</textarea>
    </div>
    <div>
      <div class="field-label">Schedule Date &amp; Time</div>
      <input class="dt-input" type="datetime-local" id="dt-${p.id}"
             value="${p.when}" min="${new Date().toISOString().slice(0,16)}">
      <div class="field-label" style="margin-top:14px">Post To</div>
      <div class="acc-grid">${accChipsHTML(p)}</div>
    </div>
  </div>` : `
  <div style="font-size:13px;color:var(--muted);margin-top:6px">
    📅 ${fmtDate(p.when)} &nbsp;·&nbsp; ${p.accounts.length} account(s)
  </div>`}
</div>`;
  }

  // ── Regular (single file) card ───────────────────────────────────────────
  const isVideo = p.file.type.startsWith("video/");
  return `
<div class="post-card ${stClass}" id="pc-${p.id}">
  <div class="card-top">
    <div class="thumb">
      ${isVideo
        ? `<video src="${p.url}" muted playsinline preload="metadata"></video>`
        : `<img src="${p.url}" alt="">`}
    </div>
    <div class="post-info">
      <div class="post-fname" title="${esc(p.file.name)}">${esc(p.file.name)}</div>
      <div class="post-fsize">${isVideo ? "🎬" : "🖼️"} ${fmtBytes(p.file.size)}</div>
      <div class="post-status-row" id="sr-${p.id}">${badgeHTML(p)}</div>
      ${p.err ? `<div style="font-size:12px;color:var(--error);margin-top:4px">⚠ ${esc(p.err)}</div>` : ""}
    </div>
    ${editable ? `<button class="btn btn-danger btn-sm" id="rm-${p.id}" title="Remove">✕</button>` : ""}
  </div>
  ${editable ? `
  <div class="card-body">
    <div>
      <div class="field-label">Caption</div>
      <textarea class="caption-ta" id="cap-${p.id}" placeholder="Write your caption…">${esc(p.caption)}</textarea>
    </div>
    <div>
      <div class="field-label">Schedule Date &amp; Time</div>
      <input class="dt-input" type="datetime-local" id="dt-${p.id}"
             value="${p.when}" min="${new Date().toISOString().slice(0,16)}">
      <div class="field-label" style="margin-top:14px">Post To</div>
      <div class="acc-grid">${accChipsHTML(p)}</div>
    </div>
  </div>` : `
  <div style="font-size:13px;color:var(--muted);margin-top:4px">
    📅 ${fmtDate(p.when)} &nbsp;·&nbsp; ${p.accounts.length} account(s)
  </div>`}
</div>`;
}

function badgeHTML(p) {
  const map = {
    pending:    `<span class="badge badge-pending">⏳ Ready to schedule</span>`,
    uploading:  `<span class="badge badge-uploading"><span class="spin"></span> Uploading…</span>`,
    scheduling: `<span class="badge badge-scheduling"><span class="spin"></span> Scheduling…</span>`,
    done:       `<span class="badge badge-done">✓ Scheduled</span>`,
    error:      `<span class="badge badge-error">✕ Failed</span>`,
  };
  return map[p.status] || map.pending;
}

// ────────────────────────── Queue actions ──────────────────────────────────
function removePost(id) {
  const p = S.posts.find(x => x.id === id);
  if (p) {
    if (p.slideshow) p.urls?.forEach(u => URL.revokeObjectURL(u));
    else if (p.url)  URL.revokeObjectURL(p.url);
  }
  S.posts = S.posts.filter(x => x.id !== id);
  renderQueue();
}

function clearQueue() {
  if (S.busy) { toast("Wait for current batch to finish", "fail"); return; }
  if (!confirm("Clear all posts from the queue?")) return;
  S.posts.forEach(p => {
    if (p.slideshow) p.urls?.forEach(u => URL.revokeObjectURL(u));
    else if (p.url)  URL.revokeObjectURL(p.url);
  });
  S.posts = [];
  renderQueue();
}

// ────────────────────────── Schedule all ───────────────────────────────────
async function scheduleAll() {
  if (S.busy) return;

  const pending = S.posts.filter(p => p.status === "pending" || p.status === "error");
  if (!pending.length) { toast("No pending posts to schedule", "fail"); return; }

  // Validate
  for (const p of pending) {
    const label = p.slideshow ? `Slideshow (${p.files.length} slides)` : p.file.name;
    if (!p.accounts.length) { toast(`Select at least one account for: ${label}`, "fail"); return; }
    if (!p.when)             { toast(`Set a date/time for: ${label}`, "fail"); return; }
    if (new Date(p.when) <= new Date()) { toast(`Schedule time must be in the future: ${label}`, "fail"); return; }
  }

  S.busy = true;
  const btn = document.getElementById("schedBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span> Scheduling…`;

  const prog   = document.getElementById("batchProgress");
  const fill   = document.getElementById("progFill");
  const label  = document.getElementById("progLabel");
  const frac   = document.getElementById("progFrac");
  prog.classList.remove("hidden");

  let done = 0;
  const total = pending.length;

  for (const p of pending) {
    frac.textContent  = `${done} / ${total}`;
    fill.style.width  = `${(done / total) * 100}%`;
    const postLabel = p.slideshow ? `Slideshow (${p.files.length} slides)` : p.file.name;
    label.textContent = `Uploading: ${postLabel}`;

    try {
      const MAX_MB = 100;
      setStatus(p, "uploading");
      let mediaItems = [];  // [{id, path}, …] — one per file

      if (p.slideshow) {
        // Upload each slide individually, collect all IDs
        for (let i = 0; i < p.files.length; i++) {
          label.textContent = `Uploading slide ${i + 1}/${p.files.length}…`;
          const fd = new FormData();
          fd.append("file", p.files[i]);
          const up = await api("POST", "/upload", fd, true);
          mediaItems.push({ id: up.id, path: up.path });
        }
      } else {
        if (p.file.size > MAX_MB * 1024 * 1024) {
          throw new Error(`File is ${fmtBytes(p.file.size)} — Postiz rejects uploads over ${MAX_MB} MB. Please compress the video first.`);
        }
        const fd = new FormData();
        fd.append("file", p.file);
        const up = await api("POST", "/upload", fd, true);
        mediaItems.push({ id: up.id, path: up.path });
      }

      label.textContent = `Scheduling: ${postLabel}`;
      setStatus(p, "scheduling");

      const title = (p.caption || (p.slideshow ? "Slideshow" : p.file.name)).slice(0, 100);
      const needsMusic = p.slideshow
        ? true  // slideshows have no original audio
        : (p.file.type.startsWith("image/") || !(await videoHasAudio(p.url)));

      await api("POST", "/posts", {
        type: "schedule",
        date: new Date(p.when).toISOString(),
        shortLink: false,
        tags: [],
        posts: p.accounts.map(intId => ({
          integration: { id: intId },
          value: [{
            content: p.caption,
            image:   mediaItems   // multiple items = carousel/slideshow
          }],
          settings: buildSettings(intId, title, needsMusic)
        }))
      });

      setStatus(p, "done");
      done++;
      toast(`✓ Scheduled: ${postLabel}`, "ok");

    } catch (e) {
      p.err = e.message;
      setStatus(p, "error");
      toast(`Failed: ${postLabel}`, "fail");
    }

    renderQueue();
  }

  frac.textContent  = `${done} / ${total}`;
  fill.style.width  = "100%";
  label.textContent = done === total ? "✓ All posts scheduled!" : `Done — ${done}/${total} succeeded`;

  S.busy = false;
  btn.disabled = false;
  btn.textContent = "🚀 Schedule All";
  setTimeout(() => prog.classList.add("hidden"), 4000);

  toast(
    done === total
      ? `All ${done} post(s) scheduled successfully!`
      : `${done}/${total} posts scheduled (${total - done} failed)`,
    done === total ? "ok" : "fail"
  );
}

function setStatus(p, st) {
  p.status = st;
  const sr = byId(`sr-${p.id}`);
  if (sr) sr.innerHTML = badgeHTML(p);
  const card = byId(`pc-${p.id}`);
  if (card) {
    card.className = `post-card ${{
      uploading:"st-uploading", scheduling:"st-scheduling",
      done:"st-done", error:"st-error"
    }[st] || ""}`;
  }
}

// ────────────────────────── Utilities ──────────────────────────────────────
function esc(s) {
  return String(s ?? "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function byId(id) { return document.getElementById(id); }
function fmtBytes(b) {
  if (b < 1024)     return b + " B";
  if (b < 1048576)  return (b/1024).toFixed(1) + " KB";
  return (b/1048576).toFixed(1) + " MB";
}
function fmtDate(s) {
  if (!s) return "—";
  return new Date(s).toLocaleString(undefined, {
    month:"short", day:"numeric", year:"numeric",
    hour:"2-digit", minute:"2-digit"
  });
}

// ────────────────────────── Toasts ─────────────────────────────────────────
function toast(msg, type = "") {
  const wrap = document.getElementById("toasts");
  const el   = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span style="font-size:16px">${type==="ok"?"✓":type==="fail"?"✕":"ℹ"}</span>
                  <span>${esc(msg)}</span>`;
  wrap.appendChild(el);
  setTimeout(() => {
    el.classList.add("bye");
    setTimeout(() => el.remove(), 300);
  }, 3800);
}

// Expose for inline onclick
window.connect         = connect;
window.loadIntegrations= loadIntegrations;
window.scheduleAll     = scheduleAll;
window.clearQueue      = clearQueue;
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
#  HTTP request handler — serves the app + proxies Postiz API calls
# ─────────────────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    # ── CORS preflight ────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/api/integrations":
            self._proxy_get("/integrations")

        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    # ── POST ──────────────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path == "/api/upload":
            self._proxy_post("/upload")
        elif self.path == "/api/posts":
            self._proxy_post("/posts")
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    # ── Proxy helpers ─────────────────────────────────────────────────────────
    def _auth(self):
        return self.headers.get("Authorization", "")

    def _proxy_get(self, endpoint):
        try:
            req = urllib.request.Request(
                f"{POSTIZ_API}{endpoint}",
                headers={
                    "Authorization": self._auth(),
                    "Accept": "application/json",
                }
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
            # ── Debug: dump full integration objects to terminal ─────────────
            if endpoint == "/integrations":
                try:
                    data = json.loads(body)
                    items = data if isinstance(data, list) else data.get("integrations", data.get("data", data.get("results", [])))
                    print("\n  ══ RAW INTEGRATIONS ══════════════════════════════")
                    for i in items:
                        print(f"  {json.dumps(i, indent=4)}")
                    print("  ══════════════════════════════════════════════════\n")
                except Exception as ex:
                    print(f"  [debug error] {ex}")
                    print(f"  raw body: {body[:500]}")
            self._ok(body)
        except urllib.error.HTTPError as e:
            self._forward_error(e)
        except Exception as e:
            self._err(str(e))

    def _proxy_post(self, endpoint):
        try:
            length = int(self.headers.get("Content-Length", 0))
            ct     = self.headers.get("Content-Type", "application/json")
            body   = self.rfile.read(length) if length else self.rfile.read()

            # Retry up to 3 times on transient SSL / connection errors
            # (SSLV3_ALERT_BAD_RECORD_MAC often happens on consecutive uploads)
            last_exc = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(
                        f"{POSTIZ_API}{endpoint}",
                        data=body,
                        headers={
                            "Authorization": self._auth(),
                            "Content-Type":  ct,
                            "Accept":        "application/json",
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=120) as r:
                        resp_body = r.read()
                    self._ok(resp_body)
                    return
                except urllib.error.HTTPError:
                    raise   # pass HTTP errors straight through — no retry
                except Exception as exc:
                    last_exc = exc
                    if attempt < 2:
                        print(f"  [upload retry {attempt + 1}] {exc}")
                        time.sleep(2 ** attempt)   # 1s, 2s backoff
                    else:
                        raise last_exc

        except urllib.error.HTTPError as e:
            self._forward_error(e)
        except Exception as e:
            self._err(str(e))

    def _ok(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _forward_error(self, e: urllib.error.HTTPError):
        body = e.read()
        self.send_response(e.code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg: str):
        body = json.dumps({"error": msg}).encode()
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    # ── Logging ───────────────────────────────────────────────────────────────
    def log_message(self, fmt, *args):
        method, path, status = args[0], args[1], args[2] if len(args) > 2 else ""
        # Only log API calls, not the HTML page itself
        if "/api/" in path or str(status).startswith(("4", "5")):
            print(f"  {status}  {path}")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    url = f"http://localhost:{PORT}"

    # Open browser after a short delay so the server is ready
    def open_browser():
        time.sleep(0.9)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    print()
    print("  ╔══════════════════════════════════════════╗")
    print(f"  ║  🚀  Postiz Bulk Scheduler               ║")
    print(f"  ║                                          ║")
    print(f"  ║  Open:  {url:<33}║")
    print(f"  ║  Stop:  Ctrl + C                         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    server = HTTPServer(("localhost", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped. Bye!")


if __name__ == "__main__":
    main()