#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import re


STRATEGY_LOCK_FILENAME = "_strategy_lock.md"
CREATIVE_BRIEF_FILENAME = "_creative_brief.md"
PARALLEL_ROLES_FILENAME = "_parallel_roles.md"
AGENT_SETTINGS_FILENAME = "_agent_settings.md"

REQUIRED_FIELDS: list[str] = [
  "primary segment",
  "secondary segment",
  "tone guardrails",
  "hook",
  "cta",
]

REQUIRED_BRIEF_FIELDS: list[str] = [
  "hero offer",
  "primary audience",
  "tone",
  "visual direction",
  "primary cta",
]

REQUIRED_ROLE_SECTIONS: list[str] = [
  "marketing-director",
  "cardnews-copy-chief",
  "cardnews-designer",
  "cardnews-quality-auditor",
]

REQUIRED_AGENT_SETTING_SECTIONS: dict[str, list[str]] = {
  "marketing-director": [
    "objective",
    "must include",
    "must avoid",
  ],
  "cardnews-copy-chief": [
    "headline style",
    "body style",
    "cta style",
  ],
  "cardnews-designer": [
    "template preference",
    "color policy",
    "layout policy",
  ],
  "cardnews-quality-auditor": [
    "acceptance criteria",
    "blocker rules",
    "pass threshold",
  ],
}

PLACEHOLDER_VALUES: set[str] = {
  "",
  "-",
  "todo",
  "tbd",
  "n/a",
  "(fill)",
  "(작성)",
  "(추가)",
}


def _strict_mode() -> bool:
  return _norm_value(os.environ.get("JUSTSELL_STRICT_PIPELINE", "")) in {"1", "true", "yes", "on"}


def strategy_lock_path(project_dir: Path) -> Path:
  return (project_dir / "channels" / "instagram" / "cardnews" / STRATEGY_LOCK_FILENAME).resolve()


def creative_brief_path(project_dir: Path) -> Path:
  return (project_dir / "channels" / "instagram" / "cardnews" / CREATIVE_BRIEF_FILENAME).resolve()


def parallel_roles_path(project_dir: Path) -> Path:
  return (project_dir / "channels" / "instagram" / "cardnews" / PARALLEL_ROLES_FILENAME).resolve()


def agent_settings_path(project_dir: Path) -> Path:
  return (project_dir / "channels" / "instagram" / "cardnews" / AGENT_SETTINGS_FILENAME).resolve()


def strategy_lock_template() -> str:
  return (
    "# Strategy Lock\n"
    "- primary segment: 마케팅 인력이 1~3명인 한국 B2B SaaS 팀(창업자 또는 그로스 리드 중심)\n"
    "- secondary segment: 콘텐츠 제작을 혼자 담당하는 실무 마케터(기획-디자인-배포를 모두 수행)\n"
    "- tone guardrails: 추상어 대신 실제 문제/비용 중심으로 작성하고, 과장/가짜 수치 표현은 금지\n"
    "- hook: \"열심히 올리는데 문의가 안 들어오는 이유\"를 첫 장에서 바로 드러낸다\n"
    "- CTA: 이번 주 안에 15분 진단 콜 예약(현재 카드뉴스 흐름 점검 + 개선 포인트 3개 제공)\n"
  )


def creative_brief_template() -> str:
  return (
    "# Creative Brief\n"
    "- hero offer: \"게시 직전까지 바로 쓸 수 있는 카드뉴스를 한 번에 제작해주는 운영 파이프라인\"\n"
    "- primary audience: 콘텐츠는 만들지만 리드 전환이 약한 한국 B2B SaaS 창업팀\n"
    "- tone: 단정하고 실무적인 어조, 과장 없이 손실/효과를 분명하게 전달\n"
    "- visual direction: claude-like 기반, 고대비 타이포와 넉넉한 여백, 포인트 컬러는 최소 사용\n"
    "- primary CTA: \"15분 진단 콜 신청\"으로 단일화하고, 신청 전 얻는 결과를 한 줄로 명시\n"
  )


