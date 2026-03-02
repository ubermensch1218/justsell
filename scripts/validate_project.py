#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class ValidationResult:
  ok: bool
  missing: list[str]


def validate_project(project_dir: Path) -> ValidationResult:
  required = [
    project_dir / "SalesInfo.md",
    project_dir / "brand.md",
    project_dir / "product.md",
    project_dir / "ConversationPolicy.md",
  ]
  missing = [str(p) for p in required if not p.exists()]
  return ValidationResult(ok=len(missing) == 0, missing=missing)


def main() -> int:
  parser = argparse.ArgumentParser(description="Validate JustSell project folder.")
  parser.add_argument("project_dir", type=Path)
  args = parser.parse_args()

  result = validate_project(args.project_dir)
  if result.ok:
    print("OK")
    return 0

  print("Missing required files:")
  for p in result.missing:
    print(f"- {p}")
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
