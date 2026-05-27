"""Pure validation rules, No streamlit, no SQL - easy to unit test."""

import re
import pandas as pd

EMP_ID_PATTERN = re.compile(r"^EMP\d{4}$")
REQUIRED_FIELDS = ("name", "dept", "title")

def validate_employee_diff(
        original_df: pd.DataFrame, diff: dict
) -> tuple[list[str], list[str]]:
    """Check a data_editor diff. Returns (errors, warnings).
    Errors block save; warnings are advisory."""
    errors: list[str] = []
    warnings: list[str] = []
    
    existing_ids = set(original_df["employee_id"])
    existing_depts = set(original_df["dept"])
    existing_titles = set(original_df["title"])

    # ---- ADDED rows ----
    added_ids_in_batch: list[str] = []
    for i, row in enumerate(diff.get("added_rows", []), start=1):
        emp_id = (row.get("employee_id") or "").strip()
        if not EMP_ID_PATTERN.fullmatch(emp_id):
            errors.append(f"Added row {i}: employee_id '{emp_id}' must match EMP9999")
        if emp_id in existing_ids:
            errors.append(f"Added row {i}: employee_id '{emp_id}' already exists")
        if emp_id in added_ids_in_batch:
            errors.append(f"Added row {i}: employee_id '{emp_id}' duplicated in this batch")
        added_ids_in_batch.append(emp_id)

        for f in REQUIRED_FIELDS:
            if not (row.get(f) or "").strip():
                errors.append(f"Added row {i}: '{f}' is required")

        dept = (row.get("dept") or "").strip()
        title = (row.get("title") or "").strip()
        if dept and dept not in existing_depts:
            warnings.append(f"Added row {i}: dept '{dept}' is new — typo?")
        if title and title not in existing_titles:
            warnings.append(f"Added row {i}: title '{title}' is new — typo?")

    # ---- EDITED rows ----
    for idx, changes in diff.get("edited_rows", {}).items():
        row_no = idx + 1
        if "employee_id" in changes:
            errors.append(f"Edited row {row_no}: changing employee_id is not allowed")
        for f in REQUIRED_FIELDS:
            if f in changes and not (changes[f] or "").strip():
                errors.append(f"Edited row {row_no}: '{f}' cannot be empty")

        if "dept" in changes:
            new_dept = (changes["dept"] or "").strip()
            if new_dept and new_dept not in existing_depts:
                warnings.append(f"Edited row {row_no}: dept '{new_dept}' is new — typo?")
        if "title" in changes:
            new_title = (changes["title"] or "").strip()
            if new_title and new_title not in existing_titles:
                warnings.append(f"Edited row {row_no}: title '{new_title}' is new — typo?")

    return errors, warnings