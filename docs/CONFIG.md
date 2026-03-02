# Config (`~/.claude/.omc/justsell/config.json`)

JustSell은 로컬-first로 설정과 OAuth 토큰을 저장합니다. (Claude Code가 `CLAUDE_CONFIG_DIR`를 쓰면 그 경로를 우선합니다.)

## Top-level shape
```json
{
  "version": 1,
  "settings": {},
  "secrets": {},
  "meta": {},
  "updated_at": "..."
}
```

## `settings` (no tokens)
### `settings.public_base_url`
- Instagram carousel publish에서 이미지 URL로 사용됩니다.
- 로컬 콘솔을 ngrok/cloudflared로 공개했을 때 그 base URL을 넣습니다.

### `settings.cardnews`
```json
{
  "template": "channels/instagram/templates/cardnews.boc_like.yaml",
  "theme": {
    "accent_primary": "#00E676",
    "accent_secondary": "#111111",
    "cover_fill": "#00E676",
    "panel_fill": "#2B2B2B",
    "bg_kind": "solid",
    "bg_solid": "#2B2B2B",
    "bg_from": "",
    "bg_to": ""
  },
  "fonts": {
    "title_name": "GDmarket Bold",
    "body_name": "Pretendard Regular",
    "footer_name": "Pretendard Regular"
  }
}
```

### OAuth App settings
설치/연결 전에 app ID/secret을 여기에 저장합니다(로컬).  
- `settings.threads_app_id`
- `settings.threads_app_secret`
- `settings.meta_app_id`
- `settings.meta_app_secret`
- `settings.graph_api_version` (예: `v20.0`)

## `secrets` (tokens)
콘솔 OAuth를 통해 발급된 토큰/선택된 계정 id가 여기에 저장됩니다.

- `secrets.threads.access_token`
- `secrets.threads.user_id`
- `secrets.instagram.access_token`
- `secrets.instagram.ig_user_id`

주의:
- 로그에는 토큰이 저장되지 않도록 redaction 처리합니다.
- 게시(publish)는 항상 dry-run 기본이며 `confirm=1`이 있어야 실행합니다.

