---
name: research
description: >
  Research a technical topic or a product landscape and write a sourced report to research/.
  Triggers: "research", "/research", "исследуй", "ресерч"
---

Research the topic from the user's request and leave a report they can act on.

## Output

`<repo root>/research/<topic-slug>.md`. Write findings into the file as you go, so an interrupted run still leaves something usable. The report opens with an executive summary and a recommendation, lists disputed or unverified claims separately, and ends with annotated sources.

## Scope

- Ask at most three clarifying questions, and only if the topic is genuinely ambiguous.
- Split the topic into 3–5 subtopics and research them in parallel sub-agents when available.
- Product landscape: players, features, pricing, weaknesses, user sentiment. Technical topic: how it works, alternatives, pitfalls, recommended practice.

## Quality bar

- Prefer primary sources (official docs, changelogs, source code); use HN, Reddit and GitHub issues for field experience.
- Confirm key claims in 2–3 independent sources and mark each finding high, medium or low confidence.
- Always search for the case against: problems, criticism, reasons not to use it.
- Stop when every subtopic is covered and new searches stop turning up new information.

Reply with the file path, 3–5 key findings and what remains unverified, in the user's language.
