from datetime import date
from io import BytesIO
from pathlib import Path
import base64, hashlib
import streamlit as st
from PIL import Image, ImageOps
from modules.application_reader import read_application
from modules.report_text import make_draft
from modules.excel_writer import build_report
from modules.email_helper import build_eml, make_html_body, make_subject

VERSION = 'V13'
BASE=Path(__file__).resolve().parent
st.set_page_config(page_title='Jeongwoo AI 품질검사 결과서',page_icon='📋',layout='wide',initial_sidebar_state='expanded')
CODES=[('서류검토','DR'),('열처리','HT'),('재료검사','MI'),('조립검사','AS'),('마킹검사','MK'),('압력시험','PR'),('취부검사','FU'),('성능시험','PF'),('치수검사','DI'),('비파괴검사','NDE'),('외관검사','VI'),('도장/도금','PT'),('가공검사','MA'),('포장/출하','PK'),('성형검사','FM'),('용접검사','WD')]

def data_uri(path):
    return 'data:image/jpeg;base64,'+base64.b64encode(Path(path).read_bytes()).decode('ascii')
hero_uri=data_uri(BASE/'assets/company_view_day.jpg')

st.markdown(f"""<style>
:root{{--jw-red:#c8102e;--jw-navy:#0f1f3d;--jw-soft:#f4f6f9;--jw-line:#dde3eb;--jw-text:#17233b}}
html,body,[class*='css'],[data-testid='stAppViewContainer'],[data-testid='stSidebar']{{font-family:'Malgun Gothic','맑은 고딕','Noto Sans KR',Arial,sans-serif!important;color:var(--jw-text)}}
[data-testid='stAppViewContainer']{{background:#fff}}
[data-testid='stHeader']{{background:rgba(255,255,255,.92)}}
.block-container{{max-width:1280px;padding-top:1.7rem!important;padding-bottom:4rem!important}}
section[data-testid='stSidebar']{{background:linear-gradient(180deg,#f5f7fa 0%,#eef2f7 100%);border-right:1px solid #dbe1e9}}
section[data-testid='stSidebar'] .block-container{{padding:1.15rem .85rem!important}}
[data-testid='stSidebar'] img{{background:#fff;border-radius:12px;padding:8px;border:1px solid #e2e6ec}}
.side-card{{background:#fff;border:1px solid #dce2e9;border-top:4px solid var(--jw-red);border-radius:10px;padding:15px 14px;line-height:1.65;font-size:.86rem;box-shadow:0 4px 14px rgba(28,42,67,.05)}}
.side-footer{{margin-top:32px;padding:18px 6px 4px;border-top:1px solid #cfd6df;color:#687386;font-size:.72rem;line-height:1.6}}
.version-badge{{display:inline-block;margin:8px 0 10px;padding:5px 12px;border-radius:18px;background:#667085;color:white;font-weight:700}}
.hero{{position:relative;overflow:hidden;min-height:280px;border-radius:15px;background:linear-gradient(90deg,rgba(5,16,33,.96) 0%,rgba(5,16,33,.82) 48%,rgba(5,16,33,.12) 100%),url('{hero_uri}') center 58%/cover no-repeat;display:flex;align-items:center;padding:35px 38px;box-shadow:0 10px 28px rgba(20,35,60,.16)}}
.hero-copy{{max-width:720px;color:#fff}}
.hero-title{{font-size:3rem;line-height:1.23;font-weight:900;letter-spacing:-.055em;margin:0 0 18px;text-shadow:0 2px 8px rgba(0,0,0,.28)}}
.hero-title .accent{{color:#ff334f}}
.hero-sub{{font-size:1.02rem;line-height:1.75;font-weight:600;text-shadow:0 1px 5px rgba(0,0,0,.35)}}
.section-title{{display:flex;align-items:center;gap:10px;margin:18px 0 0;padding:13px 17px;background:linear-gradient(180deg,#f3f1e9,#e4e0d2);border:1px solid #d3cdbc;border-radius:11px 11px 0 0;color:#13213c;font-size:1.12rem;font-weight:900}}
.section-body-start{{height:0}}
[data-testid='stVerticalBlockBorderWrapper']{{border-color:#e0e5ec!important;border-radius:0 0 12px 12px!important;box-shadow:0 4px 15px rgba(20,35,60,.035)}}
[data-baseweb='input']>div,[data-baseweb='textarea']>div,[data-baseweb='select']>div{{background:#f7f9fc!important;border-color:#dde3ec!important;border-radius:8px!important}}
.stTextInput input,.stTextArea textarea{{color:#18243c}}
.stButton button,.stDownloadButton button{{border-radius:9px!important;font-weight:800!important;min-height:45px}}
.stButton button[kind='primary'],.stDownloadButton button[kind='primary']{{background:linear-gradient(90deg,#c8102e,#ec153e)!important;border:0!important;box-shadow:0 6px 14px rgba(200,16,46,.18)}}
[data-testid='stFileUploaderDropzone']{{background:#f8fafc!important;border:1.5px dashed #c9d2df!important;border-radius:10px!important;padding:1rem!important}}
.quick-note{{font-size:.81rem;color:#667085;line-height:1.6;background:#f7f9fc;border:1px solid #e0e5ec;border-radius:8px;padding:10px 12px}}
.mailbox{{background:#fff;border:2px solid var(--jw-red);border-radius:12px;padding:16px;margin-top:18px}}
@media(max-width:900px){{.hero{{min-height:240px;padding:28px 24px;background-position:62% center}}.hero-title{{font-size:2.2rem}}.hero-sub{{font-size:.92rem}}}}
</style>""",unsafe_allow_html=True)

