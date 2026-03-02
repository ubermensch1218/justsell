# Workflow

## 1) Per-Project 기준 문서 유지
- 프로젝트별로 `projects/<project>/영업Info.md`를 최신 상태로 유지합니다.
- 카피/카드뉴스/DM은 이 문서에서 파생됩니다.
- AI 상담/대화 권한은 `projects/<project>/상담권한.md`에서 정의합니다.

## 2) 채널별 산출물 관리
- 채널 공통 규칙/템플릿은 `channels/<channel>/`에 둡니다.
- 프로젝트별 초안/발행물은 `projects/<project>/channels/<channel>/` 아래에서 관리합니다.

## 3) Instagram 카드뉴스
- 카드뉴스 스펙(YAML): `projects/<project>/channels/instagram/cardnews/*.yaml`
- 결과물(PNG): `projects/<project>/channels/instagram/exports/`
- 생성 스크립트: `scripts/render_cardnews.py`

## 4) 검증
- 필수 파일 누락/경로를 `scripts/validate_project.py`로 확인합니다.
