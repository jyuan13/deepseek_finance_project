"""
==========================================================================================
【文件定义】
文件名: finance_core.py
类名  : FinanceCore
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(client, fdm, shadow_engine, ...)
   [依赖注入] -> (Client, FDM, Shadow, Guard, Macro, Prompt, Kronos)
         ↓
   [配置宏观指数列表] -> [配置 Kronos 预测标的] -> [Ready]

2. scan_macro_environment(predict, debug)
   [MacroAnalyzer] -> (指数趋势 + 宏观流动性) -> [打印概览]
         ↓
   [Kronos Check] -> {Active?} -> [Loop Targets: Fetch Hist -> Predict -> Append]
         ↓
   [合并数据] -> [返回 Macro Data]

3. analyze_fund(fund_code, user_cost, ...)
   [FDM Info/Holdings] -> [Shadow Calc NAV] -> [News + RAG Query] -> [Risk Guard Check]
         ↓
   [Calc MA Trend] -> [Calc Est PnL] -> [Construct LLM Prompt (Macro+RAG+Risk)]
         ↓
   [Call LLM (Reasoner)] -> [Parse JSON] -> [Return Decision]

4. analyze_index(symbol, market_value, ...)
   [Get Snapshot] -> {Valid?} -> [Calc FX Impact (USD/CNY)] -> [Calc Today PnL]
         ↓
   [Get News] -> [Calc Tech Trend (MA20)] -> [Construct LLM Prompt]
         ↓
   [Call LLM] -> [Parse JSON] -> [Return Decision]

5. _calculate_ma_trend(fund_code, debug)
   [Get NAV History] -> {Len < 20?} -> (Return "数据不足")
         ↓
   [Calc MA10/20/60] -> [Compare Current vs MA] -> [Determine Trend State]
         ↓
   [Return Trend String]

6. _parse_llm_json(content)
   [Regex Match ```json ... ```] -> {Match?} -> (Load Group 1)
         ↓
   (No Match) -> [Load Full Content] -> {Exception?} -> [Return Default Error Dict]
==========================================================================================
"""

import json
import re
import pandas as pd
import numpy as np
from datetime import datetime

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return json.JSONEncoder.default(self, obj)