with st.sidebar:
    st.image(str(BASE/'assets/jeongwoo_logo.jpg'),use_container_width=True)
    st.markdown("""<div class='side-card'><b>☎ 시스템 문의 및 지원</b><br><br><b>부서:</b> PS품질팀<br><b>담당자:</b> 김선웅<br><b>이메일:</b> <span style='color:#0067b8'>sukim1@jimc.co.kr</span><br><br><span style='color:#667085'>프로그램 오류, 기능 개선,<br>검사양식 및 입력항목 변경 요청</span></div>""",unsafe_allow_html=True)
    st.markdown(f"""<div class='side-footer'><b style='color:#17233b;font-size:.8rem'>Jeongwoo AI Inspection Report</b><br><span class='version-badge'>Version {VERSION}</span><br><a href='https://www.jimc.co.kr' target='_blank' style='color:#c8102e;font-weight:800;text-decoration:none'>JIMC.CO.KR ↗</a><br><br>Copyright © JEONGWOO.<br>All Rights Reserved.</div>""",unsafe_allow_html=True)

st.markdown("""<div class='hero'><div class='hero-copy'><div class='hero-title'><span class='accent'>AI로 더 빠르게</span> 작성하고<br><span class='accent'>공유하는</span> 품질검사 결과서</div><div class='hero-sub'>사진과 간략하게 검사내용을 입력하고 결과만 확인하세요.<br>입력 오타를 다듬어 검사 결과서를 작성하고 메일로 간편하게 공유할 수 있습니다.</div></div></div>""",unsafe_allow_html=True)

c1,c2=st.columns(2,gap='medium')
with c1:
    with st.expander('👁 완성 결과서 예시 보기'):
        st.image(str(BASE/'assets/sample_result.png'),use_container_width=True)
with c2:
    manual=BASE/'assets/Jeongwoo_AI_품질검사_결과서_V12_사용매뉴얼.pdf'
    st.download_button('📕 사용 매뉴얼 PDF 다운로드',manual.read_bytes(),file_name=manual.name,mime='application/pdf',use_container_width=True)

st.markdown("<div class='section-title'>1. 검사신청서 불러오기</div>",unsafe_allow_html=True)
with st.container(border=True):
    app=st.file_uploader('검사신청서 PDF 또는 Excel 파일을 업로드하세요.',type=['pdf','xlsx'],help='기존 또는 신규 검사신청서를 첨부하면 확실한 기본정보만 자동으로 입력합니다.')
    if app:
        sig=hashlib.sha256(app.getvalue()).hexdigest()
        if st.session_state.get('appsig')!=sig:
            try:
                info,preview=read_application(app)
                for key in ('customer','part_name','order_no','po_step_no','inspection_location'):st.session_state[key]=info.get(key,'')
                st.session_state.appsig=sig;st.session_state.preview=preview;st.session_state.reader_info=info
            except Exception as exc:
                st.error(f'신청서 분석 중 오류가 발생했습니다: {exc}')
        info=st.session_state.get('reader_info',{})
        review=info.get('review_fields',[]);names={'customer':'고객사','part_name':'부품명','order_no':'수주번호','po_step_no':'발주/공정번호','inspection_location':'검사장소'}
        if review:st.warning('확실한 정보만 자동입력했습니다. 직접 확인 필요: '+', '.join(names.get(x,x) for x in review))
        else:st.success('신청서 기본정보를 자동입력했습니다. 아래 내용을 최종 확인해 주세요.')
        if st.session_state.get('preview') is not None:
            with st.expander('방향 보정된 신청서 미리보기'):st.image(st.session_state.preview,use_container_width=True)

