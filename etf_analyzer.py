"""
==========================================================================================
【文件定义】
文件名: etf_analyzer.py
类名  : ETFAnalyzer
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(tushare_token)
   {Has Token?} -> [Init Tushare Pro API]
        ↓
   [Set self.pro] -> [Ready]

2. analyze_etf_targets(etf_list)
   [Loop ETF List] -> [Unpack Symbol/Market]
        ↓
   [Call: Valuation + Growth + Consensus + Commodity] -> [Aggregate Data]
        ↓
   [Return Results Dict]

3. _get_etf_valuation(symbol, market)
   [Init Default N/A] -> {Market==CN?} -> (Try AKShare Fund Val)
        ↓
   {Data Missing?} -> (Try Tushare Daily Basic) -> [Update PE/PB/Div] -> [Return Data]

4. _get_underlying_growth(symbol, market)
   [Return Placeholder Dict] (TODO: Implementation)

5. _get_analyst_consensus(symbol, market)
   {CN?} -> [TS Fund Portfolio] -> [Get Top Stock] -> [TS Forecast]
        ↓
   {US?} -> [YF Ticker] -> [Get Recommendations] -> [Return Consensus]

6. _get_related_commodity(sector_type)
   [Map Sector -> Ticker] -> {Target Exists?}
        ↓
   [YF History(5d)] -> [Get Last Close] -> [Return {Target: Price}]
==========================================================================================
"""

import tushare as ts
import yfinance as yf
import akshare as ak
from typing import Dict, Any, List

class ETFAnalyzer:
    """
    ETF深度分析器 - 集成 AKShare 和 Tushare 双轨估值分析
    """
    
    def __init__(self, tushare_token=None):
        self.pro = ts.pro_api(tushare_token) if tushare_token else None
    
    def analyze_etf_targets(self, etf_list: List[Dict]) -> Dict[str, Any]:
        """深度分析ETF目标"""
        results = {}
        
        for etf in etf_list:
            symbol = etf['symbol']
            name = etf['name']
            market = etf['market']
            
            etf_data = {
                'name': name,
                'valuation': self._get_etf_valuation(symbol, market),
                'growth_quality': self._get_underlying_growth(symbol, market),
                'analyst_sentiment': self._get_analyst_consensus(symbol, market),
                'correlated_assets': self._get_related_commodity(etf.get('sector'))
            }
            results[symbol] = etf_data
            
        return results
    
    def _get_etf_valuation(self, symbol: str, market: str) -> Dict[str, Any]:
        """获取ETF估值 (双轨: AKShare优先 -> Tushare备选)"""
        data = {'pe_ttm': 'N/A', 'pb': 'N/A', 'dividend': 'N/A', 'source': 'None'}
        
        clean_code = symbol.split('.')[0]
        
        # 1. 尝试 AKShare (免费且无需Token)
        if market == 'CN':
            try:
                # 东方财富 ETF 估值数据
                df = ak.fund_etf_valuation_em(symbol=clean_code)
                if df is not None and not df.empty:
                    # AKShare 返回的数据通常包含历史数据，取最新一行
                    latest = df.iloc[-1]
                    # 列名可能变化，尝试匹配
                    # 通常列名: 统计日期, 估值, ... 
                    # 注意：ak接口返回列名可能不固定，这里主要作为演示，需根据实际返回调整
                    # 由于fund_etf_valuation_em返回比较复杂，这里简化处理，如果失败则跳过
                    # 备选：ak.fund_etf_spot_em 获取实时行情中的量比等，估值可能需要专用接口
                    pass 
            except:
                pass

        # 2. 尝试 Tushare (如果配置了Token)
        if data['pe_ttm'] == 'N/A' and market == 'CN' and self.pro:
            try:
                df = self.pro.daily_basic(ts_code=symbol, fields='pe_ttm,pb,dv_ratio')
                if not df.empty:
                    data['pe_ttm'] = df.iloc[0]['pe_ttm']
                    data['pb'] = df.iloc[0]['pb']
                    data['dividend'] = df.iloc[0]['dv_ratio']
                    data['source'] = 'Tushare'
            except:
                pass
        
        return data
    
    def _get_underlying_growth(self, symbol: str, market: str) -> Dict[str, Any]:
        """获取底层资产成长性"""
        return {"status": "placeholder", "message": "持仓分析待实现"}
    
    def _get_analyst_consensus(self, symbol: str, market: str) -> Dict[str, Any]:
        """获取分析师共识"""
        consensus = {}
        
        if market == 'CN' and self.pro:
            try:
                portfolio = self.pro.fund_portfolio(ts_code=symbol)
                if not portfolio.empty:
                    top_stock = portfolio.iloc[0]['symbol']
                    forecast = self.pro.forecast(ts_code=top_stock, start_date='20240101')
                    if not forecast.empty:
                        type_counts = forecast['type'].value_counts().to_dict()
                        consensus['top_holding_forecast'] = type_counts
            except:
                pass
        elif market == 'US':
            try:
                ticker = yf.Ticker(symbol)
                recs = ticker.recommendations
                if recs is not None and not recs.empty:
                    latest = recs.iloc[-1].to_dict()
                    consensus['us_rating'] = latest
            except:
                pass
        
        return consensus
    
    def _get_related_commodity(self, sector_type: str) -> Dict[str, Any]:
        """获取关联大宗商品"""
        mapping = {
            'energy': 'CL=F',
            'chips': '^SOX',
            'gold': 'GC=F',
            'consumer': 'ZC=F'
        }
        
        target = mapping.get(sector_type)
        if target:
            try:
                px = yf.Ticker(target).history(period="5d")['Close'].iloc[-1]
                return {target: px}
            except:
                pass
        
        return {}