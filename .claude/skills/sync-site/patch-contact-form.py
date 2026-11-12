#!/usr/bin/env python3
"""Deploy-only transform: wire the Contact ("Let's Build") form to the Google
Sheet endpoint, with a honeypot anti-spam field.

Claude Design's form does nothing on submit (only shows "Message received"),
so this must be re-applied after every /sync-site pull. Idempotent and robust:
it replaces whatever `submit` is present (Design-original OR a prior wired
version) and inserts the honeypot input only if missing. Run from repo root.

Also prefills the form from the URL fragment (#first=&last=&email=&message=) so the
"Ask your AI about Gregory" conversation can hand a drafted message to the visitor, who
reviews it and presses Send themselves (nothing is submitted by the link). The fragment
never reaches a server and is wiped from the address bar after load.

Usage: python3 patch-contact-form.py [file]   (default: Contact.dc.html)

Pairs with a server-side check in the Apps Script doPost:
    if (e.parameter.company_site) { return ...{ok:true}...; }   // honeypot -> ignore
"""
import sys

P = sys.argv[1] if len(sys.argv) > 1 else "Contact.dc.html"
# Google Apps Script Web App (doPost appends a row; honeypot rejects bots).
EP = "https://script.google.com/macros/s/AKfycbzBYfeq7nwrDsd9ZSwAmr_KSrgl8TDz3Hau1GD3YNcF17-AKDKpfR5tga3HJHBCXGVi/exec"

# Hidden honeypot input — invisible & unfocusable for humans, auto-filled by bots.
HP_INPUT = ('            <input type="text" id="grx-hp" name="company_site" tabindex="-1" '
            'autocomplete="off" aria-hidden="true" '
            'style="position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;'
            'opacity:0;pointer-events:none">\n')
ANCHOR = '            <sc-if value="{{ showError }}" hint-placeholder-val="{{ false }}">'

NEW_SUBMIT = """      submit: () => {
        if (!(this.state.firstName.trim() && validEmail)) { this.setState({ showError: true }); return; }
        try {
          var hp = (document.getElementById('grx-hp') || {}).value || '';
          if (!hp) fetch('%s', { method: 'POST', mode: 'no-cors', body: new URLSearchParams({ firstName: this.state.firstName, lastName: this.state.lastName, email: this.state.email, message: this.state.message, company_site: '' }) });
        } catch (e) {}
        this.setState({ sent: true, showError: false });
      },
""" % EP

s = open(P, encoding="utf-8").read()

# 1) Replace the whole submit region (submit: () => { ... }, up to reset:)
try:
    i = s.index("      submit: () => {")
    j = s.index("      reset:", i)
except ValueError:
    print("contact form: !! could not locate submit/reset markers — re-inspect Contact.dc.html", file=sys.stderr)
    sys.exit(1)
s = s[:i] + NEW_SUBMIT + s[j:]

# 2) Insert honeypot input (idempotent)
if 'id="grx-hp"' not in s:
    if ANCHOR not in s:
        print("contact form: !! honeypot anchor not found — re-inspect form", file=sys.stderr)
        sys.exit(1)
    s = s.replace(ANCHOR, HP_INPUT + ANCHOR, 1)

# 3) Prefill from the URL fragment (idempotent, marker: grx-prefill)
STATE_OLD = "  state = { lang: 'en', firstName: '', lastName: '', email: '', message: '', sent: false, showError: false };"
STATE_NEW = (
    "  state = (() => { /* grx-prefill */ var p = {}; "
    "try { p = Object.fromEntries(new URLSearchParams((location.hash || '').replace(/^#/, ''))); } catch (e) {} "
    "var c = function (k, n) { return String(p[k] || '').slice(0, n); }; "
    "if (location.hash) { setTimeout(function () { try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {} }, 1500); } "
    "return { lang: 'en', firstName: c('first', 80), lastName: c('last', 80), email: c('email', 120), message: c('message', 2000), sent: false, showError: false }; })();"
)
if "grx-prefill" not in s:
    if STATE_OLD not in s:
        print("contact form: !! state line not found — re-inspect Contact.dc.html", file=sys.stderr)
        sys.exit(1)
    s = s.replace(STATE_OLD, STATE_NEW, 1)

open(P, "w", encoding="utf-8").write(s)
print("contact form: wired to Google Sheet + honeypot + URL-fragment prefill in place")
