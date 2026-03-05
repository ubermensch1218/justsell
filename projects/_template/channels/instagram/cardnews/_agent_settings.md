# Agent Settings
## marketing-director
- objective: 이번 카드뉴스의 1차 목표는 상담 신청 전환, 2차 목표는 저장/공유 유도
- must include: 첫 슬라이드에서 타깃 명시, 고객 손실 비용 2개 이상, CTA는 끝 슬라이드 1개로 고정
- must avoid: 누구에게 필요한지 흐린 문장, 과장된 표현, 한 장에 CTA 여러 개

## cardnews-copy-chief
- headline style: 12자 내외의 짧은 문장, 문제를 바로 체감하게 하는 표현 우선
- body style: 모바일 기준 1줄 18~24자, 추상어 대신 실제 상황/비용 단어 사용
- CTA style: 행동 하나만 제시하고 마감/소요시간을 함께 적기

## cardnews-designer
- template preference: claude_code_like를 기본으로 하되 커버/문제/해결/CTA 흐름은 유지
- color policy: 강조색은 핵심 단어와 버튼성 요소에만 사용, 나머지는 대비 중심으로 절제
- layout policy: 제목-본문-보조문구 계층을 고정하고 슬라이드마다 위치 흔들지 않기

## cardnews-quality-auditor
- acceptance criteria: 문장만 읽어도 맥락이 이어지고, CTA가 구체적이며, 가독성 저해 요소가 없어야 함
- blocker rules: 빈 문장, 근거 없는 주장, 스타일 불일치, 목적 불명확한 슬라이드가 있으면 실패
- pass threshold: 하드 블로커 0건 + validator 통과 + 최종 검수 메모에서 PASS 선언
