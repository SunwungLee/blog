# Orchestration Foundation

Status: design baseline for the n8n integration. No n8n workflow, Google Sheets/Drive integration, process transport, or provider adapter is implemented or configured yet. The module-side support it relies on (`--hash-only`, envelope-only CLI output, `id-allocator`) is implemented and unit-tested.
Decision record: [Phase_0_design.md](../Phase_0_design.md) sections 9, 14, 14.1, and 20.14.

## Responsibilities

n8n owns sequencing, approval waits, technical retries, recovery, and storage writes. Python Skills and Scripts each perform one task. Workflows never re-implement module judgement or content rules.

- n8n: read current state, fetch the minimal references, invoke modules, branch on responses, wait for approvals, record state and execution history.
- Python modules: receive the versioned JSON envelope, do one task, return structured output or a structured error.
- Google Sheets: state, IDs, approvals, execution logs, metadata.
- Google Drive: research artifacts, articles, images, platform outputs.
- People: approve topic, plan, final article, and each platform output; publish publicly by hand.

`run_skill.py` and `run_script.py` are the local entry points. Which n8n node or transport calls them is decided on the operations PC after security and feasibility checks; this document does not fix shell argument construction, credentials, OAuth, webhooks, or storage nodes.

## Workflow Split

| Workflow | Starts at | Main steps | Waits / ends |
| --- | --- | --- | --- |
| Topic Discovery | A person requests discovery | Create the Discovery Run (`IDEA`, UUID `discovery_run_id`) → `topic-discovery` → allocate `topic_id`s with `id-allocator` and record candidates in recommendation order | Waits at `WAITING_FOR_TOPIC_APPROVAL`; on approval allocates `content_id` and creates the Content Pipeline row in `RESEARCHING` |
| Content Production | `RESEARCHING`, or re-entry after a publish rejection | Research → planning → plan approval → interview → drafting → fact-check → SEO → (re-fact-check if the body changed) → article approval → image preparation → platform adaptation | Waits at `WAITING_FOR_PLAN_APPROVAL`, `INTERVIEWING` (until every required question is answered or recorded as `모름`), `WAITING_FOR_ARTICLE_APPROVAL`. Ends at `PUBLISH_READY` |
| Publishing | `PUBLISH_READY` | Move to `WAITING_FOR_PUBLISH_APPROVAL` → approve per platform → create or update the Blogspot draft for an approved Blogspot output → person publishes → completion recorded per platform | Waits at `WAITING_FOR_MANUAL_PUBLISH`; `PUBLISHED` once every selected platform is complete |
| Performance Analysis | A person requests analysis while `PUBLISHED` | Move to `ANALYZING` → fetch Publishing rows and metrics → `performance-analysis` → record results | Returns to `PUBLISHED` |

This split defines responsibilities and resume points. Whether workflows call each other and how triggers are wired is decided during implementation.

Re-entry and loop paths:

- Topic rejection 1–3: end the run and its candidates as `REJECTED`; create a new Discovery Run in `IDEA` linked by `previous_run_id` with `attempt_no` + 1. The fourth rejection moves the run to `NEEDS_REVISION`.
- SEO response `requires_refactcheck = true`: run `fact-checking` again before requesting article approval. A failure follows the fact-check failure path below.
- Publish rejection (Publishing → Content Production): format/structure → `PLATFORM_ADAPTATION` for that platform only; image problems → `IMAGE_PREPARING`; factual or core-content changes → `DRAFTING`, then article approval again.

## Module Invocation Procedure

1. Read the current state and references from Sheets. If the step is not an allowed transition from that state, do not call the module.
2. Create the call's `run_id` and build the envelope with only the IDs and minimal input valid at that point.
3. Call the module with `--hash-only` to obtain `output.input_hash` without running it. It uses the same function as a real run, so the value always equals the real response's `usage.input_hash`. If Execution Logs already holds a successful row for the same subject (`discovery_run_id` before content creation, otherwise `content_id`), module, and `input_hash`, reuse its `output_ref` and skip the call. A `--hash-only` error means the envelope is invalid; route it like the same error from a real run.
4. Write an Execution Logs row with `started_at` for the new attempt, then call the module. Every outcome is one JSON envelope on stdout: exit code 0 carries `output`, exit code 1 carries `error` (including module load failures). Parse stdout for both codes and check `run_id`, `module`, and `schema_version` against the request. Treat a missing or unparsable envelope, mismatched identifiers, any other exit code, or a timeout as `UNKNOWN_FAILURE`. Never store raw stderr in Sheets or logs; it may contain secrets.
5. On success, persist the artifact first, then complete the log row and update state and usage. On failure, record the attempt's `error_code` and route by the table below.
6. If a record or an external side effect has an uncertain outcome, query storage and reconcile before repeating it.

Execution Logs gets one row per attempt. Technical retries keep the `run_id` and increase `attempt_no`. Reuse applies only to identical input and configuration; changed input or configuration is a new call.

`id-allocator` is never subject to hash reuse: identical requests must still return new IDs.

## ID Allocation

`topic_id` and `content_id` (`TOP|CNT-YYYYMMDD-NNNN`) are allocated only by the workflow through `run_script.py id-allocator` with input `{"kind": "topic" | "content", "date": "YYYY-MM-DD", "count": 1..100, "floor": 0..9999}`.

