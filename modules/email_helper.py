from email.message import EmailMessage
from html import escape
import re


def split_addresses(value):
    parts = re.split(
        r"[;,\n]+",
        value or ""
    )

    return [
        address.strip()
        for address in parts
        if address.strip()
    ]


def judgment_mark(judgment):
    marks = {
        "합격": "✅ 합격",
        "불합격": "❌ 불합격",
        "조건부 합격": "⚠️ 조건부 합격",
        "N/A": "N/A",
    }

    return marks.get(
        judgment,
        judgment
    )


def inspector_name(data):
    """
    기본정보에서 선택한 검사자 이름을 사용한다.

    inspector 값이 전달되지 않은 경우에도
    프로그램 오류가 발생하지 않도록 처리한다.
    """

    name = str(
        data.get(
            "inspector",
            ""
        )
    ).strip()

    if not name:
        name = "검사자"

    return name


def make_subject(data):
    return (
        f"[검사결과 공유] "
        f"{data.get('order_no', '')} / "
        f"{data.get('po_step_no', '')} / "
        f"{data.get('judgment', '')} / "
        f"{data.get('document_no', '')}"
    )


def make_html_body(data):
    e = escape

    inspector = inspector_name(data)

    result = judgment_mark(
        data.get(
            "judgment",
            ""
        )
    )

    return f"""
<div style="
    font-family:'Malgun Gothic','맑은 고딕',Arial,sans-serif;
    font-size:11pt;
    line-height:1.7;
    color:#222222;
">

    <p>
        안녕하십니까.<br>
        품질팀 <b>{e(inspector)}</b>입니다.
    </p>

    <p>
        제목의 건 검사결과를 아래와 같이 공유드립니다.
    </p>

    <div style="
        border-left:5px solid #c8102e;
        background:#f6f7f9;
        padding:15px 18px;
        margin:16px 0;
        max-width:760px;
    ">

        <div style="
            font-size:13pt;
            font-weight:700;
            margin-bottom:10px;
        ">
            검사결과 요약
        </div>

        <div>
            <b>프로젝트:</b>
            {e(str(data.get('order_no', '')))}
        </div>

        <div>
            <b>품명:</b>
            {e(str(data.get('part_name', '')))}
        </div>

        <div>
            <b>검사종류:</b>
            {e(str(data.get('types', '')))}
        </div>

        <div>
            <b>검사장소:</b>
            {e(str(data.get('inspection_location', '')))}
        </div>

        <div>
            <b>최종판정:</b>
            <b>{e(result)}</b>
        </div>

    </div>

    <div style="
        margin:16px 0;
        max-width:760px;
    ">

        <div style="
            font-size:12pt;
            font-weight:700;
            margin-bottom:6px;
        ">
            검사내용
        </div>

        <div>
            {e(str(data.get('inspection_content', '')))}
        </div>

    </div>

    <p>
        <b>
            상세 검사내용 및 전체 검사사진은
            첨부된 검사결과서를 참고하여 주시기 바랍니다.
        </b>
    </p>

    <p>
        감사합니다.<br>
        <b>{e(inspector)}</b> 드림.
    </p>

</div>
""".strip()


def make_text_body(data):
    inspector = inspector_name(data)

    return f"""안녕하십니까.
품질팀 {inspector}입니다.

제목의 건 검사결과를 아래와 같이 공유드립니다.

검사결과 요약

프로젝트: {data.get('order_no', '')}
품명: {data.get('part_name', '')}
검사종류: {data.get('types', '')}
검사장소: {data.get('inspection_location', '')}
최종판정: {judgment_mark(data.get('judgment', ''))}

검사내용

{data.get('inspection_content', '')}

상세 검사내용 및 전체 검사사진은
첨부된 검사결과서를 참고하여 주시기 바랍니다.

감사합니다.
{inspector} 드림.
"""


def build_eml(
    data,
    excel_bytes,
    excel_filename,
    to_value="",
    cc_value="",
):
    message = EmailMessage()

    message["Subject"] = make_subject(
        data
    )

    to_list = split_addresses(
        to_value
    )

    cc_list = split_addresses(
        cc_value
    )

    if to_list:
        message["To"] = ", ".join(
            to_list
        )

    if cc_list:
        message["Cc"] = ", ".join(
            cc_list
        )

    message.set_content(
        make_text_body(data)
    )

    message.add_alternative(
        make_html_body(data),
        subtype="html",
    )

    message.add_attachment(
        excel_bytes,
        maintype="application",
        subtype=(
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        filename=excel_filename,
    )

    return message.as_bytes()
