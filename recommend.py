import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials

# ============================================================================
# 1. 설정 및 상수
# ============================================================================
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SPREADSHEET_NAME = 'Hipass_db'
SHEET_USER_LOG = '사용자_로그'
SHEET_CONSULT_LOG = '상담_신청'
LOCAL_LOG_FILE = "local_log.xlsx"

# ============================================================================
# 2. 고정 태그맵 (룰베이스)
# ============================================================================
INTEREST_TAG_MAP = {
    "MZ_사회초년생_Pick": {
        "누구": ["#사회초년생", "#2030세대", "#1인가구", "#독립준비생"],
        "위험": ["#생활비부족", "#예기치못한상해", "#전세사기위험", "#우울증/마음건강"],
        "우선순위": ["#가성비_보험료", "#세액공제효과", "#스마트폰가입", "#유연한납입"],
        "변화": ["#첫출근", "#독립", "#연봉협상"]
    },
    "골든에이지_시니어케어": {
        "누구": ["#부모님", "#고령자", "#은퇴준비자", "#활동적시니어"],
        "위험": ["#간병인사용", "#치매케어", "#낙상/골절", "#대상포진/질병"],
        "우선순위": ["#간편가입(유병자)", "#정기적건강검진", "#보장한도확대", "#가족통합보장"],
        "변화": ["#환갑/칠순", "#손주탄생", "#퇴직"]
    },
    "DINK_맞벌이부부_자산관리": {
        "누구": ["#맞벌이부부", "#무자녀가정", "#고소득자", "#부부통합관리"],
        "위험": ["#소득단절리스크", "#노후생활비부족", "#자산손실", "#암/중증질환"],
        "우선순위": ["#연금액_지급", "#복리효과", "#종합자산보장", "#세제혜택최대화"],
        "변화": ["#결혼기념일", "#부동산매입", "#해외장기체류"]
    },
    "세상_모든_집사_모여라": {
        "누구": ["#반려견", "#반려묘", "#노령펫", "#다펫가정"],
        "위험": ["#슬개골/관절염", "#피부질환", "#구강케어", "#배상책임(물림사고)"],
        "우선순위": ["#다빈도질병보상", "#보험료할인특약", "#실시간청구", "#예방접종지원"],
        "변화": ["#반려동물입양", "#노령기진입", "#이사"]
    },
    "초보부터_베테랑까지_드라이빙": {
        "누구": ["#초보운전자", "#고령운전자", "#가족운전자", "#업무용운전자"],
        "위험": ["#교통사고처리지원금", "#벌금/변호사비용", "#보복운전피해", "#자동차사고상해"],
        "우선순위": ["#안전운전UBI할인", "#커넥티드카할인", "#신속한긴급출동", "#민사/형사합의금"],
        "변화": ["#신차출고", "#중고차구매", "#면허취득"]
    },
    "성장기_아이를_위한_든든함": {
        "누구": ["#태아/산모", "#영유아", "#초등학생", "#다자녀가정"],
        "위험": ["#선천이상", "#성장기질병(호흡기)", "#학교/학원사고", "#아토피/피부질환"],
        "우선순위": ["#성장단계별보장", "#교육자금마련", "#납입면제", "#어린이전용서비스"],
        "변화": ["#출산예정", "#유치원/학교입학", "#이사"]
    },
    "주말_레저_프로취미러": {
        "누구": ["#골프매니아", "#등산/캠핑족", "#해외여행족", "#레저활동여행자"],
        "위험": ["#홀인원축하금", "#장비도난/파손", "#산행중사고", "#휴대품손해"],
        "우선순위": ["#하루단기가입", "#종합레저보장", "#실속형보험료", "#간편한청구"],
        "변화": ["#시즌오픈", "#대회참가", "#해외출국"]
    },
    "사장님_사업장_안심케어": {
        "누구": ["#소상공인", "#카페/음식점운영", "#다중이용시설관리자", "#창업준비생"],
        "위험": ["#화재손해", "#시설배상책임", "#음식물사고", "#영업중단손실"],
        "우선순위": ["#의무보험가입", "#저렴한화재보험", "#신속한피해보상", "#법률컨설팅"],
        "변화": ["#오픈기념", "#사업확장", "#내집마련"]
    }
}

# ============================================================================
# 3. 데이터 로드 및 UI 지원 함수
# ============================================================================
def load_catalog_tags():
    catalog_file = "catalog_tags.json"
    if not os.path.exists(catalog_file):
        return {"product_tags": {}, "all_tags": {}}
    try:
        with open(catalog_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"product_tags": {}, "all_tags": {}}

CATALOG_DATA = load_catalog_tags()

def get_catalog_product_tags() -> dict:
    return CATALOG_DATA.get("product_tags", {})

def get_recommended_tags_for_interest(interest: str) -> dict:
    full_tags = INTEREST_TAG_MAP.get(interest, {})
    recommended = {}
    for category, tags in full_tags.items():
        recommended[category] = tags[:4]
    return recommended

def get_all_tags_by_category(category: str) -> list:
    all_tags = set()
    for interest_tags in INTEREST_TAG_MAP.values():
        if category in interest_tags:
            all_tags.update(interest_tags[category])
    return sorted(list(all_tags))

def get_all_interests() -> list:
    return list(INTEREST_TAG_MAP.keys())

