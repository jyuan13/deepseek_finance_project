# deepseek_finance_project_V3/finance_analyzer.py

"""
==========================================================================================
【文件定义】
文件名: finance_analyzer.py
类名  : FinancialAnalyzer
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(deepseek_client, fund_data_mgr, portfolio_manager, operation_logger)
   [初始化所有子引擎] -> (RBSA, Shadow, Guard, Tech, Macro, Sentiment, RAG, Evolution)
          ↓
   [初始化 FinanceCore] -> [初始化 FinanceReporter]

2. kronos (property)
   [Lazy Load] -> [尝试实例化 KronosAdapter] -> [返回实例或None]

3. run_analysis_menu
   [Print 标题 & Kronos 状态] -> [调用 _analyze_portfolio_all]

4. _ask_debug_mode
   [Input (y/n)] -> [Return bool]

5. _analyze_portfolio_all
   [Ask Debug] -> [Core.scan_macro_environment]
          ↓
   [获取 PM.get_fund_positions] -> [遍历持仓]
     -> [检查 shares==0 and market_val>0 ?] (Lite配置判断)
     -> (Yes) -> [FDM.get_realtime_snapshot] -> [Calc Shares & Cost]
     -> (No)  -> [使用已有 Shares & Cost]
          ↓
   [Core.analyze_fund (传入计算后的数据)] -> [Reporter.gen_card]
          ↓
   [获取 PM.get_index_positions] -> [遍历指数] -> [FDM.get_exchange_rate]
          ↓
   [Core.analyze_index] -> [Reporter.gen_card]
          ↓
   [Reporter.generate_unified_report]

6. _analyze_free_target
   [Input Code] -> [Core.analyze_fund] -> [Reporter.save_report]

7. _run_step_debug_mode
   [Input Code] -> [Core.scan_macro (Debug=True)] -> [Core.analyze_fund (Debug=True)]

8. manage_rag_system
   [Print RAG Stats] -> [Menu 1.Auto Fetch / 2.Ingest PDF] -> [Call RAG Engine]

9. perform_system_reset
   [Confirm] -> [Clear Logs] -> [Clear DB] -> [Reset RAG/Evolution]
==========================================================================================
"""

from shadow_engine import ShadowEngine
from rbsa_engine import RBSAEngine
from risk_guard import RiskGuard
from prompt_builder import PromptBuilder
from technical_engine import TechnicalEngine
from macro_analyzer import MacroAnalyzer
from sentiment_engine import SentimentEngine
from financial_brain import FinancialBrainRAG
from strategy_evolution import StrategyEvolutionEngine
from kronos_adapter import KronosAdapter

