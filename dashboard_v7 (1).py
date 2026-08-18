# Review Insight Copilot v7 - 채널(맘큐/스마트스토어)별 리뷰 감성·VOC 비교 분석 대시보드
# Co-authored with CoCo
# -*- coding: utf-8 -*-
"""
Review Insight Copilot v7
v6 → v7 변경
- 채널(SOURCE_CHANNEL) 필터 + 채널별 리뷰 수 KPI + 채널별 감성 비교 차트 (맘큐 vs 스마트스토어)
- 리뷰 키워드 순위 TOP20 + 긍정/부정 키워드 TOP10 분리 차트
- 채널 × VOC 교차 분석 (VOC 탭)
- 분석 기간·채널 캡션 표시
- SOURCE_CHANNEL 컬럼이 아직 없어도 동작하도록 안전 처리
"""

import os
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
CHANNEL_RANGE = ["#7c3aed", "#059669", "#f59e0b", "#0ea5e9"]

# 채널 컬럼명 — 테이블에 없으면 자동으로 채널 기능이 비활성화됨
CHANNEL_COL = "SOURCE_CHANNEL"


# ──────────────────────────────────────────────
# Snowflake 연결
# ──────────────────────────────────────────────
def _get_connection():
    private_key_text = None
    try:
        private_key_text = st.secrets["connections"]["snowflake"].get("private_key")
    except Exception:
        pass

    if private_key_text:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        p_key = serialization.load_pem_private_key(
            private_key_text.encode("utf-8"), password=None, backend=default_backend()
        )
        private_key_der = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return st.connection("snowflake", private_key=private_key_der)

    return st.connection("snowflake", ttl=os.getenv("SNOWFLAKE_CONNECTION_TTL"))


conn = _get_connection()


@st.cache_data(ttl=60)
def load_data():
    # SOURCE_CHANNEL이 아직 없는 테이블에서도 깨지지 않도록 컬럼 존재 여부 확인
    cols_df = conn.query("""
        SELECT COLUMN_NAME
        FROM SIDA_DB.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'BRONZE'
          AND TABLE_NAME = 'REVIEWS_VOC_ANALYSIS'
    """, ttl=600)

    has_channel = CHANNEL_COL in set(cols_df["COLUMN_NAME"].str.upper())
    channel_select = f"{CHANNEL_COL}," if has_channel else ""

    df = conn.query(f"""
        SELECT REVIEW_CODE, PRODUCT_CODE, PRODUCT_NAME, TEXT, RATING, CREATED_DATE,
               {channel_select}
               SENTIMENT, NEGATIVE_CATEGORY, VOC, CLASSIFICATION_REASON,
               PRODUCT_CATEGORY, REPURCHASE_INTENT, KEYWORDS, ANALYZED_AT
        FROM SIDA_DB.BRONZE.REVIEWS_VOC_ANALYSIS
        ORDER BY ANALYZED_AT DESC
    """, ttl=60)

    if not has_channel:
        df[CHANNEL_COL] = "미지정"

    df["_날짜"] = pd.to_datetime(
        df["CREATED_DATE"].astype(str).str.replace(r"\.$", "", regex=True),
        format="%Y.%m.%d. %H:%M:%S",
        errors="coerce",
    )
    return df, has_channel


def llm_keyword_counter(series: pd.Series) -> Counter:
    """LLM이 추출한 핵심키워드 컬럼을 집계한다."""
    bag = []
    for kw_str in series.dropna():
        for kw in str(kw_str).split(","):
            cleaned = kw.strip().strip("{}[]\"'")
            if cleaned:
                bag.append(cleaned)
    return Counter(bag)


def keyword_bar(counter: Counter, top_n: int, color: str, height: int):
    kdf = pd.DataFrame(counter.most_common(top_n), columns=["키워드", "빈도"])
    if kdf.empty:
        return None
    return alt.Chart(kdf).mark_bar(color=color).encode(
        x=alt.X("빈도:Q"),
        y=alt.Y("키워드:N", sort="-x"),
        tooltip=["키워드", "빈도"],
    ).properties(height=height)


# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.title("📊 Review Insight Copilot")
st.caption("Snowflake Cortex LLM (claude-4-sonnet) 기반 리뷰 감성·VOC·상품 리스크 자동 분석")