class FinanceCore:
    """
    金融分析核心逻辑层 (Model)
    [V3.92 Brain Activated] 
    1. 即使行情缺失，也坚持完成分析
    2. 显式调用 RAG 知识库，将研报观点注入 Prompt
    """
    def __init__(self, client, fdm, shadow_engine, risk_guard, macro_analyzer, prompt_builder, kronos_provider):
        self.client = client
        self.fdm = fdm
        self.shadow = shadow_engine
        self.guard = risk_guard
        self.macro_analyzer = macro_analyzer
        self.prompt_builder = prompt_builder
        self.kronos_provider = kronos_provider 

        # 宏观指数配置
        self.indices_config = {
            'Nasdaq': '^IXIC', 
            'SP500': '^GSPC', 
            'Shanghai': '000001.SS', 
            'CSI300': '000300.SS',
            'HangSeng': '^HSI',
            'HSTech': '^HSTECH',
            'Nikkei225': '^N225',
            'Gold': 'GC=F'
        }
        
        # Kronos 预测配置
        self.kronos_targets = [
            {"name": "Nasdaq (US)", "symbol": "^IXIC", "market": "US"},
            {"name": "S&P 500 (US)", "symbol": "^GSPC", "market": "US"},
            {"name": "Shanghai (CN)", "symbol": "000001.SS", "market": "A"},
            {"name": "CSI 300 (CN)", "symbol": "000300.SS", "market": "A"},
            {"name": "Hang Seng (HK)", "symbol": "^HSI", "market": "Global"},
            {"name": "HS Tech (HK)", "symbol": "^HSTECH", "market": "Global"},
            {"name": "Nikkei 225 (JP)", "symbol": "^N225", "market": "Global"}
        ]

    def scan_macro_environment(self, predict=False, debug=False):
        print("🌍 正在扫描宏观环境 (读取本地缓存/联网)...")
        macro_data = {}
        try:
            macro_data = self.macro_analyzer.analyze_indices_trend(self.indices_config)
            if debug: print(f"\n🐛 [DEBUG] 宏观数据: {macro_data}")
            
            macro_liquidity = self.macro_analyzer.analyze_macro_liquidity()
            print("\n📊 宏观数据概览:")
            for k, v in macro_data.items():
                print(f"  - {k:<15}: {v}")
            
            kronos = self.kronos_provider()
            if predict and kronos and kronos.is_active:
                print(f"\n🤖 Kronos Global Forecast (Scanning {len(self.kronos_targets)} Indices)...")
                macro_data['Kronos_Detail'] = []
                macro_data['Kronos_Prediction'] = "See Detail Table"
                
                for target in self.kronos_targets:
                    symbol = target['symbol']
                    market = target['market']
                    name = target['name']
                    
                    df_hist = self.fdm.provider.fetch_history_kline(symbol, market=market)
                    if not df_hist.empty:
                        snapshot, valid = self.fdm.get_realtime_snapshot(symbol)
                        if valid and snapshot.get('price'):
                            last_hist_date = pd.to_datetime(df_hist.iloc[-1]['date']).date()
                            if datetime.now().date() > last_hist_date:
                                new_row = pd.DataFrame([{
                                    'date': datetime.now(), 
                                    'open': snapshot.get('open', snapshot['price']), 
                                    'high': snapshot.get('high', snapshot['price']),
                                    'low': snapshot.get('low', snapshot['price']),
                                    'close': snapshot['price'], 
                                    'volume': 0
                                }])
                                df_hist = pd.concat([df_hist, new_row], ignore_index=True)
                    
                        pred_desc, conf, pred_df = kronos.predict_trend(df_hist, pred_len=5, debug=debug)
                        print(f"   🔮 {name:<18} | T+1: {pred_desc} | Conf: {conf}")
                        
                        if pred_df is not None:
                            t1_row = pred_df.iloc[0]
                            macro_data['Kronos_Detail'].append({
                                'name': name,
                                'date': t1_row['date'].strftime('%m-%d'),
                                'close': f"{t1_row['close']:.2f}",
                                'chg': f"{t1_row['cum_pct_chg']:+.2f}%",
                                'conf': conf
                            })

            if macro_liquidity:
                return {**macro_data, "US_10Y": macro_liquidity.get("us_10y")}
            return macro_data
        except Exception as e:
            print(f"⚠️ 宏观扫描失败: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def analyze_fund(self, fund_code, user_cost, holding_qty, max_invest_limit, dca_amount, target_amount, macro_context, debug=False, fund_comment=""):
        if debug: print(f"\n{'='*20} 开始分析: {fund_code} {'='*20}")
        
        info = self.fdm.get_fund_basic_info(fund_code)
        if debug: print(f"🐛 [DEBUG] 基金基础信息 (Info): {info}")
        
        asset_type = info.get('type', 'stock') 
        real_name = info.get('name', fund_code)
        display_name = f"{real_name} ({fund_code})"
        
        holdings = self.fdm.get_top_holdings(fund_code)
        est_nav_chg, basis = self.shadow.calc_realtime_nav(fund_code, holdings)
        
        # [News] 获取新闻
        news = self.fdm.get_aggregated_news(fund_code)
        if news:
            print(f"   📰 关联舆情 ({len(news)}条):")
            for n in news[:3]:
                print(f"     - {n[:60]}...")
        else:
            print("   📰 关联舆情: 暂无显著新闻")
            
        # [RAG] 获取知识库研报 (Core Fix)
        rag_context = "暂无相关研报"
        try:
            # 尝试通过 prompt_builder.rag_engine 获取上下文
            # 假设 rag_engine 有一个标准的 query 接口
            if hasattr(self.prompt_builder, 'rag_engine') and self.prompt_builder.rag_engine:
                # 构造查询词：代码 + 名称 + "投资观点"
                query_text = f"{fund_code} {real_name} 投资价值 分析"
                # 假设 query 方法返回 list of strings
                rag_results = self.prompt_builder.rag_engine.query(query_text, n_results=2)
                if rag_results:
                    rag_context = "\n".join([f"- {r}" for r in rag_results])
                    print(f"   🧠 RAG 知识库: 检索到 {len(rag_results)} 条相关观点")
        except Exception as e:
            if debug: print(f"   ⚠️ RAG 检索失败: {e}")

        ma_trend = self._calculate_ma_trend(fund_code, debug=debug)
        
        holding_pnl_pct = 0.0
        pnl_desc = "(盈亏数据不足)"
        
        if user_cost > 0 and holding_qty > 0:
            try:
                hist = self.fdm.get_fund_nav_history(fund_code, lookback_days=5)
                if not hist.empty:
                    latest_nav = hist.iloc[-1]['nav']
                    curr_est_nav = latest_nav * (1 + est_nav_chg/100)
                    holding_pnl_pct = ((curr_est_nav - user_cost) / user_cost) * 100
                    pnl_desc = f"{holding_pnl_pct:.2f}% (累计)"
                else:
                    holding_pnl_pct = est_nav_chg
                    pnl_desc = f"{holding_pnl_pct:.2f}% (仅今日浮动)"
            except:
                holding_pnl_pct = est_nav_chg
                pnl_desc = f"{holding_pnl_pct:.2f}% (仅今日浮动)"
        
        risk_ctx = {
            "shadow_change": est_nav_chg, 
            "holding_pnl": holding_pnl_pct,
            "has_holding": (holding_qty > 0),
            "asset_type": asset_type,
            "max_invest_limit": max_invest_limit
        }
        
        is_safe, risk_msg = self.guard.check_risk("BUY", risk_ctx)
        
        limit_str = f"{max_invest_limit}元" if max_invest_limit > 0 else "NA (不限)"
        target_str = f"{target_amount}元" if target_amount > 0 else "NA (未设定)"
        dca_str = f"{dca_amount}元" if dca_amount > 0 else "0 (非定投)"
        
        macro_str = json.dumps(macro_context, ensure_ascii=False, cls=NumpyEncoder) if macro_context else "数据暂缺"
        kronos_signal = macro_context.get('Kronos_Prediction', '模型未就绪')
        
        fallback_instruction = ""
        if "模型未就绪" in kronos_signal:
            fallback_instruction = "⚠️ **注意**: Kronos AI 预测暂时不可用。请重点参考 Shadow NAV。"

        prompt = f"""
# Role: Chief Risk Officer (CIO)
# Language: Chinese (Simplified)
# Task: 对标的【{display_name}】给出明确操作指令。

# 核心数据
- 备注说明: {fund_comment}
- 资产类型: {asset_type}
- 实时估值: {est_nav_chg}% (Shadow NAV)
- 传统技术面: {ma_trend} (均线趋势)
- 持仓状态: {"持有" if holding_qty>0 else "空仓"} (估算盈亏: {pnl_desc})
- 每日限额: {limit_str}
- 定投基准: {dca_str}
- 计划投资总额: {target_str} (Target Allocation)

# AI 预测 (Global Macro)
- Kronos: {kronos_signal}

# 环境与舆情
- 宏观环境: {macro_str}
- 关键新闻: {chr(10).join(news[:5]) if news else "无"}
- 机构/研报观点 (RAG): {rag_context}
- 风控结论: {risk_msg}

# Requirement
Please think and output strictly in Chinese.

# 决策逻辑
{fallback_instruction}
1. **定投优先**: 如果这是定投计划的一部分，且未触发止损，优先建议执行定投。
2. **遵守限额**: 建议买入金额不得超过每日限额。
3. **仓位控制**: 参考"计划投资总额"，如果已接近目标，应减少买入或暂停。
4. **综合研判**: 结合RAG机构观点和实时新闻进行修正。

请输出 JSON:
```json
{{
    "signal": "BUY/SELL/HOLD",
    "reason": "决策理由（包含宏观、技术、舆情/研报三方面，100字以内）",
    "suggested_amount": "建议金额 (数字或'0')"
}}
""" 
        print("   🧠 正在生成决策...")
        response = self.client.chat(prompt, model_type="reasoner", use_history=False)
        result_json = self._parse_llm_json(response.get('content', ''))
        
        result_json['fund_name'] = real_name
        result_json['fund_code'] = fund_code
        result_json['comment'] = fund_comment
        result_json['time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        result_json['shadow_nav'] = f"{est_nav_chg:+}%"
        result_json['risk_msg'] = risk_msg
        
        return result_json

    def analyze_index(self, symbol, market_value, pnl_rate, target_amount, name, comment, macro_context, fx_data, debug=False):
        print(f"\n{'='*20} 分析指数: {symbol} {'='*20}")
        
        snapshot, valid = self.fdm.get_realtime_snapshot(symbol)
        
        if not valid:
            print("     ⚠️ 实时行情缺失，尝试仅基于宏观和新闻进行分析...")
            idx_change_pct = 0.0
            real_change_pct = 0.0
            today_pnl_amt = 0.0
            currency_info = "(行情缺失)"
        else:
            current_price = snapshot['price']
            prev_close = snapshot['prev_close']
            idx_change_pct = ((current_price - prev_close) / prev_close) * 100
            
            real_change_pct = idx_change_pct
            currency_info = ""
            
            if symbol.startswith("^") and symbol != "^HSI": 
                usd_rate, usd_chg = fx_data
                real_change_pct = idx_change_pct + usd_chg
                currency_info = f"(含汇率波动 {usd_chg:+.2f}%)"
                
            today_pnl_amt = market_value * (real_change_pct / 100)
            
            print(f"   📉 指数涨跌: {idx_change_pct:+.2f}%")
            print(f"   💰 今日预估: {today_pnl_amt:+.2f} 元 {currency_info}")

        news = self.fdm.provider.news.fetch_sentiment_news(symbol)
        if news:
            print(f"   📰 关联舆情 ({len(news)}条):")
            for n in news[:3]:
                print(f"     - {n[:60]}...")
        else:
            print("   📰 关联舆情: 暂无显著新闻")
        
        ma_trend = "数据不足" 
        try:
            df = self.fdm.provider.fetch_history_kline(symbol, market="US" if symbol.startswith("^") else "A")
            if not df.empty and len(df) > 20:
                 ma20 = df['close'].rolling(20).mean().iloc[-1]
                 if valid and snapshot['price'] > ma20: ma_trend = "多头 ( > MA20)"
                 else: ma_trend = "空头 ( < MA20)"
        except: pass

        target_str = f"{target_amount}元" if target_amount > 0 else "NA (未设定)"
        change_str = f"{idx_change_pct:+.2f}%" if valid else "N/A"

        prompt = f"""
# Role: Chief Investment Officer
# Task: 分析指数持仓【{name} ({symbol})】

# 核心数据
- 持仓市值: {market_value} CNY
- 累计盈亏: {pnl_rate}%
- 计划投资总额: {target_str}
- 今日指数涨跌: {change_str}
- 汇率修正后涨跌: {real_change_pct:+.2f}% {currency_info}
- 今日预估盈亏: {today_pnl_amt:+.1f} CNY
- 技术状态: {ma_trend}

# 宏观环境
{json.dumps(macro_context, ensure_ascii=False, cls=NumpyEncoder)}

# 舆情
{chr(10).join(news[:5]) if news else "无"}

# Requirement
Please think and output strictly in Chinese.

请给出操作建议 (Buy/Sell/Hold) 及简短理由。如果数据缺失，请提示风险。
输出 JSON: {{ "signal": "...", "reason": "...", "suggested_amount": "0" }}
"""
        print("   🧠 请求 AI 决策...")
        response = self.client.chat(prompt, model_type="reasoner", use_history=False)
        result_json = self._parse_llm_json(response.get('content', ''))
        
        result_json['fund_name'] = name if name else symbol
        result_json['fund_code'] = symbol
        result_json['comment'] = f"[指数] {comment}"
        result_json['time'] = datetime.now().strftime('%m-%d %H:%M')
        result_json['shadow_nav'] = f"{real_change_pct:+.2f}%" if valid else "N/A"
        result_json['risk_msg'] = f"今日 {today_pnl_amt:+.0f}元" if valid else "行情缺失"
        
        return result_json

    def _calculate_ma_trend(self, fund_code, debug=False):
        try:
            df = self.fdm.get_fund_nav_history(fund_code, lookback_days=120)
            if len(df) < 20: return "数据不足"
            
            ma10 = df['nav'].rolling(window=10).mean().iloc[-1]
            ma20 = df['nav'].rolling(window=20).mean().iloc[-1]
            ma60 = df['nav'].rolling(window=60).mean().iloc[-1]
            current = df['nav'].iloc[-1]
            
            trend = "震荡"
            if current > ma20 and ma20 > ma60: trend = "多头排列 (Strong Up)"
            elif current < ma20 and ma20 < ma60: trend = "空头排列 (Strong Down)"
            elif current > ma20: trend = "短期反弹"
            
            return f"{trend} (MA20={ma20:.3f}, Now={current:.3f})"
        except: return "计算失败"

    def _parse_llm_json(self, content):
        try:
            match = re.search(r'```json(.*?)```', content, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                return json.loads(json_str)
            return json.loads(content)
        except:
            return {
                "signal": "HOLD", 
                "reason": f"JSON解析失败，LLM回复异常: {content[:50]}...", 
                "suggested_amount": "0"
            }