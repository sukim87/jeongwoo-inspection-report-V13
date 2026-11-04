import json
import re

import streamlit as st
from google import genai


MODEL_NAME = "gemini-3.8-flash"


# Gemini가 일시적으로 동작하지 않을 때 사용하는 최소 백업 교정
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
    text = (text or "").strip()

    for wrong, correct in FALLBACK_FIX.items():
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


def fallback_draft(
    inspection_types,
    specification,
    inspection_content,
    judgment,
    photo_count,
):
    title = " / ".join(inspection_types)

    corrected_spec = fallback_clean(specification)
    corrected_content = fallback_clean(inspection_content)

    if judgment == "합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            f"적용 기준({corrected_spec})을 충족하여 "
            f"합격으로 판정함."
        )
        action = "별도 조치사항 없음."

    elif judgment == "불합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            f"적용 기준({corrected_spec})을 충족하지 못하여 "
            f"불합격으로 판정함."
        )
        action = (
            "부적합 내용 확인 후 적절한 조치를 실시하고 "
            "재검사할 것."
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
        result = (
            f"{title} 항목은 해당 없음(N/A)으로 처리함."
        )
        action = "해당 없음."

    caption = (
        f"사진 1~{photo_count}: "
        f"{title} 대상 및 검사 상태"
        if photo_count
        else ""
    )

    return (
        result,
        action,
        caption,
        corrected_spec,
        corrected_content,
    )


def make_draft(
    types,
    spec,
    content,
    judgment,
    count,
):
    title = " / ".join(types)

    try:
        api_key = st.secrets["GEMINI_API_KEY"]

        client = genai.Client(api_key=api_key)

        prompt = f"""
당신은 플랜트 및 제작품 품질검사 결과서 작성 보조 AI입니다.

현장 검사자가 휴대전화로 급하게 작성한 검사내용에
맞춤법, 띄어쓰기, 심한 오타가 포함되어 있어도
검사 문맥을 이해하여 자연스러운 품질문서 문장으로 교정하세요.

[검사종류]
{title}

[검사기준]
{spec}

[검사자 원문]
{content}

[최종판정]
{judgment}

반드시 다음 규칙을 지키세요.

1. 오타를 단순 글자 치환이 아니라 전체 문맥으로 이해한다.

2. 검사자가 입력한 숫자, 수량, 재질, Grade,
도면번호, Tag No., 측정값은 임의로 변경하지 않는다.

3. 원문에 없는 숫자, 측정값, 재질, 규격,
압력, 온도, 시간 등을 새로 만들지 않는다.

4. 원문에 단위가 없으면 단위를 임의로 추가하지 않는다.

5. 검사기준에 없는 Spec을 새로 만들지 않는다.

6. 사용자가 선택한 최종판정을 임의로 변경하지 않는다.

7. 검사장소는 검사결과 문장에 반복 작성하지 않는다.

8. corrected_content에는 작업자의 검사내용을
자연스러운 품질검사 문장으로 교정한 내용만 작성한다.

9. result에는 공식 검사결과 문장만 작성한다.

10. action에는 검사내용에 적합한 조치요구만 작성한다.

11. 합격이면 action은 반드시
'별도 조치사항 없음.'
으로 작성한다.

12. 불합격이면 검사종류, 검사기준과 실제 검사내용을
종합하여 문제에 적합한 조치요구를 작성한다.

예:
도막두께 미달
→ 기준 미달 부위를 재도장한 후
도막두께를 재측정하여 요구 기준 충족 여부를 확인할 것.

치수 초과 또는 미달
→ 해당 부위를 수정 또는 재가공한 후
치수를 재측정하여 요구사항 충족 여부를 확인할 것.

외관 손상
→ 손상 부위를 보수한 후 외관 상태를 재확인할 것.

녹 또는 부식
→ 녹 또는 부식을 제거한 후
표면상태를 재확인할 것.

압력시험 누설
→ 누설 부위를 보수한 후
동일 시험조건으로 재시험하여 누설 여부를 확인할 것.

재질 불일치
→ 부적합 자재를 격리 또는 교체하고
재질 및 관련 성적서를 확인한 후 재검사할 것.

용접 외관 불량
→ 불량부를 보수한 후 외관 재검사를 실시할 것.

도장 뭉침 또는 미도장 부위
→ 해당 부위를 보수하고
도장 외관 상태를 재확인할 것.

마스킹 미제거
→ 마스킹을 제거한 후 해당 부위 상태를 재확인할 것.

13. 검사내용에 명확한 조치방법이 포함되어 있으면
그 내용을 우선 반영한다.

14. 검사내용만으로 구체적인 조치방법을 판단하기 어려우면
임의로 추측하지 말고 반드시 다음과 같이 작성한다.

'부적합 내용 확인 후 적절한 조치를 실시하고 재검사할 것.'

15. 조건부 합격이면 검사내용에 기재된
보완사항을 기준으로 조치요구를 작성한다.

16. N/A이면 action은
'해당 없음.'
으로 작성한다.

17. 의미가 불확실한 단어를 억지로 확정하지 않는다.
정확한 의미를 판단하기 어려우면
'내용 확인 필요'라고 표현한다.

다음 수준의 오타도 문맥으로 교정한다.

입력:
도막두게 측정결과 256 267 258 스팩 민달 제도쟝필요

교정:
도막두께 측정 결과 256, 267, 258로 확인되었으며
스펙 미달로 재도장이 필요함.

입력:
압력시헝 합격햇으며 문재가 업음

교정:
압력시험 결과 특이사항이 확인되지 않았으며
적용 기준을 충족함.

입력:
치수 측정결가 도면치수랑 일치하구
외관도 찍힘 변형 부식 업음 전체적으루 양호함

교정:
치수 측정 결과 도면 치수와 일치하며,
외관상 찍힘, 변형 및 부식이 없고 전체적으로 양호함.

입력:
도장 색상 상의하고 도장 뭉친 거 미제가 있고
현장 용접부 마스킹 미제거

교정:
도장 색상에 대한 협의가 필요하며,
일부 부위에서 도장 뭉침과 미처리 상태가 확인됨.
또한 현장 용접부의 마스킹이 제거되지 않은 상태임.

위 예시에서 '미제가'처럼 의미가 완전히 확실하지 않은 표현은
임의로 '미도장'이라고 확정하지 않는다.

반드시 JSON 형식으로만 답변하세요.
"""

        response_schema = {
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
            model=MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": response_schema,
                "temperature": 0.2,
            },
        )

        response_data = json.loads(response.text)

        corrected_spec = str(
            response_data.get(
                "corrected_spec",
                spec,
            )
        ).strip()

        corrected_content = str(
            response_data.get(
                "corrected_content",
                content,
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

    except Exception as error:

        # Gemini가 실패하면 화면에 실제 오류를 보여줍니다.
        # 이 문구가 보이면 캡처해서 확인하면 됩니다.
        st.error(
            f"Gemini 호출 오류: {error}"
        )

        # Gemini 오류가 발생해도 V13 자체는 사용할 수 있도록
        # 기존 규칙 방식으로 자동 전환합니다.
        return fallback_draft(
            types,
            spec,
            content,
            judgment,
            count,
        )
