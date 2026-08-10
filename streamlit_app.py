# Review Insight Copilot - Snowflake Cortex LLM(claude-4-sonnet) 기반 VOC 분석 대시보드
# Co-authored with CoCo
# -*- coding: utf-8 -*-
"""
Review Insight Copilot v4 — Streamlit Community Cloud
- Snowflake REVIEWS_VOC_ANALYSIS 테이블 연동 (Key Pair 인증)
- claude-4-sonnet 기반 감성/부정카테고리/VOC/분류사유 분석
"""

import re
from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

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

STOP_WORDS = {
    "좋아요", "있어요", "합니다", "너무", "정말", "제품", "사용",
    "같아요", "그리고", "해서", "했는데", "인데", "해요", "이에요",
    "구매", "주문", "상품", "아이", "좋아",
}

REPURCHASE_KEYWORDS = ["재구매", "또 구매", "또 주문", "계속 사용", "계속 구매", "또 살"]

# ──────────────────────────────────────────────
# Snowflake 연결 (Key Pair 인증)
# ──────────────────────────────────────────────
private_key_text = st.secrets["connections"]["snowflake"]["private_key"]
private_key_bytes = private_key_text.encode("utf-8")
p_key = serialization.load_pem_private_key(
    private_key_bytes, password=None, backend=default_backend()
)
private_key_der = p_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

conn = st.connection("snowflake", private_key=private_key_der)


@st.cache_data(ttl=60)
def load_data():
    df = conn.query("""
        SELECT REVIEW_CODE, PRODUCT_CODE, PRODUCT_NAME, TEXT,
               SENTIMENT, NEGATIVE_CATEGORY, VOC, CLASSIFICATION_REASON,
               ANALYZED_AT
        FROM SIDA_DB.BRONZE.REVIEWS_VOC_ANALYSIS
        ORDER BY ANALYZED_AT DESC
    """, ttl=60)
    return df


# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.title("📊 Review Insight Copilot")
st.caption("Snowflake Cortex LLM (claude-4-sonnet) 기반 리뷰 감성·VOC·리스크 자동 분석")

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
    st.header("🔎 필터")

    products = sorted(df["PRODUCT_NAME"].dropna().unique())
    sel_products = st.multiselect("상품", products, default=[])

    sel_sentiment = st.selectbox("감성", ["전체", "긍정", "중립", "부정"])

    voc_list = sorted(df["VOC"].dropna().unique())
    sel_voc = st.selectbox("VOC", ["전체"] + voc_list)

    neg_cats = sorted(df["NEGATIVE_CATEGORY"].dropna().unique())
    sel_neg_cat = st.selectbox("부정카테고리", ["전체"] + neg_cats)

filtered_df = df.copy()
if sel_products:
    filtered_df = filtered_df[filtered_df["PRODUCT_NAME"].isin(sel_products)]
if sel_sentiment != "전체":
    filtered_df = filtered_df[filtered_df["SENTIMENT"] == sel_sentiment]
if sel_voc != "전체":
    filtered_df = filtered_df[filtered_df["VOC"] == sel_voc]
if sel_neg_cat != "전체":
    filtered_df = filtered_df[filtered_df["NEGATIVE_CATEGORY"] == sel_neg_cat]

if filtered_df.empty:
    st.warning("조건에 맞는 리뷰가 없습니다. 필터를 조정해주세요.")
    st.stop()

# ──────────────────────────────────────────────
# KPI
# ──────────────────────────────────────────────
total = len(filtered_df)
positive = int((filtered_df["SENTIMENT"] == "긍정").sum())
negative = int((filtered_df["SENTIMENT"] == "부정").sum())
neutral = int((filtered_df["SENTIMENT"] == "중립").sum())
positive_rate = round(positive / total * 100, 1) if total else 0

repurchase_count = int(
    filtered_df["TEXT"].fillna("").apply(
        lambda x: any(k in x for k in REPURCHASE_KEYWORDS)
    ).sum()
)
repurchase_rate = round(repurchase_count / total * 100, 1) if total else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("전체 리뷰", f"{total:,}")
k2.metric("긍정", f"{positive:,}")
k3.metric("부정", f"{negative:,}")
k4.metric("긍정률", f"{positive_rate}%")
k5.metric("재구매 의향", f"{repurchase_rate}%")

