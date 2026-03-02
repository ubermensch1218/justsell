# Workflow

JustSell은 로컬-first로 “SALES_INFO.md → 초안/카드뉴스 스펙 → 렌더 → (선택) 게시”를 반복합니다.

## Flow A: 신규 설치 사용자
1) Install
   - `/plugin marketplace add https://github.com/ubermensch1218/justsell`
   - `/plugin install justsell`
2) Init
   - `/js init` → `/connect`에서 Setup 저장
     - 카드뉴스 템플릿, 키컬러, 폰트
     - Threads/Meta OAuth app 설정
     - (선택) public_base_url
3) OAuth
   - `/connect`에서 Threads/Instagram OAuth 연결
   - Instagram은 `Discover accounts` → 1개 `Select`해서 `ig_user_id` 고정
4) Project
   - `/connect`에서 slug로 프로젝트 생성 또는 `cp -R projects/_template projects/<slug>`
   - `projects/<slug>/SALES_INFO.md` 작성
5) Generate + Render
   - 콘솔 `/`에서 프로젝트 선택 → Generate + Render

## Flow B: 기존 운영 사용자(이미 계정/토큰 있음)
1) Install/Update 후 `/js console`
2) `/connect`에서 Setup만 보강
   - 카드뉴스 템플릿/키컬러/폰트(기존에 없던 부분)
   - public_base_url(IG publish 필요 시)
3) Instagram 계정 선택 재확인
   - `/connect` → Discover accounts → Select (1개)
4) 운영 루프
   - `/`에서 Generate/Render
   - Publish는 dry-run 기본, confirm이 있어야 실행

## 1) Per-Project 기준 문서 유지
- 프로젝트별로 `projects/<project>/SALES_INFO.md`를 최신 상태로 유지합니다.
- 카피/카드뉴스/DM은 이 문서에서 파생됩니다.
- AI 상담/대화 권한은 `projects/<project>/CONVERSATION_POLICY.md`에서 정의합니다.

## 2) 채널별 산출물 관리
- 채널 공통 규칙/템플릿은 `channels/<channel>/`에 둡니다.
- 프로젝트별 초안/발행물은 `projects/<project>/channels/<channel>/` 아래에서 관리합니다.

## 3) Instagram 카드뉴스
- 카드뉴스 스펙(YAML): `projects/<project>/channels/instagram/cardnews/*.yaml`
- 결과물(PNG): `projects/<project>/channels/instagram/exports/`
- 생성 스크립트: `scripts/render_cardnews.py`

## 4) 검증
- 필수 파일 누락/경로를 `scripts/validate_project.py`로 확인합니다.
