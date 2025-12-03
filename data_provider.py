# deepseek_finance_project_V3/data_provider.py

import os
import time
import requests
import pandas as pd
import akshare as ak
import baostock as bs
import yfinance as yf
from duckduckgo_search import DDGS
from retrying import retry
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

class NewsProvider:
    """
    [V3.9 并发舆情聚合器]
    策略: 同时发起 Finnhub, AlphaVantage, AkShare, DuckDuckGo 请求。
    """
    def __init__(self):
        self.finnhub_key = os.environ.get("Finnhub_API_Key")
        self.av_key = os.environ.get("Alpha_Vantage_API_Key")
        # [V3.14 新增] 集成 Financial Modeling Prep (FMP) API Key (预留功能)
        self.fmp_key = os.environ.get("FMP_API_Key")

    def _fetch_finnhub(self, symbol, start, end):
        if not self.finnhub_key: return []
        try:
            url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={start}&to={end}&token={self.finnhub_key}"
            res = requests.get(url, timeout=5).json()
            if isinstance(res, list):
                return [f"[Finnhub] {item.get('headline')}" for item in res[:5]]
        except Exception: pass
        return []

    def _fetch_alpha_vantage(self, symbol):
        if not self.av_key: return []
        try:
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={self.av_key}"
            res = requests.get(url, timeout=5).json()
            if "feed" in res:
                return [f"[AlphaVantage] {item.get('title')}" for item in res["feed"][:3]]
        except Exception: pass
        return []

    def _fetch_akshare_news(self, symbol):
        if not symbol.isdigit(): return [] 
        try:
            df = ak.stock_news_em(symbol=symbol)
            if not df.empty:
                return [f"[AkShare] {row['新闻标题']}" for _, row in df.head(5).iterrows()]
        except: return []

    def _fetch_ddg(self, symbol):
        try:
            with DDGS() as ddgs:
                keywords = f"{symbol} stock news finance"
                results = list(ddgs.text(keywords, max_results=3))
                return [f"[DuckDuckGo] {r['title']}" for r in results]
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
    """
    [V3.13 多轨行情 - 稳健版]
    升级: 港股全市场缓存 + 自动重试 + YFinance 降级兜底
    """
    def __init__(self):
        self._bs_logged_in = False
        self._hk_cache = None
        self._hk_cache_time = None

    def _login_baostock(self):
        if not self._bs_logged_in:
            try:
                bs.login()
                self._bs_logged_in = True
            except: pass

    def _fetch_akshare_snapshot(self, symbol):
        """A股快照"""
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == symbol]
            if not row.empty:
                return {
                    'price': float(row.iloc[0]['最新价']),
                    'prev_close': float(row.iloc[0]['昨收']),
                    'source': 'AkShare_A'
                }
        except: return None

    # 自动重试机制: 如果连接中断，等待2秒重试，最多3次
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _fetch_hk_snapshot_akshare(self):
        """内部方法: 带重试的 AkShare 港股获取"""
        return ak.stock_hk_spot_em()

    def _fetch_hk_snapshot(self, symbol):
        """港股快照 (AkShare 缓存 -> 失败则返回 None)"""
        try:
            now = datetime.now()
            # 缓存有效性检查 (60秒)
            if self._hk_cache is not None and self._hk_cache_time and (now - self._hk_cache_time).seconds < 60:
                df = self._hk_cache
            else:
                # 调用带重试的下载函数
                df = self._fetch_hk_snapshot_akshare()
                df['代码'] = df['代码'].astype(str).str.zfill(5)
                self._hk_cache = df
                self._hk_cache_time = now
            
            target_symbol = str(symbol).zfill(5)
            row = df[df['代码'] == target_symbol]
            
            if not row.empty:
                return {
                    'price': float(row.iloc[0]['最新价']),
                    'prev_close': float(row.iloc[0]['昨收']),
                    'source': 'AkShare_HK'
                }
        except Exception as e:
            print(f"   ❌ [DEBUG] AkShare 港股接口最终失败: {e}")
            pass
        return None

    def _fetch_yahoo_snapshot(self, symbol):
        """美股/港股(带后缀) 快照"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            price = info.last_price
            prev = info.previous_close
            
            # 简单的有效性检查
            if price is not None and prev is not None:
                return {
                    'price': price,
                    'prev_close': prev,
                    'source': 'Yahoo'
                }
        except: return None

    def get_quote_snapshot(self, symbol: str, market="A"):
        """获取实时行情快照 (带多级降级)"""
        snapshot = None
        
        if market == "HK":
            # 策略1: 尝试 AkShare 全市场缓存 (速度快，但可能连接失败)
            snapshot = self._fetch_hk_snapshot(symbol)
            
            # 策略2: 如果 AkShare 失败，降级使用 YFinance 单个查询
            if not snapshot:
                try:
                    # 转换代码格式: 00700 -> 00700.HK
                    yf_symbol = f"{str(symbol).zfill(5)}.HK"
                    snapshot = self._fetch_yahoo_snapshot(yf_symbol)
                except: pass
                
        elif market == "A":
            snapshot = self._fetch_akshare_snapshot(symbol)
        else:
            snapshot = self._fetch_yahoo_snapshot(symbol)
            
        if snapshot and snapshot['price'] > 0:
            return snapshot, True
        return None, False

    def fetch_history_kline(self, symbol: str, market="A", days=365):
        """历史 K 线获取"""
        start_date_str = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date_str = datetime.now().strftime("%Y-%m-%d")
        start_date_ak = start_date_str.replace("-", "")
        df_final = pd.DataFrame()

        if market == "A":
            try:
                df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date_ak, adjust="qfq")
                df_final = df.rename(columns={"日期": "date", "收盘": "close", "开盘": "open", "最高": "high", "最低": "low", "成交量": "volume"})
            except: pass
            
            if df_final.empty:
                try:
                    self._login_baostock()
                    bs_code = f"sh.{symbol}" if symbol.startswith('6') else f"sz.{symbol}"
                    rs = bs.query_history_k_data_plus(bs_code, "date,open,high,low,close,volume", start_date=start_date_str, end_date=end_date_str, frequency="d", adjustflag="3")
                    data_list = []
                    while (rs.error_code == '0') & rs.next(): data_list.append(rs.get_row_data())
                    if data_list:
                        df_final = pd.DataFrame(data_list, columns=rs.fields).apply(pd.to_numeric, errors='ignore')
                except: pass

        elif market == "US":
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
            except Exception: pass

            if df_final.empty:
                try:
                    df = yf.download(symbol, start=start_date_str, end=end_date_str, progress=False, auto_adjust=False)
                    df = df.reset_index()
                    df.columns = [c.lower() for c in df.columns]
                    if 'datetime' in df.columns: df.rename(columns={'datetime': 'date'}, inplace=True)
                    df_final = df
                except: pass

        return df_final

class DataProvider:
    def __init__(self):
        self.news = NewsProvider()
        self.market = MarketProvider()
        
        self.etf_mapping = {
            "013403": "513180", 
            "012804": "513180", 
            "006327": "159941", 
            "006479": "159941", 
            "000834": "513500",
            "000001": "000001"
        }

    def fetch_fund_nav_history(self, fund_code, start_date=None, end_date=None):
        df = pd.DataFrame()
        try:
            df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
            if not df.empty:
                df = df.rename(columns={"净值日期": "date", "单位净值": "nav", "日增长率": "daily_change"})
        except Exception: pass

        if df.empty:
            try:
                df = ak.fund_nav_history_em(symbol=fund_code)
                if not df.empty:
                    df = df.rename(columns={"净值日期": "date", "单位净值": "nav", "日增长率": "daily_change"})
            except Exception: pass
        
        if df.empty and fund_code in self.etf_mapping:
            try:
                target_etf = self.etf_mapping[fund_code]
                df_etf = self.market.fetch_history_kline(target_etf, market="A")
                if not df_etf.empty:
                    df = df_etf[['date', 'close']].rename(columns={'close': 'nav'})
                    df['daily_change'] = df['nav'].pct_change() * 100
            except: pass

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

    def fetch_fund_portfolio(self, fund_code, years_to_try=2):
        target_code = self.etf_mapping.get(fund_code, fund_code)
        if target_code != fund_code:
            print(f"   🔗 检测到联接基金，自动穿透至目标 ETF: {target_code}")
        
        current_year = datetime.now().year
        df = pd.DataFrame()

        for i in range(years_to_try):
            try_year = str(current_year - i)
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
                    return df
            except Exception: pass
        
        return pd.DataFrame()