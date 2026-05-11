#!/usr/bin/env python3
"""
Postiz Bulk Scheduler
=====================
Run:   python3 postiz_scheduler.py
Then:  Browser opens automatically at http://localhost:8080

No third-party packages required — uses only Python's standard library.
"""

import json
import os
import mimetypes
import uuid
import urllib.request
import urllib.error
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

POSTIZ_API = "https://api.postiz.com/public/v1"
PORT = int(os.environ.get("PORT", 8080))

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
  cursor: pointer; user-select: none; transition: all .15s;
}
.int-chip:hover:not(.active) { border-color: var(--muted); }
.int-chip.active {
  border-color: var(--accent); background: rgba(124,106,247,.14);
}
.int-chip.active .int-name { color: var(--accent); }
.int-chip img { width: 26px; height: 26px; border-radius: 50%; object-fit: cover; }
.int-chip .pi { font-size: 18px; width: 26px; text-align: center; line-height: 1; }
.int-name { font-weight: 600; line-height: 1.2; transition: color .15s; }
.int-platform { font-size: 11px; color: var(--muted); margin-top: 1px; }
.int-check { font-size: 13px; margin-left: 2px; opacity: 0; transition: opacity .15s; }
.int-chip.active .int-check { opacity: 1; }

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed var(--border); border-radius: 12px;
  padding: 36px 20px 28px; text-align: center; cursor: pointer;
  background: var(--card2); transition: border-color .2s, background .2s;
  display: flex; flex-direction: column; align-items: center;
}
.drop-zone:hover, .drop-zone.drag-over {
  border-color: var(--accent); background: rgba(124,106,247,.07);
}
.dz-icon { font-size: 44px; display: block; margin-bottom: 14px; }
.drop-zone strong { font-size: 16px; }
.drop-zone p { color: var(--muted); font-size: 13px; margin-top: 6px; }
.dz-browse-btn {
  margin-top: 16px; display: inline-flex; align-items: center; gap: 6px;
  background: var(--card); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px 16px; font-size: 13px; font-weight: 600;
  color: var(--text); cursor: pointer; transition: background .15s, border-color .15s;
  font-family: inherit;
}
.dz-browse-btn:hover { background: var(--card2); border-color: var(--accent); color: var(--accent); }

/* ── Folder loader zone ── */
.folder-zone {
  border: 2px dashed #7c6af755; border-radius: 12px;
  padding: 28px 20px; background: var(--card2);
  display: flex; flex-direction: column; gap: 12px;
}
.folder-zone-title { font-size: 16px; font-weight: 700; }
.folder-zone-sub { color: var(--muted); font-size: 13px; margin-top: 2px; }
.folder-browse-big {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 16px 10px 10px;
}
.folder-browse-icon { font-size: 36px; }
.folder-browse-btn {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--accent); color: #fff; border: none;
  border-radius: 9px; padding: 10px 20px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background .15s; font-family: inherit;
}
.folder-browse-btn:hover { background: var(--accentH); }
.folder-browse-btn:disabled { opacity: .45; cursor: not-allowed; }
.folder-or-row {
  display: flex; align-items: center; gap: 10px;
  color: var(--muted); font-size: 12px;
}
.folder-or-row::before, .folder-or-row::after {
  content: ""; flex: 1; height: 1px; background: var(--border);
}
.folder-input-row { display: flex; gap: 10px; }
.folder-path-input {
  flex: 1; background: var(--bg); border: 1px solid var(--border);
  border-radius: 9px; color: var(--text); font-size: 13px;
  padding: 10px 14px; outline: none; font-family: monospace;
  transition: border-color .2s;
}
.folder-path-input:focus { border-color: var(--accent); }
.folder-hint {
  font-size: 11px; color: var(--muted); line-height: 1.6;
}
.folder-hint code {
  background: var(--bg); border-radius: 4px; padding: 1px 5px;
  font-family: monospace; color: var(--accent);
}

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

/* ── Auto-fill button ── */
.autofill-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(124,106,247,.15); border: 1px solid rgba(124,106,247,.35);
  color: var(--accent); border-radius: 7px;
  padding: 4px 10px; font-size: 11px; font-weight: 600;
  cursor: pointer; transition: background .15s, border-color .15s;
  font-family: inherit; white-space: nowrap;
}
.autofill-btn:hover { background: rgba(124,106,247,.28); border-color: var(--accent); }
.autofill-btn:disabled { opacity: .45; cursor: not-allowed; }

