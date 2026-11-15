# Data Schema and Module Contracts

Status: PHASE 0 schema outline. Column types, requiredness, enumerations, and machine-validated JSON Schema remain to be finalized before implementation.
Decision record: [Phase_0_design.md](../Phase_0_design.md)

## Identifier and Time Rules

- `topic_id`: `TOP-YYYYMMDD-0001`; allocated when a candidate is created.
- `content_id`: `CNT-YYYYMMDD-0001`; allocated after topic approval.
- Internal row IDs such as `run_id`, `research_id`, `approval_id`, and `article_version_id` use UUIDs.
- Date IDs use the issuing date. The workflow allocates them only through the `id-allocator` script, which serializes callers with a file lock and never goes below the `floor` (highest sequence already in Sheets). See [ORCHESTRATION_FOUNDATION.md](ORCHESTRATION_FOUNDATION.md#id-allocation).
- Timestamps use ISO 8601 with a time-zone offset.

## Google Sheets Tabs

One row represents one record. Link records by IDs; represent repeating keywords, topic-source links, target platforms, approvals, platform outputs, and measurements as separate rows. The confirmed lifecycle rules are summarized below; the canonical state machine is in section 14.1 of the decision record.

| Tab | Key fields |
| --- | --- |
| Topics | `topic_id`, `discovery_run_id`, `recommendation_order`, `content_type`, `candidate_title`, `search_intent`, `rationale`, `freshness`, `requires_firsthand_experience`, `status` (`CANDIDATE`, `SELECTED`, `REJECTED`), `selected_content_id`, `created_at` |
| Topic Keywords | `topic_id`, `keyword`, `keyword_type` (`primary`, `related`), `sort_order` |
| Topic Sources | `topic_source_id`, `topic_id`, `source_title`, `source_url`, `publisher`, `accessed_at` |
| Discovery Runs | `discovery_run_id`, `status`, `attempt_no`, `previous_run_id`, `resume_status`, `selected_topic_id`, `created_at`, `updated_at` |
| Content Pipeline | `content_id`, `topic_id`, `content_type`, `working_title`, `current_status`, `current_step`, `resume_status`, `current_article_version`, `review_rework_count`, `created_at`, `updated_at` |
| Content Platforms | `content_id`, `platform` (`naver`, `blogspot`), `selected_at` |
| Research | `research_id`, `content_id`, `source_title`, `source_url`, `publisher`, `published_at`, `accessed_at`, `source_type`, `evidence_summary`, `source_file_id`, `verification_status` |
| Articles | `article_version_id`, `content_id`, `version_no`, `article_kind` (`plan`, `draft`, `final`), `status`, `drive_file_id`, `file_name`, `checksum`, `created_at`, `created_by_run_id` |
| Publishing | `publishing_id`, `content_id`, `platform`, `article_version_id`, `output_version_no`, `status`, `drive_file_id`, `platform_draft_id`, `draft_url`, `human_published_at`, `completed_at` |
| Approvals | `approval_id`, `discovery_run_id`, `topic_id`, `content_id`, `platform`, `approval_stage`, `attempt_no`, `artifact_type`, `artifact_ref_id`, `requested_at`, `decision`, `resume_to_status`, `decided_at`, `decided_by_role`, `feedback` |
| Interview Responses | `response_id`, `form_response_id`, `content_id`, `question_id`, `question_version`, `question_source` (`template`, `ai`), `question_text`, `answer_text`, `answered_at` |
| Fact Checks | `fact_check_id`, `content_id`, `article_version_id`, `claim_text`, `result`, `research_id`, `note`, `checked_at`, `created_by_run_id` |
| Images | `image_id`, `content_id`, `source_type` (`own`, `licensed`, `ai_generated`), `drive_file_id`, `rights_note`, `rights_checked_at`, `status` |
| Performance | `metric_id`, `content_id`, `platform`, `measured_at`, `metric_name`, `metric_value`, `source` |
| Settings | `setting_key`, `setting_value`, `updated_at`; no secrets |
| Execution Logs | `execution_log_id`, `run_id`, `module`, `workflow_step`, `discovery_run_id`, `topic_id`, `content_id`, `platform`, `input_hash`, `output_ref`, `status`, `started_at`, `completed_at`, `attempt_no`, `error_code`, `token_usage`, `estimated_cost` |
| Question Templates | `question_id`, `category`, `content_type` (empty for common questions), `question`, `required`, `sort_order`, `active`, `version`; key is `question_id` + `version` |

Notes on specific tabs:

- Discovery Runs holds the topic-stage state (`IDEA`, `WAITING_FOR_TOPIC_APPROVAL`, `COMPLETED`, `REJECTED`, `NEEDS_REVISION`, `FAILED`, `CANCELLED`) because no `content_id` exists before topic approval. The workflow issues `discovery_run_id` before calling the Skill. Rejecting all candidates ends that run and its candidates as `REJECTED` and creates a new run linked by `previous_run_id` with `attempt_no` increased. The first run is 1. A fourth rejection moves the run to `NEEDS_REVISION` instead; a resume decision ends it as `REJECTED` and starts a new run with `attempt_no` 1. A Content Pipeline row is created in `RESEARCHING` when a topic is approved.
- `resume_status` stores the state held just before `FAILED` or `NEEDS_REVISION`. `current_step` is the module currently running or last run.
- `review_rework_count` counts returns from `REVIEWING` to `DRAFTING` after a failed fact-check (at most 2; the third failure moves to `NEEDS_REVISION`). It starts at 0 and resets on a `NEEDS_REVISION` resume or when an article/publish rejection starts a new drafting cycle. See [ORCHESTRATION_FOUNDATION.md](ORCHESTRATION_FOUNDATION.md).
- Article versions are append-only; `version_no` counts per `article_kind`. Platform outputs are recorded in Publishing, not Articles.
- Topics are returned in recommendation order; `recommendation_order` preserves display order and is not a quality or search-demand score. No search-volume or competition score is stored.
- Topic Keywords stores one primary keyword and three to five related keywords per successful discovery candidate.
- Topic Sources stores web references used to explore a candidate, not fact-checked Research records. Store source metadata and links, not full page text or search snippets. A successful discovery candidate has at least one relevant URL; fewer than five source-supported candidates returns `INSUFFICIENT_EVIDENCE`. Finance/policy discovery prefers official sources. Whether a search provider's terms allow storing its links here must be checked before that provider is selected.
- Approvals: a rejected approval creates a new row; `attempt_no` starts at 1. Each stage allows an initial review plus up to three re-reviews. A fourth rejection moves the item to `NEEDS_REVISION`; after a resume decision, that stage's attempt count restarts at 1. `approval_stage` is `topic` (keyed by `discovery_run_id`), `plan` or `article` (keyed by `content_id`, referencing an `article_version_id`), `publish` (one row per `content_id` + `platform`, referencing a `publishing_id`), or `revision_decision` (recording resume or cancel and, when resuming, `resume_to_status`). Record only the approver role (`writer` or `administrator`), never an email address.
- Interview Responses keep the question text as asked. AI follow-up questions use `question_source = ai` and a UUID `question_id`. An answer of "모름" (don't know) is stored as the answer and is not asked again or filled in by AI. `form_response_id` applies only if Google Forms is confirmed as the input screen; how a Forms response is linked to a `content_id` is open.
- Question Templates: editing a question adds a new row with a higher `version`; existing rows are not changed.
- Execution Logs: `run_id` identifies one module call; retries keep the `run_id` and increase `attempt_no`. `input_hash` covers the module input and applied configuration version. A successful row with the same applicable subject ID (`discovery_run_id` before content creation, otherwise `content_id`), module, and `input_hash` means the step is not run again and `output_ref` is reused; cached research is found the same way.
- Images whose usage rights are not confirmed are not used in published outputs.
- Images `status`: `PLANNED` (image plan only), `RIGHTS_CONFIRMED` (`image_id`, `drive_file_id`, `rights_note`, `rights_checked_at` all present and source type allowed), `PENDING_RIGHTS` (anything missing). `image_id` is issued by the Images tab, never by a Skill or model.
- Fact Checks `result`: `supported`, `unsupported`, `contradicted`, `unverifiable`. `created_by_run_id` is the `run_id` of the fact-checking call. Finance claims count as supported only with an `official` source.
- Per-post settings passed to content Skills: `sponsored` (boolean; `true` adds the advertising notice) and `blocked_terms` (list of names, places, or other strings that must never appear in prompts or outputs for that post, in addition to the default PII patterns).
- `input_hash` is `sha256` over the canonical JSON of `{module, input}` plus the configuration version (`model-config`, `quality-rules`, `writing-style` versions; `common/config.config_version`).
- Performance analysis receives the content's Publishing rows; only rows with `human_published_at` are used, the latest per platform.

## Google Drive

Create one folder for each approved `content_id`:

```text
content/{content_id}/
├── research/
├── plans/
├── articles/
├── images/
└── publishing/
    ├── naver/
    └── blogspot/
```

Name files `{content_id}_{artifact_type}_v{version:03d}.{ext}`. Do not put titles in file names. Examples: `CNT-20261112-0001_plan_v001.md`, `CNT-20261112-0001_master_v001.md`, and `CNT-20261112-0001_naver_v001.html`. Store Drive file IDs and version metadata in Sheets. Plan, draft, and final article files use the Articles `version_no`; platform output files use the Publishing `output_version_no`.

File-kind mapping used by the code: the Articles `article_kind = draft` row points to a `master` file (`*_master_vNNN.md`, written by `master-article`); `final` is the SEO-processed article (`*_final_vNNN.md`); platform outputs are HTML (`*_naver_vNNN.html`, `*_blogspot_vNNN.html`) because both are pasted or posted as HTML.

Until Drive integration exists, Skills return the file inline as `output.artifact` (`file_name`, `drive_path`, `content_type`, `content`, `checksum`). n8n saves it to Drive and records the Drive file ID and `checksum` (`sha256:<hex>`) in Sheets. Inline content is a temporary transport, not the long-term contract.

## JSON Request and Response Envelope

```json
{
  "schema_version": "1.0",
  "run_id": "UUID",
  "module": "module-name",
  "refs": {
    "discovery_run_id": "UUID",
    "topic_id": "TOP-YYYYMMDD-0001",
    "content_id": "CNT-YYYYMMDD-0001",
    "drive_file_ids": []
  },
  "input": {}
}
```

Include only applicable references. A topic-discovery request carries only `discovery_run_id`, because no topic or content ID exists yet. Pass Drive references and necessary excerpts instead of repeatedly passing a full article. The envelope validator rejects malformed `topic_id`/`content_id`, an empty `discovery_run_id`, or a non-string `drive_file_ids` entry with `INVALID_INPUT` before any model call. Request JSON is read as UTF-8 (a BOM is tolerated).

Successful responses contain `schema_version`, `run_id`, `module`, `refs`, `output`, and `usage`. Failed responses contain the same execution identifiers and an `error` object with `code`, `message`, and `retryable`, plus `usage` when the request was readable; optional `details` must not contain secrets. `usage` = `{llm_calls, search_calls, input_tokens, output_tokens, input_hash}`; token fields appear only when a model was called and are `null` if the adapter did not report them. n8n copies `usage` into Execution Logs (`token_usage`, `input_hash`) and computes `estimated_cost`. The canonical error codes and retry mapping are in the decision record.

## Relationships and Constraints

- One topic candidate may link to its approved content through `selected_content_id`.
- A topic candidate can have multiple keyword and topic-source records. Each successful `topic-discovery` candidate has at least one source link.
- A content can have multiple research records, article versions, approval attempts, publishing records, responses, and performance measurements.
- Enforce one Publishing record per `content_id` + `platform` + `article_version_id` + `output_version_no`. Re-adapting the same article after a publish rejection adds a row with a higher `output_version_no`, preserving the previous output. For Blogspot, create a draft only after platform approval; if a `platform_draft_id` already exists for the content and platform, update that draft instead of creating another.
- Target platforms are selected per content at plan approval and stored in Content Platforms. Create Publishing records only for those platforms; `PUBLISHED` requires all of them to be marked complete.
- The state list and transition rules are defined only in the decision record, sections 14 and 14.1.
- Interview responses are retained with the content and deleted when the content is deleted.
- Never store API keys or credentials in Sheets.
- A person may cancel only while an item is in a `WAITING_FOR_*` state or `NEEDS_REVISION`; the workflow never cancels automatically. `ANALYZING` returns to `PUBLISHED` when analysis is complete.

## Deferred

Finalize column types, required and nullable fields, enumerations, validation rules, formal JSON Schema files, exact module transport, and Drive access/save behavior before implementation.
