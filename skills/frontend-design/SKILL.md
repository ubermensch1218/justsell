---
name: frontend-design
description: Improve JustSellConsole UI and cardnews style presets (typography, spacing, color system) without breaking local-first constraints.
---

# Frontend Design (JustSellConsole + Cardnews)

목표:
- JustSellConsole UI를 “설정/연결/미리보기” 관점에서 덜 촌스럽게 만든다.
- 카드뉴스 템플릿을 “폰트/굵기/여백/넘버링” 기준으로 시스템화한다.

규칙:
- UI는 로컬 HTML (server-side string) 기준으로 최소 변경.
- 색은 `~/.claude/.js/config.json`의 `settings.cardnews.theme`로 제어(또는 ENV override).
- 폰트는 이름 기반(`Pretendard Regular`)으로 지정하고, 없으면 `assets/fonts/`에 추가한다.
- 이모지 금지.

## Quick Audit Checklist
JustSellConsole:
- 정보 구조: `/connect`에 Setup → OAuth → Account Select → Project 순서가 한 화면에서 보이는가
- 경고/가드레일: publish는 confirm 없으면 절대 실행되지 않는가
- 대비: 텍스트 대비가 충분한가(회색 너무 연하지 않게)

Cardnews:
- Title weight/size: Bold가 과하지 않은가
- Body line-height: 너무 빡빡하거나 느슨하지 않은가
- Accent bar: 두께/간격이 일관적인가
- Slide number: `01 / 05` 형식, 좌하단, 안전영역에 들어오는가

## Where to edit
- Console UI: `apps/justsell_console/server.py`
- Templates: `channels/instagram/templates/`
- Renderer: `scripts/render_cardnews.py`

