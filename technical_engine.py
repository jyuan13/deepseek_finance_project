# deepseek_finance_project_V2/technical_engine.py

import yfinance as yf
import akshare as ak
import talib
import time
import random
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import re

class TechnicalEngine:
    """技术分析引擎 - 支持 YFinance 和 AkShare 双源数据获取与验证"""

    def __init__(self, request_delay=2, max_retries=3):
        # 默认延迟增加到 2 秒
        self.request_delay = request_delay
        self.max_retries = max_retries

    def set_request_delay(self, delay_seconds):
        self.request_delay = delay_seconds
        print(f"✅ 请求延迟已设置为 {delay_seconds} 秒")

    def get_stock_data_dual_source(self, symbol, period="6mo"):
        """双源数据获取与验证"""
        # 清理输入字符，防止带有空格
        symbol = symbol.strip()
        
        # 1. 获取 YFinance 数据
        yf_data = self.get_stock_data_yfinance(symbol, period)
        
        # 2. 获取 AkShare 数据
        ak_data = self.get_stock_data_akshare(symbol, period)
        
        # 3. 决策与融合
        if ak_data is not None and not ak_data.empty:
            if yf_data is not None and not yf_data.empty:
                check_result = self._compare_data_sources(symbol, yf_data, ak_data)
                return ak_data, check_result
            else:
                return ak_data, {"status": "Warning", "msg": "仅AkShare数据可用"}
        elif yf_data is not None and not yf_data.empty:
            return yf_data, {"status": "Warning", "msg": "仅YFinance数据可用 (AkShare失败)"}
        else:
            return None, {"status": "Error", "msg": "双源获取均失败"}

    def _compare_data_sources(self, symbol, yf_data, ak_data):
        try:
            yf_latest = yf_data['Close'].iloc[-1]
            ak_latest = ak_data['Close'].iloc[-1]
            diff_pct = abs(yf_latest - ak_latest) / ak_latest * 100
            
            info = {
                "yf_price": round(yf_latest, 3),
                "ak_price": round(ak_latest, 3),
                "diff_pct": round(diff_pct, 2)
            }
            if diff_pct < 1.0:
                info["status"] = "Success"
                info["msg"] = f"数据一致 (偏差{diff_pct}%)"
            else:
                info["status"] = "Divergence"
                info["msg"] = f"⚠️ 数据分歧! YF:{yf_latest} vs AK:{ak_latest}"
            return info
        except Exception as e:
            return {"status": "Error", "msg": f"对比失败: {str(e)}"}

    def get_stock_data_yfinance(self, symbol, period="1y", retry_count=0):
        """使用 yfinance 获取数据"""
        try:
            # 增加随机延迟，防止封IP
            time.sleep(random.uniform(1.0, 2.0))
            
            # --- 核心修复：HK股票代码强力适配 ---
            search_symbol = symbol.strip()
            # 如果是港股，使用正则去掉前导零，保留 .HK
            if search_symbol.endswith(".HK"):
                code_part = search_symbol.split('.')[0]
                # 去掉开头的0，例如 00700 -> 700
                new_code = code_part.lstrip('0')
                search_symbol = f"{new_code}.HK"
                # 特殊修正：如果去零后变成空（例如代码就是0.HK），则还原
                if new_code == "": search_symbol = symbol 
            
            ticker = yf.Ticker(search_symbol)
            data = ticker.history(period=period)
            
            if data is None or data.empty:
                if retry_count < self.max_retries:
                    print(f"    ⚠️ [YFinance] {search_symbol} 获取为空，重试 {retry_count+1}...")
                    time.sleep(3) # 失败后多睡一会
                    return self.get_stock_data_yfinance(symbol, period, retry_count + 1)
                return None

            return data
        except Exception as e:
            # 这里的 print 可能会被外层捕获，不打印堆栈以免刷屏
            return None

    def get_stock_data_akshare(self, symbol_full, period="6mo"):
        try:
            # 增加随机延迟
            time.sleep(random.uniform(0.5, 1.5))
            
            symbol_full = symbol_full.strip()
            clean_symbol = symbol_full.split('.')[0]
            market = symbol_full.split('.')[-1] if '.' in symbol_full else ""
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = self._get_start_date_by_period(period)
            
            df = None
            
            # 1. 尝试 ETF
            try:
                df = ak.fund_etf_hist_em(
                    symbol=clean_symbol, 
                    period="daily", 
                    start_date=start_date, 
                    end_date=end_date,
                    adjust="qfq"
                )
            except: pass
                
            # 2. 尝试 A股
            if df is None or df.empty:
                try:
                    df = ak.stock_zh_a_hist(
                        symbol=clean_symbol, 
                        period="daily", 
                        start_date=start_date, 
                        end_date=end_date,
                        adjust="qfq"
                    )
                except: pass
            
            # 3. 尝试 港股
            if (df is None or df.empty) and market == 'HK':
                try:
                    # AkShare 港股通常需要 5 位
                    hk_symbol = clean_symbol.zfill(5)
                    df = ak.stock_hk_hist(
                        symbol=hk_symbol,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"
                    )
                except: pass

            if df is None or df.empty: return None
                
            rename_map = {
                "日期": "Date", "收盘": "Close", "开盘": "Open", 
                "最高": "High", "最低": "Low", "成交量": "Volume",
                "收盘价": "Close", "开盘价": "Open", "最高价": "High", "最低价": "Low"
            }
            df = df.rename(columns=rename_map)
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            for col in ["Close", "Open", "High", "Low", "Volume"]:
                if col in df.columns: df[col] = pd.to_numeric(df[col])
            
            return df
        except:
            return None

    def _get_start_date_by_period(self, period):
        now = datetime.now()
        days_map = {'1mo': 30, '3mo': 90, '6mo': 180, '1y': 365}
        delta = timedelta(days=days_map.get(period, 180))
        return (now - delta).strftime("%Y%m%d")

    def get_multiple_periods_data(self, symbol):
        periods = {'1mo': '1个月', '3mo': '3个月', '6mo': '6个月', '1y': '1年'}
        all_data = {}
        print(f"🔄 正在双源获取 {symbol} 多周期数据...")
        
        for period_code, period_name in periods.items():
            data, source_info = self.get_stock_data_dual_source(symbol, period_code)
            if data is not None and not data.empty:
                technical_data = self.calculate_technical_indicators(data)
                if technical_data is not None:
                    all_data[period_code] = {
                        'raw': data,
                        'technical': technical_data,
                        'name': period_name,
                        'source_info': source_info
                    }
        
        # 只要能获取到一个周期就算成功
        if all_data:
            print(f"✅ 成功准备好 {len(all_data)} 个周期的数据")
            return all_data
        else:
            print("❌ 无法获取任何周期的数据")
            return None

    def calculate_technical_indicators(self, data):
        if data is None or data.empty: return None
        df = data.copy()
        try:
            df['SMA_5'] = talib.SMA(df['Close'], timeperiod=5)
            df['SMA_10'] = talib.SMA(df['Close'], timeperiod=10)
            df['SMA_20'] = talib.SMA(df['Close'], timeperiod=20)
            df['SMA_60'] = talib.SMA(df['Close'], timeperiod=60)
            df['SMA_200'] = talib.SMA(df['Close'], timeperiod=200)
            df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
            df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(df['Close'])
            return df
        except: return None

    def analyze_ma_trend(self, latest_data):
        trends = []
        # 简化的趋势判断
        if all(k in latest_data for k in ['SMA_5', 'SMA_10', 'SMA_20']) and not pd.isna(latest_data['SMA_20']):
            if latest_data['SMA_5'] > latest_data['SMA_10'] > latest_data['SMA_20']:
                trends.append("✅ **多头排列** (5>10>20)")
            elif latest_data['SMA_5'] < latest_data['SMA_10'] < latest_data['SMA_20']:
                trends.append("❌ **空头排列** (5<10<20)")
        
        key_mas = [('SMA_20', '20日'), ('SMA_60', '60日'), ('SMA_200', '200日')]
        for ma_key, ma_name in key_mas:
            if ma_key in latest_data and not pd.isna(latest_data[ma_key]):
                if latest_data['Close'] > latest_data[ma_key]:
                    trends.append(f"📈 **站稳{ma_name}线**")
                else:
                    trends.append(f"📉 **跌破{ma_name}线**")
        return "\n".join(trends) if trends else "数据不足"

    # 其他辅助方法保持空或简单实现
    def validate_stock_symbol(self, symbol): return True
    def display_raw_data(self, data, symbol): pass
    def get_ma_analysis_for_period(self, latest_data): return ""
    def plot_technical_analysis(self, data, symbol, period_name): return True