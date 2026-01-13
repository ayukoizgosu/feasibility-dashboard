
# 0000 Use MADR for architectural decisions

Date: 2026-01-12

## Status
Accepted

## Context
We want a lightweight, consistent format for recording architectural decisions so that humans and AI agents stop guessing and the project stays coherent over time.

## Decision
Use Markdown Architectural Decision Records (MADR) for ADRs in `docs/decisions/`.

## Consequences
- Decisions become easy to review in PRs.
- Agents must read recent ADRs before proposing changes.

## Alternatives considered
- No ADRs (too much drift)
- Heavyweight design docs (too slow for small-team)

## Links
- docs/decisions/TEMPLATE.md
