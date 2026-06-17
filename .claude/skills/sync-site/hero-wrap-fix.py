#!/usr/bin/env python3
"""
hero-wrap-fix.py — deploy-only CSS override.

Claude Design sets `white-space:nowrap` on several hero <h1> titles (and uses the
`.grx-hero-h1` class). On narrow screens that forces the title onto one line and
shrinks it down to its clamp() minimum (~16px), which reads badly on mobile.

This injects a tiny override <style> before </head> so those titles wrap normally
below 900px (the site's own mobile breakpoint). `!important` beats the inline
`white-space:nowrap`. Desktop (>900px) keeps the intended one-line look. Idempotent.

Usage:
  python3 hero-wrap-fix.py                 # deploy context: *.dc.html + index.html
  python3 hero-wrap-fix.py *.html          # one-off on already-deployed pages
"""
import glob, sys, os

CSS = ('<style id="grx-hero-wrap-fix">'
       '@media (max-width:900px){'
       'h1[style*="nowrap"],.grx-hero-h1{white-space:normal!important}'
       '}</style>')


def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else (glob.glob("*.dc.html") + ["index.html"])
    seen, n = set(), 0
    for f in files:
        if f in seen or not os.path.exists(f):
            continue
        seen.add(f)
        s = open(f, encoding="utf-8").read()
        if "grx-hero-wrap-fix" in s:
            continue
        if "</head>" in s:
            s = s.replace("</head>", CSS + "\n</head>", 1)
            open(f, "w", encoding="utf-8", newline="").write(s)
            n += 1
            print("  hero-wrap fix:", f)
    print("hero-wrap: %d file(s) patched" % n)


if __name__ == "__main__":
    main()
