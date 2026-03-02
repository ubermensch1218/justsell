---
name: twitter-compose
description: Draft X (Twitter) posts from projects/<project>/영업Info.md
---

# twitter-compose

`projects/<project>/영업Info.md`를 기반으로 트위터 초안을 생성해 `drafts/`에 저장합니다.

## Input
- `projects/<project>/영업Info.md`

## Output
- `projects/<project>/channels/twitter/drafts/<yyyymmdd-hhmm>.md`

## Commands
```bash
python3 scripts/generate_drafts.py twitter --project projects/<project> --style bernays
```
