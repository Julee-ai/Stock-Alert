import os
import requests
import matplotlib
matplotlib.use("Agg")
import mplfinance as mpf
import FinanceDataReader as fdr
from pykrx import stock
from datetime import datetime, timedelta
import pandas as pd

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_photo(image_path, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    with open(image_path, "rb") as f:
        requests.post(url, data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}, files={"photo": f})

def send_message(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def save_chart(ticker, name, today):
    end = datetime.strptime(today, "%Y%m%d")
    start = (end - timedelta(weeks=260)).strftime("%Y-%m-%d")

    df = fdr.DataReader(ticker, start)
    if df.empty or len(df) < 20:
        return None

    df.index = pd.to_datetime(df.index)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    all_time_high = df["High"].max()
    ma20 = df["Close"].rolling(20).mean()
    ma60 = df["Close"].rolling(60).mean()
    ma120 = df["Close"].rolling(120).mean()

    apds = [
        mpf.make_addplot(ma20, color="#f6a623", width=0.8),
        mpf.make_addplot(ma60, color="#4a90e2", width=0.8),
        mpf.make_addplot(ma120, color="#7ed321", width=0.8),
        mpf.make_addplot(pd.Series(all_time_high, index=df.index), color="red", width=1.2, linestyle="--"),
    ]

    style = mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mpf.make_marketcolors(up="#e83030", down="#4a90e2", volume="in"),
        gridstyle="--",
        gridcolor="#333333",
        facecolor="#1a1a2e",
        figcolor="#1a1a2e",
        rc={"axes.labelcolor": "white", "xtick.color": "white", "ytick.color": "white"}
    )

    image_path = f"/tmp/{ticker}.png"
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        title=f"\n{name} ({ticker})  |  5년 차트",
        volume=True,
        addplot=apds,
        figsize=(14, 8),
        returnfig=True,
        tight_layout=True,
    )

    axes[0].legend(["MA20", "MA60", "MA120", "5년 신고가"], loc="upper left",
                   facecolor="#1a1a2e", edgecolor="white", labelcolor="white", fontsize=9)

    import matplotlib.pyplot as plt
    fig.savefig(image_path, dpi=130, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    return image_path

def main():
    today = datetime.now().strftime("%Y%m%d")

    # pykrx로 거래대금 상위 50개 한번에 가져오기
    kospi = stock.get_market_trading_value_by_ticker(today, "KOSPI")
    kosdaq = stock.get_market_trading_value_by_ticker(today, "KOSDAQ")
    combined = pd.concat([kospi, kosdaq])
    combined = combined.sort_values("거래대금", ascending=False).head(50)

    today_str = datetime.now().strftime("%Y-%m-%d")
    start_str = (datetime.now() - timedelta(weeks=260)).strftime("%Y-%m-%d")

    hit_tickers = []
    for ticker in combined.index:
        try:
            name = stock.get_market_ticker_name(ticker)
            hist = fdr.DataReader(ticker, start_str, today_str)
            if hist.empty:
                continue
            five_year_high = hist["High"].max()
            today_high = hist["High"].iloc[-1]
            if today_high >= five_year_high:
                vol = combined.loc[ticker, "거래대금"]
                hit_tickers.append((ticker, name, vol))
        except:
            continue

    if not hit_tickers:
        send_message(f"📭 [{today}] 해당 조건 종목 없음")
        return

    send_message(f"📈 <b>[{today}] 거래대금 상위 50 + 5년 신고가</b>\n총 {len(hit_tickers)}개 종목")

    for ticker, name, vol in hit_tickers:
        volume_억 = vol / 1e8
        image_path = save_chart(ticker, name, today)
        if image_path:
            caption = f"<b>{name} ({ticker})</b>\n거래대금: {volume_억:.0f}억원"
            send_photo(image_path, caption)

if __name__ == "__main__":
    main()
