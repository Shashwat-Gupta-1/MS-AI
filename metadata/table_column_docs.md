# Table & Column Documentation — NBFC MVP Schema (v2)

Covers 26 tables across 10 systems. **What changed from v1:** every categorical column now inlines its actual value set (pulled directly from the generator YAMLs, not just described in prose), every numeric column states its realistic range, and 11 primary-key columns that were mislabeled as self-referential foreign keys in v1 have been corrected. `same_as_ref` columns (e.g. `loans.customer_id`) now resolve to their true semantic FK target instead of the intermediate copy-source table.

## Base Entities (`base`)

### `branches`
Physical branch locations the NBFC operates from — the geographic anchor for employees, loans, and campaigns.

| Column | Description |
|---|---|
| `branch_id` | Primary key — uniquely identifies each row in this table. |
| `branch_name` | Display name of the branch, typically the city it's located in plus 'Branch'. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `state` | Indian state associated with the record. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |

### `employees`
All staff across every role (loan officers, collections agents, branch managers, sales reps, KYC officers), each attached to a home branch.

| Column | Description |
|---|---|
| `employee_id` | Primary key — uniquely identifies each row in this table. |
| `name` | Full name of the person this record represents. |
| `role` | Job function — loan_officer, collections_agent, branch_manager, sales_rep, or kyc_officer. One of: loan_officer, collections_agent, branch_manager, sales_rep, kyc_officer. |
| `branch_id` | Foreign key to `branches` — the branch this record is associated with. Foreign key into `branches`. |
| `joined_date` | Date the employee joined the NBFC. Date, ranging 2019-01-01 to 2026-06-01. |

### `customers`
Master record for every borrower — one row per real person, referenced by nearly every other table in the schema.

| Column | Description |
|---|---|
| `customer_id` | Primary key — uniquely identifies each row in this table. |
| `name` | Full name of the person this record represents. |
| `dob` | Customer's date of birth. Date, ranging 1960-01-01 to 2005-01-01. |
| `pan_number` | Permanent Account Number — India's tax ID, used as a unique identity check. |
| `phone` | Contact phone number, in local (non-formatted) digits. |
| `city` | City associated with the record. |
| `state` | Indian state associated with the record. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |
| `occupation` | Customer's stated occupation category, used in credit assessment. One of: salaried, self_employed, business_owner, farmer. |
| `income_band` | Customer's self-declared annual income bracket. One of: 0-3L, 3-6L, 6-12L, 12L+. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2020-01-01 to 2026-08-01. |

### `loan_products`
The catalog of loan types the NBFC offers (gold, personal, vehicle, business, microfinance) and their amount bands.

| Column | Description |
|---|---|
| `product_id` | Primary key — uniquely identifies each row in this table. |
| `loan_type` | The kind of loan this product represents (gold, personal, vehicle, business, microfinance). One of: gold, personal, vehicle, business, microfinance. |
| `min_amount` | Minimum loan amount allowed under this product. Numeric, uniformly ranging 10000–20000. |
| `max_amount` | Maximum loan amount allowed under this product. Numeric, uniformly ranging 500000–2000000. |

## LOS (`los`)

### `loan_applications`
Every loan application submitted, whether it was later approved, rejected, or is still pending — the entry point into the lending funnel.

| Column | Description |
|---|---|
| `application_id` | Primary key — uniquely identifies each row in this table. |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers`. |
| `product_id` | Foreign key to `loan_products` — the loan product involved. Foreign key into `loan_products`. |
| `branch_id` | Foreign key to `branches` — the branch this record is associated with. Foreign key into `branches`. |
| `requested_amount` | Amount the customer requested at time of application. Numeric, roughly centered around 250000 (stddev 90000), bounded [15000, -]. |
| `application_date` | Date the application was submitted. Date, ranging 2023-01-01 to 2026-08-01. |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: approved, rejected, pending. |
| `rejection_reason` | Reason the application was rejected; null unless status is 'rejected'. One of: low_credit_score, income_mismatch, incomplete_kyc, high_existing_debt (null unless status != rejected). |

### `kyc_documents`
Identity documents submitted per customer (PAN, Aadhaar, Passport, Voter ID) and their verification status.

| Column | Description |
|---|---|
| `kyc_id` | Primary key — uniquely identifies each row in this table. |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers`. |
| `doc_type` | Type of identity document submitted. One of: PAN, Aadhaar, Passport, Voter_ID. |
| `verification_status` | Whether the document has been verified, is pending, or was rejected. One of: verified, pending, rejected. |
| `verified_at` | Date the document verification was completed. Date, ranging 2020-01-01 to 2026-08-01. |

### `customer_risk_scores`
Credit risk scoring snapshots per customer, used at underwriting time to inform the approval decision.