/* ── Skipped folders panel ── */
.skipped-panel {
  background: var(--card); border: 1px solid var(--error);
  border-radius: 13px; padding: 18px; margin-top: 14px;
}
.skipped-panel-title {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.skipped-panel-title strong { color: var(--error); font-size: 14px; }
.skipped-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
.skipped-table th {
  text-align: left; color: var(--muted); font-size: 10px;
  font-weight: 700; text-transform: uppercase; letter-spacing: .8px;
  padding: 0 8px 8px 0; border-bottom: 1px solid var(--border);
}
.skipped-table td {
  padding: 7px 8px 7px 0; border-bottom: 1px solid rgba(42,47,71,.5);
  vertical-align: middle;
}
.skipped-table tr:last-child td { border-bottom: none; }
.skipped-count-badge {
  display: inline-block; background: rgba(240,106,138,.15);
  color: var(--error); border-radius: 5px;
  padding: 2px 7px; font-size: 12px; font-weight: 700;
}
.skipped-name {
  font-family: monospace; font-size: 12px; color: var(--text);
  word-break: break-all;
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

  <!-- ── Anthropic API Key (for auto-caption) ── -->
  <div class="card" id="anthropicCard">
    <div class="section-label" style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
      ✨ Claude Auto-Caption &nbsp;<span style="background:rgba(124,106,247,.18);color:var(--accent);border-radius:5px;padding:1px 7px;font-size:10px;font-weight:700">Optional</span>
    </div>
    <div class="key-row">
      <input class="key-input" id="anthropicKeyInput" type="password"
             placeholder="sk-ant-… (Anthropic API key for ✨ Auto-fill captions)">
      <button class="btn btn-outline" id="saveAnthropicBtn" onclick="saveAnthropicKey()">Save</button>
    </div>
    <div style="margin-top:10px;font-size:12px;color:var(--muted)">
      Get a key at
      <a class="link" href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>
      &nbsp;·&nbsp; Used only locally to generate captions from your media.
    </div>
  </div>

  <!-- ── Connected Accounts / Channel Selector ── -->
  <div class="card hidden" id="intCard">
    <div class="row" style="margin-bottom:6px">
      <div class="section-label" style="margin:0">Post To — Select Channels</div>
      <div class="spacer"></div>
      <button class="btn btn-outline btn-sm" style="padding:5px 10px;font-size:11px"
              onclick="selectAllChannels()">Select All</button>
      <button class="btn btn-outline btn-sm" style="padding:5px 10px;font-size:11px"
              onclick="selectNoneChannels()">Deselect All</button>
      <button class="btn btn-outline btn-sm" onclick="loadIntegrations()">↻ Refresh</button>
    </div>
    <div style="font-size:12px;color:var(--muted);margin-bottom:12px">
      Click to toggle which channels new posts will be sent to. You can also adjust per-post below.
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
      <div class="drop-zone" id="dropZone">
        <span class="dz-icon">🎬</span>
        <strong>Videos &amp; Images</strong>
        <p>Drag &amp; drop files here</p>
        <p style="font-size:11px;color:var(--muted);margin-top:2px">MP4 · MOV · JPG · PNG</p>
        <div style="display:flex;gap:8px;margin-top:16px">
          <button class="dz-browse-btn" style="margin-top:0"
                  onclick="event.stopPropagation();document.getElementById('fileInput').click()">
            📄 Browse Files
          </button>
          <button class="dz-browse-btn" style="margin-top:0"
                  onclick="event.stopPropagation();document.getElementById('videoFolderInput').click()">
            📂 Browse Folder
          </button>
        </div>
      </div>

      <!-- Slideshow / carousel via folder picker -->
      <div class="folder-zone">
        <div>
          <div class="folder-zone-title">🖼️ Slideshow / Carousel</div>
          <div class="folder-zone-sub">Select a folder — one post with all slides</div>
        </div>
        <div class="folder-browse-big">
          <span class="folder-browse-icon">📂</span>
          <button class="folder-browse-btn" id="folderBrowseBtn"
                  onclick="document.getElementById('folderBrowseInput').click()">
            Choose Folder
          </button>
          <span style="font-size:12px;color:var(--muted)">
            Folder needs a <code style="background:var(--bg);padding:1px 5px;border-radius:4px;color:var(--accent);font-family:monospace">slides/</code> subfolder &amp; <code style="background:var(--bg);padding:1px 5px;border-radius:4px;color:var(--accent);font-family:monospace">.json</code> file
          </span>
        </div>
        <div class="folder-or-row">or paste path manually</div>
        <div class="folder-input-row">
          <input class="folder-path-input" id="folderInput"
                 placeholder="/Users/you/carousels/my_slideshow">
          <button class="btn btn-sm" id="loadFolderBtn" onclick="loadSlideshowFromFolder()"
                  style="padding:8px 14px;font-size:12px">Load</button>
        </div>
      </div>
    </div>
    <input type="file" id="fileInput"         multiple accept="video/*,image/*" style="display:none">
    <input type="file" id="videoFolderInput" webkitdirectory style="display:none">
    <input type="file" id="folderBrowseInput" webkitdirectory style="display:none">
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
  apiKey:          localStorage.getItem("postiz_key") || "",
  anthropicKey:    localStorage.getItem("anthropic_key") || "",
  integrations:    [],
  defaultAccounts: new Set(),   // which channels new posts should default to
  posts:           [],
  busy:            false
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
  if (S.anthropicKey) {
    document.getElementById("anthropicKeyInput").value = S.anthropicKey;
  }
  initDrop();
});

function saveAnthropicKey() {
  const key = document.getElementById("anthropicKeyInput").value.trim();
  S.anthropicKey = key;
  if (key) { localStorage.setItem("anthropic_key", key); toast("Anthropic key saved", "ok"); }
  else      { localStorage.removeItem("anthropic_key"); toast("Anthropic key cleared", "ok"); }
}

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

  // On first load, select ALL channels by default.
  // On refresh, keep existing selection but add any newly discovered channels.
  if (S.defaultAccounts.size === 0) {
    S.integrations.forEach(i => S.defaultAccounts.add(i.id));
  } else {
    S.integrations.forEach(i => {
      // auto-add brand-new integrations as selected
      if (!S.defaultAccounts.has(i.id) &&
          !S._knownIntegrationIds?.has(i.id)) {
        S.defaultAccounts.add(i.id);
      }
    });
  }
  // remember which IDs we've seen so far
  S._knownIntegrationIds = new Set(S.integrations.map(i => i.id));

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
    const pl  = platform(i);
    const ic  = ICONS[pl] || ICONS.default;
    const col = COLORS[pl] || COLORS.default;
    const sel = S.defaultAccounts.has(i.id);
    return `<div class="int-chip ${sel ? "active" : ""}" id="intchip-${i.id}"
                 onclick="toggleDefaultAcc('${i.id}')" title="Click to toggle channel">
      ${i.picture
        ? `<img src="${i.picture}" onerror="this.style.display='none';this.nextElementSibling.style.display='inline'">`
        : ""}
      <span class="pi" style="${i.picture ? "display:none" : ""}">${ic}</span>
      <div>
        <div class="int-name">${esc(i.name || i.identifier || "Account")}</div>
        <div class="int-platform" style="color:${col}"
             title="identifier: ${esc(i.identifier||'')} | type: ${esc(i.type||'')} | provider: ${esc(i.provider||'')}">${pl || "(unknown)"}</div>
      </div>
      <span class="int-check">✓</span>
    </div>`;
  }).join("");
}

// Propagate current defaultAccounts to every pending post and refresh their chips.
function syncPostsToDefault() {
  const ids = [...S.defaultAccounts];
  S.posts.forEach(p => {
    if (p.status !== "pending" && p.status !== "error") return;
    p.accounts = [...ids];
    // Refresh per-post chip visuals without a full re-render
    S.integrations.forEach(i => {
      const chip = document.getElementById(`chip-${p.id}-${i.id}`);
      if (chip) chip.classList.toggle("selected", ids.includes(i.id));
    });
  });
}

