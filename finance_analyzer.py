# deepseek_finance_project_V3/finance_analyzer.py

import json
import re
import os
import pandas as pd
import numpy as np
from datetime import datetime
from shadow_engine import ShadowEngine
from rbsa_engine import RBSAEngine
from risk_guard import RiskGuard
from prompt_builder import PromptBuilder
from fund_data_manager import FundDataManager
from technical_engine import TechnicalEngine
from macro_analyzer import MacroAnalyzer
from sentiment_engine import SentimentEngine
from financial_brain import FinancialBrainRAG
from strategy_evolution import StrategyEvolutionEngine
from kronos_adapter import KronosAdapter

# [V3.50 Fix] 兼容 Numpy 2.0 的 JSON 编码器
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

class FinancialAnalyzer:
    def __init__(self, deepseek_client, fund_data_mgr, portfolio_manager, operation_logger):
        self.client = deepseek_client
        self.fdm = fund_data_mgr
        self.pm = portfolio_manager
        self.logger = operation_logger
        
        self.rbsa = RBSAEngine(self.fdm.db)
        self.shadow = ShadowEngine(self.fdm, self.rbsa)
        self.guard = RiskGuard()
        self.tech_engine = TechnicalEngine()
        self.macro_analyzer = MacroAnalyzer()
        self.sentiment_engine = SentimentEngine()
        self.rag_engine = FinancialBrainRAG(persist_directory="./brain_memory")
        self.evolution_engine = StrategyEvolutionEngine(db_path='financial_memory.db', deepseek_client=deepseek_client)
        self.prompt_builder = PromptBuilder(self.sentiment_engine, self.rag_engine)
        
        self._kronos_instance = None
        
        # [V3.26] 扩展宏观监测名单 (7大核心指数)
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
        
        # Kronos 预测目标配置 (对应上述指数)
        self.kronos_targets = [
            {"name": "Nasdaq (US)", "symbol": "^IXIC", "market": "US"},
            {"name": "S&P 500 (US)", "symbol": "^GSPC", "market": "US"},
            {"name": "Shanghai (CN)", "symbol": "000001.SS", "market": "A"},
            {"name": "CSI 300 (CN)", "symbol": "000300.SS", "market": "A"},
            {"name": "Hang Seng (HK)", "symbol": "^HSI", "market": "Global"},
            {"name": "HS Tech (HK)", "symbol": "^HSTECH", "market": "Global"},
            {"name": "Nikkei 225 (JP)", "symbol": "^N225", "market": "Global"}
        ]

    @property
    def kronos(self):
        if self._kronos_instance is None:
            try:
                self._kronos_instance = KronosAdapter(model_size="small")
            except Exception: self._kronos_instance = None
        return self._kronos_instance

    def run_analysis_menu(self):
        print("\n🚀 V3.1-01 智能金融分析引擎 (Unified Report & Safe Reset)")
        print("=" * 45)
        
        if self.kronos and self.kronos.is_active:
            print("✅ Kronos 预测服务: 在线")
        else:
            print("⚠️  Kronos 预测服务: 离线 (将在分析时降级策略)")

        while True:
            print("\n1. 💰 持仓基金深度透视 (生成统一日报)")
            print("2. 🔍 任意标的自由透视")
            print("3. 📊 宏观扫描 & Kronos 预测")
            print("4. 🧠 RAG 知识库管理")
            print("5. 🐞 分步调试模式 (Step Debugger)")
            print("99. 🧹 系统重置 (Safe Mode)")
            print("0. 返回")
            
            choice = input("请选择功能 (0-99): ").strip()
            if choice == "1": self._analyze_portfolio_funds()
            elif choice == "2": self._analyze_free_target()
            elif choice == "3": self._scan_macro_environment(predict=True, debug=True)
            elif choice == "4": self.manage_rag_system()
            elif choice == "5": self._run_step_debug_mode()
            elif choice == "99": self.perform_system_reset()
            elif choice == "0": break
            else: print("❌ 无效输入")

    def _ask_debug_mode(self):
        return input("是否开启调试模式? (y/n): ").lower() == 'y'

    def _run_step_debug_mode(self):
        print("\n🐞 进入分步调试模式")
        print("此模式将把分析流程拆解，执行完选定步骤后立即暂停并打印全部数据。")
        code = input("请输入要调试的基金代码 (如 013403): ").strip()
        if not code: return

        print("\n请选择中断点 (Stop At):")
        print("1. 📝 基础信息 (Info & Type)")
        print("2. 🔮 持仓 & 影子净值 (Holdings & Shadow NAV)")
        print("3. 📰 舆情数据 (News)")
        print("4. 📈 技术指标 (MA Trend)")
        print("5. 🛡️ 风控检查 (Risk Guard)")
        print("6. 🧠 提示词生成 (Prompt Builder)")
        
        step = input("选择步骤 (1-6): ").strip()
        if not step.isdigit(): return
        
        macro = self._scan_macro_environment(predict=True, debug=True)
        self._analyze_fund_trend(code, 0, 0, 0, 0, macro, debug=True, batch_mode=False, stop_stage=int(step))
        print("\n✅ 调试结束，流程已中断。")

    def _scan_macro_environment(self, predict=False, debug=False):
        print("🌍 正在扫描宏观环境 (读取本地缓存/联网)...")
        macro_data = {}
        try:
            # 1. 基础趋势 (YFinance/AkShare)
            macro_data = self.macro_analyzer.analyze_indices_trend(self.indices_config)
            
            if debug: print(f"\n🐛 [DEBUG] 宏观数据: {macro_data}")
            
            macro_liquidity = self.macro_analyzer.analyze_macro_liquidity()

            print("\n📊 宏观数据概览:")
            for k, v in macro_data.items():
                print(f"  - {k:<15}: {v}")
            
            # 2. Kronos 全球预测
            if predict and self.kronos and self.kronos.is_active:
                print(f"\n🤖 Kronos Global Forecast (Scanning {len(self.kronos_targets)} Indices)...")
                
                macro_data['Kronos_Detail'] = []
                macro_data['Kronos_Prediction'] = "See Detail Table"
                
                for target in self.kronos_targets:
                    symbol = target['symbol']
                    market = target['market']
                    name = target['name']
                    
                    # 使用 DataProvider 获取历史 K 线 (自动缓存)
                    df_hist = self.fdm.provider.fetch_history_kline(symbol, market=market)
                    
                    if not df_hist.empty:
                        # 尝试拼接今日实时快照 (减少滞后)
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
                    
                        # 执行预测
                        pred_desc, conf, pred_df = self.kronos.predict_trend(df_hist, pred_len=5, debug=debug)
                        
                        print(f"   🔮 {name:<18} | T+1: {pred_desc} | Conf: {conf}")
                        
                        # 记录到数据结构中，供报告使用
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

    def _analyze_portfolio_funds(self):
        positions = self.pm.get_current_positions()
        if not positions:
            print("⚠️ 当前无持仓配置")
            return
        
        debug = self._ask_debug_mode()
        macro_context = self._scan_macro_environment(predict=True, debug=debug)

        print(f"\n📨 正在生成统一日报 (Unified Dashboard)，共 {len(positions)} 个标的...")
        
        report_cards = []
        
        for pos in positions:
            self.client.clear_history()
            comment = pos.get('//comment', pos.get('comment', ''))
            
            html_card = self._analyze_fund_trend(
                fund_code=pos['symbol'],
                user_cost=pos.get('cost_price', 0),
                holding_qty=pos.get('current_shares', 0),
                max_invest_limit=pos.get('max_invest_limit', 0),
                dca_amount=pos.get('dca_config', {}).get('base_amount', 0),
                macro_context=macro_context,
                debug=debug,
                fund_comment=comment,
                batch_mode=True 
            )
            
            if html_card:
                report_cards.append(html_card)

        if report_cards:
            self._generate_unified_report(macro_context, report_cards)
        else:
            print("⚠️ 未生成任何有效报告")

    def _analyze_free_target(self):
        code = input("请输入基金代码: ").strip()
        if not code: return
        self.client.clear_history()
        debug = self._ask_debug_mode()
        macro = self._scan_macro_environment(predict=True, debug=debug)
        self._analyze_fund_trend(code, 0, 0, 0, 0, macro, debug, batch_mode=False)

    def _calculate_ma_trend(self, fund_code, debug=False):
        """计算均线趋势"""
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

    def _analyze_fund_trend(self, fund_code, user_cost, holding_qty, max_invest_limit, dca_amount, macro_context, debug=False, fund_comment="", batch_mode=False, stop_stage=None):
        if debug: print(f"\n{'='*20} 开始分析: {fund_code} {'='*20}")
        
        # --- Step 1: Info ---
        if stop_stage: print(f"\n👉 步骤 1: 获取基础信息...")
        info = self.fdm.get_fund_basic_info(fund_code)
        if debug: print(f"🐛 [DEBUG] 基金基础信息 (Info): {info}")
        
        asset_type = info.get('type', 'stock') 
        real_name = info.get('name', fund_code)
        display_name = f"{real_name} ({fund_code})"
        
        if stop_stage == 1:
            print(f"\n🛑 [DEBUG STOP] 步骤1 结束。\n{json.dumps(info, ensure_ascii=False, indent=2)}")
            return None

        # --- Step 2: Holdings & Shadow ---
        if stop_stage: print(f"\n👉 步骤 2: 穿透持仓 & 计算影子净值...")
        holdings = self.fdm.get_top_holdings(fund_code)
        if debug:
            print(f"🐛 [DEBUG] 前十大持仓 (Top Holdings): {len(holdings)} 条")
            for h in holdings[:10]: 
                print(f"   - {h['stock_name']} ({h['stock_code']}): {h['weight']}%")
        
        est_nav_chg, basis = self.shadow.calc_realtime_nav(fund_code, holdings)
        if debug:
            print(f"🐛 [DEBUG] Shadow NAV: {est_nav_chg}%")
            print(f"🐛 [DEBUG] Shadow NAV 计算说明: {basis}")
            
        if stop_stage == 2:
            print(f"\n🛑 [DEBUG STOP] 步骤2 结束。\n结果: {est_nav_chg}%\n基准: {basis}")
            return None
        
        # --- Step 3: News ---
        if stop_stage: print(f"\n👉 步骤 3: 获取舆情数据...")
        news = self.fdm.get_aggregated_news(fund_code)
        if debug:
            print(f"🐛 [DEBUG] 聚合新闻条数: {len(news)}")
            
        if stop_stage == 3:
            print(f"\n🛑 [DEBUG STOP] 步骤3 结束。\n{json.dumps(news, ensure_ascii=False, indent=2)}")
            return None
        
        # --- Step 4: Technical ---
        if stop_stage: print(f"\n👉 步骤 4: 计算技术指标...")
        ma_trend = self._calculate_ma_trend(fund_code, debug=debug)
        
        if stop_stage == 4:
            print(f"\n🛑 [DEBUG STOP] 步骤4 结束。\n趋势: {ma_trend}")
            return None
        
        # --- Calc PNL ---
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
        
        # --- Step 5: Risk ---
        if stop_stage: print(f"\n👉 步骤 5: 风控审查...")
        risk_ctx = {
            "shadow_change": est_nav_chg, 
            "holding_pnl": holding_pnl_pct,
            "has_holding": (holding_qty > 0),
            "asset_type": asset_type,
            "max_invest_limit": max_invest_limit
        }
        
        if debug:
            print(f"🐛 [DEBUG] 提交给 RiskGuard 的上下文: {json.dumps(risk_ctx, ensure_ascii=False, cls=NumpyEncoder)}")
            
        is_safe, risk_msg = self.guard.check_risk("BUY", risk_ctx)
        
        if debug:
             print(f"🐛 [DEBUG] 风控结论: Safe={is_safe}, Msg={risk_msg}")
             
        if stop_stage == 5:
            print(f"\n🛑 [DEBUG STOP] 步骤5 结束。\n上下文: {risk_ctx}\n结论: {risk_msg}")
            return None

        # --- Step 6: Prompt & LLM ---
        if stop_stage: print(f"\n👉 步骤 6: 生成 Prompt 并请求 AI...")
        
        # [Fix] 使用 NumpyEncoder 兼容 Numpy 2.0
        macro_str = json.dumps(macro_context, ensure_ascii=False, cls=NumpyEncoder) if macro_context else "数据暂缺"
        limit_str = f"{max_invest_limit}元" if max_invest_limit > 0 else "无"
        
        kronos_signal = macro_context.get('Kronos_Prediction', '模型未就绪')
        
        fallback_instruction = ""
        if "模型未就绪" in kronos_signal:
            fallback_instruction = """
            ⚠️ **注意**: Kronos AI 预测暂时不可用。请立即降级策略：
            1. **重点参考 Shadow NAV**: 这是最实时的估值，如果 > 0.5% 且美股期货上涨，依然可以视为买入信号。
            2. **参考均线趋势**: 关注 MA20/MA60 状态。
            3. **定投策略**: 如果是定投基金(DCA)，只要没有暴跌风险，应建议继续定投以平摊成本。
            """

        prompt = f"""
# 角色: 首席风控官 (CIO)
# 任务: 对标的【{display_name}】给出明确操作指令。

# 核心数据
- 备注说明: {fund_comment}
- 资产类型: {asset_type}
- 实时估值: {est_nav_chg}% (Shadow NAV)
- 传统技术面: {ma_trend} (均线趋势)
- 持仓状态: {"持有" if holding_qty>0 else "空仓"} (估算盈亏: {pnl_desc})
- 每日限额: {limit_str}
- 定投基准: {dca_amount}元 (如果是定投策略)

# AI 预测 (Global Macro)
- Kronos: {kronos_signal}

# 环境
- 宏观: {macro_str}
- 舆情: {chr(10).join(news[:3]) if news else "无"}
- 风控结论: {risk_msg}

# 决策逻辑
{fallback_instruction}
1. **定投优先**: 如果这是定投计划的一部分（见定投基准），且今日未触发止损，优先建议执行定投。
2. **遵守限额**: 建议买入金额不得超过 {limit_str}。
3. **拒绝无脑观望**: 即使模型未就绪，也要根据实时估值和均线给出方向性建议（买/卖/持），除非市场确实极度不明朗。

请输出 JSON:
```json
{{
    "signal": "BUY/SELL/HOLD",
    "reason": "决策理由（100字以内）",
    "suggested_amount": "建议金额 (数字或'0')"
}}
""" 
        if debug: 
            print(f"\n🐞 [DEBUG] 发送给 LLM 的 Prompt:\n{'-'*40}\n{prompt}\n{'-'*40}")
            
        if stop_stage == 6:
            print(f"\n🛑 [DEBUG STOP] 步骤6 结束 (Prompt已打印)。")
            return None
        
        print("   🧠 正在生成决策...")
        response = self.client.chat(prompt, model_type="reasoner", use_history=False)
        
        if debug:
            print(f"🐛 [DEBUG] LLM 原始回复:\n{response.get('content', 'No content')}")
        
        result_json = self._parse_llm_json(response.get('content', ''))
        
        if debug:
             print(f"🐛 [DEBUG] 解析后的 JSON: {result_json}")

        result_json['fund_name'] = real_name
        result_json['fund_code'] = fund_code
        result_json['comment'] = fund_comment
        result_json['time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        result_json['shadow_nav'] = f"{est_nav_chg:+}%"
        result_json['risk_msg'] = risk_msg
        
        html_report = self._generate_html_card(result_json)
        
        if batch_mode:
            self._print_console_summary(result_json)
            return html_report
        else:
            self._save_report(fund_code, html_report)
            self._print_console_summary(result_json)
            return None

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

    def _generate_html_card(self, data):
        color_map = {"BUY": "#d63031", "SELL": "#00b894", "HOLD": "#636e72"}
        color = color_map.get(data.get('signal', 'HOLD'), "#636e72")
        
        html = f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: white; font-family: 'Segoe UI', sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #eee; padding-bottom: 8px; margin-bottom: 12px;">
                <div>
                    <span style="font-size: 18px; font-weight: bold; color: #2d3436;">{data['fund_name']}</span>
                    <span style="font-size: 14px; color: #636e72; margin-left: 8px;">{data['fund_code']}</span>
                </div>
                <div style="font-size: 12px; color: #b2bec3;">{data['time']}</div>
            </div>
            
            <div style="margin-bottom: 8px;">
                <span style="background-color: #f1f2f6; color: #2d3436; padding: 2px 6px; border-radius: 4px; font-size: 12px;">{data['comment']}</span>
            </div>

            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <div style="background-color: {color}; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-size: 16px;">
                    {data['signal']}
                </div>
                <div style="margin-left: 16px; font-size: 14px;">
                    建议金额: <span style="font-weight: bold; color: {color};">{data['suggested_amount']}</span>
                </div>
            </div>

            <div style="background-color: #f9f9f9; padding: 12px; border-radius: 4px; color: #2d3436; font-size: 14px; line-height: 1.5;">
                {data['reason']}
            </div>

            <div style="margin-top: 12px; font-size: 12px; color: #636e72; display: flex; gap: 16px;">
                <span>🔮 影子净值: <b>{data['shadow_nav']}</b></span>
                <span>🛡️ 风控: {data['risk_msg']}</span>
            </div>
        </div>
        """
        return html

    def _generate_unified_report(self, macro_data, cards_html):
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        macro_html = ""
        if macro_data:
            # 1. 基础宏观数据
            macro_items = ""
            for k, v in macro_data.items():
                if k != 'Kronos_Detail': # 跳过详情列表
                    macro_items += f"<div style='display:inline-block; background:#dfe6e9; padding:8px 15px; margin:5px; border-radius:20px; font-size:14px;'><b>{k}:</b> {v}</div>"
            macro_html = f"<div style='margin-bottom:20px;'>{macro_items}</div>"
            
            # 2. Kronos 趋势详情表 (新增)
            if 'Kronos_Detail' in macro_data and macro_data['Kronos_Detail']:
                kronos_table = """
                <div style="margin-top: 15px; background: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 4px solid #6c5ce7;">
                    <h4 style="margin: 0 0 10px 0; color: #6c5ce7;">🤖 Kronos AI Forecast (Global T+1)</h4>
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <tr style="background: #e1e4e8;">
                            <th style="padding: 6px; text-align: left;">Index</th>
                            <th style="padding: 6px; text-align: left;">Date</th>
                            <th style="padding: 6px; text-align: right;">Target</th>
                            <th style="padding: 6px; text-align: right;">Chg%</th>
                            <th style="padding: 6px; text-align: right;">Conf</th>
                        </tr>
                """
                for row in macro_data['Kronos_Detail']:
                    color = "red" if float(row['chg'].replace('%','')) > 0 else "green"
                    kronos_table += f"""
                        <tr>
                            <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['name']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee;">{row['date']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['close']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right; color: {color}; font-weight: bold;">{row['chg']}</td>
                            <td style="padding: 6px; border-bottom: 1px solid #eee; text-align: right;">{row['conf']}</td>
                        </tr>
                    """
                kronos_table += "</table></div>"
                macro_html += kronos_table

        full_html = f"""
        <html>
        <head>
            <title>DeepSeek Finance Daily Report - {date_str}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f6fa; color: #2d3436; padding: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section-title {{ color: #2c3e50; border-left: 5px solid #0984e3; padding-left: 10px; margin-top: 30px; margin-bottom: 20px; }}
                .macro-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 30px; }}
                .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 DeepSeek Finance Daily Report</h1>
                <p style="color: #636e72;">Generated on {date_str}</p>
            </div>
            
            <h2 class="section-title">🌍 Global Macro Overview</h2>
            <div class="macro-box">
                {macro_html if macro_html else "<p>暂无宏观数据</p>"}
            </div>

            <h2 class="section-title">💼 Portfolio Analysis ({len(cards_html)} Positions)</h2>
            <div class="grid-container">
                {"".join(cards_html)}
            </div>
            
            <div style="text-align: center; margin-top: 50px; color: #b2bec3; font-size: 12px;">
                Powered by DeepSeek Finance V3
            </div>
        </body>
        </html>
        """
        
        try:
            if not os.path.exists("data"): os.makedirs("data")
            filename = f"data/Daily_Report_{datetime.now().strftime('%Y%m%d')}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(full_html)
            print(f"\n📊 统一日报已生成: {filename}")
            
        except Exception as e:
            print(f"❌ 统一日报保存失败: {e}")

    def _print_console_summary(self, data):
        color_code = "\033[91m" if data['signal'] == "BUY" else "\033[92m" if data['signal'] == "SELL" else "\033[90m"
        reset_code = "\033[0m"
        print(f"   🎯 结论: {color_code}{data['signal']}{reset_code} | 金额: {data['suggested_amount']}")
        print(f"   📝 理由: {data['reason']}")
        print("   " + "-"*30)

    def _save_report(self, symbol, content):
        try:
            if not os.path.exists("data"): os.makedirs("data")
            path = f"data/Advice_{symbol}_{datetime.now().strftime('%Y%m%d')}.html"
            mode = 'a' if os.path.exists(path) else 'w'
            with open(path, mode, encoding='utf-8') as f: f.write(content)
            print(f"   💾 卡片已存: {path}")
        except Exception as e: 
            print(f"❌ 报告保存失败: {e}")

    def perform_system_reset(self):
        print("\n⚠️  [危险操作] 正在请求系统重置...")
        print("此操作将清除缓存数据库、日志和AI记忆，但会【保留】您的持仓配置(my_portfolio.json)。")
        confirm = input("确认要重置吗？请输入 'RESET' 继续: ").strip()
        if confirm != 'RESET':
            print("❌ 操作已取消")
            return

        print("\n⏳ 正在执行深度清理...")
        self.logger.clear_logs()
        self.client.clear_all_conversations()
        self.fdm.db.clear_all_data()
        self.rag_engine.reset_all_memories()
        self.evolution_engine.reset_evolution_data()
        print("\n✨ 系统缓存已清理！持仓文件已保留。请重启程序。")

    def manage_rag_system(self):
        print("\n🧠 RAG 知识库管理")
        print("=" * 40)
        try:
            stats = self.rag_engine.get_collection_stats()
            print(f"当前状态: 研报({stats.get('knowledge_base',0)}) | 经验({stats.get('experience_base',0)}) | 新闻({stats.get('news_base',0)})")
        except:
            print("当前状态: 知识库未初始化")
            
        while True:
            print("\n1. 自动抓取顶级投行观点 (EastMoney)")
            print("2. 导入本地PDF研报")
            print("0. 返回")
            choice = input("选择: ").strip()
            
            if choice == "1":
                self.rag_engine.auto_fetch_institutional_views(top_n=20)
            elif choice == "2":
                path = input("请输入PDF文件路径: ").strip()
                if path and path.endswith('.pdf'):
                    self.rag_engine.ingest_pdf_report(path)
                else:
                    print("❌ 无效的文件路径或非PDF文件")
            elif choice == "0":
                break