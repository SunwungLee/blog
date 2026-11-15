# Implementation Plan

Status: PHASE 0 design baseline. Initial setup on the designated PC began 2026-11-15. Python 3.12.10, Node.js 24.14.1, Git for Windows, and n8n 2.47.4 are available; the project `.venv` contains Pillow 13.0.0. All 132 unit tests pass in that environment. n8n account setup, workflows, Google integrations, provider selection, credentials, and real-provider quality tests remain pending.

Implementation status (user-directed, before the environment gate): all 10 Skills (`skills/`), the 5 Scripts (`scripts/`, including the workflow-only `id-allocator`) and shared code (`common/`) exist as standard-library Python with provider-independent `llm`/`search` injection and 132 passing unit tests (`python -m unittest discover -s tests/unit`). n8n 2.47.4 is installed, but no provider adapter, API call, n8n workflow, Sheets/Drive access or real-provider quality test exists yet; those, and the design approvals above, remain gated. Model roles per task live in `config/model-config.json` (roles only, no model IDs) and quality thresholds in `config/quality-rules.json`; both are JSON until PyYAML may be installed, then they move to `config/*.yaml`. Threshold values (minimum body 1500 chars, overlap limits, unverified ratios, SEO body growth 10%) are provisional until real-provider quality tests. CLI entry points: `run_skill.py <skill>` and `run_script.py <script>` read a request envelope from stdin (UTF-8, BOM tolerated) and print exactly one response envelope (exit 0 = `output`, 1 = `error`); `--hash-only` returns the `input_hash` without running the module.

Code review and design-conformance review (2026-11, see section 20.12 of the decision record) were applied. The four items deferred by that review were then decided on recommendation and implemented (section 20.13): the response envelope reports `usage` (call counts, adapter-reported tokens, `input_hash`); platform adaptation converts Blogspot by script first and uses AI for Naver; performance analysis takes optional `publishing[]` references; `topic-discovery` accepts only `locale = ko-KR`.
Decision record: [Phase_0_design.md](../Phase_0_design.md)

## Guiding Rules

- Work through one phase and one independent module at a time.
- Finish design and receive approval before writing implementation code.
- Use TDD, then independent verification and code review.
- Keep modules connected through versioned JSON and stable IDs.
- Document decisions and unresolved items in Markdown at the end of each scheduled stage.
- Do not publish content automatically; human approval and publication remain required.

## PHASE 0: Foundation and Detailed Design

Completed design activities:

1. Review the PHASE 0 document and identify design gaps.
2. Resolve foundational choices with the user.
3. Define engine responsibilities and local invocation architecture.
4. Draft Sheets, Drive, and module data contracts.
5. Define workflow transitions, approval returns, retries, and recovery.
6. Record user and operations requirements.

The PHASE 0 document package is consolidated. Some integration-specific decisions remain explicitly open in the canonical PHASE 0 decision record. The designated PC's base runtime setup is complete; account connections and workflow integration remain gated. `topic-discovery` design drafts are also available.

## Before PHASE 1: Development Environment

The prerequisite list for the user's designated personal/operations PC is recorded in [`requirements.txt`](../requirements.txt). It is an environment checklist, not a Python dependency lockfile. The base runtime is installed; provider choices, credentials, account integrations, and local invocation/recovery checks remain.

Remaining setup and integration work:

1. Review the existing Git repository state; all project files are currently untracked.
2. Verify that n8n can invoke local programs using the agreed JSON contract.
3. Separate development and operations credentials; configure environment variables securely.
4. Verify restart, network, and recovery behavior.
5. Initially run n8n manually; configure automatic startup after stabilization.
6. The user manually manages encrypted external-drive backups. Do not assume automated backup administration.
7. Estimate candidate model and search-API costs, then confirm the monthly AI/API cap with the user. A provisional $5/month cap for 30 `topic-discovery` runs has been approved; it covers that Skill only. The full-system cap and over-limit behavior remain open.
8. Choose the model and search API for `topic-discovery` after a Korean quality comparison and an availability, price, and terms recheck.
9. Apply the confirmed state and data rules from section 20.8 of the decision record.