- An OS file lock serializes callers on the single operations PC; allocations are unique across concurrent processes.
- `floor` is the highest sequence already present in Sheets for that kind and date. The counter never drops below it, so a lost or reset state file cannot cause collisions. Always pass it.
- State lives in `state/id-sequences.json` under the repository, or in the folder set by the `BLOG_ID_STATE_DIR` environment variable. It holds only counters, no secrets.
- Lock timeout, an unreadable state file, or an exhausted daily sequence returns `STORAGE_FAILURE`, which routes to `FAILED`. An exhausted request consumes no numbers.
- Allocated but unused numbers (for example after a later failure) are skipped, not reused. Gaps are expected.

## Error, Retry, and Recovery Routing

| Situation | Orchestration action |
| --- | --- |
| `API_TRANSIENT`, `API_RATE_LIMITED` | Retry up to 3 times after the initial call. Honour `Retry-After` when given; otherwise use the configured exponential backoff |
| `AUTH_OR_PERMISSION`, `STORAGE_FAILURE`, or exhausted retries | Save the previous state in `resume_status` and move to `FAILED`. Resume from the failed step after operator recovery |
| `INVALID_INPUT`, `INSUFFICIENT_EVIDENCE` | No automatic retry. Move to `NEEDS_REVISION` for a person to fix input or criteria and decide to resume |
| Module error `INVALID_JSON` | The module (`call_json` in `common/llm.py`) has already used its two repair attempts. Do not retry; move to `NEEDS_REVISION` |
| Module error `QUALITY_BELOW_THRESHOLD` | `master-article`, `seo-optimization`, and `platform-adaptation` have already used their two reruns (`run_with_quality`). Do not rerun; move to `NEEDS_REVISION` |
| Fact-check failure (`fact-checking` success response with `passed = false`) | Record `QUALITY_BELOW_THRESHOLD`, increase `review_rework_count`, and return to `DRAFTING` while the count is at most 2. A third failure, or insufficient evidence, moves to `NEEDS_REVISION` |
| `UNKNOWN_FAILURE`, envelope-less output, or another unrecoverable technical error | No automatic retry. Save `resume_status` and move to `FAILED` |
| Approval rejection | Add a new Approvals row per attempt and return to the step for that reason. The fourth rejection including the first review moves to `NEEDS_REVISION`. A `revision_decision` resume restarts that stage's attempt count at 1 |
| Cancellation | Only a recorded human decision in `WAITING_FOR_*` or `NEEDS_REVISION` moves to `CANCELLED` |

n8n retries automatically only for `API_TRANSIENT` and `API_RATE_LIMITED`. JSON repair and quality reruns happen inside modules; repeating them in n8n would exceed the decided limits.

Approval waits are never retried automatically. `FAILED`, `NEEDS_REVISION`, and `CANCELLED` follow the same rules in Discovery Runs and Content Pipeline. `FAILED` returns to `resume_status` after operator recovery. Resuming a topic-stage `NEEDS_REVISION` ends that run as `REJECTED` and creates a new run in `IDEA` with `attempt_no` 1.

### Fact-check rework counter

`review_rework_count` on the Content Pipeline row counts returns from `REVIEWING` to `DRAFTING` caused by a failed fact-check. It is a column rather than an Execution Logs aggregate because every redraft is a new module call with a new `run_id`, so `attempt_no` cannot express it.

- Start at 0 when the row is created.
- Reset to 0 when the content is resumed from `NEEDS_REVISION`, and when an article or publish rejection sends it back to `DRAFTING` (a new revision cycle).
- The re-fact-check after SEO uses the same counter.

## Side-Effect Boundaries

- No module or automatic step publishes publicly. `PUBLISHED` is reached only through per-platform human completion records.
- The Blogspot draft is saved only after platform approval. If a `platform_draft_id` exists for the content and platform, update that draft instead of creating another.
- If a Drive save has an uncertain outcome, compare the stored file name and checksum before retrying. Never save again without checking for a duplicate.
- Article and platform-output versions are append-only.
- Execution Logs record token usage and `input_hash`. n8n computes cost; prices and secrets are never passed to modules.

## Implementation Order and Completion

1. **Design baseline**: keep state, approval, error, and idempotency rules aligned with this document and the decision record. Module-side support is done; no integration exists.
2. **Environment and invocation boundary**: on the designated PC only, set up n8n and local Python execution. Verify the transport, permissions, input size, timeout and termination of hung processes, stdout/stderr separation, exit codes, envelope checks, and that no secret is exposed.
3. **Storage adapters**: with development Sheets/Drive credentials, verify minimal reads and writes, partial failures, and reconciliation after duplicate requests. Keep operations credentials separate.
4. **One workflow at a time**: start with mocked module results and no provider calls. Verify approval waits, error routing, interrupted runs and resume, and duplicate runs before moving to the next workflow.
5. **Operations readiness**: real providers only after model/search selection, the cost cap, a terms review, and the environment gate, with separate approval. Automatic public publishing is out of scope.

A workflow integration is complete only when state and logs stay consistent on the success path and under malformed responses, transient errors, exhausted retries, uncertain storage outcomes, approval waits, resume, and duplicate execution.

## Open Items Before Integration

- The transport n8n uses to run local programs, request/response size limits, the timeout value, and how hung processes are killed.
- Sheets/Drive nodes or adapters, OAuth scopes, and the development/operations account split.
- Retry wait values, workflow concurrency, and duplicate-trigger protection beyond ID allocation.
- The approval request and notification channel and how decisions reach Sheets.
- Atomicity and recovery when a multi-row Sheets update fails part-way.
- Providers, the full-system cost cap, the price table, and real-provider quality checks.

Do not settle these by guessing in code or credentials. Close each by user decision or by verification on the designated PC before the related implementation.
