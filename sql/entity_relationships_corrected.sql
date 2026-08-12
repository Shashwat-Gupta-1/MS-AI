-- Entity relationships table (v2, corrected) -- every FK-like join path in the schema,
-- derived from the generator YAML configs' ref/ref_filtered/same_as_ref columns.
-- v2 fix: same_as_ref edges now resolve to their TRUE target table instead of the
-- intermediate table the value was copied through (e.g. loans.customer_id -> customers,
-- not loans.customer_id -> loan_applications). collections_activity.loan_id -> loans
-- fixed the same way (was pointing at overdue_accounts).
--
-- NOTE: none of these exist as real BigQuery constraints (BigQuery does not enforce
-- or expose FKs even when declared) -- this table is the substitute: a hand-verified
-- relationship graph for the LLM/retrieval layer to join against.

CREATE SCHEMA IF NOT EXISTS `your-project.rag_meta`;

CREATE OR REPLACE TABLE `your-project.rag_meta.entity_relationships` (
  from_table STRING,
  from_column STRING,
  to_table STRING,
  to_column STRING,
  relationship_type STRING,
  derivation STRING,
  row_filter STRING,
  is_declared_fk BOOL,
  source STRING
);

INSERT INTO `your-project.rag_meta.entity_relationships`
(from_table, from_column, to_table, to_column, relationship_type, derivation, row_filter, is_declared_fk, source)
VALUES
  ('employees', 'branch_id', 'branches', 'branch_id', 'based_at', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('loan_applications', 'customer_id', 'customers', 'customer_id', 'applied_by', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('loan_applications', 'product_id', 'loan_products', 'product_id', 'for_product', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('loan_applications', 'branch_id', 'branches', 'branch_id', 'submitted_at', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('kyc_documents', 'customer_id', 'customers', 'customer_id', 'identity_of', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('customer_risk_scores', 'customer_id', 'customers', 'customer_id', 'risk_profile_of', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('loans', 'application_id', 'loan_applications', 'application_id', 'originated_from', 'direct_ref', 'status=approved', FALSE, 'generator_yaml_v2'),
  ('loans', 'customer_id', 'customers', 'customer_id', 'is_borrower_of', 'same_as_ref (copied via loans.application_id, corrected to true target)', NULL, FALSE, 'generator_yaml_v2'),
  ('loans', 'product_id', 'loan_products', 'product_id', 'for_product', 'same_as_ref (copied via loans.application_id, corrected to true target)', NULL, FALSE, 'generator_yaml_v2'),
  ('loans', 'branch_id', 'branches', 'branch_id', 'disbursed_by', 'same_as_ref (copied via loans.application_id, corrected to true target)', NULL, FALSE, 'generator_yaml_v2'),
  ('collections_activity', 'loan_id', 'loans', 'loan_id', 'recovery_action_on', 'direct_ref (corrected: yaml sources from overdue_accounts, true FK target is loans)', NULL, FALSE, 'generator_yaml_v2'),
  ('collections_activity', 'employee_id', 'employees', 'employee_id', 'handled_by', 'direct_ref_filtered', 'role=collections_agent', FALSE, 'generator_yaml_v2'),
  ('incentive_payouts', 'employee_id', 'employees', 'employee_id', 'earned_by', 'direct_ref_filtered', 'role=loan_officer', FALSE, 'generator_yaml_v2'),
  ('incentive_payouts', 'loan_id', 'loans', 'loan_id', 'earned_against', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('zoho_employee_records', 'employee_id', 'employees', 'employee_id', 'hr_record_of', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('campaigns', 'product_id', 'loan_products', 'product_id', 'promotes', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('campaigns', 'campaign_manager_id', 'employees', 'employee_id', 'managed_by', 'direct_ref_filtered', 'role=sales_rep', FALSE, 'generator_yaml_v2'),
  ('leads', 'campaign_id', 'campaigns', 'campaign_id', 'sourced_via', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('leads', 'product_id', 'loan_products', 'product_id', 'interested_in', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('leads', 'assigned_employee_id', 'employees', 'employee_id', 'assigned_to', 'direct_ref_filtered', 'role=sales_rep', FALSE, 'generator_yaml_v2'),
  ('lead_activities', 'lead_id', 'leads', 'lead_id', 'touchpoint_on', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('lead_activities', 'employee_id', 'employees', 'employee_id', 'performed_by', 'direct_ref_filtered', 'role=sales_rep', FALSE, 'generator_yaml_v2'),
  ('campaign_responses', 'campaign_id', 'campaigns', 'campaign_id', 'responds_to', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('campaign_responses', 'lead_id', 'leads', 'lead_id', 'response_from', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('treasury_transactions', 'funding_source_id', 'funding_sources', 'funding_source_id', 'cash_flow_against', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('insurance_policies', 'loan_id', 'loans', 'loan_id', 'attached_to', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('insurance_policies', 'customer_id', 'loans', 'customer_id', 'is_insured_person', 'same_as_ref (copied via insurance_policies.loan_id, corrected to true target)', NULL, FALSE, 'generator_yaml_v2'),
  ('insurance_policies', 'sold_by_employee_id', 'employees', 'employee_id', 'sold_by', 'direct_ref_filtered', 'role=loan_officer', FALSE, 'generator_yaml_v2'),
  ('insurance_claims', 'policy_id', 'insurance_policies', 'policy_id', 'claim_against', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('audit_logs', 'performed_by_employee_id', 'employees', 'employee_id', 'performed_by', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('audit_logs', 'branch_id', 'branches', 'branch_id', 'occurred_at', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('compliance_flags', 'customer_id', 'customers', 'customer_id', 'raised_against_customer', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('compliance_flags', 'loan_id', 'loans', 'loan_id', 'raised_against_loan', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('compliance_flags', 'branch_id', 'branches', 'branch_id', 'raised_at', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('support_tickets', 'customer_id', 'customers', 'customer_id', 'raised_by', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('support_tickets', 'loan_id', 'loans', 'loan_id', 'concerns_loan', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('support_tickets', 'assigned_employee_id', 'employees', 'employee_id', 'assigned_to', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('support_tickets', 'branch_id', 'branches', 'branch_id', 'handled_at', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('ticket_interactions', 'ticket_id', 'support_tickets', 'ticket_id', 'interaction_on', 'direct_ref', NULL, FALSE, 'generator_yaml_v2'),
  ('ticket_interactions', 'employee_id', 'employees', 'employee_id', 'logged_by', 'direct_ref', NULL, FALSE, 'generator_yaml_v2');