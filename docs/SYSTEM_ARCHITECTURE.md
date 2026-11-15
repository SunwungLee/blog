# System Architecture

Status: PHASE 0 design baseline; implementation and provider-specific details remain open.
Decision record: [Phase_0_design.md](../Phase_0_design.md)

## Goals and Constraints

- Automate repeatable content work while keeping topic, plan, article, and publishing decisions with a person.
- Develop independent modules and connect them through versioned JSON contracts.
- Use scripts for deterministic processing and AI Skills only for semantic work.
- Run n8n on the Windows operations PC; do not introduce a cloud workflow server.
- Keep secrets out of source, Google Sheets, shared folders, prompts, and logs.

## Logical Components

| Component | Responsibilities | Boundary |
| --- | --- | --- |
| Script Engine | Validate and transform JSON; normalize data; perform deterministic SEO checks; handle file and image processing | Does not make semantic judgments or invent content |
| AI Skill Engine | Discover topics; synthesize research; plan, draft, fact-check, optimize, and adapt content | Each Skill has a defined JSON input/output contract; model IDs are supplied through configuration |
| Workflow Engine (n8n) | Orchestrate modules; route work; pause for approvals; retry or recover; record status and execution history | Does not duplicate module business logic or publish posts publicly |
| Google Sheets | Store IDs, metadata, current states, approvals, settings, and execution records | Does not store full article text |
| Google Drive | Store research artifacts, article versions, images, and platform-specific files | Files are referenced by Drive IDs in Sheets and module payloads |

## Runtime and Module Calls

n8n invokes local Python or JavaScript programs on the operations PC. Requests and responses use the common JSON envelope in [DATA_SCHEMA.md](DATA_SCHEMA.md). Exact process transport, permissions, and persistence calls are deferred to environment setup.

The orchestration foundation, workflow boundaries, invocation procedure, and integration gates are described in [ORCHESTRATION_FOUNDATION.md](ORCHESTRATION_FOUNDATION.md). Treat it as a design contract, not an implemented n8n workflow.

The PC initially starts n8n manually. Once operation is stable, configure and verify automatic startup. Inbound webhooks remain disabled unless a required integration is validated and secured. Google OAuth and other outbound integrations are verified during environment setup.

## Main Data Flow

1. n8n reads the current content state and necessary references from Sheets and Drive.
2. It builds a minimal JSON request and invokes the responsible local module.
3. The Script Engine handles deterministic work; the AI Skill Engine handles semantic work.
4. The module returns structured output or an error. n8n routes the result, updates state and execution logs, and stores file references.
5. At approval gates, the workflow waits for a human decision and records each approval attempt.
6. Completed stages are not repeated unnecessarily. A failure resumes at the failed stage after recovery.

```text
Proposed Google Forms input / human decisions
              |
              v
Google Sheets <--> n8n Workflow Engine <--> local Script / AI Skill modules
       |                 |                         |
       +-----------------+-------------------------+
                         |
                         v
                    Google Drive
```

## Approval and Publishing Boundary

Human approval is required for topic selection, the content plan, the final SEO-processed article, and the platform outputs (approved per platform). Target platforms are selected at plan approval. After each platform output is approved, create or update its Blogspot draft if applicable; after all selected platforms are approved, the workflow enters `WAITING_FOR_MANUAL_PUBLISH`. A person publishes on each selected platform and records completion; the system never makes a post public. `PUBLISHED` is reached only after all selected platforms are marked complete.

The topic stage is tracked per discovery run because no `content_id` exists yet; the content state starts at `RESEARCHING` after topic approval. Each approval stage allows the first review plus up to three re-reviews; a fourth rejection moves the item to `NEEDS_REVISION`, where a person decides whether to resume or cancel. If resumed, the attempt count for that stage restarts. A person may cancel only from a `WAITING_FOR_*` state or `NEEDS_REVISION`; cancellation is never automatic. The full state list, transitions, and the entry and exit rules for `FAILED`, `NEEDS_REVISION`, and `CANCELLED` are in [Phase_0_design.md](../Phase_0_design.md), sections 14 and 14.1.

## Reliability and Security

- Transient API failures and rate limits receive bounded retries; content-quality and JSON-repair loops have separate limits. See [Phase_0_design.md](../Phase_0_design.md), sections 9 and 14.
- Technical failures enter `FAILED` and require operator recovery before resuming the failed stage. Content or evidence issues enter `NEEDS_REVISION`. The state held before either is saved in `resume_status`.
- Reconcile uncertain storage outcomes before repeating a side effect. Check the Publishing record before creating a Blogspot draft, and update an existing draft rather than creating a second one.
- Skip a module call when Execution Logs already holds a successful row for the same execution subject (the `discovery_run_id` before content creation, otherwise `content_id`), module, and input hash.
- A publish rejection is routed by reason: format/structure to adaptation for that platform, image problems to image preparation, and factual or core-content changes to drafting and final-article approval again.
- `ANALYZING` is a temporary state and returns to `PUBLISHED` when the analysis run completes.
- Use n8n Credentials and environment variables. Separate development and operations credentials.
- Share Forms, Sheets, and Drive only with approved family-writer and administrator accounts; do not use public links.
- Do not log secrets or store them in Sheets.
- Backups are managed manually by the user: one encrypted external-drive backup per day.

## Deferred Decisions

Exact local process transport, n8n installation and startup configuration, OAuth/webhook requirements, Drive permission and save mechanisms, and model/search providers are not fixed here. Resolve these before the relevant integrations are implemented.
