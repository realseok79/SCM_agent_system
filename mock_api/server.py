"""
mock_api/server.py
------------------
외부 변수(날씨, 거시경제 지표, 리드타임)를 가상으로 생성해 Data Agent에게 제공하는 Mock API 서버.
타임 시뮬레이터와 동기화할 수 있도록 가상 날짜 계산 로직이 추가되었습니다.
"""

from flask import Flask, jsonify, request
from dotenv import load_dotenv
import numpy as np
import os
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)

# ──────────────────────────────────────────────
# 시드 고정 (재현 가능한 시뮬레이션을 위해 완벽 통일)
# ──────────────────────────────────────────────
SEED = 42
rng = np.random.default_rng(SEED)

# 시뮬레이션 시작 가상 날짜 (기준점)
START_DATE = datetime(2026, 1, 1)

# ──────────────────────────────────────────────
# 헬퍼 함수: 가상 날짜 및 일차(Day) 계산
# ──────────────────────────────────────────────
def get_context_date():
    """
    Data Agent가 ?day=15 와 같이 쿼리를 주면 가상 시뮬레이션 날짜를 계산하고,
    누락되면 실제 현재 시각을 기준으로 반환합니다. (시간 압축 시뮬레이터 대응)
    """
    day_param = request.args.get('day', type=int)
    if day_param is not None:
        virtual_date = START_DATE + timedelta(days=day_param)
        return virtual_date.isoformat(), day_param
    return datetime.now().isoformat(), None

# ──────────────────────────────────────────────
# 헬스체크
# ──────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    """서버 정상 동작 확인용 엔드포인트"""
    return jsonify({
        "status": "ok",
        "server": "SCM Mock API",
        "timestamp": datetime.now().isoformat()
    })

# ──────────────────────────────────────────────
# 내부 로직 함수 (중복 제거 및 캡슐화)
# ──────────────────────────────────────────────
def generate_weather_data():
    """날씨 데이터 생성 로직 (정규분포 + 극단 이변 포아송/유니폼 모킹)"""
    base_index = float(rng.normal(loc=1.0, scale=0.2))
    base_index = round(max(0.3, min(2.0, base_index)), 3)

    # random.random() 대신 무조건 rng 활용하여 시드 격리 보장
    stress_event = rng.random() < 0.05
    if stress_event:
        base_index = round(float(rng.uniform(0.1, 0.3)), 3)  # 악천후로 인한 수요 급감

    return {
        "weather_index": base_index,
        "stress_event": stress_event,
        "description": _weather_description(base_index)
    }

def _weather_description(index: float) -> str:
    if index >= 1.3:
        return "성수기/맑음 - 수요 증가 예상"
    elif index >= 0.8:
        return "평상시 - 수요 정상"
    elif index >= 0.4:
        return "비수기/악천후 - 수요 감소 예상"
    else:
        return "⚠️ 기상 이변 - 수요 급감 경보"

def generate_macro_data():
    """거시경제 지표 생성 로직 (정규분포)"""
    trend = float(rng.normal(loc=1.0, scale=0.15))
    trend = round(max(0.5, min(1.8, trend)), 3)

    return {
        "macro_trend": trend,
        "gdp_growth_signal": round(trend - 1.0, 3),
        "consumer_confidence": round(trend * 100, 1),
        "description": _macro_description(trend)
    }

def _macro_description(trend: float) -> str:
    if trend >= 1.2:
        return "경기 호황 - 소비 증가 추세"
    elif trend >= 0.9:
        return "경기 안정 - 정상 소비 수준"
    elif trend >= 0.7:
        return "경기 둔화 - 소비 위축 주의"
    else:
        return "⚠️ 경기 침체 - 수요 급감 경보"

# ──────────────────────────────────────────────
# 라우터 엔드포인트 구현
# ──────────────────────────────────────────────
@app.route("/api/weather", methods=["GET"])
def get_weather():
    timestamp, day = get_context_date()
    data = generate_weather_data()
    data.update({"timestamp": timestamp, "simulation_day": day})
    return jsonify(data)

@app.route("/api/macro", methods=["GET"])
def get_macro():
    timestamp, day = get_context_date()
    data = generate_macro_data()
    data.update({"timestamp": timestamp, "simulation_day": day})
    return jsonify(data)

@app.route("/api/external-signals", methods=["GET"])
def get_external_signals():
    """Data Agent 전용 통합 엔드포인트 (중복 코드 제거 버전)"""
    timestamp, day = get_context_date()
    
    weather = generate_weather_data()
    macro = generate_macro_data()
    
    # 두 지표를 융합한 복합 수요 승수 계산
    combined_multiplier = round(weather["weather_index"] * macro["macro_trend"], 3)
    
    return jsonify({
        "simulation_day": day,
        "weather_index": weather["weather_index"],
        "macro_trend": macro["macro_trend"],
        "stress_event": weather["stress_event"], # 기상 이변이 곧 스트레스 이벤트
        "combined_demand_multiplier": combined_multiplier,
        "description": f"{weather['description']} / {macro['description']}",
        "timestamp": timestamp
    })

@app.route("/api/lead-time", methods=["GET"])
def get_lead_time():
    """공급망 조달 기간 반환 (정규 분포 기반 + 3% 확률 지연 초래)"""
    timestamp, day = get_context_date()
    
    # 조달 기간 변동성은 계획서대로 정규분포 가동
    base_lead_time = float(rng.normal(loc=7.0, scale=1.5))
    base_lead_time = round(max(3.0, min(14.0, base_lead_time)), 1)

    # 무작위성 버그 수정 (rng 사용)
    delay_event = rng.random() < 0.03
    if delay_event:
        # 조달 기간 2~3배 지연 스트레스 테스트 반영
        base_lead_time = round(base_lead_time * float(rng.uniform(2.0, 3.0)), 1)

    return jsonify({
        "simulation_day": day,
        "lead_time_days": base_lead_time,
        "delay_event": delay_event,
        "description": "⚠️ 공급망 지연 이벤트 발생(블랙 스완)" if delay_event else "정상 조달 기간",
        "timestamp": timestamp
    })

# ──────────────────────────────────────────────
# 서버 실행
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # 환경 변수 분리 및 예외 예방 조치
    mock_host_env = os.getenv("MOCK_API_HOST", "http://localhost:8080")
    # URL에서 호스트와 포트 추출
    host_port = mock_host_env.replace("http://", "").replace("https://", "")
    host = host_port.split(":")[0]
    port = int(host_port.split(":")[-1]) if ":" in host_port else 8080

    print(f"[Mock API 서버 시작] http://{host}:{port}")
    print("제공 엔드포인트 (타임 시뮬레이터 연동 시 '?day=일차' 쿼리스트링 사용 가능):")
    print("  GET /health                - 헬스체크")
    print("  GET /api/weather           - 날씨 지수")
    print("  GET /api/macro             - 거시경제 지표")
    print("  GET /api/external-signals   - 통합 외부 신호 (Data Agent 권장)")
    print("  GET /api/lead-time         - 조달기간 변동")

    app.run(host=host, port=port, debug=False)
