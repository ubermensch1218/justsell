#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


@dataclass(frozen=True)
class SalesInfo:
  project_name: str
  one_liner: str
  contact_channel: str
  icp_role: str
  icp_stage: str
  current_alternatives: str
  pains: list[str]
  value_prop: str
  features: list[str]
  differentiators: list[str]
  proof: str
  primary_cta: str


@dataclass(frozen=True)
class ProductTone:
  name: str
  title_prefix: str
  attempt_label: str
  failure_label: str
  result_label: str
  limitation_line: str
  discussion_prompt: str
  disclosure_line: str
  fallback_cta: str


@dataclass(frozen=True)
class BrandTone:
  name: str
  opener_line: str
  evidence_tag: str
  caution_line: str
  ask_suffix: str
  fallback_cta: str


@dataclass(frozen=True)
class ChannelTone:
  name: str
  target_subreddit: str
  norm_hint: str
  safe_rule_line: str
  publish_rule_line: str


def _clean_placeholder(s: str) -> str:
  s = s.strip()
  return re.sub(r"\{[^}]+\}", "", s).strip()


def _find_section_lines(lines: list[str], heading_prefix: str) -> list[str]:
  in_block = False
  out: list[str] = []
  for line in lines:
    if re.match(rf"^\s*##\s*{re.escape(heading_prefix)}", line):
      in_block = True
      continue
    if in_block and line.startswith("## "):
      break
    if in_block:
      out.append(line)
  return out


def _extract_bullet_value(lines: list[str], prefix: str) -> str:
  for line in lines:
    match = re.match(rf"^\s*-\s*{re.escape(prefix)}\s*:\s*(.+)\s*$", line)
    if match:
      return _clean_placeholder(match.group(1))
  return ""


def _extract_numbered(lines: list[str], start_re: str) -> list[str]:
  out: list[str] = []
  in_block = False
  for line in lines:
    if re.match(start_re, line):
      in_block = True
      continue
    if in_block and line.startswith("## "):
      break
    if not in_block:
      continue
    match = re.match(r"^\s*\d+\)\s*(.+)\s*$", line)
    if match:
      value = _clean_placeholder(match.group(1))
      if value:
        out.append(value)
  return out


def _extract_simple_bullets(lines: list[str], heading: str) -> list[str]:
  out: list[str] = []
  in_block = False
  for line in lines:
    if line.strip() == f"## {heading}":
      in_block = True
      continue
    if in_block and line.startswith("## "):
      break
    if not in_block:
      continue
    match = re.match(r"^\s*-\s*(.+)\s*$", line)
    if match:
      value = _clean_placeholder(match.group(1))
      if value:
        out.append(value)
  return out


def parse_sales_info(path: Path) -> SalesInfo:
  raw = path.read_text(encoding="utf-8")
  lines = raw.splitlines()

  project_name = _extract_bullet_value(lines, "프로젝트명")
  one_liner = _extract_bullet_value(lines, "한 줄 소개")
  contact_channel = _extract_bullet_value(lines, "웹/데모/문의 채널")
  icp_role = _extract_bullet_value(lines, "산업/직무")
  icp_stage = _extract_bullet_value(lines, "규모/단계")
  current_alternatives = _extract_bullet_value(lines, "현재 쓰는 대안")
  pains = _extract_numbered(lines, r"^\s*##\s*고객 문제")
  features = _extract_numbered(lines, r"^\s*##\s*핵심 기능")
  differentiators = _extract_simple_bullets(lines, "차별점")

  value_prop = ""
  for line in _find_section_lines(lines, "제공 가치"):
    match = re.match(r"^\s*-\s*(.+)\s*$", line)
    if not match:
      continue
    candidate = _clean_placeholder(match.group(1))
    if candidate:
      value_prop = candidate
      break

  proof_lines = _extract_simple_bullets(lines, "근거/증거 (있을 때만)")
  proof = "; ".join(proof_lines[:3]).strip()

  primary_cta = ""
  in_cta = False
  for line in lines:
    if line.strip() == "## 대표 CTA (1개)":
      in_cta = True
      continue
    if in_cta and line.startswith("## "):
      break
    if not in_cta:
      continue
    match = re.match(r"^\s*-\s*(.+)\s*$", line)
    if match:
      primary_cta = _clean_placeholder(match.group(1))
      break

  return SalesInfo(
    project_name=project_name,
    one_liner=one_liner,
    contact_channel=contact_channel,
    icp_role=icp_role,
    icp_stage=icp_stage,
    current_alternatives=current_alternatives,
    pains=pains,
    value_prop=value_prop,
    features=features,
    differentiators=differentiators,
    proof=proof,
    primary_cta=primary_cta,
  )


