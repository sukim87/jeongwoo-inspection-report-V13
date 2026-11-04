import json
import re
import urllib.error
import urllib.request

import streamlit as st


MODEL_NAME = "gemini-3.5-flash-lite"
TIMEOUT_SECONDS = 15


# Gemini 연결 실패 시 사용할 최소 백업 교정
FALLBACK_FIX = {
    "외관상태양호": "외관 상태 양호",
    "이상없슴": "이상 없음",
    "이상업음": "이상 없음",
    "이상 업음": "이상 없음",
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
    "압력시엄": "압력시험",
    "합격햇": "합격했",
    "합격하엿": "합격하였",
    "문재": "문제",
    "업음": "없음",
    "업슴": "없음",

    "후렌지": "플랜지",
    "치수이상없음": "치수 이상 없음",
    "외관이상없음": "외관 이상 없음",
    "누설없음": "누설 없음",
    "변형없음": "변형 없음",
    "부식없음": "부식 없음",

    "측정결가": "측정 결과",
    "일치하구": "일치하며",
    "전체적으루": "전체적으로",

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


def fallback_action(corrected_content, judgment):
    if judgment == "합격":
        return "별도 조치사항 없음."

    if judgment == "조건부 합격":
        return (
            "지정된 보완사항을 완료하고 객관적 증빙을 확인한 후 "
            "최종 승인할 것."
        )

    if judgment == "N/A":
        return "해당 없음."

    text = corrected_content

    if "도막두께" in text and (
        "미달" in text or "재도장" in text
    ):
        return (
            "기준 미달 부위를 재도장한 후 도막두께를 재측정하여 "
            "요구 기준 충족 여부를 확인할 것."
        )

    if "누설" in text:
        return (
            "누설 부위를 보수한 후 동일 시험조건으로 재시험하여 "
            "누설 여부를 확인할 것."
        )

    if "재질 불일치" in text or "재질불일치" in text:
        return (
            "부적합 자재를 격리 또는 교체하고 재질 및 관련 성적서를 "
            "확인한 후 재검사할 것."
        )

    if "치수" in text and (
        "초과" in text
        or "미달" in text
        or "재가공" in text
    ):
        return (
            "기준을 벗어난 부위를 수정 또는 재가공한 후 치수를 "
            "재측정하여 요구사항 충족 여부를 확인할 것."
        )

    actions = []

    if "도장 뭉침" in text or "도장뭉침" in text:
        actions.append("도장 뭉침 부위를 보수")

    if "미도장" in text:
        actions.append("미도장 부위를 보수도장")

    if "마스킹 미제거" in text or (
        "마스킹" in text and "미제거" in text
    ):
        actions.append("현장 용접부의 마스킹을 제거")

    if actions:
        joined = ", ".join(actions)

        return (
            f"{joined}한 후 해당 부위의 도장 및 외관 상태를 "
            "재확인할 것."
        )

    if "녹" in text or "부식" in text:
        return (
            "녹 또는 부식을 제거한 후 표면 상태를 재확인할 것."
        )

    if "용접" in text and (
        "불량" in text or "보수" in text
    ):
        return (
            "용접 불량 부위를 보수한 후 용접 외관 재검사를 실시할 것."
        )

    return (
        "부적합 내용 확인 후 적절한 조치를 실시하고 재검사할 것."
    )


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
            f"적용 기준({corrected_spec})을 충족하여 합격으로 판정함."
        )

    elif judgment == "불합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            f"적용 기준({corrected_spec})을 충족하지 못하여 "
            f"불합격으로 판정함."
        )

    elif judgment == "조건부 합격":
        result = (
            f"{title} 결과, {corrected_content}로 확인되었으며 "
            "보완조건 이행을 전제로 조건부 합격으로 판정함."
        )

    else:
        result = f"{title} 항목은 해당 없음(N/A)으로 처리함."

    action = fallback_action(
        corrected_content,
        judgment,
    )

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


def extract_response_text(response_data):
    candidates = response_data.get("candidates", [])

    if not candidates:
        raise ValueError(
            "Gemini 응답에 candidates가 없습니다."
        )

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    for part in parts:
        text = part.get("text")

        if text:
            return text.strip()

    raise ValueError(
        "Gemini 응답에 text가 없습니다."
    )


def call_gemini(prompt):
    api_key = st.secrets["GEMINI_API_KEY"]

    endpoint = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL_NAME}:generateContent"
    )

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "corrected_spec": {
                "type": "STRING"
            },
            "corrected_content": {
                "type": "STRING"
            },
            "result": {
                "type": "STRING"
            },
            "action": {
                "type": "STRING"
            },
        },
        "required": [
            "corrected_spec",
            "corrected_content",
            "result",
            "action",
        ],
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": response_schema,
            "maxOutputTokens": 700,
        },
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT_SECONDS,
    ) as response:
        response_body = response.read().decode(
            "utf-8"
        )

    response_data = json.loads(response_body)
    response_text = extract_response_text(
        response_data
    )

    return json.loads(response_text)