from finance_core import FinanceCore
from finance_report import FinanceReporter

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
        
        self.core = FinanceCore(
            client=self.client,
            fdm=self.fdm,
            shadow_engine=self.shadow,
            risk_guard=self.guard,
            macro_analyzer=self.macro_analyzer,
            prompt_builder=self.prompt_builder,
            kronos_provider=lambda: self.kronos
        )
        self.reporter = FinanceReporter()

    @property
    def kronos(self):
        if self._kronos_instance is None:
            try: self._kronos_instance = KronosAdapter(model_size="small")
            except: self._kronos_instance = None
        return self._kronos_instance

    def run_analysis_menu(self):
        print("\n🚀 V4.0 智能金融分析引擎 (Runtime Calculation)")
        print("=" * 45)
        if self.kronos and self.kronos.is_active: print("✅ Kronos 预测服务: 在线")
        else: print("⚠️  Kronos 预测服务: 离线")

        self._analyze_portfolio_all()

    def _ask_debug_mode(self):
        return input("是否开启调试模式? (y/n): ").lower() == 'y'

    def _analyze_portfolio_all(self):
        """调用 Core 分析，支持运行时自动计算份额"""
        debug = self._ask_debug_mode()
        macro_context = self.core.scan_macro_environment(predict=True, debug=debug)
        
        report_cards = []
        
        # [Fix] 补回缺失的变量定义
        funds = self.pm.get_fund_positions()
        
        if funds:
            print(f"\n📨 正在分析基金持仓 ({len(funds)} 个)...")
            for pos in funds:
                self.client.clear_history()
                
                # [V4.0 Runtime Logic]
                symbol = pos['symbol']
                shares = pos.get('current_shares', 0)
                cost = pos.get('cost_price', 0)
                market_val = pos.get('market_value', 0)
                pnl_rate = pos.get('pnl_rate', 0)
                
                # 如果是 Lite GUI 配置的 (份额为0，但有市值)
                if shares <= 0 and market_val > 0:
                    print(f"   🔄 [{symbol}] 正在获取实时价格以反推份额...")
                    snapshot, valid = self.fdm.get_realtime_snapshot(symbol)
                    current_price = 0
                    if valid and snapshot['price'] > 0:
                        current_price = snapshot['price']
                    else:
                        # 尝试拿最新净值
                        df_nav = self.fdm.get_fund_nav_history(symbol, lookback_days=5)
                        if not df_nav.empty: current_price = df_nav.iloc[-1]['nav']
                    
                    if current_price > 0:
                        shares = market_val / current_price
                        # Cost = Price / (1 + PnL%)
                        cost = current_price / (1 + pnl_rate/100.0)
                        if debug: print(f"     ✅ 反推成功: 价格={current_price:.3f}, 份额={shares:.2f}, 成本={cost:.3f}")
                    else:
                        print(f"     ⚠️ 无法获取价格，无法计算真实盈亏，将仅作基本分析。")

                data_json = self.core.analyze_fund(
                    fund_code=symbol,
                    user_cost=cost,
                    holding_qty=shares,
                    max_invest_limit=pos.get('max_invest_limit', 0),
                    dca_amount=pos.get('dca_config', {}).get('base_amount', 0),
                    target_amount=pos.get('target_amount', 0),
                    macro_context=macro_context,
                    debug=debug,
                    fund_comment=pos.get('comment', '')
                )
                if data_json:
                    self.reporter.print_console_summary(data_json)
                    html = self.reporter.generate_html_card(data_json)
                    report_cards.append(html)

        indices = self.pm.get_index_positions()
        if indices:
            print(f"\n📨 正在分析指数持仓 ({len(indices)} 个)...")
            usd_cny_rate, usd_cny_chg = self.fdm.provider.get_exchange_rate("CNY")
            print(f"   💱 当前美元汇率: {usd_cny_rate:.4f} (变动 {usd_cny_chg:+.2f}%)")
            
            for pos in indices:
                self.client.clear_history()
                data_json = self.core.analyze_index(
                    symbol=pos['symbol'],
                    market_value=pos['market_value_cny'],
                    pnl_rate=pos['pnl_rate'],
                    target_amount=pos.get('target_amount', 0),
                    name=pos.get('name', ''),
                    comment=pos.get('comment', ''),
                    macro_context=macro_context,
                    fx_data=(usd_cny_rate, usd_cny_chg),
                    debug=debug
                )
                if data_json:
                    self.reporter.print_console_summary(data_json)
                    html = self.reporter.generate_html_card(data_json)
                    report_cards.append(html)
        
        if report_cards:
            self.reporter.generate_unified_report(macro_context, report_cards)
        else:
            print("⚠️ 未生成有效报告")

    def _analyze_free_target(self):
        code = input("请输入基金代码: ").strip()
        if not code: return
        self.client.clear_history()
        debug = self._ask_debug_mode()
        macro = self.core.scan_macro_environment(predict=True, debug=debug)
        
        data_json = self.core.analyze_fund(code, 0, 0, 0, 0, 0, macro, debug)
        if data_json:
            self.reporter.print_console_summary(data_json)
            html = self.reporter.generate_html_card(data_json)
            self.reporter.save_report(code, html)

    def _run_step_debug_mode(self):
        print("\n🐞 进入分步调试模式")
        code = input("请输入要调试的基金代码 (如 013403): ").strip()
        if not code: return
        print("注意：新版架构下，分步调试将直接运行全流程并开启详细 Debug 日志。")
        macro = self.core.scan_macro_environment(predict=True, debug=True)
        self.core.analyze_fund(code, 0, 0, 0, 0, 0, macro, debug=True)

    def manage_rag_system(self):
        print("\n🧠 RAG 知识库管理")
        try:
            stats = self.rag_engine.get_collection_stats()
            print(f"当前状态: 研报({stats.get('knowledge_base',0)}) | 经验({stats.get('experience_base',0)})")
        except: print("当前状态: 知识库未初始化")
            
        while True:
            print("\n1. 自动抓取顶级投行观点")
            print("2. 导入本地PDF研报")
            print("0. 返回")
            c = input("选择: ").strip()
            if c == "1": self.rag_engine.auto_fetch_institutional_views(top_n=20)
            elif c == "2": 
                p = input("PDF路径: ").strip()
                if p: self.rag_engine.ingest_pdf_report(p)
            elif c == "0": break

    def perform_system_reset(self):
        print("\n⚠️  [危险操作] 正在请求系统重置...")
        if input("确认要重置吗？请输入 'RESET' 继续: ").strip() != 'RESET': return
        self.logger.clear_logs()
        self.client.clear_all_conversations()
        self.fdm.db.clear_all_data()
        self.rag_engine.reset_all_memories()
        self.evolution_engine.reset_evolution_data()
        print("\n✨ 系统缓存已清理！持仓文件已保留。")