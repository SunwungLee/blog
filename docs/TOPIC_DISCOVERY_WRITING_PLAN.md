# Topic Discovery Skill Writing Plan

Status: Draft. Standard-library implementation and unit tests now exist (`skills/topic-discovery/`, `tests/unit/test_topic_discovery.py`); provider selection and real-provider quality tests remain open.
Design: [TOPIC_DISCOVERY_DESIGN.md](TOPIC_DISCOVERY_DESIGN.md)
Implementation gate: work on application code and provider calls waits until the user's designated personal-PC environment is available and the user approves implementation.

## Sequence

1. Review and approve the Skill design, especially the candidate contract and evidence error behavior.
2. Before implementation, recheck provider availability, prices, terms (including whether source links may be stored), and the per-run search budget. Narrow the model and search-provider candidates to a shortlist; do not make the final selection yet.
3. Define the formal JSON Schema and the boundary between the AI Skill and deterministic Script/Workflow responsibilities.
4. Write failing tests first using fixed editorial briefs and mocked search results; tests must not require network access or credentials.
5. Implement the smallest provider-independent Skill behavior needed to pass the contract.
6. Add adapter tests for provider errors, rate limits, malformed responses, missing citations, and insufficient search evidence.
7. Compare the shortlisted providers' outputs on representative Korean inputs for all five content types, then select the model and search provider with the user. Keep numeric ranking and search-volume claims out of the candidate result.
8. Verify privacy rules, human approval handoff, stable `topic_id` assignment outside the model, logs/cost estimates, and documentation.
9. Complete independent review and verification before n8n integration.

## Test Fixtures and Scenarios

- One content type, multiple selected content types, and omitted type selection using all active types.
- Candidate counts 5 and 10; counts below 5 or above 10 return `INVALID_INPUT`.
- A request for 10 with 5–9 sourced results returns those results with a `REQUESTED_COUNT_NOT_MET` warning; fewer than 5 returns `INSUFFICIENT_EVIDENCE`.
- Optional excluded-topic lists and near-duplicate candidates.
- Evergreen, seasonal, and timely candidates with source access timestamps.
- Finance/policy candidates with official sources preferred.
- Experience candidates that do not claim unprovided first-hand experience.
- Search API timeout, rate limit, malformed JSON, unusable URLs, and retry exhaustion.
- Privacy guard returns `INVALID_INPUT` and prevents identifying family information from reaching search queries.

## Exit Criteria

- User approves the design and exact I/O contract.
- Contract tests cover success, validation, privacy, evidence insufficiency, and provider failures.
- Korean quality comparison is reviewed, and the provider and model are selected only after it.
- No real API key is required for unit tests; secrets are never stored in fixtures or source.
- Documentation and data schema agree with the implemented behavior.
