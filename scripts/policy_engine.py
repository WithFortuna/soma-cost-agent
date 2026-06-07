from __future__ import annotations

import html
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any


DOC_PRIORITY = [
    "00-ai-guide.md",
    "rules.json",
    "02-process-and-deadlines.md",
    "03-board-activity-plan.md",
    "04-board-support-items.md",
    "05-board-payment-methods.md",
    "06-board-evidence-documents.md",
    "01-full-source.md",
]

CATEGORY_ALIASES = {
    "cloud_service_fee": ["aws", "클라우드", "서버", "통합빌링", "통합 빌링"],
    "material_purchase": ["재료", "허브", "벨킨", "디바이스마트", "구매대행", "구매 대행"],
    "equipment_rental": ["기자재", "장비", "임대", "렌탈"],
    "ai_sw_service_fee": ["ai", "sw", "소프트웨어", "라이선스", "api", "구독", "chatgpt", "생성형"],
    "expert_utilization_fee": ["전문가", "디자인", "외주", "번역", "자문", "퍼블리싱", "용역"],
    "marketing_fee": ["마케팅", "광고", "홍보", "배너", "인스타", "구글 광고"],
    "other_fee": ["기타", "논문", "학회", "도메인", "템플릿", "등록비"],
}

CATEGORY_NAME_ALIASES = {
    "클라우드 서비스": "cloud_service_fee",
    "클라우드 서비스 이용료": "cloud_service_fee",
    "재료 구매비": "material_purchase",
    "재료 일반구매": "material_purchase",
    "재료 구매대행": "material_purchase",
    "기자재 임대비": "equipment_rental",
    "AI·SW 서비스 이용료": "ai_sw_service_fee",
    "AI SW 서비스 이용료": "ai_sw_service_fee",
    "AI/SW 서비스 이용료": "ai_sw_service_fee",
    "전문가 활용비": "expert_utilization_fee",
    "디자인 제작비": "expert_utilization_fee",
    "마케팅비": "marketing_fee",
    "기타": "other_fee",
    "기타 사용료": "other_fee",
}

AMBIGUITY_HINTS = {
    "material_purchase": ["맥북", "노트북", "도킹", "독", "dock", "docking", "컴퓨터 부속", "컴퓨터 주변"],
    "expert_utilization_fee": ["개발 외주", "개발자 외주", "개발 용역", "개발 전문가"],
}

CONFLICT_STOP_TERMS = {
    "사용",
    "비용",
    "지원",
    "신청서",
    "확인",
    "여부",
    "항목",
    "프로젝트",
    "필요",
    "구매",
    "결제",
    "발생한",
}

CLASSIFY_STOP_TERMS = CONFLICT_STOP_TERMS | {
    "가능",
    "불가",
    "조건부",
    "정책",
    "문서",
    "기준",
    "판단",
    "근거",
    "파일명",
    "확정",
    "금지",
    "cost",
    "soma",
}

ALL_SUPPORT_ITEM_IDS = [
    "cloud_service_fee",
    "material_purchase",
    "equipment_rental",
    "ai_sw_service_fee",
    "expert_utilization_fee",
    "marketing_fee",
    "other_fee",
]

FORM_FIELD_LABELS = {
    "team_name": "팀명",
    "project_name": "프로젝트명",
    "application_date": "작성일/동의일",
    "round": "신청 회차",
    "item_name": "품목명",
    "service_name": "서비스명",
    "equipment_name": "기자재명",
    "quantity": "수량",
    "amount_krw": "금액(VAT 포함)",
    "use_period": "사용/이용/임대 기간",
    "purchase_reason": "구매/사용 사유",
    "payment_method": "결제방식",
    "team_members": "동의자/팀원",
    "signatures": "자필 또는 전자 서명",
    "evidence_files": "실제 증빙 이미지/파일",
    "orderer_name": "주문자 성명",
    "order_id": "주문 ID",
    "phone": "연락처",
    "email": "이메일",
    "address": "주소",
    "customs_id": "개인통관고유부호",
    "proxy_purchase_items": "구매대행 상품 목록",
    "vendor": "업체명",
    "company_name": "법인명/기업명",
    "business_registration_number": "사업자등록번호",
    "bank_name": "은행명",
    "account_number": "계좌번호",
    "account_holder": "예금주",
    "expert_name": "전문가 성명",
    "resident_registration_number": "주민등록번호",
    "income_type": "소득 유형(사업소득/기타소득)",
    "work_date": "작업 일자",
    "work_time": "작업 시간",
    "work_topic": "작업 주제",
    "work_content": "작업 내용",
    "ad_platform": "광고 플랫폼",
    "ad_period": "광고 기간",
    "usage_item": "사용 항목",
    "usage_description": "사용 내역",
    "receipt_image": "결제 영수증 이미지",
    "card_statement": "카드사 매출전표",
    "transaction_statement": "거래명세서/임대내역서",
    "product_photo": "제품/기자재 사진",
    "company_bankbook_copy": "기업 통장 사본",
    "expert_id_copy": "전문가 신분증 사본",
    "expert_bankbook_copy": "전문가 통장 사본",
    "business_registration_copy": "사업자등록증 사본",
}

SENSITIVE_FORM_FIELDS = {
    "resident_registration_number",
    "bank_name",
    "account_number",
    "account_holder",
    "bank_account",
    "customs_id",
    "phone",
    "email",
    "address",
    "signatures",
    "expert_id_copy",
    "expert_bankbook_copy",
    "company_bankbook_copy",
    "business_registration_copy",
}

MANUAL_ATTACHMENT_FIELDS = {
    "signatures",
    "evidence_files",
    "receipt_image",
    "card_statement",
    "transaction_statement",
    "product_photo",
    "company_bankbook_copy",
    "expert_id_copy",
    "expert_bankbook_copy",
    "business_registration_copy",
}

CORE_ARTIFACT_FIELDS = {
    "team_name",
    "project_name",
    "application_date",
    "item_name",
    "service_name",
    "equipment_name",
    "quantity",
    "amount_krw",
    "use_period",
    "vendor",
    "company_name",
    "expert_name",
    "work_date",
    "work_topic",
    "ad_platform",
    "usage_item",
}