| Column | Description |
|---|---|
| `score_id` | Primary key — uniquely identifies each row in this table. |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers`. |
| `credit_score` | Numeric credit score at time of assessment (roughly 300-900 scale). Numeric, roughly centered around 680 (stddev 90), bounded [300, 900]. |
| `risk_category` | Bucketed risk tier derived from the credit score — low, medium, or high. One of: low, medium, high. |
| `scored_at` | Date this risk score was calculated. Date, ranging 2023-01-01 to 2026-08-01. |

## LMS (`lms`)

### `loans`
Disbursed loans only — the subset of approved applications that actually converted into live loan accounts.

| Column | Description |
|---|---|
| `loan_id` | Primary key — uniquely identifies each row in this table. |
| `application_id` | Foreign key to `loan_applications` — the originating application. Foreign key into `loan_applications` (restricted to status=approved). |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers` — value is carried through from `loan_applications` at generation time via `application_id`, not sampled independently, so it always stays consistent with it. |
| `product_id` | Foreign key to `loan_products` — the loan product involved. Foreign key into `loan_products` — value is carried through from `loan_applications` at generation time via `application_id`, not sampled independently, so it always stays consistent with it. |
| `branch_id` | Foreign key to `branches` — the branch this record is associated with. Foreign key into `branches` — value is carried through from `loan_applications` at generation time via `application_id`, not sampled independently, so it always stays consistent with it. |
| `disbursed_amount` | Actual principal amount disbursed to the customer. Numeric, roughly centered around 240000 (stddev 85000), bounded [15000, -]. |
| `interest_rate` | Annual interest rate applied to this loan, in percent. Numeric, uniformly ranging 8–24. |
| `tenure_months` | Loan tenure in months, used to compute the amortization schedule. One of: 12, 24, 36, 48, 60. |
| `disbursement_date` | Date the loan amount was disbursed to the customer. Date, ranging 2023-01-15 to 2026-07-01. |
| `status` | Current loan status — active, closed, npa (non-performing), or written_off. One of: active, closed, npa, written_off. |

### `emi_schedule`
The full reducing-balance amortization schedule, one row per EMI installment per loan — the ground truth for what's owed and when.

| Column | Description |
|---|---|

### `payments`
EMIs that have actually been paid, with realistic on-time/late/missed timing derived from each loan's status.

| Column | Description |
|---|---|

### `overdue_accounts`
One row per loan currently overdue, aggregating unpaid EMIs past their due date into a days-past-due (DPD) bucket.

| Column | Description |
|---|---|

### `collections_activity`
Recovery actions taken against overdue loans — calls, field visits, legal notices — and their outcomes.

| Column | Description |
|---|---|
| `activity_id` | Unique identifier (primary key) for this row. |
| `loan_id` | Foreign key to `loans` — the disbursed loan this record relates to. Foreign key into `overdue_accounts`. |
| `employee_id` | Foreign key to `employees` — the staff member associated with this record. Foreign key into `employees` (restricted to role=collections_agent). |
| `activity_type` | Type of recovery action taken — call, field visit, legal notice, or SMS reminder. One of: call, field_visit, legal_notice, sms_reminder. |
| `activity_date` | Date the collections activity took place. Date, ranging 2024-01-01 to 2026-08-01. |
| `outcome` | Result of the collections activity — promised to pay, no response, paid, or disputed. One of: promised_to_pay, no_response, paid, disputed. |

## Incentive Engine (`incentive`)

### `incentive_payouts`
Monthly incentive/bonus payouts to loan officers, tied to loan sourcing, collections, cross-sell, or retention performance.

| Column | Description |
|---|---|
| `incentive_id` | Primary key — uniquely identifies each row in this table. |
| `employee_id` | Foreign key to `employees` — the staff member associated with this record. Foreign key into `employees` (restricted to role=loan_officer). |
| `loan_id` | Foreign key to `loans` — the disbursed loan this record relates to. Foreign key into `loans`. |
| `incentive_type` | Category of incentive being paid — loan sourcing, collections bonus, cross-sell, or retention. One of: loan_sourcing, collections_bonus, cross_sell, retention. |
| `period_month` | The month this incentive payout covers. Date, ranging 2024-01-01 to 2026-07-01. |
| `base_amount` | Fixed base incentive amount before bonuses or deductions. Numeric, roughly centered around 8000 (stddev 2500), bounded [500, -]. |
| `bonus_amount` | Variable bonus added on top of the base incentive. Numeric, uniformly ranging 0–6000. |
| `deduction_amount` | Amount deducted from the incentive, e.g. for policy violations or clawbacks. Numeric, uniformly ranging 0–1500. |
| `payout_status` | Whether the incentive has been paid, is pending, or is on hold. One of: paid, pending, hold. |
| `payout_date` | Date the incentive was (or is scheduled to be) paid out. Date, ranging 2024-01-05 to 2026-08-01. |

