import os, requests, numpy as np, pandas as pd, streamlit as st

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("📈 Single Stock Analyzer")

# -------------------
# Keys
# -------------------
def get_key(name: str) -> str:
    try:
        return st.secrets.get(name, "")
    except:
        return os.getenv(name, "")

AV_KEY = get_key("ALPHAVANTAGE_KEY")
FRED_KEY = get_key("FRED_KEY")


# -------------------
# Utils
# -------------------
def get_json(url, params):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default


# -------------------
# Data
# -------------------
@st.cache_data(ttl=3600)
def get_overview(ticker):
    if not AV_KEY:
        return {}
    try:
        return get_json(
            "https://www.alphavantage.co/query",
            {"function": "OVERVIEW", "symbol": ticker, "apikey": AV_KEY},
        )
    except:
        return {}


@st.cache_data(ttl=3600)
def get_price(ticker):
    if not AV_KEY:
        return pd.DataFrame()

    try:
        data = get_json(
            "https://www.alphavantage.co/query",
            {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": ticker,
                "apikey": AV_KEY,
                "outputsize": "compact",
            },
        )

        ts = data.get("Time Series (Daily)", {})
        if not ts:
            return pd.DataFrame()

        df = pd.DataFrame.from_dict(ts, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df["close"] = pd.to_numeric(df["4. close"], errors="coerce")
        return df

    except:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_10y():
    if not FRED_KEY:
        return np.nan

    try:
        data = get_json(
            "https://api.stlouisfed.org/fred/series/observations",
            {
                "series_id": "DGS10",
                "api_key": FRED_KEY,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 1,
            },
        )

        obs = data.get("observations", [])
        if not obs:
            return np.nan

        return float(obs[0]["value"])

    except:
        return np.nan


# -------------------
# UI
# -------------------
ticker = st.text_input("Ticker", "AAPL").upper()

if st.button("Analyze"):

    overview = get_overview(ticker)
    price = get_price(ticker)
    y10 = get_10y()

    pe = safe_float(overview.get("PERatio"))
    roe_raw = safe_float(overview.get("ReturnOnEquityTTM"))
    roe = roe_raw * 100 if roe_raw <= 1 else roe_raw
    debt = safe_float(overview.get("DebtToEquityRatio"))
    beta = safe_float(overview.get("Beta"))

    score = 0
    if pe and pe < 20: score += 25
    if roe and roe > 15: score += 25
    if debt and debt < 120: score += 25
    if beta and beta < 1.3: score += 25

    st.subheader("Fundamentals")
    st.write({
        "PER": pe,
        "ROE%": roe,
        "DebtRatio": debt,
        "Beta": beta,
        "US10Y": None if np.isnan(y10) else y10,
        "Quant Score(0-100)": score
    })

    if not price.empty:
        st.subheader("Price")
        st.line_chart(price["close"])
    else:
        st.warning("No price data (rate limit or ticker issue)")
