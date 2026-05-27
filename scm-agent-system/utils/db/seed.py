# utils/db/seed.py
import os
from .connection import get_db_connection

def seed_initial_data():
    """
    Clone 직후 빈 DB에 초기 운영 데이터를 자동 주입합니다.
    이미 데이터가 있는 경우 아무 작업도 수행하지 않습니다 (멱등성 보장).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # ── 1. region_inventory 시드 ──
        cursor.execute("SELECT COUNT(*) FROM region_inventory")
        if cursor.fetchone()[0] == 0:
            csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/sample_inventory_data.csv"))
            if os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)

                # 한글 컬럼명 → 영문 매핑
                column_map = {"지점": "region", "상품명": "product", "수량": "quantity", "날짜": "date"}
                df.rename(columns=column_map, inplace=True)

                # 지점명 → region_code 변환
                region_name_to_code = {"서울": "KR-11", "부산": "KR-26", "제주": "KR-49"}
                df["region_code"] = df["region"].map(region_name_to_code)

                inserted = 0
                for _, row in df.iterrows():
                    if pd.notna(row.get("region_code")):
                        prod_name = row["product"]
                        if prod_name == "MCU 반도체":
                            prod_name = "반도체 칩"
                        elif prod_name == "마스크":
                            prod_name = "마스크"
                        elif prod_name == "손소독제":
                            prod_name = "종합 품목"
                            
                        # Avoid sqlite3 or PostgreSQL syntax mismatch using ? or %s
                        # We use executing raw connection queries
                        # Since wrapper translates to postgres correctly:
                        cursor.execute(
                            """INSERT INTO region_inventory 
                               (region_code, product_name, date, quantity) 
                               VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING""",
                            (row["region_code"], prod_name, row["date"], row["quantity"])
                        )
                        inserted += 1
                conn.commit()
                print(f"✅ [DB 시드] 초기 재고 데이터 {inserted}건 자동 주입 완료 (소스: {csv_path})")
            else:
                print(f"⚠️ [DB 시드 실패] 초기 데이터 파일 없음: {csv_path}")
                print(f"   → region_inventory 테이블이 비어있는 상태로 시뮬레이션이 시작됩니다.")
                print(f"   → 대시보드 UI를 통해 수동으로 Excel/CSV 데이터를 주입해야 합니다.")

        # ── 2. daily_demand_stats 시드 ──
        cursor.execute("SELECT COUNT(*) FROM daily_demand_stats")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                SELECT region_code, product_name, date, quantity
                FROM region_inventory
                ORDER BY region_code, product_name, date
            """)
            rows = cursor.fetchall()

            if rows:
                inserted = 0
                for row in rows:
                    cursor.execute(
                        """INSERT INTO daily_demand_stats 
                           (region_code, product_name, date, daily_outbound_total, moving_avg_30d) 
                           VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
                        (row[0], row[1], row[2],
                         row[3] * 0.03,  # 일 출고량 추정 (재고의 3%)
                         row[3] * 0.03)   # 초기값이므로 이동평균 = 일 출고량
                    )
                    inserted += 1
                conn.commit()
                print(f"✅ [DB 시드] 일별 수요 통계 {inserted}건 자동 생성 완료")
            else:
                print(f"⚠️ [DB 시드 실패] region_inventory가 비어있어 daily_demand_stats를 생성할 수 없습니다.")

    except Exception as e:
        print(f"❌ [DB 시드 실패] 초기 데이터 주입 중 중대한 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()