## Zoho People (`zoho`)

### `zoho_employee_records`
HR master data synced from Zoho People — designation, department, joining date, and performance rating per employee.

| Column | Description |
|---|---|
| `zoho_record_id` | Primary key — uniquely identifies each row in this table. |
| `employee_id` | Foreign key to `employees` — the staff member associated with this record. Foreign key into `employees`. |
| `designation` | Job title/level in the HR system, distinct from the operational `role` field in `employees`. One of: associate, senior_associate, team_lead, assistant_manager, manager. |
| `department` | HR department the employee is assigned to. One of: sales, collections, operations, credit, hr. |
| `date_of_joining` | Joining date as recorded in Zoho (should align with `employees.joined_date`). Date, ranging 2019-01-01 to 2026-06-01. |
| `employment_type` | Full-time, contract, or intern. One of: full_time, contract, intern. |
| `reporting_manager` | Name of the employee's manager, as recorded in Zoho. |
| `work_location` | City the employee is based out of for HR purposes. |
| `leave_balance_days` | Number of paid leave days remaining for the employee. Numeric, uniformly ranging 0–30. |
| `performance_rating` | Latest performance rating on a 1-5 scale (stored as text). One of: 1, 2, 3, 4, 5. |

## CRM (`crm`)

### `campaigns`
Marketing campaigns run to generate loan leads — budget, channel, targeting, and performance-to-target at the campaign level.

| Column | Description |
|---|---|
| `campaign_id` | Primary key — uniquely identifies each row in this table. |
| `campaign_name` | Human-readable name of the marketing campaign. One of: Diwali Gold Loan Push, Monsoon Personal Loan, Vehicle Loan Blitz, SME Growth Drive, Digital First-Time Borrower, Referral Rewards, New Year Cashback, Farm Credit Outreach. |
| `channel` | Primary channel the campaign runs through — digital, referral, branch walk-in, or telecalling. One of: digital, referral, branch_walkin, telecalling. |
| `campaign_type` | Strategic purpose of the campaign — awareness, acquisition, retention, or cross-sell. One of: awareness, acquisition, retention, cross_sell. |
| `product_id` | Foreign key to `loan_products` — the loan product involved. Foreign key into `loan_products`. |
| `target_region` | Region the campaign is targeted at. One of: North, South, East, West, Central. |
| `target_state` | State the campaign is targeted at. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |
| `start_date` | Date the campaign begins. Date, ranging 2023-01-01 to 2026-06-01. |
| `end_date` | Date the campaign ends (or is scheduled to end). Date, ranging 2023-02-01 to 2026-08-01. |
| `budget_allocated` | Total budget approved for the campaign. Numeric, roughly centered around 500000 (stddev 150000), bounded [20000, -]. |
| `budget_spent` | Actual spend to date against the allocated budget. Numeric, roughly centered around 420000 (stddev 140000), bounded [0, -]. |
| `leads_target` | Number of leads the campaign is targeted to generate. Numeric, uniformly ranging 200–5000. |
| `impressions` | Total ad/content impressions generated by the campaign. Numeric, uniformly ranging 10000–2000000. |
| `clicks` | Total clicks generated by the campaign. Numeric, uniformly ranging 500–100000. |
| `conversion_rate_target` | Target conversion rate (%) the campaign is expected to hit. Numeric, uniformly ranging 1–15. |
| `cost_per_lead` | Average cost incurred per lead generated. Numeric, roughly centered around 150 (stddev 60), bounded [10, -]. |
| `campaign_manager_id` | Foreign key to `employees` (sales_rep) — the person managing this campaign. Foreign key into `employees` (restricted to role=sales_rep). |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: active, completed, paused. |
| `priority` | Relative priority/urgency assigned to this record. One of: high, medium, low. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-06-01. |

### `leads`
Prospective customers captured through a campaign or other channel, before (or instead of) converting into an actual borrower.

