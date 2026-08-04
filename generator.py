"""
Config-driven mock data generator for the NBFC MVP.
Reads YAML system definitions from systems/, generates referentially-consistent
CSVs into output/, ready to load into BigQuery Sandbox.
"""

import gc
import yaml
import uuid
import numpy as np
import pandas as pd
from pathlib import Path
from faker import Faker

fake = Faker("en_IN")
np.random.seed(42)  # reproducible runs

SYSTEMS_DIR = Path(__file__).parent / "systems"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Column-level generators (used for normal, non-derived tables)
# ---------------------------------------------------------------------------

def gen_column(spec, n, context):
    kind = spec["generator"]

    if kind == "uuid":
        return [str(uuid.uuid4()) for _ in range(n)]

    if kind == "choice":
        return list(np.random.choice(spec["values"], n))

    if kind == "weighted_choice":
        values, weights = zip(*spec["values"].items())
        return list(np.random.choice(values, n, p=weights))

    if kind == "weighted_choice_nullable":
        # only fills a value where the null_when condition (checked externally) is false;
        # here we just generate the pool, filtering is applied by caller after the fact
        values, weights = zip(*spec["values"].items())
        return list(np.random.choice(values, n, p=weights))

    if kind == "fixed_sequence":
        vals = spec["values"]
        reps = int(np.ceil(n / len(vals)))
        return (vals * reps)[:n]

    if kind == "normal":
        arr = np.random.normal(spec["mean"], spec["stddev"], n)
        if "min_clip" in spec or "max_clip" in spec:
            arr = np.clip(arr, spec.get("min_clip", -np.inf), spec.get("max_clip", np.inf))
        return np.round(arr, 2)

    if kind == "uniform":
        arr = np.random.uniform(spec["min"], spec["max"], n)
        return np.round(arr, 2)

    if kind == "date_range":
        # NOTE: previously used pd.Timestamp(...).value (nanoseconds since epoch,
        # ~1.7e18) fed straight into np.random.randint, which overflows int32
        # (max ~2.1e9) and raises "high is out of bounds for int32".
        # Fixed by generating a small integer day-offset instead, then adding
        # it as a timedelta onto the start date.
        start = pd.Timestamp(spec["start"])
        end = pd.Timestamp(spec["end"])
        day_span = (end - start).days
        if day_span <= 0:
            raise ValueError(f"date_range: end ({end}) must be after start ({start})")
        offsets = np.random.randint(0, day_span, n)  # small int, no overflow
        return (start + pd.to_timedelta(offsets, unit="D")).date

    if kind == "ref":
        pool = context[spec["ref_table"]]
        if "ref_filter" in spec:
            col, val = spec["ref_filter"].split("=")
            pool = pool[pool[col] == val]
        return list(np.random.choice(pool[spec["ref_key"]].values, n))

    if kind == "ref_filtered":
        pool = context[spec["ref_table"]]
        pool = pool[pool[spec["filter_col"]] == spec["filter_val"]]
        return list(np.random.choice(pool[spec["ref_key"]].values, n))

    if kind == "same_as_ref":
        # pulls a value from a row already tied via a join key already generated in this table
        raise RuntimeError("same_as_ref must be handled in table-level pass, not column pass")

    if kind == "person_name":
        return [fake.name() for _ in range(n)]

    if kind == "branch_name":
        return [f"{fake.city()} Branch" for _ in range(n)]

    if kind == "city":
        return [fake.city() for _ in range(n)]

    if kind == "phone":
        return [f"9{np.random.randint(100000000, 999999999)}" for _ in range(n)]

    if kind == "pan":
        letters = lambda k: "".join(np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), k))
        return [f"{letters(5)}{np.random.randint(1000,9999)}{letters(1)}" for _ in range(n)]

    raise ValueError(f"Unknown generator kind: {kind}")


def generate_standard_table(table_cfg, context):
    n = table_cfg["row_count"]
    data = {}

    # first pass: everything except same_as_ref (needs another column already resolved)
    same_as_specs = []
    for col in table_cfg["columns"]:
        if col["generator"] == "same_as_ref":
            same_as_specs.append(col)
            continue
        data[col["name"]] = gen_column(col, n, context)

    df = pd.DataFrame(data)

    # second pass: same_as_ref columns — look up the value from the referenced table
    # via the join_on column already present in this df
    for col in same_as_specs:
        join_col = col["join_on"]
        ref_lookup = context[col["ref_table"]].set_index(join_col)[col["ref_key"]]
        df[col["name"]] = df[join_col].map(ref_lookup)

    # handle nullable-conditional columns (rejection_reason etc.)
    for col in table_cfg["columns"]:
        if col["generator"] == "weighted_choice_nullable":
            condition = col["null_when"]  # e.g. "status != rejected"
            field, op, val = condition.split()
            mask = df[field] != val if op == "!=" else df[field] == val
            df.loc[mask, col["name"]] = None

    return df


