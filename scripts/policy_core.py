"""Script-facing Cost SOMA policy helpers."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any


_ENGINE_PATH = Path(__file__).resolve().with_name("policy_engine.py")
_CWD_DOCUMENT_ROOT = Path.cwd() / "document"
_PLUGIN_DOCUMENT_ROOT = Path(__file__).resolve().parents[1] / "document"
os.environ.setdefault(
    "COST_SOMA_DOCUMENT_ROOT",
    str(_CWD_DOCUMENT_ROOT if (_CWD_DOCUMENT_ROOT / "rules.json").exists() else _PLUGIN_DOCUMENT_ROOT),
)
_SPEC = importlib.util.spec_from_file_location("_cost_soma_policy_engine", _ENGINE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy engine from {_ENGINE_PATH}")

_engine = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_engine)


load_rules = _engine.load_rules
support_items = _engine.support_items
item_by_category = _engine.item_by_category
markdown_files = _engine.markdown_files
search_policy = _engine.search_policy
evidence_from_rule_item = _engine.evidence_from_rule_item
classify_expense_item = _engine.classify_expense_item
draft_application_form = _engine.draft_application_form
get_required_documents = _engine.get_required_documents
contains_any = _engine.contains_any
list_policy_form_templates = _engine.list_policy_form_templates
prepare_policy_form_packet = _engine.prepare_policy_form_packet
validate_form_artifacts = _engine.validate_form_artifacts


REQUIRED_SECTIONS = ["결론", "신청방법", "글쓰기 포맷", "유의사항", "근거"]
GENERIC_POLICY_TERMS = [
    "soma",
    "sw마에스트로",
    "지원",
    "지원항목",
    "활동비",
    "신청방법",
    "글쓰기 포맷",
    "유의사항",
    "증빙",
    "구매",
    "외주",
    "aws",
    "허브",
    "독",
    "디자인",
]


def _item_for_category(category: str) -> dict[str, Any] | None:
    return item_by_category(category)


def build_application_method(category: str) -> list[dict[str, Any]]:
    item = _item_for_category(category)
    return _engine.build_application_method(item) if item else []


def build_writing_format(question: str, category: str) -> dict[str, Any]:
    item = _item_for_category(category)
    if not item:
        return {"fields": [], "user_choices_needed": [], "user_inputs_needed": []}
    return _engine.build_writing_format(question, item)


def build_cautions(question: str, category: str) -> list[dict[str, Any]]:
    item = _item_for_category(category)
    return _engine.build_cautions(question, item) if item else []


def render_writing_format_text(question: str, category: str, writing_format: list[dict[str, Any]] | None = None) -> str:
    """Return a final-answer-ready writing format template."""
    item = _item_for_category(category)
    item_id = item.get("id", "") if item else category

    if item_id == "material_purchase":
        return "\n".join(
            [
                "- 구분 : [프로젝트 활동비] 선택",
                "- 제목 : \"**재료 일반구매(신청일)**\" 또는 \"**재료 구매대행(신청일)**\" 작성",
                "           (ex. 재료 일반구매(6/10) 또는 재료 구매대행(6/10))",
                "- 상세구분 : [재료 구매비] 선택",
                "- 품목명 : 구매 희망 품목명 작성(ex. 벨킨 허브)",
                "- 결제방식 : \"**디바이스마트**\" 작성",
                "- 세부사항 : 디바이스마트 사이트에 명시된 품목의 구체적인 모델명 작성",
                "  (ex. [Belkin] 벨킨 INC009b (USB허브/7포트/멀티허브) ▶ [무전원/C타입] ◀)",
                "- 수량 : 수량 작성",
                "- 금액 : 금액 작성",
                "    - 개별 단가가 아닌 **총액**으로 작성",
                "    - 디바이스마트에서 확인한 부가세 10% 포함 금액으로 작성",
                "      (활동비에서도 부가세 10% 포함 금액 기준으로 차감)",
                "    - ***(구매대행인 경우***) \"**0**\" 으로 작성해두고, 추후 사무국에서 전달하는 견적 확인 후 금액을 수정",
                "- 구매사유 : 해당 항목이 프로젝트에 필요한 사유 작성",
                "    - 회계사, 담당 멘토, 사무국 담당자가 팀 프로젝트와의 관련성을 파악할 수 있도록 작성",
                "    - 최소 30자(공백 미포함) 이상 작성",
                "- 첨부파일 : ***(구매대행인 경우)*** 아래의 [구매대행 신청서] 파일 첨부",
            ]
        )

    if writing_format is None:
        writing_format = build_writing_format(question, category).get("fields", [])

    lines: list[str] = []
    for field in writing_format:
        name = field.get("field", "")
        status = field.get("status", "")
        draft = field.get("draft")
        options = field.get("options") or []
        note = field.get("note")

        if options and status == "choice_required":
            lines.append(f"- {name} : " + " 또는 ".join(f"\"**{option}**\"" for option in options) + " 중 선택")
        elif draft:
            lines.append(f"- {name} : {draft}")
        elif note:
            lines.append(f"- {name} : {note}")
        else:
            lines.append(f"- {name} : 작성")

        if note and draft:
            lines.append(f"    - {note}")

    return "\n".join(lines)


def docs_for_category(category: str) -> dict[str, Any]:
    """Return policy document helpers for a support category."""
    writing = build_writing_format("", category)
    return {
        "category": category,
        "required_documents": get_required_documents(category),
        "application_method": build_application_method(category),
        "writing_format": writing,
        "writing_format_text": render_writing_format_text("", category, writing.get("fields", [])),
        "cautions": build_cautions("", category),
    }


def form_for_question(question: str, category: str | None = None) -> dict[str, Any]:
    """Return the application-method bundle for a question/category."""
    if category is None:
        classification = classify_expense_item(question)
        candidates = classification.get("candidates", [])
        category = candidates[0].get("category_id") if candidates else ""
    else:
        classification = classify_expense_item(question)

    if not category:
        return {
            "question": question,
            "classification": classification,
            "category": "",
            "application_method": "",
            "writing_format": "",
            "cautions": [],
            "draft": {},
            "required_documents": [],
        }

    draft = draft_application_form(question, category)
    return {
        "question": question,
        "classification": classification,
        "category": category,
        "category_id": draft.get("category_id"),
        "category_name": draft.get("category_name"),
        "application_method": draft.get("application_method", []),
        "writing_format": draft.get("writing_format", []),
        "writing_format_text": render_writing_format_text(question, category, draft.get("writing_format", [])),
        "user_choices_needed": draft.get("user_choices_needed", []),
        "user_inputs_needed": draft.get("user_inputs_needed", []),
        "cautions": draft.get("cautions", []),
        "draft": draft,
        "required_documents": get_required_documents(category),
    }


def validate_policy_answer(question: str, answer: str) -> dict[str, Any]:
    """Validate a Cost SOMA answer with generic and category-specific checks."""
    payload = _engine.validate_policy_answer(question, answer)
    findings = list(payload.get("findings", []))
    classification = payload.get("classification_summary") or classify_expense_item(question)
    candidates = classification.get("candidates", [])

    lower_answer = answer.lower()
    should_have_policy_shape = bool(candidates) or contains_any(answer, GENERIC_POLICY_TERMS)

    if should_have_policy_shape:
        for section in REQUIRED_SECTIONS:
            if section not in answer:
                finding = f"Missing required section: {section}"
                if finding not in findings:
                    findings.append(finding)

        for phrase in ["신청방법", "글쓰기 포맷", "유의사항"]:
            if phrase not in answer:
                finding = f"Missing support-item field: {phrase}"
                if finding not in findings:
                    findings.append(finding)

    category_names = {
        candidate.get("category", "") or candidate.get("category_name", "") or candidate.get("category_id", "")
        for candidate in candidates
    }
    question_has_design = contains_any(question, ["디자인", "외주", "로고", "ui", "ux"])
    answer_has_design = contains_any(answer, ["디자인 제작비", "디자인", "외주"])
    if question_has_design or "디자인 제작비" in category_names or answer_has_design:
        for phrase in ["3년", "승인", "개발 외주"]:
            if phrase not in answer:
                finding = f"Design outsourcing answer should mention: {phrase}"
                if finding not in findings:
                    findings.append(finding)

    question_has_aws = contains_any(question, ["aws", "클라우드", "서버"])
    answer_has_aws = "aws" in lower_answer or "클라우드" in answer
    if question_has_aws or "클라우드 서버 이용료" in category_names or answer_has_aws:
        for phrase in ["환율", "실사용", "콘솔"]:
            if phrase not in answer:
                finding = f"Cloud server answer should mention: {phrase}"
                if finding not in findings:
                    findings.append(finding)

    question_has_hub = contains_any(question, ["허브", "독", "dock", "hub"])
    answer_has_hub = contains_any(answer, ["PC 소모품 구입비", "허브", "독"])
    if question_has_hub or "PC 소모품 구입비" in category_names or answer_has_hub:
        for phrase in ["장비 목록", "노트북"]:
            if phrase not in answer:
                finding = f"Hub/dock answer should mention: {phrase}"
                if finding not in findings:
                    findings.append(finding)

    question_has_material = contains_any(question, ["아두이노", "허브", "재료", "디바이스마트", "구매대행"])
    answer_has_material = contains_any(answer, ["재료 구매비", "디바이스마트", "구매대행 신청서"])
    if question_has_material or "재료 구매비" in category_names or answer_has_material:
        material_requirements = {
            "material title options": ["재료 일반구매", "재료 구매대행"],
            "material detail category": ["상세구분", "재료 구매비"],
            "material VAT total amount rule": ["총액", "부가세", "10%"],
            "material proxy amount rule": ["구매대행", "0"],
            "material attachment rule": ["첨부파일", "구매대행 신청서"],
        }
        for label, phrases in material_requirements.items():
            if not all(phrase in answer for phrase in phrases):
                finding = f"Material purchase writing format missing: {label}"
                if finding not in findings:
                    findings.append(finding)

    form_request = contains_any(
        question,
        ["양식 작성", "신청서 작성", "증빙문서 작성", "제출용", "파일 만들어", "문서 만들어", "docx", "xlsx"],
    )
    if form_request and not contains_any(
        answer,
        ["form_packet", "form-packet", "prepare_policy_form_packet", ".docx", ".xlsx", "outputs/cost-soma-forms", "누락", "입력 필요"],
    ):
        findings.append("Form-generation request should mention a form packet, generated artifact path, or missing required fields.")

    return {
        **payload,
        "passed": not findings,
        "findings": findings,
        "classification_summary": classification,
    }
