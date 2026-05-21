# tests/test_ml_agent.py
import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_ml_map_schema_exact():
    """
    Test Sentence-BERT schema mapping with raw headers
    """
    payload = {
        "company_id": "SIGMA",
        "raw_headers": ["지점", "품목", "수량", "날짜", "담당자이름"],
        "standard_columns": ["region_code", "product_name", "quantity", "date"]
    }
    response = client.post("/api/v1/ml/map-schema", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "mapping" in data
    assert "mapping_confidence" in data
    
    # Exact/alias matches should succeed
    assert data["mapping"]["지점"] == "region_code"
    assert data["mapping"]["품목"] == "product_name"
    assert data["mapping"]["수량"] == "quantity"
    assert data["mapping"]["날짜"] == "date"
    
    # Unmapped should be "UNMAPPED" or None (handled as UNMAPPED in mapping response)
    assert data["mapping"]["담당자이름"] == "UNMAPPED"


def test_ml_anomaly_score():
    """
    Test Isolation Forest anomaly detection for IoT logs
    """
    payload = {
        "telemetry_logs": [
            {"temperature": 22.5, "humidity": 45.0, "vibration": 0.05},
            {"temperature": 22.8, "humidity": 45.5, "vibration": 0.04},
            {"temperature": 23.0, "humidity": 46.0, "vibration": 0.06},
            {"temperature": 22.4, "humidity": 44.8, "vibration": 0.05},
            {"temperature": 22.6, "humidity": 45.2, "vibration": 0.04},
            {"temperature": 99.0, "humidity": 99.0, "vibration": 9.99}  # Clearly an outlier
        ]
    }
    response = client.post("/api/v1/ml/anomaly-score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "is_anomaly" in data
    assert "anomaly_scores" in data
    assert len(data["is_anomaly"]) == 6
    # The last one should be detected as anomalous (-1)
    assert data["is_anomaly"][-1] == -1


def test_ml_predict_leadtime():
    """
    Test XGBoost Lead Time Prediction
    """
    payload = {
        "route_id": "ROUTE_SEOUL_BUSAN",
        "weather_score": 5.5,
        "port_congestion_score": 25.0,
        "historical_lead_times": [2.5, 3.0, 2.8, 3.2, 2.9]
    }
    response = client.post("/api/v1/ml/predict-leadtime", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_lead_time_days" in data
    assert "feature_importance" in data
    assert data["predicted_lead_time_days"] > 0.0


def test_ml_predict_demand():
    """
    Test Prophet Demand forecasting
    """
    payload = {
        "dates": [
            "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04",
            "2026-05-05", "2026-05-06", "2026-05-07"
        ],
        "quantities": [10.0, 12.0, 11.0, 15.0, 14.0, 13.0, 16.0],
        "forecast_days": 3
    }
    response = client.post("/api/v1/ml/predict-demand", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ds" in data
    assert "yhat" in data
    assert len(data["ds"]) == 3
    assert len(data["yhat"]) == 3

def test_ml_predict_demand_hybrid():
    """
    Test hybrid demand prediction endpoint (TFT & Pinball Loss format)
    """
    payload = {
        "item_id": "SemiConductor_A",
        "region_code": "KR-SL",
        "recent_sales": [
            {"date": "2026-05-18", "qty": 12.0},
            {"date": "2026-05-19", "qty": 15.0},
            {"date": "2026-05-20", "qty": 14.0}
        ],
        "future_events": [
            {"date": "2026-05-22", "is_holiday": True, "event_type": "Chuseok"}
        ]
    }
    response = client.post("/api/v1/ml/predict-demand-hybrid", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "SemiConductor_A"
    assert data["region_code"] == "KR-SL"
    assert "predicted_demand_10" in data
    assert "predicted_demand_50" in data
    assert "predicted_demand_90" in data
    assert "shap_values" in data
    assert "global_base_v1.0" in data["model_version"]
    assert data["predicted_demand_90"] >= data["predicted_demand_50"]
    assert data["predicted_demand_50"] >= data["predicted_demand_10"]

def test_ml_train_model():
    """
    Test fine-tuning model training endpoint
    """
    payload = {
        "company_id": "SIGMA",
        "item_id": "SemiConductor_A",
        "historical_sales": [
            {"date": "2026-05-01", "qty": 10.0},
            {"date": "2026-05-02", "qty": 11.0},
            {"date": "2026-05-03", "qty": 12.0},
            {"date": "2026-05-04", "qty": 13.0},
            {"date": "2026-05-05", "qty": 14.0},
            {"date": "2026-05-06", "qty": 15.0},
            {"date": "2026-05-07", "qty": 16.0},
            {"date": "2026-05-08", "qty": 17.0},
            {"date": "2026-05-09", "qty": 18.0},
            {"date": "2026-05-10", "qty": 19.0},
            {"date": "2026-05-11", "qty": 20.0},
            {"date": "2026-05-12", "qty": 21.0},
            {"date": "2026-05-13", "qty": 22.0},
            {"date": "2026-05-14", "qty": 23.0}
        ],
        "hyperparameters": {
            "learning_rate": 0.002,
            "epochs": 20
        }
    }
    response = client.post("/api/v1/ml/train", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "Model fine-tuning completed successfully." in data["message"]
    assert "global_tuned_SIGMA_SemiConductor_A" in data["trained_model_version"]
    assert "loss" in data["metrics"]
    assert "mae" in data["metrics"]

def test_ml_train_model_insufficient_data():
    """
    Test fine-tuning model fails when historical sales records < 14
    """
    payload = {
        "company_id": "SIGMA",
        "item_id": "SemiConductor_A",
        "historical_sales": [
            {"date": "2026-05-01", "qty": 10.0}
        ]
    }
    response = client.post("/api/v1/ml/train", json=payload)
    assert response.status_code == 400
    assert "Fine-tuning requires at least 14 days of historical sales." in response.json()["detail"]


