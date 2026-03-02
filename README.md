# JustSell (Marketing Ops)

`oh-my-claudecode`, `oh-my-codex` 스타일을 참고해서 만든 **마케팅 운영 전용** 디렉토리 구조입니다.

## 목표
- 채널별 운영 가이드/템플릿을 표준화
- 프로젝트별(Per-Project) 영업 정보(`영업Info.md`)를 Source of Truth로 유지
- Instagram 카드뉴스(이미지) 생성 같은 반복 작업을 스크립트로 자동화
- 마케팅 팀이 단독으로 운영 가능한 로컬 콘솔/로그/권한 정책 제공

## 구조 (요약)
- `projects/`: 프로젝트별 영업/브랜드/채널별 초안과 산출물
  - `projects/<project>/영업Info.md`: 영업/세일즈 메시지의 기준 문서
  - `projects/<project>/상담권한.md`: AI 상담/대화 권한(자동/초안/금지) 정책
- `channels/`: 채널 공통 가이드 + 템플릿(트위터/인스타/쓰레드/링크드인)
- `prompts/`: LLM에 넣는 프롬프트 조각(채널별/작업별)
- `templates/`: 브리프, 카피, 카드뉴스 스펙 템플릿
- `scripts/`: 로컬 자동화(예: 카드뉴스 렌더링)
- `apps/justsell_console/`: 로컬 콘솔(미리보기/렌더/생성/연결/로그)

## 빠른 시작
0) (선택) Claude Code에 설치

- Claude Code 플러그인(oh-my-claudecode 방식):
  - Claude Code에서 실행:
```bash
/plugin marketplace add <REPO_URL>
/plugin install justsell
```
  - 설치 후: `/justsell-setup`, `/console-start`, `/instagram-cardnews` 같은 스킬이 잡힘

- 로컬 설치(명령/스킬 심기):
```bash
./install.sh
```

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
