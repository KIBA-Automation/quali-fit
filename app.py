import streamlit as st
import db
import validation

st.set_page_config(page_title="quali-fit", layout="wide")

url_choice = st.query_params.get("svc", db.KNOWN_TABLES[0])
if url_choice not in db.KNOWN_TABLES:
    url_choice = db.KNOWN_TABLES[0]

choice = st.segmented_control(
    "Service",
    db.KNOWN_TABLES,
    default=url_choice,
    label_visibility="collapsed",
)

if choice and choice != st.query_params.get("svc"):
    st.query_params["svc"] = choice

if choice:
    st.subheader(choice)
    df = db.fetch_all(choice)
    editor_key = f"{choice}_editor"
    meta = db.table_meta(choice)
    fk_opts = db.fk_options(choice)
    column_config = {
        col: st.column_config.SelectboxColumn(col, options=opts, required=True)
        for col, opts in fk_opts.items()
    }
    # Derived columns (from LEFT JOINs in fetch_all) — read-only display.
    real_cols = set(meta["all_cols"])
    for c in df.columns:
        if c not in real_cols:
            column_config[c] = st.column_config.TextColumn(c, disabled=True)
    # Auto-generated ID columns — show but lock the cell.
    for c in meta["auto_id_cols"]:
        column_config[c] = st.column_config.TextColumn(c, disabled=True, help="auto-generated on save")

    st.data_editor(
        df,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key=editor_key,
        column_config=column_config,
    )

    if st.button("Save"):
        diff = st.session_state[editor_key]
        meta = db.table_meta(choice)
        errors, warnings = validation.validate_diff(meta, df, diff)
        for msg in warnings:
            st.warning(msg)
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            try:
                db.save_diff(choice, df, diff)
                st.toast("Saved.", icon="✅")
                del st.session_state[editor_key]
                st.rerun()
            except Exception as e:
                st.error(f"Error saving changes: {e}", icon="❌")
