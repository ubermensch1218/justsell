# Integrations

채널 API 연동(게시/예약/댓글 수집/답장)은 여기서 관리합니다.

원칙:
- URL/토큰 하드코딩 금지: 환경변수로만 주입
- 실제 게시/답장은 “명시적으로” 실행(드라이런 기본)
- 프로젝트 컨텍스트는 항상 `projects/<project>/영업Info.md`에서 가져옴

현재 상태:
- 구조/인터페이스만 스텁으로 제공합니다(실제 API 호출은 별도 구현 단계).

## 디렉토리
- `integrations/meta/`: Instagram/Threads
- `integrations/twitter/`: X(Twitter)
- `integrations/linkedin/`: LinkedIn
- `integrations/ports.py`: 채널 공통 포트(인터페이스)

