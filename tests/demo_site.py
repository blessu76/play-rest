"""Build a repo-shaped demo site WITH the test-only journal posts, for the render check (never touches the repo):
    python3 tests/demo_site.py OUTDIR && PLAY_ROOT=OUTDIR NODE_PATH=<playwright> node tests/ui_check.js SHOTS
Pass --empty to build it with no posts at all (the empty-state view)."""
import shutil
import sys
from pathlib import Path

from helpers import build, make_site, make_site_with_posts

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    out = Path(args[0]).resolve()
    src = make_site() if "--empty" in sys.argv else make_site_with_posts()
    build(src)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(src, out)
    shutil.rmtree(src, True)
    print("demo site in", out)
