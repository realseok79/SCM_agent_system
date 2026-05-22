import os
import json
import math
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DecisionAgent:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self.client = genai.Client(api_key=self.api_key)
                self.model_name = "gemini-2.5-flash" # Use gemini 2.5 or 2.0 or 3.1
            except ImportError:
                self.client = None
                logger.warning("google-genai package not found. AI Decision will fallback to heuristics.")
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY not found. AI Decision will fallback to heuristics.")

    def calculate_q_final(self, 
                          current_inv: float, 
                          d90: float, 
                          safety_stock: float, 
                          moq: int, 
                          lot_size: int) -> int:
        """
        확정적(Deterministic) 수리 모델 기반 1차 발주량(Q_final) 산출 필터
        환각(Hallucination)을 원천 차단하기 위해 순수 수학적 연산만 수행합니다.
        """
        # 1. 목표 재고량 산출 (보수적 예측치 D90 + 안전재고)
        target_inventory = d90 + safety_stock
        
        # 2. 순 필요 발주량 (Current Inventory 차감)
        net_q = target_inventory - current_inv
        
        # 발주 필요 없음
        if net_q <= 0:
            return 0
            
        # 3. 제약 조건 필터링 (계단 함수 적용)
        # MOQ(최소발주량)과 Lot Size(포장단위)를 만족하는 이산적 발주량 도출
        q_discrete = math.ceil(net_q / lot_size) * lot_size
        q_final = max(moq, q_discrete)
        
        return int(q_final)

    def evaluate_risk(self, item_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Q_final 값을 넘겨받아 '인간 개입' 여부를 판정하는 처방적 분석 엔진
        """
        q_final = self.calculate_q_final(
            current_inv=context.get("current_inventory", 0),
            d90=context.get("d90", 0),
            safety_stock=context.get("safety_stock", 0),
            moq=context.get("moq", 1),
            lot_size=context.get("lot_size", 1)
        )

        if q_final == 0:
            return {
                "item_id": item_id,
                "recommended_qty": 0,
                "status": "AUTO_APPROVED",
                "reasoning": "재고가 충분하여 발주가 불필요함."
            }

        total_price = q_final * context.get("unit_price", 0)
        budget_limit = context.get("budget_limit", 5000000) # 기본 예산 임계치 500만원
        
        # 기본 컨텍스트 구성
        decision_context = {
            "item_id": item_id,
            "calculated_q_final": q_final,
            "total_order_amount": total_price,
            "budget_limit": budget_limit,
            "d10": context.get("d10", 0),
            "d90": context.get("d90", 0),
            "drift_score": context.get("drift_score", 0.0)
        }

        # 1. Fallback (결함 허용 아키텍처)
        if not self.client:
            return self._fallback_decision(decision_context)

        # 2. Gemini 3.1 Flash (or 2.0) 호출
        prompt = f"""
너는 글로벌 최고 수준의 SCM 리스크 관리 디렉터다. 감정을 배제하고 수치와 논리로만 판단하라.
다음 주어지는 컨텍스트를 바탕으로, 발주 상태를 'AUTO_APPROVED' 또는 'PENDING'으로 결정하라.

판단 기준:
1. 발주 총액이 예산({budget_limit}원) 이상이면 무조건 PENDING
2. 데이터 드리프트 스코어(drift_score)가 1.5 이상이면 무조건 PENDING
3. D90과 D10의 격차(불확실성)가 너무 크면 PENDING
위 리스크가 모두 낮다면 AUTO_APPROVED를 선택하라.

[컨텍스트]
{json.dumps(decision_context, ensure_ascii=False, indent=2)}

반드시 아래 JSON 스키마를 따르고, 어떠한 마크다운 백틱이나 인사말도 출력하지 마라.
reasoning은 한국어 50자 이내로 간결하게 작성하라.
{{
  "item_id": "{item_id}",
  "recommended_qty": {q_final},
  "status": "PENDING 또는 AUTO_APPROVED",
  "reasoning": "판단 사유 50자 이내"
}}
"""
        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0, # 결정론적 응답 강제
                )
            )
            
            # 파싱 보정
            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            result_dict = json.loads(result_text)
            
            # 안전장치: 응답 스키마 보정
            if "status" not in result_dict:
                raise ValueError("JSON response missing 'status'")
                
            return result_dict
            
        except Exception as e:
            logger.error(f"Decision Agent API Error: {e}")
            return self._fallback_decision(decision_context)

    def _fallback_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        네트워크 장애나 API 할당량 초과 시, 시스템 다운을 막기 위한 보수적(Conservative) Fallback
        """
        logger.warning("Triggering Fallback Decision Logic -> Force PENDING")
        return {
            "item_id": context.get("item_id"),
            "recommended_qty": context.get("calculated_q_final"),
            "status": "PENDING", # 보수적 선택
            "reasoning": "AI 통신 장애 및 예산 초과 리스크 방어를 위한 수동 검토 (Fallback)"
        }
