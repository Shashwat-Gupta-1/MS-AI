"""
Role-based domain filtering at retrieval time.

This is the UX layer, NOT the security boundary. It runs right after
Stage A (domain classification) and BEFORE Stage B (table vector search),
so a user gets a clear "that's outside your access" message instead of
either (a) the chatbot silently trying and BigQuery throwing a permissions
error deep in the pipeline, or (b) worse, the chatbot generating SQL against
tables the user's actual BigQuery credentials can't read anyway.

The REAL boundary is the BigQuery authorized views + IAM grants generated
by generate_role_views.py. This filter is a courtesy layer on top of that,
not a replacement for it -- if this code has a bug, the IAM boundary still
holds. If the IAM boundary were the only thing enforcing this, a bug here
would just mean a confusing raw permissions error instead of a helpful one.
"""

import yaml
from pathlib import Path

ROLES = yaml.safe_load(Path("role_domain_access.yaml").read_text())["roles"]
DOMAIN_TAGS = yaml.safe_load(Path("domain_tags_v2.yaml").read_text())
ALL_DOMAINS = sorted({tag for t in DOMAIN_TAGS["tables"] for tag in t["domain_tags"]})


def get_allowed_domains(role_name: str) -> set[str]:
    role = ROLES.get(role_name)
    if role is None:
        raise ValueError(f"Unknown role: {role_name}")
    if role["allowed_domains"] == "*":
        return set(ALL_DOMAINS)
    return set(role["allowed_domains"])


def apply_role_filter(matched_domains: list[str], role_name: str) -> dict:
    """
    Called right after Stage A domain classification.

    Returns:
      {
        "effective_domains": [...],   # domains to actually search within
        "blocked_domains": [...],     # domains the question needed but role can't access
        "fully_blocked": bool         # True if EVERY matched domain was blocked
      }
    """
    allowed = get_allowed_domains(role_name)
    matched = set(matched_domains)

    effective = matched & allowed
    blocked = matched - allowed

    return {
        "effective_domains": sorted(effective),
        "blocked_domains": sorted(blocked),
        "fully_blocked": len(effective) == 0 and len(matched) > 0,
    }


def format_access_message(filter_result: dict, role_name: str) -> str | None:
    """
    Returns a user-facing message if access was partially or fully restricted,
    or None if the question was fully within the role's access.
    """
    if not filter_result["blocked_domains"]:
        return None

    role_desc = ROLES[role_name]["description"]
    blocked = ", ".join(filter_result["blocked_domains"])

    if filter_result["fully_blocked"]:
        return (
            f"This question needs data outside what your role ({role_name}) "
            f"has access to ({blocked}). {role_desc.capitalize()} — this "
            f"question falls outside that scope. If you believe you should "
            f"have access, contact your admin."
        )
    else:
        return (
            f"Note: this answer only includes data your role has access to. "
            f"Some relevant data ({blocked}) was excluded because it's "
            f"outside your role's permitted access."
        )


# ---------------------------------------------------------------------------
# Example usage — how this slots into the pipeline from earlier in the build
# ---------------------------------------------------------------------------

def example_pipeline_stage(question: str, user_role: str):
    # Stage A: domain classification (LLM-based, as designed earlier)
    matched_domains = ["loan", "treasury"]  # placeholder for the real classifier call

    # NEW STEP: role filter, right after Stage A
    filter_result = apply_role_filter(matched_domains, user_role)
    message = format_access_message(filter_result, user_role)

    if filter_result["fully_blocked"]:
        return {"answer": message, "sql": None}  # stop here, don't even attempt retrieval

    # Stage B onward proceeds using ONLY filter_result["effective_domains"],
    # not the original matched_domains -- this is what actually restricts
    # which tables Stage B's vector search is allowed to consider.
    effective_domains = filter_result["effective_domains"]

    # ... vector search, FK expansion, schema fetch, LLM SQL generation ...
    # ... executed via the role's own authorized-view credentials, so even
    #     if this filter were somehow bypassed, BigQuery itself would still
    #     refuse to return data outside views_{role_name}.* ...

    return {
        "effective_domains": effective_domains,
        "access_note": message,  # attach as a caveat even on partial success
    }


if __name__ == "__main__":
    # Quick smoke test across a few roles
    test_cases = [
        ("hr_officer", ["hr", "loan"]),
        ("treasury_manager", ["loan"]),
        ("executive", ["compliance", "treasury", "hr"]),
    ]
    for role, domains in test_cases:
        result = apply_role_filter(domains, role)
        msg = format_access_message(result, role)
        print(f"role={role} matched={domains}")
        print(f"  -> effective={result['effective_domains']} blocked={result['blocked_domains']}")
        if msg:
            print(f"  -> message: {msg}")
        print()
