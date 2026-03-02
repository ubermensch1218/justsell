[English](README.md) | 한국어 | [日本語](README.ja.md)

# justsell

Claude Code용 로컬 우선 마케팅 자동화 플러그인입니다.

Threads, Instagram 카드뉴스, Remotion 영상 워크플로우를 로컬 콘솔에서 생성/렌더/검토하고, 명시적 확인 후에만 게시합니다.

[빠른 시작](#빠른-시작) | [명령어](#명령어-레퍼런스) | [설정 문서](docs/CONFIG.md) | [워크플로우](docs/WORKFLOW.md)

## 빠른 시작

1) 설치
```bash
/plugin marketplace add https://github.com/ubermensch1218/justsell
/plugin install justsell
```

2) 초기 설정
```bash
/justsell:js init
```

3) 콘솔 실행
```bash
/justsell:js console
```

선택: 단계별 온보딩
```bash
/justsell:onboard
```

## 핵심 워크플로우

| 워크플로우 | 진입점 | 결과 |
|------------|--------|------|
| 설정 | `justsell-setup` / `/justsell:js init` | 로컬 설정 저장 + OAuth/Setup 시작 |
| 콘솔 | `console-start` / `/justsell:js console` | `http://127.0.0.1:5678/` 대시보드 실행 |
| 카드뉴스 | `instagram-cardnews` / `/justsell:js cardnews` | 카드뉴스 스펙 생성 + PNG 렌더 |
| Remotion | `/justsell:js remotion` | 영상 스펙 생성 + MP4 렌더 |
| 온보딩 | `/justsell:onboard` | 한 단계씩 초기 가이드 |

## 명령어 레퍼런스

| 명령어 | 설명 |
|--------|------|
| `/justsell:js init` | 로컬 설정 초기화 및 Setup 모드 실행 |
| `/justsell:js console` | JustSellConsole 실행 |
| `/justsell:js cardnews` | Instagram 카드뉴스 생성/렌더 |
| `/justsell:js remotion` | Instagram Remotion 영상 생성/렌더 |
| `/justsell:onboard` | 단계형 온보딩 |

## 기본 저장 경로

- 설정/토큰: `~/.claude/.js/config.json`
- 콘솔 로그/이벤트: `~/.claude/.js/console/`
- 프로젝트: `~/.claude/.js/projects/`

## 주요 환경변수

- `CLAUDE_CONFIG_DIR`
- `CLAUDE_PLUGIN_ROOT`
- `JUSTSELL_HOME`
- `JUSTSELL_CONFIG_PATH`
- `JUSTSELL_PROJECTS_DIR`
- `JUSTSELL_CONSOLE_HOST`
- `JUSTSELL_CONSOLE_PORT`
- `JUSTSELL_PUBLIC_BASE_URL`
- `JUSTSELL_FONT_PATH`
- `JUSTSELL_THREADS_APP_ID`, `JUSTSELL_THREADS_APP_SECRET`, `JUSTSELL_THREADS_REDIRECT_URI`
- `JUSTSELL_META_APP_ID`, `JUSTSELL_META_APP_SECRET`, `JUSTSELL_IG_REDIRECT_URI`, `JUSTSELL_GRAPH_API_VERSION`

자세한 설명은 [README.md](README.md)의 Environment Variables 표를 참고하세요.
