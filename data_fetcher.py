
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime, timedelta
import numpy as np

US_STOCK_KO_MAPPING = {
    "애플": "AAPL", "테슬라": "TSLA", "알파벳": "GOOGL", "알파벳A": "GOOGL", 
    "알파벳C": "GOOG", "구글": "GOOGL", "엔비디아": "NVDA", "마이크로소프트": "MSFT", 
    "아마존": "AMZN", "메타": "META", "페이스북": "META", "넷플릭스": "NFLX", 
    "에이엠디": "AMD", "인텔": "INTC", "퀄컴": "QCOM", "브로드컴": "AVGO", 
    "티에스엠씨": "TSM", "TSMC": "TSM", "제이피모건": "JPM", "존슨앤드존슨": "JNJ", 
    "버크셔해서웨이": "BRK-B", "버크셔": "BRK-B", "일라이릴리": "LLY", "비자": "V", 
    "마스터카드": "MA", "엑슨모빌": "XOM", "월마트": "WMT", "유나이티드헬스": "UNH", 
    "코스트코": "COST", "프록터앤갬블": "PG", "홈디포": "HD", "디즈니": "DIS", 
    "코카콜라": "KO", "펩시": "PEP", "맥도날드": "MCD", "스타벅스": "SBUX", 
    "나이키": "NKE", "보잉": "BA", "팔란티어": "PLTR", "아이비엠": "IBM", 
    "오라클": "ORCL", "어도비": "ADBE", "시스코": "CSCO", "우버": "UBER", 
    "에어비앤비": "ABNB", "쇼피파이": "SHOP", "로블록스": "RBLX", "니콜라": "NKLA", 
    "루시드": "LCID", "리비안": "RIVN", "니오": "NIO", "쿠팡": "CPNG", 
    "스퀘어": "SQ", "블록": "SQ", "페이팔": "PYPL", "줌": "ZM", "인튜이트": "INTU", 
    "암": "ARM", "슈퍼마이크로": "SMCI", "슈퍼마이크로컴퓨터": "SMCI", "델": "DELL"
}

def is_korean(text):
    return bool(re.search('[가-힣]', text))

def is_numeric(text):
    return text.isdigit()

_krx_df = None

