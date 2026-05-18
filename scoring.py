"""매칭 점수 (v5 — 업무코드↔자격증 매핑 테이블 기반). 가중치는 WEIGHTS 에서 튜닝.

선택한 업무분류코드 → 업무코드_자격증_매핑.csv 에서 자격할 자격증코드 + 업무관련영향력
(1~5)·추천사유 획득 → 직원이 보유한 자격증(직원_자격증) 중 해당 코드의 기여를 합산.
"""
from datetime import date

WEIGHTS = {
    "W_LEVEL": 6,        # 업무관련영향력 1점당 점수 (레벨5 = 30)
    "W_BREADTH": 3,      # 관련 자격증 추가 1건당 다양성 보너스
    "BREADTH_CAP": 15,   # 다양성 보너스 상한
    "EXPIRED_FACTOR": 0.5,  # 만료 자격증 기여 배수
}
MAX_SCORE = WEIGHTS["W_LEVEL"] * 5 + WEIGHTS["BREADTH_CAP"]  # 45


def parse_expiry(s):
    """'YY.MM.DD' → date. 공란/이상값이면 None."""
    s = "" if s is None else str(s).strip()
    if not s or s.lower() == "nan":
        return None
    parts = s.split(".")
    if len(parts) != 3:
        return None
    try:
        y, m, d = (int(p) for p in parts)
        return date(2000 + y, m, d)
    except ValueError:
        return None


def score_employee(cert_rows, qualmap: dict, today: date) -> dict:
    """cert_rows: 직원 보유 자격증 행(dict) 목록. qualmap: {자격증코드: {업무관련영향력,
    추천사유, 매핑근거}} (선택 업무코드 기준).

    반환: total, base, breadth, lines[](기여 자격증별 설명).
    """
    lines = []
    for r in cert_rows:
        code = str(r.get("자격증코드", "")).strip()
        q = qualmap.get(code)
        if not q:
            continue
        try:
            lvl = int(str(q.get("업무관련영향력", "0")).strip() or 0)
        except ValueError:
            lvl = 0
        if lvl <= 0:
            continue
        base = WEIGHTS["W_LEVEL"] * lvl
        exp = parse_expiry(r.get("유효기간"))
        expired = exp is not None and exp < today
        pts = round(base * (WEIGHTS["EXPIRED_FACTOR"] if expired else 1), 1)
        lines.append({
            "자격증": r.get("자격증", ""),
            "자격증코드": code,
            "영향력": lvl,
            "영향력 근거": q.get("영향력 근거", ""),
            "만료": "만료" if expired else ("유효" if exp else "영구/미기재"),
            "기여점수": pts,
        })
    if not lines:
        return {"total": 0.0, "base": 0.0, "breadth": 0.0, "lines": []}
    base = max(l["기여점수"] for l in lines)
    breadth = float(min((len(lines) - 1) * WEIGHTS["W_BREADTH"],
                        WEIGHTS["BREADTH_CAP"]))
    lines.sort(key=lambda l: l["기여점수"], reverse=True)
    return {"total": round(base + breadth, 1), "base": round(base, 1),
            "breadth": breadth, "lines": lines}


def rank_employees(roster, certs_by_key, qualmap, today):
    """roster: list[dict]({직원번호,이름,소속,직책}). certs_by_key: {직원번호:[row]}."""
    out = []
    for emp in roster:
        rows = certs_by_key.get(str(emp.get("직원번호", "")).strip(), [])
        sc = score_employee(rows, qualmap, today)
        out.append({**emp, **sc, "관련자격증수": len(sc["lines"])})
    out.sort(key=lambda r: (-r["total"], -r["관련자격증수"], r.get("이름", "")))
    return out
