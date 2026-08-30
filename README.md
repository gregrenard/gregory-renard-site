# gregory-renard.com

Personal site of Gregory Renard — AI architect. Static site served by GitHub Pages at
**https://gregory-renard.com**.

## How this repo relates to Claude Design

**Claude Design is the source of truth**, not this repo. The pages are authored visually in
the Claude Design project *gregory-renard.com*; this repo holds the **deployed output** —
the Design pages plus a set of deploy-only transforms Claude Design cannot express
(clean root URL, extensionless URLs, static SEO head, wired contact form, static
pre-render).

Consequence: **never edit a page here by hand** expecting it to last. The next sync pulls
from Design and overwrites it. Content changes go in Claude Design; deploy behaviour goes
in the sync scripts.

## Updating the site

Run the `/sync-site` skill (`.claude/skills/sync-site/`). It pulls the pages from Claude
Design, re-applies every deploy transform, verifies the result, and pushes. See
`.claude/skills/sync-site/SKILL.md` for the full pipeline and its ordering constraints.

## Structure

`index.html` is a **generated artifact** — a direct copy of the Design home page, so `/`
serves the homepage with no redirect. GitHub Pages serves `X.html` at `/X`, so every page
is reachable extensionless.

Content pages:

| URL | Page |
|---|---|
| `/` | Home / Vision |
| `/Method` | The three-phase Applied AI method |
| `/Why` | Career timeline, vision and values |
| `/Keynote-Speaker` | Keynotes, topics and references |
| `/Ethics` | Human-centered, responsible AI |
| `/Publications` | Patents and peer-reviewed research |
| `/Press` | Awards, distinctions and media coverage |
| `/Contact` | Contact form (wired to a Google Sheet) |
| `/AI-for-Good-2026` | UN/ITU AI for Good Global Summit recap |
| `/WEF-Digital-Safety-2026` | WEF Digital Safety workshop recap |
| `/AI-for-Humanity-2018` | Élysée Palace AI dinner recap |

Redirect stubs (kept so old URLs and backlinks resolve):

| URL | Redirects to | Indexed |
|---|---|---|
| `/AI-Transformation` | `/Method` | yes (canonical → `/Method`) |
| `/AI-Lab` | `freedom.ai` | no |
| `/Advisory-Execution` | `freedom.ai` | no |
| `/services` | `/Advisory-Execution` | — |
| `/keynotes-speaker` | `/Keynote-Speaker` | — |

## Repo-only files (not from Claude Design — a sync must never clobber them)

`CNAME` (custom domain) · `404.html` (branded 404 + JS redirect for old Wix slugs) ·
`services.html`, `keynotes-speaker.html` (redirect stubs) · `robots.txt` · `sitemap.xml` ·
`llms.txt` (site summary for AI crawlers) · `support.js` (the dc-runtime).

⚠️ **macOS case-insensitivity trap:** never add a flat redirect stub whose name collides
case-insensitively with a real page — `why.html` would overwrite `Why.html` on APFS. Only
slugs with no capitalized twin are safe as flat files; the rest are handled by `404.html`.
