from agents.analysis_agent import AnalysisAgent
from dto.schemas import DataDTO, InventorySignalDTO

def test_analyze_demand():
    agent = AnalysisAgent()
    data = DataDTO(
        timestamp="2026-01-01T00:00:00",
        day=1,
        daily_demand=100.0,
        current_stock=100.0, # Less than ROP, should trigger order
        lead_time_days=7.0,
        weather_index=1.0,
        macro_trend=1.0,
        history_demand=[100.0],
        history_lead_time=[7.0],
        gdelt_risk_level="Low",
        gdelt_average_tone=0.0,
        gdelt_article_count=0,
        gdelt_top_headline="",
        trend_composite_score=0.0,
        trend_matched_count=0
    )
    result = agent.analyze(data)
    assert isinstance(result, InventorySignalDTO)
    assert result.day == 1
    assert result.optimal_order_qty > 0
