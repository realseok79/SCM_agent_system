# drift_monitor.py
import os
import sys
import json
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# FastAPI ML API URL 및 데이터 정의
ML_API_URL = os.environ.get("ML_API_URL", "http://localhost:8000")
DEFAULT_LEAD_TIME_DAYS = 7  # SCM 도메인 현실적 리드타임
DRIFT_THRESHOLD_MAPE = 15.0  # Drift 판정 임계치 (15%)

def calculate_drift_with_lead_time(predictions_df, actuals_df, lead_time_days=DEFAULT_LEAD_TIME_DAYS):
    """
    SCM 도메인의 시간차(Temporal Lag)를 역산하여 데이터 드리프트(Drift) 오차를 구동합니다.
    - t시점의 실제 판매량은 t - lead_time_days 시점에 AI가 예측했던 값과 정렬(Shift) 매칭되어야 합니다.
    """
    print(f"📊 Running Drift Calculation with Lead Time Shift: {lead_time_days} days...")
    
    # 날짜를 datetime 형식으로 포맷팅
    predictions_df['date'] = pd.to_datetime(predictions_df['date'])
    actuals_df['date'] = pd.to_datetime(actuals_df['date'])
    
    # [시간차 역산 정렬 핵심 로직]
    # 예측 데이터를 lead_time_days 만큼 미래로 이동시킵니다.
    # 즉, 5월 14일 예측값의 'date'를 5월 21일로 변환하여, 5월 21일 실제값과 1:1 병합(Merge)이 되도록 합니다.
    shifted_predictions = predictions_df.copy()
    shifted_predictions['matching_date'] = shifted_predictions['date'] + timedelta(days=lead_time_days)
    
    # 실제값 테이블과 matching_date 기준으로 결합
    merged = pd.merge(
        actuals_df, 
        shifted_predictions, 
        left_on='date', 
        right_on='matching_date', 
        suffixes=('_actual', '_pred')
    )
    
    if merged.empty:
        print("⚠️ 데이터가 부족하여 정렬된 매칭 데이터를 생성할 수 없습니다.")
        return None, None
        
    print(f"✅ 시간차 역산 정렬 완료. 총 {len(merged)}개의 데이터 쌍 매칭 성공.")
    
    # 오차 지표 연산 (MAE & MAPE)
    actual = merged['quantity_actual']
    pred = merged['quantity_pred']
    
    mae = np.mean(np.abs(actual - pred))
    
    # 분모가 0인 경우를 방지하여 MAPE 계산
    mape = np.mean(np.abs((actual - pred) / np.maximum(actual, 1.0))) * 100
    
    return float(mae), float(mape)

def trigger_automated_retraining(company_id="SIGMA", item_id="MASK_A01"):
    """
    데이터 드리프트 발생 시 FastAPI CT(/api/v1/ml/train) 엔드포인트를 호출하여 자동 재학습 파이프라인을 구동합니다.
    """
    print("🔄 Triggering Automated Continuous Training (CT) Pipeline...")
    # 지난 14일간의 가상 데이터를 재학습 데이터셋으로 넘겨 학습 수행
    dummy_sales = [
        {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), "qty": float(200 + i * 8 + np.random.randint(-20, 20))}
        for i in reversed(range(20))
    ]
    
    payload = {
        "company_id": company_id,
        "item_id": item_id,
        "historical_sales": dummy_sales,
        "hyperparameters": {
            "epochs": 10,
            "learning_rate": 0.001
        }
    }
    
    try:
        res = requests.post(f"{ML_API_URL}/api/v1/ml/train", json=payload, timeout=30)
        if res.status_code == 200:
            result = res.json()
            print(f"🎉 CT 파이프라인 전이 학습 완료! 가중치 저장 및 Hot-swap 성공.")
            print(f"   • 신규 모델 버전: {result['trained_model_version']}")
            print(f"   • 재학습 MAE: {result['metrics']['mae']:.4f}")
            return True
        else:
            print(f"❌ 자동 재학습 호출 실패: {res.text}")
    except Exception as e:
        print(f"❌ API 서버 연결 예외 발생: {e}")
    return False

def run_monitor():
    # 1. 가상 예측 이력 생성 (e.g. 5월 1일 ~ 5월 14일까지 AI가 예측한 값)
    pred_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 15)]
    pred_qtys = [250.0 + np.random.randint(-20, 20) for _ in pred_dates]
    predictions_df = pd.DataFrame({"date": pred_dates, "quantity": pred_qtys})
    
    # 2. 가상 실제 판매량 생성 (e.g. 5월 8일 ~ 5월 21일의 실제 판매 실적)
    actual_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 14)]
    
    # 유통 변동 시나리오 시뮬레이션:
    # 7일전(5월 14일)의 예측 대비 오늘의 실제 판매량을 급격하게 튀게(Drift) 설정함
    actual_qtys = []
    for d in actual_dates:
        # 최근 3일 동안 수요가 급증하는 시장 충격(Drift) 재현
        dt_val = datetime.strptime(d, "%Y-%m-%d")
        if (datetime.now() - dt_val).days <= 3:
            actual_qtys.append(420.0 + np.random.randint(-30, 30)) # 수요 급증 (Drift)
        else:
            actual_qtys.append(260.0 + np.random.randint(-20, 20)) # 정상 수요
            
    actuals_df = pd.DataFrame({"date": actual_dates, "quantity": actual_qtys})
    
    # 3. 시간차(Temporal Lag)를 반영한 Drift 오차 계산
    mae, mape = calculate_drift_with_lead_time(predictions_df, actuals_df, lead_time_days=DEFAULT_LEAD_TIME_DAYS)
    
    if mae is None or mape is None:
        print("❌ 드리프트 분석이 무산되었습니다.")
        return
        
    print(f"📈 [Drift Result] Shifted MAE: {mae:.2f} | Shifted MAPE: {mape:.2f}%")
    
    # 4. 임계치 판단 및 CT 트리거 제어
    if mape > DRIFT_THRESHOLD_MAPE:
        print(f"🚨 [ALERT] 데이터 드리프트 심각화! MAPE {mape:.2f}% > 임계치 {DRIFT_THRESHOLD_MAPE}% 초과.")
        trigger_automated_retraining()
    else:
        print("✅ [OK] SCM 예측 모형 상태 양호. 예측 오차가 가드라인 이내에서 안전 통제되고 있습니다.")

if __name__ == "__main__":
    run_monitor()
