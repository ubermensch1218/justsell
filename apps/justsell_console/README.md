# JustSellConsole

로컬에서 카드뉴스/채널 초안 생성과 미리보기를 한 곳에서 보는 콘솔입니다.

## Run
```bash
python3 /Users/jskang/Projects/JustSell/scripts/justsell_console.py
```

기본 주소:
- `http://localhost:5678`

포트 변경:
- `JUSTSELL_CONSOLE_PORT=6789`

## Features
- Spec 목록/렌더 결과 목록
- Spec 미리보기(이미지 캐러셀)
- 버튼으로 `generate_drafts.py` / `render_cardnews.py` 실행
- Threads/Instagram 연결(OAuth) 및 publish (선택)
- 간단한 cron-like jobs (설정 파일 기반, 서버 실행 중 동작)
- 이벤트/채팅/잡 로그 로컬 저장 (JSONL)

## Config
- `apps/justsell_console/config/jobs.json`

## Connect (Threads/Instagram)
- `http://localhost:5678/connect`

### Threads ENV
- `JUSTSELL_THREADS_APP_ID`
- `JUSTSELL_THREADS_APP_SECRET`
- `JUSTSELL_THREADS_REDIRECT_URI` (default `http://127.0.0.1:5678/oauth/threads/callback`)
- `JUSTSELL_THREADS_SCOPES` (optional)

### Instagram(Graph) ENV
- `JUSTSELL_META_APP_ID`
- `JUSTSELL_META_APP_SECRET`
- `JUSTSELL_IG_REDIRECT_URI` (default `http://127.0.0.1:5678/oauth/ig/callback`)
- `JUSTSELL_GRAPH_API_VERSION` (optional)

### Instagram carousel publish (public URL required)
Meta가 이미지를 가져갈 수 있게, exports PNG가 **공개 URL**로 접근 가능해야 합니다.
이 콘솔은 `/asset/<repo-rel-path>.png`로 로컬 파일을 서빙하므로,
공개 터널을 붙이고 아래를 지정하면 publish가 가능합니다.

- `JUSTSELL_PUBLIC_BASE_URL` (예: `https://xxxx.ngrok-free.app`)

## Local logs
모든 로그는 로컬에 저장됩니다.
- 일반 로그: `~/.claude/.js/console/console.log`
- 이벤트 로그(JSONL): `~/.claude/.js/console/events/events-YYYY-MM-DD.jsonl`
- 채팅 로그(JSONL): `~/.claude/.js/console/events/chat-YYYY-MM-DD.jsonl`
- 잡 로그(JSONL): `~/.claude/.js/console/events/jobs-YYYY-MM-DD.jsonl`

## Project policy
프로젝트별 AI 상담/대화 권한은 아래 파일로 관리합니다.
- `projects/<project>/상담권한.md`

콘솔에서 표시:
- `http://localhost:5678/` (spec 선택 시 Policy 표시)
- API: `http://localhost:5678/api/policy?project=projects/<project>`

## Installed config (OAuth + settings)
OAuth로 받은 토큰/식별자는 로컬에 저장되고(로그에는 마스킹), 아래 파일로 “한 곳에” 묶여 저장됩니다.
- `~/.claude/.js/config.json`

이 파일은 다른 로컬 도구(예: ClaudeCode/자동화 스크립트)가 읽어서 재사용할 수 있는 형태로 유지합니다.

또한 `config.json`의 `settings`에 앱 설정을 넣어두면 ENV 없이도 콘솔이 동작합니다(ENV가 항상 우선).
- `settings.meta_app_id`, `settings.meta_app_secret`, `settings.ig_redirect_uri`
- `settings.threads_app_id`, `settings.threads_app_secret`, `settings.threads_redirect_uri`
- `settings.public_base_url` (IG carousel publish용 터널 URL)