FORM_TEMPLATE_DEFINITIONS = [
    {
        "id": "activity_plan",
        "name_ko": "프로젝트 활동비 활용계획서",
        "stage": "application",
        "extension": ".docx",
        "file_keywords": ["프로젝트 활동비 활용계획서"],
        "related_support_item_ids": ALL_SUPPORT_ITEM_IDS,
        "required_fields": ["project_name", "team_name"],
        "optional_fields": ["item_name", "amount_krw", "use_period", "purchase_reason"],
        "manual_fields": [],
        "output_name": "프로젝트_활동비_활용계획서_{team_name}.docx",
        "notes": ["활용계획서는 프로젝트 단위 계획 문서이며, 항목별 예산 행은 제공된 값만 채웁니다."],
    },
    {
        "id": "cloud_consent",
        "name_ko": "클라우드 서비스 사용 동의서",
        "stage": "application",
        "extension": ".docx",
        "file_keywords": ["클라우드 서비스 사용 동의서"],
        "related_support_item_ids": ["cloud_service_fee"],
        "required_fields": ["team_name", "project_name", "application_date", "team_members"],
        "optional_fields": [],
        "manual_fields": ["signatures"],
        "output_name": "클라우드_서비스_사용_동의서_{team_name}.docx",
        "notes": ["이름 타이핑 서명은 인정되지 않으므로 최종 제출 전 자필 또는 전자 서명이 필요합니다."],
    },
    {
        "id": "proxy_purchase_request",
        "name_ko": "구매대행 신청서",
        "stage": "application",
        "extension": ".xlsx",
        "file_keywords": ["구매대행 신청서"],
        "related_support_item_ids": ["material_purchase"],
        "required_fields": ["orderer_name", "order_id", "phone", "email", "address", "proxy_purchase_items"],
        "optional_fields": ["customs_id"],
        "manual_fields": ["business_registration_copy"],
        "output_name": "구매대행_신청서_{team_name}_{application_date}.xlsx",
        "notes": ["해외 구매대행 건이 포함되면 수령인의 개인통관고유부호를 직접 입력해야 합니다."],
    },
    {
        "id": "material_purchase_evidence_report",
        "name_ko": "재료 구매비 증빙 내역서",
        "stage": "evidence",
        "extension": ".docx",
        "file_keywords": ["재료 구매비 증빙 내역서"],
        "related_support_item_ids": ["material_purchase"],
        "required_fields": ["team_name", "amount_krw", "item_name", "quantity"],
        "optional_fields": [],
        "manual_fields": ["transaction_statement", "product_photo"],
        "output_name": "재료_구매비_증빙_내역서_{team_name}.docx",
        "notes": ["제품 박스 사진은 불인정되며, 실제 개봉 제품과 팀명/제품명 메모가 함께 보여야 합니다."],
    },
    {
        "id": "equipment_rental_evidence_report",
        "name_ko": "기자재 임대비 증빙 내역서",
        "stage": "evidence",
        "extension": ".docx",
        "file_keywords": ["기자재 임대비 증빙 내역서"],
        "related_support_item_ids": ["equipment_rental"],
        "required_fields": ["team_name", "amount_krw", "equipment_name", "quantity", "vendor", "use_period"],
        "optional_fields": [],
        "manual_fields": ["transaction_statement", "product_photo"],
        "output_name": "기자재_임대비_증빙_내역서_{team_name}.docx",
        "notes": ["정식 임대업체 거래명세서 또는 임대 결제 내역과 실제 기자재 사진이 필요합니다."],
    },
    {
        "id": "ai_sw_service_evidence_report",
        "name_ko": "AI·SW 서비스 이용료 증빙 내역서",
        "stage": "evidence",
        "extension": ".docx",
        "file_keywords": ["AI·SW 서비스 이용료 증빙 내역서"],
        "related_support_item_ids": ["ai_sw_service_fee"],
        "required_fields": ["team_name", "amount_krw", "service_name", "use_period"],
        "optional_fields": [],
        "manual_fields": ["receipt_image", "card_statement"],
        "output_name": "AI_SW_서비스_이용료_증빙_내역서_{team_name}.docx",
        "notes": ["업체 발행 결제 영수증과 카드사 매출전표 이미지를 모두 첨부해야 합니다."],
    },
    {
        "id": "expert_utilization_evidence_report",
        "name_ko": "전문가 활용비 증빙 내역서",
        "stage": "evidence",
        "extension": ".docx",
        "file_keywords": ["전문가 활용비 증빙 내역서"],
        "related_support_item_ids": ["expert_utilization_fee"],
        "required_fields": ["team_name", "expert_name", "work_date", "work_time", "work_topic", "work_content"],
        "optional_fields": [],
        "manual_fields": ["evidence_files"],
        "output_name": "전문가_활용비_증빙_내역서_{team_name}.docx",
        "notes": ["작업 결과물 이미지 등 결과를 확인할 수 있는 증빙자료가 필요합니다."],
    },
    {
        "id": "marketing_evidence_report",
        "name_ko": "마케팅비 증빙 내역서",
        "stage": "evidence",
        "extension": ".docx",
        "file_keywords": ["마케팅비 증빙 내역서"],
        "related_support_item_ids": ["marketing_fee"],
        "required_fields": ["team_name", "amount_krw", "ad_platform", "ad_period"],
        "optional_fields": [],
        "manual_fields": ["evidence_files"],
        "output_name": "마케팅비_증빙_내역서_{team_name}.docx",
        "notes": ["광고 결과 자료와 광고 집행 내역을 확인할 수 있는 자료가 필요합니다."],
    },
    {
        "id": "other_fee_evidence_report",
        "name_ko": "기타 사용료 증빙 내역서",
        "stage": "evidence",
        "extension": ".docx",
        "file_keywords": ["기타 사용료 증빙 내역서"],
        "related_support_item_ids": ["other_fee"],
        "required_fields": ["team_name", "amount_krw", "usage_item", "usage_description"],
        "optional_fields": [],
        "manual_fields": ["evidence_files"],
        "output_name": "기타_사용료_증빙_내역서_{team_name}.docx",
        "notes": ["증빙자료를 별도 첨부하는 경우 양식에 '별도 첨부' 문구를 기재해야 합니다."],
    },
    {
        "id": "tax_invoice_payment_request",
        "name_ko": "비용 지급요청서(세금계산서용)",
        "stage": "payment_request",
        "extension": ".docx",
        "file_keywords": ["비용 지급요청서", "세금계산서용"],
        "related_support_item_ids": ["equipment_rental", "expert_utilization_fee", "marketing_fee", "other_fee"],
        "related_payment_method_ids": ["tax_invoice_proxy_payment"],
        "required_fields": ["company_name", "business_registration_number", "bank_name", "account_number", "account_holder"],
        "optional_fields": [],
        "manual_fields": ["business_registration_copy", "company_bankbook_copy"],
        "output_name": "비용_지급요청서_세금계산서용_{team_name}.docx",
        "notes": ["기업 통장 사본에는 이름, 은행명, 계좌번호가 모두 나와야 합니다."],
    },
    {
        "id": "expert_bank_transfer_payment_request",
        "name_ko": "비용 지급요청서(전문가 계좌이체)",
        "stage": "payment_request",
        "extension": ".docx",
        "file_keywords": ["비용 지급요청서", "전문가 계좌이체"],
        "related_support_item_ids": ["expert_utilization_fee"],
        "related_payment_method_ids": ["expert_bank_transfer"],
        "required_fields": [
            "expert_name",
            "application_date",
            "resident_registration_number",
            "income_type",
            "bank_name",
            "account_number",
            "account_holder",
        ],
        "optional_fields": [],
        "manual_fields": ["signatures", "expert_id_copy", "expert_bankbook_copy"],
        "choice_fields": [
            {
                "field": "income_type",
                "options": ["사업소득", "기타소득"],
                "note": "전문가가 해당 수입을 신고하는 유형을 확인해 1개를 체크해야 합니다.",
            }
        ],
        "output_name": "비용_지급요청서_전문가_계좌이체_{team_name}.docx",
        "notes": ["전문가 주민등록번호는 뒷자리까지 필요하며, 신분증/통장 사본은 사용자가 직접 제공해야 합니다."],
    },
    {
        "id": "expert_contract_reference",
        "name_ko": "전문가 계약서 양식",
        "stage": "reference",
        "extension": ".docx",
        "file_keywords": ["전문가 계약서 양식"],
        "related_support_item_ids": ["expert_utilization_fee"],
        "required_fields": [],
        "optional_fields": ["team_name", "project_name", "expert_name", "work_content", "amount_krw", "use_period"],
        "manual_fields": ["signatures"],
        "submission_required": False,
        "output_name": "전문가_계약서_참고양식_{team_name}.docx",
        "notes": ["문서상 사무국 제출 필수 양식이 아니라 참고 양식입니다."],
    },
]

