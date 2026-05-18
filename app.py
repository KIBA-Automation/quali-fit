"""사내 서비스 플랫폼 — 상단 내비 + 서비스 디스패치 (v2)."""
import streamlit as st

from services import SERVICES

st.set_page_config(page_title="원가용역 사내 서비스", layout="wide")

LABELS = [s["label"] for s in SERVICES]

# 새로고침(새 세션)에도 현재 서비스 유지 → URL 쿼리파라미터에 저장/복원
_q = st.query_params.get("svc")
_default = _q if _q in LABELS else LABELS[0]
# segmented_control 은 활성 칩 재클릭 시 None(토글 해제) → 마지막 선택으로 폴백
sel = st.segmented_control("서비스", LABELS, key="nav", default=_default)
if sel is None:
    sel = st.session_state.get("nav_last", _default)
st.session_state["nav_last"] = sel
if st.query_params.get("svc") != sel:
    st.query_params["svc"] = sel

st.divider()
next(s for s in SERVICES if s["label"] == sel)["render"]()
