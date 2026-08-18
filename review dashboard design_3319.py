"""
리뷰 분석 대시보드 고도화 설계안
맘큐 / 네이버 스마트스토어 리뷰 데이터 기반

이 파일은 대시보드 설계 내용을 파이썬 데이터 구조(dict/list)로 정리한 것으로,
그대로 백엔드 설정값, API 응답 스키마, 혹은 기획 문서의 소스로 활용할 수 있다.
"""

# =========================================================
# 1. 대시보드 전체 구조 (섹션/탭 구성)
# =========================================================

DASHBOARD_LAYOUT = {
    "filters": ["상품선택", "기간선택", "채널(맘큐/스토어)", "세그먼트"],
    "top_section": "이번 달 핵심 인사이트 (AI 자동 생성)",
    "kpi_rows": 3,
    "tabs": [
        "개요",
        "토픽분석",
        "평점별이슈",
        "상품비교",
        "세그먼트",
        "VOC이상탐지",
    ],
    "bottom_section": {
        "title": "팀별 활용 리포트 다운로드",
        "reports": ["상품기획", "마케팅", "CRM", "CS", "경영진"],
    },
}


# =========================================================
# 2. KPI 설계
# =========================================================

KPI_BASIC = [
    {"name": "총 리뷰 수", "desc": "기간 내 전체 리뷰 건수"},
    {"name": "평점 평균", "desc": "5점 만점 평균"},
    {"name": "평점 분포", "desc": "1~5점 비율"},
    {"name": "월별 리뷰 추이", "desc": "시계열 리뷰량"},
    {"name": "상품별 리뷰 수 / 평점", "desc": "상품 랭킹"},
]

KPI_QUALITY = [
    {"name": "텍스트 리뷰 비율", "definition": "10자 이상 서술형 리뷰 / 전체", "use": "리뷰 품질 관리"},
    {"name": "포토 리뷰 비율", "definition": "이미지 첨부 리뷰 / 전체", "use": "마케팅 소재 확보량 파악"},
    {"name": "동영상 리뷰 비율", "definition": "영상 첨부 리뷰 / 전체", "use": "콘텐츠 마케팅 소재 파악"},
    {"name": "리뷰 길이 평균", "definition": "평균 글자수", "use": "관여도 측정"},
    {"name": "상세 리뷰 작성 비율", "definition": "100자 이상 리뷰 / 전체", "use": "고관여 고객 비율"},
]

KPI_SATISFACTION = [
    {"name": "NPS 유사 점수", "formula": "(5점비율 - 1·2점비율) * 100"},
    {"name": "추천 의향 언급률", "formula": "'추천' 등 키워드 언급 리뷰 / 전체"},
    {"name": "재구매 의향 언급률", "formula": "'재구매', '또 살게요' 언급 리뷰 / 전체"},
    {"name": "선물 추천 언급률", "formula": "'선물', '드렸어요' 언급 리뷰 / 전체"},
]

KPI_NEGATIVE_ISSUE = [
    {"name": "배송 관련 불만율", "definition": "배송 토픽 부정 리뷰 / 전체 부정 리뷰"},
    {"name": "품질 관련 불만율", "definition": "품질(내구성·불량) 토픽 부정 비율"},
    {"name": "가격 관련 불만율", "definition": "가격 토픽 부정 비율"},
    {"name": "고객센터 관련 불만율", "definition": "CS 응대 토픽 부정 비율"},
    {"name": "사용성 관련 불만율", "definition": "사용법·편의성 토픽 부정 비율"},
]

KPI_ADDITIONAL_SUGGESTED = [
    {"name": "리뷰 전환율", "definition": "리뷰 작성 수 / 구매 건수", "reason": "리뷰 유도 정책 효과 측정"},
    {"name": "평점 변동 추세 지수", "definition": "최근 4주 vs 이전 4주 평점 변화율", "reason": "조기 경보용"},
    {"name": "이슈 재발률", "definition": "동일 부정 토픽 재등장 빈도", "reason": "근본 개선 여부 확인"},
    {"name": "계절/시즌 민감도 지수", "definition": "특정 시즌 특정 토픽 언급 급증 정도", "reason": "시즌 대응 상품기획"},
    {"name": "사이즈 불만 지수", "definition": "'작아요/커요' 언급 비율", "reason": "사이즈 가이드 개선 판단"},
    {"name": "VOC 처리 후 재언급률", "definition": "CS 답변 후 동일 고객 재문제 제기 여부", "reason": "CS 대응 효과 검증"},
]


