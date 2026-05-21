# tests/test_data_drift_temporal.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from drift_monitor import calculate_drift_with_lead_time

def test_calculate_drift_with_lead_time_exact():
    # 1. 가상 예측 이력 생성 (t시점의 예측)
    pred_dates = ["2026-05-01", "2026-05-02", "2026-05-03"]
    pred_qtys = [100.0, 110.0, 120.0]
    predictions_df = pd.DataFrame({"date": pred_dates, "quantity": pred_qtys})
    
    # 2. 가상 실제 판매량 생성 (t + 7시점의 실제 판매량)
    # 리드타임이 7일이므로, 5월 1일 예측값(100.0)은 5월 8일 실제값과 매칭되어야 합니다.
    actual_dates = ["2026-05-08", "2026-05-09", "2026-05-10"]
    actual_qtys = [105.0, 108.0, 125.0]
    actuals_df = pd.DataFrame({"date": actual_dates, "quantity": actual_qtys})
    
    # 3. 리드타임 7일을 적용하여 Drift 계산
    mae, mape = calculate_drift_with_lead_time(predictions_df, actuals_df, lead_time_days=7)
    
    # 매칭 관계:
    # (Pred) 5월 1일 (100) -> 5월 8일 매칭 -> (Actual) 5월 8일 (105) : 오차 = 5
    # (Pred) 5월 2일 (110) -> 5월 9일 매칭 -> (Actual) 5월 9일 (108) : 오차 = 2
    # (Pred) 5월 3일 (120) -> 5월 10일 매칭 -> (Actual) 5월 10일 (125) : 오차 = 5
    # MAE = (5 + 2 + 5) / 3 = 4.0
    # MAPE = ( (5/105) + (2/108) + (5/125) ) / 3 * 100 %
    expected_mae = (5 + 2 + 5) / 3.0
    expected_mape = ((5/105.0) + (2/108.0) + (5/125.0)) / 3.0 * 100.0
    
    assert mae is not None
    assert mape is not None
    assert pytest.approx(mae, 0.01) == expected_mae
    assert pytest.approx(mape, 0.01) == expected_mape

def test_calculate_drift_no_match():
    pred_dates = ["2026-05-01", "2026-05-02"]
    pred_qtys = [100.0, 110.0]
    predictions_df = pd.DataFrame({"date": pred_dates, "quantity": pred_qtys})
    
    # 날짜가 어긋나 매칭이 되지 않도록 설정
    actual_dates = ["2026-05-01", "2026-05-02"]
    actual_qtys = [100.0, 110.0]
    actuals_df = pd.DataFrame({"date": actual_dates, "quantity": actual_qtys})
    
    mae, mape = calculate_drift_with_lead_time(predictions_df, actuals_df, lead_time_days=7)
    
    assert mae is None
    assert mape is None
