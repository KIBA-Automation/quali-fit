from __future__ import annotations

from html import escape
from math import ceil

import pandas as pd


INFO_COLUMNS = ["work_code", "l1", "l2", "l3", "task_type"]
INFO_LABELS = {
    "work_code": "업무분류코드",
    "l1": "대",
    "l2": "중분류",
    "l3": "소분류",
    "task_type": "산정/검증",
}


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return escape(str(value))


def build_mapping_print_html(
    matrix: pd.DataFrame,
    *,
    bucket: str,
    cert_meta: dict[str, dict],
    certs_per_page: int = 8,
    rows_per_page: int = 40,
) -> str:
    """Build a self-contained, paginated print document for a mapping matrix."""
    if certs_per_page < 1 or rows_per_page < 1:
        raise ValueError("page dimensions must be positive")

    missing = [column for column in INFO_COLUMNS if column not in matrix.columns]
    if missing:
        raise ValueError(f"matrix is missing info columns: {missing}")

    cert_columns = [
        column for column in matrix.columns if column not in INFO_COLUMNS
    ]
    cert_chunks = [
        cert_columns[index:index + certs_per_page]
        for index in range(0, len(cert_columns), certs_per_page)
    ] or [[]]
    row_chunks = [
        matrix.iloc[index:index + rows_per_page]
        for index in range(0, len(matrix), rows_per_page)
    ] or [matrix.iloc[0:0]]

    page_count = len(cert_chunks) * len(row_chunks)
    pages: list[str] = []
    page_number = 0

    for cert_chunk in cert_chunks:
        for row_chunk in row_chunks:
            page_number += 1
            header_cells = "".join(
                f"<th class='info {escape(column)}'>{INFO_LABELS[column]}</th>"
                for column in INFO_COLUMNS
            )
            for cert_code in cert_chunk:
                meta = cert_meta.get(cert_code, {})
                cert_name = escape(str(meta.get("cert_name", cert_code)))
                holder_count = escape(str(meta.get("holder_count", 0)))
                header_cells += (
                    "<th class='cert'>"
                    f"<span class='cert-name'>{cert_name}</span>"
                    f"<span class='cert-code'>{escape(cert_code)}</span>"
                    f"<span class='holders'>{holder_count}명</span>"
                    "</th>"
                )

            body_rows: list[str] = []
            for _, row in row_chunk.iterrows():
                cells = "".join(
                    f"<td class='info {escape(column)}'>{_text(row[column])}</td>"
                    for column in INFO_COLUMNS
                )
                cells += "".join(
                    f"<td class='score'>{_text(row[cert_code])}</td>"
                    for cert_code in cert_chunk
                )
                body_rows.append(f"<tr>{cells}</tr>")

            cert_start = cert_columns.index(cert_chunk[0]) + 1 if cert_chunk else 0
            cert_end = cert_start + len(cert_chunk) - 1 if cert_chunk else 0
            row_start = int(row_chunk.index[0]) + 1 if len(row_chunk) else 0
            row_end = int(row_chunk.index[-1]) + 1 if len(row_chunk) else 0

            pages.append(
                "<section class='print-page'>"
                "<header>"
                f"<h1>업무분류-자격증 매핑: {escape(bucket)}</h1>"
                "<div class='page-meta'>"
                f"자격증 {cert_start}-{cert_end} / 업무 {row_start}-{row_end} "
                f"/ {page_number} of {page_count}"
                "</div>"
                "</header>"
                "<table>"
                f"<thead><tr>{header_cells}</tr></thead>"
                f"<tbody>{''.join(body_rows)}</tbody>"
                "</table>"
                "</section>"
            )

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>업무분류-자격증 매핑 인쇄</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    color: #111;
    background: #f3f4f6;
    font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
  }}
  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
    color: white;
    background: #0f172a;
  }}
  .toolbar button {{
    border: 0;
    border-radius: 6px;
    padding: 8px 16px;
    color: white;
    background: #2563eb;
    font-weight: 700;
    cursor: pointer;
  }}
  .print-page {{
    width: 277mm;
    min-height: 190mm;
    margin: 12px auto;
    padding: 7mm;
    background: white;
    box-shadow: 0 1px 5px rgba(0, 0, 0, .18);
    break-after: page;
    page-break-after: always;
  }}
  .print-page:last-child {{
    break-after: auto;
    page-break-after: auto;
  }}
  header {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 4px;
  }}
  h1 {{ margin: 0; font-size: 12px; }}
  .page-meta {{ color: #475569; font-size: 8px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    font-size: 7px;
  }}
  th, td {{
    height: 4mm;
    padding: 1px 2px;
    overflow: hidden;
    border: .2mm solid #64748b;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  th {{ height: 15mm; background: #e2e8f0; }}
  th.cert {{ width: 7.2%; white-space: normal; }}
  .cert-name, .cert-code, .holders {{ display: block; line-height: 1.25; }}
  .cert-code, .holders {{ color: #475569; font-size: 6px; }}
  .work_code {{ width: 10%; }}
  .l1 {{ width: 3%; }}
  .l2 {{ width: 8%; }}
  .l3 {{ width: 14%; }}
  .task_type {{ width: 6%; }}
  td.l2, td.l3 {{ text-align: left; }}
  td.score {{ font-size: 8px; font-weight: 700; }}
  tbody tr:nth-child(even) {{ background: #f8fafc; }}
  @page {{ size: A4 landscape; margin: 6mm; }}
  @media print {{
    body {{ background: white; }}
    .toolbar {{ display: none; }}
    .print-page {{
      width: auto;
      min-height: 0;
      margin: 0;
      padding: 0;
      box-shadow: none;
    }}
    thead {{ display: table-header-group; }}
  }}
</style>
</head>
<body>
  <div class="toolbar">
    <span>{page_count}페이지 · 자격증 최대 {certs_per_page}열 · 업무 최대 {rows_per_page}행</span>
    <button type="button" onclick="window.print()">인쇄 / PDF 저장</button>
  </div>
  {''.join(pages)}
</body>
</html>"""
