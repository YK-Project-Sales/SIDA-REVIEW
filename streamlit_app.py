# Review Insight Copilot - Snowflake VOC 분석 결과 대시보드 (Community Cloud 배포용)
# Co-authored with CoCo
# -*- coding: utf-8 -*-
"""
Review Insight Copilot v3 — Streamlit Community Cloud
- Snowflake REVIEWS_VOC_ANALYSIS 테이블 연동
- Cortex LLM 기반 VOC 분류 결과 시각화
- 감성/VOC 카테고리/상품별 분석
"""

from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────
# 기본 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Review Insight Copilot",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
<style>
    html, body, [class*="css"] {
        font-family: "Pretendard", "Noto Sans KR", sans-serif;
    }
    div[data-testid="stMetric"] {
        background: #f7f9fc;
        border: 1px solid #e3e8f0;
        border-radius: 10px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.85rem;
        color: #5b6b82;
    }
</style>
    """,
    unsafe_allow_html=True,
)

SENT_DOMAIN = ["긍정", "중립", "부정"]
SENT_RANGE = ["#2563eb", "#94a3b8", "#dc2626"]

# ──────────────────────────────────────────────
# Snowflake 연결 (secrets.toml 기반)
# ──────────────────────────────────────────────
conn = st.connection("snowflake")


@st.cache_data(ttl=600)
def load_data():
    df = conn.query("""
        SELECT REVIEW_CODE, PRODUCT_NAME, TEXT, RATING, CREATED_DATE,
               SENTIMENT, VOC_CATEGORY, VOC_KEYWORDS, ANALYZED_AT
        FROM SIDA_DB.BRONZE.REVIEWS_VOC_ANALYSIS
        ORDER BY ANALYZED_AT DESC
    """)
    return df


# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.title("📊 Review Insight Copilot")
st.caption("Snowflake Cortex LLM 기반 리뷰 VOC 자동 분석 대시보드")

col_h1, col_h2 = st.columns([8, 1])
with col_h2:
    if st.button("🔄 새로고침"):
        load_data.clear()
        st.rerun()

with st.spinner("데이터 로딩 중..."):
    df = load_data()

if df.empty:
    st.warning("분석 데이터가 없습니다. Task 실행 후 다시 확인해주세요.")
    st.stop()

# ──────────────────────────────────────────────
# 사이드바 필터
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 필터")

    products = sorted(df["PRODUCT_NAME"].dropna().unique())
    sel_products = st.multiselect("상품", products, default=[])

    sentiments = ["긍정", "중립", "부정"]
    sel_sentiments = st.multiselect("감성", sentiments, default=sentiments)

    categories = sorted(df["VOC_CATEGORY"].dropna().unique())
    sel_categories = st.multiselect("VOC 카테고리", categories, default=[])

filtered = df.copy()
if sel_products:
    filtered = filtered[filtered["PRODUCT_NAME"].isin(sel_products)]
if sel_sentiments:
    filtered = filtered[filtered["SENTIMENT"].isin(sel_sentiments)]
if sel_categories:
    filtered = filtered[filtered["VOC_CATEGORY"].isin(sel_categories)]

# ──────────────────────────────────────────────
# KPI 요약
# ──────────────────────────────────────────────
st.divider()
c1, c2, c3, c4 = st.columns(4)
total = len(filtered)
pos_count = len(filtered[filtered["SENTIMENT"] == "긍정"])
neg_count = len(filtered[filtered["SENTIMENT"] == "부정"])
avg_rating = filtered["RATING"].mean() if total > 0 else 0

c1.metric("전체 리뷰", f"{total:,}건")
c2.metric("긍정 비율", f"{pos_count/total*100:.1f}%" if total else "0%")
c3.metric("부정 리뷰", f"{neg_count:,}건")
c4.metric("평균 평점", f"{avg_rating:.1f}⭐")

# ──────────────────────────────────────────────
# 탭
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 감성 분석", "🏷️ VOC 분류", "⚠️ 상품별 리스크", "📋 원본 데이터"])

with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("감성 분포")
        sent_counts = filtered["SENTIMENT"].value_counts().reset_index()
        sent_counts.columns = ["감성", "건수"]
        chart_pie = alt.Chart(sent_counts).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("건수:Q"),
            color=alt.Color("감성:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE)),
            tooltip=["감성", "건수"],
        ).properties(height=300)
        st.altair_chart(chart_pie, use_container_width=True)

    with col2:
        st.subheader("평점별 감성 분포")
        rating_sent = filtered.groupby(["RATING", "SENTIMENT"]).size().reset_index(name="건수")
        chart_bar = alt.Chart(rating_sent).mark_bar().encode(
            x=alt.X("RATING:O", title="평점"),
            y=alt.Y("건수:Q"),
            color=alt.Color("SENTIMENT:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE), title="감성"),
            tooltip=["RATING", "SENTIMENT", "건수"],
        ).properties(height=300)
        st.altair_chart(chart_bar, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("VOC 카테고리 분포")
        voc_counts = filtered["VOC_CATEGORY"].value_counts().reset_index()
        voc_counts.columns = ["카테고리", "건수"]
        chart_voc = alt.Chart(voc_counts).mark_bar().encode(
            x=alt.X("건수:Q"),
            y=alt.Y("카테고리:N", sort="-x"),
            color=alt.Color("카테고리:N", legend=None),
            tooltip=["카테고리", "건수"],
        ).properties(height=300)
        st.altair_chart(chart_voc, use_container_width=True)

    with col2:
        st.subheader("감성별 VOC 카테고리")
        voc_sent = filtered.groupby(["VOC_CATEGORY", "SENTIMENT"]).size().reset_index(name="건수")
        chart_vs = alt.Chart(voc_sent).mark_bar().encode(
            x=alt.X("VOC_CATEGORY:N", title="카테고리"),
            y=alt.Y("건수:Q"),
            color=alt.Color("SENTIMENT:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE), title="감성"),
            xOffset="SENTIMENT:N",
            tooltip=["VOC_CATEGORY", "SENTIMENT", "건수"],
        ).properties(height=300)
        st.altair_chart(chart_vs, use_container_width=True)

    st.subheader("주요 키워드 (Top 20)")
    all_keywords = []
    for kw_str in filtered["VOC_KEYWORDS"].dropna():
        for kw in kw_str.split(","):
            cleaned = kw.strip()
            if cleaned and len(cleaned) > 1:
                all_keywords.append(cleaned)
    if all_keywords:
        kw_counter = Counter(all_keywords).most_common(20)
        kw_df = pd.DataFrame(kw_counter, columns=["키워드", "빈도"])
        chart_kw = alt.Chart(kw_df).mark_bar().encode(
            x=alt.X("빈도:Q"),
            y=alt.Y("키워드:N", sort="-x"),
            tooltip=["키워드", "빈도"],
        ).properties(height=400)
        st.altair_chart(chart_kw, use_container_width=True)
    else:
        st.info("키워드 데이터가 없습니다.")

with tab3:
    st.subheader("상품별 부정 리뷰 비율")
    min_reviews = st.slider("최소 리뷰 수", 5, 50, 10)

    product_stats = filtered.groupby("PRODUCT_NAME").agg(
        전체=("REVIEW_CODE", "count"),
        부정=("SENTIMENT", lambda x: (x == "부정").sum()),
        평균평점=("RATING", "mean"),
    ).reset_index()
    product_stats = product_stats[product_stats["전체"] >= min_reviews]
    product_stats["위험도(%)"] = (product_stats["부정"] / product_stats["전체"] * 100).round(1)
    product_stats = product_stats.sort_values("위험도(%)", ascending=False)

    top15 = product_stats.head(15).copy()
    top15["상품(축약)"] = top15["PRODUCT_NAME"].str[:30]
    chart_risk = alt.Chart(top15).mark_bar().encode(
        x=alt.X("위험도(%):Q"),
        y=alt.Y("상품(축약):N", sort="-x"),
        color=alt.Color("위험도(%):Q", scale=alt.Scale(scheme="redyellowgreen", reverse=True)),
        tooltip=["PRODUCT_NAME", "위험도(%)", "전체", "부정"],
    ).properties(height=400)
    st.altair_chart(chart_risk, use_container_width=True)

    st.subheader("⚠️ 주의 상품")
    watch = product_stats[product_stats["위험도(%)"] >= 30].head(5)
    if watch.empty:
        st.write(f"위험도 30% 이상 상품이 없습니다. (최소 리뷰 수 {min_reviews}건 기준)")
    else:
        for _, row in watch.iterrows():
            st.markdown(
                f"- **{row['PRODUCT_NAME'][:40]}** — 위험도 {row['위험도(%)']}% "
                f"(부정 {int(row['부정'])}건 / 전체 {int(row['전체'])}건, 평균 {row['평균평점']:.1f}⭐)"
            )

with tab4:
    st.subheader("분석 결과 원본")
    st.dataframe(
        filtered[["PRODUCT_NAME", "TEXT", "RATING", "SENTIMENT", "VOC_CATEGORY", "VOC_KEYWORDS", "CREATED_DATE"]],
        use_container_width=True,
        height=500,
    )

# ──────────────────────────────────────────────
# 다운로드
# ──────────────────────────────────────────────
st.divider()
csv = filtered.to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    "📥 분석 결과 다운로드 (CSV)",
    csv,
    file_name="review_voc_analysis.csv",
    mime="text/csv",
)
