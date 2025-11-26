from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import talib
import os
import time
import random
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from email_sender import EmailSender

class ETFHoldingsManager:
    """ETF持仓管理器"""
    
    def __init__(self):
        # ETF持仓配置 {ETF代码: {持仓股代码: 权重}}
        self.etf_holdings_config = {
            "513120.SS": {  # 港股创新药ETF
                "1801.HK": 9.5,   # 信达生物
                "6160.HK": 9.2,   # 百济神州
                "2269.HK": 9.1,   # 药明生物 (去掉前导0)
                "9926.HK": 9.1,   # 康方生物
                "1177.HK": 8.2,   # 中国生物制药
                "1093.HK": 6.7,   # 石药集团
                "1530.HK": 5.2,   # 三生制药
                "2359.HK": 4.8,   # 药明康德
                "3692.HK": 3.8,   # 翰森制药
                "6990.HK": 3.7    # 科伦博泰生物-B
            },
            "513180.SS": {  # 恒生科技指数ETF
                "00700.HK": 10.2,  # 腾讯控股
                "09988.HK": 9.8,   # 阿里巴巴
                "03690.HK": 9.5,   # 美团
                "09888.HK": 8.2,   # 百度
                "09618.HK": 7.8,   # 京东
                "09999.HK": 6.5,   # 网易
                "02020.HK": 5.8,   # 安踏体育
                "09626.HK": 5.2,   # 哔哩哔哩
                "09868.HK": 4.8,   # 小鹏汽车
                "09866.HK": 4.2    # 蔚来
            },
            "512890.SS": {  # 红利低波ETF
                "601318.SS": 8.5,  # 中国平安
                "601288.SS": 7.8,  # 农业银行
                "601328.SS": 7.2,  # 交通银行
                "601398.SS": 6.8,  # 工商银行
                "601988.SS": 6.5,  # 中国银行
                "600036.SS": 5.8,  # 招商银行
                "601166.SS": 5.2,  # 兴业银行
                "600000.SS": 4.8,  # 浦发银行
                "601818.SS": 4.5,  # 光大银行
                "601169.SS": 4.2   # 北京银行
            },
            "159995.SZ": {  # 芯片ETF
                "603986.SS": 9.2,  # 兆易创新
                "688981.SS": 8.8,  # 中芯国际
                "002049.SZ": 8.2,  # 紫光国微
                "603501.SS": 7.5,  # 韦尔股份
                "688008.SS": 7.2,  # 澜起科技
                "002371.SZ": 6.8,  # 北方华创
                "603290.SS": 6.2,  # 斯达半导
                "688126.SS": 5.8,  # 沪硅产业
                "300661.SZ": 5.5,  # 圣邦股份
                "688521.SS": 5.2   # 芯原股份
            }
        }
    
    def get_holdings(self, etf_symbol):
        """获取ETF的持仓配置"""
        return self.etf_holdings_config.get(etf_symbol, {})
    
    def add_holding(self, etf_symbol, stock_symbol, weight):
        """添加或更新持仓配置"""
        if etf_symbol not in self.etf_holdings_config:
            self.etf_holdings_config[etf_symbol] = {}
        self.etf_holdings_config[etf_symbol][stock_symbol] = weight
        print(f"✅ 已更新 {etf_symbol} 的持仓: {stock_symbol} -> {weight}%")
    
    def remove_holding(self, etf_symbol, stock_symbol):
        """移除持仓配置"""
        if etf_symbol in self.etf_holdings_config:
            if stock_symbol in self.etf_holdings_config[etf_symbol]:
                del self.etf_holdings_config[etf_symbol][stock_symbol]
                print(f"✅ 已移除 {etf_symbol} 的持仓: {stock_symbol}")
            else:
                print(f"❌ 未找到 {etf_symbol} 的持仓: {stock_symbol}")
        else:
            print(f"❌ 未找到ETF: {etf_symbol}")
    
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


