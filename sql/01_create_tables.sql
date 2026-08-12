-- STEP 1: CREATE TABLE with real inferred types (fixes prior all-STRING bug for crm/treasury/insurance/compliance/support)

CREATE TABLE `your-project.base.branches` (
  branch_id STRING,
  branch_name STRING,
  region STRING,
  state STRING
);

CREATE TABLE `your-project.base.employees` (
  employee_id STRING,
  name STRING,
  role STRING,
  branch_id STRING,
  joined_date DATE
);

CREATE TABLE `your-project.base.customers` (
  customer_id STRING,
  name STRING,
  dob DATE,
  pan_number STRING,
  phone STRING,
  city STRING,
  state STRING,
  occupation STRING,
  income_band STRING,
  created_at DATE
);

CREATE TABLE `your-project.base.loan_products` (
  product_id STRING,
  loan_type STRING,
  min_amount FLOAT64,
  max_amount FLOAT64
);

CREATE TABLE `your-project.los.loan_applications` (
  application_id STRING,
  customer_id STRING,
  product_id STRING,
  branch_id STRING,
  requested_amount FLOAT64,
  application_date DATE,
  status STRING,
  rejection_reason STRING
);

CREATE TABLE `your-project.los.kyc_documents` (
  kyc_id STRING,
  customer_id STRING,
  doc_type STRING,
  verification_status STRING,
  verified_at DATE
);

CREATE TABLE `your-project.los.customer_risk_scores` (
  score_id STRING,
  customer_id STRING,
  credit_score FLOAT64,
  risk_category STRING,
  scored_at DATE
);

CREATE TABLE `your-project.lms.loans` (
  loan_id STRING,
  application_id STRING,
  customer_id STRING,
  product_id STRING,
  branch_id STRING,
  disbursed_amount FLOAT64,
  interest_rate FLOAT64,
  tenure_months INT64,
  disbursement_date DATE,
  status STRING
);

CREATE TABLE `your-project.lms.emi_schedule` (
  emi_id STRING,
  loan_id STRING,
  installment_no INT64,
  due_date DATE,
  emi_amount FLOAT64,
  principal_component FLOAT64,
  interest_component FLOAT64,
  outstanding_after FLOAT64
);

CREATE TABLE `your-project.lms.payments` (
  payment_id STRING,
  emi_id STRING,
  loan_id STRING,
  amount_paid FLOAT64,
  payment_date DATE,
  payment_mode STRING
);

CREATE TABLE `your-project.lms.overdue_accounts` (
  loan_id STRING,
  days_past_due INT64,
  overdue_amount FLOAT64,
  dpd_bucket STRING
);

CREATE TABLE `your-project.lms.collections_activity` (
  activity_id STRING,
  loan_id STRING,
  employee_id STRING,
  activity_type STRING,
  activity_date DATE,
  outcome STRING
);

CREATE TABLE `your-project.incentive.incentive_payouts` (
  incentive_id STRING,
  employee_id STRING,
  loan_id STRING,
  incentive_type STRING,
  period_month DATE,
  base_amount FLOAT64,
  bonus_amount FLOAT64,
  deduction_amount FLOAT64,
  payout_status STRING,
  payout_date DATE
);

CREATE TABLE `your-project.zoho.zoho_employee_records` (
  zoho_record_id STRING,
  employee_id STRING,
  designation STRING,
  department STRING,
  date_of_joining DATE,
  employment_type STRING,
  reporting_manager STRING,
  work_location STRING,
  leave_balance_days FLOAT64,
  performance_rating STRING
);

CREATE TABLE `your-project.crm.campaigns` (
  campaign_id STRING,
  campaign_name STRING,
  channel STRING,
  campaign_type STRING,
  product_id STRING,
  target_region STRING,
  target_state STRING,
  start_date DATE,
  end_date DATE,
  budget_allocated FLOAT64,
  budget_spent FLOAT64,
  leads_target FLOAT64,
  impressions FLOAT64,
  clicks FLOAT64,
  conversion_rate_target FLOAT64,
  cost_per_lead FLOAT64,
  campaign_manager_id STRING,
  status STRING,
  priority STRING,
  created_at DATE
);

CREATE TABLE `your-project.crm.leads` (
  lead_id STRING,
  campaign_id STRING,
  lead_name STRING,
  phone STRING,
  city STRING,
  state STRING,
  source_channel STRING,
  product_id STRING,
  requested_amount_interest FLOAT64,
  lead_score FLOAT64,
  status STRING,
  assigned_employee_id STRING,
  created_at DATE,
  last_contacted_at DATE,
  follow_up_count FLOAT64,
  conversion_probability FLOAT64,
  age_band STRING,
  occupation STRING,
  income_band STRING,
  is_existing_customer STRING
);

CREATE TABLE `your-project.crm.lead_activities` (
  activity_id STRING,
  lead_id STRING,
  employee_id STRING,
  activity_type STRING,
  activity_date DATE,
  outcome STRING,
  duration_minutes FLOAT64,
  channel_cost FLOAT64,
  sentiment_score FLOAT64,
  follow_up_scheduled STRING,
  priority STRING,
  region STRING,
  device_type STRING,
  agent_notes_flag STRING,
  time_of_day STRING,
  day_of_week_type STRING,
  attempt_number FLOAT64,
  resulted_in_lead_status_change STRING,
  escalated STRING,
  created_at DATE
);

