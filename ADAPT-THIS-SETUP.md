# Adapting this setup to another site — a guide for the AI agent doing it

**You are probably an AI coding agent whose human handed you a link to this repository and
said "set up the same thing for my site".** This file is written for you. It explains what
this setup is, which parts transfer unchanged, which parts are one person's site in code
and must be rewritten, and the constraints that will bite you if you don't know them.

Read this file completely before you copy anything. Roughly half of what is here is
generic machinery and half is Gregory Renard's site — shipping the second half by accident
produces a site that deploys to the wrong domain and a contact form that mails a stranger.

---

## 1. What this repository actually is

A three-part arrangement:

| Layer | What it is | Who owns it |
|---|---|---|
| **Claude Design project** | Where the pages are authored, visually. The source of truth. | The human |
| **This repository** | The *deployed output* — Design's pages plus deploy-only transforms. | The sync scripts |
| **GitHub Pages** | Serves the repository at a custom domain. | GitHub |

The critical consequence, and the first thing to tell your human: **the repository is not
where content is edited.** Pages here are overwritten by the next sync. Content changes go
in Claude Design; deploy behaviour goes in the sync scripts. An agent that "fixes a typo"
by editing `Why.html` has done work that will silently vanish.

Why transforms exist at all: Claude Design exports pages that are *almost* deployable but
not quite. Its `index.html` is a redirect rather than the home page. Its pages link to the
home by its Design filename (`Gregory%20Renard%20-%20Home%20v2.dc.html`) — a redirect
behind an ugly `%20` URL. Page `<head>` metadata lives in a `<helmet>` block that only the
client-side runtime reads, so crawlers see nothing. Its contact form shows "Message
received" and posts nowhere. Each transform in `deploy.sh` closes one of those gaps, and
each must be re-applied on every sync because a fresh pull reverts it.

---

## 2. What your human needs before you start

The repository cannot supply these. Check all five before writing any code.

1. **Their own Claude Design project**, with the pages authored in it. This setup syncs
   *from* Design; it does not create Design pages.
2. **The DesignSync connector active in their session.** In Claude Code that means they
   have run `/design-login`. Without it you have no `list_files` / `get_file`, and nothing
   else in this guide can run. Note DesignSync is **read-only** for a project of this
   type: you can pull, you can never push a change back into Design.
3. **Python 3 and Google Chrome installed locally.** Chrome is not optional — the
   pre-render stage drives it headless.
4. **A GitHub repository with Pages enabled**, and `gh` authenticated as an account that
   can push to it.
5. **Claude Code specifically, for the pull step.** `extract-pulled.py` reconstructs the
   pulled pages by reading the *session transcript JSONL* that Claude Code writes to
   `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`. That coupling is invisible until
   it breaks. On a different agent runtime you must replace that one script with whatever
   writes tool results to disk there — the rest of the pipeline does not care.

---

## 3. The pipeline — this is the part worth copying

The scripts are less valuable than their **order** and the constraints that hold it
together. `deploy.sh` is the executable reference; if this description and `deploy.sh` ever
disagree, `deploy.sh` wins.

```
DesignSync list_files          → has the page structure changed?
DesignSync get_file × N        → pull each page (results land in the transcript)
extract-pulled.py              → write them to disk byte-exact
deploy.sh
  1  clean root                → cp "<Home>.dc.html" index.html   (no redirect at /)
  2  home-link rewrite         → "<Home>.dc.html" → "./"          (quote-anchored)
  3  wire the contact form     → POST to a real endpoint
  3b enrich SEO                → JSON-LD Person, richer title/description
  4  clean URLs + static head  → strip .dc.html, copy <helmet> into real <head>
  4b mobile hero-wrap fix      → design-specific CSS override
  4c gallery .png → .jpg       → site-specific asset naming
  5  rename *.dc.html → *.html → and delete the redundant home source
  6  bump sitemap <lastmod>
  7  pre-render (headless)     → inject resolved content for non-JS crawlers
verify.sh                      → ten gates; nothing ships until they pass
extract-contents.py            → plain-text copies for a human proof-reader (optional)
```

**Four ordering constraints. Violating any one produces a broken deploy that still looks
fine locally.**

- **Pre-render runs LAST**, after clean-URLs and after the rename. It captures the
  post-JavaScript DOM and injects it as a static mirror; run it earlier and every link
  inside that mirror keeps its `.dc.html` extension and 404s.
- **Clean-URLs runs before the rename**, and after the home-link rewrite and form patch —
  it rewrites links, so it must see them in their Design form.
- **The home-link rewrite is quote-anchored** (`"…dc.html"` → `"./"`, and the `'…'` form
  separately). An unanchored substitution yields `.//` in some contexts. Gate (a) checks
  for exactly this.
