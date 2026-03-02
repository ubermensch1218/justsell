from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class MediaAsset:
  path: str
  mime_type: str


@dataclass(frozen=True)
class PublishResult:
  remote_id: str
  url: str | None = None


class ChannelPublisherPort(Protocol):
  def publish_text(self, *, text: str) -> PublishResult: ...

  def publish_images(self, *, caption: str, images: Sequence[MediaAsset]) -> PublishResult: ...


class ChannelInboxPort(Protocol):
  def list_unreplied(self, *, limit: int = 20) -> list[dict]: ...

  def reply(self, *, thread_id: str, text: str) -> PublishResult: ...

