---
name: reddit-compose
description: Draft Reddit posts from projects/<project>/SALES_INFO.md with product/brand/channel tone tripod
---

# reddit-compose

`projects/<project>/SALES_INFO.md`와 `projects/<project>/brand.md`를 바탕으로 Reddit 초안을 생성합니다.

출력:
- `projects/<project>/channels/reddit/drafts/<yyyymmdd-hhmmss>.md`

실행:
```bash
python3 scripts/generate_reddit_drafts.py --project projects/<project> --style bernays
```

서브레딧 맞춤 톤:
```bash
python3 scripts/generate_reddit_drafts.py --project projects/<project> --style bernays --subreddit r/webdev
```

근황/복귀 스타일:
```bash
python3 scripts/generate_reddit_drafts.py --project projects/<project> --style comeback
```
