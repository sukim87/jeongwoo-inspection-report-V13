import re

# 현장에서 자주 발생하는 오타
FIX = {
    "외관상태양호": "외관 상태 양호",
    "이상없슴": "이상 없음",
    "이상업음": "이상 없음",
    "기준미달": "기준 미달",

    "스팩": "스펙",
    "스팩미달": "스펙 미달",
    "스팩민달": "스펙 미달",
    "스펙민달": "스펙 미달",
    "민달": "미달",

    "도막두게": "도막두께",
    "도막두깨": "도막두께",
    "도막 두게": "도막두께",

    "제도장": "재도장",
    "제도쟝": "재도장",
    "재도쟝": "재도장",
    "제도쟝필요": "재도장 필요",
    "재도장필요": "재도장 필요",

    "재검사필요": "재검사 필요",
    "재검사실시": "재검사 실시",
    "치수이상없음": "치수 이상 없음",
    "외관이상없음": "외관 이상 없음",
    "누설없음": "누설 없음",
    "변형없음": "변형 없음",
    "부식없음": "부식 없음",
    "사진참조": "사진 참조",
    "도면참조": "도면 참조",
}


def clean(text):
    text = (text or "").strip()

    # 오타 교정
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

    # 불필요한 공백 정리
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_draft(types, spec, content, judgment, count):

    title = " / ".join(types)

    spec = clean(spec)
    content = clean(content)

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
