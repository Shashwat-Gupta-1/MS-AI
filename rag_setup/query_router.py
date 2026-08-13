import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def decompose_query(raw_query: str) -> dict:
    """
    Uses Gemini to decompose a raw user question into a core search concept and filters.
    """
    model = genai.GenerativeModel("gemini-3.5-flash")
    
    prompt = f"""
You are a SQL Query Decomposer. 
Take the user's natural language question and break it into a strict JSON format with exactly these three fields:
1. "search_concept": Extract the core business concepts, domain states, and metrics (e.g. "defaulted accounts past due", "PAN number", "marketing spend"). DO NOT strip domain status terms like "salaried", "self-employed","defaulted", "overdue", "active", "NPA", or "past due". Strip ONLY math operations (highest, lowest, average, count, sum), question words (who, what, show me), and literal entity values (person names, city names, campaign names, customer IDs).
2. "filters": A list of specific literal entity values and timeframes mentioned in the query (e.g. "Mumbai", "Rohit", "CUST-12345", "Diwali", "last month", "2023"). Do NOT include business concepts or status terms here.
3. "domains": A list of domains that the question relates to. Choose from this exact list of valid domains: ["loan", "sales", "hr", "support", "risk", "compliance", "collections", "insurance", "treasury", "branch"]. You can choose more than one if the question spans multiple domains.

User Question: "{raw_query}"

Return ONLY valid JSON.
"""

    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json", "temperature": 0.0}
    )
    
    try:
        return json.loads(response.text)
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        # Fallback to returning the raw query if parsing fails
        return {"search_concept": raw_query, "filters": [], "domains": []}
