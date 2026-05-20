# tests/test_macro_connector.py
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from utils.connectors.macro_connector import GlobalMacroEngine

@pytest.fixture
def macro_engine():
    with patch("utils.connectors.macro_connector.Fred") as mock_fred:
        engine = GlobalMacroEngine()
        yield engine

def test_global_macro_engine_init(macro_engine):
    assert macro_engine is not None

def test_global_macro_engine_init_exception():
    # Trigger FRED initialization exception
    with patch("utils.connectors.macro_connector.Fred", side_effect=Exception("Fred init error")):
        engine = GlobalMacroEngine()
        assert engine.fred is None


@patch("requests.get")
def test_get_economic_indicator_success(mock_get, macro_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"page": 1},
        [
            {"country": {"value": "South Korea"}, "date": "2023", "value": 3.5},
            {"country": {"value": "South Korea"}, "date": "2022", "value": None}
        ]
    ]
    mock_get.return_value = mock_response

    df = macro_engine.get_economic_indicator("KOR", "FR.INR.LEND")
    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["Country"] == "South Korea"
    assert df.iloc[0]["Year"] == "2023"
    assert df.iloc[0]["Value"] == 3.5

@patch("requests.get")
def test_get_economic_indicator_failure(mock_get, macro_engine):
    mock_get.side_effect = Exception("API connection timed out")
    df = macro_engine.get_economic_indicator("KOR", "FR.INR.LEND")
    assert df is None

@patch("yfinance.download")
@patch("requests.get")
def test_fetch_unified_macro_vector_us(mock_get, mock_yf_download, macro_engine):
    # Mock yfinance CL=F and ^GSPC. Also return multi-column df to cover line 60
    oil_cols = pd.MultiIndex.from_tuples([("Close", "Ticker"), ("Open", "Ticker")])
    oil_df = pd.DataFrame([[70.0, 69.0], [72.0, 71.0]], columns=oil_cols, index=pd.date_range("2026-05-10", periods=2))
    idx_df = pd.DataFrame({"Close": [5000.0, 5050.0]}, index=pd.date_range("2026-05-10", periods=2))
    
    def side_effect(ticker, *args, **kwargs):
        if ticker == "CL=F":
            return oil_df
        elif ticker == "^GSPC":
            return idx_df
        return pd.DataFrame()
        
    mock_yf_download.side_effect = side_effect

    # Mock FRED to return length >= 13 for CPI to avoid None inflation
    macro_engine.fred = MagicMock()
    macro_engine.fred.get_series.side_effect = lambda key: (
        pd.Series([5.25, 5.33]) if key == "FEDFUNDS" 
        else pd.Series([300.0] * 12 + [309.0])
    )

    vector = macro_engine.fetch_unified_macro_vector("United States")
    assert vector is not None
    assert vector["country"] == "United States"
    assert vector["currency_code"] == "USD"
    assert vector["oil_price"] == 72.0
    assert vector["oil_change_pct"] == round(((72.0 - 70.0) / 70.0) * 100, 2)
    assert vector["index_value"] == 5050.0
    assert vector["index_change_pct"] == round(((5050.0 - 5000.0) / 5000.0) * 100, 2)
    assert vector["interest_rate"] == 5.33
    assert vector["inflation_rate"] == 3.0  # ((309 - 300) / 300) * 100

@patch("yfinance.download")
@patch("requests.get")
def test_fetch_unified_macro_vector_korea_with_fred_failure(mock_get, mock_yf_download, macro_engine):
    oil_df = pd.DataFrame({"Close": [70.0, 68.0]}, index=pd.date_range("2026-05-10", periods=2))
    fx_df = pd.DataFrame({"Close": [1350.0, 1360.0]}, index=pd.date_range("2026-05-10", periods=2))
    idx_df = pd.DataFrame({"Close": [2700.0, 2680.0]}, index=pd.date_range("2026-05-10", periods=2))
    
    def side_effect(ticker, *args, **kwargs):
        if ticker == "CL=F":
            return oil_df
        elif ticker == "USDKRW=X":
            return fx_df
        elif ticker == "^KS11":
            return idx_df
        return pd.DataFrame()
        
    mock_yf_download.side_effect = side_effect

    # Mock FRED failure
    macro_engine.fred = MagicMock()
    macro_engine.fred.get_series.side_effect = Exception("FRED Down")

    # Mock World Bank Fallback
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"page": 1},
        [
            {"country": {"value": "South Korea"}, "date": "2023", "value": 4.25}
        ]
    ]
    mock_get.return_value = mock_response

    vector = macro_engine.fetch_unified_macro_vector("South Korea")
    assert vector is not None
    assert vector["interest_rate"] == 4.25
    assert vector["inflation_rate"] == 4.25

@patch("yfinance.download")
def test_fetch_unified_macro_vector_yf_exceptions(mock_yf_download, macro_engine):
    # Trigger yfinance exceptions to hit line 66-67, 129-135, and 150-151
    mock_yf_download.side_effect = Exception("yfinance API Error")
    
    # Mock FRED to return single value < 20.0 for CPI fallback (line 186)
    macro_engine.fred = MagicMock()
    macro_engine.fred.get_series.side_effect = lambda key: (
        pd.Series([4.5]) if key == "IRSTCB01KRM156N" 
        else pd.Series([3.5])
    )
    
    vector = macro_engine.fetch_unified_macro_vector("South Korea")
    assert vector is not None
    assert vector["fx_value"] == 1350.0  # Fallback FX rate
    assert vector["oil_price"] == 0.0
    assert vector["index_value"] == 0.0
    assert vector["interest_rate"] == 4.5
    assert vector["inflation_rate"] == 3.5

@patch("yfinance.download")
def test_fetch_unified_macro_vector_unknown_country(mock_yf_download, macro_engine):
    mock_yf_download.return_value = pd.DataFrame()
    vector = macro_engine.fetch_unified_macro_vector("Atlantis")
    assert vector is not None
    assert vector["country"] == "Atlantis"
    assert vector["currency_code"] == "Unknown"
    assert vector["fx_value"] == 1.0
    assert vector["fx_change_pct"] == 0.0
    assert vector["index_value"] == 0.0
    assert vector["index_change_pct"] == 0.0
    assert vector["interest_rate"] is None