# =========================================================
# 3. 시각화 차트 설계
# =========================================================

CHART_DESIGN = [
    {"chart": "월별 리뷰량·평점 추이", "type": "콤보(막대+선)", "purpose": "전체 추세 파악"},
    {"chart": "감정 추이 오버레이", "type": "영역+선 차트", "purpose": "긍정/부정률과 평점의 상관 확인"},
    {"chart": "토픽별 언급량×긍정률", "type": "버블차트(x=언급량, y=긍정률, size=평점)", "purpose": "임팩트 큰 토픽 파악"},
    {"chart": "평점별 이슈 매트릭스", "type": "히트맵(행=평점, 열=이슈)", "purpose": "평점대별 불만 패턴"},
    {"chart": "부정률 급상승 탐지", "type": "시계열 + 이상치 마커", "purpose": "변곡점 자동 표시"},
    {"chart": "상품 비교 레이더", "type": "레이더차트", "purpose": "상품 간 포지셔닝 비교"},
    {"chart": "경쟁력/개선 Top10", "type": "가로 막대(중요도순)", "purpose": "우선순위 직관적 확인"},
    {"chart": "코호트별 만족도", "type": "그룹 막대", "purpose": "고객 생애주기별 비교"},
    {"chart": "VOC 이상징후 알림 타임라인", "type": "이벤트 타임라인", "purpose": "급증 키워드·평점 급락 시점 표시"},
    {"chart": "페르소나 분포", "type": "도넛차트", "purpose": "세그먼트 비중"},
]


# =========================================================
# 4. AI 인사이트 설계 (자동 생성 로직 - 의사코드 형태 함수 시그니처)
# =========================================================

def analyze_topics(reviews: list) -> dict:
    """
    리뷰 토픽 분석
    - 형태소 분석/임베딩 -> 사전 정의 토픽 매핑 또는 BERTopic 등 비지도 클러스터링
    - 사전 토픽 예시: 흡수력, 피부자극, 발진, 두께, 사이즈, 가격, 배송, 향, 포장
    - 반환: {topic: {"mentions": int, "positive_rate": float,
                      "negative_rate": float, "avg_rating": float}}
    """
    raise NotImplementedError


def extract_rating_band_issues(reviews: list) -> dict:
    """
    평점별 주요 이슈 추출
    - 1~2점: 불만 / 3점: 아쉬운 점 / 4점: 개선 요청 / 5점: 만족 포인트
    - 반환: {"1": [...], "2": [...], "3": [...], "4": [...], "5": [...]}
    """
    raise NotImplementedError


def detect_sentiment_inflection_point(monthly_negative_rate: list) -> dict:
    """
    감정 변화 및 변곡점 자동 탐지
    - 이동평균 대비 표준편차 기준(e.g. +1.5 sigma) 이상치 시점을 변곡점으로 판정
    - 출력 예: {"date": "2026-08-W3", "change_pct": 42, "cause_topic": "발진"}
    """
    raise NotImplementedError


def compare_products(product_a_reviews: list, product_b_reviews: list) -> str:
    """
    상품 비교 및 원인 설명 (AI 자연어 생성)
    - 토픽별 긍정률 차이가 가장 큰 상위 3개 토픽을 근거로 설명 문장 생성
    - 출력 예: "A상품은 B상품 대비 '흡수력' 긍정률이 23%p 높고 ..."
    """
    raise NotImplementedError


def detect_voc_anomaly(reviews_stream: list) -> list:
    """
    VOC 이상징후 탐지
    - 키워드 언급량 전주 대비 N% 이상 급증
    - 특정 상품 평점 급락 (예: 4.5 -> 3.8)
    - 부정률 임계치(예: 20%) 초과
    - 반환: [{"type": "keyword_spike", "keyword": "사이즈", "change": "3x", "period_days": 7}, ...]
    """
    raise NotImplementedError


