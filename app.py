import streamlit as st
import plotly.graph_objects as go
from data_fetcher import fetch_stock_data
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Legendary Wall Street Broker AI", page_icon="📈", layout="wide")

# Custom CSS for Premium Dark Theme
st.markdown("""
<style>
    /* Global styles */
    .reportview-container {
        background: #0e1117;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #e0e0e0 !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards for metrics */
    div[data-testid="metric-container"] {
        background-color: #1e2129;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #00C6ff 0%, #0072ff 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 114, 255, 0.4);
    }
    
    /* AI Analysis Box */
    .ai-box {
        background-color: #1a1c23;
        border-left: 5px solid #00c6ff;
        padding: 25px;
        border-radius: 0 10px 10px 0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        color: #d1d5db;
        font-size: 1.05rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

def get_ai_analysis(api_key, stock_data):
    if not api_key:
        return "⚠️ API 키가 제공되지 않았습니다. 좌측 사이드바에 Gemini API 키를 입력해주세요."
        
    try:
        genai.configure(api_key=api_key)
        
        valid_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                valid_models.append(m.name)
                
        if not valid_models:
            return "❌ 사용 가능한 Gemini 모델이 없습니다. API 키 상태를 확인해주세요."
            
        model_name = valid_models[0] 
        for pref in ['models/gemini-1.5-pro-latest', 'models/gemini-1.5-pro', 'models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash']:
            if pref in valid_models:
                model_name = pref
                break
                
        # Pro model is highly recommended for reasoning
        model = genai.GenerativeModel(model_name)
        
        info = stock_data['info']
        market = stock_data['market']
        name = stock_data['name']
        ticker = stock_data['ticker']
        
        hist_df = stock_data['history']
        trend_info = "알수없음"
        last_ma20 = "N/A"
        last_ma60 = "N/A"
        
        if not hist_df.empty:
            # 6개월치 월/주별 압축 데이터 대신 최근 30일 데이터와 추세 지표 제공
            recent_hist = hist_df.tail(20).to_markdown()
            trend_info = getattr(hist_df, 'attrs', {}).get('trend', '알수없음')
            last_ma20 = getattr(hist_df, 'attrs', {}).get('last_ma20', 'N/A')
            last_ma60 = getattr(hist_df, 'attrs', {}).get('last_ma60', 'N/A')
            if last_ma20 != 'N/A': last_ma20 = f"{last_ma20:,.2f}"
            if last_ma60 != 'N/A': last_ma60 = f"{last_ma60:,.2f}"
        else:
            recent_hist = "최근 주가 데이터가 없습니다."
            
        news_text = "\n".join([f"- {n}" for n in info.get('news', [])])
        disc_text = "\n".join([f"- {d}" for n, d in enumerate(info.get('disclosures', []))])
        
        fin_df = info.get('financials')
        if fin_df is not None:
            fin_text = fin_df.to_markdown()
        else:
            fin_text = "재무제표 정보가 없습니다."
            
        current_price = info.get('current_price', '알수없음')
        
        prompt = f"""
당신은 미국 월스트리트 역사상 단 한 번도 손해를 본 적이 없는 **전설적인 증권사 최고 투자 책임자(Expert Broker)**입니다.
당신은 피도 눈물도 없는 냉철한 이성을 가졌으며, 감정에 휘둘리지 않고 철저히 데이터와 차트를 기반으로 분석합니다.
투자자에게 막대한 부를 안겨주기 위해, 결론을 내기 전 반드시 내부적으로 10번 이상 심층 분석을 거쳐 확신이 설 때만 '매수'를 외칩니다.

아래 제공된 '{name} ({ticker}, {market} 시장)'의 최신 주식 데이터와 기술적 차트 지표를 바탕으로 분석 리포트를 작성해주세요.

[제공된 데이터]
- 현재 가격: {current_price}
- 시가 총액: {info.get('market_cap')}
- 거래량: {info.get('volume')}
- 차트 추세(MA 분석): {trend_info} (20일선: {last_ma20}, 60일선: {last_ma60})

- 최근 주요 뉴스:
{news_text}

- 최근 공시/발표:
{disc_text}

- 최근 20일 주가 및 거래량 추이:
{recent_hist}

- 재무제표 (일부 발췌):
{fin_text}

[요청 사항]
당신은 이 데이터를 보고 즉시 대답하지 않습니다. 반드시 <thinking> 태그를 사용하여 10단계의 내부 심층 사고 과정(거시경제, 재무상태, 차트의 흐름, 지지/저항선, 수급, 악재/호재 평가, 매수/매도 리스크 등)을 적나라하게 보여준 후, 최종 결론을 도출하세요.

최종 결론에는 **아래 3가지 항목을 반드시 빠짐없이** 포함해야 합니다.

<thinking>
1. [1단계 사고] ...
2. [2단계 사고] ...
...
10. [10단계 사고] ...
</thinking>

# 💼 전설적 브로커의 최종 판결

1. **📊 전체적인 차트 및 현재 상황 판단**: 제공된 MA(이동평균선) 추세와 최근 주가 흐름, 뉴스를 종합하여 현재 이 주식이 어떤 국면에 있는지 뼈때리는 직언으로 요약하세요.
2. **⚖️ 최종 투자 의견 (매수 / 관망 / 매도)**: 셋 중 하나를 명확히 제시하세요.
3. **🎯 구체적인 매수 타이밍 및 목표 금액 (가장 중요!)**: 
   - 만약 '매수' 의견이라면: "현재가({current_price})에 즉시 매수하라" 거나 "차트상 눌림목인 OOOO원에 도달했을 때 비중 OO%로 매수하라" 와 같이 **정확한 매수 타이밍과 매수 금액(단가)**을 콕 집어주세요. 
   - 또한 단기/중장기 목표가와 손절가도 숫자로 명시하세요. 
   - 만약 '관망'이나 '매도'라면: "이 가격엔 절대 살 수 없다. OOOO원까지 떨어지면 그때 다시 보겠다" 식으로 구체적 기준 가격을 제시하세요.

(한국어로 작성하고, 가독성 좋은 마크다운 포맷을 사용해주세요. 경고 문구로 "본 예측은 AI의 가상 시나리오이며, 실제 투자 책임은 본인에게 있습니다."를 마지막에 작게 포함해주세요.)
"""
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"❌ AI 분석 중 오류가 발생했습니다: {str(e)}"

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/bullish.png", width=80)
    st.title("월가 전설의 브로커 AI")
    st.markdown("단 한 번도 손실을 내지 않은 AI의 날카로운 분석")
    
    st.divider()
    
    st.header("🔑 설정")
    api_key = st.text_input("Gemini API Key를 입력하세요", type="password")
    
    st.markdown("""
    **API 키 발급 방법:**
    1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
    2. 'Create API Key' 클릭
    """)
    st.divider()
    
    st.markdown("""
    ### 🌐 클라우드 배포 모드 가동 중
    이 앱은 **Streamlit Community Cloud**를 통해 24시간 언제 어디서나 모바일로 접속할 수 있도록 설계되었습니다. PC를 꺼도 작동합니다!
    """)
    
    st.divider()
    st.write("📌 **검색 예시**")
    st.write("- 한국주식: 삼성전자, 005930, 카카오")
    st.write("- 미국주식: AAPL, 테슬라, 엔비디아")

# Main Content
st.title("📈 무패(無敗)의 트레이더 AI 주식 분석")
st.markdown("한국 주식(이름/종목코드) 및 미국 주식(티커/이름)을 입력하면, **10번의 심층 사고** 후 가장 완벽한 **매수 타이밍과 가격**을 알려드립니다.")

query = st.text_input("분석할 주식 이름 또는 종목 코드(티커)를 입력하세요:", placeholder="예: 엔비디아, 삼성전자, AAPL")

if "stock_data" not in st.session_state:
    st.session_state.stock_data = None
    st.session_state.ai_report = None

col1, col2 = st.columns([1, 5])
with col1:
    search_btn = st.button("🔥 분석 시작", use_container_width=True)

if search_btn:
    if not query:
        st.warning("종목을 입력해주세요.")
    else:
        with st.spinner(f"'{query}' 데이터를 월스트리트 터미널에서 긁어오는 중..."):
            import importlib
            import data_fetcher
            importlib.reload(data_fetcher)
            data = data_fetcher.fetch_stock_data(query)
            if "error" in data:
                st.error(data["error"])
                import sys
                st.write(f"System encoding: {sys.getdefaultencoding()}")
            if "error" in data:
                st.error(data["error"])
                st.session_state.stock_data = None
                st.session_state.ai_report = None
            else:
                st.session_state.stock_data = data
                st.success("데이터 확보 완료. AI 브로커가 차트를 분석합니다...")
                
                if api_key:
                    with st.spinner("🧠 전설의 브로커가 10단계 심층 사고를 진행 중입니다... (약 10~20초 소요)"):
                        report = get_ai_analysis(api_key, data)
                        st.session_state.ai_report = report
                else:
                    st.session_state.ai_report = "⚠️ AI 분석을 위해 좌측 사이드바에 Gemini API 키를 입력해주세요."

# Display Results
if st.session_state.stock_data:
    data = st.session_state.stock_data
    info = data['info']
    
    st.divider()
    st.subheader(f"🏢 {data['name']} ({data['ticker']} - {data['market']})")
    
    # Metrics
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("현재가", info.get('current_price', 'N/A'))
    mcol2.metric("시가총액", info.get('market_cap', 'N/A'))
    mcol3.metric("거래량", info.get('volume', 'N/A'))
    trend = getattr(data['history'], 'attrs', {}).get('trend', '분석 불가')
    mcol4.metric("차트 추세", trend)
    
    # Chart
    hist_df = data['history']
    if not hist_df.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 최근 2년 주가 추이 및 이동평균선")
        fig = go.Figure()
        
        # Close Price
        close_col = 'Close'
        if isinstance(hist_df.columns, pd.MultiIndex):
            # For multi-index (yf new version)
            close_col = ('Close', data['ticker']) if ('Close', data['ticker']) in hist_df.columns else hist_df.columns[0]
            
        y_data = hist_df[close_col] if close_col in hist_df else hist_df.iloc[:, 0]
        fig.add_trace(go.Scatter(x=hist_df.index, y=y_data, mode='lines', name='종가 (Close)', line=dict(color='#00c6ff', width=2)))
        
        # MA20
        if 'MA20' in hist_df.columns:
            fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA20'], mode='lines', name='20일선', line=dict(color='#ff9900', width=1, dash='dot')))
        # MA60
        if 'MA60' in hist_df.columns:
            fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA60'], mode='lines', name='60일선', line=dict(color='#ff0055', width=1, dash='dash')))
            
        fig.update_layout(
            plot_bgcolor='#1e2129',
            paper_bgcolor='#0e1117',
            font=dict(color='#e0e0e0'),
            xaxis=dict(showgrid=True, gridcolor='#333'),
            yaxis=dict(showgrid=True, gridcolor='#333'),
            margin=dict(l=0, r=0, t=30, b=0),
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # AI Report
    if st.session_state.ai_report:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("💡 브로커의 심층 분석 리포트")
        st.markdown(f"<div class='ai-box'>{st.session_state.ai_report}</div>", unsafe_allow_html=True)
