---
name: console-start
description: Start JustSellConsole (localhost 5678) for connect/preview/render/publish
---

# console-start

JustSellConsole를 로컬에서 실행합니다. 연결(OAuth), 미리보기, 렌더, 게시(dry-run 기본)를 한 곳에서 처리합니다.

## Input
- (optional) `projects/<project>/` 경로

## Output
- 로컬 콘솔: `http://127.0.0.1:5678/`
- 로컬 저장소: `~/.claude/.js/justsell/console/` (로그/이벤트/잡)
- 설정/토큰: `~/.claude/.js/justsell/config.json`

## Commands
```bash
python3 scripts/justsell_console.py
```
