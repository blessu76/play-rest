#!/usr/bin/env python3
"""Build play.ipe.rest, the ipe games portal. Static site, Python 3.8+ stdlib only.

Sources
  content/i18n/<lang>.json          UI strings and home copy (same keys in every language, see KEYS; AI-translated languages
                                    also MT_KEYS: the AI-translation notice, the link to the English original, "Journal (in English)")
  content/games.json                the five games: facts, links and the en/ko card copy (text keyed by language; a link with no
                                    entry for a language falls back to the English one)
  content/i18n/games/<lang>.json    the card copy of the AI-translated languages (see GAME_TEXT); game names stay as in English
  content/pages/<lang>/<page>.md    about / privacy / contact (front matter title + description + updated,
                                    Markdown body, placeholders {{OPERATOR}} {{EMAIL}} {{EFFECTIVE}})
  content/journal/<slug>.<lang>.md  journal posts (en + ko pair per slug; front matter title, description, published
                                    [KST, YYYY-MM-DDTHH:MM+09:00], optional updated / excerpt; Markdown body)
  content/shared/ipe-localtime.js   company-wide module (byte-for-byte copy of ipe-rest/shared), inlined into pages with
                                    <time data-ipe-time>: stored in KST, shown in the reader's time zone

Output (generated, never edit by hand)
  en lives at the root, every other language under /<lang>/ (decision 0087: en ko ja zh es pt id ru vi fr de):
  /  /about/  /privacy/  /contact/  /ko/ /ja/ ... same ...  /404.html  /sitemap.xml  /robots.txt  /llms.txt
  A language is built only when all of its sources are there (i18n + games text + the three pages); each page, sitemap entry
  and hreflang set lists only the languages that really have that page.
  en + ko are written by people; the other nine are AI translations of the English original: every page says so and links
  to the English page (MT_KEYS).
  Journal (JOURNAL_LANGS = en + ko only): /journal/  /journal/<slug>/  /journal/feed.xml  and  /ko/journal/ ... (list, posts,
  RSS; the home page shows the newest 3). AI-translated languages get no journal pages of their own: their journal links go to
  the English journal (marked hreflang="en", "Journal (in English)"), and their home page has no journal cards.
  There is no portal terms page: games link to their own sites.

Usage
  python3 scripts/build_site.py                 # build into the repo root
  python3 scripts/build_site.py --check         # validate sources only, write nothing
  python3 scripts/build_site.py --root DIR      # another repo-shaped folder (tests)
  python3 scripts/build_site.py --now 2026-11-01   # as of that KST date ($PLAY_NOW does the same); default: today in KST
  Date gate: a journal post whose published date is after the build date is validated but written nowhere (no page, list, home card,
  RSS item, sitemap entry or llms.txt line). The daily workflow rebuilds at 12:05 KST, so a post goes live on its publish date.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

SITE = "https://play.ipe.rest"
KST = dt.timezone(dt.timedelta(hours=9))
ASSET_V = "20261031i"  # keep in sync: bump when assets/play.css or play.js change
SITE_UPDATED = "2026-11-01"  # "Last updated" of home / 404 and sitemap lastmod: bump by hand when their text changes
OPERATOR = "Davy Kim (ipe Studio)"
EMAIL = "ipe.haven@gmail.com"
EFFECTIVE = "2026-11-01"
# GA4 (same property as ipe.rest). Inserted once into every page by render(); the privacy policy (section 2), the contact FAQ,
# llms.txt and CLAUDE.md say so -> change them together with this.
GA_MEASUREMENT_ID = "G-XG4BH800J0"
GA_SNIPPET = (
    "<script>(function(){var GA_ID='%s';"
    # local preview (localhost / 127.0.0.1 / file:// = empty hostname): no gtag load, no events
    "var H=location.hostname;if(!H||H==='localhost'||H==='127.0.0.1')return;"
    "var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+GA_ID;document.head.appendChild(s);"
    "window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments)};"
    "window.gtag('js',new Date());window.gtag('config',GA_ID);"
    # game-card buttons and footer game links point to *.ipe.rest, which the outbound handler skips -> own event (game id + link address + card|footer)
    "function track(e){if(e.type==='auxclick'&&e.button!==1)return;"
    "var a=e.target.closest&&e.target.closest('a[href^=\"http\"]');if(!a)return;"
    "var g=a.getAttribute('data-game');"
    "if(g){window.gtag('event','select_game',{game:g,placement:a.getAttribute('data-placement')||'card',link_url:a.href,transport_type:'beacon'});return}"
    "var h=a.hostname;if(h==='ipe.rest'||/\\.ipe\\.rest$/.test(h))return;"
    "window.gtag('event','outbound_click',{link_url:a.href,link_domain:h,transport_type:'beacon'})}"
    "document.addEventListener('click',track);document.addEventListener('auxclick',track)})();</script>") % GA_MEASUREMENT_ID
ORG_ID = "https://ipe.rest/#organization"
ORG = {"@type": "Organization", "@id": ORG_ID, "name": "ipe()", "url": "https://ipe.rest/"}
GEN_MARK = "generated by scripts/build_site.py"
OG_IMAGE = "/assets/og-image.png"
TITLE_MAX, DESC_MAX = 60, 160

# order = language switcher order. (name, og locale, direction, short code). Decision 0087 (11 languages); Arabic is not
# offered on this portal.
LANGS = {"en": ("English", "en_US", "ltr", "EN"), "ko": ("한국어", "ko_KR", "ltr", "KO"), "ja": ("日本語", "ja_JP", "ltr", "JA"),
         "zh": ("简体中文", "zh_CN", "ltr", "ZH"), "es": ("Español", "es_ES", "ltr", "ES"), "pt": ("Português", "pt_BR", "ltr", "PT"),
         "id": ("Bahasa Indonesia", "id_ID", "ltr", "ID"), "ru": ("Русский", "ru_RU", "ltr", "RU"), "vi": ("Tiếng Việt", "vi_VN", "ltr", "VI"),
         "fr": ("Français", "fr_FR", "ltr", "FR"), "de": ("Deutsch", "de_DE", "ltr", "DE")}
EN_NAMES = {"en": "English", "ko": "Korean", "ja": "Japanese", "zh": "Chinese (Simplified)", "es": "Spanish", "pt": "Portuguese (Brazil)",
            "id": "Indonesian", "ru": "Russian", "vi": "Vietnamese", "fr": "French", "de": "German"}  # llms.txt is in English
MAIN_LANGS = ("en", "ko")  # written (and checked) by people; must always be complete
SOURCE_LANG = "en"  # the original every AI translation is made from (and links back to)
MT_LANGS = tuple(l for l in LANGS if l not in MAIN_LANGS)  # AI translations, shown with a label + a link to the original
JOURNAL_LANGS = MAIN_LANGS  # journal posts are written in en + ko only
# translated card copy of a game (content/i18n/games/<lang>.json); name and sub are names, they stay as in English
GAME_TEXT = ("status", "platform", "pricing", "tagline")
PAGE_SLUGS = ("about", "privacy", "contact")
JOURNAL_DIR = "journal"
RESERVED_SLUGS = {"feed"}  # /journal/feed.xml is the RSS file, no post may take that URL segment
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PUBLISHED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+09:00$")  # published time is always recorded in KST
HOME_CARDS = 3
EXCERPT_MAX = 200
GAME_IDS = ("iltonggi", "inkisle", "sunmeld", "claimball", "patchland")
# which games keep which principle (docs ch.2). Sunmeld has no public round length, so it is not listed under principle 1.
PRINCIPLE_GAMES = {1: ("iltonggi", "inkisle", "claimball", "patchland"), 2: GAME_IDS, 3: ("iltonggi", "inkisle", "sunmeld", "claimball"), 4: GAME_IDS, 5: ("iltonggi", "inkisle", "sunmeld", "claimball")}
COMPARE_ROWS = "oneline style length difficulty players platform offline pricing languages status".split()
# first-paint theme: runs before the stylesheet so data-theme (and the address-bar colour) is right on the first frame
THEME_HEAD_SCRIPT = ("<script>(function(){var t,C={light:'#fbfcfe',dark:'#0c1118',noir:'#0a0810'};try{t=localStorage.getItem('play-theme')}catch(e){}"
                     "if(({light:1,dark:1,noir:1})[t]!==1)t=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light';"
                     "document.documentElement.setAttribute('data-theme',t);var m=document.querySelectorAll('meta[name=theme-color]');"
                     "for(var i=0;i<m.length;i++)m[i].content=C[t]})()</script>")
_ICO = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"%s aria-hidden="true" focusable="false">%s</svg>'
GLOBE_ICON = _ICO % ("", '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>')
THEME_ICONS = (
    ("light", _ICO % ("", '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>')),
    ("dark", _ICO % ("", '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>')),
    ("noir", _ICO % (' stroke-linejoin="round"', '<path d="M6 4h12l4 6-10 11L2 10z"/><path d="M2 10h20M9 4l3 6 3-6M12 10v11"/>')),
)
KEYS = (
    "nav_home nav_games nav_about nav_journal nav_contact nav_privacy skip lang_label theme_label theme_light theme_dark theme_noir updated_label crumb_home "
    "home_title home_desc hero_code hero_h1 hero_sub hero_strip_aria "
    "phil_h phil_rest phil_kept p1_h p1_p p2_h p2_p p3_h p3_p p4_h p4_p p5_h p5_p "
    "games_h games_lead g_likes g_nots g_visit g_terms g_blog g_status "
    "compare_h compare_lead compare_note compare_game row_oneline row_style row_length row_difficulty row_players "
    "row_platform row_offline row_pricing row_languages row_status "
    "choose_h choose_lead choose_1 choose_2 choose_3 choose_4 choose_5 choose_go "
    "made_h made_lead made_now made_feed made_read ipe_h ipe_p ipe_studio ipe_music ipe_contact "
    "footer_line footer_code footer_tm footer_games footer_terms footer_site footer_about nf_h nf_p "
    "journal_h journal_lead journal_all journal_empty journal_desc journal_rss journal_back journal_feed_title"
).split()
MT_KEYS = ("ai_note", "ai_original", "journal_en", "en_mark")  # required in the AI-translated languages; en.json holds the English source
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# link targets that may become an href: http(s), a site path (not protocol-relative), a fragment, mailto
HREF_OK = re.compile(r"^(?:https?://[^\s/]|/(?![/\\])|#|mailto:[^\s])", re.I)
FENCE = re.compile(r"^(`{3,})[ \t]*[\w+-]*[ \t]*$")
# never in public text: local paths, internal tools, secrets
FORBIDDEN = ("/Users/", "ipe-harness", "ipe-room", "claude.ai/", "AuthKey_", "api_key", "sk-ant", "SLACK_BOT_TOKEN", ".env")
# brand / policy rules for every public text: no trademarked game names (the sunmeld list plus the other well-known
# drop / merge / ball games), no emoji
BANNED_WORDS = re.compile(r"\bsuika\b|수박\s?게임|watermelon game|\bpong\b|\bbreakout\b|\barkanoid\b|\bsplatoon\b|\bclash of clans\b", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
BOTS = ("GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-Web", "anthropic-ai", "PerplexityBot",
        "Google-Extended", "Applebot-Extended", "CCBot", "Bytespider", "Amazonbot", "cohere-ai", "Meta-ExternalAgent")
PRICE = re.compile(r"[$€₩]\s?\d|\d\s?(?:USD|KRW|원)\b|\d+\+? (?:downloads|reviews|ratings)|(?:다운로드|리뷰|평점)\s?\d", re.I)


def esc(s):
    return html.escape(str(s), quote=True)


def valid_date(value):
    """'2026-11-01' -> True only for a real calendar date (2026-13-45 and 2026-02-30 are not)"""
    if not DATE_RE.match(value or ""):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def text_problems(where, text):
    """policy checks on any public text -> list of errors"""
    errs = ["%s: forbidden text %r" % (where, bad) for bad in FORBIDDEN if bad in text]
    if BANNED_WORDS.search(text):
        errs.append("%s: banned word %r" % (where, BANNED_WORDS.search(text).group(0)))
    if EMOJI.search(text):
        errs.append("%s: emoji are not allowed" % where)
    if PRICE.search(text):
        errs.append("%s: prices, ratings and download counts are not allowed" % where)
    return errs


# ---------------------------------------------------------------- paths
def lp(lang):
    return "" if lang == "en" else "/" + lang


def path_home(lang):
    return lp(lang) + "/"


def path_page(lang, slug):
    return "%s/%s/" % (lp(lang), slug)


def path_journal(lang):
    return "%s/%s/" % (lp(lang), JOURNAL_DIR)


def path_post(lang, slug):
    return "%s/%s/%s/" % (lp(lang), JOURNAL_DIR, slug)


def path_feed(lang):
    return path_journal(lang) + "feed.xml"


def url(path):
    return SITE + path


# ---------------------------------------------------------------- front matter + markdown
def parse_front(text):
    m = re.match(r"^---\n(.*?)\n---[ \t]*\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, sep, v = line.partition(":")
        if not sep:
            raise ValueError("bad front matter line: %r" % line)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k.strip()] = v
    return meta, m.group(2).strip("\n")


def link(m):
    """[text](url) -> <a> only for an allowed href (see HREF_OK); anything else (javascript:, data:, ...) keeps just the text.
    Runs on already-escaped text, so quotes and ampersands in the url are entities and cannot leave the attribute."""
    text, href = m.group(1), m.group(2)
    if not HREF_OK.match(href):
        return text
    return '<a href="%s"%s>%s</a>' % (href, ' rel="noopener"' if href.lower().startswith("http") else "", text)


def inline(s):
    codes = []
    s = s.replace("\x00", "")  # \x00 marks stashed code spans below; source text must not forge it

    def stash(m):
        codes.append("<code>%s</code>" % esc(m.group(1)))
        return "\x00%d\x00" % (len(codes) - 1)

    s = re.sub(r"`([^`]+)`", stash, s)
    s = esc(s)
    # the url may hold one level of balanced parentheses, e.g. https://en.wikipedia.org/wiki/Go_(game)
    s = re.sub(r"\[([^\]]+)\]\(((?:[^()\s\x00]|\([^()\s\x00]*\))+)\)", link, s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], s)


def markdown(text):
    """Small Markdown subset: paragraphs, ## to #### headings, lists, blockquotes, hr, ``` code fences, inline code/links/bold/italic.
    Not supported (write around them): nested lists, images, tables, raw HTML (it is shown as text)."""
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)
    para = []

    def flush():
        if para:
            out.append("<p>%s</p>" % inline(" ".join(x.strip() for x in para)))
            para.clear()

    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush(); i += 1; continue
        fm = FENCE.match(s)
        if fm:  # fenced code: everything up to the closing fence is literal text
            flush(); code = []; i += 1
            while i < n and not re.match(r"^`{%d,}[ \t]*$" % len(fm.group(1)), lines[i].strip()):
                code.append(lines[i].rstrip("\r")); i += 1
            i += 1  # the closing fence (an unclosed fence runs to the end of the text)
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(code)))
            continue
        m = re.match(r"^(#{2,4})\s+(.*)$", s)
        if m:
            flush(); lvl = len(m.group(1))
            out.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl)); i += 1; continue
        if s.startswith(">"):
            flush(); quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^>\s?", "", lines[i].strip())); i += 1
            out.append("<blockquote>%s</blockquote>" % markdown("\n".join(quote)))
            continue
        if re.match(r"^-{3,}$", s):
            flush(); out.append("<hr>"); i += 1; continue
        if re.match(r"^[-*]\s+", s) or re.match(r"^\d+\.\s+", s):
            flush(); ordered = bool(re.match(r"^\d+\.", s)); items = []
            start = int(re.match(r"\d+", s).group(0)) if ordered else 1
            while i < n and re.match(r"^(?:[-*]|\d+\.)\s+", lines[i].strip()):
                items.append(re.sub(r"^(?:[-*]|\d+\.)\s+", "", lines[i].strip())); i += 1
            tag = "ol" if ordered else "ul"
            attr = ' start="%d"' % start if ordered and start != 1 else ""  # a list split by a blank line keeps counting
            out.append("<%s%s>%s</%s>" % (tag, attr, "".join("<li>%s</li>" % inline(x) for x in items), tag))
            continue
        para.append(ln); i += 1
    flush()
    return "\n".join(out)


# ---------------------------------------------------------------- loading
def load_i18n(root):
    d, errs = {}, []
    for f in sorted((Path(root) / "content" / "i18n").glob("*.json")):
        lang = f.stem
        if lang not in LANGS:
            errs.append("i18n/%s.json: unknown language" % lang); continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as ex:
            errs.append("i18n/%s.json: %s" % (lang, ex)); continue
        need = list(KEYS) + (list(MT_KEYS) if lang in MT_LANGS else [])
        miss = [k for k in need if not str(data.get(k, "")).strip()]
        extra = [k for k in data if k not in KEYS and k not in MT_KEYS]
        if miss:
            errs.append("i18n/%s.json: missing %s" % (lang, ", ".join(miss)))
        if extra:
            errs.append("i18n/%s.json: unknown keys %s" % (lang, ", ".join(extra)))
        for k, v in data.items():
            errs += text_problems("i18n/%s.json %s" % (lang, k), str(v))
        for k in ("home_title",):
            if len(data.get(k, "")) > TITLE_MAX:
                errs.append("i18n/%s.json: %s longer than %d characters" % (lang, k, TITLE_MAX))
        if len(data.get("home_desc", "")) > DESC_MAX:
            errs.append("i18n/%s.json: home_desc longer than %d characters" % (lang, DESC_MAX))
        if not miss:
            d[lang] = data
    return d, errs


def load_pages(root):
    pages, errs = {}, []
    for lang in LANGS:
        for slug in PAGE_SLUGS:
            f = Path(root) / "content" / "pages" / lang / (slug + ".md")
            if not f.is_file():
                continue
            try:
                meta, body = parse_front(f.read_text(encoding="utf-8"))
            except ValueError as ex:
                errs.append("%s: %s" % (f, ex)); continue
            for k in ("title", "description", "updated"):
                if not meta.get(k):
                    errs.append("%s/%s: missing %s" % (lang, f.name, k))
            if meta.get("updated") and not valid_date(meta["updated"]):
                errs.append("%s/%s: updated must look like 2026-10-31" % (lang, f.name))
            if len(meta.get("description", "")) > DESC_MAX:
                errs.append("%s/%s: description longer than %d characters" % (lang, f.name, DESC_MAX))
            if len(meta.get("title", "")) + len(" — play.ipe.rest") > TITLE_MAX:
                errs.append("%s/%s: title too long for the <title> limit" % (lang, f.name))
            errs += text_problems("%s/%s" % (lang, slug), meta.get("title", "") + meta.get("description", "") + body)
            pages[(lang, slug)] = (meta, body)
    return pages, errs


def parse_published(value):
    """'2026-11-01T09:30+09:00' -> aware datetime in KST, or None when it is not a real KST time"""
    if not PUBLISHED_RE.match(value or ""):
        return None
    try:
        return dt.datetime.fromisoformat(value).astimezone(KST)  # a real calendar date and clock time, at +09:00
    except ValueError:
        return None


def resolve_today(now=None):
    """the build's reference date (a KST calendar date): `now` (date / 'YYYY-MM-DD' / datetime) > $PLAY_NOW > the current KST date"""
    now = now or os.environ.get("PLAY_NOW") or dt.datetime.now(KST)
    if isinstance(now, str):
        if not valid_date(now):
            raise ValueError("--now / PLAY_NOW must be a real date like 2026-11-01, got %r" % now)
        return dt.date.fromisoformat(now)
    return now.astimezone(KST).date() if isinstance(now, dt.datetime) else now


