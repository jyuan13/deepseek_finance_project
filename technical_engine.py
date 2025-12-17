"""
==========================================================================================
【文件定义】
文件名: technical_engine.py
类名  : TechnicalEngine
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(request_delay, max_retries)
   [Try Import TA-Lib] -> (Success/Fail? Set HAS_TALIB)
         ↓
   [Init Cache Variables] -> [Ready]

2. get_realtime_price(symbol)
   {EndsWith .HK?} -> [Call _get_hk_realtime_price]
         ↓
   {EndsWith .SH/.SZ or Digit?} -> [Try AKShare Spot] -> [Retry Loop]
         ↓
   {Is Alpha or .US?} -> [Try YFinance fast_info]
         ↓
   [Return Price, ChangePct]

3. _get_hk_realtime_price(symbol)
   {Cache Valid (<15s)?} -> (Return Cache)
         ↓
   [AKShare HK Spot] -> [Update Cache] -> [Find Symbol] -> [Return Price]

4. analyze_holdings_health(holdings_list)
   [ThreadPoolExecutor] -> [Concurrent: _analyze_single_stock]
         ↓
   [Loop Futures] -> [Collect Results] -> [Aggregate Metrics (MA/RSI/ShadowNAV)]
         ↓
   [Normalize Metrics] -> [Sort by Weight] -> [Return Results Dict]

5. _analyze_single_stock(stock_info)
   [Call get_realtime_price] -> {Failed?} -> (Return None)
         ↓
   [Call get_stock_data_for_ma] -> {History < 60?} -> (Return No_History)
         ↓
   [Call _calculate_indicators] -> [Call _generate_signal] -> [Return Data Dict]

6. get_stock_data_for_ma(symbol)
   {CN/HK Market?} -> [Call get_stock_data_akshare]
         ↓
   {US Market?} -> [Call get_stock_data_yfinance]

7. get_stock_data_akshare(symbol, period)
   {HK?} -> [AKShare HK Hist]
         ↓
   {A-Share?} -> [AKShare A Hist]
         ↓
   [Rename Cols] -> [Format Date/Numeric] -> [Return DF]

8. get_stock_data_yfinance(symbol, period)
   [YFinance Ticker] -> [History] -> [Return DF]

9. _calculate_indicators(df)
   {HAS_TALIB?} -> (Yes: TA-Lib SMA/RSI)
         ↓
   (No: Pandas Rolling Mean / Manual RSI Calc) -> [Return DF]

10. _generate_signal(price, ma_data)
    [Check MA60 Distance (Pressure/Support)] -> [Check RSI (Overbought/Oversold)]
          ↓
    [Return Signal String]
==========================================================================================
"""

import yfinance as yf
import akshare as ak
import time
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入 TA-Lib，如果没有则使用 Pandas 兼容模式
try:
    import talib
    HAS_TALIB = True
except ImportError:
    print("⚠️ 未检测到 TA-Lib 库，将使用 Pandas 进行技术指标计算（性能可能略低）")
    HAS_TALIB = False

