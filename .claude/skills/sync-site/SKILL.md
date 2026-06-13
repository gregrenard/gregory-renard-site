---
name: sync-site
description: Sync the gregory-renard.com site from Claude Design to GitHub so the live site updates, re-applying deploy-only fixes (clean root URL) that Claude Design can't do. Use when the user has edited pages in claude.ai/design and wants the changes published — triggers like "sync the site", "j'ai modifié dans Claude Design", "publie / mets à jour le site", "push my edits", "déploie le site".
---

# Sync site — Claude Design → GitHub (with deploy-only fixes)

Pull the latest **text** content from the user's Claude Design project, **re-apply the deploy-only transforms** Claude Design can't do (clean root URL), verify all internal links, then push to GitHub. GitHub Pages redeploys the live site automatically (~1 min).

## Project facts
- **Source of truth:** Claude Design project **"gregory-renard.com"**, projectId `25751aee-ab2f-4af9-a3b3-66cf466244c4`. The user edits the **root-level** components there.
- **Repo / remote:** `origin/main` → `github.com/gregrenard/gregory-renard-site` (this working directory).
- **Live site:** https://gregrenard.github.io/gregory-renard-site (custom domain target: gregory-renard.com).
- **DesignSync is READ-ONLY for this project** (type `PROJECT_TYPE_PROJECT`). NEVER call `write_files`/`finalize_plan`/`delete_files` against it — only `list_files` and `get_file`.

## Syncable files (TEXT only)
Root-level files that map 1:1 to the repo root and pull via DesignSync `get_file`:

- The 10 pages: `AI-Lab.dc.html`, `AI-Transformation.dc.html`, `Advisory-Execution.dc.html`, `Contact.dc.html`, `Ethics.dc.html`, `Gregory Renard - Home.dc.html`, `Keynote-Speaker.dc.html`, `Press.dc.html`, `Publications.dc.html`, `Why.dc.html`
- `support.js`, `sitemap.xml`, `robots.txt`, `llms.txt`
- NOTE: do NOT pull Design's `index.html` (it's a redirect stub). In the repo, `index.html` is a **generated deploy artifact** — see "Deploy-only transforms" below.

⚠️ **Binaries cannot be synced.** `get_file` is capped at 256 KiB, so `assets/*.png|jpg|pdf|mp4` (images, keynote PDF, video) will NOT come through. They are already in the repo. If the user says they changed an image or the video in Design, tell them it must be transferred **manually** (have them send/point you to the new file) — DesignSync can't pull it.

## Steps
1. **Scope:** if the user named specific page(s), pull only those (plus always re-run the transform if Home or any page changed). If they say "everything"/"tout" or don't specify, pull all the text files above.
2. **Pull & diff:** for each in-scope file, `DesignSync get_file` (projectId above), compare to the local copy, write only files whose content actually changed.
3. **Re-apply deploy-only transforms** (always, after any page is pulled) — see next section.
4. **Verify internal links** — see "Verify hrefs".
5. If nothing changed at all, stop and tell the user "no changes to push" (live site already current).
6. Otherwise `git add` the changed files, commit (message listing what changed, e.g. `Update Home from Claude Design + rebuild clean index`), end the message with:
   ```
   Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
   ```
   then `git push origin main`.
7. Report files updated + confirm push. Remind the user GitHub Pages redeploys in ~1 min, and to **open `/` in a browser to confirm the homepage renders** (curl/HEAD only proves bytes are served, not that the dc-runtime rendered — check the console for `[dc-runtime] … failed`). If a binary change was mentioned, restate it still needs manual handling.

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

Scope stays **root-only**: sub-pages keep their `.dc.html` URLs. Do NOT attempt per-page clean URLs (e.g. `/contact/`) — that needs a directory + `index.html` restructure that breaks every `./support.js` / `./assets/` relative path and only works once the custom domain is on root. `sitemap.xml` and `llms.txt` already list the home as `https://gregory-renard.com/` (the clean root) — leave them; just don't let any `…/Gregory%20…Home.dc.html` URL appear in them.

## Verify hrefs ("tout nickel")
After the transforms, confirm no broken internal links:
```bash
# (a) no encoded home link or accidental .// remains
grep -rn "Gregory%20Renard%20-%20Home.dc.html" *.dc.html index.html   # expect: nothing
grep -rn '\.//' *.dc.html index.html                                  # expect: nothing
# (b) index.html is the homepage, not a redirect
grep -c 'http-equiv="refresh"' index.html   # expect 0
grep -c '<x-dc>' index.html                 # expect 1
# (c) every literal .dc.html reference resolves to a file that exists
for t in $(grep -rhoE "[A-Za-z0-9%][A-Za-z0-9%_.-]*\.dc\.html" *.dc.html index.html | sort -u); do
  dec=$(printf '%s' "$t" | sed 's/%20/ /g'); [ -f "$dec" ] && echo "OK $t" || echo "MISS $t"
done   # expect all OK
```
Optionally, after the push + redeploy, curl each internal link against the live site and expect HTTP 200. Template placeholders like `{{ it.url }}` are NOT broken links — they're bound at runtime from the JS arrays (whose literal values the check above already covers).

## Notes
- Filenames with spaces (`Gregory Renard - Home.dc.html`) are fine for git, sed globs, and DesignSync — pass them verbatim.
- Don't re-fetch files outside the user's scope; it wastes time and context.
