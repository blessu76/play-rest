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

Times are stored in KST and shown in the reader's time zone by `ipe-localtime` from the shared web kit `ipe_web_kit` (inlined by the build, hash-tested).

## ipe_web_kit (private) — local setup

The shared web kit is a private repo, so its source is **not** committed here (this repo is public). Only `vendor/ipe_web_kit.lock` (tag, commit, manifest hash) is. Before building:

```sh
python3 scripts/kit_lock.py sync --kit ~/Developer/ipe_web_kit   # copy the locked tag from a local kit clone into vendor/ipe_web_kit/ (gitignored)
python3 scripts/kit_lock.py check                                  # installed copy == lock
```

CI (`.github/actions/ipe-web-kit`) checks out the kit at the locked commit with a read-only deploy key (secret `IPE_WEB_KIT_DEPLOY_KEY`) and runs the same `sync`.
To move to another kit tag: `python3 scripts/kit_lock.py sync --kit <clone> --update --tag vX.Y.Z`, run `bash scripts/check.sh`, commit the lock.