def make_draft(
    types,
    spec,
    content,
    judgment,
    count,
):
    title = " / ".join(types)

    prompt = f"""
당신은 플랜트 및 제작품 품질검사 결과서 작성 보조 AI입니다.

현장 검사자가 휴대전화로 작성한 문장에서
심한 오타, 맞춤법, 띄어쓰기와 품질용어를 교정하고
공식 검사결과와 조치요구를 작성하세요.

검사종류:
{title}

검사기준:
{spec}

검사자 원문:
{content}

최종판정:
{judgment}

규칙:

1. 문장 전체의 검사 문맥을 이해하여 오타를 교정한다.

2. 숫자, 수량, 재질, Grade, 도면번호,
Tag No. 및 측정값을 변경하거나 새로 만들지 않는다.

3. 원문에 없는 단위, 규격, 압력, 온도 및 시간을
추가하지 않는다.

4. 사용자가 선택한 최종판정을 변경하지 않는다.

5. 검사장소는 검사결과 문장에 작성하지 않는다.

6. corrected_spec에는 교정된 검사기준만 작성한다.

7. corrected_content에는 작업자의 원문을
자연스러운 품질검사 문장으로 교정한 내용만 작성한다.

8. result에는 공식 검사결과 문장만 작성한다.

9. action에는 실제 검사내용에 적합한 조치요구만 작성한다.

10. 합격이면 action은 반드시
'별도 조치사항 없음.'
으로 작성한다.

11. 불합격이면 다음 원칙을 적용한다.

- 도막두께 미달:
  재도장 후 도막두께 재측정

- 치수 초과 또는 미달:
  수정 또는 재가공 후 치수 재검사

- 외관 손상:
  손상 부위 보수 후 외관 재확인

- 녹 또는 부식:
  제거 후 표면상태 재확인

- 압력시험 누설:
  누설 부위 보수 후 동일 시험조건으로 재시험

- 재질 불일치:
  부적합 자재 격리 또는 교체 후
  재질과 성적서 확인 및 재검사

- 용접 외관 불량:
  불량부 보수 후 용접 외관 재검사

- 도장 뭉침:
  도장 뭉침 부위 보수 후 도장상태 재확인

- 미도장 부위:
  보수도장 후 도장상태 재확인

- 마스킹 미제거:
  마스킹 제거 후 해당 부위 상태 재확인

12. 검사자 원문에 조치방법이 있으면
해당 내용을 우선 반영한다.

13. 의미가 불확실한 표현은 임의로 확정하지 말고
'내용 확인 필요'라고 작성한다.

14. 구체적인 조치방법을 판단하기 어려우면
'부적합 내용 확인 후 적절한 조치를 실시하고 재검사할 것.'
으로 작성한다.

15. 조건부 합격은 입력된 보완사항을 반영한다.

16. N/A이면 action은 '해당 없음.'으로 작성한다.

예시 1:

입력:
도막두게 256 267 258 스팩 민달 제도쟝필요

교정:
도막두께 측정값 256, 267, 258이 스펙 미달로 확인되어
재도장이 필요함.

예시 2:

입력:
압력시헝 합격햇으며 문재가 업음

교정:
압력시험 결과 특이사항이 확인되지 않았으며
적용 기준을 충족함.

예시 3:

입력:
도장 색상 상의하고 도장 뭉친 거 미제가 있고
현장 용접부 마스킹 미제거

교정:
도장 색상에 대한 협의가 필요하며,
도장 뭉침과 미처리 상태 및
현장 용접부 마스킹 미제거가 확인됨.

반드시 다음 네 항목만 JSON으로 반환한다.

corrected_spec
corrected_content
result
action
"""

    try:
        data = call_gemini(prompt)

        corrected_spec = str(
            data.get(
                "corrected_spec",
                spec,
            )
        ).strip()

        corrected_content = str(
            data.get(
                "corrected_content",
                content,
            )
        ).strip()

        result = str(
            data.get(
                "result",
                "",
            )
        ).strip()

        action = str(
            data.get(
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

    except urllib.error.HTTPError as error:
        detail = error.read().decode(
            "utf-8",
            errors="replace",
        )

        error_message = (
            f"Gemini HTTP 오류 {error.code}: "
            f"{detail[:500]}"
        )

        print(error_message)
        st.error(error_message)

    except urllib.error.URLError as error:
        error_message = (
            "Gemini 연결 오류: "
            f"{error.reason}"
        )

        print(error_message)
        st.error(error_message)

    except TimeoutError:
        error_message = (
            f"Gemini 응답이 {TIMEOUT_SECONDS}초를 초과하여 "
            "기본 교정으로 전환했습니다."
        )

        print(error_message)
        st.warning(error_message)

    except Exception as error:
        error_message = (
            "Gemini 처리 오류: "
            f"{type(error).__name__}: {error}"
        )

        print(error_message)
        st.error(error_message)

    # Gemini 실패 시 즉시 기존 방식으로 전환
    return fallback_draft(
        types,
        spec,
        content,
        judgment,
        count,
    )
