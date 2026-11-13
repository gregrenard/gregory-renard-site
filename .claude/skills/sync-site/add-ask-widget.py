#!/usr/bin/env python3
"""
add-ask-widget.py — deploy-only transform: the "Ask your AI about Gregory" widget.

Injects a self-contained <style>+<div>+<script> block before </body>. The widget is a
corner card (collapsible) with four deep links — Claude, ChatGPT, Gemini (via Google AI
mode), Perplexity — each opening the visitor's OWN assistant with a prefilled prompt that
asks it to read https://gregory-renard.com/ask-gregory.md and use it as its guide. The conversation style lives in that file, not in the link, so a visitor who reads the prompt sees a plain, honest request. No server,
no API key, no cost: the visitor's AI does the talking, ask-gregory.md is the source of
truth. Modelled on the widget at bright.ai.

Also injects the "Let's talk" modal (marker id="grx-talk"): clicking a "Let's talk" /
"Parlons-en" button that links to Contact opens a popup with the same four AI links
and the contact form itself (same Apps Script endpoint and honeypot as Contact, read
from patch-contact-form.py so the URL lives in one place). Without JS the button still
navigates to /Contact. The corner widget goes on index.html only; the modal goes on
every file passed in.

Wired into deploy.sh (step 5b, after the rename). The ?q= prefill links are unofficial and can
change; Google AI mode is used for Gemini because Gemini itself has no prefill link.

Idempotent (guarded by the id="grx-ask" marker). Collapsed/expanded state is remembered
in localStorage; first visit is expanded on desktop (>900px) and collapsed on mobile.

Usage:
  python3 add-ask-widget.py                          # default: index.html
  python3 add-ask-widget.py index.html Why.html Ethics.html
"""
import os, re, sys, urllib.parse

BRIEF = "https://gregory-renard.com/ask-gregory.md"
PROMPT = (
    f"Read {BRIEF}: it is your source of facts about Gregory Renard. Receive me the way "
    "the maître d' of a four-star restaurant receives a CEO: impeccable, warm, attentive, "
    "never rushed, never salesy in a cheap way. Welcome me in three short sentences that "
    "make me feel expected and show why his thirty years of hands-on AI are remarkable, "
    "then ask what I would love to build with GenAI. Then, one question at a time, "
    "anticipate what I need: reflect my words back, serve me the one or two of his "
    "projects that best match my ambition as short stories with a striking detail, and "
    "answer any hesitation with grace. When I am ready, offer to prepare a short message "
    "to him and give me a link to his pre-filled contact form (the page explains the "
    "format) that I review and send myself; he is always glad to hear from leaders with "
    "ambitious GenAI projects. Answer in my language."
)
PROMPT_FR = (
    f"Lis {BRIEF} : c'est ta source de faits sur Gregory Renard. Reçois-moi comme le "
    "maître d'hôtel d'un restaurant quatre étoiles reçoit un chef d'entreprise : "
    "impeccable, chaleureux, attentif, sans jamais me presser ni vendre de façon "
    "grossière. Accueille-moi en trois phrases courtes qui me donnent le sentiment d'être "
    "attendu et montrent pourquoi ses trente ans d'IA construite à la main sont "
    "remarquables, puis demande-moi ce que j'aimerais construire avec la GenAI. Ensuite, "
    "une question à la fois, anticipe mes besoins : reformule mes mots, raconte-moi en "
    "courtes histoires, avec un détail marquant, un ou deux de ses projets qui "
    "correspondent le mieux à mon ambition, et réponds à chaque hésitation avec grâce. "
    "Quand je suis prêt, propose de préparer un court message pour lui et donne-moi un "
    "lien vers son formulaire de contact prérempli (la page explique le format) que je "
    "relis et envoie moi-même ; il est toujours heureux d'échanger avec des dirigeants "
    "qui portent des projets GenAI ambitieux. Réponds-moi en français."
)
Q = urllib.parse.quote(PROMPT, safe="")
QF = urllib.parse.quote(PROMPT_FR, safe="")

PROVIDER_BASES = [
    ("Claude", "https://claude.ai/new?q="),
    ("ChatGPT", "https://chatgpt.com/?q="),
    ("Gemini", "https://www.google.com/search?udm=50&aep=11&q="),
    ("Perplexity", "https://www.perplexity.ai/search/new?q="),
]

