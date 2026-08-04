"""
csv_to_excel.py — Convert generator output CSVs into Excel workbooks.

Usage:
    python csv_to_excel.py                  # converts everything under output/
    python csv_to_excel.py output/lms        # convert just one system's folder
    python csv_to_excel.py output/lms/loans.csv   # convert a single CSV

Behavior:
    - Given a folder containing CSVs (e.g. output/lms/), produces ONE .xlsx
      with one sheet per CSV (sheet name = table name), saved as
      output/lms/lms.xlsx
    - Given the top-level output/ folder, does this per system-subfolder,
      producing output/base/base.xlsx, output/los/los.xlsx, etc.
    - Given a single .csv file, converts just that file to a matching .xlsx
      next to it.

Notes:
    - Excel sheet names are capped at 31 characters and can't contain
      [ ] : * ? / \\ — table names here are all short/clean so this is a
      non-issue, but long_table_name_examples get truncated automatically.
    - Large tables (emi_schedule, payments, audit_logs, etc.) can run into
      the millions of rows — Excel's hard limit is 1,048,576 rows per sheet.
      If a table exceeds that, this script will warn and truncate rather
      than fail silently.
"""

import sys
from pathlib import Path
import pandas as pd

EXCEL_ROW_LIMIT = 1_048_576 - 1  # leave room for the header row


def sheet_name_from(table_name: str) -> str:
    invalid = set('[]:*?/\\')
    cleaned = "".join(c for c in table_name if c not in invalid)
    return cleaned[:31]


def convert_csv_to_sheet(csv_path: Path, writer: pd.ExcelWriter):
    df = pd.read_csv(csv_path)
    if len(df) > EXCEL_ROW_LIMIT:
        print(f"  WARNING: {csv_path.name} has {len(df):,} rows, "
              f"exceeding Excel's {EXCEL_ROW_LIMIT:,} row limit per sheet — truncating.")
        df = df.iloc[:EXCEL_ROW_LIMIT]
    sheet = sheet_name_from(csv_path.stem)
    df.to_excel(writer, sheet_name=sheet, index=False)
    print(f"  {csv_path.name:<30} -> sheet '{sheet}'  ({len(df):,} rows, {len(df.columns)} cols)")


def convert_folder(folder: Path):
    csvs = sorted(folder.glob("*.csv"))
    if not csvs:
        return
    out_path = folder / f"{folder.name}.xlsx"
    print(f"\n{folder} -> {out_path.name}")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for csv_path in csvs:
            convert_csv_to_sheet(csv_path, writer)


def convert_single_file(csv_path: Path):
    out_path = csv_path.with_suffix(".xlsx")
    print(f"\n{csv_path} -> {out_path.name}")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        convert_csv_to_sheet(csv_path, writer)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output")

    if target.is_file() and target.suffix == ".csv":
        convert_single_file(target)
        return

    if not target.exists():
        print(f"Path not found: {target}")
        sys.exit(1)

    # If target itself has CSVs directly in it, treat it as one system folder.
    if list(target.glob("*.csv")):
        convert_folder(target)
        return

    # Otherwise assume it's the top-level output/ dir — convert each subfolder.
    subfolders = sorted(p for p in target.iterdir() if p.is_dir())
    if not subfolders:
        print(f"No CSVs or system subfolders found under {target}")
        return
    for sub in subfolders:
        convert_folder(sub)

    print("\nDone.")


if __name__ == "__main__":
    main()