# ---------------------------------------------------------------------------
# Amortization logic — the one piece that needs real sequential business math,
# not random sampling. Reducing-balance EMI schedule per loan.
# ---------------------------------------------------------------------------

def build_emi_schedule(loans_df):
    """
    Vectorized reducing-balance amortization: instead of looping loan-by-loan
    in Python (too slow at 100K+ loans), group loans by tenure_months and run
    the recurrence across the whole group at once with NumPy, one iteration
    per month (max 60 iterations) rather than one iteration per loan.
    """
    all_frames = []

    for tenure, group in loans_df.groupby("tenure_months"):
        tenure = int(tenure)
        n = len(group)
        principal = group["disbursed_amount"].to_numpy(dtype=float)
        monthly_rate = group["interest_rate"].to_numpy(dtype=float) / 12 / 100
        loan_ids = group["loan_id"].to_numpy()
        disb_dates = pd.to_datetime(group["disbursement_date"]).to_numpy()

        with np.errstate(divide="ignore", invalid="ignore"):
            emi = np.where(
                monthly_rate == 0,
                principal / tenure,
                principal * monthly_rate * (1 + monthly_rate) ** tenure /
                ((1 + monthly_rate) ** tenure - 1)
            )

        outstanding = principal.copy()
        disb_ts = pd.Series(disb_dates)

        month_chunks = []
        for month_no in range(1, tenure + 1):
            interest_component = np.round(outstanding * monthly_rate, 2)
            principal_component = np.round(emi - interest_component, 2)
            outstanding = np.round(outstanding - principal_component, 2)
            due_dates = (disb_ts + pd.DateOffset(months=month_no)).dt.date.to_numpy()

            month_chunks.append(pd.DataFrame({
                "emi_id": [str(uuid.uuid4()) for _ in range(n)],
                "loan_id": loan_ids,
                "installment_no": month_no,
                "due_date": due_dates,
                "emi_amount": np.round(emi, 2),
                "principal_component": principal_component,
                "interest_component": interest_component,
                "outstanding_after": np.clip(outstanding, 0, None),
            }))

        all_frames.append(pd.concat(month_chunks, ignore_index=True))
        print(f"    amortization: tenure={tenure} months, {n:,} loans -> {n*tenure:,} EMI rows")

    return pd.concat(all_frames, ignore_index=True)


def build_payments(emi_df, loans_df):
    """
    Realistic payment behavior, driven by each loan's overall status:
      - closed loans: every EMI paid, mostly on time
      - active loans: EMIs paid up to 'today', a few days of jitter
      - npa/written_off loans: payments stop partway through, simulating default

    Processed per tenure-group (same grouping as EMI generation) to keep peak
    memory bounded instead of merging the full multi-million-row EMI table at once.
    """
    today = pd.Timestamp("2026-08-01")
    status_map = loans_df.set_index("loan_id")["status"]
    tenure_map = loans_df.set_index("loan_id")["tenure_months"]

    jitter_choices = np.array([-2, -1, 0, 0, 0, 1, 3, 7, 15])
    jitter_probs = np.array([0.05, 0.1, 0.35, 0.001, 0.001, 0.199, 0.1, 0.1, 0.099])
    jitter_probs = jitter_probs / jitter_probs.sum()

    payment_frames = []

    for loan_id_batch_start in range(0, len(loans_df), 20000):
        batch = loans_df.iloc[loan_id_batch_start: loan_id_batch_start + 20000]
        batch_ids = set(batch["loan_id"])
        batch_emi = emi_df[emi_df["loan_id"].isin(batch_ids)].copy()
        if batch_emi.empty:
            continue

        batch_emi["status"] = batch_emi["loan_id"].map(status_map)
        batch_emi["tenure"] = batch_emi["loan_id"].map(tenure_map)

        statuses = batch_emi["status"].to_numpy()
        pay_fraction = np.where(
            statuses == "closed", 1.0,
            np.where(
                np.isin(statuses, ["npa", "written_off"]),
                np.random.uniform(0.2, 0.6, len(statuses)),
                np.random.uniform(0.5, 0.95, len(statuses)),
            )
        )
        n_to_pay = (batch_emi["tenure"].to_numpy() * pay_fraction).astype(int)
        payable = batch_emi[batch_emi["installment_no"].to_numpy() <= n_to_pay].copy()

        due_ts = pd.to_datetime(payable["due_date"])
        payable = payable[due_ts.to_numpy() <= today.to_datetime64()]
        if payable.empty:
            continue

        n = len(payable)
        jitters = np.random.choice(jitter_choices, n, p=jitter_probs)
        payment_dates = (pd.to_datetime(payable["due_date"]) + pd.to_timedelta(jitters, unit="D")).dt.date

        payment_frames.append(pd.DataFrame({
            "payment_id": [str(uuid.uuid4()) for _ in range(n)],
            "emi_id": payable["emi_id"].to_numpy(),
            "loan_id": payable["loan_id"].to_numpy(),
            "amount_paid": payable["emi_amount"].to_numpy(),
            "payment_date": payment_dates.to_numpy(),
            "payment_mode": np.random.choice(
                ["upi", "neft", "auto_debit", "cash"], n, p=[0.4, 0.25, 0.25, 0.1]
            ),
        }))

    return pd.concat(payment_frames, ignore_index=True)


