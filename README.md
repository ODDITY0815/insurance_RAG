# 💡 현대해상 Hi-light: AI 맞춤형 보험 추천 및 약관 분석 서비스
본 프로젝트는 사용자의 관심 태그와 상황을 바탕으로 최적의 보험 상품을 추천하고, 복잡한 보험 약관을 AI가 정밀 분석하여 알기 쉽게 설명해 주는 서비스입니다.
# 핵심
## 1. 하이브리드 추천 로직 (2-Step Search)
### Step 1: 카탈로그 기반 경량 검색

웹 페이지(https://www.hi.co.kr/serviceAction.do?menuId=202652) 크롤링 데이터를 기반으로 구축된 경량 DB를 탐색합니다.

사용자가 선택한 태그와 상품별 추출 태그의 유사도를 비교하여 적합한 보험 상품을 우선 제안합니다.

추천 상품과 관련된 일상적 사고 시나리오를 제시하여 사용자가 자연스럽게 상세 분석 단계로 진입하도록 유도합니다.

### Step 2: 약관(Clause) 기반 정밀 분석

기존 RAG 로직을 활용하여 약관 전문 DB에서 상세 보장 내용을 검색합니다.

추천 사유, 약관 근거, 보장 한계점, 매칭 점수를 객관적으로 제시하여 정보의 신뢰도를 높입니다.

## 2. 비즈니스 로직 및 로그 관리
Logic Separation: 추천 엔진과 로그 관리 로직을 recommend.py로 모듈화하여 UI 코드(app.py)와 분리했습니다.

Rule-based Engine: 카탈로그 데이터 기반의 룰베이스 추천을 수행하며, 향후 알고리즘 고도화 시 UI 수정 없이 백엔드 로직만 업데이트가 가능합니다.

Dual Logging: 구글 스프레드시트와 로컬 엑셀 파일에 상담 신청 내역 및 행동 로그를 실시간으로 기록하여 운영 효율성을 확보했습니다.


📂 프로젝트 구조 (최소 구성)
Plaintext
```
project-root/
├── app.py                # 메인 Streamlit UI 및 페이지 로직
├── recommend.py          # 추천 알고리즘 및 로그 저장 로직 (구글 스프레드시트/로컬)
├── .env                  # GOOGLE_API_KEY 설정 파일
├── service_account.json  # 구글 스프레드시트 연동용 인증 키
├── catalog_tags.json     # 상품별 태그 데이터베이스
├── toc_meta_summary.txt  # 약관 분석 가이드용 목차 요약
├── chroma_db_catalog/    # 1단계 상품 카탈로그 벡터 DB(20 청크 미만)
└── chroma_db_clause/     # 2단계 약관 전문 벡터 DB(5만 청크 이상)
```
🛠️ 설치 및 실행 가이드
1. 가상환경 생성 및 활성화 (insurance_RAG)
중복 환경 활성화로 인한 의존성 오류를 방지하기 위해 반드시 기존 환경을 해제한 후 아래 단계를 수행하세요.


```
# 기존 환경 해제 (필요시)
deactivate
conda deactivate
```
```
# 새 가상환경 생성
python3 -m venv insurance_RAG
```
```
# 가상환경 활성화 (Mac/Linux)
source insurance_RAG/bin/activate
```
```
# 가상환경 활성화 (Windows)
# insurance_RAG\Scripts\activate
```
2. 필수 라이브러리 설치
의존성 충돌을 방지하기 위해 데이터 처리 라이브러리를 먼저 설치하고 AI 관련 패키지를 설치합니다.


```
Bash
# 기본 도구 및 데이터 처리 패키지 설치
pip install --upgrade pip setuptools wheel
pip install python-dateutil pytz pandas openpyxl

# Streamlit 및 RAG 관련 패키지 설치
pip install streamlit python-dotenv gspread google-auth gdown
pip install langchain langchain-community langchain-chroma langchain-huggingface langchain-google-genai pydantic

# 임베딩 모델 구동을 위한 필수 패키지
pip install sentence-transformers huggingface-hub
```


```
# 원할 경우 requirements.txt 설치
pip install -r requirements.txt
```
3. 서비스 실행
설치가 완료되면 아래 명령어로 앱을 구동합니다.
```
streamlit run app.py
```
