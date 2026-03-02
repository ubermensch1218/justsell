---
name: linkedin-compose
description: Draft LinkedIn posts from projects/<project>/영업Info.md
---

# linkedin-compose

`projects/<project>/영업Info.md`를 기반으로 LinkedIn 초안을 생성해 `drafts/`에 저장합니다.

## Input
- `projects/<project>/영업Info.md`

## Output
- `projects/<project>/channels/linkedin/drafts/<yyyymmdd-hhmm>.md`

## Commands
```bash
python3 scripts/generate_drafts.py linkedin --project projects/<project> --style bernays
```
