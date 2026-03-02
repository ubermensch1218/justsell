# Cardnews Automation (Template vs Variables)

목표: “레퍼런스 같은 카드뉴스”를 **자동 생성**하려면, spec을 2~3 레이어로 쪼개는 게 제일 안정적입니다.

## 1) 템플릿(거의 고정)
**A. Style preset (디자인/레이아웃)**
- 파일 위치(권장): `channels/instagram/templates/`
- 예시:
  - `cardnews.claude_code_like.yaml`
  - `cardnews.claude_code_like.json`

### 사용자 템플릿(업데이트에 안 날아가게)
플러그인/레포 업데이트와 상관없이 “내 템플릿 폴더”에 두고 쓰려면:
- `~/.claude/.js/templates/instagram/`
- 확장자: `.yaml`, `.yml`, `.json`

콘솔 `/connect`의 Template 드롭다운과 `/js init` 위저드에서 자동으로 목록에 뜹니다.

여기에 들어가는 것(고정):
- `canvas`: 사이즈(예: 1080x1080)
- `theme`: 배경/컬러/패널/커버/pills/bullets/title_rule
- `font`: 타이틀 Bold, 바디 Regular 같은 “굵기” 고정
- `layout`: padding, card_padding, footer_align 등 “위치” 고정
- `slides[].kind`: cover/bullets/pills 같은 레이아웃 타입

## 2) 가변(프로젝트/캠페인)
**B. Project facts (Source of Truth)**
- 파일 위치: `projects/<project>/영업Info.md`
- 여기서 뽑는 것:
  - 프로젝트명/한줄/ICP/문제/가치/차별점/CTA

**C. Campaign brief (선택)**
- 파일 위치(권장): `projects/<project>/channels/instagram/brief.md` (아직은 템플릿만)
- 여기서 뽑는 것:
  - 목표(인지/리드/세일즈)
  - 톤(진지/가벼움)
  - 기간/행사 정보(커버 footer 문구)

## 3) “와리가리” 하는 부분(자동 생성 영역)
자동화 스크립트가 매번 바꾸는 곳은 사실상 “copy” 뿐입니다.

변하는 것:
- `brand.name/contact` (프로젝트마다)
- `slides[].title/body/footer` (캠페인마다)

안 변하는 것:
- `theme/*`, `layout/*`, `font/*`, `slides[].kind`

## 현재 구현 상태
- 렌더러: `scripts/render_cardnews.py`
  - YAML/JSON spec 둘 다 입력 가능
  - `slides[].kind`에 따라 cover/bullets/pills 렌더링
- 생성기: `scripts/generate_drafts.py`
  - `projects/<project>/영업Info.md` → 카드뉴스 spec 생성 가능
  - 출력 포맷: `--format yaml|json`

## 추천 운영 플로우
1) 스타일 확정(템플릿 고정): `channels/instagram/templates/cardnews.claude_code_like.(yaml|json)`
2) 프로젝트 팩트 유지: `projects/<project>/영업Info.md`
3) 캠페인별로 copy 생성:
   - 자동: `scripts/generate_drafts.py instagram-cardnews --project projects/<project> --style bernays --format json`
   - 필요 시 사람이 커버 footer/문구만 손봄
4) 렌더:
   - `python3 scripts/render_cardnews.py --spec <spec>.json --out <exports>`

## ENV로 키컬러(테마) 바꾸기
디자인 템플릿 파일을 건드리지 않고 “키컬러”만 바꾸고 싶으면 ENV override를 씁니다.

지원 ENV:
- `JUSTSELL_ACCENT_PRIMARY` (예: `#FF6A2A`)
- `JUSTSELL_ACCENT_SECONDARY` (예: `#111111`)
- `JUSTSELL_COVER_FILL` (예: `#FF6A2A`)
- `JUSTSELL_PANEL_FILL` (예: `#141414`)
- `JUSTSELL_BG_KIND` (`solid` 또는 `gradient`)
- `JUSTSELL_BG_SOLID` (예: `#FFFFFF`)
- `JUSTSELL_BG_FROM`, `JUSTSELL_BG_TO` (그라디언트용, 예: `#050505`, `#0B0F19`)

## 폰트를 “이름”으로 지정하기
파일 경로 대신, “폰트 이름”으로 지정할 수 있습니다. 렌더러는 `assets/fonts/`와 OS 폰트 디렉토리에서 파일명을 기반으로 찾습니다.

- 예시 템플릿: `channels/instagram/templates/cardnews.font_by_name.example.yaml`
- 키:
  - `font.title_name` (예: `GDmarket Bold`)
  - `font.body_name` (예: `Pretendard Regular`)
  - `font.footer_name` (예: `Pretendard Regular`)
- 팀에서 “없는 폰트면 실패”가 필요하면:
  - spec: `font.strict: true` 또는 ENV: `JUSTSELL_STRICT_FONTS=1`
