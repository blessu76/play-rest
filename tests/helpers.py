"""Shared fixtures: a repo-shaped temp copy of the sources (content + assets) to build into."""
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import build_site as bs  # noqa: E402

NOW = dt.datetime(2026, 11, 3, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
# the builder's date gate reads $PLAY_NOW: pin it so the fixtures (dated 10-30 .. 11-02) are always released, whatever day the tests run
os.environ["PLAY_NOW"] = NOW.date().isoformat()


def make_site():
    root = Path(tempfile.mkdtemp(prefix="play-test-"))
    # real journal posts are left out so the tests see only their own fixtures (empty state included)
    shutil.copytree(REPO / "content", root / "content", ignore=shutil.ignore_patterns("journal"))
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


# ---- journal fixtures (test-only posts; real posts live in content/journal/ and are never faked in the repo)
JOURNAL_FIXTURES = {
    # slug: (published, updated, en title, en excerpt, ko title, ko excerpt)
    "turn-based-in-a-break": ("2026-11-01T09:30+09:00", "2026-11-01", "Turn-based games that fit in a break",
                              "A short turn-based round can end before the coffee gets cold.",
                              "쉬는 시간에 끝나는 턴제 게임", "짧은 턴제 한 판은 커피가 식기 전에 끝날 수 있습니다."),
    "killing-time-honestly": ("2026-11-02T08:05+09:00", "2026-11-02", "Killing time, honestly",
                              "What a killing-time game owes you when it takes only a few minutes of your day.",
                              "시간을 죽이는 게임이 지켜야 할 것", "몇 분의 시간을 쓰게 하는 게임이 플레이어에게 빚지고 있는 것은 무엇일까요."),
    "why-rounds-end": ("2026-10-31T23:40+09:00", "2026-10-31", "Why a round should end clearly",
                       "A clear ending is the kindest rule a short game can have.", "한 판은 왜 분명하게 끝나야 할까",
                       "분명한 끝은 짧은 게임이 가질 수 있는 가장 다정한 규칙입니다."),
    "one-more-old-post": ("2026-10-30T12:00+09:00", "2026-10-30", "An older post that falls off the home page",
                          "Only the newest three posts get a card on the home page.", "홈에서 밀려나는 오래된 글",
                          "홈 화면에는 가장 새로운 글 세 개만 카드로 올라갑니다."),
}


def post_md(lang, slug, **over):
    published, updated, ten, xen, tko, xko = JOURNAL_FIXTURES[slug]
    meta = {"title": ten if lang == "en" else tko, "description": (xen if lang == "en" else xko), "published": published}
    meta.update(over)
    head = "\n".join("%s: %s" % (k, v) for k, v in meta.items() if v is not None)
    body = ("## First point\n\nA paragraph with **bold**, a [link](/about/) and `code`.\n\n> A quiet quote.\n\n- one\n- two\n" if lang == "en"
            else "## 첫 번째 이야기\n\n**굵은 글씨**, [링크](/ko/about/), `코드`가 있는 문단입니다.\n\n> 조용한 인용입니다.\n\n- 하나\n- 둘\n")
    return "---\n%s\n---\n%s" % (head, body)


def add_post(root, slug, langs=("en", "ko"), **over):
    d = Path(root) / "content" / "journal"
    d.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        (d / ("%s.%s.md" % (slug, lang))).write_text(post_md(lang, slug, **over), encoding="utf-8")


def make_site_with_posts(slugs=tuple(JOURNAL_FIXTURES)):
    root = make_site()
    for slug in slugs:
        add_post(root, slug)
    return root
