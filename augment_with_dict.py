"""
augment_with_dict.py
-------------------
Reads all chunks from table_chunks, uses a static dictionary mapping 
to inject domain-specific business questions for each chunk, and updates BigQuery 
in a batch-friendly way. Bypasses LLM completely for 0 cost and instant speed!
"""

import os
import uuid
import time
import google.generativeai as genai
from google.cloud import bigquery

PROJECT_ID = "project-f118f2cb-f557-4d4f-990"
DATASET    = "rag_meta"

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DOMAIN_MAPPING = {
    # Customers & KYC
    "customers.col.customer_id": "What is the customer ID? Who is this borrower?",
    "customers.col.pan_number": "What is the customer's PAN? What is their tax ID? Permanent Account Number?",
    "customers.col.occupation": "What does the customer do for a living? Are they salaried or self-employed?",
    "customers.col.income_band": "What is the customer's salary? How much do they earn? Income bracket?",
    "kyc_documents.col.doc_type": "What identity proof was submitted? Passport, Aadhaar, Voter ID validation.",
    
    # Loan Lifecycle & Payments
    "loans.col.disbursed_amount": "How much was the loan for? What was the principal disbursed?",
    "loans.col.interest_rate": "What is the interest rate? How much interest is charged? What is the APR?",
    "loans.col.status": "Is the loan active or closed? Is it a non-performing asset (NPA)?",
    "loan_products.col.product_type": "What kind of loans are offered? Gold loan, personal loan, vehicle finance catalog.",
    "loan_applications.col.status": "Was the application approved or rejected? Pending lending pipeline.",
    "emi_schedule.col.emi_amount": "What is the monthly installment? How much is owed each month? Amortization breakdown.",
    "payments.col.payment_amount": "How much was repaid? Paid EMIs, successful collections and transactions.",
    
    # Branches & Employees
    "branches.col.branch_name": "Where is the branch located? Which city is the branch in?",
    "employees.col.role": "What is the employee's job? Are they a loan officer or branch manager?",
    "zoho_employee_records.col.designation": "What is the employee's HR designation? Are they a manager?",
    "zoho_employee_records.col.performance_rating": "How did the employee perform? What is their rating?",
    "zoho_employee_records.col.reporting_manager": "Who is the manager? What is the manager's name? Who runs the branch?",
    "incentive_payouts.col.bonus_amount": "What is the employee bonus? How much incentive was paid? Staff commission payout amount.",
    
    # Risk, Compliance & Collections
    "customer_risk_scores.col.credit_score": "What is the customer's credit score? How risky is this borrower? What is the CIBIL score?",
    "customer_risk_scores.col.risk_category": "Is the borrower high risk or low risk?",
    "compliance_flags.col.flag_type": "Why was the compliance flag raised? Was it an AML or PEP check? KYC mismatch?",
    "overdue_accounts.col.dpd_bucket": "Who is late on payments? How many days past due (DPD)? Defaulted and delinquent accounts.",
    "collections_activity.col.outcome": "Did the recovery agent collect the money? Repossession and field visit outcomes.",
    
    # Marketing & CRM
    "campaigns.col.budget_spent": "How much did the campaign cost? What was the marketing spend?",
    "campaigns.col.cost_per_lead": "What is the CPL? How much does a lead cost?",
    "campaign_responses.col.response_type": "Did the customer click the marketing email? Promo conversion.",
    "leads.col.source": "Where did the prospect come from? Sales funnel generation.",
    "lead_activities.col.activity_type": "Did the sales rep call the prospect? Follow-up logs.",
    
    # Support Tickets
    "support_tickets.col.issue_type": "What is the customer complaining about? Grievances and helpdesk.",
    "ticket_interactions.col.agent_notes": "What did customer service say? Support chat transcripts.",
    
    # Treasury & Insurance
    "funding_sources.col.interest_rate": "What is the borrowing cost for the NBFC? What is the cost of funds?",
    "treasury_transactions.col.transaction_type": "Was it a drawdown or a principal repayment?",
    "insurance_policies.col.premium_amount": "How much does the coverage cost? Policy premium.",
    "insurance_claims.col.claim_status": "Was the insurance payout approved? Claim settlement.",
    
    # System & Audit
    "audit_logs.col.action": "Who changed this record? System history and security footprint."
}

def generate_questions(chunk_id: str, clean_text: str = "") -> str:
    """
    1. Checks if a human-curated static question set exists in DOMAIN_MAPPING.
    2. If not, uses Gemini to dynamically generate questions for the new/unmapped schema.
    """
    for key, questions in DOMAIN_MAPPING.items():
        if key in chunk_id:
            return questions
            
    # Gemini LLM Fallback for new schema items not yet in dictionary
    print(f"   [Gemini Auto-Augment] Generating questions for unmapped chunk: '{chunk_id}'...")
    try:
        model = genai.GenerativeModel("gemini-3.6-flash")
        prompt = f"""
Given the following database column/table description, generate 3-4 domain-specific business questions that a user might ask to find this data.
Use synonyms and industry terms. Output ONLY the questions separated by spaces.

Description:
{clean_text}
"""
        response = model.generate_content(prompt)
        time.sleep(1) # Prevent API rate limit
        return response.text.strip().replace('\n', ' ')
    except Exception as e:
        print(f"   [Gemini Warning] Could not generate questions for {chunk_id}: {e}")
        parts = chunk_id.split('.')
        name = parts[-1].replace('_', ' ') if parts else "data"
        return f"What is the {name}? Tell me about {name}."

def main():
    bq = bigquery.Client(project=PROJECT_ID)
    
    print("Fetching chunks to augment (Dict Method)...")
    query = f"""
        SELECT chunk_id, chunk_text 
        FROM `{PROJECT_ID}.{DATASET}.table_chunks` 
    """
    rows = bq.query(query).result()
    chunks = list(rows)
    print(f"Found {len(chunks)} chunks to augment.")
    
    augmented_data = []
    
    for row in chunks:
        chunk_id = row.chunk_id
        chunk_text = row.chunk_text
        
        # Strip old questions prefix if present to prevent duplication
        clean_text = chunk_text.split(" --- ", 1)[-1] if " --- " in chunk_text else chunk_text
        
        questions = generate_questions(chunk_id, clean_text)
        new_text = f"Questions: {questions} --- {clean_text}"
        
        augmented_data.append({
            "chunk_id": chunk_id,
            "chunk_text": new_text
        })
            
    if not augmented_data:
        print("No chunks augmented.")
        return
        
    print(f"\nWriting {len(augmented_data)} augmented chunks back to BigQuery staging...")
    
    stg_table_id = f"{PROJECT_ID}.{DATASET}.chunks_stg_{uuid.uuid4().hex[:6]}"
    
    # Define schema for staging table
    schema = [
        bigquery.SchemaField("chunk_id", "STRING"),
        bigquery.SchemaField("chunk_text", "STRING"),
    ]
    
    job_config = bigquery.LoadJobConfig(schema=schema)
    
    load_job = bq.load_table_from_json(augmented_data, stg_table_id, job_config=job_config)
    load_job.result()  # Waits for table load to complete.
    
    print(f"Staging table {stg_table_id} loaded. Updating main table...")
    
    update_sql = f"""
        UPDATE `{PROJECT_ID}.{DATASET}.table_chunks` main
        SET chunk_text = stg.chunk_text
        FROM `{stg_table_id}` stg
        WHERE main.chunk_id = stg.chunk_id
    """
    bq.query(update_sql).result()
    
    print("Main table updated! Cleaning up staging table...")
    bq.delete_table(stg_table_id)
    
    print("All done!")

if __name__ == "__main__":
    main()
