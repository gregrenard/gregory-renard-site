#!/usr/bin/env python3
"""Deploy-only transform: wire the Contact ("Let's Build") form to the Google
Sheet endpoint, with a honeypot anti-spam field.

Claude Design's form does nothing on submit (only shows "Message received"),
so this must be re-applied after every /sync-site pull. Idempotent and robust:
it replaces whatever `submit` is present (Design-original OR a prior wired
version) and inserts the honeypot input only if missing. Run from repo root.

Pairs with a server-side check in the Apps Script doPost:
    if (e.parameter.company_site) { return ...{ok:true}...; }   // honeypot -> ignore
"""
import sys

P = "Contact.dc.html"
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

open(P, "w", encoding="utf-8").write(s)
print("contact form: wired to Google Sheet + honeypot in place")