def parallel_roles_template() -> str:
  return (
    "# Parallel Role Outputs\n"
    "## marketing-director\n"
    "- segment positioning: \"콘텐츠는 만들지만 전환은 안 나는\" 초기 B2B 팀의 실무 통증에 맞춰 포지셔닝\n"
    "- core promise: 기획-카피-디자인을 한 흐름으로 묶어, 바로 게시 가능한 카드뉴스를 빠르게 만든다\n"
    "- cta angle: 큰 계약 제안 대신 15분 진단 콜로 진입장벽을 낮춰 첫 응답을 확보한다\n"
    "\n"
    "## cardnews-copy-chief\n"
    "- copy rewrite notes: 첫 2장은 공감 문장, 중간 2장은 해결 구조, 마지막 1장은 행동 유도 문장으로 분리\n"
    "- hook options: A) 시간 낭비형, B) 리드 손실형, C) 팀 피로 누적형 프레임 중 상황에 맞게 선택\n"
    "- cta wording: \"이번 주 빈 시간 15분만 잡아주세요. 현재 흐름을 바로 점검해드립니다.\"\n"
    "\n"
    "## cardnews-designer\n"
    "- visual system: 제목 대비를 강하게 두고 본문은 안정된 리듬으로 배치해 스크롤 이탈을 줄인다\n"
    "- layout notes: 커버는 한 메시지 원칙, 문제 슬라이드는 여백을 넓혀 문장 호흡을 확보한다\n"
    "- template/color decisions: claude_code_like 기반, 오렌지 포인트 최소 사용, 어두운 텍스트 대비 유지\n"
    "\n"
    "## cardnews-quality-auditor\n"
    "- pass/fail: pass\n"
    "- blocking issues: 없음. 다만 캡션에 타깃 업종 예시 1줄 추가 권장\n"
    "- final readiness note: 시안 퀄리티는 게시 가능 수준이며, 실제 게시 전 CTA 링크만 최종 확인\n"
  )


def agent_settings_template() -> str:
  return (
    "# Agent Settings\n"
    "## marketing-director\n"
    "- objective: 이번 카드뉴스의 1차 목표는 상담 신청 전환, 2차 목표는 저장/공유 유도\n"
    "- must include: 첫 슬라이드에서 타깃 명시, 고객 손실 비용 2개 이상, CTA는 끝 슬라이드 1개로 고정\n"
    "- must avoid: 누구에게 필요한지 흐린 문장, 과장된 표현, 한 장에 CTA 여러 개\n"
    "\n"
    "## cardnews-copy-chief\n"
    "- headline style: 12자 내외의 짧은 문장, 문제를 바로 체감하게 하는 표현 우선\n"
    "- body style: 모바일 기준 1줄 18~24자, 추상어 대신 실제 상황/비용 단어 사용\n"
    "- CTA style: 행동 하나만 제시하고 마감/소요시간을 함께 적기\n"
    "\n"
    "## cardnews-designer\n"
    "- template preference: claude_code_like를 기본으로 하되 커버/문제/해결/CTA 흐름은 유지\n"
    "- color policy: 강조색은 핵심 단어와 버튼성 요소에만 사용, 나머지는 대비 중심으로 절제\n"
    "- layout policy: 제목-본문-보조문구 계층을 고정하고 슬라이드마다 위치 흔들지 않기\n"
    "\n"
    "## cardnews-quality-auditor\n"
    "- acceptance criteria: 문장만 읽어도 맥락이 이어지고, CTA가 구체적이며, 가독성 저해 요소가 없어야 함\n"
    "- blocker rules: 빈 문장, 근거 없는 주장, 스타일 불일치, 목적 불명확한 슬라이드가 있으면 실패\n"
    "- pass threshold: 하드 블로커 0건 + validator 통과 + 최종 검수 메모에서 PASS 선언\n"
  )


def _norm_key(s: str) -> str:
  return re.sub(r"\s+", " ", s.strip().lower())


def _norm_value(s: str) -> str:
  return re.sub(r"\s+", " ", s.strip().lower())


def _parse_strategy_lock(text: str) -> dict[str, str]:
  out: dict[str, str] = {}
  for raw in text.splitlines():
    m = re.match(r"^\s*-\s*([^:]+)\s*:\s*(.*?)\s*$", raw)
    if not m:
      continue
    key = _norm_key(m.group(1))
    val = m.group(2).strip()
    out[key] = val
  return out


def _is_effective_value(value: str) -> bool:
  return _norm_value(value) not in PLACEHOLDER_VALUES


def _extract_section(text: str, section: str) -> str:
  pattern = rf"(?ms)^##\s*{re.escape(section)}\s*\n(.*?)(?=^##\s|\Z)"
  m = re.search(pattern, text)
  return m.group(1) if m else ""