st.markdown("<div class='section-title'>2. 기본정보</div>",unsafe_allow_html=True)
with st.container(border=True):
    a,b=st.columns(2);customer=a.text_input('고객사',key='customer',placeholder='예: 한화오션');part=b.text_input('부품명 *',key='part_name',placeholder='예: Cold Support')
    a,b=st.columns(2);order=a.text_input('수주번호 *',key='order_no',placeholder='예: H260926UD');po=b.text_input('발주/공정번호 *',key='po_step_no',placeholder='예: PS2610022')
    a,b=st.columns(2)
    location=a.text_input('검사장소 *',key='inspection_location',placeholder='신청서의 업체/팀명이 있으면 자동입력')
    inspector_names=['김상민','김선웅','김희성','박재암','송민준','안병영','안예지','유병조','이승현','이진원','이진표']
    inspector=b.selectbox('검사자 *',inspector_names,index=inspector_names.index('김선웅'),help='검사를 수행한 검사원을 선택하세요.')
    a,b=st.columns(2);seq=a.number_input('문서 순번',1,999,1,help='최초 001, 동일 건의 추가 검사·재검사는 002, 003 순으로 사용');doc=f"IRR-{order or 'ORDER'}-{po or 'PO-STEP'}-{int(seq):03d}";b.text_input('문서번호',doc,disabled=True)

st.markdown("<div class='section-title'>3. 검사종류 <span style='font-size:.8rem;font-weight:600;color:#667085'>(복수 선택 가능)</span></div>",unsafe_allow_html=True)
with st.container(border=True):
    cols=st.columns(4);selected=[]
    for i,(name,code) in enumerate(CODES):
        label=f'{name} ({code})'
        if cols[i%4].checkbox(label,key=f'inspection_{code}'):selected.append(label)

st.markdown("<div class='section-title'>4. 검사 기준 및 검사내용</div>",unsafe_allow_html=True)
with st.container(border=True):
    refs=[];rc=st.columns(3)
    for col,item in zip(rc,('도면','구매사양서','구매발주서')):
        if col.checkbox(item,key='ref_'+item):refs.append(item)
    manual_spec=st.text_input('추가 검사기준 직접 입력 (선택)',placeholder='예: ASME B31.1 / DFT Min. 320 μm / 승인도면 Rev.2')
    spec=' / '.join(refs+([manual_spec.strip()] if manual_spec.strip() else []))
    a,b=st.columns(2);a.text_area('검사기준 *',value=spec,height=95,disabled=True);content=b.text_area('검사내용 *',key='inspection_content',height=95,placeholder='현장에서 확인한 내용을 간단히 입력하세요.\n예: 치수 및 외관 스펙 만족')
    judgment=st.selectbox('최종판정',['합격','불합격','조건부 합격','N/A'])

st.markdown("<div class='section-title'>5. 검사사진 첨부</div>",unsafe_allow_html=True)
with st.container(border=True):
    photos=st.file_uploader('검사사진을 업로드하세요. (최대 8장)',type=['jpg','jpeg','png','webp'],accept_multiple_files=True);rots=[];fit_modes=[]
    if len(photos)>8:st.warning('앞에서부터 8장까지만 자동 배치됩니다. 추가 사진은 을지 양식을 복사·편집해 주세요.')
    if photos:
        pcs=st.columns(2)
        for i,p in enumerate(photos[:8]):
            with pcs[i%2]:
                im=ImageOps.exif_transpose(Image.open(BytesIO(p.getvalue())))
                r=st.selectbox(f'사진 {i+1} 방향',['자동','오른쪽 90°','180°','왼쪽 90°'],key=f'rot_{i}')
                deg={'자동':0,'오른쪽 90°':90,'180°':180,'왼쪽 90°':270}[r];rots.append(deg)
                mode=st.selectbox(f'사진 {i+1} 맞춤',['전체 사진 표시','사진 칸 채우기'],key=f'fit_{i}');fit_modes.append(mode)
                if deg:im=im.rotate(-deg,expand=True)
                st.image(im,caption=f'사진 {i+1}',use_container_width=True)
    st.markdown("<div class='quick-note'>전체 사진 표시가 기본값이며 사진을 자르지 않습니다. 갑지에는 사진 1~2, 사진 3~8은 을지에 배치됩니다.</div>",unsafe_allow_html=True)

