import json
from dotenv import load_dotenv

# Load env variables for GEMINI_API_KEY
load_dotenv()

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.decision_agent import DecisionAgent

def run_tests():
    agent = DecisionAgent()
    print("🚀 SCM 하이브리드 AI: Decision Agent 테스트 시작\n")
    
    # Test 1: AUTO_APPROVED Scenario
    print("--- [테스트 1] 정상 수요 & 예산 이내 (AUTO_APPROVED 기대) ---")
    context_normal = {
        "current_inventory": 200,
        "d10": 500,
        "d50": 600,
        "d90": 700,
        "safety_stock": 100,
        "moq": 100,
        "lot_size": 50,
        "unit_price": 5000, # 5000원
        "budget_limit": 5000000,
        "drift_score": 0.5
    }
    # Expected: Target = 700 + 100 = 800
    # Net_Q = 800 - 200 = 600
    # Q_discrete = ceil(600/50)*50 = 600. max(100, 600) = 600.
    # Total Price = 600 * 5000 = 3,000,000원 (< 5M)
    res_normal = agent.evaluate_risk("ITEM_NORMAL", context_normal)
    print(json.dumps(res_normal, indent=2, ensure_ascii=False))
    
    # Test 2: PENDING Scenario (Budget Exceeded)
    print("\n--- [테스트 2] 대량 발주로 인한 예산 초과 리스크 (PENDING 기대) ---")
    context_budget = context_normal.copy()
    context_budget["d90"] = 2500
    # Target = 2600. Net = 2400. Q = 2400.
    # Total = 2400 * 5000 = 12,000,000원 (> 5M)
    res_budget = agent.evaluate_risk("ITEM_EXPENSIVE", context_budget)
    print(json.dumps(res_budget, indent=2, ensure_ascii=False))
    
    # Test 3: PENDING Scenario (High Drift Score)
    print("\n--- [테스트 3] 데이터 드리프트 스코어 이상 감지 (PENDING 기대) ---")
    context_drift = context_normal.copy()
    context_drift["drift_score"] = 2.0
    res_drift = agent.evaluate_risk("ITEM_DRIFT", context_drift)
    print(json.dumps(res_drift, indent=2, ensure_ascii=False))
    
    # Test 4: FALLBACK Scenario (API 장애 시뮬레이션)
    print("\n--- [테스트 4] 구글 API 연결 끊김 시뮬레이션 (무조건 PENDING 기대) ---")
    agent.client = None # Force fallback
    res_fallback = agent.evaluate_risk("ITEM_FALLBACK", context_normal)
    print(json.dumps(res_fallback, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_tests()
