import json
import re

import streamlit as st
from google import genai
from google.genai import types


MODEL_NAME = "gemini-2.5-flash"


# Gemini 연결 실패 시 사용할 최소 오타 교정 규칙
FALLBACK_FIX = {
    "외관상태양호": "외관 상태 양호",
    "이상없슴": "이상 없음",
    "이상업음": "이상 없음",
    "기준미달": "기준 미달",

    "도막두게": "도막두께",
    "도막두깨": "도막두께",
    "도막 두게": "도막두께",

    "스팩": "스펙",
    "스팩미달": "스펙 미달",
    "스팩민달": "스펙 미달",
    "스펙민달": "스펙 미달",
    "민달": "미달",

    "제도장": "재도장",
    "제도쟝": "재도장",
    "재도쟝": "재도장",
    "제도쟝필요": "재도장 필요",
    "재도장필요": "재도장 필요",

    "압력시헝": "압력시험",
    "합격햇": "합격했",
    "문재": "문제",
    "업음": "없음",
    "업슴": "없음",
    "누설업음": "누설 없음",

    "후렌지": "플랜지",
    "치수이상없음": "치수 이상 없음",
    "외관이상없음": "외관 이상 없음",
    "변형없음": "변형 없음",
    "부식없음": "부식 없음",

    "재검사필요": "재검사 필요",
    "재검사실시": "재검사 실시",
    "재작업필요": "재작업 필요",
    "사진참조": "사진 참조",
    "도면참조": "도면 참조",
}


def fallback_clean(text):
    """
    Gemini를 사용할 수 없을 때 적용하는 기본 교정입니다.
    """
    text = (text or "").strip()

    for wrong, correct in FALLBACK_FIX.items():
        text = text.replace(wrong, correct)

    # 측정값 3개가 공백으로 입력되면 쉼표로 정리
    # 예: 256 267 258 → 256, 267, 258
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(\d+(?:\.\d+)?)",
        r"\1, \2, \3",
        text,
    )

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def fallback_draft(
    inspection_types,
    specification,
    inspection_content,
    judgment,
    photo_count,
):
    """
    Gemini 호출 실패 시 기존 방식으로 검사결과와 조치요구를 작성합니다.
    """
    title = " / ".join(inspection_types)

    corrected_specification = fallback_clean(specification)
    corrected_content = fallback_clean(inspection_content)

    if judgment == "합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            f"적용 기준({corrected_specification})을 충족하여 "
            f"합격으로 판정함."
        )

        action = "별도 조치사항 없음."

    elif judgment == "불합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            f"적용 기준({corrected_specification})을 충족하지 못하여 "
            f"불합격으로 판정함."
        )

        action = (
            "부적합 내용을 확인하여 필요한 수정 또는 보수를 실시하고, "
            "동일 기준으로 재검사하여 결과를 확인할 것."
        )

    elif judgment == "조건부 합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            "보완조건 이행을 전제로 조건부 합격으로 판정함."
        )

        action = (
            "지정된 보완사항을 완료하고 객관적 증빙을 확인한 후 "
            "최종 승인할 것."
        )

    else:
        result = f"{title} 항목은 해당 없음(N/A)으로 처리함."
        action = "해당 없음."

    caption = (
        f"사진 1~{photo_count}: {title} 대상 및 검사 상태"
        if photo_count
        else ""
    )

    return (
        result,
        action,
        caption,
        corrected_specification,
        corrected_content,
    )


def make_draft(
    types_list,
    specification,
    inspection_content,
    judgment,
    photo_count,
):
    """
    Gemini를 이용해 다음 내용을 작성합니다.

    1. 검사기준 오타 교정
    2. 검사내용 오타 및 품질용어 교정
    3. 공식 검사결과 문장 작성
    4. 검사내용에 적합한 조치요구 작성
    5. 공통 사진 설명 작성
    """

    inspection_title = " / ".join(types_list)

    try:
        api_key = st.secrets["GEMINI_API_KEY"]

        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
당신은 플랜트 및 제작품의 품질검사 결과서 작성 보조 AI입니다.

현장 검사자가 휴대전화로 급하게 작성한 검사내용의
심한 오타, 맞춤법, 띄어쓰기 및 품질용어를 문맥으로 교정하고,
검사결과와 조치요구를 작성하세요.

[검사종류]
{inspection_title}

[검사기준]
{specification}

[검사자 원문]
{inspection_content}

[사용자 선택 최종판정]
{judgment}

다음 규칙을 반드시 지키세요.

1. 심한 오타도 검사종류와 문장 전체의 문맥을 참고하여 교정한다.

2. 검사자가 입력한 숫자, 수량, 재질, Grade, 도면번호,
   Tag No., 규격 및 측정값은 절대 임의로 변경하지 않는다.