sig=hashlib.sha256(('|'.join(selected)+'|'+spec+'|'+content+'|'+judgment+'|'+str(len(photos))).encode()).hexdigest()
if st.session_state.get('draft_sig') not in (None,sig):st.session_state.draft_ready=False
if st.button('✨ 오타 교정 후 AI 초안 작성',type='primary',use_container_width=True):
    if not selected or not spec or not content.strip():st.error('검사종류, 검사기준, 검사내용을 먼저 입력해 주세요.')
    else:
        r,a,c,cs,cc=make_draft(selected,spec,content,judgment,len(photos));st.session_state.ai_result=r;st.session_state.ai_action=a;st.session_state.ai_caption=c;st.session_state.corrected_spec=cs;st.session_state.corrected_content=cc;st.session_state.draft_ready=True;st.session_state.draft_sig=sig;st.rerun()

if st.session_state.get('draft_ready'):
    st.markdown("<div class='section-title'>6. AI 작성 결과 확인</div>",unsafe_allow_html=True)
    with st.container(border=True):
        a,b=st.columns(2);a.text_area('교정된 검사기준',st.session_state.corrected_spec,disabled=True);b.text_area('교정된 검사내용',st.session_state.corrected_content,disabled=True)
        result=st.text_area('검사결과 문장',key='ai_result');action=st.text_area('조치요구',key='ai_action');caption=st.text_area('사진 설명',key='ai_caption')
        missing=[n for n,v in [('부품명',part),('수주번호',order),('발주/공정번호',po),('검사장소',location)] if not str(v).strip()]
        if missing:st.warning('필수 입력: '+', '.join(missing))
        if st.button('✅ 검사결과서 생성',type='primary',use_container_width=True,disabled=bool(missing)):
            data={'customer':customer,'part_name':part,'order_no':order,'po_step_no':po,'inspection_location':location,'inspector':inspector,'date':date.today(),'doc':doc,'types':' / '.join(selected),'spec':st.session_state.corrected_spec,'inspection_content':st.session_state.corrected_content,'judgment':judgment,'result':result,'action':action,'caption':caption}
            st.session_state.mail_data={'order_no':order,'po_step_no':po,'part_name':part,'inspection_location':location,'types':' / '.join(selected),'judgment':judgment,'inspection_content':st.session_state.corrected_content,'document_no':doc}
            try:st.session_state.out,st.session_state.name=build_report(data,photos[:8],rots,fit_modes);st.success('검사결과서가 완성되었습니다.')
            except Exception as exc:st.error(f'검사결과서 생성 중 오류: {exc}')

if st.session_state.get('out'):
    st.download_button('📥 검사결과서 다운로드',st.session_state.out,file_name=st.session_state.name,mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',type='primary',use_container_width=True)
    st.markdown("<div class='mailbox'><b>✉️ 검사결과 메일 작성</b><br><span style='color:#667085'>수신자만 입력하면 제목, 본문, Excel 첨부가 포함된 Outlook 메일 파일을 만듭니다.</span></div>",unsafe_allow_html=True)
    to_value=st.text_input('받는 사람 이메일',placeholder='여러 명은 세미콜론(;)으로 구분');cc_value=st.text_input('참조 이메일 (선택)')
    mail_data=st.session_state.mail_data;st.text_input('메일 제목',value=make_subject(mail_data),disabled=True)
    with st.expander('메일 본문 미리보기',expanded=True):st.markdown(make_html_body(mail_data),unsafe_allow_html=True)
    eml=build_eml(mail_data,st.session_state.out,st.session_state.name,to_value,cc_value)
    st.download_button('✉️ 첨부 포함 Outlook 메일 열기 (.eml)',eml,file_name=f"{mail_data['document_no']}_메일.eml",mime='message/rfc822',type='primary',use_container_width=True)
