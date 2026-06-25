#!/usr/bin/env bash
# verify.sh — post-deploy sanity checks. Exits non-zero if anything is wrong.
# Safe to run standalone:  bash .claude/skills/sync-site/verify.sh
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"
cd "$REPO"

SUBPAGES="AI-Lab AI-Transformation Advisory-Execution Contact Ethics Keynote-Speaker Method Press Publications Why"
# Full content pages carry the static SEO head; these 3 are intentional redirect
# stubs (AI-Lab/Advisory-Execution -> freedom.ai, AI-Transformation -> /Method)
# with only <title> + a meta refresh, so they're excluded from the og:title check.
CONTENT="Contact Ethics Keynote-Speaker Method Press Publications Why"
fail=0

echo "--- (a) extension gone + no accidental .// ---"
if grep -rl "\.dc\.html" *.html >/dev/null 2>&1; then echo "  BAD: .dc.html still present"; fail=1; else echo "  ok: extensionless"; fi
if grep -rn '\.//' *.html >/dev/null 2>&1;        then echo "  BAD: .// found";            fail=1; else echo "  ok: no .//"; fi

echo "--- (b) index.html is the homepage (not a redirect) ---"
[ "$(grep -c 'http-equiv="refresh"' index.html)" = "0" ] && echo "  ok: no refresh redirect" || { echo "  BAD: index has refresh"; fail=1; }
[ "$(grep -c '<x-dc>' index.html)" -ge 1 ]               && echo "  ok: <x-dc> present"      || { echo "  BAD: no <x-dc>"; fail=1; }

echo "--- (c) static SEO present: each content page has <title> + og:title inside <head> ---"
cfail=0
for f in index.html $(for n in $CONTENT; do echo "$n.html"; done); do
  h=$(awk 'BEGIN{p=1}/<body/{p=0}{if(p)print}' "$f")
  if echo "$h" | grep -q "<title>" && echo "$h" | grep -q "og:title"; then :; else echo "  MISS seo-head: $f"; fail=1; cfail=1; fi
done
[ $cfail -eq 0 ] && echo "  ok: all content pages have <title> + og:title in <head>"
echo "--- (c2) redirect stubs carry a refresh + canonical ---"
for n in AI-Lab AI-Transformation Advisory-Execution; do
  [ -f "$n.html" ] || continue
  if grep -q 'http-equiv="refresh"' "$n.html" && grep -q 'rel="canonical"' "$n.html"; then echo "  ok: $n redirect stub"; else echo "  WARN: $n missing refresh/canonical"; fi
done

echo "--- (d) every internal page link resolves to a .html file ---"
for n in $SUBPAGES; do
  if grep -qhoE "href=\"$n\"|url: '$n'" *.html 2>/dev/null; then
    [ -f "$n.html" ] && echo "  ok: $n" || { echo "  MISS: $n.html"; fail=1; }
  fi
done

echo "--- (e) every local asset reference resolves ---"
for t in $(grep -rhoE "assets/[A-Za-z0-9%@_.-]+\.(png|jpg|jpeg|webp|gif|svg|mp4|pdf)" *.html 2>/dev/null | sort -u); do
  [ -f "$t" ] && echo "  ok: $t" || { echo "  MISS: $t"; fail=1; }
done

echo "--- (f) permanent redirect / SEO files intact (must NOT be clobbered by a sync) ---"
for pf in 404.html services.html keynotes-speaker.html CNAME robots.txt sitemap.xml llms.txt support.js; do
  [ -f "$pf" ] && echo "  ok: $pf" || { echo "  BAD: $pf MISSING"; fail=1; }
done
# 404.html must still carry its migration redirect logic
grep -q "location.replace" 404.html 2>/dev/null && echo "  ok: 404.html redirect logic present" || { echo "  BAD: 404.html redirect logic gone"; fail=1; }

echo "--- (g) footer label consistent with top nav ---"
if grep -rq "label: 'Work together'\|label: 'Travailler ensemble'" *.html 2>/dev/null; then
  echo "  WARN: footer says 'Work together'/'Travailler ensemble' but the top nav says"
  echo "        'Advisory & Execution' — fix the footer label in Claude Design."
else
  echo "  ok: footer label matches top nav"
fi

echo
[ $fail -eq 0 ] && echo "VERIFY: all checks passed ✅" || echo "VERIFY: FAILURES above ❌"
exit $fail