- **`index.html` is a generated artifact**, a copy of the home page. Never edit it; edit
  the Design home.

### The single source of truth: `pages.json`

Every script derives its page list from `.claude/skills/sync-site/pages.json` through
`manifest.py`. Before it existed, the page list was duplicated in six places and drifted.
**Do not re-hardcode a page list anywhere.** One entry per page:

```json
{ "design": "Home v2.dc.html", "slug": "index", "role": "home" }
{ "design": "About.dc.html",   "slug": "About", "role": "content" }
{ "design": "Old.dc.html",     "slug": "Old",   "role": "stub",
  "redirect": "/About", "indexed": true, "note": "superseded by About" }
```

`role` drives everything downstream: `home` becomes `index.html`; `content` gets the
static SEO head, the pre-render mirror, a sitemap entry and an `llms.txt` line; `stub` is
a redirect-only page that gets none of those.

`manifest.py` answers queries — `design`, `home-design`, `subpages`, `content`, `stubs`,
`prerender`, `sitemap-urls` — from Python or from bash.

> **Bash trap:** the home's Design filename contains spaces. Read `manifest.py` output
> line-by-line; never let the shell word-split it. (And `zsh` does not word-split
> variables at all, so a loop that works in `bash` may silently do nothing in `zsh`.)

### The pre-render mirror, and why it exists

The Claude Design runtime (`support.js`) renders each page body from a `{{ }}` template at
runtime, in React. So the raw HTML ships unresolved placeholders: fine for browsers and
for Google, bad for no-JS clients, for LinkedIn's body scrape, and for many AI crawlers.

`prerender.py` headless-renders each page, captures the resolved `#dc-root`, and injects it
as a mirror that is **visible by default** and hidden the instant the runtime mounts, via
pure CSS — no JavaScript timing, no cloaking, the same content either way:

```css
x-dc { display: none }                                /* hide the raw template */
#dc-root:not(:empty) ~ #dc-prerender { display: none } /* hide the mirror once React mounts */
```

It is idempotent: it strips any previous mirror before injecting, including the newline the
previous injection added — omit that detail and every page grows two blank lines per sync,
forever.

One non-obvious design decision you should keep: the little HTTP server `prerender.py`
runs **returns 404 for `.mp4`/`.webm`/`.mov`/`.m4v`/`.ogv`**. Chrome's
`--virtual-time-budget` does not advance while a media element is still loading, so a page
carrying `<video preload="metadata">` on a large file stalls the render past its timeout.
What gets captured is the resolved DOM, and `<video>` markup is byte-identical whether or
not its metadata loaded — so refusing the file changes nothing in the output and makes
every render deterministic. If you drop that handler you will reintroduce a hang that
looks like random flakiness.

### The verification gate

`verify.sh` runs ten checks, (a) through (i), and it is what makes an unattended sync safe.
Do not ship past a failure and do not weaken a gate to make it pass.

| Gate | Checks |
|---|---|
| (a) | `.dc.html` fully gone, no accidental `.//` |
| (b) | `index.html` is the homepage, not a redirect |
| (c) | every content page has `<title>` + `og:title` **inside `<head>`** |
| (c2) | redirect stubs carry a refresh + canonical |
| (d) | every internal page link resolves to a real `.html` file |
| (e) | every local asset reference resolves |
| (f) | permanent non-Design files were not clobbered by the sync |
| (g) | footer labels agree with the top nav |
| (h) | every content page has a pre-render mirror with **zero** `{{ }}` left in it |
| (i) | `pages.json`, `sitemap.xml` and `llms.txt` list the same URLs, both directions |

Gate (i) is the one people skip and regret. Without it, a retired page keeps being
advertised to crawlers and to LLMs for weeks before anyone notices.

---

## 4. What transfers, and what does not

### Copy unchanged — no edits needed

| File | What it does |
|---|---|
| `manifest.py` | Reads `pages.json`, answers page-list queries |
| `extract-pulled.py` | Rebuilds pulled pages byte-exact from the session transcript |
| `prerender.py` | Headless render + mirror injection |
| `extract-contents.py` | Plain-text dumps per URL, EN + FR, for a human proof-reader |
| `seo-clean-urls.py` | Strips extensions, lifts `<helmet>` into the real `<head>` |
| `pull-asset.py` | Writes a base64 asset pulled from Design |
| `support.js` | The Claude Design runtime. **Vendored and generated — copy as-is, never edit.** |

### Fill in — one configuration file

`pages.json`: the site domain plus one entry per page. This is the only file that should
need editing for a straightforward adaptation.

### Rewrite from scratch — these are one person's site in code

