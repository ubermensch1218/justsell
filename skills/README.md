# Skills (JustSell Marketing Pack)

이 레포는 “마케팅 운영용 Skills 모음”으로 쓸 수 있게 구성합니다.

## 설치(옵션)
Claude Code는 기본적으로 `~/.claude/skills` 아래의 `SKILL.md`를 Skills로 인식합니다.
Codex도 `$CODEX_HOME/skills`를 사용합니다.
그래서 이 레포의 `skills/*`를 심볼릭 링크로 연결하는 방식을 권장합니다.

```bash
bash scripts/install_skills.sh
```

## 포함된 Skills
- `skills/project-init/`: 프로젝트 폴더 생성 + 필수 파일 점검
- `skills/twitter-compose/`: 트위터 초안 생성(파일로 저장)
- `skills/threads-compose/`: Threads 초안 생성(파일로 저장)
- `skills/linkedin-compose/`: LinkedIn 초안 생성(파일로 저장)
- `skills/instagram-cardnews/`: 영업Info.md 기반 카드뉴스 스펙 생성 + PNG 렌더
