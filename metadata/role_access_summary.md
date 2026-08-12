# Role Access Summary

## `hr_officer` — HR staff managing employee records and performance data
Domains: hr, ops
Tables visible (6):
  - `base.branches`
  - `base.employees`
  - `base.customers`
  - `base.loan_products`
  - `incentive.incentive_payouts`
  - `zoho.zoho_employee_records`

## `loan_officer` — Originates and manages loans day-to-day
Domains: incentive, kyc, loan, ops, risk
Tables visible (13):
  - `base.branches`
  - `base.employees`
  - `base.customers`
  - `base.loan_products`
  - `los.loan_applications`
  - `los.kyc_documents`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `incentive.incentive_payouts`
  - `compliance.compliance_flags`

## `collections_agent` — Works overdue accounts and recovery activity
Domains: collections, loan, ops
Tables visible (12):
  - `base.branches`
  - `base.employees`
  - `base.customers`
  - `base.loan_products`
  - `los.loan_applications`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `lms.collections_activity`
  - `incentive.incentive_payouts`

## `sales_rep` — Works leads through to conversion
Domains: leads, marketing, ops, sales
Tables visible (8):
  - `base.branches`
  - `base.employees`
  - `base.customers`
  - `base.loan_products`
  - `crm.campaigns`
  - `crm.leads`
  - `crm.lead_activities`
  - `crm.campaign_responses`

## `branch_manager` — Oversees a branch across lending, collections, and staff
Domains: collections, hr, incentive, kyc, loan, ops, risk
Tables visible (15):
  - `base.branches`
  - `base.employees`
  - `base.customers`
  - `base.loan_products`
  - `los.loan_applications`
  - `los.kyc_documents`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `lms.collections_activity`
  - `incentive.incentive_payouts`
  - `zoho.zoho_employee_records`
  - `compliance.compliance_flags`

## `compliance_officer` — Regulatory, audit, and risk oversight
Domains: audit, compliance, kyc, loan, risk
Tables visible (12):
  - `base.customers`
  - `base.loan_products`
  - `los.loan_applications`
  - `los.kyc_documents`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `incentive.incentive_payouts`
  - `compliance.audit_logs`
  - `compliance.compliance_flags`

## `treasury_manager` — Manages the NBFC's own funding and cash flow
Domains: finance, treasury
Tables visible (2):
  - `treasury.funding_sources`
  - `treasury.treasury_transactions`

## `insurance_ops` — Manages cross-sell insurance policies and claims
Domains: cross_sell, insurance, loan
Tables visible (10):
  - `base.loan_products`
  - `los.loan_applications`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `incentive.incentive_payouts`
  - `insurance.insurance_policies`
  - `insurance.insurance_claims`

## `support_agent` — Handles customer service tickets
Domains: customer_service, kyc, loan, support
Tables visible (12):
  - `base.customers`
  - `base.loan_products`
  - `los.loan_applications`
  - `los.kyc_documents`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `incentive.incentive_payouts`
  - `support.support_tickets`
  - `support.ticket_interactions`

## `executive` — Full visibility across the entire business — leadership, strategy, and cross-functional reporting roles
Domains: audit, collections, compliance, cross_sell, customer_service, finance, hr, incentive, insurance, kyc, leads, loan, marketing, ops, risk, sales, support, treasury
Tables visible (26):
  - `base.branches`
  - `base.employees`
  - `base.customers`
  - `base.loan_products`
  - `los.loan_applications`
  - `los.kyc_documents`
  - `los.customer_risk_scores`
  - `lms.loans`
  - `lms.emi_schedule`
  - `lms.payments`
  - `lms.overdue_accounts`
  - `lms.collections_activity`
  - `incentive.incentive_payouts`
  - `zoho.zoho_employee_records`
  - `crm.campaigns`
  - `crm.leads`
  - `crm.lead_activities`
  - `crm.campaign_responses`
  - `treasury.funding_sources`
  - `treasury.treasury_transactions`
  - `insurance.insurance_policies`
  - `insurance.insurance_claims`
  - `compliance.audit_logs`
  - `compliance.compliance_flags`
  - `support.support_tickets`
  - `support.ticket_interactions`