# ============================================================================
# 4. 추천 및 유사도 로직
# ============================================================================
def calculate_tag_similarity(user_tags: List[str], product_tags: List[str]) -> float:
    if not user_tags or not product_tags: return 0.0
    score = 0.0
    user_tags_set = set(user_tags)
    product_tags_set = set(product_tags)
    score += len(user_tags_set & product_tags_set) * 1.0
    for user_tag in user_tags:
        u_kw = user_tag.replace("#", "").lower()
        for p_tag in product_tags:
            if user_tag == p_tag: continue
            p_kw = p_tag.replace("#", "").lower()
            if u_kw in p_kw or p_kw in u_kw:
                score += 0.5
                break
    return score

def get_product_by_tags(selected_tags: Dict[str, List[str]]) -> Optional[str]:
    p_tags_db = CATALOG_DATA.get("product_tags", {})
    if not p_tags_db: return None
    u_tags_flat = [tag for tags in selected_tags.values() for tag in tags]
    
    best_match, best_score = None, 0.0
    for p_name, p_data in p_tags_db.items():
        p_tags_flat = []
        for tags in p_data.get("tags", {}).values(): p_tags_flat.extend(tags)
        
        sim = calculate_tag_similarity(u_tags_flat, p_tags_flat)
        risk_match = len(set(selected_tags.get("위험", [])) & set(p_data.get("tags", {}).get("위험", [])))
        final_score = sim + (risk_match * 0.5)
        
        if final_score > best_score:
            best_score, best_match = final_score, p_name
            
    return best_match if best_score >= 1.5 else None

# ============================================================================
# 5. 로컬 엑셀 저장
# ============================================================================
def _log_to_local_excel(sheet_name: str, row_data: list, columns: list):
    try:
        new_df = pd.DataFrame([row_data], columns=columns)
        
        if os.path.exists(LOCAL_LOG_FILE):
            try:
                with pd.ExcelFile(LOCAL_LOG_FILE, engine='openpyxl') as xls:
                    all_dfs = {}
                    for sn in xls.sheet_names:
                        df = pd.read_excel(xls, sheet_name=sn)
                        df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
                        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
                        all_dfs[sn] = df
            except Exception:
                all_dfs = {}

            if sheet_name in all_dfs:
                all_dfs[sheet_name] = pd.concat([all_dfs[sheet_name], new_df], ignore_index=True)
            else:
                all_dfs[sheet_name] = new_df

            with pd.ExcelWriter(LOCAL_LOG_FILE, engine='openpyxl') as writer:
                for sn, df in all_dfs.items():
                    df.to_excel(writer, sheet_name=sn, index=False)
        else:
            new_df.to_excel(LOCAL_LOG_FILE, sheet_name=sheet_name, index=False, engine='openpyxl')
    except Exception as e:
        print(f"❌ [로컬] 기록 실패: {e}")

# ============================================================================
# 6. 구글 시트 연동 및 통합 로깅 (수정됨)
# ============================================================================
def get_sheets_client():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception: return None

def get_or_create_sheet(client, sheet_name: str):
    if client is None: return None
    try:
        ss = client.open(SPREADSHEET_NAME)
        try: return ss.worksheet(sheet_name)
        except gspread.WorksheetNotFound: return ss.add_worksheet(title=sheet_name, rows=1000, cols=20)
    except Exception: return None

def log_user_action(visitor_id, consult_count, open_time_str, action_type, user_input="", recommended_product="", duration=0.0):
    action_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [visitor_id, consult_count, open_time_str, action_time, action_type, user_input, recommended_product, round(duration, 2)]
    headers = ['visitor_id', 'consult_count', 'open_time', 'action_time', 'action_type', 'user_input', 'recommended_product', 'duration_sec']
    
    try:
        client = get_sheets_client()
        ws = get_or_create_sheet(client, SHEET_USER_LOG)
        if ws:
            # [해결] append_row 대신 append_rows([[row]]) 사용
            # 리스트를 한 번 더 감싸면(2차원 배열), 구글 시트가 항상 A열부터 채웁니다.
            ws.append_rows([row], value_input_option='USER_ENTERED')
    except Exception as e:
        print(f"❌ [구글시트] 기록 실패: {e}")
    
    _log_to_local_excel(SHEET_USER_LOG, row, headers)

def log_consultation_request(visitor_id, consult_count, open_time_str, recommended_product, user_name="", user_phone="", user_email="", preferred_time=""):
    req_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [req_time, visitor_id, consult_count, open_time_str, recommended_product, user_name, user_phone, user_email, preferred_time, '대기중']
    headers = ['request_time', 'visitor_id', 'consult_count', 'session_start', 'recommended_product', 'name', 'phone', 'email', 'preferred_time', 'status']
    
    try:
        client = get_sheets_client()
        ws = get_or_create_sheet(client, SHEET_CONSULT_LOG)
        if ws:
            if not ws.get_all_values():
                ws.append_row(headers, value_input_option='USER_ENTERED')
            
            # [핵심 수정] 계단 현상 방지를 위해 옵션 강제 적용
            ws.append_row(
                row, 
                value_input_option='USER_ENTERED', 
                insert_data_option='INSERT_ROWS'
            )
    except Exception: pass
    
    _log_to_local_excel(SHEET_CONSULT_LOG, row, headers)
    return True

# ============================================================================
# 7. 초기화 및 외부 호출 함수
# ============================================================================
def get_recommendation(interest: str, selected_tags: Dict[str, List[str]], situation_text: str = "") -> Optional[str]:
    return get_product_by_tags(selected_tags)

def initialize_recommendation_system():
    print(f"✅ 시스템 초기화 완료 (로그: {LOCAL_LOG_FILE})")

if __name__ == "__main__":
    initialize_recommendation_system()
