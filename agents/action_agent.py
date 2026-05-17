"""
agents/action_agent.py
----------------------
Action Agent: Analysis Agent의 연산 결과를 받아
동적 발주 스크립트(order_list.json)를 자동 생성하고 이력을 저장합니다.
초기 상태의 발산을 막는 절대 상한선(Absolute Ceiling)과 이동평균 상한선(Relative Ceiling)을
이중으로 적용하여 강력한 비즈니스 가드레일을 구축합니다.
"""

import json
import os
from datetime import datetime
from collections import deque

from dto.schemas import InventorySignalDTO, AlertLevel
from utils.logger import get_logger
from agents.config import PATHS, GUARDRAILS

logger = get_logger("ActionAgent")

# ── 환경 변수 및 임계값 ─────────────────────────────────
ORDER_OUTPUT_PATH = PATHS["ORDER_OUTPUT"]
REPORT_OUTPUT_PATH = PATHS["REPORT"]
HISTORY_OUTPUT_PATH = PATHS["ORDER_HISTORY"]

# 상대적 상한비 (계획서 요구사항: 30일 평균의 3배)
MAX_ORDER_CEILING_RATIO = GUARDRAILS["MAX_ORDER_CEILING_RATIO"]

# 절대적 상한선 (초기 상태 발산 방지 및 창고 물리적 한계치)
ABSOLUTE_MAX_CAPACITY = GUARDRAILS["ABSOLUTE_MAX_CAPACITY"]


