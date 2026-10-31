# play-rest

Source of https://play.ipe.rest, the portal for the ipe() games. Static site, built with a Python stdlib script.

```
python3 scripts/build_site.py   # content/ -> generated pages
bash scripts/check.sh           # sources, tests, up-to-date build, sitemap -> GREEN
```

Text lives in `content/` (`i18n/`, `games.json`, `pages/`). See `CLAUDE.md` for the rules.