def ensure_strategy_lock(project_dir: Path) -> Path:
  lock_path = strategy_lock_path(project_dir)
  lock_path.parent.mkdir(parents=True, exist_ok=True)

  if not lock_path.exists():
    lock_path.write_text(strategy_lock_template(), encoding="utf-8")
    if _strict_mode():
      raise RuntimeError(
        f"Missing strategy lock: {lock_path}. "
        "Template created. Fill all required fields and retry."
      )
    return lock_path

  parsed = _parse_strategy_lock(lock_path.read_text(encoding="utf-8"))
  missing: list[str] = []
  for field in REQUIRED_FIELDS:
    v = parsed.get(field, "")
    if not _is_effective_value(v):
      missing.append(field)

  if missing:
    if _strict_mode():
      raise RuntimeError(
        f"Incomplete strategy lock: {lock_path}. "
        f"Missing/empty fields: {', '.join(missing)}"
      )
    lock_path.write_text(strategy_lock_template(), encoding="utf-8")

  return lock_path


def ensure_creative_brief(project_dir: Path) -> Path:
  brief_path = creative_brief_path(project_dir)
  brief_path.parent.mkdir(parents=True, exist_ok=True)

  if not brief_path.exists():
    brief_path.write_text(creative_brief_template(), encoding="utf-8")
    if _strict_mode():
      raise RuntimeError(
        f"Missing creative brief: {brief_path}. "
        "Template created. Fill all required fields and retry."
      )
    return brief_path

  parsed = _parse_strategy_lock(brief_path.read_text(encoding="utf-8"))
  missing: list[str] = []
  for field in REQUIRED_BRIEF_FIELDS:
    v = parsed.get(field, "")
    if not _is_effective_value(v):
      missing.append(field)

  if missing:
    if _strict_mode():
      raise RuntimeError(
        f"Incomplete creative brief: {brief_path}. "
        f"Missing/empty fields: {', '.join(missing)}"
      )
    brief_path.write_text(creative_brief_template(), encoding="utf-8")

  return brief_path


def ensure_parallel_roles(project_dir: Path) -> Path:
  roles_path = parallel_roles_path(project_dir)
  roles_path.parent.mkdir(parents=True, exist_ok=True)
  if not roles_path.exists():
    roles_path.write_text(parallel_roles_template(), encoding="utf-8")
    if _strict_mode():
      raise RuntimeError(
        f"Missing parallel role output: {roles_path}. "
        "Template created. Run parallel role passes and fill all sections."
      )
    return roles_path

  raw = roles_path.read_text(encoding="utf-8")
  missing: list[str] = []
  for role in REQUIRED_ROLE_SECTIONS:
    marker = f"## {role}"
    if marker not in raw:
      missing.append(role)

  if missing:
    if _strict_mode():
      raise RuntimeError(
        f"Incomplete parallel role output: {roles_path}. "
        f"Missing sections: {', '.join(missing)}"
      )
    roles_path.write_text(parallel_roles_template(), encoding="utf-8")
  return roles_path


def ensure_agent_settings(project_dir: Path) -> Path:
  settings_path = agent_settings_path(project_dir)
  settings_path.parent.mkdir(parents=True, exist_ok=True)
  if not settings_path.exists():
    settings_path.write_text(agent_settings_template(), encoding="utf-8")
    if _strict_mode():
      raise RuntimeError(
        f"Missing agent settings: {settings_path}. "
        "Template created. Fill agent settings and retry."
      )
    return settings_path

  raw = settings_path.read_text(encoding="utf-8")
  missing_sections: list[str] = []
  for section in REQUIRED_AGENT_SETTING_SECTIONS.keys():
    if f"## {section}" not in raw:
      missing_sections.append(section)
  if missing_sections:
    if _strict_mode():
      raise RuntimeError(
        f"Incomplete agent settings: {settings_path}. "
        f"Missing sections: {', '.join(missing_sections)}"
      )
    settings_path.write_text(agent_settings_template(), encoding="utf-8")
    return settings_path

  missing_fields: list[str] = []
  for section, fields in REQUIRED_AGENT_SETTING_SECTIONS.items():
    block = _extract_section(raw, section)
    parsed = _parse_strategy_lock(block)
    for field in fields:
      v = parsed.get(_norm_key(field), "")
      if not _is_effective_value(v):
        missing_fields.append(f"{section}.{field}")

  if missing_fields:
    if _strict_mode():
      raise RuntimeError(
        f"Incomplete agent settings: {settings_path}. "
        f"Missing/empty fields: {', '.join(missing_fields)}"
      )
    settings_path.write_text(agent_settings_template(), encoding="utf-8")

  return settings_path


def infer_project_dir_from_spec(spec_path: Path) -> Path | None:
  # .../projects/<slug>/channels/instagram/cardnews/<spec>.{yaml,json}
  p = spec_path.resolve()
  if p.parent.name != "cardnews":
    return None
  if p.parent.parent.name != "instagram":
    return None
  if p.parent.parent.parent.name != "channels":
    return None
  return p.parent.parent.parent.parent
