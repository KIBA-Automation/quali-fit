"""서비스: 업무코드 마스터 편집 + 분류 체계 시각화.

업무분류코드(C-제조-제작-산정 / P-타당성-산정)는 대분류·중분류·소분류·업무구분에서
자동 생성(읽기전용). 평탄화 표를 위에, 시각화를 아래에 표시.
"""
import streamlit as st

from data_loader import (MAP_COLS, MAP_CSV, WCM_COLS, WCM_CSV,
                         load_cert_master, load_wc_cert_map,
                         load_workcode_master)
from services._common import run_editor
from validation import validate_wc_cert_map, validate_workcode_master

SUBS = ["업무코드", "자격증 매핑"]


def _subtab():
    q = st.query_params.get("wtab")
    d = q if q in SUBS else SUBS[0]
    tab = st.segmented_control("표 선택", SUBS, key="wtab", default=d,
                               label_visibility="collapsed")
    if tab is None:
        tab = st.session_state.get("wtab_last", d)
    st.session_state["wtab_last"] = tab
    if st.query_params.get("wtab") != tab:
        st.query_params["wtab"] = tab
    return tab


def _abbr(dae: str) -> str:
    return "C" if "원가" in dae else ("P" if "연구용역" in dae else dae[:1])


def _assign_codes(df):
    df = df.copy()
    out = []
    for _, r in df.iterrows():
        if str(r.get("대분류", "")).strip() == "":
            out.append(str(r.get("업무분류코드", "")).strip())
            continue
        parts = [_abbr(str(r["대분류"]).strip()),
                 str(r.get("중분류", "")).strip(),
                 str(r.get("소분류", "")).strip(),
                 str(r.get("업무구분", "")).strip()]
        out.append("-".join(p for p in parts if p))
    df["업무분류코드"] = out
    return df


def _link_certname(df, certname):
    df = df.copy()
    df["자격증명"] = df["자격증코드"].astype(str).str.strip().map(
        lambda c: certname.get(c, ""))
    return df


def render():
    st.subheader("한국경영분석연구원의 업무코드")
    df = load_workcode_master()
    tab = _subtab()

    if tab == "업무코드":
        st.caption("업무분류코드는 대분류·중분류·소분류·업무구분에서 자동 생성(읽기전용).")
        대opts = sorted({v for v in df["대분류"].astype(str).str.strip() if v})
        중opts = sorted({v for v in df["중분류"].astype(str).str.strip() if v})
        run_editor(
            sid="wcm", title="업무코드", caption=None,
            df=df, target=WCM_CSV, cols=WCM_COLS,
            validator=validate_workcode_master,
            clear_fn=load_workcode_master.clear,
            disabled_cols={"업무분류코드"},
            derive_fn=_assign_codes,
            select_cols={"대분류": 대opts, "중분류": 중opts,
                         "업무구분": ["산정", "검증"]},
            col_widths={"업무분류코드": "medium", "대분류": "small",
                        "중분류": "small", "소분류": "small", "업무구분": "small"},
        )
        st.divider()
        st.markdown("### 분류 체계 (파트별)")
        view = ["중분류", "소분류", "업무구분", "업무분류코드"]
        for part, label in [("원가(C)", "원가 파트"),
                            ("연구용역(P)", "연구용역 파트")]:
            sub = df[df["대분류"] == part]
            if sub.empty:
                continue
            st.markdown(f"**{label}** · {len(sub)}건")
            st.dataframe(sub[view].reset_index(drop=True),
                         width="stretch", hide_index=True)

    else:  # 자격증 매핑
        st.caption("자격증↔업무 매칭의 단일 소스. 추천 점수는 '업무관련영향력'으로 계산됩니다.")
        mp = load_wc_cert_map()
        cm = load_cert_master()
        wc_codes = sorted(df["업무분류코드"].astype(str).str.strip().unique())
        cert_codes = sorted(cm["자격증코드"].astype(str).str.strip().unique())
        certname = {str(r["자격증코드"]).strip(): str(r["자격증명"])
                    for _, r in cm.iterrows()}
        m1, m2, m3 = st.columns(3)
        m1.metric("매핑 행", f"{len(mp):,}")
        m2.metric("업무코드 커버리지",
                  f"{mp['업무분류코드'].nunique()} / {len(wc_codes)}")
        m3.metric("매핑된 자격증",
                  f"{mp['자격증코드'].nunique()} / {len(cert_codes)}")
        run_editor(
            sid="map", title="업무코드_자격증_매핑", caption=None,
            df=mp, target=MAP_CSV, cols=MAP_COLS,
            display_cols=["업무분류코드", "자격증코드", "자격증명",
                          "업무관련영향력", "영향력 근거", "매핑근거"],
            validator=validate_wc_cert_map, clear_fn=load_wc_cert_map.clear,
            validator_kwargs={"wcm_codes": set(wc_codes),
                              "cert_codes": set(cert_codes)},
            disabled_cols={"자격증명"},
            derive_fn=lambda d: _link_certname(d, certname),
            select_cols={"업무분류코드": wc_codes, "자격증코드": cert_codes,
                         "업무관련영향력": ["1", "2", "3", "4", "5"]},
            col_widths={"업무분류코드": "medium", "자격증코드": "medium",
                        "자격증명": "medium", "업무관련영향력": "small",
                        "영향력 근거": "large", "매핑근거": "medium"},
        )
