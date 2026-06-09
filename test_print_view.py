import unittest

import pandas as pd

from print_view import build_mapping_print_html


class MappingPrintViewTest(unittest.TestCase):
    def test_paginates_eight_cert_columns_and_forty_rows(self):
        rows = 81
        data = {
            "work_code": [f"WORK-{index:03d}" for index in range(rows)],
            "l1": ["C"] * rows,
            "l2": ["제조"] * rows,
            "l3": ["제작"] * rows,
            "task_type": ["산정"] * rows,
        }
        for index in range(9):
            data[f"CERT-{index:02d}"] = [index % 5 + 1] * rows
        matrix = pd.DataFrame(data)

        html = build_mapping_print_html(
            matrix,
            bucket="공통",
            cert_meta={},
        )

        self.assertEqual(html.count("<section class='print-page'>"), 6)
        self.assertIn("6페이지 · 자격증 최대 8열 · 업무 최대 40행", html)
        self.assertIn("자격증 9-9 / 업무 81-81 / 6 of 6", html)

    def test_escapes_database_text(self):
        matrix = pd.DataFrame(
            [{
                "work_code": "<WORK>",
                "l1": "C",
                "l2": "제조",
                "l3": "A&B",
                "task_type": "산정",
                "CERT-01": 5,
            }]
        )

        html = build_mapping_print_html(
            matrix,
            bucket="<공통>",
            cert_meta={
                "CERT-01": {
                    "cert_name": "<자격증>",
                    "holder_count": 1,
                }
            },
        )

        self.assertIn("&lt;WORK&gt;", html)
        self.assertIn("A&amp;B", html)
        self.assertIn("&lt;자격증&gt;", html)
        self.assertNotIn("<자격증>", html)


if __name__ == "__main__":
    unittest.main()