# English link by default; data-fr carries the French one, swapped in by the page script
# when the visitor's browser is French or the French popup was opened.
BUTTONS = "".join(
    f'<a class="grx-ask-btn" href="{base + Q}" data-en="{base + Q}" data-fr="{base + QF}" '
    f'target="_blank" rel="noopener" aria-label="Ask {name} about Gregory Renard">{name}</a>'
    for name, base in PROVIDER_BASES
)

BLOCK = (
    '<style id="grx-ask-css">'
    "#grx-ask{position:fixed;right:16px;bottom:16px;z-index:2147483000;"
    "font-family:var(--font-sans,'Hanken Grotesk',system-ui,sans-serif);color:#F5F1E6}"
    "#grx-ask .grx-ask-card{width:min(300px,calc(100vw - 32px));background:#172139;"
    "border:1px solid rgba(235,217,168,.35);border-radius:14px;padding:18px 18px 16px;"
    "box-shadow:0 12px 40px rgba(23,33,57,.35)}"
    "#grx-ask .grx-ask-title{font-size:20px;line-height:1.2;font-weight:600;margin:0 28px 8px 0}"
    "#grx-ask .grx-ask-text{font-size:14px;line-height:1.45;margin:0 0 14px;"
    "color:rgba(245,241,230,.78)}"
    "#grx-ask .grx-ask-row{display:flex;flex-wrap:wrap;gap:8px}"
    "#grx-ask .grx-ask-hint{font-size:12px;line-height:1.4;margin:10px 0 0;color:rgba(245,241,230,.6)}"
    "#grx-ask .grx-ask-btn{display:inline-block;padding:8px 12px;border-radius:8px;"
    "background:#F5F1E6;color:#172139;font-size:13px;font-weight:600;text-decoration:none}"
    "#grx-ask .grx-ask-btn:hover{background:#EBD9A8}"
    "#grx-ask .grx-ask-min{position:absolute;top:10px;right:10px;width:26px;height:26px;"
    "border-radius:50%;border:1px solid rgba(235,217,168,.45);background:transparent;"
    "color:#F5F1E6;font-size:16px;line-height:1;cursor:pointer}"
    "#grx-ask .grx-ask-pill{display:none;align-items:center;gap:8px;cursor:pointer;"
    "background:#172139;color:#F5F1E6;border:1px solid rgba(235,217,168,.45);"
    "border-radius:999px;padding:10px 16px;font:inherit;font-size:14px;font-weight:600;"
    "box-shadow:0 8px 28px rgba(23,33,57,.3)}"
    "#grx-ask.grx-collapsed .grx-ask-card{display:none}"
    "#grx-ask.grx-collapsed .grx-ask-pill{display:inline-flex}"
    "@media print{#grx-ask{display:none}}"
    "</style>"
    '<div id="grx-ask" role="complementary" aria-label="Ask your AI about Gregory Renard">'
    '<div class="grx-ask-card">'
    '<button type="button" class="grx-ask-min" aria-label="Minimize">&minus;</button>'
    '<p class="grx-ask-title">Ask your AI about Gregory</p>'
    '<p class="grx-ask-text">Explore my story, my work, my recent talks and what I stand '
    "for &mdash; in a conversation with your own AI assistant.</p>"
    f'<div class="grx-ask-row">{BUTTONS}</div>'
    '<p class="grx-ask-hint"></p>'
    "</div>"
    '<button type="button" class="grx-ask-pill">Ask your AI about Gregory</button>'
    "</div>"
    "<script>(function(){"
    "var el=document.getElementById('grx-ask'),K='grx-ask-state',s=null;"
    "try{s=localStorage.getItem(K)}catch(e){}"
    "function set(c){el.classList.toggle('grx-collapsed',c);"
    "try{localStorage.setItem(K,c?'collapsed':'open')}catch(e){}}"
    "el.classList.toggle('grx-collapsed',s?s==='collapsed':window.innerWidth<=900);"
    "el.querySelector('.grx-ask-min').addEventListener('click',function(){set(true)});"
    "el.querySelector('.grx-ask-pill').addEventListener('click',function(){set(false)});"
    "function isFr(){var as=document.querySelectorAll('a'),fr=0,en=0;for(var i=0;i<as.length;i++){var x=as[i];if(!x.offsetParent)continue;var t=(x.textContent||'').trim();if(/^parlons-en/i.test(t))fr=1;else if(/^let.?s talk/i.test(t))en=1}return fr?true:en?false:/^fr/i.test(navigator.language||'')}"
    "var hint=el.querySelector('.grx-ask-hint');"
    "function sync(){var f=isFr();hint.textContent=f?'Claude et ChatGPT s’ouvrent avec le prompt prêt : appuyez simplement sur Entrée.':'Claude and ChatGPT open with the prompt ready: just press Enter.'}"
    "sync();el.addEventListener('mouseenter',sync);"
    "el.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('.grx-ask-btn');if(a)a.href=a.getAttribute(isFr()?'data-fr':'data-en')},true);"
    "})();</script>"
)



