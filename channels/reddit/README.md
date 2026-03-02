# Reddit

## 운영 원칙
- 서브레딧 규칙 우선: 자기홍보, 링크, 플레어 정책 먼저 확인
- 가치 선행: 홍보 전에 문제 맥락/시행착오/결과를 먼저 제공
- 톤 삼박자: 제품 톤 + 브랜드 톤 + 채널 톤을 동시에 반영
- 링크 최소화: safe draft는 무링크, publish-ready도 1개 이하
- 금지: 브리게이딩, 투표 유도, 다계정, 대량 DM

## 템플릿
- `channels/reddit/templates/post.md`

## 생성 커맨드
```bash
python3 scripts/generate_reddit_drafts.py --project projects/<project> --style bernays
```

서브레딧 맞춤 톤:
```bash
python3 scripts/generate_reddit_drafts.py --project projects/<project> --style bernays --subreddit r/startups
```
