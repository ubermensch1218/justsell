# justsell

OMC(oh-my-claudecode) 스타일의 **마케팅 자동화 플러그인**입니다.

로컬-first로 운영합니다:
- 로그/잡/채팅: `~/.claude/.omc/justsell/console/`
- 설정/토큰: `~/.claude/.omc/justsell/config.json`

## 구조 (요약)
- `projects/`: 프로젝트별 영업/브랜드/채널별 초안과 산출물
  - `projects/<project>/영업Info.md`: 영업/세일즈 메시지의 기준 문서
  - `projects/<project>/상담권한.md`: AI 상담/대화 권한(자동/초안/금지) 정책
- `channels/`: 채널 공통 가이드 + 템플릿(트위터/인스타/쓰레드/링크드인)
- `prompts/`: LLM에 넣는 프롬프트 조각(채널별/작업별)
- `templates/`: 브리프, 카피, 카드뉴스 스펙 템플릿
- `scripts/`: 로컬 자동화(예: 카드뉴스 렌더링)
- `apps/justsell_console/`: 로컬 콘솔(미리보기/렌더/생성/연결/로그)
- `agents/`: 마케팅 전용 에이전트 프롬프트(디렉터/카드뉴스/브랜딩/소셜운영)

## Quick Start

Step 1) Install (OMC 방식)
```bash
/plugin marketplace add https://github.com/ubermensch1218/justsell
/plugin install justsell
```

Step 2) Setup (다이얼로그 흐름)
```bash
/js init
```

Step 3) Run console
```bash
/js console
```

Config 구조: `docs/CONFIG.md`

1) 새 프로젝트 만들기
```bash
cp -R projects/_template projects/<project-slug>
```

2) 프로젝트 정보 채우기
- `projects/<project-slug>/영업Info.md`
- `projects/<project-slug>/brand.md`
- `projects/<project-slug>/product.md`

3) Instagram 카드뉴스 이미지 생성(로컬)
```bash
python3 scripts/render_cardnews.py \
  --spec projects/<project-slug>/channels/instagram/cardnews/01.yaml \
  --out  projects/<project-slug>/channels/instagram/exports
```

폰트가 한글을 못 그리면 `assets/fonts/`에 `.ttf`를 넣고 스펙에서 `font.path`로 지정하거나,
환경변수 `JUSTSELL_FONT_PATH`로 지정하세요.

## 로컬 콘솔 (JustSellConsole)
- 실행:
```bash
python3 scripts/justsell_console.py
```
- 주소: `http://127.0.0.1:5678/`
- 저장 위치(기본): `~/.claude/.omc/justsell/`
  - 설정/토큰: `~/.claude/.omc/justsell/config.json`
  - 로그/이벤트: `~/.claude/.omc/justsell/console/`