The first n8n CLI invocation generated a local encryption key in the user's n8n configuration directory. Preserve that configuration in secure backups; losing the key may prevent decrypting credentials stored by n8n. No external credentials have been added. In PowerShell, use the `.cmd` launchers (for example `npm.cmd` and `n8n.cmd`) because script execution policy blocks the `.ps1` shims in this environment.

Steps 8–10 must be finished before PHASE 1 implementation starts. The review choices in section 20.8 are confirmed. Open items are listed in section 19 of the decision record and in the open-items list of [TOPIC_DISCOVERY_DESIGN.md](TOPIC_DISCOVERY_DESIGN.md). The model and search provider remain unselected; the full-system monthly cap also remains unconfirmed.

Working interpretation, awaiting user confirmation: the approved `topic-discovery` cap is enough to start implementing that Skill, and the full-system cap is set after the other Skills are estimated.

Environment setup is not application implementation. The initial local runtime is installed and the unit suite passes, but the environment gate is not complete until provider choices, credentials, cost limits, and local invocation/recovery checks are resolved.

Until provider selection and the remaining environment gates are complete, do not call provider APIs or enter credentials. Design work and offline tests may proceed. Implementation, API quality tests, and operation remain gated on user approval and the required environment checks.

## PHASE 1: `topic-discovery`

Build only the first Skill. Steps 1–3 are design work and may run before the environment is ready; steps 4–6 wait for the environment gate.

1. Run Superpowers Brainstorming and clarify requirements, constraints, and edge cases.
2. Define its responsibility and exact JSON input/output contract.
3. Write and review the Skill Design Document and Writing Plan.
4. Write failing tests first (RED), implement the minimum behavior (GREEN), and refactor.
5. Verify candidate count (5–10), keyword sets, search intent, freshness labels, source links, structured errors, that the Skill invents no IDs, and that output supports the workflow's human topic-approval step.
6. Complete independent tests and code review before preparing integration.

Do not begin other Skills in parallel.

## Gates

- Design gate: responsibilities, I/O, error handling, approval flow, and open decisions are documented and approved.
- Environment gate (before implementation): local module execution, credentials, tests, and recovery checks work; the cap covering the Skill being built and the `topic-discovery` model and search provider are set; the confirmed state and data rules are represented.
- Module gate: tests and verification pass; documentation is current; no secrets are exposed.
- Integration gate: the independent module contract and side-effect/idempotency behavior are verified.

## Orchestration Foundation

The n8n orchestration blueprint is documented in [ORCHESTRATION_FOUNDATION.md](ORCHESTRATION_FOUNDATION.md). No n8n workflow, Google integration, local process transport, or provider adapter is implemented or configured here. The module-side support it needs is implemented and tested (decision record section 20.14): `--hash-only` for pre-call duplicate checks, one-envelope CLI output including module load failures, the `id-allocator` script for serialized date-sequence IDs, and the `review_rework_count` rule for fact-check rework.

After the designated-PC environment gate, validate the local invocation and storage boundaries before creating workflows. Then integrate and verify one workflow at a time (topic discovery, content production, publishing, performance analysis) with mocked module results first. Each integration must cover approval pauses, structured error routing, bounded retries, duplicate-run reuse, uncertain side-effect reconciliation, and manual recovery before it is considered complete. Preserve the existing prohibition on automatic public publishing.

## Deferred Decisions

Resolve model and search providers after the Korean quality comparison and a cost, availability, and terms review; set the full-system monthly cap once the remaining Skills are estimated. Finalize provider wait intervals, exact Sheets field types and JSON Schema, local process transport, Drive save permissions, OAuth needs, UI notifications, quality thresholds, and platform-specific API details before those integrations are implemented.