def build_overdue_accounts(emi_df, payments_df):
    """
    A loan is overdue if it has EMIs whose due_date has passed but no matching payment exists.
    DPD (days past due) computed from the oldest unpaid, past-due EMI.
    """
    today = pd.Timestamp("2026-08-01")
    paid_emi_ids = set(payments_df["emi_id"])

    unpaid_past_due = emi_df[
        (~emi_df["emi_id"].isin(paid_emi_ids)) &
        (pd.to_datetime(emi_df["due_date"]) <= today)
    ].copy()

    if unpaid_past_due.empty:
        return pd.DataFrame(columns=["loan_id", "days_past_due", "dpd_bucket", "overdue_amount"])

    unpaid_past_due["days_past_due"] = (today - pd.to_datetime(unpaid_past_due["due_date"])).dt.days

    grouped = unpaid_past_due.groupby("loan_id").agg(
        days_past_due=("days_past_due", "max"),
        overdue_amount=("emi_amount", "sum"),
    ).reset_index()

    def bucket(d):
        if d <= 30: return "0-30"
        if d <= 60: return "31-60"
        if d <= 90: return "61-90"
        return "90+"

    grouped["dpd_bucket"] = grouped["days_past_due"].apply(bucket)
    return grouped


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run():
    context = {}
    system_files = sorted(SYSTEMS_DIR.glob("*.yaml"))

    for path in system_files:
        config = yaml.safe_load(path.read_text())
        print(f"\n=== {config['system_name']} ({path.name}) ===")

        # Each system gets its own output subfolder, e.g. output/base/, output/los/,
        # output/lms/, output/incentive/, output/zoho/ — derived from the filename
        # (numeric prefix stripped) rather than system_name, so it stays a clean,
        # predictable folder/table path with no spaces or punctuation to worry about.
        stem = path.stem  # e.g. "00_base", "03_incentive"
        parts = stem.split("_", 1)
        folder_name = parts[1] if len(parts) == 2 and parts[0].isdigit() else stem
        system_out_dir = OUTPUT_DIR / folder_name
        system_out_dir.mkdir(parents=True, exist_ok=True)

        for table_cfg in config["tables"]:
            name = table_cfg["name"]
            ttype = table_cfg.get("type", "standard")

            if ttype == "standard":
                df = generate_standard_table(table_cfg, context)

            elif ttype == "amortization_schedule":
                loans_df = context[table_cfg["source_table"]]
                df = build_emi_schedule(loans_df)

            elif ttype == "derived_payments":
                emi_df = context[table_cfg["source_table"]]
                df = build_payments(emi_df, context["loans"])

            elif ttype == "derived_overdue":
                emi_df = context[table_cfg["source_table"]]
                df = build_overdue_accounts(emi_df, context["payments"])

            else:
                raise ValueError(f"Unknown table type: {ttype}")

            context[name] = df
            out_path = system_out_dir / f"{name}.csv"
            df.to_csv(out_path, index=False)
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"  {name:<24} {len(df):>10,} rows   {size_mb:>8.1f} MB   -> {out_path.relative_to(OUTPUT_DIR)}")
            gc.collect()

    all_csvs = list(OUTPUT_DIR.glob("**/*.csv"))
    total_mb = sum(f.stat().st_size for f in all_csvs) / (1024 * 1024)
    print(f"\nTOTAL OUTPUT SIZE: {total_mb:.1f} MB across {len(all_csvs)} tables, "
          f"organized into {len(system_files)} system folders under {OUTPUT_DIR}/")


if __name__ == "__main__":
    run()