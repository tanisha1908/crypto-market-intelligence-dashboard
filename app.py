import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Crypto Market Intelligence",
    page_icon="₿",
    layout="wide"
)


# =========================================================
# AUTO REFRESH - EVERY 60 SECONDS
# =========================================================

st_autorefresh(
    interval=60_000,
    key="crypto_refresh"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 0px;
    }

    .subtitle {
        color: #888888;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 600;
        margin-top: 20px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# TITLE
# =========================================================

st.markdown(
    '<div class="main-title">₿ Crypto Market Intelligence</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Live cryptocurrency market analytics powered by CoinGecko'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# COIN INFORMATION
# =========================================================

coins = {
    "Bitcoin": {
        "id": "bitcoin",
        "symbol": "₿"
    },

    "Ethereum": {
        "id": "ethereum",
        "symbol": "Ξ"
    },

    "Solana": {
        "id": "solana",
        "symbol": "◎"
    }
}


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Dashboard Controls")

selected_coin = st.sidebar.selectbox(
    "Select Cryptocurrency",
    list(coins.keys())
)


time_range = st.sidebar.radio(
    "Select Time Range",
    ["1H", "24H", "7D", "30D", "1Y"]
)


st.sidebar.divider()

st.sidebar.info(
    "Data source: CoinGecko API\n\n"
    "Dashboard refreshes automatically every 60 seconds."
)


# =========================================================
# SELECT COIN
# =========================================================

coin_id = coins[selected_coin]["id"]
coin_symbol = coins[selected_coin]["symbol"]


# =========================================================
# CURRENT PRICE API
# =========================================================

try:

    price_url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price"
    )

    price_params = {
        "ids": coin_id,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true",
        "include_24hr_vol": "true"
    }

    response = requests.get(
        price_url,
        params=price_params,
        timeout=20
    )

    response.raise_for_status()

    coin_data = response.json()[coin_id]

    current_price = coin_data["usd"]

    change_24h = coin_data.get(
        "usd_24h_change",
        0
    )

    market_cap = coin_data.get(
        "usd_market_cap",
        0
    )

    volume = coin_data.get(
        "usd_24h_vol",
        0
    )


    # =====================================================
    # HEADER
    # =====================================================

    st.subheader(
        f"{coin_symbol} {selected_coin}"
    )


    # =====================================================
    # METRIC CARDS
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)


    with col1:

        st.metric(
            "Current Price",
            f"${current_price:,.2f}",
            f"{change_24h:.2f}%"
        )


    with col2:

        st.metric(
            "24H Change",
            f"{change_24h:.2f}%"
        )


    with col3:

        st.metric(
            "Market Cap",
            f"${market_cap / 1e9:.2f}B"
        )


    with col4:

        st.metric(
            "24H Volume",
            f"${volume / 1e9:.2f}B"
        )


    st.divider()


    # =====================================================
    # HISTORICAL PRICE DATA
    # =====================================================

    days_map = {

        "1H": 1,

        "24H": 1,

        "7D": 7,

        "30D": 30,

        "1Y": 365
    }


    chart_url = (
        "https://api.coingecko.com/api/v3/"
        f"coins/{coin_id}/market_chart"
    )


    chart_params = {

        "vs_currency": "usd",

        "days": days_map[time_range]
    }


    chart_response = requests.get(
        chart_url,
        params=chart_params,
        timeout=20
    )


    chart_response.raise_for_status()


    historical_prices = (
        chart_response
        .json()["prices"]
    )


    # =====================================================
    # DATAFRAME
    # =====================================================

    df = pd.DataFrame(
        historical_prices,
        columns=[
            "timestamp",
            "price"
        ]
    )


    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms"
    )


    # =====================================================
    # LAST 1 HOUR FILTER
    # =====================================================

    if time_range == "1H":

        one_hour_ago = (
            df["timestamp"].max()
            - pd.Timedelta(hours=1)
        )

        df = df[
            df["timestamp"] >= one_hour_ago
        ]


    # =====================================================
    # ANOMALY DETECTION
    # =====================================================

    df["rolling_mean"] = (
        df["price"]
        .rolling(
            window=20,
            min_periods=5
        )
        .mean()
    )


    df["rolling_std"] = (
        df["price"]
        .rolling(
            window=20,
            min_periods=5
        )
        .std()
    )


    df["z_score"] = (
        (df["price"] - df["rolling_mean"])
        / df["rolling_std"]
    )


    df["anomaly"] = (
        df["z_score"].abs() > 2
    )


    anomaly_count = int(
        df["anomaly"].sum()
    )


    # =====================================================
    # PRICE CHART
    # =====================================================

    st.subheader(
        f"{selected_coin} Price Chart"
    )


    fig = go.Figure()


    # Main price line

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["price"],
            mode="lines",
            name="Price",
            line=dict(
                width=3
            ),
            hovertemplate=
                "<b>$%{y:,.2f}</b>"
                "<br>%{x|%d %b %Y, %H:%M}"
                "<extra></extra>"
        )
    )


    # =====================================================
    # ANOMALY POINTS
    # =====================================================

    anomaly_df = df[
        df["anomaly"] == True
    ]


    if not anomaly_df.empty:

        fig.add_trace(
            go.Scatter(
                x=anomaly_df["timestamp"],
                y=anomaly_df["price"],
                mode="markers",
                name="Anomaly",
                marker=dict(
                    size=9,
                    symbol="circle"
                ),
                hovertemplate=
                    "<b>Anomaly</b>"
                    "<br>$%{y:,.2f}"
                    "<br>%{x|%d %b %Y, %H:%M}"
                    "<extra></extra>"
            )
        )


    # =====================================================
    # CHART DESIGN
    # =====================================================

    fig.update_layout(

        height=500,

        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10
        ),

        xaxis=dict(
            showgrid=False,
            title=""
        ),

        yaxis=dict(
            showgrid=True,
            title="USD",
            tickprefix="$",
            tickformat=",.0f"
        ),

        hovermode="x unified",

        dragmode="zoom",

        showlegend=True,

        plot_bgcolor="rgba(0,0,0,0)",

        paper_bgcolor="rgba(0,0,0,0)"
    )


    st.plotly_chart(
        fig,
        use_container_width=True
    )


    # =====================================================
    # MARKET STATUS
    # =====================================================

    st.subheader("Market Status")


    status_col1, status_col2 = st.columns(2)


    with status_col1:

        if change_24h >= 0:

            st.success(
                f"📈 {selected_coin} is up "
                f"{change_24h:.2f}% in the last 24 hours."
            )

        else:

            st.error(
                f"📉 {selected_coin} is down "
                f"{abs(change_24h):.2f}% in the last 24 hours."
            )


    with status_col2:

        if anomaly_count > 0:

            st.warning(
                f"🚨 {anomaly_count} unusual "
                f"price movement(s) detected."
            )

        else:

            st.success(
                "🟢 No significant price anomalies detected."
            )


    # =====================================================
    # RECENT DATA TABLE
    # =====================================================

    st.subheader("Recent Market Data")


    display_df = df[
        [
            "timestamp",
            "price",
            "z_score",
            "anomaly"
        ]
    ].tail(10).copy()


    display_df["timestamp"] = (
        display_df["timestamp"]
        .dt.strftime("%d %b %Y %H:%M")
    )


    display_df["price"] = (
        display_df["price"]
        .map(
            lambda x: f"${x:,.2f}"
        )
    )


    display_df["z_score"] = (
        display_df["z_score"]
        .round(2)
    )


    display_df = display_df.rename(
        columns={
            "timestamp": "Time",
            "price": "Price",
            "z_score": "Z-Score",
            "anomaly": "Anomaly"
        }
    )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # FOOTER
    # =====================================================

    st.divider()


    st.success(
        "🟢 Live data connected | "
        f"Last updated: "
        f"{pd.Timestamp.now().strftime('%d %b %Y, %H:%M:%S')}"
    )


    st.caption(
        "Crypto Market Intelligence Dashboard | "
        "CoinGecko API | Python | Streamlit | Plotly"
    )


# =========================================================
# ERROR HANDLING
# =========================================================

except requests.exceptions.RequestException:

    st.error(
        "Unable to connect to CoinGecko API. "
        "Please check your internet connection "
        "and try again."
    )


except Exception as e:

    st.error(
        "Something went wrong while loading the dashboard."
    )

    st.write(e)