def released(post, today):
    """a post is public from its KST publish date on (the whole day: the daily build runs once, at noon KST)"""
    return post["published"][:10] <= today.isoformat()


def load_journal(root):
    """content/journal/<slug>.<lang>.md -> (posts newest first, errors).
    post = {slug, published, updated, langs: {lang: {title, description, excerpt, body}}}; every post has both journal languages.
    Builders never index p["langs"][lang] blindly: they go through post_langs() / ctx.posts_in(), so a page is made only for the
    languages a post really has."""
    jdir = Path(root) / "content" / JOURNAL_DIR
    errs, found = [], {}
    for f in sorted(jdir.glob("*.md")) if jdir.is_dir() else []:
        stem, _, lang = f.stem.rpartition(".")
        tag = "journal/" + f.name
        if not stem or lang not in JOURNAL_LANGS:
            errs.append("%s: file name must be <slug>.<%s>.md (journal posts are written in %s only)" % (
                tag, "|".join(JOURNAL_LANGS), " + ".join(JOURNAL_LANGS))); continue
        if not SLUG_RE.match(stem) or stem in RESERVED_SLUGS:
            errs.append("%s: slug %r must be lowercase letters, digits and single hyphens (and not %s)" % (tag, stem, "/".join(sorted(RESERVED_SLUGS)))); continue
        try:
            meta, body = parse_front(f.read_text(encoding="utf-8"))
        except ValueError as ex:
            errs.append("%s: %s" % (tag, ex)); continue
        if not meta.get("published") and meta.get("published_at"):
            meta["published"] = meta["published_at"]  # alias used by the manuscript drafts
        n0 = len(errs)
        for k in ("title", "description", "published"):
            if not meta.get(k):
                errs.append("%s: missing %s" % (tag, k))
        pub = parse_published(meta.get("published"))
        if meta.get("published") and not pub:
            errs.append("%s: published must be a KST time like 2026-11-01T09:30+09:00" % tag)
        upd = meta.get("updated") or (meta["published"][:10] if meta.get("published") else "")
        if upd and not (valid_date(upd) and (not pub or upd >= meta["published"][:10])):
            errs.append("%s: updated must look like 2026-11-01 and not be before published" % tag)
        if len(meta.get("description", "")) > DESC_MAX:
            errs.append("%s: description longer than %d characters" % (tag, DESC_MAX))
        if len(meta.get("excerpt", "")) > EXCERPT_MAX:
            errs.append("%s: excerpt longer than %d characters" % (tag, EXCERPT_MAX))
        if len(meta.get("title", "")) > TITLE_MAX:
            errs.append("%s: title longer than %d characters" % (tag, TITLE_MAX))
        if meta.get("lang") and meta["lang"] != lang:
            errs.append("%s: front matter lang %r does not match the file name" % (tag, meta["lang"]))
        if not body.strip():
            errs.append("%s: empty body" % tag)
        if re.search(r"(?m)^#\s", re.sub(r"(?ms)^`{3,}.*?(?:^`{3,}[ \t]*$|\Z)", "", body)):  # '# ' inside a code fence is fine
            errs.append("%s: body must not contain a '# ' heading (the title is the h1); use ## and below" % tag)
        errs += text_problems(tag, meta.get("title", "") + " " + meta.get("description", "") + " " + meta.get("excerpt", "") + " " + body)
        if len(errs) == n0:
            found.setdefault(stem, {})[lang] = {"title": meta["title"], "description": meta["description"],
                                                "excerpt": meta.get("excerpt") or meta["description"], "body": body,
                                                "published": meta["published"], "updated": upd}
    posts = []
    for slug, langs in found.items():
        missing = [l for l in MAIN_LANGS if l not in langs]
        if missing:
            errs.append("journal/%s: missing the %s version (every post needs en and ko)" % (slug, "/".join(missing))); continue
        if len({v["published"] for v in langs.values()}) != 1:
            errs.append("journal/%s: en and ko must have the same published time" % slug); continue
        posts.append({"slug": slug, "published": langs["en"]["published"], "updated": max(v["updated"] for v in langs.values()), "langs": langs})
    posts.sort(key=lambda p: (parse_published(p["published"]), p["slug"]), reverse=True)
    return posts, errs


