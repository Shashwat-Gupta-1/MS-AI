Let's consolidate everything into one complete guardrails-and-edge-cases reference, organized by where in the pipeline each risk shows up, with the concrete mitigation for each.

## 1. Security / Access Control Guardrails

| Risk | Mitigation |
|---|---|
| App bug or prompt injection tries to write/delete data | Read-only service account (`bigquery.dataViewer` + `bigquery.jobUser` only) — no write path exists at the IAM layer, regardless of app code |
| LLM generates DML/DDL despite instructions | Static SQL parser (`sqlglot`) rejects anything except SELECT/WITH before it ever reaches BigQuery |
| A role/person sees data outside their permission | BigQuery Authorized Views per domain + row-level access policies — enforced by BigQuery itself, not app code |
| App-layer role filtering has a bug | Never treat app-layer filtering as the real boundary — it's a UX nicety; BigQuery IAM/views are the actual enforcement |
| Shared service account makes per-user access impossible | Propagate real user identity via OAuth or impersonation so BigQuery's row/column policies actually apply |
| Sensitive columns (Aadhaar, PAN) exposed even to authorized users | Column-level policy tags — restrict specific columns independently of table-level access |

## 2. Privacy Guardrails (row data never reaching an LLM)

| Risk | Mitigation |
|---|---|
| Row-level data accidentally sent to cloud LLM | Only schema text + question go to the LLM; result rows are handled separately (template or local-only model) |
| LLM asked to "guess" or state a data value | System prompt explicitly instructs: never assume or state what any data value is, only reference structure |
| Error messages leak real data values | Scrub error text of literal values before sending back to the LLM for auto-retry |
| Large result sets need natural-language summarization | Route only through a self-hosted/local model if this is needed — never an external API, since that's the one point row data exists outside BigQuery |

## 3. Retrieval Guardrails (Layer 3)

| Edge case | Mitigation |
|---|---|
| Ambiguous column names across tables (multiple "status" columns) | Rich, distinct column descriptions per table so embeddings differentiate them |
| Business synonyms not matching schema vocabulary ("defaulters" vs. `dpd_bucket`) | Domain summaries written with real business vocabulary, not just formal terms; optional synonym glossary table |
| Multi-domain questions (spans loan + lead + collections) | Generous top-k for domain matching (2-3, not 1) so no domain silently gets dropped |
| Vector search misses a needed join table because it's not semantically similar to the question | FK-expansion step — pulls in linked tables via `fk_relationships`, independent of vector similarity |
| No confident match found at all | Distance threshold — below it, tell the user "I couldn't confidently identify the right tables, can you rephrase?" rather than guessing |
| Table belongs to multiple domains (hub tables like `customers`) | `domain_tags` as an array; filtering uses overlap, not exact match |
| New table added without domain tags | Alert/flag any table with zero tags after a schema-sync run — don't let it silently vanish from retrieval |
| LLM-suggested domain tags are wrong | `reviewed_by_human = FALSE` gate — nothing untrusted enters production retrieval until reviewed |

## 4. SQL Generation Guardrails (Layer 4)

| Edge case | Mitigation |
|---|---|
| Aggregation ambiguity (requested vs. disbursed amount) | Semantic layer / pre-defined metrics for known recurring questions, so the LLM isn't guessing every time |
| Time-window ambiguity ("recent," "this quarter") | Explicit date anchoring in the prompt; don't let the LLM silently pick a default |
| Joins causing row fan-out (loans × EMIs × payments double-counting amounts) | Include this exact scenario in your eval set; instruct the LLM about aggregation-before-join patterns where relevant |
| NULL handling changes the meaning of an aggregate | Explicit instruction/example in the prompt about how to treat NULLs in financial fields |
| LLM hallucinates a column/table that doesn't exist | Dry run catches this immediately — feed the error back for one retry, then fail gracefully |
| Schema drift causes generated SQL to reference outdated structure | Dry-run failure spikes act as your alert signal that drift may have occurred |

## 5. Execution / Cost Guardrails (Layer 4)

| Edge case | Mitigation |
|---|---|
| Expensive/runaway query (full scan of an 8M-row table) | Dry-run byte estimate + cost-guard threshold check before execution |
| Something slips past the estimate | `maximum_bytes_billed` hard cap enforced by BigQuery itself at execution time |
| Query takes too long / hangs | Query timeout enforced at execution |
| Query returns an enormous result set | Row limit on the execution call (e.g. `max_results=200`) |

## 6. Answer Delivery Guardrails (Layer 5)

| Edge case | Mitigation |
|---|---|
| Large result set needs formatting | Shape-based logic: scalar → template, small table → direct render, large → capped/truncated with a note |
| Sensitive column values end up in the final answer even if masked upstream | Output-filtering step that redacts sensitive fields regardless of what the SQL returned, as a last-line safety net |
| User asks a non-analytical question ("how do I apply for a loan") | Lightweight intent classification before attempting SQL generation at all — route conversationally instead |

## 7. Conversational / Follow-up Guardrails

| Edge case | Mitigation |
|---|---|
| Short follow-up question lacks enough context to retrieve anything ("what about last month?") | Rewrite step: LLM combines prior question + new fragment into a self-contained question before re-entering the pipeline |
| Session state grows unbounded | Keep only a short rolling window (last 1-3 exchanges), expire after inactivity |

## 8. Ingestion Pipeline Guardrails (Layer 2)

| Edge case | Mitigation |
|---|---|
| Re-embedding everything every run is wasteful | Schema hash diffing — only reprocess tables whose structure actually changed |
| A table gets dropped from BigQuery but lingers in the catalog | Explicit `DELETE` step for tables no longer present in the latest schema scan |
| Pipeline fails partway through | Log every run's outcome (scanned/changed/dropped/errors); alert on error spikes rather than assuming silent success |
| Domain tagging inconsistent as new tables appear | Layered approach — keyword rules first (fast, deterministic), LLM fallback only when rules find nothing, human review gate before anything untrusted goes live |

## 9. Evaluation / Ongoing Trust Guardrails

| Risk | Mitigation |
|---|---|
| No way to know if retrieval/SQL generation is actually accurate | Build a labeled eval set (~50-100 question → correct tables → correct SQL pairs) before treating the MVP as "done" |
| Accuracy silently degrades as schema evolves | Re-run the eval set periodically, especially after major schema changes |
| You don't know what real users are actually asking or where it fails | Log every request (question, matched domains, tables, SQL, success/failure) — this is your feedback loop for improving tagging and retrieval over time, without ever logging actual result values |

---

## The one organizing principle behind all of this

Every guardrail here follows the same pattern we kept returning to: **never rely on a single point of enforcement.** The SQL validator catches what the LLM shouldn't have written; the IAM role catches it again even if the validator has a bug; the dry run catches wrong SQL before it costs anything; the cost guard catches expensive SQL even if it's technically correct. Wherever there are two independent layers doing the same job in different ways (app-layer check + infra-layer enforcement), that's deliberate — one is allowed to fail without the whole system failing with it.

Want me to turn this into an actual **eval checklist artifact** — concrete test questions covering each of these edge cases — so you have something to literally run against your MVP before considering it production-ready?