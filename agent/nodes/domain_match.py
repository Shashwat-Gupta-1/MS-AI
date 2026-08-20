"""
agent/nodes/domain_match.py — Node [2]: Role-Scoped Domain Classifier & RBAC Validator.
Evaluates question against allowed role domains using keyword pre-match + Groq LLM classifier.
Combines signals via combine_domain_signals() and rejects unauthorized access securely.
"""

import time
import yaml
from pathlib import Path
from typing import Dict, Any, List, Set
from langchain_core.messages import SystemMessage, HumanMessage

from config import METADATA_DIR
from agent.state import GraphState
from agent.groq_client import invoke_groq_with_retry
from agent.logging_store import DEFAULT_LOGGING_STORE

try:
    from query_router import decompose_query
except ImportError:
    decompose_query = None


def load_role_domain_access() -> Dict[str, Any]:
    """Load role -> allowed_domains mapping from role_domain_access.yaml."""
    path = METADATA_DIR / "role_domain_access.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("roles", {})


def load_all_domains() -> Set[str]:
    """Extract full set of unique domains from domain_tags.yaml."""
    path = METADATA_DIR / "domain_tags.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    domains = set()
    for table_entry in data.get("tables", []):
        domains.update(table_entry.get("domain_tags", []))
    return domains


def load_domain_summaries() -> str:
    """Load domain_summaries.md text."""
    path = METADATA_DIR / "domain_summaries.md"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


ROLE_ACCESS_MAP = load_role_domain_access()
ALL_KNOWN_DOMAINS = load_all_domains()
DOMAIN_SUMMARIES_TEXT = load_domain_summaries()


def get_allowed_domains_for_role(role_name: str) -> Set[str]:
    """Resolve allowed domains for a given role name."""
    role_info = ROLE_ACCESS_MAP.get(role_name, {})
    allowed = role_info.get("allowed_domains", [])
    if allowed == "*" or allowed == ["*"]:
        return ALL_KNOWN_DOMAINS
    return set(allowed)


def keyword_domain_match(question: str, candidate_domains: Set[str]) -> List[str]:
    """Deterministic keyword match against question text for candidate domains."""
    q_lower = question.lower()
    matched = []
    
    # Common domain keyword associations
    keyword_map = {
        "loan": ["loan", "disbursement", "emi", "principal", "interest", "borrower", "sanction"],
        "collections": ["collection", "field visit", "overdue", "dpd", "recovery", "default", "npa", "delinquent"],
        "hr": ["employee", "staff", "zoho", "designation", "rating", "performance", "payout", "bonus", "department"],
        "ops": ["branch", "jaipur", "delhi", "mumbai", "location", "city"],
        "kyc": ["kyc", "aadhaar", "pan", "document", "identity", "passport"],
        "risk": ["risk", "credit score", "foir", "cibil", "underwriting"],
        "leads": ["lead", "prospect", "funnel", "conversion"],
        "sales": ["sales", "rep", "agent", "deal"],
        "marketing": ["campaign", "channel", "ad", "marketing"],
        "treasury": ["treasury", "ncd", "borrowing facility", "funding"],
        "finance": ["finance", "cash flow", "balance sheet"],
        "insurance": ["insurance", "claim", "policy", "premium"],
        "cross_sell": ["cross sell", "cross-sell", "rider"],
        "compliance": ["compliance", "flag", "aml", "pep", "audit log"],
        "audit": ["audit", "log"],
        "support": ["ticket", "support", "issue", "complaint"],
        "customer_service": ["customer service", "interaction"],
        "incentive": ["incentive", "bonus", "payout"],
    }
    
    for dom in candidate_domains:
        keywords = keyword_map.get(dom, [dom])
        if any(kw in q_lower for kw in keywords):
            matched.append(dom)
            
    return matched


def combine_domain_signals(llm_result: List[str], keyword_result: List[str]) -> List[str]:
    """
    Section 3a: Combine LLM and Keyword signals behind a single function.
    LLM result is primary; keyword result acts as a tie-breaker/sanity check.
    """
    final = list(dict.fromkeys(llm_result + keyword_result))
    return final


DOMAIN_CLASSIFIER_PROMPT = """You are a domain classification assistant for an NBFC data warehouse.
Your task is to classify the user's analytical question into one or more of the PERMITTED business domains listed below.

[PERMITTED DOMAINS & SUMMARIES]
{allowed_summaries}

Rules:
1. Select ONLY from the permitted domains listed above. Do NOT output any domain not listed.
2. Output your answer as a simple comma-separated list of domain names (e.g. "loan, collections").
3. If no permitted domain matches the question, output EXACTLY "NONE".
"""


