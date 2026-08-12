# Domain Tagging & Summaries — NBFC MVP Schema (v2)

Covers 26 tables across 10 systems/datasets.

**What changed from v1:** every summary below now includes an explicit boundary
statement ("not the same as X, because Y") against its most easily-confused
neighbor domain. This matters more now than under pure embedding matching: an
LLM classifying a question against all 18 domains at once uses these boundary
statements as active disambiguation rules, not just descriptive color. The
`incentive` summary's `loan` connection is now also reflected in its actual
tags (see `domain_tags.yaml` v2 — `incentive_payouts` now carries
`[incentive, hr, loan]`, not just `[incentive, hr]`).

## 1. Domain Summaries

### `kyc`
Identity verification and customer onboarding data — the documents and checks
that establish who a customer is before they're allowed to transact. Covers
PAN, Aadhaar, and other ID document submission and verification status.
Almost every regulatory question ("how many customers have unverified KYC")
joins through here. **Not the same as `compliance`** — KYC is the onboarding
check itself; compliance is what happens when something's flagged as wrong.
**Tables:** customers, kyc_documents

### `ops`
General operational master data everything else hangs off of — branches, base
customer records, and the loan product catalog. These tables have no
interesting business logic of their own; they're the anchor points every
other domain joins against. Not a domain anyone asks a standalone question
about — it's almost always pulled in via relationship expansion from another
domain, not matched directly.
**Tables:** branches, customers, employees, loan_products

### `hr`
Employee lifecycle and personnel data — role, designation, department,
tenure, performance ratings, and compensation-adjacent records. Spans two
systems (the core `employees` table and the richer Zoho People HR extract)
that share `employee_id` in this MVP; a real integration would likely need
entity resolution between them. **Not the same as `incentive`** — HR is who
someone is and how they're rated; incentive is what they were actually paid.
**Tables:** employees, incentive_payouts, zoho_employee_records

### `loan`
The center of gravity for an NBFC: applications, disbursed loans,
amortization schedules, and payments. Covers requested vs. disbursed
amounts, interest rates, tenure, EMI (equated monthly installment)
schedules, and loan status (active, closed, NPA — non-performing asset —
or written off). Most cross-domain questions (collections, insurance,
incentives) ultimately trace back to a loan_id here. **Not the same as
`treasury`** — loan is money going out to customers; treasury is where the
company's own lending capital comes from.
**Tables:** customer_risk_scores, emi_schedule, loan_applications,
loan_products, loans, overdue_accounts, payments, incentive_payouts

### `risk`
Credit risk and compliance risk signals — customer risk scoring at
origination, and compliance flags raised later in a loan's life.
Distinguishing `risk` from plain `loan` matters because risk questions
("what's our NPA rate by risk category") need a different join path than
servicing questions. **Not the same as `compliance`** — risk is a
score/signal computed at origination; compliance is an investigation or
regulatory action taken later.
**Tables:** compliance_flags, customer_risk_scores

### `collections`
Recovery activity on loans that have gone overdue — DPD (days past due)
tracking and the actions (calls, field visits, legal notices) taken to
recover them. Tagged separately from `loan` because collections questions
almost always filter to a subset of loans (overdue ones) rather than the
whole book. **Not the same as `support`** — collections is the NBFC
contacting the customer about non-payment; support is the customer
contacting the NBFC about something else entirely.
**Tables:** collections_activity, overdue_accounts

### `incentive`
Employee compensation tied to performance — payouts to loan officers and
staff for loan sourcing, collections recovery, cross-sell, and retention.
Bridges `hr` and `loan`, since a payout only makes sense in the context of
both who earned it and what loan or activity earned it. **Not the same as
`hr` alone** — incentive is the money paid out; HR is the person's role and
record.
**Tables:** incentive_payouts

### `leads`
Pre-conversion pipeline — people who haven't become customers yet, and every
touchpoint with them. Distinct from `loan`/`kyc` domains because a lead has
no guaranteed link to a real customer until (and unless) they convert.
**Not the same as `marketing`** — leads are individual people and their
status; marketing is the campaign-level activity that generated them.
**Tables:** campaign_responses, campaigns, lead_activities, leads