def _extract_brand_voice_rules(brand_path: Path) -> list[str]:
  if not brand_path.exists():
    return []
  try:
    raw = brand_path.read_text(encoding="utf-8")
  except Exception:
    return []
  return _extract_simple_bullets(raw.splitlines(), "Voice")


def _first_nonempty(values: list[str]) -> str:
  for value in values:
    if value.strip():
      return value.strip()
  return ""


def _keyword_score(text: str, keywords: list[str]) -> int:
  score = 0
  for keyword in keywords:
    if keyword and keyword in text:
      score += 1
  return score


def _product_tone(si: SalesInfo) -> ProductTone:
  blob = " ".join(
    [
      si.project_name,
      si.one_liner,
      si.icp_role,
      si.icp_stage,
      si.current_alternatives,
      si.value_prop,
      " ".join(si.features),
      " ".join(si.differentiators),
      " ".join(si.pains),
    ]
  ).lower()

  dev_score = _keyword_score(
    blob,
    [
      "developer", "dev", "engineer", "api", "sdk", "cli", "github", "repo", "code",
      "typescript", "python", "infra", "k8s", "backend", "frontend", "database",
      "개발자", "엔지니어", "코드", "인프라", "백엔드", "프론트엔드", "데브옵스", "llm",
    ],
  )
  b2b_ops_score = _keyword_score(
    blob,
    [
      "b2b", "saas", "crm", "sales", "marketing", "workflow", "automation", "ops", "revops",
      "고객사", "영업", "마케팅", "운영", "업무", "프로세스", "자동화", "팀", "리드",
    ],
  )
  ecommerce_score = _keyword_score(
    blob,
    [
      "ecommerce", "shop", "store", "checkout", "conversion", "cart", "order", "roas",
      "쇼핑몰", "스토어", "장바구니", "구매", "전환", "주문", "배송", "매출", "재구매",
    ],
  )
  consumer_content_score = _keyword_score(
    blob,
    [
      "consumer", "creator", "content", "community", "newsletter", "audience", "subscriber",
      "콘텐츠", "크리에이터", "커뮤니티", "구독", "독자", "팔로워", "브랜드",
    ],
  )

  scores = {
    "devtool": dev_score,
    "b2b_ops": b2b_ops_score,
    "ecommerce": ecommerce_score,
    "consumer_content": consumer_content_score,
  }
  tone_name, max_score = max(scores.items(), key=lambda item: item[1])
  if max_score <= 0:
    tone_name = "generic"

  profiles: dict[str, ProductTone] = {
    "devtool": ProductTone(
      name="DEVTOOL",
      title_prefix="[Build Log]",
      attempt_label="초기 구현",
      failure_label="깨졌던 지점",
      result_label="성능/품질 지표",
      limitation_line="남은 이슈: edge case와 운영 환경 편차는 아직 완전히 해소되지 않았습니다.",
      discussion_prompt="비슷한 스택에서 더 깔끔한 패턴이 있으면 알려주세요.",
      disclosure_line="I build and maintain this tool.",
      fallback_cta="원하면 구현 디테일과 트레이드오프를 공유하겠습니다.",
    ),
    "b2b_ops": ProductTone(
      name="B2B_OPS",
      title_prefix="[운영 개선 로그]",
      attempt_label="기존 운영 방식",
      failure_label="팀 단위 병목",
      result_label="운영 지표",
      limitation_line="남은 이슈: 팀/조직마다 프로세스 편차가 커서 추가 튜닝이 필요합니다.",
      discussion_prompt="비슷한 규모 팀에서는 어떤 운영 지표를 핵심으로 보시나요?",
      disclosure_line="I build and operate this workflow.",
      fallback_cta="비슷한 운영 병목이 있으면 케이스를 알려주세요.",
    ),
    "ecommerce": ProductTone(
      name="ECOMMERCE",
      title_prefix="[전환 실험]",
      attempt_label="기존 퍼널 가정",
      failure_label="전환 누수 포인트",
      result_label="전환/매출 지표",
      limitation_line="남은 이슈: 시즌성과 트래픽 소스에 따라 결과 편차가 큽니다.",
      discussion_prompt="유사 퍼널에서 가장 효과 있었던 실험이 무엇인지 궁금합니다.",
      disclosure_line="I build and maintain this commerce workflow.",
      fallback_cta="원하면 퍼널 진단 기준을 공유하겠습니다.",
    ),
    "consumer_content": ProductTone(
      name="CONSUMER_CONTENT",
      title_prefix="[실험 기록]",
      attempt_label="초기 가정",
      failure_label="사용자 반응 한계",
      result_label="사용자 반응 지표",
      limitation_line="남은 이슈: 초기 반응은 확보했지만 장기 리텐션은 더 봐야 합니다.",
      discussion_prompt="초기 반응 검증에서 어떤 신호를 가장 신뢰하시나요?",
      disclosure_line="I build and maintain this product.",
      fallback_cta="원하면 실험 설계와 실패 케이스를 공유하겠습니다.",
    ),
    "generic": ProductTone(
      name="GENERIC",
      title_prefix="[실무 공유]",
      attempt_label="처음 가정",
      failure_label="막혔던 지점",
      result_label="관찰 지표",
      limitation_line="남은 이슈: 특정 환경에서는 추가 보완이 필요합니다.",
      discussion_prompt="비슷한 문제를 겪으셨다면 어떤 접근이 효과적이었는지 궁금합니다.",
      disclosure_line="I build and maintain this.",
      fallback_cta="비슷한 문제 있으면 상황 공유해 주세요.",
    ),
  }
  return profiles[tone_name]


