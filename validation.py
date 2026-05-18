"""파일별 유효성 검사 (순수 함수, streamlit 비의존).

(errors, warnings) 반환. errors 있으면 저장 차단, warnings 는 비차단(표시만).
행 번호 1-based.
"""
import re

from scoring import parse_expiry

EMP_RE = re.compile(r"^EMP\d{4}$")
EC_RE = re.compile(r"^EMP\d{4}-CRT-\d+$")    # 직원자격증번호 = {직원번호}-CRT-NN
EDU_RE = re.compile(r"^EMP\d{4}-EDU-\d+$")   # 학력정보번호 = {직원번호}-EDU-NN
EDU_LEVELS = {"박사", "석사", "학사", "전문학사", "고졸"}


def _s(v):
    return "" if v is None else str(v)


def _blank(v):
    s = _s(v).strip()
    return s == "" or s.lower() == "nan"


def _date_bad(v):
    s = _s(v).strip()
    return s != "" and s.lower() != "nan" and parse_expiry(s) is None


def _required(df, cols, errors):
    for c in cols:
        if c not in df.columns:
            errors.append(f"필수 컬럼 '{c}' 가 표에 없습니다.")
    return all(c in df.columns for c in cols)


def _dup(df, col, errors):
    seen = {}
    for i, (_, row) in enumerate(df.iterrows(), 1):
        v = _s(row[col]).strip()
        if not v:
            continue
        if v in seen:
            errors.append(f"행 {i} '{col}': '{v}' 가 행 {seen[v]} 와 중복입니다.")
        else:
            seen[v] = i


def _fk_warn(df, col, valid, label, warnings):
    if valid is None or col not in df.columns:
        return
    for i, (_, row) in enumerate(df.iterrows(), 1):
        v = _s(row[col]).strip()
        if v and v not in valid:
            warnings.append(f"행 {i} '{col}': '{v}' 는 {label} 에 없습니다.")


def _level_ok(v):
    s = _s(v).strip()
    return s == "" or (s.isdigit() and 1 <= int(s) <= 5)


# ── 파일별 ──────────────────────────────────────────────────────────

def validate_employees(df):
    e, w = [], []
    if not _required(df, ["직원번호", "이름", "소속", "직책"], e):
        return e, w
    for i, (_, r) in enumerate(df.iterrows(), 1):
        for c in ("이름", "소속", "직책"):
            if _blank(r[c]):
                e.append(f"행 {i} '{c}': 필수값이 비어 있습니다.")
        v = _s(r["직원번호"]).strip()
        if v and not EMP_RE.match(v):
            e.append(f"행 {i} '직원번호': '{v}' 형식 오류(EMP0001, 신규는 공란→자동).")
    _dup(df, "직원번호", e)
    return e, w


def validate_education(df, roster_ids=None):
    e, w = [], []
    if not _required(df, ["직원번호", "학력정보번호"], e):
        return e, w
    for i, (_, r) in enumerate(df.iterrows(), 1):
        if _blank(r["직원번호"]):
            e.append(f"행 {i} '직원번호': 필수값이 비어 있습니다.")
        elif not EMP_RE.match(_s(r["직원번호"]).strip()):
            e.append(f"행 {i} '직원번호': 형식 오류(EMP0001).")
        lv = _s(r.get("학력", "")).strip()
        if lv and lv not in EDU_LEVELS:
            w.append(f"행 {i} '학력': '{lv}' 표준값 아님({'/'.join(sorted(EDU_LEVELS))}).")
    _dup(df, "학력정보번호", e)
    _fk_warn(df, "직원번호", roster_ids, "직원 명부", w)
    return e, w


def validate_empcert(df, roster_ids=None, cert_codes=None):
    e, w = [], []
    if not _required(df, ["직원번호", "직원자격증번호", "자격증코드"], e):
        return e, w
    for i, (_, r) in enumerate(df.iterrows(), 1):
        if _blank(r["직원번호"]):
            e.append(f"행 {i} '직원번호': 필수값이 비어 있습니다.")
        elif not EMP_RE.match(_s(r["직원번호"]).strip()):
            e.append(f"행 {i} '직원번호': 형식 오류(EMP0001).")
        v = _s(r["직원자격증번호"]).strip()
        if v and not EC_RE.match(v):
            e.append(f"행 {i} '직원자격증번호': '{v}' 형식 오류({{직원번호}}-CRT-NN, 신규 공란→자동).")
        if _blank(r["자격증코드"]):
            e.append(f"행 {i} '자격증코드': 필수값이 비어 있습니다.")
        for c in ("취득일", "등록일", "유효기간"):
            if c in df.columns and _date_bad(r[c]):
                e.append(f"행 {i} '{c}': '{_s(r[c]).strip()}' YY.MM.DD 형식 아님.")
    _dup(df, "직원자격증번호", e)
    _fk_warn(df, "직원번호", roster_ids, "직원 명부", w)
    _fk_warn(df, "자격증코드", cert_codes, "자격증 마스터", w)
    return e, w


def validate_cert_master(df):
    e, w = [], []
    if not _required(df, ["자격증코드", "자격증명"], e):
        return e, w
    for i, (_, r) in enumerate(df.iterrows(), 1):
        if _blank(r["자격증명"]):
            e.append(f"행 {i} '자격증명': 필수값이 비어 있습니다.")
        if "영향력" in df.columns and not _level_ok(r["영향력"]):
            e.append(f"행 {i} '영향력': '{_s(r['영향력']).strip()}' 1~5 또는 공란이어야 함.")
    _dup(df, "자격증코드", e)
    return e, w


def validate_workcode_master(df):
    e, w = [], []
    if not _required(df, ["업무분류코드", "대분류", "중분류", "업무구분"], e):
        return e, w
    for i, (_, r) in enumerate(df.iterrows(), 1):
        for c in ("대분류", "중분류", "업무구분", "업무분류코드"):
            if _blank(r[c]):
                e.append(f"행 {i} '{c}': 필수값이 비어 있습니다.")
    _dup(df, "업무분류코드", e)
    return e, w


def validate_wc_cert_map(df, wcm_codes=None, cert_codes=None):
    e, w = [], []
    if not _required(df, ["업무분류코드", "자격증코드", "업무관련영향력"], e):
        return e, w
    seen = {}
    for i, (_, r) in enumerate(df.iterrows(), 1):
        wc = _s(r["업무분류코드"]).strip()
        cc = _s(r["자격증코드"]).strip()
        if _blank(wc):
            e.append(f"행 {i} '업무분류코드': 필수값이 비어 있습니다.")
        if _blank(cc):
            e.append(f"행 {i} '자격증코드': 필수값이 비어 있습니다.")
        if not _level_ok(r["업무관련영향력"]) or _blank(r["업무관련영향력"]):
            e.append(f"행 {i} '업무관련영향력': 1~5 정수여야 합니다.")
        if wc and cc:
            k = (wc, cc)
            if k in seen:
                e.append(f"행 {i}: ({wc},{cc}) 가 행 {seen[k]} 와 중복입니다.")
            else:
                seen[k] = i
    _fk_warn(df, "업무분류코드", wcm_codes, "업무코드 마스터", w)
    _fk_warn(df, "자격증코드", cert_codes, "자격증 마스터", w)
    return e, w