### `marketing`
Campaign-level planning and response data — budget, targeting, channel
performance, impressions, and conversion rates, one level up from any
individual lead's journey. Useful for ROI and cost-per-acquisition
questions that don't care about any single lead. **Not the same as
`sales`** — marketing is the campaign's own performance; sales is what a
rep did with the leads it produced.
**Tables:** campaign_responses, campaigns

### `sales`
The sales-rep-facing side of lead conversion — activity logs and
assignment, as opposed to marketing's campaign-level view. Split from
`marketing` since sales questions ("which rep has the best conversion
rate") need employee-level joins that campaign-level tables don't support.
**Not the same as `leads` alone** — sales is what an employee did; leads is
the person being acted on.
**Tables:** lead_activities, leads

### `treasury`
The NBFC's own borrowing — where its lending capital comes from (bank
loans, NCDs, securitization, commercial paper) and the cash flows against
those facilities (drawdowns, interest payments, principal repayment).
Deliberately has no FK into `loan`; it's a balance-sheet-liability domain,
not a customer-facing one. **Not the same as `loan`** — treasury is money
coming into the company from lenders; loan is money going out to customers.
**Tables:** funding_sources, treasury_transactions

### `finance`
Overlaps with `treasury` here (both tags applied to the same two tables) —
used when a question is really about cost of funds, cash flow, or balance
sheet health rather than the mechanics of a specific facility. Same
boundary as treasury: not customer-facing, no relationship into the loan
book.
**Tables:** funding_sources, treasury_transactions

### `insurance`
Loan-linked insurance products sold as cross-sell, and the claims against
them. Connects to `loan` via `loan_id` but has its own lifecycle (policy
issuance, premium, underwriting, claims) that doesn't touch LMS at all.
**Not the same as `loan`** — insurance is a separate product attached to a
loan, not the loan itself.
**Tables:** insurance_claims, insurance_policies

### `cross_sell`
Marks tables representing non-core-lending revenue sold alongside a loan —
currently just insurance, but this tag exists so future cross-sell products
(savings accounts, cards) can be found without needing to know they're
technically filed under a different system name.
**Tables:** insurance_policies

### `compliance`
Regulatory and internal-audit-facing data — action-level audit trails and
named compliance concerns (AML watchlist, PEP checks, KYC mismatches,
duplicate PAN). This is the domain most likely to need very precise
relationship-type filtering since `audit_logs` touches every other system.
**Not the same as `risk`** — compliance is an investigation, flag, or
regulatory action; risk is a score computed at origination.
**Tables:** audit_logs, compliance_flags

### `audit`
A narrower tag than `compliance`, applied only to the raw action-log table.
Separated out because "show me the audit trail for X" is a much more
literal, mechanical query than "show me compliance risk," even though both
currently map to the same table.
**Tables:** audit_logs

### `support`
Customer-facing service interactions — tickets and the individual touches
(calls, notes, emails) that resolve them. Distinct from `collections` even
though both can involve a call to a customer, because support is
customer-initiated and collections is NBFC-initiated.
**Tables:** support_tickets, ticket_interactions

