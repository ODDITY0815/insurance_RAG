# recommend.py
import os
import json
import pandas as pd  # 로컬 엑셀 저장을 위해 추가
from datetime import datetime
from typing import Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials

# ============================================================================
# 설정
# ============================================================================
# Google Sheets 설정
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_NAME = 'Hilight_db'

# 시트 이름
SHEET_USER_LOG = '사용자_로그'
SHEET_CONSULT_LOG = '상담_신청'

# [추가] 로컬 로그 파일 설정
LOCAL_LOG_FILE = "local_log.xlsx"

# ============================================================================
# 고정 태그맵 (룰베이스) - 기존과 동일
# ============================================================================

INTEREST_TAG_MAP = {
    "자녀/육아": {
        "누구": ["#우리_아이", "#자녀", "#태아", "#산모", "#가족", "#0세", "#15세", "#30세", "#만12세이하자녀"],
        "위험": ["#학교폭력", "#학교폭력피해치료", "#선천이상", "#성장단계별보장", "#일상_생활책임", "#화상", "#골절", "#질병"],
        "우선순위": ["#성장단계별보장", "#폭넓은보장", "#납입면제", "#건강관리서비스", "#어린이할인특약"],
        "변화": ["#자녀입학", "#출산예정"]
    },
    "운전": {
        "누구": ["#운전자", "#나", "#현대차_블루링크_가입고객", "#기아_커넥트_서비스_가입고객", "#제네시스_커넥티드_서비스_가입고객", "#KG_MOBILITY_인포콘_서비스_가입고객", "#르노코리아_서비스_가입고객", "#메르세데스벤츠_Mercedes_me_서비스_가입고객"],
        "위험": ["#교통사고", "#자동차사고", "#자동차사고벌금", "#변호사선임비용", "#형사합의금", "#면허정지", "#면허취소", "#자동차사고처리지원금"],
        "우선순위": ["#안전운전할인", "#블랙박스할인특약", "#커넥티드카할인특약", "#스마트안전운전UBI할인특약", "#첨단안전장치장착할인특약", "#Eco마일리지특약", "#대중교통이용할인특약"],
        "변화": ["#신차출고"]
    },
    "주택/부동산": {
        "누구": ["#주택소유자", "#다주택자", "#가족"],
        "위험": ["#화재", "#누수_화재", "#가전제품고장", "#일상_생활책임", "#배상책임", "#도난/파손"],
        "우선순위": ["#폭넓은보장", "#가성비_보험료"],
        "변화": ["#이사", "#내집마련"]
    },
    "반려동물": {
        "누구": ["#반려견", "#반려묘"],
        "위험": ["#피부질환", "#구강질환", "#슬개골", "#배상책임", "#입원치료비", "#통원치료비", "#상해", "#질병"],
        "우선순위": ["#보험료할인", "#특정처치보장", "#특정약물치료보장", "#다빈도질병보상"],
        "변화": ["#반려동물입양"]
    },
    "여행/레저": {
        "누구": ["#나", "#가족"],
        "위험": ["#상해", "#골절", "#화상", "#상해후유장해", "#배상책임", "#휴대품손해"],
        "우선순위": ["#종합보장", "#가성비_보험료"],
        "변화": []
    },
    "건강": {
        "누구": ["#나", "#부모님", "#가족", "#40세", "#60세"],
        "위험": ["#암_중증질환", "#뇌혈관질환", "#심장질환", "#허혈심장질환", "#수술_입원비", "#진단비", "#치료비", "#항암약물치료", "#방사선치료", "#전이암", "#간병인사용", "#질병", "#3대질병", "#사망", "#후유장해", "#치매"],
        "우선순위": ["#100세보장", "#간편가입", "#가성비_보험료", "#든든한_진단비", "#매년_주요치료비_지급", "#유병자도가입가능", "#종합보장", "#연금액_지급", "#노후준비"],
        "변화": ["#유병자경력", "#건강검진예정", "#노후준비"]
    }
}

