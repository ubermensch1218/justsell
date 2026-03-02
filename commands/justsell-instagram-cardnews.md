---
description: Generate Instagram cardnews spec (YAML/JSON) and render PNGs
---

$ARGUMENTS

You generate Instagram cardnews from `projects/<project>/SALES_INFO.md` and render PNG files.

Rules:
- Use Pretendard if available (download via `scripts/fetch_pretendard.sh`).
- Ensure slide number format is consistent (example: `01 / 05`).
- Keep styling consistent with the chosen template. Do not invent random typography.

Commands (example):
```bash
python3 scripts/generate_drafts.py instagram-cardnews --project projects/<project> --style bernays --format yaml
python3 scripts/render_cardnews.py --spec projects/<project>/channels/instagram/cardnews/<spec>.yaml --out projects/<project>/channels/instagram/exports
```