# ──────────────────────────────────────────────
# 탭
# ──────────────────────────────────────────────
tab_dash, tab_voc, tab_product, tab_review, tab_insight = st.tabs(
    ["📈 대시보드", "🚨 VOC 분석", "📦 상품 분석", "📝 리뷰 상세", "💡 인사이트"]
)

with tab_dash:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("감성 분포")
        sent_data = pd.DataFrame(
            {"감성": ["긍정", "중립", "부정"], "건수": [positive, neutral, negative]}
        )
        chart = alt.Chart(sent_data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("건수:Q"),
            color=alt.Color("감성:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE)),
            tooltip=["감성", "건수"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    with c2:
        st.subheader("VOC 분포 (Top 10)")
        voc_counts = filtered_df["VOC"].value_counts().head(10).reset_index()
        voc_counts.columns = ["VOC", "건수"]
        chart = alt.Chart(voc_counts).mark_bar().encode(
            x=alt.X("건수:Q"),
            y=alt.Y("VOC:N", sort="-x"),
            color=alt.Color("VOC:N", legend=None),
            tooltip=["VOC", "건수"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    st.subheader("🔥 TOP 키워드")
    text_blob = " ".join(filtered_df["TEXT"].fillna(""))
    words = [w for w in re.findall(r"[가-힣]{2,}", text_blob) if w not in STOP_WORDS]
    keyword_df = pd.DataFrame(Counter(words).most_common(20), columns=["키워드", "빈도"])
    if not keyword_df.empty:
        chart = alt.Chart(keyword_df).mark_bar().encode(
            x=alt.X("빈도:Q"), y=alt.Y("키워드:N", sort="-x"), tooltip=["키워드", "빈도"],
        ).properties(height=450)
        st.altair_chart(chart, use_container_width=True)

with tab_voc:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("VOC별 감성 분포")
        voc_sent = filtered_df.groupby(["VOC", "SENTIMENT"]).size().reset_index(name="건수")
        chart = alt.Chart(voc_sent).mark_bar().encode(
            x=alt.X("VOC:N", sort="-y"), y=alt.Y("건수:Q"),
            color=alt.Color("SENTIMENT:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE), title="감성"),
            xOffset="SENTIMENT:N", tooltip=["VOC", "SENTIMENT", "건수"],
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)
    with c2:
        st.subheader("VOC별 부정률")
        voc_neg = (
            filtered_df.groupby("VOC")
            .agg(전체=("REVIEW_CODE", "count"), 부정=("SENTIMENT", lambda x: (x == "부정").sum()))
            .reset_index()
        )
        voc_neg["부정률(%)"] = (voc_neg["부정"] / voc_neg["전체"] * 100).round(1)
        voc_neg = voc_neg.sort_values("부정률(%)", ascending=False)
        st.dataframe(voc_neg, use_container_width=True, hide_index=True)

    st.subheader("부정카테고리 분포")
    neg_df = filtered_df[filtered_df["NEGATIVE_CATEGORY"].notna()]
    if not neg_df.empty:
        neg_cat_counts = neg_df["NEGATIVE_CATEGORY"].value_counts().reset_index()
        neg_cat_counts.columns = ["부정카테고리", "건수"]
        chart = alt.Chart(neg_cat_counts).mark_bar().encode(
            x=alt.X("건수:Q"), y=alt.Y("부정카테고리:N", sort="-x"),
            color=alt.value("#dc2626"), tooltip=["부정카테고리", "건수"],
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("부정 리뷰가 없습니다.")

with tab_product:
    st.subheader("⚠️ 상품 위험도 (부정 리뷰 비율)")
    min_reviews = st.slider("최소 리뷰 수", 1, 30, 5)
    risk_df = (
        filtered_df.groupby("PRODUCT_NAME")
        .agg(전체리뷰=("SENTIMENT", "count"), 부정리뷰=("SENTIMENT", lambda x: (x == "부정").sum()))
        .reset_index()
    )
    risk_df = risk_df[risk_df["전체리뷰"] >= min_reviews]
    risk_df["위험도(%)"] = (risk_df["부정리뷰"] / risk_df["전체리뷰"] * 100).round(1)
    risk_df = risk_df.sort_values("위험도(%)", ascending=False)
    risk_df["상품명(축약)"] = risk_df["PRODUCT_NAME"].str[:35]
    top15 = risk_df.head(15)
    if not top15.empty:
        chart = alt.Chart(top15).mark_bar().encode(
            x=alt.X("위험도(%):Q"), y=alt.Y("상품명(축약):N", sort="-x"),
            color=alt.Color("위험도(%):Q", scale=alt.Scale(scheme="redyellowgreen", reverse=True)),
            tooltip=["PRODUCT_NAME", "위험도(%)", "전체리뷰", "부정리뷰"],
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

with tab_review:
    search = st.text_input("리뷰 내 키워드 검색", placeholder="예: 배송, 트러블, 백탁")
    view_df = filtered_df[["SENTIMENT", "VOC", "NEGATIVE_CATEGORY", "PRODUCT_NAME", "TEXT", "CLASSIFICATION_REASON"]].rename(
        columns={"SENTIMENT": "감성", "NEGATIVE_CATEGORY": "부정카테고리",
                 "PRODUCT_NAME": "상품명", "TEXT": "리뷰", "CLASSIFICATION_REASON": "분류사유"}
    )
    if search:
        view_df = view_df[view_df["리뷰"].str.contains(search, na=False)]
    st.caption(f"{len(view_df):,}건 표시 중")
    st.dataframe(view_df, use_container_width=True, height=600)

with tab_insight:
    st.subheader("💡 경영진 요약")
    if positive_rate >= 80:
        st.success(f"긍정률 {positive_rate}% — 고객 만족도가 매우 높은 수준입니다.")
    elif positive_rate >= 60:
        st.warning(f"긍정률 {positive_rate}% — 만족도는 보통 수준이며 개선 여지가 있습니다.")
    else:
        st.error(f"긍정률 {positive_rate}% — 만족도 개선이 시급합니다.")

    st.subheader("🎯 개선 우선순위 (부정카테고리별)")
    neg_only = filtered_df[filtered_df["NEGATIVE_CATEGORY"].notna()]
    if neg_only.empty:
        st.write("부정 리뷰가 없어 우선순위를 산출할 수 없습니다.")
    else:
        neg_cat_rank = neg_only["NEGATIVE_CATEGORY"].value_counts()
        for rank, (cat, cnt) in enumerate(neg_cat_rank.head(5).items(), start=1):
            cat_reviews = neg_only[neg_only["NEGATIVE_CATEGORY"] == cat]["TEXT"]
            blob = " ".join(cat_reviews.fillna(""))
            kw = [w for w in re.findall(r"[가-힣]{2,}", blob) if w not in STOP_WORDS]
            top_kw = ", ".join(w for w, _ in Counter(kw).most_common(5))
            st.markdown(f"**{rank}위 — {cat}** (부정 {cnt}건)")
            if top_kw:
                st.caption(f"관련 키워드: {top_kw}")
            sample_reasons = neg_only[neg_only["NEGATIVE_CATEGORY"] == cat]["CLASSIFICATION_REASON"].head(3)
            for reason in sample_reasons:
                if reason:
                    st.markdown(f"  - _{reason}_")

    st.subheader("⚠️ 주의 상품")
    watch = risk_df[risk_df["위험도(%)"] >= 30].head(3)
    if watch.empty:
        st.write(f"위험도 30% 이상 상품이 없습니다. (최소 리뷰 수 {min_reviews}건 기준)")
    else:
        for _, row in watch.iterrows():
            st.markdown(
                f"- **{row['PRODUCT_NAME'][:40]}** — 위험도 {row['위험도(%)']}% "
                f"(부정 {int(row['부정리뷰'])}건 / 전체 {int(row['전체리뷰'])}건)"
            )

# ──────────────────────────────────────────────
# 다운로드
# ──────────────────────────────────────────────
st.divider()
csv_bytes = filtered_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "📥 분석 결과 다운로드 (CSV — Excel 호환)",
    csv_bytes,
    file_name="review_voc_analysis.csv",
    mime="text/csv; charset=utf-8-sig",
)