function toggleDefaultAcc(intId) {
  if (S.defaultAccounts.has(intId)) {
    S.defaultAccounts.delete(intId);
  } else {
    S.defaultAccounts.add(intId);
  }
  const chip = document.getElementById(`intchip-${intId}`);
  if (chip) chip.classList.toggle("active", S.defaultAccounts.has(intId));
  syncPostsToDefault();
  const count = S.defaultAccounts.size;
  toast(`${count} channel${count !== 1 ? "s" : ""} selected — all pending posts updated`, count ? "ok" : "");
}

function selectAllChannels() {
  S.integrations.forEach(i => {
    S.defaultAccounts.add(i.id);
    document.getElementById(`intchip-${i.id}`)?.classList.add("active");
  });
  syncPostsToDefault();
  toast(`All ${S.integrations.length} channels selected — all pending posts updated`, "ok");
}

function selectNoneChannels() {
  S.defaultAccounts.clear();
  S.integrations.forEach(i => {
    document.getElementById(`intchip-${i.id}`)?.classList.remove("active");
  });
  syncPostsToDefault();
  toast("All channels deselected — pending posts cleared too", "");
}

function platform(i) {
  return ((i.identifier || i.type || i.provider || "")).toLowerCase();
}

// Detect whether a video has an audio track using the browser media API.
async function videoHasAudio(objectUrl) {
  return new Promise(resolve => {
    const v = document.createElement("video");
    v.preload = "metadata";
    v.src = objectUrl;
    const finish = r => { v.src = ""; resolve(r); };
    v.onloadedmetadata = () => {
      if (v.audioTracks) finish(v.audioTracks.length > 0);
      else               finish(true);
    };
    v.onerror = () => finish(false);
    setTimeout(() => finish(true), 4000);
  });
}

// Build platform-specific settings.
// isCarousel = true when posting multiple images (slideshow)
function buildSettings(intId, title, needsMusic = false, isCarousel = false) {
  const int  = S.integrations.find(i => i.id === intId);
  const pl   = int ? platform(int) : "";
  const base = { title: (title || "").slice(0, 100) };

  console.log(`[buildSettings] intId=${intId} platform="${pl}" carousel=${isCarousel}`);

  let extra = {};

  if (pl.includes("tiktok")) {
    extra = {
      privacy_level:           "PUBLIC_TO_EVERYONE",
      duet:                    false,
      stitch:                  false,
      comment:                 true,
      autoAddMusic:            needsMusic ? "yes" : "no",
      brand_content_toggle:    false,
      brand_organic_toggle:    false,
      content_posting_method:  "DIRECT_POST"
    };
  } else if (pl.includes("youtube")) {
    extra = { type: "public" };
  } else if (pl.includes("linkedin")) {
    extra = { privacy_level: "PUBLIC" };
  } else if (pl.includes("instagram")) {
    // post_type: "post" covers both single images and carousels.
    // trial_reel must be false for image posts — if true, Instagram rejects
    // any non-video content and Postiz routes it through "standalone" incorrectly.
    extra = {
      post_type:   "post",
      trial_reel:  false
    };
  } else if (pl.includes("facebook")) {
    extra = {};
  }

  return { ...base, ...extra };
}

// ────────────────────────── Drop zone ──────────────────────────────────────
function initDrop() {
  // ── Video/image drop zone ──
  const zone = document.getElementById("dropZone");
  const inp  = document.getElementById("fileInput");
  zone.addEventListener("dragover",  e => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", ()=> zone.classList.remove("drag-over"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("drag-over");
    addFiles([...e.dataTransfer.files]);
  });
  // Click the whole zone (but not child buttons — they call directly)
  zone.addEventListener("click", e => {
    if (e.target === zone || e.target.tagName === "SPAN" || e.target.tagName === "STRONG" || e.target.tagName === "P") {
      document.getElementById("fileInput").click();
    }
  });
  inp.addEventListener("change", () => { addFiles([...inp.files]); inp.value = ""; });

  // ── Video folder browser (webkitdirectory) ──
  const videoFolderInput = document.getElementById("videoFolderInput");
  videoFolderInput.addEventListener("change", () => {
    handleVideoFolderBrowse(videoFolderInput);
  });

  // ── Slideshow folder browser (webkitdirectory) ──
  const folderBrowseInput = document.getElementById("folderBrowseInput");
  folderBrowseInput.addEventListener("change", () => {
    handleFolderBrowse(folderBrowseInput);
  });

  // Allow pressing Enter in the manual path input
  document.getElementById("folderInput")?.addEventListener("keydown", e => {
    if (e.key === "Enter") loadSlideshowFromFolder();
  });
}

// ────────────────────────── Handle video folder browse ──────────────────────
function handleVideoFolderBrowse(input) {
  const allFiles = [...input.files];
  input.value = "";
  if (!allFiles.length) return;

  const folderName = allFiles[0].webkitRelativePath.split("/")[0];

  // Accept any video or image file anywhere inside the folder (recursive)
  const valid = allFiles.filter(f =>
    f.type.startsWith("video/") || f.type.startsWith("image/")
  );

  // Reject oversized files early
  const MAX_MB = 100;
  const tooBig  = valid.filter(f => f.size > MAX_MB * 1024 * 1024);
  const ok      = valid.filter(f => f.size <= MAX_MB * 1024 * 1024);

  if (!ok.length) {
    toast(`No valid video/image files found in "${folderName}"`, "fail");
    return;
  }

  // Sort by full relative path so sibling folders come out grouped and ordered
  ok.sort((a, b) => a.webkitRelativePath.localeCompare(b.webkitRelativePath, undefined, { numeric: true }));

  const startStep = S.posts.filter(p => p.status === "pending").length;
  ok.forEach((f, idx) => {
    S.posts.push({
      id:       `p${Date.now()}${Math.random().toString(36).slice(2)}`,
      file:     f,
      url:      URL.createObjectURL(f),
      caption:  "",
      accounts: [...S.defaultAccounts],
      when:     staggeredDT(startStep + idx),
      status:   "pending",
      err:      null
    });
  });

  renderQueue();
  toast(`Added ${ok.length} file(s) from "${folderName}"`, "ok");

  if (tooBig.length) {
    toast(`Skipped ${tooBig.length} file(s) over ${MAX_MB} MB`, "fail");
  }
}

