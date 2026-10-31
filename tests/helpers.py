"""Shared fixtures: a repo-shaped temp copy of the sources (content + assets) to build into."""
import datetime as dt
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import build_site as bs  # noqa: E402

NOW = dt.datetime(2026, 11, 3, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))


def make_site():
    root = Path(tempfile.mkdtemp(prefix="play-test-"))
    shutil.copytree(REPO / "content", root / "content")
    shutil.copytree(REPO / "assets", root / "assets")
    return root


def build(root):
    ctx, errs = bs.make_ctx(root)
    assert not errs, errs
    for rel, text in bs.build_all(ctx).items():
        f = Path(root) / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    return ctx


def jsonld(html_text):
    return [json.loads(m.group(1)) for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S)]
