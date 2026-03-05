from __future__ import annotations

from urllib.parse import urlparse
import re


HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def _is_hex_color(value: str) -> bool:
  return bool(HEX_COLOR_RE.match(value))


def _is_http_url(value: str) -> bool:
  try:
    p = urlparse(value)
    return p.scheme in {"http", "https"} and bool(p.netloc)
  except Exception:
    return False


def validate_setup_form(data: dict[str, object]) -> dict[str, str]:
  errors: dict[str, str] = {}

  def get_str(key: str) -> str:
    return str(data.get(key, "") or "").strip()

  public_base_url = get_str("public_base_url")
  if public_base_url and not _is_http_url(public_base_url):
    errors["public_base_url"] = "Use a full URL starting with http:// or https://"

  bg_kind = get_str("cardnews_bg_kind")
  if bg_kind and bg_kind not in {"solid", "gradient"}:
    errors["cardnews_bg_kind"] = "Choose solid or gradient."

  color_fields = [
    "cardnews_accent_primary",
    "cardnews_accent_secondary",
    "cardnews_cover_fill",
    "cardnews_panel_fill",
    "cardnews_bg_solid",
    "cardnews_bg_from",
    "cardnews_bg_to",
  ]
  for key in color_fields:
    val = get_str(key)
    if val and not _is_hex_color(val):
      errors[key] = "Use HEX color like #RRGGBB."

  if bg_kind == "gradient":
    if not get_str("cardnews_bg_from"):
      errors["cardnews_bg_from"] = "Required when bg_kind is gradient."
    if not get_str("cardnews_bg_to"):
      errors["cardnews_bg_to"] = "Required when bg_kind is gradient."

  return errors

