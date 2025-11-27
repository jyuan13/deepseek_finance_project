# deepseek_finance_project_V2/macro_analyzer.py

import pandas_datareader.data as web
import yfinance as yf
import akshare as ak
import datetime
from datetime import timedelta
from typing import Dict, Any

class MacroAnalyzer:
    """
    宏观数据分析器 - 集成 AKShare 双轨验证
    """
    
    def __init__(self):
        self.fred_map = {
            'US_10Y': 'DGS10', 
            'US_CPI': 'CPIAUCSL'
        }
    
    def analyze_macro_liquidity(self) -> Dict[str, Any]:
        """分析宏观流动性"""
        data = {}
        try:
            # 1. 美债与通胀 (FRED)
            try:
                start = datetime.datetime.now() - timedelta(days=365)
                fred = web.DataReader(['DGS10', 'T10YIE'], 'fred', start)
                data['us_10y'] = fred['DGS10'].iloc[-1]
                data['us_inflation_exp'] = fred['T10YIE'].iloc[-1]
            except:
                data['us_10y'] = "N/A"
                data['us_inflation_exp'] = "N/A"
            
            # 2. 汇率 (YFinance)
            try:
                dxy = yf.Ticker("DX-Y.NYB").history(period="5d")
                data['dxy'] = dxy['Close'].iloc[-1]
            except:
                data['dxy'] = "N/A"
            
            # 3. 中国国债 (AKShare)
            try:
                cn_bond = ak.bond_zh_us_rate()
                data['cn_10y'] = cn_bond['中国国债收益率10年'].iloc[-1]
                # 计算利差
                if isinstance(data['us_10y'], (int, float)):
                    data['spread_cn_us'] = data['cn_10y'] - data['us_10y']
                else:
                    data['spread_cn_us'] = "N/A"
            except:
                data['cn_10y'] = "N/A"
                
        except Exception as e:
            data['error'] = str(e)
        
        return data
    
    def analyze_cross_border_flow(self) -> Dict[str, Any]:
        """分析跨境资金流"""
        flows = {}
        try:
            # 北向资金 (AKShare)
            north_data = None
            try:
                if hasattr(ak, 'stock_hsgt_north_net_flow_in_em'):
                    north_data = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")
                elif hasattr(ak, 'stock_hsgt_hist_em'):
                    north_data = ak.stock_hsgt_hist_em(symbol="北向资金")
            except: pass

            if north_data is not None and not north_data.empty:
                # --- 修改为更精确的查找，防止误读股票代码列 ---
                val_col = None
                # 优先找我们要的资金列名
                for col in ['value', '当日净流入', '净买入额', 'net_amount']:
                    if col in north_data.columns:
                        val_col = col
                        break
                
                if val_col:
                    flows['north_money'] = north_data.iloc[-1][val_col]
                else:
                    # 如果找不到明确的资金列，宁可显示报错也不要瞎猜最后一列（因为最后一列可能是代码）
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
            trend_result = "N/A"
            
            # 1. 优先尝试 YFinance
            try:
                clean_sym = symbol.replace('.SH', '.SS') if '.SH' in symbol else symbol
                hist = yf.Ticker(clean_sym).history(period="60d")
                if not hist.empty:
                    trend_result = self._calculate_trend(hist)
            except:
                pass
            
            # 2. 如果失败，且是特定指数，尝试 AKShare 兜底
            if trend_result == "N/A":
                try:
                    ak_hist = None
                    if name == 'China_A50': # 000016
                        ak_hist = ak.stock_zh_index_daily(symbol="sh000016")
                    elif name == 'HangSeng_Tech': # 恒生科技
                        # 恒生科技指数 AKShare 可能需要特定接口，这里用恒生指数作为近似测试
                        # 或者尝试新浪接口
                        ak_hist = ak.stock_hk_index_daily_sina(symbol="HSTECH")
                    
                    if ak_hist is not None and not ak_hist.empty:
                        # 统一列名
                        ak_hist.rename(columns={'close': 'Close'}, inplace=True)
                        trend_result = self._calculate_trend(ak_hist)
                        print(f"    ℹ️ {name} 使用 AKShare 数据修复成功")
                except:
                    pass
            
            trends[name] = trend_result
        
        return trends

    def _calculate_trend(self, hist_df) -> str:
        """计算趋势的辅助函数"""
        try:
            # 确保按日期排序
            if 'date' in hist_df.columns:
                hist_df.set_index('date', inplace=True)
            
            # 确保列名正确 (AkShare返回可能是小写)
            close_col = 'Close' if 'Close' in hist_df.columns else 'close'
            if close_col not in hist_df.columns: return "N/A"

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