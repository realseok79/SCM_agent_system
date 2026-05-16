import datetime
import pandas as pd
import yfinance as yf
from fredapi import Fred
import streamlit as st
import os
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

class GlobalMacroEngine:
    def __init__(self):
        self.fred_key = st.secrets.get("FRED_API_KEY", os.environ.get("FRED_API_KEY", ""))
        try:
            self.fred = Fred(api_key=self.fred_key)
        except Exception as e:
            self.fred = None
            print(f"🚨 [FRED 초기화 실패]: {str(e)}")

    def fetch_unified_macro_vector(self, country_name):
        """
        국가별 고유 거시경제 지표를 엄격하게 분리하여 수집합니다.
        데이터 오염을 막기 위해 타국(미국) 데이터 대체 로직을 전면 폐기합니다.
        """
        # WTI 유가는 글로벌 공통 지표이므로 선행 수집
        wti_oil_price, wti_oil_change = 0.0, 0.0
        try:
            oil_hist = yf.download("CL=F", period="7d", progress=False)
            if not oil_hist.empty and 'Close' in oil_hist.columns:
                close_data = oil_hist['Close']
                if isinstance(close_data, pd.DataFrame): 
                    close_data = close_data.iloc[:, 0]
                close_data = close_data.sort_index()  # 날짜 순정렬 보장
                if len(close_data) >= 2:
                    wti_oil_price = float(close_data.iloc[-1])
                    prev_oil = float(close_data.iloc[-2])
                    wti_oil_change = ((wti_oil_price - prev_oil) / prev_oil) * 100
        except:
            pass

        # 국가별 확장 매핑 테이블
        euro_countries = ["Germany", "France", "Italy", "Spain", "Netherlands", "Belgium", "Austria", "Greece", "Portugal", "Ireland", "Finland"]
        country_registry = {
            "United States": {"fx": None, "idx": "^GSPC", "rate_id": "FEDFUNDS", "cpi_id": "CPALTT01USM657N", "currency": "USD"},
            "South Korea": {"fx": "USDKRW=X", "idx": "^KS11", "rate_id": "IRSTCB01KRM156N", "cpi_id": "KORCPIALLMINMEI", "currency": "KRW"},
            "China": {"fx": "USDCNY=X", "idx": "000001.SS", "rate_id": "INTDSRCNM193N", "cpi_id": "CHNCPIALLMINMEI", "currency": "CNY"},
            "Japan": {"fx": "USDJPY=X", "idx": "^N225", "rate_id": "INTDSRJPM193N", "cpi_id": "JPNCPIALLMINMEI", "currency": "JPY"},
            "United Kingdom": {"fx": "GBPUSD=X", "idx": "^FTSE", "rate_id": "BOERUDATE", "cpi_id": "GBRCPIALLMINMEI", "currency": "GBP"},
            "Canada": {"fx": "USDCAD=X", "idx": "^GSPTSE", "rate_id": "INTDSRCAM193N", "cpi_id": "CANCPIALLMINMEI", "currency": "CAD"},
            "Australia": {"fx": "AUDUSD=X", "idx": "^AXJO", "rate_id": "IR3TIB01AUM156N", "cpi_id": "AUSCPIALLMINMEI", "currency": "AUD"},
            "India": {"fx": "USDINR=X", "idx": "^BSESN", "rate_id": "INTDSRINM193N", "cpi_id": "INDCPIALLMINMEI", "currency": "INR"},
            "Brazil": {"fx": "USDBRL=X", "idx": "^BVSP", "rate_id": "INTDSRBRM193N", "cpi_id": "BRACPIALLMINMEI", "currency": "BRL"},
            "Mexico": {"fx": "USDMXN=X", "idx": "^MXX", "rate_id": "INTDSRMXM193N", "cpi_id": "MEXCPIALLMINMEI", "currency": "MXN"},
            "Taiwan": {"fx": "USDTWD=X", "idx": "^TWII", "rate_id": None, "cpi_id": None, "currency": "TWD"},
            "Singapore": {"fx": "USDSGD=X", "idx": "^STI", "rate_id": None, "cpi_id": None, "currency": "SGD"},
            "Switzerland": {"fx": "USDCHF=X", "idx": "^SSMI", "rate_id": "INTDSRCHM193N", "cpi_id": "CHECPIALLMINMEI", "currency": "CHF"},
            "South Africa": {"fx": "USDZAR=X", "idx": None, "rate_id": "INTDSRZAM193N", "cpi_id": "ZAFCPIALLMINMEI", "currency": "ZAR"},
            "New Zealand": {"fx": "NZDUSD=X", "idx": "^NZ50", "rate_id": "INTDSRNZM193N", "cpi_id": "NZLCPIALLMINMEI", "currency": "NZD"},
            "Sweden": {"fx": "USDSEK=X", "idx": "^OMX", "rate_id": "INTDSRSEM193N", "cpi_id": "SWECPIALLMINMEI", "currency": "SEK"},
            "Norway": {"fx": "USDNOK=X", "idx": None, "rate_id": None, "cpi_id": "NORCPIALLMINMEI", "currency": "NOK"},
        }

        for ec in euro_countries:
            if ec not in country_registry:
                country_registry[ec] = {"fx": "EURUSD=X", "idx": "^STOXX50E", "rate_id": "ECBDFR", "cpi_id": "CP0000EZ19M086NES", "currency": "EUR"}

        # 매핑에 없는 국가인 경우 에러 방지를 위해 기본 뼈대만 반환 (데이터는 전부 0이나 None)
        cfg = country_registry.get(country_name, {
            "fx": None, "idx": None, "rate_id": None, "cpi_id": None, "currency": "Unknown"
        })

        # (A) 환율 데이터 수집
        fx_val, fx_chg = 1.0, 0.0
        if cfg["fx"]:
            try:
                fx_hist = yf.download(cfg["fx"], period="7d", progress=False)
                if not fx_hist.empty and 'Close' in fx_hist.columns:
                    close_data = fx_hist['Close']
                    if isinstance(close_data, pd.DataFrame): close_data = close_data.iloc[:, 0]
                    close_data = close_data.sort_index()
                    if len(close_data) >= 2:
                        fx_val = float(close_data.iloc[-1])
                        prev_fx = float(close_data.iloc[-2])
                        fx_chg = ((fx_val - prev_fx) / prev_fx) * 100
            except:
                pass

        # (B) 주가지수 데이터 수집
        idx_val, idx_chg = 0.0, 0.0
        if cfg["idx"]:
            try:
                idx_hist = yf.download(cfg["idx"], period="7d", progress=False)
                if not idx_hist.empty and 'Close' in idx_hist.columns:
                    close_data = idx_hist['Close']
                    if isinstance(close_data, pd.DataFrame): close_data = close_data.iloc[:, 0]
                    close_data = close_data.sort_index()
                    if len(close_data) >= 2:
                        idx_val = float(close_data.iloc[-1])
                        prev_idx = float(close_data.iloc[-2])
                        idx_chg = ((idx_val - prev_idx) / prev_idx) * 100
            except:
                pass

        # (C) 해당 국가 금리 수집 (데이터 없으면 None 반환하여 수치 오염 원천 차단)
        domestic_rate = None
        if cfg["rate_id"] and self.fred:
            try:
                r_data = self.fred.get_series(cfg["rate_id"])
                if not r_data.empty:
                    r_data = r_data.sort_index().dropna()  # 시계열 순정렬 및 결측치 제거
                    if not r_data.empty:
                        domestic_rate = float(r_data.iloc[-1])
            except:
                pass

        # (D) 해당 국가 소비자물가(CPI) 수집 -> 실질 물가상승률(YoY %)로 완벽 변환
        domestic_inflation = None
        if cfg["cpi_id"] and self.fred:
            try:
                c_data = self.fred.get_series(cfg["cpi_id"])
                if not c_data.empty:
                    c_data = c_data.sort_index().dropna()  # 날짜 순정렬 필수 보장
                    
                    # 1년 전 데이터와의 비교를 위해 최소 13개월 이상의 데이터 확보 필요
                    if len(c_data) >= 13:
                        current_cpi = float(c_data.iloc[-1])
                        prev_year_cpi = float(c_data.iloc[-13]) # 정확히 12~13개월 전 원본 지수와 비교
                        
                        # 지수 원본을 전년 동월 대비 변동률(%) 수식으로 변환
                        if prev_year_cpi > 0:
                            domestic_inflation = ((current_cpi - prev_year_cpi) / prev_year_cpi) * 100
                    else:
                        # 시계열이 짧다면 단일 값 검증 분기
                        single_val = float(c_data.iloc[-1])
                        if single_val < 20.0: # 지수가 아니라 이미 % 단위로 제공되는 데이터일 경우 방어
                            domestic_inflation = single_val
            except:
                pass

        # (E) 알고리즘 피딩용 위험도 계산 (데이터 유효성 검증 포함)
        safe_fx_chg = fx_chg if fx_chg is not None else 0.0
        safe_idx_chg = idx_chg if idx_chg is not None else 0.0
        calculated_risk = min(100.0, max(0.0, (abs(safe_fx_chg) * 30 + abs(safe_idx_chg) * 30 + abs(wti_oil_change) * 40)))

        return {
            "country": country_name,
            "currency_code": cfg["currency"],
            "fx_ticker": cfg["fx"],
            "fx_value": round(fx_val, 2) if fx_val else 0.0,
            "fx_change_pct": round(fx_chg, 2),
            "index_ticker": cfg["idx"],
            "index_value": round(idx_val, 2) if idx_val else 0.0,
            "index_change_pct": round(idx_chg, 2),
            "oil_price": round(wti_oil_price, 2),
            "oil_change_pct": round(wti_oil_change, 2),
            "interest_rate": round(domestic_rate, 2) if domestic_rate is not None else None,
            "inflation_rate": round(domestic_inflation, 2) if domestic_inflation is not None else None,
            "integrated_risk_score": round(calculated_risk, 2),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
