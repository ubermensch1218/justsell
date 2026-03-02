---
name: threads-compose
description: Draft Threads posts from projects/<project>/SALES_INFO.md
---

# threads-compose

`projects/<project>/SALES_INFO.md`를 기반으로 Threads 초안을 생성해 `drafts/`에 저장합니다.

## Input
- `projects/<project>/SALES_INFO.md`

## Output
- `projects/<project>/channels/threads/drafts/<yyyymmdd-hhmm>.md`

## Commands
```bash
python3 scripts/generate_drafts.py threads --project projects/<project> --style bernays
```
