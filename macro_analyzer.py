"""
==========================================================================================
【文件定义】
文件名: macro_analyzer.py
类名  : MacroAnalyzer
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__
   [初始化 FRED 映射] -> [检查并创建缓存目录]
         ↓
   [Ready]

2. _load_cache(key)
   [Check File Exists] -> [Open JSON] -> {Key Exists & Not Expired?}
         ↓
   (Yes: Return Data) / (No: Return None)

3. _save_cache(key, data)
   [Load Existing Cache] -> [Update Key with Timestamp]
         ↓
   [Dump to JSON File]

4. analyze_macro_liquidity
   [Check Cache] -> (Hit? Return)
         ↓
   [AKShare Bond Rates] -> (Get US/CN 10Y)
         ↓
   {Missing US 10Y?} -> (Fallback: Web Reader FRED)
         ↓
   [AKShare/YFinance DXY] -> (Get Dollar Index)
         ↓
   [Calc Spread (CN-US)] -> [Save Cache] -> [Return Dict]

5. analyze_cross_border_flow
   [Try AKShare North Flow Interfaces] -> {Success?}
         ↓
   [Match Column Names] -> [Extract Latest Value] -> [Return Dict]

6. analyze_indices_trend(indices_config)
   [Check Cache] -> (Hit? Return)
         ↓
   [Loop Config] -> (1. Try YFinance History)
         ↓
   {Fail?} -> (2. Try AKShare Fallback: Index/ETF) -> [Special Logic: HSTech/A50/Gold]
         ↓
   [Call _calculate_trend] -> [Aggregate Results] -> [Save Cache] -> [Return Dict]

7. _calculate_trend(hist_df)
   [Standardize Index/Columns] -> {Len < 60?} -> (Return "Insufficient")
         ↓
   [Calc MA20, MA60] -> [Compare Current vs MAs] -> [Return Trend Str]
==========================================================================================
"""

import pandas_datareader.data as web
import yfinance as yf
import akshare as ak
import pandas as pd
import numpy as np
import datetime
import os
import json
import time
from datetime import timedelta
from typing import Dict, Any

