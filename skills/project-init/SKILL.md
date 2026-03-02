---
name: project-init
description: Create a new project folder from template and validate required files
---

# project-init

프로젝트 폴더를 만들고 필수 파일이 있는지 검증합니다.

## Input
- project slug (예: `my-product`)

## Output
- `projects/<project-slug>/` 생성
- `projects/<project-slug>/SALES_INFO.md`, `brand.md`, `product.md`, `CONVERSATION_POLICY.md` 존재 확인

## Commands
```bash
cp -R projects/_template projects/<project-slug>
python3 scripts/validate_project.py projects/<project-slug>
```