// ────────────────────────── Handle folder browse (webkitdirectory) ─────────
async function handleFolderBrowse(input) {
  const allFiles = [...input.files];
  input.value = "";
  if (!allFiles.length) return;

  const btn = document.getElementById("folderBrowseBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span> Reading…`;

  try {
    const IMAGE_RE = /\.(jpg|jpeg|png|gif|webp|avif)$/i;
    const rootName = allFiles[0].webkitRelativePath.split("/")[0];

    // ── Detect mode using actual path depths ─────────────────────────────────
    // Single:  root/slides/img.png           → parts[1]=="slides", length==3
    // Parent:  root/subfolder/slides/img.png → parts[2]=="slides", length==4
    const isSingle = allFiles.some(f => {
      const p = f.webkitRelativePath.split("/");
      return p.length === 3 && p[1].toLowerCase() === "slides" && IMAGE_RE.test(f.name);
    });

    if (isSingle) {
      // ── Single slideshow folder ──────────────────────────────────────────
      // JSON: root/name.json  (length 2)
      const jsonFile = allFiles.find(f => {
        const p = f.webkitRelativePath.split("/");
        return p.length === 2 && f.name.toLowerCase().endsWith(".json");
      });
      // Slides: root/slides/img.png  (length 3, parts[1]=="slides")
      let slides = allFiles.filter(f => {
        const p = f.webkitRelativePath.split("/");
        return p.length === 3 && p[1].toLowerCase() === "slides" && IMAGE_RE.test(f.name);
      });
      slides.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

      if (slides.length < 2) {
        toast(`Only ${slides.length} slide(s) found — need at least 2`, "fail"); return;
      }
      let meta = {};
      if (jsonFile) { try { meta = JSON.parse(await jsonFile.text()); } catch(e) {} }

      S.posts.push(makePostFromFiles(rootName, slides, meta, 0));
      renderQueue();
      toast(`Loaded "${rootName}": ${slides.length} slides`, "ok");

    } else {
      // ── Parent folder: extract per-subfolder directly from allFiles ──────
      // Group by the subfolder name (parts[1]), keeping ALL files regardless
      // of depth so we never accidentally exclude anything.
      const groups = {};
      for (const f of allFiles) {
        const p = f.webkitRelativePath.split("/");
        // p[0] = root (output_compilations), p[1] = subfolder name
        if (p.length >= 3) {
          const sub = p[1];
          (groups[sub] = groups[sub] || []).push(f);
        }
      }

      const subNames = Object.keys(groups).sort();
      if (!subNames.length) {
        toast("No subfolders found inside the selected folder", "fail");
        return;
      }

      console.log(`[folder] root="${rootName}" subfolders:`, subNames);

      let added = 0;
      const skippedList = [];  // [{name, count}, …]
      for (const subName of subNames) {
        const subFiles = groups[subName];

        // JSON: root/subName/file.json — any depth under subName, just find the .json
        const jsonFile = subFiles.find(f => {
          const p = f.webkitRelativePath.split("/");
          // Direct child: root/subName/name.json  → length 3
          return p.length === 3 && f.name.toLowerCase().endsWith(".json");
        });

        // Slides: root/subName/slides/img.* — look for ANY image file whose
        // grandparent folder is "slides" (p[2]=="slides"), regardless of exact depth
        let slides = subFiles.filter(f => {
          const p = f.webkitRelativePath.split("/");
          // p[0]=root  p[1]=subName  p[2]="slides"  p[3]=filename
          return p.length >= 4 && p[2].toLowerCase() === "slides" && IMAGE_RE.test(f.name);
        });
        slides.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));

        console.log(`[folder]   ${subName}: ${slides.length} slides, json=${!!jsonFile}`);

        if (slides.length < 2) {
          skippedList.push({ name: subName, count: slides.length });
          continue;
        }

        let meta = {};
        if (jsonFile) { try { meta = JSON.parse(await jsonFile.text()); } catch(e) { console.warn(e); } }

        S.posts.push(makePostFromFiles(subName, slides, meta, added));
        added++;
      }

      renderQueue();
      if (added) toast(`Queued ${added} slideshow(s) from "${rootName}"`, "ok");

      if (skippedList.length) {
        // Show a persistent panel listing every skipped folder with its slide count
        showSkippedPanel(skippedList);
      }
    }

  } catch (e) {
    toast("Failed to read folder: " + e.message, "fail");
  }

  btn.disabled = false;
  btn.innerHTML = "Choose Folder";
}

