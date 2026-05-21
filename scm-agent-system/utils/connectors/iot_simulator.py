# utils/connectors/iot_simulator.py
import random
from collections import deque
import numpy as np

# 노이즈 차단을 위한 각 지역별 센서 채널의 EMA(Exponential Moving Average) 캐시
# Key: {region_code}_{sensor_type} -> Deque of raw values or current filtered value
_sensor_ema_cache = {}
EMA_ALPHA = 0.3  # 로우패스 필터 가중치 (새 값 반영 비중 30%, 이전 상태 유지 70%)

class IoTSensorSimulator:
    """
    산업 현장(Shop Floor) 창고 환경 모니터링 IoT 센서 시뮬레이터.
    - 온도(°C), 습도(%), 진동(g), RFID 스캔 속도(scans/hr) 시뮬레이션
    - 로우패스 필터(EMA)를 활용해 노이즈/일시적 스파이크(Spike) 필터링
    - 건강 지수(Warehouse Health Score, 0~100) 산출
    """
    SENSOR_PROFILES = {
        "temperature": {"mean": 22.0, "std": 1.5, "unit": "°C", "alert_min": 10.0, "alert_max": 30.0},
        "humidity":    {"mean": 45.0, "std": 5.0, "unit": "%",  "alert_min": 30.0, "alert_max": 65.0},
        "vibration":  {"mean": 0.2,  "std": 0.05, "unit": "g",  "alert_min": 0.0,  "alert_max": 0.8},
        "rfid_count":  {"mean": 150.0, "std": 20.0, "unit": "scans/hr", "alert_min": 80.0, "alert_max": 250.0},
    }

    def generate_raw_reading(self, sensor_type: str) -> float:
        """가우시안 분포 기반 원시 센서값 생성 (10% 확률로 순간 스파이크/노이즈 주입)"""
        profile = self.SENSOR_PROFILES[sensor_type]
        val = random.gauss(profile["mean"], profile["std"])
        
        # 10% 확률로 비정상 노이즈 스파이크 주입 (센서 순간 오작동 가정)
        if random.random() < 0.10:
            spike_direction = 1 if random.random() > 0.5 else -1
            # 정상 분포 표준편차의 5~7배에 달하는 노이즈 스파이크
            val += spike_direction * profile["std"] * random.uniform(5.0, 7.0)
            
        return val

    def get_filtered_reading(self, region_code: str, sensor_type: str) -> float:
        """
        일시적 노이즈를 완전 차단하기 위해 1차 로우패스 IIR 필터 (EMA) 적용
        y[t] = alpha * x[t] + (1 - alpha) * y[t-1]
        """
        raw_val = self.generate_raw_reading(sensor_type)
        cache_key = f"{region_code}_{sensor_type}"
        
        if cache_key not in _sensor_ema_cache:
            # 초기화 시점에는 raw 값을 그대로 시작값으로 사용
            _sensor_ema_cache[cache_key] = raw_val
        else:
            prev_filtered = _sensor_ema_cache[cache_key]
            # 로우패스 필터 수식 적용하여 스파이크 감쇠
            filtered = EMA_ALPHA * raw_val + (1.0 - EMA_ALPHA) * prev_filtered
            _sensor_ema_cache[cache_key] = filtered
            
        return _sensor_ema_cache[cache_key]

    def get_warehouse_health_score(self, region_code: str) -> dict:
        """
        특정 지역 창고의 필터링된 센서 세트 읽기 및 통합 건강 스코어(0~100) 산출.
        - 각 센서가 정상 임계치를 벗어난 정도를 감점(Penalty)화 하여 산식 계산.
        """
        readings = {}
        penalty_sum = 0.0
        
        for s_type, profile in self.SENSOR_PROFILES.items():
            val = self.get_filtered_reading(region_code, s_type)
            readings[s_type] = round(val, 2)
            
            # 정상 범위(alert_min, alert_max) 이탈 정도 계산
            if val < profile["alert_min"]:
                deviation = (profile["alert_min"] - val) / profile["alert_min"]
                penalty_sum += deviation * 25.0  # 최대 감점 가중치
            elif val > profile["alert_max"]:
                deviation = (val - profile["alert_max"]) / profile["alert_max"]
                penalty_sum += deviation * 30.0  # 최대 감점 가중치
                
        # 기본 100점에서 이탈 페널티 차감 (최하점 0점 방어)
        health_score = max(0.0, min(100.0, 100.0 - penalty_sum))
        
        return {
            "region_code": region_code,
            "readings": readings,
            "warehouse_health_score": round(health_score, 1),
            "status": "STABLE" if health_score >= 80.0 else ("WARNING" if health_score >= 50.0 else "CRITICAL")
        }