CREATE TABLE `your-project.crm.campaign_responses` (
  response_id STRING,
  campaign_id STRING,
  lead_id STRING,
  response_channel STRING,
  response_date DATE,
  engagement_score FLOAT64,
  clicked STRING,
  converted STRING,
  device_type STRING,
  region STRING,
  time_to_respond_hours FLOAT64,
  bounce_flag STRING,
  form_completion_pct FLOAT64,
  ab_test_variant STRING,
  cost_attributed FLOAT64,
  referral_source STRING,
  utm_source_flag STRING,
  session_duration_seconds FLOAT64,
  repeat_response STRING,
  created_at DATE
);

CREATE TABLE `your-project.treasury.funding_sources` (
  funding_source_id STRING,
  source_name STRING,
  source_type STRING,
  lender_name STRING,
  sanctioned_amount FLOAT64,
  drawn_amount FLOAT64,
  interest_rate FLOAT64,
  tenure_years FLOAT64,
  sanction_date DATE,
  maturity_date DATE,
  region STRING,
  state STRING,
  credit_rating STRING,
  collateral_type STRING,
  repayment_frequency STRING,
  status STRING,
  relationship_manager STRING,
  processing_fee FLOAT64,
  covenant_breach_flag STRING,
  created_at DATE
);

CREATE TABLE `your-project.treasury.treasury_transactions` (
  transaction_id STRING,
  funding_source_id STRING,
  transaction_type STRING,
  transaction_date DATE,
  amount FLOAT64,
  currency STRING,
  settlement_mode STRING,
  approved_by STRING,
  region STRING,
  book_balance_after FLOAT64,
  reconciliation_status STRING,
  value_date DATE,
  counterparty_bank STRING,
  interest_component FLOAT64,
  principal_component FLOAT64,
  is_intercompany STRING,
  processed_by_system STRING,
  audit_flag STRING,
  narration_code STRING,
  created_at DATE
);

CREATE TABLE `your-project.insurance.insurance_policies` (
  policy_id STRING,
  loan_id STRING,
  customer_id STRING,
  policy_type STRING,
  insurer_name STRING,
  sum_assured FLOAT64,
  premium_amount FLOAT64,
  premium_frequency STRING,
  policy_start_date DATE,
  policy_end_date DATE,
  status STRING,
  sold_by_employee_id STRING,
  region STRING,
  state STRING,
  nominee_relation STRING,
  underwriting_decision STRING,
  commission_amount FLOAT64,
  renewal_due STRING,
  digital_issuance STRING,
  created_at DATE
);

CREATE TABLE `your-project.insurance.insurance_claims` (
  claim_id STRING,
  policy_id STRING,
  claim_type STRING,
  claim_amount FLOAT64,
  claim_filed_date DATE,
  claim_status STRING,
  rejection_reason STRING,
  settlement_amount FLOAT64,
  settlement_date DATE,
  processed_by STRING,
  region STRING,
  turnaround_days FLOAT64,
  documentation_score FLOAT64,
  investigator_assigned STRING,
  fraud_flag STRING,
  appeal_filed STRING,
  customer_satisfaction_score FLOAT64,
  channel_reported STRING,
  payout_mode STRING,
  created_at DATE
);

CREATE TABLE `your-project.compliance.audit_logs` (
  audit_id STRING,
  entity_type STRING,
  action_type STRING,
  performed_by_employee_id STRING,
  branch_id STRING,
  action_timestamp DATE,
  ip_region STRING,
  severity STRING,
  system_source STRING,
  field_changed STRING,
  old_value_flag STRING,
  session_id STRING,
  device_type STRING,
  approval_required STRING,
  approved_flag STRING,
  anomaly_score FLOAT64,
  flagged_for_review STRING,
  retention_category STRING,
  log_version STRING,
  created_at DATE
);

CREATE TABLE `your-project.compliance.compliance_flags` (
  flag_id STRING,
  customer_id STRING,
  loan_id STRING,
  flag_type STRING,
  flag_severity STRING,
  raised_date DATE,
  resolved_date DATE,
  status STRING,
  investigated_by STRING,
  regulatory_body STRING,
  reported_externally STRING,
  region STRING,
  state STRING,
  resolution_notes_flag STRING,
  recurrence_count FLOAT64 ,
  risk_score_at_flag FLOAT64,
  branch_id STRING,
  escalation_level STRING,
  sla_breach STRING,
  created_at DATE
);
`
CREATE TABLE `your-project.support.support_tickets` (
  ticket_id STRING,
  customer_id STRING,
  loan_id STRING,
  category STRING,
  channel STRING,
  priority STRING,
  status STRING,
  created_at DATE,
  resolved_at DATE,
  assigned_employee_id STRING,
  branch_id STRING,
  region STRING,
  csat_score FLOAT64,
  reopened_count FLOAT64,
  first_response_minutes FLOAT64,
  resolution_hours FLOAT64,
  escalated STRING,
  language_preference STRING,
  sla_breach STRING,
  sentiment STRING
);

CREATE TABLE `your-project.support.ticket_interactions` (
  interaction_id STRING,
  ticket_id STRING,
  employee_id STRING,
  interaction_type STRING,
  interaction_date DATE,
  channel STRING,
  duration_minutes FLOAT64,
  outcome STRING,
  customer_response_flag STRING,
  internal_only STRING,
  attachment_flag STRING,
  region STRING,
  shift STRING,
  automated_flag STRING,
  tone_flag STRING,
  follow_up_required STRING,
  quality_score FLOAT64,
  template_used STRING,
  resolution_confidence FLOAT64,
  created_at DATE
);
