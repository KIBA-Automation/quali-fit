# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

An internal **multi-service Streamlit platform** (원가용역 사내 서비스): edit the cost-engineering
HR/qualification data and get an explainable staff recommendation for a selected work code.
Data is editable by anyone (no auth) with mandatory validation, atomic CSV write-back, and
timestamped backups. Not a git repo.

## Commands

System Python is 3.14 (no prebuilt pandas/streamlit wheels) — **use the Python 3.13 venv**.

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

No test suite. Verify headlessly with Streamlit's `AppTest` and by exercising the pure
modules (`scoring.py`, `validation.py` are Streamlit-free):

```bash
.venv/bin/python -c "from streamlit.testing.v1 import AppTest;\
 at=AppTest.from_file('app.py',default_timeout=60); at.session_state['nav']='원가용역 직원 추천';\
 at.run(); assert len(at.exception)==0"
```
Browser checks: launch Chrome with `--remote-debugging-port=9222 --headless=new
--user-data-dir=/tmp/...` then drive via the Playwright MCP (`http://localhost:8533/`).

## Data model (normalized, single source of truth)

Six CSVs in `Data/` (UTF-8 BOM). **The user maintains this schema manually**; do not run
`migrate.py` (retired — it assumed the old schema and would corrupt data).

| file | key | columns |
|---|---|---|
| `직원.csv` | PK `직원번호`=`EMP%04d` | 직원번호,이름,소속,직책 |
| `직원_학력.csv` | `학력정보번호`=`{직원번호}-EDU-NN` | 직원번호(FK),학력정보번호,학력,학위,학교명,학부(과),전공,비고 |
| `직원_자격증.csv` | `직원자격증번호`=`{직원번호}-CRT-NN` | 직원번호(FK),직원자격증번호,자격증코드(FK),자격증,취득일,등록일,유효기간 |
| `자격증_마스터.csv` | PK `자격증코드`=`{대분류}-NNNN` | 자격증코드,자격증명,대분류,중분류,원가산정검증활용,자격증내용,수행가능업무,자격유형,증빙유형,자격등급구분,키워드,영향력(1-5),관련부처,시행/발급기관 |
| `업무코드_마스터.csv` | PK `업무분류코드` (path, e.g. `C-제조-제작-산정`) | 업무분류코드,대분류,중분류,소분류,업무구분(산정/검증),분류기준,관리부서,책임자,관련지침,관련법령 |
| `업무코드_자격증_매핑.csv` | (`업무분류코드`,`자격증코드`) | 업무분류코드(FK),자격증코드(FK),업무관련영향력(1-5),영향력 근거,매핑근거 |

- `직원_학력`/`직원_자격증` store **only 직원번호**; 이름·소속·직책 are derived from the roster
  for display (read-only). `직원_자격증.자격증` is derived from `자격증_마스터` by 자격증코드.
- **`업무코드_자격증_매핑.csv` is the single source of the cert↔workcode matching.** No domain
  codes (CA/CB…), no per-cert mapping columns — those concepts are gone. Schema constants live
  in `data_loader.py` (`EMP_COLS`/`EDU_COLS`/`EMPCERT_COLS`/`WCM_COLS`/`MAP_COLS`).
- `업무분류코드` = `{C|P}-중분류-소분류-업무구분` (소분류 omitted when blank), auto-derived.

## Architecture

- **`app.py`** — entry only: `set_page_config` → top `st.segmented_control` nav (persisted to
  `?svc=` query param so browser refresh stays put; `None` on toggle-off → `nav_last` fallback)
  → dispatch to the selected service's `render()`.
- **`services/`** — one module per service, registered in `services/__init__.py` `SERVICES`
  (add a service = one line). Labels are user-facing and have been renamed:
  `emp_data`→**"직원 정보"** (직원/직원_학력/직원_자격증 sub-tabs via `?etab=`),
  `cert_master`→**"한국 자격증 DB"**, `workcode_master`→**"한국경영분석연구원의 업무코드"**
  (sub-tabs via `?wtab=`: **"업무코드"** = editor + a clean 원가/연구용역 split table, **"자격증 매핑"** = the
  업무코드_자격증_매핑 editor — the matching source, merged in here, no longer its own service),
  `recommend`→**"원가용역 직원 추천"**.