def _bilingual(v, tag, errs):
    if not isinstance(v, dict) or any(not str(v.get(l, "")).strip() for l in MAIN_LANGS):
        errs.append("%s: needs a non-empty text for each of %s" % (tag, "/".join(MAIN_LANGS)))
        return
    for l in MAIN_LANGS:
        errs += text_problems("%s.%s" % (tag, l), str(v[l]))


def load_games(root):
    f = Path(root) / "content" / "games.json"
    if not f.is_file():
        return [], ["content/games.json: missing"]
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))["games"]
    except (ValueError, KeyError, TypeError) as ex:
        return [], ["content/games.json: %s" % ex]
    errs = []
    ids = [g.get("id") for g in raw]
    if tuple(ids) != GAME_IDS:
        errs.append("games.json: games must be exactly %s in this order, got %s" % (", ".join(GAME_IDS), ids))
    for g in raw:
        tag = "games.json %s" % g.get("id")
        for k in ("name", "sub", "status", "platform", "pricing", "tagline"):
            _bilingual(g.get(k), "%s %s" % (tag, k), errs)
        if not str(g.get("url", "")).startswith("https://%s.ipe.rest" % g.get("id")):
            errs.append("%s: url must be https://%s.ipe.rest..." % (tag, g.get("id")))
        if not (Path(root) / "assets" / "games" / str(g.get("icon", "-"))).is_file():
            errs.append("%s: icon file missing" % tag)
        if not (isinstance(g.get("accent"), list) and len(g["accent"]) == 2 and all(re.match(r"^#[0-9a-fA-F]{6}$", c) for c in g["accent"])):
            errs.append("%s: accent must be two #rrggbb colors" % tag)
        for key, want in (("pros", 3), ("cons", 2)):
            items = g.get(key)
            if not isinstance(items, list) or len(items) != want:
                errs.append("%s: %s needs %d items" % (tag, key, want)); continue
            for i, it in enumerate(items):
                _bilingual(it.get("h"), "%s %s[%d].h" % (tag, key, i), errs)
                _bilingual(it.get("p"), "%s %s[%d].p" % (tag, key, i), errs)
        if g.get("terms") is not None:
            _bilingual(g["terms"], "%s terms" % tag, errs)
        j = g.get("journal") or {}  # optional: a game with no journal yet (journal null) gets no journal link and no "making of" row
        if g.get("journal") is not None:
            for k in ("label", "url", "feed"):
                _bilingual(j.get(k), "%s journal.%s" % (tag, k), errs)
        c = g.get("compare") or {}
        for row in COMPARE_ROWS:
            _bilingual(c.get(row), "%s compare.%s" % (tag, row), errs)
        if not g.get("platforms") or not g.get("genre"):
            errs.append("%s: platforms and genre are needed for JSON-LD" % tag)
        urls = [g.get("url", "")] + [x for k in ("terms",) if g.get(k) for x in g[k].values()] + \
               [x for k in ("url", "feed") for x in (j.get(k) or {}).values()]
        for u in urls:
            if not str(u).startswith("https://%s.ipe.rest" % g.get("id")):
                errs.append("%s: link %s is not on the game's own site" % (tag, u))
    return raw, errs


