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
        print(f"🔧 初始化 NewsProvider (Keys: Finnhub={'✅' if self.finnhub_key else '❌'}, AV={'✅' if self.av_key else '❌'})")

    def _fetch_finnhub(self, symbol, start, end):
        if not self.finnhub_key: return []
        try:
            url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={start}&to={end}&token={self.finnhub_key}"
            res = requests.get(url, timeout=5).json()
            if isinstance(res, list):
                return [f"[Finnhub] {item.get('headline')}" for item in res[:5]]
        except Exception as e:
            print(f"   ⚠️ Finnhub 异常: {e}")
        return []

    def _fetch_alpha_vantage(self, symbol):
        if not self.av_key: return []
        try:
            url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={symbol}&apikey={self.av_key}"
            res = requests.get(url, timeout=5).json()
            if "feed" in res:
                return [f"[AlphaVantage] {item.get('title')}" for item in res["feed"][:3]]
        except Exception as e:
            print(f"   ⚠️ AlphaVantage 异常: {e}")
        return []

    def _fetch_akshare_news(self, symbol):
        if not symbol.isdigit(): return [] 
        try:
            df = ak.stock_news_em(symbol=symbol)
            if not df.empty:
                return [f"[AkShare] {row['新闻标题']}" for _, row in df.head(5).iterrows()]
        except:
            return []

    def _fetch_ddg(self, symbol):
        try:
            with DDGS() as ddgs:
                keywords = f"{symbol} stock news finance"
                results = list(ddgs.text(keywords, max_results=3))
                return [f"[DuckDuckGo] {r['title']}" for r in results]
        except Exception as e:
            print(f"   ⚠️ DDG 搜索异常: {e}")
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

        print(f"   ⚡ 正在并发请求舆情源 ({', '.join(tasks.keys())})...")
        
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
    [V3.9 多轨行情]
    升级: 支持获取 Snapshot (现价 + 昨收)，解决冷启动问题。
    """
    def __init__(self):
        self._bs_logged_in = False

    def _login_baostock(self):
        if not self._bs_logged_in:
            bs.login()
            self._bs_logged_in = True

    def _fetch_akshare_snapshot(self, symbol):
        """返回 {'price': float, 'prev_close': float}"""
        try:
            # 使用东财实时接口，包含昨收
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == symbol]
            if not row.empty:
                return {
                    'price': float(row.iloc[0]['最新价']),
                    'prev_close': float(row.iloc[0]['昨收']),
                    'source': 'AkShare'
                }
        except:
            return None

    def _fetch_yahoo_snapshot(self, symbol):
        """返回 {'price': float, 'prev_close': float}"""
        try:
            ticker = yf.Ticker(symbol)
            # fast_info 比 history 快且全
            info = ticker.fast_info
            return {
                'price': info.last_price,
                'prev_close': info.previous_close,
                'source': 'Yahoo'
            }
        except:
            return None

    def get_quote_snapshot(self, symbol: str, market="A"):
        """
        获取实时行情快照 (优先用于 Shadow NAV 计算)
        """
        snapshot = None
        
        if market == "A":
            snapshot = self._fetch_akshare_snapshot(symbol)
        else:
            snapshot = self._fetch_yahoo_snapshot(symbol)
            
        if snapshot and snapshot['price'] > 0:
            return snapshot, True
        return None, False

    def fetch_history_kline(self, symbol: str, market="A", days=365):
        """历史 K 线获取 (保持 V3.7 逻辑)"""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        df_final = pd.DataFrame()

        if market == "A":
            try:
                df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="qfq")
                df_final = df.rename(columns={"日期": "date", "收盘": "close", "开盘": "open", "最高": "high", "最低": "low", "成交量": "volume"})
            except: pass
            
            if df_final.empty:
                try:
                    self._login_baostock()
                    bs_code = f"sh.{symbol}" if symbol.startswith('6') else f"sz.{symbol}"
                    rs = bs.query_history_k_data_plus(bs_code, "date,open,high,low,close,volume", start_date=start_date, end_date=end_date, frequency="d", adjustflag="3")
                    data_list = []
                    while (rs.error_code == '0') & rs.next(): data_list.append(rs.get_row_data())
                    if data_list:
                        df_final = pd.DataFrame(data_list, columns=rs.fields).apply(pd.to_numeric, errors='ignore')
                except: pass

        elif market == "US":
            try:
                df = yf.download(symbol, start=start_date, end=end_date, progress=False)
                df = df.reset_index()
                df.columns = [c.lower() for c in df.columns]
                df_final = df
            except: pass

        return df_final

class DataProvider:
    def __init__(self):
        self.news = NewsProvider()
        self.market = MarketProvider()

    def fetch_fund_nav_history(self, fund_code, start_date=None, end_date=None):
        try:
            df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
            df = df.rename(columns={"净值日期": "date", "单位净值": "nav", "日增长率": "daily_change"})
            df['date'] = pd.to_datetime(df['date'])
            df['fund_code'] = fund_code
            if start_date: df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date: df = df[df['date'] <= pd.to_datetime(end_date)]
            return df
        except:
            return pd.DataFrame()

    def fetch_fund_portfolio(self, fund_code, year=None):
        try:
            if not year: year = str(datetime.now().year)
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
            df = df.rename(columns={"股票代码": "stock_code", "股票名称": "stock_name", "占净值比例": "weight", "季度": "quarter"})
            df['fund_code'] = fund_code
            return df
        except:
            return pd.DataFrame()