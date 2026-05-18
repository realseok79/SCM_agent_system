# agents/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# SCM Agent System - Central Configuration Hub

# ── Paths Configuration
PATHS = {
    "SCM_DATA": os.getenv("SCM_DATA_PATH", "outputs/scm_dummy_data.json"),
    "ORDER_OUTPUT": os.getenv("ORDER_OUTPUT_PATH", "outputs/order_list.json"),
    "ORDER_HISTORY": os.getenv("HISTORY_OUTPUT_PATH", "outputs/order_history.json"),
    "REPORT": os.getenv("REPORT_OUTPUT_PATH", "outputs/emergency_report.json"),
    "EMERGENCY_DIR": "outputs",
    "WMO_CSV": "data/wmo_station_master.csv",
    "ENTERPRISE_DB": "data/sigma_enterprise.db",
}

# ── Network Settings
NETWORK = {
    "MOCK_API_HOST": os.getenv("MOCK_API_HOST", "http://localhost:8080"),
    "MOCK_API_PORT": int(os.getenv("MOCK_API_PORT", 8080)),
}

# ── Simulation Settings
SIMULATION = {
    "DAYS": int(os.getenv("SIMULATION_DAYS", 100)),
    "SPEED_SECONDS": float(os.getenv("SIMULATION_SPEED_SECONDS", 300)),
}

# ── Guardrails Settings
GUARDRAILS = {
    "MAX_ORDER_CEILING_RATIO": float(os.getenv("MAX_ORDER_CEILING_RATIO", 3.0)),
    "ABSOLUTE_MAX_CAPACITY": float(os.getenv("ABSOLUTE_MAX_CAPACITY", 5000.0)),
}

# ── Agent Configurations
AGENT_CONFIG = {
    "data_agent": {
        "name": "DataAgent",
        "role": "데이터 수집 및 전처리 전담",
        "input_sources": ["virtual_erp_db", "mock_api_server"],
        "output_format": "standard_dataframe_dto"
    },
    "analysis_agent": {
        "name": "AnalysisAgent",
        "role": "확률론적 수요 예측 및 ROP 연산 전담",
        "input_format": "standard_dataframe_dto",
        "output_format": "inventory_signal_dto"
    },
    "action_agent": {
        "name": "ActionAgent",
        "role": "발주 스크립트 실행 및 리포트 발행 전담",
        "input_format": "inventory_signal_dto",
        "output_path": PATHS["ORDER_OUTPUT"]
    }
}

# ── Automatic directory creation on initialization (User Feedback)
os.makedirs("outputs", exist_ok=True)
os.makedirs("data", exist_ok=True)
