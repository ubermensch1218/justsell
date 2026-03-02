---
name: justsell-setup
description: Interactive setup wizard (OMC-style) for JustSell config under ~/.claude/.js
---

# JustSell Setup

목표: OMC(`omc-setup`)처럼 “설치 후 한 번만” 설정하면 끝나는 형태로, 로컬 설정을 CLI 위저드로 저장합니다.

저장 위치(로컬-first):
- 설정/토큰: `~/.claude/.js/config.json`
- Claude Code가 `CLAUDE_CONFIG_DIR`를 쓰면, `~/.claude` 대신 그 경로를 사용합니다.

## Step 0. 설정 위저드 실행
```bash
python3 scripts/justsell_setup.py --wizard
```

`config.json`이 이미 있으면 위저드가 아래 중 하나를 먼저 묻습니다:
1) 기존 값 유지 + 일부만 업데이트
2) 전체 설정 다시 진행
3) 취소

위저드에서 물어보는 값(빈 값 허용):
- Cardnews preset: `BOC-like` / `Claude-like` / Custom
- `public_base_url` (Instagram carousel publish에 필요할 수 있음)
- Threads: `threads_app_id`, `threads_app_secret`
- Meta(Instagram Graph API): `meta_app_id`, `meta_app_secret`, `graph_api_version` (기본값 `v20.0`)
- Cardnews defaults
  - template: `channels/instagram/templates/*.yaml`
  - key colors: `accent_primary`, `cover_fill`, `bg_kind` 등
  - fonts by name: `title_name/body_name/footer_name` (예: `Gmarket Bold`, `Pretendard Regular`)

## Step 1. 콘솔 실행 + OAuth 연결
```bash
python3 scripts/justsell_console.py
```
그리고 `http://127.0.0.1:5678/connect`에서 OAuth 연결을 진행합니다:
- Threads: "Connect Threads (OAuth)"
- Instagram: "Connect Instagram (OAuth)"
- "Discover accounts" 후 하나의 `ig_user_id`를 "Select"

## Optional. 비대화형(스크립트 플래그) 저장
대화형 위저드를 쓰기 어려우면 플래그로 저장합니다(빈 값은 기존값 유지):
```bash
python3 scripts/justsell_setup.py --public-base-url "<public_base_url>"
```