def _brand_tone(project_dir: Path) -> BrandTone:
  voice_rules = _extract_brand_voice_rules(project_dir / "brand.md")
  blob = " ".join(voice_rules).lower()

  trust_score = _keyword_score(
    blob,
    [
      "신뢰", "정확", "근거", "검증", "데이터", "팩트", "전문", "차분", "명확",
      "trust", "accurate", "evidence", "data", "professional", "clear",
    ],
  )
  friendly_score = _keyword_score(
    blob,
    [
      "친근", "대화", "쉽게", "부드럽", "가볍", "따뜻", "공감",
      "friendly", "warm", "casual", "conversational",
    ],
  )
  bold_score = _keyword_score(
    blob,
    [
      "직설", "도전", "강하게", "선명", "과감", "날카롭",
      "bold", "sharp", "provocative", "direct",
    ],
  )

  scores = {"trusted": trust_score, "friendly": friendly_score, "bold": bold_score}
  tone_name, max_score = max(scores.items(), key=lambda item: item[1])
  if max_score <= 0:
    tone_name = "neutral"

  profiles: dict[str, BrandTone] = {
    "trusted": BrandTone(
      name="TRUSTED_EXPERT",
      opener_line="검증 가능한 범위에서 실무 경험만 공유합니다.",
      evidence_tag="근거 중심",
      caution_line="브랜드 원칙: 과장 대신 검증 가능한 사실만 사용합니다.",
      ask_suffix="가능하면 수치/재현 가능한 기준으로 피드백 부탁드립니다.",
      fallback_cta="원하면 검증 기준 문서를 공유하겠습니다.",
    ),
    "friendly": BrandTone(
      name="FRIENDLY_GUIDE",
      opener_line="현업 시행착오를 이해하기 쉽게 정리해봅니다.",
      evidence_tag="공개 가능한 범위",
      caution_line="브랜드 원칙: 단정 표현보다 맥락 설명을 우선합니다.",
      ask_suffix="비슷한 경험이 있으면 편하게 사례를 남겨주세요.",
      fallback_cta="원하면 템플릿 형태로 정리해 공유하겠습니다.",
    ),
    "bold": BrandTone(
      name="BOLD_CHALLENGER",
      opener_line="기존 관행을 다시 검토해야 한다는 전제로 공유합니다.",
      evidence_tag="실험 결과",
      caution_line="브랜드 원칙: 강한 주장이라도 검증 가능한 근거를 같이 제시합니다.",
      ask_suffix="반례가 있다면 구체적인 케이스로 반박 부탁드립니다.",
      fallback_cta="원하면 실험 설계와 실패 로그까지 공유하겠습니다.",
    ),
    "neutral": BrandTone(
      name="NEUTRAL",
      opener_line="운영 중 관찰한 내용을 기준으로 공유합니다.",
      evidence_tag="공개 범위",
      caution_line="브랜드 원칙: 재현 가능한 정보만 남깁니다.",
      ask_suffix="유사 상황의 피드백이 있으면 공유 부탁드립니다.",
      fallback_cta="원하면 상세 맥락을 공유하겠습니다.",
    ),
  }
  return profiles[tone_name]


