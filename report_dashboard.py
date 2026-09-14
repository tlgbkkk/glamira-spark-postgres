from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

from spark_job.config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

st.set_page_config(page_title="Glamira Product View Reports", layout="wide")


@st.cache_resource
def get_engine():
    url = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    return create_engine(url)


def run_query(sql, params=None):
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


st.title("Glamira Product View — Real-time Reports")

if st.sidebar.button("Refresh"):
    st.cache_data.clear()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Top 10 sản phẩm được xem nhiều nhất hôm nay")
    df = run_query("SELECT * FROM glamira.rpt_top10_products_today;")
    if df.empty:
        st.info("Chưa có dữ liệu.")
    else:
        st.bar_chart(df.set_index("product_id")["view_count"])

with col2:
    st.subheader("Top 10 quốc gia có lượt xem nhiều nhất hôm nay")
    df = run_query("SELECT * FROM glamira.rpt_top10_countries_today;")
    if df.empty:
        st.info("Chưa có dữ liệu.")
    else:
        st.bar_chart(df.set_index("country")["view_count"])

st.subheader("Top 5 referrer_url có lượt xem nhiều nhất hôm nay")
df = run_query("SELECT * FROM glamira.rpt_top5_referrers_today;")
if df.empty:
    st.info("Chưa có dữ liệu.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
col3, col4 = st.columns(2)

with col3:
    st.subheader("Lượt xem theo store_id — theo quốc gia")
    countries_df = run_query("SELECT DISTINCT country_name AS country FROM glamira.dim_location ORDER BY country_name;")
    countries = countries_df["country"].tolist() if not countries_df.empty else []
    if countries:
        selected_country = st.selectbox("Chọn quốc gia", countries)
        df = run_query(
            "SELECT * FROM glamira.get_store_views_by_country(:country);",
            params={"country": selected_country},
        )
        if df.empty:
            st.info("Không có dữ liệu cho quốc gia này.")
        else:
            st.bar_chart(df.set_index("store_id")["view_count"])

    else:
        st.info("Chưa có dữ liệu để chọn quốc gia.")

with col4:
    st.subheader("Lượt xem theo giờ — theo product_id")
    product_id = st.text_input("Nhập product_id", value="").strip()
    selected_date = st.date_input("Ngày", value=date.today())
    if product_id:
        df = run_query(
            "SELECT * FROM glamira.get_hourly_views_by_product(:pid, :d);",
            params={"pid": product_id, "d": selected_date},
        )

        if df.empty:
            st.info("Không có dữ liệu cho product_id / ngày này.")
        else:
            df["event_hour"] = pd.to_numeric(df["event_hour"], errors="coerce")
            df["view_count"] = pd.to_numeric(df["view_count"], errors="coerce")

            df = df.dropna(subset=["event_hour", "view_count"])

            df = df.sort_values("event_hour")

            fig = px.line(
                df,
                x="event_hour",
                y="view_count",
                markers=True,
            )

            fig.update_layout(
                xaxis_title="Giờ trong ngày",
                yaxis_title="Lượt xem",
                xaxis=dict(
                    tickmode="linear",
                    tick0=0,
                    dtick=1,
                ),
            )

            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Nhập product_id để xem biểu đồ.")

st.divider()

st.subheader("Lượt xem theo giờ — theo browser & OS (hôm nay)")
df = run_query("SELECT * FROM glamira.rpt_hourly_views_by_browser_os_today;")
if df.empty:
    st.info("Chưa có dữ liệu.")
else:
    df["series"] = df["browser"] + " / " + df["os"]
    fig = px.line(df, x="event_hour", y="view_count", color="series", markers=True)
    fig.update_layout(
        xaxis_title="Giờ trong ngày",
        yaxis_title="Lượt xem",
        legend_title="Browser / OS",
    )
    st.plotly_chart(fig, use_container_width=True)