FORM_TEMPLATE_GUIDELINES = {
    "activity_plan": {
        "sources": [
            "03-board-activity-plan.md:19",
            "03-board-activity-plan.md:638",
            "document/extracted/assets/010_1866fd55b379127a_37091e40-1fdf-8067-b455-dc9a95b67e91-__000.txt",
        ],
        "writing": [
            "프로젝트명과 팀명을 실제 값으로 채웁니다.",
            "각 항목의 상세 내용에는 품목명, 단가/수량 또는 사용 기간, 프로젝트 필요 사유를 함께 작성합니다.",
            "클라우드, AI/SW, 마케팅처럼 기간이 중요한 항목은 예상 사용 기간을 포함합니다.",
            "전문가 활용비는 자문 분야, 사유, 예상 인원과 금액을 작성하며 디자인 제작비는 총 500만원 제한을 확인합니다.",
            "마케팅비는 플랫폼, 필요 사유, 예상 금액과 사용 기간을 작성하며 총 400만원 제한을 확인합니다.",
        ],
        "qa": [
            "원본의 예시 문구는 실제 값으로 대체하고 제출본에 남기지 않습니다.",
            "활용계획서 제출 글쓰기 값은 제목/품목명 '프로젝트 활동비 활용계획서', 결제방식/세부사항 '없음', 금액 0입니다.",
        ],
        "notify_if_unmet": [
            "항목별 금액, 기간, 사유가 불명확하면 제출용 파일 생성 전에 사용자에게 확인합니다.",
            "담당 멘토 의견은 파일 생성 이후 포털에서 별도로 요청해야 합니다.",
        ],
    },
    "cloud_consent": {
        "sources": [
            "03-board-activity-plan.md:73",
            "03-board-activity-plan.md:82",
            "document/extracted/assets/008_a0e956e5c85e574e_37091e40-1fdf-804c-b93b-f1c0160df6df-__000.txt",
        ],
        "writing": [
            "팀명, 프로젝트명, 동의일, 팀원별 동의자 이름을 실제 값으로 채웁니다.",
            "신청 글쓰기 값은 품목명 'AWS', 결제방식 '사무국', 세부사항 '없음', 금액 0입니다.",
            "구매사유는 프로젝트 관련성을 판단할 수 있도록 공백 제외 30자 이상이어야 합니다.",
        ],
        "manual": {
            "signatures": [
                "동의자별 자필 또는 전자 서명이 필요합니다.",
                "이름을 타이핑한 서명은 인정되지 않습니다.",
            ]
        },
        "qa": [
            "모든 팀원의 동의자 칸과 서명 칸이 서로 대응되는지 확인합니다.",
            "승인 전 클라우드 서비스 사용은 개인 과금 위험이 있으므로 제출 안내에 남깁니다.",
        ],
        "notify_if_unmet": ["서명본이 없으면 파일은 생성할 수 있어도 제출 준비 완료로 안내하지 않습니다."],
    },
    "proxy_purchase_request": {
        "sources": [
            "03-board-activity-plan.md:220",
            "document/extracted/assets/005_92fd1bb6072eebb6_35f91e40-1fdf-8026-a58a-c9372e9031ec-____00.00.txt",
        ],
        "writing": [
            "파일명은 '구매대행 신청서_팀명_신청일' 형식으로 만들고 확장자는 .xlsx를 유지합니다.",
            "성명, 주문ID, 연락처, 이메일, 주소를 주문자/수령인 기준으로 작성합니다.",
            "구매 상품 리스트에는 품명, 사이트에 표시된 옵션명, 수량, URL을 정확히 작성합니다.",
            "해외 구매대행 건이 포함되면 수령인의 개인통관고유부호가 필요합니다.",
        ],
        "manual": {
            "business_registration_copy": [
                "원본 양식의 필요 서류 칸에 해당하는 실제 첨부 서류는 사용자가 제공해야 합니다."
            ]
        },
        "qa": [
            "디바이스마트에서 구매할 수 없는 제품인지 확인이 필요하면 사용자에게 안내합니다.",
            "옵션명은 판매 페이지에 표시된 문구 그대로 작성했는지 확인합니다.",
        ],
        "notify_if_unmet": ["상품 옵션, 수량, URL 중 하나라도 불명확하면 사용자에게 확인합니다."],
    },
    "material_purchase_evidence_report": {
        "sources": [
            "06-board-evidence-documents.md:24",
            "document/extracted/assets/018_9202289af9f6446a_37191e40-1fdf-805a-ac86-da508f4422ed-__000.txt",
        ],
        "writing": ["팀명, 금액(VAT 포함), 제품명, 수량을 실제 구매 내역과 일치시킵니다."],
        "manual": {
            "transaction_statement": [
                "제품 수령 시 받은 거래명세서 이미지를 첨부합니다.",
                "실물 거래명세서가 없으면 디바이스마트 사이트상의 거래명세서를 첨부합니다.",
                "구매대행 건은 거래명세서 제출을 생략할 수 있습니다.",
            ],
            "product_photo": [
                "제품과 제품명/팀명이 수기로 기재된 메모가 함께 나온 사진을 첨부합니다.",
                "실제 개봉된 제품 사진만 인정되며 제품 박스 사진은 불인정됩니다.",
                "동일 제품을 여러 개 구매한 경우 전체 수량이 확인되어야 하고, 품목별 사진을 각각 첨부해야 합니다.",
            ],
        },
        "qa": ["금액은 VAT 포함 총액인지 확인합니다.", "사진 조건은 자동 검증이 어려우므로 사용자 확인 항목으로 남깁니다."],
        "notify_if_unmet": ["거래명세서 또는 실제 제품 사진 조건을 충족하지 못하면 제출 불가 가능성을 사용자에게 알립니다."],
    },
    "equipment_rental_evidence_report": {
        "sources": [
            "06-board-evidence-documents.md:54",
            "06-board-evidence-documents.md:78",
            "document/extracted/assets/023_bb21db7d9538723f_37191e40-1fdf-80b2-96ed-f5e25a70bc8b-__000.txt",
        ],
        "writing": ["팀명, 금액(VAT 포함), 기자재명, 수량, 임대 업체명, 임대 기간을 실제 임대 내역과 일치시킵니다."],
        "manual": {
            "transaction_statement": [
                "거래명세서 또는 임대내역서 이미지를 첨부합니다.",
                "거래명세서가 없으면 임대 결제 내역을 첨부합니다.",
            ],
            "product_photo": [
                "기자재와 기자재명/팀명이 수기로 기재된 메모가 함께 나온 사진을 첨부합니다.",
                "실제 개봉된 기자재 사진만 인정되며 기자재 박스 사진은 불인정됩니다.",
                "동일 기자재를 여러 개 임대한 경우 전체 수량이 확인되어야 하고, 품목별 사진을 각각 첨부해야 합니다.",
            ],
        },
        "qa": ["임대 기간이 신청/결제 기간과 어긋나지 않는지 확인합니다.", "사진 조건은 자동 검증이 어려우므로 사용자 확인 항목으로 남깁니다."],
        "notify_if_unmet": ["임대내역서 또는 실제 기자재 사진 조건을 충족하지 못하면 제출 불가 가능성을 사용자에게 알립니다."],
    },
    "ai_sw_service_evidence_report": {
        "sources": [
            "06-board-evidence-documents.md:115",
            "document/extracted/assets/016_55440ba157014f29_37191e40-1fdf-804c-a00f-ead0a63f1f5e-_AI_SW.txt",
        ],
        "writing": ["팀명, 금액(VAT 포함), 서비스명, 이용 기간을 실제 결제 내역과 일치시킵니다."],
        "manual": {
            "receipt_image": [
                "결제 직후 받은 업체 발행 결제 영수증 또는 결제 내역 이미지를 첨부합니다.",
                "서비스 이용료는 매월 월 단위 결제를 원칙으로 합니다.",
            ],
            "card_statement": [
                "카드사 앱 또는 홈페이지에서 매출전표를 출력해 이미지를 첨부합니다.",
                "카드사 매출전표는 결제일 기준 2~3일 후 확인 가능하며 실제 결제 금액 확인을 위한 필수 서류입니다.",
            ],
        },
        "qa": ["영수증 금액과 매출전표 금액이 양식의 금액(VAT 포함)과 일치하는지 확인합니다."],
        "notify_if_unmet": ["영수증과 카드사 매출전표 중 하나라도 없으면 제출 준비 완료로 안내하지 않습니다."],
    },
    "expert_utilization_evidence_report": {
        "sources": [
            "06-board-evidence-documents.md:153",
            "06-board-evidence-documents.md:206",
            "06-board-evidence-documents.md:236",
            "document/extracted/assets/012_5faba595c82ae8b5_37191e40-1fdf-8014-9889-d2cce7557d52-__000.txt",
        ],
        "writing": [
            "팀명, 전문가명 또는 기업명, 작업 일자, 작업 시간, 주제를 실제 수행 내역과 일치시킵니다.",
            "내용에는 작업 또는 자문 내용을 구체적으로 쓰고, 진행 결과와 현재 완료 수준을 함께 작성합니다.",
            "계좌이체 정산 기준은 1일 최대 4시간, 시간당 10만원입니다.",
        ],
        "manual": {
            "evidence_files": [
                "작업 결과물 이미지 등 작업 결과를 확인할 수 있는 증빙자료를 첨부합니다.",
                "증빙자료를 별도 첨부하면 양식에는 '별도 첨부' 문구를 기재합니다.",
                "기간 내 최종 결과물 제출이 어려우면 중간 수행 자료를 우선 제출하고 추후 최종 결과 자료를 별도 제출해야 합니다.",
            ]
        },
        "qa": ["작업 결과물은 결제가 이루어진 해당 신청 회차 제출 기간 내 자료인지 확인합니다."],
        "notify_if_unmet": ["작업 결과 증빙이 없거나 완료 수준이 불명확하면 사용자에게 보완 안내를 합니다."],
    },
    "marketing_evidence_report": {
        "sources": [
            "06-board-evidence-documents.md:276",
            "06-board-evidence-documents.md:304",
            "document/extracted/assets/014_18df64f92ba1a78d_37191e40-1fdf-8039-a205-fc42f49185cd-__000.txt",
        ],
        "writing": ["팀명, 금액(VAT 포함), 광고 플랫폼, 광고 기간을 실제 집행 내역과 일치시킵니다."],
        "manual": {
            "evidence_files": [
                "광고 게시물, 홍보 URL, 배너 제작 결과물 등 광고 수행 결과 자료를 첨부합니다.",
                "광고 노출 횟수, 조회수, 클릭수 등 마케팅 집행 내역을 확인할 수 있는 자료를 첨부합니다.",
                "기간 내 최종 자료 제출이 어려우면 광고 집행 진행 상황 또는 중간 수행 자료를 우선 제출하고 추후 최종 결과 자료를 별도 제출해야 합니다.",
            ]
        },
        "qa": ["광고 결과 자료와 집행 내역은 결제가 이루어진 해당 신청 회차 제출 기간 내 자료인지 확인합니다."],
        "notify_if_unmet": ["광고 결과 자료 또는 집행 지표가 없으면 제출 준비 완료로 안내하지 않습니다."],
    },
    "other_fee_evidence_report": {
        "sources": [
            "06-board-evidence-documents.md:345",
            "06-board-evidence-documents.md:361",
            "document/extracted/assets/015_48b79fab6cfc7988_37191e40-1fdf-804a-8e17-e2a21752a921-__000.txt",
        ],
        "writing": ["팀명, 금액(VAT 포함), 사용 항목, 활용 내역을 실제 사용 내용과 일치시킵니다."],
        "manual": {
            "evidence_files": [
                "활용 내역 및 결과를 확인할 수 있는 증빙자료를 첨부합니다.",
                "증빙자료를 별도 첨부하면 양식에는 '별도 첨부' 문구를 기재합니다.",
            ]
        },
        "qa": ["사용 항목과 증빙자료의 서비스/행사/등록 내용이 일치하는지 확인합니다."],
        "notify_if_unmet": ["활용 결과를 확인할 수 있는 자료가 없으면 사용자에게 보완 안내를 합니다."],
    },
    "tax_invoice_payment_request": {
        "sources": [
            "05-board-payment-methods.md:192",
            "06-board-evidence-documents.md:255",
            "06-board-evidence-documents.md:325",
            "06-board-evidence-documents.md:370",
            "document/extracted/assets/017_6b066dd49cd35106_37191e40-1fdf-8059-ba8e-c53846b53e96-__000.txt",
        ],
        "writing": ["법인명, 사업자등록번호, 은행명, 계좌번호, 예금주를 실제 기업 서류와 일치시킵니다."],
        "manual": {
            "business_registration_copy": ["사업자등록증 사본은 사용자가 직접 제공해야 합니다."],
            "company_bankbook_copy": ["기업 통장 사본에는 이름, 은행명, 계좌번호가 모두 보여야 합니다."],
        },
        "qa": ["항목별 증빙 내역서와 비용 지급요청서를 모두 제출해야 합니다.", "승인받은 사용신청서 금액을 초과한 비용 지급은 불가합니다."],
        "notify_if_unmet": ["사업자등록증 또는 기업 통장 사본 조건을 충족하지 못하면 제출 준비 완료로 안내하지 않습니다."],
    },
    "expert_bank_transfer_payment_request": {
        "sources": [
            "05-board-payment-methods.md:135",
            "06-board-evidence-documents.md:178",
            "document/extracted/assets/022_6a3752d1640fa095_37191e40-1fdf-8092-8a67-f436e97fb644-__000.txt",
        ],
        "fields": {
            "income_type": [
                "사업소득 또는 기타소득 중 1개를 체크해야 합니다.",
                "체크하지 않으면 별도 확인 없이 기타소득으로 신고되어 비용이 지급됩니다.",
            ],
            "resident_registration_number": ["주민등록번호는 뒷자리까지 작성해야 비용 지급이 가능합니다."],
        },
        "writing": [
            "전문가 성명, 작성일, 주민등록번호, 은행명, 계좌번호, 예금주를 실제 지급 정보와 일치시킵니다.",
            "전문가 계좌로는 원천징수 후 금액이 입금되므로 사업소득/기타소득 선택을 확인합니다.",
            "증빙 내역서의 작업 일자와 비용 지급요청서의 작성일이 동일해야 합니다.",
        ],
        "manual": {
            "signatures": ["개인정보 수집·이용 동의서의 성명 및 서명은 전문가가 직접 작성해야 합니다."],
            "expert_id_copy": [
                "전문가 신분증 사본에는 성명과 주민등록번호가 모두 보여야 합니다.",
                "주민등록번호 뒷자리를 가리면 비용 지급이 불가합니다.",
            ],
            "expert_bankbook_copy": ["전문가 통장 사본에는 예금주, 은행명, 계좌번호가 모두 보여야 합니다."],
        },
        "qa": [
            "사업소득은 3.3%, 기타소득은 8.8% 원천징수 후 지급되는 점을 사용자에게 안내합니다.",
            "전문가 활용비 증빙 내역서와 비용 지급요청서를 모두 제출해야 합니다.",
        ],
        "notify_if_unmet": ["소득 유형, 서명, 신분증/통장 사본 조건을 충족하지 못하면 제출 준비 완료로 안내하지 않습니다."],
    },
    "expert_contract_reference": {
        "sources": ["03-board-activity-plan.md:414"],
        "writing": ["전문가 계약서는 제출 필수 양식이 아니라 참고 양식으로만 노출합니다."],
        "manual": {"signatures": ["참고 계약서로 사용하는 경우 당사자 서명은 사용자가 직접 받아야 합니다."]},
        "qa": ["제출 필수 서류로 오인되지 않도록 최종 안내에 참고 양식임을 명시합니다."],
        "notify_if_unmet": ["제출 필수로 안내하지 않습니다."],
    },
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value)


