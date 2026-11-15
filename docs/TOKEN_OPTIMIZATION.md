# Token and Cost Optimization

Status: PHASE 0 operating principles plus a preliminary `topic-discovery` cost review. A provisional $5/month cap is approved for that Skill only; the full-system cap and provider selection remain open.
Decision record: [Phase_0_design.md](../Phase_0_design.md)

## Core Principle

Use scripts for deterministic work and AI only for semantic judgment or creation. Do not reduce factual, editorial, or human approval checks to save tokens.

## Model Routing

Use task-based model roles (lightweight and high-quality) through configuration. Do not hard-code provider or model IDs into Skills. Select actual providers and models after checking availability and cost at implementation time.

| Work | Preferred handling |
| --- | --- |
| Data cleanup, validation, deduplication, file naming, formatting, character counts, mechanical SEO | Script |
| Keyword classification, search intent, answer analysis, additional questions, SEO quality review | Lightweight AI where needed |
| Planning, article writing, fact-checking | High-quality AI, with search/source evidence as required |
| Research | Search API plus AI synthesis; provider choice remains open |
| Topic discovery | Search API plus AI; model tier and providers chosen after a Korean quality/cost test |
| Platform conversion | Script first; AI only when semantic adaptation is necessary |

## Input and Output Discipline

- Pass stable IDs and Drive references instead of repeatedly sending full articles.
- Include only relevant excerpts and sources for the current task.
- Return structured JSON and file references; avoid duplicating large artifacts across workflow steps.
- Cache reusable research and outputs using input hashes and versioned configuration. Invalidate the cache when material inputs, prompts, rules, or source versions change.
- Record each module attempt, token usage, estimated cost, and retries in Execution Logs.

## Cost Controls

- Estimate provider and search-API costs before fixing the monthly AI/API cap.
- Set the monthly cap before PHASE 1 implementation starts. Only the `topic-discovery` cap is set so far (see the cost review below). What happens when a cap is exceeded (stop or notify) is not yet decided.
- Use lightweight models only where quality tests show they are sufficient.
- Keep quality checks and approval gates even when retrying or optimizing.
- Review actual usage against the cap and revise routing based on measured quality and costs.

## Evaluation

Track at minimum the execution ID, module, retry count, token usage, and estimated cost. Compare cost with quality outcomes and human return-for-revision rates. Exact reporting cadence and success thresholds remain open until initial operating results are available.

## Preliminary Cost Review (2026-11-12)

The user estimates 30 `topic-discovery` runs per month. For planning only, assume 10,000 input tokens and 2,000 billed output tokens per run. Actual cost depends on prompts, output length, retries, and model availability; benchmark Korean output and recheck prices before selecting a provider.

| Candidate model | Standard API price per 1M tokens (input/output) | Estimated model cost per run | Estimated cost for 30 runs |
| --- | --- | ---: | ---: |
| OpenAI `gpt-5.4-mini` | $0.75 / $4.50 | $0.0165 | $0.50 |
| Google `gemini-3.8-flash` | $0.75 / $3.75 through 2026-12-31; $1.50 / $7.50 from 2027-01-01 | $0.015 currently; $0.03 from 2027-01-01 | $0.45 currently; $0.90 from 2027-01-01 |

These are candidates for a quality/cost test, not a provider or model decision. Which configuration role (`lightweight` or `high_quality`) they would fill is also undecided. The OpenAI price list includes cheaper current models (for example `gpt-6-luna` at $0.10 / $0.50); include them in the quality test rather than treating this pair as the full shortlist. Gemini's unpaid API tier may use prompts and responses to improve Google products and may involve human review; do not send personal or sensitive content to the unpaid tier. Paid Gemini API use is not used to improve Google's products, though prompts and responses are logged for a limited period for abuse detection. OpenAI API data is not used for training by default, but abuse-monitoring logs may retain content for up to 30 days. Tavily's handling of search queries has not been reviewed yet; check it before selection. Keep identifying information out of prompts and search queries regardless.

| Search option | Published pricing | Notes |
| --- | --- | --- |
| Tavily Search, `advanced` | 2 credits/request; 1,000 free credits/month, then $0.008/credit ($0.016/request) | At two advanced searches per run, 30 runs use 120 credits. If free credits are unavailable, estimated search cost is $0.96/month. Predictable request-based cost. Returns search results, not keyword-volume metrics. |
| Gemini Google Search grounding | 5,000 search requests/month shared across Gemini 3+ models, then $14/1,000 requests | A single model request may perform multiple separately billed queries, so actual query count should be measured. **Terms review required before selection:** the Gemini API terms restrict collecting grounding Links (URLs and titles) by automated means for another purpose and restrict storing Grounded Results, which may be incompatible with saving source links in the Topic Sources tab. Grounding prompts and output are also stored by Google for 30 days. |

Google Custom Search JSON API is closed to new customers and is scheduled to end on 2027-01-01; it is not a candidate for a new integration.

At 30 runs/month, two Tavily advanced searches per run, and paid model/search rates (assuming no free search credits), the estimated combined usage is about $1.46/month with GPT-5.4-mini, $1.41/month with Gemini 3.8 Flash at its current price, or $1.86/month with Gemini 3.8 Flash at its price from 2027-01-01. The estimate excludes retries, JSON-repair and quality reruns, re-discovery after a topic rejection, and any extra reasoning tokens billed as output. On 2026-11-12, the user approved a provisional $5/month cap for `topic-discovery` alone, about 2.7–3.5 times the estimate. This is not the monthly cap for the full system; research, planning, writing, fact-checking, and other Skills still need to be estimated. The overall cap and whether to stop or notify at the limit remain undecided.

Prices checked 2026-11-12; USD, excluding tax and currency conversion. Recheck before implementation:

- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- [OpenAI API data controls](https://developers.openai.com/api/docs/guides/your-data)
- [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- [Gemini API terms and data use](https://aistudio.google.com/docs/terms)
- [Tavily credits and pricing](https://docs.tavily.com/documentation/api-credits)
- [Google Custom Search JSON API status and pricing](https://developers.google.com/custom-search/v1/overview)
