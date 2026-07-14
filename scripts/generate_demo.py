"""Demo animated SVG for timecapsule — shows the timeline browser TUI
with narrative commit messages scrolling through the timeline."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SVG = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600" width="800" height="600">
  <defs>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&amp;display=swap');
      text { font-family: 'JetBrains Mono', 'Courier New', monospace; }
      @keyframes fadeIn { 0% { opacity: 0; } 100% { opacity: 1; } }
      @keyframes slideIn { 0% { transform: translateY(-20px); opacity: 0; } 100% { transform: translateY(0); opacity: 1; } }
      @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      @keyframes scrollLog {
        0% { transform: translateY(0); }
        100% { transform: translateY(-120px); }
      }
      @keyframes pulse { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; } }
      .title { animation: fadeIn 0.8s ease-out both; }
      .panel { animation: fadeIn 1s ease-out 0.3s both; }
      .file-item { animation: slideIn 0.5s ease-out both; }
      .file-item:nth-child(1) { animation-delay: 0.5s; }
      .file-item:nth-child(2) { animation-delay: 0.7s; }
      .file-item:nth-child(3) { animation-delay: 0.9s; }
      .file-item:nth-child(4) { animation-delay: 1.1s; }
      .file-item:nth-child(5) { animation-delay: 1.3s; }
      .commit-item { animation: slideIn 0.4s ease-out both; }
      .commit-item:nth-child(1) { animation-delay: 1.5s; }
      .commit-item:nth-child(2) { animation-delay: 1.8s; }
      .commit-item:nth-child(3) { animation-delay: 2.1s; }
      .commit-item:nth-child(4) { animation-delay: 2.4s; }
      .commit-item:nth-child(5) { animation-delay: 2.7s; }
      .commit-item:nth-child(6) { animation-delay: 3.0s; }
      .scroll-area { animation: scrollLog 12s ease-in-out 1.5s infinite alternate; }
      .blink-dot { animation: blink 2s ease-in-out infinite; }
      .pulse { animation: pulse 2s ease-in-out infinite; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="800" height="600" fill="#0a0a0a" rx="4"/>

  <!-- Header -->
  <rect x="0" y="0" width="800" height="28" fill="#00aa55" class="title"/>
  <text x="15" y="19" fill="#000" font-size="13" font-weight="bold" class="title">timecapsule — Timeline Browser</text>
  <text x="785" y="19" fill="#000" font-size="10" text-anchor="end" class="title">📁 47 snapshots</text>

  <!-- File list panel (left sidebar) -->
  <rect x="8" y="34" width="180" height="480" fill="#0d1a12" stroke="#00ff88" stroke-width="1" rx="2" class="panel"/>
  <text x="16" y="54" fill="#00ff88" font-size="11" font-weight="bold" class="title">📁 Tracked Files</text>
  <line x1="10" y1="60" x2="186" y2="60" stroke="#00ff88" stroke-width="0.5" opacity="0.3"/>

  <g class="file-item" font-size="10">
    <rect x="10" y="66" width="176" height="20" fill="#00ff88" opacity="0.15" rx="2"/>
    <text x="20" y="80" fill="#00ff88" font-weight="bold">app.py — Initialized Flask</text>

    <rect x="10" y="88" width="176" height="18" fill="none"/>
    <text x="20" y="100" fill="#aaa">main.py — Refactored routing</text>

    <rect x="10" y="108" width="176" height="18" fill="none"/>
    <text x="20" y="120" fill="#aaa">config.py — Fixed CORS bug</text>

    <rect x="10" y="128" width="176" height="18" fill="none"/>
    <text x="20" y="140" fill="#aaa">styles.css — Header gradient</text>

    <rect x="10" y="148" width="176" height="18" fill="none"/>
    <text x="20" y="160" fill="#666">utils.py — Moved to helpers/</text>

    <rect x="10" y="168" width="176" height="18" fill="none"/>
    <text x="20" y="180" fill="#666">test_api.py — Wrote integration</text>
  </g>

  <!-- Timeline panel (center) -->
  <rect x="194" y="34" width="410" height="480" fill="#1a0f05" stroke="#ff8800" stroke-width="1" rx="2" class="panel"/>
  <text x="202" y="54" fill="#ff8800" font-size="11" font-weight="bold" class="title">📜 Timeline — app.py</text>
  <line x1="196" y1="60" x2="602" y2="60" stroke="#ff8800" stroke-width="0.5" opacity="0.3"/>

  <!-- Scrolling commit messages -->
  <g clip-path="url(#timelineClip)">
    <clipPath id="timelineClip">
      <rect x="194" y="62" width="410" height="450"/>
    </clipPath>
    <g class="scroll-area" font-size="10">
      <!-- Commit entries -->
      <g class="commit-item">
        <circle cx="214" cy="88" r="4" fill="#ff8800"/>
        <text x="226" y="84" fill="#888" font-size="8">Jul 14, 23:15</text>
        <text x="226" y="96" fill="#ddd" font-weight="bold" font-size="10">Initialized Flask app with Blueprint structure</text>
      </g>

      <g class="commit-item">
        <circle cx="214" cy="128" r="4" fill="#ff8800"/>
        <text x="226" y="124" fill="#888" font-size="8">Jul 14, 22:58</text>
        <text x="226" y="136" fill="#ddd" font-weight="bold" font-size="10">Added CORS middleware after the frontend team</text>
        <text x="226" y="150" fill="#aaa" font-size="9">reported cross-origin errors in staging</text>
      </g>

      <g class="commit-item">
        <circle cx="214" cy="180" r="4" fill="#ff8800"/>
        <text x="226" y="176" fill="#888" font-size="8">Jul 14, 22:12</text>
        <text x="226" y="188" fill="#ddd" font-weight="bold" font-size="10">Refactored auth routes into their own module</text>
        <text x="226" y="202" fill="#aaa" font-size="9">— cleaned up app.py which was getting bloated</text>
      </g>

      <g class="commit-item">
        <circle cx="214" cy="230" r="4" fill="#ff8800"/>
        <text x="226" y="226" fill="#888" font-size="8">Jul 14, 21:45</text>
        <text x="226" y="238" fill="#ddd" font-weight="bold" font-size="10">Fixed the login redirect loop — was sending</text>
        <text x="226" y="252" fill="#aaa" font-size="9">authenticated users back to /login indefinitely</text>
      </g>

      <g class="commit-item">
        <circle cx="214" cy="280" r="4" fill="#ff8800"/>
        <text x="226" y="276" fill="#888" font-size="8">Jul 14, 20:30</text>
        <text x="226" y="288" fill="#ddd" font-weight="bold" font-size="10">Renamed users.py to auth.py to better reflect</text>
        <text x="226" y="302" fill="#aaa" font-size="9">its scope—now handles both auth and profiles</text>
      </g>

      <g class="commit-item">
        <circle cx="214" cy="330" r="4" fill="#ff8800"/>
        <text x="226" y="326" fill="#888" font-size="8">Jul 14, 19:10</text>
        <text x="226" y="338" fill="#ddd" font-weight="bold" font-size="10">Switched from parse() to tokenize() after</text>
        <text x="226" y="352" fill="#aaa" font-size="9">deciding to handle plain text first — removed</text>
        <text x="226" y="366" fill="#aaa" font-size="9">unused XML import to silence the linter</text>
      </g>

      <g class="commit-item">
        <circle cx="214" cy="400" r="4" fill="#ff8800"/>
        <text x="226" y="396" fill="#888" font-size="8">Jul 14, 17:00</text>
        <text x="226" y="408" fill="#ddd" font-weight="bold" font-size="10">Adjusted the header gradient after client</text>
        <text x="226" y="422" fill="#aaa" font-size="9">feedback, then reverted the logo size because</text>
        <text x="226" y="436" fill="#aaa" font-size="9">it broke the mobile layout</text>
      </g>
    </g>
  </g>

  <!-- Diff panel (bottom) -->
  <rect x="8" y="520" width="784" height="72" fill="#0a0a0a" stroke="#444" stroke-width="1" rx="2" class="panel"/>
  <text x="16" y="536" fill="#888" font-size="10">📄 Diff — app.py @ [23:15] Added CORS middleware</text>
  <text x="16" y="553" fill="#55ff55" font-size="9" font-family="monospace">
    <tspan x="16" dy="0">+ from flask_cors import CORS</tspan>
    <tspan x="16" dy="14">+ CORS(app, origins=[\"https://frontend.internal\"])</tspan>
    <tspan x="16" dy="14" fill="#ff5555">- # TODO: add CORS support</tspan>
  </text>

  <!-- Status bar -->
  <rect x="0" y="595" width="800" height="5" fill="#00ff88" opacity="0.3"/>
</svg>'''


def generate(output_path: str = None) -> str:
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "..", "timecapsule_demo.svg")
    output_path = os.path.normpath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(SVG)
    return output_path


if __name__ == "__main__":
    path = generate()
    print(f"Demo SVG: {path}")