def has_form_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def template_guidelines(template: dict[str, Any]) -> dict[str, Any]:
    raw = FORM_TEMPLATE_GUIDELINES.get(template.get("id"), {})
    return {
        "sources": list(raw.get("sources", [])),
        "writing": list(raw.get("writing", [])),
        "fields": dict(raw.get("fields", {})),
        "manual": dict(raw.get("manual", {})),
        "qa": list(raw.get("qa", [])),
        "notify_if_unmet": list(raw.get("notify_if_unmet", [])),
    }


def field_guidelines(template: dict[str, Any], field: str) -> list[str]:
    guidelines = template_guidelines(template)
    return list(guidelines.get("fields", {}).get(field, []))


def manual_guidelines(template: dict[str, Any], field: str) -> list[str]:
    guidelines = template_guidelines(template)
    return list(guidelines.get("manual", {}).get(field, []))


def selected_template_sources(templates: list[dict[str, Any]]) -> list[str]:
    sources: set[str] = set()
    for template in templates:
        sources.update(template_guidelines(template).get("sources", []))
    return sorted(sources)


def document_root() -> Path:
    configured = os.environ.get("COST_SOMA_DOCUMENT_ROOT")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / "document",
            cwd.parent / "document",
            Path(__file__).resolve().parents[1] / "document",
            Path(__file__).resolve().parents[2] / "document",
        ]
    )
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "rules.json").exists():
            return resolved
    raise RuntimeError("Could not locate Cost SOMA document root with rules.json")


def assets_root() -> Path:
    return document_root() / "assets"


