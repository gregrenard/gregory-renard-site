---
name: sync-site
description: Sync the gregory-renard.com site from Claude Design to GitHub so the live site updates, re-applying deploy-only fixes (clean root URL) that Claude Design can't do. Use when the user has edited pages in claude.ai/design and wants the changes published — triggers like "sync the site", "j'ai modifié dans Claude Design", "publie / mets à jour le site", "push my edits", "déploie le site".
---

# Sync site — Claude Design → GitHub (with deploy-only fixes)

Pull the latest **text** content from the user's Claude Design project, **re-apply the deploy-only transforms** Claude Design can't do (clean root URL), verify all internal links, then push to GitHub. GitHub Pages redeploys the live site automatically (~1 min).

## Automated flow (do this — 3 scripts + the DesignSync pulls)
Once the user confirms editing is **finished**:
1. **Detect structure changes:** `DesignSync list_files` → confirm the 10 page filenames are unchanged. A renamed/added/removed page changes a URL (SEO + redirect impact) — handle that before continuing.
2. **Pull pages:** `DesignSync get_file` for each of the 10 root pages (full resync) or just the edited ones. Pull first so results flush to the transcript.
3. **Write them byte-exact:** `python3 .claude/skills/sync-site/extract-pulled.py`  (reads the transcript: inline + persisted .txt, freshest wins).
4. **Transform + verify in one shot:** `bash .claude/skills/sync-site/deploy.sh`  (full pipeline → then `verify.sh`).
   - If verify flags a **MISSING asset** (image changed/added in Design, ≤256 KiB): `DesignSync get_file assets/<file>` → `python3 .claude/skills/sync-site/pull-asset.py assets/<file>` → re-run `bash .claude/skills/sync-site/verify.sh`. (>256 KiB → ask the user to send the file.)
5. **Review + ship:** `git diff -U0 -- '*.html'` to eyeball the real content delta, then `git add -A && git commit && git push origin main`. Remind the user to open `/` in a browser to confirm the dc-runtime renders.

Everything below is the reference for what those scripts do.

## Project facts
- **Source of truth:** Claude Design project **"gregory-renard.com"**, projectId `25751aee-ab2f-4af9-a3b3-66cf466244c4`. The user edits the **root-level** components there.
- **Repo / remote:** `origin/main` → `github.com/gregrenard/gregory-renard-site` (this working directory).
- **Live site:** https://gregory-renard.com (custom domain, HTTPS; also reachable at https://gregrenard.github.io/gregory-renard-site).
- **DesignSync is READ-ONLY for this project** (type `PROJECT_TYPE_PROJECT`). NEVER call `write_files`/`finalize_plan`/`delete_files` against it — only `list_files` and `get_file`.

## Syncable files (TEXT only)
Root-level files that map 1:1 to the repo root and pull via DesignSync `get_file`:

- The 10 pages: `AI-Lab.dc.html`, `AI-Transformation.dc.html`, `Advisory-Execution.dc.html`, `Contact.dc.html`, `Ethics.dc.html`, `Gregory Renard - Home.dc.html`, `Keynote-Speaker.dc.html`, `Press.dc.html`, `Publications.dc.html`, `Why.dc.html`
- `support.js`, `sitemap.xml`, `robots.txt`, `llms.txt`
- NOTE: do NOT pull Design's `index.html` (it's a redirect stub). In the repo, `index.html` is a **generated deploy artifact** — see "Deploy-only transforms" below.

⚠️ **Binaries cannot be synced.** `get_file` is capped at 256 KiB, so `assets/*.png|jpg|pdf|mp4` (images, keynote PDF, video) will NOT come through. They are already in the repo. If the user says they changed an image or the video in Design, tell them it must be transferred **manually** (have them send/point you to the new file) — DesignSync can't pull it.

