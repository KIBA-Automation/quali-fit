"""서비스: 직원·자격증 데이터 편집 (정규화 스키마 v5).

- 직원.csv 가 직원번호 원천. 학력/자격증은 직원번호로만 저장, 인적사항은 연동(읽기전용).
- 직원_자격증: 자격증코드(드롭다운)→자격증명은 자격증_마스터에서 연동(읽기전용).
- 서브탭은 URL 쿼리파라미터로 보존(새로고침 유지).
"""
import re

import streamlit as st

from data_loader import (EDU_COLS, EDU_CSV, EMP_COLS, EMP_CSV, EMPCERT_COLS,
                         EMPCERT_CSV, load_cert_master, load_employees)
from services._common import run_editor
from validation import (validate_education, validate_empcert,
                        validate_employees)

EDU_LEVELS = ["박사", "석사", "학사", "전문학사", "고졸"]
SUBS = ["직원", "직원_학력", "직원_자격증"]


def _assign_seq(df, col, prefix, width):
    df = df.copy()
    if col not in df.columns:
        df[col] = ""
    mx = 0
    for v in df[col].astype(str):
        m = re.match(rf"^{prefix}(\d+)$", v.strip())
        if m:
            mx = max(mx, int(m.group(1)))
    nxt = mx + 1
    out = []
    for v in df[col].astype(str):
        s = v.strip()
        if re.match(rf"^{prefix}\d+$", s):
            out.append(s)
        else:
            out.append(f"{prefix}{nxt:0{width}d}")
            nxt += 1
    df[col] = out
    return df


def _assign_child_ids(df, col, tag):
    """{직원번호}-{tag}-NN (직원별 일련). 기존 유효값 유지, 공란/이상만 새로 부여."""
    df = df.copy()
    if col not in df.columns:
        df[col] = ""
    pat = re.compile(rf"^(EMP\d{{4}})-{tag}-(\d+)$")
    emps = df["직원번호"].astype(str).str.strip()
    seq = {}
    for v in df[col].astype(str):
        m = pat.match(v.strip())
        if m:
            seq[m.group(1)] = max(seq.get(m.group(1), 0), int(m.group(2)))
    out = []
    for emp, v in zip(emps, df[col].astype(str)):
        s = v.strip()
        if pat.match(s):
            out.append(s)
        elif not emp:
            out.append("")
        else:
            seq[emp] = seq.get(emp, 0) + 1
            out.append(f"{emp}-{tag}-{seq[emp]:02d}")
    df[col] = out
    return df


def _link_roster(df, idmap):
    df = df.copy()
    ids = df["직원번호"].astype(str).str.strip()
    df["이름"] = ids.map(lambda x: idmap.get(x, ("", "", ""))[0])
    df["소속"] = ids.map(lambda x: idmap.get(x, ("", "", ""))[1])
    df["직책"] = ids.map(lambda x: idmap.get(x, ("", "", ""))[2])
    return df


def _link_cert_name(df, codemap):
    df = df.copy()
    df["자격증"] = df["자격증코드"].astype(str).str.strip().map(
        lambda c: codemap.get(c, ""))
    return df


def _subtab():
    q = st.query_params.get("etab")
    d = q if q in SUBS else SUBS[0]
    tab = st.segmented_control("표 선택", SUBS, key="etab", default=d,
                               label_visibility="collapsed")
    if tab is None:
        tab = st.session_state.get("etab_last", d)
    st.session_state["etab_last"] = tab
    if st.query_params.get("etab") != tab:
        st.query_params["etab"] = tab
    return tab


def render():
    st.subheader("직원·자격증 데이터")
    st.caption("표를 직접 편집하고 '검증 후 저장'을 누르세요. 행 추가/삭제 가능.")

    roster_df, edu_df, ec_df = load_employees()
    cm = load_cert_master()
    idmap = {str(r["직원번호"]).strip():
             (str(r["이름"]), str(r["소속"]), str(r["직책"]))
             for _, r in roster_df.iterrows()}
    roster_ids = sorted(idmap)
    codemap = {str(r["자격증코드"]).strip(): str(r["자격증명"])
               for _, r in cm.iterrows()}
    cert_codes = sorted(codemap)
    소속opts = sorted({v for v in roster_df["소속"].astype(str).str.strip() if v})
    직책opts = sorted({v for v in roster_df["직책"].astype(str).str.strip() if v})

    tab = _subtab()

    if tab == "직원":
        run_editor(
            sid="emp", title="직원 명부",
            caption="신규 행은 직원번호 공란 → 저장 시 자동 부여. 소속·직책은 드롭다운.",
            df=roster_df, target=EMP_CSV, cols=EMP_COLS,
            validator=validate_employees, clear_fn=load_employees.clear,
            disabled_cols={"직원번호"},
            derive_fn=lambda d: _assign_seq(d, "직원번호", "EMP", 4),
            select_cols={"소속": 소속opts, "직책": 직책opts},
            col_widths={"직원번호": "small", "이름": "small",
                        "소속": "medium", "직책": "small"},
        )

    elif tab == "직원_학력":
        run_editor(
            sid="edu", title="직원 학력",
            caption="직원번호 선택 시 이름·소속·직책 자동 연동(읽기전용). 직원번호순.",
            df=edu_df, target=EDU_CSV, cols=EDU_COLS,
            display_cols=["직원번호", "이름", "소속", "직책", "학력정보번호",
                          "학력", "학위", "학교명", "학부(과)", "전공", "비고"],
            validator=validate_education, clear_fn=load_employees.clear,
            validator_kwargs={"roster_ids": set(roster_ids)},
            disabled_cols={"이름", "소속", "직책", "학력정보번호"},
            derive_fn=lambda d: _assign_child_ids(
                _link_roster(d, idmap), "학력정보번호", "EDU"),
            select_cols={"직원번호": roster_ids, "학력": EDU_LEVELS},
            sort_by="직원번호",
            col_widths={"직원번호": "small", "이름": "small", "소속": "small",
                        "직책": "small", "학력정보번호": "medium",
                        "학력": "small", "학위": "medium", "학교명": "large",
                        "학부(과)": "medium", "전공": "medium", "비고": "small"},
        )

    else:  # 직원_자격증
        run_editor(
            sid="cert", title="직원 자격증",
            caption="직원번호·자격증코드는 드롭다운. 자격증명은 한국 자격증 DB에서 연동. 직원번호순.",
            df=ec_df, target=EMPCERT_CSV, cols=EMPCERT_COLS,
            display_cols=["직원번호", "이름", "소속", "직책", "직원자격증번호",
                          "자격증코드", "자격증", "취득일", "등록일", "유효기간"],
            validator=validate_empcert, clear_fn=load_employees.clear,
            validator_kwargs={"roster_ids": set(roster_ids),
                              "cert_codes": set(cert_codes)},
            disabled_cols={"이름", "소속", "직책", "직원자격증번호", "자격증"},
            derive_fn=lambda d: _assign_child_ids(
                _link_cert_name(_link_roster(d, idmap), codemap),
                "직원자격증번호", "CRT"),
            select_cols={"직원번호": roster_ids, "자격증코드": cert_codes},
            sort_by="직원번호",
            col_widths={"직원번호": "small", "이름": "small", "소속": "small",
                        "직책": "small", "직원자격증번호": "small",
                        "자격증코드": "medium", "자격증": "large",
                        "취득일": "small", "등록일": "small", "유효기간": "small"},
        )
