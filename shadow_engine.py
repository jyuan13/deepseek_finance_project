"""
==========================================================================================
【文件定义】
文件名: shadow_engine.py
类名  : ShadowEngine
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(fund_data_manager, rbsa_engine)
   [依赖注入] -> [赋值 self.fdm, self.rbsa]
         ↓
   [Ready]

2. _fetch_stock_change(stock)
   [FDM 获取实时快照] -> {Valid?} -> (No: Return FAIL)
         ↓
   [Calc Pct Change] -> [Return Name/Weight/Chg/Source/Status]

3. calc_realtime_nav(fund_code, fund_holdings)
   {Empty Holdings?} -> (Return 0.0)
         ↓
   [ThreadPoolExecutor] -> [并发提交 _fetch_stock_change]
         ↓
   [Loop Futures] -> [Collect Results] -> [Accumulate Weighted Sum]
         ↓
   [Print Detailed List] -> [Calc Average Change]
         ↓
   [Apply Correction Factor (0.6/0.85/0.95)] -> [Return Final Change, Basis Msg]
==========================================================================================
"""

import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class ShadowEngine:
    """
    [V3.18 影子净值引擎]
    升级: 增加详细的成功/失败清单打印，优化置信度计算
    核心公式: Est_NAV_Chg = (Sum(Stock_Chg * Weight) / Total_Monitored_Weight) * Correction
    """
    
    def __init__(self, fund_data_manager, rbsa_engine):
        self.fdm = fund_data_manager
        self.rbsa = rbsa_engine

    def _fetch_stock_change(self, stock):
        """单个股票涨跌幅获取任务 (Snapshot Mode)"""
        symbol = stock['stock_code']
        weight = float(stock['weight'])
        
        snapshot, valid = self.fdm.get_realtime_snapshot(symbol)
        
        if not valid or not snapshot:
            return {
                "name": stock['stock_name'],
                "weight": weight,
                "status": "FAIL",
                "source": "-"
            }
            
        current_price = snapshot['price']
        prev_close = snapshot['prev_close']
        source = snapshot.get('source', 'Unknown')
        
        if prev_close <= 0:
            return {
                "name": stock['stock_name'],
                "weight": weight,
                "status": "FAIL",
                "source": source
            }
        
        pct_chg = ((current_price - prev_close) / prev_close) * 100
        
        return {
            "name": stock['stock_name'],
            "weight": weight,
            "pct_chg": pct_chg,
            "status": "SUCCESS",
            "source": source
        }

    def calc_realtime_nav(self, fund_code, fund_holdings):
        """
        计算实时估算净值涨跌幅 (并发版)
        """
        if not fund_holdings:
            return 0.0, "❌ 数据缺失: 无持仓信息"

        total_monitored_weight = 0.0
        weighted_change_sum = 0.0
        results_list = []
        
        print(f"   📊 正在计算 {fund_code} 影子净值 (扫描 {len(fund_holdings)} 只重仓股)...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self._fetch_stock_change, stock) for stock in fund_holdings]
            
            for future in as_completed(futures):
                res = future.result()
                results_list.append(res)
                
                if res['status'] == 'SUCCESS':
                    weighted_change_sum += res['pct_chg'] * res['weight']
                    total_monitored_weight += res['weight']

        # [V3.18] 打印详细清单
        print(f"\n   📋 成分股行情获取清单:")
        print(f"   {'名称':<10} | {'来源':<10} | {'涨跌幅':<8} | {'状态'}")
        print("   " + "-"*45)
        for r in results_list[:10]: # 只打印前10个避免刷屏
            chg_str = f"{r.get('pct_chg', 0.0):.2f}%" if r['status']=='SUCCESS' else "-"
            print(f"   {r['name'][:8]:<10} | {r['source']:<10} | {chg_str:<8} | {r['status']}")
        if len(results_list) > 10:
            print(f"   ... (共 {len(results_list)} 只)")

        if total_monitored_weight == 0:
            return 0.0, "❌ 数据缺失: 无法获取任何成分股行情"

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