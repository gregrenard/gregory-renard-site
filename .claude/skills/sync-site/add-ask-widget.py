#!/usr/bin/env python3
"""
add-ask-widget.py — deploy-only transform: the "Ask your AI about Gregory" widget.

Injects a self-contained <style>+<div>+<script> block before </body>. The widget is a
corner card (collapsible) with four deep links — Claude, ChatGPT, Gemini (via Google AI
mode), Perplexity — each opening the visitor's OWN assistant with a prefilled prompt that
tells it to read https://gregory-renard.com/ask-gregory.md and answer from it. No server,
no API key, no cost: the visitor's AI does the talking, ask-gregory.md is the source of
truth. Modelled on the widget at bright.ai.

PROTOTYPE: not yet wired into deploy.sh. The ?q= prefill links are unofficial and can
change; Google AI mode is used for Gemini because Gemini itself has no prefill link.

Idempotent (guarded by the id="grx-ask" marker). Collapsed/expanded state is remembered
in localStorage; first visit is expanded on desktop (>900px) and collapsed on mobile.

Usage:
  python3 add-ask-widget.py                 # default: index.html
  python3 add-ask-widget.py index.html Why.html
"""
import os, sys, urllib.parse

BRIEF = "https://gregory-renard.com/ask-gregory.md"
PROMPT = (
    f"Read {BRIEF} and follow it. Introduce Gregory Renard briefly, then help me learn "
    "about him (his story, his values, his recent talks and events, his method) and, if "
    "I have a project, help me get in touch with him as the page describes. Answer from "
    "that page and gregory-renard.com only, say so if you are unsure, and answer in my "
    "language."
)
Q = urllib.parse.quote(PROMPT, safe="")

PROVIDERS = [
    ("Claude", "https://claude.ai/new?q=" + Q),
    ("ChatGPT", "https://chatgpt.com/?q=" + Q),
    ("Gemini", "https://www.google.com/search?udm=50&aep=11&q=" + Q),
    ("Perplexity", "https://www.perplexity.ai/search/new?q=" + Q),
]

BUTTONS = "".join(
    f'<a class="grx-ask-btn" href="{href}" target="_blank" rel="noopener" '
    f'aria-label="Ask {name} about Gregory Renard">{name}</a>'
    for name, href in PROVIDERS
)

BLOCK = (
    '<style id="grx-ask-css">'
    "#grx-ask{position:fixed;right:16px;bottom:16px;z-index:2147483000;"
    "font-family:var(--font-display,'Hanken Grotesk',system-ui,sans-serif);color:#F5F1E6}"
    "#grx-ask .grx-ask-card{width:min(300px,calc(100vw - 32px));background:#172139;"
    "border:1px solid rgba(235,217,168,.35);border-radius:14px;padding:18px 18px 16px;"
    "box-shadow:0 12px 40px rgba(23,33,57,.35)}"
    "#grx-ask .grx-ask-title{font-size:20px;line-height:1.2;font-weight:600;margin:0 28px 8px 0}"
    "#grx-ask .grx-ask-text{font-size:14px;line-height:1.45;margin:0 0 14px;"
    "color:rgba(245,241,230,.78)}"
    "#grx-ask .grx-ask-row{display:flex;flex-wrap:wrap;gap:8px}"
    "#grx-ask .grx-ask-btn{display:inline-block;padding:8px 12px;border-radius:8px;"
    "background:#F5F1E6;color:#172139;font-size:13px;font-weight:600;text-decoration:none}"
    "#grx-ask .grx-ask-btn:hover{background:#EBD9A8}"
    "#grx-ask .grx-ask-min{position:absolute;top:10px;right:10px;width:26px;height:26px;"
    "border-radius:50%;border:1px solid rgba(235,217,168,.45);background:transparent;"
    "color:#F5F1E6;font-size:16px;line-height:1;cursor:pointer}"
    "#grx-ask .grx-ask-pill{display:none;align-items:center;gap:8px;cursor:pointer;"
    "background:#172139;color:#F5F1E6;border:1px solid rgba(235,217,168,.45);"
    "border-radius:999px;padding:10px 16px;font:inherit;font-size:14px;font-weight:600;"
    "box-shadow:0 8px 28px rgba(23,33,57,.3)}"
    "#grx-ask.grx-collapsed .grx-ask-card{display:none}"
    "#grx-ask.grx-collapsed .grx-ask-pill{display:inline-flex}"
    "@media print{#grx-ask{display:none}}"
    "</style>"
    '<div id="grx-ask" role="complementary" aria-label="Ask your AI about Gregory Renard">'
    '<div class="grx-ask-card">'
    '<button type="button" class="grx-ask-min" aria-label="Minimize">&minus;</button>'
    '<p class="grx-ask-title">Ask your AI about Gregory</p>'
    '<p class="grx-ask-text">Explore my story, my work, my recent talks and what I stand '
    "for &mdash; in a conversation with your own AI assistant.</p>"
    f'<div class="grx-ask-row">{BUTTONS}</div>'
    "</div>"
    '<button type="button" class="grx-ask-pill">Ask your AI about Gregory</button>'
    "</div>"
    "<script>(function(){"
    "var el=document.getElementById('grx-ask'),K='grx-ask-state',s=null;"
    "try{s=localStorage.getItem(K)}catch(e){}"
    "function set(c){el.classList.toggle('grx-collapsed',c);"
    "try{localStorage.setItem(K,c?'collapsed':'open')}catch(e){}}"
    "el.classList.toggle('grx-collapsed',s?s==='collapsed':window.innerWidth<=900);"
    "el.querySelector('.grx-ask-min').addEventListener('click',function(){set(true)});"
    "el.querySelector('.grx-ask-pill').addEventListener('click',function(){set(false)});"
    "})();</script>"
)


def main():
    files = sys.argv[1:] or ["index.html"]
    n = 0
    for f in files:
        if not os.path.exists(f):
            continue
        s = open(f, encoding="utf-8").read()
        if 'id="grx-ask"' in s or "</body>" not in s:
            continue
        s = s.replace("</body>", BLOCK + "\n</body>", 1)
        open(f, "w", encoding="utf-8", newline="").write(s)
        n += 1
        print("  ask widget:", f)
    print("ask-widget: %d file(s) patched" % n)


if __name__ == "__main__":
    main()
