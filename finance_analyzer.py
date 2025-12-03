# deepseek_finance_project_V3/finance_analyzer.py

import json
import re
import os
import pandas as pd
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

class FinancialAnalyzer:
    def __init__(self, deepseek_client, fund_data_mgr, portfolio_manager, operation_logger):
        self.client = deepseek_client
        self.fdm = fund_data_mgr
        self.pm = portfolio_manager
        self.logger = operation_logger
        
        # --- 核心引擎 ---
        self.rbsa = RBSAEngine(self.fdm.db)
        self.shadow = ShadowEngine(self.fdm, self.rbsa)
        self.guard = RiskGuard()
        
        # --- 辅助组件 ---
        self.tech_engine = TechnicalEngine()
        self.macro_analyzer = MacroAnalyzer()
        self.sentiment_engine = SentimentEngine()
        self.rag_engine = FinancialBrainRAG(persist_directory="./brain_memory")
        self.evolution_engine = StrategyEvolutionEngine(db_path='financial_memory.db', deepseek_client=deepseek_client)
        self.prompt_builder = PromptBuilder(self.sentiment_engine, self.rag_engine)
        
        self._kronos_instance = None
        self.indices_config = {'Nasdaq_Future': 'NQ=F', 'SP500_Future': 'ES=F', 'China_A50': 'CN=F', 'Gold': 'GC=F'}
        self.kronos_targets = {"US": "^IXIC", "CN": "000300.SS"}

    @property
    def kronos(self):
        if self._kronos_instance is None:
            print("💤 正在唤醒 Kronos 预测引擎...")
            try:
                self._kronos_instance = KronosAdapter(model_size="small")
            except Exception as e:
                print(f"❌ Kronos 初始化失败: {e}")
                self._kronos_instance = None
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
        """[新增] 分步调试模式，用于排查每一步的数据获取问题"""
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
        print("🌍 正在扫描宏观环境 (期货实时数据)...")
        macro_data = {}
        try:
            macro_data = self.macro_analyzer.analyze_indices_trend(self.indices_config)
            
            if debug:
                print(f"\n🐛 [DEBUG] 原始期货数据: {macro_data}")
                if not macro_data:
                    print("⚠️ [DEBUG] 警告: 未获取到任何期货数据，请检查网络或 YFinance 接口。")

            macro_liquidity = self.macro_analyzer.analyze_macro_liquidity()
            if debug:
                 print(f"🐛 [DEBUG] 宏观流动性指标: {macro_liquidity}")

            print("\n📊 宏观数据概览:")
            print(json.dumps(macro_data, indent=2, ensure_ascii=False))
            
            if predict and self.kronos and self.kronos.is_active:
                print("\n🤖 正在调用 Kronos 进行大盘趋势预测...")
                target_code = self.kronos_targets["US"]
                
                self.fdm.update_market_quotes([target_code])
                df_hist = self.fdm.db.get_market_data(target_code)
                
                if debug:
                    print(f"🐛 [DEBUG] Kronos 输入历史数据长度: {len(df_hist)}")
                    if not df_hist.empty:
                        print(f"🐛 [DEBUG] 历史数据最后一行:\n{df_hist.iloc[-1].to_dict()}")

                snapshot, valid = self.fdm.get_realtime_snapshot(target_code)
                if debug:
                    print(f"🐛 [DEBUG] 实时快照 ({target_code}): {snapshot} (Valid: {valid})")
                
                if valid and not df_hist.empty:
                    last_hist_date = pd.to_datetime(df_hist.iloc[-1]['date']).date()
                    if datetime.now().date() > last_hist_date:
                        print(f"   ⚡ [Realtime Injection] 拼接今日实时K线: {target_code} @ {snapshot['price']}")
                        new_row = pd.DataFrame([{
                            'date': datetime.now(), 'symbol': target_code,
                            'open': snapshot.get('open', snapshot['price']), 
                            'high': snapshot.get('high', snapshot['price']),
                            'low': snapshot.get('low', snapshot['price']),
                            'close': snapshot['price'], 'volume': snapshot.get('volume', 0),
                            'source': 'snapshot'
                        }])
                        df_hist = pd.concat([df_hist, new_row], ignore_index=True)
                
                if df_hist.empty:
                    print("⚠️ [DEBUG] 错误: 没有足够的历史数据供 Kronos 预测。")
                else:
                    pred_us, conf_us, _ = self.kronos.predict_trend(df_hist, pred_len=1)
                    print(f"   🇺🇸 纳斯达克原生指数预测 (T+1): {pred_us} (置信度: {conf_us})")
                    macro_data['Kronos_Prediction'] = f"Nasdaq(T+1): {pred_us}"

            if macro_liquidity:
                return {**macro_data, "US_10Y": macro_liquidity.get("us_10y")}
            return macro_data
        except Exception as e:
            print(f"⚠️ 宏观扫描失败: {e}")
            if debug:
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
            
            if debug:
                print(f"🐛 [DEBUG] {fund_code} 净值历史数据行数: {len(df)}")
            
            if len(df) < 20: 
                if debug: print(f"⚠️ [DEBUG] 数据不足 20 行，无法计算 MA20")
                return "数据不足"
            
            ma10 = df['nav'].rolling(window=10).mean().iloc[-1]
            ma20 = df['nav'].rolling(window=20).mean().iloc[-1]
            ma60 = df['nav'].rolling(window=60).mean().iloc[-1]
            current = df['nav'].iloc[-1]
            
            if debug:
                print(f"🐛 [DEBUG] MA 指标: Now={current:.3f}, MA10={ma10:.3f}, MA20={ma20:.3f}, MA60={ma60:.3f}")

            trend = "震荡"
            if current > ma20 and ma20 > ma60: trend = "多头排列 (Strong Up)"
            elif current < ma20 and ma20 < ma60: trend = "空头排列 (Strong Down)"
            elif current > ma20: trend = "短期反弹"
            
            return f"{trend} (MA20={ma20:.3f}, Now={current:.3f})"
        except Exception as e:
            if debug: print(f"🐛 [DEBUG] MA 计算发生异常: {e}")
            return "计算失败"

    def _analyze_fund_trend(self, fund_code, user_cost, holding_qty, max_invest_limit, dca_amount, macro_context, debug=False, fund_comment="", batch_mode=False, stop_stage=None):
        if debug: print(f"\n{'='*20} 开始分析: {fund_code} {'='*20}")
        
        # --- Step 1: Info ---
        info = self.fdm.get_fund_basic_info(fund_code)
        if debug: print(f"🐛 [DEBUG] 基金基础信息 (Info): {info}")
        
        if not info:
            print(f"⚠️ 警告: 无法获取 {fund_code} 的基础信息，可能代码错误或数据源暂不可用。")
            asset_type = 'unknown'
            real_name = fund_code
        else:
            asset_type = info.get('type', 'stock') 
            real_name = info.get('name', fund_code)
            
        display_name = f"{real_name} ({fund_code})"
        print(f"\n🔍 分析中: {display_name} {f'[{fund_comment}]' if fund_comment else ''} ...")
        
        if stop_stage == 1:
            print(f"\n🛑 [DEBUG STOP] 步骤1: 基础信息获取完毕。\n{json.dumps(info, ensure_ascii=False, indent=2)}")
            return None

        # --- Step 2: Holdings & Shadow ---
        holdings = self.fdm.get_top_holdings(fund_code)
        if debug:
            print(f"🐛 [DEBUG] 前十大持仓 (Top Holdings): {len(holdings)} 条")
            for h in holdings[:10]: # Limit print to 10
                print(f"   - {h['stock_name']} ({h['stock_code']}): {h['weight']}%")
        
        if not holdings:
             print("⚠️ 警告: 未获取到持仓明细，Shadow NAV 估算可能不准确。")

        est_nav_chg, basis = self.shadow.calc_realtime_nav(fund_code, holdings)
        print(f"   🔮 Shadow NAV: {est_nav_chg:+}%")
        if debug:
            print(f"🐛 [DEBUG] Shadow NAV 计算说明: {basis}")
            print(f"🐛 [DEBUG] 估算结果: {est_nav_chg}")
            
        if stop_stage == 2:
            print(f"\n🛑 [DEBUG STOP] 步骤2: 影子净值计算完毕。\n结果: {est_nav_chg}%\n基准: {basis}")
            return None
        
        # --- Step 3: News ---
        news = self.fdm.get_aggregated_news(fund_code)
        if debug:
            print(f"🐛 [DEBUG] 聚合新闻条数: {len(news)}")
            if news: print(f"   - 第一条: {news[0][:50]}...")
            
        if stop_stage == 3:
            print(f"\n🛑 [DEBUG STOP] 步骤3: 舆情获取完毕。\n{json.dumps(news, ensure_ascii=False, indent=2)}")
            return None
        
        # --- Step 4: Technical ---
        ma_trend = self._calculate_ma_trend(fund_code, debug=debug)
        
        if stop_stage == 4:
            print(f"\n🛑 [DEBUG STOP] 步骤4: 技术指标计算完毕。\n趋势: {ma_trend}")
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
        risk_ctx = {
            "shadow_change": est_nav_chg, 
            "holding_pnl": holding_pnl_pct,
            "has_holding": (holding_qty > 0),
            "asset_type": asset_type,
            "max_invest_limit": max_invest_limit
        }
        
        if debug:
            print(f"🐛 [DEBUG] 提交给 RiskGuard 的上下文: {json.dumps(risk_ctx, ensure_ascii=False)}")
            
        is_safe, risk_msg = self.guard.check_risk("BUY", risk_ctx)
        
        if debug:
             print(f"🐛 [DEBUG] 风控结论: Safe={is_safe}, Msg={risk_msg}")
             
        if stop_stage == 5:
            print(f"\n🛑 [DEBUG STOP] 步骤5: 风控检查完毕。\n上下文: {risk_ctx}\n结论: {risk_msg}")
            return None

        # --- Step 6: Prompt & LLM ---
        macro_str = json.dumps(macro_context, ensure_ascii=False) if macro_context else "数据暂缺"
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

# AI 预测
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
            print(f"\n🛑 [DEBUG STOP] 步骤6: Prompt生成完毕，流程中断。")
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
            macro_items = ""
            for k, v in macro_data.items():
                macro_items += f"<div style='display:inline-block; background:#dfe6e9; padding:8px 15px; margin:5px; border-radius:20px; font-size:14px;'><b>{k}:</b> {v}</div>"
            macro_html = f"<div style='margin-bottom:20px;'>{macro_items}</div>"
        
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