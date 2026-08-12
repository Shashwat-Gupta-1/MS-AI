
-- ============ Views for role: hr_officer ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_hr_officer`;
CREATE OR REPLACE VIEW `your-project.views_hr_officer.branches` AS SELECT * FROM `your-project.base.branches`;
CREATE OR REPLACE VIEW `your-project.views_hr_officer.employees` AS SELECT * FROM `your-project.base.employees`;
CREATE OR REPLACE VIEW `your-project.views_hr_officer.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_hr_officer.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_hr_officer.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_hr_officer.zoho_employee_records` AS SELECT * FROM `your-project.zoho.zoho_employee_records`;

-- ============ Views for role: loan_officer ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_loan_officer`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.branches` AS SELECT * FROM `your-project.base.branches`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.employees` AS SELECT * FROM `your-project.base.employees`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.kyc_documents` AS SELECT * FROM `your-project.los.kyc_documents`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_loan_officer.compliance_flags` AS SELECT * FROM `your-project.compliance.compliance_flags`;

-- ============ Views for role: collections_agent ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_collections_agent`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.branches` AS SELECT * FROM `your-project.base.branches`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.employees` AS SELECT * FROM `your-project.base.employees`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.collections_activity` AS SELECT * FROM `your-project.lms.collections_activity`;
CREATE OR REPLACE VIEW `your-project.views_collections_agent.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;

-- ============ Views for role: sales_rep ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_sales_rep`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.branches` AS SELECT * FROM `your-project.base.branches`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.employees` AS SELECT * FROM `your-project.base.employees`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.campaigns` AS SELECT * FROM `your-project.crm.campaigns`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.leads` AS SELECT * FROM `your-project.crm.leads`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.lead_activities` AS SELECT * FROM `your-project.crm.lead_activities`;
CREATE OR REPLACE VIEW `your-project.views_sales_rep.campaign_responses` AS SELECT * FROM `your-project.crm.campaign_responses`;

-- ============ Views for role: branch_manager ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_branch_manager`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.branches` AS SELECT * FROM `your-project.base.branches`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.employees` AS SELECT * FROM `your-project.base.employees`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.kyc_documents` AS SELECT * FROM `your-project.los.kyc_documents`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.collections_activity` AS SELECT * FROM `your-project.lms.collections_activity`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.zoho_employee_records` AS SELECT * FROM `your-project.zoho.zoho_employee_records`;
CREATE OR REPLACE VIEW `your-project.views_branch_manager.compliance_flags` AS SELECT * FROM `your-project.compliance.compliance_flags`;

-- ============ Views for role: compliance_officer ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_compliance_officer`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.kyc_documents` AS SELECT * FROM `your-project.los.kyc_documents`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.audit_logs` AS SELECT * FROM `your-project.compliance.audit_logs`;
CREATE OR REPLACE VIEW `your-project.views_compliance_officer.compliance_flags` AS SELECT * FROM `your-project.compliance.compliance_flags`;

-- ============ Views for role: treasury_manager ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_treasury_manager`;
CREATE OR REPLACE VIEW `your-project.views_treasury_manager.funding_sources` AS SELECT * FROM `your-project.treasury.funding_sources`;
CREATE OR REPLACE VIEW `your-project.views_treasury_manager.treasury_transactions` AS SELECT * FROM `your-project.treasury.treasury_transactions`;

-- ============ Views for role: insurance_ops ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_insurance_ops`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.insurance_policies` AS SELECT * FROM `your-project.insurance.insurance_policies`;
CREATE OR REPLACE VIEW `your-project.views_insurance_ops.insurance_claims` AS SELECT * FROM `your-project.insurance.insurance_claims`;

-- ============ Views for role: support_agent ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_support_agent`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.kyc_documents` AS SELECT * FROM `your-project.los.kyc_documents`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.support_tickets` AS SELECT * FROM `your-project.support.support_tickets`;
CREATE OR REPLACE VIEW `your-project.views_support_agent.ticket_interactions` AS SELECT * FROM `your-project.support.ticket_interactions`;

