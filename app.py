import os, requests, numpy as np, pandas as pd, streamlit as st

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("📈 Single Stock Analyzer")

# --- Read keys (works on Streamlit Cloud + local) ---
def get_key(name: str) -> str:
    # Streamlit Cloud
    try:
        return st.secrets.get(name, "")
    except Exception:
        pass
    # Local env
    return os.getenv(name, "")

AV_KEY = get_key("ALPHAVANTAGE_KEY")
FRED_KEY = get_key("FRED_KEY")

def get_json(url, params):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def get_overview(ticker):
    if not AV_KEY:
        return {}
    url = "https://www.alphavantage.co/query"
    try:
        return get_json(url, {"function":"OVERVIEW","symbol":ticker,"apikey":AV_KEY})
    except Exception:
        return {}

@st.cache_data(ttl=3600)
def get_price(ticker):
    if not AV_KEY:
        return pd.DataFrame()
    url = "https://www.alphavantage.co/query"
    try:
        data = get_json(url, {"function":"TIME_SERIES_DAILY_ADJUSTED","symbol":ticker,"apikey":AV_KEY,"outputsize":"compact"})
        ts = data.get("Time Series (Daily)",{})
        if not ts:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(ts, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df["close"] = pd.to_numeric(df["4. close"], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_10y():
    """Return latest US10Y (DGS10). If it fails, return NaN but DO NOT crash."""
    if not FRED_KEY:
        return np.nan
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":"DGS10",
        "api_key":FRED_KEY,
        "file_type":"json",
        "sort_order":"desc",
        "limit":1
    }
    try:
        data = get_json(url, params)
        obs = data.get("observations", [])
        if not obs:
            return np.nan
        return float(obs[0].get("value", "nan"))
    except Exception:
        return np.nan

def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def quant_score(pe, roe, debt, beta):
    score = 0
    if pe and pe < 20: score += 25
    if roe and roe > 15: score += 25
    if debt and debt < 120: score += 25
    if beta and beta < 1.3: score += 25
    return score

ticker = st.text_input("Ticker", "AAPL").upper()

# Show key status (helps debugging)
with st.expander("🔧 Key status (debug)"):
    st.write({
        "ALPHAVANTAGE_KEY_set": bool(AV_KEY),
        "FRED_KEY_set": bool(FRED_KEY),
    })

if st.button("Analyze"):
    ov = get_overview(ticker)
    price = get_price(ticker)
    y10 = get_10y()

    pe = safe_float(ov.get("PERatio"), 0)
    roe_raw = safe_float(ov.get("ReturnOnEquityTTM"), 0)
    roe = roe_raw * 100 if roe_raw <= 1 else roe_raw
    debt = safe_float(ov.get("DebtToEquityRatio"), 0)
    beta = safe_float(ov.get("Beta"), 1)

    score = quant_score(pe, roe, debt, beta)

    st.subheader("Fundamentals")
    st.writ
::contentReference[oaicite:0]{index=0}
