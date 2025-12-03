# deepseek_finance_project_V3/macro_analyzer.py

import pandas_datareader.data as web
import yfinance as yf
import akshare as ak
import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
from typing import Dict, Any

class MacroAnalyzer:
    """
    宏观数据分析器 - 集成 AKShare 双轨验证
    [V3.4 优化] 增加详细进度打印，防止 YFinance 阻塞时用户以为死机
    """
    
    def __init__(self):
        self.fred_map = {
            'US_10Y': 'DGS10', 
            'US_CPI': 'CPIAUCSL'
        }
    
    def analyze_macro_liquidity(self) -> Dict[str, Any]:
        """分析宏观流动性"""
        print("   ⏳ 正在分析宏观流动性 (美债/美元)...")
        data = {
            "us_10y": np.nan,
            "dxy": np.nan,
            "cn_10y": np.nan,
            "us_inflation_exp": 2.24,  # 静态预设值
            "spread_cn_us": "N/A"
        }
        
        try:
            # 1. 美债 10年期收益率 (优先 AkShare)
            try:
                # bond_zh_us_rate 返回: 日期, 中国国债, 美国国债...
                df_bond = ak.bond_zh_us_rate()
                if not df_bond.empty:
                    us_col = [c for c in df_bond.columns if "10年" in c and "美国" in c]
                    if us_col:
                        data["us_10y"] = float(df_bond.iloc[-1][us_col[0]])
                    
                    cn_col = [c for c in df_bond.columns if "10年" in c and "中国" in c]
                    if cn_col:
                        data["cn_10y"] = float(df_bond.iloc[-1][cn_col[0]])
            except Exception as e:
                print(f"   ⚠️ AkShare 宏观数据获取部分失败: {e}")

            # 2. 如果 AkShare 没拿到美债，尝试 FRED
            if np.isnan(data['us_10y']):
                try:
                    start = datetime.datetime.now() - timedelta(days=30)
                    fred = web.DataReader(['DGS10'], 'fred', start)
                    data['us_10y'] = fred['DGS10'].iloc[-1]
                except: pass

            # 3. 美元指数 (DXY)
            try:
                df_dxy = ak.index_us_stock_sina(symbol=".DINI")
                if not df_dxy.empty:
                    data["dxy"] = float(df_dxy.iloc[-1]['close'])
            except:
                try:
                    dxy = yf.Ticker("DX-Y.NYB").history(period="5d")
                    if not dxy.empty:
                        data['dxy'] = dxy['Close'].iloc[-1]
                except: pass
            
            # 4. 计算利差
            if isinstance(data['us_10y'], (int, float)) and isinstance(data['cn_10y'], (int, float)):
                if not np.isnan(data['us_10y']) and not np.isnan(data['cn_10y']):
                    data['spread_cn_us'] = data['cn_10y'] - data['us_10y']
                
        except Exception as e:
            data['error'] = str(e)
        
        return data
    
    def analyze_cross_border_flow(self) -> Dict[str, Any]:
        """分析跨境资金流"""
        flows = {}
        try:
            north_data = None
            try:
                if hasattr(ak, 'stock_hsgt_north_net_flow_in_em'):
                    north_data = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
                elif hasattr(ak, 'stock_hsgt_hist_em'):
                    north_data = ak.stock_hsgt_hist_em(symbol="北向资金")
            except: pass

            if north_data is not None and not north_data.empty:
                val_col = None
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
        """
        分析主要指数趋势 (双轨制: YFinance + AKShare)
        """
        trends = {}
        
        for name, symbol in indices_config.items():
            # [V3.4 新增] 打印当前处理进度
            print(f"   ⏳ 正在获取 {name} ({symbol})...")
            
            trend_result = "N/A"
            
            # 1. 优先尝试 YFinance
            try:
                clean_sym = symbol.replace('.SH', '.SS') if '.SH' in symbol else symbol
                hist = yf.Ticker(clean_sym).history(period="180d")
                if not hist.empty:
                    trend_result = self._calculate_trend(hist)
            except:
                pass
            
            # 2. 如果失败，尝试 AKShare 兜底
            if trend_result in ["N/A", "Data Insufficient"]:
                # print(f"      ⚠️ YFinance 数据不足，尝试 AkShare 修复 {name}...")
                try:
                    ak_hist = None
                    if name == 'China_A50': 
                        ak_hist = ak.stock_zh_index_daily(symbol="sh000016")
                    elif name == 'HangSeng_Tech': 
                        try:
                            ak_hist = ak.stock_hk_index_daily_sina(symbol="HSTECH")
                        except: pass
                    elif 'Nasdaq' in name:
                        try:
                            ak_hist = ak.index_us_stock_sina(symbol=".IXIC")
                        except: pass
                    elif 'SP500' in name:
                        try:
                            ak_hist = ak.index_us_stock_sina(symbol=".INX")
                        except: pass
                    elif 'Gold' in name:
                        try:
                            # 黄金ETF作为近似替代
                            ak_hist = ak.fund_etf_hist_sina(symbol="sz159937")
                        except: pass
                    
                    if ak_hist is not None and not ak_hist.empty:
                        cols = [c.lower() for c in ak_hist.columns]
                        ak_hist.columns = cols
                        if 'close' in cols:
                            ak_hist.rename(columns={'close': 'Close'}, inplace=True)
                        elif '收盘' in cols:
                            ak_hist.rename(columns={'收盘': 'Close'}, inplace=True)
                            
                        trend_result = self._calculate_trend(ak_hist)
                        if trend_result not in ["N/A", "Data Insufficient"]:
                            print(f"      ℹ️ {name} 使用 AKShare 数据修复成功")
                except Exception as e:
                    pass
            
            trends[name] = trend_result
        
        return trends

    def _calculate_trend(self, hist_df) -> str:
        """计算趋势的辅助函数"""
        try:
            if 'date' in hist_df.columns:
                hist_df['date'] = pd.to_datetime(hist_df['date'])
                hist_df.set_index('date', inplace=True)
                hist_df.sort_index(inplace=True)
            
            close_col = 'Close' if 'Close' in hist_df.columns else 'close'
            if close_col not in hist_df.columns: return "N/A"

            if len(hist_df) < 60:
                return "Data Insufficient"

            ma20 = hist_df[close_col].rolling(20).mean().iloc[-1]
            ma60 = hist_df[close_col].rolling(60).mean().iloc[-1]
            curr = hist_df[close_col].iloc[-1]
            
            if curr > ma20 > ma60:
                return "Strong Bull"
            elif curr < ma20 < ma60:
                return "Strong Bear"
            else:
                return "Consolidation"
        except:
            return "N/A"