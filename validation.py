"""Pure validation rules. No streamlit, no SQL — easy to unit test."""

import pandas as pd


def _missing(v) -> bool:
    """True if v counts as not-filled (None, or whitespace-only string)."""
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _norm(v):
    """Normalize for comparison: strip strings, leave others as-is."""
    return v.strip() if isinstance(v, str) else v


def validate_diff(
    table_meta: dict, original_df: pd.DataFrame, diff: dict
) -> tuple[list[str], list[str]]:
    """Check a data_editor diff against a table's metadata.
    Returns (errors, warnings). Errors block save; warnings are advisory.

    table_meta = {"pk_cols": [...], "required_cols": [...]}
    """
    errors: list[str] = []
    warnings: list[str] = []
    pk_cols = table_meta["pk_cols"]
    required_cols = table_meta["required_cols"]

    # Existing PK tuples (for collision detection on added rows)
    existing_pks: set = {
        tuple(_norm(row[c]) for c in pk_cols)
        for _, row in original_df[pk_cols].iterrows()
    }

    # ---- ADDED rows ----
    seen_in_batch: set = set()
    for i, row in enumerate(diff.get("added_rows", []), start=1):
        for f in required_cols:
            if _missing(row.get(f)):
                errors.append(f"Added row {i}: '{f}' is required")

        if not any(_missing(row.get(c)) for c in pk_cols):
            pk_tuple = tuple(_norm(row.get(c)) for c in pk_cols)
            pk_str = ", ".join(f"{c}={v!r}" for c, v in zip(pk_cols, pk_tuple))
            if pk_tuple in existing_pks:
                errors.append(f"Added row {i}: PK ({pk_str}) already exists")
            if pk_tuple in seen_in_batch:
                errors.append(f"Added row {i}: PK ({pk_str}) duplicated in this batch")
            seen_in_batch.add(pk_tuple)

    # ---- EDITED rows ----
    for idx, changes in diff.get("edited_rows", {}).items():
        row_no = idx + 1
        for c in pk_cols:
            if c in changes:
                errors.append(f"Edited row {row_no}: cannot change PK column '{c}'")
        for f in required_cols:
            if f in changes and _missing(changes[f]):
                errors.append(f"Edited row {row_no}: '{f}' cannot be empty")

    return errors, warnings
