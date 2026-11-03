from email.message import EmailMessage
from email.headerregistry import Address
from html import escape
import re


def split_addresses(value):
    parts = re.split(r'[;,\n]+', value or '')
    return [item.strip() for item in parts if item.strip()]


def judgment_mark(judgment):
    return {
        '합격': '✅ 합격',
        '불합격': '❌ 불합격',
        '조건부 합격': '⚠️ 조건부 합격',
        'N/A': 'N/A',
    }.get(judgment, judgment)


def make_subject(data):
    return (
        f"[검사결과 공유] {data['order_no']} / {data['po_step_no']} / "
        f"{data['judgment']} / {data['document_no']}"
    )


def make_html_body(data):
    e = escape
    result = judgment_mark(data['judgment'])
    return f"""
    <div style="font-family:Malgun Gothic,Arial,sans-serif;font-size:11pt;line-height:1.65;color:#222">
      <p>안녕하십니까. 품질팀 김선웅입니다.</p>
      <p>제목의 건 검사결과를 아래와 같이 공유드립니다.</p>
      <div style="border-left:5px solid #c8102e;background:#f7f8fa;padding:14px 18px;margin:16px 0;max-width:760px">
        <div style="font-size:13pt;font-weight:700;margin-bottom:9px">검사결과 요약</div>
        <div><b>프로젝트:</b> {e(data['order_no'])}</div>
        <div><b>품명:</b> {e(data['part_name'])}</div>
        <div><b>검사종류:</b> {e(data['types'])}</div>
        <div><b>검사장소:</b> {e(data['inspection_location'])}</div>
        <div><b>최종판정:</b> <b>{e(result)}</b></div>
      </div>
      <div style="margin:16px 0;max-width:760px">
        <div style="font-size:12pt;font-weight:700;margin-bottom:6px">검사내용</div>
        <div>{e(data['inspection_content'])}</div>
      </div>
      <p><b>상세 검사내용 및 전체 검사사진은 첨부된 검사결과서를 참고하여 주시기 바랍니다.</b></p>
      <p>감사합니다.<br>김선웅 드림.</p>
    </div>
    """.strip()


def make_text_body(data):
    return f"""안녕하십니까. 품질팀 김선웅입니다.

제목의 건 검사결과를 아래와 같이 공유드립니다.

검사결과 요약
프로젝트: {data['order_no']}
품명: {data['part_name']}
검사종류: {data['types']}
검사장소: {data['inspection_location']}
최종판정: {judgment_mark(data['judgment'])}

검사내용
{data['inspection_content']}

상세 검사내용 및 전체 검사사진은 첨부된 검사결과서를 참고하여 주시기 바랍니다.

감사합니다.
김선웅 드림.
"""


def build_eml(data, excel_bytes, excel_filename, to_value='', cc_value=''):
    message = EmailMessage()
    message['Subject'] = make_subject(data)
    to_list = split_addresses(to_value)
    cc_list = split_addresses(cc_value)
    if to_list:
        message['To'] = ', '.join(to_list)
    if cc_list:
        message['Cc'] = ', '.join(cc_list)
    message.set_content(make_text_body(data))
    message.add_alternative(make_html_body(data), subtype='html')
    message.add_attachment(
        excel_bytes,
        maintype='application',
        subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=excel_filename,
    )
    return message.as_bytes()