# ---- "Let's talk" modal ---------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
_m = re.search(r'^EP = "([^"]+)"', open(os.path.join(HERE, "patch-contact-form.py"), encoding="utf-8").read(), re.M)
if not _m:
    sys.exit("add-ask-widget: could not read EP from patch-contact-form.py")
ENDPOINT = _m.group(1)

TALK_CSS = (
    '<style id="grx-talk-css">'
    "#grx-talk{position:fixed;inset:0;z-index:2147483100;display:none;align-items:center;"
    "justify-content:center;padding:16px;background:rgba(14,22,40,.62);backdrop-filter:blur(3px);"
    "font-family:var(--font-sans,'Hanken Grotesk',system-ui,sans-serif);color:#172139}"
    "#grx-talk.grx-open{display:flex}"
    "#grx-talk .grx-t-card{position:relative;width:min(500px,100%);max-height:calc(100vh - 32px);"
    "overflow:auto;background:#FAF7EF;border-radius:16px;border-top:4px solid #94731B;"
    "padding:24px 26px 22px;box-shadow:0 30px 80px rgba(14,22,40,.5)}"
    "#grx-talk .grx-t-x{position:absolute;top:14px;right:14px;width:30px;height:30px;border-radius:50%;"
    "border:1px solid rgba(23,33,57,.22);background:transparent;color:#172139;font-size:18px;"
    "line-height:1;cursor:pointer}"
    "#grx-talk .grx-t-head{display:flex;align-items:center;gap:12px;margin:0 38px 14px 0}"
    "#grx-talk .grx-t-pic{width:52px;height:52px;border-radius:50%;object-fit:cover;"
    "object-position:50% 18%;border:2px solid #94731B;flex:none}"
    "#grx-talk .grx-t-name{font-size:15px;font-weight:700;line-height:1.2}"
    "#grx-talk .grx-t-role{font-size:12px;color:rgba(23,33,57,.6);margin-top:2px}"
    "#grx-talk h2{font-family:var(--font-display,'Newsreader',Georgia,serif);font-size:28px;"
    "line-height:1.12;margin:0 0 8px;font-weight:600;letter-spacing:-.01em}"
    "#grx-talk h3{font-size:14px;margin:0 0 4px;font-weight:700}"
    "#grx-talk p{font-size:14px;line-height:1.5;margin:0 0 12px;color:rgba(23,33,57,.74)}"
    "#grx-talk .grx-t-proof{font-size:11px;letter-spacing:.09em;text-transform:uppercase;"
    "color:#7a5f14;margin:0 0 4px}"
    "#grx-talk .grx-t-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:4px}"
    "#grx-talk .grx-t-btn{flex:1 1 calc(50% - 8px);text-align:center;padding:13px 14px;border-radius:10px;"
    "background:#172139;color:#FAF7EF;font-size:15px;font-weight:700;text-decoration:none;"
    "box-shadow:0 8px 20px rgba(23,33,57,.25)}"
    "#grx-talk .grx-t-btn:hover{background:#94731B;color:#172139}"
    "#grx-talk .grx-t-hint{font-size:12.5px;margin:10px 0 12px;color:rgba(23,33,57,.6)}"
    "#grx-talk .grx-t-or{display:flex;align-items:center;gap:12px;margin:16px 0 12px;font-size:11px;"
    "letter-spacing:.14em;text-transform:uppercase;color:rgba(23,33,57,.5)}"
    "#grx-talk .grx-t-or:before,#grx-talk .grx-t-or:after{content:'';flex:1;height:1px;"
    "background:rgba(23,33,57,.16)}"
    "#grx-talk form{display:grid;gap:10px}"
    "#grx-talk .grx-t-two{display:grid;grid-template-columns:1fr 1fr;gap:10px}"
    "#grx-talk label{font-size:12px;font-weight:600;display:block;margin-bottom:4px}"
    "#grx-talk input[type=text],#grx-talk input[type=email],#grx-talk textarea{width:100%;"
    "box-sizing:border-box;padding:11px 12px;border-radius:9px;border:1px solid rgba(23,33,57,.2);"
    "background:#fff;color:#172139;font:inherit;font-size:14px}"
    "#grx-talk input:focus,#grx-talk textarea:focus{outline:2px solid #94731B;outline-offset:1px}"
    "#grx-talk textarea{min-height:92px;resize:vertical}"
    "#grx-talk .grx-t-go{padding:11px 16px;border:1px solid #172139;border-radius:10px;background:transparent;"
    "color:#172139;font:inherit;font-size:14px;font-weight:700;cursor:pointer}"
    "#grx-talk .grx-t-go:hover{background:#172139;color:#FAF7EF}"
    "#grx-talk .grx-t-err{display:none;font-size:13px;color:#a02020;margin:0}"
    "#grx-talk .grx-t-ok{display:none;text-align:center;padding:14px 0 4px}"
    "#grx-talk .grx-t-more{display:block;margin-top:14px;font-size:12px;color:rgba(23,33,57,.6)}"
    "@media (max-width:420px){#grx-talk .grx-t-two{grid-template-columns:1fr}"
    "#grx-talk .grx-t-card{padding:20px 18px 18px}#grx-talk h2{font-size:23px}}"
    "@media print{#grx-talk{display:none}}"
    "</style>"
)

