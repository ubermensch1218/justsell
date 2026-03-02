---
name: instagram-remotion-video
description: Generate Remotion promo video spec and render MP4 from projects/<project>/SALES_INFO.md
---

# instagram-remotion-video

`SALES_INFO.md`를 기준으로 Remotion 영상 스펙(JSON)을 만들고 MP4를 렌더합니다.

## Input
- `projects/<project>/SALES_INFO.md`

## Output
- spec: `projects/<project>/channels/instagram/remotion/<yyyymmdd-hhmm>.json`
- video: `projects/<project>/channels/instagram/videos/<spec-stem>.mp4`

## Commands
```bash
python3 scripts/generate_remotion_spec.py \
  --project projects/<project> \
  --style bernays \
  --video-seconds 22 \
  --video-format auto \
  --channel-profile instagram-reel \
  --device-profile mobile

python3 scripts/render_remotion_video.py \
  --spec projects/<project>/channels/instagram/remotion/<spec>.json \
  --out projects/<project>/channels/instagram/videos
```

## Profiles
- `--video-format`: `auto | portrait | square | landscape`
- `--channel-profile`: `instagram-reel | instagram-feed | threads-post | linkedin-feed | youtube-short | youtube-landscape`
- `--device-profile`: `mobile | desktop`

## Notes
- Remotion runtime 설치 경로: `~/.claude/.js/remotion-runtime/` (`JUSTSELL_HOME` 우선)
- 첫 렌더 시 npm dependencies 설치가 자동으로 수행될 수 있습니다.
