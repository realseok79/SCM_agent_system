# agents/integrity_agent.py
import datetime
from db import get_db_connection

def verify_stock_integrity(region_code: str, product_name: str, target_date_str: str = None) -> dict:
    """
    특정 날짜의 전산 재고 변동량(전날 재고 - 오늘 재고)과 
    실제 기록된 트랜잭션 출고량(daily_demand_stats)을 비교하여 
    유실(Shrinkage)이나 데이터 부정합을 감지합니다.
    """
    if target_date_str is None:
        target_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    # 어제 날짜 계산
    target_dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d")
    yesterday_str = (target_dt - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. 어제 재고와 오늘 재고 조회
        cursor.execute("""
            SELECT quantity FROM region_inventory
            WHERE region_code = ? AND product_name = ? AND date = ?
        """, (region_code, product_name, yesterday_str))
        row_yesterday = cursor.fetchone()
        
        cursor.execute("""
            SELECT quantity FROM region_inventory
            WHERE region_code = ? AND product_name = ? AND date = ?
        """, (region_code, product_name, target_date_str))
        row_today = cursor.fetchone()
        
        # 데이터가 둘 중 하나라도 없으면 분석 불가 (정상으로 간주하여 폴백)
        if not row_yesterday or not row_today:
            return {
                "has_discrepancy": False,
                "yesterday_qty": 0.0,
                "today_qty": 0.0,
                "computed_delta": 0.0,
                "actual_outbound": 0.0,
                "shrinkage_qty": 0.0,
                "message": "비교할 이전 또는 당일의 장부 재고 데이터가 부족합니다."
            }
            
        yesterday_qty = row_yesterday["quantity"]
        today_qty = row_today["quantity"]
        
        # 전산상 감소량 (전산 변동량)
        computed_delta = yesterday_qty - today_qty
        
        # 2. 실제 기록된 트랜잭션 출고 합계 조회
        cursor.execute("""
            SELECT daily_outbound_total FROM daily_demand_stats
            WHERE region_code = ? AND product_name = ? AND date = ?
        """, (region_code, product_name, target_date_str))
        row_demand = cursor.fetchone()
        actual_outbound = row_demand["daily_outbound_total"] if row_demand else 0.0
        
        # 3. 불일치(Shrinkage) 계산
        shrinkage_qty = computed_delta - actual_outbound
        
        # 4. 유실 자산 누수액(Cost_shrink) 산출 (특허 4번 재무 연산)
        cursor.execute("SELECT unit_price FROM product_financial_master WHERE product_name = ?", (product_name,))
        row_price = cursor.fetchone()
        unit_price = row_price["unit_price"] if row_price else 10000
        shrinkage_cost = shrinkage_qty * unit_price
        
        # 소수점 오차 방지
        has_discrepancy = abs(shrinkage_qty) > 0.01
        
        if has_discrepancy:
            if shrinkage_qty > 0:
                message = f"전산 변동량({computed_delta:.1f}개)과 실제 트랜잭션 출고량({actual_outbound:.1f}개)이 일치하지 않습니다. **{shrinkage_qty:.1f}개**의 원인 불명 유실(Shrinkage)이 의심되며, 예상 누수액은 **₩{shrinkage_cost:,.0f}** 입니다. 창고 실사를 권장합니다."
            else:
                message = f"경고: 실제 트랜잭션 출고량({actual_outbound:.1f}개)이 전산 재고 변동량({computed_delta:.1f}개)을 초과했습니다. 초과 출고 **{abs(shrinkage_qty):.1f}개** (₩{abs(shrinkage_cost):,.0f}) 에 대한 오기입 검토가 필요합니다."
        else:
            message = "전산 장부 재고 변동과 트랜잭션 출고 로그가 완벽히 일치하여 데이터 무결성이 검증되었습니다."
            
        return {
            "has_discrepancy": has_discrepancy,
            "yesterday_qty": yesterday_qty,
            "today_qty": today_qty,
            "computed_delta": computed_delta,
            "actual_outbound": actual_outbound,
            "shrinkage_qty": shrinkage_qty,
            "shrinkage_cost": shrinkage_cost,
            "message": message
        }
    except Exception as e:
        print(f"❌ [verify_stock_integrity] 에러 발생: {e}")
        return {
            "has_discrepancy": False,
            "yesterday_qty": 0.0,
            "today_qty": 0.0,
            "computed_delta": 0.0,
            "actual_outbound": 0.0,
            "shrinkage_qty": 0.0,
            "message": f"무결성 분석 도중 에러가 발생했습니다: {e}"
        }
    finally:
        conn.close()
