# Topic Discovery Skill Design

Status: Draft for user review. A provider-independent standard-library implementation exists (`skills/topic-discovery/`); no provider API calls or installations have been made.
Decision record: [Phase_0_design.md](../Phase_0_design.md)
Shared Skill rules: [SKILL_SPECIFICATION.md](SKILL_SPECIFICATION.md)
Data contract baseline: [DATA_SCHEMA.md](DATA_SCHEMA.md)

## Purpose

Generate a human-reviewable list of Korean blog topic ideas. Each candidate includes a recommended title, one primary keyword, three to five related keywords, a search-intent description, a short rationale, a freshness label, and at least one relevant web source.

This Skill suggests topics; it does not select or publish them. A person approves a candidate before the workflow creates a content record.

## Scope and Boundaries

- Content types are `experience`, `finance`, `review`, `guide`, and `compare`.
- A request may select one or more active content types. If none are selected, use all active types.
- When multiple types are requested, include at least one candidate per type when the candidate count permits; rank remaining candidates by editorial fit.
- Return 5–10 candidates. The draft default is 5, subject to user review.
- Prefer evergreen candidates while allowing useful seasonal or timely ideas. Label each candidate `evergreen`, `seasonal`, or `timely`.
- Use web search for topical context and source links. Do not state search volume, competition, trend rank, or demand as measured facts.
- Search references are discovery signals, not fact-check results. Fact-checking and full source research happen in later Skills.
- Each candidate must have at least one relevant source URL. If fewer than five candidates meet this condition, return a structured `INSUFFICIENT_EVIDENCE` error rather than filling the list with unsupported ideas or fabricated citations.
- Provide no numeric quality, search-volume, or competition score. Candidate array order is the recommendation order; `rationale` explains the ordering.
- The caller may pass an optional `excluded_topics` list. Avoid close matches only against entries in that list; do not assume hidden history.
- Do not invent personal experience. For `experience` topics, describe an idea as conditional on the writer having relevant real experience.
- Finance and policy ideas should prefer official sources. A discovery link does not establish that a claim has been verified.

## Inputs (Draft)

The Skill uses the common versioned JSON request envelope. The workflow creates the Discovery Runs row and passes its `discovery_run_id` in `refs`; that ID keys execution logs and duplicate-run checks. Proposed `input` fields:

| Field | Requirement | Purpose |
| --- | --- | --- |
| `editorial_context` | Required | General blog purpose and audience context; must not contain identifying or sensitive family information |
| `active_content_types` | Required | Enabled content types from configuration |
| `requested_content_types` | Optional | One or more active types; omitted means all active types |
| `candidate_count` | Optional | Integer from 5 through 10; draft default is 5 |
| `discovery_criteria` | Optional | Topic focus, audience needs, exclusions, or other editorial constraints |
| `excluded_topics` | Optional | Existing topic names or short descriptions to avoid repeating |
| `locale` | Configuration default | `ko-KR`; target Korean-language readers and search context |

The provider, model ID, search API, and search request budget are configuration concerns, not user-authored prompt fields. Provider selection and exact request limits remain open. The $5 monthly allowance for this Skill was estimated assuming at most two Tavily Advanced requests per run; that assumption is not a finalized integration contract.

## Candidate Output (Draft)

Each candidate contains:

| Field | Meaning |
| --- | --- |
| `content_type` | One selected active content type |
| `candidate_title` | Suggested Korean blog title; must not imply unprovided personal experience |
| `primary_keyword` | One main keyword phrase |
| `related_keywords` | Three to five related keyword phrases |
| `search_intent` | Short natural-language description of the likely reader need; not a measured metric |
| `rationale` | Editorial fit, reader usefulness, and why the source context supports exploring the topic |
| `freshness` | `evergreen`, `seasonal`, or `timely` |
| `requires_firsthand_experience` | Whether the idea depends on the writer's actual experience |
| `sources` | One or more source references with title, URL, publisher when available, and access time |

The response array order is the recommendation order. The Script/Workflow layer assigns `topic_id` and `recommendation_order`, then persists candidate, keyword, and source metadata in the Topics, Topic Keywords, and Topic Sources tabs; the model must not invent IDs. Source snippets and full page text are not stored in Sheets as part of this Skill.

The draft success output is `{ "candidates": [...], "warnings": [...] }`. If the caller requests more than five candidates but only five to nine meet the evidence requirement, return the supported list and a `REQUESTED_COUNT_NOT_MET` warning. Fewer than five candidates remains an error.

## Privacy and Evidence Rules

- Never include names, locations, faces, or other identifying family information in search queries.
- If supplied context contains identifying or sensitive information, do not forward it to a search provider; return `INVALID_INPUT` so the context can be sanitized.
- Do not write first-person claims or assert that the writer experienced an event.
- Do not treat search-result count or ranking as search demand.
- Keep source links and their access time so a person can inspect the basis of a suggestion.

## Error Behavior

Error codes come from the canonical table in section 9.2 of the decision record.

- Invalid content types, candidate counts outside 5–10, missing required editorial context, or identifying information in the input return `INVALID_INPUT`.
- Fewer than five source-supported candidates return `INSUFFICIENT_EVIDENCE`; no success-shaped list below the agreed minimum. If the requested target is above five but fewer than requested are supported, return the supported 5–9 candidates with a `REQUESTED_COUNT_NOT_MET` warning. That warning is part of a successful response, not an error code.
- Provider outages, rate limits, and malformed provider responses use the shared structured error contract and n8n retry policy.
- `INSUFFICIENT_EVIDENCE` and `INVALID_INPUT` are content/review issues, not a technical `FAILED` state. The workflow moves the discovery run to `NEEDS_REVISION`; a person revises the criteria or input and resumes, or cancels.

## Quality Checks and Acceptance Criteria

- Successful output contains 5–10 candidates; it meets the requested/default target when evidence permits.
- Each candidate has exactly one primary keyword, three to five related keywords, a content type, intent, rationale, freshness label, and at least one usable source URL.
- Requested content types are honored; when multiple types are requested, coverage is balanced when the requested count permits.
- Results are Korean-language ideas suited to the selected Korean audience and content types.
- No invented search-volume, competition, or trend-ranking numbers.
- No fabricated or missing source URLs; an insufficient evidence set returns an error.
- No identifying personal data is sent to search, and no lived experience is invented.
- The result remains reviewable by a human and does not create a `content_id` or publish content.

## Open Design Items

- Choose the model and search provider after Korean quality, availability, price, and terms checks on the designated personal PC. Confirm that the search provider's terms allow storing source titles and URLs in Topic Sources; Gemini Google Search grounding has restrictions that need review.
- Validate the search-request budget; the preliminary cost estimate assumes at most two advanced searches per run.
- Define provider-independent source relevance and credibility checks, especially the official-source requirement for finance and policy topics.
- Confirm the draft default candidate count of five.
- Confirm the partial-list rule: 5–9 supported candidates returned with `REQUESTED_COUNT_NOT_MET` when more were requested.
- Finalize field types, nullable rules, exact intent labels, and JSON Schema.
- Confirm how selected/published topics are assembled into `excluded_topics`, and whether candidates rejected in an earlier run are added to it on re-discovery.
- Decide whether Discovery Runs should store the request parameters and warnings.
