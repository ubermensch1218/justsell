---
name: competitive-ads-extractor
description: Build a local competitive ads swipe file and extract reusable angles without scraping or centralized servers.
---

# Competitive Ads Extractor (Local-first)

목표: 경쟁사 광고를 “스와이프 파일”로 로컬에 쌓고, 반복되는 훅/오퍼/CTA 패턴을 뽑아낸다.

주의:
- 자동 스크래핑 없이 시작한다(계정/봇 탐지/약관 리스크 줄이기).
- 필요하면 나중에 Playwright 기반 캡처를 별도 옵션으로 추가한다.
- 이모지 금지.

## Input
- 경쟁사 목록(이름 + 제품/URL)
- 광고 5~20개 (링크 + 스크린샷/캡처)

## Output (권장 폴더)
- 스와이프 파일: `projects/<project>/research/ads/`
  - `projects/<project>/research/ads/<competitor>/<YYYY-MM-DD>/ad-01.md`
  - 스크린샷: 같은 폴더에 `*.png`

## Capture Template (ad-01.md)
- Platform: (threads / instagram / facebook / google / linkedin)
- Link:
- Creative: (image/video, format)
- Hook:
- Offer:
- Proof:
- CTA:
- Targeting guess:
- Angle tags: (pain / urgency / authority / price / social-proof / mechanism)

## Extraction
수집한 광고 10개를 보고 아래를 정리한다:
- 반복 훅 패턴 Top 5
- 오퍼 구조 Top 3
- CTA 문장 Top 10
- “금지할 표현” (우리 브랜드 톤과 안 맞는 것)

