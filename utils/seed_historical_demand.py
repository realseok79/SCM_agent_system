# utils/seed_historical_demand.py
import os
import sys
import random
import numpy as np
from datetime import datetime, timedelta

# 상위 디렉터리를 sys.path에 추가하여 db 및 utils 모듈 로드 가능하게 함
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db import get_db_connection, init_db
from utils.demand_tracker import log_stock_out_bulk, aggregate_daily_demand

def seed_historical_demand(days_back: int = 90):
    print("=" * 60)
    print(f"📊 SCM AI 관제센터 과거 {days_back}일 출고 데이터 시드 주입 개시")
    print("=" * 60)

    # 1. DB 초기화 (테이블 생성 보장)
    init_db()

    # 2. 파라미터 정의
    regions = ["KR-11", "KR-26", "KR-49"]  # 서울, 부산, 제주
    products = {
        "마스크": {"vmr_type": "poisson", "mean": 150.0, "std": 12.0},
        "반도체 칩": {"vmr_type": "neg_bin", "mean": 30.0, "std": 15.0},  # 과산포 유도
        "종합 품목": {"vmr_type": "normal", "mean": 85.0, "std": 20.0}
    }

    # 기준일: 2026-01-01
    start_date = datetime(2026, 1, 1) - timedelta(days=days_back)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 중복 주입을 방지하기 위해 기존 90일 이전 과거 데이터 제거
    try:
        cursor.execute("DELETE FROM stock_out_logs WHERE timestamp < '2026-01-01'")
        cursor.execute("DELETE FROM daily_demand_stats WHERE date < '2026-01-01'")
        conn.commit()
        print("🧹 기존의 90일 이전 가상 출고 데이터 초기화 완료")
    except Exception as e:
        print(f"⚠️ 초기화 에러 (무시하고 진행): {e}")
    finally:
        conn.close()

    random.seed(42)
    np.random.seed(42)

    bulk_logs = []

    # 3. 과거 90일 동안 매일 트랜잭션 생성
    for day_idx in range(days_back):
        current_virtual_date = start_date + timedelta(days=day_idx)
        date_str = current_virtual_date.strftime("%Y-%m-%d")
        
        for region in regions:
            for product, params in products.items():
                # ── 동적 확률 분포 모델 생성 ──
                if params["vmr_type"] == "poisson":
                    # 포아송 분포 (VMR = 1.0)
                    qty = float(np.random.poisson(params["mean"]))
                elif params["vmr_type"] == "neg_bin":
                    # 과산포 음이항 분포 (VMR > 1.15)
                    # mean = r(1-p)/p, var = r(1-p)/p^2
                    # VMR = var / mean = 1 / p => p = 1 / VMR
                    # r = mean * p / (1 - p)
                    vmr = 7.0  # 고의로 강한 과산포 유도
                    p = 1.0 / vmr
                    r = params["mean"] * p / (1.0 - p)
                    qty = float(np.random.negative_binomial(r, p))
                else:
                    # 일반 정규 분포 변동
                    qty = float(max(0.0, np.random.normal(params["mean"], params["std"])))
                
                # 가상 주말 시그널 보정 (토요일/일요일 수요 감소)
                if current_virtual_date.weekday() in [5, 6]:
                    qty *= 0.4
                
                qty = round(qty, 1)
                
                if qty > 0:
                    # 1일 3~5회의 개별 출고 건으로 분할 적재하여 트랜잭션 리얼리티 극대화
                    num_transactions = random.randint(2, 4)
                    qty_per_t = round(qty / num_transactions, 1)
                    
                    for t_idx in range(num_transactions):
                        # 타임스탬프 시계열 분산 (12시 ~ 18시 사이 무작위 분포)
                        hour = random.randint(9, 18)
                        minute = random.randint(0, 59)
                        second = random.randint(0, 59)
                        timestamp_str = f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"
                        
                        bulk_logs.append({
                            "region_code": region,
                            "product_name": product,
                            "outbound_qty": qty_per_t,
                            "transaction_type": "정상출고",
                            "timestamp": timestamp_str
                        })

    # 4. Bulk Insert 실행
    print(f"📦 생성된 총 {len(bulk_logs)}건의 출고 건을 stock_out_logs에 Bulk Insert 적재 중...")
    success = log_stock_out_bulk(bulk_logs)
    if success:
        print("✅ Bulk Insert 트랜잭션 적재 성공!")
    else:
        print("❌ Bulk Insert 트랜잭션 적재 실패!")
        return

    # 5. 매일 일일 수요 통계(daily_demand_stats) 집계 및 30일 이동평균 갱신
    print("🔄 과거 90일 치 일일 집계 및 30일 이동평균선 산출(daily_demand_stats UPSERT) 수행 중...")
    for day_idx in range(days_back):
        current_virtual_date = start_date + timedelta(days=day_idx)
        date_str = current_virtual_date.strftime("%Y-%m-%d")
        aggregate_daily_demand(date_str)
    
    print("✅ 모든 과거 90일 데이터 집계 및 이동평균 산출 완료!")
    print("=" * 60)

if __name__ == "__main__":
    seed_historical_demand(90)
