---
name: frontend-design
description: Production UI/design system tuning for console + cardnews templates
---

# frontend-design

[FRONTEND DESIGN MODE ACTIVATED]

## Operating Goal
Align console UI and cardnews visual system to a coherent production baseline.

## Ownership
- Console UI: `apps/justsell_console/server.py`
- Cardnews templates: `channels/instagram/templates/`
- Cardnews renderer: `scripts/render_cardnews.py`

## Execution Rules
1) Keep local-first behavior and existing runtime contracts.
2) Do not introduce publish-by-default behavior.
3) Preserve accessibility contrast and predictable typography.
4) Keep changes minimal and testable.

## Quality Checklist
- Information order in `/connect`: Setup -> OAuth -> Account -> Project
- Publish guard remains explicit-confirm only
- Text contrast is readable (`text-gray-600` equivalent or stronger)
- Cardnews title/body/footer hierarchy is consistent
- Slide number and safe area are stable across templates
