"""
mock_api/server.py
------------------
외부 변수(날씨, 거시경제 지표, 리드타임)를 가상으로 생성해 Data Agent에게 제공하는 Mock API 서버.
TimeSimulator 및 DataGenerator와 동일한 스트레스 스케줄을 공유하여 완벽한 데이터 정합성을 보장합니다.
"""

from flask import Flask, jsonify, request
from dotenv import load_dotenv
import numpy as np
import os
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)

# 시뮬레이션 시작 가상 날짜 (기준점)
START_DATE = datetime(2026, 1, 1)

# ── [동기화] 전체 시스템(엔진, 제너레이터) 공통 스트레스 스케줄 명세 ──
STRESS_SCHEDULE = [
    {"start": 30, "end": 35, "demand_mult": 5.0, "lt_mult": 1.0, "desc": "수요 폭증"},
    {"start": 60, "end": 81, "demand_mult": 1.0, "lt_mult": 3.0, "desc": "조달 지연"},
    {"start": 85, "end": 90, "demand_mult": 3.0, "lt_mult": 2.5, "desc": "복합 위기"}
]


def get_context_date(day: int) -> datetime:
    """시뮬레이션 day를 기반으로 현재 가상 날짜 반환"""
    return START_DATE + timedelta(days=(day - 1))


def get_stress_multipliers(day: int) -> tuple[bool, float, float, str]:
    """현재 가상 일차의 스트레스 이벤트 여부와 가중치 반환"""
    for event in STRESS_SCHEDULE:
        if event["start"] <= day <= event["end"]:
            return True, event["demand_mult"], event["lt_mult"], event["desc"]
    return False, 1.0, 1.0, "정상 상태"


def get_seeded_rng(day: int):
    """
    [도입] day별 독립 시드 생성기
    동일한 day로 재호출 시 항상 같은 값이 나오도록 보장하여 시뮬레이션 재현성 확보
    """
    base_seed = 42
    return np.random.default_rng(base_seed + day)


@app.route("/", methods=["GET"])
def health_check():
    return jsonify({
        "status": "online",
        "service": "SCM Mock API Server (Flask)",
        "simulation_start_date": START_DATE.strftime("%Y-%m-%d"),
        "synchronized_events": len(STRESS_SCHEDULE)
    })


@app.route("/api/external-signals", methods=["GET"])
def get_external_signals():
    # 1. 쿼리 스트링 파싱 및 해당 일차 전용 RNG 확보
    day = int(request.args.get("day", 1))
    current_date = get_context_date(day)
    rng = get_seeded_rng(day)
    
    # 2. 시스템 공통 스트레스 이벤트 체크
    is_stress, demand_mult, _, crisis_desc = get_stress_multipliers(day)

    # 3. 날씨 지수 생성 (계절성 반영)
    base_weather = rng.normal(loc=1.0, scale=0.05)
    if current_date.month in [7, 8]:  # 여름철 가중치
        base_weather += 0.1 
    weather_index = round(float(np.clip(base_weather, 0.8, 1.2)), 3)

    # 4. 거시경제 지수 생성 (스트레스 이벤트 발생 시 매크로 트렌드 동반 왜곡)
    macro_trend = 1.0 + (day * 0.0005)
    if is_stress and demand_mult > 1.0:
        macro_trend += 0.15  # 시장 과열 상태 표현
    macro_noise = rng.normal(loc=0.0, scale=0.02)
    macro_index = round(float(np.clip(macro_trend + macro_noise, 0.8, 1.5)), 3)

    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "virtual_date": current_date.strftime("%Y-%m-%d"),
        "day": day,
        "weather_index": weather_index,
        "macro_trend": macro_index,
        "stress_event": is_stress,
        "stress_description": crisis_desc
    })


@app.route("/api/lead-time", methods=["GET"])
def get_lead_time():
    # 1. day 기반 독립 RNG 확보
    day = int(request.args.get("day", 1))
    rng = get_seeded_rng(day)
    
    # 2. 시스템 공통 스트레스 이벤트에 따른 리드타임 가중치 확보
    _, _, lt_mult, _ = get_stress_multipliers(day)

    # 3. 베이스 라인 리드타임(7일)에 위기 배율 곱 연산
    base_loc = 7.0 * lt_mult
    lt = rng.normal(loc=base_loc, scale=1.0 if lt_mult == 1.0 else 2.0)
    
    # 조달 기간 한계 가드레일 (최소 2일)
    lead_time_days = round(float(max(2.0, lt)), 1)

    return jsonify({
        "day": day,
        "lead_time_days": lead_time_days,
        "unit": "days",
        "is_delayed_state": lt_mult > 1.0
    })


if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agents.config import NETWORK
    port = NETWORK["MOCK_API_PORT"]
    print(f" * SCM Mock API Server starting on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
