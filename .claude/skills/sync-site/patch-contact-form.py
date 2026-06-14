#!/usr/bin/env python3
"""Deploy-only transform: wire the Contact ("Let's Build") form to the Google
Sheet endpoint. Claude Design's form goes nowhere (it only shows "Message
received"), so this patch must be re-applied after every /sync-site pull.
Idempotent: safe to run repeatedly. Run from the repo root."""
import sys

P = "Contact.dc.html"
# Google Apps Script Web App (doPost appends a row to the contacts sheet).
EP = "https://script.google.com/macros/s/AKfycbzBYfeq7nwrDsd9ZSwAmr_KSrgl8TDz3Hau1GD3YNcF17-AKDKpfR5tga3HJHBCXGVi/exec"

OLD = """      submit: () => {
        if (this.state.firstName.trim() && validEmail) this.setState({ sent: true, showError: false });
        else this.setState({ showError: true });
      },"""

NEW = """      submit: () => {
        if (!(this.state.firstName.trim() && validEmail)) { this.setState({ showError: true }); return; }
        try { fetch('%s', { method: 'POST', mode: 'no-cors', body: new URLSearchParams({ firstName: this.state.firstName, lastName: this.state.lastName, email: this.state.email, message: this.state.message }) }); } catch (e) {}
        this.setState({ sent: true, showError: false });
      },""" % EP

s = open(P, encoding="utf-8").read()
if "script.google.com/macros" in s:
    print("contact form: already wired")
elif OLD in s:
    open(P, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
    print("contact form: wired to Google Sheet endpoint")
else:
    print("contact form: !! OLD submit block not found — Design may have changed the form; re-inspect Contact.dc.html", file=sys.stderr)
    sys.exit(1)
