---
name: linkedin-compose
description: Draft LinkedIn posts from projects/<project>/SALES_INFO.md
---

# linkedin-compose

`projects/<project>/SALES_INFO.md`를 기반으로 LinkedIn 초안을 생성해 `drafts/`에 저장합니다.

## Input
- `projects/<project>/SALES_INFO.md`

## Output
- `projects/<project>/channels/linkedin/drafts/<yyyymmdd-hhmm>.md`

## Commands
```bash
python3 scripts/generate_drafts.py linkedin --project projects/<project> --style bernays
```
