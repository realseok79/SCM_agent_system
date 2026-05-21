# utils/demand_tracker.py
import datetime
from db import get_db_connection

def log_stock_out(region_code: str, product_name: str, outbound_qty: float, transaction_type: str = "정상출고") -> bool:
    """
    출고 트랜잭션을 기록(stock_out_logs)하는 함수
    """
    if outbound_qty <= 0:
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stock_out_logs (region_code, product_name, outbound_qty, transaction_type)
            VALUES (?, ?, ?, ?)
        """, (region_code, product_name, outbound_qty, transaction_type))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ [log_stock_out] 에러 발생: {e}")
        return False
    finally:
        conn.close()

def log_stock_out_bulk(logs: list[dict]) -> bool:
    """
    출고 트랜잭션 목록을 Bulk Insert(executemany) 방식으로 일괄 기록하는 함수
    """
    if not logs:
        return True
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO stock_out_logs (region_code, product_name, outbound_qty, transaction_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, [(log["region_code"], log["product_name"], log["outbound_qty"], log.get("transaction_type", "정상출고"), log["timestamp"]) for log in logs])
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ [log_stock_out_bulk] 에러 발생: {e}")
        return False
    finally:
        conn.close()

def aggregate_daily_demand(target_date_str: str = None) -> bool:
    """
    특정 날짜(기본값: 오늘)의 출고 데이터를 집계하여 daily_demand_stats 테이블에 적재하고,
    최근 30일 평균 출고량(moving_avg_30d)을 계산하여 UPSERT 합니다.
    """
    if target_date_str is None:
        target_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. 대상 날짜에 출고가 있었던 region_code, product_name 목록과 당일 총 출고 수량 조회
        # timestamp 형식: 'YYYY-MM-DD HH:MM:SS' 이므로 DATE(timestamp)로 비교
        cursor.execute("""
            SELECT region_code, product_name, SUM(outbound_qty) as total_qty
            FROM stock_out_logs
            WHERE DATE(timestamp) = ?
            GROUP BY region_code, product_name
        """, (target_date_str,))
        daily_outputs = cursor.fetchall()
        
        # 만약 해당 날짜에 출고가 없었으나, 기존 등록된 품목/지역이 있는 경우를 대비해
        # 활성화된 모든 (region_code, product_name) 조합을 가져와서 0개 출고로라도 갱신해 줍니다.
        cursor.execute("""
            SELECT DISTINCT region_code, product_name FROM region_inventory
        """)
        all_inventory_items = cursor.fetchall()
        
        # 맵 형태로 일일 출고 정보 구성
        daily_map = {(row["region_code"], row["product_name"]): row["total_qty"] for row in daily_outputs}
        
        for item in all_inventory_items:
            r_code = item["region_code"]
            p_name = item["product_name"]
            qty = daily_map.get((r_code, p_name), 0.0)
            
            # 2. 최근 30일(target_date 기준 30일 전 ~ target_date) 동안의 일별 총 출고량 평균 계산
            # daily_demand_stats에 이전에 기록된 내역들과 오늘치를 합산해 계산합니다.
            cursor.execute("""
                SELECT daily_outbound_total
                FROM daily_demand_stats
                WHERE region_code = ? AND product_name = ?
                  AND date <= ? AND date >= DATE(?, '-30 days')
            """, (r_code, p_name, target_date_str, target_date_str))
            
            past_totals = [row["daily_outbound_total"] for row in cursor.fetchall()]
            past_totals.append(qty) # 오늘치 추가
            
            moving_avg = sum(past_totals) / len(past_totals) if past_totals else 0.0
            
            # 3. daily_demand_stats 테이블에 UPSERT
            cursor.execute("""
                INSERT INTO daily_demand_stats (region_code, product_name, date, daily_outbound_total, moving_avg_30d)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(region_code, product_name, date) DO UPDATE SET
                    daily_outbound_total = excluded.daily_outbound_total,
                    moving_avg_30d = excluded.moving_avg_30d
            """, (r_code, p_name, target_date_str, qty, moving_avg))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ [aggregate_daily_demand] 에러 발생: {e}")
        return False
    finally:
        conn.close()

def calculate_dead_stock_cost(region_code: str, product_name: str, current_qty: float, moving_avg_30d: float) -> float:
    """
    방치 재고 기회비용(Cost_dead) 산출 (특허 4번 재무 연산)
    Cost_dead = I_dead * C_h * T_dead
    (T_dead = DoS = current_qty / moving_avg_30d)
    """
    if moving_avg_30d <= 0 or current_qty <= 0:
        return 0.0
        
    dos = current_qty / moving_avg_30d
    if dos <= 90:
        return 0.0
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT holding_cost_per_day FROM product_financial_master WHERE product_name = ?", (product_name,))
        row = cursor.fetchone()
        c_h = row["holding_cost_per_day"] if row else 50.0
        
        # 방치 일수(T_dead)는 DoS 전체로 볼지, 90일 초과분으로 볼지 정책에 따라 다름. (여기선 전체 DoS 기간 누적분으로 산출)
        cost_dead = current_qty * c_h * dos
        return cost_dead
    except Exception as e:
        print(f"❌ [calculate_dead_stock_cost] 에러 발생: {e}")
        return 0.0
    finally:
        conn.close()