3. 원문에 없는 숫자, 수량, 측정값, 압력, 온도, 시간,
   재질, 규격 또는 판정근거를 생성하지 않는다.

4. 원문에 단위가 없으면 단위를 임의로 추가하지 않는다.

5. 사용자가 선택한 최종판정을 임의로 변경하지 않는다.

6. 검사장소는 검사결과 문장에 작성하지 않는다.

7. 검사결과는 간결하고 전문적인 품질문서 문장으로 작성한다.

8. 조치요구는 검사종류, 검사기준, 검사내용,
   최종판정을 종합하여 작성한다.

9. 합격이면 조치요구는 반드시
   '별도 조치사항 없음.'
   으로 작성한다.

10. 불합격이면 검사내용에서 확인된 실제 문제에 맞는
    조치요구를 작성한다.

11. 도막두께 미달이면 기준 미달 부위 재도장 후
    도막두께 재측정을 요구한다.

12. 치수 초과 또는 미달이면 해당 부위 수정 또는
    재가공 후 치수 재검사를 요구한다.

13. 외관 손상이면 손상 부위 보수 후 외관 재검사를 요구한다.

14. 녹 또는 부식이면 녹과 부식을 제거하고
    표면상태를 재확인하도록 요구한다.

15. 압력시험 누설이면 누설 부위 보수 후
    동일 시험조건으로 재시험하도록 요구한다.

16. 재질 불일치이면 부적합 자재를 격리 또는 교체하고
    재질과 관련 성적서를 확인한 후 재검사하도록 요구한다.

17. 용접 외관 불량이면 불량부를 보수한 후
    외관 재검사를 요구한다.

18. 조치요구에 원문에서 확인되지 않은 작업방법,
    수치, 재질, 규격, 압력, 온도 및 시간을 만들지 않는다.

19. 검사내용만으로 구체적인 조치방법을 판단하기 어려우면
    임의로 추측하지 말고 다음과 같이 작성한다.
    '부적합 내용 확인 후 적절한 조치를 실시하고 재검사할 것.'

20. 조건부 합격이면 검사내용에 명시된 보완사항을 반영하여
    조치요구를 작성한다.

21. N/A이면 조치요구는
    '해당 없음.'
    으로 작성한다.

22. corrected_content에는 교정된 현장 검사내용만 작성한다.

23. result에는 공식 검사결과 문장만 작성한다.

24. action에는 조치요구 문장만 작성한다.

교정 예시 1:
원문:
도막두게 측정결과 256 267 258 스팩 민달 제도쟝필요

교정:
도막두께 측정 결과 256, 267, 258로 확인되었으며,
스펙 미달로 재도장이 필요함.

교정 예시 2:
원문:
압력시헝 합격햇으며 문재가 업음

교정:
압력시험 결과 특이사항이 확인되지 않았으며
적용 기준을 충족함.

교정 예시 3:
원문:
치수 측정결가 도면치수랑 일치하구
외관도 찍힘 변형 부식 업음 전체적으루 양호함

교정:
치수 측정 결과 도면 치수와 일치하며,
외관상 찍힘, 변형 및 부식이 없고 전체적으로 양호함.

JSON 형식으로만 답변하세요.
"""

        response_schema = {
            "type": "object",
            "properties": {
                "corrected_spec": {
                    "type": "string",
                },
                "corrected_content": {
                    "type": "string",
                },
                "result": {
                    "type": "string",
                },
                "action": {
                    "type": "string",
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
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=response_schema,
                temperature=0.2,
            ),
        )

        response_data = json.loads(
            response.text
        )

        corrected_specification = str(
            response_data.get(
                "corrected_spec",
                specification,
            )
        ).strip()

        corrected_content = str(
            response_data.get(
                "corrected_content",
                inspection_content,
            )
        ).strip()

        result = str(
            response_data.get(
                "result",
                "",
            )
        ).strip()

        action = str(
            response_data.get(
                "action",
                "",
            )
        ).strip()

        if not corrected_content:
            raise ValueError(
                "교정된 검사내용이 비어 있습니다."
            )

        if not result:
            raise ValueError(
                "검사결과 문장이 비어 있습니다."
            )

        if not action:
            raise ValueError(
                "조치요구 문장이 비어 있습니다."
            )

        photo_caption = (
            f"사진 1~{photo_count}: "
            f"{inspection_title} 대상 및 검사 상태"
            if photo_count
            else ""
        )

        return (
            result,
            action,
            photo_caption,
            corrected_specification,
            corrected_content,
        )

    except Exception:
        # API 오류, 무료 한도 초과, 통신 장애,
        # 응답형식 오류가 발생해도 웹앱이 중단되지 않도록
        # 기존 규칙 방식으로 자동 전환합니다.
        return fallback_draft(
            types_list,
            specification,
            inspection_content,
            judgment,
            photo_count,
        )
