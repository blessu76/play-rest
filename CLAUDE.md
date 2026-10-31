# play-rest

play.ipe.rest — ipe() 게임 4종(일통기·잉크아일·선멜드·클레임볼)을 한곳에 모은 정적 포털. GitHub Pages(`CNAME`), 영어(루트) + 한국어(`/ko/`).

- 생성 파일(`index.html`, `ko/`, `about/`, `privacy/`, `contact/`, `404.html`, `sitemap.xml`, `robots.txt`, `llms.txt`)은 손으로 고치지 않는다. 원본은 `content/`(`i18n/*.json`, `games.json`, `pages/<lang>/*.md`), 생성기는 `scripts/build_site.py`.
- 사이트 문구의 정본은 `_ipe/site/play/GAMEHUB_DOCS.md`. [미검증]·[Davy]·[미정] 항목, 가격·출시일·평점·라이벌 이름·이모지·장르 대표작 이름은 싣지 않는다.
- 게임 링크는 각 게임 공식 사이트만(스토어 링크 없음). 약관 페이지는 이 사이트에 없고 게임별 약관으로 링크한다. 저널·GA4 없음.
- `assets/play.css`·`play.js`를 바꾸면 `build_site.py`의 `ASSET_V`를 올린다.
- 커밋 전: `python3 scripts/build_site.py && bash scripts/check.sh` → `GREEN`. 화면 검증: `NODE_PATH=<playwright 폴더> node tests/ui_check.js <outDir>` (375/320/768/1280).
- OG·아이콘 PNG: `node scripts/render_png.js` (폰트는 `assets/fonts` 로컬).