def load_game_text(root, games):
    """content/i18n/games/<lang>.json -> merges the translated card copy into games (g[field][lang]); -> (languages complete, errors).
    Shape: {"<game id>": {status, platform, pricing, tagline, pros: [{h, p}] x3, cons: [{h, p}] x2, journal_label, compare: {row: text}}}.
    Names stay as in English (no translated game names)."""
    done, errs = [], []
    by_id = {g.get("id"): g for g in games}
    for lang in MT_LANGS:
        f = Path(root) / "content" / "i18n" / "games" / (lang + ".json")
        if not f.is_file():
            continue
        tag = "i18n/games/%s.json" % lang
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as ex:
            errs.append("%s: %s" % (tag, ex)); continue
        n0 = len(errs)
        if sorted(data) != sorted(by_id):
            errs.append("%s: needs exactly the games %s" % (tag, ", ".join(GAME_IDS))); continue
        for gid, d in data.items():
            g, where = by_id[gid], "%s %s" % (tag, gid)

            def text(v, name):
                if not isinstance(v, str) or not v.strip():
                    errs.append("%s: %s is missing" % (where, name)); return ""
                errs.extend(text_problems("%s %s" % (where, name), v))
                return v
            vals = {k: text(d.get(k), k) for k in GAME_TEXT}
            items = {}
            for key in ("pros", "cons"):
                src = d.get(key)
                if not isinstance(src, list) or len(src) != len(g.get(key) or []):
                    errs.append("%s: %s needs %d items" % (where, key, len(g.get(key) or []))); continue
                items[key] = [(text((it or {}).get("h"), "%s[%d].h" % (key, i)), text((it or {}).get("p"), "%s[%d].p" % (key, i))) for i, it in enumerate(src)]
            label = text(d.get("journal_label"), "journal_label") if g.get("journal") else ""
            cmp_ = d.get("compare") if isinstance(d.get("compare"), dict) else {}
            cells = {r: text(cmp_.get(r), "compare." + r) for r in COMPARE_ROWS}
            if len(errs) > n0:
                continue
            for k, v in vals.items():
                g[k][lang] = v
            for key, pairs in items.items():
                for it, (h, p_) in zip(g[key], pairs):
                    it["h"][lang], it["p"][lang] = h, p_
            if g.get("journal"):
                g["journal"]["label"][lang] = label
            for r, v in cells.items():
                g["compare"][r][lang] = v
            g["name"][lang], g["sub"][lang] = g["name"][SOURCE_LANG], g["sub"][SOURCE_LANG]
        if len(errs) == n0:
            done.append(lang)
    return done, errs


EN_LINK = ' hreflang="%s"' % SOURCE_LANG  # an <a> whose target is the English page of a game site / the journal


def loc_link(ctx, links, lang):
    """(href, attrs, mark) of a game link: the language's own page, else the English one -- which is then said openly: hreflang="en"
    and, in the AI-translated languages, the same "(in English)" mark the portal's own journal link carries (en_mark)"""
    if links.get(lang):
        return links[lang], "", ""
    mark = ctx.t(lang, "en_mark") if lang in MT_LANGS else ""
    return links[SOURCE_LANG], EN_LINK, (mark if mark.startswith("（") else " " + mark) if mark else ""


# ---------------------------------------------------------------- html pieces
def langpick_script(root, langs):
    """The root page's language picker (assets/langpick.js) inlined with the languages this build has."""
    src = (Path(root) / "assets" / "langpick.js").read_text(encoding="utf-8")
    src = re.sub(r"/\*.*?\*/", "", src, count=1, flags=re.S)
    return "<script>%s</script>" % re.sub(r"\s*\n\s*", "", src.replace("/*SUPPORTED*/[]", json.dumps(list(langs)))).strip()


def localtime_script(root):
    """shared/ipe-localtime.js inlined byte for byte (no whitespace added around it): <time data-ipe-time> is stored in KST
    and shown in the reader's time zone. Inline on purpose (no external load); the test pins its SHA-256."""
    return "<script>" + (Path(root) / "content" / "shared" / "ipe-localtime.js").read_bytes().decode("utf-8") + "</script>"


def time_tag(published):
    """<time> of a post time: ISO with +09:00 for machines, '2026-11-01 09:30 KST' as the static text (no JS / crawlers)"""
    return '<time datetime="%s" data-ipe-time dir="ltr">%s %s KST</time>' % (esc(published), esc(published[:10]), esc(published[11:16]))


class Ctx:
    def __init__(self, root, i18n, pages, games, langs, posts=()):
        self.root, self.i18n, self.pages, self.games, self.langs, self.posts = root, i18n, pages, games, langs, list(posts)
        self.journal_langs = [l for l in langs if l in JOURNAL_LANGS]

    def t(self, lang, key):
        return self.i18n[lang][key]

    def posts_in(self, lang):
        """posts that have a version in this language (newest first); [] for a language with no journal"""
        return [p for p in self.posts if lang in self.journal_langs and lang in p["langs"]]

    def journal_lang(self, lang):
        """the language whose journal a page in `lang` links to: its own, else the English original (decision 0087: en is the default)"""
        return lang if lang in self.journal_langs else SOURCE_LANG

    def sub(self, text):
        return (text.replace("{{OPERATOR}}", OPERATOR).replace("{{EMAIL}}", EMAIL).replace("{{EFFECTIVE}}", EFFECTIVE)
                .replace("{{SITE}}", SITE))


def post_langs(ctx, p):
    """the built languages this post has a version in"""
    return [l for l in ctx.journal_langs if l in p["langs"]]