def domain_match_node(state: GraphState) -> Dict[str, Any]:
    """LangGraph node classifying domain and validating role authorization."""
    start_time = time.time()
    question = state.get("question", "")
    session_id = state.get("session_id", "default")
    role = state.get("role", "unknown")
    
    # 2a: Get allowed domains
    allowed_domains = get_allowed_domains_for_role(role)
    
    if not allowed_domains:
        res = {
            "status": "rejected",
            "final_response": "This question needs data outside your role's access.",
            "allowed_domains": [],
            "final_domains": [],
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="domain_match",
            input_data=question,
            output_data="No allowed domains for role.",
            success=False,
            failure_reason="Role has no permitted domains.",
            latency_ms=(time.time() - start_time) * 1000,
        )
        return res

    # 2b: Keyword match signal against ALL known domains (for unauthorized domain detection)
    keyword_matched = keyword_domain_match(question, ALL_KNOWN_DOMAINS)

    
    # 2c: Decompose query & classify domain using query_router if available
    llm_matched = []
    extracted_filters = []
    search_concept = question
    
    if decompose_query is not None:
        try:
            decomp = decompose_query(question)
            search_concept = decomp.get("search_concept", question)
            extracted_filters = decomp.get("filters", [])
            decomp_domains = [d.lower() for d in decomp.get("domains", [])]
            for dom in decomp_domains:
                if dom in allowed_domains and dom not in llm_matched:
                    llm_matched.append(dom)
        except Exception as e:
            logger.warning(f"decompose_query error: {e}")

    if not llm_matched:
        filtered_summaries = []
        for line in DOMAIN_SUMMARIES_TEXT.split("\n"):
            if any(dom in line.lower() for dom in allowed_domains):
                filtered_summaries.append(line)
        summary_context = "\n".join(filtered_summaries) if filtered_summaries else DOMAIN_SUMMARIES_TEXT
        
        prompt = DOMAIN_CLASSIFIER_PROMPT.format(allowed_summaries=summary_context)
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"User Role: {role}\nQuestion: {question}"),
        ]
        
        try:
            response = invoke_groq_with_retry(messages, temperature=0.0)
            meta = getattr(response, "response_metadata", {}) or {}
            llm_model = meta.get("model_name")
            tokens_used = meta.get("token_usage")
            raw_output = response.content.strip().lower()
            if "none" not in raw_output:
                for item in raw_output.split(","):
                    dom = item.strip()
                    if dom in allowed_domains:
                        llm_matched.append(dom)
        except Exception:
            llm_matched = []

    # 2d: Combine signals safely
    unauth_keywords = [d for d in keyword_matched if d not in allowed_domains]
    auth_keywords = [d for d in keyword_matched if d in allowed_domains]

    if unauth_keywords and not auth_keywords:
        # Question explicitly targets unauthorized domains; override any LLM hallucinations
        final_matched = []
    else:
        final_matched = combine_domain_signals(llm_matched, keyword_matched)
    
    # Security Check: Must overlap with allowed domains
    valid_overlap = [d for d in final_matched if d in allowed_domains]

    
    if not valid_overlap:
        # Rejection message must NEVER name blocked domains or tables
        res = {
            "status": "rejected",
            "final_response": "This question needs data outside your role's access.",
            "allowed_domains": list(allowed_domains),
            "keyword_matched_domains": keyword_matched,
            "llm_matched_domains": llm_matched,
            "final_domains": [],
        }
        DEFAULT_LOGGING_STORE.log_stage(
            session_id=session_id,
            role=role,
            turn_index=0,
            stage="domain_match",
            input_data=question,
            output_data="No valid overlapping domain.",
            success=False,
            failure_reason="Role unauthorized for question domains.",
            latency_ms=(time.time() - start_time) * 1000,
            llm_model=llm_model,
            tokens_used=tokens_used,
            extra_fields={
                "keyword_matched": keyword_matched,
                "llm_matched": llm_matched,
                "final_matched": [],
            }
        )
        return res
        
    # 2e: Concept extraction for clean vector search
    import re
    # Clean math operators, question words, and entity literals for vector search focus
    clean_concept = re.sub(r"\b(show|tell|give|list|me|what|who|where|how|many|much|is|are|the|a|an|total|average|mean|highest|lowest|sum|count)\b", "", question, flags=re.IGNORECASE).strip()
    search_concept = clean_concept if len(clean_concept) > 3 else question

    res = {
        "allowed_domains": list(allowed_domains),
        "keyword_matched_domains": keyword_matched,
        "llm_matched_domains": llm_matched,
        "final_domains": valid_overlap,
        "search_concept": search_concept,
    }
    
    DEFAULT_LOGGING_STORE.log_stage(
        session_id=session_id,
        role=role,
        turn_index=0,
        stage="domain_match",
        input_data=question,
        output_data=valid_overlap,
        success=True,
        latency_ms=(time.time() - start_time) * 1000,
        llm_model=llm_model,
        tokens_used=tokens_used,
        extra_fields={
            "keyword_matched": keyword_matched,
            "llm_matched": llm_matched,
            "final_matched": valid_overlap,
        }
    )

    return res
