import os
import requests
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("📈 Single Stock Analyzer")

# -------------------
# Keys
# -------------------
def get_key(name: str) -> str:
    # Streamlit Cloud secrets first
    try:
        return st.secrets.get(name, "")
    except Exception:
        return os.getenv(name, "")

AV_KEY = get_key("ALPHAVANTAGE_KEY")
FRED_KEY = get_key("FRED_KEY")


# -------------------
# HTTP helper
# -------------------
def get_json(url, params):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


# -------------------
# Data fetchers
# -------------------
@st.cache_data(ttl=3600)
def fetch_overview(ticker: str) -> dict:
    if not AV_KEY:
        return {"_error": "ALPHAVANTAGE_KEY is missing"}
    try:
        data = get_json(
            "https://www.alphavantage.co/query",
            {"function": "OVERVIEW", "symbol": ticker, "apikey": AV_KEY},
        )
        # Pass through AV messages for debugging
        return data
    except Exception as e:
        return {"_error": f"Alpha Vantage OVERVIEW request failed: {e}"}


@st.cache_data(ttl=3600)
def fetch_prices(ticker: str) -> dict:
    """
    Return the raw AV response dict for TIME_SERIES_DAILY_ADJUSTED
    (so we can show Note/Error Message).
    """
    if not AV_KEY:
        return {"_error": "ALPHAVANTAGE_KEY is missing"}
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
        return data
    except Exception as e:
        return {"_error": f"Alpha Vantage PRICE request failed: {e}"}


@st.cache_data(ttl=3600)
def fetch_us10y() -> dict:
    """
    Return raw FRED response dict (or error) so we can debug.
    """
    if not FRED_KEY:
        return {"_error": "FRED_KEY is missing"}
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
        return data
    except Exception as e:
        return {"_error": f"FRED request failed: {e}"}


def parse_price_df(price_raw: dict) -> pd.DataFrame:
    ts = price_raw.get("Time Series (Daily)", {})
    if not ts:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(ts, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df["close"] = pd.to_numeric(df.get("4. close"), errors="coerce")
    return df


def parse_us10y(us10y_raw: dict) -> float:
    obs = us10y_raw.get("observations", [])
    if not obs:
        return np.nan
    return safe_float(obs[0].get("value"), np.nan)


# -------------------
# UI
# -------------------
ticker = st.text_input("Ticker", "AAPL").upper().strip()

with st.expander("🔧 Debug / Key status"):
    st.write(
        {
            "ALPHAVANTAGE_KEY_set": bool(AV_KEY),
            "FRED_KEY_set": bool(FRED_KEY),
        }
    )
    st.caption("If keys are True but data is missing, check rate limits or API error messages below.")

if st.button("Analyze"):
    # ---- Fetch ----
    ov = fetch_overview(ticker)
    price_raw = fetch_prices(ticker)
    us10y_raw = fetch_us10y()

    # ---- Show API debug messages (very helpful) ----
    # Alpha Vantage messages
    if "_error" in ov:
        st.error(ov["_error"])
    if "Note" in ov:
        st.warning(f"Alpha Vantage (OVERVIEW) Note: {ov['Note']}")
    if "Error Message" in ov:
        st.error(f"Alpha Vantage (OVERVIEW) Error: {ov['Error Message']}")

    if "_error" in price_raw:
        st.error(price_raw["_error"])
    if "Note" in price_raw:
        st.warning(f"Alpha Vantage (PRICE) Note: {price_raw['Note']}")
    if "Error Message" in price_raw:
        st.error(f"Alpha Vantage (PRICE) Error: {price_raw['Error Message']}")

    # FRED messages
    if "_error" in us10y_raw:
        st.warning(us10y_raw["_error"])

    # ---- Parse ----
    price_df = parse_price_df(price_raw)
    us10y = parse_us10y(us10y_raw)

    # Fundamentals
    pe = safe_float(ov.get("PERatio"), 0)
    roe_raw = safe_float(ov.get("ReturnOnEquityTTM"), 0)
    roe = roe_raw * 100 if roe_raw <= 1 else roe_raw  # AV often gives ROE as decimal
    debt = safe_float(ov.get("DebtToEquityRatio"), 0)
    beta = safe_float(ov.get("Beta"), 1)

    # Simple quant score
    score = 0
    if pe and pe < 20:
        score += 25
    if roe and roe > 15:
        score += 25
    if debt and debt < 120:
        score += 25
    if beta and beta < 1.3:
        score += 25

    # ---- Output ----
    st.subheader("Fundamentals")
    st.write(
        {
            "PER": pe,
            "ROE%": roe,
            "DebtRatio": debt,
            "Beta": beta,
            "US10Y": None if np.isnan(us10y) else us10y,
            "Quant Score(0-100)": score,
        }
    )

    st.subheader("Price")
    if not price_df.empty and price_df["close"].notna().any():
        st.line_chart(price_df["close"])
    else:
        st.warning("No price data returned. Likely rate limit or API error. See messages above.")

    # 