| Column | Description |
|---|---|
| `lead_id` | Primary key — uniquely identifies each row in this table. |
| `campaign_id` | Foreign key to `campaigns` — the marketing campaign this record is tied to. Foreign key into `campaigns`. |
| `lead_name` | Name of the prospective customer. |
| `phone` | Contact phone number, in local (non-formatted) digits. |
| `city` | City associated with the record. |
| `state` | Indian state associated with the record. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |
| `source_channel` | Channel the lead originated from — digital, referral, branch walk-in, or telecalling. One of: digital, referral, branch_walkin, telecalling. |
| `product_id` | Foreign key to `loan_products` — the loan product involved. Foreign key into `loan_products`. |
| `requested_amount_interest` | Approximate loan amount the lead has expressed interest in. Numeric, roughly centered around 220000 (stddev 90000), bounded [10000, -]. |
| `lead_score` | Numeric score (0-100) indicating how promising this lead is, used for prioritization. Numeric, uniformly ranging 0–100. |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: new, contacted, qualified, converted, dropped. |
| `assigned_employee_id` | Foreign key to `employees` (sales_rep) — who is working this lead. Foreign key into `employees` (restricted to role=sales_rep). |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |
| `last_contacted_at` | Date of the most recent contact attempt with this lead. Date, ranging 2023-01-02 to 2026-08-01. |
| `follow_up_count` | Number of follow-up attempts made with this lead so far. Numeric, uniformly ranging 0–12. |
| `conversion_probability` | Modeled probability (0-1) that this lead converts into a customer. Numeric, uniformly ranging 0–1. |
| `age_band` | Age bracket of the lead. One of: 18-25, 26-35, 36-45, 46-60, 60+. |
| `occupation` | Lead's stated occupation category. One of: salaried, self_employed, business_owner, farmer. |
| `income_band` | Lead's self-declared income bracket. One of: 0-3L, 3-6L, 6-12L, 12L+. |
| `is_existing_customer` | Whether this 'lead' is actually an existing customer being cross-sold to. One of: yes, no. |

### `lead_activities`
Every individual touchpoint (call, SMS, email, branch visit) a sales rep has with a lead, and its outcome.

| Column | Description |
|---|---|
| `activity_id` | Primary key — uniquely identifies each row in this table. |
| `lead_id` | Foreign key to `leads` — the prospective customer this record relates to. Foreign key into `leads`. |
| `employee_id` | Foreign key to `employees` — the staff member associated with this record. Foreign key into `employees` (restricted to role=sales_rep). |
| `activity_type` | Type of touchpoint — call, SMS, email, WhatsApp, or branch visit. One of: call, sms, email, whatsapp, branch_visit. |
| `activity_date` | Date the activity took place. Date, ranging 2023-01-01 to 2026-08-01. |
| `outcome` | Result of the activity — interested, not interested, callback requested, no answer, or converted. One of: interested, not_interested, callback_requested, no_answer, converted. |
| `duration_minutes` | Length of the interaction, in minutes. Numeric, uniformly ranging 1–45. |
| `channel_cost` | Cost incurred to carry out this specific activity. Numeric, roughly centered around 20 (stddev 8), bounded [0, -]. |
| `sentiment_score` | Sentiment of the interaction, from -1 (negative) to 1 (positive). Numeric, uniformly ranging -1–1. |
| `follow_up_scheduled` | Whether a follow-up has been scheduled as a result of this activity. One of: yes, no. |
| `priority` | Relative priority/urgency assigned to this record. One of: high, medium, low. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `device_type` | Device the lead used, if the activity was digital. One of: mobile, desktop, tablet, in_person. |
| `agent_notes_flag` | Categorical value for agent notes flag. One of: yes, no. |
| `time_of_day` | Part of day the activity occurred. One of: morning, afternoon, evening, night. |
| `day_of_week_type` | Whether the activity happened on a weekday or weekend. One of: weekday, weekend. |
| `attempt_number` | Which numbered contact attempt this is for this lead. Numeric, uniformly ranging 1–8. |
| `resulted_in_lead_status_change` | Whether this activity caused the lead's status field to change. One of: yes, no. |
| `escalated` | Whether this activity was escalated to a supervisor. One of: yes, no. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |

### `campaign_responses`
Discrete response events to a campaign (a click, a form submit, a branch walk-in) tied back to both the campaign and the lead who responded.

