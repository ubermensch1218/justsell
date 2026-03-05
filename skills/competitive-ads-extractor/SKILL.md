---
name: competitive-ads-extractor
description: Production local-first swipe-file extraction workflow for competitor ads
---

# competitive-ads-extractor

[COMPETITIVE ADS MODE ACTIVATED]

## Operating Goal
Build a reusable local swipe file and extract repeatable hook/offer/CTA patterns.

## Execution Rules
1) Default to manual capture; no scraping-first workflow.
2) Keep all assets in local project storage.
3) Convert findings into reusable copy angles for downstream generation.

## Input
- Competitor list (name + product URL)
- 5-20 ad references (link + screenshot)

## Output
- `~/.claude/.js/projects/<project>/research/ads/<competitor>/<YYYY-MM-DD>/ad-01.md`
- Screenshot assets in the same folder (`*.png`)

## Capture Template
- Platform
- Link
- Creative type
- Hook
- Offer
- Proof
- CTA
- Targeting guess
- Angle tags

## Extraction Deliverable
- Repeated hook patterns Top 5
- Offer structures Top 3
- CTA lines Top 10
- Ban-list phrases that do not fit brand voice
