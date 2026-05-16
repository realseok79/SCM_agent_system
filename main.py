from dotenv import load_dotenv
from simulator.time_engine import TimeSimulator
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.action_agent import ActionAgent

load_dotenv()

def run_pipeline(day: int):
    # 각 에이전트의 메서드 이름은 이후 구현에 맞춰 변경될 수 있습니다.
    raw = DataAgent().collect(day)        # 이진석
    signal = AnalysisAgent().analyze(raw) # 박정우
    ActionAgent().execute(signal)         # 이진석

if __name__ == "__main__":
    sim = TimeSimulator()
    sim.run(run_pipeline)