def generate_executive_summary(kpi_delta: dict, top_topics: list, anomalies: list) -> str:
    """
    AI Executive Summary 생성
    - 템플릿: 현재 상태 -> 주요 변화(전월 대비) -> 위험요소 -> 액션 아이템
    - 목표: 1분 내 읽기 가능한 5~7문장 요약
    """
    raise NotImplementedError


# =========================================================
# 5. 실무 활용 시나리오 (팀별)
# =========================================================

TEAM_USE_CASES = {
    "상품기획팀": [
        "고객 요구사항 요약 (예: L사이즈 확대 요청 비율 18%)",
        "부정 토픽 Top3 기반 개선 아이디어 자동 제안",
        "신규 클러스터 토픽 탐지 -> 신규 제품 기회로 제안",
        "언급량 x 부정영향도 매트릭스로 기능 개선 우선순위화",
    ],
    "마케팅팀": [
        "긍정 리뷰 원문 기반 광고 카피 후보 생성",
        "경쟁력 Top10 토픽을 USP 후보로 자동 정리",
        "포토/상세 리뷰 중 긍정 점수 상위 리뷰 자동 큐레이션",
        "재구매·선물 의향 언급 리뷰 분석으로 핵심 구매 이유 도출",
    ],
    "CRM팀": [
        "재구매 의향 언급 리뷰의 공통 토픽 추출",
        "장기 고객 코호트 리뷰 패턴 프로파일링",
        "평점 하락 + 부정 토픽 언급 고객군 식별 -> 이탈 위험 타깃팅",
    ],
    "CS팀": [
        "부정 토픽 빈도 기준 반복 VOC Top10 상시 모니터링",
        "부정 영향도 '매우 높음' 이슈 자동 플래깅 (예: 발진·안전)",
        "전주 대비 언급량 급증 토픽 알림",
    ],
    "경영진": [
        "AI Executive Summary로 현재 상태·위험·액션아이템 1분 파악",
        "상품별 포트폴리오 만족도 비교로 투자/단종 의사결정 지원",
    ],
}


# =========================================================
# 6. 고급 분석 기능 & 고객 페르소나
# =========================================================

ADVANCED_FEATURES = [
    {"feature": "VOC 이상징후 탐지", "desc": "키워드 급증, 평점 급락, 부정률 급상승 자동 알림"},
    {"feature": "리뷰 코호트 분석", "desc": "첫구매/재구매/장기고객 그룹별 만족도 비교"},
    {"feature": "리뷰 기반 고객 페르소나", "desc": "관심사·만족요인·불만요인 기반 자동 세그먼트"},
    {"feature": "AI Executive Summary", "desc": "경영진용 1분 요약 자동 생성"},
]

CUSTOMER_PERSONAS = {
    "민감성 피부형": {
        "관심사": ["피부자극", "성분"],
        "만족요인": ["트러블 없음"],
        "불만요인": ["발진"],
    },
    "가성비 추구형": {
        "관심사": ["가격", "용량"],
        "만족요인": ["가격 대비 만족"],
        "불만요인": ["양 적음"],
    },
    "선물 구매형": {
        "관심사": ["포장", "향"],
        "만족요인": ["패키지 고급스러움"],
        "불만요인": ["배송 지연"],
    },
}


# =========================================================
# 다음 단계 제안
# =========================================================

NEXT_STEPS = [
    "토픽 사전(흡수력, 발진, 사이즈 등) 1차 정의 및 형태소 분석기 연동",
    "평점 구간별 이슈 추출 로직 프로토타입 (1주)",
    "AI 인사이트 요약 프롬프트 설계 및 검증 (2주)",
    "대시보드 UI 와이어프레임 -> 실제 디자인 목업 전환",
]


if __name__ == "__main__":
    import json

    design = {
        "layout": DASHBOARD_LAYOUT,
        "kpi": {
            "basic": KPI_BASIC,
            "quality": KPI_QUALITY,
            "satisfaction": KPI_SATISFACTION,
            "negative_issue": KPI_NEGATIVE_ISSUE,
            "additional_suggested": KPI_ADDITIONAL_SUGGESTED,
        },
        "charts": CHART_DESIGN,
        "team_use_cases": TEAM_USE_CASES,
        "advanced_features": ADVANCED_FEATURES,
        "customer_personas": CUSTOMER_PERSONAS,
        "next_steps": NEXT_STEPS,
    }
    print(json.dumps(design, ensure_ascii=False, indent=2))
