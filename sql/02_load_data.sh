#!/bin/bash

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:base.branches output/base/branches.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:base.employees output/base/employees.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:base.customers output/base/customers.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:base.loan_products output/base/loan_products.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:los.loan_applications output/los/loan_applications.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:los.kyc_documents output/los/kyc_documents.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:los.customer_risk_scores output/los/customer_risk_scores.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:lms.loans output/lms/loans.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:lms.emi_schedule output/lms/emi_schedule.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:lms.payments output/lms/payments.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:lms.overdue_accounts output/lms/overdue_accounts.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:lms.collections_activity output/lms/collections_activity.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:incentive.incentive_payouts output/incentive/incentive_payouts.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:zoho.zoho_employee_records output/zoho/zoho_employee_records.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:crm.campaigns output/crm/campaigns.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:crm.leads output/crm/leads.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:crm.lead_activities output/crm/lead_activities.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:crm.campaign_responses output/crm/campaign_responses.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:treasury.funding_sources output/treasury/funding_sources.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:treasury.treasury_transactions output/treasury/treasury_transactions.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:insurance.insurance_policies output/insurance/insurance_policies.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:insurance.insurance_claims output/insurance/insurance_claims.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:compliance.audit_logs output/compliance/audit_logs.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:compliance.compliance_flags output/compliance/compliance_flags.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:support.support_tickets output/support/support_tickets.csv

bq load --source_format=CSV --skip_leading_rows=1 --noreplace \
  your-project:support.ticket_interactions output/support/ticket_interactions.csv
