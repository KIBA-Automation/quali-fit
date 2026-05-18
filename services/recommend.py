"""서비스: 원가용역 직원 추천 (v5 — 매핑 테이블 기반)."""
from datetime import date

import pandas as pd
import streamlit as st

from data_loader import (build_certs_by_key, load_employees,
                         load_wc_cert_map, load_workcode_master)
from scoring import MAX_SCORE, WEIGHTS, rank_employees

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
_LV = {5: "#1e7a34", 4: "#2e7d32", 3: "#1f5fb0", 2: "#5f6368", 1: "#777"}


def _lv_css(v):
    try:
        return f"background-color:{_LV.get(int(v),'')};color:#fff;font-weight:600"
    except (ValueError, TypeError):
        return ""


def _exp_css(v):
    return "background-color:#b00020;color:#fff;font-weight:600" if str(v) == "만료" else ""


def _detail(emp, edu_df):
    st.markdown(
        f"**총점 {emp['total']}점** (만점 {MAX_SCORE})\n"
        f"- 자격증 1건 기여점수 = 업무관련영향력(1~5) × {WEIGHTS['W_LEVEL']}점 "
        f"(유효기간 지난 자격증은 ×{WEIGHTS['EXPIRED_FACTOR']})\n"
        f"- 기본점수 = 보유 자격증 중 가장 높은 기여점수 = **{emp['base']}**\n"
        f"- 다양성 보너스 = (관련 {emp['관련자격증수']}건 − 1) × {WEIGHTS['W_BREADTH']}점, "
        f"최대 {WEIGHTS['BREADTH_CAP']}점 = **{emp['breadth']}**\n"
        f"- 총점 = 기본점수 + 다양성 보너스 = **{emp['total']}**"
    )
    if emp["lines"]:
        b = pd.DataFrame(emp["lines"]).reset_index(drop=True)
        b.index = range(1, len(b) + 1)
        sty = (b.style.map(_lv_css, subset=["영향력"])
               .map(_exp_css, subset=["만료"]))
        st.dataframe(sty, width="stretch")
    else:
        st.write("이 업무코드에 매핑된 보유 자격증이 없습니다.")
    e = edu_df[edu_df["직원번호"].astype(str).str.strip() == str(emp["직원번호"]).strip()]
    if not e.empty:
        e = e.reset_index(drop=True)
        e.index = range(1, len(e) + 1)
        st.caption("학력 (참고용 · 점수 미반영)")
        st.dataframe(e, width="stretch")


def render():
    today = date.today()
    roster_df, edu_df, ec_df = load_employees()
    wcm = load_workcode_master()
    mp = load_wc_cert_map()
    certs_by_key = build_certs_by_key(ec_df)
    roster = roster_df[["직원번호", "이름", "소속", "직책"]].to_dict("records")

    st.subheader("원가용역 직원 추천")
    st.caption("업무 코드를 선택하면 적합한 직원을 매칭 점수 순으로 보여줍니다.")

    st.markdown("##### 1. 업무 코드 선택")
    c1, c2, c3 = st.columns(3)
    with c1:
        dae = st.selectbox("대분류", list(wcm["대분류"].unique()))
    s1 = wcm[wcm["대분류"] == dae]
    with c2:  # 중분류·소분류는 업무코드 순서대로 정렬
        mid = st.selectbox("중분류", list(dict.fromkeys(s1["중분류"])))
    s2 = s1[s1["중분류"] == mid]
    with c3:
        opt = st.selectbox(
            "소분류·업무구분",
            [f"{r['업무분류코드']}  ·  {r['소분류']} {r['업무구분']}".strip()
             for _, r in s2.iterrows()])
    code = opt.split("  ·  ")[0]
    sel = s2[s2["업무분류코드"] == code].iloc[0]

    st.caption(f"관리부서 / 책임자: {sel['관리부서']} / {sel['책임자']}")

    qrows = mp[mp["업무분류코드"] == code]
    qualmap = {str(r["자격증코드"]).strip(): {
        "업무관련영향력": r["업무관련영향력"], "영향력 근거": r.get("영향력 근거", ""),
        "매핑근거": r.get("매핑근거", "")} for _, r in qrows.iterrows()}
    if not qualmap:
        st.warning("이 업무코드에 매핑된 자격증이 없습니다 (업무코드↔자격증 매핑 확인).")
        return

    ranked = rank_employees(roster, certs_by_key, qualmap, today)
    show_zero = st.toggle("점수 0 직원도 표시", value=False)
    rows = [r for r in ranked if show_zero or r["total"] > 0]
    if not rows:
        st.info("매칭되는 직원이 없습니다.")
        return

    st.markdown("##### 2. 점수 산정 방식")
    st.markdown(
        f"- **자격증 1건 기여점수** = 그 자격증의 *업무관련영향력*(1~5) × "
        f"{WEIGHTS['W_LEVEL']}점. 유효기간이 지난 자격증은 ×{WEIGHTS['EXPIRED_FACTOR']}.\n"
        f"- **기본점수** = 그 직원이 보유한 관련 자격증 중 *가장 높은* 기여점수.\n"
        f"- **관련 자격증 수** = 선택한 업무코드에 매핑된 자격증 중 그 직원이 보유한 개수.\n"
        f"- **다양성 보너스** = (관련 자격증 수 − 1) × {WEIGHTS['W_BREADTH']}점, "
        f"최대 {WEIGHTS['BREADTH_CAP']}점.\n"
        f"- **총점** = 기본점수 + 다양성 보너스  (만점 {MAX_SCORE})"
    )

    st.markdown("##### 3. 추천 순위")
    tbl = pd.DataFrame([{
        "순위": f"{MEDALS.get(i + 1, '')} {i + 1}".strip(),
        "직원번호": r["직원번호"], "이름": r["이름"], "소속": r["소속"],
        "직책": r["직책"], "총점": r["total"], "기본점수": r["base"],
        "다양성보너스": r["breadth"], "관련자격증수": r["관련자격증수"],
    } for i, r in enumerate(rows)])
    tbl.index = range(1, len(tbl) + 1)
    st.dataframe(tbl, width="stretch", column_config={
        "총점": st.column_config.ProgressColumn(
            "총점", min_value=0, max_value=float(MAX_SCORE), format="%.1f")})

    st.markdown("##### 4. 상위 5명 점수 근거")
    for i, emp in enumerate(rows[:5]):
        with st.container(border=True):
            st.markdown(f"### {MEDALS.get(i + 1, f'{i + 1}.')} {emp['이름']} "
                        f"· {emp['소속']} · {emp['직책']} — **{emp['total']}점**")
            _detail(emp, edu_df)

    if len(rows) > 5:
        with st.expander(f"그 외 직원 상세 ({len(rows) - 5}명)"):
            labels = [f"{r['이름']} ({r['소속']}/{r['직책']}) — {r['total']}점"
                      for r in rows[5:]]
            pick = st.selectbox("직원 선택", labels, key="rec_more")
            _detail(rows[5:][labels.index(pick)], edu_df)
