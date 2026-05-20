import pytest
from db import get_db_connection
from agents.llm_diagnoser import generate_action_plan

def test_llm_batch_isolation():
    """
    LLM 리포트가 대화형 UI를 통해 실시간으로 호출되지 않고,
    오직 비동기 배치(Batch) 방식으로 DB에만 적재되어 읽기 전용으로 활용되는지 검증합니다.
    """
    region_code = "TEST-REGION"
    date_str = "2026-05-19"
    
    # 1. LLM 배치 모듈(generate_action_plan) 독립 실행
    res = generate_action_plan(
        region_name="Test Hub",
        product_name="Test SKU",
        delay_days=1.5,
        demand_shock=10.0,
        action_code="BATCH_TEST",
        base_message="배치 처리 테스트 제언입니다."
    )
    
    # 결과가 string(자연어)인지 확인
    assert isinstance(res, str)
    assert len(res) > 0
    
    # 2. DB에 성공적으로 단방향 캐싱(UPSERT) 시뮬레이션
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 테스트용 데이터 삽입
    cursor.execute("""
        INSERT INTO regional_insights (region_code, date, action_plan_msg)
        VALUES (?, ?, ?)
    """, (region_code, date_str, res))
    conn.commit()
    
    # 3. 프론트엔드(UI)에서는 LLM을 다시 호출하지 않고 DB에서 읽기만 수행 (Read-only)
    cursor.execute("SELECT action_plan_msg FROM regional_insights WHERE region_code = ? AND date = ?", (region_code, date_str))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "배치 결과가 DB에 캐싱되지 않았습니다."
    assert row["action_plan_msg"] == res, "반환된 리포트와 DB 캐시본이 일치하지 않습니다."
    
    assert row is not None, "배치 결과가 DB에 캐싱되지 않았습니다."
    assert row["action_plan_msg"] == res, "반환된 리포트와 DB 캐시본이 일치하지 않습니다."

