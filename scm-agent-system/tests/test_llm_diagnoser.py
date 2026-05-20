# tests/test_llm_diagnoser.py
import re
from agents.llm_diagnoser import generate_action_plan


def test_generate_action_plan_fallback(monkeypatch):
    """OPENAI_API_KEY 미설정 시 base_message를 그대로 반환하는 Fallback 검증."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    base_msg = "안전 재고 수준을 평소보다 15% 상향 조정하십시오."
    plan = generate_action_plan(
        region_name="Seoul Hub",
        product_name="Mask",
        delay_days=3.5,
        demand_shock=15.0,
        action_code="REORDER_UP_15",
        base_message=base_msg
    )
    
    assert plan == base_msg


def test_generate_action_plan_llm_success(monkeypatch):
    """Mock OpenAI 클라이언트를 통해 LLM 경로가 정상 작동하는지 검증.
    비결정론적 응답 대신 구조적 불변성(Invariant)만 확인합니다."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-test-key")

    llm_response = "**서울 허브** 마스크 품목의 조달 지연 **3.5일**이 예상되므로, 안전 재고를 **15%** 상향 조정한 긴급 발주를 즉시 실행하십시오."

    class MockMessage:
        content = llm_response

    class MockChoice:
        message = MockMessage()

    class MockCompletion:
        choices = [MockChoice()]

    class MockChatCompletions:
        def create(self, *args, **kwargs):
            return MockCompletion()

    class MockChat:
        completions = MockChatCompletions()

    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            # timeout=3.0 이 전달되었는지 확인
            assert kwargs.get("timeout") == 3.0, "서킷 브레이커 timeout이 3.0s로 설정되어야 합니다."
            self.chat = MockChat()

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)

    plan = generate_action_plan(
        region_name="Seoul Hub",
        product_name="Mask",
        delay_days=3.5,
        demand_shock=15.0,
        action_code="REORDER_UP_15",
        base_message="기본 메시지"
    )

    # 불변성 검증: LLM 경로를 통과하면 기본 메시지가 아닌 다른 값이 반환되어야 함
    assert plan != "기본 메시지"
    # 불변성 검증: 볼드 마크다운(**...**)이 포함되어야 함
    assert re.search(r'\*\*.+\*\*', plan), "LLM 응답에 볼드체 강조가 포함되어야 합니다."
    # 불변성 검증: 비어 있지 않아야 함
    assert len(plan) > 10


def test_generate_action_plan_api_timeout_fallback(monkeypatch):
    """API 타임아웃/예외 발생 시 base_message로 안전하게 회귀하는 서킷 브레이커 검증."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-test-key")

    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = self

        @property
        def completions(self):
            return self

        def create(self, *args, **kwargs):
            raise TimeoutError("Connection timed out (서킷 브레이커 시뮬레이션)")

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)

    base_msg = "타임아웃 시 이 메시지가 반환되어야 합니다."
    plan = generate_action_plan(
        region_name="Busan Hub",
        product_name="Chip",
        delay_days=5.0,
        demand_shock=25.0,
        action_code="EMERGENCY_ORDER",
        base_message=base_msg
    )

    assert plan == base_msg, "API 타임아웃 시 base_message로 안전하게 회귀해야 합니다."
