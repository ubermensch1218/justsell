# Workflow

JustSell은 로컬-first로 “SALES_INFO.md → 초안/카드뉴스 스펙 → 렌더 → (선택) 게시”를 반복합니다.

구성요소 정의(Command/Skill/Agent/Script/Artifact)는 `docs/DEFINITIONS.md`를 기준으로 합니다.

## Flow A: 신규 설치 사용자
1) Install
   - `/plugin marketplace add https://github.com/ubermensch1218/justsell`
   - `/plugin install justsell`
2) Init
   - `/justsell:js init` → `/connect`에서 Setup 저장
   - 헷갈리면 `/justsell:onboard`로 한 단계씩 진행
     - 카드뉴스 템플릿, 키컬러, 폰트
     - Threads/Meta OAuth app 설정
     - (선택) public_base_url
3) OAuth
   - `/connect`에서 Threads OAuth를 먼저 연결
   - Threads 연결이 끝나면 Instagram OAuth 연결
   - Instagram은 `Discover accounts` → 1개 `Select`해서 `ig_user_id` 고정
4) Project
   - `/connect`에서 slug로 프로젝트 생성(권장)
   - 프로젝트는 로컬에 저장됩니다:
     - 기본: `~/.claude/.js/projects/<slug>/`
     - override: `JUSTSELL_PROJECTS_DIR`
   - `~/.claude/.js/projects/<slug>/SALES_INFO.md` 작성
5) Generate + Render
   - 콘솔 `/`에서 프로젝트 선택 → Generate + Render

## Flow B: 기존 운영 사용자(이미 계정/토큰 있음)
1) Install/Update 후 `/justsell:js console`
2) `/connect`에서 Setup만 보강
   - 카드뉴스 템플릿/키컬러/폰트(기존에 없던 부분)
   - public_base_url(IG publish 필요 시)
3) Instagram 계정 선택 재확인
   - `/connect` → Discover accounts → Select (1개)
4) 운영 루프
   - `/`에서 Generate/Render
   - Publish는 dry-run 기본, confirm이 있어야 실행

## 1) Per-Project 기준 문서 유지
- 프로젝트별로 `~/.claude/.js/projects/<project>/SALES_INFO.md`를 최신 상태로 유지합니다.
- 카피/카드뉴스/DM은 이 문서에서 파생됩니다.
- AI 상담/대화 권한은 `~/.claude/.js/projects/<project>/CONVERSATION_POLICY.md`에서 정의합니다.

## 2) 채널별 산출물 관리
- 채널 공통 규칙/템플릿은 `channels/<channel>/`에 둡니다.
- 프로젝트별 초안/발행물은 `~/.claude/.js/projects/<project>/channels/<channel>/` 아래에서 관리합니다.

## 3) Instagram 카드뉴스
- 하드가드: 아래 파일이 없거나 미완성이면 generate/render가 실패합니다.
  - `~/.claude/.js/projects/<project>/channels/instagram/cardnews/_parallel_roles.md`
  - `~/.claude/.js/projects/<project>/channels/instagram/cardnews/_creative_brief.md`
  - `~/.claude/.js/projects/<project>/channels/instagram/cardnews/_strategy_lock.md`
- 운영 기본 플로우:
  - zero-touch 자동 부트스트랩(기본)
  - 역할 병렬 패스(`marketing-director`, `cardnews-copy-chief`, `cardnews-designer`, `cardnews-quality-auditor`)
  - spec 생성 → `scripts/validate_cardnews_spec.py` 통과 → 렌더
  - strict 수동 모드가 필요하면 `JUSTSELL_STRICT_PIPELINE=1` 사용
- 카드뉴스 스펙(YAML): `~/.claude/.js/projects/<project>/channels/instagram/cardnews/*.yaml`
- 결과물(PNG): `~/.claude/.js/projects/<project>/channels/instagram/exports/`
- 생성 스크립트: `scripts/render_cardnews.py`

## 4) 검증
- 필수 파일 누락/경로를 `scripts/validate_project.py`로 확인합니다.

## 5) Remotion (Flow Recording First)
- Remotion은 텍스트만으로 구성하지 않고 실제 플로우 녹화 입력을 필수로 사용합니다.
- 필수 스텝 파일:
  - `~/.claude/.js/projects/<project>/channels/instagram/remotion/_flow_steps.json`
  - 예시 템플릿: `templates/briefs/remotion_flow_steps.example.json`
- 모듈 구조 권장:
  - `_flow_steps.json`에 `modules[]`를 정의해 기능별 클립으로 녹화
  - 녹화 결과 manifest: `~/.claude/.js/projects/<project>/channels/instagram/remotion/_flow_manifest.json`
- 실행 순서:
  1) `scripts/record_flow.py`로 흐름 영상 녹화
  2) 기능별 모듈 클립 생성 + (옵션) 자동 스티치
  3) `scripts/generate_remotion_spec.py --flow-manifest <manifest.json>`
  4) `scripts/render_remotion_video.py`로 최종 렌더