def get_krx_ticker(name_or_code):
    global _krx_df
    if is_numeric(name_or_code):
        return name_or_code.zfill(6), name_or_code
    
    # 유명한 국내 주식들의 한글-영문 사명 매핑 (KRX 공식 등록명 기준)
    KR_STOCK_KO_MAPPING = {
        "네이버": "NAVER",
        "에쓰오일": "S-Oil",
        "기아차": "기아",
        "현대차": "현대자동차",
        "포스코": "POSCO홀딩스",
        "포스코홀딩스": "POSCO홀딩스",
        "케이티": "KT",
        "에스케이": "SK",
        "엘지": "LG",
        "씨제이": "CJ",
    }
    
    name_clean = name_or_code.strip()
    search_name = KR_STOCK_KO_MAPPING.get(name_clean, name_clean)
    
    import pandas as pd
    import os
    try:
        if _krx_df is None:
            csv_path = os.path.join(os.path.dirname(__file__), 'krx_tickers.csv')
            if os.path.exists(csv_path):
                _krx_df = pd.read_csv(csv_path, dtype={'Code': str}, encoding='utf-8-sig')
                _krx_df.columns = _krx_df.columns.str.strip()
            else:
                import FinanceDataReader as fdr
                _krx_df = fdr.StockListing('KRX')
                if _krx_df is not None and not _krx_df.empty:
                    _krx_df.columns = _krx_df.columns.str.strip()
                
        df = _krx_df
        
        name_col = 'Name' if 'Name' in df.columns else (df.columns[0] if len(df.columns) > 0 else None)
        code_col = 'Code' if 'Code' in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
        
        if name_col and code_col:
            # Remove all spaces from the query and the CSV name for comparison
            query_clean = search_name.replace(" ", "").strip()
            df_names_clean = df[name_col].astype(str).str.replace(" ", "").str.strip()
            
            # Exact match (ignoring spaces)
            result = df[df_names_clean == query_clean]
            if not result.empty:
                return result.iloc[0][code_col], result.iloc[0][name_col]
            
            # Contains match (ignoring spaces)
            result = df[df_names_clean.str.contains(query_clean, case=False, na=False)]
            if not result.empty:
                return result.iloc[0][code_col], result.iloc[0][name_col]
                
            # If not found in CSV, try fetching real-time KRX listing as a fallback
            try:
                import FinanceDataReader as fdr
                realtime_df = fdr.StockListing('KRX')
                if realtime_df is not None and not realtime_df.empty:
                    realtime_df.columns = realtime_df.columns.str.strip()
                    rt_name_col = 'Name' if 'Name' in realtime_df.columns else realtime_df.columns[0]
                    rt_code_col = 'Code' if 'Code' in realtime_df.columns else realtime_df.columns[1]
                    
                    rt_names_clean = realtime_df[rt_name_col].astype(str).str.replace(" ", "").str.strip()
                    
                    # Exact match
                    result = realtime_df[rt_names_clean == query_clean]
                    if not result.empty:
                        return result.iloc[0][rt_code_col], result.iloc[0][rt_name_col]
                        
                    # Contains match
                    result = realtime_df[rt_names_clean.str.contains(query_clean, case=False, na=False)]
                    if not result.empty:
                        return result.iloc[0][rt_code_col], result.iloc[0][rt_name_col]
            except Exception as fdr_err:
                print(f"FinanceDataReader StockListing fallback failed: {fdr_err}")
            
    except Exception as e:
        print(f"KRX 종목 목록을 가져오는 중 오류 발생: {e}")
        pass
        
    return None, name_or_code

def fetch_naver_finance(ticker):
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    data = {}
    soup = None
    html_text = ""
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'euc-kr'
        html_text = res.text
        soup = BeautifulSoup(html_text, 'html.parser')
    except Exception as e:
        print(f"네이버 금융 요청 중 오류 발생: {e}")
        pass
    
    try:
        price_tag = soup.select_one('.no_today .blind') if soup else None
        if price_tag:
            data['current_price'] = price_tag.text.strip()
        else:
            data['current_price'] = "N/A"
    except:
        data['current_price'] = "N/A"
        
    try:
        mcap = soup.select_one('#_market_sum') if soup else None
        if mcap:
            data['market_cap'] = ' '.join(mcap.text.split()) + "억원"
        else:
            data['market_cap'] = "N/A"
    except:
        data['market_cap'] = "N/A"
        
    try:
        vol_tag = soup.select_one('.no_info span.blind') if soup else None
        if vol_tag:
            data['volume'] = "최근 데이터 참조"
        else:
            data['volume'] = "N/A"
    except:
        data['volume'] = "N/A"
        
    news_list = []
    try:
        if soup:
            news_tags = soup.select('.news_section ul li a')
            for tag in news_tags[:10]:
                title = tag.get('title') or tag.text
                if title: news_list.append(title.strip())
    except:
        pass
    data['news'] = list(dict.fromkeys(news_list))
    
    disc_list = []
    try:
        if not soup:
            disc_list.append("공시 정보를 파싱할 수 없습니다.")
        else:
            disc_tags = soup.select('.sub_section.news_section_2 ul li a')
            if not disc_tags:
                disc_list.append("최신 공시는 위 '최근 뉴스' 목록에 통합되어 표시됩니다.")
            else:
                for tag in disc_tags[:5]:
                    title = tag.get('title') or tag.text
                    if title: disc_list.append(title.strip())
    except:
        disc_list.append("공시 정보를 파싱할 수 없습니다.")
    data['disclosures'] = list(dict.fromkeys(disc_list))
    
    try:
        if html_text:
            # Pass the already fetched HTML text directly to prevent extra rate-limited HTTP requests
            dfs = pd.read_html(html_text, encoding='euc-kr')
        else:
            dfs = []
            
        fin_df = None
        for df in dfs:
            cols = " ".join([str(c) for c in df.columns])
            if '매출액' in cols or '영업이익' in cols:
                fin_df = df
                break
        if fin_df is None and len(dfs) > 4:
            fin_df = dfs[4]
            
        if fin_df is not None:
            if isinstance(fin_df.columns, pd.MultiIndex):
                fin_df.columns = ['_'.join(str(c) for c in col).strip() for col in fin_df.columns.values]
            fin_df = fin_df.astype(str)
            data['financials'] = fin_df.head(10)
        else:
            data['financials'] = None
    except Exception as e:
        print(f"네이버 금융 재무제표 파싱 중 오류 발생: {e}")
        data['financials'] = None
        
    return data

