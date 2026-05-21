# agents/baseline_agent.py
import numpy as np
import pandas as pd

class BaselineAgent:
    def __init__(self):
        pass

    def run_simulation(self, sku, unit_price, holding_cost, base_demand=40.0, lead_time=3, initial_stock=300.0, days=100, alpha_factor=1.0):
        """
        주어진 SKU에 대해 100일 동안의 대조군(이동평균) vs 실험군(확률론적 AI) 재고 및 비용 시뮬레이션을 수행합니다.
        
        비용 파라미터:
        - Ordering Cost (회당 고정): unit_price * 0.1 (약 10% 수준)
        - Shortage Penalty Cost (개당): unit_price * 1.5 (품절 시 기회 비용 및 긴급 수송 비용 반영)
        - Holding Cost (개당/일): holding_cost
        """
        np.random.seed(42)  # 시뮬레이션 재현성 확보

        # 일일 수요 생성 (포아송 분포 적용)
        # 평일/주말 및 무작위 노이즈를 포함한 포아송 파라미터(lambda) 설정
        demand_series = np.random.poisson(lam=base_demand, size=days)
        
        # 1. 30일 이동평균 대조군 시뮬레이션 (Baseline)
        control_stock = float(initial_stock)
        control_history = []
        control_orders_pending = [] # (delivery_day, qty)
        control_order_count = 0
        control_shortage_units = 0.0

        # 초기 30일 이동평균 계산용 이력 (시뮬레이션 시작 전 30일 동안 평균 base_demand 발생했다고 가정)
        demand_history = list(np.random.normal(loc=base_demand, scale=base_demand*0.1, size=30))

        # 2. 포아송 확률론적 실험군 시뮬레이션 (AI + Guardrail)
        test_stock = float(initial_stock)
        test_history = []
        test_orders_pending = []
        test_order_count = 0
        test_shortage_units = 0.0
        
        # AI 가드레일 임계값 (Day 4의 파라미터 보정 시뮬레이션 결합)
        # alpha_factor는 ROP 보정 계수
        for day in range(days):
            today_demand = demand_series[day]

            # ------------------------------------------------
            # [대조군 로직]
            # ------------------------------------------------
            # 미결 주문 입고 처리
            arrived_control = sum(qty for del_day, qty in control_orders_pending if del_day == day)
            control_stock += arrived_control
            control_orders_pending = [item for item in control_orders_pending if item[0] != day]

            # 수요 발생 및 품절 연산
            if control_stock >= today_demand:
                control_stock -= today_demand
                shortage_c = 0.0
            else:
                shortage_c = today_demand - control_stock
                control_stock = 0.0
                control_shortage_units += shortage_c

            # 30일 이동평균 기반 ROP 계산
            moving_avg = np.mean(demand_history[-30:])
            rop_control = moving_avg * lead_time
            eoq_control = base_demand * 5  # 고정 발주량

            # 발주 의사 결정 (ROP 미달 시 발주)
            total_on_hand_control = control_stock + sum(qty for _, qty in control_orders_pending)
            if total_on_hand_control < rop_control:
                control_orders_pending.append((day + lead_time, eoq_control))
                control_order_count += 1

            # 이동평균 히스토리 갱신
            demand_history.append(today_demand)
            control_history.append({
                "day": day + 1,
                "stock": control_stock,
                "demand": today_demand,
                "shortage": shortage_c,
                "order_triggered": 1 if total_on_hand_control < rop_control else 0
            })

            # ------------------------------------------------
            # [실험군 로직 (AI + Dynamic ROP)]
            # ------------------------------------------------
            # 미결 주문 입고 처리
            arrived_test = sum(qty for del_day, qty in test_orders_pending if del_day == day)
            test_stock += arrived_test
            test_orders_pending = [item for item in test_orders_pending if item[0] != day]

            # 수요 발생 및 품절 연산
            if test_stock >= today_demand:
                test_stock -= today_demand
                shortage_t = 0.0
            else:
                shortage_t = today_demand - test_stock
                test_stock = 0.0
                test_shortage_units += shortage_t

            # AI Dynamic ROP:
            # - 기본 리드타임에 기상이변이나 물류 지연 가중치(1.5배)를 시뮬레이션 요일에 따라 동적 부여
            # - alpha_factor 보정 계수를 반영하여 ROP의 임계치를 최적화 조율
            day_lead_time = lead_time
            if day in [30, 31, 32, 60, 61, 62]:  # 특정 구간 물류 마비 시뮬레이션
                day_lead_time = int(lead_time * 1.8)

            # 포아송 안전재고(95% 서비스 수준 Z=1.65 적용) ROP 계산
            std_demand = np.sqrt(base_demand) # 포아송의 표준편차는 sqrt(lambda)
            rop_test = (base_demand * day_lead_time) + (1.65 * std_demand * np.sqrt(day_lead_time))
            rop_test = rop_test * alpha_factor  # 가드레일 보정 factor 적용

            eoq_test = np.sqrt((2 * (base_demand * 365) * (unit_price * 0.1)) / (holding_cost * 365)) # 수학적 EOQ 최적 주문량
            if eoq_test < 50:
                eoq_test = base_demand * 5

            # 발주 의사 결정
            total_on_hand_test = test_stock + sum(qty for _, qty in test_orders_pending)
            if total_on_hand_test < rop_test:
                test_orders_pending.append((day + lead_time, eoq_test))
                test_order_count += 1

            test_history.append({
                "day": day + 1,
                "stock": test_stock,
                "demand": today_demand,
                "shortage": shortage_t,
                "order_triggered": 1 if total_on_hand_test < rop_test else 0
            })

        # ------------------------------------------------
        # 비용 정량적 요약 계산
        # ------------------------------------------------
        # 1. 대조군 비용
        avg_stock_c = np.mean([h["stock"] for h in control_history])
        holding_cost_c = avg_stock_c * holding_cost * days
        ordering_cost_c = control_order_count * (unit_price * 0.1)
        shortage_cost_c = control_shortage_units * (unit_price * 1.5)
        total_cost_c = holding_cost_c + ordering_cost_c + shortage_cost_c

        # 2. 실험군 비용
        avg_stock_t = np.mean([h["stock"] for h in test_history])
        holding_cost_t = avg_stock_t * holding_cost * days
        ordering_cost_t = test_order_count * (unit_price * 0.1)
        shortage_cost_t = test_shortage_units * (unit_price * 1.5)
        total_cost_t = holding_cost_t + ordering_cost_t + shortage_cost_t

        return {
            "control": {
                "history": control_history,
                "avg_stock": avg_stock_c,
                "order_count": control_order_count,
                "shortage_units": control_shortage_units,
                "holding_cost": holding_cost_c,
                "ordering_cost": ordering_cost_c,
                "shortage_cost": shortage_cost_c,
                "total_cost": total_cost_c
            },
            "test": {
                "history": test_history,
                "avg_stock": avg_stock_t,
                "order_count": test_order_count,
                "shortage_units": test_shortage_units,
                "holding_cost": holding_cost_t,
                "ordering_cost": ordering_cost_t,
                "shortage_cost": shortage_cost_t,
                "total_cost": total_cost_t
            }
        }
