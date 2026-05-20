# agents/llm_diagnoser.py
import os
from dotenv import load_dotenv

load_dotenv()

def generate_action_plan(
    region_name: str,
    product_name: str,
    delay_days: float,
    demand_shock: float,
    action_code: str,
    base_message: str
) -> str:
    """
    SCM 의사결정 점수와 규칙을 문장화하는 LLM 에이전트.
    OPENAI_API_KEY가 존재할 시 GPT API를 호출해 한 줄짜리 가독성 높은 리포트를 생성하며,
    없을 경우 제공된 기성 템플릿(base_message)을 기본 반환합니다.
    
    Pro-tip: 
      - 핵심 수치는 볼드체(**)로 표시.
      - 한 문장으로 간결하게 작성할 것.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return base_message

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, timeout=3.0)
        
        prompt = f"""
[SCM Decision Rule Output]
지점: {region_name}
품목명: {product_name}
예상 조달 지연일: {delay_days}일
예상 수요 변동률: {demand_shock}%
추천 조치 코드: {action_code}
기본 추천 메시지: {base_message}

위 데이터를 기반으로, 현업 물류 관리자가 직관적으로 이해하고 당장 수행할 수 있는 '한 줄짜리' 최종 SCM 조치 처방전(Action Plan)을 작성해 주십시오.

[작성 제약사항]
1. 반드시 '한 문장'으로만 간결하게 작성할 것. (접두사나 추가 서술 배제)
2. 지연 일수, 증감 비율, 발주 권장 수량 등의 핵심 수치는 반드시 볼드체(예: **3.5일**, **20%**, **500개**)로 강조할 것.
3. 전문적이고 단호한 물류 관리 어조를 유지할 것.
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional supply chain management (SCM) expert and decision engine."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.2
        )
        plan = response.choices[0].message.content.strip()
        if plan:
            return plan
    except Exception as e:
        # API 오류 시 안전하게 기본 메시지 반환
        print(f"[LLM Diagnoser] API call failed: {e}")
        
    return base_message
