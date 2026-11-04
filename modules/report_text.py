import json
import re

import streamlit as st
from google import genai


MODEL = "gemini-2.5-flash"


# Gemini 장애 시 사용하는 최소 백업 교정
FIX = {
    "도막두게": "도막두께",
    "도막두깨": "도막두께",
    "스팩": "스펙",
    "민달": "미달",
    "제도쟝": "재도장",
    "재도쟝": "재도장",
    "합격햇": "합격했",
    "문재": "문제",
    "업음": "없음",
    "업슴": "없음",
    "누설업음": "누설 없음",
    "이상없슴": "이상 없음",
    "기준미달": "기준 미달",
    "사진참조": "사진 참조",
}


def fallback_clean(text):
    text = (text or "").strip()

    for wrong, correct in FIX.items():
        text = text.replace(wrong, correct)

    # 256 267 258 → 256, 267, 258
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(\d+(?:\.\d+)?)",
        r"\1, \2, \3",
        text,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def fallback_draft(types, spec, content, judgment, count):
    title = " / ".join(types)

    spec = fallback_clean(spec)
    content = fallback_clean(content)

    if judgment == "합격":
        result = (
            f"{title} 결과, {content}로 확인되었으며 "
            f"적용 기준({spec})을 충족하여 합격으로 판정함."
        )
        action = "별도 조치사항 없음."

    elif judgment == "불합격":
        result = (
            f"{title} 결과, {content}로 확인되었으며 "
            f"적용 기준({spec})을 충족하지 못하여 "
            f"불합격으로 판정함."
        )
        action = (
            "부적합 부위를 수정·보수한 후 "
            "동일 기준으로 재검사하고 결과를 확인할 것."
        )

    elif judgment == "조건부 합격":
        result = (
            f"{title} 결과, {content}로 확인되었으며 "
            "보완조건 이행을 전제로 조건부 합격으로 판정함."
        )
        action = (
            "지정된 보완사항을 완료하고 "
            "객관적 증빙을 확인한 후 최종 승인할 것."
        )

    else:
        result = f"{title} 항목은 해당 없음(N/A)으로 처리함."
        action = "해당 없음."

    caption = (
        f"사진 1~{count}: {title} 대상 및 검사 상태"
        if count
        else ""
    )

    return result, action, caption, spec, content


def make_draft(types, spec, content, judgment, count):

    title = " / ".join(types)

    try:
        api_key = st.secrets["GEMINI_API_KEY"]

        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
당신은 플랜트·제작 품질검사 보고서 작성 보조 AI입니다.

작업자가 현장에서 휴대폰으로 급하게 입력한 문장을
자연스러운 품질검사 문장으로 교정하세요.

[검사종류]
{title}

[검사기준]
{spec}

[작업자 원문]
{content}

[최종판정]
{judgment}

반드시 다음 규칙을 지키세요.

1. 맞춤법, 띄어쓰기, 심한 오타를 문맥으로 교정한다.
2. 품질검사 전문용어를 우선 사용한다.
3. 원문에 있는 숫자, 수량, 규격, 재질은 절대 변경하지 않는다.
4. 원문에 없는 숫자나 측정값을 만들지 않는다.
5. 원문에 없는 규격이나 Spec을 만들지 않는다.
6. 재질 Grade를 임의로 변경하지 않는다.
7. 사용자가 선택한 최종판정은 임의로 변경하지 않는다.
8. 검사장소는 검사결과 문장에 작성하지 않는다.
9. 의미가 불확실한 내용은 임의 추측하지 않는다.
10. 검사결과는 간결한 품질문서 문장으로 작성한다.
11. 불합격이면 합리적인 조치요구 문장을 작성한다.
12. 합격이면 조치요구는 '별도 조치사항 없음.'으로 한다.
13. 작업자가 입력한 표현이 거칠더라도 의미를 최대한 파악한다.

예시:
'도막두게 측정결과 256 267 258 스팩 민달 제도쟝필요'
→
'도막두께 측정 결과 256, 267, 258로 확인되었으며
스펙 미달로 재도장이 필요함.'

예시:
'압력시헝 합격햇으며 문재가 업음'
→
'압력시험 결과 특이사항이 확인되지 않았으며
적용 기준을 충족함.'

JSON 형식으로만 답변하세요.
"""

        schema = {
            "type": "object",
            "properties": {
                "corrected_spec": {
                    "type": "string"
                },
                "corrected_content": {
                    "type": "string"
                },
                "result": {
                    "type": "string"
                },
                "action": {
                    "type": "string"
                },
            },
            "required": [
                "corrected_spec",
                "corrected_content",
                "result",
                "action",
            ],
        }

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
                "temperature": 0.2,
            },
        )

        data = json.loads(response.text)

        corrected_spec = data[
            "corrected_spec"
        ].strip()

        corrected_content = data[
            "corrected_content"
        ].strip()

        result = data[
            "result"
        ].strip()

        action = data[
            "action"
        ].strip()

        caption = (
            f"사진 1~{count}: "
            f"{title} 대상 및 검사 상태"
            if count
            else ""
        )

        return (
            result,
            action,
            caption,
            corrected_spec,
            corrected_content,
        )

    except Exception:
        # Gemini 오류, 무료 한도 초과,
        # 통신 장애 시 기존 방식으로 자동 전환
        return fallback_draft(
            types,
            spec,
            content,
            judgment,
            count,
        )
