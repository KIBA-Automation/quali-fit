"""데이터 로딩 (정규화 스키마 v5).

파일:
- 직원.csv               직원번호,이름,소속,직책
- 직원_학력.csv          직원번호,학력정보번호(EDU-분야-NNN),학력,학위,학교명,학부(과),전공,비고
- 직원_자격증.csv        직원번호,직원자격증번호(EC),자격증코드,자격증,취득일,등록일,유효기간
- 자격증_마스터.csv      코드,자격증명,대분류,중분류,…,영향력,…
- 업무코드_마스터.csv    업무분류코드,대분류,중분류,소분류,업무구분,…
- 업무코드_자격증_매핑.csv  업무분류코드,자격증코드,업무관련영향력,추천사유,매핑근거
자격증↔업무 매칭은 업무코드_자격증_매핑.csv 단일 소스. (이전 도메인/8분류/xlsx 개념 폐기)
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "Data"
EMP_CSV = DATA_DIR / "직원.csv"
EDU_CSV = DATA_DIR / "직원_학력.csv"
EMPCERT_CSV = DATA_DIR / "직원_자격증.csv"
CERTM_CSV = DATA_DIR / "자격증_마스터.csv"
WCM_CSV = DATA_DIR / "업무코드_마스터.csv"
MAP_CSV = DATA_DIR / "업무코드_자격증_매핑.csv"

EMP_ID = "직원번호"
EMP_COLS = ["직원번호", "이름", "소속", "직책"]
EDU_COLS = ["직원번호", "학력정보번호", "학력", "학위", "학교명",
            "학부(과)", "전공", "비고"]
EMPCERT_COLS = ["직원번호", "직원자격증번호", "자격증코드", "자격증",
                "취득일", "등록일", "유효기간"]
WCM_COLS = ["업무분류코드", "대분류", "중분류", "소분류", "업무구분",
            "분류기준", "관리부서", "책임자", "관련지침", "관련법령"]
MAP_COLS = ["업무분류코드", "자격증코드", "업무관련영향력", "영향력 근거", "매핑근거"]

# 학력 전공/학부 → 분야 (학력정보번호 EDU-{분야}-NNN 휴리스틱)
FIELD_RULES = [
    ("의료", ["의학", "간호", "보건", "약학", "치의", "한의", "의료", "수의"]),
    ("법", ["법학", "법무", "법률", "법"]),
    ("교육", ["교육", "평생교육"]),
    ("예술", ["미술", "음악", "디자인", "예술", "체육", "무용", "연극", "영상", "공예"]),
    ("공학", ["공학", "건축", "토목", "전기", "전자", "기계", "컴퓨터", "소프트", "정보",
              "산업", "화학공", "도시", "건설", "에너지", "재료", "항공", "조선", "IT"]),
    ("경영", ["경영", "회계", "무역", "경제", "금융", "세무", "마케팅", "MBA", "물류",
              "부동산", "보험"]),
    ("사회", ["사회", "행정", "정책", "복지", "심리", "정치", "언론", "신문", "방송",
              "상담", "인류", "지리"]),
    ("자연", ["이학", "수학", "물리", "화학", "생물", "통계", "천문", "지질", "자연",
              "농학", "식품", "원예", "산림"]),
]


def field_of(major: str, faculty: str = "") -> str:
    txt = f"{major} {faculty}"
    for name, kws in FIELD_RULES:
        if any(k in txt for k in kws):
            return name
    return "기타"


def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    df.columns = [str(c).strip() for c in df.columns]
    drop = [c for c in df.columns
            if (c == "" or c.startswith("Unnamed")) and not df[c].str.strip().any()]
    return df.drop(columns=drop)


@st.cache_data
def load_employees():
    """(roster, edu, empcert)."""
    return (_read_csv(EMP_CSV), _read_csv(EDU_CSV), _read_csv(EMPCERT_CSV))


@st.cache_data
def load_cert_master() -> pd.DataFrame:
    return _read_csv(CERTM_CSV)


@st.cache_data
def load_workcode_master() -> pd.DataFrame:
    return _read_csv(WCM_CSV)


@st.cache_data
def load_wc_cert_map() -> pd.DataFrame:
    return _read_csv(MAP_CSV)


@st.cache_data
def build_certs_by_key(empcert_df: pd.DataFrame) -> dict:
    """{직원번호: [자격증 행 dict, ...]}"""
    out: dict = {}
    for _, row in empcert_df.iterrows():
        out.setdefault(str(row.get(EMP_ID, "")).strip(), []).append(row.to_dict())
    return out