## Steps
1. **Confirm editing is finished.** DesignSync reads the live project — if the user is still editing, content changes between reads (verified: a page's nav order / hero sizing shifted between two pulls). Ask them to confirm "done" before a full pull, or you'll capture a half-edited snapshot.
2. **Scope:** if the user named specific page(s), pull only those. If they say "everything"/"tout" or don't specify, pull all the text files above.
3. **Pull (byte-exact, no retyping):** `DesignSync get_file` each in-scope file.
   - Large results (≈>50 KB, e.g. Home) auto-persist to a `tool-results/<toolu_…>.txt` file — the result gives the path. `python3 -c "import json;print(json.load(open(P))['content'],end='')"` → write to disk.
   - Smaller pages come back **inline**. DO NOT hand-retype them (corruption risk on a live site). Instead extract them byte-exact from the session transcript JSONL at `~/.claude/projects/<proj>/<session-id>.jsonl`: parse each line, walk for string values starting with `{"method":"get_file"`, json-parse, keep the **last** occurrence per path (= freshest). Write each `content` to disk. (Pull first, extract in a later step so the results are flushed to the JSONL.) Verify freshness with a known marker from the new edit before trusting it.
4. **Reconcile:** overwrite the local pages with the pulled versions, then **re-apply the deploy-only transforms** (clean root + home-link → `./`) — see next section. `git diff` is then the source of truth for what really changed.
5. **Binary assets** (images/video changed in Design): try `get_file` — if it returns `isBase64:true` and `truncated:false`, base64-decode and write to `assets/`. If `truncated` (file >256 KiB), it CANNOT be pulled — keep the previous working ref for that spot (don't commit a broken ref) and ask the user to upload the file manually.
6. **Verify** internal links AND asset existence — see "Verify".
7. If nothing changed at all, stop and tell the user "no changes to push".
8. Otherwise `git add -A`, commit (message listing what changed), end the message with:
   ```
   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
   then `git push origin main`.
9. Report files updated + confirm push. Remind the user GitHub Pages redeploys in ~1 min, and to **open `/` in a browser to confirm rendering** (curl proves bytes served, not that the dc-runtime rendered — check console for `[dc-runtime] … failed`). Restate any asset still needing manual upload.

## Deploy-only transforms (what Claude Design can't do)
Claude Design's `index.html` is a redirect and its pages link to the home as `Gregory%20Renard%20-%20Home.dc.html` (a redirect + an ugly `%20` URL). For a clean root URL we maintain two deploy-only edits **in the repo** that must be re-applied every time pages are pulled, because a fresh pull reverts them:

1. **Clean root:** make `index.html` a direct copy of the home page (no redirect):
   ```bash
   cp "Gregory Renard - Home.dc.html" index.html
   ```
   (Verified safe: `support.js`'s `boot()` adopts the inline `<x-dc>` block, and the pages have no sibling-component references — only `<a href>` links — so rendering doesn't depend on the filename.)
2. **Rewrite the home link to `./`** across every page (both the `href="…"` form and the `url: '…'` form inside the `<script data-dc-script>` JS arrays). Quote-anchored so it can't produce `.//`:
   ```bash
   sed -i '' 's|"Gregory%20Renard%20-%20Home\.dc\.html"|"./"|g' *.dc.html index.html
   sed -i '' "s|'Gregory%20Renard%20-%20Home\.dc\.html'|'./'|g" *.dc.html index.html
   ```
3. **Wire the Contact form to the Google Sheet endpoint.** Claude Design's "Let's Build" form does nothing on submit (just shows "Message received") — re-apply the idempotent patch that POSTs it to the Apps Script Web App:
   ```bash
   python3 .claude/skills/sync-site/patch-contact-form.py
   ```
   (Posts firstName/lastName/email/message via `fetch(..., {mode:'no-cors'})` to a Google Apps Script `/exec` that appends a row to the contacts sheet. Endpoint lives in that script; update it there if the deployment changes.)

4. **Clean URLs + static SEO** — run on every `*.dc.html` + `index.html`, AFTER the home-link rewrite and the contact-form patch, BEFORE renaming:
   ```bash
   python3 .claude/skills/sync-site/seo-clean-urls.py
   ```
   Strips the `.dc.html` extension from all links/canonical/og:url, copies each page's `<helmet>` into the real `<head>` (so non-JS crawlers + social/AI scrapers get title/description/canonical/og/twitter/JSON-LD), and adds `lang="en"`. Idempotent.
5. **Rename to extensionless `.html`** + drop the redundant home source:
   ```bash
   for f in AI-Lab AI-Transformation Advisory-Execution Contact Ethics Keynote-Speaker Press Publications Why; do mv "$f.dc.html" "$f.html"; done
   rm -f "Gregory Renard - Home.dc.html"   # index.html is the deployed home
   ```
   GitHub Pages serves `X.html` at `/X` (verified live — `/AI-Transformation` → 200). `index.html` stays the root. Bump `sitemap.xml`'s `<lastmod>` to today (it already lists the extensionless URLs).

**Pipeline order (critical):** cp Home→index → home-link `./` → `patch-contact-form.py` → `seo-clean-urls.py` → rename `*.dc.html`→`*.html` (+ rm Home) → bump sitemap. The contact-form patch must run while the file is still `Contact.dc.html`; the SEO/clean-URL transform must run before the rename.

## Verify ("tout nickel")
After the transforms, confirm no broken internal links AND no missing assets:
Run AFTER the rename, on the final `*.html` set:
```bash
# (a) extension fully gone, no accidental .//
grep -rl "\.dc\.html" *.html && echo "BAD: .dc.html remains" || echo "ok: extensionless"
grep -rn '\.//' *.html || echo "ok: no .//"
# (b) index.html is the homepage (not a redirect) and renders
grep -c 'http-equiv="refresh"' index.html   # expect 0
grep -c '<x-dc>' index.html                 # expect 1
# (c) static SEO present: each page has <title> + og:title inside <head>
for f in *.html; do h=$(awk 'BEGIN{p=1}/<body/{p=0}{if(p)print}' "$f"); echo "$h" | grep -q "<title>" && echo "$h" | grep -q "og:title" && echo "OK seo-head $f" || echo "MISS seo-head $f"; done
# (d) every internal page link (extensionless) resolves to a .html file
for n in AI-Lab AI-Transformation Advisory-Execution Contact Ethics Keynote-Speaker Press Publications Why; do
  grep -qhoE "href=\"$n\"|url: '$n'" *.html && { [ -f "$n.html" ] && echo "OK link $n" || echo "MISS $n.html"; }
done
# (e) every local asset reference resolves
for t in $(grep -rhoE "assets/[A-Za-z0-9%@_.-]+\.(png|jpg|jpeg|webp|gif|svg|mp4|pdf)" *.html | sort -u); do
  [ -f "$t" ] && echo "OK $t" || echo "MISS $t"
done
```
A MISS in (e) = an asset the user added in Design; fetch the binary (step 5) or flag it. Template `{{ … }}` placeholders are NOT broken links (bound at runtime from the JS arrays).

## Assets (all resolved — keep present in `assets/`)
- **`assets/greg-home-orange.png`** (Why portrait, 870 KiB) — user-provided manually; >256 KiB so un-fetchable via DesignSync. The fresh Design `Why` already references `assets/greg-home-orange.png`, so just keep the file in `assets/` (don't let it get deleted). No revert needed anymore.
- **`assets/favicon.png` (256) + `assets/favicon-64.png` (64)** — generated GR logo (blue gradient + white "GR", via Pillow). Keep them; referenced site-wide.
- Every `assets/*` reference in the pages must resolve to a file — the Verify step (d) catches anything new the user adds in Design.

## Pending Claude Design fixes (temporary transforms — verify each future sync)
Things the user will fix in Claude Design *later*; until then a deploy step keeps the live
site correct. Each is **idempotent** (no-op once Design is updated) — when a sync's `git diff`
shows the step no longer changes anything, delete it from `deploy.sh` and this list.

- **Footer label** (added 2026-06-14): the top nav says `Advisory & Execution` / `Conseil & Exécution`,
  but Claude Design's **footer** "Navigate" column still says `Work together` / `Travailler ensemble`.
  `deploy.sh` step **2b** rewrites the footer `label:` to match. `verify.sh` check **(g)** warns if the
  old label reappears. **Remove step 2b once the footer is updated in Claude Design.**

## Permanent repo files (NOT from Design — never delete/clobber on sync)
These live only in the repo (Claude Design doesn't know about them). A sync pulls/overwrites only the Design-sourced files above, so these survive — just don't `rm` them or let a transform touch them:
- `CNAME` (custom domain), `404.html` (migration catch-all + branded 404), `services.html` + `keynotes-speaker.html` (200 redirect stubs: old Wix slugs → `/Advisory-Execution` and `/Keynote-Speaker`).
- ⚠️ **macOS case-insensitivity trap:** never create a flat redirect stub whose name collides case-insensitively with a real page (e.g. `why.html` would overwrite `Why.html` on APFS). Only slugs with NO capitalized twin are safe as flat files (`services`, `keynotes-speaker`); all case-only old slugs (`/why`, `/contact`, …) are handled by `404.html`'s JS redirect instead.

## Notes
- Filenames with spaces (`Gregory Renard - Home.dc.html`) are fine for git, sed globs, and DesignSync — pass them verbatim.
- Don't re-fetch files outside the user's scope; it wastes time and context.