def _normalize_subreddit(raw: str) -> str:
  value = raw.strip()
  if not value:
    return ""
  if value.lower().startswith("r/"):
    value = value[2:]
  value = value.strip().strip("/")
  return value.lower()


def _channel_tone(subreddit: str) -> ChannelTone:
  normalized = _normalize_subreddit(subreddit)
  if normalized in {"programming", "webdev", "typescript", "python", "reactjs"}:
    return ChannelTone(
      name="REDDIT_DEV_COMMUNITY",
      target_subreddit=f"r/{normalized}",
      norm_hint="개발자 커뮤니티 톤: 구현 맥락/트레이드오프/실패 원인 중심으로 씁니다.",
      safe_rule_line="채널 원칙: 링크 없이 재현 가능한 맥락과 실패 로그를 먼저 공유합니다.",
      publish_rule_line="채널 원칙: 링크는 1개 이하, 오픈소스/데모/가이드 맥락으로만 붙입니다.",
    )
  if normalized in {"saas", "startups", "entrepreneur", "marketing", "smallbusiness"}:
    return ChannelTone(
      name="REDDIT_BUSINESS_COMMUNITY",
      target_subreddit=f"r/{normalized}",
      norm_hint="비즈니스 커뮤니티 톤: 숫자 과장 없이 운영 맥락/실험 과정 중심으로 씁니다.",
      safe_rule_line="채널 원칙: 링크 없이 문제 정의와 실행 교훈부터 공유합니다.",
      publish_rule_line="채널 원칙: 링크는 1개 이하, self-promo 규정과 flair 요구사항을 먼저 확인합니다.",
    )
  return ChannelTone(
    name="REDDIT_COMMUNITY",
    target_subreddit=f"r/{normalized}" if normalized else "generic",
    norm_hint="레딧 커뮤니티 톤: 질문/교훈/토론 유도 중심으로 씁니다.",
    safe_rule_line="채널 원칙: 링크 없이 맥락/실패/교훈을 먼저 공유합니다.",
    publish_rule_line="채널 원칙: 링크는 1개 이하, 자기홍보 규정 위반 여부를 먼저 확인합니다.",
  )


