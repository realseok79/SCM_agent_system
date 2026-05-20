"""
data_config.py
==============
[Enterprise SCM Edition v2.0]
악재·호재 대칭형 초고밀도 키워드 매트릭스 + 가중치 + 시차(Lag) 내장 아키텍처

[v2.0 업그레이드 포인트]
- 카테고리: 4개 → 9개 (반도체·에너지·노동·정책·소비자 심리 축 신규 추가)
- 키워드 수: ~80개 → ~400개 (5배 확대)
- 가중치(weight): 0.0~1.0 (수요 충격 강도)
- 시차(lag_days): 키워드 트렌드가 실제 수요에 반영되기까지의 일 수
- direction: +1(수요 증가), -1(수요 감소)
- Google Trends 연동 적합성: 각 키워드는 실제 검색량 기반 신호로 사용 가능
"""

KEYWORD_WEIGHT_MAP = {}  # 하단 빌드 함수로 자동 생성

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 1: 보건·바이오 위기 vs 건강·웰빙 붐
# ──────────────────────────────────────────────────────────────────────────────
HEALTH_AND_BIOTECH = {
    "THREAT": {
        "마스크 품절":           {"weight": 0.95, "lag_days": 0,  "direction": +1},
        "KF94 구매":             {"weight": 0.90, "lag_days": 0,  "direction": +1},
        "코로나 확진자":          {"weight": 0.88, "lag_days": 2,  "direction": +1},
        "감염병 경보":            {"weight": 0.85, "lag_days": 1,  "direction": +1},
        "팬데믹 선언":            {"weight": 0.98, "lag_days": 0,  "direction": +1},
        "봉쇄령":                {"weight": 0.92, "lag_days": 1,  "direction": -1},
        "격리":                  {"weight": 0.80, "lag_days": 3,  "direction": -1},
        "셧다운":                {"weight": 0.88, "lag_days": 1,  "direction": -1},
        "진단키트 부족":          {"weight": 0.85, "lag_days": 1,  "direction": +1},
        "재택근무":              {"weight": 0.75, "lag_days": 7,  "direction": -1},
        "원격수업":              {"weight": 0.70, "lag_days": 5,  "direction": -1},
        "생필품 사재기":          {"weight": 0.93, "lag_days": 0,  "direction": +1},
        "의료 붕괴":             {"weight": 0.90, "lag_days": 3,  "direction": -1},
        "변이 바이러스":          {"weight": 0.85, "lag_days": 5,  "direction": +1},
        "치료제 부족":            {"weight": 0.82, "lag_days": 3,  "direction": +1},
        "방역 강화":             {"weight": 0.78, "lag_days": 2,  "direction": -1},
        "확산 경보":             {"weight": 0.80, "lag_days": 2,  "direction": +1},
        "집합 금지":             {"weight": 0.72, "lag_days": 3,  "direction": -1},
        "자가격리 키트":          {"weight": 0.88, "lag_days": 0,  "direction": +1},
        "손소독제 품귀":          {"weight": 0.83, "lag_days": 0,  "direction": +1},
        "항바이러스제":          {"weight": 0.80, "lag_days": 2,  "direction": +1},
        "의료용 장갑 부족":       {"weight": 0.77, "lag_days": 3,  "direction": +1},
    },
    "OPPORTUNITY": {
        "엔데믹":               {"weight": 0.85, "lag_days": 7,  "direction": +1},
        "거리두기 해제":         {"weight": 0.88, "lag_days": 3,  "direction": +1},
        "야외 활동 증가":        {"weight": 0.75, "lag_days": 7,  "direction": +1},
        "위드코로나":            {"weight": 0.80, "lag_days": 5,  "direction": +1},
        "헬스케어":              {"weight": 0.65, "lag_days": 14, "direction": +1},
        "웰빙 푸드":             {"weight": 0.60, "lag_days": 14, "direction": +1},
        "비타민 구매":           {"weight": 0.65, "lag_days": 7,  "direction": +1},
        "건강기능식품":          {"weight": 0.68, "lag_days": 10, "direction": +1},
        "체육시설 개방":         {"weight": 0.70, "lag_days": 5,  "direction": +1},
        "단체 관광 재개":        {"weight": 0.75, "lag_days": 14, "direction": +1},
        "오프라인 쇼핑 회복":    {"weight": 0.82, "lag_days": 7,  "direction": +1},
        "보복 여행":             {"weight": 0.80, "lag_days": 10, "direction": +1},
        "공연 재개":             {"weight": 0.72, "lag_days": 7,  "direction": +1},
        "스포츠 관람":           {"weight": 0.68, "lag_days": 7,  "direction": +1},
        "헬스장 등록":           {"weight": 0.65, "lag_days": 10, "direction": +1},
        "면역력 식품":           {"weight": 0.62, "lag_days": 14, "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 2: 물류·무역 마비 vs 조달 고속화
# ──────────────────────────────────────────────────────────────────────────────
LOGISTICS_AND_TRADE = {
    "THREAT": {
        "물류 파업":             {"weight": 0.92, "lag_days": 3,  "direction": -1},
        "화물연대 파업":         {"weight": 0.93, "lag_days": 2,  "direction": -1},
        "항만 봉쇄":             {"weight": 0.90, "lag_days": 5,  "direction": -1},
        "운송 중단":             {"weight": 0.88, "lag_days": 3,  "direction": -1},
        "컨테이너 부족":         {"weight": 0.85, "lag_days": 7,  "direction": -1},
        "해운 운임 폭등":        {"weight": 0.87, "lag_days": 14, "direction": -1},
        "SCFI 상승":             {"weight": 0.80, "lag_days": 14, "direction": -1},
        "수에즈 운하 마비":      {"weight": 0.95, "lag_days": 7,  "direction": -1},
        "공급망 붕괴":           {"weight": 0.93, "lag_days": 10, "direction": -1},
        "통관 지연":             {"weight": 0.82, "lag_days": 5,  "direction": -1},
        "수출 통제":             {"weight": 0.88, "lag_days": 14, "direction": -1},
        "관세 폭탄":             {"weight": 0.85, "lag_days": 30, "direction": -1},
        "항로 우회":             {"weight": 0.78, "lag_days": 10, "direction": -1},
        "선박 대기":             {"weight": 0.75, "lag_days": 7,  "direction": -1},
        "원자재 고갈":           {"weight": 0.90, "lag_days": 21, "direction": -1},
        "물류 대란":             {"weight": 0.92, "lag_days": 3,  "direction": -1},
        "배송 지연":             {"weight": 0.78, "lag_days": 2,  "direction": -1},
        "항공 화물 증편 실패":   {"weight": 0.72, "lag_days": 5,  "direction": -1},
        "지정학적 리스크":       {"weight": 0.80, "lag_days": 14, "direction": -1},
        "전쟁 발발":             {"weight": 0.98, "lag_days": 3,  "direction": -1},
        "러시아 제재":           {"weight": 0.88, "lag_days": 7,  "direction": -1},
        "미중 무역 분쟁":        {"weight": 0.85, "lag_days": 21, "direction": -1},
        "요소수 부족":           {"weight": 0.90, "lag_days": 3,  "direction": -1},
        "트럭 파업":             {"weight": 0.88, "lag_days": 2,  "direction": -1},
        "철도 파업":             {"weight": 0.82, "lag_days": 2,  "direction": -1},
    },
    "OPPORTUNITY": {
        "물류 정상화":           {"weight": 0.82, "lag_days": 7,  "direction": +1},
        "해운 운임 안정":        {"weight": 0.78, "lag_days": 14, "direction": +1},
        "자유무역협정":          {"weight": 0.75, "lag_days": 30, "direction": +1},
        "FTA 타결":              {"weight": 0.78, "lag_days": 30, "direction": +1},
        "관세 인하":             {"weight": 0.80, "lag_days": 21, "direction": +1},
        "통관 간소화":           {"weight": 0.70, "lag_days": 14, "direction": +1},
        "공급망 다변화":         {"weight": 0.72, "lag_days": 30, "direction": +1},
        "물류 거점 확대":        {"weight": 0.68, "lag_days": 30, "direction": +1},
        "화물기 증편":           {"weight": 0.70, "lag_days": 7,  "direction": +1},
        "신속 통관":             {"weight": 0.75, "lag_days": 5,  "direction": +1},
        "항만 정체 해소":        {"weight": 0.80, "lag_days": 7,  "direction": +1},
        "리쇼어링":              {"weight": 0.72, "lag_days": 60, "direction": +1},
        "무역 재개":             {"weight": 0.83, "lag_days": 14, "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 3: 이상기후·자연재해 vs 시즌 특수
# ──────────────────────────────────────────────────────────────────────────────
WEATHER_AND_CLIMATE = {
    "THREAT": {
        "폭설":                  {"weight": 0.85, "lag_days": 0,  "direction": -1},
        "한파":                  {"weight": 0.82, "lag_days": 0,  "direction": -1},
        "태풍 상륙":             {"weight": 0.88, "lag_days": 1,  "direction": -1},
        "폭우":                  {"weight": 0.80, "lag_days": 0,  "direction": -1},
        "침수 피해":             {"weight": 0.85, "lag_days": 1,  "direction": -1},
        "장마 시작":             {"weight": 0.72, "lag_days": 0,  "direction": -1},
        "기온 급락":             {"weight": 0.78, "lag_days": 0,  "direction": -1},
        "기습 폭설":             {"weight": 0.88, "lag_days": 0,  "direction": -1},
        "냉해 피해":             {"weight": 0.80, "lag_days": 7,  "direction": -1},
        "단전":                  {"weight": 0.90, "lag_days": 0,  "direction": -1},
        "공장 침수":             {"weight": 0.92, "lag_days": 1,  "direction": -1},
        "결항":                  {"weight": 0.83, "lag_days": 0,  "direction": -1},
        "폭염 경보":             {"weight": 0.78, "lag_days": 0,  "direction": -1},
        "전력 부족":             {"weight": 0.85, "lag_days": 0,  "direction": -1},
        "동파":                  {"weight": 0.82, "lag_days": 0,  "direction": -1},
        "지진":                  {"weight": 0.90, "lag_days": 0,  "direction": -1},
        "산불":                  {"weight": 0.88, "lag_days": 1,  "direction": -1},
        "가뭄":                  {"weight": 0.75, "lag_days": 21, "direction": -1},
        "홍수":                  {"weight": 0.87, "lag_days": 0,  "direction": -1},
        "기상 이변":             {"weight": 0.80, "lag_days": 3,  "direction": -1},
    },
    "OPPORTUNITY": {
        "여름 성수기":           {"weight": 0.85, "lag_days": 14, "direction": +1},
        "겨울 성수기":           {"weight": 0.82, "lag_days": 14, "direction": +1},
        "방한 용품 특수":        {"weight": 0.88, "lag_days": 7,  "direction": +1},
        "냉방 가전 폭주":        {"weight": 0.90, "lag_days": 7,  "direction": +1},
        "캠핑 시즌":             {"weight": 0.78, "lag_days": 10, "direction": +1},
        "나들이 기후":           {"weight": 0.72, "lag_days": 3,  "direction": +1},
        "바캉스 시즌":           {"weight": 0.80, "lag_days": 14, "direction": +1},
        "야외 콘서트":           {"weight": 0.68, "lag_days": 7,  "direction": +1},
        "단풍 시즌":             {"weight": 0.65, "lag_days": 7,  "direction": +1},
        "스키 시즌":             {"weight": 0.78, "lag_days": 14, "direction": +1},
        "풍작":                  {"weight": 0.72, "lag_days": 30, "direction": +1},
        "우산 특수":             {"weight": 0.75, "lag_days": 0,  "direction": +1},
        "기후 안정":             {"weight": 0.65, "lag_days": 7,  "direction": +1},
        "벚꽃 시즌":             {"weight": 0.70, "lag_days": 7,  "direction": +1},
        "개화 시기":             {"weight": 0.68, "lag_days": 5,  "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 4: 거시경제 침체·고금리 vs 경기 부양·소비 회복
# ──────────────────────────────────────────────────────────────────────────────
MACRO_ECONOMY = {
    "THREAT": {
        "금리 인상":             {"weight": 0.88, "lag_days": 45, "direction": -1},
        "기준금리 인상":         {"weight": 0.90, "lag_days": 45, "direction": -1},
        "물가 폭등":             {"weight": 0.87, "lag_days": 14, "direction": -1},
        "CPI 폭등":              {"weight": 0.85, "lag_days": 21, "direction": -1},
        "원달러 환율 상승":      {"weight": 0.83, "lag_days": 14, "direction": -1},
        "스태그플레이션":        {"weight": 0.92, "lag_days": 30, "direction": -1},
        "경기 침체":             {"weight": 0.90, "lag_days": 30, "direction": -1},
        "소비 심리 위축":        {"weight": 0.85, "lag_days": 14, "direction": -1},
        "구조조정":              {"weight": 0.82, "lag_days": 21, "direction": -1},
        "디폴트 위기":           {"weight": 0.93, "lag_days": 7,  "direction": -1},
        "금융 위기":             {"weight": 0.95, "lag_days": 7,  "direction": -1},
        "수입 단가 폭등":        {"weight": 0.88, "lag_days": 21, "direction": -1},
        "원자재 가격 상승":      {"weight": 0.85, "lag_days": 14, "direction": -1},
        "달러 강세":             {"weight": 0.80, "lag_days": 14, "direction": -1},
        "대출 금리 상승":        {"weight": 0.82, "lag_days": 30, "direction": -1},
        "부동산 침체":           {"weight": 0.78, "lag_days": 30, "direction": -1},
        "주가 폭락":             {"weight": 0.88, "lag_days": 7,  "direction": -1},
        "코스피 급락":           {"weight": 0.85, "lag_days": 7,  "direction": -1},
        "가계부채 증가":         {"weight": 0.75, "lag_days": 30, "direction": -1},
        "실업률 상승":           {"weight": 0.82, "lag_days": 21, "direction": -1},
        "무역수지 적자":         {"weight": 0.80, "lag_days": 21, "direction": -1},
        "기업 파산":             {"weight": 0.88, "lag_days": 14, "direction": -1},
        "소비자 신뢰지수 하락":  {"weight": 0.83, "lag_days": 14, "direction": -1},
    },
    "OPPORTUNITY": {
        "금리 인하":             {"weight": 0.88, "lag_days": 45, "direction": +1},
        "기준금리 인하":         {"weight": 0.90, "lag_days": 45, "direction": +1},
        "물가 안정":             {"weight": 0.82, "lag_days": 21, "direction": +1},
        "소비 심리 회복":        {"weight": 0.85, "lag_days": 14, "direction": +1},
        "경기 부양책":           {"weight": 0.88, "lag_days": 21, "direction": +1},
        "소비 진작":             {"weight": 0.82, "lag_days": 14, "direction": +1},
        "내수 활성화":           {"weight": 0.80, "lag_days": 21, "direction": +1},
        "수출 호조":             {"weight": 0.83, "lag_days": 14, "direction": +1},
        "보복 소비":             {"weight": 0.90, "lag_days": 7,  "direction": +1},
        "블랙프라이데이":        {"weight": 0.92, "lag_days": 7,  "direction": +1},
        "코리아세일페스타":      {"weight": 0.88, "lag_days": 5,  "direction": +1},
        "쇼핑 페스티벌":         {"weight": 0.85, "lag_days": 5,  "direction": +1},
        "소득 증가":             {"weight": 0.78, "lag_days": 21, "direction": +1},
        "주가 상승":             {"weight": 0.82, "lag_days": 7,  "direction": +1},
        "달러 약세":             {"weight": 0.78, "lag_days": 14, "direction": +1},
        "무역수지 흑자":         {"weight": 0.75, "lag_days": 14, "direction": +1},
        "광군제":                {"weight": 0.88, "lag_days": 5,  "direction": +1},
        "추석 특수":             {"weight": 0.90, "lag_days": 14, "direction": +1},
        "설 특수":               {"weight": 0.90, "lag_days": 14, "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 5: 반도체·기술 공급망 위기 vs 기술 특수 (신규)
# ──────────────────────────────────────────────────────────────────────────────
TECH_AND_SEMICONDUCTOR = {
    "THREAT": {
        "반도체 공급 부족":      {"weight": 0.92, "lag_days": 30, "direction": -1},
        "칩 부족":               {"weight": 0.90, "lag_days": 21, "direction": -1},
        "반도체 수출 규제":      {"weight": 0.93, "lag_days": 21, "direction": -1},
        "TSMC 생산 차질":        {"weight": 0.88, "lag_days": 21, "direction": -1},
        "미국 반도체 제재":      {"weight": 0.90, "lag_days": 14, "direction": -1},
        "D램 가격 급락":         {"weight": 0.82, "lag_days": 14, "direction": -1},
        "IT 경기 침체":          {"weight": 0.85, "lag_days": 21, "direction": -1},
        "스마트폰 수요 둔화":    {"weight": 0.80, "lag_days": 14, "direction": -1},
        "AI 반도체 품귀":        {"weight": 0.88, "lag_days": 14, "direction": +1},
        "클라우드 투자 축소":    {"weight": 0.78, "lag_days": 30, "direction": -1},
        "테크 레이오프":         {"weight": 0.82, "lag_days": 14, "direction": -1},
        "배터리 소재 부족":      {"weight": 0.88, "lag_days": 21, "direction": -1},
        "리튬 가격 폭등":        {"weight": 0.85, "lag_days": 14, "direction": -1},
        "전기차 수요 둔화":      {"weight": 0.80, "lag_days": 21, "direction": -1},
        "소프트웨어 라이선스 비용 급등": {"weight": 0.72, "lag_days": 30, "direction": -1},
    },
    "OPPORTUNITY": {
        "반도체 슈퍼사이클":     {"weight": 0.92, "lag_days": 30, "direction": +1},
        "AI 수요 폭증":          {"weight": 0.93, "lag_days": 14, "direction": +1},
        "챗GPT 열풍":            {"weight": 0.88, "lag_days": 7,  "direction": +1},
        "신형 스마트폰 출시":    {"weight": 0.85, "lag_days": 14, "direction": +1},
        "5G 상용화":             {"weight": 0.80, "lag_days": 30, "direction": +1},
        "전기차 보조금":         {"weight": 0.85, "lag_days": 21, "direction": +1},
        "배터리 기술 혁신":      {"weight": 0.78, "lag_days": 30, "direction": +1},
        "클라우드 투자 확대":    {"weight": 0.82, "lag_days": 21, "direction": +1},
        "게이밍 시즌":           {"weight": 0.78, "lag_days": 7,  "direction": +1},
        "IT 기기 교체 수요":     {"weight": 0.80, "lag_days": 14, "direction": +1},
        "반도체 보조금":         {"weight": 0.82, "lag_days": 30, "direction": +1},
        "드론 배송 상용화":      {"weight": 0.70, "lag_days": 60, "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 6: 에너지·원자재 위기 vs 공급 안정 (신규)
# ──────────────────────────────────────────────────────────────────────────────
ENERGY_AND_RAW_MATERIALS = {
    "THREAT": {
        "유가 폭등":             {"weight": 0.92, "lag_days": 7,  "direction": -1},
        "WTI 급등":              {"weight": 0.90, "lag_days": 7,  "direction": -1},
        "천연가스 가격 폭등":    {"weight": 0.88, "lag_days": 7,  "direction": -1},
        "전기 요금 인상":        {"weight": 0.85, "lag_days": 14, "direction": -1},
        "석탄 가격 상승":        {"weight": 0.80, "lag_days": 14, "direction": -1},
        "에너지 위기":           {"weight": 0.92, "lag_days": 7,  "direction": -1},
        "OPEC 감산":             {"weight": 0.88, "lag_days": 7,  "direction": -1},
        "러시아 가스 공급 중단": {"weight": 0.95, "lag_days": 3,  "direction": -1},
        "철강 가격 폭등":        {"weight": 0.85, "lag_days": 21, "direction": -1},
        "알루미늄 가격 급등":    {"weight": 0.83, "lag_days": 21, "direction": -1},
        "구리 가격 폭등":        {"weight": 0.82, "lag_days": 14, "direction": -1},
        "플라스틱 원료 부족":    {"weight": 0.85, "lag_days": 14, "direction": -1},
        "원자재 수급 불안":      {"weight": 0.88, "lag_days": 14, "direction": -1},
        "희토류 수출 제한":      {"weight": 0.90, "lag_days": 21, "direction": -1},
        "정전 위기":             {"weight": 0.90, "lag_days": 0,  "direction": -1},
        "가스 대란":             {"weight": 0.88, "lag_days": 3,  "direction": -1},
    },
    "OPPORTUNITY": {
        "유가 안정":             {"weight": 0.80, "lag_days": 7,  "direction": +1},
        "원자재 가격 하락":      {"weight": 0.82, "lag_days": 14, "direction": +1},
        "재생에너지 확대":       {"weight": 0.70, "lag_days": 60, "direction": +1},
        "태양광 설치 확대":      {"weight": 0.68, "lag_days": 45, "direction": +1},
        "에너지 요금 인하":      {"weight": 0.80, "lag_days": 14, "direction": +1},
        "OPEC 증산":             {"weight": 0.82, "lag_days": 7,  "direction": +1},
        "전기차 충전 인프라":    {"weight": 0.70, "lag_days": 30, "direction": +1},
        "원자재 수급 안정":      {"weight": 0.78, "lag_days": 14, "direction": +1},
        "철강 가격 안정":        {"weight": 0.75, "lag_days": 21, "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 7: 노동·인력 리스크 vs 생산성 향상 (신규)
# ──────────────────────────────────────────────────────────────────────────────
LABOR_AND_WORKFORCE = {
    "THREAT": {
        "총파업":                {"weight": 0.93, "lag_days": 1,  "direction": -1},
        "노사 분규":             {"weight": 0.85, "lag_days": 3,  "direction": -1},
        "최저임금 대폭 인상":   {"weight": 0.80, "lag_days": 30, "direction": -1},
        "인력 부족":             {"weight": 0.82, "lag_days": 14, "direction": -1},
        "대량 해고":             {"weight": 0.88, "lag_days": 14, "direction": -1},
        "공장 가동 중단":        {"weight": 0.92, "lag_days": 2,  "direction": -1},
        "생산직 이직률 급증":    {"weight": 0.78, "lag_days": 14, "direction": -1},
        "외국인 노동자 입국 제한": {"weight": 0.80, "lag_days": 21, "direction": -1},
        "산업재해 증가":         {"weight": 0.75, "lag_days": 7,  "direction": -1},
        "근로시간 단축":         {"weight": 0.72, "lag_days": 30, "direction": -1},
        "레이오프":              {"weight": 0.82, "lag_days": 7,  "direction": -1},
        "직장 폐쇄":             {"weight": 0.90, "lag_days": 1,  "direction": -1},
    },
    "OPPORTUNITY": {
        "자동화 도입":           {"weight": 0.75, "lag_days": 60, "direction": +1},
        "로봇 도입":             {"weight": 0.78, "lag_days": 60, "direction": +1},
        "스마트 팩토리":         {"weight": 0.72, "lag_days": 60, "direction": +1},
        "외국인 노동자 확대":    {"weight": 0.70, "lag_days": 21, "direction": +1},
        "고용 보조금":           {"weight": 0.72, "lag_days": 14, "direction": +1},
        "생산성 향상":           {"weight": 0.75, "lag_days": 21, "direction": +1},
        "공장 신설":             {"weight": 0.80, "lag_days": 60, "direction": +1},
        "야간 교대 확대":        {"weight": 0.68, "lag_days": 7,  "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 8: 정책·규제 리스크 vs 정책 지원 (신규)
# ──────────────────────────────────────────────────────────────────────────────
REGULATORY_AND_POLICY = {
    "THREAT": {
        "수입 규제 강화":        {"weight": 0.85, "lag_days": 21, "direction": -1},
        "환경 규제 강화":        {"weight": 0.78, "lag_days": 30, "direction": -1},
        "탄소세 도입":           {"weight": 0.80, "lag_days": 45, "direction": -1},
        "식품 안전 기준 강화":   {"weight": 0.75, "lag_days": 21, "direction": -1},
        "리콜 사태":             {"weight": 0.90, "lag_days": 3,  "direction": -1},
        "제품 안전 규제":        {"weight": 0.82, "lag_days": 14, "direction": -1},
        "개인정보 규제":         {"weight": 0.72, "lag_days": 30, "direction": -1},
        "독과점 규제":           {"weight": 0.75, "lag_days": 30, "direction": -1},
        "플랫폼 규제":           {"weight": 0.78, "lag_days": 21, "direction": -1},
        "의약품 허가 취소":      {"weight": 0.88, "lag_days": 3,  "direction": -1},
        "수출 허가 취소":        {"weight": 0.90, "lag_days": 5,  "direction": -1},
        "제조업 이전 규제":      {"weight": 0.72, "lag_days": 45, "direction": -1},
    },
    "OPPORTUNITY": {
        "정부 보조금":           {"weight": 0.85, "lag_days": 21, "direction": +1},
        "산업 육성 정책":        {"weight": 0.80, "lag_days": 30, "direction": +1},
        "수출 지원":             {"weight": 0.78, "lag_days": 14, "direction": +1},
        "R&D 세액공제":          {"weight": 0.72, "lag_days": 30, "direction": +1},
        "규제 샌드박스":         {"weight": 0.70, "lag_days": 45, "direction": +1},
        "인허가 간소화":         {"weight": 0.73, "lag_days": 30, "direction": +1},
        "특별경제구역":          {"weight": 0.75, "lag_days": 60, "direction": +1},
        "중소기업 지원":         {"weight": 0.72, "lag_days": 21, "direction": +1},
        "탄소 크레딧 완화":      {"weight": 0.70, "lag_days": 30, "direction": +1},
        "디지털 전환 지원":      {"weight": 0.73, "lag_days": 30, "direction": +1},
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 카테고리 9: 소비자 심리·트렌드 (신규)
# ──────────────────────────────────────────────────────────────────────────────
CONSUMER_SENTIMENT = {
    "THREAT": {
        "소비자 신뢰지수 하락":  {"weight": 0.85, "lag_days": 7,  "direction": -1},
        "지갑 닫기":             {"weight": 0.88, "lag_days": 7,  "direction": -1},
        "불매 운동":             {"weight": 0.90, "lag_days": 3,  "direction": -1},
        "가성비 소비":           {"weight": 0.75, "lag_days": 14, "direction": -1},
        "명품 소비 급감":        {"weight": 0.82, "lag_days": 14, "direction": -1},
        "소비 절벽":             {"weight": 0.90, "lag_days": 7,  "direction": -1},
        "과소비 경계":           {"weight": 0.72, "lag_days": 14, "direction": -1},
        "짠테크":                {"weight": 0.78, "lag_days": 7,  "direction": -1},
        "가계 긴축":             {"weight": 0.83, "lag_days": 14, "direction": -1},
        "온라인 가격 비교 급증": {"weight": 0.70, "lag_days": 5,  "direction": -1},
        "중고 거래 급증":        {"weight": 0.72, "lag_days": 5,  "direction": -1},
        "할인 쿠폰 검색 급증":   {"weight": 0.73, "lag_days": 3,  "direction": -1},
    },
    "OPPORTUNITY": {
        "소비자 신뢰지수 상승":  {"weight": 0.85, "lag_days": 7,  "direction": +1},
        "명품 소비 폭증":        {"weight": 0.88, "lag_days": 7,  "direction": +1},
        "MZ세대 소비":           {"weight": 0.78, "lag_days": 14, "direction": +1},
        "한류 소비 붐":          {"weight": 0.82, "lag_days": 7,  "direction": +1},
        "K-뷰티 열풍":           {"weight": 0.85, "lag_days": 7,  "direction": +1},
        "펫 산업 성장":          {"weight": 0.72, "lag_days": 14, "direction": +1},
        "홈코노미":              {"weight": 0.80, "lag_days": 7,  "direction": +1},
        "편의점 특수":           {"weight": 0.75, "lag_days": 3,  "direction": +1},
        "구독 경제 성장":        {"weight": 0.70, "lag_days": 21, "direction": +1},
        "소확행 소비":           {"weight": 0.72, "lag_days": 7,  "direction": +1},
        "프리미엄 소비":         {"weight": 0.78, "lag_days": 14, "direction": +1},
        "친환경 소비":           {"weight": 0.68, "lag_days": 21, "direction": +1},
        "밸런타인 특수":         {"weight": 0.80, "lag_days": 7,  "direction": +1},
        "수능 이후 소비 폭증":   {"weight": 0.82, "lag_days": 3,  "direction": +1},
        "연말 소비 특수":        {"weight": 0.88, "lag_days": 14, "direction": +1},
    }
}

SCENARIO_KEYWORDS = {
    "HEALTH_AND_BIOTECH":       HEALTH_AND_BIOTECH,
    "LOGISTICS_AND_TRADE":      LOGISTICS_AND_TRADE,
    "WEATHER_AND_CLIMATE":      WEATHER_AND_CLIMATE,
    "MACRO_ECONOMY":            MACRO_ECONOMY,
    "TECH_AND_SEMICONDUCTOR":   TECH_AND_SEMICONDUCTOR,
    "ENERGY_AND_RAW_MATERIALS": ENERGY_AND_RAW_MATERIALS,
    "LABOR_AND_WORKFORCE":      LABOR_AND_WORKFORCE,
    "REGULATORY_AND_POLICY":    REGULATORY_AND_POLICY,
    "CONSUMER_SENTIMENT":       CONSUMER_SENTIMENT,
}

def build_weight_map() -> dict:
    weight_map = {}
    for category, sides in SCENARIO_KEYWORDS.items():
        for side, keywords in sides.items():
            for kw, meta in keywords.items():
                weight_map[kw] = {
                    **meta,
                    "category": category,
                    "side": side,
                }
    return weight_map

def get_demand_impact_score(
    trending_keywords: list[str],
    weight_map: dict = None
) -> dict:
    if weight_map is None:
        weight_map = build_weight_map()

    total_weighted_direction = 0.0
    total_weights            = 0.0
    lag_summary              = []

    sorted_master_keywords = sorted(weight_map.keys(), key=len, reverse=True)

    for user_kw in trending_keywords:
        normalized_user_kw = user_kw.replace(" ", "").lower()

        for master_kw in sorted_master_keywords:
            normalized_master_kw = master_kw.replace(" ", "").lower()

            if normalized_master_kw in normalized_user_kw:
                meta = weight_map[master_kw]
                impact                    = meta["weight"] * meta["direction"]
                total_weighted_direction += impact
                total_weights            += meta["weight"]

                lag_summary.append({
                    "matched_input" : user_kw,
                    "master_keyword": master_kw,
                    "direction"     : meta["direction"],
                    "lag_days"      : meta["lag_days"],
                    "weight"        : meta["weight"],
                    "category"      : meta["category"],
                    "side"          : meta["side"],
                })
                break

    if total_weights == 0.0:
        return {
            "composite_score"  : 0.0,
            "affected_lag_items": [],
            "immediate_impact" : 0.0,
            "deferred_impact"  : [],
            "matched_count"    : 0,
        }

    composite_score = round(total_weighted_direction / total_weights, 4)

    immediate_items  = [x for x in lag_summary if x["lag_days"] == 0]
    deferred_items   = [x for x in lag_summary if x["lag_days"] >  0]

    immediate_impact = 0.0
    if immediate_items:
        imm_w = sum(x["weight"] for x in immediate_items)
        imm_d = sum(x["weight"] * x["direction"] for x in immediate_items)
        immediate_impact = round(imm_d / imm_w, 4) if imm_w > 0 else 0.0

    return {
        "composite_score"  : composite_score,
        "affected_lag_items": lag_summary,
        "immediate_impact" : immediate_impact,
        "deferred_impact"  : sorted(deferred_items, key=lambda x: x["lag_days"]),
        "matched_count"    : len(lag_summary),
    }

if __name__ == "__main__":
    wmap = build_weight_map()
    total = len(wmap)
    cats  = len(SCENARIO_KEYWORDS)

    print(f"\n{'='*55}")
    print(f"  Enterprise SCM 키워드 매트릭스 v2.0 통계")
    print(f"{'='*55}")
    print(f"  총 카테고리 수  : {cats}개")
    print(f"  총 키워드 수    : {total}개")
    print(f"\n  카테고리별 키워드 수:")
    for cat, sides in SCENARIO_KEYWORDS.items():
        t_cnt = len(sides.get("THREAT", {}))
        o_cnt = len(sides.get("OPPORTUNITY", {}))
        print(f"    {cat:<30} THREAT {t_cnt:>3}개 / OPPORTUNITY {o_cnt:>3}개")

    print(f"\n  평균 가중치     : {sum(v['weight'] for v in wmap.values()) / total:.3f}")
    print(f"  평균 시차(Lag)  : {sum(v['lag_days'] for v in wmap.values()) / total:.1f}일")
    print(f"{'='*55}\n")
