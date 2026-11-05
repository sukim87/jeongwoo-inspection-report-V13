from datetime import date
from io import BytesIO
from pathlib import Path
import base64
import hashlib

import streamlit as st
from PIL import Image, ImageOps

from modules.application_reader import read_application
from modules.report_text import make_draft
from modules.excel_writer import build_report
from modules.email_helper import (
    build_eml,
    make_html_body,
    make_subject,
)


VERSION = "V13"
BASE = Path(__file__).resolve().parent


st.set_page_config(
    page_title="Jeongwoo AI 품질검사 결과서",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)


INSPECTION_CODES = [
    ("서류검토", "DR"),
    ("열처리", "HT"),
    ("재료검사", "MI"),
    ("조립검사", "AS"),
    ("마킹검사", "MK"),
    ("압력시험", "PR"),
    ("취부검사", "FU"),
    ("성능시험", "PF"),
    ("치수검사", "DI"),
    ("비파괴검사", "NDE"),
    ("외관검사", "VI"),
    ("도장/도금", "PT"),
    ("가공검사", "MA"),
    ("포장/출하", "PK"),
    ("성형검사", "FM"),
    ("용접검사", "WD"),
]


INSPECTOR_NAMES = [
    "김상민",
    "김선웅",
    "김희성",
    "박재암",
    "송민준",
    "안병영",
    "안예지",
    "유병조",
    "이승현",
    "이진원",
    "이진표",
]


def image_data_uri(path):
    image_bytes = Path(path).read_bytes()

    encoded = base64.b64encode(
        image_bytes
    ).decode("ascii")

    return (
        "data:image/jpeg;base64,"
        + encoded
    )


company_photo_path = (
    BASE
    / "assets"
    / "company_view_day.jpg"
)

hero_image_uri = image_data_uri(
    company_photo_path
)


# =========================================================
# 화면 스타일
# =========================================================