class FinancialAnalyzer:
    def __init__(self, deepseek_client, data_manager):
        self.client = deepseek_client
        self.data_manager = data_manager
        
        # 重新组织标的分类
        self.available_etfs = {
            "513120.SS": "港股创新药ETF",
            "513180.SS": "恒生科技指数ETF", 
            "512890.SS": "红利低波ETF",
            "159995.SZ": "芯片ETF"
        }
        
        # 初始化持仓管理器
        self.holdings_manager = ETFHoldingsManager()
        
        # 初始化邮件发送器
        self.email_sender = EmailSender()
        
        # 为后续扩展预留
        self.available_indices = {}
        self.available_commodities = {}
        
        self.request_delay = 1
        self.max_retries = 3
    
    def get_etf_holdings(self, etf_symbol):
        """获取ETF的重仓股票信息（使用手动配置）"""
        try:
            # 从持仓管理器获取配置的持仓
            holdings_config = self.holdings_manager.get_holdings(etf_symbol)
            
            if holdings_config:
                print(f"✅ 使用配置获取 {etf_symbol} 的 {len(holdings_config)} 个持仓")
                
                # 转换为统一的持仓格式
                holdings = []
                for stock_symbol, weight in holdings_config.items():
                    holdings.append({
                        'symbol': stock_symbol,
                        'holdingName': stock_symbol,  # 可以后续扩展为股票名称
                        'holdingPercent': weight
                    })
                
                return holdings
            else:
                print(f"⚠ 未配置 {etf_symbol} 的持仓信息")
                return []
                
        except Exception as e:
            print(f"❌ 获取ETF持仓失败: {e}")
            return []

    def validate_stock_symbol(self, symbol):
        """使用yfinance验证股票代码是否存在（修复版本）"""
        try:
            import yfinance as yf
            print(f"    🔍 验证股票代码: {symbol}")
            
            # 方法1: 直接尝试获取数据来验证
            try:
                ticker = yf.Ticker(symbol)
                # 尝试获取少量数据来验证代码是否存在
                data = ticker.history(period="1d")
                if data is not None and not data.empty:
                    print(f"    ✅ 股票代码 {symbol} 验证通过")
                    return True
                else:
                    print(f"    ❌ 股票代码 {symbol} 不存在或无法获取数据")
                    return False
            except Exception as e:
                print(f"    ⚠ 通过数据获取验证股票代码 {symbol} 时出错: {e}")
                # 如果验证失败，我们仍然尝试获取数据
                return True
                
        except Exception as e:
            print(f"    ⚠ 验证股票代码 {symbol} 时出错: {e}")
            # 如果验证失败，我们仍然尝试获取数据
            return True

    def analyze_etf_with_holdings(self, etf_symbol):
        """分析ETF及其重仓股票（自动多周期分析 + 持仓股技术分析）"""
        print(f"\n📊 正在深度分析 {etf_symbol} 及其重仓股...")
        
        # 自动获取多个周期的数据
        all_periods_data = self.get_multiple_periods_data(etf_symbol)
        if not all_periods_data or len(all_periods_data) == 0:
            return {"content": f"无法获取 {etf_symbol} 数据", "usage": None, "cost": 0.0}
        
        # 使用6个月数据作为主要分析数据
        main_period_data = all_periods_data.get('6mo')
        if main_period_data is None:
            return {"content": f"无法获取 {etf_symbol} 的6个月数据", "usage": None, "cost": 0.0}
        
        # 从字典中获取实际的DataFrame数据
        main_data = main_period_data.get('raw')
        
        # 检查DataFrame是否为空
        if main_data is None or main_data.empty:
            return {"content": f"无法获取 {etf_symbol} 的有效数据", "usage": None, "cost": 0.0}
        
        # 显示原始数据预览
        self.display_raw_data(main_data, etf_symbol)
        
        # 获取持仓股票
        holdings = self.get_etf_holdings(etf_symbol)
        
        # 获取持仓股票的技术数据
        holdings_analysis = []
        if holdings:
            print("📈 获取重仓股票技术数据...")
            successful_holdings = 0
            
            for i, holding in enumerate(holdings[:10]):  # 分析前10大持仓
                stock_symbol = holding.get('symbol', '')
                if stock_symbol:
                    print(f"  正在分析持仓股 {i+1}/{len(holdings)}: {stock_symbol}")
                    
                    # 先验证股票代码是否存在
                    if not self.validate_stock_symbol(stock_symbol):
                        print(f"    ❌ 股票代码 {stock_symbol} 验证失败，跳过")
                        continue
                    
                    # 尝试多种周期获取数据
                    stock_data = None
                    periods_to_try = ["1mo", "3mo", "6mo", "1y"]
                    
                    for period in periods_to_try:
                        stock_data = self.get_stock_data(stock_symbol, period)
                        if stock_data is not None and not stock_data.empty:
                            print(f"    ✅ 使用 {period} 数据")
                            break
                        else:
                            print(f"    ⚠ {period} 数据获取失败")
                    
                    if stock_data is not None and not stock_data.empty:
                        # 计算技术指标
                        stock_technical = self.calculate_technical_indicators(stock_data)
                        if stock_technical is not None:
                            latest = stock_technical.iloc[-1]
                            
                            # 计算短期表现
                            price_change = ((stock_data['Close'].iloc[-1] - stock_data['Close'].iloc[0]) / 
                                        stock_data['Close'].iloc[0] * 100)
                            
                            # 分析技术状态
                            rsi_status = "超买" if latest['RSI'] > 70 else "超卖" if latest['RSI'] < 30 else "正常"
                            macd_signal = "金叉" if latest['MACD'] > latest['MACD_Signal'] else "死叉"
                            
                            holdings_analysis.append({
                                'symbol': stock_symbol,
                                'name': holding.get('holdingName', stock_symbol),
                                'weight': holding.get('holdingPercent', 0),
                                'price': latest['Close'],
                                'price_change': price_change,
                                'rsi': latest['RSI'],
                                'rsi_status': rsi_status,
                                'macd_signal': macd_signal,
                                'above_20ma': latest['Close'] > latest.get('SMA_20', 0),
                                'above_60ma': latest['Close'] > latest.get('SMA_60', 0)
                            })
                            successful_holdings += 1
                    else:
                        print(f"    ❌ 所有周期数据获取都失败，跳过 {stock_symbol}")
            
            print(f"✅ 成功分析 {successful_holdings}/{len(holdings[:10])} 个持仓股")
        
        prompt = self.create_enhanced_etf_analysis_prompt(etf_symbol, all_periods_data, holdings_analysis)
        
        print("🤖 使用AI进行ETF深度分析...")
        result = self.client.chat(
            message=prompt,
            model_type="chat",
            system_prompt="你是专业的ETF分析师，擅长多周期技术分析和持仓股综合分析",
            use_history=False
        )
        
        # 保存分析结果
        self.save_analysis_report(etf_symbol, result, all_periods_data)
        
        return result

    def create_enhanced_etf_analysis_prompt(self, symbol, all_periods_data, holdings_analysis):
        """创建增强的ETF分析提示词（修复字段名问题）"""
        symbol_name = self.available_etfs.get(symbol, '未知ETF')
        
        prompt = f"""
    请作为专业金融分析师对 {symbol} ({symbol_name}) 进行深度多周期技术分析：

    ## 多周期技术指标汇总
    """
        
        # 为每个周期生成分析摘要
        for period_code, period_data in all_periods_data.items():
            technical_data = period_data['technical']
            period_name = period_data['name']
            latest = technical_data.iloc[-1]
            
            # 计算价格变化
            if len(technical_data) > 1:
                previous = technical_data.iloc[-2]
                price_change = ((latest['Close'] - previous['Close']) / previous['Close']) * 100
            else:
                price_change = 0
            
            prompt += f"""
    ### {period_name}周期分析
    - 当前价格: ￥{latest['Close']:.2f} ({price_change:+.2f}%)
    - RSI: {latest['RSI']:.1f} {'(超买)' if latest['RSI'] > 70 else '(超卖)' if latest['RSI'] < 30 else '(正常)'}
    - MACD: {latest['MACD']:.3f} {'(金叉)' if latest['MACD'] > latest['MACD_Signal'] else '(死叉)'}
    """
            
            # 添加该周期的均线分析
            ma_analysis = self._get_ma_analysis_for_period(latest)
            prompt += ma_analysis
        
        # 添加持仓股技术分析
        if holdings_analysis:
            prompt += "\n## 重仓股技术分析详情\n"
            for holding in holdings_analysis:
                # 修复：使用 price_change 而不是 price_change_1m
                trend_icon = "📈" if holding['price_change'] > 0 else "📉"
                ma_status = []
                if holding['above_20ma']:
                    ma_status.append("20日线上")
                if holding['above_60ma']:
                    ma_status.append("60日线上")
                
                ma_status_str = " | ".join(ma_status) if ma_status else "均线下方"
                
                prompt += f"""
    ### {holding['symbol']} ({holding['name']}) - 权重{holding['weight']}%
    - 当前价格: ￥{holding['price']:.2f} {trend_icon}{holding['price_change']:+.1f}%
    - RSI: {holding['rsi']:.1f} ({holding['rsi_status']})
    - MACD: {holding['macd_signal']}
    - 均线位置: {ma_status_str}
    """
        
        # 添加综合分析要求
        prompt += """
    ## 请提供以下综合分析：

    ### 1. ETF多周期趋势判断
    - 短期趋势（1个月）：上涨/下跌/震荡及强度
    - 中期趋势（3-6个月）：主要趋势方向  
    - 长期趋势（1年）：整体格局判断

    ### 2. 持仓股技术面汇总
    - 重仓股整体技术状态（强势/弱势股票数量）
    - 关键持仓股的技术信号
    - 持仓股对ETF的技术面影响

    ### 3. 关键技术位分析
    - 各周期支撑位和阻力位
    - 关键均线（特别是60日季线和200日年线）的作用

    ### 4. 交易策略建议
    - 基于ETF和持仓股技术面的综合买卖信号
    - 最佳入场时机建议
    - 止损和止盈位置建议

    ### 5. 风险评估
    - ETF整体风险评估
    - 持仓股技术风险分析
    - 仓位管理建议

    请基于ETF多周期数据和持仓股技术分析提供全面、客观的投资建议。
    """
        
        return prompt

    def check_global_exit(self, user_input):
        """检查是否请求全局退出"""
        exit_commands = ['quit', 'exit', '退出', 'q', '0']
        return user_input.lower().strip() in exit_commands

    def input_with_exit_check(self, prompt):
        """带退出检查的输入函数"""
        user_input = input(prompt).strip()
        if self.check_global_exit(user_input):
            raise KeyboardInterrupt("用户请求退出")
        return user_input

    def get_multiple_periods_data(self, symbol):
        """获取多个时间周期的数据"""
        periods = {
            '1mo': '1个月',
            '3mo': '3个月', 
            '6mo': '6个月',
            '1y': '1年'
        }
        
        all_data = {}
        print("🔄 正在获取多周期数据...")
        
        for period_code, period_name in periods.items():
            print(f"  正在获取 {period_name} 数据...")
            data = self.get_stock_data(symbol, period_code)
            if data is not None and not data.empty:
                technical_data = self.calculate_technical_indicators(data)
                if technical_data is not None:
                    all_data[period_code] = {
                        'raw': data,
                        'technical': technical_data,
                        'name': period_name
                    }
        
        if all_data:
            print(f"✅ 成功获取 {len(all_data)} 个周期的数据")
            return all_data
        else:
            print("❌ 无法获取任何周期的数据")
            return None

    def calculate_technical_indicators(self, data):
        """计算技术指标（包含5日、10日、20日、60日、200日均线）"""
        if data is None or data.empty:
            return None
        
        df = data.copy()
        
        try:
            # 移动平均线 - 按照您的要求添加
            df['SMA_5'] = talib.SMA(df['Close'], timeperiod=5)    # 5日均线
            df['SMA_10'] = talib.SMA(df['Close'], timeperiod=10)  # 10日均线
            df['SMA_20'] = talib.SMA(df['Close'], timeperiod=20)  # 20日均线
            df['SMA_60'] = talib.SMA(df['Close'], timeperiod=60)  # 60日季线
            df['SMA_200'] = talib.SMA(df['Close'], timeperiod=200) # 200日年线
            
            # 指数移动平均线
            df['EMA_12'] = talib.EMA(df['Close'], timeperiod=12)
            df['EMA_26'] = talib.EMA(df['Close'], timeperiod=26)
            
            # RSI
            df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
            
            # MACD
            df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(df['Close'])
            
            # 布林带
            df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = talib.BBANDS(
                df['Close'], timeperiod=20, nbdevup=2, nbdevdn=2
            )
            
            # 成交量指标
            if 'Volume' in df.columns:
                df['Volume_SMA'] = talib.SMA(df['Volume'], timeperiod=20)
                df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
            else:
                df['Volume_SMA'] = 0
                df['Volume_Ratio'] = 1.0
            
            print("✅ 技术指标计算完成")
            return df
            
        except Exception as e:
            print(f"❌ 计算技术指标失败: {e}")
            return None

    def _get_ma_analysis(self, latest_data):
        """获取均线系统分析（包含所有5条均线）"""
        ma_info = []
        
        # 按照您要求的顺序：5日、10日、20日、60日、200日
        ma_periods = [
            ('SMA_5', '5日均线'),
            ('SMA_10', '10日均线'),
            ('SMA_20', '20日均线'), 
            ('SMA_60', '60日季线'),
            ('SMA_200', '200日年线')
        ]
        
        for ma_key, ma_name in ma_periods:
            if ma_key in latest_data and not pd.isna(latest_data[ma_key]):
                position = "上方" if latest_data['Close'] > latest_data[ma_key] else "下方"
                ma_info.append(f"- {ma_name}: ￥{latest_data[ma_key]:.2f}, 价格位置: {position}")
        
        # 分析均线排列
        ma_trend = self._analyze_ma_trend(latest_data)
        
        return "\n".join(ma_info) + f"\n\n## 均线趋势分析\n{ma_trend}"

    def _analyze_ma_trend(self, latest_data):
        """分析均线排列趋势"""
        trends = []
        
        # 检查完整的多头排列（5日>10日>20日>60日>200日）
        if all(key in latest_data for key in ['SMA_5', 'SMA_10', 'SMA_20', 'SMA_60', 'SMA_200']):
            ma_values = [
                latest_data['SMA_5'], latest_data['SMA_10'], latest_data['SMA_20'],
                latest_data['SMA_60'], latest_data['SMA_200']
            ]
            
            # 检查是否严格递增（多头排列）
            if all(ma_values[i] > ma_values[i+1] for i in range(len(ma_values)-1)):
                if latest_data['Close'] > latest_data['SMA_5']:
                    trends.append("✅ **强势多头排列**: 5日>10日>20日>60日>200日，价格在所有均线之上，强烈看涨")
                else:
                    trends.append("✅ **多头排列**: 5日>10日>20日>60日>200日，但价格在5日线附近")
            
            # 检查是否严格递减（空头排列）
            elif all(ma_values[i] < ma_values[i+1] for i in range(len(ma_values)-1)):
                if latest_data['Close'] < latest_data['SMA_5']:
                    trends.append("❌ **强势空头排列**: 5日<10日<20日<60日<200日，价格在所有均线之下，强烈看跌")
                else:
                    trends.append("❌ **空头排列**: 5日<10日<20日<60日<200日，但价格在5日线附近")
            
            else:
                trends.append("🔄 **震荡排列**: 均线交错，市场处于震荡状态")
        
        # 检查关键均线支撑压力
        key_mas = [
            ('SMA_20', '20日'),
            ('SMA_60', '60日'),
            ('SMA_200', '200日')
        ]
        
        for ma_key, ma_name in key_mas:
            if ma_key in latest_data:
                if latest_data['Close'] > latest_data[ma_key]:
                    trends.append(f"📈 **站稳{ma_name}线**: 价格在{ma_name}均线之上，该均线构成支撑")
                else:
                    trends.append(f"📉 **跌破{ma_name}线**: 价格在{ma_name}均线之下，该均线构成压力")
        
        return "\n".join(trends) if trends else "⚠ 均线趋势分析数据不足"

    def create_multiperiod_analysis_prompt(self, symbol, all_periods_data, holdings_analysis=None):
        """创建多周期分析提示词"""
        # ✅ 修复这里：使用 available_etfs 而不是 available_symbols
        symbol_name = self.available_etfs.get(symbol, '未知ETF')
        
        prompt = f"""
    请作为专业金融分析师对 {symbol} ({symbol_name}) 进行多周期技术分析：

    ## 多周期技术指标汇总
    """
        
        # 为每个周期生成分析摘要
        for period_code, period_data in all_periods_data.items():
            technical_data = period_data['technical']
            period_name = period_data['name']
            latest = technical_data.iloc[-1]
            
            # 计算价格变化
            if len(technical_data) > 1:
                previous = technical_data.iloc[-2]
                price_change = ((latest['Close'] - previous['Close']) / previous['Close']) * 100
            else:
                price_change = 0
            
            prompt += f"""
    ### {period_name}周期分析
    - 当前价格: ￥{latest['Close']:.2f} ({price_change:+.2f}%)
    - RSI: {latest['RSI']:.1f} {'(超买)' if latest['RSI'] > 70 else '(超卖)' if latest['RSI'] < 30 else '(正常)'}
    - MACD: {latest['MACD']:.3f} {'(金叉)' if latest['MACD'] > latest['MACD_Signal'] else '(死叉)'}
    """
            
            # 添加该周期的均线分析
            ma_analysis = self._get_ma_analysis_for_period(latest)
            prompt += ma_analysis
        
        # 添加重仓股分析
        if holdings_analysis:
            prompt += "\n## 前五大重仓股表现\n"
            for holding in holdings_analysis:
                trend = "📈" if holding['price_change'] > 0 else "📉"
                prompt += f"- {holding['symbol']} ({holding['name']}): 权重{holding['weight']:.1f}%, 近一月{trend}{holding['price_change']:+.1f}%\n"
        
        # 添加综合分析要求
        prompt += """
    ## 请提供以下综合分析：

    ### 1. 多周期趋势判断
    - 短期趋势（1个月）：上涨/下跌/震荡及强度
    - 中期趋势（3-6个月）：主要趋势方向
    - 长期趋势（1年）：整体格局判断

    ### 2. 关键技术位分析
    - 各周期支撑位和阻力位
    - 关键均线（特别是60日季线和200日年线）的作用
    - 布林带位置分析

    ### 3. 交易信号汇总
    - 各周期的买卖信号一致性
    - 最佳入场时机建议
    - 止损和止盈位置建议

    ### 4. 风险评估
    - 各周期风险等级评估
    - 仓位管理建议
    - 最大回撤控制

    ### 5. 未来走势预测
    - 短期（1-2周）走势预测
    - 中期（1-3个月）趋势展望
    - 关键事件或时间节点

    请基于多周期数据提供全面、客观的技术分析，避免单一周期的片面判断。
    """
        
        return prompt

    def _get_ma_analysis_for_period(self, latest_data):
        """为单个周期生成均线分析摘要"""
        analysis = "\n**均线系统**:\n"
        
        # 关键均线分析
        key_mas = [
            ('SMA_5', '5日'),
            ('SMA_10', '10日'),
            ('SMA_20', '20日'),
            ('SMA_60', '60日'),
            ('SMA_200', '200日')
        ]
        
        for ma_key, ma_name in key_mas:
            if ma_key in latest_data and not pd.isna(latest_data[ma_key]):
                position = "上方" if latest_data['Close'] > latest_data[ma_key] else "下方"
                analysis += f"- {ma_name}线: ￥{latest_data[ma_key]:.2f} (价格{position})\n"
        
        return analysis

    def get_stock_data(self, symbol, period="1y", retry_count=0):
        """获取股票数据，带有重试机制（加快版本）"""
        try:
            # 将随机延迟从0-2秒改为0-0.5秒
            delay = self.request_delay + random.uniform(0, 0.5)  # 原来是 random.uniform(0, 2)
            print(f"⏳ 请求数据中，等待 {delay:.1f} 秒...")
            time.sleep(delay)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data is None or data.empty:
                if retry_count < self.max_retries:
                    print(f"⚠ 第 {retry_count + 1} 次获取数据为空，重试中...")
                    return self.get_stock_data(symbol, period, retry_count + 1)
                else:
                    print(f"❌ 获取 {symbol} 数据失败: 数据为空")
                    return None

            if data is not None and not data.empty:
                latest_date = data.index[-1]
                current_date = pd.Timestamp.now().normalize()
                
                if latest_date.date() == current_date.date():
                    data_status = "最新"
                else:
                    data_status = "延迟"

            print(f"✅ 成功获取 {symbol} {period} 数据 (状态: {data_status})，共 {len(data)} 条记录")
            return data
            
        except Exception as e:
            error_msg = str(e)
            if "Too Many Requests" in error_msg or "Rate limited" in error_msg:
                if retry_count < self.max_retries:
                    # 将重试等待时间从10秒改为3秒
                    wait_time = (retry_count + 1) * 3  # 原来是 (retry_count + 1) * 10
                    print(f"⚠ 请求频率过高，等待 {wait_time} 秒后重试... (第 {retry_count + 1}/{self.max_retries} 次)")
                    time.sleep(wait_time)
                    return self.get_stock_data(symbol, period, retry_count + 1)
                else:
                    print(f"❌ 获取 {symbol} 数据失败: 请求频率限制，请稍后再试")
            else:
                print(f"❌ 获取 {symbol} 数据失败: {error_msg}")
            return None
            
        except Exception as e:
            error_msg = str(e)
            if "Too Many Requests" in error_msg or "Rate limited" in error_msg:
                if retry_count < self.max_retries:
                    wait_time = (retry_count + 1) * 10
                    print(f"⚠ 请求频率过高，等待 {wait_time} 秒后重试... (第 {retry_count + 1}/{self.max_retries} 次)")
                    time.sleep(wait_time)
                    return self.get_stock_data(symbol, period, retry_count + 1)
                else:
                    print(f"❌ 获取 {symbol} 数据失败: 请求频率限制，请稍后再试")
            else:
                print(f"❌ 获取 {symbol} 数据失败: {error_msg}")
            return None
    
    def set_request_delay(self, delay_seconds):
        """设置请求延迟时间"""
        self.request_delay = delay_seconds
        print(f"✅ 请求延迟已设置为 {delay_seconds} 秒")

    def identify_candlestick_patterns(self, data):
        """识别K线形态"""
        try:
            patterns = {}
            
            # 使用TA-Lib识别常见K线形态
            patterns['doji'] = talib.CDLDOJI(data['Open'], data['High'], data['Low'], data['Close'])
            patterns['hammer'] = talib.CDLHAMMER(data['Open'], data['High'], data['Low'], data['Close'])
            patterns['engulfing'] = talib.CDLENGULFING(data['Open'], data['High'], data['Low'], data['Close'])
            patterns['morning_star'] = talib.CDLMORNINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
            patterns['evening_star'] = talib.CDLEVENINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
            patterns['shooting_star'] = talib.CDLSHOOTINGSTAR(data['Open'], data['High'], data['Low'], data['Close'])
            patterns['hanging_man'] = talib.CDLHANGINGMAN(data['Open'], data['High'], data['Low'], data['Close'])
            
            # 分析最近5天的形态
            recent_patterns = []
            for i in range(min(5, len(data))):
                idx = -1 - i
                date = data.index[idx].strftime('%Y-%m-%d')
                day_patterns = []
                
                for pattern_name, pattern_data in patterns.items():
                    if pattern_data.iloc[idx] != 0:
                        day_patterns.append(pattern_name)
                
                if day_patterns:
                    recent_patterns.append({
                        'date': date,
                        'patterns': day_patterns,
                        'close_price': data['Close'].iloc[idx]
                    })
            
            return recent_patterns
            
        except Exception as e:
            print(f"❌ 识别K线形态失败: {e}")
            return []

    def plot_technical_analysis(self, data, symbol, period_name="6个月"):
        """绘制技术分析图表"""
        try:
            # 确保有足够的空间显示图表
            plt.rcParams['figure.figsize'] = [12, 8]
            
            # 创建子图
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))
            
            # 1. K线图 + 移动平均线
            ax1.set_title(f'{symbol} - K线图与移动平均线 ({period_name})', fontsize=14, fontweight='bold')
            mpf.plot(data, type='candle', style='charles', ax=ax1, volume=False, show_nontrading=False)
            
            # 添加所有移动平均线
            ma_configs = [
                ('SMA_5', '5日均线', 'orange', 1, 0.7),
                ('SMA_10', '10日均线', 'purple', 1, 0.7),
                ('SMA_20', '20日均线', 'blue', 1.5, 1),
                ('SMA_60', '60日季线', 'red', 2, 1),
                ('SMA_200', '200日年线', 'green', 2, 1)
            ]
            
            for ma_key, label, color, width, alpha in ma_configs:
                if ma_key in data.columns:
                    ax1.plot(data.index, data[ma_key], label=label, color=color, 
                            linewidth=width, alpha=alpha)
                
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 2. RSI指标
            ax2.set_title('RSI相对强弱指标', fontsize=12, fontweight='bold')
            if 'RSI' in data.columns:
                ax2.plot(data.index, data['RSI'], label='RSI', color='purple', linewidth=1)
                ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='超买线(70)')
                ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='超卖线(30)')
                ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.5)
                ax2.set_ylim(0, 100)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # 3. MACD指标
            ax3.set_title('MACD指标', fontsize=12, fontweight='bold')
            if 'MACD' in data.columns and 'MACD_Signal' in data.columns:
                ax3.plot(data.index, data['MACD'], label='MACD', color='blue', linewidth=1)
                ax3.plot(data.index, data['MACD_Signal'], label='信号线', color='red', linewidth=1)
                
                # 绘制MACD柱状图
                colors = ['green' if x >= 0 else 'red' for x in data['MACD_Hist']]
                ax3.bar(data.index, data['MACD_Hist'], color=colors, alpha=0.3, label='MACD柱')
                
                ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存图表
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{symbol}_technical_analysis_{timestamp}.png"
            plt.savefig(f"financial_data/{filename}", dpi=300, bbox_inches='tight')
            print(f"✅ 技术分析图表已保存: {filename}")
            
            plt.show()
            return True
            
        except Exception as e:
            print(f"❌ 绘制技术分析图表失败: {e}")
            return False

    def analyze_symbol(self, symbol):
        """分析单个标的（自动多周期分析）"""
        print(f"\n📊 正在对 {symbol} 进行多周期分析...")
        
        # 获取多周期数据
        all_periods_data = self.get_multiple_periods_data(symbol)
        if not all_periods_data:
            return {
                "content": f"无法获取 {symbol} 的数据，可能是请求频率限制，请稍后再试",
                "usage": None,
                "cost": 0.0
            }
        
        # 显示主要周期的原始数据
        main_data = all_periods_data.get('6mo', {}).get('raw')
        if main_data is not None:
            self.display_raw_data(main_data, symbol)
        
        # 创建多周期分析提示词
        prompt = self.create_multiperiod_analysis_prompt(symbol, all_periods_data)
        
        # 增强提示词，加入日期信息
        enhanced_prompt = self.enhance_analysis_prompt_with_dates(symbol, all_periods_data, prompt)
        
        # 使用AI分析
        print("🤖 正在使用AI进行多周期分析...")
        result = self.client.chat(
            message=enhanced_prompt,
            model_type="chat",
            system_prompt="你是一个专业的金融量化分析师，擅长多周期技术分析和风险管理。请提供客观、专业的分析。",
            use_history=False
        )
        
        # 保存分析结果
        self.save_analysis_report(symbol, result, all_periods_data)
        
        return result
    
    def interactive_analysis(self):
        """交互式分析模式（简化版，ETF统一使用深度分析）"""
        print("\n📈 金融数据分析模式")
        print("=" * 40)
        print("💡 提示: 在任何输入环节输入 'quit'、'exit' 或 '退出' 可立即结束当前操作")
        print("=" * 40)
        
        while True:
            print("\n可选功能:")
            print("1. 📊 ETF深度分析（含重仓股）")
            print("2. 📈 技术分析图表（6个月）")
            print("3. ⚙️  设置请求延迟")
            print("4. 🗃️  管理ETF持仓配置")
            print("5. 📧 邮件发送设置")
            print("0. 返回主菜单")
            print("-" * 40)
            
            try:
                choice = self.input_with_exit_check("请选择功能 (0-5): ").strip()
                
                if choice == "0":
                    break
                elif choice == "1":
                    # ETF深度分析
                    print("\n选择要深度分析的ETF:")
                    if not self.available_etfs:
                        print("❌ 当前没有可用的ETF标的")
                        continue
                        
                    for i, (symbol, name) in enumerate(self.available_etfs.items(), 1):
                        print(f"{i}. {symbol}: {name}")
                    
                    etf_choice = self.input_with_exit_check("请选择ETF编号: ").strip()
                    if etf_choice.isdigit():
                        idx = int(etf_choice) - 1
                        if 0 <= idx < len(self.available_etfs):
                            symbol = list(self.available_etfs.keys())[idx]
                            result = self.analyze_etf_with_holdings(symbol)
                            
                            # 显示分析结果
                            if "content" in result:
                                print(f"\n✅ ETF深度分析完成!")
                                print(f"\n📋 分析结果:")
                                print("-" * 50)
                                print(result["content"])
                                print("-" * 50)
                                
                                if result["usage"]:
                                    usage = result["usage"]
                                    print(f"\n📊 使用统计: 输入{usage.prompt_tokens} tokens, 输出{usage.completion_tokens} tokens")
                                    print(f"💰 费用估算: ￥{result['cost']:.6f}")
                                
                                # 询问是否发送邮件
                                send_email = self.input_with_exit_check("\n是否发送分析报告到邮箱? (y/n): ").strip().lower()
                                if send_email == 'y':
                                    if not self.email_sender.sender_email:
                                        print("📧 首次使用需要配置邮箱...")
                                        if not self.email_sender.setup_email_config():
                                            continue
                                    
                                    recipient = self.input_with_exit_check("请输入接收邮箱地址: ").strip()
                                    if recipient:
                                        # 准备分析结果数据
                                        analysis_data = {
                                            'content': result["content"],
                                            'cost': result.get("cost", 0),
                                            'symbol_name': self.available_etfs.get(symbol, '未知ETF')
                                        }
                                        self.email_sender.send_analysis_report(recipient, symbol, analysis_data)
                        else:
                            print("❌ 无效的ETF选择")
                    else:
                        print("❌ 请输入有效的数字")
                        
                elif choice == "2":
                    # 技术分析图表
                    print("\n选择要生成图表的ETF:")
                    if not self.available_etfs:
                        print("❌ 当前没有可用的ETF标的")
                        continue
                        
                    for i, (symbol, name) in enumerate(self.available_etfs.items(), 1):
                        print(f"{i}. {symbol}: {name}")
                    
                    chart_choice = self.input_with_exit_check("请选择ETF编号: ").strip()
                    if chart_choice.isdigit():
                        idx = int(chart_choice) - 1
                        if 0 <= idx < len(self.available_etfs):
                            symbol = list(self.available_etfs.keys())[idx]
                            
                            # 获取6个月数据并生成图表
                            data = self.get_stock_data(symbol, "6mo")
                            if data is not None:
                                technical_data = self.calculate_technical_indicators(data)
                                if technical_data is not None:
                                    # 生成图表文件路径
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filename = f"{symbol}_technical_analysis_{timestamp}.png"
                                    filepath = f"financial_data/{filename}"
                                    
                                    if self.plot_technical_analysis(technical_data, symbol, "6个月"):
                                        # 询问是否发送图表邮件
                                        send_email = self.input_with_exit_check("\n是否发送技术分析图表到邮箱? (y/n): ").strip().lower()
                                        if send_email == 'y':
                                            if not self.email_sender.sender_email:
                                                print("📧 首次使用需要配置邮箱...")
                                                if not self.email_sender.setup_email_config():
                                                    continue
                                            
                                            recipient = self.input_with_exit_check("请输入接收邮箱地址: ").strip()
                                            if recipient:
                                                self.email_sender.send_technical_chart(recipient, symbol, filepath)
                        else:
                            print("❌ 无效的选择")
                    else:
                        print("❌ 请输入有效的数字")
                        
                elif choice == "3":
                    # 设置请求延迟
                    try:
                        delay_input = self.input_with_exit_check("请输入请求延迟时间(秒，建议5-10): ")
                        delay = float(delay_input)
                        self.set_request_delay(delay)
                    except ValueError:
                        print("❌ 请输入有效的数字")
                    continue
                
                elif choice == "4":
                    # 管理ETF持仓配置
                    self.manage_etf_holdings()
                    
                elif choice == "5":
                    # 邮件发送设置
                    self.email_sender.setup_email_config()
                    
                else:
                    print("❌ 无效的选择，请重新输入")
                            
            except KeyboardInterrupt:
                print("\n\n🔚 操作已结束，返回功能菜单")
                continue
            except (ValueError, IndexError):
                print("❌ 无效的选择")
            except Exception as e:
                print(f"❌ 分析过程中出现错误: {e}")

    def manage_etf_holdings(self):
        """管理ETF持仓配置"""
        print("\n🗃️  ETF持仓配置管理")
        print("=" * 40)
        
        while True:
            print("\n可选操作:")
            print("1. 查看ETF持仓配置")
            print("2. 添加/更新持仓")
            print("3. 移除持仓")
            print("0. 返回上一级")
            print("-" * 40)
            
            try:
                choice = self.input_with_exit_check("请选择操作 (0-3): ").strip()
                
                if choice == "0":
                    break
                elif choice == "1":
                    # 查看持仓配置
                    print("\n选择要查看的ETF:")
                    for i, (symbol, name) in enumerate(self.available_etfs.items(), 1):
                        print(f"{i}. {symbol}: {name}")
                    
                    etf_choice = self.input_with_exit_check("请选择ETF编号: ").strip()
                    if etf_choice.isdigit():
                        idx = int(etf_choice) - 1
                        if 0 <= idx < len(self.available_etfs):
                            symbol = list(self.available_etfs.keys())[idx]
                            self.holdings_manager.show_holdings(symbol)
                        else:
                            print("❌ 无效的ETF选择")
                    else:
                        print("❌ 请输入有效的数字")
                        
                elif choice == "2":
                    # 添加/更新持仓
                    print("\n选择要配置的ETF:")
                    for i, (symbol, name) in enumerate(self.available_etfs.items(), 1):
                        print(f"{i}. {symbol}: {name}")
                    
                    etf_choice = self.input_with_exit_check("请选择ETF编号: ").strip()
                    if etf_choice.isdigit():
                        idx = int(etf_choice) - 1
                        if 0 <= idx < len(self.available_etfs):
                            symbol = list(self.available_etfs.keys())[idx]
                            stock_symbol = self.input_with_exit_check("请输入股票代码: ").strip()
                            weight_input = self.input_with_exit_check("请输入权重(%): ").strip()
                            try:
                                weight = float(weight_input)
                                self.holdings_manager.add_holding(symbol, stock_symbol, weight)
                            except ValueError:
                                print("❌ 请输入有效的权重数字")
                        else:
                            print("❌ 无效的ETF选择")
                    else:
                        print("❌ 请输入有效的数字")
                        
                elif choice == "3":
                    # 移除持仓
                    print("\n选择要配置的ETF:")
                    for i, (symbol, name) in enumerate(self.available_etfs.items(), 1):
                        print(f"{i}. {symbol}: {name}")
                    
                    etf_choice = self.input_with_exit_check("请选择ETF编号: ").strip()
                    if etf_choice.isdigit():
                        idx = int(etf_choice) - 1
                        if 0 <= idx < len(self.available_etfs):
                            symbol = list(self.available_etfs.keys())[idx]
                            stock_symbol = self.input_with_exit_check("请输入要移除的股票代码: ").strip()
                            self.holdings_manager.remove_holding(symbol, stock_symbol)
                        else:
                            print("❌ 无效的ETF选择")
                    else:
                        print("❌ 请输入有效的数字")
                        
                else:
                    print("❌ 无效的选择，请重新输入")
                            
            except KeyboardInterrupt:
                print("\n\n🔚 操作已结束，返回配置菜单")
                continue
            except Exception as e:
                print(f"❌ 操作过程中出现错误: {e}")

    def display_raw_data(self, data, symbol):
        """显示原始数据预览"""
        try:
            if data is None or data.empty:
                print(f"❌ 没有获取到 {symbol} 的数据")
                return
            
            print(f"\n📊 {symbol} 原始数据预览:")
            print("=" * 60)
            print(f"数据时间范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"最新数据日期: {data.index[-1].strftime('%Y-%m-%d')}")
            print(f"数据条数: {len(data)}")
            print("\n最近5个交易日数据:")
            display_columns = ['Open', 'High', 'Low', 'Close']
            if 'Volume' in data.columns:
                display_columns.append('Volume')
            print(data[display_columns].tail())
            print("=" * 60)
        except Exception as e:
            print(f"❌ 显示数据时出错: {e}")

    def save_analysis_report(self, symbol, analysis_result, all_periods_data):
        """保存分析报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存各周期数据
            for period_code, period_data in all_periods_data.items():
                raw_data = period_data.get('raw')
                technical_data = period_data.get('technical')
                period_name = period_data.get('name', period_code)
                
                if raw_data is not None and not raw_data.empty:
                    raw_filename = f"{symbol}_{period_name}_raw_data_{timestamp}"
                    if self.data_manager.save_data(raw_data, raw_filename, 'csv'):
                        print(f"✅ {period_name}原始数据已保存: {raw_filename}.csv")
                
                if technical_data is not None and not technical_data.empty:
                    tech_filename = f"{symbol}_{period_name}_technical_{timestamp}"
                    if self.data_manager.save_data(technical_data, tech_filename, 'csv'):
                        print(f"✅ {period_name}技术指标数据已保存: {tech_filename}.csv")
            
            # 保存分析报告
            if analysis_result and "content" in analysis_result:
                latest_date = "未知"
                # 使用6个月数据的最新日期
                six_month_data = all_periods_data.get('6mo', {}).get('raw')
                if six_month_data is not None:
                    latest_date = six_month_data.index[-1].strftime('%Y-%m-%d')
                
                report_data = {
                    'symbol': [symbol],
                    'symbol_name': [self.available_etfs.get(symbol, '未知ETF')],  # ✅ 修复这里
                    'analysis_time': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    'data_latest_date': [latest_date],
                    'analysis_report': [analysis_result["content"]],
                    'cost': [analysis_result.get("cost", 0)]
                }
                
                if analysis_result.get("usage"):
                    usage = analysis_result["usage"]
                    report_data['input_tokens'] = [getattr(usage, 'prompt_tokens', 0)]
                    report_data['output_tokens'] = [getattr(usage, 'completion_tokens', 0)]
                
                report_df = pd.DataFrame(report_data)
                report_filename = f"{symbol}_multi_period_analysis_report_{timestamp}"
                if self.data_manager.save_data(report_df, report_filename, 'csv'):
                    print(f"✅ 多周期分析报告已保存: {report_filename}.csv")
                    
        except Exception as e:
            print(f"❌ 保存分析报告时出错: {e}")
    
    def enhance_analysis_prompt_with_dates(self, symbol, all_periods_data, base_prompt):
        """在分析提示词中加入日期信息"""
        try:
            latest_date = "未知"
            # 使用6个月数据的最新日期
            six_month_data = all_periods_data.get('6mo', {}).get('raw')
            if six_month_data is not None:
                latest_date = six_month_data.index[-1].strftime('%Y-%m-%d')
            
            # ✅ 修复这里：使用 available_etfs 而不是 available_symbols
            symbol_name = self.available_etfs.get(symbol, '未知ETF')
            
            date_info = f"""
    ## 数据时效性说明
    - 分析标的: {symbol} ({symbol_name})
    - 分析基于的数据截止日期: {latest_date}
    - 当前系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    - 请注意数据可能存在1-2天的延迟
    - 分析包含1个月、3个月、6个月、1年四个周期数据

    请基于多周期数据时效性进行综合分析，如果数据不是最新的，请在分析中说明这一限制。
    """
            return base_prompt + date_info
        except Exception as e:
            print(f"❌ 增强提示词时出错: {e}")
            return base_prompt
        
    def add_index(self, symbol, name):
        """添加指数标的"""
        self.available_indices[symbol] = name
        print(f"✅ 已添加指数: {symbol} - {name}")

    def add_commodity(self, symbol, name):
        """添加商品标的"""
        self.available_commodities[symbol] = name
        print(f"✅ 已添加商品: {symbol} - {name}")

    def analyze_index(self, symbol):
        """分析指数（多周期技术分析，不含持仓）"""
        # 这里可以复用现有的多周期分析逻辑，但不包含持仓分析
        print(f"\n📊 正在对指数 {symbol} 进行多周期分析...")
        
        all_periods_data = self.get_multiple_periods_data(symbol)
        if not all_periods_data:
            return {
                "content": f"无法获取 {symbol} 的数据",
                "usage": None,
                "cost": 0.0
            }
        
        # 创建专门针对指数的分析提示词
        prompt = self.create_index_analysis_prompt(symbol, all_periods_data)
        
        # 使用AI分析
        print("🤖 正在使用AI进行指数分析...")
        result = self.client.chat(
            message=prompt,
            model_type="chat",
            system_prompt="你是一个专业的指数分析师，擅长多周期技术分析和宏观经济影响分析",
            use_history=False
        )
        
        # 保存分析结果
        self.save_analysis_report(symbol, result, all_periods_data)
        
        return result

    def create_index_analysis_prompt(self, symbol, all_periods_data):
        """创建指数分析提示词"""
        # 这里可以基于现有的多周期分析提示词，但调整分析重点
        base_prompt = f"""
    请作为专业指数分析师对 {symbol} 进行多周期技术分析：

    ## 多周期技术指标汇总
    """
        
        # 为每个周期生成分析摘要（复用现有逻辑）
        for period_code, period_data in all_periods_data.items():
            technical_data = period_data['technical']
            period_name = period_data['name']
            latest = technical_data.iloc[-1]
            
            # 计算价格变化
            if len(technical_data) > 1:
                previous = technical_data.iloc[-2]
                price_change = ((latest['Close'] - previous['Close']) / previous['Close']) * 100
            else:
                price_change = 0
            
            prompt += f"""
    ### {period_name}周期分析
    - 当前点位: {latest['Close']:.2f} ({price_change:+.2f}%)
    - RSI: {latest['RSI']:.1f} {'(超买)' if latest['RSI'] > 70 else '(超卖)' if latest['RSI'] < 30 else '(正常)'}
    - 均线系统: 5日{latest.get('SMA_5', 0):.2f} | 20日{latest.get('SMA_20', 0):.2f} | 60日{latest.get('SMA_60', 0):.2f}
    """
        
        prompt += """
    ## 请提供以下指数专项分析：

    ### 1. 多周期趋势判断
    - 短期、中期、长期趋势分析
    - 关键技术位和支撑阻力分析

    ### 2. 宏观影响因素
    - 可能的宏观经济影响因素
    - 政策面、资金面分析

    ### 3. 行业轮动观察
    - 成分股行业表现分析
    - 市场风格判断

    ### 4. 风险评估
    - 系统性风险评估
    - 波动率分析

    请基于多周期数据提供全面、客观的指数分析。
    """
        
        return prompt
