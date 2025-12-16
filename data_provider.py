# deepseek_finance_project_V3/data_provider.py

import os
import time
import requests
import pandas as pd
import akshare as ak
import yfinance as yf
from duckduckgo_search import DDGS
from retrying import retry
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import logging
import urllib3
import warnings

# [V3.58 最终修复版] 
# 1. 增加 ETF 联接基金穿透映射 (解决 019671/019670 无持仓问题)
# 2. 修复 Yahoo Finance 空值异常
# 3. 优化日志输出

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

_orig_request = requests.Session.request
def _patched_request(self, method, url, *args, **kwargs):
    timeout = kwargs.get("timeout")
    if timeout is None:
        kwargs["timeout"] = 300
    elif isinstance(timeout, (int, float)) and timeout < 300:
        kwargs["timeout"] = 300
    return _orig_request(self, method, url, *args, **kwargs)
requests.Session.request = _patched_request

class NewsProvider:
    def __init__(self):
        self.finnhub_key = os.environ.get("Finnhub_API_Key")
        self.av_key = os.environ.get("Alpha_Vantage_API_Key")
        self.fmp_key = os.environ.get("FMP_API_Key")
        self.twelvedata_key = os.environ.get("TwelveData_API_Key")

    def _fetch_finnhub(self, symbol, start, end):
        if not self.finnhub_key: return []
        print(f"   ⚡ [API] 请求 Finnhub 新闻: {symbol}...")
        try:
            url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={start}&to={end}&token={self.finnhub_key}"
            res = requests.get(url, timeout=15, verify=False)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    return [f"[Finnhub] {item.get('headline')}" for item in res.json()[:5]]
        except Exception: pass
        return []

    def _fetch_alpha_vantage(self, symbol):
        if not self.av_key: return []
        print(f"   ⚡ [API] 请求 Alpha Vantage 新闻: {symbol}...")
        try:
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={self.av_key}"
            res = requests.get(url, timeout=15, verify=False)
            if res.status_code == 200:
                data = res.json()
                if "feed" in data:
                    return [f"[AlphaVantage] {item.get('title')}" for item in data["feed"][:3]]
        except Exception: pass
        return []

    def _fetch_akshare_news(self, symbol):
        if not symbol.isdigit(): return [] 
        print(f"   ⚡ [API] 请求 AkShare (东方财富) 新闻: {symbol}...")
        try:
            df = ak.stock_news_em(symbol=symbol)
            if not df.empty:
                return [f"[AkShare] {row['新闻标题']}" for _, row in df.head(5).iterrows()]
        except Exception: pass
        return []

    def _fetch_ddg(self, symbol):
        search_query = f"{symbol} 基金 财经" if symbol.isdigit() else f"{symbol} stock news"
        print(f"   ⚡ [API] 请求 DuckDuckGo 搜索: {search_query}...")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=5))
                valid_results = []
                for r in results:
                    title = r['title']
                    if symbol in title or "基金" in title or "stock" in title.lower():
                        valid_results.append(f"[DuckDuckGo] {title}")
                return valid_results[:3]
        except Exception: pass
        return []

    def fetch_sentiment_news(self, symbol: str, lookback_days=3):
        start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        
        news_pool = []
        tasks = {
            "finnhub": lambda: self._fetch_finnhub(symbol, start, end),
            "av": lambda: self._fetch_alpha_vantage(symbol),
            "akshare": lambda: self._fetch_akshare_news(symbol),
            "ddg": lambda: self._fetch_ddg(symbol)
        }
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_source = {executor.submit(func): source for source, func in tasks.items()}
            for future in as_completed(future_to_source):
                try:
                    data = future.result()
                    if data: news_pool.extend(data)
                except Exception: pass

        return list(set(news_pool))

