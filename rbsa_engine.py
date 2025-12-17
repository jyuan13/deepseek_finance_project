"""
==========================================================================================
【文件定义】
文件名: rbsa_engine.py
类名  : RBSAEngine
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(data_manager)
   [接收 DB Manager] -> [初始化基准因子 (NASDAQ/SP500/HSI/CSI300/GOLD)]
         ↓
   [Ready]

2. analyze_style(fund_code, lookback_days)
   [DB Get Fund NAV] -> {Len < 30?} -> (Return {})
         ↓
   [Calc Fund Pct Change] -> [Loop Factors: Get Market Data] -> [Calc Factor Pct Change]
         ↓
   [Merge Data (Outer Join)] -> [FillNA (0)] -> (Fix Holiday Bias)
         ↓
   [Lasso Regression (Positive Constraint)] -> [Get Coefficients]
         ↓
   [Normalize Weights] -> [Filter Noise (<5%)] -> [Return Weights Dict]
==========================================================================================
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Lasso
from datetime import datetime, timedelta

class RBSAEngine:
    """
    [V3.9 风格侦探] Based on Return-Based Style Analysis
    修复: 解决中美交易日历不一致导致的数据丢失问题 (Survivorship Bias)
    """
    
    def __init__(self, data_manager):
        self.db = data_manager
        # 使用 A 股上市的 QDII ETF 作为基准
        self.factors = {
            "513100": "纳斯达克100",
            "513500": "标普500",
            "513180": "恒生科技",
            "510300": "沪深300",
            "518880": "黄金ETF"
        }

    def analyze_style(self, fund_code, lookback_days=60):
        print(f"🕵️ [RBSA] 正在侦测基金 {fund_code} 的真实持仓风格...")
        try:
            # 1. 获取基金净值收益率
            fund_df = self.db.get_fund_nav(fund_code, limit=lookback_days + 20)
            if len(fund_df) < 30:
                print(f"   ⚠️ 基金 {fund_code} 历史数据不足，跳过")
                return {}
            
            fund_series = fund_df.sort_values('date').set_index('date')['nav']
            fund_pct = fund_series.pct_change().dropna()
            fund_pct.name = "Fund"

            # 2. 获取基准指数
            factor_data = {}
            for code, name in self.factors.items():
                idx_df = self.db.get_market_data(code, start_date=fund_pct.index[0].strftime("%Y-%m-%d"))
                if not idx_df.empty:
                    idx_series = idx_df.sort_values('date').set_index('date')['close']
                    factor_data[name] = idx_series.pct_change().dropna()
            
            if not factor_data:
                return {}

            # 3. [V3.9 关键修复] 数据对齐 - 使用 Outer Join 防止数据丢失
            df_factors = pd.DataFrame(factor_data)
            # 使用 outer join 保留所有日期
            df_merged = pd.concat([fund_pct, df_factors], axis=1, join='outer')
            
            # 填补缺失值 (处理中美节假日)
            # 策略: 前值填充 (ffill) -> 0值填充 (fillna(0))
            # 意思是: 这一天休市没涨跌，就当做 0% 波动，而不是丢弃这一天
            df_merged = df_merged.fillna(0)
            
            # 再次检查长度
            if len(df_merged) < 20:
                return {}

            X = df_merged[list(factor_data.keys())]
            y = df_merged["Fund"]

            # 4. Lasso 回归
            lasso = Lasso(alpha=0.001, positive=True, fit_intercept=True, max_iter=5000)
            lasso.fit(X, y)
            
            raw_weights = dict(zip(X.columns, lasso.coef_))
            
            # 5. 归一化
            total_w = sum(raw_weights.values())
            final_weights = {}
            if total_w > 0.01:
                for name, w in raw_weights.items():
                    normalized_w = w / total_w
                    if normalized_w > 0.05: # 忽略 < 5% 的噪音
                        final_weights[name] = round(normalized_w, 2)
            
            score = lasso.score(X, y)
            print(f"   ✅ RBSA 分析完成 (R²={score:.2f}): {final_weights}")
            return final_weights

        except Exception as e:
            print(f"❌ RBSA 分析异常: {e}")
            return {}

if __name__ == "__main__":
    pass