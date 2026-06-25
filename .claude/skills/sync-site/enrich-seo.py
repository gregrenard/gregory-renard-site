#!/usr/bin/env python3
"""Deploy-only SEO transform: foreground the "AI pioneer" positioning and inject a
rich schema.org Person knowledge graph, sourced from the public Wikipedia bio.

Runs on the HOME (index.html) and the STORY page (Why.dc.html), AFTER the
home-link transform and BEFORE seo-clean-urls.py — so the enriched <helmet> tags
get copied into the static <head> (read by Google + AI crawlers that don't run JS).

What it does (idempotent — re-running on freshly pulled pages is byte-identical):
  - <title>            -> lead with "AI Pioneer"
  - meta description   -> pioneer-forward, key facts (also og:/twitter:)
  - JSON-LD Person     -> replace (home) / insert (why) an enriched, shared @id
                          entity: birthDate/Place, nationality, awards, knowsAbout,
                          worksFor, full career prose. Existing sameAs preserved.

Only factual fields from the sources; no invented schools/org URLs.
"""
import re, json, glob

# ---- shared Person knowledge-graph entity (same @id => Google merges the two) ----
PERSON = {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": "https://gregory-renard.com/#person",
    "name": "Gregory Renard",
    "alternateName": "Grégory Renard",
    "jobTitle": "AI Architect",
    "disambiguatingDescription": "Pioneer of applied AI, conversational AI and Natural Language Processing (NLP).",
    "url": "https://gregory-renard.com/",
    "image": "https://gregory-renard.com/assets/og-cover.png",
    "birthDate": "1975-08-12",
    "birthPlace": {"@type": "Place", "name": "Mouscron, Belgium"},
    "nationality": "Belgian-American",
    "description": (
        "Gregory Renard is a Belgian-American computer scientist, mathematician and "
        "entrepreneur — a pioneer of applied artificial intelligence, conversational AI "
        "and Natural Language Processing (NLP) for over 30 years. In 2003 he co-founded "
        "Wygwam in Lille; in 2011 he founded xBrain, launching Angie — France's first "
        "large-scale conversational assistant — at the 2012 Microsoft TechDays. As a "
        "member of the AI Technical Committee at NASA FDL / SETI he received the NASA FDL "
        "Applied AI Award of Merit (2022). He co-initiated the AI4Humanity campaign behind "
        "France's Villani mission, contributed to the France IA national strategy and the "
        "EU High-Level Expert Group on AI, and co-authored the Holberton-Turing Oath on AI "
        "ethics. He created Cognitive Orchestration™, the methodology Fortune 500 "
        "companies use to move enterprise AI from experimentation to production at scale. "
        "Based in Silicon Valley, he was named Officer of the Order of Merit of Wallonia in 2025."
    ),
    "knowsAbout": [
        "Artificial Intelligence", "Applied AI", "Conversational AI",
        "Natural Language Processing", "AI Ethics", "Cognitive Orchestration",
        "Machine Learning", "Agentic AI",
    ],
    "award": [
        "NASA FDL Applied AI Award of Merit (2022)",
        "Officer of the Order of Merit of Wallonia (2025)",
    ],
    "worksFor": {"@type": "Organization", "name": "Freedom.AI", "url": "https://www.freedom.ai/"},
    "sameAs": [
        "https://www.linkedin.com/in/gregoryrenard/",
        "https://fr.wikipedia.org/wiki/Gr%C3%A9gory_Renard",
        "https://scholar.google.com/citations?user=Khit-6kAAAAJ&hl=fr",
        "https://github.com/gregrenard/",
        "https://twitter.com/Redo",
        "https://www.youtube.com/@GregoryRenard",
    ],
}
LDJSON = '<script type="application/ld+json">' + json.dumps(PERSON, ensure_ascii=False, separators=(",", ":")) + "</script>"

# ---- per-page title + description (pioneer-forward) ----
PAGES = {
    "index.html": {
        "title": "Gregory Renard — AI Pioneer & Applied AI Architect",
        "desc": ("Gregory Renard — pioneer of applied AI, conversational AI and NLP for 30+ years. "
                 "Creator of Cognitive Orchestration™ and recipient of the NASA FDL Applied AI Award of Merit."),
    },
    "Why.dc.html": {
        "title": "Who is Gregory Renard? — AI Pioneer & Applied AI Architect",
        "desc": ("The story of Gregory Renard — a pioneer of applied AI, conversational AI and NLP for "
                 "30+ years, from xBrain and Angie to NASA FDL and Cognitive Orchestration™."),
    },
}


def esc_text(t):   # for element text (<title>)
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(t):   # for attribute value (content="...")
    return esc_text(t).replace('"', "&quot;")


def sub1(pattern, repl, s):
    return re.sub(pattern, lambda _m: repl, s, count=1, flags=re.S)


for page, cfg in PAGES.items():
    if not glob.glob(page):
        continue
    s = open(page, encoding="utf-8").read()
    t_text, t_attr, d_attr = esc_text(cfg["title"]), esc_attr(cfg["title"]), esc_attr(cfg["desc"])

    s = sub1(r"<title>.*?</title>", "<title>" + t_text + "</title>", s)
    s = sub1(r'<meta name="description" content="[^"]*">', '<meta name="description" content="' + d_attr + '">', s)
    s = sub1(r'<meta property="og:title" content="[^"]*">', '<meta property="og:title" content="' + t_attr + '">', s)
    s = sub1(r'<meta property="og:description" content="[^"]*">', '<meta property="og:description" content="' + d_attr + '">', s)
    s = sub1(r'<meta name="twitter:title" content="[^"]*">', '<meta name="twitter:title" content="' + t_attr + '">', s)
    s = sub1(r'<meta name="twitter:description" content="[^"]*">', '<meta name="twitter:description" content="' + d_attr + '">', s)

    # JSON-LD Person: replace the first existing block (home), else insert in the helmet (why)
    if re.search(r'<script type="application/ld\+json">.*?</script>', s, re.S):
        s = sub1(r'<script type="application/ld\+json">.*?</script>', LDJSON, s)
    else:
        s = s.replace("</helmet>", LDJSON + "\n</helmet>", 1)

    open(page, "w", encoding="utf-8").write(s)
    print("enrich-seo:", page)
