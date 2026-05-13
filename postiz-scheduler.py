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
import subprocess
import tempfile
import shutil
import urllib.request
import urllib.error
import webbrowser
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
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


.cadence-settings {
  background: var(--card2); border-radius: 10px; padding: 16px;
  border: 1px solid var(--border);
}
.cadence-preview {
  margin-top: 12px; font-size: 12px; color: var(--muted); line-height: 1.9;
  background: var(--bg); border-radius: 8px; padding: 10px 14px;
}

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

  <!-- ── Scheduling / Cadence ── -->
  <div class="card hidden" id="schedModeCard">
    <div class="section-label">📅 Daily Cadence — 8 AM to 8 PM EST</div>
    <div class="cadence-settings">
      <div style="display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap">
        <div>
          <div class="field-label">Posts Per Day</div>
          <input type="number" id="postsPerDay" min="1" max="12" value="3"
                 class="dt-input" style="width:110px"
                 oninput="cadenceChanged()">
        </div>
        <div>
          <div class="field-label">Start Date</div>
          <input type="date" id="cadenceStartDate" class="dt-input" style="width:170px"
                 oninput="cadenceChanged()">
        </div>
      </div>
      <div id="cadencePreview" class="cadence-preview"></div>
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

  <!-- ── Video Stitch Tool ── -->
  <div class="card" id="stitchCard">
    <div class="section-label" style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
      <span>🎬</span> Stitch Source + CTA Video
    </div>
    <p style="font-size:13px;color:var(--muted);margin-bottom:18px">
      Pick <strong style="color:var(--text)">one video or a whole folder</strong> of source videos — each gets stitched
      with the same CTA clip. Download individually or grab everything as a ZIP.
    </p>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:18px">

      <!-- ── SOURCE column ── -->
      <div>
        <div class="field-label">Source Videos</div>

        <!-- File pickers -->
        <div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap">
          <button class="btn btn-outline btn-sm" title="Pick individual video files"
                  onclick="document.getElementById('stitchSourceFiles').click()">
            📄 Browse Files
          </button>
          <button class="btn btn-outline btn-sm" title="Pick an entire folder of videos"
                  onclick="document.getElementById('stitchSourceFolder').click()">
            📁 Browse Folder
          </button>
          <button class="btn btn-outline btn-sm" title="Clear source selection"
                  onclick="stitchClearSource()" style="color:var(--error);border-color:var(--error)">✕</button>
        </div>
        <input type="file" id="stitchSourceFiles"  accept="video/*" multiple style="display:none"
               onchange="stitchSourceFilesChosen(this)">
        <input type="file" id="stitchSourceFolder" accept="video/*" webkitdirectory style="display:none"
               onchange="stitchSourceFolderChosen(this)">

        <!-- File list -->
        <div id="stitchSourceList"
             style="min-height:36px;max-height:160px;overflow-y:auto;background:var(--card2);
                    border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:12px;color:var(--muted)">
          No files selected
        </div>

        <!-- OR disk path -->
        <div style="margin-top:10px;font-size:11px;color:var(--muted);margin-bottom:4px">
          — or type a folder path (server reads from disk) —
        </div>
        <div style="display:flex;gap:6px">
          <input type="text" id="stitchFolderPath" class="key-input"
                 placeholder="/Users/harsh/Videos/sources"
                 style="font-size:12px;flex:1"
                 oninput="stitchClearSource()">
        </div>
      </div>

      <!-- ── CTA column ── -->
      <div>
        <div class="field-label">CTA Video (single, applied to all)</div>
        <div style="display:flex;gap:8px;margin-bottom:10px">
          <button class="btn btn-outline btn-sm"
                  onclick="document.getElementById('stitchCtaFile').click()">
            📂 Browse
          </button>
          <span id="stitchCtaName"
                style="font-size:12px;color:var(--muted);align-self:center;
                       overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px">
            No file chosen
          </span>
        </div>
        <input type="file" id="stitchCtaFile" accept="video/*" style="display:none"
               onchange="stitchCtaFileChosen(this)">
        <input type="text" id="stitchCtaUrl" class="key-input"
               placeholder="…or paste CTA URL / disk path"
               style="font-size:12px"
               oninput="stitchClearCta()">
      </div>
    </div>

    <!-- Source seconds + Stitch button -->
    <div style="display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:6px">
      <div>
        <div class="field-label">Source clip length (seconds)</div>
        <div style="display:flex;align-items:center;gap:10px">
          <input type="range" id="stitchSecRange" min="1" max="30" value="5" step="1"
                 style="width:140px;accent-color:var(--accent)"
                 oninput="document.getElementById('stitchSecVal').textContent=this.value">
          <span id="stitchSecVal"
                style="font-size:15px;font-weight:700;color:var(--accent);min-width:28px">5</span>
          <span style="font-size:12px;color:var(--muted)">sec</span>
        </div>
      </div>
      <button class="btn" id="stitchBtn" onclick="runStitch()" style="padding:11px 24px">
        🎬 Stitch All
      </button>
    </div>

    <!-- Progress bar -->
    <div id="stitchProgress" style="display:none;margin-top:14px">
      <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:6px">
        <span id="stitchProgLabel">Stitching…</span>
        <span id="stitchProgFrac"></span>
      </div>
      <div style="background:var(--card2);border-radius:6px;height:6px;overflow:hidden">
        <div id="stitchProgFill"
             style="height:100%;background:var(--accent);transition:width .3s;width:0%"></div>
      </div>
    </div>

    <!-- Results -->
    <div id="stitchResults" style="display:none;margin-top:16px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
        <div style="font-size:13px;font-weight:600;color:var(--success)" id="stitchResultsTitle">✓ Done</div>
        <a id="stitchZipLink" href="#" class="btn btn-outline btn-sm" download="stitched_videos.zip"
           style="display:none">⬇ Download All (ZIP)</a>
      </div>
      <div id="stitchResultsList"
           style="display:flex;flex-direction:column;gap:8px"></div>
    </div>

    <div id="stitchError"
         style="display:none;margin-top:12px;font-size:13px;color:var(--error)"></div>
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
  integrations:    [],
  defaultAccounts: new Set(),   // which channels new posts should default to
  posts:           [],
  busy:            false,
  // scheduling mode
  schedMode:       "cadence",   // "staggered" | "cadence"
  postsPerDay:     3,
  cadenceStart:    null           // Date (midnight local) for cadence start day
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
  initSchedMode();
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
    document.getElementById("schedModeCard").classList.remove("hidden");
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
// isVideo    = true when the post is a video file (not image/carousel)
function buildSettings(intId, title, needsMusic = false, isCarousel = false, isVideo = false) {
  const int  = S.integrations.find(i => i.id === intId);
  const pl   = int ? platform(int) : "";

  // For YouTube Shorts: append #Shorts — reserve 8 chars so it never gets truncated
  let resolvedTitle = (title || "").slice(0, 92);
  if (pl.includes("youtube") && isVideo && !resolvedTitle.includes("#Shorts")) {
    resolvedTitle = (resolvedTitle + " #Shorts").trim();
  }
  resolvedTitle = resolvedTitle.slice(0, 100);

  const base = { title: resolvedTitle };

  console.log(`[buildSettings] intId=${intId} platform="${pl}" carousel=${isCarousel} video=${isVideo}`);

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
    // For short vertical videos post as YouTube Shorts explicitly.
    // youtubeVideoType tells Postiz to use the Shorts upload path.
    // type is the privacy setting (always "public").
    extra = {
      type:             "public",
      youtubeVideoType: isVideo ? "short" : "video",
    };
  } else if (pl.includes("linkedin")) {
    extra = { privacy_level: "PUBLIC" };
  } else if (pl.includes("instagram")) {
    // Instagram carousels require DIRECT_POST (Business/Creator accounts only).
    // REMINDER mode only supports single images/videos — not carousels.
    // trial_reel must be false for image posts (it's for video Reels only).
    extra = {
      post_type:               isCarousel ? "post" : "post",
      content_posting_method:  "DIRECT_POST",
      trial_reel:              false
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
  if (S.schedMode === "cadence") applyDailyCadence();
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
      if (S.schedMode === "cadence") applyDailyCadence();
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
      if (S.schedMode === "cadence") applyDailyCadence();
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

// ── Extract caption + title from either JSON format ─────────────────────────
// New format: { caption, title, slides[], hashtags_str, hashtags[], short_pitch, … }
// Old format: { hook_caption, recipes[], cta_caption[], theme, … }
function extractMeta(metadata) {
  if (!metadata) return { caption: "", title: "" };

  // Resolve hashtag string from whichever field is present
  const hashtagsStr = (
    metadata.hashtags_str ||
    (Array.isArray(metadata.hashtags) ? metadata.hashtags.join(" ") : "")
  ).trim();

  // New format — caption is already fully assembled
  if (metadata.caption) {
    let caption = metadata.caption.trim();
    // Append hashtags if they're not already present in the caption
    if (hashtagsStr && !caption.includes(hashtagsStr.slice(0, 15))) {
      caption = caption + "\n\n" + hashtagsStr;
    }
    return {
      caption,
      title: (metadata.title || metadata.slug || "").slice(0, 100)
    };
  }

  // Old format — build caption from parts
  const parts = [];
  if (metadata.hook_caption) parts.push(metadata.hook_caption);
  if (metadata.recipes?.length) parts.push(metadata.recipes.map(r => r.title).join("\n"));
  if (metadata.cta_caption?.length) {
    parts.push(Array.isArray(metadata.cta_caption)
      ? metadata.cta_caption.join("\n") : metadata.cta_caption);
  }
  if (hashtagsStr) parts.push(hashtagsStr);
  return {
    caption: parts.join("\n\n").trim(),
    title:   (metadata.theme || "").slice(0, 100)
  };
}

// ── Build a post object from real File objects ───────────────────────────────
function makePostFromFiles(folderName, slideFiles, metadata, stepIndex) {
  const { caption, title } = extractMeta(metadata);
  const when = staggeredDT(stepIndex);
  return {
    id:         `p${Date.now()}${Math.random().toString(36).slice(2)}`,
    slideshow:  true,
    fromFolder: false,
    folderPath: folderName,
    files:      slideFiles,
    urls:       slideFiles.map(f => URL.createObjectURL(f)),
    caption,
    postTitle:  title,
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
      if (S.schedMode === "cadence") applyDailyCadence();
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
      if (S.schedMode === "cadence") applyDailyCadence();
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
  const { caption, title } = extractMeta(metadata);
  return {
    id:         `p${Date.now()}${Math.random().toString(36).slice(2)}`,
    slideshow:  true,
    fromFolder: true,
    folderPath: folderName,
    files:      slides,
    urls:       slides.map(s => `/api/file?path=${encodeURIComponent(s.path)}`),
    caption,
    postTitle:  title,
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
  if (S.schedMode === "cadence") applyDailyCadence();
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

// ────────────────────────── Daily cadence scheduling ───────────────────────
// Window: 8 AM EST (UTC-5 = 13:00 UTC) → 8 PM PST (UTC-8 = 04:00 UTC next day)
// That is a 15-hour (900 min) window.
// Posts are spread evenly across that window each day.
// If more posts than postsPerDay, they overflow into subsequent days.

function initSchedMode() {
  const today = new Date();
  const pad = n => String(n).padStart(2, "0");
  const todayStr = `${today.getFullYear()}-${pad(today.getMonth()+1)}-${pad(today.getDate())}`;
  document.getElementById("cadenceStartDate").value = todayStr;
  S.cadenceStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
}


function cadenceChanged() {
  const ppd = parseInt(document.getElementById("postsPerDay").value) || 3;
  S.postsPerDay = Math.max(1, Math.min(12, ppd));
  const dateVal = document.getElementById("cadenceStartDate").value;
  if (dateVal) {
    const [y, m, d] = dateVal.split("-").map(Number);
    S.cadenceStart = new Date(y, m - 1, d);
  }
  applyDailyCadence();
  updateCadencePreview();
}

// Returns UTC minutes from midnight UTC for slot i of n slots within the daily window.
// Window: 8 AM EST (13:00 UTC) → 8 PM EST (01:00 UTC next day = 25:00) = 12 hours.
function cadenceSlotUTCMinutes(i, n) {
  const WIN_START = 13 * 60;   // 8 AM EST = 13:00 UTC
  const WIN_END   = 25 * 60;   // 8 PM EST = next-day 01:00 UTC
  const winLen    = WIN_END - WIN_START;   // 720 minutes = 12 hours
  if (n === 1) return WIN_START + winLen / 2;   // single post → midpoint
  return WIN_START + i * winLen / (n - 1);      // spread from start to end
}

// Return datetime-local string for global post index (0-based across all days).
function cadenceDT(postIndex) {
  const ppd  = S.postsPerDay || 3;
  const day  = Math.floor(postIndex / ppd);
  const slot = postIndex % ppd;

  // Base date: cadenceStart (midnight local) + day offset
  const base = S.cadenceStart ? new Date(S.cadenceStart) : new Date();
  base.setHours(0, 0, 0, 0);
  base.setDate(base.getDate() + day);

  // Compute UTC midnight of that local date
  // We use Date.UTC with local year/month/day so the slot offsets are from UTC midnight
  const utcMidnight = Date.UTC(base.getFullYear(), base.getMonth(), base.getDate());
  const slotUTCMs   = utcMidnight + cadenceSlotUTCMinutes(slot, ppd) * 60000;

  return localDTStr(new Date(slotUTCMs));
}

// Reassign scheduled times for all pending/error posts using the cadence.
function applyDailyCadence() {
  if (S.schedMode !== "cadence") return;
  const pending = S.posts.filter(p => p.status === "pending" || p.status === "error");
  pending.forEach((p, i) => { p.when = cadenceDT(i); });
  renderQueue();
  updateCadencePreview();
}

function updateCadencePreview() {
  const preview = document.getElementById("cadencePreview");
  if (!preview) return;
  const ppd = S.postsPerDay || 3;
  const pendingCount = S.posts.filter(p => p.status === "pending" || p.status === "error").length;
  const totalDays = pendingCount ? Math.ceil(pendingCount / ppd) : 2;
  const showDays  = Math.min(totalDays, 4);

  const lines = [];
  for (let day = 0; day < showDays; day++) {
    const slots = [];
    for (let slot = 0; slot < ppd; slot++) {
      const dt = new Date(cadenceDT(day * ppd + slot));
      slots.push(dt.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }));
    }
    const base = S.cadenceStart ? new Date(S.cadenceStart) : new Date();
    base.setHours(0, 0, 0, 0);
    base.setDate(base.getDate() + day);
    const label = day === 0 ? "Today" : day === 1 ? "Tomorrow"
      : base.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
    const postNums = [];
    for (let s = 0; s < ppd; s++) {
      const idx = day * ppd + s;
      if (idx < pendingCount) postNums.push(`Post ${idx + 1}`);
    }
    const postHint = postNums.length ? ` <span style="color:var(--accent);font-weight:600">(${postNums.join(", ")})</span>` : "";
    lines.push(`<div><strong style="color:var(--text)">${label}:</strong> ${slots.join(" · ")}${postHint}</div>`);
  }
  if (totalDays > showDays) {
    lines.push(`<div style="color:var(--muted)">…continuing for ${totalDays - showDays} more day${totalDays - showDays > 1 ? "s" : ""}</div>`);
  }
  const note = `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border);color:var(--muted);font-size:11px">
    Times shown in your local timezone · Window = 8 AM EST → 8 PM EST (${ppd} slot${ppd>1?"s":""}/day)
  </div>`;
  preview.innerHTML = lines.join("") + note;
}

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
      <div class="post-fname">Slideshow — ${p.files.length} slides${p.postTitle ? ` · ${esc(p.postTitle)}` : ""}${p.files.length > 10 ? ` <span style="background:rgba(240,185,106,.18);color:var(--warn);border-radius:5px;padding:1px 7px;font-size:11px;font-weight:700">⚠ Instagram: first 10 only</span>` : ""}</div>
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
      </div>
      <textarea class="caption-ta" id="cap-${p.id}" style="min-height:120px"
        placeholder="Write your caption…">${esc(p.caption)}</textarea>
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
      <div style="margin-bottom:7px">
        <div class="field-label" style="margin:0">Caption</div>
      </div>
      <textarea class="caption-ta" id="cap-${p.id}"
        placeholder="Write your caption…">${esc(p.caption)}</textarea>
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
  if (S.schedMode === "cadence") applyDailyCadence();
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
        // Instagram carousels allow max 10 slides — cap here to avoid API rejection
        const INSTA_MAX = 10;
        const slidesToUpload = p.files.slice(0, INSTA_MAX);
        if (p.files.length > INSTA_MAX) {
          toast(`⚠ ${postLabel}: trimmed to ${INSTA_MAX} slides (Instagram max)`, "");
        }

        // Upload each slide; fromFolder posts go via server-side path upload
        for (let i = 0; i < slidesToUpload.length; i++) {
          label.textContent = `Uploading slide ${i + 1}/${slidesToUpload.length}…`;
          let up;
          if (p.fromFolder) {
            // Server reads the file from disk and proxies to Postiz
            up = await api("POST", "/upload-from-path", { path: slidesToUpload[i].path });
          } else {
            const fd = new FormData();
            fd.append("file", slidesToUpload[i]);
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

      // Title: prefer explicit postTitle (from JSON), else clean filename for videos, else caption
      const rawTitle = p.slideshow
        ? (p.postTitle || "Slideshow")
        : (p.postTitle || cleanVideoTitle(p.file.name) || p.caption || p.file.name);
      const title = rawTitle.slice(0, 100);
      const isCarousel = p.slideshow && mediaItems.length > 1;
      const isVideo    = !p.slideshow && p.file?.type?.startsWith("video/");
      const needsMusic = p.slideshow
        ? true
        : (p.file.type.startsWith("image/") || !(await videoHasAudio(p.url)));

      await api("POST", "/posts", {
        type: "schedule",
        date: new Date(p.when).toISOString(),
        shortLink: false,
        tags: [],
        posts: p.accounts.map(intId => {
          const intObj  = S.integrations.find(i => i.id === intId) || {};
          const pl_     = platform(intObj);
          // YouTube: inject #Shorts into description so the algorithm gets two signals
          // (title already has it from buildSettings; description is the second trigger)
          let content = p.caption;
          if (pl_.includes("youtube") && isVideo && !content.includes("#Shorts")) {
            content = (content + "\n\n#Shorts").trim();
          }
          return {
            integration: { id: intId },
            value: [{ content, image: mediaItems }],
            settings: buildSettings(intId, title, needsMusic, isCarousel, isVideo)
          };
        })
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
// Extract a clean human title from a video filename.
// "grill_#recipe_1778212134827.mp4" → "grill #recipe"
// Steps: strip extension → remove trailing numeric timestamp → underscores to spaces → trim
function cleanVideoTitle(filename) {
  let name = filename.replace(/\.[^.]+$/, "");        // strip extension
  name = name.replace(/_[0-9a-f]{6,12}$/i, "");      // remove trailing _hexhash  (e.g. _be73417f)
  name = name.replace(/_\d{8,}/g, "");               // remove any _longNumber anywhere (timestamps like _1778212134827)
  name = name.replace(/_/g, " ").trim();              // underscores → spaces
  return name;
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

// ────────────────────────── Video Stitch UI ────────────────────────────────

const STITCH = {
  sourceFiles: [],   // File[] from browser picker
  ctaFile:     null, // File from browser picker
};

// ── Source selection ─────────────────────────────────────────────────────────
function stitchSourceFilesChosen(input) {
  const files = [...input.files].filter(f => f.type.startsWith("video/"));
  if (!files.length) return;
  STITCH.sourceFiles = files;
  document.getElementById("stitchFolderPath").value = "";
  stitchRenderSourceList();
  input.value = "";
}

function stitchSourceFolderChosen(input) {
  const files = [...input.files].filter(f => f.type.startsWith("video/"));
  if (!files.length) { toast("No video files found in that folder", "fail"); return; }
  STITCH.sourceFiles = files;
  document.getElementById("stitchFolderPath").value = "";
  stitchRenderSourceList();
  input.value = "";
}

function stitchClearSource() {
  STITCH.sourceFiles = [];
  stitchRenderSourceList();
}

function stitchRenderSourceList() {
  const el = document.getElementById("stitchSourceList");
  if (!STITCH.sourceFiles.length) {
    el.innerHTML = `<span style="color:var(--muted)">No files selected</span>`;
    return;
  }
  const total = STITCH.sourceFiles.reduce((s, f) => s + f.size, 0);
  el.innerHTML =
    `<div style="color:var(--accent);font-weight:600;margin-bottom:6px">
       ${STITCH.sourceFiles.length} video${STITCH.sourceFiles.length > 1 ? "s" : ""} selected
       · ${fmtBytes(total)} total
     </div>` +
    STITCH.sourceFiles.map(f =>
      `<div style="display:flex;justify-content:space-between;padding:2px 0;
                   border-bottom:1px solid var(--border)">
         <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
                      max-width:70%;color:var(--text)">${esc(f.name)}</span>
         <span style="color:var(--muted);white-space:nowrap;margin-left:8px">${fmtBytes(f.size)}</span>
       </div>`
    ).join("");
}

// ── CTA selection ─────────────────────────────────────────────────────────────
function stitchCtaFileChosen(input) {
  const file = input.files[0];
  if (!file) return;
  STITCH.ctaFile = file;
  document.getElementById("stitchCtaName").textContent = file.name;
  document.getElementById("stitchCtaName").title       = file.name;
  document.getElementById("stitchCtaUrl").value        = "";
  input.value = "";
}

function stitchClearCta() {
  STITCH.ctaFile = null;
  document.getElementById("stitchCtaName").textContent = "No file chosen";
}

// ── Main stitch runner ────────────────────────────────────────────────────────
async function runStitch() {
  const btn       = document.getElementById("stitchBtn");
  const progWrap  = document.getElementById("stitchProgress");
  const progLabel = document.getElementById("stitchProgLabel");
  const progFrac  = document.getElementById("stitchProgFrac");
  const progFill  = document.getElementById("stitchProgFill");
  const resultsEl = document.getElementById("stitchResults");
  const errorEl   = document.getElementById("stitchError");
  const srcSec    = parseFloat(document.getElementById("stitchSecRange").value) || 5;

  resultsEl.style.display = "none";
  errorEl.style.display   = "none";

  const folderPath   = document.getElementById("stitchFolderPath").value.trim();
  const ctaUrl       = document.getElementById("stitchCtaUrl").value.trim();
  const hasFiles     = STITCH.sourceFiles.length > 0;
  const hasFolderPath = !!folderPath;
  const hasCtaFile   = !!STITCH.ctaFile;
  const hasCtaUrl    = !!ctaUrl;

  // Validate source
  if (!hasFiles && !hasFolderPath) {
    errorEl.textContent   = "⚠ Select source video file(s) / folder, or enter a disk folder path.";
    errorEl.style.display = "block"; return;
  }
  // Validate CTA
  if (!hasCtaFile && !hasCtaUrl) {
    errorEl.textContent   = "⚠ Choose a CTA video file or paste a URL / disk path.";
    errorEl.style.display = "block"; return;
  }
  // File mode: CTA must also be a file (can't mix upload + URL)
  if (hasFiles && !hasCtaFile) {
    errorEl.textContent   = "⚠ When uploading source files, the CTA must also be a file (not a URL).";
    errorEl.style.display = "block"; return;
  }

  btn.disabled          = true;
  btn.innerHTML         = `<span class="spin"></span> Stitching…`;
  progWrap.style.display = "block";
  progFill.style.width   = "0%";

  const totalCount = hasFiles ? STITCH.sourceFiles.length : "?";
  progLabel.textContent = `Stitching… (${totalCount} video${totalCount === 1 ? "" : "s"})`;
  progFrac.textContent  = "";

  // Animate indeterminate bar while waiting for server
  let animFrame;
  let pseudo = 0;
  function animBar() {
    pseudo = (pseudo + 0.8) % 100;
    progFill.style.width = `${Math.min(pseudo, 90)}%`;
    animFrame = requestAnimationFrame(animBar);
  }
  animFrame = requestAnimationFrame(animBar);

  try {
    let res;

    if (hasFiles) {
      // ── Multipart: all source files + CTA uploaded ──
      const fd = new FormData();
      STITCH.sourceFiles.forEach(f => fd.append("source", f));
      fd.append("cta",            STITCH.ctaFile);
      fd.append("source_seconds", srcSec);
      res = await fetch("/api/stitch-videos", { method: "POST", body: fd });
    } else {
      // ── JSON: folder path on disk + CTA URL/path ──
      const body = {
        folder_path:    folderPath,
        source_seconds: srcSec,
      };
      if (hasCtaUrl) body.cta_url  = ctaUrl;
      else           body.cta_path = ctaUrl; // treat as path if starts with /
      res = await fetch("/api/stitch-videos", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(body)
      });
    }

    cancelAnimationFrame(animFrame);

    if (!res.ok) {
      const t = await res.text().catch(() => res.statusText);
      let msg = t;
      try { msg = JSON.parse(t).error || t; } catch (_) {}
      throw new Error(msg.slice(0, 300));
    }

    const data = await res.json();
    progFill.style.width  = "100%";
    progFrac.textContent  = `${data.succeeded}/${data.total}`;
    progLabel.textContent = data.succeeded === data.total
      ? `✓ All ${data.total} videos stitched!`
      : `Done — ${data.succeeded}/${data.total} succeeded`;

    stitchRenderResults(data);
    toast(`🎬 Stitch done — ${data.succeeded}/${data.total} videos ready`, "ok");

  } catch (e) {
    cancelAnimationFrame(animFrame);
    errorEl.textContent   = "⚠ " + e.message;
    errorEl.style.display = "block";
    toast("Stitch failed: " + e.message, "fail");
    progWrap.style.display = "none";
  }

  btn.disabled  = false;
  btn.innerHTML = "🎬 Stitch All";
}

function stitchRenderResults(data) {
  const resultsEl  = document.getElementById("stitchResults");
  const listEl     = document.getElementById("stitchResultsList");
  const titleEl    = document.getElementById("stitchResultsTitle");
  const zipLinkEl  = document.getElementById("stitchZipLink");

  const ok      = (data.results || []).filter(r => r.ok);
  const failed  = (data.results || []).filter(r => !r.ok);

  titleEl.textContent = `✓ ${ok.length} of ${data.total} video${data.total > 1 ? "s" : ""} stitched`;
  titleEl.style.color = failed.length ? "var(--warn)" : "var(--success)";

  // ZIP button
  if (data.zip_url && ok.length > 1) {
    zipLinkEl.href          = data.zip_url;
    zipLinkEl.style.display = "inline-flex";
  } else {
    zipLinkEl.style.display = "none";
  }

  listEl.innerHTML = (data.results || []).map(r => {
    if (r.ok) {
      return `
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:10px 12px;background:var(--card2);border-radius:8px;
            border:1px solid var(--border);gap:12px">
  <div style="overflow:hidden">
    <div style="font-size:12px;font-weight:600;color:var(--text);
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(r.label)}</div>
    <div style="font-size:11px;color:var(--muted);word-break:break-all;margin-top:2px">${esc(r.stitched_filepath)}</div>
  </div>
  <a href="${esc(r.download_url)}" class="btn btn-success btn-sm"
     download="${esc(r.filename)}" style="white-space:nowrap;flex-shrink:0">⬇ Download</a>
</div>`;
    } else {
      return `
<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;
            background:rgba(240,106,138,.08);border-radius:8px;
            border:1px solid rgba(240,106,138,.3)">
  <span style="font-size:18px">✕</span>
  <div>
    <div style="font-size:12px;font-weight:600;color:var(--error)">${esc(r.label)}</div>
    <div style="font-size:11px;color:var(--muted)">${esc(r.error || "Unknown error")}</div>
  </div>
</div>`;
    }
  }).join("");

  resultsEl.style.display = "block";
  resultsEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Expose for inline onclick / global use
window.connect                     = connect;
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
window.runStitch                   = runStitch;
window.stitchSourceFilesChosen     = stitchSourceFilesChosen;
window.stitchSourceFolderChosen    = stitchSourceFolderChosen;
window.stitchCtaFileChosen         = stitchCtaFileChosen;
window.stitchClearSource           = stitchClearSource;
window.stitchClearCta              = stitchClearCta;
window.stitchRenderResults         = stitchRenderResults;
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
#  Video stitching helpers (ported from nutrition-rag-chatbot /download-profile-videos)
# ─────────────────────────────────────────────────────────────────────────────

STITCH_OUTPUT_BASE = os.path.expanduser("~/Documents/stitched_profile_videos")


def _parse_multipart(content_type: str, data: bytes) -> dict:
    """
    Minimal multipart/form-data parser — no external deps.
    Returns {field_name: [{"data": bytes, "filename": str|None}, ...]}.
    Duplicate field names (e.g. multiple 'source' files) accumulate as a list.
    """
    boundary = None
    for seg in content_type.split(";"):
        seg = seg.strip()
        if seg.lower().startswith("boundary="):
            boundary = seg[9:].strip('"\'')
            break
    if not boundary:
        return {}

    delim  = ("--" + boundary).encode()
    result = {}

    for chunk in data.split(delim)[1:]:
        stripped = chunk.strip()
        if stripped in (b"--", b"") or stripped.startswith(b"--"):
            continue
        sep = b"\r\n\r\n" if b"\r\n\r\n" in chunk else b"\n\n"
        if sep not in chunk:
            continue
        raw_headers, body = chunk.split(sep, 1)
        if body.endswith(b"\r\n"):
            body = body[:-2]

        name = filename = None
        for line in raw_headers.split(b"\r\n"):
            line_s = line.decode("utf-8", errors="replace")
            if line_s.lower().startswith("content-disposition:"):
                for part in line_s.split(";"):
                    part = part.strip()
                    if part.startswith("name="):
                        name = part[5:].strip("\"'")
                    elif part.startswith("filename="):
                        filename = part[9:].strip("\"'")
        if name:
            result.setdefault(name, []).append({"data": body, "filename": filename})

    return result


def _probe_format_duration_sec(path: str):
    """Best-effort container duration from ffprobe (seconds)."""
    r = subprocess.run(
        ["ffprobe", "-v", "quiet",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         path],
        capture_output=True, text=True,
    )
    s = (r.stdout or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _stitch_videos_ffmpeg(
    video1_path: str,
    video2_path: str,
    output_path: str,
    *,
    gap_seconds: float = 0,
    source_prefix_seconds=None,
) -> str:
    """
    Stitch [video1 (or its first source_prefix_seconds)] then [video2].
    Audio for the entire output comes from video1 only (CTA audio is ignored).
    Both clips are scaled to match the source orientation at 30fps / H.264 + AAC 128k.
    Vertical source  (h > w) → 1080×1920  (9:16, for Shorts/Reels/TikTok).
    Landscape source (w > h) → 1920×1080  (16:9).
    """
    # ── Probe source dimensions to choose output orientation ─────────────────
    # Default is VERTICAL (1080×1920) — correct for Shorts/Reels/TikTok.
    # Only switch to landscape if the source is clearly wider than it is tall.
    out_w, out_h = 1080, 1920  # safe default: portrait

    _dim = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0",
         video1_path],
        capture_output=True, text=True,
    )
    try:
        _parts = _dim.stdout.strip().split(",")
        _src_w = int(_parts[0])
        _src_h = int(_parts[1])
        if _src_w > _src_h:          # clearly landscape source
            out_w, out_h = 1920, 1080
    except Exception as _probe_err:
        _src_w, _src_h = 0, 0
        print(f"  [stitch] ⚠ ffprobe failed ({_probe_err}), defaulting to portrait 1080×1920")

    print(f"  [stitch] source dims: {_src_w}×{_src_h} → output: {out_w}×{out_h}")

    scale_pad = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30"
    )

    # Probe whether video1 has audio
    _pr = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "a",
         "-show_entries", "stream=codec_type",
         "-print_format", "json",
         video1_path],
        capture_output=True, text=True,
    )
    try:
        src_has_audio = bool(json.loads(_pr.stdout or "{}").get("streams"))
    except (json.JSONDecodeError, ValueError):
        src_has_audio = False

    src_sec = (
        float(source_prefix_seconds)
        if source_prefix_seconds and float(source_prefix_seconds) > 0
        else None
    )
    gap_sec = float(gap_seconds) if gap_seconds and float(gap_seconds) > 0 else 0.0

    v1_dur = _probe_format_duration_sec(video1_path) or 0.0
    v2_dur = _probe_format_duration_sec(video2_path) or 0.0
    used_v1_dur = float(src_sec) if src_sec else v1_dur
    total_dur = used_v1_dur + gap_sec + v2_dur

    parts = []

    # Video 1 — trim to src_sec or natural duration
    if src_sec:
        t = f"{src_sec:.6f}".rstrip("0").rstrip(".")
    elif v1_dur > 0:
        t = f"{v1_dur:.3f}"
    else:
        t = None

    if t:
        parts.append(f"[0:v]trim=start=0:duration={t},setpts=PTS-STARTPTS,{scale_pad}[vA]")
    else:
        parts.append(f"[0:v]{scale_pad}[vA]")

    # Video 2 (CTA) — scale only, no audio taken from it
    parts.append(f"[1:v]{scale_pad}[vB]")

    # Video concat (with optional gap)
    if gap_sec > 0:
        gap_t = f"{gap_sec:.3f}"
        parts.append(f"color=c=black:size={out_w}x{out_h}:rate=30:duration={gap_t},format=yuv420p[gv]")
        parts.append("[vA][gv][vB]concat=n=3:v=1:a=0[outv]")
    else:
        parts.append("[vA][vB]concat=n=2:v=1:a=0[outv]")

    # Audio from source only
    extra_flags = []
    if src_has_audio:
        if total_dur > 0:
            t_total = f"{total_dur:.3f}"
            parts.append(
                f"[0:a]atrim=start=0:duration={t_total},asetpts=PTS-STARTPTS,"
                f"aresample=44100,aformat=channel_layouts=stereo[outa]"
            )
        else:
            parts.append("[0:a]aresample=44100,aformat=channel_layouts=stereo[outa]")
            extra_flags = ["-shortest"]
    else:
        if total_dur > 0:
            t_total = f"{total_dur:.3f}"
            parts.append(
                f"aevalsrc=0|0:sample_rate=44100:channel_layout=stereo"
                f":duration={t_total}[outa]"
            )
        else:
            parts.append("aevalsrc=0|0:sample_rate=44100:channel_layout=stereo[outa]")
            extra_flags = ["-shortest"]

    filter_complex = ";".join(parts)

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", video1_path,
            "-i", video2_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            *extra_flags,
            output_path,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg stitch failed:\n{result.stderr[-800:]}")

    return output_path


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

        elif path == "/api/stitch-download":
            fpath = unquote(qs.get("path", [""])[0])
            self._serve_stitched_download(fpath)

        elif path == "/api/stitch-zip":
            paths_json = unquote(qs.get("paths", ["[]"])[0])
            self._handle_stitch_zip(paths_json)

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
        elif self.path == "/api/stitch-videos":
            self._handle_stitch_videos()
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

    # ── Video stitcher ────────────────────────────────────────────────────────
    def _handle_stitch_videos(self):
        """
        Batch stitch: each source video (file upload or disk path) is stitched
        with a single CTA, producing one output per source.

        Multipart mode  — fields:
          source   (file, repeatable — one per source video)
          cta      (file, single)
          source_seconds (text, default 5)

        JSON mode — body:
          {
            "folder_path": "/abs/path/to/folder",   # scan for videos
            "source_paths": ["/abs/path/v1.mp4"],    # explicit list of paths
            "cta_path": "/abs/path/cta.mp4",         # cta from disk
            "cta_url": "https://…",                  # cta from URL
            "source_seconds": 5
          }
        """
        import zipfile as _zipfile
        VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
        os.makedirs(STITCH_OUTPUT_BASE, exist_ok=True)
        tmp_dir = tempfile.mkdtemp(prefix="stitch_batch_")

        try:
            content_type = self.headers.get("Content-Type", "").lower()

            # ── resolve source paths + CTA path ───────────────────────────────
            source_paths      = []   # list of absolute paths to source videos
            cta_path          = None
            source_prefix_sec = 5.0
            source_labels     = []   # original filenames for output naming

            if "multipart/form-data" in content_type:
                length = int(self.headers.get("Content-Length", 0))
                raw    = self.rfile.read(length) if length else self.rfile.read()
                form   = _parse_multipart(self.headers.get("Content-Type", ""), raw)

                src_entries = form.get("source", [])
                cta_entries = form.get("cta",    [])
                sec_entries = form.get("source_seconds", [])
                source_prefix_sec = float(
                    (sec_entries[0]["data"].decode() if sec_entries else None) or "5"
                )

                if not src_entries:
                    self._err("No source video files received"); return
                if not cta_entries or not cta_entries[0].get("filename"):
                    self._err("multipart field 'cta' (file) is required"); return

                # Save CTA once
                ext_c    = os.path.splitext(cta_entries[0]["filename"])[1] or ".mp4"
                cta_path = os.path.join(tmp_dir, f"cta{ext_c}")
                with open(cta_path, "wb") as fh:
                    fh.write(cta_entries[0]["data"])

                # Save each source file
                for i, entry in enumerate(src_entries):
                    if not entry.get("filename"):
                        continue
                    # webkitdirectory sends relative paths like "folder/video.mp4" — strip to basename
                    base_name = os.path.basename(entry["filename"])
                    ext_s = os.path.splitext(base_name)[1] or ".mp4"
                    sp    = os.path.join(tmp_dir, f"src_{i}{ext_s}")
                    with open(sp, "wb") as fh:
                        fh.write(entry["data"])
                    source_paths.append(sp)
                    source_labels.append(os.path.splitext(base_name)[0])

            else:
                # JSON / disk-path mode
                length = int(self.headers.get("Content-Length", 0))
                raw    = self.rfile.read(length) if length else self.rfile.read()
                data   = json.loads(raw)

                source_prefix_sec = float(data.get("source_seconds", 5))

                # Resolve CTA
                cta_url_raw = (data.get("cta_url") or data.get("cta") or "").strip()
                cta_path_raw = (data.get("cta_path") or "").strip()
                if cta_path_raw and os.path.isfile(cta_path_raw):
                    cta_path = cta_path_raw
                elif cta_url_raw:
                    cta_path = os.path.join(tmp_dir, "cta.mp4")
                    req = urllib.request.Request(
                        cta_url_raw, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=120) as r:
                        with open(cta_path, "wb") as fh:
                            fh.write(r.read())
                else:
                    self._err("Provide cta_path or cta_url"); return

                # Resolve sources from folder OR explicit list
                folder_path  = (data.get("folder_path") or "").strip()
                explicit_paths = data.get("source_paths") or []

                if folder_path:
                    folder_path = os.path.expanduser(folder_path)
                    if not os.path.isdir(folder_path):
                        self._err(f"folder_path not found: {folder_path}"); return
                    for fname in sorted(os.listdir(folder_path)):
                        ext = os.path.splitext(fname.lower())[1]
                        if ext in VIDEO_EXTS:
                            source_paths.append(os.path.join(folder_path, fname))
                            source_labels.append(os.path.splitext(fname)[0])
                elif explicit_paths:
                    for p in explicit_paths:
                        p = os.path.expanduser(p)
                        if os.path.isfile(p):
                            source_paths.append(p)
                            source_labels.append(
                                os.path.splitext(os.path.basename(p))[0])
                else:
                    self._err("Provide folder_path or source_paths"); return

            if not source_paths:
                self._err("No valid source video files found"); return
            if not cta_path or not os.path.exists(cta_path):
                self._err("CTA video is missing or empty"); return

            source_prefix_sec = max(0.1, min(source_prefix_sec, 3600.0))

            # ── Stitch each source with CTA ────────────────────────────────────
            results = []
            for i, src_path in enumerate(source_paths):
                label = source_labels[i] if i < len(source_labels) else f"video_{i}"
                # Sanitize: strip directory separators and characters that break filenames
                safe_label = os.path.basename(label)
                safe_label = "".join(c if c.isalnum() or c in "-_. #" else "_" for c in safe_label)
                safe_label = safe_label[:60] or f"video_{i}"
                out_name = f"stitched_{safe_label}_{uuid.uuid4().hex[:8]}.mp4"
                out_path = os.path.join(STITCH_OUTPUT_BASE, out_name)
                print(f"  [stitch {i+1}/{len(source_paths)}] {label} → {out_name}")
                try:
                    _stitch_videos_ffmpeg(
                        src_path, cta_path, out_path,
                        gap_seconds=0,
                        source_prefix_seconds=source_prefix_sec,
                    )
                    results.append({
                        "label":             label,
                        "filename":          out_name,
                        "stitched_filepath": out_path,
                        "download_url":      f"/api/stitch-download?path={urllib.parse.quote(out_path)}",
                        "ok":                True,
                    })
                    # Verify output dimensions
                    _vfy = subprocess.run(
                        ["ffprobe", "-v", "error", "-select_streams", "v:0",
                         "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", out_path],
                        capture_output=True, text=True,
                    )
                    print(f"  [stitch] ✓ {out_name}  (output dims: {_vfy.stdout.strip()})")
                except Exception as e:
                    results.append({
                        "label": label,
                        "ok":    False,
                        "error": str(e)[:200],
                    })
                    print(f"  [stitch] ✗ {label}: {e}")

            # Build a zip_url covering all successful outputs
            ok_paths = [r["stitched_filepath"] for r in results if r.get("ok")]
            zip_url  = ""
            if len(ok_paths) > 1:
                paths_param = urllib.parse.quote(json.dumps(ok_paths))
                zip_url = f"/api/stitch-zip?paths={paths_param}"

            self._ok(json.dumps({
                "total":          len(results),
                "succeeded":      sum(1 for r in results if r.get("ok")),
                "source_seconds": source_prefix_sec,
                "results":        results,
                "zip_url":        zip_url,
            }).encode())

        except RuntimeError as e:
            self._err(f"FFmpeg stitching failed: {e}")
        except Exception as e:
            self._err(f"Stitch error: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _handle_stitch_zip(self, paths_json: str):
        """
        Stream a ZIP of all stitched files whose paths are in paths_json.
        Only files inside STITCH_OUTPUT_BASE are served (security check).
        """
        import zipfile as _zipfile, io as _io
        try:
            paths     = json.loads(paths_json)
            real_base = os.path.realpath(STITCH_OUTPUT_BASE)
            buf       = _io.BytesIO()
            with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
                for p in paths:
                    p = os.path.realpath(p)
                    if not p.startswith(real_base):
                        continue
                    if not os.path.isfile(p):
                        continue
                    zf.write(p, os.path.basename(p))
            zip_bytes = buf.getvalue()
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(zip_bytes)))
            self.send_header("Content-Disposition",
                             'attachment; filename="stitched_videos.zip"')
            self._cors()
            self.end_headers()
            self.wfile.write(zip_bytes)
        except Exception as e:
            self._err(str(e))

    def _serve_stitched_download(self, file_path: str):
        """Stream a stitched video file back to the browser as a download."""
        file_path = os.path.expanduser(file_path.strip())
        # Safety: only serve files inside STITCH_OUTPUT_BASE
        real_path = os.path.realpath(file_path)
        real_base = os.path.realpath(STITCH_OUTPUT_BASE)
        if not real_path.startswith(real_base):
            self.send_response(403)
            self._cors()
            self.end_headers()
            return
        if not os.path.isfile(real_path):
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        mime = mimetypes.guess_type(real_path)[0] or "video/mp4"
        filename = os.path.basename(real_path)
        try:
            with open(real_path, "rb") as fh:
                data = fh.read()
        except Exception as e:
            self._err(str(e))
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self._cors()
        self.end_headers()
        self.wfile.write(data)

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