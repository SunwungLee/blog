# AI Skill Specification

Status: Shared PHASE 0 responsibility and I/O outline. `topic-discovery` design is in draft at [TOPIC_DISCOVERY_DESIGN.md](TOPIC_DISCOVERY_DESIGN.md); provider selection and implementation remain open.
Decision record: [Phase_0_design.md](../Phase_0_design.md)

## Common Contract

Every Skill is an independent module called by n8n with the versioned JSON envelope in [DATA_SCHEMA.md](DATA_SCHEMA.md). Inputs include only the relevant IDs, settings, references, and necessary excerpts. Outputs are structured JSON; long-form artifacts are saved to Drive and returned by reference.

Each Skill:

- owns one clear semantic responsibility and does not orchestrate the full workflow;
- uses model roles from configuration, not hard-coded provider/model IDs;
- identifies sources, uncertainty, warnings, and missing evidence where relevant;
- does not invent the user's lived experience;
- does not change facts or core meaning after final-article approval;
- returns an explicit structured error rather than silently substituting missing data.

## Skill Responsibilities and I/O Outline

| Skill | Input | Output |
| --- | --- | --- |
| `topic-discovery` | Editorial context, selected content types, criteria, optional exclusions | 5–10 ranked Korean candidates with primary/related keywords, search intent, rationale, freshness, and source links |
| `source-research` | Approved topic, research questions, source criteria | Source metadata, evidence summaries, Drive references |
| `content-planning` | Topic and research references, content type | Direction, outline, key message |
| `interview-questioning` | Approved plan, question templates, existing answers | Missing/conflicting answers and 1–3 additional questions when needed |
| `master-article` | Approved plan, evidence, interview answers | Master Article reference, source references, review warnings |
| `fact-checking` | Article version and evidence | Claim-level support results, citations, unresolved claims |
| `seo-optimization` | Article, keywords, search intent | SEO checks and the pre-approval optimized article |
| `image-preparation` | Approved plan/article reference and image constraints | Image plan, asset references, usage-rights metadata |
| `platform-adaptation` | Approved article version and target platform | Platform-specific file reference and adaptation summary |
| `performance-analysis` | Publishing references and collected metrics | Performance summary and improvement suggestions |

## Content-Type Variation

The five active content types are `experience`, `finance`, `review`, `guide`, and `compare`. Each may vary its questions, research method, structure, fact-check rules, SEO strategy, and writing prompts. Define those variants within the corresponding Skill design; do not make five separate copies of the entire system.

The `topic-discovery` draft contract uses one or more requested active types, or all active types when the request omits them. It prioritizes evergreen ideas while labeling useful seasonal/timely candidates. Search links support topic exploration only; they do not prove search volume or fact-check candidate claims. See [TOPIC_DISCOVERY_DESIGN.md](TOPIC_DISCOVERY_DESIGN.md).

## Content Rules

These rules from the decision record apply to every Skill that produces or checks content.

- Sources: prefer official and original sources, record the publication date and the date checked, and use secondary sources only to add context. Finance and policy information relies on official material.
- Privacy: exclude identifying information about the family (real names, faces, locations) by default. Use it only where explicitly allowed for that post, and then minimally.
- Experience: write from the user's real experience. Do not invent it.
- Finance: no buy recommendations and no unsupported return forecasts. Finance posts carry a notice that the content is not investment advice, plus the reference date of the information.
- Sponsorship, affiliate, or advertising content is disclosed.
- Images are used only when usage rights are confirmed.
- The same text is not posted unchanged to both Naver Blog and Google Blogspot.

Interview question rules (`interview-questioning`):

