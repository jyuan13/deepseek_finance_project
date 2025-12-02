# deepseek_finance_project_V3/shadow_engine.py

import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class ShadowEngine:
    """
    [V3.9 影子净值引擎]
    升级: 使用 Snapshot 机制彻底解决 Cold Start 问题。
    核心公式: Est_NAV_Chg = (Sum(Stock_Chg * Weight) / Total_Monitored_Weight) * Correction
    """
    
    def __init__(self, fund_data_manager, rbsa_engine):
        self.fdm = fund_data_manager
        self.rbsa = rbsa_engine

    def _fetch_stock_change(self, stock):
        """单个股票涨跌幅获取任务 (Snapshot Mode)"""
        symbol = stock['stock_code']
        weight = float(stock['weight'])
        
        # [V3.9] 直接获取快照，包含现价和昨收
        snapshot, valid = self.fdm.get_realtime_snapshot(symbol)
        
        if not valid or not snapshot:
            return None
            
        current_price = snapshot['price']
        prev_close = snapshot['prev_close']
        
        if prev_close <= 0: return None
        
        # 实时计算涨跌幅，无需查询历史库
        pct_chg = ((current_price - prev_close) / prev_close) * 100
        
        return {
            "name": stock['stock_name'],
            "weight": weight,
            "pct_chg": pct_chg
        }

    def calc_realtime_nav(self, fund_code, fund_holdings):
        """
        计算实时估算净值涨跌幅 (并发版)
        """
        if not fund_holdings:
            return 0.0, "❌ 数据缺失: 无持仓信息"

        total_monitored_weight = 0.0
        weighted_change_sum = 0.0
        details = []
        
        print(f"   📊 正在计算 {fund_code} 影子净值 (并发快照扫描 {len(fund_holdings)} 只重仓股)...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._fetch_stock_change, stock) for stock in fund_holdings]
            
            for future in as_completed(futures):
                res = future.result()
                if res:
                    weighted_change_sum += res['pct_chg'] * res['weight']
                    total_monitored_weight += res['weight']
                    # details.append(f"{res['name']}:{res['pct_chg']:.1f}%")

        if total_monitored_weight == 0:
            return 0.0, "❌ 数据缺失: 无法获取行情快照"

        # [V3.9] 动态归一化与置信度检查
        stock_portion_change = weighted_change_sum / total_monitored_weight
        
        # 动态修正系数
        exposure_factor = 0.85 
        confidence_level = "High"
        
        if total_monitored_weight < 30: 
            exposure_factor = 0.6 
            confidence_level = "LOW (Sample<30%)"
        elif total_monitored_weight > 80: 
            exposure_factor = 0.95 
            confidence_level = "Very High"
            
        final_change = stock_portion_change * exposure_factor
        
        basis_msg = f"监控仓位 {total_monitored_weight:.1f}%, 修正系数 {exposure_factor}, 置信度: {confidence_level}"
        return round(final_change, 2), basis_msg