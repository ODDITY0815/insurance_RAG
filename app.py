import streamlit as st
import os
import re
import uuid
import time
import json
import zipfile
import gdown
from datetime import datetime
from dotenv import load_dotenv

# LangChain & Vector DB
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Recommendation System
import recommend

# ============================================================================
# 0. DB 자동 다운로드 (최초 실행 시)
# ============================================================================
def setup_vector_dbs():
    """Google Drive에서 Vector DB 다운로드 및 압축 해제"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_configs = [
        {"id": "1ttI_cujWXDOBFkD6WO_vlI21V3YGzgSB", "zip_name": "chroma_db_catalog.zip", "folder": "chroma_db_catalog"},
        {"id": "11D34U49KZwgJLnURnCu8K4p8kKjBlaL4", "zip_name": "chroma_db_clause.zip", "folder": "chroma_db_clause"}
    ]

    needed = [db for db in db_configs if not os.path.exists(os.path.join(base_path, db["folder"]))]
    
    if not needed:
        return True

    # 데이터가 없을 때만 화면에 상태 표시
    with st.status("🚀 최초 실행을 위한 데이터베이스 구성 중...", expanded=True) as status:
        for db in needed:
            st.write(f"📥 {db['folder']} 다운로드 중 (약 30초 소요)...")
            url = f'https://drive.google.com/uc?id={db["id"]}'
            zip_path = os.path.join(base_path, db["zip_name"])
            
            try:
                gdown.download(url, zip_path, quiet=False, fuzzy=True)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(base_path)
                os.remove(zip_path)
            except Exception as e:
                st.error(f"다운로드 실패: {e}")
                return False
        status.update(label="✅ 구성 완료! 서비스를 시작합니다.", state="complete", expanded=False)
    return True

# ============================================================================
# 1. 환경 설정 및 스타일링
# ============================================================================
load_dotenv()

st.set_page_config(
    page_title="현대해상 Hi-light",
    page_icon="💡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 모바일 앱 스타일 CSS
st.markdown("""
<style>
    /* Font & Base */
    @import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css");
    .stApp { font-family: 'Pretendard', sans-serif; background-color: #FFF8E1; }
    
    /* Header/Footer Hide */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Breadcrumb */
    .breadcrumb {
        background: linear-gradient(135deg, #E8EAF6 0%, #C5CAE9 100%);
        border-left: 5px solid #283593;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .breadcrumb-title {
        color: #1A237E;
        font-weight: 700;
        font-size: 13px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .breadcrumb-content {
        color: #283593;
        font-size: 14px;
        line-height: 1.6;
        font-weight: 500;
    }

    /* Hero Card */
    .hero-card {
        background-color: #ffffff;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(255, 159, 67, 0.15);
        border: 1px solid #FFE0B2;
        border-left: 5px solid #FF9F43;
        position: relative;
        overflow: hidden;
    }
    
    /* Situation Card */
    .situation-card {
        background: linear-gradient(135deg, #FFF8E1 0%, #FFE0B2 100%);
        border: 2px solid #FF9F43;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(255, 159, 67, 0.2);
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .situation-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 20px rgba(255, 159, 67, 0.3);
    }
    .situation-text {
        color: #37474F;
        font-size: 15px;
        line-height: 1.6;
        margin-bottom: 12px;
        font-weight: 500;
    }
    
    /* Mini Situation Card (3페이지용) */
    .mini-situation-card {
        background: white;
        border: 2px solid #E8EAF6;
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .mini-situation-card:hover {
        border-color: #283593;
        box-shadow: 0 4px 12px rgba(40, 53, 147, 0.2);
        transform: translateY(-2px);
    }
    .mini-situation-text {
        color: #37474F;
        font-size: 14px;
        line-height: 1.5;
    }
    
    /* Keyword Box */
    .keyword-box {
        background: linear-gradient(135deg, #E8EAF6 0%, #C5CAE9 100%);
        border-left: 5px solid #283593;
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
    }
    .keyword-title {
        color: #1A237E;
        font-weight: 700;
        font-size: 13px;
        margin-bottom: 8px;
    }
    .keyword-text {
        color: #283593;
        font-size: 14px;
        font-weight: 600;
    }
    
    /* Product Mini Card */
    .product-mini-card {
        background: white;
        border: 2px solid #FFE0B2;
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .product-mini-card:hover {
        border-color: #FF9F43;
        box-shadow: 0 4px 12px rgba(255, 159, 67, 0.2);
        transform: translateY(-2px);
    }
    .product-mini-title {
        color: #1A237E;
        font-size: 16px;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .product-mini-desc {
        color: #546E7A;
        font-size: 13px;
        line-height: 1.4;
    }
    
    .score-badge {
        position: absolute;
        top: 20px;
        right: 20px;
        background: #FFF3E0;
        color: #E65100;
        font-weight: 800;
        font-size: 14px;
        padding: 6px 12px;
        border-radius: 12px;
        border: 1px solid #FFCC80;
    }

    .hero-label {
        display: inline-block;
        background: linear-gradient(90deg, #FF9F43, #FFB74D);
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 12px;
        letter-spacing: 0.5px;
    }

    .product-title {
        color: #1A237E;
        margin: 0 0 10px 0;
        font-size: 20px;
        font-weight: 800;
        line-height: 1.3;
    }

    .summary-box {
        background-color: #FFFDE7;
        padding: 14px;
        border-radius: 12px;
        color: #37474F;
        font-size: 14px;
        line-height: 1.5;
        border-left: 4px solid #FFD54F;
        margin-top: 10px;
    }
    
    .tag-explain-box {
        background-color: #E8EAF6;
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        border: 1px solid #C5CAE9;
    }
    .tag-explain-title {
        color: #283593;
        font-weight: 700;
        font-size: 12px;
        margin-bottom: 4px;
    }
    .tag-explain-text {
        color: #1A237E;
        font-size: 13px;
        line-height: 1.4;
    }
    
    .no-result-card {
        background-color: #FFF3E0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        border: 2px dashed #FF9F43;
        text-align: center;
    }
    .no-result-icon { font-size: 48px; margin-bottom: 12px; }
    .no-result-title { color: #E65100; font-size: 18px; font-weight: 700; margin-bottom: 8px; }
    .no-result-text { color: #BF360C; font-size: 14px; line-height: 1.6; }
    
    .situation-prompt {
        background: linear-gradient(135deg, #FF9F43 0%, #FF6F00 100%);
        color: white;
        padding: 20px;
        border-radius: 16px;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(255, 159, 67, 0.4);
    }
    .situation-prompt h3 { margin: 0 0 8px 0; font-size: 16px; font-weight: 700; }
    .situation-prompt p { margin: 0 0 12px 0; font-size: 14px; opacity: 0.95; line-height: 1.5; }

    .easy-box {
        background-color: #E8EAF6;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 16px;
        border: 1px solid #C5CAE9;
    }
    .easy-label { color: #283593; font-weight: 700; font-size: 13px; margin-bottom: 6px; }
    .easy-text { color: #1A237E; font-size: 14px; line-height: 1.6; font-weight: 500; }

    .tag-container {
        display: flex; flex-wrap: wrap; gap: 8px; background-color: white; padding: 12px;
        border-radius: 12px; border: 1px solid #FFE0B2; margin-top: 10px; min-height: 50px;
    }
    .tag-chip {
        background-color: #FFF3E0; color: #E65100; padding: 6px 12px; border-radius: 20px;
        font-size: 13px; font-weight: 600; border: 1px solid #FFCC80;
    }
    .tag-placeholder { color: #90A4AE; font-size: 13px; align-self: center; }

    .stCheckbox {
        padding: 8px 12px; background-color: #FFFFFF; border-radius: 8px; border: 1px solid #FFE0B2; transition: all 0.2s ease;
    }
    .stCheckbox:hover { background-color: #FFF8E1; border-color: #FF9F43; }
    .stCheckbox > label { font-size: 13px; font-weight: 600; color: #37474F; }
    
    .stButton button[type="primary"] {
        background: linear-gradient(90deg, #FF9F43, #FF6F00) !important;
        color: white !important; border: none !important;
        box-shadow: 0 4px 10px rgba(255, 159, 67, 0.3) !important;
    }
    .stButton button[type="primary"]:hover {
        background: linear-gradient(90deg, #FF6F00, #E65100) !important;
        box-shadow: 0 6px 15px rgba(255, 159, 67, 0.4) !important;
    }
    div[data-testid="stLinkButton"] a {
        background: linear-gradient(90deg, #FF9F43, #FF6F00) !important;
        color: white !important; border: none !important;
        box-shadow: 0 4px 10px rgba(255, 159, 67, 0.3) !important;
    }

    .loading-text { font-size: 15px; color: #546E7A; font-weight: 500; text-align: center; margin-top: 15px; }
    
    .consultation-banner {
        background: linear-gradient(135deg, #FF9F43 0%, #FF6F00 100%);
        color: white; padding: 20px; border-radius: 16px; text-align: center; margin: 20px 0;
        box-shadow: 0 4px 15px rgba(255, 159, 67, 0.4);
    }
    .consultation-banner h3 { margin: 0 0 8px 0; font-size: 18px; font-weight: 700; }
    .consultation-banner p { margin: 0; font-size: 14px; opacity: 0.9; }
    
    /* 자연어 입력 박스 */
    .custom-input-box {
        background: white;
        border: 2px solid #FFE0B2;
        border-radius: 12px;
        padding: 16px;
        margin: 20px 0;
    }
    .custom-input-label {
        color: #E65100;
        font-weight: 700;
        font-size: 14px;
        margin-bottom: 10px;
        display: block;
    }
</style>

<script>
    window.addEventListener('load', function() {
        window.scrollTo(0, 0);
    });
</script>
""", unsafe_allow_html=True)

# ============================================================================
# 1.5. Global Data Load
# ============================================================================
def load_toc_data():
    toc_path = "toc_meta_summary.txt"
    if os.path.exists(toc_path):
        with open(toc_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "TOC Data Not Found."

if "global_toc_data" not in st.session_state:
    st.session_state.global_toc_data = load_toc_data()

PERSIST_DIR = "./chroma_db_clause"
CATALOG_DIR = "./chroma_db_catalog"
MODEL_NAME = "BAAI/bge-m3"
DEVICE = "cpu"

# ============================================================================
# 2. Data Constants
# ============================================================================

def get_tag_hierarchy():
    interests = recommend.get_all_interests()
    
    hierarchy = {
        "관심사": {},
        "누구": recommend.get_all_tags_by_category("누구"),
        "위험": recommend.get_all_tags_by_category("위험"),
        "우선순위": recommend.get_all_tags_by_category("우선순위"),
        "변화": recommend.get_all_tags_by_category("변화")
    }
    
    for interest in interests:
        hierarchy["관심사"][interest] = recommend.get_recommended_tags_for_interest(interest)
    
    return hierarchy

TAG_HIERARCHY = get_tag_hierarchy()

PRODUCT_LINKS = {
    "개인용 자동차보험": "https://www.hi.co.kr/serviceAction.do?menuId=100212",
    "간편한 3.10.10 건강보험(세만기형)": "https://www.hi.co.kr/serviceAction.do?menuId=202652",
    "간편한3·10·10건강보험": "https://www.hi.co.kr/serviceAction.do?menuId=202652",
    "골든타임 수술종합보험": "https://www.hi.co.kr/serviceAction.do?menuId=204360",
    "굿앤굿스타 종합보험(세만기형)": "https://www.hi.co.kr/serviceAction.do?menuId=100223",
    "굿앤굿 어린이종합보험Q": "https://www.hi.co.kr/serviceAction.do?menuId=100222",
    "내삶엔(3N) 맞춤간편 건강보험": "https://www.hi.co.kr/serviceAction.do?menuId=203552",
    "뉴하이카 운전자상해보험": "https://www.hi.co.kr/serviceAction.do?menuId=100215",
    "굿앤굿 우리펫보험": "https://www.hi.co.kr/serviceAction.do?menuId=202403",
    "퍼펙트플러스 종합보험(세만기형)": "https://www.hi.co.kr/serviceAction.do?menuId=202211",
    "행복가득 생활보장보험": "https://www.hi.co.kr/serviceAction.do?menuId=100242",
    "두배받는 암보험": "https://www.hi.co.kr/serviceAction.do?menuId=100224",
    "노후웰스보험": "https://www.hi.co.kr/serviceAction.do?menuId=100231"
}

# ============================================================================
# 3. Resource Loading
# ============================================================================
@st.cache_resource
def load_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={'device': DEVICE},
        encode_kwargs={'normalize_embeddings': True}
    )
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        return Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings, collection_name="insurance_rag")
    return None

@st.cache_resource
def load_catalog_vectorstore():
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={'device': DEVICE},
        encode_kwargs={'normalize_embeddings': True}
    )
    if os.path.exists(CATALOG_DIR) and os.listdir(CATALOG_DIR):
        return Chroma(persist_directory=CATALOG_DIR, embedding_function=embeddings, collection_name="insurance_catalog")
    return None

@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)

# Session State 초기화
if "step" not in st.session_state: st.session_state.step = 1
if "selected_interest" not in st.session_state: st.session_state.selected_interest = None
if "selected_tags" not in st.session_state: st.session_state.selected_tags = {"누구": [], "위험": [], "우선순위": [], "변화": []}
if "natural_language_inputs" not in st.session_state: st.session_state.natural_language_inputs = {"누구": "", "위험": "", "우선순위": "", "변화": ""}
if "free_text_input" not in st.session_state: st.session_state.free_text_input = ""
if "situation" not in st.session_state: st.session_state.situation = {"when": None, "where": None, "what": None, "text": ""}
if "catalog_result" not in st.session_state: st.session_state.catalog_result = None
if "generated_situations" not in st.session_state: st.session_state.generated_situations = []
if "selected_situation" not in st.session_state: st.session_state.selected_situation = None
if "selected_product_name" not in st.session_state: st.session_state.selected_product_name = None
if "keyword_analysis" not in st.session_state: st.session_state.keyword_analysis = None
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# ============================================================================
# 4. Analysis Engine
# ============================================================================

def preprocess_text(text):
    if not text:
        return ""
    
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</br>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'\|[\s-]+\|', '\n', text)
    text = text.replace('|', '  ')
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r' +', ' ', text)
    
    return text.strip()

# ============================================================================
# 4.1. 상황 질문 생성
# ============================================================================
def generate_situations_from_tags(llm, tags, natural_language_inputs, free_text):
    """태그 + 자연어 + 자유 입력 기반으로 3개의 질문 생성"""
    
    tag_descriptions = []
    for category, tag_list in tags.items():
        if tag_list:
            tag_descriptions.append(f"{category}: {', '.join(tag_list)}")
        
        nl_input = natural_language_inputs.get(category, "").strip()
        if nl_input:
            tag_descriptions.append(f"{category} (자연어): {nl_input}")
    
    if free_text.strip():
        tag_descriptions.append(f"자유 입력: {free_text}")
    
    tag_str = " | ".join(tag_descriptions)
    
    template = """당신은 보험 소비자의 일상적 고민을 이해하는 전문가입니다.

**[고객 선택 정보]**
{tags}

---
**[임무]**
위 태그 조합에서 발생할 수 있는 **일상적이고 구체적인 상황 3가지**를 생성하세요.

**[중요 원칙]**
1. **전문용어 사용 금지**: "배상책임", "면책", "특약" 같은 보험 용어 사용하지 말 것
2. **1인칭 시점**: "저는...", "제가..." 형식으로 작성
3. **구체적 상황**: 추상적이지 않고 실제 일어날 법한 사건
4. **길이 제한**: 각 질문은 50자 이내

**[출력 형식 - JSON Only]**
{{
    "situations": [
        "질문 1 (50자 이내, 전문용어 없이)",
        "질문 2 (50자 이내, 전문용어 없이)",
        "질문 3 (50자 이내, 전문용어 없이)"
    ]
}}
"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({"tags": tag_str})
    
    return response

# ============================================================================
# 4.2. 키워드 변환
# ============================================================================
def analyze_situation_to_keywords(llm, situation_text, tags):
    tag_str = ", ".join([f"{k}: {', '.join(v)}" for k, v in tags.items() if v])
    
    template = """당신은 보험 약관 전문가입니다.

**[고객의 질문]**
{situation}

**[선택된 태그]**
{tags}

---
**[임무]**
위 질문을 보험 약관에서 사용하는 **전문 키워드**로 변환하세요.

**[출력 형식 - JSON Only]**
{{
    "keywords": [
        {{"original": "일상 표현", "professional": "보험 전문용어", "explanation": "왜 이 용어인지 20자 이내 설명"}},
        {{"original": "일상 표현", "professional": "보험 전문용어", "explanation": "설명"}},
        {{"original": "일상 표현", "professional": "보험 전문용어", "explanation": "설명"}}
    ],
    "summary": "이 상황은 보험에서 어떤 영역인지 50자 이내 요약"
}}
"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({"situation": situation_text, "tags": tag_str})
    
    return response

# ============================================================================
# 4.3. 상품 추천
# ============================================================================
def recommend_products_for_situation(vectorstore, llm, situation_text, keywords_data):
    """키워드 기반으로 관련 상품 2~3개 추천"""
    
    try:
        keywords_obj = json.loads(keywords_data)
        professional_keywords = [k["professional"] for k in keywords_obj.get("keywords", [])]
        keyword_str = ", ".join(professional_keywords)
    except:
        keyword_str = situation_text
    
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(keyword_str)
    
    def format_docs(docs):
        return "\n".join([
            f"<상품 {i+1}>\n- 상품명: {d.metadata.get('source', '알 수 없음')}\n- 내용: {preprocess_text(d.page_content)[:400]}..."
            for i, d in enumerate(docs)
        ])
    
    template = """당신은 보험 상품 추천 전문가입니다.

**[고객 상황]**
{situation}

**[변환된 키워드]**
{keywords}

**[검색된 약관]**
{docs}

---
**[임무]**
위 상황에 적합한 **상품 2~3개**를 추천하세요.

**[중요]**
- product_name은 반드시 **파일 확장자(.txt) 없이** 순수 상품명만 출력하세요.
- 예: "무배당 현대해상 퍼펙트플러스 종합보험(세만기형)(Hi2508)" (O)

**[출력 형식 - JSON Only]**
{{
    "products": [
        {{
            "product_name": "순수 상품명 (확장자 제외)",
            "relevant_feature": "이 상황에 적합한 특약명",
            "why_suitable": "왜 이 상품이 적합한지 30자 이내",
            "match_score": 85
        }},
        {{
            "product_name": "상품명 2",
            "relevant_feature": "특약명",
            "why_suitable": "이유",
            "match_score": 75
        }}
    ]
}}
"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "situation": situation_text,
        "keywords": keyword_str,
        "docs": format_docs(docs)
    })
    
    return response

# ============================================================================
# 4.4. 상세 분석 (수정: Python 레벨 필터링으로 변경)
# ============================================================================
def analyze_tags_and_situation(vectorstore, llm, tags, situation_text, target_product_name=None):
    """
    상황 기반 분석 (특정 상품 약관에서만 검색)
    
    Args:
        target_product_name: 검색 대상 상품명 (None이면 전체 검색)
    """
    
    current_toc_summary = st.session_state.get("global_toc_data", "목차 데이터 없음")
    tag_str = ", ".join([f"{k}: {', '.join(v)}" for k, v in tags.items() if v])
    
    # Python 레벨 필터링 (Chroma DB 필터 대신)
    if target_product_name:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 30})  # 많이 검색
        all_docs = retriever.invoke(f"{situation_text} {tag_str}")
        
        # 상품명으로 필터링 (부분 매칭)
        docs = [d for d in all_docs if target_product_name in d.metadata.get('source', '')][:8]
        
        # 필터링 결과가 없으면 전체 검색 결과 사용
        if not docs:
            st.warning(f"⚠️ '{target_product_name}' 상품의 약관을 찾지 못해 전체 약관에서 검색합니다.")
            docs = all_docs[:8]
    else:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
        docs = retriever.invoke(f"{situation_text} {tag_str}")
    
    def format_docs_with_meta(docs):
        return "\n".join([f"<Chunk {i+1}>\n- Metadata: {d.metadata}\n- Content: {preprocess_text(d.page_content)[:600]}..." for i, d in enumerate(docs)])

    template = """당신은 보험 소비자의 이익을 최우선으로 하는 객관적인 '보상 분석관'입니다.

아래 제공된 정보를 바탕으로 사용자의 상황을 정밀 분석하세요.

**[전체 목차]** {toc_summary}
**[약관 증거]** {context}
**[사용자 정보]** 상황: {situation} / 태그: {tags}
{product_context}

---
**[분석 프로토콜]**
1. **매핑:** 사용자의 상황이 약관의 어느 조항에 해당하는지 찾으십시오.
2. **증거 발췌:** 해당 조항의 원문 텍스트를 그대로 발췌하십시오.
3. **한계점 식별:** 이 상품으로 해결되지 않는 한계점을 반드시 1개 이상 찾으십시오.
4. **점수 산출:** 상황과 약관의 일치도를 0~100점으로 산출.

---
**[최종 출력 형식 (JSON Only)]**
{{
    "product_name": "검증된 상품명",
    "feature_name": "핵심 특약명",
    "match_score": 95,
    "summary": "가정법을 사용한 보장 가능성 요약",
    "easy_explanation": "초등학생도 이해하는 쉬운 설명",
    "reasoning": "논리적 분석 내용",
    "evidence_snippet": "제N조(조항명)\\n① 항 내용...\\n② 항 내용...", 
    "limitations": "이 상품이 보장하지 않는 아쉬운 점",
    "checklist": ["확인할 점 1", "확인할 점 2"]
}}
"""
    
    product_context = f"\n**[분석 대상 상품]** {target_product_name}" if target_product_name else ""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = (
        {
            "tags": lambda x: tag_str,
            "situation": lambda x: situation_text,
            "context": lambda x: format_docs_with_meta(docs),
            "toc_summary": lambda x: current_toc_summary,
            "product_context": lambda x: product_context
        }
        | prompt | llm | StrOutputParser()
    )
    return chain.stream(situation_text)

# ============================================================================
# 4.5. 챗봇 응답 생성
# ============================================================================
def generate_chat_response(vectorstore, llm, question, analysis_context):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    relevant_docs = retriever.invoke(question)
    
    docs_context = "\n\n".join([
        f"[약관 {i+1}]\n상품: {doc.metadata.get('source', '알 수 없음')}\n내용: {preprocess_text(doc.page_content)[:500]}..."
        for i, doc in enumerate(relevant_docs)
    ])
    
    chat_template = """당신은 현대해상 보험 전문 상담 AI입니다.

**[이전 추천 분석 결과]**
{analysis_context}

**[검색된 관련 약관]**
{docs_context}

**[사용자 질문]**
{question}

---
**[답변 원칙]**
1. 위 약관 증거에 근거하여 답변하세요.
2. 약관에 명시되지 않은 내용은 "약관에서 확인되지 않습니다"라고 솔직히 말하세요.
3. 보장 여부는 가정법을 사용하세요.
4. 구체적인 조항명이나 특약명을 언급하여 신뢰성을 높이세요.
5. 친절하고 이해하기 쉽게 설명하세요.

답변:
"""
    
    prompt = ChatPromptTemplate.from_template(chat_template)
    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke({
        "analysis_context": analysis_context,
        "docs_context": docs_context,
        "question": question
    })
    
    return response

# ============================================================================
# 5. UI Rendering
# ============================================================================

def render_breadcrumb(step):
    """이전 작업 내용 표시"""
    if step == 1.5:
        all_selected = []
        for cat in st.session_state.selected_tags:
            all_selected.extend(st.session_state.selected_tags[cat])
        
        nl_texts = [f"💬 {v}" for v in st.session_state.natural_language_inputs.values() if v.strip()]
        
        if all_selected or nl_texts:
            tags_display = ", ".join(all_selected + nl_texts)
            st.markdown(f"""
            <div class="breadcrumb">
                <div class="breadcrumb-title">🏷️ 선택하신 정보</div>
                <div class="breadcrumb-content">{tags_display}</div>
            </div>
            """, unsafe_allow_html=True)
    
    elif step == 2.5:
        if st.session_state.selected_situation:
            st.markdown(f"""
            <div class="breadcrumb">
                <div class="breadcrumb-title">💭 선택하신 상황</div>
                <div class="breadcrumb-content">"{st.session_state.selected_situation}"</div>
            </div>
            """, unsafe_allow_html=True)
    
    elif step == 3:
        if st.session_state.selected_situation:
            st.markdown(f"""
            <div class="breadcrumb">
                <div class="breadcrumb-title">💭 분석 중인 상황</div>
                <div class="breadcrumb-content">"{st.session_state.selected_situation}"</div>
            </div>
            """, unsafe_allow_html=True)

def render_situation_cards(situations):
    """1단계: 3개의 상황 질문 카드 렌더링"""
    st.markdown("### 💭 저와 편하게 찾아봐요!")
    st.caption("궁금한 상황을 선택하면 보험 전문가가 분석해드립니다")
    
    for i, situation in enumerate(situations):
        st.markdown(f"""
        <div class="situation-card">
            <div class="situation-text">"{situation}"</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🔗 이런 고민 더 찾아보기", key=f"sit_{i}", use_container_width=True):
            st.session_state.selected_situation = situation
            st.session_state.step = 2.5
            st.session_state.step_start_time = time.time()
            
            recommend.log_user_action(
                visitor_id=st.session_state.visitor_id,
                consult_count=st.session_state.consult_count,
                open_time_str=st.session_state.open_time_str,
                action_type="situation_select",
                user_input=situation,
                recommended_product="",
                duration=time.time() - st.session_state.step_start_time
            )
            
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
            st.rerun()

def render_mini_situation_cards(situations, exclude_current=True):
    """3페이지용: 작은 상황 카드 렌더링"""
    st.markdown("### 💡 다른 고민도 찾아보시겠어요?")
    st.caption("클릭하면 해당 상황을 분석해드립니다")
    
    for i, situation in enumerate(situations):
        if exclude_current and situation == st.session_state.selected_situation:
            continue
        
        st.markdown(f"""
        <div class="mini-situation-card">
            <div class="mini-situation-text">"{situation}"</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"분석하기", key=f"mini_sit_{i}", use_container_width=True):
            st.session_state.selected_situation = situation
            st.session_state.keyword_analysis = None
            st.session_state.product_recommendations = None
            st.session_state.analysis_result = None
            st.session_state.selected_product_name = None
            st.session_state.step = 2.5
            st.session_state.step_start_time = time.time()
            
            recommend.log_user_action(
                visitor_id=st.session_state.visitor_id,
                consult_count=st.session_state.consult_count,
                open_time_str=st.session_state.open_time_str,
                action_type="situation_switch",
                user_input=situation,
                recommended_product="",
                duration=time.time() - st.session_state.step_start_time
            )
            
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
            st.rerun()

def render_keyword_analysis(keywords_data, situation_text):
    """2단계: 키워드 변환 결과"""
    try:
        json_str = keywords_data.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        
        st.markdown(f"""
        <div class="hero-card">
            <div class="hero-label">보험 키워드 분석</div>
            <h3 style="color:#1A237E; margin-bottom:16px;">선택하신 상황</h3>
            <p style="color:#546E7A; font-size:15px; line-height:1.6; margin-bottom:20px;">"{situation_text}"</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**🔑 보험 전문 키워드로 변환하면**")
        
        for keyword in data.get("keywords", []):
            st.markdown(f"""
            <div class="keyword-box">
                <div class="keyword-title">{keyword.get('original', '')}</div>
                <div class="keyword-text">→ {keyword.get('professional', '')} <span style="font-size:12px; opacity:0.8;">({keyword.get('explanation', '')})</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        summary = data.get("summary", "")
        if summary:
            st.info(f"📌 **요약**: {summary}")
            
    except json.JSONDecodeError as e:
        st.error("키워드 분석 결과 파싱 오류")
        with st.expander("🔍 디버그 정보", expanded=False):
            st.code(keywords_data)

def render_product_recommendations(products_data):
    """2단계 하단: 추천 상품 미니 카드"""
    try:
        json_str = products_data.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        
        products = data.get("products", [])
        
        if not products:
            st.warning("관련 상품을 찾지 못했습니다.")
            return
        
        st.markdown("---")
        st.markdown("### 📦 이런 상품이 도움이 될 수 있어요")
        
        for i, product in enumerate(products):
            raw_name = product.get("product_name", "상품명 없음")
            prod_name = raw_name.replace(".txt", "").replace("표준_", "").strip()
            
            feature = product.get("relevant_feature", "")
            why = product.get("why_suitable", "")
            score = product.get("match_score", 0)
            
            st.markdown(f"""
            <div class="product-mini-card">
                <div class="product-mini-title">{prod_name} <span style="color:#FF9F43; font-size:13px;">({score}% 적합)</span></div>
                <div class="product-mini-desc">
                    <strong>핵심 특약:</strong> {feature}<br>
                    <strong>적합 이유:</strong> {why}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"상세 분석 보기", key=f"prod_{i}", use_container_width=True):
                st.session_state.selected_product = product
                st.session_state.selected_product_name = prod_name
                st.session_state.step = 3
                st.session_state.step_start_time = time.time()
                
                st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
                st.rerun()
                
    except json.JSONDecodeError as e:
        st.error("상품 추천 결과 파싱 오류")
        with st.expander("🔍 디버그 정보", expanded=False):
            st.code(products_data)

def render_hero_card(data):
    """3단계: 상세 분석 결과 카드"""
    try:
        import html
        import re
        prod_name = str(data.get("product_name", "추천 상품"))
        score = int(data.get("match_score", 0))
        feature_name = str(data.get('feature_name', '특약 정보 없음'))
        summary = str(data.get('summary', '요약 정보 없음'))
        easy_explanation = str(data.get('easy_explanation', '설명 정보 없음'))
        reasoning = str(data.get('reasoning', '근거 정보 없음'))
        evidence_raw = str(data.get("evidence_snippet", "관련 약관 원문을 찾을 수 없습니다."))
        limitations = str(data.get("limitations", "특별한 한계점이 발견되지 않았습니다."))
        checklist = data.get('checklist', [])
        
        prod_name_safe = html.escape(prod_name)
        feature_name_safe = html.escape(feature_name)
        summary_safe = html.escape(summary)
        easy_explanation_safe = html.escape(easy_explanation)
        limitations_safe = html.escape(limitations)

        evidence_formatted = evidence_raw
        evidence_formatted = re.sub(r'(제\d+조\(.*?\))', r'<br><strong>\1</strong><br>', evidence_formatted)
        evidence_formatted = re.sub(r'([①-⑮])', r'<br>\1', evidence_formatted)
        evidence_formatted = re.sub(r'^<br>', '', evidence_formatted).strip()
        
        st.markdown(f"""
        <div class="hero-card">
            <div class="score-badge">{score}% 매칭</div>
            <div class="hero-label">AI 분석 결과</div>
            <h2 class="product-title">{prod_name_safe}</h2>
            <div style="color:#546E7A; font-size:14px; margin-bottom:12px;">
                💡 <span style="color:#F57C00; font-weight:700;">{feature_name_safe}</span> 특약이 상황에 가장 적합합니다.
            </div>
            <div class="summary-box">
                {summary_safe}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📜 분석 근거: 약관 원문 보기", expanded=False):
            st.markdown(f"""
            <div style="background-color:#FFFDE7; padding:15px; border-radius:8px; border:1px dashed #FFB74D; font-size:13px; color:#37474F; line-height:1.6;">
                {evidence_formatted}
            </div>
            <p style="font-size:12px; color:#90A4AE; margin-top:5px; text-align:right;">
                * 위 내용은 현대해상 실제 약관 데이터에 기반합니다.
            </p>
            """, unsafe_allow_html=True)
            
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="easy-box">
                <div class="easy-label">👶 3초 요약</div>
                <div class="easy-text">{easy_explanation_safe}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="easy-box" style="background-color: #FFF3E0; border-color: #FFCC80;">
                <div class="easy-label" style="color: #E65100;">⚠️ 유의할 점</div>
                <div class="easy-text" style="color: #BF360C;">{limitations_safe}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with st.expander("🔍 논리적 분석 내용 보기", expanded=False):
            st.write(reasoning)
            
        with st.expander("✅ 가입/청구 전 체크리스트", expanded=False):
            if checklist and isinstance(checklist, list):
                for i, item in enumerate(checklist):
                    st.checkbox(str(item), key=f"chk_{i}_{hash(str(item))}")
            else:
                st.info("체크리스트 항목이 없습니다.")
                
    except Exception as e:
        st.error(f"카드 렌더링 오류: {str(e)}")
        with st.expander("🔍 디버그 정보", expanded=False):
            st.json(data)

# ============================================================================
# 6. Main App Flow
# ============================================================================

def main():
    """메인 실행 함수"""
    
    # [중요] DB 자동 다운로드 (최초 실행 시)
    if not setup_vector_dbs():
        st.error("❌ 데이터베이스 로드에 실패했습니다. 관리자에게 문의하세요.")
        st.stop()
    
    # Vector Store 로드
    vectorstore = load_vectorstore()
    catalog_vectorstore = load_catalog_vectorstore()

    if not vectorstore:
        st.error("❌ 'chroma_db_clause' 폴더를 찾을 수 없습니다.")
        st.stop()

    if not catalog_vectorstore:
        st.warning("⚠️ 'chroma_db_catalog' 폴더를 찾을 수 없습니다.")

    llm = get_llm()

    if "recommend_initialized" not in st.session_state:
        recommend.initialize_recommendation_system()
        st.session_state.recommend_initialized = True

    # 세션 추적 변수
    if "visitor_id" not in st.session_state:
        st.session_state.visitor_id = str(uuid.uuid4())
    if "consult_count" not in st.session_state:
        st.session_state.consult_count = 0
    if "open_time_str" not in st.session_state:
        st.session_state.open_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "step_start_time" not in st.session_state:
        st.session_state.step_start_time = time.time()

    # --- Step 1: Interest & Tag Selection ---
    if st.session_state.step == 1:
        st.title("Hi-Pass")
        st.caption("일상적인 고민을 쉽게 찾아보는 AI")
        
        st.subheader("관심사를 선택해주세요")
        cols = st.columns(3)
        interests = list(TAG_HIERARCHY["관심사"].keys())
        for i, interest in enumerate(interests):
            with cols[i % 3]:
                is_selected = (st.session_state.selected_interest == interest)
                if st.button(interest, key=f"int_{i}", use_container_width=True, type="primary" if is_selected else "secondary"):
                    st.session_state.selected_interest = None if is_selected else interest
                    
                    recommend.log_user_action(
                        visitor_id=st.session_state.visitor_id,
                        consult_count=st.session_state.consult_count,
                        open_time_str=st.session_state.open_time_str,
                        action_type="interest_select",
                        user_input=interest if not is_selected else f"deselect: {interest}",
                        recommended_product="",
                        duration=time.time() - st.session_state.step_start_time
                    )
                    
                    st.rerun()
        
        if st.session_state.selected_interest:
            st.markdown("---")
            
            recommended = TAG_HIERARCHY["관심사"][st.session_state.selected_interest]
            all_tags_by_category = {
                "누구": TAG_HIERARCHY["누구"],
                "위험": TAG_HIERARCHY["위험"],
                "우선순위": TAG_HIERARCHY["우선순위"]
            }
            
            for category in ["누구", "위험", "우선순위"]:
                st.markdown(f"**{category}**")
                
                recommended_tags = recommended.get(category, [])
                other_tags = [t for t in all_tags_by_category[category] if t not in recommended_tags]
                all_tags = recommended_tags + other_tags
                
                display_tags = all_tags[:5]
                
                cols = st.columns(3)
                for i, tag in enumerate(display_tags):
                    with cols[i % 3]:
                        is_checked = tag in st.session_state.selected_tags[category]
                        
                        checked = st.checkbox(
                            tag,
                            value=is_checked,
                            key=f"chk_{category}_{i}"
                        )
                        
                        if checked and not is_checked:
                            st.session_state.selected_tags[category].append(tag)
                            
                            recommend.log_user_action(
                                visitor_id=st.session_state.visitor_id,
                                consult_count=st.session_state.consult_count,
                                open_time_str=st.session_state.open_time_str,
                                action_type="tag_select",
                                user_input=f"{category}: {tag}",
                                recommended_product="",
                                duration=time.time() - st.session_state.step_start_time
                            )
                        elif not checked and is_checked:
                            st.session_state.selected_tags[category].remove(tag)
                            
                            recommend.log_user_action(
                                visitor_id=st.session_state.visitor_id,
                                consult_count=st.session_state.consult_count,
                                open_time_str=st.session_state.open_time_str,
                                action_type="tag_deselect",
                                user_input=f"{category}: {tag}",
                                recommended_product="",
                                duration=time.time() - st.session_state.step_start_time
                            )
                
                nl_key = f"nl_{category}"
                nl_input = st.text_input(
                    f"💬 {category} 직접 입력",
                    value=st.session_state.natural_language_inputs.get(category, ""),
                    placeholder=f"편하게 말씀해주세요!",
                    key=nl_key
                )
                st.session_state.natural_language_inputs[category] = nl_input

        st.markdown("---")
        st.markdown("**🔖 선택된 태그**")
        
        all_selected = []
        for cat in st.session_state.selected_tags:
            all_selected.extend(st.session_state.selected_tags[cat])
        
        nl_texts = [f"💬 {v}" for v in st.session_state.natural_language_inputs.values() if v.strip()]
        
        if all_selected or nl_texts:
            chips_html = "".join([f'<span class="tag-chip">{t}</span>' for t in all_selected + nl_texts])
            st.markdown(f"""
            <div class="tag-container">
                {chips_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""<div class="tag-container"><span class="tag-placeholder">선택된 태그가 여기에 표시됩니다</span></div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        
        has_any_input = bool(all_selected) or any(v.strip() for v in st.session_state.natural_language_inputs.values())
        
        if st.button("어떤 고민이 있으신가요?", type="primary", disabled=not has_any_input, use_container_width=True):
            st.session_state.step = 1.5
            st.session_state.step_start_time = time.time()
            
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
            st.rerun()

    # --- Step 1.5: Generate Situations ---
    elif st.session_state.step == 1.5:
        render_breadcrumb(1.5)
        
        if not st.session_state.generated_situations:
            loading = st.empty()
            with loading.container():
                st.markdown("<br>", unsafe_allow_html=True)
                with st.spinner(""):
                    status = st.markdown('<p class="loading-text">💭 고객님의 상황을 정리하고 있습니다...</p>', unsafe_allow_html=True)
                    
                    response = generate_situations_from_tags(
                        llm,
                        st.session_state.selected_tags,
                        st.session_state.natural_language_inputs,
                        st.session_state.free_text_input
                    )
                    
                    time.sleep(1)
                    status.markdown('<p class="loading-text">✨ 질문 생성 완료!</p>', unsafe_allow_html=True)
                    time.sleep(0.5)
                    
                    try:
                        json_str = response.replace("```json", "").replace("```", "").strip()
                        data = json.loads(json_str)
                        st.session_state.generated_situations = data.get("situations", [])
                    except json.JSONDecodeError as e:
                        st.error("질문 생성 오류")
                        st.code(response)
                        st.session_state.generated_situations = ["오류가 발생했습니다."]
                    
                    recommend.log_user_action(
                        visitor_id=st.session_state.visitor_id,
                        consult_count=st.session_state.consult_count,
                        open_time_str=st.session_state.open_time_str,
                        action_type="situations_generated",
                        user_input=str(st.session_state.generated_situations),
                        recommended_product="",
                        duration=time.time() - st.session_state.step_start_time
                    )
                    
            loading.empty()
            st.rerun()
        
        render_situation_cards(st.session_state.generated_situations)
        
        # 자연어 입력 추가
        st.markdown("---")
        st.markdown("""
        <div class="custom-input-box">
            <span class="custom-input-label">✍️ 또는 자유롭게 상황을 입력해주세요</span>
        </div>
        """, unsafe_allow_html=True)
        
        free_text = st.text_area(
            "상황을 자유롭게 적어주세요",
            value=st.session_state.free_text_input,
            height=100,
            placeholder="예: 주말에 축구하다가 다리가 부러졌어요.",
            key="free_text_area_15"
        )
        st.session_state.free_text_input = free_text
        
        if st.button("이 상황으로 찾기 🔍", type="primary", disabled=not free_text.strip(), use_container_width=True):
            st.session_state.selected_situation = free_text
            st.session_state.step = 2.5
            st.session_state.step_start_time = time.time()
            
            recommend.log_user_action(
                visitor_id=st.session_state.visitor_id,
                consult_count=st.session_state.consult_count,
                open_time_str=st.session_state.open_time_str,
                action_type="free_text_submit",
                user_input=free_text,
                recommended_product="",
                duration=time.time() - st.session_state.step_start_time
            )
            
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
            st.rerun()
        
        st.markdown("---")
        if st.button("⬅️ 처음으로", use_container_width=True):
            visitor_id_backup = st.session_state.visitor_id
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.visitor_id = visitor_id_backup
            st.session_state.open_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.step_start_time = time.time()
            st.rerun()

    # --- Step 2.5: Keyword Analysis + Product Recommendation ---
    elif st.session_state.step == 2.5:
        render_breadcrumb(2.5)
        
        if not st.session_state.keyword_analysis:
            loading = st.empty()
            with loading.container():
                st.markdown("<br>", unsafe_allow_html=True)
                with st.spinner(""):
                    status = st.markdown('<p class="loading-text">📦 고객님의 고민을 이해하는 중...</p>', unsafe_allow_html=True)
                    
                    keyword_response = analyze_situation_to_keywords(
                        llm,
                        st.session_state.selected_situation,
                        st.session_state.selected_tags
                    )
                    
                    time.sleep(1)
                    status.markdown('<p class="loading-text">🔍 보험 전문 키워드로 변환 중...</p>', unsafe_allow_html=True)
                    
                    product_response = recommend_products_for_situation(
                        vectorstore,
                        llm,
                        st.session_state.selected_situation,
                        keyword_response
                    )
                    
                    status.markdown('<p class="loading-text">✨ 분석 완료!</p>', unsafe_allow_html=True)
                    time.sleep(0.5)
                    
                    st.session_state.keyword_analysis = keyword_response
                    st.session_state.product_recommendations = product_response
                    
            loading.empty()
            st.rerun()
        
        render_keyword_analysis(st.session_state.keyword_analysis, st.session_state.selected_situation)
        render_product_recommendations(st.session_state.product_recommendations)
        
        st.markdown("---")
        if st.button("⬅️ 다른 질문 보기", use_container_width=True):
            st.session_state.keyword_analysis = None
            st.session_state.product_recommendations = None
            st.session_state.selected_situation = None
            st.session_state.step = 1.5
            
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
            st.rerun()

    # --- Step 3: Deep Analysis ---
    elif st.session_state.step == 3:
        render_breadcrumb(3)
        
        if not st.session_state.analysis_result:
            loading = st.empty()
            with loading.container():
                st.markdown("<br>", unsafe_allow_html=True)
                with st.spinner(""):
                    status = st.markdown('<p class="loading-text">📚 약관 책장에서 관련 페이지 찾는 중...</p>', unsafe_allow_html=True)
                    
                    # 특정 상품 약관에서만 검색
                    stream = analyze_tags_and_situation(
                        vectorstore,
                        llm,
                        st.session_state.selected_tags,
                        st.session_state.selected_situation,
                        target_product_name=st.session_state.selected_product_name
                    )
                    
                    time.sleep(1)
                    status.markdown('<p class="loading-text">🖍️ 보장 범위에 형광펜 칠하는 중...</p>', unsafe_allow_html=True)
                    
                    full_res = ""
                    for chunk in stream:
                        full_res += chunk
                    
                    status.markdown('<p class="loading-text">✨ 분석 완료!</p>', unsafe_allow_html=True)
                    time.sleep(0.5)
                    
                    st.session_state.analysis_result = full_res
                    
                    recommend.log_user_action(
                        visitor_id=st.session_state.visitor_id,
                        consult_count=st.session_state.consult_count,
                        open_time_str=st.session_state.open_time_str,
                        action_type="deep_analysis_complete",
                        user_input=st.session_state.selected_situation,
                        recommended_product=st.session_state.selected_product_name,
                        duration=time.time() - st.session_state.step_start_time
                    )
                    
                    st.session_state.consult_count += 1
                    
            loading.empty()
            st.rerun()

        try:
            json_str = st.session_state.analysis_result.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            
            render_hero_card(data)
            
            st.markdown("---")
            
            if "consultation_submitted" not in st.session_state:
                st.session_state.consultation_submitted = False
            
            if not st.session_state.consultation_submitted:
                st.markdown("""
                <div class="consultation-banner">
                    <h3>📞 전문 상담사와 1:1 상담하기</h3>
                    <p>클릭 한 번으로 상담 신청 완료! 24시간 내 연락드립니다.</p>
                </div>
                """, unsafe_allow_html=True)
                
                col_left, col_center, col_right = st.columns([1, 2, 1])
                with col_center:
                    if st.button("📞 바로 상담 신청하기", use_container_width=True, type="primary", key="quick_consult"):
                        try:
                            user_name = f"고객_{st.session_state.visitor_id[:8]}"
                            user_phone = "연락처 미입력"
                            user_email = "이메일 미입력"
                            
                            product_name = data.get("product_name", "알 수 없음")
                            
                            success = recommend.log_consultation_request(
                                visitor_id=st.session_state.visitor_id,
                                consult_count=st.session_state.consult_count,
                                open_time_str=st.session_state.open_time_str,
                                recommended_product=product_name,
                                user_name=user_name,
                                user_phone=user_phone,
                                user_email=user_email,
                                preferred_time="언제든지 가능"
                            )
                            
                            if success or success is None:
                                st.session_state.consultation_submitted = True
                                st.rerun()
                            else:
                                st.error("상담 신청 중 오류가 발생했습니다.")
                                
                        except Exception as e:
                            st.error(f"상담 신청 오류: {str(e)}")
            
            else:
                st.success("✅ 상담 신청이 완료되었습니다!")
                st.info(f"""
                **📌 다음 단계**
                - 방문자 ID: `{st.session_state.visitor_id[:16]}...`
                - 추천 상품: **{data.get('product_name', '알 수 없음')}**
                - 영업일 기준 24시간 내에 전문 상담사가 연락드립니다.
                """)
            
        except json.JSONDecodeError as e:
            st.error("❌ 분석 결과 형식 오류")
            with st.expander("🔍 상세 오류 정보", expanded=False):
                st.code(f"JSON 파싱 오류: {str(e)}\n\n원본 데이터:\n{st.session_state.analysis_result}", language="text")

        st.markdown("---")
        
        st.subheader("💬 AI 상담사")
        st.caption("추천 상품뿐만 아니라 모든 약관 정보를 검색하여 답변드립니다.")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("추가로 궁금한 점을 물어보세요!"):
            recommend.log_user_action(
                visitor_id=st.session_state.visitor_id,
                consult_count=st.session_state.consult_count,
                open_time_str=st.session_state.open_time_str,
                action_type="chat_question",
                user_input=prompt,
                recommended_product="",
                duration=time.time() - st.session_state.step_start_time
            )
            
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("약관을 검색하여 답변을 준비하고 있습니다..."):
                    response = generate_chat_response(
                        vectorstore=vectorstore,
                        llm=llm,
                        question=prompt,
                        analysis_context=st.session_state.analysis_result
                    )
                    st.markdown(response)
                    
            st.session_state.chat_history.append({"role": "assistant", "content": response})

        # 다른 질문 탐색 섹션
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.session_state.generated_situations:
            render_mini_situation_cards(st.session_state.generated_situations, exclude_current=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🔄 처음으로 돌아가기", use_container_width=True):
            visitor_id_backup = st.session_state.visitor_id
            
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.session_state.visitor_id = visitor_id_backup
            st.session_state.open_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.step_start_time = time.time()
            
            st.markdown('<script>window.scrollTo(0, 0);</script>', unsafe_allow_html=True)
            st.rerun()

    # ============================================================================
    # 7. 공통 푸터 (면책 조항)
    # ============================================================================
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style='background-color: #FFFDE7; padding: 20px; border-radius: 10px; color: #546E7A; font-size: 12px; line-height: 1.6; border: 1px solid #FFE0B2;'>
        <strong>[면책 조항 및 유의사항]</strong><br>
        <ul>
            <li>본 서비스는 인공지능(AI) 기술을 활용하여 보험 약관 및 상품 설명서 데이터를 기반으로 정보를 제공하는 참고용 서비스입니다.</li>
            <li>제공되는 추천 결과 및 분석 내용은 보험 모집을 위한 법적 효력이 있는 청약 권유가 아니며, 실제 가입 가능 여부나 보장 내용은 개인의 조건에 따라 달라질 수 있습니다.</li>
            <li>AI의 답변은 부정확하거나 시의성이 떨어질 수 있으므로, 정확한 내용은 반드시 <strong>현대해상 공식 약관 및 상품 설명서</strong>를 확인하시거나 전문 상담사와 상의하시기 바랍니다.</li>
            <li>본 서비스의 결과만을 신뢰하여 발생한 손해에 대해서는 회사가 책임을 지지 않습니다.</li>
        </ul>
        <div style='text-align: center; margin-top: 10px; color: #90A4AE;'>
            &copy; 2026 현대해상 Hi-light AI Service. All rights reserved.
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