class ActionAgent:
    """
    SCM 발주 실행 제어 에이전트
    """

    def __init__(self):
        self._order_history_30d: deque[float] = deque(maxlen=30)
        self._full_history: list[dict] = self._load_history()

        logger.info("ActionAgent 초기화 완료")
        logger.info(f"  제어 가드레일 (절대) : Max {ABSOLUTE_MAX_CAPACITY} units")
        logger.info(f"  제어 가드레일 (상대) : 30일 이동평균의 {MAX_ORDER_CEILING_RATIO}배")

    def _load_history(self) -> list[dict]:
        if os.path.exists(HISTORY_OUTPUT_PATH):
            with open(HISTORY_OUTPUT_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
            
            recent = [h["order_qty"] for h in history[-30:] if h.get("status") == "APPROVED"]
            self._order_history_30d = deque(recent, maxlen=30)
            logger.info(f"이전 발주 이력 복원 완료 (총 {len(history)}건)")
            return history
        return []

    def _validate_guardrail(self, order_qty: float) -> dict:
        """
        이중 가드레일(Dual Guardrail) 제어 로직
        1. 절대 상한선 검증 (물리적 한계)
        2. 상대 상한선 검증 (30일 이동평균 기반)
        """
        # 1. 절대 상한선 검증 (t < 5 인 초기 상태의 환각 발산 방지)
        if order_qty > ABSOLUTE_MAX_CAPACITY:
            reason = f"[절대 상한 초과] 요청 {order_qty:.0f} > 창고 최대 한계 {ABSOLUTE_MAX_CAPACITY:.0f}"
            logger.error(f"⛔ {reason}")
            return {
                "status": "BLOCKED",
                "reason": reason,
                "ceiling": ABSOLUTE_MAX_CAPACITY,
                "required_action": "관리자 즉시 개입 및 파라미터 재설정 요구"
            }

        # 2. 상대 상한선 검증
        if len(self._order_history_30d) < 5:
            logger.debug(f"초기 상태(t={len(self._order_history_30d)}) 상대 가드레일 보류 → APPROVED")
            return {"status": "APPROVED", "reason": "초기 상태 절대 상한 통과"}

        avg_30d = sum(self._order_history_30d) / len(self._order_history_30d)
        relative_ceiling = avg_30d * MAX_ORDER_CEILING_RATIO

        if order_qty > relative_ceiling:
            reason = f"[상대 상한 초과] 요청 {order_qty:.0f} > 동적 한계 {relative_ceiling:.0f} (평균 {avg_30d:.0f} × {MAX_ORDER_CEILING_RATIO})"
            logger.warning(f"⛔ {reason}")
            return {
                "status": "BLOCKED",
                "reason": reason,
                "avg_30d_order": round(avg_30d, 1),
                "ceiling": round(relative_ceiling, 1),
                "required_action": "관리자 수동 승인 필요"
            }

        return {
            "status": "APPROVED",
            "reason": "모든 가드레일 제어 조건 만족"
        }

    def _create_order(self, signal: InventorySignalDTO, guardrail: dict) -> dict:
        order = {
            "order_id": f"ORD-DAY{signal.day:03d}-{datetime.now().strftime('%H%M%S')}",
            "timestamp": signal.timestamp,
            "day": signal.day,
            "order_qty": signal.optimal_order_qty,
            "status": guardrail["status"],
            "guardrail_info": guardrail,
            "trigger": {
                "reorder_point": signal.reorder_point,
                "safety_stock": signal.safety_stock,
                "alert_level": signal.alert_level.value if isinstance(signal.alert_level, AlertLevel) else signal.alert_level,
            },
            "note": guardrail.get("required_action", "자동 발주 집행")
        }

        with open(ORDER_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(order, f, ensure_ascii=False, indent=2)

        return order

    def _issue_emergency_report(self, signal: InventorySignalDTO, order: dict) -> dict:
        current_level_str = signal.alert_level.value if isinstance(signal.alert_level, AlertLevel) else str(signal.alert_level)
        
        report = {
            "report_id": f"EMG-DAY{signal.day:03d}-{datetime.now().strftime('%H%M%S')}",
            "timestamp": signal.timestamp,
            "day": signal.day,
            "alert_level": current_level_str,
            "situation_summary": (
                f"{signal.day}일차 {current_level_str} 경보 발령 | "
                f"ROP: {signal.reorder_point:.0f} | SS: {signal.safety_stock:.0f}"
            ),
            "defense_scenarios": [
                {
                    "scenario": "A - 즉시 긴급 발주",
                    "action": f"최적 발주량 {signal.optimal_order_qty:.0f}개 즉시 집행",
                    "recommended": current_level_str == "CRITICAL"
                },
                {
                    "scenario": "B - 분할 발주",
                    "action": f"발주량 2회 분할",
                    "recommended": current_level_str == "WARNING"
                }
            ],
            "guardrail_status": order["status"]
        }

        daily_report_path = f"outputs/emergency_report_day{signal.day:03d}.json"
        with open(daily_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.warning(f"🚨 시스템 비상 모드 가동 [{current_level_str}] 리포트 발행 완료 ➔ {daily_report_path}")
        return report

    def _save_history(self, order: dict):
        self._full_history.append(order)
        if order["status"] == "APPROVED":
            self._order_history_30d.append(order["order_qty"])

        with open(HISTORY_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(self._full_history, f, ensure_ascii=False, indent=2)

    def execute(self, signal: InventorySignalDTO) -> dict:
        """
        제어 변수(승인된 발주량)를 시뮬레이터로 반환하여 상태 피드백 루프를 완성합니다.
        """
        if signal.alert_level == AlertLevel.NORMAL:
            return {
                "action": "NO_ORDER",
                "day": signal.day,
                "approved_qty": 0.0,
                "reason": f"현재 재고가 ROP({signal.reorder_point:.0f}) 위에서 안정적으로 유지 중"
            }

        guardrail = self._validate_guardrail(signal.optimal_order_qty)
        order = self._create_order(signal, guardrail)

        report = None
        if signal.alert_level in (AlertLevel.WARNING, AlertLevel.CRITICAL):
            report = self._issue_emergency_report(signal, order)

        self._save_history(order)

        approved_qty = signal.optimal_order_qty if guardrail["status"] == "APPROVED" else 0.0

        result = {
            "action": "ORDER_EXECUTED" if guardrail["status"] == "APPROVED" else "ORDER_BLOCKED",
            "day": signal.day,
            "approved_qty": approved_qty, 
            "order_id": order["order_id"],
            "emergency_report_issued": report is not None
        }

        logger.info(f"[{signal.day}일차] 액션: {result['action']} | 최종 집행량: {approved_qty:.0f}개")
        return result
