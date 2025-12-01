# deepseek_finance_project_V2/fund_data_manager.py

import akshare as ak
import pandas as pd
from datetime import datetime
import re

class FundDataManager:
    """
    V5 核心组件：基金数据管理器
    负责获取基金基本信息、持仓结构、实时估值等
    """

    def __init__(self):
        pass

    def get_fund_basic_info(self, fund_code):
        """获取基金基本信息（名称、类型、规模）"""
        try:
            # 尝试从通用接口获取名称
            df = ak.fund_name_em()
            row = df[df['基金代码'] == fund_code]
            
            if not row.empty:
                return {
                    "code": fund_code,
                    "name": row.iloc[0]['基金简称'],
                    "type": row.iloc[0]['基金类型']
                }
            return {"code": fund_code, "name": "未知基金", "type": "未知"}
        except Exception as e:
            print(f"❌ 获取基金基础信息失败: {e}")
            return {"code": fund_code, "name": "未知基金", "type": "Error"}

    def get_top_holdings(self, fund_code, year=None):
        """
        [核心] 获取基金前十大重仓股
        """
        if year is None:
            year = str(datetime.now().year)
            
        try:
            # 获取持仓数据
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
            if df is None or df.empty:
                # 尝试获取去年的（可能年初还没出年报）
                prev_year = str(int(year) - 1)
                df = ak.fund_portfolio_hold_em(symbol=fund_code, date=prev_year)
            
            if df is None or df.empty:
                return []

            # 提取最新季度的数据
            latest_quarter = df['季度'].iloc[0]
            quarter_data = df[df['季度'] == latest_quarter].head(10) # 取前10

            holdings = []
            for _, row in quarter_data.iterrows():
                raw_code = str(row['股票代码'])
                raw_name = str(row['股票名称'])
                
                # [关键] 智能代码对齐
                clean_code = self._align_stock_code(raw_code, raw_name)
                
                holdings.append({
                    "code": clean_code,
                    "name": raw_name,
                    "weight": float(row['占净值比例']),
                    "raw_code": raw_code
                })
            
            return holdings
        except Exception as e:
            print(f"⚠️ 无法获取持仓数据 ({fund_code}): {e}")
            return []

    def _align_stock_code(self, code, name):
        """
        智能识别股票市场并添加后缀
        """
        code = code.strip()
        
        # 港股 (5位数字)
        if len(code) == 5 and code.isdigit():
            return f"{code}.HK"
            
        # A股 (6位数字)
        if len(code) == 6 and code.isdigit():
            if code.startswith(('60', '68')):
                return f"{code}.SH"
            if code.startswith(('00', '30')):
                return f"{code}.SZ"
            # 北交所
            if code.startswith(('4', '8')): 
                return f"{code}.BJ"
                
        # 美股 (字母)
        if re.match(r'^[A-Za-z]+$', code):
            return code # yfinance 格式通常直接是字母
            
        return code