class TechnicalEngine:
    """技术分析引擎 V5.0 - 全天候趋势增强版"""

    def __init__(self, request_delay=1, max_retries=3):
        self.request_delay = request_delay
        self.max_retries = max_retries
        self._hk_spot_cache = None 
        self._hk_cache_time = 0

    def get_realtime_price(self, symbol):
        """获取实时价格 (支持 A股/港股/美股)"""
        try:
            symbol = symbol.strip().upper()
            
            # 1. 港股处理 (00700.HK)
            if symbol.endswith('.HK'):
                return self._get_hk_realtime_price(symbol)
            
            # 2. A股处理 (600519.SH)
            if symbol.endswith(('.SH', '.SZ', '.BJ')) or (symbol.isdigit() and len(symbol) == 6):
                clean_symbol = symbol.split('.')[0]
                for _ in range(2):
                    try:
                        df = ak.stock_zh_a_spot_em()
                        row = df[df['代码'] == clean_symbol]
                        if not row.empty:
                            return float(row.iloc[0]['最新价']), float(row.iloc[0]['涨跌幅'])
                    except: pass
                    time.sleep(0.5)
            
            # 3. [V5新增] 美股/QDII处理 (NVDA, AAPL) - 使用 YFinance
            if symbol.isalpha() or symbol.endswith('.US'):
                clean_symbol = symbol.replace('.US', '')
                try:
                    ticker = yf.Ticker(clean_symbol)
                    # fast_info 提供了比 history 更快的实时快照
                    price = ticker.fast_info.last_price
                    prev_close = ticker.fast_info.previous_close
                    if price and prev_close:
                        change_pct = ((price - prev_close) / prev_close) * 100
                        return float(price), float(change_pct)
                except: pass

            return None, 0.0
        except Exception as e:
            # print(f"获取价格异常 {symbol}: {e}")
            return None, 0.0

    def _get_hk_realtime_price(self, symbol):
        try:
            current_time = time.time()
            if self._hk_spot_cache is None or (current_time - self._hk_cache_time > 15):
                self._hk_spot_cache = ak.stock_hk_spot_em()
                self._hk_cache_time = current_time
            
            raw_code = symbol.split('.')[0].zfill(5)
            df = self._hk_spot_cache
            row = df[df['代码'] == raw_code]
            if not row.empty:
                return float(row.iloc[0]['最新价']), float(row.iloc[0]['涨跌幅'])
            return None, 0.0
        except: return None, 0.0

    def analyze_holdings_health(self, holdings_list):
        """
        [V5 核心] 持仓健康度扫描 (多线程并发)
        计算：影子净值、均线矩阵、压力位
        """
        if not holdings_list:
            return None

        results = {
            "holdings_xray": [],
            "health_metrics": {
                "total_weight_analyzed": 0.0,
                "weighted_above_ma20": 0.0,
                "weighted_above_ma60": 0.0,
                "shadow_nav_change": 0.0,
                "weighted_rsi_sum": 0.0
            }
        }

        # 并发获取每一只重仓股的数据
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_stock = {
                executor.submit(self._analyze_single_stock, stock): stock 
                for stock in holdings_list
            }

            for future in as_completed(future_to_stock):
                stock_info = future_to_stock[future]
                try:
                    data = future.result(timeout=15)
                    if data:
                        results["holdings_xray"].append(data)
                        
                        # 累加统计数据
                        w = stock_info['weight']
                        results["health_metrics"]["total_weight_analyzed"] += w
                        results["health_metrics"]["shadow_nav_change"] += data['realtime']['change_pct'] * (w / 100)
                        
                        # 均线统计
                        if data['ma_matrix']['price'] > data['ma_matrix']['ma20']:
                            results["health_metrics"]["weighted_above_ma20"] += w
                        if data['ma_matrix']['price'] > data['ma_matrix']['ma60']:
                            results["health_metrics"]["weighted_above_ma60"] += w
                            
                        # RSI 统计
                        results["health_metrics"]["weighted_rsi_sum"] += data['ma_matrix']['rsi'] * w

                except Exception as e:
                    print(f"   ⚠️ 分析股票 {stock_info['name']} ({stock_info['code']}) 失败: {e}")

        # 归一化处理
        total_w = results["health_metrics"]["total_weight_analyzed"]
        if total_w > 0:
            scale_factor = 100 / total_w if total_w < 95 else 1.0 
            results["health_metrics"]["shadow_nav_change"] *= scale_factor
            
            results["health_metrics"]["ratio_above_ma20"] = round(results["health_metrics"]["weighted_above_ma20"] / total_w, 2)
            results["health_metrics"]["ratio_above_ma60"] = round(results["health_metrics"]["weighted_above_ma60"] / total_w, 2)
            results["health_metrics"]["weighted_rsi_14"] = round(results["health_metrics"]["weighted_rsi_sum"] / total_w, 2)
        else:
            results["health_metrics"]["weighted_rsi_14"] = 50.0
        
        # 按权重排序
        results["holdings_xray"].sort(key=lambda x: x['weight'], reverse=True)
        
        return results

    def _analyze_single_stock(self, stock_info):
        """分析单只股票：获取实时价 + 计算历史均线"""
        symbol = stock_info['code']
        
        # 1. 获取实时价格
        current_price, change_pct = self.get_realtime_price(symbol)
        if current_price is None:
            return None

        # 2. 获取历史 K 线 (用于计算 MA)
        hist_data = self.get_stock_data_for_ma(symbol)
        if hist_data is None or len(hist_data) < 60:
            return {
                 "code": symbol,
                 "name": stock_info['name'],
                 "weight": stock_info['weight'],
                 "realtime": {"price": current_price, "change_pct": change_pct},
                 "ma_matrix": {"price": current_price, "ma20": 0, "ma60": 0, "rsi": 50},
                 "technical_signal": "No_History"
            }
            
        # 3. 计算技术指标
        ma_data = self._calculate_indicators(hist_data)
        latest_ma = ma_data.iloc[-1]
        
        # 4. 组装数据
        return {
            "code": symbol,
            "name": stock_info['name'],
            "weight": stock_info['weight'],
            "realtime": {
                "price": current_price,
                "change_pct": change_pct
            },
            "ma_matrix": {
                "price": current_price,
                "ma5": float(latest_ma.get('MA5', 0)),
                "ma10": float(latest_ma.get('MA10', 0)),
                "ma20": float(latest_ma.get('MA20', 0)),
                "ma60": float(latest_ma.get('MA60', 0)),
                "rsi": float(latest_ma.get('RSI', 50))
            },
            "technical_signal": self._generate_signal(current_price, latest_ma)
        }

    def get_stock_data_for_ma(self, symbol):
        """获取用于计算均线的历史数据"""
        # 优先使用 AkShare (A股/港股)
        if symbol.endswith(('.SH', '.SZ', '.BJ', '.HK')):
            return self.get_stock_data_akshare(symbol, period='6mo')
        # 美股或其他使用 YFinance
        return self.get_stock_data_yfinance(symbol, period='6mo')

    def get_stock_data_akshare(self, symbol_full, period="6mo"):
        try:
            clean_symbol = symbol_full.split('.')[0]
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=200)).strftime("%Y%m%d")
            
            df = None
            if symbol_full.endswith('.HK'):
                df = ak.stock_hk_hist(symbol=clean_symbol.zfill(5), start_date=start_date, end_date=end_date, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=clean_symbol, start_date=start_date, end_date=end_date, adjust="qfq")
            
            if df is None or df.empty: return None
            
            rename_map = {"日期": "Date", "收盘": "Close", "收盘价": "Close"}
            df = df.rename(columns=rename_map)
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            df["Close"] = pd.to_numeric(df["Close"])
            return df
        except:
            return None
            
    def get_stock_data_yfinance(self, symbol, period="6mo"):
        try:
            ticker = yf.Ticker(symbol)
            return ticker.history(period=period)
        except: return None

    def _calculate_indicators(self, df):
        """计算 MA 和 RSI"""
        if HAS_TALIB:
            df['MA5'] = talib.SMA(df['Close'], timeperiod=5)
            df['MA10'] = talib.SMA(df['Close'], timeperiod=10)
            df['MA20'] = talib.SMA(df['Close'], timeperiod=20)
            df['MA60'] = talib.SMA(df['Close'], timeperiod=60)
            df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
        else:
            # Pandas Fallback
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            # 简单的 RSI 近似算法
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
        return df

    def _generate_signal(self, price, ma_data):
        """生成简单的单股技术信号"""
        ma60 = ma_data.get('MA60', 0)
        signals = []
        
        if ma60 > 0:
            diff = (price - ma60) / ma60 * 100
            if -2 < diff < 0:
                signals.append("Near_Pressure_MA60")
            elif 0 < diff < 2:
                signals.append("Near_Support_MA60")
                
        rsi = ma_data.get('RSI', 50)
        if rsi > 70: signals.append("Overbought")
        if rsi < 30: signals.append("Oversold")
        
        return ", ".join(signals) if signals else "Neutral"