col_h1, col_h2 = st.columns([8, 1])
with col_h2:
    if st.button("🔄 새로고침"):
        load_data.clear()
        st.rerun()

with st.spinner("데이터 로딩 중..."):
    df, has_channel = load_data()

if df.empty:
    st.warning("분석 데이터가 없습니다. Task 실행 후 다시 확인해주세요.")
    st.stop()

# ──────────────────────────────────────────────
# 사이드바 필터
# ──────────────────────────────────────────────
with st.sidebar:
    st.header("🔎 필터")

    channel_options = sorted(df[CHANNEL_COL].dropna().unique().tolist())
    if has_channel:
        sel_channel = st.multiselect("채널", channel_options, default=[])
    else:
        sel_channel = []
        st.caption("채널 컬럼(SOURCE_CHANNEL)이 없어 채널 필터가 비활성화됐습니다.")

    sel_category = st.selectbox(
        "상품카테고리",
        ["전체"] + sorted(df["PRODUCT_CATEGORY"].dropna().unique().tolist())
    )

    sel_sentiment = st.selectbox("감성", ["전체", "긍정", "중립", "부정"])

    sel_voc = st.selectbox("VOC", ["전체"] + sorted(df["VOC"].dropna().unique().tolist()))

    sel_neg_cat = st.selectbox(
        "부정카테고리",
        ["전체"] + sorted(df["NEGATIVE_CATEGORY"].dropna().unique().tolist())
    )

    sel_repurchase = st.selectbox("재구매의향", ["전체", "있음", "없음", "불명"])

    st.divider()

    sel_products = st.multiselect(
        "특정 상품만 보기",
        sorted(df["PRODUCT_NAME"].dropna().unique()),
        default=[]
    )

filtered_df = df.copy()
if sel_channel:
    filtered_df = filtered_df[filtered_df[CHANNEL_COL].isin(sel_channel)]
if sel_category != "전체":
    filtered_df = filtered_df[filtered_df["PRODUCT_CATEGORY"] == sel_category]
if sel_sentiment != "전체":
    filtered_df = filtered_df[filtered_df["SENTIMENT"] == sel_sentiment]
if sel_voc != "전체":
    filtered_df = filtered_df[filtered_df["VOC"] == sel_voc]
if sel_neg_cat != "전체":
    filtered_df = filtered_df[filtered_df["NEGATIVE_CATEGORY"] == sel_neg_cat]
if sel_repurchase != "전체":
    filtered_df = filtered_df[filtered_df["REPURCHASE_INTENT"] == sel_repurchase]
if sel_products:
    filtered_df = filtered_df[filtered_df["PRODUCT_NAME"].isin(sel_products)]

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
avg_rating = round(filtered_df["RATING"].mean(), 2) if total else 0

repurchase_yes = int((filtered_df["REPURCHASE_INTENT"] == "있음").sum())
repurchase_rate = round(repurchase_yes / total * 100, 1) if total else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("전체 리뷰", f"{total:,}")
k2.metric("긍정", f"{positive:,}")
k3.metric("부정", f"{negative:,}")
k4.metric("긍정률", f"{positive_rate}%")
k5.metric("평균 평점", f"{avg_rating}⭐")
k6.metric("재구매 의향", f"{repurchase_rate}%")

# 채널별 리뷰 수 KPI (채널 컬럼이 있을 때만)
if has_channel:
    channel_counts = filtered_df[CHANNEL_COL].value_counts()
    ch_cols = st.columns(max(len(channel_counts), 1))
    for col, (ch, cnt) in zip(ch_cols, channel_counts.items()):
        ch_pos = int(((filtered_df[CHANNEL_COL] == ch) & (filtered_df["SENTIMENT"] == "긍정")).sum())
        ch_rate = round(ch_pos / cnt * 100, 1) if cnt else 0
        col.metric(f"{ch} 리뷰", f"{cnt:,}", help=f"{ch} 긍정률 {ch_rate}%")

# 분석 기간·채널 캡션
if filtered_df["_날짜"].notna().any():
    d_min = filtered_df["_날짜"].min().strftime("%Y-%m-%d")
    d_max = filtered_df["_날짜"].max().strftime("%Y-%m-%d")
    period_txt = f"분석 기간 : {d_min} ~ {d_max}"
else:
    period_txt = "분석 기간 : (날짜 정보 없음)"
