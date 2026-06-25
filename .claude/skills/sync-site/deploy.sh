#!/usr/bin/env bash
# deploy.sh — re-apply ALL deploy-only transforms after pulling the *.dc.html pages
# from Claude Design (via extract-pulled.py), then verify. Idempotent.
#
# Pipeline order is critical (see SKILL.md):
#   cp Home->index -> home-link ./ -> patch-contact-form -> seo-clean-urls
#   -> rename *.dc.html->*.html (+ rm Home) -> bump sitemap -> verify
#
# Does NOT touch the permanent repo files (404.html, services.html,
# keynotes-speaker.html, CNAME, robots.txt, llms.txt, support.js) — those are not
# from Design and must survive every sync.
#
# Usage:  bash .claude/skills/sync-site/deploy.sh      (run from anywhere)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"
cd "$REPO"

HOME_SRC="Gregory Renard - Home v2.dc.html"
SUBPAGES="AI-Lab AI-Transformation Advisory-Execution Contact Ethics Keynote-Speaker Method Press Publications Why"

[ -f "$HOME_SRC" ] || { echo "ERROR: '$HOME_SRC' not found — run extract-pulled.py first."; exit 1; }

echo "==> 1/6  clean root: index.html = home page"
cp "$HOME_SRC" index.html

echo "==> 2/6  rewrite home link -> ./  (href + JS url forms, quote-anchored)"
# v3 home file is "… - Home v2.dc.html"; also keep the legacy "- Home" form (no-op if absent)
sed -i '' 's|"Gregory%20Renard%20-%20Home%20v2\.dc\.html"|"./"|g' *.dc.html index.html
sed -i '' "s|'Gregory%20Renard%20-%20Home%20v2\.dc\.html'|'./'|g" *.dc.html index.html
sed -i '' 's|"Gregory%20Renard%20-%20Home\.dc\.html"|"./"|g' *.dc.html index.html
sed -i '' "s|'Gregory%20Renard%20-%20Home\.dc\.html'|'./'|g" *.dc.html index.html

echo "==> 3/6  wire contact form -> Google Sheet (+ honeypot)"
python3 "$SKILL_DIR/patch-contact-form.py"

echo "==> 3b/6 enrich SEO: 'AI pioneer' title/description + rich Person JSON-LD (home + Why)"
python3 "$SKILL_DIR/enrich-seo.py"

echo "==> 4/6  clean URLs + static SEO head"
python3 "$SKILL_DIR/seo-clean-urls.py"

echo "==> 4b/6 mobile hero-wrap fix (let hero titles wrap < 900px instead of shrinking)"
python3 "$SKILL_DIR/hero-wrap-fix.py"

echo "==> 5/6  rename *.dc.html -> *.html (+ drop redundant home source)"
for f in $SUBPAGES; do [ -f "$f.dc.html" ] && mv "$f.dc.html" "$f.html"; done
rm -f "$HOME_SRC"

echo "==> 6/6  bump sitemap <lastmod> to today"
TODAY="$(date +%F)"
sed -i '' "s|<lastmod>[^<]*</lastmod>|<lastmod>$TODAY</lastmod>|g" sitemap.xml

echo "==> 7/7  static pre-render (headless): real content for no-JS / non-JS crawlers"
python3 "$SKILL_DIR/prerender.py"

echo
bash "$SKILL_DIR/verify.sh"