| Column | Description |
|---|---|
| `response_id` | Primary key — uniquely identifies each row in this table. |
| `campaign_id` | Foreign key to `campaigns` — the marketing campaign this record is tied to. Foreign key into `campaigns`. |
| `lead_id` | Foreign key to `leads` — the prospective customer this record relates to. Foreign key into `leads`. |
| `response_channel` | How the lead responded — SMS link, email click, callback, form submit, or branch visit. One of: sms_link, email_click, call_back, form_submit, branch_visit. |
| `response_date` | Date of the response event. Date, ranging 2023-01-01 to 2026-08-01. |
| `engagement_score` | Numeric measure (0-100) of how engaged the response was. Numeric, uniformly ranging 0–100. |
| `clicked` | Whether the lead clicked through on the campaign content. One of: yes, no. |
| `converted` | Whether this specific response ultimately led to a conversion. One of: yes, no. |
| `device_type` | Device used to respond to the campaign. One of: mobile, desktop, tablet. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `time_to_respond_hours` | Hours elapsed between the campaign touch and the lead's response. Numeric, uniformly ranging 0–240. |
| `bounce_flag` | Whether the response bounced immediately (e.g. landing page exit with no engagement). One of: yes, no. |
| `form_completion_pct` | Percentage of a lead-capture form the respondent completed. Numeric, uniformly ranging 0–100. |
| `ab_test_variant` | Which A/B test variant (A, B, or control) this response belongs to. One of: A, B, control. |
| `cost_attributed` | Marketing cost attributed to this individual response. Numeric, roughly centered around 80 (stddev 30), bounded [0, -]. |
| `referral_source` | Traffic source the response is attributed to. One of: organic, paid_search, social, sms, email, field_agent. |
| `utm_source_flag` | Whether the response carried UTM tracking parameters. One of: yes, no. |
| `session_duration_seconds` | Length of the digital session associated with the response. Numeric, uniformly ranging 5–1800. |
| `repeat_response` | Whether this lead has responded to a campaign before. One of: yes, no. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |

## Treasury (`treasury`)

### `funding_sources`
The NBFC's own borrowing facilities (bank term loans, NCDs, securitization, etc.) that fund the loans it disburses to customers.

