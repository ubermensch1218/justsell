---
name: justsell-setup
description: Interactive setup wizard (OMC-style) for JustSell config under ~/.claude/.omc/justsell
---

# JustSell Setup

목표: OMC(`omc-setup`)처럼 “설치 후 한 번만” 설정하면 끝나는 형태로 구성합니다.

저장 위치(로컬-first):
- 설정/토큰: `~/.claude/.omc/justsell/config.json`
- Claude Code가 `CLAUDE_CONFIG_DIR`를 쓰면, `~/.claude` 대신 그 경로를 사용합니다.

## Step 0. 이미 설정되어 있는지 확인
`config.json`이 이미 있으면, 아래 중 하나를 먼저 물어봅니다:
1) 기존 값 유지 + 일부만 업데이트
2) 전체 설정 다시 진행
3) 취소

체크(쉘):
```bash
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-${CLAUDE_HOME:-$HOME/.claude}}"
CONFIG="$CLAUDE_DIR/.omc/justsell/config.json"
python3 - <<'PY'
import json, os
from pathlib import Path
claude_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or os.environ.get("CLAUDE_HOME") or Path.home() / ".claude").expanduser()
config = claude_dir / ".omc" / "justsell" / "config.json"
if not config.exists():
  print("NOT_CONFIGURED")
  raise SystemExit(0)
try:
  data = json.loads(config.read_text(encoding="utf-8"))
except Exception:
  data = {}
meta = (data.get("meta") or {}) if isinstance(data, dict) else {}
print("CONFIGURED")
print("setupCompletedAt=", meta.get("setupCompletedAt", ""))
PY
```

## Step 1. 사용자에게 질문(다이얼로그 스타일)
다음 값을 물어봅니다(사용자가 모르면 빈 값 허용):
- `public_base_url` (Instagram carousel publish에 필요할 수 있음)
- Threads
  - `threads_app_id`
  - `threads_app_secret`
- Meta(Instagram Graph API)
  - `meta_app_id`
  - `meta_app_secret`
  - `graph_api_version` (기본값 `v20.0`)
- Cardnews defaults
  - template: `channels/instagram/templates/*.yaml`
  - key colors: `accent_primary`, `cover_fill`, `bg_kind` 등
  - fonts: title/body/footer font name (예: `GDmarket Bold`, `Pretendard Regular`)

## Step 2. config.json에 저장(스크립트로)
아래 커맨드로 저장합니다(빈 값은 기존값 유지):
```bash
python3 scripts/justsell_setup.py \
  --public-base-url "<public_base_url>" \
  --threads-app-id "<threads_app_id>" \
  --threads-app-secret "<threads_app_secret>" \
  --meta-app-id "<meta_app_id>" \
  --meta-app-secret "<meta_app_secret>" \
  --graph-api-version "v20.0" \
  --cardnews-template "channels/instagram/templates/cardnews.boc_like.yaml" \
  --accent-primary "#00E676" \
  --accent-secondary "#111111" \
  --cover-fill "#00E676" \
  --panel-fill "#2B2B2B" \
  --bg-kind "solid" \
  --bg-solid "#2B2B2B" \
  --title-font "GDmarket Bold" \
  --body-font "Pretendard Regular" \
  --footer-font "Pretendard Regular"
```

## Step 3. 콘솔 실행
```bash
python3 scripts/justsell_console.py
```
그리고 `http://127.0.0.1:5678/connect`에서 OAuth 연결을 진행합니다.
