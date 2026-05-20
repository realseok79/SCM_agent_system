# analysis-microservice/main.py
import math
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from scipy import stats
from scipy.optimize import minimize_scalar

app = FastAPI(title="SCM Ingestion & Analysis Microservice", version="1.0")

class InventoryItem(BaseModel):
    regionCode: str
    productName: str
    date: str
    quantity: float

class BatchAnalysisRequest(BaseModel):
    batchId: str
    inventories: List[InventoryItem]

# --- 1. 3시그마 클리핑 가드레일 ---
def clip_outliers(data: np.ndarray, sigma_multiplier: float = 3.0) -> np.ndarray:
    if len(data) < 2:
        return data
    mu = np.mean(data)
    sigma = np.std(data, ddof=1)
    if sigma == 0:
        return data
    lower_bound = mu - sigma_multiplier * sigma
    upper_bound = mu + sigma_multiplier * sigma
    return np.clip(data, lower_bound, upper_bound)

# --- 2. 과산포 분석 및 음이항 분포 피팅 ---
def fit_negative_binomial(mean_d: float, var_d: float) -> tuple:
    if var_d <= mean_d or mean_d <= 0:
        return 1e6, mean_d / (mean_d + 1e-6)
    p = mean_d / var_d
    r = (mean_d ** 2) / (var_d - mean_d)
    p = np.clip(p, 1e-6, 1.0 - 1e-6)
    r = max(r, 1e-3)
    return r, p

# --- 3. 총 운영 비용(TC) 목적함수 최소화 ---
TAIL_PROBABILITY_THRESHOLD = 1e-4

def compute_expected_total_cost(
    order_qty: float,
    SS: float,
    lambda_adjusted: float,
    E_L: float,
    unit_holding_cost: float,
    stockout_penalty: float,
    order_cost: float,
    annual_demand: float,
    is_overdispersed: bool,
    nb_r: float,
    nb_p: float
) -> float:
    if order_qty <= 0:
        return float('inf')

    h_annual = unit_holding_cost * 365
    holding_cost = h_annual * (order_qty / 2 + SS)

    lt_lambda = lambda_adjusted * E_L
    expected_shortage = 0.0
    reorder_level = order_qty + SS

    k = 0
    cumulative_prob = 0.0
    while True:
        if is_overdispersed:
            nb_n_scaled = max(nb_r * E_L, 1e-3)
            prob = stats.nbinom.pmf(k, nb_n_scaled, nb_p)
        else:
            prob = stats.poisson.pmf(k, lt_lambda)

        shortage = max(k - reorder_level, 0)
        expected_shortage += prob * shortage
        cumulative_prob += prob

        if cumulative_prob >= (1.0 - TAIL_PROBABILITY_THRESHOLD) and k > lt_lambda:
            break
        if k > max(lt_lambda * 10, 10000):
            break
        k += 1

    order_frequency = annual_demand / order_qty if order_qty > 0 else 0
    stockout_cost = stockout_penalty * expected_shortage * order_frequency
    ordering_cost = order_cost * order_frequency

    return holding_cost + stockout_cost + ordering_cost

def minimize_total_cost(
    SS: float,
    lambda_adjusted: float,
    E_D: float,
    E_L: float,
    unit_holding_cost: float,
    stockout_penalty: float,
    order_cost: float,
    is_overdispersed: bool,
    nb_r: float,
    nb_p: float
) -> tuple:
    annual_demand = E_D * 365

    def tc_objective(q):
        return compute_expected_total_cost(
            order_qty=q,
            SS=SS,
            lambda_adjusted=lambda_adjusted,
            E_L=E_L,
            unit_holding_cost=unit_holding_cost,
            stockout_penalty=stockout_penalty,
            order_cost=order_cost,
            annual_demand=annual_demand,
            is_overdispersed=is_overdispersed,
            nb_r=nb_r,
            nb_p=nb_p
        )

    # Wilson EOQ estimate
    if annual_demand <= 0 or order_cost <= 0 or unit_holding_cost <= 0:
        eoq_estimate = 100.0
    else:
        eoq_estimate = math.sqrt(2 * annual_demand * order_cost / (unit_holding_cost * 365))
        
    search_upper = max(eoq_estimate * 3, 100.0)

    res = minimize_scalar(
        tc_objective,
        bounds=(1.0, search_upper),
        method='bounded',
        options={'xatol': 0.5}
    )

    return max(res.x, 1.0), res.fun

@app.get("/health")
def health_check():
    return {"status": "UP", "message": "SCM Analysis Microservice is operating smoothly."}

@app.get("/macro/vector")
def get_macro_vector(country: str):
    # FRED/yfinance 스크랩 및 분석 스텁 (Plan A)
    # yfinance 차단 발생 시 Emergency mode로 대응하기 위한 stub 데이터 갱신 구조
    return {
        "country": country,
        "inflation_rate": 2.4,
        "gdp_growth": 1.9,
        "unemployment_rate": 3.7,
        "yfinance_status": "OK",
        "emergency_mode": False
    }

@app.post("/analyze/batch")
def analyze_batch(request: BatchAnalysisRequest):
    if not request.inventories:
        raise HTTPException(status_code=400, detail="Inventories list is empty")

    # 3만개 수준의 SKU 배치 고속 벡터 연산 수행
    quantities = np.array([inv.quantity for inv in request.inventories], dtype=float)
    
    # 3시그마 클리핑 처리
    clipped_qty = clip_outliers(quantities)

    mean_d = float(np.mean(clipped_qty)) if len(clipped_qty) > 0 else 0.0
    var_d = float(np.var(clipped_qty, ddof=1)) if len(clipped_qty) > 1 else 0.0
    
    is_overdispersed = var_d > mean_d
    nb_r, nb_p = fit_negative_binomial(mean_d, var_d)

    # 95% 서비스 수준 z-score
    z = float(stats.norm.ppf(0.95))
    
    # 결합 불확실성 산출 (평균 리드타임=3일, 표준편차=0.5일 기준)
    E_L = 3.0
    V_L = 0.25
    sigma_DL = math.sqrt(E_L * var_d + (mean_d ** 2) * V_L)
    
    SS = z * sigma_DL
    ROP = mean_d * E_L + SS

    # 최적화 연산 수행 (지주 단위 비용 기준: 보유비용 0.05, 품절패널티 25.0, 발주비용 50.0)
    opt_q, min_tc = minimize_total_cost(
        SS=SS,
        lambda_adjusted=mean_d,
        E_D=mean_d,
        E_L=E_L,
        unit_holding_cost=0.05,
        stockout_penalty=25.0,
        order_cost=50.0,
        is_overdispersed=is_overdispersed,
        nb_r=nb_r,
        nb_p=nb_p
    )

    return {
        "batchId": request.batchId,
        "engine": "FASTAPI_NUMPY_SCIPY",
        "status": "SUCCESS",
        "totalQuantity": float(np.sum(clipped_qty)),
        "averageQuantity": mean_d,
        "safetyStock": round(SS, 2),
        "reorderPoint": round(ROP, 2),
        "optimalOrderQuantity": round(opt_q, 2),
        "minTotalCost": round(min_tc, 2),
        "alert": "NORMAL"
    }