| File | Why |
|---|---|
| `enrich-seo.py` | Contains a full biography: JSON-LD `Person`, employer, social profiles, and hand-written titles/descriptions for two specific pages. Nothing here is reusable. |
| `patch-contact-form.py` | **Contains a live Google Apps Script `/exec` endpoint.** See the warning below. |
| `hero-wrap-fix.py` | A CSS override keyed to this design's `.grx-*` class names. Useful only if the other site came from the same Design template. |
| `SKILL.md` | Describes this pipeline, this page list, this GitHub account, this push policy. |

> ### ⚠️ The contact-form endpoint
> `patch-contact-form.py` hard-codes the URL of Gregory Renard's Google Apps Script Web
> App. If you copy that file unchanged, **every message submitted on your human's site is
> appended to Gregory's spreadsheet.** Your human must deploy their own Apps Script Web
> App and you must replace the endpoint before the first deploy. If they don't want a form
> at all, delete the script and drop stage 3 from `deploy.sh`.

### Adapt — small, specific edits

| File | What to change |
|---|---|
| `deploy.sh` | Stage 4c is two `sed` lines renaming `.png` → `.jpg` inside two named photo-gallery directories. Delete them unless the same mismatch exists. |
| `verify.sh` | Gate (i) has the domain in a regex; gate (f)'s protected-file list names legacy redirect pages from a previous Wix site. |

### Do not copy at all — these are the site itself

`CNAME` (the custom domain), `sitemap.xml`, `llms.txt`, `robots.txt` (its `Sitemap:` line
carries the domain), `404.html` (its redirect map is old Wix URLs), everything under
`assets/` including `og-cover.png`, and every `*.html` page.

`llms.txt` deserves a note: it is the file that tells AI crawlers what the site is, in
prose. It is **deliberately hand-written, not generated** — the descriptions are editorial
judgement, and a generated version reads like a sitemap. Gate (i) keeps its *URL list*
honest without pretending to write its *content*.

---

## 5. How you must behave while operating this

These are not style preferences. Each one is a failure that already happened.

- **Confirm the human has finished editing in Design before you pull.** DesignSync reads
  the *live* project. Pull mid-edit and you capture a half-finished page — this was
  observed: a page's nav order shifted between two reads in the same session.
- **Never hand-retype a pulled page.** Pages come back from `get_file` either inline or
  persisted to a `tool-results/*.txt`; `extract-pulled.py` reconstructs both byte-exact.
  Retyping a 60 KB page into a `Write` call risks silent corruption on a live site, and
  you will not notice.
- **Never hand-edit a deployed page** to fix content. The next sync overwrites it. Fix it
  in Design.
- **Assets over 256 KiB cannot be pulled.** `get_file` returns `truncated: true` and there
  is no workaround. Keep the previous working reference — never commit a broken one — and
  ask the human to add the file manually.
- **Re-run all the gates after fixing one.** A fix for gate (h) can break gate (d).

---

## 6. Bootstrapping from zero — the order to do it in

1. Create the repo, enable GitHub Pages, point the custom domain, add `CNAME`.
2. Copy `.claude/skills/sync-site/` across. Delete `enrich-seo.py`,
   `patch-contact-form.py` and `hero-wrap-fix.py` for now — add them back deliberately if
   the site needs them.
3. Write `pages.json`: the domain, and one entry per Design page with its role.
4. Trim `deploy.sh` to the stages that apply. Keep 1, 2, 4, 5, 6, 7 — those are structural.
   Stages 3, 3b, 4b, 4c are site-specific.
5. Copy `support.js` as-is.
6. Write `sitemap.xml`, `llms.txt` and `robots.txt` for the new domain, listing exactly the
   `content` pages from `pages.json`. Gate (i) will tell you when they disagree.
7. Trim `verify.sh`: fix the domain in gate (i), replace gate (f)'s protected-file list,
   drop gate (g) if the design has no footer nav.
8. Run one full cycle end-to-end and make every gate pass **before** the first push. It is
   much easier to debug a pipeline that has never been live.
9. Rewrite `SKILL.md` for the new site, and confirm the push-approval policy with the
   human — do not assume it. On this repo the owner explicitly authorised pushing without
   asking, because it is his own site with no other contributors. **That is his decision
   about his repository, not a default you inherit.** Ask yours.

---

## 7. If you only remember four things

1. **Design is the source of truth; the repo is output.** Never fix content here.
2. **`pages.json` is the only page list.** Never hardcode another.
3. **Pre-render runs last, and the gates are not negotiable.**
4. **Replace the contact-form endpoint before the first deploy.**

---

*This file describes the setup as it stands in this repository. It is documentation, not a
supported product: nothing here is versioned, and the scripts assume macOS (`sed -i ''`)
and Claude Code. Read `.claude/skills/sync-site/SKILL.md` for the full operational detail.*
