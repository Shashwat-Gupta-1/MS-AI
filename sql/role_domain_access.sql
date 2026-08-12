-- Role -> allowed domains mapping.
-- App-level lookup / audit trail ONLY -- this table is NOT the security
-- boundary. The real boundary is generated_role_views.sql + generated_role_grants.sh
-- (BigQuery IAM + authorized views), generated FROM this same source yaml.

CREATE SCHEMA IF NOT EXISTS `your-project.rag_meta`;

CREATE OR REPLACE TABLE `your-project.rag_meta.role_domain_access` (
  role_name STRING,
  description STRING,
  allowed_domains ARRAY<STRING>,
  is_wildcard BOOL
);

INSERT INTO `your-project.rag_meta.role_domain_access`
(role_name, description, allowed_domains, is_wildcard)
VALUES
  ('hr_officer', 'HR staff managing employee records and performance data', ['hr', 'ops'], FALSE),
  ('loan_officer', 'Originates and manages loans day-to-day', ['loan', 'kyc', 'risk', 'ops', 'incentive'], FALSE),
  ('collections_agent', 'Works overdue accounts and recovery activity', ['collections', 'loan', 'ops'], FALSE),
  ('sales_rep', 'Works leads through to conversion', ['leads', 'sales', 'marketing', 'ops'], FALSE),
  ('branch_manager', 'Oversees a branch across lending, collections, and staff', ['loan', 'collections', 'kyc', 'risk', 'hr', 'incentive', 'ops'], FALSE),
  ('compliance_officer', 'Regulatory, audit, and risk oversight', ['compliance', 'audit', 'risk', 'kyc', 'loan'], FALSE),
  ('treasury_manager', 'Manages the NBFC\'s own funding and cash flow', ['treasury', 'finance'], FALSE),
  ('insurance_ops', 'Manages cross-sell insurance policies and claims', ['insurance', 'cross_sell', 'loan'], FALSE),
  ('support_agent', 'Handles customer service tickets', ['support', 'customer_service', 'loan', 'kyc'], FALSE),
  ('executive', 'Full visibility across the entire business — leadership, strategy, and cross-functional reporting roles', [], TRUE);