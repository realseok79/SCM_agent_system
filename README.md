# SCM Agent System

AI 기반 다중 에이전트 공급망 관리 시스템

## 📋 사전 요구사항

| 항목 | 버전 | 비고 |
|------|------|------|
| Python | 3.12+ | `python --version`으로 확인 |
| Docker & Compose | 최신 | 백엔드 데이터베이스 구동용 (선택) |
| Java (JDK) | 21+ | Java 백엔드 개발 시 필요 (선택) |

---

## 🚀 빠른 시작 (Quick Start)

### 1. 소스코드 복사
```bash
git clone https://github.com/realseok79/SCM_agent_system.git
cd SCM_agent_system
```

### 2. 백엔드 및 PostgreSQL 기동 (Docker 방식 권장)
로컬에 PostgreSQL을 설치할 필요 없이 Docker Compose를 통해 백엔드 앱과 DB를 원클릭으로 구동할 수 있습니다.
```bash
cd scm-agent-backend
docker-compose up -d   # PostgreSQL DB 및 Analysis 마이크로서비스 기동
```

### 3. Python 가상환경 구축 및 의존성 설치
```bash
cd ../scm-agent-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 환경 변수 복사 및 외부 API 설정
```bash
# .env 복사
cp .env.example .env

# Streamlit API 키 설정 (없을 시 mock 데이터로 자동 대체 작동)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

> **API 키 발급 안내 (모두 무료)**
> | 키 | 발급처 | 용도 |
> |---|--------|------|
> | `FRED_API_KEY` | [FRED API Key 발급 페이지](https://fred.stlouisfed.org/docs/api/api_key.html) | 미국 연방준비은행 거시경제 지표 수집 |
> | `KMA_API_KEY` | [기상청 API 허브](https://apihub.kma.go.kr) | 대한민국 국내 실시간 기상 관측 데이터 |
> | `OPENWEATHER_API_KEY` | [OpenWeather API Appid](https://openweathermap.org/appid) | 글로벌 공급망 노선 기상 정보 |

### 5. 프로그램 실행
```bash
# 시뮬레이터 구동 (100일 분량)
python main.py

# 대시보드 서버 실행
streamlit run dashboard/app.py
```

### 6. 테스트 수행
```bash
pytest                  # 199개 단위/통합 테스트 검증
```

---

## 📁 프로젝트 구조

```
scm-agent-system/
├── agents/              # AI 에이전트 모듈 (Data, Analysis, Action)
├── config/              # 비즈니스 규칙 설정 (decision_rules.yaml)
├── dashboard/           # Streamlit 대시보드 UI
├── data/                # 마스터 데이터 (CSV) + SQLite DB (자동 생성)
├── dto/                 # 데이터 전송 객체 스키마
├── outputs/             # 발주서, 리포트 출력 (런타임 생성)
├── simulator/           # 시간 압축 시뮬레이션 엔진
├── tests/               # 199개 단위/통합 테스트
├── utils/               # 공통 유틸 (파서, 커넥터, 스코어링 엔진)
├── .env.example         # 환경변수 템플릿
├── .streamlit/          # Streamlit 설정 (테마 + secrets 템플릿)
├── db.py                # SQLite DB 스키마 + 시드 데이터 초기화
├── main.py              # 시뮬레이션 진입점
└── requirements.txt     # Python 의존성 목록
```