selected_channels = ", ".join(sel_channel) if sel_channel else "전체"
st.caption(f"{period_txt} · 채널 : {selected_channels}")

# ──────────────────────────────────────────────
# 탭
# ──────────────────────────────────────────────
tab_dash, tab_voc, tab_product, tab_review, tab_insight = st.tabs(
    ["📈 대시보드", "🚨 VOC 분석", "📦 상품 분석", "📝 리뷰 상세", "💡 인사이트"]
)

# ── 대시보드 ──
with tab_dash:
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("감성 분포")
        sent_data = pd.DataFrame(
            {"감성": ["긍정", "중립", "부정"], "건수": [positive, neutral, negative]}
        )
        chart = alt.Chart(sent_data).mark_arc(innerRadius=55).encode(
            theta=alt.Theta("건수:Q"),
            color=alt.Color("감성:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE)),
            tooltip=["감성", "건수"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    with c2:
        st.subheader("상품카테고리별 리뷰 수")
        cat_count = filtered_df.groupby("PRODUCT_CATEGORY").size().reset_index(name="리뷰수")
        cat_count.columns = ["상품카테고리", "리뷰수"]
        chart = alt.Chart(cat_count).mark_bar().encode(
            x=alt.X("리뷰수:Q"),
            y=alt.Y("상품카테고리:N", sort="-x"),
            color=alt.Color("상품카테고리:N", legend=None),
            tooltip=["상품카테고리", "리뷰수"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    # 채널별 감성 비교 (핵심 추가)
    if has_channel and filtered_df[CHANNEL_COL].nunique() >= 1:
        st.subheader("📡 채널별 감성 비교")
        ch_sent = (
            filtered_df.groupby([CHANNEL_COL, "SENTIMENT"]).size()
            .reset_index(name="건수")
            .rename(columns={CHANNEL_COL: "채널"})
        )
        ch_tot = ch_sent.groupby("채널")["건수"].transform("sum")
        ch_sent["비율(%)"] = (ch_sent["건수"] / ch_tot * 100).round(1)

        cc1, cc2 = st.columns([3, 2])
        with cc1:
            chart = alt.Chart(ch_sent).mark_bar().encode(
                x=alt.X("비율(%):Q", stack="normalize", axis=alt.Axis(format="%"), title="비율"),
                y=alt.Y("채널:N"),
                color=alt.Color("SENTIMENT:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE), title="감성"),
                tooltip=["채널", "SENTIMENT", "건수", "비율(%)"],
            ).properties(height=120 + 40 * ch_sent["채널"].nunique())
            st.altair_chart(chart, use_container_width=True)

        with cc2:
            ch_summary = (
                filtered_df.groupby(CHANNEL_COL)
                .agg(
                    리뷰수=("REVIEW_CODE", "count"),
                    긍정률=("SENTIMENT", lambda x: round((x == "긍정").mean() * 100, 1)),
                    부정률=("SENTIMENT", lambda x: round((x == "부정").mean() * 100, 1)),
                    평균평점=("RATING", "mean"),
                    재구매의향=("REPURCHASE_INTENT", lambda x: round((x == "있음").mean() * 100, 1)),
                )
                .reset_index()
                .rename(columns={
                    CHANNEL_COL: "채널", "긍정률": "긍정률(%)",
                    "부정률": "부정률(%)", "재구매의향": "재구매의향(%)"
                })
            )
            ch_summary["평균평점"] = ch_summary["평균평점"].round(2)
            st.dataframe(ch_summary, use_container_width=True, hide_index=True)

    if filtered_df["_날짜"].notna().any():
        st.subheader("월별 감성 추이")
        trend = (
            filtered_df.dropna(subset=["_날짜"])
            .assign(월=lambda d: d["_날짜"].dt.to_period("M").astype(str))
            .groupby(["월", "SENTIMENT"]).size()
            .reset_index(name="건수")
        )
        chart = alt.Chart(trend).mark_line(point=True).encode(
            x=alt.X("월:N", title="월"),
            y=alt.Y("건수:Q"),
            color=alt.Color("SENTIMENT:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE), title="감성"),
            tooltip=["월", "SENTIMENT", "건수"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    c3, c4 = st.columns([2, 3])
    with c3:
        st.subheader("카테고리별 평균 평점")
        rating_df = (
            filtered_df.groupby("PRODUCT_CATEGORY")
            .agg(평균평점=("RATING", "mean"), 리뷰수=("RATING", "count"))
            .reset_index()
            .rename(columns={"PRODUCT_CATEGORY": "상품카테고리"})
        )
        rating_df["평균평점"] = rating_df["평균평점"].round(2)
        st.dataframe(
            rating_df.sort_values("평균평점", ascending=False),
            use_container_width=True, hide_index=True,
        )

    with c4:
        st.subheader("☁️ 리뷰 키워드 순위 TOP 20 (LLM 추출)")
        chart = keyword_bar(llm_keyword_counter(filtered_df["KEYWORDS"]), 20, "#6d28d9", 500)
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("추출된 키워드가 없습니다.")

    # 긍정/부정 키워드 분리
    st.subheader("키워드 감성 분리")
    kc1, kc2 = st.columns(2)
    with kc1:
        st.markdown("**👍 긍정 키워드 TOP 10**")
        chart = keyword_bar(
            llm_keyword_counter(filtered_df[filtered_df["SENTIMENT"] == "긍정"]["KEYWORDS"]),
            10, "#2563eb", 320,
        )
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("긍정 리뷰 키워드가 없습니다.")

    with kc2:
        st.markdown("**👎 부정 키워드 TOP 10**")
        chart = keyword_bar(
            llm_keyword_counter(filtered_df[filtered_df["SENTIMENT"] == "부정"]["KEYWORDS"]),
            10, "#dc2626", 320,
        )
        if chart is not None:
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("부정 리뷰 키워드가 없습니다.")

# ── VOC 분석 ──
with tab_voc:
    c1, c2 = st.columns([3, 2])

    with c1:
        st.subheader("VOC 분포")
        voc_counts = filtered_df["VOC"].value_counts().reset_index()
        voc_counts.columns = ["VOC", "건수"]
        chart = alt.Chart(voc_counts).mark_bar().encode(
            x=alt.X("VOC:N", sort="-y"),
            y=alt.Y("건수:Q"),
            color=alt.Color("VOC:N", legend=None),
            tooltip=["VOC", "건수"],
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
        st.dataframe(
            voc_neg.sort_values("부정률(%)", ascending=False),
            use_container_width=True, hide_index=True, height=350,
        )

    st.subheader("VOC × 감성 교차 분석")
    voc_sent = filtered_df.groupby(["VOC", "SENTIMENT"]).size().reset_index(name="건수")
    chart = alt.Chart(voc_sent).mark_bar().encode(
        x=alt.X("VOC:N", sort="-y", title="VOC"),
        y=alt.Y("건수:Q"),
        color=alt.Color("SENTIMENT:N", scale=alt.Scale(domain=SENT_DOMAIN, range=SENT_RANGE), title="감성"),
        tooltip=["VOC", "SENTIMENT", "건수"],
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # 채널 × VOC 교차
    if has_channel and filtered_df[CHANNEL_COL].nunique() >= 2:
        st.subheader("📡 채널 × VOC 교차 분석")
        ch_voc = (
            filtered_df.groupby([CHANNEL_COL, "VOC"]).size()
            .reset_index(name="건수")
            .rename(columns={CHANNEL_COL: "채널"})
        )
        chart = alt.Chart(ch_voc).mark_bar().encode(
            x=alt.X("VOC:N", sort="-y"),
            y=alt.Y("건수:Q"),
            color=alt.Color("채널:N", scale=alt.Scale(range=CHANNEL_RANGE)),
            xOffset="채널:N",
            tooltip=["채널", "VOC", "건수"],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    st.subheader("부정카테고리 분포")
    neg_df = filtered_df[filtered_df["NEGATIVE_CATEGORY"].notna()]
    if not neg_df.empty:
        neg_cat_counts = neg_df["NEGATIVE_CATEGORY"].value_counts().reset_index()
        neg_cat_counts.columns = ["부정카테고리", "건수"]
        chart = alt.Chart(neg_cat_counts).mark_bar().encode(
            x=alt.X("건수:Q"),
            y=alt.Y("부정카테고리:N", sort="-x"),
            color=alt.value("#dc2626"),
            tooltip=["부정카테고리", "건수"],
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("부정 리뷰가 없습니다.")

# ── 상품 분석 ──
with tab_product:
    st.subheader("상품별 리뷰 TOP 20")
    product_df = (
        filtered_df.groupby("PRODUCT_NAME")
        .agg(리뷰수=("REVIEW_CODE", "count"),
             평균평점=("RATING", "mean"),
             부정=("SENTIMENT", lambda x: (x == "부정").sum()),
             재구매의향=("REPURCHASE_INTENT", lambda x: (x == "있음").sum()))
        .reset_index()
        .rename(columns={"PRODUCT_NAME": "상품명"})
    )
    product_df["평균평점"] = product_df["평균평점"].round(2)
    st.dataframe(
        product_df.sort_values("리뷰수", ascending=False).head(20),
        use_container_width=True, hide_index=True,
    )

    st.subheader("⚠️ 상품 위험도 (부정 리뷰 비율)")
    min_reviews = st.slider(
        "최소 리뷰 수 (표본이 적은 상품 제외)", 1, 30, 5,
        help="리뷰 1~2건짜리 상품이 위험도 100%로 잡히는 걸 방지합니다.",
    )
    risk_df = (
        filtered_df.groupby("PRODUCT_NAME")
        .agg(전체리뷰=("SENTIMENT", "count"),
             부정리뷰=("SENTIMENT", lambda x: (x == "부정").sum()),
             평균평점=("RATING", "mean"))
        .reset_index()
        .rename(columns={"PRODUCT_NAME": "상품명"})
    )
    risk_df = risk_df[risk_df["전체리뷰"] >= min_reviews]
    risk_df["위험도(%)"] = (risk_df["부정리뷰"] / risk_df["전체리뷰"] * 100).round(1)
    risk_df["평균평점"] = risk_df["평균평점"].round(2)
    risk_df = risk_df.sort_values("위험도(%)", ascending=False)

    st.dataframe(
        risk_df[["상품명", "전체리뷰", "부정리뷰", "위험도(%)", "평균평점"]].head(20),
        use_container_width=True, hide_index=True,
    )

# ── 리뷰 상세 ──
with tab_review:
    search = st.text_input("리뷰 내 키워드 검색", placeholder="예: 배송, 트러블, 백탁")

    view_cols = [
        "SENTIMENT", CHANNEL_COL, "PRODUCT_CATEGORY", "VOC", "NEGATIVE_CATEGORY",
        "REPURCHASE_INTENT", "PRODUCT_NAME", "TEXT", "KEYWORDS",
        "CLASSIFICATION_REASON", "RATING",
    ]
    if not has_channel:
        view_cols.remove(CHANNEL_COL)

    view_df = filtered_df[view_cols].rename(columns={
        "SENTIMENT": "감성",
        CHANNEL_COL: "채널",
        "PRODUCT_CATEGORY": "상품카테고리",
        "NEGATIVE_CATEGORY": "부정카테고리",
        "REPURCHASE_INTENT": "재구매의향",
        "PRODUCT_NAME": "상품명",
        "TEXT": "리뷰",
        "KEYWORDS": "핵심키워드",
        "CLASSIFICATION_REASON": "분류사유",
        "RATING": "평점",
    })
    if search:
        view_df = view_df[view_df["리뷰"].str.contains(search, na=False)]

    st.caption(f"{len(view_df):,}건 표시 중")

    def color_sentiment(val):
        if val == "긍정":
            return "color:#2563eb;font-weight:bold"
        if val == "부정":
            return "color:#dc2626;font-weight:bold"
        return ""

    def highlight_row(row):
        if row["감성"] == "부정":
            return ["background-color:#fdf0f0"] * len(row)
        if row["감성"] == "긍정":
            return ["background-color:#f0f6fd"] * len(row)
        return [""] * len(row)

    styled = (
        view_df.style
        .map(color_sentiment, subset=["감성"])
        .apply(highlight_row, axis=1)
    )
    st.dataframe(styled, use_container_width=True, height=600)

# ── 인사이트 ──
with tab_insight:
    st.subheader("💡 경영진 요약")

    if positive_rate >= 80:
        st.success(f"긍정률 {positive_rate}% — 고객 만족도가 매우 높은 수준입니다.")
    elif positive_rate >= 60:
        st.warning(f"긍정률 {positive_rate}% — 만족도는 보통 수준이며 개선 여지가 있습니다.")
    else:
        st.error(f"긍정률 {positive_rate}% — 만족도 개선이 시급합니다.")

    st.caption(
        f"재구매 의향 명시 {repurchase_yes:,}건 ({repurchase_rate}%) · "
        f"평균 평점 {avg_rating}⭐"
    )

    # 채널 간 격차 코멘트
    if has_channel and filtered_df[CHANNEL_COL].nunique() >= 2:
        ch_neg = (
            filtered_df.groupby(CHANNEL_COL)["SENTIMENT"]
            .apply(lambda x: round((x == "부정").mean() * 100, 1))
            .sort_values(ascending=False)
        )
        worst_ch, worst_rate = ch_neg.index[0], ch_neg.iloc[0]
        best_ch, best_rate = ch_neg.index[-1], ch_neg.iloc[-1]
        gap = round(worst_rate - best_rate, 1)
        if gap >= 5:
            st.warning(
                f"📡 채널 격차: **{worst_ch}** 부정률 {worst_rate}% vs **{best_ch}** {best_rate}% "
                f"(격차 {gap}%p) — {worst_ch} 채널 VOC를 우선 점검하세요."
            )
        else:
            st.info(f"📡 채널 간 부정률 격차 {gap}%p — 채널별 편차는 크지 않습니다.")

    st.subheader("🎯 개선 우선순위 (부정 리뷰가 집중된 VOC)")
    neg_only = filtered_df[filtered_df["SENTIMENT"] == "부정"]
    if neg_only.empty:
        st.write("부정 리뷰가 없어 우선순위를 산출할 수 없습니다.")
    else:
        for rank, (voc, cnt) in enumerate(neg_only["VOC"].value_counts().head(5).items(), start=1):
            sub = neg_only[neg_only["VOC"] == voc]
            kw_counter = llm_keyword_counter(sub["KEYWORDS"])
            top_kw = ", ".join(w for w, _ in kw_counter.most_common(5))
            ch_txt = ""
            if has_channel and sub[CHANNEL_COL].nunique() >= 1:
                ch_break = sub[CHANNEL_COL].value_counts()
                ch_txt = " · " + ", ".join(f"{c} {n}건" for c, n in ch_break.items())
            st.markdown(f"**{rank}위 — {voc}** (부정 {cnt}건{ch_txt})")
            if top_kw:
                st.caption(f"LLM 추출 키워드: {top_kw}")
            for reason in sub["CLASSIFICATION_REASON"].head(2):
                if reason:
                    st.markdown(f"  - _{reason}_")

    st.subheader("📊 부정카테고리별 우선순위")
    neg_cat_only = filtered_df[filtered_df["NEGATIVE_CATEGORY"].notna()]
    if not neg_cat_only.empty:
        cat_rank = neg_cat_only["NEGATIVE_CATEGORY"].value_counts().reset_index()
        cat_rank.columns = ["부정카테고리", "건수"]
        cat_rank["비중(%)"] = (cat_rank["건수"] / cat_rank["건수"].sum() * 100).round(1)
        st.dataframe(cat_rank, use_container_width=True, hide_index=True)

    st.subheader("🔁 재구매 의향 분포")
    rep_dist = filtered_df["REPURCHASE_INTENT"].value_counts().reset_index()
    rep_dist.columns = ["재구매의향", "건수"]
    rep_dist["비중(%)"] = (rep_dist["건수"] / rep_dist["건수"].sum() * 100).round(1)
    st.dataframe(rep_dist, use_container_width=True, hide_index=True)

    st.subheader("⚠️ 주의 상품")
    watch = risk_df[risk_df["위험도(%)"] >= 30].head(5)
    if watch.empty:
        st.write(f"위험도 30% 이상 상품이 없습니다. (최소 리뷰 수 {min_reviews}건 기준)")
    else:
        for _, row in watch.iterrows():
            st.markdown(
                f"- **{row['상품명'][:45]}** — 위험도 {row['위험도(%)']}% "
                f"(부정 {int(row['부정리뷰'])}건 / 전체 {int(row['전체리뷰'])}건, 평균 {row['평균평점']}⭐)"
            )

# ──────────────────────────────────────────────
# 다운로드
# ──────────────────────────────────────────────
st.divider()
export_df = filtered_df.drop(columns=["_날짜"])
csv_bytes = export_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button(
    "📥 분석 결과 다운로드 (CSV — Excel 호환)",
    csv_bytes,
    file_name="review_voc_analysis.csv",
    mime="text/csv; charset=utf-8-sig",
)
