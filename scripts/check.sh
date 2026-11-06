#!/bin/bash
# Green gate for play-rest — run before every commit. Exit 0 = green.
#   scripts/check.sh              # sources + tests + build (into a temp copy) + sitemap check
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== 0/4 kit"; python3 scripts/kit_lock.py check
echo "== 1/4 sources"; python3 scripts/build_site.py --check
echo "== 2/4 unit tests"; python3 -m unittest discover -s tests -q
echo "== 3/4 build is up to date"
# The committed HTML is built as of one KST date (the daily workflow rebuilds at 12:05 KST). Between 00:00 and 12:05 KST the
# committed build is still yesterday's, so it is "up to date" if it matches a build as of today OR yesterday; two days behind = stale
# (the daily job is failing -- worth a red check). A fixed date can be pinned with PLAY_NOW=YYYY-MM-DD (then only that date counts).
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
rsync -a --exclude='.git' ./ "$tmp/"
fresh=""
for back in 0 1; do
  if [ -n "${PLAY_NOW:-}" ] && [ "$back" = 1 ]; then break; fi
  day="$(python3 -c "import sys; sys.path.insert(0,'scripts'); import build_site as b, datetime as d; print(b.resolve_today() - d.timedelta(days=$back))")"
  python3 scripts/build_site.py --root "$tmp" --now "$day" >/dev/null
  if diff -r -q --exclude='.git' --exclude='__pycache__' --exclude='scripts' --exclude='tests' --exclude='docs' --exclude='ops' --exclude='.github' \
     --exclude='content' --exclude='assets' --exclude='*.md' --exclude='*.txt' --exclude='CNAME' --exclude='.nojekyll' . "$tmp" >/dev/null 2>&1 \
     && cmp -s llms.txt "$tmp/llms.txt" && cmp -s robots.txt "$tmp/robots.txt"; then fresh="$day"; break; fi
done
if [ -z "$fresh" ]; then echo "generated files are stale — run: python3 scripts/build_site.py"; exit 1; fi
echo "   matches a build as of $fresh"
echo "== 4/4 sitemap"; python3 scripts/check_sitemap.py
echo "GREEN"