def render(ctx, lang, *, path, title, desc, body, graph, alt, updated, og_type="website", noindex=False, hreflang=True, nav=""):
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    name, og_loc, direction, short = LANGS[lang]
    jl = ctx.journal_lang(lang)  # en for a language without a journal of its own
    jattr = ' hreflang="%s"' % jl if jl != lang else ""
    canonical = url(path)
    head = ['<meta charset="utf-8">', '<meta name="viewport" content="width=device-width,initial-scale=1">',
            "<title>%s</title>" % esc(title), '<meta name="description" content="%s">' % esc(desc)]
    head.append('<meta name="robots" content="%s">' % ("noindex,follow" if noindex else "index,follow,max-image-preview:large"))
    head.append('<link rel="canonical" href="%s">' % esc(canonical))
    if hreflang and len(alt) > 1:
        for l, pth in alt.items():
            head.append('<link rel="alternate" hreflang="%s" href="%s">' % (l, esc(url(pth))))
        head.append('<link rel="alternate" hreflang="x-default" href="%s">' % esc(url(alt.get("en", next(iter(alt.values()))))))
    head += ['<meta property="og:type" content="%s">' % og_type, '<meta property="og:site_name" content="ipe() Games">',
             '<meta property="og:title" content="%s">' % esc(title), '<meta property="og:description" content="%s">' % esc(desc),
             '<meta property="og:url" content="%s">' % esc(canonical), '<meta property="og:locale" content="%s">' % og_loc,
             '<meta property="og:image" content="%s">' % (SITE + OG_IMAGE), '<meta property="og:image:width" content="1200">',
             '<meta property="og:image:height" content="630">', '<meta name="twitter:card" content="summary_large_image">',
             '<meta name="twitter:title" content="%s">' % esc(title), '<meta name="twitter:description" content="%s">' % esc(desc),
             '<meta name="twitter:image" content="%s">' % (SITE + OG_IMAGE),
             '<meta name="theme-color" content="#fbfcfe" media="(prefers-color-scheme: light)">',
             '<meta name="theme-color" content="#0c1118" media="(prefers-color-scheme: dark)">',
             '<meta name="color-scheme" content="light dark">',
             THEME_HEAD_SCRIPT,
             '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">',
             '<link rel="apple-touch-icon" href="/assets/icon-180.png">',
             '<link rel="preload" href="/assets/fonts/inter-400.woff2" as="font" type="font/woff2" crossorigin>',
             '<link rel="alternate" type="application/rss+xml" title="%s" href="%s">' % (esc(ctx.t(jl, "journal_feed_title")), esc(path_feed(jl))),
             '<link rel="stylesheet" href="/assets/play.css?v=%s">' % ASSET_V]
    if path == "/":
        head.append(langpick_script(ctx.root, ctx.langs))
    head.append('<script type="application/ld+json">%s</script>' % json.dumps({"@context": "https://schema.org", "@graph": graph},
                                                                            ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    # language switcher: a <details> menu (works without JS); each item is this page in that language, or that language's
    # home when this page has no version there (a journal page in ja -> /ja/), never a page that does not exist
    switch = "".join('<li><a href="%s" hreflang="%s" lang="%s"%s>%s</a></li>' % (
        esc(alt.get(l) or path_home(l)), l, l, ' aria-current="true"' if l == lang else "", esc(LANGS[l][0])) for l in ctx.langs)
    langsw = ('<details class="langsw"><summary aria-label="%s: %s">%s<span class="langsw__cur" aria-hidden="true">%s</span></summary>'
              '<ul class="langsw__list" aria-label="%s">%s</ul></details>') % (
        esc(t("lang_label")), esc(name), GLOBE_ICON, esc(short), esc(t("lang_label")), switch)
    jhref, jnav_attr, jnav_mark = loc_link(ctx, {jl: path_journal(jl)}, lang)  # a language without its own journal says "(in English)" here too
    navlinks = [(path_home(lang) + "#games", t("nav_games"), "games", ""), (path_page(lang, "about"), t("nav_about"), "about", ""),
                (jhref, t("nav_journal") + jnav_mark, "journal", jnav_attr), (path_page(lang, "contact"), t("nav_contact"), "contact", "")]
    nav_html = "".join('<a href="%s"%s%s>%s</a>' % (esc(h), a, ' aria-current="page"' if nav == k else "", esc(label)) for h, label, k, a in navlinks)
    theme_btns = "".join('<button type="button" data-theme-set="%s" aria-pressed="false" aria-label="%s" title="%s">%s</button>' % (
        k, esc(t("theme_" + k)), esc(t("theme_" + k)), svg) for k, svg in THEME_ICONS)
    header = ('<header class="site-header"><div class="wrap bar"><a class="brand" href="%s" aria-label="ipe() Games"><span class="logo">ipe()</span>'
              '<span class="brand-sub">games</span></a><nav class="nav" aria-label="main">%s</nav>'
              '<div class="tools">%s<div class="themesw" role="group" aria-label="%s">%s</div></div></div></header>') % (
        esc(path_home(lang)), nav_html, langsw, esc(t("theme_label")), theme_btns)
    game_links = "".join('<li><a href="%s" rel="noopener" data-game="%s" data-placement="footer">%s</a></li>' % (
        esc(g["url"]), esc(g["id"]), esc(g["name"][lang])) for g in ctx.games)
    terms_links = "".join('<li><a href="%s" rel="noopener"%s>%s</a></li>' % (esc(h), a, esc(g["name"][lang] + m))
                          for g in ctx.games if g.get("terms") for h, a, m in [loc_link(ctx, g["terms"], lang)])
    site_links = ('<li><a href="https://ipe.rest/" rel="noopener">ipe.rest</a></li><li><a href="%s">%s</a></li><li><a href="%s"%s>%s</a></li>'
                  '<li><a href="%s">%s</a></li><li><a href="%s">%s</a></li>') % (
        esc(path_page(lang, "about")), esc(t("footer_about")), esc(path_journal(jl)), jattr, esc(t("nav_journal") if jl == lang else t("journal_en")),
        esc(path_page(lang, "contact")), esc(t("nav_contact")),
        esc(path_page(lang, "privacy")), esc(t("nav_privacy")))
    foot_langs = ('<p class="foot-langs" aria-label="%s">%s</p>' % (esc(t("lang_label")), " ".join(
        '<a href="%s" hreflang="%s" lang="%s"%s>%s</a>' % (esc(alt.get(l) or path_home(l)), l, l, ' aria-current="true"' if l == lang else "", esc(LANGS[l][0]))
        for l in ctx.langs))) if len(ctx.langs) > 1 else ""
    footer = ('<footer class="site-footer"><div class="wrap"><div class="foot-grid">'
              '<div class="foot-brand"><span class="logo">ipe()</span><p>%s<br>© 2026 %s</p><p class="mono small">%s</p><p class="small">%s</p></div>'
              '<div><h2 class="foot-h">%s</h2><ul>%s</ul></div><div><h2 class="foot-h">%s</h2><ul>%s</ul></div><div><h2 class="foot-h">%s</h2><ul>%s</ul></div>'
              '</div>%s</div></footer>') % (
        esc(t("footer_line")), esc(OPERATOR), esc(t("footer_code")), esc(t("footer_tm")), esc(t("footer_games")), game_links,
        esc(t("footer_terms")), terms_links, esc(t("footer_site")), site_links, foot_langs)
    last = '<p class="updated mono">%s: <time datetime="%s">%s</time></p>' % (esc(t("updated_label")), esc(updated), esc(updated))
    # decision 0087: the nine non-native languages are AI translations -> a visible label + a link to the English original
    mt = ""
    if lang in MT_LANGS:
        mt = '<div class="mtnote" role="note"><div class="wrap"><p>%s <a href="%s" hreflang="%s">%s</a></p></div></div>' % (
            esc(t("ai_note")), esc(alt[SOURCE_LANG]), SOURCE_LANG, esc(t("ai_original")))
    return ('<!doctype html>\n<!-- %s -->\n<html lang="%s" dir="%s"><head>%s</head><body>'
            '<a class="skip" href="#main">%s</a>%s<main id="main">%s%s<div class="wrap">%s</div></main>%s'
            '<script src="/assets/play.js?v=%s" defer></script>%s%s</body></html>\n') % (
        GEN_MARK, lang, direction, "\n".join(head), esc(t("skip")), header, mt, body, last, footer, ASSET_V,
        localtime_script(ctx.root) if "data-ipe-time" in body else "", GA_SNIPPET)


def breadcrumb_html(items):
    return '<nav class="crumbs" aria-label="breadcrumb">%s</nav>' % " › ".join(
        '<a href="%s">%s</a>' % (esc(h), esc(l)) if h else "<span>%s</span>" % esc(l) for h, l in items)


def breadcrumb_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": l, **({"item": url(h)} if h else {})} for i, (h, l) in enumerate(items)]}


def website_ld(lang):
    return {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": "ipe() Games", "inLanguage": lang,
            "publisher": {"@id": ORG_ID}}


def game_ld(g, lang):
    # confirmed facts only: no offers, no ratings, no release date (none of the games is out)
    return {"@type": "VideoGame", "@id": SITE + "/#" + g["id"], "name": g["name"]["en"], "url": g["url"],
            "description": g["tagline"][lang], "inLanguage": lang, "genre": g["genre"],
            "applicationCategory": "GameApplication", "gamePlatform": g["platforms"],
            "image": SITE + "/assets/games/" + g["icon"], "creator": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}}


def num(n):
    return "%02d" % n


# ---------------------------------------------------------------- page builders
def game_card(ctx, lang, g):
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    pros = "".join("<li><strong>%s</strong> %s</li>" % (esc(x["h"][lang]), esc(x["p"][lang])) for x in g["pros"])
    cons = "".join("<li><strong>%s</strong> %s</li>" % (esc(x["h"][lang]), esc(x["p"][lang])) for x in g["cons"])
    j = g.get("journal")
    links = ['<a class="btn" href="%s" rel="noopener" data-game="%s" data-placement="card">%s: %s <span aria-hidden="true">→</span></a>' % (
        esc(g["url"]), esc(g["id"]), esc(t("g_visit")), esc(g["name"][lang]))]
    if j:
        h, a, m = loc_link(ctx, j["url"], lang)
        links.append('<a class="textlink" href="%s" rel="noopener"%s>%s</a>' % (esc(h), a, esc("%s: %s%s" % (j["label"][lang], t("g_blog"), m))))
    if g.get("terms"):
        h, a, m = loc_link(ctx, g["terms"], lang)
        links.append('<a class="textlink" href="%s" rel="noopener"%s>%s</a>' % (esc(h), a, esc(t("g_terms") + m)))
    sub = g["sub"][lang] if g["sub"][lang] != g["name"][lang] else ""
    return ('<article class="game" id="%s" style="--a:%s;--a2:%s"><header class="game-head"><img class="game-icon" src="/assets/games/%s" width="64" height="64" alt="">'
            '<div><h3>%s</h3>%s<p class="meta"><span class="badge">%s</span> <span class="plat">%s</span></p></div></header>'
            '<p class="tagline">%s</p><p class="price mono">%s</p>'
            '<div class="cols"><div><h4>%s</h4><ol>%s</ol></div><div><h4>%s</h4><ol>%s</ol></div></div>'
            '<p class="links">%s</p></article>') % (
        g["id"], g["accent"][0], g["accent"][1], esc(g["icon"]), esc(g["name"][lang]),
        ('<p class="sub">%s</p>' % esc(sub)) if sub else "", esc(g["status"][lang]), esc(g["platform"][lang]),
        esc(g["tagline"][lang]), esc(g["pricing"][lang]), esc(t("g_likes")), pros, esc(t("g_nots")), cons, " ".join(links))


def compare_html(ctx, lang):
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    head = "".join('<th scope="col" style="--a:%s;--a2:%s">%s</th>' % (g["accent"][0], g["accent"][1], esc(g["name"][lang])) for g in ctx.games)
    rows = ""
    for r in COMPARE_ROWS:
        rows += '<tr><th scope="row">%s</th>%s</tr>' % (esc(t("row_" + r)), "".join("<td>%s</td>" % esc(g["compare"][r][lang]) for g in ctx.games))
    table = ('<div class="cmp-wide"><table class="cmp"><caption class="sr-only">%s</caption><thead><tr><th scope="col"><span class="sr-only">%s</span></th>%s</tr></thead>'
             '<tbody>%s</tbody></table></div>') % (esc(t("compare_h")), esc(t("compare_game")), head, rows)
    cards = ""
    for g in ctx.games:
        dl = "".join("<div><dt>%s</dt><dd>%s</dd></div>" % (esc(t("row_" + r)), esc(g["compare"][r][lang])) for r in COMPARE_ROWS)
        cards += '<article class="cmp-card" style="--a:%s;--a2:%s"><h3>%s</h3><dl>%s</dl></article>' % (g["accent"][0], g["accent"][1], esc(g["name"][lang]), dl)
    return table + '<div class="cmp-cards">%s</div>' % cards


def build_home(ctx, lang):
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    by_id = {g["id"]: g for g in ctx.games}
    strip = "".join('<li><a href="#%s"><img src="/assets/games/%s" width="64" height="64" alt="%s"></a></li>' % (
        g["id"], esc(g["icon"]), esc(g["name"][lang])) for g in ctx.games)
    hero = ('<section class="hero"><div class="wrap"><p class="code mono">%s</p><h1>%s</h1><p class="hero-sub">%s</p>'
            '<ul class="strip" aria-label="%s">%s</ul></div></section>') % (esc(t("hero_code")), esc(t("hero_h1")), esc(t("hero_sub")), esc(t("hero_strip_aria")), strip)
    principles = ""
    for n in range(1, 6):
        kept = "".join('<li><img src="/assets/games/%s" width="24" height="24" alt="">%s</li>' % (esc(by_id[i]["icon"]), esc(by_id[i]["name"][lang])) for i in PRINCIPLE_GAMES[n])
        principles += ('<li class="principle"><span class="pn mono">%s</span><div><h3>%s</h3><p>%s</p><p class="kept"><span class="mono">%s</span></p><ul class="chips">%s</ul></div></li>') % (
            num(n), esc(t("p%d_h" % n)), esc(t("p%d_p" % n)), esc(t("phil_kept")), kept)
    phil = ('<section class="sec" id="philosophy"><div class="wrap"><h2><span class="sn mono">01</span>%s</h2><p class="rest">%s</p>'
            '<ol class="principles">%s</ol></div></section>') % (esc(t("phil_h")), esc(t("phil_rest")), principles)
    games = ('<section class="sec tint" id="games"><div class="wrap"><h2><span class="sn mono">02</span>%s</h2><p class="lead">%s</p><div class="game-list">%s</div></div></section>') % (
        esc(t("games_h")), esc(t("games_lead")), "".join(game_card(ctx, lang, g) for g in ctx.games))
    cmp_ = ('<section class="sec" id="compare"><div class="wrap"><h2><span class="sn mono">03</span>%s</h2><p class="lead">%s</p>%s<p class="note">%s</p></div></section>') % (
        esc(t("compare_h")), esc(t("compare_lead")), compare_html(ctx, lang), esc(t("compare_note")))
    choose_items = "".join('<li><span>%s</span><a class="btn ghost" href="#%s">%s <span aria-hidden="true">→</span></a></li>' % (
        esc(t("choose_%d" % (i + 1))), g["id"], esc(g["name"][lang])) for i, g in enumerate(ctx.games))
    choose = ('<section class="sec tint" id="choose"><div class="wrap"><h2><span class="sn mono">04</span>%s</h2><p class="lead">%s</p><ul class="choose">%s</ul></div></section>') % (
        esc(t("choose_h")), esc(t("choose_lead")), choose_items)
    made_items = ""
    for g in [x for x in ctx.games if x.get("journal")]:
        jh, ja_, jm = loc_link(ctx, g["journal"]["url"], lang)
        fh, fa, fm = loc_link(ctx, g["journal"]["feed"], lang)
        made_items += (
            '<li style="--a:%s;--a2:%s"><div><h3>%s</h3><p class="meta"><span class="badge">%s</span></p></div><p class="links">'
            '<a class="textlink" href="%s" rel="noopener"%s>%s</a> <a class="textlink" href="%s" rel="noopener"%s>%s</a></p></li>') % (
            g["accent"][0], g["accent"][1], esc(g["name"][lang]), esc(t("made_now")), esc(jh), ja_,
            esc(g["journal"]["label"][lang] + ": " + t("made_read") + jm), esc(fh), fa, esc(t("made_feed") + fm))
    made = ('<section class="sec" id="made"><div class="wrap"><h2><span class="sn mono">05</span>%s</h2><p class="lead">%s</p><ul class="made">%s</ul></div></section>') % (
        esc(t("made_h")), esc(t("made_lead")), made_items)
    # recent posts only where the journal is written in this language (en/ko): an English card list inside a page that says
    # lang="ja" would mix languages; the ja reader still reaches the English journal from the nav and footer
    posts = ctx.posts_in(lang)
    journal = journal_section(ctx, lang, num(6), posts) if posts else ""
    studio = ('<section class="sec%s" id="studio"><div class="wrap"><h2><span class="sn mono">%s</span>%s</h2><p class="lead">%s</p>'
              '<p class="links"><a class="textlink" href="https://ipe.rest/" rel="noopener">%s</a> <a class="textlink" href="https://idle.ipe.rest/" rel="noopener">%s</a> '
              '<a class="textlink" href="%s">%s</a></p></div></section>') % (
        "" if posts else " tint", num(7 if posts else 6), esc(t("ipe_h")), esc(t("ipe_p")), esc(t("ipe_studio")), esc(t("ipe_music")), esc(path_page(lang, "contact")), esc(t("ipe_contact")))
    graph = [ORG, website_ld(lang)] + [game_ld(g, lang) for g in ctx.games]
    alt = {l: path_home(l) for l in ctx.langs}
    return path_home(lang), render(ctx, lang, path=path_home(lang), title=t("home_title"), desc=t("home_desc"), body=hero + phil + games + cmp_ + choose + made + journal + studio,
                                   graph=graph, alt=alt, updated=home_updated(ctx, lang), nav="")


def home_updated(ctx, lang):
    return max([SITE_UPDATED] + [p["langs"][lang]["updated"] for p in ctx.posts_in(lang)])


def post_card(lang, p):
    v = p["langs"][lang]  # callers pass only posts from ctx.posts_in(lang)
    return ('<article class="journal-card"><a class="journal-card__link" href="%s">%s<h3>%s</h3><p>%s</p></a></article>') % (
        esc(path_post(lang, p["slug"])), time_tag(p["published"]), esc(v["title"]), esc(v["excerpt"]))


def journal_section(ctx, lang, number, posts):
    """home: the newest HOME_CARDS posts in this language, generated from the same sources as the list (no JS)"""
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    cards = "".join(post_card(lang, p) for p in posts[:HOME_CARDS])
    return ('<section class="sec tint" id="journal"><div class="wrap"><div class="journal__head"><h2><span class="sn mono">%s</span>%s</h2>'
            '<a class="textlink journal__all" href="%s">%s <span aria-hidden="true">→</span></a></div><p class="lead">%s</p>'
            '<div class="journal__grid">%s</div></div></section>') % (
        number, esc(t("journal_h")), esc(path_journal(lang)), esc(t("journal_all")), esc(t("journal_lead")), cards)


def journal_title(ctx, lang, title):
    full = "%s — play.ipe.rest" % title
    return full if len(full) <= TITLE_MAX else title


def build_journal_list(ctx, lang):
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    pth = path_journal(lang)
    crumbs = [(path_home(lang), t("crumb_home")), (None, t("journal_h"))]
    posts = ctx.posts_in(lang)
    if posts:
        items = "".join('<li class="jitem">%s<h2><a href="%s">%s</a></h2><p>%s</p></li>' % (
            time_tag(p["published"]), esc(path_post(lang, p["slug"])), esc(p["langs"][lang]["title"]), esc(p["langs"][lang]["excerpt"])) for p in posts)
        main = '<ol class="jlist">%s</ol>' % items
    else:
        main = '<p class="jempty">%s</p>' % esc(t("journal_empty"))
    body = ('<div class="wrap">%s<section class="prose jhead"><h1>%s</h1><p class="lead">%s</p></section>%s'
            '<p class="jfoot"><a class="textlink" href="%s">%s</a></p></div>') % (
        breadcrumb_html(crumbs), esc(t("journal_h")), esc(t("journal_lead")), main, esc(path_feed(lang)), esc(t("journal_rss")))
    page_ld = {"@type": "CollectionPage", "@id": url(pth) + "#page", "url": url(pth), "name": t("journal_h"), "description": t("journal_desc"),
               "inLanguage": lang, "isPartOf": {"@id": SITE + "/#website"}}
    if posts:
        page_ld["mainEntity"] = {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": url(path_post(lang, p["slug"]))} for i, p in enumerate(posts)]}
    updated = max([p["langs"][lang]["updated"] for p in posts] or [SITE_UPDATED])
    return pth, render(ctx, lang, path=pth, title="%s — play.ipe.rest" % t("journal_h"), desc=t("journal_desc"), body=body,
                       graph=[ORG, website_ld(lang), page_ld, breadcrumb_ld(crumbs)], alt={l: path_journal(l) for l in ctx.journal_langs},
                       updated=updated, noindex=not posts, nav="journal")


def build_post(ctx, lang, p):
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    v = p["langs"][lang]
    pth = path_post(lang, p["slug"])
    crumbs = [(path_home(lang), t("crumb_home")), (path_journal(lang), t("journal_h")), (None, v["title"])]
    body = ('<div class="wrap">%s<article class="prose post"><h1>%s</h1><p class="post-meta">%s</p>%s'
            '<p class="jfoot"><a class="textlink" href="%s"><span aria-hidden="true">←</span>&nbsp;%s</a></p></article></div>') % (
        breadcrumb_html(crumbs), esc(v["title"]), time_tag(p["published"]), markdown(ctx.sub(v["body"])), esc(path_journal(lang)), esc(t("journal_back")))
    ld = {"@type": "BlogPosting", "@id": url(pth) + "#article", "url": url(pth), "mainEntityOfPage": {"@type": "WebPage", "@id": url(pth)},
          "headline": v["title"], "description": v["description"], "inLanguage": lang, "datePublished": p["published"],
          "dateModified": p["published"] if v["updated"] == p["published"][:10] else v["updated"], "image": SITE + OG_IMAGE,
          "isAccessibleForFree": True, "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID}, "isPartOf": {"@id": SITE + "/#website"}}
    return pth, render(ctx, lang, path=pth, title=journal_title(ctx, lang, v["title"]), desc=v["description"], body=body,
                       graph=[ORG, website_ld(lang), ld, breadcrumb_ld(crumbs)], alt={l: path_post(l, p["slug"]) for l in post_langs(ctx, p)},
                       updated=v["updated"], og_type="article", nav="journal")


def rfc822(published):
    d = parse_published(published)
    return "%s, %02d %s %d %02d:%02d:00 +0900" % ("Mon Tue Wed Thu Fri Sat Sun".split()[d.weekday()], d.day,
                                                  "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()[d.month - 1], d.year, d.hour, d.minute)


def build_feed(ctx, lang):
    """RSS 2.0 of the journal in one language; lastBuildDate = newest post (deterministic, not the build time)"""
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    rows = ['<?xml version="1.0" encoding="UTF-8"?>', "<!-- %s -->" % GEN_MARK,
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
            "<title>%s</title>" % esc(t("journal_feed_title")), "<link>%s</link>" % esc(url(path_journal(lang))),
            '<atom:link href="%s" rel="self" type="application/rss+xml"/>' % esc(url(path_feed(lang))),
            "<description>%s</description>" % esc(t("journal_desc")), "<language>%s</language>" % lang]
    posts = ctx.posts_in(lang)
    if posts:
        rows.append("<lastBuildDate>%s</lastBuildDate>" % rfc822(posts[0]["published"]))
    for p in posts:
        link = esc(url(path_post(lang, p["slug"])))
        rows.append("<item><title>%s</title><link>%s</link><guid isPermaLink=\"true\">%s</guid><pubDate>%s</pubDate><description>%s</description></item>" % (
            esc(p["langs"][lang]["title"]), link, link, rfc822(p["published"]), esc(p["langs"][lang]["excerpt"])))
    rows.append("</channel></rss>")
    return "\n".join(rows) + "\n"


def build_page(ctx, lang, slug):
    meta, md = ctx.pages[(lang, slug)]
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    crumbs = [(path_home(lang), t("crumb_home")), (None, meta["title"])]
    body = '<div class="wrap">%s<article class="prose"><h1>%s</h1>%s</article></div>' % (
        breadcrumb_html(crumbs), esc(meta["title"]), markdown(ctx.sub(md)))
    page_ld = {"@type": {"about": "AboutPage", "contact": "ContactPage"}.get(slug, "WebPage"), "@id": url(path_page(lang, slug)) + "#page",
               "url": url(path_page(lang, slug)), "name": meta["title"], "description": meta["description"], "inLanguage": lang,
               "dateModified": meta["updated"], "isPartOf": {"@id": SITE + "/#website"}}
    graph = [ORG, website_ld(lang), page_ld, breadcrumb_ld(crumbs)]
    alt = {l: path_page(l, slug) for l in ctx.langs if (l, slug) in ctx.pages}
    return path_page(lang, slug), render(ctx, lang, path=path_page(lang, slug), title="%s — play.ipe.rest" % meta["title"],
                                         desc=meta["description"], body=body, graph=graph, alt=alt, updated=meta["updated"],
                                         nav=slug if slug in ("about", "contact") else "")


def build_404(ctx):
    lang = "en"
    t = lambda k: ctx.t(lang, k)  # noqa: E731
    body = '<div class="wrap prose"><h1>404</h1><p class="lead">%s</p><p><a class="btn" href="/">%s</a></p></div>' % (esc(t("nf_p")), esc(t("nav_home")))
    return render(ctx, lang, path="/404.html", title="404 — play.ipe.rest", desc=t("nf_h"), body=body, graph=[ORG, website_ld(lang)],
                  alt={"en": "/"}, updated=SITE_UPDATED, noindex=True, hreflang=False).replace(
        '<link rel="canonical" href="%s">' % (SITE + "/404.html"), "")


# ---------------------------------------------------------------- site files
def sitemap_entries(ctx):
    """[(path, lastmod, {lang: path})]"""
    ents = []
    for l in ctx.langs:
        ents.append((path_home(l), home_updated(ctx, l), {x: path_home(x) for x in ctx.langs}))
    for slug in PAGE_SLUGS:
        for l in ctx.langs:
            if (l, slug) in ctx.pages:
                ents.append((path_page(l, slug), ctx.pages[(l, slug)][0]["updated"], {x: path_page(x, slug) for x in ctx.langs if (x, slug) in ctx.pages}))
    # the journal exists in JOURNAL_LANGS only; a journal list with no post is noindex and stays out of the sitemap
    jl = [l for l in ctx.journal_langs if ctx.posts_in(l)]
    for l in jl:
        ents.append((path_journal(l), max(p["langs"][l]["updated"] for p in ctx.posts_in(l)), {x: path_journal(x) for x in jl}))
    for p in ctx.posts:
        pl = post_langs(ctx, p)
        for l in pl:
            ents.append((path_post(l, p["slug"]), p["langs"][l]["updated"], {x: path_post(x, p["slug"]) for x in pl}))
    return ents


def build_sitemap(ctx):
    rows = ['<?xml version="1.0" encoding="UTF-8"?>', "<!-- %s -->" % GEN_MARK,
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for pth, lm, alts in sitemap_entries(ctx):
        rows.append("<url><loc>%s</loc><lastmod>%s</lastmod>" % (esc(url(pth)), lm))
        if len(alts) > 1:
            for l, ap in alts.items():
                rows.append('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l, esc(url(ap))))
            rows.append('<xhtml:link rel="alternate" hreflang="x-default" href="%s"/>' % esc(url(alts.get("en", next(iter(alts.values()))))))
        rows.append("</url>")
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def build_robots():
    rows = ["# %s" % GEN_MARK, "User-agent: *", "Allow: /", ""]
    for b in BOTS:
        rows += ["User-agent: %s" % b, "Allow: /", ""]
    rows += ["Sitemap: %s/sitemap.xml" % SITE, ""]
    return "\n".join(rows)


def build_llms(ctx):
    en = ctx.i18n["en"]
    rows = ["# ipe() Games", "", "> %s" % en["home_desc"], "",
            "play.ipe.rest is the portal for the games made by ipe() (https://ipe.rest/). It collects five games in one place and links to each game's own "
            "official site. None of the five games has been released: no store page or release date exists for any of them. This portal has no accounts "
            "or ads, collects only basic visit statistics through Google Analytics, and has no terms of its own (each game's site has its own terms). It has a journal with notes on turn-based games, "
            "killing-time games and how ipe() makes games.", "",
            "## The games", ""]
    for g in ctx.games:
        rows.append("- [%s](%s): %s Status: %s. Platform: %s. Pricing: %s." % (
            g["name"]["en"], g["url"], g["tagline"]["en"], g["status"]["en"], g["platform"]["en"], g["pricing"]["en"]))
    rows += ["", "## How ipe makes games", ""]
    for n in range(1, 6):
        rows.append("- %s: %s" % (en["p%d_h" % n], en["p%d_p" % n]))
    if ctx.posts:
        rows += ["", "## Journal", "", "RSS: %s%s" % (SITE, path_feed("en")), ""]
        rows += ["- [%s](%s%s): %s" % (p["langs"]["en"]["title"], SITE, path_post("en", p["slug"]), p["langs"]["en"]["description"]) for p in ctx.posts]
    rows += ["", "## Pages", "", "- [Home](%s/): %s" % (SITE, en["hero_h1"]),
             "- [About](%s%s): what this portal is and who makes the games" % (SITE, path_page("en", "about")),
             "- [Contact](%s%s): email and questions" % (SITE, path_page("en", "contact")),
             "- [Journal](%s%s): %s" % (SITE, path_journal("en"), en["journal_lead"]),
             "- [Privacy Policy](%s%s)" % (SITE, path_page("en", "privacy")), "",
             "## Languages", "", "The site is available in %d languages: %s. English is at the root; every other language lives under /<code>/ "
             "(for example /ko/, /ja/). English and Korean are written by ipe(); %s are AI translations of the English original, "
             "marked as such on every page. The journal is written in %s only." % (
                 len(ctx.langs), ", ".join("%s (%s)" % (EN_NAMES[l], l) for l in ctx.langs),
                 ", ".join(EN_NAMES[l] for l in ctx.langs if l in MT_LANGS) or "no languages",
                 " and ".join(EN_NAMES[l] for l in ctx.journal_langs)), "",
             "## Contact and operator", "", "%s — %s" % (OPERATOR, EMAIL), ""]
    return "\n".join(rows)


# ---------------------------------------------------------------- orchestration
def make_ctx(root, now=None):
    root = Path(root)
    i18n, errs = load_i18n(root)
    pages, e2 = load_pages(root)
    games, e3 = load_games(root)
    game_langs, e5 = load_game_text(root, games) if not e3 else ([], [])
    posts, e4 = load_journal(root)
    today = resolve_today(now)
    total = len(posts)
    posts = [p for p in posts if released(p, today)]  # the date gate: a post dated after `today` (KST) is on no page, feed or sitemap
    errs += e2 + e3 + e5 + e4

    def has(l):
        return {"i18n": l in i18n, "pages": all((l, s) in pages for s in PAGE_SLUGS), "games": l in MAIN_LANGS or l in game_langs}
    langs = [l for l in LANGS if all(has(l).values())]
    if "en" not in langs or "ko" not in langs:
        errs.append("en and ko must both be complete (i18n + %s)" % " + ".join(PAGE_SLUGS))
    for l in MT_LANGS:  # a language is built whole or not at all: half a translation is an error, not a silent skip
        h = has(l)
        started = l in i18n or any((l, s) in pages for s in PAGE_SLUGS) or (Path(root) / ("content/i18n/games/%s.json" % l)).is_file()
        if started and not all(h.values()):
            errs.append("%s: translation is incomplete — missing %s" % (l, ", ".join(k for k, v in h.items() if not v)))
    ctx = Ctx(root, i18n, pages, games, langs, posts)
    ctx.today, ctx.scheduled = today, total - len(posts)
    return ctx, errs


def build_all(ctx):
    """-> {relative file path: text}"""
    files = {}

    def put(path, text):
        files[path.lstrip("/") + "index.html" if path.endswith("/") else path.lstrip("/")] = text

    for l in ctx.langs:
        put(*build_home(ctx, l))
        for slug in PAGE_SLUGS:
            put(*build_page(ctx, l, slug))
    for l in ctx.journal_langs:  # no /ja/journal/: the journal is en + ko only
        put(*build_journal_list(ctx, l))
        files[path_feed(l).lstrip("/")] = build_feed(ctx, l)
        for p in ctx.posts_in(l):
            put(*build_post(ctx, l, p))
    files["404.html"] = build_404(ctx)
    files["sitemap.xml"] = build_sitemap(ctx)
    files["robots.txt"] = build_robots()
    files["llms.txt"] = build_llms(ctx)
    return files


def clean(root):
    root = Path(root)
    for name in list(PAGE_SLUGS) + [JOURNAL_DIR] + [l for l in LANGS if l != "en"]:
        d = root / name
        if d.is_dir():
            shutil.rmtree(d)
    for name in ("index.html", "404.html", "sitemap.xml", "robots.txt", "llms.txt"):
        f = root / name
        if f.is_file():
            f.unlink()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--check", action="store_true", help="validate sources only")
    ap.add_argument("--now", metavar="YYYY-MM-DD", help="build as of this KST date: posts dated later stay out of every page, feed and sitemap "
                    "(default: $PLAY_NOW, else today in KST)")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    try:
        ctx, errs = make_ctx(root, a.now)
    except ValueError as ex:
        print("build_site: %s" % ex, file=sys.stderr)
        return 2
    if errs:
        print("build_site: %d problem(s)\n  %s" % (len(errs), "\n  ".join(errs)), file=sys.stderr)
        return 1
    files = build_all(ctx)
    if a.check:
        print("build_site: sources OK — %d language(s), %d game(s), %d file(s) would be written, %d journal post(s) live, %d scheduled (as of %s)" % (len(ctx.langs), len(ctx.games), len(files), len(ctx.posts), ctx.scheduled, ctx.today))
        return 0
    clean(root)
    for rel, text in files.items():
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    print("build_site: wrote %d file(s) — %d language(s), %d game(s), %d journal post(s) live, %d scheduled (as of %s)" % (len(files), len(ctx.langs), len(ctx.games), len(ctx.posts), ctx.scheduled, ctx.today))
    return 0


if __name__ == "__main__":
    sys.exit(main())
