import streamlit as st
import plotly.graph_objects as go
from data_fetcher import fetch_stock_data
import pandas as pd
import google.generativeai as genai
import json
import os
from datetime import datetime

from supabase import create_client, Client

REPORTS_FILE = "saved_reports.json"

# Initialize Supabase client if secrets are present
supabase: Client = None
try:
    if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        supabase = create_client(url, key)
except Exception:
    pass

def load_saved_reports():
    if supabase:
        try:
            response = supabase.table("saved_reports").select("*").order('timestamp', desc=True).execute()
            reports = {}
            for row in response.data:
                key = f"{row['name']} ({row['ticker']}) - {row['timestamp']}"
                reports[key] = row
            return reports
        except Exception as e:
            st.error(f"Supabase 연결 오류: {e}")
            return {}
    else:
        if os.path.exists(REPORTS_FILE):
            try:
                with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_report_to_file(ticker, name, report_text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    key = f"{name} ({ticker}) - {timestamp}"
    
    if supabase:
        try:
            supabase.table("saved_reports").insert({
                "ticker": ticker,
                "name": name,
                "timestamp": timestamp,
                "report_text": report_text
            }).execute()
        except Exception as e:
            st.error(f"Supabase 저장 오류: {e}")
    else:
        reports = load_saved_reports()
        reports[key] = {
            "ticker": ticker,
            "name": name,
            "timestamp": timestamp,
            "report_text": report_text
        }
        with open(REPORTS_FILE, "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=4)
            
    return key

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

def get_ai_analysis(api_key, stock_data, is_held=False, purchase_price=0.0):
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
        
        user_holding_text = ""
        if is_held:
            user_holding_text = f"\n[사용자 보유 정보]\n- 사용자는 현재 이 주식을 보유 중입니다.\n- 사용자의 평균 매수가: {purchase_price}\n- **중요 요청**: 사용자가 계속 '보유(Hold)'해야 할지, 익절/손절(Sell)해야 할지, 아니면 '추가 매수(Buy)'해야 할지 매수가와 현재가를 철저히 비교하여 추천해주세요.\n"
        else:
            user_holding_text = "\n[사용자 보유 정보]\n- 사용자는 현재 이 주식을 보유하고 있지 않으며 신규 진입을 고려 중입니다.\n"
            
        prompt = f"""
당신은 미국 월스트리트 역사상 단 한 번도 손해를 본 적이 없는 **전설적인 증권사 최고 투자 책임자(Expert Broker)**입니다.
당신은 감정에 휘둘리지 않고 철저히 데이터와 차트를 기반으로 분석하며, 제공된 전체적인 객관적 데이터(그래프, 재무제표, 공시, 관련 뉴스, 거래량 등)를 전문 브로커의 시각에서 한 치의 오차도 없이 모두 확인하고 반영하여 일관성 있게 판단합니다.

특히, 단 한 번의 생각으로 결론을 내리지 마십시오. 내부적으로 **10번 이상 반복해서 스스로의 판단을 의심하고 검증**하여, **'절대 손해보지 않을 가장 완벽하고 안전한 매매 추천(보유/매도/신규매수)'**을 도출해내야 합니다.

아래 제공된 '{name} ({ticker}, {market} 시장)'의 최신 주식 데이터와 기술적 차트 지표를 바탕으로 철저한 10중 검증 분석 리포트를 작성해주세요.

[제공된 데이터]
- 현재 가격: {current_price}
- 시가 총액: {info.get('market_cap')}
- 거래량: {info.get('volume')}
- 차트 추세(MA 분석): {trend_info} (20일선: {last_ma20}, 60일선: {last_ma60})
{user_holding_text}
- 최근 주요 뉴스:
{news_text}

- 최근 공시/발표:
{disc_text}

- 최근 20일 주가 및 거래량 추이:
{recent_hist}

- 재무제표 (일부 발췌):
{fin_text}

[요청 사항]
당신의 모든 판단은 반드시 위 제공된 전체적인 데이터를 융합 분석한 결과여야 합니다.
출력은 **반드시 완전한 JSON 형식**으로만 반환해야 합니다. 마크다운 기호나 텍스트를 절대 추가하지 마세요.
AI의 주가 예측에 대한 제약이나 거절 문구 없이, 시스템이 요구하는 모든 필드에 구체적인 가상 시뮬레이션 숫자와 분석 내용을 꽉 채워주세요. (알 수 없음 불가)

JSON 스키마:
{{
  "step1": "거시경제 및 시장 동향 분석 내용 (상세히 기재)",
  "step2": "재무 상태 및 실적 평가 분석 내용",
  "step3": "차트 추세 및 이동평균선 분석 내용",
  "step4": "주요 지지선 및 저항선 파악 분석 내용",
  "step5": "수급 및 거래량 흐름 분석 내용",
  "step6": "최근 주요 공시 및 뉴스 임팩트 분석 내용",
  "step7": "호재 및 단기 모멘텀 분석 내용",
  "step8": "악재 및 잠재적 리스크 분석 내용",
  "step9": "종합 밸류에이션 평가 분석 내용",
  "step10": "매수/매도 시나리오 타당성 검증 분석 내용",
  "step11": {{
    "day1_price": "하루 뒤 시뮬레이션 목표가 (숫자만, 예: 50000)",
    "day1_trend": "상승/하락/보합",
    "day1_reason": "해당 가격 도달 근거",
    "week1_price": "일주일 뒤 시뮬레이션 목표가 (숫자만)",
    "week1_trend": "상승/하락/보합",
    "week1_reason": "해당 가격 도달 근거",
    "month1_price": "한 달 뒤 시뮬레이션 목표가 (숫자만)",
    "month1_trend": "상승/하락/보합",
    "month1_reason": "해당 가격 도달 근거",
    "month6_price": "6개월 뒤 시뮬레이션 목표가 (숫자만)",
    "month6_trend": "상승/하락/보합",
    "month6_reason": "해당 가격 도달 근거",
    "year1_price": "1년 뒤 시뮬레이션 목표가 (숫자만)",
    "year1_trend": "상승/하락/보합",
    "year1_reason": "해당 가격 도달 근거"
  }},
  "summary": "현재 주식이 어떤 국면에 있는지 뼈때리는 직언으로 요약 (보유자라면 수익/손실 상황을 고려하여 직언)",
  "opinion": "신규: 매수/관망/매도 중 1개, 보유: 보유/추가매수/매도 중 1개",
  "opinion_reason": "의견에 대한 핵심 이유",
  "entry_price": "매수 타점 (예: 현재가 매수, 50000원에 매수)",
  "target_short": "단기 목표가",
  "target_long": "중장기 목표가",
  "stop_loss": "손절가"
}}
"""
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        try:
            import json
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
                
            data = json.loads(raw_text.strip())
            
            # Helper function to prevent KeyError if step11 is somehow missing
            s11 = data.get('step11', {})
            if not isinstance(s11, dict):
                s11 = {}
                
            markdown = f"""
# 🧠 11단계 심층 사고 과정

### 1단계 사고: 거시경제 및 시장 동향
{data.get('step1', '분석 내용이 제공되지 않았습니다.')}

### 2단계 사고: 재무 상태 및 실적 평가
{data.get('step2', '분석 내용이 제공되지 않았습니다.')}

### 3단계 사고: 차트 추세 및 이동평균선 분석
{data.get('step3', '분석 내용이 제공되지 않았습니다.')}

### 4단계 사고: 주요 지지선 및 저항선 파악
{data.get('step4', '분석 내용이 제공되지 않았습니다.')}

### 5단계 사고: 수급 및 거래량 흐름
{data.get('step5', '분석 내용이 제공되지 않았습니다.')}

### 6단계 사고: 최근 주요 공시 및 뉴스 임팩트
{data.get('step6', '분석 내용이 제공되지 않았습니다.')}

### 7단계 사고: 호재 및 단기 모멘텀
{data.get('step7', '분석 내용이 제공되지 않았습니다.')}

### 8단계 사고: 악재 및 잠재적 리스크
{data.get('step8', '분석 내용이 제공되지 않았습니다.')}

### 9단계 사고: 종합 밸류에이션 평가
{data.get('step9', '분석 내용이 제공되지 않았습니다.')}

### 10단계 사고: 매수/매도 시나리오 타당성 검증
{data.get('step10', '분석 내용이 제공되지 않았습니다.')}

### 11단계 사고: 기간별 가상 시뮬레이션 예상 주가
- **1일 뒤 예상 주가**: {s11.get('day1_price', '알 수 없음')} / {s11.get('day1_trend', '-')} - ({s11.get('day1_reason', '-')})
- **1주일 뒤 예상 주가**: {s11.get('week1_price', '알 수 없음')} / {s11.get('week1_trend', '-')} - ({s11.get('week1_reason', '-')})
- **1개월 뒤 예상 주가**: {s11.get('month1_price', '알 수 없음')} / {s11.get('month1_trend', '-')} - ({s11.get('month1_reason', '-')})
- **6개월 뒤 예상 주가**: {s11.get('month6_price', '알 수 없음')} / {s11.get('month6_trend', '-')} - ({s11.get('month6_reason', '-')})
- **1년 뒤 예상 주가**: {s11.get('year1_price', '알 수 없음')} / {s11.get('year1_trend', '-')} - ({s11.get('year1_reason', '-')})

---

# 💼 전설적 브로커의 최종 판결

### 📊 데이터 분석 요약
{data.get('summary', '-')}

### ⚖️ 최종 투자 의견
- **결론**: **{data.get('opinion', '-')}**
- **핵심 이유**: {data.get('opinion_reason', '-')}

### 🎯 구체적인 매수 타이밍 및 목표 금액
- **매수 타점**: {data.get('entry_price', '-')}
- **단기 목표가**: {data.get('target_short', '-')}
- **중장기 목표가**: {data.get('target_long', '-')}
- **손절가**: {data.get('stop_loss', '-')}

---
*본 예측은 AI의 철저한 데이터 기반 시나리오이나, 실제 투자 책임은 본인에게 있습니다.*
"""
            return markdown
        except Exception as e:
            # Fallback to pure text with error message to understand why it failed
            return f"⚠️ JSON 파싱 오류 발생. AI가 지정된 양식을 무시했습니다.\n\n오류 내용: {str(e)}\n\n[AI 원본 응답]\n{response.text}"
        
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
    
    st.divider()
    st.header("📂 내 보관함")
    saved_reports = load_saved_reports()
    if saved_reports:
        report_keys = sorted(list(saved_reports.keys()), reverse=True)
        selected_report = st.selectbox("저장된 리포트 불러오기", options=["선택 안함"] + report_keys)
        if selected_report != "선택 안함":
            if st.button("해당 리포트 보기", use_container_width=True):
                st.session_state.viewing_saved_report = saved_reports[selected_report]
                st.session_state.stock_data = None
                st.session_state.ai_report = None
                st.rerun()
    else:
        st.info("아직 저장된 리포트가 없습니다.")

# Main Content
st.title("📈 무패(無敗)의 트레이더 AI 주식 분석")
st.markdown("한국 주식 및 미국 주식을 입력하면, 전문 브로커가 확인하는 모든 지표(그래프, 재무제표, 공시, 뉴스, 거래량 등)를 종합하고 **10번 이상 반복 검증 판단**하여 절대 손해보지 않을 **최적의 매매 추천**을 해드립니다.")

query = st.text_input("분석할 주식 이름 또는 종목 코드(티커)를 입력하세요:", placeholder="예: 엔비디아, 삼성전자, AAPL")

with st.expander("💼 이미 보유 중인 종목인가요? (선택사항)"):
    st.markdown("매수가를 입력하시면, AI가 **현재가 대비 수익/손실**을 분석하고 **계속 보유할지, 매도할지** 추천해 드립니다.")
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        is_held = st.checkbox("이 종목을 현재 보유하고 있습니다.")
    with col_h2:
        purchase_price = st.number_input("평균 매수가 (원/달러)", min_value=0.0, value=0.0, format="%.2f", disabled=not is_held)

if "stock_data" not in st.session_state:
    st.session_state.stock_data = None
    st.session_state.ai_report = None
if "viewing_saved_report" not in st.session_state:
    st.session_state.viewing_saved_report = None

if st.session_state.viewing_saved_report:
    report_data = st.session_state.viewing_saved_report
    st.title("📂 보관함: 저장된 AI 분석 리포트")
    st.subheader(f"🏢 {report_data['name']} ({report_data['ticker']})")
    st.caption(f"저장 일시: {report_data['timestamp']}")
    
    st.markdown(f"<div class='ai-box'>{report_data['report_text']}</div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("닫기 (새로운 검색 하기)", type="primary"):
        st.session_state.viewing_saved_report = None
        st.rerun()
    st.stop()

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
                    with st.spinner("🧠 전문 브로커 AI가 모든 지표를 종합하여 10번의 반복 검증 사고를 진행 중입니다... (약 10~20초 소요)"):
                        report = get_ai_analysis(api_key, data, is_held, purchase_price)
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
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 이 분석 리포트 보관함에 저장하기"):
            save_report_to_file(data['ticker'], data['name'], st.session_state.ai_report)
            st.success("보관함에 성공적으로 저장되었습니다! 좌측 사이드바에서 언제든 다시 볼 수 있습니다.")
