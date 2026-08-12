# Entity Relationship Doc — for LLM-driven join-path retrieval (v2, corrected)

40 relationships across 26 tables.

**What changed from v1:** the `same_as_ref`-derived edges (`loans.customer_id`, 
`loans.product_id`, `loans.branch_id`, `insurance_policies.customer_id`) previously 
pointed at the intermediate table the value was copied THROUGH (e.g. `loan_applications`), 
not the actual table the relationship means (e.g. `customers`). All four are now 
resolved to their true target. `collections_activity.loan_id` also previously pointed 
at `overdue_accounts` (the yaml's literal ref_table) instead of `loans` (the real FK) — 
corrected as well.

This doc is the substitute for BigQuery foreign keys, which are not enforced or 
queryable via INFORMATION_SCHEMA unless explicitly declared (see sql/03_add_constraints.sql). 
Every edge below was derived from the generator YAML's `ref` / `ref_filtered` / `same_as_ref` 
column definitions, not from any live database constraint.

## Hub tables (most heavily referenced — need relationship_type disambiguation)

- **employees** — referenced by 10 different foreign keys across the schema
- **branches** — referenced by 6 different foreign keys across the schema
- **customers** — referenced by 6 different foreign keys across the schema
- **loans** — referenced by 6 different foreign keys across the schema
- **loan_products** — referenced by 4 different foreign keys across the schema
- **campaigns** — referenced by 2 different foreign keys across the schema

## Full relationship graph, by source table

### `compliance.audit_logs`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `performed_by_employee_id` | `employees.employee_id` | `performed_by` |  |
| `branch_id` | `branches.branch_id` | `occurred_at` |  |

### `crm.campaign_responses`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `campaign_id` | `campaigns.campaign_id` | `responds_to` |  |
| `lead_id` | `leads.lead_id` | `response_from` |  |

### `crm.campaigns`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `product_id` | `loan_products.product_id` | `promotes` |  |
| `campaign_manager_id` | `employees.employee_id` | `managed_by` | filtered: role=sales_rep |

### `lms.collections_activity`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `loan_id` | `loans.loan_id` | `recovery_action_on` | direct_ref (corrected: yaml sources from overdue_accounts, true FK target is loans) |
| `employee_id` | `employees.employee_id` | `handled_by` | filtered: role=collections_agent |

### `compliance.compliance_flags`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `customer_id` | `customers.customer_id` | `raised_against_customer` |  |
| `loan_id` | `loans.loan_id` | `raised_against_loan` |  |
| `branch_id` | `branches.branch_id` | `raised_at` |  |

### `los.customer_risk_scores`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `customer_id` | `customers.customer_id` | `risk_profile_of` |  |

### `base.employees`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `branch_id` | `branches.branch_id` | `based_at` |  |

### `incentive.incentive_payouts`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `employee_id` | `employees.employee_id` | `earned_by` | filtered: role=loan_officer |
| `loan_id` | `loans.loan_id` | `earned_against` |  |

### `insurance.insurance_claims`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `policy_id` | `insurance_policies.policy_id` | `claim_against` |  |

### `insurance.insurance_policies`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `loan_id` | `loans.loan_id` | `attached_to` |  |
| `customer_id` | `loans.customer_id` | `is_insured_person` | same_as_ref (copied via insurance_policies.loan_id, corrected to true target) |
| `sold_by_employee_id` | `employees.employee_id` | `sold_by` | filtered: role=loan_officer |

### `los.kyc_documents`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `customer_id` | `customers.customer_id` | `identity_of` |  |

### `crm.lead_activities`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `lead_id` | `leads.lead_id` | `touchpoint_on` |  |
| `employee_id` | `employees.employee_id` | `performed_by` | filtered: role=sales_rep |

### `crm.leads`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `campaign_id` | `campaigns.campaign_id` | `sourced_via` |  |
| `product_id` | `loan_products.product_id` | `interested_in` |  |
| `assigned_employee_id` | `employees.employee_id` | `assigned_to` | filtered: role=sales_rep |

### `los.loan_applications`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `customer_id` | `customers.customer_id` | `applied_by` |  |
| `product_id` | `loan_products.product_id` | `for_product` |  |
| `branch_id` | `branches.branch_id` | `submitted_at` |  |

### `lms.loans`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `application_id` | `loan_applications.application_id` | `originated_from` | filtered: status=approved |
| `customer_id` | `customers.customer_id` | `is_borrower_of` | same_as_ref (copied via loans.application_id, corrected to true target) |
| `product_id` | `loan_products.product_id` | `for_product` | same_as_ref (copied via loans.application_id, corrected to true target) |
| `branch_id` | `branches.branch_id` | `disbursed_by` | same_as_ref (copied via loans.application_id, corrected to true target) |

### `support.support_tickets`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `customer_id` | `customers.customer_id` | `raised_by` |  |
| `loan_id` | `loans.loan_id` | `concerns_loan` |  |
| `assigned_employee_id` | `employees.employee_id` | `assigned_to` |  |
| `branch_id` | `branches.branch_id` | `handled_at` |  |

### `support.ticket_interactions`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `ticket_id` | `support_tickets.ticket_id` | `interaction_on` |  |
| `employee_id` | `employees.employee_id` | `logged_by` |  |

### `treasury.treasury_transactions`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `funding_source_id` | `funding_sources.funding_source_id` | `cash_flow_against` |  |

### `zoho.zoho_employee_records`
| Column | -> Table.Column | Relationship | Notes |
|---|---|---|---|
| `employee_id` | `employees.employee_id` | `hr_record_of` |  |

## Multi-path ambiguity warnings

Cases where two DIFFERENT relationship_types connect the same two tables:

- `insurance_policies` <-> `loans`: attached_to, is_insured_person