# ============================================================================
# 카탈로그 데이터 로드
# ============================================================================
def load_catalog_tags():
    catalog_file = "catalog_tags.json"
    if not os.path.exists(catalog_file):
        return {"product_tags": {}, "all_tags": {}}
    try:
        with open(catalog_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return {"product_tags": {}, "all_tags": {}}

CATALOG_DATA = load_catalog_tags()

# ============================================================================
# UI 지원 함수
# ============================================================================
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

def get_catalog_product_tags() -> dict:
    return CATALOG_DATA.get("product_tags", {})

# ============================================================================
# 태그 유사도 계산 및 추천 로직
# ============================================================================
def calculate_tag_similarity(user_tags: List[str], product_tags: List[str]) -> float:
    if not user_tags or not product_tags: return 0.0
    score = 0.0
    user_tags_set = set(user_tags)
    product_tags_set = set(product_tags)
    score += len(user_tags_set & product_tags_set) * 1.0
    for user_tag in user_tags:
        user_keyword = user_tag.replace("#", "").lower()
        for product_tag in product_tags:
            if user_tag == product_tag: continue
            product_keyword = product_tag.replace("#", "").lower()
            if user_keyword in product_keyword or product_keyword in user_keyword:
                score += 0.5
                break
    return score

def get_product_by_tags(selected_tags: Dict[str, List[str]]) -> Optional[str]:
    product_tags = CATALOG_DATA.get("product_tags", {})
    if not product_tags: return None
    user_tags_flat = []
    for category, tags in selected_tags.items():
        user_tags_flat.extend(tags)
    if not user_tags_flat: return None
    
    best_match = None
    best_score = 0.0
    for product_name, product_data in product_tags.items():
        product_tags_flat = []
        for category, tags in product_data.get("tags", {}).items():
            product_tags_flat.extend(tags)
        similarity = calculate_tag_similarity(user_tags_flat, product_tags_flat)
        risk_tags_user = set(selected_tags.get("위험", []))
        risk_tags_product = set(product_data.get("tags", {}).get("위험", []))
        risk_match = len(risk_tags_user & risk_tags_product)
        final_score = similarity + (risk_match * 0.5)
        if final_score > best_score:
            best_score = final_score
            best_match = product_name
    
    if best_score >= 1.5: return best_match
    else: return None

# ============================================================================
# [추가] 로컬 엑셀 저장 함수
# ============================================================================
def _log_to_local_excel(sheet_name: str, row_data: list, columns: list):
    """로컬 엑셀 파일에 로그를 추가하는 함수"""
    try:
        new_df = pd.DataFrame([row_data], columns=columns)
        
        if os.path.exists(LOCAL_LOG_FILE):
            # 파일이 있으면 기존 데이터 로드 후 병합
            try:
                # 모든 시트를 읽어옵니다.
                dfs = pd.read_excel(LOCAL_LOG_FILE, sheet_name=None)
                
                if sheet_name in dfs:
                    # 해당 시트가 있으면 데이터 추가
                    dfs[sheet_name] = pd.concat([dfs[sheet_name], new_df], ignore_index=True)
                else:
                    # 해당 시트가 없으면 새로 생성
                    dfs[sheet_name] = new_df
                
                # 모든 시트를 다시 저장합니다.
                with pd.ExcelWriter(LOCAL_LOG_FILE, engine='openpyxl') as writer:
                    for s_name, df in dfs.items():
                        df.to_excel(writer, sheet_name=s_name, index=False)
                        
            except Exception as e:
                print(f"❌ [로컬] 파일 읽기/쓰기 오류 (재시도): {e}")
                # 오류 발생 시 새 파일로 덮어쓰거나 무시 (데이터 무결성 위해)
        else:
            # 파일이 없으면 새로 생성
            with pd.ExcelWriter(LOCAL_LOG_FILE, engine='openpyxl') as writer:
                new_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
        print(f"✅ [로컬] 엑셀 기록 완료: {sheet_name}")
    except Exception as e:
        print(f"❌ [로컬] 엑셀 기록 실패: {e}")

# ============================================================================
# Google Sheets 클라이언트
# ============================================================================
def get_sheets_client():
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE): return None
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception: return None

def get_or_create_sheet(client, sheet_name: str):
    if client is None: return None
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SPREADSHEET_NAME)
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        # 헤더 설정은 아래 로깅 함수에서 처리하지 않으므로 초기 생성 시는 빈 시트
        return worksheet

# ============================================================================
# 사용자 로그 기록 (통합)
# ============================================================================
def log_user_action(visitor_id, consult_count, open_time_str, action_type, user_input="", recommended_product="", duration=0.0):
    action_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [visitor_id, consult_count, open_time_str, action_time, action_type, user_input, recommended_product, round(duration, 2)]
    headers = ['visitor_id', 'consult_count', 'open_time', 'action_time', 'action_type', 'user_input', 'recommended_product', 'duration_sec']

    # 1. Google Sheets 기록
    try:
        client = get_sheets_client()
        if client:
            worksheet = get_or_create_sheet(client, SHEET_USER_LOG)
            if worksheet:
                if len(worksheet.get_all_values()) == 0: worksheet.append_row(headers)
                worksheet.append_row(row)
    except Exception as e:
        print(f"❌ 구글 시트 로그 실패: {e}")

    # 2. 로컬 엑셀 기록
    _log_to_local_excel(SHEET_USER_LOG, row, headers)

# ============================================================================
# 상담 신청 기록 (통합)
# ============================================================================
def log_consultation_request(visitor_id, consult_count, open_time_str, recommended_product, user_name="", user_phone="", user_email="", preferred_time=""):
    request_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [request_time, visitor_id, consult_count, open_time_str, recommended_product, user_name, user_phone, user_email, preferred_time, '대기중']
    headers = ['request_time', 'visitor_id', 'consult_count', 'session_start', 'recommended_product', 'name', 'phone', 'email', 'preferred_time', 'status']

    # 1. Google Sheets 기록
    success = False
    try:
        client = get_sheets_client()
        if client:
            worksheet = get_or_create_sheet(client, SHEET_CONSULT_LOG)
            if worksheet:
                if len(worksheet.get_all_values()) == 0: worksheet.append_row(headers)
                worksheet.append_row(row)
                success = True
    except Exception as e:
        print(f"❌ 구글 시트 상담신청 실패: {e}")

    # 2. 로컬 엑셀 기록 (구글 시트 실패해도 로컬엔 남김)
    _log_to_local_excel(SHEET_CONSULT_LOG, row, headers)
    
    # 로컬 저장 성공했다면 True 반환 (구글 시트가 없어도 로컬 동작하면 성공으로 간주)
    return True

# ============================================================================
# 추천 메인 및 초기화
# ============================================================================
def get_recommendation(interest: str, selected_tags: Dict[str, List[str]], situation_text: str = "") -> Optional[str]:
    return get_product_by_tags(selected_tags)

def initialize_recommendation_system():
    print(f"✅ 추천 시스템 초기화 완료 (로컬 로그: {LOCAL_LOG_FILE})")

if __name__ == "__main__":
    initialize_recommendation_system()