"""편집 서비스 공통 흐름: data_editor → 검증 → 백업·원자적 저장 → 캐시 무효화.

행번호는 엑셀식 인덱스 거터로 표시(저장 안 됨). disabled_cols 는 읽기전용(연동) 컬럼.
derive_fn 은 연동 컬럼을 원천(직원/자격증마스터) 값으로 다시 채우는 함수 — 표시 직전과
저장 직전 모두 적용한다.
"""
import streamlit as st

from persistence import backup_then_atomic_write, file_mtime, prune_backups


def run_editor(*, sid, title, caption, df, target, cols, validator,
               clear_fn, validator_kwargs=None, disabled_cols=None,
               derive_fn=None, display_cols=None, col_widths=None,
               select_cols=None, sort_by=None):
    """편집표 1개 렌더 + 저장 처리. 저장 성공 시 st.rerun() (호출 복귀 안 함).

    cols          : CSV 에 저장되는 컬럼(순서). 파생 표시 컬럼은 제외.
    display_cols  : 에디터 표시 순서(파생 읽기전용 포함 상위집합). 기본 = cols.
    col_widths    : {컬럼: 'small'|'medium'|'large'} 표시 폭.
    select_cols   : {컬럼: [선택지]} → 드롭다운(SelectboxColumn)으로 표시(오타 방지).
    sort_by       : 표시 정렬 기준 컬럼(파생 후 적용).
    """
    st.markdown(f"#### {title}")
    if caption:
        st.caption(caption)
    st.caption(
        "회색 칸 = 자동 연동(읽기전용) · ▾ 표시 칸 = 목록에서 선택 · 그 외 = 직접 입력. "
        "동시 편집 보호 없음(마지막 저장이 덮어씀), 저장 시 자동 백업."
    )

    disabled_cols = set(disabled_cols or [])
    display_cols = list(display_cols or cols)
    col_widths = col_widths or {}
    select_cols = select_cols or {}
    df = df.reset_index(drop=True)
    if derive_fn is not None:
        df = derive_fn(df)

    ver = st.session_state.get(f"ver_{sid}", 0)
    mkey = f"mtime_{sid}_{ver}"
    if mkey not in st.session_state:
        st.session_state[mkey] = file_mtime(target)

    display = df.reindex(columns=display_cols).copy()
    if sort_by and sort_by in display.columns:
        display = display.sort_values(sort_by, kind="stable").reset_index(drop=True)
    display.index = range(1, len(display) + 1)  # 엑셀식 행번호 거터(저장 안 됨)

    colcfg = {}
    for c in display_cols:
        if c in select_cols:
            colcfg[c] = st.column_config.SelectboxColumn(
                c, options=select_cols[c], disabled=(c in disabled_cols),
                width=col_widths.get(c))
        else:
            colcfg[c] = st.column_config.TextColumn(
                c, disabled=(c in disabled_cols), width=col_widths.get(c))

    edited = st.data_editor(
        display, num_rows="dynamic", width="stretch", hide_index=False,
        key=f"ed_{sid}_{ver}", column_config=colcfg,
    )

    if not st.button("검증 후 저장", key=f"save_{sid}_{ver}", type="primary"):
        return

    out = edited.reset_index(drop=True)
    if derive_fn is not None:
        out = derive_fn(out)
    out = out.reindex(columns=cols).fillna("").astype(str)
    errors, warnings = validator(out, **(validator_kwargs or {}))

    if file_mtime(target) != st.session_state[mkey]:
        warnings = warnings + [
            "이 파일이 불러온 이후 외부에서 변경되었습니다. 저장하면 그 변경을 덮어씁니다."
        ]

    if errors:
        st.error(f"유효성 오류 {len(errors)}건 — 저장이 차단되었습니다.")
        for m in errors[:50]:
            st.write("• " + m)
        if len(errors) > 50:
            st.write(f"… 외 {len(errors) - 50}건")
        return

    if warnings:
        st.warning(f"경고 {len(warnings)}건 (저장은 진행됨):")
        for m in warnings[:50]:
            st.write("• " + m)

    backup = backup_then_atomic_write(out, target, cols=cols)
    prune_backups(target.stem)
    clear_fn()
    st.session_state[f"ver_{sid}"] = ver + 1
    st.session_state.pop(mkey, None)
    msg = f"저장 완료 ({len(out):,} 행)."
    if backup:
        msg += f" 백업: `Data/backups/{backup.name}`"
    st.success(msg)
    st.rerun()