st.markdown(
    f"""
    <style>
    :root {{
        --jw-red: #c8102e;
        --jw-navy: #0f1f3d;
        --jw-soft: #f4f6f9;
        --jw-line: #dde3eb;
        --jw-text: #17233b;
    }}

    html,
    body,
    [class*="css"],
    [data-testid="stAppViewContainer"],
    [data-testid="stSidebar"] {{
        font-family:
            "Malgun Gothic",
            "맑은 고딕",
            "Noto Sans KR",
            Arial,
            sans-serif !important;

        color: var(--jw-text);
    }}

    [data-testid="stAppViewContainer"] {{
        background: #ffffff;
    }}

    [data-testid="stHeader"] {{
        background: rgba(
            255,
            255,
            255,
            0.92
        );
    }}

    .block-container {{
        max-width: 1280px;
        padding-top: 1.7rem !important;
        padding-bottom: 4rem !important;
    }}

    section[data-testid="stSidebar"] {{
        background:
            linear-gradient(
                180deg,
                #f5f7fa 0%,
                #eef2f7 100%
            );

        border-right:
            1px solid #dbe1e9;
    }}

    section[data-testid="stSidebar"]
    .block-container {{
        padding:
            1.15rem
            0.85rem !important;
    }}

    [data-testid="stSidebar"] img {{
        background: #ffffff;
        border-radius: 12px;
        padding: 8px;
        border:
            1px solid #e2e6ec;
    }}

    .side-card {{
        background: #ffffff;
        border:
            1px solid #dce2e9;
        border-top:
            4px solid var(--jw-red);
        border-radius: 10px;
        padding: 15px 14px;
        line-height: 1.65;
        font-size: 0.86rem;

        box-shadow:
            0 4px 14px
            rgba(28, 42, 67, 0.05);
    }}

    .side-footer {{
        margin-top: 32px;
        padding:
            18px
            6px
            4px;

        border-top:
            1px solid #cfd6df;

        color: #687386;
        font-size: 0.72rem;
        line-height: 1.6;
    }}

    .version-badge {{
        display: inline-block;
        margin:
            8px
            0
            10px;

        padding:
            5px
            12px;

        border-radius: 18px;
        background: #667085;
        color: #ffffff;
        font-weight: 700;
    }}

    .hero {{
        position: relative;
        overflow: hidden;
        min-height: 280px;
        border-radius: 15px;

        background:
            linear-gradient(
                90deg,
                rgba(5, 16, 33, 0.96) 0%,
                rgba(5, 16, 33, 0.82) 48%,
                rgba(5, 16, 33, 0.12) 100%
            ),
            url("{hero_image_uri}")
            center 58%
            / cover
            no-repeat;

        display: flex;
        align-items: center;

        padding:
            35px
            38px;

        box-shadow:
            0 10px 28px
            rgba(20, 35, 60, 0.16);
    }}

    .hero-copy {{
        max-width: 720px;
        color: #ffffff;
    }}

    .hero-title {{
        font-size: 3rem;
        line-height: 1.23;
        font-weight: 900;
        letter-spacing: -0.055em;
        margin:
            0
            0
            18px;

        text-shadow:
            0 2px 8px
            rgba(0, 0, 0, 0.28);
    }}

    .hero-title .accent {{
        color: #ff334f;
    }}

    .hero-sub {{
        font-size: 1.02rem;
        line-height: 1.75;
        font-weight: 600;

        text-shadow:
            0 1px 5px
            rgba(0, 0, 0, 0.35);
    }}

    .section-title {{
        display: flex;
        align-items: center;
        gap: 10px;

        margin:
            18px
            0
            0;

        padding:
            13px
            17px;

        background:
            linear-gradient(
                180deg,
                #f3f1e9,
                #e4e0d2
            );

        border:
            1px solid #d3cdbc;

        border-radius:
            11px
            11px
            0
            0;

        color: #13213c;
        font-size: 1.12rem;
        font-weight: 900;
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-color:
            #e0e5ec !important;

        border-radius:
            0 0 12px 12px !important;

        box-shadow:
            0 4px 15px
            rgba(20, 35, 60, 0.035);
    }}

    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {{
        background:
            #f7f9fc !important;

        border-color:
            #dde3ec !important;

        border-radius:
            8px !important;
    }}

    .stTextInput input,
    .stTextArea textarea {{
        color: #18243c;
    }}

    .stButton button,
    .stDownloadButton button {{
        border-radius:
            9px !important;

        font-weight:
            800 !important;

        min-height: 45px;
    }}

    .stButton button[kind="primary"],
    .stDownloadButton button[kind="primary"] {{
        background:
            linear-gradient(
                90deg,
                #c8102e,
                #ec153e
            ) !important;

        border:
            0 !important;

        box-shadow:
            0 6px 14px
            rgba(200, 16, 46, 0.18);
    }}

    [data-testid="stFileUploaderDropzone"] {{
        background:
            #f8fafc !important;

        border:
            1.5px dashed
            #c9d2df !important;

        border-radius:
            10px !important;

        padding:
            1rem !important;
    }}

    .quick-note {{
        font-size: 0.81rem;
        color: #667085;
        line-height: 1.6;
        background: #f7f9fc;

        border:
            1px solid #e0e5ec;

        border-radius: 8px;

        padding:
            10px
            12px;
    }}

    .mailbox {{
        background: #ffffff;

        border:
            2px solid
            var(--jw-red);

        border-radius: 12px;
        padding: 16px;
        margin-top: 18px;
    }}

    @media (
        max-width: 900px
    ) {{
        .hero {{
            min-height: 240px;
            padding:
                28px
                24px;

            background-position:
                62% center;
        }}

        .hero-title {{
            font-size: 2.2rem;
        }}

        .hero-sub {{
            font-size: 0.92rem;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 왼쪽 사이드바
# =========================================================

with st.sidebar:
    logo_path = (
        BASE
        / "assets"
        / "jeongwoo_logo.jpg"
    )

    if logo_path.exists():
        st.image(
            str(logo_path),
            use_container_width=True,
        )

    st.markdown(
        """
        <div class="side-card">
            <b>☎ 시스템 문의 및 지원</b>
            <br><br>

            <b>부서:</b> PS품질팀
            <br>

            <b>담당자:</b> 김선웅
            <br>

            <b>이메일:</b>
            <span style="color:#0067b8">
                sukim1@jimc.co.kr
            </span>

            <br><br>

            <span style="color:#667085">
                프로그램 오류, 기능 개선,
                <br>
                검사양식 및 입력항목 변경 요청
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="side-footer">
            <b style="
                color:#17233b;
                font-size:0.8rem;
            ">
                Jeongwoo AI Inspection Report
            </b>

            <br>

            <span class="version-badge">
                Version {VERSION}
            </span>

            <br>

            <a
                href="https://www.jimc.co.kr"
                target="_blank"
                style="
                    color:#c8102e;
                    font-weight:800;
                    text-decoration:none;
                "
            >
                JIMC.CO.KR ↗
            </a>

            <br><br>

            Copyright © JEONGWOO.
            <br>
            All Rights Reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 상단 Hero 영역
# =========================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-copy">

            <div class="hero-title">
                <span class="accent">
                    AI로 더 빠르게
                </span>
                작성하고
                <br>

                <span class