// ── Show a panel listing every folder that was skipped (< 2 slides) ──────────
function showSkippedPanel(list) {
  // Remove any previous skipped panel
  document.getElementById("skippedPanel")?.remove();

  const rows = list.map(({ name, count }) => `
    <tr>
      <td><span class="skipped-name">${esc(name)}</span></td>
      <td><span class="skipped-count-badge">${count} slide${count === 1 ? "" : "s"}</span></td>
      <td style="color:var(--muted);font-size:12px">
        ${count === 0 ? "No slides/ folder found" : "Below minimum (need ≥ 2)"}
      </td>
    </tr>`).join("");

  const panel = document.createElement("div");
  panel.id = "skippedPanel";
  panel.className = "skipped-panel";
  panel.innerHTML = `
    <div class="skipped-panel-title">
      <strong>⚠ ${list.length} folder${list.length > 1 ? "s" : ""} not queued — insufficient slides</strong>
      <button class="btn btn-outline btn-sm" onclick="document.getElementById('skippedPanel').remove()"
              style="padding:4px 10px;font-size:11px">Dismiss</button>
    </div>
    <table class="skipped-table">
      <thead>
        <tr>
          <th style="width:55%">Folder</th>
          <th>Slides found</th>
          <th>Reason</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;

  // Insert after the drop card
  const dropCard = document.getElementById("dropCard");
  dropCard.insertAdjacentElement("afterend", panel);
  panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ── Build a post object from real File objects ───────────────────────────────
function makePostFromFiles(folderName, slideFiles, metadata, stepIndex) {
  const captionParts = [];
  if (metadata?.hook_caption)    captionParts.push(metadata.hook_caption);
  if (metadata?.recipes?.length) captionParts.push(metadata.recipes.map(r => r.title).join("\n"));
  if (metadata?.cta_caption?.length) {
    captionParts.push(Array.isArray(metadata.cta_caption)
      ? metadata.cta_caption.join("\n") : metadata.cta_caption);
  }
  const when = staggeredDT(stepIndex);
  return {
    id:         `p${Date.now()}${Math.random().toString(36).slice(2)}`,
    slideshow:  true,
    fromFolder: false,
    folderPath: folderName,
    files:      slideFiles,
    urls:       slideFiles.map(f => URL.createObjectURL(f)),
    caption:    captionParts.join("\n\n").trim(),
    postTitle:  (metadata?.theme || "").slice(0, 100),
    accounts:   [...S.defaultAccounts],
    when,
    status:     "pending",
    err:        null
  };
}

// ────────────────────────── Load slideshow from folder (manual path) ────────
async function loadSlideshowFromFolder() {
  const folderPath = document.getElementById("folderInput").value.trim();
  if (!folderPath) { toast("Enter a folder path first", "fail"); return; }

  const btn = document.getElementById("loadFolderBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span>`;

  try {
    const res = await fetch(`/api/folder?path=${encodeURIComponent(folderPath)}`, {
      headers: { Authorization: S.apiKey }
    });
    if (!res.ok) {
      const t = await res.text().catch(() => res.statusText);
      throw new Error(t.slice(0, 200));
    }
    const data = await res.json();

    if (data.mode === "multi") {
      // ── Parent folder: multiple slideshows ──────────────────────────────
      const { slideshows, skipped: serverSkipped } = data;
      if (!slideshows?.length && !serverSkipped?.length)
        throw new Error("No slideshow subfolders found");

      let added = 0;
      for (const sw of slideshows || []) {
        const post = buildSlideshowPostFromPaths(
          sw.folderName, folderPath + "/" + sw.folderName, sw.slides, sw.metadata, added
        );
        S.posts.push(post);
        added++;
      }
      renderQueue();
      if (added) toast(`Queued ${added} slideshow(s) from folder`, "ok");

      // Show skipped panel if any subfolders didn't meet the criteria
      const skippedList = (serverSkipped || []).map(s => ({ name: s.folderName, count: s.slideCount }));
      if (skippedList.length) showSkippedPanel(skippedList);

    } else {
      // ── Single slideshow folder ──────────────────────────────────────────
      const { slides, metadata } = data;
      const folderName = folderPath.split("/").pop();
      if (!slides || slides.length < 2) {
        showSkippedPanel([{ name: folderName, count: slides?.length || 0 }]);
        throw new Error(`"${folderName}" has ${slides?.length || 0} slide(s) — need at least 2`);
      }
      S.posts.push(buildSlideshowPostFromPaths(folderName, folderPath, slides, metadata, 0));
      renderQueue();
      toast(`Loaded slideshow: ${slides.length} slides`, "ok");
    }

    document.getElementById("folderInput").value = "";

  } catch (e) {
    toast("Failed to load folder: " + e.message, "fail");
  }

  btn.disabled = false;
  btn.innerHTML = "Load";
}

// Helper: build a post object from server-returned disk paths
function buildSlideshowPostFromPaths(folderName, basePath, slides, metadata, stepIndex) {
  const captionParts = [];
  if (metadata?.hook_caption)    captionParts.push(metadata.hook_caption);
  if (metadata?.recipes?.length) captionParts.push(metadata.recipes.map(r => r.title).join("\n"));
  if (metadata?.cta_caption?.length) {
    captionParts.push(Array.isArray(metadata.cta_caption)
      ? metadata.cta_caption.join("\n") : metadata.cta_caption);
  }

  return {
    id:         `p${Date.now()}${Math.random().toString(36).slice(2)}`,
    slideshow:  true,
    fromFolder: true,
    folderPath: folderName,
    files:      slides,
    urls:       slides.map(s => `/api/file?path=${encodeURIComponent(s.path)}`),
    caption:    captionParts.join("\n\n").trim(),
    postTitle:  (metadata?.theme || "").slice(0, 100),
    accounts:   [...S.defaultAccounts],
    when:       staggeredDT(stepIndex),
    status:     "pending",
    err:        null
  };
}

function addFiles(files) {
  const valid = files.filter(f => f.type.startsWith("video/") || f.type.startsWith("image/"));
  if (!valid.length) { toast("No valid video or image files", "fail"); return; }

  const startStep = S.posts.filter(p => p.status === "pending").length;
  valid.forEach((f, idx) => {
    S.posts.push({
      id:       `p${Date.now()}${Math.random().toString(36).slice(2)}`,
      file:     f,
      url:      URL.createObjectURL(f),
      caption:  "",
      accounts: [...S.defaultAccounts],
      when:     staggeredDT(startStep + idx),
      status:   "pending",
      err:      null
    });
  });

  renderQueue();
  toast(`Added ${valid.length} file(s) to queue`, "ok");
}

