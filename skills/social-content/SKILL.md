---
name: social-content
description: Produce a small weekly content pack (Threads + Instagram cardnews) with consistent voice and local-first outputs.
---

# Social Content Pack (Threads + Instagram)

목표: “Threads 한 편 + Instagram 카드뉴스 한 세트”를 한 번에 뽑아 운영 루프를 만든다.

규칙:
- Source of Truth: `projects/<project>/SALES_INFO.md`
- 카드뉴스 스타일은 템플릿으로 고정하고, 매번 바꾸는 건 `slides[].title/body/footer`만.
- 게시(publish)는 콘솔에서 dry-run 기본.

## Step 0) 프로젝트 준비
- `projects/<project>/SALES_INFO.md` 최신화
- (권장) `projects/<project>/CONVERSATION_POLICY.md`로 자동 응답 권한 정의

## Step 1) Threads draft 생성
```bash
python3 scripts/generate_drafts.py threads --project projects/<project> --style bernays
```

## Step 2) Instagram 카드뉴스 spec 생성 + 렌더
```bash
python3 scripts/generate_drafts.py instagram-cardnews --project projects/<project> --style bernays --format yaml
python3 scripts/render_cardnews.py --spec projects/<project>/channels/instagram/cardnews/<spec>.yaml --out projects/<project>/channels/instagram/exports
```

## Step 3) 콘솔에서 미리보기/게시(dry-run)
```bash
./bin/js console
```
- Threads: Generate draft → 필요 시 수정 → Publish (confirm=1)
- Instagram: Render 확인 → caption 편집 → Publish (confirm=1)