TALK_HTML = """
<div id="grx-talk" role="dialog" aria-modal="true" aria-labelledby="grx-t-title">
<div class="grx-t-card">
<button type="button" class="grx-t-x" aria-label="Close">&times;</button>
<div class="grx-t-head"><img class="grx-t-pic" src="assets/greg-home-orange.jpg" alt="Gregory Renard" width="52" height="52"><div><div class="grx-t-name">Gregory Renard</div><div class="grx-t-role" data-k="role">Applied AI Architect &middot; since 1996</div></div></div>
<h2 id="grx-t-title" data-k="title">Ask your AI about Gregory.</h2>
<p data-k="lead">Get to know my story, my values and my work through your own AI assistant. Have a project? It will help you get in touch &mdash; and I&rsquo;ll tell you honestly what it takes to get there. No hype, no endless POCs.</p>
<div class="grx-t-row grx-t-main">__BUTTONS__</div>
<p class="grx-t-hint" data-k="aiP">Your assistant reads my public brief and answers your questions: my story, my values, my projects, my recent talks. Claude and ChatGPT open with the prompt ready &mdash; just press Enter.</p>
<div class="grx-t-proof" data-k="proof">NASA FDL Award of Merit &middot; UN AI for Good &middot; World Economic Forum &middot; AI-native since 1996</div>
<div class="grx-t-or" data-k="or">or</div>
<h3 data-k="formH">Prefer to write to me directly?</h3>
<form novalidate>
<div class="grx-t-two">
<div><label data-k="first">First name *</label><input type="text" name="first" autocomplete="given-name"></div>
<div><label data-k="last">Last name</label><input type="text" name="last" autocomplete="family-name"></div>
</div>
<div><label data-k="email">Work email *</label><input type="email" name="email" autocomplete="email"></div>
<div><label data-k="msg">Your project</label><textarea name="message" placeholder="Your organization, where you are with AI, what you&rsquo;d like to achieve&hellip;"></textarea></div>
<input type="text" name="company_site" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;top:-9999px;width:1px;height:1px;opacity:0;pointer-events:none">
<p class="grx-t-err" data-k="err">Please add your first name and a valid email.</p>
<button type="submit" class="grx-t-go" data-k="send">Send my message &rarr;</button>
</form>
<div class="grx-t-ok"><h3 data-k="okH">Message received.</h3><p data-k="okP">Thank you &mdash; Gregory&rsquo;s team will get back to you shortly.</p></div>
<a class="grx-t-more" href="Contact" data-k="more">Open the full contact page</a>
</div>
</div>
""".replace("__BUTTONS__", BUTTONS.replace("grx-ask-btn", "grx-t-btn"))

