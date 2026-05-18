"""서비스: 한국 자격증 DB 편집 (자격증_마스터.csv).

코드({대분류}-NNNN)는 읽기전용 — 신규/공란 행은 저장 시 해당 대분류 그룹의
다음 일련번호로 자동 부여. 자격증↔업무 매핑은 별도(업무코드_자격증_매핑.csv).
"""
import re

import streamlit as st

from data_loader import CERTM_CSV, load_cert_master
from services._common import run_editor
from validation import validate_cert_master

_CODE = re.compile(r"^(.+)-(\d{3,})$")


def _assign_codes(df):
    df = df.copy()
    if "자격증코드" not in df.columns:
        df["자격증코드"] = ""
    mx = {}
    for v in df["자격증코드"].astype(str):
        m = _CODE.match(v.strip())
        if m:
            mx[m.group(1)] = max(mx.get(m.group(1), 0), int(m.group(2)))
    out = []
    for _, r in df.iterrows():
        cur = str(r["자격증코드"]).strip()
        if _CODE.match(cur):
            out.append(cur)
            continue
        if str(r.get("자격증명", "")).strip() == "":
            out.append("")
            continue
        p = str(r.get("대분류", "")).strip() or "미분류"
        mx[p] = mx.get(p, 0) + 1
        out.append(f"{p}-{mx[p]:04d}")
    df["자격증코드"] = out
    return df


def render():
    st.subheader("한국 자격증 DB")
    st.caption("자격증 본정보. 코드는 대분류별 자동 부여(읽기전용).")
    df = load_cert_master()
    cols = list(df.columns)
    대opts = sorted({v for v in df["대분류"].astype(str).str.strip() if v})
    run_editor(
        sid="certm", title="한국 자격증 DB", caption=None,
        df=df, target=CERTM_CSV, cols=cols,
        validator=validate_cert_master, clear_fn=load_cert_master.clear,
        disabled_cols={"자격증코드"},
        derive_fn=_assign_codes,
        select_cols={"대분류": 대opts, "영향력": ["1", "2", "3", "4", "5"]},
        col_widths={"자격증코드": "medium", "자격증명": "medium", "대분류": "small",
                    "중분류": "small", "영향력": "small",
                    "원가산정검증활용": "large", "자격증내용": "large",
                    "수행가능업무": "large", "키워드": "large"},
    )
