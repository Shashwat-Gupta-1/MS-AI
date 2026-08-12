#!/bin/bash

# --- hr_officer ---
bq add-iam-policy-binding --member="group:hr_officer@yourcompany.com" --role="roles/bigquery.dataViewer" views_hr_officer

# --- loan_officer ---
bq add-iam-policy-binding --member="group:loan_officer@yourcompany.com" --role="roles/bigquery.dataViewer" views_loan_officer

# --- collections_agent ---
bq add-iam-policy-binding --member="group:collections_agent@yourcompany.com" --role="roles/bigquery.dataViewer" views_collections_agent

# --- sales_rep ---
bq add-iam-policy-binding --member="group:sales_rep@yourcompany.com" --role="roles/bigquery.dataViewer" views_sales_rep

# --- branch_manager ---
bq add-iam-policy-binding --member="group:branch_manager@yourcompany.com" --role="roles/bigquery.dataViewer" views_branch_manager

# --- compliance_officer ---
bq add-iam-policy-binding --member="group:compliance_officer@yourcompany.com" --role="roles/bigquery.dataViewer" views_compliance_officer

# --- treasury_manager ---
bq add-iam-policy-binding --member="group:treasury_manager@yourcompany.com" --role="roles/bigquery.dataViewer" views_treasury_manager

# --- insurance_ops ---
bq add-iam-policy-binding --member="group:insurance_ops@yourcompany.com" --role="roles/bigquery.dataViewer" views_insurance_ops

# --- support_agent ---
bq add-iam-policy-binding --member="group:support_agent@yourcompany.com" --role="roles/bigquery.dataViewer" views_support_agent

# --- executive ---
bq add-iam-policy-binding --member="group:executive@yourcompany.com" --role="roles/bigquery.dataViewer" views_executive