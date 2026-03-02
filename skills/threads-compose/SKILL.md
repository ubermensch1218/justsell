---
name: threads-compose
description: Draft Threads posts from projects/<project>/영업Info.md
---

# threads-compose

`projects/<project>/영업Info.md`를 기반으로 Threads 초안을 생성해 `drafts/`에 저장합니다.

## Input
- `projects/<project>/영업Info.md`

## Output
- `projects/<project>/channels/threads/drafts/<yyyymmdd-hhmm>.md`

## Commands
```bash
python3 scripts/generate_drafts.py threads --project projects/<project> --style bernays
```
