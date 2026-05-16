# agents/config.py
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
        "output_path": "outputs/order_list.json"
    }
}