def _bernays_fields(si: SalesInfo) -> dict[str, str]:
  return {
    "pain": si.pains[0] if si.pains else "",
    "old_belief": _first_nonempty([si.current_alternatives, "기존 방식"]),
    "hidden_cost": _first_nonempty([si.pains[1] if len(si.pains) > 1 else "", "숨은 비용"]),
    "new_standard": _first_nonempty([si.value_prop, si.one_liner, "새 기준"]),
    "proof": si.proof,
    "cta": _first_nonempty([si.primary_cta, si.contact_channel]),
  }


def render_reddit(si: SalesInfo, *, style: str, project_dir: Path, subreddit: str) -> str:
  product_tone = _product_tone(si)
  brand_tone = _brand_tone(project_dir)
  channel_tone = _channel_tone(subreddit)
  bernays = _bernays_fields(si)

  core_problem = _first_nonempty([si.pains[0] if si.pains else "", bernays["pain"], "반복되는 운영 문제"])
  failed_attempt = _first_nonempty([si.current_alternatives, bernays["old_belief"], "기존 방식"])
  hidden_cost = _first_nonempty([bernays["hidden_cost"], si.pains[1] if len(si.pains) > 1 else "", "숨은 비용"])
  new_standard = _first_nonempty([si.value_prop, bernays["new_standard"], si.one_liner])
  implementation = _first_nonempty([si.features[0] if si.features else "", si.differentiators[0] if si.differentiators else ""])
  proof = _first_nonempty([si.proof, ""])
  cta = _first_nonempty([si.primary_cta, si.contact_channel, brand_tone.fallback_cta, product_tone.fallback_cta])

  link_line = ""
  if re.match(r"^https?://", si.contact_channel.strip()):
    link_line = f"- Optional link: {si.contact_channel.strip()}"

  target_subreddit_line = f"- Target subreddit: {channel_tone.target_subreddit}" if channel_tone.target_subreddit else ""

  if style == "plain":
    title = _first_nonempty([si.one_liner, si.project_name, "실무 경험 공유"])
    body = [
      f"Title: [{channel_tone.target_subreddit}] {title}" if channel_tone.target_subreddit != "generic" else f"Title: {title}",
      "",
      "[Safe draft]",
      f"- Tone tripod: product={product_tone.name} | brand={brand_tone.name} | channel={channel_tone.name}",
      target_subreddit_line,
      channel_tone.norm_hint,
      channel_tone.safe_rule_line,
      brand_tone.opener_line,
      f"문제 맥락: {core_problem}",
      f"시도한 방식: {failed_attempt}",
      f"현재 관찰: {hidden_cost}",
      f"지금 기준: {new_standard}",
    ]
    if proof:
      body.append(f"관찰 근거({brand_tone.evidence_tag}): {proof}")
    body += [
      "",
      product_tone.limitation_line,
      brand_tone.caution_line,
      f"의견 요청: {brand_tone.ask_suffix}",
      "",
      "[Publish-ready optional add-on]",
      channel_tone.publish_rule_line,
      f"- Disclosure: {product_tone.disclosure_line}",
    ]
    if link_line:
      body.append(link_line)
    body.append(f"- Optional CTA: {cta}")
    return "\n".join([line for line in body if line]).strip() + "\n"

  if style == "comeback":
    title = _first_nonempty([si.one_liner, si.project_name, "재정비하면서 배운 점 공유"])
    body = [
      f"Title: {product_tone.title_prefix} {title} ({channel_tone.target_subreddit})" if channel_tone.target_subreddit != "generic" else f"Title: {product_tone.title_prefix} {title}",
      "",
      "[Safe draft]",
      f"- Tone tripod: product={product_tone.name} | brand={brand_tone.name} | channel={channel_tone.name}",
      target_subreddit_line,
      channel_tone.norm_hint,
      channel_tone.safe_rule_line,
      brand_tone.opener_line,
      f"최근 다시 손본 주제: {core_problem}",
      "",
      f"{product_tone.attempt_label}: `{failed_attempt}`",
      f"{product_tone.failure_label}: {hidden_cost}",
      f"이번에는 기준을 `{new_standard}`로 바꿨고, 첫 단계는 `{implementation}`부터 적용했습니다.",
    ]
    if proof:
      body.append(f"{product_tone.result_label}({brand_tone.evidence_tag}): {proof}")
    body += [
      "",
      product_tone.limitation_line,
      brand_tone.caution_line,
      f"{product_tone.discussion_prompt} {brand_tone.ask_suffix}".strip(),
      "",
      "[Publish-ready optional add-on]",
      channel_tone.publish_rule_line,
      f"- Disclosure: {product_tone.disclosure_line}",
    ]
    if link_line:
      body.append(link_line)
    body.append(f"- Optional CTA: {cta}")
    return "\n".join([line for line in body if line]).strip() + "\n"

  title = f"{product_tone.title_prefix} {_first_nonempty([core_problem, si.one_liner, si.project_name, '실무 이슈'])}를 이렇게 정리했습니다"
  body = [
    f"Title: {title} ({channel_tone.target_subreddit})" if channel_tone.target_subreddit != "generic" else f"Title: {title}",
    "",
    "[Safe draft]",
    f"- Tone tripod: product={product_tone.name} | brand={brand_tone.name} | channel={channel_tone.name}",
    target_subreddit_line,
    channel_tone.norm_hint,
    channel_tone.safe_rule_line,
    brand_tone.opener_line,
    f"문제: {core_problem}",
    f"{product_tone.attempt_label}: `{failed_attempt}`",
    f"{product_tone.failure_label}: {hidden_cost}",
    "",
    "이번에 바꾼 기준:",
    f"- {new_standard}",
  ]
  if implementation:
    body.append(f"- 구현 포인트: {implementation}")
  if proof:
    body.append(f"- {product_tone.result_label}({brand_tone.evidence_tag}): {proof}")
  body += [
    "",
    product_tone.limitation_line,
    brand_tone.caution_line,
    f"{product_tone.discussion_prompt} {brand_tone.ask_suffix}".strip(),
    "",
    "[Publish-ready optional add-on]",
    channel_tone.publish_rule_line,
    f"- Disclosure: {product_tone.disclosure_line}",
  ]
  if link_line:
    body.append(link_line)
  body.append(f"- Optional CTA: {cta}")
  return "\n".join([line for line in body if line]).strip() + "\n"


def write_reddit_draft(project_dir: Path, content: str) -> Path:
  out_dir = project_dir / "channels" / "reddit" / "drafts"
  out_dir.mkdir(parents=True, exist_ok=True)
  out_path = out_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
  out_path.write_text(content, encoding="utf-8")
  return out_path


def main() -> int:
  parser = argparse.ArgumentParser(description="Generate Reddit drafts from projects/<project>/SALES_INFO.md + brand.md")
  parser.add_argument("--project", required=True, type=Path, help="Path like projects/<project-slug>")
  parser.add_argument("--style", default="bernays", choices=["bernays", "plain", "comeback"])
  parser.add_argument("--subreddit", default="", help="Optional target subreddit, example: startups or r/webdev")
  args = parser.parse_args()

  sales_path = args.project / "SALES_INFO.md"
  if not sales_path.exists():
    raise FileNotFoundError(f"Missing: {sales_path} (expected SALES_INFO.md)")

  sales_info = parse_sales_info(sales_path)
  content = render_reddit(
    sales_info,
    style=args.style,
    project_dir=args.project,
    subreddit=args.subreddit,
  )
  out = write_reddit_draft(args.project, content)
  print(str(out))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
