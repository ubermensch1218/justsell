---
name: content-creator
description: Create audience-focused marketing content (Threads, LinkedIn, Instagram captions) using project SalesInfo.md as source of truth.
---

# Content Creator (JustSell)

목표: 프로젝트의 `SalesInfo.md`를 기준으로 “훅 → 가치 → 증거 → CTA” 구조의 콘텐츠를 빠르게 만든다.

전제:
- 사실/수치/가격/일정은 `projects/<project>/SalesInfo.md`에만 의존한다.
- 게시(publish)는 기본 dry-run. 실제 게시하려면 콘솔에서 `confirm=1`을 명시한다.
- 이모지 금지.

## Input
- `projects/<project>/SalesInfo.md`
- (선택) 캠페인 목적: awareness | leads | sales
- (선택) 톤: bernays | plain | comeback

## Output (권장 산출물 위치)
- Threads: `projects/<project>/channels/threads/drafts/<timestamp>.md`
- LinkedIn: `projects/<project>/channels/linkedin/drafts/<timestamp>.md`
- Instagram caption: 콘솔에서 spec 선택 후 캡션 편집

## Fast Path (이미 자동화된 생성기 사용)
Threads draft:
```bash
python3 scripts/generate_drafts.py threads --project projects/<project> --style bernays
```

LinkedIn draft:
```bash
python3 scripts/generate_drafts.py linkedin --project projects/<project> --style bernays
```

## Manual Framework (생성기가 부족할 때)
아래 질문 3개만 답해서 카피를 만든다:
1) 독자가 “지금 당장” 겪는 문제 1개는?
2) 기존 방식(대안)이 당연해지는 순간 생기는 숨은 비용 1개는?
3) 새 기준(한 문장)은?

그리고 출력은 항상 이 순서:
- Hook (1문장)
- Context (2~3문장)
- Value bullets (3개)
- Proof (있으면 1개)
- CTA (1문장)

