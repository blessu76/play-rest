# play-rest

play.ipe.rest — ipe() 게임 4종(일통기·잉크아일·선멜드·클레임볼)을 한곳에 모은 정적 포털. GitHub Pages(`CNAME`), 영어(루트) + 한국어(`/ko/`).

- 생성 파일(`index.html`, `ko/`, `about/`, `privacy/`, `contact/`, `404.html`, `sitemap.xml`, `robots.txt`, `llms.txt`, `journal/`)은 손으로 고치지 않는다. 원본은 `content/`(`i18n/*.json`, `games.json`, `pages/<lang>/*.md`), 생성기는 `scripts/build_site.py`.
- 사이트 문구의 정본은 `_ipe/site/play/GAMEHUB_DOCS.md`. [미검증]·[Davy]·[미정] 항목, 가격·출시일·평점·라이벌 이름·이모지·장르 대표작 이름은 싣지 않는다.
- 게임 링크는 각 게임 공식 사이트만(스토어 링크 없음). 약관 페이지는 이 사이트에 없고 게임별 약관으로 링크한다. GA4 없음.
- **저널**(턴제 게임·킬링타임 게임·ipe 게임 철학): 원고는 `content/journal/<slug>.en.md` + `<slug>.ko.md`(둘 다 있어야 함, 글당 한 쌍). 머리말 `title`·`description`(≤160)·`published`(**KST** `2026-11-01T09:30+09:00`)·선택 `updated`(날짜)·`excerpt`(≤200, 없으면 description). 본문은 `##` 이하(h1은 title), ko 는 합니다체. `/journal/`·`/ko/journal/`·`/journal/<slug>/`·`feed.xml`·메인 최신 3개 카드·sitemap·llms.txt 는 `build_site.py` 가 모두 생성한다(손으로 고치지 않는다). 게시 시각은 KST 로 기록하고 화면에는 보는 기기 시간대로 보인다 — `content/shared/ipe-localtime.js` 는 ipe-rest/shared 정본의 **바이트 그대로 사본**(해시 테스트, 인라인 삽입, 직접 수정 금지). 글이 0개여도 목록·피드·메인이 깨지지 않는다(빈 목록은 noindex·sitemap 제외, 메인 카드 섹션 없음). 테스트용 임시 글은 커밋하지 않는다: `tests/demo_site.py`(픽스처 글이 든 임시 사이트).
- `assets/play.css`·`play.js`를 바꾸면 `build_site.py`의 `ASSET_V`를 올린다.
- 커밋 전: `python3 scripts/build_site.py && bash scripts/check.sh` → `GREEN`. 화면 검증: `NODE_PATH=<playwright 폴더> node tests/ui_check.js <outDir>` (375/320/768/1280 × 라이트·다크·누아르 3테마). 글이 있는 모습은 `python3 tests/demo_site.py <dir>` 후 `PLAY_ROOT=<dir> node tests/ui_check.js <outDir>`.
- OG·아이콘 PNG: `node scripts/render_png.js` (폰트는 `assets/fonts` 로컬).