def fetch_yfinance_data(ticker_symbol):
    import yfinance as yf
    data = {
        'current_price': 'N/A',
        'market_cap': 'N/A',
        'volume': 'N/A',
        'news': [],
        'disclosures': ["야후 파이낸스는 개별 공시를 별도로 제공하지 않습니다. 주요 뉴스를 참고하세요."],
        'financials': None
    }
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        try:
            info = ticker.info
            if info:
                data['current_price'] = str(info.get('currentPrice', info.get('regularMarketPrice', 'N/A')))
                data['market_cap'] = str(info.get('marketCap', 'N/A'))
                data['volume'] = str(info.get('volume', 'N/A'))
        except Exception as info_err:
            print(f"yfinance info fetch failed: {info_err}")
            
        try:
            news_list = []
            if ticker.news:
                for news in ticker.news[:5]:
                    news_list.append(news.get('title', ''))
            data['news'] = news_list
        except Exception as news_err:
            print(f"yfinance news fetch failed: {news_err}")
            
        try:
            fin = ticker.financials
            if fin is not None and not fin.empty:
                fin = fin.astype(str)
                data['financials'] = fin.head(10)
        except Exception as fin_err:
            print(f"yfinance financials fetch failed: {fin_err}")
            
    except Exception as e:
        print(f"yfinance ticker initialization failed: {e}")
        
    return data

def calculate_technical_indicators(df):
    """AI가 차트 분석을 쉽게 할 수 있도록 이동평균선(MA)과 RSI를 계산합니다."""
    if df is None or df.empty:
        return df
        
    try:
        # 단일 인덱스/멀티 인덱스 처리
        close_series = df['Close']
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]
            
        df_new = df.copy()
        
        # 이동평균선 계산
        df_new['MA20'] = close_series.rolling(window=20).mean()
        df_new['MA60'] = close_series.rolling(window=60).mean()
        df_new['MA120'] = close_series.rolling(window=120).mean()
        
        # 현재 추세 텍스트 생성 (AI에게 전달용)
        last_close = close_series.iloc[-1]
        last_ma20 = df_new['MA20'].iloc[-1]
        last_ma60 = df_new['MA60'].iloc[-1]
        
        trend = "알수없음"
        if pd.notna(last_ma20) and pd.notna(last_ma60):
            if last_close > last_ma20 and last_ma20 > last_ma60:
                trend = "정배열(상승장)"
            elif last_close < last_ma20 and last_ma20 < last_ma60:
                trend = "역배열(하락장)"
            else:
                trend = "혼조세(박스권 또는 전환기)"
                
        df_new.attrs['trend'] = trend
        df_new.attrs['last_ma20'] = last_ma20
        df_new.attrs['last_ma60'] = last_ma60
        
        return df_new
    except Exception as e:
        print(f"지표 계산 오류: {e}")
        return df

