"""서비스 레지스트리. 새 서비스 추가 = 아래 리스트에 1줄."""
from services import cert_master, emp_data, recommend, workcode_master

SERVICES = [
    {"id": "emp_data", "label": "직원 정보", "render": emp_data.render},
    {"id": "cert_master", "label": "한국 자격증 DB", "render": cert_master.render},
    {"id": "workcode_master", "label": "한국경영분석연구원의 업무코드",
     "render": workcode_master.render},
    {"id": "recommend", "label": "원가용역 직원 추천", "render": recommend.render},
]
