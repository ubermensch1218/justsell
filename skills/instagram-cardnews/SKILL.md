---
name: instagram-cardnews
description: Generate Instagram cardnews spec and render PNGs from projects/<project>/SALES_INFO.md
---

# instagram-cardnews

`SALES_INFO.md`를 기준으로 카드뉴스 스펙(YAML)을 만들고, PNG를 렌더합니다.

## Input
- `projects/<project>/SALES_INFO.md`

## Output
- spec: `projects/<project>/channels/instagram/cardnews/<yyyymmdd-hhmm>.yaml`
- images: `projects/<project>/channels/instagram/exports/<spec-stem>-*.png`

## Commands
```bash
python3 scripts/generate_drafts.py instagram-cardnews --project projects/<project> --style bernays
python3 scripts/render_cardnews.py \
  --spec projects/<project>/channels/instagram/cardnews/<spec>.yaml \
  --out  projects/<project>/channels/instagram/exports
```

### Template 기반으로 생성(권장)
```bash
python3 scripts/generate_drafts.py instagram-cardnews \
  --project projects/<project> \
  --style bernays \
  --format yaml \
  --template channels/instagram/templates/cardnews.boc_like.yaml
```