TALK_JS = r"""<script>(function(){
var EP='__EP__',el=document.getElementById('grx-talk');if(!el)return;
var FR={role:'Architecte IA appliquée · depuis 1996',title:'Demandez à votre IA à propos de Gregory.',lead:'Faites connaissance — mon parcours, mes valeurs, mon travail — via votre propre assistant IA. Un projet ? Il vous aidera à me contacter, et je vous dirai honnêtement ce qu’il faut pour y arriver. Sans bluff, sans POC sans fin.',proof:'NASA FDL Award of Merit · ONU AI for Good · World Economic Forum · IA native depuis 1996',formH:'Vous préférez m’écrire directement ?',first:'Prénom *',last:'Nom',email:'Email professionnel *',msg:'Votre projet',ph:'Votre organisation, où vous en êtes avec l’IA, ce que vous aimeriez accomplir…',err:'Merci d’indiquer votre prénom et un email valide.',send:'Envoyer mon message →',okH:'Message reçu.',okP:'Merci — l’équipe de Gregory revient vers vous très vite.',or:'ou',aiP:'Votre assistant lit mon brief public et répond à vos questions : mon parcours, mes valeurs, mes projets, mes interventions récentes. Claude et ChatGPT s’ouvrent avec le prompt prêt — appuyez simplement sur Entrée.',more:'Ouvrir la page de contact complète'};
var EN={},ta=el.querySelector('textarea');EN.ph=ta.getAttribute('placeholder');
[].forEach.call(el.querySelectorAll('[data-k]'),function(n){EN[n.getAttribute('data-k')]=n.innerHTML});
function lang(fr){[].forEach.call(el.querySelectorAll('[data-k]'),function(n){var k=n.getAttribute('data-k');if(fr)n.textContent=FR[k];else n.innerHTML=EN[k]});ta.setAttribute('placeholder',fr?FR.ph:EN.ph);[].forEach.call(el.querySelectorAll('.grx-t-btn'),function(a){a.href=a.getAttribute(fr?'data-fr':'data-en')})}
var last=null,f=el.querySelector('form'),err=el.querySelector('.grx-t-err'),ok=el.querySelector('.grx-t-ok');
function open(fr){last=document.activeElement;lang(fr);f.style.display='';ok.style.display='none';err.style.display='none';el.classList.add('grx-open');document.documentElement.style.overflow='hidden';setTimeout(function(){var i=el.querySelector('.grx-t-btn');i&&i.focus()},30)}
function close(){el.classList.remove('grx-open');document.documentElement.style.overflow='';last&&last.focus&&last.focus()}
document.addEventListener('click',function(e){
 if(e.metaKey||e.ctrlKey||e.shiftKey||e.button)return;
 var a=e.target.closest&&e.target.closest('a');if(!a||el.contains(a))return;
 var h=a.getAttribute('href')||'';if(!/(^|\/)Contact(\.html)?$/.test(h.split('#')[0].split('?')[0]))return;
 var t=(a.textContent||'').trim();if(!/^(let.?s talk|parlons-en)/i.test(t))return;
 e.preventDefault();open(/^parlons/i.test(t));
},true);
el.addEventListener('click',function(e){if(e.target===el||e.target.closest('.grx-t-x'))close()});
document.addEventListener('keydown',function(e){if(e.key==='Escape'&&el.classList.contains('grx-open'))close()});
f.addEventListener('submit',function(e){
 e.preventDefault();var d=new FormData(f),first=(d.get('first')||'').trim(),em=(d.get('email')||'').trim();
 if(!first||!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em)){err.style.display='block';return}
 err.style.display='none';
 try{if(!d.get('company_site'))fetch(EP,{method:'POST',mode:'no-cors',body:new URLSearchParams({firstName:first,lastName:(d.get('last')||'').trim(),email:em,message:(d.get('message')||'').trim(),company_site:''})})}catch(x){}
 f.style.display='none';ok.style.display='block';
});
})();</script>"""

TALK_BLOCK = TALK_CSS + TALK_HTML + TALK_JS.replace("__EP__", ENDPOINT)


def main():
    files = sys.argv[1:] or ["index.html"]
    n = 0
    for f in files:
        if not os.path.exists(f):
            continue
        s = open(f, encoding="utf-8").read()
        if "</body>" not in s:
            continue
        add = ""
        if os.path.basename(f) == "index.html" and 'id="grx-ask"' not in s:
            add += BLOCK
        if 'id="grx-talk"' not in s:
            add += TALK_BLOCK
        if not add:
            continue
        s = s.replace("</body>", add + "\n</body>", 1)
        open(f, "w", encoding="utf-8", newline="").write(s)
        n += 1
        print("  ask widget/modal:", f)
    print("ask-widget: %d file(s) patched" % n)


if __name__ == "__main__":
    main()
