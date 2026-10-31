# play-rest

Source of https://play.ipe.rest, the portal for the ipe() games. Static site, built with a Python stdlib script.

```
python3 scripts/build_site.py   # content/ -> generated pages
bash scripts/check.sh           # sources, tests, up-to-date build, sitemap -> GREEN
```

Text lives in `content/` (`i18n/`, `games.json`, `pages/`). See `CLAUDE.md` for the rules.

## Journal

Posts are Markdown pairs in `content/journal/` (`<slug>.en.md` + `<slug>.ko.md`). Front matter: `title`, `description`, `published` (KST, `2026-11-01T09:30+09:00`), optional `updated` (`2026-11-02`) and `excerpt`. `published_at` is accepted as an alias of `published`; other keys (slug, lang, category, keywords ...) are ignored. `description` is at most 160 characters, and a `published` time still in the future makes the sitemap check fail, so insert a post on or after its publish time.

```
cp <drafts>/<slug>.en.md <drafts>/<slug>.ko.md content/journal/
python3 scripts/build_site.py   # list, posts, RSS, home cards (newest 3), sitemap, llms.txt
bash scripts/check.sh           # -> GREEN
```

Times are stored in KST and shown in the reader's time zone by `content/shared/ipe-localtime.js` (company-wide module, copied byte for byte from ipe-rest, inlined by the build, hash-tested).