// Format a Date as a local-time string for datetime-local inputs.
// toISOString() gives UTC which datetime-local misinterprets in non-UTC timezones.
function localDTStr(d) {
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// First post: now + 15 min. Each subsequent: +90 min per step.
function staggeredDT(stepIndex = 0) {
  const d = new Date();
  d.setSeconds(0, 0);
  d.setMinutes(d.getMinutes() + 15 + stepIndex * 90);
  return localDTStr(d);
}

function defaultDT() { return staggeredDT(0); }

// ────────────────────────── Render queue ───────────────────────────────────
function renderQueue() {
  const wrap = document.getElementById("queueWrap");
  const list = document.getElementById("postList");

  if (!S.posts.length) { wrap.classList.add("hidden"); return; }
  wrap.classList.remove("hidden");
  document.getElementById("qBadge").textContent = S.posts.length;

  list.innerHTML = S.posts.map(p => cardHTML(p)).join("");

  S.posts.forEach(p => {
    byId(`cap-${p.id}`)?.addEventListener("input", e => { p.caption = e.target.value; });
    byId(`dt-${p.id}`)?.addEventListener("change", e => { p.when = e.target.value; });
    byId(`rm-${p.id}`)?.addEventListener("click", () => removePost(p.id));
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
    const MAX_PREVIEW = 8;
    const thumbs = p.urls.slice(0, MAX_PREVIEW).map((u, i) =>
      `<img class="slide-thumb" src="${u}" title="${esc(p.files[i].name)}">`
    ).join("");
    const extra = p.urls.length > MAX_PREVIEW
      ? `<div class="slide-count">+${p.urls.length - MAX_PREVIEW}</div>` : "";
    const totalSize = p.files.reduce((s, f) => s + (f.size || 0), 0);
    const subline   = p.fromFolder
      ? `📂 ${esc(p.folderPath)}`
      : `🖼️ ${fmtBytes(totalSize)} total · sorted by filename`;

    return `
<div class="post-card ${stClass}" id="pc-${p.id}">
  <div class="card-top">
    <div class="thumb" style="font-size:22px">🖼️×${p.files.length}</div>
    <div class="post-info">
      <div class="post-fname">Slideshow — ${p.files.length} slides${p.postTitle ? ` · ${esc(p.postTitle)}` : ""}</div>
      <div class="post-fsize">${subline}</div>
      <div class="post-status-row" id="sr-${p.id}">${badgeHTML(p)}</div>
      ${p.err ? `<div style="font-size:12px;color:var(--error);margin-top:4px">⚠ ${esc(p.err)}</div>` : ""}
    </div>
    ${editable ? `<button class="btn btn-danger btn-sm" id="rm-${p.id}" title="Remove">✕</button>` : ""}
  </div>
  <div class="slide-strip">${thumbs}${extra}</div>
  ${editable ? `
  <div class="card-body" style="margin-top:14px">
    <div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:7px">
        <div class="field-label" style="margin:0">Caption</div>
        <button class="autofill-btn" id="gen-${p.id}" onclick="generateCaption('${p.id}')">✨ Auto-fill</button>
      </div>
      <textarea class="caption-ta" id="cap-${p.id}" style="min-height:120px"
        placeholder="Write your caption… or click ✨ Auto-fill">${esc(p.caption)}</textarea>
    </div>
    <div>
      <div class="field-label">Schedule Date &amp; Time</div>
      <input class="dt-input" type="datetime-local" id="dt-${p.id}"
             value="${p.when}" min="${localDTStr(new Date())}">
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
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:7px">
        <div class="field-label" style="margin:0">Caption</div>
        <button class="autofill-btn" id="gen-${p.id}" onclick="generateCaption('${p.id}')">✨ Auto-fill</button>
      </div>
      <textarea class="caption-ta" id="cap-${p.id}"
        placeholder="Write your caption… or click ✨ Auto-fill">${esc(p.caption)}</textarea>
    </div>
    <div>
      <div class="field-label">Schedule Date &amp; Time</div>
      <input class="dt-input" type="datetime-local" id="dt-${p.id}"
             value="${p.when}" min="${localDTStr(new Date())}">
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
  if (p && !p.fromFolder) {
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
    if (!p.fromFolder) {
      if (p.slideshow) p.urls?.forEach(u => URL.revokeObjectURL(u));
      else if (p.url)  URL.revokeObjectURL(p.url);
    }
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
      let mediaItems = [];

      if (p.slideshow) {
        // Upload each slide; fromFolder posts go via server-side path upload
        for (let i = 0; i < p.files.length; i++) {
          label.textContent = `Uploading slide ${i + 1}/${p.files.length}…`;
          let up;
          if (p.fromFolder) {
            // Server reads the file from disk and proxies to Postiz
            up = await api("POST", "/upload-from-path", { path: p.files[i].path });
          } else {
            const fd = new FormData();
            fd.append("file", p.files[i]);
            up = await api("POST", "/upload", fd, true);
          }
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

      // Title: prefer explicit postTitle (from JSON theme), then caption start, then filename
      const title = (p.postTitle || p.caption || (p.slideshow ? "Slideshow" : p.file.name)).slice(0, 100);
      const isCarousel = p.slideshow && mediaItems.length > 1;
      const needsMusic = p.slideshow
        ? true
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
            image:   mediaItems
          }],
          settings: buildSettings(intId, title, needsMusic, isCarousel)
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

// ────────────────────────── Auto-caption (Claude Vision) ───────────────────
async function generateCaption(postId) {
  if (!S.anthropicKey) {
    toast("Add your Anthropic API key in the ✨ Claude Auto-Caption section first", "fail");
    return;
  }

  const p = S.posts.find(x => x.id === postId);
  if (!p) return;

  const btn = byId(`gen-${postId}`);
  if (btn) { btn.disabled = true; btn.innerHTML = `<span class="spin"></span> Generating…`; }

  try {
    let imageB64, mediaType;

    if (p.slideshow) {
      // Use first slide as the reference image
      if (p.fromFolder) {
        const resp = await fetch(p.urls[0]);
        const blob = await resp.blob();
        mediaType = blob.type || "image/png";
        imageB64 = await blobToBase64Strip(blob);
      } else {
        mediaType = p.files[0].type || "image/png";
        imageB64 = await fileToBase64Strip(p.files[0]);
      }
    } else if (p.file.type.startsWith("video/")) {
      mediaType  = "image/jpeg";
      imageB64   = await extractVideoFrame(p.url);
      if (!imageB64) throw new Error("Could not extract a frame from the video");
    } else {
      mediaType = p.file.type || "image/jpeg";
      imageB64  = await fileToBase64Strip(p.file);
    }

    // Collect connected platform names for context
    const platforms = [...new Set(
      p.accounts.map(id => {
        const int = S.integrations.find(i => i.id === id);
        return int ? platform(int) : "";
      }).filter(Boolean)
    )];

    const res = await fetch("/api/generate", {
      method:  "POST",
      headers: {
        "Content-Type":    "application/json",
        "Authorization":   S.apiKey,
        "X-Anthropic-Key": S.anthropicKey
      },
      body: JSON.stringify({ image: imageB64, mediaType, platforms })
    });

    if (!res.ok) {
      const t = await res.text().catch(() => res.statusText);
      throw new Error(t.slice(0, 200));
    }

    const data = await res.json();

    // Build full caption: hook + blank line + hashtags
    const parts = [data.caption, data.hashtags].filter(Boolean);
    p.caption   = parts.join("\n\n").trim();
    p.postTitle = (data.title || p.postTitle || "").slice(0, 100);

    // Patch textarea and title display live without full re-render
    const ta = byId(`cap-${postId}`);
    if (ta) ta.value = p.caption;
    toast("✨ Caption generated!", "ok");

  } catch (e) {
    toast("Auto-fill failed: " + e.message, "fail");
  }

  if (btn) { btn.disabled = false; btn.innerHTML = "✨ Auto-fill"; }
}

// ── Read a File as base64 (strip data-URL prefix) ──────────────────────────
function fileToBase64Strip(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload  = () => resolve(r.result.replace(/^data:[^;]+;base64,/, ""));
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

function blobToBase64Strip(blob) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload  = () => resolve(r.result.replace(/^data:[^;]+;base64,/, ""));
    r.onerror = reject;
    r.readAsDataURL(blob);
  });
}

// ── Extract a JPEG frame from a video at ~1 s (or midpoint) ────────────────
function extractVideoFrame(videoUrl) {
  return new Promise(resolve => {
    const v = document.createElement("video");
    v.src = videoUrl; v.muted = true; v.playsInline = true;
    const done = result => { v.src = ""; resolve(result); };
    v.onloadeddata = () => { v.currentTime = Math.min(1, (v.duration || 2) / 2); };
    v.onseeked = () => {
      try {
        const MAX = 1024;
        const sc  = Math.min(1, MAX / Math.max(v.videoWidth || 640, v.videoHeight || 480));
        const c   = document.createElement("canvas");
        c.width   = Math.round((v.videoWidth  || 640) * sc);
        c.height  = Math.round((v.videoHeight || 480) * sc);
        c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
        done(c.toDataURL("image/jpeg", 0.82).replace(/^data:[^;]+;base64,/, ""));
      } catch(e) { done(null); }
    };
    v.onerror = () => done(null);
    setTimeout(() => done(null), 8000);
  });
}

// Expose for inline onclick / global use
window.connect                     = connect;
window.saveAnthropicKey            = saveAnthropicKey;
window.generateCaption             = generateCaption;
window.loadIntegrations            = loadIntegrations;
window.loadSlideshowFromFolder     = loadSlideshowFromFolder;
window.handleVideoFolderBrowse     = handleVideoFolderBrowse;
window.handleFolderBrowse          = handleFolderBrowse;
window.makePostFromFiles           = makePostFromFiles;
window.buildSlideshowPostFromPaths = buildSlideshowPostFromPaths;
window.scheduleAll                 = scheduleAll;
window.clearQueue                  = clearQueue;
window.toggleDefaultAcc            = toggleDefaultAcc;
window.selectAllChannels           = selectAllChannels;
window.selectNoneChannels          = selectNoneChannels;
window.syncPostsToDefault          = syncPostsToDefault;
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
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/integrations":
            self._proxy_get("/integrations")

        elif path == "/api/folder":
            folder = unquote(qs.get("path", [""])[0])
            self._handle_folder(folder)

        elif path == "/api/file":
            fpath = unquote(qs.get("path", [""])[0])
            self._serve_file(fpath)

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
        elif self.path == "/api/upload-from-path":
            self._handle_upload_from_path()
        elif self.path == "/api/generate":
            self._handle_generate()
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    # ── Folder scanner ────────────────────────────────────────────────────────
    def _handle_folder(self, folder_path):
        """
        Auto-detect single vs parent folder:
          • Single: folder_path/slides/ exists  → {mode:"single", slides, metadata}
          • Parent: subfolders each have slides/ → {mode:"multi", slideshows:[{folderName,slides,metadata},...]}
        """
        folder_path = os.path.expanduser(folder_path.strip())
        if not os.path.isdir(folder_path):
            self._err(f"Not a directory: {folder_path}")
            return

        slides_dir = os.path.join(folder_path, "slides")

        if os.path.isdir(slides_dir):
            # ── Single slideshow ─────────────────────────────────────────────
            slides, metadata = self._read_slideshow_dir(folder_path)
            # Always return the result — JS side shows skipped panel if < 2 slides
            result = json.dumps({"mode": "single", "slides": slides, "metadata": metadata}).encode()
            self._ok(result)

        else:
            # ── Parent folder: scan immediate subdirectories ─────────────────
            try:
                entries = sorted(os.listdir(folder_path))
            except Exception as e:
                self._err(str(e)); return

            slideshows = []
            skipped    = []
            for entry in entries:
                sub_path = os.path.join(folder_path, entry)
                if not os.path.isdir(sub_path):
                    continue
                slides, metadata = self._read_slideshow_dir(sub_path)
                slide_count = len(slides) if slides else 0
                if slides and slide_count >= 2:
                    slideshows.append({
                        "folderName": entry,
                        "slides":     slides,
                        "metadata":   metadata
                    })
                    print(f"  [folder] ✓ {entry}: {slide_count} slides")
                else:
                    reason = "no slides/ subfolder" if slides is None else f"only {slide_count} slide(s)"
                    skipped.append({
                        "folderName": entry,
                        "slideCount": slide_count,
                        "reason":     reason
                    })
                    print(f"  [folder] ✗ {entry}: {reason}")

            if not slideshows and not skipped:
                self._err(f"No subfolders found in: {folder_path}")
                return

            print(f"  [folder] {len(slideshows)} queued, {len(skipped)} skipped")
            result = json.dumps({
                "mode":       "multi",
                "slideshows": slideshows,
                "skipped":    skipped
            }).encode()
            self._ok(result)

    def _read_slideshow_dir(self, folder_path):
        """
        Return (slides_list, metadata_dict).
        slides_list is always a list (may be empty); never None.
        """
        IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}

        # JSON metadata
        metadata = {}
        try:
            json_files = sorted(
                f for f in os.listdir(folder_path) if f.lower().endswith(".json")
            )
            if json_files:
                with open(os.path.join(folder_path, json_files[0]), encoding="utf-8") as fh:
                    metadata = json.load(fh)
        except Exception as ex:
            print(f"  [folder] JSON error in {folder_path}: {ex}")

        # Slides — return empty list (not None) if slides/ doesn't exist or is empty
        slides_dir = os.path.join(folder_path, "slides")
        if not os.path.isdir(slides_dir):
            return [], metadata

        images = sorted(
            f for f in os.listdir(slides_dir)
            if os.path.splitext(f.lower())[1] in IMAGE_EXTS
        )

        slides = [
            {"name": fname,
             "path": os.path.join(slides_dir, fname),
             "size": os.path.getsize(os.path.join(slides_dir, fname))}
            for fname in images
        ]
        return slides, metadata

    # ── File server (for thumbnail previews) ─────────────────────────────────
    def _serve_file(self, file_path):
        """Serve a local image file to the browser for preview."""
        file_path = os.path.expanduser(file_path.strip())
        if not os.path.isfile(file_path):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return

        mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        try:
            with open(file_path, "rb") as fh:
                data = fh.read()
        except Exception as e:
            self._err(str(e))
            return

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    # ── Claude Vision caption generator ───────────────────────────────────────
    def _handle_generate(self):
        """Call Anthropic API with an image and return {title, caption, hashtags}."""
        import re as _re
        try:
            length   = int(self.headers.get("Content-Length", 0))
            raw      = self.rfile.read(length) if length else self.rfile.read()
            data     = json.loads(raw)

            image_b64  = data.get("image", "")
            media_type = data.get("mediaType", "image/jpeg")
            platforms  = data.get("platforms", [])
            anth_key   = self.headers.get("X-Anthropic-Key", "").strip()

            if not anth_key:
                self._err("No Anthropic API key. Add it in the ✨ Claude Auto-Caption section.")
                return
            if not image_b64:
                self._err("No image data received.")
                return

            platform_str = " and ".join(platforms) if platforms else "Instagram and TikTok"

            prompt = (
                f"Analyze this image and create social media content optimized for {platform_str}.\n\n"
                "Return ONLY a JSON object — no markdown, no extra text — with exactly these fields:\n"
                "{\n"
                '  "title": "punchy title under 80 chars (good for YouTube/TikTok)",\n'
                '  "caption": "engaging hook, 2-3 sentences, conversational tone, relevant emojis",\n'
                '  "hashtags": "#tag1 #tag2 #tag3 ... (15-20 relevant hashtags, space-separated)"\n'
                "}\n\n"
                "Caption rules: start with a strong hook, speak directly to the viewer, no generic phrases.\n"
                "Hashtags: mix of broad (#food) and niche (#sheetpandinners) tags."
            )

            body = json.dumps({
                "model": "claude-opus-4-5",
                "max_tokens": 900,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image",
                         "source": {"type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            }).encode()

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "x-api-key":         anth_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type":      "application/json",
                    "Accept":            "application/json",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=45) as r:
                resp = json.loads(r.read())

            text = resp["content"][0]["text"].strip()
            # Strip markdown code fences if Claude wrapped the JSON
            text = _re.sub(r"^```(?:json)?\s*", "", text, flags=_re.MULTILINE)
            text = _re.sub(r"\s*```$",          "", text, flags=_re.MULTILINE)
            text = text.strip()

            result = json.loads(text)
            print(f"  [generate] title={result.get('title','')[:50]}")
            self._ok(json.dumps(result).encode())

        except urllib.error.HTTPError as e:
            self._forward_error(e)
        except Exception as e:
            self._err(str(e))

    # ── Server-side upload from disk path ─────────────────────────────────────
    def _handle_upload_from_path(self):
        """Read a file from a disk path and proxy it to Postiz /upload."""
        try:
            length   = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length) if length else self.rfile.read()
            req_data = json.loads(raw_body)
            file_path = os.path.expanduser(req_data.get("path", "").strip())

            if not os.path.isfile(file_path):
                self._err(f"File not found: {file_path}")
                return

            filename  = os.path.basename(file_path)
            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

            with open(file_path, "rb") as fh:
                file_data = fh.read()

            print(f"  [upload-from-path] {filename} ({len(file_data)//1024} KB)")

            # Build multipart/form-data body manually
            boundary  = uuid.uuid4().hex
            part_head = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode("utf-8")
            part_tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
            multipart = part_head + file_data + part_tail

            last_exc = None
            for attempt in range(3):
                try:
                    req = urllib.request.Request(
                        f"{POSTIZ_API}/upload",
                        data=multipart,
                        headers={
                            "Authorization": self._auth(),
                            "Content-Type":  f"multipart/form-data; boundary={boundary}",
                            "Accept":        "application/json",
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=120) as r:
                        resp_body = r.read()
                    self._ok(resp_body)
                    return
                except urllib.error.HTTPError:
                    raise
                except Exception as exc:
                    last_exc = exc
                    if attempt < 2:
                        print(f"  [upload retry {attempt + 1}] {exc}")
                        time.sleep(2 ** attempt)
                    else:
                        raise last_exc

        except urllib.error.HTTPError as e:
            self._forward_error(e)
        except Exception as e:
            self._err(str(e))

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
            # Debug: dump integrations to terminal
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
                    raise
                except Exception as exc:
                    last_exc = exc
                    if attempt < 2:
                        print(f"  [upload retry {attempt + 1}] {exc}")
                        time.sleep(2 ** attempt)
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
        if "/api/" in path or str(status).startswith(("4", "5")):
            print(f"  {status}  {path}")


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    host = "0.0.0.0"
    url  = f"http://{host}:{PORT}"

    # Only open a browser tab when running locally (not on Render/CI)
    if not os.environ.get("RENDER"):
        def open_browser():
            time.sleep(0.9)
            webbrowser.open(f"http://localhost:{PORT}")
        threading.Thread(target=open_browser, daemon=True).start()

    print()
    print("  ╔══════════════════════════════════════════╗")
    print(f"  ║  🚀  Postiz Bulk Scheduler               ║")
    print(f"  ║                                          ║")
    print(f"  ║  Listening on port {PORT:<22}║")
    print(f"  ║  Stop:  Ctrl + C                         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()

    server = HTTPServer((host, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped. Bye!")


if __name__ == "__main__":
    main()