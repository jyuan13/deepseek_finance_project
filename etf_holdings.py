"""
==========================================================================================
【文件定义】
文件名: etf_holdings_manager.py
类名  : ETFHoldingsManager
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__
   [初始化静态配置字典] -> {预设 513120/513180/512890/159995 持仓}
         ↓
   [实例初始化完成 (作为兜底数据)]

2. get_holdings(etf_symbol)
   [接收 ETF 代码] -> {字典中存在 key?}
         ↓
   (Yes: 返回持仓 Dict) / (No: 返回空 Dict)

3. update_holdings_dynamic(etf_symbol)
   [代码清洗] -> [随机 Sleep] -> [调用 ak.fund_portfolio_em]
         ↓
   {数据有效?} -> [取前10重仓] -> [格式化子代码] -> [更新 self.config] -> [Return True/False]

4. _format_code(raw_code)
   {Len=5?} -> (.HK)
         ↓
   {Len=6?} -> (Prefix 6/5/9 -> .SS) / (Prefix 0/1/3 -> .SZ) -> [Return Code]

5. add_holding(etf_symbol, stock_symbol, weight)
   {ETF Key Exists?} -> (No: Init Dict) -> [Set Stock Weight]
         ↓
   [Print Success Msg]

6. remove_holding(etf_symbol, stock_symbol)
   {ETF Key Exists?} -> {Stock Key Exists?}
         ↓
   [Del Config Item]

7. show_holdings(etf_symbol)
   [Call get_holdings] -> {Has Data?} -> (No: Print Error)
         ↓
   [Sort by Weight Desc] -> [Loop Print Items] -> [Calc & Print Total]
==========================================================================================
"""

import akshare as ak
import time
import random

class ETFHoldingsManager:
    """ETF持仓管理器 - 支持静态配置与动态更新"""
    
    def __init__(self):
        # 静态兜底配置 (当网络获取失败时使用)
        self.etf_holdings_config = {
            "513120.SS": {  # 港股创新药ETF
                "1801.HK": 9.5, "6160.HK": 9.2, "2269.HK": 9.1, "9926.HK": 9.1, "1177.HK": 8.2,
                "1093.HK": 6.7, "1530.HK": 5.2, "2359.HK": 4.8, "3692.HK": 3.8, "6990.HK": 3.7
            },
            "513180.SS": {  # 恒生科技指数ETF
                "00700.HK": 10.2, "09988.HK": 9.8, "03690.HK": 9.5, "09888.HK": 8.2, "09618.HK": 7.8,
                "09999.HK": 6.5, "02020.HK": 5.8, "09626.HK": 5.2, "09868.HK": 4.8, "09866.HK": 4.2
            },
            "512890.SS": {  # 红利低波ETF
                "601318.SS": 8.5, "601288.SS": 7.8, "601328.SS": 7.2, "601398.SS": 6.8, "601988.SS": 6.5,
                "600036.SS": 5.8, "601166.SS": 5.2, "600000.SS": 4.8, "601818.SS": 4.5, "601169.SS": 4.2
            },
            "159995.SZ": {  # 芯片ETF
                "603986.SS": 9.2, "688981.SS": 8.8, "002049.SZ": 8.2, "603501.SS": 7.5, "688008.SS": 7.2,
                "002371.SZ": 6.8, "603290.SS": 6.2, "688126.SS": 5.8, "300661.SZ": 5.5, "688521.SS": 5.2
            }
        }
    
    def get_holdings(self, etf_symbol):
        """获取ETF的持仓配置"""
        # 在获取前，尝试动态更新一次（可选，或者由外部控制）
        # 这里为了性能，默认直接返回，建议在分析流程开始前显式调用 update_holdings_dynamic
        return self.etf_holdings_config.get(etf_symbol, {})
    
    def update_holdings_dynamic(self, etf_symbol):
        """
        [AKShare双轨] 尝试从网络动态更新ETF持仓
        """
        clean_code = etf_symbol.split('.')[0]
        print(f"🌍 [持仓更新] 正在尝试从 AKShare 获取 {etf_symbol} 的最新持仓...")
        
        try:
            # 增加延迟防止封IP
            time.sleep(random.uniform(1.0, 2.0))
            
            # 使用 AKShare 基金持仓接口
            # 注意：fund_portfolio_em 适用于场内ETF/LOF等
            df = ak.fund_portfolio_em(symbol=clean_code)
            
            if df is not None and not df.empty:
                # AKShare返回列通常包含: 序号, 股票代码, 股票名称, 占净值比例, 持股数, 持股市值
                new_holdings = {}
                
                # 取前10大重仓
                top10 = df.head(10)
                
                for _, row in top10.iterrows():
                    raw_code = str(row['股票代码'])
                    weight = float(row['占净值比例'])
                    
                    # 格式化代码为 YFinance 格式 (.SS/.SZ/.HK)
                    formatted_code = self._format_code(raw_code)
                    new_holdings[formatted_code] = weight
                
                if new_holdings:
                    self.etf_holdings_config[etf_symbol] = new_holdings
                    print(f"✅ [持仓更新] 成功更新 {etf_symbol} 的前 {len(new_holdings)} 大重仓股")
                    return True
                
        except Exception as e:
            print(f"⚠️ [持仓更新] 动态获取失败 ({e})，将使用静态配置兜底")
        
        return False

    def _format_code(self, raw_code):
        """将纯数字代码转换为带后缀的格式"""
        # 简单规则推断
        if len(raw_code) == 5: # 港股通常是5位
            return f"{raw_code}.HK"
        elif len(raw_code) == 6:
            if raw_code.startswith(('6', '5', '9')): # 沪市
                return f"{raw_code}.SS"
            elif raw_code.startswith(('0', '1', '3')): # 深市
                return f"{raw_code}.SZ"
        
        # 如果无法识别，返回原代码，依靠 TechnicalEngine 后续处理
        return raw_code

    def add_holding(self, etf_symbol, stock_symbol, weight):
        """手动添加或更新持仓配置"""
        if etf_symbol not in self.etf_holdings_config:
            self.etf_holdings_config[etf_symbol] = {}
        self.etf_holdings_config[etf_symbol][stock_symbol] = weight
        print(f"✅ 已手动更新 {etf_symbol} 的持仓: {stock_symbol} -> {weight}%")
    
    def remove_holding(self, etf_symbol, stock_symbol):
        """移除持仓配置"""
        if etf_symbol in self.etf_holdings_config:
            if stock_symbol in self.etf_holdings_config[etf_symbol]:
                del self.etf_holdings_config[etf_symbol][stock_symbol]
    
    def show_holdings(self, etf_symbol):
        """显示ETF的持仓配置"""
        holdings = self.get_holdings(etf_symbol)
        if holdings:
            print(f"\n📊 {etf_symbol} 持仓配置:")
            print("-" * 40)
            total_weight = 0
            for stock, weight in sorted(holdings.items(), key=lambda x: x[1], reverse=True):
                print(f"  {stock}: {weight}%")
                total_weight += weight
            print(f"  总权重: {total_weight:.1f}%")
            print("-" * 40)
        else:
            print(f"❌ 未找到 {etf_symbol} 的持仓配置")