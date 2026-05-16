from dotenv import load_dotenv
from simulator.time_engine import TimeSimulator
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.action_agent import ActionAgent
from datetime import datetime

load_dotenv()

def run_pipeline(day: int, current_date: datetime, stress_event: dict):
    """
    시뮬레이터에서 매일 호출하는 파이프라인 콜백 함수
    """
    # 1. 데이터 수집 (외부 Mock API 및 내부 시뮬레이션 데이터)
    raw = DataAgent().collect(day, current_date, stress_event)
    
    # 2. 수요 분석 및 재고 신호 생성
    signal = AnalysisAgent().analyze(raw)
    
    # 3. 발주 실행 및 결과 기록
    ActionAgent().execute(signal)

if __name__ == "__main__":
    # 시뮬레이터 초기화 (환경 변수 SIMULATION_DAYS, SIMULATION_SPEED_SECONDS 참조)
    sim = TimeSimulator()
    
    # 파이프라인 실행
    sim.run(run_pipeline)
