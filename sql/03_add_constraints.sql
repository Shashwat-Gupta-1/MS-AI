-- PRIMARY KEYS

ALTER TABLE `your-project.base.branches`
  ADD PRIMARY KEY (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.base.employees`
  ADD PRIMARY KEY (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.base.customers`
  ADD PRIMARY KEY (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.base.loan_products`
  ADD PRIMARY KEY (product_id) NOT ENFORCED;

ALTER TABLE `your-project.los.loan_applications`
  ADD PRIMARY KEY (application_id) NOT ENFORCED;

ALTER TABLE `your-project.los.kyc_documents`
  ADD PRIMARY KEY (kyc_id) NOT ENFORCED;

ALTER TABLE `your-project.los.customer_risk_scores`
  ADD PRIMARY KEY (score_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.loans`
  ADD PRIMARY KEY (loan_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.emi_schedule`
  ADD PRIMARY KEY (emi_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.payments`
  ADD PRIMARY KEY (payment_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.payments`
  ADD PRIMARY KEY (emi_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.collections_activity`
  ADD PRIMARY KEY (activity_id) NOT ENFORCED;

ALTER TABLE `your-project.incentive.incentive_payouts`
  ADD PRIMARY KEY (incentive_id) NOT ENFORCED;

ALTER TABLE `your-project.zoho.zoho_employee_records`
  ADD PRIMARY KEY (zoho_record_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.campaigns`
  ADD PRIMARY KEY (campaign_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.leads`
  ADD PRIMARY KEY (lead_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.lead_activities`
  ADD PRIMARY KEY (activity_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.campaign_responses`
  ADD PRIMARY KEY (response_id) NOT ENFORCED;

ALTER TABLE `your-project.treasury.funding_sources`
  ADD PRIMARY KEY (funding_source_id) NOT ENFORCED;

ALTER TABLE `your-project.treasury.treasury_transactions`
  ADD PRIMARY KEY (transaction_id) NOT ENFORCED;

ALTER TABLE `your-project.insurance.insurance_policies`
  ADD PRIMARY KEY (policy_id) NOT ENFORCED;

ALTER TABLE `your-project.insurance.insurance_claims`
  ADD PRIMARY KEY (claim_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.audit_logs`
  ADD PRIMARY KEY (audit_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.compliance_flags`
  ADD PRIMARY KEY (flag_id) NOT ENFORCED;

ALTER TABLE `your-project.support.support_tickets`
  ADD PRIMARY KEY (ticket_id) NOT ENFORCED;

ALTER TABLE `your-project.support.ticket_interactions`
  ADD PRIMARY KEY (interaction_id) NOT ENFORCED;

-- FOREIGN KEYS (corrected targets)

ALTER TABLE `your-project.base.employees`
  ADD CONSTRAINT fk_employees_branch_id
  FOREIGN KEY (branch_id) REFERENCES `your-project.base.branches` (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.los.loan_applications`
  ADD CONSTRAINT fk_loan_applications_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.los.loan_applications`
  ADD CONSTRAINT fk_loan_applications_product_id
  FOREIGN KEY (product_id) REFERENCES `your-project.base.loan_products` (product_id) NOT ENFORCED;

ALTER TABLE `your-project.los.loan_applications`
  ADD CONSTRAINT fk_loan_applications_branch_id
  FOREIGN KEY (branch_id) REFERENCES `your-project.base.branches` (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.los.kyc_documents`
  ADD CONSTRAINT fk_kyc_documents_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.los.customer_risk_scores`
  ADD CONSTRAINT fk_customer_risk_scores_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.loans`
  ADD CONSTRAINT fk_loans_application_id
  FOREIGN KEY (application_id) REFERENCES `your-project.los.loan_applications` (application_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.loans`
  ADD CONSTRAINT fk_loans_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.loans`
  ADD CONSTRAINT fk_loans_product_id
  FOREIGN KEY (product_id) REFERENCES `your-project.base.loan_products` (product_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.loans`
  ADD CONSTRAINT fk_loans_branch_id
  FOREIGN KEY (branch_id) REFERENCES `your-project.base.branches` (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.collections_activity`
  ADD CONSTRAINT fk_collections_activity_loan_id
  FOREIGN KEY (loan_id) REFERENCES `your-project.lms.loans` (loan_id) NOT ENFORCED;

ALTER TABLE `your-project.lms.collections_activity`
  ADD CONSTRAINT fk_collections_activity_employee_id
  FOREIGN KEY (employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.incentive.incentive_payouts`
  ADD CONSTRAINT fk_incentive_payouts_employee_id
  FOREIGN KEY (employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.incentive.incentive_payouts`
  ADD CONSTRAINT fk_incentive_payouts_loan_id
  FOREIGN KEY (loan_id) REFERENCES `your-project.lms.loans` (loan_id) NOT ENFORCED;

ALTER TABLE `your-project.zoho.zoho_employee_records`
  ADD CONSTRAINT fk_zoho_employee_records_employee_id
  FOREIGN KEY (employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.campaigns`
  ADD CONSTRAINT fk_campaigns_product_id
  FOREIGN KEY (product_id) REFERENCES `your-project.base.loan_products` (product_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.campaigns`
  ADD CONSTRAINT fk_campaigns_campaign_manager_id
  FOREIGN KEY (campaign_manager_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.leads`
  ADD CONSTRAINT fk_leads_campaign_id
  FOREIGN KEY (campaign_id) REFERENCES `your-project.crm.campaigns` (campaign_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.leads`
  ADD CONSTRAINT fk_leads_product_id
  FOREIGN KEY (product_id) REFERENCES `your-project.base.loan_products` (product_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.leads`
  ADD CONSTRAINT fk_leads_assigned_employee_id
  FOREIGN KEY (assigned_employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.lead_activities`
  ADD CONSTRAINT fk_lead_activities_lead_id
  FOREIGN KEY (lead_id) REFERENCES `your-project.crm.leads` (lead_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.lead_activities`
  ADD CONSTRAINT fk_lead_activities_employee_id
  FOREIGN KEY (employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.campaign_responses`
  ADD CONSTRAINT fk_campaign_responses_campaign_id
  FOREIGN KEY (campaign_id) REFERENCES `your-project.crm.campaigns` (campaign_id) NOT ENFORCED;

ALTER TABLE `your-project.crm.campaign_responses`
  ADD CONSTRAINT fk_campaign_responses_lead_id
  FOREIGN KEY (lead_id) REFERENCES `your-project.crm.leads` (lead_id) NOT ENFORCED;

ALTER TABLE `your-project.treasury.treasury_transactions`
  ADD CONSTRAINT fk_treasury_transactions_funding_source_id
  FOREIGN KEY (funding_source_id) REFERENCES `your-project.treasury.funding_sources` (funding_source_id) NOT ENFORCED;

ALTER TABLE `your-project.insurance.insurance_policies`
  ADD CONSTRAINT fk_insurance_policies_loan_id
  FOREIGN KEY (loan_id) REFERENCES `your-project.lms.loans` (loan_id) NOT ENFORCED;

ALTER TABLE `your-project.insurance.insurance_policies`
  ADD CONSTRAINT fk_insurance_policies_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.insurance.insurance_policies`
  ADD CONSTRAINT fk_insurance_policies_sold_by_employee_id
  FOREIGN KEY (sold_by_employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.insurance.insurance_claims`
  ADD CONSTRAINT fk_insurance_claims_policy_id
  FOREIGN KEY (policy_id) REFERENCES `your-project.insurance.insurance_policies` (policy_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.audit_logs`
  ADD CONSTRAINT fk_audit_logs_performed_by_employee_id
  FOREIGN KEY (performed_by_employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.audit_logs`
  ADD CONSTRAINT fk_audit_logs_branch_id
  FOREIGN KEY (branch_id) REFERENCES `your-project.base.branches` (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.compliance_flags`
  ADD CONSTRAINT fk_compliance_flags_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.compliance_flags`
  ADD CONSTRAINT fk_compliance_flags_loan_id
  FOREIGN KEY (loan_id) REFERENCES `your-project.lms.loans` (loan_id) NOT ENFORCED;

ALTER TABLE `your-project.compliance.compliance_flags`
  ADD CONSTRAINT fk_compliance_flags_branch_id
  FOREIGN KEY (branch_id) REFERENCES `your-project.base.branches` (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.support.support_tickets`
  ADD CONSTRAINT fk_support_tickets_customer_id
  FOREIGN KEY (customer_id) REFERENCES `your-project.base.customers` (customer_id) NOT ENFORCED;

ALTER TABLE `your-project.support.support_tickets`
  ADD CONSTRAINT fk_support_tickets_loan_id
  FOREIGN KEY (loan_id) REFERENCES `your-project.lms.loans` (loan_id) NOT ENFORCED;

ALTER TABLE `your-project.support.support_tickets`
  ADD CONSTRAINT fk_support_tickets_assigned_employee_id
  FOREIGN KEY (assigned_employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;

ALTER TABLE `your-project.support.support_tickets`
  ADD CONSTRAINT fk_support_tickets_branch_id
  FOREIGN KEY (branch_id) REFERENCES `your-project.base.branches` (branch_id) NOT ENFORCED;

ALTER TABLE `your-project.support.ticket_interactions`
  ADD CONSTRAINT fk_ticket_interactions_ticket_id
  FOREIGN KEY (ticket_id) REFERENCES `your-project.support.support_tickets` (ticket_id) NOT ENFORCED;

ALTER TABLE `your-project.support.ticket_interactions`
  ADD CONSTRAINT fk_ticket_interactions_employee_id
  FOREIGN KEY (employee_id) REFERENCES `your-project.base.employees` (employee_id) NOT ENFORCED;