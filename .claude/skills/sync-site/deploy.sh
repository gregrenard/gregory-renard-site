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

HOME_SRC="Gregory Renard - Home.dc.html"
SUBPAGES="AI-Lab AI-Transformation Advisory-Execution Contact Ethics Keynote-Speaker Press Publications Why"

[ -f "$HOME_SRC" ] || { echo "ERROR: '$HOME_SRC' not found — run extract-pulled.py first."; exit 1; }

echo "==> 1/6  clean root: index.html = home page"
cp "$HOME_SRC" index.html

echo "==> 2/6  rewrite home link -> ./  (href + JS url forms, quote-anchored)"
sed -i '' 's|"Gregory%20Renard%20-%20Home\.dc\.html"|"./"|g' *.dc.html index.html
sed -i '' "s|'Gregory%20Renard%20-%20Home\.dc\.html'|'./'|g" *.dc.html index.html

echo "==> 2b/6 reconcile footer label (TEMPORARY — remove once fixed in Claude Design)"
# Claude Design's footer 'Navigate' column still labels the Advisory-Execution page
# 'Work together' / 'Travailler ensemble', but the user reconciled the TOP nav to
# 'Advisory & Execution' / 'Conseil & Exécution'. Keep them consistent until the
# footer is updated in Claude Design too. Anchored to "label: '...'" so it only
# touches the footer items. Idempotent -> becomes a no-op once Design is fixed;
# DELETE this step then. (Tracked in SKILL.md "Pending Claude Design fixes".)
sed -i '' "s/label: 'Work together'/label: 'Advisory \& Execution'/g" *.dc.html index.html
sed -i '' "s/label: 'Travailler ensemble'/label: 'Conseil \& Exécution'/g" *.dc.html index.html

echo "==> 3/6  wire contact form -> Google Sheet (+ honeypot)"
python3 "$SKILL_DIR/patch-contact-form.py"

echo "==> 4/6  clean URLs + static SEO head"
python3 "$SKILL_DIR/seo-clean-urls.py"

echo "==> 5/6  rename *.dc.html -> *.html (+ drop redundant home source)"
for f in $SUBPAGES; do [ -f "$f.dc.html" ] && mv "$f.dc.html" "$f.html"; done
rm -f "$HOME_SRC"

echo "==> 6/6  bump sitemap <lastmod> to today"
TODAY="$(date +%F)"
sed -i '' "s|<lastmod>[^<]*</lastmod>|<lastmod>$TODAY</lastmod>|g" sitemap.xml

echo
bash "$SKILL_DIR/verify.sh"
