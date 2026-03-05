# JustSell Definitions

이 문서는 JustSell 구성요소를 역할과 책임 기준으로 명확히 정의합니다.

## 1) Command
정의:
- 사용자 명령 진입점.
- `/justsell:<name>` 형태로 호출되는 오케스트레이션 레이어.
- 상태를 장기 저장하지 않고, 실행 흐름을 시작/연결하는 책임만 가짐.

현재 Command:
- `js` (`commands/js.md`): 게이트웨이 라우터 (`init | console | cardnews | remotion`)
- `justsell-console` (`commands/justsell-console.md`): 콘솔 런타임 실행
- `justsell-instagram-cardnews` (`commands/justsell-instagram-cardnews.md`): 카드뉴스 생성/검증/렌더
- `justsell-instagram-remotion-video` (`commands/justsell-instagram-remotion-video.md`): remotion 스펙/렌더
- `onboard` (`commands/onboard.md`): 초기 온보딩 실행 플로우

## 2) Skill
정의:
- 재사용 가능한 작업 단위 지시서.
- `skills/<skill>/SKILL.md`로 관리.
- Command보다 세부적이며, 특정 작업(초안 생성/설정/디자인)의 표준 절차를 제공.

현재 Skill:
- Setup/Runtime
  - `justsell-setup`
  - `console-start`
  - `project-init`
- Content Compose
  - `threads-compose`
  - `twitter-compose`
  - `linkedin-compose`
  - `reddit-compose`
  - `content-creator`
  - `social-content`
- Instagram Production
  - `instagram-cardnews`
  - `instagram-remotion-video`
- Research/Design
  - `competitive-ads-extractor`
  - `frontend-design`

## 3) Agent
정의:
- 병렬 역할 분담을 위한 역할 페르소나 문서.
- 단독 실행 엔트리포인트가 아니라, Skill/Command 오케스트레이션에서 호출되는 역할 단위.

현재 Agent:
- `marketing-director`
- `cardnews-copy-chief`
- `cardnews-designer`
- `cardnews-quality-auditor`
- `social-ops`
- `remotion-video-producer`
- `brand-systems`
- `detail-page-designer`
- `seo-designer`
- `reddit-promo`

## 4) Script
정의:
- 실제 실행 코드를 가진 런타임 엔진.
- Command/Skill이 최종적으로 호출하는 구현체.

주요 Script:
- Runtime
  - `scripts/js.py`
  - `scripts/justsell_console.py`
  - `scripts/justsell_setup.py`
- Draft Generation
  - `scripts/generate_drafts.py`
  - `scripts/generate_reddit_drafts.py`
  - `scripts/generate_remotion_spec.py`
  - `scripts/record_flow.py` (실제 UI 플로우 녹화 입력 생성)
- Rendering
  - `scripts/render_cardnews.py`
  - `scripts/render_remotion_video.py`
- Validation/Guard
  - `scripts/validate_project.py`
  - `scripts/validate_cardnews_spec.py`
  - `scripts/cardnews_pipeline_guard.py`

## 5) Project (Local-First State)
정의:
- 사용자 데이터와 산출물이 저장되는 작업 단위 루트.
- 기본 경로: `~/.claude/.js/projects/<project>/`
- override: `JUSTSELL_PROJECTS_DIR`

핵심 문서:
- `SALES_INFO.md`: 카피/콘텐츠 source of truth
- `CONVERSATION_POLICY.md`: 자동 응답 권한/정책
- `channels/*`: 채널별 초안/스펙/렌더 결과물

## 6) Cardnews Pipeline Artifact
정의:
- 카드뉴스 품질 보장을 위한 필수 제약 문서.
- 생성/렌더 전 선행되어야 하는 컨텍스트.

필수 파일:
- `_agent_settings.md`
- `_parallel_roles.md`
- `_creative_brief.md`
- `_strategy_lock.md`

정책:
- 기본 모드: zero-touch auto-bootstrap
- strict 모드: `JUSTSELL_STRICT_PIPELINE=1`

## 6.1) Remotion Flow Recording Artifact
정의:
- Remotion 영상에 실제 제품/내부 UI 흐름을 삽입하기 위한 녹화 입력.

권장 파일:
- `~/.claude/.js/projects/<project>/channels/instagram/remotion/_flow_steps.json`
- `~/.claude/.js/projects/<project>/channels/instagram/flow-recordings/*.(webm|mp4)`
- `~/.claude/.js/projects/<project>/channels/instagram/remotion/_flow_manifest.json` (모듈 목록 + 스티치 결과)

정책:
- 텍스트-only 스토리 구성 금지, 실제 플로우 녹화를 필수 입력으로 사용.
- 기능 단위(`modules[]`)로 분리 녹화하고 필요 시 자동으로 이어붙여 사용.

## 7) Config vs Secrets
정의:
- Config (`settings`): 템플릿/테마/앱 설정 등 비토큰 값
- Secrets (`secrets`): OAuth 토큰 및 계정 식별자

위치:
- `~/.claude/.js/config.json`

원칙:
- Local-first 저장
- publish는 dry-run 기본, 명시 확인 시에만 실행

## 8) 책임 경계 요약
- Command: 실행 시작과 라우팅
- Skill: 작업 표준 절차
- Agent: 역할 분업 단위
- Script: 실제 구현 코드
- Project/Config: 상태와 산출물 저장소