def fetch_stock_data(query):
    query = query.strip()
    
    if query in US_STOCK_KO_MAPPING:
        market = 'US'
        ticker = US_STOCK_KO_MAPPING[query]
        name = query
    else:
        # First, try to see if it exists in the KRX (Korean) stock list (handles '네이버', 'NAVER', '035420')
        krx_code, krx_name = get_krx_ticker(query)
        if krx_code:
            market = 'KR'
            ticker = krx_code
            name = krx_name
        else:
            # If not in Korean stock list, check if it contains Korean characters. If it does, we can't find it.
            if is_korean(query):
                return {"error": f"주식 종목을 찾을 수 없습니다: {query}"}
            # Otherwise, treat as US stock ticker
            market = 'US'
            ticker = query.upper()
            name = ticker
    
    try:
        # AI가 "전체적인 차트"를 보기 위해 2년치 데이터 요청
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        if market == 'KR':
            info_data = fetch_naver_finance(ticker)
            
            # Try fetching from yfinance first (highly robust, but handles rate limits gracefully)
            hist_df = pd.DataFrame()
            try:
                import yfinance as yf
                hist_df = yf.download(f"{ticker}.KS", start=start_date, progress=False)
                if hist_df.empty:
                    hist_df = yf.download(f"{ticker}.KQ", start=start_date, progress=False)
            except Exception as yf_err:
                print(f"yfinance download failed or rate limited: {yf_err}")
                hist_df = pd.DataFrame()
                
            # Fall back to FinanceDataReader if yfinance is empty or fails
            if hist_df.empty:
                try:
                    import FinanceDataReader as fdr
                    hist_df = fdr.DataReader(ticker, start_date)
                except Exception as fdr_err:
                    print(f"FinanceDataReader 데이터 가져오기 실패: {fdr_err}")
        else:
            info_data = fetch_yfinance_data(ticker)
            hist_df = pd.DataFrame()
            try:
                import yfinance as yf
                hist_df = yf.download(ticker, start=start_date, progress=False)
            except Exception as yf_err:
                print(f"US yfinance download failed: {yf_err}")
                
            # Fall back to FinanceDataReader for US stocks too! (Prevents rate limit block failures)
            if hist_df.empty:
                try:
                    import FinanceDataReader as fdr
                    hist_df = fdr.DataReader(ticker, start_date)
                except Exception as fdr_err:
                    print(f"US FinanceDataReader fallback failed: {fdr_err}")
                    
            if hist_df.empty:
                return {"error": f"미국 주식 데이터를 가져오는 중 오류가 발생했거나 데이터가 없습니다. 잠시 후 다시 시도해 주세요."}
            
        if not hist_df.empty:
            # yfinance returns MultiIndex columns sometimes; normalize them if needed
            if isinstance(hist_df.columns, pd.MultiIndex):
                # We want to extract just the main column names (e.g. 'Close', 'Volume')
                hist_df.columns = hist_df.columns.get_level_values(0)
                
            try:
                if 'Volume' in hist_df.columns:
                    vol_data = hist_df['Volume']
                    if isinstance(vol_data, pd.DataFrame):
                        last_vol = vol_data.iloc[-1, 0]
                    else:
                        last_vol = vol_data.iloc[-1]
                    info_data['volume'] = f"{int(last_vol):,}"
            except Exception as e:
                pass
                
            try:
                if info_data.get('current_price', 'N/A') == 'N/A':
                    if 'Close' in hist_df.columns:
                        close_data = hist_df['Close']
                        if isinstance(close_data, pd.DataFrame):
                            last_close = close_data.iloc[-1, 0]
                        else:
                            last_close = close_data.iloc[-1]
                        
                        # Format as integer if it's large (like KRW), else float
                        if last_close >= 100:
                            info_data['current_price'] = f"{int(last_close):,}"
                        else:
                            info_data['current_price'] = f"{last_close:,.2f}"
            except Exception as e:
                pass
            
            # 기술적 지표 추가
            hist_df = calculate_technical_indicators(hist_df)
            
        result = {
            "market": market,
            "ticker": ticker,
            "name": name,
            "info": info_data,
            "history": hist_df
        }
        return result
    except Exception as e:
        return {"error": f"데이터 수집 중 오류 발생: {str(e)}"}
