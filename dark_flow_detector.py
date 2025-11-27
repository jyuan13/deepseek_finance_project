# deepseek_finance_project_V2/dark_flow_detector.py

import akshare as ak
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import time # 引入time
import random
from typing import Dict, Any, Optional, List 

class DarkFlowDetector:
    """
    暗流探测器 - 筹码分布 + 做空数据分析
    """
    
    def __init__(self):
        pass

    def analyze_dark_flow(self, symbol: str, market: str, **kwargs) -> Dict[str, Any]:
        """
        统一入口：分析暗流数据
        """
        result = {
            "symbol": symbol,
            "market": market,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 增加随机延迟，模拟人类操作，防止封IP
        time.sleep(random.uniform(2.0, 4.0))
        
        if market == 'CN':
            result.update(self._analyze_cn_chip_distribution(symbol, **kwargs))
        elif market == 'US':
            result.update(self._analyze_us_short_interest(symbol, **kwargs))
        elif market == 'HK':
            result.update(self._analyze_hk_market(symbol, **kwargs))
            
        return result

    # ... (中间代码保持不变，直到 analyze_etf_holdings 方法) ...
    
    def _analyze_cn_chip_distribution(self, symbol: str, **kwargs) -> Dict[str, Any]:
        # ... (保持原样) ...
        data = {
            'metric': 'Chip_Distribution',
            'winner_rate': None,
            'avg_cost': None,
            'current_price': None,
            'signal': 'Neutral',
            'desc': '数据获取中...'
        }
        
        try:
            clean_symbol = symbol.split('.')[0]
            # ... (保持原样) ...
            try:
                # 尝试多种筹码分布接口
                cyq_data = self._get_chip_data(clean_symbol)
                
                if cyq_data and not cyq_data.empty:
                    # 计算获利盘比例
                    # ...
                    # (此处代码省略，保持原样，仅为了上下文)
                    pass
                else:
                    data['error'] = "无法获取筹码分布数据"
            except Exception as e:
                data['error'] = f"筹码分析失败: {str(e)}"
        except Exception as e:
            data['error'] = f"A股分析失败: {str(e)}"
            
        return data

    def _get_chip_data(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            return ak.stock_cyq_em(symbol=symbol)
        except:
            return None

    def _calculate_winner_rate(self, chip_data: pd.DataFrame, current_price: float) -> float:
        try:
            if '获利比例' in chip_data.columns:
                return float(chip_data['获利比例'].iloc[-1])
            return 50.0
        except:
            return 50.0

    def _analyze_us_short_interest(self, symbol: str, **kwargs) -> Dict[str, Any]:
        # ... (保持原样) ...
        return {'signal': 'Neutral', 'desc': '暂无数据'}

    def _analyze_hk_market(self, symbol: str, **kwargs) -> Dict[str, Any]:
        return {'metric': 'HK_Market_Analysis', 'signal': 'Neutral', 'desc': '港股分析待完善'}

    def analyze_etf_holdings(self, etf_holdings: List[Dict]) -> Dict[str, Any]:
        """
        分析ETF重仓股的暗流数据
        """
        results = {}
        
        # 限制只分析前3大重仓股，减少请求次数防止封IP
        for holding in etf_holdings[:3]: 
            symbol = holding.get('symbol')
            market = holding.get('market', 'CN')
            name = holding.get('name', 'Unknown')
            
            if symbol:
                print(f"🔍 分析重仓股暗流: {name}({symbol})...")
                # 这里调用 analyze_dark_flow，里面已经加了 sleep
                results[symbol] = self.analyze_dark_flow(symbol, market)
        
        overall_signal = self._generate_overall_signal(results)
        results['overall'] = overall_signal
        
        return results

    def _generate_overall_signal(self, individual_results: Dict) -> Dict[str, Any]:
        # ... (保持原样) ...
        return {'signal': 'NEUTRAL', 'desc': '数据不足'}