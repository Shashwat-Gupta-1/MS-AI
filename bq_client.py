"""
bq_client.py — the one place the rest of the codebase talks to BigQuery
from. Every script/module should import get_client() (or the role-scoped
variant) from here rather than instantiating google.cloud.bigquery.Client
directly, so auth, retries, and project config stay in one place.
"""

from functools import lru_cache
import pandas as pd
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter, ArrayQueryParameter

from config import PROJECT_ID


@lru_cache(maxsize=1)
def get_client() -> bigquery.Client:
    """Single shared admin-level client, created once and reused across
    the app. Used for setup/DDL/loading and for any retrieval-metadata
    query (table_docs, entity_relationships, etc.) that isn't gated by
    row-level business data access."""
    return bigquery.Client(project=PROJECT_ID)


@lru_cache(maxsize=None)
def get_client_for_role(role_name: str) -> bigquery.Client:
    """
    Role-scoped client -- THIS is what should execute final generated SQL
    against business-data tables, not get_client(). It should authenticate
    as (or impersonate) the role's own IAM-scoped identity, so BigQuery's
    own authorized-view grants (see access_control/generated_role_grants.sh)
    are the thing actually enforcing access -- not just application logic.

    Placeholder implementation below uses the default credentials for
    every role, which does NOT enforce anything by itself. Replace this
    with real per-role service-account impersonation before this touches
    production data:

        from google.auth import impersonated_credentials
        target_principal = f"{role_name}@your-project.iam.gserviceaccount.com"
        source_credentials, _ = google.auth.default()
        creds = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_principal,
            target_scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    """
    # WARNING: Placeholder implementation using default credentials for MVP dev mode.
    # In production, this MUST use per-role service account impersonation so BigQuery's
    # IAM boundary holds independently of application-level logic.
    return bigquery.Client(project=PROJECT_ID)




def run_query(sql: str) -> pd.DataFrame:
    """Run SQL with the admin client and return a DataFrame."""
    return get_client().query(sql).to_dataframe()


def run_query_params(sql: str, params: list) -> pd.DataFrame:
    """
    Parameterized query -- always prefer this over string-formatting
    values into SQL. Example:

        run_query_params(
            "SELECT * FROM t WHERE domain IN UNNEST(@domains)",
            [ArrayQueryParameter("domains", "STRING", ["loan", "collections"])],
        )
    """
    job_config = QueryJobConfig(query_parameters=params)
    return get_client().query(sql, job_config=job_config).to_dataframe()


def run_query_as_role(sql: str, role_name: str) -> pd.DataFrame:
    """Run final generated SQL under a role's own scoped credentials --
    this is the call site for Stage 7 (execution) in the pipeline design."""
    return get_client_for_role(role_name).query(sql).to_dataframe()