class MacroAnalyzer:
    """
    宏观数据分析器 - 集成 AKShare 双轨验证
    [V3.8 优化] 修复 HSTech 映射, 增加 ETF 替代策略
    """
    
    def __init__(self):
        self.fred_map = {
            'US_10Y': 'DGS10', 
            'US_CPI': 'CPIAUCSL'
        }
        self.cache_file = "data/cache/macro_cache.json"
        if not os.path.exists("data/cache"):
            os.makedirs("data/cache")
            
    def _load_cache(self, key):
        if not os.path.exists(self.cache_file): return None
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            if key in cache_data:
                item = cache_data[key]
                if time.time() - item.get('timestamp', 0) < 3600:
                    return item.get('data')
        except: pass
        return None

    def _save_cache(self, key, data):
        try:
            cache_data = {}
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                except: pass
            
            cache_data[key] = {'timestamp': time.time(), 'data': data}
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except: pass
    
    def analyze_macro_liquidity(self) -> Dict[str, Any]:
        cached = self._load_cache('liquidity')
        if cached:
            print("   ⚡ [缓存] 读取宏观流动性数据 (1小时内有效)...")
            return cached

        print("   ⏳ [联网] 正在分析宏观流动性 (美债/美元)...")
        data = {
            "us_10y": np.nan, "dxy": np.nan, "cn_10y": np.nan,
            "us_inflation_exp": 2.24, "spread_cn_us": "N/A"
        }
        
        try:
            try:
                df_bond = ak.bond_zh_us_rate()
                if not df_bond.empty:
                    us_col = [c for c in df_bond.columns if "10年" in c and "美国" in c]
                    if us_col: data["us_10y"] = float(df_bond.iloc[-1][us_col[0]])
                    cn_col = [c for c in df_bond.columns if "10年" in c and "中国" in c]
                    if cn_col: data["cn_10y"] = float(df_bond.iloc[-1][cn_col[0]])
            except: pass

            if np.isnan(data['us_10y']):
                try:
                    start = datetime.datetime.now() - timedelta(days=30)
                    fred = web.DataReader(['DGS10'], 'fred', start)
                    data['us_10y'] = fred['DGS10'].iloc[-1]
                except: pass

            try:
                df_dxy = ak.index_us_stock_sina(symbol=".DINI")
                if not df_dxy.empty: data["dxy"] = float(df_dxy.iloc[-1]['close'])
            except:
                try:
                    dxy = yf.Ticker("DX-Y.NYB").history(period="5d")
                    if not dxy.empty: data['dxy'] = dxy['Close'].iloc[-1]
                except: pass
            
            if isinstance(data['us_10y'], (int, float)) and isinstance(data['cn_10y'], (int, float)):
                if not np.isnan(data['us_10y']) and not np.isnan(data['cn_10y']):
                    data['spread_cn_us'] = data['cn_10y'] - data['us_10y']
            
            self._save_cache('liquidity', data)
        except Exception as e:
            data['error'] = str(e)
        
        return data

    def analyze_cross_border_flow(self) -> Dict[str, Any]:
        """分析跨境资金流"""
        flows = {}
        try:
            north_data = None
            try:
                # 尝试多个可能的接口，因为 AkShare 接口名称经常变动
                if hasattr(ak, 'stock_hsgt_north_net_flow_in_em'):
                    north_data = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
                elif hasattr(ak, 'stock_hsgt_hist_em'):
                    north_data = ak.stock_hsgt_hist_em(symbol="北向资金")
            except: pass

            if north_data is not None and not north_data.empty:
                val_col = None
                # 模糊匹配列名
                for col in ['value', '当日净流入', '净买入额', 'net_amount']:
                    if col in north_data.columns:
                        val_col = col
                        break
                
                if val_col:
                    flows['north_money'] = north_data.iloc[-1][val_col]
                else:
                    flows['north_money'] = "列名匹配失败"
            else:
                flows['north_money'] = "暂无数据"

            flows['south_money'] = "暂无数据"
            
        except Exception as e:
            flows['error'] = f"获取资金流失败: {str(e)}"
        
        return flows
    
    def analyze_indices_trend(self, indices_config: Dict[str, str]) -> Dict[str, str]:
        cached = self._load_cache('indices')
        if cached:
            print("   ⚡ [缓存] 读取主要指数趋势 (1小时内有效)...")
            for name, trend in cached.items():
                print(f"     - {name}: {trend}")
            return cached

        trends = {}
        print(f"   ⏳ [联网] 正在扫描主要指数 ({len(indices_config)}个)...")

        for name, symbol in indices_config.items():
            print(f"     正在获取 {name} ({symbol})...", end="", flush=True)
            trend_result = "N/A"
            
            # 1. YFinance
            try:
                clean_sym = symbol.replace('.SH', '.SS') if '.SH' in symbol else symbol
                hist = yf.Ticker(clean_sym).history(period="180d")
                if not hist.empty:
                    trend_result = self._calculate_trend(hist)
            except: pass
            
            # 2. AkShare Fallback
            if trend_result in ["N/A", "Data Insufficient"]:
                try:
                    ak_hist = None
                    # [Fix] 增加 HSTech 兼容 & ETF 替代
                    if name in ['HangSeng_Tech', 'HSTech']: 
                        # 方案A: 尝试指数
                        try: ak_hist = ak.stock_hk_index_daily_sina(symbol="HSTECH")
                        except: pass
                        # 方案B: 尝试 ETF (03033.HK)
                        if ak_hist is None or ak_hist.empty:
                            try: 
                                # 使用恒生科技ETF作为替代品
                                ak_hist = ak.stock_hk_hist(symbol="03033", period="daily", start_date="20240101", adjust="qfq")
                                if not ak_hist.empty:
                                    print(f" [ETF替代]", end="", flush=True)
                            except: pass

                    elif name == 'China_A50': 
                        ak_hist = ak.stock_zh_index_daily(symbol="sh000016")
                    elif 'Nasdaq' in name:
                        try: ak_hist = ak.index_us_stock_sina(symbol=".IXIC")
                        except: pass
                    elif 'SP500' in name:
                        try: ak_hist = ak.index_us_stock_sina(symbol=".INX")
                        except: pass
                    elif 'Gold' in name:
                        try: ak_hist = ak.fund_etf_hist_sina(symbol="sz159937")
                        except: pass
                    elif 'Shanghai' in name:
                         ak_hist = ak.stock_zh_index_daily(symbol="sh000001")
                    elif 'CSI300' in name:
                         ak_hist = ak.stock_zh_index_daily(symbol="sh000300")
                    elif 'HangSeng' in name:
                         try: ak_hist = ak.stock_hk_index_daily_sina(symbol="HSI")
                         except: pass

                    if ak_hist is not None and not ak_hist.empty:
                        cols = [c.lower() for c in ak_hist.columns]
                        ak_hist.columns = cols
                        if 'close' in cols: ak_hist.rename(columns={'close': 'Close'}, inplace=True)
                        elif '收盘' in cols: ak_hist.rename(columns={'收盘': 'Close'}, inplace=True)
                        trend_result = self._calculate_trend(ak_hist)
                        if trend_result not in ["N/A", "Data Insufficient"]:
                            # 如果之前没有打印过提示，这里打印
                            pass
                except: pass
            
            if trend_result in ["N/A", "Data Insufficient"]:
                print(f" -> ❌ {trend_result}")
            else:
                print(f" -> ✅ {trend_result}")
            
            trends[name] = trend_result
        
        self._save_cache('indices', trends)
        return trends

    def _calculate_trend(self, hist_df) -> str:
        try:
            if 'date' in hist_df.columns:
                hist_df['date'] = pd.to_datetime(hist_df['date'])
                hist_df.set_index('date', inplace=True)
                hist_df.sort_index(inplace=True)
            
            close_col = 'Close' if 'Close' in hist_df.columns else 'close'
            if close_col not in hist_df.columns: return "N/A"

            if len(hist_df) < 60: return "Data Insufficient"

            ma20 = hist_df[close_col].rolling(20).mean().iloc[-1]
            ma60 = hist_df[close_col].rolling(60).mean().iloc[-1]
            curr = hist_df[close_col].iloc[-1]
            
            if curr > ma20 > ma60: return "Strong Bull"
            elif curr < ma20 < ma60: return "Strong Bear"
            else: return "Consolidation"
        except: return "N/A"