class MarketProvider:
    def __init__(self):
        self._hk_cache = None
        self._hk_lock = Lock()
        
        self._a_cache = None
        self._a_lock = Lock()
        self._a_cache_attempted = False
        
        self.cache_dir = "data/cache"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        self.fmp_key = os.environ.get("FMP_API_Key")
        self.av_key = os.environ.get("Alpha_Vantage_API_Key")
        self.twelvedata_key = os.environ.get("TwelveData_API_Key")

    def _fetch_fmp_snapshot(self, symbol, market):
        if not self.fmp_key: return None
        try:
            query_symbol = symbol.replace('^', '')
            if market == "HK": query_symbol = f"{str(symbol).zfill(5)}.HK"
            url = f"https://financialmodelingprep.com/api/v3/quote/{query_symbol}?apikey={self.fmp_key}"
            res = requests.get(url, timeout=15, verify=False)
            if res.status_code == 200:
                data = res.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return {'price': float(data[0].get('price', 0)), 'prev_close': float(data[0].get('previousClose', 0)), 'source': 'FMP'}
        except: pass
        return None

    def _fetch_av_snapshot(self, symbol, market):
        if not self.av_key: return None
        try:
            query_symbol = symbol
            if market == "HK": query_symbol = f"{str(symbol).zfill(5)}.HK"
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={query_symbol}&apikey={self.av_key}"
            res = requests.get(url, timeout=15, verify=False)
            if res.status_code == 200:
                quote = res.json().get("Global Quote", {})
                if quote:
                    return {'price': float(quote.get("05. price", 0)), 'prev_close': float(quote.get("08. previous close", 0)), 'source': 'AlphaVantage'}
        except: pass
        return None

    def _fetch_twelvedata_snapshot(self, symbol, market):
        if not self.twelvedata_key: return None
        try:
            query_symbol = symbol
            if market == "HK": query_symbol = f"{str(symbol).zfill(5)}.HK"
            url = f"https://api.twelvedata.com/quote?symbol={query_symbol}&apikey={self.twelvedata_key}"
            res = requests.get(url, timeout=15, verify=False)
            if res.status_code == 200:
                data = res.json()
                if 'close' in data:
                    return {'price': float(data['close']), 'prev_close': float(data.get('previous_close', 0)), 'source': 'TwelveData'}
        except: pass
        return None

    @retry(stop_max_attempt_number=3, wait_fixed=5000)
    def _download_akshare_a_spot(self):
        return ak.stock_zh_a_spot_em()

    def _fetch_akshare_snapshot(self, symbol):
        try:
            today_str = datetime.now().strftime("%Y%m%d")
            cache_file = os.path.join(self.cache_dir, f"a_snapshot_{today_str}.csv")
            
            with self._a_lock:
                if self._a_cache is not None:
                    df = self._a_cache
                elif os.path.exists(cache_file):
                    try:
                        df = pd.read_csv(cache_file, dtype={'代码': str})
                        self._a_cache = df
                    except: df = None
                
                if self._a_cache is None:
                    if False: 
                        print(f"   ⚡ [API] 请求 AkShare A股全市场行情 (每日一次)...")
                        self._a_cache_attempted = True 
                        try:
                            df = self._download_akshare_a_spot()
                            if not df.empty:
                                df.to_csv(cache_file, index=False)
                                self._a_cache = df
                        except Exception: pass
            
            search_code = symbol.split('.')[0]
            if self._a_cache is not None:
                row = self._a_cache[self._a_cache['代码'] == search_code]
                if not row.empty:
                    return {
                        'price': float(row.iloc[0]['最新价']),
                        'prev_close': float(row.iloc[0]['昨收']),
                        'source': 'AkShare_A'
                    }
        except: pass
        return None

    @retry(stop_max_attempt_number=2, wait_fixed=1000)
    def _fetch_hk_snapshot_akshare(self):
        return ak.stock_hk_spot_em()

    def _fetch_hk_snapshot(self, symbol):
        try:
            today_str = datetime.now().strftime("%Y%m%d")
            cache_file = os.path.join(self.cache_dir, f"hk_snapshot_{today_str}.csv")
            
            with self._hk_lock:
                if self._hk_cache is not None:
                    df = self._hk_cache
                elif os.path.exists(cache_file):
                    try:
                        df = pd.read_csv(cache_file, dtype={'代码': str})
                        df['代码'] = df['代码'].str.zfill(5)
                        self._hk_cache = df
                    except: df = None
                
                if self._hk_cache is None:
                    if False: 
                        print("   ⚡ [API] 请求 AkShare 港股全市场行情 (下载可能较慢)...")
                        df = self._fetch_hk_snapshot_akshare()
                        df['代码'] = df['代码'].astype(str).str.zfill(5)
                        df.to_csv(cache_file, index=False)
                        self._hk_cache = df
            
            target_symbol = str(symbol).zfill(5)
            if self._hk_cache is not None:
                row = self._hk_cache[self._hk_cache['代码'] == target_symbol]
                if not row.empty:
                    return {'price': float(row.iloc[0]['最新价']), 'prev_close': float(row.iloc[0]['昨收']), 'source': 'AkShare_HK'}
        except Exception: pass
        return None

    def _fetch_yahoo_snapshot(self, symbol):
        print(f"   ⚡ [API] 请求 Yahoo Finance 快照: {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            price, prev = None, None
            try:
                if hasattr(ticker, 'fast_info') and ticker.fast_info is not None:
                    price = ticker.fast_info.last_price
                    prev = ticker.fast_info.previous_close
            except: pass

            if price is None:
                try:
                    info = ticker.info
                    if info is not None: 
                        price = info.get('regularMarketPrice') or info.get('currentPrice')
                        prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
                except: pass

            if price is not None and prev is not None and price > 0:
                return {'price': price, 'prev_close': prev, 'source': 'Yahoo'}
            else:
                print(f"     ⚠️ Yahoo 数据无效: Price={price}, Prev={prev}")
        except Exception: pass
        return None

    def _fetch_hk_hist_fallback(self, symbol):
        print(f"   ⚡ [API] 请求 AkShare 港股历史日线 (兜底): {symbol}...")
        try:
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
            df = ak.stock_hk_hist(symbol=symbol, period="daily", start_date=start_date, adjust="qfq")
            if not df.empty:
                latest = df.iloc[-1]
                return {'price': float(latest['收盘']), 'prev_close': float(latest['收盘']), 'source': 'AkShare_Hist_Fallback'}
        except: pass
        return None

    def get_quote_snapshot(self, symbol: str, market="A"):
        snapshot = None
        if market == "HK":
            snapshot = self._fetch_hk_snapshot(symbol)
            if not snapshot: 
                try:
                    yf_symbol = f"{str(symbol).zfill(5)}.HK"
                    snapshot = self._fetch_yahoo_snapshot(yf_symbol)
                except: pass
            if not snapshot: snapshot = self._fetch_fmp_snapshot(symbol, "HK")
            if not snapshot: snapshot = self._fetch_av_snapshot(symbol, "HK")
            if not snapshot: snapshot = self._fetch_twelvedata_snapshot(symbol, "HK")
            if not snapshot: snapshot = self._fetch_hk_hist_fallback(symbol)
                
        elif market == "A":
            snapshot = self._fetch_akshare_snapshot(symbol)
            if not snapshot:
                upper_sym = symbol.upper()
                yf_symbol = symbol
                
                if not (upper_sym.endswith('.SS') or upper_sym.endswith('.SZ')):
                    yf_symbol = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
                
                snapshot = self._fetch_yahoo_snapshot(yf_symbol)
                
                if not snapshot and symbol.isdigit() and not (upper_sym.endswith('.SS') or upper_sym.endswith('.SZ')):
                     other_suffix = ".SZ" if yf_symbol.endswith(".SS") else ".SS"
                     snapshot = self._fetch_yahoo_snapshot(f"{symbol}{other_suffix}")
            
        else: # US / Global Index
            snapshot = self._fetch_yahoo_snapshot(symbol)
            if not snapshot: snapshot = self._fetch_fmp_snapshot(symbol, "US")
            if not snapshot: snapshot = self._fetch_av_snapshot(symbol, "US")
            if not snapshot: snapshot = self._fetch_twelvedata_snapshot(symbol, "US")
            
        if snapshot and snapshot['price'] > 0:
            return snapshot, True
        return None, False

    def get_exchange_rate(self, target_currency="CNY"):
        symbol = f"{target_currency}=X" 
        print(f"   ⚡ [API] 请求汇率数据: {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            rate, change_pct = 1.0, 0.0
            
            try:
                rate = ticker.fast_info.last_price
                prev = ticker.fast_info.previous_close
                change_pct = ((rate - prev) / prev) * 100
            except:
                try:
                    info = ticker.info
                    if info:
                        rate = info.get('regularMarketPrice', 1.0)
                        prev = info.get('previousClose', 1.0)
                        change_pct = ((rate - prev) / prev) * 100
                except: pass
            return rate, change_pct
        except Exception:
            return 1.0, 0.0

    def fetch_history_kline(self, symbol: str, market="A", days=365):
        start_date_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date_str = datetime.now().strftime("%Y-%m-%d")
        start_date_ak = start_date_str.replace("-", "")
        
        today_str = datetime.now().strftime("%Y%m%d")
        safe_symbol = symbol.replace("^", "").replace("=", "")
        cache_file = os.path.join(self.cache_dir, f"kline_{safe_symbol}_{today_str}.csv")
        
        if os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                df['date'] = pd.to_datetime(df['date'])
                return df
            except: pass

        print(f"   ☁️ [联网] 下载 K 线数据: {symbol}...")
        df_final = pd.DataFrame()

        if market == "A":
            print(f"   ⚡ [API] 请求 AkShare A股历史K线: {symbol}...")
            try:
                df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date_ak, adjust="qfq")
                df_final = df.rename(columns={"日期": "date", "收盘": "close", "开盘": "open", "最高": "high", "最低": "low", "成交量": "volume"})
            except Exception as e: print(f"     ❌ AkShare A股K线异常: {e}")
            
            if df_final.empty:
                print(f"   ⚡ [API] 请求 Yahoo Finance 历史K线 (A股兜底): {symbol}...")
                try:
                    yf_symbol = symbol
                    upper_sym = symbol.upper()
                    if not (upper_sym.endswith(".SS") or upper_sym.endswith(".SZ")):
                        yf_symbol = f"{symbol}.SS" if symbol.startswith("6") else f"{symbol}.SZ"
                    
                    df = yf.download(yf_symbol, start=start_date_str, end=end_date_str, progress=False, auto_adjust=False)
                    if not df.empty:
                        df = df.reset_index()
                        new_cols = []
                        for c in df.columns:
                            if isinstance(c, tuple): new_cols.append(str(c[0]).lower())
                            else: new_cols.append(str(c).lower())
                        df.columns = new_cols
                        if 'datetime' in df.columns: df.rename(columns={'datetime': 'date'}, inplace=True)
                        df_final = df
                except Exception as e: print(f"     ❌ YFinance A股兜底异常: {e}")

        else: # US / Global
            print(f"   ⚡ [API] 请求 YFinance 历史K线: {symbol}...")
            try:
                df = yf.download(symbol, start=start_date_str, end=end_date_str, progress=False, auto_adjust=False)
                if not df.empty:
                    df = df.reset_index()
                    new_cols = []
                    for c in df.columns:
                        if isinstance(c, tuple): new_cols.append(str(c[0]).lower())
                        else: new_cols.append(str(c).lower())
                    df.columns = new_cols
                    
                    if 'datetime' in df.columns: df.rename(columns={'datetime': 'date'}, inplace=True)
                    df_final = df
            except Exception as e: print(f"     ❌ YFinance K线异常: {e}")

            if df_final.empty and market == "US":
                print(f"   ⚡ [API] 请求 AkShare 美股历史K线: {symbol}...")
                try:
                    ak_symbol = symbol
                    if symbol == "^IXIC": ak_symbol = ".IXIC"
                    elif symbol == "^GSPC": ak_symbol = ".INX"
                    
                    df = ak.index_us_stock_sina(symbol=ak_symbol)
                    if not df.empty:
                        df = df.rename(columns={"date": "date", "close": "close", "open": "open", "high": "high", "low": "low", "volume": "volume"})
                        df['date'] = pd.to_datetime(df['date'])
                        df = df[df['date'] >= pd.to_datetime(start_date_str)]
                        df_final = df
                except Exception as e: print(f"     ❌ AkShare 美股K线异常: {e}")

        if not df_final.empty:
            try:
                df_final.to_csv(cache_file, index=False)
            except: pass

        return df_final

    def fetch_fund_nav_history(self, fund_code, start_date=None, end_date=None):
        print(f"   ⚡ [API] 请求 AkShare 基金净值: {fund_code}...")
        
        if str(fund_code).isdigit() and len(str(fund_code)) < 6:
            fund_code = str(fund_code).zfill(6)
            
        df = pd.DataFrame()
        try:
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if not df.empty:
                df = df.rename(columns={"净值日期": "date", "单位净值": "nav", "日增长率": "daily_change"})
        except Exception: pass

        if df.empty:
            print(f"   ⚡ [API] 尝试作为 ETF/股票获取行情: {fund_code}...")
            df_etf = self.fetch_history_kline(fund_code, market="A")
            if not df_etf.empty:
                df = df_etf[['date', 'close']].rename(columns={'close': 'nav'})
                df['daily_change'] = df['nav'].pct_change() * 100
                df['fund_code'] = fund_code
                print(f"     ✅ 兜底获取成功 ({len(df)} 条)")

        if df.empty:
             yf_symbol = f"{fund_code}.SS" if fund_code.startswith("5") or fund_code.startswith("6") else f"{fund_code}.SZ"
             if fund_code.isdigit():
                 print(f"   ⚡ [API] 尝试 Yahoo 兜底: {yf_symbol}...")
                 df_etf = self.fetch_history_kline(yf_symbol, market="A")
                 if not df_etf.empty:
                    df = df_etf[['date', 'close']].rename(columns={'close': 'nav'})
                    df['daily_change'] = df['nav'].pct_change() * 100
                    df['fund_code'] = fund_code

        if not df.empty:
            try:
                df['date'] = pd.to_datetime(df['date'])
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                df['fund_code'] = fund_code
                if start_date: df = df[df['date'] >= pd.to_datetime(start_date)]
                if end_date: df = df[df['date'] <= pd.to_datetime(end_date)]
                df = df.dropna(subset=['nav']).sort_values('date')
            except: return pd.DataFrame()
        return df

class DataProvider:
    """
    数据层总入口 (Facade)
    """
    def __init__(self):
        self.news = NewsProvider()
        self.market = MarketProvider()
        
        self.holdings_dir = "data/holdings"
        if not os.path.exists(self.holdings_dir):
            os.makedirs(self.holdings_dir)
            
        # [Fix V3.58] 新增 ETF 穿透映射
        # 广发港股创新药 C(019671)/A(019670) -> 追踪 513120 (沪港深创新药ETF) -> 甚至直接追踪 002371 (成分股)
        # 这里我们映射到一个相似的场内 ETF：159941 (纳指) 等等
        # 对于 019671，我们映射到 513120 (恒生生物科技ETF)
        self.etf_mapping = {
            "013403": {"target": "513180", "index": "HSTECH"}, 
            "012804": {"target": "513180", "index": "HSTECH"}, 
            "019671": {"target": "513120", "index": "HK_DRUG"}, 
            "019670": {"target": "513120", "index": "HK_DRUG"}, 
            "006327": {"target": "159941", "index": "IXIC"},   
            "000834": {"target": "513500", "index": "SPX"},    
            "000001": {"target": "000001", "index": "000001"}  
        }

    def _fetch_fmp_holdings_backup(self, symbol):
        if not self.news.fmp_key: return pd.DataFrame()
        suffixes = [".SS", ".SH", ".HK", ""]
        for s in suffixes:
            fmp_symbol = f"{symbol}{s}"
            print(f"   ⚡ [API] 降级尝试 FMP 获取持仓: {fmp_symbol}...")
            try:
                url = f"https://financialmodelingprep.com/api/v3/etf-holder/{fmp_symbol}?apikey={self.news.fmp_key}"
                res = requests.get(url, timeout=10, verify=False)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        holdings = []
                        for item in data:
                            holdings.append({
                                "stock_code": item.get('asset', 'Unknown'),
                                "stock_name": item.get('asset', 'Unknown'),
                                "weight": float(item.get('weightPercentage', 0)),
                                "quarter": "FMP_Latest"
                            })
                        print(f"     ✅ FMP 获取成功 ({len(holdings)}条)")
                        return pd.DataFrame(holdings)
            except: pass
        return pd.DataFrame()

    def _fetch_av_holdings_backup(self, symbol):
        if not self.news.av_key: return pd.DataFrame()
        return pd.DataFrame()

    def _fetch_index_constituents_backup(self, index_code):
        print(f"   ⚡ [API] 降级尝试获取指数成分股 (AkShare): {index_code}...")
        try:
            if index_code == "HSTECH":
                df = ak.stock_hk_index_constituent_sina(symbol="恒生科技指数")
                if not df.empty:
                    df = df.rename(columns={"symbol": "stock_code", "name": "stock_name"})
                    df['weight'] = 100 / len(df) 
                    return df
        except: pass
        return pd.DataFrame()

    def _fetch_local_holdings_backup(self, symbol):
        path = f"data/holdings/{symbol}.csv"
        if os.path.exists(path):
            print(f"   ⚡ [API] 读取本地持仓文件: {path}...")
            try:
                df = pd.read_csv(path)
                return df
            except: pass
        return pd.DataFrame()

    def fetch_history_kline(self, symbol, market="A", days=365):
        return self.market.fetch_history_kline(symbol, market=market, days=days)

    def fetch_fund_nav_history(self, fund_code, start_date=None, end_date=None):
        return self.market.fetch_fund_nav_history(fund_code, start_date, end_date)
    
    def get_exchange_rate(self, target_currency="CNY"):
        return self.market.get_exchange_rate(target_currency)

    def fetch_fund_portfolio(self, fund_code, years_to_try=2, force_update=False):
        # 强制修正 6 位代码
        if str(fund_code).isdigit() and len(str(fund_code)) < 6:
            fund_code = str(fund_code).zfill(6)
            
        target_code = fund_code
        index_code = None
        
        # [Fix] 优先检查映射 (ETF穿透)
        if fund_code in self.etf_mapping:
            mapping = self.etf_mapping[fund_code]
            target_code = mapping["target"]
            index_code = mapping.get("index")
            print(f"   🔗 [Mapping] 基金 {fund_code} 映射到目标: {target_code}")
            
        cache_file = os.path.join(self.holdings_dir, f"{target_code}.csv")
        
        # 1. 尝试读缓存
        if not force_update and os.path.exists(cache_file):
            try:
                df = pd.read_csv(cache_file)
                if not df.empty and 'stock_code' in df.columns:
                    return df
            except: pass
            
        df = pd.DataFrame()
        current_year = datetime.now().year

        # 2. 尝试 AkShare (主代码)
        for i in range(years_to_try):
            try_year = str(current_year - i)
            print(f"   ⚡ [API] 请求 AkShare 基金持仓 ({try_year}): {target_code}...")
            try:
                df = ak.fund_portfolio_hold_em(symbol=target_code, date=try_year)
                if not df.empty and len(df) > 0:
                    if '季度' in df.columns:
                        quarters = df['季度'].unique()
                        if len(quarters) > 0:
                            latest_q = sorted(quarters, reverse=True)[0]
                            df = df[df['季度'] == latest_q]

                    df = df.rename(columns={"股票代码": "stock_code", "股票名称": "stock_name", "占净值比例": "weight", "季度": "quarter"})
                    
                    if df['weight'].dtype == 'object':
                        df['weight'] = df['weight'].str.replace('%', '', regex=False)
                    
                    df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0.0)
                    df['fund_code'] = fund_code
                    
                    # 保存缓存
                    df.to_csv(cache_file, index=False)
                    return df
            except Exception: pass
        
        # 3. 降级尝试 FMP
        if df.empty:
            df = self._fetch_fmp_holdings_backup(target_code)
            if not df.empty:
                df['fund_code'] = fund_code
                df.to_csv(cache_file, index=False)
                return df
        
        # 4. 降级尝试 AV
        if df.empty:
            df = self._fetch_av_holdings_backup(target_code)
            if not df.empty:
                df['fund_code'] = fund_code
                return df

        # 5. 降级尝试指数成分股
        if df.empty and index_code:
            df = self._fetch_index_constituents_backup(index_code)
            if not df.empty:
                df['fund_code'] = fund_code
                return df

        # 6. 最后尝试本地手动文件
        if df.empty:
            df = self._fetch_local_holdings_backup(target_code)
            if not df.empty:
                df['fund_code'] = fund_code
                return df
        
        print(f"   🚫 [API] 无法获取 {fund_code} 的持仓明细 (已尝试 AkShare/FMP/Index)。")
        return pd.DataFrame()