-- ============ Views for role: executive ============
CREATE SCHEMA IF NOT EXISTS `your-project.views_executive`;
CREATE OR REPLACE VIEW `your-project.views_executive.branches` AS SELECT * FROM `your-project.base.branches`;
CREATE OR REPLACE VIEW `your-project.views_executive.employees` AS SELECT * FROM `your-project.base.employees`;
CREATE OR REPLACE VIEW `your-project.views_executive.customers` AS SELECT * FROM `your-project.base.customers`;
CREATE OR REPLACE VIEW `your-project.views_executive.loan_products` AS SELECT * FROM `your-project.base.loan_products`;
CREATE OR REPLACE VIEW `your-project.views_executive.loan_applications` AS SELECT * FROM `your-project.los.loan_applications`;
CREATE OR REPLACE VIEW `your-project.views_executive.kyc_documents` AS SELECT * FROM `your-project.los.kyc_documents`;
CREATE OR REPLACE VIEW `your-project.views_executive.customer_risk_scores` AS SELECT * FROM `your-project.los.customer_risk_scores`;
CREATE OR REPLACE VIEW `your-project.views_executive.loans` AS SELECT * FROM `your-project.lms.loans`;
CREATE OR REPLACE VIEW `your-project.views_executive.emi_schedule` AS SELECT * FROM `your-project.lms.emi_schedule`;
CREATE OR REPLACE VIEW `your-project.views_executive.payments` AS SELECT * FROM `your-project.lms.payments`;
CREATE OR REPLACE VIEW `your-project.views_executive.overdue_accounts` AS SELECT * FROM `your-project.lms.overdue_accounts`;
CREATE OR REPLACE VIEW `your-project.views_executive.collections_activity` AS SELECT * FROM `your-project.lms.collections_activity`;
CREATE OR REPLACE VIEW `your-project.views_executive.incentive_payouts` AS SELECT * FROM `your-project.incentive.incentive_payouts`;
CREATE OR REPLACE VIEW `your-project.views_executive.zoho_employee_records` AS SELECT * FROM `your-project.zoho.zoho_employee_records`;
CREATE OR REPLACE VIEW `your-project.views_executive.campaigns` AS SELECT * FROM `your-project.crm.campaigns`;
CREATE OR REPLACE VIEW `your-project.views_executive.leads` AS SELECT * FROM `your-project.crm.leads`;
CREATE OR REPLACE VIEW `your-project.views_executive.lead_activities` AS SELECT * FROM `your-project.crm.lead_activities`;
CREATE OR REPLACE VIEW `your-project.views_executive.campaign_responses` AS SELECT * FROM `your-project.crm.campaign_responses`;
CREATE OR REPLACE VIEW `your-project.views_executive.funding_sources` AS SELECT * FROM `your-project.treasury.funding_sources`;
CREATE OR REPLACE VIEW `your-project.views_executive.treasury_transactions` AS SELECT * FROM `your-project.treasury.treasury_transactions`;
CREATE OR REPLACE VIEW `your-project.views_executive.insurance_policies` AS SELECT * FROM `your-project.insurance.insurance_policies`;
CREATE OR REPLACE VIEW `your-project.views_executive.insurance_claims` AS SELECT * FROM `your-project.insurance.insurance_claims`;
CREATE OR REPLACE VIEW `your-project.views_executive.audit_logs` AS SELECT * FROM `your-project.compliance.audit_logs`;
CREATE OR REPLACE VIEW `your-project.views_executive.compliance_flags` AS SELECT * FROM `your-project.compliance.compliance_flags`;
CREATE OR REPLACE VIEW `your-project.views_executive.support_tickets` AS SELECT * FROM `your-project.support.support_tickets`;
CREATE OR REPLACE VIEW `your-project.views_executive.ticket_interactions` AS SELECT * FROM `your-project.support.ticket_interactions`;