- The workflow does not advance while a required question is unanswered; optional questions may be skipped.
- A question already answered is not asked again.
- The Skill checks for missing and conflicting answers and asks only 1–3 follow-up questions for the gaps.
- "모름" (don't know) is recorded as the answer, counts as answered even for a required question, is not asked again, and is not filled in by AI.

The detailed wording of privacy, advertising, and finance notices and the duplicate-content approach are still open in the decision record.

## Approval and Change Boundaries

- Topic discovery produces candidates; a person selects the topic.
- Content planning runs in the `PLANNING` state and waits for plan approval before interviewing. Target platforms are selected at plan approval.
- Fact-checking is automatic. A failed check sends the article back to drafting within the quality-rerun limit; beyond it, or when evidence is insufficient, the content moves to `NEEDS_REVISION`. Claim-level results are stored in the Fact Checks tab.
- The final article is fact-checked and SEO-processed before article approval.
- Image preparation and platform adaptation follow final-article approval.
- Platform adaptation can change expression, structure, and format, but not facts or core content. If facts or core content must change, the final-article approval is obtained again.
- The platform outputs require human approval per platform. A publish rejection is routed by reason: format/structure issues go back to platform adaptation for that platform, image issues to image preparation, and factual or core-content issues to drafting and final-article approval again. After platform approval, create or update the Blogspot draft if applicable. Public publishing remains manual.
- Each approval stage allows an initial review plus up to three re-reviews. A fourth rejection moves the item to `NEEDS_REVISION`; if resumed, that stage's attempt count restarts. A person may cancel only from `WAITING_FOR_*` or `NEEDS_REVISION`.
- `ANALYZING` returns to `PUBLISHED` when the analysis run completes.

## Quality and Retry

JSON repair is limited to two retries after the initial response. A quality failure reruns only the responsible Skill, at most twice after the initial output. On exhaustion, return a structured error and move to human review (`NEEDS_REVISION`). API transient and rate-limit retry handling is owned by n8n and follows [Phase_0_design.md](../Phase_0_design.md).

## Implementation Notes (current code)

- Model roles: each Skill reads its role from `config/model-config.json` (`tasks.<task>.model`, values `lightweight`/`high_quality`); no model IDs in code.
- Adapter error contract: injected `llm`/`search` raise exceptions; `common/errors.py` maps HTTP 429 → `API_RATE_LIMITED`, 401/403 → `AUTH_OR_PERMISSION`, 5xx/timeout/connection → `API_TRANSIENT`. Messages never include secrets.
- Before any model call the envelope validates `refs` formats (`topic_id`, `content_id`, non-empty `discovery_run_id`, `drive_file_ids` string list); violations return `INVALID_INPUT`.
- Successful responses with an inline `artifact` carry `artifact.checksum` (`sha256:…`) for Drive save verification.
- Shared content rules (`common/rules.py`): finance banned phrases, exact finance/sponsor notices, information-date line, AI cliché and PII checks with per-post `blocked_terms`.
- Fact-check `passed=false` is a successful response; n8n records it as `QUALITY_BELOW_THRESHOLD` and returns to drafting. SEO sets `requires_refactcheck=true` when the body changes, and fact-checking must run again before article approval.
- Scripts run through the same envelope via `run_script.py` (`data-validator`, `html-converter`, `seo-checker`, `image-processor`, and the workflow-only `id-allocator`). Both CLIs accept `--hash-only` to return the `input_hash` without running the module; see [ORCHESTRATION_FOUNDATION.md](ORCHESTRATION_FOUNDATION.md).
- Usage reporting: an `llm` adapter may return `{"text": ..., "usage": {"input_tokens", "output_tokens"}}` instead of plain text. Every response envelope carries `usage` with `llm_calls`, `search_calls`, `input_tokens`/`output_tokens` (`null` when the adapter did not report them), and `input_hash`. n8n writes these to Execution Logs (`token_usage`, `input_hash`) and computes `estimated_cost` from its price table; Skills never hold prices.
- Platform adaptation is script-first for Blogspot (no AI when the SEO article passes the content rules and does not overlap the other platform's output) and AI for Naver. `adaptation_method` reports which path ran.
- Performance analysis accepts the content's Publishing rows (`publishing[]`) to drop pre-publication measurements and report `days_since_publish`.
- `topic-discovery` accepts only `locale = ko-KR`; other values return `INVALID_INPUT`.

## Deferred

For each Skill, define exact JSON fields and types, required/optional inputs, validation, model role, prompt and quality rules, content-type variations, fixtures, and acceptance tests during that Skill's own design. `topic-discovery` is the first PHASE 1 Skill; its design and writing plan are drafts, not implementation authorization.