| Column | Description |
|---|---|
| `funding_source_id` | Primary key — uniquely identifies each row in this table. |
| `source_name` | Name/label of the specific borrowing facility. One of: Bank Term Loan, NCD Issuance, Commercial Paper, ECB, Securitization, Equity Infusion, Subordinated Debt, Bank Cash Credit. |
| `source_type` | Category of funding — bank loan, market borrowing, securitization, or equity. One of: bank_loan, market_borrowing, securitization, equity. |
| `lender_name` | Name of the bank or institution providing this facility. |
| `sanctioned_amount` | Total amount sanctioned under this facility. Numeric, roughly centered around 50000000 (stddev 20000000), bounded [1000000, -]. |
| `drawn_amount` | Amount actually drawn down so far against the sanctioned limit. Numeric, roughly centered around 40000000 (stddev 18000000), bounded [0, -]. |
| `interest_rate` | Interest rate the NBFC pays on this borrowing, in percent. Numeric, uniformly ranging 6–13. |
| `tenure_years` | Tenure of the facility, in years. Numeric, uniformly ranging 1–10. |
| `sanction_date` | Date the facility was sanctioned. Date, ranging 2021-01-01 to 2026-06-01. |
| `maturity_date` | Date the facility matures / is due for full repayment. Date, ranging 2026-06-02 to 2033-01-01. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `state` | Indian state associated with the record. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |
| `credit_rating` | Credit rating associated with this borrowing (or the NBFC's rating at the time). One of: AAA, AA+, AA, A+, A, BBB+. |
| `collateral_type` | What secures this facility, if anything. One of: loan_receivables, fixed_deposit, property, unsecured. |
| `repayment_frequency` | How often repayments are due — monthly, quarterly, or bullet (lump sum at maturity). One of: monthly, quarterly, bullet. |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: active, closed, defaulted. |
| `relationship_manager` | Name of the relationship manager on the lender's side. |
| `processing_fee` | One-time fee paid to set up this facility. Numeric, roughly centered around 250000 (stddev 100000), bounded [0, -]. |
| `covenant_breach_flag` | Whether any loan covenant on this facility has been breached. One of: yes, no. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2021-01-01 to 2026-06-01. |

### `treasury_transactions`
Cash flow events against a funding source — drawdowns, interest payments, principal repayments, fees.

| Column | Description |
|---|---|
| `transaction_id` | Primary key — uniquely identifies each row in this table. |
| `funding_source_id` | Foreign key to `funding_sources` — the borrowing facility this transaction is against. Foreign key into `funding_sources`. |
| `transaction_type` | Nature of the cash flow — drawdown, interest payment, principal repayment, or fee payment. One of: drawdown, interest_payment, principal_repayment, fee_payment. |
| `transaction_date` | Date the transaction occurred. Date, ranging 2021-01-01 to 2026-08-01. |
| `amount` | Transaction amount. Numeric, roughly centered around 1500000 (stddev 800000), bounded [1000, -]. |
| `currency` | Currency of the transaction (INR for all records here). One of: INR. |
| `settlement_mode` | How the transaction was settled — RTGS, NEFT, or internal transfer. One of: rtgs, neft, internal_transfer. |
| `approved_by` | Name of the person who approved the transaction. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `book_balance_after` | Outstanding book balance on the facility immediately after this transaction. Numeric, roughly centered around 35000000 (stddev 15000000), bounded [0, -]. |
| `reconciliation_status` | Whether the transaction has been reconciled against bank statements. One of: reconciled, pending, flagged. |
| `value_date` | Value date for interest/accounting purposes (may differ from transaction_date). Date, ranging 2021-01-01 to 2026-08-01. |
| `counterparty_bank` | Bank on the other side of this transaction. |
| `interest_component` | Portion of this transaction that is interest, where applicable. Numeric, roughly centered around 80000 (stddev 40000), bounded [0, -]. |
| `principal_component` | Portion of this transaction that is principal, where applicable. Numeric, roughly centered around 900000 (stddev 500000), bounded [0, -]. |
| `is_intercompany` | Whether this transaction is between related/group entities. One of: yes, no. |
| `processed_by_system` | System of record that processed this transaction. One of: core_treasury, manual_entry, batch_upload. |
| `audit_flag` | Whether this transaction has been flagged for audit review. One of: yes, no. |
| `narration_code` | Short internal code describing the transaction purpose. One of: DRWDN, INTPMT, PRINRPY, FEEPMT. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2021-01-01 to 2026-08-01. |

## Insurance (`insurance`)

### `insurance_policies`
Loan-linked insurance policies sold as cross-sell (credit life, asset cover, health riders) at or after loan disbursement.

| Column | Description |
|---|---|
| `policy_id` | Primary key — uniquely identifies each row in this table. |
| `loan_id` | Foreign key to `loans` — the disbursed loan this record relates to. Foreign key into `loans`. |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers` — value is carried through from `loans` at generation time via `loan_id`, not sampled independently, so it always stays consistent with it. |
| `policy_type` | Type of cover — credit life, asset cover, or health rider. One of: credit_life, asset_cover, health_rider. |
| `insurer_name` | Name of the insurance company underwriting the policy. |
| `sum_assured` | Total amount the policy pays out on a valid claim. Numeric, roughly centered around 250000 (stddev 90000), bounded [10000, -]. |
| `premium_amount` | Premium amount charged for this policy. Numeric, roughly centered around 3500 (stddev 1500), bounded [200, -]. |
| `premium_frequency` | How the premium is paid — single, annual, or monthly. One of: single, annual, monthly. |
| `policy_start_date` | Date the policy coverage begins. Date, ranging 2023-01-01 to 2026-08-01. |
| `policy_end_date` | Date the policy coverage ends. Date, ranging 2024-01-01 to 2031-08-01. |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: active, lapsed, matured, cancelled. |
| `sold_by_employee_id` | Foreign key to `employees` (loan_officer) — who sold this policy. Foreign key into `employees` (restricted to role=loan_officer). |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `state` | Indian state associated with the record. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |
| `nominee_relation` | Relationship of the policy nominee to the insured customer. One of: spouse, parent, child, sibling. |
| `underwriting_decision` | Outcome of underwriting review — accepted, accepted with loaded premium, or declined. One of: accepted, loaded_premium, declined. |
| `commission_amount` | Commission earned by the NBFC/employee for selling this policy. Numeric, roughly centered around 400 (stddev 150), bounded [0, -]. |
| `renewal_due` | Whether this policy is due for renewal. One of: yes, no. |
| `digital_issuance` | Whether the policy was issued digitally (vs. paper-based). One of: yes, no. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |

### `insurance_claims`
Claims filed against an insurance policy, their investigation status, and settlement outcome.

| Column | Description |
|---|---|
| `claim_id` | Primary key — uniquely identifies each row in this table. |
| `policy_id` | Foreign key to `insurance_policies` — the policy this record relates to. Foreign key into `insurance_policies`. |
| `claim_type` | Nature of the claim — death, disability, critical illness, or asset damage. One of: death, disability, critical_illness, asset_damage. |
| `claim_amount` | Amount claimed by the policyholder/beneficiary. Numeric, roughly centered around 220000 (stddev 95000), bounded [5000, -]. |
| `claim_filed_date` | Date the claim was filed. Date, ranging 2023-06-01 to 2026-08-01. |
| `claim_status` | Current status of the claim — approved, pending, rejected, or under review. One of: approved, pending, rejected, under_review. |
| `rejection_reason` | Reason the claim was rejected; null unless claim_status is 'rejected'. One of: documentation_incomplete, policy_lapsed, exclusion_clause (null unless claim_status != rejected). |
| `settlement_amount` | Amount actually paid out on the claim. Numeric, roughly centered around 190000 (stddev 90000), bounded [0, -]. |
| `settlement_date` | Date the claim was settled. Date, ranging 2023-07-01 to 2026-08-01. |
| `processed_by` | Name of the person who processed the claim. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `turnaround_days` | Number of days from filing to settlement/rejection. Numeric, uniformly ranging 1–120. |
| `documentation_score` | Completeness score (0-100) of the documentation submitted. Numeric, uniformly ranging 0–100. |
| `investigator_assigned` | Whether a claims investigator was assigned to this case. One of: yes, no. |
| `fraud_flag` | Whether the claim was flagged as potentially fraudulent. One of: yes, no. |
| `appeal_filed` | Whether the claimant filed an appeal against the decision. One of: yes, no. |
| `customer_satisfaction_score` | Customer's satisfaction rating (1-5) with the claims process. Numeric, uniformly ranging 1–5. |
| `channel_reported` | Channel the claim was originally reported through. One of: branch, call_center, app, agent. |
| `payout_mode` | How the settlement was paid out — NEFT, cheque, or adjusted against the loan. One of: neft, cheque, loan_adjustment. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-06-01 to 2026-08-01. |

## Compliance (`compliance`)

### `audit_logs`
System-wide action-level audit trail — every create/update/delete/view performed by an employee, across every source system.

| Column | Description |
|---|---|
| `audit_id` | Primary key — uniquely identifies each row in this table. |
| `entity_type` | Type of record the audited action was performed on. One of: loan, customer, employee, branch, kyc_document. |
| `action_type` | Nature of the action — create, update, delete, or view. One of: create, update, delete, view. |
| `performed_by_employee_id` | Foreign key to `employees` — who performed the action. Foreign key into `employees`. |
| `branch_id` | Foreign key to `branches` — the branch this record is associated with. Foreign key into `branches`. |
| `action_timestamp` | When the action occurred. Date, ranging 2023-01-01 to 2026-08-01. |
| `ip_region` | Region the action was performed from, inferred from IP. One of: North, South, East, West, Central. |
| `severity` | Severity classification of the logged action. One of: low, medium, high, critical. |
| `system_source` | Which source system the action originated in. One of: LOS, LMS, CRM, Treasury, Insurance, Zoho. |
| `field_changed` | Which field was modified, for update actions. One of: status, amount, kyc_status, contact_info, role, none. |
| `old_value_flag` | Whether a prior value existed before this change (i.e. it wasn't a first-time create). One of: yes, no. |
| `session_id` | Identifier for the user session this action was part of. System-generated unique identifier. |
| `device_type` | Device type the action was performed from. One of: desktop, mobile, api. |
| `approval_required` | Whether this action required a secondary approval. One of: yes, no. |
| `approved_flag` | Whether the required approval was granted. One of: yes, no. |
| `anomaly_score` | Automated anomaly score (0-1) assigned to this action. Numeric, uniformly ranging 0–1. |
| `flagged_for_review` | Whether this specific log entry has been flagged for manual review. One of: yes, no. |
| `retention_category` | Data retention classification applied to this log entry. One of: standard, legal_hold, regulatory. |
| `log_version` | Schema version of the audit log format used to write this entry. One of: v1, v2. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |

### `compliance_flags`
Named regulatory/compliance concerns raised against a customer or loan (AML watchlist, PEP check, KYC mismatch, etc.) and their resolution.

| Column | Description |
|---|---|
| `flag_id` | Primary key — uniquely identifies each row in this table. |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers`. |
| `loan_id` | Foreign key to `loans` — the disbursed loan this record relates to. Foreign key into `loans`. |
| `flag_type` | Nature of the compliance concern — AML watchlist, PEP check, KYC mismatch, high-risk geography, or duplicate PAN. One of: aml_watchlist, pep_check, kyc_mismatch, high_risk_geography, duplicate_pan. |
| `flag_severity` | Severity of the flag. One of: low, medium, high, critical. |
| `raised_date` | Date the flag was raised. Date, ranging 2023-01-01 to 2026-08-01. |
| `resolved_date` | Date the flag was resolved, if applicable. Date, ranging 2023-01-02 to 2026-08-01. |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: open, under_investigation, resolved, escalated. |
| `investigated_by` | Name of the person who investigated the flag. |
| `regulatory_body` | External regulator the flag relates to, if any (RBI, FIU-IND), or 'internal_audit'/'none'. One of: RBI, FIU-IND, internal_audit, none. |
| `reported_externally` | Whether this flag was reported to an external regulator. One of: yes, no. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `state` | Indian state associated with the record. One of: Rajasthan, Maharashtra, Delhi, Karnataka, Gujarat, Tamil Nadu, Uttar Pradesh, West Bengal. |
| `resolution_notes_flag` | Whether resolution notes exist for this flag. One of: yes, no. |
| `recurrence_count` | Number of times a similar flag has recurred for this customer/loan. Numeric, uniformly ranging 0–5. |
| `risk_score_at_flag` | Customer's credit risk score at the time this flag was raised. Numeric, uniformly ranging 300–900. |
| `branch_id` | Foreign key to `branches` — the branch this record is associated with. Foreign key into `branches`. |
| `escalation_level` | How far up the organization this flag has been escalated. One of: branch, regional, corporate, board. |
| `sla_breach` | Whether resolution of this flag breached its SLA. One of: yes, no. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |

## Customer Support (`support`)

### `support_tickets`
Customer service tickets raised through any channel, categorized by issue type and tracked through to resolution.

| Column | Description |
|---|---|
| `ticket_id` | Primary key — uniquely identifies each row in this table. |
| `customer_id` | Foreign key to `customers` — the borrower this record belongs to. Foreign key into `customers`. |
| `loan_id` | Foreign key to `loans` — the disbursed loan this record relates to. Foreign key into `loans`. |
| `category` | Nature of the support request. One of: payment_issue, statement_request, complaint, kyc_update, closure_request, general_query. |
| `channel` | Channel the ticket was raised through. One of: call_center, app, email, branch, whatsapp. |
| `priority` | Relative priority/urgency assigned to this record. One of: low, medium, high, urgent. |
| `status` | Current lifecycle status of this record — see the table's status values for the specific set used here. One of: open, in_progress, resolved, closed. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |
| `resolved_at` | Date/time the ticket was resolved. Date, ranging 2023-01-02 to 2026-08-01. |
| `assigned_employee_id` | Assigned employee id. Foreign key into `employees`. |
| `branch_id` | Foreign key to `branches` — the branch this record is associated with. Foreign key into `branches`. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `csat_score` | Customer satisfaction score (1-5) for this ticket. Numeric, uniformly ranging 1–5. |
| `reopened_count` | Number of times this ticket was reopened after being marked resolved. Numeric, uniformly ranging 0–4. |
| `first_response_minutes` | Minutes elapsed before the first agent response. Numeric, uniformly ranging 1–1440. |
| `resolution_hours` | Total hours from creation to resolution. Numeric, uniformly ranging 0.5–240. |
| `escalated` | Whether the ticket was escalated beyond first-line support. One of: yes, no. |
| `language_preference` | Customer's preferred language for this interaction. One of: English, Hindi, Regional. |
| `sla_breach` | Whether this ticket breached its service-level agreement. One of: yes, no. |
| `sentiment` | Overall sentiment of the customer's tone across the ticket. One of: positive, neutral, negative. |

### `ticket_interactions`
Every individual interaction (note, call, email, status change) logged against a support ticket during its lifecycle.

| Column | Description |
|---|---|
| `interaction_id` | Primary key — uniquely identifies each row in this table. |
| `ticket_id` | Foreign key to `support_tickets` — the support ticket this record belongs to. Foreign key into `support_tickets`. |
| `employee_id` | Foreign key to `employees` — the staff member associated with this record. Foreign key into `employees`. |
| `interaction_type` | Nature of this interaction — note, call, email sent, status change, or customer reply. One of: note, call, email_sent, status_change, customer_reply. |
| `interaction_date` | When this interaction occurred. Date, ranging 2023-01-01 to 2026-08-01. |
| `channel` | Categorical value for channel. One of: call_center, app, email, branch, whatsapp. |
| `duration_minutes` | Length of the interaction, in minutes. Numeric, uniformly ranging 0–60. |
| `outcome` | Result of this specific interaction. One of: resolved, pending_customer, pending_internal, escalated, no_change. |
| `customer_response_flag` | Whether the customer responded as part of this interaction. One of: yes, no. |
| `internal_only` | Whether this interaction is internal-only (not visible to the customer). One of: yes, no. |
| `attachment_flag` | Whether a file was attached to this interaction. One of: yes, no. |
| `region` | Broad geographic region (North/South/East/West/Central) the record is associated with. One of: North, South, East, West, Central. |
| `shift` | Support shift (morning/evening/night) this interaction was handled in. One of: morning, evening, night. |
| `automated_flag` | Whether this interaction was generated automatically rather than by an agent. One of: yes, no. |
| `tone_flag` | Tone classification of this specific interaction. One of: neutral, positive, negative. |
| `follow_up_required` | Whether this interaction requires a follow-up. One of: yes, no. |
| `quality_score` | QA quality score (1-10) assigned to this interaction. Numeric, uniformly ranging 1–10. |
| `template_used` | Whether a canned response template was used. One of: yes, no. |
| `resolution_confidence` | Model/agent confidence (0-1) that this interaction resolves the issue. Numeric, uniformly ranging 0–1. |
| `created_at` | Timestamp when this record was first created in the source system. Date, ranging 2023-01-01 to 2026-08-01. |
