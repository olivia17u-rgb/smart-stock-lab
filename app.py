
import os, requests, numpy as np, pandas as pd, streamlit as st
from dotenv import load_dotenv
load_dotenv()

AV_KEY = os.getenv("ALPHAVANTAGE_KEY","")
FRED_KEY = os.getenv("FRED_KEY","")

st.set_page_config(page_title="Stock Analyzer", layout="wide")
st.title("📈 Single Stock Analyzer")

def get_json(url, params):
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600)
def get_overview(ticker):
    if not AV_KEY:
        return {}
    url = "https://www.alphavantage.co/query"
    return get_json(url, {"function":"OVERVIEW","symbol":ticker,"apikey":AV_KEY})

@st.cache_data(ttl=3600)
def get_price(ticker):
    if not AV_KEY:
        return pd.DataFrame()
    url = "https://www.alphavantage.co/query"
    data = get_json(url, {"function":"TIME_SERIES_DAILY_ADJUSTED","symbol":ticker,"apikey":AV_KEY,"outputsize":"compact"})
    ts = data.get("Time Series (Daily)",{})
    if not ts: return pd.DataFrame()
    df = pd.DataFrame.from_dict(ts, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df["close"] = pd.to_numeric(df["4. close"])
    return df

@st.cache_data(ttl=3600)
def get_10y():
    if not FRED_KEY:
        return np.nan
    url = "https://api.stlouisfed.org/fred/series/observations"
    data = get_json(url, {"series_id":"DGS10","api_key":FRED_KEY,"file_type":"json","sort_order":"desc","limit":1})
    obs = data.get("observations",[])
    return float(obs[0]["value"]) if obs else np.nan

def quant_score(pe, roe, debt, beta):
    score = 0
    if pe and pe < 20: score += 25
    if roe and roe > 15: score += 25
    if debt and debt < 120: score += 25
    if beta and beta < 1.3: score += 25
    return score

ticker = st.text_input("Ticker", "AAPL").upper()

if st.button("Analyze"):
    ov = get_overview(ticker)
    price = get_price(ticker)
    y10 = get_10y()

    pe = float(ov.get("PERatio",0))
    roe = float(ov.get("ReturnOnEquityTTM",0))*100
    debt = float(ov.get("DebtToEquityRatio",0))
    beta = float(ov.get("Beta",1))

    score = quant_score(pe, roe, debt, beta)

    st.subheader("Fundamentals")
    st.write({
        "PER": pe,
        "ROE%": roe,
        "DebtRatio": debt,
        "Beta": beta,
        "US10Y": y10,
        "Quant Score(0-100)": score
    })

    if not price.empty:
        st.line_chart(price["close"])