def path_to_document_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(document_root().resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def resolve_template_source(template: dict[str, Any]) -> dict[str, Any]:
    root = assets_root()
    extension = template.get("extension", "")
    keywords = template.get("file_keywords", [])
    matches = []
    if root.exists():
        for path in sorted(root.glob(f"*{extension}")):
            name = path.name
            if all(keyword in name for keyword in keywords):
                matches.append(path)

    source: dict[str, Any] = {
        "exists": bool(matches),
        "extension": extension,
        "keywords": keywords,
    }
    if matches:
        path = matches[0].resolve()
        source.update(
            {
                "path": str(path),
                "relative_path": f"assets/{path.name}",
                "duplicates": [f"assets/{item.name}" for item in matches[1:]],
            }
        )
    else:
        source["missing_reason"] = "No matching source template was found under document/assets."
    return source


def normalize_stage(stage: str | None) -> str:
    value = normalize(stage or "auto")
    aliases = {
        "신청": "application",
        "신청서": "application",
        "application": "application",
        "apply": "application",
        "증빙": "evidence",
        "증빙서류": "evidence",
        "evidence": "evidence",
        "정산": "evidence",
        "지급": "payment_request",
        "지급요청": "payment_request",
        "지급요청서": "payment_request",
        "payment": "payment_request",
        "payment_request": "payment_request",
        "reference": "reference",
        "참고": "reference",
        "all": "all",
        "전체": "all",
        "auto": "auto",
    }
    return aliases.get(value, "auto")


def normalize_payment_method_id(payment_method: str | None) -> str | None:
    if not payment_method:
        return None
    value = normalize(payment_method)
    if contains_any(value, ["세금계산서", "세금 계산서", "tax"]):
        return "tax_invoice_proxy_payment"
    if contains_any(value, ["전문가 계좌", "계좌이체", "계좌 이체", "bank"]):
        return "expert_bank_transfer"
    if contains_any(value, ["구매대행", "구매 대행", "proxy"]):
        return "devicemart_proxy_purchase"
    if contains_any(value, ["디바이스마트", "일반구매", "일반 구매"]):
        return "devicemart_general_purchase"
    if contains_any(value, ["사후정산", "선결제", "reimbursement"]):
        return "trainee_prepaid_reimbursement"
    if contains_any(value, ["사무국", "카드결제", "카드 결제"]):
        return "office_card_visit"
    return None


def template_matches_category(template: dict[str, Any], item: dict[str, Any] | None) -> bool:
    if not item:
        return True
    related = template.get("related_support_item_ids", [])
    return not related or item.get("id") in related


def template_matches_stage(template: dict[str, Any], stage: str) -> bool:
    return stage in {"auto", "all"} or template.get("stage") == stage


def form_template_payload(template: dict[str, Any], include_source: bool = True) -> dict[str, Any]:
    payload = {
        "id": template["id"],
        "name_ko": template["name_ko"],
        "stage": template["stage"],
        "extension": template["extension"],
        "related_support_item_ids": template.get("related_support_item_ids", []),
        "related_payment_method_ids": template.get("related_payment_method_ids", []),
        "submission_required": template.get("submission_required", True),
        "required_fields": template.get("required_fields", []),
        "optional_fields": template.get("optional_fields", []),
        "manual_fields": template.get("manual_fields", []),
        "choice_fields": template.get("choice_fields", []),
        "notes": template.get("notes", []),
        "guidelines": template_guidelines(template),
    }
    if include_source:
        payload["source_template"] = resolve_template_source(template)
    return payload


def list_policy_form_templates(category: str | None = None, stage: str | None = None) -> dict[str, Any]:
    normalized_stage = normalize_stage(stage)
    item = item_by_category(category or "") if category else None
    templates = []
    selected_definitions = []
    for template in FORM_TEMPLATE_DEFINITIONS:
        if category and not template_matches_category(template, item):
            continue
        if normalized_stage != "auto" and not template_matches_stage(template, normalized_stage):
            continue
        templates.append(form_template_payload(template))
        selected_definitions.append(template)
    return {
        "category": category,
        "category_id": item.get("id") if item else None,
        "stage": normalized_stage,
        "templates": templates,
        "sources": sorted(set(["07-attachments.md", "rules.json", "document/assets", *selected_template_sources(selected_definitions)])),
    }


def wants_proxy_purchase(question: str, payment_method: str | None, known_values: dict[str, Any]) -> bool:
    purchase_mode = str(known_values.get("purchase_mode") or "")
    return contains_any(" ".join([question, payment_method or "", purchase_mode]), ["구매대행", "구매 대행", "proxy", "대행"])


def wants_form_generation(question: str) -> bool:
    return contains_any(
        question,
        [
            "양식",
            "서식",
            "신청서",
            "증빙 내역서",
            "지급요청서",
            "동의서",
            "활용계획서",
            "docx",
            "xlsx",
            "작성",
            "제출용",
            "파일",
        ],
    )


def wants_evidence_stage(question: str) -> bool:
    return contains_any(question, ["증빙", "영수증", "정산", "매출전표", "거래명세서", "수령", "작업 완료"])


def wants_payment_request_stage(question: str, payment_method: str | None) -> bool:
    return contains_any(" ".join([question, payment_method or ""]), ["지급요청", "지급 요청", "세금계산서", "계좌이체", "계좌 이체"])


def select_form_templates(
    question: str,
    item: dict[str, Any] | None,
    stage: str,
    payment_method: str | None,
    known_values: dict[str, Any],
) -> list[dict[str, Any]]:
    category_id = item.get("id") if item else None
    payment_method_id = normalize_payment_method_id(payment_method)
    selected_ids: list[str] = []

    def add(template_id: str) -> None:
        if template_id not in selected_ids:
            selected_ids.append(template_id)

    if stage == "all":
        if category_id:
            add("activity_plan")
        if category_id == "cloud_service_fee":
            add("cloud_consent")
        if category_id == "material_purchase" and wants_proxy_purchase(question, payment_method, known_values):
            add("proxy_purchase_request")
        for template in FORM_TEMPLATE_DEFINITIONS:
            if template.get("stage") == "evidence" and category_id in template.get("related_support_item_ids", []):
                add(template["id"])
        if payment_method_id == "tax_invoice_proxy_payment":
            add("tax_invoice_payment_request")
        if payment_method_id == "expert_bank_transfer":
            add("expert_bank_transfer_payment_request")
    elif stage == "application":
        if contains_any(question, ["활용계획서", "계획서"]) or known_values.get("include_activity_plan"):
            add("activity_plan")
        if category_id == "cloud_service_fee":
            add("cloud_consent")
        if category_id == "material_purchase" and wants_proxy_purchase(question, payment_method, known_values):
            add("proxy_purchase_request")
    elif stage == "evidence":
        for template in FORM_TEMPLATE_DEFINITIONS:
            if template.get("stage") == "evidence" and category_id in template.get("related_support_item_ids", []):
                add(template["id"])
    elif stage == "payment_request":
        if payment_method_id == "tax_invoice_proxy_payment":
            add("tax_invoice_payment_request")
        elif payment_method_id == "expert_bank_transfer":
            add("expert_bank_transfer_payment_request")
    elif stage == "reference":
        if category_id == "expert_utilization_fee":
            add("expert_contract_reference")
    else:
        if contains_any(question, ["활용계획서", "계획서"]):
            add("activity_plan")
        if category_id == "cloud_service_fee":
            add("cloud_consent")
        if category_id == "material_purchase" and wants_proxy_purchase(question, payment_method, known_values):
            add("proxy_purchase_request")
        if wants_evidence_stage(question):
            for template in FORM_TEMPLATE_DEFINITIONS:
                if template.get("stage") == "evidence" and category_id in template.get("related_support_item_ids", []):
                    add(template["id"])
        if wants_payment_request_stage(question, payment_method):
            if payment_method_id == "expert_bank_transfer" or (
                category_id == "expert_utilization_fee" and contains_any(question, ["계좌"])
            ):
                add("expert_bank_transfer_payment_request")
            elif payment_method_id == "tax_invoice_proxy_payment" or contains_any(question, ["세금계산서"]):
                add("tax_invoice_payment_request")

    by_id = {template["id"]: template for template in FORM_TEMPLATE_DEFINITIONS}
    return [by_id[template_id] for template_id in selected_ids if template_id in by_id]


def value_from_known(known_values: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = known_values.get(key)
        if value not in (None, ""):
            return value
    return None


def infer_form_value(field: str, question: str, item: dict[str, Any] | None, known_values: dict[str, Any], payment_method: str | None) -> tuple[Any, str]:
    direct = value_from_known(known_values, field)
    if direct is not None:
        return direct, "provided"
    if field == "item_name" and item:
        return value_from_known(known_values, "product_name", "service_name", "equipment_name") or infer_subject(question, item), "draft"
    if field == "service_name":
        return value_from_known(known_values, "item_name") or infer_subject(question, item or {}), "draft"
    if field == "equipment_name":
        return value_from_known(known_values, "item_name") or infer_subject(question, item or {}), "draft"
    if field == "usage_item":
        return value_from_known(known_values, "item_name") or infer_subject(question, item or {}), "draft"
    if field == "usage_description" and item:
        return draft_purchase_reason(question, item, infer_subject(question, item)), "draft"
    if field == "purchase_reason" and item:
        return draft_purchase_reason(question, item, infer_subject(question, item)), "draft"
    if field == "payment_method":
        return payment_method, "provided" if payment_method else "missing"
    if field == "income_type":
        if contains_any(question, ["사업소득", "사업 소득"]):
            return "사업소득", "draft"
        if contains_any(question, ["기타소득", "기타 소득"]):
            return "기타소득", "draft"
        return None, "missing"
    if field == "amount_krw" and item and item.get("id") == "cloud_service_fee":
        return 0, "fixed"
    return None, "missing"


def output_filename(template: dict[str, Any], known_values: dict[str, Any]) -> str:
    replacements = {
        "team_name": str(known_values.get("team_name") or "팀명"),
        "application_date": str(known_values.get("application_date") or "작성일"),
    }
    name = template.get("output_name", f"{template['id']}{template['extension']}")
    for key, value in replacements.items():
        safe = re.sub(r"[\\/:*?\"<>|]+", "_", value).strip() or key
        name = name.replace("{" + key + "}", safe)
    return name


def build_template_fill_fields(
    template: dict[str, Any],
    question: str,
    item: dict[str, Any] | None,
    known_values: dict[str, Any],
    payment_method: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    manual_steps: list[dict[str, Any]] = []
    draft_values: dict[str, Any] = {}
    required = set(template.get("required_fields", []))
    optional = set(template.get("optional_fields", []))
    manual = set(template.get("manual_fields", []))

    for field in [*template.get("required_fields", []), *template.get("optional_fields", [])]:
        value, status = infer_form_value(field, question, item, known_values, payment_method)
        guidelines = field_guidelines(template, field)
        entry = {
            "field": field,
            "label": FORM_FIELD_LABELS.get(field, field),
            "required": field in required,
            "sensitive": field in SENSITIVE_FORM_FIELDS,
            "manual_attachment": field in MANUAL_ATTACHMENT_FIELDS,
            "status": status if value not in (None, "") else ("missing" if field in required else "optional_missing"),
            "source": "known_values" if status == "provided" else "draft" if status == "draft" else "fixed" if status == "fixed" else "user",
        }
        if guidelines:
            entry["guidelines"] = guidelines
        if value not in (None, ""):
            entry["value"] = value
            draft_values[field] = value
        elif field in required:
            entry["blocks_generation"] = True
            missing.append(
                {
                    "field": field,
                    "label": entry["label"],
                    "template_id": template["id"],
                    "sensitive": entry["sensitive"],
                    "reason": "제출용 양식에 직접 기입해야 하는 필수 값입니다.",
                    "guidelines": guidelines,
                }
            )
        fields.append(entry)

    for field in manual:
        provided_value = value_from_known(known_values, field)
        provided = has_form_value(provided_value)
        guidelines = manual_guidelines(template, field)
        text = (
            " ".join(guidelines)
            if guidelines
            else f"{FORM_FIELD_LABELS.get(field, field)}은 Codex가 추정하거나 생성하지 말고 사용자가 직접 첨부/서명해야 합니다."
        )
        step = {
            "field": field,
            "label": FORM_FIELD_LABELS.get(field, field),
            "template_id": template["id"],
            "sensitive": field in SENSITIVE_FORM_FIELDS,
            "blocks_generation": False,
            "blocks_submission": template.get("submission_required", True) and not provided,
            "provided": provided,
            "status": "manual_provided" if provided else "manual_required",
            "text": text,
            "guidelines": guidelines,
        }
        if provided and not step["sensitive"]:
            step["value"] = provided_value
        manual_steps.append(step)
        field_entry = {
            "field": field,
            "label": step["label"],
            "required": False,
            "sensitive": step["sensitive"],
            "manual_attachment": True,
            "status": step["status"],
            "blocks_generation": False,
            "blocks_submission": step["blocks_submission"],
        }
        if guidelines:
            field_entry["guidelines"] = guidelines
        fields.append(field_entry)

    return fields, missing, manual_steps, draft_values


def collect_choice_fields(
    form_bundle: dict[str, Any],
    item: dict[str, Any] | None,
    payment_method: str | None,
    selected_templates: list[dict[str, Any]],
    known_values: dict[str, Any],
) -> list[dict[str, Any]]:
    choices = []
    for choice in form_bundle.get("user_choices_needed", []) if form_bundle.get("found") else []:
        choices.append(
            {
                "field": choice.get("field"),
                "options": choice.get("options", []),
                "note": choice.get("note"),
                "source": "draft_application_form",
            }
        )

    for template in selected_templates:
        for choice in template.get("choice_fields", []):
            if has_form_value(value_from_known(known_values, choice.get("field", ""))):
                continue
            choices.append(
                {
                    "field": choice.get("field"),
                    "options": choice.get("options", []),
                    "note": choice.get("note"),
                    "template_id": template.get("id"),
                    "source": "form_template",
                }
            )

    needs_payment_request = any(template.get("stage") == "payment_request" for template in selected_templates)
    if item and needs_payment_request and not payment_method:
        docs = get_required_documents(item.get("id", ""))
        options = [method.get("name_ko") for method in docs.get("payment_methods", []) if method.get("name_ko")]
        if options:
            choices.append(
                {
                    "field": "payment_method",
                    "options": options,
                    "note": "비용 지급요청서 종류는 결제/지급 방식에 따라 달라집니다.",
                    "source": "payment_methods",
                }
            )
    return choices


def prepare_policy_form_packet(
    question: str,
    category: str | None = None,
    stage: str = "auto",
    payment_method: str | None = None,
    known_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    known_values = dict(known_values or {})
    normalized_stage = normalize_stage(stage)
    classification = classify_expense_item(question, max_candidates=3)
    item = item_by_category(category or "") if category else None
    if not item and classification["candidates"]:
        item = item_by_category(classification["candidates"][0]["category_id"])

    if not item:
        return {
            "found": False,
            "question": question,
            "stage": normalized_stage,
            "payment_method": payment_method,
            "templates": [],
            "draft_values": {},
            "choice_fields": [],
            "missing_required_fields": [],
            "manual_steps": [],
            "artifact_instructions": [],
            "sources": ["rules.json", "07-attachments.md"],
            "ready_to_generate": False,
            "classification_summary": classification,
            "error": "No support category could be selected from local document evidence.",
        }

    form_bundle = draft_application_form(question, item.get("id"))
    selected_templates = select_form_templates(question, item, normalized_stage, payment_method, known_values)
    packet_templates = []
    all_missing: list[dict[str, Any]] = []
    all_manual_steps: list[dict[str, Any]] = []
    all_draft_values: dict[str, Any] = {}
    artifact_instructions = []

    for template in selected_templates:
        fields, missing, manual_steps, draft_values = build_template_fill_fields(
            template, question, item, known_values, payment_method
        )
        guidelines = template_guidelines(template)
        all_missing.extend(missing)
        all_manual_steps.extend(manual_steps)
        all_draft_values.update(draft_values)
        source = resolve_template_source(template)
        packet_template = form_template_payload(template, include_source=False)
        packet_template.update(
            {
                "source_template": source,
                "output_filename": output_filename(template, {**known_values, **all_draft_values}),
                "fill_fields": fields,
            }
        )
        packet_templates.append(packet_template)

        skill_name = "Documents" if template["extension"] == ".docx" else "Spreadsheets"
        qa = (
            "원본 DOCX를 복사해 필요한 필드를 채운 뒤 render_docx.py로 페이지 PNG를 렌더링하고 육안 확인합니다."
            if template["extension"] == ".docx"
            else "원본 XLSX를 복사해 필요한 셀을 채운 뒤 workbook inspect/render로 값과 시각 상태를 확인합니다."
        )
        artifact_instructions.append(
            {
                "template_id": template["id"],
                "skill": skill_name,
                "output_dir": "outputs/cost-soma-forms/<timestamp>/",
                "output_filename": packet_template["output_filename"],
                "qa": qa,
                "must_follow_guidelines": guidelines.get("writing", []) + guidelines.get("qa", []),
                "manual_conditions": [
                    {
                        "field": step.get("field"),
                        "label": step.get("label"),
                        "provided": step.get("provided", False),
                        "blocks_submission": step.get("blocks_submission", False),
                        "guidelines": step.get("guidelines", []),
                        "text": step.get("text"),
                    }
                    for step in manual_steps
                ],
                "notify_user_if_unmet": guidelines.get("notify_if_unmet", []),
                "upload_boundary": "파일 생성까지만 수행합니다. 외부 사이트 업로드는 자동화하지 않습니다.",
            }
        )

    choice_fields = collect_choice_fields(form_bundle, item, payment_method, selected_templates, {**known_values, **all_draft_values})
    unresolved_manual_steps = [step for step in all_manual_steps if step.get("blocks_submission")]
    ready_to_generate = bool(packet_templates) and not all_missing and all(template["source_template"].get("exists") for template in packet_templates)
    manual_requirements_satisfied = not unresolved_manual_steps
    if not packet_templates and not wants_form_generation(question):
        note = "현재 질문은 제출용 원본 양식 작성 요청으로 판단되지 않아 파일 생성 단계는 생략합니다."
    elif not packet_templates:
        note = "선택한 단계/항목에 해당하는 제출용 원본 양식이 문서상 확인되지 않습니다."
    elif unresolved_manual_steps:
        note = "파일 생성은 가능하지만 제출 전 사용자가 직접 충족해야 하는 서명/첨부 조건이 남아 있습니다."
    else:
        note = "missing_required_fields가 비어 있으면 Codex가 Documents/Spreadsheets 스킬로 실제 파일을 작성할 수 있습니다."

    sources = sorted(
        set(
            [
                "rules.json",
                "07-attachments.md",
                "document/assets",
                *form_bundle.get("sources", []),
                *selected_template_sources(selected_templates),
            ]
        )
    )
    return {
        "found": True,
        "question": question,
        "category_id": item.get("id"),
        "category_name": item.get("name_ko"),
        "stage": normalized_stage,
        "payment_method": payment_method,
        "payment_method_id": normalize_payment_method_id(payment_method),
        "templates": packet_templates,
        "draft_values": all_draft_values,
        "choice_fields": choice_fields,
        "missing_required_fields": all_missing,
        "manual_steps": all_manual_steps,
        "remaining_submission_requirements": unresolved_manual_steps,
        "artifact_instructions": artifact_instructions,
        "web_application": form_bundle if form_bundle.get("found") else None,
        "sources": sources,
        "ready_to_generate": ready_to_generate,
        "manual_requirements_satisfied": manual_requirements_satisfied,
        "classification_summary": classification,
        "note": note,
    }


def extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        parts = []
        for name in archive.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                xml = archive.read(name).decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", xml)
                parts.append(html.unescape(text))
        return normalize(" ".join(parts))


def extract_xlsx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        parts = []
        for name in archive.namelist():
            if name.endswith(".xml") and (name.startswith("xl/sharedStrings") or name.startswith("xl/worksheets/")):
                xml = archive.read(name).decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", xml)
                parts.append(html.unescape(text))
        return normalize(" ".join(parts))


def extract_artifact_text(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return extract_docx_text(path)
    if path.suffix.lower() == ".xlsx":
        return extract_xlsx_text(path)
    return ""


def expected_core_values(template: dict[str, Any]) -> list[str]:
    values = []
    for field in template.get("fill_fields", []):
        if field.get("field") not in CORE_ARTIFACT_FIELDS:
            continue
        value = field.get("value")
        if value in (None, ""):
            continue
        if isinstance(value, (list, dict)):
            continue
        values.append(str(value))
    return values[:6]


def value_is_visible(value: str, artifact_text: str) -> bool:
    norm_value = normalize(value)
    if norm_value in artifact_text:
        return True
    compact_value = norm_value.replace(",", "")
    compact_text = artifact_text.replace(",", "")
    return bool(compact_value and compact_value in compact_text)


def validate_form_artifacts(form_packet: dict[str, Any], artifact_paths: list[str]) -> dict[str, Any]:
    templates = form_packet.get("templates", [])
    findings = []
    warnings = []
    artifact_results = []
    unused_paths = [Path(path) for path in artifact_paths]
    unresolved_required_fields = list(form_packet.get("missing_required_fields", []))
    unresolved_manual_steps = [
        step for step in form_packet.get("manual_steps", []) if step.get("blocks_submission") and not step.get("provided")
    ]
    if unresolved_required_fields:
        warnings.append("Generated artifacts cannot be submission-ready while required form fields are still missing.")
    if unresolved_manual_steps:
        warnings.append("Generated artifacts still require user-provided signatures, attachments, or sensitive supporting documents before submission.")

    for template in templates:
        expected_ext = template.get("extension")
        matched_index = None
        for index, path in enumerate(unused_paths):
            if path.suffix.lower() == expected_ext:
                matched_index = index
                break
        if matched_index is None:
            findings.append(f"Missing generated artifact for template {template.get('id')} ({expected_ext}).")
            artifact_results.append({"template_id": template.get("id"), "passed": False, "error": "missing_artifact"})
            continue

        path = unused_paths.pop(matched_index)
        result: dict[str, Any] = {
            "template_id": template.get("id"),
            "path": str(path),
            "expected_extension": expected_ext,
            "passed": True,
            "checked_values": [],
            "qa_guidelines": template.get("guidelines", {}).get("qa", []),
        }
        if not path.exists():
            result["passed"] = False
            result["error"] = "file_not_found"
            findings.append(f"Artifact not found: {path}")
            artifact_results.append(result)
            continue
        if path.suffix.lower() != expected_ext:
            result["passed"] = False
            result["error"] = "extension_mismatch"
            findings.append(f"Artifact extension mismatch for {path}: expected {expected_ext}.")
            artifact_results.append(result)
            continue

        try:
            artifact_text = extract_artifact_text(path)
        except Exception as exc:  # noqa: BLE001 - report validation issues.
            result["passed"] = False
            result["error"] = f"text_extract_failed: {exc}"
            findings.append(f"Could not inspect artifact text for {path}: {exc}")
            artifact_results.append(result)
            continue

        for value in expected_core_values(template):
            visible = value_is_visible(value, artifact_text)
            result["checked_values"].append({"value": value, "visible": visible})
            if not visible:
                result["passed"] = False
                findings.append(f"Artifact {path} does not contain expected value: {value}")
        artifact_results.append(result)

    if unused_paths:
        artifact_results.extend({"path": str(path), "passed": True, "note": "extra artifact not required by packet"} for path in unused_paths)

    return {
        "passed": not findings,
        "submission_ready": not findings and not unresolved_required_fields and not unresolved_manual_steps,
        "findings": findings,
        "warnings": warnings,
        "unresolved_required_fields": unresolved_required_fields,
        "unresolved_manual_steps": unresolved_manual_steps,
        "artifact_results": artifact_results,
        "user_notice": (
            "파일 생성 QA는 통과했지만 제출 전 사용자가 직접 처리해야 하는 조건이 남아 있습니다."
            if not findings and (unresolved_required_fields or unresolved_manual_steps)
            else ""
        ),
        "note": "This checks generated files exist, have the expected extension, and include core filled values; it does not replace render/visual QA.",
    }


def load_rules() -> dict[str, Any]:
    return json.loads((document_root() / "rules.json").read_text(encoding="utf-8"))


def support_items() -> list[dict[str, Any]]:
    return load_rules().get("support_items", [])


def item_by_category(category: str) -> dict[str, Any] | None:
    needle = normalize(category)
    alias_id = next((item_id for alias, item_id in CATEGORY_NAME_ALIASES.items() if normalize(alias) == needle), None)
    if alias_id:
        needle = normalize(alias_id)
    for item in support_items():
        values = [item.get("id", ""), item.get("name_ko", "")]
        if any(normalize(v) == needle for v in values):
            return item
    for item in support_items():
        if needle in normalize(item.get("name_ko", "")) or needle in normalize(item.get("id", "")):
            return item
    return None


def markdown_files() -> list[Path]:
    root = document_root()
    files = []
    for name in DOC_PRIORITY:
        path = root / name
        if path.exists() and path.suffix in {".md", ".json"}:
            files.append(path)
    for path in sorted(root.glob("*.md")):
        if path not in files:
            files.append(path)
    return files


def tokenize(query: str) -> list[str]:
    raw = re.split(r"[^0-9A-Za-z가-힣·]+", normalize(query))
    return [term for term in raw if len(term) >= 2]


def conflict_terms(text: str) -> list[str]:
    return [term for term in tokenize(text) if term not in CONFLICT_STOP_TERMS]


def snippet_from_lines(lines: list[str], index: int, radius: int = 2) -> str:
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)
    return "\n".join(line.rstrip() for line in lines[start:end]).strip()


def search_policy(query: str, category: str | None = None, limit: int = 8) -> dict[str, Any]:
    terms = tokenize(" ".join([query or "", category or ""]))
    category_item = item_by_category(category or "") if category else None
    if category_item:
        terms.extend(tokenize(category_item.get("name_ko", "")))
    terms = list(dict.fromkeys(terms))

    results = []
    for path in markdown_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(lines):
            hay = normalize(line)
            score = sum(1 for term in terms if term in hay)
            if score <= 0:
                continue
            results.append(
                {
                    "source": path.name,
                    "line_start": idx + 1,
                    "score": score,
                    "snippet": snippet_from_lines(lines, idx),
                }
            )

    results.sort(key=lambda item: (-item["score"], DOC_PRIORITY.index(item["source"]) if item["source"] in DOC_PRIORITY else 99, item["line_start"]))
    return {
        "query": query,
        "category": category,
        "terms": terms,
        "results": results[:limit],
    }


def evidence_from_rule_item(item: dict[str, Any], question: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    supporting = []
    conflicting = []
    question_norm = normalize(question)

    for field_name in ["scope", "application", "evidence", "limits", "qualification_requirements", "settlement"]:
        value = item.get(field_name)
        if value:
            supporting.append(
                {
                    "source": "rules.json",
                    "field": f"{item.get('id')}.{field_name}",
                    "text": flatten_text(value)[:900],
                }
            )

    for text in item.get("not_supported", []):
        text_norm = normalize(text)
        matched = any(term in question_norm for term in conflict_terms(text_norm))
        if matched:
            conflicting.append(
                {
                    "source": "rules.json",
                    "field": f"{item.get('id')}.not_supported",
                    "text": text,
                }
            )

    for hint in AMBIGUITY_HINTS.get(item.get("id", ""), []):
        if hint in question_norm and not any(hint in normalize(entry["text"]) for entry in conflicting):
            related_exclusion = ""
            if item.get("id") == "material_purchase":
                related_exclusion = "Related exclusion to check: 컴퓨터 및 부속품 / 노트북 등."
            elif item.get("id") == "expert_utilization_fee":
                related_exclusion = "Related exclusion to check: 개발 외주 및 개발 관련 전문가 자문."
            conflicting.append(
                {
                    "source": "rules.json",
                    "field": f"{item.get('id')}.ambiguity_hint",
                    "text": f"Question contains ambiguous wording that may require checking exclusions: {hint}. {related_exclusion}".strip(),
                }
            )

    return supporting[:5], conflicting[:5]


def classify_expense_item(question: str, max_candidates: int = 3) -> dict[str, Any]:
    q = normalize(question)
    candidates = []
    for item in support_items():
        item_id = item.get("id", "")
        haystack = normalize(" ".join([item.get("name_ko", ""), flatten_text(item), " ".join(CATEGORY_ALIASES.get(item_id, []))]))
        score = 0
        matched_terms = []
        for term in tokenize(q):
            if term in CLASSIFY_STOP_TERMS:
                continue
            if term in haystack:
                score += 2
                matched_terms.append(term)
        for alias in CATEGORY_ALIASES.get(item_id, []):
            if normalize(alias) in q:
                score += 5
                matched_terms.append(alias)
        if score == 0:
            continue
        supporting, conflicting = evidence_from_rule_item(item, question)
        category_search = search_policy(question, item.get("name_ko"), limit=3)
        supporting.extend(category_search["results"][:2])
        candidates.append(
            {
                "category_id": item_id,
                "category_name": item.get("name_ko"),
                "score": score,
                "matched_terms": sorted(set(matched_terms)),
                "supporting_evidence": supporting[:5],
                "conflicting_evidence": conflicting,
                "final_decision_allowed": bool(supporting) and not conflicting,
                "decision_note": "Candidate only. Final answer must cite evidence and handle conflicts.",
            }
        )

    candidates.sort(key=lambda item: (-item["score"], item["category_name"]))
    top = candidates[:max_candidates]
    return {
        "question": question,
        "candidates": top,
        "overall_note": "Keywords produced candidates only. Documents and evidence decide truth.",
    }


def source_step(text: str, source: str = "04-board-support-items.md") -> dict[str, Any]:
    return {"text": text, "source": source}


def writing_field(
    field: str,
    status: str,
    draft: str | int | None = None,
    options: list[str] | None = None,
    note: str | None = None,
    source: str = "rules.json",
) -> dict[str, Any]:
    entry: dict[str, Any] = {"field": field, "status": status, "source": source}
    if draft is not None:
        entry["draft"] = draft
    if options:
        entry["options"] = options
    if note:
        entry["note"] = note
    return entry


def infer_subject(question: str, item: dict[str, Any]) -> str:
    item_id = item.get("id", "")
    if item_id == "cloud_service_fee":
        return "AWS"
    if contains_any(question, ["디자인", "ui", "ux"]):
        return "디자인"
    if contains_any(question, ["번역"]):
        return "번역"
    if contains_any(question, ["퍼블리싱"]):
        return "퍼블리싱"

    cleaned = re.sub(
        r"(사려고|구매하려고|구매|사용하려고|사용하러|사용|신청하려고|신청|외주주려고|외주|하려는데|하려고|뭐해야함|뭐해야|뭐 해야|가능|지원|함|해|요|입니다)",
        " ",
        question,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?.!.,")
    return cleaned or item.get("name_ko", "해당 품목")


def date_placeholder(title: str) -> str:
    return title.replace("(6/10)", "(신청일)")


def particle_for(subject: str, consonant_form: str, vowel_form: str) -> str:
    stripped = re.sub(r"[^0-9A-Za-z가-힣]", "", subject or "")
    if not stripped:
        return vowel_form
    last = stripped[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return consonant_form if (code - 0xAC00) % 28 else vowel_form
    return consonant_form if last.isdigit() and last in "013678" else vowel_form


def choose_title_option(question: str, item: dict[str, Any], options: list[str]) -> tuple[str | None, bool]:
    item_id = item.get("id", "")
    if item_id == "material_purchase":
        if contains_any(question, ["구매대행", "대행"]):
            return date_placeholder("재료 구매대행(6/10)"), False
        if contains_any(question, ["일반구매", "일반 구매", "디바이스마트"]):
            return date_placeholder("재료 일반구매(6/10)"), False
        return None, True
    if item_id == "expert_utilization_fee":
        if contains_any(question, ["디자인"]):
            return date_placeholder("디자인 제작비(6/10)"), False
        if contains_any(question, ["전문가", "자문", "번역", "퍼블리싱"]):
            return date_placeholder("전문가 활용비(6/10)"), False
        return None, True
    return None, True


def draft_details(question: str, item: dict[str, Any], subject: str) -> tuple[str, str]:
    item_id = item.get("id", "")
    if item_id == "material_purchase":
        return (
            f"{subject}의 디바이스마트 사이트상 정확한 모델명/규격을 기재",
            "문서상 세부사항은 사이트에 명시된 구체 모델명이어야 하므로 최종 모델명 확인 필요",
        )
    if item_id == "equipment_rental":
        return (
            f"{subject} 임대 품목, 임대 기간, 결제 사이트 또는 업체명을 기재",
            "임대 품목과 기간은 실제 견적/사이트 화면 기준으로 확정 필요",
        )
    if item_id == "ai_sw_service_fee":
        return (
            f"{subject} 서비스명, 요금제, 1개월 이용 범위 기재",
            "월 단위 구독 또는 선불 충전 방식인지 확인 필요",
        )
    if item_id == "expert_utilization_fee":
        if contains_any(question, ["디자인"]):
            return (
                "프로젝트 화면/브랜딩/UI 디자인 등 의뢰 범위를 구체적으로 기재",
                "정확한 산출물 범위와 작업 기간은 전문가와 협의 후 보완",
            )
        return (
            f"{subject} 관련 자문/작업 범위를 구체적으로 기재",
            "정확한 산출물 범위와 작업 기간은 전문가와 협의 후 보완",
        )
    if item_id == "marketing_fee":
        return (
            f"{subject} 집행 채널, 광고/홍보 기간, 예상 결과물을 기재",
            "광고 결과 자료와 집행 내역을 증빙으로 제출할 수 있어야 함",
        )
    return (
        f"{subject} 사용 목적, 구매처 또는 이용처, 활용 내역을 기재",
        "문서에 고정값이 없으므로 실제 구매/이용 조건 확인 필요",
    )


def draft_purchase_reason(question: str, item: dict[str, Any], subject: str) -> str:
    item_id = item.get("id", "")
    if item_id == "cloud_service_fee":
        return "팀 프로젝트의 서버 운영, 데이터 처리, 배포 환경 구성 등 클라우드 인프라 사용을 위해 AWS 이용이 필요합니다."
    if item_id == "material_purchase":
        return f"팀 프로젝트의 시제품 제작 또는 기능 검증 과정에서 {subject}{particle_for(subject, '이', '가')} 필요하여 구매를 신청합니다."
    if item_id == "equipment_rental":
        return f"팀 프로젝트 구현과 테스트 과정에서 {subject} 장비{particle_for(subject + '장비', '가', '가')} 필요하여 정해진 기간 동안 임대를 신청합니다."
    if item_id == "ai_sw_service_fee":
        return f"팀 프로젝트 개발과 검증에 필요한 {subject} 서비스를 1개월 단위로 사용하기 위해 신청합니다."
    if item_id == "expert_utilization_fee":
        if contains_any(question, ["디자인"]):
            return "팀 프로젝트의 사용성, 화면 완성도, 결과물 품질 개선을 위해 외부 디자인 전문가의 작업이 필요하여 신청합니다."
        return f"팀 프로젝트 수행 중 팀 내부 역량만으로 해결하기 어려운 {subject} 분야의 전문 작업 또는 자문이 필요하여 신청합니다."
    if item_id == "marketing_fee":
        return f"팀 프로젝트 결과물의 사용자 반응 확인과 홍보 성과 측정을 위해 {subject} 집행이 필요하여 신청합니다."
    return f"팀 프로젝트 수행에 필요한 {subject} 이용을 위해 신청합니다."


def build_application_method(item: dict[str, Any]) -> list[dict[str, Any]]:
    item_id = item.get("id", "")
    common_path = "[마이페이지] → [신청/접수] → [프로젝트 활동비] → [글쓰기]"
    if item_id == "cloud_service_fee":
        return [
            source_step("[클라우드 서비스 사용 동의서] 양식을 다운로드합니다."),
            source_step("양식 내용을 검토한 뒤 자필 또는 전자 서명합니다. 이름 타이핑은 인정되지 않습니다."),
            source_step(common_path),
            source_step("클라우드 서비스 이용료 신청 가이드라인대로 글쓰기 항목을 작성하고 사용 동의서 서명본을 첨부합니다."),
            source_step("승인 완료 후 AWS 클라우드 서비스를 사용합니다. 승인 전 사용은 개인 과금 위험이 있습니다."),
        ]
    if item_id == "material_purchase":
        return [
            source_step(common_path),
            source_step("재료 구매비 사용 신청서를 작성합니다."),
            source_step("구매대행인 경우 [구매대행 신청서] 엑셀 파일을 첨부합니다."),
            source_step("사무국 승인 후 디바이스마트에서 구매 주문합니다. 승인 전 주문은 취소될 수 있습니다."),
        ]
    if item_id == "expert_utilization_fee":
        return [
            source_step(common_path),
            source_step("전문가 활용비 또는 디자인 제작비 사용 신청서를 작성합니다."),
            source_step("전문가 경력 3년 이상을 증명할 이력서, 포트폴리오 등을 첨부합니다."),
            source_step("신청서 승인 후 전문가 작업을 시작합니다. 승인 전 작업 정황이 있으면 지원 불가입니다."),
        ]
    return [
        source_step(common_path),
        source_step(f"{item.get('name_ko')} 사용 신청서를 작성합니다."),
        source_step("구매 사이트 결제 금액 화면 캡쳐 등 항목별 필수 첨부자료를 함께 제출합니다."),
        source_step("사무국 승인 후 결제, 사용, 작업을 진행합니다."),
    ]


def build_writing_format(question: str, item: dict[str, Any]) -> dict[str, Any]:
    application = item.get("application", {})
    item_id = item.get("id", "")
    subject = infer_subject(question, item)
    fields = [writing_field("구분", "fixed", "프로젝트 활동비", note="문서상 고정 선택값")]

    if application.get("title"):
        fields.append(writing_field("제목", "fixed", application["title"]))
    elif application.get("title_example"):
        fields.append(writing_field("제목", "fixed_template", date_placeholder(application["title_example"])))
    elif application.get("title_examples"):
        options = [date_placeholder(option) for option in application["title_examples"]]
        draft, needs_choice = choose_title_option(question, item, options)
        if needs_choice:
            fields.append(
                writing_field(
                    "제목",
                    "choice_required",
                    options=options,
                    note="일반/대행 또는 전문가/디자인 중 실제 신청 성격을 골라야 함",
                )
            )
        else:
            fields.append(writing_field("제목", "draft", draft, options=options, note="질문 내용으로 초안 선택"))

    if application.get("detail_category"):
        fields.append(writing_field("상세구분", "fixed", application["detail_category"]))
    elif application.get("detail_category_options"):
        options = application["detail_category_options"]
        draft = "디자인 제작비" if item_id == "expert_utilization_fee" and contains_any(question, ["디자인"]) else None
        if draft:
            fields.append(writing_field("상세구분", "draft", draft, options=options, note="질문 내용으로 초안 선택"))
        else:
            fields.append(writing_field("상세구분", "choice_required", options=options))

    if application.get("item_name"):
        fields.append(writing_field("품목명", "fixed", application["item_name"]))
    else:
        fields.append(writing_field("품목명", "draft", subject, note="질문에서 추출한 초안. 실제 품목명으로 확인"))

    if application.get("payment_method_text"):
        fields.append(writing_field("결제방식", "fixed", application["payment_method_text"]))
    elif application.get("payment_method_text_options"):
        fields.append(
            writing_field(
                "결제방식",
                "choice_required",
                options=application["payment_method_text_options"],
                note="실제 결제/지급 방식에 맞게 하나 선택",
            )
        )

    if application.get("details_text"):
        fields.append(writing_field("세부사항", "fixed", application["details_text"]))
    else:
        details, note = draft_details(question, item, subject)
        fields.append(writing_field("세부사항", "draft_needs_confirmation", details, note=note))

    if application.get("quantity"):
        fields.append(writing_field("수량", "fixed", application["quantity"]))
    else:
        fields.append(writing_field("수량", "user_input_required", note="실제 수량 입력"))

    if "amount_krw" in application:
        fields.append(writing_field("금액", "fixed", str(application["amount_krw"])))
    else:
        note = application.get("amount_rule") or "실제 결제/견적 금액 입력"
        if item_id == "material_purchase":
            note = f"{note}; 구매대행이면 최초 0원 작성 후 사무국 견적 확인 뒤 수정"
        fields.append(writing_field("금액", "user_input_required", note=note))

    if application.get("foreign_currency_rule") or item_id == "expert_utilization_fee":
        fields.append(
            writing_field(
                "달러",
                "conditional",
                note=application.get("foreign_currency_rule") or "해외 화폐 결제 시 달러 금액 작성",
            )
        )

    fields.append(
        writing_field(
            "구매사유",
            "draft",
            draft_purchase_reason(question, item, subject),
            note="문서상 최소 30자(공백 미포함) 이상, 프로젝트 관련성이 드러나야 함",
        )
    )

    attachment = application.get("form") or application.get("attachment_required") or application.get("initial_attachment")
    if item_id == "material_purchase":
        fields.append(
            writing_field(
                "첨부파일",
                "conditional",
                application.get("attachment_required_when_proxy_purchase"),
                note="구매대행인 경우 필수. 일반구매는 문서상 별도 신청서 첨부 조건 없음",
            )
        )
    elif attachment:
        fields.append(writing_field("첨부파일", "fixed_or_required", attachment))
    else:
        fields.append(writing_field("첨부파일", "conditional", note="항목 및 결제방식별 증빙자료 확인 필요"))

    choices_needed = [
        {"field": field["field"], "options": field.get("options", []), "note": field.get("note")}
        for field in fields
        if field["status"] == "choice_required"
    ]
    inputs_needed = [
        {"field": field["field"], "note": field.get("note")}
        for field in fields
        if field["status"] in {"user_input_required", "draft_needs_confirmation"}
    ]
    return {
        "fields": fields,
        "user_choices_needed": choices_needed,
        "user_inputs_needed": inputs_needed,
    }


def build_cautions(question: str, item: dict[str, Any]) -> list[dict[str, Any]]:
    cautions = [
        {"text": "활용계획서 승인 전 사용 신청, 사무국 승인 전 결제/작업/사용은 반려 사유입니다.", "source": "rules.json"},
        {"text": "구매사유는 프로젝트 관련성이 확인되도록 공백 제외 최소 30자 이상 작성해야 합니다.", "source": "rules.json"},
    ]
    application = item.get("application", {})
    if application.get("signature_rule"):
        cautions.append({"text": application["signature_rule"], "source": "rules.json"})
    for warning in item.get("warnings", []):
        cautions.append({"text": warning, "source": "rules.json"})
    for note in item.get("special_notes", []):
        cautions.append({"text": note, "source": "rules.json"})
    for requirement in item.get("qualification_requirements", []):
        cautions.append({"text": requirement, "source": "rules.json"})
    _, conflicting = evidence_from_rule_item(item, question)
    for conflict in conflicting:
        cautions.append(
            {
                "text": f"확인 필요: {conflict.get('text')}",
                "source": conflict.get("source", "rules.json"),
                "field": conflict.get("field"),
            }
        )
    return cautions


def draft_application_form(question: str, category: str | None = None) -> dict[str, Any]:
    classification = classify_expense_item(question, max_candidates=3)
    item = item_by_category(category or "") if category else None
    if not item and classification["candidates"]:
        item = item_by_category(classification["candidates"][0]["category_id"])
    if not item:
        return {
            "found": False,
            "question": question,
            "category": category,
            "classification_summary": classification,
            "error": "No support category could be selected from local document evidence.",
        }

    writing = build_writing_format(question, item)
    return {
        "found": True,
        "question": question,
        "category_id": item.get("id"),
        "category_name": item.get("name_ko"),
        "application_method": build_application_method(item),
        "writing_format": writing["fields"],
        "user_choices_needed": writing["user_choices_needed"],
        "user_inputs_needed": writing["user_inputs_needed"],
        "cautions": build_cautions(question, item),
        "sources": sorted(set(["rules.json", "04-board-support-items.md", *item.get("sources", [])])),
        "classification_summary": classification,
        "note": "Use drafted fields for the answer. Present choice_required fields as options, and write non-choice draft fields directly.",
    }


def get_required_documents(category: str) -> dict[str, Any]:
    item = item_by_category(category)
    if not item:
        return {"category": category, "found": False, "error": "Unknown category"}
    payment_methods = load_rules().get("payment_methods", [])
    allowed = set(item.get("allowed_payment_method_ids", []))
    methods = [method for method in payment_methods if method.get("id") in allowed]
    writing = build_writing_format("", item)
    return {
        "found": True,
        "category_id": item.get("id"),
        "category_name": item.get("name_ko"),
        "scope": item.get("scope", []),
        "application": item.get("application", {}),
        "application_method": build_application_method(item),
        "writing_format": writing["fields"],
        "user_choices_needed": writing["user_choices_needed"],
        "user_inputs_needed": writing["user_inputs_needed"],
        "evidence": item.get("evidence", {}),
        "limits": item.get("limits", {}),
        "qualification_requirements": item.get("qualification_requirements", []),
        "payment_methods": methods,
        "warnings": item.get("warnings", []),
        "cautions": build_cautions("", item),
        "not_supported": item.get("not_supported", []),
        "sources": item.get("sources", []),
    }


def contains_any(text: str, terms: list[str]) -> bool:
    norm = normalize(text)
    return any(normalize(term) in norm for term in terms)


def validate_policy_answer(question: str, answer: str) -> dict[str, Any]:
    findings = []
    q = normalize(question)
    a = normalize(answer)

    if not contains_any(answer, ["가능", "불가", "조건부 가능", "문서상 확인 불가"]):
        findings.append("Missing explicit decision label.")
    if not contains_any(answer, ["근거", ".md", "rules.json", "document/"]):
        findings.append("Missing source filename or evidence section.")
    if "가능" in a and not contains_any(answer, [".md", "rules.json", "document/"]):
        findings.append("Unsupported certainty: answer says possible without source file.")

    classification = classify_expense_item(question, max_candidates=2)
    has_policy_candidate = bool(classification["candidates"])
    if has_policy_candidate:
        for section, terms in {
            "신청방법": ["신청방법", "신청 방법"],
            "글쓰기 포맷": ["글쓰기 포맷", "글쓰기", "작성 포맷"],
            "유의사항": ["유의사항", "주의사항"],
        }.items():
            if not contains_any(answer, terms):
                findings.append(f"Support-item answer missing section: {section}")
        for field in ["구분", "제목", "상세구분", "품목명", "결제방식", "구매사유", "첨부파일"]:
            if not contains_any(answer, [field]):
                findings.append(f"Writing format missing field: {field}")

        form = draft_application_form(question)
        if form.get("user_choices_needed") and not contains_any(answer, ["선택", "확정", "옵션", "중 하나"]):
            findings.append("Writing format has choice-required fields but answer does not present choices.")

    ambiguous = any(candidate.get("conflicting_evidence") for candidate in classification["candidates"])
    if ambiguous and "가능" in a and not contains_any(answer, ["조건부", "확인", "애매", "사무국", "문서상"]):
        findings.append("Ambiguous item answered as simply possible without handling conflicting evidence.")

    if contains_any(question, ["aws", "클라우드"]):
        required = {
            "클라우드 서비스 사용 동의서": ["클라우드 서비스 사용 동의서"],
            "승인 후 사용": ["승인", "사용"],
            "통합 빌링": ["통합 빌링", "통합빌링"],
            "개인 과금 warning": ["개인 과금", "지원되지"],
        }
        for label, terms in required.items():
            if not contains_any(answer, terms):
                findings.append(f"AWS answer missing: {label}")

    if contains_any(question, ["허브", "도킹", "독", "맥북"]):
        required = {
            "재료 구매비 candidate": ["재료 구매비"],
            "허브 evidence": ["허브"],
            "DeviceMart": ["디바이스마트"],
            "amount/limit": ["200,000", "20만원", "200000"],
            "computer accessory ambiguity": ["컴퓨터", "부속", "노트북", "사무국", "확인"],
        }
        for label, terms in required.items():
            if not contains_any(answer, terms):
                findings.append(f"Hub/dock answer missing: {label}")

    if contains_any(question, ["디자인", "외주", "전문가"]):
        required = {
            "design/expert category": ["디자인 제작비", "전문가 활용비"],
            "career requirement": ["3년", "경력"],
            "amount cap": ["500만원", "500"],
            "approval before work": ["승인 전", "작업"],
            "development outsourcing exclusion": ["개발", "외주", "지원 불가"],
        }
        for label, terms in required.items():
            if not contains_any(answer, terms):
                findings.append(f"Design/expert answer missing: {label}")

    return {
        "passed": not findings,
        "findings": findings,
        "classification_summary": classification,
        "note": "Validation checks evidence linkage and known risk omissions; it does not replace document review.",
    }