### `customer_service`
Synonym-adjacent to `support`, applied to the same two tables — kept as a
separate tag because users of the retrieval system are equally likely to
phrase a question either way ("support tickets" vs "customer service
issues"), and domain matching should catch both phrasings.
**Tables:** support_tickets, ticket_interactions

## 2. Per-Table Domain Tags (by system)

### Base Entities (`base`)
_Shared master data referenced by every downstream system (LOS, LMS, incentive, etc.)_
System-level tags: `[kyc, ops, hr, loan]` — corrected from v1 (was `[kyc, ops]`,
missing `hr` from `employees` and `loan` from `loan_products`).

| Table | Domain Tags |
|---|---|
| branches | `ops` |
| employees | `hr`, `ops` |
| customers | `kyc`, `ops` |
| loan_products | `loan`, `ops` |

### LOS (`los`)
_Loan Origination System — applications, underwriting decisions, before disbursement_
System-level tags: `[loan, kyc, risk]` — corrected from v1 (was `[loan]`,
missing `kyc` from `kyc_documents` and `risk` from `customer_risk_scores`).

| Table | Domain Tags |
|---|---|
| loan_applications | `loan` |
| kyc_documents | `kyc` |
| customer_risk_scores | `loan`, `risk` |

### LMS (`lms`)
_Loan Management System — disbursed loans, repayment schedules, collections_

| Table | Domain Tags |
|---|---|
| loans | `loan` |
| emi_schedule | `loan` |
| payments | `loan` |
| overdue_accounts | `collections`, `loan` |
| collections_activity | `collections` |

### Incentive Engine (`incentive`)
_Employee incentive/payout calculations tied to loan sourcing and collections performance_

| Table | Domain Tags |
|---|---|
| incentive_payouts | `incentive`, `hr`, `loan` — **corrected from v1** (was missing `loan` despite the summary text always having claimed this domain "bridges hr and loan") |

### Zoho People (`zoho`)
_HR/employee master data from Zoho People. Modeled here as sharing employee_id
with the core employees table for MVP simplicity — in a real integration this
system would likely have its own ID space with no clean shared key, which is
exactly the kind of gap entity resolution would need to close before this
could join cleanly against `employees`._
System-level tags: `[hr]` — corrected from v1 (was `[hr, ops]`; nothing in
this system's actual columns is operational/branch data, so `ops` was dropped
rather than justified).

| Table | Domain Tags |
|---|---|
| zoho_employee_records | `hr` |

### CRM (`crm`)
_Lead generation, campaign management, and pre-conversion customer engagement_

| Table | Domain Tags |
|---|---|
| campaigns | `marketing`, `leads` |
| leads | `leads`, `sales` |
| lead_activities | `leads`, `sales` |
| campaign_responses | `marketing`, `leads` |

### Treasury (`treasury`)
_Funding sources and treasury-level cash flow transactions backing loan disbursements_

| Table | Domain Tags |
|---|---|
| funding_sources | `treasury`, `finance` |
| treasury_transactions | `treasury`, `finance` |

### Insurance (`insurance`)
_Loan-linked insurance policies and claims (credit life / asset cover cross-sell)_

| Table | Domain Tags |
|---|---|
| insurance_policies | `insurance`, `cross_sell` |
| insurance_claims | `insurance` |

### Compliance (`compliance`)
_Audit logs and regulatory compliance flags across lending operations_

| Table | Domain Tags |
|---|---|
| audit_logs | `compliance`, `audit` |
| compliance_flags | `compliance`, `risk` |

### Customer Support (`support`)
_Support ticketing and customer service interactions across the loan lifecycle_

| Table | Domain Tags |
|---|---|
| support_tickets | `support`, `customer_service` |
| ticket_interactions | `support`, `customer_service` |

## 3. All Domains, Alphabetical

`audit`, `collections`, `compliance`, `cross_sell`, `customer_service`,
`finance`, `hr`, `incentive`, `insurance`, `kyc`, `leads`, `loan`,
`marketing`, `ops`, `risk`, `sales`, `support`, `treasury`

## 4. Summary of Fixes Applied in v2

1. **`incentive_payouts` domain tags** — added `loan` (was `[incentive, hr]`,
   now `[incentive, hr, loan]`), since it holds a direct `loan_id` FK and the
   summary text always described it as bridging both domains.
2. **`00_base.yaml` system-level tags** — corrected to `[kyc, ops, hr, loan]`
   to match the actual union of its tables' tags.
3. **`01_los.yaml` system-level tags** — corrected to `[loan, kyc, risk]` to
   match the actual union of its tables' tags.
4. **`04_zoho.yaml` system-level tags** — corrected to `[hr]`, dropping the
   unjustified `ops` tag.
5. **Every domain summary** — added an explicit "not the same as X, because
   Y" boundary sentence against its nearest-neighbor domain, to give the
   LLM-based domain classifier (rather than pure embedding distance) an
   explicit disambiguation rule to reason with.
6. **`loan` domain's table list** — now explicitly includes `incentive_payouts`,
   matching fix #1.