- **`services/_common.py::run_editor`** — shared editor→validate→save flow. Params:
  `cols` (persisted, ordered), `display_cols` (editor-only superset incl. derived; not saved),
  `disabled_cols` (read-only/grey), `derive_fn` (recompute linked cols + auto-assign blank IDs;
  applied before display AND before save), `select_cols` ({col:options}→`SelectboxColumn`
  dropdown, typo prevention), `col_widths`, `sort_by`.
- **`data_loader.py`** — `@st.cache_data` loaders (`utf-8-sig`); `build_certs_by_key(empcert_df)` → `{직원번호:[rows]}`.
- **`scoring.py`** (pure) — `WEIGHTS` (tune here), `parse_expiry`, `score_employee(cert_rows,
  qualmap, today)`, `rank_employees`, `MAX_SCORE`.
- **`validation.py`** (pure) — `validate_*` per file → `(errors, warnings)`.
- **`persistence.py`** (Streamlit-free) — `backup_then_atomic_write` (backup→temp in `Data/`→
  `os.replace`; µs timestamp), `prune_backups(keep=20)`.

## Scoring model (in `scoring.py`)

Select 업무분류코드 → `qualmap` = `{자격증코드: {업무관련영향력, 영향력 근거, 매핑근거}}` from
`업무코드_자격증_매핑.csv` for that code. Per employee, each held cert whose 자격증코드 is in
`qualmap` contributes `W_LEVEL × 업무관련영향력`; expired cert (`유효기간` past today) ×
`EXPIRED_FACTOR`. Employee total = best single contribution (**base**) + **breadth** bonus
(`W_BREADTH` per extra matching cert, capped `BREADTH_CAP`). `MAX_SCORE = W_LEVEL*5 +
BREADTH_CAP` (= 45 → drives the ranked table's `ProgressColumn`). `영향력 근거` from the mapping is
surfaced per cert as the explainable "why".

## Invariants (do not regress)

- After any save: call **that loader's `.clear()`** (not global), then `st.rerun()`.
  Concurrency is last-write-wins; backups are the only recovery; a soft mtime-change warning is
  shown before overwrite. Keep it honest.
- Editors: row numbers are the **Excel-like index gutter** (`df.index` 1-based,
  `hide_index=False`) — **no `번호` data column** anywhere.
- **No "경고가 있어도 저장" checkbox**: errors block save; warnings are non-blocking (shown,
  save proceeds). Do not re-add a warning gate.
- Navigation/sub-tab persist via URL query params (`?svc=`, `emp_data` `?etab=` using a
  `segmented_control`, not `st.tabs`). Keep refresh-stable.
- Auto-IDs on blank rows at save: 직원번호 `EMP`max+1; 학력정보번호 `{직원번호}-EDU-NN`
  & 직원자격증번호 `{직원번호}-CRT-NN` (per-employee seq); 자격증_마스터 자격증코드
  `{대분류}-NNNN`; 업무분류코드 from its 4 fields.
- `workcode_master` "업무코드" sub-tab order: editable table **first**, then a clean
  per-대분류 (원가/연구용역) reference table (no Mermaid — replaced by plain `st.dataframe`).
- 학력/자격증 editors sort rows by **직원번호**. The editor caption legend describes the
  actual UI (회색=읽기전용, ▾=드롭다운, 그 외=직접입력) — keep it accurate, no fake color squares.
- `recommend` section order: **1** 업무 코드 선택 (3 dropdowns; below them only a small
  관리부서/책임자 caption — no big metrics), **2** 점수 산정 방식 (static definition of
  기본점수/관련 자격증 수/다양성 보너스/총점), **3** 추천 순위 (ranked table), **4** 상위 5명
  점수 근거 (per-employee cards). 중분류/소분류 selectboxes are ordered by 업무분류코드.
- Dropdown (`select_cols`) for FK/enum fields (직원번호·자격증코드·업무분류코드·영향력·
  소속·직책·학력) to prevent typos; derived cols are `disabled` (grey).
